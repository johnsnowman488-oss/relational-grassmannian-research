"""E01-A3: replicate selected E01-A2 configurations across worlds and codebooks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from .e01 import make_case, codebooks, FEATURE_DIM, RATES
from .e01_a2 import (
    _memory_channels, _case_evidence, _threshold, _wilson,
)

CONFIGURATIONS = {
    "full_max": ("full", "max_channel"),
    "slow_only_max": ("only_0", "max_channel"),
    "drop_slow_max": ("drop_0", "max_channel"),
    "drop_channel2_max": ("drop_2", "max_channel"),
    "full_same": ("full", "same_channel"),
    "full_mean": ("full", "mean_channel"),
}
WORLD_SEEDS = (101, 202, 303)
CODEBOOK_SEEDS = (9137, 27183, 65537)
DEFAULT_N = 160


def run(configuration: str, world_seed: int, codebook_seed: int,
        n: int = DEFAULT_N) -> dict[str, Any]:
    if configuration not in CONFIGURATIONS:
        raise ValueError(f"unknown replication configuration: {configuration}")
    if world_seed not in WORLD_SEEDS:
        raise ValueError(f"world_seed must be one of {WORLD_SEEDS}")
    if codebook_seed not in CODEBOOK_SEEDS:
        raise ValueError(f"codebook_seed must be one of {CODEBOOK_SEEDS}")
    if n < 20:
        raise ValueError("n must be at least 20")

    memory_config, readout = CONFIGURATIONS[configuration]
    books = codebooks(seed=codebook_seed)
    validation_start = 100000 + world_seed * 1000
    test_start = 200000 + world_seed * 1000
    validation = [make_case(validation_start + i) for i in range(n)]
    test = [make_case(test_start + i) for i in range(n)]

    val_evidence = [
        _case_evidence(c, _memory_channels(c, memory_config, books), books, readout)
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
        _case_evidence(c, _memory_channels(c, memory_config, books), books, readout)
        for c in test
    ]
    fact_y, fact_pred = [], []
    for row in evidence:
        row["composition_prediction"] = int(row["composition_score"] >= composition_threshold)
        for fact in row["candidate_facts"]:
            fact["retrieved_prediction"] = int(fact["readout_support"] >= fact_threshold)
            fact_y.append(fact["present"])
            fact_pred.append(fact["retrieved_prediction"])
    fact_y_a = np.asarray(fact_y, dtype=np.int64)
    fact_pred_a = np.asarray(fact_pred, dtype=np.int64)
    tp = int(np.sum((fact_y_a == 1) & (fact_pred_a == 1)))
    fp = int(np.sum((fact_y_a == 0) & (fact_pred_a == 1)))
    fn = int(np.sum((fact_y_a == 1) & (fact_pred_a == 0)))

    labels = np.asarray([row["label"] for row in evidence], dtype=np.int64)
    scores = np.asarray([row["composition_score"] for row in evidence])
    predictions = np.asarray([row["composition_prediction"] for row in evidence], dtype=np.int64)
    correct = int(np.sum(predictions == labels))
    tpr = float(np.mean(predictions[labels == 1] == 1))
    tnr = float(np.mean(predictions[labels == 0] == 0))
    return {
        "experiment": "E01-A3",
        "configuration": configuration,
        "memory_config": memory_config,
        "readout": readout,
        "world_seed": world_seed,
        "codebook_seed": codebook_seed,
        "seed_ranges": {
            "validation": [validation_start, validation_start + n - 1],
            "test": [test_start, test_start + n - 1],
        },
        "sample_counts": {"validation": n, "test": n, "candidate_fact_test": len(fact_y)},
        "thresholds": {"constituent_fact": fact_threshold,
                       "composition": composition_threshold},
        "constituent_retrieval": {
            "accuracy": float(np.mean(fact_y_a == fact_pred_a)),
            "precision": tp / max(1, tp + fp),
            "recall": tp / max(1, tp + fn),
            "true_positive": tp, "false_positive": fp, "false_negative": fn,
        },
        "composition": {
            "accuracy": correct / len(evidence),
            "accuracy_wilson_95": _wilson(correct, len(evidence)),
            "balanced_accuracy": (tpr + tnr) / 2.0,
            "brier_raw_support": float(np.mean((scores - labels) ** 2)),
            "positive_mean_score": float(np.mean(scores[labels == 1])),
            "negative_mean_score": float(np.mean(scores[labels == 0])),
        },
        "configuration_frozen": {
            "feature_dim": FEATURE_DIM,
            "soe_rates": list(RATES),
            "entities": 4,
            "composition_depth": 2,
            "thresholds_fit_on_validation_only": True,
        },
        "per_sequence": evidence,
        "interpretation_guard": (
            "Replication of a small synthetic task family only. Codebook and world seeds "
            "vary, but the fixed event generator and supplied candidate-middle decoder remain."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", choices=tuple(CONFIGURATIONS), required=True)
    parser.add_argument("--world-seed", type=int, choices=WORLD_SEEDS, required=True)
    parser.add_argument("--codebook-seed", type=int, choices=CODEBOOK_SEEDS, required=True)
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.configuration, args.world_seed, args.codebook_seed, args.n)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "per_sequence"},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
