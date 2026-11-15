# Independent Relational Grassmannian Research

An independent, evidence-led research project investigating whether relational organisation conditioned by accumulated temporal memory can be represented usefully through fixed-rank Grassmannian states.

## Research configuration v0.1

- **Interpretation:** coupled relational-memory geometry.
- **Memory:** fixed sum-of-exponentials (SOE) channels; four channels initially.
- **Initial feature space:** \(\mathbb{R}^{16}\).
- **Initial Grassmannian:** \(\operatorname{Gr}(4,\mathbb{R}^{16})\).
- **Scale:** small, deterministic synthetic experiments before larger models.

## Milestones

| Milestone | Purpose | Status |
|---|---|---|
| E00 | Mathematical and computational foundations | Accepted: 40 tests and Python 3.10/3.12 CI passed |
| E01-A | Memory-only two-hop inference and controls | Complete; results archived |
| E01-A2 | Channel, constituent-retrieval and readout diagnostics | Complete; 27 cells passed |
| E01-A3 | Independent-world/codebook replication | Complete; 54 cells passed |
| E01-B | Capacity and interference frontier | Complete; 228 cells and determinism gate passed |
| E01-C | Mechanism isolation and path-level diagnostics | Complete; 108 cells and oracle gate passed |
| E02 | Event-derived graph, dense-memory and hybrid evaluation | CI campaigns reported complete on open PR #12; integration reconciliation pending |
| E03 | Representation-neutral relational task suite | Next: specification |
| E04–E08 | Relational discovery, composition, revision, recovery and transfer | Planned |
| E09 | Temporal-memory and relational-organisation cooperation | Planned |
| E10 | Geometric representation comparisons, including Grassmannian candidates | Planned |
| E11 | Hierarchical relational adaptation | Planned |

## Current evidence boundary

E01 establishes a narrow synthetic result about temporal event memory and fixed candidate-path readout. It does **not** establish relation discovery, general relational reasoning, or a Grassmannian performance advantage. The strongest current finding is that dense event superposition and max-product path composition are vulnerable to support loss, duplicate accumulation, and false-path competition.

E02 compares an explicit event-derived graph with dense memory and a graph-plus-temporal-memory hybrid. Its results remain tied to the E01-C synthetic generator. An observed-edge graph is a retrieval reference, not evidence of open-ended relation discovery. E02 branches are awaiting integration reconciliation; see the [experiment register](docs/experiment_register.md).

D2C experiments motivated a broader research question: can an adaptive system discover, preserve, compose, revise and reorganise relational structure from experience? The architecture remains open. SOE-only learned relational readout, coupled temporal/relational states and a unified augmented state are competing hypotheses. Geometry is a candidate inductive bias, not a premise; learned non-geometric alternatives must be compared.

The project remains an independent research track rather than a D2C implementation branch. The full programme and decision boundaries are recorded in the [relational adaptation ledger](docs/relational_adaptation_ledger.md). E03 is next: freeze a representation-neutral benchmark before implementing a new relational learner.

## Development

Python 3.10+; NumPy, SciPy, pytest.

~~~bash
python -m pip install -e ".[dev]"
python -m pytest
python -m rgm.experiments.e01 --variant soe
~~~

See [DECISIONS.md](DECISIONS.md), [the mathematical specification](docs/mathematical_specification.md), [the experiment register](docs/experiment_register.md), and the E01/E02 protocol documents.


## Parallel mechanism investigation: Lepto-Graph Development Hypothesis

A separate LGDH line now investigates whether fast, multidimensional, continuously refreshed SOE-like modes can develop endogenous directed relational pathways from their own trajectories, with slower modes registering relevant history. This is a **parallel mechanism hypothesis**, not an established capability and not a replacement for E03. E03 remains the next mainline milestone. LG-01A-v0.1 has been implemented and executed over 30 paired seeds. Its mathematical and reproducibility tests passed on Python 3.10 and 3.12 (122 tests each); the scientific gate failed at the fastest declared rate (0.8: 26/30 seeds). LG-01B is in protocol review, restricted to the two passing LG-01A rates (0.05 and 0.20); 0.80 remains failed and excluded. No runner is authorised yet.

- [LGDH hypothesis](docs/lgdh_hypothesis.md)
- [LG experiment spine](docs/lg_experiment_spine.md)
- [LG-01A protocol](docs/lg01a_protocol.md)
- [LG-01B protocol draft](docs/lg01b_protocol.md)
- [LGDH cross-experiment ledger](docs/lgdh_ledger.md)
- [LG-01A experiment ledger](docs/lg01a_ledger.md)


## Hybrid Relational Leptograph — mathematical foundation

A parallel LGDH extension formalises a hybrid dimensional architecture: modes share a vector space within each group, groups may have heterogeneous dimensions, and directed relations route information through dimension-compatible operators and optional relation-specific interfaces. Mode memory and relational history are separate dynamical states. Identity recognition, topology birth/death, group reorganisation and full coupled stability remain open.

- [Hybrid Relational Leptograph mathematical foundations](docs/hybrid_leptograph_foundations.md)
- [M0 analytical reference implementation](src/rgm/leptograph/m0.py)

M0 verifies five closed-form reference cases: memory, heterogeneous routing, independent reverse routing, dormancy and reactivation. It is not a scientific-performance or relation-discovery result. Five analytical cases run as independent concurrent jobs, with a Python 3.10/3.12 full-test matrix and final evidence aggregation.

Canonical GitHub Actions run [43736121964](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43736121964) passed all five analytical jobs, the aggregation gate, and 137 full-repository tests on each of Python 3.10 and 3.12.


## HLG-M1 — Heterogeneous Dimensional Routing and Geometric Invariance

M1 verifies how directed routing maps between spaces of different dimensions transform under orthonormal and general invertible coordinate changes. It separately checks metric transport and metric-aware singular values, route-chain composition, interface GL-gauge freedom, rank/nullity diagnostics and Grassmannian invariance.

- [Frozen HLG-M1 protocol and propositions](docs/hybrid_leptograph_m1_protocol.md)
- [M1 implementation](src/rgm/leptograph/m1.py)
- [M1 independent experiment runner](src/rgm/experiments/leptograph_m1.py)

Six independent deterministic cases run concurrently, followed by aggregate evidence verification and a Python 3.10/3.12 full-repository test matrix. Canonical run [43737461175](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43737461175) passed all six cases and both 183-test suites. M1 is algebraic/geometric verification of fixed operators, not evidence of learned relation discovery, semantic alignment or full adaptive-system stability.


## HLG-M2 — Multi-Route Stability, Conditioning and Information Preservation

M2 extends the fixed heterogeneous routing foundation to parallel paths and feedback networks. It distinguishes summing route contributions (where they can cancel) from keeping route outputs separately observable, measures information loss and route-erasure resilience, and tests spectral stability separately from non-normal transient amplification.

- [Frozen HLG-M2 protocol](docs/hybrid_leptograph_m2_protocol.md)
- [M2 implementation](src/rgm/leptograph/m2.py)
- [M2 independent experiment runner](src/rgm/experiments/leptograph_m2.py)

M2 is fixed-matrix algebra and LTI network verification only. It does not validate adaptive, delayed, nonlinear or learned-network stability, nor information-theoretic capacity or semantic retention.

Canonical HLG-M2 run [43741891066](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43741891066) passed all six reference cases, the aggregate evidence gate, and 198 full-repository tests on each of Python 3.10 and 3.12.


## HLG-M3 — Relational Memory and Adaptation: pre-implementation campaign

M3 begins the adaptive-learning investigation while retaining the existing vector-space architecture and the provisional history/routing equations from M0. Before implementation, seven independent jobs test historical accumulation, decay, contextual retrieval ambiguity, adaptive-operator boundedness, memory-comparison readiness, sequential reacquisition and switched-system stability limits.

- [M3 pre-implementation mathematical protocol](docs/hybrid_leptograph_m3_preimplementation_protocol.md)
- [M3 parallel execution plan](docs/hybrid_leptograph_m3_concurrency_plan.md)
- [M3 preflight reference runner](src/rgm/experiments/leptograph_m3_preflight.py)

The preflight is not an M3 production implementation. In particular, the memory-architecture comparison is expected to remain blocked until a capacity-matched unified-memory control is mathematically specified. A green CI run means the preflight executed, not that M3 implementation is authorised.


## HLG-M3 — proposed relational memory and adaptation foundation

The HLG-M3 foundation is adopted as a proposed design for review, extending the heterogeneous vector-space substrate without replacing M0-M2. It separates stored relationship operators from route activation; introduces shared context banks, metric-aware context matching with abstention, joint online operator estimation, prequential relational evidence, conditional identifiability, and a candidate-based revision mechanism. These are proposed mechanisms, not an implementation protocol or established learning result.

- [Proposed HLG-M3 mathematical foundation](docs/hybrid_leptograph_m3_foundation_proposal.md)
- [Seven-job mathematical design campaign plan](docs/hybrid_leptograph_m3_foundation_campaign_plan.md)
- [Pre-implementation reference campaign runner](src/rgm/experiments/leptograph_m3_foundation_campaign.py)

Seven concurrent mathematical design jobs (F1-F7) challenge evidence attribution, metric-aware operator estimation, context memory, evidence/activation/revision, memory controls, integrated task design, and independent mathematical limits. The implementation protocol remains explicitly unfrozen until their results are reviewed.


### HLG-M3 foundation campaign results

The canonical seven-job design campaign completed successfully (run 43756548407); all seven jobs, aggregate evidence verification, and 228-test full suites on Python 3.10/3.12 passed. The implementation protocol remains unfrozen pending research review.

- [F1-F7 canonical results and interpretation boundaries](docs/hybrid_leptograph_m3_foundation_campaign_results.md)
