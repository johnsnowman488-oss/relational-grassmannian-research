"""Closed-form reference solutions for Hybrid Relational Leptograph M0."""
from __future__ import annotations

import math

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]


def _finite_array(value: ArrayLike, *, name: str) -> FloatArray:
    result = np.asarray(value, dtype=np.float64)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    return result


def _time_grid(times: ArrayLike) -> FloatArray:
    result = _finite_array(times, name="times")
    if result.ndim != 1 or result.size == 0:
        raise ValueError("times must be a non-empty one-dimensional array")
    if result[0] < 0.0 or np.any(np.diff(result) < 0.0):
        raise ValueError("times must be non-negative and non-decreasing")
    return result


def _positive_rate(value: float, *, name: str) -> float:
    rate = float(value)
    if not math.isfinite(rate) or rate <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return rate


def exact_memory_trace(
    initial_state: ArrayLike,
    decay_rate: float,
    constant_forcing: ArrayLike,
    times: ArrayLike,
) -> FloatArray:
    """Solve dm/dt = -nu*m + g for constant vector forcing g."""
    initial = _finite_array(initial_state, name="initial_state")
    forcing = _finite_array(constant_forcing, name="constant_forcing")
    if initial.shape != forcing.shape:
        raise ValueError("initial_state and constant_forcing must have identical shapes")
    rate = _positive_rate(decay_rate, name="decay_rate")
    grid = _time_grid(times)
    decay = np.exp(-rate * grid)
    forcing_scale = -np.expm1(-rate * grid) / rate
    shape = (-1,) + (1,) * initial.ndim
    return decay.reshape(shape) * initial + forcing_scale.reshape(shape) * forcing


def exact_history_trace(
    initial_history: float,
    evidence: float,
    decay_rate: float,
    times: ArrayLike,
) -> FloatArray:
    """Solve dH/dt = lambda*(s-H) for constant evidence s."""
    initial, signal = float(initial_history), float(evidence)
    rate = _positive_rate(decay_rate, name="decay_rate")
    if not math.isfinite(initial) or not 0.0 <= initial <= 1.0:
        raise ValueError("initial_history must be finite and in [0, 1]")
    if not math.isfinite(signal) or not 0.0 <= signal <= 1.0:
        raise ValueError("evidence must be finite and in [0, 1]")
    grid = _time_grid(times)
    return signal + (initial - signal) * np.exp(-rate * grid)


def exact_operator_trace(
    initial_operator: ArrayLike,
    target_operator: ArrayLike,
    *,
    evidence: float,
    initial_history: float,
    history_decay: float,
    adaptation_rate: float,
    dormancy_decay: float,
    times: ArrayLike,
) -> FloatArray:
    """Solve the M0 constant-evidence cases for the adaptive routing operator.

    The law is dK/dt = eta*H*s*(K_target-K) - delta*(1-s)*K.
    M0 supports exact constant evidence s=0 (dormancy) and s=1
    (supported adaptation/reactivation). Other evidence values are rejected
    until their variable-coefficient solution is separately specified.
    """
    initial = _finite_array(initial_operator, name="initial_operator")
    target = _finite_array(target_operator, name="target_operator")
    if initial.ndim != 2 or target.shape != initial.shape:
        raise ValueError("initial_operator and target_operator must be equal-shape matrices")
    signal = float(evidence)
    if signal not in (0.0, 1.0):
        raise ValueError("M0 exact operator solutions require evidence exactly 0 or 1")
    h0 = float(initial_history)
    if not math.isfinite(h0) or not 0.0 <= h0 <= 1.0:
        raise ValueError("initial_history must be finite and in [0, 1]")
    lam = _positive_rate(history_decay, name="history_decay")
    eta = _positive_rate(adaptation_rate, name="adaptation_rate")
    delta = _positive_rate(dormancy_decay, name="dormancy_decay")
    grid = _time_grid(times)
    if signal == 0.0:
        return np.exp(-delta * grid)[:, None, None] * initial[None, :, :]

    # For s=1, integral_0^t H(r)dr = t-(1-H0)(1-exp(-lambda*t))/lambda.
    integrated_history = grid - (1.0 - h0) * (-np.expm1(-lam * grid)) / lam
    gain = np.exp(-eta * integrated_history)
    return target[None, :, :] + gain[:, None, None] * (initial - target)[None, :, :]


def factor_routing_operator(encoder: ArrayLike, decoder: ArrayLike) -> FloatArray:
    """Compose source -> interface -> target as decoder @ encoder."""
    source_to_interface = _finite_array(encoder, name="encoder")
    interface_to_target = _finite_array(decoder, name="decoder")
    if source_to_interface.ndim != 2 or interface_to_target.ndim != 2:
        raise ValueError("encoder and decoder must be two-dimensional matrices")
    if interface_to_target.shape[1] != source_to_interface.shape[0]:
        raise ValueError("decoder input dimension must equal encoder output dimension")
    return interface_to_target @ source_to_interface


def route(operator: ArrayLike, source_state: ArrayLike) -> FloatArray:
    """Apply a directed routing operator to a source-state vector."""
    matrix = _finite_array(operator, name="operator")
    state = _finite_array(source_state, name="source_state")
    if matrix.ndim != 2 or state.shape != (matrix.shape[1],):
        raise ValueError("source_state dimension must match operator input dimension")
    return matrix @ state
