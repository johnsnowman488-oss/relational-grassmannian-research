# HLG-M3 G2 implementation readiness — v0.2

**Status:** implementation audit v0.3; G2 has not started. The implementation work is actively closing the original blockers.  
**Canonical base at audit:** `e00ddca0df6f2de11d6113e994475ccce02842c1`.  
**G1:** accepted by workflow run [44111641084](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44111641084).  
**Frozen manifest SHA-256:** `8548f2a72de09a81f79a57a19b3cd8196dbeae185db9432619e6ac5cc2f49101`.

## 1. Why this audit exists

G1 proves that the deterministic BM-2 generator can materialise the frozen 40-world / 200-stream allocation and preserve the learner/evaluator boundary. It does not run an M3 learner or compute scientific endpoints.

The G2 workflow must not be created by relabelling the existing single-stream refinement probes. It must execute M3-A/B/C/D/E/I on the same frozen allocation, preserve the 32/32/64 candidate lifecycle, compare actual C0-C4 task performance under measured resources, and verify all package evidence against one implementation commit and manifest hash.

The readiness script is intentionally fail-closed. A green audit means the audit and tests ran; it does not mean G2 or M3 passed.

## 2. Implementation progress

This branch adds explicit source gates to `MultiSourceRidge.update` and `marginal_loss_contributions`, a packed symmetric Gram representation that preserves the full sufficient statistics with lower persistent storage, and a common prequential target-prediction/update/scoring interface for C0-C4. The controls now expose actual prediction APIs; C0 remains the zero-persistent-memory reference, while C1-C4 learn task readouts from their retained state. Regression tests cover masked source updates, exact packed-statistic equivalence, predictor chronology and resource accounting.

The implementation audit checks the frozen manifest identity, G1 allocation, masked update API, C0-C4 prediction capability, integrated resource accounting, candidate lifecycle contract and existence of a confirmatory campaign runner.

## 3. Current blockers

The repository state at the canonical base has these substantive gaps:

2. **No G2 confirmatory runner.** The current generator creates the 200 streams but explicitly does not execute scientific performance. The current refinement runner executes isolated deterministic probes, not six packages over the confirmatory allocation.
1. **The learner has no context-conditioned relation store.** The new REL-A..REL-D episodes use distinct latent operators selected by evaluator-owned context identity. `ContextBank` stores context prototypes only; `MultiSourceRidge` exposes one shared source operator per source block. There is no accepted-context-to-operator lookup or context-conditioned prediction interface. The current learner therefore does not implement the generated relation task.
3. **C0-C4 campaign integration remains open.** A common target prediction/update/scoring API now exists, but the confirmatory runner must feed identical eligible task inputs to all five controls, enforce prediction-before-feedback, and record their held-out losses and measured resources under the same stream schedule.
3. **No integrated candidate resource ledger.** Existing snapshots account for estimator sufficient statistics or a standalone C0-C4 control, not all persistent context, estimator, activation and revision state of the selected candidate.
4. **The candidate lifecycle core now exists, but campaign integration is absent.** This branch adds a streaming `CandidateLifecycle` component with exact 32-slot fit, 32-slot validation and 64-slot untouched post-promotion windows; it accumulates sufficient statistics rather than retaining raw window rows, requires at least 24 observed rows in each decision window, rejects rank-deficient fits, and records secondary alarms without opening overlapping lifecycles. Dedicated tests cover window boundaries, missing evidence, chronology, promotion and resource-buffer accounting. The confirmatory runner still does not wire detector alarms, learner residuals, conditional identifiability and evaluator scoring into this lifecycle over the 200 frozen streams.

The source-mask issue, packed sufficient-statistic representation, common C0-C4 prediction interface, context-conditioned operator store and label-blind nearest-slot reuse policy are now implemented with focused tests. Their integration into full confirmatory stream execution remains open.


## 3A. Structural feasibility findings and compact-state implementation

A new machine-readable preflight now measures the current implementation's minimum numeric-buffer footprint using the declared 2-D primary and secondary sources, 2-D context and 2-D target:

| Component | Numeric bytes |
|---|---:|
| Packed symmetric MultiSourceRidge Gram and cross sufficient statistics | 336 |
| 2-D context metric | 32 |
| One ContextSlot mean and scatter | 48 |
| **Numeric-buffer subtotal** | **416** |
| Frozen persistent-state ceiling | **512** |
| **Remaining headroom before other candidate state** | **96** |

The estimator now stores only the upper triangle of its symmetric Gram matrix and reconstructs the dense matrix transiently for solves and identifiability calculations. This preserves the mathematical sufficient statistics while reducing their persistent numeric storage from 504 to 336 bytes for the declared dimensions. The 416-byte subtotal is not a complete candidate ledger: it excludes additional context slots and novelty buffers, activation/evidence, detector state, candidate lifecycle/revision state and ordinary metadata. The compact estimator therefore removes the previous immediate 72-byte overrun, but integrated resource accounting remains required. The frozen 512-byte ceiling is unchanged.

The generator emits six distinct context prototypes: F6-CONTEXT-A/B and REL-A/B/C/D. The declared context-capacity sweep is K=2, 4, 8. The current ContextBank supports an explicit label-blind `nearest_reuse` policy when full, while retaining abstention as the default. This lets K=2 and K=4 continue operating without evaluator labels or hidden identity-based eviction. The confirmatory runner must select the declared policy before outcomes and report reuse/abstention behaviour.

The diagnostic is exposed as `src/rgm/experiments/hlg_m3_g2_structural_preflight.py` and is included in the readiness artifact. Its tests assert the 416-byte compact numeric-buffer subtotal and report the capacity issue without assuming that all six context slots are mandatory at once.

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

**Decision at v0.4:** G1 accepted; packed symmetric sufficient statistics reduce the measured estimator-plus-minimum-context numeric subtotal to 416 bytes, leaving 96 bytes before omitted candidate state. Context-conditioned operator storage and C0-C4 task prediction interfaces now exist, but integrated resource accounting, lifecycle/stream integration, full runner and campaign execution remain outstanding. G2 is not started. No M3 scientific result is claimed.
