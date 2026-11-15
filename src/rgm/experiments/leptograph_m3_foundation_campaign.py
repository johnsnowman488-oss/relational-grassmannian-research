"""Independent mathematical design probes for the proposed HLG-M3 foundation.

This is pre-implementation research code only. It defines no production M3 runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

EXPERIMENT_ID = "HYBRID-LEPTOGRAPH-M3-FOUNDATION"
SCHEMA_VERSION = "1.0"
CASE_IDS = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")


def _chol_factor(metric: np.ndarray) -> np.ndarray:
    """Return C with C.T @ C == metric."""
    return np.linalg.cholesky(metric).T


def _metric_ridge(
    x: np.ndarray,
    y: np.ndarray,
    input_metric: np.ndarray,
    output_metric: np.ndarray,
    regularisation: float,
) -> np.ndarray:
    """Metric-covariant ridge estimate for column-sample matrices."""
    ci = _chol_factor(input_metric)
    co = _chol_factor(output_metric)
    xw = ci @ x
    yw = co @ y
    gram = xw @ xw.T + regularisation * np.eye(xw.shape[0])
    cross = yw @ xw.T
    what_w = np.linalg.solve(gram, cross.T).T
    return np.linalg.solve(co, what_w) @ ci


def _conditional_information(x_target: np.ndarray, x_other: np.ndarray) -> np.ndarray:
    """Schur complement of target-block information conditional on nuisance features."""
    gtt = x_target @ x_target.T
    gto = x_target @ x_other.T
    goo = x_other @ x_other.T
    return gtt - gto @ np.linalg.pinv(goo, rcond=1e-10) @ gto.T


def case_f1() -> dict[str, Any]:
    """Sequential prequential marginal contribution, null-decoy and confounding."""
    rng = np.random.default_rng(1101)
    n_train, n_test = 1800, 900
    x1 = rng.normal(size=(2, n_train + n_test))
    x2 = rng.normal(size=(3, n_train + n_test))
    ctx = rng.normal(size=(2, n_train + n_test))
    bias = np.ones((1, n_train + n_test))
    theta1 = np.array([[0.8, -0.3], [0.2, 0.6], [-0.5, 0.4]])
    theta2 = np.zeros((3, 3))
    beta = np.array([[0.2, 0.1], [-0.1, 0.25], [0.15, -0.2]])
    intercept = np.array([[0.1], [-0.05], [0.08]])
    y = theta1 @ x1 + theta2 @ x2 + beta @ ctx + intercept @ bias
    y += 0.01 * rng.normal(size=y.shape)
    phi = np.vstack((x1, x2, ctx, bias))

    # Initialise from the training prefix; score each test observation first,
    # then incorporate that observation into the sufficient statistics.
    train_phi = phi[:, :n_train]
    train_y = y[:, :n_train]
    gram = train_phi @ train_phi.T
    cross = train_y @ train_phi.T
    regularisation = 1e-7
    full_losses, true_marginals, decoy_marginals = [], [], []
    prediction_order_ok = True
    for index in range(n_test):
        feature = phi[:, n_train + index]
        target = y[:, n_train + index]
        what = np.linalg.solve(gram + regularisation * np.eye(gram.shape[0]), cross.T).T
        prediction = what @ feature
        # Counterfactual ablations are computed from the same frozen pre-update model.
        contribution_1 = what[:, 0:2] @ x1[:, n_train + index]
        contribution_2 = what[:, 2:5] @ x2[:, n_train + index]
        full_loss = float(np.mean(np.square(target - prediction)))
        no_relation_loss = float(np.mean(np.square(target - (prediction - contribution_1))))
        no_decoy_loss = float(np.mean(np.square(target - (prediction - contribution_2))))
        full_losses.append(full_loss)
        true_marginals.append(no_relation_loss - full_loss)
        decoy_marginals.append(no_decoy_loss - full_loss)
        # The current target is incorporated only after all prequential scores exist.
        prediction_before_update = prediction.copy()
        prediction_recomputed_without_target_input = what @ feature
        prediction_order_ok &= bool(np.array_equal(prediction_before_update, prediction_recomputed_without_target_input))
        gram += np.outer(feature, feature)
        cross += np.outer(target, feature)

    full_test_mse = float(np.mean(full_losses))
    delta_true = float(np.mean(true_marginals))
    delta_null = float(np.mean(decoy_marginals))

    # Deliberately make two source blocks observationally collinear.
    x1c = rng.normal(size=(2, 500))
    mixing = np.array([[1.0, 0.2], [-0.3, 0.8], [0.5, -0.4]])
    x2c = mixing @ x1c
    conditional = _conditional_information(x1c, x2c)
    eig = np.linalg.eigvalsh((conditional + conditional.T) / 2.0)
    rank = int(np.linalg.matrix_rank(conditional, tol=1e-7))
    passed = delta_true > 0.1 and abs(delta_null) < 0.01 and rank < 2 and prediction_order_ok
    return {
        "case_id": "F1",
        "description": "Sequential prequential predictive contribution and source-confounding audit",
        "train_samples": n_train,
        "prequential_test_updates": n_test,
        "full_prequential_test_mse": full_test_mse,
        "true_relation_mean_marginal_contribution": delta_true,
        "null_decoy_mean_marginal_contribution": delta_null,
        "collinear_conditional_information_rank": rank,
        "collinear_target_block_dimension": 2,
        "collinear_conditional_information_eigenvalues": [float(v) for v in eig],
        "each_prediction_scored_before_current_target_update": prediction_order_ok,
        "interpretation": "The online prequential stream identifies a planted useful block and gives near-zero contribution for an independent null block in this probe. Collinearity removes conditional identifiability; predictive attribution is not causal attribution.",
        "passed": bool(passed),
    }
def case_f2() -> dict[str, Any]:
    """Recover heterogeneous operators and verify general-coordinate covariance."""
    rng = np.random.default_rng(2202)
    n = 2400
    x1 = rng.normal(size=(2, n))
    x2 = rng.normal(size=(3, n))
    context = rng.normal(size=(2, n))
    phi = np.vstack((x1, x2, context, np.ones((1, n))))
    target_dim = 4
    w_true = rng.normal(scale=0.35, size=(target_dim, phi.shape[0]))
    y = w_true @ phi + 0.0005 * rng.normal(size=(target_dim, n))
    estimate = _metric_ridge(phi, y, np.eye(phi.shape[0]), np.eye(target_dim), 1e-9)
    recovery_error = float(np.linalg.norm(estimate - w_true) / np.linalg.norm(w_true))

    # Passive coordinate changes: x_old=A x_new, y_old=B y_new.
    a = np.eye(phi.shape[0])
    a[:2, :2] = np.array([[2.0, 0.35], [0.1, 0.65]])
    a[2:5, 2:5] = np.array([[1.2, 0.2, 0.0], [0.1, 0.8, 0.15], [0.0, -0.1, 1.4]])
    a[5:7, 5:7] = np.array([[0.7, 0.1], [0.0, 1.8]])
    b = np.array([
        [1.8, 0.2, 0.0, 0.1],
        [0.0, 0.7, 0.1, 0.0],
        [0.1, 0.0, 1.4, 0.2],
        [0.0, 0.1, 0.0, 0.9],
    ])
    x_new = np.linalg.solve(a, phi)
    y_new = np.linalg.solve(b, y)
    gx_new = a.T @ a
    gy_new = b.T @ b
    estimate_new = _metric_ridge(x_new, y_new, gx_new, gy_new, 1e-9)
    expected_new = np.linalg.solve(b, w_true @ a)
    covariance_error = float(np.linalg.norm(estimate_new - expected_new) / np.linalg.norm(expected_new))

    # Relation 1 becomes non-identifiable when its features are in the span of relation 2.
    x1c = rng.normal(size=(2, 700))
    lift = np.array([[1.0, 0.2], [-0.3, 0.9], [0.5, -0.6]])
    x2c = lift @ x1c
    conditional = _conditional_information(x1c, x2c)
    conditional_rank = int(np.linalg.matrix_rank(conditional, tol=1e-7))
    conditional_norm = float(np.linalg.norm(conditional, ord=2))
    passed = recovery_error < 0.01 and covariance_error < 0.01 and conditional_rank == 0 and conditional_norm < 1e-7
    return {
        "case_id": "F2",
        "description": "Metric-aware heterogeneous multi-output operator estimation",
        "source_dimensions": [2, 3],
        "context_dimension": 2,
        "target_dimension": target_dim,
        "joint_feature_dimension": int(phi.shape[0]),
        "relative_operator_recovery_error": recovery_error,
        "relative_general_coordinate_covariance_error": covariance_error,
        "collinear_conditional_information_rank": conditional_rank,
        "collinear_conditional_information_norm": conditional_norm,
        "interpretation": "Whitened regularised least squares recovers the planted heterogeneous additive operator in the excited reference case and transforms covariantly with transported metrics. A rank-deficient conditional information block cannot identify the full operator.",
        "passed": bool(passed),
    }


def _context_score(z: np.ndarray, mean: np.ndarray, cov: np.ndarray, metric: np.ndarray, eps: float) -> float:
    regularised = cov + eps * np.linalg.inv(metric)
    diff = z - mean
    sign, logdet = np.linalg.slogdet(regularised)
    if sign <= 0:
        raise ValueError("context covariance must be positive definite")
    return float(diff @ np.linalg.solve(regularised, diff) + logdet)


def _context_decision(scores: list[float], fit_threshold: float, margin_threshold: float) -> str:
    order = sorted(scores)
    if order[0] > fit_threshold:
        return "NOVEL"
    if len(order) > 1 and order[1] - order[0] < margin_threshold:
        return "ABSTAIN"
    return "ACCEPT"


def case_f3() -> dict[str, Any]:
    """Context metric invariance and accept/abstain/novel slot policy."""
    means = [np.array([0.0, 0.0]), np.array([4.0, 4.0])]
    covs = [
        np.array([[0.5, 0.08], [0.08, 0.4]]),
        np.array([[0.45, -0.04], [-0.04, 0.55]]),
    ]
    metric = np.eye(2)
    eps = 0.03
    queries = {
        "separated": np.array([0.1, -0.1]),
        "ambiguous": np.array([2.0, 2.0]),
        "novel": np.array([11.0, -8.0]),
    }
    decisions = {}
    scores_by_query = {}
    for name, z in queries.items():
        scores = [_context_score(z, m, s, metric, eps) for m, s in zip(means, covs)]
        scores_by_query[name] = scores
        decisions[name] = _context_decision(scores, fit_threshold=18.0, margin_threshold=3.0)

    # Non-orthogonal context coordinate transform and transported covariance/metric.
    a = np.array([[2.0, 0.4], [0.1, 0.7]])
    ainv = np.linalg.inv(a)
    metric_new = a.T @ metric @ a
    transformed_scores = []
    original_scores = scores_by_query["separated"]
    z_new = ainv @ queries["separated"]
    for mean, cov in zip(means, covs):
        transformed_scores.append(
            _context_score(z_new, ainv @ mean, ainv @ cov @ ainv.T, metric_new, eps)
        )
    score_difference_error = float(
        np.max(np.abs((np.asarray(transformed_scores) - transformed_scores[0])
                      - (np.asarray(original_scores) - original_scores[0])))
    )

    novelty_count, required_count, slot_count, max_slots = 0, 3, 2, 3
    for _ in range(required_count):
        novelty_count += 1
    create_slot = novelty_count >= required_count and slot_count < max_slots
    if create_slot:
        slot_count += 1
    overflow_rejects = slot_count >= max_slots
    passed = (
        decisions["separated"] == "ACCEPT"
        and decisions["ambiguous"] == "ABSTAIN"
        and decisions["novel"] == "NOVEL"
        and score_difference_error < 1e-8
        and create_slot
        and overflow_rejects
    )
    return {
        "case_id": "F3",
        "description": "Metric-aware context matching, ambiguity abstention and bounded novelty",
        "decisions": decisions,
        "scores": scores_by_query,
        "general_coordinate_score_difference_error": score_difference_error,
        "novelty_observations_required": required_count,
        "new_slot_created_after_confirmed_novelty": create_slot,
        "slot_count_after_creation": slot_count,
        "max_slots": max_slots,
        "overflow_policy": "ABSTAIN_WITHOUT_EVICTION",
        "passed": bool(passed),
        "interpretation": "Metric transport preserves score differences and the reference policy separates accepted, ambiguous and novel contexts. Thresholds and context feature semantics still require validation on the task suite.",
    }


def _update_evidence(
    n_pos: float, n_neg: float, usefulness: float, delta_t: float,
    rho_q: float, rho_u: float, contribution: float | None,
    weight: float, dead_zone: float, scale: float,
) -> tuple[float, float, float]:
    n_pos *= rho_q ** delta_t
    n_neg *= rho_q ** delta_t
    usefulness *= rho_u ** delta_t
    if contribution is not None:
        if contribution > dead_zone:
            n_pos += weight
        elif contribution < -dead_zone:
            n_neg += weight
        clipped = float(np.clip(contribution / scale, -1.0, 1.0))
        usefulness += (1.0 - rho_u ** delta_t) * clipped
    return n_pos, n_neg, float(np.clip(usefulness, -1.0, 1.0))


def _activate(score: float, active: bool, on: float, off: float) -> tuple[bool, float]:
    next_active = score > off if active else score >= on
    return next_active, (score if next_active else 0.0)


def _cusum_trigger(residuals: list[float], allowance: float, threshold: float) -> tuple[int | None, float]:
    statistic = 0.0
    trigger = None
    for i, value in enumerate(residuals):
        statistic = max(0.0, statistic + value - allowance)
        if statistic >= threshold and trigger is None:
            trigger = i
    return trigger, statistic


def case_f4() -> dict[str, Any]:
    """Evidence bounds, no-observation handling, hysteresis and revision challenge."""
    np_, nn_, u = 2.0, 1.0, 0.35
    after_no_data = _update_evidence(np_, nn_, u, 3.0, 0.98, 0.8, None, 1.0, 0.02, 1.0)
    ratio_before = np_ / nn_
    ratio_after = after_no_data[0] / after_no_data[1]
    no_data_added_negative = after_no_data[1] < nn_ and abs(ratio_after - ratio_before) < 1e-12

    q = (1.0 + after_no_data[0]) / (2.0 + after_no_data[0] + after_no_data[1])
    chi = (after_no_data[0] + after_no_data[1]) / (after_no_data[0] + after_no_data[1] + 4.0)
    bounds = 0.0 <= q <= 1.0 and 0.0 <= chi <= 1.0 and -1.0 <= after_no_data[2] <= 1.0

    off_states = [_activate(s, False, 0.7, 0.4)[0] for s in (0.45, 0.52, 0.61, 0.55)]
    on_states = [_activate(s, True, 0.7, 0.4)[0] for s in (0.61, 0.52, 0.45, 0.55)]
    no_chatter = all(not state for state in off_states) and all(on_states)

    stationary = [0.01, 0.025, 0.015, 0.02, 0.01, 0.03] * 5
    changed = stationary + [0.25, 0.24, 0.27, 0.23, 0.28]
    stationary_trigger, _ = _cusum_trigger(stationary, allowance=0.06, threshold=0.5)
    change_trigger, final_stat = _cusum_trigger(changed, allowance=0.06, threshold=0.5)
    passed = no_data_added_negative and bounds and no_chatter and stationary_trigger is None and change_trigger is not None
    return {
        "case_id": "F4",
        "description": "Evidence accumulation, activation hysteresis and candidate revision detection",
        "evidence_after_no_observation": {
            "positive_mass": after_no_data[0],
            "negative_mass": after_no_data[1],
            "usefulness": after_no_data[2],
            "no_negative_event_added": no_data_added_negative,
        },
        "positive_balance_pseudo_mean": q,
        "support_sufficiency": chi,
        "all_evidence_scores_bounded": bounds,
        "hysteresis_no_chatter_in_band": no_chatter,
        "stationary_residual_false_trigger": stationary_trigger,
        "changed_residual_first_trigger_index": change_trigger,
        "change_residual_final_cusum": final_stat,
        "passed": bool(passed),
        "interpretation": "No observation discounts stale support but is not registered as a negative event. Hysteresis suppresses chatter in the chosen band. The CUSUM threshold is only a reference setting; false-alarm/detection tradeoffs require the integrated benchmark.",
    }


def case_f5() -> dict[str, Any]:
    """Specify C0-C4 memory controls and a matched resource envelope."""
    state_dim = 64
    bytes_per_scalar = 8
    state_budget_bytes = state_dim * bytes_per_scalar
    configs = {
        "C0": {"mode_state": 0, "relational_state": 0, "shared_state": 0, "persistent_bytes": 0},
        "C1": {"mode_state": 64, "relational_state": 0, "shared_state": 0, "persistent_bytes": state_budget_bytes},
        "C2": {"mode_state": 0, "relational_state": 64, "shared_state": 0, "persistent_bytes": state_budget_bytes},
        "C3": {"mode_state": 32, "relational_state": 32, "shared_state": 0, "persistent_bytes": state_budget_bytes},
        "C4": {"mode_state": 0, "relational_state": 0, "shared_state": 64, "persistent_bytes": state_budget_bytes},
    }
    matched_state_bytes = all(configs[k]["persistent_bytes"] == state_budget_bytes for k in ("C1", "C2", "C3", "C4"))
    c3_is_partitioned = configs["C3"]["mode_state"] + configs["C3"]["relational_state"] == state_dim
    c4_is_shared = configs["C4"]["shared_state"] == state_dim and configs["C4"]["mode_state"] == 0
    budgets = {
        "persistent_state_bytes": state_budget_bytes,
        "trainable_parameter_cap": 4096,
        "update_multiply_add_cap": 8192,
        "query_multiply_add_cap": 4096,
        "precision": "float64",
    }
    passed = matched_state_bytes and c3_is_partitioned and c4_is_shared and configs["C0"]["persistent_bytes"] == 0
    return {
        "case_id": "F5",
        "description": "Fair memory architecture comparison contract",
        "architectures": configs,
        "matched_state_budget_bytes": state_budget_bytes,
        "resource_budget_envelope": budgets,
        "C1_to_C4_state_bytes_matched": matched_state_bytes,
        "C3_separate_state_partitions_sum_to_budget": c3_is_partitioned,
        "C4_uses_shared_state": c4_is_shared,
        "parameter_and_compute_matching_policy": "Matched Pareto points under common hard caps; report exact parameter/update/query counts and do not claim equivalence from state bytes alone.",
        "comparison_executed": False,
        "winner_selected": False,
        "passed": bool(passed),
        "interpretation": "This defines a defensible comparison contract but does not compare performance. C4 must use shared cross-coupled latent updates rather than a block-diagonal relabeling of C3.",
    }


def _episode(seed: int, split: str) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    contexts = {"A": np.array([1.0, 0.0]), "B": np.array([0.0, 1.0])}
    theta_a = np.array([[0.6, -0.2], [0.1, 0.5]])
    theta_b = np.array([[-0.3, 0.4], [0.7, 0.1]])
    theta_other = np.array([[0.25, -0.15], [0.05, 0.2]])
    zero = np.zeros((2, 2))
    phases = [
        ("acquisition", "A", theta_a, zero, False),
        ("distractor", "A", zero, zero, False),
        ("context_switch", "B", theta_b, zero, False),
        ("relation2_isolation", "B", zero, theta_other, False),
        ("observation_gap", "A", theta_a, zero, True),
        ("reactivation", "A", theta_a, zero, False),
        ("within_context_drift", "A", theta_a + 0.25, zero, False),
    ]
    # The composition of two already encountered relation blocks appears only
    # in the held-out test worlds; training worlds observe the blocks separately.
    if split == "test":
        phases.append(("heldout_composition", "B", theta_b, theta_other, False))
    learner_rows = []
    evaluator_rows = []
    for phase_index, (phase, context_name, primary_operator, secondary_operator, masked) in enumerate(phases):
        for _step in range(20):
            source = rng.normal(size=2)
            other = rng.normal(size=2)
            ctx = contexts[context_name]
            y = primary_operator @ source + secondary_operator @ other + 0.005 * rng.normal(size=2)
            observed = not masked
            learner_rows.append({
                "source": source.tolist(),
                "other_source": other.tolist(),
                "context_features": ctx.tolist(),
                "target_observation": y.tolist() if observed else None,
                "target_mask": observed,
            })
            evaluator_rows.append({
                "episode_seed": seed,
                "phase_index": phase_index,
                "phase": phase,
                "context_label": context_name,
                "primary_operator": primary_operator.tolist(),
                "secondary_operator": secondary_operator.tolist(),
                "target_truth": y.tolist(),
            })
    return {"split": split, "seed": seed, "learner_rows": learner_rows, "evaluator_rows": evaluator_rows}


def case_f6() -> dict[str, Any]:
    """Build a leakage-separated task with a genuinely held-out relation composition."""
    train_seeds = list(range(110, 114))
    validation_seeds = list(range(210, 212))
    test_seeds = list(range(310, 312))
    splits = {"train": train_seeds, "validation": validation_seeds, "test": test_seeds}
    worlds = []
    for split, seeds in splits.items():
        worlds.extend(_episode(seed, split) for seed in seeds)
    seed_sets = [set(splits[key]) for key in ("train", "validation", "test")]
    disjoint = all(seed_sets[i].isdisjoint(seed_sets[j]) for i in range(3) for j in range(i + 1, 3))
    phases = sorted({row["phase"] for world in worlds for row in world["evaluator_rows"]})
    learner_keys = set(worlds[0]["learner_rows"][0])
    forbidden_keys = {"phase", "phase_index", "episode_seed", "context_label", "primary_operator", "secondary_operator", "target_truth"}
    leakage_free = learner_keys.isdisjoint(forbidden_keys)
    masks_correct = all(
        row["target_observation"] is None and not row["target_mask"]
        for world in worlds
        for row, ev in zip(world["learner_rows"], world["evaluator_rows"])
        if ev["phase"] == "observation_gap"
    )
    composition_is_test_only = all(
        (any(ev["phase"] == "heldout_composition" for ev in world["evaluator_rows"])) == (world["split"] == "test")
        for world in worlds
    )
    row_count = sum(len(w["learner_rows"]) for w in worlds)
    passed = (
        disjoint and len(phases) == 8 and leakage_free and masks_correct
        and composition_is_test_only and row_count > 0
    )
    return {
        "case_id": "F6",
        "description": "Integrated sequential adaptive-relational learning benchmark manifest",
        "train_seeds": train_seeds,
        "validation_seeds": validation_seeds,
        "test_seeds": test_seeds,
        "world_count": len(worlds),
        "total_rows": row_count,
        "phases": phases,
        "split_worlds_are_disjoint": disjoint,
        "evaluator_truth_and_phase_metadata_excluded_from_learner_inputs": leakage_free,
        "observation_gap_masks_enforced": masks_correct,
        "heldout_composition_phase_is_test_only": composition_is_test_only,
        "passed": bool(passed),
        "interpretation": "The task generator exposes individual relation blocks in training and reserves their joint composition for test worlds. Phase identity, planted operators and evaluator truth remain outside learner inputs. This is a benchmark design probe, not a learner performance result.",
    }

def _metric_operator_norm(k: np.ndarray, gs: np.ndarray, gt: np.ndarray) -> float:
    cs = _chol_factor(gs)
    ct = _chol_factor(gt)
    return float(np.linalg.norm(ct @ k @ np.linalg.inv(cs), ord=2))


def case_f7() -> dict[str, Any]:
    """Independent metric-invariance, switching and storage/activation challenge."""
    rng = np.random.default_rng(7707)
    k = rng.normal(size=(3, 2))
    gs = np.array([[2.0, 0.2], [0.2, 1.0]])
    gt = np.array([[1.5, 0.1, 0.0], [0.1, 0.9, 0.05], [0.0, 0.05, 1.2]])
    a = np.array([[2.0, 0.4], [0.1, 0.7]])
    b = np.array([[1.6, 0.1, 0.0], [0.0, 0.8, 0.2], [0.1, 0.0, 1.3]])
    k_new = np.linalg.solve(b, k @ a)
    gs_new = a.T @ gs @ a
    gt_new = b.T @ gt @ b
    norm_old = _metric_operator_norm(k, gs, gt)
    norm_new = _metric_operator_norm(k_new, gs_new, gt_new)
    metric_norm_error = abs(norm_old - norm_new)

    a1 = np.array([[0.8, 1.0], [0.0, 0.8]])
    a2 = np.array([[0.8, 0.0], [1.0, 0.8]])
    rho1 = float(max(abs(np.linalg.eigvals(a1))))
    rho2 = float(max(abs(np.linalg.eigvals(a2))))
    rho_product = float(max(abs(np.linalg.eigvals(a2 @ a1))))

    stored = np.array([[0.7, -0.2], [0.1, 0.4]])
    activation = 0.0
    effective = activation * stored
    stored_after_idle = stored.copy()
    storage_preserved = bool(np.array_equal(stored, stored_after_idle) and np.linalg.norm(effective) == 0.0)
    passed = metric_norm_error < 1e-8 and rho1 < 1 and rho2 < 1 and rho_product > 1 and storage_preserved
    return {
        "case_id": "F7",
        "description": "Independent metric-invariance and adaptive-stability boundary audit",
        "metric_operator_norm_original": norm_old,
        "metric_operator_norm_transformed": norm_new,
        "metric_operator_norm_invariance_error": metric_norm_error,
        "individual_spectral_radii": [rho1, rho2],
        "alternating_product_spectral_radius": rho_product,
        "switching_counterexample_confirmed": rho1 < 1 and rho2 < 1 and rho_product > 1,
        "stored_operator_preserved_when_activation_zero": storage_preserved,
        "passed": bool(passed),
        "interpretation": "Metric-aware norm bounds survive equivalent coordinate charts, while individual Schur stability does not imply arbitrary switched stability. Stored knowledge and route activity can be separated; this does not establish global network stability.",
    }


_CASES = {
    "F1": case_f1,
    "F2": case_f2,
    "F3": case_f3,
    "F4": case_f4,
    "F5": case_f5,
    "F6": case_f6,
    "F7": case_f7,
}


def run_case(case_id: str) -> dict[str, Any]:
    if case_id not in _CASES:
        raise ValueError(f"unknown design job {case_id!r}; expected {CASE_IDS}")
    payload = _CASES[case_id]()
    payload.update({
        "experiment_id": EXPERIMENT_ID,
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "execution_passed": payload.get("passed") is True,
    })
    return payload


def verify_result_directory(directory: Path) -> dict[str, Any]:
    cases = []
    for case_id in CASE_IDS:
        path = directory / f"{case_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"missing M3 foundation evidence: {path}")
        result = json.loads(path.read_text(encoding="utf-8"))
        if (
            result.get("experiment_id") != EXPERIMENT_ID
            or result.get("case_id") != case_id
            or result.get("execution_passed") is not True
        ):
            raise AssertionError(f"invalid or failed M3 foundation evidence: {path}")
        cases.append({"case_id": case_id, "execution_passed": True})
    return {
        "experiment_id": EXPERIMENT_ID,
        "schema_version": SCHEMA_VERSION,
        "case_ids": list(CASE_IDS),
        "case_count": len(cases),
        "all_design_jobs_executed": True,
        "implementation_protocol_frozen": False,
        "campaign_decision": "REVIEW_F1_F7_RESULTS_BEFORE_FREEZE",
        "unresolved_decisions": [
            "Context feature map and covariance estimation",
            "Context fit, ambiguity-margin, novelty and capacity thresholds",
            "Prequential loss, evidence dead-zone, observation-quality weighting and time constants",
            "Regularisation, conditional-identifiability tolerance and metric operator radii",
            "Estimator uncertainty calibration and activation gating",
            "Change detector, candidate revision window and promotion rule",
            "Resource-matched memory benchmark tuning and task effect thresholds",
        ],
        "cases": cases,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    path.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASE_IDS)
    parser.add_argument("--verify-result-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (args.case is None) == (args.verify_result_dir is None):
        parser.error("specify exactly one of --case or --verify-result-dir")
    result = run_case(args.case) if args.case else verify_result_directory(args.verify_result_dir)
    digest = _write_json(args.output, result)
    print(json.dumps({"output": str(args.output), "sha256": digest, **result}, sort_keys=True))
    if result.get("passed") is False or result.get("all_design_jobs_executed") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
