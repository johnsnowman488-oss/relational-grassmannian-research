"""Evidence lifecycle primitives for HLG: immutable n-ary events, summaries and witness recovery.

This module is deliberately independent of HLA/HLB policy. HLA can use the
validator/recovery API with caller-supplied records; HLB can own a bounded
EvidenceStore. It does not modify the native SOE runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence
import hashlib
import json
import math


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, order=True)
class Participant:
    role: str
    entity_id: str
    entity_type: str

    def __post_init__(self) -> None:
        if not all((self.role, self.entity_id, self.entity_type)):
            raise ValueError("participant role and entity identity/type must be non-empty")


@dataclass(frozen=True)
class NaryEvent:
    """One event identity binds all participant roles and source metadata."""
    event_id: str
    event_type: str
    participants: tuple[Participant, ...]
    event_time: float
    observed_at: float
    provenance: str
    source_locator: str
    payload_digest: str
    context: str | None = None
    valid_until: float | None = None
    revision_of: str | None = None

    def __post_init__(self) -> None:
        if not all((self.event_id, self.event_type, self.provenance,
                    self.source_locator, self.payload_digest)):
            raise ValueError("event identity, type, provenance, locator and digest are required")
        if len(self.participants) < 2:
            raise ValueError("n-ary event requires at least two participants")
        roles = [p.role for p in self.participants]
        if len(roles) != len(set(roles)):
            raise ValueError("participant roles must be unique within an event")
        if not math.isfinite(self.event_time) or not math.isfinite(self.observed_at):
            raise ValueError("event and observation times must be finite")
        if self.event_time < 0 or self.observed_at < self.event_time:
            raise ValueError("observed_at cannot precede event_time")
        if self.valid_until is not None and (
            not math.isfinite(self.valid_until) or self.valid_until <= self.event_time
        ):
            raise ValueError("valid_until must be later than event_time")
        if len(self.payload_digest) != 64 or any(c not in "0123456789abcdef" for c in self.payload_digest):
            raise ValueError("payload_digest must be a lowercase SHA-256 hex digest")

    def role(self, name: str) -> Participant:
        matches = [p for p in self.participants if p.role == name]
        if len(matches) != 1:
            raise KeyError(f"event {self.event_id!r} has no unique role {name!r}")
        return matches[0]

    def canonical(self) -> dict:
        return {
            "event_id": self.event_id, "event_type": self.event_type,
            "participants": [p.__dict__ for p in self.participants],
            "event_time": self.event_time, "observed_at": self.observed_at,
            "provenance": self.provenance, "source_locator": self.source_locator,
            "payload_digest": self.payload_digest, "context": self.context,
            "valid_until": self.valid_until, "revision_of": self.revision_of,
        }


@dataclass(frozen=True)
class EvidenceSummary:
    summary_id: str
    level: int
    text: str
    source_ids: tuple[str, ...]
    source_digest: str
    created_at: float

    def __post_init__(self) -> None:
        if not self.summary_id or not self.text or not self.source_ids:
            raise ValueError("summary requires identity, text and source references")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("summary source references must be unique")
        if self.level not in (0, 1, 2) or not math.isfinite(self.created_at):
            raise ValueError("invalid summary level or timestamp")


@dataclass(frozen=True)
class DerivedEvidence:
    derivation_id: str
    level: int
    rule_fingerprint: str
    witness_ids: tuple[str, ...]
    conclusion: str
    created_at: float

    def __post_init__(self) -> None:
        if not self.derivation_id or not self.rule_fingerprint or not self.witness_ids or not self.conclusion:
            raise ValueError("derivation requires identity, rule, witnesses and conclusion")
        if len(set(self.witness_ids)) != len(self.witness_ids):
            raise ValueError("derivation witness IDs must be unique")
        if self.level not in (0, 1, 2) or not math.isfinite(self.created_at):
            raise ValueError("invalid derivation level or timestamp")


class EvidenceStore:
    """Append-only source journal plus bounded indexes and resolvable summaries.

    Capacity applies to source event records. When full, insertion returns an
    explicit abstention and never evicts protected source evidence.
    """
    def __init__(self, capacity: int = 10000) -> None:
        if isinstance(capacity, bool) or capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = int(capacity)
        self._events: dict[str, NaryEvent] = {}
        self._summaries: dict[str, EvidenceSummary] = {}
        self._derivations: dict[str, DerivedEvidence] = {}
        self._event_order: list[str] = []

    @property
    def count(self) -> int:
        return len(self._events)

    @property
    def event_ids(self) -> tuple[str, ...]:
        return tuple(self._event_order)

    def append(self, event: NaryEvent) -> str:
        prior = self._events.get(event.event_id)
        if prior is not None:
            if prior != event:
                raise ValueError("immutable evidence ID collision")
            return "ALREADY_STORED"
        if event.revision_of is not None and event.revision_of not in self._events:
            raise KeyError("revision target is not retained")
        if len(self._events) >= self.capacity:
            return "ABSTAIN_CAPACITY"
        self._events[event.event_id] = event
        self._event_order.append(event.event_id)
        return "STORED"

    def append_summary(self, summary: EvidenceSummary) -> str:
        if summary.summary_id in self._summaries:
            if self._summaries[summary.summary_id] != summary:
                raise ValueError("summary ID collision")
            return "ALREADY_STORED"
        if any(source not in self._events and source not in self._derivations
               for source in summary.source_ids):
            raise KeyError("summary references missing evidence")
        expected = _digest([self._events[s].canonical() if s in self._events
                            else self._derivations[s].__dict__ for s in summary.source_ids])
        if summary.source_digest != expected:
            raise ValueError("summary source digest mismatch")
        self._summaries[summary.summary_id] = summary
        return "STORED"

    def append_derivation(self, item: DerivedEvidence) -> str:
        if item.derivation_id in self._derivations:
            if self._derivations[item.derivation_id] != item:
                raise ValueError("derivation ID collision")
            return "ALREADY_STORED"
        if any(w not in self._events and w not in self._derivations for w in item.witness_ids):
            raise KeyError("derivation witness is missing")
        self._derivations[item.derivation_id] = item
        return "STORED"

    def get_event(self, event_id: str, *, observation_cutoff: float | None = None) -> NaryEvent:
        event = self._events[event_id]
        if observation_cutoff is not None and event.observed_at > observation_cutoff:
            raise PermissionError("evidence was observed after the requested cutoff")
        return event

    def recover(self, evidence_id: str, *, observation_cutoff: float,
                _seen: set[str] | None = None) -> tuple[NaryEvent, ...]:
        """Resolve a source/derived/summary reference to exact source events."""
        if not math.isfinite(observation_cutoff):
            raise ValueError("observation cutoff must be finite")
        seen = set() if _seen is None else _seen
        if evidence_id in seen:
            raise ValueError("cyclic evidence reference")
        seen.add(evidence_id)
        try:
            if evidence_id in self._events:
                event = self._events[evidence_id]
                if event.observed_at > observation_cutoff:
                    raise PermissionError("source evidence is beyond observation cutoff")
                return (event,)
            if evidence_id in self._derivations:
                item = self._derivations[evidence_id]
                out = []
                for witness in item.witness_ids:
                    out.extend(self.recover(witness, observation_cutoff=observation_cutoff, _seen=seen))
                return tuple({e.event_id: e for e in out}[k] for k in sorted({e.event_id for e in out}))
            if evidence_id in self._summaries:
                summary = self._summaries[evidence_id]
                out = []
                for source in summary.source_ids:
                    out.extend(self.recover(source, observation_cutoff=observation_cutoff, _seen=seen))
                return tuple({e.event_id: e for e in out}[k] for k in sorted({e.event_id for e in out}))
            raise KeyError(f"unknown evidence reference: {evidence_id}")
        finally:
            seen.remove(evidence_id)

    def verify_provenance(self, event_id: str,
                          payload_loader: Callable[[str], bytes]) -> bool:
        event = self._events[event_id]
        payload = payload_loader(event.source_locator)
        return hashlib.sha256(payload).hexdigest() == event.payload_digest

    def contradictions(self, *, event_type: str, key_roles: Sequence[str],
                       value_role: str, observation_cutoff: float) -> tuple[tuple[str, str], ...]:
        """Find same-key, same-time-scope conflicting values without erasing either."""
        active = [e for e in self._events.values()
                  if e.event_type == event_type and e.observed_at <= observation_cutoff]
        conflicts = []
        for i, left in enumerate(active):
            for right in active[i + 1:]:
                if left.context != right.context:
                    continue
                if any(left.role(r).entity_id != right.role(r).entity_id for r in key_roles):
                    continue
                if left.role(value_role).entity_id == right.role(value_role).entity_id:
                    continue
                if left.revision_of == right.event_id or right.revision_of == left.event_id:
                    continue
                left_end = left.valid_until if left.valid_until is not None else math.inf
                right_end = right.valid_until if right.valid_until is not None else math.inf
                if max(left.event_time, right.event_time) < min(left_end, right_end):
                    conflicts.append((left.event_id, right.event_id))
        return tuple(sorted(conflicts))

    def snapshot(self) -> dict:
        return {
            "schema": "hlg-evidence-v1", "capacity": self.capacity,
            "events": [self._events[i].canonical() for i in self._event_order],
            "summaries": [s.__dict__ for s in self._summaries.values()],
            "derivations": [d.__dict__ for d in self._derivations.values()],
        }

    @classmethod
    def from_snapshot(cls, state: Mapping) -> "EvidenceStore":
        if state.get("schema") != "hlg-evidence-v1":
            raise ValueError("unsupported evidence snapshot schema")
        store = cls(int(state["capacity"]))
        for raw in state["events"]:
            event = NaryEvent(**{**raw, "participants": tuple(Participant(**p) for p in raw["participants"])})
            if store.append(event) != "STORED":
                raise ValueError("duplicate event in evidence snapshot")
        for raw in state.get("derivations", ()):
            item = DerivedEvidence(**{**raw, "witness_ids": tuple(raw["witness_ids"])})
            store.append_derivation(item)
        for raw in state.get("summaries", ()):
            item = EvidenceSummary(**{**raw, "source_ids": tuple(raw["source_ids"])})
            store.append_summary(item)
        return store
