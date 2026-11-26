# bAbI Tasks 3 and 5 — HLA/HLB Learning Protocol v1.2

**Protocol ID:** HLG-BABI-T3-T5-LEARNING-v1.2  
**Status:** FROZEN — 2026-11-26; execution gated on G0/G1/G2 acceptance  
**Supersedes:** v1.1 before any model training, candidate selection or confirmatory evaluation  
**Scope:** structured-event learning and retrieval; natural-language parsing is excluded.

## 1. Protocol revisions and claim boundary

The official `en-10k` test labels were inadvertently inspected during preprocessing debugging. The separate official `en` test files were then checked and found to overlap the `en-10k` training/test story corpus exactly (Task 3: 200/200 story blocks). Neither official test configuration can serve as independent confirmation. Both are quarantined and excluded from all campaign metrics and candidate selection.

Protocol v1.2 therefore uses:
- Official `en-10k` training source for fit and validation.
- A deterministic, independently generated **bAbI-compatible structured challenge** for confirmatory evaluation.

The generated challenge is not an official bAbI test set. Results must be reported as structured-event challenge results, not as official bAbI test-set performance.

## 2. Research questions

**Task 3 — Three Supporting Facts:** reconstruct an object's location immediately before a semantically identified movement to a queried destination, integrating pickup, movement and drop/discard events while preserving the supporting event chain.

**Task 5 — Three Argument Relations:** represent each GIVE as one n-ary event `GIVE(giver, object, recipient)`, answer role-conditioned queries, and prevent participant roles from being assembled across different event identities.

The campaign reports four distinct outcomes: task-query retrieval, learned event prediction, evidence integrity and operational behaviour. Task-query retrieval is a deterministic structured-evidence executor, not a learned answer-generation model. It must not be presented as proof that the prediction learners have learned the task.

## 3. Data partitions

### Official fit and validation source

Use the pinned official bAbI v1.2 English `en-10k` training source:
- **Fit:** 1,800 complete story blocks per task.
- **Warm-start:** 1,200 stories, deterministically selected from fit by SHA-256 story-ID ranking.
- **Online adaptation:** the remaining 600 fit stories, disjoint from warm-start.
- **Validation:** 200 complete stories, disjoint from all fit stories, selected by the frozen validation seed.

Warm-start and online-adaptation counts are per task. Whole stories, all statements, all queries and supporting lines remain together. The official `en-10k` test files are retained only as quarantined provenance and never scored.

### Independent generated confirmatory challenge

Generate exactly 200 stories per task, five queries per story (1,000 queries per task), using:
- Task 3 seed: `953900`.
- Task 5 seed: `953901`.
- Generator: `src/rgm/experiments/babi_synthetic_confirmatory.py`.
- Novel entity vocabulary disjoint from all fit/validation entity IDs.

The G1 bundle contains confirmatory inputs only. It emits no answers or supporting-event labels. At G4, after candidate freeze, the evaluator derives gold answers and witnesses from the fixed structured generator and query semantics. The generated challenge is deterministic and its input hash, story fingerprints, seeds and exact counts are recorded.

## 4. Structured event annotation

The official source-template compiler is a narrow deterministic benchmark adapter, not general NLP. It converts:
- Task 3: MOVE, PICK_UP and DROP, including source variants such as `got ... there`, `took`, `picked up`, `left` and `discarded`.
- Task 5: GIVE in active/passive forms, plus MOVE/PICK_UP/DROP distractors present in the same stories.

Model inputs contain story-scoped event/query IDs and exact source-line provenance. Fit/validation gold answers and official support IDs are isolated in separate evaluator label streams. Confirmatory generation emits input records only; label derivation is deferred to G4.

Task 3 query anchoring is derived from the question destination and timeline: the target is a MOVE by the actor currently holding the queried object. Gold support indices are not used to select it.

Task 5 queries contain bound roles and a distinct answer role. All bound roles must match within one GIVE event.

## 5. Matched HLA/HLB learning schedule

Run both architectures with identical event/query streams, feature encodings, per-seed story order, prediction cutoffs, horizons, SOE configuration and native parameters.

For each architecture/task/seed:

1. **Warm-start fit:** initialise the L0 feature predictor, typed relation-pattern learner, n-ary event-role learner and context-transition learner from the 1,200 warm-start stories only, using the existing `LearningRuntime.fit_* (partition="fit")` APIs.
2. **Warm-start dynamics:** process those stories through the hierarchical runtime in score-only mode (`learn=False`) to establish matched SOE/native state and retain source evidence without changing learned parameters.
3. **Online adaptation:** process the 600 disjoint online-adaptation stories in source order with `learn=True`. Issue predictions from the pre-event state, ingest evidence, score newly observable targets, then route only permitted learning updates. Fit labels may update task-outcome calibration only after the answer is committed.
4. **Validation:** process all 200 validation stories in score-only mode. Predictions are evaluated, but no learner, temporal eligibility or task calibrator is updated.
5. **Confirmatory:** after candidate fingerprints and validation decisions are frozen, process the generated challenge in score-only mode. No confirmatory observation updates candidate parameters.

Each bAbI story is an independent temporal episode. At every story boundary, reset all SOE banks and restore the persistent native hierarchy to its zero-state baseline while preserving the native handle and cumulative native step count. Reset transient eligibility at the same adapter tick through the journalled `LearningRuntime.reset_episode_eligibility` operation. Learned predictors, temporal-credit parameters, prediction history and HLB's append-only canonical evidence store persist across stories; query retrieval remains story-scoped. The episode-boundary marker must participate in deterministic checkpoint replay.

The director's explicit `learn=False` path must still issue and score predictions, advance native/SOE state and retain HLB source evidence, while suppressing learner updates and temporal eligibility advancement. The acceptance suite must verify this invariant.

Use ten paired seeds `953000–953009`. The same SHA-256-ranked story order is used for HLA and HLB and for all ablations within each seed. Within-story source order is preserved. Fresh trusted state is created for every architecture/task/seed.

Freeze SOE decay/configuration, native kernels, cross-level gains, `dt` and feature dimensions. This campaign does not adapt the dynamical substrate.

The matched runtime configuration is fixed as follows:
- SOE feature dimensions: L0=2, L1=3, L2=4.
- SOE decay rates: L0=(0.1, 0.4), L1=(0.2, 0.7), L2=(0.05, 0.3).
- Native kernel `gamma`: the reverse of the corresponding SOE decay-rate vector; `w=(0.5, 0.5)` at each level.
- `dt=0.01`; use the frozen H0 default cross-level edge specification.
- Native runtime: `gfe_ctypes.create_persistent_hierarchy_runtime` from Aberconics framework commit `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de`. Each adapter owns one actual persistent C++ hierarchy handle. The bridge injects all three levels' SOE feedback simultaneously and the native runtime commits exactly one step per director exchange. Record the built `libgfe_core.so` SHA-256 in every campaign artifact.

### SOE-to-temporal-credit contract

For every source event during online adaptation, capture the **pre-step** SOE bank snapshots before the current observation is injected. For each of the two SOE channels at each of the three levels, calculate the L2 norm of that channel's feature vector and append one event-resolved eligibility item:
- `feature_id=soe_l{level}_c{channel}` and the same channel key;
- event identity, event time, observation time and the next observed tick;
- magnitude equal to the pre-step SOE channel-vector norm;
- the frozen SOE configuration fingerprint.

This yields six trace-derived eligibility features per source event. The eligibility ledger uses decay `0.9`, capacity **131,072**, and no silent eviction. The L0 prediction residual updates temporal credit against the current and decayed prior event eligibility values. Thus SOE traces contribute through an explicit, inspectable projection; the system does not invert aggregate SOE state into unique causal event contributions. Eligibility is not advanced or ingested in score-only phases.

### Evidence-store parity

HLA remains the no-persistent-relation-store baseline and receives the current story's complete caller-supplied evidence window for query execution.

HLB uses its one canonical persistent evidence/relation store, with story-scoped retrieval and exact provenance. Cross-story retrieval is forbidden. Set HLB evidence capacity to **65,536 records**, report actual occupancy and abstentions, and do not evict protected evidence. This capacity is intended to hold the complete campaign's source events; any exhaustion remains an explicit failure/abstention result.

## 6. Error channels and ablations

Run six matched conditions:
1. `full_learning`
2. `no_temporal`
3. `no_relational`
4. `no_abstraction`
5. `no_task`
6. `no_learning`

All variants receive the same warm-start examples, online-adaptation stream, validation stream and confirmatory inputs. A disabled channel suppresses only its designated learner updates. The no-learning control still issues and scores forecasts but makes zero learner updates.

Temporal prediction errors and SOE-informed event eligibility remain distinct from semantic relation errors, n-ary event-role errors, context-transition errors and task-outcome errors.

## 7. Metrics

**Task 3:** exact answer accuracy, supporting-event recall, temporal-order validity, abstention and coverage.

**Task 5:** exact answer accuracy, same-event role-binding accuracy, witness recall, cross-event role-mixup rate, abstention and coverage.

**Learning:** L0 feature forecast error by horizon; L1 relation-pattern and complete n-ary event-role exact accuracy; L2 context-transition accuracy; per-channel loss, calibration, coverage and update counts. Report warm-start, online-adaptation, validation and confirmatory phases separately.

**Integrity:** false exact-witness rate, missing-witness abstention, provenance verification, cross-story contamination, late-observation leakage and prediction/evidence cutoff violations.

**Operations:** event/query throughput, wall time, HLB canonical-store occupancy, prediction/eligibility journal size, checkpoint size and restore time. This is not the separate HLA/HLB cost/workload sweep.

## 8. Candidate selection and confirmatory lock

Candidate selection uses validation only:
1. All evidence/provenance and leakage gates must pass.
2. Task-query exact answer accuracy must meet the frozen acceptance threshold (100% on fully specified structured queries).
3. Maximise L1 complete event-role/relation forecast accuracy.
4. Minimise L0 feature forecast error.
5. Minimise abstention; stable candidate ID is the final tie-break.

Any false exact witness, cross-story contamination, leakage violation, role-mixup on fully specified queries, or provenance-integrity failure rejects a candidate regardless of accuracy.

Before G4, freeze candidate fingerprints, implementation commit, protocol/criteria fingerprints, source and annotation manifests, generator seed/input hashes, validation metrics and acceptance decisions. Then run the generated confirmatory challenge once. No confirmatory-driven retuning or candidate promotion is permitted.

## 9. Statistical reporting

Report each seed, pooled micro/macro scores, exact denominators, and paired story-level bootstrap 95% intervals. Bootstrap units are stories clustered within seed. Repeated seeds over the same stories are not independent confirmatory samples.

## 10. Execution gates

- **G0:** verify pinned archive and all en-10k fit/validation source hashes; retain official test files as quarantined only.
- **G0.5:** verify deterministic challenge generation, exact story/query counts, novel entity vocabulary and input hashes; no labels emitted.
- **G1:** source-indexed fit/validation annotation, independent oracle audit and warm-start/online-adaptation split freeze.
- **G2:** score-only lifecycle acceptance, full repository CI, H1 adapter/evidence tests and compiled-native smoke.
- **G3:** ten-seed fit/online/validation campaigns and six ablations; select and freeze candidates.
- **G4:** one-time generated confirmatory challenge after G3 freeze.
- **G5:** publish artifacts, hashes, evidence ledger and claim-boundary review.

G0–G2 are hard gates before learning runs. G3 is a hard gate before confirmatory scoring.

## 11. Claim boundaries

The experiment measures structured-event learning and retrieval, not natural-language parsing, unrestricted semantic understanding, open-world reasoning or general intelligence. The synthetic confirmatory challenge is not an official bAbI test set. These two tasks cannot establish universal HLA/HLB superiority. H0 SOE/native stability evidence does not automatically extend to new learning rules or operating envelopes.
