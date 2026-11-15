"""Squat depth from reconstructed hips: jitter, repetitions and reference comparison.

The "pelvis" here is the midpoint of the detector's left and right hip
keypoints after triangulation. It is an estimated internal point, not a skin
marker and not the SMPL pelvis joint. Depth is how far that point drops along
the calibrated vertical, from standing to the bottom of a repetition.

Missing samples stay missing. The smoothing filter never bridges a gap, and a
repetition with too few observed frames is reported as unclear, not guessed.
"""
from __future__ import annotations

import numpy as np

LEFT_HIP, RIGHT_HIP = 11, 12


def pelvis_track(xyz, valid):
    """Midpoint of both hips where both were reconstructed; NaN elsewhere. xyz [F,J,3], valid [F,J]."""
    xyz, valid = np.asarray(xyz, float), np.asarray(valid, bool)
    both = valid[:, LEFT_HIP] & valid[:, RIGHT_HIP]
    pelvis = np.full((len(xyz), 3), np.nan)
    pelvis[both] = 0.5 * (xyz[both, LEFT_HIP] + xyz[both, RIGHT_HIP])
    return pelvis


def height(points, up):
    up = np.asarray(up, float)
    up = up / np.linalg.norm(up)
    return np.asarray(points, float) @ up


def smooth(values, window):
    """Centred moving average over `window` frames; NaN if any sample in the window is missing."""
    values = np.asarray(values, float)
    if window is None or window <= 1:
        return values.copy()
    if window % 2 == 0:
        raise ValueError("Filter window must be an odd number of frames")
    half = window // 2
    flat = values.reshape(len(values), -1)
    out = np.full_like(flat, np.nan)
    for i in range(half, len(values) - half):
        block = flat[i - half:i + half + 1]
        if np.isfinite(block).all():
            out[i] = block.mean(axis=0)
    return out.reshape(values.shape)


def jitter(times, points, window_s, up=None):
    """Spread of a stationary 3D point around its median position, in metres."""
    t, points = np.asarray(times, float), np.asarray(points, float)
    inside = (t >= window_s[0]) & (t <= window_s[1])
    observed = inside & np.isfinite(points).all(axis=1)
    if observed.sum() < 10:
        return {"status": "insufficient_data", "window_s": list(window_s), "samples": int(observed.sum())}
    sample = points[observed]
    distance = np.linalg.norm(sample - np.median(sample, axis=0), axis=1)
    return {"status": "measured", "window_s": list(window_s), "samples": int(observed.sum()),
            "coverage": float(observed.sum() / max(inside.sum(), 1)),
            "rms_m": float(np.sqrt(np.mean(distance ** 2))), "p95_m": float(np.percentile(distance, 95)),
            "max_m": float(distance.max()),
            "vertical_sd_m": None if up is None else float(np.std(height(sample, up)))}


def segment_reps(times, h, standing=None, min_depth_m=0.06, enter_fraction=0.5, edge_fraction=0.1):
    """Find repetitions as dips below the standing height.

    A rep starts where the person leaves standing (within edge_fraction of its
    depth) and ends where they return. Depth = local standing height before the
    rep minus the lowest observed height.
    """
    t, h = np.asarray(times, float), np.asarray(h, float)
    finite = np.isfinite(h)
    if finite.sum() < 10:
        return [], standing
    if standing is None:
        standing = float(np.percentile(h[finite], 95))
    filled = h.copy()
    last = np.nan
    for i in range(len(filled)):  # only for finding dips; measurements use real samples
        last = filled[i] if np.isfinite(filled[i]) else last
        filled[i] = last
    below = np.nan_to_num(filled, nan=standing) < standing - enter_fraction * min_depth_m
    reps, i = [], 0
    while i < len(below):
        if not below[i]:
            i += 1
            continue
        j = i
        while j < len(below) and below[j]:
            j += 1
        segment = np.arange(i, j)
        real = segment[finite[segment]]
        i = j
        if len(real) == 0:
            continue
        bottom = int(real[np.argmin(h[real])])
        previous_end = reps[-1]["end_index"] if reps else 0
        lookback = np.arange(max(previous_end, int(np.searchsorted(t, t[segment[0]] - 1.5))), segment[0] + 1)
        lookback = lookback[finite[lookback]]
        local_standing = float(h[lookback].max()) if len(lookback) else standing
        depth = local_standing - float(h[bottom])
        if depth < min_depth_m:
            continue
        edge = local_standing - edge_fraction * depth
        start = bottom
        while start > previous_end and not (finite[start] and h[start] >= edge):
            start -= 1
        end = bottom
        while end < len(h) - 1 and not (finite[end] and h[end] >= edge):
            end += 1
        span = np.arange(start, end + 1)
        reps.append({"rep": len(reps) + 1, "start_index": int(start), "bottom_index": bottom,
                     "end_index": int(end), "start_s": float(t[start]), "bottom_s": float(t[bottom]),
                     "end_s": float(t[end]), "standing_m": local_standing, "bottom_m": float(h[bottom]),
                     "depth_m": float(depth), "descent_s": float(t[bottom] - t[start]),
                     "coverage": float(finite[span].mean()),
                     "bottom_observed": bool(finite[max(bottom - 1, 0):bottom + 2].all())})
    return reps, standing


def classify(reps, reference_rep=1, tolerance_m=0.03, min_coverage=0.85, borderline_m=0.01):
    """Compare each rep's depth with a reference rep chosen by the participant.

    reached_reference: depth >= reference depth - tolerance.
    shallower: depth below that line. unclear: too little of the rep was observed.
    borderline marks reps within borderline_m of the line.
    """
    reference = next((r for r in reps if r["rep"] == reference_rep), None)
    if reference is None:
        raise ValueError(f"Reference rep {reference_rep} was not found ({len(reps)} reps detected)")
    if reference["coverage"] < min_coverage or not reference["bottom_observed"]:
        raise ValueError("The reference rep itself was not observed well enough; choose another")
    line = reference["depth_m"] - tolerance_m
    out = []
    for rep in reps:
        result = dict(rep)
        if rep["coverage"] < min_coverage or not rep["bottom_observed"]:
            result["outcome"] = "unclear"
        else:
            result["outcome"] = "reached_reference" if rep["depth_m"] >= line else "shallower"
        result["difference_from_reference_m"] = rep["depth_m"] - reference["depth_m"]
        result["borderline"] = bool(abs(rep["depth_m"] - line) <= borderline_m)
        result["is_reference"] = rep["rep"] == reference_rep
        out.append(result)
    return out, {"reference_rep": reference_rep, "reference_depth_m": reference["depth_m"],
                 "tolerance_m": tolerance_m, "pass_line_m": line, "min_coverage": min_coverage,
                 "borderline_m": borderline_m}


def score_against_labels(classified, labels):
    """Count agreement with judgements made from the footage before viewing software output.

    labels: {rep_number: "match" | "shallow" | "unclear"}.
    false_pass: software said reached, footage said shallow.
    false_flag: software said shallower, footage said match.
    """
    counts = {"compared": 0, "agree": 0, "false_pass": 0, "false_flag": 0, "software_unclear": 0,
              "label_unclear": 0, "unlabelled": 0}
    rows = []
    for rep in classified:
        label = labels.get(rep["rep"])
        row = {"rep": rep["rep"], "software": rep["outcome"], "footage": label}
        if label is None:
            counts["unlabelled"] += 1
        elif label == "unclear":
            counts["label_unclear"] += 1
        elif rep["outcome"] == "unclear":
            counts["software_unclear"] += 1
        else:
            counts["compared"] += 1
            said_reached = rep["outcome"] == "reached_reference"
            if said_reached == (label == "match"):
                counts["agree"] += 1
            elif said_reached:
                counts["false_pass"] += 1
            else:
                counts["false_flag"] += 1
        rows.append(row)
    return counts, rows
