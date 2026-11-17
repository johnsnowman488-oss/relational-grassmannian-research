# HLG-M3 BM-1 generator and evaluator-boundary contract

**Version:** v0.1 draft  
**Parent:** HLG-M3 broader benchmark protocol BM-0/BM-1  
**Status:** amendable contract; not a full benchmark generator

## 1. Separation model

The generator/evaluator owns the complete experiment state: world configuration, world-family ID, split, seeds, relation composition, primitive labels, planted operators, true context identity, change schedule, current target and future state.

The learner may receive only a LearnerObservation. It must not receive the evaluator record, split manifest, generator object, world ID, seed, composition ID, planted operators, context truth or schedule labels.

Target values are a special case: they are not part of the observation. A PrequentialGate requires the caller to register that a prediction has been produced before it can reveal TargetFeedback. Feedback contains only the current target vector and observation flag, not the evaluator metadata.

## 2. Typed learner observation

The BM-1 implementation uses a frozen LearnerObservation with exactly these fields:
- step_index;
- sorted source_ids;
- corresponding source_vectors;
- corresponding source_observed masks;
- context_vector;
- context_observed.

A missing source is represented by a false observation mask and a null vector. A missing context follows the same rule. This is a data representation, not a choice of how a particular learner imputes or processes missing inputs; those mechanisms are later benchmark work. Input validation rejects inconsistent masks, non-finite values, duplicate IDs, and undeclared metadata.

## 3. Evaluator record

EvaluatorRecord is stored on the evaluator side and contains world and split identity, seeds, composition and primitive identifiers, true context identity, latent relation operators, change schedule, and the current target/mask. It is not an argument to learner prediction, context routing, activation, detection or candidate fitting.

The generator/evaluator can retain this record for scoring, but the learner-facing function signature receives only LearnerObservation. The explicit PrequentialGate exposes a TargetFeedback object only after a prediction ticket has been marked as predicted.

## 4. Prequential state machine

For each step:
- begin_prediction accepts a LearnerObservation and issues a step-scoped PredictionTicket;
- mark_prediction confirms the model has produced its prediction;
- reveal_target accepts the matching ticket and evaluator record, then emits only TargetFeedback;
- no next step begins until the current ticket has been resolved.

Revealing a target before prediction, using a ticket for another step, revealing twice, or starting a second unresolved step is an error. The gate enforces temporal order; it cannot prevent an application from deliberately bypassing the API, so workflow and code review must also verify that learner calls receive only the typed observation and later target feedback.

## 5. Deterministic fixture

BM-1 includes a one-step fixture generated from a supplied seed. It exists solely to test deterministic generation and the information boundary. It is not one of the eight scientific world families, is not included in the confirmatory split allocation, and must not be reported as an M3 result.

BM-2 must implement the actual eight-family generator from the manifest, preserve this separation, and add tests for all factor-level combinations and generator regeneration.

## 6. Required contract tests

- manifest regeneration is byte-stable;
- exact split and seed counts are respected;
- primary relation composition IDs and ordered sequences are disjoint across splits;
- all primary test primitive atoms are present during fit;
- the auxiliary REL-E primitive-OOD stratum is explicitly excluded from the primary claim;
- learner observation types reject evaluator-only metadata;
- missing observations preserve masks rather than clean values;
- target feedback cannot be revealed before prediction;
- the feedback object contains no world/split/seed/composition/truth fields;
- deterministic fixture output matches for equal seeds.

No passing contract test is a scientific performance result.
