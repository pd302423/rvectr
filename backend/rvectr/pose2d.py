"""2D body keypoints per video frame (COCO-17 order, pixels in the displayed frame).

The default detector is RTMPose through RTMLib and ONNX Runtime. Detector
scores are clipped to [0, 1] for triangulation weighting; they are model
confidence values, not measured position error. A frame without a person keeps
NaN coordinates and zero scores: nothing is copied forward from earlier frames.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .kinematics import JOINT_NAMES
from .media import frames

JOINTS = len(JOINT_NAMES)


class RTMLibDetector:
    name = "rtmlib.Body (YOLOX + RTMPose, COCO-17)"

    def __init__(self, mode="balanced", device="cuda", backend="onnxruntime", det_frequency=5):
        """det_frequency: run the person detector every N frames; between those, the
        box comes from the previous frame's keypoints. 1 = detect on every frame."""
        try:
            from rtmlib import Body, PoseTracker
        except ImportError as error:
            raise RuntimeError("RTMLib is not installed. Run: uv sync --frozen --extra pose") from error
        if device == "cuda" and backend == "onnxruntime":
            import onnxruntime
            try:  # use CUDA/cuDNN from the project's pip packages (uv sync --extra cuda) if present
                onnxruntime.preload_dlls()
            except Exception:
                pass
        self.model = PoseTracker(Body, det_frequency=det_frequency, tracking=False, mode=mode,
                                 to_openpose=False, backend=backend, device=device)
        providers = []
        for part in (getattr(self.model, "det_model", None), getattr(self.model, "pose_model", None)):
            session = getattr(part, "session", None)
            if session is not None:
                providers += [p for p in session.get_providers() if p not in providers]
        actual = "cuda" if "CUDAExecutionProvider" in providers else ("cpu" if providers else "unknown")
        self.settings = {"mode": mode, "device_requested": device, "device_used": actual,
                         "providers": providers, "backend": backend, "det_frequency": det_frequency}
        if device == "cuda" and actual != "cuda":
            print("WARNING: GPU pose inference unavailable (needs CUDA 12 + cuDNN 9 libraries); "
                  "running on CPU. `uv sync --frozen --extra cuda --extra pose` installs them.", flush=True)

    def __call__(self, frame):
        keypoints, scores = self.model(frame)
        keypoints = np.asarray(keypoints, dtype=np.float64).reshape(-1, JOINTS, 2)
        scores = np.asarray(scores, dtype=np.float64).reshape(-1, JOINTS)
        return keypoints, scores


def choose_person(keypoints, scores, previous_center, image_diagonal):
    """Follow one person: nearest to the last choice, else the largest confident body."""
    if len(keypoints) == 0:
        return None
    good = scores > 0.3
    centers, areas = [], []
    for kp, ok in zip(keypoints, good):
        pts = kp[ok] if ok.sum() >= 3 else kp
        centers.append(pts.mean(axis=0))
        span = np.ptp(pts, axis=0)
        areas.append(float(span[0] * span[1]) * float(ok.mean()))
    centers = np.asarray(centers)
    if previous_center is not None:
        distance = np.linalg.norm(centers - previous_center, axis=1)
        nearest = int(np.argmin(distance))
        if distance[nearest] < 0.25 * image_diagonal:
            return nearest
    return int(np.argmax(areas))


def detect_video(path, metadata, detector, stride=1, start_s=0.0, end_s=None, progress=None,
                 edge_margin_fraction=0.01):
    width, height = metadata["image_size"]
    diagonal = float(np.hypot(width, height))
    indices, times, points, confidence = [], [], [], []
    previous = None
    for index, stamp, frame in frames(path, metadata, stride=stride, start_s=start_s, end_s=end_s):
        keypoints, scores = detector(frame)
        choice = choose_person(keypoints, scores, previous, diagonal)
        if choice is None:
            kp, sc = np.full((JOINTS, 2), np.nan), np.zeros(JOINTS)
        else:
            kp, sc = keypoints[choice].copy(), np.clip(scores[choice], 0, 1)
            # The model guesses joints beyond the picture (often on the border) with real-looking
            # scores. Treat anything on or past the edge as unobserved.
            margin = edge_margin_fraction * np.array([width, height])
            outside = ((kp < margin) | (kp > np.array([width, height]) - margin)).any(axis=1)
            sc[outside] = 0.0
            previous = kp[sc > 0.3].mean(axis=0) if (sc > 0.3).sum() >= 3 else kp.mean(axis=0)
        indices.append(index)
        times.append(stamp)
        points.append(kp)
        confidence.append(sc)
        if progress:
            progress(index, stamp)
    return {"frame_index": np.asarray(indices), "times_s": np.asarray(times),
            "keypoints": np.asarray(points).reshape(-1, JOINTS, 2),
            "scores": np.asarray(confidence).reshape(-1, JOINTS),
            "image_size": list(metadata["image_size"]), "joint_names": JOINT_NAMES,
            "detector": getattr(detector, "name", type(detector).__name__),
            "detector_settings": getattr(detector, "settings", {}),
            "edge_margin_fraction": edge_margin_fraction}


def save(path, observation):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {k: v for k, v in observation.items() if not isinstance(v, np.ndarray)}
    np.savez_compressed(path, frame_index=observation["frame_index"], times_s=observation["times_s"],
                        keypoints=observation["keypoints"], scores=observation["scores"],
                        meta=json.dumps(meta))


def load(path):
    with np.load(path, allow_pickle=False) as data:
        observation = {k: data[k] for k in ("frame_index", "times_s", "keypoints", "scores")}
        observation.update(json.loads(str(data["meta"])))
    return observation
