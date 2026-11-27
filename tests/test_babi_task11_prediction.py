from types import SimpleNamespace

from rgm.experiments.babi_expansion_adapters import (
    ExpansionQuery, ExpansionStory, GoldLabel, Prediction, Task11MentionEvent,
)
from rgm.experiments.babi_task11_prediction import (
    Task11AnswerDecision, evaluate_task11_predictions, predict_task11_from_learned_state,
)


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



def test_evaluator_scores_answer_and_witnesses_only_after_prediction_is_fixed():
    current = story()
    query = ExpansionQuery("q1", 11, 4, "validation#4", entity="mary")
    decision = predict_task11_from_learned_state(
        adapter({"task11:entity:mary": "location:office"}), current, query,
    )
    labels = [GoldLabel("q1", "office", (1, 3), "validation#4")]
    report = evaluate_task11_predictions([ExpansionStory(
        current.story_id, current.task_id, current.events, (query,)
    )], {"q1": decision}, labels)
    assert report["answer_exact_match"] == 1.0
    assert report["forecast_coverage"] == 1.0
    assert report["support_witness_recall"] == 1.0
    assert report["false_witness_rate"] == 0.0
    assert report["witness_recovery_mismatch_count"] == 0
    assert report["coreference_edge_metrics"]["status"] == "NOT_INDEPENDENTLY_EVALUABLE"


def test_evaluator_reports_false_witnesses_without_rewriting_the_prediction():
    current = story()
    query = ExpansionQuery("q1", 11, 4, "validation#4", entity="mary")
    prediction = Prediction("office", ("m1", "m2", "m3"), False)
    decision = Task11AnswerDecision(
        prediction, "location:office", "model-fingerprint", ("m1", "m2", "m3")
    )
    labels = [GoldLabel("q1", "office", (1, 3), "validation#4")]
    report = evaluate_task11_predictions([ExpansionStory(
        current.story_id, current.task_id, current.events, (query,)
    )], {"q1": decision}, labels)
    assert report["answer_exact_match"] == 1.0
    assert report["support_witness_recall"] == 1.0
    assert report["false_witness_rate"] == 1 / 3
    assert prediction.witness_event_ids == ("m1", "m2", "m3")
