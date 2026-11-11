"""Schema-governed relation algebra operations."""
from __future__ import annotations
from .graph import RelationEvent
from .schema import RelationSchema

def reverse_relation(event: RelationEvent, schema: RelationSchema) -> RelationEvent:
    """Reverse endpoints only when an inverse predicate is explicitly declared."""
    inverse = schema.inverse_of(event.predicate)
    return RelationEvent(
        subject=event.object, predicate=inverse, object=event.subject,
        timestamp=event.timestamp, valid_until=event.valid_until,
        event_id=f"{event.event_id}:inverse" if event.event_id else None,
    )

def compose_relations(
    first: RelationEvent, second: RelationEvent, schema: RelationSchema,
    *, timestamp: float | None = None,
) -> RelationEvent:
    """Compose a connected pair using an explicit predicate-composition rule."""
    if first.object != second.subject:
        raise ValueError("relations are not composable: first object must equal second subject")
    if timestamp is None:
        timestamp = max(first.timestamp, second.timestamp)
    if timestamp < max(first.timestamp, second.timestamp):
        raise ValueError("composition time cannot precede either input event")
    predicate = schema.composition_of(first.predicate, second.predicate)
    expiries = [value for value in (first.valid_until, second.valid_until) if value is not None]
    valid_until = min(expiries) if expiries else None
    if valid_until is not None and timestamp >= valid_until:
        raise ValueError("composed relation is not temporally valid at the requested time")
    return RelationEvent(
        subject=first.subject, predicate=predicate, object=second.object,
        timestamp=timestamp, valid_until=valid_until,
    )
