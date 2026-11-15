"""Regression tests for the five targeted HLG-M3 foundation refinements."""
from rgm.experiments.leptograph_m3_refinements import CASE_IDS, run_case

def test_all_five_refinement_jobs_pass():
    for case in CASE_IDS:
        result=run_case(case)
        assert result["execution_passed"] is True, result

def test_context_absolute_score_is_coordinate_invariant():
    r=run_case("R1")
    assert r["invariance_error"] < 1e-10

def test_prequential_probe_challenges_correlated_sources():
    r=run_case("R2")
    assert [x["source_correlation"] for x in r["correlation_sweep"]]==[0.0,.5,.9,.99]
    assert r["preupdate_target_perturbation_prediction_error"] < 1e-12
    assert r["next_prediction_responds_after_update"]

def test_activation_is_stateful_across_threshold_band():
    r=run_case("R3")
    assert r["hysteresis_sequence_matches_expected"]

def test_revision_detector_is_calibrated_and_candidate_gated():
    r=run_case("R4")
    assert r["stationary_false_alarm_rate"] <= .08
    assert r["shifted_stream_detection_rate"] >= .9
    assert r["rejected_nonimproving_candidate"]

def test_learner_interface_and_state_budget_are_explicit():
    r=run_case("R5")
    assert r["forbidden_metadata_exposed"] == []
    assert r["state_bytes_matched"]
    assert r["resource_accounting_contract"]["pareto_match_required"]
