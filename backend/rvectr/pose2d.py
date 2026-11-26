"""2D body keypoints per video frame (COCO-17 order, pixels in the displayed frame).

The default detector is RTMPose through RTMLib and ONNX Runtime. Detector
scores are clipped to [0, 1] for triangulation weighting; they are model
confidence values, not measured position error. A frame without a person keeps
NaN coordinates and zero scores: nothing is copied forward from earlier frames.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from .kinematics import JOINT_NAMES
from .media import frames

JOINTS = len(JOINT_NAMES)

# Used when the session config does not set pose.device. Live detection records whether the
# device came from the config or from this default (detector_settings["device_source"]).
DEFAULT_DEVICE = "cpu"

# Bump this when a change to RTMLibDetector, choose_person or detect_video, or to what a cache
# holds, would change the saved keypoints. Caches with another number must be regenerated.
# Other edits to this file leave existing caches valid; a test fails if the detection code changes.
CACHE_FORMAT_VERSION = 1


# ONNX file digests from the published balanced RTMLib 0.0.15 archives.
BALANCED_WEIGHTS = {
    "det": "3dea6513388889f0fff4b77bf7a26013600321b9eb9ceb0e9a400a82572f5f23",
    "pose": "5c0a4bf67953e6d2ac43ce15e77dc9d5d354ae18430a47d2c5963a7bc5683e3c",
}


class RTMLibDetector:
    name = "rtmlib.Body (YOLOX + RTMPose, COCO-17)"

    def __init__(self, mode="balanced", device=DEFAULT_DEVICE, backend="onnxruntime", det_frequency=5):
        """det_frequency: run the person detector every N frames; between those, the
        box comes from the previous frame's keypoints. 1 = detect on every frame."""
        try:
            from rtmlib import Body, PoseTracker
        except ImportError as error:
            raise RuntimeError("RTMLib is not installed. Run bash tools/bootstrap-linux.sh --pose (add --cuda for GPU inference)") from error
        if device == "cuda" and backend == "onnxruntime":
            import onnxruntime
            try:  # use CUDA/cuDNN from the project's pip packages (uv sync --extra cuda) if present
                onnxruntime.preload_dlls()
            except Exception:
                pass
        self.model = PoseTracker(Body, det_frequency=det_frequency, tracking=False, mode=mode,
                                 to_openpose=False, backend=backend, device=device)
        from importlib.metadata import version
        from .records import sha256
        weights = {name: {"file": Path(part.onnx_model).name, "sha256": sha256(part.onnx_model),
                          "source": Body.MODE[mode][name]}
                   for name, part in (("det", self.model.det_model), ("pose", self.model.pose_model))}
        providers = []
        for part in (getattr(self.model, "det_model", None), getattr(self.model, "pose_model", None)):
            session = getattr(part, "session", None)
            if hasattr(session, "get_providers"):
                providers += [p for p in session.get_providers() if p not in providers]
        actual = "cuda" if "CUDAExecutionProvider" in providers else ("cpu" if providers else "unknown")
        self.settings = {"weights": weights, "rtmlib": version("rtmlib"), "mode": mode, "device_requested": device, "device_used": actual,
                         "providers": providers, "backend": backend, "det_frequency": det_frequency}
        if backend == "onnxruntime":
            import onnxruntime
            self.settings["runtime_version"] = onnxruntime.__version__
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


def _installed_version(*distributions):
    """Version of the first of these installed packages (importlib.metadata), or None if none is installed."""
    from importlib.metadata import PackageNotFoundError, version
    for name in distributions:
        try:
            return version(name)
        except PackageNotFoundError:
            continue
    return None


def _version_note(name, saved, installed):
    return f"{name} version (cache {saved}, installed {installed or 'not installed'})"


def cache_identity(camera_id, video_sha256, metadata, settings):
    """Inputs used to generate a full-take observation cache, excluding later scoring settings."""
    detector = settings.get("source", RTMLibDetector.name)
    return {
        "schema": 1, "camera_id": camera_id, "video_sha256": video_sha256,
        "image_size": list(metadata["image_size"]), "coded_size": list(metadata["coded_size"]),
        "rotation_degrees": metadata["rotation_metadata_degrees"],
        "detector": detector,
        "pose": {key: settings[key] for key in ("mode", "backend", "device", "det_frequency", "stride")},
        "edge_margin_fraction": settings.get("edge_margin_fraction", 0.01),
        "expected_weight_sha256": (settings.get("weight_sha256") or
                                   (BALANCED_WEIGHTS if settings["mode"] == "balanced" else {}))
                                  if detector == RTMLibDetector.name else {},
        # The library versions installed now, not fixed numbers: a cache is only reused with the
        # versions that wrote it.
        "libraries": ({"rtmlib": _installed_version("rtmlib"),
                       "onnxruntime": _installed_version("onnxruntime", "onnxruntime-gpu")}
                      if detector == RTMLibDetector.name else {}),
        "cache_format_version": CACHE_FORMAT_VERSION,
    }


def verified_cache(path, identity, metadata):
    """Validate the embedded source identity and the actual saved sample arrays."""
    try:
        obs = load(path)
    except (OSError, ValueError, KeyError) as exc:
        raise ValueError(f"Unreadable keypoint cache {path.name}; rerun without --keypoints-from") from exc
    source = obs.get("source_identity", {})
    saved_format = source.get("cache_format_version")
    if saved_format != identity["cache_format_version"]:
        found = "no format version (an older release wrote it)" if saved_format is None else f"format version {saved_format}"
        raise ValueError(f"Keypoint cache {path.name} has {found}; this release needs version "
                         f"{identity['cache_format_version']}. Regenerate from the original videos without --keypoints-from.")
    # A model digest pin is verification policy, and may be added after inference.
    # The saved weight digests are compared with the requested pins below.
    mismatch = [key for key, expected in identity.items()
                if key != "expected_weight_sha256" and source.get(key) != expected]
    stride = identity["pose"]["stride"]
    pts = np.asarray(metadata["pts"])
    indices = np.arange(len(pts))[::stride]
    indices = indices[pts[indices] >= 0]  # detect_video's full-take default start_s
    if not np.array_equal(obs["frame_index"], indices) or not np.array_equal(obs["times_s"], pts[indices]):
        mismatch.append("frame indices or source timestamps")
    if (obs["keypoints"].shape != (len(indices), JOINTS, 2) or obs["scores"].shape != (len(indices), JOINTS)
            or obs.get("joint_names") != list(JOINT_NAMES) or obs.get("image_size") != identity["image_size"]
            or obs.get("detector") != identity["detector"]):
        mismatch.append("detector, display size or joint layout")
    if identity["detector"] == RTMLibDetector.name:
        actual = obs.get("detector_settings", {})
        for key, saved_key in (("mode", "mode"), ("device", "device_requested"),
                               ("backend", "backend"), ("det_frequency", "det_frequency")):
            if actual.get(saved_key) != identity["pose"][key]:
                mismatch.append("detector setting " + key)
        if obs.get("edge_margin_fraction") != identity["edge_margin_fraction"]:
            mismatch.append("detector edge margin")
        installed = identity["libraries"]
        if actual.get("rtmlib") is None or actual.get("rtmlib") != installed.get("rtmlib"):
            mismatch.append(_version_note("rtmlib", actual.get("rtmlib"), installed.get("rtmlib")))
        if actual.get("backend") == "onnxruntime":
            providers = actual.get("providers", [])
            used = "cuda" if "CUDAExecutionProvider" in providers else "cpu" if "CPUExecutionProvider" in providers else None
            if actual.get("runtime_version") is None or actual.get("runtime_version") != installed.get("onnxruntime"):
                mismatch.append(_version_note("onnxruntime", actual.get("runtime_version"), installed.get("onnxruntime")))
            if not used or used != actual.get("device_used"):
                mismatch.append("ONNX runtime providers")
            if used != identity["pose"]["device"]:
                mismatch.append("actual inference device differs from requested device")
        if set(identity["expected_weight_sha256"]) != {"det", "pose"}:
            mismatch.append("set pose.weight_sha256.det and .pose to independently verified ONNX digests")
        for part in ("det", "pose"):
            weight = actual.get("weights", {}).get(part, {})
            digest = weight.get("sha256", "")
            expected = identity["expected_weight_sha256"].get(part)
            if (not re.fullmatch(r"[0-9a-f]{64}", digest) or not weight.get("file") or not weight.get("source")
                    or digest != expected):
                mismatch.append(part + " weight provenance")
    if mismatch:
        raise ValueError(f"Incompatible or unverifiable {path.name} ({', '.join(mismatch)}). "
                         "Regenerate from the original videos without --keypoints-from.")
    return obs
