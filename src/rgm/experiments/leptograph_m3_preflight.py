"""Pre-implementation analytical probes for Hybrid Leptograph M3.

This module is deliberately not an M3 runtime or production learning implementation.
It evaluates small reference models against closed-form expectations and records
known design blockers so that passing CI cannot be mistaken for M3 approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

EXPERIMENT_ID = "HYBRID-LEPTOGRAPH-M3-PREFLIGHT"
SCHEMA_VERSION = "1.0"
CASE_IDS = ("M3-A", "M3-B", "M3-C", "M3-D", "M3-E", "M3-F", "M3-G")
TOL = 2e-10


def _integrate_piecewise_history(
    initial: float, rate: float, segments: list[tuple[float, float]], samples: int = 21
) -> tuple[list[tuple[float, float]], float]:
    """Compare exact piecewise-constant history updates with segmentwise DOP853."""
    h = float(initial)
    elapsed = 0.0
    points: list[tuple[float, float]] = [(0.0, h)]
    max_error = 0.0
    for evidence, duration in segments:
        grid = np.linspace(0.0, duration, samples)
        exact = evidence + (h - evidence) * np.exp(-rate * grid)
        numeric = solve_ivp(
            lambda _t, y: [rate * (evidence - y[0])],
            (0.0, duration),
            [h],
            t_eval=grid,
            method="DOP853",
            rtol=1e-12,
            atol=1e-13,
        )
        if not numeric.success:
            raise RuntimeError(numeric.message)
        max_error = max(max_error, float(np.max(np.abs(exact - numeric.y[0]))))
        for local_t, value in zip(grid[1:], exact[1:]):
            points.append((elapsed + float(local_t), float(value)))
        h = float(exact[-1])
        elapsed += duration
    return points, max_error


def case_a() -> dict[str, Any]:
    lam = 0.45
    segments = [(1.0, 1.5), (0.0, 2.0), (0.65, 0.8), (0.0, 1.2), (1.0, 1.0)]
    points, error = _integrate_piecewise_history(0.2, lam, segments)
    values = np.asarray([value for _, value in points])
    bounded = bool(np.min(values) >= -1e-13 and np.max(values) <= 1.0 + 1e-13)
    monotone_segments = True
    offset = 0
    for evidence, _duration in segments:
        local = values[offset : offset + 21]
        delta = local - evidence
        if delta[0] > 0:
            monotone_segments &= bool(np.all(np.diff(local) <= 1e-12))
        elif delta[0] < 0:
            monotone_segments &= bool(np.all(np.diff(local) >= -1e-12))
        offset += 20
    return {
        "case_id": "M3-A",
        "description": "Piecewise evidence accumulation and historical relational trace",
        "segments_evidence_duration": segments,
        "history_initial": 0.2,
        "history_final": float(values[-1]),
        "history_min": float(np.min(values)),
        "history_max": float(np.max(values)),
        "max_abs_error_vs_dop853": error,
        "tolerance": TOL,
        "history_in_unit_interval": bounded,
        "piecewise_response_is_monotone_toward_each_constant_evidence": monotone_segments,
        "passed": bool(error <= TOL and bounded and monotone_segments),
        "interpretation": "Validates the scalar history ODE for piecewise-constant externally supplied evidence; does not validate how evidence is inferred.",
    }


def case_b() -> dict[str, Any]:
    h0, k0, lam, delta = 0.9, 0.8, 0.35, 0.6
    t_h = math.log(2.0) / lam
    t_k = math.log(2.0) / delta
    h_half = h0 * math.exp(-lam * t_h)
    k_half = k0 * math.exp(-delta * t_k)
    grid = np.linspace(0.0, 10.0, 101)
    h = h0 * np.exp(-lam * grid)
    k = k0 * np.exp(-delta * grid)
    expected_h = h0 * math.exp(-lam * grid[-1])
    expected_k = k0 * math.exp(-delta * grid[-1])
    error = max(abs(float(h[-1]) - expected_h), abs(float(k[-1]) - expected_k))
    passed = (
        abs(h_half - h0 / 2.0) <= 1e-14
        and abs(k_half - k0 / 2.0) <= 1e-14
        and abs(t_h - t_k) > 1e-3
        and np.all(np.diff(h) < 0.0)
        and np.all(np.diff(k) < 0.0)
        and error <= 1e-14
    )
    return {
        "case_id": "M3-B",
        "description": "Independent history and route dormancy decay rates",
        "history_half_life": t_h,
        "operator_half_life": t_k,
        "history_at_its_half_life": h_half,
        "operator_at_its_half_life": k_half,
        "history_final_at_t10": float(h[-1]),
        "operator_final_at_t10": float(k[-1]),
        "decay_rates_are_independent": True,
        "passed": bool(passed),
        "interpretation": "The model has two distinct decay timescales; their relationship must be selected or estimated rather than silently equated.",
    }


def _context_score(query: np.ndarray, stored: np.ndarray, history: float, sigma: float) -> float:
    distance2 = float(np.sum((query - stored) ** 2))
    return history * math.exp(-distance2 / (2.0 * sigma * sigma))


def case_c() -> dict[str, Any]:
    """Diagnostic only: a Gaussian context kernel is a candidate, not a frozen rule."""
    sigma = 0.12
    separate_a = np.array([1.0, 0.0])
    separate_b = np.array([0.0, 1.0])
    separate_scores = {
        "A": _context_score(separate_a, separate_a, 0.9, sigma),
        "B": _context_score(separate_a, separate_b, 0.85, sigma),
    }
    near_a = np.array([1.0, 0.0])
    near_b = np.array([0.98, 0.02])
    ambiguous_query = 0.5 * (near_a + near_b)
    ambiguous_scores = {
        "A": _context_score(ambiguous_query, near_a, 0.9, sigma),
        "B": _context_score(ambiguous_query, near_b, 0.88, sigma),
    }
    sep_margin = abs(separate_scores["A"] - separate_scores["B"])
    amb_margin = abs(ambiguous_scores["A"] - ambiguous_scores["B"])
    return {
        "case_id": "M3-C",
        "description": "Context-conditioned relational retrieval discrimination probe",
        "candidate_kernel": "history multiplied by Gaussian similarity",
        "kernel_bandwidth": sigma,
        "separated_context_scores": separate_scores,
        "separated_context_margin": sep_margin,
        "separated_query_selects_correct_context": bool(separate_scores["A"] > separate_scores["B"]),
        "near_duplicate_context_scores": ambiguous_scores,
        "near_duplicate_context_margin": amb_margin,
        "near_duplicate_ambiguity_detected": bool(amb_margin < 0.05),
        "passed": bool(separate_scores["A"] > separate_scores["B"] and amb_margin < 0.05),
        "design_status": "DIAGNOSTIC_ONLY",
        "interpretation": "A candidate similarity rule can retrieve cleanly separated contexts but becomes ambiguous for near-duplicate contexts. Context representation, calibration, and reject/abstain behaviour remain unspecified.",
    }


def _spectral_norm(matrix: np.ndarray) -> float:
    return float(np.linalg.norm(matrix, ord=2))


def case_d() -> dict[str, Any]:
    """Numerically challenge the M0 adaptive-route law under switched bounded targets."""
    lam, eta, delta = 0.5, 0.9, 0.4
    radius = 1.0
    initial_k = np.array([[0.25, -0.10], [0.15, 0.20], [-0.10, 0.05]], dtype=float)
    targets = [
        np.array([[0.30, 0.10], [-0.20, 0.25], [0.10, -0.15]], dtype=float),
        np.array([[-0.15, 0.20], [0.30, 0.10], [0.05, 0.20]], dtype=float),
        np.zeros((3, 2), dtype=float),
        np.array([[0.10, -0.20], [0.15, 0.25], [-0.20, 0.10]], dtype=float),
    ]
    segments = [(1.0, 1.5, targets[0]), (0.0, 1.0, targets[1]), (0.65, 1.2, targets[2]), (1.0, 1.5, targets[3])]
    h = 0.25
    k = initial_k.copy()
    max_norm = _spectral_norm(k)
    min_h, max_h = h, h
    max_error = 0.0
    for evidence, duration, target in segments:
        if _spectral_norm(target) > radius + 1e-12:
            raise AssertionError("reference target exceeds the declared operator norm ball")
        y0 = np.concatenate(([h], k.reshape(-1)))
        grid = np.linspace(0.0, duration, 31)

        def rhs(_t: float, y: np.ndarray) -> np.ndarray:
            history = float(y[0])
            operator = y[1:].reshape(k.shape)
            dh = lam * (evidence - history)
            dk = eta * history * evidence * (target - operator) - delta * (1.0 - evidence) * operator
            return np.concatenate(([dh], dk.reshape(-1)))

        result = solve_ivp(rhs, (0.0, duration), y0, t_eval=grid, method="DOP853", rtol=1e-12, atol=1e-13)
        if not result.success:
            raise RuntimeError(result.message)
        exact_h = evidence + (h - evidence) * np.exp(-lam * grid)
        for column in result.y.T:
            hk = float(column[0])
            kk = column[1:].reshape(k.shape)
            max_norm = max(max_norm, _spectral_norm(kk))
            min_h, max_h = min(min_h, hk), max(max_h, hk)
        max_error = max(max_error, float(np.max(np.abs(result.y[0] - exact_h))))
        h = float(result.y[0, -1])
        k = result.y[1:, -1].reshape(k.shape)

    passed = max_norm <= radius + 2e-9 and min_h >= -2e-10 and max_h <= 1.0 + 2e-10 and max_error <= TOL
    return {
        "case_id": "M3-D",
        "description": "Boundedness probe for history-gated adaptive routing under bounded target switching",
        "history_decay_rate": lam,
        "adaptation_rate": eta,
        "dormancy_decay_rate": delta,
        "declared_operator_norm_radius": radius,
        "maximum_observed_operator_spectral_norm": max_norm,
        "history_min": min_h,
        "history_max": max_h,
        "history_closed_form_max_error": max_error,
        "segments": [{"evidence": s, "duration": d, "target_spectral_norm": _spectral_norm(t)} for s, d, t in segments],
        "passed": bool(passed),
        "interpretation": "Numerically consistent with the invariant norm-ball argument for bounded targets; this is not a proof of coupled network stability.",
    }


def case_e() -> dict[str, Any]:
    """Report a design blocker rather than invent an unfair memory comparison."""
    return {
        "case_id": "M3-E",
        "description": "Memory architecture comparison readiness audit",
        "passed": True,
        "design_status": "BLOCKED_PENDING_CONTROL_DEFINITION",
        "comparison_executed": False,
        "missing_specifications": [
            "A mathematically explicit unified-memory update law",
            "A shared state-dimension and precision budget for separate versus unified memory",
            "A common task distribution and observation protocol",
            "A rule for measuring memory interference independently of readout choice",
            "A declared treatment of mode memory versus relationship history",
        ],
        "interpretation": "No architecture winner can be reported. A capacity-matched comparison cannot be run until the unified-memory control and equal-resource budget are specified.",
    }


def _simulate_scalar_episode(initial_h: float, initial_k: float, reset_history_at_recall: bool) -> tuple[float, float]:
    lam, eta, delta = 0.4, 1.0, 0.4
    h, k = float(initial_h), float(initial_k)
    episodes = [(1.0, 1.0, 3.0), (0.0, 0.0, 3.0), (1.0, 1.0, 2.0)]
    for index, (evidence, target, duration) in enumerate(episodes):
        if index == 2 and reset_history_at_recall:
            h = 0.0
        y0 = np.array([h, k], dtype=float)
        result = solve_ivp(
            lambda _t, y: np.array([
                lam * (evidence - y[0]),
                eta * y[0] * evidence * (target - y[1]) - delta * (1.0 - evidence) * y[1],
            ]),
            (0.0, duration),
            y0,
            t_eval=[duration],
            method="DOP853",
            rtol=1e-12,
            atol=1e-13,
        )
        if not result.success:
            raise RuntimeError(result.message)
        h, k = map(float, result.y[:, -1])
    return abs(1.0 - k), h


def case_f() -> dict[str, Any]:
    retained_error, retained_h = _simulate_scalar_episode(0.0, 0.0, False)
    reset_error, reset_h = _simulate_scalar_episode(0.0, 0.0, True)
    reduction = (reset_error - retained_error) / reset_error if reset_error else 0.0
    return {
        "case_id": "M3-F",
        "description": "Sequential acquire-dormant-reactivate reference task",
        "task_sequence": ["acquire target route", "remove evidence and enter dormancy", "reactivate the same target"],
        "retained_history_final": retained_h,
        "reset_history_final": reset_h,
        "retained_history_final_route_error": retained_error,
        "reset_history_final_route_error": reset_error,
        "relative_error_reduction_from_retained_history": reduction,
        "passed": bool(retained_error < reset_error and reduction > 0.05),
        "interpretation": "A narrow synthetic demonstration that residual history can accelerate reacquisition under this update law; it is not evidence of relation discovery, context transfer, or general learning.",
    }


def case_g() -> dict[str, Any]:
    """Provide a counterexample to per-step spectral-radius stability reasoning."""
    a1 = np.array([[0.8, 1.0], [0.0, 0.8]], dtype=float)
    a2 = np.array([[0.8, 0.0], [1.0, 0.8]], dtype=float)
    product = a2 @ a1
    rho1 = float(np.max(np.abs(np.linalg.eigvals(a1))))
    rho2 = float(np.max(np.abs(np.linalg.eigvals(a2))))
    rho_product = float(np.max(np.abs(np.linalg.eigvals(product))))
    powers = [np.linalg.norm(np.linalg.matrix_power(product, n), ord=2) for n in range(1, 8)]
    passed = rho1 < 1.0 and rho2 < 1.0 and rho_product > 1.0 and powers[-1] > powers[0]
    return {
        "case_id": "M3-G",
        "description": "Switched-system counterexample: individually Schur operators with unstable two-step product",
        "rho_A1": rho1,
        "rho_A2": rho2,
        "two_step_product": product.tolist(),
        "rho_A2A1": rho_product,
        "product_power_norms_1_to_7": [float(v) for v in powers],
        "per_operator_spectral_test_would_be_misleading": bool(rho1 < 1.0 and rho2 < 1.0 and rho_product > 1.0),
        "passed": bool(passed),
        "interpretation": "The counterexample rules out using rho(K(t))<1 at each instant as a general proof of stability under arbitrary switching. A common Lyapunov function, joint spectral radius, dwell-time restriction, or another explicit switching condition is needed for stronger claims.",
    }


_CASES = {
    "M3-A": case_a,
    "M3-B": case_b,
    "M3-C": case_c,
    "M3-D": case_d,
    "M3-E": case_e,
    "M3-F": case_f,
    "M3-G": case_g,
}


def run_case(case_id: str) -> dict[str, Any]:
    if case_id not in _CASES:
        raise ValueError(f"unknown M3 preflight case {case_id!r}; expected {CASE_IDS}")
    result = _CASES[case_id]()
    result.update({
        "experiment_id": EXPERIMENT_ID,
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "execution_passed": result.get("passed") is True,
    })
    return result


def verify_result_directory(directory: Path) -> dict[str, Any]:
    cases = []
    for case_id in CASE_IDS:
        path = directory / f"{case_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"missing M3 preflight evidence file: {path}")
        result = json.loads(path.read_text(encoding="utf-8"))
        if (
            result.get("experiment_id") != EXPERIMENT_ID
            or result.get("case_id") != case_id
            or result.get("execution_passed") is not True
        ):
            raise AssertionError(f"invalid or failed M3 preflight evidence: {path}")
        cases.append({
            "case_id": case_id,
            "execution_passed": True,
            "design_status": result.get("design_status", "EXECUTED"),
        })
    blocked = [
        case["case_id"] for case in cases
        if case["design_status"] == "BLOCKED_PENDING_CONTROL_DEFINITION"
    ]
    return {
        "experiment_id": EXPERIMENT_ID,
        "schema_version": SCHEMA_VERSION,
        "case_ids": list(CASE_IDS),
        "case_count": len(cases),
        "all_cases_executed": True,
        "blocked_design_cases": blocked,
        "scientific_ready_for_m3_implementation": len(blocked) == 0,
        "campaign_decision": (
            "READY_FOR_IMPLEMENTATION_REVIEW"
            if not blocked
            else "PREIMPLEMENTATION_ONLY_NOT_READY_FOR_M3_IMPLEMENTATION"
        ),
        "cases": cases,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASE_IDS)
    parser.add_argument("--verify-result-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (args.case is None) == (args.verify_result_dir is None):
        parser.error("specify exactly one of --case or --verify-result-dir")
    result = run_case(args.case) if args.case else verify_result_directory(args.verify_result_dir)
    digest = _write_json(args.output, result)
    print(json.dumps({"output": str(args.output), "sha256": digest, **result}, sort_keys=True))
    if result.get("passed") is False or result.get("all_cases_executed") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
