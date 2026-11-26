#!/usr/bin/env python3
"""Audit the complete P6 controller numeric payload omitted from the v4 subtotal."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rgm.leptograph.m4.stability import CoupledAdaptiveSystem

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/experiments/HLG_H1_P6_FULL_RUNTIME_v4.json"
CAMPAIGN = ROOT / "docs/experiments/HLG_H1_P6_FULL_RUNTIME_v4_RESULT_SUMMARY.json"


def audit_resource_footprint() -> dict:
    config = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
    model = CoupledAdaptiveSystem(
        max_state_norm=float(config["p6_model"]["max_state_norm"])
    )
    state_vector_bytes = int(model.state.nbytes)
    transition_matrix_bytes = int(model.transition.nbytes)
    soe_memory_bytes = int(
        model.memory.channels.nbytes
        + model.memory.injection_matrices.nbytes
        + model.memory.decay_rates.nbytes
    )
    extra_controller_bytes = state_vector_bytes + transition_matrix_bytes
    envelope = config["resource_envelope"]
    architectures = {}
    for name, values in campaign["architectures"].items():
        total = int(values["max_resource_state_bytes"]) + extra_controller_bytes
        architectures[name] = {
            "campaign_m3_plus_soe_bytes": int(values["max_resource_state_bytes"]),
            "p6_state_vector_bytes": state_vector_bytes,
            "p6_transition_matrix_bytes": transition_matrix_bytes,
            "combined_persistent_numeric_state_bytes": total,
            "trainable_parameters": int(values["max_trainable_parameters"]),
            "update_multiply_add_upper_bound": int(values["max_update_multiply_adds"]),
            "query_multiply_add_upper_bound": int(values["max_query_multiply_adds"]),
            "checks": {
                "combined_state_within_cap": total <= int(envelope["persistent_state_bytes"]),
                "trainable_parameters_within_cap": int(values["max_trainable_parameters"])
                <= int(envelope["trainable_parameters"]),
                "update_compute_within_cap": int(values["max_update_multiply_adds"])
                <= int(envelope["update_multiply_adds"]),
                "query_compute_within_cap": int(values["max_query_multiply_adds"])
                <= int(envelope["query_multiply_adds"]),
            },
        }
    checks = {
        "p6_state_vector_included": state_vector_bytes > 0,
        "p6_transition_matrix_included": transition_matrix_bytes > 0,
        "p6_soe_memory_is_already_in_campaign_subtotal": soe_memory_bytes > 0,
    }
    for values in architectures.values():
        checks.update(values["checks"])
    return {
        "audit_id": "HLG-H1-P6-CONTROLLER-RESOURCE-AUDIT-v1",
        "campaign_id": campaign["campaign_id"],
        "campaign_workflow_run_id": campaign["workflow_run_id"],
        "campaign_artifact_id": campaign["artifact_id"],
        "scope": "campaign maximum M3 integrated state plus P6 SOE arrays, with the P6 state vector and fixed transition matrix added explicitly; excludes Python object/container overhead and native-runtime process memory",
        "p6_static_components_bytes": {
            "state_vector": state_vector_bytes,
            "transition_matrix": transition_matrix_bytes,
            "soe_memory_already_counted_in_campaign_subtotal": soe_memory_bytes,
        },
        "architectures": architectures,
        "envelope": envelope,
        "checks": checks,
        "passed": all(checks.values()),
    }



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit_resource_footprint()
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
