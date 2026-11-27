"""Learned-state-gated Task 11 answer prediction.

The learner supplies a context prediction. Raw, story-local observations and
conservative weak bindings supply grounding and witness candidates. Evaluator
labels are not accepted by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rgm.experiments.babi_expansion_adapters import (
    ExpansionQuery,
    ExpansionStory,
    GoldLabel,
    Prediction,
    Task11MentionEvent,
    derive_task11_training_bindings,
)
from rgm.leptograph.m4.learning import fingerprint


@dataclass(frozen=True)
class Task11AnswerDecision:
    prediction: Prediction
    model_context: str | None
    model_fingerprint: str
    grounding_event_ids: tuple[str, ...]


def predict_task11_from_learned_state(adapter: Any, story: ExpansionStory,
                                      query: ExpansionQuery) -> Task11AnswerDecision:
    """Answer only when learned L2 context agrees with current grounded state.

    The model's context-transition learner must predict a location for the
    queried entity. The current story must independently contain a prior-only,
    unambiguous weak-binding chain for that entity and a matching source event.
    Otherwise the predictor abstains. It never accepts or reads a GoldLabel.
    """
    if story.task_id != 11 or query.task_id != 11:
        raise ValueError("Task 11 predictor received another task's input")
    if query.entity is None:
        raise ValueError("Task 11 location query requires an entity")
    if not hasattr(adapter, "learning") or not hasattr(adapter.learning, "context_transitions"):
        raise TypeError("adapter must expose the H1 context-transition learner")

    visible = tuple(
        event for event in story.events
        if isinstance(event, Task11MentionEvent) and event.observed_at < query.observed_at
    )
    model_fingerprint = fingerprint(adapter.learning.context_transitions.snapshot())
    if not visible:
        return Task11AnswerDecision(
            Prediction(None, (), True, "no_prior_source_observations"),
            None, model_fingerprint, (),
        )

    context_key = f"task11:entity:{query.entity}"
    model_context = adapter.learning.context_transitions.predict(context_key)
    if not isinstance(model_context, str) or not model_context.startswith("location:"):
        return Task11AnswerDecision(
            Prediction(None, (), True, "learned_context_unavailable"),
            model_context, model_fingerprint, (),
        )

    bindings = derive_task11_training_bindings(story)
    binding_by_event = {row.mention_event_id: row for row in bindings["targets"]}
    grounded = []
    for event in visible:
        binding = binding_by_event.get(event.event_id)
        if binding is not None and binding.entity_id == query.entity:
            grounded.append(event)
    if not grounded:
        return Task11AnswerDecision(
            Prediction(None, (), True, "entity_has_no_unambiguous_story_binding"),
            model_context, model_fingerprint, (),
        )

    latest = max(grounded, key=lambda event: event.observed_at)
    observed_context = f"location:{latest.location}"
    if model_context != observed_context:
        return Task11AnswerDecision(
            Prediction(None, (), True, "learned_context_conflicts_with_story_evidence"),
            model_context, model_fingerprint, tuple(event.event_id for event in grounded),
        )

    witnesses = tuple(event.event_id for event in grounded)
    return Task11AnswerDecision(
        Prediction(latest.location, witnesses, False),
        model_context, model_fingerprint, tuple(event.event_id for event in grounded),
    )



def evaluate_task11_predictions(stories: list[ExpansionStory],
                                decisions: dict[str, Task11AnswerDecision],
                                labels: list[GoldLabel]) -> dict:
    """Score frozen predictions against evaluator-only answer/support labels.

    This function is the only label-consuming boundary in this module. It does
    not mutate the learner, source evidence, predictions or model parameters.
    Official Task 11 labels do not contain independent antecedent-edge gold, so
    coreference-edge metrics are explicitly reported as unavailable.
    """
    queries = {
        query.query_id: (story, query)
        for story in stories for query in story.queries
    }
    label_by_id = {label.query_id: label for label in labels}
    if len(label_by_id) != len(labels):
        raise ValueError("duplicate Task 11 evaluator label query IDs")
    if set(queries) != set(label_by_id) or set(queries) != set(decisions):
        raise ValueError("Task 11 predictions, queries and evaluator labels must match exactly")

    rows = []
    correct = 0
    abstained = 0
    true_witnesses = 0
    total_support = 0
    false_witnesses = 0
    predicted_witnesses = 0
    recovery_mismatches = 0
    for query_id in sorted(queries):
        story, query = queries[query_id]
        label = label_by_id[query_id]
        decision = decisions[query_id]
        prediction = decision.prediction
        if prediction.abstained:
            abstained += 1
        is_correct = not prediction.abstained and prediction.answer == label.answer
        correct += int(is_correct)

        event_by_id = {event.event_id: event for event in story.events}
        predicted_lines = []
        for event_id in prediction.witness_event_ids:
            event = event_by_id.get(event_id)
            if event is None or event.observed_at >= query.observed_at:
                recovery_mismatches += 1
                continue
            try:
                predicted_lines.append(int(event.source_ref.rsplit("#line=", 1)[1]))
            except (IndexError, ValueError):
                recovery_mismatches += 1
        support = set(label.support_line_numbers)
        predicted = set(predicted_lines)
        true_witnesses += len(predicted & support)
        total_support += len(support)
        false_witnesses += len(predicted - support)
        predicted_witnesses += len(predicted)
        rows.append({
            "query_id": query_id,
            "answer": prediction.answer,
            "gold_answer": label.answer,
            "answer_exact_match": is_correct,
            "abstained": prediction.abstained,
            "predicted_witness_lines": sorted(predicted),
            "gold_support_lines": sorted(support),
            "witness_recall": (len(predicted & support) / len(support)) if support else None,
            "false_witness_rate": (len(predicted - support) / len(predicted)) if predicted else None,
        })

    count = len(queries)
    return {
        "schema": "HLG-BABI-TASK11-PREDICTION-EVALUATION-v1",
        "task_id": 11,
        "query_count": count,
        "answer_exact_match": correct / count if count else None,
        "abstention_rate": abstained / count if count else None,
        "forecast_coverage": (count - abstained) / count if count else None,
        "support_witness_recall": true_witnesses / total_support if total_support else None,
        "false_witness_rate": false_witnesses / predicted_witnesses if predicted_witnesses else None,
        "witness_recovery_mismatch_count": recovery_mismatches,
        "coreference_edge_metrics": {
            "status": "NOT_INDEPENDENTLY_EVALUABLE",
            "reason": "Official Task 11 answer/support labels do not provide independent antecedent-edge gold annotations.",
        },
        "per_query": rows,
        "label_boundary": "Evaluator labels are consumed only here, after prediction decisions are fixed.",
    }
