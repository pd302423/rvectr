"""Monte Carlo error budget for the two-phone squat-depth design.

This simulation uses a constructed motion and noise settings. The published
validation contains no pilot measurements.
The aim is a PREDICTION, made before recording, of how small a depth
difference the design can detect and which error sources matter most.

The simulated world
-------------------
* A person stands facing +z. The "up" direction is -y (the same convention as
  the synthetic tests: y points down, as in an image).
* Two hip points sit 0.25 m apart (along x). The pelvis is their midpoint.
* In a repetition the pelvis goes down by `d(t)` and also travels backwards
  (-z) by 0.5 x `d(t)`. The motion is a raised cosine: d = depth x sin^2(pi s / 2T).
* Each camera is a pinhole, level, 3.0 m from the person, lens height 1.0 m.
* 2D keypoint errors (white noise, slow noise, posture bias, dropouts), a
  sync error and calibration errors are added, then hips are triangulated,
  and the project's own rules in `squat.py` find and compare repetitions.

Missing data is never filled in. A frame without both hips reconstructed is
NaN, and a repetition with too little coverage comes out "unclear" from the
project's own `squat.classify` rule.
"""
from __future__ import annotations

import zlib
import math
from dataclasses import dataclass, replace

import numpy as np
from scipy.signal import lfilter

from . import squat
from .pipeline import DEFAULTS

# ----------------------------------------------------------------------------- world constants
HIP_SPACING_M = 0.25        # distance between the two hip points
STANDING_M = 0.95           # height of the pelvis when standing
REFERENCE_DEPTH_M = 0.30    # depth of the reference repetition
BACKWARD_PER_DESCENT = 0.5  # pelvis moves back by this x the current descent
STAND_S = 3.0               # standing still at the start of a session
PAUSE_S = 1.0               # standing pause after each repetition
PACES = {"controlled": 2.0, "fast": 0.8}   # descent time in seconds

# ----------------------------------------------------------------------------- camera constants
IMAGE_W, IMAGE_H = 1080, 1920   # portrait phone video
FOCAL_PX = 1423.0
DISTANCE_M = 3.0                # camera to person (horizontal)
LENS_HEIGHT_M = 1.0
SIDE_DEG, OBLIQUE_DEG = 90.0, 45.0   # angle from the direction the person faces
MM_PER_IMAGE_PX = DISTANCE_M / FOCAL_PX * 1000.0   # about 2.11 mm per image pixel at the person
MM_PER_MODEL_PX = 1.70 * 1.25 / 256 * 1000.0       # pose model sees the person in a 256 px crop: 8.3 mm


def model_px_to_image_px(model_px):
    """Convert 'model pixels' (8.3 mm at the person) to image pixels (2.11 mm at the person)."""
    return model_px * MM_PER_MODEL_PX / MM_PER_IMAGE_PX


def image_px_to_mm(image_px):
    return image_px * MM_PER_IMAGE_PX


# ----------------------------------------------------------------------------- decision rules
# Taken from the pipeline so the simulation uses the same numbers as a real run.
RULES = DEFAULTS["squat"]
STANDING_WINDOW_S = (0.5, 2.5)   # the person stands still here; used to find the standing level
REACHED, SHALLOWER, UNCLEAR = 0, 1, 2

MODES = ("side_1cam", "oblique_1cam", "two_cam", "three_cam")


@dataclass(frozen=True)
class Setup:
    """One simulated recording set-up. The defaults are the reference case."""
    mode: str = "two_cam"
    pace: str = "controlled"
    fps: float = 60.0
    white_px: float = model_px_to_image_px(0.5)   # white noise, image pixels, 1 sigma
    slow_px: float = 0.0           # slowly varying (AR(1)) noise, image pixels, stationary sigma
    slow_tau_s: float = 0.2        # its correlation time
    beta: float = 0.0              # detected hip is raised by beta x current descent
    dropout: float = 0.0           # chance that a hip is missing in one camera in one frame
    sync_frames: float = 0.0       # camera B samples the motion at t + sync_frames / fps
    sync_offsets_frames: tuple[float, ...] = ()  # per-camera time offset; overrides sync_frames when set
    camera_bias_px: float = 0.0    # session-shared, camera-specific 2D keypoint bias sigma
    shared_vertical_sigma_m: float = 0.0  # latent per-frame vertical hip error projected by every camera
    motion_noise_factor: float = 0.0  # white-noise sigma rises by this fraction at peak speed
    dropout_burst_probability: float = 0.0  # chance per frame of a shared-camera visibility gap
    dropout_burst_frames: int = 0   # duration of each shared-camera visibility gap
    camera_translation_sigma_m: float = 0.0  # per-camera extrinsic center error, shared for a session
    camera_rotation_sigma_deg: float = 0.0   # per-camera extrinsic orientation error, shared for a session
    scale_error: float = 0.0       # reconstructed lengths x (1 + scale_error)
    tilt_deg: float = 0.0          # up-axis tilted this far towards the direction of travel
    separation_deg: float = SIDE_DEG - OBLIQUE_DEG   # angle between camera A and B
    trace: str = "raw"             # "raw" or "filtered" (5-frame moving average, as in the pipeline)
    n_test_reps: int = 3
    tolerance_m: float = RULES["tolerance_m"]
    estimator: str = RULES["estimator"]   # "parabola" (new) or "extreme" (old), see squat.segment_reps
    dwell_s: float = 0.0           # the pelvis rests at the bottom this long between going down and coming up

    def __post_init__(self):
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        if self.pace not in PACES:
            raise ValueError(f"pace must be one of {tuple(PACES)}")
        if self.trace not in ("raw", "filtered"):
            raise ValueError("trace must be 'raw' or 'filtered'")
        if self.estimator not in ("parabola", "extreme"):
            raise ValueError("estimator must be 'parabola' or 'extreme'")
        expected_cameras = 1 if self.mode.endswith("1cam") else (3 if self.mode == "three_cam" else 2)
        if self.sync_offsets_frames and len(self.sync_offsets_frames) != expected_cameras:
            raise ValueError("sync_offsets_frames must have one entry per camera in this mode")
        if self.dropout_burst_frames < 0:
            raise ValueError("dropout_burst_frames cannot be negative")
        for name in ("camera_bias_px", "shared_vertical_sigma_m", "motion_noise_factor", "dropout_burst_probability",
                     "camera_translation_sigma_m", "camera_rotation_sigma_deg"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")

    @property
    def descent_s(self):
        return PACES[self.pace]

    def with_(self, **changes):
        return replace(self, **changes)


# ----------------------------------------------------------------------------- cameras
def look_at(center, target, down=(0, 1, 0)):
    """World-to-camera rotation and translation (same as the synthetic pipeline tests)."""
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


def make_camera(angle_deg):
    """Level camera 3 m from the person. angle 0 = in front of them, 90 = on their side."""
    a = np.radians(angle_deg)
    center = [DISTANCE_M * np.sin(a), -LENS_HEIGHT_M, DISTANCE_M * np.cos(a)]   # y is down
    R, t = look_at(center, [0.0, -LENS_HEIGHT_M, 0.0])                          # look straight at the person, level
    return {"K": intrinsic(IMAGE_W, IMAGE_H, FOCAL_PX), "R": R, "t": t, "center": np.asarray(center), "distortion": np.zeros(5),
            "units": "m", "board_frame_id": "sim", "image_size": [IMAGE_W, IMAGE_H]}


def perturb_camera_calibration(cameras, setup, rng):
    """Apply session-shared per-camera extrinsic errors, as a calibration would."""
    if setup.camera_translation_sigma_m == 0 and setup.camera_rotation_sigma_deg == 0:
        return cameras
    result = []
    for camera in cameras:
        center = camera["center"] + rng.normal(0, setup.camera_translation_sigma_m, 3)
        angles = np.radians(rng.normal(0, setup.camera_rotation_sigma_deg, 3))
        cx, cy, cz = np.cos(angles)
        sx, sy, sz = np.sin(angles)
        rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
        ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
        rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
        R = (rz @ ry @ rx) @ camera["R"]
        result.append(dict(camera, R=R, t=-R @ center, center=center))
    return result


def camera_angles(setup):
    """Camera angles (degrees from the facing direction). Camera B is the second one."""
    side = SIDE_DEG
    oblique = SIDE_DEG - setup.separation_deg
    return {"side_1cam": [side], "oblique_1cam": [oblique], "two_cam": [side, oblique],
            "three_cam": [side, oblique, -oblique]}[setup.mode]   # third = mirrored oblique


def project(points, camera):
    """Pinhole projection of world points [..., 3] to pixels [..., 2]."""
    cam = points @ camera["R"].T + camera["t"]
    K = camera["K"]
    return np.stack([K[0, 0] * cam[..., 0] / cam[..., 2] + K[0, 2],
                     K[1, 1] * cam[..., 1] / cam[..., 2] + K[1, 2]], axis=-1)


# ----------------------------------------------------------------------------- vectorised triangulation
def triangulate_dlt(pixels, present, cameras):
    """Linear (DLT) triangulation of many points at once.

    pixels [N, C, 2]: where each of C cameras saw each of N points.
    present [N, C]: False where the camera did not detect the point (never filled in).
    Returns xyz [N, 3] and valid [N]; a point needs at least 2 cameras, else NaN.

    Each camera that sees the point says "the point lies on this ray". Stacking
    those equations and solving them in the least-squares sense (smallest
    eigenvector of A^T A, the same answer as the SVD in geometry.triangulate_points)
    gives the point. Unlike geometry.triangulate_points there is no refinement
    step and no outlier test, which is what makes this fast.
    """
    pixels = np.asarray(pixels, float)
    present = np.asarray(present, bool)
    n = len(pixels)
    normal = np.zeros((n, 4, 4))
    for c, cam in enumerate(cameras):
        K, P = cam["K"], np.column_stack((cam["R"], cam["t"]))
        x = (pixels[:, c, 0] - K[0, 2]) / K[0, 0]          # normalised image coordinates
        y = (pixels[:, c, 1] - K[1, 2]) / K[1, 1]
        row1 = x[:, None] * P[2] - P[0]                    # x * P3 - P1 = 0
        row2 = y[:, None] * P[2] - P[1]                    # y * P3 - P2 = 0
        use = present[:, c, None, None]
        normal += use * (row1[:, :, None] * row1[:, None, :] + row2[:, :, None] * row2[:, None, :])
    valid = present.sum(axis=1) >= 2
    xyz = np.full((n, 3), np.nan)
    if valid.any():
        _, vectors = np.linalg.eigh(normal[valid])
        homogeneous = vectors[:, :, 0]                      # smallest eigenvalue = best fit
        xyz[valid] = homogeneous[:, :3] / homogeneous[:, 3:4]
    return xyz, valid


# ----------------------------------------------------------------------------- the simulated motion
def rep_starts(setup, phase_s=0.0):
    """Start time of the reference repetition followed by the test repetitions."""
    period = 2 * setup.descent_s + setup.dwell_s + PAUSE_S
    return STAND_S + phase_s + period * np.arange(1 + setup.n_test_reps)


def descent_profile(times, starts, depths, descent_s, dwell_s=0.0):
    """How far the pelvis is below standing at each time (metres). Zero between repetitions.

    Down over descent_s, then (if dwell_s > 0) resting at the bottom for dwell_s, then up over descent_s.
    """
    times = np.asarray(times, float)
    d = np.zeros_like(times)
    for start, depth in zip(starts, depths):
        s = times - start
        down = (s >= 0) & (s < descent_s)
        rest = (s >= descent_s) & (s < descent_s + dwell_s)
        up = (s >= descent_s + dwell_s) & (s <= 2 * descent_s + dwell_s)
        d[down] += depth * np.sin(np.pi * s[down] / (2 * descent_s)) ** 2                    # raised cosine down
        d[rest] += depth                                                                      # resting at the bottom
        d[up] += depth * np.sin(np.pi * (s[up] - dwell_s) / (2 * descent_s)) ** 2             # raised cosine up
    return d


def hip_points(descent, beta=0.0):
    """World positions [F, 2, 3] of the left and right hip for a given descent.

    The detector's hip is raised by beta x descent (posture-dependent bias): the
    TRUE hip is lower than the one the detector reports.
    """
    descent = np.asarray(descent, float)
    out = np.zeros((len(descent), 2, 3))
    out[:, 0, 0], out[:, 1, 0] = -HIP_SPACING_M / 2, HIP_SPACING_M / 2           # left / right
    out[:, :, 1] = (-(STANDING_M - descent) - beta * descent)[:, None]           # y is down, so up is negative
    out[:, :, 2] = (-BACKWARD_PER_DESCENT * descent)[:, None]                    # travels backwards
    return out


def slow_noise(standard_normals, sigma, dt, tau):
    """AR(1) noise along axis 0 with stationary standard deviation sigma and correlation time tau."""
    phi = np.exp(-dt / tau)
    innovations = standard_normals * sigma * np.sqrt(1 - phi ** 2)
    innovations[0] = standard_normals[0] * sigma        # start in the stationary distribution
    return lfilter([1.0], [1.0, -phi], innovations, axis=0)


def simulate_observations(setup, depths, rng):
    """Everything the 2D detectors would report. Returns times, pixels [F,C,2,2], present [F,C,2], cameras."""
    dt = 1.0 / setup.fps
    starts = rep_starts(setup, phase_s=rng.uniform(0, dt))        # random frame phase
    total = starts[-1] + 2 * setup.descent_s + setup.dwell_s + PAUSE_S
    times = np.arange(int(np.ceil(total / dt))) * dt
    true_cameras = [make_camera(a) for a in camera_angles(setup)]
    cameras = perturb_camera_calibration(true_cameras, setup, rng)
    n_cam = len(cameras)
    shape = (len(times), n_cam, 2, 2)                             # frame, camera, hip, (u, v)
    # Always draw the same random numbers so settings can be compared on equal terms.
    z_white = rng.standard_normal(shape)
    z_slow = rng.standard_normal(shape)
    z_drop = rng.random(shape[:3])
    shared_height = rng.normal(0, setup.shared_vertical_sigma_m, len(times)) if setup.shared_vertical_sigma_m else None
    pixels = np.zeros(shape)
    for c in range(n_cam):
        if setup.sync_offsets_frames:
            shift = setup.sync_offsets_frames[c] * dt
        else:
            shift = setup.sync_frames * dt if (c == 1 and setup.mode in ("two_cam", "three_cam")) else 0.0
        d = descent_profile(times + shift, starts, depths, setup.descent_s, setup.dwell_s)
        # Project with the true physical camera; reconstruct with its perturbed calibration.
        points = hip_points(d, setup.beta)
        if shared_height is not None:
            points[:, :, 1] += shared_height[:, None]
        pixels[:, c] = project(points, true_cameras[c])
    if setup.motion_noise_factor:
        motion = np.zeros(len(times))
        for start in starts:
            s = times - start
            moving = (s >= 0) & (s <= 2 * setup.descent_s + setup.dwell_s)
            phase = np.clip(s[moving] / max(2 * setup.descent_s + setup.dwell_s, 1e-9), 0, 1)
            motion[moving] = np.maximum(motion[moving], np.abs(np.sin(2 * np.pi * phase)))
        pixels += z_white * setup.white_px * (1 + setup.motion_noise_factor * motion[:, None, None, None])
    else:
        pixels += z_white * setup.white_px
    if setup.slow_px > 0:
        pixels += slow_noise(z_slow, setup.slow_px, dt, setup.slow_tau_s)
    if setup.camera_bias_px:
        # Camera-specific keypoint bias persists across the take and is shared by both hips.
        pixels += rng.normal(0, setup.camera_bias_px, (1, n_cam, 1, 2))
    present = z_drop >= setup.dropout                             # False = this hip missing in this camera
    if setup.dropout_burst_probability and setup.dropout_burst_frames:
        burst_starts = np.flatnonzero(rng.random(len(times)) < setup.dropout_burst_probability)
        for frame in burst_starts:
            present[frame:min(len(times), frame + setup.dropout_burst_frames), :, :] = False
    return times, pixels, present, cameras, starts


def up_axis(tilt_deg):
    """Calibrated 'up' direction. A tilt leans it towards the direction of horizontal travel (-z)."""
    e = np.radians(tilt_deg)
    return np.array([0.0, -np.cos(e), -np.sin(e)])


def reconstruct(setup, pixels, present, cameras):
    """Hip positions in the layout the project's squat functions expect: xyz [F,J,3], valid [F,J]."""
    frames = len(pixels)
    xyz = np.full((frames, 13, 3), np.nan)                        # joints 11, 12 are the hips
    valid = np.zeros((frames, 13), bool)
    if setup.mode.endswith("1cam"):
        # One camera: height from the image using the scale that is right at the standing
        # position (the person is DISTANCE_M away). Moving towards/away makes this wrong.
        v = pixels[:, 0, :, 1]
        height = LENS_HEIGHT_M - (v - IMAGE_H / 2) * DISTANCE_M / FOCAL_PX
        for hip, joint in enumerate((squat.LEFT_HIP, squat.RIGHT_HIP)):
            xyz[:, joint] = np.stack([np.zeros(frames), -height[:, hip], np.zeros(frames)], axis=1)
            valid[:, joint] = present[:, 0, hip]
        up = np.array([0.0, -1.0, 0.0])
    else:
        for hip, joint in enumerate((squat.LEFT_HIP, squat.RIGHT_HIP)):
            xyz[:, joint], valid[:, joint] = triangulate_dlt(pixels[:, :, hip], present[:, :, hip], cameras)
        up = up_axis(setup.tilt_deg)
    xyz = xyz * (1.0 + setup.scale_error)                         # calibration scale error
    return xyz, valid, up


# ----------------------------------------------------------------------------- measuring with the project's rules
def pelvis_height(setup, xyz, valid, up):
    """Pelvis height trace [F] by the pipeline's steps: midpoint, optional smoothing, height along up."""
    pelvis = squat.pelvis_track(xyz, valid)                       # NaN unless both hips were reconstructed
    if setup.trace == "filtered":
        pelvis = squat.smooth(pelvis, RULES["filter_frames"])     # NaN again wherever a gap is inside the window
    return squat.height(pelvis, up)


def measure(setup, times, h, true_bottoms_s):
    """measure_with_models without the last item (kept so older callers work)."""
    return measure_with_models(setup, times, h, true_bottoms_s)[:4]


def measure_with_models(setup, times, h, true_bottoms_s):
    """Run the project's segment/classify rules on a height trace and match results to the true repetitions.

    Returns depths [R], outcomes [R] for the true repetitions in order (reference first), the number
    of repetitions the software detected (more than R means noise created false repetitions) and the
    standard error the software reports for each depth [R] (NaN if unclear, or with the old estimator).
    A repetition the software did not find is "unclear". The fifth item is the bottom_model of each
    true repetition ("parabola", "plateau", "none"; "missing" if the repetition was not found).
    """
    n = len(true_bottoms_s)
    models = np.full(n, "missing", dtype=object)
    depths, outcomes, depth_se = np.full(n, np.nan), np.full(n, UNCLEAR), np.full(n, np.nan)
    inside = (times >= STANDING_WINDOW_S[0]) & (times <= STANDING_WINDOW_S[1]) & np.isfinite(h)
    standing = float(np.median(h[inside])) if inside.sum() >= 10 else None
    reps, _ = squat.segment_reps(times, h, standing=standing, min_depth_m=RULES["min_rep_depth_m"],
                                 estimator=setup.estimator)
    if not reps:
        return depths, outcomes, 0, depth_se, models
    # Which detected repetition is which? Match by bottom time to the known truth.
    matched = []
    for bottom in true_bottoms_s:
        gaps = np.array([abs(r["bottom_s"] - bottom) for r in reps])
        matched.append(int(np.argmin(gaps)) if gaps.min() <= setup.descent_s else None)
    for i, k in enumerate(matched):
        if k is not None:
            models[i] = reps[k].get("bottom_model", "none")
    if matched[0] is None:
        return depths, outcomes, len(reps), depth_se, models              # reference not found: nothing can be compared
    try:
        classified, _ = squat.classify(reps, reps[matched[0]]["rep"], setup.tolerance_m,
                                       RULES["min_coverage"], RULES["borderline_m"])
    except ValueError:                                            # reference not observed well enough
        return depths, outcomes, len(reps), depth_se, models
    names = {"reached_reference": REACHED, "shallower": SHALLOWER, "unclear": UNCLEAR}
    for i, k in enumerate(matched):
        if k is None:
            continue
        outcomes[i] = names[classified[k]["outcome"]]
        if outcomes[i] != UNCLEAR:
            depths[i] = classified[k]["depth_m"]
            depth_se[i] = classified[k].get("depth_se_m", np.nan)
        models[i] = classified[k].get("bottom_model", "none")
    return depths, outcomes, len(reps), depth_se, models


def simulate_trace(setup, delta_m, rng):
    """One recording up to the pelvis height trace. Returns times, h [F], true depths, rep start times."""
    depths = np.r_[REFERENCE_DEPTH_M, np.full(setup.n_test_reps, REFERENCE_DEPTH_M - delta_m)]
    times, pixels, present, cameras, starts = simulate_observations(setup, depths, rng)
    xyz, valid, up = reconstruct(setup, pixels, present, cameras)
    return times, pelvis_height(setup, xyz, valid, up), depths, starts


def run_session(setup, delta_m, rng):
    """One recording: reference repetition then test repetitions shallower by delta_m."""
    times, h, depths, starts = simulate_trace(setup, delta_m, rng)
    measured, outcomes, detected, depth_se, models = measure_with_models(
        setup, times, h, starts + setup.descent_s + setup.dwell_s / 2)    # the middle of the rest is the true bottom time
    return measured, outcomes, depths, detected, depth_se, models


def run_config(setup, delta_m, n_sessions, seed=0):
    """Many sessions of one set-up and one true difference.

    Session i always uses random stream (seed, i), so results do not depend on
    how many sessions are run and are identical for the same seed.
    Returns dict of arrays: depth_error_m [n, 1+K] (NaN where unclear),
    outcome [n, 1+K] (0 reached, 1 shallower, 2 unclear), extra_reps [n] (detected minus true repetitions),
    depth_se_m [n, 1+K] (the standard error the software reported for each depth),
    bottom_model [n, 1+K] (how each bottom was read: "parabola", "plateau", "none", or "missing" if not found).
    """
    err, out, detected, reported_se, models = [], [], [], [], []
    for i in range(n_sessions):
        measured, outcomes, truth, n_found, depth_se, bottom_models = run_session(
            setup, delta_m, np.random.default_rng([seed, i]))
        models.append(bottom_models)
        reported_se.append(depth_se)
        err.append(measured - truth)
        out.append(outcomes)
        detected.append(n_found - len(truth))
    return {"delta_m": float(delta_m), "depth_error_m": np.array(err), "outcome": np.array(out),
            "extra_reps": np.array(detected), "depth_se_m": np.array(reported_se),
            "bottom_model": np.array(models, dtype=object)}


def config_seed(*parts):
    """Stable integer from names (Python's own hash() changes between runs)."""
    return zlib.crc32("|".join(map(str, parts)).encode())


# ----------------------------------------------------------------------------- statistics
def difference_error(run):
    """Measured (test - reference) depth minus the true difference, in metres; NaN where unclear."""
    err = run["depth_error_m"]
    return err[:, 1:] - err[:, :1]


def score(run):
    """How strongly each test repetition looks shallower than the reference (metres; bigger = shallower).

    score = measured reference depth - measured test depth. Unclear repetitions
    remain in the denominator and can never be counted as flagged.
    """
    s = -difference_error(run) + run["delta_m"]
    return np.where(np.isfinite(s), s, -np.inf).ravel()


def depth_error_sd_m(run):
    e = run["depth_error_m"]
    e = e[np.isfinite(e)]
    return float(np.std(e)) if len(e) > 1 else float("nan")


def difference_sd_m(run):
    d = difference_error(run)
    d = d[np.isfinite(d)]
    return float(np.std(d)) if len(d) > 1 else float("nan")


def difference_gain(run):
    """How much of a true difference the measurement shows: mean measured / true difference (1 = faithful).

    Errors that rescale depth (posture bias, scale, tilt, one-camera perspective) make this differ from 1.
    They do not hurt the best-threshold MDD (signal and noise are rescaled together) but they move the
    pipeline's fixed 3 cm line: it then corresponds to a true difference of tolerance / gain.
    Needs a run with a non-zero true difference.
    """
    if run["delta_m"] <= 0:
        raise ValueError("difference_gain needs a run with a true difference above 0")
    shown = run["delta_m"] - difference_error(run)           # measured reference depth - measured test depth
    shown = shown[np.isfinite(shown)]                        # unclear repetitions have no measured difference
    return float(shown.mean() / run["delta_m"]) if len(shown) else float("nan")


def bottom_model_shares(run):
    """Share of all repetitions read with each bottom model ("parabola", "plateau", "none", "missing" = not found)."""
    models = run["bottom_model"].ravel()
    return {name: float(np.mean(models == name)) for name in ("parabola", "plateau", "none", "missing")}


def flag_rate(run):
    """Share of test repetitions the pipeline rule flags as shallower (unclear counts as not flagged)."""
    return float(np.mean(run["outcome"][:, 1:] == SHALLOWER))


def extra_reps(run):
    """Unmatched detections per session, counted separately from missed attempts."""
    missed = (run["bottom_model"] == "missing").sum(axis=1)
    return float(np.mean(run["extra_reps"] + missed))


def unclear_rate(run):
    return float(np.mean(run["outcome"][:, 1:] == UNCLEAR))


def minimum_detectable_difference_m(runs, level=0.95):
    """Select the first passing grid difference using the training half only.

    The independent second half is reserved for detection_bracket to evaluate the
    frozen cutoff and grid point. The three tests sharing a reference stay together.
    """
    runs = sorted(runs, key=lambda r: r["delta_m"])
    if runs[0]["delta_m"] != 0:
        raise ValueError("The first run must be the matching case (delta 0)")
    n_sessions = len(runs[0]["outcome"])
    split = n_sessions // 2
    if split < 1 or split == n_sessions:
        raise ValueError("at least two sessions are needed to calibrate and evaluate a threshold")
    match_train = score(subset_sessions(runs[0], 0, split))
    threshold, _ = choose_threshold(match_train, level=level)
    if threshold is None:
        return float("inf"), float("nan")
    for run in runs[1:]:
        shallow_train = score(subset_sessions(run, 0, len(run["outcome"]) // 2))
        candidate, counts = choose_threshold(match_train, shallow_train, level)
        if counts["passes"]:
            return float(run["delta_m"]), candidate
    return float("inf"), threshold


def subset_sessions(run, start, stop):
    """Copy a run result restricted to complete session rows."""
    return {key: value[start:stop] if isinstance(value, np.ndarray) and value.ndim else value
            for key, value in run.items()}


def threshold_counts(matching_scores, shallow_scores, threshold, level=0.95):
    """Exact confusion counts using all repetitions, with unclear as not-detected."""
    matching = np.asarray(matching_scores, float)
    shallow = np.asarray(shallow_scores, float)
    if not len(matching) or not len(shallow):
        raise ValueError("matching and shallow sets must be non-empty")
    valid_match = np.isfinite(matching)
    valid_shallow = np.isfinite(shallow)
    usable_threshold = threshold is not None and np.isfinite(threshold)
    false_alarms = int(np.count_nonzero(valid_match & (matching > threshold))) if usable_threshold else 0
    detected = int(np.count_nonzero(valid_shallow & (shallow > threshold))) if usable_threshold else 0
    matching_unclear = int(np.count_nonzero(~valid_match))
    shallow_unclear = int(np.count_nonzero(~valid_shallow))
    max_false = math.floor((1 - level) * len(matching) + 1e-12)
    min_detected = math.ceil(level * len(shallow) - 1e-12)
    return {"matching_total": len(matching), "false_alarms": false_alarms,
            "shallow_total": len(shallow), "detected_shallow": detected,
            "matching_unclear": matching_unclear, "matching_unclear_rate": matching_unclear / len(matching),
            "shallow_unclear": shallow_unclear, "shallow_unclear_rate": shallow_unclear / len(shallow),
            "false_alarm_rate": false_alarms / len(matching), "detection_rate": detected / len(shallow),
            "max_false_alarms": max_false, "min_detected_shallow": min_detected,
            "passes": bool(usable_threshold and false_alarms <= max_false and detected >= min_detected)}


def choose_threshold(matching_scores, shallow_scores=None, level=0.95):
    """Choose the lowest observed cutoff allowed by the training false-alarm budget."""
    matching = np.asarray(matching_scores, float)
    ordered = np.sort(matching[np.isfinite(matching)])
    if not len(ordered):
        return None, {"matching_total": len(matching), "matching_unclear": len(matching), "passes": False}
    max_false = math.floor((1 - level) * len(matching) + 1e-12)
    if len(ordered) > max_false:
        threshold = float(ordered[-max_false - 1])
    else:
        # Flagging all usable training scores stays within the false-alarm budget.
        scores = ordered if shallow_scores is None else np.r_[ordered, shallow_scores]
        threshold = float(np.nextafter(np.min(scores[np.isfinite(scores)]), -np.inf))
    counts = (threshold_counts(matching, shallow_scores, threshold, level) if shallow_scores is not None
              else {"matching_total": len(matching), "matching_unclear": len(matching) - len(ordered),
                    "false_alarms": int(np.count_nonzero(ordered > threshold)), "max_false_alarms": max_false})
    return threshold, counts


def session_bootstrap_rate(run, outcome, n_boot=500, seed=0):
    """95% percentile interval for a repetition rate, resampling whole sessions."""
    values = (run["outcome"][:, 1:] == outcome).mean(axis=1)
    if not len(values):
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(values, size=len(values), replace=True).mean() for _ in range(n_boot)])
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def session_bootstrap_flag_rate(run, threshold, n_boot=500, seed=0):
    """95% interval for a threshold flag rate, resampling the shared-reference session."""
    flagged = (score(run).reshape(run["outcome"][:, 1:].shape) > threshold).mean(axis=1)
    if not len(flagged):
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(flagged, size=len(flagged), replace=True).mean() for _ in range(n_boot)])
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


# ----------------------------------------------------------------------------- analytic cross-check
def single_frame_difference_sd_m(setup, n_sessions, seed=0):
    """Spread of (test depth - reference depth) if each depth were read from just two frames.

    Depth = height in the frame just before the repetition minus height in the frame at the
    true bottom. No maximum, no minimum, no smoothing: this is the situation the simple
    analytic formula assumes. Also returns the per-frame spread of the pelvis height while
    standing still. Returns (difference_sd_m, standing_height_sd_m).
    """
    diffs, standing_noise = [], []
    for i in range(n_sessions):
        times, h, _, starts = simulate_trace(setup, 0.0, np.random.default_rng([seed, i]))
        quiet = (times >= STANDING_WINDOW_S[0]) & (times <= STANDING_WINDOW_S[1])
        standing_noise.append(h[quiet] - np.mean(h[quiet]))
        depth = []
        for start in starts:
            before = int(np.argmin(abs(times - (start - 0.5))))
            bottom = int(np.argmin(abs(times - (start + setup.descent_s + setup.dwell_s / 2))))
            depth.append(h[before] - h[bottom])
        diffs.extend(np.array(depth[1:]) - depth[0])
    return float(np.nanstd(diffs)), float(np.nanstd(np.concatenate(standing_noise)))
