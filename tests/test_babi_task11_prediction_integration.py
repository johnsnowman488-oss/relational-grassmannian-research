import copy

from rgm.experiments.babi_expansion_adapters import (
    ExpansionQuery, ExpansionStory, Task11MentionEvent,
)
from rgm.experiments.babi_expansion_runtime import BabiExpansionRuntime
from rgm.experiments.babi_task11_prediction import predict_task11_from_learned_state
from rgm.leptograph.m4.hierarchical import HLAAdapter
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
        candidate = self.get_state()
        for level, values in (feedback_by_level or {}).items():
            candidate["level_states"][level]["u"] = list(values)
        candidate["step_count"] += 1
        self.state = candidate
        return self.get_state()


def make_adapter():
    banks = [
        SOEMemory(feature_dim=2, decay_rates=[0.1, 0.4]),
        SOEMemory(feature_dim=3, decay_rates=[0.2, 0.7]),
        SOEMemory(feature_dim=4, decay_rates=[0.05, 0.3]),
    ]
    return HLAAdapter(
        SOEHierarchyBridge(Runtime(banks), banks, dt=0.01),
        feature_dims=[2, 3, 4],
    )


def test_persistent_hla_ingestion_trains_context_used_by_answer_predictor():
    training_story = ExpansionStory("task11/fit/story1", 11, (
        Task11MentionEvent("m1", "Mary", False, "kitchen", 1, "fit#1", "female"),
        Task11MentionEvent("m2", "John", False, "garden", 2, "fit#2", "male"),
        Task11MentionEvent("m3", "she", True, "office", 3, "fit#3", "female"),
    ), ())
    adapter = make_adapter()
    runtime = BabiExpansionRuntime(adapter)
    runtime.ingest_story_sequence([training_story])

    learned = adapter.learning.context_transitions.predict("task11:entity:mary:from:kitchen")
    assert learned == "location:office"

    query = ExpansionQuery("q1", 11, 4, "validation#4", entity="mary")
    validation_story = ExpansionStory("task11/validation/story1", 11, (
        Task11MentionEvent("v1", "Mary", False, "kitchen", 1, "validation#1", "female"),
        Task11MentionEvent("v2", "John", False, "garden", 2, "validation#2", "male"),
        Task11MentionEvent("v3", "she", True, "office", 3, "validation#3", "female"),
    ), (query,))
    decision = predict_task11_from_learned_state(adapter, validation_story, query)
    assert decision.prediction.answer == "office"
    assert decision.prediction.abstained is False
