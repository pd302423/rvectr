"""Export a compact, named simulation summary for the website.

Usage: python tools/export_simulation_summary.py --summary outputs/sim/RUN/summary.json
Every exported value is copied from the named run. The simulation outputs remain
separate from this small website data file.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def compact(summary: dict) -> dict:
    reference = [
        {key: row.get(key) for key in ("mode", "white_noise_model_px", "white_noise_mm_at_person", "pace",
                                        "mean_depth_error_mm", "minimum_detectable_difference_mm",
                                        "tested_grid_bracket_mm", "unclear_rate")}
        for row in summary["reference_table"]
    ]
    extended = [
        {key: row.get(key) for key in ("scenario", "mode", "pace", "minimum_detectable_difference_mm",
                                        "tested_grid_bracket_mm", "unclear_rate")}
        for row in summary["extended_sensitivity"]
    ]
    fixed = [
        {"mode": row["mode"], "white_noise_model_px": row["white_noise_model_px"], "pace": row["pace"],
         "tolerance_mm": row["tolerance_mm"], "by_true_difference_cm": row["by_true_difference_cm"]}
        for row in summary["detection_curves_default_rule"]
    ]
    return {
        "title": summary["title"],
        "created_utc": summary["created_utc"],
        "code_version": summary["code_version"],
        "source_dirty": summary["source_dirty"],
        "source_sha256": summary["source_sha256"],
        "supporting_source_sha256": {k: summary["source_sha256"][k] for k in ("backend/rvectr/squat.py", "backend/rvectr/pipeline.py", "uv.lock", "pyproject.toml")},
        "dependency_lock_sha256": summary["source_sha256"]["uv.lock"],
        "runtime": summary["runtime"],
        "seed": summary["seed"],
        "sessions_per_condition": summary["sessions_per_condition"],
        "settings": summary["settings"],
        "assumptions": summary["assumptions"],
        "reference_table": reference,
        "extended_sensitivity": extended,
        "detection_curves_default_rule": fixed,
        "estimator_comparison": summary["estimator_comparison"],
        "ranking": summary["ranking"],
        "pause_at_bottom": summary["pause_at_bottom"],
        "targeted_3mm_heldout": summary["targeted_3mm_heldout"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, help="full simulation summary.json")
    parser.add_argument("--output", default=str(ROOT / "src/lib/results/simulation-summary.json"))
    args = parser.parse_args()
    source = Path(args.summary)
    destination = Path(args.output)
    document = compact(json.loads(source.read_text(encoding="utf-8")))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {destination} from {source} ({destination.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
