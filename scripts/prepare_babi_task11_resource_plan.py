#!/usr/bin/env python3
"""Freeze a Task 11-only persistent-resource sample plan.

Tasks 14 and 19 are intentionally neither parsed nor partitioned here.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from rgm.experiments.babi_expansion_adapters import parse_expansion_source
from rgm.experiments.babi_expansion_preflight import TASK_FILES, _fit_validation_split, _warm_online_split


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def prepare(source_root: Path, output_root: Path) -> dict:
    train_name, _ = TASK_FILES[11]
    stories, labels = parse_expansion_source(
        source_root / train_name, task_id=11, split="train", include_labels=False,
    )
    if labels:
        raise AssertionError("Task 11 evaluator labels crossed the source parser boundary")
    fit, validation = _fit_validation_split(stories, 11)
    warm, online = _warm_online_split(fit, 11)
    fit_ids = [row.story_id for row in fit]
    validation_ids = [row.story_id for row in validation]
    warm_ids = [row.story_id for row in warm]
    online_ids = [row.story_id for row in online]
    if set(fit_ids) & set(validation_ids) or set(warm_ids) & set(online_ids):
        raise AssertionError("Task 11 whole-story partitions overlap")
    if set(warm_ids) | set(online_ids) != set(fit_ids):
        raise AssertionError("Task 11 warm/online partitions do not cover fit stories")

    manifest = {
        "schema": "HLG-BABI-TASK11-PERSISTENT-RESOURCE-MANIFEST-v1",
        "task_id": 11,
        "source_member": train_name,
        "story_count": len(stories),
        "fit_story_count": len(fit),
        "validation_story_count": len(validation),
        "partitions": {
            "fit_story_ids": fit_ids,
            "validation_story_ids": validation_ids,
            "warm_start_story_ids": warm_ids,
            "online_adaptation_story_ids": online_ids,
        },
        "labels_loaded": 0,
        "official_test_queries": 0,
        "confirmatory_labels_loaded": 0,
        "locked_tasks": [14, 19],
        "task3_task5_modified": False,
    }
    manifest["manifest_sha256"] = sha256(_canonical(manifest)).hexdigest()
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "task11-resource-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plan = {
        "schema": "HLG-BABI-TASK11-PERSISTENT-RESOURCE-PLAN-v1",
        "manifest_path": manifest_path.name,
        "manifest_sha256": manifest["manifest_sha256"],
        "task_id": 11,
        "shard_count": 4,
        "stories_per_shard": 32,
        "architectures": ["HLA", "HLB"],
        "sample_story_ids": fit_ids[:128],
    }
    (output_root / "task11-resource-plan.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return {"status": "PASS", **plan, "fit_story_count": len(fit),
            "validation_story_count": len(validation)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source_root, args.output_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
