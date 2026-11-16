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


def test_minimum_detectable_difference_is_small_for_small_noise_and_grows_with_noise():
    mdd = []
    for model_px in (0.25, 1.0):
        setup = eb.Setup(white_px=eb.model_px_to_image_px(model_px))
        runs = [eb.run_config(setup, d / 100, 20, seed=6) for d in (0, 2, 4, 8)]
        mdd.append(eb.minimum_detectable_difference_m(runs)[0])
    assert 0 < mdd[0] < mdd[1] < 0.04


def test_noise_unit_conversion():
    assert eb.MM_PER_MODEL_PX == pytest.approx(8.30, abs=0.01)
    assert eb.MM_PER_IMAGE_PX == pytest.approx(2.11, abs=0.01)
    assert eb.model_px_to_image_px(1.0) == pytest.approx(3.94, abs=0.01)
