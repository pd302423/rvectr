import numpy as np
from typing import List, Dict

def trendelenburg_score(left_hip_y: np.ndarray, right_hip_y: np.ndarray, gait_cycles: List[Dict]) -> List[float]:
    """
    During single-leg stance, measures contralateral hip drop.
    If only Y coordinates are provided, this returns the maximum Y drop of the contralateral hip 
    relative to the stance hip (units are same as input, typically meters).
    
    Args:
        left_hip_y: (N,) array of left hip Y positions.
        right_hip_y: (N,) array of right hip Y positions.
        gait_cycles: List of gait cycle dictionaries.
        
    Returns:
        List of Trendelenburg scores (maximum contralateral drop per cycle).
    """
    scores = []
    
    for cycle in gait_cycles:
        start = cycle['start_frame']
        stance_end = start + cycle['stance_frames']
        
        # Single-leg stance typically occurs in the middle of the stance phase
        # We look at the maximum drop of the opposite hip during the stance phase
        if cycle['side'] == 'left':
            # Left is in stance, check right hip drop (left_y - right_y)
            drop = left_hip_y[start:stance_end] - right_hip_y[start:stance_end]
            scores.append(float(np.max(drop)))
        else:
            # Right is in stance, check left hip drop (right_y - left_y)
            drop = right_hip_y[start:stance_end] - left_hip_y[start:stance_end]
            scores.append(float(np.max(drop)))
            
    return scores

def trunk_rotation(left_shoulder: np.ndarray, right_shoulder: np.ndarray, 
                   left_hip: np.ndarray, right_hip: np.ndarray) -> np.ndarray:
    """
    Computes trunk-pelvis rotation angle per frame in the transverse plane (X-Z).
    
    Args:
        left_shoulder, right_shoulder: (N, 3) arrays of shoulder positions.
        left_hip, right_hip: (N, 3) arrays of hip positions.
        
    Returns:
        (N,) array of trunk rotation angles in degrees.
    """
    # Shoulder vector in X-Z plane (assuming Y is up)
    shoulder_vec = right_shoulder[:, [0, 2]] - left_shoulder[:, [0, 2]]
    # Pelvis vector in X-Z plane
    pelvis_vec = right_hip[:, [0, 2]] - left_hip[:, [0, 2]]
    
    # Normalize vectors
    shoulder_norms = np.linalg.norm(shoulder_vec, axis=1, keepdims=True)
    pelvis_norms = np.linalg.norm(pelvis_vec, axis=1, keepdims=True)
    
    # Avoid division by zero
    shoulder_norms[shoulder_norms == 0] = 1.0
    pelvis_norms[pelvis_norms == 0] = 1.0
    
    shoulder_dir = shoulder_vec / shoulder_norms
    pelvis_dir = pelvis_vec / pelvis_norms
    
    # Dot product for angle
    dot_prod = np.sum(shoulder_dir * pelvis_dir, axis=1)
    dot_prod = np.clip(dot_prod, -1.0, 1.0)
    
    # Angle in degrees
    angles = np.arccos(dot_prod) * (180.0 / np.pi)
    return angles

def arm_swing_symmetry(left_wrist: np.ndarray, right_wrist: np.ndarray, fps: float) -> float:
    """
    Compares left vs right arm swing amplitude.
    
    Args:
        left_wrist, right_wrist: (N, 3) arrays of wrist positions.
        fps: Frames per second (unused for amplitude but included for signature matching).
        
    Returns:
        Symmetry index (absolute difference in amplitude / average amplitude).
        0 = perfect symmetry, higher = worse.
    """
    # Compute amplitude as the range of motion in the anterior-posterior axis (Z-axis, index 2)
    # Alternatively, use 3D bounding box diagonal. We'll use Z-axis range.
    left_amp = np.ptp(left_wrist[:, 2])
    right_amp = np.ptp(right_wrist[:, 2])
    
    mean_amp = (left_amp + right_amp) / 2.0
    if mean_amp == 0:
        return 0.0
        
    return float(abs(left_amp - right_amp) / mean_amp)
