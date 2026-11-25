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
from gfe_ctypes import load_gfe_library

ROOT = Path(__file__).resolve().parents[1]
M4_COMMIT = "2539df6bda7ef3c9dd7c707abe26eff8bdbb59de"


def run_one(architecture: str, seed: int, *, control_enabled: bool) -> dict:
    _, partitions, _ = load_frozen_partitions()
    examples = _readout_examples(partitions["train"].seeds, _readout_target_matrices())
    lib = load_gfe_library(os.environ["GFE_CORE_LIB"])
    session = _new_session(architecture, lib, examples)
    coupler = P6RuntimeCoupler(
        session["director"], hierarchy_lifecycle=session["lifecycle"],
        model=CoupledAdaptiveSystem(max_state_norm=25.0),
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
            "seed": seed, "first_failure_tick": None,
            "max_native_norm": max_native, "max_p6_norm": max_p6,
            "detector_alarms": coupler.model.detector.alarms,
            "p6_state": coupler.model.state.tolist(),
        }
    finally:
        coupler.close()


def main():
    if os.environ.get("ABERCONICS_COMMIT") != M4_COMMIT:
        raise RuntimeError("diagnostic must use the pinned M4 source")
    results = [
        run_one(architecture, 950000, control_enabled=enabled)
        for architecture in ("HLA", "HLB")
        for enabled in (False, True)
    ]
    print(json.dumps({"diagnostic_only": True, "results": results}, indent=2))


if __name__ == "__main__":
    main()
