import hashlib
import inspect
import json

import numpy as np
import pytest

from rvectr import pipeline, pose2d
from rvectr.pipeline import DEFAULTS
from rvectr.records import sha256
from rvectr.media import probe
from .test_two_camera_pipeline import write_video, needs_ffmpeg


def pin_installed_versions(monkeypatch, rtmlib="0.0.15", onnxruntime="1.22.0"):
    """Pretend these library versions are installed, so the tests do not depend on this machine."""
    versions = {"rtmlib": rtmlib, "onnxruntime": onnxruntime}
    monkeypatch.setattr(pose2d, "_installed_version", lambda *names: versions[names[0]])


def rtmlib_cache(tmp_path, mode="balanced"):
    """A small RTMLib-style cache on disk without any video: returns (path, identity, metadata, observation)."""
    meta = {"image_size": [64, 64], "coded_size": [64, 64], "rotation_metadata_degrees": 0,
            "pts": np.arange(8) / 30}
    identity = pose2d.cache_identity("cam1", "f" * 64, meta, {**pipeline.DEFAULTS["pose"], "mode": mode})
    obs = dict(frame_index=np.arange(8), times_s=meta["pts"], keypoints=np.zeros((8, 17, 2)),
               scores=np.ones((8, 17)), joint_names=list(pose2d.JOINT_NAMES), image_size=meta["image_size"],
               source_identity=identity, detector=identity["detector"], edge_margin_fraction=.01,
               detector_settings={"mode": mode, "backend": "onnxruntime", "device_requested": "cpu",
                                  "det_frequency": 5, "rtmlib": identity["libraries"]["rtmlib"],
                                  "runtime_version": identity["libraries"]["onnxruntime"],
                                  "device_used": "cpu", "providers": ["CPUExecutionProvider"],
                                  "weights": {key: {"sha256": value, "source": "fixture-url", "file": "fixture.onnx"}
                                              for key, value in pose2d.BALANCED_WEIGHTS.items()}})
    path = tmp_path / "cam1.npz"
    pose2d.save(path, obs)
    return path, identity, meta, obs


@needs_ffmpeg
def test_same_filename_other_source_and_cache_contract(tmp_path, monkeypatch):
    pin_installed_versions(monkeypatch)
    paths = []
    for name, level in (("a", 40), ("b", 140)):
        folder = tmp_path / name
        folder.mkdir()
        path = folder / "cam1.mp4"
        write_video(path, [np.full((64, 64), level, np.uint8)] * 8, 30)
        paths.append(path)
    meta = probe(paths[0])
    identity = pose2d.cache_identity("cam1", sha256(paths[0]), meta, DEFAULTS["pose"])
    obs = dict(frame_index=np.arange(8), times_s=meta["pts"], keypoints=np.zeros((8,17,2)),
               scores=np.ones((8,17)), joint_names=list(pose2d.JOINT_NAMES), image_size=meta["image_size"],
               source_identity=identity, detector=identity["detector"], edge_margin_fraction=.01,
               detector_settings={"mode": "balanced", "backend": "onnxruntime", "device_requested": "cpu",
                                  "det_frequency": 5, "rtmlib": "0.0.15", "runtime_version": "1.22.0",
                                  "device_used": "cpu", "providers": ["CPUExecutionProvider"],
                                  "weights": {key: {"sha256": value, "source": "fixture-url", "file": "fixture.onnx"}
                                              for key, value in pose2d.BALANCED_WEIGHTS.items()}})
    cache = tmp_path / "cam1.npz"
    pose2d.save(cache, obs)
    pose2d.verified_cache(cache, identity, meta)
    for update in ({"video_sha256": sha256(paths[1])}, {"camera_id": "cam2"}, {"rotation_degrees": 180},
                   {"pose": {**identity["pose"], "stride": 2}}, {"pose": {**identity["pose"], "mode": "lightweight"}}):
        with pytest.raises(ValueError, match="Regenerate"):
            pose2d.verified_cache(cache, {**identity, **update}, meta)
    for update in ({"times_s": meta["pts"] + .002}, {"frame_index": np.arange(8)[::-1]}, {"source_identity": {}},
                   {"detector_settings": {**obs["detector_settings"], "weights": {part: {"sha256": "0" * 64}
                                                                                 for part in ("det", "pose")}}},
                   {"detector_settings": {**obs["detector_settings"], "mode": "lightweight"}}):
        pose2d.save(cache, {**obs, **update})
        with pytest.raises(ValueError, match="Regenerate"):
            pose2d.verified_cache(cache, identity, meta)

    optional = pose2d.cache_identity("cam1", sha256(paths[0]), meta, {**DEFAULTS["pose"], "mode": "lightweight"})
    saved = {**obs, "source_identity": optional, "detector_settings": {**obs["detector_settings"], "mode": "lightweight"}}
    pose2d.save(cache, saved)
    with pytest.raises(ValueError, match="weight_sha256"):
        pose2d.verified_cache(cache, optional, meta)
    pinned = {**optional, "expected_weight_sha256": pose2d.BALANCED_WEIGHTS}
    pose2d.verified_cache(cache, pinned, meta)  # policy can be supplied after the original inference
    for change in ({"runtime_version": "other"}, {"device_used": "cuda", "providers": ["CUDAExecutionProvider"]}):
        pose2d.save(cache, {**saved, "detector_settings": {**saved["detector_settings"], **change}})
        with pytest.raises(ValueError, match="Regenerate"):
            pose2d.verified_cache(cache, pinned, meta)


def test_cache_is_tied_to_the_installed_library_versions_not_to_fixed_numbers(tmp_path, monkeypatch):
    # A newer library than the one this code was first written for works when the cache was written with it.
    pin_installed_versions(monkeypatch, rtmlib="0.0.16", onnxruntime="1.23.1")
    path, identity, meta, obs = rtmlib_cache(tmp_path)
    assert identity["libraries"] == {"rtmlib": "0.0.16", "onnxruntime": "1.23.1"}
    pose2d.verified_cache(path, identity, meta)
    # Upgrading afterwards makes the cache unusable, and the message names both versions.
    pin_installed_versions(monkeypatch, rtmlib="0.0.17", onnxruntime="1.23.1")
    newer = pose2d.cache_identity("cam1", "f" * 64, meta, pipeline.DEFAULTS["pose"])
    with pytest.raises(ValueError, match=r"rtmlib version \(cache 0.0.16, installed 0.0.17\).*Regenerate"):
        pose2d.verified_cache(path, newer, meta)
    # A library that is not installed here cannot confirm the cache.
    monkeypatch.setattr(pose2d, "_installed_version", lambda *names: None)
    missing = pose2d.cache_identity("cam1", "f" * 64, meta, pipeline.DEFAULTS["pose"])
    with pytest.raises(ValueError, match="installed not installed"):
        pose2d.verified_cache(path, missing, meta)


def test_onnxruntime_version_is_read_from_the_gpu_package_when_that_is_the_one_installed(monkeypatch):
    from importlib import metadata

    def fake_version(name):
        if name == "onnxruntime-gpu":
            return "1.22.0"
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(metadata, "version", fake_version)
    assert pose2d._installed_version("onnxruntime", "onnxruntime-gpu") == "1.22.0"
    assert pose2d._installed_version("rtmlib") is None


def test_cache_from_before_format_versions_asks_to_be_regenerated(tmp_path, monkeypatch):
    pin_installed_versions(monkeypatch)
    path, identity, meta, obs = rtmlib_cache(tmp_path)
    old_identity = {k: v for k, v in identity.items() if k not in ("libraries", "cache_format_version")}
    old_identity["implementation_sha256"] = "0" * 64     # what older releases stored instead
    pose2d.save(path, {**obs, "source_identity": old_identity})
    with pytest.raises(ValueError, match=r"no format version.*Regenerate from the original videos"):
        pose2d.verified_cache(path, identity, meta)
    pose2d.save(path, {**obs, "source_identity": {**identity, "cache_format_version": 0}})
    with pytest.raises(ValueError, match=r"format version 0.*needs version 1.*Regenerate"):
        pose2d.verified_cache(path, identity, meta)


def test_cache_identity_no_longer_hashes_the_whole_pose2d_file(tmp_path, monkeypatch):
    pin_installed_versions(monkeypatch)
    path, identity, meta, obs = rtmlib_cache(tmp_path)
    assert "implementation_sha256" not in identity
    assert identity["cache_format_version"] == pose2d.CACHE_FORMAT_VERSION


# If this fails you changed how keypoints are detected. Decide whether old caches are still valid:
# if not, add 1 to pose2d.CACHE_FORMAT_VERSION; then update the hash below.
DETECTION_CODE_SHA256 = "01712bd9f8f3ac6a4f948a98a2874cd816dd902f9805792ceb0a7f2b8c58b864"


def test_changing_the_detection_code_is_a_reminder_to_review_the_cache_format_version():
    source = "".join(inspect.getsource(part) for part in (pose2d.RTMLibDetector, pose2d.choose_person,
                                                          pose2d.detect_video))
    assert hashlib.sha256(source.encode()).hexdigest() == DETECTION_CODE_SHA256, \
        "detection code changed: review pose2d.CACHE_FORMAT_VERSION and update DETECTION_CODE_SHA256"


def fake_detection(monkeypatch):
    """Replace the real detector so _detect can run without models or video; returns nothing."""
    class FakeDetector:
        name = pose2d.RTMLibDetector.name
        settings = {"weights": {part: {"sha256": digest} for part, digest in pose2d.BALANCED_WEIGHTS.items()}}

        def __init__(self, *args):
            self.model = type("Model", (), {"reset": staticmethod(lambda: None)})()

    def fake_detect_video(path, info, detector, stride=1, progress=None, edge_margin_fraction=0.01):
        return {"frame_index": np.arange(2), "times_s": np.arange(2) / 30.0, "keypoints": np.zeros((2, 17, 2)),
                "scores": np.ones((2, 17)), "detector": detector.name, "detector_settings": detector.settings}

    monkeypatch.setattr(pose2d, "RTMLibDetector", FakeDetector)
    monkeypatch.setattr(pose2d, "detect_video", fake_detect_video)


@pytest.mark.parametrize("pose_section, source, logged", [({}, "default", True),
                                                          ({"device": "cpu"}, "config", False)])
def test_default_pose_device_is_logged_and_saved_with_the_cache(tmp_path, monkeypatch, pose_section, source, logged):
    fake_detection(monkeypatch)
    session = tmp_path / "session.json"
    session.write_text(json.dumps({"pose": pose_section, "cameras": [{"id": "cam1", "video": "a.mp4"},
                                                                       {"id": "cam2", "video": "b.mp4"}]}))
    config = pipeline.load_session(session)
    assert config["pose"]["device"] == "cpu" and config["pose"]["device_source"] == source
    meta = {"sha256": "f" * 64, "image_size": [64, 64], "coded_size": [64, 64], "rotation_metadata_degrees": 0,
            "frame_count": 2}
    messages = []
    run = tmp_path / "run"
    observations = pipeline._detect(config, [tmp_path / "a.mp4", tmp_path / "b.mp4"], [meta, meta], run,
                                    progress=messages.append)
    assert any("pose.device is not set" in message and "'cpu'" in message for message in messages) is logged
    assert all(obs["detector_settings"]["device_source"] == source for obs in observations)
    saved = pose2d.load(run / "keypoints2d" / "cam1.npz")
    assert saved["detector_settings"]["device_source"] == source and saved["detector_settings"]["weights"]
