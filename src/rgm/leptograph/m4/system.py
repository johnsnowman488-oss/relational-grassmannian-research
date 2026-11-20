"""Integrated HLG-M4 A/B relational memory systems.

A uses SOE temporal state and a learned readout without retaining relation
instances. B adds a bounded, persistent typed relation-instance store.
Candidate enumeration is task-visible retrieval; the learned readout ranks
candidates. The shared P0 composer validates every returned witness.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence
import copy
import math
import numpy as np

from rgm.memory import SOEMemory
from rgm.leptograph.m4.composition import (
    Entity, RelationType, RelationInstance, CompositionQuery,
    CompositionWitness, compose_paths,
)

@dataclass(frozen=True)
class M4Query:
    start: Entity
    goal: Entity
    context: str | None
    query_time: float
    observation_cutoff: float
    max_depth: int = 4
    max_event_gap: float | None = None

    def __post_init__(self):
        if self.max_depth < 1:
            raise ValueError("max_depth must be positive")
        if self.observation_cutoff > self.query_time:
            raise ValueError("observation_cutoff cannot exceed query_time")
        if not math.isfinite(self.query_time) or not math.isfinite(self.observation_cutoff):
            raise ValueError("query_time and observation_cutoff must be finite")
        if self.query_time < 0 or self.observation_cutoff < 0:
            raise ValueError("query times must be non-negative")
        if self.max_event_gap is not None and (
            not math.isfinite(self.max_event_gap) or self.max_event_gap < 0
        ):
            raise ValueError("max_event_gap must be finite and non-negative")

@dataclass(frozen=True)
class PathTrainingExample:
    relation_path: tuple[str, ...]
    label: int

    def __post_init__(self):
        if not self.relation_path or self.label not in (0, 1):
            raise ValueError("training examples require a non-empty path and binary label")

class PersistentRelationStore:
    """Identity-preserving B store. Capacity exhaustion never evicts."""
    def __init__(self, capacity: int = 4096):
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = int(capacity)
        self._records: dict[str, RelationInstance] = {}

    def insert(self, event: RelationInstance) -> str:
        existing = self._records.get(event.instance_id)
        if existing is not None:
            if existing != event:
                raise ValueError("relation instance ID collision with different content")
            return "ALREADY_STORED"
        if len(self._records) >= self.capacity:
            return "ABSTAIN_CAPACITY"
        self._records[event.instance_id] = event
        return "STORED"

    def visible(self, cutoff: float) -> tuple[RelationInstance, ...]:
        return tuple(sorted(
            (e for e in self._records.values() if e.observed_at <= cutoff),
            key=lambda e: (e.observed_at, e.event_time, e.instance_id),
        ))

    def snapshot(self) -> dict:
        return {"capacity": self.capacity, "records": tuple(self._records.values())}

    def restore(self, state: dict) -> None:
        capacity = int(state["capacity"])
        records = tuple(state["records"])
        if capacity < 1 or len(records) > capacity:
            raise ValueError("invalid relation-store snapshot")
        rebuilt = {}
        for event in records:
            if not isinstance(event, RelationInstance) or event.instance_id in rebuilt:
                raise ValueError("invalid or duplicate relation-store record")
            rebuilt[event.instance_id] = event
        self.capacity = capacity
        self._records = rebuilt

    @property
    def records(self) -> tuple[RelationInstance, ...]:
        return tuple(self._records.values())

    @property
    def state_bytes(self) -> int:
        # Deterministic payload accounting; Python allocator overhead is reported
        # separately as an implementation limitation, not silently guessed.
        total = 0
        for e in self._records.values():
            strings = (e.instance_id, e.subject.entity_id, e.subject.entity_type,
                       e.object.entity_id, e.object.entity_type, e.relation_type.name,
                       e.relation_type.domain, e.relation_type.codomain,
                       e.context or "", e.provenance or "")
            total += sum(len(s.encode("utf-8")) for s in strings)
            total += 8 * (3 if e.valid_until is not None else 2)
        return total

class M4ABSystem:
    """One common query/composition interface with architecture-specific memory.

    A queries only the event batch explicitly supplied to query(); it retains
    no relation instances. B queries its persistent store plus the current
    supplied batch. Both use the same P0 witness validator and learned scorer.
    """
    def __init__(
        self,
        architecture: str,
        relation_types: Sequence[RelationType],
        *,
        relation_capacity: int = 4096,
        max_path_depth: int = 4,
        min_probability: float = 0.5,
        min_margin: float = 0.05,
    ):
        if architecture not in {"A", "B"}:
            raise ValueError("architecture must be A or B")
        if max_path_depth < 1:
            raise ValueError("max_path_depth must be positive")
        names = [r.name for r in relation_types]
        if not names or len(set(names)) != len(names):
            raise ValueError("relation_types must have unique names")
        self.architecture = architecture
        self.max_path_depth = int(max_path_depth)
        self.relation_types = {r.name: r for r in relation_types}
        self.relation_index = {name: i for i, name in enumerate(names)}
        self.soe = SOEMemory(feature_dim=len(names))
        self.store = PersistentRelationStore(relation_capacity) if architecture == "B" else None
        self.readout_weights = np.zeros(
            (3 + self.max_path_depth) * len(names)
            + (self.max_path_depth - 1) * len(names) * len(names) + 1,
            dtype=float,
        )
        self.readout_bias = 0.0
        self.readout_fitted = False
        self.min_probability = float(min_probability)
        self.min_margin = float(min_margin)
        self.observation_count = 0
        self.last_observed_at = 0.0
        self.last_capacity_status = "OK"
        self.update_operations = 0
        self.query_operations = 0

    def observe(self, event: RelationInstance) -> str:
        if event.relation_type.name not in self.relation_index:
            raise ValueError("event relation type is outside the frozen vocabulary")
        if self.relation_types[event.relation_type.name] != event.relation_type:
            raise ValueError("event relation signature conflicts with frozen vocabulary")
        status = "OBSERVED"
        if self.architecture == "B":
            status = self.store.insert(event)
            if status == "ABSTAIN_CAPACITY":
                self.last_capacity_status = status
                return status
        feature = np.zeros(len(self.relation_index), dtype=float)
        feature[self.relation_index[event.relation_type.name]] = 1.0
        self.soe.update(feature, dt=0.0 if self.observation_count == 0 else max(
            0.0, event.observed_at - self.last_observed_at
        ))
        self.last_observed_at = max(self.last_observed_at, event.observed_at)
        self.observation_count += 1
        self.update_operations += len(feature) * self.soe.channel_count
        return status

    def advance_gap(self, dt: float) -> None:
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("gap must be finite and non-negative")
        self.soe.advance(dt)
        self.update_operations += self.soe.channels.size

    def _candidate_paths(self, events: Sequence[RelationInstance], query: M4Query):
        usable = [e for e in events
                  if e.observed_at <= query.observation_cutoff
                  and e.event_time <= query.query_time
                  and (e.valid_until is None or query.query_time < e.valid_until)
                  and (query.context is None or e.context in (None, query.context))]
        outgoing: dict[Entity, list[RelationInstance]] = {}
        for edge in usable:
            outgoing.setdefault(edge.subject, []).append(edge)
        for edges in outgoing.values():
            edges.sort(key=lambda e: (e.relation_type.name, e.instance_id))
        paths: set[tuple[str, ...]] = set()

        def walk(current: Entity, depth: int, path: tuple[str, ...],
                 prior_event_time: float | None, used: frozenset[str]):
            if current == query.goal and path:
                paths.add(path)
                return
            if depth >= query.max_depth:
                return
            for edge in outgoing.get(current, ()):
                if edge.instance_id in used:
                    continue
                if prior_event_time is not None:
                    if edge.event_time < prior_event_time:
                        continue
                    if query.max_event_gap is not None and edge.event_time - prior_event_time > query.max_event_gap:
                        continue
                walk(edge.object, depth + 1, path + (edge.relation_type.name,),
                     edge.event_time, used | {edge.instance_id})
        walk(query.start, 0, (), None, frozenset())
        return tuple(sorted(paths))

    def _features(self, path: Sequence[str]) -> np.ndarray:
        n = len(self.relation_index)
        if len(path) > self.max_path_depth:
            raise ValueError("candidate path exceeds the configured readout depth")
        counts = np.zeros(n, dtype=float)
        for name in path:
            if name not in self.relation_index:
                raise ValueError("candidate path contains unknown relation type")
            counts[self.relation_index[name]] += 1.0
        temporal = np.mean(self.soe.channels, axis=0)
        support = np.zeros(n, dtype=float)
        positional = np.zeros(self.max_path_depth * n, dtype=float)
        for position, name in enumerate(path):
            positional[position * n + self.relation_index[name]] = 1.0
        # Ordered adjacent-pair features let the linear readout distinguish
        # sequences with identical relation bags but different composition order.
        transitions = np.zeros((self.max_path_depth - 1) * n * n, dtype=float)
        for position, (left, right) in enumerate(zip(path, path[1:])):
            left_index = self.relation_index[left]
            right_index = self.relation_index[right]
            transitions[position * n * n + left_index * n + right_index] = 1.0
        if self.architecture == "B":
            for event in self.store.records:
                support[self.relation_index[event.relation_type.name]] += 1.0
            support = np.log1p(support)
        return np.concatenate([
            counts, temporal, np.zeros(n) if self.architecture == "A" else support,
            positional, transitions, [float(len(path))],
        ])

    def fit_readout(
        self,
        examples: Sequence[PathTrainingExample],
        *,
        learning_rate: float = 0.1,
        epochs: int = 400,
        l2: float = 1e-3,
    ) -> dict:
        if not examples or epochs < 1 or learning_rate <= 0 or l2 < 0:
            raise ValueError("invalid readout training configuration")
        x = np.asarray([self._features(e.relation_path) for e in examples], dtype=float)
        y = np.asarray([e.label for e in examples], dtype=float)
        if not np.all(np.isfinite(x)):
            raise ValueError("non-finite readout features")
        w = self.readout_weights.copy()
        b = float(self.readout_bias)
        for _ in range(epochs):
            z = np.clip(x @ w + b, -30.0, 30.0)
            p = 1.0 / (1.0 + np.exp(-z))
            error = p - y
            w -= learning_rate * ((x.T @ error) / len(y) + l2 * w)
            b -= learning_rate * float(np.mean(error))
        self.readout_weights = w
        self.readout_bias = b
        self.readout_fitted = True
        return {"examples": len(examples), "epochs": epochs,
                "training_accuracy": float(np.mean((1/(1+np.exp(-np.clip(x@w+b,-30,30))) >= 0.5) == y))}

    def query(self, query: M4Query, *, visible_events: Iterable[RelationInstance] = ()) -> dict:
        if not isinstance(query, M4Query):
            raise TypeError("query must be an M4Query")
        if query.max_depth > self.max_path_depth:
            return {"status": "ABSTAIN_DEPTH_UNSUPPORTED", "candidates": (), "witnesses": ()}
        if query.observation_cutoff < self.last_observed_at:
            return {"status": "ABSTAIN_CUTOFF_UNSUPPORTED", "candidates": (), "witnesses": ()}
        if not self.readout_fitted:
            return {"status": "ABSTAIN_UNTRAINED", "candidates": (), "witnesses": ()}
        events = list(visible_events)
        if self.architecture == "B":
            by_id = {e.instance_id: e for e in self.store.visible(query.observation_cutoff)}
            for e in events:
                prior = by_id.get(e.instance_id)
                if prior is not None and prior != e:
                    raise ValueError("visible event conflicts with persistent store")
                by_id[e.instance_id] = e
            events = list(by_id.values())
        else:
            # A has no persistent relation-instance memory: the caller must
            # supply the current task-visible evidence window explicitly.
            events = list(events)
        paths = self._candidate_paths(events, query)
        if not paths:
            return {"status": "ABSTAIN_NO_PATH", "candidates": (), "witnesses": ()}
        ranked = []
        for path in paths:
            features = np.asarray(self._features(path), dtype=float)
            z = float(np.clip(features @ self.readout_weights + self.readout_bias, -30, 30))
            probability = float(1.0 / (1.0 + math.exp(-z)))
            reference_query = CompositionQuery(
                query.start, tuple(self.relation_types[name] for name in path),
                query.context, query.query_time, query.observation_cutoff,
                max_event_gap=query.max_event_gap,
            )
            composed = compose_paths(events, reference_query)
            witnesses = tuple(w for w in composed.witnesses if w.endpoint == query.goal)
            if witnesses:
                ranked.append((probability, path, witnesses, composed.rejected))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        if not ranked:
            return {"status": "ABSTAIN_NO_VALID_WITNESS", "candidates": (), "witnesses": ()}
        best = ranked[0]
        second = ranked[1][0] if len(ranked) > 1 else 0.0
        if best[0] < self.min_probability:
            status = "ABSTAIN_LOW_CONFIDENCE"
        elif len(ranked) > 1 and best[0] - second < self.min_margin:
            status = "ABSTAIN_AMBIGUOUS"
        else:
            status = "SELECTED"
        self.query_operations += len(events) + sum(len(p) for p in paths)
        return {
            "status": status,
            "selected_path": best[1] if status == "SELECTED" else None,
            "score": best[0],
            "margin": best[0] - second,
            "candidates": tuple({"path": p, "score": score} for score, p, _, _ in ranked),
            "witnesses": best[2] if status == "SELECTED" else (),
            "reference_rejections": best[3],
        }

    def snapshot(self) -> dict:
        return {
            "architecture": self.architecture,
            "max_path_depth": self.max_path_depth,
            "soe": self.soe.to_dict(),
            "store": None if self.store is None else self.store.snapshot(),
            "readout_weights": self.readout_weights.copy(),
            "readout_bias": self.readout_bias,
            "readout_fitted": self.readout_fitted,
            "observation_count": self.observation_count,
            "last_observed_at": self.last_observed_at,
            "last_capacity_status": self.last_capacity_status,
            "update_operations": self.update_operations,
            "query_operations": self.query_operations,
        }

    def restore(self, state: dict) -> None:
        if state["architecture"] != self.architecture or int(state.get("max_path_depth", self.max_path_depth)) != self.max_path_depth:
            raise ValueError("snapshot architecture/configuration mismatch")
        from rgm.memory import SOEMemory
        self.soe = SOEMemory.from_dict(state["soe"])
        if self.architecture == "B":
            self.store.restore(state["store"])
        elif state["store"] is not None:
            raise ValueError("A snapshot cannot contain a persistent relation store")
        weights = np.asarray(state["readout_weights"], dtype=float)
        if weights.shape != self.readout_weights.shape or not np.all(np.isfinite(weights)):
            raise ValueError("snapshot readout has invalid shape or values")
        self.readout_weights = weights.copy()
        self.readout_bias = float(state["readout_bias"])
        self.readout_fitted = bool(state["readout_fitted"])
        self.observation_count = int(state["observation_count"])
        self.last_observed_at = float(state["last_observed_at"])
        self.last_capacity_status = str(state["last_capacity_status"])
        self.update_operations = int(state["update_operations"])
        self.query_operations = int(state.get("query_operations", 0))

    def resource_snapshot(self) -> dict:
        soe_bytes = int(self.soe.channels.nbytes + self.soe.decay_rates.nbytes
                        + self.soe.injection_matrices.nbytes)
        readout_bytes = int(self.readout_weights.nbytes + 8)
        store_bytes = 0 if self.store is None else self.store.state_bytes
        store_count = 0 if self.store is None else len(self.store.records)
        return {
            "architecture": self.architecture,
            "persistent_numeric_bytes": soe_bytes + readout_bytes,
            "relation_payload_bytes": store_bytes,
            "relation_instance_count": store_count,
            "trainable_parameter_count": int(self.readout_weights.size + 1),
            "update_operation_count": int(self.update_operations),
            "query_operation_count": int(self.query_operations),
            "accounting_note": "Relation payload bytes count UTF-8 field payload and timestamps; Python object/container allocator overhead is not included.",
        }
