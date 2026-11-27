"""Deterministic leakage-audited, four-shard non-learning bAbI preflight.

This runner executes only fixed symbolic baselines: no HLA/HLB parameter updates,
no native model training, no official test queries. It validates the frozen
360-unit orchestration, partition accounting, retry keys and evidence pipeline.
The resulting resource profile is explicitly a baseline workload measurement,
not a claim about HLA/HLB learning-run cost.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import sys
import time
import tracemalloc
from typing import Any

from rgm.experiments.babi_expansion_adapters import (
    ExpansionStory, GoldLabel, parse_expansion_source,
)
from rgm.experiments.babi_expansion_baselines import BASELINES, evaluate_baselines


TASK_FILES = {
    11: ("qa11_basic-coreference_train.txt", "qa11_basic-coreference_test.txt"),
    14: ("qa14_time-reasoning_train.txt", "qa14_time-reasoning_test.txt"),
    19: ("qa19_path-finding_train.txt", "qa19_path-finding_test.txt"),
}
TASK_EXPECTED = {
    11: {"fit_stories": 1800, "fit_queries": 9000, "validation_stories": 200, "validation_queries": 1000, "test_stories": 200, "test_queries": 1000},
    14: {"fit_stories": 1800, "fit_queries": 9000, "validation_stories": 200, "validation_queries": 1000, "test_stories": 200, "test_queries": 1000},
    19: {"fit_stories": 9000, "fit_queries": 9000, "validation_stories": 1000, "validation_queries": 1000, "test_stories": 1000, "test_queries": 1000},
}
FIT_VALIDATION_SEED = "HLG-BABI-EXPANSION-TRAIN-VALID-v1"
WARM_ONLINE_SEED = "HLG-BABI-EXPANSION-WARM-ONLINE-v1"
WARM_FRACTION = 0.80
TASKS = (11, 14, 19)
ARCHITECTURES = ("HLA", "HLB")
CONDITIONS = ("full_learning", "no_temporal", "no_relational",
              "no_abstraction", "no_task", "no_learning")
SEEDS = tuple(range(953100, 953110))
WORKER_COUNT = 4


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(payload, encoding="utf-8")
    return _file_sha(path)


def _story_query_count(stories: list[ExpansionStory]) -> int:
    return sum(len(story.queries) for story in stories)


def _story_event_count(stories: list[ExpansionStory]) -> int:
    return sum(len(story.events) for story in stories)


def _select_labels(stories: list[ExpansionStory], labels: list[GoldLabel]) -> list[GoldLabel]:
    ids = {query.query_id for story in stories for query in story.queries}
    return [label for label in labels if label.query_id in ids]


def _fit_validation_split(stories: list[ExpansionStory], task_id: int):
    ranked = sorted(
        stories,
        key=lambda story: sha256(
            f"{FIT_VALIDATION_SEED}:{task_id}:{story.story_id}".encode("utf-8")
        ).digest(),
    )
    validation_count = max(1, round(len(stories) * 0.10))
    validation_ids = {story.story_id for story in ranked[:validation_count]}
    fit = [story for story in stories if story.story_id not in validation_ids]
    validation = [story for story in stories if story.story_id in validation_ids]
    if {story.story_id for story in fit} & {story.story_id for story in validation}:
        raise AssertionError("fit/validation whole-story overlap")
    return fit, validation


def _warm_online_split(fit: list[ExpansionStory], task_id: int):
    ranked = sorted(
        fit,
        key=lambda story: sha256(
            f"{WARM_ONLINE_SEED}:{task_id}:{story.story_id}".encode("utf-8")
        ).digest(),
    )
    warm_count = int(len(fit) * WARM_FRACTION + 0.5)
    warm_ids = {story.story_id for story in ranked[:warm_count]}
    warm = [story for story in fit if story.story_id in warm_ids]
    online = [story for story in fit if story.story_id not in warm_ids]
    if not warm or not online:
        raise ValueError(f"Task {task_id}: warm/online split must be non-empty")
    if {story.story_id for story in warm} & {story.story_id for story in online}:
        raise AssertionError("warm-start/online story overlap")
    return warm, online


def _phase_record(stories: list[ExpansionStory]) -> dict:
    return {
        "story_ids": [story.story_id for story in stories],
        "query_ids": [query.query_id for story in stories for query in story.queries],
        "story_count": len(stories),
        "query_count": _story_query_count(stories),
        "event_count": _story_event_count(stories),
    }


def _run_units() -> list[dict]:
    rows = []
    for task_id in TASKS:
        for architecture in ARCHITECTURES:
            for condition in CONDITIONS:
                for seed in SEEDS:
                    index = len(rows)
                    key = f"task{task_id}-{architecture}-{condition}-seed{seed}"
                    rows.append({
                        "index": index,
                        "run_unit_key": key,
                        "task_id": task_id,
                        "architecture": architecture,
                        "condition": condition,
                        "seed": seed,
                        "shard": index % WORKER_COUNT,
                    })
    if len(rows) != 360:
        raise AssertionError(f"frozen run manifest must contain 360 units, got {len(rows)}")
    return rows


def prepare(source_root: Path, output_root: Path, protocol_path: Path) -> dict:
    """Build the exact whole-story phase manifest, baseline report and 360 keys."""
    output_root.mkdir(parents=True, exist_ok=True)
    if not protocol_path.is_file():
        raise FileNotFoundError(f"frozen learning protocol missing: {protocol_path}")
    protocol_sha = _file_sha(protocol_path)
    source_audit_path = source_root / "source-audit.json"
    source_audit_sha = _file_sha(source_audit_path) if source_audit_path.is_file() else None

    tasks: dict[str, dict] = {}
    task_cache: dict[int, tuple[list[ExpansionStory], list[GoldLabel], dict[str, list[ExpansionStory]]]] = {}
    baseline_report = {
        "schema": "HLG-BABI-EXPANSION-BASELINE-VALIDATION-v1",
        "protocol_sha256": protocol_sha,
        "label_policy": "Predictors receive only ExpansionStory/ExpansionQuery; GoldLabel enters only the score boundary.",
        "tasks": {},
    }

    for task_id, (train_name, test_name) in TASK_FILES.items():
        train_path, test_path = source_root / train_name, source_root / test_name
        train_stories, train_labels = parse_expansion_source(
            train_path, task_id=task_id, split="train", include_labels=True
        )
        test_stories, test_labels = parse_expansion_source(
            test_path, task_id=task_id, split="test-quarantined", include_labels=False
        )
        if test_labels:
            raise AssertionError(f"Task {task_id}: official test labels crossed parser boundary")
        fit, validation = _fit_validation_split(train_stories, task_id)
        warm, online = _warm_online_split(fit, task_id)
        phases = {"warm_start": warm, "online_adaptation": online, "validation": validation}
        counts = {
            "fit_stories": len(fit),
            "fit_queries": _story_query_count(fit),
            "validation_stories": len(validation),
            "validation_queries": _story_query_count(validation),
            "test_stories": len(test_stories),
            "test_queries": _story_query_count(test_stories),
        }
        if counts != TASK_EXPECTED[task_id]:
            raise ValueError(f"Task {task_id}: actual source/partition counts differ from frozen protocol: {counts}")
        phase_rows = {name: _phase_record(rows) for name, rows in phases.items()}
        warm_online_ids = set(phase_rows["warm_start"]["story_ids"]) | set(phase_rows["online_adaptation"]["story_ids"])
        if warm_online_ids != set(phase_rows["warm_start"]["story_ids"]) | set(phase_rows["online_adaptation"]["story_ids"]):
            raise AssertionError("warm/online partition construction failed")
        if warm_online_ids != {story.story_id for story in fit}:
            raise AssertionError("warm-start plus online phases do not exactly cover fit")
        if set(phase_rows["validation"]["story_ids"]) & warm_online_ids:
            raise AssertionError("validation overlaps fit phases")

        validation_labels = _select_labels(validation, train_labels)
        baseline = evaluate_baselines(validation, validation_labels, evaluate_labels=True)
        if set(baseline["task_results"].get(str(task_id), {})) != {
            name for name, _ in BASELINES[task_id]
        }:
            raise AssertionError(f"Task {task_id}: incomplete non-oracle baseline suite")
        scored = baseline["task_results"][str(task_id)]
        best_name, best_row = max(
            scored.items(),
            key=lambda item: (item[1]["answer_exact_match"], item[1]["support_witness_recall"] or 0.0, item[0]),
        )
        baseline_report["tasks"][str(task_id)] = {
            "validation_queries": counts["validation_queries"],
            "baseline_metrics": scored,
            "strongest_non_oracle_baseline": best_name,
            "strongest_non_oracle_answer_exact_match": best_row["answer_exact_match"],
        }
        tasks[str(task_id)] = {
            "source": {
                "train_file": train_name,
                "train_sha256": _file_sha(train_path),
                "test_file": test_name,
                "test_sha256": _file_sha(test_path),
                "official_test_labels_loaded": False,
            },
            "counts": counts,
            "phases": phase_rows,
        }
        task_cache[task_id] = (train_stories, train_labels, phases)

    units = _run_units()
    manifest_core = {
        "schema": "HLG-BABI-EXPANSION-PREFLIGHT-MANIFEST-v1",
        "protocol": {
            "path": str(protocol_path),
            "sha256": protocol_sha,
            "protocol_id": "HLG-BABI-EXPANSION-LEARNING-CAMPAIGN-v1",
        },
        "source_audit_sha256": source_audit_sha,
        "split_seeds": {
            "fit_validation": FIT_VALIDATION_SEED,
            "warm_online": WARM_ONLINE_SEED,
        },
        "fractions": {"fit_validation": "90/10", "warm_start": WARM_FRACTION, "online_adaptation": 1.0 - WARM_FRACTION},
        "worker_count": WORKER_COUNT,
        "units_per_shard": 90,
        "tasks": tasks,
        "run_units": units,
        "expected_query_presentations": 3_600_000,
        "baseline_predictions_per_presentation": 2,
        "learning_updates": 0,
        "official_test_query_presentations": 0,
    }
    manifest_core["manifest_sha256"] = _digest(manifest_core)
    _write_json(output_root / "phase-and-run-manifest.json", manifest_core)
    baseline_report["manifest_sha256"] = manifest_core["manifest_sha256"]
    _write_json(output_root / "baseline-validation.json", baseline_report)
    plan = {
        "schema": "HLG-BABI-EXPANSION-PREFLIGHT-PLAN-v1",
        "manifest_path": "phase-and-run-manifest.json",
        "manifest_sha256": manifest_core["manifest_sha256"],
        "source_root": str(source_root),
        "tasks": tasks,
        "run_unit_count": len(units),
        "shard_count": WORKER_COUNT,
        "baseline_validation": baseline_report["tasks"],
    }
    _write_json(output_root / "preflight-plan.json", plan)
    return {"manifest": manifest_core, "baseline_validation": baseline_report, "plan": plan}


def _resource_peak_rss_mb() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return float(peak / (1024.0 if sys.platform != "darwin" else 1024.0 * 1024.0))


def _atomic_json(path: Path, value: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return _file_sha(path)


def run_shard(plan_path: Path, shard_id: int, output_root: Path,
              *, inject_failure_key: str | None = None) -> dict:
    """Execute assigned run keys as non-learning baseline presentations."""
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    manifest_path = plan_path.parent / plan["manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_sha = manifest["manifest_sha256"]
    if shard_id not in range(WORKER_COUNT):
        raise ValueError("shard ID must be 0..3")
    output_root.mkdir(parents=True, exist_ok=True)
    units_dir = output_root / "units"
    units_dir.mkdir(parents=True, exist_ok=True)
    failures_dir = output_root / "failures"
    failures_dir.mkdir(parents=True, exist_ok=True)
    assigned = [row for row in manifest["run_units"] if row["shard"] == shard_id]
    if len(assigned) != 90:
        raise ValueError(f"shard {shard_id} expected 90 units, got {len(assigned)}")
    status_path = output_root / "shard-status.json"
    _atomic_json(status_path, {
        "schema": "HLG-BABI-EXPANSION-PREFLIGHT-SHARD-v1",
        "shard": shard_id, "status": "running",
        "manifest_sha256": manifest_sha,
        "expected_unit_keys": [row["run_unit_key"] for row in assigned],
        "completed_unit_keys": [],
    })

    loaded: dict[int, tuple[dict[str, list[ExpansionStory]], list[GoldLabel]]] = {}
    for task_id, (train_name, _) in TASK_FILES.items():
        stories, labels = parse_expansion_source(
            Path(plan["source_root"]) / train_name,
            task_id=task_id, split="train", include_labels=True,
        )
        fit, validation = _fit_validation_split(stories, task_id)
        warm, online = _warm_online_split(fit, task_id)
        loaded[task_id] = (
            {"warm_start": warm, "online_adaptation": online, "validation": validation},
            labels,
        )

    started = time.perf_counter()
    prior_resource_path = output_root / "partial-resource-usage.json"
    prior_resource = (json.loads(prior_resource_path.read_text(encoding="utf-8"))
                      if prior_resource_path.is_file() else {})
    tracemalloc.start()
    completed: list[str] = []
    skipped: list[str] = []
    query_presentations = baseline_predictions = story_presentations = event_presentations = 0
    try:
        for unit in assigned:
            key = unit["run_unit_key"]
            result_path = units_dir / f"{key}.json"
            if result_path.is_file():
                existing = json.loads(result_path.read_text(encoding="utf-8"))
                if (existing.get("status") == "success"
                        and existing.get("manifest_sha256") == manifest_sha
                        and existing.get("run_unit_key") == key):
                    completed.append(key)
                    skipped.append(key)
                    query_presentations += int(existing["query_presentations"])
                    baseline_predictions += int(existing["baseline_prediction_presentations"])
                    story_presentations += int(existing["story_presentations"])
                    event_presentations += int(existing["event_presentations"])
                    continue
                raise ValueError(f"existing result for {key} is not a reusable immutable success")
            if inject_failure_key == key and not (failures_dir / f"{key}.failure.json").exists():
                _atomic_json(failures_dir / f"{key}.failure.json", {
                    "run_unit_key": key, "manifest_sha256": manifest_sha,
                    "status": "injected_failure_for_retry_test",
                })
                raise RuntimeError(f"injected one-time failure for retry acceptance: {key}")

            task_id = int(unit["task_id"])
            phases, all_labels = loaded[task_id]
            phase_results = {}
            unit_queries = unit_events = unit_stories = 0
            for phase_name in ("warm_start", "online_adaptation", "validation"):
                phase_stories = phases[phase_name]
                phase_queries = _story_query_count(phase_stories)
                phase_events = _story_event_count(phase_stories)
                unit_queries += phase_queries
                unit_events += phase_events
                unit_stories += len(phase_stories)
                if phase_name == "validation":
                    phase_labels = _select_labels(phase_stories, all_labels)
                    outcome = evaluate_baselines(phase_stories, phase_labels, evaluate_labels=True)
                else:
                    # Deliberately no evaluator labels in either fit phase.
                    outcome = evaluate_baselines(phase_stories, [], evaluate_labels=False)
                phase_results[phase_name] = {
                    "story_count": len(phase_stories),
                    "event_count": phase_events,
                    "query_presentations": phase_queries,
                    "learning_updates": 0,
                    "evaluator_labels_received": phase_name == "validation",
                    "baseline_outcome": outcome["task_results"].get(str(task_id), {}),
                }
            expected_queries = int(manifest["tasks"][str(task_id)]["counts"]["fit_queries"]) + int(
                manifest["tasks"][str(task_id)]["counts"]["validation_queries"]
            )
            if unit_queries != expected_queries:
                raise AssertionError(f"{key}: query presentation count {unit_queries} != {expected_queries}")
            result = {
                "schema": "HLG-BABI-EXPANSION-PREFLIGHT-UNIT-v1",
                "status": "success",
                "run_unit_key": key,
                "manifest_sha256": manifest_sha,
                "task_id": task_id,
                "architecture": unit["architecture"],
                "condition": unit["condition"],
                "seed": unit["seed"],
                "shard": shard_id,
                "phase_results": phase_results,
                "query_presentations": unit_queries,
                "baseline_prediction_presentations": unit_queries * len(BASELINES[task_id]),
                "story_presentations": unit_stories,
                "event_presentations": unit_events,
                "learning_updates": 0,
                "model_steps": 0,
                "official_test_queries": 0,
                "code_commit": os.environ.get("GITHUB_SHA", "local-preflight"),
            }
            result["result_sha256"] = _atomic_json(result_path, result)
            completed.append(key)
            query_presentations += unit_queries
            baseline_predictions += result["baseline_prediction_presentations"]
            story_presentations += unit_stories
            event_presentations += unit_events
            _atomic_json(status_path, {
                "schema": "HLG-BABI-EXPANSION-PREFLIGHT-SHARD-v1",
                "shard": shard_id, "status": "running",
                "manifest_sha256": manifest_sha,
                "expected_unit_keys": [row["run_unit_key"] for row in assigned],
                "completed_unit_keys": completed,
                "skipped_unit_keys": skipped,
            })
        elapsed = time.perf_counter() - started + float(prior_resource.get("elapsed_seconds", 0.0))
        _, trace_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        trace_peak = max(trace_peak, int(prior_resource.get("tracemalloc_peak_bytes", 0)))
        query_presentations += 0
        baseline_predictions += 0
        unit_files = [p for p in units_dir.glob("*.json")]
        artifact_bytes = sum(p.stat().st_size for p in output_root.rglob("*") if p.is_file())
        usage = {
            "schema": "HLG-BABI-EXPANSION-PREFLIGHT-RESOURCE-v1",
            "shard": shard_id,
            "manifest_sha256": manifest_sha,
            "elapsed_seconds": elapsed,
            "query_presentations": query_presentations,
            "baseline_prediction_presentations": baseline_predictions,
            "queries_per_second": query_presentations / elapsed if elapsed else 0.0,
            "story_presentations": story_presentations,
            "event_presentations": event_presentations,
            "event_records_per_second": event_presentations / elapsed if elapsed else 0.0,
            "peak_rss_mb": _resource_peak_rss_mb(),
            "tracemalloc_peak_mb": trace_peak / (1024.0 * 1024.0),
            "tracemalloc_peak_bytes": trace_peak,
            "retry_elapsed_seconds_included": float(prior_resource.get("elapsed_seconds", 0.0)),
            "unit_artifact_count": len(unit_files),
            "artifact_storage_bytes": artifact_bytes,
            "learning_updates": 0,
            "official_test_queries": 0,
            "measurement_scope": "symbolic non-learning baseline workload and shard orchestration; excludes HLA/HLB native learner compute",
        }
        _atomic_json(output_root / "resource-usage.json", usage)
        status = {
            "schema": "HLG-BABI-EXPANSION-PREFLIGHT-SHARD-v1",
            "shard": shard_id, "status": "success",
            "manifest_sha256": manifest_sha,
            "expected_unit_keys": [row["run_unit_key"] for row in assigned],
            "completed_unit_keys": completed,
            "skipped_unit_keys": skipped,
            "failed_unit_keys": [],
            "unit_count": len(completed),
            "resource_file": "resource-usage.json",
            "recovered_failure_diagnostic": "failure-diagnostic.json" if (output_root / "failure-diagnostic.json").is_file() else None,
        }
        _atomic_json(status_path, status)
        return status
    except Exception as exc:
        trace_peak = 0
        if tracemalloc.is_tracing():
            _, trace_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
        partial_elapsed = time.perf_counter() - started
        trace_peak = max(trace_peak, int(prior_resource.get("tracemalloc_peak_bytes", 0)))
        _atomic_json(prior_resource_path, {
            "schema": "HLG-BABI-EXPANSION-PREFLIGHT-PARTIAL-RESOURCE-v1",
            "shard": shard_id,
            "manifest_sha256": manifest_sha,
            "elapsed_seconds": float(prior_resource.get("elapsed_seconds", 0.0)) + partial_elapsed,
            "query_presentations_completed_before_failure": query_presentations,
            "baseline_prediction_presentations_completed_before_failure": baseline_predictions,
            "peak_rss_mb": max(_resource_peak_rss_mb(), float(prior_resource.get("peak_rss_mb", 0.0))),
            "tracemalloc_peak_bytes": trace_peak,
        })
        _atomic_json(output_root / "failure-diagnostic.json", {
            "schema": "HLG-BABI-EXPANSION-PREFLIGHT-FAILURE-v1",
            "shard": shard_id, "manifest_sha256": manifest_sha,
            "completed_unit_keys": completed,
            "error_type": type(exc).__name__, "error": str(exc),
        })
        _atomic_json(status_path, {
            "schema": "HLG-BABI-EXPANSION-PREFLIGHT-SHARD-v1",
            "shard": shard_id, "status": "failed",
            "manifest_sha256": manifest_sha,
            "expected_unit_keys": [row["run_unit_key"] for row in assigned],
            "completed_unit_keys": completed,
            "skipped_unit_keys": skipped,
            "error": str(exc),
        })
        raise


def aggregate(plan_path: Path, shard_roots: list[Path], output_path: Path) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    manifest = json.loads((plan_path.parent / plan["manifest_path"]).read_text(encoding="utf-8"))
    manifest_sha = manifest["manifest_sha256"]
    expected = {row["run_unit_key"]: row for row in manifest["run_units"]}
    if len(shard_roots) != WORKER_COUNT:
        raise ValueError("aggregation requires exactly four shard evidence directories")
    results: dict[str, dict] = {}
    resources = []
    for shard_root in shard_roots:
        status_path = shard_root / "shard-status.json"
        if not status_path.is_file():
            raise FileNotFoundError(f"missing shard status: {status_path}")
        status = json.loads(status_path.read_text(encoding="utf-8"))
        shard_id = int(status["shard"])
        if status["status"] != "success" or status["manifest_sha256"] != manifest_sha:
            raise ValueError(f"shard {shard_id}: failed status or wrong manifest fingerprint")
        expected_keys = {key for key, row in expected.items() if row["shard"] == shard_id}
        if set(status["completed_unit_keys"]) != expected_keys:
            raise ValueError(f"shard {shard_id}: completed keys differ from the frozen assignment")
        for key in sorted(expected_keys):
            result_path = shard_root / "units" / f"{key}.json"
            if not result_path.is_file():
                raise FileNotFoundError(f"shard {shard_id}: missing unit artifact {key}")
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if result.get("status") != "success" or result.get("manifest_sha256") != manifest_sha:
                raise ValueError(f"{key}: invalid or mixed-manifest result")
            if key in results:
                raise ValueError(f"duplicate run unit key: {key}")
            if int(result["shard"]) != shard_id or expected[key]["shard"] != shard_id:
                raise ValueError(f"{key}: assigned to wrong worker shard")
            results[key] = result
        resource_path = shard_root / "resource-usage.json"
        if not resource_path.is_file():
            raise FileNotFoundError(f"shard {shard_id}: missing resource usage")
        resources.append(json.loads(resource_path.read_text(encoding="utf-8")))
    if set(results) != set(expected):
        missing = sorted(set(expected) - set(results))
        extra = sorted(set(results) - set(expected))
        raise ValueError(f"run-unit coverage mismatch: missing={missing[:5]}, extra={extra[:5]}")
    total_queries = sum(result["query_presentations"] for result in results.values())
    total_predictions = sum(result["baseline_prediction_presentations"] for result in results.values())
    total_learning_updates = sum(result["learning_updates"] for result in results.values())
    if total_queries != 3_600_000 or total_learning_updates != 0:
        raise ValueError(f"preflight workload/integrity mismatch: queries={total_queries}, updates={total_learning_updates}")
    if any(row["official_test_queries"] for row in results.values()):
        raise ValueError("official test queries appeared in preflight unit results")
    elapsed = sum(float(row["elapsed_seconds"]) for row in resources)
    total_artifact_bytes = sum(int(row["artifact_storage_bytes"]) for row in resources)
    summary = {
        "schema": "HLG-BABI-EXPANSION-PREFLIGHT-AGGREGATE-v1",
        "status": "PASS",
        "manifest_sha256": manifest_sha,
        "run_units_expected": len(expected),
        "run_units_accepted": len(results),
        "shards": WORKER_COUNT,
        "units_per_shard": [sum(row["shard"] == shard for row in expected.values()) for shard in range(WORKER_COUNT)],
        "query_presentations": total_queries,
        "baseline_prediction_presentations": total_predictions,
        "story_presentations": sum(result["story_presentations"] for result in results.values()),
        "event_presentations": sum(result["event_presentations"] for result in results.values()),
        "learning_updates": total_learning_updates,
        "model_steps": sum(result["model_steps"] for result in results.values()),
        "official_test_queries": 0,
        "resource_measurements": {
            "worker_elapsed_seconds_sum": elapsed,
            "worker_peak_rss_mb_max": max(float(row["peak_rss_mb"]) for row in resources),
            "worker_tracemalloc_peak_mb_max": max(float(row["tracemalloc_peak_mb"]) for row in resources),
            "query_presentations_per_worker_second": total_queries / elapsed if elapsed else 0.0,
            "artifact_storage_bytes": total_artifact_bytes,
            "artifact_storage_mib": total_artifact_bytes / (1024.0 * 1024.0),
            "per_shard": resources,
            "scope": "non-learning symbolic baseline workload; no HLA/HLB learner compute",
        },
        "retry_integrity": {
            "unique_run_unit_keys": len(results),
            "duplicate_keys": 0,
            "missing_keys": 0,
            "wrong_shard_keys": 0,
            "manifest_mismatches": 0,
        },
        "claim_boundary": "Passes source/partition/baseline/sharding/retry/evidence and baseline workload measurement. Does not estimate native HLA/HLB learning compute or establish learned performance.",
    }
    summary["aggregate_sha256"] = _write_json(output_path, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path("data/babi-v1.2-expansion"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/babi-expansion-preflight"))
    parser.add_argument("--protocol", type=Path, default=Path("docs/experiments/HLG_BABI_EXPANSION_LEARNING_CAMPAIGN_v1_0.json"))
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--shard", type=int, choices=range(4))
    parser.add_argument("--shard-output", type=Path)
    parser.add_argument("--inject-failure-key")
    parser.add_argument("--aggregate", action="store_true")
    parser.add_argument("--shard-dirs", nargs="*", type=Path, default=[])
    parser.add_argument("--aggregate-output", type=Path)
    args = parser.parse_args()
    if args.prepare:
        result = prepare(args.source_root, args.output_root, args.protocol)
        print(json.dumps({
            "manifest_sha256": result["manifest"]["manifest_sha256"],
            "run_units": result["plan"]["run_unit_count"],
            "baseline_validation": result["baseline_validation"]["tasks"],
        }, indent=2, sort_keys=True))
        return 0
    if args.shard is not None:
        if not args.plan or not args.shard_output:
            parser.error("--shard requires --plan and --shard-output")
        print(json.dumps(run_shard(args.plan, args.shard, args.shard_output,
                                   inject_failure_key=args.inject_failure_key), indent=2))
        return 0
    if args.aggregate:
        if not args.plan or not args.aggregate_output:
            parser.error("--aggregate requires --plan and --aggregate-output")
        print(json.dumps(aggregate(args.plan, args.shard_dirs, args.aggregate_output), indent=2))
        return 0
    parser.error("select --prepare, --shard or --aggregate")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
