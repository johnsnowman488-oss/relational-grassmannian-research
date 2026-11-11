# Experiment register

| ID | Question | Status | Entry criterion | Exit evidence |
|---|---|---|---|---|
| E00 | Are the mathematical/computational primitives correct and reproducible? | Local suite 35/35 passed; CI acceptance pending | v0.1 scope frozen | Unit tests, invariant checks, deterministic state round trips, CI pass |
| E01 | Does fixed SOE memory recover history-dependent predictive information? | Planned | E00 acceptance gate passed | Held-out sequence comparison with M0–M4 baselines and controls |
| E02 | Does explicit relational structure add value beyond memory alone? | Planned | E01 evidence reviewed | Ablation and held-out comparisons |
| E03 | Does Grassmannian geometry add value over non-geometric alternatives? | Planned | Independent memory/relational evidence available | Matched representation comparisons and sensitivity analysis |
| E04 | Does the coupled system add value beyond strongest components? | Planned | E02 and E03 reviewed | Controlled coupled-vs-component comparisons |

## E00 run ledger

Local implementation-validation run run_0001 passed 35/35 tests on 2026-11-11; see results/e00/run_0001. This is not predictive evidence. E00 remains open until GitHub Actions passes on the branch and the committed source/evidence snapshot is checked.
