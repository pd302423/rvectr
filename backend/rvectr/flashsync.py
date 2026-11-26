"""Synchronize cameras from a light pulse recorded at the start and end of a take.

Each camera's brightness is followed frame by frame. A pulse onset is the moment
brightness crosses halfway between its level before and its peak just after,
interpolated between frames. Pulses near the start and near the end give two
offsets; their difference measures clock drift across the take.

Limits: rolling shutter means the onset time depends slightly on where the
light appears in the frame, and auto exposure can distort the brightness curve.
Lock exposure and keep the light in a similar part of every frame.
"""
from __future__ import annotations

import cv2
import numpy as np

from .media import frames, probe


def brightness_series(path, roi=None, scale=0.25, metadata=None):
    """Mean grey level per frame (in an optional [x, y, w, h] region) with source timestamps."""
    metadata = metadata or probe(path)
    times, levels = [], []
    for _, stamp, frame in frames(path, metadata):
        if roi:
            x, y, w, h = (int(v) for v in roi)
            frame = frame[y:y + h, x:x + w]
            if frame.size == 0:
                raise ValueError("Sync region lies outside the frame")
        small = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else frame
        times.append(stamp)
        levels.append(float(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).mean()))
    return np.asarray(times), np.asarray(levels), metadata


def detect_pulses(times, levels, min_rise=6.0, noise_factor=8.0, merge_s=0.3, exposure=None):
    """Rising brightness edges. Returns a list of events with interpolated onset times."""
    t, level = np.asarray(times, float), np.asarray(levels, float)
    if len(t) < 8:
        return []
    if exposure is not None:
        duration = float(exposure["duration_s"])
        anchor = exposure["pts_at"]
        if anchor not in ("start", "centre", "end") or not 0 < duration <= np.median(np.diff(t)) + 1e-6:
            raise ValueError("Exposure needs a measured duration_s and pts_at of start, centre or end")
        shift = {"start": 0, "centre": -0.5, "end": -1}[anchor] * duration
    step = np.diff(level)
    noise = 1.4826 * np.median(np.abs(step - np.median(step))) + 1e-6
    threshold = max(min_rise / 2, noise_factor * noise)
    rising = np.flatnonzero(step > threshold)
    events, last_time = [], -np.inf
    for i in rising:
        if t[i] - last_time < merge_s:
            continue
        before = level[max(0, i - 5):i + 1]
        base = float(np.median(before))
        peak = float(level[i + 1:i + 4].max())
        amplitude = peak - base
        if amplitude < min_rise:
            continue
        half = base + amplitude / 2
        j = i + 1
        while j < len(level) and level[j] < half:
            j += 1
        if j >= len(level) or j == 0:
            continue
        lo, hi = level[j - 1], level[j]
        fraction = 0.0 if hi == lo else float(np.clip((half - lo) / (hi - lo), 0, 1))
        onset = t[j - 1] + fraction * (t[j] - t[j - 1])
        # Without exposure metadata this is a brightness landmark on the PTS
        # clock. Allow for frame sampling and unknown placement of the exposure.
        period = t[j] - t[j - 1]
        bound = 1.5 * period
        method = "half-brightness PTS; exposure timing unknown"
        if exposure is not None:
            # A step illuminates a fraction f of an integrating exposure.
            # For a transition entirely between exposures, retain the dead time.
            first = i if level[i] > base + threshold else i + 1
            lit = float(np.clip((level[first] - base) / amplitude, 0, 1))
            first_start = t[first] + shift
            if lit < 1 - threshold / amplitude:
                onset = first_start + duration * (1 - lit)
                bound = duration * threshold / amplitude
            else:
                previous_end = t[first - 1] + shift + duration
                onset = (previous_end + first_start) / 2
                bound = abs(first_start - previous_end) / 2 + duration * threshold / amplitude
            method = "integrated step with specified exposure timing"
        events.append({"onset_s": float(onset), "timing_method": method,
                       "sampling_uncertainty_s": float(bound), "frame_index": int(j), "baseline": base,
                       "peak": peak, "amplitude": amplitude, "noise": float(noise)})
        last_time = t[i]
    return events


def _pick(events, window):
    inside = [e for e in events if window[0] <= e["onset_s"] <= window[1]]
    return inside[0] if len(inside) == 1 else None


def windows_for(times, start_window_s, end_window_s):
    first, last = float(times[0]), float(times[-1])
    mid = (first + last) / 2
    return (first, min(first + start_window_s, mid)), (max(last - end_window_s, mid), last)


def align(reference, other, frame_period_s, max_drift_fraction=0.005):
    """Offset (and drift) mapping other-camera time onto the reference timeline.

    reference/other: {"start": event, "end": event or None}.
    Mapping: reference_time = other_time + offset_s + drift_rate * (other_time - anchor_s).
    """
    if not reference.get("start") or not other.get("start"):
        return {"status": "failed", "reason": "start_pulse_not_found_in_both_cameras"}
    start_offset = reference["start"]["onset_s"] - other["start"]["onset_s"]
    def uncertainty(which):
        return sum(camera[which].get("sampling_uncertainty_s", frame_period_s * 1.5)
                   for camera in (reference, other))
    result = {"status": "offset_only", "drift_checked": False,
              "method": other["start"].get("timing_method", "supplied flash landmarks"),
              "start_sampling_uncertainty_s": uncertainty("start"), "end_sampling_uncertainty_s": None,
              "independent_residual_s": None,
              "offset_s": float(start_offset), "anchor_s": float(other["start"]["onset_s"]),
              "drift_rate": 0.0, "start_offset_s": float(start_offset), "end_offset_s": None,
              "drift_s": None, "mapping": "reference_time = other_time + offset_s + drift_rate * (other_time - anchor_s)",
              "frame_period_s": float(frame_period_s),
              "uncertainty_note": "Sampling bounds assume a step flash and linear exposure. Rolling shutter, PTS latency, exposure response and nonlinear drift need independent measurement."}
    if reference.get("end") and other.get("end"):
        end_offset = reference["end"]["onset_s"] - other["end"]["onset_s"]
        span = other["end"]["onset_s"] - other["start"]["onset_s"]
        drift = end_offset - start_offset
        result.update(end_offset_s=float(end_offset), drift_s=float(drift))
        if span <= 1.0:
            result.update(status="failed", reason="start_and_end_pulses_too_close")
        elif abs(drift) > max_drift_fraction * span:
            result.update(status="failed", reason="start_and_end_offsets_disagree; pulses probably mismatched")
        else:
            result.update(status="measured", drift_checked=True, drift_rate=float(drift / span),
                          end_sampling_uncertainty_s=uncertainty("end"))
            if abs(drift) > 0.5 * frame_period_s:
                result["warning"] = "Clocks drift by more than half a frame over the take; linear correction applied"
    else:
        result["warning"] = "No end pulse in both cameras: drift could not be checked"
    return result


def to_reference(other_times, sync):
    other_times = np.asarray(other_times, float)
    return other_times + sync["offset_s"] + sync["drift_rate"] * (other_times - sync["anchor_s"])


def to_other(reference_times, sync):
    reference_times = np.asarray(reference_times, float)
    rate = sync["drift_rate"]
    return (reference_times - sync["offset_s"] + rate * sync["anchor_s"]) / (1 + rate)


def synchronize(paths, start_window_s=10.0, end_window_s=10.0, rois=None, exposures=None):
    """Find pulses in every camera and align each to the first. Returns a JSON-ready record."""
    rois = rois or [None] * len(paths)
    cameras = []
    for path, roi, exposure in zip(paths, rois, exposures or [None] * len(paths)):
        t, level, metadata = brightness_series(path, roi=roi)
        events = detect_pulses(t, level, exposure=exposure)
        start_w, end_w = windows_for(t, start_window_s, end_window_s)
        cameras.append({"path": str(path), "events": events, "start": _pick(events, start_w),
                        "end": _pick(events, end_w), "frame_period_s": 1 / metadata["median_fps"],
                        "exposure": exposure, "candidate_counts": {k: sum(lo <= e["onset_s"] <= hi for e in events)
                            for k, (lo, hi) in (("start", start_w), ("end", end_w))},
                        "brightness": {"times_s": t, "levels": level}})
    alignments = [{"status": "reference", "offset_s": 0.0, "drift_rate": 0.0, "anchor_s": 0.0}]
    for other in cameras[1:]:
        period = max(cameras[0]["frame_period_s"], other["frame_period_s"])
        alignments.append(align(cameras[0], other, period))
    return {"cameras": cameras, "alignments": alignments}
