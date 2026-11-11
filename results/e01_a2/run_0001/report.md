# E01-A2 — Diagnostic audit, run 0001

**Status:** completed; all 27 diagnostic cells and the paired-summary job succeeded.  
**Workflow run:** [43058306505](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43058306505) (run 51)  
**Experiment commit:** `ac2016405fff1dacf722cd163c144720dfac8a49`  
**Paired-summary artifact:** `e01-a2-paired-summary` (artifact ID `13872661461`)

## Frozen design

- Four entities; two typed directed relations; two-edge composition query.
- 160 validation and 160 held-out test sequences per cell.
- Identical validation/test seed ranges across all 27 cells.
- Fixed codebook seed 9137; fixed SOE rates 0.01, 0.05, 0.2, 0.8.
- Thresholds for constituent retrieval and composition fitted on validation only.
- Nine memory configurations (full, four single-channel, four leave-one-channel-out) × three readouts (max-channel, same-channel, equal-weight mean).
- Every cell saved all 160 test sequences, 24 candidate facts per sequence, per-channel supports, predictions, events, query, and state norms.
- 27 per-cell JSON artifacts were uploaded. The paired-summary job compared every cell with full/max-channel using paired bootstrap intervals and exact two-sided McNemar tests.

## Composition results

| Configuration | Accuracy | Difference vs full/max |
|---|---:|---:|
| Full / max-channel | 64.38% | baseline |
| Full / same-channel | 64.38% | 0.00 pp |
| Full / mean-channel | 62.50% | −1.88 pp |
| Only channel 0 (0.01) | 66.25% | +1.88 pp |
| Only channel 1 (0.05) | 57.50% | −6.88 pp |
| Only channel 2 (0.2) | 54.38% | −10.00 pp |
| Only channel 3 (0.8) | 58.13% | −6.25 pp |
| Drop channel 0 | 56.25% | −8.13 pp |
| Drop channel 1 | 65.63% | +1.25 pp |
| Drop channel 2 | 64.38% | 0.00 pp |
| Drop channel 3 | 63.75% | −0.63 pp |

The full/max baseline reproduces E01-A's 64.38% test accuracy.

### Paired comparisons against full/max-channel

| Comparison | Accuracy difference | Paired bootstrap 95% interval | McNemar p |
|---|---:|---:|---:|
| Only channel 0 | +1.88 pp | [−2.50, +6.25] pp | 0.581 |
| Drop channel 0 | −8.13 pp | [−16.25, 0.00] pp | 0.085 |
| Only channel 1 | −6.88 pp | [−15.63, +1.88] pp | 0.169 |
| Only channel 2 | −10.00 pp | [−19.38, −0.63] pp | 0.060 |
| Only channel 3 | −6.25 pp | [−16.25, +3.75] pp | 0.268 |
| Drop channel 1 | +1.25 pp | [−1.25, +3.75] pp | 0.625 |
| Drop channel 2 | 0.00 pp | [0.00, 0.00] pp | 1.000 |
| Drop channel 3 | −0.63 pp | [−1.88, 0.00] pp | 1.000 |
| Full / same-channel | 0.00 pp | [−3.13, +3.75] pp | 1.000 |
| Full / mean-channel | −1.88 pp | [−8.75, +5.00] pp | 0.711 |

The 26 comparisons are exploratory and unadjusted for multiple comparisons. Effect sizes and paired intervals matter more than isolated p-values. In particular, the channel-2-only result is suggestive but does not pass a conventional 0.05 McNemar threshold.

## Constituent-fact retrieval

| Configuration/readout | Accuracy | Precision | Recall |
|---|---:|---:|---:|
| Full / max-channel | 80.57% | 81.50% | 72.23% |
| Full / same-channel | 74.92% | 70.72% | 73.36% |
| Full / mean-channel | 74.92% | 70.72% | 73.36% |
| Only channel 0 | 80.52% | 78.92% | 76.02% |
| Only channel 1 | 70.99% | 71.80% | 56.07% |
| Only channel 2 | 63.52% | 88.50% | 19.60% |
| Only channel 3 | 61.93% | 88.74% | 15.39% |
| Drop channel 0 | 69.97% | 70.33% | 54.88% |
| Drop channel 1 | 80.57% | 81.67% | 72.00% |
| Drop channel 2 | 80.65% | 81.74% | 72.11% |
| Drop channel 3 | 80.57% | 81.54% | 72.17% |

Max-channel aggregation improves constituent-fact accuracy and precision over equal-weight mean aggregation, while recall is similar. That improvement does not translate into a demonstrated composition-accuracy gain: max-channel and same-channel composition have identical aggregate accuracy, and their paired McNemar comparison is not significant.

## Interpretation

1. **The slowest channel (0.01) is the strongest signal in this generator.** Removing it reduces constituent-fact retrieval from 80.57% to 69.97% and composition accuracy from 64.38% to 56.25%.
2. **Slow-only is a credible simpler challenger, not a proven winner.** It reaches 66.25% composition accuracy, but its paired interval against full SOE includes zero and McNemar p is 0.581.
3. **The other channels have not shown an independent positive contribution.** Removing channel 2 gives exactly the same max-channel test predictions as the full bank. Single channel 2 has the weakest composition result, although the paired evidence remains exploratory.
4. **Cross-channel composition is not shown to be necessary here.** Same-channel and independent max-channel readouts both reach 64.38%; equal-weight mean reaches 62.50%, with no significant paired difference from max-channel.
5. **Max-channel selection helps fact-level precision, but not aggregate two-hop accuracy.** This separates constituent retrieval from composition and is precisely the distinction this audit was designed to expose.

## Limits

This remains a small synthetic, fixed-codebook task with a supplied candidate-intermediate decoder. It does not test relation discovery or general-purpose relational reasoning. There are only 160 held-out sequences per cell. The full SOE state has 64 scalar values; single-channel controls have 16 and leave-one-out controls 48. The experiment is not capacity-matched and makes no memory-efficiency claim. The un-decayed full-history reference from E01-A is not repeated in this audit.

## Gate decision

E01-A2 is sufficiently understood to proceed to **E01-A3 replication**, but not to E01-B. The replication should retain these six diagnostic configurations:

- full / max-channel (primary reference);
- only channel 0 / max-channel (slow-only challenger);
- drop channel 0 / max-channel (slow-channel necessity control);
- drop channel 2 / max-channel (redundancy check);
- full / same-channel (cross-channel composition control);
- full / mean-channel (fixed aggregation control).

E01-A3 should use independent synthetic-world seed ranges and multiple fixed codebook seeds, with paired validation/test worlds across configurations. E01-B remains gated until those replications establish whether the A2 pattern is reproducible.
