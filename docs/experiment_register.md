# Experiment register

| ID | Question | Status | Entry criterion | Exit evidence |
|---|---|---|---|---|
| E00 | Are the mathematical/computational primitives correct and reproducible? | Expanded local suite 40/40 passed; CI matrix pending | v0.1 scope frozen | Unit tests, invariant checks, deterministic state round trips, CI pass |
| E01 | Does fixed SOE memory recover history-dependent predictive information? | Planned | E00 acceptance gate passed | Held-out sequence comparison with M0–M4 baselines and controls |
| E02 | Does explicit relational structure add value beyond memory alone? | Planned | E01 evidence reviewed | Ablation and held-out comparisons |
| E03 | Does Grassmannian geometry add value over non-geometric alternatives? | Planned | Independent memory/relational evidence available | Matched representation comparisons and sensitivity analysis |
| E04 | Does the coupled system add value beyond strongest components? | Planned | E02 and E03 reviewed | Controlled coupled-vs-component comparisons |

## E00 run ledger

Local implementation-validation run run_0002 passed 40/40 tests on 2026-11-11; see results/e00/run_0002. The previous 35-test run is retained as run_0001. Neither run is predictive evidence. E00 remains open until GitHub Actions passes on this expanded state-persistence snapshot.
