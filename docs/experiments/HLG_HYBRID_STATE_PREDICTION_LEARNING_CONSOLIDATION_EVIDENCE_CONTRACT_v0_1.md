# Hybrid State, Prediction, Learning, Consolidation and Evidence Contract

**Contract ID:** HLG-HYBRID-PLCE-v0.1  
**Status:** Proposed design contract; evidence-lifecycle primitives and structured bAbI oracle adapters are implemented on the H1 branch; integrated CI acceptance and official-data byte acquisition remain pending  
**Applies to:** H0 shared three-level SOE/native hierarchy and H1 HLA/HLB adapters  
**Prerequisite architecture:** H0 shared hierarchy/SOE bridge; H1 persistent-runtime adapters, readouts, HLB canonical relation store, composite checkpoint and rollback

## 0. Purpose and claim boundary

This document defines the epistemic and learning lifecycle of the existing hybrid architecture. It does not introduce a second SOE substrate, replace the native runtime, or select HLA over HLB. It specifies how temporal state, native state, evidence, predictions and learned parameters interact while remaining distinguishable.

The current implementation already provides:
- three SOE banks and a fixed-dt bridge;
- lossless row-major embedding of each SOE channel matrix into native level (u);
- separate native evolution and native χ state;
- one native hierarchy step per global tick, with all feedback computed from a common pre-step snapshot;
- HLA/HLB adapters and learned upper-level feature readouts;
- HLB's single canonical typed binary-relation store with level-scoped indexes;
- composite snapshots, candidate promotion and rollback machinery exercised in the H1/P6 envelope.

This contract extends those foundations. Relational event prediction, multi-signal learning, temporal eligibility, and the full evidence lifecycle below are **design requirements**, not claims that the current H1 code already implements them.

No external benchmark result, general semantic capability, global stability result, or universal architecture advantage follows from this contract.

## 1. State and epistemic contract

### 1.1 State classes are distinct

| Class | Symbol / object | Meaning | May be learned or changed? | Is it evidence? |
|---|---|---|---|---|
| SOE temporal state | (S^{SOE}_{\ell,t}), channel matrix χ-bank | Decaying multiscale traces of feature inputs at level ℓ | Evolves each tick under the frozen SOE configuration; parameters change only through a separately validated configuration candidate | No; it is a temporal summary |
| Native dynamical state | (N_{\ell,t}=(u,\chi,\ldots)) | State of the compiled native hierarchy, including native kernel state and diagnostics | Evolves through native runtime; kernel/config changes require candidate validation | No; it is dynamical state |
| Observed evidence | (E^{obs}) | Source-grounded observation/event/relation with identity, time, provenance and uncertainty | Immutable as an observation; corrections are appended as new evidence/revision records | Yes |
| Derived evidence | (E^{der}) | A conclusion produced by an explicit, versioned rule from identified evidence witnesses | Recomputable/revisable; never silently overwrites its inputs | Yes, as a derivation with lineage, not as a direct observation |
| Prediction | (P) | A time-stamped, model-versioned expectation about a future or not-yet-observed target | Created, scored, confirmed, contradicted, expired or withdrawn; never promoted to observed evidence | No |
| Model parameters | θ | Readouts, encoders, predictors, context models, retrieval policies and other learned parameters | Candidate updates only; validated promotion and rollback | No |
| Runtime/control metadata | (M) | Tick, dt, schema versions, event watermarks, RNG state, model fingerprints, checkpoint lineage | Updated transactionally | No |

**Invariant:** no conversion between these classes is implicit. In particular:
- a SOE trace is not an event record;
- native (u) is not the Python SOE bank after native evolution;
- a high-confidence prediction is not an observation;
- a derived relation is not a source observation;
- a learned parameter or abstract readout is not an exact relational witness.

The H0 embedding remains an encoding operation only. Native evolution does not reconstruct or update the Python SOE banks.

### 1.2 Evidence record minimum

An observed event/relation record must carry, where applicable:

- stable record and event identifiers;
- typed entity identifiers and types;
- event/relation type and explicit participant roles;
- event time (when it happened) and observed-at time (when received);
- validity interval and context scope;
- source/provenance reference, immutable source-payload locator/retention class, and source-span or source-payload digest;
- uncertainty/quality metadata and parser/adapter version;
- revision/supersession links, if corrected.

A derived record additionally carries:
- derivation ID and rule/operator version;
- exact input witness IDs and their roles/order;
- temporal/context compatibility result;
- derivation time and confidence/uncertainty;
- model or policy fingerprint if learned selection was involved.

A prediction additionally carries:
- prediction ID, target type and target scope;
- issue tick/time and forecast horizon/deadline;
- predicted value/distribution/candidate set;
- model and feature-schema fingerprints;
- context and evidence cutoff used;
- eventual score and outcome link, when observed.

For n-ary events, participant roles must be stored together under one event identity. A collection of independent binary edges is not a substitute for same-event role binding.

### 1.3 Time and causality

Use H0's distinction between event time and observed-at time. A forecast at cutoff (c) may use only evidence observed by (c), and only state causally available at its issue tick. Late-arriving evidence is ingested at its actual observation time; it may revise current interpretations but must not rewrite prior native states or retroactively improve an already-issued forecast.

Each global cycle:
1. takes one immutable pre-step snapshot of all three SOE banks, native state, model versions and eligible evidence;
2. issues predictions from that snapshot;
3. ingests the current event batch with original event times and current observed-at times;
4. calculates all level feedback before the native step;
5. advances all SOE banks and calls the native runtime exactly once at the configured common dt;
6. commits the SOE candidate banks only if the native step succeeds;
7. evaluates forecasts only when their target becomes observable;
8. stages learning candidates separately from the observation transaction.

An empty event batch is an explicit silent tick. A gap of (k) ticks is (k) silent cycles, consistent with H0. Evidence ingestion must not depend on whether a learning candidate is accepted.

## 2. Prediction contract

### 2.1 Prediction object and lifecycle

Every prediction is an explicit object, not a relation-store fact:

`Prediction = (id, level, target, issued_at, horizon, context, evidence_cutoff,
distribution_or_value, model_fingerprint, status)`

Statuses: `ISSUED`, `SCORED`, `CONFIRMED`, `CONTRADICTED`, `EXPIRED`, `WITHDRAWN`. Status transitions are append-only in the prediction/evaluation journal. Confirmation links to the later observation; it does not mutate the prediction into an observation.

Predictions may refer to expected entities/events/relations/compositions or numerical/contextual features. Predicted relation candidates must remain outside HLB's canonical observed/derived relation namespace until supported by a valid observation or derivation. A forecast may be used for control or attention with its uncertainty visible, but never as an exact witness.

### 2.2 Level-specific targets

| Level | H0 role | Prediction targets | Required output |
|---|---|---|---|
| L0 | Grounding | Next feature vector; event occurrence/type; entity/role slots; near-term state transition | Feature forecast and/or typed event candidate with horizon, uncertainty and source/evidence cutoff |
| L1 | Relational abstraction | Relation existence/change; role binding; short event sequence; valid composition/path; temporal/context compatibility | Typed relation/event-structure candidates, ordered witness requirements, alternatives and uncertainty |
| L2 | Context/control | Context/regime persistence or transition; expected relational pattern at a broader horizon; reliability/novelty or need for lower-level retrieval | Context distribution/state forecast, scope, horizon, and explicit lower-level evidence requests where needed |

The hierarchy does not require every level to predict every target type. Each predictor declares its target schema, horizon and scoring rule. L0 grounds; L1 predicts relational organisation; L2 predicts context/control conditions. Higher levels may request evidence from lower levels but cannot manufacture it.

The current H1 readouts are narrower: they predict upper-level feature vectors from lower-level pre-step SOE traces. This contract does not relabel those readouts as already-implemented semantic event predictors. Such targets require explicit encoders/decoders and tests.

### 2.3 Forecast evaluation

A prediction is scored only against a target observation/label that becomes available after its issue cutoff and within its declared horizon. Evaluation must record the exact target source, observation time, eligibility rule and model fingerprint.

Use target-appropriate measures:
- continuous features: MSE/MAE and, where distributional, proper probabilistic scores;
- categorical event/entity/role targets: exact accuracy, per-class precision/recall and calibrated log/Brier score when probabilities are emitted;
- relation/path targets: exact relation and role accuracy, valid-witness rate, false-witness rate, and abstention;
- context/regime targets: transition detection precision/recall, calibration and lead-time;
- temporal forecasts: error by horizon and event-time/observation-time lag.

Report coverage and abstention alongside conditional accuracy. A model that abstains on difficult cases must not be scored only on answered cases. Separate parser/grounder errors from predictor/reasoner errors.

Prevent leakage: no target evidence observed after issue cutoff may enter the forecast input; calibration/training, validation and confirmatory partitions remain separate. A repeated seed/run is reproducibility evidence, not an independent sample.

## 3. Learning contract

### 3.1 Error channels remain attributable

Keep at least these learning signals separate:

- (\epsilon^T_\ell): temporal feature/state prediction residual;
- (\epsilon^R_\ell): relational target error (existence, type, role, order or composition);
- (\epsilon^A_\ell): abstraction/context prediction error;
- (\epsilon^Q): downstream task/action outcome error.

Witness-invalidity, provenance violations, temporal incompatibility and false-witness events are integrity failures, not merely another smooth prediction residual. They trigger rejection/abstention and diagnostics; they must not be averaged away by good feature loss.

Each parameter family declares which error channels may update it. No global scalar objective is assumed in v0.1. Multi-objective weighting or shared gradients require ablation evidence and explicit conflict handling.

### 3.2 SOE traces and temporal credit assignment

SOE channels provide a multiscale history basis. They can inform which past inputs are temporally associated with a later prediction error. They are not, by definition, eligibility traces or proof of causal responsibility.

**Attribution constraint:** an aggregate SOE channel is generally a superposition of multiple past inputs and cannot be uniquely inverted into event-specific contributions. Therefore, any event-level credit assignment must use either (a) an explicit, bounded eligibility/provenance ledger that records event ID, input feature identity, tick, channel, kernel/configuration fingerprint and eligibility update, or (b) deterministic replay from an immutable input journal under the exact SOE configuration. A current χ value alone is insufficient to claim that a particular event caused an error. The ledger/replay path must respect event-time versus observed-at time, late arrivals, reset/expiry rules and the prediction's evidence cutoff. Attribution remains a learning signal with uncertainty, not causal proof.

For a channel (k) at level ℓ, an eligibility feature may be defined as a separately versioned transform of the SOE channel:
[
e_{\ell,k,t}=\rho_{\ell,k}e_{\ell,k,t-1}+g_{\ell,k}(S^{SOE}_{\ell,k,t})
]
where ρ, transform (g), reset rules and normalisation are explicit. Alternatively, the SOE channel itself may be used as a regressor for a supervised readout. These are distinct choices and must not be conflated.

A parameter update is permitted only where a declared loss depends on that parameter:
[
\Delta\theta_j=-\eta_j\sum_{\ell,k}
\left(\frac{\partial L_j}{\partial\theta_j}\right)_{\ell,k}
e_{\ell,k,t}
]
This is a design template, not a frozen update equation. The actual Jacobian/eligibility construction must be specified for each learner. Do not broadcast one scalar error indiscriminately to every level or timescale.

Initial safe learning order:
1. fit/update readouts from pre-step SOE snapshots and correctly paired future targets;
2. evaluate temporal and relational errors separately;
3. add explicitly defined eligibility features for delayed credit assignment;
4. only later consider adapting SOE decay rates, injection matrices, native kernels or cross-level gains.

Freeze SOE and native dynamical configurations during initial readout-learning experiments. Any change to them is a candidate configuration with separate stability and task validation.

### 3.3 Evidence is not a learning parameter

Learning may update encoders, readouts, predictors, context models, composition-selection policies and retrieval priorities. It may not rewrite observed event payloads, source timestamps, provenance, participant roles or witness identity.

A model correction changes the interpretation or prediction. If a source observation itself is corrected, append a new observation/revision with lineage and retain the prior source record.

## 4. Consolidation contract

### 4.1 Candidate lifecycle

All learned changes are staged as candidate versions. A candidate package includes:
- parent trusted version and candidate fingerprint;
- changed parameter/configuration families and schema versions;
- training/calibration data manifest and provenance;
- learning-signal attribution and update diagnostics;
- stability/resource envelope and compatibility checks;
- validation protocol, partition identity and results.

Lifecycle:
`TRUSTED -> CANDIDATE -> VALIDATING -> PROMOTED`
or
`TRUSTED -> CANDIDATE -> VALIDATING -> REJECTED`.

A candidate is never active merely because an optimiser produced finite parameters.

### 4.2 Validation and promotion

Validation must be independent of the candidate's fitting data and fixed before candidate evaluation. It checks:
- target-appropriate forecast improvement and calibration;
- no unacceptable regression on protected tasks/targets;
- exact-witness and provenance integrity;
- abstention/capacity behavior;
- finite-state and frozen operating-envelope constraints;
- checkpoint serialization and exact restore;
- declared memory/compute limits.

Promotion is atomic across the parameter families and runtime components that must be mutually consistent. The trusted version, validation record and candidate fingerprint are retained. Validation data must not be recycled as confirmatory evidence.

### 4.3 Consolidation policy

Consolidation may:
- promote validated predictor/readout parameters;
- stabilise or distil validated abstractions;
- update retrieval priorities or summary representations with lineage;
- expire transient predictions after scoring/retention policy;
- revise derived interpretations by appending a new derivation version.

Consolidation may not:
- turn an unconfirmed prediction into observed evidence;
- overwrite or silently delete source observations;
- detach derived conclusions from their witnesses;
- merge distinct event identities or participant roles;
- alter SOE/native dynamics outside a separately validated candidate;
- discard protected evidence to make a candidate fit capacity.

Fast adaptation remains temporary candidate state. Slow consolidation means validated, versioned promotion—not simply assigning a longer SOE decay constant. Dynamical retention and parameter consolidation are different mechanisms.

### 4.4 Rollback and revision

Rollback restores the complete trusted model/runtime package: readouts/predictors, SOE configuration and channels, native checkpoint, controller/context state, RNG state, architecture-owned state and HLB relation-store snapshot/index consistency as applicable. Schema and fingerprints are validated before activation.

Rollback reverts candidate model/runtime mutations. It does **not** erase observations that arrived during the candidate interval. Those observations remain in the evidence journal and are replayed/reconciled against the restored trusted model. This separates model rollback from evidence rollback.

Revision is append-only:
- a new observation may supersede an interpretation;
- a new derivation version may replace a prior derived conclusion for current queries;
- prior versions remain addressable with their original evidence lineage;
- conflicting evidence remains represented as conflict/uncertainty until a declared resolution policy applies.

## 5. Evidence lifecycle and per-level obligations

### 5.1 Level 0 — grounding

Must preserve:
- exact observed event/record identity and source provenance;
- typed entities and all participant roles under one event identity;
- event time, observed-at time, validity and context;
- uncertainty, source quality and parser/adapter version;
- corrections and late-arrival lineage.

May summarise:
- feature vectors and SOE traces for temporal processing;
- non-authoritative local caches, provided they do not replace source evidence.

Must not:
- merge distinct events solely because their features are similar;
- discard role identity or time ordering needed by later queries;
- treat a predicted event as observed.

### 5.2 Level 1 — relational abstraction

Must preserve:
- relation/event types and argument-role binding;
- composition order and intermediate entities;
- exact witness IDs for every derived relation/path;
- all valid alternative witnesses or an explicit bounded/abstention result;
- temporal and contextual compatibility;
- derivation rule/version and uncertainty.

May summarise:
- recurring motifs, relation embeddings, path sketches and learned abstractions;
- retrieval indexes and caches, if the canonical source records and witness references remain recoverable.

Must not:
- collapse distinct paths into one unexplained edge;
- mix participant roles from different event identities;
- present a readout prediction as a validated composition;
- hide dropped alternatives when capacity is exceeded.

### 5.3 Level 2 — context/control

Must preserve:
- abstract content, scope, time/validity and context identity;
- model/rule fingerprint and uncertainty;
- evidence cutoff and links to supporting lower-level records/derivations;
- known contradictions, exceptions and counterevidence;
- retrieval instructions sufficient to request exact lower-level witnesses.

May summarise:
- context regimes, temporal trends, recurring relational patterns and control state;
- selected statistics and compressed representations.

Must not:
- claim exact event detail without retrieving its witnesses;
- treat high confidence as evidence;
- erase lower-level contradictions when compressing;
- use top-down context to rewrite lower-level observations.

### 5.4 HLA/HLB architecture-specific obligations

**HLA:** keeps SOE temporal banks, native state, learned readouts and runtime metadata. It has no persistent relation-instance store. Exact relation/path queries are evaluated only against caller-supplied evidence and the shared witness validator. If evidence is unavailable, HLA abstains or emits a separately typed abstract prediction. It must not imply that it can recover an exact historical witness it did not retain.

**HLB:** keeps the same shared SOE/native substrate plus one bounded canonical binary-relation store and a separate append-only source-event evidence journal. Level-scoped indexes are secondary views, not independent copies. Canonical IDs, provenance, time/context filters, witness references, capacity abstention and composite rollback are mandatory. The source-event journal is deliberately outside candidate model rollback: composite checkpoints record its evidence watermark, rollback restores model/runtime and derived relation-store state, and source events received during the candidate interval remain available for reconciliation. The journal is independently serializable/restorable for storage recovery. A summary/index can be rebuilt from canonical records; it cannot become an alternate untracked source of truth.

### 5.5 Evidence retrieval protocol

A higher-level request for exact support contains:
- requested claim/target and required witness granularity;
- query time, observation cutoff and context;
- required event/role/path constraints;
- requesting level and purpose.

The lower-level evidence service returns either:
- exact source/derived record IDs plus a complete witness/derivation chain and eligibility checks; or
- an explicit result such as `NOT_FOUND`, `ABSTAIN_CAPACITY`, `INCOMPATIBLE_TIME`, `INCOMPATIBLE_CONTEXT` or `INSUFFICIENT_PROVENANCE`.

A summary alone is not a successful exact-evidence response. The caller verifies witness identities, temporal/context validity and derivation lineage before using the result. For HLA, the service can only validate evidence supplied by the caller; it cannot retrieve absent persistent records.

## 6. Required invariants and acceptance tests before external task campaigns

The contract is not considered implementation-complete until tests demonstrate:

1. **State separation:** snapshots and APIs distinguish SOE banks, native (u/\chi), observed/derived evidence, predictions, model parameters and runtime metadata.
2. **Causal prediction:** a forecast is issued from a pre-step snapshot and cannot access evidence beyond its cutoff.
3. **Prediction/evidence separation:** predictions never enter the canonical evidence store as observed/derived records without a valid confirmation/derivation transition.
4. **Level targets:** L0/L1/L2 prediction schemas and target-specific scoring are explicit; current feature readouts remain labelled as feature predictions.
5. **Error attribution:** temporal, relational, abstraction and task errors are logged separately; integrity violations trigger rejection/abstention.
6. **Temporal credit assignment:** any eligibility feature has explicit recurrence, decay, reset, normalisation and parameter attribution; tests show no cross-level leakage, include overlapping events contributing to the same channel, and demonstrate exact replay or event-ledger attribution without future-information leakage.
7. **Candidate isolation:** failed candidate learning cannot mutate the trusted model or evidence.
8. **Independent promotion:** candidate validation is independent, predeclared and fingerprinted; promotion is atomic.
9. **Evidence-safe rollback:** model/runtime rollback restores trusted state while preserving and reconciling observations received during the candidate interval.
10. **Per-level evidence preservation:** witness chains, n-ary role binding, contradictions, time/context scope and provenance survive abstraction, checkpoint and restore. Source-event journals remain append-only across model rollback; checkpoint watermarks must resolve against the active journal.
11. **HLA/HLB parity boundaries:** matched shared dynamics remain identical; HLA abstains without supplied witnesses; HLB retrieval and capacity behavior remain canonical and auditable.
12. **Resource accounting:** temporal state, native state, model parameters, HLB records/indexes, prediction journal and process overhead are reported separately.

Tests must include negative cases: late arrivals, contradictory observations, missing witnesses, invalid role combinations, stale context, capacity exhaustion, failed native steps, failed promotion and rollback with intervening new evidence.

## 7. Implementation order and external-task gate

Implement and verify the contracts in this order:
1. versioned state/epistemic schemas and cycle ordering;
2. prediction objects, target schemas and leakage-safe scoring;
3. separate learning-signal attribution and explicit temporal eligibility;
4. candidate validation, promotion, evidence-safe rollback and revision;
5. level-specific evidence summaries, witness retrieval and n-ary event role binding.

Only after the contract tests pass should external task adapters be introduced. The next planned external campaign remains bAbI Tasks 3 and 5, beginning with frozen official data/configuration and oracle structured-event inputs before adding text parsing. Their results must be reported as new evidence; H1 synthetic results do not establish benchmark performance.

## 8. Explicit non-claims

This contract does not establish:
- that current H1 readouts already perform semantic event or relational prediction;
- that SOE channels are automatically causal eligibility traces;
- that every higher-level abstraction is correct because its lower-level inputs were valid;
- that HLB's binary relation schema already supports general n-ary event binding;
- that consolidation improves generalisation or prevents catastrophic forgetting;
- that three levels are optimal;
- that HLB is universally superior to HLA;
- that the tested P6 finite-horizon stability envelope extends to new learning rules, kernels, gains, dimensions or input distributions.

All new mechanisms require separate implementation, ablation and independent validation.

## 9. Implementation update — 2026-11-26

The first evidence-lifecycle implementation has been added on the H1 branch:

- `src/rgm/leptograph/m4/evidence.py`: immutable n-ary source events, role binding, source digests, provenance verification, append-only revisions, summaries, derived evidence, exact witness recovery, observation-cutoff checks, contradiction reporting, explicit capacity abstention, and independent journal snapshots.
- `HLBAdapter`: owns the bounded source-event journal separately from its candidate relation store. HLB model snapshots carry an evidence watermark; model restore validates that checkpoint references still resolve but does not truncate the append-only source journal. Explicit evidence journal checkpoint/restore is a separate storage-recovery operation.
- `tests/test_hlg_evidence_lifecycle.py` and `tests/test_hlg_integrated_contract_acceptance.py`: unit and lifecycle cases cover role integrity, late arrival, contradictory claims, missing witnesses, provenance tampering, summary/derivation recovery, capacity exhaustion, failed validation, promotion, rollback and evidence received during a candidate interval.
- `src/rgm/experiments/babi_structured.py`: oracle structured-event solvers for Task 3 temporal object-state questions and Task 5 same-event three-role retrieval. These accept typed events only; no story-text parsing is present.
- `docs/experiments/HLG_BABI_TASKS_3_5_STRUCTURED_CAMPAIGN_v0_1.json`: freezes bAbI v1.2, English `en-valid-10k`, task-specific train/validation/test paths and the structured campaign stages. The archive SHA-256 is pinned to the upstream Git LFS object digest `0364ebde659f14d11bc21744516c5ec49d3d06cb692733f66680771244998898` (15,719,851 bytes); local acquisition and extracted-file hashes remain outstanding.

**Validation status:** workflows for the preceding evidence-test commit `b5b85585a80e88ed818317480a1c6af837acc400` passed on Python 3.10/3.12, including H1, repository regression, P6 and compiled native smoke. Subsequent commits integrated the HLB-owned journal, checkpoint watermark validation, and bAbI structured adapters; these later changes have not yet received a CI run. No official bAbI score is claimed. The archive must be acquired and its pinned digest verified before official-data scoring.
