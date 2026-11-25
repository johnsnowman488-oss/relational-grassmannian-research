# H1 implementation ledger — five hierarchical workstreams

**Status:** compiled C++ HLA/HLB smoke, checkpoint continuation and trusted rollback passed; independent partitions frozen; matched validation and confirmatory campaigns passed. Full HLA/HLB P6 coupled adaptive-stability acceptance remains open.
**Base:** `research/h0-shared-hierarchy-contract-soe-bridge`
**Branch:** `research/h1-hla-hlb-five-workstreams`
**H0 contract:** 0.1.0
**H1 schema:** 0.1.0

## Workstream 1 — HLA adapter

- Added a three-level HLA adapter over the shared H0 SOE bridge.
- Upper levels use separately fitted linear readouts (0→1 and 1→2), driven by the lower level's flattened pre-step SOE trace (not only the current event vector).
- Readout fitting accepts explicitly labelled calibration examples only.
- Abstract predictions have a distinct result type; exact witnesses are validated only against caller-supplied evidence.
- Missing/unfitted readouts do not fabricate an upper-level prediction.
- HLA has no relation-instance store; exact relational witnesses remain external evidence and are not inferred from readout outputs.

## Workstream 2 — HLB adapter

- Added one canonical relation-record map.
- Added level-scoped secondary indexes by subject and relation type; no per-level duplicate record copies.
- Enforces typed relation instances, immutable IDs, explicit capacity abstention and observation-cutoff retrieval.
- Composition delegates to the existing witness-preserving P0 composer; returned witnesses retain original instance IDs and entity sequence.

## Workstream 3 — persistent runtime integration

- Added ABI factories that build the H0 three-level chain spec and call an injected persistent-runtime factory once per adapter. The production Aberconics factory signature is compatible; the director owns and closes the persistent handle.
- Added a director that validates event and observation times and routes each global tick through exactly one adapter/bridge step.
- Late arrivals retain their original event time and are ingested at current observation time; historical native state is not rewritten.
- HLA rejects relation-store writes.
- Adapter snapshots now include all three Python SOE banks. Composite lifecycle snapshots also include the persistent native runtime checkpoint.

## Workstream 4 — common evaluation runner

- Added explicit fit/validation/confirmatory partition labels.
- The runner refuses to score the fit partition.
- Paired summaries require the same task ID, seed, partition, exact task fingerprint and task order.
- This is a harness primitive, not yet a frozen confirmatory campaign or evidence of HLA/HLB performance.

## Workstream 5 — composite lifecycle and rollback

- Added composite checkpoint fingerprinting over director/adapter/SOE/native state.
- Restore validates architecture, schema, readout dimensions/fingerprints, canonical store capacity/records and SOE configuration before activating state.
- Native restore relies on the M4 runtime's compute-then-commit restore contract.
- Promotion preserves the previous trusted checkpoint as the rollback point; rollback after promotion restores the previous trusted version rather than the candidate.

## Validation gates

- Unit tests added for readout fitting, HLA no-store boundary, HLB canonical indexing/capacity, witness preservation, director timing, composite rollback and paired evaluation.
- Dedicated H1 workflow [45712034356](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45712034356): focused H1/H0 tests and full repository suite passed on Python 3.10 and 3.12.
- Repository unit/invariant suite [45712033989](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45712033989): passed on Python 3.10 and 3.12.
- H0 contract/regression workflow [45712034002](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45712034002): passed on Python 3.10 and 3.12.
- G1–G5 development workflow [45712033907](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45712033907): passed on Python 3.10 and 3.12.
- Job 4 A/B integration workflow [45712033972](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45712033972): passed on Python 3.10 and 3.12.
- **Completed since the initial implementation review:** actual compiled C++ runtime integration, HLA/HLB checkpoint continuation, native trusted rollback, independent partition freeze, and matched validation/confirmatory campaigns. See the execution reconciliation below.
- **Still pending:** full HLA/HLB P6 estimator/detector/candidate lifecycle integration and finite-horizon coupled-stability acceptance against the compiled runtime.
- The evidence does not establish that HLA or HLB is universally superior.

## Important integration boundary

The director expects the persistent native runtime object already used by H0 and a runtime that exposes `step`, `get_state`, `checkpoint`, `restore` and `close`. This contract has now been exercised against the compiled Aberconics M4 shared library in the native smoke and matched campaign workflows; fake-runtime tests remain useful unit-level tests, not the acceptance evidence.


---

## Execution reconciliation — 2026-11-25

This section supersedes the earlier pending-status statements above where they conflict with the completed evidence below. The original implementation notes are retained for provenance.

### Gate 1 — compiled persistent C++ runtime and checkpoint continuation

- Native smoke workflow: [45719571218](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45719571218), passed against a freshly compiled Aberconics shared library.
- Follow-up native smoke with explicit trusted-version rollback: [45719954794](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45719954794), passed.
- Pinned Aberconics source commit: `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de`.
- Compiled Linux shared-library SHA-256: `38b278a93a5b3fa3b544f55d958a2f7a44bb6e1d39154e63072f5ed7be511e4b`.
- HLA and HLB each created one real native handle, executed two native steps, checkpointed after step 1, restored, and reproduced the same second-step feedback, native state, SOE banks and event tick.
- The follow-up also promoted a candidate snapshot, advanced one more step, and rolled back to the previously trusted one-step composite snapshot. Native step count, director tick and SOE banks were restored exactly. HLB's canonical relation store was restored with its one record intact.
- No fake runtime was used in either native smoke workflow.

### Gate 2 — independent partition freeze

Protocol: `HLG-H1-HIERARCHICAL-PARTITIONS-v1`.

- Train: 120 world seeds, 200000–200119.
- Validation: 60 world seeds, 400000–400059.
- Confirmatory: 120 world seeds, 900000–900119.
- Partition manifest SHA-256: `9e0610191ac3032cbfeb78b6c61511c2c358304f3d51c65a663692ddc5a1247a`.
- Frozen partition-config SHA-256 recorded by the campaign: `3f8b9a14eccfb8462a22c710d85bc63d6aafe93b5364309dcf29d7b7f13c2371`.
- Seed sets are disjoint from one another and from the earlier flat A/B confirmatory seed ranges. Each world seed generates both task modes; depth is determined by the frozen seed rule.
- The confirmatory partition was sealed in the manifest before execution. The campaign verified the config sidecar, seed-list hashes, manifest hash and prior-partition separation before running.

### Gate 3 — matched HLA/HLB validation and confirmatory campaigns

Canonical campaign workflow: [45719571254](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45719571254), passed. Validation ran before confirmatory execution; confirmatory ran only after validation succeeded.

Evidence artifacts:
- Validation: artifact `15072320022`, ZIP SHA-256 `0c8e8a5d5f6af8f0eb582f96d9fb57389dc93ec20ee6dd312612b9f9930960f3`.
- Confirmatory: artifact `15071477812`, ZIP SHA-256 `e6db0e3b76d4791e772d95fce6da668879d4283b4ac776ff769f57ec92e992b2`.

Both campaigns used the compiled native runtime pinned above and the same fitted readout fingerprints for HLA and HLB. Each task episode performed one native hierarchy step; task resets restored the baseline runtime checkpoint between episodes.

**Validation results:** 60 independent world seeds / 120 world instances, with 240 G1 rows, 960 G2 rows and 960 G3 rows.
**Confirmatory results:** 120 independent world seeds / 240 world instances, with 480 G1 rows, 1,920 G2 rows and 1,920 G3 rows.

- G1, both task modes and depths 2–4: HLA 100% correct; HLB 100% correct; zero invalid witnesses; zero future-sentinel leakage. Paired difference 0, world-clustered 95% bootstrap interval [0, 0].
- G2, outage without replay: HLA 0%; HLB 100%; HLB−HLA difference +1.0, interval [1.0, 1.0].
- G2, outage with replay: both 100%.
- G2, late target arrival before completion: both correctly wait/abstain (0% premature completion).
- G2, late target arrival after completion: both recover to 100%.
- G3, missing-edge, wrong-context and temporally invalid negatives: zero false selections and zero invalid witnesses.
- G3, multiple-witness positive control: both preserve exactly two witnesses; zero exact-witness failures.
- All 12 hard-integrity checks passed. Bootstrap comparisons use 10,000 resamples clustered by world seed.

**Interpretation:** the confirmatory evidence supports HLB's intended persistence advantage specifically during no-replay outages. HLA catches up when evidence is replayed. The architectures are equal on the tested composition, late-arrival and negative-control cases. This does not establish a universal HLB advantage, open-world topology discovery, out-of-vocabulary transfer, arbitrary-depth composition, or a Grassmannian advantage.

### Gate 4 — P6 coupled stability and rollback

**Closed subgate:** actual native + Python composite checkpoint, promotion and trusted rollback for both HLA and HLB passed in workflow 45719954794.

**Still open:** full P6 coupled adaptive-stability acceptance for the HLA/HLB hierarchy. The current H1 `CompositeLifecycle` coordinates snapshots, promotion and rollback, but the H1 branch does not yet integrate the full P6 estimator/detector/candidate-fit/independent-validation/adaptive-transition system or execute its finite-horizon coupled-stability campaign against HLA and HLB. The earlier 20-seed × 300-step P6 evidence belongs to the prior synchronous M4 prototype and must not be relabelled as HLA/HLB evidence.

Required next work:
1. Define and freeze the HLA/HLB P6 state vector and coupled transition, including all three SOE banks, readouts, HLB relation-store state, context/evidence, estimator statistics, detector, candidate and trusted-version state.
2. Integrate candidate fit, independent validation, promotion, dormancy/recovery and rollback as one atomic composite lifecycle.
3. Freeze bounded-input, switching, delayed/late-evidence and perturbation stress conditions with an explicit finite-run envelope before execution.
4. Run the matched P6 stress against the compiled native runtime; record coupled norms, transition/spectral diagnostics, detector decisions, promotion decisions, rollback exactness and recovery. Keep finite-horizon evidence distinct from a global stability theorem.

### Current acceptance summary

- Runtime/checkpoint continuation: **PASS**.
- Independent partition freeze and integrity: **PASS**.
- Matched HLA/HLB validation + confirmatory campaign: **PASS**.
- Actual-runtime trusted rollback: **PASS**.
- Full HLA/HLB P6 coupled adaptive-stability acceptance: **OPEN**.

No architecture is selected as the overall winner. PR #48 remains draft/unmerged pending review of this evidence and completion of the remaining P6 work.


### Reproducibility rerun — smoke-only follow-up commit

After adding the real-runtime trusted-rollback assertions, the full repository test suite and native smoke were rerun, and the matched campaign workflow was rerun without changing campaign source, readout fitting, thresholds, partition manifest or seeds.

- Workflow: [45719954582](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45719954582), passed.
- Repository tests: 384 passed on Python 3.10 and 384 passed on Python 3.12.
- Validation raw JSON SHA-256: `2a61f8a2f83cc4188cfa7e137c8289f36487bff3c23bfb05a20638280d0ae37c` — byte-identical to the canonical validation JSON.
- Confirmatory raw JSON SHA-256: `8938a592aa1a6b9a7b0f89aeebfe351f72b93ce47ba6917db591dd9ca6d4cb9a` — byte-identical to the canonical confirmatory JSON.
- The ZIP artifact hashes differ because the ZIP containers were regenerated; the extracted JSON payloads are exactly identical. This is a deterministic reproducibility repeat of the same frozen seed sets, not a new independent confirmation sample.
