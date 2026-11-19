"""Bounded M4 Job 4 A/B integration smoke experiment.

This is an implementation-level integration check, not the confirmatory M4
campaign and not evidence of general architecture superiority.
"""
from __future__ import annotations
import json
import sys
import numpy as np

from rgm.leptograph.m4.composition import Entity, RelationType, RelationInstance
from rgm.leptograph.m4.system import M4ABSystem, M4Query, PathTrainingExample
from rgm.leptograph.m4.adaptive import M4AdaptiveController

def _world(seed: int):
    rng = np.random.default_rng(seed)
    start = Entity("start", "A")
    middle = Entity("middle", "B")
    goal = Entity("goal", "C")
    r1 = RelationType("r1", "A", "B")
    r2 = RelationType("r2", "B", "C")
    facts = [
        RelationInstance(f"{seed}-e1", r1, start, middle, 1.0, 1.0, "ctx"),
        RelationInstance(f"{seed}-e2", r2, middle, goal, 2.0, 2.0, "ctx"),
    ]
    # A type-correct but disconnected distractor exercises candidate retrieval.
    dead = Entity(f"dead-{seed}", "C")
    facts.append(RelationInstance(f"{seed}-d1", r2, middle, dead, 2.0, 2.0, "ctx"))
    rng.shuffle(facts)
    return start, goal, (r1, r2), tuple(facts)

def run(seed_count: int = 20, delays=(0, 4, 8)):
    if seed_count < 1:
        raise ValueError("seed_count must be positive")
    rows = []
    for seed in range(seed_count):
        start, goal, relations, facts = _world(seed)
        for architecture in ("A", "B"):
            model = M4ABSystem(architecture, relations)
            for event in facts:
                model.observe(event)
            fit = model.fit_readout([
                PathTrainingExample(("r1", "r2"), 1),
                PathTrainingExample(("r1",), 0),
                PathTrainingExample(("r2",), 0),
            ])
            for delay in delays:
                # Each delay starts from the same trained state.
                trial = M4ABSystem(architecture, relations)
                for event in facts:
                    trial.observe(event)
                trial.fit_readout([
                    PathTrainingExample(("r1", "r2"), 1),
                    PathTrainingExample(("r1",), 0),
                    PathTrainingExample(("r2",), 0),
                ])
                trial.advance_gap(float(delay))
                query = M4Query(start, goal, "ctx", 10.0 + delay, 10.0, max_depth=2)
                visible = facts if delay == 0 else ()
                result = trial.query(query, visible_events=visible)
                rows.append({
                    "seed": seed, "architecture": architecture, "delay": delay,
                    "status": result["status"],
                    "selected_path": result.get("selected_path"),
                    "witness_ids": [list(w.instance_ids) for w in result.get("witnesses", ())],
                    "fit_accuracy": fit["training_accuracy"],
                    "resources": trial.resource_snapshot(),
                })
            controller = M4AdaptiveController(model)
            before = model.snapshot()
            controller.start_candidate(model.readout_weights + 0.01)
            promoted = controller.validate_candidate(1.0, 0.9, True)
            model.advance_gap(1.0)
            controller.rollback()
            rollback_ok = (
                np.array_equal(model.readout_weights, before["readout_weights"])
                and np.array_equal(model.soe.channels, np.asarray(before["soe"]["channels"]))
                and (architecture == "A" or model.store.records == before["store"]["records"])
            )
            rows.append({
                "seed": seed, "architecture": architecture, "check": "full_state_rollback",
                "promoted": promoted, "rollback_exact": bool(rollback_ok),
                "detector_threshold": controller.detector.threshold,
            })
    retrieval = {}
    for architecture in ("A", "B"):
        for delay in delays:
            subset = [r for r in rows if r.get("architecture") == architecture
                      and r.get("delay") == delay]
            retrieval[f"{architecture}@{delay}"] = {
                "selected": sum(r["status"] == "SELECTED" for r in subset),
                "total": len(subset),
            }
    rollback_rows = [r for r in rows if r.get("check") == "full_state_rollback"]
    return {
        "job": "M4-Job4-AB-integration",
        "classification": "implementation_smoke_experiment_not_confirmatory",
        "seed_count": seed_count,
        "delays": list(delays),
        "retrieval_counts": retrieval,
        "full_state_rollback_passes": sum(r["rollback_exact"] for r in rollback_rows),
        "full_state_rollback_total": len(rollback_rows),
        "seed_level_results": rows,
        "claim_boundary": "end-to-end A/B interface, witness composition, bounded retrieval and complete rollback smoke checks only; no held-out composition or M4 acceptance claim",
    }

if __name__ == "__main__":
    payload = json.dumps(run(), sort_keys=True, indent=2)
    print(payload)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as stream:
            stream.write(payload + "\n")
