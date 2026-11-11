import pytest
from rgm.relations import RelationEvent, RelationSchema, RelationalGraph
from rgm.relations.operations import compose_relations, reverse_relation

@pytest.fixture
def schema():
    return RelationSchema(
        inverses={"contains": "contained_by", "contained_by": "contains"},
        compositions={("acquires", "contains"): "acquires_component"},
        functional_predicates=frozenset({"located_at"}),
    )

def test_insert_and_temporal_validity(schema):
    graph = RelationalGraph(schema)
    event = graph.add("A", "located_at", "B", 1.0, valid_until=4.0, event_id="e1")
    assert graph.active_at(0.5) == ()
    assert graph.active_at(2.0) == (event,)
    assert graph.active_at(4.0) == ()

def test_revision_appends_new_event_and_hides_old_after_revision(schema):
    graph = RelationalGraph(schema)
    original = graph.add("A", "located_at", "B", 1.0, event_id="old")
    revised = graph.revise("old", new_object="C", timestamp=2.0, new_event_id="new")
    assert graph.events == (original, revised)
    assert revised.supersedes == "old"
    assert graph.active_at(1.5) == (original,)
    assert graph.active_at(2.5) == (revised,)

def test_functional_conflict_detection_is_schema_scoped(schema):
    graph = RelationalGraph(schema)
    graph.add("A", "located_at", "B", 0.0, event_id="a")
    graph.add("A", "located_at", "C", 0.0, event_id="b")
    graph.add("A", "likes", "D", 0.0, event_id="c")
    assert len(graph.find_contradictions(1.0)) == 1

def test_valid_inverse_requires_explicit_schema_rule(schema):
    event = RelationEvent("B", "contains", "C", 2.0)
    reversed_event = reverse_relation(event, schema)
    assert (reversed_event.subject, reversed_event.predicate, reversed_event.object) == ("C", "contained_by", "B")
    with pytest.raises(ValueError, match="no inverse semantics"):
        reverse_relation(RelationEvent("A", "unknown", "B", 0.0), schema)

def test_composition_requires_connectivity_and_explicit_rule(schema):
    first = RelationEvent("A", "acquires", "B", 1.0)
    second = RelationEvent("B", "contains", "C", 1.5)
    combined = compose_relations(first, second, schema)
    assert (combined.subject, combined.predicate, combined.object) == ("A", "acquires_component", "C")
    with pytest.raises(ValueError, match="not composable"):
        compose_relations(first, RelationEvent("X", "contains", "C", 1.5), schema)
    with pytest.raises(ValueError, match="no composition rule"):
        compose_relations(first, RelationEvent("B", "unknown", "C", 1.5), schema)

def test_invalid_events_and_duplicate_ids_are_rejected(schema):
    with pytest.raises(ValueError):
        RelationEvent("A", "r", "B", float("nan"))
    graph = RelationalGraph(schema)
    graph.add("A", "r", "B", 0.0, event_id="same")
    with pytest.raises(ValueError, match="duplicate"):
        graph.add("A", "r", "C", 1.0, event_id="same")

def test_expired_relation_is_not_returned_as_active_after_expiry(schema):
    graph = RelationalGraph(schema)
    graph.add("A", "located_at", "B", 1.0, valid_until=3.0, event_id="limited")
    assert len(graph.find_contradictions(2.0)) == 0
    assert graph.active_at(3.0) == ()

def test_revision_requires_existing_event_and_later_timestamp(schema):
    graph = RelationalGraph(schema)
    graph.add("A", "located_at", "B", 2.0, event_id="e1")
    with pytest.raises(KeyError):
        graph.revise("missing", new_object="C", timestamp=3.0)
    with pytest.raises(ValueError, match="later"):
        graph.revise("e1", new_object="C", timestamp=2.0)


def test_revision_without_explicit_id_generates_stable_unique_id(schema):
    graph = RelationalGraph(schema)
    graph.add("A", "located_at", "B", 1.0, event_id="original")
    revised = graph.revise("original", new_object="C", timestamp=2.0)
    assert revised.event_id == "original:revision:2"
    assert graph.active_at(3.0) == (revised,)
