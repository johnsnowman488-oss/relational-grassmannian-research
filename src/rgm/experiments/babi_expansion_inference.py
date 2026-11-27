"""Task 11 inference from learned H1 state with source-grounded witness checks.

This is deliberately separate from the symbolic baselines. It reads only the
active HLA/HLB learner state and source evidence already ingested by the runtime;
it has no evaluator-label argument and never mutates evidence or learner state.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from rgm.experiments.babi_expansion_adapters import ExpansionQuery
from rgm.leptograph.m4.learning import fingerprint


ABSTAIN = "__ABSTAIN__"


@dataclass(frozen=True)
class Task11ModelPrediction:
    architecture: str
    query_id: str
    l0_mention_binding: Any
    l1_coreference_edge: Any
    l2_entity_state: Any
    answer: str | None
    witness_event_ids: tuple[str, ...]
    abstained: bool
    reason: str | None
    model_fingerprint: str

    def forecast_values(self) -> dict[str, Any]:
        return {
            "l0_value": self.l0_mention_binding,
            "l1_value": self.l1_coreference_edge,
            "l2_value": self.l2_entity_state,
            "answer_value": self.answer if self.answer is not None else ABSTAIN,
        }


def _model_fingerprint(architecture: str, learning: Any) -> str:
    state = {
        "architecture": architecture,
        "relations": learning.relations.snapshot(),
        "event_roles": learning.event_roles.snapshot(),
        "context_transitions": learning.context_transitions.snapshot(),
    }
    payload = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _source_witnesses(runtime: Any, query: ExpansionQuery,
                      predicted_relation: Any, location: str) -> tuple[str, ...]:
    evidence = runtime.evidence
    ids = tuple(getattr(evidence, "event_ids", ()))
    witnesses: set[str] = set()
    candidate_ids = set(ids)
    if predicted_relation is not None:
        candidate_ids.update((predicted_relation.subject_id, predicted_relation.object_id))
    for event_id in sorted(candidate_ids):
        if event_id not in ids:
            continue
        records = evidence.recover(event_id, observation_cutoff=float(query.observed_at))
        for record in records:
            mention = record.role("mention")
            observed_location = record.role("location")
            if (mention is not None and observed_location is not None
                    and mention.entity_id.casefold() == query.entity.casefold()
                    and observed_location.entity_id.casefold() == location.casefold()):
                witnesses.add(event_id)
    return tuple(sorted(witnesses))


def predict_task11_from_learned_state(runtime: Any, query: ExpansionQuery) -> Task11ModelPrediction:
    """Forecast Task 11 targets using learned H1 predictors, not a symbolic resolver.

    The context-transition learner supplies the L2 location forecast. The
    event-role and semantic-relation learners independently supply L0/L1
    structural forecasts. Exact source witnesses are recovered separately and
    may veto an unsupported answer. Missing model state produces explicit
    abstention rather than a baseline fallback.
    """
    if query.task_id != 11:
        raise ValueError("learned Task 11 predictor received another task")
    adapter = runtime.adapter
    architecture = getattr(adapter, "architecture", None)
    if architecture not in {"HLA", "HLB"}:
        raise ValueError("Task 11 prediction requires an HLA or HLB adapter")
    learning = adapter.learning
    entity = query.entity
    if not entity:
        raise ValueError("Task 11 location query requires an entity")
    context = f"task11:entity:{entity.casefold()}"

    role_pattern = learning.event_roles.predict(context)
    relation_pattern = learning.relations.predict(context)
    next_context = learning.context_transitions.predict(context)

    l0: Any = ABSTAIN
    if role_pattern is not None:
        roles = {role: (entity_id, entity_type)
                 for role, entity_id, entity_type in role_pattern.roles}
        bound_entity = roles.get("entity")
        antecedent = roles.get("antecedent_event")
        if bound_entity is not None and bound_entity[0].casefold() == entity.casefold():
            l0 = {
                "entity_id": bound_entity[0],
                "mention_event_id": antecedent[0] if antecedent else None,
                "event_type": role_pattern.event_type,
            }

    l1: Any = ABSTAIN
    if relation_pattern is not None and relation_pattern.relation_type == "corefers_with":
        if relation_pattern.subject_type == "mention_event" and relation_pattern.object_type == "mention_event":
            l1 = {
                "mention_event_id": relation_pattern.subject_id,
                "antecedent_event_id": relation_pattern.object_id,
                "relation": relation_pattern.relation_type,
            }

    location = None
    if isinstance(next_context, str) and next_context.startswith("location:"):
        candidate = next_context[len("location:"):].strip()
        if candidate:
            location = candidate

    witnesses = _source_witnesses(runtime, query, relation_pattern, location)
    if location is None:
        return Task11ModelPrediction(
            architecture, query.query_id, l0, l1, ABSTAIN, None, witnesses,
            True, "unseen_or_unusable_entity_context", _model_fingerprint(architecture, learning),
        )
    if not witnesses:
        return Task11ModelPrediction(
            architecture, query.query_id, l0, l1,
            {"entity_id": entity, "location": location, "witness_event_ids": []},
            None, (), True, "no_source_grounded_entity_witness",
            _model_fingerprint(architecture, learning),
        )

    return Task11ModelPrediction(
        architecture, query.query_id, l0, l1,
        {"entity_id": entity, "location": location, "witness_event_ids": list(witnesses)},
        location, witnesses, False, None, _model_fingerprint(architecture, learning),
    )



def issue_task11_model_forecasts(runtime: Any, query: ExpansionQuery, forecasts: Any, *,
                                 issued_tick: int, issued_at: float,
                                 evidence_cutoff: float) -> Task11ModelPrediction:
    """Issue L0/L1/L2/answer forecasts before evaluator labels are opened."""
    prediction = predict_task11_from_learned_state(runtime, query)
    values = prediction.forecast_values()
    forecasts.issue_query_forecasts(
        query,
        issued_tick=issued_tick,
        issued_at=issued_at,
        evidence_cutoff=evidence_cutoff,
        l0_value=values["l0_value"],
        l1_value=values["l1_value"],
        l2_value=values["l2_value"],
        answer_value=values["answer_value"],
        model_fingerprint=prediction.model_fingerprint,
    )
    return prediction
