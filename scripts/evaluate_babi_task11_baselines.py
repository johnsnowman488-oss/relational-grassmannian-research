#!/usr/bin/env python3
"""Evaluate independent non-oracle Task 11 baselines on the frozen validation split."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from rgm.experiments.babi_expansion_adapters import parse_expansion_source
from rgm.experiments.babi_expansion_baselines import evaluate_baselines
from rgm.experiments.babi_expansion_preflight import _fit_validation_split


def evaluate_task11_validation(source_path: Path, output_path: Path) -> dict:
    raw = source_path.read_bytes()
    stories, labels = parse_expansion_source(
        source_path, task_id=11, split="train", include_labels=True,
    )
    fit, validation = _fit_validation_split(stories, 11)
    validation_ids = {story.story_id for story in validation}
    fit_ids = {story.story_id for story in fit}
    if validation_ids & fit_ids or validation_ids | fit_ids != {s.story_id for s in stories}:
        raise AssertionError("Task 11 fit/validation whole-story partition is not disjoint and complete")
    query_ids = {
        query.query_id for story in validation for query in story.queries
    }
    validation_labels = [label for label in labels if label.query_id in query_ids]
    if len(query_ids) != 1000 or len(validation_labels) != len(query_ids):
        raise AssertionError(
            f"expected 1,000 validation queries and labels; got {len(query_ids)} / {len(validation_labels)}"
        )
    if any(label.query_id not in query_ids for label in validation_labels):
        raise AssertionError("baseline evaluator received a label outside Task 11 validation")

    # evaluate_baselines passes only story/query objects to predictors. Labels
    # are consumed exclusively in its scoring branch after each prediction.
    scored = evaluate_baselines(validation, validation_labels, evaluate_labels=True)
    task = scored["task_results"].get("11", {})
    expected = {"nearest-compatible-antecedent", "recency-only"}
    if set(task) != expected:
        raise AssertionError(f"unexpected Task 11 baseline set: {sorted(task)}")
    report = {
        "schema": "HLG-BABI-TASK11-NONORACLE-BASELINE-VALIDATION-v1",
        "status": "PASS",
        "task_id": 11,
        "source_member": source_path.name,
        "source_sha256": sha256(raw).hexdigest(),
        "fit_story_count": len(fit),
        "validation_story_count": len(validation),
        "validation_query_count": len(query_ids),
        "validation_partition_sha256": sha256(
            json.dumps(sorted(validation_ids), separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "baseline_predictors": sorted(expected),
        "evaluation": task,
        "official_test_queries_loaded": 0,
        "confirmatory_labels_loaded": 0,
        "learning_updates": 0,
        "coreference_edge_metrics": {
            "status": "NOT_INDEPENDENTLY_EVALUABLE",
            "reason": "Official Task 11 answer/support labels do not provide independent antecedent-edge gold annotations.",
        },
        "claim_boundary": (
            "Independent symbolic non-oracle baseline validation only; no HLA/HLB learning "
            "effectiveness or coreference-edge accuracy claim."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["report_sha256"] = sha256(output_path.read_bytes()).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate_task11_validation(args.source, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
