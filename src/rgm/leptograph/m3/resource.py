"""Integrated numeric resource accounting for an HLG-M3 candidate.

The ledger counts live numeric payloads, not Python object/container overhead.
It keeps persistent state, trainable parameters, and per-operation arithmetic
separate so a compact state estimate cannot conceal an oversized parameter or
compute footprint.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np

from rgm.experiments.hlg_m3_benchmark_contract import F5_RESOURCE_ENVELOPE


def integrated_resource_snapshot(
    *,
    estimator,
    context_bank,
    activation,
    detector,
    lifecycle=None,
    revision=None,
    controls: Iterable = (),
) -> dict:
    """Measure the simultaneously live numeric state of one integrated candidate."""
    estimator_snapshot = estimator.resource_snapshot()
    context_snapshot = context_bank.relation_resource_snapshot()

    context_state_bytes = int(context_snapshot["persistent_context_state_bytes"])
    pending_context_bytes = int(sum(np.asarray(item).nbytes for item in context_bank._pending))
    context_state_bytes += pending_context_bytes

    activation_state_bytes = 0
    for state in activation.states.values():
        activation_state_bytes += (
            4 * np.dtype(np.float64).itemsize  # masses, usefulness, activation score
            + np.dtype(np.int64).itemsize     # observed count
            + np.dtype(np.bool_).itemsize     # active flag
            + np.dtype(np.int64).itemsize     # last context slot sentinel/index
        )

    detector_state_bytes = (
        np.dtype(np.float64).itemsize
        + 2 * np.dtype(np.int64).itemsize
    ) if detector is not None else 0

    lifecycle_snapshot = lifecycle.resource_snapshot() if lifecycle is not None else {}
    lifecycle_state_bytes = int(lifecycle_snapshot.get("numeric_buffer_bytes_total", 0))

    control_state_bytes = 0
    control_parameter_bytes = 0
    control_parameter_count = 0
    update_costs = [int(estimator_snapshot["update_outer_product_multiply_adds"])]
    query_costs = [int(estimator_snapshot["query_multiply_adds"])]
    for control in controls:
        snapshot = control.resource_snapshot()
        control_state_bytes += int(snapshot["persistent_state_bytes"])
        control_parameter_bytes += int(snapshot["persistent_parameter_bytes"])
        control_parameter_count += int(snapshot["trainable_parameter_count"])
        update_costs.append(int(snapshot["update_multiply_adds_observed"]))
        query_costs.append(int(snapshot["query_multiply_adds_observed"]))

    revision_parameter_bytes = 0
    revision_parameter_count = 0
    if revision is not None:
        if revision.accepted_operator is not None:
            revision_parameter_bytes += int(revision.accepted_operator.nbytes)
            revision_parameter_count += int(revision.accepted_operator.size)
        if revision.candidate_operator is not None:
            revision_parameter_bytes += int(revision.candidate_operator.nbytes)
            revision_parameter_count += int(revision.candidate_operator.size)

    persistent_state_bytes = (
        int(estimator_snapshot["sufficient_statistic_bytes"])
        + context_state_bytes
        + activation_state_bytes
        + detector_state_bytes
        + lifecycle_state_bytes
        + control_state_bytes
    )
    trainable_parameter_bytes = (
        int(context_snapshot["operator_bytes"])
        + control_parameter_bytes
        + revision_parameter_bytes
    )
    trainable_parameter_count = (
        int(context_snapshot["trainable_parameter_count"])
        + control_parameter_count
        + revision_parameter_count
    )
    envelope = F5_RESOURCE_ENVELOPE
    update_cap = int(envelope["update_multiply_add_cap_per_observed_update"])
    query_cap = int(envelope["query_multiply_add_cap_per_prediction"])
    state_cap = int(envelope["persistent_state_cap_bytes"])
    parameter_cap = int(envelope["trainable_parameter_cap"])
    max_update = max(update_costs, default=0)
    max_query = max(query_costs, default=0)
    return {
        "accounting_scope": "live numeric payloads; Python object/container overhead excluded",
        "components_bytes": {
            "estimator_sufficient_statistics": int(estimator_snapshot["sufficient_statistic_bytes"]),
            "context_metric_slots_and_pending": context_state_bytes,
            "activation_evidence": activation_state_bytes,
            "drift_detector": detector_state_bytes,
            "candidate_lifecycle": lifecycle_state_bytes,
            "C0_C4_control_state": control_state_bytes,
        },
        "persistent_state_bytes": persistent_state_bytes,
        "persistent_state_cap_bytes": state_cap,
        "persistent_state_within_cap": persistent_state_bytes <= state_cap,
        "trainable_parameter_count": trainable_parameter_count,
        "trainable_parameter_bytes": trainable_parameter_bytes,
        "trainable_parameter_cap": parameter_cap,
        "trainable_parameters_within_cap": trainable_parameter_count <= parameter_cap,
        "max_observed_or_declared_update_multiply_adds": max_update,
        "update_multiply_add_cap": update_cap,
        "update_compute_within_cap": max_update <= update_cap,
        "max_observed_or_declared_query_multiply_adds": max_query,
        "query_multiply_add_cap": query_cap,
        "query_compute_within_cap": max_query <= query_cap,
        "resource_envelope_complete": True,
        "resource_envelope_passed": (
            persistent_state_bytes <= state_cap
            and trainable_parameter_count <= parameter_cap
            and max_update <= update_cap
            and max_query <= query_cap
        ),
    }
