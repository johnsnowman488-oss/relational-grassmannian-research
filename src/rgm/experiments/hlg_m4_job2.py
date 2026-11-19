"""Matched-information preliminary P5 retention comparison (synthetic microtask)."""
from __future__ import annotations
import json, sys
import numpy as np
from rgm.leptograph.m4.architectures import M4MemoryVariant

def run(seed_count=20, relation_count=8, delays=(0,1,4,8)):
    names=("A","B","C","R"); errors={n:{str(d):[] for d in delays} for n in names}
    for seed in range(seed_count):
        rng=np.random.default_rng(seed)
        values=rng.normal(size=relation_count)
        for delay in delays:
            for key in range(relation_count):
                for name in names:
                    model=M4MemoryVariant(name,relation_count=relation_count)
                    model.observe(key,float(values[key]))
                    for j in range(delay):
                        other=(key+1+j)%relation_count
                        model.observe(other,float(rng.normal()))
                    errors[name][str(delay)].append((model.query(key)-values[key])**2)
    summary={n:{d:float(np.mean(v)) for d,v in by_delay.items()} for n,by_delay in errors.items()}
    resources={n:M4MemoryVariant(n,relation_count=relation_count).persistent_state_bytes for n in names}
    return {"job":"M4-Job2-P5","classification":"preliminary_synthetic_retention_comparison","seed_count":seed_count,"relation_count":relation_count,"delays":list(delays),"mean_squared_error_by_architecture_and_delay":summary,"empty_state_bytes_by_architecture":resources,"claim_boundary":"compares state retention under a controlled retrieval microtask only; not a general architecture winner or P0 composition result"}
if __name__=="__main__":
    result=run(); text=json.dumps(result,sort_keys=True,indent=2); print(text)
    if len(sys.argv)>1: open(sys.argv[1],"w",encoding="utf-8").write(text+"\n")
