"""Verify the six HLG-M3 G2 package files and aggregate evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PACKAGE_IDS = ("M3-A", "M3-B", "M3-C", "M3-D", "M3-E", "M3-I")
EXPECTED_MANIFEST_SHA256 = "8548f2a72de09a81f79a57a19b3cd8196dbeae185db9432619e6ac5cc2f49101"


def _digest(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def verify_evidence(output_dir: Path, manifest_path: Path) -> dict:
    raw_manifest = manifest_path.read_bytes()
    manifest_sha = hashlib.sha256(raw_manifest).hexdigest()
    if manifest_sha != EXPECTED_MANIFEST_SHA256:
        raise ValueError("evidence manifest differs from the G1-accepted bytes")
    aggregate_path = output_dir / "aggregate.json"
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    aggregate_hash = aggregate.pop("aggregate_sha256", None)
    if aggregate_hash != _digest(aggregate):
        raise ValueError("aggregate evidence digest mismatch")
    if aggregate.get("manifest_sha256") != manifest_sha:
        raise ValueError("aggregate manifest identity mismatch")
    if aggregate.get("stream_count") != 200 or aggregate.get("world_count") != 40:
        raise ValueError("aggregate does not represent the frozen 40-world/200-stream campaign")
    if aggregate.get("split_stream_counts") != {
        "development_fit": 60, "development_validation": 40, "test": 100
    }:
        raise ValueError("aggregate split stream counts do not match the frozen allocation")
    if aggregate.get("test_world_count") != 20:
        raise ValueError("aggregate test world count does not match the frozen allocation")
    observed = {}
    for package_id in PACKAGE_IDS:
        path = output_dir / f"{package_id.lower()}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        recorded = payload.pop("evidence_sha256", None)
        if payload.get("package_id") != package_id:
            raise ValueError(f"{package_id}: package identity mismatch")
        if recorded != _digest(payload):
            raise ValueError(f"{package_id}: evidence digest mismatch")
        observed[package_id] = _digest({**payload, "evidence_sha256": recorded})
    if observed != aggregate.get("package_evidence_sha256"):
        raise ValueError("aggregate package digest map does not match package files")
    if aggregate.get("integrity", {}).get("prequential_prediction_before_feedback") is not True:
        raise ValueError("prequential integrity assertion missing")
    if aggregate.get("integrity", {}).get("no_evaluator_context_labels_used_for_routing") is not True:
        raise ValueError("learner/evaluator boundary assertion missing")
    return {
        "valid": True, "manifest_sha256": manifest_sha,
        "stream_count": 200, "world_count": 40, "test_world_count": 20,
        "verified_packages": list(PACKAGE_IDS),
        "m4_authorised": bool(aggregate.get("m4_authorised")),
        "capability_gate_passed": bool(aggregate.get("capability_gate", {}).get("passed")),
        "adaptation_gate_passed": bool(aggregate.get("adaptation_gate", {}).get("passed")),
        "resource_gate_passed": bool(aggregate.get("resource_gate", {}).get("passed")),
        "aggregate_sha256": aggregate_hash,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    result = verify_evidence(args.output_dir, args.manifest)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
