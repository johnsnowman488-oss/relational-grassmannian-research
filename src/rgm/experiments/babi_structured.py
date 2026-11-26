"""Oracle structured-event adapters for bAbI Tasks 3 and 5.

These functions intentionally accept typed events, not story text. They validate
the event representation and provide deterministic reference answers; they are
not a natural-language parser and their results are not benchmark scores.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence
import math


@dataclass(frozen=True)
class StructuredEvent:
    event_id: str
    event_type: str
    roles: tuple[tuple[str, str], ...]
    event_time: int
    observed_at: int
    source_ref: str

    def __post_init__(self) -> None:
        if not self.event_id or not self.event_type or not self.source_ref:
            raise ValueError("event identity, type and source reference are required")
        names = [name for name, value in self.roles]
        if not self.roles or any(not name or not value for name, value in self.roles):
            raise ValueError("event roles and values must be non-empty")
        if len(names) != len(set(names)):
            raise ValueError("role names must be unique within an event")
        required_roles = {
            "MOVE": {"actor", "destination"},
            "PICK_UP": {"actor", "object"},
            "DROP": {"actor", "object"},
            "GIVE": {"giver", "object", "recipient"},
        }
        if self.event_type not in required_roles:
            raise ValueError(f"unsupported structured event type {self.event_type!r}")
        actual_roles = set(names)
        required = required_roles[self.event_type]
        allowed = required | ({"location"} if self.event_type in {"PICK_UP", "DROP"} else set())
        if not required.issubset(actual_roles) or not actual_roles.issubset(allowed):
            raise ValueError(f"{self.event_type} event roles must be {sorted(required)}"
                             + (" with optional location" if "location" in allowed else ""))
        if self.event_time < 0 or self.observed_at < self.event_time:
            raise ValueError("invalid event/observation ordering")

    def role_map(self) -> dict[str, str]:
        return dict(self.roles)


@dataclass(frozen=True)
class StructuredQuery:
    """Input-only query annotation; deliberately contains no answer/support labels."""
    query_id: str
    story_id: str
    task_id: int
    query_type: str
    answer_role: str
    observed_at: int
    source_ref: str
    object_id: str | None = None
    destination_id: str | None = None
    target_event_id: str | None = None
    bound_roles: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not all((self.query_id, self.story_id, self.query_type, self.answer_role, self.source_ref)):
            raise ValueError("query identity, type, answer role and provenance are required")
        if self.task_id not in (3, 5) or self.observed_at < 0:
            raise ValueError("unsupported task ID or negative query observation time")
        role_names = [name for name, value in self.bound_roles]
        if any(not name or not value for name, value in self.bound_roles):
            raise ValueError("bound query roles and values must be non-empty")
        if len(role_names) != len(set(role_names)):
            raise ValueError("bound query roles must be unique")
        if self.task_id == 3:
            if self.query_type != "OBJECT_LOCATION_BEFORE_MOVE":
                raise ValueError("Task 3 requires OBJECT_LOCATION_BEFORE_MOVE")
            if not all((self.object_id, self.destination_id, self.target_event_id)):
                raise ValueError("Task 3 query requires object, destination and target event")
            if self.answer_role != "location" or self.bound_roles:
                raise ValueError("Task 3 query answer role is location and has no bound GIVE roles")
        else:
            if self.query_type != "GIVE_ROLE":
                raise ValueError("Task 5 requires GIVE_ROLE")
            if self.object_id or self.destination_id or self.target_event_id:
                raise ValueError("Task 5 queries do not use Task 3 movement anchors")
            if not self.bound_roles or self.answer_role not in {"giver", "object", "recipient"}:
                raise ValueError("Task 5 requires bound GIVE roles and a valid answer role")
            if not set(role_names).issubset({"giver", "object", "recipient"}):
                raise ValueError("Task 5 bound roles must be GIVE roles")
            if self.answer_role in role_names:
                raise ValueError("answer role cannot also be supplied as a bound role")


@dataclass(frozen=True)
class StructuredStory:
    """A story-scoped collection of structured inputs without gold answers/witnesses."""
    story_id: str
    events: tuple[StructuredEvent, ...]
    queries: tuple[StructuredQuery, ...]

    def __post_init__(self) -> None:
        if not self.story_id:
            raise ValueError("story identity is required")
        event_ids = [event.event_id for event in self.events]
        query_ids = [query.query_id for query in self.queries]
        if len(event_ids) != len(set(event_ids)) or len(query_ids) != len(set(query_ids)):
            raise ValueError("event and query IDs must be unique within a story")
        if any(not event_id.startswith(self.story_id + ":") for event_id in event_ids):
            raise ValueError("event IDs must be story-scoped source-line identities")
        if any(not query_id.startswith(self.story_id + ":") for query_id in query_ids):
            raise ValueError("query IDs must be story-scoped source-line identities")
        if any(query.story_id != self.story_id for query in self.queries):
            raise ValueError("query story identity does not match containing story")
        if any(query.target_event_id is not None and query.target_event_id not in set(event_ids)
               for query in self.queries):
            raise ValueError("query target event is not present in the story")


def _role(event: StructuredEvent, name: str) -> str:
    try:
        return event.role_map()[name]
    except KeyError as exc:
        raise ValueError(f"{event.event_type} event lacks required role {name!r}") from exc


def task3_object_location_before_move(
    events: Sequence[StructuredEvent], *, object_id: str,
    destination_id: str, target_event_id: str, observation_cutoff: int,
) -> str | None:
    """Resolve an object's location immediately before one explicitly anchored MOVE."""
    ordered = sorted(events, key=lambda e: (e.event_time, e.event_id))
    by_id = {event.event_id: event for event in ordered}
    if len(by_id) != len(ordered):
        raise ValueError("event IDs must be unique within a story")
    if target_event_id not in by_id:
        raise KeyError(f"unknown target movement event {target_event_id!r}")
    target = by_id[target_event_id]
    if target.event_type != "MOVE" or _role(target, "destination") != destination_id:
        raise ValueError("target event must be a MOVE to the queried destination")
    if target.observed_at > observation_cutoff:
        return None

    actor_id = _role(target, "actor")
    target_key = (target.event_time, target.event_id)
    actor_location: dict[str, str] = {}
    object_location: dict[str, str] = {}
    held_by: dict[str, str] = {}
    for event in ordered:
        if (event.event_time, event.event_id) >= target_key:
            break
        if event.observed_at > observation_cutoff:
            continue
        roles = event.role_map()
        if event.event_type == "MOVE":
            actor = _role(event, "actor")
            actor_location[actor] = _role(event, "destination")
        elif event.event_type == "PICK_UP":
            actor, obj = _role(event, "actor"), _role(event, "object")
            pickup_location = roles.get("location")
            if pickup_location:
                actor_location.setdefault(actor, pickup_location)
            held_by[obj] = actor
            object_location.pop(obj, None)
        elif event.event_type == "DROP":
            actor, obj = _role(event, "actor"), _role(event, "object")
            held_by.pop(obj, None)
            drop_location = roles.get("location") or actor_location.get(actor)
            if drop_location:
                object_location[obj] = drop_location

    holder = held_by.get(object_id)
    if holder:
        return actor_location.get(holder)
    return object_location.get(object_id)

def task5_answer_role(
    events: Sequence[StructuredEvent], *, bound_roles: Mapping[str, str],
    answer_role: str, observation_cutoff: int,
) -> tuple[str, ...]:
    """Answer from the most recent single GIVE event matching all bound roles."""
    if not bound_roles or answer_role in bound_roles:
        raise ValueError("bound roles must be non-empty and exclude answer_role")
    event_ids = [event.event_id for event in events]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("event IDs must be unique within a story")
    matches = []
    for event in events:
        if event.event_type != "GIVE" or event.observed_at > observation_cutoff:
            continue
        roles = event.role_map()
        if all(roles.get(role) == value for role, value in bound_roles.items()):
            if answer_role not in roles:
                raise ValueError(f"GIVE event lacks answer role {answer_role!r}")
            matches.append(event)
    if not matches:
        return ()
    latest = max(matches, key=lambda event: (event.event_time, event.event_id))
    return (_role(latest, answer_role),)
