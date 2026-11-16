"""Two-camera squat pipeline: sync -> 2D keypoints -> triangulation -> pelvis depth.

Every stage writes its evidence into one numbered run folder (outputs/V1.1.N).
The pure functions here (reconstruct_sequence, measure_squats) take arrays so
they can be tested on synthetic cameras without video files.
"""
from __future__ import annotations

import csv
import json
import platform
import sys
import traceback
from pathlib import Path

import numpy as np

from . import flashsync, pose2d, squat
from .configuration import load_camera_calibration
from .geometry import triangulate_points
from .kinematics import JOINT_NAMES
from .media import probe
from .records import allocate_run, sha256, utc_now, write_json
from .sync import interpolate_observations

DEFAULTS = {
    "sync": {"method": "flash", "start_window_s": 10.0, "end_window_s": 10.0, "roi": {}},
    "pose": {"mode": "balanced", "device": "cuda", "backend": "onnxruntime", "stride": 1, "det_frequency": 5},
    "triangulation": {"min_confidence": 0.3, "max_reprojection_px": 10.0, "min_ray_angle_deg": 3.0},
    "squat": {"standing_window_s": None, "reference_rep": 1, "tolerance_m": 0.03, "filter_frames": 5,
              "min_rep_depth_m": 0.06, "min_coverage": 0.85, "borderline_m": 0.01, "primary": "raw",
              "estimator": "parabola"},
}


def load_session(path):
    path = Path(path)
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    cameras = config.get("cameras", [])
    if len(cameras) < 2:
        raise ValueError("A session needs at least two cameras")
    ids = [c.get("id") for c in cameras]
    if len(set(ids)) != len(ids) or not all(ids) or not all(c.get("video") for c in cameras):
        raise ValueError("Each camera needs a unique id and a video")
    for section, values in DEFAULTS.items():
        config[section] = {**values, **(config.get(section) or {})}
    if config["squat"]["primary"] not in ("raw", "filtered"):
        raise ValueError("squat.primary must be 'raw' or 'filtered'")
    if config["squat"]["estimator"] not in ("parabola", "extreme"):
        raise ValueError("squat.estimator must be 'parabola' or 'extreme'")
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


def measure_squats(times, xyz, valid, up, settings):
    settings = {**DEFAULTS["squat"], **settings}
    pelvis_raw = squat.pelvis_track(xyz, valid)
    pelvis_filtered = squat.smooth(pelvis_raw, settings["filter_frames"])
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
        if found:
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
        record = flashsync.synchronize(video_paths, settings["start_window_s"], settings["end_window_s"], rois)
        syncs = record["alignments"]
        _plot_sync(record, [c["id"] for c in config["cameras"]], run / "sync" / "brightness.png")
    else:
        raise ValueError("sync.method must be 'flash' or 'manual'")
    write_json(run / "sync" / "sync.json", record)
    failed = [a for a in syncs if a["status"] == "failed"]
    if failed:
        raise RuntimeError("Synchronization failed: " + "; ".join(a.get("reason", "") for a in failed))
    return syncs


def _detect(config, video_paths, metadata, run, keypoints_from=None, progress=print):
    observations = []
    detector = None
    for camera, path, info in zip(config["cameras"], video_paths, metadata):
        target = run / "keypoints2d" / f"{camera['id']}.npz"
        if keypoints_from:
            source = Path(keypoints_from) / "keypoints2d" / f"{camera['id']}.npz"
            observation = pose2d.load(source)
            observation["reused_from"] = str(source)
        else:
            if detector is None:
                p = config["pose"]
                detector = pose2d.RTMLibDetector(p["mode"], p["device"], p["backend"], p["det_frequency"])
            total = info["frame_count"]

            def report(index, stamp, cam=camera["id"]):
                if index % 120 == 0:
                    progress(f"  {cam}: frame {index}/{total}")
            observation = pose2d.detect_video(path, info, detector, stride=config["pose"]["stride"], progress=report)
        pose2d.save(target, observation)
        observations.append(observation)
    return observations


def run_session(config_path, paths, output_root=None, keypoints_from=None, progress=print):
    config = load_session(config_path)
    run = allocate_run(output_root or paths.outputs)
    manifest = {"schema_version": 1, "run_id": run.name, "created_utc": utc_now(), "status": "running",
                "mode": "two_camera_squat", "accuracy_validated": False, "config": config,
                "python": sys.version, "platform": platform.platform(), "inputs": [],
                "source_sha256": {p.name: sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))}}
    write_json(run / "manifest.json", manifest)
    try:
        video_paths = [paths.video(c["video"]) for c in config["cameras"]]
        metadata = []
        for camera, path in zip(config["cameras"], video_paths):
            progress(f"Reading {camera['id']}: {path}")
            info = probe(path)
            metadata.append(info)
            manifest["inputs"].append({"camera": camera["id"], "path": str(path), "sha256": sha256(path),
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
        result = measure_squats(sequence["times_s"], sequence["xyz"], sequence["valid"], up, config["squat"])
        labels = _labels(config)
        report = _report(run, config, metadata, syncs, sequence, result, labels, up)
        _write_tables(run, sequence, result)
        _plot_trace(run / "depth_trace.png", sequence["times_s"], result, config)
        manifest.update(status=report["status"], completed_utc=utc_now())
        write_json(run / "manifest.json", manifest)
        progress(f"Saved {run}: {report['status']}")
        return run, report
    except Exception as error:
        manifest.update(status="failed", completed_utc=utc_now(), error=str(error))
        write_json(run / "manifest.json", manifest)
        (run / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise


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


def _report(run, config, metadata, syncs, sequence, result, labels, up):
    valid = sequence["valid"]
    hips = valid[:, squat.LEFT_HIP] & valid[:, squat.RIGHT_HIP]
    primary = result["reps"][result["primary"]]
    report = {"run_id": run.name, "created_utc": utc_now(),
              "status": "measured" if primary["reps"] and primary["classification"] else "no_classified_reps",
              "accuracy_validated": False,
              "what_this_is": "Pelvis (hip-midpoint) height from two calibrated, synchronized phones. "
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
              "jitter_standing": result["jitter"], "primary_trace": result["primary"],
              "squat_estimator": result["settings"]["estimator"],
              "reps": {name: {k: v for k, v in entry.items()} for name, entry in result["reps"].items()},
              "filter_effect": result["filter_effect"]}
    if labels and primary["classification"]:
        counts, rows = squat.score_against_labels(primary["reps"], labels["labels"])
        report["comparison_with_footage"] = {"labels_file": labels["path"], "counts": counts, "rows": rows}
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
    columns = ["rep", "outcome", "borderline", "is_reference", "depth_m", "difference_from_reference_m",
               "descent_s", "coverage", "start_s", "bottom_s", "end_s", "standing_m", "bottom_m",
               "depth_se_m", "difference_se_m", "bottom_samples", "estimator", "bottom_model"]
    for name, entry in result["reps"].items():
        with (run / f"reps_{name}.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for rep in entry["reps"]:
                writer.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in rep.items()})


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
        axis.text(rep["bottom_s"], 0.97, f"rep {rep['rep']}\n{rep['depth_m'] * 100:.1f} cm",
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
