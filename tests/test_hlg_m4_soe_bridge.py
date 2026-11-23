import numpy as np
import pytest

from rgm.memory import SOEMemory
from rgm.leptograph.m4.soe_bridge import SOEHierarchyBridge, SOEStateLayout, make_native_level_spec


class FakeRuntime:
    def __init__(self, banks):
        self.calls = []
        self.snapshot = {"level_states": [
            {"u": np.zeros(m.channel_count * m.feature_dim).tolist(),
             "chi": [0.0] * m.channel_count, "t": 0.0}
            for m in banks
        ]}

    def get_state(self):
        return self.snapshot

    def step(self, feedback_by_level=None):
        self.calls.append(feedback_by_level)
        for index, values in feedback_by_level.items():
            self.snapshot["level_states"][index]["u"] = list(values)
        return self.snapshot


def make_banks():
    return [
        SOEMemory(feature_dim=3, decay_rates=[0.1, 0.5]),
        SOEMemory(feature_dim=2, decay_rates=[0.2, 0.7, 1.1]),
        SOEMemory(feature_dim=4, decay_rates=[0.05, 0.3]),
    ]


@pytest.mark.parametrize("channels,features", [(1, 1), (2, 3), (4, 7)])
def test_soe_embedding_is_lossless(channels, features):
    layout = SOEStateLayout(channels, features)
    matrix = np.arange(channels * features, dtype=float).reshape(channels, features) / 7
    assert np.array_equal(layout.decode(layout.encode(matrix)), matrix)


def test_native_level_spec_embeds_soe_state_and_separates_chi():
    memory = SOEMemory(feature_dim=3, decay_rates=[0.1, 0.5])
    memory.update([1.0, 2.0, 3.0], dt=0.2)
    spec = make_native_level_spec(memory, name="grounding", gamma=[0.5, 0.1], weights=[0.4, 0.6], dt=0.01)
    assert spec["u"] == memory.channels.reshape(-1).tolist()
    assert len(spec["u"]) == 6
    assert spec["chi"] == [0.0, 0.0]


def test_bridge_updates_all_banks_and_calls_native_once():
    banks = make_banks()
    runtime = FakeRuntime(banks)
    bridge = SOEHierarchyBridge(runtime, banks, dt=0.01)
    features = {0: [1.0, 0.0, -1.0], 2: [0.5, 0.25, 0.0, -0.25]}
    result = bridge.step(features)
    assert len(runtime.calls) == 1
    assert set(runtime.calls[0]) == {0, 1, 2}
    for i, bank in enumerate(banks):
        assert np.array_equal(result["soe_feedback"][i], bank.channels)
    assert result["native_u_views"][0].shape == banks[0].channels.shape


def test_silent_cycle_decays_every_bank_and_advances_once():
    banks = make_banks()
    for bank in banks:
        bank.update(np.ones(bank.feature_dim), dt=0.0)
    before = [bank.channels.copy() for bank in banks]
    runtime = FakeRuntime(banks)
    bridge = SOEHierarchyBridge(runtime, banks, dt=0.02)
    bridge.step()
    assert len(runtime.calls) == 1
    for bank, prior in zip(banks, before):
        assert np.all(bank.channels <= prior)
        assert np.any(bank.channels < prior)


def test_invalid_batch_does_not_mutate_any_bank():
    banks = make_banks()
    runtime = FakeRuntime(banks)
    bridge = SOEHierarchyBridge(runtime, banks, dt=0.01)
    before = [bank.channels.copy() for bank in banks]
    with pytest.raises(ValueError):
        bridge.step({0: [1.0, 2.0, 3.0], 2: [1.0, 2.0]})
    assert all(np.array_equal(a, b.channels) for a, b in zip(before, banks))
    assert runtime.calls == []


def test_bridge_rejects_wrong_native_dimension_and_variable_dt():
    banks = make_banks()
    bridge = SOEHierarchyBridge(FakeRuntime(banks), banks, dt=0.01)
    with pytest.raises(ValueError, match="fixed dt"):
        bridge.step(dt=0.02)
    bad = FakeRuntime(banks)
    bad.snapshot["level_states"][1]["u"] = [0.0]
    with pytest.raises(ValueError, match="dimension"):
        SOEHierarchyBridge(bad, banks, dt=0.01)


def test_silent_steps_are_explicit_global_ticks():
    banks = make_banks()
    runtime = FakeRuntime(banks)
    bridge = SOEHierarchyBridge(runtime, banks, dt=0.01)
    assert len(bridge.silent_steps(4)) == 4
    assert len(runtime.calls) == 4


def test_h0_chain_spec_has_shared_three_level_topology():
    from rgm.leptograph.m4.soe_bridge import H0_DEFAULT_EDGES, make_h0_chain_spec

    banks = make_banks()
    kernels = [
        {"gamma": sorted(bank.decay_rates.tolist(), reverse=True), "w": [1.0] * bank.channel_count}
        for bank in banks
    ]
    levels, edges = make_h0_chain_spec(banks, kernels, dt=0.01)
    assert len(levels) == 3
    assert [level["name"] for level in levels] == [
        "grounding", "relational_abstraction", "context_control"
    ]
    assert [len(level["u"]) for level in levels] == [6, 6, 8]
    assert edges == [dict(edge) for edge in H0_DEFAULT_EDGES]
    assert all(level["dt"] == 0.01 for level in levels)


def test_native_step_failure_does_not_commit_python_soe_state():
    class FailingRuntime(FakeRuntime):
        def step(self, feedback_by_level=None):
            raise RuntimeError("native step rejected")

    banks = make_banks()
    runtime = FailingRuntime(banks)
    bridge = SOEHierarchyBridge(runtime, banks, dt=0.01)
    before = [bank.channels.copy() for bank in banks]
    with pytest.raises(RuntimeError, match="native step rejected"):
        bridge.step({0: [1.0, 0.0, 0.0]})
    assert all(np.array_equal(a, b.channels) for a, b in zip(before, banks))
