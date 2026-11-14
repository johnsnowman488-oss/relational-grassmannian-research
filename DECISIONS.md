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

- **2026-11-14 — E01 integration gate:** E01-B and E01-C were merged with PR #6 at `24c8d25107d5191f7c48e4355ca4eb8d48c3a2b5`. The post-merge main validation (run 43593342921) passed all 30 jobs.
- **2026-11-14 — E02 protocol freeze:** E02-v0.1 reuses the six E01-C conditions, world and codebook seeds, and validation/test seed ranges. The model-facing contract contains only observed events, entity domain and query. Latent facts, labels, planted paths and corruption audits remain evaluator-only. E02-B compares graph-only retrieval with slow-only SOE and full-history memory; E02-C compares graph, memory and graph-plus-temporal-memory under clean, missing, spurious and mixed observations. The graph is not treated as capacity-equivalent to a 16-scalar memory trace.
