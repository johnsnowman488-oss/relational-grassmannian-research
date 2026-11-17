"""BM-2 F6-derived, factorised sequential world generator.

This module generates learner-side observations and evaluator-side truth as
separate typed records. It does not run an M3 learner or score scientific
performance. The BM-2 pilot is a deterministic generator/contract smoke.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from rgm.experiments.hlg_m3_benchmark_contract import (
    CAMPAIGN_ID,
    COMPOSITIONS,
    F6_WORLD_TEMPLATE,
    LearnerObservation,
    EvaluatorRecord,
    PrequentialGate,
    TargetFeedback,
    build_one_factor_pilot_profiles,
    validate_manifest,
    make_learner_observation,
)
from rgm.experiments.leptograph_m3_foundation_campaign import case_f6

BM2_ID = "HLG-M3-BROAD-BENCHMARK-BM2-GENERATOR-v0.1"
BASE_NOISE_STD = 0.005
COMPOSITION_STEPS_PER_RELATION = 20
BROAD_BURST_REACTIVATION_STEPS = 20
RELATION_ATOMS = ("REL-A", "REL-B", "REL-C", "REL-D")


def _f6_operators() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    theta_a = np.array([[0.6, -0.2], [0.1, 0.5]], dtype=float)
    theta_b = np.array([[-0.3, 0.4], [0.7, 0.1]], dtype=float)
    theta_other = np.array([[0.25, -0.15], [0.05, 0.2]], dtype=float)
    return theta_a, theta_b, theta_other


def _context_prototypes(dprime: float) -> dict[str, np.ndarray]:
    """Four relation prototypes with nearest-neighbour Euclidean separation d'."""
    radius = float(dprime) / np.sqrt(2.0)
    relation = {
        "REL-A": np.array([radius, 0.0]),
        "REL-B": np.array([0.0, radius]),
        "REL-C": np.array([-radius, 0.0]),
        "REL-D": np.array([0.0, -radius]),
    }
    relation["F6-CONTEXT-A"] = np.array([-float(dprime) / 2.0, 0.0])
    relation["F6-CONTEXT-B"] = np.array([float(dprime) / 2.0, 0.0])
    return relation


def _composition_operators(configuration_seed: int) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Construct distinct, configuration-specific operators for the added REL-A-D task."""
    theta_a, theta_b, theta_c = _f6_operators()
    theta_d = theta_a + theta_b - theta_c
    bases = {"REL-A": theta_a, "REL-B": theta_b, "REL-C": theta_c, "REL-D": theta_d}
    secondary_bases = {
        "REL-A": 0.15 * theta_c,
        "REL-B": 0.20 * theta_a,
        "REL-C": 0.20 * theta_b,
        "REL-D": 0.15 * (theta_a + theta_c),
    }
    rng = np.random.default_rng(int(configuration_seed))
    primary = {
        key: value + rng.normal(0.0, 0.015, size=(2, 2))
        for key, value in bases.items()
    }
    secondary = {
        key: value + rng.normal(0.0, 0.01, size=(2, 2))
        for key, value in secondary_bases.items()
    }
    return primary, secondary


def _correlated_sources(rng: np.random.Generator, rho: float) -> tuple[np.ndarray, np.ndarray]:
    primary = rng.normal(size=2)
    independent = rng.normal(size=2)
    secondary = float(rho) * primary + np.sqrt(max(0.0, 1.0 - float(rho) ** 2)) * independent
    return primary, secondary


def _record_operator(name: str, operator: np.ndarray) -> tuple[str, tuple[float, ...]]:
    return name, tuple(float(value) for value in np.asarray(operator, dtype=float).reshape(-1))


def _jsonable_digest(learner: list[LearnerObservation], evaluator: list[EvaluatorRecord]) -> str:
    payload = {
        "learner": [
            {
                "step_index": row.step_index,
                "source_ids": row.source_ids,
                "source_vectors": row.source_vectors,
                "source_observed": row.source_observed,
                "context_vector": row.context_vector,
                "context_observed": row.context_observed,
            }
            for row in learner
        ],
        "evaluator": [
            {
                "step_index": row.step_index,
                "world_id": row.world_id,
                "scenario_template_id": row.scenario_template_id,
                "split": row.split,
                "world_configuration_seed": row.world_configuration_seed,
                "replicate_seed": row.replicate_seed,
                "composition_ids": row.composition_ids,
                "primitive_relations": row.primitive_relations,
                "true_context_id": row.true_context_id,
                "latent_relation_operators": row.latent_relation_operators,
                "change_schedule": row.change_schedule,
                "target_vector": row.target_vector,
                "target_observed": row.target_observed,
                "target_truth": row.target_truth,
                "phase_id": row.phase_id,
                "composition_id": row.composition_id,
            }
            for row in evaluator
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _drifted_operator(
    base: np.ndarray,
    drift_family: str,
    phase_step: int,
    phase_length: int,
) -> tuple[np.ndarray, float]:
    change = np.full_like(base, 0.25)
    fraction = (phase_step + 1) / max(1, phase_length)
    if drift_family == "stationary":
        return base.copy(), 1.0
    if drift_family == "step":
        return base + change, 1.0
    if drift_family == "gradual":
        return base + fraction * change, 1.0
    if drift_family == "variance_only":
        return base.copy(), 2.0
    if drift_family == "transient":
        return (base + change, 1.0) if phase_step < max(1, phase_length // 4) else (base.copy(), 1.0)
    if drift_family == "compound":
        noise_factor = 2.0 if phase_step >= phase_length // 2 else 1.0
        return base + fraction * change, noise_factor
    raise ValueError(f"unknown drift family: {drift_family}")


def generate_world_stream(world: Mapping[str, Any], replicate_seed: int) -> dict[str, Any]:
    """Generate one factorised F6-derived stream with a strict learner/evaluator boundary."""
    required = {
        "world_id", "split", "scenario_template_id", "world_configuration_seed",
        "composition_ids", "factor_profile",
    }
    missing = required.difference(world)
    if missing:
        raise ValueError(f"world manifest record is missing fields: {sorted(missing)}")
    if world["scenario_template_id"] != F6_WORLD_TEMPLATE["template_id"]:
        raise ValueError("world does not use the declared F6 scenario template")
    if world["split"] not in COMPOSITIONS:
        raise ValueError("world split is not a primary benchmark split")

    profile = dict(world["factor_profile"])
    rho = float(profile["source_correlation"])
    context_dprime = float(profile["context_separation_dprime"])
    missing_probability = float(profile["independent_observation_probability"])
    burst_length = int(profile["burst_outage_steps"])
    drift_family = str(profile["drift_family"])
    noise_multiplier = float(profile["observation_noise_multiplier"])
    if not 0.0 <= rho <= 1.0:
        raise ValueError("source correlation must be in [0, 1]")
    if not 0.0 < missing_probability <= 1.0:
        raise ValueError("observation probability must be in (0, 1]")
    if context_dprime <= 0 or burst_length <= 0 or noise_multiplier <= 0:
        raise ValueError("context separation, outage length and noise multiplier must be positive")

    split = str(world["split"])
    world_id = str(world["world_id"])
    world_seed = int(world["world_configuration_seed"])
    seed = int(replicate_seed)
    rng = np.random.default_rng(seed)
    context_prototypes = _context_prototypes(context_dprime)
    theta_a, theta_b, theta_other = _f6_operators()
    relation_primary, relation_secondary = _composition_operators(world_seed)

    composition_rows = COMPOSITIONS[split]
    expected_composition_ids = [row["composition_id"] for row in composition_rows]
    if list(world["composition_ids"]) != expected_composition_ids:
        raise ValueError("world composition allocation does not match its declared split")

    learner_rows: list[LearnerObservation] = []
    evaluator_rows: list[EvaluatorRecord] = []
    change_schedule: list[tuple[int, str]] = []
    phase_first_seen: list[str] = []
    step = 0

    def emit(
        *,
        phase_id: str,
        context_id: str,
        context_prototype: np.ndarray,
        primary_operator: np.ndarray,
        secondary_operator: np.ndarray,
        force_target_missing: bool = False,
        force_all_missing: bool = False,
        phase_noise_multiplier: float = 1.0,
        composition_id: str | None = None,
        primitive_relation: str | None = None,
        operator_names: tuple[str, str] = ("F6-PRIMARY", "F6-SECONDARY"),
    ) -> None:
        nonlocal step
        if phase_id not in phase_first_seen:
            phase_first_seen.append(phase_id)
        x_primary, x_secondary = _correlated_sources(rng, rho)
        truth = (
            np.asarray(primary_operator) @ x_primary
            + np.asarray(secondary_operator) @ x_secondary
            + rng.normal(
                0.0,
                BASE_NOISE_STD * noise_multiplier * phase_noise_multiplier,
                size=2,
            )
        )
        primary_observed = (not force_all_missing) and (rng.random() < missing_probability)
        secondary_observed = (not force_all_missing) and (rng.random() < missing_probability)
        context_observed = (not force_all_missing) and (rng.random() < missing_probability)
        target_observed = (
            (not force_all_missing)
            and (not force_target_missing)
            and (rng.random() < missing_probability)
        )

        source_vectors = {
            "primary": tuple(float(value) for value in x_primary) if primary_observed else None,
            "secondary": tuple(float(value) for value in x_secondary) if secondary_observed else None,
        }
        source_masks = {
            "primary": bool(primary_observed),
            "secondary": bool(secondary_observed),
        }
        noisy_context = (
            context_prototype + rng.normal(0.0, 1.0, size=2)
            if context_observed else None
        )
        learner_rows.append(make_learner_observation(
            step_index=step,
            source_vectors=source_vectors,
            source_observed=source_masks,
            context_vector=noisy_context,
            context_observed=bool(context_observed),
        ))

        evaluator_rows.append(EvaluatorRecord(
            step_index=step,
            world_id=world_id,
            scenario_template_id=F6_WORLD_TEMPLATE["template_id"],
            split=split,
            world_configuration_seed=world_seed,
            replicate_seed=seed,
            composition_ids=tuple(expected_composition_ids),
            primitive_relations=(primitive_relation,) if primitive_relation else ("F6-RELATION-1", "F6-RELATION-2"),
            true_context_id=context_id,
            latent_relation_operators=(
                _record_operator(operator_names[0], primary_operator),
                _record_operator(operator_names[1], secondary_operator),
            ),
            change_schedule=tuple(change_schedule),
            target_vector=tuple(float(value) for value in truth) if target_observed else None,
            target_observed=bool(target_observed),
            target_truth=tuple(float(value) for value in truth),
            phase_id=phase_id,
            composition_id=composition_id,
        ))
        step += 1

    zero = np.zeros((2, 2), dtype=float)
    f6_phases = [
        ("acquisition", "F6-CONTEXT-A", theta_a, zero, False),
        ("distractor", "F6-CONTEXT-A", zero, zero, False),
        ("context_switch", "F6-CONTEXT-B", theta_b, zero, False),
        ("relation2_isolation", "F6-CONTEXT-B", zero, theta_other, False),
        ("observation_gap", "F6-CONTEXT-A", theta_a, zero, True),
        ("reactivation", "F6-CONTEXT-A", theta_a, zero, False),
        ("within_context_drift", "F6-CONTEXT-A", theta_a, zero, False),
    ]
    if split == "test":
        f6_phases.append(("heldout_composition", "F6-CONTEXT-B", theta_b, theta_other, False))

    for phase_id, context_id, primary_base, secondary_base, gap in f6_phases:
        for phase_step in range(F6_WORLD_TEMPLATE["steps_per_phase"]):
            primary_operator = primary_base
            phase_noise_factor = 1.0
            if phase_id == "within_context_drift":
                if phase_step == 0 and drift_family != "stationary":
                    change_schedule.append((step, f"drift:{drift_family}"))
                primary_operator, phase_noise_factor = _drifted_operator(
                    primary_base, drift_family, phase_step, F6_WORLD_TEMPLATE["steps_per_phase"]
                )
                if drift_family == "transient" and phase_step == F6_WORLD_TEMPLATE["steps_per_phase"] // 4:
                    change_schedule.append((step, "transient_reversion"))
                if drift_family == "compound" and phase_step == F6_WORLD_TEMPLATE["steps_per_phase"] // 2:
                    change_schedule.append((step, "variance_increase"))
            emit(
                phase_id=phase_id,
                context_id=context_id,
                context_prototype=context_prototypes[context_id],
                primary_operator=primary_operator,
                secondary_operator=secondary_base,
                force_target_missing=gap,
                phase_noise_multiplier=phase_noise_factor,
            )

    # Add a separate long burst outage and recovery segment without modifying
    # the historical F6 eight-phase ordering or its old 20-step target gap.
    change_schedule.append((step, f"extended_burst_gap:{burst_length}"))
    for _ in range(burst_length):
        emit(
            phase_id="extended_burst_gap",
            context_id="F6-CONTEXT-A",
            context_prototype=context_prototypes["F6-CONTEXT-A"],
            primary_operator=theta_a,
            secondary_operator=zero,
            force_all_missing=True,
        )
    change_schedule.append((step, "extended_reactivation"))
    for _ in range(BROAD_BURST_REACTIVATION_STEPS):
        emit(
            phase_id="extended_reactivation",
            context_id="F6-CONTEXT-A",
            context_prototype=context_prototypes["F6-CONTEXT-A"],
            primary_operator=theta_a,
            secondary_operator=zero,
        )

    # The additional REL-A-D benchmark is a sequential composition of
    # context-conditioned relation episodes. It is not an algebraic product
    # of operators. Relation labels and composition IDs remain evaluator-only.
    for composition in composition_rows:
        composition_id = str(composition["composition_id"])
        for primitive in composition["ordered_relations"]:
            for _ in range(COMPOSITION_STEPS_PER_RELATION):
                emit(
                    phase_id="composition_extension",
                    context_id=str(primitive),
                    context_prototype=context_prototypes[str(primitive)],
                    primary_operator=relation_primary[str(primitive)],
                    secondary_operator=relation_secondary[str(primitive)],
                    composition_id=composition_id,
                    primitive_relation=str(primitive),
                    operator_names=(f"{primitive}-PRIMARY", f"{primitive}-SECONDARY"),
                )

    stream = {
        "campaign_id": CAMPAIGN_ID,
        "world_id": world_id,
        "split": split,
        "scenario_template_id": F6_WORLD_TEMPLATE["template_id"],
        "world_configuration_seed": world_seed,
        "replicate_seed": seed,
        "factor_profile": profile,
        "learner_config": {
            "context_bank_capacity": int(profile["context_bank_capacity"]),
            "precision": "float64",
            "resource_envelope": "provisional_F5_common_ceiling",
        },
        "composition_ids": expected_composition_ids,
        "phase_first_seen": phase_first_seen,
        "learner_observations": learner_rows,
        "evaluator_records": evaluator_rows,
        "change_schedule": tuple(change_schedule),
    }
    verify_generated_stream(stream)
    stream["stream_sha256"] = _jsonable_digest(learner_rows, evaluator_rows)
    return stream


def verify_generated_stream(stream: Mapping[str, Any]) -> dict[str, Any]:
    learner = stream["learner_observations"]
    evaluator = stream["evaluator_records"]
    if len(learner) == 0 or len(learner) != len(evaluator):
        raise AssertionError("learner and evaluator streams must be non-empty and aligned")
    if any(type(row) is not LearnerObservation for row in learner):
        raise TypeError("learner stream contains a non-LearnerObservation record")
    if any(type(row) is not EvaluatorRecord for row in evaluator):
        raise TypeError("evaluator stream contains a non-EvaluatorRecord record")

    for index, (observation, truth) in enumerate(zip(learner, evaluator)):
        if observation.step_index != index or truth.step_index != index:
            raise AssertionError("step indices must be strictly sequential and aligned")
        if hasattr(observation, "world_id") or hasattr(observation, "target_truth"):
            raise AssertionError("evaluator-only information leaked into learner observation")
        if truth.target_observed != (truth.target_vector is not None):
            raise AssertionError("target mask and learner-visible target feedback are inconsistent")
        if truth.target_truth is None:
            raise AssertionError("evaluator target truth must be retained, including for missing observations")
        for vector, observed in zip(observation.source_vectors, observation.source_observed):
            if observed != (vector is not None):
                raise AssertionError("source missingness mask and vector disagree")
        if observation.context_observed != (observation.context_vector is not None):
            raise AssertionError("context missingness mask and vector disagree")

    expected_phases = list(F6_WORLD_TEMPLATE["common_phases"])
    if stream["split"] == "test":
        expected_phases += list(F6_WORLD_TEMPLATE["test_only_phases"])
    expected_phases += ["extended_burst_gap", "extended_reactivation", "composition_extension"]
    if stream["phase_first_seen"] != expected_phases:
        raise AssertionError(f"F6-derived phase sequence changed: {stream['phase_first_seen']}")

    burst_rows = [row for row in evaluator if row.phase_id == "extended_burst_gap"]
    if len(burst_rows) != int(stream["factor_profile"]["burst_outage_steps"]):
        raise AssertionError("extended burst outage length does not match factor profile")
    if any(
        any(observation.source_observed) or observation.context_observed or row.target_observed
        for observation, row in zip(learner, evaluator)
        if row.phase_id == "extended_burst_gap"
    ):
        raise AssertionError("extended burst outage must mask all source, context and target observations")

    if any(
        row.phase_id == "heldout_composition"
        for row in evaluator
    ) != (stream["split"] == "test"):
        raise AssertionError("historical F6 held-out-composition phase must remain test-only")

    expected_comp_ids = list(stream["composition_ids"])
    observed_comp_ids = list(dict.fromkeys(
        row.composition_id for row in evaluator if row.phase_id == "composition_extension"
    ))
    if observed_comp_ids != expected_comp_ids:
        raise AssertionError("composition extension order or allocation mismatch")
    for composition in COMPOSITIONS[stream["split"]]:
        records = [
            row for row in evaluator
            if row.phase_id == "composition_extension" and row.composition_id == composition["composition_id"]
        ]
        observed_sequence = []
        for row in records:
            primitive = row.primitive_relations[0]
            if not observed_sequence or observed_sequence[-1] != primitive:
                observed_sequence.append(primitive)
        if observed_sequence != composition["ordered_relations"]:
            raise AssertionError(f"{composition['composition_id']}: ordered composition was not generated exactly")

    # Exercise the actual prequential boundary across the generated stream:
    # the evaluator object remains private until a prediction has been marked.
    gate = PrequentialGate()
    for observation, truth in zip(learner, evaluator):
        ticket = gate.begin_prediction(observation)
        with_prediction = [0.0, 0.0]
        gate.mark_prediction(ticket, with_prediction)
        feedback: TargetFeedback = gate.reveal_target(ticket, truth)
        if feedback.step_index != observation.step_index:
            raise AssertionError("feedback step mismatch")
        if hasattr(feedback, "world_id") or hasattr(feedback, "target_truth"):
            raise AssertionError("evaluator metadata leaked through target feedback")
        if feedback.target_observed is False and feedback.target_vector is not None:
            raise AssertionError("missing target must not be revealed as observed feedback")

    return {
        "valid": True,
        "step_count": len(learner),
        "evaluator_records_aligned": True,
        "learner_evaluator_boundary_valid": True,
        "prequential_order_valid": True,
        "f6_phase_sequence_preserved": True,
        "heldout_composition_phase_test_only": True,
        "extended_burst_length": len(burst_rows),
        "composition_ids_in_order": observed_comp_ids,
        "scientific_performance_scored": False,
    }


def legacy_f6_regression_anchor() -> dict[str, Any]:
    """Call the historical F6 implementation unchanged and verify its anchor contract."""
    result = case_f6()
    expected_phases = sorted(
        list(F6_WORLD_TEMPLATE["common_phases"]) + list(F6_WORLD_TEMPLATE["test_only_phases"])
    )
    checks = {
        "passed": result.get("passed") is True,
        "world_count": result.get("world_count") == 8,
        "total_rows": result.get("total_rows") == 1160,
        "phase_set": result.get("phases") == expected_phases,
        "train_seeds": result.get("train_seeds") == [110, 111, 112, 113],
        "validation_seeds": result.get("validation_seeds") == [210, 211],
        "test_seeds": result.get("test_seeds") == [310, 311],
        "heldout_composition_test_only": result.get("heldout_composition_phase_is_test_only") is True,
        "learner_evaluator_separation": result.get("evaluator_truth_and_phase_metadata_excluded_from_learner_inputs") is True,
    }
    return {
        "campaign_id": "HLG-M3-FOUNDATION-F6",
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "historical_outputs_modified": False,
        "interpretation": "historical F6 function executed unchanged as a regression anchor; no new scientific performance result",
    }


def generate_one_factor_pilot(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Generate and deterministically regenerate the separate 21-condition OFAT pilot."""
    design = manifest["factor_design"]
    profiles = design["one_factor_pilot_profiles"]
    if len(profiles) != 21:
        raise ValueError("BM-2 pilot must contain the predeclared 21 OFAT profiles")
    base = profiles[0]["profile"]
    results = []
    for pilot in profiles:
        changed = [
            key for key in base
            if pilot["profile"][key] != base[key]
        ]
        expected_changed = [] if pilot["varied_factor"] == "baseline" else [pilot["varied_factor"]]
        if changed != expected_changed:
            raise AssertionError(f"{pilot['pilot_id']}: pilot is not one-factor-at-a-time")

        world = {
            "world_id": pilot["pilot_id"],
            "split": "development_fit",
            "scenario_template_id": F6_WORLD_TEMPLATE["template_id"],
            "world_configuration_seed": pilot["world_configuration_seed"],
            "composition_ids": [row["composition_id"] for row in COMPOSITIONS["development_fit"]],
            "factor_profile": pilot["profile"],
        }
        first = generate_world_stream(world, pilot["replicate_seed"])
        second = generate_world_stream(world, pilot["replicate_seed"])
        if first["stream_sha256"] != second["stream_sha256"]:
            raise AssertionError(f"{pilot['pilot_id']}: generator is not deterministic")
        results.append({
            "pilot_id": pilot["pilot_id"],
            "varied_factor": pilot["varied_factor"],
            "profile": dict(pilot["profile"]),
            "step_count": len(first["learner_observations"]),
            "stream_sha256": first["stream_sha256"],
            "deterministic_regeneration": True,
            "boundary_valid": True,
        })

    anchor = legacy_f6_regression_anchor()
    if not anchor["all_checks_passed"]:
        raise AssertionError("historical F6 regression anchor failed")
    return {
        "campaign_id": BM2_ID,
        "schema_version": 1,
        "pilot_profile_count": len(results),
        "pilot_profiles": results,
        "legacy_f6_anchor": anchor,
        "all_pilot_streams_regenerated_identically": all(row["deterministic_regeneration"] for row in results),
        "all_pilot_boundaries_valid": all(row["boundary_valid"] for row in results),
        "confirmatory_streams_generated": False,
        "scientific_benchmark_executed": False,
        "m3_protocol_frozen": False,
        "m3_scientific_validation_complete": False,
        "claim_ceiling": "F6-derived generator determinism, factor-profile plumbing and information-boundary contract only; no learner performance or M3 scientific validation",
    }


def validate_manifest_and_generate_pilot(manifest_path: Path) -> dict[str, Any]:
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw.decode("utf-8"))
    validate_manifest(manifest)
    evidence = generate_one_factor_pilot(manifest)
    evidence["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pilot", action="store_true", help="run the small predeclared OFAT generator pilot only")
    args = parser.parse_args()
    if not args.pilot:
        parser.error("BM-2 CLI currently requires --pilot; confirmatory benchmark generation is not run here")
    evidence = validate_manifest_and_generate_pilot(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "campaign_id": evidence["campaign_id"],
        "pilot_profile_count": evidence["pilot_profile_count"],
        "all_pilot_streams_regenerated_identically": evidence["all_pilot_streams_regenerated_identically"],
        "legacy_f6_anchor_passed": evidence["legacy_f6_anchor"]["all_checks_passed"],
        "confirmatory_streams_generated": evidence["confirmatory_streams_generated"],
        "scientific_benchmark_executed": evidence["scientific_benchmark_executed"],
        "manifest_sha256": evidence["manifest_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
