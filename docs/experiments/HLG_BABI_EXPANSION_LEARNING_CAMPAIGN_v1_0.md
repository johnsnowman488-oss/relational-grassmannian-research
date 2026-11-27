# HLG bAbI Expansion Learning Campaign — Frozen Protocol v1.0

**Status:** FROZEN — NOT AUTHORIZED  
**Tasks:** 11 (coreference), 14 (temporal reasoning), 19 (path finding)  
**Architectures:** HLA and HLB  
**Run units:** 360 matched units  
**Concurrency:** four isolated workers  
**Execution:** not authorized; no learning campaign has been launched

## 1. Freeze boundary

This document freezes the experimental design, seed set, ablation semantics, metrics, thresholds, workload arithmetic, sharding and evidence requirements. It authorizes protocol implementation and preflight only. It does **not** authorize training, online learning, validation runs, confirmatory runs or official-test access.

Task 3/5 remains the independent frozen pilot. Tasks 13, 2 and 4 are outside this first wave.

## 2. Source and partitions

Use only the individually pinned Phase Q source members in the bAbI v1.2 English `en-10k` freeze manifest. The original full tarball was not acquired; no archive-byte identity claim is made.

| Task | Fit | Validation | Official test |
|---|---:|---:|---:|
| 11 | 1,800 stories / 9,000 queries | 200 / 1,000 | 200 / 1,000 |
| 14 | 1,800 / 9,000 | 200 / 1,000 | 200 / 1,000 |
| 19 | 9,000 / 9,000 | 1,000 / 1,000 | 1,000 / 1,000 |

Fit and validation are deterministic, whole-story disjoint partitions. Split the fit partition again by whole story: 80% warm-start, 20% online adaptation, using the frozen nested seed in the JSON. Exact query counts for those nested partitions are emitted from the actual partition manifest; they are not inferred from story fractions. Validation is read-only. Official test inputs and labels remain sealed.

## 3. Matched design

- **Seeds:** 953100–953109 inclusive (10 seeds).
- **Architectures:** HLA, HLB.
- **Conditions:** `full_learning`, `no_temporal`, `no_relational`, `no_abstraction`, `no_task`, `no_learning`.
- **Matched run unit:** task × architecture × condition × seed.
- **Total:** 3 × 2 × 6 × 10 = **360 run units**.
- Every run starts from a clean model/native runtime. No state crosses task, seed, architecture or condition.
- HLA/HLB receive identical story order, seed, phase assignments, feature projection, query order and forecast horizons.

The six conditions are one-factor-off ablations plus a no-learning control. Temporal ablation disables temporal eligibility/credit and L0 feature-predictor updates; relational ablation disables L1 relation/path updates; abstraction ablation disables L2 context and event-role abstraction; task ablation disables task-answer reliability calibration; no-learning disables every learning update while retaining inference and scoring.

## 4. Task-specific targets and baselines

| Task | L0 grounding | L1 relation | L2 context | Non-oracle baselines |
|---|---|---|---|---|
| 11 | mention/entity binding | COREFERS_TO edge | entity state | nearest-compatible antecedent; recency-only |
| 14 | temporal anchor | BEFORE/AFTER precedence | temporal context | source-order-only; lexical temporal-cue rule |
| 19 | directed spatial edge | ordered path composition | route context | direct-edge-only; breadth-first search |

The query answer is a separate L2 task target. L0, L1 and L2 forecasts are scored against their own target observations; query-answer exact match must not stand in for the three level-specific scores.

Oracle symbolic predictors are diagnostic upper bounds only. They are excluded from candidate selection and from the strongest non-oracle baseline comparison.

## 5. Metrics and acceptance thresholds

Report task, architecture, condition and seed separately. Use 10,000 story-clustered paired bootstrap resamples and 95% intervals. Do not publish a pooled cross-task score or rank.

Common measures: answer exact match, support-witness recall, false-witness rate, abstention, forecast coverage, L0 accuracy, L1 exact match, L2 accuracy, per-story latency and peak memory.

Task 11 adds mention/entity accuracy, antecedent top-1, coreference-edge F1, entity-chain exact match, false-binding rate and cross-story binding count. Task 14 adds temporal parse/order accuracy, before/after F1, temporal witness recall, contradiction rate and causal-cutoff violations. Task 19 adds edge direction, inverse consistency, path exact match, path-length error, intermediate-node sequence accuracy, edge-witness recall, invalid composition and false-path rate.

A validation candidate is eligible only if all of the following hold:
- zero cross-story bindings, causal-cutoff violations, false witnesses, invalid path compositions, false paths, witness-recovery mismatches, partition overlaps and evaluator-label leaks;
- inverse-relation consistency is 1.0;
- forecast coverage is at least 0.90;
- support-witness recall is at least 0.95;
- Task 11 false-binding rate is at most 0.01;
- query-answer exact match is at least the strongest non-oracle baseline on the same validation queries.

If no seed passes every gate for a task/architecture, no confirmatory candidate is selected. Candidate selection is independent per task and architecture, using full-learning validation runs only. Tie-break by higher answer exact match, then higher witness recall, then lower seed.

## 6. Workload and four-way sharding

The frozen workload is **360 run units** and **3.6 million query presentations**: 360 × (9,000 fit + 1,000 validation). Across all units, the corresponding story presentations total 1.68 million. These are presentation counts, not wall-clock estimates.

Use four workers, each assigned 90 run units. Enumerate the run manifest in stable order and assign index modulo four to shard 0–3. Each worker writes to a unique run-id/shard-id evidence directory, created before any execution. No shared output paths. Aggregate only after all four shards finish and verify all 360 keys occur exactly once.

The workflow must use a run-id-specific concurrency group and `cancel-in-progress: false`. Retries target only failed shard/unit keys; completed artifacts remain immutable. Upload evidence even on failure. Before authorization, a representative non-learning preflight must measure event counts, memory, wall-clock and storage; no runtime estimate is invented here.

## 7. Confirmatory and test isolation

Generated confirmatory challenges are a later, separate phase. Freeze their generator, seeds, novel-entity/topology rules, label separation and hashes after validation candidate selection. They are not official bAbI test data. Official test files remain sealed and are not used for model selection, threshold setting or confirmatory scoring.

## 8. Acceptance evidence and remaining launch gates

The runtime/prediction-contract integration merged as PR #53 at commit `0e4da940644033b784fc65a4ef2b4ab64b66f7ba`. Acceptance runs `45995326040` and `45995337324` passed on Python 3.10 and 3.12. Each matrix job passed 15 expansion adapter/runtime tests, 60 integrated evidence/prediction lifecycle tests and 40 frozen Task 3/5 regression tests.

Before launch:
1. Implement and review the task-specific non-oracle baselines.
2. Implement the nested whole-story warm-start/online partition manifest.
3. Implement the four-shard runner, deterministic aggregation and failure-proof evidence upload.
4. Run the non-learning resource/artifact preflight and publish measured budgets.
5. Freeze the generated confirmatory challenge protocol.
6. Obtain explicit authorization to launch.

**The campaign is frozen as a protocol, not started.**
