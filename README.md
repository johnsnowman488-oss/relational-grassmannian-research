# Independent Relational Grassmannian Research

An independent, evidence-led research project investigating whether relational organisation conditioned by accumulated temporal memory can be represented usefully through fixed-rank Grassmannian states.

## Research configuration v0.1

- **Interpretation:** coupled relational-memory geometry.
- **Memory:** fixed sum-of-exponentials (SOE) channels; four channels initially.
- **Initial feature space:** \\(\\mathbb{R}^{16}\\).
- **Initial Grassmannian:** \\(\\operatorname{Gr}(4,\\mathbb{R}^{16})\\).
- **Scale:** small, deterministic synthetic experiments before larger models.

## Milestones

| Milestone | Purpose | Status |
|---|---|---|
| E00 | Mathematical and computational foundations | Accepted: 40 tests and Python 3.10/3.12 CI passed |
| E01-A | Memory-only two-hop inference and controls | Complete; results archived |
| E01-A2 | Channel, constituent-retrieval and readout diagnostics | Complete; 27 cells passed |
| E01-A3 | Independent-world/codebook replication | Complete; 54 cells passed |
| E01-B | Capacity and interference frontier | Complete; 228 cells and determinism gate passed |
| E01-C | Mechanism isolation and path-level diagnostics | Complete; 108 cells and oracle gate passed |
| E02 | Explicit relational graph, memory baseline and hybrid evaluation | Initial 54+54 cell campaign passed; aggregate cost report refinement underway |
| E03 | Grassmannian contribution versus non-geometric alternatives | Planned |
| E04 | Coupled system evaluation | Planned |

## Current evidence boundary

E01 establishes a narrow synthetic result about temporal event memory and fixed candidate-path readout. It does **not** establish relation discovery, general relational reasoning, or a Grassmannian performance advantage. The strongest current finding is that dense event superposition and max-product path composition are vulnerable to support loss, duplicate accumulation, and false-path competition.

E02 is implemented and the first full campaign has passed; the aggregate report is being extended to include paired cost summaries. The campaign: E02-A freezes an event-only model interface and leakage controls; E02-B compares explicit graph retrieval with the E01 dense memory baseline; E02-C tests graph-plus-temporal-memory under controlled missing and spurious observations. The experiment reuses the six E01-C conditions, world/codebook seeds and held-out sequence ranges. Model code must receive only observed events and queries. Test labels, latent facts, planted paths and corruption truth remain evaluator-only.

The project remains independent of D2C/Aberconics. SOE superiority and geometric contribution remain open hypotheses; negative results are informative.

## Development

Python 3.10+; NumPy, SciPy, pytest.

~~~bash
python -m pip install -e ".[dev]"
python -m pytest
python -m rgm.experiments.e01 --variant soe
~~~

See [DECISIONS.md](DECISIONS.md), [the mathematical specification](docs/mathematical_specification.md), [the experiment register](docs/experiment_register.md), and the [E02 protocol](docs/e02_protocol.md).
