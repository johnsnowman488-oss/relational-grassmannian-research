# HLG bAbI expansion generated-confirmatory protocol v1

**Status:** FROZEN — generator, challenge construction and seed schedule  
**Protocol ID:** `HLG-BABI-EXPANSION-CONFIRMATORY-v1`  
**Parent:** `HLG-BABI-EXPANSION-LEARNING-CAMPAIGN-v1`

## Purpose and boundary

This is the separate, one-time confirmatory challenge for Tasks 11, 14 and 19. It is generated independently of the bAbI train/validation partition. It is not official bAbI test data. It is evaluated only after validation candidate selection and is never used for fitting, warm start, online adaptation, threshold selection or candidate selection.

## Frozen generator and workload

- Generator: `src/rgm/experiments/babi_expansion_confirmatory.py`
- Seeds: **971101, 971102, 971103**
- Stories per seed per task: **128**
- Total: **384 stories per task**, **1,152 stories overall**
- Stable ordering: seed ascending, then story ordinal ascending.
- Each task has one inputs JSONL and one evaluator-label JSONL.

## Task challenge construction

**Task 11 — coreference and entity state.** Each story has four novel entity tokens and raw mention observations, including pronouns, grammatical-gender cues, locations and observation indices. The input contains no resolved antecedent or entity binding. The query names the target entity; the evaluator label contains its final location and supporting event IDs.

**Task 14 — temporal order.** Each story contains shuffled source-order event observations with actor, destination, temporal anchor and ordinal event-time feature. A before-destination query is evaluated against the previous temporal location. The separate label contains the answer and the predecessor/target witness IDs.

**Task 19 — directed route composition.** Each story contains a novel directed spatial chain and an ordered route query. The separate label contains the direction sequence and supporting edge IDs.

## Leakage and identity controls

The input schema excludes `gold_answer`, `support_event_ids`, `support_line_numbers` and answer annotations. Each input query ID must have exactly one matching evaluator label ID. The generator writes separate files and records SHA-256 for every input and label file. A repeat generation with the same code and seeds must reproduce the exact task-file hashes and aggregate manifest fingerprint.

Official test data is neither downloaded by this generator nor referenced in its inputs. The challenge's evaluator labels remain sealed until the one-time evaluation stage.

## Acceptance

The confirmatory manifest is accepted only when all three task files contain 384 input rows and 384 evaluator rows, all query IDs are unique and paired, no evaluator-only fields occur in inputs, all recorded hashes verify, and a deterministic repeat reproduces the same manifest SHA-256.

A pass supports claims only on this separately generated challenge distribution. It does not establish an official bAbI test result or broader generalisation.
