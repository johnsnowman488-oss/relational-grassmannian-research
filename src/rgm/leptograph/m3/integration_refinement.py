"""Sequential coupled M3 refinement: context gates, activation, and candidate revision."""
from __future__ import annotations
import numpy as np
from .activation import EvidenceActivation
from .context import ContextBank, ContextDecision
from .controls import MemoryArchitecture
from .estimation import MultiSourceRidge
from .revision import CUSUMDetector, CandidateRevision


def run_integrated_refinement(seed: int = 1604, steps: int = 300) -> dict:
    if steps < 240:
        raise ValueError("steps must be >= 240")
    rng = np.random.default_rng(seed)
    bank = ContextBank(np.eye(2), capacity=4, accept_threshold=10.0,
                       novelty_threshold=25.0, ambiguity_margin=0.05, novelty_repeats=3)
    bank.add_initial([0.0, 0.0], prior_covariance=0.2 * np.eye(2))
    model = MultiSourceRidge({"group_a": 2, "group_b": 3}, 2, 2, ridge=1e-3)
    activation = EvidenceActivation(on_threshold=0.12, off_threshold=0.06,
                                    evidence_rate=0.18, usefulness_rate=0.22,
                                    minimum_observations=8, context_score_limit=15.0)
    detector = CUSUMDetector(allowance=0.25, threshold=3.0)
    c3, c4 = MemoryArchitecture("C3", 2, 2, 64), MemoryArchitecture("C4", 2, 2, 64)
    a0 = np.array([[0.8, -0.2], [0.1, 0.6]])
    a1 = a0 + 0.45 * np.eye(2)
    b = np.array([[0.2, 0.0, -0.1], [0.0, 0.3, 0.15]])
    c = np.array([[0.08, 0.02], [-0.03, 0.05]])
    drift_at, context_switch_at = int(steps * 0.40), int(steps * 0.70)
    baseline_start, baseline_end = 80, 100

    losses, shadow_losses = [], []
    context_counts = {v.value: 0 for v in ContextDecision}
    gated_context_steps = 0
    active_steps = {"group_a": 0, "group_b": 0}
    transitions = {"group_a": 0, "group_b": 0}
    previous_active = {"group_a": False, "group_b": False}
    gate_gap = []
    alarms = []
    revision = None
    phase = "WAITING"
    train_x, train_y, valid_x, valid_y = [], [], [], []
    validation_losses = {"incumbent": None, "candidate": None}
    promoted = None
    initial_operator = None
    baseline_loss = None

    for t in range(steps):
        context_truth = np.array([0.0, 0.0]) if t < context_switch_at else np.array([2.0, -1.5])
        context_obs = context_truth + rng.normal(0.0, 0.04, 2)
        decision, slot_id, scores = bank.route(context_obs)
        context_counts[decision.value] += 1
        if decision is ContextDecision.NOVEL:
            bank.observe_novel(context_obs)
        context_ok = decision is ContextDecision.ACCEPT
        safe_context = context_obs if context_ok else np.zeros(2)
        context_score = float(scores[slot_id]) if context_ok and slot_id is not None else float("inf")
        if not context_ok:
            gated_context_steps += 1

        xa, xb = rng.normal(size=2), rng.normal(size=3)
        true_a = a0 if t < drift_at else a1
        target = true_a @ xa + b @ xb + c @ context_truth + rng.normal(0.0, 0.025, 2)
        sources = {"group_a": xa, "group_b": xb}

        shadow = model.predict(sources, safe_context)
        active_now = {k: bool(activation.is_active(k) and context_ok) for k in sources}
        gates = {k: float(v) for k, v in active_now.items()}
        overrides = {"group_a": revision.accepted_operator} if revision is not None else None
        effective = model.predict(sources, safe_context, source_gates=gates, operator_overrides=overrides)
        contributions = model.marginal_loss_contributions(sources, safe_context, target)
        loss = float(np.mean((target - effective) ** 2))
        shadow_loss = float(np.mean((target - shadow) ** 2))
        losses.append(loss)
        shadow_losses.append(shadow_loss)
        gate_gap.append(float(np.linalg.norm(effective - shadow)))
        for key, is_active in active_now.items():
            if is_active:
                active_steps[key] += 1

        prior_operator = model.source_operator("group_a")
        residualized_a = target - (shadow - prior_operator @ xa)

        # Prediction and scoring have completed; now update sufficient statistics.
        model.update(sources, safe_context, target)
        information = model.conditional_identifiability()
        target_scale = max(float(np.sum(target**2)), 1e-10)
        for key in sources:
            usefulness = float(np.clip(contributions[key] / target_scale, -1.0, 1.0))
            state = activation.update(
                key, predictive_improvement=usefulness, observed=True,
                identifiable=bool(information[key]["identifiable"]),
                context_score=context_score, context_slot=slot_id if context_ok else None,
            )
            if state.active != previous_active[key]:
                transitions[key] += 1
            previous_active[key] = state.active

        c3.update_mode(xa); c3.update_relation(xb[:2])
        c4.update_mode(xa); c4.update_relation(xb[:2])

        if t == baseline_end - 1:
            baseline_loss = max(float(np.median(losses[baseline_start:baseline_end])), 1e-8)
            revision = CandidateRevision(model.source_operator("group_a"))
            initial_operator = revision.accepted_operator.copy()

        if t >= baseline_end and baseline_loss is not None and context_ok and not alarms:
            residual_score = max(0.0, float(np.log(max(loss, 1e-12) / baseline_loss)))
            if detector.update(residual_score):
                alarms.append(t)
                phase = "TRAIN"

        if context_ok and phase in {"TRAIN", "VALIDATE"}:
            if phase == "TRAIN":
                train_x.append(xa.copy()); train_y.append(residualized_a.copy())
                if len(train_x) >= 16:
                    candidate = np.linalg.lstsq(np.vstack(train_x), np.vstack(train_y), rcond=None)[0].T
                    revision.start_candidate(candidate)
                    phase = "VALIDATE"
            else:
                valid_x.append(xa.copy()); valid_y.append(residualized_a.copy())
                if len(valid_x) >= 16:
                    xv, yv = np.vstack(valid_x), np.vstack(valid_y)
                    incumbent, candidate = revision.accepted_operator, revision.candidate_operator
                    validation_losses["incumbent"] = float(np.mean((yv - xv @ incumbent.T)**2))
                    validation_losses["candidate"] = float(np.mean((yv - xv @ candidate.T)**2))
                    identifiable = bool(model.conditional_identifiability()["group_a"]["identifiable"])
                    promoted = revision.evaluate(
                        incumbent_loss=validation_losses["incumbent"],
                        candidate_loss=validation_losses["candidate"],
                        identifiable=identifiable, improvement_margin=1e-7,
                    )
                    phase = "DONE"

    final_info = model.conditional_identifiability()
    operator_delta = (
        float(np.linalg.norm(revision.accepted_operator - initial_operator))
        if revision is not None and initial_operator is not None else 0.0
    )
    return {
        "seed": seed, "steps": steps,
        "evaluator_schedule": {"operator_change_index": drift_at, "context_switch_index": context_switch_at},
        "prequential": {
            "effective_mean_mse": float(np.mean(losses)),
            "effective_last_30_mse": float(np.mean(losses[-30:])),
            "shadow_mean_mse": float(np.mean(shadow_losses)),
            "shadow_last_30_mse": float(np.mean(shadow_losses[-30:])),
        },
        "context": {"decisions": context_counts, "gated_steps": gated_context_steps, "slots_at_end": len(bank.slots)},
        "activation": {
            "active_route_steps": active_steps,
            "final_active": {k: bool(activation.is_active(k)) for k in sources},
            "transitions": transitions,
            "effective_shadow_gap_mean": float(np.mean(gate_gap)),
        },
        "conditional_identifiability": final_info,
        "change_detection": {
            "alarm_count": int(detector.alarms), "alarm_steps": alarms, "baseline_mse": baseline_loss,
            "known_change_detected": bool(alarms and alarms[0] >= drift_at),
            "pre_change_alarm_count": int(sum(x < drift_at for x in alarms)),
            "detection_delay": int(alarms[0] - drift_at) if alarms and alarms[0] >= drift_at else None,
        },
        "candidate_revision": {
            "phase": phase, "started": bool(alarms), "train_count": len(train_x), "validation_count": len(valid_x),
            "validation_losses": validation_losses, "promoted": promoted,
            "promotions": int(revision.revision_count) if revision is not None else 0,
            "rejections": int(revision.rejection_count) if revision is not None else 0,
            "accepted_operator_change_norm": operator_delta,
        },
        "memory_resources": {
            "C3": c3.resource_snapshot(), "C4": c4.resource_snapshot(),
            "resource_matched": bool(c3.persistent_bytes == c4.persistent_bytes),
        },
        "scientific_checks": {
            "context_gated_when_unresolved": bool(gated_context_steps > 0),
            "activation_gate_affects_effective_prediction": bool(np.mean(gate_gap) > 1e-10),
            "both_source_groups_identifiable": bool(all(v["identifiable"] for v in final_info.values())),
            "known_change_detected": bool(alarms and alarms[0] >= drift_at),
            "candidate_validation_completed": bool(phase == "DONE"),
            "candidate_promoted": bool(promoted is True),
            "memory_controls_resource_matched": bool(c3.persistent_bytes == c4.persistent_bytes),
        },
        "claim_ceiling": "one deterministic synthetic integration refinement; no held-out composition generalisation, broad detector calibration, causal attribution, C0-C4 winner, or M4 global stability claim",
    }
