# bAbI Expansion Source Freeze — Phase Q (A1/A2)

**Branch:** `research/babi-task-expansion-v1`  
**Scope:** v1.2.0 English `en-10k` source members for Tasks 11, 14 and 19.  
**Isolation:** the Task 3/5 freezer, pilot branch, source files, partitions, runner and campaign remain unchanged.

## A1 — external source identity and format audit

The Phase Q workflow obtains a fresh external copy of the six selected source members from the immutable Git commit:

`raviraju/NLP_QA_Project@0051751275841561267b1c6f5d9116b985521df1`

It also downloads the v1.2 release `README.txt` and `LICENSE.txt` from the same commit. Each source member is checked against its independently observed Git blob SHA-1 and byte length from the commit tree. The source audit records SHA-256 as the primary experiment integrity digest.

| Task | Split | Source member |
|---|---|---|
| 11 — Basic Coreference | train / test | `qa11_basic-coreference_train.txt`, `qa11_basic-coreference_test.txt` |
| 14 — Time Reasoning | train / test | `qa14_time-reasoning_train.txt`, `qa14_time-reasoning_test.txt` |
| 19 — Path Finding | train / test | `qa19_path-finding_train.txt`, `qa19_path-finding_test.txt` |

The parser validates UTF-8, numbered records, story reset at line 1, contiguous story-local IDs, exactly three tab-separated question fields, and each support ID against a prior statement line in the same story. Task 19 answers use compact, comma-separated cardinal-direction codes (`n`, `s`, `e`, `w`) and must be retained in order; Phase B adapters map these codes to the canonical north/south/east/west relation enum without changing their sequence. Malformed records and unresolved, forward or cross-story support witnesses fail closed.

**Archive limitation recorded explicitly:** Hugging Face exposes a v1.2 tarball LFS pointer with SHA-256 `0364ebde659f14d11bc21744516c5ec49d3d06cb692733f66680771244998898` and size 15,719,851 bytes, but the attempted current `resolve/main/data/tasks_1-20_v1-2.tar.gz` endpoint returned HTTP 404. Phase Q therefore does not claim to have downloaded or verified that archive object. It instead freezes the exact six selected member bytes from the commit-pinned external copy. This provides the required second copy of the experiment inputs while preserving the archive retrieval limitation in the generated audit report.

## A2 — reproducible immutable manifest

The workflow emits `source-audit.json` beside the six files, README and license. The manifest contains dataset version, language/configuration, provenance and license evidence, external source commit, per-member byte lengths, Git blob identity, SHA-256, story/question/statement counts, answer distributions, support counts and witness validation.

The v1.2 README documents `en-10k` as the 10,000-training-example configuration and the numbered-line/tab-separated format. It explains that story IDs reset to 1 and supporting-fact IDs refer to sentences within that story. There is no separately supplied official validation split for `en-10k`; validation must therefore be derived independently from each task's training stories using a frozen, deterministic whole-story split. Official test files remain quarantined from fit, adaptation, validation and candidate selection.

## Verified Phase Q result

**Phase Q selected-member freeze: PASS.** GitHub Actions run `45990456267` completed successfully on source-freeze commit `9274637fcc1c3116ab1c5d08e85b0497e95da960`. The repository-wide Python 3.10/3.12 test matrix also passed in run `45990456233`.

The uploaded artifact is `babi-expansion-phase-q-source-freeze` (artifact ID `15192429617`), 482,044 bytes, SHA-256 `8a7b8ec029448c81008d898e6fc0936baddd370bd470ed490b6a4b265ab4b4f2`. It contains six data members, README, license and `source-audit.json`; the artifact expires on 2027-02-25.

| Member | Bytes | SHA-256 | Stories | Statements | Questions |
|---|---:|---|---:|---:|---:|
| Task 11 train | 1,046,139 | `edfcd97fecd4a5045af25e1790cf1408856ae362c39521b1b69cd32b88ec0ced` | 2,000 | 20,000 | 10,000 |
| Task 11 test | 104,800 | `46f3290d0158ce1285a40cd2d793f5a65f86ae5000226e165cbc85a3dfeb2f6f` | 200 | 2,000 | 1,000 |
| Task 14 train | 1,506,583 | `c322e0814eef71f088af1aa1334e7ae4b1ee6ca18f2ee94c05e2189226964ed6` | 2,000 | 23,404 | 10,000 |
| Task 14 test | 151,420 | `e3f0b19858ffbec3ed1e49076cc4d1295a89ce146c50318b862f13f202b3caf2` | 200 | 2,352 | 1,000 |
| Task 19 train | 2,475,046 | `6cfdc6f448e3cf0e3d8a390fa3add461935b033f89ede32aeef30812401ec91e` | 10,000 | 50,000 | 10,000 |
| Task 19 test | 247,449 | `023e391f0d7f79c9e6ae1c46c093e2d0dbd50ab8fbd8965e037a75e3614c20e5` | 1,000 | 5,000 | 1,000 |

The six source members contain 30,000 training questions and 3,000 test questions. Every question in all six files carries exactly two official support references; all 66,000 references resolve to prior statement lines within the corresponding story. Task 11 and Task 14 each have six observed answer classes; Task 19 has 12 ordered two-direction answer classes. SHA-256 values above were recomputed from the downloaded artifact, not copied solely from the manifest.

## Acceptance and transition

Phase Q source-member acceptance requires:
1. All six selected members downloaded from the immutable external commit.
2. Every member matches its pinned Git blob identity and byte size.
3. Every member parses as UTF-8 numbered bAbI records and produces a SHA-256 digest.
4. All question support IDs resolve to prior statement lines in the same story.
5. Task 19 ordered-direction answer validation passes.
6. Offline audit tests pass and the generated report is uploaded.

The full v1.2 tarball itself is **not** claimed as acquired or verified. Phase Q therefore closes at selected-member source freeze, not archive-file freeze.

Passing Phase Q authorizes Phase B adapter development for HLA/HLB Tasks 11, 14 and 19. It does **not** authorize a learning campaign. Phase B must add independent task adapters, task-specific evidence/prediction/evaluation contracts, independently written task oracles, baselines and partition/leakage tests before a learning campaign is considered.

## Provenance references

- Dataset release: Facebook bAbI v1.2.0, English `en-10k`.
- External member copy: `raviraju/NLP_QA_Project` at commit `0051751275841561267b1c6f5d9116b985521df1`.
- License evidence: `tasks_1-20_v1-2/LICENSE.txt` in that commit, identifying Facebook, Inc. and CC BY 3.0 Unported.
- Format/release evidence: `tasks_1-20_v1-2/README.txt` in that commit.
- Dataset paper: Jason Weston et al., *Towards AI-Complete Question Answering: A Set of Prerequisite Toy Tasks*, [arXiv:1502.05698](https://arxiv.org/abs/1502.05698).
- Hugging Face v1.2 archive LFS pointer: SHA-256 `0364ebde659f14d11bc21744516c5ec49d3d06cb692733f66680771244998898`, size 15,719,851 bytes; its current resolve URL returned 404 and it is not represented as a downloaded artifact.
