"""E02: event-derived relational graph, dense memory and hybrid evaluation.

Model functions accept ModelInput only. EvaluationTruth and corruption audits are
kept in the experiment runner/scorer and are never passed to prediction functions.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from ..memory import SOEMemory
from ..relations import RelationEvent, RelationSchema, RelationalGraph
from .e01_b import (
    FEATURE_DIM, GAP_PROFILES, _stable_geq, _stable_score, _support_tensors,
    _threshold, codebooks, make_case,
)

SCHEMA_VERSION = "e02-observed-input-v1"
EXPERIMENT_VERSION = "e02-v0.1"
WORLD_SEEDS = (501, 502, 503)
CODEBOOK_SEEDS = (9137, 27183, 65537)
MEMORY_ARMS = ("slow_only", "full_history")
CONDITIONS: dict[str, dict[str, Any]] = {
    "baseline_e4": dict(entities=4, facts=8, distractors=0, depth=2, gap="medium"),
    "repeat_e4": dict(entities=4, facts=8, distractors=32, depth=2, gap="medium"),
    "candidate_e16": dict(entities=16, facts=16, distractors=16, depth=2, gap="medium"),
    "factload_e16": dict(entities=16, facts=64, distractors=16, depth=2, gap="medium"),
    "depth3_e16": dict(entities=16, facts=32, distractors=16, depth=3, gap="medium"),
    "longgap_e16": dict(entities=16, facts=16, distractors=16, depth=2, gap="long"),
}
CORRUPTION_PROFILES = {
    "clean": (0.0, 0.0),
    "missing_10": (0.10, 0.0),
    "spurious_10": (0.0, 0.10),
    "mixed_10": (0.10, 0.10),
}
FORBIDDEN_MODEL_KEYS = {
    "label", "labels", "facts", "latent_facts", "planted_path",
    "ground_truth", "truth", "corruption_audit", "corruption_mask",
}


@dataclass(frozen=True)
class ObservedEvent:
    """One model-visible event; no truth, provenance or corruption marker."""
    index: int
    relation: int
    subject: int
    object: int
    dt: float

    def __post_init__(self) -> None:
        if self.index < 0 or self.relation not in (0, 1):
            raise ValueError("invalid event index or relation")
        if self.subject < 0 or self.object < 0 or self.subject == self.object:
            raise ValueError("invalid event endpoints")
        if not np.isfinite(self.dt) or self.dt < 0:
            raise ValueError("event dt must be finite and non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": int(self.index), "relation": int(self.relation),
            "subject": int(self.subject), "object": int(self.object), "dt": float(self.dt),
        }


@dataclass(frozen=True)
class ObservedQuery:
    subject: int
    object: int
    depth: int
    relation_pattern: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.subject < 0 or self.object < 0 or self.subject == self.object:
            raise ValueError("query endpoints must be distinct non-negative ids")
        if self.depth not in (1, 2, 3) or len(self.relation_pattern) != self.depth:
            raise ValueError("query depth and relation pattern are inconsistent")
        if any(x not in (0, 1) for x in self.relation_pattern):
            raise ValueError("unknown query relation")

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": int(self.subject), "object": int(self.object),
            "depth": int(self.depth), "relation_pattern": list(self.relation_pattern),
        }


@dataclass(frozen=True)
class ModelInput:
    """Allowlisted model input. It intentionally has no evaluator-truth field."""
    case_id: str
    entity_count: int
    events: tuple[ObservedEvent, ...]
    query: ObservedQuery

    def __post_init__(self) -> None:
        if self.entity_count < 4:
            raise ValueError("entity_count must be at least four")
        if self.query.subject >= self.entity_count or self.query.object >= self.entity_count:
            raise ValueError("query endpoint outside entity range")
        for event in self.events:
            if event.subject >= self.entity_count or event.object >= self.entity_count:
                raise ValueError("event endpoint outside entity range")
        if tuple(event.index for event in self.events) != tuple(range(len(self.events))):
            raise ValueError("event indices must be contiguous and ordered")

    def to_payload(self) -> dict[str, Any]:
        """Canonical model-facing payload; no labels, facts, paths or audit fields."""
        return {
            "schema_version": SCHEMA_VERSION,
            "case_id": str(self.case_id),
            "entity_count": int(self.entity_count),
            "observed_events": [event.to_dict() for event in self.events],
            "query": self.query.to_dict(),
        }

    @property
    def input_sha256(self) -> str:
        raw = json.dumps(self.to_payload(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class EvaluationTruth:
    """Evaluator-only outcome; never passed to graph or memory prediction."""
    label: int
    facts: frozenset[tuple[int, int, int]]
    planted_path: tuple[int, ...] | None


@dataclass
class DerivedGraph:
    """Event-derived append-only graph plus a unique-edge traversal index."""
    event_store: RelationalGraph
    edge_set: frozenset[tuple[int, int, int]]
    edge_records: tuple[dict[str, Any], ...]
    adjacency: dict[tuple[int, int], tuple[int, ...]]
    storage_bytes: int


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _to_pair(case: Any, depth: int) -> tuple[ModelInput, EvaluationTruth]:
    events = tuple(
        ObservedEvent(i, int(event.relation), int(event.subject), int(event.object), float(event.dt))
        for i, event in enumerate(case.events)
    )
    entity_count = max(4, max(
        max((e.subject for e in events), default=0),
        max((e.object for e in events), default=0),
        int(case.query_subject), int(case.query_object),
    ) + 1)
    query = ObservedQuery(
        int(case.query_subject), int(case.query_object), int(depth),
        tuple(step % 2 for step in range(depth)),
    )
    # Generator seeds encode the class label in their parity. Never expose
    # that seed: derive an opaque identifier only from model-visible content.
    opaque_id_payload = {
        "entity_count": entity_count,
        "observed_events": [event.to_dict() for event in events],
        "query": query.to_dict(),
    }
    opaque_case_id = hashlib.sha256(_canonical_bytes(opaque_id_payload)).hexdigest()[:24]
    model_input = ModelInput(
        case_id=opaque_case_id, entity_count=entity_count, events=events, query=query,
    )
    truth = EvaluationTruth(
        int(case.label), frozenset(tuple(map(int, fact)) for fact in case.facts),
        None if case.planted_path is None else tuple(map(int, case.planted_path)),
    )
    return model_input, truth


def _to_pair_with_entities(case: Any, entities: int, depth: int) -> tuple[ModelInput, EvaluationTruth]:
    model_input, truth = _to_pair(case, depth)
    model_input = ModelInput(
        case_id=model_input.case_id, entity_count=int(entities),
        events=model_input.events, query=model_input.query,
    )
    return model_input, truth


def build_event_graph(model_input: ModelInput) -> DerivedGraph:
    """Build a graph using observed event records only."""
    store = RelationalGraph(RelationSchema())
    aggregates: dict[tuple[int, int, int], list[float]] = {}
    elapsed = 0.0
    for event in model_input.events:
        elapsed += float(event.dt)
        key = (event.relation, event.subject, event.object)
        aggregates.setdefault(key, []).append(elapsed)
        store.add(
            str(event.subject), f"relation_{event.relation}", str(event.object),
            timestamp=elapsed,
        )
    records = tuple(
        {
            "relation": int(key[0]), "subject": int(key[1]), "object": int(key[2]),
            "occurrence_count": int(len(times)), "observed_times": [float(t) for t in times],
        }
        for key, times in sorted(aggregates.items())
    )
    edge_set = frozenset(aggregates)
    outgoing: dict[tuple[int, int], set[int]] = {}
    for relation, subject, obj in edge_set:
        outgoing.setdefault((relation, subject), set()).add(obj)
    adjacency = {key: tuple(sorted(values)) for key, values in outgoing.items()}
    payload = {
        "schema_version": "e02-event-graph-v1",
        "entity_count": int(model_input.entity_count),
        "event_count": len(model_input.events),
        "unique_edge_count": len(edge_set),
        "edges": list(records),
    }
    return DerivedGraph(store, edge_set, records, adjacency, len(_canonical_bytes(payload)))


def graph_query(model_input: ModelInput, graph: DerivedGraph) -> tuple[bool, tuple[int, ...] | None, int]:
    """Exact typed path-existence query over the observed graph; returns operation count."""
    target = model_input.query.object
    pattern = model_input.query.relation_pattern
    examined = 0

    def walk(node: int, step: int, path: tuple[int, ...]) -> tuple[int, ...] | None:
        nonlocal examined
        if step == len(pattern):
            return path if node == target else None
        for nxt in graph.adjacency.get((pattern[step], node), ()):
            examined += 1
            found = walk(nxt, step + 1, path + (nxt,))
            if found is not None:
                return found
        return None

    witness = walk(model_input.query.subject, 0, (model_input.query.subject,))
    return witness is not None, witness, examined


def _memory_support(
    model_input: ModelInput,
    arm: str,
    books: tuple[np.ndarray, np.ndarray],
) -> tuple[tuple[np.ndarray, np.ndarray], int]:
    vectors = [
        books[event.relation][event.subject * model_input.entity_count + event.object].copy()
        for event in model_input.events
    ]
    if arm == "slow_only":
        memory = SOEMemory(feature_dim=FEATURE_DIM, decay_rates=(0.01,))
        for event, vector in zip(model_input.events, vectors):
            memory.update(vector, dt=event.dt)
        state = memory.snapshot()
        state_bytes = int(state.nbytes + memory.decay_rates.nbytes)
    elif arm == "full_history":
        state = np.sum(vectors, axis=0, dtype=np.float64)[None, :] if vectors else np.zeros((1, FEATURE_DIM))
        state_bytes = int(state.nbytes)
    else:
        raise ValueError(f"unknown memory arm: {arm}")
    return _support_tensors(state, books, model_input.entity_count), state_bytes


def _composed_score(
    model_input: ModelInput,
    supports: tuple[np.ndarray, np.ndarray],
    graph: DerivedGraph | None = None,
) -> tuple[float, int]:
    """Max-product path score; hybrid mode lets memory support unobserved graph edges."""
    query = model_input.query
    best = 0.0
    candidates = 0
    for mids in itertools.product(range(model_input.entity_count), repeat=query.depth - 1):
        nodes = (query.subject, *mids, query.object)
        edge_scores: list[float] = []
        for step, relation in enumerate(query.relation_pattern):
            left, right = int(nodes[step]), int(nodes[step + 1])
            if graph is not None and (relation, left, right) in graph.edge_set:
                edge_scores.append(1.0)
            else:
                edge_scores.append(_stable_score(float(np.max(supports[relation][:, left, right]))))
        score = _stable_score(float(np.prod(edge_scores)))
        if score > best:
            best = score
        candidates += 1
    return best, candidates * query.depth


def _truth_path_exists(truth: EvaluationTruth, query: ObservedQuery) -> bool:
    outgoing: dict[tuple[int, int], set[int]] = {}
    for relation, left, right in truth.facts:
        outgoing.setdefault((relation, left), set()).add(right)

    def walk(node: int, step: int) -> bool:
        if step == query.depth:
            return node == query.object
        return any(
            walk(nxt, step + 1)
            for nxt in outgoing.get((query.relation_pattern[step], node), ())
        )
    return walk(query.subject, 0)


def _metric_summary(labels: list[int], predictions: list[int]) -> dict[str, Any]:
    y = np.asarray(labels, dtype=np.int64)
    p = np.asarray(predictions, dtype=np.int64)
    tp = int(np.sum((y == 1) & (p == 1)))
    fp = int(np.sum((y == 0) & (p == 1)))
    fn = int(np.sum((y == 1) & (p == 0)))
    tn = int(np.sum((y == 0) & (p == 0)))
    tpr = tp / max(1, tp + fn)
    tnr = tn / max(1, tn + fp)
    precision = tp / max(1, tp + fp)
    recall = tpr
    return {
        "accuracy": float((tp + tn) / max(1, len(y))),
        "balanced_accuracy": float((tpr + tnr) / 2.0),
        "precision": float(precision), "recall": float(recall),
        "false_positive_rate": float(1.0 - tnr),
        "false_negative_rate": float(1.0 - tpr),
        "positive_count": int(np.sum(y == 1)), "negative_count": int(np.sum(y == 0)),
    }


def _make_split(
    condition: str, world_seed: int, split: str, n: int,
) -> tuple[list[ModelInput], list[EvaluationTruth]]:
    params = CONDITIONS[condition]
    entities, facts = int(params["entities"]), int(params["facts"])
    distractors, depth, gap = int(params["distractors"]), int(params["depth"]), str(params["gap"])
    start = (7_000_000 if split == "validation" else 8_000_000) + world_seed * 10_000
    inputs: list[ModelInput] = []
    truths: list[EvaluationTruth] = []
    for i in range(n):
        case = make_case(start + i, entities, facts, distractors, depth, gap)
        model_input, truth = _to_pair_with_entities(case, entities, depth)
        inputs.append(model_input)
        truths.append(truth)
    return inputs, truths


def _calibration_scores(
    inputs: list[ModelInput],
    books: tuple[np.ndarray, np.ndarray],
    arm: str,
    hybrid: bool,
) -> list[float]:
    scores: list[float] = []
    for model_input in inputs:
        graph = build_event_graph(model_input) if hybrid else None
        supports, _ = _memory_support(model_input, arm, books)
        score, _ = _composed_score(model_input, supports, graph)
        scores.append(score)
    return scores


def _mean(values: Iterable[float]) -> float:
    items = list(values)
    return float(np.mean(items)) if items else 0.0


def _cost_summary(
    event_bytes: list[int], state_bytes: list[int], query_ops: list[int],
    event_counts: list[int], unique_edges: list[int],
) -> dict[str, Any]:
    return {
        "mean_model_state_bytes": _mean(state_bytes),
        "mean_common_input_bytes": _mean(event_bytes),
        "mean_query_edge_evaluations": _mean(query_ops),
        "mean_observed_event_count": _mean(event_counts),
        "mean_unique_observed_edges": _mean(unique_edges),
        "timing_policy": "Operation and serialized-byte counts are primary; wall-clock timing is not used for cross-run claims.",
    }


def run_b(condition: str, world_seed: int, codebook_seed: int, n: int = 160) -> dict[str, Any]:
    """E02-B: clean paired graph-vs-memory comparison on E01-C conditions."""
    if condition not in CONDITIONS or world_seed not in WORLD_SEEDS or codebook_seed not in CODEBOOK_SEEDS:
        raise ValueError("condition, world seed or codebook seed is outside the frozen E02 design")
    if n < 20:
        raise ValueError("n must be at least 20")
    entities = int(CONDITIONS[condition]["entities"])
    books = codebooks(entities, codebook_seed)
    val_inputs, val_truths = _make_split(condition, world_seed, "validation", n)
    test_inputs, test_truths = _make_split(condition, world_seed, "test", n)
    labels_val = [x.label for x in val_truths]
    labels_test = [x.label for x in test_truths]
    thresholds = {
        arm: _threshold(_calibration_scores(val_inputs, books, arm, False), labels_val)
        for arm in MEMORY_ARMS
    }
    graph_pred: list[int] = []
    memory_pred: dict[str, list[int]] = {arm: [] for arm in MEMORY_ARMS}
    graph_ops: list[int] = []
    graph_bytes: list[int] = []
    graph_event_counts: list[int] = []
    graph_unique_counts: list[int] = []
    input_bytes: list[int] = []
    memory_state_bytes: dict[str, list[int]] = {arm: [] for arm in MEMORY_ARMS}
    memory_ops: dict[str, list[int]] = {arm: [] for arm in MEMORY_ARMS}
    per_sequence: list[dict[str, Any]] = []
    graph_path_true: list[int] = []
    for model_input, truth in zip(test_inputs, test_truths):
        graph = build_event_graph(model_input)
        exists, witness, ops = graph_query(model_input, graph)
        graph_pred.append(int(exists))
        graph_ops.append(ops)
        graph_bytes.append(graph.storage_bytes)
        graph_event_counts.append(len(model_input.events))
        graph_unique_counts.append(len(graph.edge_set))
        input_bytes.append(len(_canonical_bytes(model_input.to_payload())))
        if witness is not None:
            edges = tuple((model_input.query.relation_pattern[i], witness[i], witness[i + 1])
                          for i in range(model_input.query.depth))
            graph_path_true.append(int(all(edge in truth.facts for edge in edges)))
        for arm in MEMORY_ARMS:
            supports, state_nbytes = _memory_support(model_input, arm, books)
            score, path_ops = _composed_score(model_input, supports)
            memory_pred[arm].append(int(_stable_geq(score, thresholds[arm])))
            memory_state_bytes[arm].append(state_nbytes)
            memory_ops[arm].append(path_ops)
        per_sequence.append({
            "case_id": str(model_input.case_id), "input_sha256": model_input.input_sha256,
            "label": int(truth.label), "event_count": len(model_input.events),
            "unique_observed_edges": len(graph.edge_set),
            "graph_prediction": int(exists), "graph_witness": list(witness) if witness else None,
            "graph_query_edge_examinations": int(ops),
            "memory_predictions": {arm: int(memory_pred[arm][-1]) for arm in MEMORY_ARMS},
        })
    architectures: dict[str, Any] = {
        "graph": {
            "metrics": _metric_summary(labels_test, graph_pred),
            "cost": _cost_summary(input_bytes, graph_bytes, graph_ops, graph_event_counts, graph_unique_counts),
            "path_witness_truth_rate": _mean(graph_path_true),
        }
    }
    for arm in MEMORY_ARMS:
        architectures[f"memory_{arm}"] = {
            "metrics": _metric_summary(labels_test, memory_pred[arm]),
            "cost": _cost_summary(
                input_bytes, memory_state_bytes[arm], memory_ops[arm],
                graph_event_counts, graph_unique_counts,
            ),
            "validation_threshold": float(thresholds[arm]),
        }
    return {
        "experiment": EXPERIMENT_VERSION, "stage": "E02-B",
        "condition": condition, "world_seed": world_seed, "codebook_seed": codebook_seed,
        "sample_counts": {"validation": n, "held_out_test": n},
        "architectures": architectures, "per_sequence": per_sequence,
        "contract": {
            "model_input_schema": SCHEMA_VERSION,
            "model_prediction_inputs": ["entity_count", "observed_events", "query"],
            "evaluator_truth_fields_excluded": sorted(FORBIDDEN_MODEL_KEYS),
            "thresholds_fit_on_validation_only": True,
        },
        "interpretation_guard": (
            "Synthetic paired comparison only. The event-derived graph stores observed facts explicitly; "
            "it is not information-capacity matched to the 16-scalar dense memory. Storage and query work "
            "are reported separately."
        ),
    }


def _corrupt_input(
    model_input: ModelInput,
    truth: EvaluationTruth,
    condition: str,
    profile: str,
    salt: int = 0,
) -> tuple[ModelInput, dict[str, Any]]:
    """Apply evaluator-controlled corruption, returning model input and a separate audit."""
    if profile not in CORRUPTION_PROFILES:
        raise ValueError(f"unknown corruption profile: {profile}")
    missing_rate, spurious_rate = CORRUPTION_PROFILES[profile]
    rng = np.random.default_rng(int(model_input.case_id[:16], 16) + 930_017 + int(salt))
    facts = sorted(truth.facts)
    drop_count = min(len(facts), int(round(missing_rate * len(facts))))
    picked = rng.choice(len(facts), size=drop_count, replace=False) if drop_count else []
    dropped = {facts[int(i)] for i in picked}
    kept = [
        event for event in model_input.events
        if (event.relation, event.subject, event.object) not in dropped
    ]
    add_count = min(
        max(0, 2 * model_input.entity_count * (model_input.entity_count - 1) - len(facts)),
        int(round(spurious_rate * len(facts))),
    )
    universe = [
        (relation, left, right)
        for relation in (0, 1)
        for left in range(model_input.entity_count)
        for right in range(model_input.entity_count)
        if left != right and (relation, left, right) not in truth.facts
    ]
    added: list[tuple[int, int, int]] = []
    if add_count and universe:
        picked = rng.choice(len(universe), size=min(add_count, len(universe)), replace=False)
        added = [universe[int(i)] for i in picked]
    gap_name = str(CONDITIONS[condition]["gap"])
    gap_choices = GAP_PROFILES[gap_name]
    mutable = list(kept)
    for relation, subject, obj in added:
        position = int(rng.integers(0, len(mutable) + 1))
        dt = float(rng.choice(gap_choices))
        mutable.insert(position, ObservedEvent(0, relation, subject, obj, dt))
    events = tuple(
        ObservedEvent(i, item.relation, item.subject, item.object, item.dt)
        for i, item in enumerate(mutable)
    )
    changed = ModelInput(
        case_id=model_input.case_id, entity_count=model_input.entity_count,
        events=events, query=model_input.query,
    )
    audit = {
        "profile": profile, "missing_rate": missing_rate, "spurious_rate": spurious_rate,
        "removed_unique_edge_count": len(dropped),
        "removed_event_count": len(model_input.events) - len(kept),
        "added_spurious_edge_count": len(added),
        "removed_edges": [list(x) for x in sorted(dropped)],
        "added_edges": [list(x) for x in sorted(added)],
    }
    return changed, audit


def run_c(condition: str, world_seed: int, codebook_seed: int, n: int = 160) -> dict[str, Any]:
    """E02-C: graph-plus-temporal-memory under paired controlled event corruption."""
    if condition not in CONDITIONS or world_seed not in WORLD_SEEDS or codebook_seed not in CODEBOOK_SEEDS:
        raise ValueError("condition, world seed or codebook seed is outside the frozen E02 design")
    if n < 20:
        raise ValueError("n must be at least 20")
    entities = int(CONDITIONS[condition]["entities"])
    books = codebooks(entities, codebook_seed)
    profiles_out: dict[str, Any] = {}
    for profile in CORRUPTION_PROFILES:
        base_val_inputs, val_truths = _make_split(condition, world_seed, "validation", n)
        base_test_inputs, test_truths = _make_split(condition, world_seed, "test", n)
        salt = world_seed * 100_003 + codebook_seed
        val_corrupted = [
            _corrupt_input(x, t, condition, profile, salt) for x, t in zip(base_val_inputs, val_truths)
        ]
        test_corrupted = [
            _corrupt_input(x, t, condition, profile, salt) for x, t in zip(base_test_inputs, test_truths)
        ]
        val_inputs = [x[0] for x in val_corrupted]
        test_inputs = [x[0] for x in test_corrupted]
        labels_val = [x.label for x in val_truths]
        labels_test = [x.label for x in test_truths]
        thresholds: dict[str, float] = {}
        for arm in MEMORY_ARMS:
            thresholds[f"memory_{arm}"] = _threshold(
                _calibration_scores(val_inputs, books, arm, False), labels_val,
            )
            thresholds[f"hybrid_{arm}"] = _threshold(
                _calibration_scores(val_inputs, books, arm, True), labels_val,
            )
        predictions: dict[str, list[int]] = {
            "graph": [], "memory_slow_only": [], "memory_full_history": [],
            "hybrid_slow_only": [], "hybrid_full_history": [],
        }
        graph_ops: list[int] = []
        graph_bytes: list[int] = []
        event_bytes: list[int] = []
        graph_event_counts: list[int] = []
        unique_edge_counts: list[int] = []
        state_bytes: dict[str, list[int]] = {key: [] for key in predictions}
        query_ops: dict[str, list[int]] = {key: [] for key in predictions}
        per_sequence: list[dict[str, Any]] = []
        audit_summary = {
            "removed_unique_edge_count": 0, "removed_event_count": 0,
            "added_spurious_edge_count": 0,
        }
        for model_input, truth, (_, audit) in zip(test_inputs, test_truths, test_corrupted):
            graph = build_event_graph(model_input)
            graph_exists, witness, gops = graph_query(model_input, graph)
            predictions["graph"].append(int(graph_exists))
            graph_ops.append(gops)
            graph_bytes.append(graph.storage_bytes)
            event_bytes.append(len(_canonical_bytes(model_input.to_payload())))
            graph_event_counts.append(len(model_input.events))
            unique_edge_counts.append(len(graph.edge_set))
            for key in audit_summary:
                audit_summary[key] += int(audit[key])
            row_scores: dict[str, float] = {}
            for arm in MEMORY_ARMS:
                supports, mem_bytes = _memory_support(model_input, arm, books)
                mem_score, mem_ops = _composed_score(model_input, supports)
                hyb_score, hyb_ops = _composed_score(model_input, supports, graph)
                memory_key, hybrid_key = f"memory_{arm}", f"hybrid_{arm}"
                predictions[memory_key].append(int(_stable_geq(mem_score, thresholds[memory_key])))
                predictions[hybrid_key].append(int(_stable_geq(hyb_score, thresholds[hybrid_key])))
                row_scores[memory_key] = float(mem_score)
                row_scores[hybrid_key] = float(hyb_score)
                state_bytes[memory_key].append(mem_bytes)
                state_bytes[hybrid_key].append(mem_bytes + graph.storage_bytes)
                query_ops[memory_key].append(mem_ops)
                query_ops[hybrid_key].append(hyb_ops)
            state_bytes["graph"].append(graph.storage_bytes)
            query_ops["graph"].append(gops)
            per_sequence.append({
                "case_id": str(model_input.case_id), "input_sha256": model_input.input_sha256,
                "label": int(truth.label), "event_count": len(model_input.events),
                "unique_observed_edges": len(graph.edge_set),
                "graph_prediction": int(graph_exists),
                "graph_witness": list(witness) if witness else None,
                "graph_query_edge_examinations": int(gops),
                "scores": row_scores,
                "predictions": {key: int(predictions[key][-1]) for key in predictions},
                "corruption_audit": audit,
            })
        architectures: dict[str, Any] = {}
        for key, pred in predictions.items():
            architectures[key] = {
                "metrics": _metric_summary(labels_test, pred),
                "cost": _cost_summary(
                    event_bytes, state_bytes[key], query_ops[key],
                    graph_event_counts, unique_edge_counts,
                ),
                "validation_threshold": None if key == "graph" else float(thresholds[key]),
            }
        count = max(1, len(test_inputs))
        profiles_out[profile] = {
            "architectures": architectures,
            "corruption_totals": {key: int(value) for key, value in audit_summary.items()},
            "corruption_mean_per_case": {
                key: float(value / count) for key, value in audit_summary.items()
            },
            "per_sequence": per_sequence,
        }
    return {
        "experiment": EXPERIMENT_VERSION, "stage": "E02-C",
        "condition": condition, "world_seed": world_seed, "codebook_seed": codebook_seed,
        "sample_counts": {"validation": n, "held_out_test": n},
        "corruption_profiles": list(CORRUPTION_PROFILES),
        "profiles": profiles_out,
        "contract": {
            "model_input_schema": SCHEMA_VERSION,
            "model_prediction_inputs": ["entity_count", "observed_events", "query"],
            "evaluator_truth_fields_excluded": sorted(FORBIDDEN_MODEL_KEYS),
            "thresholds_fit_on_profile_matched_validation_only": True,
            "corruption_masks_excluded_from_model_input": True,
        },
        "interpretation_guard": (
            "Synthetic corruption study. Hybrid memory can only add scores derived from the same observed "
            "stream; it receives no missing-edge list, spurious-edge marker or evaluator truth. A hybrid "
            "gain is evidence for this specific temporal-support fallback, not general relational reasoning."
        ),
    }


def run_contract() -> dict[str, Any]:
    """Executable E02-A contract receipt, also exercised by unit tests."""
    case = make_case(7_700_001, entities=4, fact_count=8, distractors=3, depth=2, gap="medium")
    model_input, truth = _to_pair_with_entities(case, 4, 2)
    payload = model_input.to_payload()
    flattened = set(payload)
    flattened.update(k for event in payload["observed_events"] for k in event)
    flattened.update(payload["query"])
    leaked = sorted(flattened.intersection(FORBIDDEN_MODEL_KEYS))
    if leaked:
        raise AssertionError(f"evaluator fields leaked into model input: {leaked}")
    graph = build_event_graph(model_input)
    prediction, _, _ = graph_query(model_input, graph)
    return {
        "experiment": EXPERIMENT_VERSION, "stage": "E02-A",
        "status": "passed", "schema_version": SCHEMA_VERSION,
        "model_input_keys": sorted(payload), "forbidden_fields_found": leaked,
        "input_sha256": model_input.input_sha256,
        "observed_event_count": len(model_input.events),
        "graph_unique_edge_count": len(graph.edge_set),
        "clean_graph_query_prediction": bool(prediction),
        "evaluator_truth_stored_separately": True,
        "seed_manifest": {
            "world_seeds": list(WORLD_SEEDS), "codebook_seeds": list(CODEBOOK_SEEDS),
            "conditions": list(CONDITIONS), "default_sequences_per_split": 160,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("contract", "b", "c"), required=True)
    parser.add_argument("--condition", choices=tuple(CONDITIONS))
    parser.add_argument("--world-seed", type=int, choices=WORLD_SEEDS)
    parser.add_argument("--codebook-seed", type=int, choices=CODEBOOK_SEEDS)
    parser.add_argument("--n", type=int, default=160)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.stage == "contract":
        result = run_contract()
    else:
        if args.condition is None or args.world_seed is None or args.codebook_seed is None:
            parser.error("--condition, --world-seed and --codebook-seed are required for B/C")
        result = (
            run_b(args.condition, args.world_seed, args.codebook_seed, args.n)
            if args.stage == "b"
            else run_c(args.condition, args.world_seed, args.codebook_seed, args.n)
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.stage == "contract":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps({
            "stage": result["stage"], "condition": result["condition"],
            "world_seed": result["world_seed"], "codebook_seed": result["codebook_seed"],
            "architectures": (
                {key: value["metrics"]["accuracy"] for key, value in result["architectures"].items()}
                if args.stage == "b" else
                {
                    profile: {key: value["metrics"]["accuracy"] for key, value in item["architectures"].items()}
                    for profile, item in result["profiles"].items()
                }
            ),
        }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
