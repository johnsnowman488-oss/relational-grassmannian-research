"""Deterministic preliminary P0/P1 semantic check; not a confirmatory campaign."""
from __future__ import annotations
import json
from ._m4_output import emit_json
from rgm.leptograph.m4.composition import Entity, RelationType, RelationInstance, CompositionQuery, compose_paths, attribute_failure

def run():
    a=Entity("a","A"); b=Entity("b","B"); c=Entity("c","C"); d=Entity("d","D")
    r1=RelationType("r1","A","B"); r2=RelationType("r2","B","C"); r3=RelationType("r3","C","D")
    facts=[RelationInstance("e1",r1,a,b,1,1,"ctx"),RelationInstance("e2",r2,b,c,2,2,"ctx"),RelationInstance("e3",r3,c,d,3,3,"ctx"),
           RelationInstance("future",r1,a,Entity("b2","B"),1,9,"ctx")]
    q=CompositionQuery(a,(r1,r2,r3),"ctx",4,4,max_event_gap=2)
    result=compose_paths(facts,q)
    layers={name: True for name in ("retention","retrieval","binding","path_selection","operator_application","composition","readout")}
    layers["binding"]=False
    out={"job":"M4-Job1-P0-P1","classification":"preliminary_reference_semantics","query_path":["r1","r2","r3"],"witness_count":len(result.witnesses),"witness_ids":[list(w.instance_ids) for w in result.witnesses],"endpoint_ids":[e.entity_id for e in result.endpoints],"rejected":result.rejected,"future_observation_excluded":result.rejected["not_observed"]==1,"p1_first_failure":attribute_failure(layers),"claim_boundary":"reference semantics and diagnostic attribution only; no learner performance claim"}
    return out
if __name__=="__main__": emit_json(run())
