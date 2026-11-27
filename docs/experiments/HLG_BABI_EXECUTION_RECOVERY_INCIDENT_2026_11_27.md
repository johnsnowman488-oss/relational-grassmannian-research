# bAbI HLA/HLB Campaign Execution Recovery

**Incident date:** 2026-11-27  
**Recovery branch:** `research/h1-babi-execution-recovery-v1`  
**Affected campaign:** HLG-BABI-T3-T5-LEARNING-v1.2.2

## Summary

The original matched campaign did not complete any seed-condition within its six-hour job limit. Its two prerequisite jobs succeeded, and all four matrix jobs entered the campaign runner. Each job wrote only its initial checkpoint; the runner did not persist useful progress until all phases of a seed-condition had completed.

The failure was not an HLA/HLB research result. It exposed multiple execution and protocol-boundary defects that needed separate corrections.

## Root causes and corrections

### 1. Per-exchange work scaled with retained history

The director captured a full adapter snapshot before every event exchange. That snapshot included growing prediction, observation, relation and source-evidence state. Prediction scoring also scanned the full prediction journal to find the active forecast for a target. Semantic pattern selection scanned its entire context bucket, and HLB campaign lookups repeatedly materialized/scanned all global evidence IDs.

Corrections on this branch:

- Replaced per-exchange full snapshots with a bounded transaction checkpoint for mutable native/SOE/readout and learner state.
- Added rollback-aware mutation journals for predictions, semantic-pattern counts, temporal weights and task outcomes.
- Added direct active-prediction and best-pattern indexes.
- Added constant-time source-evidence membership and story-scoped HLB witness recovery.
- Kept full snapshots for durable checkpoints; only the hot per-exchange rollback path changed.
- Kept HLB source event evidence and source relation observations append-only across failed candidate exchanges.

### 2. Same-time observations were rejected as forecast targets

The strict prediction contract requires the target observation to be strictly later than the forecast's evidence cutoff. The input timeline can contain observations with the same timestamp. The old campaign treated that valid non-scoreable case as a fatal exception during confirmatory processing.

Correction:

- A prediction whose target is at or before its evidence cutoff is now explicitly marked `WITHDRAWN`.
- The observation and evidence are still retained.
- It is not scored, and the strict score cutoff remains unchanged.
- The withdrawal is transactionally reversible.
- Campaign results expose prediction lifecycle counts.

This preserves causal correctness rather than relaxing the cutoff or silently counting a noncausal score.

### 3. HLB capacity was sized below the complete per-run source journal

HLB preserves source events and source relation projections across warm-start, online adaptation, validation and generated confirmatory phases for one seed-condition. The previous capacity of 65,536 only appeared sufficient when viewed against a subset of the campaign.

Frozen input counts:

| Task | Source events retained | Typed relation projections |
|---|---:|---:|
| Task 3 | 154,786 | 154,786 |
| Task 5 | 61,532 | 73,971 |

Correction:

- HLB capacity is 262,144 for the evidence store, canonical relation store and source relation journal.
- A preflight now counts the complete input workload before a seed-condition starts.
- Capacity requirements and the preflight result are recorded in the campaign source manifest.
- A future input expansion above capacity fails before the expensive campaign begins.

### 4. Native binary provenance path was incorrect

The earlier result manifest attempted to hash the vendored Aberconics build output, although CI executes the downloaded, checksum-verified binary under `GFE_CORE_LIB`. This produced a null native library hash in completed HLA pilot outputs.

Correction:

- Campaign provenance now resolves the exact `GFE_CORE_LIB` path first.
- It requires that file to exist and records both its resolved path and SHA-256.
- A campaign cannot emit a supposedly complete result with an unknown native binary hash.

## Progress and recovery behavior

The campaign writes an atomic progress sidecar at phase start, every 25 stories, at phase completion and after the final seed-condition. It records task, architecture, seed, ablation, phase, story and query counts, native steps, elapsed time and completed condition count. The upload step runs even after failure, preserving progress for inspection.

The recovery branch runs a bounded pilot: seed `953000`, `full_learning` only, for each of the four task/architecture combinations. This is an execution and contract gate, not the matched research campaign. The complete 10-seed × 6-condition campaign remains gated on successful four-way pilot evidence.

## Pilot evidence observed so far

The first post-optimization pilot on commit `c9de8d810b24f787027d83e1d1054832151145f3` exposed the same-time case and old HLB capacity. It also completed both HLA full-learning pilots:

| Task / architecture | Result | Elapsed | Validation candidate |
|---|---|---:|---|
| Task 3 — HLA | Completed all four phases | ~237 s | Accepted |
| Task 5 — HLA | Completed all four phases | ~164 s | Accepted |
| Task 3 — HLB | Failed at old 65,536 source-relation capacity | — | Not evaluated |
| Task 5 — HLB | Failed at old 65,536 source-relation capacity | — | Not evaluated |

The HLA pilot results showed 100% exact task-answer accuracy and 100% support-witness recall on eligible queries, with no false cross-story witnesses or provenance failures. Task 5 contained same-time observations that were correctly quarantined (not scored). These task-answer figures are produced by the deterministic evidence-backed task solver; they are **not** evidence that learned prediction alone answers bAbI. Separate prediction metrics and learner-state changes are recorded independently.

The HLA pilot outputs on that commit predate the native-library hash correction. They must not be treated as provenance-complete final artifacts.

The four-way pilot on the capacity-corrected code is currently the next acceptance gate. Do not infer HLB success until its completed artifacts are inspected and the preflight, capacity, witness, provenance and runtime invariants all pass.

## Acceptance gates before the full campaign

1. Repository unit/invariant CI passes on Python 3.10 and 3.12.
2. All four bounded pilots finish with `complete=true`, exactly one result each, and no missing/duplicate seed-condition.
3. Each artifact has matching task/architecture/seed/variant identity and frozen input hashes.
4. Native runtime path, pinned commit and actual loaded-library SHA-256 are present and match the downloaded runtime artifact.
5. HLB source event and relation counts remain within the configured capacity; no capacity misses occur.
6. HLA and HLB preserve the one-native-step-per-adapter-tick invariant.
7. Validation and confirmatory scoring do not mutate the accepted candidate fingerprint.
8. No false witnesses, provenance failures or cross-story witness leakage occur; support-witness recall is reported separately from exact task-answer accuracy.
9. Prediction lifecycle status counts account for scored, withdrawn and remaining issued forecasts; same-time/late observations never become causal forecast scores.
10. Only after all four pilots pass should the full matched 10-seed × 6-condition campaign be launched.

## Research boundary

This incident changes runtime execution and evidence integrity, not the frozen task, split, seed or ablation definitions. HLA/HLB comparison remains open. No architecture winner or learning-advantage claim is supported by the bounded pilots alone.
