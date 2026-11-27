#!/usr/bin/env python3
"""Validate matched HLA/HLB validation artifacts and select one full-learning seed per task."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

VARIANTS = (
    "full_learning", "no_temporal", "no_relational",
    "no_abstraction", "no_task", "no_learning",
)
ARCHITECTURES = ("HLA", "HLB")
TASKS = (3, 5)
TARGETS = (
    "next_l0_features", "next_relation_pattern",
    "next_event_role_pattern", "next_context",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _phase_parity(left: dict, right: dict, label: str) -> None:
    fields = (
        "queries", "eligible_queries", "quarantined_queries", "correct",
        "abstained", "support_total", "support_available",
        "provenance_checked", "provenance_failures", "false_witnesses",
        "evidence_capacity_misses", "query_accuracy", "abstention_rate",
        "support_witness_recall", "prediction_metrics",
        "prediction_lifecycle", "expected_scoreable_prediction_targets",
        "prediction_target_coverage_complete", "task_outcome_prediction",
    )
    for field in fields:
        _require(left.get(field) == right.get(field),
                 f"HLA/HLB parity mismatch at {label}.{field}: "
                 f"{left.get(field)!r} != {right.get(field)!r}")


def _assert_manipulations(results: dict[tuple[int, str, int, str], dict]) -> None:
    for task in TASKS:
        for architecture in ARCHITECTURES:
            seeds = sorted(k[2] for k in results if k[0] == task and k[1] == architecture)
            for seed in seeds:
                def row(variant: str) -> dict:
                    return results[(task, architecture, seed, variant)]

                full = row("full_learning")
                no_temporal = row("no_temporal")
                no_relational = row("no_relational")
                no_abstraction = row("no_abstraction")
                no_task = row("no_task")
                no_learning = row("no_learning")

                changed = full["online_learner_state_changed"]
                _require(changed.get("task_outcomes") is True,
                         f"task {task} {architecture} seed {seed}: full_learning did not update task calibration")
                _require(no_temporal["online_learner_state_changed"].get("level0") is False
                         and no_temporal["online_learner_state_changed"].get("temporal_credit") is False,
                         f"task {task} {architecture} seed {seed}: no_temporal leaked into temporal learners")
                _require(no_relational["online_learner_state_changed"].get("relations") is False,
                         f"task {task} {architecture} seed {seed}: no_relational changed relation learner")
                _require(no_abstraction["online_learner_state_changed"].get("event_roles") is False
                         and no_abstraction["online_learner_state_changed"].get("context_transitions") is False,
                         f"task {task} {architecture} seed {seed}: no_abstraction leaked into abstraction learners")
                _require(no_task["online_learner_state_changed"].get("task_outcomes") is False,
                         f"task {task} {architecture} seed {seed}: no_task changed task calibration")
                _require(all(value is False for value in no_learning["online_learner_state_changed"].values()),
                         f"task {task} {architecture} seed {seed}: no_learning changed learner state")

                task_signal = no_task["phases"]["online_adaptation"]["task_outcome_prediction"]
                _require(task_signal["count"] > 0 and task_signal["mean_brier_score"] is not None,
                         f"task {task} {architecture} seed {seed}: no_task did not measure task Brier error")
                _require(task_signal["updates_enabled"] is False,
                         f"task {task} {architecture} seed {seed}: no_task reports updates enabled")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    args = parser.parse_args()

    expected_seeds = list(args.seeds)
    _require(len(expected_seeds) == len(set(expected_seeds)), "seed list contains duplicates")
    files = sorted(
        args.input_dir / f"task{task}-{architecture}.json"
        for task in TASKS for architecture in ARCHITECTURES
    )
    _require(all(path.is_file() for path in files),
             "one or more of the four worker result JSON files is missing")

    worker_data: dict[tuple[int, str], dict] = {}
    for path in files:
        bundle = _load(path)
        task, architecture = int(bundle["task_id"]), bundle["architecture"]
        _require(task in TASKS and architecture in ARCHITECTURES,
                 f"unexpected worker identity in {path}")
        _require((task, architecture) not in worker_data,
                 f"duplicate worker artifact for task {task} {architecture}")
        _require(bundle.get("protocol_id") == "HLG-BABI-T3-T5-LEARNING-v1.3.0",
                 f"{path}: wrong protocol id")
        _require(bundle.get("stage") == "validation_selection",
                 f"{path}: confirmatory metrics must not appear in validation stage")
        _require(bundle.get("complete") is True and bundle.get("status") == "completed",
                 f"{path}: worker campaign is incomplete")
        _require(bundle.get("seeds") == expected_seeds, f"{path}: seed list mismatch")
        _require(bundle.get("variants") == list(VARIANTS), f"{path}: six-condition list mismatch")
        _require(bundle.get("expected_run_count") == len(expected_seeds) * len(VARIANTS)
                 and bundle.get("completed_run_count") == bundle.get("expected_run_count"),
                 f"{path}: incomplete or duplicate seed-condition outputs")
        worker_data[(task, architecture)] = bundle

    _require(set(worker_data) == {(t, a) for t in TASKS for a in ARCHITECTURES},
             "one or more of the four matched workers is missing")

    results: dict[tuple[int, str, int, str], dict] = {}
    for (task, architecture), bundle in worker_data.items():
        for result in bundle["results"]:
            key = (task, architecture, int(result["seed"]), result["variant"])
            _require(key not in results, f"duplicate seed-condition result {key}")
            _require(result["task_id"] == task and result["architecture"] == architecture,
                     f"result identity mismatch for {key}")
            _require(result["protocol_id"] == "HLG-BABI-T3-T5-LEARNING-v1.3.0",
                     f"result protocol mismatch for {key}")
            _require(result.get("confirmatory_evaluated") is False
                     and result["phases"]["generated_confirmatory"] is None
                     and result["candidate_fingerprint_after_confirmatory"] is None,
                     f"{key}: confirmatory evaluation occurred before candidate selection")
            _require(result.get("candidate_accepted_on_validation") is True,
                     f"{key}: validation acceptance gates failed")
            _require(result.get("warm_start_score_only_fingerprint_stable") is True,
                     f"{key}: score-only warm-start dynamics mutated fitted learner parameters")
            _require(result.get("warm_start_fingerprint_before_score_only")
                     == result.get("warm_start_fingerprint_after_score_only"),
                     f"{key}: warm-start fingerprint mismatch")
            _require(result.get("candidate_fingerprint_after_validation") == result.get("candidate_fingerprint"),
                     f"{key}: score-only validation mutated candidate fingerprint")
            _require(result["source_manifest"].get("implementation_commit"),
                     f"{key}: implementation commit missing from provenance")
            _require(result["source_manifest"].get("campaign_manifest_sha256"),
                     f"{key}: campaign manifest hash missing")
            _require(result["source_manifest"].get("protocol_document_sha256"),
                     f"{key}: protocol document hash missing")
            _require(result["source_manifest"].get("native_library_sha256")
                     == "38b278a93a5b3fa3b544f55d958a2f7a44bb6e1d39154e63072f5ed7be511e4b",
                     f"{key}: native library hash mismatch")
            _require(result["runtime"].get("one_native_step_per_tick") is True,
                     f"{key}: native-step invariant failed")
            if architecture == "HLB":
                capacity = result["source_manifest"]["campaign_capacity"]
                _require(capacity["configured_hlb_capacity"] == 262144
                         and capacity["preflight_passed"] is True,
                         f"{key}: HLB capacity preflight failed")
                _require(result["runtime"]["hlb_evidence_count"]
                         == result["source_manifest"]["campaign_capacity"]["source_event_count"]
                         and result["runtime"]["hlb_relation_count"]
                         == result["source_manifest"]["campaign_capacity"]["source_relation_count"],
                         f"{key}: HLB evidence totals do not match the frozen input workload")
                _require(result["runtime"]["hlb_evidence_count"] <= 262144
                         and result["runtime"]["hlb_relation_count"] <= 262144,
                         f"{key}: HLB capacity exceeded")
            for phase_name in ("warm_start_dynamics", "online_adaptation", "validation"):
                phase = result["phases"][phase_name]
                _require(phase["prediction_target_coverage_complete"] is True,
                         f"{key} {phase_name}: prediction target coverage incomplete")
                _require(phase["prediction_lifecycle"] and all(
                    phase["prediction_lifecycle"][target]["still_issued"] == 0
                    for target in TARGETS
                ), f"{key} {phase_name}: open forecasts remain at phase end")
                _require(set(phase["prediction_metrics"]) == set(TARGETS),
                         f"{key} {phase_name}: declared prediction target rows incomplete")
                _require(phase["task_outcome_prediction"]["count"] > 0,
                         f"{key} {phase_name}: task outcome forecast was not measured")
            results[key] = result

    _require(len(results) == 4 * len(expected_seeds) * len(VARIANTS),
             "total seed-condition result count mismatch")

    # Exact paired HLA/HLB parity is required for all six conditions and all phases.
    for task in TASKS:
        for seed in expected_seeds:
            for variant in VARIANTS:
                hla = results[(task, "HLA", seed, variant)]
                hlb = results[(task, "HLB", seed, variant)]
                _require(hla["candidate_fingerprint"] == hlb["candidate_fingerprint"],
                         f"candidate fingerprint parity failed: task {task} seed {seed} {variant}")
                _require(hla["online_learner_state_changed"] == hlb["online_learner_state_changed"],
                         f"learner update parity failed: task {task} seed {seed} {variant}")
                for field in (
                    "task_input_sha256", "annotation_manifest_sha256",
                    "confirmatory_manifest_sha256", "campaign_manifest_sha256",
                    "protocol_document_sha256", "native_runtime_commit",
                    "native_library_sha256",
                ):
                    _require(hla["source_manifest"].get(field) == hlb["source_manifest"].get(field),
                             f"source provenance parity failed: task {task} seed {seed} {variant} {field}")
                for phase_name in ("warm_start_dynamics", "online_adaptation", "validation"):
                    _phase_parity(hla["phases"][phase_name], hlb["phases"][phase_name],
                                  f"task{task}/{seed}/{variant}/{phase_name}")

    _assert_manipulations(results)

    # Select only among full_learning runs: ablations are causal controls, not
    # candidate alternatives. Choose one paired seed per task from validation.
    selected: dict[str, dict[str, Any]] = {}
    for task in TASKS:
        ranked = []
        for seed in expected_seeds:
            hla = results[(task, "HLA", seed, "full_learning")]
            hlb = results[(task, "HLB", seed, "full_learning")]
            relation_accuracy = []
            role_accuracy = []
            l0_mse = []
            abstention = []
            for candidate in (hla, hlb):
                metrics = candidate["phases"]["validation"]["prediction_metrics"]
                relation_accuracy.append(float(metrics["next_relation_pattern"]["accuracy"]))
                role_accuracy.append(float(metrics["next_event_role_pattern"]["accuracy"]))
                l0_mse.append(float(metrics["next_l0_features"]["mean_value"]))
                abstention.append(float(candidate["phases"]["validation"]["abstention_rate"]))
            l1_score = (sum(relation_accuracy) + sum(role_accuracy)) / 4.0
            ranked.append((
                -l1_score, sum(l0_mse) / 2.0, sum(abstention) / 2.0, seed,
                hla, hlb, l1_score,
            ))
        best = min(ranked, key=lambda row: row[:4])
        _neg_score, mean_l0_mse, mean_abstention, seed, hla, hlb, l1_score = best
        selected[str(task)] = {
            "seed": seed,
            "variant": "full_learning",
            "candidate_fingerprints": {
                "HLA": hla["candidate_fingerprint"],
                "HLB": hlb["candidate_fingerprint"],
            },
            "validation_selection_metrics": {
                "mean_l1_relation_event_role_accuracy": l1_score,
                "mean_l0_mse": mean_l0_mse,
                "mean_task_query_abstention_rate": mean_abstention,
            },
        }

    artifact_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }
    output = {
        "protocol_id": "HLG-BABI-T3-T5-LEARNING-v1.3.0",
        "stage": "validation_only_candidate_selection",
        "selection_policy": "select one paired seed per task from full_learning only; ablations remain controls",
        "input_worker_artifact_sha256": artifact_hashes,
        "expected_seeds": expected_seeds,
        "selected_candidates": selected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "accepted",
        "worker_artifacts": len(files),
        "seed_condition_results": len(results),
        "selected": {task: {"seed": row["seed"], "variant": row["variant"]}
                     for task, row in selected.items()},
        "output": str(args.output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
