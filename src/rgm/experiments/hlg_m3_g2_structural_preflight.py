"""Structural preflight diagnostics for the frozen HLG-M3 G2 design.

These are implementation-feasibility diagnostics, not scientific results. The
resource calculation is a deliberately conservative lower bound: it counts
only the estimator sufficient statistics, the context metric and one stored
context slot, while omitting activation, detector and candidate-revision state.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from rgm.experiments.hlg_m3_benchmark_contract import (
    F5_RESOURCE_ENVELOPE,
    FACTOR_LEVELS,
    PRIMARY_ATOMS,
)
from rgm.leptograph.m3.context import ContextBank
from rgm.leptograph.m3.estimation import MultiSourceRidge


STRUCTURAL_PREFLIGHT_ID = "HLG-M3-G2-STRUCTURAL-PREFLIGHT-v0.1"
PRIMARY_SOURCE_DIMENSIONS = {"primary": 2, "secondary": 2}
CONTEXT_DIMENSION = 2
TARGET_DIMENSION = 2


def build_structural_preflight_report() -> dict[str, Any]:
    """Measure minimal existing learner buffers and expose context-capacity pressure."""
    estimator = MultiSourceRidge(
        source_dimensions=PRIMARY_SOURCE_DIMENSIONS,
        context_dimension=CONTEXT_DIMENSION,
        target_dimension=TARGET_DIMENSION,
        ridge=1e-3,
    )
    estimator_bytes = int(estimator.resource_snapshot()["sufficient_statistic_bytes"])

    # Count the context metric and one real ContextSlot. This intentionally
    # ignores additional slots, novelty buffers, activation and revision state.
    context_bank = ContextBank(metric=np.eye(CONTEXT_DIMENSION), capacity=8)
    slot_id = context_bank.add_initial(
        np.zeros(CONTEXT_DIMENSION),
        prior_covariance=np.eye(CONTEXT_DIMENSION),
    )
    context_metric_bytes = int(context_bank.metric.nbytes)
    slot = next(item for item in context_bank.slots if item.slot_id == slot_id)
    context_slot_bytes = int(slot.mean.nbytes + slot.scatter.nbytes)

    components = {
        "multi_source_ridge_sufficient_statistics_bytes": estimator_bytes,
        "context_metric_bytes": context_metric_bytes,
        "one_context_slot_mean_and_scatter_bytes": context_slot_bytes,
    }
    numeric_buffer_lower_bound = int(sum(components.values()))
    state_cap = int(F5_RESOURCE_ENVELOPE["persistent_state_cap_bytes"])

    # There are two F6 context prototypes plus four primary relation contexts.
    # This is a pressure diagnostic, not an assertion that every implementation
    # must retain all six simultaneously: a predeclared admission/reuse policy
    # could change the requirement, but none is currently implemented.
    context_labels = ["F6-CONTEXT-A", "F6-CONTEXT-B", *PRIMARY_ATOMS]
    capacity_levels = [int(value) for value in FACTOR_LEVELS["context_bank_capacity"]]

    return {
        "preflight_id": STRUCTURAL_PREFLIGHT_ID,
        "status": (
            "BLOCKED_CURRENT_MINIMUM_EXCEEDS_FROZEN_STATE_CAP"
            if numeric_buffer_lower_bound > state_cap
            else "MINIMUM_NUMERIC_BUFFERS_WITHIN_FROZEN_STATE_CAP"
        ),
        "resource_lower_bound": {
            "components_bytes": components,
            "numeric_buffer_lower_bound_bytes": numeric_buffer_lower_bound,
            "persistent_state_cap_bytes": state_cap,
            "excess_bytes": max(0, numeric_buffer_lower_bound - state_cap),
            "headroom_bytes": max(0, state_cap - numeric_buffer_lower_bound),
            "lower_bound_only": True,
            "excluded_state": [
                "context novelty buffers and additional slots",
                "activation/evidence state",
                "detector state",
                "candidate lifecycle and revision state",
                "other Python-side persistent metadata",
            ],
            "interpretation": (
                "The current estimator plus the minimum context representation "
                "already exceeds the frozen 512-byte persistent-state ceiling; "
                "the omitted state can only increase the total. A redesign or "
                "explicit pre-G2 budget amendment is required."
            ),
        },
        "context_capacity_pressure": {
            "distinct_generated_context_prototypes": context_labels,
            "distinct_prototype_count": len(context_labels),
            "declared_capacity_levels": capacity_levels,
            "can_retain_one_slot_per_prototype": {
                str(capacity): capacity >= len(context_labels)
                for capacity in capacity_levels
            },
            "interpretation": (
                "With one shared non-evicting ContextBank and one slot per "
                "prototype, capacities 2 and 4 cannot retain all six generated "
                "context prototypes. This is a design-pressure finding, not a "
                "claim that all six must be retained simultaneously; a learner "
                "admission/reuse policy must be specified and tested without "
                "using evaluator labels."
            ),
        },
        "scientific_benchmark_executed": False,
        "m3_scientific_validation_complete": False,
        "claim_ceiling": (
            "Structural implementation-feasibility diagnostics only. No G2 "
            "confirmatory run or learner-performance result."
        ),
    }
