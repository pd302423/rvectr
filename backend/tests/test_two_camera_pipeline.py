"""Synthetic end-to-end checks of the two-camera squat pipeline.

Everything here is generated: rendered checkerboards, simulated light pulses
and a simulated squatting skeleton seen by two virtual cameras. Passing shows
the software recovers known answers; it says nothing about real-phone accuracy.
"""
import json
import shutil
import subprocess

import cv2
import numpy as np
import pytest

from rvectr import board, flashsync, pose2d, squat
from rvectr.calibration import calibrate_extrinsics
from rvectr.paths import RuntimePaths
from rvectr.pipeline import measure_points, measure_squats, reconstruct_sequence, run_session

SQUARE_M = 0.06
HIPS = [11, 12]
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


# ----------------------------------------------------------------------------- helpers
def look_at(center, target, down=(0, 1, 0)):
    center, target = np.asarray(center, float), np.asarray(target, float)
    z = target - center
    z /= np.linalg.norm(z)
    x = np.cross(down, z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.vstack([x, y, z])
    return R, -R @ center


def intrinsic(width, height, focal):
    return np.array([[focal, 0, width / 2], [0, focal, height / 2], [0, 0, 1.0]])


def render_board(K, R, t, size, squares=(11, 8), square_m=SQUARE_M, background=150):
    pixels, border = 40, 1
    W, H = (squares[0] + 2 * border) * pixels, (squares[1] + 2 * border) * pixels
    pattern = np.full((H, W), 255, np.uint8)
    for r in range(squares[1]):
        for c in range(squares[0]):
            if (r + c) % 2 == 0:
                y0, x0 = (border + r) * pixels, (border + c) * pixels
                pattern[y0:y0 + pixels, x0:x0 + pixels] = 0
    origin = (border + 1) * pixels - 0.5  # first inner corner, pixel-centre convention
    scale = square_m / pixels
    to_board = np.array([[scale, 0, -origin * scale], [0, scale, -origin * scale], [0, 0, 1]])
    homography = K @ np.column_stack([R[:, 0], R[:, 1], t]) @ to_board
    image = cv2.warpPerspective(pattern, homography, size, flags=cv2.INTER_LINEAR, borderValue=background)
    return cv2.GaussianBlur(image, (3, 3), 0.7)


def write_video(path, frames, fps):
    height, width = frames[0].shape[:2]
    process = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray",
                                "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-c:v", "libx264",
                                "-crf", "8", "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)
    for frame in frames:
        process.stdin.write(np.ascontiguousarray(frame, dtype=np.uint8).tobytes())
    process.stdin.close()
    assert process.wait() == 0


def project(points, K, R, t):
    return cv2.projectPoints(np.asarray(points, float).reshape(-1, 3), cv2.Rodrigues(R)[0], t, K,
                             np.zeros(5))[0].reshape(-1, 2)


# ----------------------------------------------------------------------------- board
def test_square_counts_become_inner_corners():
    assert board.parse_squares("8x11") == (10, 7)
    assert board.parse_squares("11×8") == (10, 7)
    with pytest.raises(ValueError):
        board.parse_squares("8x8")


def test_rendered_board_is_found_in_a_fixed_order():
    K = intrinsic(1280, 720, 1000)
    R = cv2.Rodrigues(np.array([0.15, -0.3, 0.05]))[0]
    t = np.array([-0.3, -0.2, 1.4])
    image = render_board(K, R, t, (1280, 720))
    corners = board.detect(image, (10, 7))
    expected = project(board.object_points((10, 7), SQUARE_M), K, R, t)
    assert corners is not None
    assert np.abs(corners - expected).max() < 0.5
    rotated = board.canonical_order(corners[::-1])
    np.testing.assert_allclose(rotated, corners)


@needs_ffmpeg
def test_intrinsics_and_extrinsics_from_rendered_videos(tmp_path):
    size, K = (1280, 720), intrinsic(1280, 720, 1000)
    rng = np.random.default_rng(4)
    obj = board.object_points((10, 7), SQUARE_M)
    frames = []
    while len(frames) < 40:
        R = cv2.Rodrigues(rng.uniform([-0.6, -0.6, -0.15], [0.6, 0.6, 0.15]))[0]
        t = np.array([rng.uniform(-0.45, 0.05), rng.uniform(-0.3, -0.05), rng.uniform(0.9, 1.7)])
        pts = project(obj, K, R, t)
        if pts.min() < 30 or pts[:, 0].max() > size[0] - 30 or pts[:, 1].max() > size[1] - 30:
            continue
        frames.append(render_board(K, R, t, size))
    write_video(tmp_path / "intrinsics.mp4", frames, 30)
    result = board.intrinsics_from_video(tmp_path / "intrinsics.mp4", "8x11", SQUARE_M * 1000, "cam1", stride=1)
    assert result["status"] == "passed", result.get("reason")
    np.testing.assert_allclose(np.asarray(result["K"])[[0, 1, 0, 1], [0, 1, 2, 2]], [1000, 1000, 640, 360], rtol=0.02, atol=6)

    # The same board, still and upright, seen by a camera standing to its front-left.
    R_true, t_true = look_at([-1.2, -0.1, -2.0], [0.3, 0.2, 0.0])
    still = [render_board(K, R_true, t_true, size)] * 20
    write_video(tmp_path / "extrinsics.mp4", still, 30)
    camera = board.extrinsics_from_video(tmp_path / "extrinsics.mp4", result, "8x11", SQUARE_M * 1000,
                                         "setupA", 0.0, 1.0, recording_mode_verified=True,
                                         overlay_path=tmp_path / "corners.png")
    assert camera["corner_overlay"]["file"] == "corners.png"
    overlay = cv2.imread(str(tmp_path / "corners.png"))
    assert overlay.shape[:2] == (720, 1280)
    assert (overlay[:, :, 2].astype(float) - overlay[:, :, 0]).max() > 200
    assert camera["status"] == "passed", camera.get("reason")
    centre_true = -R_true.T @ t_true
    centre = -np.asarray(camera["R"]).T @ np.asarray(camera["t"])
    assert np.linalg.norm(centre - centre_true) < 0.03
    assert camera["up_axis_board"] == [0.0, -1.0, 0.0]


def test_up_axis_for_floor_board_points_towards_camera():
    R, t = look_at([0.3, -0.4, -2.0], [0.3, 0.2, 0.0])
    # Board lying flat, printed side facing a camera that is on the -Z side.
    assert board.up_axis(R, t, "floor") == [0.0, 0.0, -1.0]


# ----------------------------------------------------------------------------- light-pulse sync
def pulse_levels(times, onsets, base=60.0, bright=200.0, period=1 / 60):
    """Brightness integrated over each exposure, so the onset frame is partly lit."""
    level = np.full(len(times), base)
    for onset in onsets:
        lit = np.clip((times + period - onset) / period, 0, 1)
        lit[times > onset + 0.4] = 0  # light switched off after 0.4 s
        lit[(times > onset + 0.4 - period) & (times <= onset + 0.4)] = np.clip(
            (onset + 0.4 - times[(times > onset + 0.4 - period) & (times <= onset + 0.4)]) / period, 0, 1)
        level = np.maximum(level, base + (bright - base) * lit)
    return level


def test_pulse_onset_is_recovered_between_frames():
    times = np.arange(0, 6, 1 / 60)
    events = flashsync.detect_pulses(times, pulse_levels(times, [1.2345, 4.5678]))
    assert len(events) == 2
    # With exposure lasting the whole frame, the half-brightness crossing is half a frame early.
    onsets = np.array([e["onset_s"] for e in events]) + 0.5 / 60
    np.testing.assert_allclose(onsets, [1.2345, 4.5678], atol=0.0015)


def test_offset_and_drift_mapping_round_trip():
    ref = {"start": {"onset_s": 2.000}, "end": {"onset_s": 32.000}}
    other = {"start": {"onset_s": 0.500}, "end": {"onset_s": 30.497}}
    sync = flashsync.align(ref, other, 1 / 60)
    assert sync["status"] == "measured"
    assert sync["offset_s"] == pytest.approx(1.5)
    assert sync["drift_s"] == pytest.approx(0.003, abs=1e-9)
    np.testing.assert_allclose(flashsync.to_reference([0.5, 30.497], sync), [2.0, 32.0], atol=1e-9)
    np.testing.assert_allclose(flashsync.to_other(flashsync.to_reference([7.0], sync), sync), [7.0])


def test_mismatched_pulses_are_rejected():
    sync = flashsync.align({"start": {"onset_s": 1.0}, "end": {"onset_s": 20.0}},
                           {"start": {"onset_s": 1.0}, "end": {"onset_s": 17.0}}, 1 / 60)
    assert sync["status"] == "failed"


# ----------------------------------------------------------------------------- squat measurement
DEPTHS = [0.30, 0.31, 0.17, 0.29, 0.14, 0.30]   # rep 1 is the reference
STANDING_HIP_HEIGHT = 0.95


def hip_height(times, descents=(1.0, 1.0, 1.0, 0.5, 0.5, 0.5)):
    h = np.full(len(times), STANDING_HIP_HEIGHT)
    start = 3.0
    for depth, descent in zip(DEPTHS, descents):
        phase = (times - start) / (2 * descent)
        inside = (phase >= 0) & (phase <= 1)
        h[inside] -= depth * 0.5 * (1 - np.cos(2 * np.pi * phase[inside]))
        start += 2 * descent + 0.8
    return h


def skeleton(times):
    """17 COCO joints for a person squatting in place; board frame, Y points down."""
    h = hip_height(times)
    offsets = {0: (0, -0.65, -0.05), 5: (-0.18, -0.48, 0), 6: (0.18, -0.48, 0), 7: (-0.22, -0.2, 0),
               8: (0.22, -0.2, 0), 9: (-0.22, 0.05, -0.1), 10: (0.22, 0.05, -0.1), 11: (-0.1, 0, 0),
               12: (0.1, 0, 0)}
    xyz = np.zeros((len(times), 17, 3))
    for j in range(17):
        xyz[:, j] = [0.3, 0, 0.5]
    for j, (x, y, z) in offsets.items():
        xyz[:, j, 0] += x
        xyz[:, j, 1] = -h + y
        xyz[:, j, 2] += z
    for side, (knee, ankle) in enumerate(((13, 15), (14, 16))):
        x = -0.12 if side == 0 else 0.12
        xyz[:, ankle] = [0.3 + x, 0, 0.5]
        bend = STANDING_HIP_HEIGHT - h
        xyz[:, knee, 0] = 0.3 + x
        xyz[:, knee, 1] = -0.48 + bend * 0.15
        xyz[:, knee, 2] = 0.5 - bend * 0.9
    return xyz


def two_cameras(width=1920, height=1080):
    K = intrinsic(width, height, 1500)
    target = [0.3, -0.7, 0.5]
    views = []
    for angle in (-50, 40):
        a = np.radians(angle)
        center = [0.3 + 3.2 * np.sin(a), -1.0, 0.5 - 3.2 * np.cos(a)]
        R, t = look_at(center, target)
        views.append({"K": K, "R": R, "t": t, "distortion": np.zeros(5), "units": "m",
                      "board_frame_id": "setupA", "image_size": [width, height]})
    return views


def observe(times, xyz, camera, noise_px, rng):
    points = np.stack([project(frame, camera["K"], camera["R"], camera["t"]) for frame in xyz])
    points += rng.normal(0, noise_px, points.shape)
    return {"times_s": times, "keypoints": points, "scores": np.full(points.shape[:2], 0.9)}


def synthetic_observations(noise_px=0.7, offset_s=0.6173, seed=11):
    rng = np.random.default_rng(seed)
    cameras = two_cameras()
    ref_times = np.arange(0, 22, 1 / 60)
    other_times = np.arange(0, 22, 1 / 30) + 0.0037   # slower phone, its own clock
    ref = observe(ref_times, skeleton(ref_times), cameras[0], noise_px, rng)
    # The second phone's frame at its time u shows the world at reference time u + offset.
    other = observe(other_times, skeleton(other_times + offset_s), cameras[1], noise_px, rng)
    syncs = [{"offset_s": 0.0, "drift_rate": 0.0, "anchor_s": 0.0},
             {"offset_s": offset_s, "drift_rate": 0.0, "anchor_s": 0.0}]
    return cameras, [ref, other], syncs


def test_two_camera_depths_and_outcomes_are_recovered():
    cameras, observations, syncs = synthetic_observations()
    sequence = reconstruct_sequence(observations, cameras, syncs, frame_periods=[1 / 60, 1 / 30], joints=HIPS)
    hips = sequence["valid"][:, 11] & sequence["valid"][:, 12]
    assert hips.mean() > 0.95
    result = measure_squats(sequence["times_s"], sequence["xyz"], sequence["valid"], [0, -1, 0],
                            {"standing_window_s": [0.5, 2.5], "tolerance_m": 0.03})
    reps = result["reps"]["raw"]["reps"]
    assert [r["rep"] for r in reps] == [1, 2, 3, 4, 5, 6]
    np.testing.assert_allclose([r["depth_m"] for r in reps], DEPTHS, atol=0.012)
    assert [r["outcome"] for r in reps] == ["reached_reference", "reached_reference", "shallower",
                                            "reached_reference", "shallower", "reached_reference"]
    jitter = result["jitter"]["raw"]
    assert jitter["status"] == "measured" and jitter["rms_m"] < 0.005
    assert result["jitter"]["filtered"]["rms_m"] < jitter["rms_m"]
    effect = {e["rep"]: e for e in result["filter_effect"]}
    assert abs(effect[4]["filtered_minus_raw_m"]) < 0.01   # fast rep keeps its depth under a 5-frame filter


def test_wrong_sync_offset_degrades_the_reconstruction():
    cameras, observations, syncs = synthetic_observations(noise_px=0.3)
    good = reconstruct_sequence(observations, cameras, syncs, frame_periods=[1 / 60, 1 / 30], joints=HIPS)
    syncs[1] = {**syncs[1], "offset_s": syncs[1]["offset_s"] + 2 / 60}   # two frames late
    bad = reconstruct_sequence(observations, cameras, syncs, frame_periods=[1 / 60, 1 / 30], joints=HIPS)
    assert np.nanmedian(bad["reprojection_px"][:, 11]) > 2 * np.nanmedian(good["reprojection_px"][:, 11])


def test_missing_hips_make_a_rep_unclear_not_guessed():
    times = np.arange(0, 22, 1 / 60)
    h = hip_height(times)
    h[(times > 6.6) & (times < 7.4)] = np.nan   # rep 2's bottom unseen
    reps, _ = squat.segment_reps(times, h, standing=STANDING_HIP_HEIGHT)
    classified, _ = squat.classify(reps, 1, 0.03)
    assert classified[1]["outcome"] == "unclear"
    assert np.isnan(squat.smooth(h, 5)[(times > 6.6) & (times < 7.4)]).all()


def test_comparison_with_footage_counts_false_passes_and_flags():
    reps = [{"rep": 1, "outcome": "reached_reference"}, {"rep": 2, "outcome": "reached_reference"},
            {"rep": 3, "outcome": "shallower"}, {"rep": 4, "outcome": "unclear"}, {"rep": 5, "outcome": "shallower"}]
    counts, _ = squat.score_against_labels(reps, {1: "match", 2: "shallow", 3: "match", 4: "match", 5: "shallow"})
    assert counts == {"compared": 4, "agree": 2, "false_pass": 1, "false_flag": 1, "software_unclear": 1,
                      "label_unclear": 0, "unlabelled": 0}


def test_rigid_target_length_from_marked_pixels():
    cameras = two_cameras()
    a, b = np.array([0.1, -0.9, 0.4]), np.array([0.6, -0.9, 0.4])
    spec = {"points": {name: {f"cam{i + 1}": project(p, c["K"], c["R"], c["t"])[0].tolist()
                              for i, c in enumerate(cameras)} for name, p in (("A", a), ("B", b))},
            "distances": [{"from": "A", "to": "B", "known_m": 0.5}]}
    result = measure_points(spec, {"cam1": cameras[0], "cam2": cameras[1]})
    assert abs(result["distances"][0]["error_m"]) < 1e-6


# ----------------------------------------------------------------------------- whole run from files
def prepare_full_run(tmp_path, monkeypatch):
    """Synthetic videos, calibrations, saved keypoints and session config; returns what run_session needs."""
    width, height, offset = 640, 360, 0.45
    cameras = two_cameras(width, height)
    data, calibration, outputs = tmp_path / "data", tmp_path / "calibration", tmp_path / "outputs"
    for folder in (data, calibration):
        folder.mkdir()
    duration, fps = 23.0, (60, 30)
    rng = np.random.default_rng(5)
    observations = []
    for index, (camera, rate) in enumerate(zip(cameras, fps)):
        own_times = np.arange(0, duration, 1 / rate)
        world_times = own_times + (offset if index == 1 else 0.0)
        # Light pulses happen at fixed world times; this phone sees them at its own times.
        levels = pulse_levels(own_times, [1.0 - (offset if index else 0), 22.0 - (offset if index else 0)],
                              period=1 / rate)
        write_video(data / f"cam{index + 1}.mp4", [np.full((height, width), v, np.uint8) for v in levels], rate)
        record = {**{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in camera.items()},
                  "camera_id": f"cam{index + 1}", "status": "passed", "recording_mode_verified": True,
                  "up_axis_board": [0.0, -1.0, 0.0]}
        (calibration / f"cam{index + 1}.json").write_text(json.dumps(record))
        obs = observe(world_times, skeleton(world_times), camera, 0.5, rng)
        obs.update(frame_index=np.arange(len(own_times)), times_s=own_times, image_size=[width, height],
                   joint_names=[], detector="synthetic projection")
        from rvectr.media import probe
        from rvectr.records import sha256
        from rvectr.pipeline import DEFAULTS
        path = data / f"cam{index + 1}.mp4"
        meta = probe(path)
        obs.update(times_s=meta["pts"], joint_names=list(pose2d.JOINT_NAMES),
                   source_identity=pose2d.cache_identity(f"cam{index + 1}", sha256(path), meta,
                                                        {**DEFAULTS["pose"], "source": "synthetic projection"}))
        observations.append(obs)
    previous = outputs / "V1.1.1"
    for index, obs in enumerate(observations):
        pose2d.save(previous / "keypoints2d" / f"cam{index + 1}.npz", obs)
    (tmp_path / "labels.csv").write_text("rep,judged_from_footage\n1,match\n2,match\n3,shallow\n4,match\n5,shallow\n6,match\n")
    config = {"session": "synthetic", "pose": {"source": "synthetic projection"}, "cameras": [{"id": f"cam{i}", "video": f"cam{i}.mp4", "calibration": f"cam{i}.json"}
                                                  for i in (1, 2)],
              "sync": {"method": "flash", "start_window_s": 3, "end_window_s": 3},
              "squat": {"standing_window_s": [1.6, 2.8]}, "labels": "labels.csv"}
    (tmp_path / "session.json").write_text(json.dumps(config))
    monkeypatch.setenv("RVECTR_DATA_ROOT", str(data))
    monkeypatch.setenv("RVECTR_CALIBRATION_DIR", str(calibration))
    paths = RuntimePaths.discover(load_local=False)
    return paths, outputs, previous, offset


@needs_ffmpeg
def test_full_run_from_videos_and_saved_keypoints(tmp_path, monkeypatch):
    paths, outputs, previous, offset = prepare_full_run(tmp_path, monkeypatch)
    run, report = run_session(tmp_path / "session.json", paths, outputs, keypoints_from=previous, progress=lambda *_: None)
    assert run.name == "V1.1.2"
    assert report["status"] == "measured"
    assert report["synchronization"][1]["offset_s"] == pytest.approx(offset, abs=0.01)
    assert len(report["reps"]["raw"]["reps"]) == 6
    assert report["reference_source"]["kind"] == "legacy_detection_index"
    assert report["comparison_with_footage"]["status"] == "not_scored_requires_independent_timestamps"
    assert len(report["comparison_with_footage"]["labels"]) == 6
    assert "counts" not in report["comparison_with_footage"]
    for name in ("report.json", "manifest.json", "pelvis_trace.csv", "reps_raw.csv", "depth_trace.png",
                 "points3d.npz", "sync/sync.json", "sync/brightness.png", "keypoints2d/cam2.npz"):
        assert (run / name).exists(), name


@needs_ffmpeg
def test_keypoints_on_the_frame_edge_count_as_missing(tmp_path):
    write_video(tmp_path / "blank.mp4", [np.zeros((240, 320), np.uint8)] * 3, 30)

    class Stub:
        def __call__(self, frame):
            kp = np.tile([[160.0, 120.0]], (17, 1))
            kp[11] = [160, 239.5]          # left hip guessed on the bottom border
            kp[12] = [170, 300]            # right hip beyond the picture
            return kp[None], np.full((1, 17), 0.8)

    from rvectr.media import probe
    path = tmp_path / "blank.mp4"
    observation = pose2d.detect_video(path, probe(path), Stub())
    assert (observation["scores"][:, 11:13] == 0).all()
    assert (observation["scores"][:, 0] == pytest.approx(0.8))
