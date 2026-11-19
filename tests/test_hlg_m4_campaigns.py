import numpy as np
from rgm.experiments.m4_campaigns import run, _world, _new_model
from rgm.leptograph.m4.system import M4Query

def test_g1_campaign_contains_all_depths_and_both_architectures():
    result=run(seed_count=2)
    rows=result["G1"]["rows"]
    assert {r["depth"] for r in rows}=={2,3,4}
    assert {r["architecture"] for r in rows}=={"A","B"}
    assert all(r["witness_valid"] for r in rows if r["status"]=="SELECTED")

def test_order_sensitive_readout_separates_same_bag_heldout_paths():
    result=run(seed_count=3)
    assert all(v["correct"]==v["total"] for v in result["G1"]["accuracy_by_architecture_depth"].values())

def test_g3_abstention_and_g4_full_rollback_are_exercised():
    result=run(seed_count=2)
    assert result["G3"]["ambiguity_abstention_rate"]==1.0
    assert result["G3"]["wrong_context_abstention_rate"]==1.0
    assert all(r["rollback_exact"] for r in result["G4"]["rows"])
    assert all(r["detector_threshold"]==24.0 for r in result["G4"]["rows"])

def test_g5_populated_relation_store_scales_without_eviction():
    result=run(seed_count=1)
    rows=result["G5"]["rows"]
    assert [r["B"]["relation_instance_count"] for r in rows]==[10,100,500,1000]
    assert all(r["A"]["relation_instance_count"]==0 for r in rows)
    assert rows[-1]["B"]["relation_payload_bytes"]>rows[0]["B"]["relation_payload_bytes"]
