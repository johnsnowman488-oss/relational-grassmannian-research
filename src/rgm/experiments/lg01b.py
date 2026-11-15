"""LG-01B-v0.1: recover a hidden directed topology from coupled trajectories.

The model-facing pipeline receives trajectories and frozen metadata only. The
hidden graph, graph-generation seed, orthogonal transform, and evaluator labels
remain in the campaign controller and are used only after rankings are frozen.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import resource
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import expm, solve

FloatArray = NDArray[np.float64]
EXPERIMENT_ID = "LG-01B"
PROTOCOL_VERSION = "LG-01B-v0.1"
RATES = (0.05, 0.20)
WORLD_SEEDS = tuple(range(301, 331))
N_MODES = 8
FEATURE_DIM = 16
OUT_DEGREE = 2
DT = 0.125
COUPLING_RATIO = 0.05
TANGENT_EPS = 1e-12
RIDGE_ALPHAS = (1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0)
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 4401
STREAM_CODES = {
    "graph": 1, "rotation": 2, "train": 3, "validation": 4,
    "test": 5, "random_baseline": 6, "shuffle": 7,
}
SPLIT_DURATIONS_TAU = {
    "train": (10.0, 40.0),
    "validation": (10.0, 10.0),
    "test": (10.0, 20.0),
}
CONTROL_NAMES = (
    "source_state", "direction_blind", "shuffled_tangent",
    "reverse_time", "symmetric_association", "random",
)


@dataclass(frozen=True)
class LG01BConfig:
    protocol_version: str = PROTOCOL_VERSION
    rates: tuple[float, ...] = RATES
    world_seeds: tuple[int, ...] = WORLD_SEEDS
    mode_count: int = N_MODES
    feature_dim: int = FEATURE_DIM
    out_degree: int = OUT_DEGREE
    dt: float = DT
    coupling_ratio: float = COUPLING_RATIO
    tangent_epsilon: float = TANGENT_EPS
    ridge_alphas: tuple[float, ...] = RIDGE_ALPHAS
    bootstrap_resamples: int = BOOTSTRAP_RESAMPLES
    bootstrap_seed: int = BOOTSTRAP_SEED
    edge_precision_min: float = 0.60
    chance_precision: float = 2.0 / 7.0
    control_margin: float = 0.10
    min_worlds_at_half: int = 24
    path_precision_min: float = 0.30
    path_control_margin: float = 0.10

    def validate(self) -> None:
        frozen = (
            self.protocol_version == PROTOCOL_VERSION and self.rates == RATES
            and self.world_seeds == WORLD_SEEDS and self.mode_count == N_MODES
            and self.feature_dim == FEATURE_DIM and self.out_degree == OUT_DEGREE
            and self.dt == DT and self.coupling_ratio == COUPLING_RATIO
            and self.tangent_epsilon == TANGENT_EPS and self.ridge_alphas == RIDGE_ALPHAS
            and self.bootstrap_resamples == BOOTSTRAP_RESAMPLES
            and self.bootstrap_seed == BOOTSTRAP_SEED and self.edge_precision_min == 0.60
            and self.control_margin == 0.10 and self.min_worlds_at_half == 24
            and self.path_precision_min == 0.30 and self.path_control_margin == 0.10
        )
        if not frozen:
            raise ValueError("LG-01B-v0.1 configuration is frozen; use a dated protocol revision to change it")
        if len(self.world_seeds) != 30 or len(set(self.world_seeds)) != 30:
            raise ValueError("LG-01B-v0.1 requires exactly 30 unique world seeds")
        for rate in self.rates:
            for burn_tau, record_tau in SPLIT_DURATIONS_TAU.values():
                for multiple in (burn_tau, record_tau):
                    steps = multiple / rate / self.dt
                    if not math.isclose(steps, round(steps), rel_tol=0.0, abs_tol=1e-10):
                        raise ValueError(f"episode duration is not divisible by dt at gamma={rate}")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _seed_entropy(world_seed: int, stream_code: int, mode_id: int = 0, split_code: int | None = None) -> list[int]:
    if split_code is None:
        return [int(world_seed), int(stream_code), int(mode_id)]
    return [int(world_seed), int(stream_code), int(split_code), int(mode_id)]


def _rng_from_entropy(entropy: Iterable[int]) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(list(entropy))))


def _reachable(adjacency: NDArray[np.integer], reverse: bool = False) -> set[int]:
    graph = adjacency.T if reverse else adjacency
    seen = {0}
    stack = [0]
    while stack:
        node = stack.pop()
        for neighbour in np.flatnonzero(graph[node]):
            neighbour = int(neighbour)
            if neighbour not in seen:
                seen.add(neighbour)
                stack.append(neighbour)
    return seen


def is_strongly_connected(adjacency: NDArray[np.integer]) -> bool:
    if adjacency.ndim != 2 or adjacency.shape[0] != adjacency.shape[1]:
        return False
    n = adjacency.shape[0]
    return len(_reachable(adjacency)) == n and len(_reachable(adjacency, reverse=True)) == n


def generate_hidden_graph(world_seed: int) -> tuple[NDArray[np.int8], int]:
    """Generate a strongly connected simple digraph with exact out-degree two."""
    rng = _rng_from_entropy(_seed_entropy(world_seed, STREAM_CODES["graph"], 0))
    candidates = np.arange(N_MODES)
    rejection_count = 0
    for _ in range(100_000):
        adjacency = np.zeros((N_MODES, N_MODES), dtype=np.int8)
        for source in range(N_MODES):
            allowed = candidates[candidates != source]
            destinations = rng.choice(allowed, size=OUT_DEGREE, replace=False)
            adjacency[source, destinations] = 1
        if is_strongly_connected(adjacency):
            if not np.all(adjacency.sum(axis=1) == OUT_DEGREE) or np.any(np.diag(adjacency)):
                raise AssertionError("graph generator violated its structural contract")
            return adjacency, rejection_count
        rejection_count += 1
    raise RuntimeError("graph rejection sampler exceeded 100000 draws")


def generate_orthogonal_transform(world_seed: int) -> FloatArray:
    rng = _rng_from_entropy(_seed_entropy(world_seed, STREAM_CODES["rotation"], 0))
    raw = rng.standard_normal((FEATURE_DIM, FEATURE_DIM), dtype=np.float64)
    q, r = np.linalg.qr(raw)
    signs = np.where(np.diag(r) >= 0.0, 1.0, -1.0)
    q = q * signs[np.newaxis, :]
    if not np.allclose(q.T @ q, np.eye(FEATURE_DIM), rtol=0.0, atol=2e-12):
        raise AssertionError("QR transform is not orthogonal within tolerance")
    return np.asarray(q, dtype=np.float64)


def build_transition(
    adjacency: NDArray[np.integer], rotation: FloatArray, gamma: float, dt: float = DT
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Return F, A=expm(F*dt), B=solve(F, A-I) in node-major ordering."""
    if adjacency.shape != (N_MODES, N_MODES) or rotation.shape != (FEATURE_DIM, FEATURE_DIM):
        raise ValueError("invalid adjacency or rotation shape")
    if not (math.isfinite(gamma) and gamma > 0 and math.isfinite(dt) and dt > 0):
        raise ValueError("gamma and dt must be finite and positive")
    coupling = COUPLING_RATIO * gamma
    operator = np.kron(np.asarray(adjacency, dtype=np.float64).T, rotation)
    size = N_MODES * FEATURE_DIM
    f_matrix = -gamma * np.eye(size, dtype=np.float64) + coupling * operator
    a_matrix = expm(f_matrix * dt)
    b_matrix = solve(f_matrix, a_matrix - np.eye(size, dtype=np.float64), assume_a="gen")
    if not (np.all(np.isfinite(a_matrix)) and np.all(np.isfinite(b_matrix))):
        raise FloatingPointError("non-finite exact transition matrices")
    return f_matrix, np.asarray(a_matrix), np.asarray(b_matrix)


def stability_diagnostics(f_matrix: FloatArray, a_matrix: FloatArray) -> dict[str, float]:
    symmetric = 0.5 * (f_matrix + f_matrix.T)
    margin = -float(np.max(np.linalg.eigvalsh(symmetric)))
    radius = float(np.max(np.abs(np.linalg.eigvals(a_matrix))))
    if margin <= 0 or radius >= 1.0:
        raise AssertionError(f"transition is not strictly stable: margin={margin}, radius={radius}")
    return {"symmetric_dissipativity_margin": margin, "transition_spectral_radius": radius}


def generate_unit_input_batch(
    world_seed: int, split: str, total_steps: int
) -> tuple[FloatArray, list[list[int]]]:
    """Independent unit-norm AR(1) inputs with a fixed physical correlation time."""
    if split not in ("train", "validation", "test") or total_steps < 1:
        raise ValueError("invalid split or input length")
    rho = math.exp(-DT / 2.0)
    innovation_scale = math.sqrt(1.0 - rho * rho)
    inputs = np.empty((total_steps, N_MODES, FEATURE_DIM), dtype=np.float64)
    entropies: list[list[int]] = []
    for mode in range(N_MODES):
        entropy = _seed_entropy(world_seed, STREAM_CODES[split], mode)
        entropies.append(entropy)
        rng = _rng_from_entropy(entropy)
        value = rng.standard_normal(FEATURE_DIM, dtype=np.float64)
        for step in range(total_steps):
            if step:
                value = rho * value + innovation_scale * rng.standard_normal(FEATURE_DIM, dtype=np.float64)
            norm = float(np.linalg.norm(value))
            if not (math.isfinite(norm) and norm > 0.0):
                raise FloatingPointError("invalid AR input norm")
            inputs[step, mode] = value / norm
    return inputs, entropies


def _steps_for_tau(gamma: float, multiple: float) -> int:
    steps = multiple / gamma / DT
    rounded = int(round(steps))
    if not math.isclose(steps, rounded, rel_tol=0.0, abs_tol=1e-10):
        raise ValueError(f"duration {multiple} tau is not divisible by dt at gamma={gamma}")
    return rounded


def simulate_episode(
    adjacency: NDArray[np.integer], rotation: FloatArray, gamma: float,
    inputs: FloatArray, burn_steps: int, record_steps: int,
) -> FloatArray:
    """Simulate a reset episode, discard burn-in, and return initial plus recorded states."""
    expected = burn_steps + record_steps
    if inputs.shape != (expected, N_MODES, FEATURE_DIM):
        raise ValueError(f"inputs must have shape {(expected, N_MODES, FEATURE_DIM)}")
    _, a_matrix, b_matrix = build_transition(adjacency, rotation, gamma, DT)
    state = np.zeros((N_MODES, FEATURE_DIM), dtype=np.float64)
    if not np.any(adjacency):
        decay = math.exp(-gamma * DT)
        gain = -math.expm1(-gamma * DT) / gamma
        for step in range(burn_steps):
            state = decay * state + gain * inputs[step]
        output = np.empty((record_steps + 1, N_MODES, FEATURE_DIM), dtype=np.float64)
        output[0] = state
        for local_step in range(record_steps):
            state = decay * state + gain * inputs[burn_steps + local_step]
            output[local_step + 1] = state
    else:
        transition = np.concatenate((a_matrix, b_matrix), axis=1)
        for step in range(burn_steps):
            vector = np.concatenate((state.reshape(-1), inputs[step].reshape(-1)))
            state = (transition @ vector).reshape(N_MODES, FEATURE_DIM)
        output = np.empty((record_steps + 1, N_MODES, FEATURE_DIM), dtype=np.float64)
        output[0] = state
        for local_step in range(record_steps):
            vector = np.concatenate((state.reshape(-1), inputs[burn_steps + local_step].reshape(-1)))
            state = (transition @ vector).reshape(N_MODES, FEATURE_DIM)
            output[local_step + 1] = state
    if not np.all(np.isfinite(output)):
        raise FloatingPointError("non-finite trajectory state")
    return output


def make_model_payload(states: FloatArray, split_name: str) -> dict[str, Any]:
    """Model input contract: trajectories and declared dimensions/prior only."""
    if split_name not in ("train", "validation", "test"):
        raise ValueError("invalid split name")
    array = np.asarray(states, dtype=np.float64)
    if array.ndim != 3 or array.shape[1:] != (N_MODES, FEATURE_DIM) or not np.all(np.isfinite(array)):
        raise ValueError("states must be a finite (time, 8, 16) array")
    return {
        "states": array, "dt": DT, "mode_count": N_MODES,
        "feature_dim": FEATURE_DIM, "out_degree_prior": OUT_DEGREE,
        "split_name": split_name,
    }


def model_payload_sha256(payload: dict[str, Any]) -> str:
    allowed = {"states", "dt", "mode_count", "feature_dim", "out_degree_prior", "split_name"}
    if set(payload) != allowed:
        raise ValueError("model payload contains missing or evaluator-only fields")
    metadata = {key: payload[key] for key in ("dt", "mode_count", "feature_dim", "out_degree_prior", "split_name")}
    array = np.ascontiguousarray(payload["states"], dtype="<f8")
    return _sha256(_canonical_json(metadata) + array.tobytes(order="C"))


def backward_tangents(states: FloatArray, dt: float = DT) -> tuple[FloatArray, FloatArray, int]:
    """Causal backward differences; zero degenerate tangents and count them."""
    if states.ndim != 3 or states.shape[1:] != (N_MODES, FEATURE_DIM):
        raise ValueError("states must have shape (time, 8, 16)")
    if not (math.isfinite(dt) and dt > 0):
        raise ValueError("dt must be finite and positive")
    differences = np.diff(np.asarray(states, dtype=np.float64), axis=0) / dt
    if not np.all(np.isfinite(differences)):
        raise FloatingPointError("non-finite backward tangent")
    norms = np.linalg.norm(differences, axis=2)
    degenerate = norms <= TANGENT_EPS
    tangents = np.zeros_like(states, dtype=np.float64)
    valid = ~degenerate
    scaled = np.zeros_like(differences)
    scaled[valid] = differences[valid] / (norms[valid, np.newaxis] + TANGENT_EPS)
    tangents[1:] = scaled
    speeds = np.zeros((states.shape[0], N_MODES), dtype=np.float64)
    speeds[1:] = norms
    return tangents, speeds, int(np.count_nonzero(degenerate))


def _block_shuffle_tangents(tangents: FloatArray, shuffle_rngs: list[np.random.Generator]) -> FloatArray:
    shuffled = np.array(tangents, dtype=np.float64, copy=True)
    n_steps = tangents.shape[0] - 1
    block_size = int(round(1.0 / DT))
    for mode in range(N_MODES):
        values = tangents[1:, mode]
        blocks = [values[start:start + block_size] for start in range(0, n_steps, block_size)]
        order = shuffle_rngs[mode].permutation(len(blocks))
        shuffled[1:, mode] = np.concatenate([blocks[int(index)] for index in order], axis=0)
    return shuffled


def prepare_episode(
    states: FloatArray, split: str, shuffle_rngs: list[np.random.Generator]
) -> dict[str, Any]:
    payload = make_model_payload(states, split)
    tangents, speeds, degenerate = backward_tangents(payload["states"], payload["dt"])
    return {
        "payload": payload, "tangents": tangents, "speeds": speeds,
        "shuffled_tangents": _block_shuffle_tangents(tangents, shuffle_rngs),
        "degenerate_tangent_count": degenerate, "payload_sha256": model_payload_sha256(payload),
    }


def _sample_indices(states: FloatArray, horizon_steps: int) -> NDArray[np.int64]:
    n_records = states.shape[0] - 1
    if horizon_steps < 1 or n_records <= horizon_steps:
        raise ValueError("episode is too short for the prediction horizon")
    return np.arange(1, n_records - horizon_steps + 1, dtype=np.int64)


def build_xy(
    episode: dict[str, Any], destination: int, horizon_steps: int, source_kind: str,
    *, reverse_time: bool = False,
) -> tuple[FloatArray, FloatArray, dict[int, slice]]:
    """Build one destination's design matrix using only the supplied trajectory episode."""
    states, tangents = episode["payload"]["states"], episode["tangents"]
    speeds, shuffled = episode["speeds"], episode["shuffled_tangents"]
    indices = _sample_indices(states, horizon_steps)
    feature_time = indices + horizon_steps if reverse_time else indices
    target_time = indices if reverse_time else indices + horizon_steps
    x_parts = [states[feature_time, destination], tangents[feature_time, destination]]
    groups: dict[int, slice] = {}
    cursor = 2 * FEATURE_DIM
    for source in range(N_MODES):
        if source == destination:
            continue
        if source_kind == "tangent":
            block = tangents[feature_time, source]
        elif source_kind == "state":
            block = states[feature_time, source]
        elif source_kind == "activity":
            block = speeds[feature_time, source, np.newaxis]
        elif source_kind == "shuffled_tangent":
            block = shuffled[feature_time, source]
        elif source_kind == "none":
            continue
        else:
            raise ValueError(f"unknown source feature kind {source_kind!r}")
        x_parts.append(np.asarray(block, dtype=np.float64))
        groups[source] = slice(cursor, cursor + block.shape[1])
        cursor += block.shape[1]
    x_matrix = np.concatenate(x_parts, axis=1)
    y_matrix = states[target_time, destination]
    if not (np.all(np.isfinite(x_matrix)) and np.all(np.isfinite(y_matrix))):
        raise FloatingPointError("non-finite regression data")
    return x_matrix, y_matrix, groups


def fit_ridge_model(
    x_train: FloatArray, y_train: FloatArray, x_validation: FloatArray,
    y_validation: FloatArray, alphas: tuple[float, ...] = RIDGE_ALPHAS,
) -> tuple[dict[str, Any], float]:
    """Fit train statistics and select regularisation by validation loss only."""
    if any(array.ndim != 2 for array in (x_train, y_train, x_validation, y_validation)):
        raise ValueError("ridge inputs and targets must be two-dimensional")
    if x_train.shape[1] != x_validation.shape[1] or y_train.shape[1] != y_validation.shape[1]:
        raise ValueError("train/validation feature and target dimensions must match")
    if x_train.shape[0] != y_train.shape[0] or x_validation.shape[0] != y_validation.shape[0]:
        raise ValueError("feature and target sample counts must match")
    if not all(np.all(np.isfinite(array)) for array in (x_train, y_train, x_validation, y_validation)):
        raise FloatingPointError("non-finite ridge data")
    mean = np.mean(x_train, axis=0)
    scale = np.std(x_train, axis=0)
    scale[scale < 1e-12] = 1.0
    x_train_scaled = (x_train - mean) / scale
    x_validation_scaled = (x_validation - mean) / scale
    y_mean = np.mean(y_train, axis=0)
    y_centered = y_train - y_mean
    gram = x_train_scaled.T @ x_train_scaled
    cross = x_train_scaled.T @ y_centered
    identity = np.eye(gram.shape[0], dtype=np.float64)
    best_model: dict[str, Any] | None = None
    best_mse, best_alpha = math.inf, math.inf
    for alpha in alphas:
        coefficient = solve(
            gram + float(alpha) * identity, cross, assume_a="pos", check_finite=False
        )
        prediction = y_mean + x_validation_scaled @ coefficient
        mse = float(np.mean((prediction - y_validation) ** 2))
        if not math.isfinite(mse):
            raise FloatingPointError("ridge validation loss is non-finite")
        if (mse, float(alpha)) < (best_mse, best_alpha):
            best_mse, best_alpha = mse, float(alpha)
            best_model = {
                "mean": mean, "scale": scale, "y_mean": y_mean,
                "coefficient": coefficient, "alpha": best_alpha,
            }
    if best_model is None:
        raise RuntimeError("ridge alpha grid was empty")
    return best_model, best_mse


def _standardized_prediction(model: dict[str, Any], x: FloatArray, ablation: slice | None = None) -> FloatArray:
    scaled = (x - model["mean"]) / model["scale"]
    if ablation is not None:
        scaled[:, ablation] = 0.0
    return model["y_mean"] + scaled @ model["coefficient"]


def _mse(model: dict[str, Any], x: FloatArray, y: FloatArray, ablation: slice | None = None) -> float:
    prediction = _standardized_prediction(model, x, ablation)
    return float(np.mean((prediction - y) ** 2))


def _fit_target_models(
    train: dict[str, Any], validation: dict[str, Any], horizon_steps: int, *, reverse_time: bool = False
) -> tuple[list[dict[str, Any]], FloatArray]:
    models: list[dict[str, Any]] = []
    losses = np.zeros(N_MODES, dtype=np.float64)
    for destination in range(N_MODES):
        x_train, y_train, _ = build_xy(train, destination, horizon_steps, "none", reverse_time=reverse_time)
        x_val, y_val, _ = build_xy(validation, destination, horizon_steps, "none", reverse_time=reverse_time)
        model, loss = fit_ridge_model(x_train, y_train, x_val, y_val)
        models.append(model)
        losses[destination] = loss
    return models, losses


def _fit_variant(
    train: dict[str, Any], validation: dict[str, Any], horizon_steps: int,
    source_kind: str, target_validation_losses: FloatArray, *, reverse_time: bool = False,
) -> tuple[FloatArray, list[dict[str, Any]], FloatArray]:
    scores = np.zeros((N_MODES, N_MODES), dtype=np.float64)
    models: list[dict[str, Any]] = []
    full_losses = np.zeros(N_MODES, dtype=np.float64)
    for destination in range(N_MODES):
        x_train, y_train, train_groups = build_xy(
            train, destination, horizon_steps, source_kind, reverse_time=reverse_time
        )
        x_val, y_val, val_groups = build_xy(
            validation, destination, horizon_steps, source_kind, reverse_time=reverse_time
        )
        if train_groups.keys() != val_groups.keys():
            raise AssertionError("train and validation source groups differ")
        model, full_loss = fit_ridge_model(x_train, y_train, x_val, y_val)
        models.append(model)
        full_losses[destination] = full_loss
        denominator = max(float(target_validation_losses[destination]), 1e-15)
        for source, group in val_groups.items():
            scores[source, destination] = (_mse(model, x_val, y_val, group) - full_loss) / denominator
    np.fill_diagonal(scores, 0.0)
    return scores, models, full_losses


def select_topk(scores: FloatArray, k: int = OUT_DEGREE) -> list[list[int]]:
    if scores.shape != (N_MODES, N_MODES) or k < 1 or k >= N_MODES:
        raise ValueError("invalid score matrix or top-k value")
    output: list[list[int]] = []
    for source in range(N_MODES):
        destinations = [destination for destination in range(N_MODES) if destination != source]
        destinations.sort(key=lambda destination: (-float(scores[source, destination]), destination))
        output.append(destinations[:k])
    return output


def _symmetric_association_scores(validation: dict[str, Any], horizon_steps: int) -> FloatArray:
    states = validation["payload"]["states"]
    indices = _sample_indices(states, horizon_steps)
    energy = np.linalg.norm(states[indices], axis=2)
    correlations = np.corrcoef(energy, rowvar=False)
    scores = np.abs(np.nan_to_num(correlations, nan=0.0, posinf=0.0, neginf=0.0))
    np.fill_diagonal(scores, 0.0)
    return scores


def _random_scores(rng: np.random.Generator) -> FloatArray:
    scores = rng.random((N_MODES, N_MODES), dtype=np.float64)
    np.fill_diagonal(scores, 0.0)
    return scores


def _ranking_json(scores: FloatArray) -> list[dict[str, Any]]:
    selected = select_topk(scores)
    return [
        {
            "source": source,
            "destinations": destinations,
            "scores": [float(scores[source, destination]) for destination in destinations],
        }
        for source, destinations in enumerate(selected)
    ]


def _selected_edge_set(selected: list[list[int]]) -> set[tuple[int, int]]:
    return {(source, destination) for source, destinations in enumerate(selected) for destination in destinations}


def _path_set(adjacency: NDArray[np.integer]) -> set[tuple[int, int, int]]:
    paths: set[tuple[int, int, int]] = set()
    for source in range(N_MODES):
        for middle in np.flatnonzero(adjacency[source]):
            for destination in np.flatnonzero(adjacency[int(middle)]):
                paths.add((source, int(middle), int(destination)))
    return paths


def topology_metrics(truth: NDArray[np.integer], selected: list[list[int]]) -> dict[str, float | int]:
    true_edges = {(i, j) for i in range(N_MODES) for j in range(N_MODES) if truth[i, j]}
    inferred_edges = _selected_edge_set(selected)
    correct = len(true_edges & inferred_edges)
    inferred_adjacency = np.zeros_like(truth, dtype=np.int8)
    for source, destination in inferred_edges:
        inferred_adjacency[source, destination] = 1
    inferred_paths, true_paths = _path_set(inferred_adjacency), _path_set(truth)
    correct_paths = len(inferred_paths & true_paths)
    unique_pairs = {(source, destination) for source, _, destination in inferred_paths}
    return {
        "correct_edges": int(correct),
        "edge_precision_at_2": float(correct / max(len(inferred_edges), 1)),
        "edge_recall_at_2": float(correct / max(len(true_edges), 1)),
        "correct_two_hop_paths": int(correct_paths),
        "inferred_two_hop_paths": int(len(inferred_paths)),
        "true_two_hop_paths": int(len(true_paths)),
        "path_precision": float(correct_paths / max(len(inferred_paths), 1)),
        "path_recall": float(correct_paths / max(len(true_paths), 1)),
        "two_hop_query_coverage": float(len(unique_pairs) / (N_MODES * N_MODES)),
    }


def _primary_test_contributions(
    test: dict[str, Any], horizon_steps: int,
    models: list[dict[str, Any]], target_models: list[dict[str, Any]],
) -> FloatArray:
    contribution = np.zeros((N_MODES, N_MODES), dtype=np.float64)
    for destination in range(N_MODES):
        x_test, y_test, groups = build_xy(test, destination, horizon_steps, "tangent")
        full_loss = _mse(models[destination], x_test, y_test)
        x_target, y_target, _ = build_xy(test, destination, horizon_steps, "none")
        target_loss = _mse(target_models[destination], x_target, y_target)
        denominator = max(target_loss, 1e-15)
        for source, group in groups.items():
            ablated = _mse(models[destination], x_test, y_test, group)
            contribution[source, destination] = (ablated - full_loss) / denominator
    np.fill_diagonal(contribution, 0.0)
    return contribution


def make_control_rngs(
    world_seed: int,
) -> tuple[dict[str, list[np.random.Generator]], np.random.Generator]:
    shuffle_rngs: dict[str, list[np.random.Generator]] = {}
    for split in ("train", "validation", "test"):
        split_code = STREAM_CODES[split]
        shuffle_rngs[split] = [
            _rng_from_entropy(_seed_entropy(world_seed, STREAM_CODES["shuffle"], mode, split_code))
            for mode in range(N_MODES)
        ]
    random_rng = _rng_from_entropy(_seed_entropy(world_seed, STREAM_CODES["random_baseline"], 0))
    return shuffle_rngs, random_rng


def run_mapping(
    episodes: dict[str, FloatArray], gamma: float,
    shuffle_rngs: dict[str, list[np.random.Generator]],
    random_rng: np.random.Generator, *, include_controls: bool = True,
) -> dict[str, Any]:
    """Trajectory-only mapper. Hidden adjacency and evaluator labels are not arguments."""
    horizon_steps = int(round(0.25 / gamma / DT))
    prepared = {
        split: prepare_episode(states, split, shuffle_rngs[split])
        for split, states in episodes.items()
    }
    train, validation, test = prepared["train"], prepared["validation"], prepared["test"]
    target_models, target_val_losses = _fit_target_models(train, validation, horizon_steps)
    specs = {"primary": ("tangent", False)}
    if include_controls:
        specs.update({
            "source_state": ("state", False),
            "direction_blind": ("activity", False),
            "shuffled_tangent": ("shuffled_tangent", False),
            "reverse_time": ("tangent", True),
        })
    results: dict[str, Any] = {}
    primary_models: list[dict[str, Any]] = []
    for name, (kind, reverse) in specs.items():
        if reverse:
            reverse_target_models, reverse_target_losses = _fit_target_models(
                train, validation, horizon_steps, reverse_time=True
            )
            scores, models, losses = _fit_variant(
                train, validation, horizon_steps, kind, reverse_target_losses, reverse_time=True
            )
            results["reverse_target_models"] = reverse_target_models
        else:
            scores, models, losses = _fit_variant(
                train, validation, horizon_steps, kind, target_val_losses
            )
        results[name] = {
            "scores": scores, "selected": select_topk(scores),
            "models": models, "validation_full_losses": losses,
        }
        if name == "primary":
            primary_models = models
    if include_controls:
        symmetric = _symmetric_association_scores(validation, horizon_steps)
        random_scores = _random_scores(random_rng)
        results["symmetric_association"] = {"scores": symmetric, "selected": select_topk(symmetric)}
        results["random"] = {"scores": random_scores, "selected": select_topk(random_scores)}
    results["primary_test_pair_contributions"] = _primary_test_contributions(
        test, horizon_steps, primary_models, target_models
    )
    results["payload_hashes"] = {
        split: prepared[split]["payload_sha256"] for split in ("train", "validation", "test")
    }
    results["degenerate_tangent_counts"] = {
        split: prepared[split]["degenerate_tangent_count"] for split in ("train", "validation", "test")
    }
    results["sample_counts"] = {
        split: int(_sample_indices(episodes[split], horizon_steps).size)
        for split in ("train", "validation", "test")
    }
    return results


def _bootstrap_indices(n_worlds: int, seed: int = BOOTSTRAP_SEED) -> NDArray[np.int64]:
    rng = _rng_from_entropy([seed])
    return rng.integers(0, n_worlds, size=(BOOTSTRAP_RESAMPLES, n_worlds), dtype=np.int64)


def _bootstrap_ci(values: FloatArray, indices: NDArray[np.integer]) -> tuple[float, float]:
    samples = np.mean(values[indices], axis=1)
    low, high = np.percentile(samples, [2.5, 97.5])
    return float(low), float(high)


def _best_control_delta(
    primary: FloatArray, controls: dict[str, FloatArray], indices: NDArray[np.integer]
) -> tuple[float, tuple[float, float], str]:
    means = {name: float(np.mean(values)) for name, values in controls.items()}
    strongest = max(means, key=means.get)
    point = float(np.mean(primary) - means[strongest])
    primary_boot = np.mean(primary[indices], axis=1)
    control_boot = np.stack([np.mean(values[indices], axis=1) for values in controls.values()], axis=0)
    delta_boot = primary_boot - np.max(control_boot, axis=0)
    low, high = np.percentile(delta_boot, [2.5, 97.5])
    return point, (float(low), float(high)), strongest


def _gate_for_rate(
    world_rows: list[dict[str, Any]], indices: NDArray[np.integer], config: LG01BConfig
) -> dict[str, Any]:
    primary = np.asarray([row["primary"]["edge_precision_at_2"] for row in world_rows], dtype=np.float64)
    controls = {
        name: np.asarray([row[name]["edge_precision_at_2"] for row in world_rows], dtype=np.float64)
        for name in CONTROL_NAMES
    }
    primary_mean = float(np.mean(primary))
    primary_ci = _bootstrap_ci(primary, indices)
    control_delta, control_delta_ci, best_control = _best_control_delta(primary, controls, indices)
    paths = np.asarray([row["primary"]["path_precision"] for row in world_rows], dtype=np.float64)
    path_controls = {
        name: np.asarray([row[name]["path_precision"] for row in world_rows], dtype=np.float64)
        for name in CONTROL_NAMES
    }
    best_path_control = max(path_controls, key=lambda name: float(np.mean(path_controls[name])))
    path_mean = float(np.mean(paths))
    path_margin = path_mean - float(np.mean(path_controls[best_path_control]))
    selected = np.asarray([row["test_selected_contribution"] for row in world_rows], dtype=np.float64)
    unselected = np.asarray([row["test_unselected_contribution"] for row in world_rows], dtype=np.float64)
    uncoupled = np.asarray([row["uncoupled_test_selected_contribution"] for row in world_rows], dtype=np.float64)
    paired_delta = selected - uncoupled
    paired_delta_ci = _bootstrap_ci(paired_delta, indices)
    selected_minus_unselected = selected - unselected
    criteria = {
        "mean_precision_at_2_ge_0_60": primary_mean >= config.edge_precision_min,
        "precision_ci_lower_above_chance": primary_ci[0] > config.chance_precision,
        "at_least_24_worlds_precision_ge_0_50": int(np.count_nonzero(primary >= 0.50)) >= config.min_worlds_at_half,
        "best_control_margin_ge_0_10_and_ci_above_zero": (
            control_delta >= config.control_margin and control_delta_ci[0] > 0.0
        ),
        "test_selected_contribution_positive": float(np.mean(selected)) > 0.0,
        "test_selected_exceeds_nonselected": float(np.mean(selected_minus_unselected)) > 0.0,
        "test_selected_exceeds_uncoupled_with_ci_above_zero": (
            float(np.mean(paired_delta)) > 0.0 and paired_delta_ci[0] > 0.0
        ),
        "path_precision_ge_0_30": path_mean >= config.path_precision_min,
        "path_margin_over_best_control_ge_0_10": path_margin >= config.path_control_margin,
    }
    return {
        "status": "pass" if all(criteria.values()) else "fail",
        "criteria": criteria,
        "primary_precision_at_2": {
            "mean": primary_mean, "ci95": list(primary_ci),
            "worlds_ge_0_50": int(np.count_nonzero(primary >= 0.50)),
            "per_world": primary.tolist(),
        },
        "best_control": {
            "name": best_control, "mean_margin": control_delta,
            "paired_bootstrap_ci95": list(control_delta_ci),
            "control_means": {name: float(np.mean(values)) for name, values in controls.items()},
        },
        "path_witness": {
            "mean_precision": path_mean, "best_control": best_path_control,
            "best_control_mean": float(np.mean(path_controls[best_path_control])),
            "margin": path_margin,
        },
        "test_predictive_contribution": {
            "selected_mean": float(np.mean(selected)),
            "nonselected_mean": float(np.mean(unselected)),
            "selected_minus_nonselected_mean": float(np.mean(selected_minus_unselected)),
            "uncoupled_selected_mean": float(np.mean(uncoupled)),
            "coupled_minus_uncoupled_mean": float(np.mean(paired_delta)),
            "coupled_minus_uncoupled_ci95": list(paired_delta_ci),
        },
    }


def _metric_for_prediction(mapping: dict[str, Any], truth: NDArray[np.integer]) -> dict[str, Any]:
    return {
        name: topology_metrics(truth, mapping[name]["selected"])
        for name in ("primary",) + CONTROL_NAMES
    }


def _memory_peak_bytes() -> int | None:
    try:
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value * (1024 if sys.platform != "darwin" else 1))
    except Exception:
        return None


def _episode_lengths(gamma: float) -> dict[str, tuple[int, int]]:
    return {
        split: (_steps_for_tau(gamma, burn_tau), _steps_for_tau(gamma, record_tau))
        for split, (burn_tau, record_tau) in SPLIT_DURATIONS_TAU.items()
    }


def _json_matrix(matrix: FloatArray) -> list[list[float]]:
    return [[float(value) for value in row] for row in matrix]


def _world_record(
    truth: NDArray[np.integer], coupled: dict[str, Any], null: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    metrics = _metric_for_prediction(coupled, truth)
    selected_edges = _selected_edge_set(coupled["primary"]["selected"])
    null_edges = _selected_edge_set(null["primary"]["selected"])
    test_scores = coupled["primary_test_pair_contributions"]
    null_scores = null["primary_test_pair_contributions"]
    selected_values = [float(test_scores[i, j]) for i, j in selected_edges]
    unselected_values = [
        float(test_scores[i, j]) for i in range(N_MODES) for j in range(N_MODES)
        if i != j and (i, j) not in selected_edges
    ]
    null_values = [float(null_scores[i, j]) for i, j in null_edges]
    record = {
        **metrics,
        "test_selected_contribution": float(np.mean(selected_values)),
        "test_unselected_contribution": float(np.mean(unselected_values)),
        "uncoupled_test_selected_contribution": float(np.mean(null_values)),
    }
    prediction_record = {
        "coupled": {
            "rankings": {name: _ranking_json(coupled[name]["scores"]) for name in ("primary",) + CONTROL_NAMES},
            "validation_pair_scores": {
                name: _json_matrix(coupled[name]["scores"]) for name in ("primary",) + CONTROL_NAMES
            },
            "primary_test_pair_contributions": _json_matrix(test_scores),
            "primary_selected_test_contribution": record["test_selected_contribution"],
            "primary_unselected_test_contribution": record["test_unselected_contribution"],
        },
        "uncoupled_null": {
            "primary_ranking": _ranking_json(null["primary"]["scores"]),
            "primary_validation_pair_scores": _json_matrix(null["primary"]["scores"]),
            "primary_test_pair_contributions": _json_matrix(null_scores),
            "primary_selected_test_contribution": record["uncoupled_test_selected_contribution"],
        },
    }
    return record, prediction_record


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _write_checksums(root: Path) -> None:
    checksum_path = root / "SHA256SUMS"
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path != checksum_path:
            rows.append(f"{_sha256(path.read_bytes())}  {path.relative_to(root).as_posix()}")
    checksum_path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def verify_checksums(root: Path) -> bool:
    checksum_path = root / "SHA256SUMS"
    if not checksum_path.exists():
        return False
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = root / relative
        if not path.is_file() or _sha256(path.read_bytes()) != expected:
            return False
    return True


def _write_report(path: Path, gates: dict[str, Any], run_id: str, commit_sha: str) -> None:
    lines = [
        "# LG-01B-v0.1 campaign report", "",
        f"- Run ID: {run_id}",
        f"- Source commit: {commit_sha}",
        "- Frozen rates: γ=0.05 and γ=0.20 (evaluated independently)",
        "- Worlds: 30 paired graph worlds (seeds 301–330)",
        "- Hidden graph was evaluator-only; the mapper received trajectories and the declared k=2 prior only.",
        "- γ=0.80 remains excluded because LG-01A-v0.1 failed there (26/30); no LG-01A result is revised.",
        "- Interpretation ceiling: synthetic fixed-topology reconstruction, not spontaneous graph emergence.",
        "",
        "| Rate | Decision | Mean edge precision@2 | 95% CI | Worlds ≥0.50 | Best-control margin | Path precision | Path margin |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for rate in RATES:
        item = gates[f"{rate:.2f}"]
        precision = item["primary_precision_at_2"]
        lines.append(
            f"| {rate:.2f} | {item['status'].upper()} | {precision['mean']:.4f} | "
            f"[{precision['ci95'][0]:.4f}, {precision['ci95'][1]:.4f}] | "
            f"{precision['worlds_ge_0_50']}/30 | {item['best_control']['mean_margin']:.4f} | "
            f"{item['path_witness']['mean_precision']:.4f} | {item['path_witness']['margin']:.4f} |"
        )
    lines.extend(["", "## Rate-specific gate details", ""])
    for rate in RATES:
        item = gates[f"{rate:.2f}"]
        lines.append(f"### γ={rate:.2f}: **{item['status'].upper()}**")
        for name, passed in item["criteria"].items():
            lines.append(f"- [{'x' if passed else ' '}] {name}")
        lines.append("")
        lines.append(f"Strongest edge control: {item['best_control']['name']}.")
        lines.append(
            f"Selected test contribution {item['test_predictive_contribution']['selected_mean']:.6g}; "
            f"non-selected {item['test_predictive_contribution']['nonselected_mean']:.6g}; "
            f"uncoupled-null top-two {item['test_predictive_contribution']['uncoupled_selected_mean']:.6g}."
        )
        lines.append("")
    lines.extend([
        "## Frozen interpretation", "",
        "A rate passes only if every edge-recovery, held-out contribution, and two-hop witness criterion passes. "
        "The two rates are not averaged to create an overall pass. Any mixed or failed result is reported as such.",
        "",
        "A pass establishes only task-specific recovery of the hidden directed coupling structure in this stable "
        "synthetic linear family under a known out-degree prior. It does not establish spontaneous topology emergence, "
        "unknown-degree discovery, nonlinear mapping, general reasoning, or neurobiological equivalence.",
        "",
        "The coupling ratio c=0.05 was not tuned. A failure at this strength is retained as the scientific outcome.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_campaign(output_root: Path, run_id: str, config: LG01BConfig | None = None) -> dict[str, Any]:
    config = config or LG01BConfig()
    config.validate()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    repo_root = Path(__file__).resolve().parents[3]
    protocol_path = repo_root / "docs" / "lg01b_protocol.md"
    if not protocol_path.is_file():
        raise FileNotFoundError(f"frozen protocol snapshot not found: {protocol_path}")
    protocol_bytes = protocol_path.read_bytes()
    protocol_hash = _sha256(protocol_bytes)
    (run_dir / "protocol_snapshot.md").write_bytes(protocol_bytes)
    try:
        commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
        git_status = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_root, text=True).strip()
    except Exception:
        commit_sha, git_status = "unavailable", "unavailable"

    _write_json(run_dir / "config.json", asdict(config) | {
        "split_durations_tau": SPLIT_DURATIONS_TAU,
        "seed_stream_codes": STREAM_CODES,
        "prediction_horizon_tau": 0.25,
        "block_shuffle_duration_physical": 1.0,
    })
    _write_json(run_dir / "environment.json", {
        "python": sys.version, "platform": platform.platform(),
        "numpy": np.__version__, "scipy": __import__("scipy").__version__,
        "repository_commit": commit_sha, "working_tree_clean": git_status == "",
        "working_tree_status": git_status, "protocol_sha256": protocol_hash,
    })
    seed_manifest: list[dict[str, Any]] = []
    evaluator_root, payload_root, prediction_root = (
        run_dir / "evaluator_only", run_dir / "model_facing", run_dir / "predictions"
    )
    evaluator_root.mkdir()
    payload_root.mkdir()
    prediction_root.mkdir()
    world_results: dict[str, list[dict[str, Any]]] = {f"{rate:.2f}": [] for rate in RATES}
    world_costs: list[dict[str, Any]] = []

    for world_seed in config.world_seeds:
        world_start = time.perf_counter()
        truth, rejection_count = generate_hidden_graph(world_seed)
        rotation = generate_orthogonal_transform(world_seed)
        graph_entropy = _seed_entropy(world_seed, STREAM_CODES["graph"], 0)
        rotation_entropy = _seed_entropy(world_seed, STREAM_CODES["rotation"], 0)
        seed_manifest.extend([
            {
                "world_seed": world_seed, "purpose": "hidden_graph",
                "stream_code": STREAM_CODES["graph"], "mode_id": 0,
                "seed_entropy": graph_entropy, "rejected_graph_draws": rejection_count,
            },
            {
                "world_seed": world_seed, "purpose": "orthogonal_transform",
                "stream_code": STREAM_CODES["rotation"], "mode_id": 0,
                "seed_entropy": rotation_entropy,
            },
        ])
        _write_json(evaluator_root / f"world_{world_seed}" / "hidden_world.json", {
            "world_seed": world_seed, "graph_seed_entropy": graph_entropy,
            "graph_rejection_count": rejection_count,
            "adjacency_source_to_destination": truth.tolist(),
            "directed_edges": [[int(i), int(j)] for i, j in zip(*np.nonzero(truth))],
            "rotation_seed_entropy": rotation_entropy, "rotation_matrix": rotation.tolist(),
            "rotation_sha256": _sha256(np.ascontiguousarray(rotation, dtype="<f8").tobytes()),
        })

        for rate in config.rates:
            rate_key = f"{rate:.2f}"
            rate_start = time.perf_counter()
            lengths = _episode_lengths(rate)
            coupled_episodes: dict[str, FloatArray] = {}
            null_episodes: dict[str, FloatArray] = {}
            for split, (burn_steps, record_steps) in lengths.items():
                inputs, entropies = generate_unit_input_batch(
                    world_seed, split, burn_steps + record_steps
                )
                seed_manifest.extend([
                    {
                        "world_seed": world_seed, "rate": rate,
                        "purpose": f"{split}_input_mode_{mode}",
                        "stream_code": STREAM_CODES[split], "mode_id": mode,
                        "seed_entropy": entropies[mode], "input_steps": int(inputs.shape[0]),
                    }
                    for mode in range(N_MODES)
                ])
                coupled_episodes[split] = simulate_episode(
                    truth, rotation, rate, inputs, burn_steps, record_steps
                )
                null_episodes[split] = simulate_episode(
                    np.zeros_like(truth), rotation, rate, inputs, burn_steps, record_steps
                )
            shuffle_rngs, random_rng = make_control_rngs(world_seed)
            for split in ("train", "validation", "test"):
                split_code = STREAM_CODES[split]
                for mode in range(N_MODES):
                    seed_manifest.append({
                        "world_seed": world_seed, "rate": rate,
                        "purpose": f"{split}_shuffle_mode_{mode}",
                        "stream_code": STREAM_CODES["shuffle"], "mode_id": mode,
                        "split_stream_code": split_code,
                        "seed_entropy": _seed_entropy(world_seed, STREAM_CODES["shuffle"], mode, split_code),
                    })
            seed_manifest.append({
                "world_seed": world_seed, "rate": rate, "purpose": "random_baseline",
                "stream_code": STREAM_CODES["random_baseline"], "mode_id": 0,
                "seed_entropy": _seed_entropy(world_seed, STREAM_CODES["random_baseline"], 0),
            })

            coupled_mapping = run_mapping(
                coupled_episodes, rate, shuffle_rngs, random_rng, include_controls=True
            )
            null_shuffle_rngs, null_random_rng = make_control_rngs(world_seed)
            null_mapping = run_mapping(
                null_episodes, rate, null_shuffle_rngs, null_random_rng, include_controls=False
            )
            world_record, prediction_record = _world_record(truth, coupled_mapping, null_mapping)
            world_record.update({
                "world_seed": world_seed, "rate": rate,
                "graph_rejection_count": rejection_count,
                "coupled_degenerate_tangents": coupled_mapping["degenerate_tangent_counts"],
                "coupled_sample_counts": coupled_mapping["sample_counts"],
                "null_degenerate_tangents": null_mapping["degenerate_tangent_counts"],
                "null_sample_counts": null_mapping["sample_counts"],
            })
            world_results[rate_key].append(world_record)
            _write_json(
                prediction_root / f"world_{world_seed}" / f"gamma_{rate_key}.json",
                prediction_record,
            )
            for arm_name, arm_mapping in (("coupled", coupled_mapping), ("uncoupled_null", null_mapping)):
                for split, digest in arm_mapping["payload_hashes"].items():
                    _write_json(
                        payload_root / arm_name / f"world_{world_seed}" / f"gamma_{rate_key}" / f"{split}.json",
                        {
                            "world_seed": world_seed, "rate": rate, "arm": arm_name, "split": split,
                            "payload_sha256": digest,
                            "interface": {
                                "dt": DT, "mode_count": N_MODES,
                                "feature_dim": FEATURE_DIM, "out_degree_prior": OUT_DEGREE,
                            },
                            "regeneration": {
                                "input_stream_code": STREAM_CODES[split], "generator": "NumPy PCG64",
                                "episode_burn_steps": lengths[split][0],
                                "episode_record_steps": lengths[split][1],
                            },
                        },
                    )
            world_costs.append({
                "world_seed": world_seed, "rate": rate,
                "wall_clock_seconds": time.perf_counter() - rate_start,
                "training_samples_per_destination": coupled_mapping["sample_counts"]["train"],
                "validation_samples_per_destination": coupled_mapping["sample_counts"]["validation"],
                "test_samples_per_destination": coupled_mapping["sample_counts"]["test"],
                "approx_primary_test_prediction_multiply_adds": int(
                    8 * coupled_mapping["sample_counts"]["test"]
                    * (2 * FEATURE_DIM + (N_MODES - 1) * FEATURE_DIM) * FEATURE_DIM
                ),
            })
        world_costs.append({
            "world_seed": world_seed, "world_wall_clock_seconds": time.perf_counter() - world_start
        })

    bootstrap = _bootstrap_indices(len(config.world_seeds), config.bootstrap_seed)
    gates = {
        rate_key: _gate_for_rate(rows, bootstrap, config)
        for rate_key, rows in world_results.items()
    }
    scientific_pass = all(item["status"] == "pass" for item in gates.values())
    summary = {
        "experiment_id": EXPERIMENT_ID, "protocol_version": PROTOCOL_VERSION,
        "run_id": run_id, "source_commit": commit_sha, "protocol_sha256": protocol_hash,
        "world_count": len(config.world_seeds), "world_seeds": list(config.world_seeds),
        "rates": list(config.rates),
        "scientific_status": "pass" if scientific_pass else "fail",
        "rate_gates": gates, "world_results": world_results, "world_costs": world_costs,
        "total_wall_clock_seconds": time.perf_counter() - started,
        "peak_memory_bytes": _memory_peak_bytes(),
        "seed_manifest_entries": len(seed_manifest),
        "model_facing_payload_count": 2 * len(config.world_seeds) * len(config.rates) * 3,
    }
    _write_json(run_dir / "seed_manifest.json", {
        "generator": "NumPy PCG64", "world_seeds": list(config.world_seeds),
        "stream_codes": STREAM_CODES, "entries": seed_manifest,
    })
    _write_json(run_dir / "world_metrics.json", world_results)
    _write_json(run_dir / "summary.json", summary)
    flat_rows: list[dict[str, Any]] = []
    for rate_key, rows in world_results.items():
        for row in rows:
            flat = {"rate": rate_key, "world_seed": row["world_seed"]}
            for control, metrics in row.items():
                if isinstance(metrics, dict) and "edge_precision_at_2" in metrics:
                    flat[f"{control}_precision_at_2"] = metrics["edge_precision_at_2"]
                    flat[f"{control}_path_precision"] = metrics["path_precision"]
            flat["test_selected_contribution"] = row["test_selected_contribution"]
            flat["test_unselected_contribution"] = row["test_unselected_contribution"]
            flat["uncoupled_test_selected_contribution"] = row["uncoupled_test_selected_contribution"]
            flat_rows.append(flat)
    with (run_dir / "world_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = sorted({key for row in flat_rows for key in row})
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat_rows)
    _write_report(run_dir / "report.md", gates, run_id, commit_sha)
    _write_json(run_dir / "costs.json", {
        "world_costs": world_costs, "total_wall_clock_seconds": summary["total_wall_clock_seconds"],
        "peak_memory_bytes": summary["peak_memory_bytes"],
    })
    _write_checksums(run_dir)
    if not verify_checksums(run_dir):
        raise IOError("SHA256SUMS verification failed after bundle creation")
    return {
        "run_dir": str(run_dir), "scientific_status": summary["scientific_status"],
        "rate_gates": gates, "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=os.environ.get("LG01B_RUN_ID"))
    parser.add_argument("--output-root", type=Path, default=Path("results/lg01b"))
    args = parser.parse_args(argv)
    run_id = args.run_id or datetime.now(timezone.utc).strftime("lg01b_%Y%m%dT%H%M%SZ")
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    if not run_id or any(char not in allowed for char in run_id):
        parser.error("run-id may contain only letters, numbers, dot, underscore, and hyphen")
    run_dir = args.output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = run_campaign(args.output_root, run_id)
        print(json.dumps({
            "run_dir": result["run_dir"], "scientific_status": result["scientific_status"],
            "rate_gates": {
                key: {
                    "status": item["status"],
                    "precision_mean": item["primary_precision_at_2"]["mean"],
                    "path_precision_mean": item["path_witness"]["mean_precision"],
                }
                for key, item in result["rate_gates"].items()
            },
        }, indent=2, sort_keys=True))
        return 0 if result["scientific_status"] == "pass" else 1
    except Exception as exc:
        _write_json(run_dir / "execution_error.json", {
            "error_type": type(exc).__name__, "error": str(exc),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        })
        _write_checksums(run_dir)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
