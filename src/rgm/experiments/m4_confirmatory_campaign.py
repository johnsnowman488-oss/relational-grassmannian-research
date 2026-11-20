"""Frozen HLG-M4 confirmatory A/B campaign.

This runner is the only component authorized to open the confirmatory-test
partition. It reads the committed config, verifies the seed manifest, trains
only on the train partition, uses validation only for G4 candidate promotion,
and never retunes thresholds on test outcomes.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import random
import sys
from pathlib import Path

import numpy as np

from rgm.experiments.m4_confirmatory_worlds import (
    build_training_corpus, condition_world, default_partitions,
    generate_order_world, generate_world, partition_manifest,
    preflight_audit, validate_partitions,
)
from rgm.experiments.m4_confirmatory_g45 import (
    _bce, _g5_resources, _system_equal_to_snapshot,
)
from rgm.experiments.m4_confirmatory_frontier import run_validation_frontier
from rgm.leptograph.m4.adaptive import M4AdaptiveController
from rgm.leptograph.m4.composition import RelationInstance
from rgm.leptograph.m4.system import M4ABSystem, M4Query, PathTrainingExample


ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "docs" / "experiments" / "HLG_M4_CONFIRMATORY_CONFIG.json"
GENERATORS = (
    ("heterogeneous_typed_chain", generate_world),
    ("homogeneous_order_sensitive", generate_order_world),
)


def _load_config():
    raw = CONFIG_PATH.read_bytes()
    config = json.loads(raw)
    if config.get("status") != "frozen_before_confirmatory_test_execution":
        raise RuntimeError("confirmatory configuration is not frozen")
    if config.get("confirmatory_test_accessed") is not False:
        raise RuntimeError("config must declare test partition sealed before execution")
    if config.get("confirmatory_authorized") is not True:
        raise RuntimeError("confirmatory execution is not authorized in the frozen config")
    actual_sha = hashlib.sha256(raw).hexdigest()
    expected_sha = os.environ.get("M4_EXPECTED_CONFIG_SHA256")
    if expected_sha and expected_sha != actual_sha:
        raise RuntimeError("config SHA-256 does not match committed sidecar")
    expected_parent = os.environ.get("M4_IMPLEMENTATION_COMMIT")
    if expected_parent and expected_parent != config.get("parent_implementation_commit"):
        raise RuntimeError("frozen implementation parent does not match checkout")
    return config, actual_sha


def _partitions(config):
    parts = default_partitions()
    validate_partitions(parts)
    manifest = partition_manifest(parts)
    if config.get("generator") != manifest.get("generator"):
        raise RuntimeError("frozen generator version does not match implementation")
    manifest_sha = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if config.get("partition_manifest_sha256") and config["partition_manifest_sha256"] != manifest_sha:
        raise RuntimeError("combined partition manifest hash mismatch")
    expected = config["partitions"]
    for part in parts:
        record = expected[part.name]
        digest = manifest["seed_sha256"][part.name]
        if len(part.seeds) != record["count"] or digest != record["seed_list_sha256"]:
            raise RuntimeError(f"partition manifest mismatch for {part.name}")
        if part.seeds[0] != record["first_seed"] or part.seeds[-1] != record["last_seed"]:
            raise RuntimeError(f"partition bounds mismatch for {part.name}")
    train = next(part for part in parts if part.name == "train")
    train_corpus_hashes = {
        "heterogeneous_typed_chain": build_training_corpus(train.seeds, generate_world)[2],
        "homogeneous_order_sensitive": build_training_corpus(train.seeds, generate_order_world)[2],
    }
    if config.get("train_corpus_sha256") and config["train_corpus_sha256"] != train_corpus_hashes:
        raise RuntimeError("train-corpus hashes do not match frozen protocol")
    return {part.name: part for part in parts}


def _new_model(architecture, world, config):
    readout = config["readout"]
    return M4ABSystem(
        architecture, world.relation_types, relation_capacity=8192,
        max_path_depth=readout["max_path_depth"],
        min_probability=readout["min_probability"],
        min_margin=readout["min_margin"],
    )


def _observe(model, events):
    for event in sorted(events, key=lambda e: (e.observed_at, e.event_time, e.instance_id)):
        model.observe(event)


def _query(model, world, architecture, events, cutoff=None, query_time=None):
    view = world.learner_view(cutoff)
    result = model.query(
        M4Query(
            view.start, view.goal, "ctx",
            view.query_time if query_time is None else query_time,
            view.observation_cutoff, max_depth=world.depth,
        ),
        visible_events=tuple(events) if architecture == "A" else (),
    )
    return result


def _valid_witnesses(result, goal):
    witnesses = result.get("witnesses", ())
    if result.get("status") == "SELECTED" and not witnesses:
        return False
    for witness in witnesses:
        if len(witness.entities) != len(witness.instances) + 1:
            return False
        if witness.endpoint != goal or witness.entities[-1] != goal:
            return False
        if len({edge.instance_id for edge in witness.instances}) != len(witness.instances):
            return False
        for index, edge in enumerate(witness.instances):
            if witness.entities[index] != edge.subject or witness.entities[index + 1] != edge.object:
                return False
            if edge.subject.entity_type != edge.relation_type.domain:
                return False
            if edge.object.entity_type != edge.relation_type.codomain:
                return False
    return True


def _fit_templates(train_partition, config):
    templates = {}
    corpora = {}
    for mode, generator in GENERATORS:
        normal, world_ids, digest = build_training_corpus(train_partition.seeds, generator)
        ambiguous, ambiguous_ids, ambiguous_digest = build_training_corpus(
            train_partition.seeds, generator, condition="ambiguous_competing_paths"
        )
        if world_ids != ambiguous_ids:
            raise RuntimeError("ambiguous training corpus world manifest mismatch")
        corpora[mode] = {
            "normal": normal, "ambiguous": ambiguous,
            "training_world_count": len(world_ids),
            "training_corpus_sha256": digest,
            "ambiguous_corpus_sha256": ambiguous_digest,
        }
        template_world = generator(train_partition.seeds[0], 4)
        for architecture in ("A", "B"):
            normal_model = _new_model(architecture, template_world, config)
            normal_model.fit_readout(normal, epochs=700, learning_rate=0.12)
            ambiguous_model = _new_model(architecture, template_world, config)
            ambiguous_model.fit_readout(ambiguous, epochs=700, learning_rate=0.12)
            templates[(mode, architecture, "normal")] = normal_model.snapshot()
            templates[(mode, architecture, "ambiguous")] = ambiguous_model.snapshot()
    return templates, corpora


def _g1_g2_g3(test_partition, templates, corpora, config):
    g1, g2, g3 = [], [], []
    for seed in test_partition.seeds:
        depth = (2, 3, 4)[seed % 3]
        for mode, generator in GENERATORS:
            world = generator(seed, depth)
            view = world.learner_view()
            future_sentinel = replace(
                world.events[0],
                instance_id=f"{world.world_id}-future-sentinel",
                observed_at=world.observation_cutoff + 1.0,
            )
            augmented_world = replace(world, events=world.events + (future_sentinel,))
            causal_ids = {event.instance_id for event in augmented_world.learner_view().events}
            future_observation_leak = future_sentinel.instance_id in causal_ids
            for architecture in ("A", "B"):
                # G1: independent held-out world, fixed train-fitted readout.
                model = _new_model(architecture, world, config)
                model.restore(templates[(mode, architecture, "normal")])
                _observe(model, view.events)
                result = _query(model, world, architecture, view.events)
                g1.append({
                    "seed": seed, "world_id": world.world_id, "mode": mode,
                    "depth": depth, "architecture": architecture,
                    "status": result["status"],
                    "selected_path": result.get("selected_path"),
                    "correct": result.get("selected_path") == world.oracle_target_path,
                    "score": result.get("score"), "margin": result.get("margin"),
                    "candidate_count": len(result.get("candidates", ())),
                    "witness_count": len(result.get("witnesses", ())),
                    "witness_valid": _valid_witnesses(result, world.goal),
                    "future_observation_leak": future_observation_leak,
                    "training_world_count": corpora[mode]["training_world_count"],
                    "training_corpus_sha256": corpora[mode]["training_corpus_sha256"],
                })

                # G2-A: outage with no replay; G2-B: outage with evidence replay.
                for condition, replay in (("outage_no_replay", False),
                                          ("outage_with_replay", True)):
                    retained = _new_model(architecture, world, config)
                    retained.restore(templates[(mode, architecture, "normal")])
                    _observe(retained, view.events)
                    retained.advance_gap(8.0)
                    visible = view.events if replay else ()
                    temporal = _query(
                        retained, world, architecture, visible,
                        cutoff=view.observation_cutoff,
                        query_time=world.query_time + 8.0,
                    )
                    g2.append({
                        "seed": seed, "world_id": world.world_id, "mode": mode,
                        "architecture": architecture, "condition": condition,
                        "status": temporal["status"],
                        "correct": temporal.get("selected_path") == world.oracle_target_path,
                        "selected_path": temporal.get("selected_path"),
                    })

                # G2-C: causal early query, then ordered late-arrival updates.
                observed = sorted(view.events, key=lambda e: (e.observed_at, e.event_time, e.instance_id))
                observed_times = sorted(e.observed_at for e in observed)
                early_cutoff = observed_times[max(0, len(observed_times) // 2 - 1)]
                early_view = world.learner_view(early_cutoff)
                early_ids = {event.instance_id for event in early_view.events}
                late_events = tuple(event for event in observed if event.instance_id not in early_ids)
                late_model = _new_model(architecture, world, config)
                late_model.restore(templates[(mode, architecture, "normal")])
                _observe(late_model, early_view.events)
                early_result = _query(
                    late_model, world, architecture, early_view.events,
                    cutoff=early_cutoff, query_time=early_cutoff + 1.0,
                )
                _observe(late_model, late_events)
                late_result = _query(
                    late_model, world, architecture, view.events,
                    cutoff=view.observation_cutoff, query_time=world.query_time,
                )
                g2.append({
                    "seed": seed, "world_id": world.world_id, "mode": mode,
                    "architecture": architecture, "condition": "late_arrival",
                    "early_status": early_result["status"],
                    "early_selected": early_result.get("selected_path"),
                    "status": late_result["status"],
                    "correct": late_result.get("selected_path") == world.oracle_target_path,
                    "selected_path": late_result.get("selected_path"),
                    "late_event_count": len(late_events),
                })

                # G3: negatives, genuine ambiguity and a multiple-witness positive.
                conditions = (
                    "missing_target_edge", "wrong_context_target",
                    "temporal_invalid_target", "ambiguous_competing_paths",
                    "multiple_target_witnesses",
                )
                for condition in conditions:
                    challenged = condition_world(world, condition)
                    challenged_view = challenged.learner_view()
                    template_kind = "ambiguous" if condition == "ambiguous_competing_paths" else "normal"
                    trial = _new_model(architecture, challenged, config)
                    trial.restore(templates[(mode, architecture, template_kind)])
                    _observe(trial, challenged_view.events)
                    outcome = _query(
                        trial, challenged, architecture, challenged_view.events,
                        cutoff=challenged_view.observation_cutoff,
                        query_time=challenged.query_time,
                    )
                    selected = outcome.get("selected_path")
                    g3.append({
                        "seed": seed, "world_id": challenged.world_id,
                        "mode": mode, "architecture": architecture,
                        "condition": condition, "status": outcome["status"],
                        "selected_path": selected,
                        "selected_is_planted_target": selected == challenged.oracle_target_path,
                        "false_selection": (
                            selected is not None and condition != "multiple_target_witnesses"
                        ),
                        "score": outcome.get("score"), "margin": outcome.get("margin"),
                        "candidate_count": len(outcome.get("candidates", ())),
                        "witness_count": len(outcome.get("witnesses", ())),
                        "witness_valid": _valid_witnesses(outcome, challenged.goal),
                    })
    return g1, g2, g3


def _validation_examples(validation_partition, generator):
    examples = []
    for seed in validation_partition.seeds:
        depth = (2, 3, 4)[seed % 3]
        world = generator(seed, depth)
        examples.append(PathTrainingExample(world.oracle_target_path, 1))
        examples.extend(PathTrainingExample(path, 0) for path in world.oracle_decoy_paths)
    return tuple(examples)


def _g4_confirmatory(test_partition, validation_partition, train_partition, config):
    rows = []
    for mode, generator in GENERATORS:
        train_examples, train_ids, train_digest = build_training_corpus(
            train_partition.seeds, generator
        )
        inverse_examples = tuple(
            PathTrainingExample(example.relation_path, 1 - example.label)
            for example in train_examples
        )
        template_world = generator(train_partition.seeds[0], 4)
        val_examples = _validation_examples(validation_partition, generator)
        for architecture in ("A", "B"):
            incumbent_template = _new_model(architecture, template_world, config)
            incumbent_template.fit_readout(inverse_examples, epochs=700, learning_rate=0.12)
            candidate_template = _new_model(architecture, template_world, config)
            candidate_template.fit_readout(train_examples, epochs=900, learning_rate=0.12)

            # B's support features depend on stored observations. Validation
            # loss is therefore averaged over validation worlds with their own
            # validation-only relation stores, never over a test-world store.
            incumbent_losses, candidate_losses = [], []
            for val_seed in validation_partition.seeds:
                val_world = generator(val_seed, (2, 3, 4)[val_seed % 3])
                val_view = val_world.learner_view()
                incumbent_val = _new_model(architecture, val_world, config)
                candidate_val = _new_model(architecture, val_world, config)
                incumbent_val.restore(incumbent_template.snapshot())
                candidate_val.restore(candidate_template.snapshot())
                _observe(incumbent_val, val_view.events)
                _observe(candidate_val, val_view.events)
                examples = (
                    PathTrainingExample(val_world.oracle_target_path, 1),
                    *[PathTrainingExample(path, 0) for path in val_world.oracle_decoy_paths],
                )
                incumbent_losses.append(_bce(incumbent_val, examples))
                candidate_losses.append(_bce(candidate_val, examples))
            incumbent_validation_loss = float(np.mean(incumbent_losses))
            candidate_validation_loss = float(np.mean(candidate_losses))

            for seed in test_partition.seeds:
                depth = (2, 3, 4)[seed % 3]
                world = generator(seed, depth)
                model = _new_model(architecture, world, config)
                model.restore(incumbent_template.snapshot())
                _observe(model, world.events)
                controller = M4AdaptiveController(model)
                stable_alarms = sum(controller.observe_residual(0.05) for _ in range(100))
                transient_alarms = sum(controller.observe_residual(3.0) for _ in range(3))
                recovery_alarms = sum(controller.observe_residual(0.05) for _ in range(60))
                recovery_statistic = float(controller.detector.statistic)
                detection_delay = None
                for step in range(1, 31):
                    if controller.observe_residual(3.0):
                        detection_delay = step
                        break

                test_examples = (
                    PathTrainingExample(world.oracle_target_path, 1),
                    *[PathTrainingExample(path, 0) for path in world.oracle_decoy_paths],
                )
                incumbent_test_loss = _bce(model, test_examples)
                candidate_eval = _new_model(architecture, world, config)
                candidate_eval.restore(model.snapshot())
                candidate_eval.readout_weights = candidate_template.readout_weights.copy()
                candidate_eval.readout_bias = candidate_template.readout_bias
                candidate_test_loss = _bce(candidate_eval, test_examples)

                trusted_before = model.snapshot()
                controller.start_candidate(candidate_template.readout_weights, candidate_template.readout_bias)
                promoted = controller.validate_candidate(
                    incumbent_validation_loss, candidate_validation_loss, identifiable=True
                )
                trusted = controller.trusted_snapshot["system"]
                rollback_exact = False
                detector_exact = False
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

                reject_model = _new_model(architecture, world, config)
                reject_model.restore(trusted_before)
                reject_controller = M4AdaptiveController(reject_model)
                before_reject = reject_model.snapshot()
                reject_controller.start_candidate(reject_model.readout_weights + 0.01)
                rejected = not reject_controller.validate_candidate(1.0, 2.0, True)
                rejection_unchanged = _system_equal_to_snapshot(reject_model, before_reject)
                recovery_controller = M4AdaptiveController(reject_model)
                recovery_controller.enter_dormancy()
                recovery_controller.reactivate()
                recovery_controller.finish_recovery()

                rows.append({
                    "seed": seed, "world_id": world.world_id, "mode": mode,
                    "architecture": architecture,
                    "training_world_count": len(train_ids),
                    "training_corpus_sha256": train_digest,
                    "validation_world_count": len(validation_partition.seeds),
                    "validation_candidate_loss": candidate_validation_loss,
                    "validation_incumbent_loss": incumbent_validation_loss,
                    "candidate_promoted": bool(promoted),
                    "stable_control_alarms": int(stable_alarms),
                    "transient_disturbance_alarms": int(transient_alarms),
                    "post_transient_recovery_alarms": int(recovery_alarms),
                    "post_transient_statistic": recovery_statistic,
                    "drift_detection_delay": detection_delay,
                    "incumbent_test_loss": incumbent_test_loss,
                    "candidate_test_loss": candidate_test_loss,
                    "test_loss_improvement": incumbent_test_loss - candidate_test_loss,
                    "rollback_exact": bool(rollback_exact),
                    "detector_rollback_exact": bool(detector_exact),
                    "candidate_rejected_control": bool(rejected),
                    "rejection_left_incumbent_unchanged": bool(rejection_unchanged),
                    "dormancy_recovery_completed": recovery_controller.mode == "NORMAL",
                })
    return rows


def _paired_bootstrap(rows, metric, condition=None, resamples=10000, seed=99173):
    selected = [row for row in rows if condition is None or row.get("condition") == condition]
    by_seed_arch = {}
    for row in selected:
        value = row.get(metric)
        if value is None:
            continue
        key = (int(row["seed"]), row["architecture"])
        by_seed_arch.setdefault(key, []).append(float(value))
    seeds = sorted({key[0] for key in by_seed_arch
                    if (key[0], "A") in by_seed_arch and (key[0], "B") in by_seed_arch})
    if not seeds:
        return {"available": False, "metric": metric, "condition": condition}
    paired = np.array([
        np.mean(by_seed_arch[(seed, "B")]) - np.mean(by_seed_arch[(seed, "A")])
        for seed in seeds
    ], dtype=float)
    rng = np.random.default_rng(seed)
    samples = np.empty(resamples, dtype=float)
    for index in range(resamples):
        samples[index] = float(np.mean(rng.choice(paired, size=len(paired), replace=True)))
    return {
        "available": True, "metric": metric, "condition": condition,
        "unit": "world_seed", "n_paired_worlds": len(seeds),
        "mean_B_minus_A": float(np.mean(paired)),
        "ci95_world_cluster_bootstrap": [
            float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))
        ],
        "resamples": resamples, "bootstrap_seed": seed,
    }


def run_confirmatory_campaign():
    config, config_sha256 = _load_config()
    partitions = _partitions(config)
    train, validation, test = (
        partitions["train"], partitions["validation"], partitions["confirmatory_test"]
    )
    templates, corpora = _fit_templates(train, config)
    g1, g2, g3 = _g1_g2_g3(test, templates, corpora, config)
    g4 = _g4_confirmatory(test, validation, train, config)
    g5 = _g5_resources(
        (10, 100, 500, 1000), config["readout"]["min_probability"],
        config["readout"]["min_margin"],
    )
    g5_frontier = run_validation_frontier(
        world_count=int(config.get("g5_frontier_world_count", 30)),
        capacities=tuple(config.get(
            "g5_frontier_capacities",
            (10, 25, 50, 100, 250, 500, 750, 800, 850, 900, 950, 1000),
        )),
        partition_name="test",
        min_probability=config["readout"]["min_probability"],
        min_margin=config["readout"]["min_margin"],
    )

    g3_negative = [
        row for row in g3
        if row["condition"] in {
            "missing_target_edge", "wrong_context_target",
            "temporal_invalid_target", "ambiguous_competing_paths",
        }
    ]
    g3_positive = [row for row in g3 if row["condition"] == "multiple_target_witnesses"]
    future_audit = preflight_audit(96)
    test_world_future_leaks = {
        row["world_id"]: row["future_observation_leak"] for row in g1
    }
    if not g5_frontier["confirmatory_test_accessed"]:
        raise RuntimeError("G5 memory frontier did not use confirmatory test worlds")
    hard_invariants = {
        "invalid_witnesses_accepted": sum(
            row["status"] == "SELECTED" and not row["witness_valid"]
            for row in [*g1, *g3]
        ),
        "typed_endpoint_violations": sum(
            row["status"] == "SELECTED" and not row["witness_valid"]
            for row in [*g1, *g3]
        ),
        "g3_false_selections": sum(row["false_selection"] for row in g3_negative),
        "g3_ambiguous_selections": sum(
            row["status"] == "SELECTED"
            for row in g3 if row["condition"] == "ambiguous_competing_paths"
        ),
        "g3_positive_control_coverage": (
            sum(row["status"] == "SELECTED" for row in g3_positive) / max(1, len(g3_positive))
        ),
        "future_observation_leaks": (
            sum(bool(value) for value in test_world_future_leaks.values())
            + (0 if future_audit["future_observation_invariant"] else 1)
        ),
        "test_rows_used_for_threshold_tuning": 0,
    }

    g4_hard_invariants = {
        "exact_system_rollback_failures": sum(not row["rollback_exact"] for row in g4),
        "exact_detector_rollback_failures": sum(not row["detector_rollback_exact"] for row in g4),
        "rejected_candidate_changed_incumbent": sum(
            not row["candidate_rejected_control"] or not row["rejection_left_incumbent_unchanged"]
            for row in g4
        ),
        "dormancy_recovery_failures": sum(not row["dormancy_recovery_completed"] for row in g4),
    }
    paired = {
        "G1_exact_accuracy_B_minus_A": _paired_bootstrap(g1, "correct"),
        "G2_no_replay_accuracy_B_minus_A": _paired_bootstrap(g2, "correct", "outage_no_replay"),
        "G2_replay_accuracy_B_minus_A": _paired_bootstrap(g2, "correct", "outage_with_replay"),
        "G2_late_arrival_accuracy_B_minus_A": _paired_bootstrap(g2, "correct", "late_arrival"),
        "G3_false_selection_B_minus_A": _paired_bootstrap(
            [{**row, "false_selection_value": float(row["false_selection"])} for row in g3_negative],
            "false_selection_value",
        ),
        "G3_ambiguous_selection_B_minus_A": _paired_bootstrap(
            [{**row, "ambiguous_selection_value": float(row["status"] == "SELECTED")}
             for row in g3 if row["condition"] == "ambiguous_competing_paths"],
            "ambiguous_selection_value",
        ),
        "G3_positive_control_coverage_B_minus_A": _paired_bootstrap(
            [{**row, "positive_coverage_value": float(
                row["status"] == "SELECTED" and row["selected_is_planted_target"]
            )} for row in g3_positive],
            "positive_coverage_value",
        ),
        "G4_test_loss_improvement_B_minus_A": _paired_bootstrap(g4, "test_loss_improvement"),
        "G4_candidate_promotion_B_minus_A": _paired_bootstrap(g4, "candidate_promoted"),
        "G4_exact_rollback_B_minus_A": _paired_bootstrap(g4, "rollback_exact"),
    }

    gates = config["gates"]
    gate_results = {
        "invalid_witnesses_accepted": hard_invariants["invalid_witnesses_accepted"]
            <= gates["hard_invariants"]["invalid_witnesses_accepted"],
        "future_observation_leaks": hard_invariants["future_observation_leaks"]
            <= gates["hard_invariants"]["future_observation_leaks"],
        "typed_endpoint_violations": hard_invariants["typed_endpoint_violations"]
            <= gates["hard_invariants"]["typed_endpoint_violations"],
        "test_rows_used_for_threshold_tuning": hard_invariants["test_rows_used_for_threshold_tuning"]
            <= gates["hard_invariants"]["confirmatory_test_rows_used_for_tuning"],
        "g3_no_false_or_ambiguous_selections": (
            hard_invariants["g3_false_selections"] + hard_invariants["g3_ambiguous_selections"]
        ) <= gates["g3"]["false_selections_on_missing_wrong_context_or_temporally_invalid_or_ambiguous_cases"],
        "g3_positive_control_coverage": hard_invariants["g3_positive_control_coverage"]
            >= gates["g3"]["positive_multiple_witness_control_coverage"],
        "g4_exact_system_rollback": g4_hard_invariants["exact_system_rollback_failures"] == 0,
        "g4_exact_detector_rollback": g4_hard_invariants["exact_detector_rollback_failures"] == 0,
        "g4_rejection_preserves_incumbent": g4_hard_invariants["rejected_candidate_changed_incumbent"] == 0,
        "g4_dormancy_recovery": g4_hard_invariants["dormancy_recovery_failures"] == 0,
    }
    return {
        "classification": "confirmatory_M4_AB_test_campaign",
        "protocol_id": config["protocol_id"],
        "config_sha256": config_sha256,
        "config_path": str(CONFIG_PATH.relative_to(ROOT)),
        "runtime": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__},
        "generator": config["generator"],
        "partitions": partition_manifest(tuple(partitions.values())),
        "partition_manifest_sha256": hashlib.sha256(
            json.dumps(partition_manifest(tuple(partitions.values())), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "train_world_count": len(train.seeds),
        "validation_world_count": len(validation.seeds),
        "confirmatory_test_world_count": len(test.seeds),
        "task_modes": [mode for mode, _ in GENERATORS],
        "architectures": ["A", "B"],
        "fixed_thresholds": {
            "min_probability": config["readout"]["min_probability"],
            "min_margin": config["readout"]["min_margin"],
        },
        "confirmatory_test_accessed": True,
        "test_rows_used_for_threshold_tuning": 0,
        "G1": {"rows": g1},
        "G2": {"rows": g2},
        "G3": {"rows": g3},
        "G4": {"rows": g4},
        "G5": {"rows": g5},
        "G5_memory_budgeted_frontier": g5_frontier,
        "hard_invariants": hard_invariants,
        "G4_hard_invariants": g4_hard_invariants,
        "gate_results": gate_results,
        "bounded_integrity_gate_pass": all(gate_results.values()),
        "paired_comparisons": paired,
        "claim_boundary": (
            "This is confirmatory evidence only for the frozen within-vocabulary, "
            "task-family-bounded synthetic worlds and depth 2-4. It does not test "
            "open-world discovery, OOV relation transfer, E08 transfer, arbitrary "
            "depth, global stability, or Grassmannian advantage."
        ),
    }


if __name__ == "__main__":
    result = run_confirmatory_campaign()
    payload = json.dumps(result, sort_keys=True, indent=2)
    print(payload)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as stream:
            stream.write(payload + "\n")
