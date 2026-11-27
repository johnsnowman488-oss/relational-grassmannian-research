import copy

from rgm.experiments.babi_expansion_runtime import BabiExpansionRuntime
from rgm.leptograph.m4.hierarchical import HLAAdapter
from rgm.leptograph.m4.learning import ErrorChannel
from rgm.leptograph.m4.soe_bridge import SOEHierarchyBridge
from rgm.memory import SOEMemory


class Runtime:
    def __init__(self, banks):
        self.state = {
            "level_states": [
                {"u": bank.snapshot().reshape(-1).tolist(),
                 "chi": [0.0] * bank.channel_count, "t": 0.0}
                for bank in banks
            ],
            "step_count": 0,
        }

    def get_state(self):
        return copy.deepcopy(self.state)

    def checkpoint(self):
        return self.get_state()

    def restore(self, state):
        self.state = copy.deepcopy(state)

    def step(self, feedback_by_level=None):
        self.state["step_count"] += 1
        return self.get_state()


def make_adapter():
    banks = [
        SOEMemory(feature_dim=2, decay_rates=[0.1, 0.4]),
        SOEMemory(feature_dim=3, decay_rates=[0.2, 0.7]),
        SOEMemory(feature_dim=4, decay_rates=[0.05, 0.3]),
    ]
    bridge = SOEHierarchyBridge(Runtime(banks), banks, dt=0.01)
    return HLAAdapter(bridge, feature_dims=[2, 3, 4])


def test_runtime_can_freeze_exact_ablation_channels_before_learning_starts():
    adapter = make_adapter()
    selected = {ErrorChannel.RELATIONAL, ErrorChannel.ABSTRACTION}
    runtime = BabiExpansionRuntime(adapter, enabled_channels=selected)
    assert runtime.adapter.learning.enabled_channels == frozenset(selected)
    assert runtime.adapter.learning._observation_journal == []


def test_runtime_without_channel_override_preserves_existing_learning_runtime():
    adapter = make_adapter()
    original = adapter.learning
    runtime = BabiExpansionRuntime(adapter)
    assert runtime.adapter.learning is original
    assert runtime.adapter.learning.enabled_channels == frozenset(ErrorChannel)
