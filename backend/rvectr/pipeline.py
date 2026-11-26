"""Two-camera squat pipeline: sync -> 2D keypoints -> triangulation -> pelvis depth.

Every stage writes its evidence into one numbered run folder (outputs/V1.1.N).
The pure functions here (reconstruct_sequence, measure_squats) take arrays so
they can be tested on synthetic cameras without video files.
"""
from __future__ import annotations

import csv
import json
from itertools import combinations
import platform
import sys
import traceback
from pathlib import Path

import numpy as np

from . import experiment, flashsync, oneview, pose2d, squat
from .configuration import load_camera_calibration, load_capture_config
from .geometry import triangulate_points
from .kinematics import JOINT_NAMES
from .media import probe
from .records import allocate_run, sha256, utc_now, write_json
from .sync import interpolate_observations

DEFAULTS = {
    "sync": {"method": "flash", "start_window_s": 10.0, "end_window_s": 10.0, "roi": {}},
    "pose": {"mode": "balanced", "device": pose2d.DEFAULT_DEVICE, "backend": "onnxruntime", "stride": 1,
             "det_frequency": 5},
    "triangulation": {"min_confidence": 0.3, "max_reprojection_px": 10.0, "min_ray_angle_deg": 3.0},
    "squat": {"standing_window_s": None, "reference_rep": 1, "tolerance_m": 0.03, "filter_frames": 5,
              "min_rep_depth_m": 0.06, "min_coverage": 0.85, "borderline_m": 0.01, "primary": "raw",
              "estimator": "parabola"},
    "views": {"compare": True, "standing_point_m": None, "hip_line": None},
    "experiment": {"annotations": None, "match_window_s": 0.5, "tolerance_m": 0.03, "borderline_m": 0.01},
}


def load_session(path):
    path = Path(path)
    config = load_capture_config(path)
    set_by_user = "device" in (config.get("pose") or {})
    for section, values in DEFAULTS.items():
        config[section] = {**values, **(config.get(section) or {})}
    config["pose"]["device_source"] = "config" if set_by_user else "default"
    if config["squat"]["primary"] not in ("raw", "filtered"):
        raise ValueError("squat.primary must be 'raw' or 'filtered'")
    if config["squat"]["estimator"] not in ("parabola", "extreme"):
        raise ValueError("squat.estimator must be 'parabola' or 'extreme'")
    views = config["views"]
    if (views["standing_point_m"] is None) != (views["hip_line"] is None):
        raise ValueError("views.standing_point_m and views.hip_line must be given together (or both left out)")
    for key in ("standing_point_m", "hip_line"):
        if views[key] is not None and (np.shape(views[key]) != (3,) or not np.isfinite(views[key]).all()):
            raise ValueError(f"views.{key} must be three numbers in the calibration frame")
    experiment_settings = config["experiment"]
    if experiment_settings["annotations"]:
        annotations_path = Path(experiment_settings["annotations"])
        if not annotations_path.is_absolute():
            annotations_path = path.resolve().parent / annotations_path
        experiment_settings["annotations"] = str(annotations_path.resolve())
    if experiment_settings["match_window_s"] <= 0 or experiment_settings["tolerance_m"] < 0 or experiment_settings["borderline_m"] < 0:
        raise ValueError("experiment.match_window_s must be positive and experiment tolerances non-negative")
    config["_path"] = str(path.resolve())
    return config


# --------------------------------------------------------------------------- core
def resample_to_reference(observation, reference_times, sync, max_gap_s):
    """Other-camera keypoints at the reference camera's frame times (bounded interpolation only)."""
    query = flashsync.to_other(reference_times, sync)
    return interpolate_observations(observation["times_s"], observation["keypoints"],
                                    observation["scores"], query, max_gap_s=max_gap_s)


def reconstruct_sequence(observations, cameras, syncs, min_confidence=0.3, max_reprojection_px=10.0,
                         min_ray_angle_deg=3.0, frame_periods=None, joints=None):
    """Triangulate every reference-camera frame. observations[0] defines the timeline.

    joints: optional subset of joint indices to reconstruct (others stay NaN).
    """
    reference = observations[0]
    times = np.asarray(reference["times_s"], float)
    frame_periods = frame_periods or [float(np.median(np.diff(o["times_s"]))) for o in observations]
    views_xy, views_score = [np.asarray(reference["keypoints"], float)], [np.asarray(reference["scores"], float)]
    for observation, sync, period in zip(observations[1:], syncs[1:], frame_periods[1:]):
        xy, score = resample_to_reference(observation, times, sync, max_gap_s=1.5 * period)
        views_xy.append(xy)
        views_score.append(score)
    frames, count = views_xy[0].shape[:2]
    subset = np.arange(count) if joints is None else np.asarray(joints, int)
    xyz = np.full((frames, count, 3), np.nan)
    valid = np.zeros((frames, count), bool)
    reprojection = np.full((frames, count), np.nan)
    reasons = {}
    for f in range(frames):
        points = np.stack([v[f, subset] for v in views_xy])
        scores = np.stack([s[f, subset] for s in views_score])
        result = triangulate_points(points, scores, cameras, threshold=min_confidence,
                                    reprojection_px=max_reprojection_px, min_ray_angle_deg=min_ray_angle_deg)
        xyz[f, subset], valid[f, subset], reprojection[f, subset] = (result["xyz"], result["valid"],
                                                                     result["reprojection_px"])
        for reason in result["reasons"]:
            reasons[reason] = reasons.get(reason, 0) + 1
    return {"times_s": times, "xyz": xyz, "valid": valid, "reprojection_px": reprojection,
            "reason_counts": reasons, "views_xy": views_xy, "views_score": views_score}


def measure_squats(times, xyz, valid, up, settings, annotations=None, experiment_settings=None):
    settings = {**DEFAULTS["squat"], **settings}
    pelvis_raw = squat.pelvis_track(xyz, valid)
    pelvis_filtered = squat.smooth(pelvis_raw, settings["filter_frames"], times=times)
    traces = {"raw": squat.height(pelvis_raw, up), "filtered": squat.height(pelvis_filtered, up)}
    window = settings.get("standing_window_s")
    jitter, standing = {}, None
    if window:
        jitter = {name: squat.jitter(times, pts, window, up) for name, pts in
                  (("raw", pelvis_raw), ("filtered", pelvis_filtered))}
        inside = (times >= window[0]) & (times <= window[1]) & np.isfinite(traces["raw"])
        standing = float(np.median(traces["raw"][inside])) if inside.sum() >= 10 else None
    reps = {}
    for name, h in traces.items():
        found, level = squat.segment_reps(times, h, standing=standing, min_depth_m=settings["min_rep_depth_m"],
                                      estimator=settings["estimator"])
        entry = {"standing_level_m": level, "reps": found, "classification": None, "error": None}
        if annotations is not None:
            policy = experiment_settings or DEFAULTS["experiment"]
            scored = experiment.score_condition(annotations, found, policy["match_window_s"], policy["tolerance_m"],
                                                policy["borderline_m"], settings["min_coverage"])
            detected = scored["detections"]
            entry.update(reps=detected, agreement=scored["summary"], attempts=scored["rows"])
            reference = next((rep for rep in detected if rep.get("is_reference") and rep.get("quality_valid")
                              and rep.get("outcome") != "unclear"), None)
            if reference is None:
                entry["error"] = "Intended reference missed or rejected; no reference-relative decisions"
            else:
                entry["classification"] = {**scored["summary"]["decision_rule"],
                                           "reference_rep": reference["rep"], "reference_annotation_id": reference["annotation_id"],
                                           "reference_depth_m": reference["depth_m"],
                                           "pass_line_m": reference["depth_m"] - policy["tolerance_m"]}
        elif found:
            try:
                classified, rule = squat.classify(found, settings["reference_rep"], settings["tolerance_m"],
                                                  settings["min_coverage"], settings["borderline_m"])
                entry.update(reps=classified, classification=rule)
            except ValueError as error:
                entry["error"] = str(error)
        reps[name] = entry
    filter_effect = []
    for rep in reps["raw"]["reps"]:
        match = min(reps["filtered"]["reps"], key=lambda r: abs(r["bottom_s"] - rep["bottom_s"]), default=None)
        if match is not None and abs(match["bottom_s"] - rep["bottom_s"]) < 0.5:
            filter_effect.append({"rep": rep["rep"], "descent_s": rep["descent_s"],
                                  "depth_raw_m": rep["depth_m"], "depth_filtered_m": match["depth_m"],
                                  "filtered_minus_raw_m": match["depth_m"] - rep["depth_m"]})
    return {"settings": settings, "pelvis_raw": pelvis_raw, "pelvis_filtered": pelvis_filtered,
            "height_m": traces, "jitter": jitter, "reps": reps, "filter_effect": filter_effect,
            "primary": settings["primary"]}


def measure_points(spec, cameras_by_id, max_reprojection_px=10.0):
    """Triangulate hand-marked pixel points (rigid target, skin marker) and compare known distances.

    spec = {"points": {"A": {"cam1": [u, v], "cam2": [u, v]}, ...},
            "distances": [{"from": "A", "to": "B", "known_m": 0.5}, ...]}
    """
    ids = list(cameras_by_id)
    cameras = [cameras_by_id[i] for i in ids]
    names = list(spec["points"])
    pixels = np.full((len(ids), len(names), 2), np.nan)
    for j, name in enumerate(names):
        for c, cam in enumerate(ids):
            if cam in spec["points"][name]:
                pixels[c, j] = spec["points"][name][cam]
    result = triangulate_points(pixels, np.where(np.isfinite(pixels).all(axis=2), 1.0, 0.0), cameras,
                                reprojection_px=max_reprojection_px)
    points = {name: {"xyz_m": result["xyz"][j], "valid": bool(result["valid"][j]),
                     "reprojection_px": result["reprojection_px"][j], "reason": result["reasons"][j]}
              for j, name in enumerate(names)}
    distances = []
    for item in spec.get("distances", []):
        a, b = points[item["from"]], points[item["to"]]
        measured = float(np.linalg.norm(a["xyz_m"] - b["xyz_m"])) if a["valid"] and b["valid"] else None
        known = item.get("known_m")
        distances.append({**item, "measured_m": measured,
                          "error_m": None if measured is None or known is None else measured - known})
    return {"points": points, "distances": distances}


# --------------------------------------------------------------------------- number of camera views
# The research question is how accuracy changes with the number of views, so the same
# 2D detections are measured again with one camera, every pair, and all cameras.
VIEW_COLUMNS = ["condition", "cameras", "model", "rep", "depth_m", "depth_se_m", "difference_from_reference_m",
                "difference_se_m", "outcome", "bottom_model", "coverage", "depth_minus_all_views_m"]
MATCH_WINDOW_S = 0.5   # a rep of another condition counts as the same rep if its bottom is this close


def _sync_between(first, other):
    """Sync mapping camera `other`'s clock onto camera `first`'s clock (both syncs map onto the reference)."""
    def line(s):   # reference_time = scale * own_time + shift
        return 1 + s["drift_rate"], s["offset_s"] - s["drift_rate"] * s["anchor_s"]
    scale_first, shift_first = line(first)
    scale_other, shift_other = line(other)
    scale = scale_other / scale_first
    return {"offset_s": (shift_other - shift_first) / scale_first, "drift_rate": scale - 1, "anchor_s": 0.0}


def _standing_level(times, trace, window):
    """Median height while standing still (same rule as measure_squats); None if too few frames."""
    if not window:
        return None
    inside = (times >= window[0]) & (times <= window[1]) & np.isfinite(trace)
    return float(np.median(trace[inside])) if inside.sum() >= 10 else None


def _standing_plane_inputs(config, sequence, result, up):
    """Standing spot and hip line (calibration frame) for the one-camera planes, and where they came from."""
    views = config["views"]
    if views["standing_point_m"] is not None:
        return (np.asarray(views["standing_point_m"], float), np.asarray(views["hip_line"], float), "measured")
    times, xyz, valid = sequence["times_s"], sequence["xyz"], sequence["valid"]
    both = valid[:, squat.LEFT_HIP] & valid[:, squat.RIGHT_HIP]
    window = config["squat"].get("standing_window_s")
    if window:
        standing = both & (times >= window[0]) & (times <= window[1])
    else:   # no window given: frames whose height is within 2 cm of the standing level
        trace = result["height_m"][result["primary"]]
        level = result["reps"][result["primary"]]["standing_level_m"]
        standing = both & np.isfinite(trace) & (np.abs(trace - level) < 0.02)
    if standing.sum() < 5:
        raise ValueError("Too few standing frames with both hips reconstructed to place the movement planes")
    pelvis = squat.pelvis_track(xyz, valid)[standing]
    hip_line = xyz[standing, squat.RIGHT_HIP] - xyz[standing, squat.LEFT_HIP]   # left hip -> right hip
    return np.median(pelvis, axis=0), np.median(hip_line, axis=0), "multiview_standing"


def _match_reps(reference_reps, found):
    """Pair each reference rep with the nearest rep of another condition by bottom time (within 0.5 s)."""
    pairs = sorted(((abs(f["bottom_s"] - r["bottom_s"]), ri, fi) for ri, r in enumerate(reference_reps)
                    for fi, f in enumerate(found)), key=lambda p: p[0])
    taken_ref, taken_found, matched = set(), set(), {}
    for gap, ri, fi in pairs:
        if gap >= MATCH_WINDOW_S or ri in taken_ref or fi in taken_found:
            continue
        taken_ref.add(ri)
        taken_found.add(fi)
        matched[ri] = fi
    return matched, len(found) - len(taken_found)


def _measure_condition(times, xyz, valid, up, settings, reference_reps):
    """Same squat settings as the main result; reps are renumbered to match the all-cameras reps."""
    pelvis = squat.pelvis_track(xyz, valid)
    if settings["primary"] == "filtered":
        pelvis = squat.smooth(pelvis, settings["filter_frames"], times=times)
    trace = squat.height(pelvis, up)
    window = settings.get("standing_window_s")
    jitter = squat.jitter(times, pelvis, window, up) if window else {}
    standing = _standing_level(times, squat.height(squat.pelvis_track(xyz, valid), up), window)
    found, _ = squat.segment_reps(times, trace, standing=standing, min_depth_m=settings["min_rep_depth_m"],
                                  estimator=settings["estimator"])
    matched, extra = _match_reps(reference_reps, found) if reference_reps else ({}, 0)
    if reference_reps:
        reps = [{**found[fi], "rep": reference_reps[ri]["rep"]} for ri, fi in sorted(matched.items())]
    else:
        reps = [{**rep, "rep": index + 1} for index, rep in enumerate(found)]
    error, rule = None, None
    try:
        if not reference_reps:
            raise ValueError("No all-view reference reps; independent annotation scoring is required")
        reps, rule = squat.classify(reps, settings["reference_rep"], settings["tolerance_m"],
                                    settings["min_coverage"], settings["borderline_m"])
    except ValueError as problem:   # for example the reference rep was not seen in this condition
        error = str(problem)
    return {"reps": reps, "extra_reps": extra, "jitter": jitter, "rule": rule, "error": error}


def _sd(values):
    return float(np.std(values, ddof=1)) if len(values) >= 2 else None


def _mean(values):
    return float(np.mean(values)) if len(values) else None


def _pair_conditions(observations, cameras, syncs, config, frame_periods):
    """Every pair of cameras (only when there are three or more), triangulated on their own."""
    ids = [c["id"] for c in config["cameras"]]
    t = config["triangulation"]
    conditions = []
    if len(ids) >= 3:
        for pair in combinations(range(len(ids)), 2):
            first = pair[0]   # this camera's frame times form the timeline
            chosen = [observations[i] for i in pair]
            chosen_syncs = [{"offset_s": 0.0, "drift_rate": 0.0, "anchor_s": 0.0}] + \
                           [_sync_between(syncs[first], syncs[i]) for i in pair[1:]]
            label = "+".join(ids[i] for i in pair)
            try:
                seq = reconstruct_sequence(chosen, [cameras[i] for i in pair], chosen_syncs, t["min_confidence"],
                                           t["max_reprojection_px"], t["min_ray_angle_deg"],
                                           [frame_periods[i] for i in pair],
                                           joints=[squat.LEFT_HIP, squat.RIGHT_HIP])
                conditions.append({"name": f"two views ({label})", "cameras": [ids[i] for i in pair],
                                   "model": "triangulation", "times": flashsync.to_reference(seq["times_s"], syncs[first]),
                                   "xyz": seq["xyz"], "valid": seq["valid"],
                                   "assumption": f"Triangulates with only {label}; no assumption about where the person moves."})
            except Exception as error:
                conditions.append({"name": f"two views ({label})", "cameras": [ids[i] for i in pair],
                                   "model": "triangulation", "error": str(error),
                                   "assumption": f"Triangulates with only {label}; no assumption about where the person moves."})
    return conditions


ONE_VIEW_ASSUMPTION = {
    "fixed_distance": "Assumes the person stays the same distance from this camera and moves only up and down "
                      "in a plane facing it; a step towards or away from the camera makes the depth read too long or short.",
    "movement_plane": "Assumes the person moves only forwards, backwards, up and down in the vertical plane perpendicular to "
                      "the hip line through the standing spot; a sideways shift is misread.",
}
KIND_NAME = {"fixed_distance": "fixed distance", "movement_plane": "movement plane"}


def compare_views(observations, cameras, syncs, up, config, sequence, result, frame_periods=None, run=None,
                 annotations=None):
    """Measure the same recording with one camera, every pair of cameras, and all cameras together.

    observations/cameras/syncs: as for reconstruct_sequence (camera 0 is the reference clock).
    sequence/result: the all-cameras reconstruction and measurement (reused as the last condition).
    Returns the summary; when `run` is given, also writes views_comparison.csv, views_summary.json
    and views_depth.png into it.
    """
    settings = {**DEFAULTS["squat"], **config["squat"]}
    ids = [c["id"] for c in config["cameras"]]
    frame_periods = frame_periods or [float(np.median(np.diff(o["times_s"]))) for o in observations]
    primary = result["reps"][settings["primary"]]
    reference_reps = primary["reps"] if annotations is None else []
    if annotations is None and (not reference_reps or not primary["classification"]):
        raise ValueError("The all-cameras measurement has no classified reps to compare against")

    plane_error = None
    try:
        point, hip_line, plane_source = _standing_plane_inputs(config, sequence, result, up)
    except Exception as error:
        point, hip_line, plane_source, plane_error = None, None, "unavailable", str(error)
    borrowed = (" The plane was set from the multi-view standing position, so this condition borrows set-up "
                "information from the other cameras." if plane_source == "multiview_standing" else "")
    conditions = []
    for index, camera_id in enumerate(ids):
        centre = oneview.camera_centre(cameras[index])
        obs = observations[index]
        times = flashsync.to_reference(obs["times_s"], syncs[index])   # own frames, on the reference timeline
        for kind in ("fixed_distance", "movement_plane"):
            try:
                if plane_error:
                    raise ValueError(plane_error)
                plane_point, normal = oneview.movement_plane(kind, point, up, centre, hip_line)
                xyz, valid = oneview.reconstruct_one_view(obs["keypoints"], obs["scores"], cameras[index], plane_point,
                                                          normal, config["triangulation"]["min_confidence"])
                conditions.append({"name": f"one view, {KIND_NAME[kind]} ({camera_id})", "cameras": [camera_id],
                                   "model": kind, "times": times, "xyz": xyz, "valid": valid,
                                   "assumption": ONE_VIEW_ASSUMPTION[kind] + borrowed})
            except Exception as error:
                conditions.append({"name": f"one view, {KIND_NAME[kind]} ({camera_id})", "cameras": [camera_id],
                                   "model": kind, "error": str(error),
                                   "assumption": ONE_VIEW_ASSUMPTION[kind] + borrowed})
    conditions += _pair_conditions(observations, cameras, syncs, config, frame_periods)

    rows, summary, experiment_rows, experiment_conditions = [], {}, [], {}
    everything = [{"name": "all views (" + "+".join(ids) + ")", "cameras": ids, "model": "triangulation",
                   "assumption": "Triangulates with every camera (the main result): no assumption about where the person moves."}]
    for cond in conditions + everything:
        try:
            if cond.get("error"):
                raise ValueError(cond["error"])
            if "xyz" in cond:
                measured = _measure_condition(cond["times"], cond["xyz"], cond["valid"], up,
                                              settings, reference_reps)
            elif annotations is not None:
                measured = _measure_condition(sequence["times_s"], sequence["xyz"], sequence["valid"], up,
                                              settings, reference_reps)
            else:   # all cameras: the main result itself
                measured = {"reps": reference_reps, "extra_reps": 0, "rule": primary["classification"], "error": None,
                            "jitter": result["jitter"].get(settings["primary"]) or {}}
            condition_error = None
        except Exception as error:
            condition_error = str(error)
            measured = {"reps": [], "extra_reps": 0, "rule": None, "error": condition_error, "jitter": {}}
        by_rep = {r["rep"]: r for r in measured["reps"]}
        diffs_depth, diffs_reference = [], []
        for ref in reference_reps:
            rep = by_rep.get(ref["rep"])
            row = {"condition": cond["name"], "cameras": "+".join(cond["cameras"]), "model": cond["model"],
                   "rep": ref["rep"]}
            if rep is None:
                row["outcome"] = "not_found"
            else:
                gap = rep["depth_m"] - ref["depth_m"]
                accepted = (not ref.get("is_reference") and rep.get("outcome") in ("reached_reference", "shallower")
                            and ref.get("outcome") in ("reached_reference", "shallower"))
                if accepted:
                    diffs_depth.append(gap)
                reference_gap = rep.get("difference_from_reference_m")
                if accepted and reference_gap is not None:
                    diffs_reference.append(reference_gap - ref["difference_from_reference_m"])
                row.update(depth_m=rep["depth_m"], depth_se_m=rep.get("depth_se_m"),
                           difference_from_reference_m=reference_gap, difference_se_m=rep.get("difference_se_m"),
                           outcome=rep.get("outcome", "not_classified"), bottom_model=rep.get("bottom_model"),
                           coverage=rep["coverage"], depth_minus_all_views_m=gap)
            rows.append(row)
        jitter = measured["jitter"]
        summary[cond["name"]] = {
            "cameras": cond["cameras"], "model": cond["model"], "assumes": cond["assumption"],
            "plane_source": plane_source if cond["model"] in ("fixed_distance", "movement_plane") else None,
            "reps_found": len(by_rep), "reps_expected": len(reference_reps), "extra_reps_not_matched": measured["extra_reps"],
            "unclear": sum(r.get("outcome") == "unclear" for r in measured["reps"]),
            "standing_jitter_m": {"total_sd": jitter.get("vertical_sd_m"), "fast_sd": jitter.get("vertical_fast_sd_m"),
                                  "slow_sd": jitter.get("vertical_slow_sd_m")},
            "depth_minus_all_views_m": {"mean": _mean(diffs_depth), "sd": _sd(diffs_depth), "n": len(diffs_depth)},
            "difference_from_reference_minus_all_views_m": {"mean": _mean(diffs_reference), "sd": _sd(diffs_reference),
                                                            "n": len(diffs_reference)},
            "classification_error": measured["error"]}
        if annotations is not None:
            policy = (config["experiment"]["match_window_s"], config["experiment"]["tolerance_m"],
                      config["experiment"]["borderline_m"], config["squat"]["min_coverage"])
            if condition_error:
                # The condition could not be measured: record it as failed, not as every squat missed.
                scored = experiment.score_failed_condition(annotations, condition_error, *policy)
            else:
                scored = experiment.score_condition(annotations, measured["reps"], *policy)
            experiment_conditions[cond["name"]] = {"cameras": cond["cameras"], "model": cond["model"],
                                                     "status": "failed" if condition_error else "scored",
                                                     "plane_source": summary[cond["name"]]["plane_source"],
                                                     "assumes": cond["assumption"],
                                                     "error": condition_error,
                                                     **scored["summary"]}
            experiment_rows.extend({"condition": cond["name"], "cameras": "+".join(cond["cameras"]),
                                    "model": cond["model"], **row} for row in scored["rows"])
    info = {"plane_source": plane_source, "standing_point_m": point, "hip_line": hip_line,
            "reference_rep": settings["reference_rep"], "trace": settings["primary"],
            "conditions": summary, "rows": rows,
            "note": ("The one-camera setup could not be placed: " + plane_error) if plane_error else
                     ("With multiview_standing the one-camera conditions borrow the standing spot and hip line from "
                     "the multi-view result, so they are not fully independent of the other cameras. Give "
                     "views.standing_point_m and views.hip_line (measured on the floor) to avoid that.")
            if plane_source == "multiview_standing" else "Planes were set from measured values in the config."}
    if annotations is not None:
        reference_id = next(a["annotation_id"] for a in annotations if a["role"] == "reference")
        info["reference_source"] = {"kind": "independent_same_take_annotation", "annotation_id": reference_id,
                                    "file": config["experiment"]["annotations"], "take": config.get("take")}
        info["experiment"] = {"annotations_file": config["experiment"]["annotations"],
                               "reference_source": info["reference_source"],
                               "conditions": experiment_conditions, "rows": experiment_rows,
                               "note": "All conditions use the same independent timed annotations; the detected reference repetition anchors each condition's own classifications."}
    if annotations is not None:
        numbers = {a["annotation_id"]: i for i, a in enumerate(annotations, 1)}
        info["annotation_ids"] = list(numbers)
        info["reference_rep"] = reference_id
        info["rows"] = [{**row, "rep": numbers.get(row["annotation_id"]),
                         "outcome": row.get("model_outcome") or row["status"]} for row in experiment_rows]
        for name, condition in info["conditions"].items():
            scored = experiment_conditions[name]
            condition.update(reps_expected=len(annotations), extra_reps_not_matched=scored["counts"]["extra"],
                             unclear=scored["counts"]["model_unclear"], classification_error=scored["error"],
                             reference_annotation_id=info["reference_rep"],
                             continuous_depth_error_m=scored["continuous_depth_error_m"],
                             counts=scored["counts"])
    else:
        info["reference_source"] = {"kind": "legacy_detection_index", "rep": settings["reference_rep"],
                                    "take": config.get("take")}
    if run is not None:
        _write_views(Path(run), info)
    return info


def _csv_value(value):
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return ""
    return value


def _write_views(run, info):
    with (run / "views_comparison.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = list(VIEW_COLUMNS)
        if info.get("annotation_ids"):
            fields += sorted({k for row in info["rows"] for k in row} - set(fields))
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in info["rows"]:
            writer.writerow({k: _csv_value(v) for k, v in row.items()})
    write_json(run / "views_summary.json", {k: v for k, v in info.items() if k not in ("rows", "experiment")})
    if info.get("experiment"):
        experiment_info = info["experiment"]
        write_json(run / "views_experiment.json", {k: v for k, v in experiment_info.items() if k != "rows"})
        with (run / "views_experiment.csv").open("w", newline="", encoding="utf-8") as stream:
            fields = sorted({key for row in experiment_info["rows"] for key in row})
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in experiment_info["rows"]:
                writer.writerow({k: _csv_value(v) for k, v in row.items()})
    _plot_views(run / "views_depth.png", info)


def _plot_views(path, info):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = list(info["conditions"])
    figure, axis = plt.subplots(figsize=(12, 5), dpi=130)
    colors, markers = plt.get_cmap("tab10").colors, "osD^v<>PXh"
    width = 0.8 / max(len(names), 1)
    for k, name in enumerate(names):
        rows = [r for r in info["rows"] if r["condition"] == name and r.get("depth_m") is not None and r.get("rep") is not None]
        x = np.array([r["rep"] for r in rows], float) - 0.4 + width * (k + 0.5)
        depth = np.array([r["depth_m"] for r in rows]) * 100
        error = np.array([r["depth_se_m"] if r.get("depth_se_m") is not None else np.nan for r in rows]) * 100
        colour = colors[k % len(colors)]
        axis.plot(x, depth, markers[k % len(markers)], color=colour, ms=5, label=name)
        known = np.isfinite(error)
        if known.any():
            axis.errorbar(x[known], depth[known], yerr=error[known], fmt="none", ecolor=colour, capsize=2)

    if "annotation_ids" in info:
        axis.set_xticks(np.arange(1, len(info["annotation_ids"])+1), info["annotation_ids"], rotation=25)
        axis.set_xlabel("Independent attempt ID (empty slot = no detected depth)")
    else:
        axis.set_xlabel("Repetition in all-camera reconstruction (legacy diagnostic)")

    axis.set_ylabel("depth (cm)")
    axis.set_title(f"Squat depth by number of views (bars show known standard errors only; planes: {info['plane_source']})")
    axis.legend(fontsize=7, ncol=2)
    axis.grid(alpha=0.3)
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)


def _run_views_comparison(run, config, observations, cameras, syncs, up, sequence, result, metadata, report, progress, annotations=None):
    """Run the comparison without ever losing the main result; record any error in the report."""
    try:
        periods = [1 / m["median_fps"] * config["pose"]["stride"] for m in metadata]
        info = compare_views(observations, cameras, syncs, up, config, sequence, result, periods, run=run,
                             annotations=annotations)
        report["views"] = {"status": "done", "plane_source": info["plane_source"],
                           "files": ["views_comparison.csv", "views_summary.json", "views_depth.png"]
                                    + (["views_experiment.csv", "views_experiment.json"] if annotations else []),
                           "conditions": {name: {"reps_found": c["reps_found"], "unclear": c["unclear"],
                                                 "mean_depth_minus_all_views_m": c["depth_minus_all_views_m"]["mean"],
                                                 "sd_depth_minus_all_views_m": c["depth_minus_all_views_m"]["sd"]}
                                          for name, c in info["conditions"].items()},
                           **({"experiment": {name: c for name, c in info["experiment"]["conditions"].items()}}
                              if annotations else {})}
    except Exception as error:
        progress(f"Views comparison failed (main result kept): {error}")
        (run / "views_error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        report["views"] = {"status": "failed", "error": str(error)}
    write_json(run / "report.json", report)


# --------------------------------------------------------------------------- I/O
def _cameras(config, paths, metadata):
    records = []
    for camera, info in zip(config["cameras"], metadata):
        if not camera.get("calibration"):
            raise ValueError(f"{camera['id']}: no calibration file in the session config")
        records.append(load_camera_calibration(paths.calibration_file(camera["calibration"]),
                                               camera["id"], info["image_size"]))
    frames_ids = {r["board_frame_id"] for r in records}
    if len(frames_ids) != 1:
        raise ValueError("Cameras were calibrated against different board frames")
    ups = [tuple(r.get("up_axis_board") or ()) for r in records]
    if not ups[0] or len(set(ups)) != 1:
        raise ValueError("Calibrations must agree on the vertical (up_axis_board); recalibrate extrinsics")
    return records, list(ups[0])


def _sync(config, video_paths, metadata, run):
    settings = config["sync"]
    if settings["method"] == "manual":
        syncs = [{"status": "reference", "offset_s": 0.0, "drift_rate": 0.0, "anchor_s": 0.0}]
        for camera in config["cameras"][1:]:
            syncs.append({"status": "manual", "offset_s": float(settings["offsets_s"][camera["id"]]),
                          "drift_rate": 0.0, "anchor_s": 0.0,
                          "mapping": "reference_time = other_time + offset_s"})
        record = {"method": "manual", "alignments": syncs}
    elif settings["method"] == "flash":
        rois = [settings["roi"].get(c["id"]) for c in config["cameras"]]
        record = flashsync.synchronize(video_paths, settings["start_window_s"], settings["end_window_s"], rois,
                                       [settings.get("exposures", {}).get(c["id"]) for c in config["cameras"]])
        syncs = record["alignments"]
        _plot_sync(record, [c["id"] for c in config["cameras"]], run / "sync" / "brightness.png")
    else:
        raise ValueError("sync.method must be 'flash' or 'manual'")
    write_json(run / "sync" / "sync.json", record)
    failed = [a for a in syncs if a["status"] == "failed"]
    if failed:
        raise RuntimeError("Synchronization failed: " + "; ".join(a.get("reason", "") for a in failed))
    scoring_pilot = bool(config.get("experiment", {}).get("annotations"))
    if (settings.get("require_end") or scoring_pilot) and not all(a.get("drift_checked") for a in syncs[1:]):
        raise ValueError("The speed comparison requires one usable start and end flash per camera; inspect sync.json")
    return syncs


def _detect(config, video_paths, metadata, run, keypoints_from=None, progress=print):
    observations = []
    detector = None
    if config["pose"].get("device_source") == "default":
        progress(f"pose.device is not set in the config: using the default '{config['pose']['device']}'")
    for camera, path, info in zip(config["cameras"], video_paths, metadata):
        target = run / "keypoints2d" / f"{camera['id']}.npz"
        identity = pose2d.cache_identity(camera["id"], info["sha256"], info, config["pose"])
        if keypoints_from:
            source = Path(keypoints_from) / "keypoints2d" / f"{camera['id']}.npz"
            observation = pose2d.verified_cache(source, identity, info)
            observation["reused_from"] = str(source)
        else:
            if identity["detector"] != pose2d.RTMLibDetector.name:
                raise ValueError("Live detection requires the RTMLib detector")
            if detector is None:
                p = config["pose"]
                detector = pose2d.RTMLibDetector(p["mode"], p["device"], p["backend"], p["det_frequency"])
            detector.model.reset()  # tracking state belongs to one camera only
            total = info["frame_count"]

            def report(index, stamp, cam=camera["id"]):
                if index % 120 == 0:
                    progress(f"  {cam}: frame {index}/{total}")
            observation = pose2d.detect_video(path, info, detector, stride=config["pose"]["stride"], progress=report,
                                               edge_margin_fraction=identity["edge_margin_fraction"])
            weights = observation["detector_settings"]["weights"]
            if any(weights[key]["sha256"] != value for key, value in identity["expected_weight_sha256"].items()):
                raise ValueError("Detector weights differ from the expected hashes for the requested pose settings")
            observation["source_identity"] = identity
            # Say whether the device came from the config or from the default.
            observation["detector_settings"] = {**observation["detector_settings"],
                                                "device_source": config["pose"].get("device_source")}
        pose2d.save(target, observation)
        observations.append(observation)
    return observations


def run_session(config_path, paths, output_root=None, keypoints_from=None, progress=print, annotations_override=None):
    run = allocate_run(output_root or paths.outputs)
    config_path = Path(config_path).expanduser().resolve()
    try:
        config_digest = sha256(config_path) if config_path.is_file() else None
    except OSError:
        config_digest = None
    manifest = {"schema_version": 1, "run_id": run.name, "created_utc": utc_now(), "status": "running",
                "mode": "two_camera_squat", "accuracy_validated": False,
                "config_attempt": {"path": str(config_path),
                                   "sha256": config_digest},
                "python": sys.version, "platform": platform.platform(), "inputs": [],
                "source_sha256": {p.name: sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))}}
    write_json(run / "manifest.json", manifest)
    config = None
    annotations = None
    try:
        config = load_session(config_path)
        if annotations_override is not None:
            config["experiment"]["annotations"] = str(Path(annotations_override).expanduser().resolve())
        manifest["config"] = config
        manifest["annotations_attempt"] = config["experiment"]["annotations"]
        write_json(run / "manifest.json", manifest)
        annotation_path = config["experiment"]["annotations"]
        if annotation_path:
            annotations = experiment.load_annotations(annotation_path)
            experiment.check_match_window(annotations, config["experiment"]["match_window_s"])
            manifest["annotation_sha256"] = sha256(annotation_path)
        video_paths = [paths.video(c["video"]) for c in config["cameras"]]
        metadata = []
        for camera, path in zip(config["cameras"], video_paths):
            progress(f"Reading {camera['id']}: {path}")
            info = probe(path)
            info["sha256"] = sha256(path)
            metadata.append(info)
            manifest["inputs"].append({"camera": camera["id"], "path": str(path), "sha256": info["sha256"],
                                       "image_size": info["image_size"], "median_fps": info["median_fps"],
                                       "frame_count": info["frame_count"]})
        write_json(run / "manifest.json", manifest)
        cameras, up = _cameras(config, paths, metadata)
        progress("Synchronizing")
        syncs = _sync(config, video_paths, metadata, run)
        progress("Detecting 2D keypoints" + (" (reusing earlier run)" if keypoints_from else ""))
        observations = _detect(config, video_paths, metadata, run, keypoints_from, progress)
        progress("Triangulating")
        t = config["triangulation"]
        sequence = reconstruct_sequence(observations, cameras, syncs, t["min_confidence"],
                                        t["max_reprojection_px"], t["min_ray_angle_deg"],
                                        [1 / m["median_fps"] * config["pose"]["stride"] for m in metadata])
        np.savez_compressed(run / "points3d.npz", times_s=sequence["times_s"], xyz=sequence["xyz"],
                            valid=sequence["valid"], reprojection_px=sequence["reprojection_px"],
                            joint_names=np.array(JOINT_NAMES))
        progress("Measuring squat depth")
        result = measure_squats(sequence["times_s"], sequence["xyz"], sequence["valid"], up, config["squat"],
                                annotations, config["experiment"])
        # Keep legacy labels for audit, but never score them against automatic
        # rep numbers: dropped/extra detections make that comparison ambiguous.
        labels = _labels(config)
        report = _report(run, config, metadata, syncs, sequence, result, labels, up, observations)
        if annotations is not None:
            primary = result["reps"][result["primary"]]
            name = "all views (" + "+".join(c["id"] for c in config["cameras"]) + ")"
            report["experiment"] = {name: {"model": "triangulation",
                                          "status": primary["agreement"]["reference_status"],
                                          "cameras": [c["id"] for c in config["cameras"]],
                                          **primary["agreement"]}}
            report["scoring"] = {"source": "independent_timed_annotations",
                                 "annotations_file": config["experiment"]["annotations"],
                                 "annotations_sha256": manifest["annotation_sha256"],
                                 "primary_condition": name, "legacy_rep_number_labels_used": False,
                                 "decision_settings": _annotated_decision_settings(config)}
            if report["scoring"]["decision_settings"]["warning"]:
                progress("Warning: " + report["scoring"]["decision_settings"]["warning"])
        _write_tables(run, sequence, result)
        _plot_trace(run / "depth_trace.png", sequence["times_s"], result, config)
        if config["views"]["compare"]:
            progress("Comparing numbers of camera views")
            _run_views_comparison(run, config, observations, cameras, syncs, up, sequence, result, metadata,
                                  report, progress, annotations)
        write_json(run / "report.json", report)
        manifest.update(status=report["status"], completed_utc=utc_now())
        write_json(run / "manifest.json", manifest)
        progress(f"Saved {run}: {report['status']}")
        return run, report
    except Exception as error:
        manifest.update(status="failed", completed_utc=utc_now(), error=str(error))
        write_json(run / "manifest.json", manifest)
        trace = traceback.format_exc()
        (run / "error.txt").write_text(trace, encoding="utf-8")
        if (run / "report.json").exists():
            try:
                report = json.loads((run / "report.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                report = {"run_id": run.name, "accuracy_validated": False}
            report.update(status="failed", pipeline_failure=str(error), traceback_file="error.txt")
        else:
            report = {"run_id": run.name, "status": "failed", "accuracy_validated": False,
                      "stage": ("configuration" if config is None or isinstance(error, experiment.AnnotationConfigError)
                                else "analysis"),
                      "error": str(error), "traceback_file": "error.txt",
                      "config_path": str(config_path), "config_sha256": manifest["config_attempt"]["sha256"]}
            report["reference_source"] = {"kind": "unavailable", "reason": "failed before resolving reference"}
            if config is not None and not config["experiment"]["annotations"]:
                report["reference_source"] = {"kind": "legacy_detection_index", "take": config.get("take"),
                                              "rep": config["squat"]["reference_rep"]}
            annotation_path = Path(annotations_override).expanduser() if annotations_override is not None else None
            if annotation_path is None:
                try:
                    raw_config = json.loads(config_path.read_text(encoding="utf-8-sig"))
                    section = raw_config.get("experiment") if isinstance(raw_config, dict) else None
                    annotation_value = section.get("annotations") if isinstance(section, dict) else None
                    if isinstance(annotation_value, str) and annotation_value:
                        annotation_path = Path(annotation_value).expanduser()
                        if not annotation_path.is_absolute():
                            annotation_path = config_path.parent / annotation_path
                except (OSError, ValueError, TypeError):
                    annotation_path = None
            if annotation_path is not None:
                attempt = {"path": str(annotation_path.resolve()),
                           "sha256": sha256(annotation_path) if annotation_path.is_file() else None,
                           "status": "unavailable"}
                try:
                    roster = annotations or experiment.load_annotations(annotation_path)
                    ref = next(a for a in roster if a["role"] == "reference")
                    report["reference_source"] = {"kind": "independent_same_take_annotation",
                                                  "annotation_id": ref["annotation_id"], "file": str(annotation_path),
                                                  "take": config.get("take") if config else None}
                    attempt["annotated_tests"] = len(roster) - 1
                    attempt["status"] = "available_but_unscorable_run_failed_before_result"
                    report["experiment_attempt"] = {**attempt, "records": [
                        {"annotation_id": item["annotation_id"], "role": item["role"], "label": item["label"],
                         "bottom_s": item["bottom_s"], "status": "unscorable_run_failed_before_result"}
                        for item in roster]}
                except (OSError, ValueError) as annotation_error:
                    attempt["error"] = str(annotation_error)
                    report["experiment_attempt"] = attempt
        write_json(run / "report.json", report)
        raise


def _annotated_decision_settings(config):
    """The tolerances that scored an annotated run, and any squat.* values that were ignored.

    With annotations the experiment section decides; squat.tolerance_m and squat.borderline_m
    belong to the older rep-number path and are not used.
    """
    used = {key: config["experiment"][key] for key in ("tolerance_m", "borderline_m")}
    ignored = {f"squat.{key}": config["squat"][key] for key in used if config["squat"][key] != used[key]}
    warning = None
    if ignored:
        warning = (f"Annotated scoring used experiment.tolerance_m={used['tolerance_m']:g} and "
                   f"experiment.borderline_m={used['borderline_m']:g}; ignored "
                   + ", ".join(f"{name}={value:g}" for name, value in ignored.items()) + ".")
    return {**used, "source": "experiment section", "squat_values_not_used": ignored, "warning": warning}


def _labels(config):
    source = config.get("labels")
    if not source:
        return None
    path = Path(source)
    if not path.is_absolute():
        path = Path(config["_path"]).parent / path
    labels = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            judged = row["judged_from_footage"].strip().lower()
            if judged not in ("match", "shallow", "unclear"):
                raise ValueError(f"Label for rep {row['rep']} must be match, shallow or unclear")
            labels[int(row["rep"])] = judged
    return {"path": str(path), "labels": labels}


def _report(run, config, metadata, syncs, sequence, result, labels, up, observations=None):
    valid = sequence["valid"]
    hips = valid[:, squat.LEFT_HIP] & valid[:, squat.RIGHT_HIP]
    primary = result["reps"][result["primary"]]
    report = {"run_id": run.name, "created_utc": utc_now(),
              "status": "measured" if primary["reps"] and primary["classification"] else "no_classified_reps",
              "accuracy_validated": False,
              "reference_source": ({"kind": "independent_same_take_annotation", "take": config.get("take"),
                                    "file": config["experiment"]["annotations"],
                                    "annotation_id": primary["agreement"]["reference_annotation_id"]}
                                   if "agreement" in primary else
                                   {"kind": "legacy_detection_index", "take": config.get("take"),
                                    "rep": config["squat"]["reference_rep"]}),
              "evidence_kind": config.get("evidence_kind") or
                               ("synthetic_projection" if any(obs.get("detector") == "synthetic projection"
                                                              for obs in observations or []) else "video_estimate"),
              "what_this_is": "Pelvis (hip-midpoint) height from calibrated, synchronized cameras. "
                              "Agreement with the footage and with a pelvis marker must be checked separately.",
              "session": {k: config.get(k) for k in ("session", "participant", "take", "pace")},
              "up_axis_board": up, "synchronization": syncs,
              "frames": {"reference_frames": int(len(sequence["times_s"])),
                         "pelvis_reconstructed_fraction": float(hips.mean()) if len(hips) else 0.0,
                         "joint_reason_counts": sequence["reason_counts"],
                         "hip_reprojection_px_median": _nanmedian(sequence["reprojection_px"][:, [11, 12]])},
              "recordings": [{"camera": c["id"], "image_size": m["image_size"], "median_fps": m["median_fps"],
                              "duration_s": m["duration_s"], "frame_count": m["frame_count"]}
                             for c, m in zip(config["cameras"], metadata)],
              "observations": [{"camera": camera["id"],
                                "kind": observation.get("detector") or observation.get("source") or "unknown",
                                "reused_from": observation.get("reused_from")}
                               for camera, observation in zip(config["cameras"], observations or [])],
              "jitter_standing": result["jitter"], "primary_trace": result["primary"],
              "squat_estimator": result["settings"]["estimator"],
              "reps": {name: {k: v for k, v in entry.items()} for name, entry in result["reps"].items()},
              "filter_effect": result["filter_effect"]}
    if labels:
        report["comparison_with_footage"] = {
            "labels_file": labels["path"], "status": "not_scored_requires_independent_timestamps",
            "reason": ("Rep-number matching can hide missed or extra detections. Add timed independent "
                       "annotations in experiment.annotations to score each camera condition."),
            "labels": [{"rep": rep, "judged_from_footage": judged}
                       for rep, judged in sorted(labels["labels"].items())]}
    write_json(run / "report.json", report)
    return report


def _nanmedian(values):
    values = np.asarray(values, float)
    return float(np.nanmedian(values)) if np.isfinite(values).any() else None


def _write_tables(run, sequence, result):
    with (run / "pelvis_trace.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time_s", "height_raw_m", "height_filtered_m", "left_hip_reprojection_px",
                         "right_hip_reprojection_px"])
        for i, t in enumerate(sequence["times_s"]):
            writer.writerow([f"{t:.5f}"] + [("" if not np.isfinite(v) else f"{v:.5f}") for v in
                            (result["height_m"]["raw"][i], result["height_m"]["filtered"][i],
                             sequence["reprojection_px"][i, 11], sequence["reprojection_px"][i, 12])])
    columns = ["rep", "annotation_id", "quality_status", "outcome", "borderline", "is_reference", "depth_m", "difference_from_reference_m",
               "descent_s", "coverage", "start_s", "bottom_s", "end_s", "standing_m", "bottom_m",
               "depth_se_m", "difference_se_m", "bottom_samples", "estimator", "bottom_model", "split_by_gap"]
    for name, entry in result["reps"].items():
        with (run / f"reps_{name}.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for rep in entry["reps"]:
                writer.writerow({k: _csv_value(v) for k, v in rep.items()})


OUTCOME_COLORS = {"reached_reference": "#2e7d32", "shallower": "#c62828", "unclear": "#9e9e9e", None: "#1565c0"}


def _plot_trace(path, times, result, config):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure, axis = plt.subplots(figsize=(12, 4.5), dpi=130)
    axis.plot(times, result["height_m"]["raw"], color="#90a4ae", lw=1, label="raw")
    axis.plot(times, result["height_m"]["filtered"], color="#263238", lw=1.6,
              label=f"filtered ({result['settings']['filter_frames']} frames)")
    primary = result["reps"][result["primary"]]
    rule = primary["classification"]
    if rule:
        axis.axhline(primary["standing_level_m"] - rule["pass_line_m"], color="#6a1b9a", ls="--", lw=1,
                     label=f"reference depth - {rule['tolerance_m'] * 100:.0f} cm")
    for rep in primary["reps"]:
        color = OUTCOME_COLORS[rep.get("outcome")]
        axis.axvspan(rep["start_s"], rep["end_s"], color=color, alpha=0.12)
        axis.text(rep["bottom_s"], 0.97, f"{rep.get('annotation_id') or rep['rep']}\n{rep['depth_m'] * 100:.1f} cm",
                  transform=axis.get_xaxis_transform(), ha="center", va="top", fontsize=8, color=color)
    window = result["settings"].get("standing_window_s")
    if window:
        axis.axvspan(*window, color="#ffb300", alpha=0.15, label="standing still (jitter)")
    axis.set_xlabel("time on reference camera (s)")
    axis.set_ylabel("pelvis height along vertical (m)")
    title = config.get("session") or "session"
    axis.set_title(f"{title}: pelvis height, reps shaded by outcome ({result['primary']} trace)")
    axis.legend(loc="upper right", fontsize=8)
    axis.grid(alpha=0.3)
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)


def _plot_sync(record, names, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(len(names), 1, figsize=(12, 2.4 * len(names)), dpi=110, sharex=False)
    for axis, name, camera in zip(np.atleast_1d(axes), names, record["cameras"]):
        axis.plot(camera["brightness"]["times_s"], camera["brightness"]["levels"], lw=0.8)
        for key, color in (("start", "#2e7d32"), ("end", "#c62828")):
            if camera.get(key):
                axis.axvline(camera[key]["onset_s"], color=color, ls="--")
        axis.set_ylabel(f"{name}\nmean grey")
    np.atleast_1d(axes)[-1].set_xlabel("camera's own time (s); dashed = pulses used")
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)


def extract_frames(config_path, paths, reference_time_s, out_dir, sync_json=None):
    """Save each camera's frame nearest a reference time (for marking points by hand)."""
    import cv2
    from .media import frames as iterate
    config = load_session(config_path)
    syncs = None
    if sync_json:
        syncs = json.loads(Path(sync_json).read_text())["alignments"]
    saved = []
    for index, camera in enumerate(config["cameras"]):
        path = paths.video(camera["video"])
        info = probe(path)
        target = reference_time_s if not syncs else float(flashsync.to_other([reference_time_s], syncs[index])[0])
        nearest = int(np.argmin(np.abs(info["pts"] - target)))
        for frame_index, stamp, frame in iterate(path, info):
            if frame_index == nearest:
                out = Path(out_dir) / f"{camera['id']}_t{reference_time_s:.3f}.png"
                out.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(out), frame)
                saved.append({"camera": camera["id"], "file": str(out), "camera_time_s": stamp,
                              "requested_camera_time_s": target})
                break
    return saved
