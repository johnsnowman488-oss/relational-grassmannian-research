"""Independent, source-template adapters for bAbI Tasks 11, 14 and 19.

The adapters consume source lines and produce task-specific observed inputs.
Gold answers/support IDs are returned in a separate evaluator-only channel.
They do not modify or widen the frozen Task 3/5 parser or runner.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias
import re


@dataclass(frozen=True)
class Task11MentionEvent:
    """Raw mention observation; identity resolution is baseline/learner-derived.

    No entity binding or antecedent witness is stored in the source adapter.
    """
    event_id: str
    surface_mention: str
    is_pronoun: bool
    location: str
    observed_at: int
    source_ref: str


@dataclass(frozen=True)
class Task14TemporalEvent:
    event_id: str
    actor: str
    destination: str
    temporal_anchor: str
    event_time: tuple[int, int]
    observed_at: int
    source_ref: str


@dataclass(frozen=True)
class Task19SpatialEdge:
    event_id: str
    start: str
    end: str
    direction: str
    observed_at: int
    source_ref: str


TaskEvent: TypeAlias = Task11MentionEvent | Task14TemporalEvent | Task19SpatialEdge


@dataclass(frozen=True)
class ExpansionQuery:
    query_id: str
    task_id: int
    observed_at: int
    source_ref: str
    entity: str | None = None
    target_location: str | None = None
    start_location: str | None = None
    end_location: str | None = None


@dataclass(frozen=True)
class ExpansionStory:
    story_id: str
    task_id: int
    events: tuple[TaskEvent, ...]
    queries: tuple[ExpansionQuery, ...]


@dataclass(frozen=True)
class GoldLabel:
    query_id: str
    answer: str
    support_line_numbers: tuple[int, ...]
    source_ref: str


@dataclass(frozen=True)
class Prediction:
    answer: str | None
    witness_event_ids: tuple[str, ...]
    abstained: bool
    reason: str | None = None


class AmbiguousPathError(ValueError):
    """Raised when equally short valid routes yield different answer sequences."""


# These are lexical gender priors used only to interpret this controlled source
# grammar. The resolved entity is always explicit in the emitted input event.
_NAME_GENDER = {
    "mary": "female", "sandra": "female", "julie": "female",
    "john": "male", "daniel": "male", "fred": "male", "bill": "male",
}
_PRONOUN_GENDER = {"she": "female", "he": "male"}
_TEMPORAL_RANK = {
    "yesterday": 0,
    "this morning": 1,
    "this afternoon": 2,
    "this evening": 3,
}
_DIRECTIONS = {"n": "north", "s": "south", "e": "east", "w": "west"}
_INVERSE = {"north": "south", "south": "north", "east": "west", "west": "east"}
_DIRECTION_ORDER = ("north", "south", "east", "west")
_LINE = re.compile(r"^(\d+)\s+(.*)$")


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _line_id(story_id: str, line_no: int) -> str:
    return f"{story_id}:line{line_no:06d}"


def _records(path: Path):
    """Yield (story ordinal, line number, payload); reject broken story numbering."""
    ordinal = 0
    previous = 0
    for physical_line, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        match = _LINE.fullmatch(raw)
        if not match:
            raise ValueError(f"{path}:{physical_line}: expected numbered bAbI record")
        line_no, payload = int(match.group(1)), match.group(2)
        if line_no == 1:
            ordinal += 1
            previous = 0
        if ordinal == 0:
            raise ValueError(f"{path}:{physical_line}: first story must start at line 1")
        if line_no != previous + 1:
            raise ValueError(
                f"{path}:{physical_line}: expected story-local line {previous + 1}, got {line_no}"
            )
        previous = line_no
        yield ordinal, line_no, payload


def _label(query_id: str, payload: str, source_ref: str) -> GoldLabel:
    fields = payload.split("\t")
    if len(fields) != 3:
        raise ValueError(f"{source_ref}: question requires question, answer and support fields")
    answer, support = fields[1].strip(), fields[2].strip()
    if not answer or not support:
        raise ValueError(f"{source_ref}: answer and support fields must be non-empty")
    try:
        support_ids = tuple(int(item) for item in support.split())
    except ValueError as exc:
        raise ValueError(f"{source_ref}: malformed support-line list") from exc
    if len(support_ids) != len(set(support_ids)):
        raise ValueError(f"{source_ref}: duplicate support-line ID")
    return GoldLabel(query_id, answer, support_ids, source_ref)


def parse_task11(path: Path, *, split: str, include_labels: bool = True):
    """Parse singular coreference and location-state questions for Task 11."""
    stories: dict[int, dict[str, list]] = {}
    labels: list[GoldLabel] = []
    move_pattern = re.compile(
        r"(?:(?:After that|Afterwards|Following that|Then)\s+)?"
        r"(?P<mention>[A-Za-z]+)\s+"
        r"(?:went(?:\s+back)?|moved|travelled|traveled|journeyed)\s+"
        r"to\s+the\s+(?P<location>[A-Za-z]+)\.?",
        re.IGNORECASE,
    )
    question_pattern = re.compile(r"Where\s+is\s+(?P<entity>[A-Za-z]+)\?", re.IGNORECASE)

    for ordinal, line_no, payload in _records(path):
        story_id = f"task11/{split}/story{ordinal:06d}"
        state = stories.setdefault(ordinal, {"id": story_id, "events": [], "queries": []})
        body = payload.split("\t", 1)[0].strip()
        source_ref = f"{story_id}#line={line_no}"
        event_id = _line_id(story_id, line_no)
        if "?" in body:
            match = question_pattern.fullmatch(body)
            if not match:
                raise ValueError(f"{source_ref}: unsupported Task 11 question: {body!r}")
            entity = _norm(match.group("entity"))
            query = ExpansionQuery(
                event_id, 11, line_no, source_ref, entity=entity
            )
            state["queries"].append(query)
            if include_labels:
                labels.append(_label(event_id, payload, source_ref))
            continue

        match = move_pattern.fullmatch(body)
        if not match:
            raise ValueError(f"{source_ref}: unsupported Task 11 statement: {body!r}")
        mention = match.group("mention").casefold()
        location = _norm(match.group("location"))
        is_pronoun = mention in _PRONOUN_GENDER
        # Preserve only the observed surface mention. Antecedent selection is
        # deliberately deferred to a baseline or to the learning runtime.
        state["events"].append(Task11MentionEvent(
            event_id, mention, is_pronoun, location, line_no, source_ref,
        ))

    result = [
        ExpansionStory(v["id"], 11, tuple(v["events"]), tuple(v["queries"]))
        for _, v in sorted(stories.items())
    ]
    return result, labels


def parse_task14(path: Path, *, split: str, include_labels: bool = True):
    """Parse time-anchored movements and 'before the <place>' queries."""
    stories: dict[int, dict[str, list]] = {}
    labels: list[GoldLabel] = []
    statement = re.compile(
        r"(?:(?P<prefix>Yesterday|This morning|This afternoon|This evening)\s+)?"
        r"(?P<actor>[A-Za-z]+)\s+"
        r"(?:went(?:\s+back)?|moved|travelled|traveled|journeyed)\s+"
        r"to\s+the\s+(?P<destination>[A-Za-z]+)"
        r"(?:\s+(?P<suffix>yesterday|this morning|this afternoon|this evening))?\.?",
        re.IGNORECASE,
    )
    question = re.compile(
        r"Where\s+was\s+(?P<actor>[A-Za-z]+)\s+before\s+the\s+(?P<destination>[A-Za-z]+)\?",
        re.IGNORECASE,
    )

    for ordinal, line_no, payload in _records(path):
        story_id = f"task14/{split}/story{ordinal:06d}"
        state = stories.setdefault(ordinal, {"id": story_id, "events": [], "queries": []})
        body = payload.split("\t", 1)[0].strip()
        source_ref = f"{story_id}#line={line_no}"
        event_id = _line_id(story_id, line_no)
        if "?" in body:
            match = question.fullmatch(body)
            if not match:
                raise ValueError(f"{source_ref}: unsupported Task 14 question: {body!r}")
            query = ExpansionQuery(
                event_id, 14, line_no, source_ref,
                entity=_norm(match.group("actor")),
                target_location=_norm(match.group("destination")),
            )
            state["queries"].append(query)
            if include_labels:
                labels.append(_label(event_id, payload, source_ref))
            continue
        match = statement.fullmatch(body)
        if not match:
            raise ValueError(f"{source_ref}: unsupported Task 14 statement: {body!r}")
        anchor = (match.group("prefix") or match.group("suffix") or "").casefold()
        if not anchor:
            raise ValueError(f"{source_ref}: movement has no temporal anchor")
        anchor = " ".join(anchor.split())
        state["events"].append(Task14TemporalEvent(
            event_id, _norm(match.group("actor")),
            _norm(match.group("destination")), anchor,
            (_TEMPORAL_RANK[anchor], line_no), line_no, source_ref,
        ))

    result = [
        ExpansionStory(v["id"], 14, tuple(v["events"]), tuple(v["queries"]))
        for _, v in sorted(stories.items())
    ]
    return result, labels


def parse_task19(path: Path, *, split: str, include_labels: bool = True):
    """Parse directed spatial relations and ordered two-step route questions."""
    stories: dict[int, dict[str, list]] = {}
    labels: list[GoldLabel] = []
    statement = re.compile(
        r"The\s+(?P<left>[A-Za-z]+)\s+is\s+"
        r"(?P<direction>north|south|east|west)\s+of\s+the\s+(?P<right>[A-Za-z]+)\.?",
        re.IGNORECASE,
    )
    question = re.compile(
        r"How\s+do\s+you\s+go\s+from\s+the\s+(?P<start>[A-Za-z]+)\s+"
        r"to\s+the\s+(?P<end>[A-Za-z]+)\?",
        re.IGNORECASE,
    )

    for ordinal, line_no, payload in _records(path):
        story_id = f"task19/{split}/story{ordinal:06d}"
        state = stories.setdefault(ordinal, {"id": story_id, "events": [], "queries": []})
        body = payload.split("\t", 1)[0].strip()
        source_ref = f"{story_id}#line={line_no}"
        event_id = _line_id(story_id, line_no)
        if "?" in body:
            match = question.fullmatch(body)
            if not match:
                raise ValueError(f"{source_ref}: unsupported Task 19 question: {body!r}")
            query = ExpansionQuery(
                event_id, 19, line_no, source_ref,
                start_location=_norm(match.group("start")),
                end_location=_norm(match.group("end")),
            )
            state["queries"].append(query)
            if include_labels:
                label = _label(event_id, payload, source_ref)
                if not re.fullmatch(r"[nsew](?:,[nsew])*", label.answer):
                    raise ValueError(f"{source_ref}: Task 19 answer must be comma-separated n/s/e/w")
                labels.append(label)
            continue
        match = statement.fullmatch(body)
        if not match:
            raise ValueError(f"{source_ref}: unsupported Task 19 statement: {body!r}")
        # "X is east of Y" means the path from Y to X travels east.
        state["events"].append(Task19SpatialEdge(
            event_id, _norm(match.group("right")), _norm(match.group("left")),
            match.group("direction").casefold(), line_no, source_ref,
        ))

    result = [
        ExpansionStory(v["id"], 19, tuple(v["events"]), tuple(v["queries"]))
        for _, v in sorted(stories.items())
    ]
    return result, labels


def parse_expansion_source(path: Path, *, task_id: int, split: str,
                           include_labels: bool = True):
    adapters = {11: parse_task11, 14: parse_task14, 19: parse_task19}
    try:
        parser = adapters[task_id]
    except KeyError as exc:
        raise ValueError(f"no expansion adapter for Task {task_id}") from exc
    return parser(path, split=split, include_labels=include_labels)


def predict_task11(story: ExpansionStory, query: ExpansionQuery) -> Prediction:
    """Nearest gender-compatible antecedent baseline over raw mention events.

    This is a deterministic, source-grammar baseline, not a parser annotation
    and not a learned coreference result. It sees no GoldLabel or support IDs.
    """
    if story.task_id != 11 or query.task_id != 11:
        raise ValueError("Task 11 predictor received another task's input")
    history: list[tuple[str, str, str]] = []
    state: dict[str, tuple[str, str, tuple[str, ...]]] = {}
    for event in story.events:
        if not isinstance(event, Task11MentionEvent) or event.observed_at >= query.observed_at:
            continue
        mention = event.surface_mention.casefold()
        if not event.is_pronoun:
            entity = _norm(mention)
            history.append((entity, event.event_id, _NAME_GENDER.get(entity, "unknown")))
            state[entity] = (event.location, event.event_id, (event.event_id,))
            continue
        gender = _PRONOUN_GENDER.get(mention)
        if not gender:
            continue
        candidates = [row for row in history if row[2] == gender]
        if not candidates:
            continue
        entity, antecedent_id, _ = candidates[-1]
        previous = state.get(entity)
        witnesses = (antecedent_id, event.event_id)
        if previous:
            witnesses = tuple(dict.fromkeys(previous[2] + witnesses))
        state[entity] = (event.location, event.event_id, witnesses)
    target = state.get(query.entity or "")
    if target is None:
        return Prediction(None, (), True, "entity_state_not_observed")
    return Prediction(target[0], target[2], False)


def predict_task14(story: ExpansionStory, query: ExpansionQuery) -> Prediction:
    if story.task_id != 14 or query.task_id != 14:
        raise ValueError("Task 14 predictor received another task's input")
    events = [
        event for event in story.events
        if isinstance(event, Task14TemporalEvent) and event.observed_at < query.observed_at
    ]
    targets = [
        event for event in events
        if event.actor == query.entity and event.destination == query.target_location
    ]
    if not targets:
        return Prediction(None, (), True, "target_event_not_observed")
    target = max(targets, key=lambda event: event.event_time)
    prior = [
        event for event in events
        if event.actor == query.entity and event.event_time < target.event_time
    ]
    if not prior:
        return Prediction(None, (target.event_id,), True, "no_prior_temporal_location")
    previous = max(prior, key=lambda event: event.event_time)
    return Prediction(previous.destination, (previous.event_id, target.event_id), False)


def predict_task19(story: ExpansionStory, query: ExpansionQuery) -> Prediction:
    if story.task_id != 19 or query.task_id != 19:
        raise ValueError("Task 19 predictor received another task's input")
    graph: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for event in story.events:
        if not isinstance(event, Task19SpatialEdge) or event.observed_at >= query.observed_at:
            continue
        graph[event.start].append((event.end, event.direction, event.event_id))
        graph[event.end].append((event.start, _INVERSE[event.direction], event.event_id))
    for node in graph:
        graph[node].sort(key=lambda item: (_DIRECTION_ORDER.index(item[1]), item[0], item[2]))

    # Enumerate only shortest simple paths. Distinct shortest direction sequences
    # are a genuine ambiguity and cause explicit abstention rather than guessing.
    queue = deque([(query.start_location, (), (), frozenset({query.start_location}))])
    best_depth: int | None = None
    solutions: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
    while queue:
        node, directions, witnesses, visited = queue.popleft()
        depth = len(directions)
        if best_depth is not None and depth > best_depth:
            break
        if node == query.end_location and directions:
            best_depth = depth
            solutions.append((directions, witnesses))
            continue
        for next_node, direction, event_id in graph.get(node, []):
            if next_node in visited:
                continue
            queue.append((
                next_node, directions + (direction,), witnesses + (event_id,),
                visited | {next_node},
            ))
    if not solutions:
        return Prediction(None, (), True, "no_observed_path")
    direction_sequences = {item[0] for item in solutions}
    if len(direction_sequences) > 1:
        return Prediction(None, (), True, "ambiguous_shortest_paths")
    directions, witnesses = sorted(solutions, key=lambda item: item[1])[0]
    answer = ",".join(next(code for code, word in _DIRECTIONS.items() if word == d)
                      for d in directions)
    return Prediction(answer, witnesses, False)


def audit_predictions(stories: list[ExpansionStory], labels: list[GoldLabel]) -> dict:
    """Compare independent task oracles to evaluator-only labels; never feeds labels back."""
    by_query = {label.query_id: label for label in labels}
    counts = {"queries": 0, "exact_matches": 0, "mismatches": [], "missing_labels": []}
    predictors = {11: predict_task11, 14: predict_task14, 19: predict_task19}
    for story in stories:
        for query in story.queries:
            label = by_query.get(query.query_id)
            if label is None:
                counts["missing_labels"].append(query.query_id)
                continue
            prediction = predictors[story.task_id](story, query)
            counts["queries"] += 1
            expected = label.answer if story.task_id == 19 else _norm(label.answer)
            if not prediction.abstained and prediction.answer == expected:
                counts["exact_matches"] += 1
            else:
                counts["mismatches"].append({
                    "query_id": query.query_id,
                    "gold": label.answer,
                    "prediction": prediction.answer,
                    "abstained": prediction.abstained,
                    "reason": prediction.reason,
                })
    counts["exact_match_rate"] = (
        counts["exact_matches"] / counts["queries"] if counts["queries"] else 0.0
    )
    return counts
