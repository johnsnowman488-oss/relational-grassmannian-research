"""Matched-information preliminary P5 retention comparison and P2/P3 checks."""
from __future__ import annotations
import json,sys
import numpy as np
from rgm.leptograph.m4.architectures import M4MemoryVariant,BoundedContextAcquisition,P4_TRANSFER_SCOPE
from rgm.leptograph.m3.context import ContextBank

def run(seed_count=20,relation_count=8,delays=(0,1,4,8)):
    names=("A","B","C","R"); errors={n:{str(d):[] for d in delays} for n in names}
    for seed in range(seed_count):
        world_rng=np.random.default_rng(seed); values=world_rng.normal(size=relation_count)
        for delay in delays:
            for key in range(relation_count):
                distractors=[(int((key+1+j)%relation_count),float(world_rng.normal()),world_rng.normal(size=2)) for j in range(delay)]
                for name in names:
                    model=M4MemoryVariant(name,relation_count=relation_count)
                    model.observe(key,float(values[key]))
                    for other,value,mode in distractors: model.observe(other,value,mode)
                    errors[name][str(delay)].append((model.query(key)-values[key])**2)
    summary={n:{d:float(np.mean(v)) for d,v in by_delay.items()} for n,by_delay in errors.items()}
    resources={n:M4MemoryVariant(n,relation_count=relation_count).persistent_state_bytes for n in names}
    bank=ContextBank(metric=np.eye(2),capacity=1,novelty_repeats=2)
    bank.add_initial([0.0,0.0]); acquisition=BoundedContextAcquisition(bank)
    acquisition.observe([10.0,10.0]); capacity_result=acquisition.observe([10.0,10.0])
    return {"job":"M4-Job2-P5","classification":"preliminary_synthetic_retention_comparison","seed_count":seed_count,"relation_count":relation_count,"delays":list(delays),"mean_squared_error_by_architecture_and_delay":summary,"empty_state_numeric_bytes_by_architecture":resources,"p2_full_capacity_decision":capacity_result["status"],"p3_gap_semantics":"A/C temporal states decay during advance_gap; B/R explicit relation stores persist","p4_transfer_scope":P4_TRANSFER_SCOPE,"claim_boundary":"controlled retrieval retention and bounded acquisition only; not a general architecture winner or P0 composition result"}
if __name__=="__main__":
    result=run(); text=json.dumps(result,sort_keys=True,indent=2); print(text)
    if len(sys.argv)>1: open(sys.argv[1],"w",encoding="utf-8").write(text+"\n")
