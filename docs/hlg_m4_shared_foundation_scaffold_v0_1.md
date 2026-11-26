# HLG-M4 shared foundation scaffold

**Version:** 0.1 (provisional)
**Status:** Adopted working scaffold for independent P0/P5/P6 design jobs; not a frozen implementation API.
**Parent ledger:** [HLG-M4 pre-implementation research ledger](hlg_m4_preimplementation_ledger_v0_1.md)
**Purpose:** Provide one representation-neutral vocabulary and information boundary so parallel jobs can proceed without inventing incompatible task semantics.

## 1. Design constraints

1. Preserve the distinction between relational facts, relation instances, relation operators and representation-level transformations.
2. Keep learner-visible inputs separate from evaluator-only ground truth.
3. Preserve context, time and provenance where they affect relation validity.
4. Treat relation composition as ordered and typed unless a job proves a different algebra is required.
5. Do not prescribe graph, matrix, tensor, Grassmannian, neural or symbolic representation at scaffold stage.
6. Keep M3's ordered primitive-episode benchmark semantics separate from the relational/operator composition task defined here.
7. Make each capability observable independently; do not infer composition from retrieval or from a final answer alone.

## 2. Provisional object vocabulary

| Object | Provisional meaning | Notes |
|---|---|---|
| Entity | A typed identity participating in relations | Identity and type are part of the task contract. |
| Relation type | A typed predicate/operator family | Domain and codomain constrain valid arguments. |
| Relation instance | A particular evidenced relation between entities | Carries provenance, context and temporal validity. |
| Relation operator | A rule or transformation associated with a relation type | Not interchangeable with a stored fact. |
| Context | Conditions under which a relation or operator is applicable | May be observed, inferred or evaluator-only depending on task split. |
| Time | Event/order/validity information | Distinguish event time from observation time where needed. |
| Provenance | Source and evidence history for an instance | Supports conflict and revision analysis. |
| Witness | Evaluator-grounded intermediate entities and relation instances proving a path | Hidden from learner unless explicitly made part of a diagnostic condition. |
| Query | Learner-visible request with typed roles and conditions | Must not encode the answer path inadvertently. |
| Readout | Mapping from selected/composed result to an answer | Scored separately from internal path correctness. |

This vocabulary is provisional. P0 may refine or split objects if the task semantics require it.

## 3. Typed composition contract (provisional)

For entity types (A,B,C), relation instances (r_1:A\to B) and (r_2:B\to C) may compose only when their intermediate type/identity, context and temporal constraints are compatible.

At the extensional level:
\[
R_2\circ R_1=\{(a,c):\exists b,\ (a,b)\in R_1\land(b,c)\in R_2\}.
\]

The composition witness is not just the endpoint pair. It contains, at minimum, the intermediate entity identity and the specific relation instances used. Where multiple witnesses exist, the evaluator records all valid witnesses or an explicit equivalence/selection rule.

A context/time admissibility predicate may constrain composition:
\[
\mathcal A(r_1,r_2;c,t_1,t_2)\in\{0,1\}.
\]
P0 must decide whether admissibility is local to adjacent edges, global to a path, or both. No associativity claim is assumed for context-sensitive composition until these conditions are specified.

Operator composition is a separate object:
\[
T_{21}=T_2\circ T_1.
\]
The semantic validity of the result must be established against independently held relational truth; an operator product is not itself a ground-truth witness.

## 4. Learner/evaluator information boundary

### Learner may receive (as defined by each task condition)
- entity observations and type information;
- observed relation instances and their allowed metadata;
- query and context features;
- temporal/event observations and explicit missingness signals;
- its own persistent state and permitted feedback.

### Evaluator retains
- complete ground-truth relation inventory and validity conditions;
- hidden intermediate witnesses and all valid/invalid paths;
- hidden labels for held-out relations/compositions;
- scoring rules, split assignments and diagnostic-oracle answers;
- task-generation seeds and audit metadata.

The evaluator must not expose hidden witnesses, future labels, answer paths or oracle outputs through task IDs, ordering, metadata, file names, timing side channels or benchmark-generation artifacts. Any deliberate oracle condition is a separately labelled diagnostic arm and is never learner acceptance evidence.

## 5. Observable capability ladder

| Layer | Capability | Minimum observable evidence |
|---|---|---|
| L1 | Retention | Relevant relation instance remains available after a controlled delay/interference condition. |
| L2 | Retrieval | Query retrieves the correct stored instance(s), with distractors controlled. |
| L3 | Binding | Correctly binds entity identities, roles, relation types and context. |
| L4 | Path selection | Selects valid ordered path(s) among competing candidates. |
| L5 | Primitive operator application | Applies a specified primitive relation/operator to the correct typed arguments. |
| L6 | Multi-relation composition | Produces a valid endpoint and independently verifiable witness for a multi-edge path. |
| L7 | Readout | Converts the internally selected/composed result into the required answer format. |

The ladder is an evidence/claim hierarchy, not a mandatory software decomposition. A task may isolate one layer or combine layers, but the report must identify which layers are being tested.

## 6. State boundary for architecture and stability analysis

The following are conceptual state roles, not commitments to separate memory modules:

- **Temporal state (s_t):** retained event/history information and temporal traces.
- **Relational state (z_t):** persistent relational organisation, relation-instance/operator associations and structural support.
- **Context/routing state (c_t):** current context, state selection and routing information.
- **Evidence/activation state (e_t):** support, confidence, eligibility, activation and dormancy information.
- **Adaptation/control state (d_t,k_t):** detection, candidate fitting, validation, promotion, rollback and resource-control state.

Each job must specify which roles are present, observable, persistent, updated and independently reset in each architecture. A variable may be represented within another state; conceptual separation does not mandate physical separation.

## 7. Architecture hypotheses (labels only)

- **A — SOE-only:** no separately maintained relational state; relational capability must emerge through temporal state dynamics and learned readout.
- **B — coupled:** temporal and relational state have distinguishable persistence/update semantics and explicit interaction.
- **C — unified augmented:** one jointly updated augmented state, with its coupling and retention rules specified.
- **R — relational-only reference:** relational state without the temporal-memory mechanism under investigation.

The labels do not imply a winner. P5 must define operationally testable implementations and matched budgets. Merely concatenating state vectors does not establish a distinct architecture.

## 8. Required task axes and exclusions

Every proposed M4 task must state:
- whether the path is supplied or must be selected;
- number of relation steps and whether relation types are homogeneous/heterogeneous;
- whether intermediate entities are observed, hidden or partially observed;
- context and temporal validity conditions;
- distractor, ambiguity and competing-witness conditions;
- missingness/outage/recovery conditions;
- whether the task tests retention, retrieval, binding, path selection, operator application, composition or readout;
- what is learner-visible and evaluator-only.

Initial tasks should use a bounded controlled relational world and explicitly specified paths to isolate binding/operator application/composition before adding path selection. Noise, competing paths, missingness, controlled relation change and transfer are introduced only when justified by P1-P4 and included in the frozen operating envelope.

Out of scope unless explicitly justified and approved: unrestricted topology birth/death, arbitrary asynchronous updates, unrestricted nonlinear operator learning and claims of broad cross-domain transfer.

## 9. Open decisions assigned to jobs

- **P0:** exact type system, witness representation, temporal/context admissibility, path semantics, ambiguity and associativity conditions.
- **P1:** diagnostic oracle/control matrix and non-leakage audit.
- **P2:** whether bounded candidate acquisition belongs in M4; if yes, its bounded interface and metrics.
- **P3:** minimum interruption/recovery challenge not already covered by M3.
- **P4:** whether a structurally distinct transfer challenge is necessary for M4 stability claims or should remain deferred.
- **P5:** operational A/B/C/R update contracts, budgets and C0-C4 reuse.
- **P6:** full state transition model, mode guards, stability notions, proof obligations and counterexamples.

## 10. Change control

This scaffold may be revised by any job when evidence or a counterexample requires it. Changes must be recorded with rationale and impact on dependent jobs. No job may silently assume a changed contract. The fourth integration job resolves conflicts and freezes the final shared contract in the M4 implementation protocol.
