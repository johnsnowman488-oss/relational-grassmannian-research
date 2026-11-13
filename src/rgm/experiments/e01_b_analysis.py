"""Aggregate E01-B one-factor frontiers without overclaiming two-world significance."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binomtest

from .e01_b import CONDITIONS, MEMORY_ARMS, WORLD_SEEDS


def _paired_world(base: dict[int, dict[str, Any]],
                  other: dict[int, dict[str, Any]]) -> dict[str, Any]:
    common = sorted(set(base) & set(other))
    if not common:
        raise ValueError("no paired test sequence IDs")
    a = np.asarray([base[k]["composition_prediction"] == base[k]["label"] for k in common], dtype=np.int8)
    b = np.asarray([other[k]["composition_prediction"] == other[k]["label"] for k in common], dtype=np.int8)
    better = int(np.sum((a == 0) & (b == 1)))
    worse = int(np.sum((a == 1) & (b == 0)))
    discordant = better + worse
    p = float(binomtest(better, discordant, 0.5).pvalue) if discordant else 1.0
    return {
        "n_paired_sequences": len(common),
        "baseline_accuracy": float(np.mean(a)),
        "comparison_accuracy": float(np.mean(b)),
        "accuracy_difference": float(np.mean(b - a)),
        "baseline_correct_comparison_wrong": worse,
        "baseline_wrong_comparison_correct": better,
        "discordant_pairs": discordant,
        "mcnemar_exact_two_sided_p": p,
    }


def analyze(input_dir: Path) -> dict[str, Any]:
    files = sorted(input_dir.glob("ci-*.json"))
    expected = len(CONDITIONS) * len(MEMORY_ARMS) * len(WORLD_SEEDS)
    if len(files) != expected:
        raise ValueError(f"expected {expected} E01-B cell artifacts, found {len(files)}")
    cells: dict[str, dict[str, dict[int, dict[str, Any]]]] = {}
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        condition, arm, world = payload["condition"], payload["memory_arm"], int(payload["world_seed"])
        bucket = cells.setdefault(condition, {}).setdefault(arm, {})
        if world in bucket:
            raise ValueError(f"duplicate artifact for {condition}/{arm}/world {world}")
        bucket[world] = payload
    if set(cells) != set(CONDITIONS):
        raise ValueError("condition set does not match the frozen E01-B protocol")

    summaries: dict[str, Any] = {}
    for condition, arms in sorted(cells.items()):
        if set(arms) != set(MEMORY_ARMS):
            raise ValueError(f"memory-arm set incomplete for {condition}")
        baseline = arms["slow_only"]
        arm_summaries = {}
        for arm, worlds in sorted(arms.items()):
            if set(worlds) != set(WORLD_SEEDS):
                raise ValueError(f"world-seed set incomplete for {condition}/{arm}")
            acc = [worlds[w]["composition"]["accuracy"] for w in WORLD_SEEDS]
            fact_acc = [worlds[w]["constituent_retrieval"]["accuracy"] for w in WORLD_SEEDS]
            state_counts = [worlds[w]["parameters"]["state_scalar_count"] for w in WORLD_SEEDS]
            comparisons = {
                str(w): _paired_world(
                    {r["seed"]: r for r in baseline[w]["per_sequence"]},
                    {r["seed"]: r for r in worlds[w]["per_sequence"]},
                )
                for w in WORLD_SEEDS
            } if arm != "slow_only" else {}
            deltas = [comparisons[str(w)]["accuracy_difference"] for w in WORLD_SEEDS] if comparisons else [0.0, 0.0]
            arm_summaries[arm] = {
                "mean_composition_accuracy": float(np.mean(acc)),
                "world_accuracies": {str(w): float(worlds[w]["composition"]["accuracy"]) for w in WORLD_SEEDS},
                "mean_constituent_retrieval_accuracy": float(np.mean(fact_acc)),
                "state_scalar_count": int(state_counts[0]),
                "mean_difference_vs_slow_only": float(np.mean(deltas)),
                "paired_world_comparisons_vs_slow_only": comparisons,
            }
        raw_params = next(iter(arms.values()))[WORLD_SEEDS[0]]["parameters"]
        params = {key: value for key, value in raw_params.items() if key != "state_scalar_count"}
        summaries[condition] = {"parameters": params, "memory_arms": arm_summaries}

    return {
        "experiment": "E01-B capacity and interference frontier",
        "conditions": len(CONDITIONS),
        "memory_arms": list(MEMORY_ARMS),
        "world_seeds": list(WORLD_SEEDS),
        "cells": expected,
        "sequences_per_cell": 160,
        "configuration_summaries": summaries,
        "interpretation_guard": (
            "One-factor synthetic frontiers with two independent world seeds. Per-world paired "
            "differences are descriptive; two worlds are insufficient for broad inferential claims. "
            "Only slow-only and finite-history arms are 16-scalar comparisons; full_soe is 64 scalars. "
            "For entities above four, random normalized codewords in fixed R^16 intentionally create "
            "codebook crowding. Interaction effects are not estimated by this one-factor design."
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
