"""
Gait event detection tested against synthetic signals with KNOWN ground truth.

The point of constructing the signal ourselves is that we know exactly how many
strikes there are and where. A test that merely asserts "returns a list" would
pass against a broken detector.

Two families of fixture, and the distinction matters:

* **Square wave** (`_two_ankles`) — transitions are instantaneous, so the signal
  clears any hysteresis band between two adjacent samples. Good for asserting
  counts and exact event frames, useless for exercising the band itself. These
  fixtures passed against a detector that dropped 75% of events on real data.
* **Smooth sinusoid** (`_smooth_ankles`) — a real ankle trajectory takes several
  frames to traverse the band. This is the shape that catches band bugs, and the
  frame rate has to be swept because the failure got *worse* as fps rose.
"""

import numpy as np
import pytest

from pipeline.gait_events import (
    _detect_crossings,
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


def _smooth_ankles(fps, duration_s=4.0, step_hz=2.0, low=0.01, high=0.19):
    """
    Smooth sinusoidal ankle height, both sides in antiphase — the shape a real
    trajectory has. Crossings per side are known exactly: one per period.
    """
    n = int(duration_s * fps)
    t = np.arange(n) / fps
    mid = (low + high) / 2.0
    amp = (high - low) / 2.0
    left = mid + amp * np.sin(2 * np.pi * step_hz * t)
    right = mid + amp * np.sin(2 * np.pi * step_hz * t + np.pi)
    return np.column_stack([left, right]), int(duration_s * step_hz)


@pytest.mark.parametrize("fps", [30.0, 60.0, 120.0, 240.0])
@pytest.mark.parametrize("threshold", [0.10, 0.025])
def test_smooth_signal_detection_is_frame_rate_independent(fps, threshold):
    """
    The same motion sampled faster must not yield fewer events.

    This is the regression test for the hysteresis bug. The old detector required
    the signal to cross the whole band in one sample, so a higher frame rate —
    smaller per-frame step — dropped more events: 16/16 at 30 fps, 8/16 at
    120 fps, and 4/16 at 120 fps with the threshold near ground contact, which is
    where a foot-strike threshold actually belongs.
    """
    ankles, per_side = _smooth_ankles(fps)
    strikes = detect_foot_strikes(ankles, threshold=threshold, fps=fps)

    left = [e for e in strikes if e["side"] == "left"]
    right = [e for e in strikes if e["side"] == "right"]

    # One descending crossing per period per side; the window may clip one.
    assert per_side - 1 <= len(left) <= per_side
    assert per_side - 1 <= len(right) <= per_side


def test_smooth_signal_strikes_are_evenly_spaced():
    """A periodic input must give periodic events — no dropped or doubled steps."""
    fps = 120.0
    ankles, per_side = _smooth_ankles(fps, step_hz=2.0)

    strikes = detect_foot_strikes(ankles, threshold=0.05, fps=fps)
    left = sorted(e["frame"] for e in strikes if e["side"] == "left")

    assert len(left) >= 3
    gaps = np.diff(left)
    expected = fps / 2.0  # one step period at 2 Hz
    assert np.allclose(gaps, expected, atol=2), f"uneven step spacing: {gaps}"


def test_slow_traversal_through_band_is_not_dropped():
    """
    A signal that creeps across the threshold — many samples inside the
    hysteresis band — is the exact case the old two-sample comparison missed.
    """
    fps = 100.0
    # Descend across the threshold over 50 frames, then hold low.
    signal = np.concatenate([np.linspace(1.0, 0.0, 50), np.zeros(50)])
    ankles = np.column_stack([signal, signal])

    strikes = detect_foot_strikes(ankles, threshold=0.5, fps=fps)

    assert len([e for e in strikes if e["side"] == "left"]) == 1


def test_jitter_across_the_threshold_yields_one_event_not_many():
    """
    A descent that wobbles back and forth across the nominal threshold, without
    ever leaving the hysteresis band, is one foot strike — not one per wobble.

    Calls `_detect_crossings` with the refractory period disabled so this
    exercises the hysteresis band alone; otherwise the 200 ms lockout would mask
    the behaviour under test and the assertion would prove nothing.
    """
    rng = np.random.default_rng(0)
    descent = np.linspace(1.0, 0.52, 20)
    # 30 frames hovering at the threshold, jittering inside the +/-0.01 band.
    hover = 0.5 + rng.normal(0.0, 0.002, 30)
    settle = np.linspace(0.48, 0.0, 20)
    signal = np.concatenate([descent, hover, settle])

    events = _detect_crossings(signal, threshold=0.5, direction="down",
                               fps=100.0, side="left", refractory_s=0.0)

    assert len(events) == 1, f"jitter produced {len(events)} events"


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
