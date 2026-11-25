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


def make_p6_coupler():
    banks = [
        SOEMemory(feature_dim=2, decay_rates=[0.1, 0.4]),
        SOEMemory(feature_dim=3, decay_rates=[0.2, 0.7]),
        SOEMemory(feature_dim=4, decay_rates=[0.05, 0.3]),
    ]
    runtime = FakePersistentRuntime(banks)
    bridge = SOEHierarchyBridge(runtime, banks, dt=0.01)
    adapter = HLAAdapter(bridge, feature_dims=[2, 3, 4])
    director = HierarchicalRuntimeDirector(adapter)
    coupler = P6RuntimeCoupler(director)
    return coupler, runtime


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
