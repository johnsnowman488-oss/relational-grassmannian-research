# bAbI Expansion Source Freeze — Phase Q (A1/A2)

**Branch:** `research/babi-task-expansion-v1`  
**Scope:** official v1.2.0 English `en-10k` source members for Tasks 11, 14 and 19.  
**Isolation:** the Task 3/5 freezer, pilot branch, source files, partitions, runner and campaign remain unchanged.

## A1 — source identity and format audit

The workflow downloads a fresh copy of `tasks_1-20_v1-2.tar.gz` from the content-addressed Hugging Face mirror and requires the exact Git-LFS SHA-256 and byte length recorded in the source pin. It extracts only these six regular-file members:

| Task | Split | Archive member |
|---|---|---|
| 11 — Basic Coreference | train / test | `qa11_basic-coreference_train.txt`, `qa11_basic-coreference_test.txt` |
| 14 — Time Reasoning | train / test | `qa14_time-reasoning_train.txt`, `qa14_time-reasoning_test.txt` |
| 19 — Path Finding | train / test | `qa19_path-finding_train.txt`, `qa19_path-finding_test.txt` |

The freezer verifies each member's exact byte length and Git blob SHA-1 against the independent, commit-pinned `raviraju/NLP_QA_Project` copy. It also records SHA-256, byte size, line counts, story counts, statement/question counts, answer distributions and supporting-fact distributions.

The parser validates UTF-8, numbered records, story reset at line 1, contiguous story-local line IDs, exactly three tab-separated question fields, and every support ID against a prior statement line in the same story. Task 19 answers must be ordered sequences of cardinal directions. A malformed record or unresolved/forward/cross-story support witness fails closed.

## A2 — reproducible immutable manifest

The workflow emits `source-audit.json` alongside the archive and six extracted members. The manifest contains the archive LFS object identity, source URL, dataset version, provenance caveat, license evidence, independent mirror commit, selected-member SHA-256 and size, task-specific format statistics, support-witness validation and the no-official-validation-split policy.

The `en-10k` release supplies training and test files, not a separately named official validation split. Validation must therefore be derived independently from each task's training file using deterministic whole-story partitioning. Official test files remain quarantined from fit, adaptation and validation.

## Acceptance and transition

Phase Q is complete only when the GitHub Actions job passes both the offline audit tests and the fresh external acquisition, all six extracted member bytes match the independent mirror, and the generated source manifest reports all acceptance flags true. The uploaded artifact is the branch's fresh source copy; it is not committed as raw dataset files.

Passing Phase Q authorizes Phase B adapter development for HLA/HLB Tasks 11, 14 and 19. It does **not** authorize a learning campaign. Phase B must add independent task adapters, evidence/prediction/evaluation contracts, task-specific oracles and baselines, and partition/leakage tests before any campaign is scheduled.

## Provenance references

- Dataset: `facebook/babi_qa`, v1.2.0, English `en-10k`; archive object pinned by SHA-256.
- Independent extracted-member mirror: `raviraju/NLP_QA_Project` at commit `0051751275841561267b1c6f5d9116b985521df1`.
- Dataset paper: Jason Weston et al., *Towards AI-Complete Question Answering: A Set of Prerequisite Toy Tasks*, [arXiv:1502.05698](https://arxiv.org/abs/1502.05698).
- License: CC BY 3.0 Unported, evidenced by the mirror's `tasks_1-20_v1-2/LICENSE.txt` and the Facebook bAbI dataset loader metadata.

The archive endpoint is a mirror, not a currently publisher-controlled download host. The source manifest preserves that distinction rather than representing the mirror as the original publisher.
