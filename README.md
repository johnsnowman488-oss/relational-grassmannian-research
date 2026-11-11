# Independent Relational Grassmannian Research

An independent, evidence-led research project investigating whether relational organisation conditioned by accumulated temporal memory can be represented usefully through fixed-rank Grassmannian states.

## Research configuration v0.1

- **Interpretation:** coupled relational-memory geometry.
- **Memory:** fixed sum-of-exponentials (SOE) channels; four channels initially.
- **Initial feature space:** \(\mathbb{R}^{16}\).
- **Initial Grassmannian:** \(\operatorname{Gr}(4,\mathbb{R}^{16})\).
- **Scale:** small, deterministic synthetic experiments first.

The SOE memory stores multiscale temporal traces. The relational layer stores explicit typed relations and their temporal validity. The Grassmannian state represents a fixed-rank subspace of relational organisation, conditioned by memory. These are distinct objects and will be validated independently before they are coupled.

## Milestones

| Milestone | Purpose | Status |
|---|---|---|
| E00 | Mathematical and computational foundations: SOE memory, symbolic relations, Grassmannian primitives, transition interface | In progress |
| E01 | Establish history dependence and compare memory representations with Markov baselines | Planned |
| E02 | Test the additional value of explicit relational structure | Planned |
| E03 | Test the contribution of Grassmannian geometry against non-geometric representations | Planned |
| E04 | Test the coupled system after component-level evidence exists | Planned |

## Scientific boundary

The project does not assume that SOE memory is superior to finite-order Markov models or that Grassmannian geometry adds predictive value. A negative result is informative. No performance or novelty claim will be made from E00 alone.

This repository is independent of D2C/Aberconics. No integration is planned for v0.1.

## Development

Python 3.10+; NumPy; SciPy; pytest.

```bash
python -m pip install -e ".[dev]"
pytest
```

See [DECISIONS.md](DECISIONS.md), [the mathematical specification](docs/mathematical_specification.md), and [the experiment register](docs/experiment_register.md) for the frozen scope and evidence rules.
