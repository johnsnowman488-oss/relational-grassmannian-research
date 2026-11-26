# H1 architecture-level evidence review — HLA vs HLB

**Review ID:** HLG-H1-ARCHITECTURE-EVIDENCE-REVIEW-v1  
**Date:** 2026-11-26  
**Status:** evidence review complete; no architecture selected as universal winner  
**Evidence base:** frozen H1 validation/confirmatory campaigns, compiled-runtime smoke and rollback, P6 v4 full-runtime campaign, and the companion P6 resource audit.

## 1. Executive finding

HLA and HLB are both viable implementations of the shared three-level hierarchy contract on the tested compiled Aberconics M4 runtime. The evidence does not support replacing one with the other across all workloads.

The meaningful architectural distinction is not native numerical stability: the matched native hierarchy and P6 trajectories are identical in the tested configuration. The distinction is how relational evidence survives between observations:

- **HLA** is a readout-and-current-evidence architecture. It avoids a persistent relation-instance store. Exact path claims are checked against evidence supplied for the query; learned upper-level outputs remain explicitly abstract predictions.
- **HLB** adds one bounded canonical typed relation-instance store with level-scoped indexes and witness-preserving composition. It can answer from retained observations during a no-replay outage, but incurs persistence, capacity, indexing, and consistency obligations.

The confirmatory evidence demonstrates a narrow but decisive HLB advantage when previously observed evidence is unavailable for replay. When evidence is replayed, HLA catches up. On the tested composition, delayed-arrival, and negative-control cases, the two architectures otherwise match.

**Decision:** retain both architectures. Use HLA as the no-store reference and resource/complexity baseline; use HLB where retained relational evidence is a required capability. Do not call HLB the overall winner, and do not infer a general Leptograph or Grassmannian advantage from these tests.

## 2. Evidence ledger

### 2.1 Shared implementation and runtime

Both adapters use the same H0 three-level topology, SOE bridge, native kernel configuration, timestep, readout dimensions and fitted readout fingerprints in matched campaigns. Each adapter owns one persistent native handle. The compiled-runtime smoke tests exercised actual C++ handles, one-step checkpoint continuation, and trusted rollback; fake-runtime tests are not being substituted for those acceptance results.

Pinned runtime:
- Aberconics source commit: `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de`
- Compiled shared-library SHA-256: `38b278a93a5b3fa3b544f55d958a2f7a44bb6e1d39154e63072f5ed7be511e4b`

### 2.2 Matched hierarchical task campaign

Frozen independent partitions:
- Training: 120 world seeds, 200000–200119.
- Validation: 60 world seeds, 400000–400059.
- Confirmatory: 120 world seeds, 900000–900119.

The confirmatory campaign covered 240 world instances across two generated task modes and depths 2–4, with 480 G1 rows, 1,920 G2 rows and 1,920 G3 rows. HLA and HLB received paired task worlds and matched readout fingerprints.

| Test | HLA | HLB | Evidence-based interpretation |
|---|---:|---:|---|
| G1 exact target path, both modes, depths 2–4 | 100% | 100% | No observed separation |
| G2 outage without replay | 0% | 100% | HLB retains evidence that HLA's current query window lacks |
| G2 outage with replay | 100% | 100% | Replay removes the observed HLB advantage |
| G2 late target arrives before completion | 0% premature completion | 0% premature completion | Both wait/abstain correctly |
| G2 late target arrives after completion | 100% recovery | 100% recovery | Both recover when evidence becomes available |
| G3 missing-edge, wrong-context and temporally invalid negatives | 0 false selections | 0 false selections | Both enforce the tested witness constraints |
| G3 multiple-witness positive control | Exactly 2 preserved | Exactly 2 preserved | Both preserve multiplicity and exact witness identity |

All 12 hard-integrity checks passed. The confirmatory bootstrap used 10,000 resamples clustered by world seed; the paired G1 difference was zero with interval [0, 0], while the no-replay G2 difference was +1.0 for HLB over HLA with interval [1.0, 1.0].

Interpretation is deliberately limited to the tested task generators, depths, contexts, temporal rules, observation cutoffs, and outage/replay conditions. The generated worlds are controlled synthetic tests of typed path composition and evidence availability; they are not a demonstration of open-world semantic understanding or real deployment generalization.

### 2.3 P6 coupled adaptive stability and rollback

P6 v4 passed 37/37 frozen acceptance checks for each architecture over 20 seeds per architecture, 300 operating steps per seed, and 100-step stationary negative controls. Both architectures:
- remained within the frozen P6 state norm limit of 25 and native-level norm limit of 1,500;
- had transition spectral radius 0.6663325 and finite native state throughout;
- produced exactly two CUSUM alarms per seed and zero negative-control false alarms;
- completed DETECT → DORMANT → RECOVERY → NORMAL on all seeds;
- exercised all four context slots and abstained on a fifth novel context without eviction;
- promoted independently validated candidates 20/20 times and achieved exact operator rollback, composite rollback, and incumbent replay 20/20 times.

HLB additionally preserved its protected two-edge witness, abstained on a capacity-exceeding insertion, and removed the candidate-only record on rollback for all 20 seeds.

The P6/native trajectory metrics were identical for HLA and HLB. P6 therefore validates the coupled runtime/lifecycle envelope shared by both; it does not demonstrate a numerical stability advantage for either architecture. HLB's differentiating P6 evidence is its additional relation-store integrity path.

### 2.4 Resource evidence and its boundary

The v4 campaign reported an 854-byte M3-plus-SOE numeric subtotal. A separate audit explicitly added the omitted 16-byte P6 state vector and 32-byte fixed transition matrix, yielding **902 bytes** of declared persistent numeric state for each architecture. Parameter and operation-count ceilings also passed.

This is **not** a complete architecture memory comparison. The audit excludes Python object/container overhead and native-runtime process memory; it also does not establish the full storage cost of HLB's relation records and indexes at realistic occupancy. In particular, the 902-byte figure must not be presented as HLB's total memory footprint or as proof that HLA and HLB have equal total memory cost.

## 3. Architecture-level interpretation

### HLA — what it demonstrates

1. A three-level hierarchy can use learned upper-level readouts without retaining relation instances in an internal canonical store.
2. It preserves the semantic boundary between an abstract learned prediction and an exact relational witness.
3. Exact path claims remain grounded in caller-supplied evidence and the shared typed/time/context witness validator.
4. When evidence is replayed, HLA matches HLB on the tested exact path tasks.
5. It avoids the additional relation-store capacity and record-consistency responsibilities present in HLB.

HLA's demonstrated weakness is equally specific: when the query-time evidence window lacks an earlier observation and no replay is supplied, HLA cannot reconstruct the missing exact witness. This is a consequence of its design boundary, not an implementation defect hidden by the tests.

### HLB — what it demonstrates

1. A single canonical typed relation store with level-scoped indexes can retain evidence across a no-replay outage and recover the exact path.
2. It preserves original relation-instance identity through composition rather than replacing witnesses with inferred abstractions.
3. Capacity exhaustion can be explicit abstention rather than silent eviction.
4. Candidate-only relation mutation can be rolled back with the rest of the composite runtime while preserving protected evidence.

HLB's advantage is conditional on retention being valuable and the relevant evidence having been observed and stored before the outage. It does not establish discovery of unobserved facts, indefinite retention, arbitrary graph-scale retrieval, or superiority under high write rates and large stores. Its persistent store creates operational costs that have not yet been measured at realistic scale.

### Shared strengths and unresolved questions

Both architectures currently share the same native numerical substrate and learned upper-level readouts. The synthetic calibration/readout construction validates deterministic fitting and matched integration, but does not yet establish that those readouts learn useful abstractions from noisy, naturally occurring or distribution-shifted relational data.

The three-level arrangement, current readout form, and tested task generators are fixed design choices here. No level-count ablation, broad task-distribution sweep, open-world transfer test, or realistic store-load/latency benchmark is part of this H1 evidence.

## 4. Decision matrix

| Workload requirement | Evidence-supported choice | Reason |
|---|---|---|
| Exact query over evidence supplied at query time | HLA or HLB | Both matched on tested replay and exact composition |
| Must answer from retained evidence during no-replay outage | HLB | Only HLB achieved the tested 100% result |
| Avoid internal relation-instance persistence | HLA | No canonical relation store by design |
| Explicit capacity abstention and witness-preserving persistence | HLB | Directly implemented and exercised |
| Lowest total runtime memory/latency | Undetermined | Numeric subtotal is incomplete for total architecture cost |
| Better native/P6 numerical stability | Neither | Matched trajectories were identical |
| General semantic or open-world reasoning | Undetermined | Not tested by these synthetic controlled tasks |

## 5. Research-policy findings and claim restrictions

The following distinctions are mandatory in subsequent papers and reports:

- **Observed result:** HLB outperformed HLA in the frozen no-replay outage condition.
- **Mechanistic explanation supported by implementation:** HLB queried retained canonical records while HLA required current query evidence.
- **Not established:** HLB is generally more intelligent, more accurate, or universally more robust.
- **Observed result:** both passed the specified P6 finite-horizon coupled acceptance campaign.
- **Not established:** global stability, ISS, arbitrary-switching stability, or stability for other kernels, gains, dimensions, timesteps, capacities or input distributions.
- **Observed result:** declared numeric P6+M3 state was 902 bytes under the audit's accounting scope.
- **Not established:** whole-process memory, total HLB record-store memory, production latency, energy efficiency, or a complete cost advantage.
- **Not established:** a Grassmannian-specific advantage, geometric optimality, arbitrary-depth composition, open-world topology discovery, or out-of-vocabulary transfer.

Failed P6 v1/v2 configurations remain part of the research record and must not be erased or relabelled as successful confirmatory trials. Reproducibility reruns over the same frozen seeds remain reproducibility checks, not new independent samples.

## 6. Recommended next research phase

The next phase should not be another broad stability campaign. P6 execution is closed for the declared envelope. The highest-value unresolved question is whether HLB's persistence advantage remains worthwhile after its storage and retrieval costs are measured, and where HLA becomes preferable.

Recommended sequence:

1. **Freeze an architecture cost protocol before execution.** Measure HLB record bytes at the serialized and in-memory levels, index overhead, insertion/update/query latency, checkpoint size and restore time across controlled store occupancies. Measure HLA under the same runtime and task loads. Keep numeric controller state, Python overhead, native process memory and relation-store memory as separate accounting layers.
2. **Run a retention/outage workload sweep.** Vary outage duration, replay availability, record age/expiry, context fragmentation, write rate, duplicate/conflicting observations and store occupancy. Pre-register the regimes in which HLB should win and the regimes in which HLA should tie or be cheaper.
3. **Test retrieval robustness beyond the current small worlds.** Increase graph size, path branching, witness multiplicity, temporal disorder and distractor density; preserve independent world-level splits and exact witness validation.
4. **Test abstraction learning separately.** Replace or supplement the synthetic linear calibration target with noisy, held-out relational tasks. Evaluate calibration, abstention, distribution shift and whether readouts add value over the shared SOE/native baseline.
5. **Only then decide whether to specialize or combine.** A hybrid policy (HLA-style abstract readout plus HLB persistence only for selected relation classes) is a hypothesis for a later experiment, not a conclusion from current evidence.

### Decision gate for selecting a primary architecture

Do not select a primary architecture until the cost/outage sweep reports, on held-out workloads:
- exact-witness success and false-witness rate;
- outage performance with and without replay;
- abstention and capacity behavior;
- retrieval/insertion latency distributions;
- serialized and resident memory split by component;
- checkpoint/restore and rollback cost;
- robustness under context shift and temporal noise.

The choice should be workload-conditional if the trade-off persists. HLA remains the no-store baseline; HLB remains the persistence-capable candidate.

## 7. Source-of-truth evidence

- H1 execution ledger: `docs/experiments/HLG_H1_FIVE_WORKSTREAMS_LEDGER.md`
- H0 shared hierarchy contract: `docs/experiments/HLG_H0_SHARED_HIERARCHY_CONTRACT.md`
- H1 partition manifest: `docs/experiments/HLG_H1_HIERARCHICAL_PARTITIONS_v1.json`
- P6 v4 frozen protocol: `docs/experiments/HLG_H1_P6_FULL_RUNTIME_v4.json`
- P6 v4 result summary: `docs/experiments/HLG_H1_P6_FULL_RUNTIME_v4_RESULT_SUMMARY.json`
- P6 resource audit implementation: `scripts/audit_h1_p6_resource_footprint.py`; execution evidence: workflow [45726337240](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45726337240), artifact `15074058248`
- Compiled-runtime campaign and smoke workflows are linked in the H1 execution ledger.

**Final H1 architecture disposition:** both HLA and HLB pass the current implementation and execution gates. HLB has a demonstrated persistence advantage in the no-replay condition; HLA provides the no-store alternative. Keep both. The next selection decision is empirical and workload-dependent, not a theoretical winner declaration.
