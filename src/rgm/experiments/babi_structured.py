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
        if self.event_time < 0 or self.observed_at < self.event_time:
            raise ValueError("invalid event/observation ordering")

    def role_map(self) -> dict[str, str]:
        return dict(self.roles)


def _role(event: StructuredEvent, name: str) -> str:
    try:
        return event.role_map()[name]
    except KeyError as exc:
        raise ValueError(f"{event.event_type} event lacks required role {name!r}") from exc


def task3_object_location_before_move(
    events: Sequence[StructuredEvent], *, object_id: str,
    actor_id: str, destination_id: str, observation_cutoff: int,
) -> str | None:
    """Resolve an object's location immediately before a matching MOVE event."""
    ordered = sorted(events, key=lambda e: (e.event_time, e.event_id))
    if len({e.event_id for e in ordered}) != len(ordered):
        raise ValueError("event IDs must be unique")
    actor_location: dict[str, str] = {}
    object_location: dict[str, str] = {}
    held_by: dict[str, str] = {}
    for event in ordered:
        if event.observed_at > observation_cutoff:
            continue
        roles = event.role_map()
        if event.event_type == "MOVE":
            actor = _role(event, "actor")
            destination = _role(event, "destination")
            if actor == actor_id and destination == destination_id:
                holder = held_by.get(object_id)
                return actor_location.get(holder) if holder else object_location.get(object_id)
            actor_location[actor] = destination
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
    return None


def task5_answer_role(
    events: Sequence[StructuredEvent], *, bound_roles: Mapping[str, str],
    answer_role: str, observation_cutoff: int,
) -> tuple[str, ...]:
    """Return role values only from a single matching n-ary GIVE event."""
    if not bound_roles or answer_role in bound_roles:
        raise ValueError("bound roles must be non-empty and exclude answer_role")
    answers = set()
    for event in events:
        if event.event_type != "GIVE" or event.observed_at > observation_cutoff:
            continue
        roles = event.role_map()
        if all(roles.get(role) == value for role, value in bound_roles.items()):
            if answer_role not in roles:
                raise ValueError(f"GIVE event lacks answer role {answer_role!r}")
            answers.add(roles[answer_role])
    return tuple(sorted(answers))
