#!/usr/bin/env python3
"""Smoke-test HLA and HLB against the compiled Aberconics M4 C++ runtime.

This is an integration test, not an architecture-performance experiment.
It verifies real ctypes/native handle creation, stepping, composite checkpoint
continuation, architecture-state restoration, and native handle destruction.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ABERCONICS_PYTHON = Path(os.environ["ABERCONICS_PYTHON"])
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ABERCONICS_PYTHON))

from gfe_ctypes import create_persistent_hierarchy_runtime, load_gfe_library
from rgm.memory import SOEMemory
from rgm.leptograph.m4.composition import Entity, RelationInstance, RelationType
from rgm.leptograph.m4.hierarchical import (
    CompositeLifecycle,
    HLAAdapter,
    HLBAdapter,
    HierarchicalRuntimeDirector,
    ReadoutExample,
    create_hla_adapter,
    create_hlb_adapter,
)


DT = 0.01
FEATURE_DIMS = (3, 3, 3)


def fresh_banks():
    return [SOEMemory(feature_dim=d) for d in FEATURE_DIMS]


def kernel_specs(banks):
    return [
        {
            # Native ABI requires descending gamma; SOE channel ordering is
            # left untouched because native chi/kernel state is separate.
            "gamma": bank.decay_rates[::-1].tolist(),
            "w": [0.25] * bank.channel_count,
            "linear_decay": [0.05] * (bank.channel_count * bank.feature_dim),
            "forcing_bias": [0.0] * (bank.channel_count * bank.feature_dim),
        }
        for bank in banks
    ]


def train_hla_readouts(adapter):
    adapter.fit_upper_readouts(
        [
            ReadoutExample(tuple([0.0] * 12), tuple([0.0] * 3)),
            ReadoutExample(tuple([1.0] * 12), tuple([1.0] * 3)),
        ],
        [
            ReadoutExample(tuple([0.0] * 12), tuple([0.0] * 3)),
            ReadoutExample(tuple([1.0] * 12), tuple([1.0] * 3)),
        ],
    )


def assert_native_equal(left, right, *, label):
    assert left["step_count"] == right["step_count"], label + ": step_count"
    for level, (a, b) in enumerate(zip(left["level_states"], right["level_states"])):
        for key in ("u", "chi", "t"):
            np.testing.assert_allclose(a[key], b[key], rtol=0.0, atol=1e-12,
                                       err_msg=f"{label}: level {level} {key}")
    for level, (a, b) in enumerate(zip(left["active_kernels"], right["active_kernels"])):
        for key in ("gamma", "w"):
            np.testing.assert_allclose(a[key], b[key], rtol=0.0, atol=1e-12,
                                       err_msg=f"{label}: kernel {level} {key}")


def exercise_hla(lib):
    banks = fresh_banks()
    adapter = create_hla_adapter(
        lib, banks, kernel_specs(banks), dt=DT,
        runtime_factory=create_persistent_hierarchy_runtime,
    )
    train_hla_readouts(adapter)
    director = HierarchicalRuntimeDirector(adapter)
    lifecycle = CompositeLifecycle(director)
    try:
        director.exchange(event_time=DT, observed_at=DT,
                          event_features={0: [0.2, -0.1, 0.3]})
        checkpoint = lifecycle.checkpoint()
        assert checkpoint["native"]["step_count"] == 1

        director.exchange(event_time=2 * DT, observed_at=2 * DT,
                          event_features={0: [-0.4, 0.5, 0.1]})
        expected_native = adapter.bridge.runtime.get_state()
        expected_soe = [bank.snapshot() for bank in banks]

        lifecycle.restore(checkpoint)
        assert adapter.bridge.runtime.step_count == 1
        director.exchange(event_time=2 * DT, observed_at=2 * DT,
                          event_features={0: [-0.4, 0.5, 0.1]})
        actual_native = adapter.bridge.runtime.get_state()
        assert_native_equal(expected_native, actual_native, label="HLA continuation")
        for index, (expected, actual) in enumerate(zip(expected_soe, banks)):
            np.testing.assert_allclose(expected, actual.snapshot(), rtol=0.0, atol=1e-12,
                                       err_msg=f"HLA SOE bank {index} continuation")
        assert director.event_tick == 2
        assert adapter.bridge.runtime.step_count == 2
        return {"architecture": "HLA", "native_steps": 2, "checkpoint_restore": "PASS"}
    finally:
        director.close()


def exercise_hlb(lib):
    banks = fresh_banks()
    adapter = create_hlb_adapter(
        lib, banks, kernel_specs(banks), dt=DT,
        runtime_factory=create_persistent_hierarchy_runtime,
        capacity=32,
    )
    director = HierarchicalRuntimeDirector(adapter)
    lifecycle = CompositeLifecycle(director)
    subject = Entity("smoke-person", "person")
    place = Entity("smoke-place", "place")
    relation = RelationType("located_at", "person", "place")
    record = RelationInstance("smoke-edge-1", relation, subject, place, DT, DT)
    try:
        assert adapter.observe(0, record) == "STORED"
        director.exchange(event_time=DT, observed_at=DT,
                          event_features={0: [0.2, -0.1, 0.3],
                                          1: [0.1, 0.2, -0.2],
                                          2: [-0.1, 0.3, 0.2]})
        checkpoint = lifecycle.checkpoint()
        assert checkpoint["native"]["step_count"] == 1

        director.exchange(event_time=2 * DT, observed_at=2 * DT,
                          event_features={0: [-0.4, 0.5, 0.1],
                                          1: [0.3, -0.2, 0.1],
                                          2: [0.2, 0.1, -0.3]})
        expected_native = adapter.bridge.runtime.get_state()
        expected_soe = [bank.snapshot() for bank in banks]
        expected_store = adapter.store.snapshot()

        lifecycle.restore(checkpoint)
        assert adapter.bridge.runtime.step_count == 1
        assert adapter.store.count == 1
        director.exchange(event_time=2 * DT, observed_at=2 * DT,
                          event_features={0: [-0.4, 0.5, 0.1],
                                          1: [0.3, -0.2, 0.1],
                                          2: [0.2, 0.1, -0.3]})
        actual_native = adapter.bridge.runtime.get_state()
        assert_native_equal(expected_native, actual_native, label="HLB continuation")
        for index, (expected, actual) in enumerate(zip(expected_soe, banks)):
            np.testing.assert_allclose(expected, actual.snapshot(), rtol=0.0, atol=1e-12,
                                       err_msg=f"HLB SOE bank {index} continuation")
        assert adapter.store.snapshot() == expected_store
        assert director.event_tick == 2
        assert adapter.bridge.runtime.step_count == 2
        return {"architecture": "HLB", "native_steps": 2, "checkpoint_restore": "PASS",
                "relation_records_after_restore": adapter.store.count}
    finally:
        director.close()


def main():
    lib_path = os.environ.get("GFE_CORE_LIB")
    if not lib_path or not Path(lib_path).is_file():
        raise SystemExit("GFE_CORE_LIB must point to the freshly compiled shared library")
    lib = load_gfe_library(lib_path)
    results = [exercise_hla(lib), exercise_hlb(lib)]
    print(json.dumps({
        "result": "PASS",
        "library": str(Path(lib_path).resolve()),
        "m4_commit": os.environ.get("ABERCONICS_COMMIT", "unknown"),
        "architectures": results,
    }, indent=2))


if __name__ == "__main__":
    main()
