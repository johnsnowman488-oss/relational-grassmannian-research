"""Execute deterministic analytical reference cases for Leptograph M0."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.integrate import solve_ivp

from rgm.leptograph.m0 import (
    exact_history_trace, exact_memory_trace, exact_operator_trace,
    factor_routing_operator, route,
)

EXPERIMENT_ID = "HYBRID-LEPTOGRAPH-M0"
SCHEMA_VERSION = "1.0"
CASE_IDS = ("M0-A", "M0-B", "M0-C", "M0-D", "M0-E")


def _integrate(rhs: Callable, initial: np.ndarray, times: np.ndarray) -> np.ndarray:
    """Independent high-accuracy numerical reference using DOP853."""
    result = solve_ivp(
        rhs, (0.0, float(times[-1])), np.asarray(initial, dtype=float).reshape(-1),
        t_eval=times, method="DOP853", rtol=1e-12, atol=1e-13,
    )
    if not result.success or result.y.shape[1] != len(times):
        raise RuntimeError(f"DOP853 reference integration failed: {result.message}")
    return result.y.T


def _error(exact: np.ndarray, numerical: np.ndarray) -> float:
    return float(np.max(np.abs(exact - numerical)))


def _case_a() -> dict[str, Any]:
    t = np.linspace(0.0, 6.0, 31)
    m0 = np.array([1.25, -0.5, 0.2])
    forcing = np.array([0.4, 0.1, -0.3])
    nu = 0.7
    exact = exact_memory_trace(m0, nu, forcing, t)
    numeric = _integrate(lambda _t, m: -nu*m + forcing, m0, t)
    unforced = exact_memory_trace(m0, nu, np.zeros_like(m0), t)
    expected = np.exp(-nu*t)[:, None] * m0[None, :]
    err, unforced_err = _error(exact, numeric), _error(unforced, expected)
    return {
        "case_id": "M0-A", "description": "One mode-level memory state under constant forcing and washout",
        "state_shape": list(m0.shape), "max_abs_error_vs_dop853": err,
        "unforced_closed_form_error": unforced_err, "tolerance": 2e-10,
        "passed": bool(err <= 2e-10 and unforced_err <= 1e-13),
    }


def _case_b() -> dict[str, Any]:
    t = np.linspace(0.0, 5.0, 41)
    encoder = np.array([[1, .2], [0, 1], [.5, -.1], [.2, .3]], dtype=float)
    decoder = np.array([
        [1, 0, .2, -.1], [.1, .8, 0, .2], [-.3, .2, 1, 0],
        [0, .4, -.2, .7], [.5, 0, .1, .3],
    ], dtype=float)
    target = factor_routing_operator(encoder, decoder)
    initial = np.linspace(-.3, .4, target.size).reshape(target.shape)
    eta = .65
    exact = exact_operator_trace(
        initial, target, evidence=1, initial_history=1, history_decay=.4,
        adaptation_rate=eta, dormancy_decay=.3, times=t,
    )
    numeric = _integrate(
        lambda _t, y: (eta*(target-y.reshape(target.shape))).ravel(), initial, t,
    ).reshape(exact.shape)
    received = route(exact[-1], np.array([.6, -1.2]))
    err = _error(exact, numeric)
    return {
        "case_id": "M0-B", "description": "Directed heterogeneous route R2 -> R4 -> R5",
        "source_dimension": 2, "interface_dimension": 4, "target_dimension": 5,
        "operator_shape": list(target.shape), "received_shape": list(received.shape),
        "max_abs_error_vs_dop853": err, "tolerance": 2e-10,
        "passed": bool(err <= 2e-10 and received.shape == (5,)),
    }


def _case_c() -> dict[str, Any]:
    t = np.linspace(0.0, 4.0, 33)
    target_ab = np.array([[1, 0], [0, 1], [1, -1], [.5, .2], [-.3, .7]], dtype=float)
    target_ba = np.array([[.2, -.4, .1, .7, -.2], [-.1, .3, .8, -.5, .6]], dtype=float)
    initial_ab, initial_ba = np.zeros_like(target_ab), np.full_like(target_ba, .15)
    eta_ab, eta_ba = .4, 1.1
    common = {"evidence": 1, "initial_history": 1, "history_decay": .5, "dormancy_decay": .4}
    ab = exact_operator_trace(initial_ab, target_ab, adaptation_rate=eta_ab, times=t, **common)
    ba = exact_operator_trace(initial_ba, target_ba, adaptation_rate=eta_ba, times=t, **common)
    num_ab = _integrate(
        lambda _t, y: (eta_ab*(target_ab-y.reshape(target_ab.shape))).ravel(), initial_ab, t,
    ).reshape(ab.shape)
    num_ba = _integrate(
        lambda _t, y: (eta_ba*(target_ba-y.reshape(target_ba.shape))).ravel(), initial_ba, t,
    ).reshape(ba.shape)
    err = max(_error(ab, num_ab), _error(ba, num_ba))
    asymmetry = float(np.linalg.norm(ba[-1]-ab[-1].T))
    round_trip = float(np.linalg.norm(ba[-1]@ab[-1]-np.eye(2)))
    return {
        "case_id": "M0-C", "description": "Independent forward and reverse directed operators",
        "forward_shape": list(ab[-1].shape), "reverse_shape": list(ba[-1].shape),
        "forward_rate": eta_ab, "reverse_rate": eta_ba,
        "reverse_minus_forward_transpose_frobenius": asymmetry,
        "round_trip_minus_identity_frobenius": round_trip,
        "max_abs_error_vs_dop853": err, "tolerance": 2e-10,
        "passed": bool(err <= 2e-10 and asymmetry > 1e-6 and round_trip > 1e-6),
    }


def _case_d() -> dict[str, Any]:
    t = np.linspace(0.0, 8.0, 41)
    h0, lam, delta = .8, .3, .5
    k0 = np.array([[1, -.5], [.2, .7], [-.3, .4]], dtype=float)
    history = exact_history_trace(h0, 0, lam, t)
    operator = exact_operator_trace(
        k0, np.zeros_like(k0), evidence=0, initial_history=h0,
        history_decay=lam, adaptation_rate=.6, dormancy_decay=delta, times=t,
    )
    y0 = np.concatenate(([h0], k0.ravel()))
    numeric = _integrate(lambda _t, y: np.concatenate(([-lam*y[0]], -delta*y[1:])), y0, t)
    exact = np.column_stack((history, operator.reshape(len(t), -1)))
    err = _error(exact, numeric)
    return {
        "case_id": "M0-D", "description": "Dormancy with independently decaying history and route",
        "history_decay": lam, "operator_decay": delta, "history_endpoint": float(history[-1]),
        "operator_norm_ratio": float(np.linalg.norm(operator[-1])/np.linalg.norm(k0)),
        "max_abs_error_vs_dop853": err, "tolerance": 2e-10,
        "passed": bool(err <= 2e-10 and history[-1] < history[0]),
    }


def _case_e() -> dict[str, Any]:
    dormant_duration, h_before, lam, delta = 6.0, .85, .4, .5
    k_before = np.array([[1, -.2], [.1, .8], [-.4, .3]], dtype=float)
    target = np.array([[.3, .7], [-.6, .2], [.5, -.1]], dtype=float)
    h0 = float(exact_history_trace(h_before, 0, lam, [dormant_duration])[-1])
    k0 = k_before*math.exp(-delta*dormant_duration)
    t, eta = np.linspace(0.0, 12.0, 49), .9
    history = exact_history_trace(h0, 1, lam, t)
    operator = exact_operator_trace(
        k0, target, evidence=1, initial_history=h0, history_decay=lam,
        adaptation_rate=eta, dormancy_decay=delta, times=t,
    )
    y0 = np.concatenate(([h0], k0.ravel()))
    numeric = _integrate(
        lambda _t, y: np.concatenate((
            [lam*(1-y[0])], (eta*y[0]*(target-y[1:].reshape(target.shape))).ravel(),
        )), y0, t,
    )
    exact = np.column_stack((history, operator.reshape(len(t), -1)))
    err = _error(exact, numeric)
    initial_err, final_err = float(np.linalg.norm(k0-target)), float(np.linalg.norm(operator[-1]-target))
    return {
        "case_id": "M0-E", "description": "Reactivation after dormancy under renewed constant evidence",
        "dormant_duration": dormant_duration, "history_at_reactivation": h0,
        "initial_operator_error": initial_err, "final_operator_error": final_err,
        "max_abs_error_vs_dop853": err, "tolerance": 2e-10,
        "passed": bool(err <= 2e-10 and history[-1] > history[0] and final_err < .01*initial_err),
    }


_CASES = {"M0-A": _case_a, "M0-B": _case_b, "M0-C": _case_c, "M0-D": _case_d, "M0-E": _case_e}


def run_case(case_id: str) -> dict[str, Any]:
    if case_id not in _CASES:
        raise ValueError(f"unknown M0 case {case_id!r}; expected {CASE_IDS}")
    result = _CASES[case_id]()
    result.update({"experiment_id": EXPERIMENT_ID, "schema_version": SCHEMA_VERSION, "case_id": case_id})
    return result


def verify_result_directory(directory: Path) -> dict[str, Any]:
    cases = []
    for case_id in CASE_IDS:
        path = directory / f"{case_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"missing M0 evidence file: {path}")
        result = json.loads(path.read_text(encoding="utf-8"))
        if result.get("experiment_id") != EXPERIMENT_ID or result.get("case_id") != case_id:
            raise ValueError(f"invalid experiment/case identity in {path}")
        if result.get("passed") is not True:
            raise AssertionError(f"M0 case {case_id} did not pass")
        cases.append({"case_id": case_id, "passed": True})
    return {
        "experiment_id": EXPERIMENT_ID, "schema_version": SCHEMA_VERSION,
        "case_ids": list(CASE_IDS), "case_count": len(cases),
        "all_cases_passed": True, "cases": cases,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False)+"\n").encode()
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
    if result.get("passed") is False or result.get("all_cases_passed") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
