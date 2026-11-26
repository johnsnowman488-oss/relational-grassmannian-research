# bAbI Tasks 3 and 5 — HLA/HLB Learning Protocol v1.0

**Protocol ID:** HLG-BABI-T3-T5-LEARNING-v1.0  
**Status:** FROZEN — 2026-11-26  
**Parent implementation:** `research/h1-learning-runtime-integration` (PR #50, draft)  
**Data manifest:** `HLG_BABI_TASKS_3_5_STRUCTURED_CAMPAIGN_v0_1.json`  
**Scope:** structured-event learning and retrieval only; natural-language parsing is excluded.

## 1. Research questions

**Task 3 — Three Supporting Facts.** Can the hybrid hierarchy maintain temporally ordered object-state information and answer an object-location query immediately before a specified movement event, while preserving the relevant supporting event chain?

**Task 5 — Three Argument Relations.** Can it represent a GIVE event as one n-ary event with giver, object and recipient bound to the same event identity, then answer role-conditioned queries without assembling roles across different events?

The campaign evaluates four distinct outcomes: task answer quality, learned event prediction, evidence/witness integrity, and operational behaviour. None substitutes for another.

## 2. Immutable data and partitions

Use bAbI QA v1.2, English `en-10k`, Tasks 3 and 5. The pinned official archive is 11,745,123 bytes with SHA-256:

`84f5296ab9a1ad0dc9464e08c491d65cd08830fca3acae9ab86f75e0fb81573c`.

The archive and eight source/derived split files are already recorded in the source-freeze manifest and artifact (run `45832843743`, artifact `15123500490`). Before campaign execution, CI must re-verify every byte hash and count.

For each task:
- **Fit:** 1,800 complete story blocks, derived deterministically from the official 2,000-story training source.
- **Validation:** 200 complete, disjoint story blocks, using the frozen seed `HLG-BABI-T3-T5-VALIDATION-v1`.
- **Confirmatory:** the 200 official test stories, byte-preserved and sealed until all candidate selection and configuration are frozen.

No story, statement, query or supporting-fact line may be split across partitions. The official test split is never used for fitting, threshold selection, debugging against labels or candidate promotion.

## 3. Structured input and leakage controls

The campaign consumes typed structured events and query annotations. It does **not** include natural-language parsing. The source-indexed annotation bundle must be independently checked and frozen before training/validation begins.

Every event and query has a story-scoped identity and exact source-line provenance. Model inputs exclude:
- gold answers;
- official supporting-line IDs;
- test labels;
- any target-event annotation copied from the gold supporting-fact column.

Gold answers and official support IDs are retained in a separate evaluator-only label bundle. They are joined only after a prediction is committed. Fit answers may be used after scoring to update task-outcome calibration; validation and confirmatory labels never update model state.

### Task 3 query semantics

A query of type `OBJECT_LOCATION_BEFORE_MOVE` supplies the object, destination and the identity of the exact target `MOVE` event. The target movement is independently identified from the question semantics and story timeline, not from gold support indices. The answer is the object's location immediately before that exact movement. The solver must account for PICK_UP, MOVE and DROP state transitions and event/observation cutoffs. This preserves the actual “before the kitchen/office/etc.” task semantics rather than substituting current-location QA.

### Task 5 query semantics

A query of type `GIVE_ROLE` supplies one or more bound roles and a distinct answer role. A match must satisfy every bound role within one single `GIVE(giver, object, recipient)` event. If multiple events match, use the most recent eligible event by event time and stable event ID. A role from one event must never be combined with a participant from another.

## 4. Matched HLA/HLB execution

Run both architectures under the same frozen conditions:
- Same structured event/query bundle, feature encoding, SOE configuration, `dt`, native kernels, cross-level gains and feature dimensions.
- Same per-seed story permutation, within-story event order, query order, observation cutoffs and forecast horizons.
- One online fit pass over the 1,800 fit stories. At each event, issue forecasts from the pre-event state, ingest the event, score only forecasts whose targets are now observable, and then apply only permitted learning updates.
- No parameter updates on validation or confirmatory stories.
- Fresh trusted model/runtime state for every architecture/task/seed. No state crosses seed or task boundaries.
- SOE decay/configuration and native dynamics remain frozen. This campaign does not adapt SOE kernels, native kernels or cross-level gains.
- Use a declared evidence/relation capacity of 16,384 records. Report HLB canonical-store occupancy and HLA caller-supplied evidence-window size separately.

HLA remains the no-persistent-relation-store baseline: it receives the complete evidence window for the current story from the evaluator. HLB uses its canonical evidence store with story-scoped retrieval and provenance. Neither architecture may retrieve evidence from another story. The distinction is intentional and must be reported, not hidden by giving HLA a persistent store.

### Seeds and pairing

Use exactly these ten seeds: `953000–953009`. For each seed, rank complete fit stories by SHA-256 of the protocol seed, task ID and story ID to obtain a deterministic permutation. Apply the identical permutation to HLA and HLB. Preserve source order inside each story. Confirmatory stories remain in fixed source order. Seeds measure order sensitivity/reproducibility; they do not create ten independent test datasets.

## 5. Learning conditions and ablations

Run six matched conditions:
1. `full_learning`
2. `no_temporal`
3. `no_relational`
4. `no_abstraction`
5. `no_task`
6. `no_learning`

Each condition receives exactly the same fit events, queries, forecast cutoffs and feedback schedule. A disabled channel must suppress only its designated learner updates. The no-learning condition still issues and scores predictions but performs zero online parameter updates.

The task reference solver and direct structured retrieval baseline are reported separately. They are not labelled as learned HLA/HLB performance.

## 6. Metrics

### Task 3
- Exact answer accuracy.
- Supporting-event recall against evaluator-only official support IDs.
- Temporal-order validity of recovered evidence.
- Abstention rate and answer coverage.

### Task 5
- Exact answer accuracy.
- Same-event role-binding accuracy.
- Witness recall against evaluator-only support IDs.
- Cross-event role-mixup rate.
- Abstention rate and answer coverage.

### Learning
- L0 feature forecast error by horizon.
- L1 event-type and complete role-binding exact accuracy.
- L2 context-transition accuracy where a defined target exists.
- Per-channel prediction loss, calibration, coverage and online update counts.

### Integrity
- False exact-witness rate.
- Missing-witness abstention.
- Provenance verification rate.
- Cross-story contamination count.
- Late-observation leakage count.
- Prediction/evidence cutoff violations.

### Operations
- Event/query throughput and wall time.
- HLB canonical-store occupancy.
- Prediction and eligibility journal sizes.
- Checkpoint size and restore time.

These measurements do not constitute the separate HLA/HLB cost/workload sweep.

## 7. Candidate selection and confirmatory lock

Candidate selection uses validation only. Rank candidates by:
1. exact-answer accuracy;
2. mandatory evidence-integrity gates;
3. L1 event/role forecast accuracy;
4. lower abstention;
5. stable candidate ID as final tie-break.

Any false exact witness, cross-story contamination, leakage violation, nonzero role-mixup on fully specified exact-match cases, or provenance-integrity failure rejects a candidate regardless of accuracy.

Before confirmatory execution, record and freeze:
- selected candidate fingerprints;
- implementation commit;
- protocol and criteria fingerprints;
- source and annotation manifest hashes;
- validation metrics and acceptance decisions;
- runtime/SOE/native configuration.

Then access the official test split once. No test-driven retuning, candidate promotion or protocol changes are permitted. Any later change requires a new protocol version and a new independent confirmatory source.

## 8. Statistical reporting

Report every seed separately, pooled micro and macro scores, exact denominators, and paired story-level bootstrap 95% intervals for HLA/HLB differences. Bootstrap units are stories, clustered within seed. Do not treat repeated seed runs over the same stories as independent confirmatory samples.

Ablation differences are reported by channel and task; no scalar aggregate may conceal an integrity failure or a task-specific regression.

## 9. Execution gates

- **G0 — Source verification:** archive and all eight split-file hashes, byte sizes and story counts re-verified.
- **G1 — Annotation freeze:** source-indexed event/query bundle generated without gold support leakage; independent annotation audit and bundle hashes committed.
- **G2 — Software acceptance:** current-head repository CI, H1 adapter/evidence acceptance and compiled-native smoke pass.
- **G3 — Development campaign:** fit/validation, six ablations, candidate rejection/promotion and artifact integrity complete; candidates frozen.
- **G4 — Confirmatory campaign:** official test accessed once, after G3 freeze.
- **G5 — Evidence ledger:** machine-readable results, artifact hashes, exact configurations and claim-boundary review committed.

G1 and G2 are hard gates before the learning campaign. G3 is a hard gate before confirmatory access.

## 10. Claim boundaries

This is a structured-event benchmark. It does not measure natural-language parsing, unrestricted semantic understanding, open-world reasoning, or general intelligence. Task 3 measures temporal object-state reconstruction around a specified movement; Task 5 measures same-event three-role binding and role-conditioned retrieval. Results from these two tasks cannot establish universal HLA/HLB superiority. The frozen H0 SOE/native stability evidence does not automatically extend to new learning rules or operating envelopes.
