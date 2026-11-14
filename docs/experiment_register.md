# Experiment register

| ID | Question | Status | Entry criterion | Exit evidence |
|---|---|---|---|---|
| E00 | Are mathematical/computational primitives correct and reproducible? | Accepted | v0.1 scope frozen | Unit tests, invariants, deterministic state round trips, Python 3.10/3.12 CI |
| E01-A | Can fixed SOE memory support two-hop inference versus controls? | Complete | E00 accepted; overlap reviewed | Nine controls, held-out sequences, archived evidence |
| E01-A2 | Which memory channels/readouts support retrieval and composition? | Complete | E01-A reviewed | 27-cell diagnostic audit; constituent probes and ablations |
| E01-A3 | Does the A2 pattern replicate across worlds/codebooks? | Complete | A2 configuration selected | 54-cell paired replication across 3 worlds × 3 codebooks |
| E01-B | Where does the memory capacity/interference frontier degrade? | Complete | A3 reviewed | 228-cell one-factor frontier; corrected cross-worker determinism gate |
| E01-C | Why does relational composition fail under selected stresses? | Complete | B frontier reviewed | 108-cell mechanism campaign; repeat suppression, path diagnostics and oracle gate |
| E02-A | Can we freeze a leakage-safe graph/event interface and reproducible corpus? | Next | E01 complete | Schema/contract tests, event-only model input, evaluator-only truth, stable hashes |
| E02-B | Does explicit event-derived graph storage outperform dense memory on the six E01-C conditions? | Planned | E02-A contract passes | Paired held-out graph-vs-memory outputs, path/query, cost and storage metrics |
| E02-C | Does graph-plus-temporal memory add value under controlled corruption? | Planned | E02-A contract passes | Paired clean/corrupted comparisons, robustness and temporal-context metrics |
| E03 | Does Grassmannian geometry add value over non-geometric alternatives? | Planned | Independent memory/relational evidence available | Matched representation comparisons and sensitivity analysis |
| E04 | Does the coupled system add value beyond its strongest components? | Planned | E02 and E03 reviewed | Controlled coupled-vs-component comparisons |

## E00 run ledger

E00 run_0002 passed the Python 3.10/3.12 CI matrix with 40 tests. This validates implementation and invariants only, not predictive performance or novelty.

## E01 run ledger

| Stage | Workflow run | Evidence |
|---|---:|---|
| E01-A | 43054698098 | Nine memory/control variants and unit-test matrix passed |
| E01-A2 | 43058306505 | 27 diagnostic cells and paired summary passed |
| E01-A3 | 43061507431 | 54 replication cells and paired summary passed |
| E01-B corrected | 43433259761 | 228 cells, Python 3.10/3.12 tests, two independent replicas, zero-difference determinism comparison, and summary passed |
| E01-C stable-threshold | 43433509287 | 108 cells, Python 3.10/3.12 tests, oracle gate, and paired summary passed |

Primary reports:
- [E01-A](../results/e01/run_0001/report.md)
- [E01-A2](../results/e01_a2/run_0001/report.md)
- [E01-A3](../results/e01_a3/run_0001/report.md)
- [E01-B corrected](../results/e01_b/run_0001/report.md)
- [E01-C stable-threshold](../results/e01_c/run_0001/report.md)

## E01 interpretation boundary

The A-series supports a task-specific slow-timescale contribution but does not show that the four-channel SOE bank beats slow-only SOE. B shows no aggregate composition advantage from the larger SOE bank. C identifies duplicate-event accumulation and false-path competition as important failure mechanisms, while long-gap evidence illustrates the trade-off between decaying traces and persistent facts.

None of E01-A through E01-C tests Grassmannian geometry. E01 is evidence about a constrained memory/readout task, not a result for the project's central geometric hypothesis.

## E02 entry conditions

1. The event-side model interface is distinct from evaluator truth.
2. The graph is built only from observed event records and relation definitions.
3. Test labels, latent fact sets, planted paths and corruption masks are unavailable to prediction jobs.
4. Validation labels may be exposed only for declared calibration; test truth is consumed only by scoring jobs after predictions are sealed.
5. Both architectures receive the same event/query inputs, conditions, seed manifests and held-out queries.
6. Storage and compute are reported separately; an unbounded explicit graph is not treated as capacity-equivalent to a 16-scalar trace.
