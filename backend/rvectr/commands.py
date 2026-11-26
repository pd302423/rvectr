"""Command-line steps of the two-camera pipeline. See docs/TWO_CAMERA_PIPELINE.md."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .paths import RuntimePaths
from .records import write_json


def _board_args(parser):
    parser.add_argument("--squares", default="8x11", help="printed squares on the board, e.g. 8x11")
    parser.add_argument("--square-mm", type=float, required=True,
                        help="MEASURED side of one printed square in millimetres (measure 4 squares, divide by 4)")


def _print(result):
    print(json.dumps({k: v for k, v in result.items() if k not in ("quality",)}, indent=2, default=str)[:4000])


def calibrate_intrinsics(argv):
    from .board import intrinsics_from_video
    parser = argparse.ArgumentParser(prog="rvectr calibrate-intrinsics",
                                     description="Lens calibration from a video of the board moved and tilted around one phone's frame")
    parser.add_argument("--camera-id", required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=6, help="check every Nth frame")
    parser.add_argument("--max-views", type=int, default=30)
    _board_args(parser)
    args = parser.parse_args(argv)
    result = intrinsics_from_video(args.video, args.squares, args.square_mm, args.camera_id, args.stride,
                                   args.max_views, progress=lambda i, t, n: print(f"  t={t:7.2f}s  views={n}")
                                   if n % 10 == 0 else None)
    write_json(args.out, result)
    print(f"{result['status'].upper()}: {args.out}")
    q = result.get("quality", {})
    for key in ("detected_views", "view_count", "training_rms_px", "heldout_rms_px", "board_normal_spread_deg"):
        if key in q:
            print(f"  {key}: {q[key]}")
    if result["status"] != "passed":
        print(f"  reason: {result.get('reason')}")
    return 0 if result["status"] == "passed" else 1


def calibrate_extrinsics(argv):
    from .board import extrinsics_from_video
    parser = argparse.ArgumentParser(prog="rvectr calibrate-extrinsics",
                                     description="Camera position from the shared board held still in front of all cameras")
    parser.add_argument("--intrinsics", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--start", type=float, required=True, help="seconds into THIS video where the board is still")
    parser.add_argument("--end", type=float, required=True)
    parser.add_argument("--board-frame-id", required=True,
                        help="same label for every camera of this setup, e.g. 2026-11-16_setupA")
    parser.add_argument("--placement", choices=("upright", "floor"), default="upright",
                        help="upright = board standing and levelled; floor = lying flat")
    parser.add_argument("--same-recording-mode", action="store_true",
                        help="confirm the exercise videos use the same phone, lens, resolution, orientation and stabilization")
    parser.add_argument("--out", type=Path, required=True)
    _board_args(parser)
    args = parser.parse_args(argv)
    intrinsics = json.loads(args.intrinsics.read_text())
    result = extrinsics_from_video(args.video, intrinsics, args.squares, args.square_mm, args.board_frame_id,
                                   args.start, args.end, args.placement,
                                   recording_mode_verified=args.same_recording_mode, overlay_path=args.out.with_suffix(".corners.png"))
    write_json(args.out, result)
    print(f"{result['status'].upper()}: {args.out}")
    q = result.get("quality", {})
    for key in ("frames_with_board", "max_corner_motion_px", "rms_px", "max_px"):
        if key in q:
            print(f"  {key}: {q[key]}")
    if result["status"] == "passed":
        print(f"  up axis in board frame: {result['up_axis_board']}")
        if not result["recording_mode_verified"]:
            print("  NOTE: add --same-recording-mode once you have checked the settings; runs refuse it otherwise")
    else:
        print(f"  reason: {result.get('reason')}")
    return 0 if result["status"] == "passed" else 1


def sync(argv):
    from .flashsync import synchronize
    from .pipeline import _plot_sync, load_session
    parser = argparse.ArgumentParser(prog="rvectr sync", description="Check light-pulse sync without running pose detection")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("sync_check"))
    args = parser.parse_args(argv)
    config = load_session(args.config)
    paths = RuntimePaths.discover()
    videos = [paths.video(c["video"]) for c in config["cameras"]]
    s = config["sync"]
    record = synchronize(videos, s["start_window_s"], s["end_window_s"], [s["roi"].get(c["id"]) for c in config["cameras"]],
                         [s.get("exposures", {}).get(c["id"]) for c in config["cameras"]])
    write_json(args.out / "sync.json", record)
    _plot_sync(record, [c["id"] for c in config["cameras"]], args.out / "brightness.png")
    for camera, cam, align in zip(config["cameras"], record["cameras"], record["alignments"]):
        found = {k: (round(cam[k]["onset_s"], 4) if cam.get(k) else None) for k in ("start", "end")}
        print(f"{camera['id']}: pulses at {found}; {len(cam['events'])} brightness jumps in total")
        if align["status"] not in ("reference",):
            print(f"  {align['status']}: offset {align.get('offset_s')} s, drift {align.get('drift_s')} s"
                  + (f"  ({align.get('reason') or align.get('warning')})" if align.get('reason') or align.get('warning') else ""))
            if align.get("start_sampling_uncertainty_s") is not None:
                print(f"  start sampling uncertainty ±{1000 * align['start_sampling_uncertainty_s']:.1f} ms")
    print(f"Plot: {args.out / 'brightness.png'}")
    require_end = s.get("require_end") or bool(config.get("experiment", {}).get("annotations"))
    return 0 if all(a["status"] != "failed" and (not require_end or a.get("drift_checked"))
                    for a in record["alignments"][1:]) else 1


def run(argv):
    from .pipeline import run_session
    parser = argparse.ArgumentParser(prog="rvectr run", description=(
        "Measure squat depth, compare every camera subset, and optionally score every condition against "
        "the independent timed annotations in config.experiment.annotations. Use one reference rep in the same take."))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--keypoints-from", type=Path, help="earlier run folder whose 2D keypoints to reuse")
    parser.add_argument("--annotations", type=Path,
                        help="independent timed annotation CSV; overrides experiment.annotations in the config")
    args = parser.parse_args(argv)
    run_dir, report = run_session(args.config, RuntimePaths.discover(), args.output_root, args.keypoints_from,
                                  annotations_override=args.annotations)
    primary = report["reps"][report["primary_trace"]]
    print(f"\nPelvis reconstructed in {report['frames']['pelvis_reconstructed_fraction']:.0%} of frames")
    jitter = report["jitter_standing"].get(report["primary_trace"]) if report["jitter_standing"] else None
    if jitter and jitter.get("status") == "measured":
        print(f"Standing jitter ({report['primary_trace']}): RMS {jitter['rms_m'] * 1000:.1f} mm, p95 {jitter['p95_m'] * 1000:.1f} mm")
    if primary.get("error"):
        print(f"Classification: {primary['error']}")
    experiment = report.get("views", {}).get("experiment") or report.get("experiment")
    independent = bool(experiment) or report.get("scoring", {}).get("source") == "independent_timed_annotations"
    for rep in primary["reps"]:
        status = "" if independent else (f"  {rep.get('outcome', '-')}{' (borderline)' if rep.get('borderline') else ''}"
                                          f"{'  <- reference' if rep.get('is_reference') else ''}")
        print(f"  rep {rep['rep']:2d}: depth {rep['depth_m'] * 100:5.1f} cm  descent {rep['descent_s']:.2f} s{status}")
    if "comparison_with_footage" in report and not independent:
        print("Footage labels retained, not scored:", report["comparison_with_footage"]["reason"])
    if experiment:
        print("\nIndependent annotation score (reference excluded; same timed list for each condition):")
        for name, entry in experiment.items():
            counts = entry.get("counts", {})
            classification = entry.get("classification", {})
            accuracy = classification.get("accuracy")
            accuracy_text = "unknown" if accuracy is None else f"{accuracy:.1%}"
            end_to_end = classification.get("end_to_end_accuracy")
            end_to_end_text = "unknown" if end_to_end is None else f"{end_to_end:.1%}"
            print(f"  {name}: {entry.get('status')}  accuracy {accuracy_text} "
                  f"({counts.get('correct', 0)}/{classification.get('denominator', 0)}); "
                  f"end-to-end {end_to_end_text} "
                  f"({counts.get('correct', 0)}/{classification.get('all_eligible_tests_denominator', 0)}); "
                  f"missed {counts.get('missed', 0)}, extra {counts.get('extra', 0)}, "
                  f"rejected {counts.get('rejected', 0)}, unscorable {counts.get('unscorable_annotation', 0)}, "
                  f"unclear {counts.get('model_unclear', 0)}")
    print(f"\nRun folder: {run_dir}")
    return 0


def check_points(argv):
    from .configuration import load_camera_calibration
    from .pipeline import load_session, measure_points
    from .media import probe
    parser = argparse.ArgumentParser(prog="rvectr check-points",
                                     description="Triangulate hand-marked points and compare with known distances")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--points", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    config = load_session(args.config)
    paths = RuntimePaths.discover()
    cameras = {c["id"]: load_camera_calibration(paths.calibration_file(c["calibration"]), c["id"],
                                                probe(paths.video(c["video"]))["image_size"])
               for c in config["cameras"]}
    result = measure_points(json.loads(args.points.read_text()), cameras)
    if args.out:
        write_json(args.out, result)
    for item in result["distances"]:
        measured = "not reconstructed" if item["measured_m"] is None else f"{item['measured_m'] * 1000:.1f} mm"
        error = "" if item["error_m"] is None else f"  error {item['error_m'] * 1000:+.1f} mm"
        print(f"{item['from']}-{item['to']}: {measured}{error}")
    return 0


def frames(argv):
    from .pipeline import extract_frames
    parser = argparse.ArgumentParser(prog="rvectr frames", description=(
        "Save synchronized frames for marking points. Supply --sync sync.json so the images show the same "
        "reference-camera time. The filenames identify the camera and requested time."))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--time", type=float, required=True, help="seconds on the reference (first) camera")
    parser.add_argument("--sync", type=Path, help="sync.json from a run or from `rvectr sync`")
    parser.add_argument("--out", type=Path, default=Path("frames"))
    args = parser.parse_args(argv)
    for item in extract_frames(args.config, RuntimePaths.discover(), args.time, args.out, args.sync):
        print(f"{item['camera']}: {item['file']} (camera time {item['camera_time_s']:.3f} s)")
    return 0


def dispatch(name, argv):
    return {"calibrate-intrinsics": calibrate_intrinsics, "calibrate-extrinsics": calibrate_extrinsics,
            "sync": sync, "run": run, "check-points": check_points, "frames": frames}[name](argv)
