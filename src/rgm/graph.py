"""Event-derived directed typed graph primitives for E02.

The builder accepts only an ordered iterable of observed events. It has no
interface for latent facts, labels, planted paths, or evaluator metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Protocol


class EventLike(Protocol):
    relation: int
    subject: int
    object: int
    dt: float


@dataclass(frozen=True, order=True)
class EdgeKey:
    relation: int
    subject: int
    object: int


@dataclass(frozen=True)
class EdgeRecord:
    key: EdgeKey
    count: int
    first_seen: float
    last_seen: float
    first_event_index: int
    last_event_index: int


@dataclass(frozen=True)
class GraphStats:
    event_count: int
    unique_edge_count: int
    duplicate_event_count: int
    node_count: int


class ObservedEventGraph:
    """Directed, typed graph containing only edges observed in an event stream."""

    def __init__(self) -> None:
        self._edges: dict[EdgeKey, EdgeRecord] = {}
        self._nodes: set[int] = set()
        self._event_count = 0
        self._elapsed = 0.0

    @classmethod
    def from_events(cls, events: Iterable[EventLike]) -> "ObservedEventGraph":
        graph = cls()
        for event in events:
            graph.add_event(
                relation=event.relation,
                subject=event.subject,
                object=event.object,
                dt=event.dt,
            )
        return graph

    def add_event(self, *, relation: int, subject: int, object: int, dt: float) -> None:
        """Ingest one observation; no ground-truth or query arguments are accepted."""
        for name, value in (("relation", relation), ("subject", subject), ("object", object)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        try:
            delta = float(dt)
        except (TypeError, ValueError) as exc:
            raise ValueError("dt must be a finite non-negative number") from exc
        if not math.isfinite(delta) or delta < 0:
            raise ValueError("dt must be a finite non-negative number")

        self._elapsed += delta
        key = EdgeKey(relation, subject, object)
        previous = self._edges.get(key)
        index = self._event_count
        if previous is None:
            self._edges[key] = EdgeRecord(
                key=key, count=1, first_seen=self._elapsed, last_seen=self._elapsed,
                first_event_index=index, last_event_index=index,
            )
        else:
            self._edges[key] = EdgeRecord(
                key=key, count=previous.count + 1,
                first_seen=previous.first_seen, last_seen=self._elapsed,
                first_event_index=previous.first_event_index, last_event_index=index,
            )
        self._nodes.update((subject, object))
        self._event_count += 1

    def contains(self, relation: int, subject: int, object: int) -> bool:
        return EdgeKey(relation, subject, object) in self._edges

    def edge(self, relation: int, subject: int, object: int) -> EdgeRecord | None:
        return self._edges.get(EdgeKey(relation, subject, object))

    def outgoing(self, subject: int, relation: int | None = None) -> tuple[EdgeRecord, ...]:
        records = [
            record for key, record in self._edges.items()
            if key.subject == subject and (relation is None or key.relation == relation)
        ]
        return tuple(sorted(records, key=lambda record: record.key))

    @property
    def stats(self) -> GraphStats:
        return GraphStats(
            event_count=self._event_count,
            unique_edge_count=len(self._edges),
            duplicate_event_count=self._event_count - len(self._edges),
            node_count=len(self._nodes),
        )

    @property
    def edges(self) -> tuple[EdgeRecord, ...]:
        return tuple(self._edges[key] for key in sorted(self._edges))

    def to_dict(self) -> dict[str, object]:
        """Canonical JSON-compatible representation for hashing and accounting."""
        return {
            "schema_version": 1,
            "stats": {
                "event_count": self.stats.event_count,
                "unique_edge_count": self.stats.unique_edge_count,
                "duplicate_event_count": self.stats.duplicate_event_count,
                "node_count": self.stats.node_count,
            },
            "edges": [
                {
                    "relation": record.key.relation,
                    "subject": record.key.subject,
                    "object": record.key.object,
                    "count": record.count,
                    "first_seen": record.first_seen,
                    "last_seen": record.last_seen,
                    "first_event_index": record.first_event_index,
                    "last_event_index": record.last_event_index,
                }
                for record in self.edges
            ],
        }
