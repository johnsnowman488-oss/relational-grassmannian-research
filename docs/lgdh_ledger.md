# LGDH Cross-Experiment Ledger

**Research stream:** Lepto-Graph Development Hypothesis  
**Status:** Hypothesis registered; LG-01A protocol frozen for implementation; no experimental results  
**Opened:** 2026-11-14

## 2026-11-14 — LGDH opened as a parallel mechanism hypothesis

### Proposal

Fast, multidimensional memory modes may remain operational under continuous information flow while the contribution of any specific earlier input decays. Their own trajectories provide an endogenous directional signal. Slower memory channels may register trajectory history and provide contextual information that helps fast modes choose where information should flow next. The resulting system may develop directed relational pathways native to its dynamics.

### Clarifications frozen

1. Direction is derived from the trajectory of the mode itself; it is not preassigned as an edge.
2. The trajectory tangent is a direction in source-mode state space, not a destination identifier. A map to candidate destination modes remains an unresolved mechanism.
3. Slower memory registers the history needed for contextual route choice; it does not replace the current trajectory-derived signal.
4. Lepto-modes are proposed primarily as routing/relational state, not as durable stores of each information item.
5. Graph emergence cannot be claimed when a target topology is supplied to the mechanism.
6. Computational neurogenesis and synaptogenesis are separate follow-up hypotheses; neither belongs in LG-01A.
7. The Relational Grassmannian remains an independent mathematical/representation track. It should be introduced into LGDH only if a geometric quantity earns a defined role and measurable value.
8. The LG stream is parallel to the main E-series. E03 remains the next mainline experiment and is not displaced by LG-01A.

### Relation to the completed E01/E02 evidence

E01 tested fixed SOE memory and candidate-path retrieval/composition. E02 compared dense event memory with an explicit observed-event graph and a graph-plus-temporal-memory hybrid. Those results motivate the question but do not demonstrate endogenous trajectory-derived routing. The E02 observed-event graph is the correct explicit-graph reference for later LG comparisons; it is not itself a self-organising lepto-graph.

### Experiment decisions

- **LG-01A:** specify and test only fast-mode transient activity under bounded ongoing refresh, independent tagged-contribution decay, and post-refresh washout.
- **LG-01B:** later test whether trajectories form directed relations using a fixed mode population and no supplied target graph.
- **LG-01C:** later isolate the contribution of slower trajectory registration to contextual routing.
- **LG-01D:** later test relational reorganisation under controlled structural change and irrelevant interference.
- **LG-02A:** mode birth/death (computational neurogenesis), tested in isolation.
- **LG-02B:** directed connection plasticity (computational synaptogenesis), tested in isolation.
- **LG-02C:** combined developmental system, only after the two isolated mechanisms have evidence.

See the LG experiment spine and the LG-01A experiment ledger.

## 2026-11-14 — LG-01A-v0.1 executed; fastest fast-mode gate not met

The LG-01A runner and mathematical/reproducibility tests were implemented on branch research/lgdh-lg01a-spine. Dedicated GitHub Actions run 43652121470, source commit 5fd9b5169bda1617ad3093d5bcd6f5b2877a44a0, passed the complete repository suite on Python 3.10 and 3.12 (122 tests in each environment), then executed all 30 paired seeds (101–130). The complete evidence bundle is artifact lg01a-43652121470-1, artifact ID 14136786352.

The campaign runner completed and uploaded all artifacts. Its final workflow state is failure because the scientific gate failed, not because execution or artifact production failed.

| Fast rate | Seeds meeting the window gate | Result |
|---:|---:|---|
| 0.05 | 30/30 | Pass |
| 0.20 | 30/30 | Pass |
| 0.80 | 26/30 | Fail |

At rate 0.80, seeds 105, 112, 114 and 116 failed the pre-registered requirement that at least 90% of windows in a seed meet activity ratio 5.0 or greater and reference ratio [0.8, 1.2]. Seven windows failed across those four seeds. The aggregate mean activity ratio was 9.26482 (95% CI 8.84306–9.68658); this does not override the per-seed gate.

All mathematical, input-response, analytic-boundedness, finite-state and washout checks passed. The candidate and independently stepped conventional SOE traces matched within maximum relative difference 2.02055e-15 (tolerance 1e-10). Continuous and intermittent input energies matched exactly. Thus the dynamics are fully explained by the ordinary leaky-SOE null in this experiment; no new primitive is demonstrated.

**Decision:** valid scientific fail for LG-01A-v0.1's declared fast-rate range. Keep the result. Do not advance to LG-01B. Any reconsideration of the 0.8 operating threshold, input normalization or timescale range must be made through a dated v0.2 protocol revision and fresh confirmation run; no post-hoc threshold adjustment is permitted.

The LGDH concept remains a hypothesis. This result establishes only that the tested transient-refresh operating condition is reliable at 0.05 and 0.2 under this protocol, not at 0.8 with the chosen criterion. It does not test endogenous routing, historical trajectory registration, graph formation or adaptive reasoning.

### Same-protocol repeat

A second push workflow, run 43652352159 from the workflow-only commit b29a6df4b81653c0ac1055d068dee5ecdee40183, reproduced the same LG-01A-v0.1 outcome: 30/30 seeds at 0.05, 30/30 at 0.2 and 26/30 at 0.8. Both Python 3.10 and 3.12 test jobs again passed 122 tests each. Its complete artifact (ID 14136263436) also passed SHA256SUMS verification. This is repeat execution of the same protocol and seeds, not a new independent-seed confirmation or a protocol revision.
