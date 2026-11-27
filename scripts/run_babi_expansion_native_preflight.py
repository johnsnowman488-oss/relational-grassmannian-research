"""Measure the pinned native HLA/HLB runtime in explicit no-learning mode.

The script uses only raw fit-story observations. It never loads GoldLabel rows,
never enters validation or official test, and asserts that learner parameters
remain byte-identical before and after each story episode.
"""
from __future__ import annotations

import argparse
import gc
from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import sys
import time
import tracemalloc

from rgm.experiments.babi_expansion_adapters import parse_expansion_source
from rgm.experiments.babi_expansion_preflight import (
    TASK_FILES, _fit_validation_split,
)
from rgm.experiments.babi_expansion_runtime import BabiExpansionRuntime
from rgm.leptograph.m4.hierarchical import create_hla_adapter, create_hlb_adapter
from rgm.memory import SOEMemory


DT = 0.01
FEATURE_DIMS = (3, 3, 3)
NATIVE_COMMIT = "2539df6bda7ef3c9dd7c707abe26eff8bdbb59de"


def _sha(value: bytes) -> str:
    return sha256(value).hexdigest()


def _json_fingerprint(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return _sha(payload)


def _learner_parameter_state(adapter) -> dict:
    learning = adapter.learning
    return {
        "level0": learning.level0.snapshot(),
        "relations": learning.relations.snapshot(),
        "event_roles": learning.event_roles.snapshot(),
        "contexts": learning.context_transitions.snapshot(),
        "task": learning.task_outcomes.snapshot(),
        "temporal": learning.temporal_credit.snapshot(),
    }


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


def run(source_root: Path, output_root: Path, shard: int, python_abi_path: Path) -> dict:
    if shard not in range(4):
        raise ValueError("shard must be 0..3")
    sys.path.insert(0, str(python_abi_path))
    import gfe_ctypes  # provided by the pinned Aberconics Python ABI checkout

    native_library = gfe_ctypes.load_gfe_library()
    output_root.mkdir(parents=True, exist_ok=True)
    tracemalloc.start()
    started = time.perf_counter()
    story_results = []
    total_events = total_stories = total_native_steps = 0
    task_records = {}

    for task_id, (train_name, _) in TASK_FILES.items():
        stories, labels = parse_expansion_source(
            source_root / train_name, task_id=task_id,
            split="train", include_labels=False,
        )
        if labels:
            raise AssertionError(f"Task {task_id}: no evaluator labels are permitted in native preflight")
        fit, _validation = _fit_validation_split(stories, task_id)
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
                runtime = BabiExpansionRuntime(adapter, learning_enabled=False)
                before = _learner_parameter_state(adapter)
                before_fingerprint = _json_fingerprint(before)
                story_started = time.perf_counter()
                try:
                    outputs = runtime.ingest_story(story)
                    story_elapsed = time.perf_counter() - story_started
                    if len(outputs) != len(story.events):
                        raise AssertionError(f"{story.story_id}: event-output count mismatch")
                    if any(item.get("abstained") for item in outputs):
                        raise RuntimeError(f"{story.story_id}: capacity/runtime abstention in preflight")
                    after = _learner_parameter_state(adapter)
                    after_fingerprint = _json_fingerprint(after)
                    if before_fingerprint != after_fingerprint:
                        raise AssertionError(
                            f"{story.story_id}: learner parameters changed while learn=False"
                        )
                    learn_true_rows = [
                        row for row in adapter.learning._observation_journal
                        if row.get("learn") is True
                    ]
                    if learn_true_rows:
                        raise AssertionError(f"{story.story_id}: learning-enabled observation recorded")
                    # The pinned PersistentHierarchyRuntime exposes the
                    # committed count as a property; get_state() contains only
                    # level state, kernels and spectral units.
                    native_steps = int(adapter.bridge.runtime.step_count)
                    if native_steps != len(story.events):
                        raise AssertionError(
                            f"{story.story_id}: expected {len(story.events)} native steps, got {native_steps}"
                        )
                    if adapter.ticks != len(story.events):
                        raise AssertionError(f"{story.story_id}: adapter tick/event mismatch")
                    story_results.append({
                        "task_id": task_id,
                        "architecture": architecture,
                        "story_id": story.story_id,
                        "events": len(story.events),
                        "native_steps": native_steps,
                        "elapsed_seconds": story_elapsed,
                        "learner_parameters_unchanged": True,
                        "learning_updates": 0,
                        "labels_loaded": 0,
                    })
                    total_stories += 1
                    total_events += len(story.events)
                    total_native_steps += native_steps
                finally:
                    runtime.director.close()
                    del runtime, adapter
                    gc.collect()

    elapsed = time.perf_counter() - started
    _, trace_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    report = {
        "schema": "HLG-BABI-EXPANSION-NATIVE-NONLEARNING-PREFLIGHT-v1",
        "status": "PASS",
        "shard": shard,
        "native_commit": os.environ.get("GFE_ABERCONICS_COMMIT", NATIVE_COMMIT),
        "source_root": str(source_root),
        "sample_policy": "Eight deterministic fit stories per task per shard; both HLA and HLB; no validation/test stories and no GoldLabel loading.",
        "tasks": task_records,
        "story_runs": story_results,
        "story_count": total_stories,
        "event_count": total_events,
        "native_step_count": total_native_steps,
        "learning_updates": 0,
        "labels_loaded": 0,
        "elapsed_seconds": elapsed,
        "stories_per_second": total_stories / elapsed if elapsed else 0.0,
        "native_steps_per_second": total_native_steps / elapsed if elapsed else 0.0,
        "peak_rss_mb": peak_rss,
        "tracemalloc_peak_mb": trace_peak / (1024.0 * 1024.0),
        "measurement_scope": "Actual pinned native HLA/HLB SOE hierarchy, observation/evidence ingestion and non-learning prediction lifecycle; excludes parameter learning and full 360-unit campaign compute.",
    }
    path = output_root / "native-runtime-usage.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["artifact_sha256"] = _sha(path.read_bytes())
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path("data/babi-v1.2-expansion"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/shards/native-preflight"))
    parser.add_argument("--shard", type=int, choices=range(4), required=True)
    parser.add_argument("--python-abi-path", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source_root, args.output_root, args.shard, args.python_abi_path)
    print(json.dumps({k: v for k, v in result.items() if k != "story_runs"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
