# HLG bAbI expansion resource budget assessment v1.0

**Current status:** `PARTIAL_NO_LEARNING_ONLY`  
**Decision:** The existing preflight is not a full learning-campaign resource qualification.

## Evidence currently measured by the preflight

- Four concurrent workers, each assigned 90 of 360 deterministic run-unit keys.
- Per worker: 900,000 symbolic baseline query presentations, including one injected mid-shard failure and retry.
- Aggregate symbolic baseline workload: 3,600,000 query presentations; zero HLA/HLB learning updates; zero official-test queries.
- Each shard measures a deterministic native sample of eight fit stories per task for each of HLA and HLB: 48 story-runs per shard, 192 overall.
- Native no-learning evidence records event/native-step counts, per-story elapsed seconds, model-parameter immutability, peak RSS, Python allocation peak and native library pin.
- Symbolic shard evidence records elapsed time including retry, presentation throughput, peak RSS, Python allocation peak and artifact storage.
- Native projection is task- and architecture-specific, based on sampled story rate and event rate. Both are reported so readers can see the effect of task-specific story lengths. Projections are simple linear extrapolations of no-learning runtime only.

## What this does not measure

- HLA/HLB parameter-update compute for any learning condition.
- Growth of trainable state, optimizer/learning metadata or relation/context banks during a full campaign.
- Memory and time cost of repeated learning updates, checkpoint creation, candidate validation, consolidation, promotion or rollback.
- Runtime variability at full 3.6-million-presentation scale in the native learner.
- End-to-end duration when source acquisition, evaluator isolation and final confirmatory evaluation are included.

The native sample has only 32 stories per task/architecture across the four shards. The symbolic run units are orchestration and baseline measurements, not proxy learner updates. Do not multiply no-learning runtime by a generic factor and report that as learned runtime.

## Gate closure criteria

The resource gate remains open until one of the following is reviewed:
1. A separately authorized, bounded HLA/HLB learning microbenchmark covers representative tasks, conditions, event volumes, parameter updates, checkpoints and recovery, with per-task/architecture throughput and peak memory; or
2. A transparent learner-cost model is independently reviewed and anchored by measured update-level costs.

The assessment must include safety margins for parallelism, peak resident memory, artifact retention and retries. A microbenchmark is not permission to launch the 360-unit learning campaign. The full campaign remains `execution_authorized=false` until all gates pass and explicit authorization is given.


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
