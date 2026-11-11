# E01-A run 0001 — initial CI results

- Source commit: b6942ba30135905f4c480334553ff15b4788c9ec
- Push workflow: [43054096437](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43054096437) — success
- PR workflow: [43054216655](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43054216655) — success
- Unit tests: Python 3.10 and 3.12 passed; all nine E01 matrix jobs passed
- Validation/test: 160 / 160 sequences per arm; identical held-out seed ranges across arms

## Results

| Variant | Accuracy | Wilson 95% interval | Balanced accuracy | Brier score | Positive nonzero support |
|---|---:|---:|---:|---:|---:|
| SOE (four channels) | 0.6438 | 0.567–0.714 | 0.6438 | 0.2380 | 0.975 |
| Slow-only (0.01) | **0.6625** | 0.586–0.731 | **0.6625** | 0.2595 | 0.925 |
| Fast-only (0.8) | 0.5813 | 0.504–0.655 | 0.5813 | 0.4417 | 0.800 |
| Full history | 0.6438 | 0.567–0.714 | 0.6438 | 0.2775 | 0.950 |
| Shuffled SOE history | 0.6375 | 0.561–0.708 | 0.6375 | **0.2410** | 0.975 |
| Window 8 | 0.6313 | 0.554–0.702 | 0.6313 | 0.2674 | 0.950 |
| Window 2 | 0.5375 | 0.460–0.613 | 0.5375 | 0.4046 | 0.650 |
| Current event | 0.4938 | 0.417–0.570 | 0.4938 | 0.4568 | 0.388 |
| Reset | 0.5000 | 0.423–0.577 | 0.5000 | 0.5000 | 0.000 |

## Initial interpretation

1. The current-event and reset controls are near chance; the two-event window is only modestly above chance. Retaining more event history materially improves this particular task family.
2. Four-channel SOE reaches 64.4% accuracy, but does **not** beat the single slow channel (66.3%) or the un-decayed full-history reference (64.4%). The accuracy intervals overlap substantially. This run therefore does not establish a benefit from multiple SOE timescales.
3. Shuffling event order changes accuracy only slightly relative to SOE (63.8% vs 64.4%). In this configuration, order-sensitive decay is not shown to be the source of the observed advantage over short-window/current-event controls.
4. SOE has the lowest reported Brier score (0.238), but these are raw bounded composition-support scores, not a calibrated probabilistic readout. Treat Brier only as a descriptive score comparison, not as calibrated uncertainty evidence.

## Limitations and decision

This is one deterministic synthetic task family, one fixed encoder, four entities, two-hop composition, and 160 test sequences per arm. The same test cases are used across arms, but the current artifact stores aggregate metrics rather than per-case predictions; paired significance testing is therefore not yet available. All accuracy confidence intervals overlap. The relation-specific orthogonal codebooks and candidate-middle composition decoder are strong representational assumptions, not a general-purpose relational learner.

**Decision:** E01-A execution and CI validation pass as an implementation/pipeline milestone. Scientific conclusion remains limited: history retention helps this task relative to current/reset/short-window controls, but no multi-timescale SOE advantage is demonstrated. Before E01-B, improve diagnostics to retain per-case fact-support scores and predictions, then run paired comparisons and a pre-specified capacity/interference sweep. Do not proceed to an SOE superiority claim or treat E01-A as proof of general relational reasoning.
