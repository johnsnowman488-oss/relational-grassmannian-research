# E01-A2 — Diagnostic audit

## Purpose

E01-A2 audits the mechanism behind E01-A rather than expanding task difficulty. It uses the same fixed synthetic task family, fixed codebook seed, and disjoint validation/test seed ranges. The original E01-A archive remains immutable.

## Diagnostic dimensions

### Memory-channel controls

- `full`: all four SOE channels (rates 0.01, 0.05, 0.2, 0.8).
- `only_0` … `only_3`: one channel at a time.
- `drop_0` … `drop_3`: leave one channel out.

The channel controls identify whether a particular timescale is carrying the observed signal. They are not capacity-matched comparisons: channel count and state dimension differ by construction.

### Readout controls

- `max_channel`: each candidate fact selects its best channel independently; the two fact supports are then composed. This reproduces the E01-A rule.
- `same_channel`: the two edges in a candidate path must be supported by the same channel.
- `mean_channel`: equal-weight channel averaging is applied before composition; there is no per-fact channel selection.

For a single-channel ablation these readouts are mathematically equivalent. Those repeated cells are retained in the matrix for a uniform artifact schema, not counted as independent evidence.

## Evidence saved

Every test sequence artifact stores:
- seed, label, query, ordered event list and elapsed gaps;
- all possible typed non-self candidate facts, their truth labels, each channel's support and the readout support;
- composed query score and channel-state norms.

Constituent fact threshold and composed-query threshold are each selected using validation data only. Test data is not used to select thresholds.

## Metrics

Constituent fact retrieval reports accuracy, precision, recall and confusion counts over the candidate-fact set. Composition reports exact accuracy, Wilson 95% interval, balanced accuracy and raw bounded-support Brier score. The Brier-like score is descriptive and is not a calibrated probability.

The artifacts enable paired per-sequence comparisons because each matrix cell uses the same validation/test sequence seeds. A later analysis should use paired bootstrap intervals and McNemar tests where appropriate; overlapping Wilson intervals are not a paired test.

## Interpretation boundaries

The event encoder and codebooks remain fixed. The decoder enumerates candidate intermediate entities; it is not discovering relations or learning a general inference procedure. A constituent retrieval failure points to representation/readout limitations before composition is considered. A retrieval success with composition failure is evidence of a distinct composition bottleneck.

The four-channel SOE state has 64 scalar values. Single-channel ablations have 16 and leave-one-out configurations have 48. The finite-window/full-history baselines in E01-A are 16-dimensional. This audit diagnoses channel/readout behavior but does not establish memory efficiency or capacity superiority. A separate capacity-matched study is required before making those claims.

## Execution

GitHub Actions runs the 9 memory configurations × 3 readouts as 27 independent matrix cells with fail-fast disabled and bounded parallelism. Each cell uploads one immutable JSON artifact. Unit tests run separately on Python 3.10 and 3.12.

## Gate to E01-A3 and E01-B

Review the full per-sequence artifacts first. Select only configurations whose constituent retrieval and composition behavior can be interpreted. E01-A3 then replicates selected configurations across independent worlds and codebook seeds. E01-B remains blocked until diagnostic interpretation and replication are complete.
