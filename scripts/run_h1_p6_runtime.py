#!/usr/bin/env python3
"""Run frozen P6 closed-loop stability and rollback campaign on compiled M4."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from rgm.experiments.h1_hierarchical_campaign import (
    M4_RUNTIME_COMMIT,
    _new_session,
    _readout_examples,
    _readout_target_matrices,
    load_frozen_partitions,
)
from rgm.leptograph.m4.p6_runtime import P6RuntimeCoupler
from rgm.leptograph.m4.stability import CoupledAdaptiveSystem

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/experiments/HLG_H1_P6_ACTUAL_RUNTIME_v2.json"
SIDECAR = ROOT / "docs/experiments/HLG_H1_P6_ACTUAL_RUNTIME_v2.sha256"
SOURCE_FILES = (
    "src/rgm/leptograph/m4/composition.py",
    "src/rgm/leptograph/m4/soe_bridge.py",
    "src/rgm/leptograph/m4/hierarchical.py",
    "src/rgm/leptograph/m4/stability.py",
    "src/rgm/leptograph/m4/p6_runtime.py",
    "src/rgm/experiments/h1_hierarchical_campaign.py",
    "scripts/run_h1_p6_runtime.py",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_hash() -> str:
    digest = hashlib.sha256()
    for relative in SOURCE_FILES:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update((ROOT / relative).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_protocol():
    raw = PROTOCOL.read_bytes()
    expected = SIDECAR.read_text(encoding="utf-8").split()[0]
    if _sha256(raw) != expected:
        raise RuntimeError("P6 protocol checksum mismatch")
    config = json.loads(raw)
    seeds = tuple(range(config["seed_range"][0], config["seed_range"][1] + 1))
    seed_hash = hashlib.sha256(",".join(map(str, seeds)).encode()).hexdigest()
    if len(seeds) != config["seed_count"] or seed_hash != config["seed_list_sha256"]:
        raise RuntimeError("P6 seed manifest mismatch")
    expected_commit = config.get("implementation_commit")
    actual_commit = os.environ.get("P6_IMPLEMENTATION_COMMIT")
    if not expected_commit or actual_commit != expected_commit:
        raise RuntimeError("P6 implementation commit does not match the frozen protocol")
    return config, seeds, _sha256(raw)


def _native_state_metrics(result):
    native = result["hierarchy"]["result"]["native"]
    maximum = 0.0
    finite = True
    for level in native["level_states"]:
        for key in ("u", "chi"):
            values = np.asarray(level[key], dtype=np.float64)
            finite = finite and bool(np.all(np.isfinite(values)))
            maximum = max(maximum, float(np.linalg.norm(values)))
    return finite, maximum


def _fit_candidate(seed: int):
    truth = np.asarray([[0.8, 0.1], [0.1, 0.7]], dtype=np.float64)
    fit_rng = np.random.default_rng(seed + 1000003)
    val_rng = np.random.default_rng(seed + 2000003)
    x_fit = fit_rng.normal(size=(128, 2))
    y_fit = x_fit @ truth.T + fit_rng.normal(scale=0.05, size=(128, 2))
    fitted = np.linalg.lstsq(x_fit, y_fit, rcond=None)[0].T
    x_val = val_rng.normal(size=(128, 2))
    y_val = x_val @ truth.T + val_rng.normal(scale=0.05, size=(128, 2))
    prior = np.eye(2, dtype=np.float64)
    incumbent_loss = float(np.mean((x_val @ prior.T - y_val) ** 2))
    candidate_loss = float(np.mean((x_val @ fitted.T - y_val) ** 2))
    identifiable = bool(np.linalg.matrix_rank(x_fit) == 2)
    return fitted, prior, incumbent_loss, candidate_loss, identifiable


def _run_architecture(architecture, lib, readout_examples, seeds, config):
    session = _new_session(architecture, lib, readout_examples)
    director = session["director"]
    coupler = P6RuntimeCoupler(
        director, hierarchy_lifecycle=session["lifecycle"],
        model=CoupledAdaptiveSystem(max_state_norm=float(config["p6_model"]["max_state_norm"])),
        readout_gain=float(config["coupling"]["readout_gain"]),
        control_gain=float(config["coupling"]["control_gain"]),
    )
    initial = coupler.checkpoint()
    rng = None
    rows = []
    p6_max_norm = 0.0
    native_max_norm = 0.0
    control_max_abs = 0.0
    native_finite = True
    total_native_steps = 0
    try:
        for seed in seeds:
            coupler.restore(initial)
            coupler.checkpoint()  # Reset the trusted point and rollback lineage per seed.
            rng = np.random.default_rng(seed)
            for tick in range(config["steps_per_seed"]):
                feature = rng.uniform(-1.0, 1.0, size=16).astype(float)
                residual = (
                    float(config["residual_spike_value"])
                    if tick in config["residual_spike_steps"] else 0.0
                )
                result = coupler.exchange(
                    event_time=(tick + 1) * 0.01,
                    observed_at=(tick + 1) * 0.01,
                    event_features={0: feature},
                    residual_score=residual,
                )
                finite, native_norm = _native_state_metrics(result)
                native_finite = native_finite and finite
                native_max_norm = max(native_max_norm, native_norm)
                p6_max_norm = max(p6_max_norm, result["p6_state_norm"])
                control_max_abs = max(
                    control_max_abs,
                    float(np.max(np.abs(result["p6_control"]))),
                )
                total_native_steps += 1

            model = coupler.model
            alarms = model.detector.alarms
            if alarms != 2:
                raise AssertionError(f"{architecture} seed {seed}: expected 2 CUSUM alarms, got {alarms}")
            if model.mode.value != "DETECT":
                raise AssertionError(f"{architecture} seed {seed}: expected DETECT mode, got {model.mode.value}")

            # Freeze the incumbent state before measuring a paired 20-step
            # continuation and testing a separately fitted candidate.
            pre_candidate = coupler.checkpoint()
            replay_inputs = [rng.uniform(-1.0, 1.0, size=16).astype(float) for _ in range(20)]
            for index, feature in enumerate(replay_inputs):
                result = coupler.exchange(
                    event_time=(config["steps_per_seed"] + index + 1) * 0.01,
                    observed_at=(config["steps_per_seed"] + index + 1) * 0.01,
                    event_features={0: feature}, residual_score=0.0,
                )
                finite, native_norm = _native_state_metrics(result)
                native_finite = native_finite and finite
                native_max_norm = max(native_max_norm, native_norm)
                p6_max_norm = max(p6_max_norm, result["p6_state_norm"])
                total_native_steps += 1
            incumbent_continuation = coupler.snapshot()

            coupler.restore(pre_candidate)
            fitted, prior, incumbent_loss, candidate_loss, identifiable = _fit_candidate(seed)
            coupler.start_candidate(fitted)
            promoted = coupler.validate_candidate(
                incumbent_loss=incumbent_loss,
                candidate_loss=candidate_loss,
                identifiable=identifiable,
            )
            if not promoted:
                raise AssertionError(f"{architecture} seed {seed}: independently validated candidate was not promoted")
            if not np.array_equal(coupler.model.revision.accepted_operator, fitted):
                raise AssertionError("promoted P6 operator differs from fitted candidate")

            for index, feature in enumerate(replay_inputs):
                result = coupler.exchange(
                    event_time=(config["steps_per_seed"] + index + 1) * 0.01,
                    observed_at=(config["steps_per_seed"] + index + 1) * 0.01,
                    event_features={0: feature}, residual_score=0.0,
                )
                finite, native_norm = _native_state_metrics(result)
                native_finite = native_finite and finite
                native_max_norm = max(native_max_norm, native_norm)
                p6_max_norm = max(p6_max_norm, result["p6_state_norm"])
                total_native_steps += 1

            # Exercise the model-level rollback first, then restore the entire
            # hierarchy/native/P6 composite to the pre-candidate checkpoint.
            coupler.model.rollback()
            operator_rollback = np.array_equal(
                coupler.model.revision.accepted_operator, prior
            ) and coupler.model.rollback_count == 1
            coupler.rollback()
            composite_rollback = coupler.snapshot()["fingerprint"] == pre_candidate["fingerprint"]
            if not operator_rollback or not composite_rollback:
                raise AssertionError(f"{architecture} seed {seed}: P6 rollback contract failed")

            for index, feature in enumerate(replay_inputs):
                result = coupler.exchange(
                    event_time=(config["steps_per_seed"] + index + 1) * 0.01,
                    observed_at=(config["steps_per_seed"] + index + 1) * 0.01,
                    event_features={0: feature}, residual_score=0.0,
                )
                finite, native_norm = _native_state_metrics(result)
                native_finite = native_finite and finite
                native_max_norm = max(native_max_norm, native_norm)
                p6_max_norm = max(p6_max_norm, result["p6_state_norm"])
                total_native_steps += 1
            replayed_continuation = coupler.snapshot()
            replay_equal = (
                replayed_continuation["fingerprint"]
                == incumbent_continuation["fingerprint"]
            )
            if not replay_equal:
                raise AssertionError(f"{architecture} seed {seed}: incumbent replay diverged after composite rollback")

            rows.append({
                "seed": int(seed),
                "cusum_alarms": int(alarms),
                "p6_max_norm": float(model.max_observed_norm),
                "transition_spectral_radius": model.transition_spectral_radius,
                "incumbent_validation_loss": incumbent_loss,
                "candidate_validation_loss": candidate_loss,
                "validation_improvement": incumbent_loss - candidate_loss,
                "candidate_promoted": bool(promoted),
                "operator_rollback_exact": bool(operator_rollback),
                "composite_rollback_exact": bool(composite_rollback),
                "incumbent_replay_exact": bool(replay_equal),
            })

        return {
            "architecture": architecture,
            "seed_count": len(seeds),
            "steps_per_seed_before_candidate": config["steps_per_seed"],
            "native_steps_total": total_native_steps,
            "max_p6_state_norm": p6_max_norm,
            "max_native_level_state_norm": native_max_norm,
            "max_abs_p6_control": control_max_abs,
            "native_state_finite_all_steps": native_finite,
            "mean_validation_improvement": float(np.mean([r["validation_improvement"] for r in rows])),
            "candidate_promotions": sum(r["candidate_promoted"] for r in rows),
            "operator_rollback_exact_count": sum(r["operator_rollback_exact"] for r in rows),
            "composite_rollback_exact_count": sum(r["composite_rollback_exact"] for r in rows),
            "incumbent_replay_exact_count": sum(r["incumbent_replay_exact"] for r in rows),
            "cusum_alarm_counts": sorted(set(r["cusum_alarms"] for r in rows)),
            "transition_spectral_radius": float(rows[0]["transition_spectral_radius"]),
            "rows": rows,
        }
    finally:
        coupler.close()


def run_p6_runtime_campaign(output_path: str | Path | None = None) -> dict:
    config, seeds, protocol_sha = _load_protocol()
    from gfe_ctypes import load_gfe_library
    library_path = os.environ.get("GFE_CORE_LIB")
    if not library_path:
        raise RuntimeError("GFE_CORE_LIB must point to the compiled M4 shared library")
    actual_m4_commit = os.environ.get("ABERCONICS_COMMIT")
    if actual_m4_commit != M4_RUNTIME_COMMIT:
        raise RuntimeError("P6 runtime source does not match the frozen M4 commit")
    lib = load_gfe_library(library_path)
    partitions_config, partitions, _ = load_frozen_partitions()
    matrices = _readout_target_matrices()
    train_examples = _readout_examples(partitions["train"].seeds, matrices)
    results = {
        architecture: _run_architecture(architecture, lib, train_examples, seeds, config)
        for architecture in ("HLA", "HLB")
    }
    acceptance = config["acceptance"]
    checks = {
        "HLA_P6_finite_horizon_norm_below_25": results["HLA"]["max_p6_state_norm"] < 25.0,
        "HLB_P6_finite_horizon_norm_below_25": results["HLB"]["max_p6_state_norm"] < 25.0,
        "HLA_transition_spectral_radius_below_1": results["HLA"]["transition_spectral_radius"] < 1.0,
        "HLB_transition_spectral_radius_below_1": results["HLB"]["transition_spectral_radius"] < 1.0,
        "HLA_native_state_finite": results["HLA"]["native_state_finite_all_steps"],
        "HLB_native_state_finite": results["HLB"]["native_state_finite_all_steps"],
        "HLA_exactly_two_alarms_per_seed": results["HLA"]["cusum_alarm_counts"] == [2],
        "HLB_exactly_two_alarms_per_seed": results["HLB"]["cusum_alarm_counts"] == [2],
        "HLA_all_candidates_promoted": results["HLA"]["candidate_promotions"] == len(seeds),
        "HLB_all_candidates_promoted": results["HLB"]["candidate_promotions"] == len(seeds),
        "HLA_operator_rollback_exact": results["HLA"]["operator_rollback_exact_count"] == len(seeds),
        "HLB_operator_rollback_exact": results["HLB"]["operator_rollback_exact_count"] == len(seeds),
        "HLA_composite_rollback_exact": results["HLA"]["composite_rollback_exact_count"] == len(seeds),
        "HLB_composite_rollback_exact": results["HLB"]["composite_rollback_exact_count"] == len(seeds),
        "HLA_incumbent_replay_exact": results["HLA"]["incumbent_replay_exact_count"] == len(seeds),
        "HLB_incumbent_replay_exact": results["HLB"]["incumbent_replay_exact_count"] == len(seeds),
    }
    result = {
        "protocol_id": config["protocol_id"],
        "protocol_sha256": protocol_sha,
        "seed_range": list(config["seed_range"]),
        "seed_count": len(seeds),
        "architectures": results,
        "acceptance": {"checks": checks, "passed": all(checks.values())},
        "runtime": {
            "m4_source_commit": M4_RUNTIME_COMMIT,
            "shared_library_sha256": _sha256(Path(library_path).read_bytes()),
            "p6_source_sha256": _source_hash(),
        },
        "result": "PASS" if all(checks.values()) else "FAIL",
        "claim_boundary": config["claim_boundary"],
    }
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run_p6_runtime_campaign(args.output)
    print(json.dumps({
        "result": result["result"],
        "seed_count": result["seed_count"],
        "acceptance": result["acceptance"],
        "architectures": {
            name: {key: value for key, value in item.items() if key != "rows"}
            for name, item in result["architectures"].items()
        },
        "runtime": result["runtime"],
        "output": args.output,
    }, indent=2))
    if result["result"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
