# E02 — Explicit relational graph versus temporal memory

## Research question

Does an explicit, event-derived relational graph improve constituent-fact retrieval and multi-hop composition over the E01 temporal-memory readout, and does a hybrid graph-plus-temporal-memory system add value beyond the graph alone?

E02 is a non-geometric control. No Grassmannian representation, learned embedding, or new adaptive memory is introduced. E02 results are a prerequisite for deciding whether geometric structure is warranted.

## Stages and dependency

1. **E02-A — protocol and data contract.** Freeze event ingestion, graph semantics, leakage boundaries, paired splits, metrics, and reproducibility. This stage must pass before either model comparison runs.
2. **E02-B — clean architecture comparison.** Compare the E01 memory-only baseline against an observed-event graph on the six frozen E01-C conditions. Use identical generated cases and paired world/codebook seeds.
3. **E02-C — hybrid and corruption study.** Compare graph-only with graph-plus-temporal-memory, then repeat under separately controlled missing-event and spurious-event corruption. Do not mix clean and corrupted outcomes in one aggregate.

E02-B and E02-C may execute concurrently after E02-A passes. Both must use the same frozen event interface and case manifest.

## Frozen E01-C condition set

| Condition | Entities | Facts | Repeated distractors | Path depth | Gap |
|---|---:|---:|---:|---:|---|
| baseline_e4 | 4 | 8 | 0 | 2 | medium |
| repeat_e4 | 4 | 8 | 32 | 2 | medium |
| candidate_e16 | 16 | 16 | 16 | 2 | medium |
| factload_e16 | 16 | 64 | 16 | 2 | medium |
| depth3_e16 | 16 | 32 | 16 | 3 | medium |
| longgap_e16 | 16 | 16 | 16 | 2 | long |

Feature dimension remains 16 in the inherited memory baseline. E02 must not silently change these condition definitions. Reuse the E01-C world seeds (501, 502, 503), codebook seeds (9137, 27183, 65537), and the validation/test separation (160 validation and 160 held-out test sequences per cell) unless a documented feasibility issue requires a protocol amendment before results are examined.

## E02-A: event and graph contract

The graph builder receives **only an ordered observed-event stream**. Each event has:
- `relation`: non-negative integer relation type;
- `subject`: non-negative integer entity identifier;
- `object`: non-negative integer entity identifier;
- `dt`: finite, non-negative elapsed time since the preceding event.

The graph builder does not accept a Case, fact set, query label, planted path, validation/test designation, corruption mask, or evaluator result. It must not import the E01 case generator or inspect hidden truth. The caller supplies the event sequence and nothing else.

Graph semantics:
- Directed, typed edge identity is the tuple `(relation, subject, object)`.
- Repeated observations update an edge's count and first/last observed time; they do not create duplicate edge identities.
- Relation types remain distinct: `(r0, a, b)` is not `(r1, a, b)`.
- Event order is retained through cumulative elapsed time and event indices.
- No transitive closure, inferred edge, planted-path insertion, or label-conditioned edge is permitted in E02-A.
- An edge exists in the graph if and only if at least one matching event was observed by the builder.

A graph snapshot is derived data, not ground truth. The evaluator alone retains the generator's latent fact set and query label.

## Leakage controls

The following are evaluator-only and must never enter graph construction, model fitting, or architecture-specific feature generation:
- latent `Case.facts` / complete ground-truth fact membership;
- `Case.label`, planted path, or query answer;
- held-out labels or any test-derived threshold;
- corruption masks and the identities of events selected for deletion/insertion;
- evaluator path lists, oracle facts, or post-hoc diagnosis.

The query subject/object and requested relation sequence are allowed at query time because they define the question, not its answer. Thresholds, if needed by a model arm, are fitted on validation data only and frozen before held-out evaluation.

The graph ingestion API is intentionally narrower than the experiment case object. Tests must demonstrate that graph state depends only on the event sequence, including when unrelated evaluator metadata exists outside the builder call.

## Architecture arms

- **Memory-only:** E01-C's `slow_only` and `full_history` memory/readout arms, unchanged.
- **Graph-only:** unique observed typed edges, with edge counts and temporal metadata available to the graph query procedure. No dense memory state is supplied.
- **Hybrid:** the same graph plus a temporal memory state built from the same observed event sequence. The graph and memory receive identical events; no additional labels or facts are available.

Do not describe graph and memory as capacity-matched. Report each arm's stored information and resource use explicitly.

## Paired execution and reporting

For each condition, pair model arms on identical generated validation and held-out cases, world seeds, and codebook seeds. Preserve per-sequence evidence and a machine-readable manifest with code revision, Python/NumPy versions, condition, seeds, sample counts, and hashes.

Report at minimum:
- constituent-fact retrieval: accuracy, precision, recall, balanced accuracy;
- composition: accuracy, precision, recall, balanced accuracy;
- positive-query true-path recovery and best true/false path support where defined;
- false-path activation on negative queries;
- graph nodes, unique typed edges, total observed events, duplicate-event count;
- event-log bytes, graph serialization bytes, memory-state scalar count/bytes;
- query operations (edge probes / candidate paths), and wall-clock latency as descriptive measurements.

Storage comparisons must state what each arm retains. A fixed 16-scalar memory is not an information-equivalent baseline to an event log or graph.

## E02-C corruption protocol

Clean results are reported separately and remain the primary architecture comparison. Corruption is applied only to the observed stream supplied to all applicable arms:
- **missing events:** remove a deterministic, seeded fraction of event observations;
- **spurious events:** insert deterministic, seeded events drawn from the legal relation/entity domain but absent from the original observed sequence.

Use predeclared rates and seeds, preserve an evaluator-side corruption manifest, and never pass that manifest to model code. Graph-only and hybrid receive exactly the same corrupted stream. The memory-only reference may be included as a robustness comparator, but E02-C's principal paired contrast is hybrid versus graph-only.

## Interpretation and decision gates

- A graph advantage is evidence for explicit relational storage on these synthetic tasks, not general reasoning or universal superiority.
- A hybrid advantage over graph-only is evidence that the chosen temporal-memory component adds value under the tested conditions; it is not evidence for Grassmannian geometry.
- If graph-only matches or exceeds hybrid, do not add temporal memory to the graph without a separately motivated test.
- If hybrid helps only under missing observations or temporal gaps, report that interaction rather than averaging it away.
- If the graph's apparent advantage is explained by greater retained information or query-time access to exact edge identity, report the cost and information asymmetry explicitly.
- No E02 result alone establishes a Grassmannian advantage.

## E02-A acceptance checklist

- [ ] Event-only graph builder and typed-edge invariants implemented.
- [ ] Duplicate observations update counts and temporal metadata deterministically.
- [ ] Tests cover relation separation, directionality, event ordering, invalid inputs, and evaluator-data isolation.
- [ ] Six E01-C conditions and seeds are frozen and cross-checked against `e01_c.py`.
- [ ] Validation/test boundaries and corruption manifests are evaluator-owned.
- [ ] E02-A tests pass on Python 3.10 and 3.12.
