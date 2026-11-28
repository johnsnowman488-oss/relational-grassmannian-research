#!/usr/bin/env python3
"""Prepare a Task 11-only 120-unit whole-story campaign manifest."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from rgm.experiments.babi_expansion_adapters import parse_expansion_source
from rgm.experiments.babi_expansion_preflight import _fit_validation_split


TASK11_TRAIN = "qa11_basic-coreference_train.txt"
ARCHITECTURES = ("HLA", "HLB")
CONDITIONS = (
    "full_learning", "no_temporal", "no_relational",
    "no_abstraction", "no_task", "no_learning",
)
SEEDS = tuple(range(953100, 953110))
RESERVED_PREFLIGHT_SEED = 953099
WORKERS = 4
WARM_FRACTION = 0.80
FIT_VALIDATION_SEED = "HLG-BABI-EXPANSION-TRAIN-VALID-v1"
WARM_ONLINE_SEED = "HLG-BABI-TASK11-WARM-ONLINE-v1"


def _sha_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _phase(stories) -> dict:
    story_ids = [story.story_id for story in stories]
    query_ids = [query.query_id for story in stories for query in story.queries]
    return {
        "story_ids": story_ids,
        "query_ids": query_ids,
        "story_count": len(stories),
        "query_count": len(query_ids),
        "event_count": sum(len(story.events) for story in stories),
        "story_ids_sha256": _sha_bytes("\n".join(story_ids).encode()),
        "query_ids_sha256": _sha_bytes("\n".join(query_ids).encode()),
    }


def seeded_warm_online_split(fit_stories, seed: int):
    ranked = sorted(
        fit_stories,
        key=lambda story: sha256(
            f"{WARM_ONLINE_SEED}:{seed}:11:{story.story_id}".encode()
        ).digest(),
    )
    warm_count = int(len(fit_stories) * WARM_FRACTION + 0.5)
    warm_ids = {story.story_id for story in ranked[:warm_count]}
    warm = [story for story in fit_stories if story.story_id in warm_ids]
    online = [story for story in fit_stories if story.story_id not in warm_ids]
    if not warm or not online or set(warm_ids) & {s.story_id for s in online}:
        raise AssertionError("invalid Task 11 seed-specific whole-story split")
    if {s.story_id for s in warm} | {s.story_id for s in online} != {
        s.story_id for s in fit_stories
    }:
        raise AssertionError("warm/online split does not cover fit stories")
    return warm, online


def build_manifest(source_root: Path, protocol_path: Path, output_root: Path) -> dict:
    source_path = source_root / TASK11_TRAIN
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("schema") not in {
        "HLG-BABI-TASK11-LEARNING-CAMPAIGN-v1.0",
        "HLG-BABI-TASK11-LEARNING-CAMPAIGN-v1.1",
    }:
        raise ValueError("unsupported Task 11 campaign protocol")
    if protocol.get("scope", {}).get("tasks") != [11]:
        raise ValueError("campaign protocol must contain Task 11 only")

    stories, labels = parse_expansion_source(
        source_path, task_id=11, split="train", include_labels=False,
    )
    if labels:
        raise AssertionError("fit/validation observations parser returned evaluator labels")
    fit, validation = _fit_validation_split(stories, 11)
    counts = {
        "training_stories": len(stories),
        "training_queries": sum(len(s.queries) for s in stories),
        "fit_stories": len(fit),
        "fit_queries": sum(len(s.queries) for s in fit),
        "validation_stories": len(validation),
        "validation_queries": sum(len(s.queries) for s in validation),
    }
    expected = {
        "training_stories": 2000, "training_queries": 10000,
        "fit_stories": 1800, "fit_queries": 9000,
        "validation_stories": 200, "validation_queries": 1000,
    }
    if counts != expected:
        raise ValueError(f"Task 11 source counts differ from frozen protocol: {counts}")

    fit_ids = {s.story_id for s in fit}
    validation_ids = {s.story_id for s in validation}
    if fit_ids & validation_ids or fit_ids | validation_ids != {s.story_id for s in stories}:
        raise AssertionError("Task 11 fit/validation partition overlap or omission")

    seed_partitions = {}
    for seed in (*SEEDS, RESERVED_PREFLIGHT_SEED):
        warm, online = seeded_warm_online_split(fit, seed)
        warm_ids, online_ids = {s.story_id for s in warm}, {s.story_id for s in online}
        if warm_ids & online_ids or warm_ids | online_ids != fit_ids:
            raise AssertionError(f"seed {seed}: nested partition is not disjoint and complete")
        seed_partitions[str(seed)] = {
            "warm_start": _phase(warm),
            "online_adaptation": _phase(online),
            "partition_seed": f"{WARM_ONLINE_SEED}:{seed}",
        }

    run_units = []
    for architecture in ARCHITECTURES:
        for condition in CONDITIONS:
            for seed in SEEDS:
                index = len(run_units)
                run_units.append({
                    "index": index,
                    "run_unit_key": f"task11-{architecture}-{condition}-seed{seed}",
                    "task_id": 11,
                    "architecture": architecture,
                    "condition": condition,
                    "seed": seed,
                    "shard": index % WORKERS,
                })
    if len(run_units) != 120 or [sum(u["shard"] == n for u in run_units) for n in range(WORKERS)] != [30] * 4:
        raise AssertionError("Task 11 campaign must contain 120 units, 30 per shard")

    output_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "HLG-BABI-TASK11-CAMPAIGN-MANIFEST-v1",
        "protocol_sha256": _sha_file(protocol_path),
        "source": {
            "member": TASK11_TRAIN,
            "sha256": _sha_file(source_path),
            "official_test_member_loaded": False,
        },
        "split_seeds": {
            "fit_validation": FIT_VALIDATION_SEED,
            "warm_online_prefix": WARM_ONLINE_SEED,
        },
        "counts": counts,
        "fit": _phase(fit),
        "validation": _phase(validation),
        "seed_partitions": seed_partitions,
        "run_units": run_units,
        "worker_count": WORKERS,
        "units_per_shard": 30,
        "official_test_queries_loaded": 0,
        "confirmatory_labels_loaded": 0,
        "learner_labels_loaded": 0,
        "validation_labels_are_evaluator_only": True,
        "native_commit": "48228f8c326c0e8546855eb898d374453d705b77",
        "soe_feature_dims": [3, 3, 3],
        "soe_dt": 0.01,
        "top_down_gain": 1.0,
        "hlb_model_relation_capacity": 262144,
        "eligibility_capacity": 131072,
    }
    manifest["manifest_sha256"] = _sha_bytes(_canonical(manifest))
    path = output_root / "task11-campaign-manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["manifest_file_sha256"] = _sha_file(path)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = build_manifest(args.source_root, args.protocol, args.output_root)
    print(json.dumps({
        "status": "PASS",
        "manifest_sha256": result["manifest_sha256"],
        "counts": result["counts"],
        "run_units": len(result["run_units"]),
        "units_per_shard": result["units_per_shard"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
