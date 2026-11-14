# E01-B — Capacity and interference frontier, corrected run 0001

## Execution record

- **Status:** passed — 228 frontier cells, Python 3.10/3.12 unit-test jobs, two independent determinism replicas, deterministic comparison, and aggregate summary succeeded.
- **Corrected workflow run:** [43433259761](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43433259761)
- **Corrected experiment commit:** `d4a2c5c0d00b94034809d371c9346748b1f0bf64`
- **Frontier summary artifact:** `e01-b-frontier-summary`, ID `14043621651`, SHA-256 `06a5fcad6c1397132df14d3779c3d1d07a436e0c5a5772d5ad8d56cfc85fb95b`
- **Determinism artifact:** `e01-b-determinism-check`, ID `14040144215`
- 19 one-factor conditions × 6 memory arms × 2 worlds = **228 cells**.
- Each cell used 160 validation and 160 held-out test sequences. The fixed codebook seed was 9137.

## Frozen design

E01-B measured how memory-only relational support changes across five one-factor sweeps: entity count (4, 8, 16, 32), distinct-fact load (4, 8, 16, 32, 64), repeated distractor pulses (0, 4, 16, 32), temporal gap (short, medium, long), and composition depth (1, 2, 3).

The six memory arms were slow-only SOE (16 scalars), full four-channel SOE (64), current-event (16), window-2 (16), window-8 (16), and full-history sum (16). Thresholds were fitted on validation only. Each memory arm uses the same generator, queries and held-out sequence seeds within a condition/world.

## Corrected aggregate results

The following means are descriptive averages over the 19 one-factor condition summaries. Conditions reuse reference settings and must not be interpreted as independent samples or pooled population estimates.

| Memory arm | Mean composition accuracy | Mean constituent-fact retrieval |
|---|---:|---:|
| Slow-only SOE (16 scalars) | **52.83%** | 67.12% |
| Full four-channel SOE (64 scalars) | 52.86% | 67.71% |
| Full-history sum (16 scalars) | 50.63% | 67.99% |
| Window-8 sum (16 scalars) | 51.91% | 63.23% |
| Window-2 sum (16 scalars) | 50.39% | 57.05% |
| Current event (16 scalars) | 50.58% | 53.82% |

The four-channel bank and slow-only SOE are effectively tied on this descriptive mean, despite the fourfold state-size difference. This run does not show a material multiscale-SOE advantage. Fact retrieval remains higher than composition for most arms; that difference is consistent with a composition/readout bottleneck but is not, by itself, proof that all facts needed for each path were independently preserved.

## Condition-level composition accuracy

Values are means across the two synthetic worlds.

| Sweep condition | Slow SOE | Full SOE | Full history | Window-8 |
|---|---:|---:|---:|---:|
| Entity count 4 | 50.94% | 50.94% | 49.69% | 51.88% |
| Entity count 8 | 50.63% | 50.62% | 50.94% | 53.75% |
| Entity count 16 | 53.12% | 53.12% | 50.63% | 54.06% |
| Entity count 32 | 50.31% | 50.31% | 49.38% | 52.19% |
| Distinct facts 4 | 50.94% | 50.62% | 51.56% | 53.12% |
| Distinct facts 8 | 53.12% | 53.12% | 50.63% | 54.06% |
| Distinct facts 16 | 52.19% | 52.19% | 48.75% | 49.06% |
| Distinct facts 32 | 54.37% | 53.12% | 49.06% | 53.75% |
| Distinct facts 64 | 49.06% | 48.75% | 51.25% | 49.06% |
| Distractor pulses 0 | 54.69% | 58.44% | 55.62% | 50.62% |
| Distractor pulses 4 | 55.62% | 55.31% | 53.12% | 58.13% |
| Distractor pulses 16 | 52.19% | 52.19% | 48.75% | 49.06% |
| Distractor pulses 32 | 56.25% | 56.25% | 50.62% | 51.25% |
| Gap short | 50.63% | 49.69% | 48.75% | 49.06% |
| Gap medium | 52.19% | 52.19% | 48.75% | 49.06% |
| Gap long | 56.88% | 55.94% | 48.75% | 49.06% |
| Depth 1 | 57.19% | 57.50% | 56.56% | 55.94% |
| Depth 2 | 52.19% | 52.19% | 48.75% | 49.06% |
| Depth 3 | 51.25% | 51.88% | 50.31% | 54.06% |

## Determinism correction and validation

The pre-correction replicas differed in the previously problematic `entity_e4 / current / world 402` cell. Event records matched, but a sub-precision difference in the validation-fitted threshold flipped one held-out prediction.

The corrected implementation rounds support, edge and path scores to a shared 12-decimal grid before threshold fitting and held-out decisions. Threshold comparisons are inclusive and use that same grid. The correction is a numerical decision policy, not a probability-calibration step.

The fresh independent-worker audit completed with:
- `equivalent: true`;
- `difference_count: 0`;
- comparison tolerance (10^{-12}) absolute and relative;
- matching per-sequence predictions and summary metrics.

The corrected 228-cell matrix and its aggregate summary then completed successfully. This replaces the initial report's pre-correction averages and pending-validation note.

## Interpretation

1. **No demonstrated advantage from four SOE channels.** Slow-only and full SOE are 52.83% and 52.86% respectively, while full SOE uses 64 rather than 16 state scalars.
2. **Short-window/current controls remain weak on the aggregate.** This is consistent with E01-A's evidence that event history helps, but these descriptive means do not establish a general model ranking.
3. **The long-gap result favours decaying memory over the tested finite-history references in this particular generator.** Slow-only is 56.88%, full SOE 55.94%, full-history 48.75%, and window-8 49.06%. E01-C adds an important qualification: full-history can preserve more constituent-fact evidence under long gaps even when final composition accuracy is similar.
4. **Depth-3 composition remains weak.** All arms are near chance, and the larger candidate-space/path diagnostics in E01-C point to false-path competition.
5. **The sweeps are not pure causal axes in every region.** Above four entities, fixed-`R^{16}` codebooks use normalized random codewords rather than orthogonal vectors, so entity scale includes codebook crowding. Distractor effects are non-monotonic.

## Limits

Only two world seeds and one codebook seed were used. The across-condition means are descriptive, not independent pooled estimates. Full SOE is not state-dimension matched to the other arms. The task uses a fixed encoder and alternating-relation path decoder; it does not test relation discovery, general relational reasoning, real-world data, or Grassmannian geometry.

## Decision

E01-B is complete after the corrected determinism gate. E01-C's path-level diagnosis motivates E02: compare the current dense memory/readout path against an event-derived explicit relational graph, then test a graph-plus-temporal-memory hybrid. Ground-truth facts remain evaluator-only throughout E02.
