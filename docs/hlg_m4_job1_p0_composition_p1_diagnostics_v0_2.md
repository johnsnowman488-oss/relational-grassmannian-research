# M4 Job 1 — P0 composition semantics and P1 failure attribution (working draft v0.2)

**Status:** v0.2 post-code-audit design result; reviewable but not a frozen task contract.
**Parent issue:** [#33](https://github.com/johnsnowman488-oss/relational-grassmannian-research/issues/33)
**Foundation:** [M4 shared scaffold v0.2](hlg_m4_shared_foundation_scaffold_v0_2.md)

## 1. Main conclusion

M4 must not define composition as “the model returned the correct endpoint.” A composition claim requires a valid, ordered, typed path and an independently checkable witness. The endpoint, path, relation instances, context/time admissibility and answer readout must be scored separately.

The first benchmark should supply the relation-type sequence while withholding the intermediate entity identities and witness. This isolates retrieval/binding/operator application/composition from path selection. A second task condition may withhold the path sequence and require selection among competing paths. These conditions must not be collapsed into one headline metric.

## 2. Formal objects

Let each entity (v\) have a type \(\tau_V(v)\). Let a relation type \(r\) have a domain and codomain:
\[
r:A\to B.
\]
A relation instance is
\[
e=(id,r,a,b,\kappa,t_v,t_o,p,\eta),
\]
where:
- (id\) is a stable instance identifier;
- (r\) is the relation type;
- (a,b\) are typed endpoint identities;
- \(\kappa\) is context;
- \(t_v\) is validity/event time (or interval);
- \(t_o\) is observation time;
- (p\) is provenance;
- \(\eta\) is evidence/quality metadata.

An instance is admissible for query context \((\kappa_q,t_q)\) only under an explicit predicate:
\[
\operatorname{Valid}(e;\kappa_q,t_q)\in\{0,1\}.
\]
This predicate may include context compatibility, temporal validity, provenance quality and task-specific rules. It must be part of the evaluator contract and only the allowed features may be exposed to the learner.

A path schema is an ordered typed sequence
\[
\pi=(r_1:A_0\to A_1,\ldots,r_n:A_{n-1}\to A_n).
\]
A witness is an ordered sequence
\[
\omega=(v_0,e_1,v_1,\ldots,e_n,v_n)
\]
such that each edge instance (e_i\) has relation type (r_i\), endpoints ((v_{i-1},v_i)\), compatible types, and passes the task's validity/admissibility rules. The output endpoint pair is not a substitute for \(\omega\).

## 3. Relational composition

For extensional relations (R_i\subseteq V_{i-1}\times V_i\), define:
\[
R_n\circ\cdots\circ R_1
=\{(v_0,v_n):\exists v_1,\ldots,v_{n-1},\ (v_{i-1},v_i)\in R_i\}.
\]
The witness set for endpoints is:
\[
\Omega_\pi(v_0,v_n)
=\{\omega:\omega\text{ satisfies }\pi\text{ and all validity rules}\}.
\]
This makes multiplicity explicit: several intermediate paths may support the same endpoint pair. The task must say whether success requires any valid witness, all valid witnesses, a ranked witness, or a particular canonical witness. The default diagnostic task should accept any valid witness and score path selection/ranking separately.

### Context and temporal admissibility

Do not insert a loosely defined pairwise predicate into the binary operator and then assume associativity. Instead define a path-level validity function:
\[
\operatorname{PathValid}(\omega;\kappa_q,t_q,\mathcal C),
\]
where \(\mathcal C\) contains explicit global constraints (e.g. compatible contexts across edges, temporal order, maximum gap, provenance restrictions). If all constraints are edge-local and independent of parenthesisation, ordinary relational composition remains associative. If validity depends on the whole path, the mathematical relation join can remain associative while the *filtered task semantics* may not be representable as an associative binary operator. This is a real design decision for P0, not an implementation detail.

### Associativity conditions

For ordinary set-valued relations with compatible types, relational composition is associative:
\[
(R_3\circ R_2)\circ R_1=R_3\circ(R_2\circ R_1).
\]
This relies on existential joining over the same intermediate identities and no grouping-dependent side condition.

Associativity can fail at the task/operator level if:
- intermediate composition discards witness/provenance needed by later constraints;
- admissibility is evaluated differently at intermediate grouping boundaries;
- context is updated by a non-associative stateful rule;
- temporal windows are truncated or re-anchored after each binary composition;
- a learned operator approximation is not functionally associative.

Therefore retain both the exact extensional reference semantics and the implemented/learned operator semantics. Test associativity explicitly rather than assuming it.

## 4. Relational versus operator composition

Relational composition joins evidenced instances. Operator composition composes functions:
\[
T_{21}=T_2\circ T_1,\qquad T_{21}(x)=T_2(T_1(x)).
\]
The operator may act on a representation or latent state. Its output can be numerically well-formed and still fail to correspond to any valid relation-instance witness. Evaluation must therefore include:
1. operator output quality;
2. whether a valid relational witness exists;
3. whether the predicted witness matches one of the evaluator's valid witnesses;
4. whether the final readout is correct.

An algebraic product of matrices/subspaces/operators is not semantic proof of a relation.

## 5. Staged task contract

### Task A — supplied path schema, hidden witness

Learner receives:
- start entity and its public type;
- ordered relation-type sequence \(\pi\);
- permitted observations of relation instances and metadata;
- query context/time features and explicit missingness markers.

Learner does not receive:
- intermediate entity identities;
- hidden witness sequence;
- complete ground-truth relation inventory;
- future/held-out labels or evaluator path enumeration.

Learner must return endpoint candidate(s), a witness or witness reference assembled from learner-accessible evidence, and calibrated uncertainty/abstention where supported.

This task isolates multi-hop binding and composition conditional on the path schema. It does not establish path selection.

### Task B — path selection plus composition

Learner receives a start entity, target/query constraints, context/time and the permitted evidence stream, but not the relation-type path. It must select a path and produce a valid witness and endpoint. Competing paths and distractors are introduced only after Task A is stable.

Task B adds path selection and must be reported separately from Task A.

### Task C — controlled change/revision

Only after A/B contracts are stable, introduce a relation change, invalidation or context shift. Score legitimate revision separately from collateral damage to unrelated retained relations. This condition connects P0 to P6 and should be included only if the P6 model needs it.

## 6. P1 failure attribution matrix

| Layer | Diagnostic question | Useful control/oracle | Interpretation limit |
|---|---|---|---|
| Retention | Was the required instance still represented after delay/interference? | Exact-fact probe; immediate-versus-delayed condition | Oracle retrieval does not prove learner retrieval. |
| Retrieval | Can the query recover the right instance among distractors? | Exact-instance retrieval oracle; shuffled distractors | Correct fact without correct role binding is not success. |
| Binding | Are endpoint identities, roles, relation type and context correctly bound? | No-binding / role-shuffle control | Supplied binding is an upper bound, not learned binding evidence. |
| Path selection | Is the selected ordered relation sequence valid? | Supplied-path Task A versus hidden-path Task B | Task A cannot support a path-selection claim. |
| Operator application | Does the primitive operator act on the correct typed arguments? | Exact-operator oracle; primitive-only task | Correct operator output alone does not prove multi-hop composition. |
| Composition | Does a valid ordered witness connect start to endpoint? | Exact-witness oracle; order-destroyed control | Endpoint-only accuracy can conceal invalid paths. |
| Readout | Is the internally supported result rendered as the requested answer? | Oracle readout from learner-provided witness | Oracle readout must not repair an invalid witness. |

Every oracle is a diagnostic upper bound. Oracle outputs must never enter the learner's persistent state or acceptance score.

## 7. Minimum metric bundle

Report at least:
- instance retention after delay/interference;
- query-conditioned instance retrieval precision/recall;
- role/entity/context binding accuracy;
- path validity and path-selection accuracy (Task B only);
- primitive operator error (where an operator is part of the model);
- endpoint accuracy conditional on valid witness;
- witness validity/precision/recall;
- readout accuracy conditional on correct witness;
- abstention and uncertainty calibration;
- false-path rate and ambiguity handling.

A single aggregate may be reported secondarily, but cannot replace the layer metrics.

## 8. Leakage and integrity checks

Before any confirmatory use, audit:
- identifiers, ordering, file paths and metadata for encoded labels;
- whether query wording reveals intermediate nodes or path order beyond the intended schema;
- train/validation/test overlap in entities, relation instances, templates and generator seeds;
- whether hidden evaluator structures are imported by learner code;
- whether oracle conditions can accidentally be enabled in ordinary runs;
- whether scoring accepts endpoint-only answers without witness evidence.

## 9. Open decisions for reconciliation

1. Are relation instances point-valid, interval-valid or event-valid? The first implementation should choose one explicit convention.
2. Is context compatibility edge-local, path-global or both?
3. For multiple valid witnesses, is any-witness success sufficient for the primary metric, with ranking as a secondary metric?
4. Does the first operator task require learned operators, or should exact primitive operators be supplied to isolate relational composition? The cleanest first pass is likely supplied exact primitives with separate operator-learning deferred.
5. Which existing M3 controls can be reused directly without changing their benchmark semantics?

## 10. Current result

P0 now has a candidate mathematical contract and a layered task design. P1 has a diagnostic matrix and leakage checklist. This is a working design result only: no benchmark implementation, empirical run, associativity proof for a context-dependent learned operator, or M4 acceptance result is claimed.


## 11. Cross-check against existing relational and operator primitives

### Existing repository implementation

The P0 task must reuse and distinguish three already-present forms of composition.

| Existing primitive | Actual contract | What it does not establish |
|---|---|---|
| \`rgm.relations.RelationEvent\` / \`RelationalGraph\` | Event assertion with string subject, predicate, object, timestamp, optional half-open expiry, event ID and supersession; graph supports active-at-time queries and functional-predicate contradiction checks. | Endpoint types, context, observation time, rich provenance, query-conditioned path binding or composition witnesses. |
| \`RelationSchema.compositions\` / \`compose_relations\` | Explicit ordered predicate-pair lookup; requires \`first.object == second.subject\`; derived event timestamp cannot precede either input and must be before the earliest expiry. | General path enumeration, multiple-witness management or retention of the source event sequence. The returned derived event does not contain the input event IDs as a witness/provenance chain. |
| \`rgm.leptograph.m1.compose_routes\` | Dimension-compatible linear-map chain in traversal order, computed as \`K_n @ ... @ K_2 @ K_1\`; M1 tests establish coordinate/basis covariance for this operator product. | Semantic truth of a relation path or evidence that a chain of relation instances exists. |

Existing regression coverage in \`tests/test_relations.py\` verifies endpoint connectivity, explicit predicate rules, temporal validity, graph revision and contradiction handling. \`tests/test_leptograph_m1.py\` verifies heterogeneous linear-map route composition and covariance. Reuse these tests and APIs as the starting reference; do not recreate their already-tested narrow contracts.

### Required P0 semantic separation

P0 v0.2 makes the following distinction explicit:

1. **Extensional path composition:** join relation instances through matching intermediate entity identities and return a witness containing the edge/event IDs and intermediate entities. This is the primary semantic composition target.
2. **Schema-level predicate algebra:** map an ordered pair of predicate names to a composed predicate name. This is a declared symbolic rule and may be useful for validating or labelling a path, but it is not the witness itself.
3. **Representation/operator composition:** compose linear maps or learned operators. This is evaluated separately against relation-instance truth and a valid witness.

The current \`RelationEvent\` API has no endpoint type registry. P0 should introduce the minimum typed-domain/codomain contract at the path/task layer, or in an explicit schema registry, without requiring a disruptive rewrite of the legacy event record. Likewise, context and richer provenance should be optional task metadata only where the M4 task requires them.

### Temporal compatibility

Preserve the current event-validity convention: validity is half-open, \([timestamp, valid\_until)\). The existing binary compose helper chooses \(\max(t_1,t_2)\) by default and intersects expiry by the minimum finite expiry. For a multi-edge path, P0 must define whether all edges must be simultaneously valid at query time or whether an ordered event-time path is admissible under a separate temporal rule. Do not substitute event time for observation time; the current event record has no distinct observation-time field.

### Associativity correction

Ordinary extensional relational joins are associative for type-compatible relations when the same witness set and constraints are preserved. This does not imply that every \`RelationSchema.compositions\` table is associative. A declared predicate operation must separately satisfy
\[
(r_3\star r_2)\star r_1=r_3\star(r_2\star r_1)
\]
for all admissible triples (with domain/codomain compatibility); current tests demonstrate only one binary rule and do not establish this law. Grouping-dependent temporal/context filters or witness-discarding intermediate records can also make a filtered task operator non-associative.

### Consequences for the first task

Use the current event graph as an input/reference source if useful, but return a separate witness-bearing path object rather than relying on the lossy derived \`RelationEvent\` alone. A composed predicate label may be returned as a secondary field. Supplied-path Task A must still require the learner to recover intermediate identities and source event instances; Task B may add path selection. The evaluator retains the complete witness inventory.

**Current P0 audit decision:** existing primitives pass their original narrow contracts and should be reused. They do not yet satisfy the full P0 witness, type, context and leakage contract; implement those as bounded M4 task-layer extensions, not as retroactive M0-M2 changes.
