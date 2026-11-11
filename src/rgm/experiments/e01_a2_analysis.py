"""Paired analysis of the E01-A2 per-cell artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binomtest


def _paired_metrics(base: dict[int, dict[str, Any]],
                    other: dict[int, dict[str, Any]],
                    seed: int) -> dict[str, Any]:
    common = sorted(set(base) & set(other))
    if not common:
        raise ValueError("no overlapping test sequence IDs")
    a = np.asarray([base[k]["composition_prediction"] == base[k]["label"] for k in common], dtype=float)
    b = np.asarray([other[k]["composition_prediction"] == other[k]["label"] for k in common], dtype=float)
    delta = b - a
    base_correct, other_correct = a.astype(bool), b.astype(bool)
    b_to_a = int(np.sum(base_correct & ~other_correct))
    a_to_b = int(np.sum(~base_correct & other_correct))
    discordant = b_to_a + a_to_b
    p_value = float(binomtest(a_to_b, discordant, 0.5, alternative="two-sided").pvalue) if discordant else 1.0
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(delta), size=(5000, len(delta)))
    boot = np.mean(delta[draws], axis=1)
    return {
        "n_paired_sequences": len(common),
        "baseline_accuracy": float(np.mean(a)),
        "comparison_accuracy": float(np.mean(b)),
        "accuracy_difference_comparison_minus_baseline": float(np.mean(delta)),
        "paired_bootstrap_95": [float(x) for x in np.quantile(boot, [0.025, 0.975])],
        "mcnemar": {
            "baseline_correct_comparison_wrong": b_to_a,
            "baseline_wrong_comparison_correct": a_to_b,
            "discordant_pairs": discordant,
            "exact_two_sided_p": p_value,
        },
    }


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload


def analyze(input_dir: Path) -> dict[str, Any]:
    files = sorted(input_dir.glob("ci-*.json"))
    if len(files) != 27:
        raise ValueError(f"expected 27 E01-A2 cell artifacts, found {len(files)}")
    cells = {}
    for path in files:
        payload = _load(path)
        key = f'{payload["memory_config"]}/{payload["readout"]}'
        if key in cells:
            raise ValueError(f"duplicate cell artifact: {key}")
        cells[key] = payload
    baseline_key = "full/max_channel"
    if baseline_key not in cells:
        raise ValueError(f"missing baseline cell: {baseline_key}")
    baseline = {
        row["seed"]: row for row in cells[baseline_key]["per_sequence"]
    }
    comparisons = {}
    for key, payload in sorted(cells.items()):
        if key == baseline_key:
            continue
        current = {row["seed"]: row for row in payload["per_sequence"]}
        comparisons[key] = _paired_metrics(baseline, current, seed=41000 + len(comparisons))
    return {
        "experiment": "E01-A2 paired comparison",
        "baseline": baseline_key,
        "cells": len(cells),
        "comparisons": comparisons,
        "interpretation_guard": (
            "Exploratory paired comparisons within one synthetic generator and fixed codebook. "
            "P-values do not establish broad generalisation; readout and channel cells are "
            "not all independent hypotheses. Treat effect sizes and intervals as primary."
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
