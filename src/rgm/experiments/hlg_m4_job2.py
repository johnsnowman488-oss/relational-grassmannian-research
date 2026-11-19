"""Matched-information P5 comparison: relation retrieval plus current temporal mode."""
from __future__ import annotations
import json,sys
import numpy as np
from rgm.leptograph.m4.architectures import M4MemoryVariant,BoundedContextAcquisition,P4_TRANSFER_SCOPE
from rgm.leptograph.m3.context import ContextBank

def run(seed_count=20,relation_count=8,delays=(0,1,4,8)):
    names=("A","B","C","R"); errors={n:{str(d):[] for d in delays} for n in names}; gains=[]; mode_gains=[]
    rates=np.array([0.01,0.05,0.2,0.8])
    for seed in range(seed_count):
        world_rng=np.random.default_rng(seed); values=world_rng.normal(size=relation_count)
        calibration_targets=world_rng.normal(size=128); calibration_delays=world_rng.integers(0,9,size=128)
        calibration_traces=calibration_targets*np.mean(np.exp(-rates[:,None]*calibration_delays[None,:]),axis=0)
        calibrator=M4MemoryVariant("A",relation_count=relation_count)
        gain=calibrator.fit_readout(calibration_traces,calibration_targets); gains.append(gain)
        mode_cal=world_rng.normal(size=128); mode_calibrator=M4MemoryVariant("A",relation_count=relation_count)
        mode_gain=mode_calibrator.fit_mode_readout(mode_cal,mode_cal); mode_gains.append(mode_gain)
        for delay in delays:
            for key in range(relation_count):
                initial_mode=world_rng.normal(size=2)
                distractors=[(int((key+1+(j%(relation_count-1)))%relation_count),float(world_rng.normal()),world_rng.normal(size=2)) for j in range(delay)]
                mode_channels=np.zeros(rates.size)
                for observed_mode in [initial_mode]+[item[2] for item in distractors]:
                    mode_channels=np.exp(-rates)*mode_channels+observed_mode[0]
                target=float(values[key]+0.5*np.mean(mode_channels))
                for name in names:
                    model=M4MemoryVariant(name,relation_count=relation_count)
                    if name=="A": model.readout_gain=gain; model.mode_gain=mode_gain
                    if name=="B": model.mode_gain=mode_gain
                    model.observe(key,float(values[key]),initial_mode)
                    for other,value,mode in distractors: model.observe(other,value,mode)
                    errors[name][str(delay)].append((model.query(key)-target)**2)
    summary={n:{d:float(np.mean(v)) for d,v in by_delay.items()} for n,by_delay in errors.items()}
    resources={n:M4MemoryVariant(n,relation_count=relation_count).persistent_state_bytes for n in names}
    bank=ContextBank(metric=np.eye(2),capacity=1,novelty_repeats=2); bank.add_initial([0.0,0.0]); acquisition=BoundedContextAcquisition(bank)
    acquisition.observe([10.0,10.0]); capacity_result=acquisition.observe([10.0,10.0])
    return {"job":"M4-Job2-P5","classification":"preliminary_synthetic_joint_relation_temporal_comparison","seed_count":seed_count,"relation_count":relation_count,"delays":list(delays),"target":"stored relation value + 0.5 * latest temporal-mode coordinate","mean_squared_error_by_architecture_and_delay":summary,"empty_state_numeric_bytes_by_architecture":resources,"A_relational_readout_gain_mean":float(np.mean(gains)),"temporal_mode_readout_gain_mean":float(np.mean(mode_gains)),"learned_readout_parameter_count":{"A":2,"B":1,"C":0,"R":0},"p2_full_capacity_decision":capacity_result["status"],"p3_gap_semantics":"A/C temporal state decays; B relation store persists while its SOE mode trace decays; R relation store persists","p4_transfer_scope":P4_TRANSFER_SCOPE,"claim_boundary":"controlled joint retrieval microtask and bounded acquisition only; not a general architecture winner or P0 composition result"}
if __name__=="__main__":
    result=run(); text=json.dumps(result,sort_keys=True,indent=2); print(text)
    if len(sys.argv)>1: open(sys.argv[1],"w",encoding="utf-8").write(text+"\n")
