"""Runtime bridge and prediction contracts for bAbI Tasks 11, 14 and 19.

This layer translates the frozen source adapters into the existing H1
HierarchicalRuntimeDirector / HLA / HLB interfaces. It does not implement a
second learner and it never passes evaluator labels into the observation path.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Any, Iterable, Mapping
import json

from rgm.experiments.babi_expansion_adapters import (
    ExpansionStory, ExpansionQuery, GoldLabel, Task11MentionEvent,
    Task11TrainingBinding, Task14TemporalEvent, Task19SpatialEdge,
    derive_task11_training_bindings,
)
from rgm.leptograph.m4.evidence import EvidenceStore, NaryEvent, Participant
from rgm.leptograph.m4.composition import Entity, RelationInstance, RelationType
from rgm.leptograph.m4.hierarchical import (
    HLAAdapter, HLBAdapter, HierarchicalRuntimeDirector,
)
from rgm.leptograph.m4.learning import (
    EligibilityEvent, ErrorChannel, LearningRuntime, Level, Prediction, PredictionJournal,
    TargetObservation, TargetSchema, fingerprint,
)


@dataclass(frozen=True)
class Task11SupervisionBundle:
    """Evaluator/training target bundle; never accepted by evidence ingestion."""
    query_id: str
    l0_mention_binding: dict[str, Any]
    l1_coreference_edge: dict[str, Any]
    l2_entity_state: dict[str, Any]
    source_ref: str


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


def _task11_learning_event(
    source_event: NaryEvent, binding: Task11TrainingBinding, *, context: str,
) -> NaryEvent:
    """Build a derived target for the learner journal, never for source evidence."""
    participants = source_event.participants + (
        Participant("entity", binding.entity_id, "entity"),
        Participant("antecedent_event", binding.antecedent_event_id, "mention_event"),
    )
    payload = {
        "source_event_id": source_event.event_id,
        "mention_event_id": binding.mention_event_id,
        "antecedent_event_id": binding.antecedent_event_id,
        "entity_id": binding.entity_id,
        "source_ref": binding.source_ref,
        "target_kind": binding.target_kind,
        "rule_id": binding.rule_id,
        "gold": binding.is_gold,
    }
    return NaryEvent(
        event_id=f"{source_event.event_id}:task11-learning-target",
        event_type="TASK11_MENTION_BINDING_TARGET",
        participants=participants,
        event_time=source_event.event_time,
        observed_at=source_event.observed_at,
        provenance=f"derived-learning-target:{binding.rule_id}",
        source_locator=binding.source_ref,
        payload_digest=_canonical_digest(payload),
        context=context,
    )


def _task11_learning_relation(
    source_event: NaryEvent,
    binding: Task11TrainingBinding,
    antecedent_source_ref: str,
    *,
    context: str,
) -> RelationInstance:
    """Build a typed L1 target for LearningRuntime only."""
    return RelationInstance(
        instance_id=f"{source_event.event_id}:task11-coreference-target",
        relation_type=RelationType(
            "corefers_with", "mention_event", "mention_event",
        ),
        subject=Entity(source_event.event_id, "mention_event"),
        object=Entity(binding.antecedent_event_id, "mention_event"),
        event_time=source_event.event_time,
        observed_at=source_event.observed_at,
        context=context,
        provenance=(
            f"{binding.source_ref}|{antecedent_source_ref}|{binding.rule_id}"
        ),
    )


def _task11_location_transition_relation(
    source_event: NaryEvent,
    binding: Task11TrainingBinding,
    *,
    previous_location: str | None,
    location: str,
) -> RelationInstance:
    """Build an HLB model relation, separate from durable source evidence.

    This typed transition is derived from a source mention plus its conservative
    weak binding. It is inserted with HLBAdapter.observe(), never observe_source(),
    and therefore lives in the rollback-scoped model relation store rather than
    the immutable source evidence journal.
    """
    previous = previous_location if previous_location is not None else "__START__"
    return RelationInstance(
        instance_id=f"{source_event.event_id}:task11-location-transition",
        relation_type=RelationType(
            "task11_location_transition", "entity_state", "location",
        ),
        subject=Entity(f"{binding.entity_id}|{previous}", "entity_state"),
        object=Entity(location, "location"),
        event_time=source_event.event_time,
        observed_at=source_event.observed_at,
        context="task11_location_transition",
        provenance=f"derived-learning-target:{binding.rule_id}|{binding.source_ref}",
    )


def to_nary_event(story: ExpansionStory, event: Any) -> NaryEvent:
    """Map one adapter event to the shared immutable, role-bound evidence type."""
    if story.task_id == 11 and isinstance(event, Task11MentionEvent):
        # Only source-observed fields cross the learner boundary. In particular,
        # no antecedent ID or resolved entity is fabricated by the parser.
        event_type = "ENTITY_LOCATION_MENTION"
        participants = (
            Participant("mention", event.surface_mention,
                        "pronoun" if event.is_pronoun else "name"),
            Participant("location", event.location, "location"),
        ) + ((Participant("grammatical_gender", event.grammatical_gender, "attribute"),)
             if event.grammatical_gender is not None else ())
        event_time = float(event.observed_at)
        observed_at = float(event.observed_at)
        locator = event.source_ref
        payload = {"event_id": event.event_id, "mention": event.surface_mention,
                   "pronoun": event.is_pronoun, "location": event.location,
                   "grammatical_gender": event.grammatical_gender}
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
        # Coreference is a prediction target, not an observed relation. The raw
        # mention event is retained at L0; no gold or heuristic antecedent edge
        # is injected into L1 ingestion.
        return ()
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
    def __init__(self, adapter: HLAAdapter | HLBAdapter, *, capacity: int = 100000,
                 learning_enabled: bool = True,
                 enabled_channels: Iterable[ErrorChannel] | None = None,
                 eligibility_capacity: int = 4096):
        if not isinstance(adapter, (HLAAdapter, HLBAdapter)):
            raise TypeError("adapter must be an existing HLAAdapter or HLBAdapter")
        if not isinstance(learning_enabled, bool):
            raise TypeError("learning_enabled must be a boolean")
        self.adapter = adapter
        self.learning_enabled = learning_enabled
        if enabled_channels is not None:
            # Configure ablation channels before any fit/online updates. Replacing
            # the learning runtime here guarantees an empty, condition-specific
            # learner while preserving the already-created HLA/HLB native bridge.
            channels = frozenset(enabled_channels)
            if any(not isinstance(channel, ErrorChannel) for channel in channels):
                raise TypeError("enabled_channels must contain ErrorChannel values")
            self.adapter.learning = LearningRuntime(
                enabled_channels=channels,
                eligibility_capacity=eligibility_capacity,
            )
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
        task11_bindings_by_id = {}
        task11_events_by_id = {}
        task11_previous_location: dict[str, str] = {}
        if story.task_id == 11:
            binding_report = derive_task11_training_bindings(story)
            task11_bindings_by_id = {
                binding.mention_event_id: binding
                for binding in binding_report["targets"]
            }
            task11_events_by_id = {event.event_id: event for event in story.events}
        for event in story.events:
            binding = None
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
            learning_nary_events = None
            eligibility_events = ()
            suppress_context_learning = False
            prediction_context = f"task{story.task_id}:pre:{event.event_id}"
            observed_context = f"task{story.task_id}:{type(event).__name__}"
            if story.task_id == 11 and isinstance(event, Task11MentionEvent):
                binding = task11_bindings_by_id.get(event.event_id)
                if binding is None:
                    # Preserve the source event, but an ambiguous/unresolved
                    # pronoun contributes no invented L0/L1/L2 learning target.
                    learning_nary_events = ()
                    learning_relations = ()
                    prediction_context = f"task11:unresolved:{event.event_id}"
                    observed_context = None
                    suppress_context_learning = True
                else:
                    previous_location = task11_previous_location.get(binding.entity_id)
                    previous_key = previous_location if previous_location is not None else "__START__"
                    entity_context = f"task11:entity:{binding.entity_id}:from:{previous_key}"
                    learning_nary_events = (
                        _task11_learning_event(nary, binding, context=entity_context),
                    )
                    if binding.target_kind == "weak_coreference":
                        antecedent = task11_events_by_id[binding.antecedent_event_id]
                        learning_relations = (
                            _task11_learning_relation(
                                nary, binding, antecedent.source_ref,
                                context=entity_context,
                            ),
                        )
                    else:
                        learning_relations = ()
                    prediction_context = entity_context
                    observed_context = f"location:{event.location}"
                    tick = self.director.event_tick + 1
                    eligible_levels = ["L0", "L2"]
                    if binding.target_kind == "weak_coreference":
                        eligible_levels.append("L1")
                    eligibility_events = tuple(
                        EligibilityEvent(
                            event_id=event.event_id,
                            feature_id=f"task11:{level.lower()}:binding",
                            channel=f"task11:{level}",
                            event_time=nary.event_time,
                            observed_at=nary.observed_at,
                            observed_tick=tick,
                            magnitude=1.0,
                            config_fingerprint="h1-soe-eligibility-v1",
                        )
                        for level in eligible_levels
                    )
            if isinstance(event, Task14TemporalEvent):
                temporal_history.append(event)
            result = self.director.exchange(
                event_time=nary.event_time, observed_at=nary.observed_at,
                event_features=features,
                relation_records=tuple((1, relation) for relation in relations)
                    if isinstance(self.adapter, HLBAdapter) else (),
                learning_relations=learning_relations,
                nary_events=(nary,),
                learning_nary_events=learning_nary_events,
                prediction_context=prediction_context,
                observed_context=observed_context,
                suppress_context_learning=suppress_context_learning,
                eligibility_events=eligibility_events,
                learn=self.learning_enabled,
            )
            if story.task_id == 11 and isinstance(event, Task11MentionEvent) and binding is not None:
                # HLB has a typed L2 transition model in its canonical relation
                # store. These are derived learner targets, not source evidence:
                # use observe(), never observe_source(), and honor the abstraction
                # ablation. HLA uses its shared L2 context-transition learner.
                if (self.learning_enabled
                        and isinstance(self.adapter, HLBAdapter)
                        and ErrorChannel.ABSTRACTION in self.adapter.learning.enabled_channels):
                    transition = _task11_location_transition_relation(
                        nary, binding,
                        previous_location=task11_previous_location.get(binding.entity_id),
                        location=event.location,
                    )
                    if self.adapter.store.count >= self.adapter.store.capacity:
                        raise RuntimeError("HLB Task 11 model relation capacity exhausted")
                    status = self.adapter.observe(1, transition)
                    if status.startswith("ABSTAIN"):
                        raise RuntimeError(f"HLB Task 11 model relation insertion failed: {status}")
                # The entity transition state is story-local. A new story starts
                # from __START__; no prior story's entity/location can be reused.
                task11_previous_location[binding.entity_id] = event.location
            outputs.append({"event_id": nary.event_id, "status": status,
                            "abstained": False, "runtime": result})
        return outputs

    def ingest_story_sequence(self, stories: tuple[ExpansionStory, ...] | list[ExpansionStory]) -> list[dict]:
        """Process independent Task 11 stories through one persistent learner.

        Story-local weak supervision is derived independently for each story;
        learner parameters, SOE eligibility/credit, native state and evidence
        stores persist across the sequence. Since bAbI line numbers restart at
        each story, the runtime event/observation clock is mapped to a monotonic
        sequence clock. Event IDs and source references preserve original lines.
        """
        stories = tuple(stories)
        if not stories:
            return []
        if any(story.task_id != 11 for story in stories):
            raise ValueError("persistent story sequences are restricted to Task 11")
        ids = [story.story_id for story in stories]
        if len(ids) != len(set(ids)):
            raise ValueError("persistent story sequence contains duplicate story IDs")

        outputs = []
        clock = (self.director.event_log[-1]["observed_at"] + 1.0
                 if self.director.event_log else 1.0)
        for story in stories:
            # Reset only the wrapper's one-story guard. The director, adapter,
            # native runtime, learner, evidence and temporal-credit state persist.
            self._story_id = None
            self._task_id = None
            shifted_events = tuple(
                replace(event, observed_at=clock + index)
                for index, event in enumerate(story.events)
            )
            sequence_story = replace(story, events=shifted_events)
            outputs.extend(self.ingest_story(sequence_story))
            clock += len(sequence_story.events) + 1.0
        return outputs

    def recover_witness(self, event_id: str, *, observation_cutoff: float) -> tuple[NaryEvent, ...]:
        return self.evidence.recover(event_id, observation_cutoff=observation_cutoff)


def task11_supervision_from_evaluator_label(
    query: ExpansionQuery, evaluator_label: Mapping[str, Any],
) -> Task11SupervisionBundle:
    """Materialize task targets from a sealed label, outside runtime ingestion.

    Task 11 source bAbI labels do not contain gold antecedent edges. The generated
    confirmatory stream supplies explicit L0/L1/L2 targets, but remains sealed
    from the runtime until forecasts have been issued.
    """
    if query.task_id != 11 or evaluator_label.get("query_id") != query.query_id:
        raise ValueError("Task 11 supervision query/label identity mismatch")
    target = evaluator_label.get("task11_supervision")
    required = {"l0_mention_binding", "l1_coreference_edge", "l2_entity_state"}
    if not isinstance(target, dict) or set(target) != required:
        raise ValueError("Task 11 evaluator label has an incomplete target-supervision bundle")
    l0, l1, l2 = (target["l0_mention_binding"], target["l1_coreference_edge"],
                  target["l2_entity_state"])
    if not all(isinstance(row, dict) for row in (l0, l1, l2)):
        raise ValueError("Task 11 supervision targets must be structured objects")
    if l0.get("entity_id") != query.entity or l2.get("entity_id") != query.entity:
        raise ValueError("Task 11 supervision target entity does not match query")
    source_ref = str(evaluator_label.get("source_ref", ""))
    if not source_ref:
        raise ValueError("Task 11 supervision source provenance is required")
    return Task11SupervisionBundle(query.query_id, l0, l1, l2, source_ref)


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

    def score_task11_supervision(
        self, query: ExpansionQuery, supervision: Task11SupervisionBundle, *,
        evaluated_tick: int, observed_at: float,
    ) -> dict[str, Any]:
        """Score L0/L1/L2 only after forecasts; this does not ingest labels as evidence."""
        if self.contract.task_id != 11 or supervision.query_id != query.query_id:
            raise ValueError("Task 11 supervision cannot be scored against this forecast")
        if observed_at < float(query.observed_at) or evaluated_tick < query.observed_at:
            raise ValueError("Task 11 supervision cannot be observed before its query target")
        targets = {
            "L0": supervision.l0_mention_binding,
            "L1": supervision.l1_coreference_edge,
            "L2": supervision.l2_entity_state,
        }
        return {
            level: self.score_level_target(
                query, level, value=value, source_id=supervision.source_ref,
                event_time=float(query.observed_at), observed_at=observed_at,
                observed_tick=evaluated_tick,
            )
            for level, value in targets.items()
        }

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
