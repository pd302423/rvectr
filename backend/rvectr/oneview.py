"""Locating a point with ONE camera, by assuming which plane it moves in.

A camera does not see distance. Each pixel gives a ray: a straight line from the
camera centre through that pixel and on into the room. Two cameras give two rays
that cross at the point. One camera gives only the ray, so we add an assumption:
"the pelvis moves in this flat, vertical plane". The point is then where the ray
meets the plane. If the assumption is wrong, the point is wrong, and that is
exactly what the comparison of one view against several views measures.

Everything is in the calibration (board) frame, in metres. Missing results are
NaN and are never filled in.
"""
from __future__ import annotations

import cv2
import numpy as np

from .geometry import _camera

# A ray that runs almost along the plane meets it at an unstable, far-away spot.
MIN_RAY_PLANE_ANGLE_DEG = 5.0


def camera_centre(camera):
    """Where the camera is, in the board frame (R and t map board to camera: X_cam = R X + t)."""
    return _camera(camera)["center"]


def camera_centre_and_rays(points2d, camera):
    """Camera centre [3] and unit ray directions [..., 3] for pixels [..., 2].

    Lens distortion is removed first (the pixel is where the ray would be with a
    perfect lens). Pixels that are NaN give NaN rays.
    """
    cam = _camera(camera)
    pixels = np.asarray(points2d, float)
    flat = pixels.reshape(-1, 2)
    rays = np.full((len(flat), 3), np.nan)
    seen = np.isfinite(flat).all(axis=1)
    if seen.any():
        # Many iterations and a tiny tolerance: the default of 5 iterations is not exact for strong distortion.
        criteria = (cv2.TERM_CRITERIA_COUNT + cv2.TERM_CRITERIA_EPS, 100, 1e-12)
        flat_seen = np.ascontiguousarray(flat[seen]).reshape(-1, 1, 2)
        normalised = cv2.undistortPointsIter(flat_seen, cam["K"], cam["distortion"], None, None,
                                             criteria).reshape(-1, 2)
        # In the camera frame the ray is (x, y, 1). R.T turns it into board-frame directions.
        direction = np.column_stack([normalised, np.ones(len(normalised))]) @ cam["R"]
        rays[seen] = direction / np.linalg.norm(direction, axis=1, keepdims=True)
    return cam["center"], rays.reshape(pixels.shape[:-1] + (3,))


def _horizontal(vector, up):
    """The part of a vector that lies flat (perpendicular to up), as a unit vector."""
    up = np.asarray(up, float)
    up = up / np.linalg.norm(up)
    vector = np.asarray(vector, float)
    flat = vector - (vector @ up) * up
    length = np.linalg.norm(flat)
    if not np.isfinite(length) or length < 1e-9:
        raise ValueError("The direction has no horizontal part, so it cannot define a vertical plane")
    return flat / length


def movement_plane(kind, standing_point, up, camera_centre=None, hip_line=None):
    """A vertical plane through the standing spot, as (point, unit normal).

    kind="fixed_distance": the plane faces the camera. Its normal is the flat
        part of the line from the standing spot to the camera. Assumes the
        person never moves towards or away from the camera.
    kind="movement_plane": the plane the person moves in (forwards, backwards,
        up, down). Its normal points along the hip line, from the left hip to
        the right hip, because stepping sideways is the one thing not allowed.
    """
    point = np.asarray(standing_point, float).reshape(3)
    if kind == "fixed_distance":
        if camera_centre is None:
            raise ValueError("fixed_distance needs the camera centre")
        return point, _horizontal(np.asarray(camera_centre, float) - point, up)
    if kind == "movement_plane":
        if hip_line is None:
            raise ValueError("movement_plane needs the hip line")
        return point, _horizontal(hip_line, up)
    raise ValueError("kind must be 'fixed_distance' or 'movement_plane'")


def reconstruct_one_view(points2d, confidence, camera, plane_point, plane_normal, min_confidence=0.3):
    """Place each joint where its camera ray meets the plane.

    points2d [F,J,2], confidence [F,J] -> xyz [F,J,3] and valid [F,J].
    A joint is invalid (NaN) when its confidence is too low, when the ray runs
    nearly along the plane, or when the meeting point would be behind the camera.
    """
    points2d = np.asarray(points2d, float)
    confidence = np.asarray(confidence, float)
    normal = np.asarray(plane_normal, float)
    normal = normal / np.linalg.norm(normal)
    centre, rays = camera_centre_and_rays(points2d, camera)
    with np.errstate(invalid="ignore", divide="ignore"):
        # Ray: centre + s * ray. Plane: normal . (X - plane_point) = 0. Solve for s.
        slope = rays @ normal                          # how squarely the ray hits the plane
        distance = normal @ (np.asarray(plane_point, float) - centre)
        s = distance / slope
        confident = np.isfinite(confidence) & (confidence >= min_confidence) & (confidence > 0)
        valid = (confident & np.isfinite(rays).all(axis=-1)
                 & (np.abs(slope) >= np.sin(np.radians(MIN_RAY_PLANE_ANGLE_DEG)))
                 & (s > 1e-6))                          # s > 0: in front of the camera
    xyz = np.full(points2d.shape[:-1] + (3,), np.nan)
    xyz[valid] = centre + s[valid][:, None] * rays[valid]
    return xyz, valid
