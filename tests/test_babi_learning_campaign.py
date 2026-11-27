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
        @property
        def event_ids(self):
            raise AssertionError("campaign hot path must not materialize the global evidence-ID list")

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




def test_hlb_capacity_preflight_counts_event_and_relation_projections():
    from rgm.experiments.babi_learning_campaign import (
        HLB_CAPACITY, _capacity_requirements,
    )
    from rgm.experiments.babi_structured import StructuredStory

    move = StructuredEvent(
        "capacity:story:move", "MOVE",
        (("actor", "amara"), ("destination", "garden")),
        1, 1, "synthetic://capacity/move",
    )
    give = StructuredEvent(
        "capacity:story:give", "GIVE",
        (("giver", "amara"), ("recipient", "belen"), ("object", "book")),
        2, 2, "synthetic://capacity/give",
    )
    story = StructuredStory("capacity:story", (move, give), ())
    requirements = _capacity_requirements([(story, {})])

    assert requirements == {"source_event_count": 2, "source_relation_count": 3}
    # Frozen full Task 3 campaign needs 154,786; keep explicit safety margin.
    assert HLB_CAPACITY >= 154786


def test_campaign_checkpoint_is_atomic_and_marks_partial_vs_complete(tmp_path):
    import json
    from rgm.experiments.babi_learning_campaign import (
        CHANNELS, _write_campaign_checkpoint,
    )

    output_path = tmp_path / "task3-HLA.json"
    partial = [{"seed": 1, "variant": "full_learning"}]
    snapshot = _write_campaign_checkpoint(
        output_path, task_id=3, architecture="HLA",
        seeds=[1, 2], variants=list(CHANNELS), results=partial,
        expected_run_count=2 * len(CHANNELS), complete=False,
    )
    assert snapshot["status"] == "in_progress"
    assert snapshot["complete"] is False
    assert snapshot["completed_run_count"] == 1
    assert snapshot["expected_run_count"] == 2 * len(CHANNELS)
    assert json.loads(output_path.read_text()) == snapshot
    assert not (tmp_path / "task3-HLA.json.tmp").exists()

    completed = _write_campaign_checkpoint(
        output_path, task_id=3, architecture="HLA",
        seeds=[1, 2], variants=list(CHANNELS), results=partial * (2 * len(CHANNELS)),
        expected_run_count=2 * len(CHANNELS), complete=True,
    )
    assert completed["status"] == "completed"
    assert completed["complete"] is True
    assert completed["completed_run_count"] == completed["expected_run_count"]
