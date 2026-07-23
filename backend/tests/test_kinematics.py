import pytest
import numpy as np
from extract_kinematics import (
    load_j_regressor,
    get_joints,
    extract_frame_kinematics,
    compute_angular_velocities,
    SMPL_MODEL_PATH
)

def test_load_j_regressor(j_regressor):
    assert j_regressor.shape == (24, 6890)

def test_get_joints(sample_mesh_vertices, j_regressor):
    joints = get_joints(sample_mesh_vertices, j_regressor)
    assert joints.shape == (24, 3)

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
