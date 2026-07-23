import numpy as np
from typing import List, Dict, Union

def _detect_crossings(signal: np.ndarray, threshold: float, direction: str, fps: float, side: str) -> List[Dict]:
    """Helper to find threshold crossings with hysteresis and minimum duration."""
    events = []
    min_frames = int(0.2 * fps)  # 200ms minimum between events
    last_frame = -min_frames
    
    # Simple hysteresis margin to prevent jitter
    margin = 0.01 * np.ptp(signal) if len(signal) > 0 else 0
    upper_thresh = threshold + margin
    lower_thresh = threshold - margin

    for i in range(1, len(signal)):
        if direction == 'down' and signal[i-1] >= upper_thresh and signal[i] < lower_thresh:
            if (i - last_frame) >= min_frames:
                events.append({'frame': i, 'time': i / fps, 'side': side})
                last_frame = i
        elif direction == 'up' and signal[i-1] <= lower_thresh and signal[i] > upper_thresh:
            if (i - last_frame) >= min_frames:
                events.append({'frame': i, 'time': i / fps, 'side': side})
                last_frame = i
    return events

def detect_foot_strikes(ankle_positions: np.ndarray, threshold: float, fps: float) -> List[Dict]:
    """
    Detects when ankle crosses below threshold (foot strike / initial contact).
    
    Args:
        ankle_positions: (N, 2) array of Y positions for left (0) and right (1) ankles.
        threshold: Y position threshold.
        fps: Frames per second.
        
    Returns:
        List of dictionaries containing frame, time, and side.
    """
    left_events = _detect_crossings(ankle_positions[:, 0], threshold, 'down', fps, 'left')
    right_events = _detect_crossings(ankle_positions[:, 1], threshold, 'down', fps, 'right')
    
    all_events = sorted(left_events + right_events, key=lambda x: x['frame'])
    return all_events

def detect_toe_offs(ankle_positions: np.ndarray, threshold: float, fps: float) -> List[Dict]:
    """
    Detects when ankle rises above threshold (toe-off).
    
    Args:
        ankle_positions: (N, 2) array of Y positions for left (0) and right (1) ankles.
        threshold: Y position threshold.
        fps: Frames per second.
        
    Returns:
        List of dictionaries containing frame, time, and side.
    """
    left_events = _detect_crossings(ankle_positions[:, 0], threshold, 'up', fps, 'left')
    right_events = _detect_crossings(ankle_positions[:, 1], threshold, 'up', fps, 'right')
    
    all_events = sorted(left_events + right_events, key=lambda x: x['frame'])
    return all_events

def detect_gait_cycles(foot_strikes: List[Dict], toe_offs: List[Dict]) -> List[Dict]:
    """
    Groups events into complete gait cycles (heel strike -> toe off -> swing -> heel strike).
    
    Args:
        foot_strikes: List of foot strike events.
        toe_offs: List of toe off events.
        
    Returns:
        List of dictionaries with start_frame, end_frame, stance_frames, swing_frames, and side.
    """
    cycles = []
    
    for side in ['left', 'right']:
        side_strikes = [e for e in foot_strikes if e['side'] == side]
        side_toeoffs = [e for e in toe_offs if e['side'] == side]
        
        for i in range(len(side_strikes) - 1):
            start_strike = side_strikes[i]
            end_strike = side_strikes[i+1]
            
            # Find toe-off between these strikes
            valid_toeoffs = [to for to in side_toeoffs if start_strike['frame'] < to['frame'] < end_strike['frame']]
            if valid_toeoffs:
                toe_off = valid_toeoffs[0]
                stance_frames = toe_off['frame'] - start_strike['frame']
                swing_frames = end_strike['frame'] - toe_off['frame']
                cycles.append({
                    'start_frame': start_strike['frame'],
                    'end_frame': end_strike['frame'],
                    'stance_frames': stance_frames,
                    'swing_frames': swing_frames,
                    'side': side
                })
                
    return sorted(cycles, key=lambda x: x['start_frame'])
