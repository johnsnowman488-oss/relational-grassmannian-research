# HLG-M3 broader benchmark protocol — BM-0/BM-1 draft v0.1

**Campaign:** HLG-M3-BROAD-BENCHMARK-BM0-BM1-v0.1  
**Parent evidence:** M3 preflight; F1-F7; R1-R5; HLG-M3 implementation v0.1; HLG-M3 final refinement v0.2  
**Status:** draft, amendable, review required; not frozen  
**Current scope:** BM-0 benchmark contract and BM-1 deterministic manifest/information-boundary validation  
**M3 boundary:** supplied fixed candidate topology; topology birth/death is excluded; global coupled stability remains M4

## 1. Purpose and evidence preservation

This protocol moves the HLG-M3 investigation from deterministic component refinement toward a multi-world sequential benchmark. It does not revise, replace, or inflate earlier evidence. The prior preflight, F1-F7, R1-R5, implementation v0.1 and refinement v0.2 artifacts remain the record of what was previously designed and executed.

The v0.2 canonical campaign demonstrated executable context gating, effective activation, conditional-identifiability diagnostics and an integrated candidate-revision path on one deterministic synthetic stream. It did not establish held-out composition generalisation, broad context or detector calibration, multi-world robustness, or resource-fair C0-C4 superiority. BM-0/BM-1 establishes the experiment contract needed to test those claims.

## 2. Three governing design decisions

### Decision 1 — staged scope, predeclared full matrix

The full confirmatory allocation is fixed in the manifest before benchmark outcomes are observed:

| Split | Independent world configurations | Replicate seeds per world | Streams |
|---|---:|---:|---:|
| Development fit | 12 | 5 | 60 |
| Development validation | 8 | 5 | 40 |
| Held-out test | 20 | 5 | 100 |
| **Total** | **40** | **5** | **200** |

The historical F6 design contains eight pilot worlds (four development-fit, two validation and two test), not eight separately specified world-family generators. BM-0 therefore preserves F6 as the `F6-INTEGRATED-SEQUENTIAL-v1` scenario template: seven shared phases (acquisition, distractor, context switch, relation-2 isolation, observation gap, reactivation and within-context drift), plus the held-out-composition phase in test only. The historical F6 seeds are retained as provenance and are not reused in the confirmatory campaign. BM-2 must define explicit factor-valued world configurations from this template; each configuration receives a separate configuration seed and five independent stream seeds.

Do not run the full Cartesian product of every stress factor. It would be expensive and obscure which factor caused an effect. Use a structured design:
- Each package first gets a one-factor-at-a-time core sweep with the same base stream definitions.
- Predeclared pairwise interactions are context ambiguity × context capacity, source correlation × missingness, and drift family × observation noise.
- The pilot uses a deliberately small diagnostic subset, fixed before execution.
- The full 200-stream split allocation remains unchanged. Reducing the pilot does not reduce the confirmatory allocation.

Factor levels to carry into BM-2 and later packages:

| Factor | Initial levels |
|---|---|
| Source correlation | rho = 0, 0.5, 0.9, 0.99, 1.0 (exact collinearity) |
| Context ambiguity | standardized separation d-prime = 4, 2, 1, 0.5 |
| Context-bank capacity | K = 2, 4, 8 |
| Independent missingness | observation probability = 1.0, 0.95, 0.80 |
| Burst missingness | outage lengths = 20, 50, 100 steps |
| Drift family | stationary, step, gradual, variance-only, transient, compound |
| Observation noise | baseline, 2x baseline, 4x baseline |

These levels are design factors, not results. The generator must record the realised factor settings and actual missingness mask. A missing source vector remains missing; it must not silently be replaced with a clean value.

### Decision 2 — common resource envelopes plus measured Pareto frontiers

C0 remains the zero-persistent-memory reference floor. It is not described as having equal used memory to C1-C4.

C1-C4 receive the same hard resource ceilings at each comparison tier:
- total persistent bytes, including state and trainable parameter storage;
- parameter count and parameter precision;
- update-compute ceiling per observed update;
- query-compute ceiling per prediction;
- identical source/task streams and evaluation windows.

Unused budget is permitted and reported. No architecture is padded with dummy parameters or artificial operations to claim equal use. Every comparison reports actual consumption and the common ceiling. Where a configuration cannot satisfy every ceiling, it is excluded from the matched-envelope analysis and may appear only in a clearly marked unmatched/Pareto appendix.

BM-4 must derive the numeric tier ceilings from the audited C0-C4 implementations and representative task dimensions before any C0-C4 performance ranking is run. The current 512-byte versus 2,560-byte C3/C4 mismatch is an explicit warning, not a baseline to conceal. The final report will show performance versus actual persistent bytes, parameter count, update work and query work; there is no single winner by default.

### Decision 3 — hold out compositions, not the primitive vocabulary

The primary generalisation claim concerns unseen ordered compositions of relation primitives that have appeared during development. The primary primitive vocabulary is REL-A through REL-D. The ordered nature matters: [A,B] and [B,A] are different compositions.

- Fit compositions: [A,B], [B,C], [C,D], [D,A].
- Validation compositions: [A,C], [B,D].
- Primary test compositions: [B,A], [C,B], [D,C], [A,D], [A,B,C], [B,C,D], [C,D,A], [D,A,B].

Every primary test primitive appears in at least one fit composition. No exact ordered composition is shared across fit, validation and test. Test includes held-out pairs and longer three-relation compositions. This makes the primary test about composition generalisation rather than discovery of an entirely unseen primitive.

A separate, optional primitive-OOD stratum introduces REL-E. Its results must be labelled separately and must not be folded into the primary held-out-composition claim. The benchmark manifest explicitly marks that stratum as excluded from primary scoring.

## 3. Hypotheses and counter-evidence

| ID | Hypothesis under test | Required counter-evidence |
|---|---|---|
| H1 Context | Context decisions remain useful under overlap, noise and finite capacity | False acceptance, false novelty, excessive abstention or slot instability |
| H2 Sources | Joint learning retains predictive utility under correlated heterogeneous inputs | Conditional rank collapse, coefficient instability or elevated held-out loss |
| H3 Missing/dormant | Missing observations remain neutral and dormant operators can reactivate | Negative evidence from absence, dormant-route leakage or lost operator state |
| H4 Drift | Detection distinguishes persistent change from stationary noise and transients | False alarms, missed changes or unacceptable delay |
| H5 Revision | Candidate promotion improves later unseen observations and harmful candidates are rejected | Validation overfit, non-identifiable promotion or post-promotion degradation |
| H6 Memory | C0-C4 exhibit interpretable performance/resource trade-offs under common ceilings | Apparent benefit vanishes under the shared envelope or causes cross-task interference |
| H7 Robustness | Findings reproduce across world configurations and independent seeds | Strong world/seed dependence or a result driven by a few favourable streams |

No hypothesis is assumed true. Scientific checks must remain separate from executable checks.

## 4. Split and seed contract

The machine-readable split manifest is docs/hybrid_leptograph_m3_benchmark_split_manifest_v0_1.json.

- 12 development-fit world configurations, each with five independent replicate seeds.
- 8 development-validation world configurations, each with five independent replicate seeds.
- 20 held-out-test world configurations, each with five independent replicate seeds.
- Every confirmatory world configuration references the F6 scenario template. The 40 configuration seeds and 200 replicate stream seeds are new and disjoint across splits; BM-2 materialises the factor-valued configuration associated with each configuration ID.
- World configuration seeds and replicate stream seeds use separate, non-overlapping deterministic ranges.
- The manifest is immutable within a campaign run and its SHA-256 is recorded in every evidence record.
- Test split membership, relation compositions, context truth, operator parameters, change schedules and future observations are evaluator-only data.

A new seed is not a new world configuration. The reporting unit for uncertainty is the independent world/stream replicate, not each individual time step. Paired control comparisons use the same world, composition, replicate seed and observation mask.

## 5. Data-generation and benchmark factor protocol

BM-2 implements the full sequential world generator from the F6 scenario template. It must bind each of the 40 configuration IDs to explicit factor values before generating streams; a configuration seed and replicate stream seed are distinct inputs. Generator version, configuration values, factor levels, composition IDs, realised masks and content hashes are recorded.

The data-generation plan must include:
- heterogeneous source groups with controlled correlation, shared factors and exact collinearity;
- ordered relation compositions with the fit/validation/test partition above;
- clean, overlapping, ambiguous and noisy context observations;
- finite context banks, including full-bank behaviour;
- isolated missingness, target missingness, burst outages and long dormant intervals;
- stationary, step, gradual, variance-only, transient and compound changes;
- observation noise levels and multiple independent source groups.

The learner receives only current permitted observations. The evaluator retains the latent world, truth labels, planted operators, context identity and schedules. The split manifest is never injected into learner state or model calls.

## 6. Learner/evaluator boundary and sequential order

The learner-side observation is a strict typed record containing only:
- current step index;
- current source identifiers, observed source vectors and source-observation masks;
- current context vector and context-observation mask.

It contains no world ID, family ID, split, seed, composition ID, primitive-relation label, context truth, planted operator, schedule, future observation or target. Targets are revealed through a separate feedback object only after the current prediction has been recorded.

The event order remains:
1. build the current learner observation;
2. resolve context and retrieve eligible state;
3. produce and record the prediction;
4. reveal the current target (or missing-target marker);
5. score prequential loss;
6. update estimator/evidence/activation;
7. update detector and candidate state;
8. record evaluator-only truth for scoring, outside learner state.

A NOVEL or ABSTAIN context must not leak raw context-conditioned features into the effective predictor. A missing source or target must not be converted into negative evidence. The learner may keep its own history and internal state, but evaluator metadata must not enter that state.

BM-1 implements a deterministic one-step contract fixture and prequential gate. It tests the information boundary and event order; it does not claim to implement or scientifically validate the full F6-derived sequential generator. The full generator is BM-2.

## 7. Candidate revision protocol

For every eligible detected change:
- keep the incumbent operator active until promotion;
- fit a candidate on the next 32 chronological time slots after the alarm;
- validate it on the subsequent, disjoint 32 slots;
- evaluate the accepted candidate on a further untouched 64-slot post-promotion segment.

A segment must contain at least 24 observed target rows to support a promotion decision. If not, report INSUFFICIENT_EVIDENCE and preserve the incumbent; do not shorten the segment after inspecting results. Record time-slot bounds, target masks, usable row counts, identifiability, incumbent/candidate validation losses and post-promotion test loss. Do not refit a candidate using its validation or post-promotion test observations.

If another alarm occurs while a candidate lifecycle is open, record it as a secondary alarm; do not silently launch overlapping candidate lifecycles. A new lifecycle can begin after the current one is resolved.

## 8. Required metrics and uncertainty

Report per world/seed first, then aggregate. Include:
- prequential and held-out loss, calibration and per-composition performance;
- conditional rank, condition number and coefficient variability for every source block;
- context ACCEPT/ABSTAIN/NOVEL rates, false acceptance, false novelty, coverage-risk and slot saturation;
- activation false transitions, dormant prediction leakage, stored-operator retention and reactivation delay;
- detector false alarms per 1,000 steps, stationary per-stream false-alarm probability, detection probability, missed-change rate, delay distribution and transient false alarms;
- candidate promotion/rejection counts, identifiability gate results, validation improvement and untouched post-promotion improvement;
- actual persistent state/parameter bytes, parameter count, precision, update/query operations and cross-task memory interference;
- all failed, inconclusive or skipped conditions with reasons.

For uncertainty, report mean, median, standard deviation, 95% world-clustered bootstrap intervals, paired differences on matched streams, per-world distributions and worst-decile outcomes. Detection-rate intervals must use independent streams as the sampling unit. Do not treat time steps within one stream as independent replicates.

## 9. Concurrent workflow and aggregate contract

The full broader benchmark will execute in one workflow from one immutable implementation commit and one manifest hash. Independent jobs run concurrently:
- M3-A context ambiguity/capacity;
- M3-B held-out composition, correlation and identifiability;
- M3-C missingness, dormancy and reactivation;
- M3-D drift detection and candidate revision;
- M3-E C0-C4 common-envelope/Pareto task comparison;
- M3-I integrated multi-world sequential benchmark;
- full repository tests on Python 3.10 and 3.12.

One aggregate waits for all package jobs and both test jobs. It verifies exact artifact and matrix coverage, schema version, campaign and commit identity, manifest hash, stream uniqueness, split/composition disjointness, no leakage fields in learner records, chronology/disjointness of fit-validation-post-promotion windows, valid resource accounting, and Python test outcomes. Scientific checks are summarised per hypothesis and are never collapsed into one green M3-success flag.

BM-0/BM-1 has its own contract gate workflow with the same one-workflow principle: manifest/leakage validation and Python 3.10/3.12 full suites run concurrently; an aggregate verifies the contract evidence and preserves the claim ceiling.

## 10. Claim ceiling and milestone boundaries

Passing BM-0/BM-1 demonstrates only that the split manifest, composition partition and learner/evaluator boundary are machine-checked and deterministic. It is not evidence of predictive generalisation, context robustness, detector calibration, successful candidate adaptation, a C0-C4 winner, or M3 completion.

M3 remains bounded to the supplied fixed candidate topology. It does not introduce topology birth/death. Predictive ablation is not causal attribution. No global coupled adaptive stability claim is made; that remains M4.

**Protocol frozen:** no.  
**Scientific benchmark executed:** no.  
**BM-0/BM-1 executable status:** to be established by the contract workflow.
