# HLG-M3 foundation design campaign — results

**Campaign:** HLG-M3-FOUNDATION-F1-F7-v0.1  
**Canonical run:** 43756548407  
**Source commit:** a34e4d3fc1086b9419b99515e8bb266e5d9cf0ec  
**PR:** #22 — proposed HLG-M3 foundation and F1-F7 design campaign  
**Result:** seven design jobs and aggregate passed; implementation protocol remains unfrozen  
**Date:** 2026-11-15

## 1. Execution summary

The canonical GitHub Actions run completed successfully:

- F1-F7: 7 of 7 independent design jobs passed.
- Aggregate evidence verification passed; exactly seven expected result files were present and valid.
- Full repository tests: 228 passed on Python 3.10 and 228 passed on Python 3.12.
- The aggregate reports REVIEW_F1_F7_RESULTS_BEFORE_FREEZE and implementation_protocol_frozen=false.

Aggregate summary JSON SHA-256:

3eba7510f5532b03540c3231c2d30e7c8b1b146dd0e24ae17e05277fd6cc743f

## 2. Case results

### F1 — Sequential prequential evidence and attribution

- Training prefix: 1,800 observations.
- Online prequential test stream: 900 observations. Each prediction and full/ablated loss comparison was computed before incorporating the current target into the sufficient statistics.
- Full prequential test MSE: 0.0001016639.
- Mean marginal predictive contribution for the planted useful relation: 0.5173964.
- Mean marginal predictive contribution for the independent null decoy: -3.55 × 10^-7.
- Under deliberately collinear source blocks, conditional information rank was 0 for a two-dimensional target block.

**Interpretation:** the frozen additive predictor assigns a strong marginal predictive contribution to the planted useful block and near-zero contribution to an independent null block. When source blocks are collinear, the conditional information test exposes non-identifiability. This is predictive attribution under a specified model, not causal attribution.

### F2 — Metric-aware heterogeneous operator estimation

- Source dimensions: 2 and 3.
- Context dimension: 2.
- Target dimension: 4.
- Joint feature dimension, including context and intercept: 8.
- Relative operator recovery error: 3.7423 × 10^-5.
- Relative general-coordinate covariance error: 4.8669 × 10^-5.
- Collinear conditional information rank: 0; conditional information spectral norm: 6.2765 × 10^-13.

**Interpretation:** whitened regularised least squares recovers the planted heterogeneous additive operator in the sufficiently excited reference case and transforms consistently under the tested non-orthogonal coordinate changes with transported metrics. The collinear case demonstrates that regularisation does not solve missing identifiability.

### F3 — Context memory and abstention

| Query condition | Decision |
|---|---|
| Clearly separated known context | ACCEPT |
| Near-duplicate/ambiguous context | ABSTAIN |
| Context outside all stored regions | NOVEL |

- General-coordinate score-difference invariance error: 0.
- Repeated novelty observations required before slot creation: 3.
- Reference maximum slot count: 3.
- Overflow policy: abstain without evicting a stored slot.

**Interpretation:** the diagnostic Gaussian/Mahalanobis score supports the proposed three-way decision contract in these reference cases. The feature map, covariance estimation, absolute fit threshold, ambiguity margin and novelty policy still require calibration on the integrated task suite.

### F4 — Evidence, activation and revision

- Positive evidence pseudo-mean in the reference state: 0.59756.
- Support sufficiency: 0.41380.
- No-observation interval: positive and negative evidence masses were discounted proportionally; no negative event was added.
- Hysteresis: no switching inside the declared band in the tested sequence.
- Stationary residual control: no CUSUM trigger.
- Changed residual sequence: first trigger at sample index 32 under the selected reference parameters.

**Interpretation:** the state-update definitions preserve their declared bounds and distinguish missing observations from negative evidence. The CUSUM output is only a reference challenge. Its thresholds do not yet have an empirically established false-alarm rate or detection-delay guarantee.

### F5 — Memory architecture comparison contract

The reference budget used 64 float64 state scalars, or 512 bytes, for each persistent-memory configuration C1-C4:

| Configuration | State allocation | Persistent bytes |
|---|---|---:|
| C0 | No persistent state | 0 |
| C1 | 64 mode-memory scalars | 512 |
| C2 | 64 relational-memory scalars | 512 |
| C3 | 32 mode + 32 relational scalars | 512 |
| C4 | 64 shared latent scalars | 512 |

The proposed common resource envelope records a 4,096 trainable-parameter cap, 8,192 update multiply-add cap and 4,096 query multiply-add cap, all at float64 precision.

**Important limitation:** F5 validates bookkeeping and the comparison contract only. It does not execute C0-C4 models, and it does not prove that a specific implementation of each model can attain matched parameter/update/query costs. The eventual comparison must report actual costs and compare matched Pareto points. No architecture winner was selected.

### F6 — Integrated benchmark design

- Worlds: 8.
- Training seeds: 110-113.
- Validation seeds: 210-211.
- Test seeds: 310-311.
- Total learner rows: 1,160.
- Eight phases across the suite: acquisition, distractor, context switch, relation-2 isolation, observation gap, reactivation, within-context drift and held-out composition.
- The relation-2 block is exposed separately during training; its joint composition with the other learned block is present only in test worlds.
- Phase identifiers, world seed metadata, planted operators and evaluator truth remain outside learner-visible rows.
- Observation-gap target masks are enforced.

**Interpretation:** the generator's split and information boundary pass their reference audit. It is a task-manifest check, not evidence that a model learns or generalises. Task coverage, effect thresholds, noise/drift schedules and seed counts require scientific review before a frozen benchmark protocol.

### F7 — Independent mathematical/adversarial review

- Metric-aware operator norm before coordinate change: 1.4336993032.
- Metric-aware operator norm after equivalent non-orthogonal coordinate change: 1.4336993032.
- Absolute invariance error: 4.44 × 10^-16.
- Individual switched matrices each have spectral radius 0.8.
- Alternating two-step product spectral radius: 2.0833981.
- Stored operator remains unchanged while activation is zero and the effective route is zero.

**Interpretation:** M1 metric transport is compatible with the proposed norm constraint. The switching counterexample reiterates that individual spectral-radius checks do not establish arbitrary switched-system stability. The storage/activation separation is mathematically coherent at the edge level; full adaptive-network stability remains an M4 question.

## 3. Overall findings

The jobs support these proposed foundations sufficiently to continue design review:

1. Prequential marginal predictive contribution is a useful operational evidence signal, provided its attribution limitations under correlated inputs remain explicit.
2. Online joint operator estimation can retain heterogeneous source/target dimensions and preserve M1 coordinate covariance when estimation is performed in whitened coordinates.
3. Context retrieval needs explicit abstention and bounded slot management; a forced nearest-neighbour decision is not acceptable.
4. Missing observations must not be counted as negative relational evidence.
5. Stored relationship knowledge and current route activation should remain separate.
6. A two-phase candidate revision mechanism is worth retaining as a proposal, but its detector and promotion thresholds need benchmark evaluation.
7. Memory architecture comparisons require both matched state capacity and explicit accounting of parameter/update/query cost.
8. Global adaptive network stability cannot be inferred from per-edge bounds or instantaneous spectral radii.

These are reference-calculation and design-contract findings. They do not establish end-to-end relational learning, relation discovery, causal correctness, transfer or scientific superiority of the proposed memory architecture.

## 4. Corrections made during campaign development

Exploratory attempts were not treated as canonical evidence:

- The first F3 setting used an ambiguity margin of 2.0. Its near-duplicate pair had a score margin of approximately 2.2495 and was therefore accepted. The reference margin was raised to 3.0; the final canonical run returned ABSTAIN.
- The first F6 manifest exposed phase index and episode seed in learner rows. These were moved to evaluator-only metadata.
- F1 was strengthened from a static train/test comparison to a sequential prequential stream: each test prediction and ablation score is computed before the current target updates the sufficient statistics.
- F6 was strengthened so the two-block composition is absent from training/validation and appears only in held-out test worlds.
- A shared metric-norm helper and the F6 result-field assertion were restored/aligned after an intermediate regression.

Only the final run 43756548407 on commit a34e4d3fc1086b9419b99515e8bb266e5d9cf0ec is the canonical evidence set.

## 5. Evidence artifacts

All artifacts were uploaded by the canonical run and were unexpired at execution time. GitHub Actions retention is scheduled through 2027-02-13.

| Evidence | Artifact ID |
|---|---:|
| F1 | 14178546656 |
| F2 | 14177898945 |
| F3 | 14177419726 |
| F4 | 14178139365 |
| F5 | 14178646333 |
| F6 | 14178183449 |
| F7 | 14178307423 |
| Aggregate summary | 14178406183 |

Canonical run: https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43756548407

## 6. Decisions still required before implementation protocol freeze

The aggregate intentionally leaves the implementation protocol unfrozen. Research review must decide:

- fixed context feature map and context covariance strategy;
- context acceptance, ambiguity and novelty thresholds, slot count and overflow policy;
- predictive loss, evidence dead-zone, observation-quality weights and time constants;
- operator regularisation, conditional-identifiability tolerances and metric norm bounds;
- estimator uncertainty calibration and its role in activation;
- change detector, candidate revision window and promotion rule;
- matched resource frontier for C0-C4;
- integrated task coverage, seed counts, held-out splits and minimum effect sizes.

Select thresholds on training/validation data and freeze them before held-out testing.

## 7. Status

**Proposed foundation adopted:** yes.  
**Seven-job design campaign:** completed successfully.  
**Canonical aggregate:** passed.  
**Implementation protocol:** not frozen.  
**Production M3 implementation:** not authorised by this campaign.

The next step is scientific analysis of F1-F7 and explicit resolution of the design choices above. Only then should HLG-M3 implementation protocol v1.0 be frozen.
