"""Tests for the pre-implementation Leptograph M3 mathematical probes."""
from pathlib import Path

import pytest

from rgm.experiments.leptograph_m3_preflight import (
    CASE_IDS, case_a, case_b, case_c, case_d, case_e, case_f, case_g,
    run_case, verify_result_directory, _write_json,
)


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_each_preflight_case_executes(case_id: str) -> None:
    result = run_case(case_id)
    assert result["experiment_id"] == "HYBRID-LEPTOGRAPH-M3-PREFLIGHT"
    assert result["execution_passed"] is True


def test_piecewise_history_matches_independent_integrator() -> None:
    result = case_a()
    assert result["max_abs_error_vs_dop853"] <= result["tolerance"]
    assert result["history_in_unit_interval"] is True
    assert result["piecewise_response_is_monotone_toward_each_constant_evidence"] is True


def test_history_and_operator_have_distinct_decay_timescales() -> None:
    result = case_b()
    assert result["history_half_life"] != pytest.approx(result["operator_half_life"])


def test_context_probe_detects_near_duplicate_ambiguity() -> None:
    result = case_c()
    assert result["separated_query_selects_correct_context"] is True
    assert result["near_duplicate_ambiguity_detected"] is True
    assert result["design_status"] == "DIAGNOSTIC_ONLY"


def test_adaptive_operator_stays_in_declared_norm_ball() -> None:
    result = case_d()
    assert result["maximum_observed_operator_spectral_norm"] <= 1.0 + 2e-9


def test_memory_architecture_comparison_is_explicitly_blocked() -> None:
    result = case_e()
    assert result["comparison_executed"] is False
    assert result["design_status"] == "BLOCKED_PENDING_CONTROL_DEFINITION"


def test_retained_history_improves_same_target_reacquisition_probe() -> None:
    result = case_f()
    assert result["retained_history_final_route_error"] < result["reset_history_final_route_error"]


def test_switching_counterexample_defeats_per_step_spectral_test() -> None:
    result = case_g()
    assert result["rho_A1"] < 1.0
    assert result["rho_A2"] < 1.0
    assert result["rho_A2A1"] > 1.0


def test_aggregate_requires_exact_complete_evidence_set(tmp_path: Path) -> None:
    for case_id in CASE_IDS:
        _write_json(tmp_path / f"{case_id}.json", run_case(case_id))
    result = verify_result_directory(tmp_path)
    assert result["all_cases_executed"] is True
    assert result["blocked_design_cases"] == ["M3-E"]
    assert result["scientific_ready_for_m3_implementation"] is False
