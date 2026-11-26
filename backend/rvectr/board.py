"""Checkerboard detection in video and calibration records built from it.

Board frame (metres): corner 0 is the origin, X runs along a row of inner
corners, Y runs from row to row, Z = X x Y. Detected corners are put in a fixed
order: the first corner is the one nearest the top-left of the image. For a
level board this is a candidate orientation. Check the saved origin and axis
overlays against an asymmetric physical mark on the same board in every view.

Board sizes are given as printed SQUARES (for example 8x11). OpenCV works with
INNER corners, which is one fewer in each direction (7x10).
"""
from __future__ import annotations

import cv2
import numpy as np

from .calibration import calibrate_extrinsics, calibrate_intrinsics
from .media import frames, probe


def parse_squares(text):
    """'8x11' printed squares -> (cols, rows) inner corners, e.g. (10, 7)."""
    try:
        a, b = (int(v) for v in str(text).lower().replace("×", "x").split("x"))
    except ValueError as error:
        raise ValueError("Board size must look like 8x11 (printed squares)") from error
    if min(a, b) < 3:
        raise ValueError("Each board side needs at least 3 squares")
    if a == b:
        raise ValueError("A square board (equal sides) has an ambiguous orientation; use a rectangular board")
    inner = sorted((a - 1, b - 1))
    return inner[1], inner[0]


def object_points(pattern, square_m):
    cols, rows = pattern
    if not np.isfinite(square_m) or not 0.005 <= square_m <= 0.5:
        raise ValueError("Square size must be a measured value between 5 mm and 500 mm")
    grid = np.array([[c * square_m, r * square_m, 0.0] for r in range(rows) for c in range(cols)])
    return grid


def canonical_order(corners):
    """Resolve OpenCV's 180-degree ambiguity: first corner nearest the image top-left."""
    corners = np.asarray(corners, dtype=np.float64).reshape(-1, 2)
    diagonal = corners[-1] - corners[0]
    return corners[::-1].copy() if diagonal.sum() < 0 else corners


def detect(frame, pattern, precheck_width=960):
    """Return ordered corners [N,2] in full-resolution pixels, or None.

    A fast check on a reduced copy rejects frames without a board; the accurate
    sector-based detector then runs on the full-resolution frame.
    """
    gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    scale = min(1.0, precheck_width / gray.shape[1])
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else gray
    found, _ = cv2.findChessboardCorners(small, pattern, flags=cv2.CALIB_CB_ADAPTIVE_THRESH |
                                         cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_FAST_CHECK)
    if not found:
        return None
    found, corners = cv2.findChessboardCornersSB(gray, pattern, flags=cv2.CALIB_CB_NORMALIZE_IMAGE |
                                                 cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY)
    if not found:
        return None
    return canonical_order(corners)


def sharpness(gray, pattern, corners):
    """Mean edge width in pixels around the corners (lower is sharper)."""
    try:
        value = cv2.estimateChessboardSharpness(gray, pattern, corners.reshape(-1, 1, 2).astype(np.float32))
        return float(value[0][0])
    except cv2.error:
        return float("nan")


def view_features(corners, pattern, image_size):
    """Position, size and perspective of one board view, for picking diverse views."""
    cols, rows = pattern
    grid = corners.reshape(rows, cols, 2)
    width, height = image_size
    top, bottom = np.linalg.norm(grid[0, -1] - grid[0, 0]), np.linalg.norm(grid[-1, -1] - grid[-1, 0])
    left, right = np.linalg.norm(grid[-1, 0] - grid[0, 0]), np.linalg.norm(grid[-1, -1] - grid[0, -1])
    area = cv2.contourArea(np.array([grid[0, 0], grid[0, -1], grid[-1, -1], grid[-1, 0]], dtype=np.float32))
    center = corners.mean(axis=0) / [width, height]
    return np.array([center[0], center[1], 0.5 * np.log(max(area, 1) / (width * height)),
                     3 * np.log(top / bottom), 3 * np.log(left / right)])


def select_diverse(features, count):
    """Greedy farthest-point choice; returns indices in time order."""
    features = np.asarray(features)
    if len(features) <= count:
        return list(range(len(features)))
    spread = features.std(axis=0)
    scaled = features / np.where(spread > 1e-9, spread, 1)
    chosen = [int(np.argmin(np.linalg.norm(scaled - scaled.mean(axis=0), axis=1)))]
    distance = np.linalg.norm(scaled - scaled[chosen[0]], axis=1)
    while len(chosen) < count:
        index = int(np.argmax(distance))
        chosen.append(index)
        distance = np.minimum(distance, np.linalg.norm(scaled - scaled[index], axis=1))
    return sorted(chosen)


def scan_video(path, pattern, stride=6, start_s=0.0, end_s=None, max_edge_px=3.0, progress=None):
    """Detect the board through a video; returns metadata and per-frame detections."""
    metadata = probe(path)
    detections = []
    for index, stamp, frame in frames(path, metadata, stride=stride, start_s=start_s, end_s=end_s):
        corners = detect(frame, pattern)
        if corners is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edge = sharpness(gray, pattern, corners)
        if np.isfinite(edge) and edge > max_edge_px:
            continue
        detections.append({"frame_index": index, "time_s": stamp, "corners": corners, "edge_width_px": edge})
        if progress:
            progress(index, stamp, len(detections))
    return metadata, detections


def intrinsics_from_video(path, squares, square_mm, camera_id, stride=6, max_views=30, progress=None):
    """Lens calibration from a video of the board moved and tilted around the frame."""
    pattern = parse_squares(squares)
    obj = object_points(pattern, square_mm / 1000.0)
    metadata, detections = scan_video(path, pattern, stride=stride, progress=progress)
    size = metadata["image_size"]
    if len(detections) < 10:
        result = {"status": "failed", "reason": "too_few_sharp_board_views",
                  "quality": {"detected_views": len(detections)}}
    else:
        features = [view_features(d["corners"], pattern, size) for d in detections]
        picked = [detections[i] for i in select_diverse(features, max_views)]
        observations = [{"corners": d["corners"], "object_points": obj, "image_size": size,
                         "source": f"{metadata['path']}#t={d['time_s']:.3f}"} for d in picked]
        result = calibrate_intrinsics(observations, image_size=size)
        result.setdefault("quality", {})["detected_views"] = len(detections)
    result.update({"camera_id": camera_id, "kind": "intrinsics", "image_size": size,
                   "board": {"squares": squares, "inner_corners": list(pattern), "square_mm": square_mm},
                   "video": {"path": metadata["path"], "median_fps": metadata["median_fps"],
                             "coded_size": metadata["coded_size"]}})
    return result


def up_axis(R, t, placement):
    """World 'up' as a board axis, from where the camera is (board assumed level)."""
    R, t = np.asarray(R, float), np.asarray(t, float).reshape(3)
    if placement == "floor":
        center = -R.T @ t
        return [0.0, 0.0, float(np.sign(center[2]) or 1.0)]
    if placement != "upright":
        raise ValueError("Board placement must be 'upright' or 'floor'")
    camera_up = R.T @ np.array([0.0, -1.0, 0.0])
    axis = int(np.argmax(np.abs(camera_up[:2])))
    up = [0.0, 0.0, 0.0]
    up[axis] = float(np.sign(camera_up[axis]))
    return up


def extrinsics_from_video(path, intrinsics, squares, square_mm, board_frame_id, start_s, end_s,
                          placement="upright", max_corner_motion_px=1.5, recording_mode_verified=False, overlay_path=None):
    """Camera position in the shared board frame, from a still board held in [start_s, end_s].

    Every camera must see the same board, in the same place, during its window.
    Because the board is still, the cameras do not need to be synchronized here.
    """
    if intrinsics.get("status") != "passed":
        raise ValueError("Intrinsics must pass their quality checks first")
    pattern = parse_squares(squares)
    obj = object_points(pattern, square_mm / 1000.0)
    metadata, detections = scan_video(path, pattern, stride=1, start_s=start_s, end_s=end_s)
    if list(metadata["image_size"]) != list(intrinsics["image_size"]):
        raise ValueError("This video's frame size differs from the intrinsics video; recalibrate in this mode")
    base = {"camera_id": intrinsics.get("camera_id"), "kind": "camera", "image_size": metadata["image_size"],
            "board": {"squares": squares, "inner_corners": list(pattern), "square_mm": square_mm,
                      "placement": placement},
            "extrinsics_video": {"path": metadata["path"], "window_s": [start_s, end_s]}}
    if len(detections) < 3:
        return {**base, "status": "failed", "reason": "board_not_found_in_window",
                "quality": {"frames_with_board": len(detections)}}
    if overlay_path is not None:
        sample = detections[len(detections) // 2]
        frame_iter = frames(path, metadata, start_s=sample["time_s"], end_s=sample["time_s"])
        try:
            _, _, overlay = next(frame_iter)
        finally:
            frame_iter.close()
        corners = np.rint(sample["corners"]).astype(int)
        origin = tuple(corners[0])
        for index, label, color in ((pattern[0]-1, "+X", (0, 0, 255)),
                                    (-pattern[0], "+Y", (0, 255, 0))):
            tip = tuple(corners[index])
            cv2.arrowedLine(overlay, origin, tip, color, 3)
            cv2.putText(overlay, label, tip, cv2.FONT_HERSHEY_SIMPLEX, .8, color, 2)
        cv2.circle(overlay, origin, 6, (255, 0, 255), 2)
        cv2.putText(overlay, "0", origin, cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 0, 255), 2)
        overlay_path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(overlay_path), overlay):
            raise OSError("Could not save the checkerboard orientation overlay")
        base["corner_overlay"] = {"file": overlay_path.name, "frame_index": sample["frame_index"],
                                  "review": "Compare corner 0 and both axes to physical marks in every view"}
    stack = np.stack([d["corners"] for d in detections])
    motion = float(np.max(np.linalg.norm(stack - np.median(stack, axis=0), axis=2)))
    if motion > max_corner_motion_px:
        return {**base, "status": "failed", "reason": "board_or_camera_moved_during_window",
                "quality": {"frames_with_board": len(detections), "max_corner_motion_px": motion}}
    corners = np.median(stack, axis=0)
    result = calibrate_extrinsics(intrinsics["K"], intrinsics["distortion"], corners, obj,
                                  board_frame_id=board_frame_id, image_size=metadata["image_size"])
    result.update(base)
    result["quality"].update({"frames_with_board": len(detections), "max_corner_motion_px": motion})
    result["intrinsics_quality"] = intrinsics.get("quality", {})
    result["intrinsics_sources"] = intrinsics.get("sources", [])
    if result["status"] == "passed":
        result["up_axis_board"] = up_axis(result["R"], result["t"], placement)
    result["recording_mode_verified"] = bool(recording_mode_verified)
    result["recording_mode_note"] = ("Confirmed by the operator: same phone, lens, resolution, orientation, "
                                     "zoom and stabilization as the intrinsics and exercise videos"
                                     if recording_mode_verified else
                                     "Not confirmed; rerun with --same-recording-mode once checked")
    return result
