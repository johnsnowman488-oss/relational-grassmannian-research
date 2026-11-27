# Task 11 non-oracle baseline validation record v1

**Status:** ACCEPTED — baseline validation only  
**Run:** [GitHub Actions 46078354046](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/46078354046)  
**Commit:** `9a91ff6e7ff7a3183bcec604d09662a6bf171a23`  
**Artifact:** `babi-task11-nonoracle-baseline-validation`, ID `15235003730`  
**Artifact ZIP digest:** `sha256:490255b5d2cdaae3aa247f3ef3e458f0f0163b37dbc76d94e00d903b488c9004`

## Frozen validation sample

| Item | Accepted value |
|---|---:|
| Task | 11 only |
| Fit stories | 1,800 |
| Validation stories | 200 |
| Validation queries | 1,000 |
| Fit/validation overlap | 0 |
| Official test queries loaded | 0 |
| Confirmatory labels loaded | 0 |
| Learning updates | 0 |

Source member SHA-256: `edfcd97fecd4a5045af25e1790cf1408856ae362c39521b1b69cd32b88ec0ced`  
Validation partition SHA-256: `b7d8347930eb99deee0d3df36b931f5099c3814988d9ef3d3d8b8cee85b88dd0`  
Scorecard SHA-256: `43dc4434e813ef65f32116d1d1bdc2f6430c006c873eb8430887a0fa77bff15d`

## Results

| Non-oracle baseline | Answer exact match | Coverage | Support-witness recall | False-witness rate |
|---|---:|---:|---:|---:|
| Nearest-compatible antecedent | 1.000 (1,000/1,000) | 1.000 | 1.000 (2,000/2,000) | 0.000 |
| Recency-only | 0.704 (704/1,000) | 1.000 | 0.3255 (651/2,000) | 0.349 |

Both predictors were evaluated against the same frozen 1,000 validation queries. Their input is limited to source-observed story/query objects; the labels enter only at the scoring boundary.

## Interpretation

The nearest-compatible-antecedent baseline is the strongest current non-oracle comparator and achieves perfect answer and support-witness scores on this particular validation split. The recency-only control is materially weaker. This shows that identity-aware resolution is important in this dataset; it does **not** establish HLA/HLB learning effectiveness.

The result is also a demanding candidate-selection threshold: a learned HLA/HLB candidate must match the strongest baseline on the same validation queries while meeting the integrity, coverage and witness requirements. If no candidate does so, the correct outcome is no candidate selected—not a relaxed threshold.

Official Task 11 labels do not include independent antecedent-edge gold. Coreference-edge precision/recall/F1, antecedent top-1 accuracy and entity-chain exact match remain **NOT INDEPENDENTLY EVALUABLE**. No such metrics are inferred from the baseline's own weak resolver.

This record closes the baseline-validation gate for Task 11 only. It does not authorize or constitute the 120-unit learning campaign. Tasks 14 and 19 remain locked.
