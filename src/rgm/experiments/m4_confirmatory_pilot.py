"""Validation-only G1 software pilot for independent relational worlds.

Runs both heterogeneous typed composition and homogeneous same-bag/different-
order tasks. It reads only the validation partition; it is not the confirmatory
evaluator and cannot be used to report acceptance or select A/B.
"""
from __future__ import annotations

import json
import sys

from rgm.experiments.m4_confirmatory_worlds import (
    default_partitions, build_training_corpus, generate_order_world, generate_world,
    validate_partitions,
)
from rgm.leptograph.m4.system import M4ABSystem, M4Query


def _trained_template(architecture: str, relation_types, training_examples, min_probability, min_margin):
    model = M4ABSystem(
        architecture, relation_types, relation_capacity=8192,
        max_path_depth=4, min_probability=min_probability, min_margin=min_margin,
    )
    # The readout is fit on a corpus aggregated from disjoint train worlds.
    # Validation graph instances and their oracle labels are never supplied.
    model.fit_readout(training_examples, epochs=700, learning_rate=0.12)
    return model.snapshot()


def run_validation_pilot(
    world_count: int = 60, *, partition_name: str = "validation",
    min_probability: float = 0.75, min_margin: float = 0.25,
) -> dict:
    if world_count < 1:
        raise ValueError("world_count must be positive")
    partitions = default_partitions()
    validate_partitions(partitions)
    if partition_name != "validation":
        raise ValueError("validation pilot is sealed to the validation partition")
    selected_partition = next(p for p in partitions if p.name == partition_name)
    selected_seeds = selected_partition.seeds[:world_count]
    if len(selected_seeds) != world_count:
        raise ValueError("requested pilot exceeds validation partition size")

    generators = (
        ("heterogeneous_typed_chain", generate_world),
        ("homogeneous_order_sensitive", generate_order_world),
    )
    train_partition = next(p for p in partitions if p.name == "train")
    training_corpora = {
        mode: build_training_corpus(train_partition.seeds, generator)[0]
        for mode, generator in generators
    }
    templates = {}
    for mode, generator in generators:
        template_world = generator(10_000, 4, schema_namespace=0)
        for architecture in ("A", "B"):
            templates[(mode, architecture)] = _trained_template(
                architecture, template_world.relation_types,
                training_corpora[mode], min_probability, min_margin,
            )

    rows = []
    for seed in selected_seeds:
        depth = (2, 3, 4)[seed % 3]
        for mode, generator in generators:
            world = generator(seed, depth)
            view = world.learner_view()
            for architecture in ("A", "B"):
                model = M4ABSystem(
                    architecture, world.relation_types, relation_capacity=8192,
                    max_path_depth=4, min_probability=min_probability,
                    min_margin=min_margin,
                )
                model.restore(templates[(mode, architecture)])
                for event in sorted(view.events, key=lambda e: (e.observed_at, e.event_time, e.instance_id)):
                    model.observe(event)
                result = model.query(
                    M4Query(
                        view.start, view.goal, "ctx", world.query_time,
                        view.observation_cutoff, max_depth=depth,
                    ),
                    visible_events=view.events if architecture == "A" else (),
                )
                selected = result.get("selected_path")
                witnesses = result.get("witnesses", ())
                witness_valid = all(
                    len(w.entities) == len(w.instances) + 1
                    and w.endpoint == view.goal
                    and len({edge.instance_id for edge in w.instances}) == len(w.instances)
                    for w in witnesses
                )
                rows.append({
                    "world_seed": seed,
                    "world_id": world.world_id,
                    "partition": "validation",
                    "mode": mode,
                    "depth": depth,
                    "architecture": architecture,
                    "status": result["status"],
                    "selected_path": selected,
                    "correct": selected == world.oracle_target_path,
                    "score": result.get("score"),
                    "margin": result.get("margin"),
                    "witness_valid": witness_valid,
                })

    summaries = {}
    for architecture in ("A", "B"):
        subset = [r for r in rows if r["architecture"] == architecture]
        chosen = [r for r in subset if r["status"] == "SELECTED"]
        summaries[architecture] = {
            "worlds": len(subset),
            "selected": len(chosen),
            "abstained": len(subset) - len(chosen),
            "correct_selected": sum(r["correct"] for r in chosen),
            "invalid_witnesses": sum(not r["witness_valid"] for r in chosen),
            "by_mode": {
                mode: {
                    "worlds": sum(r["mode"] == mode for r in subset),
                    "correct_selected": sum(r["mode"] == mode and r["correct"] for r in chosen),
                    "invalid_witnesses": sum(r["mode"] == mode and not r["witness_valid"] for r in chosen),
                }
                for mode, _ in generators
            },
        }
    return {
        "classification": (
            "confirmatory_partition_execution" if partition_name == "test"
            else "validation_only_software_pilot_not_confirmatory"
        ),
        "partition": partition_name,
        "world_seeds": list(selected_seeds),
        "world_modes": [mode for mode, _ in generators],
        "training_world_count_per_mode": len(train_partition.seeds),
        "unique_training_examples_per_mode": {
            mode: len(examples) for mode, examples in training_corpora.items()
        },
        "training_signal": "aggregated in-vocabulary readout corpus from disjoint train worlds, separate by task mode",
        "training_world_count_per_mode": len(next(p for p in partitions if p.name == "train").seeds),
        "confirmatory_test_accessed": partition_name == "test",
        "thresholds": {"min_probability": min_probability, "min_margin": min_margin},
        "rows": rows,
        "summary": summaries,
        "claim_boundary": (
            "software integration and validation diagnostics only; no acceptance "
            "threshold, architecture-selection, open-world discovery or transfer claim"
        ),
    }


if __name__ == "__main__":
    payload = json.dumps(run_validation_pilot(), sort_keys=True, indent=2)
    print(payload)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as stream:
            stream.write(payload + "\n")
