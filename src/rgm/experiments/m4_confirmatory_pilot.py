"""Validation-only G1 software pilot for the independent-world generator.

This runner intentionally reads only the validation partition. It is not the
confirmatory evaluator and must not be used to report acceptance or select A/B.
"""
from __future__ import annotations

import json
import sys

from rgm.experiments.m4_confirmatory_worlds import (
    default_partitions, generate_world, validate_partitions,
)
from rgm.leptograph.m4.system import M4ABSystem, M4Query


def _trained_template(architecture: str, relation_types):
    model = M4ABSystem(
        architecture, relation_types, relation_capacity=8192,
        max_path_depth=4, min_probability=0.5, min_margin=0.05,
    )
    # The task grammar is the training signal. Held-out validation graph
    # instances are never used to fit the readout.
    examples = []
    for depth in (2, 3, 4):
        examples.append(__import__(
            "rgm.leptograph.m4.system", fromlist=["PathTrainingExample"]
        ).PathTrainingExample(tuple(f"a{i}" for i in range(depth)), 1))
        examples.append(__import__(
            "rgm.leptograph.m4.system", fromlist=["PathTrainingExample"]
        ).PathTrainingExample(tuple(f"b{i}" for i in range(depth)), 0))
    model.fit_readout(examples, epochs=700, learning_rate=0.12)
    return model.snapshot()


def run_validation_pilot(world_count: int = 12) -> dict:
    if world_count < 1:
        raise ValueError("world_count must be positive")
    partitions = default_partitions()
    validate_partitions(partitions)
    validation = next(p for p in partitions if p.name == "validation")
    selected_seeds = validation.seeds[:world_count]
    if len(selected_seeds) != world_count:
        raise ValueError("requested pilot exceeds validation partition size")

    # Train once per architecture using the fixed in-vocabulary task grammar.
    # All validation worlds remain unseen during fitting.
    template_world = generate_world(10_000, 4, schema_namespace=0)
    templates = {
        arch: _trained_template(arch, template_world.relation_types)
        for arch in ("A", "B")
    }
    rows = []
    for seed in selected_seeds:
        depth = (2, 3, 4)[seed % 3]
        world = generate_world(seed, depth)
        view = world.learner_view()
        for architecture in ("A", "B"):
            model = M4ABSystem(
                architecture, world.relation_types, relation_capacity=8192,
                max_path_depth=4, min_probability=0.5, min_margin=0.05,
            )
            model.restore(templates[architecture])
            for event in view.events:
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
        }
    return {
        "classification": "validation_only_software_pilot_not_confirmatory",
        "partition": "validation",
        "world_seeds": list(selected_seeds),
        "training_signal": "fixed in-vocabulary relation-sequence task grammar",
        "confirmatory_test_accessed": False,
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
