"""Executable BM-0/BM-1 split and learner/evaluator boundary tests."""
from dataclasses import fields
import json
from pathlib import Path

import pytest

from rgm.experiments.hlg_m3_benchmark_contract import (
    CAMPAIGN_ID,
    EvaluatorRecord,
    LearnerObservation,
    PrequentialGate,
    TargetFeedback,
    build_manifest,
    build_reference_fixture,
    make_learner_observation,
    validate_learner_observation,
    validate_manifest,
)

MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "hybrid_leptograph_m3_benchmark_split_manifest_v0_1.json"
)


def test_static_manifest_matches_deterministic_builder():
    static = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert static == build_manifest()
    assert static["campaign_id"] == CAMPAIGN_ID


def test_predeclared_split_counts_seeds_and_world_family_coverage():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    report = validate_manifest(manifest)
    assert report["valid"] is True
    assert report["split_world_configurations"] == {
        "development_fit": 12,
        "development_validation": 8,
        "test": 20,
    }
    assert report["world_configuration_count"] == 40
    assert report["replicate_stream_count"] == 200
    for split, families in report["world_families_covered_per_split"].items():
        assert len(families) == 8, split


def test_primary_compositions_are_disjoint_and_test_atoms_are_seen_in_fit():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    report = validate_manifest(manifest)
    assert report["primary_test_compositions"] == 8
    assert report["primary_test_includes_pairs_and_triples"] is True
    assert report["all_primary_test_atoms_seen_in_fit"] is True
    ids = [
        row["composition_id"]
        for split in ("development_fit", "development_validation", "test")
        for row in manifest["composition_partitions"][split]
    ]
    assert len(ids) == len(set(ids))


def test_primitive_ood_is_separate_from_primary_composition_claim():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    auxiliary = manifest["auxiliary_primitive_ood"]
    assert auxiliary["excluded_from_primary_scoring"] is True
    assert "REL-E" not in manifest["primary_relation_atoms"]


def test_validator_rejects_incomplete_world_registry_and_seed_accounting():
    manifest = build_manifest()
    manifest["world_family_registry"]["family_ids"].pop()
    with pytest.raises(ValueError, match="world-family registry"):
        validate_manifest(manifest)

    manifest = build_manifest()
    manifest["allocation"]["total_streams"] -= 1
    with pytest.raises(ValueError, match="total replicate-stream"):
        validate_manifest(manifest)


def test_validator_rejects_incomplete_evaluator_forbidden_field_contract():
    manifest = build_manifest()
    manifest["learner_boundary"]["evaluator_fields_forbidden_in_learner"].remove("target")
    with pytest.raises(ValueError, match="forbidden field list"):
        validate_manifest(manifest)


def test_validator_rejects_duplicate_world_identity():
    manifest = build_manifest()
    manifest["worlds"][1]["world_id"] = manifest["worlds"][0]["world_id"]
    with pytest.raises(ValueError, match="world IDs"):
        validate_manifest(manifest)


def test_validator_rejects_test_composition_leakage():
    manifest = build_manifest()
    manifest["composition_partitions"]["test"][0] = dict(
        manifest["composition_partitions"]["development_fit"][0]
    )
    with pytest.raises(ValueError, match="composition"):
        validate_manifest(manifest)


def test_learner_observation_contains_only_current_permitted_fields():
    observation, evaluator = build_reference_fixture(seed=17, step_index=4)
    validate_learner_observation(observation)
    learner_fields = {item.name for item in fields(LearnerObservation)}
    assert learner_fields == {
        "step_index",
        "source_ids",
        "source_vectors",
        "source_observed",
        "context_vector",
        "context_observed",
    }
    evaluator_only = {
        "world_id", "world_family_id", "split", "world_configuration_seed",
        "replicate_seed", "composition_ids", "primitive_relations",
        "true_context_id", "latent_relation_operators", "change_schedule",
        "future_observations", "target_vector",
    }
    assert learner_fields.isdisjoint(evaluator_only)
    assert not hasattr(observation, "target_vector")
    assert hasattr(evaluator, "latent_relation_operators")


def test_observation_constructor_rejects_evaluator_metadata():
    with pytest.raises(TypeError):
        LearnerObservation(
            step_index=0,
            source_ids=(),
            source_vectors=(),
            source_observed=(),
            context_vector=None,
            context_observed=False,
            world_id="LEAKED-WORLD",
        )


def test_missing_sources_and_context_are_explicit_not_imputed():
    observation = make_learner_observation(
        step_index=1,
        source_vectors={"a": (1.0,), "b": None},
        source_observed={"a": True, "b": False},
        context_vector=None,
        context_observed=False,
    )
    assert observation.source_vectors == ((1.0,), None)
    assert observation.source_observed == (True, False)
    assert observation.context_vector is None
    assert observation.context_observed is False


def test_mask_vector_disagreement_is_rejected():
    with pytest.raises(ValueError, match="disagree"):
        make_learner_observation(
            step_index=1,
            source_vectors={"a": None},
            source_observed={"a": True},
            context_vector=None,
            context_observed=False,
        )


def test_prequential_gate_reveals_target_only_after_prediction():
    observation, evaluator = build_reference_fixture(seed=91, step_index=2)
    gate = PrequentialGate()
    ticket = gate.begin_prediction(observation)
    with pytest.raises(RuntimeError, match="before"):
        gate.reveal_target(ticket, evaluator)
    gate.mark_prediction(ticket, (0.25,))
    feedback = gate.reveal_target(ticket, evaluator)
    assert type(feedback) is TargetFeedback
    assert feedback.target_vector == evaluator.target_vector
    assert feedback.target_observed is True
    assert not hasattr(feedback, "world_id")
    assert not hasattr(feedback, "true_context_id")
    assert not hasattr(feedback, "latent_relation_operators")


def test_prequential_gate_requires_a_finite_recorded_prediction():
    observation, evaluator = build_reference_fixture(seed=90, step_index=1)
    gate = PrequentialGate()
    ticket = gate.begin_prediction(observation)
    with pytest.raises(ValueError, match="finite"):
        gate.mark_prediction(ticket, (float("nan"),))
    with pytest.raises(ValueError, match="finite"):
        gate.mark_prediction(ticket, ())
    gate.mark_prediction(ticket, (0.1, -0.2))
    with pytest.raises(RuntimeError, match="duplicated"):
        gate.mark_prediction(ticket, (0.1, -0.2))
    gate.reveal_target(ticket, evaluator)


def test_prequential_gate_requires_matching_step_and_one_open_exchange():
    observation, evaluator = build_reference_fixture(seed=92, step_index=5)
    later_observation, later_evaluator = build_reference_fixture(seed=93, step_index=6)
    gate = PrequentialGate()
    ticket = gate.begin_prediction(observation)
    with pytest.raises(RuntimeError, match="previous step"):
        gate.begin_prediction(later_observation)
    gate.mark_prediction(ticket, (0.25,))
    with pytest.raises(TypeError, match="matching evaluator"):
        gate.reveal_target(ticket, later_evaluator)
    feedback = gate.reveal_target(ticket, evaluator)
    assert feedback.step_index == 5
    next_ticket = gate.begin_prediction(later_observation)
    gate.mark_prediction(next_ticket, (0.5,))
    assert gate.reveal_target(next_ticket, later_evaluator).step_index == 6


def test_reference_fixture_is_seed_deterministic_and_not_a_scientific_world():
    obs_a, ev_a = build_reference_fixture(seed=1711)
    obs_b, ev_b = build_reference_fixture(seed=1711)
    obs_c, ev_c = build_reference_fixture(seed=1712)
    assert obs_a == obs_b
    assert ev_a == ev_b
    assert obs_a != obs_c
    assert ev_a.target_vector != ev_c.target_vector
    assert ev_a.split == "fixture"
    assert ev_a.world_family_id == "FIXTURE-ONLY"
