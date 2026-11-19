import numpy as np
import pytest
from rgm.leptograph.m4.composition import Entity, RelationType, RelationInstance, CompositionWitness
from rgm.leptograph.m4.system import M4ABSystem, M4Query, PathTrainingExample
from rgm.leptograph.m4.adaptive import M4AdaptiveController

def fixture():
    a=Entity("a","A"); b=Entity("b","B"); c=Entity("c","C")
    r1=RelationType("r1","A","B"); r2=RelationType("r2","B","C")
    events=(RelationInstance("e1",r1,a,b,1,1,"ctx"),
            RelationInstance("e2",r2,b,c,2,2,"ctx"))
    return a,b,c,r1,r2,events

def trained(arch, rels, events):
    model=M4ABSystem(arch,rels)
    for e in events: model.observe(e)
    model.fit_readout([
        PathTrainingExample(("r1","r2"),1),
        PathTrainingExample(("r1",),0),
        PathTrainingExample(("r2",),0),
    ],epochs=500,learning_rate=0.15)
    return model

def test_A_and_B_share_witness_contract_but_only_B_retains_relation_instances():
    a,b,c,r1,r2,events=fixture()
    A=trained("A",(r1,r2),events); B=trained("B",(r1,r2),events)
    assert A.store is None and B.store is not None
    assert len(B.store.records)==2
    assert A.resource_snapshot()["relation_instance_count"]==0
    assert B.resource_snapshot()["relation_instance_count"]==2

def test_B_retrieves_after_outage_and_A_requires_current_visible_batch():
    a,b,c,r1,r2,events=fixture()
    A=trained("A",(r1,r2),events); B=trained("B",(r1,r2),events)
    A.advance_gap(8); B.advance_gap(8)
    q=M4Query(a,c,"ctx",query_time=10,observation_cutoff=10,max_depth=2)
    assert A.query(q)["status"]=="ABSTAIN_NO_PATH"
    result=B.query(q)
    assert result["status"]=="SELECTED"
    assert result["witnesses"][0].instance_ids==("e1","e2")

def test_A_can_query_an_explicit_current_observation_window_without_persistent_store():
    a,b,c,r1,r2,events=fixture()
    A=trained("A",(r1,r2),events)
    q=M4Query(a,c,"ctx",10,10,max_depth=2)
    result=A.query(q,visible_events=events)
    assert result["status"]=="SELECTED"
    assert A.store is None

def test_future_observation_is_not_used_by_B_even_if_already_stored():
    a,b,c,r1,r2,events=fixture()
    B=trained("B",(r1,r2),events)
    future=RelationInstance("future",r1,a,Entity("b2","B"),1,20,"ctx")
    B.observe(future)
    q=M4Query(a,c,"ctx",query_time=10,observation_cutoff=10,max_depth=2)
    result=B.query(q)
    assert result["status"]=="ABSTAIN_CUTOFF_UNSUPPORTED"
    # The system refuses an as-of query older than its current temporal state;
    # it does not silently score using future-contaminated SOE traces.

def test_B_capacity_abstains_without_silent_eviction():
    a,b,c,r1,r2,events=fixture()
    B=M4ABSystem("B",(r1,r2),relation_capacity=1)
    assert B.observe(events[0])=="STORED"
    assert B.observe(events[1])=="ABSTAIN_CAPACITY"
    assert [e.instance_id for e in B.store.records]==["e1"]

def test_full_snapshot_rollback_restores_temporal_and_relational_state():
    a,b,c,r1,r2,events=fixture()
    B=trained("B",(r1,r2),events)
    controller=M4AdaptiveController(B)
    before=B.snapshot()
    controller.start_candidate(B.readout_weights+0.2)
    assert controller.validate_candidate(1.0,0.5,True)
    B.observe(RelationInstance("e3",r2,b,c,3,3,"ctx"))
    B.advance_gap(2)
    controller.rollback()
    assert B.store.records==before["store"]["records"]
    assert np.array_equal(B.soe.channels,np.asarray(before["soe"]["channels"]))
    assert np.array_equal(B.readout_weights,before["readout_weights"])
    assert controller.rollback_count==1

def test_failed_candidate_does_not_change_trusted_system():
    a,b,c,r1,r2,events=fixture()
    A=trained("A",(r1,r2),events)
    before=A.snapshot()
    controller=M4AdaptiveController(A)
    controller.start_candidate(A.readout_weights+0.1)
    assert not controller.validate_candidate(1.0,1.1,True)
    assert np.array_equal(A.readout_weights,before["readout_weights"])
    assert controller.mode=="NORMAL"

def test_threshold_24_is_used_for_integrated_detector():
    a,b,c,r1,r2,events=fixture()
    A=trained("A",(r1,r2),events)
    controller=M4AdaptiveController(A)
    assert controller.detector.threshold==24.0

def test_manually_constructed_inconsistent_witness_is_rejected():
    a,b,c,r1,r2,events=fixture()
    with pytest.raises(ValueError):
        CompositionWitness((a,c),(events[0],))
