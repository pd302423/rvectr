"""
Stride metrics tested against hand-constructed cycles with known answers.

Each cycle here is built so the correct output is arithmetic we can state in the
assertion, rather than whatever the implementation happens to return.
"""

import numpy as np
import pytest

from pipeline.stride_metrics import (
    ground_contact_time,
    flight_time,
    stride_length,
    cadence,
    vertical_oscillation,
    duty_factor,
)

FPS = 100.0


def _cycle(start, end, stance, side="left"):
    return {
        "start_frame": start,
        "end_frame": end,
        "stance_frames": stance,
        "swing_frames": (end - start) - stance,
        "side": side,
    }


def test_ground_contact_time_converts_frames_to_ms():
    # 60 frames of stance at 100 fps = 0.6 s = 600 ms
    assert ground_contact_time(_cycle(0, 100, 60), FPS) == pytest.approx(600.0)


def test_duty_factor_is_stance_fraction():
    assert duty_factor(_cycle(0, 100, 60)) == pytest.approx(0.6)
    assert duty_factor(_cycle(0, 100, 100)) == pytest.approx(1.0)


def test_duty_factor_zero_length_cycle_does_not_divide_by_zero():
    assert duty_factor(_cycle(50, 50, 0)) == 0.0


def test_flight_time_gap_between_toe_off_and_next_strike():
    # Cycle A: starts 0, stance 60 -> toe-off at 60. Next strike at 80.
    # Flight = 20 frames = 200 ms.
    cycles = [_cycle(0, 160, 60, "left"), _cycle(80, 240, 60, "right")]
    assert flight_time(cycles, FPS) == [pytest.approx(200.0)]


def test_flight_time_clamps_overlap_to_zero():
    """When stance overlaps the next strike (both feet down) flight is 0, not
    negative."""
    cycles = [_cycle(0, 160, 100, "left"), _cycle(80, 240, 60, "right")]
    assert flight_time(cycles, FPS) == [0.0]


def test_stride_length_is_horizontal_displacement():
    pelvis = np.zeros((101, 3))
    pelvis[100] = [3.0, 1.2, 4.0]  # 3-4-5 triangle in the XZ plane
    # Y (height) must be excluded from the distance.
    assert stride_length(pelvis, _cycle(0, 100, 60)) == pytest.approx(5.0)


def test_vertical_oscillation_is_y_range_within_cycle():
    pelvis = np.zeros((200, 3))
    pelvis[:, 1] = np.linspace(0.0, 2.0, 200)
    # Within frames 0..100 the Y range is 100/199 * 2.0
    expected = np.ptp(pelvis[0:100, 1])
    assert vertical_oscillation(pelvis, _cycle(0, 100, 60)) == pytest.approx(expected)


def test_vertical_oscillation_ignores_motion_outside_the_cycle():
    pelvis = np.zeros((200, 3))
    pelvis[150:, 1] = 99.0  # a large excursion after the cycle ends
    assert vertical_oscillation(pelvis, _cycle(0, 100, 60)) == pytest.approx(0.0)


def test_cadence_counts_steps_per_minute():
    """
    Four steps starting at frames 0, 100, 200, 300 at 100 fps means one step
    every second. That is 60 steps per minute.

    Note the interval count: 4 step onsets span 3 intervals, so the rate is
    (n - 1) / elapsed, not n / elapsed. Using n would report 80 here.
    """
    cycles = [
        _cycle(0, 200, 60),
        _cycle(100, 300, 60),
        _cycle(200, 400, 60),
        _cycle(300, 500, 60),
    ]
    assert cadence(cycles, FPS) == pytest.approx(60.0)


def test_cadence_insufficient_data_returns_zero():
    assert cadence([], FPS) == 0.0
    assert cadence([_cycle(0, 100, 60)], FPS) == 0.0


def test_cadence_zero_elapsed_does_not_divide_by_zero():
    cycles = [_cycle(0, 100, 60), _cycle(0, 100, 60, "right")]
    assert cadence(cycles, FPS) == 0.0
