import csv

import pytest

from rvectr.experiment import ANNOTATION_COLUMNS, load_annotations, score_condition


def write_annotations(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=ANNOTATION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def row(aid, bottom, role="test", label="match", **values):
    return {"annotation_id": aid, "start_s": bottom - 0.4, "bottom_s": bottom,
            "end_s": bottom + 0.4, "role": role, "label": label,
            "marker_depth_m": "", "marker_uncertainty_m": "", "reader": "R1",
            "reader_uncertainty_s": "", "reader_uncertainty_m": "", **values}


def test_annotation_file_requires_one_reference_and_keeps_unknown_uncertainty(tmp_path):
    path = write_annotations(tmp_path / "notes.csv", [
        row("base", 2.0, "reference", marker_depth_m="0.30", marker_uncertainty_m="0.01"),
        row("rep2", 4.0, reader_uncertainty_s="0.04"),
    ])
    parsed = load_annotations(path)
    assert parsed[1]["marker_uncertainty_m"] is None
    assert parsed[1]["reader_uncertainty_s"] == 0.04
    with pytest.raises(ValueError, match="exactly one reference"):
        load_annotations(write_annotations(tmp_path / "no_ref.csv", [row("rep2", 4.0)]))


def test_scoring_is_one_to_one_and_excludes_reference_from_denominator(tmp_path):
    annotations = [
        row("base", 1.0, "reference", marker_depth_m="0.30", marker_uncertainty_m="0.01",
            reader_uncertainty_m="0.005"),
        row("rep2", 2.0, label="match", marker_depth_m="0.27", marker_uncertainty_m="0.02",
            reader_uncertainty_m="0.004"),
        row("rep3", 3.0, label="shallow", marker_depth_m="0.20"),
        row("rep4", 4.0, label="rejected"),
        row("rep5", 5.0, label="unscorable"),
    ]
    reps = [
        {"rep": 1, "bottom_s": 1.02, "depth_m": .31, "coverage": .95, "bottom_observed": True,
         "depth_se_m": .001, "outcome": "reached_reference"},
        {"rep": 2, "bottom_s": 2.02, "depth_m": .28, "coverage": .95, "bottom_observed": True,
         "depth_se_m": .001, "outcome": "reached_reference"},
        {"rep": 3, "bottom_s": 3.02, "depth_m": .29, "coverage": .95, "bottom_observed": True,
         "depth_se_m": .001, "outcome": "reached_reference"},
        {"rep": 4, "bottom_s": 8.0, "depth_m": .2, "coverage": .95, "bottom_observed": True,
         "depth_se_m": .001, "outcome": "unclear"},
    ]
    annotations = load_annotations(write_annotations(tmp_path / "score.csv", annotations))
    scored = score_condition(annotations, reps)
    counts = scored["summary"]["counts"]
    assert counts["reference_excluded"] == 1
    assert counts["scorable_matched"] == 2
    assert counts["correct"] == 1 and counts["false_pass"] == 1
    assert counts["rejected"] == counts["unscorable_annotation"] == 1
    assert counts["extra"] == 1
    rows = {item.get("annotation_id"): item for item in scored["rows"] if item.get("annotation_id")}
    assert rows["rep2"]["marker_expected_outcome"] == "reached_reference"
    assert rows["rep2"]["marker_borderline"] is True
    assert rows["rep2"]["model_outcome"] == "reached_reference"
    assert rows["rep2"]["model_borderline"] is True
    assert rows["rep2"]["marker_combined_uncertainty_m"] > .02
    assert rows["rep3"]["marker_combined_uncertainty_m"] is None
    assert scored["summary"]["classification"]["denominator"] == 2


def test_extra_detections_do_not_rescue_missed_annotations(tmp_path):
    annotations = [row("base", 1.0, "reference"), row("rep2", 2.0), row("rep3", 3.0)]
    annotations = load_annotations(write_annotations(tmp_path / "score.csv", annotations))
    reps = [{"rep": 1, "bottom_s": 2.0, "depth_m": .3, "coverage": .95, "bottom_observed": True,
             "depth_se_m": .001, "outcome": "reached_reference"}]
    counts = score_condition(annotations, reps)["summary"]["counts"]
    assert counts["matched"] == 1 and counts["missed"] == 1
    assert counts["extra"] == 0


def test_bad_reference_makes_condition_unclear_instead_of_replacing_reference(tmp_path):
    annotations = [row("base", 1.0, "reference"), row("rep2", 2.0)]
    annotations = load_annotations(write_annotations(tmp_path / "score.csv", annotations))
    reps = [
        {"rep": 1, "bottom_s": 1.01, "depth_m": .3, "coverage": .5, "bottom_observed": False},
        {"rep": 2, "bottom_s": 2.01, "depth_m": .29, "coverage": .99, "bottom_observed": True},
    ]
    scored = score_condition(annotations, reps)
    rows = {item.get("annotation_id"): item for item in scored["rows"] if item.get("annotation_id")}
    assert rows["base"]["status"] == "reference_unscorable_quality"
    assert rows["rep2"]["model_outcome"] == "unclear"
    assert rows["rep2"]["status"] == "model_unclear"
    assert scored["summary"]["classification"]["denominator"] == 0


def test_rejected_reference_is_consumed_and_no_other_rep_becomes_reference(tmp_path):
    annotations = [row("base", 1.0, "reference", label="rejected"), row("rep2", 2.0)]
    annotations = load_annotations(write_annotations(tmp_path / "score.csv", annotations))
    reps = [
        {"rep": 1, "bottom_s": 1.01, "depth_m": .30, "coverage": .99, "bottom_observed": True},
        {"rep": 2, "bottom_s": 2.01, "depth_m": .29, "coverage": .99, "bottom_observed": True},
    ]
    scored = score_condition(annotations, reps)
    rows = {item.get("annotation_id"): item for item in scored["rows"] if item.get("annotation_id")}
    assert rows["base"]["status"] == "reference_rejected"
    assert rows["rep2"]["model_outcome"] == "unclear"
    assert scored["summary"]["reference_status"] == "reference_rejected"
    reference_detection = next(item for item in scored["detections"] if item["is_reference"])
    assert reference_detection["annotation_id"] == "base"


def test_annotation_label_conflict_with_clear_marker_is_flagged_and_preserved(tmp_path):
    annotations = [
        row("base", 1.0, "reference", marker_depth_m="0.30"),
        row("rep2", 2.0, label="match", marker_depth_m="0.20"),
    ]
    annotations = load_annotations(write_annotations(tmp_path / "score.csv", annotations))
    reps = [{"rep": 1, "bottom_s": 1.0, "depth_m": .30, "coverage": .99, "bottom_observed": True},
            {"rep": 2, "bottom_s": 2.0, "depth_m": .29, "coverage": .99, "bottom_observed": True}]
    scored = score_condition(annotations, reps)
    selected_row = next(item for item in scored["rows"] if item.get("annotation_id") == "rep2")
    assert selected_row["label"] == "match"
    assert selected_row["model_outcome"] == "reached_reference"
    assert selected_row["marker_expected_outcome"] == "shallower"
    assert selected_row["marker_label_conflict"] is True
    assert selected_row["marker_label_conflict_outside_borderline"] is True
    assert scored["summary"]["counts"]["marker_label_disagreements_outside_borderline"] == 1
    assert len(scored["rows"]) == 2


def test_time_match_maximizes_valid_pairs_before_minimizing_time_error(tmp_path):
    annotations = [row("base", 0.0, "reference"), row("rep2", 0.8)]
    annotations = load_annotations(write_annotations(tmp_path / "score.csv", annotations))
    reps = [
        {"rep": 1, "bottom_s": -0.5, "depth_m": .30, "coverage": .99, "bottom_observed": True,
         "depth_se_m": .001},
        {"rep": 2, "bottom_s": 0.3, "depth_m": .30, "coverage": .99, "bottom_observed": True,
         "depth_se_m": .001},
    ]
    scored = score_condition(annotations, reps)
    summary = scored["summary"]
    assert summary["counts"]["matched"] == 1
    assert summary["counts"]["missed"] == 0
    mapped = {item["annotation_id"]: item["bottom_s"] for item in scored["detections"] if item["annotation_id"]}
    assert mapped == {"base": -0.5, "rep2": 0.3}


def test_tolerance_boundary_is_inclusive_with_float_rounding(tmp_path):
    annotations = [row("base", 1.0, "reference"), row("rep2", 2.0)]
    annotations = load_annotations(write_annotations(tmp_path / "score.csv", annotations))
    reps = [
        {"rep": 1, "bottom_s": 1.0, "depth_m": 0.3, "coverage": .99, "bottom_observed": True},
        {"rep": 2, "bottom_s": 2.0, "depth_m": 0.27, "coverage": .99, "bottom_observed": True},
    ]
    scored = score_condition(annotations, reps, tolerance_m=.03)
    test_detection = next(item for item in scored["detections"] if item["annotation_id"] == "rep2")
    assert test_detection["outcome"] == "reached_reference"


def test_run_cli_hides_legacy_classification_when_timed_scoring_is_active(tmp_path, monkeypatch, capsys):
    from rvectr import pipeline
    from rvectr.commands import run

    report = {
        "reps": {"raw": {"reps": [{"rep": 2, "depth_m": .24, "descent_s": 1.1,
                                    "outcome": "reached_reference", "borderline": True}] }},
        "primary_trace": "raw", "frames": {"pelvis_reconstructed_fraction": .95},
        "jitter_standing": {}, "comparison_with_footage": {"counts": {"agree": 99}},
        "views": {"experiment": {"all views (cam1+cam2)": {
            "status": "scored", "counts": {"correct": 1, "missed": 1, "extra": 0,
                                              "rejected": 0, "unscorable_annotation": 0, "model_unclear": 0},
            "classification": {"denominator": 2, "accuracy": .5,
                               "all_eligible_tests_denominator": 4, "end_to_end_accuracy": .25}}}},
    }
    monkeypatch.setattr(pipeline, "run_session", lambda *args, **kwargs: (tmp_path / "run", report))
    run(["--config", str(tmp_path / "session.json")])
    output = capsys.readouterr().out
    assert "reached_reference" not in output
    assert "Footage labels retained, not scored" not in output
    assert "accuracy 50.0% (1/2)" in output
    assert "end-to-end 25.0% (1/4)" in output
    assert "missed 1" in output


def test_run_cli_marks_legacy_rep_labels_unscored(tmp_path, monkeypatch, capsys):
    from rvectr import pipeline
    from rvectr.commands import run

    report = {
        "reps": {"raw": {"reps": []}}, "primary_trace": "raw",
        "frames": {"pelvis_reconstructed_fraction": .95}, "jitter_standing": {},
        "comparison_with_footage": {"status": "not_scored_requires_independent_timestamps",
                                    "reason": "Use independent timed annotations.", "labels": [{"rep": 1}]},
    }
    monkeypatch.setattr(pipeline, "run_session", lambda *args, **kwargs: (tmp_path / "run", report))
    run(["--config", str(tmp_path / "session.json")])
    output = capsys.readouterr().out
    assert "Footage labels retained, not scored" in output
    assert "Against footage labels" not in output
    assert "agree" not in output



def test_interrupted_attempt_without_bottom_stays_in_the_ledger(tmp_path):
    interrupted = row("interrupted", 4, label="rejected", marker_depth_m="0.20")
    interrupted["bottom_s"] = ""
    notes = [row("base", 1, "reference", marker_depth_m="0.30"), interrupted]
    annotations = load_annotations(write_annotations(tmp_path / "attempts.csv", notes))
    scored = score_condition(annotations, [])
    assert scored["rows"][1]["status"] == "rejected"
    assert scored["rows"][1]["measured_descent_s"] is None
    assert scored["rows"][1].get("marker_label_conflict") is None
    assert scored["summary"]["counts"]["rejected"] == 1
    assert scored["summary"]["classification"]["denominator"] == 0
    assert scored["summary"]["classification"]["matched_annotation_coverage"] is None
    interrupted["label"] = "shallow"
    with pytest.raises(ValueError, match="scorable attempts need"):
        load_annotations(write_annotations(tmp_path / "incomplete.csv", notes))
