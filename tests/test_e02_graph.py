from dataclasses import dataclass

import pytest

from rgm.graph import ObservedEventGraph


@dataclass(frozen=True)
class Event:
    relation: int
    subject: int
    object: int
    dt: float


def test_duplicate_observations_update_one_typed_edge():
    graph = ObservedEventGraph.from_events([
        Event(0, 1, 2, 1.0),
        Event(0, 1, 2, 2.0),
        Event(1, 1, 2, 3.0),
    ])
    assert graph.stats.event_count == 3
    assert graph.stats.unique_edge_count == 2
    assert graph.stats.duplicate_event_count == 1
    edge = graph.edge(0, 1, 2)
    assert edge is not None
    assert edge.count == 2
    assert edge.first_seen == 1.0
    assert edge.last_seen == 3.0
    assert edge.first_event_index == 0
    assert edge.last_event_index == 1
    assert graph.contains(1, 1, 2)


def test_edges_are_directed_and_relation_typed():
    graph = ObservedEventGraph.from_events([
        Event(0, 1, 2, 0.5),
        Event(0, 2, 1, 0.5),
        Event(1, 1, 2, 0.5),
    ])
    assert graph.contains(0, 1, 2)
    assert graph.contains(0, 2, 1)
    assert graph.contains(1, 1, 2)
    assert len(graph.edges) == 3


def test_outgoing_is_stable_and_relation_filterable():
    graph = ObservedEventGraph.from_events([
        Event(1, 4, 8, 1),
        Event(0, 4, 7, 1),
        Event(0, 4, 6, 1),
    ])
    assert [(e.key.relation, e.key.object) for e in graph.outgoing(4)] == [
        (0, 6), (0, 7), (1, 8)
    ]
    assert [e.key.object for e in graph.outgoing(4, relation=0)] == [6, 7]


def test_event_sequence_is_retained_in_cumulative_time_and_indices():
    graph = ObservedEventGraph.from_events([
        Event(0, 0, 1, 2.0),
        Event(0, 0, 2, 4.0),
        Event(0, 0, 1, 1.0),
    ])
    edge = graph.edge(0, 0, 1)
    assert edge is not None
    assert edge.first_seen == 2.0
    assert edge.last_seen == 7.0
    assert edge.first_event_index == 0
    assert edge.last_event_index == 2


def test_graph_depends_only_on_the_event_stream():
    # Evaluator metadata is deliberately held outside the builder interface.
    events = [Event(0, 1, 3, 1.0), Event(1, 3, 5, 2.0)]
    graph_a = ObservedEventGraph.from_events(events)
    evaluator_facts_a = {(0, 1, 3), (1, 3, 5)}
    evaluator_facts_b = {(0, 1, 3), (1, 3, 5), (0, 1, 5)}
    evaluator_label_a, evaluator_label_b = 1, 0
    graph_b = ObservedEventGraph.from_events(events)
    assert graph_a.to_dict() == graph_b.to_dict()
    assert evaluator_facts_a != evaluator_facts_b
    assert evaluator_label_a != evaluator_label_b
    assert not graph_a.contains(0, 1, 5)


@pytest.mark.parametrize("bad", [-1, 1.5, True])
def test_identifiers_must_be_nonnegative_integers(bad):
    graph = ObservedEventGraph()
    with pytest.raises(ValueError):
        graph.add_event(relation=0, subject=bad, object=1, dt=1.0)


@pytest.mark.parametrize("bad_dt", [-1.0, float("nan"), float("inf"), "not-time"])
def test_elapsed_time_must_be_finite_and_nonnegative(bad_dt):
    graph = ObservedEventGraph()
    with pytest.raises(ValueError):
        graph.add_event(relation=0, subject=1, object=2, dt=bad_dt)


def test_empty_stream_produces_empty_graph():
    graph = ObservedEventGraph.from_events([])
    assert graph.stats.event_count == 0
    assert graph.stats.unique_edge_count == 0
    assert graph.stats.node_count == 0
    assert graph.to_dict()["edges"] == []
