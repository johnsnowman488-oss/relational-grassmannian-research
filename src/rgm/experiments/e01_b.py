"""E01-B: controlled capacity and interference frontiers."""
from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ..memory import SOEMemory

FloatArray = NDArray[np.float64]
FEATURE_DIM = 16
SOE_RATES = (0.01, 0.05, 0.2, 0.8)
CODEBOOK_SEED = 9137
WORLD_SEEDS = (401, 402)
MEMORY_ARMS = ("slow_only", "full_soe", "current", "window2", "window8", "full_history")
GAP_PROFILES = {
    "short": (0.25, 0.5, 1.0),
    "medium": (2.0, 4.0, 8.0),
    "long": (16.0, 32.0, 64.0),
}

# One-factor sweeps: all unlisted factors remain fixed at the stated reference.
CONDITIONS: dict[str, dict[str, Any]] = {}
for _entities in (4, 8, 16, 32):
    CONDITIONS[f"entity_e{_entities}"] = {
        "sweep": "entity_scale", "entities": _entities, "facts": 8,
        "distractors": 16, "depth": 2, "gap": "medium",
    }
for _facts in (4, 8, 16, 32, 64):
    CONDITIONS[f"facts_f{_facts}"] = {
        "sweep": "fact_load", "entities": 16, "facts": _facts,
        "distractors": 16, "depth": 2, "gap": "medium",
    }
for _distractors in (0, 4, 16, 32):
    CONDITIONS[f"distractors_d{_distractors}"] = {
        "sweep": "distractor_load", "entities": 16, "facts": 16,
        "distractors": _distractors, "depth": 2, "gap": "medium",
    }
for _gap in ("short", "medium", "long"):
    CONDITIONS[f"gap_{_gap}"] = {
        "sweep": "temporal_gap", "entities": 16, "facts": 16,
        "distractors": 16, "depth": 2, "gap": _gap,
    }
for _depth in (1, 2, 3):
    CONDITIONS[f"depth_d{_depth}"] = {
        "sweep": "composition_depth", "entities": 16, "facts": 16,
        "distractors": 16, "depth": _depth, "gap": "medium",
    }


@dataclass(frozen=True)
class Event:
    relation: int
    subject: int
    object: int
    dt: float


@dataclass(frozen=True)
class Case:
    seed: int
    events: tuple[Event, ...]
    facts: frozenset[tuple[int, int, int]]
    query_subject: int
    query_object: int
    label: int
    planted_path: tuple[int, ...] | None
    distractor_count: int


def codebooks(entities: int, seed: int = CODEBOOK_SEED) -> tuple[FloatArray, FloatArray]:
    """Fixed 16-D codebooks; beyond four entities, normalized rows necessarily interfere."""
    if entities < 4:
        raise ValueError("entities must be at least four")
    if entities == 4:
        rng = np.random.default_rng(seed)
        q, r = np.linalg.qr(rng.normal(size=(FEATURE_DIM, FEATURE_DIM)))
        # QR bases are sign-ambiguous: canonicalize each column using R's diagonal
        # so independent CI workers encode the same seeded basis.
        signs = np.where(np.diag(r) < 0.0, -1.0, 1.0)
        q = q * signs[np.newaxis, :]
        return np.eye(FEATURE_DIM, dtype=np.float64), q.T.copy()
    rng = np.random.default_rng(seed + entities * 1009)
    books = []
    for _ in (0, 1):
        vectors = rng.normal(size=(entities * entities, FEATURE_DIM))
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        books.append(vectors.astype(np.float64))
    return books[0], books[1]


def event_vector(event: Event, books: tuple[FloatArray, FloatArray], entities: int) -> FloatArray:
    return books[event.relation][event.subject * entities + event.object].copy()


def _path_exists(facts: set[tuple[int, int, int]], subject: int,
                 obj: int, depth: int) -> bool:
    outgoing: dict[tuple[int, int], list[int]] = {}
    for relation, left, right in facts:
        outgoing.setdefault((relation, left), []).append(right)

    def walk(node: int, step: int) -> bool:
        if step == depth:
            return node == obj
        relation = step % 2
        return any(walk(nxt, step + 1) for nxt in outgoing.get((relation, node), ()))

    return walk(subject, 0)


def _make_case_once(seed: int, entities: int, fact_count: int, distractors: int,
                    depth: int, gap: str) -> Case:
    rng = np.random.default_rng(seed)
    subject, obj = rng.choice(entities, size=2, replace=False).tolist()
    positive = bool(seed % 2)
    path: tuple[int, ...] | None = None
    facts: set[tuple[int, int, int]] = set()
    if positive:
        available = [x for x in range(entities) if x not in (subject, obj)]
        intermediates = rng.choice(available, size=depth - 1, replace=False).tolist()
        nodes = (subject, *[int(x) for x in intermediates], obj)
        path = tuple(int(x) for x in nodes)
        for step in range(depth):
            facts.add((step % 2, nodes[step], nodes[step + 1]))

    candidates = [
        (relation, left, right)
        for relation in (0, 1)
        for left in range(entities)
        for right in range(entities)
        if left != right
    ]
    rng.shuffle(candidates)
    for fact in candidates:
        if len(facts) >= fact_count:
            break
        if fact in facts:
            continue
        proposed = facts | {fact}
        if not positive and _path_exists(proposed, subject, obj, depth):
            continue
        facts.add(fact)
    if len(facts) != fact_count:
        raise ValueError("could not construct requested distinct-fact count")

    path_facts = set()
    if path is not None:
        path_facts = {(step % 2, path[step], path[step + 1]) for step in range(depth)}
    distractor_pool = sorted(facts - path_facts) or sorted(facts)
    extra_indices = rng.integers(0, len(distractor_pool), size=distractors) if distractors else []
    pulses = sorted(facts) + [distractor_pool[int(i)] for i in extra_indices]
    rng.shuffle(pulses)
    events = tuple(
        Event(int(relation), int(left), int(right), float(rng.choice(GAP_PROFILES[gap])))
        for relation, left, right in pulses
    )
    return Case(
        seed=seed, events=events, facts=frozenset(facts),
        query_subject=int(subject), query_object=int(obj),
        label=int(positive), planted_path=path, distractor_count=distractors,
    )


def make_case(seed: int, entities: int, fact_count: int, distractors: int,
              depth: int, gap: str) -> Case:
    if depth not in (1, 2, 3):
        raise ValueError("composition depth must be 1, 2, or 3")
    if entities < depth + 1:
        raise ValueError("entity count must be at least composition depth + 1")
    if fact_count < depth or fact_count > 2 * entities * (entities - 1):
        raise ValueError("distinct fact count is outside the feasible range")
    if distractors < 0 or gap not in GAP_PROFILES:
        raise ValueError("invalid distractor count or temporal gap profile")
    for attempt in range(20):
        try:
            return _make_case_once(
                seed + attempt * 2000006, entities, fact_count, distractors, depth, gap
            )
        except ValueError:
            continue
    raise ValueError("could not generate a valid case after 20 deterministic attempts")


def _memory_channels(case: Case, arm: str,
                     books: tuple[FloatArray, FloatArray], entities: int) -> FloatArray:
    vectors = [event_vector(event, books, entities) for event in case.events]
    if arm == "current":
        return vectors[-1][None, :]
    if arm == "window2":
        return np.sum(vectors[-2:], axis=0)[None, :]
    if arm == "window8":
        return np.sum(vectors[-8:], axis=0)[None, :]
    if arm == "full_history":
        return np.sum(vectors, axis=0)[None, :]
    rates = (0.01,) if arm == "slow_only" else SOE_RATES if arm == "full_soe" else None
    if rates is None:
        raise ValueError(f"unknown memory arm: {arm}")
    memory = SOEMemory(feature_dim=FEATURE_DIM, decay_rates=rates)
    for event in case.events:
        memory.update(event_vector(event, books, entities), dt=event.dt)
    return memory.snapshot()


def _support_tensors(channels: FloatArray,
                     books: tuple[FloatArray, FloatArray],
                     entities: int) -> tuple[FloatArray, FloatArray]:
    supports = []
    for relation in (0, 1):
        scores = channels @ books[relation].T
        # Suppress positive round-off residue around exact orthogonality. Without
        # this floor, validation thresholds can depend on tiny BLAS/QR differences.
        scores = np.where(scores < 1e-12, 0.0, scores)
        supports.append(np.clip(scores, 0.0, 1.0).reshape(
            channels.shape[0], entities, entities
        ))
    return tuple(supports)  # type: ignore[return-value]


def _composition_score(case: Case, supports: tuple[FloatArray, FloatArray],
                       depth: int) -> tuple[float, tuple[int, ...], list[float]]:
    best_score = -1.0
    best_nodes: tuple[int, ...] = ()
    best_edges: list[float] = []
    intermediates = itertools.product(range(supports[0].shape[1]), repeat=depth - 1)
    for middle in intermediates:
        nodes = (case.query_subject, *middle, case.query_object)
        edge_scores = [
            float(np.max(supports[step % 2][:, nodes[step], nodes[step + 1]]))
            for step in range(depth)
        ]
        score = float(np.prod(edge_scores))
        if score > best_score:
            best_score, best_nodes, best_edges = score, tuple(nodes), edge_scores
    return max(0.0, best_score), best_nodes, best_edges


def _fact_probes(case: Case, supports: tuple[FloatArray, FloatArray],
                 seed: int) -> tuple[list[float], list[int]]:
    true_facts = sorted(case.facts)
    all_facts = [
        (relation, left, right)
        for relation in (0, 1)
        for left in range(supports[relation].shape[1])
        for right in range(supports[relation].shape[2])
        if left != right
    ]
    present = set(true_facts)
    absent = [fact for fact in all_facts if fact not in present]
    rng = np.random.default_rng(seed + 910003)
    sample_n = min(len(true_facts), len(absent))
    selected = [absent[int(i)] for i in rng.choice(len(absent), size=sample_n, replace=False)]
    probes = [(fact, 1) for fact in true_facts] + [(fact, 0) for fact in selected]
    scores, labels = [], []
    for (relation, left, right), label in probes:
        scores.append(float(np.max(supports[relation][:, left, right])))
        labels.append(label)
    return scores, labels


def _threshold(scores: list[float], labels: list[int]) -> float:
    values = np.unique(np.asarray([0.0, 1.0, *scores], dtype=np.float64))
    y = np.asarray(labels, dtype=np.int64)
    best_t, best = 0.5, -1.0
    for threshold in values:
        accuracy = float(np.mean((np.asarray(scores) >= threshold).astype(np.int64) == y))
        if accuracy > best or (accuracy == best and threshold > best_t):
            best_t, best = float(threshold), accuracy
    return best_t


def _wilson(k: int, n: int) -> list[float]:
    z, p = 1.959963984540054, k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / d
    half = z * np.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / d
    return [float(max(0.0, centre - half)), float(min(1.0, centre + half))]


def run(condition: str, memory_arm: str, world_seed: int,
        n: int = 160) -> dict[str, Any]:
    if condition not in CONDITIONS or memory_arm not in MEMORY_ARMS:
        raise ValueError("unknown condition or memory arm")
    if world_seed not in WORLD_SEEDS:
        raise ValueError(f"world_seed must be one of {WORLD_SEEDS}")
    params = CONDITIONS[condition]
    entities, fact_count = int(params["entities"]), int(params["facts"])
    distractors, depth, gap = int(params["distractors"]), int(params["depth"]), str(params["gap"])
    books = codebooks(entities, CODEBOOK_SEED)
    validation_start = 3000000 + world_seed * 10000
    test_start = 4000000 + world_seed * 10000

    def prepare(start: int) -> tuple[list[Case], list[FloatArray], list[tuple[FloatArray, FloatArray]], list[float], list[int]]:
        cases, states, support_list, fact_scores, fact_labels = [], [], [], [], []
        for index in range(n):
            case = make_case(start + index, entities, fact_count, distractors, depth, gap)
            channels = _memory_channels(case, memory_arm, books, entities)
            supports = _support_tensors(channels, books, entities)
            local_scores, local_labels = _fact_probes(case, supports, case.seed)
            cases.append(case)
            states.append(channels)
            support_list.append(supports)
            fact_scores.extend(local_scores)
            fact_labels.extend(local_labels)
        return cases, states, support_list, fact_scores, fact_labels

    validation, _, validation_supports, val_fact_scores, val_fact_labels = prepare(validation_start)
    val_composition_scores = [
        _composition_score(case, support, depth)[0]
        for case, support in zip(validation, validation_supports)
    ]
    composition_threshold = _threshold(val_composition_scores, [case.label for case in validation])
    fact_threshold = _threshold(val_fact_scores, val_fact_labels)

    test_cases, test_states, test_supports, test_fact_scores, test_fact_labels = prepare(test_start)
    per_sequence = []
    composition_scores, labels, predictions = [], [], []
    for case, state, support in zip(test_cases, test_states, test_supports):
        score, best_path, edge_scores = _composition_score(case, support, depth)
        prediction = int(score >= composition_threshold)
        composition_scores.append(score)
        labels.append(case.label)
        predictions.append(prediction)
        per_sequence.append({
            "seed": case.seed,
            "label": case.label,
            "query": {"subject": case.query_subject, "object": case.query_object},
            "event_count": len(case.events),
            "unique_fact_count": len(case.facts),
            "distractor_count": case.distractor_count,
            "composition_score": score,
            "composition_prediction": prediction,
            "best_path": list(best_path),
            "best_path_edge_supports": edge_scores,
            "state_scalar_count": int(state.size),
            "channel_state_norms": np.linalg.norm(state, axis=1).tolist(),
            "events": [
                {"relation": e.relation, "subject": e.subject, "object": e.object, "dt": e.dt}
                for e in case.events
            ],
        })

    y = np.asarray(labels, dtype=np.int64)
    pred = np.asarray(predictions, dtype=np.int64)
    scores = np.asarray(composition_scores, dtype=np.float64)
    correct = int(np.sum(y == pred))
    tpr = float(np.mean(pred[y == 1] == 1))
    tnr = float(np.mean(pred[y == 0] == 0))
    fy = np.asarray(test_fact_labels, dtype=np.int64)
    fpred = (np.asarray(test_fact_scores) >= fact_threshold).astype(np.int64)
    tp = int(np.sum((fy == 1) & (fpred == 1)))
    fpos = int(np.sum((fy == 0) & (fpred == 1)))
    fneg = int(np.sum((fy == 1) & (fpred == 0)))
    state_count = 64 if memory_arm == "full_soe" else 16
    return {
        "experiment": "E01-B",
        "condition": condition,
        "sweep": params["sweep"],
        "memory_arm": memory_arm,
        "world_seed": world_seed,
        "codebook_seed": CODEBOOK_SEED,
        "parameters": {
            "entities": entities, "distinct_facts": fact_count,
            "distractor_events": distractors, "composition_depth": depth,
            "gap_profile": gap, "gap_values": list(GAP_PROFILES[gap]),
            "feature_dim": FEATURE_DIM, "soe_rates": list(SOE_RATES),
            "state_scalar_count": state_count,
        },
        "seed_ranges": {
            "validation": [validation_start, validation_start + n - 1],
            "test": [test_start, test_start + n - 1],
        },
        "sample_counts": {
            "validation": n, "test": n,
            "fact_probes_test": len(test_fact_labels),
        },
        "thresholds": {
            "composition": composition_threshold,
            "constituent_fact": fact_threshold,
            "fit_on_validation_only": True,
        },
        "composition": {
            "accuracy": correct / n,
            "accuracy_wilson_95": _wilson(correct, n),
            "balanced_accuracy": (tpr + tnr) / 2.0,
            "brier_raw_support": float(np.mean((scores - y) ** 2)),
            "positive_mean_score": float(np.mean(scores[y == 1])),
            "negative_mean_score": float(np.mean(scores[y == 0])),
        },
        "constituent_retrieval": {
            "accuracy": float(np.mean(fy == fpred)),
            "precision": tp / max(1, tp + fpos),
            "recall": tp / max(1, tp + fneg),
            "true_positive": tp, "false_positive": fpos, "false_negative": fneg,
        },
        "per_sequence": per_sequence,
        "interpretation_guard": (
            "Synthetic one-factor frontier. The 16-D codebook is orthogonal only at four entities; "
            "larger entity counts use normalized random codewords and intentionally expose codebook "
            "interference. Full SOE uses 64 scalars; all other arms use 16."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition", choices=tuple(CONDITIONS), required=True)
    parser.add_argument("--memory-arm", choices=MEMORY_ARMS, required=True)
    parser.add_argument("--world-seed", type=int, choices=WORLD_SEEDS, required=True)
    parser.add_argument("--n", type=int, default=160)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.condition, args.memory_arm, args.world_seed, args.n)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "per_sequence"},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
