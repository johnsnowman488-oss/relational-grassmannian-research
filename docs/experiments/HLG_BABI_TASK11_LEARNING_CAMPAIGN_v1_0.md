# bAbI Task 11 HLA/HLB learning campaign protocol v1.0

**Status:** FROZEN — full-scale resource preflight required before campaign launch  
**Scope:** Task 11 only; HLA and HLB; Tasks 14 and 19 remain locked  
**Protocol JSON:** `HLG_BABI_TASK11_LEARNING_CAMPAIGN_v1_0.json`

## 1. Fixed experiment

The campaign contains exactly:

[
1\text{ task}\times2\text{ architectures}\times6\text{ conditions}\times10\text{ seeds}=120\text{ run units}.
]

The seeds are 953100–953109. The six conditions are full learning, no temporal, no relational, no abstraction, no task, and no learning. The no-task condition is explicitly a placebo/negative control for Task 11: the evaluator-label firewall means there is no independent task-outcome training target in this task path, so this condition must not be interpreted as a causal task-channel ablation. Each run unit starts with a clean learner and native runtime. HLA and HLB are paired on identical story order, partitions, event features and query cutoffs.

This protocol replaces the earlier multi-task 360-unit design for the active Task 11 campaign. It does not modify the historical protocol record, Task 3/5 campaign, or Tasks 14/19 source/experiment state.

## 2. Source and nested whole-story partitions

The only active source is the frozen bAbI v1.2.0 English en-10k Task 11 training member:

- 1,800 fit stories (9,000 queries);
- 200 validation stories (1,000 queries);
- 200 official test stories (1,000 queries), labels sealed and never loaded.

Fit stories are partitioned again for each campaign seed by a seed-specific SHA-256 hash into 1,440 warm-start stories and 360 online-adaptation stories. HLA and HLB share the exact same assignment for each seed. Each seed's phase membership and hashes are frozen in the campaign manifest. Story membership is indivisible. The exact query counts for these two nested phases must be computed from the story manifest; they must not be estimated from the 80/20 story ratio.

Validation is read-only. It may be ingested as observed source context for prediction, but it cannot update learner parameters, thresholds, normalization, calibration or candidate state. Official test remains sealed.

## 3. Prediction, learning and evaluator boundaries

The Task 11 prediction contract is architecture-specific. HLA reads its answer transition from the learned L2 `ContextTransitionLearner`, conditioned on entity and preceding story-local location. HLB reads typed `task11_location_transition` records from its rollback-scoped canonical model relation store. HLB inserts these derived learning targets through `observe()`, never `observe_source()`, so they do not enter the immutable source evidence journal. Both paths require every predicted transition to be available from the learner and consistent with observed story data. Missing, conflicting or ambiguous transitions cause abstention; there is no silent symbolic-baseline fallback.

The weak antecedent rule admits a pronoun target only when exactly one distinct compatible prior named entity exists. Ambiguous and unresolved mentions abstain. Story-local entity/location state resets between stories even when the model persists across the fit sequence.

The learner sees only source observations and permitted weak training targets. Official answer/support labels are consumed only by the evaluator after predictions are fixed. Official Task 11 labels do not contain independent antecedent-edge gold, so antecedent top-1, coreference-edge F1 and entity-chain exact match remain NOT INDEPENDENTLY EVALUABLE. Generated confirmatory labels are separate and are never used for training, validation, threshold tuning or candidate selection.

## 4. Baseline comparison

The independent validation workflow evaluated 1,000 whole-story validation queries:

| Baseline | Answer exact match | Support-witness recall | False-witness rate |
|---|---:|---:|---:|
| Nearest-compatible antecedent | 1.000 | 1.000 | 0.000 |
| Recency-only | 0.704 | 0.3255 | 0.349 |

The nearest-compatible antecedent is the strongest non-oracle baseline. A learned candidate must match it on the same validation split while satisfying all integrity gates. If no seed qualifies, no candidate is selected; thresholds are not relaxed after seeing the results.

The archived scorecard and artifact digest are in `HLG_BABI_TASK11_NONORACLE_BASELINE_VALIDATION_v1_0.md`.

## 5. Resource qualification before 120 units

The previously accepted resource qualification covered four independent 32-story persistent sequences per architecture. It is not a full 1,800-story run-unit qualification.

Therefore the campaign has a separate reserved-seed preflight (seed 953099, excluded from the 10 campaign seeds). It runs the complete 1,800-story fit path and 200-story read-only validation for HLA and HLB under full-learning and no-learning conditions: four run units total.

The campaign reuses the exact three-level SOE feature dimensions (3, 3, 3), fixed time step (0.01), and native kernel configuration from the accepted Task 11 persistent-resource qualification. The full HLB relation store is configured at 262,144 records and the event-resolved eligibility ledger at 131,072 records; these are explicit capacity settings, not estimates. The preflight must measure peak RSS, Python allocation, update time, full checkpoint size and restore time, artifact size, and retry behavior. Hard ceilings are:

| Measure | Maximum |
|---|---:|
| Worker RSS | 4,096 MiB |
| Python allocation peak | 2,048 MiB |
| Full checkpoint | 512 MiB |
| Run-unit wall time | 3,600 s |
| Run-unit evidence artifacts | 256 MiB |

All four units must complete with zero partition overlap, zero evaluator leakage, zero validation updates and zero cross-story bindings. Failed attempts and retries remain visible in evidence. The preflight's measured budget must be committed before campaign launch.

## 6. Four-worker deterministic campaign

Enumerate the 120 run-unit keys in stable architecture/condition/seed order and assign index modulo four to shards 0–3. Each shard receives 30 unique units. No two units share mutable output paths. The workflow uses four-way concurrency, run-specific concurrency identity, and `cancel-in-progress: false`.

Aggregation requires exactly 120 unique run-unit keys, no duplicates or missing units, one matching protocol/source/partition identity, and complete per-unit metrics and hashes. Retries may target only failed keys; successful evidence is immutable.

## 7. Confirmatory challenge is a separate phase

The Task 11 generated confirmatory challenge is specified separately in the protocol JSON and implemented by `generate_task11_confirmatory`. Its generator seed is 953200 and its frozen size is 384 stories: 320 answerable novel-name cases and 64 ambiguous-pronoun cases that must abstain. It includes explicit entity anchors, location changes, uniquely resolvable pronouns in the answerable subset, and a predeclared ambiguous subset.

Generated inputs and evaluator labels must be separate files with independent hashes. The challenge is generated/evaluated only after validation candidate selection, once per selected architecture. The generator and evaluator are tested independently; CI does not publish or consume the challenge artifact before candidate selection. It cannot feed training, candidate selection or threshold changes. It is not official bAbI test data and does not establish generalisation to unrestricted raw text.

## 8. Launch gate

This protocol is frozen but not itself a campaign launch. The 120 units remain blocked until:
1. prediction/evaluation CI is green;
2. the baseline scorecard is archived;
3. the Task 11-only protocol and partition tests pass;
4. all four full-scale reserved-seed preflight units pass and the measured resource record is archived;
5. the Task 11-only confirmatory generator and label-isolation checks pass.

No Task 14/19 experiment or Task 3/5 modification is permitted in this sequence.


## Full-scale native stability calibration

The accepted 32-story-per-shard resource qualification used the original Aberconics native commit `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de` with H0 top-down gain 1.0. That bounded sample did not expose the long-sequence numerical failure.

The first full-scale fit-only preflight on that native commit failed at Task 11 story `task11/train/story000050`, event `line000001`, observation tick 386. Native state maxima across the three levels were approximately 302, 640 and 932; the first two spectral reports returned non-finite `mcap=inf`, followed by `sum(w) must be non-zero`. A subsequent gain-0.001 attempt failed at story 530 after state magnitudes exceeded 1.57 million and spectral values became non-finite. Gain reduction was therefore not accepted as the architectural fix. Gain 1e-8 was an interim diagnostic configuration only and is not the frozen campaign setting.

The underlying defect was unbounded mean-absolute SOE state entering exponential top-down kernel modulation. Aberconics PR #12 fixed this in native code and merged as `4bbcaa132131733372c17a68895a329a030c84d0`. The native fix:
- saturates the mean-absolute top-down observable with `tanh` using long-double accumulation and finite-input checks;
- uses stable log-sum-exp normalization for positive kernel weights;
- rejects non-finite or non-positive decay-rate materialization;
- bounds top-down edge gain magnitude at 50; and
- includes a C++ regression test with observables of magnitude 1e9, finite positive kernels and finite spectral Mcap.

The campaign now pins native commit `4bbcaa132131733372c17a68895a329a030c84d0` and restores H0 top-down gain 1.0 for HLA and HLB, all six conditions and all ten seeds. This retains the intended modulation strength while bounding its drive in the native implementation. Native Linux/Windows C++ and Python CI passed; the full-scale Task 11 resource/integrity preflight on this exact commit remains mandatory. The earlier 32-story resource reports remain preserved as historical evidence for the original native commit and are not substituted for the new full-scale preflight.

## Interpretation of the six conditions

The Task 11 answer head reads the L2 entity-conditioned location-transition model. Therefore `no_temporal` and `no_relational` are mechanistic learner-component controls, not direct answer-head ablations: their answer predictions are expected to remain invariant to `full_learning`. `no_task` is also expected to be answer-invariant and is a placebo because Task 11 supplies no independent task-outcome training target under the label firewall. The campaign aggregator checks these invariances per architecture and seed.

`no_abstraction` disables the L2 answer-transition model and `no_learning` disables all learning; both are negative controls expected to have zero answer coverage. Any violation is an integrity failure, not a reason to revise the expected result after seeing validation scores.

The campaign workflow runs the complete repository/Task 11 contract suite first, then the reserved-seed full-scale preflight. It launches the 120 units only after both gates pass. The actual generated confirmatory challenge is created only after validation-only candidate selection; predictions are frozen before its separate evaluator-label file is opened.


## Reserved-seed preflight boundary

The reserved seed (953099) is a resource/integrity preflight, not a performance-selection seed. Its validation predictions and scores are archived for diagnosis, but answer exact match, coverage and witness scores do not gate campaign launch and do not select a candidate. Launch depends on complete unit execution, exact partitions, label isolation, zero validation parameter updates, checkpoint recovery and resource ceilings. The 120-unit campaign uses only seeds 953100–953109 for validation-based candidate selection. No reserved-seed result is folded into the campaign summary.
