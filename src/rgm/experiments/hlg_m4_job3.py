"""Preliminary bounded-input and lifecycle safety run for M4 P6."""
from __future__ import annotations
import json,sys
import numpy as np
from rgm.leptograph.m4.stability import CoupledAdaptiveSystem, AdaptiveMode

def run(seed_count=20,steps=300):
    maxima=[]; alarm_total=0; rollback_checks=0; promotion_checks=0
    for seed in range(seed_count):
        rng=np.random.default_rng(seed); model=CoupledAdaptiveSystem()
        for t in range(steps):
            obs=rng.uniform(-1.0,1.0,size=2); residual=3.0 if t in (80,190) else 0.0
            model.step(obs,residual)
        maxima.append(model.max_observed_norm); alarm_total+=model.detector.alarms
        prior=model.revision.accepted_operator.copy(); candidate=prior+0.05*np.eye(2)
        model.mode=AdaptiveMode.NORMAL; model.start_candidate(candidate)
        promoted=model.validate_candidate(incumbent_loss=1.0,candidate_loss=0.8,identifiable=True)
        promotion_checks+=int(promoted)
        model.rollback(); rollback_checks+=int(np.array_equal(model.revision.accepted_operator,prior))
    coupled=np.array([[0.5,1.2],[1.2,0.5]])
    return {"job":"M4-Job3-P6","classification":"preliminary_finite_horizon_stress_and_lifecycle_check","seed_count":seed_count,"steps_per_seed":steps,"transition_spectral_radius":CoupledAdaptiveSystem().transition_spectral_radius,"max_state_norm_observed":float(max(maxima)),"all_runs_within_declared_norm_25":bool(max(maxima)<25.0),"detector_alarms":alarm_total,"candidate_promotions":promotion_checks,"rollback_restored_trusted_state":rollback_checks==seed_count,"coupled_counterexample_eigenvalues":[{"real":float(v.real),"imag":float(v.imag)} for v in np.linalg.eigvals(coupled)],"claim_boundary":"finite-horizon bounded-input and rollback checks for this synchronous model only; no arbitrary-switching or global stability theorem"}
if __name__=="__main__":
    result=run(); text=json.dumps(result,sort_keys=True,indent=2); print(text)
    if len(sys.argv)>1: open(sys.argv[1],"w",encoding="utf-8").write(text+"\n")
