"""Replay frozen G2 test streams to recover detector and candidate event telemetry.

This module does not tune detector parameters or change G2 scientific outcomes.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from rgm.experiments.hlg_m3_benchmark_contract import validate_manifest
from rgm.experiments.hlg_m3_g2_confirmatory import (
    CAMPAIGN_ID, COMPARATOR_NAMES, _new_bundle, _run_stream, _json_hash,
)

EXPECTED_MANIFEST_SHA256 = "8548f2a72de09a81f79a57a19b3cd8196dbeae185db9432619e6ac5cc2f49101"
G2_EXECUTION_COMMIT_SHA = "65b3db7a8a548bbc0c08bca477d34ab88b80895f"
EXPECTED_M3_D = {
    "test_streams_with_alarms": 98,
    "total_detector_alarms": 2592,
    "candidate_revisions_applied_to_fallback": 2,
    "alarms_by_drift_family": {
        "compound": 390, "gradual": 545, "stationary": 765,
        "step": 317, "transient": 203, "variance_only": 372,
    },
    "candidate_lifecycle_status_counts": {
        "IN_PROGRESS": 1, "INSUFFICIENT_EVIDENCE_FIT": 29,
        "INSUFFICIENT_EVIDENCE_VALIDATION": 50, "REJECTED": 16,
        "PROMOTED_POST_INSUFFICIENT_EVIDENCE": 0, "PROMOTED_EVALUATED": 2,
    },
}


def _percentile_summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "p90": None}
    arr = np.asarray(values, dtype=float)
    return {
        "count": int(arr.size),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p90": float(np.quantile(arr, 0.90)),
    }


def classify_stream(row: dict[str, Any]) -> dict[str, Any]:
    """Separate evaluator change events from learner-visible alarm events."""
    family = str(row["factor_profile"]["drift_family"])
    events = list(row.get("change_schedule", []))
    drift_events = [e for e in events if str(e["event"]).startswith("drift:")]
    drift_start = int(drift_events[0]["step"]) if drift_events else None
    reversion = next((int(e["step"]) for e in events if e["event"] == "transient_reversion"), None)
    variance_change = next((int(e["step"]) for e in events if e["event"] == "variance_increase"), None)
    alarms = [int(step) for step in row["alarm_steps"]]
    pre_drift = [step for step in alarms if drift_start is not None and step < drift_start]
    post_drift = [step for step in alarms if drift_start is not None and step >= drift_start]
    first_post = post_drift[0] if post_drift else None
    delay = first_post - drift_start if first_post is not None and drift_start is not None else None
    return {
        "world_id": row["world_id"],
        "world_configuration_seed": int(row["world_configuration_seed"]),
        "replicate_seed": int(row["replicate_seed"]),
        "split": row["split"],
        "stream_sha256": row["stream_sha256"],
        "step_count": int(row["step_count"]),
        "factor_profile": row["factor_profile"],
        "detector_parameters": {"allowance": 0.25, "threshold": 5.0},
        "detector_alarm_steps": alarms,
        "detector_alarm_count": int(row["detector_alarms"]),
        "detector_update_count": len(row["detector_trace"] or []),
        "change_schedule_evaluator_only": events,
        "drift_start_step_evaluator_only": drift_start,
        "transient_reversion_step_evaluator_only": reversion,
        "variance_increase_step_evaluator_only": variance_change,
        "pre_drift_alarm_steps": pre_drift,
        "post_drift_alarm_steps": post_drift,
        "first_post_drift_alarm_step": first_post,
        "detection_delay_steps": delay,
        "stationary_false_alarm_stream": bool(family == "stationary" and alarms),
        "stationary_false_alarm_count": len(alarms) if family == "stationary" else 0,
        "missed_scheduled_change": bool(drift_start is not None and first_post is None),
        "detected_before_transient_reversion": bool(
            family == "transient" and first_post is not None and reversion is not None and first_post < reversion
        ),
        "first_detection_after_transient_reversion": bool(
            family == "transient" and first_post is not None and reversion is not None and first_post >= reversion
        ),
        "detected_before_compound_variance_increase": bool(
            family == "compound" and first_post is not None and variance_change is not None
            and first_post < variance_change
        ),
        "detector_trace": row["detector_trace"] or [],
        "detector_baseline": row["detector_baseline"],
        "candidate_lifecycle": row["candidate_lifecycle"],
        "candidate_lifecycle_records": row["candidate_lifecycle_records"],
        "candidate_revision_applied_to_fallback": bool(row["candidate_revision_applied_to_fallback"]),
        "resource": row["resource"],
    }


def _summarize_by_family(streams: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for family in sorted({str(s["factor_profile"]["drift_family"]) for s in streams}):
        rows = [s for s in streams if s["factor_profile"]["drift_family"] == family]
        delays = [float(s["detection_delay_steps"]) for s in rows if s["detection_delay_steps"] is not None]
        statuses = defaultdict(int)
        for row in rows:
            lifecycle = row["candidate_lifecycle"]
            if lifecycle:
                statuses[str(lifecycle["status"])] += 1
        detector_updates = sum(int(row["detector_update_count"]) for row in rows)
        alarm_count = sum(int(row["detector_alarm_count"]) for row in rows)
        summary[family] = {
            "stream_count": len(rows),
            "streams_with_any_alarm": sum(bool(row["detector_alarm_steps"]) for row in rows),
            "total_alarm_events": alarm_count,
            "detector_update_count": detector_updates,
            "alarms_per_1000_detector_updates": (
                1000.0 * alarm_count / detector_updates if detector_updates else None
            ),
            "stationary_false_alarm_streams": sum(bool(row["stationary_false_alarm_stream"]) for row in rows),
            "stationary_false_alarm_events": sum(int(row["stationary_false_alarm_count"]) for row in rows),
            "pre_drift_alarm_streams": sum(bool(row["pre_drift_alarm_steps"]) for row in rows),
            "pre_drift_alarm_events": sum(len(row["pre_drift_alarm_steps"]) for row in rows),
            "detected_change_streams": sum(row["first_post_drift_alarm_step"] is not None for row in rows),
            "missed_change_streams": sum(bool(row["missed_scheduled_change"]) for row in rows),
            "detection_delay_steps": _percentile_summary(delays),
            "detected_before_transient_reversion": sum(bool(row["detected_before_transient_reversion"]) for row in rows),
            "first_detection_after_transient_reversion": sum(bool(row["first_detection_after_transient_reversion"]) for row in rows),
            "detected_before_compound_variance_increase": sum(bool(row["detected_before_compound_variance_increase"]) for row in rows),
            "candidate_lifecycle_status_counts": dict(sorted(statuses.items())),
            "candidate_promotions": sum(bool(row["candidate_revision_applied_to_fallback"]) for row in rows),
        }
    return summary


def run_detector_telemetry_replay(manifest_path: Path) -> dict[str, Any]:
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw.decode("utf-8"))
    manifest_validation = validate_manifest(manifest)
    manifest_sha = hashlib.sha256(raw).hexdigest()
    if manifest_sha != EXPECTED_MANIFEST_SHA256:
        raise ValueError("G2 telemetry replay requires the byte-identical frozen BM0/BM1 manifest")
    if manifest_validation["world_configuration_count"] != 40 or manifest_validation["replicate_stream_count"] != 200:
        raise ValueError("G2 telemetry replay requires the frozen 40-world/200-stream allocation")

    bundles = {capacity: _new_bundle(capacity) for capacity in (2, 4, 8)}
    # Rebuild the same fit+validation state in manifest order before touching test streams.
    for world in manifest["worlds"]:
        if world["split"] == "test":
            continue
        capacity = int(world["factor_profile"]["context_bank_capacity"])
        for seed in world["replicate_seeds"]:
            _run_stream(world, int(seed), bundles[capacity])

    replay_rows = []
    for world in manifest["worlds"]:
        if world["split"] != "test":
            continue
        capacity = int(world["factor_profile"]["context_bank_capacity"])
        for seed in world["replicate_seeds"]:
            test_bundle = copy.deepcopy(bundles[capacity])
            row = _run_stream(world, int(seed), test_bundle, include_detector_trace=True)
            if row["detector_alarms"] != len(row["alarm_steps"]):
                raise AssertionError("alarm counter and event timestamps disagree")
            replay_rows.append(classify_stream(row))

    world_ids = {row["world_id"] for row in replay_rows}
    streams_per_world = defaultdict(int)
    for row in replay_rows:
        streams_per_world[row["world_id"]] += 1
    if len(replay_rows) != 100 or len(world_ids) != 20 or set(streams_per_world.values()) != {5}:
        raise AssertionError("replay did not reproduce exactly 20 held-out worlds × 5 streams")

    alarms_by_family = {
        family: sum(int(row["detector_alarm_count"]) for row in replay_rows
                    if row["factor_profile"]["drift_family"] == family)
        for family in sorted({str(row["factor_profile"]["drift_family"]) for row in replay_rows})
    }
    statuses = {
        status: sum(1 for row in replay_rows if row["candidate_lifecycle"]
                    and row["candidate_lifecycle"]["status"] == status)
        for status in ("IN_PROGRESS", "INSUFFICIENT_EVIDENCE_FIT", "INSUFFICIENT_EVIDENCE_VALIDATION",
                       "REJECTED", "PROMOTED_POST_INSUFFICIENT_EVIDENCE", "PROMOTED_EVALUATED")
    }
    replayed_m3_d = {
        "test_streams_with_alarms": sum(bool(row["detector_alarm_steps"]) for row in replay_rows),
        "total_detector_alarms": sum(int(row["detector_alarm_count"]) for row in replay_rows),
        "candidate_revisions_applied_to_fallback": sum(bool(row["candidate_revision_applied_to_fallback"]) for row in replay_rows),
        "alarms_by_drift_family": alarms_by_family,
        "candidate_lifecycle_status_counts": statuses,
    }
    if replayed_m3_d != EXPECTED_M3_D:
        raise AssertionError({"expected_frozen_m3_d": EXPECTED_M3_D, "replayed_m3_d": replayed_m3_d})

    report = {
        "campaign_id": "HLG-M3-G2-DETECTOR-TELEMETRY-REPLAY-v0.1",
        "source_campaign_id": CAMPAIGN_ID,
        "g2_execution_commit_sha": G2_EXECUTION_COMMIT_SHA,
        "replay_commit_sha": os.environ.get("GITHUB_SHA"),
        "manifest_sha256": manifest_sha,
        "detector_parameters": {"cusum_allowance": 0.25, "cusum_threshold": 5.0},
        "scientific_tuning_performed": False,
        "test_outcomes_used_for_tuning": False,
        "test_worlds_used_for_threshold_selection": False,
        "fit_validation_state_rebuilt_in_manifest_order": True,
        "test_streams_started_from_independent_fit_validation_bundle_copies": True,
        "replayed_m3_d_summary": replayed_m3_d,
        "original_m3_d_summary_reproduced": True,
        "by_drift_family": _summarize_by_family(replay_rows),
        "streams": replay_rows,
        "integrity": {
            "frozen_manifest_identity_verified": True,
            "exact_test_stream_count": len(replay_rows),
            "exact_test_world_count": len(world_ids),
            "replicates_per_world": 5,
            "learner_evaluator_separation_preserved": True,
            "prequential_prediction_before_feedback_preserved": True,
            "alarm_timestamps_match_detector_counter": True,
            "original_m3_d_package_totals_reproduced": True,
        },
        "claim_ceiling": (
            "deterministic telemetry replay of the frozen G2 test allocation; no detector retuning, "
            "no revised G2 scientific gate, and no new performance claim"
        ),
    }
    report["evidence_sha256"] = _json_hash(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_detector_telemetry_replay(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "campaign_id": report["campaign_id"],
        "stream_count": len(report["streams"]),
        "total_detector_alarms": report["replayed_m3_d_summary"]["total_detector_alarms"],
        "original_m3_d_summary_reproduced": report["original_m3_d_summary_reproduced"],
        "evidence_sha256": report["evidence_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
