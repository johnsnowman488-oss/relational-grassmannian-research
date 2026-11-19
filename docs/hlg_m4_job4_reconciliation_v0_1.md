# HLG-M4 Job 4 implementation reconciliation — v0.1

**Date:** 2026-11-19  
**Repository:** `johnsnowman488-oss/relational-grassmannian-research`  
**Purpose:** Reconcile the actual Job 1–3 code and preliminary evidence before freezing the A/B implementation protocol.  
**Status:** Source audit complete; protocol and gate proposal prepared for review. No confirmatory M4 campaign has run.

## 1. Executive disposition

Jobs 1–3 are real, independently implemented work packages with focused tests, preliminary runners, uploaded artifacts, and successful Python 3.10/3.12 regression runs. Their PRs remain open and mergeable:

| Job | PR / head | Implemented scope | Reconciliation disposition |
|---|---|---|---|
| Job 1 P0/P1 | [#37](https://github.com/johnsnowman488-oss/relational-grassmannian-research/pull/37), `db4f98463059f564f3679721ca836793164539fa` | Typed relation instances, ordered extensional path composition, witnesses, temporal/context/cutoff filters, first-failure attribution | Accept as the **reference semantics and diagnostic foundation**, subject to the contract clarifications in §2. |
| Job 2 P5/P2–P4 | [#38](https://github.com/johnsnowman488-oss/relational-grassmannian-research/pull/38), `e297b449528ff803017b586277e27abdadc26174` | Operational A/B/C/R memory variants, bounded context acquisition, outage advancement, joint retrieval microtask | Accept as **preliminary mechanism code and diagnostic evidence only**. Its B store and task are not yet the M4 typed relational learner/composition system. |
| Job 3 P6 | [#39](https://github.com/johnsnowman488-oss/relational-grassmannian-research/pull/39), `efe43695086a9d38985325ad01f948a10ca14ce4` | Synchronous coupled-state reference model, detector/revision lifecycle, finite-horizon stress and rollback tests | Accept as a **P6 prototype and counterexample set**, not as the A/B integrated stability implementation. |

The three PRs have no submitted GitHub reviews or inline review threads at this audit point. Their CI is green, but green CI is not a code-review disposition and does not imply the scientific claims have passed.

**Job 4 consequence:** preserve the PRs open for their own review/merge decisions. Use their code as the implementation starting point. Do not merge them merely to close this issue. The A/B implementation must be integrated through the frozen shared contracts, and the P6 prototype must be adapted to the actual A/B state.

## 2. P0/P1 reconciliation — Job 1

### Accepted semantics

The new task-layer API is appropriately separate from legacy relation and M1 operator APIs. It represents typed entities, relation types and relation instances, including event time, observation time, context, expiry and provenance. The reference path runner preserves the full entity sequence and relation-instance IDs. It applies:
- endpoint type compatibility;
- exact context match, with global (`None`) facts allowed;
- half-open validity interval `[event_time, valid_until)`;
- explicit observation cutoff;
- nondecreasing event-time order and optional maximum event gap;
- identity-preserving binary extensional joins.

The tests cover a three-edge witness, future-observed and expired facts, context and event-order filtering, invalid type chains, ordinary extensional join associativity, and multiple witnesses sharing one endpoint.

### Clarifications required in the shared contract

1. **Reference path versus learned path:** `CompositionQuery.relation_path` supplies a relation sequence. That is a reference-semantics query, not a learned path-discovery interface. The M4 learner-facing query must not disclose the planted relation sequence. It should expose only the declared start/goal/context/time/cutoff/depth constraints; the learner proposes candidate relation paths, which the shared composition engine then validates.
2. **Witness validation:** validate witness shape and internal consistency (entity count, edge count, endpoint continuity, relation-type sequence, unique instance IDs) at construction or at the shared verifier boundary. The current dataclass permits manually constructed inconsistent witnesses.
3. **Time semantics:** preserve the current independent meanings of event time, observation time, query time and observation cutoff. The protocol must state whether the cutoff is constrained to be no later than query time. Never silently collapse these clocks.
4. **Composition law:** the tested associativity is for ordinary extensional witness joins. It is not a proof that arbitrary predicate-composition tables or learned operators are associative.
5. **Provenance:** the field is currently carried but not interpreted by the runner. Define it as audit metadata, not a hidden truth label or an implicit learner input.

These are contract refinements for M4, not reasons to discard the working reference implementation.

## 3. P5 architecture reconciliation — Job 2

### What is actually implemented

- **A:** fixed SOE channels encode relation-value and mode features; learned scalar gains read them out.
- **B:** the same SOE mode trace plus a separate Python dictionary mapping relation IDs directly to scalar values.
- **C:** one decaying unified vector.
- **R:** relation dictionary only.
- P2 wraps the existing bounded `ContextBank`; P3 advances temporal traces through an outage while leaving B/R relation dictionaries unchanged; P4 transfer is deferred to E08.

The implementation is a useful controlled probe of temporal trace versus explicit scalar persistence. It is not yet a typed relation-instance store, a path candidate generator, a witness-preserving relational composition learner, or an end-to-end A/B implementation.

### Preliminary result interpretation

The reported B zero MSE is structurally expected for this microtask: B writes the target relation value directly into `relations[relation_id]` and reads that same value back, while the target is defined as that stored value plus a mode term. This verifies that an explicit persistent scalar store can preserve the supplied scalar in this task. It does **not** demonstrate learned relational retrieval, competing-path selection, multi-edge composition, unseen-combination generalisation, or a general B advantage.

A's non-monotonic delay pattern is a diagnostic observation, not evidence of a failed general architecture. The runner's scalar readout/calibration and its selected mode coordinate should be checked against the task target before any comparative claim.

### Required M4 disposition

- Retain A and B as the only primary architectures, per the adopted Job 4 plan.
- Keep C and R as historical/reference controls; do not expand them into primary implementation lanes.
- B's production relational store must hold typed relation instances and provenance/temporal metadata, not only `relation_id -> float`.
- A must use the same observation stream and task-visible information, but must not gain a separate persistent relation store.
- Both architectures must use the same learner-facing query contract, candidate/witness verifier and evaluator.
- Re-run the diagnostic microtask only if needed to explain a demonstrated implementation discrepancy; it is not a confirmatory architecture-selection campaign.

## 4. P6 reconciliation — Job 3

### What the prototype establishes

The prototype implements a synchronous discrete-time two-dimensional state coupled to an SOE trace, a CUSUM detector, M3 candidate revision and evidence activation. Its tests exercise a finite-horizon bounded-input sample, a coupled unstable counterexample despite stable diagonal blocks, candidate promotion/rejection, operator rollback, dormancy/reactivation and a switched-product counterexample.

The 20-seed × 300-step runner reports finite-horizon norms, detector alarms, independent fit/validation losses and restoration of the prior accepted operator in the promoted cases. The claim boundary correctly excludes arbitrary-switching and global stability theorems.

### Why it is not yet the M4 A/B stability model

1. The state is a fixed two-vector plus a two-feature SOE memory; it does not contain the actual A readout state or B relation store.
2. The boundedness check is applied to the two-vector norm, not to the complete temporal, relational, context, estimator, evidence, detector, candidate and resource state.
3. The trusted snapshot contains only `accepted_operator`; it does not snapshot/restore the full A/B system state, relation-store contents, temporal traces, context state, sufficient statistics, detector/evidence state or lifecycle metadata.
4. The prototype's `FIT/VALIDATE` path is simpler than the actual M3 integrated-refinement harness, which has ordered context decisions, active-source gates, prequential predictions/updates, residual detection, and `WAITING/TRAIN/VALIDATE/DONE` candidate phases. The separate M3 candidate lifecycle also uses 32/32/64 fit/validation/post-promotion windows.
5. The prototype uses a default CUSUM threshold of 2.0. The adopted G3 validated-revision policy for M4 entry uses threshold 24. The operating policy must be explicit and the two values must not be conflated.

### Required M4 disposition

P6 is a reusable mechanism prototype, not the integrated stability proof. The M4 P6 lane must adapt it to the actual A/B state and transition contract, include the selected G3 policy (threshold 24) unless a separately justified protocol change is accepted, and test complete trusted-state snapshot/rollback. Any finite-horizon boundedness envelope must be derived for the integrated state and declared inputs before confirmatory runs; the prototype's norm bound 25 cannot simply be transferred to a different state space.

## 5. Cross-cutting contracts

The integrated A/B system must preserve the following distinctions.

### Information and query boundary
- Model-visible: observations actually received, event/observation timestamps, typed fields made available by the task, context evidence and query constraints.
- Evaluator-only: planted world graph, hidden target path, unobserved/future events, split membership labels, corruption schedule and oracle candidate ranking.
- The learner-facing query does not include the hidden relation sequence. Oracle/reference path enumeration is a separate diagnostic mode.
- No data observed after the declared cutoff may affect candidate generation, ranking, memory updates or readout for that query.

### Shared pipeline
Observation/event ingestion → architecture-specific memory update → learner-facing query → candidate retrieval → learned path selection or explicit abstention → shared witness-preserving composition/validation → readout and P1 first-failure attribution.

### Shared data contracts
- Relation instance: stable instance ID, typed subject/object, relation type, event time, observed-at time, optional context, half-open expiry and provenance.
- Query: start/goal constraints, context, query time, observation cutoff, maximum path depth and declared temporal constraints.
- Candidate: ordered relation-type path plus any entity/instance bindings the learner commits to.
- Result: selected path or abstention, endpoint, full ordered witness, score/confidence if defined, and diagnostics.
- Architecture adapters expose `observe`, `advance_gap`, `query`, `snapshot`, `restore` and `resource_snapshot` against one versioned contract.

### Architecture-specific boundary
- A's persistent learned state is the SOE temporal memory plus its fitted relational readout parameters. It may use transient input batches during an update, but it must not retain a separate explicit relation-instance graph/store.
- B's state is SOE temporal memory plus a distinct persistent typed relation-instance store. The store must preserve identity and temporal/provenance metadata and expose only records visible under the query cutoff.
- The common composer validates candidate paths and witnesses; it must not choose the learner's path on the learner's behalf.

## 6. Resource and experimental comparability

The current P5 resource report uses empty-state byte counts. It therefore does not measure the populated B dictionary, its Python/container overhead, or the full state required by A/B. The cross-audit of C0-C4 also shows that equal state bytes did not imply equal parameter counts or update/query work.

M4 must report separately:
1. persistent state bytes, including populated relation-store entries and declared container/serialization overhead;
2. trainable parameter count and parameter bytes;
3. update work (operation counts with a documented convention);
4. query work;
5. wall-clock update/query latency with fixed hardware/software conditions.

Report both:
- **native operating point:** each architecture's actual resource use;
- **matched-budget frontier:** compare at common declared parameter/state/compute budgets, without silently truncating or dropping B's relation records.

If an exact match is impossible because one architecture's representation has irreducible storage overhead, show the Pareto frontier and state the mismatch. Do not call the comparison resource-matched merely because one scalar budget is equal.

## 7. Adaptation policy and M4 operating envelope

The 18 November user-authorised amendment in `docs/hlg_m3_adaptation_gate_revision_v0_1.md` establishes M4 entry under the G3-defined policy:
- detector threshold 24;
- fixed candidate topology;
- stable, gradual-change and abrupt-change synthetic environments;
- at least 2% relative reduction in post-change loss versus no revision, separately in gradual and abrupt environments;
- paired 95% world-clustered CI lower bound above zero and positive effects in at least 15/20 held-out worlds in each changing environment;
- stable negative control: zero detector alarms and zero candidate promotions.

The existing G3 evidence meets this revised **M4 entry** criterion. It does not automatically establish the integrated A/B system's M4 exit criterion. M4 must run the adopted policy against the actual integrated A/B state and retain the distinction between gradual and abrupt regime behaviour. The original G2 adaptation failure remains unchanged.

## 8. CI and artifact audit

The current PR heads have completed the focused workflows and full repository test matrices:

| Job | Focused workflow | Full regression workflow | Artifact IDs (Python 3.10 / 3.12) |
|---|---:|---:|---|
| Job 1 | [44557934266](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44557934266) | [44557934433](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44557934433) | 14544749505 / 14546047579 |
| Job 2 | [44557953487](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44557953487) | [44557953690](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44557953690) | 14545228933 / 14545668323 |
| Job 3 | [44558021147](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44558021147) | [44558020970](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44558020970) | 14545049297 / 14545059245 |

All six workflows completed successfully. Both Python versions passed each focused test suite and full repository regression suite. Artifact digests are recorded in the context ledger and GitHub Actions artifact metadata. No M4 confirmatory campaign is represented by these workflows.

## 9. Decisions carried into the protocol

1. A/B only as primary architectures; B is a leading hypothesis, not a preselected winner.
2. C/R remain reference controls unless a specific reconciliation issue requires a bounded diagnostic.
3. Job 1 composition is the shared reference validator; learned path generation/selection remains a separate learner obligation.
4. Job 2's B exact-fit result is not architecture-selection evidence.
5. Job 3 P6 is a prototype; complete A/B state, transition and rollback integration is required.
6. P4 transfer remains deferred to E08.
7. M4 remains fixed-topology and within the adopted G3 synthetic operating envelope; no broad transfer, topology emergence or global-stability claim.
8. No confirmatory M4 campaign until the protocol and acceptance gate are reviewed and frozen.

## 10. Exit disposition

The source-level reconciliation is complete enough to define the A/B implementation interfaces and the required corrective integration work. It does **not** mean Jobs 1–3 PRs are merged, that the P5 learner is complete, or that P6 is already integrated.

The accompanying implementation protocol and gate proposal are the remaining reviewable M4 pre-implementation deliverables. Once those are accepted, Job 4 can be closed as a **pre-implementation protocol/gate completion**. M4 itself remains open until the integrated implementation and confirmatory evidence pass its gate.
