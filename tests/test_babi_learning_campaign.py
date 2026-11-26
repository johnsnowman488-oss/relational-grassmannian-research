from rgm.experiments.babi_learning_campaign import (
    SOE_BANK_CONFIG, _features, _make_nary, _make_relations, _query_events,
)
from rgm.leptograph.m4.soe_bridge import make_h0_chain_spec
from rgm.memory.soe import SOEMemory
from rgm.experiments.babi_structured import StructuredEvent


def test_event_features_have_the_three_frozen_level_dimensions():
    event = StructuredEvent(
        "story:event1", "GIVE",
        (("giver", "amara"), ("object", "crystal"), ("recipient", "belen")),
        1, 1, "synthetic://story/event/1",
    )
    features = _features(5, event, "start", 1, 10)
    assert {level: len(vector) for level, vector in features.items()} == {0: 4, 1: 4, 2: 4}


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



def test_babi_feature_embedding_satisfies_pinned_h0_chain_dimensions():
    memories = [
        SOEMemory(feature_dim=dimension, decay_rates=decays)
        for dimension, decays in SOE_BANK_CONFIG
    ]
    kernels = [
        {"gamma": list(reversed(decays)), "w": [0.5, 0.5]}
        for _dimension, decays in SOE_BANK_CONFIG
    ]
    levels, edges = make_h0_chain_spec(memories, kernels, dt=0.01)
    native_dimensions = [len(level["u"]) for level in levels]
    assert native_dimensions == [8, 8, 8]
    assert [(edge["source_level"], edge["target_level"]) for edge in edges if edge["relation"] == 0] == [
        (0, 1), (1, 2),
    ]



def test_hlb_query_recovery_flattens_source_event_tuple():
    event = StructuredEvent(
        "task5/fit/story000001:line000001", "GIVE",
        (("giver", "amara"), ("object", "crystal"), ("recipient", "belen")),
        1, 1, "task5/fit/story000001#line=1",
    )
    nary = _make_nary(event, "start", "test-source")

    class Evidence:
        event_ids = (event.event_id,)

    class Adapter:
        evidence = Evidence()

        @staticmethod
        def recover_evidence(evidence_id, *, observation_cutoff):
            assert evidence_id == event.event_id
            assert observation_cutoff == 2.0
            return (nary,)

    recovered = _query_events(
        Adapter(), "HLB", "task5/fit/story000001", 2, [event]
    )
    assert recovered == [event]
