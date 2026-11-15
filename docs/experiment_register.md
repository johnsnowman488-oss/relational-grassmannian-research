# Experiment register

This register tracks experimental questions, entry gates and evidence. The full adaptive-relational research programme is recorded in [the relational adaptation ledger](relational_adaptation_ledger.md).

| ID | Question | Status | Entry criterion | Exit evidence |
|---|---|---|---|---|
| E00 | Are mathematical/computational primitives correct and reproducible? | Accepted | v0.1 scope frozen | Unit tests, invariants, deterministic state round trips, Python 3.10/3.12 CI |
| E01-A | Can fixed SOE memory support two-hop inference versus controls? | Complete | E00 accepted; overlap reviewed | Nine controls, held-out sequences, archived evidence |
| E01-A2 | Which memory channels/readouts support retrieval and composition? | Complete | E01-A reviewed | 27-cell diagnostic audit; constituent probes and ablations |
| E01-A3 | Does the A2 pattern replicate across worlds/codebooks? | Complete | A2 configuration selected | 54-cell paired replication across 3 worlds × 3 codebooks |
| E01-B | Where does the memory capacity/interference frontier degrade? | Complete | A3 reviewed | 228-cell one-factor frontier; corrected cross-worker determinism gate |
| E01-C | Why does relational composition fail under selected stresses? | Complete | B frontier reviewed | 108-cell mechanism campaign; repeat suppression, path diagnostics and oracle gate |
| E02-A | Can we freeze a leakage-safe graph/event interface and reproducible corpus? | Complete; reconciled interface merged; CI passed | E01 complete | Reconcile the two open PR implementations, protocol and workflow; merge only after review |
| E02-B | Does explicit event-derived graph storage outperform dense memory on the six E01-C conditions? | Complete; 54/54 cells passed; summary artifact archived | E02-A contract passes | Preserve all paired cell evidence, costs and interpretation limits in main |
| E02-C | Does graph-plus-temporal memory add value under controlled corruption? | Complete; 54/54 cells passed; summary artifact archived | E02-A contract passes | Preserve profile-specific outcomes and distinguish corrupted-learning from recovery-after-gap |
| E03 | Does a representation-neutral task suite expose relational capability across explicit, higher-order and continuous domains? | Next: specification | E01 reviewed; E02 integration/review documented | Frozen task semantics, splits, baselines, leakage controls, metrics and acceptance gates |
| E04 | Can relational organisation be discovered without a complete supplied schema? | Planned | E03 benchmark frozen | Discovery precision/recall, false structures, stability and held-out relation patterns |
| E05 | Can learned relations be composed and generalised to unfamiliar configurations? | Planned | E04 reviewed | Held-out composition, higher-order generalisation and witness quality |
| E06 | Can relational organisation be revised under change and contradiction? | Planned | E04/E05 baselines established | Revision accuracy, stale relations, collateral loss and adaptation cost |
| E07 | Does relational organisation persist and recover through missing/noisy observations and temporal gaps? | Planned | E06 protocol available | Separate corrupted-learning and clean-memory-then-outage protocols |
| E08 | Does relational capability transfer across domains and unseen relation configurations? | Planned | E04/E05 capability established | Zero-/few-shot transfer and adaptation cost |
| E09 | Does a separate relational state add value beyond SOE-only or a unified state? | Planned | E05–E08 reviewed | Matched comparison of SOE-only, coupled-state and unified-state hypotheses |
| E10 | Does geometric, including Grassmannian, representation add measurable value? | Planned | E03–E09 controls and candidate mechanisms established | Matched-compute/supervision comparisons, ablations, sensitivity and transfer |
| E11 | Can relational organisation adapt hierarchically across D2C temporal scales? | Planned | Earlier relational capabilities demonstrated | Long-horizon, cross-scale and top-down adaptation evidence |

## E00 run ledger

E00 run_0002 passed the Python 3.10/3.12 CI matrix with 40 tests. This validates implementation and invariants only, not predictive performance or novelty.

## E01 run ledger

| Stage | Workflow run | Evidence |
|---|---:|---|
| E01-A | 43054698098 | Nine memory/control variants and unit-test matrix passed |
| E01-A2 | 43058306505 | 27 diagnostic cells and paired summary passed |
| E01-A3 | 43061507431 | 54 replication cells and paired summary passed |
| E01-B corrected | 43433259761 | 228 cells, Python 3.10/3.12 tests, two independent replicas, zero-difference determinism comparison, and summary passed |
| E01-C stable-threshold | 43433509287 | 108 cells, Python 3.10/3.12 tests, oracle gate, and paired summary passed |

Primary reports:
- [E01-A](../results/e01/run_0001/report.md)
- [E01-A2](../results/e01_a2/run_0001/report.md)
- [E01-A3](../results/e01_a3/run_0001/report.md)
- [E01-B corrected](../results/e01_b/run_0001/report.md)
- [E01-C stable-threshold](../results/e01_c/run_0001/report.md)

## E01 interpretation boundary

The A-series supports a task-specific slow-timescale contribution but does not show that the four-channel SOE bank beats slow-only SOE. B shows no aggregate composition advantage from the larger SOE bank. C identifies duplicate-event accumulation and false-path competition as important failure mechanisms, while long-gap evidence illustrates the trade-off between decaying traces and persistent facts.

None of E01-A through E01-C tests Grassmannian geometry. E01 is evidence about a constrained memory/readout task, not a result for the project's central geometric hypothesis.

## E02 integration and interpretation notes

PR #12 and PR #13 were reconciled through PR #15. The shared ObservedEventGraph primitive is now the sole E02 graph-construction path; E02 derives typed-edge traversal and storage accounting from it. The protocol, workflow and tests were aligned, and the existing main research ledger/README/decisions were preserved. PR #15 merged as `5ee58679e3f8b80c453344815ee91be94ddc181b`. Workflow run `43639855566` passed E02-A on Python 3.10/3.12, 54 E02-B cells, 54 E02-C cells and combined aggregation. Repository validation run `43639855578` passed. Combined summary artifact: `14132220095`.

The E02 campaign is reported as passing 54 E02-B cells and 54 E02-C cells on PR #12. Its results remain synthetic and tied to the E01-C generator. Graph traversal over explicitly observed edges is a retrieval reference, not evidence of open-ended relation discovery. Graph storage is not capacity-matched to a 16-scalar trace. E02-C corrupts the input stream before both graph and memory receive it; it does not test a system that first stores clean relational state and then experiences an observation outage.

## E03–E11 programme boundary

The next programme investigates relational task diversity, discovery, composition, revision, persistence/recovery, cross-domain transfer, temporal/relational cooperation, geometric representation and hierarchical relational adaptation. It is not a commitment to a graph-based or Grassmannian D2C architecture.

Three architectural hypotheses remain open:
1. SOE-only with learned relational readout/dynamics.
2. Coupled SOE temporal memory and a separate learned relational state.
3. A unified augmented dynamical-geometric state.

Geometry must be compared against learned non-geometric alternatives. E03 is the next task: freeze a representation-neutral benchmark and its controls before implementing a new relational learner. See the [relational adaptation ledger](relational_adaptation_ledger.md).


## Parallel LGDH mechanism stream

LGDH is a separately tracked mechanism investigation. It does not displace E03 as the next mainline E-series experiment and does not imply that the Grassmannian representation has been selected for the mechanism.

| ID | Question | Status | Entry criterion | Exit evidence |
|---|---|---|---|---|
| LG-01A | Can fast multidimensional modes remain active under bounded refresh while individual tagged contributions decay? | Implemented; v0.1 executed; valid scientific fail at rate 0.8 (26/30) | Protocol and runner frozen | 30-seed run bundle; exact decay, washout, boundedness, energy and SOE-null checks pass; refresh gate fails at fastest rate |
| LG-01B | Can intrinsic mode trajectories support recovery of directed relations without a supplied target graph? | Protocol draft under review; not frozen | Restricted to γ=0.05 and 0.20 (LG-01A 30/30 each); γ=0.80 remains failed/excluded; protocol approval before runner | Held-out directed-edge recovery and valid path witnesses above source-state, direction-blind, shuffled, reverse-time and random controls |
| LG-01C | Does slower trajectory registration improve contextual route selection? | Planned | LG-01B reproducible | Paired improvement over fast-only and slow-only controls |
| LG-01D | Can the relational organisation revise under structural change while preserving stable relations? | Planned | LG-01B and LG-01C pass separately | Adaptation, retention, stability and interference evidence |
| LG-02A | Does computational mode birth/death help represent novel recurring trajectories? | Provisional | Fixed-population routing validated | Controlled utility of mode growth under frozen connection weights |
| LG-02B | Does directed connection plasticity improve routing? | Provisional | Fixed-population routing validated | Useful edge changes with mode population fixed |
| LG-02C | Do mode growth and connection plasticity interact beneficially? | Provisional | LG-02A and LG-02B independently supported | Joint effect and complexity-control evidence |

**LG-01A interpretation ceiling:** a pass validates only transient activity under refresh. The conventional leaky SOE null is expected to reproduce the same equations. This experiment cannot establish graph formation, endogenous destination selection, reasoning or a distinct lepto-graph primitive.

Full specifications and ledgers are in the [LGDH experiment spine](lg_experiment_spine.md).


## Hybrid Relational Leptograph analytical milestone

| ID | Question | Status | Entry criterion | Exit evidence |
|---|---|---|---|---|
| HLG-M0 | Do the hybrid group's spaces, directed heterogeneous routing, memory, dormancy and reactivation equations have correct analytical reference implementations? | Implemented; all five analytical cases, aggregate evidence gate and full Python 3.10/3.12 test matrices passed (137 tests each) | Foundation v0.1 recorded; equations and claim boundaries explicit | Five independent exact-vs-DOP853 references, full Python 3.10/3.12 repository tests, and aggregate evidence manifest |

HLG-M0 cases are independently executable and suitable for concurrent CI jobs: M0-A memory; M0-B heterogeneous forward routing; M0-C independent reverse routing; M0-D dormancy; M0-E reactivation. M0 is mathematical/implementation verification only. It does not test whether relations can be discovered, whether identity can be recognised, whether topology can emerge, or whether the fully coupled adaptive system is stable. See [the mathematical foundations](hybrid_leptograph_foundations.md).

 
### HLG-M0 canonical run

The canonical GitHub Actions run is [43736121964](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43736121964) at commit 199f57f22d534d481b33925aa3785647d761eef9. Five analytical cases passed concurrently, the aggregate evidence verifier passed, and the complete test suite passed with 137 tests on each of Python 3.10 and 3.12. The summary artifact is 14169848246. See the relational adaptation ledger for error maxima, artifact digests and the invalid first harness-attempt note.


## Hybrid Relational Leptograph M1 — Heterogeneous Dimensional Routing and Geometric Invariance

| ID | Question | Status | Entry criterion | Exit evidence |
|---|---|---|---|---|
| HLG-M1 | Do heterogeneous directed maps, route compositions, interface factorizations and Grassmannian signatures transform correctly under coordinate changes? | Passed; six concurrent analytical cases, aggregate evidence gate and full Python 3.10/3.12 test suites (183 tests each) | HLG-M0 passed; M1-v0.1 protocol frozen | Six passing invariance cases, aggregate evidence manifest, full repository tests on Python 3.10/3.12 |

M1-A through M1-F test (A) orthonormal source/target basis covariance; (B) general invertible coordinate covariance with metric transport; (C) a heterogeneous 2→4→3→5 route chain; (D) interface GL-gauge invariance and factorisation rank bounds; (E) rank-nullity and information-dimension diagnostics; and (F) Grassmannian principal-angle, distance and projector invariance. Each case is an independent concurrent job followed by aggregate evidence validation. This is a fixed-operator algebraic verification milestone, not evidence of learned relational discovery or adaptive-network stability. See [the frozen M1 protocol](hybrid_leptograph_m1_protocol.md).


### HLG-M1 canonical execution

Canonical GitHub Actions run [43737461175](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43737461175) completed successfully at source commit 63897b81ff043aa36418447e4372caf7b375a46f. Six independent analytical jobs, the aggregate evidence verifier, and both complete repository test matrices passed. The full suite reported 183 tests passed on Python 3.10 and 183 on Python 3.12. Numerical maxima, all artifact IDs and ZIP SHA-256 digests are in the relational adaptation ledger.


## Parallel HLG mathematical implementation milestones

| ID | Question | Status | Entry criterion | Exit evidence |
|---|---|---|---|---|
| HLG-M0 | Do memory traces and heterogeneous fixed routes match analytical references? | Accepted: 5 cases; 137 tests × Python 3.10/3.12 | Frozen equations and reference cases | Independent analytical references, DOP853 cross-checks, complete CI |
| HLG-M1 | Are heterogeneous routes and geometric quantities covariant/invariant under coordinate changes? | Accepted: 6 cases; 183 tests × Python 3.10/3.12 | M0 accepted | Coordinate/metric covariance, route composition, interface gauge, Grassmannian checks |
| HLG-M2 | How do multiple fixed routes interact, preserve information, compound conditioning and affect feedback stability? | Accepted: 6 cases; 198 tests × Python 3.10/3.12 | M1 accepted | Six route/network reference cases, erasure diagnostics, spectral/transient separation, Python 3.10/3.12 full-suite CI |

HLG-M0/M1/M2 are a separate mathematical verification stream. Their passing CI does not establish relational discovery, semantic information, learned operators or adaptive-network capability; E03 remains the next mainline E-series specification.


### HLG-M2 execution record

Canonical branch-push run [43741891066](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43741891066) passed all six independent M2 cases, the evidence aggregation gate, and the complete repository suite on Python 3.10 and 3.12 (198 tests on each). The PR-triggered M2 run 43741942671 also passed all nine jobs. See the relational adaptation ledger for per-case metrics and artifact digests.
