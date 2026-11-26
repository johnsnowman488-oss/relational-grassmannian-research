"""H1 hierarchical HLA/HLB adapters and coordinated execution primitives.

This module implements the five H1 workstreams on top of the frozen H0
SOEHierarchyBridge. It deliberately keeps native numerical evolution in the
persistent runtime and architecture policy in Python.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence
import copy
import hashlib
import json
import math

import numpy as np

from rgm.leptograph.m4.composition import (
    Entity, RelationInstance, RelationType, CompositionQuery,
    CompositionWitness, compose_paths,
)
from rgm.leptograph.m4.soe_bridge import SOEHierarchyBridge, make_h0_chain_spec
from rgm.leptograph.m4.evidence import EvidenceStore, NaryEvent


H1_SCHEMA_VERSION = "0.1.0"
LEVELS = ("grounding", "relational_abstraction", "context_control")


def _finite_vector(value, *, name: str) -> np.ndarray:
    vector = np.asarray(value, dtype=np.float64).reshape(-1)
    if vector.size == 0 or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a non-empty finite vector")
    return vector.copy()


def _fingerprint(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _memory_snapshots(bridge: SOEHierarchyBridge) -> list[dict]:
    return [memory.to_dict() for memory in bridge.memories]


def _validate_memory_snapshots(bridge: SOEHierarchyBridge, states: Sequence[Mapping]) -> None:
    if len(states) != 3:
        raise ValueError("composite architecture snapshot must contain three SOE banks")
    for current, candidate in zip(bridge.memories, states):
        restored = type(current).from_dict(dict(candidate))
        if (restored.feature_dim, restored.channel_count) != (current.feature_dim, current.channel_count):
            raise ValueError("SOE checkpoint dimensions differ from the active H0 bridge")
        if not (np.array_equal(restored.decay_rates, current.decay_rates)
                and np.array_equal(restored.injection_matrices, current.injection_matrices)):
            raise ValueError("SOE checkpoint configuration differs from the active H0 bridge")


def _restore_memories(bridge: SOEHierarchyBridge, states: Sequence[Mapping]) -> None:
    _validate_memory_snapshots(bridge, states)
    for memory, candidate in zip(bridge.memories, states):
        memory.channels = type(memory).from_dict(dict(candidate)).channels.copy()


@dataclass(frozen=True)
class AbstractPrediction:
    """A learned upper-level feature prediction, never an exact path witness."""
    level: int
    features: tuple[float, ...]
    readout_fingerprint: str
    kind: str = "ABSTRACT_PREDICTION"


@dataclass(frozen=True)
class ReadoutExample:
    """One labelled calibration example; never constructed from confirmatory data."""
    features: tuple[float, ...]
    targets: tuple[float, ...]
    partition: str = "calibration"

    def __post_init__(self):
        x, y = _finite_vector(self.features, name="features"), _finite_vector(self.targets, name="targets")
        if x.size == 0 or y.size == 0 or self.partition != "calibration":
            raise ValueError("readout fitting accepts non-empty calibration examples only")


class LinearReadout:
    """Ridge readout with explicit dimensions and a stable parameter fingerprint."""
    def __init__(self, input_dim: int, output_dim: int, ridge: float = 1e-6):
        if input_dim < 1 or output_dim < 1 or not math.isfinite(ridge) or ridge < 0:
            raise ValueError("invalid readout dimensions or ridge")
        self.input_dim, self.output_dim, self.ridge = int(input_dim), int(output_dim), float(ridge)
        self.weights = np.zeros((self.input_dim + 1, self.output_dim), dtype=np.float64)
        self.fitted = False

    def fit(self, examples: Sequence[ReadoutExample]) -> dict:
        if not examples:
            raise ValueError("at least one calibration example is required")
        x = np.asarray([e.features for e in examples], dtype=np.float64)
        y = np.asarray([e.targets for e in examples], dtype=np.float64)
        if x.ndim != 2 or y.ndim != 2 or x.shape[1] != self.input_dim or y.shape != (len(examples), self.output_dim):
            raise ValueError("calibration examples do not match frozen readout dimensions")
        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
            raise ValueError("calibration data must be finite")
        design = np.column_stack([x, np.ones(len(x))])
        penalty = np.eye(self.input_dim + 1) * self.ridge
        penalty[-1, -1] = 0.0
        candidate = np.linalg.solve(design.T @ design + penalty, design.T @ y)
        if not np.all(np.isfinite(candidate)):
            raise ValueError("readout fit produced non-finite parameters")
        self.weights = candidate
        self.fitted = True
        residual = design @ candidate - y
        return {"examples": len(examples), "mse": float(np.mean(residual ** 2)),
                "fingerprint": self.fingerprint}

    def predict(self, features: Sequence[float]) -> np.ndarray:
        x = _finite_vector(features, name="readout features")
        if x.size != self.input_dim:
            raise ValueError("readout feature dimension mismatch")
        if not self.fitted:
            raise RuntimeError("readout is not fitted")
        return np.concatenate([x, [1.0]]) @ self.weights

    @property
    def fingerprint(self) -> str:
        return _fingerprint({"input_dim": self.input_dim, "output_dim": self.output_dim,
                             "ridge": self.ridge, "weights": self.weights.tolist(),
                             "fitted": self.fitted})

    def snapshot(self) -> dict:
        return {"input_dim": self.input_dim, "output_dim": self.output_dim,
                "ridge": self.ridge, "weights": self.weights.tolist(),
                "fitted": self.fitted, "fingerprint": self.fingerprint}

    def restore(self, state: Mapping) -> None:
        if (int(state["input_dim"]), int(state["output_dim"])) != (self.input_dim, self.output_dim):
            raise ValueError("readout snapshot dimension mismatch")
        candidate = np.asarray(state["weights"], dtype=np.float64)
        if candidate.shape != self.weights.shape or not np.all(np.isfinite(candidate)):
            raise ValueError("readout snapshot contains invalid weights")
        self.weights = candidate.copy()
        self.fitted = bool(state["fitted"])
        if state.get("fingerprint") != self.fingerprint:
            raise ValueError("readout snapshot fingerprint mismatch")


def create_hla_adapter(native_library, memories, kernels, *, dt: float,
                       runtime_factory: Callable, ridge: float = 1e-6) -> "HLAAdapter":
    """Create one persistent native handle and bind it to HLA.

    runtime_factory is the production ABI factory, such as
    gfe_ctypes.create_persistent_hierarchy_runtime from Aberconics.
    Dependency injection keeps this package independent of a checkout path.
    """
    levels, edges = make_h0_chain_spec(memories, kernels, dt=dt)
    runtime = runtime_factory(native_library, levels, edges)
    try:
        bridge = SOEHierarchyBridge(runtime, memories, dt=dt)
        return HLAAdapter(bridge, feature_dims=[m.feature_dim for m in memories], ridge=ridge)
    except Exception:
        close = getattr(runtime, "close", None)
        if callable(close):
            close()
        raise


def create_hlb_adapter(native_library, memories, kernels, *, dt: float,
                       runtime_factory: Callable, capacity: int = 8192,
                       ridge: float = 1e-6) -> "HLBAdapter":
    """Create one persistent native handle and bind it to HLB."""
    levels, edges = make_h0_chain_spec(memories, kernels, dt=dt)
    runtime = runtime_factory(native_library, levels, edges)
    try:
        return HLBAdapter(SOEHierarchyBridge(runtime, memories, dt=dt), capacity=capacity, ridge=ridge)
    except Exception:
        close = getattr(runtime, "close", None)
        if callable(close):
            close()
        raise


class HLAAdapter:
    """HLA: three-level SOE hierarchy with learned upper readouts, no relation store."""
    architecture = "HLA"

    def __init__(self, bridge: SOEHierarchyBridge, *, feature_dims: Sequence[int],
                 ridge: float = 1e-6):
        if len(feature_dims) != 3 or any(int(d) < 1 for d in feature_dims):
            raise ValueError("HLA requires three positive feature dimensions")
        self.bridge = bridge
        self.feature_dims = tuple(int(d) for d in feature_dims)
        if tuple(m.feature_dim for m in bridge.memories) != self.feature_dims:
            raise ValueError("HLA feature dimensions must match H0 SOE banks")
        # Readouts consume the flattened pre-step SOE trace at the lower
        # level, not the current event vector or a partially updated bank.
        self.readouts = (
            LinearReadout(bridge.layouts[0].native_state_dim, self.feature_dims[1], ridge),
            LinearReadout(bridge.layouts[1].native_state_dim, self.feature_dims[2], ridge),
        )
        self.ticks = 0
        self.abstentions = 0

    def fit_upper_readouts(self, level1: Sequence[ReadoutExample],
                           level2: Sequence[ReadoutExample]) -> dict:
        return {"level1": self.readouts[0].fit(level1),
                "level2": self.readouts[1].fit(level2)}

    def step(self, event_features: Mapping[int, Sequence[float]] | None = None) -> dict:
        supplied = {} if event_features is None else dict(event_features)
        # Every readout observes the same pre-step SOE snapshot. This avoids
        # sequential partial updates and keeps H0's one-tick synchronisation
        # invariant intact. The current event is injected by the bridge below.
        if self.readouts[0].fitted and 1 not in supplied:
            trace0 = self.bridge.memories[0].snapshot().reshape(-1)
            supplied[1] = self.readouts[0].predict(trace0).tolist()
        if self.readouts[1].fitted and 2 not in supplied:
            trace1 = self.bridge.memories[1].snapshot().reshape(-1)
            supplied[2] = self.readouts[1].predict(trace1).tolist()
        result = self.bridge.step(supplied)
        self.ticks += 1
        return {"architecture": self.architecture, "tick": self.ticks, **result}

    def query_readout(self, level: int, lower_level_trace: Sequence[float]) -> np.ndarray:
        if level not in (1, 2):
            raise ValueError("learned HLA readouts exist only at levels 1 and 2")
        try:
            return self.readouts[level - 1].predict(lower_level_trace)
        except RuntimeError:
            self.abstentions += 1
            raise

    def predict_abstract(self, level: int, lower_level_trace: Sequence[float]) -> AbstractPrediction:
        values = self.query_readout(level, lower_level_trace)
        return AbstractPrediction(level, tuple(float(x) for x in values),
                                  self.readouts[level - 1].fingerprint)

    def validate_exact_witness(self, witness: CompositionWitness, *,
                               evidence: Iterable[RelationInstance],
                               relation_path: Sequence[RelationType],
                               context: str | None, query_time: float,
                               observation_cutoff: float) -> bool:
        """Validate exact claims only against caller-supplied current evidence."""
        query = CompositionQuery(witness.entities[0], tuple(relation_path), context,
                                 query_time, observation_cutoff)
        valid = compose_paths(evidence, query).witnesses
        return witness in valid

    def query(self, start: Entity, relation_path: Sequence[RelationType], *,
              evidence: Iterable[RelationInstance], context: str | None,
              query_time: float, observation_cutoff: float,
              max_event_gap: float | None = None) -> tuple[CompositionWitness, ...]:
        """Compose only from the caller's current evidence window; retain nothing."""
        query = CompositionQuery(start, tuple(relation_path), context, query_time,
                                 observation_cutoff, max_event_gap=max_event_gap)
        witnesses = compose_paths(evidence, query).witnesses
        if not witnesses:
            self.abstentions += 1
        return witnesses

    def snapshot(self) -> dict:
        return {"schema_version": H1_SCHEMA_VERSION, "architecture": self.architecture,
                "ticks": self.ticks, "abstentions": self.abstentions,
                "soe_banks": _memory_snapshots(self.bridge),
                "readouts": [r.snapshot() for r in self.readouts]}

    def validate_snapshot(self, state: Mapping) -> None:
        if state.get("schema_version") != H1_SCHEMA_VERSION or state.get("architecture") != self.architecture:
            raise ValueError("HLA snapshot schema or architecture mismatch")
        if len(state.get("readouts", ())) != 2:
            raise ValueError("HLA snapshot must contain both upper readouts")
        _validate_memory_snapshots(self.bridge, state.get("soe_banks", ()))
        for readout, candidate in zip(self.readouts, state["readouts"]):
            probe = LinearReadout(readout.input_dim, readout.output_dim, readout.ridge)
            probe.restore(candidate)

    def restore(self, state: Mapping) -> None:
        self.validate_snapshot(state)
        _restore_memories(self.bridge, state["soe_banks"])
        for readout, candidate in zip(self.readouts, state["readouts"]):
            readout.restore(candidate)
        self.ticks, self.abstentions = int(state["ticks"]), int(state["abstentions"])


class CanonicalRelationStore:
    """One canonical relation record map with level-scoped secondary indexes."""
    def __init__(self, capacity: int = 8192):
        if isinstance(capacity, bool) or capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = int(capacity)
        self._records: dict[str, RelationInstance] = {}
        self._level_index: dict[int, set[str]] = {0: set(), 1: set(), 2: set()}
        self._subject_index: dict[tuple[int, Entity], set[str]] = {}
        self._type_index: dict[tuple[int, str], set[str]] = {}

    def insert(self, level: int, record: RelationInstance) -> str:
        if level not in (0, 1, 2) or not isinstance(record, RelationInstance):
            raise ValueError("relation insertion requires level 0, 1 or 2 and a typed record")
        prior = self._records.get(record.instance_id)
        if prior is not None:
            if prior != record:
                raise ValueError("canonical relation ID collision")
            if record.instance_id not in self._level_index[level]:
                raise ValueError("one canonical relation cannot be silently reclassified across levels")
            return "ALREADY_STORED"
        if len(self._records) >= self.capacity:
            return "ABSTAIN_CAPACITY"
        self._records[record.instance_id] = record
        self._level_index[level].add(record.instance_id)
        self._subject_index.setdefault((level, record.subject), set()).add(record.instance_id)
        self._type_index.setdefault((level, record.relation_type.name), set()).add(record.instance_id)
        return "STORED"

    def records(self, *, cutoff: float, levels: Sequence[int] = (0, 1, 2)) -> tuple[RelationInstance, ...]:
        if not math.isfinite(cutoff) or any(level not in (0, 1, 2) for level in levels):
            raise ValueError("invalid observation cutoff or level selection")
        ids = set().union(*(self._level_index[level] for level in levels)) if levels else set()
        return tuple(self._records[i] for i in sorted(ids)
                     if self._records[i].observed_at <= cutoff)

    def by_subject(self, level: int, subject: Entity, *, cutoff: float) -> tuple[RelationInstance, ...]:
        ids = self._subject_index.get((level, subject), set())
        return tuple(self._records[i] for i in sorted(ids)
                     if self._records[i].observed_at <= cutoff)

    def snapshot(self) -> dict:
        return {"capacity": self.capacity,
                "records": [{"level": level, "record": _record_to_dict(self._records[i])}
                            for level in range(3) for i in sorted(self._level_index[level])]}

    def restore(self, state: Mapping) -> None:
        capacity, records = int(state["capacity"]), tuple(state["records"])
        if capacity < 1 or len(records) > capacity:
            raise ValueError("invalid canonical store snapshot capacity")
        candidate = CanonicalRelationStore(capacity)
        for item in records:
            status = candidate.insert(int(item["level"]), _record_from_dict(item["record"]))
            if status != "STORED":
                raise ValueError("duplicate relation record in snapshot")
        self.capacity = candidate.capacity
        self._records, self._level_index = candidate._records, candidate._level_index
        self._subject_index, self._type_index = candidate._subject_index, candidate._type_index

    @property
    def count(self) -> int:
        return len(self._records)


def _record_to_dict(record: RelationInstance) -> dict:
    return {"instance_id": record.instance_id,
            "relation_type": {"name": record.relation_type.name, "domain": record.relation_type.domain,
                              "codomain": record.relation_type.codomain},
            "subject": {"entity_id": record.subject.entity_id, "entity_type": record.subject.entity_type},
            "object": {"entity_id": record.object.entity_id, "entity_type": record.object.entity_type},
            "event_time": record.event_time, "observed_at": record.observed_at,
            "context": record.context, "valid_until": record.valid_until, "provenance": record.provenance}


def _record_from_dict(state: Mapping) -> RelationInstance:
    return RelationInstance(
        str(state["instance_id"]),
        RelationType(**state["relation_type"]),
        Entity(**state["subject"]), Entity(**state["object"]),
        float(state["event_time"]), float(state["observed_at"]),
        state.get("context"), state.get("valid_until"), state.get("provenance"),
    )


class HLBAdapter:
    """HLB: shared SOE hierarchy plus a single canonical typed relation store."""
    architecture = "HLB"

    def __init__(self, bridge: SOEHierarchyBridge, *, capacity: int = 8192,
                 ridge: float = 1e-6):
        self.bridge = bridge
        self.store = CanonicalRelationStore(capacity)
        # Source-event journal is append-only and intentionally outside model rollback.
        self.evidence = EvidenceStore(capacity=capacity)
        self.feature_dims = tuple(memory.feature_dim for memory in bridge.memories)
        self.readouts = (
            LinearReadout(bridge.layouts[0].native_state_dim, self.feature_dims[1], ridge),
            LinearReadout(bridge.layouts[1].native_state_dim, self.feature_dims[2], ridge),
        )
        self.ticks = 0
        self.abstentions = 0

    def fit_upper_readouts(self, level1: Sequence[ReadoutExample],
                           level2: Sequence[ReadoutExample]) -> dict:
        return {"level1": self.readouts[0].fit(level1),
                "level2": self.readouts[1].fit(level2)}

    def query_readout(self, level: int, lower_level_trace: Sequence[float]) -> np.ndarray:
        if level not in (1, 2):
            raise ValueError("learned upper readouts exist only at levels 1 and 2")
        try:
            return self.readouts[level - 1].predict(lower_level_trace)
        except RuntimeError:
            self.abstentions += 1
            raise

    def predict_abstract(self, level: int, lower_level_trace: Sequence[float]) -> AbstractPrediction:
        values = self.query_readout(level, lower_level_trace)
        return AbstractPrediction(level, tuple(float(x) for x in values),
                                  self.readouts[level - 1].fingerprint)

    def observe(self, level: int, record: RelationInstance) -> str:
        return self.store.insert(level, record)

    def observe_event(self, event: NaryEvent) -> str:
        """Append source-grounded n-ary evidence outside candidate rollback state."""
        return self.evidence.append(event)

    def recover_evidence(self, evidence_id: str, *, observation_cutoff: float):
        return self.evidence.recover(evidence_id, observation_cutoff=observation_cutoff)

    def verify_event_provenance(self, event_id: str, payload_loader: Callable[[str], bytes]) -> bool:
        return self.evidence.verify_provenance(event_id, payload_loader)

    def evidence_checkpoint(self) -> dict:
        """Serialize the durable source journal separately from model checkpoints."""
        return self.evidence.snapshot()

    def restore_evidence_checkpoint(self, state: Mapping) -> None:
        """Merge a journal during storage recovery without deleting newer local evidence."""
        self.evidence.merge_snapshot(state)

    def query(self, start: Entity, relation_path: Sequence[RelationType], *,
              context: str | None, query_time: float, observation_cutoff: float,
              max_event_gap: float | None = None) -> tuple[CompositionWitness, ...]:
        records = self.store.records(cutoff=observation_cutoff)
        query = CompositionQuery(start, tuple(relation_path), context, query_time,
                                 observation_cutoff, max_event_gap=max_event_gap)
        witnesses = compose_paths(records, query).witnesses
        if not witnesses:
            self.abstentions += 1
        return witnesses

    def step(self, event_features: Mapping[int, Sequence[float]] | None = None) -> dict:
        supplied = {} if event_features is None else dict(event_features)
        if self.readouts[0].fitted and 1 not in supplied:
            trace0 = self.bridge.memories[0].snapshot().reshape(-1)
            supplied[1] = self.readouts[0].predict(trace0).tolist()
        if self.readouts[1].fitted and 2 not in supplied:
            trace1 = self.bridge.memories[1].snapshot().reshape(-1)
            supplied[2] = self.readouts[1].predict(trace1).tolist()
        result = self.bridge.step(supplied)
        self.ticks += 1
        return {"architecture": self.architecture, "tick": self.ticks, **result}

    def snapshot(self) -> dict:
        return {"schema_version": H1_SCHEMA_VERSION, "architecture": self.architecture,
                "ticks": self.ticks, "abstentions": self.abstentions,
                "store": self.store.snapshot(),
                "evidence_watermark": list(self.evidence.event_ids),
                "soe_banks": _memory_snapshots(self.bridge),
                "readouts": [readout.snapshot() for readout in self.readouts]}

    def validate_snapshot(self, state: Mapping) -> None:
        if state.get("schema_version") != H1_SCHEMA_VERSION or state.get("architecture") != self.architecture:
            raise ValueError("HLB snapshot schema or architecture mismatch")
        probe = CanonicalRelationStore()
        probe.restore(state["store"])
        # The append-only source journal is not rolled back with candidate state,
        # but every checkpoint watermark must still resolve in the active journal.
        watermark = tuple(state.get("evidence_watermark", ()))
        if len(watermark) != len(set(watermark)) or any(
            event_id not in self.evidence.event_ids for event_id in watermark
        ):
            raise ValueError("HLB checkpoint references unavailable source evidence")
        _validate_memory_snapshots(self.bridge, state.get("soe_banks", ()))
        if len(state.get("readouts", ())) != 2:
            raise ValueError("HLB snapshot must contain both upper readouts")
        for readout, candidate in zip(self.readouts, state["readouts"]):
            probe_readout = LinearReadout(readout.input_dim, readout.output_dim, readout.ridge)
            probe_readout.restore(candidate)

    def restore(self, state: Mapping) -> None:
        self.validate_snapshot(state)
        self.store.restore(state["store"])
        _restore_memories(self.bridge, state["soe_banks"])
        for readout, candidate in zip(self.readouts, state["readouts"]):
            readout.restore(candidate)
        self.ticks, self.abstentions = int(state["ticks"]), int(state["abstentions"])


class HierarchicalRuntimeDirector:
    """One orchestration point: validate a tick, then perform one H0 bridge step."""
    def __init__(self, adapter: HLAAdapter | HLBAdapter):
        self.adapter = adapter
        self.event_tick = 0
        self.event_log: list[dict] = []

    def exchange(self, *, event_time: float, observed_at: float,
                 event_features: Mapping[int, Sequence[float]] | None = None,
                 relation_records: Sequence[tuple[int, RelationInstance]] = ()) -> dict:
        if not math.isfinite(event_time) or not math.isfinite(observed_at) or event_time < 0 or observed_at < event_time:
            raise ValueError("event_time and observed_at must be finite and observation cannot precede event")
        if observed_at < (self.event_log[-1]["observed_at"] if self.event_log else 0.0):
            raise ValueError("observation time must be nondecreasing; late events retain their original event_time")
        if isinstance(self.adapter, HLAAdapter) and relation_records:
            raise ValueError("HLA cannot retain relation instances")
        # Validate and insert records before the numerical cycle. If the native
        # step fails, restore the adapter snapshot so the whole exchange rolls back.
        before = self.adapter.snapshot()
        statuses = []
        try:
            if isinstance(self.adapter, HLBAdapter):
                for level, record in relation_records:
                    statuses.append(self.adapter.observe(level, record))
                    if statuses[-1] == "ABSTAIN_CAPACITY":
                        raise RuntimeError("HLB relation capacity exhausted; exchange abstained")
            result = self.adapter.step(event_features)
        except Exception:
            self.adapter.restore(before)
            raise
        self.event_tick += 1
        self.event_log.append({"event_time": float(event_time), "observed_at": float(observed_at),
                               "tick": self.event_tick})
        return {"tick": self.event_tick, "relation_status": tuple(statuses), "result": result}

    def close(self) -> None:
        """Release the single persistent native handle owned by this director."""
        close = getattr(self.adapter.bridge.runtime, "close", None)
        if callable(close):
            close()

    def snapshot(self) -> dict:
        return {"schema_version": H1_SCHEMA_VERSION, "event_tick": self.event_tick,
                "event_log": copy.deepcopy(self.event_log),
                "adapter": self.adapter.snapshot()}

    def validate_snapshot(self, state: Mapping) -> None:
        if state.get("schema_version") != H1_SCHEMA_VERSION:
            raise ValueError("director snapshot schema mismatch")
        self.adapter.validate_snapshot(state["adapter"])
        log = state.get("event_log", ())
        if len(log) != int(state["event_tick"]):
            raise ValueError("director event tick/log mismatch")

    def restore(self, state: Mapping) -> None:
        self.validate_snapshot(state)
        self.adapter.restore(state["adapter"])
        self.event_tick = int(state["event_tick"])
        self.event_log = copy.deepcopy(list(state["event_log"]))


class CompositeLifecycle:
    """Composite checkpoint and rollback coordinator for adapter + native runtime."""
    def __init__(self, director: HierarchicalRuntimeDirector):
        self.director = director
        self._trusted: dict | None = None
        self._rollback_point: dict | None = None
        self.version = 0

    def _capture_checkpoint(self) -> dict:
        runtime = self.director.adapter.bridge.runtime
        if not hasattr(runtime, "checkpoint"):
            raise TypeError("persistent native runtime must expose checkpoint()")
        state = {"schema_version": H1_SCHEMA_VERSION,
                 "director": self.director.snapshot(),
                 "native": runtime.checkpoint(),
                 "version": self.version}
        state["fingerprint"] = _fingerprint({
            "director": state["director"], "native": state["native"], "version": state["version"]
        })
        return state

    def checkpoint(self) -> dict:
        state = self._capture_checkpoint()
        self._trusted = copy.deepcopy(state)
        self._rollback_point = None
        return copy.deepcopy(state)

    def restore(self, state: Mapping) -> None:
        if state.get("schema_version") != H1_SCHEMA_VERSION:
            raise ValueError("composite checkpoint schema mismatch")
        expected = _fingerprint({"director": state["director"], "native": state["native"],
                                 "version": int(state["version"])})
        if state.get("fingerprint") != expected:
            raise ValueError("composite checkpoint fingerprint mismatch")
        self.director.validate_snapshot(state["director"])
        runtime = self.director.adapter.bridge.runtime
        if not hasattr(runtime, "restore"):
            raise TypeError("persistent native runtime must expose restore(checkpoint)")
        # Native restore is required to be internally compute-then-commit (M4 ABI).
        runtime.restore(state["native"])
        self.director.restore(state["director"])
        self.version = int(state["version"])

    def rollback(self) -> None:
        target = self._rollback_point if self._rollback_point is not None else self._trusted
        if target is None:
            raise RuntimeError("no trusted composite checkpoint exists")
        self.restore(target)
        self._trusted = copy.deepcopy(target)
        self._rollback_point = None

    def promote(self) -> int:
        if self._trusted is None:
            raise RuntimeError("an initial trusted checkpoint is required before promotion")
        previous_trusted = copy.deepcopy(self._trusted)
        previous_version = self.version
        self.version += 1
        try:
            promoted = self._capture_checkpoint()
        except Exception:
            self.version = previous_version
            raise
        self._rollback_point = previous_trusted
        self._trusted = copy.deepcopy(promoted)
        return self.version


@dataclass(frozen=True)
class EvaluationPartition:
    name: str
    tasks: tuple[object, ...]

    def __post_init__(self):
        if self.name not in {"fit", "validation", "confirmatory"}:
            raise ValueError("partition must be fit, validation or confirmatory")


class HierarchicalEvaluationRunner:
    """Paired runner; fitting and confirmatory data are structurally separated."""
    def __init__(self, task_fn: Callable, *, task_id: str, seed: int):
        if not task_id:
            raise ValueError("task_id must be non-empty")
        self.task_fn, self.task_id, self.seed = task_fn, task_id, int(seed)

    def run(self, adapter, partition: EvaluationPartition) -> dict:
        if partition.name == "fit":
            raise ValueError("fit partition is not an evaluation partition")
        rows = []
        for index, task in enumerate(partition.tasks):
            result = self.task_fn(adapter, task)
            if not isinstance(result, Mapping):
                raise TypeError("task function must return a metric mapping")
            rows.append(dict(result, task_index=index))
        metric_names = sorted(set.intersection(*(set(r) - {"task_index"} for r in rows))) if rows else []
        metrics = {}
        for name in metric_names:
            values = np.asarray([r[name] for r in rows], dtype=np.float64)
            if not np.all(np.isfinite(values)):
                raise ValueError(f"metric {name} contains non-finite values")
            metrics[name] = {"mean": float(np.mean(values)), "count": int(values.size)}
        return {"schema_version": H1_SCHEMA_VERSION, "task_id": self.task_id,
                "seed": self.seed, "architecture": adapter.architecture,
                "partition": partition.name, "task_fingerprint": _fingerprint(list(partition.tasks)),
                "task_count": len(rows),
                "metrics": metrics, "rows": rows}

    @staticmethod
    def paired_summary(first: Mapping, second: Mapping) -> dict:
        if (first["task_id"], first["seed"], first["partition"], first["task_fingerprint"]) != (
            second["task_id"], second["seed"], second["partition"], second["task_fingerprint"]
        ):
            raise ValueError("paired comparison requires identical task, seed and partition")
        if [r["task_index"] for r in first["rows"]] != [r["task_index"] for r in second["rows"]]:
            raise ValueError("paired comparison requires identical task order")
        common = set(first["metrics"]) & set(second["metrics"])
        return {"architectures": (first["architecture"], second["architecture"]),
                "partition": first["partition"],
                "differences": {name: first["metrics"][name]["mean"] -
                                second["metrics"][name]["mean"] for name in sorted(common)}}
