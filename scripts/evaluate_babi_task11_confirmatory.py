#!/usr/bin/env python3
"""Run the once-only Task 11 confirmatory challenge after validation selection."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

from rgm.experiments.babi_expansion_adapters import task11_confirmatory_input_to_story
from rgm.experiments.babi_expansion_confirmatory import (
    evaluate_task11_confirmatory,
    generate_task11_confirmatory,
    verify_task11_confirmatory,
)
from rgm.experiments.babi_task11_prediction import predict_task11_from_learned_state
from rgm.leptograph.m4.hierarchical import CanonicalRelationStore
from rgm.leptograph.m4.learning import LearningRuntime


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path):
    return sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _load_candidate_model(root: Path, run_key: str, architecture: str):
    artifact_name = "babi-task11-campaign-" + run_key.removeprefix("task11-")
    snapshot_path = root / artifact_name / "model-snapshot.json"
    snapshot = _load(snapshot_path)
    if snapshot.get("run_key") != run_key or snapshot.get("architecture") != architecture:
        raise ValueError("selected candidate model snapshot identity mismatch")
    if snapshot.get("evaluator_labels_included") is not False:
        raise ValueError("selected candidate model snapshot contains evaluator labels")
    learning = LearningRuntime()
    learning.context_transitions.restore(snapshot["context_transitions"])
    adapter = SimpleNamespace(architecture=architecture, learning=learning)
    if architecture == "HLB":
        store = CanonicalRelationStore(capacity=262144)
        store.restore(snapshot["hlb_model_relations"])
        adapter.store = store
    return adapter, snapshot_path, snapshot


def evaluate(candidate_selection_path: Path, campaign_run_root: Path,
             output_root: Path) -> dict:
    selection = _load(candidate_selection_path)
    selected = selection.get("selected", {})
    chosen = {architecture: run_key for architecture, run_key in selected.items() if run_key}
    output_root.mkdir(parents=True, exist_ok=True)
    if not chosen:
        report = {
            "schema": "HLG-BABI-TASK11-CONFIRMATORY-EXECUTION-v1",
            "status": "SKIPPED_NO_VALIDATION_CANDIDATE",
            "candidate_selection": selected,
            "challenge_generated": False,
            "reason": "No full-learning seed met the frozen baseline and integrity thresholds.",
        }
        (output_root / "confirmatory-execution.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        return report

    challenge_root = output_root / "challenge"
    generator_manifest = generate_task11_confirmatory(challenge_root)
    verification = verify_task11_confirmatory(challenge_root)
    input_rows = _read_jsonl(challenge_root / "task11-confirmatory-inputs.jsonl")
    stories = [task11_confirmatory_input_to_story(row) for row in input_rows]

    # Freeze all selected-candidate predictions before opening the evaluator labels.
    decisions_by_architecture = {}
    candidate_provenance = {}
    for architecture, run_key in sorted(chosen.items()):
        adapter, snapshot_path, snapshot = _load_candidate_model(
            campaign_run_root, run_key, architecture,
        )
        decisions = {}
        prediction_rows = []
        for story in stories:
            if len(story.queries) != 1:
                raise ValueError("confirmatory story must contain exactly one query")
            query = story.queries[0]
            decision = predict_task11_from_learned_state(adapter, story, query)
            decisions[query.query_id] = decision
            prediction_rows.append({
                "query_id": query.query_id,
                "story_id": story.story_id,
                "answer": decision.prediction.answer,
                "abstained": decision.prediction.abstained,
                "reason": decision.prediction.reason,
                "witness_event_ids": list(decision.prediction.witness_event_ids),
                "model_fingerprint": decision.model_fingerprint,
                "grounding_event_ids": list(decision.grounding_event_ids),
            })
        decisions_by_architecture[architecture] = decisions
        prediction_path = output_root / f"{architecture.lower()}-confirmatory-predictions.jsonl"
        prediction_path.write_text(
            "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n"
                    for row in prediction_rows),
            encoding="utf-8",
        )
        candidate_provenance[architecture] = {
            "run_key": run_key,
            "model_snapshot_sha256": _sha(snapshot_path),
            "fit_model_fingerprint": snapshot["fit_model_fingerprint"],
        }

    # Evaluator labels are opened only after every selected architecture's
    # prediction journal has been frozen to disk.
    labels = _read_jsonl(challenge_root / "task11-confirmatory-evaluator-labels.jsonl")
    scorecards = {}
    for architecture, decisions in decisions_by_architecture.items():
        scorecards[architecture] = evaluate_task11_confirmatory(
            input_rows, labels, decisions,
        )
    report = {
        "schema": "HLG-BABI-TASK11-CONFIRMATORY-EXECUTION-v1",
        "status": "PASS",
        "task_id": 11,
        "candidate_selection": selected,
        "candidate_provenance": candidate_provenance,
        "generator_manifest_sha256": generator_manifest["manifest_sha256"],
        "generator_verification": verification,
        "scores": scorecards,
        "candidate_reselection_from_confirmatory": False,
        "threshold_tuning_from_confirmatory": False,
        "claim_boundary": (
            "Novel-name transfer and ambiguous-mention abstention challenge only; "
            "not official bAbI test data and not independent coreference-edge gold."
        ),
    }
    (output_root / "confirmatory-execution.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-selection", type=Path, required=True)
    parser.add_argument("--campaign-run-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.candidate_selection, args.campaign_run_root, args.output_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
