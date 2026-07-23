"""
extract_kinematics.py — 3D Biomechanical Kinematics Extraction

Extracts per-frame joint angles, segment lengths, velocities, and angular
velocities from a sequence of SMPL mesh .obj files.

Uses the SMPL J_regressor (24 x 6890 sparse matrix) to map mesh vertices
to 24 anatomical joint positions. This works for any body shape, any
orientation, and any pose — no magic numbers or body-specific tuning.

SMPL 24-Joint Index Map:
    0  Pelvis          12 Neck
    1  Left Hip        13 Left Collar
    2  Right Hip       14 Right Collar
    3  Spine (lower)   15 Head
    4  Left Knee       16 Left Shoulder
    5  Right Knee      17 Right Shoulder
    6  Spine (mid)     18 Left Elbow
    7  Left Ankle      19 Right Elbow
    8  Right Ankle     20 Left Wrist
    9  Spine (upper)   21 Right Wrist
    10 Left Foot       22 Left Hand
    11 Right Foot      23 Right Hand

Usage:
    python extract_kinematics.py [--mesh-dir DIR] [--output FILE] [--fps N]
"""

import trimesh
import numpy as np
import scipy.sparse
import glob
import os
import json
import pickle
import argparse


# ---------------------------------------------------------------------------
# SMPL joint indices (standard 24-joint ordering)
# ---------------------------------------------------------------------------
PELVIS       = 0
L_HIP        = 1
R_HIP        = 2
SPINE_LOWER  = 3
L_KNEE       = 4
R_KNEE       = 5
SPINE_MID    = 6
L_ANKLE      = 7
R_ANKLE      = 8
SPINE_UPPER  = 9
L_FOOT       = 10
R_FOOT       = 11
NECK         = 12
L_COLLAR     = 13
R_COLLAR     = 14
HEAD         = 15
L_SHOULDER   = 16
R_SHOULDER   = 17
L_ELBOW      = 18
R_ELBOW      = 19
L_WRIST      = 20
R_WRIST      = 21
L_HAND       = 22
R_HAND       = 23


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SMPL_MODEL_PATH = os.path.join(
    SCRIPT_DIR, "EasyMocap", "data", "smplx", "SMPL_NEUTRAL.pkl"
)


# ---------------------------------------------------------------------------
# Core math
# ---------------------------------------------------------------------------
def calculate_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """
    Calculate the angle at point B formed by rays BA and BC.
    Returns the angle in degrees.
    """
    ba = a - b
    bc = c - b
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba < 1e-8 or norm_bc < 1e-8:
        return 0.0
    cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return float(np.degrees(angle))


def load_j_regressor(smpl_model_path: str) -> np.ndarray:
    """
    Load the SMPL J_regressor matrix (24 x 6890) from a pickle file.
    Handles both sparse and dense formats.
    """
    with open(smpl_model_path, "rb") as f:
        smpl_data = pickle.load(f, encoding="latin1")

    J_reg = smpl_data["J_regressor"]

    # Convert to dense numpy array if sparse
    if scipy.sparse.issparse(J_reg):
        J_reg = np.array(J_reg.todense())
    elif not isinstance(J_reg, np.ndarray):
        J_reg = np.array(J_reg)

    assert J_reg.shape == (24, 6890), (
        f"Expected J_regressor shape (24, 6890), got {J_reg.shape}"
    )
    return J_reg


def get_joints(vertices: np.ndarray, J_regressor: np.ndarray) -> np.ndarray:
    """
    Map 6890 mesh vertices to 24 anatomical joint positions.
    Returns (24, 3) array of joint 3D coordinates.
    """
    return J_regressor @ vertices


def extract_frame_kinematics(
    joints: np.ndarray,
    prev_depth: float | None,
    fps: float,
) -> dict:
    """
    Given 24 joint positions for a single frame, compute all biomechanical
    metrics: joint angles, torso lean, depth, velocity, segment lengths.
    """
    # Unpack joint positions
    pelvis      = joints[PELVIS]
    l_hip       = joints[L_HIP]
    r_hip       = joints[R_HIP]
    l_knee      = joints[L_KNEE]
    r_knee      = joints[R_KNEE]
    l_ankle     = joints[L_ANKLE]
    r_ankle     = joints[R_ANKLE]
    l_foot      = joints[L_FOOT]
    r_foot      = joints[R_FOOT]
    l_shoulder  = joints[L_SHOULDER]
    r_shoulder  = joints[R_SHOULDER]
    head        = joints[HEAD]
    neck        = joints[NECK]

    # --- Joint Angles ---

    # Knee flexion: Hip → Knee → Ankle
    left_knee_angle  = calculate_angle(l_hip, l_knee, l_ankle)
    right_knee_angle = calculate_angle(r_hip, r_knee, r_ankle)

    # Hip flexion: Shoulder → Hip → Knee
    left_hip_angle  = calculate_angle(l_shoulder, l_hip, l_knee)
    right_hip_angle = calculate_angle(r_shoulder, r_hip, r_knee)

    # Ankle dorsiflexion: Knee → Ankle → Foot
    left_ankle_angle  = calculate_angle(l_knee, l_ankle, l_foot)
    right_ankle_angle = calculate_angle(r_knee, r_ankle, r_foot)

    # Elbow flexion: Shoulder → Elbow → Wrist
    l_elbow    = joints[L_ELBOW]
    r_elbow    = joints[R_ELBOW]
    l_wrist    = joints[L_WRIST]
    r_wrist    = joints[R_WRIST]
    left_elbow_angle  = calculate_angle(l_shoulder, l_elbow, l_wrist)
    right_elbow_angle = calculate_angle(r_shoulder, r_elbow, r_wrist)

    # --- Torso & Posture ---

    # Torso lean: angle of spine vector relative to vertical Y-axis
    spine_vector = head - pelvis
    vertical = np.array([0, -1, 0])
    norm_spine = np.linalg.norm(spine_vector)
    if norm_spine > 1e-8:
        cosine_lean = np.dot(spine_vector, vertical) / norm_spine
        torso_lean = float(np.degrees(np.arccos(np.clip(cosine_lean, -1.0, 1.0))))
    else:
        torso_lean = 0.0

    # Shoulder tilt: angle of shoulder line in the frontal plane
    shoulder_tilt = float(np.degrees(np.arctan2(
        r_shoulder[1] - l_shoulder[1],
        r_shoulder[0] - l_shoulder[0]
    )))

    # Pelvic tilt: angle of hip line in the frontal plane
    pelvic_tilt = float(np.degrees(np.arctan2(
        r_hip[1] - l_hip[1],
        r_hip[0] - l_hip[0]
    )))

    # --- Depth & Velocity ---

    squat_depth = float(pelvis[1])
    velocity = 0.0
    if prev_depth is not None:
        velocity = (squat_depth - prev_depth) * fps

    # --- Spatial Metrics ---

    knee_distance = float(np.linalg.norm(l_knee - r_knee))
    ankle_distance = float(np.linalg.norm(l_ankle - r_ankle))

    # --- Segment Lengths ---

    l_femur_len     = float(np.linalg.norm(l_hip - l_knee))
    r_femur_len     = float(np.linalg.norm(r_hip - r_knee))
    l_tibia_len     = float(np.linalg.norm(l_knee - l_ankle))
    r_tibia_len     = float(np.linalg.norm(r_knee - r_ankle))
    torso_len       = float(np.linalg.norm(pelvis - neck))
    shoulder_width  = float(np.linalg.norm(l_shoulder - r_shoulder))
    hip_width       = float(np.linalg.norm(l_hip - r_hip))

    return {
        # Joint angles
        "left_knee_angle":    round(left_knee_angle, 2),
        "right_knee_angle":   round(right_knee_angle, 2),
        "left_hip_angle":     round(left_hip_angle, 2),
        "right_hip_angle":    round(right_hip_angle, 2),
        "left_ankle_angle":   round(left_ankle_angle, 2),
        "right_ankle_angle":  round(right_ankle_angle, 2),
        "left_elbow_angle":   round(left_elbow_angle, 2),
        "right_elbow_angle":  round(right_elbow_angle, 2),
        # Posture
        "torso_lean":         round(torso_lean, 2),
        "shoulder_tilt":      round(shoulder_tilt, 2),
        "pelvic_tilt":        round(pelvic_tilt, 2),
        # Depth & motion
        "squat_depth":        round(squat_depth, 4),
        "velocity":           round(velocity, 4),
        # Spatial
        "knee_distance":      round(knee_distance, 4),
        "ankle_distance":     round(ankle_distance, 4),
        # Segment lengths
        "l_femur_len":        round(l_femur_len, 4),
        "r_femur_len":        round(r_femur_len, 4),
        "l_tibia_len":        round(l_tibia_len, 4),
        "r_tibia_len":        round(r_tibia_len, 4),
        "torso_len":          round(torso_len, 4),
        "shoulder_width":     round(shoulder_width, 4),
        "hip_width":          round(hip_width, 4),
    }


def compute_angular_velocities(data: list[dict], fps: float) -> list[dict]:
    """
    Compute angular velocity (degrees/second) for each joint angle using
    central differences. Adds *_velocity keys to each frame dict.
    """
    angle_keys = [
        "left_knee_angle", "right_knee_angle",
        "left_hip_angle", "right_hip_angle",
        "left_ankle_angle", "right_ankle_angle",
        "left_elbow_angle", "right_elbow_angle",
    ]

    dt = 1.0 / fps

    for key in angle_keys:
        angles = np.array([d[key] for d in data])
        angular_vel = np.gradient(angles, dt)
        vel_key = key.replace("_angle", "_angular_vel")
        for i, d in enumerate(data):
            d[vel_key] = round(float(angular_vel[i]), 2)

    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Extract 3D biomechanical kinematics from SMPL mesh sequences."
    )
    parser.add_argument(
        "--mesh-dir",
        default=os.path.join(SCRIPT_DIR, "squat_demo_out"),
        help="Directory containing .obj mesh files (default: squat_demo_out/)",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(SCRIPT_DIR, "squat_kinematics.json"),
        help="Output JSON file path (default: squat_kinematics.json)",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=30.0,
        help="Video frame rate for velocity calculations (default: 30)",
    )
    parser.add_argument(
        "--smpl-model",
        default=SMPL_MODEL_PATH,
        help="Path to SMPL model .pkl file containing J_regressor",
    )
    args = parser.parse_args()

    # Load the J_regressor
    print(f"Loading SMPL J_regressor from {args.smpl_model}...")
    J_regressor = load_j_regressor(args.smpl_model)
    print(f"  J_regressor shape: {J_regressor.shape}")

    # Find mesh files
    obj_files = sorted(glob.glob(os.path.join(args.mesh_dir, "*.obj")))
    if not obj_files:
        print(f"No .obj files found in {args.mesh_dir}")
        return

    print(f"Processing {len(obj_files)} frames from {args.mesh_dir}...")

    data = []
    prev_depth = None

    for i, obj_path in enumerate(obj_files):
        mesh = trimesh.load(obj_path, process=False)
        vertices = mesh.vertices

        if vertices.shape[0] != 6890:
            print(f"  WARNING: Frame {i+1} has {vertices.shape[0]} vertices "
                  f"(expected 6890 for SMPL). Skipping.")
            continue

        # Map vertices → 24 joints via regressor
        joints = get_joints(vertices, J_regressor)

        # Extract all metrics
        frame_data = extract_frame_kinematics(joints, prev_depth, args.fps)
        frame_data["frame"] = i + 1
        prev_depth = frame_data["squat_depth"]

        data.append(frame_data)

        if (i + 1) % 50 == 0 or (i + 1) == len(obj_files):
            print(f"  Processed {i + 1}/{len(obj_files)} frames")

    # Compute angular velocities across the full sequence
    if len(data) > 1:
        print("Computing angular velocities...")
        data = compute_angular_velocities(data, args.fps)

    # Save
    with open(args.output, "w") as f:
        json.dump(data, f, indent=4)

    print(f"\nExtracted kinematics for {len(data)} frames → {args.output}")
    print(f"  Metrics per frame: {len(data[0]) if data else 0}")


if __name__ == "__main__":
    main()
