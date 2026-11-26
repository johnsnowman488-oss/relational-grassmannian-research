#!/usr/bin/env python3
"""Audit the complete P6 controller numeric payload omitted from the v4 subtotal."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rgm.leptograph.m3.resource import integrated_resource_snapshot
from rgm.leptograph.m4.stability import CoupledAdaptiveSystem

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/experiments/HLG_H1_P6_FULL_RUNTIME_v4.json"


def audit_resource_footprint() -> dict:
    config = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    model = CoupledAdaptiveSystem(
        max_state_norm=float(config["p6_model"]["max_state_norm"])
    )
    base = integrated_resource_snapshot(
        estimator=model.estimator,
        context_bank=model.context_bank,
        activation=model.activation,
        detector=model.detector,
        revision=model.revision,
    )
    state_vector_bytes = int(model.state.nbytes)
    transition_matrix_bytes = int(model.transition.nbytes)
    soe_memory_bytes = int(
        model.memory.channels.nbytes
        + model.memory.injection_matrices.nbytes
        + model.memory.decay_rates.nbytes
    )
    p6_controller_bytes = (
        state_vector_bytes + transition_matrix_bytes + soe_memory_bytes
    )
    total_persistent_bytes = (
        int(base["persistent_state_bytes"]) + p6_controller_bytes
    )
    envelope = config["resource_envelope"]
    checks = {
        "p6_state_vector_included": state_vector_bytes > 0,
        "p6_transition_matrix_included": transition_matrix_bytes > 0,
        "p6_soe_memory_included": soe_memory_bytes > 0,
        "persistent_numeric_state_within_cap": total_persistent_bytes
        <= int(envelope["persistent_state_bytes"]),
        "trainable_parameters_within_cap": int(base["trainable_parameter_count"])
        <= int(envelope["trainable_parameters"]),
        "update_compute_within_cap": int(base["max_observed_or_declared_update_multiply_adds"])
        <= int(envelope["update_multiply_adds"]),
        "query_compute_within_cap": int(base["max_observed_or_declared_query_multiply_adds"])
        <= int(envelope["query_multiply_adds"]),
    }
    return {
        "audit_id": "HLG-H1-P6-CONTROLLER-RESOURCE-AUDIT-v1",
        "scope": "initial full numeric P6 controller plus integrated M3 adaptive state; adds the P6 state vector and fixed transition matrix omitted from the v4 campaign subtotal; excludes Python object/container overhead and native-runtime process memory",
        "components_bytes": {
            "m3_integrated_persistent_state": int(base["persistent_state_bytes"]),
            "p6_state_vector": state_vector_bytes,
            "p6_transition_matrix": transition_matrix_bytes,
            "p6_soe_memory": soe_memory_bytes,
            "p6_controller_total": p6_controller_bytes,
            "combined_persistent_numeric_state": total_persistent_bytes,
        },
        "trainable_parameter_count": int(base["trainable_parameter_count"]),
        "update_multiply_add_upper_bound": int(base["max_observed_or_declared_update_multiply_adds"]),
        "query_multiply_add_upper_bound": int(base["max_observed_or_declared_query_multiply_adds"]),
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
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
