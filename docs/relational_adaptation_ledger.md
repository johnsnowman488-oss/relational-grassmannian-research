# Relational adaptation research ledger

**Ledger date:** 2026-11-14  
**Status:** Research direction agreed; E03 specification is the next design task.  
**Relationship to Aberconics/D2C:** This programme is motivated in part by capabilities exposed as missing during D2C experiments. The present repository remains an independent experimental track; this ledger does not assert that any proposed representation has already been integrated into D2C.

## 1. Research motivation

The E01/E02 investigations exposed an important distinction for adaptive systems, especially systems intended for advanced reasoning:

- Retaining observations over time is not the same as preserving the relational organisation that gives those observations meaning.
- Retaining individual relation-like signals does not guarantee that the system preserves relation identity, dependencies, or the conditions under which relations can be composed.
- An explicit graph can solve tasks whose relations are directly supplied as typed edges, but that does not establish open-ended relation discovery or general relational reasoning.
- A system intended to adapt across diverse tasks should be able to learn relational organisation rather than depend entirely on manually prescribed, task-specific relational operators.

The central capability under investigation is:

> Can an adaptive system discover, preserve, compose, revise and reorganise relational structure from experience, and transfer that capability to unfamiliar tasks?

This is a research question, not an established capability of the current SOE or geometric implementation.

## 2. Conceptual decomposition

Keep three functions distinct when designing experiments:

1. **Temporal memory** — what has happened, what persists, and how past context influences current processing.
2. **Relational organisation** — how entities, events, attributes, configurations and constraints are related or depend on one another.
3. **Relational dynamics** — how that organisation is discovered, composed, revised, reorganised and learned over time.

D2C's hierarchy introduces another axis: multiple temporal scales and top-down predictive context. Hierarchical levels must not be confused with different representational types.

A geometric substrate is a candidate inductive bias and representation, not a complete relational learning mechanism. It must still be shown how observations map into it, how relational organisation is learned, and how composition and revision occur.

## 3. Architectural hypotheses — deliberately unresolved

Do not assume that D2C necessarily requires two independent persistent states. Compare:

- **A — SOE-only:** temporal memory with learned readouts/dynamics that discover and express relational organisation.
- **B — coupled states:** SOE temporal memory plus a separate learned relational state, potentially geometric.
- **C — unified state:** an augmented dynamical-geometric state jointly maintains temporal and relational information.

A graph may be learned or manually specified; geometry may still encode task-specific assumptions. The fair comparison is therefore between different inductive biases and learning procedures, not simply “manual graph versus automatic geometry.”

The explicit graph remains a useful reference/control representation. It is not selected as the permanent D2C architecture.

## 4. Experimental programme

### E01–E02 — Initial relational-memory investigation

| Experiment | Question / contribution | Status |
|---|---|---|
| E01 | Can fixed SOE temporal memory support relational retrieval and composition under controlled synthetic conditions? | Complete; evidence archived on main |
| E02-A | Can an event-only interface and observed-event graph be specified with leakage-safe boundaries? | CI evidence exists on open PR branches; integration pending |
| E02-B | How does explicit event-derived graph retrieval compare with the E01 dense-memory baseline? | CI campaign reported complete on PR #12; review/integration pending |
| E02-C | Does graph-plus-temporal-memory help under clean, missing, spurious and mixed observations? | CI campaign reported complete on PR #12; review/integration pending |

**E01 interpretation boundary:** The experiments are synthetic and task-specific. They identify support loss, duplicate-event accumulation and false-path competition in the tested memory/readout. They do not establish general relational reasoning or a Grassmannian advantage.

**E02 interpretation boundary:** A graph result is evidence about retrieval/composition when observed facts are explicitly represented as edges. It is not evidence of relation discovery. Graph storage is not information-capacity matched to a fixed-size memory state. The E02-C corruption design, as currently described, corrupts the observations before graph and memory receive them; it does not establish recovery from a clean relational state retained before a later observation outage.

**Integration note (2026-11-14):** PR #12 (e02-event-graph) and PR #13 (e02-explicit-graph-memory) are both open against main and share paths including .github/workflows/e02.yml and docs/e02_protocol.md. PR #12 contains the full E02-B/C campaign and its own event-derived graph implementation. PR #13 adds a standalone ObservedEventGraph abstraction and a separate contract/workflow. They are independent branches, not a stacked implementation. Do not merge both blindly; reconcile the interface, workflow, protocol and tests first. CI success on a branch is not equivalent to integration into main.

### E03 — Relational task diversity and representation challenge

**Purpose:** Establish a benchmark that does not quietly favour graphs, vectors or geometry.

Include at least:
- explicit relations: ownership, location, ordering, dependency and connection;
- higher-order relations: multi-entity configurations, shared constraints and interactions;
- continuous/changing relations: similarity, influence, proximity, transformations and evolving dependencies.

**Question:** Can one relational learning mechanism operate across fundamentally different task structures?

**Evidence:** A controlled task suite with known ground truth, complexity levels, train/test splits, and tests separating fact retrieval from relational reasoning.

### E04 — Relational structure discovery

**Purpose:** Test whether relational organisation can be learned from observations without supplying a complete relational schema.

Compare:
- manually specified relational structures;
- learned graph structures;
- learned non-geometric relational representations;
- learned geometric representations.

**Question:** Can the system discover useful relations, configurations and dependencies rather than merely operate on relations supplied by the experiment designer?

**Evidence:** Discovery precision/recall, false-positive and false-negative structure, stability across seeds, and performance on withheld relation patterns.

### E05 — Relational composition and generalisation

**Purpose:** Test reusable composition beyond simple transitivity or fixed path templates.

**Question:** Can the system apply learned relational operations to unfamiliar combinations, higher-order configurations and longer chains?

**Evidence:** Held-out composition accuracy, compositional generalisation, false composition rate, and relational witness quality.

### E06 — Relational revision and structural adaptation

**Purpose:** Test changes to previously learned relationships.

Include:
- relations that change over time;
- contradictory observations;
- temporary versus persistent changes;
- new relations that invalidate earlier assumptions;
- local changes that should not destroy unrelated knowledge.

**Question:** Can the system revise relational organisation without manual reconstruction?

**Evidence:** Revision accuracy, stale-relation persistence, collateral loss, confidence calibration and adaptation cost.

### E07 — Partial observation, temporal gaps and recovery

**Purpose:** Separate learning under corrupted input from recovery using previously retained clean memory.

Test at least two distinct protocols:
1. corruption is present while the system first learns the relations;
2. the system first learns cleanly, then experiences an observation gap or degraded observation period and must use retained state.

**Question:** Does relational organisation survive interruption, and can it be updated when evidence returns?

**Evidence:** Retention, recovery, robustness, confidence calibration and interference.

### E08 — Cross-domain relational transfer

**Purpose:** Test whether learned relational mechanisms transfer beyond familiar surface features and task vocabularies.

**Question:** Does the system transfer relational capabilities to a new domain, or merely memorise familiar structures?

**Evidence:** Zero-shot and few-shot transfer, adaptation sample/compute cost, and performance on unseen relation configurations.

### E09 — Temporal memory and relational organisation cooperation

**Purpose:** Determine whether a separate relational state adds value beyond temporal memory and learned readout.

Compare A (SOE-only), B (coupled SOE plus relational state), and C (unified augmented state). Include a relational-only reference where useful.

**Question:** Is a distinct persistent relational state necessary or beneficial?

**Evidence:** Composition, retention, revision, transfer, state size, update cost and query cost. Include ablations of memory, relational state and coupling.

### E10 — Geometric relational representation

**Purpose:** Test geometry as a candidate general representation and inductive bias.

Compare suitable vector/tensor, learned graph, non-geometric latent, subspace, Grassmannian and other justified geometric alternatives.

**Question:** Does geometry provide measurable benefits in invariance/equivariance, higher-order organisation, compositionality, smooth adaptation, compactness or transfer?

**Evidence:** Matched-compute and matched-supervision comparisons, ablations, sensitivity analysis, interpretability and transfer. Grassmannian geometry must earn its place experimentally; it is not presumed to be the answer.

### E11 — Hierarchical relational adaptation

**Purpose:** Only after earlier capabilities are demonstrated, test relational learning within D2C's multi-timescale hierarchy.

Include fast local relations, persistent contextual relations, higher-level structural patterns, and top-down predictions that influence lower-level relational learning.

**Question:** Can relational organisation itself become hierarchical and adaptive?

**Evidence:** Long-horizon reasoning, structural adaptation, predictive consistency, cross-scale coordination and task transfer.

## 5. Shared experimental controls

Across the programme, where applicable:

- Use the same observations, training examples, supervision, compute budgets and evaluation queries across compared models.
- Separate model-visible inputs from evaluator-only truth, planted structures, labels and corruption audits.
- Include both graph-like and non-graph-like task families.
- Hold out relation configurations and, where possible, relation types or domains.
- Test noise, ambiguity, missing evidence, contradiction, temporal gaps and structural change.
- Report fact retrieval separately from relation discovery, composition and reasoning.
- Report state size, update work, query work and wall-clock measurements separately; do not equate unlike operation counters.
- Include ablations for geometry, SOE, coupling and hierarchy.
- Require interpretable relational witnesses or explanations where the task permits them.
- Preserve negative results and version experimental protocols before inspecting held-out outcomes.

## 6. E03 entry gate and next action

E03 is the next design task, not yet an implementation commitment.

Before coding E03, freeze:
1. task families and ground-truth semantics;
2. complexity levels and held-out generalisation splits;
3. model-visible versus evaluator-only information;
4. baseline architectures and fair training/compute controls;
5. metrics, seeds, reproducibility artifacts and acceptance criteria.

E03 must not encode the answer in the representation being evaluated. The system should be allowed to discover problem structure rather than merely operate on structure pre-discovered by the benchmark designer.

## 7. Decision log

- **2026-11-14 — Adaptive relational capability added as a research objective:** D2C experiments motivated explicit investigation of relational discovery, preservation, composition, revision and reorganisation. This expands the questions asked by the independent relational research track; it does not establish a D2C architecture change.
- **2026-11-14 — Architecture kept open:** SOE-only, coupled temporal/relational states and a unified augmented state remain competing hypotheses.
- **2026-11-14 — Geometry kept as a candidate, not a premise:** Grassmannian and other geometric representations must be compared with learned non-geometric alternatives.
- **2026-11-14 — E03 designated next:** benchmark diversity and representation-neutral controls precede implementation of a new relational learner.
