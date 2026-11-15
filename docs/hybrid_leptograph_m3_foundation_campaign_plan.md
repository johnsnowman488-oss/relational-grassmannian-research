# HLG-M3 foundation — seven-job mathematical design campaign

**Campaign:** HLG-M3-FOUNDATION-F1-F7-v0.1  
**Status:** concurrent design validation; not implementation authorisation

## Objective

Challenge the proposed HLG-M3 foundation through seven independent mathematical/reference workstreams. Reuse M0-M2 foundations, respect M1 inner-product metric transport, and separate individual parameter boundedness from M4 global adaptive stability.

## Job allocation

| Job | Workstream | Mathematical deliverable | Executable probe |
|---|---|---|---|
| F1 | Prequential evidence and attribution | Marginal predictive contribution, no-leakage order, missing-target semantics and confounding boundary | True relation vs null decoy; independent vs correlated source excitation |
| F2 | Metric-aware operator estimation | Whitened multi-output ridge estimator, coordinate transformation and conditional information Schur complement | Recover heterogeneous operators; transform input/output charts; test rank-deficient sources |
| F3 | Context memory | Metric-invariant regularised Mahalanobis/Gaussian scores, accept/abstain/novel decision and bounded capacity | Separated, ambiguous and novel contexts under invertible coordinate changes |
| F4 | Evidence, activation and revision | Pseudo-count/update bounds, no-observation semantics, hysteresis and two-phase revision obligations | Evidence sweeps, no-data interval, threshold chatter and change detection challenge |
| F5 | Architecture comparison | C0-C4, equal state-byte/precision budgets and matched parameter/update/query compute envelope | Check budget accounting and comparison eligibility; no winner selection |
| F6 | Integrated benchmark | Deterministic worlds, task phases, learner/evaluator boundary and leakage-safe splits | Generate and audit reference sequential task manifest |
| F7 | Independent adversarial review | Metric invariance, attribution, identifiability, storage/activation separation and M4 boundary | Coordinate-norm countercheck, collinear-source counterexample, switched-system example |

## Execution independence

Each workstream runs in its own GitHub Actions matrix instance and writes only its matching F1-F7 JSON evidence. No job edits shared source or consumes another job's intermediate result. The matrix uses fail-fast false and permits seven concurrent case jobs. The existing full repository suite runs in parallel on Python 3.10 and 3.12.

The aggregate waits for all design jobs and test-matrix jobs, verifies exact case identity/completeness and writes summary.json. Missing, malformed, duplicated or failed case evidence fails aggregation.

## Interpretation

A job's execution_passed field means its pre-registered reference calculations and internal assertions completed. It does not imply every mechanism is scientifically established. Each result contains design findings and caveats.

The aggregate must report:
- all seven workstreams executed;
- both supported full-suite test jobs passed;
- unresolved design choices and caveats;
- implementation_protocol_frozen=false;
- campaign_decision=REVIEW_F1_F7_RESULTS_BEFORE_FREEZE.

The research review must examine the evidence before HLG-M3 implementation protocol v1.0 is authored. No production M3 API or runtime is part of this campaign.
