"""Run the squat-depth error-budget simulation and write results to outputs/sim/.

    uv run --no-sync python tools/run_error_budget.py --quick    # under a minute
    uv run --no-sync python tools/run_error_budget.py            # full run, a few minutes

SIMULATION, NOT A MEASUREMENT. See backend/rvectr/errorbudget.py for the model.
Writes summary.json, summary.md and PNG figures into outputs/sim/error_budget_<UTC time>/.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import multiprocessing
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from rvectr import errorbudget as eb  # noqa: E402

# ----------------------------------------------------------------------------- what to run
ESTIMATORS = ("parabola", "extreme")        # the new estimator and the old one, compared in section 6
SLOW_CALIBRATION_PX = 0.5                    # slow noise added in the second calibration table (model px)
NOISE_LEVELS = (0.5, 1.0)                    # white noise in "model pixels" (8.3 mm each at the person)
DETECTION_CM = (0, 1, 2, 3, 4, 6, 8)         # true differences reported in the detection tables
MODE_LABELS = {"side_1cam": "1 camera (side)", "oblique_1cam": "1 camera (oblique)",
               "two_cam": "2 cameras", "three_cam": "3 cameras"}
DWELLS_S = (0.0, 0.3, 1.0)                   # time resting at the bottom in the "pause at the bottom" table
BASE = eb.Setup()                            # reference: 2 cameras at 90 and 45 degrees, 60 fps, 0.5 model px white noise


def model(value):
    return eb.model_px_to_image_px(value)


# name, levels, how to apply a level, level used in the ranking, baseline level, unit label
SWEEPS = {
    "white_noise": ([0, 0.25, 0.5, 1.0, 1.5, 2.0], lambda s, v: s.with_(white_px=model(v)), 1.0, 0.5, "model px"),
    "slow_noise": ([0, 0.25, 0.5, 1.0], lambda s, v: s.with_(slow_px=model(v)), 0.5, 0, "model px (sigma, tau 0.2 s)"),
    "posture_bias_beta": ([0, 0.05, 0.10, 0.20], lambda s, v: s.with_(beta=v), 0.10, 0, "x descent"),
    "dropouts": ([0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.10], lambda s, v: s.with_(dropout=v), 0.02, 0, "probability per hip per camera"),
    "sync_error": ([0, 0.5, 1, 2], lambda s, v: s.with_(sync_frames=v), 1, 0, "frames (camera B)"),
    "frame_rate": ([30, 60], lambda s, v: s.with_(fps=float(v)), 30, 60, "fps"),
    "camera_separation": ([20, 30, 45, 60, 75, 90], lambda s, v: s.with_(separation_deg=float(v)), 20, 45, "degrees between A and B"),
    "scale_error": ([-0.05, -0.03, -0.01, 0, 0.01, 0.03, 0.05], lambda s, v: s.with_(scale_error=v), -0.03, 0, "fraction"),
    "tilt": ([0, 0.5, 1, 2, 3, 5], lambda s, v: s.with_(tilt_deg=float(v)), 2, 0, "degrees towards travel"),
}

EXTENDED_SENSITIVITY = {
    "clustered_missing_8_frames": eb.Setup(dropout_burst_probability=0.004, dropout_burst_frames=8),
    "motion_dependent_noise_100pct": eb.Setup(motion_noise_factor=1.0),
    "camera_specific_bias_0_5_px": eb.Setup(camera_bias_px=0.5),
    "shared_vertical_error_4mm": eb.Setup(shared_vertical_sigma_m=0.004),
    "slow_drift_0_5_model_px": eb.Setup(slow_px=model(0.5)),
    "two_camera_offset_1_frame": eb.Setup(sync_offsets_frames=(0.0, -1.0)),
    "three_camera_offsets_1_frame": eb.Setup(mode="three_cam", sync_offsets_frames=(0.0, -1.0, 1.0)),
    "camera_center_error_10mm": eb.Setup(camera_translation_sigma_m=0.01),
    "camera_rotation_error_0_5deg": eb.Setup(camera_rotation_sigma_deg=0.5),
}


def settings(quick, sessions):
    if quick:
        return {"sessions": sessions or 20, "ref_grid_cm": (0, 0.3, 2, 3, 4, 6, 8, 12), "sweep_grid_cm": (0, 4, 8, 16),
                "check_sessions": 30}
    return {"sessions": sessions or 300, "ref_grid_cm": (0, 0.3, 0.5, 0.8, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 8, 12, 16),
            "sweep_grid_cm": (0, 2, 4, 8, 12, 16), "check_sessions": 150}


# ----------------------------------------------------------------------------- parallel work
def work(job):
    kind, setup, arg, n, seed = job
    if kind in ("run", "target"):
        return job[:3], eb.run_config(setup, arg, n, seed)
    return job[:3], eb.single_frame_difference_sd_m(setup, n, seed)


def execute(jobs, workers):
    done, started = {}, time.time()
    if workers > 1:
        with multiprocessing.get_context("fork").Pool(workers) as pool:
            for i, (key, value) in enumerate(pool.imap_unordered(work, jobs, chunksize=2), 1):
                done[key] = value
                if i % 100 == 0:
                    print(f"  {i}/{len(jobs)} jobs, {time.time() - started:.0f} s", file=sys.stderr)
    else:
        for key, value in map(work, jobs):
            done[key] = value
    return done


def mdd_mm(done, setup, grid_cm):
    runs = [done[("run", setup, d / 100)] for d in grid_cm]
    mdd, threshold = eb.minimum_detectable_difference_m(runs)
    return (None if not np.isfinite(mdd) else mdd * 1000), threshold * 1000


def detection_bracket(done, setup, grid_cm, seed=0):
    """Training-selected grid point and one frozen held-out evaluation with clustered intervals."""
    runs = [done[("run", setup, d / 100)] for d in grid_cm]
    first, threshold = eb.minimum_detectable_difference_m(runs)
    split = len(runs[0]["outcome"]) // 2
    train_match = eb.score(eb.subset_sessions(runs[0], 0, split))
    if np.isfinite(first):
        idx = next(i for i, d in enumerate(grid_cm) if abs(d / 100 - first) < 1e-12)
    else:
        idx = len(grid_cm) - 1
    train_shallow = eb.score(eb.subset_sessions(runs[idx], 0, split))
    training = eb.threshold_counts(train_match, train_shallow, threshold)
    match_run = eb.subset_sessions(runs[0], split, len(runs[0]["outcome"]))
    shallow_run = eb.subset_sessions(runs[idx], split, len(runs[idx]["outcome"]))
    heldout = eb.threshold_counts(eb.score(match_run), eb.score(shallow_run), threshold)
    return {"lower_tested_mm": grid_cm[idx - 1] * 10 if idx else 0,
            "first_passing_tested_mm": first * 1000 if np.isfinite(first) else None,
            "diagnostic_tested_mm": grid_cm[idx] * 10, "threshold_mm": threshold * 1000,
            "training_counts": training,
            "heldout_matching_false_alarm_rate": heldout["false_alarm_rate"],
            "heldout_matching_false_alarm_rate_95ci": eb.session_bootstrap_flag_rate(match_run, threshold, seed=seed),
            "heldout_shallow_detection_rate": heldout["detection_rate"],
            "heldout_shallow_detection_rate_95ci": eb.session_bootstrap_flag_rate(shallow_run, threshold, seed=seed + 1),
            "heldout_matching_counts": {k: heldout[k] for k in ("matching_total", "matching_unclear", "matching_unclear_rate", "false_alarms", "max_false_alarms")},
            "heldout_shallow_counts": {k: heldout[k] for k in ("shallow_total", "shallow_unclear", "shallow_unclear_rate", "detected_shallow", "min_detected_shallow")},
            "passes_on_training_grid": bool(np.isfinite(first)),
            "passes_on_heldout_sessions": heldout["passes"]}


def effective_tolerance_mm(done, setup):
    """True difference that the pipeline's fixed 3 cm line really corresponds to (3 cm / gain, gain from the 8 cm runs)."""
    return setup.tolerance_m * 1000 / eb.difference_gain(done[("run", setup, 0.08)])


def text_mm(value, grid_cm):
    return f"> {grid_cm[-1] * 10:.0f}" if value is None else f"{value:.1f}"


# ----------------------------------------------------------------------------- main
def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="few sessions and coarse grids (under a minute)")
    parser.add_argument("--sessions", type=int, help="sessions per condition (default 300, or 20 with --quick)")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--pelvis-fast-mm", type=float, help="measured fast (frame-to-frame) noise of the two-camera pelvis "
                        "height, as squat.jitter reports it (vertical_fast_sd_m); adds the measured-noise scenario table")
    parser.add_argument("--pelvis-slow-mm", type=float, help="measured slow drift of the two-camera pelvis height "
                        "(vertical_slow_sd_m); adds the measured-noise scenario table")
    parser.add_argument("--workers", type=int, default=min(16, os.cpu_count() or 1))
    parser.add_argument("--out-root", default=str(ROOT / "outputs" / "sim"))
    args = parser.parse_args()
    if args.sessions is not None and args.sessions < 2:
        parser.error("--sessions must be at least 2 for a training/holdout split")
    cfg = settings(args.quick, args.sessions)
    n, seed = cfg["sessions"], args.seed
    ref_grid, sweep_grid = cfg["ref_grid_cm"], cfg["sweep_grid_cm"]
    started = time.time()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(args.out_root) / f"error_budget_{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    try:
        code_version = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                      text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                                    text=True, check=True).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        code_version = "working-tree-uncommitted"
        dirty = True
    source_files = ("backend/rvectr/errorbudget.py", "backend/rvectr/squat.py",
                    "backend/rvectr/pipeline.py", "tools/run_error_budget.py", "uv.lock", "pyproject.toml")
    source_hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in source_files}
    runtime = {"python": platform.python_version(),
               **{name: importlib.metadata.version(name) for name in ("numpy", "scipy")}}

    # ---- list every (set-up, true difference) simulation we need
    wanted = {}   # setup -> grid

    def need(setup, grid):
        wanted[setup] = tuple(sorted(set(wanted.get(setup, ())) | set(grid)))

    reference = {(m, noise, pace): BASE.with_(mode=m, white_px=model(noise), pace=pace)
                 for m in eb.MODES for noise in NOISE_LEVELS for pace in eb.PACES}
    for setup in reference.values():
        need(setup, ref_grid)
    for pace in eb.PACES:
        need(BASE.with_(pace=pace, trace="filtered"), ref_grid)
    sweep_setups = {}
    for name, (levels, apply, _, _, _) in SWEEPS.items():
        for pace in eb.PACES:
            for level in levels:
                sweep_setups[(name, "two_cam", pace, level)] = apply(BASE.with_(pace=pace), level)
    for pace in eb.PACES:   # a third camera is the obvious cure for dropouts, so show it too
        for level in SWEEPS["dropouts"][0]:
            sweep_setups[("dropouts", "three_cam", pace, level)] = SWEEPS["dropouts"][1](
                BASE.with_(pace=pace, mode="three_cam"), level)
    for setup in sweep_setups.values():
        need(setup, sweep_grid)
    # ---- estimator comparison: the same two-camera set-ups with the old "extreme" estimator,
    # the dropout sweep and the 2.0 px noise case with it, and the slow-noise runs for the calibration table
    comparison_setups = {(est, noise, pace): BASE.with_(white_px=model(noise), pace=pace, estimator=est)
                         for est in ESTIMATORS for noise in NOISE_LEVELS for pace in eb.PACES}
    for setup in comparison_setups.values():
        need(setup, ref_grid)
    dropout_setups = {(est, pace, level): BASE.with_(pace=pace, dropout=level, estimator=est)
                      for est in ESTIMATORS for pace in eb.PACES for level in SWEEPS["dropouts"][0]}
    noisy_setups = {(est, pace): BASE.with_(pace=pace, white_px=model(2.0), estimator=est)
                    for est in ESTIMATORS for pace in eb.PACES}
    slow_setups = {(noise, pace): BASE.with_(white_px=model(noise), slow_px=model(SLOW_CALIBRATION_PX), pace=pace)
                   for noise in NOISE_LEVELS for pace in eb.PACES}
    for setup in list(dropout_setups.values()) + list(noisy_setups.values()) + list(slow_setups.values()):
        need(setup, (0,))
    # ---- pause at the bottom: two cameras, 0.5 model px, both paces, dwell 0 / 0.3 / 1.0 s
    dwell_setups = {(pace, dwell): BASE.with_(pace=pace, dwell_s=dwell) for pace in eb.PACES for dwell in DWELLS_S}
    for setup in dwell_setups.values():
        need(setup, ref_grid)
    # ---- measured-noise scenario: only if the user gave measured jitter
    measured_setups = measured_noise_setups(args.pelvis_fast_mm, args.pelvis_slow_mm)
    for setup in measured_setups.values():
        need(setup, ref_grid)
    sensitivity_setups = {}
    for name, template in EXTENDED_SENSITIVITY.items():
        modes = eb.MODES if name in {"clustered_missing_8_frames", "motion_dependent_noise_100pct",
                                     "camera_specific_bias_0_5_px", "shared_vertical_error_4mm", "slow_drift_0_5_model_px",
                                     "camera_center_error_10mm", "camera_rotation_error_0_5deg"} else (template.mode,)
        for mode in modes:
            for pace in eb.PACES:
                overrides = {**template.__dict__, "mode": mode, "pace": pace}
                if template.sync_offsets_frames and len(template.sync_offsets_frames) != (3 if mode == "three_cam" else 2):
                    continue
                if mode.endswith("1cam") and template.sync_offsets_frames:
                    continue
                setup = BASE.with_(**overrides)
                sensitivity_setups[(name, mode, pace)] = setup
                need(setup, ref_grid)
    jobs = [("run", s, d / 100, n, seed) for s, grid in wanted.items() for d in grid]
    target_setup = BASE.with_(pace="controlled")
    target_sessions = 600
    jobs += [("target", target_setup, d / 1000, target_sessions, seed + 73491) for d in (0, 3)]
    check_setups = {(noise, pace): BASE.with_(white_px=model(noise), pace=pace)
                    for noise in NOISE_LEVELS for pace in eb.PACES}
    jobs += [("single", s, 0, cfg["check_sessions"], seed) for s in check_setups.values()]
    print(f"{len(jobs)} jobs, {n} sessions each, {args.workers} workers", file=sys.stderr)
    done = execute(jobs, args.workers)

    # ---- reference set-up table and detection curves
    table, detection = [], []
    for (mode, noise, pace), setup in reference.items():
        run0 = done[("run", setup, 0.0)]
        mdd, threshold = mdd_mm(done, setup, ref_grid)
        bracket = detection_bracket(done, setup, ref_grid, seed=seed)
        table.append({"mode": mode, "white_noise_model_px": noise, "white_noise_image_px": setup.white_px,
                      "white_noise_mm_at_person": eb.image_px_to_mm(setup.white_px), "pace": pace,
                      "sd_single_depth_error_mm": eb.depth_error_sd_m(run0) * 1000,
                      "mean_depth_error_mm": float(np.nanmean(run0["depth_error_m"])) * 1000,
                      "sd_difference_two_reps_mm": eb.difference_sd_m(run0) * 1000,
                      "minimum_detectable_difference_mm": mdd, "tested_grid_bracket_mm": bracket, "threshold_mm": threshold,
                      "unclear_rate": eb.unclear_rate(run0), "extra_detected_reps_per_session": eb.extra_reps(run0)})
        curve = {}
        for d in ref_grid:
            r = done[("run", setup, d / 100)]
            attempts = r["outcome"][:, 1:]
            curve[d] = {"flagged_shallower": eb.flag_rate(r), "unclear": eb.unclear_rate(r),
                        "total": attempts.size, "flagged_count": int(np.count_nonzero(attempts == eb.SHALLOWER)),
                        "unclear_count": int(np.count_nonzero(attempts == eb.UNCLEAR)),
                        "missed_count": int(np.count_nonzero(r["bottom_model"][:, 1:] == "missing")),
                        "extra_detections_per_session": eb.extra_reps(r)}
        detection.append({"mode": mode, "white_noise_model_px": noise, "pace": pace,
                          "tolerance_mm": setup.tolerance_m * 1000,
                          "by_true_difference_cm": {str(k): v for k, v in curve.items()}})
    filtered = []
    for pace in eb.PACES:
        s = BASE.with_(pace=pace, trace="filtered")
        mdd, _ = mdd_mm(done, s, ref_grid)
        filtered.append({"pace": pace, "mode": "two_cam", "white_noise_model_px": 0.5,
                         "sd_difference_two_reps_mm": eb.difference_sd_m(done[("run", s, 0.0)]) * 1000,
                         "minimum_detectable_difference_mm": mdd})

    # ---- sweeps and ranking
    sweeps = {}
    for (name, mode, pace, level), setup in sweep_setups.items():
        mdd, _ = mdd_mm(done, setup, sweep_grid)
        run0 = done[("run", setup, 0.0)]
        sweeps.setdefault(f"{name}" if mode == "two_cam" else f"{name}_{mode}", []).append(
            {"level": level, "pace": pace, "mode": mode, "minimum_detectable_difference_mm": mdd,
             "sd_difference_two_reps_mm": eb.difference_sd_m(run0) * 1000, "unclear_rate": eb.unclear_rate(run0), "extra_detected_reps_per_session": eb.extra_reps(run0),
             "effective_tolerance_mm": effective_tolerance_mm(done, setup)})
    ranking = []
    for name, (levels, apply, plausible, base_level, unit) in SWEEPS.items():
        entry = {"source": name, "plausible_level": plausible, "baseline_level": base_level, "unit": unit}
        for pace in eb.PACES:
            base = mdd_mm(done, BASE.with_(pace=pace), sweep_grid)[0]
            this = mdd_mm(done, apply(BASE.with_(pace=pace), plausible), sweep_grid)[0]
            run0 = done[("run", apply(BASE.with_(pace=pace), plausible), 0.0)]
            entry[pace] = {"baseline_mdd_mm": base, "mdd_mm": this,
                           "change_mm": None if this is None or base is None else this - base,
                           "unclear_rate": eb.unclear_rate(run0),
                           "effective_tolerance_mm": effective_tolerance_mm(done, apply(BASE.with_(pace=pace), plausible))}
        ranking.append(entry)

    def rank_key(e):
        changes = [abs(e[p]["change_mm"]) if e[p]["change_mm"] is not None else 1e9 for p in eb.PACES]
        return -max(changes)
    ranking.sort(key=rank_key)

    # ---- analytic cross-check (white noise only)
    check = []
    for (noise, pace), setup in check_setups.items():
        analytic = eb.image_px_to_mm(setup.white_px)
        single, standing = done[("single", setup, 0)]
        simulated = eb.difference_sd_m(done[("run", setup, 0.0)]) * 1000
        check.append({"white_noise_model_px": noise, "pace": pace, "analytic_sigma_camera_mm": analytic,
                      "simulated_sd_difference_mm": simulated, "ratio_simulated_to_analytic": simulated / analytic,
                      "differs_more_than_15_percent": abs(simulated / analytic - 1) > 0.15,
                      "single_frame_sd_difference_mm": single * 1000,
                      "ratio_single_frame_to_analytic": single * 1000 / analytic,
                      "standing_pelvis_height_sd_mm": standing * 1000,
                      "analytic_pelvis_height_sd_mm": analytic / 2})

    pause = []
    for (pace, dwell), setup in dwell_setups.items():
        run0 = done[("run", setup, 0.0)]
        mdd, _ = mdd_mm(done, setup, ref_grid)
        pause.append({"pace": pace, "dwell_s": dwell, "mean_depth_error_mm": float(np.nanmean(run0["depth_error_m"])) * 1000,
                      "sd_depth_error_mm": eb.depth_error_sd_m(run0) * 1000,
                      "bottom_model_share": eb.bottom_model_shares(run0), "unclear_rate": eb.unclear_rate(run0),
                      "minimum_detectable_difference_mm": mdd})
    measured = None
    if measured_setups:
        measured = {"pelvis_fast_mm": args.pelvis_fast_mm or 0.0, "pelvis_slow_mm": args.pelvis_slow_mm or 0.0,
                    "per_camera_per_hip_white_mm": 2 * (args.pelvis_fast_mm or 0.0),
                    "per_camera_per_hip_slow_mm": 2 * (args.pelvis_slow_mm or 0.0), "rows": []}
        for (mode, pace), setup in measured_setups.items():
            mdd, _ = mdd_mm(done, setup, ref_grid)
            measured["rows"].append({"mode": mode, "pace": pace, "minimum_detectable_difference_mm": mdd,
                                     "unclear_rate": eb.unclear_rate(done[("run", setup, 0.0)])})

    extended = []
    for (name, mode, pace), setup in sensitivity_setups.items():
        bracket = detection_bracket(done, setup, ref_grid, seed=seed + len(extended) * 7)
        run0 = done[("run", setup, 0.0)]
        extended.append({"scenario": name, "pace": pace, "mode": mode,
                         "minimum_detectable_difference_mm": bracket["first_passing_tested_mm"],
                         "tested_grid_bracket_mm": bracket,
                         "unclear_rate": eb.unclear_rate(run0),
                         "fixed_3cm_shallow_flag_rate_at_0cm": eb.flag_rate(run0),
                         "fixed_3cm_shallow_flag_rate_95ci_at_0cm": eb.session_bootstrap_rate(run0, eb.SHALLOWER, seed=seed + len(extended))})

    comparison = estimator_comparison(done, ref_grid, comparison_setups, dropout_setups, noisy_setups, slow_setups)
    assumptions = assumption_list(n, seed, cfg)
    target_match = done[("target", target_setup, 0.0)]
    target_shallow = done[("target", target_setup, 0.003)]
    target_split = len(target_match["outcome"]) // 2
    target_threshold, _ = eb.choose_threshold(eb.score(eb.subset_sessions(target_match, 0, target_split)))
    target_match_holdout = eb.subset_sessions(target_match, target_split, target_sessions)
    target_shallow_holdout = eb.subset_sessions(target_shallow, target_split, target_sessions)
    target_counts = eb.threshold_counts(eb.score(target_match_holdout), eb.score(target_shallow_holdout), target_threshold)
    target_result = {"difference_mm": 3, "sessions_total": target_sessions,
                     "sessions_for_threshold": target_split, "sessions_held_out": target_sessions - target_split,
                     "threshold_mm": target_threshold * 1000,
                     "heldout_matching_counts": {k: target_counts[k] for k in ("matching_total", "matching_unclear", "matching_unclear_rate", "false_alarms", "max_false_alarms")},
                     "heldout_shallow_counts": {k: target_counts[k] for k in ("shallow_total", "shallow_unclear", "shallow_unclear_rate", "detected_shallow", "min_detected_shallow")},
                     "heldout_matching_false_alarm_rate": target_counts["false_alarm_rate"],
                     "heldout_matching_false_alarm_rate_95ci": eb.session_bootstrap_flag_rate(target_match_holdout, target_threshold, seed=seed + 2),
                     "heldout_shallow_detection_rate": target_counts["detection_rate"],
                     "heldout_shallow_detection_rate_95ci": eb.session_bootstrap_flag_rate(target_shallow_holdout, target_threshold, seed=seed + 3),
                     "passes_on_heldout_sessions": target_counts["passes"]}
    result = {"title": "Squat-depth error budget: simulation, not a measurement",
              "created_utc": stamp, "quick": args.quick, "sessions_per_condition": n, "seed": seed,
              "code_version": code_version, "source_dirty": dirty, "source_sha256": source_hashes, "runtime": runtime,
              "settings": {"reference_grid_cm": list(ref_grid), "sweep_grid_cm": list(sweep_grid),
                           "baseline_frame_rate_fps": BASE.fps, "frame_rate_sensitivity_fps": SWEEPS["frame_rate"][0],
                           "baseline_camera_geometry": f"Side at {eb.SIDE_DEG:g}°, oblique at {eb.OBLIQUE_DEG:g}°, optional mirrored oblique at {-eb.OBLIQUE_DEG:g}°. Distance {eb.DISTANCE_M:g} m, lens height {eb.LENS_HEIGHT_M:g} m.",
                           "pipeline_defaults_squat": eb.RULES,
                           "session_test_repetitions": BASE.n_test_reps,
                           "units": {"depth": "m internally; mm/cm in reports", "image_noise": "image px at camera; model px converted at person", "timing": "frames", "camera_angles": "degrees"},
                           "confidence_interval": "95% percentile bootstrap resampling whole sessions; 500 replicates"},
              "assumptions": assumptions, "reference_table": table, "reference_filtered_trace": filtered,
              "detection_curves_default_rule": detection, "sweeps": sweeps, "ranking": ranking,
              "analytic_cross_check": check, "estimator_comparison": comparison,
              "extended_sensitivity": extended,
              "targeted_3mm_heldout": target_result,
              "pause_at_bottom": pause, "measured_noise_scenario": measured,
              "runtime_s": time.time() - started}
    (out / "summary.json").write_text(json.dumps(clean(result), indent=2, default=float, allow_nan=False), encoding="utf-8")
    figures(out, table, detection, sweeps, ranking, ref_grid)
    (out / "summary.md").write_text(markdown(result, ref_grid, sweep_grid), encoding="utf-8")
    print(f"wrote {out} in {time.time() - started:.0f} s")


def measured_noise_setups(fast_mm, slow_mm):
    """Set-ups for the measured-noise scenario (empty if no measured jitter was given).

    The measured numbers describe the two-camera pelvis height. That height averages two cameras and
    two hips, so its noise is the per-camera, per-hip noise divided by 2 (the same factor the analytic
    cross-check in section 5 uses). The per-camera, per-hip noise is therefore 2 x the measured value.
    The same per-camera noise is then used for one, two and three cameras.
    """
    if fast_mm is None and slow_mm is None:
        return {}
    white_px = 2 * (fast_mm or 0.0) / eb.MM_PER_IMAGE_PX
    slow_px = 2 * (slow_mm or 0.0) / eb.MM_PER_IMAGE_PX
    return {(mode, pace): BASE.with_(mode=mode, pace=pace, white_px=white_px, slow_px=slow_px)
            for mode in eb.MODES for pace in eb.PACES}


def estimator_comparison(done, ref_grid, comparison_setups, dropout_setups, noisy_setups, slow_setups):
    """Old ("extreme") against new ("parabola") estimator, two cameras, plus the calibration of depth_se_m."""
    rows = []
    for (est, noise, pace), setup in comparison_setups.items():
        run0 = done[("run", setup, 0.0)]
        mdd, _ = mdd_mm(done, setup, ref_grid)
        rows.append({"estimator": est, "white_noise_model_px": noise, "pace": pace,
                     "mean_depth_error_mm": float(np.nanmean(run0["depth_error_m"])) * 1000,
                     "sd_depth_error_mm": eb.depth_error_sd_m(run0) * 1000,
                     "sd_difference_two_reps_mm": eb.difference_sd_m(run0) * 1000,
                     "minimum_detectable_difference_mm": mdd, "unclear_rate": eb.unclear_rate(run0)})
    dropouts = [{"estimator": est, "pace": pace, "dropout": level,
                 "unclear_rate": eb.unclear_rate(done[("run", setup, 0.0)])}
                for (est, pace, level), setup in dropout_setups.items()]
    extra = [{"estimator": est, "pace": pace, "white_noise_model_px": 2.0,
              "extra_detected_reps_per_session": eb.extra_reps(done[("run", setup, 0.0)])}
             for (est, pace), setup in noisy_setups.items()]
    calibration = []
    for slow, table in ((0.0, {k: v for k, v in comparison_setups.items() if k[0] == "parabola"}),
                        (SLOW_CALIBRATION_PX, {("parabola",) + k: v for k, v in slow_setups.items()})):
        for (_, noise, pace), setup in table.items():
            run0 = done[("run", setup, 0.0)]
            reported = run0["depth_se_m"][np.isfinite(run0["depth_se_m"])]
            actual = eb.depth_error_sd_m(run0)
            calibration.append({"slow_noise_model_px": slow, "white_noise_model_px": noise, "pace": pace,
                                "mean_reported_depth_se_mm": float(reported.mean()) * 1000 if len(reported) else None,
                                "empirical_sd_depth_error_mm": actual * 1000,
                                "ratio_reported_to_empirical": float(reported.mean() / actual) if len(reported) else None})
    return {"rows": rows, "dropouts": dropouts, "extra_reps_2px": extra, "calibration": calibration}


def clean(value):
    """Replace NaN/inf by null so the JSON file is strictly valid."""
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    return value


# ----------------------------------------------------------------------------- text
def assumption_list(n, seed, cfg):
    s = eb
    return [
        "THIS IS A SIMULATION, NOT A MEASUREMENT. No two-phone footage exists yet; every number below is a prediction to be compared with experiment later.",
        f"Person: two hip points {s.HIP_SPACING_M} m apart; pelvis = midpoint; standing pelvis height {s.STANDING_M} m; reference repetition depth {s.REFERENCE_DEPTH_M} m.",
        f"Session: {s.STAND_S:.0f} s standing, the reference repetition, then 3 test repetitions, each shallower than the reference by the true difference; {s.PAUSE_S:.0f} s standing pause after every repetition.",
        "Motion: raised cosine (depth x sin^2) down and up, equal descent and ascent time; no pause at the bottom (except in section 7, where the pelvis rests at the bottom for dwell_s). Descent time 2.0 s (controlled) or 0.8 s (fast). The pelvis also moves backwards by 0.5 x the current descent.",
        f"Cameras: pinhole, {s.IMAGE_W}x{s.IMAGE_H} portrait, focal length {s.FOCAL_PX:.0f} px, {s.DISTANCE_M} m from the person, lens height {s.LENS_HEIGHT_M} m, level, no lens distortion. Camera A side-on (90 deg from the facing direction), camera B front-oblique (45 deg); optional camera C at the mirrored oblique position (-45 deg). 60 fps (30 fps in the frame-rate sweep); frame phase random.",
        f"White noise is set in 'model pixels' (1 model pixel = 1.70 m x 1.25 / 256 = {s.MM_PER_MODEL_PX:.2f} mm at the person) and converted at {s.MM_PER_IMAGE_PX:.2f} mm per image pixel: 0.5 model px = {s.model_px_to_image_px(0.5):.2f} image px, 1.0 model px = {s.model_px_to_image_px(1.0):.2f} image px, per frame, per camera, per hip, per image axis, 1 sigma, independent.",
        "Slow noise: AR(1) per camera, hip and image axis, correlation time 0.2 s, given as stationary sigma. Posture bias: the detected hip is displaced upward in 3D by beta x current descent (same displacement seen by every camera). Dropouts: each hip in each camera is missing in a frame with probability p, independently. Missing data is never filled in.",
        "Sync error: camera B samples the motion at t + d frames and is then treated as simultaneous (cameras A and C are exact). Only the two-camera and three-camera modes have it.",
        "Extended sensitivity cases: missing blocks last 8 frames and affect every camera/hip together; detector noise can rise by 100% at peak motion; a 0.5 image-pixel camera-specific bias is fixed for an entire take; a separate case projects the same 4 mm SD vertical error into every camera for each frame; phone offsets are supplied per camera; camera-center and camera-orientation errors are drawn independently per camera and stay fixed within a take.",
        "Calibration errors: scale error multiplies every reconstructed length by (1 + s); tilt leans the calibrated up-axis by e degrees towards the direction of horizontal travel (backwards). Tilt does not apply to the one-camera modes (they have no horizontal position).",
        "Two or more cameras: hips are triangulated by a vectorised linear (DLT) method (checked against rvectr.geometry.triangulate_points), then the pipeline's own steps are used: squat.pelvis_track, squat.segment_reps, squat.classify, pipeline defaults (tolerance 3 cm, min depth 6 cm, min coverage 0.85, reference rep 1, raw trace; standing level from the 0.5-2.5 s window). Not simulated: the pipeline's confidence, reprojection-error and ray-angle rejection, the robust refinement step, left/right hip swaps, lens distortion, and correlation between the two hips' errors.",
        "Depth estimator (sections 1 to 5): the pipeline default 'parabola' (standing height = median of the standing samples; bottom = vertex of a parabola fitted to the samples near the lowest point; the lowest point needs at least 5 usable samples, an upward-opening fit, the vertex inside the samples with 2 on each side, and no gap above 0.1 s). The original 'extreme' estimator (highest standing sample minus lowest bottom sample) is compared in section 6.",
        "One camera: the comparison uses image-row scale at the person's standing distance. During this simulated descent, the hips move backwards, away from the angled front camera. Their image displacement understates depth when scaled at the standing distance. Other paths and placements can change this bias. A side view has no depth motion in this particular simulated path. Multi-view triangulation can recover depth when camera calibration and timing are accurate; it does not remove calibration or detector errors by itself.",
        "Detected repetitions are matched to the true ones by bottom time. A repetition the software does not find, or finds with too little coverage, is 'unclear'. If the reference repetition itself is unusable (classify refuses it), every test repetition of that session is 'unclear'.",
        "Detection threshold: the measured reference depth minus measured test depth must be above one cutoff. The training half sets the cutoff allowed by the false-alarm budget and selects the first grid difference meeting both count limits. The second half evaluates this frozen pair. Unclear test repetitions stay in the denominator and count as not detected; unclear matching repetitions stay in the denominator and are not false alarms. At least 95% of all shallow repetitions must be flagged and no more than 5% of all matching repetitions may be flagged. The reported value is the first passing tested grid point, with the previous tested point as a lower bracket; no interpolation is used. This best-threshold comparison is separate from the pipeline's fixed 3 cm decision rule.",
        f"Statistics: {n} simulated sessions per condition, each with 3 test repetitions sharing one reference; seed {seed}. The first half calibrates the cutoff and the second half evaluates it. The same session random streams are reused across comparable conditions (common random numbers). Rate intervals resample whole sessions (500 bootstrap samples), preserving the within-session dependence.",
        "Production differences: simulated keypoints are generated from the motion and noise settings. The real pipeline uses RTMPose detections and also applies confidence, reprojection-error and ray-angle rejection and robust triangulation refinement. Those effects, lens distortion, hip swaps, clothing, real camera-to-camera error correlation and measured calibration/sync distributions are not validated by this simulation.",
    ]


def table_md(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(map(str, row)) + " |" for row in rows]
    return "\n".join(lines)


def markdown(r, ref_grid, sweep_grid):
    top = ref_grid[-1] * 10
    out = ["# Squat-depth error budget (simulation, not a measurement)", "",
           f"Created {r['created_utc']} UTC. {'Quick run: few sessions, treat as a rough preview. ' if r['quick'] else ''}"
           "Every number here comes from a computer simulation of the planned two-phone design. It is a prediction to compare with experiment, not a measurement.", "",
           "## Assumptions", ""] + [f"- {a}" for a in r["assumptions"]]
    out += ["", "## 1. Reference set-up: how small a difference can be detected", "",
            "Reference: camera A side-on, camera B at 45 degrees (cameras 45 degrees apart), 60 fps. "
            "'extra reps found' counts detections unmatched to the four true attempts per session, even when another attempt was missed. 'sd depth' is the spread of one measured depth around the truth; 'sd diff' is the spread of (test - reference) with no true difference; "
            f"First passing tested difference on the training grid (a '>' means not reached within {top:.0f} mm). Grid values only; see the bracket and counts in summary.json. Millimetres.", ""]
    rows = []
    for e in r["reference_table"]:
        rows.append([MODE_LABELS[e["mode"]], f"{e['white_noise_model_px']} ({e['white_noise_mm_at_person']:.1f} mm)", e["pace"],
                     f"{e['sd_single_depth_error_mm']:.1f}", f"{e['mean_depth_error_mm']:+.1f}", f"{e['sd_difference_two_reps_mm']:.1f}",
                     text_mm(e["minimum_detectable_difference_mm"], ref_grid), f"{e['threshold_mm']:.1f}", f"{100 * e['unclear_rate']:.0f}%",
                     f"{e['extra_detected_reps_per_session']:+.2f}"])
    out.append(table_md(["mode", "white noise, model px (mm at person)", "pace", "sd depth", "mean depth error", "sd diff", "MDD", "best threshold", "unclear", "extra reps found"], rows))
    target = r["targeted_3mm_heldout"]
    matches, shallow = target["heldout_matching_counts"], target["heldout_shallow_counts"]
    out += ["", f"Independent targeted 3 mm check at {target['threshold_mm']:.3f} mm: "
            f"{matches['false_alarms']}/{matches['matching_total']} matching attempts flagged "
            f"({matches['matching_unclear']} unclear); {shallow['detected_shallow']}/{shallow['shallow_total']} "
            f"shallower attempts flagged ({shallow['shallow_unclear']} unclear). "
            f"Meets both held-out count limits: {target['passes_on_heldout_sessions']}. "
            "Session-bootstrap intervals and per-condition counts are in summary.json."]
    out += ["", "Same, two cameras but using the pipeline's 5-frame filtered trace instead of the raw trace (0.5 model px):", ""]
    out.append(table_md(["pace", "sd diff", "MDD"], [[f["pace"], f"{f['sd_difference_two_reps_mm']:.1f}", text_mm(f["minimum_detectable_difference_mm"], ref_grid)] for f in r["reference_filtered_trace"]]))
    out += ["", "## 2. Detection curve with the pipeline's default rule (tolerance 3 cm)", "",
            "Percentage of test repetitions flagged 'shallower' versus the true difference (cm). "
            "A flag needs the measured depth to fall more than 3 cm below the measured reference, so the 50% point sits near 3 cm by design. "
            "'unclear' is the share of test repetitions the software refused to judge (at a true difference of 0).", ""]
    cm = [d for d in ref_grid if d in eb_detection_cm(ref_grid)]
    rows = []
    for e in r["detection_curves_default_rule"]:
        c = e["by_true_difference_cm"]
        rows.append([MODE_LABELS[e["mode"]], e["white_noise_model_px"], e["pace"]] + [f"{100 * c[str(d)]['flagged_shallower']:.0f}" for d in cm] + [f"{100 * c['0']['unclear']:.0f}%"])
    out.append(table_md(["mode", "noise", "pace"] + [f"{d} cm" for d in cm] + ["unclear"], rows))
    out += ["", "## 3. One-at-a-time sensitivity sweeps (two cameras unless stated, 0.5 model px white noise)", "",
            f"Minimum detectable difference in mm for each level; '>' means not reached within {sweep_grid[-1] * 10:.0f} mm "
            "(often because more than 5% of repetitions are unclear). 'unclear' and 'extra reps' (repetitions found beyond the 4 real ones, per session) are at true difference 0. '3 cm line is really' is the true "
            "difference (mm) that the pipeline's fixed 3 cm tolerance corresponds to once the error rescales the measured depth; "
            "errors that rescale depth (posture bias, scale, tilt) barely change the best-threshold MDD but shift this line.", ""]
    for name, rows_ in r["sweeps"].items():
        levels = sorted({x["level"] for x in rows_})
        body = []
        for level in levels:
            cells = [level]
            for pace in eb.PACES:
                x = next(x for x in rows_ if x["level"] == level and x["pace"] == pace)
                cells += [text_mm(x["minimum_detectable_difference_mm"], sweep_grid), f"{100 * x['unclear_rate']:.0f}%",
                          f"{x['extra_detected_reps_per_session']:+.2f}", f"{x['effective_tolerance_mm']:.1f}"]
            body.append(cells)
        out += [f"**{name}**", "", table_md(["level", "controlled MDD", "unclear", "extra reps", "3 cm line is really", "fast MDD", "unclear", "extra reps", "3 cm line is really"], body), ""]
    out += ["## 4. Ranking: which error source matters most", "",
            "Change in minimum detectable difference when one error is set to a plausible level (all else at the reference). Positive = worse. "
            "'not reached' means the criterion could not be met at all. The last column is the true difference that the pipeline's fixed 3 cm tolerance then corresponds to (30 mm if there is no rescaling error).", ""]
    rows = []
    for e in r["ranking"]:
        def cell(p):
            x = e[p]
            if x["change_mm"] is None:
                return f"not reached ({100 * x['unclear_rate']:.0f}% unclear)"
            return f"{x['change_mm']:+.1f} (from {x['baseline_mdd_mm']:.1f} to {x['mdd_mm']:.1f})"
        rows.append([e["source"], f"{e['plausible_level']} {e['unit']}", cell("controlled"), cell("fast"),
                     f"{e['controlled']['effective_tolerance_mm']:.1f} / {e['fast']['effective_tolerance_mm']:.1f}"])
    out.append(table_md(["source", "plausible level", "controlled, mm", "fast, mm", "3 cm line is really (controlled / fast), mm"], rows))
    out += ["", "How to read this (structural reasons, each visible in the tables of this run): "
            "(a) The depth is a vertical distance, so camera separation, sync error and the horizontal travel hardly matter: the height of a hip comes mostly from each camera's image row, "
            "and at the bottom of a repetition the pelvis is momentarily still, so a clock offset between phones costs little there. "
            "(b) Errors that rescale depth (posture bias, scale, tilt, one-camera perspective) scale signal and noise together, so they leave the best-threshold MDD almost unchanged "
            "but move the 3 cm decision line (last column). "
            "(c) Large white noise does more than add jitter: once the pelvis-height noise is a sizeable fraction of the 3 cm entry level of squat.segment_reps, "
            "the rule splits or invents repetitions ('extra reps' column) and the MDD grows faster than the noise. "
            "(d) Dropouts act through the coverage rule (at least 85% of the repetition) and the bottom rule (enough observed samples around the lowest point, without a long gap; "
            "the old estimator instead needed the bottom frame and both its neighbours, which made about 6% of repetitions unclear at only 0.5% missing detections per hip per camera, see section 6). "
            "With two cameras every hip needs both cameras, so the pelvis is missing in a frame about four times as often as one detection.", "",
            "![ranking](ranking.png)", "![detection](detection_curves.png)", "![sweeps](sweeps.png)", "",
            "## 5. Cross-check against the analytic value (white noise only, two cameras)", "",
            "Simple argument: the height of one hip from two cameras has spread sigma/sqrt(2); the pelvis (two hips) sigma/2; "
            "depth = standing minus bottom multiplies by sqrt(2); the difference of two repetitions by another sqrt(2). Result: sigma_camera, "
            "where sigma_camera is the white noise in mm at the person.", ""]
    rows = [[c["white_noise_model_px"], c["pace"], f"{c['analytic_sigma_camera_mm']:.1f}", f"{c['simulated_sd_difference_mm']:.1f}",
             f"{c['ratio_simulated_to_analytic']:.2f}", f"{c['single_frame_sd_difference_mm']:.1f}", f"{c['ratio_single_frame_to_analytic']:.2f}",
             f"{c['standing_pelvis_height_sd_mm']:.2f} (expected {c['analytic_pelvis_height_sd_mm']:.2f})"] for c in r["analytic_cross_check"]]
    out.append(table_md(["noise, model px", "pace", "analytic, mm", "simulated sd diff, mm", "ratio", "two-frame estimator, mm", "ratio", "pelvis sd standing, mm"], rows))
    if any(c["differs_more_than_15_percent"] for c in r["analytic_cross_check"]):
        out += ["", "The full simulation differs from the analytic value by more than 15%. Why: the analytic formula assumes each depth is read from "
                "one standing frame and one bottom frame. The pipeline's estimator uses the MEDIAN of about a second of standing frames and a PARABOLA fitted to "
                "the frames near the bottom, so it averages many noisy values and the real spread is smaller (the old 'extreme' estimator, see section 6, "
                "used the maximum and the minimum, which are also less spread but biased). The 'two-frame estimator' columns "
                "check this: reading depth from two single frames reproduces the analytic value, and the standing pelvis spread confirms sigma/2. "
                "The fast pace is closer to the analytic value because fewer frames lie near the bottom. The raw trace is not smoothed; smoothing would reduce the spread further."]
    else:
        out += ["", "The full simulation agrees with the analytic value to within 15%."]
    out += estimator_markdown(r["estimator_comparison"], ref_grid)
    out += pause_markdown(r["pause_at_bottom"], ref_grid)
    if r["measured_noise_scenario"]:
        out += measured_markdown(r["measured_noise_scenario"], ref_grid)
    out.append("")
    return "\n".join(out)


def estimator_markdown(c, ref_grid):
    """Section 6: the old and the new depth estimator side by side."""
    out = ["", "## 6. Estimator comparison: old 'extreme' against new 'parabola' (two cameras)", "",
           "'extreme' = highest standing sample minus lowest bottom sample (the original rule). 'parabola' = median of the standing samples "
           "minus the vertex of a parabola fitted around the lowest point (the new default, used in sections 1 to 5). "
           "Mean depth error is the bias (a positive value means depths read too deep). Millimetres.", ""]
    rows = [[e["estimator"], e["white_noise_model_px"], e["pace"], f"{e['mean_depth_error_mm']:+.1f}", f"{e['sd_depth_error_mm']:.1f}",
             f"{e['sd_difference_two_reps_mm']:.1f}", text_mm(e["minimum_detectable_difference_mm"], ref_grid),
             f"{100 * e['unclear_rate']:.0f}%"] for e in c["rows"]]
    out.append(table_md(["estimator", "white noise, model px", "pace", "mean depth error (bias)", "sd depth error", "sd diff",
                         "minimum detectable difference", "unclear"], rows))
    out += ["", "Unclear share of test repetitions with dropouts (each hip in each camera missing in a frame with this probability), no other noise than the reference 0.5 model px:", ""]
    levels = sorted({d["dropout"] for d in c["dropouts"]})
    rows = []
    for level in levels:
        cells = [level]
        for pace in eb.PACES:
            for est in ESTIMATORS:
                x = next(d for d in c["dropouts"] if d["dropout"] == level and d["pace"] == pace and d["estimator"] == est)
                cells.append(f"{100 * x['unclear_rate']:.0f}%")
        rows.append(cells)
    out.append(table_md(["dropout probability"] + [f"{p}, {e}" for p in eb.PACES for e in ESTIMATORS], rows))
    out += ["", "Extra repetitions found per session (beyond the 4 real ones) at 2.0 model px white noise:", ""]
    out.append(table_md(["estimator", "pace", "extra reps per session"],
                        [[x["estimator"], x["pace"], f"{x['extra_detected_reps_per_session']:+.2f}"] for x in c["extra_reps_2px"]]))
    out += ["", "Calibration of the reported error bar (parabola): mean reported depth_se_m against the actual spread (standard deviation) of the depth error. "
            "The reported value assumes errors from frame to frame are independent, so with slow noise it should be too small. Millimetres.", ""]
    rows = [[x["slow_noise_model_px"], x["white_noise_model_px"], x["pace"],
             "n/a" if x["mean_reported_depth_se_mm"] is None else f"{x['mean_reported_depth_se_mm']:.2f}",
             f"{x['empirical_sd_depth_error_mm']:.2f}",
             "n/a" if x["ratio_reported_to_empirical"] is None else f"{x['ratio_reported_to_empirical']:.2f}"] for x in c["calibration"]]
    out.append(table_md(["slow noise, model px", "white noise, model px", "pace", "mean reported depth_se", "actual sd of depth error",
                         "ratio reported / actual"], rows))
    return out


def pause_markdown(rows_in, ref_grid):
    """Section 7: resting at the bottom for a while (for example touching a stool)."""
    out = ["", "## 7. Pause at the bottom (two cameras, 0.5 model px white noise)", "",
           "The pelvis goes down, stays at the bottom for the dwell time, then comes up. With a rest, height against time is flat at the bottom, "
           "not a parabola. 'parabola', 'plateau', 'none' = share of all repetitions whose bottom was read with that model "
           "('none' = the bottom was not seen well enough, so the repetition is unclear; 'missing' = the repetition was not found at all). "
           "Mean and sd of the depth error in mm; MDD = minimum detectable difference in mm.", ""]
    rows = []
    for e in rows_in:
        share = e["bottom_model_share"]
        rows.append([e["pace"], e["dwell_s"], f"{e['mean_depth_error_mm']:+.2f}", f"{e['sd_depth_error_mm']:.2f}",
                     f"{100 * share['parabola']:.0f}%", f"{100 * share['plateau']:.0f}%",
                     f"{100 * (share['none'] + share['missing']):.0f}%", f"{100 * e['unclear_rate']:.0f}%",
                     text_mm(e["minimum_detectable_difference_mm"], ref_grid)])
    out.append(table_md(["pace", "dwell, s", "mean depth error", "sd depth error", "parabola", "plateau", "none", "unclear", "MDD"], rows))
    return out


def measured_markdown(m, ref_grid):
    """Section 8: the design's minimum detectable difference if the noise is what was measured."""
    out = ["", "## 8. Measured-noise scenario", "",
           f"Measured jitter of the two-camera pelvis height: fast noise {m['pelvis_fast_mm']} mm, slow drift {m['pelvis_slow_mm']} mm "
           "(what squat.jitter reports as vertical_fast_sd_m and vertical_slow_sd_m). ASSUMPTION: pelvis-height noise = per-camera, per-hip noise / 2 "
           "for two cameras, because two cameras and two hips are averaged. So the simulation uses "
           f"{m['per_camera_per_hip_white_mm']} mm white noise and {m['per_camera_per_hip_slow_mm']} mm slow noise (correlation time 0.2 s) "
           "per camera, per hip, per image axis, for every mode; one- and three-camera pelvis noise then differs from the measured value. Millimetres.", ""]
    rows = [[MODE_LABELS[x["mode"]], x["pace"], text_mm(x["minimum_detectable_difference_mm"], ref_grid), f"{100 * x['unclear_rate']:.0f}%"]
            for x in m["rows"]]
    out.append(table_md(["mode", "pace", "MDD", "unclear"], rows))
    return out


def eb_detection_cm(grid):
    return [d for d in DETECTION_CM if d in grid]


# ----------------------------------------------------------------------------- figures
def figures(out, table, detection, sweeps, ranking, ref_grid):
    colours = {"side_1cam": "#c0504d", "oblique_1cam": "#e69f00", "two_cam": "#0072b2", "three_cam": "#009e73"}
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), sharex=True, sharey=True)
    for e in detection:
        ax = axes[list(eb.PACES).index(e["pace"]), NOISE_LEVELS.index(e["white_noise_model_px"])]
        xs = sorted(float(k) for k in e["by_true_difference_cm"])
        ys = [100 * e["by_true_difference_cm"][str(int(k)) if k == int(k) else str(k)]["flagged_shallower"] for k in xs]
        ax.plot([x * 10 for x in xs], ys, "o-", ms=3, color=colours[e["mode"]], label=MODE_LABELS[e["mode"]])
    for (i, pace), (j, noise) in [(a, b) for a in enumerate(eb.PACES) for b in enumerate(NOISE_LEVELS)]:
        ax = axes[i, j]
        ax.axvline(30, color="grey", ls=":", lw=1)
        ax.set_xlim(-2, 82)
        ax.set_title(f"{pace} pace, white noise {noise} model px", fontsize=10)
        ax.grid(alpha=0.3)
    for ax in axes[1]:
        ax.set_xlabel("true difference from reference (mm)")
    for ax in axes[:, 0]:
        ax.set_ylabel("flagged shallower (%)")
    axes[0, 0].legend(fontsize=8, loc="upper left")
    fig.suptitle("Simulation, not a measurement: detection with the default 3 cm tolerance (dotted line)")
    fig.tight_layout()
    fig.savefig(out / "detection_curves.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    finite = [abs(e[p]["change_mm"]) for e in ranking for p in eb.PACES if e[p]["change_mm"] is not None]
    cap = 1.3 * max(finite + [1.0])
    names = [f"{e['source']} ({e['plausible_level']})" for e in ranking][::-1]
    ys = np.arange(len(ranking))
    for k, (pace, colour) in enumerate(zip(eb.PACES, ("#0072b2", "#e69f00"))):
        vals = [e[pace]["change_mm"] for e in ranking][::-1]
        shown = [cap if v is None else v for v in vals]
        ax.barh(ys + (k - 0.5) * 0.38, shown, 0.38, color=colour, label=pace)
        for y, v in zip(ys + (k - 0.5) * 0.38, vals):
            ax.text(max(0, cap if v is None else v) + 0.1, y, "not reached" if v is None else f"{v:+.1f}", va="center", fontsize=7)
    ax.set_yticks(ys, names)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("change in minimum detectable difference (mm); positive = worse")
    ax.set_title("Simulation, not a measurement: which error source matters most\n(one error at a time at the plausible level in brackets; reference = 2 cameras, 0.5 model px)", fontsize=10)
    ax.legend()
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "ranking.png", dpi=130)
    plt.close(fig)

    names = [n for n in sweeps if not n.endswith("three_cam")]
    fig, axes = plt.subplots(3, 3, figsize=(12, 9))
    for ax, name in zip(axes.ravel(), names):
        for pace, colour in zip(eb.PACES, ("#0072b2", "#e69f00")):
            pts = sorted((x["level"], x["minimum_detectable_difference_mm"]) for x in sweeps[name] if x["pace"] == pace)
            ax.plot([p[0] for p in pts], [np.nan if p[1] is None else p[1] for p in pts], "o-", color=colour, label=pace)
            if name == "dropouts":
                pts3 = sorted((x["level"], x["minimum_detectable_difference_mm"]) for x in sweeps["dropouts_three_cam"] if x["pace"] == pace)
                ax.plot([p[0] for p in pts3], [np.nan if p[1] is None else p[1] for p in pts3], "s--", color=colour, label=f"{pace}, 3 cameras")
        ax.set_title(name, fontsize=10)
        ax.set_ylabel("MDD (mm)")
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=7)
    fig.suptitle("Simulation, not a measurement: minimum detectable difference, one error at a time (gaps = not reached)")
    fig.tight_layout()
    fig.savefig(out / "sweeps.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
