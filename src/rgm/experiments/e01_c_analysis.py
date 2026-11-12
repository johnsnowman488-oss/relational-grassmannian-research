"""Aggregate paired E01-C intervention effects across world/codebook replicates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from .e01_c import CODEBOOK_SEEDS, CONDITIONS, MEMORY_ARMS, VARIANTS, WORLD_SEEDS

METRICS = {
    "composition_accuracy": ("composition", "accuracy"),
    "fact_accuracy": ("constituent_retrieval", "accuracy"),
    "true_path_detected_rate": (
        "path_diagnostics", "positive_cases_with_any_true_path_fully_retrieved"
    ),
    "best_true_path_score": ("path_diagnostics", "mean_best_true_path_score"),
    "false_path_score_positive": ("path_diagnostics", "mean_best_false_path_score_positive"),
    "false_path_score_negative": ("path_diagnostics", "mean_best_false_path_score_negative"),
    "best_path_is_true_rate": ("path_diagnostics", "positive_cases_best_path_is_true"),
    "best_true_path_rank": ("path_diagnostics", "median_best_true_path_rank"),
}


def _get(payload: dict[str, Any], variant: str, path: tuple[str, str]) -> float | None:
    value: Any = payload["variants"][variant]
    for key in path:
        value = value[key]
    return None if value is None else float(value)


def _summary(values: list[float], seed: int) -> dict[str, Any]:
    a = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    draws = rng.choice(a, size=(10000, len(a)), replace=True).mean(axis=1) if len(a) > 1 else a
    ci = np.quantile(draws, [0.025, 0.975])
    return {
        "mean": float(np.mean(a)),
        "replicate_sd": float(np.std(a, ddof=1)) if len(a) > 1 else 0.0,
        "range": [float(np.min(a)), float(np.max(a))],
        "replicate_bootstrap_95": [float(ci[0]), float(ci[1])],
        "per_replicate": [float(v) for v in a],
    }


def _delta(base: list[float], other: list[float], seed: int) -> dict[str, Any]:
    if len(base) != len(other) or not base:
        raise ValueError("paired arrays must have equal non-zero length")
    return _summary([b - a for a, b in zip(base, other)], seed)


def analyze(input_dir: Path) -> dict[str, Any]:
    files = sorted(input_dir.glob("ci-*.json"))
    expected = len(CONDITIONS) * len(MEMORY_ARMS) * len(WORLD_SEEDS) * len(CODEBOOK_SEEDS)
    if len(files) != expected:
        raise ValueError(f"expected {expected} cells, found {len(files)}")
    cells = {}
    for path in files:
        item = json.loads(path.read_text(encoding="utf-8"))
        key = (item["condition"], item["memory_arm"], int(item["world_seed"]), int(item["codebook_seed"]))
        if key in cells:
            raise ValueError(f"duplicate cell: {key}")
        if set(item["variants"]) != set(VARIANTS):
            raise ValueError(f"missing intervention in {path.name}")
        cells[key] = item
    expected_keys = {
        (c, a, w, b) for c in CONDITIONS for a in MEMORY_ARMS
        for w in WORLD_SEEDS for b in CODEBOOK_SEEDS
    }
    if set(cells) != expected_keys:
        raise ValueError("cell keys do not match frozen E01-C design")

    result, oracle_failures = {}, []
    for ci, (condition, params) in enumerate(sorted(CONDITIONS.items())):
        arms_result = {}
        for ai, arm in enumerate(MEMORY_ARMS):
            payloads = [cells[(condition, arm, w, b)]
                        for w in WORLD_SEEDS for b in CODEBOOK_SEEDS]
            variant_values, variant_result = {}, {}
            for vi, variant in enumerate(VARIANTS):
                vals = {}
                for mi, (metric, path) in enumerate(METRICS.items()):
                    values = [
                        v for payload in payloads
                        if (v := _get(payload, variant, path)) is not None
                    ]
                    vals[metric] = values
                    variant_result.setdefault(variant, {})[metric] = _summary(
                        values, 9000 + ci * 100 + ai * 10 + vi * 2 + mi
                    )
                variant_values[variant] = vals
                if variant == "oracle_facts":
                    for ix, payload in enumerate(payloads):
                        comp = payload["variants"][variant]["composition"]["accuracy"]
                        fact = payload["variants"][variant]["constituent_retrieval"]["accuracy"]
                        if abs(comp - 1.0) > 1e-12 or abs(fact - 1.0) > 1e-12:
                            oracle_failures.append(f"{condition}/{arm}/{ix}: comp={comp}, fact={fact}")
            diagnosis_totals = {}
            for variant in VARIANTS:
                labels = {label for payload in payloads
                          for label in payload["variants"][variant]["diagnosis_counts"]}
                diagnosis_totals[variant] = {
                    label: int(sum(payload["variants"][variant]["diagnosis_counts"].get(label, 0)
                                   for payload in payloads))
                    for label in sorted(labels)
                }
            intervention_deltas = {}
            for vi, variant in enumerate(("repeat_suppressed", "oracle_facts")):
                name = f"{variant}_minus_observed"
                intervention_deltas[name] = {
                    metric: _delta(
                        variant_values["observed"][metric], variant_values[variant][metric],
                        12000 + ci * 100 + ai * 10 + mi,
                    )
                    for mi, metric in enumerate(METRICS)
                }
            arms_result[arm] = {
                "variants": variant_result,
                "diagnosis_counts_across_replicates": diagnosis_totals,
                "paired_intervention_differences": intervention_deltas,
                "replicate_ids": [
                    {"world_seed": p["world_seed"], "codebook_seed": p["codebook_seed"]}
                    for p in payloads
                ],
            }

        memory_delta = {}
        for mi, (metric, path) in enumerate(METRICS.items()):
            history = [_get(cells[(condition, "full_history", w, b)], "observed", path)
                       for w in WORLD_SEEDS for b in CODEBOOK_SEEDS]
            slow = [_get(cells[(condition, "slow_only", w, b)], "observed", path)
                    for w in WORLD_SEEDS for b in CODEBOOK_SEEDS]
            memory_delta[metric] = _delta(
                [float(x) for x in history if x is not None],
                [float(x) for x in slow if x is not None],
                14000 + ci * 100 + mi,
            )
        result[condition] = {
            "parameters": params, "memory_arms": arms_result,
            "slow_only_minus_full_history_observed": memory_delta,
        }
    if oracle_failures:
        raise ValueError("oracle exact-label gate failed:\n" + "\n".join(oracle_failures))
    return {
        "experiment": "E01-C mechanism isolation",
        "conditions": len(CONDITIONS), "memory_arms": list(MEMORY_ARMS),
        "interventions": list(VARIANTS), "world_seeds": list(WORLD_SEEDS),
        "codebook_seeds": list(CODEBOOK_SEEDS),
        "replicates_per_condition_arm": len(WORLD_SEEDS) * len(CODEBOOK_SEEDS),
        "cells": expected, "sequences_per_cell": 160,
        "condition_summaries": result,
        "oracle_gate": "passed: exact facts recover all generated labels",
        "interpretation_guide": {
            "repeat_suppression_gain": "Duplicate-pulse accumulation contributes to memory interference.",
            "oracle_gain_without_repeat_gain": "Event encoding, memory support or readout is limiting.",
            "high_false_path_support": "Candidate-path competition or false-positive composition is limiting.",
            "slow_vs_history_difference": "Temporal update or decay contributes; this is not geometric evidence.",
        },
        "interpretation_guard": (
            "Synthetic evidence only. Nine paired world/codebook replicates per condition/arm. "
            "Oracle facts are an upper-bound diagnostic, not a deployable model. E01-C does not "
            "test Grassmannian geometry or establish real-world generalisation."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = analyze(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
