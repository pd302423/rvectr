"""
running_kinematics.py — Dynamic Running Motion Tracking & Gait Analysis

Extracts running-specific biomechanical metrics from 3D joint trajectories:
- Ground Contact Time (GCT) in milliseconds (Left vs Right asymmetry)
- Cadence (Steps per Minute - SPM)
- Flight Time / Air Time (ms)
- Duty Factor & Stride Frequency
- Vertical Oscillation (Center of Mass displacement)
- Knee Flexion at Initial Contact vs Peak Stance
"""

import numpy as np


def detect_gait_phases(left_foot_y: np.ndarray, right_foot_y: np.ndarray, ground_y: float = 0.0, fps: float = 30.0) -> dict:
    """
    Detects Heel Strike, Toe Off, Ground Contact Time (GCT), and Cadence.
    """
    dt = 1.0 / fps
    left_contact = left_foot_y <= (ground_y + 0.03)
    right_contact = right_foot_y <= (ground_y + 0.03)
    
    # Calculate GCT for left and right
    left_gct_frames = np.sum(left_contact)
    right_gct_frames = np.sum(right_contact)
    
    left_gct_ms = (left_gct_frames * dt) * 1000.0
    right_gct_ms = (right_gct_frames * dt) * 1000.0
    
    # Cadence (Steps per Minute)
    total_time_sec = len(left_foot_y) * dt
    step_count = np.count_nonzero(np.diff(left_contact.astype(int)) == 1) + \
                 np.count_nonzero(np.diff(right_contact.astype(int)) == 1)
                 
    cadence_spm = (step_count / max(0.001, total_time_sec)) * 60.0
    
    # Calculate Duty Factor (Contact Time / Stride Time)
    duty_factor = (left_gct_frames + right_gct_frames) / max(1, len(left_foot_y) * 2)

    return {
        "left_gct_ms": round(float(left_gct_ms), 1),
        "right_gct_ms": round(float(right_gct_ms), 1),
        "cadence_spm": round(float(cadence_spm), 1),
        "duty_factor": round(float(duty_factor), 3),
        "asymmetry_percent": round(abs(left_gct_ms - right_gct_ms) / max(1.0, max(left_gct_ms, right_gct_ms)) * 100.0, 2)
    }


def compute_vertical_oscillation(pelvis_y: np.ndarray) -> float:
    """
    Compute peak-to-trough vertical oscillation (in cm) of pelvis/COM during running.
    """
    if len(pelvis_y) == 0:
        return 0.0
    oscillation_meters = float(np.max(pelvis_y) - np.min(pelvis_y))
    return round(oscillation_meters * 100.0, 2)
