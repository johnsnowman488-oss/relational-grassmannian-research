# bAbI Task Expansion — Evidence and Acceptance Preparation v1.0

**Status:** preparation contract; no new task execution authorized  
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

## 8. Current known implementation boundary

The current code has:
- a numbered-story parser and evaluator-only answer/support label separation for Tasks 3 and 5;
- a deterministic template grammar for Task 3 MOVE/PICK_UP/DROP and Task 5 GIVE;
- a whole-story source split and a deterministic warm-start/online story split;
- a structured query/event model whose task-ID validation is limited to 3 and 5;
- a runner CLI with `choices=(3, 5)`, and a freezer whose source-member table and partition generation are limited to 3 and 5.

Consequently, this branch adds only the expansion contract, machine-readable task configurations and schema acceptance tests. It does not claim a parser, task oracle, campaign runner, or experiment is implemented for the new tasks.
