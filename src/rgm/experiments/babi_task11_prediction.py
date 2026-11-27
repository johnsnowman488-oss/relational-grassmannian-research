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
    _NAME_GENDER,
    _PRONOUN_GENDER,
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
    """Replay a story-local entity transition chain through the learned L2 model.

    Each observed mention must be predicted by the learned transition keyed by
    the entity and its preceding location state. The observed location confirms
    that transition; a missing or conflicting model transition causes abstention.
    The resolver is prior-only and conservative, and no GoldLabel is accepted.
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
    model_state = {
        "architecture": getattr(adapter, "architecture", None),
        "context_transitions": adapter.learning.context_transitions.snapshot(),
        "hlb_model_relations": adapter.store.snapshot() if getattr(adapter, "architecture", None) == "HLB" else None,
    }
    model_fingerprint = fingerprint(model_state)
    if not visible:
        return Task11AnswerDecision(
            Prediction(None, (), True, "no_prior_source_observations"),
            None, model_fingerprint, (),
        )

    bindings = derive_task11_training_bindings(story)
    binding_by_event = {row.mention_event_id: row for row in bindings["targets"]}
    grounded = [
        event for event in visible
        if (binding := binding_by_event.get(event.event_id)) is not None
        and binding.entity_id == query.entity
    ]
    if not grounded:
        return Task11AnswerDecision(
            Prediction(None, (), True, "entity_has_no_unambiguous_story_binding"),
            None, model_fingerprint, (),
        )

    # An ambiguous/unresolved pronoun after the last unambiguous mention could
    # refer to this entity. Do not answer from a stale earlier location merely
    # because the conservative weak resolver correctly withheld that pronoun.
    entity_gender = _NAME_GENDER.get(query.entity.casefold())
    if entity_gender is not None:
        last_grounded_time = max(event.observed_at for event in grounded)
        event_by_id = {event.event_id: event for event in visible}
        for abstention in bindings["abstentions"]:
            unresolved = event_by_id.get(abstention["mention_event_id"])
            if unresolved is None or unresolved.observed_at <= last_grounded_time:
                continue
            unresolved_gender = (
                unresolved.grammatical_gender
                or _PRONOUN_GENDER.get(unresolved.surface_mention.casefold())
            )
            if unresolved_gender == entity_gender:
                return Task11AnswerDecision(
                    Prediction(None, (), True,
                               "ambiguous_entity_mention_after_last_grounded_state"),
                    None, model_fingerprint, tuple(event.event_id for event in grounded),
                )

    previous_location = None
    model_context = None
    witnesses = []
    for event in grounded:
        previous_key = previous_location if previous_location is not None else "__START__"
        context_key = (
            f"task11:entity:{query.entity}:from:{previous_key}"
        )
        if getattr(adapter, "architecture", None) == "HLB":
            # HLB predicts through its typed, rollback-scoped model relation
            # store. These records are learned transitions, not durable source
            # evidence. The model store is fit-only during validation.
            matches = [
                record for record in adapter.store.records(cutoff=1e300, levels=(1,))
                if record.relation_type.name == "task11_location_transition"
                and record.subject.entity_id == f"{query.entity}|{previous_key}"
            ]
            predicted_locations = {record.object.entity_id for record in matches}
            if len(predicted_locations) == 1:
                model_context = f"location:{next(iter(predicted_locations))}"
            elif len(predicted_locations) > 1:
                model_context = "__AMBIGUOUS__"
            else:
                model_context = None
        else:
            model_context = adapter.learning.context_transitions.predict(context_key)
        observed_context = f"location:{event.location}"
        if model_context == "__AMBIGUOUS__":
            return Task11AnswerDecision(
                Prediction(None, (), True, "learned_transition_ambiguous"),
                model_context, model_fingerprint, tuple(witnesses),
            )
        if not isinstance(model_context, str) or not model_context.startswith("location:"):
            return Task11AnswerDecision(
                Prediction(None, (), True, "learned_transition_unavailable"),
                model_context, model_fingerprint, tuple(witnesses),
            )
        if model_context != observed_context:
            return Task11AnswerDecision(
                Prediction(None, (), True, "learned_transition_conflicts_with_story_evidence"),
                model_context, model_fingerprint, tuple(witnesses),
            )
        previous_location = event.location
        witnesses.append(event.event_id)

    return Task11AnswerDecision(
        Prediction(previous_location, tuple(witnesses), False),
        model_context, model_fingerprint, tuple(witnesses),
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
