"""BM-2 F6-derived factor generator, pilot and boundary tests."""
import json
from pathlib import Path

import numpy as np
import pytest

from rgm.experiments.hlg_m3_benchmark_contract import (
    COMPOSITIONS,
    F6_WORLD_TEMPLATE,
    FACTOR_LEVELS,
    build_factor_design,
    build_manifest,
    build_one_factor_pilot_profiles,
    factor_profile_for_world,
    validate_manifest,
)
from rgm.experiments.hlg_m3_benchmark_generator import (
    generate_one_factor_pilot,
    generate_world_stream,
    legacy_f6_regression_anchor,
    verify_generated_stream,
)

MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "hybrid_leptograph_m3_benchmark_split_manifest_v0_1.json"
)


def test_factor_profiles_cover_all_main_effect_levels_in_each_split():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest == build_manifest()
    validate_manifest(manifest)
    for split in ("development_fit", "development_validation", "test"):
        worlds = [world for world in manifest["worlds"] if world["split"] == split]
        for factor, levels in FACTOR_LEVELS.items():
            assert {world["factor_profile"][factor] for world in worlds} == set(levels)


def test_test_split_covers_predeclared_pairwise_interactions():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    worlds = [world for world in manifest["worlds"] if world["split"] == "test"]
    expected = {
        ("context_separation_dprime", "context_bank_capacity"): 12,
        ("source_correlation", "independent_observation_probability"): 15,
        ("drift_family", "observation_noise_multiplier"): 18,
    }
    for (left, right), count in expected.items():
        pairs = {
            (world["factor_profile"][left], world["factor_profile"][right])
            for world in worlds
        }
        assert len(pairs) == count


def test_one_factor_pilot_has_baseline_and_every_factor_level():
    profiles = build_one_factor_pilot_profiles()
    assert len(profiles) == 21
    baseline = profiles[0]["profile"]
    for pilot in profiles:
        changed = [key for key in baseline if pilot["profile"][key] != baseline[key]]
        expected = [] if pilot["varied_factor"] == "baseline" else [pilot["varied_factor"]]
        assert changed == expected
    for factor, levels in FACTOR_LEVELS.items():
        assert {pilot["profile"][factor] for pilot in profiles} == set(levels)


def _world(manifest, split, local_index):
    return next(
        world for world in manifest["worlds"]
        if world["split"] == split and world["world_id"].endswith(f"W{local_index + 1:02d}")
    )


def test_generator_is_deterministic_and_preserves_f6_phase_sequence_for_fit():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    world = _world(manifest, "development_fit", 0)
    a = generate_world_stream(world, world["replicate_seeds"][0])
    b = generate_world_stream(world, world["replicate_seeds"][0])
    assert a["stream_sha256"] == b["stream_sha256"]
    assert a["phase_first_seen"] == list(F6_WORLD_TEMPLATE["common_phases"]) + [
        "extended_burst_gap", "extended_reactivation", "composition_extension"
    ]
    assert verify_generated_stream(a)["valid"] is True


def test_test_generator_keeps_historical_f6_composition_test_only_and_generates_new_compositions():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    world = _world(manifest, "test", 0)
    stream = generate_world_stream(world, world["replicate_seeds"][0])
    phases = stream["phase_first_seen"]
    assert phases[:8] == list(F6_WORLD_TEMPLATE["common_phases"]) + list(F6_WORLD_TEMPLATE["test_only_phases"])
    assert phases[-1] == "composition_extension"
    assert set(stream["composition_ids"]) == {
        row["composition_id"] for row in COMPOSITIONS["test"]
    }
    assert verify_generated_stream(stream)["heldout_composition_phase_test_only"] is True


def test_exact_collinearity_and_burst_masks_are_materialised():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    world = next(
        w for w in manifest["worlds"]
        if w["split"] == "test" and w["factor_profile"]["source_correlation"] == 1.0
    )
    stream = generate_world_stream(world, world["replicate_seeds"][0])
    for obs in stream["learner_observations"]:
        if obs.source_observed == (True, True):
            assert np.array_equal(np.asarray(obs.source_vectors[0]), np.asarray(obs.source_vectors[1]))
    burst = [
        (obs, truth)
        for obs, truth in zip(stream["learner_observations"], stream["evaluator_records"])
        if truth.phase_id == "extended_burst_gap"
    ]
    assert len(burst) == world["factor_profile"]["burst_outage_steps"]
    assert all(not any(obs.source_observed) and not obs.context_observed and not ev.target_observed for obs, ev in burst)


def test_evaluator_truth_retained_when_target_is_missing_but_feedback_does_not_reveal_it():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    world = next(
        w for w in manifest["worlds"]
        if w["split"] == "test" and w["factor_profile"]["independent_observation_probability"] < 1.0
    )
    stream = generate_world_stream(world, world["replicate_seeds"][0])
    missing = next(
        (obs, ev) for obs, ev in zip(stream["learner_observations"], stream["evaluator_records"])
        if not ev.target_observed
    )
    obs, ev = missing
    assert ev.target_truth is not None
    assert ev.target_vector is None
    assert not hasattr(obs, "target_truth")


def test_legacy_f6_anchor_runs_unchanged():
    anchor = legacy_f6_regression_anchor()
    assert anchor["all_checks_passed"] is True
    assert anchor["checks"]["world_count"] is True
    assert anchor["checks"]["total_rows"] is True
    assert anchor["historical_outputs_modified"] is False


def test_bm2_ofat_generator_pilot_emits_contract_evidence_only():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    evidence = generate_one_factor_pilot(manifest)
    assert evidence["pilot_profile_count"] == 21
    assert evidence["all_pilot_streams_regenerated_identically"] is True
    assert evidence["all_pilot_boundaries_valid"] is True
    assert evidence["confirmatory_streams_generated"] is False
    assert evidence["scientific_benchmark_executed"] is False
    assert evidence["legacy_f6_anchor"]["all_checks_passed"] is True
    assert evidence["m3_scientific_validation_complete"] is False
