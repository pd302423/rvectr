import numpy as np
import pytest

from rvectr import pose2d
from rvectr.pipeline import DEFAULTS
from rvectr.records import sha256
from rvectr.media import probe
from .test_two_camera_pipeline import write_video, needs_ffmpeg


@needs_ffmpeg
def test_same_filename_other_source_and_cache_contract(tmp_path):
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
