"""Runtime bridge and prediction contracts for bAbI Tasks 11, 14 and 19.

This layer translates the frozen source adapters into the existing H1
HierarchicalRuntimeDirector / HLA / HLB interfaces. It does not implement a
second learner and it never passes evaluator labels into the observation path.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping
import json

from rgm.experiments.babi_expansion_adapters import (
    ExpansionStory, ExpansionQuery, GoldLabel, Task11MentionEvent,
    Task14TemporalEvent, Task19SpatialEdge,
)
from rgm.leptograph.m4.evidence import EvidenceStore, NaryEvent, Participant
from rgm.leptograph.m4.composition import Entity, RelationInstance, RelationType
from rgm.leptograph.m4.hierarchical import (
    HLAAdapter, HLBAdapter, HierarchicalRuntimeDirector,
)
from rgm.leptograph.m4.learning import (
    Level, Prediction, PredictionJournal, TargetObservation, TargetSchema,
    fingerprint,
)


@dataclass(frozen=True)
class TaskTargetContract:
    task_id: int
    l0: TargetSchema
    l1: TargetSchema
    l2: TargetSchema
    answer: TargetSchema


def target_contract(task_id: int) -> TaskTargetContract:
    """Task-specific targets preserve grounding, relation and context semantics."""
    specs = {
        11: ("mention_binding", "coreference_edge", "entity_state", "location_answer"),
        14: ("temporal_anchor", "temporal_precedence", "temporal_context", "before_location_answer"),
        19: ("spatial_edge", "path_composition", "route_context", "ordered_route_answer"),
    }
    if task_id not in specs:
        raise ValueError(f"unsupported expansion task: {task_id}")
    l0, l1, l2, answer = specs[task_id]
    return TaskTargetContract(
        task_id,
        TargetSchema(f"task{task_id}.l0.{l0}", Level.L0, "categorical", 1, "accuracy"),
        TargetSchema(f"task{task_id}.l1.{l1}", Level.L1, "relation", 1, "exact_match"),
        TargetSchema(f"task{task_id}.l2.{l2}", Level.L2, "context", 1, "accuracy"),
        TargetSchema(f"task{task_id}.answer.{answer}", Level.L2, "context", 1, "accuracy"),
    )


def _canonical_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def to_nary_event(story: ExpansionStory, event: Any) -> NaryEvent:
    """Map one adapter event to the shared immutable, role-bound evidence type."""
    if story.task_id == 11 and isinstance(event, Task11MentionEvent):
        event_type = "COREFERS_TO" if event.is_pronoun else "ENTITY_LOCATION_MENTION"
        participants = (
            Participant("entity", event.actor_entity, "person"),
            Participant("mention", event.surface_mention, "pronoun" if event.is_pronoun else "name"),
            Participant("location", event.location, "location"),
            Participant("antecedent", event.antecedent_event_id, "mention_event"),
        )
        event_time = float(event.observed_at)
        observed_at = float(event.observed_at)
        locator = event.source_ref
        payload = {"event_id": event.event_id, "entity": event.actor_entity,
                   "mention": event.surface_mention, "pronoun": event.is_pronoun,
                   "location": event.location, "antecedent": event.antecedent_event_id}
    elif story.task_id == 14 and isinstance(event, Task14TemporalEvent):
        event_type = "TEMPORAL_LOCATION_EVENT"
        participants = (
            Participant("actor", event.actor, "person"),
            Participant("destination", event.destination, "location"),
            Participant("temporal_anchor", event.temporal_anchor, "time_anchor"),
        )
        event_time = float(event.event_time[0]) / 1000.0
        observed_at = float(event.observed_at)
        locator = event.source_ref
        payload = {"event_id": event.event_id, "actor": event.actor,
                   "destination": event.destination, "anchor": event.temporal_anchor,
                   "event_time": list(event.event_time), "observed_at": event.observed_at}
    elif story.task_id == 19 and isinstance(event, Task19SpatialEdge):
        event_type = "SPATIAL_EDGE"
        participants = (
            Participant("start", event.start, "location"),
            Participant("end", event.end, "location"),
            Participant("direction", event.direction, "cardinal_direction"),
        )
        event_time = float(event.observed_at)
        observed_at = float(event.observed_at)
        locator = event.source_ref
        payload = {"event_id": event.event_id, "start": event.start,
                   "end": event.end, "direction": event.direction}
    else:
        raise TypeError("event type does not match its expansion story task")
    return NaryEvent(
        event.event_id, event_type, participants, event_time, observed_at,
        f"babi-v1.2-task-{story.task_id}", locator, _canonical_digest(payload),
        context=f"task{story.task_id}:{story.story_id}",
    )


def to_spatial_relations(event: Task19SpatialEdge) -> tuple[RelationInstance, RelationInstance]:
    """Create both directed orientations, retaining the same source witness."""
    inverse = {"north": "south", "south": "north", "east": "west", "west": "east"}
    forward = RelationInstance(
        instance_id=f"{event.event_id}:forward",
        relation_type=RelationType(f"spatial_{event.direction}", "location", "location"),
        subject=Entity(event.start, "location"),
        object=Entity(event.end, "location"),
        event_time=float(event.observed_at),
        observed_at=float(event.observed_at),
        context="task19_spatial",
        provenance=event.source_ref,
    )
    backward = RelationInstance(
        instance_id=f"{event.event_id}:inverse",
        relation_type=RelationType(f"spatial_{inverse[event.direction]}", "location", "location"),
        subject=Entity(event.end, "location"),
        object=Entity(event.start, "location"),
        event_time=float(event.observed_at),
        observed_at=float(event.observed_at),
        context="task19_spatial",
        provenance=event.source_ref,
    )
    return forward, backward


def to_spatial_relation(event: Task19SpatialEdge) -> RelationInstance:
    """Compatibility helper returning the forward directed edge."""
    return to_spatial_relations(event)[0]


def to_task_relations(
    story: ExpansionStory, event: Any, *,
    prior_temporal_events: tuple[Task14TemporalEvent, ...] = (),
) -> tuple[RelationInstance, ...]:
    """Materialize task-specific L1 relations with exact source provenance."""
    if story.task_id == 11 and isinstance(event, Task11MentionEvent):
        if not event.is_pronoun:
            return ()
        return (RelationInstance(
            instance_id=f"{event.event_id}:corefers_to",
            relation_type=RelationType("corefers_to", "mention_event", "mention_event"),
            subject=Entity(event.event_id, "mention_event"),
            object=Entity(event.antecedent_event_id, "mention_event"),
            event_time=float(event.observed_at),
            observed_at=float(event.observed_at),
            context=f"task11:{story.story_id}",
            provenance=event.source_ref,
        ),)
    if story.task_id == 14 and isinstance(event, Task14TemporalEvent):
        same_actor = [prior for prior in prior_temporal_events if prior.actor == event.actor]
        if not same_actor:
            return ()
        earlier = [prior for prior in same_actor if prior.event_time < event.event_time]
        later = [prior for prior in same_actor if prior.event_time > event.event_time]
        if earlier:
            before_event = max(earlier, key=lambda item: item.event_time)
            after_event = event
        elif later:
            before_event = event
            after_event = min(later, key=lambda item: item.event_time)
        else:
            return ()
        return (RelationInstance(
            instance_id=f"{before_event.event_id}:before:{after_event.event_id}",
            relation_type=RelationType("before", "temporal_event", "temporal_event"),
            subject=Entity(before_event.event_id, "temporal_event"),
            object=Entity(after_event.event_id, "temporal_event"),
            event_time=float(before_event.event_time[0]) / 1000.0,
            observed_at=float(event.observed_at),
            context=f"task14:{story.story_id}",
            provenance=f"{before_event.source_ref}|{after_event.source_ref}",
        ),)
    if story.task_id == 19 and isinstance(event, Task19SpatialEdge):
        return to_spatial_relations(event)
    raise TypeError("event type does not match its expansion story task")


def _feature_vector(task_id: int, event: Any, level: int, width: int) -> tuple[float, ...]:
    """Deterministic label-free projection shared by HLA and HLB."""
    payload = json.dumps(
        {"task": task_id, "level": level, "event": repr(event)},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    digest = sha256(payload).digest()
    values = tuple((digest[i % len(digest)] / 255.0) for i in range(width))
    return values


class BabiExpansionRuntime:
    """Feeds expansion observations through the existing H1 runtime director.

    HLA and HLB receive identical feature vectors, n-ary events and learning
    labels. HLB additionally retains the n-ary source journal and typed spatial
    relations using its existing durable stores. HLA uses this bridge's external
    evidence journal for exact witness recovery without retaining relation paths.
    """
    def __init__(self, adapter: HLAAdapter | HLBAdapter, *, capacity: int = 100000):
        if not isinstance(adapter, (HLAAdapter, HLBAdapter)):
            raise TypeError("adapter must be an existing HLAAdapter or HLBAdapter")
        self.adapter = adapter
        self.director = HierarchicalRuntimeDirector(adapter)
        admission_capacity = min(capacity, adapter.evidence.capacity) if isinstance(adapter, HLBAdapter) else capacity
        self._admission = EvidenceStore(admission_capacity)
        self.evidence = adapter.evidence if isinstance(adapter, HLBAdapter) else self._admission
        self._story_id: str | None = None
        self._task_id: int | None = None

    def ingest_story(self, story: ExpansionStory) -> list[dict]:
        if self._story_id is not None:
            raise RuntimeError("runtime instance is story-scoped; create a new episode for another story")
        self._story_id, self._task_id = story.story_id, story.task_id
        outputs = []
        temporal_history: list[Task14TemporalEvent] = []
        for event in story.events:
            nary = to_nary_event(story, event)
            status = self._admission.append(nary)
            if status == "ABSTAIN_CAPACITY":
                outputs.append({"event_id": nary.event_id, "status": status, "abstained": True})
                continue
            if isinstance(self.adapter, HLBAdapter) and self.evidence is self.adapter.evidence:
                # HLB's director also appends nary_events. The idempotent append
                # contract makes the preflight append safe and catches capacity
                # exhaustion before native state advances.
                pass
            features = {
                level: _feature_vector(story.task_id, event, level, self.adapter.feature_dims[level])
                for level in range(3)
            }
            relations = to_task_relations(
                story, event, prior_temporal_events=tuple(temporal_history),
            )
            learning_relations = (relations[0],) if relations else ()
            if isinstance(event, Task14TemporalEvent):
                temporal_history.append(event)
            result = self.director.exchange(
                event_time=nary.event_time, observed_at=nary.observed_at,
                event_features=features,
                relation_records=tuple((1, relation) for relation in relations)
                    if isinstance(self.adapter, HLBAdapter) else (),
                learning_relations=learning_relations,
                nary_events=(nary,),
                prediction_context=f"task{story.task_id}:pre:{event.event_id}",
                observed_context=f"task{story.task_id}:{type(event).__name__}",
            )
            outputs.append({"event_id": nary.event_id, "status": status,
                            "abstained": False, "runtime": result})
        return outputs

    def recover_witness(self, event_id: str, *, observation_cutoff: float) -> tuple[NaryEvent, ...]:
        return self.evidence.recover(event_id, observation_cutoff=observation_cutoff)


class ExpansionForecasts:
    """Evaluator-separated task-specific prediction lifecycle over the H1 journal."""
    def __init__(self, task_id: int):
        self.contract = target_contract(task_id)
        self.journal = PredictionJournal()
        self._sequence = 0

    def issue_query_forecasts(
        self, query: ExpansionQuery, *, issued_tick: int,
        issued_at: float, evidence_cutoff: float,
        l0_value: Any, l1_value: Any, l2_value: Any, answer_value: Any,
        model_fingerprint: str,
    ) -> tuple[Prediction, ...]:
        if query.task_id != self.contract.task_id:
            raise ValueError("query task does not match prediction contract")
        if issued_at > evidence_cutoff or issued_tick < 0 or query.observed_at <= evidence_cutoff:
            raise ValueError("forecast must precede the query target and its evidence cutoff")
        issued = []
        for schema, value, suffix in (
            (self.contract.l0, l0_value, "l0"),
            (self.contract.l1, l1_value, "l1"),
            (self.contract.l2, l2_value, "l2"),
            (self.contract.answer, answer_value, "answer"),
        ):
            self._sequence += 1
            prediction = Prediction(
                f"babi{query.task_id}-{suffix}-{self._sequence}",
                schema.level, schema.name, query.query_id, issued_tick, issued_at,
                schema.horizon_ticks, evidence_cutoff, value, model_fingerprint,
                fingerprint(schema.__dict__),
            )
            self.journal.issue(prediction)
            issued.append(prediction)
        return tuple(issued)

    def score_query(self, query: ExpansionQuery, label: GoldLabel, *,
                    evaluated_tick: int, observed_at: float) -> dict[str, Any]:
        """Evaluator-only method; labels never enter BabiExpansionRuntime."""
        if query.task_id != self.contract.task_id or label.query_id != query.query_id:
            raise ValueError("query/label identity mismatch")
        scored = {}
        for schema in (self.contract.l0, self.contract.l1, self.contract.l2, self.contract.answer):
            prediction_id = self.journal._active_by_target.get((schema.name, query.query_id))
            if prediction_id is None:
                continue
            prediction = self.journal.get(prediction_id)
            # Only the answer target is compared with the official answer. The
            # L0/L1/L2 targets must be scored against their own separately
            # materialized target values by score_level_target().
            if schema is not self.contract.answer:
                continue
            target = TargetObservation(
                schema.name, query.query_id, label.answer,
                float(query.observed_at), observed_at, evaluated_tick, label.source_ref,
            )
            scored[schema.name] = self.journal.score(
                prediction_id, target, schema, evaluated_tick=evaluated_tick,
            ).__dict__
        return scored

    def score_level_target(self, query: ExpansionQuery, level: str, *,
                           value: Any, source_id: str, event_time: float,
                           observed_at: float, observed_tick: int) -> dict[str, Any]:
        schemas = {"L0": self.contract.l0, "L1": self.contract.l1, "L2": self.contract.l2}
        if level not in schemas:
            raise ValueError("level must be L0, L1 or L2")
        schema = schemas[level]
        prediction_id = self.journal._active_by_target.get((schema.name, query.query_id))
        if prediction_id is None:
            raise KeyError(f"no active {level} forecast for query")
        target = TargetObservation(schema.name, query.query_id, value, event_time,
                                    observed_at, observed_tick, source_id)
        return self.journal.score(prediction_id, target, schema,
                                  evaluated_tick=observed_tick).__dict__
