# Task 11 learned-state prediction contract v1

**Status:** implementation candidate; CI review required  
**Scope:** Task 11 only; HLA and HLB; Tasks 14 and 19 remain locked  
**Purpose:** distinguish actual H1 learner-state inference from symbolic baseline prediction.

## 1. Prediction source

The Task 11 model predictor reads the active adapter's learned H1 components:

- L0: `NaryEventRoleLearner.predict(entity_context)`
- L1: `SemanticRelationLearner.predict(entity_context)`
- L2 and answer: `ContextTransitionLearner.predict(entity_context)`

The query context is `task11:entity:<normalized-query-entity>`. It is the same context key used by Task 11 learning-only updates. The predictor does not call the symbolic `predict_task11` baseline, derive new weak labels, read evaluator fields, or update model state.

The L2 context must have the form `location:<location>`. The location prediction is not accepted as a supported answer unless source evidence independently recovers at least one mention event for the queried named entity at that predicted location.

## 2. Abstention policy

- Unknown task or architecture: reject the call as a contract error.
- Missing entity query: reject the call as malformed input.
- No usable learned L2 context: abstain with `unseen_or_unusable_entity_context`.
- Learned L2 location without a source-grounded matching entity/location witness: abstain with `no_source_grounded_entity_witness`.
- Missing L0 role pattern: L0 is explicitly `__ABSTAIN__`; this does not silently fall back to a symbolic resolver.
- Missing or non-coreference L1 relation pattern: L1 is explicitly `__ABSTAIN__`.
- An answer-level abstention does not fabricate a location or witness.

L0/L1 abstention is recorded independently from answer-level abstention. A missing L1 relation is not evidence that the entity binding is wrong; it is an unavailable forecast.

## 3. Forecast/evaluator lifecycle

`issue_task11_model_forecasts()` creates L0, L1, L2 and answer forecasts using the current model fingerprint. It receives no evaluator label. The existing `ExpansionForecasts` journal enforces that the forecast issue time and evidence cutoff precede the query target.

Only after forecast issuance may an evaluator process open the official answer/support label and call `score_query()`. Generated L0/L1/L2 challenge labels remain a separate evaluator-only stream and may be passed to `score_task11_supervision()` only after all forecasts exist. Neither scoring method ingests labels into runtime evidence or learner state.

Official Task 11 answer/support annotations do not provide independent gold antecedent edges. Therefore L0/L1/L2 antecedent and coreference claims are not scored from official labels. Synthetic confirmatory edge scores remain separate and do not establish raw-text generalisation.

## 4. Evidence and model identity

The predictor computes a stable fingerprint over architecture identity and the current relation, event-role and context-transition learner snapshots. Exact witnesses are recovered from the runtime's source evidence journal at the query observation cutoff. A predicted location without a matching source witness is rejected.

The predictor is inference-only: it does not append evidence, update learners, reveal evaluator labels, or use future observations. Its answer is an H1 learned-context forecast, not a symbolic last-mention lookup.

## 5. Limits that remain open

This contract is a minimal learned-state-to-answer path, not proof of learning effectiveness. It does not yet establish:
- robust answer prediction on the frozen raw Task 11 validation partition;
- calibrated confidence or a calibrated abstention threshold;
- independently annotated raw-text coreference accuracy;
- generalisation to unseen names, ambiguous antecedents or novel discourse forms;
- campaign-scale runtime and memory under the full six-condition, ten-seed design.

These require the validation-only evaluation and baseline comparison gates. No confirmatory labels may be used for model fitting, candidate selection, warm start, online adaptation or threshold tuning.

## 6. Acceptance tests

The new tests exercise:
- inference from learned H1 component outputs for both supported architecture labels;
- source-grounded witness requirement;
- independent L0/L1 abstention and answer abstention;
- invalid task/architecture rejection;
- forecast issuance before official answer scoring;
- answer scoring through the evaluator-only prediction journal.

Passing these tests closes the implementation contract only. It does not close the baseline, campaign protocol, resource-preflight or confirmatory gates.
