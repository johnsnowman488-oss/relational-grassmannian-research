# bAbI Tasks 3 and 5 — HLA/HLB Learning Protocol v1.3.0

**Protocol ID:** HLG-BABI-T3-T5-LEARNING-v1.3.0  
**Status:** Proposed frozen amendment; acceptance-gated before the ten-seed campaign  
**Supersedes:** v1.2.2 for all future runs. The v1.2.2 pilot remains immutable historical evidence.  
**Parent protocol:** [v1.2.2](HLG_BABI_TASKS_3_5_LEARNING_PROTOCOL_v1_2.md)

## 1. Amendment rationale and claim boundary

The v1.2.2 recovery pilot completed all four task/architecture workers and all six configured variants. It established exact HLA/HLB parity for the observed pilot conditions, but it exposed three measurement/protocol defects:

1. The L1 relation-pattern score was absent in held-out phases because forecasts were conditional on a learned pattern being available. Missing forecasts were not distinguished from zero-score forecasts.
2. The task ablation was inert: the task channel received only deterministic answer-solver error, which was zero for all eligible pilot queries.
3. The frozen v1.2.2 document still stated an HLB capacity of 65,536, while the corrected runner used 262,144.

This amendment repairs the measurement lifecycle, gives the task channel a real task-level predictive target, and reconciles the HLB capacity and provenance. It does not reinterpret v1.2.2 results retroactively.

The deterministic task-query executor remains separate from learned prediction. Task-channel learning below predicts the probability of a task-solver error; it does **not** predict the answer and must not be reported as learned QA.

## 2. Data, partitions and provenance

Retain the v1.2.2 source and partition rules:

- Official bAbI v1.2.0 English `en-10k` archive, complete archive SHA-256 `84f5296ab9a1ad0dc9464e08c491d65cd08830fca3acae9ab86f75e0fb81573c`, 11,745,123 bytes.
- Task 3 source training file SHA-256 `d125e8d2987ef764d107bf9f23223bfd166400581c1ace418533b540fd19592f`.
- Task 5 source training file SHA-256 `2506910935b701bac64fc8b1d7ff12bd8d0f47ceefca183454282bec784c12a5`.
- Fit: 1,800 whole story blocks per task; warm-start: 1,200 stories; online adaptation: 600 disjoint stories.
- Validation: 200 whole story blocks per task, derived deterministically from the source training set and disjoint from fit.
- Confirmatory: 200 independently generated structured stories per task, five queries per story, seeds 953900 (Task 3) and 953901 (Task 5). This is not an official bAbI test set.
- Official `en-10k` test files remain quarantined and excluded from metrics and candidate selection.

The exact source/derived split hashes remain in the v0.1 structured-campaign manifest. The recovery pilot's frozen-input artifact is GitHub artifact 15179043770, ZIP SHA-256 `77ce2b6d9931d1d8c2cd601422d8234242bbf6664ec08e68cac43853703a79eb`. Within that artifact:

- Annotation manifest SHA-256: `beec2c62fc3bdf1b43f7fbca28d1f4ef7b70e0ffac487cddb16272e90bbc15c8`.
- Confirmatory-input manifest SHA-256: `bdca487bf20ba9e44a76f3f8412cd0774b7309eae9e7f1498ce57675ef025680`.

Every campaign output must record the exact implementation commit, protocol-manifest SHA-256, source split/annotation/confirmatory manifest hashes, per-task input hashes, seed, variant, native runtime commit, actual loaded native library path and SHA-256. Missing provenance is a hard failure.

## 3. Matched runtime and evidence-store capacity

Keep the v1.2.2 matched HLA/HLB runtime, SOE configuration, native step contract, episode resets and story order. Both architectures receive identical event/query streams, feature encodings, per-seed story order, prediction cutoffs and horizons.

Pinned native runtime:

- Aberconics framework commit: `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de`.
- Actual loaded `libgfe_core.so` SHA-256: `38b278a93a5b3fa3b544f55d958a2f7a44bb6e1d39154e63072f5ed7be511e4b`.
- Each adapter owns one persistent C++ hierarchy handle.
- Exactly one native step per director exchange; record and assert native steps equal adapter ticks.

HLB uses one canonical persistent evidence/relation store with story-scoped exact witness recovery and no cross-story retrieval. Set the evidence store, canonical relation store and source-relation journal capacity to **262,144 records**. This covers the complete frozen per-seed workload with headroom:

| Task | Source events | Source relation projections |
|---|---:|---:|
| Task 3 | 154,786 | 154,786 |
| Task 5 | 61,532 | 73,971 |

Run the complete-workload preflight before any seed-condition starts. A capacity shortfall or capacity miss is a hard failure; do not evict protected evidence or silently truncate records. The earlier 65,536 value is superseded and must not be used by implementation, tests, workflow defaults or current protocol references.

## 4. Prediction target and lifecycle contract

All four declared targets are part of the prediction contract:

| Target | Level | Type / metric | Observation target |
|---|---|---|---|
| `next_l0_features` | L0 | continuous / MSE | next event or query feature vector |
| `next_relation_pattern` | L1 | relation / exact match | one canonical relation projection for the next source-event exchange |
| `next_event_role_pattern` | L1 | relation / exact match | complete typed n-ary event-role pattern |
| `next_context` | L2 | categorical / accuracy | next event/query context |

### 4.1 Forecast issuance and abstention

A declared target must receive a forecast at each applicable exchange. If a learned L1 or L2 predictor has no pattern for the requested context, it must issue the explicit sentinel `__ABSTAIN__`. The sentinel is scored against the subsequently observed target and therefore counts as an incorrect forecast, not as a missing metric or silently omitted example. It remains distinguishable in the lifecycle/coverage counts.

The relation-pattern target is one canonical projection per source-event exchange. For Task 5 GIVE, the source evidence still preserves both typed projections (`gave_to` and `gave_object`); the forecast metric is explicitly the first canonical projection in the deterministic relation ordering. The n-ary event-role target separately scores the complete GIVE(giver, object, recipient) event.

Relation and event-role forecasts are not applicable to query-only exchanges. Withdraw those forecasts at that exchange and record the withdrawal; never allow them to remain active and match a later event. At story/phase boundaries, close all remaining issued forecasts as right-censored/withdrawn. This prevents forecasts from crossing episode boundaries.

### 4.2 Strict causal scoring

A target is scoreable only when its observation time is strictly later than the forecast evidence cutoff and its observation tick is after issue and within the declared horizon. Same-time or late observations remain in the evidence journal but withdraw the forecast; they are not scored. Do not relax this cutoff to increase coverage.

Every phase must report, for each target:

- forecasts issued;
- forecasts scored;
- forecasts withdrawn;
- forecasts expired;
- forecasts still issued at phase end (must be zero after closure);
- expected scoreable targets;
- score coverage = scored / expected scoreable targets.

The phase must also report a metric row for every declared target even when its score count is zero. Validation and generated-confirmatory phases require 100% score coverage for all expected scoreable targets. Any gap blocks candidate acceptance and must be diagnosed, not imputed.

Score-only warm-start dynamics, validation and confirmatory processing must issue and score predictions, advance the native/SOE state and preserve HLB source evidence, while leaving all learner parameters, task calibration state and temporal eligibility unchanged.

## 5. Task-channel prediction and ablation

The task channel predicts **task-solver error probability**, not the answer.

For each task key (Task 3 or Task 5), let the observed online binary outcome be (y_t=1) when the deterministic structured solver's committed answer is wrong and (y_t=0) when it is correct. Before observing the current outcome, predict:

[
p_t = rac{1+sum_{i<t} y_i}{2+n_{t-1}}
]

This is the Laplace-smoothed empirical error probability, with an initial prior of 0.5. Score the forecast with Brier loss:

[
L_t=(p_t-y_t)^2
]

After the answer is committed and the outcome is known, append the binary outcome to the task-outcome learner if and only if the task channel is enabled and the phase permits learning. Correct outcomes ((y_t=0)) must be recorded; otherwise the task learner would remain inert on an all-correct solver workload. Warm-start dynamics, validation and confirmatory phases calculate/report the score but do not update the learner.

The `no_task` condition suppresses only these task-outcome calibration updates. It still computes and reports the same task Brier signal. The `full_learning` condition updates on every eligible online task outcome. This is a real task-level prediction-error signal; it does not create synthetic wrong answers or modify the deterministic solver.

## 6. Six matched conditions and manipulation checks

Run exactly these six conditions with identical input order:

1. `full_learning`
2. `no_temporal`
3. `no_relational`
4. `no_abstraction`
5. `no_task`
6. `no_learning`

Each condition must be proven by learner-state deltas, not inferred from its label:

- Full: temporal, relational, abstraction and task learner state can update.
- No temporal: temporal eligibility/credit and L0 predictor updates are suppressed; other channels remain enabled.
- No relational: semantic relation learner updates are suppressed.
- No abstraction: event-role and context-transition learner updates are suppressed.
- No task: task-outcome calibration state is unchanged despite a measured task Brier signal.
- No learning: all online learner state remains unchanged.

All conditions use the same fit-only warm-start fitting. Therefore `no_learning` means no online learner updates; it is not an untrained model.

## 7. Candidate selection and one-time confirmatory lock

Use ten paired seeds `953000–953009`. Run four workers concurrently: Task 3 HLA, Task 3 HLB, Task 5 HLA and Task 5 HLB. Each worker executes all six conditions for all ten seeds (60 seed-condition outputs per worker; 240 across the matched campaign).

Candidate selection uses validation only:

1. All source, provenance, prediction-coverage, no-leakage and evidence-integrity gates pass.
2. Task-query exact accuracy and supporting-witness recall meet the frozen structured-query acceptance thresholds.
3. Maximise L1 event-role and relation-pattern forecast accuracy.
4. Minimise L0 feature forecast error.
5. Report L2 context accuracy and task-outcome Brier loss as distinct outcomes.
6. Minimise abstention; stable candidate identity is the final tie-break.

Before G4, freeze candidate fingerprints, implementation commit, protocol and criteria fingerprints, source/annotation/confirmatory manifests, validation metrics and acceptance decisions. Run the generated confirmatory challenge once after candidate freeze. Confirmatory evidence cannot retune or promote a candidate.

## 8. Acceptance gates

- **G0:** verify official archive, source/derived split hashes and quarantined test policy.
- **G0.5:** verify deterministic generated challenge, exact counts, novel entities and label-free input manifest.
- **G1:** verify source-indexed annotations, evaluator-label isolation and whole-story partition boundaries.
- **G2:** targeted prediction lifecycle, score-only immutability, all six ablation manipulations, HLA/HLB evidence parity, HLB capacity preflight, exact provenance, native one-step-per-tick and full repository CI all pass.
- **G3:** ten-seed × six-condition matched campaign completes; candidate selection and fingerprint freeze from validation only.
- **G4:** one-time generated confirmatory scoring after G3 freeze.
- **G5:** publish results, artifacts, hashes, lifecycle counts, per-seed outcomes and claim-boundary review.

No G3 campaign begins before G2 acceptance. No G4 confirmatory evaluation begins before G3 candidate freeze.

## 9. Statistical reporting and claim boundaries

Report per-seed results, pooled micro/macro metrics, exact denominators and paired story-level bootstrap 95% intervals, with stories clustered within seed. Repeated seeds over the same stories are not independent confirmatory samples.

This experiment measures structured-event prediction, task-outcome calibration and evidence-backed retrieval. It does not measure natural-language parsing, unrestricted semantic understanding, open-world reasoning or general intelligence. The generated confirmatory challenge is not an official bAbI test set. No HLA/HLB winner or broad learning-advantage claim follows from the single-seed pilot.
