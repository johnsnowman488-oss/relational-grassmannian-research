#!/usr/bin/env python3
"""Build deterministic train/validation inputs and audit Tasks 11/14/19.

Official test members are parsed label-free and remain quarantined. Validation
is a project-defined whole-story 10% split from the en-10k training members.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from rgm.experiments.babi_expansion_adapters import (
    ExpansionStory, GoldLabel, audit_predictions, parse_expansion_source,
)

SEED = "HLG-BABI-EXPANSION-TRAIN-VALID-v1"
TASK_FILES = {
    11: ("qa11_basic-coreference_train.txt", "qa11_basic-coreference_test.txt"),
    14: ("qa14_time-reasoning_train.txt", "qa14_time-reasoning_test.txt"),
    19: ("qa19_path-finding_train.txt", "qa19_path-finding_test.txt"),
}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _split(stories: list[ExpansionStory], task_id: int):
    ranked = sorted(
        stories,
        key=lambda story: sha256(
            f"{SEED}:{task_id}:{story.story_id}".encode("utf-8")
        ).digest(),
    )
    validation_count = max(1, round(len(stories) * 0.10))
    validation_ids = {story.story_id for story in ranked[:validation_count]}
    fit = [story for story in stories if story.story_id not in validation_ids]
    validation = [story for story in stories if story.story_id in validation_ids]
    if set(s.story_id for s in fit) & set(s.story_id for s in validation):
        raise AssertionError("whole-story partition overlap")
    if len(fit) + len(validation) != len(stories):
        raise AssertionError("whole-story partition lost records")
    return fit, validation


def _write_jsonl(path: Path, rows: list[dict]) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return {"path": str(path), "rows": len(rows), "sha256": _sha(path)}


def _input_row(story: ExpansionStory) -> dict:
    return {
        "story_id": story.story_id,
        "task_id": story.task_id,
        "events": [asdict(event) for event in story.events],
        "queries": [asdict(query) for query in story.queries],
    }


def _labels_for_partition(stories: list[ExpansionStory], labels: list[GoldLabel],
                          audit: dict) -> list[dict]:
    selected = {query.query_id for story in stories for query in story.queries}
    mismatches = {item["query_id"]: item for item in audit["mismatches"]}
    rows = []
    for label in labels:
        if label.query_id not in selected:
            continue
        mismatch = mismatches.get(label.query_id)
        query_line = int(label.source_ref.rsplit("=", 1)[1])
        rows.append({
            "query_id": label.query_id,
            "gold_answer": label.answer,
            "support_line_numbers": list(label.support_line_numbers),
            "support_event_ids": [
                label.query_id.rsplit(":line", 1)[0] + f":line{line:06d}"
                for line in label.support_line_numbers
            ],
            "source_ref": label.source_ref,
            "audit_status": "quarantined" if mismatch else "passed",
            "audit_reason": mismatch["reason"] if mismatch else None,
            "oracle_prediction": mismatch["prediction"] if mismatch else None,
            "query_line": query_line,
        })
    return rows


def _verify_supports(source_path: Path, labels: list[GoldLabel]) -> None:
    statement_lines: dict[int, set[int]] = {}
    story_ordinal = 0
    for raw in source_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        left, payload = raw.split(" ", 1)
        line_no = int(left)
        if line_no == 1:
            story_ordinal += 1
            statement_lines[story_ordinal] = set()
        if "\t" not in payload:
            statement_lines[story_ordinal].add(line_no)
    for label in labels:
        ordinal = int(label.query_id.rsplit("story", 1)[1].split(":", 1)[0])
        query_line = int(label.source_ref.rsplit("=", 1)[1])
        if any(
            support >= query_line or support not in statement_lines[ordinal]
            for support in label.support_line_numbers
        ):
            raise ValueError(f"{label.query_id}: support is not a prior same-story statement")


def run(source_root: Path, output_root: Path, max_quarantine_fraction: float) -> dict:
    output_root.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "HLG-BABI-EXPANSION-ADAPTER-AUDIT-v1.0",
        "status": "PASS",
        "validation_policy": {
            "kind": "project_defined_whole_story_split",
            "seed": SEED,
            "validation_fraction": 0.10,
            "official_test": "parsed label-free; no test inputs or labels emitted",
        },
        "tasks": {},
    }

    for task_id, (train_name, test_name) in TASK_FILES.items():
        train_path = source_root / train_name
        test_path = source_root / test_name
        train_stories, train_labels = parse_expansion_source(
            train_path, task_id=task_id, split="train", include_labels=True
        )
        _verify_supports(train_path, train_labels)
        test_stories, test_labels = parse_expansion_source(
            test_path, task_id=task_id, split="test-quarantined", include_labels=False
        )
        if test_labels:
            raise AssertionError("official test labels entered the annotation channel")
        if not test_stories or not train_stories:
            raise ValueError(f"Task {task_id}: empty source split")

        audit = audit_predictions(train_stories, train_labels)
        quarantine_fraction = (
            len(audit["mismatches"]) / max(1, audit["queries"])
        )
        fit, validation = _split(train_stories, task_id)
        task_record = {
            "source": {
                "train_file": train_name,
                "train_sha256": _sha(train_path),
                "train_story_count": len(train_stories),
                "train_query_count": len(train_labels),
                "test_file": test_name,
                "test_sha256": _sha(test_path),
                "test_story_count": len(test_stories),
                "test_query_count": sum(len(s.queries) for s in test_stories),
                "test_label_access": False,
            },
            "partitions": {},
            "oracle_audit": {
                "queries": audit["queries"],
                "exact_matches": audit["exact_matches"],
                "exact_match_rate": audit["exact_match_rate"],
                "quarantined": len(audit["mismatches"]),
                "quarantine_fraction": quarantine_fraction,
                "mismatches": audit["mismatches"],
            },
        }
        for name, selected in (("fit", fit), ("validation", validation)):
            input_path = output_root / f"task{task_id}-{name}.inputs.jsonl"
            label_path = output_root / f"task{task_id}-{name}.labels.jsonl"
            input_meta = _write_jsonl(input_path, [_input_row(s) for s in selected])
            label_rows = _labels_for_partition(selected, train_labels, audit)
            label_meta = _write_jsonl(label_path, label_rows)
            task_record["partitions"][name] = {
                "story_count": len(selected),
                "query_count": sum(len(s.queries) for s in selected),
                "quarantined_query_count": sum(
                    row["audit_status"] == "quarantined" for row in label_rows
                ),
                "inputs": input_meta,
                "evaluator_labels": label_meta,
            }
        report["tasks"][str(task_id)] = task_record
        if quarantine_fraction > max_quarantine_fraction:
            report["status"] = "FAIL"
            raise ValueError(
                f"Task {task_id}: oracle quarantine fraction {quarantine_fraction:.6f} "
                f"exceeds {max_quarantine_fraction:.6f}; see diagnostics: "
                f"{audit['mismatches'][:10]!r}"
            )

    report_path = output_root / "adapter-audit.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)
    report["report_sha256"] = _sha(report_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path("data/babi-v1.2-expansion"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/babi-expansion"))
    parser.add_argument("--max-quarantine-fraction", type=float, default=0.005)
    args = parser.parse_args()
    report = run(args.source_root, args.output_root, args.max_quarantine_fraction)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
