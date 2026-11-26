"""Independent, time-matched scoring for pilot annotations.

Annotations describe one take. A single marked reference repetition is kept in
the ledger but excluded from scored test-repetition denominators. Missing
uncertainties stay unknown; this module never replaces them with zero.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

ANNOTATION_COLUMNS = (
    "annotation_id", "start_s", "bottom_s", "end_s", "role", "label",
    "target_height_m", "marker_depth_m", "marker_uncertainty_m", "reader", "reader_uncertainty_s",
    "reader_uncertainty_m",
)
LABELS = {"match", "shallow", "rejected", "unscorable"}
MODEL_POSITIVE = "reached_reference"
MODEL_NEGATIVE = "shallower"


def _reached(depth, reference_depth, tolerance_m):
    delta = float(depth) - float(reference_depth)
    boundary = -float(tolerance_m)
    return delta >= boundary or bool(np.isclose(delta, boundary, rtol=0.0, atol=1e-9))


def _within(value, margin):
    distance, margin = abs(float(value)), float(margin)
    return distance <= margin or bool(np.isclose(distance, margin, rtol=0.0, atol=1e-9))


def _optional_float(value, field, row_number):
    if value is None or not str(value).strip():
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Annotation row {row_number}: {field} must be a number or blank") from error
    if not np.isfinite(number) or number < 0:
        raise ValueError(f"Annotation row {row_number}: {field} must be finite and non-negative")
    return number


def load_annotations(path):
    """Read the fixed annotation list; times are seconds on camera 1's video clock."""
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = [name for name in ANNOTATION_COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("Annotation CSV is missing columns: " + ", ".join(missing))
        rows = []
        seen = set()
        for row_number, raw in enumerate(reader, start=2):
            item = {key: value.strip() if isinstance(value, str) else value for key, value in raw.items()}
            aid = item["annotation_id"]
            if not aid or aid in seen:
                raise ValueError(f"Annotation row {row_number}: annotation_id must be nonempty and unique")
            seen.add(aid)
            role, label = (item["role"] or "").lower(), (item["label"] or "").lower()
            try:
                times = tuple(float(item[key]) if item[key] else None for key in ("start_s", "bottom_s", "end_s"))
            except ValueError as error:
                raise ValueError(f"Annotation row {row_number}: times must be numbers or blank") from error
            if label not in ("rejected", "unscorable") and None in times:
                raise ValueError(f"Annotation row {row_number}: scorable attempts need start, bottom and end times")
            known_times = [t for t in times if t is not None]
            if not np.isfinite(known_times).all() or sorted(known_times) != known_times:
                raise ValueError(f"Annotation row {row_number}: require finite start_s <= bottom_s <= end_s")
            start, bottom, end = times
            if role not in ("reference", "test"):
                raise ValueError(f"Annotation row {row_number}: role must be reference or test")
            if label not in LABELS:
                raise ValueError(f"Annotation row {row_number}: label must be one of {sorted(LABELS)}")
            if role == "reference" and label == "shallow":
                raise ValueError(f"Annotation row {row_number}: reference label must be match, rejected or unscorable")
            rows.append({
                "annotation_id": aid, "start_s": start, "bottom_s": bottom, "end_s": end,
                "role": role, "label": label,
                "target_height_m": _optional_float(item["target_height_m"], "target_height_m", row_number),
                "marker_depth_m": _optional_float(item["marker_depth_m"], "marker_depth_m", row_number),
                "marker_uncertainty_m": _optional_float(item["marker_uncertainty_m"], "marker_uncertainty_m", row_number),
                "reader": item["reader"] or None,
                "reader_uncertainty_s": _optional_float(item["reader_uncertainty_s"], "reader_uncertainty_s", row_number),
                "reader_uncertainty_m": _optional_float(item["reader_uncertainty_m"], "reader_uncertainty_m", row_number),
            })
    refs = [row for row in rows if row["role"] == "reference"]
    if len(refs) != 1:
        raise ValueError(f"Annotation list needs exactly one reference repetition; found {len(refs)}")
    return rows


class AnnotationConfigError(ValueError):
    """The annotation file and the matching settings cannot be scored together."""


def check_match_window(annotations, match_window_s):
    """Refuse a match window that could pair one detection with two annotations.

    One-to-one matching keeps as many pairs as possible before it looks at timing
    error. If two annotated bottoms are closer than twice the window, a missed
    squat could be paired with its neighbour's detection to free a second pair.
    Requiring the window to be under half the smallest gap rules that out.
    """
    timed = sorted((row["bottom_s"], row["annotation_id"]) for row in annotations
                   if row["bottom_s"] is not None)
    if len(timed) < 2:
        return
    gap, first, second = min((b[0] - a[0], a[1], b[1]) for a, b in zip(timed, timed[1:]))
    if match_window_s >= gap / 2:
        raise AnnotationConfigError(
            f"experiment.match_window_s ({match_window_s:g} s) must be less than half the smallest gap between "
            f"annotated bottom times ({gap:g} s, between '{first}' and '{second}'); use a window below "
            f"{gap / 2:g} s or correct the annotation times")


def _finite_stats(values):
    values = np.asarray(values, float)
    values = values[np.isfinite(values)]
    return {"n": int(len(values)), "mean": float(values.mean()) if len(values) else None,
            "sd": float(values.std(ddof=1)) if len(values) > 1 else None,
            "mae": float(np.abs(values).mean()) if len(values) else None,
            "rmse": float(np.sqrt(np.mean(values ** 2))) if len(values) else None}


def score_condition(annotations, reps, match_window_s=0.5, tolerance_m=0.03, borderline_m=0.01,
                    min_coverage=0.85):
    """One-to-one match a condition's detections to fixed annotations by bottom time.

    Return one row per attempted squat plus unmatched detections. Maximize
    the number of timed matches, then minimize total absolute timing error.
    """
    if match_window_s <= 0 or tolerance_m < 0 or borderline_m < 0 or not 0 <= min_coverage <= 1:
        raise ValueError("match window must be positive and tolerances non-negative")
    if not annotations:
        raise ValueError("At least one independent annotation is required")
    check_match_window(annotations, match_window_s)
    reference_index = next(i for i, row in enumerate(annotations) if row["role"] == "reference")
    reference = annotations[reference_index]
    tests = [row for row in annotations if row["role"] == "test"]
    detections = sorted(reps or [], key=lambda rep: float(rep["bottom_s"]))
    # Sorted one-dimensional dynamic programming gives maximum match count
    # first, then minimum total timing error. Greedily consuming the nearest
    # pair can strand a neighbouring annotation despite a complete assignment.
    timed = (i for i, row in enumerate(annotations) if row["bottom_s"] is not None)
    annotation_order = sorted(timed, key=lambda i: annotations[i]["bottom_s"])
    n, m = len(annotation_order), len(detections)
    dp = [[(0, 0.0, ()) for _ in range(m + 1)] for _ in range(n + 1)]

    def better(left, right):
        return min((left, right), key=lambda item: (-item[0], item[1], item[2]))

    for i in range(1, n + 1):
        ai = annotation_order[i - 1]
        for j in range(1, m + 1):
            best = better(dp[i - 1][j], dp[i][j - 1])
            ri = j - 1
            delta = abs(float(detections[ri]["bottom_s"]) - annotations[ai]["bottom_s"])
            if delta <= match_window_s:
                prev = dp[i - 1][j - 1]
                candidate = (prev[0] + 1, prev[1] + delta, prev[2] + ((ai, ri),))
                best = better(best, candidate)
            dp[i][j] = best
    matches = {ai: (ri, detections[ri]) for ai, ri in dp[n][m][2]}
    used_reps = {ri for ri, _ in matches.values()}

    # Anchor every condition's predicted classes to its own detection of the
    # independently annotated reference repetition.
    matched_reference = matches.get(reference_index)
    reference_rep = matched_reference[1] if matched_reference else None
    reference_quality = bool(reference["label"] == "match" and reference_rep
                             and reference_rep.get("coverage", 0) >= min_coverage
                             and reference_rep.get("bottom_observed", False)
                             and reference_rep.get("depth_m") is not None)
    reference_depth = reference_rep.get("depth_m") if reference_quality else None
    reference_se = reference_rep.get("depth_se_m") if reference_quality else None
    classified = []
    for rep in detections:
        updated = dict(rep)
        quality = bool(rep.get("coverage", 0) >= min_coverage and rep.get("bottom_observed", False)
                       and rep.get("depth_m") is not None)
        updated["quality_valid"] = quality
        if not quality:
            updated["quality_status"] = ("low_coverage" if rep.get("coverage", 0) < min_coverage
                                          else "bottom_not_observed")
            updated["outcome"] = "unclear"
            updated["borderline"] = None
        elif reference_depth is None:
            updated["quality_status"] = "reference_unscorable"
            updated["outcome"] = "unclear"
            updated["borderline"] = None
        else:
            updated["quality_status"] = "observed"
            difference = float(rep["depth_m"]) - float(reference_depth)
            line = -tolerance_m
            updated["difference_from_reference_m"] = difference
            updated["outcome"] = MODEL_POSITIVE if _reached(rep["depth_m"], reference_depth, tolerance_m) else MODEL_NEGATIVE
            own_se = rep.get("depth_se_m")
            uncertainty = (float(np.hypot(own_se, reference_se))
                           if own_se is not None and reference_se is not None else None)
            updated["difference_se_m"] = uncertainty
            updated["borderline"] = (_within(difference - line, max(borderline_m, 2 * uncertainty))
                                     if uncertainty is not None and np.isfinite(uncertainty)
                                     else _within(difference - line, borderline_m))
        classified.append(updated)
    detections = classified
    matches = {ai: (ri, detections[ri]) for ai, (ri, _) in matches.items()}

    rows, errors = [], []
    reference_status = ("reference_rejected" if reference["label"] == "rejected" else
                        "reference_unscorable_annotation" if reference["label"] == "unscorable" else
                        "reference_missed" if reference_rep is None else
                        "reference_unscorable_quality" if not reference_quality else "reference_observed")
    marker_reference_usable = (reference["label"] == "match" and reference["marker_depth_m"] is not None)
    eligible_denominator = sum(a["role"] == "test" and a["label"] in ("match", "shallow") for a in annotations)
    counts = {"annotated_test_reps": len(tests), "all_annotated_test_attempts": len(tests),
              "eligible_test_attempts": eligible_denominator, "matched_any": 0,
              "matched": 0, "missed": 0, "extra": 0,
              "rejected": 0, "unscorable_annotation": 0, "scorable_matched": 0,
              "model_unclear": 0, "correct": 0, "false_pass": 0, "false_flag": 0,
              "reference_excluded": 1, "marker_depth_available": 0,
              "marker_label_agreement_n": 0, "marker_label_disagreements": 0,
              "marker_label_disagreements_outside_borderline": 0,
              "marker_borderline_n": 0}
    mapped_detections = []
    for ai, annotation in enumerate(annotations):
        pair = matches.get(ai)
        rep = pair[1] if pair else None
        eligible = annotation["role"] == "test" and annotation["label"] in ("match", "shallow")
        row = {"annotation_id": annotation["annotation_id"], "role": annotation["role"],
               "label": annotation["label"], "start_s": annotation["start_s"], "bottom_s": annotation["bottom_s"],
               "end_s": annotation["end_s"],
               "reader": annotation["reader"], "reader_uncertainty_s": annotation["reader_uncertainty_s"],
               "reader_uncertainty_m": annotation["reader_uncertainty_m"],
               "target_height_m": annotation["target_height_m"],
               "measured_descent_s": (annotation["bottom_s"] - annotation["start_s"]
                                      if None not in (annotation["bottom_s"], annotation["start_s"]) else None),
               "classification_comparison_source": None,
               "marker_depth_m": annotation["marker_depth_m"],
               "marker_uncertainty_m": annotation["marker_uncertainty_m"],
               "status": ("reference_excluded" if annotation["role"] == "reference" else annotation["label"]),
               "matched": rep is not None, "detection_rep": rep.get("rep") if rep else None,
               "detection_bottom_s": rep.get("bottom_s") if rep else None,
               "depth_m": rep.get("depth_m") if rep else None,
               "depth_se_m": rep.get("depth_se_m") if rep else None,
               "reference_depth_se_m": reference_se,
               "difference_se_m": rep.get("difference_se_m") if rep else None,
               "reference_status": reference_status,
               "model_outcome": rep.get("outcome") if rep else None,
               "model_borderline": rep.get("borderline") if rep else None,
               "quality_status": rep.get("quality_status") if rep else None,
               "quality_valid": rep.get("quality_valid") if rep else None,
               "depth_error_m": None, "marker_expected_outcome": None,
               "marker_borderline": None, "marker_combined_uncertainty_m": None}
        if annotation["role"] == "reference" and not reference_quality:
            row["status"] = reference_status
        elif eligible and rep is None:
            row["status"] = "missed"
        elif eligible and (not rep.get("quality_valid") or not reference_quality):
            row["status"] = "model_unclear"
        if annotation["role"] == "test":
            if rep is not None:
                counts["matched_any"] += 1
            if annotation["label"] == "rejected":
                counts["rejected"] += 1
            elif annotation["label"] == "unscorable":
                counts["unscorable_annotation"] += 1
            elif rep is None:
                counts["missed"] += 1
            elif eligible:
                counts["matched"] += 1
                if rep.get("outcome") in (MODEL_POSITIVE, MODEL_NEGATIVE):
                    counts["scorable_matched"] += 1
                    expected_positive = annotation["label"] == "match"
                    row["classification_comparison_source"] = "independent_reader_label"
                    if marker_reference_usable and annotation["marker_depth_m"] is not None:
                        row["classification_comparison_source"] = "independent_marker_displacement"
                        expected_positive = _reached(annotation["marker_depth_m"], reference["marker_depth_m"], tolerance_m)
                    got_positive = rep["outcome"] == MODEL_POSITIVE
                    if expected_positive == got_positive:
                        counts["correct"] += 1
                    elif got_positive:
                        counts["false_pass"] += 1
                    else:
                        counts["false_flag"] += 1
                else:
                    counts["model_unclear"] += 1
        if rep is not None and annotation["role"] == "test":
            if (eligible and rep.get("quality_valid") and annotation["marker_depth_m"] is not None
                    and rep.get("depth_m") is not None):
                error = float(rep["depth_m"]) - annotation["marker_depth_m"]
                row["depth_error_m"] = error
                errors.append(error)
                counts["marker_depth_available"] += 1
        if (annotation["role"] == "test" and marker_reference_usable
                and annotation["marker_depth_m"] is not None):
            depth_delta = annotation["marker_depth_m"] - reference["marker_depth_m"]
            boundary = -tolerance_m
            row["marker_expected_outcome"] = (MODEL_POSITIVE if
                                               _reached(annotation["marker_depth_m"], reference["marker_depth_m"], tolerance_m)
                                               else MODEL_NEGATIVE)
            us = [annotation["marker_uncertainty_m"], reference["marker_uncertainty_m"]]
            reader_us = [annotation["reader_uncertainty_m"], reference["reader_uncertainty_m"]]
            combined_uncertainty = None
            if all(value is not None for value in us + reader_us):
                combined_uncertainty = float(np.linalg.norm(us + reader_us))
                row["marker_combined_uncertainty_m"] = combined_uncertainty
            marker_margin = max(borderline_m, 2 * combined_uncertainty) if combined_uncertainty is not None else borderline_m
            row["marker_borderline"] = _within(depth_delta - boundary, marker_margin)
            if eligible:
                reader_outcome = MODEL_POSITIVE if annotation["label"] == "match" else MODEL_NEGATIVE
                row["marker_label_agrees"] = row["marker_expected_outcome"] == reader_outcome
                row["marker_label_conflict"] = not row["marker_label_agrees"]
                row["marker_label_conflict_outside_borderline"] = row["marker_label_conflict"] and not row["marker_borderline"]
                counts["marker_label_agreement_n"] += 1
                if not row["marker_label_agrees"]:
                    counts["marker_label_disagreements"] += 1
                if row["marker_label_conflict_outside_borderline"]:
                    counts["marker_label_disagreements_outside_borderline"] += 1
                counts["marker_borderline_n"] += int(row["marker_borderline"])
        rows.append(row)
        if rep is not None:
            mapped_detections.append({**rep, "annotation_id": annotation["annotation_id"],
                                      "is_reference": annotation["role"] == "reference",
                                      "reference_status": reference_status})

    extras = [rep for i, rep in enumerate(detections) if i not in used_reps]
    counts["extra"] = len(extras)
    # Pieces of one squat cut by a timestamp hole are still counted as extra detections,
    # but this count shows how many of them are such pieces.
    counts["extra_split_by_gap"] = sum(bool(rep.get("split_by_gap")) for rep in extras)
    for index, rep in enumerate(extras, start=1):
        rows.append({"annotation_id": None, "role": None, "label": None, "bottom_s": None,
                     "status": "extra_detection", "matched": False, "detection_rep": rep.get("rep"),
                     "detection_bottom_s": rep.get("bottom_s"), "depth_m": rep.get("depth_m"),
                     "model_outcome": rep.get("outcome"), "extra_index": index,
                     "split_by_gap": bool(rep.get("split_by_gap"))})
        mapped_detections.append({**rep, "annotation_id": None, "is_reference": False,
                                  "reference_status": reference_status})
    denominator = counts["scorable_matched"]
    summary = {"counts": counts,
               "classification": {"denominator": denominator,
                                  "accuracy": counts["correct"] / denominator if denominator else None,
                                  "conditional_accuracy": counts["correct"] / denominator if denominator else None,
                                  "all_eligible_tests_denominator": eligible_denominator,
                                  "end_to_end_accuracy": counts["correct"] / eligible_denominator if eligible_denominator else None,
                                  "false_pass_rate": counts["false_pass"] / denominator if denominator else None,
                                  "false_flag_rate": counts["false_flag"] / denominator if denominator else None,
                                  "matched_annotation_coverage": counts["matched"] / eligible_denominator if eligible_denominator else None,
                                  "all_attempts_denominator": len(tests),
                                  "all_attempt_coverage": counts["matched_any"] / len(tests) if tests else None},
               "continuous_depth_error_m": _finite_stats(errors),
               "reference_annotation_id": reference["annotation_id"], "reference_status": reference_status,
               "matching": {"method": "maximum_cardinality_then_minimum_total_bottom_time_error",
                            "window_s": match_window_s},
               "decision_rule": {"tolerance_m": tolerance_m, "borderline_m": borderline_m,
                                 "min_coverage": min_coverage,
                                 "positive": "depth >= matched reference depth - tolerance"},
               "uncertainty_note": "Blank marker or reader uncertainties remain unknown; no zero uncertainty is assumed."}
    return {"summary": summary, "rows": rows, "detections": mapped_detections}


# Counts and rates that come from the model's detections. They are unknown
# (None) for a condition that failed, not zero.
_DETECTION_COUNTS = ("matched_any", "matched", "missed", "extra", "scorable_matched", "model_unclear",
                     "correct", "false_pass", "false_flag", "marker_depth_available", "extra_split_by_gap")
_DETECTION_RATES = ("denominator", "accuracy", "conditional_accuracy", "false_pass_rate", "false_flag_rate",
                    "end_to_end_accuracy", "matched_annotation_coverage", "all_attempt_coverage")


def score_failed_condition(annotations, reason, match_window_s=0.5, tolerance_m=0.03, borderline_m=0.01,
                           min_coverage=0.85):
    """Record a condition that could not be measured at all (for example a plane or triangulation error).

    Every attempt keeps its ID but is marked condition_failed instead of missed, and the
    detection-based counts and rates are None. The reason is stored on the summary and each row.
    """
    scored = score_condition(annotations, [], match_window_s, tolerance_m, borderline_m, min_coverage)
    summary = scored["summary"]
    for key in _DETECTION_COUNTS:
        summary["counts"][key] = None
    for key in _DETECTION_RATES:
        summary["classification"][key] = None
    summary["reference_status"] = "condition_failed"
    summary["failure_reason"] = reason
    for row in scored["rows"]:
        row["reference_status"] = "condition_failed"
        row["condition_failure"] = reason
        # Rejected and unscorable attempts never reach the model, so they keep their annotation status.
        if row["status"] not in ("rejected", "unscorable"):
            row["status"] = "condition_failed"
    return scored
