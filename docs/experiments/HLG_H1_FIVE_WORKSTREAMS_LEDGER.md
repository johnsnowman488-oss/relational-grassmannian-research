# H1 implementation ledger — five hierarchical workstreams

**Status:** H1 execution gates closed for the frozen scope: compiled C++ HLA/HLB smoke, checkpoint continuation and trusted rollback passed; independent partitions frozen; matched validation and confirmatory campaigns passed; full P6 v4 finite-horizon coupled adaptive-stability campaign and resource audit passed. Architecture-level evidence review completed; HLA and HLB retained as workload-conditional alternatives, with no universal winner selected.
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
- **Completed:** full P6 v4 estimator/context/activation/detector/dormancy/recovery/candidate lifecycle, HLB relation-store integrity, resource-envelope and finite-horizon stability acceptance against the compiled runtime. A global stability theorem and broader operating-envelope claims remain outside the evidence.
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

### Full P6 remained OPEN after v3; closed by v4 below
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


## Full P6 coupled adaptive stability — v4 execution (2026-11-26)

**Result: PASS — 37/37 frozen acceptance checks across HLA and HLB.** This closes the previously open full P6 execution gate for the declared runtime and bounded operating envelope.

- Protocol: `HLG-H1-P6-FULL-RUNTIME-v4`; protocol JSON SHA-256 `7c4c96e0ddef3a9e6cd1201783a190e30a44dfcb0cd0ded5e6d044f8a65bde8d`.
- Workflow: [45725650801](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45725650801), passed; artifact ID `15073354015`.
- Artifact ZIP SHA-256 `babbdedf20ce5874ca98d714d27ad49bb83cf06f6d8b8aee5fcfa1e1fc009991`; extracted result JSON SHA-256 `d0ab65bb06d202d63695ce0b026aa27ec2faaf589bdd9c3991253f96507123da`.
- P6 source SHA-256 `43f322461c94bae08e910d4013c3419fad69518731b10e84cf4f9d79a081bf2c`; pinned M4 commit `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de`; compiled shared-library SHA-256 `38b278a93a5b3fa3b544f55d958a2f7a44bb6e1d39154e63072f5ed7be511e4b`.
- Frozen seeds: 953000–953019 (20 per architecture); 300 coupled operating steps per seed, 100-step stationary negative control, candidate continuation and exact incumbent replay. Native execution: 9,200 steps per architecture, 18,400 total.
- Both HLA and HLB: maximum P6 state norm **19.6131** (<25); maximum native-level state norm **1,022.2545** (<1,500); transition spectral radius **0.6663325**; all native states finite; exactly two CUSUM alarms per seed; zero negative-control false alarms.
- Both architectures completed the `DETECT → DORMANT → RECOVERY → NORMAL` mode path on all 20 seeds. Context/estimator state updated; all four context slots were exercised; fifth-context capacity probes abstained without eviction on all 20 seeds. Lower and upper relations were active for 208–293 of 300 operating steps (mean 280).
- Candidate lifecycle: **20/20** independently validated promotions per architecture; **20/20** exact operator rollbacks; **20/20** exact composite checkpoint rollbacks; **20/20** exact incumbent replay fingerprints. Mean independent validation improvement **0.0774273** (minimum **0.0631968**).
- Resource envelope, using the frozen M3 numeric ledger plus P6 SOE memory accounting: maximum **854 bytes**, **26** trainable parameters, **1,272** update multiply-add upper bound, and **741** query multiply-add upper bound; all below the frozen caps.
- HLB-only relational integrity: the protected two-edge witness remained available; candidate-only relation insertion raised store count from 2 to 3; the next insertion returned `ABSTAIN_CAPACITY`; composite rollback removed the candidate-only record and restored exactly the two protected records on all 20 seeds.
- HLA and HLB P6/native trajectory metrics are identical in this campaign; HLB's additional result is the explicit relation-store capacity and witness-integrity coverage. No overall architecture winner is inferred.

**Claim boundary:** this is finite-horizon evidence for the specified HLA/HLB implementation, compiled M4 kernel, input distribution, timestep, coupling gains, context/store capacities and perturbation schedule. It is not a global stability theorem, an ISS theorem, an arbitrary-switching guarantee, or evidence for other kernels, gains, dimensions, or unbounded inputs. The resource figure is the protocol's declared numeric accounting scope (M3 integrated state plus P6 SOE arrays); it excludes Python object/container overhead and does not claim whole-process RAM.

### Follow-up audit

The v4 acceptance is complete. Closed by the separate P6 controller resource audit below.


### P6 controller resource-accounting audit — PASS

- Audit workflow: [45726337240](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45726337240), passed; artifact ID `15074058248`.
- Audit artifact ZIP SHA-256: `7a5f4d3a45845605dbc46c76dff19bd8c393ead953e8c8180f485109b9a7ae5f`; extracted JSON SHA-256: `2411ce7a4cdb06758fc8fafadfda1bbf97711422615ca8f241c33701df7e7fb7`.
- Explicitly added P6 state vector **16 bytes** and fixed transition matrix **32 bytes** to the campaign maximum M3-plus-SOE subtotal of **854 bytes**. Complete declared numeric P6+M3 state total: **902 bytes** for both HLA and HLB, below the 16,384-byte cap.
- The campaign subtotal already included **224 bytes** of P6 SOE arrays; these were not double-counted.
- Parameter count **26**, update upper bound **1,272**, and query upper bound **741** remain within their respective caps.
- All seven audit checks passed. Scope still excludes Python object/container overhead and native-runtime process memory; this is not a whole-process RAM measurement.


## H1 architecture-level evidence review — 2026-11-26

**Review:** `docs/experiments/HLG_H1_ARCHITECTURE_EVIDENCE_REVIEW_v1.md`  
**Commit introducing review:** `bfbea77739546038198cb1f889a78fe6dc38b318`

The P6 execution milestone is **CLOSED** for the frozen v4 implementation and operating envelope, with the separate resource-accounting audit complete. No further P6 execution is required to close H1.

### Evidence-based architecture disposition

- **HLA and HLB both pass** the shared compiled-runtime, checkpoint/continuation, matched task, and P6 finite-horizon execution gates.
- **HLB's supported differentiator:** 100% versus 0% in the frozen G2 no-replay outage condition. The result is explained by its canonical retained relation store; with evidence replay, both are 100%.
- **No other general advantage is established:** G1, late-arrival handling, G3 negatives and multiple-witness preservation match on the tested cases. P6/native numerical trajectories are identical.
- **HLB-specific integrity:** protected witness preservation, explicit capacity abstention, and removal of candidate-only records on rollback passed 20/20 P6 seeds.
- **HLA's role:** no-store reference architecture; exact claims remain grounded in caller-supplied evidence and the shared witness validator.
- **Decision:** keep both. HLB is the persistence-capable candidate; HLA is the no-store baseline. Primary architecture selection is deferred pending measured storage/latency/retention/outage trade-offs.

### Research-policy boundaries

- No universal HLB superiority, semantic intelligence, open-world discovery, arbitrary-depth composition, out-of-vocabulary transfer, or Grassmannian-specific advantage is claimed.
- P6 remains finite-horizon evidence only; no global stability, ISS, or arbitrary-switching theorem is claimed.
- The 902-byte audit is the declared numeric P6+M3 state scope. It excludes Python object/container overhead and native-runtime process memory, and does not measure HLB's complete relation-store footprint.
- Synthetic generated worlds and synthetic linear readout calibration do not establish real-world semantic generalization.
- Failed P6 v1/v2 attempts remain preserved; same-seed reruns remain reproducibility checks, not independent samples.

### Next phase

The next research phase is an architecture cost and workload-envelope comparison—not another broad P6 campaign. Freeze its protocol before execution. Measure HLA and HLB under matched store occupancy, record age/expiry, outage/replay, write rate, context fragmentation, branching, witness multiplicity, retrieval latency, checkpoint/restore cost, and component-separated memory accounting. Test readout generalization separately on noisy held-out relational tasks. Do not select a primary architecture until these workload-conditional trade-offs are measured.


## Hybrid state, prediction, learning, consolidation and evidence contract — 2026-11-26

**Design contract:** `docs/experiments/HLG_HYBRID_STATE_PREDICTION_LEARNING_CONSOLIDATION_EVIDENCE_CONTRACT_v0_1.md`  
**Contract ID:** `HLG-HYBRID-PLCE-v0.1`  
**Status:** proposed design contract; implementation and external-task validation are not yet claimed.  
**Commit:** `e15dd3fcf3def71b96eab097f262da5ee43b7ea4`

The contract formalises five previously discussed interfaces against the existing H0/H1 architecture:

1. **State and epistemic separation:** SOE temporal banks, native runtime state, observed evidence, derived evidence, predictions, learned parameters and runtime metadata are distinct state classes. The H0 row-major SOE embedding remains an encoding bridge; native evolution is not SOE evolution.
2. **Prediction:** explicit time-stamped, model-fingerprinted prediction objects at L0 grounding, L1 relational abstraction and L2 context/control. Forecasts are scored only against later eligible observations; current H1 upper readouts remain feature predictions, not semantic event predictors.
3. **Learning:** temporal, relational, abstraction and task errors remain attributable. SOE channels provide multiscale history features; they are not automatically eligibility traces. Any eligibility mechanism must define recurrence, decay, reset, normalisation and parameter attribution.
4. **Consolidation:** candidate → independent validation → atomic promotion or rejection; rollback restores model/runtime state but preserves observations received during candidate execution for reconciliation. Source evidence is append-only; revisions and derivations retain lineage.
5. **Evidence lifecycle:** L0 preserves exact event grounding and provenance; L1 preserves relation/role structure and exact composition witnesses; L2 may compress but retains scope, uncertainty, contradictions and resolvable evidence references. HLA remains no-store; HLB retains one canonical bounded relation store with level-scoped secondary indexes.

**Important implementation boundary:** this document is a normative design target. It does not claim that current H1 implements relational semantic prediction, temporal eligibility learning, n-ary event storage, or the complete evidence-safe consolidation lifecycle. Current H1 already supplies the SOE/native bridge, feature readouts, HLA/HLB distinction, HLB canonical binary relation store, composite snapshots and tested promotion/rollback primitives.

**Gate before external tasks:** implement and test state schemas/cycle ordering; prediction objects and leakage-safe evaluation; attributable learning signals and explicit temporal eligibility; candidate validation/promotion/evidence-safe rollback; and per-level evidence retrieval including n-ary role binding. Only then freeze and begin the planned bAbI Tasks 3/5 campaign (oracle structured events first, text parsing measured separately).

No H1 results or claims are upgraded by this design document. The P6 stability evidence remains limited to its frozen finite-horizon operating envelope; new learning rules require separate stability and task validation.

---

## Evidence lifecycle and external-task continuation — 2026-11-26

**Parent objective:** implement the proposed HLG-HYBRID-PLCE-v0.1 evidence lifecycle and then resume bAbI Tasks 3 and 5 without conflating structured reasoning with language parsing.

### Evidence lifecycle implementation

- Added `src/rgm/leptograph/m4/evidence.py` with immutable n-ary source events; same-event participant-role binding; source payload SHA-256 and provenance verification; append-only revision lineage; derived evidence with witness IDs; summaries with source digests; exact source-witness recovery; observation-cutoff enforcement; contradiction reporting; explicit capacity abstention; and independent journal serialization.
- Integrated separate bounded append-only source-event and source-relation journals into `HLBAdapter`. Both are intentionally outside candidate model rollback. HLB composite snapshots carry both evidence watermarks; restore verifies that checkpoint references still resolve and replays durable source relations into the canonical index. Candidate/transient relation insertions remain rollback-scoped. Both journals have explicit capacity abstention and monotonic storage-recovery merge.
- HLA remains the no-store reference: exact witness validation continues to require caller-supplied evidence. No HLA persistent event journal has been added.
- Added `tests/test_hlg_evidence_lifecycle.py` and `tests/test_hlg_integrated_contract_acceptance.py` for n-ary role integrity, late observations, contradictions, missing witnesses, provenance tampering, summary/derivation recovery, capacity exhaustion, failed validation, promotion and rollback while retaining intervening evidence.
- The source journal and canonical binary relation store remain separate: one preserves source event identity and n-ary roles; the other remains the existing bounded relation index/composition substrate.

### bAbI Tasks 3 and 5

- Added `scripts/freeze_babi_tasks.py` to acquire the official bAbI v1.2 `en-10k` archive from the historical S3 mirror, verify its exact 11,745,123-byte size and SHA-256, preserve official Task 3/5 train/test files, and derive a deterministic 10% validation partition from whole training stories. The script writes archive/file hashes, byte counts, line counts and story counts into the manifest. Acquisition is now being revalidated in CI.
- Added `src/rgm/experiments/babi_structured.py` with oracle structured-event reference solvers:
  - Task 3: temporal object-location reconstruction before a target movement event.
  - Task 5: role-conditioned retrieval from a single n-ary GIVE event, preventing cross-event role mixing.
- Added structured fixtures and tests in `tests/test_babi_structured.py`. These are adapter/solver tests, not official benchmark scores and not text parsing.
- Frozen protocol: `docs/experiments/HLG_BABI_TASKS_3_5_STRUCTURED_CAMPAIGN_v0_1.json`.
- Source identity: bAbI QA v1.2, English `en-10k`, Tasks 3 and 5. The exact S3 archive bytes observed in CI are pinned as SHA-256 `84f5296ab9a1ad0dc9464e08c491d65cd08830fca3acae9ab86f75e0fb81573c`, size 11,745,123 bytes. The Hugging Face staff-hosted LFS archive has digest `0364ebde659f14d11bc21744516c5ec49d3d06cb692733f66680771244998898`, size 15,719,851 bytes, but its CDN returned 403 during acquisition. The S3 archive contains the original `en-10k` train/test files, not the HF-generated `en-valid-10k` convenience layout. We therefore preserve official train/test bytes and derive validation from whole training stories using a frozen seed; we do not mislabel the derived validation split as upstream-official.
- Partition policy: preserve official story-level splits; train only on train, select on valid, access test only after configuration freeze. No story/question/support-index splitting.

### CI and claim boundary

- The preceding commit `b5b85585a80e88ed818317480a1c6af837acc400` passed H1 tests, repository regression, P6 controller tests and compiled native smoke on Python 3.10/3.12.
- Later commits integrated HLB's durable evidence journal, watermark validation, and bAbI structured-event adapters. They do **not** yet have a corresponding CI run. Do not transfer the earlier pass to these later commits.
- No official bAbI task result, HLA/HLB performance comparison, or natural-language parsing result is claimed.

### Next execution

1. Obtain the pinned bAbI archive and verify its local SHA-256/size; extract and hash the six selected files; update the manifest.
2. Run focused and full CI on the current H1 head, fixing only demonstrated failures.
3. Extend the structured adapter from fixture-level inputs to source-indexed official task records without parsing sentence text; validate source-line/support-index lineage.
4. Run deterministic oracle/reference checks on train/validation/test separately.
5. Run matched HLA/HLB structured-input campaigns; retain test as confirmatory.
6. Only after the structured-event stage is stable, add text-to-event parsing and report parser errors separately from reasoning errors.

### Follow-up hardening — 2026-11-26

- HLB now distinguishes transient/candidate relation insertion (`observe`) from observed source relation ingestion (`observe_source`). The latter is held in a separate bounded append-only journal, carries its own watermark in composite snapshots, and is reindexed after rollback. If the canonical index is temporarily full, the source relation remains recoverable by ID and is reindexed when rollback frees capacity; if the source journal itself is full, ingestion explicitly abstains.
- Added monotonic source-relation journal recovery and exact lookup for records that are not currently indexed. Journal recovery is atomic and does not delete newer records.
- Added `EvidenceStore.recover_chain` / `HLBAdapter.recover_evidence_chain` to recover the summary, derivation, witness IDs and exact source-event chain, preserving witness traversal order.
- Promotion now requires an explicit independent validation receipt with passed status, validation partition, SHA-256 protocol/criteria/data-manifest fingerprints, measured metrics and the exact active candidate fingerprint. Failed, incomplete or stale receipts are rejected. Validation receipts are stored with promoted trusted checkpoints. The initial trusted checkpoint cannot be reset to bypass validation.
- Added tests for failed promotion, stale receipt rejection, source relation retention through rollback, source journal capacity abstention, and monotonic relation journal recovery.
- Repository CI now includes `workflow_dispatch` and the H1 branch in its push filter. A run observed during execution (`45827809639`) remained queued at earlier head `97b6a569...`; no completed CI result exists for the latest head `72b1037ebefb3bde91782e3b2f9921a87624fd15`. Do not treat the earlier successful run as validation of these later changes.

### CI reconciliation — 2026-11-26

- Repository CI run [45827809639](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45827809639) executed against earlier head `97b6a56918df91e59956da1244c58d46e1f312f0` and failed on one new Task 3 fixture assertion; **414 tests passed, one failed** on both Python 3.10 and 3.12.
- Failure diagnosis: the late-arrival fixture asked for an object's location after two MOVE events but omitted the PICK_UP event that makes the object follow the actor. The solver correctly returned unknown. The fixture now includes PICK_UP before movement (commit `ed628152596b9e9995941c333dfe6cade93d4f81`).
- This was a fixture defect, not a solver failure. The later promotion-receipt and evidence-watermark hardening was added after the failing run.
- **Current status:** latest changes have not yet been exercised by a completed CI run. The failed run must not be treated as acceptance of the latest head. Repository CI has a manual `workflow_dispatch` entry and includes the H1 branch in its push filter.

### Latest CI reconciliation — 2026-11-26

- On head `62bab60d3e44542fff97c5573e2f2d1d08b1d8cf`, repository unit/invariant CI passed on Python 3.10 and 3.12: [45828409811](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45828409811) (PR) and [45828397709](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45828397709) (push).
- H1 hierarchical adapter/lifecycle tests passed on Python 3.10 and 3.12: [45828409791](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45828409791).
- P6 controller tests passed: [45828410688](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45828410688).
- The compiled native library built successfully and matched the pinned SHA-256, but the native smoke job then failed because its legacy test harness still called `lifecycle.promote()` without the newly required validation receipt. This was a harness/API migration failure; the native runtime smoke assertions were not reached.
- Updated `scripts/h1_native_runtime_smoke.py` to provide an explicit, fingerprinted software-integration validation receipt for the smoke-only promotion/rollback exercise (commit `3a479aed04bd17eaf49d0b92f359858883091cae`). This is not a model-performance validation claim.
- The corrected native smoke script has not yet been rerun. The native smoke workflow already supports manual dispatch. Do not mark compiled-runtime evidence-lifecycle acceptance complete until that rerun passes.

### Corrected full acceptance cycle — 2026-11-26

The corrected native smoke harness and current repository state were exercised on head `fc2acbc8c3e4e323d5d5c2efb3be1c64561ec29a`:

- Repository unit/invariant suite passed on Python 3.10 and 3.12: [45828807472](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45828807472). The push-triggered duplicate run [45828796751](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45828796751) also passed both versions.
- H1 hierarchical adapters/lifecycle suite passed on Python 3.10 and 3.12: [45828807247](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45828807247).
- P6 adaptive state/checkpoint/rollback tests passed: [45828807281](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45828807281).
- Compiled C++ native runtime smoke passed: [45828807523](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45828807523). The native library was built from pinned Aberconics commit `2539df6bda7ef3c9dd7c707abe26eff8bdbb59de`, SHA-256 `38b278a93a5b3fa3b544f55d958a2f7a44bb6e1d39154e63072f5ed7be511e4b`.
- Native smoke results: HLA and HLB each completed two native steps; checkpoint restore and P6 trusted rollback passed for both; HLB restored its one relation record. Artifact `h1-native-runtime-smoke`, ID `15122020830`, preserves the compiled shared library.
- The prior native smoke failure was resolved by updating the smoke harness to supply the explicit integration validation receipt required by the hardened promotion API.

**Acceptance conclusion:** repository tests, H1 adapter/lifecycle tests, P6 tests, and compiled-native HLA/HLB smoke all pass on the recorded head. This closes the integrated software-contract acceptance for the implemented scope; it does not establish bAbI performance or natural-language parsing capability. Official bAbI data acquisition and the structured-event campaign remain the next external-task gates.

### bAbI acquisition automation — 2026-11-26

- Added `.github/workflows/h1-babi-structured-freeze.yml` for manual acquisition and structured smoke.
- Added a branch-scoped `babi-source-freeze` job to the existing repository CI workflow. It downloads the pinned v1.2 archive, verifies its SHA-256 and size, extracts official Task 3/5 en-10k train/test files, creates deterministic whole-story fit/validation partitions, records hashes and row/story counts in the manifest, runs the structured-event/evidence tests, and uploads the frozen data plus updated manifest as an artifact.
- The archive itself has not yet been acquired in a completed workflow run. The workflow must pass before the six file-level hashes can be treated as frozen. No official bAbI benchmark score is claimed.


### CI diagnosis and source-freeze correction — 2026-11-26

- Inspected the latest failed GitHub Actions runs and their job logs. H1 hierarchical adapters/lifecycle, P6 controller/checkpoint tests, compiled native runtime smoke, and Python 3.10/3.12 unit tests passed on the latest previously completed head. The aggregate repository workflow was red because its bAbI acquisition sub-job failed; it was not a separate HLA/HLB regression.
- The initial source-freeze attempt pinned the Hugging Face staff-hosted LFS object. GitHub Actions received HTTP 403 from the LFS CDN despite the object pointer being publicly visible. The S3 archive is a different archive layout and does not contain the HF-generated validation directory.
- The S3 archive is the v1.2 archive referenced by the official Hugging Face dataset builder, and its exact bytes were observed in CI: 11,745,123 bytes, SHA-256 `84f5296ab9a1ad0dc9464e08c491d65cd08830fca3acae9ab86f75e0fb81573c`. It contains the official English `en-10k` Task 3/5 train and test files.
- Revised the freeze protocol to pin that archive identity, preserve the official test split, and derive a deterministic 10% validation split by complete story blocks from the official training data. The derived split is explicitly labelled as derived, not an upstream official split. This avoids question-level/story-level leakage and keeps the confirmatory test bytes untouched.
- Added deterministic split tests and wired them into the source-freeze workflow. Latest source-freeze run is pending; no claim of successful acquisition or frozen per-file hashes until that run completes.
