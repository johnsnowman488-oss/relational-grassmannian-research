# Research decisions — v0.1

This file records frozen choices, their scope, and what remains open. Changes require a dated decision entry rather than silent drift.

## Frozen configuration

| Decision | v0.1 choice | Boundary |
|---|---|---|
| Research track | Independent relational Grassmannian research | No D2C/Aberconics integration |
| Interpretation | Coupled | Memory conditions relational organisation; memory and geometry remain distinct components |
| Memory | Fixed sum of exponentials (SOE) | Four fixed channels; no adaptive rates or learned dynamics |
| Initial rates | (0.01, 0.05, 0.2, 0.8) | Normalized time units; sensitivity is a later experiment |
| Feature dimension | 16 | Experimental constraint, not a theoretical necessity |
| Grassmannian | Gr(4, R^16) | Rank four is provisional |
| Scale | Small | Deterministic synthetic tests before larger models |
| Tooling | Python, NumPy, SciPy, pytest | No neural framework or compiled core without evidence of need |

## Mathematical separation

1. Event/observable state describes what is currently observed.
2. SOE memory stores decaying traces of event features.
3. The relational engine stores explicit typed, directed, time-stamped relations.
4. A Grassmannian point is a rank-four subspace of the 16-dimensional feature space.
5. An eventual coupled state may condition a geometric representation on memory. E00 does not invent a coupling rule or claim component-level predictive value.

## Decision log

- **2026-11-11 — v0.1 initial configuration:** adopted coupled interpretation, four fixed SOE channels, 16-dimensional feature space, rank-four Grassmannian, and small-scale execution. Initial SOE rates are experimental values, not fitted or optimal values.
- **2026-11-11 — E00 boundary:** implement and test primitives independently. A subspace update is a mathematically valid candidate operation, not an empirically justified model update.
- **2026-11-11 — E00 implementation gate:** accepted after 40 local tests passed and the Python 3.10/3.12 GitHub Actions push and pull-request matrices passed. This validates code and invariants only; predictive hypotheses remain open for E01 onward.
- **2026-11-13 — E01 evidence consolidation:** E01-A, A2, A3, B and C are complete. E01-B's cross-worker prediction changed at a validation-threshold boundary under sub-precision floating-point drift. The decision rule now rounds support/path scores to 12 decimal places before threshold fitting and uses the same inclusive comparison grid at test time. A fresh 228-cell B run passed, including a two-worker zero-difference determinism comparison. E01-C was rerun under the shared score policy and all 108 cells plus the oracle gate passed. This is a numerical reproducibility convention, not probability calibration.
- **2026-11-13 — E02 direction:** compare event-derived explicit graph storage with the E01 dense memory baseline before evaluating Grassmannian geometry. A graph is constructed only from observed events; latent facts, planted paths, corruption masks and held-out labels are reserved for scoring. The graph's storage and query costs must be reported rather than represented as capacity-equivalent to a fixed-size memory state.
- **2026-11-14 — Adaptive relational capability:** D2C experiments motivated a broader investigation of relational discovery, preservation, composition, revision, reorganisation and transfer. This is a research extension and does not itself change D2C implementation or the independent status of this repository.
- **2026-11-14 — Architecture and representation remain open:** SOE-only learned relational readout, coupled temporal/relational states and a unified augmented state remain competing hypotheses. Explicit graphs remain reference models. Grassmannian geometry is a candidate, not a presumed solution; learned non-geometric alternatives must be compared.
- **2026-11-14 — E03 next:** design a representation-neutral task suite with explicit, higher-order and continuous/changing relations before implementing a new relational learner.
- **2026-11-14 — E02 integration completed:** PR #12's campaign and PR #13's graph primitive were reconciled through PR #15. E02 now uses `ObservedEventGraph` as its sole graph-construction path, retaining duplicate counts and full observed-time histories. PR #15 merged to main at `5ee58679e3f8b80c453344815ee91be94ddc181b`. E02 campaign run `43639855566` passed the Python 3.10/3.12 contract tests, all 54 E02-B cells, all 54 E02-C cells and combined aggregation; repository validation run `43639855578` passed. The combined summary is archived as Actions artifact `14132220095`.


- **2026-11-14 — LGDH opened as a parallel mechanism stream:** record the lepto-graph development hypothesis in the Relational Grassmannian research repository, not the Aberconics implementation repository. Keep the LG stream parallel to the E-series; E03 remains the next mainline milestone.
- **2026-11-14 — LG-01A scope frozen:** test only fast-mode transient activity under bounded refresh, decay of an individually tagged contribution, and post-refresh washout. Use the existing 16-dimensional feature space and fixed four-rate SOE bank for continuity. No routing, graph edges, slow trajectory registration, adaptive growth or Grassmannian update in LG-01A.
- **2026-11-14 — LG-01A null and claim ceiling:** ordinary linear SOE auxiliary states are the explicit null baseline and are expected to reproduce the candidate dynamics. A pass validates the operating premise only; it is not evidence of a distinct lepto-graph mechanism or relational reasoning.
- **2026-11-14 — LG follow-up order:** test fixed-population trajectory-derived relation formation (LG-01B), then isolate slow-history registration (LG-01C), then adaptive reorganisation (LG-01D). Test computational neurogenesis and synaptogenesis separately in LG-02A/B before any combined LG-02C system.

- **2026-11-14 — LG-01A-v0.1 execution and decision:** implemented the runner and mathematical/reproducibility tests. GitHub Actions run 43652121470 on source commit 5fd9b5169bda1617ad3093d5bcd6f5b2877a44a0 passed the full 122-test repository suite on Python 3.10 and 3.12, then executed all 30 paired seeds and uploaded artifact 14136786352. Rates 0.05 and 0.2 passed 30/30 seeds; rate 0.8 passed only 26/30, below the frozen 27/30 gate. Mathematical, boundedness, washout, energy-match and conventional-SOE-null checks passed. Record this as a valid scientific fail for the v0.1 fast-rate range. LG-01B implementation and execution remain blocked until its separate protocol is reviewed and frozen; no post-hoc threshold or seed changes are permitted.

- **2026-11-14 — LG-01B downstream scope:** following the LG-01A-v0.1 result, authorise LG-01B protocol specification only at γ=0.05 and γ=0.20 (30/30 each). Keep γ=0.80 recorded as a valid failure (26/30) and exclude it from the initial LG-01B scope. This is not a retrospective LG-01A pass or threshold change.
- **2026-11-14 — LG-01B protocol review state:** a draft protocol has been prepared with a hidden eight-mode directed coupling world, causal tangent features, conditional ridge destination scoring, held-out episodes, controls and edge/path metrics. The protocol remains unapproved and unfrozen; no runner, CI campaign or scientific execution is authorised until the design is reviewed and frozen.
