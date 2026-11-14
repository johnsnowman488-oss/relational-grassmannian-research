# E02 — Event-derived graph, dense memory and temporal hybrid

**Protocol version:** E02-v0.1  
**Status:** Frozen for CI execution, subject to correction only through a documented protocol revision  
**Prerequisite:** E01-A/A2/A3/B/C integrated into main

## Research question

Does explicit relational storage derived from observed events preserve and compose relational facts more reliably than the E01 dense event-memory baseline? When observations are missing or spurious, does adding a temporal memory trace to the explicit graph recover useful evidence, or does it reintroduce false paths?

E02 is a non-geometric baseline study. It does not test Grassmannian geometry, open-ended relation discovery, or general-purpose reasoning.

## E02-A — Frozen data and model interface

### Model-facing contract

The versioned e02-observed-input-v1 payload contains only:

- case_id and entity_count;
- ordered observed_events, each with an event index, typed relation ID, subject ID, object ID and elapsed-time increment dt;
- a query containing subject, object, depth and the declared alternating relation pattern.

The query relation pattern is fixed by the E01-C generator (0, 1, 0, ...). It is task specification, not a hidden answer.

The model-facing object does **not** contain labels, latent fact sets, planted paths, evaluator truth, corruption masks or corruption flags. Graph construction, memory updates and prediction functions accept this model input only. The scorer holds a separate evaluator object. Validation truth may be used only by the declared validation-threshold fitting step; held-out test truth is used only after prediction outputs have been produced.

Every model input is canonically serialized and assigned a SHA-256 digest. Seeds, condition parameters, input hashes and output configuration are recorded in each cell artifact.

### Graph construction

The explicit graph is a directed, typed, event-derived graph. Each observed event creates an append-only event record. The traversal index deduplicates topology by (relation, subject, object) but retains occurrence count and observed timestamps for every unique edge. Repeated observations therefore do not create new logical edges, but their frequency and timing remain measurable.

No graph edge may be created from evaluator facts or the planted path. The graph query performs exact typed path traversal over observed edges using the query's declared relation sequence. It returns a path witness and deterministic edge-examination count.

### Dense memory baseline

The baseline reuses the E01-C encoder and frozen decision precision. It evaluates both 16-scalar memory arms:

- slow_only: one SOE channel with decay rate 0.01;
- full_history: un-decayed sum of event vectors.

Composition scores are maximum products over the same fixed candidate-path space. Each arm's threshold is fit on validation cases only and then held fixed for held-out test cases.

### Frozen conditions and seeds

E02 uses the exact six E01-C conditions and the same generator parameters:

| Condition | Entities | Distinct facts | Extra distractor pulses | Path depth | Gap |
|---|---:|---:|---:|---:|---|
| baseline_e4 | 4 | 8 | 0 | 2 | medium |
| repeat_e4 | 4 | 8 | 32 | 2 | medium |
| candidate_e16 | 16 | 16 | 16 | 2 | medium |
| factload_e16 | 16 | 64 | 16 | 2 | medium |
| depth3_e16 | 16 | 32 | 16 | 3 | medium |
| longgap_e16 | 16 | 16 | 16 | 2 | long |

World seeds: 501, 502, 503. Codebook seeds: 9137, 27183, 65537. Each cell has 160 validation and 160 held-out test sequences. The E01-C sequence seed ranges are reused: validation begins at 7,000,000 + world_seed × 10,000; test begins at 8,000,000 + world_seed × 10,000. Thus cases and queries are paired with E01-C, while graph, memory and hybrid arms receive the same event/query payload within each E02 cell.

### Storage and compute accounting

Report separately:

- common serialized event/query input bytes;
- explicit graph state bytes, including edge occurrence counts and timestamps;
- dense memory state bytes;
- hybrid graph-plus-memory state bytes;
- unique observed edges and event count;
- deterministic graph traversal edge examinations and dense path-edge score evaluations.

The graph is **not** treated as information-capacity matched to a 16-scalar trace. No cross-run speed claim is based on noisy wall-clock timing.

## E02-B — Clean graph versus dense memory

For every condition × world × codebook cell, evaluate:

1. observed-event graph;
2. dense slow_only memory;
3. dense full_history memory.

All arms receive the identical clean event stream and query. Only memory thresholds are calibrated on validation labels; graph traversal returns whether an observed path exists. Compare held-out accuracy, balanced accuracy, precision, recall, false-positive rate, path witness correctness, storage and query work.

The graph's clean result is an explicit observation-retrieval reference: all generated facts are represented in the event stream. A perfect graph score must not be described as relation discovery or general reasoning.

## E02-C — Hybrid temporal memory and controlled corruption

For the same paired cases, apply four deterministic observation profiles:

- clean: no event intervention;
- missing_10: remove all occurrences of a seeded 10% sample of unique true edges;
- spurious_10: add seeded events for absent relation triples, targeting 10% of the original unique-fact count;
- mixed_10: apply both interventions.

Missing and spurious masks are generated by the evaluator. They are never included in the model input. Spurious events have the same visible schema as ordinary events. Original event order is retained; inserted events are placed at deterministic seeded positions with time increments drawn from the condition's frozen gap profile.

For every profile compare graph-only, memory-only (slow_only, full_history) and hybrid graph-plus-memory (slow_only, full_history). In a hybrid edge score, an observed graph edge has support 1; where the graph has no edge, the temporal memory support may contribute. The hybrid cannot see which events were corrupted or which facts were removed.

Each profile receives its own validation-only thresholds for the memory and hybrid score. The test split is never used for calibration. Report the same predictive and cost metrics as E02-B, along with applied corruption counts.

## Execution and decision rules

One GitHub Actions workflow orchestrates all stages:

1. E02-A schema/leakage tests and Python 3.10/3.12 test matrix must pass.
2. E02-B's 54 paired cells and E02-C's 54 paired cells then run concurrently.
3. A final aggregation job requires both matrices and writes a combined JSON summary and Markdown report.

The campaign is interpreted by paired world/codebook cell, not by treating all sequences as independent worlds. Report means and dispersion across the nine paired cells per condition/profile. A difference is descriptive synthetic evidence, not a population-level confidence interval.

A hybrid that helps under missing observations but hurts under spurious observations indicates a recovery/false-path trade-off, not unconditional superiority. A hybrid that does not improve over graph-only does not justify adding temporal state for this task. Results must be interpreted alongside state size and operation counts.

## Reproducibility and audit requirements

- Stable seeds and canonical SHA-256 input manifests are mandatory.
- The same test inputs are used for all architectures within a cell/profile.
- No test labels or truth are used by model functions or threshold calibration.
- Corruption audit and prediction input are separate objects.
- Every CI cell uploads a machine-readable JSON artifact.
- The final report must show expected and observed cell counts; missing cells fail aggregation.
- No E02 result constitutes evidence for a Grassmannian advantage. E03 is considered only after E02's graph/memory trade-offs are reviewed.
