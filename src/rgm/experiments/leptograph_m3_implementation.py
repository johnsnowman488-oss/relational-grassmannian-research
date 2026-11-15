"""Run one independent HLG-M3 implementation work package and emit evidence."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

from rgm.leptograph.m3 import (
    CandidateRevision, ContextBank, ContextDecision, CUSUMDetector,
    EvidenceActivation, MemoryArchitecture, MultiSourceRidge,
)
from rgm.leptograph.m3.integration import run_integrated_smoke

CAMPAIGN_ID = "HLG-M3-IMPLEMENTATION-v0.1"
WORK_PACKAGES = ("M3-A", "M3-B", "M3-C", "M3-D", "M3-E", "M3-I")


def run_package(package_id: str) -> dict:
    if package_id == "M3-A":
        g = np.array([[2.0, 0.25], [0.25, 1.2]])
        sigma = np.array([[0.5, 0.08], [0.08, 0.35]])
        mu = np.array([0.4, -0.2])
        z = np.array([0.1, 0.3])
        old = ContextBank(g, capacity=3, regularisation=0.03)
        sid = old.add_initial(mu, prior_covariance=sigma)
        score_old = old.score(z, sid)
        a = np.array([[1.8, 0.4], [0.1, 0.7]])
        ai = np.linalg.inv(a)
        new = ContextBank(a.T @ g @ a, capacity=3, regularisation=0.03)
        sid_new = new.add_initial(ai @ mu, prior_covariance=ai @ sigma @ ai.T)
        score_new = new.score(ai @ z, sid_new)
        accepted = old.route(mu + np.array([0.01, -0.01]))[0] is ContextDecision.ACCEPT
        return {
            "campaign_id": CAMPAIGN_ID, "package_id": package_id,
            "score_original": score_old, "score_transformed": score_new,
            "coordinate_invariance_error": abs(score_old - score_new),
            "near_prototype_accepted": accepted,
            "metric_coordinate_invariance": abs(score_old - score_new) < 1e-9,
            "execution_passed": abs(score_old - score_new) < 1e-9 and accepted,
            "interpretation": "Metric-aware context score and explicit routing contract; randomised/high-dimensional calibration remains open.",
        }
    if package_id == "M3-B":
        rng = np.random.default_rng(2301)
        model = MultiSourceRidge({"small_group": 2, "large_group": 3}, 2, 2, ridge=1e-5)
        wa = np.array([[0.8, -0.2], [0.1, 0.6]])
        wb = np.array([[0.2, 0.0, -0.1], [0.0, 0.3, 0.15]])
        wc = np.array([[0.08, 0.02], [-0.03, 0.05]])
        errors = []
        last_sources = last_context = last_target = None
        for _ in range(700):
            xa, xb, c = rng.normal(size=2), rng.normal(size=3), rng.normal(size=2)
            y = wa @ xa + wb @ xb + wc @ c + rng.normal(0, 0.01, 2)
            sources = {"small_group": xa, "large_group": xb}
            pred = model.predict(sources, c)
            errors.append(float(np.mean((y - pred) ** 2)))
            model.update(sources, c, y)
            last_sources, last_context, last_target = sources, c, y
        contributions = model.marginal_loss_contributions(last_sources, last_context, last_target)
        beta = model.coefficients()
        all_sources_used = bool(np.linalg.norm(beta[:2]) > 0.1 and np.linalg.norm(beta[2:5]) > 0.1)
        return {
            "campaign_id": CAMPAIGN_ID, "package_id": package_id,
            "samples": model.sample_count, "feature_dimension": model.feature_dimension,
            "final_window_mse": float(np.mean(errors[-100:])),
            "marginal_loss_contributions": contributions,
            "source_coefficients_nontrivial": all_sources_used,
            "resource_snapshot": model.resource_snapshot(),
            "execution_passed": model.sample_count == 700 and all_sources_used and np.mean(errors[-100:]) < 0.01,
            "interpretation": "The fitted prequential predictor includes every declared heterogeneous source and context feature; contribution is predictive, not causal.",
        }
    if package_id == "M3-C":
        ctl = EvidenceActivation(on_threshold=0.2, off_threshold=0.1,
                                 evidence_rate=0.3, usefulness_rate=0.4,
                                 minimum_observations=2, context_score_limit=5.0)
        for _ in range(12):
            ctl.update("r", predictive_improvement=0.9, observed=True,
                       identifiable=True, context_score=1.0, context_slot=0)
        before = ctl.states["r"].observed_count
        ctl.update("r", predictive_improvement=None, observed=False,
                   identifiable=True, context_score=1.0, context_slot=0)
        missing_noop = ctl.states["r"].observed_count == before
        active_after_positive = ctl.is_active("r")
        for _ in range(20):
            ctl.update("r", predictive_improvement=-1.0, observed=True,
                       identifiable=True, context_score=1.0, context_slot=0)
        inactive_after_negative = not ctl.is_active("r")
        return {
            "campaign_id": CAMPAIGN_ID, "package_id": package_id,
            "positive_evidence_activated": active_after_positive,
            "missing_observation_noop": missing_noop,
            "negative_evidence_deactivated": inactive_after_negative,
            "final_state": ctl.snapshot("r"),
            "execution_passed": active_after_positive and missing_noop and inactive_after_negative,
            "interpretation": "Tests separation of evidence/usefulness/sufficiency and hysteretic route activation; thresholds need broader calibration.",
        }
    if package_id == "M3-D":
        detector = CUSUMDetector(allowance=0.2, threshold=3.0)
        stationary = [detector.update(0.1) for _ in range(30)]
        shifted = [detector.update(1.0) for _ in range(8)]
        incumbent = np.eye(2)
        revision = CandidateRevision(incumbent)
        revision.start_candidate(2.0 * np.eye(2))
        rejected = not revision.evaluate(incumbent_loss=0.4, candidate_loss=0.6, identifiable=True)
        preserved = np.array_equal(revision.accepted_operator, incumbent)
        revision.start_candidate(0.9 * np.eye(2))
        promoted = revision.evaluate(incumbent_loss=0.4, candidate_loss=0.2, identifiable=True)
        return {
            "campaign_id": CAMPAIGN_ID, "package_id": package_id,
            "stationary_alarm_count": sum(stationary), "shift_alarm_count": sum(shifted),
            "nonimproving_candidate_rejected": rejected, "accepted_operator_preserved_on_rejection": preserved,
            "improving_identifiable_candidate_promoted": promoted,
            "execution_passed": not any(stationary) and any(shifted) and rejected and preserved and promoted,
            "interpretation": "Verifies two-phase revision semantics on bounded reference streams; broad detector calibration and drift families remain open.",
        }
    if package_id == "M3-E":
        systems = [MemoryArchitecture(k, 2, 2, state_budget=64) for k in ("C0", "C1", "C2", "C3", "C4")]
        for system in systems:
            system.update_mode(np.array([0.2, -0.1]))
            system.update_relation(np.array([0.1, 0.3]))
            system.read_mode()
            system.read_relation()
        resources = {s.name: s.resource_snapshot() for s in systems}
        distinct = len({json.dumps(v, sort_keys=True) for v in resources.values()}) == 5
        return {
            "campaign_id": CAMPAIGN_ID, "package_id": package_id,
            "architectures": resources, "all_five_controls_distinct": distinct,
            "c4_shared_state_and_readouts": resources["C4"]["persistent_state_bytes"] > 0 and resources["C4"]["trainable_parameter_count"] > 0,
            "comparison_status": "INSTRUMENTED_REFERENCE_CONTROLS_NOT_PERFORMANCE_RANKED",
            "execution_passed": distinct and resources["C0"]["persistent_bytes_total"] == 0 and resources["C4"]["trainable_parameter_count"] > 0,
            "interpretation": "Actual persistent bytes, parameter counts and observed update/query multiply-adds are counted; task-performance and Pareto comparisons remain to be run.",
        }
    if package_id == "M3-I":
        result = run_integrated_smoke()
        passed = (
            result["both_sources_used"]
            and result["prequential_order_enforced_by_call_sequence"]
            and result["steps"] == 240
            and np.isfinite(result["mean_squared_prediction_error"])
            and result["candidate_revision"]["rejections"] >= 0
        )
        return {
            "campaign_id": CAMPAIGN_ID, "package_id": package_id,
            "integration": result, "execution_passed": bool(passed),
            "interpretation": "Integrated synthetic smoke only; it is not the full eight-world held-out benchmark or an M3 success claim.",
        }
    raise ValueError(f"unknown work package: {package_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-package", choices=WORK_PACKAGES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_package(args.work_package)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    args.output.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode()).hexdigest()
    print(json.dumps({"sha256": digest, **result}, sort_keys=True))
    if result["execution_passed"] is not True:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
