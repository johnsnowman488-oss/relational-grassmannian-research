# E00 implementation validation — run_0002

**Date:** 2026-11-11  
**Run type:** implementation, interface, and mathematical-invariant validation  
**Result:** 40 passed, 0 failed, 0 skipped

## Coverage

- SOE memory: analytical exponential decay, event injection, decay-rate differentiation, reset, defensive snapshots, input validation, serialization, and continuation trajectory.
- Symbolic relations: temporal validity, revisions, explicit inverse/composition rules, functional-predicate contradiction checks, duplicate IDs, and automatic revision IDs.
- Grassmannian geometry: orthonormal frames, projector invariants, basis-change invariance, principal angles, canonical distance, skew-generator evolution, fixed rank, and reproducible initialization.
- Transition interface: normalized categorical distributions, score conversion, label and probability validation.
- Augmented state: versioned JSON round trip for observable state, SOE channels, relational schema and event history, and Grassmannian subspace; continuation of the same SOE trajectory after restoration.

## Interpretation

All 40 tests passed locally using Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0, and pytest 9.0.2. This remains implementation validation, not a predictive experiment. No performance, novelty, superiority, or scientific-utility claim is made.

GitHub Actions passed on the source commit a2d85aed9b690c3f2020b4f80e08125a73c3126d on both Python 3.10 and 3.12. Push run 43043322772 and pull-request run 43043435960 both completed successfully; see ci_summary.json.
