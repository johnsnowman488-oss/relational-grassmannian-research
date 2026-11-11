"""E01-A2 diagnostic audit: constituent retrieval and SOE readout controls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .e01 import (
    ENTITIES, FEATURE_DIM, RATES, Case, codebooks, event_vector, make_case,
)
from ..memory import SOEMemory

FloatArray = NDArray[np.float64]
MEMORY_CONFIGS = (
    "full", "only_0", "only_1", "only_2", "only_3",
    "drop_0", "drop_1", "drop_2", "drop_3",
)
READOUTS = ("max_channel", "same_channel", "mean_channel")
VALIDATION_START, TEST_START = 20000, 30000
DEFAULT_N = 160


def _memory_channels(case: Case, config: str, books: tuple[FloatArray, FloatArray]) -> FloatArray:
    """Return the selected SOE channels, retaining original channel indices."""
    if config not in MEMORY_CONFIGS:
        raise ValueError(f"unknown memory config: {config}")
    memory = SOEMemory(feature_dim=FEATURE_DIM, decay_rates=RATES)
    for event in case.events:
        memory.update(event_vector(event, books), dt=event.dt)
    state = memory.snapshot()
    if config == "full":
        indices = [0, 1, 2, 3]
    elif config.startswith("only_"):
        indices = [int(config[-1])]
    else:
        excluded = int(config[-1])
        indices = [i for i in range(4) if i != excluded]
    return state[indices, :]


def _fact_scores(channels: FloatArray, books: tuple[FloatArray, FloatArray]) -> dict[str, FloatArray]:
    """Scores for every possible typed directed fact, separately by channel."""
    result: dict[str, FloatArray] = {}
    for relation in (0, 1):
        # Shape: channels x subject x object. Diagonal facts are excluded downstream.
        result[str(relation)] = np.clip(channels @ books[relation].T, 0.0, 1.0)
    return result


def _fact_support(scores: FloatArray, readout: str) -> FloatArray:
    if readout == "max_channel":
        return np.max(scores, axis=0)
    if readout == "mean_channel":
        return np.mean(scores, axis=0)
    if readout == "same_channel":
        # Fact-level retrieval still uses a fixed mean; same-channel restriction
        # applies to the two-fact composition, not to individual fact evidence.
        return np.mean(scores, axis=0)
    raise ValueError(f"unknown readout: {readout}")


def _composition_score(case: Case, scores: dict[str, FloatArray], readout: str) -> float:
    subject, obj = case.query_subject, case.query_object
    left = scores["0"][:, subject, :]
    right = scores["1"][:, :, obj]
    if readout == "max_channel":
        # Reproduce E01-A: each fact may select its own best channel.
        return float(np.max(np.max(left, axis=0) * np.max(right, axis=0)))
    if readout == "same_channel":
        # Both edges must be supported by the same SOE channel.
        return float(np.max(np.max(left * right, axis=1)))
    if readout == "mean_channel":
        # Prespecified equal-weight aggregation; no per-fact channel selection.
        return float(np.max(np.mean(left, axis=0) * np.mean(right, axis=0)))
    raise ValueError(f"unknown readout: {readout}")


def _threshold(scores: list[float], labels: list[int]) -> float:
    values = np.unique(np.asarray([0.0, 1.0, *scores], dtype=np.float64))
    y = np.asarray(labels, dtype=np.int64)
    best_t, best = 0.5, -1.0
    for t in values:
        acc = float(np.mean((np.asarray(scores) >= t).astype(np.int64) == y))
        if acc > best or (acc == best and t > best_t):
            best_t, best = float(t), acc
    return best_t


def _wilson(k: int, n: int) -> list[float]:
    z, p = 1.959963984540054, k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / d
    half = z * np.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / d
    return [float(max(0.0, centre - half)), float(min(1.0, centre + half))]


def _case_evidence(case: Case, channels: FloatArray,
                   books: tuple[FloatArray, FloatArray], readout: str) -> dict[str, Any]:
    raw = _fact_scores(channels, books)
    fact_scores = {r: _fact_support(s, readout) for r, s in raw.items()}
    true_facts = {(e.relation, e.subject, e.object) for e in case.events}
    candidates = []
    for relation in (0, 1):
        for subject in range(ENTITIES):
            for obj in range(ENTITIES):
                if subject == obj:
                    continue
                candidates.append({
                    "relation": relation, "subject": subject, "object": obj,
                    "present": int((relation, subject, obj) in true_facts),
                    "channel_support": raw[str(relation)][:, subject, obj].tolist(),
                    "readout_support": float(fact_scores[str(relation)][subject, obj]),
                })
    return {
        "seed": case.seed, "label": case.label,
        "query": {"subject": case.query_subject, "object": case.query_object},
        "events": [{"relation": e.relation, "subject": e.subject,
                    "object": e.object, "dt": e.dt} for e in case.events],
        "candidate_facts": candidates,
        "composition_score": _composition_score(case, raw, readout),
        "channel_state_norms": np.linalg.norm(channels, axis=1).tolist(),
    }


def run(config: str, readout: str, n: int = DEFAULT_N) -> dict[str, Any]:
    if config not in MEMORY_CONFIGS or readout not in READOUTS:
        raise ValueError("unknown memory config or readout")
    books = codebooks()
    validation = [make_case(VALIDATION_START + i) for i in range(n)]
    test = [make_case(TEST_START + i) for i in range(n)]

    val_evidence = [
        _case_evidence(c, _memory_channels(c, config, books), books, readout)
        for c in validation
    ]
    fact_val_scores = [f["readout_support"] for row in val_evidence for f in row["candidate_facts"]]
    fact_val_labels = [f["present"] for row in val_evidence for f in row["candidate_facts"]]
    fact_threshold = _threshold(fact_val_scores, fact_val_labels)
    composition_threshold = _threshold(
        [row["composition_score"] for row in val_evidence],
        [row["label"] for row in val_evidence],
    )

    evidence = [
        _case_evidence(c, _memory_channels(c, config, books), books, readout)
        for c in test
    ]
    fact_y, fact_pred = [], []
    for row in evidence:
        for fact in row["candidate_facts"]:
            fact_y.append(fact["present"])
            fact_pred.append(int(fact["readout_support"] >= fact_threshold))
    fact_y_a, fact_pred_a = np.asarray(fact_y), np.asarray(fact_pred)
    fact_tp = int(np.sum((fact_y_a == 1) & (fact_pred_a == 1)))
    fact_fp = int(np.sum((fact_y_a == 0) & (fact_pred_a == 1)))
    fact_fn = int(np.sum((fact_y_a == 1) & (fact_pred_a == 0)))
    comp_y = np.asarray([row["label"] for row in evidence], dtype=np.int64)
    comp_score = np.asarray([row["composition_score"] for row in evidence])
    comp_pred = (comp_score >= composition_threshold).astype(np.int64)
    comp_correct = int(np.sum(comp_pred == comp_y))
    comp_tpr = float(np.mean(comp_pred[comp_y == 1] == 1))
    comp_tnr = float(np.mean(comp_pred[comp_y == 0] == 0))
    return {
        "experiment": "E01-A2", "memory_config": config, "readout": readout,
        "codebook_seed": 9137,
        "seed_ranges": {"validation": [VALIDATION_START, VALIDATION_START+n-1],
                        "test": [TEST_START, TEST_START+n-1]},
        "sample_counts": {"validation": n, "test": n,
                          "candidate_fact_test": len(fact_y)},
        "configuration": {"feature_dim": FEATURE_DIM, "entities": ENTITIES,
                          "soe_rates": list(RATES), "composition_depth": 2,
                          "thresholds_fit_on_validation_only": True},
        "thresholds": {"constituent_fact": fact_threshold,
                       "composition": composition_threshold},
        "constituent_retrieval": {
            "accuracy": float(np.mean(fact_y_a == fact_pred_a)),
            "precision": fact_tp / max(1, fact_tp + fact_fp),
            "recall": fact_tp / max(1, fact_tp + fact_fn),
            "true_positive": fact_tp, "false_positive": fact_fp,
            "false_negative": fact_fn,
        },
        "composition": {
            "accuracy": comp_correct / len(evidence),
            "accuracy_wilson_95": _wilson(comp_correct, len(evidence)),
            "balanced_accuracy": (comp_tpr + comp_tnr) / 2.0,
            "brier_raw_support": float(np.mean((comp_score - comp_y) ** 2)),
            "positive_mean_score": float(np.mean(comp_score[comp_y == 1])),
            "negative_mean_score": float(np.mean(comp_score[comp_y == 0])),
        },
        "per_sequence": evidence,
        "interpretation_guard": (
            "Synthetic diagnostic only. Fixed codebooks and a supplied candidate-middle "
            "decoder do not establish relation discovery or general relational reasoning."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-config", choices=MEMORY_CONFIGS, required=True)
    parser.add_argument("--readout", choices=READOUTS, required=True)
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.n < 20:
        parser.error("--n must be at least 20")
    payload = run(args.memory_config, args.readout, args.n)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "per_sequence"},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
