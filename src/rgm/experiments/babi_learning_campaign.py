"""Matched HLA/HLB bAbI structured learning campaign runner.

The task-answer executor is deterministic and evidence-backed. Learned prediction
metrics are reported separately; query accuracy is not claimed as learned QA.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Callable
import hashlib
import json
import math
import os
import time

import numpy as np

from rgm.experiments.babi_structured import (
    StructuredEvent, StructuredQuery, StructuredStory,
    task3_object_location_before_move, task5_answer_role,
)
from rgm.leptograph.m4.evidence import NaryEvent, Participant
from rgm.leptograph.m4.composition import Entity, RelationInstance, RelationType
from rgm.leptograph.m4.hierarchical import (
    HierarchicalRuntimeDirector, create_hla_adapter, create_hlb_adapter,
)
from rgm.leptograph.m4.learning import (
    EligibilityEvent, ErrorChannel, LearningRuntime,
)
from rgm.memory.soe import SOEMemory


# HLB keeps all source evidence and source relations across all four phases
# of one seed-condition. The frozen Task 3 input alone contains 154,786 events
# across warm-start, online, validation and confirmatory partitions. Task 5
# contributes 73,971 projected relation records because GIVE has two roles.
# 262,144 leaves headroom; run_campaign also checks exact input requirements
# before starting so later dataset growth cannot silently exhaust this journal.
HLB_CAPACITY = 262144
ELIGIBILITY_CAPACITY = 131072
SOE_DT = 0.01
# The pinned H0 native chain requires equal native state dimensions across
# adjacent levels. Preserve the three level-specific feature semantics in a
# common four-coordinate embedding, padding only unused trailing coordinates.
# Each level keeps its own two-channel SOE decay configuration.
SOE_BANK_CONFIG = (
    (4, (0.1, 0.4)),
    (4, (0.2, 0.7)),
    (4, (0.05, 0.3)),
)
CHANNELS = {
    "full_learning": frozenset(ErrorChannel),
    "no_temporal": frozenset({ErrorChannel.RELATIONAL, ErrorChannel.ABSTRACTION, ErrorChannel.TASK}),
    "no_relational": frozenset({ErrorChannel.TEMPORAL, ErrorChannel.ABSTRACTION, ErrorChannel.TASK}),
    "no_abstraction": frozenset({ErrorChannel.TEMPORAL, ErrorChannel.RELATIONAL, ErrorChannel.TASK}),
    "no_task": frozenset({ErrorChannel.TEMPORAL, ErrorChannel.RELATIONAL, ErrorChannel.ABSTRACTION}),
    "no_learning": frozenset(),
}
EVENT_CONTEXT = {"MOVE": "movement", "PICK_UP": "acquisition", "DROP": "release", "GIVE": "transfer"}
CONTEXT_CODE = {"start": 0.0, "movement": 0.2, "acquisition": 0.4,
                "release": 0.6, "transfer": 0.8, "query": 1.0}
EVENT_CODE = {"MOVE": 0.0, "PICK_UP": 1.0 / 3.0, "DROP": 2.0 / 3.0, "GIVE": 1.0}
ENTITY_TYPES = {
    "actor": "person", "giver": "person", "recipient": "person",
    "object": "object", "destination": "location",
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return _jsonable(value.value)
    if hasattr(value, "__dataclass_fields__"):
        return _jsonable(asdict(value))
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def _digest_json(value: Any) -> str:
    payload = json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _model_state(learning: LearningRuntime) -> dict[str, Any]:
    return {
        "level0": learning.level0.snapshot(),
        "relations": learning.relations.snapshot(),
        "event_roles": learning.event_roles.snapshot(),
        "context_transitions": learning.context_transitions.snapshot(),
        "temporal_credit": learning.temporal_credit.snapshot(),
        "task_outcomes": learning.task_outcomes.snapshot(),
    }


def model_fingerprint(learning: LearningRuntime) -> str:
    return _digest_json(_model_state(learning))


def _capacity_requirements(*story_phases) -> dict[str, int]:
    """Count the persistent HLB source records required by the complete campaign."""
    event_count = 0
    relation_count = 0
    for phase in story_phases:
        for story, _labels in phase:
            event_count += len(story.events)
            relation_count += sum(
                len(_make_relations(event, "capacity-preflight"))
                for event in story.events
            )
    return {
        "source_event_count": event_count,
        "source_relation_count": relation_count,
    }


def _load_stories(input_path: Path, labels_path: Path | None = None) -> list[tuple[StructuredStory, dict[str, dict[str, Any]]]]:
    labels: dict[str, dict[str, Any]] = {}
    if labels_path is not None:
        labels = {
            row["query_id"]: row
            for row in (json.loads(line) for line in labels_path.read_text(encoding="utf-8").splitlines() if line)
        }
    result = []
    for line in input_path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        row = json.loads(line)
        events = tuple(
            StructuredEvent(
                event["event_id"], event["event_type"],
                tuple(tuple(pair) for pair in event["roles"]),
                int(event["event_time"]), int(event["observed_at"]), event["source_ref"],
            )
            for event in row["events"]
        )
        queries = tuple(
            StructuredQuery(
                query["query_id"], query["story_id"], int(query["task_id"]),
                query["query_type"], query["answer_role"], int(query["observed_at"]),
                query["source_ref"],
                object_id=query.get("object_id"),
                destination_id=query.get("destination_id"),
                target_event_id=query.get("target_event_id"),
                bound_roles=tuple(tuple(pair) for pair in query.get("bound_roles", ())),
            )
            for query in row["queries"]
        )
        story = StructuredStory(row["story_id"], events, queries)
        result.append((story, {q.query_id: labels[q.query_id] for q in queries if q.query_id in labels}))
    return result


def _ordered(stories, seed: int):
    return sorted(stories, key=lambda item: hashlib.sha256(
        f"{seed}:{item[0].story_id}".encode("utf-8")
    ).digest())


def _event_context(event: StructuredEvent) -> str:
    return EVENT_CONTEXT[event.event_type]


def _payload(event: StructuredEvent) -> bytes:
    return json.dumps({
        "event_id": event.event_id,
        "event_type": event.event_type,
        "roles": list(event.roles),
        "source_ref": event.source_ref,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _make_nary(event: StructuredEvent, context: str, source_name: str) -> NaryEvent:
    participants = tuple(
        Participant(role, entity_id, ENTITY_TYPES[role])
        for role, entity_id in event.roles
    )
    payload = _payload(event)
    return NaryEvent(
        event.event_id, event.event_type.lower(), participants,
        float(event.event_time), float(event.observed_at), source_name,
        event.source_ref, hashlib.sha256(payload).hexdigest(), context,
    )


def _make_relations(event: StructuredEvent, context: str) -> tuple[RelationInstance, ...]:
    roles = event.role_map()
    pairs: list[tuple[str, str, str, str, str]] = []
    if event.event_type == "MOVE":
        pairs.append(("located_at", "person", roles["actor"], "location", roles["destination"]))
    elif event.event_type == "PICK_UP":
        pairs.append(("holds", "person", roles["actor"], "object", roles["object"]))
    elif event.event_type == "DROP":
        pairs.append(("released", "person", roles["actor"], "object", roles["object"]))
    elif event.event_type == "GIVE":
        pairs.extend((
            ("gave_to", "person", roles["giver"], "person", roles["recipient"]),
            ("gave_object", "person", roles["giver"], "object", roles["object"]),
        ))
    records = []
    for name, subject_type, subject_id, object_type, object_id in pairs:
        signature = RelationType(name, subject_type, object_type)
        records.append(RelationInstance(
            f"{event.event_id}:rel:{name}", signature,
            Entity(subject_id, subject_type), Entity(object_id, object_type),
            float(event.event_time), float(event.observed_at), context,
            provenance=f"source={event.source_ref};event={event.event_id};relation={name}",
        ))
    return tuple(records)


def _features(task_id: int, item: Any, previous_context: str,
              index: int, total: int) -> dict[int, list[float]]:
    context_code = CONTEXT_CODE[previous_context]
    if isinstance(item, StructuredEvent):
        roles = item.role_map()
        unique_entities = len(set(roles.values()))
        l0 = [EVENT_CODE[item.event_type], min(1.0, len(roles) / 3.0), 0.0, 0.0]
        l1 = [min(1.0, len(roles) / 3.0), min(1.0, unique_entities / 3.0), context_code, 0.0]
        l2 = [task_id / 5.0, index / max(total, 1), context_code, 0.0]
    else:
        l0 = [1.0, 0.0, 0.0, 0.0]
        l1 = [0.0, 0.0, context_code, 0.0]
        l2 = [task_id / 5.0, index / max(total, 1), context_code, 1.0]
    return {0: l0, 1: l1, 2: l2}


def _timeline(story: StructuredStory):
    items = [(event.observed_at, 0, event) for event in story.events]
    items.extend((query.observed_at, 1, query) for query in story.queries)
    return sorted(items, key=lambda item: (item[0], item[1]))


def _fit_warm_start(learning: LearningRuntime, stories, task_id: int) -> None:
    l0_features: list[list[float]] = []
    relation_patterns: list[RelationInstance] = []
    event_patterns: list[NaryEvent] = []
    context_transitions: list[tuple[str, str]] = []
    for story, _labels in stories:
        current_context = "start"
        timeline = _timeline(story)
        for index, (_time, kind, item) in enumerate(timeline, start=1):
            features = _features(task_id, item, current_context, index, len(timeline))
            l0_features.append(features[0])
            if kind == 0:
                event = item
                event_patterns.append(_make_nary(event, current_context, "babi-en10k-fit"))
                relation_patterns.extend(_make_relations(event, current_context))
                next_context = _event_context(event)
            else:
                next_context = "query"
            context_transitions.append((current_context, next_context))
            current_context = next_context
    learning.fit_level0_predictor(l0_features, partition="fit")
    learning.fit_relation_patterns(relation_patterns, partition="fit")
    learning.fit_event_role_patterns(event_patterns, partition="fit")
    learning.fit_context_transitions(context_transitions, partition="fit")


def _soe_fingerprint(memories) -> str:
    return _digest_json({
        "dt": SOE_DT,
        "banks": [
            {"feature_dim": memory.feature_dim, "decay_rates": list(memory.decay_rates)}
            for memory in memories
        ],
    })


def _make_eligibility(adapter, event: StructuredEvent, global_time: int,
                      source_tick: int, soe_fingerprint: str) -> tuple[EligibilityEvent, ...]:
    result = []
    for level, memory in enumerate(adapter.bridge.memories):
        traces = np.asarray(memory.snapshot(), dtype=float)
        for channel in range(traces.shape[0]):
            magnitude = float(np.linalg.norm(traces[channel, :]))
            feature_id = f"soe_l{level}_c{channel}"
            result.append(EligibilityEvent(
                event.event_id, feature_id, feature_id,
                float(global_time), float(global_time), source_tick,
                magnitude, soe_fingerprint,
            ))
    return tuple(result)


def _from_nary(event: NaryEvent) -> StructuredEvent:
    return StructuredEvent(
        event.event_id, event.event_type.upper(),
        tuple(sorted((p.role, p.entity_id) for p in event.participants)),
        int(event.event_time), int(event.observed_at), event.source_locator,
    )


def _query_events(adapter, architecture: str, story_id: str,
                  cutoff: int, caller_events: list[StructuredEvent]) -> list[StructuredEvent]:
    if architecture == "HLA":
        return [event for event in caller_events if event.observed_at <= cutoff]
    recovered = []
    # caller_events is already scoped to this story. Recover exact source
    # witnesses without scanning/rebuilding the global evidence-ID tuple.
    for caller_event in caller_events:
        source_events = adapter.recover_evidence(
            caller_event.event_id, observation_cutoff=float(cutoff)
        )
        for event in source_events:
            recovered.append(_from_nary(event))
    return sorted(
        {event.event_id: event for event in recovered}.values(),
        key=lambda event: (event.observed_at, event.event_time, event.event_id),
    )


def _derive_support(story: StructuredStory, query: StructuredQuery) -> list[str]:
    if query.task_id == 5:
        matches = [
            event for event in story.events
            if event.event_type == "GIVE"
            and event.observed_at <= query.observed_at
            and all(event.role_map().get(role) == value for role, value in query.bound_roles)
        ]
        if not matches:
            return []
        return [max(matches, key=lambda event: (event.event_time, event.event_id)).event_id]
    target = next((event for event in story.events if event.event_id == query.target_event_id), None)
    if target is None:
        return []
    roles = target.role_map()
    prior = [event for event in story.events if event.event_time < target.event_time]
    moves = [event for event in prior if event.event_type == "MOVE" and event.role_map().get("actor") == roles.get("actor")]
    pickups = [
        event for event in prior if event.event_type == "PICK_UP"
        and event.role_map().get("actor") == roles.get("actor")
        and event.role_map().get("object") == query.object_id
    ]
    if not moves or not pickups:
        return [target.event_id]
    return [max(moves, key=lambda e: e.event_time).event_id,
            max(pickups, key=lambda e: e.event_time).event_id, target.event_id]


def _reference_label(story: StructuredStory, query: StructuredQuery) -> dict[str, Any]:
    if query.task_id == 3:
        answer = task3_object_location_before_move(
            story.events, object_id=query.object_id or "",
            destination_id=query.destination_id or "",
            target_event_id=query.target_event_id or "",
            observation_cutoff=query.observed_at,
        )
    else:
        values = task5_answer_role(
            story.events, bound_roles=dict(query.bound_roles),
            answer_role=query.answer_role, observation_cutoff=query.observed_at,
        )
        answer = values[0] if len(values) == 1 else None
    return {"gold_answer": answer, "support_event_ids": _derive_support(story, query)}


def _score_prediction_delta(adapter, start_index: int) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    scores = adapter.learning.predictions.scores[start_index:]
    for score in scores:
        prediction = adapter.learning.predictions.get(score.prediction_id)
        name = prediction.target_name
        metric = str(score.metric)
        row = grouped.setdefault(name, {"metric": metric, "count": 0, "values": [], "correct": 0})
        row["count"] += 1
        row["values"].append(float(score.value))
        if metric == "exact_match":
            row["correct"] += int(float(score.value) == 0.0)
        elif metric == "accuracy":
            row["correct"] += int(float(score.value) == 1.0)
    output = {}
    for name, row in grouped.items():
        values = row.pop("values")
        output[name] = {
            "metric": row["metric"],
            "count": row["count"],
            "mean_value": float(sum(values) / len(values)) if values else None,
            "accuracy": (row["correct"] / row["count"]
                         if row["metric"] in {"exact_match", "accuracy"} and row["count"] else None),
        }
    return output


def _query_answer(task_id: int, events: list[StructuredEvent], query: StructuredQuery,
                  cutoff: int) -> str | None:
    if task_id == 3:
        return task3_object_location_before_move(
            events, object_id=query.object_id or "",
            destination_id=query.destination_id or "",
            target_event_id=query.target_event_id or "",
            observation_cutoff=cutoff,
        )
    values = task5_answer_role(
        events, bound_roles=dict(query.bound_roles),
        answer_role=query.answer_role, observation_cutoff=cutoff,
    )
    return values[0] if len(values) == 1 else None


def _reset_episode(adapter, baseline_native_checkpoint: dict[str, Any], gfe_module) -> None:
    """Reset transient SOE/native/eligibility state while retaining learned models and HLB evidence."""
    for memory in adapter.bridge.memories:
        memory.reset()
    runtime = adapter.bridge.runtime
    checkpoint = deepcopy(baseline_native_checkpoint)
    checkpoint["step_count"] = runtime.step_count
    checkpoint.pop("payload_sha256", None)
    checkpoint["payload_sha256"] = hashlib.sha256(
        gfe_module._canonical_json(checkpoint).encode("utf-8")
    ).hexdigest()
    runtime.restore(checkpoint)
    adapter.learning.reset_episode_eligibility(
        tick=adapter.ticks,
        observed_at=adapter.learning._last_observed_at,
    )


def _process_phase(adapter, director, architecture: str, task_id: int, stories,
                   phase: str, learn: bool, source_name: str,
                   soe_fingerprint: str, global_clock: int, baseline_native_checkpoint: dict[str, Any], gfe_module,
                   progress_callback: Callable[[dict[str, Any]], None] | None = None) -> tuple[dict[str, Any], int]:
    score_start = len(adapter.learning.predictions.scores)
    totals = {
        "queries": 0, "eligible_queries": 0, "quarantined_queries": 0,
        "correct": 0, "abstained": 0,
        "support_total": 0, "support_available": 0,
        "provenance_checked": 0, "provenance_failures": 0,
        "evidence_capacity_misses": 0, "false_witnesses": 0,
    }
    for story_index, (story, story_labels) in enumerate(stories, start=1):
        _reset_episode(adapter, baseline_native_checkpoint, gfe_module)
        offset = global_clock + 1
        seen_events: list[StructuredEvent] = []
        source_payloads: dict[str, bytes] = {}
        nary_by_id: dict[str, NaryEvent] = {}
        current_context = "start"
        timeline = _timeline(story)
        for index, (_local_time, kind, item) in enumerate(timeline, start=1):
            global_time = offset + int(item.observed_at)
            if kind == 0:
                event = item
                global_event = replace(
                    event, event_time=offset + int(event.event_time),
                    observed_at=offset + int(event.observed_at),
                )
                nary = _make_nary(global_event, current_context, source_name)
                payload = _payload(global_event)
                source_payloads[global_event.source_ref] = payload
                nary_by_id[event.event_id] = nary
                relations = _make_relations(global_event, current_context)
                eligibility = _make_eligibility(
                    adapter, global_event, global_time, adapter.ticks + 1, soe_fingerprint
                ) if learn else ()
                features = _features(task_id, event, current_context, index, len(timeline))
                kwargs = {
                    "event_time": float(global_time), "observed_at": float(global_time),
                    "event_features": features, "prediction_context": current_context,
                    "observed_context": _event_context(event), "nary_events": (nary,),
                    "eligibility_events": eligibility, "learn": learn,
                }
                if architecture == "HLB":
                    kwargs["relation_records"] = tuple((1, relation) for relation in relations)
                else:
                    kwargs["learning_relations"] = relations
                result = director.exchange(**kwargs)
                if architecture == "HLB" and not adapter.evidence.has_event(event.event_id):
                    totals["evidence_capacity_misses"] += 1
                seen_events.append(global_event)
                current_context = _event_context(event)
            else:
                query = item
                global_query = replace(query, observed_at=global_time)
                evidence_events = _query_events(
                    adapter, architecture, story.story_id, global_time, seen_events
                )
                evidence_ids = {event.event_id for event in evidence_events}
                if any(not event_id.startswith(story.story_id + ":") for event_id in evidence_ids):
                    totals["false_witnesses"] += 1
                label = story_labels.get(query.query_id)
                if label is None:
                    label = _reference_label(story, query)
                support_ids = list(label.get("support_event_ids", ()))
                answer = _query_answer(task_id, evidence_events, global_query, global_time)
                gold = label.get("gold_answer")
                totals["queries"] += 1
                quarantined = label.get("audit_status") == "quarantined"
                task_outcome = None
                if quarantined:
                    totals["quarantined_queries"] += 1
                else:
                    totals["eligible_queries"] += 1
                    totals["support_total"] += len(support_ids)
                    available = [event_id for event_id in support_ids if event_id in evidence_ids]
                    totals["support_available"] += len(available)
                    if answer is None:
                        totals["abstained"] += 1
                    elif answer == gold:
                        totals["correct"] += 1
                    if architecture == "HLB":
                        for event_id in available:
                            totals["provenance_checked"] += 1
                            if not adapter.verify_event_provenance(
                                event_id, lambda locator: source_payloads.get(locator)
                            ):
                                totals["provenance_failures"] += 1
                    else:
                        for event_id in available:
                            totals["provenance_checked"] += 1
                            original = nary_by_id.get(event_id)
                            if original is None or hashlib.sha256(
                                source_payloads.get(original.source_locator, b"")
                            ).hexdigest() != original.payload_digest:
                                totals["provenance_failures"] += 1
                    task_error = 0.0 if answer == gold else 1.0
                    task_outcome = (f"task{task_id}", task_error)
                query_features = _features(task_id, query, current_context, index, len(timeline))
                director.exchange(
                    event_time=float(global_time), observed_at=float(global_time),
                    event_features=query_features, prediction_context=current_context,
                    observed_context="query",
                    task_outcome=task_outcome, learn=learn,
                )
                current_context = "query"
        global_clock = offset + max(
            [int(event.observed_at) for event in story.events]
            + [int(query.observed_at) for query in story.queries] + [0]
        ) + 1
        if progress_callback is not None:
            progress_callback({
                "phase": phase,
                "stories_completed": story_index,
                "stories_expected": len(stories),
                "queries_completed": totals["queries"],
                "eligible_queries_completed": totals["eligible_queries"],
                "native_steps": adapter.bridge.runtime.step_count,
                "adapter_ticks": adapter.ticks,
            })

    predictions = _score_prediction_delta(adapter, score_start)
    query_count = totals["eligible_queries"]
    support_total = totals["support_total"]
    metrics = {
        "phase": phase,
        "learn_enabled": learn,
        **totals,
        "eligible_query_coverage": query_count / totals["queries"] if totals["queries"] else None,
        "quarantine_fraction": totals["quarantined_queries"] / totals["queries"] if totals["queries"] else 0.0,
        "query_accuracy": totals["correct"] / query_count if query_count else None,
        "abstention_rate": totals["abstained"] / query_count if query_count else None,
        "support_witness_recall": (
            totals["support_available"] / support_total if support_total else None
        ),
        "cross_story_witness_count": totals["false_witnesses"],
        "provenance_failure_rate": (
            totals["provenance_failures"] / totals["provenance_checked"]
            if totals["provenance_checked"] else 0.0
        ),
        "prediction_metrics": predictions,
    }
    return metrics, global_clock


def _make_adapter(architecture: str, gfe_module, native_library,
                  enabled_channels: frozenset[ErrorChannel]):
    memories = [
        SOEMemory(feature_dim=dim, decay_rates=decays)
        for dim, decays in SOE_BANK_CONFIG
    ]
    kernels = [
        {"gamma": list(reversed(decays)), "w": [0.5, 0.5]}
        for _dim, decays in SOE_BANK_CONFIG
    ]
    soe_fingerprint = _digest_json({
        "dt": SOE_DT, "banks": SOE_BANK_CONFIG, "kernels": kernels,
    })
    runtime_factory = gfe_module.create_persistent_hierarchy_runtime
    if architecture == "HLA":
        adapter = create_hla_adapter(
            native_library, memories, kernels, dt=SOE_DT, runtime_factory=runtime_factory,
        )
    else:
        adapter = create_hlb_adapter(
            native_library, memories, kernels, dt=SOE_DT, runtime_factory=runtime_factory,
            capacity=HLB_CAPACITY,
        )
    adapter.learning = LearningRuntime(
        enabled_channels=enabled_channels,
        eligibility_decay=0.9,
        eligibility_capacity=ELIGIBILITY_CAPACITY,
        eligibility_config_fingerprint=soe_fingerprint,
    )
    return adapter, soe_fingerprint


def _fit_and_process(
    task_id: int, architecture: str, variant: str, seed: int,
    warm_start, online, validation, confirmatory,
    gfe_module, native_library, source_manifest: dict[str, Any],
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    adapter, soe_fingerprint = _make_adapter(
        architecture, gfe_module, native_library, CHANNELS[variant]
    )
    director = HierarchicalRuntimeDirector(adapter)
    baseline_native_checkpoint = adapter.bridge.runtime.checkpoint()
    warm_order = _ordered(warm_start, seed)
    online_order = _ordered(online, seed)
    validation_order = _ordered(validation, seed)
    confirmatory_order = _ordered(confirmatory, seed)

    _fit_warm_start(adapter.learning, warm_order, task_id)
    global_clock = 0
    warm_metrics, global_clock = _process_phase(
        adapter, director, architecture, task_id, warm_order,
        "warm_start_dynamics", False, "babi-v1.2-en10k-fit",
        soe_fingerprint, global_clock, baseline_native_checkpoint, gfe_module,
        progress_callback=progress_callback,
    )
    model_before_online = _model_state(adapter.learning)
    online_metrics, global_clock = _process_phase(
        adapter, director, architecture, task_id, online_order,
        "online_adaptation", True, "babi-v1.2-en10k-fit",
        soe_fingerprint, global_clock, baseline_native_checkpoint, gfe_module,
        progress_callback=progress_callback,
    )
    model_after_online = _model_state(adapter.learning)
    candidate_fingerprint = model_fingerprint(adapter.learning)
    online_changes = {
        key: _digest_json(model_before_online[key]) != _digest_json(model_after_online[key])
        for key in model_before_online
    }

    validation_metrics, global_clock = _process_phase(
        adapter, director, architecture, task_id, validation_order,
        "validation", False, "babi-v1.2-en10k-validation",
        soe_fingerprint, global_clock, baseline_native_checkpoint, gfe_module,
        progress_callback=progress_callback,
    )
    fingerprint_after_validation = model_fingerprint(adapter.learning)
    if fingerprint_after_validation != candidate_fingerprint:
        raise RuntimeError("score-only validation mutated candidate learner parameters")

    accepted = (
        validation_metrics["query_accuracy"] == 1.0
        and validation_metrics["support_witness_recall"] == 1.0
        and validation_metrics["provenance_failures"] == 0
        and validation_metrics["evidence_capacity_misses"] == 0
    )
    confirmatory_metrics = None
    fingerprint_after_confirmatory = None
    if accepted:
        # Gold answers and witness IDs are derived only now, after candidate freeze.
        confirmatory_metrics, global_clock = _process_phase(
            adapter, director, architecture, task_id, confirmatory_order,
            "generated_confirmatory", False, "babi-synthetic-confirmatory-v1.2",
            soe_fingerprint, global_clock, baseline_native_checkpoint, gfe_module,
            progress_callback=progress_callback,
        )
        fingerprint_after_confirmatory = model_fingerprint(adapter.learning)
        if fingerprint_after_confirmatory != candidate_fingerprint:
            raise RuntimeError("score-only confirmatory evaluation mutated candidate parameters")

    runtime = adapter.bridge.runtime
    prediction_status_counts: dict[str, int] = {}
    for prediction in adapter.learning.predictions._predictions.values():
        status = prediction.status.value
        prediction_status_counts[status] = prediction_status_counts.get(status, 0) + 1
    output = {
        "protocol_id": "HLG-BABI-T3-T5-LEARNING-v1.2.2",
        "task_id": task_id,
        "architecture": architecture,
        "variant": variant,
        "seed": seed,
        "candidate_accepted_on_validation": accepted,
        "candidate_fingerprint": candidate_fingerprint,
        "candidate_fingerprint_after_validation": fingerprint_after_validation,
        "candidate_fingerprint_after_confirmatory": fingerprint_after_confirmatory,
        "online_learner_state_changed": online_changes,
        "phases": {
            "warm_start_dynamics": warm_metrics,
            "online_adaptation": online_metrics,
            "validation": validation_metrics,
            "generated_confirmatory": confirmatory_metrics,
        },
        "runtime": {
            "native_steps": runtime.step_count,
            "adapter_ticks": adapter.ticks,
            "one_native_step_per_tick": runtime.step_count == adapter.ticks,
            "hlb_evidence_count": len(adapter.evidence.event_ids) if architecture == "HLB" else 0,
            "hlb_relation_count": (
                (adapter.store.count() if callable(adapter.store.count) else adapter.store.count)
                if architecture == "HLB" else 0
            ),
            "eligibility_values": len(adapter.learning.eligibility.values(prediction_cutoff_tick=adapter.ticks)),
            "prediction_status_counts": prediction_status_counts,
            "temporal_credit_state_sha256": _digest_json(adapter.learning.temporal_credit.snapshot()),
            "soe_configuration_fingerprint": soe_fingerprint,
        },
        "source_manifest": source_manifest,
    }
    runtime.close()
    return output


def _write_campaign_checkpoint(
    output_path: Path, *, task_id: int, architecture: str,
    seeds: list[int], variants: list[str], results: list[dict[str, Any]],
    expected_run_count: int, complete: bool,
) -> dict[str, Any]:
    """Atomically persist an evidence snapshot after each completed run."""
    output = {
        "protocol_id": "HLG-BABI-T3-T5-LEARNING-v1.2.2",
        "task_id": task_id,
        "architecture": architecture,
        "seeds": seeds,
        "variants": list(variants),
        "status": "completed" if complete else "in_progress",
        "complete": complete,
        "expected_run_count": expected_run_count,
        "completed_run_count": len(results),
        "run_count": len(results),
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(output_path.name + ".tmp")
    temporary_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary_path.replace(output_path)
    return output


def _write_progress_checkpoint(output_path: Path, payload: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(output_path.name + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary_path.replace(output_path)


def run_campaign(task_id: int, architecture: str, data_root: Path,
                 annotation_root: Path, confirmatory_root: Path,
                 output_path: Path, seeds: list[int],
                 gfe_module, native_library,
                 variants: list[str] | None = None) -> dict[str, Any]:
    warm = _load_stories(
        annotation_root / f"task{task_id}-warm-start.inputs.jsonl",
        annotation_root / f"task{task_id}-warm-start.labels.jsonl",
    )
    online = _load_stories(
        annotation_root / f"task{task_id}-online-adaptation.inputs.jsonl",
        annotation_root / f"task{task_id}-online-adaptation.labels.jsonl",
    )
    validation = _load_stories(
        annotation_root / f"task{task_id}-validation.inputs.jsonl",
        annotation_root / f"task{task_id}-validation.labels.jsonl",
    )
    confirmatory = _load_stories(
        confirmatory_root / f"task{task_id}-confirmatory.inputs.jsonl"
    )
    configured_native_path = os.environ.get("GFE_CORE_LIB")
    native_path = (
        Path(configured_native_path).expanduser().resolve()
        if configured_native_path else
        Path(gfe_module.__file__).resolve().parent.parent / "c++ core" / "build-shared" / "libgfe_core.so"
    )
    if not native_path.is_file():
        raise RuntimeError(
            "cannot establish native runtime provenance: configured library does not exist at "
            f"{native_path}"
        )
    native_library_sha256 = hashlib.sha256(native_path.read_bytes()).hexdigest()
    campaign_manifest_path = Path("docs/experiments/HLG_BABI_TASKS_3_5_STRUCTURED_CAMPAIGN_v0_1.json")
    source_manifest = {
        "annotation_manifest_sha256": hashlib.sha256(
            (annotation_root / "annotation-manifest.json").read_bytes()
        ).hexdigest(),
        "confirmatory_manifest_sha256": hashlib.sha256(
            (confirmatory_root / "confirmatory-input-manifest.json").read_bytes()
        ).hexdigest(),
        "campaign_manifest_sha256": hashlib.sha256(campaign_manifest_path.read_bytes()).hexdigest()
            if campaign_manifest_path.exists() else None,
        "native_runtime_commit": os.environ.get("GFE_ABERCONICS_COMMIT"),
        "native_library_path": str(native_path),
        "native_library_sha256": native_library_sha256,
    }
    capacity_requirements = _capacity_requirements(warm, online, validation, confirmatory)
    if architecture == "HLB":
        required_capacity = max(
            capacity_requirements["source_event_count"],
            capacity_requirements["source_relation_count"],
        )
        if required_capacity > HLB_CAPACITY:
            raise RuntimeError(
                "HLB capacity preflight failed before execution: "
                f"requires {capacity_requirements['source_event_count']} source events and "
                f"{capacity_requirements['source_relation_count']} source relations, "
                f"configured capacity is {HLB_CAPACITY}"
            )
    source_manifest["campaign_capacity"] = {
        **capacity_requirements,
        "configured_hlb_capacity": HLB_CAPACITY,
        "preflight_passed": architecture != "HLB" or max(
            capacity_requirements["source_event_count"],
            capacity_requirements["source_relation_count"],
        ) <= HLB_CAPACITY,
    }
    variants = list(CHANNELS) if variants is None else list(variants)
    if not variants or len(variants) != len(set(variants)) or any(v not in CHANNELS for v in variants):
        raise ValueError("variants must be a non-empty unique subset of the frozen ablation conditions")
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("seeds must be non-empty and unique")
    expected_run_count = len(seeds) * len(variants)
    results: list[dict[str, Any]] = []
    progress_path = output_path.with_name(output_path.stem + ".progress.json")
    campaign_started = time.monotonic()
    _write_campaign_checkpoint(
        output_path, task_id=task_id, architecture=architecture,
        seeds=seeds, variants=variants, results=results,
        expected_run_count=expected_run_count, complete=False,
    )

    def report_progress(seed: int, variant: str, seed_index: int,
                        variant_index: int, details: dict[str, Any]) -> None:
        stories_done = int(details["stories_completed"])
        stories_expected = int(details["stories_expected"])
        if stories_done not in {1, stories_expected} and stories_done % 25 != 0:
            return
        payload = {
            "protocol_id": "HLG-BABI-T3-T5-LEARNING-v1.2.2",
            "status": "in_progress", "task_id": task_id,
            "architecture": architecture, "seed": seed, "variant": variant,
            "seed_index": seed_index, "seed_count": len(seeds),
            "variant_index": variant_index, "variant_count": len(variants),
            "completed_run_count": len(results),
            "expected_run_count": expected_run_count,
            **details,
            "elapsed_seconds": round(time.monotonic() - campaign_started, 3),
        }
        _write_progress_checkpoint(progress_path, payload)
        print(
            f"[campaign-progress] task={task_id} architecture={architecture} "
            f"seed={seed} ({seed_index}/{len(seeds)}) "
            f"variant={variant} ({variant_index}/{len(variants)}) "
            f"phase={details['phase']} stories={stories_done}/{stories_expected} "
            f"queries={details['queries_completed']} native_steps={details['native_steps']} "
            f"elapsed={payload['elapsed_seconds']:.1f}s",
            flush=True,
        )

    for seed_index, seed in enumerate(seeds, start=1):
        for variant_index, variant in enumerate(variants, start=1):
            _write_progress_checkpoint(progress_path, {
                "protocol_id": "HLG-BABI-T3-T5-LEARNING-v1.2.2",
                "status": "starting_run", "task_id": task_id,
                "architecture": architecture, "seed": seed, "variant": variant,
                "seed_index": seed_index, "seed_count": len(seeds),
                "variant_index": variant_index, "variant_count": len(variants),
                "completed_run_count": len(results),
                "expected_run_count": expected_run_count,
                "elapsed_seconds": round(time.monotonic() - campaign_started, 3),
            })
            result = _fit_and_process(
                task_id, architecture, variant, seed,
                warm, online, validation, confirmatory,
                gfe_module, native_library, source_manifest,
                progress_callback=lambda details, seed=seed, variant=variant,
                    seed_index=seed_index, variant_index=variant_index:
                    report_progress(seed, variant, seed_index, variant_index, details),
            )
            results.append(result)
            _write_campaign_checkpoint(
                output_path, task_id=task_id, architecture=architecture,
                seeds=seeds, variants=variants, results=results,
                expected_run_count=expected_run_count, complete=False,
            )
            print(
                f"[campaign-progress] task={task_id} architecture={architecture} "
                f"seed={seed} ({seed_index}/{len(seeds)}) "
                f"variant={variant} ({variant_index}/{len(variants)}) "
                f"completed={len(results)}/{expected_run_count}",
                flush=True,
            )
    completed = _write_campaign_checkpoint(
        output_path, task_id=task_id, architecture=architecture,
        seeds=seeds, variants=variants, results=results,
        expected_run_count=expected_run_count, complete=True,
    )
    _write_progress_checkpoint(progress_path, {
        "protocol_id": "HLG-BABI-T3-T5-LEARNING-v1.2.2",
        "status": "completed", "task_id": task_id,
        "architecture": architecture, "completed_run_count": len(results),
        "expected_run_count": expected_run_count,
        "elapsed_seconds": round(time.monotonic() - campaign_started, 3),
    })
    return completed
