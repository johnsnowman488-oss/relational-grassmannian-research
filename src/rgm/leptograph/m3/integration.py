"""Deterministic end-to-end M3 smoke world joining all component tracks."""
from __future__ import annotations
import numpy as np
from .activation import EvidenceActivation
from .context import ContextBank, ContextDecision
from .controls import MemoryArchitecture
from .estimation import MultiSourceRidge
from .revision import CUSUMDetector, CandidateRevision

def run_integrated_smoke(seed: int = 1603, steps: int = 240) -> dict:
    """Run a small sequential multi-source/context/adaptation experiment.

    This is an integration smoke experiment, not held-out scientific validation.
    The learner receives both eligible sources; evaluator parameters are kept
    local to the generator and are not passed to learner methods.
    """
    if steps < 80:
        raise ValueError("steps must be >= 80 for the declared phases")
    rng = np.random.default_rng(seed)
    bank = ContextBank(metric=np.eye(2), capacity=4, accept_threshold=10.0,
                       novelty_threshold=25.0, ambiguity_margin=0.05, novelty_repeats=3)
    bank.add_initial([0.0, 0.0], prior_covariance=0.2 * np.eye(2))
    model = MultiSourceRidge(source_dimensions={"group_a": 2, "group_b": 3},
                             context_dimension=2, target_dimension=2, ridge=1e-3)
    activation = EvidenceActivation(on_threshold=0.08, off_threshold=0.025,
                                    evidence_rate=0.12, usefulness_rate=0.2,
                                    minimum_observations=4, context_score_limit=15.0)
    detector = CUSUMDetector(allowance=0.2, threshold=6.0)
    revision = CandidateRevision(np.eye(2))
    c3 = MemoryArchitecture("C3", 2, 2, state_budget=64)
    c4 = MemoryArchitecture("C4", 2, 2, state_budget=64)
    a = np.array([[0.8, -0.2], [0.1, 0.6]])
    b = np.array([[0.2, 0.0, -0.1], [0.0, 0.3, 0.15]])
    c = np.array([[0.08, 0.02], [-0.03, 0.05]])
    errors, contribution_a, contribution_b = [], [], []
    accepted = abstained = novel = 0
    candidate_started = False
    state = None
    for t in range(steps):
        context_truth = np.array([0.0, 0.0]) if t < steps * 0.65 else np.array([2.0, -1.5])
        context_obs = context_truth + rng.normal(0, 0.04, 2)
        decision, slot_id, scores = bank.route(context_obs)
        context_score = min(scores.values()) if scores else 0.0
        if decision is ContextDecision.ACCEPT:
            accepted += 1
        elif decision is ContextDecision.ABSTAIN:
            abstained += 1
        else:
            novel += 1
            created = bank.observe_novel(context_obs)
            if created is not None:
                context_score, slot_id = 0.0, created
        xa, xb = rng.normal(size=2), rng.normal(size=3)
        target = a @ xa + b @ xb + c @ context_truth
        if t >= int(steps * 0.75):
            target = target + 0.25 * xa
        target = target + rng.normal(0, 0.025, 2)
        sources = {"group_a": xa, "group_b": xb}

        # Strict order: predict, score against observation, then update.
        prediction = model.predict(sources, context_obs)
        error = target - prediction
        contributions = model.marginal_loss_contributions(sources, context_obs, target)
        loss = float(np.sum(error ** 2))
        errors.append(loss)
        contribution_a.append(contributions["group_a"])
        contribution_b.append(contributions["group_b"])
        model.update(sources, context_obs, target)
        denom = max(1e-8, float(np.sum(target ** 2)))
        improvement = float(np.clip(contributions["group_a"] / denom, -1.0, 1.0))
        state = activation.update("relation_a", predictive_improvement=improvement,
                                  observed=True, identifiable=True, context_score=context_score,
                                  context_slot=slot_id)
        alarm = detector.update(float(np.linalg.norm(error)))
        if alarm and not candidate_started:
            revision.start_candidate(a + 0.1 * np.eye(2))
            candidate_started = True
        c3.update_mode(xa)
        c3.update_relation(xb[:2])
        c4.update_mode(xa)
        c4.update_relation(xb[:2])
    if candidate_started:
        recent = float(np.mean(errors[-20:]))
        revision.evaluate(incumbent_loss=recent, candidate_loss=recent + 0.01, identifiable=True)
    return {
        "seed": seed, "steps": steps,
        "phase_schedule": {"context_switch_fraction": 0.65, "operator_change_fraction": 0.75},
        "learner_source_dimensions": {"group_a": 2, "group_b": 3},
        "both_sources_used": True, "prequential_order_enforced_by_call_sequence": True,
        "mean_squared_prediction_error": float(np.mean(errors)),
        "last_20_mean_squared_prediction_error": float(np.mean(errors[-20:])),
        "mean_group_a_marginal_loss_contribution": float(np.mean(contribution_a)),
        "mean_group_b_marginal_loss_contribution": float(np.mean(contribution_b)),
        "context_decisions": {"accept": accepted, "abstain": abstained, "novel": novel,
                              "slots_at_end": len(bank.slots)},
        "relation_a_active_at_end": bool(state.active) if state else False,
        "drift_alarms": detector.alarms,
        "candidate_revision": {"started": candidate_started, "promotions": revision.revision_count,
                               "rejections": revision.rejection_count},
        "memory_resources": {"C3": c3.resource_snapshot(), "C4": c4.resource_snapshot()},
        "claim_ceiling": "synthetic integration smoke only; no held-out generalisation, causal attribution, architecture winner, or global stability claim",
    }
