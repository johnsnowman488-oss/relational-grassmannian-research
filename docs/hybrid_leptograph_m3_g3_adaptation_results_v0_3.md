# HLG-M3 G3 adaptation diagnostic — v0.3 results

**Campaign:** `HLG-M3-G3-ADAPTATION-v0.3`  
**Canonical workflow:** [44343380057](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44343380057)  
**Implementation commit:** `5a7c03fbc85944e851c18a91903273a320e380eb`  
**Calibration manifest SHA-256:** `9fb952f87bc014cbd1caf156a801bebeb9ece5606da17bff4e5b72ef11b4f59d`

## 1. Execution and calibration

The v0.3 calibration gate passed before any held-out environment job ran.

| Calibration item | Result |
|---|---:|
| Fit worlds / streams | 12 / 60 |
| Fresh validation worlds / streams | 8 / 40 |
| Selected threshold | **24** |
| Fit false alarms | 0/60 (0%) |
| Fresh validation false alarms | 0/40 (0%) |
| Test-world outcomes used for calibration | No |

Threshold 24 was the lowest threshold in the predeclared grid with zero observed fit false alarms. The same threshold was frozen for all environments.

All three environment jobs and the aggregate evidence verifier passed. Python 3.10 and Python 3.12 each passed the complete 302-test suite. The aggregate verified three environments, 20 held-out worlds × five replicate seeds per environment, four policy arms, 1,200 policy evaluations, and the prequential/paired-stream integrity flags.

The first v0.3 attempt is retained as a failed implementation-validation attempt: calibration and environment jobs passed, but a new unit-test fixture lacked its required `world_id`. The fixture alone was corrected; no scientific code, manifest, threshold, or seed changed. The canonical successful run is the workflow above. The first attempt is not pooled as a separate scientific replicate.

## 2. Main results

The comparison below is validated revision against no revision, paired by world and replicate seed. Intervals are 95% bootstrap intervals over 20 held-out world-cluster means.

| Environment | Validated revision relative improvement | 95% world-clustered interval | Positive worlds | Validated promotions |
|---|---:|---:|---:|---:|
| Stable | approximately 0% | approximately 0% | 0/20 strictly positive; numerical effects are round-off around zero | 0/100 |
| Gradual | **49.07%** | **46.13% to 51.90%** | **20/20** | **100/100** |
| Abrupt | **78.63%** | **76.56% to 80.33%** | **20/20** | **100/100** |

### Stable negative control

- No detector alarms in any policy arm (0/100 per revision arm).
- No candidate promotions.
- All policies retain the incumbent.
- The near-zero effect is the expected negative-control outcome, not a failure to adapt.

### Gradual change

- 100/100 streams alarmed in each revision-enabled policy arm; no pre-change alarms were observed.
- Mean detection delay: **38.61 steps** (range 15–85).
- Validated revision promoted in 100/100 streams.
- Mean post-change loss: no revision **0.12447**; immediate revision **0.06206**; validated revision **0.06557**; delayed validated revision **0.04520**.
- Delayed validated revision performed best in this gradual regime, consistent with fitting later in the moving trajectory.

### Abrupt change

- 100/100 streams alarmed in each revision-enabled policy arm; no pre-change alarms were observed.
- Mean detection delay: **1.14 steps** (range 0–13).
- Validated revision promoted in 100/100 streams.
- Mean post-change loss: no revision **0.17521**; immediate revision **0.02081**; validated revision **0.03614**; delayed validated revision **0.05128**.
- Immediate revision performed best in this abrupt regime; the extra validation/delay time carries a recovery cost.

## 3. Interpretation

The original uncertainty about whether adaptation can activate under a suitable task is now narrowed:

1. The detector remained inactive in the stable negative control.
2. It activated in all gradual and abrupt streams after the programmed change, with no observed pre-change alarms.
3. The validated candidate passed its separate validation window and was promoted in every changed stream.
4. The post-change loss comparison was positive in all 20 held-out worlds for both changed environments.

This is evidence that the implemented adaptation path can activate selectively and improve prediction in these controlled synthetic change regimes. It does **not** overturn G2's failed adaptation gate. G2's broader 200-stream adaptation result remains negative: -0.28% mean improvement, 0/20 positive worlds, and only two promoted/evaluated streams. G3 is a targeted diagnostic with a deliberately supplied change schedule and a different, controlled two-dimensional task.

## 4. Metric and claim limits

The reported G3 post-change loss averages cover all observations from the scheduled change start (step 160) through the end of the stream. They include detection latency, candidate fitting, validation, and post-promotion observations; they are not a pure untouched post-promotion-only endpoint. This makes the comparison sensitive to adaptation delay, but it must not be relabelled as the frozen G2 post-promotion adaptation metric.

The experiment does not establish:
- general adaptation across arbitrary environments or relational tasks;
- a universal policy winner (the best policy differed between gradual and abrupt change);
- causal attribution;
- broad stability of the coupled adaptive system;
- completion of the M3 scientific decision-report gate or authorisation for M4.

G2 artifacts, thresholds, results, and the M3/M4 exit criteria remain unchanged. The next outstanding work is the separately scoped deterministic G2 detector-telemetry replay and the reporting-only correction to the stale G2 readiness status.
