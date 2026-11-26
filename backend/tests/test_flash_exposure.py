import numpy as np
import pytest
from rvectr import flashsync


def pulses(rate, duration, onsets=(1.013, 5.018), anchor="start"):
    start = np.arange(6 * rate) / rate
    pts = start + {"start": 0, "centre": .5, "end": 1}[anchor] * duration
    levels = np.zeros_like(pts)
    for time in onsets:
        levels += 120 * np.clip((start + duration - time) / duration, 0, 1) * (start < time + .2)
    events = flashsync.detect_pulses(pts, levels, exposure={"pts_at": anchor, "duration_s": duration})
    return dict(zip(("start", "end"), events))


@pytest.mark.parametrize("durations", [(1/30, 1/60), (.018, .009)])
def test_mixed_rate_exposure_bounds(durations):
    a, b = pulses(30, durations[0]), pulses(60, durations[1], anchor="end")
    result = flashsync.align(a, b, 1/30)
    assert result["drift_checked"]
    for end in ("start", "end"):
        assert abs(result[end + "_offset_s"]) <= result[end + "_sampling_uncertainty_s"] + 1e-12
    if durations[0] == 1/30:
        assert abs(result["offset_s"]) < .0001


def test_distractor_and_missing_end_are_visible():
    a = pulses(30, .025)
    assert flashsync._pick([a["start"], dict(a["start"], onset_s=1.5, amplitude=250)], (0, 2)) is None
    result = flashsync.align(a, {"start": a["start"]}, 1/30)
    assert result["status"] == "offset_only" and not result["drift_checked"]
    assert result["end_sampling_uncertainty_s"] is None


def test_two_candidate_flashes_in_a_window_are_reported_as_ambiguous_not_missing():
    a = pulses(30, .025)
    reference = {**a, "candidate_counts": {"start": 1, "end": 1}}
    two_starts = {"start": None, "end": a["end"], "candidate_counts": {"start": 2, "end": 1}}
    result = flashsync.align(reference, two_starts, 1/30)
    assert result["status"] == "failed"
    assert result["reason"] == "start_pulse_ambiguous: candidate flashes in the start window: reference 1, other 2"
    # No flash at all keeps the "not found" reason.
    none_found = {"start": None, "end": None, "candidate_counts": {"start": 0, "end": 0}}
    assert flashsync.align(reference, none_found, 1/30)["reason"] == "start_pulse_not_found_in_both_cameras"
    # The same for the end window: the take stays offset-only, and the warning says why.
    two_ends = {"start": a["start"], "end": None, "candidate_counts": {"start": 1, "end": 2}}
    result = flashsync.align(reference, two_ends, 1/30)
    assert result["status"] == "offset_only" and not result["drift_checked"]
    assert result["warning"] == ("End pulse ambiguous (candidate flashes in the end window: reference 1, other 2)"
                                 ": drift could not be checked")


def test_speed_comparison_blocks_start_only_and_records_sync(tmp_path, monkeypatch):
    from rvectr import pipeline

    record = {"alignments": [{"status": "reference"}, {"status": "offset_only", "drift_checked": False}]}
    monkeypatch.setattr(flashsync, "synchronize", lambda *a: record)
    monkeypatch.setattr(pipeline, "_plot_sync", lambda *a: None)
    config = {"sync": {"method": "flash", "start_window_s": 2, "end_window_s": 2, "roi": {}},
              "experiment": {"annotations": "attempts.csv"}, "cameras": [{"id": "a"}, {"id": "b"}]}
    with pytest.raises(ValueError, match="end flash"):
        pipeline._sync(config, [], [], tmp_path)
    assert (tmp_path / "sync/sync.json").exists()
