"""Squat depth from reconstructed hips: jitter, repetitions and reference comparison.

The "pelvis" here is the midpoint of the detector's left and right hip
keypoints after triangulation. It is an estimated internal point, not a skin
marker and not the SMPL pelvis joint. Depth is how far that point drops along
the calibrated vertical, from standing to the bottom of a repetition.

Missing samples stay missing. The smoothing filter never bridges a gap, and a
repetition with too few observed frames is reported as unclear, not guessed.
"""
from __future__ import annotations

import warnings

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
    vertical_sd = fast_sd = slow_sd = None
    if up is not None:
        vertical_sd = float(np.std(height(sample, up)))
        # Fast noise: how much the height changes from one frame to the next (consecutive observed
        # frames only). Two independent errors differ by sqrt(2) times their size, hence the division.
        # Slow drift changes little from frame to frame, so it hardly shows up here.
        h = height(np.nan_to_num(points), up)
        both = observed[:-1] & observed[1:]
        steps = np.diff(h)[both]
        if len(steps) >= 2:
            fast_sd = float(np.std(steps) / np.sqrt(2))
            # What is left of the total spread once the fast part is taken away is slow drift.
            slow_sd = float(np.sqrt(max(vertical_sd ** 2 - fast_sd ** 2, 0.0)))
    return {"status": "measured", "window_s": list(window_s), "samples": int(observed.sum()),
            "coverage": float(observed.sum() / max(inside.sum(), 1)),
            "rms_m": float(np.sqrt(np.mean(distance ** 2))), "p95_m": float(np.percentile(distance, 95)),
            "max_m": float(distance.max()),
            "vertical_sd_m": vertical_sd, "vertical_fast_sd_m": fast_sd, "vertical_slow_sd_m": slow_sd}


def segment_reps(times, h, standing=None, min_depth_m=0.06, enter_fraction=0.5, edge_fraction=0.1, *,
                 estimator="parabola", standing_window_s=1.0, standing_guard_s=0.5, bottom_cap_m=0.015,
                 max_bottom_gap_s=0.1, min_bottom_samples=5):
    """Find repetitions as dips below the standing height and measure each one's depth.

    A rep starts where the person leaves standing (within edge_fraction of its
    depth) and ends where they return. Depth = standing height before the rep
    minus the height of its bottom. Two estimators of those two heights:

    "parabola" (default): standing = median of the observed samples in the
    standing_window_s before the rep (stopping standing_guard_s before the dip
    starts, so the first movement is not included). Bottom = the lowest point of
    a parabola fitted to the raw samples around the lowest point. Medians and
    fits average noise instead of picking its extremes, so they are not biased.
    Each depth comes with a standard error (depth_se_m).

    "extreme": the original rule (highest standing sample minus lowest bottom
    sample), kept to compare. It reads every depth too deep.

    Missing samples stay missing. A smoothed copy of the trace is used only to
    find dips and choose windows; heights are always measured on real samples.
    """
    if estimator == "extreme":
        return _segment_extreme(times, h, standing, min_depth_m, enter_fraction, edge_fraction)
    if estimator != "parabola":
        raise ValueError("estimator must be 'parabola' or 'extreme'")
    t, h = np.asarray(times, float), np.asarray(h, float)
    finite = np.isfinite(h)
    if finite.sum() < 10:
        return [], standing
    smooth_h = _running_median(h, _median_window(t))
    if standing is None:
        standing = float(np.percentile(smooth_h[np.isfinite(smooth_h)], 95))
    filled = _carry_forward(smooth_h)  # only for finding dips; measurements use real samples
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
        previous_end = reps[-1]["end_index"] if reps else 0
        local = _standing_height(t, h, finite, previous_end, t[segment[0]], standing, standing_window_s,
                                 standing_guard_s)
        bottom = _bottom_height(t, h, finite, smooth_h, segment, real, bottom_cap_m, max_bottom_gap_s,
                                min_bottom_samples)
        depth = local["height"] - bottom["height"]
        if depth < min_depth_m:
            continue
        edge = local["height"] - edge_fraction * depth
        start = bottom["index"]
        while start > previous_end and not (finite[start] and h[start] >= edge):
            start -= 1
        end = bottom["index"]
        while end < len(h) - 1 and not (finite[end] and h[end] >= edge):
            end += 1
        span = np.arange(start, end + 1)
        reps.append({"rep": len(reps) + 1, "estimator": "parabola", "start_index": int(start),
                     "bottom_index": bottom["index"], "end_index": int(end), "start_s": float(t[start]),
                     "bottom_s": bottom["time"], "end_s": float(t[end]), "standing_m": local["height"],
                     "bottom_m": bottom["height"], "depth_m": float(depth), "descent_s": float(bottom["time"] - t[start]),
                     "coverage": float(finite[span].mean()), "bottom_observed": bottom["observed"],
                     "bottom_model": bottom["model"], "bottom_window_stops": list(bottom["stops"]),
                     "standing_source": local["source"], "standing_samples": local["samples"],
                     "standing_se_m": local["se"], "bottom_samples": bottom["samples"],
                     "bottom_max_gap_s": bottom["max_gap_s"], "bottom_se_m": bottom["se"],
                     "depth_se_m": float(np.sqrt(local["se"] ** 2 + bottom["se"] ** 2))})
    return reps, standing


def _median_window(t):
    """About 0.2 s as an odd number of frames (at least 3)."""
    dt = float(np.median(np.diff(t))) if len(t) > 1 else 1.0
    return max(3, 2 * int(round(0.1 / dt)) + 1)


def _running_median(values, window):
    """Centred moving median that ignores missing samples (NaN only if the whole window is missing)."""
    half = window // 2
    padded = np.concatenate([np.full(half, np.nan), values, np.full(half, np.nan)])
    blocks = np.lib.stride_tricks.sliding_window_view(padded, window)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # "all-NaN window" is expected and gives NaN
        return np.nanmedian(blocks, axis=1)


def _carry_forward(values):
    out = values.copy()
    for i in range(1, len(out)):
        if not np.isfinite(out[i]):
            out[i] = out[i - 1]
    return out


def _standing_height(t, h, finite, previous_end, dip_start_s, session_standing, window_s, guard_s):
    """Standing height before one rep: the median of the observed samples while the person stood still.

    First choice: the window_s seconds that end guard_s before the dip starts, but starting no
    earlier than guard_s after the previous rep ended (the person is still rising then and the
    median would be pulled down). If that holds fewer than 10 samples, take every
    observed sample from the end of the previous rep up to the guard. If there are still fewer
    than 5, fall back to the session standing level (and say so).
    """
    guard_s = max(guard_s, 0.2)
    stop = dip_start_s - guard_s
    earliest = t[previous_end] if previous_end > 0 else -np.inf
    # Right after the previous rep the person is still rising, so wait guard_s there as well.
    first_choice_start = max(stop - window_s, earliest + guard_s)
    inside = finite & (t >= first_choice_start) & (t <= stop)
    if inside.sum() < 10:
        inside = finite & (t >= earliest) & (t <= stop)
    if inside.sum() < 5:
        return {"height": float(session_standing), "source": "session", "samples": int(inside.sum()), "se": np.nan}
    values = h[inside]
    centre = float(np.median(values))
    sigma = 1.4826 * float(np.median(np.abs(values - centre)))   # robust spread (median absolute deviation)
    # 1.2533 = sqrt(pi/2): the median of n noisy samples is that much less precise than their mean.
    return {"height": centre, "source": "local", "samples": int(inside.sum()),
            "se": 1.2533 * sigma / np.sqrt(inside.sum())}


def _bottom_height(t, h, finite, smooth_h, segment, real, cap_m, max_gap_s, min_samples):
    """Height and time of the bottom of a dip, from the raw samples near the lowest point.

    Two shapes are possible at the bottom, and "bottom_model" says which one was used:

    "parabola": the pelvis turns round at the bottom. Near the lowest point it has roughly
    constant acceleration, so height against time is a parabola, like a thrown ball at the top
    of its flight. Its vertex is the bottom. Fitting many samples averages out the noise,
    whereas the single lowest sample is the luckiest noise value and sits too low.

    "plateau": the person rests at the bottom (for example on a stool). Height against time is
    flat there, not a parabola, so the fit may open downwards or put its vertex outside the
    samples. Then the bottom is the median of the raw samples that lie on the flat part.

    The samples used are the observed ones next to the smoothed minimum whose smoothed height
    is within cap_m of it (at most 0.5 s either side). The parabola is accepted only if enough
    samples were used, it opens upwards, its vertex lies inside the used samples with at least
    2 on each side, and no gap between used samples exceeds max_gap_s. A parabola rejected for
    its shape becomes a plateau if there are enough samples, no long gap, and the window did not
    end because of missing data or at the edge of the dip (then we cannot tell what happened
    there). Otherwise the bottom is "none": reported as the lowest observed sample for plotting,
    not observed, with no error bar.

    "stops" says why the window stopped growing on each side: "cap" (the smoothed height rose
    above the cap), "limit" (0.5 s reached), "edge" (the edge of the dip) or "missing" (the
    smoothed height is missing there).
    """
    lowest_real = int(real[np.argmin(h[real])])
    fallback = {"index": lowest_real, "time": float(t[lowest_real]), "height": float(h[lowest_real]),
                "observed": False, "samples": 0, "max_gap_s": np.nan, "se": np.nan, "model": "none",
                "stops": (None, None)}
    usable = segment[np.isfinite(smooth_h[segment])]
    if len(usable) == 0:
        return fallback
    k = int(usable[np.argmin(smooth_h[usable])])

    def widen(step, cap):
        """Walk from k in one direction while the smoothed height stays low; return the last index and why we stopped."""
        i = k
        while True:
            if (i == segment[0] and step < 0) or (i == segment[-1] and step > 0):
                return i, "edge"
            if not np.isfinite(smooth_h[i + step]):
                return i, "missing"
            if abs(t[i + step] - t[k]) > 0.5:
                return i, "limit"
            if smooth_h[i + step] > smooth_h[k] + cap:
                return i, "cap"
            i += step

    used = np.array([], int)
    stops = (None, None)
    for cap in (cap_m, 2 * cap_m):   # widen the cap once if too few samples
        lo, why_lo = widen(-1, cap)
        hi, why_hi = widen(+1, cap)
        stops = (why_lo, why_hi)
        used = np.arange(lo, hi + 1)
        used = used[finite[used]]
        if len(used) >= min_samples:
            break
    fallback["samples"] = int(len(used))
    fallback["stops"] = stops
    if len(used) < max(min_samples, 4):
        return fallback
    x = t[used] - t[k]                      # time measured from the lowest point
    design = np.column_stack([np.ones_like(x), x, x ** 2])
    coef, *_ = np.linalg.lstsq(design, h[used], rcond=None)
    c0, c1, c2 = coef
    gaps = np.diff(t[used])
    fallback["max_gap_s"] = float(gaps.max()) if len(gaps) else np.nan
    if gaps.max() > max_gap_s + 1e-6:        # 1e-6 s: rounding of frame times
        return fallback
    vertex_x = -c1 / (2 * c2) if c2 > 0 else np.nan
    vertex_inside = c2 > 0 and (x < vertex_x).sum() >= 2 and (x > vertex_x).sum() >= 2
    if not vertex_inside:                    # opens downwards or vertex outside: not a turning point
        return _plateau(t, h, smooth_h, used, k, real, cap_m, max_gap_s, min_samples, stops, fallback)
    vertex_h = c0 - c1 ** 2 / (4 * c2)
    # Error bar: scatter of the samples around the fit gives the coefficient covariance;
    # the delta method turns it into an error on the vertex height.
    residual = h[used] - design @ coef
    variance = float(residual @ residual) / (len(used) - 3)
    covariance = variance * np.linalg.inv(design.T @ design)
    gradient = np.array([1.0, -c1 / (2 * c2), c1 ** 2 / (4 * c2 ** 2)])
    se = float(np.sqrt(max(gradient @ covariance @ gradient, 0.0)))
    vertex_s = float(t[k] + vertex_x)
    nearest = int(real[np.argmin(np.abs(t[real] - vertex_s))])
    return {"index": nearest, "time": vertex_s, "height": float(vertex_h), "observed": True,
            "samples": int(len(used)), "max_gap_s": fallback["max_gap_s"], "se": se, "model": "parabola",
            "stops": stops}


def _plateau(t, h, smooth_h, used, k, real, cap_m, max_gap_s, min_samples, stops, fallback):
    """Bottom of a person resting at the bottom: the median of the flat part, or "none" if it cannot be trusted."""
    # A hole next to the bottom, or a window that ran into the edge of the dip (the recording started
    # or stopped while the person was down): we cannot tell what happened there, so do not guess.
    if "missing" in stops or "edge" in stops:
        return fallback
    flat = used[smooth_h[used] <= smooth_h[k] + cap_m / 3]   # samples within a third of the cap of the lowest level
    if len(flat) < min_samples:
        return fallback
    if len(flat) > 1 and np.diff(t[flat]).max() > max_gap_s + 1e-6:
        return fallback
    values = h[flat]
    centre = float(np.median(values))
    sigma = 1.4826 * float(np.median(np.abs(values - centre)))   # robust spread (median absolute deviation)
    bottom_s = float(np.median(t[flat]))
    nearest = int(real[np.argmin(np.abs(t[real] - bottom_s))])
    # 1.2533 = sqrt(pi/2): the median of n noisy samples is that much less precise than their mean.
    return {"index": nearest, "time": bottom_s, "height": centre, "observed": True, "samples": int(len(flat)),
            "max_gap_s": float(np.diff(t[flat]).max()) if len(flat) > 1 else np.nan,
            "se": 1.2533 * sigma / np.sqrt(len(flat)), "model": "plateau", "stops": stops}


def _segment_extreme(times, h, standing, min_depth_m, enter_fraction, edge_fraction):
    """The original estimator: highest standing sample, lowest bottom sample.

    A rep starts where the person leaves standing (within edge_fraction of its
    depth) and ends where they return. Depth = local standing height before the
    rep minus the lowest observed height. Kept for comparison: the extremes of
    noisy samples are biased (the maximum sits too high, the minimum too low),
    so every depth comes out too deep.
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
        reps.append({"rep": len(reps) + 1, "estimator": "extreme", "bottom_model": "extreme", "start_index": int(start), "bottom_index": bottom,
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
    borderline marks reps close to the line: within borderline_m, or within twice
    the standard error of (this depth - reference depth) if that is larger and known.
    """
    reference = next((r for r in reps if r["rep"] == reference_rep), None)
    if reference is None:
        raise ValueError(f"Reference rep {reference_rep} was not found ({len(reps)} reps detected)")
    if reference["coverage"] < min_coverage or not reference["bottom_observed"]:
        raise ValueError("The reference rep itself was not observed well enough; choose another")
    line = reference["depth_m"] - tolerance_m
    reference_se = reference.get("depth_se_m", np.nan)
    out = []
    for rep in reps:
        result = dict(rep)
        if rep["coverage"] < min_coverage or not rep["bottom_observed"]:
            result["outcome"] = "unclear"
        else:
            result["outcome"] = "reached_reference" if rep["depth_m"] >= line else "shallower"
        result["difference_from_reference_m"] = rep["depth_m"] - reference["depth_m"]
        # Both depths carry an error, so their difference has the two errors combined (added as squares).
        if rep["rep"] == reference_rep:
            difference_se = 0.0
        else:
            difference_se = float(np.sqrt(rep.get("depth_se_m", np.nan) ** 2 + reference_se ** 2))
        result["difference_se_m"] = difference_se
        margin = max(borderline_m, 2 * difference_se) if np.isfinite(difference_se) else borderline_m
        result["borderline"] = bool(abs(rep["depth_m"] - line) <= margin)
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
