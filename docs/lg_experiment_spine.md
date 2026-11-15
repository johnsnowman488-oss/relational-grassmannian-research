# LG — Lepto-Graph Experiment Spine

**Research stream:** Lepto-Graph Development Hypothesis (LGDH)  
**Status:** LG-01A-v0.1 complete; restricted operating envelope adopted; LG-01B-v0.1 frozen; runner and 30-world campaign in progress  
**Programme relationship:** Parallel to the E-series; E03 remains the next mainline milestone

## 1. Research objective

Test whether rapidly decaying, continuously refreshed, multidimensional memory modes can develop useful directed relational pathways from their intrinsic trajectories, with slower memory channels registering and returning relevant history.

Separate the claims:

1. **Transient-mode viability:** ongoing input can keep a fast state operational even though contributions from individual earlier inputs decay.
2. **Directional relation formation:** intrinsic mode trajectories can generate directed relations without a supplied target graph.
3. **Contextual routing:** slower registered history improves destination selection beyond the current fast trajectory alone.
4. **Adaptive relational utility:** the resulting organisation revises under real structural change and improves held-out relational tasks.

A pass at one layer does not imply a pass at the next.

## 2. Experiment sequence

| ID | Question | Isolated mechanism | Entry gate | Required exit evidence |
|---|---|---|---|---|
| **LG-01A — Transient mode behaviour** | Can fast multidimensional modes remain active under bounded refresh while tagged historical contributions decay? | Fixed leaky modes; no mode-to-mode edges or learning | Protocol frozen | Analytic decay, input-response, refresh activity, boundedness and reproducible run evidence |
| **LG-01B — Trajectory-derived directional relations** | Can intrinsic mode trajectories support recovery of directed relations without a supplied target topology? | LG-01A rates γ=0.05 and 0.20 met 30/30; γ=0.80 excluded after its 26/30 failure; LG-01B protocol frozen before implementation | Held-out directed-edge recovery and valid path witnesses above source-state, direction-blind, shuffled, reverse-time and random controls |
| **LG-01C — Slow historical registration and routing** | Does slow registration of trajectory history improve routing under delayed, ambiguous or context-dependent sequences? | Slow SOE registration and context-conditioned destination selection | LG-01B route formation is reproducible | Paired route/retrieval improvement over fast-only and slow-only controls; ablation evidence |
| **LG-01D — Relational reorganisation** | Can pathways revise after genuine relation changes without unnecessary destruction of stable relations? | Online route adaptation with fixed mode population | LG-01B and LG-01C pass separately | Change detection, adaptation latency, retained stable relations, low spurious rewiring and held-out task benefit |

LG-01A is deliberately narrow. It does not test route formation or the graph claim. LG-01B begins with a fixed population so that mode birth/death cannot be used to rescue a failed routing mechanism.

## 3. Structural development follow-ups

These are separate hypotheses and are not part of LG-01A–D.

| ID | Working title | Research question | Isolation |
|---|---|---|---|
| **LG-02A — Computational neurogenesis** | When should a new transient mode be created because recurring novel trajectories cannot be represented adequately by current modes? | Test birth/death while connection weights remain frozen |
| **LG-02B — Computational synaptogenesis** | When should a directed connection be created, strengthened, weakened or removed because it has demonstrated useful predictive/routing value? | Test edge plasticity with a fixed mode population |
| **LG-02C — Coupled development** | Do mode birth/death and connection plasticity interact beneficially? | Only after LG-02A and LG-02B have independent evidence |

Mode birth must use pre-registered novelty, capacity and utility criteria, with explicit complexity penalties and pruning. Connection plasticity must rely on directional or predictive value, not co-activation alone. LG-02C must not be used to obscure which isolated mechanism did or did not work.

## 4. Mathematical scaffold

For mode \(i\), state \(z_i(t)\in\mathbb R^d\) has an endogenous trajectory. A finite-difference or continuous tangent may provide its directional signal:

\[
d_i(t)=\frac{\dot z_i(t)}{\|\dot z_i(t)\|+\varepsilon}.
\]

A slower memory may register a feature map of state and direction:

\[
M_i(t)=\int_0^t K_i(t-s)\Phi(z_i(s),d_i(s))\,ds.
\]

A future route proposal is

\[
r_i(t)=F(z_i(t),d_i(t),M_i(t),\mathcal C_i(t)).
\]

The destination map, the features in \(\Phi\), uncertainty representation, and learning rule remain open until their own experiment specifications are frozen. A tangent in the source mode's state space is not automatically a destination label.

## 5. Common controls and comparison discipline

For any experiment that compares architectures, match where possible:

- scalar state dimension and total mode count;
- SOE decay rates / timescale budget and initialization;
- input sequences, query sequences, training opportunities and held-out examples;
- random seeds and seed-to-arm pairing;
- parameter count, update count and compute budget;
- observation access and evaluator-only information.

Record mismatches instead of implying capacity equivalence.

Required baseline families as relevant to the stage:

1. **Conventional SOE:** same state equations and decay bank without lepto-specific trajectory-to-destination logic. This is the critical null for LG-01A.
2. **No-refresh / pulse-only:** isolates natural decay without ongoing information.
3. **Matched-energy intermittent refresh:** tests temporal delivery pattern against a continuous stream with the same input energy.
4. **Fast-only and slow-only:** separate current transient dynamics from historical registration in LG-01C.
5. **Frozen / non-directional routing and random routing:** test whether directional information matters in LG-01B/D.
6. **Explicit observed-event graph:** later reference using the E02 ObservedEventGraph protocol/implementation. It is an observed-edge retrieval comparator, not an endogenous learner. Any departure from the E02 implementation must be named as a different baseline.

Do not add Grassmannian geometry as a required component before a specific geometric quantity has an independently stated role and measurable value.

## 6. Shared evidence and reporting

Report at the independent-run / seed level, not by treating timesteps from one trajectory as independent observations. Preserve raw per-seed metrics and artefacts.

Across the stages, track as applicable:

- decay and refresh activity profiles;
- state boundedness, numerical error and input-response fidelity;
- route accuracy, false routes, unresolved-route rate and path-witness correctness;
- retrieval accuracy and delay sensitivity;
- route stability, unnecessary rewiring and adaptation latency;
- interference resistance, context specificity and retained stable relations;
- state size, parameter count, update work, query work and wall-clock cost.

Every result must state what it does not establish.

## 7. LG-01A gate summary

The frozen LG-01A-v0.1 campaign ran 30 paired seeds. The 0.05 and 0.2 fast rates passed 30/30; the 0.8 rate passed only 26/30, below the pre-registered 27/30 threshold. The result is a **valid scientific fail for the declared fast-rate range**. Mathematical, boundedness, input-response, washout, energy-matching and conventional-SOE-null checks passed. See the LG-01A experiment ledger for run IDs, per-seed failures and artifact hashes.

**Downstream scope decision (2026-11-14):** LG-01B is authorised for specification only at the two LG-01A-v0.1 fast rates that met the frozen per-seed gate: γ=0.05 and γ=0.20 (30/30 each). γ=0.80 remains a valid failure (26/30) and is excluded. This does not change the LG-01A-v0.1 result or its acceptance threshold.

LG-01B-v0.1 is frozen and its runner/campaign are authorised. The frozen experiment tests hidden-topology recovery from coupled trajectories only; it does not test spontaneous graph emergence. The k=2 prior and conservative c=0.05 coupling remain fixed, with no post-hoc tuning. The conventional leaky SOE channel matched the LG-01A candidate as expected; that result does not show a distinct primitive.

## 8. Per-experiment ledger rule

Each experiment has its own ledger. Before any confirmation run, record:
- frozen specification version and approval date;
- exact code commit, configuration, seeds and execution environment;
- run IDs, output paths and SHA-256 hashes;
- per-seed metrics, aggregate summaries and uncertainty;
- deviations, exclusions and their reasons;
- interpretation against the pre-registered criteria;
- decision: **pass**, **fail**, **inconclusive**, or **invalid run**.

The cross-experiment LGDH ledger records changes in the hypothesis and decisions that affect more than one experiment. The repository experiment register gives current status. A CI pass is an execution result, not automatically a scientific pass.


**2026-11-15 freeze:** user approved hidden directed-topology recovery as LG-01B's first operational question and deferred spontaneous emergence. See `lg01b_protocol.md` for frozen parameters, controls and gates. Only γ=0.05 and γ=0.20 are in scope.
