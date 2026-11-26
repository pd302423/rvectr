import numpy as np
import pytest

from rvectr import squat
from rvectr.sync import interpolate_observations
from .test_squat_estimator import make_trace


@pytest.mark.parametrize("dwell", [0, .25, 1.6])
def test_noisy_complete_or_cut_at_bottom(dwell):
    t, h, b = make_trace(depths=(.30,), dwell_s=dwell, noise_m=.004, rng=np.random.default_rng(0))
    assert squat.segment_reps(t, h)[0][0]["bottom_observed"]
    for keep in (t <= b[0], t >= b[0], t >= b[0] - .6, t <= b[0] + .6):
        rep = squat.segment_reps(t[keep], h[keep], standing=.95)[0][0]
        assert not rep["bottom_observed"]
        assert rep["depth_m"] > .2 and np.isnan(rep["depth_se_m"])


def test_timestamp_hole_and_two_dips():
    t, h, _ = make_trace(depths=(.3, .3))
    keep = (t <= 4) | (t >= 4 + 26/60)
    partial = squat.segment_reps(t[keep], h[keep])[0]
    assert all(not r["bottom_observed"] and r["coverage"] < 1 for r in partial if r["bottom_s"] < 8)
    assert partial[-1]["bottom_observed"]
    # The squat cut by the hole comes out as pieces, and every piece says so.
    assert all(r["split_by_gap"] for r in partial if r["bottom_s"] < 8)
    assert not partial[-1]["split_by_gap"]
    keep = (t <= 5.2) | (t >= 10.75)
    split = squat.segment_reps(t[keep], h[keep])[0]
    assert len(split) == 2 and not any(r["bottom_observed"] for r in split)
    assert all(r["split_by_gap"] for r in split)


def test_short_timestamp_hole_lowers_coverage_without_splitting_the_squat():
    t, h, _ = make_trace(depths=(.3,))
    whole = squat.segment_reps(t, h)[0]
    assert len(whole) == 1 and whole[0]["coverage"] == pytest.approx(1) and not whole[0]["split_by_gap"]
    # 0.35 s is under the split threshold max(0.4 s, 3 frames), so this stays one squat.
    keep = (t <= 4) | (t >= 4 + 21 / 60)
    assert np.diff(t[keep]).max() < 0.4
    holed = squat.segment_reps(t[keep], h[keep])[0]
    assert len(holed) == 1
    assert holed[0]["coverage"] < 1
    assert not holed[0]["split_by_gap"]
    assert holed[0]["depth_m"] == pytest.approx(whole[0]["depth_m"], abs=0.01)


def test_resampling_requires_two_observed_hips():
    xy = np.ones((3, 2, 2))
    conf = np.ones((3, 2))
    conf[1, 0] = 0
    out, scores = interpolate_observations([0, .02, .04], xy, conf, [.01, .03])
    assert np.isnan(out[:, 0]).all() and (scores[:, 0] == 0).all()
    assert np.isfinite(out[:, 1]).all()
