#!/usr/bin/env python3
"""Verify the one-time confirmatory outputs against the validation selection lock."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--selection-file", type=Path, required=True)
    args = parser.parse_args()

    selection = json.loads(args.selection_file.read_text(encoding="utf-8"))
    selected = selection["selected_candidates"]
    files = sorted(
        args.input_dir / f"task{task}-{architecture}.json"
        for task in (3, 5) for architecture in ("HLA", "HLB")
    )
    require(all(path.is_file() for path in files),
            "one or more of the four confirmatory result JSON files is missing")

    results = {}
    for path in files:
        bundle = json.loads(path.read_text(encoding="utf-8"))
        task = int(bundle["task_id"])
        architecture = bundle["architecture"]
        require(bundle.get("protocol_id") == "HLG-BABI-T3-T5-LEARNING-v1.3.0",
                f"{path}: protocol id mismatch")
        require(bundle.get("stage") == "confirmatory", f"{path}: wrong campaign stage")
        require(bundle.get("complete") is True and bundle.get("status") == "completed",
                f"{path}: confirmatory run incomplete")
        require(bundle.get("expected_run_count") == 1 and bundle.get("completed_run_count") == 1,
                f"{path}: confirmatory run must contain exactly one selected candidate")
        require(len(bundle.get("results", [])) == 1, f"{path}: expected one result")
        result = bundle["results"][0]
        key = (task, architecture)
        require(key not in results, f"duplicate confirmatory output {key}")
        expected = selected[str(task)]
        expected_fp = expected["candidate_fingerprints"][architecture]
        require(result["variant"] == "full_learning" and result["seed"] == expected["seed"],
                f"{key}: confirmatory candidate identity differs from selection lock")
        require(result.get("confirmatory_evaluated") is True
                and result["phases"]["generated_confirmatory"] is not None,
                f"{key}: selected candidate was not confirmatorily evaluated")
        require(result["candidate_fingerprint"] == expected_fp,
                f"{key}: reconstructed candidate fingerprint differs from selection lock")
        require(result["candidate_fingerprint_after_validation"] == expected_fp
                and result["candidate_fingerprint_after_confirmatory"] == expected_fp,
                f"{key}: score-only validation/confirmatory mutated candidate parameters")
        phase = result["phases"]["generated_confirmatory"]
        require(phase["learn_enabled"] is False, f"{key}: confirmatory phase was not score-only")
        require(phase["prediction_target_coverage_complete"] is True,
                f"{key}: confirmatory prediction target coverage incomplete")
        require(all(phase["prediction_lifecycle"][name]["still_issued"] == 0
                    for name in phase["prediction_lifecycle"]),
                f"{key}: open forecasts remain after confirmatory evaluation")
        require(phase["query_accuracy"] == 1.0 and phase["support_witness_recall"] == 1.0,
                f"{key}: structured task/evidence acceptance failed")
        require(phase["provenance_failures"] == 0
                and phase["cross_story_witness_count"] == 0
                and phase["evidence_capacity_misses"] == 0,
                f"{key}: evidence integrity or capacity gate failed")
        require(result["runtime"]["one_native_step_per_tick"] is True,
                f"{key}: native step invariant failed")
        results[key] = result

    require(set(results) == {(task, arch) for task in (3, 5) for arch in ("HLA", "HLB")},
            "one or more task/architecture confirmatory outputs are missing")
    for task in (3, 5):
        hla = results[(task, "HLA")]["phases"]["generated_confirmatory"]
        hlb = results[(task, "HLB")]["phases"]["generated_confirmatory"]
        for field in (
            "queries", "eligible_queries", "correct", "abstained",
            "support_total", "support_available", "provenance_failures",
            "false_witnesses", "query_accuracy", "support_witness_recall",
            "prediction_metrics", "prediction_lifecycle",
            "expected_scoreable_prediction_targets",
            "prediction_target_coverage_complete", "task_outcome_prediction",
        ):
            require(hla.get(field) == hlb.get(field),
                    f"Task {task}: confirmatory HLA/HLB parity mismatch in {field}")

    print(json.dumps({
        "status": "accepted",
        "confirmatory_evaluations": len(results),
        "selected_candidates": {
            task: {"seed": row["seed"], "variant": row["variant"]}
            for task, row in selected.items()
        },
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
