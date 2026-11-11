# E01-A3 — Independent-world and codebook replication

## Purpose

E01-A3 tests whether the E01-A2 diagnostic pattern survives changes in both synthetic worlds and the fixed relation-1 codebook. It does not increase task complexity; that is reserved for E01-B after replication.

## Selected configurations

The A2 result selected six configurations:

1. `full_max`: full four-channel SOE with the original independent max-channel readout.
2. `slow_only_max`: channel 0 only (decay 0.01), max readout.
3. `drop_slow_max`: remove channel 0, max readout.
4. `drop_channel2_max`: remove channel 2, max readout.
5. `full_same`: full SOE, same-channel composition.
6. `full_mean`: full SOE, fixed equal-weight channel aggregation.

These preserve the main baseline, the slow-only challenger, the slow-channel necessity control, the channel-2 redundancy check, and the two readout controls.

## Replication design

- Synthetic-world seeds: 101, 202, 303.
- Codebook seeds: 9137, 27183, 65537.
- Six configurations × three worlds × three codebooks = **54 independent CI cells**.
- Each cell uses 160 validation and 160 held-out test sequences.
- All configurations share the same test sequences within each world/codebook pair.
- Thresholds are fitted on validation data only.
- Every cell stores per-sequence composition predictions, all candidate-fact supports, channel supports, and event/query evidence.

Codebook seed 9137 reproduces the original E01-A2 codebook; the two additional seeds vary the relation-1 orthogonal basis. Relation-0 retains the standard basis. World seed ranges are disjoint from E01-A2 and from one another.

## Analysis

The summary aggregates nine world/codebook replicate cells per configuration. Primary uncertainty is estimated from paired replicate-level accuracy differences (bootstrap over the nine paired cells), alongside the number of replicates improved/worsened/tied and an exact sign test. Pooled sequence-level McNemar results are reported as secondary because the same synthetic world is reused across codebook seeds.

Constituent retrieval is summarized alongside composition, allowing us to check whether any change originates at fact retrieval or at composition.

## Execution

The dedicated GitHub Actions workflow runs:
- Python 3.10 and 3.12 unit suites;
- 54 independent matrix cells, bounded to nine concurrent experiment jobs;
- one summary job after all 54 cells succeed.

Each cell uploads a JSON evidence artifact; the summary job downloads all 54 and produces a paired replication summary.

## Interpretation boundaries

The event generator, feature dimension, task, fixed encoder family, and supplied candidate-middle decoder remain unchanged. This is replication across random worlds and codebooks, not validation on real data and not evidence of relation discovery or general-purpose reasoning.

## Gate to E01-B

E01-B may begin only after all 54 cells and the paired summary succeed and the A2 patterns are reviewed for consistency. If slow-channel dependence or readout behavior is not reproducible, E01-B should be redesigned around the observed failure rather than proceed as originally imagined.
