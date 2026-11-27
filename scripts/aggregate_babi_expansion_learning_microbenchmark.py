#!/usr/bin/env python3
"""Validate and aggregate persistent Task 11 resource-qualification shards."""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean

NATIVE_COMMIT = "2539df6bda7ef3c9dd7c707abe26eff8bdbb59de"
STORIES_PER_SHARD = 32


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def aggregate(plan_path: Path, shard_dirs: list[Path], output_path: Path) -> dict:
    plan = _load(plan_path)
    manifest = _load(plan_path.parent / plan["manifest_path"])
    manifest_sha = manifest["manifest_sha256"]
    if len(shard_dirs) != 4:
        raise ValueError("Task 11 resource aggregation requires exactly four shards")
    task = manifest["tasks"]["11"]
    fit_ids = (set(task["phases"]["warm_start"]["story_ids"])
               | set(task["phases"]["online_adaptation"]["story_ids"]))
    by_arch = defaultdict(list)
    per_shard = []
    all_rows = []
    artifact_bytes = 0

    for shard, root in enumerate(shard_dirs):
        path = root / f"task11-persistent-resource-shard-{shard}.json"
        if not path.is_file():
            raise FileNotFoundError(f"missing Task 11 persistent resource shard {shard}")
        report = _load(path)
        if report.get("status") != "PASS" or report.get("task_id") != 11:
            raise ValueError(f"shard {shard}: Task 11 resource report did not pass")
        if report.get("shard") != shard or report.get("manifest_sha256") != manifest_sha:
            raise ValueError(f"shard {shard}: shard/manifest identity mismatch")
        if report.get("native_commit") != NATIVE_COMMIT:
            raise ValueError(f"shard {shard}: native ABI pin mismatch")
        if report.get("persistent_learner_per_architecture") is not True:
            raise ValueError(f"shard {shard}: learner was not persistent across stories")
        if any(report.get(key) != 0 for key in (
            "labels_loaded", "official_test_queries", "confirmatory_labels_loaded",
        )):
            raise ValueError(f"shard {shard}: evaluator/test labels crossed boundary")
        ids = report.get("sample_story_ids", [])
        if len(ids) != STORIES_PER_SHARD or len(set(ids)) != STORIES_PER_SHARD:
            raise ValueError(f"shard {shard}: expected 32 unique fit stories")
        if not set(ids) <= fit_ids:
            raise ValueError(f"shard {shard}: sample includes a non-fit story")
        rows = report.get("story_runs", [])
        if len(rows) != STORIES_PER_SHARD * 2:
            raise ValueError(f"shard {shard}: expected 64 Task 11 architecture/story rows")
        for architecture in ("HLA", "HLB"):
            arch_rows = [row for row in rows if row.get("architecture") == architecture]
            if len(arch_rows) != STORIES_PER_SHARD:
                raise ValueError(f"shard {shard}/{architecture}: incomplete story rows")
            if {row["story_id"] for row in arch_rows} != set(ids):
                raise ValueError(f"shard {shard}/{architecture}: story IDs mismatch")
            totals = report["per_architecture"][architecture]
            if totals.get("stories") != STORIES_PER_SHARD or totals.get("learner_changed") is not True:
                raise ValueError(f"shard {shard}/{architecture}: persistent learner did not update")
            if totals.get("events", 0) <= 0 or totals.get("final_checkpoint_bytes", 0) <= 0:
                raise ValueError(f"shard {shard}/{architecture}: missing resource measurements")
            for row in arch_rows:
                if row.get("state_sha256_after") != row.get("state_sha256_after_restore"):
                    raise ValueError(f"{row['story_id']}/{architecture}: checkpoint recovery mismatch")
                if any(row.get(key) != 0 for key in (
                    "labels_loaded", "official_test_queries", "confirmatory_labels_loaded",
                )):
                    raise ValueError(f"{row['story_id']}: label isolation failure")
                by_arch[architecture].append(row)
                all_rows.append(row)
        per_shard.append({
            "shard": shard,
            "stories_per_architecture": STORIES_PER_SHARD,
            "events": report["event_count"],
            "elapsed_seconds": report["elapsed_seconds"],
            "peak_rss_mb": report["peak_rss_mb"],
            "tracemalloc_peak_mb": report["tracemalloc_peak_mb"],
            "artifact_bytes": path.stat().st_size,
        })
        artifact_bytes += sum(p.stat().st_size for p in root.rglob("*") if p.is_file())

    if len(all_rows) != 256:
        raise ValueError(f"expected 256 Task 11 story rows, got {len(all_rows)}")
    task_metrics = {}
    for architecture in ("HLA", "HLB"):
        rows = by_arch[architecture]
        ids = [row["story_id"] for row in rows]
        if len(rows) != 128 or len(set(ids)) != 128:
            raise ValueError(f"{architecture}: expected 128 unique paired fit stories")
        for shard in range(4):
            ordered = sorted(
                [row for row in rows if int(row["shard"]) == shard],
                key=lambda row: int(row["story_index"]),
            )
            if len(ordered) != STORIES_PER_SHARD:
                raise ValueError(f"{architecture}/shard {shard}: persistent sequence incomplete")
            journal = [int(row["observation_journal_rows"]) for row in ordered]
            if any(b < a for a, b in zip(journal, journal[1:])):
                raise ValueError(f"{architecture}/shard {shard}: learner journal shrank across stories")
        update = sum(float(row["update_seconds"]) for row in rows)
        events = sum(int(row["events"]) for row in rows)
        task_metrics[architecture] = {
            "persistent_story_runs": len(rows),
            "events": events,
            "mean_update_seconds_per_story": mean(float(row["update_seconds"]) for row in rows),
            "events_per_update_second": events / update if update else 0.0,
            "mean_snapshot_seconds": mean(float(row["snapshot_seconds"]) for row in rows),
            "mean_restore_seconds": mean(float(row["restore_seconds"]) for row in rows),
            "mean_checkpoint_bytes": mean(int(row["checkpoint_bytes"]) for row in rows),
            "max_checkpoint_bytes": max(int(row["checkpoint_bytes"]) for row in rows),
            "final_checkpoint_bytes_max": max(
                int(max(
                    row["checkpoint_bytes"] for row in rows
                    if int(row["shard"]) == shard and int(row["story_index"]) == STORIES_PER_SHARD - 1
                )) for shard in range(4)
            ),
            "max_observation_journal_rows": max(journal),
            "max_temporal_credit_weights": max(int(row["temporal_credit_weights"]) for row in rows),
            "max_eligibility_records": max(int(row["eligibility_records"]) for row in rows),
        }

    result = {
        "schema": "HLG-BABI-TASK11-PERSISTENT-RESOURCE-AGGREGATE-v1",
        "status": "PASS",
        "task_id": 11,
        "native_commit": NATIVE_COMMIT,
        "manifest_sha256": manifest_sha,
        "shards_expected": 4,
        "shards_accepted": len(per_shard),
        "persistent_story_runs_expected": 256,
        "persistent_story_runs_accepted": len(all_rows),
        "stories_per_architecture": 128,
        "architectures": ["HLA", "HLB"],
        "events": sum(int(row["events"]) for row in all_rows),
        "peak_worker_rss_mb_max": max(float(row["peak_rss_mb"]) for row in per_shard),
        "peak_worker_tracemalloc_mb_max": max(float(row["tracemalloc_peak_mb"]) for row in per_shard),
        "worker_elapsed_seconds_sum": sum(float(row["elapsed_seconds"]) for row in per_shard),
        "artifact_storage_bytes": artifact_bytes,
        "no_evaluator_labels_loaded": True,
        "official_test_queries": 0,
        "confirmatory_labels_loaded": 0,
        "per_architecture": task_metrics,
        "per_shard": per_shard,
        "resource_gate": {
            "status": "PASS_TASK11_BOUNDED_PERSISTENT_RESOURCE_QUALIFICATION",
            "measured": [
                "128 successive fit stories per architecture across persistent HLA/HLB learners",
                "per-story learner/native state growth and observation-journal growth",
                "native event update time and throughput",
                "full director/adapter plus native checkpoint size, snapshot and restore time",
                "checkpoint recovery fingerprints after every story",
                "worker peak RSS, Python allocation peak and retained artifact size",
            ],
            "limitations": [
                "This is a bounded resource sample, not a full-campaign runtime guarantee.",
                "No validation, official-test or generated-confirmatory labels were loaded.",
                "No Task 11 antecedent/coreference effectiveness claim is made by this resource test.",
            ],
            "decision": "Task 11 may proceed to its 120-unit learning campaign using this measured bounded resource evidence and the existing accepted no-learning preflight.",
        },
        "execution_authorized": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    output_path.write_text(payload, encoding="utf-8")
    result["aggregate_sha256"] = sha256(output_path.read_bytes()).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--shard-dirs", nargs=4, type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = aggregate(args.plan, args.shard_dirs, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
