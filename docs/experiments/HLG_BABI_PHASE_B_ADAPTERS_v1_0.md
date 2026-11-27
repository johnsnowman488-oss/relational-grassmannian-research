# HLG bAbI Phase B — Independent Task Adapters v1.0

**Status:** implementation prepared; full source-wide CI audit pending  
**Tasks:** HLA / Task 11, HLB / Task 14, HLC / Task 19  
**Source freeze:** Phase Q selected-member manifest v1.2  
**Campaign status:** not authorized

## 1. Phase B objective

Turn the Phase Q-frozen source members into three independent, task-specific evidence adapters. Each adapter exposes the task's observable input structure, source provenance and query objects without leaking gold answers or support labels. Each has a deterministic symbolic reference predictor for parser/oracle acceptance and baseline comparison. These reference predictors are not HLA/HLB learned results.

The existing Task 3/5 parser, structured schema, annotations, runner, protocol and pilot branch remain untouched.

## 2. Adapter boundaries

### HLA — Task 11: singular coreference

**Observed input**
- Named entity movement statements.
- Singular pronominal mentions (he, she) with their source-line position.
- Location updates and explicit location questions.

**L0**
- Mention surface, mention type, grammatical gender cue, source/observation line and destination state.

**L1**
- Mention node, entity-binding edge, and COREFERS_TO edge from pronoun mention to the antecedent mention.
- The edge preserves both source line references.

**L2**
- Per-entity current location and mention-chain context, with no gold antecedent injected.

**Reference baseline**
- Constrained source-name gender prior plus nearest compatible explicitly named antecedent.
- Current-state lookup by resolved entity.
- Unresolved pronouns abstain; cross-story binding is impossible by construction.

**Metrics to preserve**
- Mention-to-entity accuracy, antecedent top-1 accuracy, coreference-edge precision/recall/F1, entity-chain exact match, state-answer exact match, support-witness recall, false-binding rate and abstention rate.

The name-gender prior is a transparent symbolic baseline, not a learned coreference model. Its limits must remain visible in the report.

### HLB — Task 14: temporal ordering

**Observed input**
- Movement assertions with one of four source temporal anchors: yesterday, this morning, this afternoon, this evening.
- "Where was X before Y?" queries.

**L0**
- Event assertion, temporal phrase, normalized event-time bucket, source order and observation time.

**L1**
- Event nodes and temporal precedence relations with exact source witnesses.

**L2**
- Ordered per-entity event history and temporal index.

**Reference baseline**
- Order by temporal bucket, then source-line order for events sharing a bucket.
- Select the event in which the queried entity reaches the target location; answer with that entity's immediately preceding location.
- Abstain if no target event or no prior location exists.

Event time and observation time are separate fields. A fact observed later in the text may describe an earlier time; no event after the query's observation cutoff may be used.

**Metrics to preserve**
- Temporal expression parse accuracy, event-time order accuracy, before/after relation F1, temporal query exact match, temporal witness recall, contradiction rate, abstention rate and causal-cutoff violations.

### HLC — Task 19: path composition

**Observed input**
- Relative-position statement: "The X is direction of the Y."
- Route query: "How do you go from the X to the Y?"
- Gold route uses ordered comma-separated direction codes n, s, e, w.

**L0**
- Endpoint mentions, direction token, source line and observation cutoff.

**L1**
- Directed spatial edge and explicit inverse edge, each retaining the source witness.

**L2**
- Ordered route, intermediate nodes, direction sequence and edge-witness chain.

**Reference baseline**
- Breadth-first search over observed edges.
- Convert a relation "X is east of Y" into a path edge Y --east--> X; generate the inverse X --west--> Y.
- Preserve the exact direction order.
- If equally short paths produce different direction sequences, abstain rather than select one arbitrarily.
- Never invent an edge or use an unobserved shortcut.

**Metrics to preserve**
- Edge-direction accuracy, inverse consistency, path exact match, path-length error, intermediate-node sequence accuracy, edge-witness recall, invalid composition rate, false-path rate and abstention rate.

## 3. Input / label / witness separation

The adapter returns:
- ExpansionStory: story-scoped task ID, typed events and typed queries.
- ExpansionQuery: query identity, source line and task-specific query arguments.
- GoldLabel: evaluator-only answer and official support line numbers.

Gold answers and support IDs do not appear in ExpansionStory, ExpansionQuery, or the predictor inputs. The source audit script writes learner inputs and evaluator labels to distinct JSONL files. Official test members are parsed with labels disabled and are not emitted as learner inputs or validation partitions.

Every support witness must be a prior statement line in the same story. The source freezer independently verifies this for all six selected files; the Phase B script rechecks training support references before annotation.

## 4. Partitions

The v1.2 en-valid-10k configuration is a separate 90/10 train/validation configuration, but its task files are not present in the pinned external mirror commit used for Phase Q. This experiment therefore uses a project-defined deterministic 90/10 split from each frozen en-10k training member.

Partition algorithm:
1. Rank whole stories by SHA-256 of HLG-BABI-EXPANSION-TRAIN-VALID-v1:{task_id}:{story_id}.
2. Assign the first rounded 10% to validation and the remainder to fit.
3. Preserve original source order inside each partition.
4. Keep each story and all its questions together.
5. Retain the official test member only as a sealed source file; parse it label-free for syntax coverage.

Expected story/query totals from the Phase Q source audit:
- Task 11: 2,000 train stories / 10,000 train questions; 200 test stories / 1,000 test questions.
- Task 14: 2,000 train stories / 10,000 train questions; 200 test stories / 1,000 test questions.
- Task 19: 10,000 train stories / 10,000 train questions; 1,000 test stories / 1,000 test questions.

These are source counts, not learned-performance claims. The actual split counts and artifact hashes are generated by the acceptance workflow.

## 5. Source-wide acceptance workflow

The workflow .github/workflows/h1-babi-expansion-adapter-validation.yml:
1. Installs the project test dependencies.
2. Runs isolated adapter, source-freeze and expansion-manifest tests.
3. Downloads the six selected members from the immutable Phase Q external source commit.
4. Parses every train and test member.
5. Rechecks all training support references.
6. Audits task-specific training oracle predictions against evaluator-only gold labels.
7. Creates whole-story fit/validation partitions and separate input/label artifacts.
8. Uploads source and adapter audit evidence, even on failure where files exist.

The workflow must be reviewed for each task's exact-match rate, quarantine count/reasons, partition counts, source hashes and label separation. A green unit-test job alone is not sufficient.

## 6. Acceptance gates before HLA/HLB/HLC learning

- Parser coverage: every source record is accepted; unsupported syntax fails closed and is counted.
- Coreference: no cross-story binding; unresolved pronouns abstain; antecedent witnesses are traceable.
- Temporal: event time is distinct from observation time; same-bucket tie policy is deterministic; no future observation leaks into a prediction.
- Path: edge orientation and inverse are tested; direction sequence is exact; ambiguous routes abstain.
- Oracle: task-specific answer mismatches are quarantined with reasons and remain below the predeclared threshold.
- Partitions: deterministic, disjoint whole-story fit/validation; test labels remain unavailable to the adapter.
- Runtime: prediction targets, HLA/HLB input parity, ablation semantics, forecast lifecycle and per-task baselines are separately tested.
- Authorization: per-task thresholds, seed set, worker sharding, workload estimate and campaign protocol are reviewed before any learning run.

**No learning campaign is authorized by this implementation.** Phase B here means adapter and source-wide contract preparation. The next decision follows inspection of the source-wide CI artifact.
