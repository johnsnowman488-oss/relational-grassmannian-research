"""Integrated acceptance of evidence-safe lifecycle behavior over the H1 director."""
import copy
import hashlib

import pytest

from rgm.memory import SOEMemory
from rgm.leptograph.m4.evidence import NaryEvent, Participant
from rgm.leptograph.m4.hierarchical import (
    CompositeLifecycle, HLBAdapter, HierarchicalRuntimeDirector,
)
from rgm.leptograph.m4.soe_bridge import SOEHierarchyBridge


class Runtime:
    def __init__(self, banks):
        self.state = {
            "level_states": [
                {"u": m.snapshot().reshape(-1).tolist(),
                 "chi": [0.0] * m.channel_count, "t": 0.0}
                for m in banks
            ],
            "step_count": 0,
        }

    def get_state(self):
        return copy.deepcopy(self.state)

    def step(self, feedback_by_level=None):
        candidate = self.get_state()
        for level, values in (feedback_by_level or {}).items():
            candidate["level_states"][level]["u"] = list(values)
        candidate["step_count"] += 1
        self.state = candidate
        return self.get_state()

    def checkpoint(self):
        return self.get_state()

    def restore(self, state):
        if len(state["level_states"]) != 3:
            raise ValueError("invalid native checkpoint")
        self.state = copy.deepcopy(state)


def make_system(capacity=8):
    banks = [
        SOEMemory(feature_dim=2, decay_rates=[0.1, 0.4]),
        SOEMemory(feature_dim=3, decay_rates=[0.2, 0.7]),
        SOEMemory(feature_dim=4, decay_rates=[0.05, 0.3]),
    ]
    runtime = Runtime(banks)
    bridge = SOEHierarchyBridge(runtime, banks, dt=0.01)
    adapter = HLBAdapter(bridge, capacity=capacity)
    director = HierarchicalRuntimeDirector(adapter)
    return runtime, director, CompositeLifecycle(director)


def evidence(event_id, *, event_time, observed_at, value="fred"):
    payload = event_id.encode()
    return NaryEvent(
        event_id, "gift",
        (Participant("giver", "mary", "person"),
         Participant("object", "cake", "object"),
         Participant("recipient", value, "person")),
        event_time, observed_at, "test-source", f"mem://{event_id}",
        hashlib.sha256(payload).hexdigest(),
    )


def test_integrated_failed_validation_never_promotes_and_rollback_keeps_new_evidence():
    runtime, director, lifecycle = make_system()
    evidence_store = director.adapter.evidence
    initial = lifecycle.checkpoint()
    director.exchange(event_time=1.0, observed_at=1.0, event_features={0: [1.0, 0.0]})
    director.adapter.observe_event(evidence("during-candidate", event_time=1.0, observed_at=1.0))

    # A failed independent validation is a hard promotion rejection.
    validation_passed = False
    if validation_passed:
        lifecycle.promote()
    assert lifecycle.version == 0
    lifecycle.rollback()

    assert runtime.state["step_count"] == initial["native"]["step_count"]
    assert director.event_tick == 0
    assert evidence_store.event_ids == ("during-candidate",)
    assert evidence_store.get_event("during-candidate").role("recipient").entity_id == "fred"


def test_integrated_promotion_then_rollback_preserves_intervening_and_late_evidence():
    runtime, director, lifecycle = make_system()
    evidence_store = director.adapter.evidence
    director.adapter.observe_event(evidence("preexisting", event_time=0.5, observed_at=0.5))
    lifecycle.checkpoint()

    director.exchange(event_time=1.0, observed_at=1.0, event_features={0: [0.5, 0.25]})
    director.adapter.observe_event(evidence("candidate-observation", event_time=1.0, observed_at=1.0))
    assert lifecycle.promote() == 1

    # This observation arrives while the promoted candidate is active. Its
    # event time is earlier than arrival time, but the source journal is append-only.
    director.exchange(event_time=1.5, observed_at=2.0, event_features={0: [0.0, 1.0]})
    director.adapter.observe_event(evidence("late-observation", event_time=1.5, observed_at=2.0))
    before_rollback_ids = evidence_store.event_ids

    lifecycle.rollback()
    assert lifecycle.version == 0
    assert runtime.state["step_count"] == 0
    assert director.event_tick == 0
    assert evidence_store.event_ids == before_rollback_ids
    assert "preexisting" in evidence_store.event_ids
    assert evidence_store.get_event("late-observation", observation_cutoff=2.0).event_time == 1.5
    with pytest.raises(PermissionError):
        evidence_store.get_event("late-observation", observation_cutoff=1.9)


def test_integrated_capacity_exhaustion_is_explicit_and_does_not_erase_protected_records():
    runtime, director, lifecycle = make_system(capacity=1)
    lifecycle.checkpoint()
    from rgm.leptograph.m4.composition import Entity, RelationInstance, RelationType
    person, place = Entity("p", "person"), Entity("x", "place")
    relation = RelationType("located_at", "person", "place")
    first = RelationInstance("r1", relation, person, place, 1.0, 1.0, provenance="src")
    second = RelationInstance("r2", relation, person, place, 2.0, 2.0, provenance="src")
    assert director.adapter.observe(0, first) == "STORED"
    assert director.adapter.observe(0, second) == "ABSTAIN_CAPACITY"
    assert director.adapter.store.count == 1
    assert director.adapter.store.records(cutoff=3.0)[0].instance_id == "r1"

def test_source_relations_survive_candidate_rollback_but_candidate_relations_do_not():
    runtime, director, lifecycle = make_system()
    from rgm.leptograph.m4.composition import Entity, RelationInstance, RelationType
    person, office = Entity("p", "person"), Entity("office", "place")
    relation = RelationType("located_at", "person", "place")
    observed = RelationInstance("source-r1", relation, person, office, 1.0, 1.0,
                                provenance="source-payload")
    candidate = RelationInstance("candidate-r2", relation, person, office, 2.0, 2.0,
                                 provenance="candidate")
    lifecycle.checkpoint()
    director.exchange(event_time=1.0, observed_at=1.0, relation_records=((0, observed),))
    assert director.adapter.store.count == 1
    assert director.adapter.observe(0, candidate) == "STORED"

    lifecycle.rollback()
    records = director.adapter.store.records(cutoff=3.0)
    assert {record.instance_id for record in records} == {"source-r1"}
    assert set(director.adapter.source_relation_checkpoint()["records"][0]["record"]) >= {
        "instance_id", "subject", "object", "relation_type"
    }
