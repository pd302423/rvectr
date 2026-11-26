"""Fast checks of the error-budget simulation (a simulation, not a measurement)."""
import numpy as np
import pytest

from rvectr import errorbudget as eb
from rvectr.geometry import triangulate_points


def test_zero_noise_recovers_every_depth_within_1_mm():
    for mode in ("two_cam", "three_cam"):
        for pace in eb.PACES:
            for fps in (60.0, 30.0):
                setup = eb.Setup(mode=mode, pace=pace, fps=fps, white_px=0.0)
                run = eb.run_config(setup, 0.04, 3, seed=5)
                assert np.isfinite(run["depth_error_m"]).all()       # nothing unclear
                assert np.abs(run["depth_error_m"]).max() < 1e-3


def test_one_camera_side_view_is_accurate_but_oblique_view_has_perspective_error():
    side = eb.run_config(eb.Setup(mode="side_1cam", white_px=0.0), 0.0, 2, seed=1)
    oblique = eb.run_config(eb.Setup(mode="oblique_1cam", white_px=0.0), 0.0, 2, seed=1)
    assert np.abs(side["depth_error_m"]).max() < 1e-3
    assert np.abs(oblique["depth_error_m"]).max() > 5e-3      # moving away from the camera shrinks the image


def test_same_seed_gives_identical_results_and_other_seed_differs():
    setup = eb.Setup(slow_px=2.0, dropout=0.002)
    a, b = eb.run_config(setup, 0.02, 4, seed=7), eb.run_config(setup, 0.02, 4, seed=7)
    c = eb.run_config(setup, 0.02, 4, seed=8)
    np.testing.assert_array_equal(a["depth_error_m"], b["depth_error_m"])
    np.testing.assert_array_equal(a["outcome"], b["outcome"])
    assert not np.array_equal(a["depth_error_m"], c["depth_error_m"], equal_nan=True)


def test_more_white_noise_never_reduces_the_depth_error_spread():
    spreads = []
    for model_px in (0.0, 0.25, 0.5, 1.0, 2.0):
        run = eb.run_config(eb.Setup(white_px=eb.model_px_to_image_px(model_px)), 0.0, 25, seed=3)
        spreads.append(eb.depth_error_sd_m(run))
    assert spreads[0] < 1e-3
    assert all(later >= earlier for earlier, later in zip(spreads, spreads[1:]))
    assert spreads[-1] > 4 * spreads[1]


def test_vectorised_triangulation_agrees_with_the_project_function():
    rng = np.random.default_rng(0)
    cameras = [eb.make_camera(a) for a in (90, 45, -45)]
    points = rng.uniform(-0.4, 0.4, (40, 3)) + [0, -0.8, 0]
    for use in ([0, 1], [0, 2], [0, 1, 2]):
        chosen = [cameras[i] for i in use]
        pixels = np.stack([eb.project(points, cameras[i]) for i in use], axis=1)         # [N, C, 2]
        fast, valid = eb.triangulate_dlt(pixels, np.ones(pixels.shape[:2], bool), chosen)
        assert valid.all()
        for point, view, fast_xyz in zip(points, pixels, fast):
            slow = triangulate_points(view[:, None, :], np.ones((len(use), 1)), chosen)["xyz"][0]
            assert np.abs(fast_xyz - slow).max() < 1e-6
            assert np.abs(fast_xyz - point).max() < 1e-6


def test_triangulation_never_fills_in_a_point_seen_by_fewer_than_two_cameras():
    cameras = [eb.make_camera(a) for a in (90, 45)]
    pixels = np.stack([eb.project(np.array([[0.0, -0.9, 0.0]] * 3), c) for c in cameras], axis=1)
    present = np.array([[True, True], [True, False], [False, False]])
    xyz, valid = eb.triangulate_dlt(pixels, present, cameras)
    assert valid.tolist() == [True, False, False]
    assert np.isnan(xyz[1:]).all()


def test_heavy_dropouts_give_unclear_repetitions_not_guessed_depths():
    setup = eb.Setup(white_px=0.0, dropout=0.35)           # both hips seen by both cameras in only ~18% of frames
    rng = np.random.default_rng(2)
    times, h, depths, starts = eb.simulate_trace(setup, 0.04, rng)
    assert 0.05 < np.isfinite(h).mean() < 0.4              # gaps stay as NaN
    run = eb.run_config(setup, 0.04, 6, seed=2)
    assert (run["outcome"] == eb.UNCLEAR).all()
    assert np.isnan(run["depth_error_m"]).all()
    assert eb.flag_rate(run) == 0 and eb.unclear_rate(run) == 1


def test_a_missing_bottom_frame_makes_a_repetition_unclear_through_classify():
    setup = eb.Setup(white_px=0.0)
    times, h, depths, starts = eb.simulate_trace(setup, 0.0, np.random.default_rng(1))
    bottoms = starts + setup.descent_s
    h[np.abs(times - bottoms[2]) < 0.1] = np.nan             # no data around the bottom of repetition 2
    measured, outcomes, _, _ = eb.measure(setup, times, h, bottoms)
    assert outcomes[2] == eb.UNCLEAR and np.isnan(measured[2])
    assert outcomes[1] == eb.REACHED and outcomes[3] == eb.REACHED


def test_shallow_repetitions_are_flagged_with_the_default_rule():
    setup = eb.Setup(white_px=eb.model_px_to_image_px(0.5))
    deep = eb.run_config(setup, 0.0, 8, seed=4)
    shallow = eb.run_config(setup, 0.06, 8, seed=4)
    assert eb.flag_rate(deep) == 0 and eb.flag_rate(shallow) == 1


def test_minimum_detectable_difference_grows_with_noise_and_is_a_tested_grid_value():
    grid_m = [step / 200 for step in range(7)]          # 0, 0.5 cm, ... 3 cm: fine enough to tell the noise levels apart
    found = []
    for model_px in (0.25, 1.0, 2.0):
        setup = eb.Setup(white_px=eb.model_px_to_image_px(model_px))
        runs = [eb.run_config(setup, delta, 24, seed=6) for delta in grid_m]
        found.append(eb.minimum_detectable_difference_m(runs)[0])
    assert all(value in grid_m[1:] for value in found)   # a tested value, never interpolated
    assert found == sorted(found) and found[0] < found[-1]


def test_simulated_truth_matching_windows_are_disjoint_for_both_paces():
    for pace in eb.PACES:
        setup = eb.Setup(pace=pace)
        bottoms = eb.rep_starts(setup) + setup.descent_s
        # A true bottom is matched within one descent duration; the 1 s standing
        # pause leaves a positive gap between adjacent matching windows.
        assert np.all(np.diff(bottoms) > 2 * setup.descent_s)


def test_grid_point_is_selected_on_training_sessions_and_not_researched_on_holdout():
    def fake_run(delta, shallow_holdout_unclear=0):
        outcome = np.zeros((20, 4), dtype=int)
        depth_error = np.zeros((20, 4), dtype=float)
        if delta:
            outcome[10:, 1:][:shallow_holdout_unclear] = eb.UNCLEAR
            depth_error[:, 1:] = -delta
            depth_error[10:10 + shallow_holdout_unclear, 1:] = np.nan
        return {"delta_m": delta, "depth_error_m": depth_error, "outcome": outcome}

    runs = [fake_run(0), fake_run(0.003, shallow_holdout_unclear=1), fake_run(0.005, shallow_holdout_unclear=4)]
    detected, threshold = eb.minimum_detectable_difference_m(runs)
    assert detected == pytest.approx(0.003)
    heldout_match = eb.score(eb.subset_sessions(runs[0], 10, 20))
    heldout_shallow = eb.score(eb.subset_sessions(runs[1], 10, 20))
    assert not eb.threshold_counts(heldout_match, heldout_shallow, threshold)["passes"]


def test_exact_95_of_100_with_five_unclear_counts_unclear_in_denominator():
    matching = np.zeros(100)
    shallow = np.r_[np.full(95, 2.0), np.full(5, -np.inf)]
    threshold, _ = eb.choose_threshold(matching)
    counts = eb.threshold_counts(matching, shallow, threshold)
    assert threshold == 0
    assert counts["matching_total"] == counts["shallow_total"] == 100
    assert counts["false_alarms"] == 0 and counts["detected_shallow"] == 95
    assert counts["shallow_unclear"] == 5 and counts["shallow_unclear_rate"] == 0.05
    assert counts["matching_unclear"] == 0
    assert counts["passes"]


def test_minimum_grid_accepts_95_detected_and_five_unclear_in_exact_100_training_reps():
    def run(delta, unclear_first_half=0):
        errors = np.zeros((200, 2), dtype=float)
        outcomes = np.zeros((200, 2), dtype=int)
        if unclear_first_half:
            errors[:unclear_first_half, 1] = np.nan
            outcomes[:unclear_first_half, 1] = eb.UNCLEAR
        return {"delta_m": delta, "depth_error_m": errors, "outcome": outcomes}

    matching, shallow = run(0), run(0.003, unclear_first_half=5)
    detected, threshold = eb.minimum_detectable_difference_m([matching, shallow])
    train_match = eb.score(eb.subset_sessions(matching, 0, 100))
    train_shallow = eb.score(eb.subset_sessions(shallow, 0, 100))
    counts = eb.threshold_counts(train_match, train_shallow, threshold)
    assert detected == pytest.approx(0.003)
    assert counts["matching_total"] == counts["shallow_total"] == 100
    assert counts["false_alarms"] == 0
    assert counts["detected_shallow"] == 95
    assert counts["passes"]


def test_six_unclear_of_100_cannot_reach_95_percent_detection():
    matching = np.r_[np.zeros(95), np.ones(5)]
    shallow = np.r_[np.full(94, 2.0), np.full(6, -np.inf)]
    threshold, _ = eb.choose_threshold(matching)
    counts = eb.threshold_counts(matching, shallow, threshold)
    assert counts["detected_shallow"] == 94
    assert not counts["passes"]


def test_five_percent_false_alarm_boundary_is_inclusive_and_ties_are_not_flags():
    matching = np.r_[np.zeros(95), np.ones(5)]
    shallow = np.full(100, 2.0)
    threshold, _ = eb.choose_threshold(matching)
    counts = eb.threshold_counts(matching, shallow, threshold)
    assert counts["false_alarms"] == 5
    assert counts["passes"]
    assert np.count_nonzero(matching == threshold) == 95  # a score equal to the cutoff is not flagged


def test_unclear_all_repetitions_does_not_produce_a_valid_threshold():
    assert eb.choose_threshold(np.full(100, -np.inf))[0] is None


def test_cluster_bootstrap_samples_sessions_not_repetitions():
    run = {"outcome": np.array([[0, 1, 1, 1], [0, 0, 0, 0]], dtype=int)}
    lo, hi = eb.session_bootstrap_rate(run, eb.SHALLOWER, n_boot=200, seed=3)
    assert 0 <= lo <= hi <= 1
    assert lo < hi


def test_extended_setup_accepts_per_camera_timing_and_shared_camera_scenarios():
    setup = eb.Setup(sync_offsets_frames=(0.0, -1.0), camera_bias_px=0.5,
                     dropout_burst_probability=0.001, dropout_burst_frames=6,
                     motion_noise_factor=0.5, camera_translation_sigma_m=0.01,
                     camera_rotation_sigma_deg=0.25)
    run = eb.run_config(setup, 0.04, 2, seed=2)
    assert run["outcome"].shape == (2, 4)


def test_camera_extrinsic_perturbation_is_an_error_not_a_camera_repositioning():
    exact = eb.run_config(eb.Setup(white_px=0.0), 0.04, 3, seed=8)
    perturbed = eb.run_config(eb.Setup(white_px=0.0, camera_translation_sigma_m=0.02,
                                       camera_rotation_sigma_deg=0.5), 0.04, 3, seed=8)
    assert np.max(np.abs(exact["depth_error_m"])) < 1e-3
    assert np.nanmax(np.abs(perturbed["depth_error_m"] - exact["depth_error_m"])) > 1e-3


def test_noise_unit_conversion():
    assert eb.MM_PER_MODEL_PX == pytest.approx(8.30, abs=0.01)
    assert eb.MM_PER_IMAGE_PX == pytest.approx(2.11, abs=0.01)
    assert eb.model_px_to_image_px(1.0) == pytest.approx(3.94, abs=0.01)


def test_dwell_keeps_the_pelvis_at_the_bottom_and_is_still_measured():
    times = np.arange(0, 10, 0.01)
    d = eb.descent_profile(times, [1.0], [0.3], 2.0, dwell_s=1.0)
    assert np.allclose(d[(times >= 3.0) & (times < 4.0)], 0.3)       # rests for 1 s after the 2 s descent
    assert d[times > 5.0 + 2.0].max() == 0 and d[times < 1.0].max() == 0
    run = eb.run_config(eb.Setup(pace="fast", white_px=0.0, dwell_s=1.0), 0.0, 2, seed=3)
    assert np.isfinite(run["depth_error_m"]).all()                   # nothing unclear
    assert np.abs(run["depth_error_m"]).max() < 3e-3
    shares = eb.bottom_model_shares(run)
    assert abs(sum(shares.values()) - 1) < 1e-12 and shares["missing"] == 0

def test_sparse_matching_set_uses_finite_cutoff_and_separate_unclear_counts():
    matches = np.r_[np.full(97, np.nan), [0.0, 1.0, 1.0]]
    cutoff, counts = eb.choose_threshold(matches, np.full(100, -2.0))
    assert np.isfinite(cutoff) and cutoff < -2
    assert counts["matching_unclear"] == 97
    assert counts["false_alarms"] == 3 and counts["detected_shallow"] == 100
    assert counts["passes"]


def test_shared_vertical_error_projects_same_height_in_every_camera():
    setup = eb.Setup(mode="three_cam", white_px=0.0, shared_vertical_sigma_m=0.004)
    times, pixels, _, cameras, starts = eb.simulate_observations(setup, [0.30] * 4, np.random.default_rng(1))
    points = eb.hip_points(eb.descent_profile(times, starts, [0.30] * 4, setup.descent_s))
    measured = []
    for i, cam in enumerate(cameras):
        camera_depth = (points @ cam["R"].T + cam["t"].reshape(3))[:, :, 2]
        measured.append((pixels[:, i, :, 1] - eb.project(points, cam)[:, :, 1]) * camera_depth / cam["K"][1, 1])
    np.testing.assert_allclose(measured[0], measured[1], atol=1e-12)
    np.testing.assert_allclose(measured[1], measured[2], atol=1e-12)
    assert np.std(measured[0]) == pytest.approx(0.004, rel=0.1)
