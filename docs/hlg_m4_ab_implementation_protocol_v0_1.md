# HLG-M4 A/B implementation protocol — v0.1

**Status:** Proposed for review; not frozen until the acceptance gate is approved.  
**Parent:** M4 Job 4 / issue #36.  
**Scope:** Fixed-topology synthetic A/B relational-memory integration and stability; no confirmatory run authorised by this draft.

## 1. Research question

Does a system combining temporal memory with learned relational organisation retain and compose typed relational evidence over time, select valid multi-edge paths from partial observations, and revise its relational organisation under controlled change without corrupting trusted knowledge?

Primary comparison:
- **A — SOE-only:** SOE temporal memory with learned relational readout; no separate persistent relation store.
- **B — SOE + relational store:** the same temporal-memory substrate plus a separate persistent typed relation-instance store.

B is the leading hypothesis. It is not the assumed winner. A must receive the same observations, task information, training exposure and evaluation queries.

## 2. System boundary and exclusions

Included:
- fixed relation/entity schema and fixed candidate topology;
- event ingestion with event time, observation time, context, validity interval and provenance;
- temporal SOE memory;
- A readout or B persistent relation store;
- bounded context acquisition and explicit abstention;
- candidate retrieval, learned path selection and witness-preserving composition;
- G3-derived detector/revision policy and complete trusted-state rollback;
- finite-horizon stability, resource and reproducibility characterisation.

Excluded:
- E08 cross-domain transfer;
- endogenous topology birth/death or mode birth/death;
- arbitrary predicate algebra or arbitrary-depth composition;
- Grassmannian/geometric representation advantage;
- natural-language understanding or open-world discovery;
- arbitrary asynchronous/delayed switching stability or global Lyapunov theorem;
- D2C integration claims.

## 3. Architecture definitions

### A — SOE-only learned relational readout

Persistent state consists of fixed SOE channels and learned readout parameters. Each observation is encoded into the declared SOE feature space. Retrieval and candidate path scoring must be learned from the trace/readout; A must not maintain a persistent dictionary/graph of relation instances.

The same raw typed observations may be presented at update time as B receives, but A may retain only its declared temporal state and learned parameters. Temporary input buffers must be cleared after the update and excluded from query-time access.

### B — SOE plus persistent typed relational store

Persistent state consists of:
1. the same fixed SOE temporal memory and temporal readout interface as A; and
2. a separate relation-instance store preserving stable instance ID, typed endpoints, relation type, event time, observed-at time, context, expiry and provenance.

The store must preserve historical instances and apply the query's observation cutoff and temporal-validity rules. It must not expose future observations, hidden target paths or evaluator-only labels. Relation insertion/revision and capacity policy must be explicit; no silent eviction. When capacity or ambiguity prevents a defensible result, return a typed abstention.

The Job 2 scalar dictionary is a preliminary persistence primitive, not the production B store.

## 4. Shared interface and task contract

Version one common contract before parallel implementation. The conceptual interface is:

- `observe(event)`: ingest one actually observed event.
- `advance_gap(dt)`: advance time without fabricating observations.
- `query(query_spec)`: return a selected candidate path or explicit abstention, with score and evidence.
- `snapshot()` / `restore(snapshot)`: complete trusted-state capture and restoration.
- `resource_snapshot()`: report state, parameter, update and query costs.

### Event record
- stable `instance_id`;
- typed subject and object;
- relation type;
- `event_time`;
- `observed_at`;
- optional context;
- optional `valid_until`, interpreted as half-open `[event_time, valid_until)`;
- provenance/audit metadata.

### Learner-facing query
- typed start and goal constraints;
- context constraint or explicit unknown-context state;
- query time and observation cutoff as separate values;
- maximum path depth;
- any task-visible temporal-order/gap constraints.

The query must **not** contain the hidden relation-type sequence or oracle path. A learner proposes candidate relation sequences/bindings. The shared reference composer validates those candidates and returns complete ordered witnesses. A separate oracle mode may enumerate valid reference paths for scoring and debugging, but oracle results must never enter learner inputs or learned-result metrics.

### Witness contract
A valid witness preserves the complete ordered entity sequence and relation-instance IDs. It must satisfy:
- exactly one more entity than relation instances;
- each edge's subject equals the preceding entity and object equals the next;
- each edge's type matches the candidate relation sequence;
- no relation-instance reuse within a path;
- event-time order/gap and validity rules;
- observation cutoff and context rules.

Ordinary extensional witness joining may be associative when joins are well-formed. No arbitrary predicate-composition associativity is assumed.

## 5. Information boundary and leakage controls

Model-visible information:
- events actually received by the cutoff;
- fields declared in the event/query contract;
- the current architecture state and its own learned scores.

Evaluator-only information:
- planted complete world structure;
- hidden target paths and withheld relation combinations;
- future/unobserved events;
- corruption and outage schedules;
- split labels, oracle candidate ranking and expected witness IDs.

The generator must emit model and evaluator views separately. Tests must deliberately place future-observed, expired, wrong-context, wrong-type, out-of-order and gap-violating events in the world. No such event may leak through cached candidate lists, calibration, context routing or readout.

## 6. Experimental design

### G1 — composition and witnesses
- Path depths: 2, 3 and 4 edges.
- Include unique paths, multiple valid witnesses sharing endpoints, competing paths, disconnected paths, wrong-type edges, repeated relation IDs and no-path queries.
- Hold out relation-type combinations at test time while retaining the declared type vocabulary. This is compositional generalisation, not E08 domain transfer.
- Evaluate candidate path selection separately from reference witness validity.

### G2 — temporal robustness and outages
- Vary event age, observation delay, validity expiry, context mismatch, missing observations and outage duration.
- Include clean-learn-then-outage and learn-during-corruption as separate conditions.
- Evaluate A trace decay and B store persistence without treating persistence alone as correct retrieval: B must still obey current validity and observation cutoffs.

### G3 — path selection and abstention
- Provide competing valid/invalid paths, ambiguity, incomplete evidence and capacity pressure.
- Require selection among learner-generated candidates or explicit abstention.
- Measure false-path selection, missed valid paths, correct abstention and unjustified abstention separately.

### G4 — adaptation, revision and recovery
- Use the adopted G3 synthetic stable, gradual-change and abrupt-change environments, fixed topology and threshold 24.
- Preserve the 32/32/64 fit/validation/post-promotion windows where the M3 candidate lifecycle is used, unless a separately versioned protocol amendment justifies a change.
- Compare validated revision against no revision. Keep gradual and abrupt results separate.
- Include contradictory observations, candidate rejection, promotion degradation, rollback, dormancy, reactivation and outage/recovery.
- Verify rollback restores the complete declared trusted snapshot, including all persistent A/B state and lifecycle metadata.

### G5 — resources and scaling
Report persistent state bytes, parameter count/bytes, update operation counts, query operation counts, and wall-clock latency separately. Include populated state and serialization/container overhead. Report native operating points and a matched-budget frontier. Do not claim exact resource matching from state bytes alone.

## 7. Splits, seeds and statistical unit

- Use 20 independent generated world configurations as the primary clustered units, preserving the 20-world convention of the adopted G3 adaptation evidence.
- Split by world and relational-combination family, not by randomly splitting near-duplicate episodes from one world.
- Use separate fit, calibration/validation and held-out test partitions. Calibration and validation worlds are not test worlds.
- Both architectures receive identical training streams, observation order, query sets, cutoffs and seed/world manifests.
- Use paired world-level comparisons and a 95% world-clustered confidence interval. Report every world-level result, not only pooled episode means.
- Record generator version, seed manifest, split manifest, configuration and source commit before confirmatory execution.

## 8. Metrics

Report independently:
- retention/availability of previously observed evidence;
- retrieval recall and precision;
- entity/relation binding accuracy;
- path-selection exact accuracy;
- witness exactness and witness coverage;
- invalid/false composition rate;
- correct and unjustified abstention;
- operator/readout error where relevant;
- first-failure category (retention, retrieval, binding, path selection, operator application, composition, readout);
- adaptation loss, detection delay, false alarms, promotions/rejections and rollback integrity;
- persistent bytes, parameter count, update/query operations and latency.

Do not combine these into one opaque score. Distinguish oracle/reference semantics from learned selection throughout.

## 9. Stability and lifecycle model

The integrated state must explicitly account for:
[
X_t=(m_t,r_t,c_t,	heta_t,e_t,d_t,k_t,q_t),
]
where (m_t) is SOE temporal state, (r_t) is the B relation store (absent for A), (c_t) is context/acquisition state, (	heta_t) is readout/estimator state, (e_t) is evidence/activation state, (d_t) is detector state, (k_t) is candidate lifecycle/trusted snapshot state, and (q_t) is resource/capacity state.

The update order is prequential: construct prediction from the state available before the current target feedback; score; then update memory, estimator, evidence and detector in the frozen order. Missing observations are not encoded as observed zeros.

The P6 adapter must:
- use the actual A/B state, not a detached two-vector surrogate;
- preserve the G3 threshold-24 detector policy;
- separate candidate fitting from independent validation;
- promote only on identifiability and held-out validation improvement;
- preserve the incumbent and full trusted snapshot;
- restore the complete trusted snapshot on rollback;
- model dormancy/reactivation explicitly;
- test stable, gradual and abrupt conditions, plus bounded switching/outage stress within the declared envelope.

A finite-horizon pass is not a global stability theorem. The integrated envelope and state-norm limits must be calculated from the final state contract and bounded-input specification before confirmatory runs; Job 3's norm 25 is not transferable without derivation.

## 10. Reproducibility and evidence

- Python 3.10 and 3.12 supported test matrix.
- Deterministic seeded generators and stable ordering.
- Raw per-world/per-query outputs, aggregate summaries, configuration, source SHA, environment versions and artifact manifest.
- SHA-256 for every result artifact and verifier output.
- Verifier checks required files, schemas, seeds, split identity, no missing/duplicate world rows, finite metrics and consistency between raw and aggregate results.
- Preserve failures and invalid harness attempts with explicit status; never overwrite historical evidence.

## 11. Acceptance and claim boundary

The accompanying gate proposal defines the decision rules. No confirmatory M4 campaign is authorised by this protocol draft. After gate approval, implementation lanes A, B, common evaluation and P6 may run concurrently against the same contracts. Functional integration and confirmatory campaigns remain sequential dependencies.

A successful M4 result would establish only the tested fixed-topology synthetic A/B capabilities and operating envelope. It would not establish E08 transfer, topology emergence, arbitrary-depth composition, natural-language reasoning, Grassmannian advantage or global stability.
