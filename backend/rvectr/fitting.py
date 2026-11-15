"""Movement-agnostic fitting of the user's licensed, official neutral SMPL model.

Input contract
--------------
``xyz`` is synchronized, calibrated, metric triangulation in COCO17 order and
the camera reconstruction's unchanged, right-handed coordinate system. The
caller MUST establish calibration, scale and synchronization before this stage.
Array values alone cannot certify those properties. Confidence is in [0, 1];
NaNs and zero/low-confidence observations remain missing, never frozen copies.

This is a research baseline, not an anatomical joint-centre estimator or a
clinical measurement. COCO landmarks and SMPL joint centres do not have exactly
the same anatomical definition. No head, spine, feet or hand targets are
invented from face landmarks. Twist and occluded joints are underdetermined;
weak regularization chooses a plausible representative, not an observation.
There is no learned pose prior, contact solver, free scale, forced upright
orientation, floor projection, contact locking or movement-specific rule.

One beta vector is fitted to representative observed frames and then held
constant across the sequence. Optimization uses the official SMPL joint
kinematics (exactly the first 24 joints of its LBS model), avoiding full mesh
allocation each iteration. Optional meshes are evaluated using official SMPL
in small batches and streamed to disk. Window overlaps are fixed already-fitted
poses; continuity is penalized on rotation matrices with actual time deltas,
never by smoothing axis-angle components. Missing short *bounded* intervals
may be estimated; long gaps and unbounded missing ends remain unavailable.

All returned SMPL joints are MODEL ESTIMATES. The saved observation mask and
triangulated targets, rather than fitted meshes, define input observations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


# COCO17: nose/eyes/ears, shoulders, elbows, wrists, hips, knees, ankles.
# SMPL: the original 24 kinematic joints, not added surface landmarks.
COCO_TO_SMPL = {
    5: 16, 6: 17, 7: 18, 8: 19, 9: 20, 10: 21,
    11: 1, 12: 2, 13: 4, 14: 5, 15: 7, 16: 8,
}
COCO_JOINTS = np.asarray(tuple(COCO_TO_SMPL), dtype=np.int64)
SMPL_JOINTS = np.asarray(tuple(COCO_TO_SMPL.values()), dtype=np.int64)
TORSO_COCO = np.asarray([11, 12, 5, 6], dtype=np.int64)
TORSO_SMPL = np.asarray([1, 2, 16, 17], dtype=np.int64)
MIN_CONFIDENCE = 0.05
MAX_ESTIMATED_GAP_SECONDS = 0.25
FRAME_FITTED = "fitted_observations"
FRAME_ESTIMATED = "estimated_missing_data"
FRAME_UNAVAILABLE = "unavailable"


def validate_inputs(xyz, confidence, timestamps):
    """Validate layout/time and preserve missing observations as a separate mask."""
    xyz = np.asarray(xyz, dtype=np.float64)
    confidence = np.asarray(confidence, dtype=np.float64)
    timestamps = np.asarray(timestamps, dtype=np.float64)
    if xyz.ndim != 3 or xyz.shape[1:] != (17, 3) or len(xyz) == 0:
        raise ValueError("xyz must have nonempty shape [T, 17, 3] in metres, COCO17 order")
    if confidence.shape != xyz.shape[:2]:
        raise ValueError("confidence must have shape [T, 17]")
    if timestamps.shape != (len(xyz),) or not np.isfinite(timestamps).all():
        raise ValueError("timestamps must be finite seconds with shape [T]")
    if np.any(np.diff(timestamps) <= 0):
        raise ValueError("timestamps must be strictly increasing original capture times")
    finite_confidence = confidence[np.isfinite(confidence)]
    if np.any((finite_confidence < 0) | (finite_confidence > 1)):
        raise ValueError("confidence values must lie in [0, 1], or be NaN for missing data")
    if np.isinf(confidence).any():
        raise ValueError("confidence cannot contain infinity")
    observed = (
        np.isfinite(xyz).all(axis=-1)
        & np.isfinite(confidence)
        & (confidence >= MIN_CONFIDENCE)
    )
    return xyz, confidence, timestamps, observed


def _noncollinear(points):
    if len(points) < 3:
        return False
    singular = np.linalg.svd(points - points.mean(axis=0), compute_uv=False)
    return bool(singular[0] > 1e-5 and singular[1] > max(1e-5, singular[0] * 1e-3))


def classify_frames(xyz, observed, timestamps):
    """Support is data availability, not an accuracy or clinical quality claim."""
    supported = np.zeros(len(xyz), dtype=bool)
    for frame in range(len(xyz)):
        torso = TORSO_COCO[observed[frame, TORSO_COCO]]
        supported[frame] = (
            observed[frame, COCO_JOINTS].sum() >= 6
            and _noncollinear(xyz[frame, torso])
        )
    active = supported.copy()
    anchors = np.flatnonzero(supported)
    for left, right in zip(anchors[:-1], anchors[1:]):
        if timestamps[right] - timestamps[left] <= MAX_ESTIMATED_GAP_SECONDS:
            active[left:right + 1] = True
    status = np.full(len(xyz), FRAME_UNAVAILABLE, dtype="<U24")
    status[supported] = FRAME_FITTED
    status[active & ~supported] = FRAME_ESTIMATED
    return supported, active, status


def rigid_alignment(source, target, weights):
    """Weighted Kabsch, column-vector convention; rigid scale is always one."""
    source = np.asarray(source, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if (source.shape != target.shape or source.ndim != 2 or source.shape[1] != 3
            or weights.shape != (len(source),) or not np.isfinite(weights).all()
            or np.any(weights < 0) or weights.sum() <= 0):
        raise ValueError("rigid alignment needs paired [N,3] points and nonnegative weights")
    if not _noncollinear(source) or not _noncollinear(target):
        raise ValueError("rigid orientation needs at least three noncollinear points")
    weights = weights / weights.sum()
    source_mean = np.sum(source * weights[:, None], axis=0)
    target_mean = np.sum(target * weights[:, None], axis=0)
    covariance = ((source - source_mean) * weights[:, None]).T @ (target - target_mean)
    u, _, vt = np.linalg.svd(covariance)
    correction = np.eye(3)
    correction[-1, -1] = np.sign(np.linalg.det(vt.T @ u.T))
    rotation = vt.T @ correction @ u.T
    return rotation, target_mean - rotation @ source_mean


def _align_vector(source, target):
    """Minimum-twist proper rotation between two nonzero vectors."""
    source_norm, target_norm = np.linalg.norm(source), np.linalg.norm(target)
    if min(source_norm, target_norm) < 1e-8:
        return np.eye(3)
    a, b = source / source_norm, target / target_norm
    cross = np.cross(a, b)
    cosine = float(np.clip(a @ b, -1, 1))
    if cosine < -1 + 1e-7:
        axis = np.cross(a, np.eye(3)[np.argmin(np.abs(a))])
        axis /= np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    skew = np.array([[0, -cross[2], cross[1]], [cross[2], 0, -cross[0]],
                     [-cross[1], cross[0], 0]])
    return np.eye(3) + skew + (skew @ skew) / (1 + cosine)


def _initialize(rest, xyz, confidence, observed, timestamps, supported, active):
    from scipy.spatial.transform import Rotation, Slerp

    count = len(xyz)
    rotations = np.tile(np.eye(3), (count, 24, 1, 1))
    translations = np.full((count, 3), np.nan, dtype=np.float64)
    # joint -> child, and their COCO counterparts. No external floor/up axis.
    limbs = ((1, 4, 7, 11, 13, 15), (2, 5, 8, 12, 14, 16),
             (16, 18, 20, 5, 7, 9), (17, 19, 21, 6, 8, 10))
    for frame in np.flatnonzero(supported):
        valid_torso = observed[frame, TORSO_COCO]
        root, rigid_translation = rigid_alignment(
            rest[TORSO_SMPL[valid_torso]], xyz[frame, TORSO_COCO[valid_torso]],
            confidence[frame, TORSO_COCO[valid_torso]],
        )
        rotations[frame, 0] = root
        # SMPL rotates around its shaped pelvis, which remains at rest[0].
        translations[frame] = rigid_translation + root @ rest[0] - rest[0]
        for upper, middle, tip, coco_upper, coco_middle, coco_tip in limbs:
            if observed[frame, [coco_upper, coco_middle]].all():
                rotations[frame, upper] = _align_vector(
                    rest[middle] - rest[upper],
                    root.T @ (xyz[frame, coco_middle] - xyz[frame, coco_upper]),
                )
                if observed[frame, coco_tip]:
                    parent_rotation = root @ rotations[frame, upper]
                    rotations[frame, middle] = _align_vector(
                        rest[tip] - rest[middle],
                        parent_rotation.T @ (xyz[frame, coco_tip] - xyz[frame, coco_middle]),
                    )
    # Only interpolate short, bounded holes and retain their estimated status.
    anchors = np.flatnonzero(supported)
    for left, right in zip(anchors[:-1], anchors[1:]):
        missing = np.arange(left + 1, right)
        missing = missing[active[missing]]
        if len(missing) == 0:
            continue
        fraction = (timestamps[missing] - timestamps[left]) / (timestamps[right] - timestamps[left])
        translations[missing] = ((1 - fraction[:, None]) * translations[left]
                                 + fraction[:, None] * translations[right])
        for joint in range(24):
            interpolator = Slerp([timestamps[left], timestamps[right]],
                                 Rotation.from_matrix(rotations[[left, right], joint]))
            rotations[missing, joint] = interpolator(timestamps[missing]).as_matrix()
    axis_angles = Rotation.from_matrix(rotations.reshape(-1, 3, 3)).as_rotvec().reshape(count, 24, 3)
    return axis_angles[:, 0].astype(np.float32), axis_angles[:, 1:].reshape(count, 69).astype(np.float32), translations.astype(np.float32)


def _segments(active, timestamps):
    start = None
    for index in range(len(active)):
        gap = index > 0 and timestamps[index] - timestamps[index - 1] > MAX_ESTIMATED_GAP_SECONDS
        if start is not None and (not active[index] or gap):
            yield start, index
            start = None
        if active[index] and start is None:
            start = index
    if start is not None:
        yield start, len(active)


def _load_model(model_dir, device):
    import smplx

    model_dir = Path(model_dir).resolve()
    if (model_dir / "smpl" / "SMPL_NEUTRAL.pkl").is_file():
        model_dir /= "smpl"
    if not (model_dir / "SMPL_NEUTRAL.pkl").is_file():
        raise FileNotFoundError(f"Official neutral SMPL model missing: {model_dir / 'SMPL_NEUTRAL.pkl'}")
    model = smplx.SMPL(str(model_dir), gender="neutral", num_betas=10, batch_size=1,
                       create_betas=False, create_global_orient=False,
                       create_body_pose=False, create_transl=False).to(device)
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    return model


class _JointModel:
    """Exact official SMPL kinematic joints; no per-iteration vertex buffers."""

    def __init__(self, model):
        import torch
        from smplx.lbs import batch_rigid_transform, batch_rodrigues

        self.torch = torch
        self.rodrigues = batch_rodrigues
        self.transform = batch_rigid_transform
        self.rest = (model.J_regressor @ model.v_template).detach()
        self.basis = torch.einsum("jv,vck->jck", model.J_regressor, model.shapedirs).detach()
        self.parents = model.parents

    def shaped_rest(self, beta):
        return self.rest + self.torch.einsum("jck,k->jc", self.basis, beta.reshape(-1))

    def __call__(self, beta, orient, pose, translation):
        count = len(orient)
        aa = self.torch.cat([orient, pose], dim=1)
        rotations = self.rodrigues(aa.reshape(-1, 3)).reshape(count, 24, 3, 3)
        joints, _ = self.transform(rotations, self.shaped_rest(beta)[None].expand(count, -1, -1), self.parents)
        return joints + translation[:, None, :], rotations


def _temporal_loss(rotations, translations, timestamps):
    """Robust chordal SO(3) velocity penalty integrated over real elapsed time."""
    import torch

    if len(rotations) < 2:
        return rotations.sum() * 0
    dt = timestamps[1:] - timestamps[:-1]
    rotation_rate_sq = 0.5 * (rotations[1:] - rotations[:-1]).square().sum(dim=(-1, -2)) / dt[:, None].square()
    translation_rate_sq = ((translations[1:] - translations[:-1]) / dt[:, None]).square().sum(dim=-1)
    penalty = (2e-5 * torch.log1p(rotation_rate_sq / 25).mean(dim=-1)
               + 1e-5 * torch.log1p(translation_rate_sq))
    return (penalty * dt).sum() / dt.sum()


def _optimize(joint_model, beta, orient, pose, translation, targets, weights,
              timestamps, iterations, *, fit_shape=False, fixed_prefix=0):
    import torch

    device = joint_model.rest.device
    tensor = lambda value: torch.as_tensor(value, dtype=torch.float32, device=device)
    beta_var = tensor(beta).clone().detach().requires_grad_(fit_shape)
    variables = [tensor(value).clone().detach().requires_grad_(True) for value in (orient, pose, translation)]
    frozen = [value.detach().clone() for value in variables]
    optimizer = torch.optim.Adam([{"params": variables, "lr": 0.025}]
                                 + ([{"params": [beta_var], "lr": 0.015}] if fit_shape else []))
    target = tensor(np.nan_to_num(targets, nan=0, posinf=0, neginf=0))
    weight = tensor(weights)
    times = tensor(np.asarray(timestamps) - timestamps[0])
    identity = torch.eye(3, device=device)
    observed_indices = torch.as_tensor(SMPL_JOINTS, device=device)
    best_loss, best = float("inf"), None

    for _ in range(iterations):
        optimizer.zero_grad(set_to_none=True)
        current = [torch.cat([old[:fixed_prefix], value[fixed_prefix:]], dim=0)
                   if fixed_prefix else value for old, value in zip(frozen, variables)]
        joints, rotations = joint_model(beta_var, *current)
        squared_error = (joints.index_select(1, observed_indices) - target).square().sum(dim=-1)
        # Pseudo-Huber, 3 cm transition: distant outliers have bounded influence.
        robust_error = 2 * 0.03 * (torch.sqrt(squared_error + 0.03 ** 2) - 0.03)
        data_loss = (robust_error * weight).sum() / weight.sum().clamp_min(1)
        pose_prior = 1e-5 * (rotations[:, 1:] - identity).square().mean()
        shape_prior = 2e-4 * beta_var.square().mean()
        # Shape representatives are separated in time; no false adjacency.
        temporal = joints.sum() * 0 if fit_shape else _temporal_loss(rotations, current[2], times)
        loss = data_loss + pose_prior + shape_prior + temporal
        if not torch.isfinite(loss):
            raise RuntimeError("SMPL optimization became nonfinite; no successful fit was produced")
        scalar_loss = float(loss.detach().cpu())
        if scalar_loss < best_loss:
            best_loss = scalar_loss
            best = [beta_var.detach().clone()] + [value.detach().clone() for value in current]
        loss.backward()
        torch.nn.utils.clip_grad_norm_(variables + ([beta_var] if fit_shape else []), 1.0)
        optimizer.step()
        if fit_shape:
            with torch.no_grad():
                beta_var.clamp_(-3, 3)
    return tuple(value.cpu().numpy() for value in best), best_loss


def fit_smpl(xyz, confidence, timestamps, model_dir: Path, output_dir: Path,
             device="auto", iterations=100, *, export_vertices=False,
             export_keyframe=False) -> dict[str, Any]:
    """Fit verified metric COCO17 triangulation, keeping every original timestamp.

    ``iterations`` is the maximum per motion window; shape uses at most 80.
    Missing frames are retained with explicit status. Optional vertex files are
    actual official-SMPL outputs, streamed as ``vertices.npy``. No input is
    resampled, rescaled, projected to a floor, or converted into ground truth.
    Existing result files are never overwritten. See the module input contract.
    """
    xyz, confidence, timestamps, observed = validate_inputs(xyz, confidence, timestamps)
    if not isinstance(iterations, int) or isinstance(iterations, bool) or iterations < 1:
        raise ValueError("iterations must be a positive integer")
    supported, active, frame_status = classify_frames(xyz, observed, timestamps)
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in ("params.npz", "joints.npy", "fit_report.json", "vertices.npy", "keyframe.obj"):
        if (output_dir / name).exists():
            raise FileExistsError(f"Refusing to replace an existing fit: {output_dir / name}")
    count = len(xyz)
    beta = np.full(10, np.nan, dtype=np.float32)
    orient = np.full((count, 3), np.nan, dtype=np.float32)
    pose = np.full((count, 69), np.nan, dtype=np.float32)
    translation = np.full((count, 3), np.nan, dtype=np.float32)
    joints = np.full((count, 24, 3), np.nan, dtype=np.float32)
    residuals = np.full((count, len(COCO_JOINTS)), np.nan, dtype=np.float32)
    window_losses = []
    shape_indices = np.asarray([], dtype=np.int64)
    selected_device = None
    vertices_path = None
    keyframe_index = None
    warnings = [
        "Metric scale, calibration and synchronization are caller-verified prerequisites; arrays alone do not verify them.",
        "SMPL joints and detector landmarks differ anatomically. Fit residual is not independent accuracy.",
        "All fitted joints and surfaces are estimates; unobserved twist, spine, head, hands and feet are prior-driven.",
        "This baseline has weak neutral-pose regularization, not a learned pose prior or biomechanical/contact model.",
    ]

    if supported.any():
        import torch

        if device == "auto":
            selected_device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            selected_device = str(torch.device(device))
        if selected_device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but this PyTorch environment has no available CUDA device")
        model = _load_model(model_dir, selected_device)
        joint_model = _JointModel(model)
        beta = np.zeros(joint_model.basis.shape[-1], dtype=np.float32)
        rest = joint_model.rest.cpu().numpy()
        orient, pose, translation = _initialize(rest, xyz, confidence, observed, timestamps, supported, active)
        anchors = np.flatnonzero(supported)
        shape_indices = anchors[np.unique(np.round(np.linspace(0, len(anchors) - 1, min(32, len(anchors)))).astype(int))]
        weights = np.where(observed[:, COCO_JOINTS], confidence[:, COCO_JOINTS], 0).astype(np.float32)
        shape_parameters, shape_loss = _optimize(
            joint_model, beta, orient[shape_indices], pose[shape_indices], translation[shape_indices],
            xyz[shape_indices][:, COCO_JOINTS], weights[shape_indices], timestamps[shape_indices],
            min(80, iterations), fit_shape=True,
        )
        beta = shape_parameters[0]
        with torch.no_grad():
            rest = joint_model.shaped_rest(torch.as_tensor(beta, device=selected_device)).cpu().numpy()
        orient, pose, translation = _initialize(rest, xyz, confidence, observed, timestamps, supported, active)
        orient[shape_indices], pose[shape_indices], translation[shape_indices] = shape_parameters[1:]
        window_size, overlap = (128, 12) if selected_device.startswith("cuda") else (64, 8)
        for segment_start, segment_end in _segments(active, timestamps):
            start = segment_start
            while start < segment_end:
                end = min(start + window_size, segment_end)
                fixed = 0 if start == segment_start else overlap
                parameters, loss = _optimize(
                    joint_model, beta, orient[start:end], pose[start:end], translation[start:end],
                    xyz[start:end, COCO_JOINTS], weights[start:end], timestamps[start:end],
                    iterations, fixed_prefix=fixed,
                )
                orient[start:end], pose[start:end], translation[start:end] = parameters[1:]
                window_losses.append({"start_frame": start, "end_frame_exclusive": end,
                                      "fixed_overlap_frames": fixed, "objective": loss})
                if end == segment_end:
                    break
                start = end - overlap
        # Keep complete missing intervals explicit in every parameter array.
        for array in (orient, pose, translation):
            array[~active] = np.nan
        active_indices = np.flatnonzero(active)
        with torch.no_grad():
            for start in range(0, len(active_indices), window_size):
                indices = active_indices[start:start + window_size]
                values = [torch.as_tensor(value, dtype=torch.float32, device=selected_device)
                          for value in (beta, orient[indices], pose[indices], translation[indices])]
                evaluated, _ = joint_model(*values)
                joints[indices] = evaluated.cpu().numpy()
        residuals = np.linalg.norm(joints[:, SMPL_JOINTS] - xyz[:, COCO_JOINTS], axis=-1).astype(np.float32)
        residuals[~observed[:, COCO_JOINTS]] = np.nan
        if export_vertices or export_keyframe:
            vertices_path = output_dir / "vertices.npy" if export_vertices else None
            vertex_file = (np.lib.format.open_memmap(vertices_path, mode="w+", dtype=np.float32,
                           shape=(count, len(model.v_template), 3)) if export_vertices else None)
            if vertex_file is not None:
                # Initialize in bounded batches; no [T,6890,3] RAM allocation.
                for start in range(0, count, 16):
                    vertex_file[start:start + 16] = np.nan
            keyframe_index = int(anchors[np.argmax(observed[anchors][:, COCO_JOINTS].sum(axis=1))]) if export_keyframe else None
            mesh_indices = active_indices if export_vertices else np.asarray([keyframe_index])
            with torch.no_grad():
                for start in range(0, len(mesh_indices), 8):
                    indices = mesh_indices[start:start + 8]
                    as_tensor = lambda value: torch.as_tensor(value, dtype=torch.float32, device=selected_device)
                    result = model(betas=as_tensor(beta[None]).expand(len(indices), -1),
                                   global_orient=as_tensor(orient[indices]), body_pose=as_tensor(pose[indices]),
                                   transl=as_tensor(translation[indices]), return_verts=True)
                    vertices = result.vertices.cpu().numpy()
                    if vertex_file is not None:
                        vertex_file[indices] = vertices
                    if keyframe_index in indices:
                        selected = vertices[int(np.flatnonzero(indices == keyframe_index)[0])]
                        with (output_dir / "keyframe.obj").open("x", encoding="utf-8") as handle:
                            handle.write(f"# Official SMPL estimate; frame {keyframe_index}; seconds {timestamps[keyframe_index]:.9f}\n")
                            for vertex in selected:
                                handle.write("v {:.7f} {:.7f} {:.7f}\n".format(*vertex))
                            for face in model.faces:
                                handle.write("f {} {} {}\n".format(*(face + 1)))
            if vertex_file is not None:
                vertex_file.flush()
                del vertex_file
        if np.any(np.abs(beta) >= 2.99):
            warnings.append("At least one shape coefficient reached its bound; check metric calibration and landmark correspondence.")
    else:
        shape_loss = None
        warnings.append("No frames have six limb observations and a noncollinear three-point torso; no body was fitted.")

    params_path, joints_path = output_dir / "params.npz", output_dir / "joints.npy"
    with params_path.open("xb") as handle:
        np.savez_compressed(handle, betas=beta, global_orient=orient, body_pose=pose,
                            transl=translation, joints=joints, timestamps=timestamps,
                            scale=np.asarray(1.0), frame_status=frame_status,
                            observation_mask=observed, confidence=confidence, target_xyz=xyz,
                            coco_indices=COCO_JOINTS, smpl_indices=SMPL_JOINTS,
                            residual_m=residuals, shape_frame_indices=shape_indices)
    with joints_path.open("xb") as handle:
        np.save(handle, joints, allow_pickle=False)
    finite_residuals = residuals[np.isfinite(residuals)]
    report = {
        "schema_version": "1.0", "status": "completed" if supported.any() else "no_supported_frames",
        "output_dir": str(output_dir), "params_path": str(params_path),
        "joints_path": str(joints_path), "report_path": str(output_dir / "fit_report.json"),
        "vertices_path": str(vertices_path) if vertices_path else None,
        "keyframe_index": keyframe_index, "frames": count,
        "fitted_frames": int(supported.sum()), "estimated_frames": int((active & ~supported).sum()),
        "unavailable_frames": int((~active).sum()), "device": selected_device,
        "timestamps_preserved": True, "scale": 1.0, "units": "metres",
        "coordinate_frame": "unchanged_input_reconstruction_frame", "gender_model": "neutral",
        "shape_is_shared": True, "shape_fit_objective": shape_loss,
        "max_estimated_gap_seconds": MAX_ESTIMATED_GAP_SECONDS,
        "min_observation_confidence": MIN_CONFIDENCE,
        "fit_residual_mean_m": float(finite_residuals.mean()) if finite_residuals.size else None,
        "fit_residual_p95_m": float(np.percentile(finite_residuals, 95)) if finite_residuals.size else None,
        "residual_is_accuracy": False, "model_output_is_measurement": False,
        "frame_status_meanings": {
            FRAME_FITTED: "Model estimate fitted to sufficient observed limb/torso points; accuracy unverified.",
            FRAME_ESTIMATED: "Model estimate in a short bounded interval with insufficient observations.",
            FRAME_UNAVAILABLE: "Insufficient unbounded/long-gap data; model output is NaN.",
        },
        "window_objectives": window_losses, "warnings": warnings,
    }
    with (output_dir / "fit_report.json").open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
    return report
