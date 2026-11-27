# bAbI Task Expansion — Evidence and Acceptance Preparation v1.0

**Status:** Phase B adapters passed source-wide audit; learning campaign not authorized  
**Parent:** Task 3/5 pilot branch commit `58a13629d1ac7257a3e0627dacb35c3624217236`  
**Scope:** Tasks 11, 14, 19 first; Task 13 second; Tasks 2 and 4 as controls.

## 1. Isolation and intent

This is a separate workstream. It must not edit the frozen Task 3/5 protocol, source freezer, annotations, partitions, campaign runner, workflows, artifacts, or acceptance thresholds. The existing Task 3/5 runner is explicitly restricted to task IDs 3 and 5; it is not a generic task adapter. The current annotation grammar also explicitly accepts only Tasks 3 and 5. New tasks therefore require task-specific adapters and must not be routed through the current parser by loosening its task-ID guard.

## 2. Verified source record format

The official bAbI v1.2 English text convention is:
- Each story is a sequence of numbered lines; a new story begins when the line number resets to `1`.
- A statement line contains the numbered natural-language sentence.
- A question line contains the numbered question followed by tab-separated gold answer and supporting-fact line numbers.
- The supporting-fact field is a whitespace-separated list of line numbers referring to statements in that same story.
- Story boundaries, question line, answer and support IDs must be retained exactly. Do not split a story across partitions.
- The archive is the pinned v1.2 archive in the adjacent JSON manifest. The exact member names, bytes and hashes for all six new tasks must be verified from the archive before implementation is treated as source-verified.

The examples in the original bAbI paper and public task documentation establish the task semantics: Task 11 uses singular pronoun coreference; Task 13 uses compound antecedents and plural pronouns; Task 14 asks about event order using temporal expressions; Task 19 composes relative spatial directions into an ordered path. They do not substitute for a byte-level audit of the pinned en-10k files.

## 3. Evidence mapping

| Task | L0 observed/native features | L1 explicit relational evidence | L2 retained context |
|---|---|---|---|
| 11 | mentions, pronoun/person/number, source time | mention-of and coreference edges to antecedent entity | entity state plus mention-chain summary |
| 14 | event features, temporal cues, observation time | event-time anchors and BEFORE/AFTER/SAME_TIME edges | ordered event context and temporal index |
| 19 | endpoints, direction, source edge | directed spatial edges, inverse and compositional path edges | ordered route/path state |
| 13 | plural mentions and group membership cues | entity-set membership and plural coreference | group state with membership-sensitive updates |
| 2 | observed facts and object/entity features | two-edge support chain | two-hop evidence summary |
| 4 | subject/relation/object tuple | directed binary relation and explicit inverse | relation-query context |

These are proposed semantic encodings, not claims that the current runtime already implements them.

## 4. Task-specific prediction and evaluation contracts

The machine-readable manifest defines target names, task-specific metrics, baselines and known ambiguity risks. The shared four-target Task 3/5 prediction contract is not sufficient by itself:
- Task 11 needs entity-binding and coreference-edge forecasts.
- Task 14 needs temporal-anchor and event-order forecasts; event time must remain distinct from observation time.
- Task 19 needs edge-direction and ordered path-composition forecasts.
- Task 13 needs set-valued antecedent and plural-coreference forecasts.
- Tasks 2 and 4 need depth-specific support-chain and directed binary-relation controls.

Every forecast must retain issue cutoff, target horizon, provenance and lifecycle status. Abstentions remain explicit and are scored; non-applicable targets are withdrawn with reason. Per-phase issued/scored/withdrawn/expired/coverage counts must reconcile exactly. No metric aggregation across tasks may obscure task-specific failure.

## 5. Case-study progression

1. **Task 11:** establish entity identity binding under singular coreference.
2. **Task 14:** establish temporal anchoring and ordering, including partial/incomparable times.
3. **Task 19:** establish directed spatial composition and exact route reconstruction.
4. **Task 13:** extend coreference to set-valued compound antecedents and membership-sensitive updates.
5. **Task 2 control:** verify a simpler two-support composition depth.
6. **Task 4 control:** verify directed binary relation representation without assuming transitive closure.

Tasks 11, 14 and 19 are independent case studies. Their first-wave readiness work may proceed in parallel, but no combined score or shared task parser is assumed. Task 13 follows after Task 11's entity-binding contract is reviewed. Tasks 2 and 4 are controls, not primary evidence for the harder capabilities.

## 6. Partition and campaign rules

Derive each task's partitions independently from its own official training file. Keep whole stories intact. Do not copy Task 3/5's story counts, warm/online ratio, hashes or confirmatory seeds without measuring the new task source and approving a task-specific freeze. Quarantine official test files until parser and annotation audits are complete. Confirmatory evaluation must use a separate fixed-seed generated challenge with novel entity/time/topology combinations and label-free runtime inputs.

Retain HLA/HLB paired inputs and the six existing ablation semantics only after verifying each task's enabled channels are meaningful. In particular, the task-error predictor must use real observed task outcomes; no artificial errors may be injected to make an ablation appear active. Do not pool candidate selection across tasks.

## 7. Acceptance gates before any campaign

- **X0 Source identity:** archive identity and all six task member names, byte lengths, SHA-256 hashes and line/story counts verified.
- **X1 Format coverage:** parser accepts every official train/validation/test syntax variant in the selected task files; unrecognized lines fail closed and are counted.
- **X2 Annotation integrity:** gold answer/support labels are evaluator-only; every support ID resolves to a same-story statement; no support occurs after its query; story IDs and provenance are unique.
- **X3 Partition integrity:** fit/warm/online/validation are disjoint whole-story sets; test remains quarantined; all split hashes are frozen.
- **X4 Semantic oracle:** independently written task oracle agrees with official answer/support labels on every eligible query; ambiguous/incomparable cases have explicit quarantine policy.
- **X5 Runtime contracts:** task-specific evidence schema, prediction targets, causal scoring, abstention, forecast lifecycle and HLA/HLB input parity pass tests.
- **X6 Baselines:** all listed baselines run on identical partitions and report exact-match, witness, abstention and resource metrics.
- **X7 Pilot authorization:** task-specific thresholds, seed set, workload estimate, worker sharding and manifest hash reviewed before execution.

A CI pass only establishes implementation/contract acceptance. It does not establish that the architecture has learned coreference, temporal reasoning or path composition.

## 8. Phase B implementation boundary

The separate module `src/rgm/experiments/babi_expansion_adapters.py` now implements independent parsers and input-only adapters for Tasks 11, 14 and 19, with task-specific deterministic reference predictors. It does not import or widen the Task 3/5 parser.

- Task 11 resolves constrained singular `he/she` mentions to the nearest compatible explicitly named entity, emits a mention-to-entity binding and answers current-location queries. Unknown or unanchored pronouns fail closed.
- Task 14 parses the source's four temporal anchors (yesterday, this morning, this afternoon, this evening), keeps event-time ordering distinct from observation time, and answers "Where was X before Y?" from the immediately preceding temporal location.
- Task 19 converts "X is direction of Y" into a directed edge from Y to X, adds the explicit inverse edge, and composes an ordered path. It preserves edge witnesses and abstains when shortest paths disagree on the direction sequence.

The `ExpansionStory` and `ExpansionQuery` inputs contain no gold answers or support IDs. `GoldLabel` is a separate evaluator-only record. `scripts/audit_babi_expansion.py` derives deterministic 90/10 whole-story fit/validation partitions from the en-10k training members. Official test members are parsed with labels disabled and are not emitted as learner inputs.

The Phase B validation workflow reacquires the pinned external source members, runs the adapter contract tests, parses all six train/test members, verifies train support references, audits training oracle predictions against evaluator-only labels, freezes partition hashes and uploads evidence. It is an acceptance workflow, not a learning campaign.

**Important limitation:** Task 11's constrained name-gender prior and nearest-compatible-antecedent resolver is an explicit symbolic baseline/adapter, not a learned coreference model. Task 14's four-bucket temporal parser is limited to the source grammar. Task 19's BFS is a deterministic compositional baseline. None of these establishes HLA/HLB learning capability.

## 9. Remaining Phase B acceptance gates

1. Run the full source-wide workflow and inspect every task's parser coverage, oracle mismatches and quarantine rate.
2. Confirm exact 90/10 whole-story counts, disjointness, source-order preservation and deterministic hashes.
3. Review the task-specific baseline outputs and support-witness behavior, especially Task 11's antecedent witnesses and Task 14's temporal tie policy.
4. Add task-specific prediction target serialization and HLA/HLB parity only after the adapter audit passes.
5. Define and review thresholds, workload estimates, worker sharding and candidate selection separately for each task.

No learning campaign may start until these gates are reviewed and explicitly authorized.

## 9. Verified Phase B result

The source-wide adapter validation passed on 2026-11-27:
- Workflow run 45993209014: success.
- Repository unit/invariant matrix run 45993208940: Python 3.10 and 3.12 both success.
- Artifact ID 15195305886, SHA-256 39d7247dd0ab0c3f015405d8933ef0a06c111e103d2911775dae21ef8794d767.
- Task 11, 14 and 19 training oracle exact match: 10,000/10,000 each; zero quarantines.
- Derived fit/validation partitions are 90/10 whole-story splits with counts of 1,800/200 stories for Tasks 11 and 14, and 9,000/1,000 for Task 19.
- Official test members were parsed label-free (200, 200 and 1,000 stories respectively); no test labels or inputs were emitted.

The result verifies source parser and deterministic symbolic-oracle agreement. It is not a learning result and does not authorize campaign execution.

## 10. Current known implementation boundary

The current code has:
- a numbered-story parser and evaluator-only answer/support label separation for Tasks 3 and 5;
- a deterministic template grammar for Task 3 MOVE/PICK_UP/DROP and Task 5 GIVE;
- a whole-story source split and a deterministic warm-start/online story split;
- a structured query/event model whose task-ID validation is limited to 3 and 5;
- a runner CLI with `choices=(3, 5)`, and a freezer whose source-member table and partition generation are limited to 3 and 5.

Consequently, this branch adds only the expansion contract, machine-readable task configurations and schema acceptance tests. It does not claim a parser, task oracle, campaign runner, or experiment is implemented for the new tasks.


## Phase C runtime and prediction-contract acceptance — PASS

The Tasks 11, 14 and 19 adapters are now connected to the existing H1 runtime through `BabiExpansionRuntime`, `HierarchicalRuntimeDirector`, HLA/HLB, immutable n-ary evidence and the existing prediction journal primitives.

- Runtime/prediction-contract PR #53 merged at `0e4da940644033b784fc65a4ef2b4ab64b66f7ba`.
- CI runs `45995326040` and `45995337324` passed on Python 3.10 and 3.12.
- Each Python matrix job passed 21 expansion adapter/runtime/protocol tests, 60 integrated HLG lifecycle tests and 40 frozen Task 3/5 regression tests (121 total).
- Task 3/5 files and campaign protocol were not changed by the runtime integration.

## First-wave learning campaign protocol — FROZEN, NOT AUTHORIZED

The protocol is frozen in `HLG_BABI_EXPANSION_LEARNING_CAMPAIGN_v1_0.json` and its companion Markdown document.

- Tasks 11, 14 and 19; HLA and HLB; six learning/ablation conditions; seeds 953100–953109.
- 360 matched run units, assigned deterministically to four shards (90 units each).
- 3.6 million fit-plus-validation query presentations.
- Task-specific baselines, level metrics, integrity/performance thresholds, paired evaluation, artifact provenance and retry-safe sharding are specified.
- Official test labels remain sealed. Task 3/5 remains frozen and isolated.

**Important:** this freezes the protocol only. No learning run, validation campaign or confirmatory campaign is authorized or launched. Remaining launch gates are baseline implementation, nested warm-start/online partitioning, four-shard failure/retry/evidence preflight, measured resource budgets, generated-confirmatory protocol and explicit authorization.


## 11. Current preflight work and execution boundary — 2026-11-27

This section supersedes earlier "remaining Phase B" wording where it conflicts with the later Phase C acceptance record. Historical sections are retained as the development sequence, not as the current status.

**Current workstream:** continue only on `research/babi-task-expansion-v1`. The frozen Task 3/5 campaign is parked and must remain untouched. No Task 11/14/19 learning campaign has been launched or authorized.

### Accepted foundation (do not re-open without a concrete defect)

- Phase B source-wide adapter acceptance passed: Tasks 11, 14 and 19; 10,000/10,000 deterministic oracle matches per task, zero quarantines, whole-story 90/10 fit/validation partitions, and official test data parsed label-free.
- Phase C runtime/prediction-contract integration passed. PR #53 merged at `0e4da940644033b784fc65a4ef2b4ab64b66f7ba`; recorded CI matrix passed on Python 3.10 and 3.12, including expansion runtime/protocol, integrated evidence lifecycle and frozen Task 3/5 regression tests.
- The first-wave protocol remains frozen: Tasks 11/14/19 × HLA/HLB × six conditions × ten seeds (953100–953109), 360 run units, four shards of 90, and 3.6 million fit-plus-validation query presentations. Protocol freeze is not execution authorization.

### Preflight implementation progress

The latest recorded implementation work has advanced beyond the original Phase C "remaining gates" list:

1. **Task 11 leakage boundary:** implementation work separates raw mention observations from inferred antecedent/entity bindings. Equivalent leakage-boundary audit is required for Tasks 14 and 19; do not treat Task 11 completion as closing all three audits.
2. **Independent baselines:** reviewed non-oracle baseline predictors are being added as an independent suite. Existing symbolic adapter/oracle predictors and source-audit predictors must not be counted as the full reviewed baseline suite.
3. **Nested partitions and deterministic workload:** deterministic partition/shard machinery is being added so warm-start and online adaptation are nested and whole-story safe, with deterministic unit assignment and reproducible aggregation.
4. **Four-worker preflight:** CI matrix/wiring and dry-run evidence are still required. A manifest describing four shards is not proof that four workers execute, retry, preserve evidence and aggregate correctly.
5. **Resource preflight:** runtime, throughput, peak memory and storage must be measured on representative workloads and compared with declared budgets. Estimates alone do not pass this gate.
6. **Confirmatory protocol:** a separate generated-challenge manifest has been versioned with fixed seeds, story counts and SHA-256 provenance. Its generator, label separation, reproducibility and challenge validity still require CI verification before it can be treated as accepted.

The latest recorded work note says the confirmatory manifest uses three fixed seeds and 384 stories per task. This is a preflight specification under verification; it does not replace or silently alter the frozen ten-seed learning protocol. Record exact manifest path, hash, CI run and generated outputs when verified.

### Remaining gates before campaign authorization

- Finish and test the Task 11 raw-mention/inferred-binding separation; audit equivalent boundaries for Tasks 14 and 19.
- Complete and independently evaluate the reviewed non-oracle baseline suite on the exact task-specific partitions.
- Prove nested warm-start/online partitions are disjoint at whole-story granularity and preserve all frozen hashes.
- Pass a real four-worker dry run covering shard assignment, retries, failure recovery, evidence completeness, idempotence and deterministic aggregation.
- Complete measured resource preflight for runtime, throughput, peak memory and storage.
- Verify and freeze the separate generated-confirmatory challenge: specification, generator, fixed seeds, story counts, input/label separation and hashes.
- Run all CI and preflight acceptance checks successfully, inspect their artifacts, and record the exact commit/run IDs and artifact hashes.
- Obtain explicit user authorization before any learning or confirmatory campaign is launched.

**No-go rule:** any failed, missing, cancelled, incomplete or unverified gate keeps `execution_authorized=false`. Do not launch the 360-unit campaign merely because adapter/runtime CI passes or because the protocol and manifests exist.

### Research interpretation guardrails

- Adapter oracle agreement validates deterministic parsing/semantics for the source grammar; it is not evidence of learned capability.
- Runtime contract tests validate integration and lifecycle behavior; they do not demonstrate generalisation.
- Baseline comparisons must be non-oracle and independently evaluated. Oracle upper bounds must remain clearly labelled and excluded from competitive baseline claims.
- Report task-specific results separately; do not pool Tasks 11, 14 and 19 into a score that conceals a failed capability.
- Preserve official test labels as evaluator-only and keep generated-confirmatory evidence separate from official test evidence.
- Do not modify the frozen Task 3/5 branch, protocol, artifacts or thresholds as part of this workstream.


## 12. PR #55 preflight investigation — 2026-11-27

**Active implementation:** [PR #55 — Implement leakage-safe bAbI expansion execution preflight](https://github.com/johnsnowman488-oss/relational-grassmannian-research/pull/55)  
**Head branch:** `research/babi-expansion-preflight-v1`  
**Head commit inspected:** `98c88031477dda828b62fda0d34de20e882e16b2`  
**Base:** `research/babi-task-expansion-v1`  
**PR state:** open, not merged. The head is 29 commits ahead and 2 commits behind the base after this ledger update; GitHub currently reports it mergeable.

### CI status and first blocking defect

The latest inspected head commit has three associated workflow runs, all failed:

- `46000838110` — controlled execution preflight: Python 3.10 and 3.12 full-suite jobs failed; preparation, native build, four-shard and aggregate jobs were skipped.
- `46000838109` — runtime/prediction-contract workflow: Python 3.10 and 3.12 jobs failed.
- `46000838112` — Phase B adapter validation workflow: failed.

All three failures converge on one test-fixture defect in `tests/test_babi_expansion_adapters.py::test_task11_parser_preserves_pronoun_without_inventing_cross_story_binding`. The fixture contains escaped backslash-n characters rather than actual newline characters. The parser therefore receives one malformed physical line and raises an unsupported Task 11 statement error. The failure is in the test fixture, not evidence that raw-pronoun parsing itself failed. Correct the fixture to contain actual line breaks and assert the intended two-story boundary explicitly (each line-number reset to 1 starts a new story); then rerun all three workflows. Do not weaken the parser to accept malformed input.

The full-suite log reports 552 tests passed and one failed on Python 3.10; the focused workflow reports 21 passed and one failed. No downstream preflight artifact exists from these runs, so none of the new source/partition/baseline/native/shard/aggregate gates has yet been demonstrated by this PR's CI.

### Implemented in PR #55, pending acceptance

- Task 11 runtime inputs now contain surface mention, pronoun flag, location and provenance only; parser-side antecedent/entity binding was removed. Task 11 L1 ingestion no longer fabricates a coreference edge.
- Independent baseline predictors were added for Tasks 11, 14 and 19, with a validation scorecard and answer/witness/coverage metrics.
- Deterministic whole-story 90/10 fit/validation partitioning and nested 80/20 warm-start/online partitioning were added.
- The 360-key manifest and four modulo-assigned 90-unit shards were added.
- Retry-safe per-unit evidence and injected mid-shard failure/retry logic were added.
- A pinned Aberconics native HLA/HLB no-learning sample was added.
- A generated confirmatory challenge was added: three seeds (971101–971103), 128 stories per seed per task, 384 per task and 1,152 overall.

These are implementation facts from the PR diff, not accepted gate results.

### Further blockers and scientific design risks found in source review

1. **Task 11 confirmatory identifiability/input mismatch.** The generator randomly assigns genders to four novel entities and randomly assigns pronoun events to those entities. With multiple entities sharing a gender, the pronoun surface alone does not identify which entity was intended; the generator's gold state may depend on a hidden random choice. It emits a `grammatical_gender` field, but `Task11MentionEvent` and `to_nary_event` do not carry that field into the runtime. The existing nearest-compatible baseline also relies on a hard-coded known-name gender table and cannot use the novel generated names. The challenge must be redesigned so every pronoun antecedent is observable/identifiable under the declared input contract, and the exact same model-visible features are consumed by the runtime and evaluator. Do not accept the current Task 11 challenge as a valid coreference generalisation test.
2. **Baseline target-level coverage is incomplete.** The baseline scorecard currently reports answer exact match, support-witness recall, false-witness rate and coverage. The frozen task contracts additionally require direct target-level evidence such as Task 11 antecedent/coreference-edge quality, Task 14 temporal-order/relation quality, and Task 19 edge/path composition diagnostics. In particular, the Task 11 baseline returns answer and witness IDs but no explicit predicted antecedent edge set. Add task-level target metrics or narrow the protocol claims before using this scorecard for candidate-selection readiness.
3. **Runtime target materialization remains unproven.** The runtime declares L0/L1/L2 target schemas, but Task 11's observed ingestion intentionally creates no L1 coreference relation. The inspected preflight PR does not demonstrate causal issuance/scoring of Task 11 binding forecasts or equivalent task-specific L1/L2 target observations. The later learning runner must define where these targets come from without turning evaluator-only support labels into learner inputs. If the bAbI labels do not provide direct coreference-edge supervision, document and test the alternative self-supervised/weak-supervision contract explicitly.
4. **Resource budget is partial by design.** The native script measures a small no-learning sample (8 fit stories per task per shard, HLA and HLB; 48 story-runs per shard). The 360-unit shard runner executes symbolic baseline presentations and orchestration only; it does not run HLA/HLB learner updates. The aggregate explicitly excludes native learner compute. This is useful orchestration and no-learning runtime evidence, but it is not a measured full-learning campaign runtime or a complete resource budget. Keep that distinction in the gate status and obtain a justified learning-cost estimate or separately authorized bounded learning microbenchmark before claiming the campaign resource gate closed.
5. **Native projection is coarse.** Aggregate projection uses one pooled seconds-per-story value across tasks and architectures, even though event counts and per-task runtime differ. Report task/architecture-specific sample rates and event-normalized rates; avoid presenting the pooled projection as a reliable campaign estimate.
6. **PR/base synchronization.** The PR branch is two commits behind the base because the dedicated ledger was updated after the PR branch point. GitHub reports mergeable at inspection, but synchronize the branch before final merge and rerun affected CI on the final merge candidate.

### Required next sequence

1. Repair the newline fixture only; preserve the strict parser and assert two distinct stories.
2. Rerun all three currently failing workflows and inspect complete logs.
3. Only after tests pass, run source acquisition/audit, confirmatory generation/verification and partition/baseline preparation; inspect artifacts and hashes.
4. Redesign Task 11 generated-confirmatory inputs/labels to remove hidden antecedent ambiguity and align generator/runtime feature schemas.
5. Add or explicitly defer target-level baseline metrics and define the Task 11 L1 supervision/forecast lifecycle.
6. Complete four-shard no-learning/retry/aggregation CI, then review exact 360-key coverage and evidence.
7. Keep resource acceptance marked partial until the native learner cost is measured or a justified bounded estimate is independently reviewed.
8. Synchronize PR #55 with the updated base, rerun final CI and inspect every artifact.
9. Keep `execution_authorized=false` until every required gate is accepted and explicit authorization is given.

**Current decision:** PR #55 is useful and contains substantial gate-closing work, but no outstanding gate is considered passed by its latest CI. The first immediate repair is a malformed test fixture; the Task 11 confirmatory identifiability and runtime-feature mismatch are the most important design-level blockers to resolve before accepting the generated challenge.


## 13. PR #55 preflight acceptance update — 2026-11-27

**Accepted implementation code head:** `02538ee794ddd9df67297d4256b752ebf2c01894`  
**Latest PR head before base synchronization:** `fa90febc531df65a3940378b17e7aa1cc4dedd85` (adds the measured resource-budget evidence to the implementation branch).  
**Base tip before synchronization:** `5f4726c3300664c566add3db7fb87184ff0e391b`; the PR branch has 59 commits ahead and six base-only commits since common ancestor `847fc6e3d0766012e110ad1c9a8c691901b355ae`. The six base-only changes are the two research-ledger files. A two-parent merge will preserve the preflight implementation and both updated ledgers; final CI on the synchronized merge commit is still required.  
**PR:** [#55 — Implement leakage-safe bAbI expansion execution preflight](https://github.com/johnsnowman488-oss/relational-grassmannian-research/pull/55), still open and not merged at the time of this ledger update.

### CI acceptance

All three requested workflows now pass on the implementation head:

- Phase B independent adapter validation: run `46066166585` — success.
- Runtime and prediction-contract acceptance: run `46066166586` — success.
- Controlled execution preflight run #61: `46066166623` — success, including the native build, source/partition/baseline/confirmatory preparation, all four shard jobs and final aggregate.

The full repository test suite passes on Python 3.10 and 3.12. The integrated runtime/prediction-contract matrix passes on both versions, including the frozen Task 3/5 regression protection. The earlier fixture failure was repaired using actual physical newlines and explicit two-story assertions; the parser was not relaxed. The native bridge now reads the pinned `PersistentHierarchyRuntime.step_count` property rather than looking for a nonexistent key in `get_state()`.

### Source, partitions and baselines

The source acquisition/audit job passed. bAbI v1.2.0, en-10k, CC BY 3.0 members were freshly downloaded from immutable repository commit `0051751275841561267b1c6f5d9116b985521df1`; each member passed byte-length/Git-blob identity checks and SHA-256 recording. No archive-byte identity is claimed. All three tasks have 10,000 training queries and 1,000 official-test queries; official test files were parsed label-free and no official test labels or queries entered the experiment.

The prepared 90/10 train-derived whole-story partitions and nested 80/20 warm-start/online partitions passed their frozen count and ID-hash checks:

| Task | Fit stories / queries | Validation stories / queries | Warm-start stories | Online stories | Official test stories |
|---|---:|---:|---:|---:|---:|
| 11 | 1,800 / 9,000 | 200 / 1,000 | 1,440 | 360 | 200 |
| 14 | 1,800 / 9,000 | 200 / 1,000 | 1,440 | 360 | 200 |
| 19 | 9,000 / 9,000 | 1,000 / 1,000 | 7,200 | 1,800 | 1,000 |

All partitions are whole-story, disjoint and deterministic. The manifest records separate story-ID and query-ID SHA-256 values for each phase. The frozen 360 run-unit protocol remains 3 tasks × 2 architectures × 6 conditions × 10 seeds, with 90 unit keys per worker.

Independent baseline validation covered 1,000 validation queries per task:

- **Task 11:** nearest-compatible-antecedent answer exact match 1.000; recency-only 0.704. Direct antecedent/coreference-edge metrics on the official validation split are **NOT AVAILABLE**, because the raw bAbI Task 11 evaluator labels do not provide gold antecedent edges. Do not infer L1 coreference quality from location-answer accuracy or score weak labels against themselves.
- **Task 14:** lexical temporal-cue baseline answer and temporal-relation exact match 1.000; source-order-only temporal-relation exact match 0.420 (target F1 approximately 0.525).
- **Task 19:** breadth-first-search answer, directed-edge/path target F1 and ordered-path exact match 1.000; direct-edge-only abstains on the multi-edge paths and scores 0.000.

Target-level metrics are now explicit in the scorecard. The Task 11 limitation is retained as unavailable on official validation rather than filled with an unreviewed proxy.

### Task 11 confirmatory input and supervision repair

Generated-confirmatory protocol v1.1 supersedes the non-identifiable v1.0 challenge. It uses 3 fixed seeds (971101–971103), 128 stories per seed per task, 384 stories per task, 1,152 overall. The Task 11 generated schema carries an explicit synthetic grammatical-gender cue through the same typed event consumed by runtime ingestion. Each story has two distinct model-visible gender anchors, so each generated pronoun has exactly one compatible prior name anchor. Antecedent IDs, binding edges and L0/L1/L2 labels remain evaluator-only. This is a controlled synthetic task schema, **not** a claim that raw bAbI contains a structured gender field.

The Task 11 runtime does not ingest a coreference edge as an observation. The conservative weak-supervision rule emits a pseudo-binding only when exactly one compatible prior named entity exists; otherwise it abstains. The separate training-only route is now implemented: L0 mention-binding targets update the event-role learner, L1 `corefers_with` targets update the semantic-relation learner, and L2 entity-scoped location/context transitions update the context learner. Target errors also update temporal credit through distinct `task11:L0/L1/L2` eligibility channels.

The separation from durable evidence is tested on both HLA and HLB. Raw source mentions are the only events admitted to HLB's evidence store; derived n-ary target events and coreference relations are passed only to learner components and retain their provenance in the learner journal. Ambiguous pronouns remain recoverable raw observations but are masked from inferred binding updates. Tests also verify learning-disabled parameter immutability and replay of level-filtered SOE eligibility after checkpoint restore. This closes the **implementation-routing** gate, not the learning-effectiveness or generalisation gate. The target rule is still noisy weak supervision, not gold coreference truth; no calibrated numeric pseudo-label confidence or independently annotated Task 11 antecedent-edge evaluation is available.

Confirmatory generation and verification passed: each task has 384 input rows and 384 separate evaluator-label rows, with exact query-ID parity, file hashes, deterministic repeat verification and no official-test access. Task 11 generated input SHA-256 is `edc957cad4d1274d968611584c8288b53fb23332eaefe34c934ec153a7195276`; its evaluator-label file SHA-256 is `174bddeb44c629ef15c876da8108868fffb92587da0fde526db68e4d3132df65`. The internal confirmatory manifest fingerprint is `e5e6c0c981573c5e42ef4b5b449d8962365aa326a2b63068d39c1f18d02c6c1f`. These generated outputs are not official bAbI test evidence and must not be used for candidate selection.

### Four-worker preflight and resource decision

Run #61 accepted all 360/360 keys, 90 per shard, and 3,600,000 symbolic query presentations / 7,200,000 baseline prediction presentations. Retry integrity was exact: zero duplicate, missing, wrong-shard or mixed-manifest keys. All four workers preserved 45 completed keys through an injected failure and completed the remaining 45 on retry. There were zero HLA/HLB learning updates and zero official-test queries.

The native no-learning sample passed on pinned Aberconics commit `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de`: 192 story-runs, 1,692 event/native steps, zero parameter changes and zero labels loaded. The aggregate resource evidence reports 220.768 summed worker-seconds, 66.649 seconds maximum for one worker, 99.586 MiB maximum worker RSS, 1.326 MiB maximum Python allocation peak and 2.126 MiB shard artifact storage. Native no-learning sample peak RSS was 173.450 MiB and Python allocation peak 48.344 MiB. Task/architecture-specific native story/event rates and no-learning projections are stored in `HLG_BABI_EXPANSION_RESOURCE_BUDGET_v1_0.md`.

**Accepted resource gate remains PARTIAL.** Run #91 (ID `46070052456`, commit `289acf71`) passed the 360/360 symbolic retry/aggregation and pinned native no-learning checks. It does not qualify full learning-campaign resource cost.

A later workflow revision accidentally attached a learning-enabled cost job to automatic PR/push CI. Two duplicate runs (#97 `46071079818` and #98 `46071085170`, commit `db0b34c9`) each completed 192 fit-story episodes. They were not explicitly authorized and are quarantined as diagnostic-only, not accepted gate evidence. Across the two reports, observed episode update time was 6.27–7.44 cumulative seconds for 1,692 events; event throughput was 227–270 events per update-second; Python learner snapshot time was 0.225–0.260 seconds total; restore time 0.286–0.337 seconds total; serialized LearningRuntime checkpoint payload was about 7.96 MB; maximum worker RSS was about 181.5 MiB. These episodes used a fresh adapter per story, so they do not measure persistent cross-story model growth, consolidation/promotion/rollback orchestration, or full campaign execution. Neither run loaded evaluator labels, official test queries or generated-confirmatory labels. They remain **UNAUTHORIZED_DIAGNOSTICS_NOT_GATE_EVIDENCE**.

The workflow has since been corrected: learning-cost jobs require a manual `workflow_dispatch` with `enable_learning_cost_microbenchmark=true`. No future PR/push run should launch that job. The two diagnostic runs do not authorize a repeat or the full learning campaign. A separately authorized and reviewed measurement is still required for resource-gate closure.

### Current gate decision and next work

- Task 11 raw-observation/evaluator separation, Tasks 14/19 boundary audits, source freeze, deterministic partitions, reviewed baseline execution, confirmatory v1.1 validation and the four-worker retry/aggregate preflight: **PASS**, subject to the Task 11 official-label limitation above.
- Task 11 target forecast/scoring contract: **PASS at the isolated contract/test level**.
- Task 11 L0/L1/L2 HLA/HLB learner routing, evidence isolation, ambiguity masking, learning-disabled immutability and SOE eligibility replay: **IMPLEMENTED_AND_TESTED**. This is not evidence of improved task performance or coreference generalisation.
- Task 11 official validation antecedent-edge metrics: **UNAVAILABLE** until independent annotations are reviewed.
- Resource qualification for the full learner campaign: **OPEN — PARTIAL**; the accidental learning-cost diagnostics are quarantined and do not close the gate.
- Full 360-unit learning campaign: **FROZEN_NOT_AUTHORIZED**; explicit authorization is still required.
- Frozen Task 3/5 pilot branch and artifacts: **PARKED_UNTOUCHED**.

The next research gate is to assess the weak-target route with an independently reviewed Task 11 coreference evaluation set, test candidate adaptation/rollback under an authorized bounded protocol, and obtain explicit approval before any new learning-cost benchmark or full campaign. Do not treat the accidental diagnostic runs as an authorized experiment or a learned-capability result.


### Current PR and workflow authorization checkpoint — 2026-11-27

PR #55 is open on `research/babi-expansion-preflight-v1`, current head `e0ef1b99e3678db180315ce9a311b5412e33761a`, base `research/babi-task-expansion-v1` at `5f4726c3300664c566add3db7fb87184ff0e391b`. The branch is 0 commits behind base. On this head, the Phase B source audit and runtime-contract matrix passed, and full-repository tests passed on Python 3.10 and 3.12. The current no-learning preflight reruns (#99/#100) were still executing their four-shard retry/aggregate stage at the time this ledger update was written.

The workflow guard was corrected after the two unauthorized auto-runs: learning-cost jobs now require a manual `workflow_dispatch` and the explicit boolean `enable_learning_cost_microbenchmark=true`. Automatic PR/push workflows do not satisfy this condition. `execution_authorized` remains `false` and the full 360-unit learning campaign remains frozen.