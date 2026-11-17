# HLG-M3 G2 implementation readiness — v0.1

**Status:** implementation audit; G2 has not started.  
**Canonical base at audit:** `e00ddca0df6f2de11d6113e994475ccce02842c1`.  
**G1:** accepted by workflow run [44111641084](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44111641084).  
**Frozen manifest SHA-256:** `8548f2a72de09a81f79a57a19b3cd8196dbeae185db9432619e6ac5cc2f49101`.

## 1. Why this audit exists

G1 proves that the deterministic BM-2 generator can materialise the frozen 40-world / 200-stream allocation and preserve the learner/evaluator boundary. It does not run an M3 learner or compute scientific endpoints.

The G2 workflow must not be created by relabelling the existing single-stream refinement probes. It must execute M3-A/B/C/D/E/I on the same frozen allocation, preserve the 32/32/64 candidate lifecycle, compare actual C0-C4 task performance under measured resources, and verify all package evidence against one implementation commit and manifest hash.

The readiness script is intentionally fail-closed. A green audit means the audit and tests ran; it does not mean G2 or M3 passed.

## 2. Implementation progress

This branch adds explicit source gates to `MultiSourceRidge.update` and `marginal_loss_contributions`. A caller can provide a zero placeholder for a missing vector while setting that source gate to zero. The source block then contributes no feature mass to the online sufficient statistics. A regression test verifies the absent block remains unchanged.

The implementation audit checks the frozen manifest identity, G1 allocation, masked update API, C0-C4 prediction capability, integrated resource accounting, candidate lifecycle contract and existence of a confirmatory campaign runner.

## 3. Current blockers

The repository state at the canonical base has these substantive gaps:

1. **No G2 confirmatory runner.** The current generator creates the 200 streams but explicitly does not execute scientific performance. The current refinement runner executes isolated deterministic probes, not six packages over the confirmatory allocation.
2. **C0-C4 are not task predictors.** `MemoryArchitecture` implements memory writes, reads and resource counters. It exposes no target-prediction or target-scoring interface. It therefore cannot produce held-out primary-composition loss as the required matched comparator. A memory-only resource snapshot is not a predictive comparison.
3. **No integrated candidate resource ledger.** Existing snapshots account for estimator sufficient statistics or a standalone C0-C4 control, not all persistent context, estimator, activation and revision state of the selected candidate.
4. **The 32/32/64 lifecycle is not implemented over confirmatory streams.** The existing candidate revision primitive can accept or reject a supplied matrix, but the campaign-level chronological fit, validation and untouched post-promotion windows, 24-observed-row minimum and insufficient-evidence accounting are absent.

The source-mask issue was addressed on this branch; it is no longer a blocker in the readiness audit.

## 4. Interpretation constraint

The generator describes each declared ordered composition as a sequence of context-conditioned primitive episodes; it explicitly says this is not an algebraic product of operators. G2 must report held-out ordered-sequence performance under that operational definition. It must not claim algebraic relation-composition generalisation.

## 5. G2 start condition

G2 remains untriggered until the blockers above are closed and the confirmatory runner can demonstrate, before viewing test outcomes:

- one immutable implementation commit and the exact G1 manifest bytes;
- 200/200 generated stream coverage, with fit/validation/test boundaries preserved;
- prediction-before-feedback and masked-source semantics;
- the six named package outputs and exact artifact/stream coverage;
- genuine C0-C4 task-prediction adapters, with no fabricated or padded resource counts;
- chronological 32-slot candidate fitting, 32-slot validation and 64-slot untouched post-promotion evaluation, including explicit insufficient-evidence states;
- integrated persistent-state, parameter, update and query accounting;
- a verifier that reports integrity, execution and scientific outcomes separately.

The frozen 5% effects, paired 95% world-clustered interval and 15/20 held-out-world consistency requirements are unchanged. No test-driven tuning or protocol relaxation is allowed.

**Decision at v0.1:** G1 accepted; G2 implementation incomplete; G2 not started; no M3 scientific result is claimed.
