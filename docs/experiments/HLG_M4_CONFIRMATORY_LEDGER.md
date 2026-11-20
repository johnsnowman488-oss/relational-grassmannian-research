# HLG-M4 Confirmatory Experiment Ledger

**Status:** Design and preflight implementation in progress. Confirmatory test outcomes have not been opened.
**Research branch:** `m4/confirmatory-worlds-preflight`
**Parent evidence commit:** `8a259725d5092c370b284ef451a065a9b1583d36`
**Scope:** Compare integrated Architecture A and Architecture B across G1–G5. This ledger is the experiment's decision and provenance record.

## 1. Research question

Does the integrated Leptograph memory pipeline reliably retrieve, compose, select, retain, and revise relational knowledge under controlled but structurally independent relational worlds? Does Architecture B's persistent typed relation-instance store provide a measurable reliability advantage over Architecture A's SOE temporal memory and learned readout, and is that advantage worth its memory and compute costs?

A and B remain the only primary architectures. B is the leading hypothesis from preliminary persistence results, not a declared winner. A remains the necessary comparator. C and R are historical/reference controls only; D2C is motivation, not a current comparator unless separately justified.

## 2. Architecture and claim boundary

- **A:** SOE temporal memory with learned relational readout; no separate persistent relation-instance store. It can use an explicitly supplied current evidence window.
- **B:** The same SOE/readout pipeline plus a bounded persistent typed relation-instance store.
- Candidate paths are enumerated from task-visible graph instances; the learned readout ranks candidates; the P0 composer validates witnesses. This is not autonomous open-world topology discovery.
- Maximum tested composition depth is 4 in this campaign.
- P0 witness correctness and P1 first-failure attribution remain mandatory.
- P6 lifecycle must be exercised as an operational sequence, not only as isolated controller method calls.

A successful M4 result does **not** establish language understanding, arbitrary discovery, unrestricted composition depth, general cross-domain transfer (E08), arbitrary-switching/global stability, a full Leptograph realization, or a Grassmannian advantage. E09 remains the formal temporal-memory/relational-organisation reintegration point; no broad E08 transfer claim is licensed here.

## 3. Prior implementation and development evidence

The integrated Job4 work is present on the research branch:
- PR #44 integrated A/B system and P6 lifecycle; merge commit `8803011abc652d8581bacac90aabed0fd1afcdfd`.
- PR #45 added G1–G5 development evaluator; merge commit `8a259725d5092c370b284ef451a065a9b1583d36`.
- Job1/2/3 implementation heads and their evidence are retained in the earlier project ledger and PR history.

Previous development campaign reported:
- G1: A and B 20/20 at depths 2, 3, and 4.
- G2: B 60/60 across delays 0, 4, 8; A 60/60 at delay 0 and abstained at delays 4/8 when no event window was supplied.
- G3: 100% abstention in the constructed ambiguity and wrong-context cases.
- G4: one lifecycle demonstration per architecture; promotion and rollback worked.
- G5: A numeric-state bytes fixed at 912; B relation payload grew from 620 bytes at 10 instances to 67,670 bytes at 1,000 instances. Payload excludes Python allocator/container overhead.

### Critical correction to interpretation

The prior 20-seed G1/G2 cases were **not 20 independent structural worlds**. The generator reused the same target relation sequence, decoy sequence, relation vocabulary and graph topology for every seed. Seeds changed entity identifiers and fact ordering, but did not produce independent topology/composition families. Therefore 20/20 and 60/60 are repeated variants of a narrow task, not evidence of structural generalisation. These remain development/integration results only.

Other limitations:
- Prior G1 used a fixed Node-to-Node schema and fixed relation vocabulary.
- G2's A result measured absence of a supplied current evidence window; it did not separately measure outage retention when replay is available.
- G3 used a manually high ambiguity margin and a wrong-context case that removed all valid paths; it did not establish calibrated risk/coverage.
- G4 was one trial per architecture, not a repeated adaptation study.
- G5 measured payload fields, not actual serialized size, process memory, latency distributions, or throughput.

## 4. Confirmatory campaign design: G1–G5

### G1 — Composition and structural generalisation
- Independent graph topologies and independently generated entity identities.
- Heterogeneous typed entity/relation signatures, not only Node-to-Node.
- Vary branch/distractor layouts, edge ordering, relation assignments and path multiplicity.
- Include same-bag/different-order candidates, multiple valid witnesses, misleading paths, missing edges and temporally invalid chains.
- Hold out complete graph worlds and selected composition-layout families, not random rows from a seen graph.
- Report candidate selection accuracy, exact path match, witness integrity, composition success and P1 first-failure attribution.
- Keep maximum depth 4 and state the readout's fixed vocabulary/bounded feature limits explicitly.

### G2 — Temporal robustness and memory
Separate three conditions:
1. Outage with no event-window replay (tests retained memory).
2. Outage with current evidence-window replay available (tests A's explicit evidence-window capability).
3. Late-arrival, out-of-order observation and validity-window cases.
- Enforce causal online queries. Do not request historical cutoffs earlier than the system's last-observed timestamp; the current implementation correctly returns `ABSTAIN_CUTOFF_UNSUPPORTED` for such contaminated historical queries.
- Measure valid retrieval, false recall, abstention, temporal validity and recovery.

### G3 — Selection, false paths and abstention
- Include plausible false paths, ambiguous valid alternatives, incomplete paths, wrong contexts and contradictory evidence.
- Calibrate probability and margin thresholds on validation worlds only, then freeze them.
- Report false-selection rate, precision, abstention rate, coverage and risk-versus-coverage. Do not tune after test results.

### G4 — Adaptation and revision
- Repeated independent stationary controls and drift trials.
- Separate transient disturbance from persistent change.
- Fit candidate on one set and validate on independent validation worlds/time blocks.
- Exercise detector → candidate fit → independent validation → promotion/rejection → trusted-state rollback → dormancy/recovery.
- Verify rollback of SOE, relation store, readout, detector and lifecycle state.
- Report false alarms, detection delay, validation improvement, promotion/rejection, rollback fidelity and recovery.
- The inherited threshold 24 is provisional and must be checked against validation residual distributions before freeze.

### G5 — Resource and scaling
- Scale relation instances, graph branching and query load, including 10–1,000+ instances.
- Measure serialized state size, process-level memory where reproducible, p50/p95 update/query latency, throughput and operation counts.
- Report both native architecture capacities and matched-resource frontiers.
- Distinguish persistent numeric state, relation payload, serialized bytes, and process memory. Never present payload-only bytes as total memory.

## 5. Experimental controls and statistics

- A and B receive identical observation streams, query sets, observation cutoffs, train/validation/test partitions and seeds.
- The statistical unit is an independent relational world, not an entity identifier or individual query. Queries/conditions within a world are clustered.
- Use paired A/B comparisons on the same worlds and paired confidence intervals/bootstraps clustered by world.
- Training, validation and confirmatory test partitions are disjoint at the world/topology level. Do not split rows from one graph across partitions.
- Relation vocabulary may be shared where the claim is within-vocabulary generalisation; schema-family or composition-family holdouts must be declared separately and must not silently become an out-of-vocabulary transfer claim.
- Hide planted target labels/oracle paths from candidate generation and model scoring. Oracle information is used only by the evaluator after predictions are fixed.
- Test queries must be causal with respect to observation cutoffs. No future-observation leakage.
- Freeze test seeds, generator version, partition manifest, thresholds, metrics and gate rules before opening confirmatory outcomes.
- Pilot runs may inspect generator validity and software correctness, not test-set performance. Keep pilot and confirmatory artifact namespaces separate.

## 6. Gate policy

Numerical thresholds are **not yet frozen**. Derive them from task requirements and validation distributions before opening the confirmatory test partition. Do not invent or retrofit thresholds after seeing test outcomes.

Gate categories:
1. P0: no invalid witness accepted; typed endpoint and relation-instance witness integrity.
2. G1: held-out world composition/selection and witness metrics.
3. G2: causal temporal validity, no future leakage, and declared outage/replay robustness.
4. G3: false selection, abstention and coverage-risk constraints.
5. G4: stationary false-alarm control, detection, independent validation improvement and exact rollback.
6. G5: declared memory/latency/throughput envelope and matched-resource comparison.
7. Provenance: seed-level rows, immutable manifest, commit, runtime versions, artifact hashes and verifier.

## 7. Execution order

1. Verify actual merged research branch and inspect integrated implementation (completed for this work session).
2. Record this ledger in the repository and Library.
3. Implement independent typed relational-world generator and explicit train/validation/test world partitions.
4. Add generator invariants, topology-independence checks, partition-disjointness checks, causal cutoff/leakage tests and oracle isolation checks.
5. Run a small generator/software pilot only; do not expose confirmatory test outcomes.
6. Implement G1–G5 confirmatory evaluator and validation-only threshold calibration.
7. Freeze generator/config/partitions/thresholds/gates with hashes.
8. Run confirmatory A/B campaign, preserve seed/world-level results and artifacts.
9. Analyse paired comparisons and resource frontiers; issue a bounded evidence report.

## 8. Current status and open items

- [x] Verified repository default branch is `main`.
- [x] Verified PR #44/#45 work is on `research/hlg-m4-preimplementation-ledger`, not `main`.
- [x] Created isolated implementation branch from the merged research branch.
- [x] Identified fixed-topology pseudoreplication in prior 20-seed development generator.
- [ ] Independent typed-world generator and schema-family design.
- [ ] Disjoint world-level partitions and hidden confirmatory test manifest.
- [ ] Generator, leakage and oracle-isolation tests.
- [ ] G1–G5 confirmatory runner, calibration and resource instrumentation.
- [ ] Numerical gates frozen from requirements/validation.
- [ ] Confirmatory execution and analysis.

No confirmatory acceptance result is claimed at this stage.
