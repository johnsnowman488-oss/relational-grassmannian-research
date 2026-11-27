# HLG bAbI Task 11 supervision and evidence boundary v1.0

**Status:** Contract specified; weak-label derivation and evaluator scoring implemented; HLA/HLB learning-update integration remains a separate campaign implementation gate.

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

## 5. Remaining learning gate

This contract specifies how separate supervision signals are identified, provenance-bound and evaluated. It does not itself implement or demonstrate HLA/HLB parameter updates from those signals. Before a learning campaign, the learning controller must define and test how each target's loss/score reaches its appropriate L0/L1/L2 learner, how abstentions are masked, how pseudo-label confidence is represented, and how online temporal credit is assigned without converting weak predictions into facts. This requires an explicitly authorized bounded learning microbenchmark and remains outside the no-learning preflight.
