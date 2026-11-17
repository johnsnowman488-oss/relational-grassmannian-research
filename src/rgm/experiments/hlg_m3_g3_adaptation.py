"""HLG-M3 G3 paired adaptation diagnostics across three environments."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any
import numpy as np

CAMPAIGN_ID = "HLG-M3-G3-ADAPTATION-v0.1"
ENVIRONMENTS = ("stable", "gradual", "abrupt")
POLICIES = ("no_revision", "immediate_revision", "validated_revision", "delayed_validated_revision")
STEPS, INITIAL_FIT_STEPS = 512, 128
CHANGE_START, CHANGE_END = 160, 320
FIT_STEPS, VALIDATION_STEPS, DELAY_STEPS = 32, 32, 32
NOISE_STD = 0.02

def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

def _operator_pair(seed: int):
    rng = np.random.default_rng(int(seed))
    return rng.normal(0, .22, (2,2)), rng.normal(0, .20, (2,2))

def generate_stream(*, world_seed: int, replicate_seed: int, environment: str, steps: int=STEPS, noise_std: float=NOISE_STD):
    if environment not in ENVIRONMENTS: raise ValueError(f"unknown environment: {environment}")
    if steps <= INITIAL_FIT_STEPS + FIT_STEPS + VALIDATION_STEPS: raise ValueError("steps are too short")
    if noise_std <= 0: raise ValueError("noise_std must be positive")
    base, delta = _operator_pair(world_seed)
    rng = np.random.default_rng(int(replicate_seed))
    x = rng.normal(size=(steps,2)); y = np.empty((steps,2)); path = np.empty((steps,2,2))
    for t in range(steps):
        if environment == "stable": fraction = 0.0
        elif environment == "abrupt": fraction = float(t >= CHANGE_START)
        else: fraction = float(np.clip((t-CHANGE_START)/(CHANGE_END-CHANGE_START),0,1))
        theta = base + fraction*delta
        path[t] = theta
        y[t] = theta @ x[t] + rng.normal(0,noise_std,2)
    return {"x":x,"y":y,"theta_path":path,"base_operator":base,"changed_operator":base+delta,
            "environment":environment,"world_seed":int(world_seed),"replicate_seed":int(replicate_seed),
            "noise_std":float(noise_std)}

def _fit(x, y, ridge=1e-6):
    if x.ndim != 2 or y.ndim != 2 or len(x) != len(y) or len(x)<2: raise ValueError("invalid fit rows")
    return np.linalg.solve(x.T@x + ridge*np.eye(x.shape[1]), x.T@y).T

def _cluster_ci(values, seed=20261118, draws=4000):
    if not values: return {"mean":None,"lower_95":None,"upper_95":None,"world_count":0}
    a=np.asarray(values,float); rng=np.random.default_rng(seed)
    boot=np.mean(a[rng.integers(0,len(a),size=(draws,len(a)))],axis=1)
    return {"mean":float(a.mean()),"lower_95":float(np.quantile(boot,.025)),
            "upper_95":float(np.quantile(boot,.975)),"world_count":len(a)}

def evaluate_policy(stream, policy, detector_threshold=8.0):
    if policy not in POLICIES: raise ValueError(f"unknown policy: {policy}")
    x,y=stream["x"],stream["y"]; incumbent=_fit(x[:INITIAL_FIT_STEPS],y[:INITIAL_FIT_STEPS]); active=incumbent.copy()
    phase="IDLE"; delay_left=0; fit_x=[]; fit_y=[]; candidate=None
    val_c=val_i=0.0; val_n=0; cusum=0.0; alarm=None; promoted=False; promotion_step=None
    fixed_losses=[]; policy_losses=[]; post_fixed=[]; post_policy=[]; false_alarm=False
    noise_var=stream["noise_std"]**2
    for t in range(INITIAL_FIT_STEPS,len(x)):
        pred=active@x[t]; residual=y[t]-pred; pl=float(residual@residual)
        fixed_res=y[t]-incumbent@x[t]; fl=float(fixed_res@fixed_res)
        policy_losses.append(pl); fixed_losses.append(fl)
        if t>=CHANGE_START: post_policy.append(pl); post_fixed.append(fl)
        # Prediction/loss are fixed before the current target enters detector or fit.
        if policy!="no_revision" and not promoted and phase=="IDLE":
            detector_res=y[t]-incumbent@x[t]
            score=float(detector_res@detector_res)/max(2*noise_var,1e-12)-1
            cusum=max(0.0,cusum+score-.25)
            if cusum>=float(detector_threshold):
                alarm=t; false_alarm=stream["environment"]=="stable"
                phase="DELAY" if policy=="delayed_validated_revision" else "FIT"
                delay_left=DELAY_STEPS if phase=="DELAY" else 0; fit_x=[]; fit_y=[]; cusum=0
        # Feedback is consumed only after prediction and loss have been recorded.
        if phase=="DELAY":
            delay_left-=1
            if delay_left<=0: phase="FIT"
        elif phase=="FIT":
            fit_x.append(x[t].copy()); fit_y.append(y[t].copy())
            if len(fit_x)==FIT_STEPS:
                candidate=_fit(np.asarray(fit_x),np.asarray(fit_y))
                if policy=="immediate_revision":
                    active=candidate; promoted=True; promotion_step=t; phase="COMPLETE"
                else: phase="VALIDATION"
        elif phase=="VALIDATION":
            rc=y[t]-candidate@x[t]; ri=y[t]-incumbent@x[t]
            val_c+=float(rc@rc); val_i+=float(ri@ri); val_n+=1
            if val_n==VALIDATION_STEPS:
                if val_c<val_i: active=candidate; promoted=True; promotion_step=t
                phase="COMPLETE"
    pf=float(np.mean(post_fixed)); pp=float(np.mean(post_policy))
    improvement=(pf-pp)/pf if pf>0 else None
    return {"policy":policy,"detector_threshold":float(detector_threshold),"environment":stream["environment"],"world_seed":stream["world_seed"],
            "replicate_seed":stream["replicate_seed"],"alarm_step":alarm,
            "detection_delay_steps":int(alarm-CHANGE_START) if alarm is not None and stream["environment"]!="stable" else None,
            "false_alarm":bool(false_alarm),"promoted":bool(promoted),"promotion_step":promotion_step,
            "post_change_fixed_mse":pf,"post_change_policy_mse":pp,
            "post_change_relative_improvement":improvement,"overall_fixed_mse":float(np.mean(fixed_losses)),
            "overall_policy_mse":float(np.mean(policy_losses)),
            "validation_candidate_mse":val_c/val_n if val_n else None,
            "validation_incumbent_mse":val_i/val_n if val_n else None,
            "prequential_prediction_before_feedback":True}

def run_environment(worlds, environment, detector_threshold=8.0):
    rows=[]
    for world in worlds:
        if world.get("split")!="test": raise ValueError("G3 may use held-out test worlds only")
        for seed in world["replicate_seeds"]:
            stream=generate_stream(world_seed=int(world["world_configuration_seed"]),replicate_seed=int(seed),
                environment=environment,noise_std=NOISE_STD*float(world.get("factor_profile",{}).get("observation_noise_multiplier",1)))
            rows.extend(evaluate_policy(stream,p,detector_threshold=detector_threshold) for p in POLICIES)
    grouped={p:[r for r in rows if r["policy"]==p] for p in POLICIES}
    fixed={(r["world_seed"],r["replicate_seed"]):r for r in grouped["no_revision"]}
    revised={(r["world_seed"],r["replicate_seed"]):r for r in grouped["validated_revision"]}
    effects=[]
    for w in worlds:
        vals=[]
        for seed in w["replicate_seeds"]:
            a=fixed[(int(w["world_configuration_seed"]),int(seed))]["post_change_fixed_mse"]
            b=revised[(int(w["world_configuration_seed"]),int(seed))]["post_change_policy_mse"]
            if a>0: vals.append((a-b)/a)
        if vals: effects.append(float(np.mean(vals)))
    summary={}
    for p,values in grouped.items():
        delays=[r["detection_delay_steps"] for r in values if r["detection_delay_steps"] is not None]
        gains=[r["post_change_relative_improvement"] for r in values if r["post_change_relative_improvement"] is not None]
        summary[p]={"stream_count":len(values),"promotion_count":sum(r["promoted"] for r in values),
            "alarm_count":sum(r["alarm_step"] is not None for r in values),
            "false_alarm_count":sum(r["false_alarm"] for r in values),
            "mean_detection_delay_steps":float(np.mean(delays)) if delays else None,
            "mean_post_change_relative_improvement_vs_fixed":float(np.mean(gains)) if gains else None,
            "mean_post_change_policy_mse":float(np.mean([r["post_change_policy_mse"] for r in values])),
            "mean_post_change_fixed_mse":float(np.mean([r["post_change_fixed_mse"] for r in values]))}
    evidence={"campaign_id":CAMPAIGN_ID,"environment":environment,"world_count":len(worlds),
        "stream_count":sum(len(w["replicate_seeds"]) for w in worlds),"policy_arm_count":len(POLICIES),"detector_threshold":float(detector_threshold),
        "policy_summary":summary,"validated_revision_vs_no_revision_world_clustered_effect":_cluster_ci(effects),
        "paired_world_effects":[{"world_seed":int(w["world_configuration_seed"]),"relative_improvement":v} for w,v in zip(worlds,effects)],
        "streams":rows,"claim_ceiling":"Controlled synthetic adaptation diagnostic on held-out world identities; not general relational discovery, causal attribution, or M4 stability.",
        "integrity":{"held_out_test_worlds_only":True,"paired_world_and_replicate_seeds":True,
            "same_streams_across_policy_arms":True,"prequential_prediction_before_feedback":all(r["prequential_prediction_before_feedback"] for r in rows),
            "g2_protocol_and_results_unchanged":True}}
    evidence["evidence_sha256"]=_hash(evidence)
    return evidence


def calibrate_detector_threshold(fit_worlds, validation_worlds, candidate_thresholds=(8,12,16,20,24,32,48,64)):
    """Select detector threshold on development-fit stable streams; verify on validation."""
    def rate(worlds, threshold):
        alarms=0; total=0
        for world in worlds:
            if world.get("split") not in {"development_fit","development_validation"}:
                raise ValueError("calibration may use development worlds only")
            for seed in world["replicate_seeds"]:
                stream=generate_stream(world_seed=int(world["world_configuration_seed"]),
                    replicate_seed=int(seed),environment="stable",
                    noise_std=NOISE_STD*float(world.get("factor_profile",{}).get("observation_noise_multiplier",1)))
                result=evaluate_policy(stream,"validated_revision",detector_threshold=float(threshold))
                alarms += int(result["alarm_step"] is not None); total += 1
        return alarms/total if total else 1.0
    thresholds=sorted({float(v) for v in candidate_thresholds})
    if not thresholds or any(v<=0 for v in thresholds): raise ValueError("candidate thresholds must be positive")
    fit_rates=[{"threshold":t,"false_alarm_rate":rate(fit_worlds,t)} for t in thresholds]
    eligible=[r for r in fit_rates if r["false_alarm_rate"]<=0.05]
    selected=eligible[0]["threshold"] if eligible else thresholds[-1]
    validation_rate=rate(validation_worlds,selected)
    return {"campaign_id":CAMPAIGN_ID,"calibration":"stable_negative_control",
        "selected_threshold":selected,"fit_false_alarm_rate":next(r["false_alarm_rate"] for r in fit_rates if r["threshold"]==selected),
        "validation_false_alarm_rate":validation_rate,"fit_threshold_sweep":fit_rates,
        "fit_world_count":len(fit_worlds),"validation_world_count":len(validation_worlds),
        "calibration_passed":bool(next(r["false_alarm_rate"] for r in fit_rates if r["threshold"]==selected)<=0.05 and validation_rate<=0.05),
        "test_worlds_used":False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--environment",choices=ENVIRONMENTS)
    parser.add_argument("--detector-threshold",type=float)
    parser.add_argument("--calibrate",action="store_true")
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args(); manifest=json.loads(args.manifest.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True,exist_ok=True)
    if args.calibrate:
        fit=[w for w in manifest["worlds"] if w["split"]=="development_fit"]
        validation=[w for w in manifest["worlds"] if w["split"]=="development_validation"]
        if len(fit)!=12 or len(validation)!=8: raise ValueError("G3 calibration requires frozen 12/8 development worlds")
        report=calibrate_detector_threshold(fit,validation)
        report["evidence_sha256"]=_hash(report)
        path=args.output_dir/"detector_calibration.json"
        path.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        print(json.dumps(report,sort_keys=True))
        if not report["calibration_passed"]: raise SystemExit("G3 detector calibration failed; held-out environments not launched")
        return
    if args.environment is None or args.detector_threshold is None:
        raise ValueError("--environment and --detector-threshold are required outside calibration")
    worlds=[w for w in manifest["worlds"] if w["split"]=="test"]
    if len(worlds)!=20 or any(len(w["replicate_seeds"])!=5 for w in worlds):
        raise ValueError("G3 requires the frozen 20 held-out worlds × 5 replicate seeds")
    evidence=run_environment(worlds,args.environment,detector_threshold=args.detector_threshold)
    path=args.output_dir/f"{args.environment}.json"
    path.write_text(json.dumps(evidence,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"campaign_id":CAMPAIGN_ID,"environment":args.environment,
        "world_count":evidence["world_count"],"stream_count":evidence["stream_count"],
        "detector_threshold":evidence["detector_threshold"],
        "validated_effect":evidence["validated_revision_vs_no_revision_world_clustered_effect"],
        "evidence_sha256":evidence["evidence_sha256"]},sort_keys=True))

if __name__=="__main__": main()
