# Independent Relational Grassmannian Research

An independent, evidence-led research project investigating whether relational organisation conditioned by accumulated temporal memory can be represented usefully through fixed-rank Grassmannian states.

## Research configuration v0.1

- **Interpretation:** coupled relational-memory geometry.
- **Memory:** fixed sum-of-exponentials (SOE) channels; four channels initially.
- **Initial feature space:** \\(\\mathbb{R}^{16}\\).
- **Initial Grassmannian:** \\(\\operatorname{Gr}(4,\\mathbb{R}^{16})\\).
- **Scale:** small, deterministic synthetic experiments first.

## Milestones

| Milestone | Purpose | Status |
|---|---|---|
| E00 | Mathematical and computational foundations | Accepted: 40 tests and Python 3.10/3.12 CI passed |
| E01-A | Memory-only two-hop inference with independent controls | Implemented; CI matrix triggered |
| E01-B | Memory capacity/interference frontier | Deferred pending E01-A review |
| E02 | Explicit relational structure contribution | Planned |
| E03 | Grassmannian contribution versus non-geometric representations | Planned |
| E04 | Coupled system evaluation | Planned |

The project does not assume SOE superiority or that Grassmannian geometry adds predictive value. Negative results are informative. The track is independent of D2C/Aberconics; prior D2C work on delayed retrieval, temporal traces, and sequential slot-value association is acknowledged. E01-A asks the narrower question of compositional inference from an SOE-only event trace.

## Development

Python 3.10+; NumPy, SciPy, pytest.

~~~bash
python -m pip install -e ".[dev]"
python -m pytest
python -m rgm.experiments.e01 --variant soe
~~~

See [DECISIONS.md](DECISIONS.md), [the mathematical specification](docs/mathematical_specification.md), [the experiment register](docs/experiment_register.md), and [the E01-A protocol](docs/e01_protocol.md).
