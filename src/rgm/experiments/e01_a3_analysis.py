"""Aggregate E01-A3 replicated cells with replicate-level paired uncertainty."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binomtest


def _paired(base_cells: dict[tuple[int, int], dict[str, Any]],
            other_cells: dict[tuple[int, int], dict[str, Any]],
            seed: int) -> dict[str, Any]:
    replicate_keys = sorted(set(base_cells) & set(other_cells))
    if len(replicate_keys) != 9:
        raise ValueError(f"expected 9 paired world/codebook cells, found {len(replicate_keys)}")
    base_acc, other_acc, deltas = [], [], []
    base_correct, other_correct = [], []
    for key in replicate_keys:
        a = {row["seed"]: row for row in base_cells[key]["per_sequence"]}
        b = {row["seed"]: row for row in other_cells[key]["per_sequence"]}
        common = sorted(set(a) & set(b))
        if len(common) != 160:
            raise ValueError(f"expected 160 paired test cases in replicate {key}, found {len(common)}")
        ca = np.asarray([a[s]["composition_prediction"] == a[s]["label"] for s in common], dtype=np.int8)
        cb = np.asarray([b[s]["composition_prediction"] == b[s]["label"] for s in common], dtype=np.int8)
        base_acc.append(float(np.mean(ca)))
        other_acc.append(float(np.mean(cb)))
        deltas.append(float(np.mean(cb - ca)))
        base_correct.extend(ca.tolist())
        other_correct.extend(cb.tolist())
    delta = np.asarray(deltas, dtype=np.float64)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(delta), size=(10000, len(delta)))
    boot = np.mean(delta[draws], axis=1)
    positive = int(np.sum(delta > 0))
    negative = int(np.sum(delta < 0))
    tied = int(np.sum(delta == 0))
    sign_p = float(binomtest(positive, positive + negative, 0.5).pvalue) if positive + negative else 1.0
    ca, cb = np.asarray(base_correct), np.asarray(other_correct)
    base_to_other = int(np.sum((ca == 1) & (cb == 0)))
    other_to_base = int(np.sum((ca == 0) & (cb == 1)))
    discordant = base_to_other + other_to_base
    mcnemar_p = float(binomtest(other_to_base, discordant, 0.5).pvalue) if discordant else 1.0
    return {
        "paired_replicates": len(replicate_keys),
        "paired_test_sequences": len(ca),
        "baseline_mean_accuracy": float(np.mean(base_acc)),
        "comparison_mean_accuracy": float(np.mean(other_acc)),
        "mean_replicate_accuracy_difference": float(np.mean(delta)),
        "replicate_difference_values": [float(x) for x in delta],
        "replicate_paired_bootstrap_95": [float(x) for x in np.quantile(boot, [0.025, 0.975])],
        "replicates_improved": positive,
        "replicates_worsened": negative,
        "replicates_tied": tied,
        "replicate_sign_test_exact_p": sign_p,
        "pooled_sequence_mcnemar": {
            "baseline_correct_comparison_wrong": base_to_other,
            "baseline_wrong_comparison_correct": other_to_base,
            "discordant_pairs": discordant,
            "exact_two_sided_p": mcnemar_p,
            "note": "Secondary pooled test; sequences repeat across codebook seeds, so replicate-level inference is primary."
        },
    }


def analyze(input_dir: Path) -> dict[str, Any]:
    files = sorted(input_dir.glob("ci-*.json"))
    if len(files) != 54:
        raise ValueError(f"expected 54 E01-A3 cell artifacts, found {len(files)}")
    cells: dict[str, dict[tuple[int, int], dict[str, Any]]] = {}
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        config = payload["configuration"]
        key = (int(payload["world_seed"]), int(payload["codebook_seed"]))
        bucket = cells.setdefault(config, {})
        if key in bucket:
            raise ValueError(f"duplicate cell for {config}, {key}")
        bucket[key] = payload
    expected_configs = {"full_max", "slow_only_max", "drop_slow_max",
                        "drop_channel2_max", "full_same", "full_mean"}
    if set(cells) != expected_configs:
        raise ValueError(f"configuration set mismatch: {sorted(cells)}")
    baseline_name = "full_max"
    baseline = cells[baseline_name]
    summaries = {}
    for name, reps in sorted(cells.items()):
        accuracies = np.asarray([v["composition"]["accuracy"] for v in reps.values()])
        fact_accuracies = np.asarray([v["constituent_retrieval"]["accuracy"] for v in reps.values()])
        summaries[name] = {
            "replicates": len(reps),
            "composition_accuracy_mean": float(np.mean(accuracies)),
            "composition_accuracy_sd_between_replicates": float(np.std(accuracies, ddof=1)),
            "composition_accuracy_min": float(np.min(accuracies)),
            "composition_accuracy_max": float(np.max(accuracies)),
            "constituent_retrieval_accuracy_mean": float(np.mean(fact_accuracies)),
            "cell_results": [
                {"world_seed": k[0], "codebook_seed": k[1],
                 "composition_accuracy": v["composition"]["accuracy"],
                 "constituent_retrieval_accuracy": v["constituent_retrieval"]["accuracy"]}
                for k, v in sorted(reps.items())
            ],
        }
    comparisons = {
        name: _paired(baseline, reps, seed=52000 + i)
        for i, (name, reps) in enumerate(sorted(cells.items()))
        if name != baseline_name
    }
    return {
        "experiment": "E01-A3 replicated diagnostic",
        "baseline": baseline_name,
        "world_seeds": [101, 202, 303],
        "codebook_seeds": [9137, 27183, 65537],
        "replicates_per_configuration": 9,
        "test_sequences_per_replicate": 160,
        "total_cells": len(files),
        "configuration_summaries": summaries,
        "paired_comparisons_vs_full_max": comparisons,
        "interpretation_guard": (
            "Replicates vary synthetic-world and codebook seeds, but retain the same task generator, "
            "fixed encoder family, and supplied candidate-middle decoder. Replicate-level paired "
            "intervals are primary; pooled sequence McNemar is secondary because worlds recur across "
            "codebook seeds. This does not establish general relational reasoning."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
