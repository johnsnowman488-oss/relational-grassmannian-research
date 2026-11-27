#!/usr/bin/env python3
"""Accept or reject the four-unit full-scale Task 11 resource preflight."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from hashlib import sha256


EXPECTED = {
    f"task11-{architecture}-{condition}-seed953099"
    for architecture in ("HLA", "HLB")
    for condition in ("full_learning", "no_learning")
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def aggregate(report_paths: list[Path], output_path: Path) -> dict:
    if len(report_paths) != 4:
        raise ValueError("full-scale Task 11 preflight requires exactly four run-unit reports")
    reports = {}
    for path in report_paths:
        metrics = _load(path)
        key = metrics.get("run_key")
        if key in reports:
            raise ValueError(f"duplicate preflight run key: {key}")
        reports[key] = metrics
    if set(reports) != EXPECTED:
        raise ValueError(
            f"preflight run keys differ: missing={sorted(EXPECTED-set(reports))}, "
            f"extra={sorted(set(reports)-EXPECTED)}"
        )

    violations = []
    for key, row in sorted(reports.items()):
        if row.get("status") != "PASS":
            violations.append(f"{key}: unit status is not PASS")
        if row.get("run_kind") != "preflight" or row.get("seed") != 953099:
            violations.append(f"{key}: wrong preflight identity")
        if (row.get("task_id") != 11 or row.get("fit_stories") != 1800
                or row.get("warm_start_stories") != 1440
                or row.get("online_adaptation_stories") != 360
                or row.get("validation_stories") != 200
                or row.get("validation_queries") != 1000):
            violations.append(f"{key}: phase counts differ from frozen Task 11 protocol")
        if row.get("learner_labels_loaded") != 0:
            violations.append(f"{key}: learner received evaluator labels")
        if row.get("official_test_queries_loaded") != 0 or row.get("confirmatory_labels_loaded") != 0:
            violations.append(f"{key}: official-test or confirmatory data crossed boundary")
        if row.get("validation_parameter_updates") != 0:
            violations.append(f"{key}: validation changed learned model state")
        if row.get("checkpoint_fingerprint") != row.get("restored_checkpoint_fingerprint"):
            violations.append(f"{key}: checkpoint recovery fingerprint mismatch")
        if row.get("checkpoint_bytes", 0) > 536870912:
            violations.append(f"{key}: checkpoint exceeds 512 MiB")
        if row.get("peak_worker_rss_mb", 1e99) > 4096:
            violations.append(f"{key}: worker RSS exceeds 4 GiB")
        if row.get("peak_python_allocation_mb", 1e99) > 2048:
            violations.append(f"{key}: Python allocation exceeds 2 GiB")
        if row.get("elapsed_seconds", 1e99) > 3600:
            violations.append(f"{key}: run unit exceeds 60 minutes")
        if row.get("artifact_bytes", 1e99) > 268435456:
            violations.append(f"{key}: run artifacts exceed 256 MiB")
        if not row.get("resource_gate", {}).get("within_limits", False):
            violations.append(f"{key}: per-unit resource gate did not pass")

    for architecture in ("HLA", "HLB"):
        full = reports[f"task11-{architecture}-full_learning-seed953099"]
        no_learning = reports[f"task11-{architecture}-no_learning-seed953099"]
        evaluation = full["evaluation"]
        if evaluation.get("answer_exact_match") != 1.0:
            violations.append(f"{architecture}: full-learning preflight did not match 1.0 baseline exact match")
        if evaluation.get("forecast_coverage", 0.0) < 0.90:
            violations.append(f"{architecture}: full-learning preflight coverage below 0.90")
        if evaluation.get("support_witness_recall", 0.0) < 0.95:
            violations.append(f"{architecture}: full-learning preflight witness recall below 0.95")
        if evaluation.get("false_witness_rate") not in (0, 0.0):
            violations.append(f"{architecture}: full-learning preflight produced false witnesses")
        if no_learning["evaluation"].get("forecast_coverage") != 0.0:
            violations.append(f"{architecture}: no-learning control unexpectedly produced covered answers")

    max_unit_seconds = max(float(row["elapsed_seconds"]) for row in reports.values())
    estimated_total_cpu_hours = sum(float(row["elapsed_seconds"]) for row in reports.values()) / 3600.0 * 30.0
    estimated_wall_hours_at_four_workers = estimated_total_cpu_hours / 4.0
    result = {
        "schema": "HLG-BABI-TASK11-FULL-SCALE-PREFLIGHT-AGGREGATE-v1",
        "status": "PASS" if not violations else "FAIL",
        "task_id": 11,
        "reserved_seed": 953099,
        "run_units_expected": 4,
        "run_units_accepted": len(reports),
        "run_keys": sorted(reports),
        "violations": violations,
        "per_unit": {
            key: {
                "architecture": row["architecture"],
                "condition": row["condition"],
                "elapsed_seconds": row["elapsed_seconds"],
                "peak_worker_rss_mb": row["peak_worker_rss_mb"],
                "peak_python_allocation_mb": row["peak_python_allocation_mb"],
                "checkpoint_bytes": row["checkpoint_bytes"],
                "artifact_bytes": row["artifact_bytes"],
                "evaluation": row["evaluation"],
            }
            for key, row in sorted(reports.items())
        },
        "planning_estimate": {
            "basis": "Four full-scale reserved-seed units (HLA/HLB × full_learning/no_learning).",
            "max_observed_unit_seconds": max_unit_seconds,
            "estimated_total_cpu_hours": estimated_total_cpu_hours,
            "estimated_wall_hours_at_four_workers": estimated_wall_hours_at_four_workers,
            "limitation": "Planning estimate only; the six conditions and hosted-runner variance may differ.",
        },
        "execution_authorized": False,
        "decision": (
            "Full-scale resource preflight passed; 120-unit campaign may proceed after "
            "the confirmatory-generator and campaign-workflow CI gates pass."
            if not violations else
            "Campaign remains blocked. Fix the listed violations; do not relax thresholds without a separately reviewed protocol amendment."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    output_path.write_text(payload, encoding="utf-8")
    result["aggregate_sha256"] = sha256(output_path.read_bytes()).hexdigest()
    if violations:
        raise RuntimeError("Task 11 full-scale resource preflight failed: " + "; ".join(violations))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", nargs=4, type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = aggregate(args.reports, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
