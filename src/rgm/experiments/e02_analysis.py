"""Aggregate E02-B and E02-C CI cell artifacts into one evidence report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

EXPECTED_CELLS = 54
EXPECTED_CONDITIONS = {
    "baseline_e4", "repeat_e4", "candidate_e16",
    "factload_e16", "depth3_e16", "longgap_e16",
}
EXPECTED_WORLDS = {501, 502, 503}
EXPECTED_CODEBOOKS = {9137, 27183, 65537}
ARCHITECTURE_ORDER_B = ("graph", "memory_slow_only", "memory_full_history")
ARCHITECTURE_ORDER_C = (
    "graph", "memory_slow_only", "memory_full_history",
    "hybrid_slow_only", "hybrid_full_history",
)


def _load_cells(directory: Path, prefix: str, stage: str) -> list[dict[str, Any]]:
    files = sorted(directory.glob(f"{prefix}*.json"))
    cells = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("stage") == stage:
            cells.append(payload)
    if len(cells) != EXPECTED_CELLS:
        raise ValueError(
            f"{stage}: expected {EXPECTED_CELLS} condition/world/codebook cells, found {len(cells)}"
        )
    keys = {(x["condition"], x["world_seed"], x["codebook_seed"]) for x in cells}
    expected = {
        (condition, world, codebook)
        for condition in EXPECTED_CONDITIONS
        for world in EXPECTED_WORLDS
        for codebook in EXPECTED_CODEBOOKS
    }
    if keys != expected:
        missing, extra = sorted(expected - keys), sorted(keys - expected)
        raise ValueError(f"{stage}: seed manifest mismatch; missing={missing}, extra={extra}")
    return cells


def _stats(values: list[float]) -> dict[str, float | int]:
    return {
        "n_cells": len(values),
        "mean": float(mean(values)) if values else 0.0,
        "sd_across_cells": float(pstdev(values)) if len(values) > 1 else 0.0,
        "min": float(min(values)) if values else 0.0,
        "max": float(max(values)) if values else 0.0,
    }



METRIC_FIELDS = (
    "accuracy", "balanced_accuracy", "precision", "recall",
    "false_positive_rate", "false_negative_rate",
)
COST_FIELDS = (
    "mean_model_state_bytes", "mean_common_input_bytes",
    "mean_query_edge_evaluations", "mean_observed_event_count",
    "mean_unique_observed_edges",
)


def _aggregate_architecture(
    selected: list[dict[str, Any]], architecture: str, *, profile: str | None = None,
) -> dict[str, Any]:
    def artifact_values(section: dict[str, Any]) -> dict[str, Any]:
        return section["architectures"][architecture] if profile is None else section["profiles"][profile]["architectures"][architecture]

    return {
        "metrics": {
            metric: _stats([float(artifact_values(x)["metrics"][metric]) for x in selected])
            for metric in METRIC_FIELDS
        },
        "cost": {
            metric: _stats([float(artifact_values(x)["cost"][metric]) for x in selected])
            for metric in COST_FIELDS
        },
    }


def _aggregate_b(cells: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for condition in sorted({x["condition"] for x in cells}):
        result[condition] = {}
        selected = [x for x in cells if x["condition"] == condition]
        for architecture in ARCHITECTURE_ORDER_B:
            result[condition][architecture] = _aggregate_architecture(selected, architecture)
        result[condition]["paired_accuracy_difference_graph_minus_slow_only"] = _stats([
            float(x["architectures"]["graph"]["metrics"]["accuracy"])
            - float(x["architectures"]["memory_slow_only"]["metrics"]["accuracy"])
            for x in selected
        ])
    return result


def _aggregate_c(cells: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for condition in sorted({x["condition"] for x in cells}):
        result[condition] = {}
        selected = [x for x in cells if x["condition"] == condition]
        profiles = sorted({p for x in selected for p in x["profiles"]})
        for profile in profiles:
            result[condition][profile] = {}
            for architecture in ARCHITECTURE_ORDER_C:
                result[condition][profile][architecture] = _aggregate_architecture(
                    selected, architecture, profile=profile,
                )
            for hybrid in ("hybrid_slow_only", "hybrid_full_history"):
                result[condition][profile][f"paired_accuracy_difference_{hybrid}_minus_graph"] = _stats([
                    float(x["profiles"][profile]["architectures"][hybrid]["metrics"]["accuracy"])
                    - float(x["profiles"][profile]["architectures"]["graph"]["metrics"]["accuracy"])
                    for x in selected
                ])
    return result


def _table_b(summary: dict[str, Any]) -> str:
    lines = [
        "| Condition | Graph accuracy | Slow-only memory | Full-history memory | Graph − slow-only (pp) |",
        "|---|---:|---:|---:|---:|",
    ]
    for condition, values in summary.items():
        diff = values["paired_accuracy_difference_graph_minus_slow_only"]["mean"] * 100
        lines.append(
            f"| {condition} | {values['graph']['metrics']['accuracy']['mean']:.3f} | "
            f"{values['memory_slow_only']['metrics']['accuracy']['mean']:.3f} | "
            f"{values['memory_full_history']['metrics']['accuracy']['mean']:.3f} | {diff:+.2f} |"
        )
    return "\n".join(lines)


def _table_b_costs(summary: dict[str, Any]) -> str:
    lines = [
        "| Condition | Common input (B) | Graph state (B) | Slow-only state (B) | Full-history state (B) | Graph query edge checks | Dense path-edge evaluations |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition, values in summary.items():
        graph = values["graph"]["cost"]
        slow = values["memory_slow_only"]["cost"]
        full = values["memory_full_history"]["cost"]
        lines.append(
            f"| {condition} | {graph['mean_common_input_bytes']['mean']:.1f} | "
            f"{graph['mean_model_state_bytes']['mean']:.1f} | "
            f"{slow['mean_model_state_bytes']['mean']:.1f} | "
            f"{full['mean_model_state_bytes']['mean']:.1f} | "
            f"{graph['mean_query_edge_evaluations']['mean']:.1f} | "
            f"{slow['mean_query_edge_evaluations']['mean']:.1f} |"
        )
    return "\n".join(lines)


def _table_c(summary: dict[str, Any]) -> str:
    lines = [
        "| Condition | Corruption | Graph | Memory (slow) | Memory (full) | Hybrid (slow) | Hybrid (full) | Hybrid slow − graph (pp) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition, profiles in summary.items():
        for profile, values in profiles.items():
            diff = values["paired_accuracy_difference_hybrid_slow_only_minus_graph"]["mean"] * 100
            lines.append(
                f"| {condition} | {profile} | "
                f"{values['graph']['metrics']['accuracy']['mean']:.3f} | "
                f"{values['memory_slow_only']['metrics']['accuracy']['mean']:.3f} | "
                f"{values['memory_full_history']['metrics']['accuracy']['mean']:.3f} | "
                f"{values['hybrid_slow_only']['metrics']['accuracy']['mean']:.3f} | "
                f"{values['hybrid_full_history']['metrics']['accuracy']['mean']:.3f} | "
                f"{diff:+.2f} |"
            )
    return "\n".join(lines)


def _table_c_costs(summary: dict[str, Any]) -> str:
    lines = [
        "| Condition | Corruption | Graph state (B) | Memory slow (B) | Hybrid slow (B) | Graph edge checks | Hybrid path-edge evaluations |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for condition, profiles in summary.items():
        for profile, values in profiles.items():
            graph = values["graph"]["cost"]
            slow = values["memory_slow_only"]["cost"]
            hybrid = values["hybrid_slow_only"]["cost"]
            lines.append(
                f"| {condition} | {profile} | "
                f"{graph['mean_model_state_bytes']['mean']:.1f} | "
                f"{slow['mean_model_state_bytes']['mean']:.1f} | "
                f"{hybrid['mean_model_state_bytes']['mean']:.1f} | "
                f"{graph['mean_query_edge_evaluations']['mean']:.1f} | "
                f"{hybrid['mean_query_edge_evaluations']['mean']:.1f} |"
            )
    return "\n".join(lines)


def build_report(b_directory: Path, c_directory: Path, output_directory: Path) -> dict[str, Any]:
    b_cells = _load_cells(b_directory, "e02-b-", "E02-B")
    c_cells = _load_cells(c_directory, "e02-c-", "E02-C")
    b_summary = _aggregate_b(b_cells)
    c_summary = _aggregate_c(c_cells)
    payload = {
        "experiment": "E02-v0.1",
        "status": "complete",
        "cell_counts": {"E02-B": len(b_cells), "E02-C": len(c_cells)},
        "conditions": sorted(b_summary),
        "world_seeds": [501, 502, 503],
        "codebook_seeds": [9137, 27183, 65537],
        "sequences_per_validation_and_test_split_per_cell": 160,
        "E02_B": b_summary,
        "E02_C": c_summary,
        "interpretation_guard": (
            "All cells use synthetic E01-C generator conditions. The graph is built only from observed event "
            "records. Test labels, latent facts, planted paths and corruption masks are evaluator-only. Explicit "
            "graph storage is not capacity-equivalent to a 16-scalar memory trace. E02 does not test Grassmannian geometry."
        ),
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "e02_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = "\n".join([
        "# E02 — Event-derived graph and temporal-memory evaluation",
        "",
        "## Execution",
        "",
        f"- E02-B cells: **{len(b_cells)}/{EXPECTED_CELLS}**",
        f"- E02-C cells: **{len(c_cells)}/{EXPECTED_CELLS}**",
        "- Per cell: 160 validation and 160 held-out test sequences.",
        "- Paired worlds: 501, 502, 503; codebooks: 9137, 27183, 65537.",
        "",
        "## E02-B — Clean graph versus dense memory",
        "",
        _table_b(b_summary),
        "",
        "### E02-B storage and query costs",
        "",
        _table_b_costs(b_summary),
        "",
        "## E02-C — Graph, memory and hybrid under event corruption",
        "",
        _table_c(c_summary),
        "",
        "### E02-C storage and query costs",
        "",
        _table_c_costs(c_summary),
        "",
        "## Reading the results",
        "",
        "Accuracy is averaged over nine world/codebook cells for each condition. The paired difference is computed within each cell before aggregation. The cell-level standard deviation is descriptive, not a population-level confidence interval.",
        "",
        "The graph stores explicit observed edges and occurrence timestamps. Its storage is not matched to the 16-scalar memory baseline; compare the separate storage and query-operation fields in the cell artifacts. Query operation counts are deterministic proxies, not wall-clock performance.",
        "",
        "E02-C uses four paired observation profiles: clean, 10% missing unique edges, 10% spurious unique edges, and both interventions together. Percentages are rounded to integer edge counts per case. Corruption masks are produced by the evaluator and are not exposed to the model.",
        "",
        "## Scientific limits",
        "",
        "These experiments use the controlled E01-C synthetic generator, not external relational data. The graph receives complete event observations in E02-B, so a strong graph result demonstrates exact retrieval from explicit observed edges under this task; it does not establish relation discovery or general reasoning. Hybrid gains or losses are specific to this temporal fallback, encoder, graph representation, and corruption protocol. No result here establishes a Grassmannian advantage.",
        "",
    ])
    (output_directory / "report.md").write_text(report, encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--b-input-dir", type=Path, required=True)
    parser.add_argument("--c-input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build_report(args.b_input_dir, args.c_input_dir, args.output_dir)
    print(json.dumps({
        "status": result["status"], "cell_counts": result["cell_counts"],
        "output_dir": str(args.output_dir),
    }, indent=2))


if __name__ == "__main__":
    main()
