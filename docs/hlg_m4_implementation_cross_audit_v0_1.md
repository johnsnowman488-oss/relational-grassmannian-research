# HLG-M4 implementation cross-audit: C0-C4, P0 and P6

**Version:** 0.1
**Audited repository ref:** `main` at `56fa16ffa1fd66730e351cccafea7ee899cc2bc0`
**M4 planning branch prior to this audit update:** `research/hlg-m4-preimplementation-ledger` at `c21c3700102122e93acaaaebf9fc30ec5979df6e`
**Policy:** `AGENTS.md` read in full; `DECISIONS.md`, M3 implementation/refinement protocols, M3 implementation results and M3/M4 exit records reviewed.
**Purpose:** Record source-level compatibility findings that refine M4 design. This is not a new M3 experiment, code validation campaign or M4 result.

## 1. Audit method and research-policy compliance

Read the actual implementations and associated tests:
- `src/rgm/leptograph/m3/controls.py`
- `src/rgm/leptograph/m3/integration.py`
- `src/rgm/leptograph/m3/integration_refinement.py`
- `src/rgm/leptograph/m3/context.py`
- `src/rgm/leptograph/m3/estimation.py`
- `src/rgm/leptograph/m3/activation.py`
- `src/rgm/leptograph/m3/revision.py`
- `src/rgm/leptograph/m3/revision_campaign.py`
- `src/rgm/memory/soe.py`
- `src/rgm/relations/{graph,schema,operations,temporal}.py`
- `src/rgm/leptograph/m1.py`
- `tests/test_leptograph_m3_implementation.py`, `tests/test_leptograph_m3_refinements.py`, `tests/test_relations.py`, `tests/test_leptograph_m1.py`.

No code changes were made: no defect was demonstrated in the accepted earlier M0-M3 scope. The changes in this audit are M4 contract refinements and explicit claim boundaries, consistent with `AGENTS.md`'s instructions to preserve accepted work, use existing components, and make the smallest effective correction.

## 2. C0-C4 implementation findings

### 2.1 Operational semantics

- **C0:** no persistent state and no task features.
- **C1:** one mode-state vector, additively updated; no SOE decay in this class.
- **C2:** one relation-state vector, additively updated.
- **C3:** separate mode and relation state arrays, independently updated. Both feed a common learned task readout after concatenation. This is not a cross-coupled state update.
- **C4:** one shared latent state, separate mode and relation readouts, and a common task readout. Each mode/relation update call decays and writes the same latent state, so update order matters.

The control class does not import or call `SOEMemory`. The current `run_integrated_refinement` function updates C3/C4 and reports their resources, but does not use their target predictions to form a controlled task-performance comparison. Existing tests exercise the common prequential API, but no matched held-out C0-C4 architecture ranking is established.

### 2.2 Shape-derived current resource audit

Configuration: mode dimension 2, relation dimension 2, state budget 64 scalars, target dimension 2, float64.

| Control | State scalars | State bytes | Parameter count | Parameter bytes | Total numeric bytes |
|---|---:|---:|---:|---:|---:|
| C0 | 0 | 0 | 0 | 0 | 0 |
| C1 | 64 | 512 | 128 | 1,024 | 1,536 |
| C2 | 64 | 512 | 128 | 1,024 | 1,536 |
| C3 | 64 (32+32) | 512 | 128 | 1,024 | 1,536 |
| C4 | 64 | 512 | 264 | 2,112 | 2,624 |

The code's common task readout is included in these current parameter counts. The historical M3 implementation campaign artifact predates this exact code snapshot; its recorded counts remain historical and must not be overwritten. Current unit tests explicitly assert the C4 264-parameter shape.

The M3 resource envelope caps state bytes, parameter count, update compute and query compute separately. All controls fitting the 512-byte state cap at this shape does not imply exact matching; C4 has more parameters and different update/query costs. A fresh resource-performance comparison is still required before any architecture-value claim.

### 2.3 Stability implications

C1-C3 apply additive updates without decay/projection in this class; repeated constant input yields linearly growing state. C4's shared latent state is contractive for bounded inputs at the default write rate, but its readout and task-readout matrices have no built-in norm bound. Therefore none is a complete adaptive-system stability result.

## 3. P0 composition primitives

The repository has three distinct composition constructs:
1. `RelationalGraph` / `RelationEvent`: event-level directed facts with timestamp, optional expiry, event ID and supersession.
2. `RelationSchema.compositions` / `compose_relations`: explicit ordered predicate-pair composition into a derived predicate/event, requiring connected endpoints and checking temporal validity.
3. `rgm.leptograph.m1.compose_routes`: dimension-checked matrix/operator composition across heterogeneous vector spaces.

The current relation event has bare string endpoints and no endpoint type registry, context, observation time or rich provenance. The binary `compose_relations` result does not preserve its source event IDs as a path witness. Existing tests cover its declared narrow contract. M1 tests cover operator-chain covariance, not semantic relational truth.

P0 must preserve these existing APIs and separately define a witness-bearing extensional path composition. Predicate-algebra associativity requires an explicit law for the predicate-composition table; it is not implied by associativity of ordinary relational joins. The current test fixture demonstrates one binary rule only.

## 4. P6 coupled-state compatibility

The actual adaptive state is better represented as:
\[
X_t=(m_t,z_t,c_t,\theta_t,e_t,d_t,k_t,r_t),
\]
where temporal SOE state, relation/operator state, context/routing state, estimator sufficient statistics, evidence/activation, detector, candidate lifecycle and resource constraints remain distinguishable.

The SOE primitive is standalone and not used inside the current M3 integrated-refinement harness. The actual harness is synchronous, prequential and step-ordered. It has context decisions, active/inactive source gates, residual detection and a candidate path with WAITING/TRAIN/VALIDATE/DONE phases. A separate CandidateLifecycle class has 32/32/64 fit/validation/post-promotion windows. CandidateRevision supports promotion/rejection but no general rollback-after-promotion operation. Do not infer arbitrary asynchronous, delay, rollback or reactivation stability from these runs.

M4 P6 should include the actual selected state transitions and treat unimplemented transitions as explicit future work. It must test full-system boundedness and protected relational knowledge integrity; the stability of SOE channels or C4's shared latent alone is insufficient.

## 5. Disposition

- Preserve M0-M3 source code and historical results.
- Use C0-C4 as existing reference controls, with corrected labels and explicit parameter/resource accounting.
- Use existing relation/event and M1 operator APIs as reference primitives, not as proof of witness-preserving semantic composition.
- Refine P6 state bookkeeping and mode assumptions to match actual state holders and transition code.
- Do not run an M3 replay or C0-C4 architecture campaign as part of this design audit.
- Run the normal PR unit-test matrix after the M4 documentation refinement. A pass establishes repository regression health only, not any of the scientific claims above.
