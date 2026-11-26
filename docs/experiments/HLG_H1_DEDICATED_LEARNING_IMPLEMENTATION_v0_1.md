# H1 dedicated learning implementation — phase ledger

**Status:** integrated mechanism implementation and synthetic channel ablations passed; external-task learning campaigns not started  
**Parent contract:** `HLG-HYBRID-PLCE-v0.1`  
**Implementation branch:** `research/h1-learning-runtime-integration`  
**Implementation PR:** [#50](https://github.com/johnsnowman488-oss/relational-grassmannian-research/pull/50)

## Objective

Complete the H1 learning mechanisms that were not present in the initial HLA/HLB adapter implementation. Integrate them into the actual runtime while preserving the frozen H0 SOE/native dynamics and the HLA/HLB architectural distinction.

## Implemented mechanisms

### LRN-1 — Three-level prediction lifecycle

- **L0 grounding:** predicts the next observed feature vector using a fit-partition mean baseline; scores with MSE.
- **L1 relational:** predicts an exact typed relation pattern containing relation type, subject identity/type, object identity/type and context.
- **L1 event roles:** predicts one n-ary event as an event type plus every named role's exact entity identity and type. Roles remain bound to one event identity.
- **L2 context/control:** predicts the next context label conditioned on an explicitly supplied pre-observation context.
- Prediction records include level, target identity, issue tick/time, evidence cutoff, horizon, model fingerprint and target-schema fingerprint.
- The director issues predictions from pre-step state. The context used to issue a forecast is an explicit caller-supplied prior context; it is never inferred from the target event arriving in that exchange.
- A target is scoreable only after its observation cutoff and issue tick, and within its declared horizon. Prediction records remain separate from observed and derived evidence.

### LRN-2 — Error-specific learning

| Error channel | Permitted learner(s) |
|---|---|
| Temporal / L0 feature residual | L0 feature predictor and event-resolved temporal credit learner |
| Relational | Typed semantic relation-pattern learner |
| Abstraction | N-ary event-role learner and L2 context-transition learner |
| Task / action outcome | Task outcome calibration learner |

The channels remain separate; there is no universal scalar loss broadcast. Parameter-family routing returns only the explicitly permitted updates. Integrity failures block ordinary learning routes.

### LRN-3 — SOE temporal credit

- Eligibility is event-resolved: event ID, feature ID, channel, event time, observed-at time, observed tick, magnitude and SOE configuration fingerprint.
- The bounded ledger decays per event/channel and refuses silent eviction at capacity.
- Late observations begin eligibility at their actual observed tick; event time is retained but is not used to backfill prior credit.
- Incremental and deterministic replay paths are available. Eligibility state and its input journal are checkpointed with the learning runtime.
- Eligibility is a learning attribution signal, not proof of causal responsibility. Aggregate SOE `χ` is not inverted into unique event contributions.

### LRN-4 — Composite checkpoint, validation and rollback

- Both HLA and HLB adapters own the same `LearningRuntime`; its predictions, L0/L1/L2 learners, task calibrator, eligibility ledger, temporal credit and observation journal are included in adapter snapshots and composite fingerprints.
- Composite promotion binds the active candidate fingerprint, independent validation partition, protocol, criteria, data manifest and measured metrics. Failed or stale validation cannot promote.
- Ordinary checkpoint restoration is exact.
- Candidate rollback is explicitly different: it restores the incumbent model/runtime, retains observations received during the candidate interval, regenerates forecasts from the incumbent, re-evaluates intervening labels against those forecasts, and replays intervening numerical inputs through the restored native runtime.
- HLB's source event and source relation journals remain append-only; source relations are reconciled into the canonical index after rollback. HLA retains no canonical relation-witness store; its learning journal contains compact typed labels, not recoverable historical witnesses.
- Observations are not discarded merely because the candidate that first processed them is rejected.

### LRN-5 — Semantic relational and n-ary event-role learning

The feature-vector readouts remain abstract feature predictors. They are not relabelled as semantic event predictors. Separate typed learners now score:
- relation type and both endpoint identities/types;
- event type and every named participant role's entity identity/type;
- context transitions at L2.

A predicted relation or event pattern is a forecast, not a canonical observed/derived evidence record. HLB's canonical evidence store receives only source-grounded observations.

## Acceptance evidence

<badge color="success">CI passed</badge> **Run 45856623520:** 464 tests passed on Python 3.10 and 464 passed on Python 3.12.

<badge color="success">Ablations passed</badge> **Run 45856623504:** six matched synthetic variants passed, with artifact **15135123986** (`h1-learning-ablation-evidence`), ZIP SHA-256 `6118f9ecc7bfefa1f4a5a41f55f7f460a7789ea800bd41bb2f3178f16cd809ef`.

### Synthetic channel ablation outcomes

Values below are counts of online updates, not task-performance scores. Every variant received the same fit patterns and the same deliberately mismatching L0/L1/L2/task observations.

| Variant | Relation | Event roles | L2 context | L0 features | Temporal credit | Task |
|---|---:|---:|---:|---:|---:|---:|
| Full | 1 | 1 | 1 | 1 | 1 | 1 |
| Without temporal | 1 | 1 | 1 | 0 | 0 | 1 |
| Without relational | 0 | 1 | 1 | 1 | 1 | 1 |
| Without abstraction | 1 | 0 | 0 | 1 | 1 | 1 |
| Without task | 1 | 1 | 1 | 1 | 1 | 0 |
| No learning | 0 | 0 | 0 | 0 | 0 | 0 |

The ablation confirms update-route isolation: disabling one channel suppresses its designated learner updates without suppressing the other channels. The no-learning control produces no online updates while still scoring the same prediction errors.

## Scientific boundaries and remaining work

1. The L0 learner is currently a mean baseline; L1 relation/event-role and L2 context learners are deterministic empirical pattern counters. These are explicit semantic predictors and useful integration baselines, not yet compositional generalizers or evidence of broad reasoning.
2. The synthetic ablations validate mechanism isolation, not predictive performance, generalization or HLA-versus-HLB superiority.
3. No bAbI Tasks 3 or 5 learning campaign has been run. The official structured source freeze remains separate. We should discuss and preregister the learning fit/validation/confirmatory protocol before starting those campaigns.
4. HLA and HLB must receive identical fit examples, prior contexts, observation streams, prediction cutoffs and seeds in the external-task comparison.
5. The separate matched cost/workload sweep remains a later efficiency study; it must not be conflated with task accuracy.

## Disposition

The requested runtime integration, three-level semantic prediction, error routing, event-level temporal credit, composite rollback preservation and synthetic channel ablations are implemented and pass the recorded CI/ablation runs. PR #50 remains draft pending review and any further refinements agreed before the bAbI learning protocol is frozen.
