"""BM-0/BM-1 split-manifest and learner/evaluator boundary contract.

This module deliberately implements a contract fixture, not the full eight-world
scientific generator. The latter is a BM-2 deliverable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

CAMPAIGN_ID = "HLG-M3-BROAD-BENCHMARK-BM0-BM1-v0.1"
SCHEMA_VERSION = 1
SPLIT_COUNTS = {
    "development_fit": 12,
    "development_validation": 8,
    "test": 20,
}
REPLICATES_PER_WORLD = 5
F6_WORLD_TEMPLATE = {
    "template_id": "F6-INTEGRATED-SEQUENTIAL-v1",
    "source_evidence": "F6",
    "historical_world_count": 8,
    "historical_split_counts": {"development_fit": 4, "development_validation": 2, "test": 2},
    "historical_seed_sets": {
        "development_fit": [110, 111, 112, 113],
        "development_validation": [210, 211],
        "test": [310, 311],
    },
    "common_phases": [
        "acquisition", "distractor", "context_switch", "relation2_isolation",
        "observation_gap", "reactivation", "within_context_drift",
    ],
    "test_only_phases": ["heldout_composition"],
    "steps_per_phase": 20,
    "historical_seeds_reused_in_confirmatory_campaign": False,
}
F5_RESOURCE_ENVELOPE = {
    "source_evidence": "F5 in docs/hybrid_leptograph_m3_foundation_campaign_results.md",
    "reference_state_dimension_scalars": 64,
    "precision": "float64",
    "persistent_state_cap_bytes": 512,
    "trainable_parameter_cap": 4096,
    "update_multiply_add_cap_per_observed_update": 8192,
    "query_multiply_add_cap_per_prediction": 4096,
    "C0_role": "zero-persistent-memory-reference-floor-not-equal-used-memory",
    "comparison_policy": "common-hard-ceilings-with-actual-use-and-measured-pareto-frontiers",
    "status": "provisional_F5_ceiling_to_be_audited_on_actual_C0_C4_implementations_in_BM4",
}
PRIMARY_ATOMS = ("REL-A", "REL-B", "REL-C", "REL-D")
SEED_BASES = {
    "development_fit": 110_000,
    "development_validation": 220_000,
    "test": 330_000,
}
WORLD_SEED_BASE = 910_000
FORBIDDEN_LEARNER_FIELDS = (
    "world_id", "scenario_template_id", "split", "seed",
    "world_configuration_seed", "replicate_seed", "composition_ids",
    "primitive_relations", "true_context_id", "latent_relation_operators",
    "change_schedule", "future_observations", "target",
)

FACTOR_LEVELS = {
    "source_correlation": [0.0, 0.5, 0.9, 0.99, 1.0],
    "context_separation_dprime": [4.0, 2.0, 1.0, 0.5],
    "context_bank_capacity": [2, 4, 8],
    "independent_observation_probability": [1.0, 0.95, 0.8],
    "burst_outage_steps": [20, 50, 100],
    "drift_family": ["stationary", "step", "gradual", "variance_only", "transient", "compound"],
    "observation_noise_multiplier": [1.0, 2.0, 4.0],
}
PILOT_SEED_BASE = 970_000
PILOT_CONFIGURATION_SEED_BASE = 980_000


def factor_profile_for_world(split: str, local_index: int) -> dict:
    """Deterministic balanced partial-factorial profile; never a full Cartesian grid."""
    if split not in SPLIT_COUNTS or local_index < 0 or local_index >= SPLIT_COUNTS[split]:
        raise ValueError("unknown split or out-of-range split-local world index")
    levels = FACTOR_LEVELS
    j = local_index
    return {
        "source_correlation": levels["source_correlation"][j % 5],
        "context_separation_dprime": levels["context_separation_dprime"][j % 4],
        "context_bank_capacity": levels["context_bank_capacity"][(j // 4) % 3],
        "independent_observation_probability": levels["independent_observation_probability"][(j // 5) % 3],
        "burst_outage_steps": levels["burst_outage_steps"][j % 3],
        "drift_family": levels["drift_family"][j % 6],
        "observation_noise_multiplier": levels["observation_noise_multiplier"][(j // 6) % 3],
    }


def build_one_factor_pilot_profiles() -> list[dict]:
    """Baseline plus every non-baseline level of one factor at a time."""
    baseline = {
        key: values[0] for key, values in FACTOR_LEVELS.items()
    }
    profiles = [{
        "pilot_id": "PILOT-BASELINE",
        "varied_factor": "baseline",
        "profile": dict(baseline),
        "world_configuration_seed": PILOT_CONFIGURATION_SEED_BASE,
        "replicate_seed": PILOT_SEED_BASE,
    }]
    ordinal = 1
    for factor, values in FACTOR_LEVELS.items():
        for value in values[1:]:
            profile = dict(baseline)
            profile[factor] = value
            profiles.append({
                "pilot_id": f"PILOT-{factor.upper()}-{ordinal:02d}",
                "varied_factor": factor,
                "profile": profile,
                "world_configuration_seed": PILOT_CONFIGURATION_SEED_BASE + ordinal,
                "replicate_seed": PILOT_SEED_BASE + ordinal,
            })
            ordinal += 1
    return profiles


def build_factor_design() -> dict:
    return {
        "method": "deterministic_balanced_partial_factorial_with_separate_ofat_pilot",
        "factor_levels": deepcopy(FACTOR_LEVELS),
        "world_profile_assignment": {
            "source_correlation": "correlation_levels[split_local_index % 5]",
            "independent_observation_probability": "missingness_levels[(split_local_index // 5) % 3]",
            "context_separation_dprime": "context_levels[split_local_index % 4]",
            "context_bank_capacity": "capacity_levels[(split_local_index // 4) % 3]",
            "drift_family": "drift_levels[split_local_index % 6]",
            "observation_noise_multiplier": "noise_levels[(split_local_index // 6) % 3]",
            "burst_outage_steps": "outage_levels[split_local_index % 3]",
        },
        "predeclared_pairwise_interactions": [
            ["context_separation_dprime", "context_bank_capacity"],
            ["source_correlation", "independent_observation_probability"],
            ["drift_family", "observation_noise_multiplier"],
        ],
        "pairwise_coverage_policy": {
            "test_split": "all combinations covered for context separation x capacity and drift x noise; 15 of 15 combinations covered for source correlation x missingness",
            "development_splits": "main-effect levels covered; interaction coverage is descriptive and not represented as complete",
        },
        "one_factor_pilot_profiles": build_one_factor_pilot_profiles(),
        "pilot_is_separate_from_confirmatory_streams": True,
        "full_cartesian_product_run": False,
    }


COMPOSITIONS = {
    "development_fit": [
        {"composition_id": "FIT-AB", "ordered_relations": ["REL-A", "REL-B"]},
        {"composition_id": "FIT-BC", "ordered_relations": ["REL-B", "REL-C"]},
        {"composition_id": "FIT-CD", "ordered_relations": ["REL-C", "REL-D"]},
        {"composition_id": "FIT-DA", "ordered_relations": ["REL-D", "REL-A"]},
    ],
    "development_validation": [
        {"composition_id": "VAL-AC", "ordered_relations": ["REL-A", "REL-C"]},
        {"composition_id": "VAL-BD", "ordered_relations": ["REL-B", "REL-D"]},
    ],
    "test": [
        {"composition_id": "TEST-BA", "ordered_relations": ["REL-B", "REL-A"]},
        {"composition_id": "TEST-CB", "ordered_relations": ["REL-C", "REL-B"]},
        {"composition_id": "TEST-DC", "ordered_relations": ["REL-D", "REL-C"]},
        {"composition_id": "TEST-AD", "ordered_relations": ["REL-A", "REL-D"]},
        {"composition_id": "TEST-ABC", "ordered_relations": ["REL-A", "REL-B", "REL-C"]},
        {"composition_id": "TEST-BCD", "ordered_relations": ["REL-B", "REL-C", "REL-D"]},
        {"composition_id": "TEST-CDA", "ordered_relations": ["REL-C", "REL-D", "REL-A"]},
        {"composition_id": "TEST-DAB", "ordered_relations": ["REL-D", "REL-A", "REL-B"]},
    ],
}


def build_manifest() -> dict:
    """Build the deterministic, evaluator-only split manifest."""
    worlds = []
    ordinal = 0
    for split, count in SPLIT_COUNTS.items():
        split_composition_ids = [item["composition_id"] for item in COMPOSITIONS[split]]
        for local_index in range(count):
            world_id = f"{split.upper()}-W{local_index + 1:02d}"
            replicate_seeds = [
                SEED_BASES[split] + ordinal * 10 + replicate
                for replicate in range(REPLICATES_PER_WORLD)
            ]
            worlds.append({
                "world_id": world_id,
                "split": split,
                "scenario_template_id": F6_WORLD_TEMPLATE["template_id"],
                "world_configuration_seed": WORLD_SEED_BASE + ordinal,
                "replicate_seeds": replicate_seeds,
                "composition_ids": split_composition_ids,
                "factor_profile": factor_profile_for_world(split, local_index),
            })
            ordinal += 1

    return {
        "campaign_id": CAMPAIGN_ID,
        "schema_version": SCHEMA_VERSION,
        "status": "draft_amendable_not_frozen",
        "primary_relation_atoms": list(PRIMARY_ATOMS),
        "world_template": deepcopy(F6_WORLD_TEMPLATE),
        "resource_envelope": dict(F5_RESOURCE_ENVELOPE),
        "factor_design": build_factor_design(),
        "allocation": {
            "world_configurations_per_split": dict(SPLIT_COUNTS),
            "replicates_per_world": REPLICATES_PER_WORLD,
            "total_world_configurations": sum(SPLIT_COUNTS.values()),
            "total_streams": sum(SPLIT_COUNTS.values()) * REPLICATES_PER_WORLD,
        },
        "seed_policy": {
            "world_configuration_seed_base": WORLD_SEED_BASE,
            "replicate_seed_bases": dict(SEED_BASES),
            "replicate_seed_formula": "split_base + global_world_ordinal * 10 + replicate_index",
            "replicate_index_range": [0, REPLICATES_PER_WORLD - 1],
            "all_configuration_and_replicate_seeds_must_be_unique": True,
        },
        "composition_partitions": {
            split: deepcopy(COMPOSITIONS[split])
            for split in SPLIT_COUNTS
        },
        "auxiliary_primitive_ood": {
            "stratum_id": "AUX-REL-E-PRIMITIVE-OOD",
            "relation_atoms": ["REL-E", "REL-A"],
            "composition_ids": ["AUX-EA"],
            "excluded_from_primary_scoring": True,
            "interpretation": "separate primitive-OOD question; never pool with primary composition-generalisation results",
        },
        "worlds": worlds,
        "learner_boundary": {
            "learner_observation_type": "LearnerObservation",
            "evaluator_record_type": "EvaluatorRecord",
            "target_revealed_only_after_prediction": True,
            "evaluator_fields_forbidden_in_learner": [
                "world_id", "scenario_template_id", "split", "seed",
                "world_configuration_seed", "replicate_seed", "composition_ids",
                "primitive_relations", "true_context_id", "latent_relation_operators",
                "change_schedule", "future_observations", "target",
            ],
        },
        "claim_limits": {
            "topology": "fixed_candidate_topology",
            "topology_birth_death": False,
            "causal_attribution": False,
            "m4_global_coupled_stability": False,
            "m3_scientific_validation_complete": False,
        },
    }


def validate_manifest(manifest: Mapping) -> dict:
    """Raise ValueError on any split, seed, or composition leakage defect."""
    if manifest.get("campaign_id") != CAMPAIGN_ID:
        raise ValueError("campaign_id mismatch")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported manifest schema_version")
    if manifest.get("status") != "draft_amendable_not_frozen":
        raise ValueError("manifest must remain draft and amendable")

    if manifest.get("world_template") != F6_WORLD_TEMPLATE:
        raise ValueError("world template must preserve the historical F6 eight-world scenario structure")

    if manifest.get("resource_envelope") != F5_RESOURCE_ENVELOPE:
        raise ValueError("provisional F5 common resource envelope mismatch")

    if manifest.get("factor_design") != build_factor_design():
        raise ValueError("factor-level design or one-factor pilot differs from its predeclared contract")

    allocation = manifest.get("allocation", {})
    if allocation.get("world_configurations_per_split") != SPLIT_COUNTS:
        raise ValueError("world allocation differs from the predeclared split counts")
    if allocation.get("replicates_per_world") != REPLICATES_PER_WORLD:
        raise ValueError("replicate count mismatch")
    if allocation.get("total_world_configurations") != sum(SPLIT_COUNTS.values()):
        raise ValueError("total world-configuration count mismatch")
    if allocation.get("total_streams") != sum(SPLIT_COUNTS.values()) * REPLICATES_PER_WORLD:
        raise ValueError("total replicate-stream count mismatch")

    seed_policy = manifest.get("seed_policy", {})
    if seed_policy.get("world_configuration_seed_base") != WORLD_SEED_BASE:
        raise ValueError("world-configuration seed base mismatch")
    if seed_policy.get("replicate_seed_bases") != SEED_BASES:
        raise ValueError("replicate seed bases mismatch")
    if seed_policy.get("replicate_index_range") != [0, REPLICATES_PER_WORLD - 1]:
        raise ValueError("replicate seed index range mismatch")
    if seed_policy.get("all_configuration_and_replicate_seeds_must_be_unique") is not True:
        raise ValueError("global seed uniqueness must be required")

    worlds = manifest.get("worlds")
    if not isinstance(worlds, list) or len(worlds) != sum(SPLIT_COUNTS.values()):
        raise ValueError("world list has incorrect size")

    historical_seeds = {
        seed for seeds in F6_WORLD_TEMPLATE["historical_seed_sets"].values() for seed in seeds
    }
    ids, config_seeds, replicate_seeds = set(), set(), set()
    split_world_counts = {key: 0 for key in SPLIT_COUNTS}
    ordinal = 0
    for split, count in SPLIT_COUNTS.items():
        expected_compositions = [item["composition_id"] for item in COMPOSITIONS[split]]
        split_worlds = [world for world in worlds if world.get("split") == split]
        if len(split_worlds) != count:
            raise ValueError(f"{split}: wrong number of world configurations")
        split_world_counts[split] = len(split_worlds)

        for local_index, world in enumerate(split_worlds):
            world_id = world.get("world_id")
            if not isinstance(world_id, str) or world_id in ids:
                raise ValueError("world IDs must be non-empty and globally unique")
            ids.add(world_id)
            if world.get("composition_ids") != expected_compositions:
                raise ValueError(f"{world_id}: composition assignment does not match split")
            if world.get("scenario_template_id") != F6_WORLD_TEMPLATE["template_id"]:
                raise ValueError(f"{world_id}: unknown or inconsistent scenario template")
            if world.get("factor_profile") != factor_profile_for_world(split, local_index):
                raise ValueError(f"{world_id}: factor profile does not match deterministic split allocation")

            config_seed = world.get("world_configuration_seed")
            if config_seed in historical_seeds:
                raise ValueError("historical F6 anchor seeds must not be reused in the confirmatory campaign")
            if not isinstance(config_seed, int) or config_seed in config_seeds:
                raise ValueError("world configuration seeds must be unique integers")
            config_seeds.add(config_seed)

            expected_config_seed = WORLD_SEED_BASE + ordinal
            if config_seed != expected_config_seed:
                raise ValueError("world configuration seed does not match deterministic manifest policy")
            observed_replicates = world.get("replicate_seeds", [])
            if any(seed in historical_seeds for seed in observed_replicates):
                raise ValueError("historical F6 anchor seeds must not be reused in the confirmatory campaign")
            expected_replicate_seeds = [
                SEED_BASES[split] + ordinal * 10 + replicate
                for replicate in range(REPLICATES_PER_WORLD)
            ]
            if world.get("replicate_seeds") != expected_replicate_seeds:
                raise ValueError(f"{world_id}: replicate seed formula mismatch")
            for seed in expected_replicate_seeds:
                if seed in replicate_seeds or seed in config_seeds:
                    raise ValueError("replicate seeds must be globally unique")
                replicate_seeds.add(seed)
            ordinal += 1

    historical_seeds = {
        seed for seeds in F6_WORLD_TEMPLATE["historical_seed_sets"].values() for seed in seeds
    }
    if historical_seeds.intersection(config_seeds | replicate_seeds):
        raise ValueError("historical F6 anchor seeds must not be reused in the confirmatory campaign")

    partitions = manifest.get("composition_partitions", {})
    composition_ids, composition_sequences = set(), set()
    atoms_by_split = {}
    for split in SPLIT_COUNTS:
        rows = partitions.get(split)
        if rows != COMPOSITIONS[split]:
            raise ValueError(f"{split}: composition partition differs from its declared contract")
        atoms_by_split[split] = set()
        for row in rows:
            cid = row["composition_id"]
            sequence = tuple(row["ordered_relations"])
            if cid in composition_ids:
                raise ValueError("composition IDs must be disjoint across splits")
            if sequence in composition_sequences:
                raise ValueError("ordered relation compositions must be disjoint across splits")
            if len(sequence) not in (2, 3) or any(atom not in PRIMARY_ATOMS for atom in sequence):
                raise ValueError(f"{cid}: invalid primary relation composition")
            composition_ids.add(cid)
            composition_sequences.add(sequence)
            atoms_by_split[split].update(sequence)

    if atoms_by_split["development_fit"] != set(PRIMARY_ATOMS):
        raise ValueError("all primary primitive atoms must occur during development fit")
    if not atoms_by_split["test"].issubset(atoms_by_split["development_fit"]):
        raise ValueError("primary test includes a primitive not seen during fit")
    if len([row for row in COMPOSITIONS["test"] if len(row["ordered_relations"]) == 2]) != 4:
        raise ValueError("primary test must include four held-out ordered pairs")
    if len([row for row in COMPOSITIONS["test"] if len(row["ordered_relations"]) == 3]) != 4:
        raise ValueError("primary test must include four held-out triples")

    auxiliary = manifest.get("auxiliary_primitive_ood", {})
    if auxiliary.get("excluded_from_primary_scoring") is not True:
        raise ValueError("primitive-OOD stratum must be excluded from primary scoring")
    if "REL-E" not in auxiliary.get("relation_atoms", []):
        raise ValueError("auxiliary primitive-OOD stratum must introduce REL-E")

    boundary = manifest.get("learner_boundary", {})
    if boundary.get("learner_observation_type") != "LearnerObservation":
        raise ValueError("learner observation type mismatch")
    if boundary.get("evaluator_record_type") != "EvaluatorRecord":
        raise ValueError("evaluator record type mismatch")
    if boundary.get("target_revealed_only_after_prediction") is not True:
        raise ValueError("target feedback must be prequential")
    if set(boundary.get("evaluator_fields_forbidden_in_learner", [])) != set(FORBIDDEN_LEARNER_FIELDS):
        raise ValueError("evaluator-only forbidden field list is incomplete or contains unexpected fields")

    limits = manifest.get("claim_limits", {})
    if limits.get("topology") != "fixed_candidate_topology":
        raise ValueError("M3 topology must remain fixed")
    if limits.get("topology_birth_death") is not False:
        raise ValueError("topology birth/death is outside M3")
    if limits.get("m4_global_coupled_stability") is not False:
        raise ValueError("M4 global coupled stability cannot be claimed in M3")
    if limits.get("m3_scientific_validation_complete") is not False:
        raise ValueError("BM-0/BM-1 cannot declare M3 scientifically complete")

    return {
        "valid": True,
        "split_world_configurations": split_world_counts,
        "world_configuration_count": len(ids),
        "replicate_stream_count": len(replicate_seeds),
        "replicates_per_world": REPLICATES_PER_WORLD,
        "scenario_template_id": F6_WORLD_TEMPLATE["template_id"],
        "historical_f6_world_count": F6_WORLD_TEMPLATE["historical_world_count"],
        "resource_envelope": dict(F5_RESOURCE_ENVELOPE),
        "factor_design": build_factor_design(),
        "primary_composition_counts": {
            split: len(COMPOSITIONS[split]) for split in SPLIT_COUNTS
        },
        "primary_test_compositions": 8,
        "primary_test_includes_pairs_and_triples": True,
        "all_primary_test_atoms_seen_in_fit": True,
        "primitive_ood_separately_excluded": True,
        "learner_evaluator_boundary_contract_present": True,
        "m3_protocol_frozen": False,
        "m3_scientific_validation_complete": False,
    }


@dataclass(frozen=True)
class LearnerObservation:
    """Current observable inputs only; no target or evaluator metadata."""
    step_index: int
    source_ids: tuple[str, ...]
    source_vectors: tuple[tuple[float, ...] | None, ...]
    source_observed: tuple[bool, ...]
    context_vector: tuple[float, ...] | None
    context_observed: bool

    def __post_init__(self) -> None:
        if self.step_index < 0:
            raise ValueError("step_index must be non-negative")
        if tuple(sorted(self.source_ids)) != self.source_ids or len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("source_ids must be unique and sorted")
        if not (len(self.source_ids) == len(self.source_vectors) == len(self.source_observed)):
            raise ValueError("source IDs, vectors and observation masks must have equal length")
        for source_id, vector, observed in zip(self.source_ids, self.source_vectors, self.source_observed):
            if not source_id:
                raise ValueError("source IDs must be non-empty")
            if not isinstance(observed, bool):
                raise ValueError("source observation masks must be booleans")
            if observed != (vector is not None):
                raise ValueError(f"{source_id}: missingness mask and vector disagree")
            if vector is not None and (not vector or any(not math.isfinite(float(v)) for v in vector)):
                raise ValueError(f"{source_id}: observed source vector must be finite and non-empty")
        if not isinstance(self.context_observed, bool):
            raise ValueError("context_observed must be boolean")
        if self.context_observed != (self.context_vector is not None):
            raise ValueError("context missingness mask and vector disagree")
        if self.context_vector is not None and (
            not self.context_vector or any(not math.isfinite(float(v)) for v in self.context_vector)
        ):
            raise ValueError("observed context vector must be finite and non-empty")


@dataclass(frozen=True)
class EvaluatorRecord:
    """Evaluator-owned truth. Never pass this object to learner functions."""
    step_index: int
    world_id: str
    scenario_template_id: str
    split: str
    world_configuration_seed: int
    replicate_seed: int
    composition_ids: tuple[str, ...]
    primitive_relations: tuple[str, ...]
    true_context_id: str | None
    latent_relation_operators: tuple[tuple[str, tuple[float, ...]], ...]
    change_schedule: tuple[tuple[int, str], ...]
    target_vector: tuple[float, ...] | None
    target_observed: bool
    target_truth: tuple[float, ...] | None = None
    phase_id: str = ""
    composition_id: str | None = None

    def __post_init__(self) -> None:
        if self.step_index < 0:
            raise ValueError("step_index must be non-negative")
        if self.target_observed != (self.target_vector is not None):
            raise ValueError("target missingness mask and target vector disagree")
        if self.target_vector is not None and (
            not self.target_vector or any(not math.isfinite(float(v)) for v in self.target_vector)
        ):
            raise ValueError("observed target must be finite and non-empty")
        if self.target_truth is not None and (
            not self.target_truth or any(not math.isfinite(float(v)) for v in self.target_truth)
        ):
            raise ValueError("evaluator target truth must be finite and non-empty")


@dataclass(frozen=True)
class PredictionTicket:
    step_index: int


@dataclass(frozen=True)
class TargetFeedback:
    """Only the current target and its observation flag are exposed to learner."""
    step_index: int
    target_vector: tuple[float, ...] | None
    target_observed: bool


def make_learner_observation(
    *,
    step_index: int,
    source_vectors: Mapping[str, Sequence[float] | None],
    source_observed: Mapping[str, bool],
    context_vector: Sequence[float] | None,
    context_observed: bool,
) -> LearnerObservation:
    if set(source_vectors) != set(source_observed):
        raise ValueError("source vectors and masks must have identical source IDs")
    ids = tuple(sorted(source_vectors))
    vectors = tuple(
        None if source_vectors[key] is None else tuple(float(x) for x in source_vectors[key])
        for key in ids
    )
    masks = tuple(source_observed[key] for key in ids)
    context = None if context_vector is None else tuple(float(x) for x in context_vector)
    return LearnerObservation(step_index, ids, vectors, masks, context, context_observed)


def validate_learner_observation(observation: LearnerObservation) -> None:
    if type(observation) is not LearnerObservation:
        raise TypeError("learner APIs accept LearnerObservation only; evaluator metadata is forbidden")


class PrequentialGate:
    """Enforce prediction-before-target feedback for one outstanding step."""
    def __init__(self) -> None:
        self._pending_step: int | None = None
        self._prediction_recorded = False
        self._prediction: tuple[float, ...] | None = None
        self._last_resolved_step = -1

    def begin_prediction(self, observation: LearnerObservation) -> PredictionTicket:
        validate_learner_observation(observation)
        if self._pending_step is not None:
            raise RuntimeError("previous step has not received target feedback")
        if observation.step_index <= self._last_resolved_step:
            raise RuntimeError("step indices must increase strictly")
        self._pending_step = observation.step_index
        self._prediction_recorded = False
        self._prediction = None
        return PredictionTicket(observation.step_index)

    def mark_prediction(self, ticket: PredictionTicket, prediction: Sequence[float]) -> None:
        if type(ticket) is not PredictionTicket or self._pending_step != ticket.step_index or self._prediction_recorded:
            raise RuntimeError("prediction ticket is stale, duplicated or out of sequence")
        values = tuple(float(value) for value in prediction)
        if not values or any(not math.isfinite(value) for value in values):
            raise ValueError("recorded prediction must be a non-empty finite vector")
        self._prediction = values
        self._prediction_recorded = True

    def reveal_target(self, ticket: PredictionTicket, evaluator: EvaluatorRecord) -> TargetFeedback:
        if self._pending_step != ticket.step_index or not self._prediction_recorded:
            raise RuntimeError("target cannot be revealed before the matching prediction")
        if type(evaluator) is not EvaluatorRecord or evaluator.step_index != ticket.step_index:
            raise TypeError("matching evaluator record is required after prediction")
        feedback = TargetFeedback(
            step_index=evaluator.step_index,
            target_vector=evaluator.target_vector,
            target_observed=evaluator.target_observed,
        )
        self._last_resolved_step = ticket.step_index
        self._pending_step = None
        self._prediction_recorded = False
        self._prediction = None
        return feedback


def build_reference_fixture(seed: int = 1701, step_index: int = 0) -> tuple[LearnerObservation, EvaluatorRecord]:
    """Generate one deterministic contract fixture; not a scientific M3 world."""
    import random

    rng = random.Random(seed)
    source_a, source_b = rng.gauss(0.0, 1.0), rng.gauss(0.0, 1.0)
    context_0, context_1 = rng.gauss(0.0, 1.0), rng.gauss(0.0, 1.0)
    target = 0.7 * source_a - 0.35 * source_b + 0.1 * context_0 + rng.gauss(0.0, 0.02)
    observation = make_learner_observation(
        step_index=step_index,
        source_vectors={"source_a": (source_a,), "source_b": (source_b,)},
        source_observed={"source_a": True, "source_b": True},
        context_vector=(context_0, context_1),
        context_observed=True,
    )
    evaluator = EvaluatorRecord(
        step_index=step_index,
        world_id="CONTRACT-FIXTURE",
        scenario_template_id="FIXTURE-ONLY",
        split="fixture",
        world_configuration_seed=seed,
        replicate_seed=seed,
        composition_ids=("FIXTURE-A-B",),
        primitive_relations=("REL-A", "REL-B"),
        true_context_id="FIXTURE-CONTEXT-0",
        latent_relation_operators=(("REL-A", (0.7,)), ("REL-B", (-0.35,))),
        change_schedule=(),
        target_vector=(target,),
        target_observed=True,
    )
    return observation, evaluator


def validate_manifest_file(path: Path) -> dict:
    raw = path.read_bytes()
    manifest = json.loads(raw.decode("utf-8"))
    validation = validate_manifest(manifest)
    return {
        "campaign_id": CAMPAIGN_ID,
        "schema_version": SCHEMA_VERSION,
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "validation": validation,
        "scientific_status": "NOT_RUN_BM0_BM1_CONTRACT_CHECKS_ONLY",
        "claim_ceiling": "manifest and information-boundary contract only; no scientific M3 validation",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate_manifest_file(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    args.output.write_text(payload, encoding="utf-8")
    print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
