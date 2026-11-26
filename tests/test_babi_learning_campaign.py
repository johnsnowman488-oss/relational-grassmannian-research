from rgm.experiments.babi_learning_campaign import (
    _features, _make_nary, _make_relations,
)
from rgm.experiments.babi_structured import StructuredEvent


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
