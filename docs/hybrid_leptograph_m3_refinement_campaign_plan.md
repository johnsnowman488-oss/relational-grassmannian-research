# HLG-M3 foundation refinement campaign

**Campaign:** HLG-M3-FOUNDATION-REFINEMENTS-R1-R5-v0.1  
**Status:** targeted pre-freeze refinement; foundation preserved; M3 protocol remains unfrozen.

The adopted HLG-M3 foundation and its F1-F7 results are retained unchanged. This campaign addresses five specific review findings without introducing production M3 runtime code.

| Job | Refinement | Acceptance evidence |
|---|---|---|
| R1 | Coordinate-invariant absolute context fit | Generalised determinant score agrees under transported non-orthogonal coordinates |
| R2 | Stronger prequential attribution | Correlation sweep 0, .5, .9, .99; current target cannot influence its own pre-update prediction |
| R3 | Stateful activation hysteresis | One continuous sequence verifies turn-on, in-band persistence, turn-off and reactivation |
| R4 | Revision detector calibration and candidate gate | Threshold calibrated on stationary validation streams; held-out false-alarm and shifted-stream detection measured; non-improving candidate rejected |
| R5 | Learner/evaluator boundary and resource accounting | Allow-listed learner view; actual state-byte accounting; parameter/update/query costs explicitly required for future Pareto comparison |

## Execution

Five independent GitHub Actions matrix jobs run concurrently. The full repository suite runs on Python 3.10 and 3.12 in parallel. Each refinement job emits one JSON result artifact. The campaign does not freeze the implementation protocol, merge the adopted foundation, or implement the production learner.

## Interpretation limits

R1 tests the mathematical score under a reference coordinate transform. R2 is a synthetic scalar regression probe, not causal identification. R3 validates a deterministic state machine. R4's calibration and detection rates apply only to the declared synthetic residual distribution and schedule. R5 establishes a strict input projection and exact state-byte accounting; it does not claim that C0-C4 performance or compute costs have been compared. Actual architecture implementations must report measured trainable parameters, update multiply-adds, query multiply-adds and persistent bytes before any fairness claim.
