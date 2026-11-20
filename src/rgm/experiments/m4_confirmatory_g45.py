"""Validation-only G4/G5 diagnostics for HLG-M4.

G4 exercises repeated adaptive lifecycle trials on validation worlds. G5 records
native architecture resource/latency measurements. Neither freezes acceptance
gates or accesses the confirmatory-test partition.
"""
from __future__ import annotations

import json
import math
import pickle
import platform
import statistics
import sys
import time
import tracemalloc

import numpy as np

from rgm.experiments.m4_confirmatory_worlds import (
    default_partitions, build_training_corpus, generate_order_world,
    generate_world, validate_partitions,
)
from rgm.leptograph.m4.adaptive import M4AdaptiveController
from rgm.leptograph.m4.composition import Entity, RelationInstance
from rgm.leptograph.m4.system import M4ABSystem, M4Query, PathTrainingExample


def _bce(model, examples):
    losses = []
    for example in examples:
        x = model._features(example.relation_path)
        z = float(np.clip(x @ model.readout_weights + model.readout_bias, -30.0, 30.0))
        p = 1.0 / (1.0 + math.exp(-z))
        losses.append(-(example.label * math.log(max(p, 1e-12))
                       + (1 - example.label) * math.log(max(1 - p, 1e-12))))
    return float(np.mean(losses))


def _system_equal_to_snapshot(model, snapshot):
    current = model.snapshot()
    numeric = (
        np.array_equal(current["readout_weights"], snapshot["readout_weights"])
        and np.array_equal(current["soe"]["channels"], snapshot["soe"]["channels"])
        and np.array_equal(current["soe"]["decay_rates"], snapshot["soe"]["decay_rates"])
        and np.array_equal(current["soe"]["injection_matrices"], snapshot["soe"]["injection_matrices"])
    )
    store = (
        current["store"] is None if snapshot["store"] is None
        else current["store"]["records"] == snapshot["store"]["records"]
    )
    scalar_keys = (
        "readout_bias", "readout_fitted", "observation_count", "last_observed_at",
        "last_capacity_status", "update_operations", "query_operations",
    )
    return bool(numeric and store and all(current[k] == snapshot[k] for k in scalar_keys))


def _g4_trials(world_count: int):
    partitions = default_partitions()
    selected_partition = next(p for p in partitions if p.name == partition_name)
    train = next(p for p in partitions if p.name == "train")
    seeds = selected_partition.seeds[:world_count]
    rows = []
    generators = (generate_world, generate_order_world)
    corpora = {
        generator: build_training_corpus(train.seeds, generator)
        for generator in generators
    }
    templates = {}
    for generator in generators:
        train_examples, train_world_ids, train_digest = corpora[generator]
        inverse_examples = tuple(
            PathTrainingExample(example.relation_path, 1 - example.label)
            for example in train_examples
        )
        template_world = generator(train.seeds[0], 4)
        for architecture in ("A", "B"):
            incumbent_template = M4ABSystem(
                architecture, template_world.relation_types, relation_capacity=8192,
                max_path_depth=4, min_probability=min_probability, min_margin=min_margin,
            )
            incumbent_template.fit_readout(
                inverse_examples, epochs=700, learning_rate=0.12
            )
            candidate_template = M4ABSystem(
                architecture, template_world.relation_types, relation_capacity=8192,
                max_path_depth=4, min_probability=0.5, min_margin=0.05,
            )
            candidate_template.fit_readout(
                train_examples, epochs=900, learning_rate=0.12
            )
            templates[(generator, architecture)] = {
                "incumbent_snapshot": incumbent_template.snapshot(),
                "candidate_weights": candidate_template.readout_weights.copy(),
                "candidate_bias": candidate_template.readout_bias,
                "training_world_count": len(train_world_ids),
                "training_corpus_sha256": train_digest,
                "unique_training_example_count": len(train_examples),
            }

    for trial_index, seed in enumerate(seeds):
        depth = (2, 3, 4)[seed % 3]
        for generator in generators:
            world = generator(seed, depth)
            for architecture in ("A", "B"):
                template = templates[(generator, architecture)]
                model = M4ABSystem(
                    architecture, world.relation_types, relation_capacity=8192,
                    max_path_depth=4, min_probability=0.5, min_margin=0.05,
                )
                # Incumbent/candidate are fitted on the train partition only;
                # each trial evaluates them on a separate validation world.
                model.restore(template["incumbent_snapshot"])
                for event in sorted(world.events, key=lambda e: (e.observed_at, e.event_time, e.instance_id)):
                    model.observe(event)
                controller = M4AdaptiveController(model)
                stable_alarms = sum(
                    controller.observe_residual(0.05) for _ in range(100)
                )
                transient_alarms = sum(
                    controller.observe_residual(3.0) for _ in range(3)
                )
                post_transient_recovery_alarms = sum(
                    controller.observe_residual(0.05) for _ in range(60)
                )
                post_transient_statistic = float(controller.detector.statistic)
                detection_delay = None
                for step in range(1, 31):
                    if controller.observe_residual(3.0):
                        detection_delay = step
                        break

                validation_examples = (
                    PathTrainingExample(world.oracle_target_path, 1),
                    PathTrainingExample(world.oracle_decoy_paths[0], 0),
                )
                incumbent_loss = _bce(model, validation_examples)
                candidate_eval = M4ABSystem(
                    architecture, world.relation_types, relation_capacity=8192,
                    max_path_depth=4, min_probability=0.5, min_margin=0.05,
                )
                candidate_eval.restore(model.snapshot())
                candidate_eval.readout_weights = template["candidate_weights"].copy()
                candidate_eval.readout_bias = template["candidate_bias"]
                candidate_loss = _bce(candidate_eval, validation_examples)

                controller.start_candidate(template["candidate_weights"], template["candidate_bias"])
                promoted = controller.validate_candidate(
                    incumbent_loss, candidate_loss, identifiable=True
                )
                trusted = controller.trusted_snapshot["system"]
                rollback_exact = False
                if promoted:
                    model.advance_gap(2.0)
                    source = world.events[0]
                    mutated = RelationInstance(
                        f"{world.world_id}-post-promotion-mutation",
                        source.relation_type, source.subject, source.object,
                        source.event_time + 10.0, source.observed_at + 10.0,
                        source.context, source.valid_until, source.provenance,
                    )
                    model.observe(mutated)
                    controller.rollback()
                    rollback_exact = _system_equal_to_snapshot(model, trusted)
                    detector_exact = controller.detector.__dict__ == controller.trusted_snapshot["detector"]
                else:
                    detector_exact = False

                # Independent rejection and dormancy/recovery controls.
                reject_model = M4ABSystem(
                    architecture, world.relation_types, relation_capacity=8192,
                    max_path_depth=4,
                )
                reject_model.restore(model.snapshot())
                reject_controller = M4AdaptiveController(reject_model)
                before_reject = reject_model.snapshot()
                reject_controller.start_candidate(reject_model.readout_weights + 0.01)
                rejected = not reject_controller.validate_candidate(1.0, 2.0, True)
                rejection_unchanged = _system_equal_to_snapshot(reject_model, before_reject)
                recovery = M4AdaptiveController(reject_model)
                recovery.enter_dormancy()
                recovery.reactivate()
                recovery.finish_recovery()

                rows.append({
                    "seed": seed, "world_id": world.world_id, "mode": world.mode,
                    "training_world_count": template["training_world_count"],
                        "training_corpus_sha256": template["training_corpus_sha256"],
                    "architecture": architecture,
                    "stable_control_alarms": int(stable_alarms),
                    "transient_disturbance_alarms": int(transient_alarms),
                    "post_transient_recovery_alarms": int(post_transient_recovery_alarms),
                    "post_transient_statistic": post_transient_statistic,
                    "drift_detection_delay": detection_delay,
                    "incumbent_validation_loss": incumbent_loss,
                    "candidate_validation_loss": candidate_loss,
                    "candidate_promoted": bool(promoted),
                    "rollback_exact": bool(rollback_exact),
                    "detector_rollback_exact": bool(detector_exact),
                    "candidate_rejected_control": bool(rejected),
                    "rejection_left_incumbent_unchanged": bool(rejection_unchanged),
                    "dormancy_recovery_completed": recovery.mode == "NORMAL",
                })
    return rows


def _percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return float(ordered[index])


def _resource_events(world, count):
    by_name = {r.name: r for r in world.relation_types}
    chain_types = [by_name[name] for name in world.oracle_target_path]
    type_names = [chain_types[0].domain] + [r.codomain for r in chain_types]
    nodes = [Entity(f"g5-chain-{i}", type_names[i]) for i in range(5)]
    events = []
    for i, relation in enumerate(chain_types):
        events.append(RelationInstance(
            f"g5-chain-edge-{i}", relation, nodes[i], nodes[i + 1],
            float(i + 1), float(i + 1), "ctx",
        ))
    background_relation = by_name["a0"]
    for i in range(max(0, count - 4)):
        events.append(RelationInstance(
            f"g5-background-{i}", background_relation,
            Entity(f"g5-bg-s-{i}", background_relation.domain),
            Entity(f"g5-bg-o-{i}", background_relation.codomain),
            float(i + 5), float(i + 5), "ctx",
        ))
    return tuple(events)


def _g5_resources(resource_sizes):
    template = generate_world(10_000, 4, schema_namespace=0)
    rows = []
    for count in resource_sizes:
        events = _resource_events(template, count)
        for architecture in ("A", "B"):
            tracemalloc.start()
            model = M4ABSystem(
                architecture, template.relation_types,
                relation_capacity=max(count + 1, 2), max_path_depth=4,
                min_probability=0.0, min_margin=0.0,
            )
            model.fit_readout(template.training_examples, epochs=700, learning_rate=0.12)
            update_ns = []
            for event in events:
                start = time.perf_counter_ns()
                model.observe(event)
                update_ns.append(time.perf_counter_ns() - start)
            _, peak_bytes = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            snapshot_bytes = len(pickle.dumps(model.snapshot(), protocol=5))
            query = M4Query(
                events[0].subject, events[3].object, "ctx",
                float(count + 10), float(count + 9), max_depth=4,
            )
            query_ns = []
            for _ in range(20):
                start = time.perf_counter_ns()
                model.query(query, visible_events=events if architecture == "A" else ())
                query_ns.append(time.perf_counter_ns() - start)
            resource = model.resource_snapshot()
            rows.append({
                "relation_instances": len(events),
                "architecture": architecture,
                "persistent_numeric_bytes": resource["persistent_numeric_bytes"],
                "relation_payload_bytes": resource["relation_payload_bytes"],
                "serialized_snapshot_bytes": snapshot_bytes,
                "tracemalloc_peak_bytes": int(peak_bytes),
                "update_latency_ns_p50": _percentile(update_ns, 0.50),
                "update_latency_ns_p95": _percentile(update_ns, 0.95),
                "query_latency_ns_p50": _percentile(query_ns, 0.50),
                "query_latency_ns_p95": _percentile(query_ns, 0.95),
                "updates_per_second": float(1e9 * len(update_ns) / max(1, sum(update_ns))),
                "query_operation_count": resource["query_operation_count"],
                "accounting_note": resource["accounting_note"],
            })
    return rows


def run_validation_g45(world_count: int = 60,
                       resource_sizes=(10, 100, 500, 1000)) -> dict:
    if world_count < 1 or not resource_sizes or any(n < 4 for n in resource_sizes):
        raise ValueError("invalid validation trial/resource configuration")
    partitions = default_partitions()
    validate_partitions(partitions)
    g4 = _g4_trials(world_count)
    g5 = _g5_resources(tuple(resource_sizes))
    return {
        "classification": "validation_only_G4_G5_diagnostics_not_confirmatory",
        "partition": "validation_for_G4; synthetic_resource_sweep_for_G5",
        "confirmatory_test_accessed": partition_name == "test",
        "thresholds": {"min_probability": min_probability, "min_margin": min_margin},
        "runtime": {"python": sys.version, "platform": platform.platform()},
        "G4": {
            "rows": g4,
            "summary": {
                arch: {
                    "trials": sum(r["architecture"] == arch for r in g4),
                    "promotions": sum(r["architecture"] == arch and r["candidate_promoted"] for r in g4),
                    "exact_rollbacks": sum(r["architecture"] == arch and r["rollback_exact"] for r in g4),
                    "stable_control_alarms": sum(r["architecture"] == arch and r["stable_control_alarms"] > 0 for r in g4),
                    "transient_disturbance_alarms": sum(r["architecture"] == arch and r["transient_disturbance_alarms"] > 0 for r in g4),
                    "post_transient_recovery_alarms": sum(r["architecture"] == arch and r["post_transient_recovery_alarms"] > 0 for r in g4),
                    "rejection_controls_passed": sum(r["architecture"] == arch and r["candidate_rejected_control"] and r["rejection_left_incumbent_unchanged"] for r in g4),
                    "dormancy_recovery_passed": sum(r["architecture"] == arch and r["dormancy_recovery_completed"] for r in g4),
                } for arch in ("A", "B")
            },
        },
        "G5": {
            "rows": g5,
            "claim_boundary": "native resource measurements only; matched-resource frontier and acceptance envelope remain unfrozen",
        },
        "claim_boundary": (
            "validation and synthetic resource diagnostics only; no frozen gate, "
            "architecture-selection or M4 acceptance claim"
        ),
    }


if __name__ == "__main__":
    payload = json.dumps(run_validation_g45(), sort_keys=True, indent=2)
    print(payload)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as stream:
            stream.write(payload + "\n")
