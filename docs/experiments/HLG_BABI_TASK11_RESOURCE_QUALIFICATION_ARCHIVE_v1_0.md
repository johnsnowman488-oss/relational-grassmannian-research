# Task 11 persistent-resource qualification archive

**Status:** ACCEPTED — bounded persistent-resource qualification only  
**Scope:** bAbI Task 11; HLA and HLB; Tasks 14 and 19 locked  
**Recorded:** 2026-11-27

## 1. Frozen identities

| Item | Identity |
|---|---|
| Research branch at qualification | `research/babi-expansion-preflight-v1` |
| Run #3 source commit | `5b6566ac6281e8d28516aee814c1c09b4dac49c5` |
| Run #4 source commit | `792483ed4f8d13e2819d31ed71e4ae9d449bfffe` |
| Run #3 workflow | [46076075350](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/46076075350) |
| Run #4 workflow | [46076109811](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/46076109811) |
| Pinned Aberconics source commit | `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de` |
| Native shared-library SHA-256 | `38b278a93a5b3fa3b544f55d958a2f7a44bb6e1d39154e63072f5ed7be511e4b` |
| Task 11 source/partition manifest SHA-256 | `80317a130e6d8c9064e39ecc2bba857dcd0efc1f78fb255fbb013da433027f24` |

Both runs compiled the same pinned native source and produced the same shared-library SHA-256. Run #4 changed workflow run identification only; it is a repeated execution of the same qualification, not a different scientific experiment.

## 2. Aggregate acceptance records

Both workflows completed successfully, including repository tests, Task 11 source/partition preparation, native build, four resource shards and aggregate acceptance.

| Record | Run #3 | Run #4 |
|---|---|---|
| Aggregate status | `PASS_TASK11_BOUNDED_PERSISTENT_RESOURCE_QUALIFICATION` | `PASS_TASK11_BOUNDED_PERSISTENT_RESOURCE_QUALIFICATION` |
| Aggregate JSON SHA-256 | `83987a8db9d5e56be1c2c5458cda881cf91f8a23a4cedd51529688e8a8ba5746` | `4e95fb2f2bcfbdeea617fac125e36453f233f46bf9c79c127be5793f37d8b3d8` |
| Acceptance artifact ID | `15235980117` | `15235905808` |
| Acceptance artifact ZIP digest | `sha256:b80be6153f2733e1bb234fde512ef623248f76f2fad94c38be95f2d10b3c8bb8` | `sha256:edeba53c78ad8d0d97521e38976387688bb371b246bbfe442cbf3b62849054ae` |
| Source/plan artifact ID | `15234723714` | `15235210938` |
| Source/plan artifact ZIP digest | `sha256:8586c97c54896e5dd92b9a13414fcc7dcf247a5f773df5f97e2cc4edd2a6b46f` | `sha256:7aa5fb28abea68830b853240dc50b58a7b2e6e5ed0b7fc98b35101c86a1f1f1b` |
| Native artifact ID | `15235805201` | `15235670696` |
| Native artifact ZIP digest | `sha256:df658725ed99b587b0acdbdd01041d45d88b68b82ae232ca968e9d515cf34307` | `sha256:5037c1de2d0d5acc0998da0805ec375877d7b6bbfc093bf6cf48b89fa8fa125b` |

## 3. Eight shard artifacts

Run #3:

| Shard | Artifact ID | ZIP SHA-256 |
|---:|---:|---|
| 0 | `15234896291` | `c39680ac76f53ae7f5fd8f9489b305bcd0bbb46d403e8dfaf76988ac83837b9a` |
| 1 | `15235830276` | `c150fca0a6110627979a4db1da474822d1276df9453f2d5c0c2fe4aea6e54f73` |
| 2 | `15235335626` | `0894f6314155a8b252f1bd36d65f92543eab2afc849aad0c7bc8f093c1aa5d1a` |
| 3 | `15235000931` | `1f0837dfa3ab9f0baf8e768f2ed626b589a3256e9f43a89142703b53c4da472f` |

Run #4:

| Shard | Artifact ID | ZIP SHA-256 |
|---:|---:|---|
| 0 | `15235755460` | `d9ec85dc0a86a2a17d7dc24fc52bd2a19768fe122d41281e0a5ac759f6ef4d34` |
| 1 | `15235565998` | `b249273c02829f53874c5c2c61d154895daa35acb91bad2c0bd07b734ddba809` |
| 2 | `15235995406` | `94696ed48b63a951807f82649d0a76d40887f81c15b1230ccd6e558f756e45d3` |
| 3 | `15235590867` | `dfc7214707e2f687042677dcdcddda33dc86f9b701fdd4e005435da1cebd1c90` |

The GitHub artifact records retain the complete aggregate JSON, shard JSON files, Task 11 source/plan manifest and native runtime/hash file. Artifact retention is time-limited by GitHub Actions: the source/plan and native artifacts were configured for 90 days, while shard and acceptance artifacts were configured for 365 days. These IDs and digests are the retrieval/integrity references; this committed archive is the durable index, not a claim that GitHub artifact retention is indefinite.

## 4. Scope and measurement interpretation

Each workflow accepted:

- 4 shards;
- 32 successive whole fit stories per shard per architecture;
- 128 story-runs per architecture across the four shards;
- 1,280 native events per architecture and 2,560 across HLA/HLB;
- zero evaluator labels, zero official test queries and zero generated-confirmatory labels.

**Important persistence nuance:** each shard creates its own persistent HLA learner and its own persistent HLB learner. Each learner processes 32 successive stories. Thus the evidence is four independent 32-story persistent sequences per architecture, not one uninterrupted 128-story trajectory on a single learner. Story-local weak supervision resets at story boundaries; model/native state and evidence stores persist within each shard.

Run #3 aggregate measurements:

| Metric | HLA | HLB |
|---|---:|---:|
| Events | 1,280 | 1,280 |
| Events per update-second | 106.3591 | 103.4522 |
| Mean update seconds/story | 0.09402 | 0.09666 |
| Mean checkpoint bytes | 902,970.99 | 909,333.99 |
| Maximum checkpoint bytes | 1,767,420 | 1,779,673 |
| Mean snapshot seconds | 0.03559 | 0.03797 |
| Mean restore seconds | 0.11967 | 0.12472 |

Maximum worker RSS was 90.0039 MiB and maximum Python allocation peak was 17.3955 MiB. Run #4 showed the same story/event counts, checkpoint maxima and memory peaks, with ordinary timing variation.

## 5. What this closes — and what it does not

**Closed:** bounded Task 11 persistent ingestion/resource qualification, including journal growth and per-story checkpoint recovery fingerprint equality under the tested four-shard design.

**Not closed:** answer prediction accuracy, antecedent/coreference accuracy, generalisation to raw bAbI text, a single 128-story uninterrupted learner sequence, or the full 120-unit campaign runtime guarantee. Task 11 official answer/support labels do not provide independent gold antecedent-edge annotations. Coreference edge precision/recall/F1 and entity-chain exact match remain NOT INDEPENDENTLY EVALUABLE without an independent gold annotation source.

This archive does not authorize learning-campaign execution. The separate prediction/evaluation, baseline, campaign protocol and preflight gates must pass first. Tasks 14 and 19 remain locked; Task 3/5 remain unchanged.
