# Experiment register

| ID | Question | Status | Entry criterion | Exit evidence |
|---|---|---|---|---|
| E00 | Are the mathematical/computational primitives correct and reproducible? | Accepted — implementation gate passed | v0.1 scope frozen | Unit tests, invariant checks, deterministic state round trips, CI pass |
| E01 | Does fixed SOE memory recover history-dependent predictive information? | Planned | E00 acceptance gate passed | Held-out sequence comparison with M0–M4 baselines and controls |
| E02 | Does explicit relational structure add value beyond memory alone? | Planned | E01 evidence reviewed | Ablation and held-out comparisons |
| E03 | Does Grassmannian geometry add value over non-geometric alternatives? | Planned | Independent memory/relational evidence available | Matched representation comparisons and sensitivity analysis |
| E04 | Does the coupled system add value beyond strongest components? | Planned | E02 and E03 reviewed | Controlled coupled-vs-component comparisons |

## E00 run ledger

E00 run_0001 recorded 35 local tests; run_0002 expanded coverage to 40 tests including augmented-state serialization (see results/e00/run_0002). The run_0002 source head a2d85aed9b690c3f2020b4f80e08125a73c3126d passed GitHub Actions on Python 3.10 and 3.12: push run 43043322772 and pull-request run 43043435960. This is implementation acceptance only, not a predictive or novelty result.
