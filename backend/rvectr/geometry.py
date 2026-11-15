"""Calibrated multi-view geometry, independent of exercise or body orientation.

All 2D coordinates are pixels in the original, unresized camera image. Extrinsics
follow OpenCV's world-to-camera convention: X_camera = R @ X_world + t.
Coordinates have the units of t; metric=True requires explicit metre/frame
metadata on every camera. Reprojection error is a diagnostic, not an independent
accuracy measurement. Two views cannot detect every wrong correspondence.
"""

from itertools import combinations

import cv2
import numpy as np
from scipy.optimize import least_squares


def _camera(camera):
    K = np.asarray(camera["K"], dtype=np.float64)
    R = np.asarray(camera["R"], dtype=np.float64)
    t = np.asarray(camera["t"], dtype=np.float64).reshape(3)
    distortion = np.asarray(camera.get("distortion", np.zeros(5)), dtype=np.float64).reshape(-1)
    if K.shape != (3, 3) or R.shape != (3, 3):
        raise ValueError("K and R must each have shape (3,3)")
    if not all(np.isfinite(a).all() for a in (K, R, t, distortion)):
        raise ValueError("Camera parameters must be finite")
    if distortion.size not in (4, 5, 8, 12, 14):
        raise ValueError("Unsupported OpenCV distortion coefficient count")
    if K[0, 0] <= 0 or K[1, 1] <= 0 or not np.allclose(K[2], [0, 0, 1]):
        raise ValueError("Invalid camera intrinsic matrix")
    if not np.isclose(K[0, 1], 0) or not np.isclose(K[1, 0], 0):
        raise ValueError("This OpenCV camera model requires zero skew")
    if not np.allclose(R.T @ R, np.eye(3), atol=1e-5) or not np.isclose(np.linalg.det(R), 1, atol=1e-5):
        raise ValueError("R must be a proper rotation matrix")
    rvec = cv2.Rodrigues(R)[0]
    return {"K": K, "R": R, "t": t, "distortion": distortion,
            "rvec": rvec, "P": np.column_stack((R, t)), "center": -R.T @ t}


def _project(xyz, camera):
    return cv2.projectPoints(np.asarray(xyz, dtype=np.float64).reshape(1, 3),
                             camera["rvec"], camera["t"], camera["K"],
                             camera["distortion"])[0].reshape(2)


def _dlt(indices, normalized, confidence, cameras):
    rows = []
    for i in indices:
        u, v = normalized[i]
        P = cameras[i]["P"]
        weight = np.sqrt(confidence[i])
        rows.extend([weight * (u * P[2] - P[0]), weight * (v * P[2] - P[1])])
    _, _, vh = np.linalg.svd(np.asarray(rows), full_matrices=False)
    point = vh[-1]
    if abs(point[3]) < 1e-12:
        return None
    return point[:3] / point[3]


def _ray_angle(indices, normalized, cameras):
    rays = {}
    for i in indices:
        ray = cameras[i]["R"].T @ np.r_[normalized[i], 1.0]
        rays[i] = ray / np.linalg.norm(ray)
    angles = []
    for i, k in combinations(indices, 2):
        angle = np.degrees(np.arccos(np.clip(rays[i] @ rays[k], -1, 1)))
        angles.append(min(angle, 180 - angle))
    return max(angles, default=0.0)


def triangulate_points(points, confidence, cameras, threshold=0.5,
                       reprojection_px=8.0, min_ray_angle_deg=1.5):
    """Reconstruct one frame, rejecting missing/ambiguous geometry explicitly.

    Parameters: points [C,J,2], confidence [C,J], and C camera dicts with
    K/distortion/R/t. Returns numpy arrays; serialize NaNs as JSON null upstream.
    No interpolation, flooring, recentering, or assumptions about standing poses
    are applied. Three or more views permit geometric outlier rejection, but
    low residuals still do not prove anatomical landmark accuracy.
    """
    points = np.asarray(points, dtype=np.float64)
    confidence = np.asarray(confidence, dtype=np.float64)
    if points.ndim != 3 or points.shape[2] != 2 or confidence.shape != points.shape[:2]:
        raise ValueError("Expected points [C,J,2] and confidence [C,J]")
    if len(cameras) != points.shape[0]:
        raise ValueError("One camera calibration is required per view")
    if not 0 <= threshold <= 1 or reprojection_px <= 0 or not 0 < min_ray_angle_deg < 90:
        raise ValueError("Invalid confidence, reprojection, or ray-angle threshold")
    finite_confidence = confidence[np.isfinite(confidence)]
    if np.any((finite_confidence < 0) | (finite_confidence > 1)):
        raise ValueError("Confidence must lie in [0,1]")
    units = [c.get("units") for c in cameras]
    frames = [c.get("board_frame_id") for c in cameras]
    if any(u is not None for u in units) and (any(u is None for u in units) or len(set(units)) != 1):
        raise ValueError("All cameras must have matching explicit units")
    if any(f is not None for f in frames) and (not all(frames) or len(set(frames)) != 1):
        raise ValueError("All cameras must share the same labelled physical board frame")
    metric = bool(cameras) and all(u == "m" for u in units) and all(frames) and len(set(frames)) == 1
    calibrated = [_camera(c) for c in cameras]
    count, joints = points.shape[:2]
    xyz = np.full((joints, 3), np.nan)
    valid = np.zeros(joints, dtype=bool)
    errors = np.full(joints, np.nan)
    per_view = np.full((count, joints), np.nan)
    used = np.zeros((count, joints), dtype=bool)
    view_count = np.zeros(joints, dtype=int)
    ray_angles = np.full(joints, np.nan)
    reasons = ["insufficient_observations"] * joints
    observations = np.isfinite(points).all(axis=2) & np.isfinite(confidence) & (confidence >= threshold) & (confidence > 0)
    for joint in range(joints):
        available = np.flatnonzero(observations[:, joint]).tolist()
        if len(available) < 2:
            continue
        normalized = {}
        for i in available:
            c = calibrated[i]
            normalized[i] = cv2.undistortPoints(points[i, joint].reshape(1, 1, 2),
                                               c["K"], c["distortion"]).reshape(2)
        if _ray_angle(available, normalized, calibrated) < min_ray_angle_deg:
            reasons[joint] = "insufficient_ray_angle"
            continue
        candidate_sets = [available] + list(combinations(available, 2)) if len(available) > 2 else [available]
        best = None
        for seed_indices in candidate_sets:
            seed = _dlt(seed_indices, normalized, confidence[:, joint], calibrated)
            if seed is None or not np.isfinite(seed).all():
                continue
            residuals = {i: np.linalg.norm(_project(seed, calibrated[i]) - points[i, joint]) for i in available}
            inliers = [i for i in available if residuals[i] <= reprojection_px and
                       (calibrated[i]["R"] @ seed + calibrated[i]["t"])[2] > 1e-8]
            if len(inliers) < 2 or _ray_angle(inliers, normalized, calibrated) < min_ray_angle_deg:
                continue
            score = (len(inliers), -np.mean([residuals[i] ** 2 for i in inliers]))
            if best is None or score > best[0]:
                best = (score, seed, inliers)
        if best is None:
            reasons[joint] = "inconsistent_views_or_negative_depth"
            continue
        _, initial, inliers = best

        def residual_function(point):
            return np.concatenate([np.sqrt(confidence[i, joint]) *
                                   (_project(point, calibrated[i]) - points[i, joint]) for i in inliers])

        fit = least_squares(residual_function, initial, loss="soft_l1", f_scale=2.0, max_nfev=100)
        if not fit.success or not np.isfinite(fit.x).all():
            reasons[joint] = "optimization_failed"
            continue
        final_errors = {i: np.linalg.norm(_project(fit.x, calibrated[i]) - points[i, joint]) for i in available}
        if any(final_errors[i] > reprojection_px for i in inliers):
            reasons[joint] = "reprojection_error_exceeded"
            continue
        if any((calibrated[i]["R"] @ fit.x + calibrated[i]["t"])[2] <= 1e-8 for i in inliers):
            reasons[joint] = "negative_depth"
            continue
        xyz[joint] = fit.x
        valid[joint] = True
        errors[joint] = np.sqrt(np.mean([final_errors[i] ** 2 for i in inliers]))
        view_count[joint] = len(inliers)
        ray_angles[joint] = _ray_angle(inliers, normalized, calibrated)
        for i in available:
            per_view[i, joint] = final_errors[i]
        used[inliers, joint] = True
        reasons[joint] = "outlier_view_rejected" if len(inliers) < len(available) else "ok"
    return {"xyz": xyz, "valid": valid, "reprojection_px": errors,
            "per_view_reprojection_px": per_view, "view_count": view_count,
            "used_views": used, "ray_angle_deg": ray_angles, "reasons": reasons,
            "metric": metric, "units": "m" if metric else (units[0] if units and units[0] else "arbitrary"),
            "board_frame_id": frames[0] if frames else None}
