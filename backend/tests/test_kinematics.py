import pytest
import numpy as np
from extract_kinematics import (
    load_j_regressor,
    get_joints,
    extract_frame_kinematics,
    compute_angular_velocities,
    SMPL_MODEL_PATH
)

N_VERTS = 6890
N_JOINTS = 24


def test_load_j_regressor(j_regressor):
    """Requires the licensed SMPL model; skips without it."""
    assert j_regressor.shape == (N_JOINTS, N_VERTS)


def test_get_joints(sample_mesh_vertices, j_regressor):
    """End-to-end against real SMPL data; skips without the model and a mesh."""
    joints = get_joints(sample_mesh_vertices, j_regressor)
    assert joints.shape == (N_JOINTS, 3)


def test_get_joints_places_joints_at_predicted_positions():
    """
    Contract test with synthetic inputs, so it runs everywhere — including CI,
    where the SMPL model is absent and the two tests above skip.

    A joint regressor row is a set of convex weights over mesh vertices, so a
    joint must land exactly on the weighted mean of the vertices it selects.
    Building the regressor here means the expected answer is known in closed
    form, and a transposed or misapplied matmul cannot pass.
    """
    rng = np.random.default_rng(0)
    vertices = rng.random((N_VERTS, 3))

    J = np.zeros((N_JOINTS, N_VERTS))
    J[0, 0] = 1.0                    # joint 0 sits exactly on vertex 0
    J[1, 5] = J[1, 9] = 0.5          # joint 1 is the midpoint of vertices 5 and 9
    J[2, 100:104] = 0.25             # joint 2 is the centroid of vertices 100..103
    for j in range(3, N_JOINTS):     # remaining rows: arbitrary but normalised
        w = rng.random(N_VERTS)
        J[j] = w / w.sum()

    joints = get_joints(vertices, J)

    assert joints.shape == (N_JOINTS, 3)
    np.testing.assert_allclose(joints[0], vertices[0])
    np.testing.assert_allclose(joints[1], (vertices[5] + vertices[9]) / 2)
    np.testing.assert_allclose(joints[2], vertices[100:104].mean(axis=0))


def test_get_joints_is_translation_equivariant():
    """Translating the mesh must translate every joint by the same offset."""
    rng = np.random.default_rng(1)
    vertices = rng.random((N_VERTS, 3))
    w = rng.random((N_JOINTS, N_VERTS))
    J = w / w.sum(axis=1, keepdims=True)

    offset = np.array([1.5, -2.0, 0.25])
    moved = get_joints(vertices + offset, J)

    np.testing.assert_allclose(moved, get_joints(vertices, J) + offset, atol=1e-9)

def test_extract_frame_kinematics(sample_joints):
    data = extract_frame_kinematics(sample_joints, prev_depth=None, fps=30.0)
    expected_keys = [
        "left_knee_angle", "right_knee_angle", "left_hip_angle", "right_hip_angle",
        "left_ankle_angle", "right_ankle_angle", "left_elbow_angle", "right_elbow_angle",
        "torso_lean", "shoulder_tilt", "pelvic_tilt", "squat_depth", "velocity",
        "knee_distance", "ankle_distance", "l_femur_len", "r_femur_len",
        "l_tibia_len", "r_tibia_len", "torso_len", "shoulder_width", "hip_width"
    ]
    for key in expected_keys:
        assert key in data

def test_compute_angular_velocities(sample_joints):
    frame1 = extract_frame_kinematics(sample_joints, prev_depth=None, fps=30.0)
    frame2 = extract_frame_kinematics(sample_joints + 0.1, prev_depth=frame1["squat_depth"], fps=30.0)
    data = [frame1, frame2]
    result = compute_angular_velocities(data, fps=30.0)
    
    expected_vel_keys = [
        "left_knee_angular_vel", "right_knee_angular_vel", "left_hip_angular_vel", "right_hip_angular_vel",
        "left_ankle_angular_vel", "right_ankle_angular_vel", "left_elbow_angular_vel", "right_elbow_angular_vel"
    ]
    for frame in result:
        for key in expected_vel_keys:
            assert key in frame
