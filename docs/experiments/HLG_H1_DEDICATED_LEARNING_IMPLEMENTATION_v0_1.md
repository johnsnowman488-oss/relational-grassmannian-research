# H1 dedicated learning implementation — phase ledger

**Status:** implementation in progress; no external-task learning claim  
**Parent contract:** `HLG-HYBRID-PLCE-v0.1`  
**Implementation branch:** `research/h1-learning-mechanisms`

## Objective

Implement the learning mechanisms that the H1 hybrid state/prediction/learning contract requires but that the first H1 adapter milestone did not yet provide. Keep the H0 SOE/native dynamics frozen. HLA and HLB must consume identical pre-step learning inputs and retain their existing architectural distinction: HLA does not persist relational evidence; HLB uses its bounded canonical evidence store.

## Phase map and acceptance evidence

| Phase | Required mechanism | Initial implementation | Closure condition |
|---|---|---|---|
| LRN-1 | Explicit L0/L1/L2 target schemas and prediction lifecycle | `learning.py`: `TargetSchema`, `Prediction`, `PredictionJournal` | Adapter-integrated issue/evaluate ordering; per-level target schemas frozen; cutoff/horizon tests pass |
| LRN-2 | Separate error channels and parameter-family routing | `LearningSignals`, `ErrorRouter`, `ParameterRoute` | Actual readout/encoder/context learners consume only declared signals; integrity failures block candidate updates |
| LRN-3 | SOE temporal credit assignment | `EligibilityLedger`, `EligibilityEvent`, `replay_eligibility` | Exact replay parity against the immutable event-input journal; overlapping-event, late-arrival, expiry, reset and cross-level isolation tests |
| LRN-4 | Candidate adaptation and independent validation | `ConsolidationGate`, `ValidationReceipt` | Candidate learners operate on copies; validation receipts bind protocol, partition, criteria, model and evidence watermark; promotion/rollback integrate with composite HLA/HLB checkpoints |
| LRN-5 | Relational and abstraction learning | target schemas and routing primitives only | Implement and test typed event/role prediction, relation existence, ordering/composition and context-transition learners; predictions stay outside canonical evidence |
| LRN-6 | Evidence-safe consolidation | append-only journal/watermark contract in gate | Integrate with HLB source journal and HLA caller-supplied witnesses; rollback restores model/runtime while retaining/reconciling all observations received during candidate interval |
| LRN-7 | Matched validation and ablation | Not yet executed | Fit/validation/confirmatory separation, frozen bAbI Tasks 3/5 structured inputs, paired HLA/HLB campaigns, ablations for eligibility and error routing, full report |

## Implemented primitives in this branch

- Prediction objects carry level, target identity, issue tick/time, horizon, evidence cutoff, model fingerprint, schema fingerprint, value and uncertainty.
- Scoring requires a target observed strictly after the forecast cutoff and issue tick, within the declared horizon. Continuous, categorical, relation and context target types have distinct scoring paths.
- Temporal, relational, abstraction and task residuals remain separate. An integrity failure (for example false witness or provenance violation) blocks all ordinary parameter routing.
- Event-resolved eligibility records retain event identity, feature identity, channel, event time, observed-at time, observed tick, magnitude and SOE-kernel/config fingerprint. Late evidence is never backfilled. Capacity exhaustion is explicit.
- Deterministic replay rebuilds eligibility from the immutable input-event sequence.
- Candidate parameters are copied before staging. Validation receipts bind the candidate and trusted parent fingerprints, independent protocol/partition/criteria fingerprints, metrics and evidence watermark. New evidence invalidates an earlier receipt.

## Non-negotiable design boundaries

1. Eligibility is an event-resolved learning trace, not a claim of causal identification. Aggregate SOE `χ` alone is not inverted into event contributions.
2. The first implementation keeps SOE decay, injection matrices, native kernels and cross-level gains frozen.
3. A feature readout is not relabelled as a semantic event/relation predictor.
4. A predicted relation is never inserted into HLB's canonical observed/derived relation store.
5. HLA cannot recover exact historical witnesses it did not retain.
6. HLB's source journal is append-only and distinct from rollback-scoped candidate/model state.
7. Validation and confirmatory data are not recycled for fitting or candidate selection.
8. No universal HLA/HLB winner or general reasoning claim follows from passing these implementation tests.

## Immediate follow-on sequence

1. Run the full repository CI and fix every regression.
2. Add adapter-level integration so prediction issuance occurs from common pre-step snapshots and learning state participates in composite checkpoint/restore.
3. Add typed relational/event-role predictors and separate relation/context learners; test role integrity and witness-aware scoring.
4. Add immutable eligibility-input journal and verify incremental/replayed traces byte-for-byte, including late observations and overlapping events.
5. Wire actual candidate learners to LRN-2 routing and LRN-4 validation; add failure injection and rollback with intervening evidence.
6. Freeze structured bAbI Tasks 3 and 5 learning protocols and partitions; run fit/validation first, then untouched confirmatory campaigns.
7. Conduct ablations and matched HLA/HLB cost/workload analysis separately. A task score is not an efficiency result.

## Current disposition

The initial primitives are committed, but the learning programme is **not complete** until LRN-1 through LRN-7 meet their closure conditions. In particular, current H1 readouts remain feature-vector readouts; semantic relational learning, adapter integration, composite learning checkpoint tests and bAbI learning results remain open.
