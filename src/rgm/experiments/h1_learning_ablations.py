"""Deterministic synthetic ablations for H1 learning-channel mechanisms.

These mechanism checks are not bAbI results and are not a substitute for the
frozen external-task campaign. They isolate whether each declared error route
changes only its designated learner under matched observations.
"""
from __future__ import annotations

from typing import Any
import json

from rgm.leptograph.m4.composition import Entity, RelationInstance, RelationType
from rgm.leptograph.m4.evidence import NaryEvent, Participant
from rgm.leptograph.m4.learning import (
    EligibilityEvent, ErrorChannel, LearningRuntime, fingerprint,
)


def _relation(identifier: str, relation_name: str) -> RelationInstance:
    return RelationInstance(
        identifier, RelationType(relation_name, "person", "place"),
        Entity("person-1", "person"), Entity("place-1", "place"),
        1.0, 1.0, context="home", provenance=f"synthetic:{identifier}",
    )


def _event(identifier: str, event_type: str, recipient: str) -> NaryEvent:
    payload = identifier.encode("utf-8")
    import hashlib
    return NaryEvent(
        identifier, event_type,
        (Participant("giver", "mary", "person"),
         Participant("object", "cake", "object"),
         Participant("recipient", recipient, "person")),
        1.0, 1.0, "synthetic-ablation", f"synthetic://{identifier}",
        hashlib.sha256(payload).hexdigest(), context="home",
    )


def _count_nested(snapshot: dict) -> int:
    return sum(sum(bucket.values()) for bucket in snapshot.values())


def _run_variant(name: str, enabled: frozenset[ErrorChannel]) -> dict[str, Any]:
    learner = LearningRuntime(enabled_channels=enabled)
    learner.fit_relation_patterns([_relation("fit-relation", "located_at")], partition="fit")
    learner.fit_event_role_patterns([_event("fit-event", "gave", "fred")], partition="fit")

    issued = learner.begin_tick(tick=0, observed_at=0.0, context="home")
    relation_error = learner.observe_relation(
        _relation("observed-relation", "visited"), tick=1
    )
    role_error = learner.observe_nary_event(
        _event("observed-event", "moved", "bill"), tick=1
    )

    eligibility = EligibilityEvent(
        "eligibility-event", "feature-1", "slow", 1.0, 1.0, 1,
        1.0, "h1-soe-eligibility-v1",
    )
    learner.advance_temporal(1)
    learner.observe_eligibility(eligibility)
    learner.observe_temporal_error(0.5, tick=1)
    learner.observe_task_error("synthetic-task", 1.0)

    relation_count = _count_nested(learner.relations.snapshot())
    role_count = _count_nested(learner.event_roles.snapshot())
    temporal_updates = len(learner.temporal_credit.snapshot()["weights"])
    task_updates = len(learner.task_outcomes.outcomes.get("synthetic-task", ()))
    score_by_target = {
        learner.predictions.get(score.prediction_id).target_name: score.value
        for score in learner.predictions.scores
    }
    return {
        "variant": name,
        "enabled_channels": sorted(channel.value for channel in enabled),
        "issued_prediction_count": len(issued),
        "relation_error": relation_error,
        "event_role_error": role_error,
        "relation_pattern_observations": relation_count,
        "event_role_pattern_observations": role_count,
        "relation_online_updates": relation_count - 1,
        "event_role_online_updates": role_count - 1,
        "temporal_parameter_updates": temporal_updates,
        "task_outcome_updates": task_updates,
        "scored_prediction_errors": score_by_target,
        "learning_state_fingerprint": fingerprint(learner.snapshot()),
    }


def run_learning_ablation_campaign() -> dict[str, Any]:
    """Run matched one-factor-off ablations plus a no-learning control."""
    all_channels = frozenset(ErrorChannel)
    variants = [
        ("full", all_channels),
        ("without_temporal", all_channels - {ErrorChannel.TEMPORAL}),
        ("without_relational", all_channels - {ErrorChannel.RELATIONAL}),
        ("without_abstraction", all_channels - {ErrorChannel.ABSTRACTION}),
        ("without_task", all_channels - {ErrorChannel.TASK}),
        ("no_learning", frozenset()),
    ]
    rows = [_run_variant(name, enabled) for name, enabled in variants]
    by_name = {row["variant"]: row for row in rows}
    expected = {
        "full": (1, 1, 1, 1),
        "without_temporal": (1, 1, 0, 1),
        "without_relational": (0, 1, 1, 1),
        "without_abstraction": (1, 0, 1, 1),
        "without_task": (1, 1, 1, 0),
        "no_learning": (0, 0, 0, 0),
    }
    for name, values in expected.items():
        row = by_name[name]
        observed = (
            row["relation_online_updates"], row["event_role_online_updates"],
            row["temporal_parameter_updates"], row["task_outcome_updates"],
        )
        if observed != values:
            raise AssertionError(f"{name} ablation update isolation failed: {observed} != {values}")
    manifest = {
        "protocol": "H1-learning-channel-ablation-v1",
        "data": "deterministic synthetic typed relation and n-ary event-role sequence",
        "fit_partition": "one relation pattern and one n-ary event-role pattern",
        "evaluation": "one mismatching relation, one mismatching n-ary event, one temporal error, one task error",
        "variants": [name for name, _ in variants],
        "claim_boundary": "mechanism isolation only; not bAbI or generalization performance",
    }
    return {
        "schema": "h1-learning-ablation-result-v1",
        "manifest": manifest,
        "manifest_fingerprint": fingerprint(manifest),
        "rows": rows,
        "acceptance": "PASS",
    }
