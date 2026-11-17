"""Fail-closed readiness audit for the frozen HLG-M3 G2 campaign.

This is an implementation audit, not a scientific benchmark runner. It makes
G2 blockers explicit and refuses to label existing smoke probes as confirmatory
evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

from rgm.experiments.hlg_m3_benchmark_contract import validate_manifest
from rgm.experiments.hlg_m3_g2_structural_preflight import build_structural_preflight_report
from rgm.leptograph.m3.context import ContextBank
from rgm.leptograph.m3.controls import MemoryArchitecture
from rgm.leptograph.m3.estimation import MultiSourceRidge
from rgm.leptograph.m3.revision_campaign import CandidateLifecycle

CAMPAIGN_ID = "HLG-M3-BROAD-BENCHMARK-BM0-BM1-v0.1"
READINESS_ID = "HLG-M3-G2-IMPLEMENTATION-READINESS-v0.2"
G1_ACCEPTED_RUN_ID = 44111641084
G1_ACCEPTED_RUN_URL = (
    "https://github.com/johnsnowman488-oss/relational-grassmannian-research/"
    "actions/runs/44111641084"
)
G1_MANIFEST_SHA256 = (
    "8548f2a72de09a81f79a57a19b3cd8196dbeae185db9432619e6ac5cc2f49101"
)
G2_RUNNER_RELATIVE_PATH = Path("src/rgm/experiments/hlg_m3_g2_confirmatory.py")
MANIFEST_RELATIVE_PATH = Path(
    "docs/hybrid_leptograph_m3_benchmark_split_manifest_v0_1.json"
)

REQUIRED_PACKAGES = ("M3-A", "M3-B", "M3-C", "M3-D", "M3-E", "M3-I")


def build_readiness_report(root: Path) -> dict[str, Any]:
    """Inspect frozen inputs and existing public learner/control interfaces."""
    root = root.resolve()
    manifest_path = root / MANIFEST_RELATIVE_PATH
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    raw_manifest = manifest_path.read_bytes()
    manifest_hash = hashlib.sha256(raw_manifest).hexdigest()
    manifest = json.loads(raw_manifest.decode("utf-8"))
    manifest_validation = validate_manifest(manifest)
    structural_preflight = build_structural_preflight_report()

    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if manifest_hash != G1_MANIFEST_SHA256:
        blockers.append({
            "id": "manifest_identity_changed",
            "detail": (
                "The on-disk manifest does not match the manifest bytes accepted "
                "by G1. G2 must not start on a different allocation."
            ),
        })

    if not (root / G2_RUNNER_RELATIVE_PATH).is_file():
        blockers.append({
            "id": "g2_confirmatory_runner_missing",
            "detail": (
                "No runner consumes the frozen 200 streams and emits the six "
                "confirmatory package records plus aggregate evidence."
            ),
        })

    resource_lower_bound = structural_preflight["resource_lower_bound"]
    if resource_lower_bound["numeric_buffer_lower_bound_bytes"] > resource_lower_bound["persistent_state_cap_bytes"]:
        blockers.append({
            "id": "current_candidate_exceeds_frozen_persistent_state_cap",
            "detail": (
                f"The measured lower bound is {resource_lower_bound['numeric_buffer_lower_bound_bytes']} bytes "
                f"versus the frozen {resource_lower_bound['persistent_state_cap_bytes']}-byte cap. "
                "This excludes activation, detector and candidate-revision state; G2 requires "
                "a resource-feasible redesign or an explicitly approved pre-G2 budget amendment."
            ),
        })
    if any(not value for value in structural_preflight["context_capacity_pressure"]["can_retain_one_slot_per_prototype"].values()):
        warnings.append({
            "id": "context_capacity_admission_policy_required",
            "detail": (
                "The declared K=2 and K=4 settings cannot retain one slot for all six generated "
                "context prototypes simultaneously. The learner now supports an explicit "
                "label-blind nearest-slot reuse policy; G2 must freeze that policy and report "
                "its effect on context routing and relation prediction."
            ),
        })

    update_parameters = list(inspect.signature(MultiSourceRidge.update).parameters)
    masked_update = "source_gates" in update_parameters
    if not masked_update:
        blockers.append({
            "id": "masked_online_update_missing",
            "detail": (
                "The estimator cannot update sufficient statistics with explicit "
                "per-source observation gates. Missing source vectors must not be "
                "silently represented as observed zeros."
            ),
        })

    context_conditioned_methods = {
        "context_slot_operator_lookup": hasattr(ContextBank, "operator_for_slot"),
        "context_conditioned_prediction": hasattr(MultiSourceRidge, "predict_context_conditioned"),
    }
    if not all(context_conditioned_methods.values()):
        blockers.append({
            "id": "context_conditioned_relation_store_missing",
            "detail": (
                "The generated REL-A..REL-D episodes use different latent operators "
                "selected by evaluator-owned context identity. ContextBank stores "
                "prototypes only and MultiSourceRidge exposes one shared source "
                "operator per source block; there is no learner-side operator "
                "retrieval keyed by an accepted context. The current predictor "
                "therefore does not implement the generator's context-conditioned "
                "relation task."
            ),
        })

    control_methods = {
        name: hasattr(MemoryArchitecture, name)
        for name in ("predict", "update_target", "score_target")
    }
    if not control_methods["predict"]:
        blockers.append({
            "id": "c0_c4_task_prediction_adapter_missing",
            "detail": (
                "C0-C4 expose memory write/read and resource counters, but no "
                "target-prediction API. They cannot yet be compared on the frozen "
                "held-out primary-composition loss endpoint."
            ),
        })

    resource_method = hasattr(MultiSourceRidge, "resource_snapshot")
    control_resource_method = hasattr(MemoryArchitecture, "resource_snapshot")
    if not (resource_method and control_resource_method):
        blockers.append({
            "id": "resource_instrumentation_missing",
            "detail": "One or more existing model/control resource snapshots are absent.",
        })
    else:
        blockers.append({
            "id": "integrated_candidate_resource_ledger_missing",
            "detail": (
                "Current resource snapshots account for estimator statistics or "
                "individual C0-C4 controls, not the complete persistent state of "
                "the integrated context/estimator/evidence/revision candidate."
            ),
        })

    candidate_lifecycle_api_available = (
        hasattr(CandidateLifecycle, "start")
        and hasattr(CandidateLifecycle, "observe")
        and hasattr(CandidateLifecycle, "resource_snapshot")
    )
    if not candidate_lifecycle_api_available:
        blockers.append({
            "id": "candidate_lifecycle_core_missing",
            "detail": (
                "The frozen 32/32/64 candidate-window state machine with minimum "
                "24-observation gates is not available as a tested learner component."
            ),
        })
    elif not (root / G2_RUNNER_RELATIVE_PATH).is_file():
        blockers.append({
            "id": "candidate_lifecycle_campaign_integration_missing",
            "detail": (
                "The 32/32/64 lifecycle component exists, but no confirmatory "
                "runner connects alarm events, target feedback, residualized "
                "candidate fitting, validation identifiability and untouched "
                "post-promotion scoring across the frozen streams."
            ),
        })

    generator_path = root / "src/rgm/experiments/hlg_m3_benchmark_generator.py"
    generator_text = generator_path.read_text(encoding="utf-8")
    if "It is not an algebraic product of operators" in generator_text:
        warnings.append({
            "id": "composition_semantics_are_sequential",
            "detail": (
                "The generator represents each declared composition as an ordered "
                "sequence of context-conditioned primitive episodes, not as an "
                "algebraic product of relation operators. G2 reporting must retain "
                "that narrower operational interpretation."
            ),
        })

    return {
        "readiness_id": READINESS_ID,
        "campaign_id": CAMPAIGN_ID,
        "schema_version": 2,
        "g1": {
            "accepted": True,
            "workflow_run_id": G1_ACCEPTED_RUN_ID,
            "workflow_run_url": G1_ACCEPTED_RUN_URL,
            "manifest_sha256_expected": G1_MANIFEST_SHA256,
            "manifest_sha256_observed": manifest_hash,
            "manifest_identity_matches": manifest_hash == G1_MANIFEST_SHA256,
            "manifest_validation_passed": bool(manifest_validation["valid"]),
            "world_configuration_count": manifest_validation["world_configuration_count"],
            "replicate_stream_count": manifest_validation["replicate_stream_count"],
        },
        "required_packages": list(REQUIRED_PACKAGES),
        "observed_interfaces": {
            "multi_source_ridge_update_parameters": update_parameters,
            "masked_online_update_available": masked_update,
            "context_conditioned_methods": context_conditioned_methods,
            "memory_architecture_methods": {
                name: hasattr(MemoryArchitecture, name)
                for name in (
                    "update_mode", "update_relation", "read_mode",
                    "read_relation", "resource_snapshot", "predict",
                )
            },
            "integrated_resource_snapshots_available": {
                "multi_source_ridge": resource_method,
                "memory_architecture": control_resource_method,
            },
            "g2_runner_present": (root / G2_RUNNER_RELATIVE_PATH).is_file(),
            "candidate_lifecycle_api_available": candidate_lifecycle_api_available,
            "structural_preflight": structural_preflight,
        },
        "blockers": blockers,
        "warnings": warnings,
        "ready_to_start_g2": not blockers,
        "readiness_status": "READY_TO_START_G2" if not blockers else "BLOCKED_G2_NOT_STARTED",
        "scientific_benchmark_executed": False,
        "m3_scientific_validation_complete": False,
        "claim_ceiling": (
            "G2 implementation readiness audit only. No confirmatory learner "
            "performance, C0-C4 task ranking, or M3 scientific result."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="exit non-zero when G2 implementation blockers remain",
    )
    args = parser.parse_args()
    report = build_readiness_report(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({
        "readiness_status": report["readiness_status"],
        "blocker_ids": [item["id"] for item in report["blockers"]],
        "warning_ids": [item["id"] for item in report["warnings"]],
        "manifest_sha256": report["g1"]["manifest_sha256_observed"],
        "scientific_benchmark_executed": False,
    }, sort_keys=True))
    if args.require_ready and not report["ready_to_start_g2"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
