"""Explicit, held-out-tested OpenCV calibration; no inferred focal lengths.

Each intrinsic observation contains corners [N,2], object_points [N,3], and
image_size [width,height]. Optional source metadata is retained for provenance.
Object coordinates for extrinsics must be measured metres in the same labelled
physical board frame for every camera. Board-frame identity is a user assertion:
the software cannot prove that an unlabelled chessboard was not rotated/flipped.
"""

import cv2
import numpy as np


def _points(observation):
    obj = np.asarray(observation["object_points"], dtype=np.float64)
    img = np.asarray(observation.get("corners", observation.get("image_points")), dtype=np.float64)
    if obj.ndim != 2 or obj.shape[1] != 3 or img.shape != (len(obj), 2) or len(obj) < 6:
        raise ValueError("Each board observation requires >=6 paired object [N,3] and image [N,2] points")
    if not np.isfinite(obj).all() or not np.isfinite(img).all():
        raise ValueError("Calibration observations must be finite")
    if np.linalg.matrix_rank(obj - obj.mean(axis=0), tol=1e-8) < 2:
        raise ValueError("Board object points must span a plane or volume")
    if np.linalg.matrix_rank(img - img.mean(axis=0), tol=1e-8) < 2:
        raise ValueError("Board image points must not be collinear")
    return obj, img


def _failure(reason, quality=None, sources=None):
    return {"status": "failed", "reason": reason, "K": None, "distortion": None,
            "quality": quality or {}, "sources": sources or []}


def _image_size(value):
    size = np.asarray(value)
    if size.shape != (2,) or not np.issubdtype(size.dtype, np.number) or not np.isfinite(size).all():
        raise ValueError("image_size must contain finite [width,height]")
    if np.any(size <= 0) or np.any(size != np.floor(size)):
        raise ValueError("image_size must contain positive integer [width,height]")
    return tuple(int(v) for v in size)


def validate_camera(camera, image_size=None, require_metric=True):
    """Validate an externally supplied calibration and its exact pixel frame.

    Returns a JSON-serializable camera copy; raises ValueError for invalid data.
    Every externally supplied camera must declare image_size in its calibrated
    orientation. The caller must additionally enforce a common board_frame_id
    across views (triangulate_points also enforces it). Matching dimensions alone
    cannot verify unchanged cropping, stabilization, lens selection, or a 180°
    rotation; those capture settings remain explicit acquisition requirements.
    """
    from .geometry import _camera
    if not isinstance(camera, dict):
        raise ValueError("Each camera calibration must be an object")
    if camera.get("status", "passed") not in ("passed", "validated"):
        raise ValueError("A failed or provisional calibration cannot be reconstructed")
    missing = [key for key in ("K", "R", "t", "distortion", "image_size") if key not in camera]
    if missing:
        raise ValueError("Calibration is missing required fields: " + ", ".join(missing))
    declared_size = _image_size(camera["image_size"])
    if image_size is not None and declared_size != _image_size(image_size):
        raise ValueError("Calibration image_size differs from the oriented video frame; recalibrate that mode")
    if require_metric and (camera.get("units") != "m" or not isinstance(camera.get("board_frame_id"), str)
                           or not camera["board_frame_id"].strip()):
        raise ValueError("Metric calibration requires units='m' and an explicit labelled board_frame_id")
    validated = _camera(camera)
    result = dict(camera)
    for name in ("K", "R", "t", "distortion"):
        result[name] = validated[name].tolist()
    result["image_size"] = list(declared_size)
    if isinstance(result.get("board_frame_id"), str):
        result["board_frame_id"] = result["board_frame_id"].strip()
    return result


def calibrate_intrinsics(observations, image_size=None, minimum_views=10,
                         max_heldout_error_px=2.0, min_pose_spread_deg=12.0):
    """Fit using training board views and test unseen board views.

    At least ten diverse views are required by default, with 20% reserved for
    testing. The returned K/distortion are trained without those held-out views.
    Pose spread, scale range, and sensor coverage checks reject weak recordings.
    Thresholds are engineering gates, not guarantees of reconstruction accuracy.
    Failed quality checks return no camera matrix, preventing silent fallback.
    """
    observations = list(observations)
    sources = [o.get("source", o.get("source_path")) for o in observations]
    if minimum_views < 6 or max_heldout_error_px <= 0 or min_pose_spread_deg <= 0:
        raise ValueError("Invalid calibration quality thresholds")
    if len(observations) < minimum_views:
        return _failure("insufficient_calibration_views", {"view_count": len(observations),
                        "minimum_views": minimum_views}, sources)
    pairs = [_points(o) for o in observations]
    sizes = [_image_size(o.get("image_size", image_size)) for o in observations]
    if len(set(sizes)) != 1:
        raise ValueError("All calibration views must specify the same positive [width,height]")
    size = tuple(int(v) for v in sizes[0])
    if any(np.any(img < 0) or np.any(img[:, 0] >= size[0]) or np.any(img[:, 1] >= size[1]) for _, img in pairs):
        raise ValueError("Calibration corners must lie inside the declared image")
    centers = np.asarray([img.mean(axis=0) / size for _, img in pairs])
    extents = np.asarray([np.ptp(img, axis=0) / size for _, img in pairs])
    scales = np.sqrt(extents[:, 0] * extents[:, 1])
    center_span = np.ptp(centers, axis=0)
    scale_ratio = float(scales.max() / max(scales.min(), 1e-9))
    quality = {"view_count": len(pairs), "center_span_fraction": center_span.tolist(),
               "board_scale_ratio": scale_ratio, "max_heldout_error_px": max_heldout_error_px,
               "minimum_pose_spread_deg": min_pose_spread_deg}
    if np.max(center_span) < 0.12 or np.min(center_span) < 0.05 or scale_ratio < 1.2:
        return _failure("insufficient_image_coverage_or_scale_diversity", quality, sources)
    heldout_count = max(2, int(np.ceil(len(pairs) * 0.2)))
    heldout = set(np.linspace(0, len(pairs) - 1, heldout_count, dtype=int).tolist())
    train = [i for i in range(len(pairs)) if i not in heldout]
    quality.update({"training_indices": train, "heldout_indices": sorted(heldout)})
    try:
        rms, K, distortion, rvecs, _ = cv2.calibrateCamera(
            [pairs[i][0].astype(np.float32) for i in train],
            [pairs[i][1].astype(np.float32) for i in train], size, None, None,
            criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-10))
    except cv2.error as error:
        quality["opencv_error"] = str(error)
        return _failure("calibration_solver_failed", quality, sources)
    if not np.isfinite(K).all() or not np.isfinite(distortion).all() or not np.isfinite(rms):
        return _failure("nonfinite_calibration", quality, sources)
    quality["training_rms_px"] = float(rms)
    normals = np.asarray([cv2.Rodrigues(r)[0][:, 2] for r in rvecs])
    normal_angles = np.degrees(np.arccos(np.clip(normals @ normals.T, -1, 1)))
    spread = float(normal_angles.max())
    quality["board_normal_spread_deg"] = spread
    if spread < min_pose_spread_deg:
        return _failure("insufficient_board_tilt_diversity", quality, sources)
    width, height = size
    if not (0.1 * width < K[0, 0] < 10 * width and 0.1 * height < K[1, 1] < 10 * height
            and -0.1 * width < K[0, 2] < 1.1 * width and -0.1 * height < K[1, 2] < 1.1 * height):
        return _failure("implausible_intrinsics_check_board_and_recording_mode", quality, sources)
    heldout_errors = []
    for i in sorted(heldout):
        obj, img = pairs[i]
        success, rvec, tvec = cv2.solvePnP(obj, img, K, distortion, flags=cv2.SOLVEPNP_ITERATIVE)
        if not success or not np.isfinite(rvec).all() or not np.isfinite(tvec).all():
            return _failure("heldout_pose_estimation_failed", quality, sources)
        if np.any((cv2.Rodrigues(rvec)[0] @ obj.T + tvec)[2] <= 0):
            return _failure("heldout_board_behind_camera", quality, sources)
        projection = cv2.projectPoints(obj, rvec, tvec, K, distortion)[0].reshape(-1, 2)
        heldout_errors.append(float(np.sqrt(np.mean(np.sum((projection - img) ** 2, axis=1)))))
    quality["heldout_rms_px_per_view"] = heldout_errors
    quality["heldout_rms_px"] = float(np.sqrt(np.mean(np.square(heldout_errors))))
    quality["heldout_max_view_rms_px"] = float(max(heldout_errors))
    if rms > max_heldout_error_px or max(heldout_errors) > max_heldout_error_px:
        return _failure("heldout_or_training_reprojection_error_exceeded", quality, sources)
    return {"status": "passed", "K": K.tolist(), "distortion": distortion.ravel().tolist(),
            "image_size": list(size), "quality": quality, "sources": sources,
            "model": "opencv_pinhole_radial_tangential", "fit_uses_heldout_views": False,
            "scope": "Valid only for the lens, resolution, orientation, crop and stabilization mode calibrated"}


def calibrate_extrinsics(K, distortion, image_points, object_points, *,
                         board_frame_id=None, max_reprojection_px=2.0, image_size=None):
    """Estimate a camera in an explicitly labelled board coordinate system.

    object_points must be measured in metres. board_frame_id must identify the
    same physical board origin and axis direction across cameras. A board that
    moved between observations cannot establish shared camera extrinsics.
    """
    if not isinstance(board_frame_id, str) or not board_frame_id.strip():
        raise ValueError("An explicit shared board_frame_id is required; label the physical origin and axes")
    if max_reprojection_px <= 0:
        raise ValueError("max_reprojection_px must be positive")
    from .geometry import _camera
    camera = _camera({"K": K, "distortion": distortion, "R": np.eye(3), "t": np.zeros(3)})
    K, distortion = camera["K"], camera["distortion"]
    obj, img = _points({"object_points": object_points, "corners": image_points})
    try:
        success, rvec, tvec = cv2.solvePnP(obj, img, K, distortion, flags=cv2.SOLVEPNP_ITERATIVE)
    except cv2.error as error:
        return {"status": "failed", "reason": "extrinsics_solver_failed", "quality": {"opencv_error": str(error)}}
    if not success or not np.isfinite(rvec).all() or not np.isfinite(tvec).all():
        return {"status": "failed", "reason": "extrinsics_solver_failed", "quality": {}}
    R = cv2.Rodrigues(rvec)[0]
    t = tvec.reshape(3)
    projection = cv2.projectPoints(obj, rvec, t, K, distortion)[0].reshape(-1, 2)
    residuals = np.linalg.norm(projection - img, axis=1)
    depth = (R @ obj.T + t[:, None])[2]
    quality = {"rms_px": float(np.sqrt(np.mean(residuals ** 2))),
               "max_px": float(residuals.max()), "point_count": len(obj),
               "per_point_error_px": residuals.tolist(), "all_points_in_front": bool(np.all(depth > 0))}
    if not np.all(depth > 0) or quality["rms_px"] > max_reprojection_px or quality["max_px"] > max_reprojection_px * 2:
        return {"status": "failed", "reason": "extrinsics_quality_failed", "quality": quality}
    result = {"status": "passed", "K": K.tolist(), "distortion": distortion.ravel().tolist(),
              "R": R.tolist(), "t": t.tolist(), "units": "m", "board_frame_id": board_frame_id.strip(),
              "quality": quality, "coordinate_convention": "X_camera = R @ X_world + t",
              "limitation": "Low residual cannot detect a consistently mislabeled board origin or axes"}
    if image_size is not None:
        result["image_size"] = list(_image_size(image_size))
    return result
