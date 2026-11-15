# LG-01B Experiment Ledger

**Experiment:** LG-01B — Trajectory-Derived Directional Relations  
**Protocol:** LG-01B-v0.1 (frozen 2026-11-15)  
**Status:** Implementation and campaign validation in progress  
**Branch:** `research/lg01b-implementation`  
**Protocol:** [docs/lg01b_protocol.md](lg01b_protocol.md)

## Frozen question

Can a trajectory-only learner recover the hidden directed edges of a stable, coupled eight-mode synthetic system on independent held-out input episodes?

This is a topology-reconstruction / system-identification test. It is not a spontaneous graph-emergence experiment. The known out-degree prior is k=2; coupling remains c=0.05. No coupling or acceptance threshold may be changed after seeing results.

## Scope

- Rates: γ=0.05 and γ=0.20; reported independently.
- 30 paired worlds: seeds 301–330.
- γ=0.80 is excluded from LG-01B because LG-01A-v0.1 validly failed at that rate (26/30). LG-01A is not revised.
- Train/validation/test are independent episodes with declared burn-in and duration.
- Primary learner sees only mode trajectories and declared dimensions / k=2 prior.
- Evaluator-only graph, R, graph seed and labels are kept separate from the model mapping interface.
- E03 remains the next mainline E-series milestone; LGDH is parallel.

## Frozen gates

A rate passes only if every gate passes: mean edge precision@2 ≥0.60; 95% paired-world bootstrap lower bound above 2/7; at least 24/30 worlds at precision≥0.50; ≥0.10 margin over the strongest declared edge control with paired-bootstrap CI lower bound >0; positive test selected-edge contribution exceeding unselected and paired uncoupled-null top-two contribution; path precision≥0.30 and ≥0.10 above the strongest path control. Bootstrap: 10,000 resamples, seed 4401. Details and full controls are in the frozen protocol.

## Execution record

No campaign result is recorded yet. This ledger will be updated from the immutable run bundle after workflow completion.

| Item | Value |
|---|---|
| Protocol freeze date | 2026-11-15 |
| Protocol version | LG-01B-v0.1 |
| Implementation branch | `research/lg01b-implementation` |
| Runner | `src/rgm/experiments/lg01b.py` |
| Mathematical / reproducibility tests | `tests/test_lg01b.py` |
| Workflow | `.github/workflows/lg01b.yml` |
| Campaign run | Pending |
| Evidence artifact | Pending |
| Scientific decision | Pending |

## Required evidence bundle

The campaign must preserve configuration, frozen protocol snapshot and hash, repository revision / working-tree state, environment, seed derivation manifest, evaluator-only truth, model-facing payload hashes and regeneration metadata, rankings and pair scores, per-world/rate/control metrics, held-out test contributions, paired bootstrap gates, cost metrics, report, and SHA256SUMS. A CI execution failure and a scientific gate failure must be distinguished explicitly.

## Interpretation boundary

Even a pass establishes only task-specific recovery of a hidden directed coupling structure in this synthetic linear system with known out-degree. It does not establish spontaneous topology emergence, unknown-degree discovery, nonlinear destination mapping, neurobiological equivalence, or general reasoning.
