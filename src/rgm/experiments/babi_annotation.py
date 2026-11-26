"""Deterministic source-template annotation for bAbI Tasks 3 and 5.

This is a narrow, auditable grammar for the benchmark's controlled templates,
not a general natural-language parser. Gold answers/support IDs are emitted to
a separate evaluator-only label stream and never enter StructuredStory inputs.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
import hashlib
import json
import re

from rgm.experiments.babi_structured import (
    StructuredEvent, StructuredQuery, StructuredStory,
    task3_object_location_before_move, task5_answer_role,
)


def _entity(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _event(task_id: int, story_id: str, line_no: int, sentence: str) -> StructuredEvent:
    source_ref = f"{story_id}#line={line_no}"
    event_id = f"{story_id}:line{line_no:06d}"
    common_patterns = (
        ("MOVE", r"(?P<actor>[A-Za-z]+)\s+(?:went(?:\s+back)?|moved|travelled|traveled|journeyed)\s+to\s+the\s+(?P<destination>.+?)\.?"),
        ("PICK_UP", r"(?P<actor>[A-Za-z]+)\s+(?:picked\s+up|grabbed|took|got)\s+the\s+(?P<object>.+?)(?:\s+there)?\.?"),
        ("DROP", r"(?P<actor>[A-Za-z]+)\s+(?:dropped|left|discarded|put\s+down)\s+the\s+(?P<object>.+?)(?:\s+there)?\.?"),
    )
    for kind, pattern in common_patterns:
        match = re.fullmatch(pattern, sentence.strip(), flags=re.IGNORECASE)
        if match:
            roles = {key: _entity(value) for key, value in match.groupdict().items()}
            return StructuredEvent(event_id, kind, tuple(roles.items()), line_no, line_no, source_ref)
    if task_id == 5:
        give_patterns = (
            r"(?P<giver>[A-Za-z]+)\s+(?:gave|handed)\s+the\s+(?P<object>.+?)\s+to\s+(?P<recipient>[A-Za-z]+)\.?",
            r"(?P<recipient>[A-Za-z]+)\s+was\s+(?:given|handed)\s+the\s+(?P<object>.+?)\s+by\s+(?P<giver>[A-Za-z]+)\.?",
        )
        for pattern in give_patterns:
            match = re.fullmatch(pattern, sentence.strip(), flags=re.IGNORECASE)
            if match:
                roles = {key: _entity(value) for key, value in match.groupdict().items()}
                return StructuredEvent(event_id, "GIVE", tuple(roles.items()), line_no, line_no, source_ref)
        pass_patterns = (
            r"(?P<sender>[A-Za-z]+)\s+passed\s+the\s+(?P<object>.+?)\s+to\s+(?P<recipient>[A-Za-z]+)\.?",
            r"(?P<recipient>[A-Za-z]+)\s+was\s+passed\s+the\s+(?P<object>.+?)\s+by\s+(?P<sender>[A-Za-z]+)\.?",
        )
        for pattern in pass_patterns:
            match = re.fullmatch(pattern, sentence.strip(), flags=re.IGNORECASE)
            if match:
                roles = {key: _entity(value) for key, value in match.groupdict().items()}
                return StructuredEvent(event_id, "PASS", tuple(roles.items()), line_no, line_no, source_ref)
    raise ValueError(f"unrecognised Task {task_id} source statement at {source_ref}: {sentence!r}")
def _task3_query(story_id: str, line_no: int, question: str,
                 prior_events: list[StructuredEvent]) -> StructuredQuery:
    match = re.fullmatch(
        r"Where\s+was\s+the\s+(?P<object>.+?)\s+before\s+the\s+(?P<destination>.+?)\?",
        question.strip(), flags=re.IGNORECASE,
    )
    if not match:
        raise ValueError(f"unrecognised Task 3 query at {story_id}#line={line_no}: {question!r}")
    object_id, destination_id = (_entity(match.group("object")), _entity(match.group("destination")))
    holder: dict[str, str] = {}
    candidates: list[StructuredEvent] = []
    for event in sorted(prior_events, key=lambda item: (item.event_time, item.event_id)):
        if event.observed_at > line_no:
            continue
        roles = event.role_map()
        if event.event_type == "MOVE":
            if roles["destination"] == destination_id and holder.get(object_id) == roles["actor"]:
                candidates.append(event)
        elif event.event_type == "PICK_UP":
            if roles["object"] == object_id:
                holder[object_id] = roles["actor"]
        elif event.event_type == "DROP":
            if roles["object"] == object_id and holder.get(object_id) == roles["actor"]:
                holder.pop(object_id, None)
    if not candidates:
        timeline = [
            (event.event_time, event.event_type, event.role_map())
            for event in sorted(prior_events, key=lambda item: (item.event_time, item.event_id))
        ]
        raise ValueError(
            f"cannot independently anchor Task 3 query to a MOVE by the current holder: "
            f"{story_id}#line={line_no}; object={object_id}; destination={destination_id}; "
            f"timeline={timeline!r}"
        )
    target = candidates[-1]
    return StructuredQuery(
        query_id=f"{story_id}:line{line_no:06d}", story_id=story_id, task_id=3,
        query_type="OBJECT_LOCATION_BEFORE_MOVE", answer_role="location",
        observed_at=line_no, source_ref=f"{story_id}#line={line_no}",
        object_id=object_id, destination_id=destination_id,
        target_event_id=target.event_id,
    )


def _task5_query(story_id: str, line_no: int, question: str) -> StructuredQuery:
    q = question.strip()
    patterns = (
        (r"Who\s+gave\s+the\s+(?P<object>.+?)\s+to\s+(?P<recipient>[A-Za-z]+)\?", "giver"),
        (r"Who\s+gave\s+the\s+(?P<object>.+?)\?", "giver"),
        (r"Who\s+received\s+the\s+(?P<object>.+?)\?", "recipient"),
        (r"Who\s+did\s+(?P<giver>[A-Za-z]+)\s+give\s+the\s+(?P<object>.+?)\s+to\?", "recipient"),
        (r"What\s+did\s+(?P<giver>[A-Za-z]+)\s+give\s+to\s+(?P<recipient>[A-Za-z]+)\?", "object"),
        (r"What\s+did\s+(?P<recipient>[A-Za-z]+)\s+receive\?", "object"),
    )
    for pattern, answer_role in patterns:
        match = re.fullmatch(pattern, q, flags=re.IGNORECASE)
        if match:
            roles = tuple((key, _entity(value)) for key, value in match.groupdict().items() if value is not None)
            return StructuredQuery(
                query_id=f"{story_id}:line{line_no:06d}", story_id=story_id, task_id=5,
                query_type="GIVE_ROLE", answer_role=answer_role,
                observed_at=line_no, source_ref=f"{story_id}#line={line_no}",
                bound_roles=roles,
            )
    raise ValueError(f"unrecognised Task 5 query at {story_id}#line={line_no}: {question!r}")


def _support_ids(story_id: str, raw: str) -> tuple[str, ...]:
    if not raw.strip():
        return ()
    try:
        numbers = [int(value) for value in raw.split()]
    except ValueError as exc:
        raise ValueError(f"invalid official support-line list for {story_id}: {raw!r}") from exc
    return tuple(f"{story_id}:line{number:06d}" for number in numbers)


def parse_source_file(path: Path, *, task_id: int, split: str,
                      include_labels: bool = True) -> list[tuple[StructuredStory, list[dict[str, Any]]]]:
    """Parse numbered stories; confirmatory callers can forbid label access entirely."""

    if task_id not in (3, 5):
        raise ValueError("only bAbI Tasks 3 and 5 are supported")
    rows = path.read_text(encoding="utf-8").splitlines()
    output: list[tuple[StructuredStory, list[dict[str, Any]]]] = []
    story_ordinal = 0
    current_id: str | None = None
    events: list[StructuredEvent] = []
    queries: list[StructuredQuery] = []
    labels: list[dict[str, Any]] = []

    def finish() -> None:
        if current_id is None:
            return
        story = StructuredStory(current_id, tuple(events), tuple(queries))
        event_ids = {event.event_id for event in events}
        for label in labels:
            if not set(label["support_event_ids"]).issubset(event_ids):
                raise ValueError(f"gold support ID does not resolve to a parsed event in {current_id}")
        output.append((story, list(labels)))

    for raw_line in rows:
        if not raw_line.strip():
            continue
        match = re.match(r"^(\d+)\s+(.*)$", raw_line)
        if not match:
            raise ValueError(f"invalid numbered source line in {path}: {raw_line!r}")
        line_no, payload = int(match.group(1)), match.group(2)
        if line_no == 1:
            finish()
            story_ordinal += 1
            current_id = f"task{task_id}/{split}/story{story_ordinal:06d}"
            events, queries, labels = [], [], []
        if current_id is None:
            raise ValueError(f"source file {path} does not begin with story line 1")
        if include_labels:
            fields = payload.split("\t")
            sentence = fields[0].strip()
        else:
            sentence = payload.split("\t", 1)[0].strip()
            fields = [sentence]
        if sentence.endswith("?"):
            query = (_task3_query(current_id, line_no, sentence, events) if task_id == 3
                     else _task5_query(current_id, line_no, sentence))
            queries.append(query)
            if include_labels:
                answer = fields[1].strip() if len(fields) > 1 else ""
                supports = _support_ids(current_id, fields[2] if len(fields) > 2 else "")
                labels.append({
                    "query_id": query.query_id,
                    "gold_answer": _entity(answer),
                    "support_event_ids": list(supports),
                    "source_ref": query.source_ref,
                })
        else:
            events.append(_event(task_id, current_id, line_no, sentence))
    finish()
    return output


def _story_input(story: StructuredStory) -> dict[str, Any]:
    return {
        "story_id": story.story_id,
        "task_id": story.queries[0].task_id if story.queries else None,
        "events": [asdict(event) for event in story.events],
        "queries": [asdict(query) for query in story.queries],
    }


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


WARM_ONLINE_SEED = "HLG-BABI-T3-T5-WARM-ONLINE-v1"
WARM_START_FRACTION = 2.0 / 3.0


def split_fit_stories(
    stories: list[tuple[StructuredStory, list[dict[str, Any]]]], *, task_id: int,
) -> tuple[list[tuple[StructuredStory, list[dict[str, Any]]]],
           list[tuple[StructuredStory, list[dict[str, Any]]]]]:
    """Deterministically split the 1,800 fit stories into 1,200/600 whole-story sets."""
    ranked = sorted(
        stories,
        key=lambda item: hashlib.sha256(
            f"{WARM_ONLINE_SEED}:{task_id}:{item[0].story_id}".encode("utf-8")
        ).digest(),
    )
    warm_count = round(len(stories) * WARM_START_FRACTION)
    warm_ids = {item[0].story_id for item in ranked[:warm_count]}
    warm = [item for item in stories if item[0].story_id in warm_ids]
    online = [item for item in stories if item[0].story_id not in warm_ids]
    return warm, online


def write_annotation_bundle(source_root: Path, output_root: Path) -> dict[str, Any]:
    """Build source-indexed fit/validation inputs and isolated evaluator labels."""
    output_root.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": "HLG-BABI-ANNOTATION-BUNDLE-v1",
        "protocol_id": "HLG-BABI-T3-T5-LEARNING-v1.2",
        "parser": "deterministic source-template grammar; not general NLP",
        "warm_online_split": {
            "seed": WARM_ONLINE_SEED,
            "warm_start_fraction": WARM_START_FRACTION,
            "target_counts_per_task": {"warm_start": 1200, "online_adaptation": 600},
            "unit": "whole story block",
        },
        "splits": {},
        "audit": {"fit_validation_queries": 0, "fit_validation_exact_matches": 0},
    }

    def write_partition(task_id: int, split_name: str,
                        selected: list[tuple[StructuredStory, list[dict[str, Any]]]],
                        *, audit: bool) -> None:
        input_path = output_root / f"task{task_id}-{split_name}.inputs.jsonl"
        label_path = output_root / f"task{task_id}-{split_name}.labels.jsonl"
        input_lines, label_lines = [], []
        exact = 0
        for story, labels in selected:
            input_lines.append(json.dumps(_story_input(story), sort_keys=True))
            label_lines.extend(json.dumps(label, sort_keys=True) for label in labels)
            if audit:
                event_index = {event.event_id: event for event in story.events}
                for query, label in zip(story.queries, labels):
                    if task_id == 3:
                        answer = task3_object_location_before_move(
                            story.events, object_id=query.object_id or "",
                            destination_id=query.destination_id or "",
                            target_event_id=query.target_event_id or "",
                            observation_cutoff=query.observed_at,
                        )
                    else:
                        answer_values = task5_answer_role(
                            story.events, bound_roles=dict(query.bound_roles),
                            answer_role=query.answer_role,
                            observation_cutoff=query.observed_at,
                        )
                        answer = answer_values[0] if answer_values else None
                    if answer != label["gold_answer"]:
                        raise ValueError(
                            f"independent annotation/oracle audit mismatch for {query.query_id}: "
                            f"predicted={answer!r} gold={label['gold_answer']!r}"
                        )
                    if not label["support_event_ids"]:
                        raise ValueError(f"query has no official support witnesses: {query.query_id}")
                    if not set(label["support_event_ids"]).issubset(event_index):
                        raise ValueError(f"support witness missing from parsed story: {query.query_id}")
                    exact += 1
        input_path.write_text("\n".join(input_lines) + "\n", encoding="utf-8")
        label_path.write_text("\n".join(label_lines) + "\n", encoding="utf-8")
        report["splits"][f"task{task_id}_{split_name}"] = {
            "story_count": len(selected),
            "query_count": sum(len(story.queries) for story, _ in selected),
            "input_path": str(input_path),
            "input_sha256": _digest(input_path),
            "label_path": str(label_path),
            "label_sha256": _digest(label_path),
            "annotation_coverage": "100% or hard failure",
            "gold_audit": "exact answer and support-ID resolution passed" if audit else "fit-only labels; no separate oracle audit",
        }
        if audit:
            report["audit"]["fit_validation_queries"] += sum(len(story.queries) for story, _ in selected)
            report["audit"]["fit_validation_exact_matches"] += exact

    for task_id in (3, 5):
        prefix = "qa3" if task_id == 3 else "qa5"
        for split, filename in (("fit", f"{prefix}_train.txt"),
                                ("validation", f"{prefix}_valid.txt")):
            source = source_root / filename
            stories = parse_source_file(source, task_id=task_id, split=split, include_labels=True)
            write_partition(task_id, split, stories, audit=True)
            if split == "fit":
                warm, online = split_fit_stories(stories, task_id=task_id)
                write_partition(task_id, "warm-start", warm, audit=False)
                write_partition(task_id, "online-adaptation", online, audit=False)

    manifest_path = output_root / "annotation-manifest.json"
    manifest_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["manifest_sha256"] = _digest(manifest_path)
    return report
