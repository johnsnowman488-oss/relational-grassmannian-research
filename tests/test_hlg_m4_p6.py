import numpy as np
import pytest
from rgm.leptograph.m4.stability import CoupledAdaptiveSystem, AdaptiveMode
from rgm.experiments.hlg_m4_job3 import run

def test_bounded_input_synchronous_coupled_model_remains_in_declared_envelope():
    rng=np.random.default_rng(4); model=CoupledAdaptiveSystem()
    for _ in range(500): model.step(rng.uniform(-1,1,2))
    assert model.max_observed_norm<model.max_state_norm
    assert model.transition_spectral_radius<1

def test_stable_diagonal_blocks_do_not_imply_stable_coupled_matrix():
    matrix=np.array([[0.5,1.2],[1.2,0.5]])
    assert max(abs(np.linalg.eigvals(np.diag([0.5,0.5]))))<1
    assert max(abs(np.linalg.eigvals(matrix)))>1

def test_candidate_promotion_and_rollback_restore_trusted_operator():
    model=CoupledAdaptiveSystem(); prior=model.revision.accepted_operator.copy()
    model.start_candidate(prior+0.1*np.eye(2))
    assert model.validate_candidate(1.0,0.5,True)
    assert not np.array_equal(model.revision.accepted_operator,prior)
    model.rollback()
    assert np.array_equal(model.revision.accepted_operator,prior)
    assert model.rollback_count==1

def test_candidate_rejection_does_not_change_trusted_operator():
    model=CoupledAdaptiveSystem(); prior=model.revision.accepted_operator.copy()
    model.start_candidate(prior+0.1*np.eye(2))
    assert not model.validate_candidate(1.0,1.1,True)
    assert np.array_equal(model.revision.accepted_operator,prior)

def test_dormancy_and_recovery_modes_are_explicit():
    model=CoupledAdaptiveSystem(); model.enter_dormancy(); assert model.mode==AdaptiveMode.DORMANT
    model.reactivate(); assert model.mode==AdaptiveMode.RECOVERY
    model.finish_recovery(); assert model.mode==AdaptiveMode.NORMAL

def test_preliminary_stress_run_reports_limited_claim():
    result=run(seed_count=3,steps=30)
    assert result["all_runs_within_declared_norm_25"]
    assert result["rollback_restored_trusted_state"]
    assert "no arbitrary-switching" in result["claim_boundary"]


def test_individually_stable_switched_modes_can_have_unstable_product():
    first=np.array([[0.5,2.0],[0.0,0.5]])
    second=np.array([[0.5,0.0],[2.0,0.5]])
    assert max(abs(np.linalg.eigvals(first)))==pytest.approx(0.5)
    assert max(abs(np.linalg.eigvals(second)))==pytest.approx(0.5)
    assert max(abs(np.linalg.eigvals(second@first)))>1.0

def test_existing_evidence_activation_is_reused_without_counting_missingness():
    model=CoupledAdaptiveSystem()
    state=model.update_relation_evidence("r",None,observed=False,identifiable=True,context_score=0.0)
    assert int(state.observed_count)==0
    state=model.update_relation_evidence("r",0.8,observed=True,identifiable=True,context_score=0.0)
    assert int(state.observed_count)==1
