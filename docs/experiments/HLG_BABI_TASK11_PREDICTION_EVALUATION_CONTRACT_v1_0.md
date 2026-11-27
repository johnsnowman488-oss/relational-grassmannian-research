# bAbI Task 11 prediction and evaluation contract v1.0

**Status:** IMPLEMENTED — contract tests passing; validation effectiveness not yet measured  
**Scope:** Task 11 only; HLA/HLB; Tasks 14 and 19 remain locked

## 1. Purpose and claim boundary

This contract closes the gap between source ingestion and a query-level Task 11 answer. It does not claim that coreference is solved, that the weak resolver is gold, or that HLA/HLB generalise beyond the frozen Task 11 source grammar.

The prediction path is deliberately conservative: the learned L2 context-transition model must support every location transition in the query story, and a separate story-local grounding pass must find a unique prior-only weak binding for the queried entity. Any missing or conflicting transition causes abstention.

## 2. Model input and training lifecycle

The model receives only source-observed Task 11 mention events:
- surface mention;
- whether the mention is a pronoun;
- observed location;
- source observation time and source reference;
- grammatical cue available from the observed pronoun token.

No evaluator answer, support-line list, antecedent ID or gold entity binding is passed into runtime ingestion.

The existing conservative weak-target derivation is used only for learning and story-local grounding:
- an explicit name mention creates a self-anchor;
- a pronoun is admitted only if exactly one distinct prior named entity has a compatible gender cue;
- zero-candidate or multi-candidate pronouns are quarantined;
- the target stream remains separate from durable source evidence.

For each bound mention, the H1 context-transition learner is conditioned on the entity and its immediately preceding story-local location:

`task11:entity:<entity>:from:<previous-location>`

The first transition uses `__START__`. The observed target is `location:<place>`. The previous-location state is reset at every story boundary; no entity or location state crosses stories. HLA and HLB use the same input and transition semantics.

A campaign condition configures the enabled H1 error channels before the learning runtime is used. The six conditions are the frozen full-learning condition and five declared ablations; `no_learning` enables no learning channels.

## 3. Query prediction

For a query, the predictor:
1. accepts only an `ExpansionStory` and an `ExpansionQuery` (no evaluator label);
2. filters source events to those observed strictly before the query cutoff;
3. independently derives the conservative story-local weak bindings;
4. replays the queried entity's bound location sequence through the learned transition model, using the preceding location as each transition key;
5. requires each learned transition to match the corresponding source-observed location;
6. returns the final location and the ordered source mention event IDs as witness candidates only if the complete chain is supported.

Abstention reasons include:
- no prior source observations;
- no unambiguous story-local binding for the queried entity;
- learned transition unavailable;
- learned transition conflicts with story evidence.

The predictor does not silently fall back to the symbolic baseline when the model abstains. The baseline is measured separately.

## 4. Evaluator-only scoring

Predictions are frozen before labels are passed to `evaluate_task11_predictions()`. The evaluator requires exact query coverage and one label per query. It does not mutate the model, runtime, evidence store or prediction.

Report:
- answer exact match;
- forecast coverage and abstention rate;
- support-witness recall;
- false-witness rate;
- witness-recovery mismatch count.

Official Task 11 answer/support labels do not contain independent antecedent-edge annotations. Therefore antecedent top-1 accuracy, coreference-edge precision/recall/F1 and entity-chain exact match remain **NOT INDEPENDENTLY EVALUABLE** unless a separately reviewed gold annotation stream is supplied. Do not infer these metrics from weak targets or from the resolver's own outputs.

## 5. Leakage and evidence invariants

- Query labels and support-line IDs are never inputs to prediction or learning.
- Validation stories may be ingested as observed context with learning disabled; validation answers are used only in the evaluator.
- No official test member or query is loaded by this contract.
- No generated-confirmatory labels are loaded by this contract.
- Raw mention events remain the only durable source evidence; inferred bindings and coreference edges remain learning-only.
- Every returned witness must identify a source event in the same story and precede the query cutoff.
- Story-local binding state is reset for every story, including within persistent multi-story training sequences.

## 6. Known limitations

The H1 context-transition learner is an empirical categorical transition learner. Its prediction is not a calibrated probability. The weak antecedent rule is constrained by the source grammar and its name/pronoun cue coverage. A correct Task 11 location answer does not prove independent coreference accuracy. Baseline comparison and validation coverage are required before any effectiveness claim.

The Task 11 non-oracle baselines are evaluated separately:
- nearest compatible antecedent;
- recency-only.

The official validation scorecard will compare HLA and HLB answers against these non-oracle baselines on the same whole-story validation queries. Symbolic oracle predictors are excluded from candidate selection.

## 7. Acceptance evidence

The implementation adds:
- learned-state Task 11 answer prediction with explicit abstention;
- story-local location-conditioned context transitions;
- explicit H1 error-channel configuration for ablations;
- evaluator-only answer and witness scoring;
- unit and runtime integration tests for HLA/HLB contracts.

The contract is implementation-complete only after the repository CI matrix passes. Its predictive effectiveness remains unmeasured until the independent baseline scorecard and the frozen 120-unit campaign are completed.
