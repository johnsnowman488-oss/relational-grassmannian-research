# E01-C — Mechanism isolation, run 0001

## Execution record

- Status: **passed** — all 108 diagnostic cells, Python 3.10 and 3.12 unit tests, and paired-summary job succeeded.
- Workflow run: [43250297397](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43250297397)
- Experiment commit: \`21faa21ea725b3903c931687670d29695b946dd0\`
- Paired-summary artifact: \`e01-c-paired-summary\`, artifact ID \`13959311664\`
- Six conditions × two 16-scalar memory arms × three worlds × three codebook seeds = **108 cells**.
- Nine paired world/codebook replicates per condition and memory arm; 160 validation and 160 held-out test sequences per cell.
- Oracle gate: **passed**. Exact fact supports recovered every generated query label in every cell.

## Frozen diagnostic design

The experiment compared:
- \`slow_only\`: one SOE channel at decay rate 0.01;
- \`full_history\`: un-decayed sum of event vectors.

Both use 16 scalar state values.

Each case was evaluated with:
- \`observed\`: ordinary memory update;
- \`repeat_suppressed\`: later contributions from repeated typed facts were zeroed while event order and SOE elapsed-time updates were preserved;
- \`oracle_facts\`: memory supports were bypassed in favour of exact fact membership. This is a diagnostic upper bound, not an implementable model.

Thresholds were fitted on validation sequences separately for each variant. Test case seeds were paired across interventions, memory arms and codebook seeds.

## Composition accuracy

Mean held-out composition accuracy across the nine world/codebook replicates:

| Condition | Memory | Observed | Repeat-suppressed | Exact-fact oracle |
|---|---|---:|---:|---:|
| baseline E4, no repeats | Full history | 74.37% | 74.37% | 100% |
| baseline E4, no repeats | Slow-only SOE | 74.31% | 74.31% | 100% |
| repeat E4, 32 repeats | Full history | 51.46% | 74.37% | 100% |
| repeat E4, 32 repeats | Slow-only SOE | 52.99% | 82.78% | 100% |
| candidate E16 | Full history | 51.60% | 56.04% | 100% |
| candidate E16 | Slow-only SOE | 52.29% | 58.75% | 100% |
| fact load E16, 64 facts | Full history | 50.90% | 50.07% | 100% |
| fact load E16, 64 facts | Slow-only SOE | 50.28% | 51.60% | 100% |
| depth 3, E16 | Full history | 50.00% | 50.83% | 100% |
| depth 3, E16 | Slow-only SOE | 51.39% | 52.22% | 100% |
| long gaps, E16 | Full history | 51.60% | 56.04% | 100% |
| long gaps, E16 | Slow-only SOE | 51.11% | 53.47% | 100% |

### Paired repeat-suppression effects

Difference is repeat-suppressed minus observed composition accuracy. Intervals are 95% bootstrap intervals over the nine paired world/codebook replicates.

| Condition | Full history | Slow-only SOE |
|---|---:|---:|
| baseline E4 | 0.00 pp [0.00, 0.00] | 0.00 pp [0.00, 0.00] |
| repeat E4 | **+22.92 pp [+20.00, +25.56]** | **+29.79 pp [+26.32, +33.75]** |
| candidate E16 | **+4.44 pp [+1.81, +7.01]** | **+6.46 pp [+3.40, +9.65]** |
| fact load E16 | −0.83 pp [−1.81, +0.14] | +1.32 pp [−0.35, +2.92] |
| depth 3, E16 | +0.83 pp [−0.28, +2.08] | +0.83 pp [−1.39, +3.06] |
| long gaps, E16 | **+4.44 pp [+1.81, +7.01]** | +2.36 pp [−0.49, +5.28] |

The no-repeat baseline is a useful negative control: repeat suppression changes nothing there. Under explicit repeated-pulse stress, the gain is large and consistent. At high distinct-fact load and depth 3, however, duplicate suppression alone does not materially recover composition accuracy.

## What the path diagnostics establish

### 1. Repeated pulses are a real, causal source of interference

For the E4 repeated-pulse condition, slow-only SOE changes as follows:
- composition accuracy: **52.99% → 82.78%**;
- positive queries with at least one fully retrieved true path: **13.33% → 83.75%**;
- positive queries where the highest-scoring path is true: **24.86% → 90.97%**;
- mean best false-path score on negative queries: **0.633 → 0.028**.

The corresponding full-history composition gain is also large: 51.46% → 74.37%. The intervention has no effect in the no-repeat baseline. This is strong synthetic evidence that repeated event pulses can inflate or distort the memory support state and cause false relational paths.

### 2. Codebook/support interference and path competition dominate at larger entity counts

At E16 with 16 facts and 16 distractor pulses, the slow-only observed condition has:
- constituent-fact accuracy: **66.17%**;
- at least one fully supported true path in only **23.89%** of positive queries;
- highest-scoring path is true in only **15.14%** of positive queries;
- mean best false-path score on negative queries: **0.813**.

Repeat suppression improves the last three path diagnostics (true path detected 55.14%; best path true 43.19%; false-path score 0.327), but composition rises only from 52.29% to 58.75%.

This indicates that repeated pulses contribute, but are not the whole problem. The E16 codebooks are non-orthogonal normalized vectors in fixed \`R^16\`; unrelated typed facts can therefore have positive support. The candidate path search can combine such spurious edge supports into high-scoring false paths.

### 3. Three-hop composition exposes severe false-path accumulation

At E16 and depth 3 there are **256 candidate paths per query**. In the observed condition:
- the best-scoring path is graph-true in only **1.2%** of positive queries for slow-only SOE and **1.0%** for full history;
- the median rank of the best true path is approximately **29**;
- the mean best false-path score on negative queries is **0.917** for slow-only and **0.998** for full history.

Repeat suppression improves the probability that a true path has sufficiently supported edges, but the best-scoring path is still true in only 3.6% (slow-only) or 2.6% (full-history) of positive queries. Composition accuracy remains near chance.

The current max-product path readout is therefore highly vulnerable to false edge supports as candidate paths multiply. Importantly, exact-fact oracle supports give 100% accuracy and rank the true path first. Thus the enumerator can solve the generated task when its edges are correct; the failure is in the noisy supports and their amplification through path selection, rather than an unavoidable impossibility of the path query itself.

### 4. Slow-only SOE loses persistent facts at long gaps

In the E16 long-gap condition, slow-only SOE is lower than full history by:
- **8.15 pp** in constituent retrieval (95% paired bootstrap interval [−8.54, −7.72]);
- **15.69 pp** in true-path detection ([−20.42, −10.97]).

The composition-accuracy difference is only −0.49 pp ([−2.43, +1.46]) and is not distinguishable in this run. The fact/path diagnostics are more revealing than the final binary accuracy: with these long gaps and still-valid facts, a single decaying channel loses support. The task has no fact-expiry semantics, so this does not imply decay is generally wrong; it shows that this decay rate alone is insufficient for persistent relational facts under this protocol.

## Interpretation and decision

The evidence supports three distinct mechanisms:

1. **Representation/support loss is the broad bottleneck.** The exact-fact oracle improves composition by roughly 26 pp even in the low-load E4 baseline, and by roughly 48–50 pp across the E16 conditions. It also restores all fact probes and path labels. The observed memory state does not preserve clean enough edge supports.
2. **Repeated-event accumulation is an additional, condition-specific mechanism.** Suppressing duplicate pulses has a large effect in E4 repeated-pulse stress and a smaller effect in E16 candidate/long-gap cases. It is not sufficient under high distinct-fact load or depth-3 path competition.
3. **The path readout amplifies noisy edge supports.** False path scores become very high as candidate count and depth increase. The exact oracle demonstrates that the task's path enumerator works with correct edge information, but the current max-product scoring rule is vulnerable to spurious supports.

The temporal memory comparison is secondary: slow-only SOE and full-history produce similar final composition accuracy in most conditions, while full-history preserves fact/path evidence better at long gaps. Adding more SOE channels is not supported as the immediate remedy by E01-A2/A3 or this experiment.

## Recommended next intervention

Before introducing Grassmannian geometry, implement a matched **non-geometric relational-graph/readout baseline**:

1. Calibrate edge support against absent-fact probes and inspect codebook Gram/cross-talk as entity count increases.
2. Compare the existing dense superposition readout with explicit sparse fact/edge storage and graph traversal.
3. Test thresholded or top-\`k\` edge pruning and calibrated path scoring against the current max-product path rule, preserving the same cases and memory budget where possible.
4. Compare a repeated-fact idempotent/saturating update against ordinary accumulation; keep occurrence counts as a separate signal if repetition itself carries meaning.
5. Add a persistent factual store plus a decaying episodic trace before increasing the number of SOE channels.

A coupled Grassmannian representation remains a legitimate hypothesis for preserving relational organisation under interference. E01-C does not establish that it is necessary or superior. The next fair test is to compare it against the explicit non-geometric graph baseline under matched information exposure, memory and readout capacity.

## Limits

All results are from the frozen synthetic generator, 16-dimensional feature space, fixed decoder family, and nine world/codebook replicates. E01-C does not test relation discovery, open-ended reasoning, real data, or any Grassmannian model. Bootstrap intervals over nine synthetic replicates describe this designed campaign; they are not evidence of external generalisation.
