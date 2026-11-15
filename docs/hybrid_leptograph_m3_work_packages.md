# HLG-M3 six work-package execution briefs

**Campaign:** HLG-M3-IMPLEMENTATION-v0.1  
**Parent contract:** docs/hybrid_leptograph_m3_implementation_protocol_v0_1.md  
**Execution:** M3-A through M3-E in parallel; M3-I after component jobs

## M3-A — Context memory

**Question:** Can context retrieval be metric-aware, bounded and honest about ambiguity?

Implement a bounded bank of context slots. Each slot retains a prototype, covariance/scatter and observation count. Score candidates with a regularised metric-aware distance plus generalised covariance-volume term. Return exactly one of ACCEPT, ABSTAIN or NOVEL. Repeated novelty may create a slot. A full bank must abstain without overwriting an accepted slot.

Required probes: separated contexts, near-duplicates, novel contexts, full-bank overflow, transported non-orthogonal coordinate systems, singular/ill-conditioned input rejection. Record thresholds as provisional calibration parameters.

Known limitation: the first reference score is not a calibrated probability and its Gaussian/covariance assumptions require wider evaluation.

## M3-B — Joint relational learning

**Question:** Does the actual online predictor use every eligible heterogeneous incoming source?

Implement fixed-key source feature assembly with dimension checks, context nuisance features and intercept. Maintain regularised online sufficient statistics. Separate predict and update operations so predictions precede target observation. Provide source-ablation marginal predictive loss contributions and condition/rank diagnostics.

Required probes: at least two source groups of different dimensions, a nuisance context stream, correlated and redundant sources, missing/invalid-source rejection, pre-update target perturbation, stable solve and recovery of a synthetic multi-source map.

Known limitation: ablation is predictive attribution, not causal attribution. Ridge regularisation cannot turn a rank-deficient source configuration into an identified relationship.

## M3-C — Evidence and activation

**Question:** Can historical support, recent usefulness, sufficiency and activation remain distinct?

Maintain positive and negative predictive-evidence masses, usefulness, observation count, uncertainty proxy and activation state. Use separate on/off thresholds. Missing observations leave evidence unchanged. Context fit and conditional identifiability gate activation. Dormant status cannot delete or shrink the stored relationship operator.

Required probes: acquire, persist, negative evidence, dormancy, reactivation, missing observations, unidentifiable relation and context mismatch. Include noisy boundary sweeps and multiple relation IDs in later integration tests.

Known limitation: the first scalar evidence/uncertainty calibration is provisional and must be tested against multiple scoring scales.

## M3-D — Revision and adaptation

**Question:** Can the system react to persistent change without replacing accepted knowledge prematurely?

Implement a residual detector with configurable allowance/threshold and an isolated candidate operator. Candidate evaluation uses validation/prequential loss, an identifiability gate and an explicit improvement margin. Rejection preserves the incumbent exactly; promotion changes the accepted version only after all gates pass.

Required probes: stationary false alarms, abrupt and gradual change, variance/transient disturbances, candidate non-improvement, non-identifiability, successful promotion, and collateral effects on unrelated relations.

Known limitation: an initial CUSUM mean-shift probe is not general drift detection. Detector calibration is distribution- and schedule-specific.

## M3-E — Memory architecture controls

**Question:** What do separate and unified memory architectures actually cost and preserve?

Implement C0 no persistent memory; C1 mode-only; C2 relationship-only; C3 independent mode/relationship stores; C4 one genuinely shared latent state with common write dynamics and distinct readouts. Count persistent state bytes, trainable parameter count and bytes, observed update multiply-adds and query multiply-adds. Include observation masks and state precision in records.

Required probes: memory retention/interference tasks, relationship reacquisition, context transfer, cross-channel interference and matched-resource Pareto comparisons.

Known limitation: the initial implementation slice only instruments concrete reference controls. It does not rank their task performance. A unified C4's readout parameters must be included in its budget.

## M3-I — Integrated heterogeneous learner

**Question:** Do the components operate coherently under one sequential event protocol?

Connect M3-A through M3-E with a learner/evaluator boundary. For each step: receive inputs; route context; retrieve applicable stored relations; predict with all eligible sources; observe and score target; update estimator/evidence; update activation; detect change; evaluate candidate; record state and metrics.

Required probes: context switch, mixed source dimensions, source correlation, observation gap, dormancy/reactivation, operator drift, candidate rejection/promotion, memory resources and geometry checks.

The first integrated smoke world is an interface/ordering probe only. Full M3 evidence requires independent worlds/seeds, held-out compositions and the broader task schedule.

## Shared return contract

Each package emits one JSON file with campaign_id, package_id, execution_passed, measurements, interpretation and limitations. Each package owns its output path and does not write a shared summary. The integration job runs only after M3-A through M3-E complete. The aggregate verifies exactly six package records and preserves implementation_protocol_frozen=false.

A green package job means only that its declared implementation and checks executed successfully. Failed scientific probes are valid research findings and must not be hidden by turning the aggregate green.
