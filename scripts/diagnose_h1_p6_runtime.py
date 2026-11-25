#!/usr/bin/env python3
"""Diagnostic only: locate the first P6/native blow-up on the already-failed seed."""
from __future__ import annotations
import json
import os
from pathlib import Path

import numpy as np

from rgm.experiments.h1_hierarchical_campaign import (
    _new_session, _readout_examples, _readout_target_matrices, load_frozen_partitions,
)
from rgm.leptograph.m4.p6_runtime import P6RuntimeCoupler
from rgm.leptograph.m4.stability import CoupledAdaptiveSystem
from rgm.leptograph.m4.soe_bridge import SOEHierarchyBridge, make_h0_chain_spec
from rgm.leptograph.m4.hierarchical import HLAAdapter, HierarchicalRuntimeDirector
from rgm.memory import SOEMemory
from gfe_ctypes import load_gfe_library, create_persistent_hierarchy_runtime

ROOT = Path(__file__).resolve().parents[1]
M4_COMMIT = "2539df6bda7ef3c9dd7c707abe26eff8bdbb59de"


def run_one(architecture: str, seed: int, *, control_enabled: bool,
            readout_gain: float = 1.0, control_gain: float = 1.0) -> dict:
    _, partitions, _ = load_frozen_partitions()
    examples = _readout_examples(partitions["train"].seeds, _readout_target_matrices())
    lib = load_gfe_library(os.environ["GFE_CORE_LIB"])
    session = _new_session(architecture, lib, examples)
    coupler = P6RuntimeCoupler(
        session["director"], hierarchy_lifecycle=session["lifecycle"],
        model=CoupledAdaptiveSystem(max_state_norm=25.0),
        readout_gain=readout_gain, control_gain=control_gain,
    )
    if not control_enabled:
        coupler.model.revision.accepted_operator = np.zeros((2, 2), dtype=np.float64)
    coupler.checkpoint()
    rng = np.random.default_rng(seed)
    max_native = 0.0
    max_p6 = 0.0
    try:
        for tick in range(300):
            feature = rng.uniform(-1.0, 1.0, size=16)
            residual = 3.0 if tick in (80, 190) else 0.0
            try:
                result = coupler.exchange(
                    event_time=(tick + 1) * 0.01,
                    observed_at=(tick + 1) * 0.01,
                    event_features={0: feature}, residual_score=residual,
                )
                native = result["hierarchy"]["result"]["native"]["level_states"]
                level_norms = [
                    float(np.linalg.norm(np.asarray(level["u"], dtype=np.float64)))
                    for level in native
                ]
                max_native = max(max_native, *level_norms)
                max_p6 = max(max_p6, result["p6_state_norm"])
            except Exception as exc:
                return {
                    "architecture": architecture,
                    "control_enabled": control_enabled,
                    "readout_gain": readout_gain,
                    "control_gain": control_gain,
                    "seed": seed,
                    "first_failure_tick": tick,
                    "event_time": (tick + 1) * 0.01,
                    "exception": type(exc).__name__,
                    "message": str(exc),
                    "max_native_norm_before_failure": max_native,
                    "max_p6_norm_before_failure": max_p6,
                }
        return {
            "architecture": architecture, "control_enabled": control_enabled,
            "readout_gain": readout_gain, "control_gain": control_gain,
            "seed": seed, "first_failure_tick": None,
            "max_native_norm": max_native, "max_p6_norm": max_p6,
            "detector_alarms": coupler.model.detector.alarms,
            "p6_state": coupler.model.state.tolist(),
        }
    finally:
        coupler.close()



def sweep_native_parameters(seed: int = 950000) -> list[dict]:
    """Exploratory one-seed sweep to isolate native coupling vs damping."""
    _, partitions, _ = load_frozen_partitions()
    examples = _readout_examples(partitions["train"].seeds, _readout_target_matrices())
    lib = load_gfe_library(os.environ["GFE_CORE_LIB"])
    results = []
    for edge_gain in (1.0, 0.25, 0.1, 0.05, 0.01):
        for decay in (0.05, 0.5, 1.0, 2.0, 5.0):
            banks = [SOEMemory(feature_dim=16) for _ in range(3)]
            kernels = [
                {
                    "gamma": bank.decay_rates[::-1].tolist(),
                    "w": [0.25] * bank.channel_count,
                    "linear_decay": [decay] * (bank.channel_count * bank.feature_dim),
                    "forcing_bias": [0.0] * (bank.channel_count * bank.feature_dim),
                }
                for bank in banks
            ]
            levels, edges = make_h0_chain_spec(banks, kernels, dt=0.01)
            for edge in edges:
                edge["gain"] = edge_gain
            runtime = create_persistent_hierarchy_runtime(lib, levels, edges)
            bridge = SOEHierarchyBridge(runtime, banks, dt=0.01)
            adapter = HLAAdapter(bridge, feature_dims=[16, 16, 16])
            adapter.fit_upper_readouts(*examples)
            director = HierarchicalRuntimeDirector(adapter)
            p6 = CoupledAdaptiveSystem(max_state_norm=25.0)
            rng = np.random.default_rng(seed)
            max_native = [0.0, 0.0, 0.0]
            max_p6 = 0.0
            first_p6_failure = None
            native_finite = True
            try:
                for tick in range(300):
                    feature = rng.uniform(-1.0, 1.0, size=16)
                    result = director.exchange(
                        event_time=(tick + 1) * 0.01,
                        observed_at=(tick + 1) * 0.01,
                        event_features={0: feature},
                    )
                    native_levels = result["result"]["native"]["level_states"]
                    for level_index, level in enumerate(native_levels):
                        values = np.asarray(level["u"], dtype=np.float64)
                        native_finite = native_finite and bool(np.all(np.isfinite(values)))
                        max_native[level_index] = max(max_native[level_index], float(np.linalg.norm(values)))
                    views = result["result"]["native_u_views"]
                    observation = np.asarray([np.mean(views[1]), np.mean(views[2])], dtype=np.float64)
                    try:
                        state = p6.step(observation, residual_score=3.0 if tick in (80, 190) else 0.0)
                        max_p6 = max(max_p6, float(np.linalg.norm(state)))
                    except FloatingPointError as exc:
                        first_p6_failure = {"tick": tick, "norm": float(np.linalg.norm(p6.state)),
                                            "message": str(exc)}
                        break
                results.append({
                    "edge_gain": edge_gain, "linear_decay": decay,
                    "native_max_level_norms": max_native,
                    "native_finite": native_finite,
                    "p6_max_norm": max_p6,
                    "p6_first_failure": first_p6_failure,
                    "native_steps": runtime.step_count,
                })
            finally:
                director.close()
    return results



def sweep_feedback_gain(seed: int = 950000) -> list[dict]:
    """Isolate whether repeated absolute SOE forcing drives native state growth."""
    _, partitions, _ = load_frozen_partitions()
    examples = _readout_examples(partitions["train"].seeds, _readout_target_matrices())
    lib = load_gfe_library(os.environ["GFE_CORE_LIB"])
    results = []
    for feedback_gain in (1.0, 0.1, 0.01, 0.005, 0.001):
        banks = [SOEMemory(feature_dim=16) for _ in range(3)]
        kernels = [
            {
                "gamma": bank.decay_rates[::-1].tolist(),
                "w": [0.25] * bank.channel_count,
                "linear_decay": [0.05] * (bank.channel_count * bank.feature_dim),
                "forcing_bias": [0.0] * (bank.channel_count * bank.feature_dim),
            }
            for bank in banks
        ]
        levels, edges = make_h0_chain_spec(banks, kernels, dt=0.01)
        runtime = create_persistent_hierarchy_runtime(lib, levels, edges)
        original_step = runtime.step

        def scaled_step(feedback_by_level=None, *, scale=feedback_gain):
            scaled = {
                int(level): (np.asarray(values, dtype=np.float64) * scale).tolist()
                for level, values in (feedback_by_level or {}).items()
            }
            return original_step(scaled)

        runtime.step = scaled_step
        bridge = SOEHierarchyBridge(runtime, banks, dt=0.01)
        adapter = HLAAdapter(bridge, feature_dims=[16, 16, 16])
        adapter.fit_upper_readouts(*examples)
        director = HierarchicalRuntimeDirector(adapter)
        p6 = CoupledAdaptiveSystem(max_state_norm=25.0)
        rng = np.random.default_rng(seed)
        max_native = [0.0, 0.0, 0.0]
        max_p6 = 0.0
        first_failure = None
        try:
            for tick in range(300):
                result = director.exchange(
                    event_time=(tick + 1) * 0.01,
                    observed_at=(tick + 1) * 0.01,
                    event_features={0: rng.uniform(-1.0, 1.0, size=16)},
                )
                native_levels = result["result"]["native"]["level_states"]
                for level_index, level in enumerate(native_levels):
                    values = np.asarray(level["u"], dtype=np.float64)
                    max_native[level_index] = max(max_native[level_index], float(np.linalg.norm(values)))
                views = result["result"]["native_u_views"]
                observation = np.asarray([np.mean(views[1]), np.mean(views[2])], dtype=np.float64)
                try:
                    state = p6.step(observation, residual_score=3.0 if tick in (80, 190) else 0.0)
                    max_p6 = max(max_p6, float(np.linalg.norm(state)))
                except FloatingPointError as exc:
                    first_failure = {"tick": tick, "norm": float(np.linalg.norm(p6.state)),
                                     "message": str(exc)}
                    break
            results.append({
                "feedback_gain": feedback_gain,
                "native_max_level_norms": max_native,
                "p6_max_norm": max_p6,
                "p6_first_failure": first_failure,
                "native_steps": runtime.step_count,
            })
        finally:
            director.close()
    return results



def sweep_readout_modes(seed: int = 950000) -> list[dict]:
    """Isolate long-horizon native growth caused by learned upper readouts."""
    _, partitions, _ = load_frozen_partitions()
    examples = _readout_examples(partitions["train"].seeds, _readout_target_matrices())
    lib = load_gfe_library(os.environ["GFE_CORE_LIB"])
    results = []
    for mode in ("trained", "untrained", "explicit_zero", "clipped", "scaled_0.1"):
        banks = [SOEMemory(feature_dim=16) for _ in range(3)]
        kernels = [
            {
                "gamma": bank.decay_rates[::-1].tolist(),
                "w": [0.25] * bank.channel_count,
                "linear_decay": [0.05] * (bank.channel_count * bank.feature_dim),
                "forcing_bias": [0.0] * (bank.channel_count * bank.feature_dim),
            }
            for bank in banks
        ]
        levels, edges = make_h0_chain_spec(banks, kernels, dt=0.01)
        runtime = create_persistent_hierarchy_runtime(lib, levels, edges)
        bridge = SOEHierarchyBridge(runtime, banks, dt=0.01)
        adapter = HLAAdapter(bridge, feature_dims=[16, 16, 16])
        if mode != "untrained":
            adapter.fit_upper_readouts(*examples)
        weight_norms = [
            float(np.linalg.norm(readout.weights)) if readout.fitted else 0.0
            for readout in adapter.readouts
        ]
        spectral_norms = [
            float(np.linalg.norm(readout.weights, ord=2)) if readout.fitted else 0.0
            for readout in adapter.readouts
        ]
        if mode in ("clipped", "scaled_0.1"):
            for readout in adapter.readouts:
                original_predict = readout.predict
                if mode == "clipped":
                    readout.predict = lambda x, fn=original_predict: np.clip(fn(x), -1.0, 1.0)
                else:
                    readout.predict = lambda x, fn=original_predict: 0.1 * fn(x)
        director = HierarchicalRuntimeDirector(adapter)
        p6 = CoupledAdaptiveSystem(max_state_norm=25.0)
        rng = np.random.default_rng(seed)
        max_native = [0.0, 0.0, 0.0]
        max_p6 = 0.0
        first_failure = None
        try:
            for tick in range(300):
                features = {0: rng.uniform(-1.0, 1.0, size=16)}
                if mode == "explicit_zero":
                    features[1] = np.zeros(16)
                    features[2] = np.zeros(16)
                result = director.exchange(
                    event_time=(tick + 1) * 0.01,
                    observed_at=(tick + 1) * 0.01,
                    event_features=features,
                )
                native_levels = result["result"]["native"]["level_states"]
                for level_index, level in enumerate(native_levels):
                    values = np.asarray(level["u"], dtype=np.float64)
                    max_native[level_index] = max(max_native[level_index], float(np.linalg.norm(values)))
                views = result["result"]["native_u_views"]
                observation = np.asarray([np.mean(views[1]), np.mean(views[2])], dtype=np.float64)
                try:
                    state = p6.step(observation, residual_score=3.0 if tick in (80, 190) else 0.0)
                    max_p6 = max(max_p6, float(np.linalg.norm(state)))
                except FloatingPointError as exc:
                    first_failure = {"tick": tick, "norm": float(np.linalg.norm(p6.state)),
                                     "message": str(exc)}
                    break
            results.append({
                "readout_mode": mode,
                "readout_weight_frobenius_norms": weight_norms,
                "readout_weight_spectral_norms": spectral_norms,
                "native_max_level_norms": max_native,
                "p6_max_norm": max_p6,
                "p6_first_failure": first_failure,
                "native_steps": runtime.step_count,
            })
        finally:
            director.close()
    return results


def main():
    if os.environ.get("ABERCONICS_COMMIT") != M4_COMMIT:
        raise RuntimeError("diagnostic must use the pinned M4 source")
    results = [
        run_one(architecture, 950000, control_enabled=enabled)
        for architecture in ("HLA", "HLB")
        for enabled in (False, True)
    ]
    readout_modes = sweep_readout_modes(950000)
    reduced_gain = [
        run_one(architecture, 950000, control_enabled=True,
                readout_gain=0.1, control_gain=0.1)
        for architecture in ("HLA", "HLB")
    ]
    print(json.dumps({"diagnostic_only": True, "control_isolation": results,
                      "readout_mode_sweep": readout_modes,
                      "reduced_gain_closed_loop": reduced_gain}, indent=2))


if __name__ == "__main__":
    main()
