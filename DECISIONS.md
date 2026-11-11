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
