"""Preliminary bounded-input and independent-fit/validation P6 run."""
from __future__ import annotations
import json,sys
import numpy as np
from rgm.leptograph.m4.stability import CoupledAdaptiveSystem, AdaptiveMode

def run(seed_count=20,steps=300):
    maxima=[]; alarm_total=0; rollback_checks=0; promotion_checks=0; improvements=[]
    truth=np.array([[0.8,0.1],[0.1,0.7]])
    for seed in range(seed_count):
        rng=np.random.default_rng(seed); model=CoupledAdaptiveSystem()
        for t in range(steps):
            obs=rng.uniform(-1.0,1.0,size=2); residual=3.0 if t in (80,190) else 0.0
            model.step(obs,residual)
        maxima.append(model.max_observed_norm); alarm_total+=model.detector.alarms
        # Candidate fit and validation use independent generated samples.
        x_fit=rng.normal(size=(128,2)); y_fit=x_fit@truth.T+rng.normal(scale=0.05,size=(128,2))
        fitted=np.linalg.lstsq(x_fit,y_fit,rcond=None)[0].T
        x_val=rng.normal(size=(128,2)); y_val=x_val@truth.T+rng.normal(scale=0.05,size=(128,2))
        incumbent_loss=float(np.mean((x_val@model.revision.accepted_operator.T-y_val)**2))
        candidate_loss=float(np.mean((x_val@fitted.T-y_val)**2))
        prior=model.revision.accepted_operator.copy()
        model.mode=AdaptiveMode.NORMAL; model.start_candidate(fitted)
        promoted=model.validate_candidate(incumbent_loss=incumbent_loss,candidate_loss=candidate_loss,identifiable=True)
        promotion_checks+=int(promoted); improvements.append(incumbent_loss-candidate_loss)
        if promoted:
            model.rollback(); rollback_checks+=int(np.array_equal(model.revision.accepted_operator,prior))
    coupled=np.array([[0.5,1.2],[1.2,0.5]])
    return {"job":"M4-Job3-P6","classification":"preliminary_finite_horizon_stress_and_independent_candidate_validation","seed_count":seed_count,"steps_per_seed":steps,"transition_spectral_radius":CoupledAdaptiveSystem().transition_spectral_radius,"max_state_norm_observed":float(max(maxima)),"all_runs_within_declared_norm_25":bool(max(maxima)<25.0),"detector_alarms":alarm_total,"candidate_promotions":promotion_checks,"mean_independent_validation_loss_improvement":float(np.mean(improvements)),"rollback_restored_trusted_state":rollback_checks==promotion_checks,"coupled_counterexample_eigenvalues":[{"real":float(v.real),"imag":float(v.imag)} for v in np.linalg.eigvals(coupled)],"claim_boundary":"finite-horizon bounded-input and independent-fit/validation lifecycle checks for this synchronous model only; no arbitrary-switching or global stability theorem"}
if __name__=="__main__":
    result=run(); text=json.dumps(result,sort_keys=True,indent=2); print(text)
    if len(sys.argv)>1: open(sys.argv[1],"w",encoding="utf-8").write(text+"\n")
