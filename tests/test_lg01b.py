from __future__ import annotations

import inspect
import json

import numpy as np
import pytest
from scipy.linalg import expm

from rgm.experiments import lg01b as lg


def _cycle_plus_skip() -> np.ndarray:
    graph = np.zeros((lg.N_MODES, lg.N_MODES), dtype=np.int8)
    for source in range(lg.N_MODES):
        graph[source, (source + 1) % lg.N_MODES] = 1
        graph[source, (source + 2) % lg.N_MODES] = 1
    return graph


def _small_episode(seed: int, steps: int = 60) -> np.ndarray:
    rng = np.random.default_rng(seed)
    values = rng.standard_normal((steps + 1, lg.N_MODES, lg.FEATURE_DIM))
    # Smooth the random path so tangent features remain well-scaled.
    for index in range(1, values.shape[0]):
        values[index] = 0.8 * values[index - 1] + 0.2 * values[index]
    return values.astype(np.float64)


def test_config_freezes_the_registered_design() -> None:
    config = lg.LG01BConfig()
    config.validate()
    assert config.rates == (0.05, 0.20)
    assert config.world_seeds == tuple(range(301, 331))
    with pytest.raises(ValueError, match="frozen"):
        lg.LG01BConfig(coupling_ratio=0.06).validate()
    with pytest.raises(ValueError, match="frozen"):
        lg.LG01BConfig(rates=(0.05, 0.20, 0.80)).validate()


def test_hidden_graph_is_deterministic_strongly_connected_and_two_out() -> None:
    first, rejected_first = lg.generate_hidden_graph(301)
    second, rejected_second = lg.generate_hidden_graph(301)
    assert np.array_equal(first, second)
    assert rejected_first == rejected_second
    assert np.all(first.sum(axis=1) == 2)
    assert np.all(np.diag(first) == 0)
    assert lg.is_strongly_connected(first)


def test_graph_direction_convention_is_source_row_destination_column() -> None:
    graph = np.zeros((lg.N_MODES, lg.N_MODES), dtype=np.int8)
    graph[0, 1] = 1
    rotation = np.eye(lg.FEATURE_DIM)
    f_matrix, _, _ = lg.build_transition(graph, rotation, 0.05)
    coupling = lg.COUPLING_RATIO * 0.05
    # Destination-1 state receives the source-0 block under node-major stacking.
    assert np.allclose(f_matrix[16:32, 0:16], coupling * rotation)
    assert np.allclose(f_matrix[0:16, 16:32], 0.0)


def test_orthogonal_transform_is_deterministic_and_orthogonal() -> None:
    first = lg.generate_orthogonal_transform(307)
    second = lg.generate_orthogonal_transform(307)
    assert np.array_equal(first, second)
    assert np.allclose(first.T @ first, np.eye(lg.FEATURE_DIM), atol=2e-12, rtol=0.0)


def test_exact_zoh_transition_matches_independent_augmented_exponential() -> None:
    graph = _cycle_plus_skip()
    rotation = lg.generate_orthogonal_transform(301)
    f_matrix, a_matrix, b_matrix = lg.build_transition(graph, rotation, 0.05)
    size = lg.N_MODES * lg.FEATURE_DIM
    augmented = np.zeros((2 * size, 2 * size), dtype=np.float64)
    augmented[:size, :size] = f_matrix
    augmented[:size, size:] = np.eye(size)
    reference = expm(augmented * lg.DT)
    assert np.allclose(a_matrix, reference[:size, :size], rtol=2e-12, atol=2e-14)
    assert np.allclose(b_matrix, reference[:size, size:], rtol=2e-11, atol=2e-13)


def test_stability_bound_and_discrete_transition_are_strictly_stable() -> None:
    graph, _ = lg.generate_hidden_graph(311)
    rotation = lg.generate_orthogonal_transform(311)
    f_matrix, a_matrix, _ = lg.build_transition(graph, rotation, 0.20)
    diagnostics = lg.stability_diagnostics(f_matrix, a_matrix)
    assert diagnostics["symmetric_dissipativity_margin"] > 0.0
    assert diagnostics["transition_spectral_radius"] < 1.0
    assert 0.05 * np.sqrt(14.0) < 1.0


def test_input_batches_are_deterministic_unit_norm_and_split_separated() -> None:
    train, train_seeds = lg.generate_unit_input_batch(301, "train", 50)
    replay, replay_seeds = lg.generate_unit_input_batch(301, "train", 50)
    validation, validation_seeds = lg.generate_unit_input_batch(301, "validation", 50)
    assert np.array_equal(train, replay)
    assert train_seeds == replay_seeds
    assert train_seeds != validation_seeds
    norms = np.linalg.norm(train, axis=2)
    assert np.allclose(norms, 1.0, atol=2e-14, rtol=0.0)


def test_null_simulation_matches_scalar_exact_soe_update() -> None:
    zero_graph = np.zeros((lg.N_MODES, lg.N_MODES), dtype=np.int8)
    rotation = lg.generate_orthogonal_transform(301)
    inputs, _ = lg.generate_unit_input_batch(301, "train", 13)
    states = lg.simulate_episode(zero_graph, rotation, 0.20, inputs, 5, 8)
    decay = np.exp(-0.20 * lg.DT)
    gain = -np.expm1(-0.20 * lg.DT) / 0.20
    expected = np.zeros((lg.N_MODES, lg.FEATURE_DIM), dtype=np.float64)
    for index in range(5):
        expected = decay * expected + gain * inputs[index]
    assert np.allclose(states[0], expected, atol=1e-13, rtol=1e-13)
    for index in range(8):
        expected = decay * expected + gain * inputs[5 + index]
        assert np.allclose(states[index + 1], expected, atol=1e-13, rtol=1e-13)


def test_backward_tangents_are_causal_normalised_and_count_degeneracy() -> None:
    states = np.zeros((4, lg.N_MODES, lg.FEATURE_DIM), dtype=np.float64)
    states[1, :, 0] = 1.0
    states[2, :, 0] = 3.0
    states[3, :, 0] = 3.0
    tangents, speeds, degenerate = lg.backward_tangents(states)
    assert degenerate == 8
    assert np.allclose(tangents[1, :, 0], 1.0, atol=1e-12)
    assert np.allclose(tangents[2, :, 0], 1.0, atol=1e-12)
    assert np.all(tangents[3] == 0.0)
    assert np.allclose(speeds[1], 8.0)
    assert np.allclose(speeds[2], 16.0)
    assert np.all(speeds[3] == 0.0)


def test_tangent_at_k_does_not_depend_on_future_states() -> None:
    states = _small_episode(4, 8)
    before, _, _ = lg.backward_tangents(states)
    changed = states.copy()
    changed[5:] += 1000.0
    after, _, _ = lg.backward_tangents(changed)
    assert np.array_equal(before[3], after[3])


def test_model_payload_excludes_evaluator_fields_and_hashes_deterministically() -> None:
    states = _small_episode(10, 20)
    payload = lg.make_model_payload(states, "train")
    assert set(payload) == {
        "states", "dt", "mode_count", "feature_dim", "out_degree_prior", "split_name"
    }
    digest = lg.model_payload_sha256(payload)
    assert digest == lg.model_payload_sha256(payload)
    with pytest.raises(ValueError, match="evaluator-only"):
        lg.model_payload_sha256(payload | {"hidden_adjacency": np.eye(lg.N_MODES)})


def test_forward_and_reverse_xy_use_the_declared_time_direction() -> None:
    states = np.zeros((6, lg.N_MODES, lg.FEATURE_DIM), dtype=np.float64)
    for time_index in range(6):
        states[time_index, :, 0] = float(time_index)
    rngs, _ = lg.make_control_rngs(301)
    episode = lg.prepare_episode(states, "train", rngs["train"])
    forward_x, forward_y, forward_groups = lg.build_xy(episode, 0, 2, "tangent")
    reverse_x, reverse_y, reverse_groups = lg.build_xy(
        episode, 0, 2, "tangent", reverse_time=True
    )
    # Valid origins are k=1,2,3; forward labels are k+2, reverse labels are k.
    assert forward_x.shape[0] == 3
    assert np.allclose(forward_y[:, 0], [3.0, 4.0, 5.0])
    assert np.allclose(reverse_y[:, 0], [1.0, 2.0, 3.0])
    assert set(forward_groups) == set(range(1, lg.N_MODES))
    assert set(reverse_groups) == set(forward_groups)
    assert forward_x.shape[1] == 2 * lg.FEATURE_DIM + 7 * lg.FEATURE_DIM


def test_training_statistics_are_not_estimated_from_validation_or_test() -> None:
    x_train = np.arange(60, dtype=np.float64).reshape(20, 3)
    y_train = (x_train[:, :1] * 0.2)
    x_val = np.full((10, 3), 10000.0)
    y_val = np.zeros((10, 1))
    model, _ = lg.fit_ridge_model(x_train, y_train, x_val, y_val)
    assert np.allclose(model["mean"], np.mean(x_train, axis=0))
    assert np.allclose(model["scale"], np.std(x_train, axis=0))


def test_topk_excludes_self_and_uses_stable_tie_breaking() -> None:
    scores = np.zeros((lg.N_MODES, lg.N_MODES), dtype=np.float64)
    selected = lg.select_topk(scores)
    for source, destinations in enumerate(selected):
        assert len(destinations) == 2
        assert source not in destinations
        assert destinations == [0 if source != 0 else 1, 1 if source not in (0, 1) else 2]


def test_edge_and_path_metrics_are_exact_on_a_known_graph() -> None:
    truth = _cycle_plus_skip()
    selected = [np.flatnonzero(truth[source]).astype(int).tolist() for source in range(lg.N_MODES)]
    metrics = lg.topology_metrics(truth, selected)
    assert metrics["correct_edges"] == 16
    assert metrics["edge_precision_at_2"] == 1.0
    assert metrics["edge_recall_at_2"] == 1.0
    assert metrics["path_precision"] == 1.0
    assert metrics["path_recall"] == 1.0
    assert metrics["inferred_two_hop_paths"] == 32


def test_campaign_mapper_has_no_adjacency_or_truth_argument() -> None:
    parameters = inspect.signature(lg.run_mapping).parameters
    assert "adjacency" not in parameters
    assert "truth" not in parameters


def test_run_mapping_freezes_rankings_before_test_evaluation() -> None:
    train = _small_episode(21, 60)
    validation = _small_episode(22, 60)
    test_a = _small_episode(23, 60)
    test_b = test_a.copy()
    test_b[1:] += 5.0 * np.random.default_rng(24).standard_normal(test_b[1:].shape)
    episodes_a = {"train": train, "validation": validation, "test": test_a}
    episodes_b = {"train": train, "validation": validation, "test": test_b}
    shuffle_a, random_a = lg.make_control_rngs(301)
    shuffle_b, random_b = lg.make_control_rngs(301)
    first = lg.run_mapping(episodes_a, 0.20, shuffle_a, random_a, include_controls=True)
    second = lg.run_mapping(episodes_b, 0.20, shuffle_b, random_b, include_controls=True)
    assert np.array_equal(first["primary"]["scores"], second["primary"]["scores"])
    assert first["primary"]["selected"] == second["primary"]["selected"]
    assert first["primary"]["models"][0]["alpha"] == second["primary"]["models"][0]["alpha"]
    assert not np.array_equal(
        first["primary_test_pair_contributions"], second["primary_test_pair_contributions"]
    )


def test_bootstrap_is_paired_and_best_control_is_selected_within_each_resample() -> None:
    indices_a = lg._bootstrap_indices(30)
    indices_b = lg._bootstrap_indices(30)
    assert np.array_equal(indices_a, indices_b)
    primary = np.full(30, 0.8)
    controls = {
        "a": np.full(30, 0.48),
        "b": np.linspace(0.3, 0.7, 30),
    }
    delta, ci, best = lg._best_control_delta(primary, controls, indices_a)
    assert best == "b"
    assert delta == pytest.approx(0.3)
    assert ci[0] > 0.0


def test_checksum_manifest_verifies_and_detects_tampering(tmp_path) -> None:
    (tmp_path / "report.txt").write_text("stable evidence\n", encoding="utf-8")
    lg._write_checksums(tmp_path)
    assert lg.verify_checksums(tmp_path)
    (tmp_path / "report.txt").write_text("changed evidence\n", encoding="utf-8")
    assert not lg.verify_checksums(tmp_path)


def test_seed_streams_are_separated_by_purpose_mode_and_split() -> None:
    graph_seed = lg._seed_entropy(301, lg.STREAM_CODES["graph"], 0)
    rotation_seed = lg._seed_entropy(301, lg.STREAM_CODES["rotation"], 0)
    train_mode_0 = lg._seed_entropy(301, lg.STREAM_CODES["train"], 0)
    train_mode_1 = lg._seed_entropy(301, lg.STREAM_CODES["train"], 1)
    validation_mode_0 = lg._seed_entropy(301, lg.STREAM_CODES["validation"], 0)
    shuffle_train_mode_0 = lg._seed_entropy(301, lg.STREAM_CODES["shuffle"], 0, lg.STREAM_CODES["train"])
    shuffle_validation_mode_0 = lg._seed_entropy(301, lg.STREAM_CODES["shuffle"], 0, lg.STREAM_CODES["validation"])
    assert len({
        tuple(graph_seed), tuple(rotation_seed), tuple(train_mode_0), tuple(train_mode_1),
        tuple(validation_mode_0), tuple(shuffle_train_mode_0), tuple(shuffle_validation_mode_0),
    }) == 7


def test_gate_requires_both_edge_and_path_criteria() -> None:
    # A complete miniature gate fixture makes any future criterion omission visible.
    row = {
        "primary": {"edge_precision_at_2": 0.7, "path_precision": 0.4},
        "test_selected_contribution": 0.3,
        "test_unselected_contribution": 0.1,
        "uncoupled_test_selected_contribution": 0.0,
    }
    for name in lg.CONTROL_NAMES:
        row[name] = {"edge_precision_at_2": 0.4, "path_precision": 0.2}
    rows = [row.copy() for _ in range(30)]
    indices = np.tile(np.arange(30), (lg.BOOTSTRAP_RESAMPLES, 1))
    result = lg._gate_for_rate(rows, indices, lg.LG01BConfig())
    assert result["criteria"]["mean_precision_at_2_ge_0_60"]
    assert result["criteria"]["path_precision_ge_0_30"]
    assert result["criteria"]["path_margin_over_best_control_ge_0_10"]
    assert result["status"] == "pass"
