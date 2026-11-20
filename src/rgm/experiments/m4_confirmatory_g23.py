"""Validation-only G2/G3 diagnostics for HLG-M4.

This module does not read confirmatory-test worlds and does not freeze thresholds.
It records outage/replay/late-arrival behavior and false-path/abstention cases.
"""
from __future__ import annotations

import json
import sys

from rgm.experiments.m4_confirmatory_worlds import (
    default_partitions, build_training_corpus, condition_world,
    generate_order_world, generate_world, validate_partitions,
)
from rgm.leptograph.m4.system import M4ABSystem, M4Query


def _model(architecture, world, training_examples, min_probability=0.5, min_margin=0.05):
    model = M4ABSystem(
        architecture, world.relation_types, relation_capacity=8192,
        max_path_depth=4, min_probability=min_probability, min_margin=min_margin,
    )
    model.fit_readout(training_examples, epochs=700, learning_rate=0.12)
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


def run_validation_g23(world_count: int = 60) -> dict:
    if world_count < 1:
        raise ValueError("world_count must be positive")
    partitions = default_partitions()
    validate_partitions(partitions)
    validation = next(p for p in partitions if p.name == "validation")
    train = next(p for p in partitions if p.name == "train")
    seeds = validation.seeds[:world_count]
    if len(seeds) != world_count:
        raise ValueError("requested run exceeds validation partition")

    generators = (generate_world, generate_order_world)
    training_corpora = {}
    ambiguous_corpora = {}
    corpus_metadata = {}
    for generator in generators:
        corpus, world_ids, digest = build_training_corpus(train.seeds, generator)
        ambiguous, _, ambiguous_digest = build_training_corpus(
            train.seeds, generator, condition="ambiguous_competing_paths"
        )
        training_corpora[generator] = corpus
        ambiguous_corpora[generator] = ambiguous
        corpus_metadata[generator] = {
            "training_world_count": len(world_ids),
            "unique_training_example_count": len(corpus),
            "ambiguous_unique_training_example_count": len(ambiguous),
            "training_corpus_sha256": digest,
            "ambiguous_corpus_sha256": ambiguous_digest,
        }
    templates = {}
    ambiguous_templates = {}
    for generator in generators:
        template_world = generator(train.seeds[0], 4)
        for architecture in ("A", "B"):
            templates[(generator, architecture)] = _model(
                architecture, template_world, training_corpora[generator]
            ).snapshot()
            ambiguous_templates[(generator, architecture)] = _model(
                architecture, template_world, ambiguous_corpora[generator]
            ).snapshot()

    g2_rows = []
    g3_rows = []
    for seed in seeds:
        depth = (2, 3, 4)[seed % 3]
        for generator in generators:
            base = generator(seed, depth)
            train_examples = training_corpora[generator]
            corpus_info = corpus_metadata[generator]
            full_view = base.learner_view()
            for architecture in ("A", "B"):
                # G2-A: outage with no replay. A has no retained relation
                # instances; B must answer from its persistent typed store.
                retained = M4ABSystem(architecture, base.relation_types, relation_capacity=8192, max_path_depth=4, min_probability=0.5, min_margin=0.05)
                retained.restore(templates[(generator, architecture)])
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
                    **corpus_info,
                    "architecture": architecture, "condition": "outage_no_replay",
                    "status": no_replay["status"],
                    "correct": no_replay.get("selected_path") == base.oracle_target_path,
                    "selected_path": no_replay.get("selected_path"),
                })

                # G2-B: outage with current evidence-window replay available.
                replay = M4ABSystem(architecture, base.relation_types, relation_capacity=8192, max_path_depth=4, min_probability=0.5, min_margin=0.05)
                replay.restore(templates[(generator, architecture)])
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
                    **corpus_info, "architecture": architecture,
                    "condition": "outage_with_replay",
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
                late_model = M4ABSystem(architecture, base.relation_types, relation_capacity=8192, max_path_depth=4, min_probability=0.5, min_margin=0.05)
                late_model.restore(templates[(generator, architecture)])
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
                    **corpus_info, "architecture": architecture,
                    "condition": "late_arrival",
                    "early_status": early_result["status"],
                    "early_selected": early_result.get("selected_path"),
                    "late_status": late_result["status"],
                    "late_correct": late_result.get("selected_path") == base.oracle_target_path,
                    "late_selected": late_result.get("selected_path"),
                    "late_event_count": len(late_events),
                })

                # G3: hard negatives and multiple-witness positive control.
                for condition in ("missing_target_edge", "wrong_context_target",
                                  "temporal_invalid_target", "multiple_target_witnesses",
                                  "ambiguous_competing_paths"):
                    challenged = condition_world(base, condition)
                    challenged_view = challenged.learner_view()
                    is_ambiguous = condition == "ambiguous_competing_paths"
                    condition_examples = (
                        ambiguous_corpora[generator] if is_ambiguous else train_examples
                    )
                    condition_corpus_digest = (
                        corpus_info["ambiguous_corpus_sha256"]
                        if is_ambiguous else corpus_info["training_corpus_sha256"]
                    )
                    trial = M4ABSystem(
                        architecture, challenged.relation_types, relation_capacity=8192,
                        max_path_depth=4, min_probability=0.5, min_margin=0.05,
                    )
                    trial.restore(
                        ambiguous_templates[(generator, architecture)]
                        if is_ambiguous else templates[(generator, architecture)]
                    )
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
                        **corpus_info,
                        "training_corpus_sha256": condition_corpus_digest,
                        "condition": condition, "status": result["status"],
                        "selected_path": result.get("selected_path"),
                        "selected_is_planted_target": (
                            result.get("selected_path") == challenged.oracle_target_path
                        ),
                        "ambiguous_valid_alternatives": condition == "ambiguous_competing_paths",
                        "score": result.get("score"), "margin": result.get("margin"),
                        "candidate_count": len(result.get("candidates", ())),
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
            "correct": sum(bool(r.get("correct", r.get("late_correct", r.get("selected_is_planted_target", False)))) for r in subset),
        }

    calibration_count = max(1, len(seeds) // 2)
    calibration_seeds = set(seeds[:calibration_count])
    heldout_seeds = set(seeds[calibration_count:])

    def make_threshold_grid(rows):
        grid = []
        for probability_threshold in (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75):
            for margin_threshold in (0.0, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25):
                decisions = []
                for row in rows:
                    score = row["score"]
                    margin = row["margin"]
                    selected = (
                        score is not None
                        and score >= probability_threshold
                        and (row["candidate_count"] <= 1 or margin >= margin_threshold)
                    )
                    decisions.append((row, selected))
                false_selected = sum(
                    selected for row, selected in decisions
                    if row["condition"] in negative_conditions
                )
                ambiguous_selected = sum(
                    selected for row, selected in decisions
                    if row["condition"] == "ambiguous_competing_paths"
                )
                positive = [selected for row, selected in decisions
                            if row["condition"] == "multiple_target_witnesses"]
                grid.append({
                    "min_probability": probability_threshold,
                    "min_margin": margin_threshold,
                    "false_selections": false_selected,
                    "ambiguous_selections": ambiguous_selected,
                    "positive_coverage": (
                        sum(positive) / len(positive) if positive else 0.0
                    ),
                    "meets_validation_separation": (
                        false_selected == 0 and ambiguous_selected == 0
                    ),
                })
        return grid

    def choose_threshold(grid):
        feasible = [
            item for item in grid
            if item["meets_validation_separation"] and item["positive_coverage"] == 1.0
        ]
        if not feasible:
            return None
        # Predeclared conservative tie-break: highest probability threshold,
        # then highest margin threshold, among calibration-feasible points.
        best = max(feasible, key=lambda item: (
            item["min_probability"], item["min_margin"]
        ))
        return {
            "min_probability": best["min_probability"],
            "min_margin": best["min_margin"],
        }

    def apply_threshold(rows, threshold):
        if threshold is None:
            return {"available": False}
        decisions = []
        for row in rows:
            score = row["score"]
            margin = row["margin"]
            selected = (
                score is not None
                and score >= threshold["min_probability"]
                and (row["candidate_count"] <= 1 or margin >= threshold["min_margin"])
            )
            decisions.append((row, selected))
        return {
            "available": True,
            "false_selections": sum(
                selected for row, selected in decisions
                if row["condition"] in negative_conditions
            ),
            "ambiguous_selections": sum(
                selected for row, selected in decisions
                if row["condition"] == "ambiguous_competing_paths"
            ),
            "positive_coverage": (
                sum(selected for row, selected in decisions
                    if row["condition"] == "multiple_target_witnesses")
                / max(1, sum(row["condition"] == "multiple_target_witnesses"
                             for row, _ in decisions))
            ),
        }

    threshold_sweep = {}
    score_summary = {}
    negative_conditions = {
        "missing_target_edge", "wrong_context_target", "temporal_invalid_target"
    }
    for architecture in ("A", "B"):
        subset = [row for row in g3_rows if row["architecture"] == architecture]
        calibration_rows = [row for row in subset if row["seed"] in calibration_seeds]
        heldout_rows = [row for row in subset if row["seed"] in heldout_seeds]
        modes = sorted({row["mode"] for row in subset})
        pooled_grid = make_threshold_grid(calibration_rows)
        pooled_threshold = choose_threshold(pooled_grid)
        threshold_sweep[architecture] = {
            "calibration_world_seeds": sorted(calibration_seeds),
            "heldout_validation_world_seeds": sorted(heldout_seeds),
            "pooled_calibration_grid": pooled_grid,
            "pooled_selected_threshold": pooled_threshold,
            "pooled_heldout_metrics": apply_threshold(heldout_rows, pooled_threshold),
            "by_mode": {},
        }
        for mode in modes:
            mode_calibration = [row for row in calibration_rows if row["mode"] == mode]
            mode_heldout = [row for row in heldout_rows if row["mode"] == mode]
            mode_grid = make_threshold_grid(mode_calibration)
            mode_threshold = choose_threshold(mode_grid)
            threshold_sweep[architecture]["by_mode"][mode] = {
                "calibration_grid": mode_grid,
                "selected_threshold": mode_threshold,
                "heldout_metrics": apply_threshold(mode_heldout, mode_threshold),
            }

        score_summary[architecture] = {}
        for mode in modes:
            score_summary[architecture][mode] = {}
            for condition in sorted({row["condition"] for row in subset if row["mode"] == mode}):
                group = [row for row in subset
                         if row["mode"] == mode and row["condition"] == condition]
                scores = [row["score"] for row in group if row["score"] is not None]
                margins = [row["margin"] for row in group if row["margin"] is not None]
                score_summary[architecture][mode][condition] = {
                    "status_counts": {
                        status: sum(row["status"] == status for row in group)
                        for status in sorted({row["status"] for row in group})
                    },
                    "score_min": min(scores) if scores else None,
                    "score_max": max(scores) if scores else None,
                    "margin_min": min(margins) if margins else None,
                    "margin_max": max(margins) if margins else None,
                }

    return {
        "classification": "validation_only_G2_G3_diagnostics_not_confirmatory",
        "partition": "validation",
        "world_seeds": list(seeds),
        "calibration_world_count": len(calibration_seeds),
        "heldout_validation_world_count": len(heldout_seeds),
        "threshold_selection_rule": "calibration-only zero false/ambiguous selections and full positive coverage; tie-break highest probability then margin",
        "training_corpora": {
            generator(10_000, 4).mode: corpus_metadata[generator]
            for generator in generators
        },
        "world_modes": ["heterogeneous_typed_chain", "homogeneous_order_sensitive"],
        "confirmatory_test_accessed": False,
        "G2": {
            "rows": g2_rows,
            "summary": {arch: summarize(g2_rows, arch) for arch in ("A", "B")},
        },
        "G3": {
            "rows": g3_rows,
            "summary": {arch: summarize(g3_rows, arch) for arch in ("A", "B")},
            "validation_threshold_sweep": threshold_sweep,
            "score_summary": score_summary,
            "thresholds_frozen": False,
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
