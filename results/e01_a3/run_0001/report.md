# E01-A3 — Replication, run 0001

**Status:** completed; all 54 replication cells, both unit-test jobs, and the paired-summary job succeeded.  
**Workflow run:** [43060065891](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43060065891) (run 4)  
**Experiment commit:** `e919d681dac893de370eeaab710799fdc84d05f3`  
**Paired-summary artifact:** `e01-a3-paired-summary` (artifact ID `13872727810`)

## Frozen design

- Six configurations selected from E01-A2.
- Synthetic-world seeds: 101, 202, 303.
- Codebook seeds: 9137, 27183, 65537.
- Nine paired world/codebook cells per configuration; 160 validation and 160 held-out test sequences per cell.
- Same test cases shared across configurations within each world/codebook pair.
- Validation-only threshold selection.
- Per-sequence event/query evidence, candidate-fact supports, channel supports, composition predictions and state norms.

## Replicated composition results

| Configuration | Mean accuracy | Between-replicate SD | Range |
|---|---:|---:|---:|
| Full SOE / max-channel | 67.08% | 2.56 pp | 63.75–71.25% |
| Slow-only / max-channel | 67.43% | 3.34 pp | 61.88–71.25% |
| Drop slow channel | 55.42% | 3.63 pp | 49.38–61.25% |
| Drop channel 2 | 67.36% | 3.38 pp | 63.75–74.38% |
| Full SOE / same-channel | 66.53% | 2.76 pp | 63.12–70.00% |
| Full SOE / mean-channel | 61.88% | 3.14 pp | 56.87–68.13% |

## Paired replicate-level comparisons against full/max-channel

| Configuration | Mean paired difference | 95% paired replicate-bootstrap interval | Replicates better / worse / tied | Exact sign-test p |
|---|---:|---:|---:|---:|
| Slow-only | +0.35 pp | [−1.18, +2.01] pp | 5 / 4 / 0 | 1.000 |
| Drop slow channel | −11.67 pp | [−13.47, −9.79] pp | 0 / 9 / 0 | 0.0039 |
| Drop channel 2 | +0.28 pp | [−0.21, +1.04] pp | 1 / 1 / 7 | 1.000 |
| Same-channel | −0.56 pp | [−1.81, +0.69] pp | 2 / 6 / 1 | 0.289 |
| Mean-channel | −5.21 pp | [−7.64, −3.54] pp | 0 / 9 / 0 | 0.0039 |

The paired replicate bootstrap resamples the nine world/codebook cells and is the primary uncertainty estimate. Pooled sequence-level McNemar tests are secondary because each world is reused across codebook seeds.

## Constituent retrieval

Mean constituent-fact retrieval accuracy across the nine replicates:

| Configuration | Retrieval accuracy |
|---|---:|
| Full SOE / max-channel | 79.99% |
| Slow-only / max-channel | 80.40% |
| Drop slow channel | 69.36% |
| Drop channel 2 | 80.04% |
| Full SOE / same-channel | 74.64% |
| Full SOE / mean-channel | 74.64% |

## Interpretation

1. The slow-channel dependence observed in A2 replicated strongly: removing the 0.01 channel reduced composition accuracy by 11.67 percentage points, and all nine paired replicates were worse.
2. Slow-only performed essentially the same as the full four-channel bank. The added channels have not demonstrated an independent composition benefit in this task.
3. Removing channel 2 had negligible effect; seven of nine paired replicates were exactly tied in accuracy.
4. Same-channel composition remained close to independent max-channel composition. Cross-channel composition is not shown to be necessary.
5. Equal-weight mean aggregation was consistently weaker than max-channel, by 5.21 percentage points on average.
6. Constituent retrieval and composition remain distinct: max-channel/same-channel/mean-channel retrieval accuracy differs, but the composition result does not track every retrieval difference.

## Limits

The event generator, fixed feature dimension, encoder family and supplied candidate-middle decoder remain unchanged. These are synthetic-world and codebook replications, not real-data validation or evidence of general relational reasoning. The full SOE state has 64 scalar values; slow-only and the finite-memory controls have 16. No efficiency claim follows.

## Gate decision

E01-A3 supports moving to **E01-B capacity and interference frontiers**. The primary memory comparison should be slow-only SOE (16 scalars) against 16-dimensional current-event, finite-window and full-history controls. The four-channel SOE should remain a larger-state diagnostic reference, not the primary comparator.
