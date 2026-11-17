"""Run one independent M3 v0.2 refinement work package and emit JSON."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

from rgm.leptograph.m3 import CandidateRevision, ContextBank, ContextDecision, CUSUMDetector, EvidenceActivation, MemoryArchitecture, MultiSourceRidge
from rgm.leptograph.m3.integration_refinement import run_integrated_refinement

CAMPAIGN_ID = "HLG-M3-FINAL-REFINEMENT-v0.2"
WORK_PACKAGES = ("M3-A", "M3-B", "M3-C", "M3-D", "M3-E", "M3-I")


def _context():
    g = np.array([[2.0, 0.25], [0.25, 1.2]])
    cov = np.array([[0.5, 0.08], [0.08, 0.35]])
    mu, z = np.array([0.4, -0.2]), np.array([0.1, 0.3])
    a = np.array([[1.8, 0.4], [0.1, 0.7]])
    old = ContextBank(g, capacity=2, regularisation=0.03)
    sid = old.add_initial(mu, prior_covariance=cov)
    ai = np.linalg.inv(a)
    new = ContextBank(a.T @ g @ a, capacity=2, regularisation=0.03)
    sid2 = new.add_initial(ai @ mu, prior_covariance=ai @ cov @ ai.T)
    s1, s2 = old.score(z, sid), new.score(ai @ z, sid2)
    accepted = old.route(mu + np.array([0.01, -0.01]))[0] is ContextDecision.ACCEPT
    return {"score_invariance_error": float(abs(s1-s2)), "near_context_accepted": bool(accepted),
            "scientific_checks": {"coordinate_invariance": bool(abs(s1-s2) < 1e-9), "accept_path": bool(accepted)},
            "limitations": ["single low-dimensional transported metric example", "threshold calibration open"]}


def _learning():
    rng = np.random.default_rng(2302)
    model = MultiSourceRidge({"a": 2, "b": 3}, 2, 2, ridge=1e-6)
    wa = np.array([[0.8,-0.2],[0.1,0.6]])
    wb = np.array([[0.2,0.0,-0.1],[0.0,0.3,0.15]])
    wc = np.array([[0.08,0.02],[-0.03,0.05]])
    errors = []
    for _ in range(500):
        xa, xb, c = rng.normal(size=2), rng.normal(size=3), rng.normal(size=2)
        y = wa@xa + wb@xb + wc@c + rng.normal(0,0.01,2)
        pred = model.predict({"a":xa,"b":xb},c)
        errors.append(float(np.mean((y-pred)**2)))
        model.update({"a":xa,"b":xb},c,y)
    ident = model.conditional_identifiability()
    norms = {k: float(np.linalg.norm(model.source_operator(k))) for k in ("a","b")}
    return {"samples": int(model.sample_count), "final_100_mse": float(np.mean(errors[-100:])),
            "operator_norms": norms, "conditional_identifiability": ident,
            "scientific_checks": {"both_sources_used": bool(all(v>0.1 for v in norms.values())),
                                  "both_sources_identifiable": bool(all(v["identifiable"] for v in ident.values()))},
            "limitations": ["independent Gaussian source stream only", "held-out compositions not tested"]}


def _activation():
    rng = np.random.default_rng(2303)
    model = MultiSourceRidge({"r":1},0,1,ridge=1e-6)
    for _ in range(120):
        x=float(rng.normal()); model.update({"r":[x]},[],[1.7*x+rng.normal(0,0.01)])
    active=model.predict({"r":[1.0]},[],source_gates={"r":1.0})
    dormant=model.predict({"r":[1.0]},[],source_gates={"r":0.0})
    ctl=EvidenceActivation(on_threshold=0.2,off_threshold=0.1,minimum_observations=2)
    for _ in range(10): ctl.update("r",predictive_improvement=0.9,observed=True,identifiable=True,context_score=0.0)
    before=ctl.snapshot("r")
    ctl.update("r",predictive_improvement=None,observed=False,identifiable=True,context_score=0.0)
    noop=before==ctl.snapshot("r")
    for _ in range(20): ctl.update("r",predictive_improvement=-1.0,observed=True,identifiable=True,context_score=0.0)
    return {"active_prediction":float(active[0]),"dormant_prediction":float(dormant[0]),
            "stored_operator_norm":float(np.linalg.norm(model.source_operator("r"))),
            "scientific_checks":{"gate_changes_prediction":bool(np.linalg.norm(active-dormant)>1e-6),
                                 "operator_survives_dormancy":bool(np.linalg.norm(model.source_operator("r"))>0.1),
                                 "missing_observation_neutral":bool(noop),"negative_evidence_deactivates":bool(not ctl.is_active("r"))},
            "limitations":["single scalar relationship example","activation calibration open"]}


def _revision():
    detector=CUSUMDetector(allowance=0.2,threshold=3.0)
    stationary=[detector.update(0.1) for _ in range(40)]
    shifted=[detector.update(1.0) for _ in range(8)]
    incumbent=np.eye(2)
    accept=CandidateRevision(incumbent); accept.start_candidate(0.9*np.eye(2))
    promoted=accept.evaluate(incumbent_loss=0.4,candidate_loss=0.2,identifiable=True)
    reject=CandidateRevision(incumbent); reject.start_candidate(2.0*np.eye(2))
    rejected=not reject.evaluate(incumbent_loss=0.4,candidate_loss=0.6,identifiable=True)
    return {"stationary_alarms":int(sum(stationary)),"shift_alarms":int(sum(shifted)),
            "scientific_checks":{"stationary_no_alarm":bool(not any(stationary)),"shift_detected":bool(any(shifted)),
                                 "candidate_promoted":bool(promoted),"rejection_preserves_incumbent":bool(rejected and np.array_equal(reject.accepted_operator,incumbent))},
            "limitations":["isolated step-change test only","gradual, variance and transient drift open"]}


def _memory():
    controls=[MemoryArchitecture(k,2,2,64) for k in ("C0","C1","C2","C3","C4")]
    for item in controls:
        item.update_mode(np.array([0.2,-0.1])); item.update_relation(np.array([0.1,0.3]))
        item.read_mode(); item.read_relation()
    records={item.name:item.resource_snapshot() for item in controls}
    return {"resources":records,"scientific_checks":{"five_distinct_records":bool(len({json.dumps(v,sort_keys=True) for v in records.values()})==5),
             "C4_parameters_counted":bool(controls[4].trainable_parameter_count>0),
             "C3_C4_mismatch_reported":bool(controls[3].persistent_bytes!=controls[4].persistent_bytes)},
            "limitations":["instrumentation only","no task-level Pareto or architecture ranking"]}


def run_package(package_id: str) -> dict:
    functions={"M3-A":_context,"M3-B":_learning,"M3-C":_activation,"M3-D":_revision,"M3-E":_memory,
               "M3-I":run_integrated_refinement}
    if package_id not in functions: raise ValueError(f"unknown work package: {package_id}")
    measurements=functions[package_id]()
    json.dumps(measurements,allow_nan=False)
    return {"campaign_id":CAMPAIGN_ID,"package_id":package_id,"execution_passed":True,
            "measurements":measurements,
            "interpretation":"Execution and declared probes only; scientific checks are findings, not an M3-success Boolean."}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-package",choices=WORK_PACKAGES,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    record=run_package(args.work_package)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(record,indent=2,sort_keys=True,allow_nan=False)+"\n"
    args.output.write_text(payload,encoding="utf-8")
    print(json.dumps({"sha256":hashlib.sha256(payload.encode()).hexdigest(),**record},sort_keys=True,allow_nan=False))


if __name__=="__main__":
    main()
