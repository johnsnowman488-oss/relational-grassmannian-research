# E01-C — Mechanism isolation for relational composition

## Purpose

E01-C identifies why composed queries fail after the E01-A2 diagnostic audit,
E01-A3 replication and E01-B capacity/interference frontier. It does not add
Grassmannian geometry or run another broad capacity sweep.

The competing explanations are:
1. repeated distractor pulses accumulate and corrupt useful memory supports;
2. event representation, memory retention or support readout loses information;
3. valid relational paths remain detectable, but false candidate paths dominate
   the composition score as candidate count or path depth increases.

## Frozen conditions

| Condition | Entities | Facts | Repeated distractors | Depth | Gap | Diagnostic focus |
|---|---:|---:|---:|---:|---|---|
| baseline_e4 | 4 | 8 | 0 | 2 | medium | Low-interference reference |
| repeat_e4 | 4 | 8 | 32 | 2 | medium | Repeated-pulse stress |
| candidate_e16 | 16 | 16 | 16 | 2 | medium | Candidate-space growth and codebook crowding |
| factload_e16 | 16 | 64 | 16 | 2 | medium | High distinct-fact load |
| depth3_e16 | 16 | 32 | 16 | 3 | medium | Multi-hop path competition |
| longgap_e16 | 16 | 16 | 16 | 2 | long | Temporal persistence |

Feature dimension remains 16. Four-entity codebooks are orthogonal; larger
entity conditions use normalized non-orthogonal codewords in the same fixed
feature space. Thus the entity condition combines candidate-space growth and
codebook interference, as it did in E01-B.

## Memory arms and interventions

Two 16-scalar memory arms are compared:
- slow_only: one SOE channel with decay rate 0.01;
- full_history: un-decayed sum of event vectors.

Each case is tested in three paired variants:
- observed: ordinary event encoding and memory update;
- repeat_suppressed: only the first occurrence of each typed fact contributes
  a vector; later duplicates contribute zero, while original event order and
  elapsed-time updates are retained;
- oracle_facts: exact ground-truth fact membership replaces memory supports.
  This is an upper-bound diagnostic, not a deployable model.

Each variant selects its fact and composition thresholds on validation data
only. The exact same generated cases are reused across variants and memory arms.

## Replication and execution

- Three world seeds: 501, 502, 503.
- Three codebook seeds: 9137, 27183, 65537.
- 160 validation and 160 held-out test sequences per cell.
- Six conditions × two memory arms × three worlds × three codebooks = 108 cells.

## Measurements

- Balanced constituent-fact accuracy, precision and recall.
- Fraction of positive queries with at least one true path whose every edge is
  above the validation-fitted constituent threshold.
- Best true-path support and best false-path support.
- Whether the highest-scoring candidate path is graph-true.
- Rank of the best true path among candidate paths.
- False-path activation rate on negative queries.
- Paired changes under repeat suppression and oracle fact support.

All graph-true paths count as valid for positive queries; the generator's planted
path is not treated as the only valid path.

## Interpretation rules

- Repeat suppression improves retrieval and composition: repeated-event
  accumulation is a credible memory-interference mechanism.
- Oracle facts improve sharply but repeat suppression does not: event encoding,
  representation, retention or support readout is the more likely bottleneck.
- True paths are supported but false paths score higher, or negative queries
  activate false paths: prioritise composition/readout or candidate-path control.
- Slow-only and full-history differ consistently: temporal memory/update choice
  contributes, but this is not evidence for geometry.
- Oracle facts fail the exact-label gate: stop and repair the generator/path
  evaluator before interpreting architecture results.

E01-C determines which mechanism deserves the next intervention. It does not
establish a Grassmannian advantage. An explicit non-geometric graph baseline
should be compared before Grassmannian structure is considered necessary.
