"""Synthetic geometry checks; these do not claim real human motion accuracy."""

import cv2
import numpy as np
import pytest

from rvectr.calibration import calibrate_extrinsics, calibrate_intrinsics, validate_camera
from rvectr.geometry import triangulate_points


K = np.array([[1100.0, 0, 960], [0, 1080.0, 540], [0, 0, 1]])


def cameras(centers=None, distortion=None):
    if centers is None:
        centers = [[-0.7, 0, 0], [0.7, 0, 0], [0, 0.7, 0]]
    return [{"K": K.copy(), "R": np.eye(3), "t": -np.array(c, dtype=float),
             "distortion": np.zeros(5) if distortion is None else distortion,
             "units": "m", "board_frame_id": "labelled_board_A"} for c in centers]


def projections(xyz, views):
    return np.stack([cv2.projectPoints(np.asarray(xyz, dtype=float), cv2.Rodrigues(c["R"])[0],
                                      c["t"], c["K"], c["distortion"])[0].reshape(-1, 2) for c in views])


def board():
    x, y = np.meshgrid(np.linspace(-0.24, 0.24, 9), np.linspace(-0.16, 0.16, 7))
    return np.column_stack([x.ravel(), y.ravel(), np.zeros(x.size)])


def calibration_observations(tilted=True, noise=0.08):
    rng = np.random.default_rng(81)
    obj = board()
    observations = []
    for i in range(24):
        rotation = rng.uniform([-0.55, -0.55, -0.2], [0.55, 0.55, 0.2]) if tilted else np.zeros(3)
        translation = np.array([rng.uniform(-0.3, 0.3), rng.uniform(-0.2, 0.2), rng.uniform(1.0, 1.8)])
        img = cv2.projectPoints(obj, rotation, translation, K, np.array([0.03, -0.01, 0.001, 0.001, 0]))[0].reshape(-1, 2)
        img += rng.normal(0, noise, img.shape)
        assert (img >= 0).all() and (img[:, 0] < 1920).all() and (img[:, 1] < 1080).all()
        observations.append({"corners": img, "object_points": obj, "image_size": [1920, 1080], "source": f"synthetic_{i}"})
    return observations


def test_metric_reconstruction_preserves_arbitrary_height_and_motion():
    views = cameras()
    expected = np.array([[0.1, -0.3, 3.2], [-0.2, 0.1, 2.5], [0.3, 0.2, 2.7]])
    result = triangulate_points(projections(expected, views), np.ones((3, 3)), views)
    assert result["valid"].all()
    np.testing.assert_allclose(result["xyz"], expected, atol=1e-8)
    assert result["xyz"][0, 1] < 0  # No fabricated ground/floor clamp.
    assert result["metric"] and result["units"] == "m"
    assert result["reprojection_px"].max() < 1e-8


def test_lens_distortion_is_applied_and_undistorted():
    views = cameras(distortion=np.array([0.2, -0.08, 0.001, -0.002, 0.01]))
    expected = np.array([[0.35, -0.25, 2.3], [-0.35, 0.25, 2.9]])
    result = triangulate_points(projections(expected, views), np.ones((3, 2)), views)
    assert result["valid"].all()
    np.testing.assert_allclose(result["xyz"], expected, atol=1e-6)


def test_camera_rotations_use_world_to_camera_convention():
    views = cameras()
    for i, view in enumerate(views):
        center = -view["t"]
        view["R"] = cv2.Rodrigues(np.array([0.0, (i - 1) * 0.2, 0.1]))[0]
        view["t"] = -view["R"] @ center
    expected = np.array([[0.1, -0.3, 3.2]])
    result = triangulate_points(projections(expected, views), np.ones((3, 1)), views)
    np.testing.assert_allclose(result["xyz"], expected, atol=1e-8)


def test_confidence_and_missing_views_cannot_be_filled_with_previous_values():
    views = cameras()[:2]
    points = projections([[0, 0, 3], [0.1, 0.1, 3]], views)
    points[1, 1] = np.nan
    result = triangulate_points(points, [[1, 1], [0.1, 1]], views)
    assert not result["valid"].any()
    assert np.isnan(result["xyz"]).all()
    assert result["reasons"] == ["insufficient_observations"] * 2


def test_low_baseline_is_rejected_despite_tiny_reprojection_error():
    views = cameras([[0, 0, 0], [0.001, 0, 0]])
    result = triangulate_points(projections([[0.1, 0, 3]], views), np.ones((2, 1)), views)
    assert not result["valid"][0]
    assert result["reasons"][0] == "insufficient_ray_angle"


def test_inconsistent_two_view_correspondence_is_rejected():
    views = cameras()[:2]
    points = projections([[0.1, 0, 3]], views)
    points[1, 0, 1] += 80
    result = triangulate_points(points, np.ones((2, 1)), views)
    assert not result["valid"][0]
    assert np.isnan(result["xyz"][0]).all()


def test_third_camera_outlier_is_rejected_without_biasing_valid_pair():
    views = cameras()
    expected = np.array([[0.1, -0.2, 3.0]])
    points = projections(expected, views)
    points[2, 0] += [100, -150]
    result = triangulate_points(points, np.ones((3, 1)), views)
    assert result["valid"][0] and result["view_count"][0] == 2
    assert result["reasons"][0] == "outlier_view_rejected"
    np.testing.assert_allclose(result["xyz"], expected, atol=1e-8)
    assert not result["used_views"][2, 0]
    assert result["per_view_reprojection_px"][2, 0] > 100


def test_negative_depth_is_rejected():
    views = cameras()[:2]
    result = triangulate_points(projections([[0.1, 0, -3]], views), np.ones((2, 1)), views)
    assert not result["valid"][0]


def test_mismatched_board_frames_and_units_are_rejected():
    views = cameras()[:2]
    points = projections([[0.1, 0, 3]], views)
    views[1]["board_frame_id"] = "different_origin"
    with pytest.raises(ValueError, match="same labelled physical board frame"):
        triangulate_points(points, np.ones((2, 1)), views)
    views[1]["board_frame_id"] = views[0]["board_frame_id"]
    views[1]["units"] = "mm"
    with pytest.raises(ValueError, match="matching explicit units"):
        triangulate_points(points, np.ones((2, 1)), views)


def test_unlabelled_geometry_never_claims_metric_accuracy():
    views = cameras()[:2]
    for view in views:
        del view["units"]
        del view["board_frame_id"]
    result = triangulate_points(projections([[0.1, 0, 3]], views), np.ones((2, 1)), views)
    assert result["valid"][0] and not result["metric"]
    assert result["units"] == "arbitrary"


def test_intrinsics_reject_insufficient_data_without_guessing():
    result = calibrate_intrinsics(calibration_observations()[:3])
    assert result["status"] == "failed"
    assert result["reason"] == "insufficient_calibration_views"
    assert result["K"] is None


def test_intrinsics_reject_repeated_identical_board_poses():
    observation = calibration_observations()[0]
    result = calibrate_intrinsics([observation] * 12)
    assert result["status"] == "failed"
    assert "diversity" in result["reason"]
    assert result["K"] is None


def test_intrinsics_reject_frontoparallel_views_despite_position_and_scale_changes():
    result = calibrate_intrinsics(calibration_observations(tilted=False))
    assert result["status"] == "failed"
    assert result["reason"] == "insufficient_board_tilt_diversity"
    assert result["K"] is None


def test_intrinsics_recover_known_camera_with_independent_heldout_poses():
    result = calibrate_intrinsics(calibration_observations())
    assert result["status"] == "passed", result
    recovered = np.asarray(result["K"])
    np.testing.assert_allclose(recovered[[0, 1], [0, 1]], K[[0, 1], [0, 1]], rtol=0.025)
    assert result["quality"]["heldout_rms_px"] < 0.3
    assert not set(result["quality"]["training_indices"]) & set(result["quality"]["heldout_indices"])
    assert not result["fit_uses_heldout_views"]


def test_intrinsics_reject_noisy_heldout_observations():
    observations = calibration_observations()
    heldout_indices = np.linspace(0, len(observations) - 1, 5, dtype=int)
    rng = np.random.default_rng(3)
    for i in heldout_indices:
        observations[i]["corners"] += rng.normal(0, 5, observations[i]["corners"].shape)
    result = calibrate_intrinsics(observations)
    assert result["status"] == "failed"
    assert result["reason"] == "heldout_or_training_reprojection_error_exceeded"
    assert result["K"] is None


def test_extrinsics_require_labelled_shared_physical_frame():
    obj = board()
    img = cv2.projectPoints(obj, np.zeros(3), np.array([0, 0, 2.0]), K, np.zeros(5))[0].reshape(-1, 2)
    with pytest.raises(ValueError, match="board_frame_id"):
        calibrate_extrinsics(K, np.zeros(5), img, obj)


def test_extrinsics_recover_known_metric_camera_and_refuse_bad_points():
    obj = board()
    rotation = np.array([0.2, -0.3, 0.05])
    translation = np.array([0.1, -0.05, 1.8])
    img = cv2.projectPoints(obj, rotation, translation, K, np.zeros(5))[0].reshape(-1, 2)
    result = calibrate_extrinsics(K, np.zeros(5), img, obj, board_frame_id="marked_corner_A")
    assert result["status"] == "passed"
    np.testing.assert_allclose(result["R"], cv2.Rodrigues(rotation)[0], atol=1e-7)
    np.testing.assert_allclose(result["t"], translation, atol=1e-7)
    assert result["units"] == "m" and result["quality"]["rms_px"] < 1e-6
    img[0] += [60, 30]
    failed = calibrate_extrinsics(K, np.zeros(5), img, obj, board_frame_id="marked_corner_A")
    assert failed["status"] == "failed" and "R" not in failed


def test_external_camera_validation_checks_orientation_units_and_rotation():
    view = cameras()[0]
    view["image_size"] = [1920, 1080]
    validated = validate_camera(view, [1920, 1080])
    assert validated["units"] == "m" and isinstance(validated["K"], list)
    with pytest.raises(ValueError, match="oriented video frame"):
        validate_camera(view, [1080, 1920])
    view["R"] = np.diag([1, 1, -1])
    with pytest.raises(ValueError, match="proper rotation"):
        validate_camera(view)
    view["R"] = np.eye(3)
    view["units"] = "mm"
    with pytest.raises(ValueError, match="Metric calibration"):
        validate_camera(view)


def test_external_camera_validation_rejects_missing_size_and_failed_status():
    view = cameras()[0]
    with pytest.raises(ValueError, match="missing required fields"):
        validate_camera(view)
    view["image_size"] = [1920, 1080]
    view["status"] = "failed"
    with pytest.raises(ValueError, match="failed or provisional"):
        validate_camera(view)
