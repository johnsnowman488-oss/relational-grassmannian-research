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
