import numpy as np

from rgm.experiments.babi_learning_campaign import (
    CtypesPersistentRuntime, _features, _make_nary, _make_relations,
)
from rgm.experiments.babi_structured import StructuredEvent


class FakeGFE:
    def __init__(self):
        self.calls = 0

    def step_hierarchical_chain_spec(
        self, library, levels, edges, *, level_states, external_forcing, forcing_level
    ):
        self.calls += 1
        assert forcing_level == 0
        assert external_forcing == [0.0, 0.0]
        updated = []
        for state in level_states:
            updated.append({
                "u": [float(x) + 1.0 for x in state["u"]],
                "chi": [float(x) + 0.1 for x in state["chi"]],
                "t": float(state["t"]) + 0.01,
            })
        return {"level_states": updated, "spectral_units": []}


def test_ctypes_runtime_embeds_all_level_feedback_and_issues_one_native_step():
    gfe = FakeGFE()
    levels = [
        {"u": [0.0, 0.0], "chi": [0.0], "t": 0.0},
        {"u": [0.0, 0.0, 0.0], "chi": [0.0], "t": 0.0},
        {"u": [0.0, 0.0, 0.0, 0.0], "chi": [0.0], "t": 0.0},
    ]
    runtime = CtypesPersistentRuntime(gfe, object(), levels, [])
    feedback = {
        0: [0.1, 0.2],
        1: [0.3, 0.4, 0.5],
        2: [0.6, 0.7, 0.8, 0.9],
    }
    result = runtime.step(feedback)
    assert gfe.calls == 1
    assert runtime.step_count == 1
    assert result["level_states"][2]["u"] == [1.6, 1.7, 1.8, 1.9]
    assert runtime.get_state()["level_states"][0]["u"] == [1.1, 1.2]
    snapshot = runtime.get_state()
    runtime.step(feedback)
    runtime.restore(snapshot)
    assert runtime.get_state() == snapshot


def test_event_features_have_the_three_frozen_level_dimensions():
    event = StructuredEvent(
        "story:event1", "GIVE",
        (("giver", "amara"), ("object", "crystal"), ("recipient", "belen")),
        1, 1, "synthetic://story/event/1",
    )
    features = _features(5, event, "start", 1, 10)
    assert {level: len(vector) for level, vector in features.items()} == {0: 2, 1: 3, 2: 4}


def test_nary_event_and_relational_projection_preserve_one_source_event():
    event = StructuredEvent(
        "story:event1", "GIVE",
        (("giver", "amara"), ("object", "crystal"), ("recipient", "belen")),
        1, 1, "synthetic://story/event/1",
    )
    nary = _make_nary(event, "start", "test-source")
    relations = _make_relations(event, "start")
    assert nary.event_id == event.event_id
    assert {p.role for p in nary.participants} == {"giver", "object", "recipient"}
    assert len(relations) == 2
    assert all(event.event_id in relation.provenance for relation in relations)
