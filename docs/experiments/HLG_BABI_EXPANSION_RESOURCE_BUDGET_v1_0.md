# HLG bAbI expansion resource budget assessment v1.0

**Current status:** `PARTIAL; ACCEPTED_NO_LEARNING_PREFLIGHT_PLUS_QUARANTINED_UNAUTHORIZED_LEARNING_DIAGNOSTIC`  
**Decision:** The existing preflight is not a full learning-campaign resource qualification.

## Evidence currently measured by the preflight

- Four concurrent workers, each assigned 90 of 360 deterministic run-unit keys.
- Per worker: 900,000 symbolic baseline query presentations, including one injected mid-shard failure and retry.
- Aggregate symbolic baseline workload: 3,600,000 query presentations; zero HLA/HLB learning updates; zero official-test queries.
- Each shard measures a deterministic native sample of eight fit stories per task for each of HLA and HLB: 48 story-runs per shard, 192 overall.
- Native no-learning evidence records event/native-step counts, per-story elapsed seconds, model-parameter immutability, peak RSS, Python allocation peak and native library pin.
- Symbolic shard evidence records elapsed time including retry, presentation throughput, peak RSS, Python allocation peak and artifact storage.
- Native projection is task- and architecture-specific, based on sampled story rate and event rate. Both are reported so readers can see the effect of task-specific story lengths. Projections are simple linear extrapolations of no-learning runtime only.

## What the accepted preflight does not measure

- HLA/HLB parameter-update compute for any learning condition.
- Growth of trainable state, optimizer/learning metadata or relation/context banks during a long-lived multi-story campaign.
- Memory and time cost of full candidate validation, consolidation, promotion or rollback orchestration.
- Runtime variability at full 3.6-million-presentation scale in the native learner.
- End-to-end duration when source acquisition, evaluator isolation and final confirmatory evaluation are included.

The native no-learning sample has only 32 stories per task/architecture across the four shards. The symbolic run units are orchestration and baseline measurements, not proxy learner updates. A separate learning-enabled sample was later executed automatically by mistake; it is quarantined in the final section and is not accepted resource-gate evidence. Do not multiply no-learning runtime by a generic factor or treat the quarantined sample as a full-campaign forecast.

## Gate closure criteria

The resource gate remains open until one of the following is reviewed:
1. A separately authorized, bounded HLA/HLB learning microbenchmark covers representative tasks, conditions, event volumes, parameter updates, checkpoints and recovery, with per-task/architecture throughput and peak memory; or
2. A transparent learner-cost model is independently reviewed and anchored by measured update-level costs.

The assessment must include safety margins for parallelism, peak resident memory, artifact retention and retries. A microbenchmark is not permission to launch the 360-unit learning campaign. The full campaign remains `execution_authorized=false` until all gates pass and explicit authorization is given. A learning-cost benchmark itself also requires explicit authorization; workflow automation must not infer consent from a passing no-learning preflight.


## Observed preflight evidence — 2026-11-27

**Accepted controlled preflight:** run #61, ID `46066166623`, commit `02538ee794ddd9df67297d4256b752ebf2c01894`.  
**Result:** PASS. [GitHub Actions run](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/46066166623)  
**Aggregate artifact:** `babi-expansion-preflight-acceptance`, artifact ID `15231091582`, GitHub artifact digest `sha256:d81b1c0adf1f12c604234e35f45dc7b1a5e474cdcc69458e63aa18e215e59c4d`.

### Four-worker symbolic workload

| Measure | Observed value |
|---|---:|
| Run units expected / accepted | 360 / 360 |
| Run units per shard | 90 / 90 / 90 / 90 |
| Query presentations | 3,600,000 |
| Baseline prediction presentations | 7,200,000 |
| Learning updates / official-test queries | 0 / 0 |
| Sum of worker elapsed times (includes retries) | 220.768 s |
| Slowest worker elapsed time | 66.649 s |
| Maximum worker peak RSS | 99.586 MiB |
| Maximum Python allocation peak | 1.326 MiB |
| Total shard evidence storage | 2,229,711 bytes (2.126 MiB) |
| Sum-normalized query throughput | 16,306.7 query presentations / worker-second |

Per-shard elapsed times were 48.155 s, 66.649 s, 53.674 s and 52.290 s. Each shard completed 900,000 query presentations and retained exactly 90 unit artifacts. Injected failure/retry elapsed time was included in the measurements. Aggregate retry integrity: 360 unique keys, zero duplicates, zero missing keys, zero wrong-shard keys and zero manifest mismatches.

### Pinned native HLA/HLB no-learning sample

Native ABI commit: `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de`. Across all four shards, the sample covered 192 story-runs and 1,692 native observation steps in 22.442 cumulative seconds. Maximum process peak RSS was 173.450 MiB; maximum Python allocation peak was 48.344 MiB. The run asserted zero learner parameter changes, zero learning updates and zero loaded evaluator labels.

Task/architecture-specific projections are linear extrapolations of this **no-learning** sample only:

| Task / architecture | Sample stories / events | Measured stories/s | Measured events/s | Projected no-learning seconds (story rate / event rate) |
|---|---:|---:|---:|---:|
| Task 11 / HLA | 32 / 320 | 38.591 | 385.907 | 3,109.6 / 3,109.6 |
| Task 11 / HLB | 32 / 320 | 37.660 | 376.598 | 3,186.4 / 3,186.4 |
| Task 14 / HLA | 32 / 366 | 30.857 | 352.923 | 3,889.0 / 3,978.9 |
| Task 14 / HLB | 32 / 366 | 31.910 | 364.968 | 3,760.6 / 3,847.6 |
| Task 19 / HLA | 32 / 160 | 68.170 | 340.851 | 8,801.5 / 8,801.5 |
| Task 19 / HLB | 32 / 160 | 68.257 | 341.284 | 8,790.3 / 8,790.3 |

The projected sample counts/throughput are task- and architecture-specific. They are not full-campaign forecasts: they exclude parameter updates, learning-state growth, checkpoints, validation, consolidation, promotion, rollback and retry costs of the learner itself. In particular, do not read these projections as the runtime of the 360 learning runs.

### Resource decision

The measured symbolic orchestration, artifact storage and native no-learning runtime gates pass for this preflight workload. The resource-budget gate remains **`PARTIAL_NO_LEARNING_ONLY`** because actual HLA/HLB learning-update compute, trainable state growth and checkpoint/rollback costs have not been measured. Closure still requires a separately authorized bounded learner microbenchmark or a reviewed cost model grounded in measured update-level costs. This report is not authorization to run either that microbenchmark or the full learning campaign.


## Quarantined learning-cost diagnostics — not accepted gate evidence

**Process incident:** the PR workflow initially attached the learning-enabled microbenchmark directly to successful no-learning aggregate completion. This caused two duplicate automatic runs on commit `db0b34c970b8ffabaf5d96d8928cfb4979bf970c` without explicit user authorization. Both completed successfully, but both are recorded as **UNAUTHORIZED_DIAGNOSTICS_NOT_GATE_EVIDENCE**. The aggregates explicitly retained `execution_authorized=false`.

| Run | ID | Aggregate artifact | Artifact digest |
|---|---:|---:|---|
| #97 | `46071079818` | `15233515418` | `sha256:380eda01825aef8e60eb5d49fed84eae91da231d3286ccdff3fd8c6196ba058e` |
| #98 | `46071085170` | `15232928490` | `sha256:c85394a61ce3e986ab0914be0b44b929c238e15a4c035a3519696d5a839dc58b` |

Each run sampled 192 fit-story episodes (eight per task per shard, both HLA and HLB), 1,692 events/native steps total, with a fresh adapter per story. All 192 episodes showed a learner-state change. Neither run loaded evaluator labels, official-test queries or generated-confirmatory labels.

| Measure | Run #97 | Run #98 |
|---|---:|---:|
| Measured episode update time (sum across the 192 episodes) | 7.439 s | 6.272 s |
| Event throughput normalized by episode update time | 227.45 events/s | 269.78 events/s |
| LearningRuntime snapshot time (sum) | 0.260 s | 0.225 s |
| LearningRuntime restore time (sum) | 0.337 s | 0.286 s |
| Serialized LearningRuntime checkpoint payload (sum) | 7,959,286 bytes | 7,959,286 bytes |
| Maximum worker peak RSS | 181.461 MiB | 181.480 MiB |
| Maximum worker Python allocation peak | 48.555 MiB | 48.555 MiB |
| Sum of worker wall times | 32.933 s | 28.130 s |

Per task/architecture, mean episode update times ranged from 18.4–22.4 ms (Task 19 HLA), 19.4–23.0 ms (Task 19 HLB), 37.0–43.7 ms (Task 11 HLA), 37.5–44.1 ms (Task 11 HLB), 41.2–49.0 ms (Task 14 HLA) and 42.4–50.3 ms (Task 14 HLB).

**Interpretation limits:** the sample used fresh adapters for every story. It measured native event ingestion with existing H1 learner updates enabled, per-episode learner-state deltas, learned journal rows, eligibility/temporal state, and Python LearningRuntime snapshot/restore time and serialized size. It did **not** measure persistent parameter/bank growth across successive stories on one learner, full native/runtime checkpoints, candidate validation, consolidation, promotion, rollback orchestration, full 360-unit learning campaign cost, or learning/generalisation performance. It is a useful debugging and rough initial cost diagnostic, but it cannot close the formal resource gate because it was not authorized and the lifecycle sample is incomplete.

### Workflow correction

The workflow now exposes `workflow_dispatch` with a required boolean `enable_learning_cost_microbenchmark` defaulting to `false`. The learning-cost jobs run only when that boolean is explicitly set to `true` on a manual dispatch **and** the preceding no-learning aggregate succeeds. PR/push-triggered runs skip the learning-cost jobs. No further benchmark should be launched without explicit user authorization. The 360-unit learning campaign remains separately frozen and unauthorized.


## Task 11-only persistent learner qualification — superseding execution scope

**Scope decision (2026-11-27):** Task 11 is the only active expansion task. Tasks 14 and 19 are locked and excluded from this qualification. The earlier three-task fresh-adapter diagnostics (#97/#98) remain quarantined and are not reused.

The replacement qualification runs four shards. Each shard processes 32 whole Task 11 fit stories through one persistent HLA adapter and one persistent HLB adapter. Across the four shards this yields 128 sequential story updates per architecture. The same learner, H1 director, evidence store and native runtime persist within each shard. Weak supervision remains story-local, so a pronoun in a new story cannot bind to an entity observed in a previous story.

The sample records, after each story:
- native event/update time and event throughput;
- full director/adapter and native-runtime checkpoint size;
- snapshot and restore latency, plus equality of the restored state fingerprint;
- observation-journal, temporal-credit and eligibility growth;
- worker peak RSS, Python allocation peak and retained evidence size.

The Task 11 source freeze and plan contain only Task 11 members and partitions. Validation labels, official-test inputs/queries and generated-confirmatory labels are excluded. Tasks 14/19 are not parsed or run. Task 3/5 remain untouched.

**Acceptance rule:** all four shards must provide exactly 32 unique fit stories for both HLA and HLB; each architecture must show persistent learner changes; checkpoint recovery fingerprints must match after every story; source event/native tick counts must agree; and all label-isolation counters must remain zero. The aggregate reports measured costs and limitations without claiming learning effectiveness.

A passing aggregate closes the bounded Task 11 resource-qualification gate for proceeding to the Task 11-only campaign. It is not a guarantee of full-campaign wall-clock or memory usage; the campaign itself retains per-run timeouts, artifact retention, retries, and worker-level memory monitoring.
