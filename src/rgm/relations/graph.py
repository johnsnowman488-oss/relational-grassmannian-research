"""Append-only event store for explicit typed directed relations."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable
import math
from .schema import RelationSchema
from .temporal import is_valid_at

@dataclass(frozen=True)
class RelationEvent:
    """One asserted relation event; revisions are represented by new events."""
    subject: str
    predicate: str
    object: str
    timestamp: float
    valid_until: float | None = None
    event_id: str | None = None
    supersedes: str | None = None

    def __post_init__(self) -> None:
        if not self.subject or not self.predicate or not self.object:
            raise ValueError("subject, predicate, and object must be non-empty")
        if not math.isfinite(self.timestamp) or self.timestamp < 0:
            raise ValueError("timestamp must be finite and non-negative")
        if self.valid_until is not None and (
            not math.isfinite(self.valid_until) or self.valid_until <= self.timestamp
        ):
            raise ValueError("valid_until must be finite and greater than timestamp")

class RelationalGraph:
    """Small append-only relation event store with explicit schema semantics."""
    def __init__(self, schema: RelationSchema | None = None) -> None:
        self.schema = schema or RelationSchema()
        self._events: list[RelationEvent] = []
        self._ids: set[str] = set()

    @property
    def events(self) -> tuple[RelationEvent, ...]:
        return tuple(self._events)

    def insert(self, event: RelationEvent) -> RelationEvent:
        if event.event_id is not None and event.event_id in self._ids:
            raise ValueError(f"duplicate event_id: {event.event_id}")
        if event.supersedes is not None and event.supersedes not in self._ids:
            raise ValueError(f"superseded event not found: {event.supersedes}")
        self._events.append(event)
        if event.event_id is not None:
            self._ids.add(event.event_id)
        return event

    def add(
        self, subject: str, predicate: str, object: str, timestamp: float,
        *, valid_until: float | None = None, event_id: str | None = None,
    ) -> RelationEvent:
        return self.insert(RelationEvent(subject, predicate, object, timestamp, valid_until, event_id))

    def revise(
        self, event_id: str, *, new_object: str, timestamp: float,
        new_event_id: str | None = None,
    ) -> RelationEvent:
        """Append a replacement assertion while retaining the original event."""
        prior = next((event for event in self._events if event.event_id == event_id), None)
        if prior is None:
            raise KeyError(f"unknown event_id: {event_id}")
        if timestamp <= prior.timestamp:
            raise ValueError("revision timestamp must be later than the original event")
        event = RelationEvent(
            subject=prior.subject, predicate=prior.predicate, object=new_object,
            timestamp=timestamp, event_id=new_event_id, supersedes=event_id,
        )
        return self.insert(event)

    def active_at(self, time: float) -> tuple[RelationEvent, ...]:
        if not math.isfinite(time) or time < 0:
            raise ValueError("time must be finite and non-negative")
        valid = [event for event in self._events if is_valid_at(event, time)]
        superseded = {event.supersedes for event in valid if event.supersedes is not None}
        return tuple(event for event in valid if event.event_id not in superseded)

    def find_contradictions(self, time: float) -> tuple[tuple[RelationEvent, RelationEvent], ...]:
        """Find simultaneous conflicting values for declared functional predicates."""
        active = [
            event for event in self.active_at(time)
            if event.predicate in self.schema.functional_predicates
        ]
        conflicts: list[tuple[RelationEvent, RelationEvent]] = []
        for left, right in combinations(active, 2):
            if left.subject == right.subject and left.predicate == right.predicate and left.object != right.object:
                conflicts.append((left, right))
        return tuple(conflicts)

    def by_subject(self, subject: str, *, at_time: float | None = None) -> tuple[RelationEvent, ...]:
        events: Iterable[RelationEvent] = self._events if at_time is None else self.active_at(at_time)
        return tuple(event for event in events if event.subject == subject)
