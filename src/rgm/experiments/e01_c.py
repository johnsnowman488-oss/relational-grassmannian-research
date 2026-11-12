"""E01-C paired diagnostics for memory, representation and path-composition failure."""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ..memory import SOEMemory
from .e01_b import FEATURE_DIM, _support_tensors, codebooks, event_vector, make_case

FloatArray = NDArray[np.float64]
CONDITIONS: dict[str, dict[str, Any]] = {
    "baseline_e4": dict(entities=4, facts=8, distractors=0, depth=2, gap="medium"),
    "repeat_e4": dict(entities=4, facts=8, distractors=32, depth=2, gap="medium"),
    "candidate_e16": dict(entities=16, facts=16, distractors=16, depth=2, gap="medium"),
    "factload_e16": dict(entities=16, facts=64, distractors=16, depth=2, gap="medium"),
    "depth3_e16": dict(entities=16, facts=32, distractors=16, depth=3, gap="medium"),
    "longgap_e16": dict(entities=16, facts=16, distractors=16, depth=2, gap="long"),
}
MEMORY_ARMS = ("slow_only", "full_history")
VARIANTS = ("observed", "repeat_suppressed", "oracle_facts")
WORLD_SEEDS = (501, 502, 503)
CODEBOOK_SEEDS = (9137, 27183, 65537)
DEFAULT_N = 160


def _threshold(scores: list[float], labels: list[int]) -> float:
    values = np.unique(np.asarray([0.0, 1.0, *scores], dtype=np.float64))
    y, s = np.asarray(labels, dtype=np.int64), np.asarray(scores, dtype=np.float64)
    best_t, best_acc = 0.5, -1.0
    for t in values:
        acc = float(np.mean((s >= t).astype(np.int64) == y))
        if acc > best_acc or (acc == best_acc and t > best_t):
            best_t, best_acc = float(t), acc
    return best_t


def _memory_state(case: Any, arm: str, books: tuple[FloatArray, FloatArray],
                  entities: int, suppress: bool) -> FloatArray:
    seen: set[tuple[int, int, int]] = set()
    if arm == "slow_only":
        memory = SOEMemory(feature_dim=FEATURE_DIM, decay_rates=(0.01,))
        for event in case.events:
            key = (event.relation, event.subject, event.object)
            vector = event_vector(event, books, entities)
            if suppress and key in seen:
                vector = np.zeros(FEATURE_DIM, dtype=np.float64)
            else:
                seen.add(key)
            memory.update(vector, dt=event.dt)
        return memory.snapshot()
    if arm == "full_history":
        vectors = []
        for event in case.events:
            key = (event.relation, event.subject, event.object)
            vector = event_vector(event, books, entities)
            if suppress and key in seen:
                vector = np.zeros(FEATURE_DIM, dtype=np.float64)
            else:
                seen.add(key)
            vectors.append(vector)
        return np.sum(vectors, axis=0, dtype=np.float64)[None, :]
    raise ValueError(f"unknown memory arm: {arm}")


def _supports(case: Any, variant: str, arm: str,
              books: tuple[FloatArray, FloatArray], entities: int
              ) -> tuple[FloatArray, FloatArray]:
    if variant == "oracle_facts":
        exact = np.zeros((2, entities, entities), dtype=np.float64)
        for relation, subject, obj in case.facts:
            exact[relation, subject, obj] = 1.0
        return exact[0][None, :, :], exact[1][None, :, :]
    if variant not in ("observed", "repeat_suppressed"):
        raise ValueError(f"unknown variant: {variant}")
    state = _memory_state(case, arm, books, entities, variant == "repeat_suppressed")
    return _support_tensors(state, books, entities)


def _fact_probes(case: Any, support: tuple[FloatArray, FloatArray]
                 ) -> tuple[list[dict[str, Any]], list[float], list[int]]:
    entities = support[0].shape[1]
    true = sorted(case.facts)
    all_facts = [(r, a, b) for r in (0, 1) for a in range(entities)
                 for b in range(entities) if a != b]
    absent = [fact for fact in all_facts if fact not in set(true)]
    n = min(len(true), len(absent))
    rng = np.random.default_rng(case.seed + 910003)
    chosen = rng.choice(len(absent), size=n, replace=False) if n else []
    probes = [(fact, 1) for fact in true]
    probes += [(absent[int(i)], 0) for i in chosen]
    records, scores, labels = [], [], []
    for (r, a, b), label in probes:
        value = float(np.max(support[r][:, a, b]))
        records.append(dict(relation=r, subject=a, object=b, present=label, support=value))
        scores.append(value)
        labels.append(label)
    return records, scores, labels


def _paths(case: Any, support: tuple[FloatArray, FloatArray], depth: int) -> dict[str, Any]:
    entities, facts, records = support[0].shape[1], set(case.facts), []
    for mids in itertools.product(range(entities), repeat=depth - 1):
        nodes = (case.query_subject, *mids, case.query_object)
        edges = [(step % 2, int(nodes[step]), int(nodes[step + 1])) for step in range(depth)]
        edge_scores = [float(np.max(support[r][:, a, b])) for r, a, b in edges]
        records.append(dict(
            nodes=list(map(int, nodes)), edges=[list(edge) for edge in edges],
            edge_supports=edge_scores, score=float(np.prod(edge_scores)),
            is_true=all(edge in facts for edge in edges),
        ))
    records.sort(key=lambda x: x["score"], reverse=True)
    true_paths = [x for x in records if x["is_true"]]
    false_paths = [x for x in records if not x["is_true"]]
    if bool(case.label) != bool(true_paths):
        raise AssertionError(f"generator/path mismatch for case seed {case.seed}")
    best_true = true_paths[0] if true_paths else None
    best_false = false_paths[0] if false_paths else None
    rank = None if best_true is None else 1 + sum(
        x["score"] > best_true["score"] + 1e-15 for x in false_paths
    )
    return dict(
        count=len(records), best_any=records[0], best_true=best_true,
        best_false=best_false, true_paths=true_paths, true_rank=rank,
        top_five=records[:5],
    )


def _prepare(cases: list[Any], variant: str, arm: str,
             books: tuple[FloatArray, FloatArray], entities: int, depth: int
             ) -> tuple[list[dict[str, Any]], list[float], list[int]]:
    rows, scores, labels = [], [], []
    for case in cases:
        support = _supports(case, variant, arm, books, entities)
        fact_records, fact_scores, fact_labels = _fact_probes(case, support)
        path = _paths(case, support, depth)
        rows.append(dict(
            case=case, support=support, fact_records=fact_records,
            fact_scores=fact_scores, fact_labels=fact_labels, path=path,
        ))
        scores.extend(fact_scores)
        labels.extend(fact_labels)
    return rows, scores, labels


def _evaluate(rows: list[dict[str, Any]], fact_t: float, comp_t: float,
              variant: str, arm: str, condition: str) -> dict[str, Any]:
    labels, predictions, fact_y, fact_pred = [], [], [], []
    path_detected, true_scores, false_pos_scores, false_neg_scores = [], [], [], []
    best_path_true, true_ranks, diagnosis_counts, per_sequence = [], [], {}, []
    for row in rows:
        case, path = row["case"], row["path"]
        best, best_true, best_false = path["best_any"], path["best_true"], path["best_false"]
        pred = int(best["score"] >= comp_t)
        labels.append(int(case.label))
        predictions.append(pred)
        fact_y.extend(row["fact_labels"])
        fact_pred.extend(int(v >= fact_t) for v in row["fact_scores"])
        detected = False
        if case.label:
            if best_true is None:
                raise AssertionError("positive case has no true path")
            true_scores.append(float(best_true["score"]))
            false_pos_scores.append(float(best_false["score"]) if best_false else 0.0)
            best_path_true.append(int(bool(best["is_true"])))
            true_ranks.append(int(path["true_rank"]))
            detected = any(
                all(v >= fact_t for v in candidate["edge_supports"])
                for candidate in path["true_paths"]
            )
            path_detected.append(int(detected))
            if not detected:
                diagnosis = "true_path_edge_evidence_missing"
            elif best_true["score"] < comp_t and not pred:
                diagnosis = "true_path_product_below_threshold"
            elif not best["is_true"]:
                diagnosis = "false_candidate_path_outscored_true_path"
            else:
                diagnosis = "true_path_support_sufficient"
        else:
            false_neg_scores.append(float(best["score"]))
            diagnosis = (
                "negative_query_false_path_crossed_threshold"
                if pred else "negative_query_rejected"
            )
        diagnosis_counts[diagnosis] = diagnosis_counts.get(diagnosis, 0) + 1
        path_out = {
            "candidate_path_count": path["count"], "best_any_path": best,
            "best_true_path": best_true, "best_false_path": best_false,
            "best_true_path_rank": path["true_rank"],
            "true_path_count": len(path["true_paths"]), "top_five_paths": path["top_five"],
        }
        per_sequence.append({
            "seed": int(case.seed), "label": int(case.label),
            "query": {"subject": int(case.query_subject), "object": int(case.query_object)},
            "event_count": len(case.events), "unique_fact_count": len(case.facts),
            "distractor_count": int(case.distractor_count),
            "facts": [list(x) for x in sorted(case.facts)],
            "events": [
                {"relation": int(e.relation), "subject": int(e.subject),
                 "object": int(e.object), "dt": float(e.dt)} for e in case.events
            ],
            "fact_probes": row["fact_records"], "path_evidence": path_out,
            "composition_score": float(best["score"]), "composition_prediction": pred,
            "fact_threshold": float(fact_t), "composition_threshold": float(comp_t),
            "true_path_fully_retrieved": detected if case.label else None,
            "diagnosis": diagnosis,
        })
    y, p = np.asarray(labels), np.asarray(predictions)
    fy, fp = np.asarray(fact_y), np.asarray(fact_pred)
    tp = int(np.sum((fy == 1) & (fp == 1)))
    fpos = int(np.sum((fy == 0) & (fp == 1)))
    fneg = int(np.sum((fy == 1) & (fp == 0)))
    tpr, tnr = float(np.mean(p[y == 1] == 1)), float(np.mean(p[y == 0] == 0))
    correct = int(np.sum(y == p))
    return {
        "variant": variant, "memory_arm": arm, "condition": condition,
        "composition": {
            "accuracy": correct / len(y), "true_positive_rate": tpr,
            "true_negative_rate": tnr, "false_positive_rate": 1.0 - tnr,
            "false_negative_rate": 1.0 - tpr,
        },
        "constituent_retrieval": {
            "accuracy": float(np.mean(fy == fp)),
            "precision": tp / max(1, tp + fpos), "recall": tp / max(1, tp + fneg),
        },
        "path_diagnostics": {
            "positive_cases_with_any_true_path_fully_retrieved":
                float(np.mean(path_detected)) if path_detected else None,
            "mean_best_true_path_score": float(np.mean(true_scores)) if true_scores else None,
            "mean_best_false_path_score_positive":
                float(np.mean(false_pos_scores)) if false_pos_scores else None,
            "mean_best_false_path_score_negative":
                float(np.mean(false_neg_scores)) if false_neg_scores else None,
            "positive_cases_best_path_is_true":
                float(np.mean(best_path_true)) if best_path_true else None,
            "median_best_true_path_rank": float(np.median(true_ranks)) if true_ranks else None,
            "candidate_path_count": int(rows[0]["path"]["count"]),
        },
        "diagnosis_counts": diagnosis_counts,
        "sample_counts": {
            "test_sequences": len(rows), "positive_sequences": int(np.sum(y == 1)),
            "negative_sequences": int(np.sum(y == 0)), "fact_probes": len(fy),
        },
        "per_sequence": per_sequence,
    }


def run(condition: str, memory_arm: str, world_seed: int,
        codebook_seed: int, n: int = DEFAULT_N) -> dict[str, Any]:
    if condition not in CONDITIONS or memory_arm not in MEMORY_ARMS:
        raise ValueError("unknown condition or memory arm")
    if world_seed not in WORLD_SEEDS or codebook_seed not in CODEBOOK_SEEDS:
        raise ValueError("world or codebook seed outside frozen set")
    if n < 20:
        raise ValueError("n must be at least 20")
    params = CONDITIONS[condition]
    entities, depth = int(params["entities"]), int(params["depth"])
    books = codebooks(entities, codebook_seed)
    val_start, test_start = 7_000_000 + world_seed * 10_000, 8_000_000 + world_seed * 10_000
    val = [make_case(val_start + i, entities, int(params["facts"]),
                     int(params["distractors"]), depth, str(params["gap"])) for i in range(n)]
    test = [make_case(test_start + i, entities, int(params["facts"]),
                      int(params["distractors"]), depth, str(params["gap"])) for i in range(n)]
    variants = {}
    for variant in VARIANTS:
        vr, fs, fl = _prepare(val, variant, memory_arm, books, entities, depth)
        fact_t = _threshold(fs, fl)
        comp_t = _threshold(
            [float(row["path"]["best_any"]["score"]) for row in vr],
            [int(row["case"].label) for row in vr],
        )
        tr, _, _ = _prepare(test, variant, memory_arm, books, entities, depth)
        variants[variant] = _evaluate(tr, fact_t, comp_t, variant, memory_arm, condition)
    return {
        "experiment": "E01-C mechanism isolation", "condition": condition,
        "parameters": {
            "entities": entities, "distinct_facts": int(params["facts"]),
            "distractor_events": int(params["distractors"]), "depth": depth,
            "gap": str(params["gap"]), "purpose": str(params["purpose"]),
            "candidate_paths": entities ** (depth - 1), "feature_dim": FEATURE_DIM,
        },
        "memory_arm": memory_arm, "world_seed": world_seed,
        "codebook_seed": codebook_seed, "state_scalar_count": FEATURE_DIM,
        "seed_ranges": {
            "validation": [val_start, val_start + n - 1],
            "test": [test_start, test_start + n - 1],
        },
        "sample_counts": {"validation": n, "test": n}, "variants": variants,
        "interpretation_guard": (
            "Synthetic diagnostics only. Oracle facts are an upper-bound intervention. "
            "Repeat suppression preserves event order and elapsed-time updates while removing "
            "later duplicate-fact contributions. Entity counts above four use non-orthogonal "
            "codewords in fixed R^16."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition", choices=tuple(CONDITIONS), required=True)
    parser.add_argument("--memory-arm", choices=MEMORY_ARMS, required=True)
    parser.add_argument("--world-seed", type=int, choices=WORLD_SEEDS, required=True)
    parser.add_argument("--codebook-seed", type=int, choices=CODEBOOK_SEEDS, required=True)
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.condition, args.memory_arm, args.world_seed, args.codebook_seed, args.n)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "condition": args.condition, "memory_arm": args.memory_arm,
        "world_seed": args.world_seed, "codebook_seed": args.codebook_seed,
        "variants": {
            key: {
                "composition_accuracy": value["composition"]["accuracy"],
                "fact_accuracy": value["constituent_retrieval"]["accuracy"],
                "path_diagnostics": value["path_diagnostics"],
            } for key, value in result["variants"].items()
        },
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
