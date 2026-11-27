import json

import pytest

from scripts.aggregate_babi_expansion_learning_microbenchmark import aggregate


NATIVE_COMMIT = "2539df6bda7ef3c9dd7c707abe26eff8bdbb59de"


def _fixture(tmp_path):
    manifest_sha = "frozen-manifest-sha"
    tasks = {}
    for task_id in (11, 14, 19):
        fit_ids = [f"task{task_id}/fit/story{i:03d}" for i in range(32)]
        tasks[str(task_id)] = {
            "phases": {
                "warm_start": {"story_ids": fit_ids[:16]},
                "online_adaptation": {"story_ids": fit_ids[16:]},
            }
        }
    manifest = {"manifest_sha256": manifest_sha, "tasks": tasks}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    plan = {"manifest_path": "manifest.json"}
    (tmp_path / "preflight-plan.json").write_text(json.dumps(plan), encoding="utf-8")

    shard_dirs = []
    for shard in range(4):
        root = tmp_path / f"shard-{shard}"
        root.mkdir()
        sample_tasks = {}
        story_runs = []
        for task_id in (11, 14, 19):
            ids = tasks[str(task_id)]["phases"]["warm_start"]["story_ids"]
            fit_ids = ids + tasks[str(task_id)]["phases"]["online_adaptation"]["story_ids"]
            sample = fit_ids[shard * 8:(shard + 1) * 8]
            sample_tasks[str(task_id)] = {
                "fit_story_count": 32,
                "sample_story_ids": sample,
            }
            for architecture in ("HLA", "HLB"):
                for story_id in sample:
                    story_runs.append({
                        "task_id": task_id,
                        "architecture": architecture,
                        "story_id": story_id,
                        "events": 5,
                        "native_steps": 5,
                        "episode_update_seconds": 0.02,
                        "learning_snapshot_seconds": 0.001,
                        "learning_restore_seconds": 0.002,
                        "learning_checkpoint_bytes": 4096,
                        "changed_learner_components": ["event_roles", "contexts"],
                        "learned_journal_rows": 7,
                        "temporal_credit_weights": 3,
                        "eligibility_records": 4,
                        "labels_loaded": 0,
                        "official_test_queries": 0,
                        "confirmatory_labels_loaded": 0,
                    })
        report = {
            "status": "PASS",
            "shard": shard,
            "native_commit": NATIVE_COMMIT,
            "manifest_sha256": manifest_sha,
            "learning_enabled": True,
            "labels_loaded": 0,
            "official_test_queries": 0,
            "confirmatory_labels_loaded": 0,
            "story_count": 48,
            "event_count": 240,
            "parameter_changed_story_runs": 48,
            "learned_journal_rows": 336,
            "learning_checkpoint_bytes_total": 48 * 4096,
            "elapsed_seconds": 1.0,
            "peak_rss_mb": 100.0,
            "tracemalloc_peak_mb": 4.0,
            "tasks": sample_tasks,
            "story_runs": story_runs,
        }
        (root / f"learning-cost-microbenchmark-shard-{shard}.json").write_text(
            json.dumps(report), encoding="utf-8",
        )
        shard_dirs.append(root)
    return tmp_path / "preflight-plan.json", shard_dirs


def test_learning_cost_aggregate_requires_exact_sample_and_label_isolation(tmp_path):
    plan, shards = _fixture(tmp_path)
    output = tmp_path / "aggregate.json"
    result = aggregate(plan, shards, output)
    assert result["status"] == "PASS"
    assert result["story_runs_expected"] == result["story_runs_accepted"] == 192
    assert result["learner_changed_story_runs"] == 192
    assert result["official_test_queries"] == 0
    assert result["execution_authorized"] is False
    assert result["resource_gate"]["status"] == "PARTIAL_BOUNDED_LEARNING_MICROBENCHMARK"
    assert result["per_task_architecture"]["task11-HLA"]["story_runs"] == 32


def test_learning_cost_aggregate_rejects_mixed_manifest_shards(tmp_path):
    plan, shards = _fixture(tmp_path)
    path = shards[2] / "learning-cost-microbenchmark-shard-2.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["manifest_sha256"] = "wrong-manifest"
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest fingerprint mismatch"):
        aggregate(plan, shards, tmp_path / "aggregate.json")
