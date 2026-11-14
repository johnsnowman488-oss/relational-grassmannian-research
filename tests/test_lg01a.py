import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from rgm.experiments.lg01a import (
    LG01AConfig,
    _analytic_bound,
    _refresh_vector,
    _simulate_refresh_arm,
    _simulate_soe_null,
    _steps_for_tau,
    _unit_input_stream,
    exact_step,
    input_perturbation_relative_error,
    run_campaign,
)


def test_exact_zero_order_hold_update_matches_closed_form():
    gamma, dt = 0.2, 0.125
    state = np.array([1.0, -2.0], dtype=np.float64)
    forcing = np.array([0.5, 0.25], dtype=np.float64)
    updated = exact_step(state, forcing, gamma, dt)
    a = np.exp(-gamma * dt)
    b = (1.0 - a) / gamma
    np.testing.assert_allclose(updated, a * state + b * forcing, rtol=1e-14, atol=1e-14)


def test_exact_constant_input_has_correct_equilibrium_trajectory():
    gamma, dt = 0.8, 0.125
    forcing = np.array([0.0, 1.0], dtype=np.float64)
    state = np.zeros(2, dtype=np.float64)
    for step in range(40):
        state = exact_step(state, forcing, gamma, dt)
        expected = forcing * (1.0 - np.exp(-gamma * dt * (step + 1))) / gamma
        np.testing.assert_allclose(state, expected, rtol=1e-13, atol=1e-13)


def test_tagged_pulse_decays_exactly_to_e_minus_three_at_three_tau():
    for gamma in (0.01, 0.05, 0.2, 0.8):
        dt = 0.125
        steps = _steps_for_tau(gamma, 3.0, dt)
        state = np.zeros(16, dtype=np.float64)
        state[0] = 1.0
        for _ in range(steps):
            state = exact_step(state, np.zeros(16), gamma, dt)
        assert np.linalg.norm(state) == pytest.approx(np.exp(-3.0), abs=1e-13)


def test_seeded_refresh_streams_are_unit_norm_and_reproducible():
    a = _unit_input_stream(101, 0.2, 64, 16)
    b = _unit_input_stream(101, 0.2, 64, 16)
    np.testing.assert_array_equal(a, b)
    np.testing.assert_allclose(np.linalg.norm(a, axis=1), 1.0, atol=1e-14)
    assert not np.array_equal(a, _unit_input_stream(102, 0.2, 64, 16))


def test_continuous_and_intermittent_input_have_equal_squared_energy_per_block():
    base = _unit_input_stream(101, 0.2, 64, 16)
    continuous = np.asarray([_refresh_vector(base, i, "continuous_refresh") for i in range(64)])
    intermittent = np.asarray([_refresh_vector(base, i, "intermittent_refresh") for i in range(64)])
    for start in range(0, 64, 4):
        e_cont = float(np.sum(np.linalg.norm(continuous[start:start + 4], axis=1) ** 2))
        e_inter = float(np.sum(np.linalg.norm(intermittent[start:start + 4], axis=1) ** 2))
        assert e_cont == pytest.approx(e_inter, abs=1e-14)


def test_analytic_boundedness_envelope_is_respected_for_random_refresh():
    rate, dt = 0.8, 0.125
    inputs = _unit_input_stream(103, rate, 200, 16)
    state = np.zeros(16, dtype=np.float64)
    states = [state.copy()]
    for u in inputs:
        state = exact_step(state, u, rate, dt)
        states.append(state.copy())
    states = np.asarray(states)
    bounds = _analytic_bound(0.0, rate, np.arange(len(states)) * dt, 1.0)
    assert np.all(np.linalg.norm(states, axis=1) <= bounds + 1e-10)


@pytest.mark.parametrize("gamma", [0.01, 0.05, 0.2, 0.8])
def test_input_perturbation_matches_discrete_green_function(gamma):
    stream = _unit_input_stream(105, gamma, 64, 16)
    assert input_perturbation_relative_error(stream, gamma, 0.125) <= 1e-10


@pytest.mark.parametrize("arm", ["continuous_refresh", "intermittent_refresh"])
@pytest.mark.parametrize("gamma", [0.01, 0.05, 0.2, 0.8])
def test_candidate_trace_matches_independent_conventional_soe_null(arm, gamma):
    config = LG01AConfig(seeds=(101, 102, 103), min_passing_seeds=3)
    candidate = _simulate_refresh_arm(arm=arm, seed=101, rate=gamma, config=config, trace=True)
    null = _simulate_soe_null(101, gamma, config, arm=arm)
    observed = candidate["trace"]["obs_total"]
    scale = np.maximum(np.linalg.norm(null["obs_total"], axis=1), 1e-12)
    relative = np.max(np.linalg.norm(observed - null["obs_total"], axis=1) / scale)
    assert relative <= config.null_relative_tolerance
    assert candidate["all_finite"]
    assert candidate["tagged_max_relative_error"] <= config.relative_tolerance
    assert candidate["tagged_residual_at_3tau"] == pytest.approx(np.exp(-3.0), abs=1e-12)
    assert candidate["post_stop_washout_ratio_at_3tau"] == pytest.approx(np.exp(-3.0), abs=1e-12)


def test_config_rejects_non_frozen_decay_bank():
    config = LG01AConfig(decay_rates=(0.01, 0.05, 0.2, 1.0))
    with pytest.raises(ValueError, match="freezes decay_rates"):
        config.validate()


def test_small_campaign_writes_a_reproducible_auditable_bundle(tmp_path: Path):
    config = LG01AConfig(seeds=(101, 102, 103), min_passing_seeds=3)
    first = run_campaign(tmp_path / "a", run_id="test-run", config=config)
    second = run_campaign(tmp_path / "b", run_id="test-run", config=config)
    assert first["configuration_sha256"] == second["configuration_sha256"]
    assert first["gates"] == second["gates"]
    a = tmp_path / "a" / "test-run"
    b = tmp_path / "b" / "test-run"
    for name in ("seed_metrics.csv", "window_metrics.csv", "null_comparison.csv", "trace_samples.jsonl", "config.json"):
        assert (a / name).read_bytes() == (b / name).read_bytes()
    with (a / "seed_metrics.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 3 * 4 * 5
    with (a / "window_metrics.csv").open(newline="", encoding="utf-8") as stream:
        window_rows = list(csv.DictReader(stream))
    assert window_rows and {r["arm"] for r in window_rows} == {"continuous_refresh", "intermittent_refresh", "conventional_soe_null"}
    manifest = json.loads((a / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["protocol_version"] == "LG-01A-v0.1"
    assert "trace_samples.jsonl" in manifest["artifact_hashes"]
    checksum_lines = (a / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    for line in checksum_lines:
        digest, name = line.split("  ", 1)
        actual = hashlib.sha256((a / name).read_bytes()).hexdigest()
        assert digest == actual
    traces = [json.loads(line) for line in (a / "trace_samples.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {r["arm"] for r in traces} == {
        "continuous_refresh", "intermittent_refresh", "pulse_only", "conventional_soe_null"
    }
    assert all(len(r["state"]) == 16 and len(r["tagged"]) == 16 and
               len(r["refresh"]) == 16 and len(r["input"]) == 16 for r in traces)
