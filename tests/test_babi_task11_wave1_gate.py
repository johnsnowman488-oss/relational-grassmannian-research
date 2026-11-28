import hashlib
import json
from pathlib import Path

import pytest

from scripts.accept_babi_task11_wave1 import EXPECTED, accept


def _write(path: Path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _hash_artifacts(root: Path):
    rows = []
    for path in sorted(root.iterdir()):
        if path.is_file() and path.name != "sha256sums.txt":
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (root / "sha256sums.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path):
    protocol = {
        "protocol_version": "1.1.0",
        "native_runtime": {"pinned_commit": "native-pin"},
        "resource_preflight": {"limits": {
            "max_worker_rss_mb": 2048, "max_python_allocation_mb": 1024,
            "max_checkpoint_bytes": 536870912, "max_unit_wall_seconds": 3600,
            "max_unit_artifact_bytes": 268435456,
        }},
    }
    protocol_path = tmp_path / "protocol.json"
    _write(protocol_path, protocol)
    protocol_sha = hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    units = []
    for i, key in enumerate(sorted(EXPECTED)):
        _, architecture, condition, seed_text = key.split("-")
        units.append({
            "run_unit_key": key, "task_id": 11, "architecture": architecture,
            "condition": condition, "seed": int(seed_text.removeprefix("seed")), "shard": i,
        })
    manifest = {
        "protocol_sha256": protocol_sha, "manifest_sha256": "m" * 64,
        "native_commit": "native-pin", "source": {"sha256": "s" * 64},
        "soe_feature_dims": [3, 3, 3], "soe_dt": 0.01, "top_down_gain": 1.0,
        "run_units": units,
    }
    manifest_path = tmp_path / "manifest.json"
    _write(manifest_path, manifest)
    run_root = tmp_path / "runs"
    run_root.mkdir()
    for unit in units:
        key = unit["run_unit_key"]
        root = run_root / key
        root.mkdir()
        ids = [f"q{i}" for i in range(1000)]
        is_no_learning = unit["condition"] == "no_learning"
        metrics = {
            "run_key": key, "run_kind": "campaign", "status": "PASS",
            "task_id": 11, "architecture": unit["architecture"],
            "condition": unit["condition"], "seed": unit["seed"],
            "manifest_shard": unit["shard"], "manifest_sha256": manifest["manifest_sha256"],
            "protocol_sha256": protocol_sha, "source_sha256": manifest["source"]["sha256"],
            "native_commit": manifest["native_commit"], "native_library_sha256": "n" * 64,
            "learner_labels_loaded": 0, "official_test_queries_loaded": 0,
            "confirmatory_labels_loaded": 0, "validation_parameter_updates": 0,
            "validation_evaluator_labels_opened_after_predictions": 1000,
            "checkpoint_fingerprint": "checkpoint", "restored_checkpoint_fingerprint": "checkpoint",
            "fit_stories": 1800, "warm_start_stories": 1440,
            "online_adaptation_stories": 360, "validation_stories": 200,
            "validation_queries": 1000, "peak_worker_rss_mb": 1000,
            "peak_python_allocation_mb": 500, "checkpoint_bytes": 1024,
            "elapsed_seconds": 100, "artifact_bytes": 4096,
            "resource_gate": {"within_limits": True},
            "evaluation": {
                "forecast_coverage": 0.0 if is_no_learning else 1.0,
                "per_query": [{"query_id": q} for q in ids],
            },
        }
        _write(root / "per-run-metrics.json", metrics)
        _write(root / "per-run-config.json", {
            "run_key": key, "run_kind": "campaign", "manifest_shard": unit["shard"],
            "native_commit": manifest["native_commit"], "native_library_sha256": "n" * 64,
            "manifest_sha256": manifest["manifest_sha256"], "protocol_sha256": protocol_sha,
            "source_sha256": manifest["source"]["sha256"], "soe_feature_dims": [3, 3, 3],
            "soe_dt": 0.01, "top_down_gain": 1.0,
        })
        _write(root / "model-snapshot.json", {
            "run_key": key, "manifest_shard": unit["shard"],
            "evaluator_labels_included": False, "native_library_sha256": "n" * 64,
            "manifest_sha256": manifest["manifest_sha256"], "protocol_sha256": protocol_sha,
            "source_sha256": manifest["source"]["sha256"],
        })
        (root / "source-and-partition-manifest.json").write_text("{}\n", encoding="utf-8")
        (root / "prediction-journal.jsonl").write_text(
            "".join(json.dumps({"query_id": q, "story_id": "story"}) + "\n" for q in ids),
            encoding="utf-8",
        )
        (root / "witness-audit.jsonl").write_text("{}\n", encoding="utf-8")
        _write(root / "resource-usage.json", {"elapsed_seconds": 100})
        _hash_artifacts(root)
    return manifest_path, protocol_path, run_root


def test_wave1_accepts_four_real_campaign_units_and_authorizes_only_remaining_116(tmp_path):
    manifest, protocol, run_root = _fixture(tmp_path)
    result = accept(manifest, protocol, run_root, tmp_path / "acceptance.json")
    assert result["status"] == "PASS"
    assert result["run_units_accepted"] == 4
    assert result["remaining_campaign_units"] == 116
    assert result["remaining_units_authorized"] is True
    assert result["performance_metrics_used_for_gate"] is False


def test_wave1_rejects_evaluator_leakage_without_relaxing_limits(tmp_path):
    manifest, protocol, run_root = _fixture(tmp_path)
    metrics_path = next(run_root.rglob("per-run-metrics.json"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["learner_labels_loaded"] = 1
    _write(metrics_path, metrics)
    _hash_artifacts(metrics_path.parent)
    with pytest.raises(RuntimeError, match="acceptance failed"):
        accept(manifest, protocol, run_root, tmp_path / "acceptance.json")
