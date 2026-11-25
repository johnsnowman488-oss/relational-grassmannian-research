"""Matched HLA/HLB hierarchical campaign using independent typed worlds.

The runner deliberately evaluates the architecture boundary: HLA receives a
current evidence window; HLB retains the same observed relation instances in a
bounded canonical store. Both use identical SOE banks, fitted upper readouts,
native runtime configuration, query semantics and P0 witness composition.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import sys
from typing import Iterable, Mapping, Sequence

import numpy as np

from rgm.memory import SOEMemory
from rgm.leptograph.m4.composition import (
    Entity, RelationInstance, RelationType, CompositionWitness,
)
from rgm.leptograph.m4.hierarchical import (
    CompositeLifecycle, HLAAdapter, HLBAdapter, HierarchicalRuntimeDirector,
    ReadoutExample, create_hla_adapter, create_hlb_adapter,
)
from rgm.experiments.m4_confirmatory_worlds import (
    WorldPartition, condition_world, default_partitions, generate_order_world,
    generate_world, partition_manifest, validate_partitions,
)

ROOT = Path(__file__).resolve().parents[3]
PARTITION_CONFIG = ROOT / "docs/experiments/HLG_H1_HIERARCHICAL_PARTITIONS_v1.json"
PARTITION_SIDECAR = ROOT / "docs/experiments/HLG_H1_HIERARCHICAL_PARTITIONS_v1.sha256"
SOURCE_FILES = (
    "src/rgm/leptograph/m4/composition.py",
    "src/rgm/leptograph/m4/soe_bridge.py",
    "src/rgm/leptograph/m4/hierarchical.py",
    "src/rgm/experiments/h1_hierarchical_campaign.py",
    "scripts/run_h1_hierarchical_campaign.py",
)
M4_RUNTIME_COMMIT = "2539df6bda7ef3c9dd7c707abe26eff8bdbb59de"
DT = 0.01
FEATURE_DIM = 16
RIDGE = 1e-6
BOOTSTRAP_RESAMPLES = 10000
TASK_GENERATORS = (
    ("heterogeneous_typed_chain", generate_world),
    ("homogeneous_order_sensitive", generate_order_world),
)
NEGATIVE_CONDITIONS = ("missing_target_edge", "wrong_context_target", "temporal_invalid_target")
G3_CONDITIONS = NEGATIVE_CONDITIONS + ("multiple_target_witnesses",)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def campaign_source_sha256(root: Path = ROOT) -> str:
    digest = hashlib.sha256()
    for relative in SOURCE_FILES:
        path = root / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def load_frozen_partitions() -> tuple[dict, dict[str, WorldPartition], str]:
    raw = PARTITION_CONFIG.read_bytes()
    expected_sidecar = PARTITION_SIDECAR.read_text(encoding="utf-8").split()[0]
    config_sha = _sha256(raw)
    if config_sha != expected_sidecar:
        raise RuntimeError("H1 partition config SHA-256 does not match its sidecar")
    config = json.loads(raw)
    if config.get("protocol_id") != "HLG-H1-HIERARCHICAL-PARTITIONS-v1":
        raise RuntimeError("unexpected H1 partition protocol")
    if config.get("confirmatory_test_accessed") is not False:
        raise RuntimeError("frozen partition manifest must keep confirmatory test sealed")
    parts = []
    for name in ("train", "validation", "confirmatory_test"):
        record = config["partitions"][name]
        seeds = tuple(range(int(record["first_seed"]), int(record["last_seed"]) + 1))
        digest = hashlib.sha256(",".join(map(str, seeds)).encode()).hexdigest()
        if len(seeds) != int(record["count"]) or digest != record["seed_list_sha256"]:
            raise RuntimeError(f"frozen seed list mismatch for {name}")
        parts.append(WorldPartition(name, seeds))
    validate_partitions(parts)
    manifest = partition_manifest(parts)
    manifest_sha = _sha256(json.dumps(
        manifest, sort_keys=True, separators=(",", ":")
    ).encode("utf-8"))
    if manifest_sha != config["partition_manifest_sha256"]:
        raise RuntimeError("H1 partition manifest hash mismatch")
    prior = config["prior_partition_separation"]["prior_seed_ranges"]
    new_sets = [set(part.seeds) for part in parts]
    for prior_range in prior.values():
        old = set(range(int(prior_range[0]), int(prior_range[1]) + 1))
        if any(old.intersection(new) for new in new_sets):
            raise RuntimeError("new hierarchical partition overlaps prior flat A/B partition")
    return config, {part.name: part for part in parts}, config_sha


def _readout_target_matrices() -> tuple[np.ndarray, np.ndarray]:
    first = np.random.default_rng(20261125).normal(0.0, 0.03, size=(64, FEATURE_DIM))
    second = np.random.default_rng(20261126).normal(0.0, 0.03, size=(64, FEATURE_DIM))
    return first, second


def _readout_sample(seed: int, level: int, matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(int(seed) * 31 + level * 100003)
    memory = SOEMemory(feature_dim=FEATURE_DIM)
    for _ in range(6):
        memory.update(rng.normal(0.0, 0.5, FEATURE_DIM), dt=DT)
    trace = memory.snapshot().reshape(-1)
    target = trace @ matrix
    return trace, target


def _readout_examples(seeds: Sequence[int], matrices: tuple[np.ndarray, np.ndarray]):
    examples = []
    for level, matrix in enumerate(matrices):
        level_examples = []
        for seed in seeds:
            trace, target = _readout_sample(seed, level, matrix)
            level_examples.append(ReadoutExample(
                tuple(float(v) for v in trace),
                tuple(float(v) for v in target),
            ))
        examples.append(level_examples)
    return examples


def _readout_metrics(adapter, seeds: Sequence[int], matrices) -> dict:
    squared = [[], []]
    for seed in seeds:
        for level, matrix in enumerate(matrices):
            trace, target = _readout_sample(seed, level, matrix)
            prediction = adapter.query_readout(level + 1, trace)
            squared[level].append(float(np.mean((prediction - target) ** 2)))
    return {
        "level_1_mse": float(np.mean(squared[0])),
        "level_2_mse": float(np.mean(squared[1])),
        "examples_per_level": len(seeds),
    }


def _new_banks() -> list[SOEMemory]:
    return [SOEMemory(feature_dim=FEATURE_DIM) for _ in range(3)]


def _kernel_specs(banks: Sequence[SOEMemory]) -> list[dict]:
    return [
        {
            "gamma": bank.decay_rates[::-1].tolist(),
            "w": [0.25] * bank.channel_count,
            "linear_decay": [0.05] * (bank.channel_count * bank.feature_dim),
            "forcing_bias": [0.0] * (bank.channel_count * bank.feature_dim),
        }
        for bank in banks
    ]


def _new_session(architecture: str, lib, readout_examples):
    banks = _new_banks()
    kernels = _kernel_specs(banks)
    if architecture == "HLA":
        adapter = create_hla_adapter(
            lib, banks, kernels, dt=DT,
            runtime_factory=_persistent_runtime_factory(),
            ridge=RIDGE,
        )
    elif architecture == "HLB":
        adapter = create_hlb_adapter(
            lib, banks, kernels, dt=DT,
            runtime_factory=_persistent_runtime_factory(),
            capacity=8192, ridge=RIDGE,
        )
    else:
        raise ValueError("architecture must be HLA or HLB")
    adapter.fit_upper_readouts(*readout_examples)
    director = HierarchicalRuntimeDirector(adapter)
    lifecycle = CompositeLifecycle(director)
    baseline = lifecycle.checkpoint()
    return {
        "architecture": architecture, "adapter": adapter, "director": director,
        "lifecycle": lifecycle, "baseline": baseline, "banks": banks,
    }


def _persistent_runtime_factory():
    from gfe_ctypes import create_persistent_hierarchy_runtime
    return create_persistent_hierarchy_runtime


def _reset(session) -> None:
    session["lifecycle"].restore(session["baseline"])


def _feature_vector(seed: int, mode: str) -> list[float]:
    mode_offset = 0 if mode == "heterogeneous_typed_chain" else 1000000
    rng = np.random.default_rng(int(seed) + mode_offset + 7717)
    return rng.normal(0.0, 0.25, FEATURE_DIM).astype(float).tolist()


def _store_level(record: RelationInstance) -> int:
    try:
        slot = int(record.relation_type.domain.rsplit("_T", 1)[1])
        return min(max(slot, 0), 2)
    except (IndexError, ValueError):
        return int(abs(record.event_time)) % 3


def _insert_hlb_events(session, events: Iterable[RelationInstance]) -> None:
    adapter = session["adapter"]
    if not isinstance(adapter, HLBAdapter):
        return
    for event in sorted(events, key=lambda e: (e.observed_at, e.event_time, e.instance_id)):
        status = adapter.observe(_store_level(event), event)
        if status == "ABSTAIN_CAPACITY":
            raise RuntimeError("HLB capacity exhausted during a frozen campaign task")


def _advance_native(session, seed: int, mode: str) -> None:
    session["director"].exchange(
        event_time=DT, observed_at=DT,
        event_features={0: _feature_vector(seed, mode)},
    )


def _future_sentinel(world) -> RelationInstance:
    from dataclasses import replace
    source = world.events[0]
    return replace(
        source, instance_id=f"{world.world_id}-future-sentinel",
        observed_at=world.observation_cutoff + 1.0,
    )


def _target_relation_path(world) -> tuple[RelationType, ...]:
    by_name = {relation.name: relation for relation in world.relation_types}
    return tuple(by_name[name] for name in world.oracle_target_path)


def _query(session, world, evidence, *, query_time: float, observation_cutoff: float):
    adapter = session["adapter"]
    path = _target_relation_path(world)
    if isinstance(adapter, HLAAdapter):
        return adapter.query(
            world.start, path, evidence=evidence, context="ctx",
            query_time=query_time, observation_cutoff=observation_cutoff,
        )
    return adapter.query(
        world.start, path, context="ctx", query_time=query_time,
        observation_cutoff=observation_cutoff,
    )


def _witness_valid(witness: CompositionWitness, world, path, cutoff: float, query_time: float) -> bool:
    if witness.endpoint != world.goal or len(witness.instances) != world.depth:
        return False
    if tuple(edge.relation_type.name for edge in witness.instances) != tuple(r.name for r in path):
        return False
    if len(set(witness.instance_ids)) != len(witness.instance_ids):
        return False
    for index, edge in enumerate(witness.instances):
        if witness.entities[index] != edge.subject or witness.entities[index + 1] != edge.object:
            return False
        if edge.observed_at > cutoff or edge.event_time > query_time:
            return False
        if index and edge.event_time < witness.instances[index - 1].event_time:
            return False
    return True


def _score_witnesses(witnesses, world, cutoff, query_time) -> dict:
    path = _target_relation_path(world)
    valid = [w for w in witnesses if _witness_valid(w, world, path, cutoff, query_time)]
    correct = [w for w in valid if w.endpoint == world.goal]
    invalid = len(witnesses) - len(valid)
    return {
        "correct": float(bool(correct)),
        "witness_count": len(witnesses),
        "valid_witness_count": len(valid),
        "invalid_witness_count": invalid,
        "witness_instance_ids": [list(w.instance_ids) for w in valid],
    }


def _worlds(seeds: Sequence[int]):
    for seed in seeds:
        depth = (2, 3, 4)[seed % 3]
        for mode, generator in TASK_GENERATORS:
            yield generator(seed, depth)


def _run_g1(sessions, world) -> list[dict]:
    view = world.learner_view()
    evidence = tuple(view.events) + (_future_sentinel(world),)
    feature_mode = world.mode
    output = []
    for architecture, session in sessions.items():
        _reset(session)
        _insert_hlb_events(session, evidence)
        _advance_native(session, world.seed, feature_mode)
        witnesses = _query(
            session, world, evidence, query_time=view.query_time,
            observation_cutoff=view.observation_cutoff,
        )
        score = _score_witnesses(witnesses, world, view.observation_cutoff, view.query_time)
        output.append({
            "campaign": "G1", "seed": world.seed, "world_id": world.world_id,
            "mode": world.mode, "depth": world.depth, "architecture": architecture,
            "future_sentinel_leaked": any(
                f"{world.world_id}-future-sentinel" in witness.instance_ids
                for witness in witnesses
            ),
            **score,
        })
    return output


def _run_g2(sessions, world) -> list[dict]:
    view = world.learner_view()
    evidence = tuple(view.events) + (_future_sentinel(world),)
    output = []
    # Retention and replay are paired against the same pre-ingested world.
    for architecture, session in sessions.items():
        _reset(session)
        _insert_hlb_events(session, evidence)
        _advance_native(session, world.seed, world.mode)
        no_replay_evidence = () if architecture == "HLA" else evidence
        replay_evidence = evidence
        for condition, supplied in (
            ("outage_no_replay", no_replay_evidence),
            ("outage_with_replay", replay_evidence),
        ):
            witnesses = _query(
                session, world, supplied,
                query_time=view.query_time + 8.0,
                observation_cutoff=view.observation_cutoff,
            )
            score = _score_witnesses(
                witnesses, world, view.observation_cutoff, view.query_time + 8.0
            )
            output.append({
                "campaign": "G2", "condition": condition, "seed": world.seed,
                "world_id": world.world_id, "mode": world.mode, "depth": world.depth,
                "architecture": architecture, **score,
            })

        # Stage a causal early observation cutoff immediately before the final
        # target edge becomes visible; then ingest late arrivals and re-query.
        _reset(session)
        target_edges = [
            edge for edge in world.events
            if "-target-edge-" in edge.instance_id
        ]
        last_target_observed = max(edge.observed_at for edge in target_edges)
        early_cutoff = max(0.0, last_target_observed - 1e-6)
        early_view = world.learner_view(early_cutoff)
        early_ids = {edge.instance_id for edge in early_view.events}
        late_events = tuple(edge for edge in view.events if edge.instance_id not in early_ids)
        _insert_hlb_events(session, early_view.events)
        _advance_native(session, world.seed, world.mode)
        early_evidence = early_view.events if architecture == "HLA" else ()
        early_witnesses = _query(
            session, world, early_evidence, query_time=early_view.query_time,
            observation_cutoff=early_cutoff,
        )
        early_score = _score_witnesses(
            early_witnesses, world, early_cutoff, early_view.query_time
        )
        _insert_hlb_events(session, late_events)
        late_evidence = view.events
        late_witnesses = _query(
            session, world, late_evidence, query_time=view.query_time,
            observation_cutoff=view.observation_cutoff,
        )
        late_score = _score_witnesses(
            late_witnesses, world, view.observation_cutoff, view.query_time
        )
        output.extend([
            {
                "campaign": "G2", "condition": "late_arrival_before_completion",
                "seed": world.seed, "world_id": world.world_id, "mode": world.mode,
                "depth": world.depth, "architecture": architecture, **early_score,
            },
            {
                "campaign": "G2", "condition": "late_arrival_after_completion",
                "seed": world.seed, "world_id": world.world_id, "mode": world.mode,
                "depth": world.depth, "architecture": architecture, **late_score,
            },
        ])
    return output


def _run_g3(sessions, world) -> list[dict]:
    output = []
    for condition in G3_CONDITIONS:
        conditioned = condition_world(world, condition)
        view = conditioned.learner_view()
        evidence = tuple(view.events) + (_future_sentinel(conditioned),)
        for architecture, session in sessions.items():
            _reset(session)
            _insert_hlb_events(session, evidence)
            _advance_native(session, world.seed, world.mode)
            witnesses = _query(
                session, conditioned, evidence,
                query_time=view.query_time,
                observation_cutoff=view.observation_cutoff,
            )
            score = _score_witnesses(
                witnesses, conditioned, view.observation_cutoff, view.query_time
            )
            expected_count = 2 if condition == "multiple_target_witnesses" else 0
            output.append({
                "campaign": "G3", "condition": condition, "seed": world.seed,
                "world_id": world.world_id, "mode": world.mode, "depth": world.depth,
                "architecture": architecture, "expected_witness_count": expected_count,
                "false_selection": float(
                    condition in NEGATIVE_CONDITIONS and score["correct"] > 0.0
                ),
                "multiple_witness_exact": bool(
                    condition != "multiple_target_witnesses"
                    or score["witness_count"] == expected_count
                ),
                **score,
            })
    return output


def _paired_bootstrap(rows: Sequence[Mapping], metric: str, *, condition: str | None = None) -> dict:
    selected = [row for row in rows if condition is None or row.get("condition") == condition]
    grouped: dict[int, dict[str, list[float]]] = {}
    for row in selected:
        grouped.setdefault(int(row["seed"]), {}).setdefault(str(row["architecture"]), []).append(
            float(row[metric])
        )
    paired = []
    for seed in sorted(grouped):
        if set(grouped[seed]) != {"HLA", "HLB"}:
            raise RuntimeError(f"unpaired architecture rows for seed {seed} / {condition}")
        a = float(np.mean(grouped[seed]["HLA"]))
        b = float(np.mean(grouped[seed]["HLB"]))
        paired.append((seed, a, b, b - a))
    if not paired:
        raise RuntimeError(f"no paired rows for {metric} / {condition}")
    differences = np.asarray([row[3] for row in paired], dtype=np.float64)
    rng = np.random.default_rng(20261125 + len(paired))
    draws = np.empty(BOOTSTRAP_RESAMPLES, dtype=np.float64)
    for index in range(BOOTSTRAP_RESAMPLES):
        sampled = rng.integers(0, len(paired), size=len(paired))
        draws[index] = float(np.mean(differences[sampled]))
    return {
        "metric": metric, "condition": condition,
        "paired_world_seeds": len(paired),
        "mean_HLA": float(np.mean([row[1] for row in paired])),
        "mean_HLB": float(np.mean([row[2] for row in paired])),
        "mean_HLB_minus_HLA": float(np.mean(differences)),
        "ci95_world_cluster_bootstrap": [
            float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))
        ],
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_unit": "world_seed",
    }


def _campaign_summary(g1, g2, g3) -> dict:
    g1_summary = {
        architecture: {
            "world_mode_rows": sum(row["architecture"] == architecture for row in g1),
            "correct_rate": float(np.mean([row["correct"] for row in g1 if row["architecture"] == architecture])),
            "invalid_witnesses": int(sum(row["invalid_witness_count"] for row in g1 if row["architecture"] == architecture)),
            "future_sentinel_leaks": int(sum(row["future_sentinel_leaked"] for row in g1 if row["architecture"] == architecture)),
        }
        for architecture in ("HLA", "HLB")
    }
    g2_summary = {
        condition: _paired_bootstrap(g2, "correct", condition=condition)
        for condition in (
            "outage_no_replay", "outage_with_replay",
            "late_arrival_before_completion", "late_arrival_after_completion",
        )
    }
    g3_summary = {}
    for condition in G3_CONDITIONS:
        rows = [row for row in g3 if row["condition"] == condition]
        g3_summary[condition] = {
            "HLA_mean_witness_count": float(np.mean([r["witness_count"] for r in rows if r["architecture"] == "HLA"])),
            "HLB_mean_witness_count": float(np.mean([r["witness_count"] for r in rows if r["architecture"] == "HLB"])),
            "false_selections": int(sum(r["false_selection"] for r in rows)),
            "invalid_witnesses": int(sum(r["invalid_witness_count"] for r in rows)),
            "multiple_witness_exact_failures": int(sum(not r["multiple_witness_exact"] for r in rows)),
            "paired_witness_count": _paired_bootstrap(g3, "witness_count", condition=condition),
        }
    return {
        "G1": {"by_architecture": g1_summary, "paired_correct_rate": _paired_bootstrap(g1, "correct")},
        "G2": g2_summary,
        "G3": g3_summary,
    }


def _hard_integrity(summary) -> dict:
    g1 = summary["G1"]["by_architecture"]
    g2 = summary["G2"]
    g3 = summary["G3"]
    checks = {
        "G1_HLA_full_evidence_correct": g1["HLA"]["correct_rate"] == 1.0,
        "G1_HLB_full_evidence_correct": g1["HLB"]["correct_rate"] == 1.0,
        "G1_no_invalid_witnesses": g1["HLA"]["invalid_witnesses"] == 0 and g1["HLB"]["invalid_witnesses"] == 0,
        "G1_no_future_sentinel_leaks": g1["HLA"]["future_sentinel_leaks"] == 0 and g1["HLB"]["future_sentinel_leaks"] == 0,
        "G2_HLA_abstains_without_replay": g2["outage_no_replay"]["mean_HLA"] == 0.0,
        "G2_HLB_retains_without_replay": g2["outage_no_replay"]["mean_HLB"] == 1.0,
        "G2_both_retrieve_with_replay": g2["outage_with_replay"]["mean_HLA"] == 1.0 and g2["outage_with_replay"]["mean_HLB"] == 1.0,
        "G2_both_wait_for_late_target_edge": g2["late_arrival_before_completion"]["mean_HLA"] == 0.0 and g2["late_arrival_before_completion"]["mean_HLB"] == 0.0,
        "G2_both_recover_after_late_arrival": g2["late_arrival_after_completion"]["mean_HLA"] == 1.0 and g2["late_arrival_after_completion"]["mean_HLB"] == 1.0,
        "G3_no_false_selections_on_negative_controls": all(g3[c]["false_selections"] == 0 for c in NEGATIVE_CONDITIONS),
        "G3_no_invalid_witnesses": all(g3[c]["invalid_witnesses"] == 0 for c in G3_CONDITIONS),
        "G3_multiple_witnesses_preserved": g3["multiple_target_witnesses"]["multiple_witness_exact_failures"] == 0,
    }
    return {"checks": checks, "passed": all(checks.values())}


def run_hierarchical_campaign(partition_name: str, output_path: str | Path | None = None) -> dict:
    if partition_name not in {"validation", "confirmatory_test"}:
        raise ValueError("partition_name must be validation or confirmatory_test")
    config, partitions, config_sha = load_frozen_partitions()
    if partition_name == "confirmatory_test":
        expected_source = config.get("campaign_source_sha256")
        actual_source = campaign_source_sha256()
        if not config.get("confirmatory_authorized") or not expected_source:
            raise RuntimeError("confirmatory campaign is not frozen/authorized for this implementation")
        if expected_source != actual_source:
            raise RuntimeError("campaign source hash differs from the frozen implementation hash")
    train_seeds = partitions["train"].seeds
    task_seeds = partitions[partition_name].seeds
    matrices = _readout_target_matrices()
    readout_examples = _readout_examples(train_seeds, matrices)

    from gfe_ctypes import load_gfe_library
    library_path = os.environ.get("GFE_CORE_LIB")
    if not library_path:
        raise RuntimeError("GFE_CORE_LIB must point to the compiled M4 shared library")
    expected_m4_commit = os.environ.get("ABERCONICS_COMMIT")
    if expected_m4_commit != M4_RUNTIME_COMMIT:
        raise RuntimeError("the checked-out M4 source commit does not match the frozen campaign runtime")
    lib = load_gfe_library(library_path)
    sessions = {
        architecture: _new_session(architecture, lib, readout_examples)
        for architecture in ("HLA", "HLB")
    }
    try:
        fingerprints = {
            architecture: [readout.fingerprint for readout in session["adapter"].readouts]
            for architecture, session in sessions.items()
        }
        if fingerprints["HLA"] != fingerprints["HLB"]:
            raise RuntimeError("matched HLA/HLB readout parameters differ")
        readout_metrics = {
            architecture: _readout_metrics(session["adapter"], partitions["validation"].seeds, matrices)
            for architecture, session in sessions.items()
        }
        g1, g2, g3 = [], [], []
        world_count = 0
        for world in _worlds(task_seeds):
            world_count += 1
            g1.extend(_run_g1(sessions, world))
            g2.extend(_run_g2(sessions, world))
            g3.extend(_run_g3(sessions, world))
        summary = _campaign_summary(g1, g2, g3)
        integrity = _hard_integrity(summary)
        result = {
            "protocol_id": config["protocol_id"],
            "partition": partition_name,
            "partition_config_sha256": config_sha,
            "partition_seed_range": [
                min(task_seeds), max(task_seeds)
            ],
            "world_seed_count": len(task_seeds),
            "world_instance_count": world_count,
            "task_modes": [name for name, _ in TASK_GENERATORS],
            "depths": [2, 3, 4],
            "architectures": ["HLA", "HLB"],
            "readout_calibration": {
                "train_seed_range": [min(train_seeds), max(train_seeds)],
                "train_seed_count": len(train_seeds),
                "validation_metrics": readout_metrics,
                "same_readout_fingerprints": True,
                "ridge": RIDGE,
                "target_matrix_sha256": [
                    _sha256(matrix.tobytes()) for matrix in matrices
                ],
                "claim_boundary": "synthetic fixed-linear upper-feature calibration only; not relational path selection",
            },
            "campaign_summary": summary,
            "hard_integrity": integrity,
            "raw_rows": {"G1": g1, "G2": g2, "G3": g3},
            "runtime": {
                "m4_source_commit": M4_RUNTIME_COMMIT,
                "shared_library_sha256": _sha256(Path(library_path).read_bytes()),
                "python": sys.version,
                "platform": platform.platform(),
                "campaign_source_sha256": campaign_source_sha256(),
                "native_steps_per_architecture": {
                    "HLA": sessions["HLA"]["adapter"].bridge.runtime.step_count,
                    "HLB": sessions["HLB"]["adapter"].bridge.runtime.step_count,
                },
            },
            "result": "PASS" if integrity["passed"] else "FAIL",
            "confirmatory_test_accessed": partition_name == "confirmatory_test",
        }
    finally:
        for session in sessions.values():
            session["director"].close()
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result
