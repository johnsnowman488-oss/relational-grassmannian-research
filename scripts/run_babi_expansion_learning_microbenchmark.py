#!/usr/bin/env python3
"""Bounded learning-enabled resource microbenchmark for bAbI Tasks 11/14/19.

This is not the frozen 360-unit learning campaign. It executes eight deterministic
fit stories per task per shard with a fresh HLA/HLB adapter for each story,
loads no evaluator labels, and never reads validation or official test inputs.
It measures native event ingestion with learner updates enabled, plus in-memory
LearningRuntime snapshot/restore cost. Persistent cross-story growth and full
campaign orchestration remain outside this microbenchmark.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import gc
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


def _digest(value) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _memories():
    return [SOEMemory(feature_dim=dimension) for dimension in FEATURE_DIMS]


def _kernels(memories):
    return [
        {
            "gamma": bank.decay_rates[::-1].tolist(),
            "w": [0.25] * bank.channel_count,
            "linear_decay": [0.05] * (bank.channel_count * bank.feature_dim),
            "forcing_bias": [0.0] * (bank.channel_count * bank.feature_dim),
        }
        for bank in memories
    ]


def _adapter(architecture: str, native_library, runtime_factory):
    memories = _memories()
    kernels = _kernels(memories)
    if architecture == "HLA":
        return create_hla_adapter(
            native_library, memories, kernels, dt=DT,
            runtime_factory=runtime_factory,
        )
    return create_hlb_adapter(
        native_library, memories, kernels, dt=DT,
        runtime_factory=runtime_factory, capacity=8192,
    )


def _learner_state(adapter) -> dict:
    learning = adapter.learning
    return {
        "level0": learning.level0.snapshot(),
        "relations": learning.relations.snapshot(),
        "event_roles": learning.event_roles.snapshot(),
        "contexts": learning.context_transitions.snapshot(),
        "task": learning.task_outcomes.snapshot(),
        "temporal": learning.temporal_credit.snapshot(),
        "eligibility": learning.eligibility.snapshot(),
    }


def run(source_root: Path, output_root: Path, shard: int,
        python_abi_path: Path, plan_path: Path) -> dict:
    if shard not in range(4):
        raise ValueError("shard must be 0..3")
    sys.path.insert(0, str(python_abi_path))
    import gfe_ctypes

    native_library = gfe_ctypes.load_gfe_library()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    manifest_path = plan_path.parent / plan["manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_sha = manifest["manifest_sha256"]
    output_root.mkdir(parents=True, exist_ok=True)
    tracemalloc.start()
    started = time.perf_counter()
    story_results = []
    task_records = {}
    totals = Counter()

    for task_id, (train_name, _) in TASK_FILES.items():
        stories, labels = parse_expansion_source(
            source_root / train_name, task_id=task_id,
            split="train", include_labels=False,
        )
        if labels:
            raise AssertionError(f"Task {task_id}: evaluator labels crossed the parser boundary")
        fit, _validation = _fit_validation_split(stories, task_id)
        manifest_task = manifest["tasks"][str(task_id)]
        manifest_fit_ids = (
            set(manifest_task["phases"]["warm_start"]["story_ids"])
            | set(manifest_task["phases"]["online_adaptation"]["story_ids"])
        )
        if manifest_fit_ids != {story.story_id for story in fit}:
            raise AssertionError(f"Task {task_id}: source fit partition differs from frozen manifest")
        sample = fit[shard * 8:(shard + 1) * 8]
        if len(sample) != 8:
            raise ValueError(f"Task {task_id}: insufficient fit stories for shard {shard}")
        task_records[str(task_id)] = {
            "fit_story_count": len(fit),
            "sample_story_ids": [story.story_id for story in sample],
        }

        for architecture in ("HLA", "HLB"):
            for story in sample:
                adapter = _adapter(
                    architecture, native_library,
                    gfe_ctypes.create_persistent_hierarchy_runtime,
                )
                runtime = BabiExpansionRuntime(adapter, learning_enabled=True)
                before = _learner_state(adapter)
                before_digest = _digest(before)
                episode_started = time.perf_counter()
                try:
                    outputs = runtime.ingest_story(story)
                    episode_seconds = time.perf_counter() - episode_started
                    if len(outputs) != len(story.events):
                        raise AssertionError(f"{story.story_id}: event-output count mismatch")
                    if any(item.get("abstained") for item in outputs):
                        raise RuntimeError(
                            f"{story.story_id}: capacity/runtime abstention in learning microbenchmark"
                        )
                    native_steps = int(adapter.bridge.runtime.step_count)
                    if native_steps != len(story.events) or adapter.ticks != len(story.events):
                        raise AssertionError(f"{story.story_id}: native/event tick count mismatch")

                    after = _learner_state(adapter)
                    after_digest = _digest(after)
                    changed_components = [
                        name for name in before if before[name] != after[name]
                    ]
                    if not changed_components:
                        raise RuntimeError(
                            f"{story.story_id}/{architecture}: no learner component changed "
                            "under learning_enabled=True"
                        )

                    journal = list(adapter.learning._observation_journal)
                    journal_counts = Counter(
                        row.get("kind", "unknown") for row in journal
                        if row.get("learn") is True
                    )
                    # The checkpoint covers Python learning state and its
                    # provenance-bearing observation journal. It intentionally
                    # does not claim to be an end-to-end native/runtime checkpoint.
                    snapshot_started = time.perf_counter()
                    checkpoint = adapter.learning.snapshot()
                    snapshot_seconds = time.perf_counter() - snapshot_started
                    checkpoint_bytes = len(json.dumps(
                        checkpoint, sort_keys=True, separators=(",", ":"), default=str,
                    ).encode("utf-8"))
                    restore_started = time.perf_counter()
                    adapter.learning.restore(checkpoint, preserve_observations=False)
                    restore_seconds = time.perf_counter() - restore_started
                    restored_digest = _digest(_learner_state(adapter))
                    if restored_digest != after_digest:
                        raise AssertionError(
                            f"{story.story_id}: LearningRuntime checkpoint/restore changed learner state"
                        )

                    row = {
                        "task_id": task_id,
                        "architecture": architecture,
                        "story_id": story.story_id,
                        "events": len(story.events),
                        "native_steps": native_steps,
                        "episode_update_seconds": episode_seconds,
                        "learning_snapshot_seconds": snapshot_seconds,
                        "learning_restore_seconds": restore_seconds,
                        "learning_checkpoint_bytes": checkpoint_bytes,
                        "parameter_state_sha256_before": before_digest,
                        "parameter_state_sha256_after": after_digest,
                        "parameter_state_sha256_after_restore": restored_digest,
                        "changed_learner_components": changed_components,
                        "learned_journal_rows": sum(journal_counts.values()),
                        "learned_journal_kinds": dict(journal_counts),
                        "temporal_credit_weights": len(after["temporal"]["weights"]),
                        "eligibility_records": len(after["eligibility"]["states"]),
                        "labels_loaded": 0,
                        "official_test_queries": 0,
                        "confirmatory_labels_loaded": 0,
                    }
                    story_results.append(row)
                    totals["stories"] += 1
                    totals["events"] += len(story.events)
                    totals["native_steps"] += native_steps
                    totals["journal_rows"] += sum(journal_counts.values())
                    totals["checkpoint_bytes"] += checkpoint_bytes
                    totals["parameter_changed_story_runs"] += 1
                    for component in changed_components:
                        totals[f"component:{component}"] += 1
                finally:
                    runtime.director.close()
                    del runtime, adapter
                    gc.collect()

    elapsed = time.perf_counter() - started
    _, trace_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    if totals["stories"] != 48 or totals["events"] != totals["native_steps"]:
        raise AssertionError(f"shard {shard}: expected 48 stories and matching native steps")
    report = {
        "schema": "HLG-BABI-EXPANSION-LEARNING-COST-MICROBENCHMARK-v1",
        "status": "PASS",
        "shard": shard,
        "native_commit": os.environ.get("GFE_ABERCONICS_COMMIT", NATIVE_COMMIT),
        "manifest_sha256": manifest_sha,
        "learning_enabled": True,
        "sample_policy": (
            "Eight deterministic whole fit stories per task per shard; HLA and HLB; "
            "fresh adapter per story; no validation/test stories or evaluator labels."
        ),
        "scope": (
            "Native HLA/HLB event ingestion with H1 learner updates enabled; "
            "per-episode learner-state delta, learned journal records, eligibility/temporal state, "
            "and Python LearningRuntime snapshot/restore timing and serialized size."
        ),
        "not_measured": [
            "persistent model growth across a long sequence of stories on one learner",
            "candidate validation, consolidation, promotion and rollback orchestration",
            "full 360-unit learning campaign runtime or outcomes",
        ],
        "tasks": task_records,
        "story_runs": story_results,
        "story_count": totals["stories"],
        "event_count": totals["events"],
        "native_step_count": totals["native_steps"],
        "parameter_changed_story_runs": totals["parameter_changed_story_runs"],
        "learned_journal_rows": totals["journal_rows"],
        "changed_component_story_counts": {
            key.split(":", 1)[1]: value
            for key, value in totals.items() if key.startswith("component:")
        },
        "learning_checkpoint_bytes_total": totals["checkpoint_bytes"],
        "learning_updates_enabled": True,
        "labels_loaded": 0,
        "official_test_queries": 0,
        "confirmatory_labels_loaded": 0,
        "elapsed_seconds": elapsed,
        "peak_rss_mb": peak_rss,
        "tracemalloc_peak_mb": trace_peak / (1024.0 * 1024.0),
        "stories_per_second": totals["stories"] / elapsed if elapsed else 0.0,
        "events_per_second": totals["events"] / elapsed if elapsed else 0.0,
    }
    path = output_root / f"learning-cost-microbenchmark-shard-{shard}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["artifact_sha256"] = sha256(path.read_bytes()).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path("data/babi-v1.2-expansion"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/learning-cost-microbenchmark"))
    parser.add_argument("--shard", type=int, choices=range(4), required=True)
    parser.add_argument("--python-abi-path", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        args.source_root, args.output_root, args.shard,
        args.python_abi_path, args.plan,
    )
    print(json.dumps({
        key: value for key, value in result.items() if key != "story_runs"
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
