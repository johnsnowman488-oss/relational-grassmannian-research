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

The accepted 32-story-per-shard resource qualification used the default H0 top-down gain of 1.0. That bounded sample did not expose the long-sequence numerical failure.

The first full-scale fit-only preflight, with the same gain, failed at Task 11 story `task11/train/story000050`, event `line000001`, observation tick 386. The native state maxima across the three levels were approximately 302, 640 and 932. The first two spectral reports returned non-finite `mcap=inf`; the native exchange then failed with `sum(w) must be non-zero`. The active kernel weights themselves remained positive (0.25 per channel). This is a numerical stability failure in exponential top-down modulation under accumulated SOE state, not a label-leakage or Task 11 parser failure.

The campaign therefore freezes `top_down_gain=0.001` for both HLA and HLB, all six conditions and all ten seeds. The value scales the observed gain-1.0 modulation at the measured state magnitude to a finite regime. It is a fit-only numerical-stability correction, not a validation-selected predictive hyperparameter. The 32-story qualification remains valid for its original gain-1.0 configuration; it does not substitute for the new full-scale preflight at gain 0.001.
