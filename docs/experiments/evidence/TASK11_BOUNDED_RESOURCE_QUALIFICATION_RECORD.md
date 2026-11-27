# Task 11 bounded persistent-resource qualification — closed record

**Record status:** CLOSED / ACCEPTED  
**Scope:** Task 11 only. This record closes the bounded persistent-resource qualification performed before the Task 11 learning campaign. It does not authorize the 120-unit campaign.

## Immutable identities

| Item | Identity |
|---|---|
| Repository | `johnsnowman488-oss/relational-grassmannian-research` |
| Run 3 | [46076075350](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/46076075350) |
| Run 3 tested commit | `5b6566ac6281e8d28516aee814c1c09b4dac49c5` |
| Run 3 commit context | PR #58 merge; corrected eligibility-ledger instrumentation |
| Run 4 | [46076109811](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/46076109811) |
| Run 4 tested commit | `792483ed4f8d13e2819d31ed71e4ae9d449bfffe` |
| Run 4 commit context | Workflow-only run-name change; same experiment implementation |
| Native Aberconics source commit | `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de` |
| Native shared-library SHA-256 | `38b278a93a5b3fa3b544f55d958a2f7a44bb6e1d39154e63072f5ed7be511e4b` |
| Source member | `qa11_basic-coreference_train.txt` |
| Source member SHA-256 | `edfcd97fecd4a5045af25e1790cf1408856ae362c39521b1b69cd32b88ec0ced` |
| Resource partition manifest SHA-256 | `80317a130e6d8c9064e39ecc2bba857dcd0efc1f78fb255fbb013da433027f24` |
| Dataset source acquisition commit | `0051751275841561267b1c6f5d9116b985521df1` |

The two runs used the same source/partition manifest and native-library digest. Run 4 is a repeat execution of the same bounded resource qualification, not a separate scientific experiment or an independent learning replication.

## Preserved GitHub Actions artifacts

All artifacts below were successfully retrieved and their contents are included in the companion evidence archive. Artifact IDs are retained here for traceability.

### Run 3 — 46076075350

| Evidence | GitHub artifact ID |
|---|---:|
| Aggregate report | `15235980117` |
| Shard 0 | `15234896291` |
| Shard 1 | `15235830276` |
| Shard 2 | `15235335626` |
| Shard 3 | `15235000931` |
| Source and partition manifest bundle | `15234723714` |
| Pinned native runtime and SHA file | `15235805201` |

### Run 4 — 46076109811

| Evidence | GitHub artifact ID |
|---|---:|
| Aggregate report | `15235905808` |
| Shard 0 | `15235755460` |
| Shard 1 | `15235565998` |
| Shard 2 | `15235995406` |
| Shard 3 | `15235590867` |
| Source and partition manifest bundle | `15235210938` |
| Pinned native runtime and SHA file | `15235670696` |

The source-manifest bundle includes the frozen Task 11 training member, quarantined official test member, source audit, and resource plan. The test member was not loaded as an evaluator input in these resource runs.

## Design and interpretation

- 2,000 source stories were frozen; 1,800 were assigned to fit and 200 to a read-only validation partition.
- Four independent worker shards were used.
- **Each shard processed 32 successive stories per architecture through the same persistent learner/runtime for that shard.**
- Across four shards, this yielded 128 story-runs per architecture (256 total across HLA and HLB). This is **not** one uninterrupted 128-story learner trajectory: the four shards are separate worker-local learner/runtime sequences.
- Each story exercised native event updates, state growth, full checkpoints, snapshot/restore and recovery-fingerprint checks.
- No evaluator labels, official test queries, or generated-confirmatory labels were loaded.
- Task 14 and Task 19 remained locked; Tasks 3 and 5 remained unchanged.

## Aggregate measurements

| Metric | Run 3 | Run 4 |
|---|---:|---:|
| Status | PASS | PASS |
| Shards accepted | 4/4 | 4/4 |
| Persistent story-runs accepted | 256/256 | 256/256 |
| Native events | 2,560 | 2,560 |
| Peak worker RSS | 90.004 MB | 90.004 MB |
| Peak Python tracemalloc | 17.395 MB | 17.395 MB |
| Aggregate shard-artifact storage | 261,090 bytes | 261,088 bytes |
| Manifest SHA-256 | `80317a130e6d8c9064e39ecc2bba857dcd0efc1f78fb255fbb013da433027f24` | same |
| Native source commit | `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de` | same |

### Run 3 per-architecture profile

| Metric | HLA | HLB |
|---|---:|---:|
| Events | 1,280 | 1,280 |
| Events / update-second | 106.359 | 103.452 |
| Mean update seconds / story | 0.09402 | 0.09666 |
| Mean checkpoint size | 902,971 bytes | 909,334 bytes |
| Maximum checkpoint size | 1,767,420 bytes | 1,779,673 bytes |
| Mean snapshot seconds | 0.03559 | 0.03797 |
| Mean restore seconds | 0.11967 | 0.12472 |
| Maximum eligibility records | 608 | 608 |
| Maximum observation journal rows | 2,099 | 2,099 |
| Maximum temporal credit weights | 608 | 608 |
| Persistent story-runs | 128 | 128 |

### Run 4 per-architecture profile

| Metric | HLA | HLB |
|---|---:|---:|
| Events | 1,280 | 1,280 |
| Events / update-second | 111.347 | 106.930 |
| Mean update seconds / story | 0.08981 | 0.09352 |
| Mean checkpoint size | 902,971 bytes | 909,334 bytes |
| Maximum checkpoint size | 1,767,420 bytes | 1,779,673 bytes |
| Mean snapshot seconds | 0.03664 | 0.03951 |
| Mean restore seconds | 0.12108 | 0.12747 |
| Maximum eligibility records | 608 | 608 |
| Maximum observation journal rows | 2,099 | 2,099 |
| Maximum temporal credit weights | 608 | 608 |
| Persistent story-runs | 128 | 128 |

Small timing differences between the runs are treated as hosted-CI execution variation, not as learning improvement.

## Acceptance and limitations

Both aggregates report `PASS_TASK11_BOUNDED_PERSISTENT_RESOURCE_QUALIFICATION`. The evidence supports bounded persistent-state growth, checkpoint/restore integrity, native update timing, and worker memory use under the tested 32-story-per-shard sequences.

It does **not** establish:
- Task 11 prediction quality, answer accuracy, learning effectiveness, or generalisation;
- antecedent accuracy, coreference-edge precision/recall/F1, or entity-chain exact match;
- one continuous 128-story learner trajectory;
- a guaranteed wall-clock budget for the full 120-unit campaign.

Both aggregates retain `execution_authorized: false`. This resource record alone does not authorize campaign execution. The separate full-scale 1,800-fit / 200-validation resource preflight and all campaign gates remain mandatory.

## Artifact integrity

The companion evidence archive contains:
- both aggregate JSON reports;
- all eight shard JSON reports;
- the exact source/partition manifest;
- the native shared-library SHA-256 file.

The GitHub artifact IDs above remain the original CI provenance references. The companion archive is a second preserved copy of the evidence payloads; it does not replace the original run records.
