"""Validation-only G2/G3 diagnostics for HLG-M4.

This module does not read confirmatory-test worlds and does not freeze thresholds.
It records outage/replay/late-arrival behavior and false-path/abstention cases.
"""
from __future__ import annotations

import json
import sys

from rgm.experiments.m4_confirmatory_worlds import (
    default_partitions, condition_world, generate_order_world, generate_world,
    validate_partitions,
)
from rgm.leptograph.m4.system import M4ABSystem, M4Query


def _model(architecture, world, min_probability=0.5, min_margin=0.05):
    model = M4ABSystem(
        architecture, world.relation_types, relation_capacity=8192,
        max_path_depth=4, min_probability=min_probability, min_margin=min_margin,
    )
    model.fit_readout(world.training_examples, epochs=700, learning_rate=0.12)
    return model


def _query(model, world, events, architecture, cutoff=None, query_time=None):
    view = world.learner_view(cutoff)
    visible = tuple(events)
    result = model.query(
        M4Query(
            view.start, view.goal, "ctx",
            world.query_time if query_time is None else query_time,
            view.observation_cutoff, max_depth=world.depth,
        ),
        visible_events=visible if architecture == "A" else (),
    )
    return result


def run_validation_g23(world_count: int = 12) -> dict:
    if world_count < 1:
        raise ValueError("world_count must be positive")
    partitions = default_partitions()
    validate_partitions(partitions)
    validation = next(p for p in partitions if p.name == "validation")
    seeds = validation.seeds[:world_count]
    if len(seeds) != world_count:
        raise ValueError("requested run exceeds validation partition")

    generators = (generate_world, generate_order_world)
    g2_rows = []
    g3_rows = []
    for seed in seeds:
        depth = (2, 3, 4)[seed % 3]
        for generator in generators:
            base = generator(seed, depth)
            full_view = base.learner_view()
            for architecture in ("A", "B"):
                # G2-A: outage with no replay. A has no retained relation
                # instances; B must answer from its persistent typed store.
                retained = _model(architecture, base)
                for event in full_view.events:
                    retained.observe(event)
                retained.advance_gap(8.0)
                no_replay = _query(
                    retained, base, (), architecture,
                    cutoff=full_view.observation_cutoff,
                    query_time=base.query_time + 8.0,
                )
                g2_rows.append({
                    "seed": seed, "world_id": base.world_id, "mode": base.mode,
                    "architecture": architecture, "condition": "outage_no_replay",
                    "status": no_replay["status"],
                    "correct": no_replay.get("selected_path") == base.oracle_target_path,
                    "selected_path": no_replay.get("selected_path"),
                })

                # G2-B: outage with current evidence-window replay available.
                replay = _model(architecture, base)
                for event in full_view.events:
                    replay.observe(event)
                replay.advance_gap(8.0)
                replayed = _query(
                    replay, base, full_view.events, architecture,
                    cutoff=full_view.observation_cutoff,
                    query_time=base.query_time + 8.0,
                )
                g2_rows.append({
                    "seed": seed, "world_id": base.world_id, "mode": base.mode,
                    "architecture": architecture, "condition": "outage_with_replay",
                    "status": replayed["status"],
                    "correct": replayed.get("selected_path") == base.oracle_target_path,
                    "selected_path": replayed.get("selected_path"),
                })

                # G2-C: late-arrival sequence. Query causally at the early
                # cutoff, then deliver the remaining events and query again.
                observed_times = sorted(e.observed_at for e in full_view.events)
                early_cutoff = observed_times[max(0, len(observed_times) // 2 - 1)]
                early_view = base.learner_view(early_cutoff)
                early_ids = {e.instance_id for e in early_view.events}
                late_events = tuple(
                    sorted((e for e in full_view.events if e.instance_id not in early_ids),
                           key=lambda e: (e.observed_at, e.event_time, e.instance_id))
                )
                late_model = _model(architecture, base)
                for event in early_view.events:
                    late_model.observe(event)
                early_result = _query(
                    late_model, base, early_view.events, architecture,
                    cutoff=early_cutoff, query_time=early_cutoff + 1.0,
                )
                for event in late_events:
                    late_model.observe(event)
                late_result = _query(
                    late_model, base, full_view.events, architecture,
                    cutoff=full_view.observation_cutoff,
                    query_time=base.query_time,
                )
                g2_rows.append({
                    "seed": seed, "world_id": base.world_id, "mode": base.mode,
                    "architecture": architecture, "condition": "late_arrival",
                    "early_status": early_result["status"],
                    "early_selected": early_result.get("selected_path"),
                    "late_status": late_result["status"],
                    "late_correct": late_result.get("selected_path") == base.oracle_target_path,
                    "late_selected": late_result.get("selected_path"),
                    "late_event_count": len(late_events),
                })

                # G3: hard negatives and multiple-witness positive control.
                for condition in ("missing_target_edge", "wrong_context_target",
                                  "temporal_invalid_target", "multiple_target_witnesses"):
                    challenged = condition_world(base, condition)
                    challenged_view = challenged.learner_view()
                    trial = _model(architecture, challenged)
                    for event in challenged_view.events:
                        trial.observe(event)
                    result = _query(
                        trial, challenged, challenged_view.events, architecture,
                        cutoff=challenged_view.observation_cutoff,
                        query_time=challenged.query_time,
                    )
                    g3_rows.append({
                        "seed": seed, "world_id": challenged.world_id,
                        "mode": challenged.mode, "architecture": architecture,
                        "condition": condition, "status": result["status"],
                        "selected_path": result.get("selected_path"),
                        "selected_is_planted_target": (
                            result.get("selected_path") == challenged.oracle_target_path
                        ),
                        "score": result.get("score"), "margin": result.get("margin"),
                        "witness_count": len(result.get("witnesses", ())),
                        "witness_valid": all(
                            len(w.entities) == len(w.instances) + 1
                            and w.endpoint == challenged.goal
                            for w in result.get("witnesses", ())
                        ),
                    })

    def summarize(rows, arch):
        subset = [r for r in rows if r["architecture"] == arch]
        return {
            "rows": len(subset),
            "selected": sum(r.get("status", r.get("late_status")) == "SELECTED" for r in subset),
            "abstained": sum(str(r.get("status", r.get("late_status", ""))).startswith("ABSTAIN") for r in subset),
            "correct": sum(bool(r.get("correct", r.get("late_correct", False))) for r in subset),
        }

    return {
        "classification": "validation_only_G2_G3_diagnostics_not_confirmatory",
        "partition": "validation",
        "world_seeds": list(seeds),
        "world_modes": ["heterogeneous_typed_chain", "homogeneous_order_sensitive"],
        "confirmatory_test_accessed": False,
        "G2": {
            "rows": g2_rows,
            "summary": {arch: summarize(g2_rows, arch) for arch in ("A", "B")},
        },
        "G3": {
            "rows": g3_rows,
            "summary": {arch: summarize(g3_rows, arch) for arch in ("A", "B")},
        },
        "claim_boundary": (
            "validation diagnostics only; no calibrated risk/coverage threshold, "
            "architecture-selection or M4 acceptance claim"
        ),
    }


if __name__ == "__main__":
    payload = json.dumps(run_validation_g23(), sort_keys=True, indent=2)
    print(payload)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as stream:
            stream.write(payload + "\n")
