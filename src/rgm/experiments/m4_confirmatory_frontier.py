"""Validation-only memory-budgeted A/B retention frontier.

The frontier uses held-out validation worlds only. B's persistent store is
capacity-limited under a common serialized-snapshot upper-bound budget. A's
external evidence-window replay is reported separately and is not charged to
persistent memory.
"""
from __future__ import annotations

import json
import pickle
import random
import statistics
import sys
import time

from rgm.experiments.m4_confirmatory_worlds import (
    build_training_corpus, default_partitions, generate_world, validate_partitions,
)
from rgm.leptograph.m4.composition import Entity, RelationInstance
from rgm.leptograph.m4.system import M4ABSystem, M4Query


def _percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction)))
    return float(ordered[index])


def _frontier_world(seed: int, count: int = 1000):
    world = generate_world(seed, 4)
    relation_by_name = {r.name: r for r in world.relation_types}
    rng = random.Random(seed ^ 0x71A4)
    positions = list(range(1, count + 1))
    rng.shuffle(positions)
    target_positions = sorted(positions[:4])

    target_events = []
    current = world.start
    for index, relation_name in enumerate(world.oracle_target_path):
        relation = relation_by_name[relation_name]
        next_entity = (
            world.goal if index == 3
            else Entity(f"frontier-{seed}-target-node-{index}", relation.codomain)
        )
        target_events.append(RelationInstance(
            f"frontier-{seed}-target-edge-{index}", relation,
            current, next_entity, float(index + 1), float(target_positions[index]),
            "ctx", provenance=f"frontier-world:{seed}",
        ))
        current = next_entity

    background = []
    relation_types = list(world.relation_types)
    for index, observed_at in enumerate(positions[4:]):
        relation = relation_types[rng.randrange(len(relation_types))]
        background.append(RelationInstance(
            f"frontier-{seed}-background-{index}", relation,
            Entity(f"frontier-{seed}-bg-s-{index}", relation.domain),
            Entity(f"frontier-{seed}-bg-o-{index}", relation.codomain),
            float(observed_at), float(observed_at), "ctx",
            provenance=f"frontier-world:{seed}",
        ))
    events = tuple(sorted(
        target_events + background,
        key=lambda event: (event.observed_at, event.instance_id),
    ))
    return world, events, float(count), float(count + 2000)


def _template(architecture, relation_types, train_examples, capacity, min_probability, min_margin):
    model = M4ABSystem(
        architecture, relation_types, relation_capacity=capacity,
        max_path_depth=4, min_probability=min_probability, min_margin=min_margin,
    )
    model.fit_readout(train_examples, epochs=700, learning_rate=0.12)
    return model.snapshot()


def _query_metrics(model, query, events, architecture, replay=False):
    start = time.perf_counter_ns()
    result = model.query(
        query,
        visible_events=events if architecture == "A" and replay else (),
    )
    elapsed = time.perf_counter_ns() - start
    return result, elapsed


def run_validation_frontier(
    world_count: int = 30,
    capacities=(10, 25, 50, 100, 250, 500, 750, 800, 850, 900, 950, 1000),
    *, partition_name: str = "validation", min_probability: float = 0.75,
    min_margin: float = 0.25, confirmatory_authorized: bool = False,
) -> dict:
    if partition_name == "test" and not confirmatory_authorized:
        raise ValueError("test-partition frontier requires the frozen confirmatory campaign runner")
    if partition_name not in {"validation", "test"}:
        raise ValueError("partition_name must be validation or test")
    if world_count < 1 or not capacities or any(int(cap) < 1 for cap in capacities):
        raise ValueError("invalid validation frontier configuration")
    partitions = default_partitions()
    validate_partitions(partitions)
    train = next(part for part in partitions if part.name == "train")
    selected_partition = next(part for part in partitions if part.name == partition_name)
    # Validation uses its held-out half; confirmatory evaluation uses the sealed test partition.
    seed_source = (
        selected_partition.seeds[len(selected_partition.seeds) // 2:]
        if partition_name == "validation" else selected_partition.seeds
    )
    seeds = tuple(seed_source[:world_count])
    if len(seeds) != world_count:
        raise ValueError("requested frontier exceeds held-out validation worlds")

    train_examples, train_world_ids, train_digest = build_training_corpus(
        train.seeds, generate_world
    )
    first_world = generate_world(seeds[0], 4)
    a_template = _template("A", first_world.relation_types, train_examples, 1001, min_probability, min_margin)
    b_templates = {
        int(cap): _template("B", first_world.relation_types, train_examples, int(cap), min_probability, min_margin)
        for cap in capacities
    }

    a_no_replay = []
    a_replay = []
    a_snapshot_sizes = []
    a_query_latencies = []
    b_rows = []
    for seed in seeds:
        world, events, cutoff, query_time = _frontier_world(seed)
        query = M4Query(
            world.start, world.goal, "ctx", query_time, cutoff, max_depth=4,
        )

        model_a = M4ABSystem(
            "A", world.relation_types, relation_capacity=1001,
            max_path_depth=4, min_probability=min_probability, min_margin=min_margin,
        )
        model_a.restore(a_template)
        for event in events:
            model_a.observe(event)
        model_a.advance_gap(8.0)
        a_snapshot_sizes.append(len(pickle.dumps(model_a.snapshot(), protocol=5)))
        no_replay, no_replay_ns = _query_metrics(
            model_a, query, events, "A", replay=False
        )
        replayed, replay_ns = _query_metrics(
            model_a, query, events, "A", replay=True
        )
        a_no_replay.append({
            "seed": seed, "status": no_replay["status"],
            "correct": no_replay.get("selected_path") == world.oracle_target_path,
        })
        a_replay.append({
            "seed": seed, "status": replayed["status"],
            "correct": replayed.get("selected_path") == world.oracle_target_path,
        })
        a_query_latencies.append({"no_replay": no_replay_ns, "replay": replay_ns})

        for capacity in capacities:
            capacity = int(capacity)
            model_b = M4ABSystem(
                "B", world.relation_types, relation_capacity=capacity,
                max_path_depth=4, min_probability=min_probability, min_margin=min_margin,
            )
            model_b.restore(b_templates[capacity])
            for event in events:
                model_b.observe(event)
            model_b.advance_gap(8.0)
            snapshot_bytes = len(pickle.dumps(model_b.snapshot(), protocol=5))
            resource = model_b.resource_snapshot()
            result, query_ns = _query_metrics(
                model_b, query, events, "B", replay=False
            )
            b_rows.append({
                "seed": seed, "capacity": capacity,
                "status": result["status"],
                "selected_path": result.get("selected_path"),
                "correct": result.get("selected_path") == world.oracle_target_path,
                "stored_instances": resource["relation_instance_count"],
                "relation_payload_bytes": resource["relation_payload_bytes"],
                "serialized_snapshot_bytes": snapshot_bytes,
                "query_latency_ns": query_ns,
            })

    frontier = []
    a_snapshot_p95 = _percentile(a_snapshot_sizes, 0.95)
    for capacity in capacities:
        rows = [row for row in b_rows if row["capacity"] == int(capacity)]
        budget = _percentile([row["serialized_snapshot_bytes"] for row in rows], 0.95)
        frontier.append({
            "capacity": int(capacity),
            "memory_budget_bytes": budget,
            "A_actual_snapshot_p95_bytes": a_snapshot_p95,
            "A_within_same_upper_bound_budget": a_snapshot_p95 <= budget,
            "B_actual_snapshot_p50_bytes": _percentile(
                [row["serialized_snapshot_bytes"] for row in rows], 0.50
            ),
            "B_actual_snapshot_p95_bytes": budget,
            "B_relation_payload_p50_bytes": _percentile(
                [row["relation_payload_bytes"] for row in rows], 0.50
            ),
            "B_stored_instances_p50": _percentile(
                [row["stored_instances"] for row in rows], 0.50
            ),
            "B_correct_retention": sum(row["correct"] for row in rows),
            "B_world_count": len(rows),
            "B_false_selections": sum(
                row["status"] == "SELECTED" and not row["correct"] for row in rows
            ),
            "B_query_latency_ns_p50": _percentile(
                [row["query_latency_ns"] for row in rows], 0.50
            ),
            "B_query_latency_ns_p95": _percentile(
                [row["query_latency_ns"] for row in rows], 0.95
            ),
        })

    return {
        "classification": (
            "confirmatory_partition_execution" if partition_name == "test"
            else "validation_only_memory_budgeted_frontier_not_confirmatory"
        ),
        "partition": "test" if partition_name == "test" else "validation_heldout_half",
        "world_seeds": list(seeds),
        "confirmatory_test_accessed": partition_name == "test",
        "training_world_count": len(train_world_ids),
        "training_corpus_sha256": train_digest,
        "threshold_candidate": {"min_probability": min_probability, "min_margin": min_margin},
        "memory_budget_definition": (
            "Common upper bound on serialized persistent snapshot bytes. A's unused "
            "budget is reported as slack; A's external replay batch is excluded and "
            "reported as a separate non-persistent-evidence baseline."
        ),
        "A_no_replay": {
            "selected": sum(row["status"] == "SELECTED" for row in a_no_replay),
            "correct": sum(row["correct"] for row in a_no_replay),
            "abstained": sum(str(row["status"]).startswith("ABSTAIN") for row in a_no_replay),
            "snapshot_p95_bytes": a_snapshot_p95,
            "query_p50_ns": _percentile(
                [row["no_replay"] for row in a_query_latencies], 0.50
            ),
            "query_p95_ns": _percentile(
                [row["no_replay"] for row in a_query_latencies], 0.95
            ),
        },
        "A_with_external_replay": {
            "selected": sum(row["status"] == "SELECTED" for row in a_replay),
            "correct": sum(row["correct"] for row in a_replay),
            "world_count": len(a_replay),
            "query_p50_ns": _percentile(
                [row["replay"] for row in a_query_latencies], 0.50
            ),
            "query_p95_ns": _percentile(
                [row["replay"] for row in a_query_latencies], 0.95
            ),
            "accounting_note": "External evidence window is not charged to persistent snapshot budget.",
        },
        "frontier": frontier,
        "rows": b_rows,
        "claim_boundary": (
            "Confirmatory budget-capped persistence frontier under frozen thresholds; "
            "not equal-byte consumption and not a universal architecture ranking."
            if partition_name == "test" else
            "Validation-only budget-capped persistence frontier. It is not equal-byte "
            "memory consumption and does not establish a universal architecture winner."
        ),
    }


if __name__ == "__main__":
    payload = json.dumps(run_validation_frontier(), sort_keys=True, indent=2)
    print(payload)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as stream:
            stream.write(payload + "\n")
