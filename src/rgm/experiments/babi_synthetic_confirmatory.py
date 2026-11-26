"""Independent deterministic bAbI-compatible structured confirmatory generator.

The generated challenge is not an official bAbI test split. It is a separately
seeded structured-event holdout with novel entity identities. Inputs only are
written before candidate freeze; evaluator labels are derived only at G4.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
import hashlib
import json
import random

from rgm.experiments.babi_structured import StructuredEvent, StructuredQuery, StructuredStory

PEOPLE = (
    "amara", "belen", "cyrus", "daria", "elian", "farah",
    "galen", "hani", "imani", "jorin", "kiva", "lior",
)
OBJECTS = (
    "crystal", "compass", "lantern", "parcel", "camera", "tablet",
    "vial", "orchid", "telescope", "prism", "mosaic", "relic",
)
LOCATIONS = (
    "atrium", "observatory", "courtyard", "archive", "harbor", "studio",
    "loft", "workshop", "greenhouse", "gallery", "vault", "terrace",
)
TASK3_SEED = 953900
TASK5_SEED = 953901
STORIES_PER_TASK = 200
QUERIES_PER_STORY = 5


def _add_event(story_id: str, events: list[StructuredEvent], event_type: str,
               roles: dict[str, str]) -> StructuredEvent:
    tick = len(events) + 1
    event_id = f"{story_id}:event{tick:06d}"
    source_ref = f"synthetic://{story_id}/event/{tick:06d}"
    event = StructuredEvent(
        event_id, event_type, tuple(sorted(roles.items())),
        float(tick), float(tick), source_ref,
    )
    events.append(event)
    return event


def _task3_story(story_number: int, rng: random.Random) -> StructuredStory:
    story_id = f"task3/confirmatory/story{story_number:06d}"
    events: list[StructuredEvent] = []
    queries: list[StructuredQuery] = []
    objects = rng.sample(OBJECTS, QUERIES_PER_STORY)
    for q_index, object_id in enumerate(objects, start=1):
        actor = rng.choice(PEOPLE)
        decoy_actor = rng.choice([person for person in PEOPLE if person != actor])
        origin = rng.choice(LOCATIONS)
        destination = rng.choice([place for place in LOCATIONS if place != origin])
        decoy_location = rng.choice([place for place in LOCATIONS if place not in {origin, destination}])

        location_event = _add_event(story_id, events, "MOVE", {
            "actor": actor, "destination": origin,
        })
        _add_event(story_id, events, "MOVE", {
            "actor": decoy_actor, "destination": decoy_location,
        })
        pickup_event = _add_event(story_id, events, "PICK_UP", {
            "actor": actor, "object": object_id,
        })
        _add_event(story_id, events, "MOVE", {
            "actor": decoy_actor, "destination": destination,
        })
        target_move = _add_event(story_id, events, "MOVE", {
            "actor": actor, "destination": destination,
        })
        _add_event(story_id, events, "DROP", {
            "actor": actor, "object": object_id,
        })
        query_tick = len(events) + 1
        query_id = f"{story_id}:query{q_index:03d}"
        query = StructuredQuery(
            query_id, story_id, 3, "OBJECT_LOCATION_BEFORE_MOVE", "location",
            float(query_tick), f"synthetic://{story_id}/query/{q_index:03d}",
            object_id=object_id, destination_id=destination,
            target_event_id=target_move.event_id,
        )
        queries.append(query)
    return StructuredStory(story_id, tuple(events), tuple(queries))


def _task5_story(story_number: int, rng: random.Random) -> StructuredStory:
    story_id = f"task5/confirmatory/story{story_number:06d}"
    events: list[StructuredEvent] = []
    queries: list[StructuredQuery] = []
    objects = rng.sample(OBJECTS, QUERIES_PER_STORY)
    for q_index, object_id in enumerate(objects):
        giver, recipient = rng.sample(PEOPLE, 2)
        remaining = [person for person in PEOPLE if person not in {giver, recipient}]
        decoy_giver = rng.choice(remaining)
        decoy_recipient = rng.choice([person for person in remaining if person != decoy_giver])
        decoy_object = f"decoy_{object_id}"

        # Non-GIVE events are deliberate distractors and must remain in the story.
        decoy_actor = rng.choice(remaining)
        decoy_location = rng.choice(LOCATIONS)
        _add_event(story_id, events, "MOVE", {
            "actor": decoy_actor, "destination": decoy_location,
        })
        _add_event(story_id, events, "PICK_UP", {
            "actor": decoy_actor, "object": decoy_object,
        })
        _add_event(story_id, events, "DROP", {
            "actor": decoy_actor, "object": decoy_object,
        })

        # Each distractor agrees on one plausible subset of roles but not all
        # roles. The target event is the latest complete match for the query.
        _add_event(story_id, events, "GIVE", {
            "giver": decoy_giver, "object": object_id, "recipient": recipient,
        })
        _add_event(story_id, events, "GIVE", {
            "giver": giver, "object": object_id, "recipient": decoy_recipient,
        })
        _add_event(story_id, events, "GIVE", {
            "giver": giver, "object": decoy_object, "recipient": recipient,
        })
        target = _add_event(story_id, events, "GIVE", {
            "giver": giver, "object": object_id, "recipient": recipient,
        })

        query_specs = (
            ({"object": object_id, "recipient": recipient}, "giver"),
            ({"giver": giver, "object": object_id}, "recipient"),
            ({"giver": giver, "recipient": recipient}, "object"),
            ({"object": object_id}, "recipient"),
            ({"object": object_id}, "giver"),
        )
        bound_roles, answer_role = query_specs[q_index]
        query_tick = len(events) + 1
        query_id = f"{story_id}:query{q_index + 1:03d}"
        query = StructuredQuery(
            query_id, story_id, 5, "GIVE_ROLE", answer_role, float(query_tick),
            f"synthetic://{story_id}/query/{q_index + 1:03d}",
            bound_roles=tuple(sorted(bound_roles.items())),
        )
        queries.append(query)
    return StructuredStory(story_id, tuple(events), tuple(queries))


def _story_payload(story: StructuredStory) -> dict[str, Any]:
    return {
        "story_id": story.story_id,
        "task_id": story.queries[0].task_id,
        "events": [asdict(event) for event in story.events],
        "queries": [asdict(query) for query in story.queries],
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _official_entity_vocabulary(annotation_root: Path) -> set[str]:
    vocabulary: set[str] = set()
    for path in sorted(annotation_root.glob("task*-*.inputs.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            story = json.loads(line)
            for event in story["events"]:
                vocabulary.update(value for _, value in event["roles"])
            for query in story["queries"]:
                for key in ("object_id", "destination_id"):
                    if query.get(key):
                        vocabulary.add(query[key])
                vocabulary.update(value for _, value in query.get("bound_roles", ()))
    return vocabulary


def write_confirmatory_inputs(output_root: Path, annotation_root: Path) -> dict[str, Any]:
    """Write inputs and manifest only; do not emit or score confirmatory labels."""
    official_vocabulary = _official_entity_vocabulary(annotation_root)
    challenge_vocabulary = set(PEOPLE) | set(OBJECTS) | set(LOCATIONS) | {f"decoy_{obj}" for obj in OBJECTS}
    overlap = sorted(official_vocabulary & challenge_vocabulary)
    if overlap:
        raise ValueError(f"confirmatory entity vocabulary overlaps fit/validation: {overlap}")
    output_root.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": "HLG-BABI-SYNTHETIC-CONFIRMATORY-v1",
        "protocol_id": "HLG-BABI-T3-T5-LEARNING-v1.2",
        "generator": "deterministic structured-event generator; no text parser",
        "official_entity_vocabulary_overlap": overlap,
        "novel_entity_vocabulary": sorted(challenge_vocabulary),
        "stories_per_task": STORIES_PER_TASK,
        "queries_per_story": QUERIES_PER_STORY,
        "labels_emitted": False,
        "label_access": "deferred until G4; this G1 bundle contains inputs only",
        "tasks": {},
    }
    for task_id, seed in ((3, TASK3_SEED), (5, TASK5_SEED)):
        rng = random.Random(seed)
        input_path = output_root / f"task{task_id}-confirmatory.inputs.jsonl"
        rows = []
        story_fingerprints = []
        event_count = query_count = 0
        story_ids = set()
        for story_number in range(1, STORIES_PER_TASK + 1):
            story = (_task3_story(story_number, rng) if task_id == 3
                     else _task5_story(story_number, rng))
            if story.story_id in story_ids:
                raise ValueError(f"duplicate generated story ID: {story.story_id}")
            story_ids.add(story.story_id)
            payload = _story_payload(story)
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            rows.append(encoded)
            story_fingerprints.append(hashlib.sha256(encoded.encode("utf-8")).hexdigest())
            event_count += len(story.events)
            query_count += len(story.queries)
            if len(story.queries) != QUERIES_PER_STORY:
                raise ValueError(f"wrong query count in {story.story_id}")
            event_ids = {event.event_id for event in story.events}
            for query in story.queries:
                if query.target_event_id is not None and query.target_event_id not in event_ids:
                    raise ValueError(f"unresolved target movement in {query.query_id}")
                if query.answer_role in dict(query.bound_roles):
                    raise ValueError(f"answer role leaked into bound roles in {query.query_id}")
        if len(story_fingerprints) != len(set(story_fingerprints)):
            raise ValueError(f"duplicate structured stories in Task {task_id} confirmatory set")
        input_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        report["tasks"][str(task_id)] = {
            "seed": seed,
            "story_count": STORIES_PER_TASK,
            "event_count": event_count,
            "query_count": query_count,
            "input_path": str(input_path),
            "input_sha256": _sha256(input_path),
            "unique_story_fingerprints": len(set(story_fingerprints)),
            "story_fingerprint_set_sha256": hashlib.sha256(
                "\n".join(sorted(story_fingerprints)).encode("ascii")
            ).hexdigest(),
        }
    manifest_path = output_root / "confirmatory-input-manifest.json"
    manifest_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["manifest_sha256"] = _sha256(manifest_path)
    return report
