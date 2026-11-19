from rgm.leptograph.m4.composition import *

def fixture():
    a=Entity("a","A"); b=Entity("b","B"); c=Entity("c","C"); d=Entity("d","D")
    r1=RelationType("r1","A","B"); r2=RelationType("r2","B","C"); r3=RelationType("r3","C","D")
    edges=[RelationInstance("e1",r1,a,b,1,1,"x"),RelationInstance("e2",r2,b,c,2,2,"x"),RelationInstance("e3",r3,c,d,3,3,"x")]
    return a,b,c,d,r1,r2,r3,edges

def test_path_returns_full_witness_and_intermediate_entities():
    a,b,c,d,r1,r2,r3,edges=fixture(); q=CompositionQuery(a,(r1,r2,r3),"x",4,4)
    result=compose_paths(edges,q)
    assert len(result.witnesses)==1 and result.witnesses[0].entities==(a,b,c,d)
    assert result.witnesses[0].instance_ids==("e1","e2","e3")

def test_future_observation_and_expiry_are_excluded():
    a,b,c,d,r1,r2,r3,edges=fixture()
    edges += [RelationInstance("future",r1,a,Entity("b2","B"),1,8,"x"),RelationInstance("expired",r1,a,Entity("b3","B"),1,1,"x",valid_until=3)]
    result=compose_paths(edges,CompositionQuery(a,(r1,r2,r3),"x",4,4))
    assert len(result.witnesses)==1 and result.rejected["not_observed"]==1 and result.rejected["not_current"]==1

def test_context_and_event_order_filters():
    a,b,c,d,r1,r2,r3,edges=fixture(); wrong=RelationInstance("wrong",r2,b,c,1.5,1.5,"other")
    q=CompositionQuery(a,(r1,r2,r3),"x",4,4)
    assert len(compose_paths(edges+[wrong],q).witnesses)==1
    bad=RelationInstance("bad",r2,b,c,0.5,2,"x")
    out=compose_paths([edges[0],bad,edges[2]],q)
    assert not out.witnesses and out.rejected["time_order"]==1

def test_path_type_contract_and_failure_attribution():
    a,b,c,d,r1,r2,r3,edges=fixture()
    try: CompositionQuery(a,(r2,r1),"x",4,4)
    except ValueError: pass
    else: raise AssertionError("invalid type chain accepted")
    values={name:True for name in FAILURE_LAYERS}; values["binding"]=False
    assert attribute_failure(values)=="binding"
    values["binding"]=True; assert attribute_failure(values)=="none"

def test_extensional_join_is_associative_and_preserves_witnesses():
    a,b,c,d,r1,r2,r3,edges=fixture()
    w1=CompositionWitness((a,b),(edges[0],)); w2=CompositionWitness((b,c),(edges[1],)); w3=CompositionWitness((c,d),(edges[2],))
    left=compose_witnesses(compose_witnesses(w1,w2),w3)
    right=compose_witnesses(w1,compose_witnesses(w2,w3))
    assert left==right and left.instance_ids==("e1","e2","e3") and left.entities==(a,b,c,d)
