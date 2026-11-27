#!/usr/bin/env python3
"""Persistent-state Task 11 resource qualification for HLA and HLB.

Each shard creates one adapter per architecture and processes 32 successive
whole fit stories through that same learner/native runtime. No validation,
official-test, or confirmatory labels are loaded. This is a bounded resource
qualification, not a learning-effectiveness result.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import sys
import time
import tracemalloc

from rgm.experiments.babi_expansion_adapters import parse_expansion_source
from rgm.experiments.babi_expansion_preflight import TASK_FILES, _fit_validation_split
from rgm.experiments.babi_expansion_runtime import BabiExpansionRuntime
from rgm.leptograph.m4.hierarchical import create_hla_adapter, create_hlb_adapter
from rgm.memory import SOEMemory

DT = 0.01
FEATURE_DIMS = (3, 3, 3)
NATIVE_COMMIT = "2539df6bda7ef3c9dd7c707abe26eff8bdbb59de"
STORIES_PER_SHARD = 32


def _digest(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _memories():
    return [SOEMemory(feature_dim=dimension) for dimension in FEATURE_DIMS]


def _kernels(memories):
    return [{
        "gamma": bank.decay_rates[::-1].tolist(),
        "w": [0.25] * bank.channel_count,
        "linear_decay": [0.05] * (bank.channel_count * bank.feature_dim),
        "forcing_bias": [0.0] * (bank.channel_count * bank.feature_dim),
    } for bank in memories]


def _adapter(architecture: str, native_library, runtime_factory):
    memories = _memories()
    kernels = _kernels(memories)
    if architecture == "HLA":
        return create_hla_adapter(native_library, memories, kernels, dt=DT,
                                  runtime_factory=runtime_factory)
    return create_hlb_adapter(native_library, memories, kernels, dt=DT,
                              runtime_factory=runtime_factory, capacity=8192)


def _checkpoint(adapter, director):
    # Capture both the full H1 director/adapter state and the native runtime.
    return {
        "director": director.snapshot(),
        "native": adapter.bridge.runtime.checkpoint(),
    }


def _restore(adapter, director, checkpoint):
    adapter.bridge.runtime.restore(checkpoint["native"])
    director.restore(checkpoint["director"], preserve_observations=False)


def _state_counts(adapter):
    learning = adapter.learning
    return {
        "observation_journal_rows": len(learning._observation_journal),
        "relation_rows": len([r for r in learning._observation_journal if r.get("kind") == "relation"]),
        "event_role_rows": len([r for r in learning._observation_journal if r.get("kind") == "event_role"]),
        "context_rows": len([r for r in learning._observation_journal if r.get("kind") == "context"]),
        "temporal_credit_weights": len(learning.temporal_credit.weights),
        "eligibility_records": len(learning.eligibility._states),
    }


def run(source_root: Path, output_root: Path, shard: int,
        python_abi_path: Path, plan_path: Path) -> dict:
    if shard not in range(4):
        raise ValueError("shard must be 0..3")
    sys.path.insert(0, str(python_abi_path))
    import gfe_ctypes

    native_library = gfe_ctypes.load_gfe_library()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    manifest = json.loads((plan_path.parent / plan["manifest_path"]).read_text(encoding="utf-8"))
    manifest_sha = manifest["manifest_sha256"]
    train_name, _ = TASK_FILES[11]
    stories, labels = parse_expansion_source(
        source_root / train_name, task_id=11, split="train", include_labels=False,
    )
    if labels:
        raise AssertionError("Task 11 evaluator labels crossed the parser boundary")
    fit, _validation = _fit_validation_split(stories, 11)
    manifest_fit_ids = set(manifest["partitions"]["fit_story_ids"])
    if manifest_fit_ids != {story.story_id for story in fit}:
        raise AssertionError("Task 11 source fit partition differs from frozen manifest")
    sample = fit[shard * STORIES_PER_SHARD:(shard + 1) * STORIES_PER_SHARD]
    if len(sample) != STORIES_PER_SHARD:
        raise ValueError(f"Task 11 shard {shard}: expected {STORIES_PER_SHARD} fit stories")

    output_root.mkdir(parents=True, exist_ok=True)
    tracemalloc.start()
    worker_started = time.perf_counter()
    story_results = []
    architecture_totals = {}
    for architecture in ("HLA", "HLB"):
        adapter = _adapter(architecture, native_library,
                           gfe_ctypes.create_persistent_hierarchy_runtime)
        runtime = BabiExpansionRuntime(adapter, learning_enabled=True)
        rows = []
        events_total = 0
        update_seconds_total = 0.0
        snapshot_seconds_total = 0.0
        restore_seconds_total = 0.0
        try:
            for story_index, story in enumerate(sample):
                before = _checkpoint(adapter, runtime.director)
                before_digest = _digest(before)
                started = time.perf_counter()
                outputs = runtime.ingest_story_sequence([story])
                update_seconds = time.perf_counter() - started
                if len(outputs) != len(story.events) or any(row.get("abstained") for row in outputs):
                    raise RuntimeError(f"{story.story_id}/{architecture}: incomplete or abstained ingestion")
                if runtime.director.event_tick != events_total + len(story.events):
                    raise AssertionError(f"{story.story_id}: persistent native tick mismatch")
                events_total += len(story.events)

                after = _checkpoint(adapter, runtime.director)
                after_digest = _digest(after)
                if before_digest == after_digest:
                    raise RuntimeError(f"{story.story_id}/{architecture}: learner/runtime state did not change")

                snapshot_started = time.perf_counter()
                checkpoint = _checkpoint(adapter, runtime.director)
                snapshot_seconds = time.perf_counter() - snapshot_started
                checkpoint_bytes = len(json.dumps(
                    checkpoint, sort_keys=True, separators=(",", ":"), default=str,
                ).encode("utf-8"))
                restore_started = time.perf_counter()
                _restore(adapter, runtime.director, checkpoint)
                restore_seconds = time.perf_counter() - restore_started
                restored_digest = _digest(_checkpoint(adapter, runtime.director))
                if restored_digest != after_digest:
                    raise AssertionError(f"{story.story_id}: full checkpoint recovery mismatch")

                counts = _state_counts(adapter)
                row = {
                    "task_id": 11,
                    "shard": shard,
                    "architecture": architecture,
                    "story_id": story.story_id,
                    "story_index": story_index,
                    "events": len(story.events),
                    "native_tick_after_story": runtime.director.event_tick,
                    "update_seconds": update_seconds,
                    "snapshot_seconds": snapshot_seconds,
                    "restore_seconds": restore_seconds,
                    "checkpoint_bytes": checkpoint_bytes,
                    "state_sha256_before": before_digest,
                    "state_sha256_after": after_digest,
                    "state_sha256_after_restore": restored_digest,
                    **counts,
                    "labels_loaded": 0,
                    "official_test_queries": 0,
                    "confirmatory_labels_loaded": 0,
                }
                rows.append(row)
                story_results.append(row)
                update_seconds_total += update_seconds
                snapshot_seconds_total += snapshot_seconds
                restore_seconds_total += restore_seconds
            final_state = _checkpoint(adapter, runtime.director)
            architecture_totals[architecture] = {
                "stories": len(rows),
                "events": events_total,
                "update_seconds": update_seconds_total,
                "snapshot_seconds": snapshot_seconds_total,
                "restore_seconds": restore_seconds_total,
                "final_state_sha256": _digest(final_state),
                "final_checkpoint_bytes": len(json.dumps(
                    final_state, sort_keys=True, separators=(",", ":"), default=str,
                ).encode("utf-8")),
                "final_state_counts": _state_counts(adapter),
                "learner_changed": any(
                    row["state_sha256_before"] != row["state_sha256_after"] for row in rows
                ),
            }
        finally:
            runtime.director.close()

    elapsed = time.perf_counter() - worker_started
    _, trace_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    if len(story_results) != 2 * STORIES_PER_SHARD:
        raise AssertionError("Task 11 resource sample has incomplete architecture coverage")
    report = {
        "schema": "HLG-BABI-TASK11-PERSISTENT-RESOURCE-v1",
        "status": "PASS",
        "task_id": 11,
        "shard": shard,
        "native_commit": os.environ.get("GFE_ABERCONICS_COMMIT", NATIVE_COMMIT),
        "manifest_sha256": manifest_sha,
        "sample_story_ids": [story.story_id for story in sample],
        "stories_per_architecture": STORIES_PER_SHARD,
        "persistent_learner_per_architecture": True,
        "story_runs": story_results,
        "per_architecture": architecture_totals,
        "story_count": len(story_results),
        "event_count": sum(row["events"] for row in story_results),
        "learning_enabled": True,
        "labels_loaded": 0,
        "official_test_queries": 0,
        "confirmatory_labels_loaded": 0,
        "elapsed_seconds": elapsed,
        "peak_rss_mb": peak_rss,
        "tracemalloc_peak_mb": trace_peak / (1024.0 * 1024.0),
        "artifact_bytes": 0,
        "claim_boundary": (
            "Bounded persistent-state resource qualification only; no learning-effectiveness, "
            "coreference-generalisation or official-test claim."
        ),
    }
    path = output_root / f"task11-persistent-resource-shard-{shard}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["artifact_sha256"] = sha256(path.read_bytes()).hexdigest()
    report["artifact_bytes"] = path.stat().st_size
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path("data/babi-v1.2-expansion"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/task11-resource"))
    parser.add_argument("--shard", type=int, choices=range(4), required=True)
    parser.add_argument("--python-abi-path", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.source_root, args.output_root, args.shard, args.python_abi_path, args.plan)
    print(json.dumps({key: value for key, value in report.items() if key != "story_runs"},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
