"""Development-stage G1-G5 evaluator for integrated HLG-M4 A/B.

This runner exercises the shared pipeline and emits seed-level evidence. It is
not the confirmatory M4 acceptance campaign: no post-result gate tuning or
architecture-selection claim is permitted from these smoke/development runs.
"""
from __future__ import annotations
import json
import math
import sys
import numpy as np

from rgm.leptograph.m4.composition import Entity, RelationType, RelationInstance
from rgm.leptograph.m4.system import M4ABSystem, M4Query, PathTrainingExample
from rgm.leptograph.m4.adaptive import M4AdaptiveController

REL_NAMES = ("r0", "r1", "r2", "r3")
REL_TYPES = tuple(RelationType(name, "Node", "Node") for name in REL_NAMES)
TRAINING = (
    PathTrainingExample(("r0", "r1"), 1),
    PathTrainingExample(("r0", "r2", "r1"), 1),
    PathTrainingExample(("r0", "r3", "r1", "r2"), 1),
    PathTrainingExample(("r1", "r0"), 0),
    PathTrainingExample(("r2", "r1", "r0"), 0),
    PathTrainingExample(("r3", "r2", "r1", "r0"), 0),
)

def _chain(seed: int, tag: str, sequence: tuple[str, ...], start: Entity, goal: Entity):
    entities = [start]
    for i in range(len(sequence) - 1):
        entities.append(Entity(f"{tag}-{seed}-mid-{i}", "Node"))
    entities.append(goal)
    by_name = {r.name: r for r in REL_TYPES}
    return [
        RelationInstance(
            f"{tag}-{seed}-e{i}", by_name[name], entities[i], entities[i + 1],
            float(i + 1), float(i + 1), "ctx",
        )
        for i, name in enumerate(sequence)
    ]

def _world(seed: int, depth: int):
    true_paths = {
        2: ("r0", "r2"),
        3: ("r0", "r3", "r2"),
        4: ("r0", "r2", "r3", "r1"),
    }
    decoy_paths = {
        2: ("r2", "r0"),
        3: ("r3", "r2", "r0"),
        4: ("r2", "r3", "r1", "r0"),
    }
    start = Entity(f"start-{seed}-{depth}", "Node")
    goal = Entity(f"goal-{seed}-{depth}", "Node")
    facts = _chain(seed, "true", true_paths[depth], start, goal)
    facts += _chain(seed, "decoy", decoy_paths[depth], start, goal)
    facts.sort(key=lambda e: (e.observed_at, e.instance_id))
    return start, goal, tuple(facts), true_paths[depth], decoy_paths[depth]

def _new_model(architecture: str, *, min_margin: float = 0.05):
    model = M4ABSystem(
        architecture, REL_TYPES, relation_capacity=4096, max_path_depth=4,
        min_probability=0.5, min_margin=min_margin,
    )
    # A small, fixed, task-visible calibration stream; labels describe training
    # path examples, not any held-out test world's hidden target.
    calibration = [
        RelationInstance(f"cal-{i}", REL_TYPES[i % 4],
                         Entity(f"cal-s-{i}", "Node"), Entity(f"cal-o-{i}", "Node"),
                         float(i + 1), float(i + 1), "ctx")
        for i in range(16)
    ]
    for event in calibration:
        model.observe(event)
    model.fit_readout(TRAINING, epochs=700, learning_rate=0.12)
    return model

def _bce(model, examples, weights):
    losses = []
    for example in examples:
        x = model._features(example.relation_path)
        z = float(np.clip(x @ weights + model.readout_bias, -30.0, 30.0))
        p = 1.0 / (1.0 + math.exp(-z))
        losses.append(-(example.label * math.log(max(p, 1e-12))
                       + (1 - example.label) * math.log(max(1 - p, 1e-12))))
    return float(np.mean(losses))

def run(seed_count: int = 20):
    if seed_count < 1:
        raise ValueError("seed_count must be positive")

    # G1: held-out order combinations at depths 2, 3 and 4. Each target and
    # decoy has the same relation multiset; only ordered composition differs.
    g1_rows = []
    g2_rows = []
    g3_rows = []
    for seed in range(seed_count):
        for depth in (2, 3, 4):
            start, goal, facts, target_path, decoy_path = _world(seed, depth)
            for architecture in ("A", "B"):
                model = _new_model(architecture)
                for event in facts:
                    model.observe(event)
                query = M4Query(start, goal, "ctx", 20.0, 20.0, max_depth=depth)
                result = model.query(query, visible_events=facts if architecture == "A" else ())
                selected = result.get("selected_path")
                g1_rows.append({
                    "seed": seed, "depth": depth, "architecture": architecture,
                    "target": target_path, "decoy": decoy_path, "status": result["status"],
                    "selected": selected, "correct": selected == target_path,
                    "witness_valid": all(
                        len(w.entities) == len(w.instances) + 1
                        and w.endpoint == goal for w in result.get("witnesses", ())
                    ),
                })

                # G2: query after a gap without supplying A a new event window.
                for delay in (0, 4, 8):
                    trial = _new_model(architecture)
                    for event in facts:
                        trial.observe(event)
                    trial.advance_gap(float(delay))
                    delayed_query = M4Query(
                        start, goal, "ctx", 20.0 + delay, 20.0 + delay,
                        max_depth=depth,
                    )
                    delayed = trial.query(
                        delayed_query,
                        visible_events=facts if architecture == "A" and delay == 0 else (),
                    )
                    g2_rows.append({
                        "seed": seed, "depth": depth, "architecture": architecture,
                        "delay": delay, "status": delayed["status"],
                        "selected": delayed.get("selected_path"),
                        "correct": delayed.get("selected_path") == target_path,
                    })

                # G3: high ambiguity margin forces abstention when two valid
                # witnesses compete; a wrong context yields no valid path.
                cautious = _new_model(architecture, min_margin=1.0)
                for event in facts:
                    cautious.observe(event)
                ambiguous = cautious.query(
                    M4Query(start, goal, "ctx", 20.0, 20.0, max_depth=depth),
                    visible_events=facts if architecture == "A" else (),
                )
                wrong_context = cautious.query(
                    M4Query(start, goal, "not-ctx", 20.0, 20.0, max_depth=depth),
                    visible_events=facts if architecture == "A" else (),
                )
                g3_rows.append({
                    "seed": seed, "depth": depth, "architecture": architecture,
                    "ambiguous_status": ambiguous["status"],
                    "wrong_context_status": wrong_context["status"],
                    "ambiguity_abstained": ambiguous["status"].startswith("ABSTAIN"),
                    "wrong_context_abstained": wrong_context["status"].startswith("ABSTAIN"),
                })

    # G4: stable negative control, change detection, independent candidate fit
    # and validation, promotion, and full-state rollback for both architectures.
    g4_rows = []
    fit_examples = (
        PathTrainingExample(("r1", "r2"), 1),
        PathTrainingExample(("r1", "r3", "r2"), 1),
        PathTrainingExample(("r0", "r2"), 0),
        PathTrainingExample(("r0", "r3", "r2"), 0),
    )
    validation_examples = (
        PathTrainingExample(("r1", "r3", "r0"), 1),
        PathTrainingExample(("r1", "r2", "r3", "r0"), 1),
        PathTrainingExample(("r0", "r3", "r1"), 0),
        PathTrainingExample(("r0", "r2", "r1", "r3"), 0),
    )
    for architecture in ("A", "B"):
        model = _new_model(architecture)
        stable_controller = M4AdaptiveController(model)
        stable_alarms = sum(stable_controller.observe_residual(0.0) for _ in range(100))
        controller = M4AdaptiveController(model)
        alarms = sum(controller.observe_residual(3.0) for _ in range(10))
        candidate = M4ABSystem(architecture, REL_TYPES, relation_capacity=4096, max_path_depth=4)
        candidate.restore(model.snapshot())
        candidate.fit_readout(fit_examples, epochs=700, learning_rate=0.12)
        incumbent_loss = _bce(model, validation_examples, model.readout_weights)
        candidate_loss = _bce(model, validation_examples, candidate.readout_weights)
        before = model.snapshot()
        controller.start_candidate(candidate.readout_weights)
        promoted = controller.validate_candidate(incumbent_loss, candidate_loss, True)
        # Mutate temporal and relational state after promotion, then verify
        # rollback restores the complete trusted snapshot. A rejected candidate
        # must leave the incumbent state unchanged.
        if promoted:
            model.advance_gap(2.0)
            rollback_before = controller.rollback_count
            controller.rollback()
            rollback_delta = controller.rollback_count - rollback_before
        else:
            rollback_delta = 0
        restored = (
            np.array_equal(model.readout_weights, before["readout_weights"])
            and np.array_equal(model.soe.channels, np.asarray(before["soe"]["channels"]))
            and (architecture == "A" or model.store.records == before["store"]["records"])
        )
        g4_rows.append({
            "architecture": architecture, "stable_control_alarms": int(stable_alarms),
            "change_alarms": int(alarms), "detector_threshold": controller.detector.threshold,
            "incumbent_validation_loss": incumbent_loss,
            "candidate_validation_loss": candidate_loss, "promoted": promoted,
            "rollback_exact": bool(restored),
            "rollback_count_delta": rollback_delta,
        })

    # G5: populated-state scaling; payload accounting is explicit and does not
    # pretend to include Python allocator/container overhead.
    g5_rows = []
    for count in (10, 100, 500, 1000):
        A = M4ABSystem("A", REL_TYPES, relation_capacity=2000)
        B = M4ABSystem("B", REL_TYPES, relation_capacity=2000)
        for i in range(count):
            event = RelationInstance(
                f"scale-{i}", REL_TYPES[i % 4],
                Entity(f"scale-s-{i}", "Node"), Entity(f"scale-o-{i}", "Node"),
                float(i + 1), float(i + 1), "ctx",
            )
            A.observe(event)
            B.observe(event)
        g5_rows.append({
            "relation_instances": count,
            "A": A.resource_snapshot(),
            "B": B.resource_snapshot(),
        })

    def rates(rows, key):
        total = len(rows)
        return sum(bool(row[key]) for row in rows) / total if total else 0.0

    return {
        "job": "M4-Job4-G1-G5-development-campaigns",
        "classification": "development_and_integration_evidence_not_confirmatory_acceptance",
        "seed_count": seed_count,
        "G1": {
            "rows": g1_rows,
            "accuracy_by_architecture_depth": {
                f"{arch}-d{depth}": {
                    "correct": sum(r["correct"] for r in g1_rows if r["architecture"] == arch and r["depth"] == depth),
                    "total": sum(1 for r in g1_rows if r["architecture"] == arch and r["depth"] == depth),
                } for arch in ("A", "B") for depth in (2, 3, 4)
            },
            "claim_boundary": "held-out ordered relation combinations in a fixed Node-to-Node vocabulary; not open-world discovery",
        },
        "G2": {"rows": g2_rows},
        "G3": {
            "rows": g3_rows,
            "ambiguity_abstention_rate": rates(g3_rows, "ambiguity_abstained"),
            "wrong_context_abstention_rate": rates(g3_rows, "wrong_context_abstained"),
        },
        "G4": {"rows": g4_rows},
        "G5": {"rows": g5_rows},
        "claim_boundary": "bounded synthetic development evidence; not a frozen confirmatory gate, global stability proof, transfer result, or architecture-selection verdict",
    }

if __name__ == "__main__":
    payload = json.dumps(run(), sort_keys=True, indent=2)
    print(payload)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as stream:
            stream.write(payload + "\n")
