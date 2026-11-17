"""Unit and integration checks for the first HLG-M3 implementation slice."""
import numpy as np
import pytest

from rgm.leptograph.m3 import (
    CandidateRevision, ContextBank, ContextDecision, CUSUMDetector,
    EvidenceActivation, MemoryArchitecture, MultiSourceRidge,
)
from rgm.leptograph.m3.integration import run_integrated_smoke
from rgm.experiments.leptograph_m3_implementation import WORK_PACKAGES, run_package


def test_context_score_is_invariant_under_nonsingular_coordinate_change():
    g = np.array([[2.0, 0.25], [0.25, 1.2]])
    cov = np.array([[0.5, 0.08], [0.08, 0.35]])
    mu, z = np.array([0.4, -0.2]), np.array([0.1, 0.3])
    a = np.array([[1.8, 0.4], [0.1, 0.7]])
    old = ContextBank(g, regularisation=0.03)
    sid = old.add_initial(mu, prior_covariance=cov)
    ai = np.linalg.inv(a)
    new = ContextBank(a.T @ g @ a, regularisation=0.03)
    sid_new = new.add_initial(ai @ mu, prior_covariance=ai @ cov @ ai.T)
    assert old.score(z, sid) == pytest.approx(new.score(ai @ z, sid_new), abs=1e-9)


def test_context_bank_abstains_when_full_instead_of_evicting():
    bank = ContextBank(np.eye(2), capacity=1)
    bank.add_initial([0.0, 0.0], prior_covariance=0.1 * np.eye(2))
    before = bank.slots[0].mean.copy()
    assert bank.observe_novel([10.0, 10.0]) is None
    assert len(bank.slots) == 1
    assert np.array_equal(bank.slots[0].mean, before)


def test_context_bank_requires_repeated_novelty_before_slot_creation():
    bank = ContextBank(np.eye(2), capacity=2, novelty_repeats=3)
    bank.add_initial([0.0, 0.0], prior_covariance=0.1 * np.eye(2))
    assert bank.observe_novel([10.0, 10.0]) is None
    assert bank.observe_novel([10.1, 9.9]) is None
    assert len(bank.slots) == 1
    new_id = bank.observe_novel([9.9, 10.1])
    assert new_id == 1
    assert len(bank.slots) == 2


def test_joint_estimator_uses_all_heterogeneous_sources():
    rng = np.random.default_rng(71)
    model = MultiSourceRidge({"a": 2, "b": 3}, 2, 2, ridge=1e-6)
    wa = np.array([[0.8, -0.2], [0.1, 0.6]])
    wb = np.array([[0.2, 0.0, -0.1], [0.0, 0.3, 0.15]])
    wc = np.array([[0.08, 0.02], [-0.03, 0.05]])
    for _ in range(500):
        a, b, c = rng.normal(size=2), rng.normal(size=3), rng.normal(size=2)
        model.update({"a": a, "b": b}, c, wa @ a + wb @ b + wc @ c)
    beta = model.coefficients()
    assert np.linalg.norm(beta[:2]) > 0.1
    assert np.linalg.norm(beta[2:5]) > 0.1
    assert model.sample_count == model.update_count == 500


def test_prequential_prediction_uses_only_past_updates():
    a = MultiSourceRidge({"s": 1}, 0, 1)
    b = MultiSourceRidge({"s": 1}, 0, 1)
    for model in (a, b):
        for x, y in (([1.0], [2.0]), ([2.0], [4.0])):
            model.update({"s": x}, [], y)
    pa = a.predict({"s": [3.0]}, [])
    pb = b.predict({"s": [3.0]}, [])
    assert np.array_equal(pa, pb)
    a.update({"s": [3.0]}, [], [6.0])
    b.update({"s": [3.0]}, [], [-600.0])
    assert np.array_equal(a.predict({"s": [4.0]}, []), b.predict({"s": [4.0]}, [])) is False


def test_activation_missing_observation_is_not_negative_evidence():
    ctl = EvidenceActivation(on_threshold=0.2, off_threshold=0.1, minimum_observations=2)
    for _ in range(8):
        ctl.update("r", predictive_improvement=0.9, observed=True,
                   identifiable=True, context_score=0.0)
    before = ctl.snapshot("r")
    ctl.update("r", predictive_improvement=None, observed=False,
               identifiable=True, context_score=0.0)
    after = ctl.snapshot("r")
    assert before == after
    assert after["active"] is True
    for _ in range(20):
        ctl.update("r", predictive_improvement=-1.0, observed=True,
                   identifiable=True, context_score=0.0)
    assert ctl.is_active("r") is False


def test_cusum_and_candidate_revision_have_separate_alarm_and_promotion_gates():
    detector = CUSUMDetector(allowance=0.2, threshold=3.0)
    assert not any(detector.update(0.1) for _ in range(20))
    assert any(detector.update(1.0) for _ in range(8))
    accepted = np.eye(2)
    revision = CandidateRevision(accepted)
    revision.start_candidate(2.0 * np.eye(2))
    assert revision.evaluate(incumbent_loss=0.4, candidate_loss=0.6, identifiable=True) is False
    assert np.array_equal(revision.accepted_operator, accepted)
    revision.start_candidate(0.5 * np.eye(2))
    assert revision.evaluate(incumbent_loss=0.4, candidate_loss=0.2, identifiable=True) is True


def test_unidentifiable_candidate_is_rejected_even_if_loss_is_lower():
    revision = CandidateRevision(np.eye(2))
    revision.start_candidate(0.5 * np.eye(2))
    assert revision.evaluate(incumbent_loss=0.4, candidate_loss=0.1, identifiable=False) is False
    assert np.array_equal(revision.accepted_operator, np.eye(2))


def test_c0_c4_controls_are_distinct_and_measure_real_resources():
    systems = [MemoryArchitecture(k, 2, 2, 64) for k in ("C0", "C1", "C2", "C3", "C4")]
    for system in systems:
        system.update_mode(np.array([0.2, -0.1]))
        system.update_relation(np.array([0.1, 0.3]))
        system.read_mode()
        system.read_relation()
    snapshots = [s.resource_snapshot() for s in systems]
    assert len({str(sorted(x.items())) for x in snapshots}) == 5
    assert systems[0].persistent_bytes == 0
    assert systems[3].persistent_state_bytes == 64 * 8
    assert systems[4].persistent_state_bytes == 64 * 8
    assert systems[4].trainable_parameter_count == 264
    assert systems[4].update_multiply_adds > 0 and systems[4].query_multiply_adds > 0


def test_integrated_smoke_uses_two_sources_and_records_scope_ceiling():
    result = run_integrated_smoke(seed=1603, steps=240)
    assert result["both_sources_used"] is True
    assert result["learner_source_dimensions"] == {"group_a": 2, "group_b": 3}
    assert np.isfinite(result["mean_squared_prediction_error"])
    assert result["steps"] == 240
    assert "not the full eight-world" in run_package("M3-I")["interpretation"]


@pytest.mark.parametrize("package_id", WORK_PACKAGES)
def test_each_independent_work_package_emits_valid_execution_record(package_id):
    result = run_package(package_id)
    assert result["campaign_id"] == "HLG-M3-IMPLEMENTATION-v0.1"
    assert result["package_id"] == package_id
    assert result["execution_passed"] is True


def test_c0_c4_expose_common_prequential_target_prediction_api():
    systems = [MemoryArchitecture(k, 2, 2, 64, target_dimension=2)
               for k in ("C0", "C1", "C2", "C3", "C4")]
    for system in systems:
        system.update_mode(np.array([0.2, -0.1]))
        system.update_relation(np.array([0.1, 0.3]))
        before = system.predict()
        assert before.shape == (2,)
        loss = system.score_target(np.array([0.5, -0.25]))
        assert np.isfinite(loss)
        system.update_target(np.array([0.5, -0.25]))
        after = system.predict()
        assert after.shape == (2,)
        if system.name == "C0":
            assert np.array_equal(before, after)
        else:
            assert np.linalg.norm(after - before) > 0.0
        snapshot = system.resource_snapshot()
        assert snapshot["task_readout_parameters"] == system.task_readout.size
        assert snapshot["persistent_bytes_total"] == system.persistent_bytes


def test_control_task_prediction_rejects_invalid_target():
    system = MemoryArchitecture("C3", 2, 2, 64)
    with pytest.raises(ValueError):
        system.update_target(np.array([1.0]))
    with pytest.raises(ValueError):
        system.score_target(np.array([np.nan, 0.0]))


def test_context_bank_nearest_reuse_is_bounded_and_label_blind():
    bank = ContextBank(np.eye(2), capacity=2, full_bank_policy="nearest_reuse",
                       accept_threshold=2.0, novelty_threshold=4.0)
    first = bank.add_initial([0.0, 0.0], prior_covariance=0.2 * np.eye(2))
    second = bank.add_initial([5.0, 5.0], prior_covariance=0.2 * np.eye(2))
    reused = bank.observe_novel([0.1, -0.1])
    assert reused == first
    assert len(bank.slots) == 2
    assert bank.slots[0].novelty_hits == 1
    assert bank.slots[1].novelty_hits == 0
    assert bank.slots[0].count == 2
    assert second == 1
