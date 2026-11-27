from types import SimpleNamespace

from rgm.experiments.babi_expansion_adapters import Prediction
from rgm.experiments.babi_expansion_confirmatory import evaluate_task11_confirmatory
from rgm.experiments.babi_task11_prediction import Task11AnswerDecision


def test_task11_confirmatory_evaluator_scores_answerable_and_expected_abstention_cases():
    inputs = [
        {"query": {"query_id": "q-answer", "task_id": 11}},
        {"query": {"query_id": "q-ambiguous", "task_id": 11}},
    ]
    labels = [
        {
            "query_id": "q-answer",
            "expected_abstention": False,
            "gold_answer": "office",
            "support_event_ids": ["e1", "e2"],
        },
        {
            "query_id": "q-ambiguous",
            "expected_abstention": True,
            "expected_reason": "ambiguous_entity_mention_after_last_grounded_state",
        },
    ]
    decisions = {
        "q-answer": Task11AnswerDecision(
            Prediction("office", ("e1", "e2"), False),
            "location:office", "fp-a", ("e1", "e2"),
        ),
        "q-ambiguous": Task11AnswerDecision(
            Prediction(None, (), True, "ambiguous_entity_mention_after_last_grounded_state"),
            None, "fp-b", ("e3",),
        ),
    }
    result = evaluate_task11_confirmatory(inputs, labels, decisions)
    assert result["answer_exact_match_on_answerable"] == 1.0
    assert result["answer_coverage_on_answerable"] == 1.0
    assert result["support_witness_recall"] == 1.0
    assert result["ambiguous_abstention_recall"] == 1.0
    assert result["ambiguous_false_acceptances"] == 0


def test_task11_confirmatory_evaluator_detects_ambiguous_false_acceptance():
    inputs = [{"query": {"query_id": "q-ambiguous", "task_id": 11}}]
    labels = [{
        "query_id": "q-ambiguous",
        "expected_abstention": True,
        "expected_reason": "ambiguous_entity_mention_after_last_grounded_state",
    }]
    decisions = {
        "q-ambiguous": Task11AnswerDecision(
            Prediction("office", ("e1",), False),
            "location:office", "fp", ("e1",),
        )
    }
    result = evaluate_task11_confirmatory(inputs, labels, decisions)
    assert result["ambiguous_abstention_recall"] == 0.0
    assert result["ambiguous_false_acceptances"] == 1
