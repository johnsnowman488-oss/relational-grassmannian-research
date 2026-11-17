# HLG-M3 implementation campaign results v0.1

**Campaign:** HLG-M3-IMPLEMENTATION-v0.1  
**Canonical Actions run:** [43770581840](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43770581840)  
**Branch head at execution:** 721488a1e5ad8614658f9c166774fc6795c2a3e5  
**Status:** six package executions passed; both full test matrices passed; first integrated smoke executed  
**Scientific status:** M3 investigation ongoing; no final validation or architecture selection

## 1. Execution record

The initial run [43770332617](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43770332617) exposed one implementation defect. M3-B returned a NumPy boolean in its JSON result, and its source-coefficient diagnostic used overlapping coefficient slices despite the estimator's sorted source-key order. The same boolean type caused the only full-suite failure on both Python versions: 249 passed, one failed.

The correction added source-keyed coefficient-block norms to the estimator and explicitly serialised the package result as a Python bool. The corrected canonical run [43770581840](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43770581840) completed successfully:

- M3-A, M3-B, M3-C, M3-D and M3-E all executed concurrently and uploaded their own evidence.
- M3-I ran after all five component jobs and uploaded its integration evidence.
- The full repository suite passed **250 tests on Python 3.10** and **250 tests on Python 3.12**.
- The aggregate verified the exact six package IDs and uploaded summary artifact **14184326850**.
- Package evidence artifacts: M3-A **14183648034**; M3-B **14184465783**; M3-C **14183873419**; M3-D **14183144736**; M3-E **14184460816**; M3-I **14183953243**.

This is successful execution of the declared v0.1 package checks and tests. It is not evidence that every M3 mechanism works in a fully coupled adaptive learner.

## 2. Work-package findings

### M3-A — Context memory

- Generalised metric context score before/after a non-orthogonal coordinate transformation: **0.16550626382774802** in both coordinates.
- Absolute score invariance error: **0.0**.
- A near-prototype query was accepted.
- Package execution passed.

Interpretation: the fixed reference case supports the transported-metric score implementation. It does not calibrate acceptance thresholds, prove robust identity matching, or cover high-dimensional/ill-conditioned transformations.

### M3-B — Joint heterogeneous relational learning

- **700** sequential predict-then-update samples.
- Feature dimension **8**: source groups of dimensions 2 and 3, two context features and an intercept.
- Final 100-sample mean squared prediction error: **0.0001089612976978075**.
- Source coefficient-block norms: small_group **1.0248872231413257**, large_group **0.402169893235602**.
- Marginal predictive loss contributions on the final probe: small_group **2.660849630067426**, large_group **0.17904339617628703**.
- Sufficient-statistic storage: **640 bytes**; parameter count **16**; per-update outer-product workload **80 multiply-adds**; query workload **16 multiply-adds**.
- Package execution passed.

Interpretation: both heterogeneous source blocks participate nontrivially in the fitted predictor, addressing the previous R2 primary-source-only gap. The contribution values are predictive ablation diagnostics, not causal effects. This probe does not establish conditional identifiability under severe correlation or held-out generalisation.

### M3-C — Evidence and activation

- Positive evidence sequence activated the relation.
- Missing observation left the evidence state unchanged.
- Subsequent negative evidence deactivated the relation.
- Final observation count **32**; final evidence balance **-0.9984938867894133**; final usefulness **-0.9999306046175888**.
- Package execution passed.

Interpretation: basic state transitions and no-observation semantics work in this scalar reference sequence. Threshold calibration, noisy boundary behaviour, simultaneous relation groups and reactivation after long gaps remain open.

### M3-D — Change detection and candidate revision

- Stationary reference stream: **0** alarms.
- Shifted reference stream: **2** alarms.
- Non-improving candidate was rejected.
- Accepted operator was preserved on rejection.
- Identifiable improving candidate was promoted.
- Package execution passed.

Interpretation: the two-phase candidate gate works on this bounded reference stream. This is not broad CUSUM calibration; gradual drift, variance shifts, transients, multiple change points and confidence intervals remain open.

### M3-E — C0-C4 memory controls

Observed resource snapshots (float64):

| Control | State bytes | Parameter count | Parameter bytes | Update multiply-adds | Query multiply-adds | Total persistent bytes |
|---|---:|---:|---:|---:|---:|---:|
| C0 | 0 | 0 | 0 | 0 | 0 | 0 |
| C1 | 512 | 0 | 0 | 4 | 0 | 512 |
| C2 | 512 | 0 | 0 | 4 | 0 | 512 |
| C3 | 512 | 0 | 0 | 8 | 0 | 512 |
| C4 | 512 | 256 | 2048 | 896 | 256 | 2560 |

- All five reference controls produced distinct resource records.
- C4 has a shared latent state and two readouts.
- Package execution passed.

Interpretation: accounting now includes C4 readout parameters, as required by R5. The evidence reveals that C4 is **not resource matched** to C1-C3 at this setting: it uses 2,560 persistent bytes versus 512. Therefore no memory-architecture performance ranking or fairness claim is permitted. C4 needs budgeted readouts or a Pareto-matched comparison before task-performance results can be compared.

### M3-I — Integrated heterogeneous learner smoke

- **240** sequential steps; source groups of dimensions **2** and **3**.
- Both source groups were used; prediction preceded target scoring/update.
- Mean squared prediction error: **0.046685175223886606**.
- Last-20-step mean squared error: **0.0741768302055926**.
- Mean group-A and group-B marginal predictive contributions: **1.240781276726867** and **0.13779383159115416**.
- Context decisions: **237 ACCEPT**, **0 ABSTAIN**, **3 NOVEL**; final context slots **2**.
- Relationship A active at end.
- Integrated residual detector alarms: **0**.
- Candidate revision: **not started**, with **0 promotions** and **0 rejections**.
- Package execution passed.

Interpretation and integration limitations:

1. The context switch and operator-change schedule ran, but the configured integrated residual detector raised no alarm. Thus this integration run did not exercise candidate revision. M3-D's isolated reference probe did exercise that gate, but the complete lifecycle has not yet been demonstrated end to end.
2. The current smoke harness records activation state but does not yet use that state to mask or scale the corresponding source's effective routing contribution.
3. Context decisions are observed and recorded, but the smoke harness still supplies the raw context feature vector to the estimator even when context routing is NOVEL or ABSTAIN. No ABSTAIN occurred in this run, but the input-gating contract still needs to be implemented explicitly.
4. The C3/C4 resource counters in this smoke confirm the same budget mismatch found in M3-E.
5. The late-window error is higher than the overall mean; no baseline or held-out control has been run to determine whether the operator-change response is adequate.

Consequently, M3-I is an interface and event-ordering smoke, not yet a fully coupled adaptive learner.

## 3. Decisions and next work

**Accepted from this run:**

- The six-work-package concurrency/dependency structure executes.
- The initial component interfaces are executable.
- M3-B's predictor genuinely includes both heterogeneous source blocks in its actual prediction.
- Context-score coordinate invariance held in the tested non-orthogonal reference transformation.
- Basic evidence/no-observation and candidate-gate semantics passed their declared probes.
- Resource instrumentation correctly exposes C4's additional parameter cost.

**Do not conclude:**

- M3 is scientifically validated.
- C0-C4 have been compared fairly or a memory architecture has won.
- The complete context/activation/revision lifecycle is integrated.
- Relation attribution is causal.
- The learner generalises to held-out compositions.
- Global adaptive-network stability has been established.

**Next implementation refinement before broad M3 benchmark:**

1. Make context decisions operational: only ACCEPT (or a newly admitted NOVEL slot after its repeat criterion) supplies context-conditioned features; unresolved NOVEL and ABSTAIN must not leak raw context into the estimator.
2. Connect effective activation to actual route prediction while preserving a controlled counterfactual path for evaluating dormant candidates.
3. Connect candidate operator estimation, validation and promotion/rejection to the same relationship operator used by the learner.
4. Calibrate the integrated detector on stationary validation streams and verify detection of the known operator change without using evaluator phase labels.
5. Budget C4's latent state and readouts against C1-C3, or report a measured Pareto frontier instead of equal-resource claims.
6. Expand to independent worlds/seeds, correlation sweeps, noisy context boundaries, long observation gaps, gradual/variance/transient drift and held-out relation compositions.

The protocol remains **v0.1, amendable and not frozen**. These findings are part of the M3 investigation, not a reason to return to a pre-M3 hold.
