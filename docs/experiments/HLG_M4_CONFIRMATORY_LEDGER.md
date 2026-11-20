# HLG-M4 Confirmatory Experiment Ledger

**Status:** The frozen confirmatory A/B campaign has now completed successfully on Python 3.12 after one documented execution-recovery attempt. The 120-world test partition was evaluated once successfully with the frozen model, thresholds, gates and partition manifest. All bounded hard-integrity gates passed. The evidence report is recorded below; interpretation remains deliberately limited to the frozen synthetic task families and depth 2–4.
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
- The readout uses relation counts, SOE temporal summaries, architecture support, position-specific relation indicators and adjacent ordered-pair transition features. It remains a fixed-vocabulary, bounded-feature model. Observations are ingested in ascending `(observed_at, event_time, instance_id)` order except in explicitly staged late-arrival trials. Observations are ingested in ascending `(observed_at, event_time, instance_id)` order except in explicitly staged late-arrival trials.
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

These are software/validation diagnostics across all 60 validation seeds and two task modes. G3 uses a 30-world calibration half and a separate 30-world validation half. The train corpus is aggregated from the disjoint 120-world train partition; validation-world target labels are not used to fit the readout. The confirmatory-test partition remains sealed.

### Generator and G1

- Preflight audit: 96 generated worlds; 83 distinct identity-invariant topology fingerprints; 51 distinct relation-signature sets across 7 typed namespaces; 48 heterogeneous typed-chain and 48 homogeneous order-sensitive worlds.
- Relation-layer assignment is randomized across heterogeneous worlds. Homogeneous order-sensitive worlds use cyclic forward sequences against same-bag reverse sequences.
- The earlier readout could not separate the randomized cyclic order family. We added explicit adjacent ordered-pair transition features to the linear readout; feature dimensions and resource costs consequently increased.
- After that correction, A and B each selected the planted path in 120/120 validation cases (60 per task mode), with zero invalid witnesses and no abstentions.

### G2 and G3

- G2: 360 cases per architecture. B selected correctly in 360/360. A selected correctly in 240/360 and abstained in the 120 no-replay outage cases; A succeeded when the current evidence window was replayed and after late arrivals.
- G3: 120 cases per architecture (five conditions × 24 worlds). Both A and B abstained on all 24 missing-edge, all 24 wrong-context, all 24 temporally invalid and all 24 genuinely ambiguous competing-path cases. Both selected all 24 multiple-witness positive controls.
- A pooled probability/margin grid contains 18 validation operating points with zero negative/ambiguous selections and full positive coverage in this pilot. Task-mode-specific frontiers are also recorded. These are exploratory validation results only; no threshold or acceptance gate is frozen from this small pilot.

### G4 and G5

- G4: 120 trials per architecture (60 validation seeds × 2 task modes). Candidate promotion 120/120; exact system rollback 120/120; detector rollback exact in every promoted case; rejection controls 120/120; dormancy/recovery 120/120. Stable-control alarms, transient-disturbance alarms and post-transient recovery alarms were all zero. Persistent-change detection delay was 9 steps in all 120 trials under the single declared residual sequence. This does not establish detection robustness under varied drift shapes or noise processes.
- G4 candidate fitting uses the train-partition corpus and validation losses are computed on separate validation-world target/decoy paths.
- G5: native resource sweep at 10/100/500/1,000 relation instances. At 1,000 instances, A had 4,336 persistent numeric bytes, zero relation payload bytes, 5,225 serialized snapshot bytes and 45,404 traced peak bytes; B had 4,336 persistent numeric bytes, 79,654 relation payload bytes, 137,189 serialized snapshot bytes and 79,996 traced peak bytes.
- At 1,000 instances, query p50/p95 was A 0.93/1.31 ms and B 1.43/1.88 ms. At 10 instances, A was 35.9/60.2 μs and B 44.1/56.6 μs. These are single-run native measurements, not matched-resource frontiers or cross-machine benchmarks.

### G5 memory-budgeted retention frontier

A separate 30-world validation frontier used the held-out validation half, a fixed 0.75/0.25 readout threshold candidate, 1,000 observed relation instances per world and randomized observation positions for the four-edge target chain. The same serialized-snapshot upper-bound budget was applied to A and B; A's unused budget is shown explicitly. A's external evidence replay is reported separately and is not charged to persistent memory.

| B relation capacity | B snapshot budget (p95 bytes) | B correct retention |
|---:|---:|---:|
| 10 | 7,574 | 0/30 |
| 25 | 10,455 | 0/30 |
| 50 | 15,223 | 0/30 |
| 100 | 24,741 | 0/30 |
| 250 | 53,313 | 0/30 |
| 500 | 100,965 | 2/30 |
| 750 | 148,519 | 9/30 |
| 800 | 158,037 | 11/30 |
| 850 | 167,558 | 14/30 |
| 900 | 177,079 | 18/30 |
| 950 | 186,591 | 24/30 |
| 1,000 | 196,077 | 30/30 |

- A no-replay: 0/30 correct, 30/30 abstentions; persistent snapshot p95 5,225 bytes.
- A with external evidence-window replay: 30/30 correct. The external batch is not charged to persistent snapshot memory.
- A's 5,225-byte snapshot fits under every B upper-bound budget; this is a budget-capped frontier, not equal-byte consumption. A leaves budget unused because it has no persistent relation store.
- B false selections: 0 at every capacity.
- The frontier shows a retention/memory trade-off: with randomly positioned target edges, B needed the full 1,000-record store (about 196 KB serialized snapshot budget) for 30/30 retention in this sample. This is a bounded synthetic stress test, not a universal scaling law.

### Interpretation

The pilot now demonstrates that the implemented readout can rank both randomized typed-chain patterns and cyclic same-bag/different-order paths after adding adjacent transition features. B's persistence advantage is visible in no-replay outages, while it incurs additional stored payload and higher query latency in this resource sweep. Neither result establishes universal A/B superiority. The validation sample remains task-family bounded. The G5 frontier is a memory-budgeted upper-bound comparison, not an equal-byte frontier.

## 6. Experimental controls and statistics

- A and B receive identical observation streams, query sets, observation cutoffs, train/validation/test partitions and seeds.
- The statistical unit is an independent relational world, not an entity identifier or individual query. Queries/conditions within a world are clustered.
- Use paired A/B comparisons on the same worlds and paired confidence intervals/bootstraps clustered by world.
- Training, validation and confirmatory test partitions are disjoint at the world/topology level. Do not split rows from one graph across partitions.
- Relation vocabulary may be shared where the claim is within-vocabulary generalisation; schema-family or composition-family holdouts must be declared separately and must not silently become an out-of-vocabulary transfer claim.
- Hide planted target labels/oracle paths from candidate generation and model scoring. Oracle information is used only by the evaluator after predictions are fixed.
- Test queries must be causal with respect to observation cutoffs. No future-observation leakage.
- Freeze test seeds, generator version, partition manifest, thresholds, metrics and gate rules before opening confirmatory outcomes.
- Pilot runs may inspect generator validity and software correctness, not test-set performance. Keep pilot and confirmatory artifact namespaces separate.

## 7. Gate policy

The confirmatory protocol is frozen in `HLG_M4_CONFIRMATORY_CONFIG.json` (SHA256 `a4df456185812fdee67edd939e13a049f3889ba2bf9f5256f746d8fdeb6c5218`). The probability/margin candidate (0.75/0.25) was selected on the first 30 validation worlds and checked unchanged on the separate last 30 validation worlds. The held-out validation check had zero false/ambiguous selections and full positive-control coverage. This is the pre-test calibration basis, not a guarantee about the confirmatory set.

Gate policy deliberately distinguishes hard correctness invariants from estimated performance. Numerical acceptance is imposed only where justified by task semantics (zero invalid witnesses, zero future leaks, zero false/ambiguous G3 selections, full positive-control coverage, exact rollback, and the declared resource reporting requirements). G1/G2 accuracy and A/B differences are estimated with paired 95% world-clustered bootstrap intervals rather than arbitrary post-hoc percentage cutoffs. Do not change thresholds or gates after opening test outcomes.

Gate categories:
1. P0: no invalid witness accepted; typed endpoint and relation-instance witness integrity.
2. G1: held-out world composition/selection and witness metrics.
3. G2: causal temporal validity, no future leakage, and declared outage/replay robustness.
4. G3: false selection, abstention and coverage-risk constraints.
5. G4: stationary false-alarm control, detection, independent validation improvement and exact rollback.
6. G5: declared memory/latency/throughput envelope and matched-resource comparison.
7. Provenance: seed-level rows, immutable manifest, commit, runtime versions, artifact hashes and verifier.

## 8. Execution order

1. Verify actual merged research branch and inspect integrated implementation (completed for this work session).
2. Record this ledger in the repository and Library.
3. Implement independent typed relational-world generator and explicit train/validation/test world partitions (complete for current bounded generator).
4. Add generator invariants, identity-invariant topology checks, partition-disjointness, causal cutoff and oracle-isolation tests (complete for generator preflight).
5. Run generator/software pilots and a larger validation-only calibration/held-out check; do not expose confirmatory test outcomes (complete: all 60 validation worlds split 30/30 for G3 calibration and validation).
6. Complete expanded validation diagnostics, 30/30 threshold calibration/held-out check, and memory-budgeted G5 retention frontier (complete as bounded validation evidence; no equal-byte resource matching or confirmatory test execution yet).
7. Freeze generator/config/partitions/thresholds/gates with hashes (complete; protocol `HLG-M4-CONFIRMATORY-AB-v1`, config SHA256 `a4df456185812fdee67edd939e13a049f3889ba2bf9f5256f746d8fdeb6c5218`, partition manifest SHA256 `488d16e20f766d26459075f2e57ae0c4d7b1c68a1696f9e41a0424a68ca095b7`).
8. Run the confirmatory A/B campaign once from the frozen code/config through the dedicated `m4-confirmatory-authorized` PR-label-gated workflow; preserve seed/world-level results and artifacts.
9. Analyse paired comparisons and resource frontiers; issue a bounded evidence report.

## 9. Current status and open items

- [x] Verified repository default branch is `main`.
- [x] Verified PR #44/#45 work is on `research/hlg-m4-preimplementation-ledger`, not `main`.
- [x] Created isolated implementation branch from the merged research branch.
- [x] Identified fixed-topology pseudoreplication in prior 20-seed development generator.
- [x] Independent typed-world generator with heterogeneous entity types and seven distinct type namespaces (within-vocabulary; not seven non-isomorphic schema families).
- [x] Disjoint world-level train/validation/confirmatory-test partitions (120/60/120); partition seed digests recorded in preflight artifact.
- [x] Identity- and namespace-invariant topology fingerprint; latest preflight found 83 distinct topology fingerprints across 96 generated worlds, 51 distinct relation-signature sets and 7 schema namespaces.
- [x] Typed-edge invariants, cutoff-filtered oracle-free learner view, future-observation checks and partition-disjointness tests.
- [x] Randomized relation-layer assignment and cyclic same-bag/different-order sequence families; readout extended with adjacent ordered-pair transition features after the first validation pilot exposed a linear-feature limitation.
- [x] Validation-only G1 pilot: all 60 validation seeds × 2 task modes × A/B (120 cases per architecture); both architectures selected the planted path in 120/120 cases with no invalid witnesses.
- [x] Validation-only G2 pilot: 360 cases per architecture; B selected correctly in 360/360. A selected correctly in 240/360 and abstained in all 120 no-replay outage cases; A succeeded with evidence replay and after late arrivals. This is a measured memory/replay distinction, not an architecture verdict.
- [x] Validation-only G3 pilot: 600 cases per architecture; both abstained on all 480 negative/ambiguous cases and selected all 120 multiple-witness positive controls. Calibration on 30 worlds selected probability 0.75/margin 0.25; the separate 30-world validation half had zero false selections, zero ambiguity selections and 100% positive coverage. Candidate only; not frozen.
- [x] Validation-only G4 pilot: 120 trials per architecture using train-world candidate fitting and separate validation-world paths; promotion 120/120, exact rollback 120/120, rejection controls 120/120, dormancy/recovery 120/120, stable/transient/recovery alarms 0. Drift detection delay was 9 steps in every trial under the current controlled residual sequence; this does not establish robust detection under varied drift processes.
- [x] Validation-only G5 native resource sweep: 10/100/500/1,000 relation instances, A/B. At 1,000 instances after adding ordered-pair features, B relation payload 79,654 bytes, serialized snapshot 137,189 bytes, traced peak 79,996 bytes; A relation payload 0, serialized snapshot 5,225 bytes, traced peak 45,404 bytes. Query p50/p95 rose from A 35.9/60.2 μs and B 44.1/56.6 μs at 10 instances to A 0.93/1.31 ms and B 1.43/1.88 ms at 1,000. Native measurements only; not equal-byte matched-resource frontiers or stable cross-machine benchmarks.
- [x] G5 memory-budgeted retention frontier: 30 held-out validation worlds, 12 B capacities (10–1,000), zero false selections. A no-replay 0/30; A with external replay 30/30; B retention ranged from 0/30 at capacity 10–250 to 30/30 at capacity 1,000 (about 196 KB snapshot budget). A's 5,225-byte snapshot fit beneath all B upper-bound budgets. This is a budget-capped comparison, not equal-byte consumption.
- [x] Larger validation calibration/held-out split (30/30) with a candidate threshold and independent validation metrics; requirements-based acceptance gates remain unfrozen.
- [x] Memory-budgeted A/B retention frontier on 30 held-out validation worlds; equal-byte resource matching remains open.
- [x] Full confirmatory evaluator and immutable protocol/configuration freeze. Validation-shadow execution on the separate 30-world validation holdout passed on Python 3.10 and 3.12; `confirmatory_test_accessed=false`, `bounded_integrity_gate_pass=true`.
- [x] Confirmatory execution completed on Python 3.12 after the documented recovery. All bounded hard-integrity gates passed; detailed G1–G5 analysis and claim limits are recorded below. Python 3.10 and 3.12 unit, A/B integration and G1–G5 development workflows also passed.

Preflight and validation evidence:
- Expanded preflight workflow run `44763725166`, unit/invariant run `44763725200`, A/B integration run `44763725116`, and G1–G5 development run `44763725468` all passed on Python 3.10 and 3.12.
- Code head used for these artifacts: `905199e5c33bd91b2849c60d5f00062ddfb6c61c`.
- Python 3.12 preflight artifact `14642552702`, SHA256 `3aeffbc3243fd14ac50635512da742f7b88d79044da2da0ceb351fdf203245e1`; Python 3.10 preflight artifact `14642926392`, SHA256 `66e1bd141e19066d4b5537357700ba029f2da8351214d99dc29a393d1a57ff61`.
- Python 3.12 development artifact `14641833394`, SHA256 `613beb961a2c0d297b8d57ba40ec2517b38d0cf7ea5aa8a24a302c915e6c0328`; Python 3.10 development artifact `14643080420`, SHA256 `244d1c85e418277115aa15be9688dd4d8e696f548ba29418c470f1bfc755f3aa`.
- The Python 3.12 preflight artifact contains 96 generator-audit worlds, 83 distinct identity-invariant topology fingerprints, 51 distinct relation-signature sets across 7 namespaces, and disjoint 120/60/120 train/validation/confirmatory-test partitions.
- Both artifacts contain seed/world-level G1–G5 pilot rows. Model diagnostics access validation worlds only; the confirmatory-test partition remains sealed.
- All results above are validation/software diagnostics only; no confirmatory performance or acceptance claim is made.

No confirmatory acceptance result is claimed at this stage.


### Frozen evaluator validation-shadow evidence (not confirmatory)

- Code head: `81b54c953e18e4a248c03b175f54ac423131d28f`.
- Repository unit/invariant run `44766739568`, A/B integration run `44766739811`, G1–G5 development run `44766739850`, and independent-world preflight/validation-shadow run `44766739744` passed on Python 3.10 and 3.12.
- Preflight artifacts: Python 3.10 artifact `14644687284`, ZIP SHA256 `24c6ac9be3756296d5fda52f0169b3e1531fd949fa9ae0e2450971cf75c9d8e7`; Python 3.12 artifact `14643767904`, ZIP SHA256 `cf68d6f4d6295a2dbc570f0cb164a4e95689981edaca097a79c7c27c0c85eba2`.
- Validation-shadow JSON SHA256: Python 3.10 `00fd879b178ea31620c5673e94e5775716d78d4e775a27e9bfe66d16463103b2`; Python 3.12 `f8f5d8c4c2a91319fd11aa7abfde4d369917038cd44a3239225d692d540ed974`.
- Both runtimes report the same config SHA256 `a4df456185812fdee67edd939e13a049f3889ba2bf9f5256f746d8fdeb6c5218`, partition-manifest SHA256 `488d16e20f766d26459075f2e57ae0c4d7b1c68a1696f9e41a0424a68ca095b7`, zero confirmatory-test worlds accessed, and all bounded integrity gates true.
- Validation-shadow holdout: 30 worlds × 2 task modes; A and B both G1 60/60 exact selections, zero invalid witnesses. G2: B 60/60 in each outage/replay/late-arrival condition; A 0/60 without replay and 60/60 with replay and after late arrivals. G3: per architecture, zero false selections and zero ambiguous selections; 60/60 multiple-witness positive controls selected. G4: 60 trials per architecture; 60/60 promotion, exact system rollback, exact detector rollback, rejection controls and dormancy/recovery; zero stable/transient/recovery alarms; detection delay 9 under the single declared residual sequence. G5 at 1,000 instances: A 5,225-byte snapshot, 0 relation payload bytes, 46,116 traced peak bytes, 1.742/2.623 ms query p50/p95; B 137,189-byte snapshot, 79,654 relation payload bytes, 96,564 traced peak bytes, 2.147/2.956 ms query p50/p95.
- Paired A/B bootstrap intervals are clustered by 30 independent validation worlds (10,000 resamples). G1, replay and late-arrival differences are zero; B's no-replay advantage is +1.0 accuracy (95% interval [1.0, 1.0]) in this deliberately bounded retention task. No general A/B winner is declared.
- The validation-shadow's `bounded_integrity_gate_pass=true` is a pre-test integrity result only. It is not a confirmatory pass and does not license broad Leptograph, open-world, E08, arbitrary-depth, global-stability or Grassmannian claims.

### Confirmatory execution recovery note

The first authorized run 44767462519 loaded the frozen confirmatory partition and completed the G1–G4 calculations before failing at the G5 frontier's partition lookup. The exception was caused by a naming mismatch: the runner's public selector is test, while the actual partition object is named confirmatory_test. Both matrix jobs failed identically. Because the campaign function raised before returning, no confirmatory result JSON was written, no aggregate summary was printed, and no metrics were examined for tuning. The recovery fix maps test to confirmatory_test and adds a direct unit test. It does not change the generator, test seeds, training, model, thresholds, gates or scoring. The same frozen partition will be rerun once to complete the originally authorized campaign; results will be identified as recovered execution after a deterministic infrastructure error, not as a fresh independent test sample.


## 11. Confirmatory M4 execution — completed

### Execution provenance

- Campaign: `HLG-M4-CONFIRMATORY-AB-v1`.
- Canonical runtime: Python 3.12.16, NumPy 2.5.5, Linux x86_64.
- Confirmatory workflow run: `44768006598`; recovery execution on the one-shot authorized commit `870f6d20e5a2e7b9e4871136de51c797f0b12618`.
- Result-producing source commit recorded in the artifact: `5e4b4840a40452482cd21532af75d14ac1f8f0a3`.
- Frozen config SHA-256: `a4df456185812fdee67edd939e13a049f3889ba2bf9f5256f746d8fdeb6c5218`.
- Partition manifest SHA-256: `488d16e20f766d26459075f2e57ae0c4d7b1c68a1696f9e41a0424a68ca095b7`.
- Train / validation / confirmatory-test worlds: 120 / 60 / 120; test partition accessed only by the frozen campaign runner. Thresholds were fixed at probability 0.75 and margin 0.25 before test execution; zero test rows were used for threshold tuning.
- Artifact: `14646281905`, ZIP SHA-256 `892e7eb7c9c593c5f7ec44dfe5d4f13c8f0bd8400151354ba0e6fbc1c9f489e3`.
- Raw result JSON SHA-256: `49a17328779542c88ed9ae1b3484caf79f6a40c194600c335bbacf8de59f5384`.
- The first attempt (workflow run `44767462519`) failed at the G5 selector/partition-name boundary. No result artifact was emitted and no intermediate metrics were inspected. Recovery was limited to the deterministic selector mapping and its test; the same frozen test partition was rerun once. Treat the recovered run as completion of the originally authorized campaign, not as a second independent sample.

### G1 — composition and path selection

- 240 evaluated cases per architecture (120 independent world seeds × 2 task modes).
- A: 240/240 exact planted-path selections; B: 240/240.
- Both architectures: 240/240 selected witnesses valid; zero future-observation leaks; all depth strata (2, 3, 4) had 80/80 correct selections per architecture.
- Paired B−A accuracy difference: 0.0; 95% world-seed-clustered bootstrap interval [0.0, 0.0], 120 paired seed clusters.
- Interpretation: both systems solve this bounded, within-vocabulary composition/ranking task on generated structural worlds. This does not demonstrate open-world path discovery or OOV relation-sequence transfer.

### G2 — temporal retention, outage, replay and late arrival

Each architecture has 720 rows (120 seeds × 2 task modes × 3 conditions).

- Outage without external replay: A 0/240 correct selections (abstained in all 240); B 240/240 correct selections.
- Outage with the current evidence window supplied: A 240/240; B 240/240.
- Staged late arrival followed by a causal current-cutoff query: A 240/240; B 240/240.
- Paired B−A accuracy difference for no-replay outage: +1.0, 95% world-seed-clustered bootstrap interval [1.0, 1.0]. Replay and late-arrival differences were 0.0, intervals [0.0, 0.0].
- Interpretation: the measured advantage is specifically persistent relation-instance retention when no replay evidence is available. When A receives the current evidence window, the two architectures tie on this task.

### G3 — false-path control, ambiguity and positive witness coverage

Each architecture has 1,200 rows (120 seeds × 2 modes × 5 conditions).

- Missing target edge, wrong context, temporally invalid target and ambiguous competing paths: zero selected paths for A and B; zero false or ambiguous selections.
- Multiple-witness positive control: A selected 240/240; B selected 240/240; all selected witnesses passed integrity checks.
- Hard gates passed: zero false selections, zero ambiguity selections, 100% positive-control coverage.
- Interpretation: the frozen thresholds are conservative in these constructed conditions. This does not estimate a broad real-world risk/coverage curve beyond these task families.

### G4 — adaptation, validation, rollback and recovery

- 240 trials per architecture (120 seeds × 2 task modes).
- A and B each: candidate promotion 240/240; exact system rollback 240/240; exact detector rollback 240/240; rejected-candidate controls preserved the incumbent 240/240; dormancy/recovery completed 240/240.
- Stable-control alarms, transient-disturbance alarms and post-transient recovery alarms were all zero under the single frozen residual sequence. Drift detection delay was 9 steps in every trial.
- Mean candidate held-out test-loss improvement was 3.6075 for each architecture (range 1.7991–5.9702); the paired A/B difference was zero with 95% interval [0.0, 0.0].
- Interpretation: lifecycle and rollback invariants passed for this implementation and declared residual profile. The fixed detection delay does not establish general detector robustness under diverse drift processes or asynchronous switching.

### G5 — resource scaling and retention frontier

Native resource sweep (10, 100, 500, 1,000 relation instances):

- A serialized snapshot: 5,224–5,225 bytes; B: 6,783 / 18,381 / 71,180 / 137,189 bytes.
- At 1,000 instances: A relation payload 0 bytes, persistent numeric state 4,336 bytes, traced peak 45,404 bytes; B relation payload 79,654 bytes, persistent numeric state 4,336 bytes, traced peak 71,460 bytes.
- At 1,000 instances, update latency p50/p95: A 46.1/57.5 μs; B 47.0/61.5 μs. Query latency p50/p95: A 1.84/2.52 ms; B 2.90/3.71 ms. These are single-run environment measurements, not stable cross-machine benchmarks.
- Memory-budgeted B retention frontier over 30 test worlds: capacities 10–250 retained 0/30; capacity 500 retained 3/30; 750 retained 12/30; 800 retained 15/30; 850 retained 18/30; 900 retained 22/30; 950 retained 25/30; 1,000 retained 30/30. At capacity 1,000, B serialized-snapshot p95 was 196,071 bytes.
- A without replay selected 0/30; A with external evidence-window replay selected 30/30. A's persistent snapshot p95 was 5,225 bytes. External replay is not charged to persistent memory; therefore this is a budget-capped retention frontier, not an equal-byte total-memory comparison.
- Interpretation: B's persistence has a clear retention benefit in no-replay outage conditions, but it incurs a substantial memory and query-time cost. A can recover with replay, trading persistence for externally supplied evidence and higher query latency. Neither architecture is an unconditional winner.

### Hard gates and paired inference

- Zero invalid witnesses accepted.
- Zero future-observation leaks.
- Zero typed endpoint violations.
- Zero G3 false selections and zero ambiguity selections.
- 100% multiple-witness positive-control coverage.
- Exact system and detector rollback; rejection preserved incumbent; dormancy/recovery completed in every trial.
- Zero confirmatory rows used for threshold tuning.
- Paired comparisons used 10,000 bootstrap resamples clustered by 120 independent world seeds. The test set contains two task-mode worlds per seed; repeated conditions are clustered within seed.
- All frozen hard-integrity gate booleans passed. The numeric G1–G5 results are reported above without adding post-hoc acceptance thresholds.

### Scientific conclusion and next work

The confirmatory campaign supports a bounded conclusion: **Architecture B materially improves relational retention when the observation stream is unavailable and no external replay window is supplied; Architecture A matches B when that evidence window is supplied, with a much smaller persistent state.** G1 and G3 show parity under the tested bounded task families, and G4 shows lifecycle/rollback parity under the frozen synthetic residual profile. G5 makes the trade-off explicit: B buys persistence with growing serialized memory and slower queries.

This is not a claim that B is generally superior. The result motivates the next experiment rather than ending the architecture question:
1. Investigate a more efficient persistent representation for B (indexing, compression, selective retention) without changing the current frozen result.
2. Compare A's external replay cost against B's persistent storage cost under a clearly matched *total* resource budget, including the evidence-window memory/transfer/latency for A.
3. Expand temporal conditions beyond the single controlled outage/late-arrival profile.
4. Expand G3 into a calibrated risk/coverage curve with harder near-miss paths and contradictory evidence.
5. Expand G4 to multiple drift families, drift magnitudes, switching rates and detector calibration.
6. Only after those improvements consider E08 transfer; keep E09 as the formal temporal-memory/relational-organisation reintegration point.

The claim boundary remains: within-vocabulary, task-family-bounded synthetic relational worlds, depth 2–4, fixed candidate enumeration plus learned ranking, and the tested P0/P6 implementation. No open-world topology discovery, OOV relation transfer, arbitrary-depth composition, E08 transfer, global stability, or Grassmannian advantage is established.
