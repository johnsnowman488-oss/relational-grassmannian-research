"""Multi-route stability, conditioning and information analysis for HLG-M2."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .m1 import compose_routes, operator_diagnostics

FloatArray = NDArray[np.float64]
CASE_IDS = ("M2-A", "M2-B", "M2-C", "M2-D", "M2-E", "M2-F")


def _matrix(value: ArrayLike, *, name: str) -> FloatArray:
    result = np.asarray(value, dtype=np.float64)
    if result.ndim != 2 or min(result.shape, default=0) < 1:
        raise ValueError(f"{name} must be a non-empty two-dimensional matrix")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    return result


def _routes(values: Sequence[ArrayLike], *, name: str = "routes") -> list[FloatArray]:
    if len(values) < 1:
        raise ValueError(f"{name} must contain at least one operator")
    matrices = [_matrix(value, name=f"{name}[{i}]") for i, value in enumerate(values)]
    source_dim = matrices[0].shape[1]
    if any(item.shape[1] != source_dim for item in matrices):
        raise ValueError("all parallel routes must have the same source dimension")
    return matrices


def compose_path(*operators: ArrayLike) -> FloatArray:
    """Compose a single directed path in traversal order."""
    return compose_routes(*operators)


def sum_parallel_routes(*operators: ArrayLike) -> FloatArray:
    """Sum route maps that share the same source and target spaces."""
    matrices = _routes(operators)
    target_shape = matrices[0].shape
    if any(item.shape != target_shape for item in matrices):
        raise ValueError("summed parallel routes must share source and target dimensions")
    return np.sum(np.stack(matrices, axis=0), axis=0)


def stack_parallel_routes(*operators: ArrayLike) -> FloatArray:
    """Keep route outputs as separate observations in a direct-sum codomain."""
    matrices = _routes(operators)
    return np.concatenate(matrices, axis=0)


def multi_route_diagnostics(*operators: ArrayLike) -> dict[str, Any]:
    """Compare coalesced and separately observed parallel route banks.

    The coherence ratio is ||sum K_p||_2 / sum ||K_p||_2 and lies in [0, 1]
    up to floating-point tolerance. It is an operator diagnostic, not a
    probability or information-theoretic quantity.
    """
    matrices = _routes(operators)
    summed = sum_parallel_routes(*matrices)
    stacked = stack_parallel_routes(*matrices)
    route_norms = [float(np.linalg.norm(item, ord=2)) for item in matrices]
    total_norm = float(sum(route_norms))
    aggregate_norm = float(np.linalg.norm(summed, ord=2))
    coherence = aggregate_norm / total_norm if total_norm > 0.0 else 1.0
    coherence = min(1.0, max(0.0, coherence))
    return {
        "route_count": len(matrices),
        "source_dimension": int(matrices[0].shape[1]),
        "target_dimension": int(matrices[0].shape[0]),
        "route_operator_norms": route_norms,
        "sum_of_route_operator_norms": total_norm,
        "coalesced_operator_norm": aggregate_norm,
        "coherence_ratio": coherence,
        "cancellation_fraction": 1.0 - coherence,
        "coalesced": operator_diagnostics(summed),
        "separately_observed": operator_diagnostics(stacked),
        "coalesced_operator": summed.tolist(),
        "stacked_operator_shape": list(stacked.shape),
    }


def route_erasure_diagnostics(*operators: ArrayLike) -> dict[str, Any]:
    """Measure stacked-observation rank/conditioning after each single-route loss."""
    matrices = _routes(operators)
    if len(matrices) < 2:
        raise ValueError("at least two routes are required for route-erasure analysis")
    cases = []
    for erased in range(len(matrices)):
        remaining = [item for index, item in enumerate(matrices) if index != erased]
        info = operator_diagnostics(stack_parallel_routes(*remaining))
        cases.append({
            "erased_route_index": erased,
            "rank": info["rank"],
            "nullity": info["nullity"],
            "effective_condition_number": info["effective_condition_number"],
        })
    return {
        "route_count": len(matrices),
        "single_erasure_cases": cases,
        "minimum_rank_after_single_erasure": min(item["rank"] for item in cases),
        "maximum_nullity_after_single_erasure": max(item["nullity"] for item in cases),
        "worst_finite_condition_after_single_erasure": max(
            (item["effective_condition_number"] for item in cases
             if item["effective_condition_number"] is not None),
            default=None,
        ),
    }


def assemble_network_operator(
    node_dimensions: Mapping[str, int],
    edges: Sequence[tuple[str, str, ArrayLike]],
) -> FloatArray:
    """Assemble a synchronous block operator from (source, target, K) edges.

    Parallel edges add in the corresponding target/source block. Node order
    follows the insertion order of node_dimensions.
    """
    if not isinstance(node_dimensions, Mapping) or not node_dimensions:
        raise ValueError("node_dimensions must be a non-empty mapping")
    names = list(node_dimensions)
    dimensions: dict[str, int] = {}
    for name, dimension in node_dimensions.items():
        if not isinstance(name, str) or not name:
            raise ValueError("node names must be non-empty strings")
        if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension < 1:
            raise ValueError(f"dimension for node {name!r} must be a positive integer")
        dimensions[name] = dimension
    offsets: dict[str, slice] = {}
    cursor = 0
    for name in names:
        offsets[name] = slice(cursor, cursor + dimensions[name])
        cursor += dimensions[name]
    result = np.zeros((cursor, cursor), dtype=np.float64)
    for index, edge in enumerate(edges):
        if len(edge) != 3:
            raise ValueError(f"edge[{index}] must be (source, target, operator)")
        source, target, value = edge
        if source not in dimensions or target not in dimensions:
            raise ValueError(f"edge[{index}] references an unknown node")
        operator = _matrix(value, name=f"edge[{index}] operator")
        expected = (dimensions[target], dimensions[source])
        if operator.shape != expected:
            raise ValueError(
                f"edge[{index}] operator must have shape {expected}, got {operator.shape}"
            )
        result[offsets[target], offsets[source]] += operator
    return result


def feedback_diagnostics(transition: ArrayLike, *, horizon: int = 12) -> dict[str, Any]:
    """Analyse x[k+1] = A x[k] by spectral and finite-horizon norm criteria.

    For a fixed finite-dimensional discrete-time LTI system, rho(A) < 1 is
    necessary and sufficient for asymptotic stability. ||A||_2 < 1 is
    sufficient but not necessary. The finite-horizon peak captures transient
    amplification and is not an asymptotic stability test.
    """
    matrix = _matrix(transition, name="transition")
    if matrix.shape[0] != matrix.shape[1]:
        raise ValueError("transition must be square")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 0:
        raise ValueError("horizon must be a non-negative integer")
    if horizon > 1000:
        raise ValueError("horizon must not exceed 1000")
    eigenvalues = np.linalg.eigvals(matrix)
    spectral_radius = float(np.max(np.abs(eigenvalues))) if eigenvalues.size else 0.0
    induced_norm = float(np.linalg.norm(matrix, ord=2))
    power = np.eye(matrix.shape[0], dtype=np.float64)
    power_norms = [float(np.linalg.norm(power, ord=2))]
    for _ in range(horizon):
        power = matrix @ power
        power_norms.append(float(np.linalg.norm(power, ord=2)))
    peak = max(power_norms)
    return {
        "dimension": int(matrix.shape[0]),
        "spectral_radius": spectral_radius,
        "asymptotically_stable": bool(spectral_radius < 1.0),
        "stability_margin": float(1.0 - spectral_radius),
        "induced_2_norm": induced_norm,
        "one_step_contractive": bool(induced_norm < 1.0),
        "transient_horizon": horizon,
        "power_2_norms": power_norms,
        "peak_transient_gain": peak,
        "peak_transient_step": int(power_norms.index(peak)),
        "eigenvalues_real_imag": [
            [float(value.real), float(value.imag)] for value in eigenvalues
        ],
    }


def _case_a() -> dict[str, Any]:
    routes = (
        np.array([[1.0, 0.0], [0.0, 0.2], [0.0, 0.0]]),
        np.array([[0.5, 0.0], [0.0, 0.1], [0.0, 0.0]]),
        np.array([[-0.2, 0.0], [0.0, 0.0], [0.0, 0.0]]),
    )
    info = multi_route_diagnostics(*routes)
    passed = (
        info["route_count"] == 3
        and 0.0 < info["coherence_ratio"] < 1.0
        and 0.0 < info["cancellation_fraction"] < 1.0
        and info["coalesced"]["rank"] == 2
    )
    return {
        "case_id": "M2-A",
        "description": "Multi-path operator interference and coalescence",
        **info,
        "tolerance": 2e-12,
        "passed": bool(passed),
    }


def _case_b() -> dict[str, Any]:
    identity = np.eye(3)
    info = multi_route_diagnostics(identity, -identity)
    passed = (
        info["coalesced"]["rank"] == 0
        and info["separately_observed"]["rank"] == 3
        and info["separately_observed"]["nullity"] == 0
        and info["cancellation_fraction"] == 1.0
    )
    return {
        "case_id": "M2-B",
        "description": "Exact cancellation under summation versus information retention under stacking",
        "summed_rank": info["coalesced"]["rank"],
        "stacked_rank": info["separately_observed"]["rank"],
        "stacked_nullity": info["separately_observed"]["nullity"],
        "cancellation_fraction": info["cancellation_fraction"],
        "passed": bool(passed),
    }


def _case_c() -> dict[str, Any]:
    first = np.diag([1.0, 0.1, 0.01])
    second = np.diag([1.0, 0.5, 0.1])
    composite = compose_path(first, second)
    first_info = operator_diagnostics(first)
    second_info = operator_diagnostics(second)
    composite_info = operator_diagnostics(composite)
    product_bound = first_info["effective_condition_number"] * second_info["effective_condition_number"]
    observed = composite_info["effective_condition_number"]
    passed = bool(
        observed >= max(first_info["effective_condition_number"], second_info["effective_condition_number"])
        and observed <= product_bound * (1.0 + 1e-12)
        and composite_info["rank"] == 3
    )
    return {
        "case_id": "M2-C",
        "description": "Conditioning accumulation in a heterogeneous route cascade",
        "operator_shapes": [list(first.shape), list(second.shape)],
        "composite_singular_values": composite_info["singular_values"],
        "first_condition": first_info["effective_condition_number"],
        "second_condition": second_info["effective_condition_number"],
        "composite_condition": observed,
        "product_condition_upper_bound": product_bound,
        "passed": passed,
    }


def _case_d() -> dict[str, Any]:
    transition = np.array([[0.8, 6.0], [0.0, 0.8]])
    info = feedback_diagnostics(transition, horizon=12)
    passed = (
        info["asymptotically_stable"] is True
        and info["one_step_contractive"] is False
        and info["peak_transient_gain"] > 1.0
        and abs(info["spectral_radius"] - 0.8) < 1e-12
    )
    return {
        "case_id": "M2-D",
        "description": "Stable non-normal feedback with finite-horizon transient amplification",
        **info,
        "passed": bool(passed),
    }


def _case_e() -> dict[str, Any]:
    dimensions = {"alpha": 2, "beta": 3, "gamma": 2}
    edges = [
        ("alpha", "alpha", 0.20 * np.eye(2)),
        ("beta", "beta", 0.15 * np.eye(3)),
        ("gamma", "gamma", 0.10 * np.eye(2)),
        ("alpha", "beta", 0.10 * np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])),
        ("beta", "gamma", 0.10 * np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])),
        ("gamma", "alpha", 0.10 * np.eye(2)),
    ]
    transition = assemble_network_operator(dimensions, edges)
    info = feedback_diagnostics(transition, horizon=16)
    passed = transition.shape == (7, 7) and info["asymptotically_stable"] is True and info["spectral_radius"] < 0.5
    return {
        "case_id": "M2-E",
        "description": "Global stability of a heterogeneous 2-3-2 block network",
        "node_dimensions": dimensions,
        "edge_count": len(edges),
        "transition_shape": list(transition.shape),
        **info,
        "passed": bool(passed),
    }


def _case_f() -> dict[str, Any]:
    routes = (
        np.array([[1.0, 0.0], [0.0, 0.0], [0.0, 0.0]]),
        np.array([[0.0, 0.0], [0.0, 1.0], [0.0, 0.0]]),
        np.array([[1.0, 1.0], [1.0, -1.0], [0.0, 1.0]]),
    )
    baseline = operator_diagnostics(stack_parallel_routes(*routes))
    erasure = route_erasure_diagnostics(*routes)
    passed = (
        baseline["rank"] == 2
        and baseline["nullity"] == 0
        and erasure["minimum_rank_after_single_erasure"] == 2
        and erasure["maximum_nullity_after_single_erasure"] == 0
    )
    return {
        "case_id": "M2-F",
        "description": "Single-route erasure resilience of a separately observed route bank",
        "baseline_rank": baseline["rank"],
        "baseline_nullity": baseline["nullity"],
        **erasure,
        "passed": bool(passed),
    }


_CASES = {
    "M2-A": _case_a,
    "M2-B": _case_b,
    "M2-C": _case_c,
    "M2-D": _case_d,
    "M2-E": _case_e,
    "M2-F": _case_f,
}


def run_case(case_id: str) -> dict[str, Any]:
    """Execute one frozen deterministic M2 reference case."""
    if case_id not in _CASES:
        raise ValueError(f"unknown M2 case {case_id!r}; expected one of {CASE_IDS}")
    result = _CASES[case_id]()
    return {
        "experiment_id": "HYBRID-LEPTOGRAPH-M2",
        "schema_version": "1.0",
        "case_id": case_id,
        "passed": bool(result["passed"]),
        **{key: value for key, value in result.items() if key not in ("case_id", "passed")},
    }
