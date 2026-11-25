import numpy as np
import pytest

from rgm.leptograph.m4.p6_runtime import P6RuntimeCoupler
from rgm.leptograph.m4.stability import AdaptiveMode, CoupledAdaptiveSystem

from rgm.memory import SOEMemory
from rgm.leptograph.m4.soe_bridge import SOEHierarchyBridge
from rgm.leptograph.m4.hierarchical import HLAAdapter, HierarchicalRuntimeDirector


class FakePersistentRuntime:
    def __init__(self, memories):
        self.state = {"level_states": [
            {"u": memory.snapshot().reshape(-1).tolist(),
             "chi": [0.0] * memory.channel_count, "t": 0.0}
            for memory in memories
        ], "step_count": 0}

    def get_state(self):
        import copy
        return copy.deepcopy(self.state)

    def checkpoint(self):
        return self.get_state()

    def restore(self, state):
        import copy
        self.state = copy.deepcopy(state)

    def step(self, feedback_by_level=None):
        import copy
        candidate = copy.deepcopy(self.state)
        for level, values in (feedback_by_level or {}).items():
            candidate["level_states"][level]["u"] = list(values)
        candidate["step_count"] += 1
        self.state = candidate
        return self.get_state()


def make_p6_coupler(*, readout_gain=1.0, control_gain=1.0,
                    observation_transform="identity"):
    banks = [
        SOEMemory(feature_dim=2, decay_rates=[0.1, 0.4]),
        SOEMemory(feature_dim=3, decay_rates=[0.2, 0.7]),
        SOEMemory(feature_dim=4, decay_rates=[0.05, 0.3]),
    ]
    runtime = FakePersistentRuntime(banks)
    bridge = SOEHierarchyBridge(runtime, banks, dt=0.01)
    adapter = HLAAdapter(bridge, feature_dims=[2, 3, 4])
    director = HierarchicalRuntimeDirector(adapter)
    coupler = P6RuntimeCoupler(
        director, readout_gain=readout_gain, control_gain=control_gain,
        observation_transform=observation_transform,
    )
    return coupler, runtime


def test_p6_soe_feedback_is_dc_normalized_for_slow_channels():
    model = CoupledAdaptiveSystem(max_state_norm=25.0)
    peak = 0.0
    for _ in range(1000):
        state = model.step(np.array([5.0, 5.0]), residual_score=0.0)
        peak = max(peak, float(np.linalg.norm(state)))
    assert peak < 25.0
    assert float(np.linalg.norm(model.state)) < 3.0
    # Raw slow-channel impulse traces may be much larger than the bounded
    # input; P6 must use their DC-normalized aggregate rather than raw mean.
    assert float(np.max(np.abs(model.memory.channels))) > 25.0


def test_p6_context_estimator_state_is_checkpointed_and_restored():
    coupler, _ = make_p6_coupler(readout_gain=0.1, control_gain=0.1)
    last_adaptive = None
    for index in range(24):
        lower = np.array([np.sin(index * 0.2), np.cos(index * 0.2)])
        upper = np.array([np.cos(index * 0.13), np.sin(index * 0.13)])
        target = 0.7 * lower + 0.2 * upper
        last_adaptive = coupler.model.observe_adaptive_state(
            {"lower": lower, "upper": upper},
            np.array([0.05, -0.03]), target,
        )
    assert "resource" in last_adaptive
    assert last_adaptive["resource"]["persistent_state_bytes"] > 0
    assert last_adaptive["resource"]["p6_soe_memory_bytes"] > 0
    saved = coupler.snapshot()
    saved_count = coupler.model.estimator.sample_count
    saved_context_count = coupler.model.context_bank.slots[0].count
    coupler.model.observe_adaptive_state(
        {"lower": np.ones(2), "upper": -np.ones(2)},
        np.array([0.05, -0.03]), np.zeros(2),
    )
    coupler.restore(saved)
    restored = coupler.snapshot()
    assert restored["fingerprint"] == saved["fingerprint"]
    assert coupler.model.estimator.sample_count == saved_count == 24
    assert coupler.model.context_bank.slots[0].count == saved_context_count
    assert set(coupler.model.activation.states) == {"lower", "upper"}


def test_p6_context_bank_capacity_abstains_without_eviction():
    model = CoupledAdaptiveSystem()
    bank = model.context_bank
    bank._pending.clear()
    for center in (np.array([10.0, 10.0]), np.array([20.0, 20.0]), np.array([30.0, 30.0])):
        for _ in range(3):
            bank.observe_novel(center)
    assert len(bank.slots) == bank.capacity == 4
    slot_ids = tuple(slot.slot_id for slot in bank.slots)
    for _ in range(3):
        assert bank.observe_novel(np.array([40.0, 40.0])) is None
    assert tuple(slot.slot_id for slot in bank.slots) == slot_ids
    assert bank._pending == []


def test_p6_relation_activation_hysteresis_turns_on_then_off():
    model = CoupledAdaptiveSystem()
    for _ in range(20):
        model.update_relation_evidence(
            "lower", 0.8, observed=True, identifiable=True,
            context_score=0.0, context_slot=0,
        )
    assert model.activation.is_active("lower")
    for _ in range(30):
        model.update_relation_evidence(
            "lower", -0.8, observed=True, identifiable=True,
            context_score=0.0, context_slot=0,
        )
    assert not model.activation.is_active("lower")
    assert model.activation.snapshot("lower")["observed_count"] == 50


def test_p6_dormancy_freezes_learning_and_recovery_uses_reduced_input():
    model = CoupledAdaptiveSystem()
    model.state = np.array([1.0, -0.5])
    model.memory.update(np.array([2.0, -1.0]))
    model.enter_dormancy()
    detector_observations = model.detector.observations
    estimator_samples = model.estimator.sample_count
    prior_state = model.state.copy()
    expected_dormant = model.transition @ prior_state
    dormant = model.step(np.array([5.0, 5.0]), residual_score=10.0)
    assert np.allclose(dormant, expected_dormant)
    assert model.detector.observations == detector_observations
    model.observe_adaptive_state(
        {"lower": np.ones(2), "upper": np.ones(2)},
        np.zeros(2), np.ones(2),
    )
    assert model.estimator.sample_count == estimator_samples
    model.reactivate()
    assert model.mode == AdaptiveMode.RECOVERY
    recovered = model.step(np.array([1.0, 1.0]), residual_score=0.0)
    assert np.all(np.isfinite(recovered))
    model.finish_recovery()
    assert model.mode == AdaptiveMode.NORMAL


def test_p6_runtime_checkpoint_roundtrip_includes_controller_and_native_state():
    coupler, runtime = make_p6_coupler()
    try:
        coupler.update_relation_evidence(
            "r1", 0.8, observed=True, identifiable=True, context_score=0.0,
            context_slot=2,
        )
        before = coupler.checkpoint()
        coupler.exchange(event_time=0.01, observed_at=0.01,
                         event_features={0: [0.2, -0.1]})
        assert runtime.state["step_count"] == 1
        assert coupler.model.step_count == 1
        coupler.restore(before)
        assert runtime.state["step_count"] == 0
        assert coupler.model.step_count == 0
        assert coupler.model.activation.states["r1"].observed_count == 1
        assert coupler.snapshot() == before
    finally:
        coupler.close()


def test_p6_candidate_promotion_and_composite_rollback_restore_exact_continuation():
    coupler, runtime = make_p6_coupler()
    try:
        coupler.checkpoint()
        coupler.exchange(event_time=0.01, observed_at=0.01,
                         event_features={0: [0.2, -0.1]})
        pre_candidate = coupler.checkpoint()
        prior_operator = coupler.model.revision.accepted_operator.copy()
        coupler.start_candidate(prior_operator + 0.05 * np.eye(2))
        assert coupler.validate_candidate(
            incumbent_loss=1.0, candidate_loss=0.5, identifiable=True
        )
        assert coupler.version == 1
        assert coupler.model.mode == AdaptiveMode.PROMOTED
        coupler.exchange(event_time=0.02, observed_at=0.02,
                         event_features={0: [-0.1, 0.3]})
        coupler.model.rollback()
        assert np.array_equal(coupler.model.revision.accepted_operator, prior_operator)
        assert coupler.model.rollback_count == 1
        coupler.rollback()
        assert coupler.version == 0
        assert coupler.snapshot() == pre_candidate
        assert runtime.state["step_count"] == 1
        assert coupler.model.mode == AdaptiveMode.NORMAL
    finally:
        coupler.close()


def test_p6_failure_after_native_step_rolls_back_the_whole_exchange():
    coupler, runtime = make_p6_coupler()
    try:
        before = coupler.checkpoint()
        with pytest.raises(ValueError, match="finite"):
            coupler.exchange(
                event_time=0.01, observed_at=0.01,
                event_features={0: [0.2, -0.1]},
                residual_score=float("nan"),
            )
        assert runtime.state["step_count"] == 0
        assert coupler.snapshot() == before
    finally:
        coupler.close()



def test_p6_checkpoint_binds_readout_and_control_gain_configuration():
    coupler, _ = make_p6_coupler(readout_gain=0.1, control_gain=0.1)
    try:
        checkpoint = coupler.checkpoint()
        assert checkpoint["coupling_config"] == {
            "readout_gain": 0.1, "control_gain": 0.1,
            "observation_transform": "identity",
        }
        wrong = P6RuntimeCoupler(
            coupler.director,
            hierarchy_lifecycle=coupler.hierarchy_lifecycle,
            readout_gain=1.0, control_gain=1.0,
        )
        with pytest.raises(ValueError, match="gain configuration"):
            wrong.restore(checkpoint)
    finally:
        coupler.close()



def test_p6_tanh_observation_is_bounded_and_checkpointed():
    coupler, _ = make_p6_coupler(
        readout_gain=0.1, control_gain=0.1, observation_transform="tanh"
    )
    try:
        checkpoint = coupler.checkpoint()
        assert checkpoint["coupling_config"]["observation_transform"] == "tanh"
        result = coupler.exchange(
            event_time=0.01, observed_at=0.01,
            event_features={0: [0.2, -0.1], 1: [2.0, 2.0, 2.0],
                            2: [3.0, 3.0, 3.0, 3.0]},
        )
        raw = np.asarray(result["p6_observation_raw"])
        transformed = np.asarray(result["p6_observation"])
        assert np.allclose(transformed, np.tanh(raw))
        assert np.all(np.abs(transformed) <= 1.0)
        coupler.restore(checkpoint)
        assert coupler.snapshot() == checkpoint
    finally:
        coupler.close()
