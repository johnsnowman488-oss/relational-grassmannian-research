# LG-01B Experiment Ledger

**Experiment:** LG-01B — Trajectory-Derived Directional Relations  
**Protocol:** LG-01B-v0.1 (frozen 2026-11-15)  
**Status:** First 30-world campaign complete; same-seed evidence replay pending  
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

## Campaign 1 — completed

| Item | Value |
|---|---|
| GitHub Actions run | [43658776160](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43658776160) |
| Run ID | `lg01b_43658776160_1` |
| Source commit | `57c546d4a417df2a34ba21e4ee4d6eeb6fe6a294` |
| Artifact | `lg01b-43658776160-1` (ID `14139840352`) |
| Artifact ZIP SHA-256 | `238d7fd54815b4ba910e5062fb6a6cd00407ff150c0253066d9cdc150749824e` |
| Frozen protocol snapshot SHA-256 | `e8ecaaf1ba0bc07b29ef612fe4848442d572e9c66831a5fd1c7196610cf2e9cf` |
| Worlds / rate conditions | 30 / 60 |
| Runtime / peak memory | 346.06 s / 187,326,464 bytes |
| Unit suite | 143 passed on Python 3.10 and 143 passed on Python 3.12 |
| Bundle integrity | 459 SHA256SUMS entries; all verified |
| Overall scientific decision | **FAIL** (both rates fail; no pooled rescue) |

### Rate-level results

| Measure | γ=0.05 | γ=0.20 |
|---|---:|---:|
| Mean primary precision@2 | 0.2729 | 0.3188 |
| Paired-bootstrap 95% CI | [0.2396, 0.3042] | [0.2771, 0.3646] |
| Worlds with precision@2 ≥0.50 | 0/30 | 3/30 |
| Strongest edge control | Direction-blind | Reverse-time |
| Strongest control mean precision@2 | 0.2938 | 0.3417 |
| Primary minus strongest control | −0.0208 | −0.0229 |
| Paired-bootstrap CI for margin | [−0.0750, −0.0021] | [−0.0729, 0.0271] |
| Primary two-hop path precision | 0.0865 | 0.0885 |
| Primary minus strongest path control | −0.0042 | −0.0313 |
| Selected-edge test contribution | −0.03058 | −0.05997 |
| Non-selected pair test contribution | −0.03114 | −0.06288 |
| Uncoupled-null selected contribution | −0.03044 | −0.05978 |
| Coupled-minus-null contribution 95% CI | [−0.000315, 0.000013] | [−0.001098, 0.000659] |

At γ=0.05 the primary precision@2 mean is below the 2/7 chance baseline. At γ=0.20 the mean is above chance, but its paired-bootstrap lower bound is below chance. Neither rate approaches the 0.60 mean precision threshold or the 24/30 per-world threshold. The primary learner is beaten by the direction-blind control at γ=0.05 and the reverse-time control at γ=0.20. Path precision is far below 0.30 at both rates and below the strongest path control.

The selected-edge contribution is negative at both rates. The fact that it is slightly less negative than the non-selected mean is the only acceptance criterion that passed at either rate; it does **not** indicate positive predictive utility. Coupled-minus-uncoupled confidence intervals include zero at both rates.

### Numerical and evidence checks

- All 60 coupled transition matrices passed the strict stability check. Minimum symmetric dissipativity margin: 0.04454 at γ=0.05 and 0.17818 at γ=0.20. Maximum transition spectral radius: 0.99439 and 0.97775 respectively.
- All 30 hidden graphs had the declared two outgoing edges per source, no self-edges, and were strongly connected. Maximum rejected graph draws for any world: 6.
- No degenerate tangent samples occurred in the coupled training episodes.
- The archive contains 30 evaluator-only hidden-world records, 360 model-facing payload hash/regeneration manifests, 60 prediction files, and 3,000 seed-manifest entries.
- The protocol snapshot hash in the archive matches the environment record. All 459 internal SHA256SUMS checks passed.
- The environment record's full Git status showed only the generated untracked `results/lg01b/` output directory, created before the original status capture; no tracked source files were modified by the execution. The implementation now distinguishes tracked-source cleanliness from generated output status.

### Execution versus scientific outcome

The runner completed, wrote its summary/report, and uploaded the 775,979-byte evidence bundle successfully. The GitHub workflow is marked failed only because the final gate-propagation step correctly returns a nonzero result for the pre-registered scientific failure. This is not an infrastructure or numerical execution failure.

## Reproducibility replay

A documentation/evidence-sync commit triggers a second execution with the same frozen configuration, world seeds and source-level scientific implementation. Its purpose is to check deterministic reproducibility of the recorded run, not to alter any parameter or threshold. The first campaign above remains the canonical initial result; the replay will be recorded separately.

## Interpretation and next gate

LG-01B-v0.1 failed at both eligible rates. The result does not support advancing to LG-01C under the current precondition. Do not increase c, lower thresholds, change the feature definition, or retrospectively reinterpret the outcome. Any revised mechanism requires a separately dated protocol revision and a fresh confirmation campaign. A next review should diagnose why trajectory tangents do not provide reliable directed-edge recovery at c=0.05, including the contribution of the direction-blind and reverse-time controls, without using these held-out results to retune LG-01B-v0.1.

Even a pass would have established only task-specific recovery of a hidden directed coupling structure in this synthetic linear system with known out-degree. This failure does not by itself settle spontaneous topology emergence, nonlinear relational dynamics, or broader LGDH hypotheses.
