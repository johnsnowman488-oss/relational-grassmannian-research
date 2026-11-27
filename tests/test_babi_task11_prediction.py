from types import SimpleNamespace

from rgm.experiments.babi_expansion_adapters import (
    ExpansionQuery, ExpansionStory, Task11MentionEvent,
)
from rgm.experiments.babi_task11_prediction import predict_task11_from_learned_state


class ContextTransitions:
    def __init__(self, values):
        self.values = dict(values)

    def predict(self, key):
        return self.values.get(key)

    def snapshot(self):
        return dict(self.values)


def adapter(values):
    return SimpleNamespace(
        learning=SimpleNamespace(context_transitions=ContextTransitions(values))
    )


def story():
    return ExpansionStory("task11/validation/story1", 11, (
        Task11MentionEvent("m1", "Mary", False, "kitchen", 1, "validation#1", "female"),
        Task11MentionEvent("m2", "John", False, "garden", 2, "validation#2", "male"),
        Task11MentionEvent("m3", "she", True, "office", 3, "validation#3", "female"),
    ), ())


def test_learned_context_prediction_must_agree_with_story_grounding():
    current = story()
    query = ExpansionQuery("q1", 11, 4, "validation#4", entity="mary")
    result = predict_task11_from_learned_state(
        adapter({"task11:entity:mary": "location:office"}), current, query,
    )
    assert result.prediction.answer == "office"
    assert result.prediction.abstained is False
    assert result.prediction.witness_event_ids == ("m1", "m3")
    assert result.grounding_event_ids == ("m1", "m3")
    assert len(result.model_fingerprint) == 64


def test_learned_context_conflict_abstains_instead_of_overriding_observed_story():
    current = story()
    query = ExpansionQuery("q1", 11, 4, "validation#4", entity="mary")
    result = predict_task11_from_learned_state(
        adapter({"task11:entity:mary": "location:kitchen"}), current, query,
    )
    assert result.prediction.answer is None
    assert result.prediction.abstained is True
    assert result.prediction.reason == "learned_context_conflicts_with_story_evidence"


def test_unavailable_learned_context_abstains_even_when_story_has_answer_evidence():
    current = story()
    query = ExpansionQuery("q1", 11, 4, "validation#4", entity="mary")
    result = predict_task11_from_learned_state(adapter({}), current, query)
    assert result.prediction.abstained is True
    assert result.prediction.reason == "learned_context_unavailable"


def test_query_cutoff_excludes_later_story_events():
    current = story()
    query = ExpansionQuery("q1", 11, 2, "validation#2", entity="mary")
    result = predict_task11_from_learned_state(
        adapter({"task11:entity:mary": "location:kitchen"}), current, query,
    )
    assert result.prediction.answer == "kitchen"
    assert result.prediction.witness_event_ids == ("m1",)
