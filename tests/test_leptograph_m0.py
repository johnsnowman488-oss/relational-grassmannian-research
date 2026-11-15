"""Analytical invariants and executable references for Hybrid Leptograph M0."""
from __future__ import annotations

import numpy as np
import pytest

from rgm.experiments.leptograph_m0 import CASE_IDS, run_case
from rgm.leptograph.m0 import (
    exact_history_trace, exact_memory_trace, exact_operator_trace,
    factor_routing_operator, route,
)


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_m0_analytical_reference_case_passes(case_id: str) -> None:
    result = run_case(case_id)
    assert result["experiment_id"] == "HYBRID-LEPTOGRAPH-M0"
    assert result["case_id"] == case_id
    assert result["passed"] is True


def test_constant_forcing_memory_matches_closed_form() -> None:
    initial, forcing = np.array([1.0, -2.0]), np.array([0.5, 0.25])
    times = np.array([0.0, 0.5, 2.0])
    actual = exact_memory_trace(initial, 0.4, forcing, times)
    expected = (
        np.exp(-0.4*times)[:, None]*initial
        + ((1.0-np.exp(-0.4*times))/0.4)[:, None]*forcing
    )
    np.testing.assert_allclose(actual, expected, rtol=1e-14, atol=1e-14)


def test_history_trace_preserves_unit_interval_for_constant_evidence() -> None:
    times = np.linspace(0.0, 20.0, 101)
    for initial in (0.0, 0.25, 1.0):
        for evidence in (0.0, 0.4, 1.0):
            result = exact_history_trace(initial, evidence, 0.7, times)
            assert np.all(result >= 0.0) and np.all(result <= 1.0)


def test_dormancy_exactly_decays_history_and_operator() -> None:
    times = np.array([0.0, 1.0, 3.0])
    initial = np.array([[1.0, 2.0], [-0.5, 0.25]])
    actual = exact_operator_trace(
        initial, np.zeros_like(initial), evidence=0.0, initial_history=0.8,
        history_decay=0.3, adaptation_rate=0.5, dormancy_decay=0.4, times=times,
    )
    expected = np.exp(-0.4*times)[:, None, None]*initial
    np.testing.assert_allclose(actual, expected, rtol=1e-14, atol=1e-14)


def test_reactivation_exact_solution_uses_integrated_history() -> None:
    times = np.array([0.0, 1.0, 5.0])
    initial = np.array([[0.1, -0.3], [0.6, 0.2]])
    target = np.array([[1.0, 0.2], [-0.4, 0.8]])
    lam, eta, h0 = 0.35, 0.9, 0.2
    actual = exact_operator_trace(
        initial, target, evidence=1.0, initial_history=h0,
        history_decay=lam, adaptation_rate=eta, dormancy_decay=0.5, times=times,
    )
    integral = times-(1.0-h0)*(1.0-np.exp(-lam*times))/lam
    expected = target+np.exp(-eta*integral)[:, None, None]*(initial-target)
    np.testing.assert_allclose(actual, expected, rtol=1e-14, atol=1e-14)
    assert np.linalg.norm(actual[-1]-target) < np.linalg.norm(initial-target)


def test_heterogeneous_interface_composes_dimensionally_and_routes() -> None:
    encoder = np.arange(8, dtype=float).reshape(4, 2)/7.0
    decoder = np.arange(20, dtype=float).reshape(5, 4)/11.0
    operator = factor_routing_operator(encoder, decoder)
    source = np.array([0.25, -0.75])
    assert operator.shape == (5, 2)
    assert route(operator, source).shape == (5,)
    np.testing.assert_allclose(route(operator, source), decoder@(encoder@source))


@pytest.mark.parametrize("args", [
    (np.zeros(2), 0.0, np.zeros(2), [0.0]),
    (np.zeros(2), -1.0, np.zeros(2), [0.0]),
    (np.zeros(2), 1.0, np.zeros(3), [0.0]),
    (np.zeros(2), 1.0, np.zeros(2), [-1.0]),
])
def test_invalid_memory_reference_inputs_are_rejected(args) -> None:
    with pytest.raises(ValueError):
        exact_memory_trace(*args)


def test_intermediate_evidence_is_not_silently_approximated_in_m0() -> None:
    matrix = np.eye(2)
    with pytest.raises(ValueError, match="exactly 0 or 1"):
        exact_operator_trace(
            matrix, matrix, evidence=0.5, initial_history=0.2,
            history_decay=0.3, adaptation_rate=0.4, dormancy_decay=0.5,
            times=[0.0, 1.0],
        )
