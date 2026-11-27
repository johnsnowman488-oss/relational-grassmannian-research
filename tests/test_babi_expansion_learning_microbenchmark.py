import json

import pytest

from scripts.aggregate_babi_expansion_learning_microbenchmark import aggregate


def _fixture(tmp_path):
    task_ids = [f"task11/train/story{i:06d}" for i in range(128)]
    manifest = {
        "manifest_sha256": "a" * 64,
        "partitions": {"fit_story_ids": task_ids},
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    plan = {"manifest_path": "manifest.json"}
    plan_path = tmp_path / "preflight-plan.json"
    plan_path.write_text(json.dumps(plan))
    shard_dirs = []
    for shard in range(4):
        root = tmp_path / f"shard-{shard}"
        root.mkdir()
        ids = task_ids[shard * 32:(shard + 1) * 32]
        rows = []
        per_arch = {}
        for arch in ("HLA", "HLB"):
            for index, story_id in enumerate(ids):
                rows.append({
                    "task_id": 11, "shard": shard, "architecture": arch,
                    "story_id": story_id, "story_index": index, "events": 4,
                    "update_seconds": 0.02, "snapshot_seconds": 0.001,
                    "restore_seconds": 0.002, "checkpoint_bytes": 8192 + index,
                    "state_sha256_after": f"{shard}{arch}{index}",
                    "state_sha256_after_restore": f"{shard}{arch}{index}",
                    "observation_journal_rows": (index + 1) * 4,
                    "temporal_credit_weights": index + 1,
                    "eligibility_records": index + 1,
                    "labels_loaded": 0, "official_test_queries": 0,
                    "confirmatory_labels_loaded": 0,
                })
            per_arch[arch] = {
                "stories": 32, "events": 128, "learner_changed": True,
                "final_checkpoint_bytes": 8192 + 31,
            }
        report = {
            "status": "PASS", "task_id": 11, "shard": shard,
            "native_commit": "2539df6bda7ef3c9dd7c707abe26eff8bdbb59de",
            "manifest_sha256": "a" * 64,
            "persistent_learner_per_architecture": True,
            "sample_story_ids": ids, "story_runs": rows,
            "per_architecture": per_arch, "event_count": 256,
            "elapsed_seconds": 1.0, "peak_rss_mb": 100.0,
            "tracemalloc_peak_mb": 4.0, "labels_loaded": 0,
            "official_test_queries": 0, "confirmatory_labels_loaded": 0,
        }
        (root / f"task11-persistent-resource-shard-{shard}.json").write_text(
            json.dumps(report)
        )
        shard_dirs.append(root)
    return plan_path, shard_dirs


def test_task11_persistent_resource_aggregate_accepts_complete_label_sealed_sample(tmp_path):
    plan, shards = _fixture(tmp_path)
    result = aggregate(plan, shards, tmp_path / "aggregate.json")
    assert result["status"] == "PASS"
    assert result["task_id"] == 11
    assert result["persistent_story_runs_expected"] == 256
    assert result["persistent_story_runs_accepted"] == 256
    assert result["resource_gate"]["status"] == "PASS_TASK11_BOUNDED_PERSISTENT_RESOURCE_QUALIFICATION"
    assert result["official_test_queries"] == 0
    assert result["execution_authorized"] is False


def test_task11_persistent_resource_aggregate_rejects_label_leakage(tmp_path):
    plan, shards = _fixture(tmp_path)
    path = shards[1] / "task11-persistent-resource-shard-1.json"
    report = json.loads(path.read_text())
    report["official_test_queries"] = 1
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="evaluator/test labels crossed boundary"):
        aggregate(plan, shards, tmp_path / "aggregate.json")


def test_task11_persistent_resource_aggregate_rejects_checkpoint_recovery_mismatch(tmp_path):
    plan, shards = _fixture(tmp_path)
    path = shards[2] / "task11-persistent-resource-shard-2.json"
    report = json.loads(path.read_text())
    report["story_runs"][0]["state_sha256_after_restore"] = "wrong"
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="checkpoint recovery mismatch"):
        aggregate(plan, shards, tmp_path / "aggregate.json")


def test_state_counts_reads_actual_eligibility_ledger_storage():
    from types import SimpleNamespace

    from scripts.run_babi_expansion_learning_microbenchmark import _state_counts

    adapter = SimpleNamespace(learning=SimpleNamespace(
        _observation_journal=[{"kind": "relation"}, {"kind": "event_role"}, {"kind": "context"}],
        temporal_credit=SimpleNamespace(weights={"a": 1, "b": 2}),
        eligibility=SimpleNamespace(_states={"x": {}, "y": {}}),
    ))
    counts = _state_counts(adapter)
    assert counts["observation_journal_rows"] == 3
    assert counts["relation_rows"] == 1
    assert counts["event_role_rows"] == 1
    assert counts["context_rows"] == 1
    assert counts["temporal_credit_weights"] == 2
    assert counts["eligibility_records"] == 2
