"""Temporal predicates for relation events."""
from __future__ import annotations
import math
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .graph import RelationEvent

def is_valid_at(event: "RelationEvent", time: float) -> bool:
    """Whether an event is in force at time (half-open expiry interval)."""
    if not math.isfinite(time):
        raise ValueError("time must be finite")
    if time < event.timestamp:
        return False
    return event.valid_until is None or time < event.valid_until
