# Experiment register

| ID | Question | Status | Entry criterion | Exit evidence |
|---|---|---|---|---|
| E00 | Are the mathematical/computational primitives correct and reproducible? | Active | v0.1 scope frozen | Unit tests, invariant checks, deterministic state round trips, CI pass |
| E01 | Does fixed SOE memory recover history-dependent predictive information? | Planned | E00 acceptance gate passed | Held-out sequence comparison with M0–M4 baselines and controls |
| E02 | Does explicit relational structure add value beyond memory alone? | Planned | E01 evidence reviewed | Ablation and held-out comparisons |
| E03 | Does Grassmannian geometry add value over non-geometric alternatives? | Planned | Independent memory/relational evidence available | Matched representation comparisons and sensitivity analysis |
| E04 | Does the coupled system add value beyond strongest components? | Planned | E02 and E03 reviewed | Controlled coupled-vs-component comparisons |

## E00 run ledger

No E00 run has yet been accepted at the time this register was created. CI and local test execution results will be added with commit and environment metadata. A test pass is not a scientific result.
