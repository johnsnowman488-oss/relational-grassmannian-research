# HLG bAbI Task 11 supervision and evidence boundary v1.0

**Status:** Weak-label derivation, evaluator scoring and HLA/HLB learning-only update routing are implemented and covered by tests. Learning effectiveness, coreference generalisation and accepted resource qualification remain open.

## 1. Three information domains

| Domain | Contents | Permitted use |
|---|---|---|
| Observed input | Mention surface, pronoun flag, location, optional explicit grammatical-gender feature, observation time, source provenance | Append to evidence/runtime state |
| Derived weak supervision | Prior-only antecedent pseudo-targets from a deterministic rule when there is exactly one compatible candidate | Training target signal only; never mutate source evidence |
| Evaluator ground truth | Official answer/support labels where available; separately generated synthetic antecedent edges and L0/L1/L2 bundles | Independent scoring only after forecasts; never learner input |

No parser-side entity binding or inferred coreference edge is treated as an observation. `to_task_relations()` for Task 11 returns an empty tuple; raw mention records remain recoverable at L0.

## 2. Weak antecedent target derivation

`derive_task11_weak_binding_targets(story)` scans source observations in order. A pronoun target is emitted only if exactly one distinct named entity has a previously observed compatible grammatical-gender cue. It points to that entity's latest prior explicit name event. Zero candidates or more than one distinct candidate produce an abstention record with reason and candidate count.

Every weak target carries the mention event ID, antecedent event ID, entity ID, source reference and rule ID `task11.unique-gender-anchor.v1`. The report declares `not_gold_labels=true` and `evidence_mutations=0`. This is noisy, rule-derived supervision—not a substitute for independently annotated coreference truth. Candidate ambiguity must not be resolved by recency alone.

The model-visible gender cue in the generated confirmatory set is a synthetic feature of that challenge schema. Raw bAbI sentences do not expose a structured gender field; the ordinary parser may derive a pronoun cue from the observed pronoun token, and the name lexicon remains a baseline prior. This does not justify claiming that general coreference is solved by gender.

## 3. Forecast and scoring lifecycle

For a target query, issue forecasts for:
- **L0 — `mention_binding`:** the mention event ID and hypothesized entity ID.
- **L1 — `coreference_edge`:** the mention event ID, antecedent event ID and relation type.
- **L2 — `entity_state`:** entity ID, location and support witness IDs.
- **Answer — `location_answer`:** requested entity's location.

Forecasts carry the model fingerprint, schema fingerprint, issue tick/time and evidence cutoff. They must precede the target. `task11_supervision_from_evaluator_label()` validates the isolated evaluator bundle, and `ExpansionForecasts.score_task11_supervision()` scores L0/L1/L2 separately after reveal with the original target source reference. `score_query()` scores the answer target only. Neither scoring method appends labels to evidence or replays them through runtime ingestion.

## 4. Ground-truth availability and restrictions

The raw bAbI Task 11 task supplies answer and support annotations for the location question, not a complete gold antecedent-edge annotation. Therefore:
- validation baseline scorecards must mark Task 11 coreference-edge metrics as unavailable unless an independently reviewed target-label stream exists;
- weak pseudo-label quality cannot be evaluated by comparing the pseudo-label rule against itself;
- generated synthetic L0/L1/L2 labels are a one-time confirmatory evaluation stream, accessed only after validation candidate selection, and never used for fitting, warm-start, online adaptation, threshold tuning or selection;
- Task 11 query-answer accuracy does not imply antecedent-edge accuracy.

## 5. Learning-only target-update route (implemented)

`derive_task11_training_bindings(story)` emits a separate training-only target stream. Explicit name mentions create self-anchor targets. A pronoun creates a weak target only when the conservative prior-only resolver finds exactly one compatible named entity; unresolved and ambiguous pronouns are quarantined and produce no inferred binding. Targets retain mention ID, antecedent ID, entity ID, source reference, rule ID and `is_gold=false`. This rule is not gold coreference annotation and carries no calibrated numeric confidence.

`BabiExpansionRuntime.ingest_story()` routes these targets into existing H1 learner components without converting them to observed facts:
- **L0 mention binding:** an augmented, learning-only n-ary event updates the event-role learner.
- **L1 coreference edge:** a typed `corefers_with` relation updates the semantic-relation learner.
- **L2 entity state:** an entity-scoped location/context transition updates the context-transition learner.
- **Temporal credit:** target errors are applied through distinct `task11:L0`, `task11:L1` and `task11:L2` eligibility channels. Those filters are persisted in the observation journal and replayed after a `LearningRuntime` checkpoint restore.

The evidence boundary is preserved. The director receives the raw source `nary_events` for durable evidence storage. Derived `learning_nary_events` and `learning_relations` are delivered only to learner components; HLB does not append them to its canonical evidence store. Provenance is carried in the learner observation journal. An ambiguous pronoun remains a raw, recoverable observation but receives no inferred L0/L1 binding target and no matching L2 context update.

Acceptance tests now cover both HLA and HLB: positive L0/L1/L2 updates, durable-evidence isolation, ambiguous-pronoun masking, unchanged parameters with `learning_enabled=false`, and replay of a level-filtered SOE temporal-credit update. These are implementation/invariant tests, not a learning-capability or generalisation result.

## 6. Remaining learning and evidence gates

- The weak gender-compatibility rule is a limited pseudo-label source. It is not independently validated against a gold Task 11 antecedent-edge annotation, and Task 11 official validation still does not provide such labels.
- No numerical pseudo-label confidence calibration exists yet. The implemented confidence policy is conservative unique-candidate admission plus explicit abstention.
- The isolated `ExpansionForecasts` evaluator-scoring lifecycle remains separate from learner ingestion. Evaluator labels and generated-confirmatory labels are not used by the new runtime update route.
- The implementation has not been evaluated for improved Task 11 answer accuracy, coreference generalisation, robustness to names/genders outside the weak-rule coverage, or transfer across story distributions.
- The learning-cost workflow was accidentally attached to the automatic PR path and executed twice before the explicit-authorization guard was added. Those runs are quarantined as unauthorized diagnostics and do not close the resource gate.
- Any new learning-cost benchmark must be manually dispatched with `enable_learning_cost_microbenchmark=true` after explicit user authorization. The full 360-unit learning campaign remains separately frozen and unauthorized.
