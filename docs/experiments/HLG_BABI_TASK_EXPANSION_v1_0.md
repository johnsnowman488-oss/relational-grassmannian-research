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
