"""
Gait event detection tested against synthetic signals with KNOWN ground truth.

The point of constructing the signal ourselves is that we know exactly how many
strikes there are and where. A test that merely asserts "returns a list" would
pass against a broken detector.
"""

import numpy as np
import pytest

from pipeline.gait_events import (
    detect_foot_strikes,
    detect_toe_offs,
    detect_gait_cycles,
)

FPS = 100.0


def _synthetic_ankle_signal(n_steps, frames_per_step, n_frames, phase_offset=0):
    """
    Square-ish ankle height signal: low (planted) for the first half of each
    step, high (swinging) for the second half. Known strike count by
    construction.
    """
    sig = np.zeros(n_frames)
    for f in range(n_frames):
        pos_in_step = (f + phase_offset) % frames_per_step
        sig[f] = 0.0 if pos_in_step < frames_per_step // 2 else 1.0
    return sig


def _two_ankles(n_steps, frames_per_step, n_frames):
    """Left and right ankles in antiphase, as in real gait."""
    left = _synthetic_ankle_signal(n_steps, frames_per_step, n_frames)
    right = _synthetic_ankle_signal(
        n_steps, frames_per_step, n_frames, phase_offset=frames_per_step // 2
    )
    return np.column_stack([left, right])


def test_foot_strikes_counts_known_number_of_steps():
    frames_per_step = 50  # 0.5 s per step at 100 fps
    n_frames = 500  # 10 steps per side
    ankles = _two_ankles(10, frames_per_step, n_frames)

    strikes = detect_foot_strikes(ankles, threshold=0.5, fps=FPS)

    left = [e for e in strikes if e["side"] == "left"]
    right = [e for e in strikes if e["side"] == "right"]

    # 10 full steps per side; the first transition may be clipped by the window.
    assert 9 <= len(left) <= 10
    assert 9 <= len(right) <= 10


def test_foot_strikes_land_at_expected_frames():
    frames_per_step = 50
    n_frames = 300
    ankles = _two_ankles(6, frames_per_step, n_frames)

    strikes = detect_foot_strikes(ankles, threshold=0.5, fps=FPS)
    left_frames = [e["frame"] for e in strikes if e["side"] == "left"]

    # Left descends to planted at the start of each step period.
    for f in left_frames:
        assert f % frames_per_step == 0, f"strike at {f} is not on a step boundary"


def test_toe_offs_are_offset_from_strikes():
    frames_per_step = 50
    n_frames = 300
    ankles = _two_ankles(6, frames_per_step, n_frames)

    strikes = detect_foot_strikes(ankles, threshold=0.5, fps=FPS)
    toe_offs = detect_toe_offs(ankles, threshold=0.5, fps=FPS)

    left_strikes = sorted(e["frame"] for e in strikes if e["side"] == "left")
    left_toeoffs = sorted(e["frame"] for e in toe_offs if e["side"] == "left")

    assert left_strikes and left_toeoffs
    # Toe-off occurs mid-step, half a period after the strike.
    for strike in left_strikes[:-1]:
        following = [t for t in left_toeoffs if t > strike]
        assert following, f"no toe-off after strike at {strike}"
        assert following[0] - strike == pytest.approx(frames_per_step // 2, abs=2)


def test_minimum_event_spacing_rejects_jitter():
    """High-frequency noise crossing the threshold must not produce events
    closer together than the 200 ms refractory period."""
    n_frames = 400
    noisy = np.tile([0.0, 1.0], n_frames // 2)  # crosses every single frame
    ankles = np.column_stack([noisy, noisy])

    strikes = detect_foot_strikes(ankles, threshold=0.5, fps=FPS)
    left_frames = sorted(e["frame"] for e in strikes if e["side"] == "left")

    min_frames = int(0.2 * FPS)
    gaps = np.diff(left_frames)
    assert all(g >= min_frames for g in gaps), f"events too close together: {gaps}"


def test_gait_cycles_pair_strikes_with_intervening_toe_off():
    strikes = [
        {"frame": 0, "time": 0.0, "side": "left"},
        {"frame": 100, "time": 1.0, "side": "left"},
        {"frame": 200, "time": 2.0, "side": "left"},
    ]
    toe_offs = [
        {"frame": 60, "time": 0.6, "side": "left"},
        {"frame": 160, "time": 1.6, "side": "left"},
    ]

    cycles = detect_gait_cycles(strikes, toe_offs)

    assert len(cycles) == 2
    assert cycles[0]["start_frame"] == 0
    assert cycles[0]["end_frame"] == 100
    assert cycles[0]["stance_frames"] == 60
    assert cycles[0]["swing_frames"] == 40


def test_gait_cycles_skips_pairs_with_no_toe_off():
    """A strike pair with no toe-off between them is not a valid cycle."""
    strikes = [
        {"frame": 0, "time": 0.0, "side": "left"},
        {"frame": 100, "time": 1.0, "side": "left"},
    ]
    assert detect_gait_cycles(strikes, []) == []


def test_gait_cycles_does_not_mix_sides():
    strikes = [
        {"frame": 0, "time": 0.0, "side": "left"},
        {"frame": 100, "time": 1.0, "side": "right"},
        {"frame": 200, "time": 2.0, "side": "left"},
    ]
    toe_offs = [{"frame": 60, "time": 0.6, "side": "left"}]

    cycles = detect_gait_cycles(strikes, toe_offs)

    # The only valid left pair is 0 -> 200, with the toe-off at 60 inside it.
    assert len(cycles) == 1
    assert cycles[0]["side"] == "left"
    assert cycles[0]["start_frame"] == 0
    assert cycles[0]["end_frame"] == 200


def test_empty_input_returns_no_events():
    empty = np.zeros((0, 2))
    assert detect_foot_strikes(empty, threshold=0.5, fps=FPS) == []
    assert detect_toe_offs(empty, threshold=0.5, fps=FPS) == []
