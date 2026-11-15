"""Tests for the HLG-M3 foundation mathematical design probes."""
from pathlib import Path

import pytest

from rgm.experiments.leptograph_m3_foundation_campaign import (
    CASE_IDS,
    case_f1,
    case_f2,
    case_f3,
    case_f4,
    case_f5,
    case_f6,
    case_f7,
    run_case,
    verify_result_directory,
    _write_json,
)


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_design_job_runs(case_id: str) -> None:
    result = run_case(case_id)
    assert result["experiment_id"] == "HYBRID-LEPTOGRAPH-M3-FOUNDATION"
    assert result["execution_passed"] is True


def test_prequential_true_and_null_attribution() -> None:
    result = case_f1()
    assert result["true_relation_mean_marginal_contribution"] > 0
    assert abs(result["null_decoy_mean_marginal_contribution"]) < 0.01
    assert result["collinear_conditional_information_rank"] < 2
    assert result["each_prediction_scored_before_current_target_update"]


def test_metric_aware_operator_estimation_is_coordinate_covariant() -> None:
    result = case_f2()
    assert result["relative_operator_recovery_error"] < 0.01
    assert result["relative_general_coordinate_covariance_error"] < 0.01
    assert result["collinear_conditional_information_rank"] == 0


def test_context_retrieval_accepts_abstains_and_flags_novelty() -> None:
    result = case_f3()
    assert result["decisions"] == {
        "separated": "ACCEPT",
        "ambiguous": "ABSTAIN",
        "novel": "NOVEL",
    }
    assert result["general_coordinate_score_difference_error"] < 1e-8


def test_evidence_activation_hysteresis_and_revision_challenge() -> None:
    result = case_f4()
    assert result["evidence_after_no_observation"]["no_negative_event_added"]
    assert result["hysteresis_no_chatter_in_band"]
    assert result["stationary_residual_false_trigger"] is None
    assert result["changed_residual_first_trigger_index"] is not None


def test_memory_controls_have_matched_state_budget_without_winner_claim() -> None:
    result = case_f5()
    assert result["C1_to_C4_state_bytes_matched"]
    assert result["comparison_executed"] is False
    assert result["winner_selected"] is False


def test_integrated_benchmark_manifest_is_leakage_separated() -> None:
    result = case_f6()
    assert result["split_worlds_are_disjoint"]
    assert result["evaluator_truth_and_phase_metadata_excluded_from_learner_inputs"]
    assert result["observation_gap_masks_enforced"]
    assert result["heldout_composition_phase_is_test_only"]


def test_independent_review_checks_metric_norm_and_switching_boundary() -> None:
    result = case_f7()
    assert result["metric_operator_norm_invariance_error"] < 1e-8
    assert result["switching_counterexample_confirmed"]
    assert result["stored_operator_preserved_when_activation_zero"]


def test_aggregate_requires_exact_complete_evidence_and_never_freezes_protocol(tmp_path: Path) -> None:
    for case_id in CASE_IDS:
        _write_json(tmp_path / f"{case_id}.json", run_case(case_id))
    result = verify_result_directory(tmp_path)
    assert result["all_design_jobs_executed"] is True
    assert result["implementation_protocol_frozen"] is False
