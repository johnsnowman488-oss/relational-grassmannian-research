#!/usr/bin/env python3
"""Run frozen P6 closed-loop stability and rollback campaign on compiled M4."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from rgm.experiments.h1_hierarchical_campaign import (
    M4_RUNTIME_COMMIT,
    _new_session,
    _readout_examples,
    _readout_target_matrices,
    load_frozen_partitions,
)
from rgm.leptograph.m4.p6_runtime import P6RuntimeCoupler
from rgm.leptograph.m4.composition import Entity, RelationType, RelationInstance
from rgm.leptograph.m3.resource import integrated_resource_snapshot
from rgm.leptograph.m4.stability import CoupledAdaptiveSystem

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/experiments/HLG_H1_P6_FULL_RUNTIME_v4.json"
SIDECAR = ROOT / "docs/experiments/HLG_H1_P6_FULL_RUNTIME_v4.sha256"
SOURCE_FILES = (
    "src/rgm/leptograph/m3/activation.py",
    "src/rgm/leptograph/m3/context.py",
    "src/rgm/leptograph/m3/estimation.py",
    "src/rgm/leptograph/m3/resource.py",
    "src/rgm/leptograph/m3/revision.py",
    "src/rgm/memory/soe.py",
    "src/rgm/leptograph/m4/composition.py",
    "src/rgm/leptograph/m4/soe_bridge.py",
    "src/rgm/leptograph/m4/hierarchical.py",
    "src/rgm/leptograph/m4/stability.py",
    "src/rgm/leptograph/m4/p6_runtime.py",
    "src/rgm/experiments/h1_hierarchical_campaign.py",
    "scripts/run_h1_p6_runtime_v4.py",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_hash() -> str:
    digest = hashlib.sha256()
    for relative in SOURCE_FILES:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update((ROOT / relative).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_protocol():
    raw = PROTOCOL.read_bytes()
    expected = SIDECAR.read_text(encoding="utf-8").split()[0]
    if _sha256(raw) != expected:
        raise RuntimeError("P6 protocol checksum mismatch")
    config = json.loads(raw)
    seeds = tuple(range(config["seed_range"][0], config["seed_range"][1] + 1))
    seed_hash = hashlib.sha256(",".join(map(str, seeds)).encode()).hexdigest()
    if len(seeds) != config["seed_count"] or seed_hash != config["seed_list_sha256"]:
        raise RuntimeError("P6 seed manifest mismatch")
    expected_commit = config.get("implementation_commit")
    actual_commit = os.environ.get("P6_IMPLEMENTATION_COMMIT")
    if not expected_commit or actual_commit != expected_commit:
        raise RuntimeError("P6 implementation commit does not match the frozen protocol")
    return config, seeds, _sha256(raw)


def _native_state_metrics(result):
    native = result["hierarchy"]["result"]["native"]
    maximum = 0.0
    finite = True
    per_level = {}
    state_bytes = 0
    for index, level in enumerate(native["level_states"]):
        level_max = 0.0
        for key in ("u", "chi"):
            values = np.asarray(level[key], dtype=np.float64)
            finite = finite and bool(np.all(np.isfinite(values)))
            level_max = max(level_max, float(np.linalg.norm(values)))
            state_bytes += int(values.nbytes)
        per_level[str(index)] = level_max
        maximum = max(maximum, level_max)
    return finite, maximum, per_level, state_bytes


def _relation_fixture(seed: int):
    a = Entity(f"p6-{seed}-a", "P6_A")
    b = Entity(f"p6-{seed}-b", "P6_B")
    c = Entity(f"p6-{seed}-c", "P6_C")
    d = Entity(f"p6-{seed}-d", "P6_D")
    e = Entity(f"p6-{seed}-e", "P6_E")
    ab = RelationType(f"p6-{seed}-ab", "P6_A", "P6_B")
    bc = RelationType(f"p6-{seed}-bc", "P6_B", "P6_C")
    ad = RelationType(f"p6-{seed}-ad", "P6_A", "P6_D")
    ae = RelationType(f"p6-{seed}-ae", "P6_A", "P6_E")
    base = (
        (0, RelationInstance(f"p6-{seed}-ab-1", ab, a, b, 0.01, 0.01, context="p6", provenance="P6-v4")),
        (1, RelationInstance(f"p6-{seed}-bc-1", bc, b, c, 0.01, 0.01, context="p6", provenance="P6-v4")),
    )
    candidate = (0, RelationInstance(
        f"p6-{seed}-candidate-only", ad, a, d, 3.01, 3.01, context="p6", provenance="P6-candidate"
    ))
    capacity_probe = RelationInstance(
        f"p6-{seed}-capacity-probe", ae, a, e, 3.011, 3.011, context="p6", provenance="P6-capacity"
    )
    return a, ab, bc, base, candidate, capacity_probe


def _protected_witness_ids(adapter, start, path, cutoff=3.2):
    witnesses = adapter.query(
        start, path, context="p6", query_time=cutoff, observation_cutoff=cutoff
    )
    return tuple(tuple(witness.instance_ids) for witness in witnesses)


def _resource_metrics(model):
    resource = integrated_resource_snapshot(
        estimator=model.estimator, context_bank=model.context_bank,
        activation=model.activation, detector=model.detector,
        revision=model.revision,
    )
    resource["p6_soe_memory_bytes"] = int(
        model.memory.channels.nbytes + model.memory.injection_matrices.nbytes
        + model.memory.decay_rates.nbytes
    )
    return resource


def _fill_and_probe_context_capacity(model):
    model.context_bank._pending.clear()
    for center in (np.array([10.0, 10.0]), np.array([20.0, 20.0]), np.array([30.0, 30.0])):
        for _ in range(3):
            model.context_bank.observe_novel(center)
    if len(model.context_bank.slots) != model.context_bank.capacity:
        raise AssertionError("P6 context bank did not reach its declared capacity")
    slot_ids = tuple(slot.slot_id for slot in model.context_bank.slots)
    for _ in range(3):
        result = model.context_bank.observe_novel(np.array([40.0, 40.0]))
        if result is not None:
            raise AssertionError("full P6 context bank must abstain rather than evict")
    if tuple(slot.slot_id for slot in model.context_bank.slots) != slot_ids:
        raise AssertionError("P6 context capacity probe evicted an existing slot")
    return True


def _fit_candidate(seed: int):
    truth = np.asarray([[0.8, 0.1], [0.1, 0.7]], dtype=np.float64)
    fit_rng = np.random.default_rng(seed + 1000003)
    val_rng = np.random.default_rng(seed + 2000003)
    x_fit = fit_rng.normal(size=(128, 2))
    y_fit = x_fit @ truth.T + fit_rng.normal(scale=0.05, size=(128, 2))
    fitted = np.linalg.lstsq(x_fit, y_fit, rcond=None)[0].T
    x_val = val_rng.normal(size=(128, 2))
    y_val = x_val @ truth.T + val_rng.normal(scale=0.05, size=(128, 2))
    prior = np.eye(2, dtype=np.float64)
    incumbent_loss = float(np.mean((x_val @ prior.T - y_val) ** 2))
    candidate_loss = float(np.mean((x_val @ fitted.T - y_val) ** 2))
    identifiable = bool(np.linalg.matrix_rank(x_fit) == 2)
    return fitted, prior, incumbent_loss, candidate_loss, identifiable


def _run_architecture(architecture, lib, readout_examples, seeds, config):
    session = _new_session(architecture, lib, readout_examples)
    director = session["director"]
    adapter = session["adapter"]
    if architecture == "HLB":
        adapter.store.capacity = int(config["relation_store"]["capacity"])
    coupler = P6RuntimeCoupler(
        director, hierarchy_lifecycle=session["lifecycle"],
        model=CoupledAdaptiveSystem(max_state_norm=float(config["p6_model"]["max_state_norm"])),
        readout_gain=float(config["coupling"]["readout_gain"]),
        control_gain=float(config["coupling"]["control_gain"]),
    )
    initial = coupler.checkpoint()
    rows = []
    p6_max_norm = 0.0
    native_max_norm = 0.0
    native_max_by_level = {}
    native_max_state_bytes = 0
    control_max_abs = 0.0
    native_finite = True
    total_native_steps = 0
    max_resource_bytes = 0
    max_estimator_samples = 0
    max_context_slots = 0
    max_update_ops = 0
    max_query_ops = 0
    max_trainable_parameters = 0
    try:
        for seed in seeds:
            coupler.restore(initial)
            coupler.checkpoint()
            rng = np.random.default_rng(seed)
            negative_rng = np.random.default_rng(seed + 900001)

            # Stationary negative control: no residual spikes, no false alarms.
            for tick in range(int(config["negative_control_steps"])):
                feature = negative_rng.uniform(-1.0, 1.0, size=16).astype(float)
                result = coupler.exchange(
                    event_time=(tick + 1) * 0.01,
                    observed_at=(tick + 1) * 0.01,
                    event_features={0: feature}, residual_score=0.0,
                )
                finite, native_norm, per_level, state_bytes = _native_state_metrics(result)
                native_finite = native_finite and finite
                native_max_norm = max(native_max_norm, native_norm)
                native_max_state_bytes = max(native_max_state_bytes, state_bytes)
                for level, value in per_level.items():
                    native_max_by_level[level] = max(native_max_by_level.get(level, 0.0), value)
                p6_max_norm = max(p6_max_norm, result["p6_state_norm"])
                total_native_steps += 1
            false_alarms = coupler.model.detector.alarms
            if false_alarms != 0:
                raise AssertionError(f"{architecture} seed {seed}: negative control produced {false_alarms} false alarms")

            # Reset every state surface before the matched disturbance campaign.
            coupler.restore(initial)
            coupler.checkpoint()
            relation_fixture = _relation_fixture(seed) if architecture == "HLB" else None
            if relation_fixture is not None:
                protected_start, protected_ab, protected_bc, base_records, candidate_record, capacity_probe = relation_fixture
                protected_path = (protected_ab, protected_bc)
            else:
                protected_start = protected_ab = protected_bc = base_records = candidate_record = capacity_probe = None
                protected_path = None

            mode_path = []
            activation_active_steps = {"lower": 0, "upper": 0}
            context_decisions = {}
            for tick in range(config["steps_per_seed"]):
                if tick == config["mode_schedule"]["enter_dormancy"]:
                    coupler.model.enter_dormancy()
                elif tick == config["mode_schedule"]["reactivate"]:
                    coupler.model.reactivate()
                elif tick == config["mode_schedule"]["finish_recovery"]:
                    coupler.model.finish_recovery()
                feature = rng.uniform(-1.0, 1.0, size=16).astype(float)
                residual = (
                    float(config["residual_spike_value"])
                    if tick in config["residual_spike_steps"] else 0.0
                )
                relation_records = base_records if tick == 0 and base_records is not None else ()
                result = coupler.exchange(
                    event_time=(tick + 1) * 0.01,
                    observed_at=(tick + 1) * 0.01,
                    event_features={0: feature},
                    residual_score=residual,
                    relation_records=relation_records,
                )
                finite, native_norm, per_level, state_bytes = _native_state_metrics(result)
                native_finite = native_finite and finite
                native_max_norm = max(native_max_norm, native_norm)
                native_max_state_bytes = max(native_max_state_bytes, state_bytes)
                for level, value in per_level.items():
                    native_max_by_level[level] = max(native_max_by_level.get(level, 0.0), value)
                p6_max_norm = max(p6_max_norm, result["p6_state_norm"])
                control_max_abs = max(control_max_abs, float(np.max(np.abs(result["p6_control"]))))
                total_native_steps += 1
                mode_path.append(coupler.model.mode.value)
                adaptive = result.get("adaptive_state", {})
                decision = adaptive.get("context_decision", "DORMANT")
                context_decisions[decision] = context_decisions.get(decision, 0) + 1
                for key, active in adaptive.get("active_relations", {}).items():
                    activation_active_steps[key] = activation_active_steps.get(key, 0) + int(bool(active))
                resource = adaptive.get("resource", {})
                if resource:
                    max_resource_bytes = max(
                        max_resource_bytes,
                        int(resource.get("persistent_state_bytes", 0))
                        + int(resource.get("p6_soe_memory_bytes", 0)),
                    )
                    max_estimator_samples = max(max_estimator_samples, int(coupler.model.estimator.sample_count))
                    max_context_slots = max(max_context_slots, int(len(coupler.model.context_bank.slots)))
                    max_update_ops = max(max_update_ops, int(resource.get("max_observed_or_declared_update_multiply_adds", 0)))
                    max_query_ops = max(max_query_ops, int(resource.get("max_observed_or_declared_query_multiply_adds", 0)))
                    max_trainable_parameters = max(max_trainable_parameters, int(resource.get("trainable_parameter_count", 0)))

            model = coupler.model
            alarms = model.detector.alarms
            if alarms != 2:
                raise AssertionError(f"{architecture} seed {seed}: expected 2 CUSUM alarms, got {alarms}")
            required_modes = {"DETECT", "DORMANT", "RECOVERY", "NORMAL"}
            if not required_modes.issubset(set(mode_path)):
                raise AssertionError(f"{architecture} seed {seed}: incomplete P6 mode path {sorted(set(mode_path))}")
            if model.mode.value != "DETECT":
                raise AssertionError(f"{architecture} seed {seed}: expected DETECT mode, got {model.mode.value}")
            expected_updates = int(config["steps_per_seed"]) - (
                int(config["mode_schedule"]["reactivate"])
                - int(config["mode_schedule"]["enter_dormancy"])
            )
            if model.estimator.sample_count != expected_updates:
                raise AssertionError(
                    f"P6 estimator expected {expected_updates} updates, got {model.estimator.sample_count}"
                )
            for relation_key in ("lower", "upper"):
                if (relation_key not in model.activation.states
                        or int(model.activation.states[relation_key].observed_count) != expected_updates):
                    raise AssertionError(f"P6 activation evidence count mismatch for {relation_key}")
            context_capacity_abstained = _fill_and_probe_context_capacity(model)
            resource = _resource_metrics(model)
            max_resource_bytes = max(
                max_resource_bytes,
                int(resource["persistent_state_bytes"]) + int(resource["p6_soe_memory_bytes"]),
            )
            max_estimator_samples = max(max_estimator_samples, int(model.estimator.sample_count))
            max_context_slots = max(max_context_slots, len(model.context_bank.slots))
            max_update_ops = max(max_update_ops, int(resource["max_observed_or_declared_update_multiply_adds"]))
            max_query_ops = max(max_query_ops, int(resource["max_observed_or_declared_query_multiply_adds"]))
            max_trainable_parameters = max(max_trainable_parameters, int(resource["trainable_parameter_count"]))

            protected_ids_before = None
            store_count_before = None
            if architecture == "HLB":
                protected_ids_before = _protected_witness_ids(adapter, protected_start, protected_path)
                store_count_before = len(adapter.store.records(cutoff=3.2))
                if len(protected_ids_before) != 1 or store_count_before != 2:
                    raise AssertionError("HLB protected witness chain was not present before candidate promotion")

            pre_candidate = coupler.checkpoint()
            replay_inputs = [rng.uniform(-1.0, 1.0, size=16).astype(float) for _ in range(20)]
            for index, feature in enumerate(replay_inputs):
                result = coupler.exchange(
                    event_time=(config["steps_per_seed"] + index + 1) * 0.01,
                    observed_at=(config["steps_per_seed"] + index + 1) * 0.01,
                    event_features={0: feature}, residual_score=0.0,
                )
                finite, native_norm, per_level, state_bytes = _native_state_metrics(result)
                native_finite = native_finite and finite
                native_max_norm = max(native_max_norm, native_norm)
                native_max_state_bytes = max(native_max_state_bytes, state_bytes)
                for level, value in per_level.items():
                    native_max_by_level[level] = max(native_max_by_level.get(level, 0.0), value)
                p6_max_norm = max(p6_max_norm, result["p6_state_norm"])
                total_native_steps += 1
            incumbent_continuation = coupler.snapshot()

            coupler.restore(pre_candidate)
            fitted, prior, incumbent_loss, candidate_loss, identifiable = _fit_candidate(seed)
            coupler.start_candidate(fitted)
            promoted = coupler.validate_candidate(
                incumbent_loss=incumbent_loss,
                candidate_loss=candidate_loss,
                identifiable=identifiable,
            )
            if not promoted:
                raise AssertionError(f"{architecture} seed {seed}: independently validated candidate was not promoted")
            if not np.array_equal(coupler.model.revision.accepted_operator, fitted):
                raise AssertionError("promoted P6 operator differs from fitted candidate")
            resource = _resource_metrics(coupler.model)
            max_resource_bytes = max(
                max_resource_bytes,
                int(resource["persistent_state_bytes"]) + int(resource["p6_soe_memory_bytes"]),
            )
            max_trainable_parameters = max(max_trainable_parameters, int(resource["trainable_parameter_count"]))
            max_update_ops = max(max_update_ops, int(resource["max_observed_or_declared_update_multiply_adds"]))
            max_query_ops = max(max_query_ops, int(resource["max_observed_or_declared_query_multiply_adds"]))

            for index, feature in enumerate(replay_inputs):
                relation_records = ()
                if architecture == "HLB" and index == 0:
                    relation_records = (candidate_record,)
                result = coupler.exchange(
                    event_time=(config["steps_per_seed"] + index + 1) * 0.01,
                    observed_at=(config["steps_per_seed"] + index + 1) * 0.01,
                    event_features={0: feature}, residual_score=0.0,
                    relation_records=relation_records,
                )
                finite, native_norm, per_level, state_bytes = _native_state_metrics(result)
                native_finite = native_finite and finite
                native_max_norm = max(native_max_norm, native_norm)
                native_max_state_bytes = max(native_max_state_bytes, state_bytes)
                for level, value in per_level.items():
                    native_max_by_level[level] = max(native_max_by_level.get(level, 0.0), value)
                p6_max_norm = max(p6_max_norm, result["p6_state_norm"])
                total_native_steps += 1

            relation_capacity_abstained = None
            candidate_only_removed = None
            protected_witness_preserved = None
            store_count_after_candidate = None
            if architecture == "HLB":
                store_count_after_candidate = len(adapter.store.records(cutoff=3.2))
                status = adapter.observe(0, capacity_probe)
                relation_capacity_abstained = getattr(status, "value", str(status)) == "ABSTAIN_CAPACITY"
                if not relation_capacity_abstained or store_count_after_candidate != 3:
                    raise AssertionError("HLB relation store did not abstain at the frozen capacity")
            coupler.model.rollback()
            operator_rollback = np.array_equal(
                coupler.model.revision.accepted_operator, prior
            ) and coupler.model.rollback_count == 1
            coupler.rollback()
            composite_rollback = coupler.snapshot()["fingerprint"] == pre_candidate["fingerprint"]
            if not operator_rollback or not composite_rollback:
                raise AssertionError(f"{architecture} seed {seed}: P6 rollback contract failed")

            if architecture == "HLB":
                store_count_after_rollback = len(adapter.store.records(cutoff=3.2))
                ids_after_rollback = _protected_witness_ids(adapter, protected_start, protected_path)
                candidate_only_removed = all(
                    record.instance_id != f"p6-{seed}-candidate-only"
                    for record in adapter.store.records(cutoff=3.2)
                )
                protected_witness_preserved = ids_after_rollback == protected_ids_before
                if store_count_after_rollback != 2 or not candidate_only_removed or not protected_witness_preserved:
                    raise AssertionError("HLB relation-store rollback or protected witness integrity failed")
            else:
                store_count_after_rollback = None

            for index, feature in enumerate(replay_inputs):
                result = coupler.exchange(
                    event_time=(config["steps_per_seed"] + index + 1) * 0.01,
                    observed_at=(config["steps_per_seed"] + index + 1) * 0.01,
                    event_features={0: feature}, residual_score=0.0,
                )
                finite, native_norm, per_level, state_bytes = _native_state_metrics(result)
                native_finite = native_finite and finite
                native_max_norm = max(native_max_norm, native_norm)
                native_max_state_bytes = max(native_max_state_bytes, state_bytes)
                for level, value in per_level.items():
                    native_max_by_level[level] = max(native_max_by_level.get(level, 0.0), value)
                p6_max_norm = max(p6_max_norm, result["p6_state_norm"])
                total_native_steps += 1
            replayed_continuation = coupler.snapshot()
            replay_equal = (
                replayed_continuation["fingerprint"]
                == incumbent_continuation["fingerprint"]
            )
            if not replay_equal:
                raise AssertionError(f"{architecture} seed {seed}: incumbent replay diverged after composite rollback")

            rows.append({
                "seed": int(seed),
                "negative_control_false_alarms": int(false_alarms),
                "cusum_alarms": int(alarms),
                "mode_path": sorted(set(mode_path)),
                "activation_active_steps": activation_active_steps,
                "activation_final": {
                    key: model.activation.snapshot(key)
                    for key in ("lower", "upper") if key in model.activation.states
                },
                "estimator_sample_count": int(model.estimator.sample_count),
                "context_slot_count": len(model.context_bank.slots),
                "context_capacity_abstained": bool(context_capacity_abstained),
                "context_decisions": context_decisions,
                "resource_state_bytes_max": max_resource_bytes,
                "native_state_max_norm": native_max_norm,
                "native_state_max_by_level": dict(native_max_by_level),
                "native_state_bytes_max": native_max_state_bytes,
                "p6_max_norm": float(model.max_observed_norm),
                "transition_spectral_radius": model.transition_spectral_radius,
                "incumbent_validation_loss": incumbent_loss,
                "candidate_validation_loss": candidate_loss,
                "validation_improvement": incumbent_loss - candidate_loss,
                "candidate_promoted": bool(promoted),
                "operator_rollback_exact": bool(operator_rollback),
                "composite_rollback_exact": bool(composite_rollback),
                "incumbent_replay_exact": bool(replay_equal),
                "hlb_store_count_before_candidate": store_count_before,
                "hlb_store_count_after_candidate": store_count_after_candidate,
                "hlb_store_count_after_rollback": store_count_after_rollback,
                "hlb_relation_capacity_abstained": relation_capacity_abstained,
                "hlb_candidate_only_removed": candidate_only_removed,
                "hlb_protected_witness_preserved": protected_witness_preserved,
            })

        return {
            "architecture": architecture,
            "seed_count": len(seeds),
            "steps_per_seed_before_candidate": config["steps_per_seed"],
            "native_steps_total": total_native_steps,
            "max_p6_state_norm": p6_max_norm,
            "max_native_level_state_norm": native_max_norm,
            "max_native_state_norm_by_level": native_max_by_level,
            "max_native_state_bytes": native_max_state_bytes,
            "max_abs_p6_control": control_max_abs,
            "native_state_finite_all_steps": native_finite,
            "max_resource_state_bytes": max_resource_bytes,
            "max_estimator_samples": max_estimator_samples,
            "max_context_slots": max_context_slots,
            "max_estimator_update_ops": max_update_ops,
            "max_estimator_query_ops": max_query_ops,
            "max_trainable_parameters": max_trainable_parameters,
            "negative_control_false_alarms": sum(r["negative_control_false_alarms"] for r in rows),
            "mode_transition_contracts": sum(
                {"DETECT", "DORMANT", "RECOVERY", "NORMAL"}.issubset(set(r["mode_path"]))
                for r in rows
            ),
            "context_capacity_abstentions": sum(r["context_capacity_abstained"] for r in rows),
            "hlb_relation_capacity_abstentions": sum(bool(r["hlb_relation_capacity_abstained"]) for r in rows if architecture == "HLB"),
            "hlb_candidate_only_removed": sum(bool(r["hlb_candidate_only_removed"]) for r in rows if architecture == "HLB"),
            "hlb_protected_witness_preserved": sum(bool(r["hlb_protected_witness_preserved"]) for r in rows if architecture == "HLB"),
            "mean_validation_improvement": float(np.mean([r["validation_improvement"] for r in rows])),
            "candidate_promotions": sum(r["candidate_promoted"] for r in rows),
            "operator_rollback_exact_count": sum(r["operator_rollback_exact"] for r in rows),
            "composite_rollback_exact_count": sum(r["composite_rollback_exact"] for r in rows),
            "incumbent_replay_exact_count": sum(r["incumbent_replay_exact"] for r in rows),
            "cusum_alarm_counts": sorted(set(r["cusum_alarms"] for r in rows)),
            "transition_spectral_radius": float(rows[0]["transition_spectral_radius"]),
            "rows": rows,
        }
    finally:
        coupler.close()


def run_p6_runtime_campaign(output_path: str | Path | None = None) -> dict:
    config, seeds, protocol_sha = _load_protocol()
    from gfe_ctypes import load_gfe_library
    library_path = os.environ.get("GFE_CORE_LIB")
    if not library_path:
        raise RuntimeError("GFE_CORE_LIB must point to the compiled M4 shared library")
    actual_m4_commit = os.environ.get("ABERCONICS_COMMIT")
    if actual_m4_commit != M4_RUNTIME_COMMIT:
        raise RuntimeError("P6 runtime source does not match the frozen M4 commit")
    lib = load_gfe_library(library_path)
    partitions_config, partitions, _ = load_frozen_partitions()
    matrices = _readout_target_matrices()
    train_examples = _readout_examples(partitions["train"].seeds, matrices)
    results = {
        architecture: _run_architecture(architecture, lib, train_examples, seeds, config)
        for architecture in ("HLA", "HLB")
    }
    native_limit = float(config["native_runtime"]["max_level_state_norm"])
    checks = {
        "HLA_P6_state_below_25": results["HLA"]["max_p6_state_norm"] < float(config["p6_model"]["max_state_norm"]),
        "HLB_P6_state_below_25": results["HLB"]["max_p6_state_norm"] < float(config["p6_model"]["max_state_norm"]),
        "HLA_native_state_finite": results["HLA"]["native_state_finite_all_steps"],
        "HLB_native_state_finite": results["HLB"]["native_state_finite_all_steps"],
        "HLA_native_state_within_frozen_envelope": results["HLA"]["max_native_level_state_norm"] < native_limit,
        "HLB_native_state_within_frozen_envelope": results["HLB"]["max_native_level_state_norm"] < native_limit,
        "HLA_transition_spectral_radius_below_1": results["HLA"]["transition_spectral_radius"] < 1.0,
        "HLB_transition_spectral_radius_below_1": results["HLB"]["transition_spectral_radius"] < 1.0,
        "HLA_two_alarms_per_seed": results["HLA"]["cusum_alarm_counts"] == [2],
        "HLB_two_alarms_per_seed": results["HLB"]["cusum_alarm_counts"] == [2],
        "HLA_negative_control_zero_false_alarms": results["HLA"]["negative_control_false_alarms"] == 0,
        "HLB_negative_control_zero_false_alarms": results["HLB"]["negative_control_false_alarms"] == 0,
        "HLA_mode_transitions_all_seeds": results["HLA"]["mode_transition_contracts"] == len(seeds),
        "HLB_mode_transitions_all_seeds": results["HLB"]["mode_transition_contracts"] == len(seeds),
        "HLA_context_capacity_abstention_all_seeds": results["HLA"]["context_capacity_abstentions"] == len(seeds),
        "HLA_context_estimator_updated": results["HLA"]["max_estimator_samples"] >= int(config["steps_per_seed"]) - 10,
        "HLB_context_estimator_updated": results["HLB"]["max_estimator_samples"] >= int(config["steps_per_seed"]) - 10,
        "HLA_context_bank_capacity_reached": results["HLA"]["max_context_slots"] == int(config["context_bank"]["capacity"]),
        "HLB_context_bank_capacity_reached": results["HLB"]["max_context_slots"] == int(config["context_bank"]["capacity"]),
        "HLA_resource_state_within_cap": results["HLA"]["max_resource_state_bytes"] <= int(config["resource_envelope"]["persistent_state_bytes"])
            and results["HLA"]["max_trainable_parameters"] <= int(config["resource_envelope"]["trainable_parameters"]),
        "HLB_resource_state_within_cap": results["HLB"]["max_resource_state_bytes"] <= int(config["resource_envelope"]["persistent_state_bytes"])
            and results["HLB"]["max_trainable_parameters"] <= int(config["resource_envelope"]["trainable_parameters"]),
        "HLA_update_compute_within_cap": results["HLA"]["max_estimator_update_ops"] <= int(config["resource_envelope"]["update_multiply_adds"]),
        "HLB_update_compute_within_cap": results["HLB"]["max_estimator_update_ops"] <= int(config["resource_envelope"]["update_multiply_adds"]),
        "HLA_query_compute_within_cap": results["HLA"]["max_estimator_query_ops"] <= int(config["resource_envelope"]["query_multiply_adds"]),
        "HLB_query_compute_within_cap": results["HLB"]["max_estimator_query_ops"] <= int(config["resource_envelope"]["query_multiply_adds"]),
        "HLB_context_capacity_abstention_all_seeds": results["HLB"]["context_capacity_abstentions"] == len(seeds),
        "HLA_all_candidates_promoted": results["HLA"]["candidate_promotions"] == len(seeds),
        "HLB_all_candidates_promoted": results["HLB"]["candidate_promotions"] == len(seeds),
        "HLA_operator_rollback_exact": results["HLA"]["operator_rollback_exact_count"] == len(seeds),
        "HLB_operator_rollback_exact": results["HLB"]["operator_rollback_exact_count"] == len(seeds),
        "HLA_composite_rollback_exact": results["HLA"]["composite_rollback_exact_count"] == len(seeds),
        "HLB_composite_rollback_exact": results["HLB"]["composite_rollback_exact_count"] == len(seeds),
        "HLA_incumbent_replay_exact": results["HLA"]["incumbent_replay_exact_count"] == len(seeds),
        "HLB_incumbent_replay_exact": results["HLB"]["incumbent_replay_exact_count"] == len(seeds),
        "HLB_relation_capacity_abstention_all_seeds": results["HLB"]["hlb_relation_capacity_abstentions"] == len(seeds),
        "HLB_candidate_only_record_removed_all_seeds": results["HLB"]["hlb_candidate_only_removed"] == len(seeds),
        "HLB_protected_witness_preserved_all_seeds": results["HLB"]["hlb_protected_witness_preserved"] == len(seeds),
    }
    result = {
        "protocol_id": config["protocol_id"],
        "protocol_sha256": protocol_sha,
        "seed_range": list(config["seed_range"]),
        "seed_count": len(seeds),
        "architectures": results,
        "acceptance": {"checks": checks, "passed": all(checks.values())},
        "runtime": {
            "m4_source_commit": M4_RUNTIME_COMMIT,
            "shared_library_sha256": _sha256(Path(library_path).read_bytes()),
            "p6_source_sha256": _source_hash(),
        },
        "result": "PASS" if all(checks.values()) else "FAIL",
        "claim_boundary": config["claim_boundary"],
    }
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run_p6_runtime_campaign(args.output)
    print(json.dumps({
        "result": result["result"],
        "seed_count": result["seed_count"],
        "acceptance": result["acceptance"],
        "architectures": {
            name: {key: value for key, value in item.items() if key != "rows"}
            for name, item in result["architectures"].items()
        },
        "runtime": result["runtime"],
        "output": args.output,
    }, indent=2))
    if result["result"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
