# E01-B — Initial capacity and interference frontier report

## Execution status

The dedicated GitHub Actions workflow completed the 228-cell matrix:

- 19 one-factor conditions
- 6 memory arms
- 2 synthetic-world seeds (401, 402)
- 160 validation sequences and 160 held-out test sequences per cell
- 228 cell artifacts aggregated by the final summary job

Two workflow executions were observed: run **43062046129** and run **43062584628**. Both produced a 228-cell summary artifact; the Python 3.10 and 3.12 unit-test jobs passed, and no failures appeared in the returned job listings. The later summary is the reference used below. The duplicate summaries differed in one current-event/entity-E4 value by 0.0125, so this small run-to-run discrepancy is retained as a reproducibility warning rather than silently averaged away.

The summary artifacts are available from the corresponding GitHub Actions runs. PR #6 remains open and unmerged.

## Main results

Mean composition accuracy across the 19 one-factor configurations (descriptive average; configurations share reference cells and are not independent):

| Memory arm | Mean composition accuracy | Mean constituent-fact retrieval |
|---|---:|---:|
| Slow-only SOE (16 scalars) | 53.14% | 67.17% |
| Full four-channel SOE (64 scalars) | 53.09% | 67.77% |
| Full-history sum (16 scalars) | 50.81% | 68.14% |
| Window-8 sum (16 scalars) | 52.01% | 63.22% |
| Window-2 sum (16 scalars) | 50.41% | 57.04% |
| Current event (16 scalars) | 50.59% | 53.82% |

These are not pooled independent observations and must not be interpreted as a single population estimate. They summarize the repeated one-factor configurations.

The full four-channel SOE does not show a material average composition advantage over the 16-scalar slow-only SOE in this frontier. Its 64-scalar state is four times larger, and its mean composition accuracy is effectively the same (53.09% vs 53.14%). The state-dimension-matched slow-only SOE is descriptively stronger than the current, window-2, window-8 and un-decayed full-history controls on this repeated-condition average, but the margin is small and varies by condition. No broad inferential claim follows from two worlds.

## Condition-level frontier

Each entry below is composition accuracy for slow-only SOE / full four-channel SOE / full-history / window-8. All values are means across the two worlds.

| Sweep | Condition | Slow SOE | Full SOE | Full history | Window-8 |
|---|---|---:|---:|---:|---:|
| Entities | 4 | 56.9% | 55.3% | 53.1% | 53.8% |
| Entities | 8 | 50.6% | 50.6% | 50.9% | 53.7% |
| Entities | 16 | 53.1% | 53.1% | 50.6% | 54.1% |
| Entities | 32 | 50.3% | 50.3% | 49.4% | 52.2% |
| Distinct facts | 4 | 50.9% | 50.6% | 51.6% | 53.1% |
| Distinct facts | 8 | 53.1% | 53.1% | 50.6% | 54.1% |
| Distinct facts | 16 | 52.2% | 52.2% | 48.8% | 49.1% |
| Distinct facts | 32 | 54.4% | 53.1% | 49.1% | 53.7% |
| Distinct facts | 64 | 49.1% | 48.7% | 51.2% | 49.1% |
| Distractor pulses | 0 | 54.7% | 58.4% | 55.6% | 50.6% |
| Distractor pulses | 4 | 55.6% | 55.3% | 53.1% | 58.1% |
| Distractor pulses | 16 | 52.2% | 52.2% | 48.8% | 49.1% |
| Distractor pulses | 32 | 56.2% | 56.2% | 50.6% | 51.2% |
| Gaps | Short | 50.6% | 49.7% | 48.8% | 49.1% |
| Gaps | Medium | 52.2% | 52.2% | 48.8% | 49.1% |
| Gaps | Long | 56.9% | 55.9% | 48.8% | 49.1% |
| Composition depth | 1 hop | 57.2% | 57.5% | 56.6% | 55.9% |
| Composition depth | 2 hops | 52.2% | 52.2% | 48.8% | 49.1% |
| Composition depth | 3 hops | 51.2% | 51.9% | 50.3% | 54.1% |

## Interpretation

1. **Composition remains the limiting stage.** Across the repeated configurations, constituent-fact retrieval averages roughly 54–78% depending on condition and arm, while composed-query accuracy is mostly 49–57%. This gap suggests that retaining or detecting individual facts is easier than using them to answer the path query. It is consistent with a composition/readout bottleneck, but does not prove that memory itself is sufficient: the constituent probe and path task are not identical.
2. **No demonstrated multiscale-SOE advantage.** The 64-scalar four-channel SOE and 16-scalar slow-only SOE are nearly tied on the descriptive mean. More channels do not presently justify their extra state cost.
3. **No robust long-gap win for the full SOE bank.** Slow-only SOE reaches 56.9% at the long-gap condition; full SOE reaches 55.9%. Finite-window and full-history controls are weaker in that condition, but the result is modest and based on two worlds.
4. **Entity scale is confounded with codebook crowding by design.** At more than four entities, codewords are random normalized vectors in fixed R^16. The entity sweep therefore combines a larger candidate space with increased codebook interference; it is not a pure search-size experiment.
5. **Distractor effects are not monotonic.** Slow-only SOE accuracy is 54.7%, 55.6%, 52.2%, and 56.2% at 0, 4, 16, and 32 additional pulses. Do not infer a monotonic capacity curve from these values.
6. **Replication remains shallow.** Two synthetic worlds are useful for checking direction consistency but insufficient to establish population-level generalisation. The duplicate workflow summaries also show a small one-cell discrepancy requiring a determinism audit before publication-grade use.

## Limitations and audit flags

- The 19 configurations reuse reference settings across different sweeps. The overall means above are descriptive summaries, not independent-condition estimates.
- Only two world seeds and one codebook seed (9137) were used in E01-B. A3's multiple-codebook-seed replication is not repeated across this frontier.
- Full SOE uses 64 scalars; the other five arms use 16. The primary comparison is state-dimension-matched, not equal effective information capacity.
- The readout takes the maximum support across channels independently for each path edge. Cross-channel composition remains a property of the chosen decoder, not evidence of a mechanism learned by SOE.
- The fixed 16-dimensional codebook becomes non-orthogonal above four entities.
- The task uses a fixed event encoder and a hand-specified alternating-relation path decoder. It does not test relation discovery or general-purpose reasoning.

## Decision

E01-B has completed its initial CI frontier. **Do not expand directly to a larger factorial sweep.** The strongest next action is a targeted diagnostic follow-up on the composition/readout gap and run-to-run determinism:

- verify exact per-case seed, event-order and support reproducibility across duplicate runs;
- inspect edge-support calibration and false-positive path accumulation as candidate intermediates increase;
- compare the current max-channel path score with the A2-selected readout controls on a small set of frontier corners;
- then add more world and codebook seeds to the most informative corners (E=4/16/32, facts=4/16/64, distractors=0/16/32, gaps=short/long, depth=1/2/3).

No conclusion about the superiority of SOE, explicit relational structures, or Grassmannian geometry is warranted from this frontier alone.
