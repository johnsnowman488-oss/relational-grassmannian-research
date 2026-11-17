# HLG-M3 implementation protocol v0.1

**Protocol:** HLG-M3-IMPLEMENTATION-v0.1  
**Status:** adopted working protocol; M3 investigation authorised; protocol remains versioned and amendable  
**Date:** 2026-11-15  
**Prerequisites:** HLG-M0, HLG-M1 and HLG-M2 completed; HLG-M3 foundation and F1-F7/R1-R5 design campaigns reviewed  
**Scope:** fixed candidate topology; heterogeneous relational learning, contextual memory, evidence, activation, adaptation and memory controls

## 1. Authorisation and evidence boundary

The earlier M3 preflight and mathematical design campaigns are complete. The F1-F7 and R1-R5 findings establish sufficient grounds to proceed with genuine M3 investigation. This protocol therefore authorises implementation and execution. It does **not** declare the architecture mathematically final, freeze all hyperparameters, or claim that M3 has succeeded.

The earlier preflight, foundation and refinement artifacts remain historical evidence and are not rewritten. This protocol supersedes their earlier *operational hold* only. Their scientific limitations remain binding.

M3 is an investigation of adaptive learning over a supplied, fixed candidate topology. It does not claim autonomous relation birth/death, open-ended topology discovery, or topology reorganisation. Those questions are outside this milestone. Whole-network coupled adaptive stability is M4.

## 2. Adopted architectural commitments

The adopted HLG-M3 foundation is retained:

1. Heterogeneous mode groups use finite-dimensional inner-product spaces \(\mathcal E_g\simeq\mathbb R^{d_g}\).
2. Directed relationships use dimension-compatible operators \(\Theta_e:\mathcal E_i\rightarrow\mathcal E_j\); reverse directions are independent.
3. M1 coordinate/metric covariance and M2 routing/information-preservation requirements remain in force.
4. Stored relationship knowledge, historical evidence, context applicability and current route activation are different state roles.
5. A dormant route remains stored. Deactivation is not forgetting or deletion.
6. Context decisions are explicitly ACCEPT, ABSTAIN, or NOVEL. A full bounded context bank abstains; it does not silently evict.
7. Learning is prequential: predict first, observe target second, score the prediction third, and only then update estimator/evidence state.
8. Relationship attribution is predictive marginal contribution, not causal attribution. Correlated or non-identifiable sources must be flagged.
9. Revision is two-phase: accepted operator remains available while a bounded candidate is evaluated; promotion requires identifiability and held-out predictive improvement.
10. C0-C4 are competing reference architectures. No winner is selected before measured task and resource comparisons.

## 3. Shared interface contract (M3-0)

The implementation uses NumPy arrays and explicit source identifiers. A source group has a stable key, declared vector dimension and associated coordinate metric. A relationship estimator receives every eligible declared source for a prediction; missing a declared source is an input error unless a future version explicitly defines masking semantics.

The initial predictor is additive and linear in the chosen feature map:

\[
\widehat y_{t+1}=W_m\,\phi_t+\varepsilon_t,\qquad
\phi_t=[x_{1,t}^{\top},\ldots,x_{q,t}^{\top},c_t^{\top},1]^{\top}.
\]

This is a first executable reference, not a claim that additive linear structure is generally sufficient. Context features are nuisance predictors and must not be confused with learned relationships. Estimation uses regularised sufficient statistics and stable linear solves, not explicit matrix inversion in the online update path.

The event envelope for each observed step is conceptually:

- step/time identifier;
- source-group mapping with exact dimensions;
- current context feature vector and context decision;
- prediction produced from state strictly before the current target;
- optional target and observation mask;
- prequential loss and per-source ablation diagnostics, when observed;
- estimator/evidence/activation/revision updates;
- versioned learner state and provenance record.

### Event order

\[
\text{observe inputs}\rightarrow\text{resolve context}\rightarrow\text{retrieve}\rightarrow
\text{predict}\rightarrow\text{observe target}\rightarrow\text{score}\rightarrow
\text{update estimator/evidence}\rightarrow\text{activation}\rightarrow
\text{change detection}\rightarrow\text{candidate evaluation}\rightarrow\text{record}.
\]

The prediction object must be created before target-dependent updates. An observation mask of false causes no negative evidence update. Evaluator truth, planted parameters, future observations, split labels, and benchmark phase labels must not be exposed to learner code.

## 4. Six work packages

The five component packages M3-A through M3-E run independently and concurrently. M3-I integrates their public interfaces after the component package jobs complete. All six are part of this implementation campaign.

| Package | Responsibility | Owned outputs | Key obligation |
|---|---|---|---|
| M3-A | Context memory | Metric-aware context bank, slot update, novelty accumulation and abstention | Invariance under nonsingular coordinate changes; no silent eviction |
| M3-B | Joint relational learning | Heterogeneous online estimator, prequential prediction/update, source ablation diagnostics | All eligible sources participate in prediction; conditional identifiability is not manufactured by ridge |
| M3-C | Evidence and activation | Positive/negative evidence, sufficiency, usefulness, uncertainty gate and hysteresis | Missing observations are neutral; activation does not erase stored operators |
| M3-D | Revision and adaptation | Residual change detector, bounded candidate lifecycle and promotion/rejection gate | The accepted operator is unchanged until a candidate passes both gates |
| M3-E | Memory architecture controls | C0-C4 reference implementations and resource instrumentation | Report persistent state bytes, parameter bytes/count, update and query multiply-adds |
| M3-I | Integrated heterogeneous learner | Sequential learner harness, benchmark records and cross-component checks | Demonstrate coherent event order and component interaction without exceeding M3 claim ceiling |

### Package boundaries

M3-A owns context prototypes, covariance and slot lifecycle. It does not select relationships or update relationship operators.

M3-B owns source feature assembly, target prediction and estimator sufficient statistics. It does not own context acceptance, activation or revision.

M3-C owns predictive evidence and activation state. It cannot rewrite or delete the stored relationship operator.

M3-D owns alarms and candidate promotion/rejection. A detector alarm never directly overwrites accepted knowledge.

M3-E owns architecture controls and accounting. A matching state dimension alone is not a fairness claim. Any comparison must state precision, persistent bytes, trainable parameters, update compute, query compute, and the matched Pareto budget.

M3-I owns orchestration, learner/evaluator boundary checks and end-to-end experiment output. It cannot silently amend component contracts.

## 5. Carry-forward limitations from earlier campaigns

These are implementation obligations, not reasons to stop M3:

- R2 used a multi-source joint fit but an inadequate primary-source-only prequential predictor. M3-B must use all eligible incoming groups in the actual prediction.
- R3 validated one deterministic activation sequence; noisy boundary behaviour and multiple concurrent groups remain to be tested.
- R4's CUSUM calibration covered a narrow Gaussian mean-shift family only.
- R5 established input projection and state-byte arithmetic but did not demonstrate full C0-C4 model performance or measured compute equivalence.
- F6 audited benchmark leakage and held-out composition design; it did not establish learner generalisation.
- F7 and M3-G showed why individually stable operators do not imply stability under arbitrary switching.

The first implementation slice supplies executable reference mechanisms, not complete solutions to all these limitations. Results must be explicit about which properties were tested.

## 6. Integration sequence

1. **M3-0 — Shared contract:** this protocol, module boundaries, event order and artifact schema are the common baseline.
2. **M3-A–M3-E — Parallel component implementation:** five separate CI jobs, each with its own tests and JSON evidence artifact.
3. **M3-I — Integration:** run after the five component jobs, connecting context, all-source prediction, evidence/activation, revision and memory accounting.
4. **Sequential experiments:** move beyond smoke coverage to the existing eight-world task family, held-out compositions, multiple source groups and independent seeds.
5. **Targeted revision:** update only the affected component and protocol version, preserving prior experiment artifacts.

No package is considered scientifically validated merely because its unit tests or CI job pass.

## 7. Required measurements

At minimum report:

- prequential full-predictor loss and held-out loss;
- per-source marginal predictive contribution with correlation/identifiability diagnostics;
- context ACCEPT / ABSTAIN / NOVEL frequencies, false acceptance and slot overflow;
- evidence calibration, sufficiency and false-negative/false-positive behaviour;
- activation transitions, chatter, dormancy and reactivation;
- detector false alarms, detection delay and missed changes across several drift families;
- candidate promotion and rejection quality, stale-operator damage and collateral relation effects;
- C0-C4 persistent state bytes, parameter count/bytes, update and query compute, and task-level memory interference;
- coordinate/metric transformation errors and numerical conditioning;
- held-out composition and cross-context transfer, separately from training performance.

Thresholds and hyperparameters are selected on training/validation streams and frozen before held-out evaluation. Test results do not feed back into tuning.

## 8. Protocol versioning and decision policy

This is v0.1 and is amendable. Component interfaces may be revised when actual integration exposes contradictions. Every change must record:

- the observed failure or new evidence;
- the affected contract/equation/interface;
- backward-compatibility implications;
- the experiment that motivated the change;
- whether previous evidence remains comparable.

Do not rewrite earlier campaign outputs. Do not present a design choice as mathematically proved unless a proof and its assumptions are recorded. Do not claim global adaptive-network stability; that is M4.

**Current decision:** GO — M3 INVESTIGATION AUTHORISED.  
**Protocol frozen:** no.  
**M3 implementation complete:** no.  
**M3 scientific outcome:** open.
