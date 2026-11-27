# HLG bAbI expansion generated-confirmatory protocol v1.1

**Status:** FROZEN — revised generator, runtime input schema and seed schedule  
**Protocol ID:** `HLG-BABI-EXPANSION-CONFIRMATORY-v1`  
**Protocol version:** `1.1.0`  
**Parent:** `HLG-BABI-EXPANSION-LEARNING-CAMPAIGN-v1`

## Purpose and boundary

This is the separate, one-time confirmatory challenge for Tasks 11, 14 and 19. It is generated independently of the bAbI train/validation partition. It is not official bAbI test data. It is evaluated only after validation candidate selection and is never used for fitting, warm start, online adaptation, threshold selection or candidate selection.

The Task 11 gender cue is an explicit feature in this synthetic challenge schema. It is not claimed to be a field present in raw bAbI sentences, and generated-challenge performance must not be reported as an official bAbI result.

## Frozen generator and workload

- Generator: `src/rgm/experiments/babi_expansion_confirmatory.py`
- Seeds: **971101, 971102, 971103**
- Stories per seed per task: **128**
- Total: **384 stories per task**, **1,152 stories overall**
- Stable ordering: seed ascending, then story ordinal ascending.
- Each task has one inputs JSONL and one evaluator-label JSONL.

## Task challenge construction

**Task 11 — identifiable coreference and entity state.** Each story contains exactly two novel named entities with distinct, model-visible grammatical-gender cues (one female, one male). A pronoun's surface and cue therefore identify exactly one prior name anchor within this controlled synthetic grammar. Events are serialized in the runtime-compatible `events` schema, with `event_id`, `surface_mention`, `is_pronoun`, `grammatical_gender`, `location`, `observed_at` and `source_ref`. The query uses `entity`, `observed_at` and `source_ref`. The strict converter `task11_confirmatory_input_to_story()` maps the record directly to `Task11MentionEvent`, `ExpansionStory` and `ExpansionQuery`. No antecedent ID, coreference edge or resolved entity binding is present in an input event.

The evaluator-only label contains the answer location, support event IDs, the pronoun-to-antecedent edge set, and the L0/L1/L2 supervision bundle. The gold edge is the nearest prior explicit name anchor of the uniquely compatible gender. A non-pronoun target event is labelled as a self anchor rather than a coreference edge.

**Task 14 — temporal order.** Each story contains shuffled source-order event observations with actor, destination, temporal anchor and ordinal event-time feature. A before-destination query is evaluated against the previous temporal location. The separate label contains the answer and predecessor/target witness IDs.

**Task 19 — directed route composition.** Each story contains a novel directed spatial chain and an ordered route query. The separate label contains the direction sequence and supporting edge IDs.

## Task 11 runtime and supervision contract

Observed ingestion preserves only the raw mention surface, pronoun flag, explicit synthetic gender cue (when present), location and provenance. The gender cue is mapped as an attribute participant; it does not create an antecedent binding. `to_task_relations()` continues to return no Task 11 observed coreference relation.

The evaluator-only Task 11 bundle contains:
- **L0 `mention_binding`:** target mention event ID and entity ID.
- **L1 `coreference_edge`:** mention event, prior antecedent event, entity and relation type; a name anchor is represented as `self_anchor`.
- **L2 `entity_state`:** entity, current location and supporting event IDs.
- **Answer:** final location for the queried entity.

A forecast must be issued before the query cutoff. Only after forecast issuance may the isolated evaluator score L0, L1 and L2 with their own target schemas and source reference. The labels are not passed into `BabiExpansionRuntime.ingest_story()`, and they are not part of the native no-learning preflight.

For raw Task 11 training data, the official answer/support annotation does not provide antecedent edges. The separate weak-supervision policy is conservative: derive a pseudo-edge only when exactly one distinct prior named entity is compatible with the observed grammatical-gender cue; otherwise abstain. Weak targets carry their rule ID and source mention provenance, remain distinguishable from gold labels, and cause no mutation of observed evidence. These pseudo-targets are not a substitute for independently annotated coreference ground truth.

## Leakage, identity and determinism controls

Input files exclude `gold_answer`, `support_event_ids`, `support_line_numbers`, `mention_binding_edges`, `task11_supervision` and `antecedent_event_id`. Each input query ID must have exactly one matching evaluator label ID. The generator writes separate files and records SHA-256 for each input and label file. A repeat generation with the same code and seeds must reproduce the exact task-file hashes and aggregate manifest fingerprint.

Official test data is neither downloaded by this generator nor referenced in its inputs. The challenge's evaluator labels remain sealed until the one-time evaluation stage.

## Acceptance

The manifest is accepted only when all three task files contain 384 input rows and 384 evaluator rows, all query IDs are unique and paired, all Task 11 records pass the exact runtime schema converter, all Task 11 pronouns have exactly one compatible named antecedent, no evaluator-only fields occur in inputs, all recorded hashes verify, and a deterministic repeat reproduces the same manifest SHA-256.

A pass supports claims only on this separately generated synthetic challenge distribution. It does not establish an official bAbI test result or broader generalisation.
