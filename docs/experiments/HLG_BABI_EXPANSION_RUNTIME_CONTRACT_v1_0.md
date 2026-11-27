# HLG bAbI expansion runtime and prediction-contract acceptance v1

**Status:** implementation candidate; CI acceptance pending  
**Branch:** `research/babi-runtime-prediction-contract-v1`  
**Scope:** HLA / Task 11, HLB / Task 14, HLC / Task 19  
**Campaign:** not authorized; no learning jobs may be launched by this change.

## Runtime integration

`babi_expansion_runtime.py` maps the Phase B typed adapter events into the existing H1 contracts:

- `NaryEvent` is the common immutable event envelope. Participant roles preserve entity, mention, antecedent, destination, temporal anchor, spatial endpoints and direction.
- HLA and HLB share the same `HierarchicalRuntimeDirector.exchange` entry point, SOE feature projection, event-role learning input and prediction lifecycle.
- HLB uses its existing append-only `EvidenceStore` and canonical typed relation store for spatial edges. HLA retains exact source-event witnesses in the runtime bridge's external `EvidenceStore`; it does not gain a persistent relation store.
- Each runtime instance is story-scoped. Cross-story evidence carryover is rejected.
- Source locator and provenance are preserved. The payload digest covers the normalized adapter payload; it is not represented as a digest of the original source file bytes.

## Task-to-level contracts

| Task | L0 grounding | L1 relational | L2 context | Query answer |
|---|---|---|---|---|
| 11 | mention binding | COREFERS_TO edge | entity location state | location exact match |
| 14 | temporal anchor | temporal precedence | ordered temporal context | before-location exact match |
| 19 | directed spatial edge | ordered path composition | route context | ordered direction-sequence exact match |

The four target schemas are task-specific and use the existing `Level`, `TargetSchema`, `Prediction`, `TargetObservation` and `PredictionJournal` primitives. L0 is categorical accuracy; L1 is relation exact match; L2 context is categorical accuracy; the query-answer target is separately scored at L2. No answer label is included in `ExpansionStory`, `ExpansionQuery`, or `BabiExpansionRuntime.ingest_story`.

## Prediction lifecycle

A forecast must be issued before its evidence cutoff, carry the target schema fingerprint and model fingerprint, and become eligible only for a target observed strictly after the cutoff and within its horizon. Same-cutoff and late evidence cannot score the forecast. The evaluator-only `ExpansionForecasts.score_query` accepts `GoldLabel`; it is deliberately separate from runtime ingestion. L0/L1/L2 event targets are scored separately against their own target objects, not against the answer label.

## Acceptance gates

1. Role integrity, direction orientation and source locator preservation.
2. Event-time / observation-time distinction and causal-cutoff enforcement.
3. HLA/HLB input parity through the common runtime director.
4. Story isolation, exact witness recovery and bounded-capacity abstention.
5. Forecast schema/model identity, post-cutoff scoring, one-time scoring and answer-label separation.
6. Existing integrated HLG lifecycle, learning runtime and Task 3/5 frozen tests remain green.

A green source-adapter audit is not a learned-performance result. No baseline campaign or learning ablation is run in this phase. After acceptance, freeze a campaign protocol separately; launch remains gated on explicit review and authorization.
