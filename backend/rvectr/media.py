"""Decode in display orientation, retaining the source presentation timestamps."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
import cv2
import numpy as np


def probe(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                             "-of", "json", str(path)], check=True, capture_output=True, text=True)
    info = json.loads(result.stdout)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                             "-show_frames", "-show_entries", "frame=best_effort_timestamp_time",
                             "-of", "json", str(path)], check=True, capture_output=True, text=True)
    frames = json.loads(result.stdout)["frames"]
    if any("best_effort_timestamp_time" not in f for f in frames):
        raise ValueError("Source contains frames without presentation timestamps")
    pts = np.asarray([float(f["best_effort_timestamp_time"]) for f in frames])
    if len(pts) < 2 or np.any(np.diff(pts) <= 0):
        raise ValueError("Presentation timestamps must be strictly increasing")
    audio = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    rotation = next((float(s["rotation"]) for s in video.get("side_data_list", []) if "rotation" in s), 0)
    width, height = video["width"], video["height"]
    if abs(rotation) % 180 == 90:
        width, height = height, width
    dt = np.diff(pts)
    return {"path": str(Path(path).resolve()), "coded_size": [video["width"], video["height"]],
            "image_size": [width, height], "rotation_metadata_degrees": rotation,
            "timestamp_origin": "source presentation timestamp, seconds",
            "frame_count": len(pts), "duration_s": float(pts[-1] - pts[0]),
            "median_fps": float(1 / np.median(dt)), "frame_interval_min_s": float(dt.min()),
            "frame_interval_max_s": float(dt.max()), "audio": audio,
            "pts": pts, "stream_metadata": video}


def frames(path, metadata, stride=1, start_s=0, end_s=None):
    if stride < 1:
        raise ValueError("stride must be positive")
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
    if not cap.isOpened():
        raise OSError(f"Cannot open {path}")
    decoded = 0
    try:
        for index, stamp in enumerate(metadata["pts"]):
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f"Decode ended at frame {index}, expected {len(metadata['pts'])}")
            decoded += 1
            if [frame.shape[1], frame.shape[0]] != metadata["image_size"]:
                raise ValueError("Decoder display orientation disagrees with video metadata; do not rotate twice")
            if index % stride == 0 and stamp >= start_s and (end_s is None or stamp <= end_s):
                yield index, float(stamp), frame
            if end_s is not None and stamp > end_s:
                break
    finally:
        cap.release()


def decode_audio(path, sample_rate=16000):
    result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1",
                             "-ar", str(sample_rate), "-f", "f32le", "pipe:1"],
                            check=True, capture_output=True)
    return np.frombuffer(result.stdout, dtype="<f4").copy(), sample_rate
