#!/usr/bin/env python3
"""Accept the first four actual Task 11 campaign units as the Wave 1 gate."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path


EXPECTED = {
    f"task11-{architecture}-{condition}-seed953100"
    for architecture in ("HLA", "HLB")
    for condition in ("full_learning", "no_learning")
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _verify_hash_list(root: Path) -> None:
    hash_file = root / "sha256sums.txt"
    if not hash_file.is_file():
        raise ValueError(f"missing sha256sums.txt in {root}")
    listed = set()
    for line in hash_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        path = root / name
        if name in listed or not path.is_file() or _sha(path) != digest:
            raise ValueError(f"artifact digest missing, duplicated or invalid: {root}/{name}")
        listed.add(name)
    required = {
        "per-run-config.json", "source-and-partition-manifest.json",
        "per-run-metrics.json", "prediction-journal.jsonl",
        "witness-audit.jsonl", "resource-usage.json", "model-snapshot.json",
    }
    if not required.issubset(listed):
        raise ValueError(f"required Wave 1 evidence absent from hash list: {sorted(required-listed)}")


def accept(manifest_path: Path, protocol_path: Path, run_root: Path,
           output_path: Path) -> dict:
    manifest = _load(manifest_path)
    protocol = _load(protocol_path)
    if manifest.get("protocol_sha256") != _sha(protocol_path):
        raise ValueError("Wave 1 manifest protocol digest mismatch")
    if manifest.get("native_commit") != protocol["native_runtime"]["pinned_commit"]:
        raise ValueError("Wave 1 manifest native pin differs from protocol")
    expected_units = {
        row["run_unit_key"]: row for row in manifest["run_units"]
        if row.get("seed") == 953100
        and row.get("architecture") in ("HLA", "HLB")
        and row.get("condition") in ("full_learning", "no_learning")
    }
    if set(expected_units) != EXPECTED:
        raise ValueError("frozen manifest does not contain exactly the four Wave 1 keys")
    run_dirs = sorted(path.parent for path in run_root.rglob("per-run-metrics.json"))
    if len(run_dirs) != 4:
        raise ValueError(f"Wave 1 requires exactly four campaign artifact directories; found {len(run_dirs)}")

    limits = protocol["resource_preflight"]["limits"]
    by_key = {}
    native_hashes = set()
    per_unit = {}
    violations = []
    for root in run_dirs:
        _verify_hash_list(root)
        metrics = _load(root / "per-run-metrics.json")
        key = metrics.get("run_key")
        if key in by_key:
            violations.append(f"duplicate Wave 1 key: {key}")
            continue
        if key not in expected_units:
            violations.append(f"unexpected Wave 1 key: {key}")
            continue
        unit = expected_units[key]
        expected_identity = {
            "task_id": unit["task_id"], "architecture": unit["architecture"],
            "condition": unit["condition"], "seed": unit["seed"],
            "manifest_shard": unit["shard"],
        }
        if metrics.get("run_kind") != "campaign" or metrics.get("status") != "PASS":
            violations.append(f"{key}: not a successful campaign unit")
        if any(metrics.get(field) != value for field, value in expected_identity.items()):
            violations.append(f"{key}: run identity or shard differs from frozen manifest")
        if metrics.get("manifest_sha256") != manifest.get("manifest_sha256"):
            violations.append(f"{key}: manifest digest mismatch")
        if metrics.get("protocol_sha256") != manifest.get("protocol_sha256"):
            violations.append(f"{key}: protocol digest mismatch")
        if metrics.get("source_sha256") != manifest.get("source", {}).get("sha256"):
            violations.append(f"{key}: source digest mismatch")
        if metrics.get("native_commit") != manifest.get("native_commit"):
            violations.append(f"{key}: native commit mismatch")
        if metrics.get("learner_labels_loaded") != 0:
            violations.append(f"{key}: evaluator labels reached learner")
        if metrics.get("official_test_queries_loaded") != 0 or metrics.get("confirmatory_labels_loaded") != 0:
            violations.append(f"{key}: sealed official-test or confirmatory data was loaded")
        if metrics.get("validation_parameter_updates") != 0:
            violations.append(f"{key}: validation updated model parameters")
        if metrics.get("validation_evaluator_labels_opened_after_predictions") != 1000:
            violations.append(f"{key}: evaluator labels were not opened after all 1,000 predictions")
        if metrics.get("checkpoint_fingerprint") != metrics.get("restored_checkpoint_fingerprint"):
            violations.append(f"{key}: checkpoint restore fingerprint mismatch")
        if (metrics.get("fit_stories") != 1800 or metrics.get("warm_start_stories") != 1440
                or metrics.get("online_adaptation_stories") != 360
                or metrics.get("validation_stories") != 200
                or metrics.get("validation_queries") != 1000):
            violations.append(f"{key}: whole-story fit/adaptation/validation counts differ from protocol")
        for field, maximum in (
            ("peak_worker_rss_mb", limits["max_worker_rss_mb"]),
            ("peak_python_allocation_mb", limits["max_python_allocation_mb"]),
            ("checkpoint_bytes", limits["max_checkpoint_bytes"]),
            ("elapsed_seconds", limits["max_unit_wall_seconds"]),
            ("artifact_bytes", limits["max_unit_artifact_bytes"]),
        ):
            if not isinstance(metrics.get(field), (int, float)) or metrics[field] > maximum:
                violations.append(f"{key}: {field} exceeds or is missing its frozen ceiling")
        if not metrics.get("resource_gate", {}).get("within_limits", False):
            violations.append(f"{key}: runner resource gate did not pass")

        predictions = [
            json.loads(line) for line in (root / "prediction-journal.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        prediction_ids = [row.get("query_id") for row in predictions]
        evaluation_ids = [
            row.get("query_id") for row in metrics.get("evaluation", {}).get("per_query", [])
        ]
        if len(prediction_ids) != 1000 or len(set(prediction_ids)) != 1000:
            violations.append(f"{key}: prediction journal is incomplete or duplicated")
        if set(prediction_ids) != set(evaluation_ids) or len(evaluation_ids) != 1000:
            violations.append(f"{key}: prediction and evaluator query IDs differ")

        run_config = _load(root / "per-run-config.json")
        if run_config.get("run_key") != key or run_config.get("run_kind") != "campaign":
            violations.append(f"{key}: per-run config identity mismatch")
        if run_config.get("manifest_shard") != unit["shard"]:
            violations.append(f"{key}: per-run config shard mismatch")
        for field, expected in (
            ("native_commit", manifest["native_commit"]),
            ("manifest_sha256", manifest["manifest_sha256"]),
            ("protocol_sha256", manifest["protocol_sha256"]),
            ("source_sha256", manifest["source"]["sha256"]),
            ("soe_feature_dims", manifest["soe_feature_dims"]),
            ("soe_dt", manifest["soe_dt"]),
            ("top_down_gain", manifest["top_down_gain"]),
        ):
            if run_config.get(field) != expected:
                violations.append(f"{key}: per-run config {field} mismatch")
        native_hash = metrics.get("native_library_sha256")
        if not native_hash or run_config.get("native_library_sha256") != native_hash:
            violations.append(f"{key}: native library SHA-256 missing or inconsistent")
        native_hashes.add(native_hash)

        model = _load(root / "model-snapshot.json")
        if model.get("run_key") != key or model.get("manifest_shard") != unit["shard"]:
            violations.append(f"{key}: model snapshot identity mismatch")
        if model.get("evaluator_labels_included") is not False:
            violations.append(f"{key}: evaluator labels present in model snapshot")
        for field, expected in (
            ("native_library_sha256", native_hash),
            ("manifest_sha256", manifest["manifest_sha256"]),
            ("protocol_sha256", manifest["protocol_sha256"]),
            ("source_sha256", manifest["source"]["sha256"]),
        ):
            if model.get(field) != expected:
                violations.append(f"{key}: model snapshot {field} mismatch")
        by_key[key] = metrics
        per_unit[key] = {
            "elapsed_seconds": metrics.get("elapsed_seconds"),
            "peak_worker_rss_mb": metrics.get("peak_worker_rss_mb"),
            "peak_python_allocation_mb": metrics.get("peak_python_allocation_mb"),
            "checkpoint_bytes": metrics.get("checkpoint_bytes"),
            "artifact_bytes": metrics.get("artifact_bytes"),
            "resource_gate_passed": metrics.get("resource_gate", {}).get("within_limits") is True,
        }

    if set(by_key) != EXPECTED:
        violations.append(
            f"Wave 1 key set mismatch: missing={sorted(EXPECTED-set(by_key))}, "
            f"extra={sorted(set(by_key)-EXPECTED)}"
        )
    if len(native_hashes) != 1 or None in native_hashes:
        violations.append("Wave 1 units do not share one native-library SHA-256")
    for architecture in ("HLA", "HLB"):
        no_learning = by_key.get(f"task11-{architecture}-no_learning-seed953100")
        if no_learning and no_learning.get("evaluation", {}).get("forecast_coverage") != 0.0:
            violations.append(f"{architecture}: no-learning control unexpectedly produced forecast coverage")

    result = {
        "schema": "HLG-BABI-TASK11-WAVE1-ACCEPTANCE-v1",
        "status": "PASS" if not violations else "FAIL",
        "protocol_version": protocol.get("protocol_version"),
        "task_id": 11,
        "wave1_seed": 953100,
        "run_units_expected": 4,
        "run_units_accepted": len(by_key),
        "run_keys": sorted(by_key),
        "manifest_sha256": manifest.get("manifest_sha256"),
        "protocol_sha256": manifest.get("protocol_sha256"),
        "native_commit": manifest.get("native_commit"),
        "native_library_sha256": next(iter(native_hashes)) if len(native_hashes) == 1 else None,
        "per_unit_resource_evidence": per_unit,
        "performance_metrics_used_for_gate": False,
        "thresholds_relaxed": False,
        "remaining_campaign_units": 116,
        "remaining_units_authorized": not violations,
        "violations": violations,
        "decision": (
            "Wave 1 accepted. The four Wave 1 units count toward the 120-unit campaign; "
            "the workflow may execute only the remaining 116 unique run keys."
            if not violations else
            "Wave 1 rejected. The remaining 116 units remain blocked; preserve all evidence and do not relax frozen limits."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["acceptance_sha256"] = _sha(output_path)
    if violations:
        raise RuntimeError("Task 11 Wave 1 acceptance failed: " + "; ".join(violations))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = accept(args.manifest, args.protocol, args.run_root, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
