# HLG-M3 pre-implementation concurrency plan

**Status:** frozen execution plan for HLG-M3-PREFLIGHT-v0.1 only

## Objective

Run independent mathematical probes concurrently without allowing them to modify or implicitly select a production architecture. Each job consumes the same M0–M2 baseline and writes a separate result artifact. The campaign is evidence collection and design review, not M3 implementation.

## Job allocation

| Job | Case | Independent responsibility | Output |
|---|---|---|---|
| 1 | M3-A | Historical evidence accumulation; exact piecewise response; interval invariance | M3-A.json |
| 2 | M3-B | Memory and operator decay; independent half-life behaviour | M3-B.json |
| 3 | M3-C | Context retrieval separation and near-duplicate ambiguity using a provisional diagnostic kernel | M3-C.json |
| 4 | M3-D | Adaptive operator boundedness under bounded switched targets | M3-D.json |
| 5 | M3-E | Audit fairness/readiness of memory architecture comparisons; record missing control definitions rather than invent them | M3-E.json |
| 6 | M3-F | Sequential acquire–dormant–reactivate probe against a reset-history control | M3-F.json |
| 7 | M3-G | Independent adversarial check of time-varying/switching stability claims | M3-G.json |

Each case has a unique owner in the workflow matrix, a fixed input schedule, a machine-readable result contract and an independent artifact. Jobs do not write shared files or depend on one another's intermediate output.

## Dependency and integration rules

- M3-A and M3-B examine the base history/decay equations.
- M3-C is a provisional diagnostic that exposes the still-open context representation and ambiguity policy.
- M3-D uses the existing M0 adaptive-route law and the M3-A admissible history range.
- M3-E is a readiness audit. Its blocked result is a valid research finding, not a runner failure.
- M3-F is a bounded task probe using the existing history-gated routing law; it is not a general learner.
- M3-G independently challenges the common but invalid shortcut of inferring switched-system stability from each instantaneous spectral radius.
- The aggregate depends on all seven case artifacts and both full-repository test-matrix jobs.

No case may revise the shared equations, alter the M0–M2 protocols, or write a production Leptograph module. Any proposed change must be recorded as a recommendation for post-campaign analysis.

## CI execution order

1. GitHub Actions starts the seven case jobs concurrently (fail-fast false, maximum parallelism seven).
2. Each job installs the package, executes exactly one case and uploads exactly one JSON artifact.
3. In parallel, the full repository suite runs under Python 3.10 and 3.12.
4. The aggregate job waits for all case jobs and both full-suite jobs.
5. The aggregate verifies exactly seven expected case IDs and writes one canonical summary JSON artifact.

## Result semantics

A case's execution_passed field indicates that its declared probe completed and its pre-registered checks held. design_status records a scientific readiness condition separately. M3-E must return BLOCKED_PENDING_CONTROL_DEFINITION until a fair unified-memory control and equal-resource budget are formalised.

The expected aggregate state for v0.1 is:

- all seven jobs executed;
- all artifacts present and valid;
- full repository tests pass on both Python versions;
- one or more design blockers are listed;
- scientific_ready_for_m3_implementation is false;
- campaign_decision is PREIMPLEMENTATION_ONLY_NOT_READY_FOR_M3_IMPLEMENTATION.

This is a successful pre-implementation campaign execution with an explicit research hold, not a failed CI run and not permission to start M3 production code.
