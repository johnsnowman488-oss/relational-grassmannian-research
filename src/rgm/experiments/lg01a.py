"""LG-01A: transient-mode behaviour under bounded information refresh.

This module is deliberately a dynamical mechanism check. It does not build a
relational graph, learn destinations, or claim reasoning capability.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from numpy.typing import NDArray
from scipy.stats import t as student_t

FloatArray = NDArray[np.float64]
EXPERIMENT_ID = "LG-01A"
PROTOCOL_VERSION = "LG-01A-v0.1"
DEFAULT_RATES = (0.01, 0.05, 0.2, 0.8)
FAST_RATES = (0.05, 0.2, 0.8)
ARMS = ("pulse_only", "continuous_refresh", "intermittent_refresh", "conventional_soe_null")


@dataclass(frozen=True)
class LG01AConfig:
    feature_dim: int = 16
    decay_rates: tuple[float, ...] = DEFAULT_RATES
    dt: float = 0.125
    seeds: tuple[int, ...] = tuple(range(101, 131))
    preroll_tau: float = 8.0
    observation_tau: float = 4.0
    washout_tau: float = 3.0
    activity_ratio_min: float = 5.0
    reference_ratio_min: float = 0.8
    reference_ratio_max: float = 1.2
    min_passing_seeds: int = 27
    passing_window_fraction: float = 0.90
    relative_tolerance: float = 1e-8
    null_relative_tolerance: float = 1e-10
    bound_relative_tolerance: float = 1e-10
    trace_seed: int = 101

    def validate(self) -> None:
        if self.feature_dim != 16:
            raise ValueError("LG-01A-v0.1 freezes feature_dim=16")
        if tuple(self.decay_rates) != DEFAULT_RATES:
            raise ValueError(f"LG-01A-v0.1 freezes decay_rates={DEFAULT_RATES}")
        if not math.isfinite(self.dt) or self.dt <= 0:
            raise ValueError("dt must be finite and positive")
        if len(set(self.seeds)) != len(self.seeds) or len(self.seeds) < self.min_passing_seeds:
            raise ValueError("seed list must be unique and contain at least min_passing_seeds")
        if self.min_passing_seeds > len(self.seeds):
            raise ValueError("min_passing_seeds cannot exceed the number of seeds")
        if not (0 < self.passing_window_fraction <= 1):
            raise ValueError("passing_window_fraction must be in (0, 1]")
        if self.activity_ratio_min <= 0:
            raise ValueError("activity_ratio_min must be positive")
        if not (0 < self.reference_ratio_min < self.reference_ratio_max):
            raise ValueError("invalid reference ratio interval")
        for rate in self.decay_rates:
            for tau_multiple in (self.preroll_tau, self.observation_tau, self.washout_tau):
                steps = tau_multiple / rate / self.dt
                if not math.isclose(steps, round(steps), rel_tol=0.0, abs_tol=1e-10):
                    raise ValueError(
                        f"protocol horizon {tau_multiple}/gamma is not divisible by dt for gamma={rate}"
                    )
        if self.trace_seed not in self.seeds:
            raise ValueError("trace_seed must be one of the registered seeds")


def _steps_for_tau(rate: float, multiple: float, dt: float) -> int:
    return int(round(multiple / rate / dt))


def _unit_input_stream(seed: int, rate: float, n_steps: int, feature_dim: int) -> FloatArray:
    """Generate a deterministic stream of unit Euclidean-norm input vectors."""
    rate_code = int(round(rate * 1_000_000))
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, rate_code, 71001])))
    values = rng.standard_normal((n_steps, feature_dim), dtype=np.float64)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if np.any(norms == 0) or not np.all(np.isfinite(norms)):
        raise FloatingPointError("could not construct finite nonzero refresh vector")
    return values / norms


def _refresh_vector(base: FloatArray, step: int, arm: str) -> FloatArray:
    if arm == "continuous_refresh":
        return base[step]
    if arm == "intermittent_refresh":
        return 2.0 * base[step] if step % 4 == 0 else np.zeros_like(base[step])
    raise ValueError(f"arm {arm!r} does not use refresh input")


def _rms_norm(states: FloatArray) -> float:
    norms = np.linalg.norm(states, axis=1)
    return float(np.sqrt(np.mean(norms * norms)))


def _window_slices(rate: float, config: LG01AConfig) -> list[slice]:
    """Build deterministic windows wholly inside [3 tau, 4 tau]."""
    tau_steps = 1.0 / rate / config.dt
    window_size = max(2, int(math.ceil(tau_steps / 4.0)))
    stride = max(1, int(math.floor(tau_steps / 8.0)))
    start = int(round(3.0 * tau_steps))
    stop = int(round(4.0 * tau_steps))
    slices: list[slice] = []
    cursor = start
    while cursor + window_size <= stop + 1:
        slices.append(slice(cursor, cursor + window_size))
        cursor += stride
    if not slices:
        raise RuntimeError("protocol generated no activity evaluation windows")
    return slices


def _analytic_bound(initial_norm: float, rate: float, elapsed: FloatArray | float, umax: float) -> FloatArray:
    elapsed_arr = np.asarray(elapsed, dtype=np.float64)
    decay = np.exp(-rate * elapsed_arr)
    return decay * initial_norm + (umax / rate) * (1.0 - decay)


def _check_bound(states: FloatArray, rate: float, dt: float, initial_norm: float, umax: float) -> float:
    elapsed = np.arange(states.shape[0], dtype=np.float64) * dt
    bound = _analytic_bound(initial_norm, rate, elapsed, umax)
    norms = np.linalg.norm(states, axis=1)
    slack = 1e-10 * np.maximum(1.0, bound)
    if np.any(norms > bound + slack):
        index = int(np.argmax(norms - bound - slack))
        raise AssertionError(
            f"analytic boundedness envelope violated at step {index}: "
            f"norm={norms[index]:.16g}, bound={bound[index]:.16g}"
        )
    return float(np.max(norms))


def exact_step(state: FloatArray, input_vector: FloatArray, rate: float, dt: float) -> FloatArray:
    """Exact zero-order-hold update for dz/dt=-gamma*z+u over one step."""
    if rate <= 0 or dt <= 0 or not math.isfinite(rate * dt):
        raise ValueError("rate and dt must be finite and positive")
    if state.shape != input_vector.shape:
        raise ValueError("state and input_vector must have identical shapes")
    if not np.all(np.isfinite(state)) or not np.all(np.isfinite(input_vector)):
        raise ValueError("state and input_vector must be finite")
    a = math.exp(-rate * dt)
    b = -math.expm1(-rate * dt) / rate
    return a * state + b * input_vector


def input_perturbation_relative_error(
    base_stream: FloatArray, rate: float, dt: float, perturb_step: int = 4
) -> float:
    """Check the discrete impulse response against b*a**m*delta_u."""
    if base_stream.ndim != 2 or base_stream.shape[0] < perturb_step + 16:
        raise ValueError("base_stream must contain at least perturb_step + 16 rows")
    if not 0 <= perturb_step < base_stream.shape[0]:
        raise ValueError("perturb_step is outside base_stream")
    dim = base_stream.shape[1]
    delta = np.zeros(dim, dtype=np.float64)
    delta[0] = 0.125
    base_state = np.zeros(dim, dtype=np.float64)
    perturbed_state = np.zeros(dim, dtype=np.float64)
    a = math.exp(-rate * dt)
    b = -math.expm1(-rate * dt) / rate
    errors = []
    for step, input_vector in enumerate(base_stream[: perturb_step + 17]):
        base_state = exact_step(base_state, input_vector, rate, dt)
        perturbed_input = input_vector + delta if step == perturb_step else input_vector
        perturbed_state = exact_step(perturbed_state, perturbed_input, rate, dt)
        if step >= perturb_step:
            m = step - perturb_step
            expected = b * (a**m) * delta
            actual = perturbed_state - base_state
            denominator = max(float(np.linalg.norm(expected)), np.finfo(np.float64).tiny)
            errors.append(float(np.linalg.norm(actual - expected) / denominator))
    return max(errors, default=0.0)


def _simulate_refresh_arm(
    *, arm: str, seed: int, rate: float, config: LG01AConfig, trace: bool = False
) -> dict[str, Any]:
    if arm not in ("continuous_refresh", "intermittent_refresh"):
        raise ValueError("_simulate_refresh_arm accepts continuous or intermittent refresh")
    dim, dt = config.feature_dim, config.dt
    tau = 1.0 / rate
    n_pre = _steps_for_tau(rate, config.preroll_tau, dt)
    n_obs = _steps_for_tau(rate, config.observation_tau, dt)
    n_wash = _steps_for_tau(rate, config.washout_tau, dt)
    base = _unit_input_stream(seed, rate, n_pre + n_obs, dim)
    q = np.zeros(dim, dtype=np.float64)
    q[0] = 1.0
    a = math.exp(-rate * dt)
    b = -math.expm1(-rate * dt) / rate

    refresh = np.zeros(dim, dtype=np.float64)
    pre_refresh_states = [refresh.copy()]
    pre_inputs = []
    for step in range(n_pre):
        u = _refresh_vector(base, step, arm)
        refresh = a * refresh + b * u
        pre_refresh_states.append(refresh.copy())
        pre_inputs.append(u.copy())
    pre_refresh_trace = np.asarray(pre_refresh_states, dtype=np.float64)
    umax = 1.0 if arm == "continuous_refresh" else 2.0
    pre_max = _check_bound(pre_refresh_trace, rate, dt, 0.0, umax)

    # Tagged and refreshed contributions are maintained independently by design.
    tag = q.copy()
    combined = refresh + tag
    obs_total = [combined.copy()]
    obs_tag = [tag.copy()]
    obs_refresh = [refresh.copy()]
    obs_shadow = [refresh.copy()]
    obs_inputs = [np.zeros(dim, dtype=np.float64)]
    perturb_error = input_perturbation_relative_error(base, rate, dt)
    for local_step in range(n_obs):
        absolute_step = n_pre + local_step
        u = _refresh_vector(base, absolute_step, arm)
        tag = a * tag
        refresh = a * refresh + b * u
        combined = tag + refresh
        shadow = refresh.copy()
        obs_total.append(combined.copy())
        obs_tag.append(tag.copy())
        obs_refresh.append(refresh.copy())
        obs_shadow.append(shadow)
        obs_inputs.append(u.copy())

    total_obs = np.asarray(obs_total, dtype=np.float64)
    tag_obs = np.asarray(obs_tag, dtype=np.float64)
    refresh_obs = np.asarray(obs_refresh, dtype=np.float64)
    shadow_obs = np.asarray(obs_shadow, dtype=np.float64)
    input_obs = np.asarray(obs_inputs, dtype=np.float64)
    initial_at_tag = pre_refresh_trace[-1] + q
    obs_max = _check_bound(total_obs, rate, dt, float(np.linalg.norm(initial_at_tag)), umax)
    refresh_max = _check_bound(
        refresh_obs, rate, dt, float(np.linalg.norm(pre_refresh_trace[-1])), umax
    )

    # Individual tagged history must follow q*exp(-gamma*t) exactly.
    elapsed_obs = np.arange(n_obs + 1, dtype=np.float64) * dt
    expected_tag = np.exp(-rate * elapsed_obs)[:, None] * q[None, :]
    tagged_error = float(
        np.max(np.linalg.norm(tag_obs - expected_tag, axis=1) / np.maximum(np.linalg.norm(expected_tag, axis=1), 1e-300))
    )
    t3_steps = _steps_for_tau(rate, 3.0, dt)
    tagged_residual = float(np.linalg.norm(tag_obs[t3_steps]) / np.linalg.norm(q))

    # Compare activity with an identically timed pulse-only trajectory.
    pulse_only = expected_tag
    windows = _window_slices(rate, config)
    activity_ratios = []
    reference_ratios = []
    for window in windows:
        numerator = _rms_norm(total_obs[window])
        pulse_rms = _rms_norm(pulse_only[window])
        shadow_rms = _rms_norm(shadow_obs[window])
        activity_ratios.append(numerator / max(pulse_rms, 1e-300))
        reference_ratios.append(numerator / max(shadow_rms, 1e-300))
    passing_windows = sum(
        a_ratio >= config.activity_ratio_min
        and config.reference_ratio_min <= r_ratio <= config.reference_ratio_max
        for a_ratio, r_ratio in zip(activity_ratios, reference_ratios)
    )

    # Refresh stops after the observation interval. Both components then decay freely.
    stop_state = combined.copy()
    wash_states = [stop_state.copy()]
    for _ in range(n_wash):
        tag = a * tag
        refresh = a * refresh
        combined = tag + refresh
        wash_states.append(combined.copy())
    wash_trace = np.asarray(wash_states, dtype=np.float64)
    wash_ratio = float(np.linalg.norm(wash_trace[-1]) / max(np.linalg.norm(stop_state), 1e-300))
    wash_max = _check_bound(wash_trace, rate, dt, float(np.linalg.norm(stop_state)), 0.0)

    input_all = np.vstack((np.asarray(pre_inputs, dtype=np.float64), input_obs[1:]))
    energy = float(np.sum(np.linalg.norm(input_all, axis=1) ** 2) * dt)
    peak_input = float(np.max(np.linalg.norm(input_all, axis=1)))

    result: dict[str, Any] = {
        "seed": int(seed),
        "rate": float(rate),
        "arm": arm,
        "window_count": len(windows),
        "window_metrics": [
            {"window_index": index, "activity_ratio": float(a_ratio),
             "reference_ratio": float(r_ratio),
             "passed": bool(a_ratio >= config.activity_ratio_min
                             and config.reference_ratio_min <= r_ratio <= config.reference_ratio_max)}
            for index, (a_ratio, r_ratio) in enumerate(zip(activity_ratios, reference_ratios))
        ],
        "passing_windows": int(passing_windows),
        "passing_window_fraction": float(passing_windows / len(windows)),
        "activity_ratio_mean": float(np.mean(activity_ratios)),
        "activity_ratio_min": float(np.min(activity_ratios)),
        "reference_ratio_mean": float(np.mean(reference_ratios)),
        "reference_ratio_min": float(np.min(reference_ratios)),
        "reference_ratio_max": float(np.max(reference_ratios)),
        "tagged_max_relative_error": tagged_error,
        "tagged_residual_at_3tau": tagged_residual,
        "post_stop_washout_ratio_at_3tau": wash_ratio,
        "max_state_norm": float(max(pre_max, obs_max, refresh_max, wash_max)),
        "peak_input_norm": peak_input,
        "input_energy": energy,
        "input_response_relative_error": perturb_error,
        "all_finite": bool(
            np.all(np.isfinite(total_obs))
            and np.all(np.isfinite(tag_obs))
            and np.all(np.isfinite(refresh_obs))
            and np.all(np.isfinite(wash_trace))
        ),
    }
    if trace:
        result["trace"] = {
            "pre_states": pre_refresh_trace,
            "pre_inputs": np.asarray(pre_inputs, dtype=np.float64),
            "obs_total": total_obs,
            "obs_tag": tag_obs,
            "obs_refresh": refresh_obs,
            "obs_inputs": input_obs,
            "wash_total": wash_trace,
            "stop_state": stop_state,
            "tau": tau,
            "n_pre": n_pre,
            "n_obs": n_obs,
            "n_wash": n_wash,
        }
    return result


def _simulate_pulse_only(seed: int, rate: float, config: LG01AConfig, trace: bool = False) -> dict[str, Any]:
    dt, dim = config.dt, config.feature_dim
    tau = 1.0 / rate
    n_obs = _steps_for_tau(rate, config.observation_tau, dt)
    n_wash = _steps_for_tau(rate, config.washout_tau, dt)
    q = np.zeros(dim, dtype=np.float64)
    q[0] = 1.0
    a = math.exp(-rate * dt)
    states = [q.copy()]
    state = q.copy()
    for _ in range(n_obs):
        state = a * state
        states.append(state.copy())
    obs = np.asarray(states, dtype=np.float64)
    windows = _window_slices(rate, config)
    ratios = [_rms_norm(obs[w]) / max(_rms_norm(obs[w]), 1e-300) for w in windows]
    wash = [state.copy()]
    for _ in range(n_wash):
        state = a * state
        wash.append(state.copy())
    wash_trace = np.asarray(wash, dtype=np.float64)
    t3 = _steps_for_tau(rate, 3.0, dt)
    tagged_residual = float(np.linalg.norm(obs[t3]))
    elapsed = np.arange(n_obs + 1) * dt
    expected = np.exp(-rate * elapsed)[:, None] * q[None, :]
    tagged_error = float(np.max(np.linalg.norm(obs - expected, axis=1)))
    _check_bound(obs, rate, dt, 1.0, 0.0)
    wash_ratio = float(np.linalg.norm(wash_trace[-1]) / np.linalg.norm(wash_trace[0]))
    result: dict[str, Any] = {
        "seed": int(seed),
        "rate": float(rate),
        "arm": "pulse_only",
        "window_count": len(windows),
        "passing_windows": len(windows),
        "passing_window_fraction": 1.0,
        "activity_ratio_mean": float(np.mean(ratios)),
        "activity_ratio_min": float(np.min(ratios)),
        "reference_ratio_mean": 1.0,
        "reference_ratio_min": 1.0,
        "reference_ratio_max": 1.0,
        "tagged_max_relative_error": tagged_error,
        "tagged_residual_at_3tau": tagged_residual,
        "post_stop_washout_ratio_at_3tau": wash_ratio,
        "max_state_norm": 1.0,
        "peak_input_norm": 0.0,
        "input_energy": 0.0,
        "input_response_relative_error": 0.0,
        "all_finite": bool(np.all(np.isfinite(obs)) and np.all(np.isfinite(wash_trace))),
    }
    if trace:
        result["trace"] = {
            "obs_total": obs,
            "obs_tag": obs,
            "obs_refresh": np.zeros_like(obs),
            "obs_inputs": np.zeros_like(obs),
            "wash_total": wash_trace,
            "tau": tau,
            "n_pre": 0,
            "n_obs": n_obs,
            "n_wash": n_wash,
        }
    return result


def _simulate_soe_null(
    seed: int, rate: float, config: LG01AConfig, arm: str = "continuous_refresh", trace: bool = False
) -> dict[str, Any]:
    """Independent direct-total-state implementation of the conventional SOE null."""
    if arm not in ("continuous_refresh", "intermittent_refresh"):
        raise ValueError("SOE null requires a refresh arm")
    dim, dt = config.feature_dim, config.dt
    n_pre = _steps_for_tau(rate, config.preroll_tau, dt)
    n_obs = _steps_for_tau(rate, config.observation_tau, dt)
    n_wash = _steps_for_tau(rate, config.washout_tau, dt)
    base = _unit_input_stream(seed, rate, n_pre + n_obs, dim)
    a = math.exp(-rate * dt)
    b = -math.expm1(-rate * dt) / rate
    state = np.zeros(dim, dtype=np.float64)
    pre_states = [state.copy()]
    pre_inputs = []
    for step in range(n_pre):
        u = _refresh_vector(base, step, arm)
        state = a * state + b * u
        pre_states.append(state.copy())
        pre_inputs.append(u.copy())
    q = np.zeros(dim, dtype=np.float64)
    q[0] = 1.0
    state = state + q
    states = [state.copy()]
    inputs = [np.zeros(dim, dtype=np.float64)]
    for local_step in range(n_obs):
        absolute_step = n_pre + local_step
        u = _refresh_vector(base, absolute_step, arm)
        state = a * state + b * u
        states.append(state.copy())
        inputs.append(u.copy())
    obs = np.asarray(states, dtype=np.float64)
    wash = [state.copy()]
    for _ in range(n_wash):
        state = a * state
        wash.append(state.copy())
    wash_trace = np.asarray(wash, dtype=np.float64)
    result = {
        "seed": int(seed),
        "rate": float(rate),
        "arm": "conventional_soe_null",
        "null_arm": arm,
        "obs_total": obs,
        "wash_total": wash_trace,
        "obs_inputs": np.asarray(inputs, dtype=np.float64),
        "pre_refresh_norm": float(np.linalg.norm(pre_states[-1])),
        "pre_states": np.asarray(pre_states, dtype=np.float64),
        "pre_inputs": np.asarray(pre_inputs, dtype=np.float64),
        "max_state_norm": float(max(np.max(np.linalg.norm(obs, axis=1)), np.max(np.linalg.norm(wash_trace, axis=1)))),
    }
    if trace:
        result["tau"] = 1.0 / rate
        result["n_pre"] = n_pre
        result["n_obs"] = n_obs
        result["n_wash"] = n_wash
    return result


def _score_soe_null(
    null: dict[str, Any], seed: int, rate: float, arm: str, config: LG01AConfig
) -> dict[str, Any]:
    """Score the independent conventional-SOE trajectory using the same gates."""
    dt, dim = config.dt, config.feature_dim
    n_pre = _steps_for_tau(rate, config.preroll_tau, dt)
    n_obs = _steps_for_tau(rate, config.observation_tau, dt)
    base = _unit_input_stream(seed, rate, n_pre + n_obs, dim)
    q = np.zeros(dim, dtype=np.float64); q[0] = 1.0
    elapsed = np.arange(n_obs + 1, dtype=np.float64) * dt
    tag = np.exp(-rate * elapsed)[:, None] * q[None, :]
    total = null["obs_total"]
    refresh = total - tag
    windows = _window_slices(rate, config)
    activity, reference = [], []
    for window in windows:
        total_rms = _rms_norm(total[window])
        activity.append(total_rms / max(_rms_norm(tag[window]), 1e-300))
        reference.append(total_rms / max(_rms_norm(refresh[window]), 1e-300))
    passing = sum(
        a >= config.activity_ratio_min and config.reference_ratio_min <= r <= config.reference_ratio_max
        for a, r in zip(activity, reference)
    )
    tag_error = float(np.max(
        np.linalg.norm((total - refresh) - tag, axis=1)
        / np.maximum(np.linalg.norm(tag, axis=1), 1e-300)
    ))
    t3 = _steps_for_tau(rate, 3.0, dt)
    wash_ratio = float(np.linalg.norm(null["wash_total"][-1]) / max(np.linalg.norm(total[-1]), 1e-300))
    umax = 1.0 if arm == "continuous_refresh" else 2.0
    bound_obs_max = _check_bound(
        total, rate, dt, float(np.linalg.norm(null["pre_states"][-1] + q)), umax
    )
    bound_wash_max = _check_bound(null["wash_total"], rate, dt, float(np.linalg.norm(total[-1])), 0.0)
    input_all = np.vstack((null["pre_inputs"], null["obs_inputs"][1:]))
    energy = float(np.sum(np.linalg.norm(input_all, axis=1) ** 2) * dt)
    perturb_error = input_perturbation_relative_error(base, rate, dt)
    windows_detail = [
        {"window_index": i, "activity_ratio": float(a), "reference_ratio": float(r),
         "passed": bool(a >= config.activity_ratio_min and config.reference_ratio_min <= r <= config.reference_ratio_max)}
        for i, (a, r) in enumerate(zip(activity, reference))
    ]
    return {
        "seed": int(seed), "rate": float(rate), "arm": "conventional_soe_null",
        "continuous_or_intermittent": arm, "window_count": len(windows),
        "window_metrics": windows_detail, "passing_windows": int(passing),
        "passing_window_fraction": float(passing / len(windows)),
        "activity_ratio_mean": float(np.mean(activity)), "activity_ratio_min": float(np.min(activity)),
        "reference_ratio_mean": float(np.mean(reference)), "reference_ratio_min": float(np.min(reference)),
        "reference_ratio_max": float(np.max(reference)), "tagged_max_relative_error": tag_error,
        "tagged_residual_at_3tau": float(np.linalg.norm(tag[t3])),
        "post_stop_washout_ratio_at_3tau": wash_ratio,
        "max_state_norm": float(max(bound_obs_max, bound_wash_max)),
        "peak_input_norm": float(np.max(np.linalg.norm(input_all, axis=1))),
        "input_energy": energy, "input_response_relative_error": perturb_error,
        "all_finite": bool(np.all(np.isfinite(total)) and np.all(np.isfinite(refresh))
                            and np.all(np.isfinite(null["wash_total"]))),
    }


def _mean_ci(values: Iterable[float]) -> dict[str, float | int]:
    arr = np.asarray(list(values), dtype=np.float64)
    n = int(arr.size)
    mean = float(np.mean(arr)) if n else float("nan")
    if n <= 1:
        low = high = mean
        sd = 0.0
    else:
        sd = float(np.std(arr, ddof=1))
        half = float(student_t.ppf(0.975, n - 1) * sd / math.sqrt(n))
        low, high = mean - half, mean + half
    return {"n": n, "mean": mean, "sd": sd, "ci95_low": low, "ci95_high": high,
            "min": float(np.min(arr)), "max": float(np.max(arr))}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_metadata() -> dict[str, Any]:
    def run_git(*args: str) -> str | None:
        try:
            return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None
    return {
        "commit": os.environ.get("GITHUB_SHA") or run_git("rev-parse", "HEAD"),
        "branch": os.environ.get("GITHUB_REF_NAME") or run_git("branch", "--show-current"),
        "working_tree_status": run_git("status", "--short"),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _trace_record(
    seed: int, rate: float, arm: str, stage: str, step: int,
    state: FloatArray, tag: FloatArray, refresh: FloatArray, input_vector: FloatArray,
) -> dict[str, Any]:
    return {
        "seed": seed, "rate": rate, "arm": arm, "stage": stage, "step": step,
        "time_since_tag": step * 0.125,
        "state_norm": float(np.linalg.norm(state)),
        "tag_norm": float(np.linalg.norm(tag)),
        "refresh_norm": float(np.linalg.norm(refresh)),
        "input_norm": float(np.linalg.norm(input_vector)),
        "state": state.tolist(), "tagged": tag.tolist(),
        "refresh": refresh.tolist(), "input": input_vector.tolist(),
    }


def run_campaign(output_root: Path, run_id: str | None = None, config: LG01AConfig | None = None) -> dict[str, Any]:
    config = config or LG01AConfig()
    config.validate()
    started = datetime.now(timezone.utc)
    run_id = run_id or started.strftime("lg01a_%Y%m%dT%H%M%SZ")
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    config_payload = asdict(config)
    config_payload["decay_rates"] = list(config.decay_rates)
    config_payload["seeds"] = list(config.seeds)
    config_bytes = json.dumps(config_payload, sort_keys=True, separators=(",", ":")).encode()
    config_sha = hashlib.sha256(config_bytes).hexdigest()
    _write_json(run_dir / "config.json", {**config_payload, "config_sha256": config_sha,
                                           "protocol_version": PROTOCOL_VERSION})

    rows: list[dict[str, Any]] = []
    null_diffs: list[dict[str, Any]] = []
    trace_path = run_dir / "trace_samples.jsonl"
    with trace_path.open("w", encoding="utf-8") as trace_file:
        for rate in config.decay_rates:
            for seed in config.seeds:
                for arm in ("continuous_refresh", "intermittent_refresh"):
                    candidate = _simulate_refresh_arm(
                        arm=arm, seed=seed, rate=rate, config=config,
                        trace=(seed == config.trace_seed),
                    )
                    if seed == config.trace_seed:
                        tr = candidate["trace"]
                        sample_stride = max(1, int(round((1.0 / rate) / (4.0 * config.dt))))
                        for stage, states, tags, refreshes, inputs, offset in (
                            ("preroll", tr["pre_states"], np.zeros_like(tr["pre_states"]), tr["pre_states"],
                             np.vstack((np.zeros((1, config.feature_dim)), tr["pre_inputs"])), -tr["n_pre"]),
                            ("observation", tr["obs_total"], tr["obs_tag"], tr["obs_refresh"], tr["obs_inputs"], 0),
                        ):
                            for index in range(0, len(states), sample_stride):
                                trace_file.write(json.dumps(_trace_record(
                                    seed, rate, arm, stage, offset + index,
                                    states[index], tags[index], refreshes[index], inputs[index]
                                ), separators=(",", ":")) + "\n")
                    row = {k: v for k, v in candidate.items() if k != "trace"}
                    row["continuous_or_intermittent"] = arm
                    rows.append(row)

                    null = _simulate_soe_null(seed, rate, config, arm=arm, trace=(seed == config.trace_seed))
                    if candidate.get("trace") is not None:
                        candidate_obs = candidate["trace"]["obs_total"]
                    else:
                        # Reconstruct the candidate trajectory independently of its metrics.
                        base = _unit_input_stream(seed, rate,
                            _steps_for_tau(rate, config.preroll_tau + config.observation_tau, config.dt),
                            config.feature_dim)
                        a = math.exp(-rate * config.dt)
                        b = -math.expm1(-rate * config.dt) / rate
                        refresh = np.zeros(config.feature_dim, dtype=np.float64)
                        for step in range(_steps_for_tau(rate, config.preroll_tau, config.dt)):
                            refresh = a * refresh + b * _refresh_vector(base, step, arm)
                        tag = np.zeros(config.feature_dim, dtype=np.float64); tag[0] = 1.0
                        candidate_states = [refresh + tag]
                        for local in range(_steps_for_tau(rate, config.observation_tau, config.dt)):
                            absolute = _steps_for_tau(rate, config.preroll_tau, config.dt) + local
                            tag = a * tag
                            refresh = a * refresh + b * _refresh_vector(base, absolute, arm)
                            candidate_states.append(tag + refresh)
                        candidate_obs = np.asarray(candidate_states)
                    scale = np.maximum(np.linalg.norm(null["obs_total"], axis=1), 1e-12)
                    max_diff = float(np.max(np.linalg.norm(candidate_obs - null["obs_total"], axis=1) / scale))
                    null_diffs.append({"seed": seed, "rate": rate, "arm": arm, "max_relative_trace_difference": max_diff})
                    null_row = _score_soe_null(null, seed, rate, arm, config)
                    null_row["null_max_relative_trace_difference"] = max_diff
                    rows.append(null_row)

                    if seed == config.trace_seed:
                        sample_stride = max(1, int(round((1.0 / rate) / (4.0 * config.dt))))
                        for index in range(0, len(null["obs_total"]), sample_stride):
                            state = null["obs_total"][index]
                            tag_state = np.zeros(config.feature_dim, dtype=np.float64)
                            tag_state[0] = math.exp(-rate * config.dt * index)
                            trace_file.write(json.dumps(_trace_record(
                                seed, rate, "conventional_soe_null", "observation", index,
                                state, tag_state, state - tag_state, null["obs_inputs"][index]
                            ), separators=(",", ":")) + "\n")

                pulse = _simulate_pulse_only(seed, rate, config, trace=(seed == config.trace_seed))
                if seed == config.trace_seed:
                    tr = pulse["trace"]
                    sample_stride = max(1, int(round((1.0 / rate) / (4.0 * config.dt))))
                    for index in range(0, len(tr["obs_total"]), sample_stride):
                        state = tr["obs_total"][index]
                        trace_file.write(json.dumps(_trace_record(
                            seed, rate, "pulse_only", "observation", index,
                            state, state, np.zeros(config.feature_dim), np.zeros(config.feature_dim)
                        ), separators=(",", ":")) + "\n")
                rows.append({**{k: v for k, v in pulse.items() if k != "trace"}, "continuous_or_intermittent": "reference"})

    gate_by_rate: dict[str, Any] = {}
    for rate in config.decay_rates:
        continuous_rows = [r for r in rows if r["rate"] == rate and r["arm"] == "continuous_refresh"]
        passing_seeds = sum(r["passing_window_fraction"] >= config.passing_window_fraction for r in continuous_rows)
        all_math = len(continuous_rows) == len(config.seeds) and all(
            r["tagged_max_relative_error"] <= config.relative_tolerance
            and r["tagged_residual_at_3tau"] <= 0.05 + config.relative_tolerance
            and r["post_stop_washout_ratio_at_3tau"] <= 0.05 + config.relative_tolerance
            and r["input_response_relative_error"] <= config.relative_tolerance
            and r["all_finite"] for r in continuous_rows
        )
        rate_null_diffs = [d for d in null_diffs if d["rate"] == rate]
        all_null = len(rate_null_diffs) == 2 * len(config.seeds) and all(
            d["max_relative_trace_difference"] <= config.null_relative_tolerance for d in rate_null_diffs
        )
        is_fast = rate in FAST_RATES
        passing_seed_ids = [int(r["seed"]) for r in continuous_rows
                            if r["passing_window_fraction"] >= config.passing_window_fraction]
        failing_seed_ids = [int(r["seed"]) for r in continuous_rows
                            if r["passing_window_fraction"] < config.passing_window_fraction]
        gate_by_rate[str(rate)] = {
            "role": "fast_test_rate" if is_fast else "slow_reference",
            "continuous_refresh_seed_count": len(continuous_rows),
            "seeds_passing_window_fraction": passing_seeds,
            "passing_seed_ids": passing_seed_ids,
            "failing_seed_ids": failing_seed_ids,
            "refresh_gate_pass": (passing_seeds >= config.min_passing_seeds) if is_fast else None,
            "mathematical_checks_pass": all_math,
            "boundedness_checks_pass": len(continuous_rows) == len(config.seeds),
            "conventional_soe_null_match_pass": all_null,
            "activity_ratio_threshold": config.activity_ratio_min,
            "minimum_passing_seeds": config.min_passing_seeds,
        }

    energy_diffs = []
    for rate in config.decay_rates:
        for seed in config.seeds:
            cont = next(r for r in rows if r["seed"] == seed and r["rate"] == rate and r["arm"] == "continuous_refresh")
            inter = next(r for r in rows if r["seed"] == seed and r["rate"] == rate and r["arm"] == "intermittent_refresh")
            energy_diffs.append(abs(cont["input_energy"] - inter["input_energy"]))
    energy_match_pass = max(energy_diffs, default=0.0) <= 1e-12
    null_max = max((d["max_relative_trace_difference"] for d in null_diffs), default=0.0)
    fast_gate_pass = all(gate_by_rate[str(rate)]["refresh_gate_pass"] is True for rate in FAST_RATES)
    all_global_math = all(gate_by_rate[str(rate)]["mathematical_checks_pass"] for rate in config.decay_rates)
    all_global_null = all(gate_by_rate[str(rate)]["conventional_soe_null_match_pass"] for rate in config.decay_rates)
    operational_pass = bool(fast_gate_pass and all_global_math and all_global_null and energy_match_pass)

    summary_metrics: dict[str, Any] = {}
    for rate in config.decay_rates:
        rate_key = str(rate)
        rate_rows = [r for r in rows if r["rate"] == rate and r["arm"] == "continuous_refresh"]
        summary_metrics[rate_key] = {
            metric: _mean_ci(r[metric] for r in rate_rows)
            for metric in (
                "passing_window_fraction", "activity_ratio_mean", "reference_ratio_mean",
                "tagged_max_relative_error", "tagged_residual_at_3tau",
                "post_stop_washout_ratio_at_3tau", "max_state_norm", "input_energy",
                "input_response_relative_error",
            )
        }
        intermittent_rows = [r for r in rows if r["rate"] == rate and r["arm"] == "intermittent_refresh"]
        summary_metrics[rate_key]["intermittent_refresh"] = {
            metric: _mean_ci(r[metric] for r in intermittent_rows)
            for metric in ("passing_window_fraction", "activity_ratio_mean", "reference_ratio_mean", "input_energy")
        }

    finished = datetime.now(timezone.utc)
    summary = {
        "experiment": EXPERIMENT_ID, "protocol_version": PROTOCOL_VERSION, "run_id": run_id,
        "status": "complete", "scientific_decision": "pass" if operational_pass else "fail",
        "operational_pass": operational_pass,
        "claim_boundary": (
            "A pass supports only transient-mode activity under bounded refresh with individual tagged-contribution decay. "
            "It does not establish graph formation, endogenous destination selection, slow-history registration, adaptation, "
            "reasoning, or a distinct lepto-graph primitive. The conventional SOE null is expected to match."
        ),
        "gates": {
            "by_rate": gate_by_rate,
            "all_global_mathematical_checks_pass": all_global_math,
            "all_conventional_soe_null_matches_pass": all_global_null,
            "continuous_intermit_energy_match_pass": energy_match_pass,
            "max_energy_difference": max(energy_diffs, default=0.0),
            "max_candidate_vs_null_relative_trace_difference": null_max,
            "required_fast_rates": list(FAST_RATES), "fast_refresh_gate_pass": fast_gate_pass,
        },
        "metrics": summary_metrics,
        "sample_counts": {
            "seeds": len(config.seeds), "rates": len(config.decay_rates),
            "paired_seed_rate_cells": len(config.seeds) * len(config.decay_rates),
            "seed_metric_rows": len(rows), "null_comparisons": len(null_diffs),
        },
        "null_comparison": {
            "max_relative_trace_difference": null_max, "tolerance": config.null_relative_tolerance,
            "interpretation": "An exact or near-exact conventional SOE match is expected and is not evidence of novelty."
        },
        "energy_match": {"max_absolute_energy_difference": max(energy_diffs, default=0.0), "tolerance": 1e-12},
        "timestamps_utc": {"started": started.isoformat(), "finished": finished.isoformat()},
        "configuration_sha256": config_sha,
    }
    _write_json(run_dir / "summary.json", summary)

    columns = [
        "seed", "rate", "arm", "continuous_or_intermittent", "window_count", "passing_windows",
        "passing_window_fraction", "activity_ratio_mean", "activity_ratio_min", "reference_ratio_mean",
        "reference_ratio_min", "reference_ratio_max", "tagged_max_relative_error", "tagged_residual_at_3tau",
        "post_stop_washout_ratio_at_3tau", "max_state_norm", "peak_input_norm", "input_energy",
        "input_response_relative_error", "all_finite", "null_max_relative_trace_difference",
    ]
    with (run_dir / "seed_metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    window_columns = ["seed", "rate", "arm", "window_index", "activity_ratio", "reference_ratio", "passed"]
    with (run_dir / "window_metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=window_columns)
        writer.writeheader()
        for row in rows:
            for window in row.get("window_metrics", []):
                writer.writerow({"seed": row["seed"], "rate": row["rate"], "arm": row["arm"], **window})

    with (run_dir / "null_comparison.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["seed", "rate", "arm", "max_relative_trace_difference"])
        writer.writeheader()
        writer.writerows(null_diffs)

    md_lines = [
        f"# LG-01A campaign report — {run_id}", "", f"- Protocol: {PROTOCOL_VERSION}",
        f"- Decision: **{'OPERATIONAL PASS' if operational_pass else 'FAIL'}**", "",
        "## Rate-level gates", "", "| Rate | Role | Passing seeds | Refresh gate | Math | SOE null |", "|---:|---|---:|---|---|---|",
    ]
    for rate in config.decay_rates:
        gate = gate_by_rate[str(rate)]
        md_lines.append(
            f"| {rate:g} | {gate['role']} | {gate['seeds_passing_window_fraction']}/{len(config.seeds)} | "
            f"{gate['refresh_gate_pass'] if gate['refresh_gate_pass'] is not None else 'reference'} | "
            f"{gate['mathematical_checks_pass']} | {gate['conventional_soe_null_match_pass']} |"
        )
    md_lines += ["", "## Continuous-refresh metrics", "", "| Rate | Activity ratio (mean, 95% CI) | Reference ratio (mean, 95% CI) | Washout ratio (mean) | Input energy |", "|---:|---:|---:|---:|---:|"]
    for rate in config.decay_rates:
        m = summary_metrics[str(rate)]
        a = m["activity_ratio_mean"]; r = m["reference_ratio_mean"]; w = m["post_stop_washout_ratio_at_3tau"]; e = m["input_energy"]
        md_lines.append(
            f"| {rate:g} | {a['mean']:.6g} [{a['ci95_low']:.6g}, {a['ci95_high']:.6g}] | "
            f"{r['mean']:.6g} [{r['ci95_low']:.6g}, {r['ci95_high']:.6g}] | {w['mean']:.6g} | {e['mean']:.6g} |"
        )
    md_lines += [
        "", "## Claim boundary", "", summary["claim_boundary"], "",
        "## Reproducibility artifacts", "", "- run_manifest.json — source/environment/command metadata.",
        "- config.json — exact frozen configuration and hash.", "- seed_metrics.csv — per-seed/rate/arm metrics.",
        "- window_metrics.csv — per-measurement-window ratios and outcomes.",
        "- null_comparison.csv — candidate versus conventional SOE trace comparison.",
        "- trace_samples.jsonl — deterministic sentinel-seed vector trace samples.",
        "- summary.json — machine-readable gates and aggregate metrics.",
    ]
    (run_dir / "summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    manifest = {
        "experiment": EXPERIMENT_ID, "protocol_version": PROTOCOL_VERSION, "run_id": run_id,
        "command": [sys.executable, *sys.argv], "source": _git_metadata(),
        "environment": {
            "python": sys.version, "numpy": np.__version__, "scipy": __import__("scipy").__version__,
            "platform": platform.platform(), "machine": platform.machine(),
        },
        "configuration_sha256": config_sha, "seeds": list(config.seeds), "rates": list(config.decay_rates),
        "timestamps_utc": summary["timestamps_utc"], "scientific_decision": summary["scientific_decision"],
        "artifact_hashes": {}, "note": "Manifest hash is recorded in SHA256SUMS; SHA256SUMS is not self-hashed.",
    }
    _write_json(run_dir / "run_manifest.json", manifest)
    file_hashes = {p.name: _sha256(p) for p in sorted(run_dir.iterdir())
                   if p.is_file() and p.name not in ("SHA256SUMS", "run_manifest.json")}
    manifest["artifact_hashes"] = file_hashes
    _write_json(run_dir / "run_manifest.json", manifest)
    file_hashes = {p.name: _sha256(p) for p in sorted(run_dir.iterdir()) if p.is_file() and p.name != "SHA256SUMS"}
    (run_dir / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in file_hashes.items()), encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=Path("results/lg01a"))
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    summary = run_campaign(args.output_root, run_id=args.run_id)
    print(json.dumps({
        "run_id": summary["run_id"], "scientific_decision": summary["scientific_decision"],
        "operational_pass": summary["operational_pass"], "gates": summary["gates"],
    }, indent=2, sort_keys=True))
    return 0 if summary["operational_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
