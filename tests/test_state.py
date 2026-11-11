import numpy as np
import pytest

from rgm.geometry import GrassmannianPoint
from rgm.memory import SOEMemory
from rgm.relations import RelationSchema, RelationalGraph
from rgm.state import ResearchState


def make_state():
    schema = RelationSchema(
        inverses={"contains": "contained_by"},
        compositions={("acquires", "contains"): "acquires_component"},
        functional_predicates=frozenset({"located_at"}),
    )
    graph = RelationalGraph(schema)
    graph.add("A", "located_at", "B", 0.5, event_id="evt-1")
    graph.add("B", "contains", "C", 0.75, valid_until=3.0, event_id="evt-2")
    memory = SOEMemory()
    memory.update(np.arange(16, dtype=float) / 10.0, dt=0.25)
    subspace = GrassmannianPoint.random(16, 4, seed=2026)
    return ResearchState(
        observable_state={"mode": "query", "active": True, "count": 2},
        memory=memory,
        relations=graph,
        subspace=subspace,
        step=7,
        time=1.25,
    )


def test_augmented_state_json_round_trip_preserves_every_component():
    state = make_state()
    restored = ResearchState.from_json(state.to_json())
    assert restored.observable_state == state.observable_state
    assert restored.step == state.step
    assert restored.time == state.time
    np.testing.assert_array_equal(restored.memory.channels, state.memory.channels)
    assert restored.memory.decay_rates.tolist() == state.memory.decay_rates.tolist()
    assert restored.relations.schema == state.relations.schema
    assert restored.relations.events == state.relations.events
    np.testing.assert_allclose(restored.subspace.projector, state.subspace.projector, atol=1e-12)


def test_restored_state_preserves_future_memory_trajectory():
    state = make_state()
    restored = ResearchState.from_dict(state.to_dict())
    feature = np.linspace(-1.0, 1.0, 16)
    np.testing.assert_array_equal(
        state.memory.update(feature, dt=0.4),
        restored.memory.update(feature, dt=0.4),
    )


def test_state_rejects_dimension_mismatch_and_non_json_observable_values():
    state = make_state()
    with pytest.raises(ValueError, match="dimension"):
        ResearchState(
            observable_state={},
            memory=SOEMemory(feature_dim=8),
            relations=state.relations,
            subspace=state.subspace,
        )
    with pytest.raises(ValueError, match="JSON-compatible"):
        ResearchState(
            observable_state={"bad": float("nan")},
            memory=state.memory,
            relations=state.relations,
            subspace=state.subspace,
        )


def test_state_rejects_unknown_or_invalid_snapshot_versions():
    payload = make_state().to_dict()
    payload["format_version"] = 999
    with pytest.raises(ValueError, match="unsupported"):
        ResearchState.from_dict(payload)
    with pytest.raises(ValueError, match="valid JSON"):
        ResearchState.from_json("not-json")
