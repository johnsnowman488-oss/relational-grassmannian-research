# Experiment register

| ID | Question | Status | Entry criterion | Exit evidence |
|---|---|---|---|---|
| E00 | Are the mathematical/computational primitives correct and reproducible? | Accepted — implementation gate passed | v0.1 scope frozen | Unit tests, invariants, deterministic state round trips, CI pass |
| E01-A | Can fixed SOE memory support two-hop inference from event history versus control variants? | Implemented; CI triggered | E00 accepted; D2C overlap reviewed | Disjoint held-out sequences, independent controls, artifacts, interpretation review |
| E01-B | Where is the memory capacity/interference frontier? | Deferred pending E01-A review | E01-A diagnostics reviewed | Controlled capacity, distractor, and temporal-gap sweep |
| E02 | Does explicit relational structure add value beyond memory alone? | Planned | E01 evidence reviewed | Ablation and held-out comparisons |
| E03 | Does Grassmannian geometry add value over non-geometric alternatives? | Planned | Independent memory/relational evidence available | Matched representation comparisons and sensitivity analysis |
| E04 | Does the coupled system add value beyond strongest components? | Planned | E02 and E03 reviewed | Controlled coupled-vs-component comparisons |

## E00 run ledger

E00 run_0002 passed the Python 3.10/3.12 CI matrix with 40 tests. This validates implementation and invariants only, not predictive performance or novelty.

## E01-A run ledger

The nine E01-A variants are separate GitHub Actions matrix jobs with fail-fast disabled. Each emits a per-variant JSON artifact. Add run identifiers and measured results only after the CI execution is observed. E01-A is a compact synthetic experiment, not a general claim about relational reasoning.
