import numpy as np
from typing import List, Dict

def ground_contact_time(gait_cycle: Dict, fps: float) -> float:
    """
    Computes ground contact time (GCT) in milliseconds.
    
    Args:
        gait_cycle: Dictionary containing gait cycle info.
        fps: Frames per second.
        
    Returns:
        Ground contact time in milliseconds.
    """
    return (gait_cycle['stance_frames'] / fps) * 1000.0

def flight_time(gait_cycles: List[Dict], fps: float) -> List[float]:
    """
    Computes flight time (time both feet are airborne) in milliseconds.
    Assumes gait_cycles are sorted by start_frame and alternate between left and right.
    
    Args:
        gait_cycles: List of alternating gait cycle dictionaries.
        fps: Frames per second.
        
    Returns:
        List of flight times in milliseconds.
    """
    flight_times = []
    # Sort just in case
    sorted_cycles = sorted(gait_cycles, key=lambda x: x['start_frame'])
    
    for i in range(len(sorted_cycles) - 1):
        curr_cycle = sorted_cycles[i]
        next_cycle = sorted_cycles[i + 1]
        
        # Flight time is the time from toe-off of current cycle to foot-strike of next cycle
        toe_off_frame = curr_cycle['start_frame'] + curr_cycle['stance_frames']
        next_strike_frame = next_cycle['start_frame']
        
        flight_frames = next_strike_frame - toe_off_frame
        if flight_frames > 0:
            flight_times.append((flight_frames / fps) * 1000.0)
        else:
            flight_times.append(0.0)
            
    return flight_times

def stride_length(pelvis_positions: np.ndarray, gait_cycle: Dict) -> float:
    """
    Computes world-coordinate pelvis displacement per stride.
    
    Args:
        pelvis_positions: (N, 3) array of 3D pelvis positions.
        gait_cycle: Dictionary containing gait cycle info.
        
    Returns:
        Stride length in meters (or same units as pelvis_positions).
    """
    start_pos = pelvis_positions[gait_cycle['start_frame']]
    end_pos = pelvis_positions[gait_cycle['end_frame']]
    # Horizontal plane displacement (assuming Y is up)
    displacement = np.sqrt((end_pos[0] - start_pos[0])**2 + (end_pos[2] - start_pos[2])**2)
    return float(displacement)

def cadence(gait_cycles: List[Dict], fps: float) -> float:
    """
    Computes cadence in steps per minute.
    
    Args:
        gait_cycles: List of gait cycle dictionaries.
        fps: Frames per second.
        
    Returns:
        Cadence in steps per minute.
    """
    if len(gait_cycles) < 2:
        return 0.0
        
    sorted_cycles = sorted(gait_cycles, key=lambda x: x['start_frame'])
    start_frame = sorted_cycles[0]['start_frame']
    end_frame = sorted_cycles[-1]['start_frame']
    
    total_time_minutes = (end_frame - start_frame) / fps / 60.0
    
    if total_time_minutes == 0:
        return 0.0
        
    # Each gait cycle starts with a step
    return len(sorted_cycles) / total_time_minutes

def vertical_oscillation(pelvis_positions: np.ndarray, gait_cycle: Dict) -> float:
    """
    Computes pelvis Y range per stride.
    
    Args:
        pelvis_positions: (N, 3) array of 3D pelvis positions (assuming Y is index 1).
        gait_cycle: Dictionary containing gait cycle info.
        
    Returns:
        Vertical oscillation (range of Y) in units of pelvis_positions.
    """
    start = gait_cycle['start_frame']
    end = gait_cycle['end_frame']
    y_positions = pelvis_positions[start:end, 1]
    return float(np.ptp(y_positions))

def duty_factor(gait_cycle: Dict) -> float:
    """
    Computes fraction of cycle spent in stance.
    
    Args:
        gait_cycle: Dictionary containing gait cycle info.
        
    Returns:
        Duty factor (0.0 to 1.0).
    """
    total_frames = gait_cycle['end_frame'] - gait_cycle['start_frame']
    if total_frames == 0:
        return 0.0
    return gait_cycle['stance_frames'] / total_frames

def stride_symmetry(left_cycles: List[Dict], right_cycles: List[Dict], fps: float) -> float:
    """
    Computes stride symmetry index based on contact times.
    0 = perfect symmetry, higher = worse.
    
    Args:
        left_cycles: List of left gait cycles.
        right_cycles: List of right gait cycles.
        fps: Frames per second.
        
    Returns:
        Symmetry index (absolute difference in mean GCT divided by average mean GCT).
    """
    if not left_cycles or not right_cycles:
        return 0.0
        
    left_gct = np.mean([ground_contact_time(c, fps) for c in left_cycles])
    right_gct = np.mean([ground_contact_time(c, fps) for c in right_cycles])
    
    mean_gct = (left_gct + right_gct) / 2.0
    if mean_gct == 0:
        return 0.0
        
    return abs(left_gct - right_gct) / mean_gct
