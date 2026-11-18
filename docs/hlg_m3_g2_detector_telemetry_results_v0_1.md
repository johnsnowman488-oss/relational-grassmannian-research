# HLG-M3 G2 detector telemetry replay — v0.1 results

**Replay workflow:** [44345211564](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44345211564)  
**Replay implementation commit:** `a1392d1f94ea1aa881d4a83e5b43cf64bbdbe7e4`  
**Original G2 execution:** [44146576208](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44146576208)  
**Original G2 execution commit:** `65b3db7a8a548bbc0c08bca477d34ab88b80895f`  
**Frozen manifest SHA-256:** `8548f2a72de09a81f79a57a19b3cd8196dbeae185db9432619e6ac5cc2f49101`  
**Telemetry evidence SHA-256:** `748e0731d906ccb122c8b5bd53dc7522f0e153444f3898c27d98e3fb2a55f194`

## 1. Replay integrity

The telemetry-only replay rebuilt the fit and validation learner states in frozen manifest order, then replayed the 100 held-out test streams from independent copies of the capacity-matched development state. It retained the original detector settings (CUSUM allowance 0.25, threshold 5.0) and did not tune on test outcomes.

The replay reproduced the original M3-D package totals exactly:

- 2,592 detector alarms.
- 98/100 test streams with at least one alarm.
- Alarm totals by drift family: stationary 765; gradual 545; step 317; transient 203; variance-only 372; compound 390.
- Candidate lifecycle outcomes: 29 insufficient fit evidence, 50 insufficient validation evidence, 16 rejected, 1 in progress, and 2 promoted/evaluated.
- Two candidate revisions applied to the shared fallback operator.

The run emitted event-level alarm timestamps, per-update standardized innovation/CUSUM traces, evaluator-only scheduled change events, detection delays, pre-drift alarm counts, and candidate lifecycle records. Python 3.10 and 3.12 full test suites passed; the aggregate verified the evidence hash and the original M3-D totals.

## 2. Stationary negative control

| Measurement | Result |
|---|---:|
| Streams / world configurations | 20 / 4 |
| Total test steps | 12,000 |
| Detector updates | 10,145 |
| Streams with at least one alarm | **20/20 (100%)** |
| Alarm events | **765** |
| Alarms per 1,000 test steps | **63.75** |
| Alarms per 1,000 eligible detector updates | **75.41** |
| Candidate promotions | 0 |

This is a clear detector-calibration failure in the frozen G2 benchmark. Every stationary stream produced at least one alarm. The event-level replay therefore confirms that G2's alarm volume is not merely a reporting artefact.

## 3. Change-family diagnostics

| Drift family | Streams | Streams with post-change detection | Missed changes | Pre-drift alarm events | Detection delay (mean / median / p90 steps) | Candidate promotions |
|---|---:|---:|---:|---:|---:|---:|
| Gradual | 15 | 15 | 0 | 110 | 32.07 / 12 / 98.8 | 0 |
| Step | 20 | 19 | 1 | 49 | 49.95 / 8 / 118 | 0 |
| Transient | 15 | 15 | 0 | 43 | 32.67 / 18 / 106 | 1 |
| Variance-only | 15 | 14 | 1 | 58 | 31.36 / 24.5 / 70.7 | 1 |
| Compound | 15 | 15 | 0 | 69 | 25 / 16 / 31.2 | 0 |

The 329 pre-drift alarm events across nonstationary streams are reported separately. They are alarms before the benchmark's scheduled within-context drift event; they are **not automatically false alarms**, because earlier context and relation phases contain their own real transitions.

Two additional distinctions matter:

- For transient change, only 5/15 streams were first detected before the scheduled reversion; 10/15 first detections arrived after the transient had already reverted.
- For compound change, only 4/15 streams were first detected before the scheduled variance increase.

The detector therefore raises alarms frequently, but alarm timing is not reliably aligned with the relevant change event.

## 4. Candidate lifecycle

Only **2/100** test streams reached promoted-and-evaluated status. Most streams lacked sufficient evidence to complete the candidate lifecycle:

- 29/100: insufficient fitting evidence.
- 50/100: insufficient validation evidence.
- 16/100: rejected.
- 1/100: still in progress.
- 2/100: promoted and evaluated.

This explains why a high alarm count does not translate into useful adaptation. Detection, candidate fitting, independent validation, promotion, and future benefit remain separate gates.

## 5. Interpretation and boundaries

The replay strengthens the diagnosis behind G2's failed adaptation gate:

1. The stationary negative control is severely over-triggered (20/20 streams, 765 alarms).
2. Nonstationary streams also have many alarms before the scheduled within-context drift; these require event-relative interpretation rather than blanket false-alarm labels.
3. Detection delay is long-tailed for step and transient conditions, and many transient detections occur after reversion.
4. Candidate lifecycle evidence is the bottleneck after detection: only two candidates were promoted and evaluated.

No detector threshold was changed, no G2 result was recalculated, and no held-out outcome was used for tuning. G2 remains at its original scientific status: capability and resource gates passed; adaptation gate failed; M3 remains open; M4 is not authorised.

The G3-v0.3 threshold of 24 belongs only to the separate controlled G3 diagnostic. It must not be substituted for G2's frozen threshold 5.0 or described as a repair of G2.

This artifact is a deterministic telemetry replay of the original test allocation, not a new confirmatory sample or a new performance claim.
