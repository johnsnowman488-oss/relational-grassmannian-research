#!/usr/bin/env python3
"""Run one full-scale Task 11 campaign or reserved resource-preflight unit."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import sys
import time
import tracemalloc

from rgm.experiments.babi_expansion_adapters import (
    parse_expansion_source,
)
from rgm.experiments.babi_expansion_preflight import _fit_validation_split
from rgm.experiments.babi_task11_prediction import (
    evaluate_task11_predictions,
    predict_task11_from_learned_state,
    task11_prediction_model_fingerprint,
)
from rgm.experiments.babi_expansion_runtime import BabiExpansionRuntime
from rgm.leptograph.m4.hierarchical import create_hla_adapter, create_hlb_adapter
from rgm.leptograph.m4.learning import ErrorChannel, LearningRuntime
from rgm.memory.soe import SOEMemory


NATIVE_COMMIT = "48228f8c326c0e8546855eb898d374453d705b77"
HLB_CAPACITY = 262144
TOP_DOWN_GAIN = 1.0
ELIGIBILITY_CAPACITY = 131072
SOE_DT = 0.01
FEATURE_DIMS = (3, 3, 3)
CHANNELS = {
    "full_learning": frozenset(ErrorChannel),
    "no_temporal": frozenset({ErrorChannel.RELATIONAL, ErrorChannel.ABSTRACTION, ErrorChannel.TASK}),
    "no_relational": frozenset({ErrorChannel.TEMPORAL, ErrorChannel.ABSTRACTION, ErrorChannel.TASK}),
    "no_abstraction": frozenset({ErrorChannel.TEMPORAL, ErrorChannel.RELATIONAL, ErrorChannel.TASK}),
    "no_task": frozenset({ErrorChannel.TEMPORAL, ErrorChannel.RELATIONAL, ErrorChannel.ABSTRACTION}),
    "no_learning": frozenset(),
}


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str).encode("utf-8")


def _digest(value) -> str:
    return sha256(_canonical(value)).hexdigest()


def _file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _phase_stories(stories, ids):
    by_id = {story.story_id: story for story in stories}
    if len(by_id) != len(stories):
        raise ValueError("duplicate Task 11 story IDs")
    missing = set(ids) - set(by_id)
    if missing:
        raise ValueError(f"manifest references missing stories: {sorted(missing)[:3]}")
    return [by_id[story_id] for story_id in ids]


def _memories():
    return [SOEMemory(feature_dim=dimension) for dimension in FEATURE_DIMS]


def _kernels(memories):
    # Match the already accepted Task 11 persistent-resource qualification.
    return [{
        "gamma": bank.decay_rates[::-1].tolist(),
        "w": [0.25] * bank.channel_count,
        "linear_decay": [0.05] * (bank.channel_count * bank.feature_dim),
        "forcing_bias": [0.0] * (bank.channel_count * bank.feature_dim),
    } for bank in memories]


def _make_adapter(architecture, native_library, gfe):
    memories = _memories()
    kernels = _kernels(memories)
    if architecture == "HLA":
        return create_hla_adapter(
            native_library, memories, kernels, dt=SOE_DT,
            runtime_factory=gfe.create_persistent_hierarchy_runtime,
            top_down_gain=TOP_DOWN_GAIN,
        )
    return create_hlb_adapter(
        native_library, memories, kernels, dt=SOE_DT,
        runtime_factory=gfe.create_persistent_hierarchy_runtime,
        capacity=HLB_CAPACITY,
        top_down_gain=TOP_DOWN_GAIN,
    )


def _learning_state(adapter):
    learning = adapter.learning
    state = {
        "level0": learning.level0.snapshot(),
        "relations": learning.relations.snapshot(),
        "event_roles": learning.event_roles.snapshot(),
        "context_transitions": learning.context_transitions.snapshot(),
        "temporal_credit": learning.temporal_credit.snapshot(),
        "task_outcomes": learning.task_outcomes.snapshot(),
        "eligibility": learning.eligibility.snapshot(),
    }
    if getattr(adapter, "architecture", None) == "HLB":
        state["hlb_model_store"] = adapter.store.snapshot()
    return state


def _checkpoint(runtime):
    return {
        "director": runtime.director.snapshot(),
        "native": runtime.adapter.bridge.runtime.checkpoint(),
    }


def _restore(runtime, checkpoint):
    runtime.adapter.bridge.runtime.restore(checkpoint["native"])
    runtime.director.restore(checkpoint["director"], preserve_observations=False)


def _write_json(path: Path, value) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return _file_sha(path)


def run_unit(source_root: Path, manifest_path: Path, protocol_path: Path,
             native_library_path: Path, python_abi_path: Path,
             architecture: str, condition: str, seed: int,
             output_root: Path, run_kind: str) -> dict:
    if architecture not in {"HLA", "HLB"} or condition not in CHANNELS:
        raise ValueError("unknown Task 11 architecture or condition")
    if run_kind not in {"preflight", "campaign"}:
        raise ValueError("run kind must be preflight or campaign")
    if run_kind == "preflight" and (seed != 953099 or condition not in {"full_learning", "no_learning"}):
        raise ValueError("preflight permits only reserved seed 953099 and full/no-learning conditions")
    if run_kind == "campaign" and seed not in range(953100, 953110):
        raise ValueError("campaign seed is outside the frozen ten-seed range")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if manifest.get("native_commit") != NATIVE_COMMIT:
        raise ValueError("manifest native commit differs from the pinned ABI")
    if manifest.get("protocol_sha256") != _file_sha(protocol_path):
        raise ValueError("campaign protocol digest differs from manifest")
    if manifest.get("hlb_model_relation_capacity") != HLB_CAPACITY:
        raise ValueError("HLB model relation capacity differs from frozen manifest")
    if manifest.get("eligibility_capacity") != ELIGIBILITY_CAPACITY:
        raise ValueError("eligibility capacity differs from frozen manifest")
    if manifest.get("top_down_gain") != TOP_DOWN_GAIN:
        raise ValueError("H0 top-down gain differs from frozen manifest")
    if manifest.get("soe_feature_dims") != list(FEATURE_DIMS):
        raise ValueError("SOE feature dimensions differ from frozen manifest")
    if manifest.get("soe_dt") != SOE_DT:
        raise ValueError("SOE time step differs from frozen manifest")
    if not native_library_path.is_file():
        raise FileNotFoundError(f"pinned native library is missing: {native_library_path}")
    native_library_sha256 = _file_sha(native_library_path)

    run_key = f"task11-{architecture}-{condition}-seed{seed}"
    manifest_shard = None
    if run_kind == "campaign":
        units = {row["run_unit_key"]: row for row in manifest["run_units"]}
        if run_key not in units:
            raise ValueError(f"run unit is not in frozen manifest: {run_key}")
        manifest_shard = units[run_key]["shard"]
    partition = manifest["seed_partitions"].get(str(seed))
    if partition is None:
        raise ValueError(f"missing seed-specific nested partition for seed {seed}")

    source_path = source_root / manifest["source"]["member"]
    if _file_sha(source_path) != manifest["source"]["sha256"]:
        raise ValueError("Task 11 source hash differs from frozen manifest")
    # Learner-side parse: no evaluator labels are materialized.
    stories, labels_from_learner_parse = parse_expansion_source(
        source_path, task_id=11, split="train", include_labels=False,
    )
    if labels_from_learner_parse:
        raise AssertionError("learner-side parser exposed evaluator labels")
    fit, validation = _fit_validation_split(stories, 11)
    fit_ids = {story.story_id for story in fit}
    validation_ids = {story.story_id for story in validation}
    warm = _phase_stories(fit, partition["warm_start"]["story_ids"])
    online = _phase_stories(fit, partition["online_adaptation"]["story_ids"])
    if set(s.story_id for s in warm) & set(s.story_id for s in online):
        raise AssertionError("warm-start and online-adaptation story overlap")
    if set(s.story_id for s in warm) | set(s.story_id for s in online) != fit_ids:
        raise AssertionError("warm-start plus online phases do not cover fit")
    if set(s.story_id for s in validation) != set(manifest["validation"]["story_ids"]):
        raise AssertionError("validation partition differs from manifest")
    if fit_ids & validation_ids:
        raise AssertionError("fit and validation overlap")

    sys.path.insert(0, str(python_abi_path))
    import gfe_ctypes as gfe
    native_library = gfe.load_gfe_library()
    adapter = _make_adapter(architecture, native_library, gfe)
    initial_native_state = adapter.bridge.runtime.get_state()
    initial_kernel_weights = [row["w"] for row in initial_native_state["active_kernels"]]
    print(json.dumps({
        "run_key": run_key,
        "initial_native_kernel_weights": initial_kernel_weights,
        "initial_native_spectral_units": initial_native_state["spectral_units"],
    }, sort_keys=True), flush=True)
    if any(not weights or sum(weights) <= 0 for weights in initial_kernel_weights):
        raise RuntimeError("pinned native runtime was created with zero-sum kernel weights")
    channels = CHANNELS[condition]
    runtime = BabiExpansionRuntime(
        adapter,
        capacity=HLB_CAPACITY,
        learning_enabled=(condition != "no_learning"),
        enabled_channels=channels,
        eligibility_capacity=ELIGIBILITY_CAPACITY,
    )
    tracemalloc.start()
    worker_started = time.perf_counter()
    phase_times = {}
    try:
        start = time.perf_counter()
        runtime.ingest_story_sequence(warm)
        phase_times["warm_start_seconds"] = time.perf_counter() - start

        start = time.perf_counter()
        runtime.ingest_story_sequence(online)
        phase_times["online_adaptation_seconds"] = time.perf_counter() - start

        checkpoint_started = time.perf_counter()
        checkpoint = _checkpoint(runtime)
        checkpoint_seconds = time.perf_counter() - checkpoint_started
        checkpoint_bytes = len(_canonical(checkpoint))
        checkpoint_fingerprint = _digest(checkpoint)
        restore_started = time.perf_counter()
        _restore(runtime, checkpoint)
        restore_seconds = time.perf_counter() - restore_started
        restored_fingerprint = _digest(_checkpoint(runtime))
        if restored_fingerprint != checkpoint_fingerprint:
            raise AssertionError("full HLA/HLB/native checkpoint recovery mismatch")

        fit_model_state = _learning_state(adapter)
        fit_model_fingerprint = _digest(fit_model_state)
        # Freeze the architecture-specific answer model before any validation
        # story is ingested. This is the only model snapshot eligible for the
        # later, once-only confirmatory phase.
        model_snapshot = {
            "schema": "HLG-BABI-TASK11-ANSWER-MODEL-SNAPSHOT-v1",
            "run_key": run_key,
            "manifest_shard": manifest_shard,
            "architecture": architecture,
            "condition": condition,
            "seed": seed,
            "manifest_sha256": manifest["manifest_sha256"],
            "protocol_sha256": manifest["protocol_sha256"],
            "source_sha256": manifest["source"]["sha256"],
            "native_commit": NATIVE_COMMIT,
            "native_library_sha256": native_library_sha256,
            "top_down_gain": TOP_DOWN_GAIN,
            "fit_model_fingerprint": fit_model_fingerprint,
            "context_transitions": adapter.learning.context_transitions.snapshot(),
            "hlb_model_relations": (
                adapter.store.snapshot() if architecture == "HLB" else None
            ),
            "source_sha256": manifest["source"]["sha256"],
            "manifest_sha256": manifest["manifest_sha256"],
            "protocol_sha256": manifest["protocol_sha256"],
            "evaluator_labels_included": False,
        }
        _write_json(output_root / "model-snapshot.json", model_snapshot)
        runtime.learning_enabled = False
        validation_started = time.perf_counter()
        decisions = {}
        prediction_rows = []
        # The candidate is frozen during score-only validation. Fingerprint it once.
        frozen_prediction_fingerprint = task11_prediction_model_fingerprint(adapter)
        for story in validation:
            runtime.ingest_story_sequence([story])
            for query in story.queries:
                decision = predict_task11_from_learned_state(
                    adapter, story, query,
                    frozen_model_fingerprint=frozen_prediction_fingerprint,
                )
                decisions[query.query_id] = decision
                prediction_rows.append({
                    "query_id": query.query_id,
                    "story_id": story.story_id,
                    "answer": decision.prediction.answer,
                    "abstained": decision.prediction.abstained,
                    "reason": decision.prediction.reason,
                    "witness_event_ids": list(decision.prediction.witness_event_ids),
                    "model_context": decision.model_context,
                    "model_fingerprint": decision.model_fingerprint,
                    "grounding_event_ids": list(decision.grounding_event_ids),
                })
        validation_seconds = time.perf_counter() - validation_started
        validation_model_fingerprint = _digest(_learning_state(adapter))
        validation_updates = int(validation_model_fingerprint != fit_model_fingerprint)
        if validation_updates:
            raise AssertionError("validation changed learned parameters or HLB model relations")

        # Only now open evaluator labels. They were not present in learner-side
        # parsing, training, validation ingestion, or prediction generation.
        _all_stories_with_labels, all_labels = parse_expansion_source(
            source_path, task_id=11, split="train", include_labels=True,
        )
        validation_query_ids = {
            query.query_id for story in validation for query in story.queries
        }
        validation_labels = [label for label in all_labels
                             if label.query_id in validation_query_ids]
        if len(validation_labels) != len(validation_query_ids):
            raise AssertionError("validation evaluator labels are incomplete")
        evaluation = evaluate_task11_predictions(validation, decisions, validation_labels)

        elapsed = time.perf_counter() - worker_started
        _, trace_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        output_root.mkdir(parents=True, exist_ok=True)
        _write_json(output_root / "per-run-config.json", {
            "run_key": run_key,
            "run_kind": run_kind,
            "manifest_shard": manifest_shard,
            "task_id": 11,
            "architecture": architecture,
            "condition": condition,
            "seed": seed,
            "enabled_channels": sorted(channel.value for channel in channels),
            "learning_enabled": condition != "no_learning",
            "warm_story_count": len(warm),
            "online_story_count": len(online),
            "validation_story_count": len(validation),
            "warm_story_ids_sha256": partition["warm_start"]["story_ids_sha256"],
            "online_story_ids_sha256": partition["online_adaptation"]["story_ids_sha256"],
            "validation_story_ids_sha256": manifest["validation"]["story_ids_sha256"],
            "manifest_sha256": manifest["manifest_sha256"],
            "protocol_sha256": manifest["protocol_sha256"],
            "source_sha256": manifest["source"]["sha256"],
            "native_commit": NATIVE_COMMIT,
            "native_library_sha256": native_library_sha256,
            "soe_feature_dims": list(FEATURE_DIMS),
            "soe_dt": SOE_DT,
            "hlb_model_relation_capacity": HLB_CAPACITY,
            "eligibility_capacity": ELIGIBILITY_CAPACITY,
            "top_down_gain": TOP_DOWN_GAIN,
        })
        _write_json(output_root / "source-and-partition-manifest.json", {
            "manifest_sha256": manifest["manifest_sha256"],
            "source": manifest["source"],
            "fit": manifest["fit"],
            "warm_start": partition["warm_start"],
            "online_adaptation": partition["online_adaptation"],
            "validation": manifest["validation"],
            "official_test_queries_loaded": 0,
        })
        with (output_root / "prediction-journal.jsonl").open("w", encoding="utf-8") as stream:
            for row in prediction_rows:
                stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        with (output_root / "witness-audit.jsonl").open("w", encoding="utf-8") as stream:
            for row in prediction_rows:
                stream.write(json.dumps({
                    "query_id": row["query_id"],
                    "story_id": row["story_id"],
                    "predicted_witness_event_ids": row["witness_event_ids"],
                    "grounding_event_ids": row["grounding_event_ids"],
                    "abstained": row["abstained"],
                    "reason": row["reason"],
                }, sort_keys=True) + "\n")
        metrics = {
            "schema": "HLG-BABI-TASK11-CAMPAIGN-UNIT-v1",
            "status": "PASS",
            "run_key": run_key,
            "run_kind": run_kind,
            "manifest_shard": manifest_shard,
            "task_id": 11,
            "architecture": architecture,
            "condition": condition,
            "seed": seed,
            "manifest_sha256": manifest["manifest_sha256"],
            "protocol_sha256": manifest["protocol_sha256"],
            "source_sha256": manifest["source"]["sha256"],
            "native_commit": NATIVE_COMMIT,
            "native_library_sha256": native_library_sha256,
            "soe_feature_dims": list(FEATURE_DIMS),
            "soe_dt": SOE_DT,
            "top_down_gain": TOP_DOWN_GAIN,
            "fit_stories": len(fit),
            "warm_start_stories": len(warm),
            "online_adaptation_stories": len(online),
            "validation_stories": len(validation),
            "validation_queries": len(validation_query_ids),
            "validation_evaluator_labels_opened_after_predictions": len(validation_labels),
            "learner_labels_loaded": 0,
            "official_test_queries_loaded": 0,
            "confirmatory_labels_loaded": 0,
            "validation_parameter_updates": validation_updates,
            "fit_model_fingerprint": fit_model_fingerprint,
            "validation_model_fingerprint": validation_model_fingerprint,
            "checkpoint_fingerprint": checkpoint_fingerprint,
            "restored_checkpoint_fingerprint": restored_fingerprint,
            "checkpoint_bytes": checkpoint_bytes,
            "checkpoint_seconds": checkpoint_seconds,
            "restore_seconds": restore_seconds,
            "phase_times": phase_times,
            "validation_seconds": validation_seconds,
            "elapsed_seconds": elapsed,
            "peak_worker_rss_mb": peak_rss_mb,
            "peak_python_allocation_mb": trace_peak / (1024.0 * 1024.0),
            "evaluation": evaluation,
            "no_task_condition_policy": (
                "Task 11 placebo/negative control; no independent task-outcome training targets are admitted."
            ),
        }
        _write_json(output_root / "per-run-metrics.json", metrics)
        _write_json(output_root / "resource-usage.json", {
            "elapsed_seconds": elapsed,
            "peak_worker_rss_mb": peak_rss_mb,
            "peak_python_allocation_mb": trace_peak / (1024.0 * 1024.0),
            "checkpoint_bytes": checkpoint_bytes,
            "checkpoint_seconds": checkpoint_seconds,
            "restore_seconds": restore_seconds,
        })
        _write_json(output_root / "per-run-stdout.log", {
            "run_key": run_key,
            "status": "PASS",
            "answer_exact_match": evaluation["answer_exact_match"],
            "forecast_coverage": evaluation["forecast_coverage"],
            "support_witness_recall": evaluation["support_witness_recall"],
            "false_witness_rate": evaluation["false_witness_rate"],
        })
        (output_root / "per-run-stderr.log").write_text("", encoding="utf-8")
        artifact_bytes = sum(
            path.stat().st_size for path in output_root.iterdir()
            if path.is_file() and path.name != "sha256sums.txt"
        )
        metrics["artifact_bytes"] = artifact_bytes
        metrics["resource_gate"] = {
            "rss_limit_mb": 2048,
            "python_allocation_limit_mb": 1024,
            "checkpoint_limit_bytes": 536870912,
            "unit_wall_limit_seconds": 3600,
            "artifact_limit_bytes": 268435456,
            "within_limits": (
                peak_rss_mb <= 2048
                and trace_peak / (1024.0 * 1024.0) <= 1024
                and checkpoint_bytes <= 536870912
                and elapsed <= 3600
                and artifact_bytes <= 268435456
            ),
        }
        _write_json(output_root / "per-run-metrics.json", metrics)
        hashes = []
        for path in sorted(output_root.iterdir()):
            if path.is_file() and path.name != "sha256sums.txt":
                hashes.append(f"{_file_sha(path)}  {path.name}")
        (output_root / "sha256sums.txt").write_text("\\n".join(hashes) + "\\n", encoding="utf-8")
        if not metrics["resource_gate"]["within_limits"]:
            raise RuntimeError("Task 11 unit exceeded a frozen resource ceiling")
        return metrics
    finally:
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        runtime.director.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--native-library", type=Path, required=True)
    parser.add_argument("--python-abi-path", type=Path, required=True)
    parser.add_argument("--architecture", choices=("HLA", "HLB"), required=True)
    parser.add_argument("--condition", choices=tuple(CHANNELS), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--run-kind", choices=("preflight", "campaign"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.environ["GFE_CORE_LIB"] = str(args.native_library)
    result = run_unit(
        args.source_root, args.manifest, args.protocol, args.native_library,
        args.python_abi_path, args.architecture, args.condition, args.seed,
        args.output, args.run_kind,
    )
    print(json.dumps({
        "run_key": result["run_key"],
        "status": result["status"],
        "evaluation": {
            "answer_exact_match": result["evaluation"]["answer_exact_match"],
            "forecast_coverage": result["evaluation"]["forecast_coverage"],
            "support_witness_recall": result["evaluation"]["support_witness_recall"],
            "false_witness_rate": result["evaluation"]["false_witness_rate"],
        },
        "resource_gate": result["resource_gate"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
