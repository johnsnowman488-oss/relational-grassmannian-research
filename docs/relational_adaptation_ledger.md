# Relational adaptation research ledger

**Ledger date:** 2026-11-14  
**Status:** Research direction agreed; E03 specification is the next design task.  
**Relationship to Aberconics/D2C:** This programme is motivated in part by capabilities exposed as missing during D2C experiments. The present repository remains an independent experimental track; this ledger does not assert that any proposed representation has already been integrated into D2C.

## 1. Research motivation

The E01/E02 investigations exposed an important distinction for adaptive systems, especially systems intended for advanced reasoning:

- Retaining observations over time is not the same as preserving the relational organisation that gives those observations meaning.
- Retaining individual relation-like signals does not guarantee that the system preserves relation identity, dependencies, or the conditions under which relations can be composed.
- An explicit graph can solve tasks whose relations are directly supplied as typed edges, but that does not establish open-ended relation discovery or general relational reasoning.
- A system intended to adapt across diverse tasks should be able to learn relational organisation rather than depend entirely on manually prescribed, task-specific relational operators.

The central capability under investigation is:

> Can an adaptive system discover, preserve, compose, revise and reorganise relational structure from experience, and transfer that capability to unfamiliar tasks?

This is a research question, not an established capability of the current SOE or geometric implementation.

## 2. Conceptual decomposition

Keep three functions distinct when designing experiments:

1. **Temporal memory** — what has happened, what persists, and how past context influences current processing.
2. **Relational organisation** — how entities, events, attributes, configurations and constraints are related or depend on one another.
3. **Relational dynamics** — how that organisation is discovered, composed, revised, reorganised and learned over time.

D2C's hierarchy introduces another axis: multiple temporal scales and top-down predictive context. Hierarchical levels must not be confused with different representational types.

A geometric substrate is a candidate inductive bias and representation, not a complete relational learning mechanism. It must still be shown how observations map into it, how relational organisation is learned, and how composition and revision occur.

## 3. Architectural hypotheses — deliberately unresolved

Do not assume that D2C necessarily requires two independent persistent states. Compare:

- **A — SOE-only:** temporal memory with learned readouts/dynamics that discover and express relational organisation.
- **B — coupled states:** SOE temporal memory plus a separate learned relational state, potentially geometric.
- **C — unified state:** an augmented dynamical-geometric state jointly maintains temporal and relational information.

A graph may be learned or manually specified; geometry may still encode task-specific assumptions. The fair comparison is therefore between different inductive biases and learning procedures, not simply “manual graph versus automatic geometry.”

The explicit graph remains a useful reference/control representation. It is not selected as the permanent D2C architecture.

## 4. Experimental programme

### E01–E02 — Initial relational-memory investigation

| Experiment | Question / contribution | Status |
|---|---|---|
| E01 | Can fixed SOE temporal memory support relational retrieval and composition under controlled synthetic conditions? | Complete; evidence archived on main |
| E02-A | Can an event-only interface and observed-event graph be specified with leakage-safe boundaries? | Complete; reconciled graph and campaign merged via PR #15 |
| E02-B | How does explicit event-derived graph retrieval compare with the E01 dense-memory baseline? | Complete; 54/54 cells passed; integrated via PR #15 |
| E02-C | Does graph-plus-temporal-memory help under clean, missing, spurious and mixed observations? | Complete; 54/54 cells passed; integrated via PR #15 |

**E01 interpretation boundary:** The experiments are synthetic and task-specific. They identify support loss, duplicate-event accumulation and false-path competition in the tested memory/readout. They do not establish general relational reasoning or a Grassmannian advantage.

**E02 interpretation boundary:** A graph result is evidence about retrieval/composition when observed facts are explicitly represented as edges. It is not evidence of relation discovery. Graph storage is not information-capacity matched to a fixed-size memory state. The E02-C corruption design, as currently described, corrupts the observations before graph and memory receive them; it does not establish recovery from a clean relational state retained before a later observation outage.

**Integration note (2026-11-14):** PR #12 and PR #13 were reconciled without merging either branch wholesale. PR #15 integrated the E02-B/C campaign with the shared `ObservedEventGraph` primitive, preserving duplicate counts, first/last event indices and every cumulative observed timestamp. PR #15 merged to main as `5ee58679e3f8b80c453344815ee91be94ddc181b`. The corrected PR workflow run `43639855566` passed E02-A tests on Python 3.10/3.12, all 54 E02-B cells, all 54 E02-C cells, and the combined summary job. The separate repository validation workflow run `43639855578` also passed. The combined E02 summary artifact is Actions artifact `14132220095`.

### E03 — Relational task diversity and representation challenge

**Purpose:** Establish a benchmark that does not quietly favour graphs, vectors or geometry.

Include at least:
- explicit relations: ownership, location, ordering, dependency and connection;
- higher-order relations: multi-entity configurations, shared constraints and interactions;
- continuous/changing relations: similarity, influence, proximity, transformations and evolving dependencies.

**Question:** Can one relational learning mechanism operate across fundamentally different task structures?

**Evidence:** A controlled task suite with known ground truth, complexity levels, train/test splits, and tests separating fact retrieval from relational reasoning.

### E04 — Relational structure discovery

**Purpose:** Test whether relational organisation can be learned from observations without supplying a complete relational schema.

Compare:
- manually specified relational structures;
- learned graph structures;
- learned non-geometric relational representations;
- learned geometric representations.

**Question:** Can the system discover useful relations, configurations and dependencies rather than merely operate on relations supplied by the experiment designer?

**Evidence:** Discovery precision/recall, false-positive and false-negative structure, stability across seeds, and performance on withheld relation patterns.

### E05 — Relational composition and generalisation

**Purpose:** Test reusable composition beyond simple transitivity or fixed path templates.

**Question:** Can the system apply learned relational operations to unfamiliar combinations, higher-order configurations and longer chains?

**Evidence:** Held-out composition accuracy, compositional generalisation, false composition rate, and relational witness quality.

### E06 — Relational revision and structural adaptation

**Purpose:** Test changes to previously learned relationships.

Include:
- relations that change over time;
- contradictory observations;
- temporary versus persistent changes;
- new relations that invalidate earlier assumptions;
- local changes that should not destroy unrelated knowledge.

**Question:** Can the system revise relational organisation without manual reconstruction?

**Evidence:** Revision accuracy, stale-relation persistence, collateral loss, confidence calibration and adaptation cost.

### E07 — Partial observation, temporal gaps and recovery

**Purpose:** Separate learning under corrupted input from recovery using previously retained clean memory.

Test at least two distinct protocols:
1. corruption is present while the system first learns the relations;
2. the system first learns cleanly, then experiences an observation gap or degraded observation period and must use retained state.

**Question:** Does relational organisation survive interruption, and can it be updated when evidence returns?

**Evidence:** Retention, recovery, robustness, confidence calibration and interference.

### E08 — Cross-domain relational transfer

**Purpose:** Test whether learned relational mechanisms transfer beyond familiar surface features and task vocabularies.

**Question:** Does the system transfer relational capabilities to a new domain, or merely memorise familiar structures?

**Evidence:** Zero-shot and few-shot transfer, adaptation sample/compute cost, and performance on unseen relation configurations.

### E09 — Temporal memory and relational organisation cooperation

**Purpose:** Determine whether a separate relational state adds value beyond temporal memory and learned readout.

Compare A (SOE-only), B (coupled SOE plus relational state), and C (unified augmented state). Include a relational-only reference where useful.

**Question:** Is a distinct persistent relational state necessary or beneficial?

**Evidence:** Composition, retention, revision, transfer, state size, update cost and query cost. Include ablations of memory, relational state and coupling.

### E10 — Geometric relational representation

**Purpose:** Test geometry as a candidate general representation and inductive bias.

Compare suitable vector/tensor, learned graph, non-geometric latent, subspace, Grassmannian and other justified geometric alternatives.

**Question:** Does geometry provide measurable benefits in invariance/equivariance, higher-order organisation, compositionality, smooth adaptation, compactness or transfer?

**Evidence:** Matched-compute and matched-supervision comparisons, ablations, sensitivity analysis, interpretability and transfer. Grassmannian geometry must earn its place experimentally; it is not presumed to be the answer.

### E11 — Hierarchical relational adaptation

**Purpose:** Only after earlier capabilities are demonstrated, test relational learning within D2C's multi-timescale hierarchy.

Include fast local relations, persistent contextual relations, higher-level structural patterns, and top-down predictions that influence lower-level relational learning.

**Question:** Can relational organisation itself become hierarchical and adaptive?

**Evidence:** Long-horizon reasoning, structural adaptation, predictive consistency, cross-scale coordination and task transfer.

## 5. Shared experimental controls

Across the programme, where applicable:

- Use the same observations, training examples, supervision, compute budgets and evaluation queries across compared models.
- Separate model-visible inputs from evaluator-only truth, planted structures, labels and corruption audits.
- Include both graph-like and non-graph-like task families.
- Hold out relation configurations and, where possible, relation types or domains.
- Test noise, ambiguity, missing evidence, contradiction, temporal gaps and structural change.
- Report fact retrieval separately from relation discovery, composition and reasoning.
- Report state size, update work, query work and wall-clock measurements separately; do not equate unlike operation counters.
- Include ablations for geometry, SOE, coupling and hierarchy.
- Require interpretable relational witnesses or explanations where the task permits them.
- Preserve negative results and version experimental protocols before inspecting held-out outcomes.

## 6. E03 entry gate and next action

E03 is the next design task, not yet an implementation commitment.

Before coding E03, freeze:
1. task families and ground-truth semantics;
2. complexity levels and held-out generalisation splits;
3. model-visible versus evaluator-only information;
4. baseline architectures and fair training/compute controls;
5. metrics, seeds, reproducibility artifacts and acceptance criteria.

E03 must not encode the answer in the representation being evaluated. The system should be allowed to discover problem structure rather than merely operate on structure pre-discovered by the benchmark designer.

## 7. Decision log

- **2026-11-14 — Adaptive relational capability added as a research objective:** D2C experiments motivated explicit investigation of relational discovery, preservation, composition, revision and reorganisation. This expands the questions asked by the independent relational research track; it does not establish a D2C architecture change.
- **2026-11-14 — Architecture kept open:** SOE-only, coupled temporal/relational states and a unified augmented state remain competing hypotheses.
- **2026-11-14 — Geometry kept as a candidate, not a premise:** Grassmannian and other geometric representations must be compared with learned non-geometric alternatives.
- **2026-11-14 — E03 designated next:** benchmark diversity and representation-neutral controls precede implementation of a new relational learner.


## 8. Parallel mechanism investigation — Lepto-Graph Development Hypothesis

**Status (2026-11-14):** LGDH hypothesis recorded; LG-01A-v0.1 protocol specified; implementation and runs pending.

A parallel mechanism question has been added: can fast, multidimensional, continuously refreshed memory modes develop directed relational pathways from their own trajectories, while slower modes register relevant trajectory history and supply context for later routing?

The distinction from E01/E02 is important:

- E01 studied fixed SOE temporal memory and candidate-path retrieval/composition.
- E02 studied an explicit graph derived from observed events and a graph-plus-temporal-memory hybrid.
- LGDH asks whether relational pathways can emerge endogenously from memory-mode trajectories. An observed-edge graph is a useful comparator, not a demonstration of this mechanism.

The working cycle is:

**Trajectory → historical registration → contextual recognition → routing adaptation → new trajectory**

Direction must emerge from the mode's own trajectory. A tangent identifies a direction in the source mode's state space, not a destination; a mapping to candidate recipient modes remains a central open question. Slower modes may register historical trajectories and provide context, but must not replace the current trajectory-derived signal. Lepto-modes are proposed primarily as routing/relational state, not as permanent stores for every information item.

LGDH is a **parallel research stream** and does not replace E03 as the next mainline E-series task. The Relational Grassmannian remains a separate candidate representation/analysis track; no geometric component is required in LG-01A.

### LG stream

| Experiment | Question | Status |
|---|---|---|
| LG-01A | Transient mode behaviour under ongoing bounded refresh | Protocol specified; not implemented or run |
| LG-01B | Trajectory-derived directional relation formation | Planned; waits for LG-01A gate |
| LG-01C | Slow-memory registration and contextual routing | Planned; waits for LG-01B |
| LG-01D | Adaptive relational reorganisation | Planned; waits for LG-01B and LG-01C |
| LG-02A | Computational neurogenesis / mode birth-death | Provisional follow-up |
| LG-02B | Computational synaptogenesis / connection plasticity | Provisional follow-up |
| LG-02C | Joint developmental system | Provisional; only after isolated LG-02A/B evidence |

LG-01A uses the repository's 16-dimensional state space and fixed four-rate SOE bank as a comparable dynamical scaffold. It separates a tagged pulse contribution from a continuing refresh contribution, includes an equal-energy intermittent-refresh control, and retains a conventional SOE null baseline. Its operational pass does not establish any graph or reasoning claim.

See [LGDH hypothesis](lgdh_hypothesis.md), [LG experiment spine](lg_experiment_spine.md), [LG-01A protocol](lg01a_protocol.md), [LGDH ledger](lgdh_ledger.md), and [LG-01A ledger](lg01a_ledger.md).

### LG-01A execution update (2026-11-14)

The parallel Lepto-Graph Development Hypothesis stream has moved from specification to its first controlled execution. The LG-01A-v0.1 runner and tests are implemented. GitHub Actions run 43652121470 passed 122 repository tests on both Python 3.10 and 3.12 and executed 30 paired seeds. It found 30/30 passes at fast rates 0.05 and 0.2, but only 26/30 at 0.8, below the pre-registered 27/30 requirement. All mathematical, boundedness, washout, energy-match and conventional-SOE-null controls passed. The run bundle is artifact 14136786352.

The result is a valid v0.1 scientific failure at the fastest declared rate, not an implementation failure. LG-01B is blocked until the scope of that result is reviewed. This does not change the main E-series ordering: E03 remains the next mainline milestone, and no Grassmannian or lepto-graph architecture has been selected.


## 9. Hybrid relational Leptograph — mathematical foundation (2026-11-15)

A hybrid dimensional architecture has been added as a parallel LGDH research extension. It preserves the Leptograph's n-dimensional information reception, internal processing and routing while making dimensional organisation explicit:

- Modes are partitioned into groups; modes in a group share an ambient real inner-product space \(\mathcal E_g\cong\mathbb R^{d_g}\).
- Different groups may have heterogeneous dimensions. The global state is a direct sum of local mode spaces, not an assertion that all modes share one representation.
- A directed relation from group \(g\) to group \(h\) is a linear map \(K_e:\mathcal E_g\to\mathcal E_h\). An optional relation-specific interface factors it as \(K_e=D_eS_e\), with an explicit non-identifiability/gauge freedom in that factorization.
- Reverse relations have independent operators; no inverse, transpose or symmetry is presumed.
- Mode-level temporal memory and relationship-level history are distinct states. Relationship identity, context and confidence are recorded as separate design roles, but their inference/update rules remain open.
- Provisional adaptation uses \(\dot H_e=\lambda_e(s_e-H_e)\) and \(\dot K_e=\eta_eH_es_e(\widehat K_e-K_e)-\delta_e(1-s_e)K_e\). Evidence construction must be non-circular and separately specified.

The mathematical foundation records proofs for historical-state invariance, operator norm-ball invariance under bounded targets, exact dormancy and reactivation, conditional incremental stability of the mode subsystem, and noiseless operator identifiability under full source excitation. It states the additional assumptions needed for local/global well-posedness and explicitly does **not** claim full coupled-system stability.

Grassmannian subspaces are retained as candidate relational signatures, not mandatory routing states or sufficient historical identities. Higher-order relations, endogenous topology and mode changes, identity recognition, false-reactivation control, and multi-source noisy identifiability remain open.

See [Hybrid Relational Leptograph mathematical foundations](hybrid_leptograph_foundations.md).

### M0 — analytical reference verification

M0 implements and executes five independent analytical cases:

| Case | Scope |
|---|---|
| M0-A | Exact mode-memory response and washout |
| M0-B | Heterogeneous directed routing \(\mathbb R^2\to\mathbb R^4\to\mathbb R^5\) |
| M0-C | Independent forward and reverse operators |
| M0-D | Dormant history and operator decay |
| M0-E | Reactivation after dormancy under renewed constant evidence |

M0 is an equation/code verification milestone, not evidence of relation discovery or scientific utility. Each case is independently executable; CI runs the five cases concurrently and aggregates their evidence. Initial local verification on Python 3.13.5 / NumPy 2.3.5 / SciPy 1.17.0 passed all five cases, with maximum absolute differences from independent DOP853 integration between \(4.60\times10^{-13}\) and \(5.15\times10^{-12}\), against a \(2\times10^{-10}\) tolerance. The dedicated M0 test file passed 15 tests. The canonical cross-version repository CI run 43736121964 also passed, with 137 full-suite tests on Python 3.10 and 137 on Python 3.12; the run and artifact checksums are recorded below.

This extension does not modify LG-01A or LG-01B frozen protocols, alter LG-01B's scientific failure, or unblock LG-01C. It also does not displace E03 in the main E-series.


### M0 CI execution record (2026-11-15)

**Canonical workflow run:** [43736121964](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43736121964)  
**Source commit:** 199f57f22d534d481b33925aa3785647d761eef9  
**Result:** success; all five analytical cases and the aggregate gate passed.

The full repository test suite passed on both supported CI versions:

| Python | Full-suite result |
|---|---:|
| 3.10 | 137 passed |
| 3.12 | 137 passed |

Each analytical case ran as a separate concurrent job. Maximum absolute differences between the closed-form reference and independent DOP853 integration were:

| Case | Maximum absolute error | Absolute tolerance | Result |
|---|---:|---:|---|
| M0-A | \(4.5963\times10^{-13}\) | \(2\times10^{-10}\) | Pass |
| M0-B | \(1.0968\times10^{-12}\) | \(2\times10^{-10}\) | Pass |
| M0-C | \(8.2023\times10^{-13}\) | \(2\times10^{-10}\) | Pass |
| M0-D | \(8.4077\times10^{-13}\) | \(2\times10^{-10}\) | Pass |
| M0-E | \(5.1501\times10^{-12}\) | \(2\times10^{-10}\) | Pass |

The aggregation job verified exactly the five expected case files and reported all_cases_passed=true. The canonical summary JSON SHA-256 is eec0b1b5b62023f9262ae094a3edea73468e8a3d907528e70b2998742d5fb968.

**Evidence artifacts:**

| Artifact | ID | ZIP SHA-256 |
|---|---:|---|
| M0-A | 14170317370 | 9b59b314e154d6f302981d6f0d6b52577a0dbcf8220f2c728ced6f9d4fa70caf |
| M0-B | 14169984404 | 9c893374412de6c02ac3a7f206df5f1df41ff744d6cdf025820c095b1bf9b40a |
| M0-C | 14170463179 | ff72dc23845706334a8c3c3a31e87df83c5046e6bf3da2cc2dbd8a0d02ff3808 |
| M0-D | 14170268772 | 693cf59da7491299756a93f917832437f004dab6be363215acaec597d1830aa1 |
| M0-E | 14170002887 | 9fb085f81c33eddff3fba4a6c9ec554b5b2aa25bd367056d67939bb5e32c70a8 |
| Aggregate summary | 14169848246 | e5269f02b8b7ba38e8356dc8c98a737c63cc143a3dc8938056a89ffeb9c67439 |

An earlier workflow attempt, 43736080691, is explicitly classified as an invalid CI harness attempt: escaped matrix expressions produced invalid Python-version and artifact-name values. The workflow was corrected in commit 199f57f22d534d481b33925aa3785647d761eef9, and only run 43736121964 is treated as canonical M0 CI evidence. The invalid attempt is not counted as an analytical result.

**Interpretation:** M0 passes its analytical/implementation verification gate. It validates these five fixed reference cases and the test environment. It does not establish relation discovery, identity recognition, causal inference, topology emergence, full coupled-system stability or scientific utility.


## HLG-M1 — frozen mathematical/implementation scope (2026-11-15)

M1 follows the completed M0 reference checks and isolates a new question: do heterogeneous directed operators, their compositions and geometric signatures behave consistently under changes of coordinates?

The frozen distinction is:
- **Orthonormal basis changes:** \(K'=Q_t^\top KQ_s\). These are isometries and preserve Euclidean norms, Frobenius norm, rank and ordinary singular values.
- **General invertible coordinate changes:** \(K'=A_t^{-1}KA_s\). These are not generally isometries. The inner-product matrices must also change by \(G'_s=A_s^\top G_sA_s\), \(G'_t=A_t^\top G_tA_t\); generalized metric singular values, computed after Cholesky whitening, are the invariant quantities.
- **Route composition:** internal coordinate changes cancel along a heterogeneous chain.
- **Interface gauge:** \(S'=RS,D'=DR^{-1}\) preserves \(DS\) for any invertible \(R\), but does not make the individual factors identifiable or imply that non-orthogonal gauges preserve the interface metric.
- **Grassmannian geometry:** principal angles and geodesic distance are invariant under a common orthogonal ambient coordinate change and independent orthogonal frame rotations. Both subspaces being compared must share one ambient metric space and rank.

The frozen six-case protocol is [hybrid_leptograph_m1_protocol.md](hybrid_leptograph_m1_protocol.md). Its cases use deterministic seeds 1101–1106 and float64 tolerances: M1-A/C/D/F \(2\\times10^{-10}\); M1-B \(2\\times10^{-9}\); M1-E uses exact rank/injectivity/surjectivity and factor-rank assertions. Each case writes its own result JSON; CI runs all six independently, then requires the complete evidence set. The full repository suite is checked on Python 3.10 and 3.12.

M1 does not estimate or learn route operators. It does not establish semantic alignment, causal correctness, relation identity, noisy multi-source identifiability or full adaptive-network stability. Those remain separate research questions.
