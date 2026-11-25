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

**P6 v3 finite-horizon acceptance: PASS** against the compiled persistent C++ runtime for both HLA and HLB.

The integrated `P6RuntimeCoupler` closes the loop:
- Both learned upper-level readouts are evaluated from the same pre-step SOE snapshot and injected with the frozen readout gain.
- The P6 accepted operator maps the controller state into a level-2 context/control feature using the frozen control gain.
- Native upper-level state summaries update the P6 controller on the next tick.
- Composite checkpoints include the native runtime, director/adapter state, all SOE banks, HLB canonical store where applicable, P6 state and memory, detector, activation state, candidate revision, and coupling configuration.
- Candidate promotion, P6 operator rollback, full native/Python/P6 rollback, and exact incumbent replay are tested as one coupled lifecycle.

**Preserved failed protocol lineage:**
- **P6 v1** (`HLG-H1-P6-ACTUAL-RUNTIME-v1`, seeds 950000–950019, full readout/control gains, unnormalized P6 memory aggregation) failed on the first accessed trajectory: the P6 state exceeded 25 at approximately tick 71. Diagnostic isolation showed the trained upper readouts drove native state growth; disabling readouts avoided the P6 overflow, while a 0.1 readout gain substantially reduced it.
- **P6 v2** (`HLG-H1-P6-ACTUAL-RUNTIME-v2`, seeds 951000–951019, readout/control gains 0.1) still exceeded the P6 envelope late in the 300-step run: norm 25.366 at tick 292. The raw SOE memory aggregation remained insufficiently normalized.
- Neither failed result was overwritten or counted as a pass. P6 v3 uses a new, disjoint seed set.

**P6 v3 frozen protocol and result:**
- Protocol: `HLG-H1-P6-ACTUAL-RUNTIME-v3`; seeds 952000–952019, 20 per architecture; 300 bounded-input stress steps per seed plus paired 20-step incumbent/candidate/replay continuations.
- P6 SOE memory aggregation multiplies each channel by its DC normalizer `1 - exp(-gamma)` before aggregation. Readout gain and P6 control gain remain 0.1. The state envelope remains 25; no threshold was relaxed.
- Compiled-runtime workflow: [45723190756](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45723190756), **PASS**.
- Evidence artifact: [P6 v3 JSON artifact 15073156994](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45723190756/artifacts/15073156994), ZIP SHA-256 `6b6708d438f2ba279b175b763f99ce2f304ff88c4222d8081cb48c482daf757c`.
- Pinned M4 commit: `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de`; compiled shared-library SHA-256 `38b278a93a5b3fa3b544f55d958a2f7a44bb6e1d39154e63072f5ed7be511e4b`.
- Both HLA and HLB: 7,200 native steps; max P6 state norm **15.7342**; P6 transition spectral radius **0.6663325**; exactly two CUSUM alarms per seed; 20/20 candidate promotions; 20/20 exact P6 operator rollbacks; 20/20 exact composite rollbacks; 20/20 exact incumbent replay fingerprints.
- Native state remained finite throughout. Its observed maximum level-state norm was **1,212.797**. The protocol did not assert a native-state norm bound, so this is a reported limitation, not a hidden pass criterion.
- HLA and HLB produced identical P6 results because their native hierarchy and controller dynamics are matched; the relation-store distinction does not alter this controller stability test.

**Claim boundary:** P6 v3 supports finite-horizon coupled execution and exact rollback for the declared M4 runtime, SOE normalization, readout/control gains, input bounds and 300-step horizon. It is not a global stability theorem, arbitrary-switching result, or guarantee for other kernels, dimensions, timesteps or gains.

### Current acceptance summary

- Runtime/checkpoint continuation: **PASS**.
- Independent partition freeze and integrity: **PASS**.
- Matched HLA/HLB validation + confirmatory campaign: **PASS**.
- Actual-runtime trusted rollback: **PASS**.
- HLA/HLB P6 v3 finite-horizon coupled stability and rollback: **PASS** within the declared protocol and claim boundary.

No architecture is selected as the overall winner. The native hierarchy's observed state norm is large despite remaining finite; no native-state boundedness claim is made. PR #48 remains draft/unmerged pending review of this evidence.


### Reproducibility rerun — smoke-only follow-up commit

After adding the real-runtime trusted-rollback assertions, the full repository test suite and native smoke were rerun, and the matched campaign workflow was rerun without changing campaign source, readout fitting, thresholds, partition manifest or seeds.

- Workflow: [45719954582](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45719954582), passed.
- Repository tests: 384 passed on Python 3.10 and 384 passed on Python 3.12.
- Validation raw JSON SHA-256: `2a61f8a2f83cc4188cfa7e137c8289f36487bff3c23bfb05a20638280d0ae37c` — byte-identical to the canonical validation JSON.
- Confirmatory raw JSON SHA-256: `8938a592aa1a6b9a7b0f89aeebfe351f72b93ce47ba6917db591dd9ca6d4cb9a` — byte-identical to the canonical confirmatory JSON.
- The ZIP artifact hashes differ because the ZIP containers were regenerated; the extracted JSON payloads are exactly identical. This is a deterministic reproducibility repeat of the same frozen seed sets, not a new independent confirmation sample.


## P6 coupled runtime stability — execution reconciliation (2026-11-25)

### Core P6 runtime campaign v3 — PASS, bounded claim only
- Protocol: `docs/experiments/HLG_H1_P6_ACTUAL_RUNTIME_v3.json`; SHA-256 `302c7976b9a5d9fffedfba8d55dae1f0f314a8163d4bacaac7ffa2243f9a9062` (protocol file hash before any later formatting changes).
- Workflow run: `45723023702`; artifact ID `15073565805`; artifact ZIP SHA-256 `5b757e58d789717b09262d50f3d1ef0dde8305220d3f8b929813e8f951c3bbab`.
- Native runtime: Aberconics commit `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de`; compiled shared-library SHA-256 `38b278a93a5b3fa3b544f55d958a2f7a44bb6e1d39154e63072f5ed7be511e4b`.
- P6 implementation source SHA-256 `84c8cd0767d8a025ff585e4e314cba0638f7803e89b5a558811b98909dd872ec`.
- Seeds 952000–952019, 20 per architecture, 300 operating steps per seed plus candidate/replay path; 7,200 native steps each for HLA and HLB.
- Both HLA and HLB: P6 maximum norm 15.734202 (<25); transition spectral radius 0.666332; exactly two CUSUM alarms per seed; 20/20 candidates promoted; 20/20 exact operator rollbacks; 20/20 exact composite rollbacks; 20/20 exact incumbent replay fingerprints; all native states finite.
- Mean independent validation improvement: 0.0756821. Maximum P6 control magnitude: 1.050905.
- Maximum native-level state norm observed: 1,212.7968. The v3 protocol only required native finiteness, not a native-state norm ceiling. This is an explicit open stability issue, not evidence of an acceptable native-state envelope.
- HLA and HLB campaign rows are identical because this P6 campaign did not inject relation records or exercise HLB's relational store; HLB store rollback was tested separately in the native smoke gate, not in this P6 campaign.

### Failed exploratory configurations and corrective finding
- Full-strength coupling failed the P6 norm envelope near step 72.
- Readout/control gains 0.1 without memory normalization delayed but did not remove the failure; P6 norm crossed 25 near step 293.
- Root cause: P6 SOE channels were averaged without compensating for their different DC gains. Added channelwise `(1-exp(-gamma))` normalization before aggregation, with a regression test. CI: 390 tests passed on Python 3.10 and 390 on Python 3.12.
- The normalized-memory v3 campaign is the first passing 20-seed compiled-runtime run; earlier v1/v2 attempts are exploratory failures and are not confirmatory evidence.

### Full P6 remains OPEN
The v3 result validates the core 2D P6 controller + native HLA/HLB feedback + detector + candidate promotion/rollback envelope. It does not yet validate the full M3/M4 adaptive state vector from the P6 v0.2 model. Remaining implementation gates:
1. Include `ContextBank` and `MultiSourceRidge` sufficient statistics in the same composite checkpoint/restore transaction as P6 and native hierarchy.
2. Drive and test relation evidence activation, dormancy, reactivation and recovery; ensure mode-specific state updates and dwell rules are explicit.
3. Exercise HLB relation-store mutation, protected relation retrieval/witness integrity, targeted revision, and rollback under the P6 campaign.
4. Include resource accounting/capacity state and test full-bank/capacity abstention without silent eviction.
5. Instrument per-level native state norms and perform a pre-registered feedback-gain/perturbation sweep. Freeze a defensible native operating envelope before any confirmatory stability claim.
6. Run the expanded matched HLA/HLB campaign with bounded disturbances, delayed/missing evidence, stationary negative controls, repeated outage/recovery and candidate rollback.

**Claim ceiling:** finite-horizon P6 controller-state boundedness and exact rollback for the v3 gains/runtime only. No global, arbitrary-switching, ISS, full-native-hierarchy boundedness, or full relational-integrity theorem is claimed.


### Campaign workflow trigger correction

Several additional H1 campaign invocations were triggered by an initially broad PR path filter while P6-only files were changing. They reused the same H1 campaign implementation, frozen configuration, and seed sets; they were not used for tuning and are not counted as independent confirmation. The canonical H1 result remains run 45719571254, with the deterministic reproducibility repeat 45719954582. The workflow trigger was narrowed and made one-shot to prevent further confirmatory-seed reuse.
