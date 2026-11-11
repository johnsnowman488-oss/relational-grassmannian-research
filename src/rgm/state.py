"""Serializable augmented research state joining E00 components."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .geometry import GrassmannianPoint
from .memory import SOEMemory
from .relations import RelationEvent, RelationSchema, RelationalGraph


@dataclass
class ResearchState:
    """Snapshot of observable, memory, relational, and geometric state.

    This is an interoperability and persistence boundary; it does not define a
    model update or a coupling law between its components. Observable state
    must be JSON-compatible so run snapshots are portable.
    """

    observable_state: dict[str, Any]
    memory: SOEMemory
    relations: RelationalGraph
    subspace: GrassmannianPoint
    step: int = 0
    time: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.observable_state, Mapping):
            raise ValueError("observable_state must be a mapping")
        if isinstance(self.step, bool) or not isinstance(self.step, int) or self.step < 0:
            raise ValueError("step must be a non-negative integer")
        if not math.isfinite(self.time) or self.time < 0.0:
            raise ValueError("time must be finite and non-negative")
        if self.memory.feature_dim != self.subspace.ambient_dim:
            raise ValueError("memory feature dimension must match Grassmannian ambient dimension")
        try:
            copied = json.loads(json.dumps(dict(self.observable_state), allow_nan=False))
        except (TypeError, ValueError) as exc:
            raise ValueError("observable_state must be JSON-compatible and finite") from exc
        self.observable_state = copied

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of the complete augmented state."""
        schema = self.relations.schema
        return {
            "format_version": 1,
            "step": self.step,
            "time": float(self.time),
            "observable_state": self.observable_state,
            "memory": self.memory.to_dict(),
            "relations": {
                "schema": {
                    "inverses": dict(schema.inverses),
                    "compositions": [
                        [left, right, result]
                        for (left, right), result in sorted(schema.compositions.items())
                    ],
                    "functional_predicates": sorted(schema.functional_predicates),
                },
                "events": [asdict(event) for event in self.relations.events],
            },
            "subspace": {"frame": self.subspace.frame.tolist()},
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize the complete state as portable JSON text."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, allow_nan=False)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchState":
        """Reconstruct a state from a prior to_dict snapshot."""
        if payload.get("format_version") != 1:
            raise ValueError("unsupported research-state format version")
        try:
            relation_payload = payload["relations"]
            schema_payload = relation_payload["schema"]
            compositions = {
                (str(left), str(right)): str(result)
                for left, right, result in schema_payload["compositions"]
            }
            schema = RelationSchema(
                inverses=dict(schema_payload["inverses"]),
                compositions=compositions,
                functional_predicates=frozenset(schema_payload["functional_predicates"]),
            )
            graph = RelationalGraph(schema)
            for event_data in relation_payload["events"]:
                graph.insert(RelationEvent(**event_data))
            memory = SOEMemory.from_dict(dict(payload["memory"]))
            subspace = GrassmannianPoint(payload["subspace"]["frame"])
            return cls(
                observable_state=dict(payload["observable_state"]),
                memory=memory,
                relations=graph,
                subspace=subspace,
                step=payload["step"],
                time=float(payload["time"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid research-state snapshot: {exc}") from exc

    @classmethod
    def from_json(cls, serialized: str) -> "ResearchState":
        """Deserialize a JSON state snapshot."""
        try:
            payload = json.loads(serialized)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("serialized state must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("serialized state must contain a JSON object")
        return cls.from_dict(payload)
