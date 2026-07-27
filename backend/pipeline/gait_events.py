import numpy as np
from typing import List, Dict

REFRACTORY_S = 0.2      # 200 ms minimum between events on one side
HYSTERESIS_FRAC = 0.01  # band half-width, as a fraction of signal range


def _detect_crossings(signal: np.ndarray, threshold: float, direction: str, fps: float,
                      side: str, refractory_s: float = REFRACTORY_S,
                      hysteresis_frac: float = HYSTERESIS_FRAC) -> List[Dict]:
    """
    Find confirmed threshold crossings with a two-state (Schmitt trigger) detector.

    The detector arms on the far side of the hysteresis band and fires only once
    the signal has traversed to the near side. Event timing is taken from the
    frame the signal first passed the *nominal* threshold, so widening the band
    rejects noise without shifting event times later.

    An earlier implementation compared `signal[i-1]` against one edge of the band
    and `signal[i]` against the other in a single test, which required the signal
    to clear the entire band between two adjacent samples. Any sample landing
    inside the band silently dropped the event — so raising the frame rate, which
    shrinks the per-frame step, lost *more* events rather than fewer. On a smooth
    2 Hz signal it found 16/16 events at 30 fps but only 4/16 at 120 fps with a
    threshold placed near ground contact. See the smooth-signal tests in
    tests/test_gait_events.py, which the old square-wave fixtures could not catch.
    """
    n = len(signal)
    if n == 0:
        return []

    events: List[Dict] = []
    min_frames = max(1, int(refractory_s * fps))
    last_frame = -min_frames

    margin = hysteresis_frac * float(np.ptp(signal))
    upper = threshold + margin
    lower = threshold - margin

    descending = direction == 'down'
    # Armed means "waiting on the far side"; the first sample sets the initial state.
    armed = signal[0] > threshold if descending else signal[0] < threshold
    pending = None  # frame at which the nominal threshold was first passed

    for i in range(1, n):
        v = signal[i]

        if not armed:
            # Re-arm once the signal has retreated fully past the far edge.
            if (descending and v >= upper) or (not descending and v <= lower):
                armed = True
            continue

        if pending is None:
            if (descending and v < threshold) or (not descending and v > threshold):
                pending = i
        elif (descending and v >= upper) or (not descending and v <= lower):
            pending = None  # bounced back before confirming; it was noise

        if pending is None:
            continue

        confirmed = v <= lower if descending else v >= upper
        if confirmed:
            if (pending - last_frame) >= min_frames:
                events.append({'frame': pending, 'time': pending / fps, 'side': side})
                last_frame = pending
            armed = False
            pending = None

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
