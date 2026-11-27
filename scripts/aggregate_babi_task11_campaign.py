#!/usr/bin/env python3
"""Deterministic aggregation and validation for the 120-unit Task 11 campaign."""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import random
import statistics


ARCHITECTURES = ("HLA", "HLB")
CONDITIONS = (
    "full_learning", "no_temporal", "no_relational",
    "no_abstraction", "no_task", "no_learning",
)
SEEDS = tuple(range(953100, 953110))
BOOTSTRAPS = 10000
BOOTSTRAP_SEED = 953300


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path):
    return sha256(path.read_bytes()).hexdigest()


def _verify_hash_list(root: Path):
    hash_file = root / "sha256sums.txt"
    if not hash_file.is_file():
        raise ValueError(f"missing sha256sums.txt in {root}")
    for line in hash_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        path = root / name
        if not path.is_file() or _sha(path) != digest:
            raise ValueError(f"artifact digest mismatch: {root}/{name}")


def _run_dirs(root: Path):
    return sorted(path.parent for path in root.rglob("per-run-metrics.json"))


def _summary(rows):
    keys = (
        "answer_exact_match", "forecast_coverage",
        "support_witness_recall", "false_witness_rate",
        "abstention_rate", "witness_recovery_mismatch_count",
    )
    result = {}
    for key in keys:
        values = [row["evaluation"].get(key) for row in rows]
        numeric = [float(value) for value in values if value is not None]
        result[key] = {
            "mean_across_seeds": statistics.mean(numeric) if numeric else None,
            "min_across_seeds": min(numeric) if numeric else None,
            "max_across_seeds": max(numeric) if numeric else None,
            "per_seed": {str(row["seed"]): row["evaluation"].get(key) for row in rows},
        }
    return result


def _story_stats(run_rows, run_dirs):
    result = defaultdict(lambda: {
        "correct": 0, "queries": 0, "covered": 0,
        "witness_true": 0, "support_count": 0,
        "false_witness": 0, "predicted_witness": 0,
    })
    for row, root in zip(run_rows, run_dirs):
        prediction_path = root / "prediction-journal.jsonl"
        raw = prediction_path.read_text(encoding="utf-8")
        try:
            prediction_rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        except json.JSONDecodeError:
            # Accept escaped-newline JSONL fixtures while keeping real campaign
            # artifacts on the canonical newline-delimited representation.
            prediction_rows = [
                json.loads(line) for line in raw.replace("\\n", "\n").splitlines()
                if line.strip()
            ]
        story_by_query = {item["query_id"]: item["story_id"] for item in prediction_rows}
        for query in row["evaluation"]["per_query"]:
            story_id = story_by_query.get(query["query_id"])
            if story_id is None:
                raise ValueError(f"missing story mapping for query {query['query_id']}")
            stats = result[story_id]
            stats["correct"] += int(bool(query.get("answer_correct", query.get("answer_exact_match", False))))
            stats["queries"] += 1
            covered = query.get("covered")
            if covered is None:
                covered = not bool(query.get("abstained", False))
            stats["covered"] += int(bool(covered))
            if "predicted_witness_lines" in query and "gold_support_lines" in query:
                predicted = set(query["predicted_witness_lines"])
                gold = set(query["gold_support_lines"])
                stats["witness_true"] += len(predicted & gold)
                stats["support_count"] += len(gold)
                stats["false_witness"] += len(predicted - gold)
                stats["predicted_witness"] += len(predicted)
            else:
                stats["witness_true"] += int(query.get("true_witness_line_count", 0))
                stats["support_count"] += int(query.get("support_line_count", 0))
                stats["false_witness"] += int(query.get("false_witness_line_count", 0))
                stats["predicted_witness"] += int(query.get("predicted_witness_line_count", 0))
    return dict(result)

def _bootstrap_interval(stats, *, metric: str, draws=BOOTSTRAPS, seed=BOOTSTRAP_SEED):
    story_ids = sorted(stats)
    if not story_ids:
        return None
    rng = random.Random(seed)
    values = []
    for _ in range(draws):
        sample = [rng.choice(story_ids) for _ in story_ids]
        total_a = total_b = 0.0
        for story_id in sample:
            row = stats[story_id]
            if metric == "answer_exact_match":
                total_a += row["correct"]
                total_b += row["queries"]
            elif metric == "forecast_coverage":
                total_a += row["covered"]
                total_b += row["queries"]
            elif metric == "support_witness_recall":
                total_a += row["witness_true"]
                total_b += row["support_count"]
            elif metric == "false_witness_rate":
                total_a += row["false_witness"]
                total_b += row["predicted_witness"]
        values.append(total_a / total_b if total_b else 0.0)
    values.sort()
    return {
        "lower_95": values[int(0.025 * draws)],
        "upper_95": values[min(draws - 1, int(0.975 * draws))],
        "resamples": draws,
        "cluster_unit": "whole validation story",
        "seed": seed,
    }


def aggregate(manifest_path: Path, protocol_path: Path, run_root: Path,
              output_root: Path) -> dict:
    manifest, protocol = _load(manifest_path), _load(protocol_path)
    if manifest["protocol_sha256"] != _sha(protocol_path):
        raise ValueError("campaign protocol digest mismatch")
    expected_units = {row["run_unit_key"]: row for row in manifest["run_units"]}
    if len(expected_units) != 120:
        raise ValueError("frozen manifest does not contain exactly 120 unique run units")
    run_dirs = _run_dirs(run_root)
    if len(run_dirs) != 120:
        raise ValueError(f"expected 120 run artifact directories, found {len(run_dirs)}")

    by_key = {}
    row_dir_pairs = []
    for root in run_dirs:
        _verify_hash_list(root)
        row = _load(root / "per-run-metrics.json")
        key = row.get("run_key")
        if key in by_key:
            raise ValueError(f"duplicate run-unit key: {key}")
        if key not in expected_units:
            raise ValueError(f"unexpected run-unit key: {key}")
        unit = expected_units[key]
        if any(row.get(field) != unit[field] for field in (
            "task_id", "architecture", "condition", "seed", "manifest_shard",
        )):
            raise ValueError(f"{key}: run identity/shard differs from frozen manifest")
        if row.get("run_kind") != "campaign" or row.get("status") != "PASS":
            raise ValueError(f"{key}: run unit did not complete successfully")
        if row.get("manifest_sha256") != manifest["manifest_sha256"]:
            raise ValueError(f"{key}: source/partition manifest mismatch")
        if row.get("protocol_sha256") != manifest["protocol_sha256"]:
            raise ValueError(f"{key}: protocol mismatch")
        if row.get("learner_labels_loaded") != 0 or row.get("official_test_queries_loaded") != 0:
            raise ValueError(f"{key}: evaluator/official-test labels crossed learner boundary")
        if row.get("confirmatory_labels_loaded") != 0 or row.get("validation_parameter_updates") != 0:
            raise ValueError(f"{key}: confirmatory or validation boundary violation")
        if row.get("checkpoint_fingerprint") != row.get("restored_checkpoint_fingerprint"):
            raise ValueError(f"{key}: checkpoint restore fingerprint mismatch")
        if not row.get("resource_gate", {}).get("within_limits", False):
            raise ValueError(f"{key}: resource gate failed")
        if row.get("fit_stories") != 1800 or row.get("warm_start_stories") != 1440:
            raise ValueError(f"{key}: fit/warm-start counts differ from protocol")
        if row.get("online_adaptation_stories") != 360 or row.get("validation_stories") != 200:
            raise ValueError(f"{key}: online/validation counts differ from protocol")
        if row.get("validation_queries") != 1000:
            raise ValueError(f"{key}: validation query count differs from protocol")
        pred_rows = [
            json.loads(line) for line in (root / "prediction-journal.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(pred_rows) != 1000 or len({p["query_id"] for p in pred_rows}) != 1000:
            raise ValueError(f"{key}: prediction journal incomplete or duplicated")
        if {p["query_id"] for p in pred_rows} != {
            q["query_id"] for q in row["evaluation"]["per_query"]
        }:
            raise ValueError(f"{key}: prediction journal and evaluator query IDs differ")
        run_config = _load(root / "per-run-config.json")
        if run_config.get("manifest_shard") != unit["shard"]:
            raise ValueError(f"{key}: per-run config shard differs from manifest")
        if model_snapshot.get("manifest_shard") != unit["shard"]:
            raise ValueError(f"{key}: model snapshot shard differs from manifest")
        if run_config.get("native_commit") != manifest["native_commit"]:
            raise ValueError(f"{key}: native runtime commit differs from manifest")
        if run_config.get("soe_feature_dims") != manifest["soe_feature_dims"]:
            raise ValueError(f"{key}: SOE feature dimensions differ from manifest")
        if run_config.get("soe_dt") != manifest["soe_dt"]:
            raise ValueError(f"{key}: SOE time step differs from manifest")
        if run_config.get("top_down_gain") != manifest["top_down_gain"]:
            raise ValueError(f"{key}: top-down gain differs from manifest")
        model_snapshot = _load(root / "model-snapshot.json")
        if model_snapshot.get("run_key") != key or model_snapshot.get("evaluator_labels_included") is not False:
            raise ValueError(f"{key}: answer model snapshot identity or label boundary invalid")
        if model_snapshot.get("top_down_gain") != manifest["top_down_gain"]:
            raise ValueError(f"{key}: model snapshot top-down gain differs from manifest")
        if model_snapshot.get("manifest_sha256") != manifest["manifest_sha256"]:
            raise ValueError(f"{key}: model snapshot manifest identity mismatch")
        if model_snapshot.get("protocol_sha256") != manifest["protocol_sha256"]:
            raise ValueError(f"{key}: model snapshot protocol identity mismatch")
        if model_snapshot.get("source_sha256") != manifest["source"]["sha256"]:
            raise ValueError(f"{key}: model snapshot source identity mismatch")
        if model_snapshot.get("fit_model_fingerprint") != row.get("fit_model_fingerprint"):
            raise ValueError(f"{key}: model snapshot fit fingerprint differs from metrics")
        by_key[key] = row
        row_dir_pairs.append((row, root))

    if set(by_key) != set(expected_units):
        raise ValueError("campaign has missing or extra run-unit keys")

    grouped = defaultdict(list)
    grouped_dirs = defaultdict(list)
    grouped_pairs = defaultdict(list)
    for row, root in row_dir_pairs:
        grouped_pairs[(row["architecture"], row["condition"])].append((row, root))
    for key, pairs in grouped_pairs.items():
        pairs.sort(key=lambda pair: pair[0]["seed"])
        grouped[key] = [pair[0] for pair in pairs]
        grouped_dirs[key] = [pair[1] for pair in pairs]
        rows = grouped[key]
        if len(rows) != 10 or [row["seed"] for row in rows] != list(SEEDS):
            raise ValueError(f"{key}: expected ten unique seeds")

    # These three conditions disable channels that the Task 11 answer head does
    # not consume. Their answer predictions should therefore be invariant.
    invariant_fields = (
        "answer_exact_match", "forecast_coverage",
        "support_witness_recall", "false_witness_rate",
    )
    invariance_checks = []
    for architecture in ARCHITECTURES:
        for seed in SEEDS:
            full = by_key[f"task11-{architecture}-full_learning-seed{seed}"]["evaluation"]
            for condition in ("no_temporal", "no_relational", "no_task"):
                ablated = by_key[f"task11-{architecture}-{condition}-seed{seed}"]["evaluation"]
                for field in invariant_fields:
                    if full.get(field) != ablated.get(field):
                        raise ValueError(
                            f"{architecture}/{seed}: {condition} unexpectedly changed answer metric {field}"
                        )
            invariance_checks.append({
                "architecture": architecture, "seed": seed,
                "conditions": ["no_temporal", "no_relational", "no_task"],
                "answer_metrics_invariant": True,
            })

    for architecture in ARCHITECTURES:
        for condition in ("no_abstraction", "no_learning"):
            for row in grouped[(architecture, condition)]:
                if row["evaluation"]["forecast_coverage"] != 0.0:
                    raise ValueError(f"{row['run_key']}: disabled answer model unexpectedly produced coverage")

    summaries = {}
    bootstrap = {}
    story_stats_by_group = {}
    for architecture in ARCHITECTURES:
        for condition in CONDITIONS:
            key = f"{architecture}/{condition}"
            rows = grouped[(architecture, condition)]
            summaries[key] = _summary(rows)
            stats = _story_stats(rows, grouped_dirs[(architecture, condition)])
            story_stats_by_group[(architecture, condition)] = stats
            bootstrap[key] = {
                metric: _bootstrap_interval(stats, metric=metric,
                    seed=BOOTSTRAP_SEED + ARCHITECTURES.index(architecture) * 100
                         + CONDITIONS.index(condition) * 10 + metric_index)
                for metric_index, metric in enumerate((
                    "answer_exact_match", "forecast_coverage",
                    "support_witness_recall", "false_witness_rate",
                ))
            }

    paired_differences = {}
    for condition in CONDITIONS:
        left = story_stats_by_group[("HLA", condition)]
        right = story_stats_by_group[("HLB", condition)]
        common = sorted(set(left) & set(right))
        rng = random.Random(BOOTSTRAP_SEED + 500 + CONDITIONS.index(condition))
        diffs = []
        for _ in range(BOOTSTRAPS):
            sample = [rng.choice(common) for _ in common]
            left_correct = left_queries = right_correct = right_queries = 0
            for story_id in sample:
                left_correct += left[story_id]["correct"]
                left_queries += left[story_id]["queries"]
                right_correct += right[story_id]["correct"]
                right_queries += right[story_id]["queries"]
            left_score = left_correct / left_queries if left_queries else 0.0
            right_score = right_correct / right_queries if right_queries else 0.0
            diffs.append(right_score - left_score)
        diffs.sort()
        paired_differences[condition] = {
            "metric": "HLB minus HLA answer exact match",
            "lower_95": diffs[int(0.025 * BOOTSTRAPS)],
            "upper_95": diffs[int(0.975 * BOOTSTRAPS)],
            "resamples": BOOTSTRAPS,
            "cluster_unit": "paired whole validation story",
        }

    thresholds = protocol["acceptance_thresholds"]["performance"]
    selected = {}
    candidate_checks = {}
    for architecture in ARCHITECTURES:
        candidates = []
        for row in grouped[(architecture, "full_learning")]:
            evaluation = row["evaluation"]
            qualifies = (
                evaluation["answer_exact_match"] >= 1.0
                and evaluation["forecast_coverage"] >= thresholds["minimum_forecast_coverage"]
                and evaluation["support_witness_recall"] >= thresholds["minimum_support_witness_recall"]
                and evaluation["false_witness_rate"] == thresholds["maximum_false_witness_rate"]
                and row["validation_parameter_updates"] == 0
            )
            candidate_checks[row["run_key"]] = {
                "qualifies": qualifies,
                "answer_exact_match": evaluation["answer_exact_match"],
                "forecast_coverage": evaluation["forecast_coverage"],
                "support_witness_recall": evaluation["support_witness_recall"],
                "false_witness_rate": evaluation["false_witness_rate"],
            }
            if qualifies:
                candidates.append(row)
        candidates.sort(key=lambda row: (
            -row["evaluation"]["answer_exact_match"],
            -row["evaluation"]["support_witness_recall"],
            row["seed"],
        ))
        selected[architecture] = (
            candidates[0]["run_key"] if candidates else None
        )

    output_root.mkdir(parents=True, exist_ok=True)
    candidate_selection = {
        "schema": "HLG-BABI-TASK11-CANDIDATE-SELECTION-v1",
        "selection_partition": "validation only",
        "selection_metric": "match nearest-compatible-antecedent baseline without integrity violations",
        "selected": selected,
        "candidate_checks": candidate_checks,
        "confirmatory_labels_used": False,
        "thresholds_relaxed": False,
        "no_candidate_policy": "If no seed qualifies, select no candidate and do not run confirmatory evaluation.",
    }
    candidate_path = output_root / "candidate-selection.json"
    candidate_path.write_text(json.dumps(candidate_selection, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")
    result = {
        "schema": "HLG-BABI-TASK11-120-UNIT-CAMPAIGN-AGGREGATE-v1",
        "status": "PASS",
        "task_id": 11,
        "run_units_expected": 120,
        "run_units_accepted": len(by_key),
        "manifest_sha256": manifest["manifest_sha256"],
        "protocol_sha256": manifest["protocol_sha256"],
        "conditions": list(CONDITIONS),
        "architectures": list(ARCHITECTURES),
        "seeds": list(SEEDS),
        "group_summaries": summaries,
        "story_clustered_bootstrap_95": bootstrap,
        "paired_hlb_minus_hla_answer_exact_match_95": paired_differences,
        "answer_invariance_checks": invariance_checks,
        "candidate_selection": selected,
        "candidate_selection_file": candidate_path.name,
        "confirmatory_labels_used": False,
        "not_independently_evaluable": [
            "antecedent_top1_accuracy",
            "coreference_edge_precision_recall_f1",
            "entity_chain_exact_match",
        ],
        "claim_boundary": (
            "Task 11 answer and witness results only; no independent coreference-edge gold, "
            "no unrestricted raw-text generalisation claim, and no Task 14/19 result."
        ),
        "execution_authorized": False,
    }
    result_path = output_root / "campaign-aggregate.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    result["aggregate_sha256"] = _sha(result_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = aggregate(args.manifest, args.protocol, args.run_root, args.output_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
