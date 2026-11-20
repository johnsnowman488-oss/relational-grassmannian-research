# HLG-M4 Confirmatory Experiment Ledger

**Status:** Independent-world generator, train-world corpora, ordered-transition readout features and validation-only G1–G5 pilots pass on Python 3.10/3.12. Validation diagnostics are complete for this bounded pilot; confirmatory evaluator/gates and test execution remain unfinished. Confirmatory test outcomes have not been opened.
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
- The readout uses relation counts, SOE temporal summaries, architecture support, position-specific relation indicators and adjacent ordered-pair transition features. It remains a fixed-vocabulary, bounded-feature model.
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

## 5. Validation-only independent-world pilot results

These are software/validation diagnostics on 12 validation seeds across two task modes (24 worlds per architecture for G1, and condition-expanded rows for G2/G3). The train corpus is aggregated from the disjoint 120-world train partition; validation-world target labels are not used to fit the readout. The confirmatory-test partition remains sealed.

### Generator and G1

- Preflight audit: 96 generated worlds; 83 distinct identity-invariant topology fingerprints; 51 distinct relation-signature sets across 7 typed namespaces; 48 heterogeneous typed-chain and 48 homogeneous order-sensitive worlds.
- Relation-layer assignment is randomized across heterogeneous worlds. Homogeneous order-sensitive worlds use cyclic forward sequences against same-bag reverse sequences.
- The earlier readout could not separate the randomized cyclic order family. We added explicit adjacent ordered-pair transition features to the linear readout; feature dimensions and resource costs consequently increased.
- After that correction, A and B each selected the planted path in 24/24 validation cases (12 per task mode), with zero invalid witnesses and no abstentions.

### G2 and G3

- G2: 72 cases per architecture. B selected correctly in 72/72. A selected correctly in 48/72 and abstained in the 24 no-replay outage cases; A succeeded when the current evidence window was replayed and after late arrivals.
- G3: 120 cases per architecture (five conditions × 24 worlds). Both A and B abstained on all 24 missing-edge, all 24 wrong-context, all 24 temporally invalid and all 24 genuinely ambiguous competing-path cases. Both selected all 24 multiple-witness positive controls.
- A pooled probability/margin grid contains 18 validation operating points with zero negative/ambiguous selections and full positive coverage in this pilot. Task-mode-specific frontiers are also recorded. These are exploratory validation results only; no threshold or acceptance gate is frozen from this small pilot.

### G4 and G5

- G4: 24 trials per architecture (12 validation seeds × 2 task modes). Candidate promotion 24/24; exact system rollback 24/24; detector rollback exact in every promoted case; rejection controls 24/24; dormancy/recovery 24/24. Stable-control alarms, transient-disturbance alarms and post-transient recovery alarms were all zero. Persistent-change detection delay was 9 steps in all 24 trials under the single declared residual sequence. This does not establish detection robustness under varied drift shapes or noise processes.
- G4 candidate fitting uses the train-partition corpus and validation losses are computed on separate validation-world target/decoy paths.
- G5: native resource sweep at 10/100/500/1,000 relation instances. At 1,000 instances, A had 4,336 persistent numeric bytes, zero relation payload bytes, 5,225 serialized snapshot bytes and 45,404 traced peak bytes; B had 4,336 persistent numeric bytes, 79,654 relation payload bytes, 137,189 serialized snapshot bytes and 80,476 traced peak bytes.
- At 1,000 instances, query p50/p95 was A 1.43/1.99 ms and B 2.17/2.78 ms. At 10 instances, A was 50.7/85.6 μs and B 67.7/105.5 μs. These are single-run native measurements, not matched-resource frontiers or cross-machine benchmarks.

### Interpretation

The pilot now demonstrates that the implemented readout can rank both randomized typed-chain patterns and cyclic same-bag/different-order paths after adding adjacent transition features. B's persistence advantage is visible in no-replay outages, while it incurs additional stored payload and higher query latency in this resource sweep. Neither result establishes universal A/B superiority. The validation sample remains small and task-family bounded.

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
3. Implement independent typed relational-world generator and explicit train/validation/test world partitions (complete for current bounded generator).
4. Add generator invariants, identity-invariant topology checks, partition-disjointness, causal cutoff and oracle-isolation tests (complete for generator preflight).
5. Run a small generator/software pilot only; do not expose confirmatory test outcomes (complete: 12 validation worlds, no test access).
6. Extend validation diagnostics across G1–G5, add ordered-pair features after the order-family diagnostic, and inspect limitations (complete as a bounded validation pilot; not a full confirmatory evaluator or frozen threshold calibration).
7. Freeze generator/config/partitions/thresholds/gates with hashes.
8. Run confirmatory A/B campaign, preserve seed/world-level results and artifacts.
9. Analyse paired comparisons and resource frontiers; issue a bounded evidence report.

## 8. Current status and open items

- [x] Verified repository default branch is `main`.
- [x] Verified PR #44/#45 work is on `research/hlg-m4-preimplementation-ledger`, not `main`.
- [x] Created isolated implementation branch from the merged research branch.
- [x] Identified fixed-topology pseudoreplication in prior 20-seed development generator.
- [x] Independent typed-world generator with heterogeneous entity types and seven distinct type namespaces (within-vocabulary; not seven non-isomorphic schema families).
- [x] Disjoint world-level train/validation/confirmatory-test partitions (120/60/120); partition seed digests recorded in preflight artifact.
- [x] Identity- and namespace-invariant topology fingerprint; latest preflight found 83 distinct topology fingerprints across 96 generated worlds, 51 distinct relation-signature sets and 7 schema namespaces.
- [x] Typed-edge invariants, cutoff-filtered oracle-free learner view, future-observation checks and partition-disjointness tests.
- [x] Randomized relation-layer assignment and cyclic same-bag/different-order sequence families; readout extended with adjacent ordered-pair transition features after the first validation pilot exposed a linear-feature limitation.
- [x] Validation-only G1 pilot: 12 validation seeds × 2 task modes × A/B (24 cases per architecture); both architectures selected the planted path in 24/24 cases with no invalid witnesses.
- [x] Validation-only G2 pilot: 72 cases per architecture; B selected correctly in 72/72. A selected correctly in 48/72 and abstained in all 24 no-replay outage cases; A succeeded with evidence replay and after late arrivals. This is a measured memory/replay distinction, not an architecture verdict.
- [x] Validation-only G3 pilot: 120 cases per architecture; both abstained on all 96 negative/ambiguous cases and selected all 24 multiple-witness positive controls. A pooled threshold grid has 18 feasible operating points in this pilot; thresholds remain unfrozen.
- [x] Validation-only G4 pilot: 24 trials per architecture using train-world candidate fitting and separate validation-world paths; promotion 24/24, exact rollback 24/24, rejection controls 24/24, dormancy/recovery 24/24, stable/transient/recovery alarms 0. Drift detection delay was 9 steps in every trial under the current controlled residual sequence; this does not establish robust detection under varied drift processes.
- [x] Validation-only G5 native resource sweep: 10/100/500/1,000 relation instances, A/B. At 1,000 instances after adding ordered-pair features, B relation payload 79,654 bytes, serialized snapshot 137,189 bytes, traced peak 80,476 bytes; A relation payload 0, serialized snapshot 5,225 bytes, traced peak 45,404 bytes. Query p50/p95 rose from A 41.5/71.1 μs and B 54.7/73.1 μs at 10 instances to A 1.10/1.61 ms and B 1.68/2.27 ms at 1,000. Native measurements only; not matched-resource frontiers or stable cross-machine benchmarks.
- [ ] Full confirmatory evaluator, larger validation calibration split, matched-resource frontier and numerical gate freeze.
- [ ] Validation-based calibration of probability/margin thresholds and numerical gates from requirements.
- [ ] Matched-resource A/B frontier and confirmatory evaluator with immutable configuration.
- [ ] Confirmatory execution and analysis.

Preflight and validation evidence:
- Latest preflight workflow run `44761971587` passed on Python 3.10 and 3.12.
- Repository unit/invariant run `44761971638`, A/B integration run `44761971548`, and G1–G5 development run `44761971569` all passed on Python 3.10 and 3.12.
- Head commit: `39c3acde7a1551c03b2384819887cdc308ce9982`.
- Python 3.12 artifact `14640513915`, SHA256 `85760bdded8cfd400747dc9ecddaad4190c58253a3a07e5d21d2a613e412afa6`; Python 3.10 artifact `14641427035`, SHA256 `b5842c361ad326c83e7935574ca447c9c08fe66d63a47180fb2703bb504d866d`.
- The Python 3.12 artifact contains 96 generator-audit worlds, 83 distinct identity-invariant topology fingerprints, 51 distinct relation-signature sets across 7 namespaces, and disjoint 120/60/120 train/validation/confirmatory-test partitions.
- Both artifacts contain seed/world-level G1–G5 pilot rows. Model diagnostics access validation worlds only; the confirmatory-test partition remains sealed.
- All results above are validation/software diagnostics only; no confirmatory performance or acceptance claim is made.

No confirmatory acceptance result is claimed at this stage.
