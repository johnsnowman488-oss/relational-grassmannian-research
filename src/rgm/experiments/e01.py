"""E01-A: memory-only compositional inference on synthetic event histories."""
from __future__ import annotations
import argparse, json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import numpy as np
from numpy.typing import NDArray
from ..memory import SOEMemory
FloatArray = NDArray[np.float64]
ENTITIES, FEATURE_DIM = 4, 16
RATES = (0.01, 0.05, 0.2, 0.8)
VARIANTS = ("soe", "current", "window2", "window8", "reset", "slow_only", "fast_only", "shuffled", "full_history")

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
    query_subject: int
    query_object: int
    label: int

def codebooks(seed: int = 9137) -> tuple[FloatArray, FloatArray]:
    rng = np.random.default_rng(seed)
    q, _ = np.linalg.qr(rng.normal(size=(FEATURE_DIM, FEATURE_DIM)))
    return np.eye(FEATURE_DIM, dtype=np.float64), q.T.copy()

def event_vector(event: Event, books: tuple[FloatArray, FloatArray]) -> FloatArray:
    return books[event.relation][event.subject * ENTITIES + event.object].copy()

def _has_path(facts: set[tuple[int, int, int]], subject: int, obj: int) -> bool:
    middle = {b for rel, a, b in facts if rel == 0 and a == subject}
    return any((1, b, obj) in facts for b in middle)

def make_case(seed: int) -> Case:
    rng = np.random.default_rng(seed)
    subject, obj = rng.choice(ENTITIES, size=2, replace=False).tolist()
    positive = bool(seed % 2)
    facts: set[tuple[int, int, int]] = set()
    if positive:
        middle = int(rng.choice([x for x in range(ENTITIES) if x not in (subject, obj)]))
        facts.update(((0, subject, middle), (1, middle, obj)))
    candidates = [(r, a, b) for r in (0, 1) for a in range(ENTITIES) for b in range(ENTITIES) if a != b]
    rng.shuffle(candidates)
    target_size = int(rng.integers(9, 13))
    for fact in candidates:
        if len(facts) >= target_size:
            break
        if fact in facts:
            continue
        proposed = facts | {fact}
        if not positive and _has_path(proposed, subject, obj):
            continue
        facts.add(fact)
    if positive and not _has_path(facts, subject, obj):
        raise AssertionError("positive generator lost its planted path")
    ordered = list(facts)
    rng.shuffle(ordered)
    gaps = (0.5, 1.0, 4.0, 12.0, 16.0)
    events = tuple(Event(r, a, b, float(rng.choice(gaps))) for r, a, b in ordered)
    return Case(seed, events, int(subject), int(obj), int(positive))

def _memory_vector(case: Case, variant: str, books: tuple[FloatArray, FloatArray]) -> FloatArray:
    vectors = [event_vector(event, books) for event in case.events]
    if variant == "full_history":
        return np.sum(vectors, axis=0)
    if variant == "reset":
        return np.zeros(FEATURE_DIM, dtype=np.float64)
    if variant == "current":
        return vectors[-1]
    if variant in ("window2", "window8"):
        return np.sum(vectors[-(2 if variant == "window2" else 8):], axis=0)
    events: Iterable[Event] = case.events
    if variant == "shuffled":
        events = tuple(np.random.default_rng(case.seed + 700001).permutation(case.events).tolist())
    rates = RATES if variant in ("soe", "shuffled") else ((0.01,) if variant == "slow_only" else (0.8,))
    memory = SOEMemory(feature_dim=FEATURE_DIM, decay_rates=rates)
    for event in events:
        memory.update(event_vector(event, books), dt=event.dt)
    return memory.snapshot()

def _support(vector: FloatArray, code: FloatArray) -> float:
    scores = np.asarray(vector) @ code
    if scores.ndim == 0:
        return float(np.clip(scores, 0.0, 1.0))
    return float(np.clip(np.max(scores), 0.0, 1.0))

def query_score(case: Case, vector: FloatArray, books: tuple[FloatArray, FloatArray]) -> float:
    products = []
    for middle in range(ENTITIES):
        i1 = case.query_subject * ENTITIES + middle
        i2 = middle * ENTITIES + case.query_object
        a = _support(vector, books[0][i1])
        b = _support(vector, books[1][i2])
        products.append(a * b)
    return float(max(products))

def _best_threshold(scores: FloatArray, labels: FloatArray) -> float:
    candidates = np.unique(np.concatenate(([0.0, 1.0], scores)))
    best_t, best_acc = 0.5, -1.0
    for threshold in candidates:
        acc = float(np.mean((scores >= threshold) == labels))
        if acc > best_acc or (acc == best_acc and threshold > best_t):
            best_t, best_acc = float(threshold), acc
    return best_t

def _wilson(k: int, n: int) -> list[float]:
    z, p = 1.959963984540054, k / n
    d = 1 + z*z/n
    centre = (p + z*z/(2*n))/d
    half = z*np.sqrt((p*(1-p) + z*z/(4*n))/n)/d
    return [float(max(0, centre-half)), float(min(1, centre+half))]

def run_variant(variant: str, validation_n: int = 160, test_n: int = 160) -> dict:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant: {variant}")
    books = codebooks()
    validation = [make_case(20000+i) for i in range(validation_n)]
    test = [make_case(30000+i) for i in range(test_n)]
    score = lambda c: query_score(c, _memory_vector(c, variant, books), books)
    val_scores = np.asarray([score(c) for c in validation])
    val_labels = np.asarray([c.label for c in validation], dtype=np.float64)
    threshold = _best_threshold(val_scores, val_labels)
    scores = np.asarray([score(c) for c in test])
    labels = np.asarray([c.label for c in test], dtype=np.int64)
    pred = (scores >= threshold).astype(np.int64)
    correct = int(np.sum(pred == labels))
    tpr = float(np.mean(pred[labels == 1] == 1))
    tnr = float(np.mean(pred[labels == 0] == 0))
    return {
        "experiment": "E01-A", "variant": variant,
        "seed_ranges": {"validation": [20000, 20000+validation_n-1], "test": [30000, 30000+test_n-1]},
        "sample_counts": {"validation": validation_n, "test": test_n},
        "configuration": {"feature_dim": 16, "entities": 4, "soe_rates": list(RATES), "composition_depth": 2, "temporal_gaps": [0.5, 1.0, 4.0, 12.0, 16.0], "threshold_source": "validation_only"},
        "threshold": threshold,
        "test": {"accuracy": correct/len(test), "accuracy_wilson_95": _wilson(correct, len(test)), "balanced_accuracy": (tpr+tnr)/2, "brier_score": float(np.mean((scores-labels)**2)), "positive_nonzero_composition_support_rate": float(np.mean(scores[labels == 1] > 0.0)), "mean_score_positive": float(np.mean(scores[labels == 1])), "mean_score_negative": float(np.mean(scores[labels == 0]))},
        "interpretation_guard": "Synthetic pipeline result only; not evidence of general relational reasoning or broad SOE superiority."
    }

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    payload = json.dumps(run_variant(args.variant), indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)

if __name__ == "__main__":
    main()
