#!/usr/bin/env python3
"""Aggregate the bounded learning-cost microbenchmark without campaign claims."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def aggregate(plan_path: Path, shard_dirs: list[Path], output_path: Path) -> dict:
    plan = _load(plan_path)
    manifest = _load(plan_path.parent / plan["manifest_path"])
    manifest_sha = manifest["manifest_sha256"]
    if len(shard_dirs) != 4:
        raise ValueError("learning microbenchmark aggregation requires exactly four shard artifacts")

    fit_ids = {
        int(task_id): (
            set(task["phases"]["warm_start"]["story_ids"])
            | set(task["phases"]["online_adaptation"]["story_ids"])
        )
        for task_id, task in manifest["tasks"].items()
    }
    rows_by_key = {}
    per_shard = []
    all_story_runs = []
    artifact_bytes = 0
    for expected_shard, root in enumerate(shard_dirs):
        report_path = root / f"learning-cost-microbenchmark-shard-{expected_shard}.json"
        if not report_path.is_file():
            raise FileNotFoundError(f"missing learning microbenchmark shard {expected_shard}")
        report = _load(report_path)
        if report.get("status") != "PASS" or report.get("learning_enabled") is not True:
            raise ValueError(f"shard {expected_shard}: learning microbenchmark did not pass")
        if int(report.get("shard", -1)) != expected_shard:
            raise ValueError(f"shard {expected_shard}: shard ID mismatch")
        if report.get("native_commit") != "2539df6bda7ef3c9dd7c707abe26eff8bdbb59de":
            raise ValueError(f"shard {expected_shard}: native ABI pin mismatch")
        if report.get("labels_loaded") != 0 or report.get("official_test_queries") != 0:
            raise ValueError(f"shard {expected_shard}: evaluator/test labels crossed boundary")
        if report.get("confirmatory_labels_loaded") != 0:
            raise ValueError(f"shard {expected_shard}: confirmatory labels crossed boundary")
        story_runs = report.get("story_runs", [])
        if len(story_runs) != 48 or int(report.get("story_count", 0)) != 48:
            raise ValueError(f"shard {expected_shard}: expected exactly 48 story runs")
        for row in story_runs:
            task_id = int(row["task_id"])
            architecture = str(row["architecture"])
            story_id = str(row["story_id"])
            if task_id not in fit_ids or story_id not in fit_ids[task_id]:
                raise ValueError(f"shard {expected_shard}: story is not in the frozen fit partition")
            if architecture not in {"HLA", "HLB"}:
                raise ValueError(f"shard {expected_shard}: unknown architecture")
            if int(row["events"]) != int(row["native_steps"]):
                raise ValueError(f"{story_id}: native steps do not match source event count")
            if not row.get("changed_learner_components"):
                raise ValueError(f"{story_id}/{architecture}: no learner component change recorded")
            if int(row.get("labels_loaded", -1)) != 0 or int(row.get("official_test_queries", -1)) != 0:
                raise ValueError(f"{story_id}: label/test leakage")
            key = (task_id, architecture, story_id)
            if key in rows_by_key:
                raise ValueError(f"duplicate learning microbenchmark story key: {key}")
            rows_by_key[key] = row
            all_story_runs.append(row)
        per_shard.append({
            "shard": expected_shard,
            "stories": report["story_count"],
            "events": report["event_count"],
            "elapsed_seconds": report["elapsed_seconds"],
            "peak_rss_mb": report["peak_rss_mb"],
            "tracemalloc_peak_mb": report["tracemalloc_peak_mb"],
            "parameter_changed_story_runs": report["parameter_changed_story_runs"],
            "learned_journal_rows": report["learned_journal_rows"],
            "learning_checkpoint_bytes_total": report["learning_checkpoint_bytes_total"],
        })
        artifact_bytes += sum(
            file.stat().st_size for file in root.rglob("*") if file.is_file()
        )

    expected_keys = {
        (task_id, architecture, story_id)
        for task_id, story_ids in fit_ids.items()
        for architecture in ("HLA", "HLB")
        for story_id in sorted(story_ids)[:0]
    }
    # The native no-learning sample and learning microbenchmark use the same
    # deterministic eight-fit-story slice within each of the four shards.
    # Validate complete task/architecture coverage and matching sample IDs.
    by_task_arch: dict[tuple[int, str], set[str]] = defaultdict(set)
    for task_id, architecture, story_id in rows_by_key:
        by_task_arch[(task_id, architecture)].add(story_id)
    if len(rows_by_key) != 192:
        raise ValueError(f"expected 192 unique task/architecture/story rows, got {len(rows_by_key)}")
    for task_id in (11, 14, 19):
        hla = by_task_arch[(task_id, "HLA")]
        hlb = by_task_arch[(task_id, "HLB")]
        if len(hla) != 32 or hla != hlb:
            raise ValueError(f"Task {task_id}: expected the same 32 fit stories for HLA and HLB")

    grouped: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for row in all_story_runs:
        grouped[(int(row["task_id"]), str(row["architecture"]))].append(row)
    task_arch_metrics = {}
    for (task_id, architecture), rows in sorted(grouped.items()):
        events = sum(int(row["events"]) for row in rows)
        update_time = sum(float(row["episode_update_seconds"]) for row in rows)
        snapshot_time = sum(float(row["learning_snapshot_seconds"]) for row in rows)
        restore_time = sum(float(row["learning_restore_seconds"]) for row in rows)
        task_arch_metrics[f"task{task_id}-{architecture}"] = {
            "story_runs": len(rows),
            "event_count": events,
            "native_steps": sum(int(row["native_steps"]) for row in rows),
            "learner_changed_story_runs": sum(bool(row["changed_learner_components"]) for row in rows),
            "mean_episode_update_seconds": mean(float(row["episode_update_seconds"]) for row in rows),
            "events_per_update_second": events / update_time if update_time else 0.0,
            "mean_learning_snapshot_seconds": mean(float(row["learning_snapshot_seconds"]) for row in rows),
            "mean_learning_restore_seconds": mean(float(row["learning_restore_seconds"]) for row in rows),
            "mean_learning_checkpoint_bytes": mean(int(row["learning_checkpoint_bytes"]) for row in rows),
            "mean_learned_journal_rows": mean(int(row["learned_journal_rows"]) for row in rows),
            "max_temporal_credit_weights": max(int(row["temporal_credit_weights"]) for row in rows),
            "max_eligibility_records": max(int(row["eligibility_records"]) for row in rows),
        }

    total_events = sum(int(row["events"]) for row in all_story_runs)
    total_update_seconds = sum(float(row["episode_update_seconds"]) for row in all_story_runs)
    total_snapshot_seconds = sum(float(row["learning_snapshot_seconds"]) for row in all_story_runs)
    total_restore_seconds = sum(float(row["learning_restore_seconds"]) for row in all_story_runs)
    result = {
        "schema": "HLG-BABI-EXPANSION-LEARNING-COST-AGGREGATE-v1",
        "status": "PASS",
        "native_commit": "2539df6bda7ef3c9dd7c707abe26eff8bdbb59de",
        "learning_enabled": True,
        "story_runs_expected": 192,
        "story_runs_accepted": len(all_story_runs),
        "stories_per_task_architecture": 32,
        "tasks": [11, 14, 19],
        "architectures": ["HLA", "HLB"],
        "event_count": total_events,
        "native_steps": sum(int(row["native_steps"]) for row in all_story_runs),
        "learner_changed_story_runs": sum(bool(row["changed_learner_components"]) for row in all_story_runs),
        "learned_journal_rows": sum(int(row["learned_journal_rows"]) for row in all_story_runs),
        "update_seconds_total": total_update_seconds,
        "snapshot_seconds_total": total_snapshot_seconds,
        "restore_seconds_total": total_restore_seconds,
        "measured_events_per_update_second": total_events / total_update_seconds if total_update_seconds else 0.0,
        "checkpoint_bytes_total": sum(int(row["learning_checkpoint_bytes"]) for row in all_story_runs),
        "peak_worker_rss_mb_max": max(float(row["peak_rss_mb"]) for row in per_shard),
        "peak_worker_tracemalloc_mb_max": max(float(row["tracemalloc_peak_mb"]) for row in per_shard),
        "worker_elapsed_seconds_sum": sum(float(row["elapsed_seconds"]) for row in per_shard),
        "worker_elapsed_seconds_max": max(float(row["elapsed_seconds"]) for row in per_shard),
        "microbenchmark_artifact_storage_bytes": artifact_bytes,
        "no_evaluator_labels_loaded": True,
        "official_test_queries": 0,
        "confirmatory_labels_loaded": 0,
        "per_task_architecture": task_arch_metrics,
        "per_shard": per_shard,
        "resource_gate": {
            "status": "PARTIAL_BOUNDED_LEARNING_MICROBENCHMARK",
            "measured": [
                "native HLA/HLB event ingestion with learner updates enabled",
                "per-story changed learner components and learning-journal row counts",
                "per-task/architecture update time and event-normalized throughput",
                "in-memory LearningRuntime snapshot/restore time and checkpoint payload bytes",
                "per-worker RSS, Python allocation peak and artifact storage",
            ],
            "not_measured": [
                "persistent learner-state growth across a long multi-story campaign on one model",
                "full candidate evaluation, consolidation, promotion and rollback orchestration",
                "full 360-unit campaign resource use or learning performance/generalisation",
            ],
            "decision": "The bounded sample informs a measured learner-update cost estimate but does not authorize the full campaign."
        },
        "execution_authorized": False,
    }
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
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
    print(json.dumps({
        key: value for key, value in result.items()
        if key not in {"per_task_architecture", "per_shard"}
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
