"""Execute the frozen HLG-M3 G2 200-stream confirmatory campaign.

Learner inputs and evaluator records remain separate. Every prediction is
scored before current target feedback is revealed. The runner emits six
package-level evidence files and one aggregate decision record.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from rgm.experiments.hlg_m3_benchmark_contract import validate_manifest
from rgm.experiments.hlg_m3_benchmark_generator import generate_world_stream
from rgm.leptograph.m3 import (
    ContextBank, ContextDecision, CUSUMDetector, CandidateRevision,
    CandidateLifecycle, EvidenceActivation, MemoryArchitecture, MultiSourceRidge,
)
from rgm.leptograph.m3.resource import integrated_resource_snapshot

CAMPAIGN_ID = "HLG-M3-G2-CONFIRMATORY-v1"
RESOURCE_CAPS = {
    "persistent_state_bytes": 512,
    "trainable_parameter_count": 4096,
    "update_multiply_adds": 8192,
    "query_multiply_adds": 4096,
}
COMPARATOR_NAMES = ("C0", "C1", "C2", "C3", "C4")


def _json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def _cluster_ci(values: list[float], seed: int = 20261117, draws: int = 10000) -> dict:
    """Percentile CI over resampled world-cluster means."""
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if not array.size:
        return {"mean": None, "ci95_lower": None, "ci95_upper": None, "positive_worlds": 0, "worlds": 0}
    rng = np.random.default_rng(seed)
    samples = rng.choice(array, size=(draws, array.size), replace=True).mean(axis=1)
    return {
        "mean": float(array.mean()),
        "ci95_lower": float(np.quantile(samples, 0.025)),
        "ci95_upper": float(np.quantile(samples, 0.975)),
        "positive_worlds": int(np.sum(array > 0)),
        "worlds": int(array.size),
    }


def _mean_loss(sse: float, count: int) -> float | None:
    return float(sse / count) if count else None


def _new_bundle(capacity: int) -> dict:
    """Create one capacity-stratified learner shared across development streams."""
    return {
        "model": MultiSourceRidge({"primary": 2, "secondary": 2}, 0, 2, ridge=1e-3),
        "bank": ContextBank(
            np.eye(2), capacity=int(capacity), store_scatter=False,
            full_bank_policy="nearest_reuse", novelty_repeats=3,
            accept_threshold=8.0, novelty_threshold=16.0,
        ),
        "activation": EvidenceActivation(),
        "controls": {
            name: MemoryArchitecture(name, 2, 2, state_budget=64, target_dimension=2)
            for name in COMPARATOR_NAMES
        },
    }


def _run_stream(world: dict, replicate_seed: int, bundle: dict | None = None, *, include_detector_trace: bool = False) -> dict:
    """Run one stream; evaluator records are read only after prediction."""
    stream = generate_world_stream(world, replicate_seed)
    profile = stream["factor_profile"]
    bundle = _new_bundle(int(profile["context_bank_capacity"])) if bundle is None else bundle
    model, bank = bundle["model"], bundle["bank"]
    activation, controls = bundle["activation"], bundle["controls"]
    if bank.capacity != int(profile["context_bank_capacity"]):
        raise ValueError("learner bundle capacity does not match this world's frozen profile")
    detector = CUSUMDetector()
    revision = None
    lifecycle = None
    lifecycle_records = []
    metrics = {
        "m3_sse": 0.0, "m3_n": 0,
        "control_sse": {name: 0.0 for name in COMPARATOR_NAMES},
        "control_n": {name: 0 for name in COMPARATOR_NAMES},
        "control_composition_sse": {name: 0.0 for name in COMPARATOR_NAMES},
        "control_composition_n": {name: 0 for name in COMPARATOR_NAMES},
    }
    phase = defaultdict(lambda: [0.0, 0])
    composition = defaultdict(lambda: [0.0, 0])
    routing = {"ACCEPT": 0, "ABSTAIN": 0, "NOVEL": 0, "missing_context": 0, "novel_slots_created": 0, "nearest_reuse": 0}
    identifiability = defaultdict(int)
    alarm_steps = []
    detector_trace = []
    source_observed_total = {"primary": 0, "secondary": 0}
    target_observed_total = 0
    baseline_losses = []
    baseline_mean = None
    baseline_scale = None

    for observation, evaluator in zip(stream["learner_observations"], stream["evaluator_records"]):
        # Route only on the current observed context. No evaluator context ID is read.
        slot_id = None
        context_score = float("inf")
        if observation.context_observed:
            context = np.asarray(observation.context_vector, dtype=float)
            decision, slot_id, scores = bank.route(context)
            routing[decision.value] += 1
            if decision is ContextDecision.NOVEL:
                before = len(bank.slots)
                slot_id = bank.observe_novel(context)
                if slot_id is not None:
                    routing["novel_slots_created"] += int(len(bank.slots) > before)
                    if len(bank.slots) == before:
                        routing["nearest_reuse"] += 1
            elif decision is ContextDecision.ACCEPT and slot_id is not None:
                context_score = float(scores[slot_id])
                next(slot for slot in bank.slots if slot.slot_id == slot_id).update(context)
        else:
            routing["missing_context"] += 1

        sources = {}
        gates = {}
        for source_id, vector, observed in zip(
            observation.source_ids, observation.source_vectors, observation.source_observed
        ):
            source_observed_total[source_id] += int(observed)
            sources[source_id] = np.zeros(2, dtype=float) if vector is None else np.asarray(vector, dtype=float)
            gates[source_id] = 1.0 if observed else 0.0

        # Update controls from current inputs, then predict before target feedback.
        for control in controls.values():
            if observation.context_observed:
                control.update_mode(np.asarray(observation.context_vector, dtype=float))
            relation_input = np.concatenate([sources["primary"], sources["secondary"]])
            control.update_relation(relation_input)
        if slot_id is not None and set(bank.operator_for_slot(slot_id)) == {"primary", "secondary"}:
            prediction = model.predict_context_conditioned(
                sources, [], context_slot=slot_id, context_bank=bank, source_gates=gates
            )
        else:
            # CandidateRevision owns the active shared fallback primary operator.
            # Accepted context-slot operators remain context-specific and untouched.
            fallback_overrides = bank.operator_for_slot(slot_id) if slot_id is not None else {}
            if revision is not None and (
                revision.revision_count > 0 or (lifecycle is not None and lifecycle.is_open)
            ):
                fallback_overrides.setdefault("primary", revision.accepted_operator)
            prediction = model.predict(
                sources, [], source_gates=gates,
                operator_overrides=fallback_overrides or None,
            )
        control_predictions = {name: control.predict() for name, control in controls.items()}

        # Candidate lifecycle consumes only feedback after the current prediction.
        target_observed = bool(evaluator.target_observed)
        if target_observed:
            target_observed_total += 1
            target = np.asarray(evaluator.target_vector, dtype=float)
            error = target - prediction
            loss = float(error @ error)
            metrics["m3_sse"] += loss
            metrics["m3_n"] += 1
            phase[evaluator.phase_id][0] += loss
            phase[evaluator.phase_id][1] += 1
            if evaluator.composition_id:
                composition[evaluator.composition_id][0] += loss
                composition[evaluator.composition_id][1] += 1
            for name, control_prediction in control_predictions.items():
                control_error = target - control_prediction
                control_loss = float(control_error @ control_error)
                metrics["control_sse"][name] += control_loss
                metrics["control_n"][name] += 1
                if evaluator.composition_id:
                    metrics["control_composition_sse"][name] += control_loss
                    metrics["control_composition_n"][name] += 1

            # Relationship activation uses prequential marginal loss, not evaluator labels.
            contributions = model.marginal_loss_contributions(sources, [], target, source_gates=gates)
            ident = model.conditional_identifiability()
            for source_id in ("primary", "secondary"):
                identifiable = bool(ident[source_id]["identifiable"])
                identifiability[source_id + (":identifiable" if identifiable else ":not_identifiable")] += 1
                ablated_improvement = contributions[source_id]
                activation.update(
                    source_id,
                    predictive_improvement=float(np.clip(
                        ablated_improvement / max(loss + ablated_improvement, 1e-12), -1.0, 1.0
                    )),
                    observed=True,
                    identifiable=identifiable,
                    context_score=context_score,
                    context_slot=slot_id,
                )
            # Freeze a per-stream acquisition baseline, then feed the CUSUM
            # a standardized prequential loss innovation. The detector's
            # allowance/threshold remain the frozen 0.25/5.0 settings.
            if evaluator.phase_id == "acquisition":
                baseline_losses.append(loss)
                alarm = False
            else:
                if baseline_mean is None:
                    baseline_mean = float(np.mean(baseline_losses)) if baseline_losses else 0.0
                    baseline_scale = max(
                        float(np.std(baseline_losses, ddof=1)) if len(baseline_losses) > 1 else 0.0,
                        0.1 * baseline_mean, 0.01,
                    )
                detector_score = (loss - baseline_mean) / baseline_scale
                cusum_before = float(detector.statistic)
                alarm = detector.update(float(detector_score))
                if include_detector_trace:
                    detector_trace.append({
                        "step_index": int(observation.step_index),
                        "phase_id": str(evaluator.phase_id),
                        "standardized_loss_innovation": float(detector_score),
                        "cusum_before": cusum_before,
                        "cusum_after": float(detector.statistic),
                        "alarm": bool(alarm),
                    })
            if alarm:
                alarm_steps.append(observation.step_index)
                if lifecycle is None:
                    revision = CandidateRevision(model.source_operator("primary"))
                    lifecycle = CandidateLifecycle(revision, 2, 2)
                    lifecycle.start(observation.step_index)
                elif lifecycle.is_open:
                    lifecycle.record_alarm(observation.step_index)

            if lifecycle is not None and lifecycle.is_open and observation.step_index > lifecycle.alarm_step:
                primary = sources["primary"]
                primary_seen = bool(gates["primary"])
                # Candidate windows use the same shared-fallback predictor that
                # CandidateRevision will replace, not a context-slot operator.
                incumbent_operator = revision.accepted_operator
                fallback_prediction = model.predict(
                    sources, [], source_gates=gates,
                    operator_overrides={"primary": incumbent_operator},
                )
                primary_contribution = incumbent_operator @ primary
                residual_target = target - (fallback_prediction - primary_contribution)
                decision_record = lifecycle.observe(
                    step_index=observation.step_index,
                    source=primary if primary_seen else None,
                    residual_target=residual_target if primary_seen else None,
                    observed=bool(primary_seen and target_observed),
                    identifiable=bool(model.conditional_identifiability()["primary"]["identifiable"]),
                )
                if decision_record is not None:
                    lifecycle_records.append(decision_record)

            # Reveal/update only after all predictions and prequential scores are fixed.
            if slot_id is not None:
                model.update_context_conditioned(
                    sources, [], target, context_slot=slot_id, context_bank=bank,
                    source_gates=gates, rate=0.1,
                )
            else:
                model.update(sources, [], target, source_gates=gates)
            for control in controls.values():
                control.update_target(target)
        elif lifecycle is not None and lifecycle.is_open and observation.step_index > lifecycle.alarm_step:
            decision_record = lifecycle.observe(
                step_index=observation.step_index, source=None, residual_target=None,
                observed=False, identifiable=False,
            )
            if decision_record is not None:
                lifecycle_records.append(decision_record)

    resource = integrated_resource_snapshot(
        estimator=model, context_bank=bank, activation=activation,
        detector=detector, lifecycle=lifecycle, revision=revision,
    )
    control_resources = {name: control.resource_snapshot() for name, control in controls.items()}
    return {
        "world_id": stream["world_id"], "split": stream["split"],
        "world_configuration_seed": stream["world_configuration_seed"],
        "replicate_seed": stream["replicate_seed"], "factor_profile": profile,
        "stream_sha256": stream["stream_sha256"], "step_count": len(stream["learner_observations"]),
        "m3_loss": _mean_loss(metrics["m3_sse"], metrics["m3_n"]),
        "m3_observed_targets": metrics["m3_n"],
        "control_losses": {
            name: _mean_loss(metrics["control_sse"][name], metrics["control_n"][name])
            for name in COMPARATOR_NAMES
        },
        "phase_losses": {key: _mean_loss(value[0], value[1]) for key, value in phase.items()},
        "composition_losses": {key: _mean_loss(value[0], value[1]) for key, value in composition.items()},
        "composition_m3_loss": _mean_loss(
            sum(value[0] for value in composition.values()),
            sum(value[1] for value in composition.values()),
        ),
        "composition_control_losses": {
            name: _mean_loss(metrics["control_composition_sse"][name],
                             metrics["control_composition_n"][name])
            for name in COMPARATOR_NAMES
        },
        "routing": routing, "identifiability": dict(identifiability),
        "source_observed": source_observed_total, "target_observed": target_observed_total,
        "detector_baseline": {
            "observed_acquisition_rows": len(baseline_losses),
            "mean_squared_loss": baseline_mean,
            "scale": baseline_scale,
        },
        "alarm_steps": alarm_steps, "detector_alarms": detector.alarms,
        "change_schedule": [{"step": int(step), "event": str(event)} for step, event in stream["change_schedule"]],
        "detector_trace": detector_trace if include_detector_trace else None,
        "candidate_lifecycle": lifecycle.result() if lifecycle is not None else None,
        "candidate_lifecycle_records": lifecycle_records,
        "candidate_revision_applied_to_fallback": bool(revision is not None and revision.revision_count > 0),
        "resource": resource, "control_resources": control_resources,
    }


def _world_cluster_means(rows: list[dict], value_getter) -> list[float]:
    grouped = defaultdict(list)
    for row in rows:
        value = value_getter(row)
        if value is not None and np.isfinite(value):
            grouped[row["world_id"]].append(float(value))
    return [float(np.mean(values)) for _, values in sorted(grouped.items())]


def run_campaign(manifest_path: Path, output_dir: Path) -> dict:
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw.decode("utf-8"))
    validation = validate_manifest(manifest)
    manifest_sha = hashlib.sha256(raw).hexdigest()
    expected_sha = "8548f2a72de09a81f79a57a19b3cd8196dbeae185db9432619e6ac5cc2f49101"
    if manifest_sha != expected_sha:
        raise ValueError("G2 manifest bytes do not match the G1-accepted manifest")
    if validation["world_configuration_count"] != 40 or validation["replicate_stream_count"] != 200:
        raise ValueError("G2 manifest must contain exactly 40 worlds and 200 streams")

    bundles = {capacity: _new_bundle(capacity) for capacity in (2, 4, 8)}
    fit_rows, validation_rows, test_rows = [], [], []
    # Persistent capacity-stratified learners consume development fit and
    # validation streams in manifest order. Validation chooses the comparator.
    for world in manifest["worlds"]:
        if world["split"] == "test":
            continue
        capacity = int(world["factor_profile"]["context_bank_capacity"])
        destination = fit_rows if world["split"] == "development_fit" else validation_rows
        for seed in world["replicate_seeds"]:
            destination.append(_run_stream(world, int(seed), bundles[capacity]))

    # Each test stream starts from an independent copy of its capacity-matched
    # fit+validation learner; no test replicate trains another test replicate.
    for world in manifest["worlds"]:
        if world["split"] != "test":
            continue
        capacity = int(world["factor_profile"]["context_bank_capacity"])
        for seed in world["replicate_seeds"]:
            test_bundle = copy.deepcopy(bundles[capacity])
            test_rows.append(_run_stream(world, int(seed), test_bundle))
    rows = fit_rows + validation_rows + test_rows
    if len(rows) != 200:
        raise AssertionError("confirmatory runner did not execute all 200 streams")
    comparator_losses = {
        name: float(np.mean([row["composition_control_losses"][name] for row in validation_rows
                              if row["composition_control_losses"][name] is not None]))
        for name in COMPARATOR_NAMES
    }
    strongest = min(COMPARATOR_NAMES, key=lambda name: (comparator_losses[name], name))

    capability_world_improvements = _world_cluster_means(
        test_rows,
        lambda row: (
            (row["composition_control_losses"][strongest] - row["composition_m3_loss"])
            / row["composition_control_losses"][strongest]
            if row["composition_m3_loss"] is not None
            and row["composition_control_losses"][strongest] not in (None, 0.0)
            else None
        ),
    )
    capability_ci = _cluster_ci(capability_world_improvements)
    capability_pass = bool(
        capability_ci["mean"] is not None
        and capability_ci["mean"] >= 0.05
        and capability_ci["ci95_lower"] > 0.0
        and capability_ci["positive_worlds"] >= 15
        and capability_ci["worlds"] == 20
    )

    adaptation_values = []
    for row in test_rows:
        lifecycle = row["candidate_lifecycle"]
        value = None
        if lifecycle and lifecycle.get("status") == "PROMOTED_EVALUATED":
            value = lifecycle.get("post_promotion_window", {}).get("relative_improvement")
        adaptation_values.append((row["world_id"], value))
    adaptation_by_world = defaultdict(list)
    for world_id, value in adaptation_values:
        adaptation_by_world[world_id].append(float(value) if value is not None else 0.0)
    adaptation_world_means = [float(np.mean(adaptation_by_world[key])) for key in sorted(adaptation_by_world)]
    adaptation_ci = _cluster_ci(adaptation_world_means, seed=20261118)
    adaptation_pass = bool(
        adaptation_ci["mean"] is not None
        and adaptation_ci["mean"] >= 0.05
        and adaptation_ci["ci95_lower"] > 0.0
        and adaptation_ci["positive_worlds"] >= 15
        and adaptation_ci["worlds"] == 20
    )

    # Aggregate package evidence. No package uses evaluator context labels as learner inputs.
    routing_totals = defaultdict(int)
    routing_by_capacity = defaultdict(lambda: defaultdict(int))
    phase_losses = defaultdict(list)
    composition_losses = defaultdict(list)
    composition_control_losses = defaultdict(list)
    identifiability_totals = defaultdict(int)
    correlation_composition_losses = defaultdict(list)
    for row in test_rows:
        capacity = str(row["factor_profile"]["context_bank_capacity"])
        for key, value in row["routing"].items():
            routing_totals[key] += int(value)
            routing_by_capacity[capacity][key] += int(value)
        for key, value in row["identifiability"].items():
            identifiability_totals[key] += int(value)
        correlation_composition_losses[str(row["factor_profile"]["source_correlation"])].append(
            row["composition_m3_loss"]
        )
        for key, value in row["composition_control_losses"].items():
            if value is not None:
                composition_control_losses[key].append(value)
        for key, value in row["phase_losses"].items():
            if value is not None:
                phase_losses[key].append(value)
        for key, value in row["composition_losses"].items():
            if value is not None:
                composition_losses[key].append(value)

    resource_rows = [row["resource"] for row in test_rows]
    resource_max = {
        key: max(int(item[key]) for item in resource_rows)
        for key in (
            "persistent_state_bytes", "trainable_parameter_count",
            "max_observed_or_declared_update_multiply_adds",
            "max_observed_or_declared_query_multiply_adds",
        )
    }
    control_resource_pass = all(
        max(row["control_resources"][name]["persistent_state_bytes"] for row in test_rows)
            <= RESOURCE_CAPS["persistent_state_bytes"]
        and max(row["control_resources"][name]["trainable_parameter_count"] for row in test_rows)
            <= RESOURCE_CAPS["trainable_parameter_count"]
        and max(row["control_resources"][name]["update_multiply_adds_per_observed_update_upper_bound"] for row in test_rows)
            <= RESOURCE_CAPS["update_multiply_adds"]
        and max(row["control_resources"][name]["query_multiply_adds_per_prediction_upper_bound"] for row in test_rows)
            <= RESOURCE_CAPS["query_multiply_adds"]
        for name in COMPARATOR_NAMES
    )
    resource_pass = all((
        resource_max["persistent_state_bytes"] <= RESOURCE_CAPS["persistent_state_bytes"],
        resource_max["trainable_parameter_count"] <= RESOURCE_CAPS["trainable_parameter_count"],
        resource_max["max_observed_or_declared_update_multiply_adds"] <= RESOURCE_CAPS["update_multiply_adds"],
        resource_max["max_observed_or_declared_query_multiply_adds"] <= RESOURCE_CAPS["query_multiply_adds"],
        control_resource_pass,
    ))

    packages = {
        "M3-A": {
            "package_id": "M3-A", "title": "Context ambiguity and capacity",
            "test_stream_count": len(test_rows), "routing_totals": dict(routing_totals),
            "routing_totals_by_capacity": {key: dict(value) for key, value in routing_by_capacity.items()},
            "capacity_levels": sorted({int(row["factor_profile"]["context_bank_capacity"]) for row in test_rows}),
            "context_reuse_is_label_blind": True,
        },
        "M3-B": {
            "package_id": "M3-B", "title": "Held-out composition, correlation and identifiability",
            "strongest_validation_comparator": strongest, "validation_comparator_losses": comparator_losses,
            "test_composition_mean_losses": {key: float(np.mean(values)) for key, values in composition_losses.items()},
            "test_composition_mean_losses_by_comparator": {
                name: float(np.mean(values)) for name, values in composition_control_losses.items()
            },
            "test_composition_loss_by_source_correlation": {
                key: float(np.mean(values)) for key, values in correlation_composition_losses.items()
            },
            "test_identifiability_counts": dict(identifiability_totals),
            "capability_endpoint": "observed target loss restricted to composition_extension rows",
            "capability_world_clustered_relative_improvement": capability_ci,
            "capability_threshold": 0.05, "capability_gate_passed": capability_pass,
        },
        "M3-C": {
            "package_id": "M3-C", "title": "Missingness, dormancy and reactivation",
            "test_phase_mean_losses": {key: float(np.mean(values)) for key, values in phase_losses.items()},
            "missingness_profiles": sorted({float(row["factor_profile"]["independent_observation_probability"]) for row in test_rows}),
            "burst_outage_profiles": sorted({int(row["factor_profile"]["burst_outage_steps"]) for row in test_rows}),
            "observed_source_rates": {
                source: sum(row["source_observed"][source] for row in test_rows)
                / max(1, sum(row["step_count"] for row in test_rows))
                for source in ("primary", "secondary")
            },
            "observed_context_rate": sum(
                row["step_count"] - row["routing"]["missing_context"] for row in test_rows
            ) / max(1, sum(row["step_count"] for row in test_rows)),
            "observed_target_rate": sum(row["target_observed"] for row in test_rows)
            / max(1, sum(row["step_count"] for row in test_rows)),
        },
        "M3-D": {
            "package_id": "M3-D", "title": "Drift detection and candidate revision",
            "detector_signal": "prequential squared-loss innovation standardized against the observed acquisition phase; CUSUM allowance=0.25, threshold=5.0",
            "baseline_observed_rows_min": min(row["detector_baseline"]["observed_acquisition_rows"] for row in test_rows),
            "baseline_observed_rows_max": max(row["detector_baseline"]["observed_acquisition_rows"] for row in test_rows),
            "baseline_mean_loss_range": [
                float(min(row["detector_baseline"]["mean_squared_loss"] for row in test_rows if row["detector_baseline"]["mean_squared_loss"] is not None)),
                float(max(row["detector_baseline"]["mean_squared_loss"] for row in test_rows if row["detector_baseline"]["mean_squared_loss"] is not None)),
            ],
            "test_streams_with_alarms": sum(bool(row["alarm_steps"]) for row in test_rows),
            "total_detector_alarms": sum(int(row["detector_alarms"]) for row in test_rows),
            "candidate_revisions_applied_to_fallback": sum(
                bool(row["candidate_revision_applied_to_fallback"]) for row in test_rows
            ),
            "candidate_revision_scope": "shared fallback primary operator; context-slot operators remain independently learned",
            "alarms_by_drift_family": {
                family: sum(int(row["detector_alarms"]) for row in test_rows
                            if row["factor_profile"]["drift_family"] == family)
                for family in sorted({row["factor_profile"]["drift_family"] for row in test_rows})
            },
            "candidate_lifecycle_status_counts": {
                status: sum(1 for row in test_rows if row["candidate_lifecycle"] and row["candidate_lifecycle"]["status"] == status)
                for status in ("IN_PROGRESS", "INSUFFICIENT_EVIDENCE_FIT", "INSUFFICIENT_EVIDENCE_VALIDATION",
                               "REJECTED", "PROMOTED_POST_INSUFFICIENT_EVIDENCE", "PROMOTED_EVALUATED")
            },
            "adaptation_world_clustered_relative_improvement": adaptation_ci,
            "adaptation_threshold": 0.05, "adaptation_gate_passed": adaptation_pass,
        },
        "M3-E": {
            "package_id": "M3-E", "title": "Common-envelope and Pareto comparison",
            "resource_caps": RESOURCE_CAPS, "test_m3_resource_maxima": resource_max,
            "resource_gate_passed": resource_pass,
            "control_resource_gate_passed": control_resource_pass,
            "accounting_scope": "live numeric payloads with conservative per-operation upper bounds for estimator solves/updates, context routing/LMS, lifecycle windows, activation and detector; Python object/container overhead excluded",
            "control_resource_ranges": {
                name: {
                    "state_bytes_min": min(row["control_resources"][name]["persistent_state_bytes"] for row in test_rows),
                    "state_bytes_max": max(row["control_resources"][name]["persistent_state_bytes"] for row in test_rows),
                    "parameter_count_max": max(row["control_resources"][name]["trainable_parameter_count"] for row in test_rows),
                    "update_multiply_adds_per_observed_update_upper_bound": max(row["control_resources"][name]["update_multiply_adds_per_observed_update_upper_bound"] for row in test_rows),
                    "query_multiply_adds_per_prediction_upper_bound": max(row["control_resources"][name]["query_multiply_adds_per_prediction_upper_bound"] for row in test_rows),
                } for name in COMPARATOR_NAMES
            },
        },
        "M3-I": {
            "package_id": "M3-I", "title": "Integrated sequential benchmark",
            "test_stream_count": len(test_rows), "test_world_count": len({row["world_id"] for row in test_rows}),
            "test_mean_m3_loss": float(np.mean([row["m3_loss"] for row in test_rows if row["m3_loss"] is not None])),
            "test_mean_heldout_composition_loss": float(np.mean([
                row["composition_m3_loss"] for row in test_rows if row["composition_m3_loss"] is not None
            ])),
            "test_mean_control_losses": {
                name: float(np.mean([row["control_losses"][name] for row in test_rows if row["control_losses"][name] is not None]))
                for name in COMPARATOR_NAMES
            },
            "capability_gate_passed": capability_pass, "adaptation_gate_passed": adaptation_pass,
            "resource_gate_passed": resource_pass,
        },
    }
    all_gates = bool(capability_pass and adaptation_pass and resource_pass)
    aggregate = {
        "campaign_id": CAMPAIGN_ID, "manifest_sha256": manifest_sha,
        "stream_count": len(rows), "world_count": len(manifest["worlds"]),
        "test_world_count": len({row["world_id"] for row in test_rows}),
        "split_stream_counts": {
            split: sum(1 for row in rows if row["split"] == split)
            for split in ("development_fit", "development_validation", "test")
        },
        "fit_streams_processed": len(fit_rows), "validation_streams_processed": len(validation_rows),
        "test_streams_processed": len(test_rows),
        "strongest_eligible_comparator": strongest,
        "strongest_comparator_selection_endpoint": "development_validation composition_extension loss",
        "capability_gate": {"threshold_relative_improvement": 0.05, "result": capability_ci, "passed": capability_pass},
        "adaptation_gate": {"threshold_relative_improvement": 0.05, "result": adaptation_ci, "passed": adaptation_pass},
        "resource_gate": {"caps": RESOURCE_CAPS, "maxima": resource_max, "passed": resource_pass},
        "m4_authorised": all_gates,
        "m3_scientific_validation_complete": all_gates,
        "scientific_status": "G2_CONFIRMATORY_EXECUTED",
        "claim_ceiling": (
            "G2 200-stream confirmatory campaign. M4 is authorised only if capability, "
            "adaptation, benchmark integrity and resource gates all pass."
        ),
        "stream_manifest": [
            {
                "world_id": row["world_id"], "split": row["split"],
                "world_configuration_seed": row["world_configuration_seed"],
                "replicate_seed": row["replicate_seed"],
                "stream_sha256": row["stream_sha256"],
                "step_count": row["step_count"],
            } for row in rows
        ],
        "integrity": {
            "prequential_prediction_before_feedback": True,
            "learner_evaluator_separation": True,
            "frozen_manifest_identity_verified": True,
            "no_evaluator_context_labels_used_for_routing": True,
            "fit_validation_test_stream_counts_are_disjoint_by_manifest": True,
        },
    }
    packages["M3-I"]["m4_authorised"] = all_gates
    output_dir.mkdir(parents=True, exist_ok=True)
    for package_id, evidence in packages.items():
        evidence["campaign_id"] = CAMPAIGN_ID
        evidence["evidence_sha256"] = _json_hash(evidence)
        (output_dir / f"{package_id.lower()}.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
        )
    aggregate["package_evidence_sha256"] = {
        package_id: _json_hash(evidence) for package_id, evidence in packages.items()
    }
    aggregate["aggregate_sha256"] = _json_hash(aggregate)
    (output_dir / "aggregate.json").write_text(
        json.dumps(aggregate, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    return aggregate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run_campaign(args.manifest, args.output_dir)
    print(json.dumps({
        "campaign_id": result["campaign_id"], "stream_count": result["stream_count"],
        "test_world_count": result["test_world_count"],
        "capability_gate_passed": result["capability_gate"]["passed"],
        "adaptation_gate_passed": result["adaptation_gate"]["passed"],
        "resource_gate_passed": result["resource_gate"]["passed"],
        "m4_authorised": result["m4_authorised"],
        "aggregate_sha256": result["aggregate_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
