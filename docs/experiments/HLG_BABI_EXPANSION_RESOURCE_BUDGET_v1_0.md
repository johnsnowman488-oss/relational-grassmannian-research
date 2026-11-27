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
