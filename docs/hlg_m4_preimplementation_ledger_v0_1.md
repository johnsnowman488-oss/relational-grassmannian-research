# HLG-M4 pre-implementation research ledger

**Ledger:** HLG-M4-PREIMPLEMENTATION-LEDGER-v0.1  
**Date opened:** 2026-11-18  
**Status:** Planning record; discussion adopted as the starting basis for M4 pre-implementation work. This is not the M4 implementation protocol, a result report, or authorisation to begin the M4 confirmatory campaign.  
**Parent:** HLG-M0 through HLG-M3; M4 is the coupled adaptive-system stability investigation.  
**Programme relationship:** M-series branched from E03. The intended formal reintegration point after M4 is E09.

## 1. Why this ledger exists

The M-series began as a deeper investigation of the adaptive relational mechanisms opened by E03. It has since covered substantial parts of the capability questions originally distributed across E03-E08 and has already begun the architecture comparisons intended for E09.

The M4 planning process must therefore not treat E03-E08 as untouched work, nor create new experiments merely to reproduce questions already investigated within M3's declared scope.

At the same time, the M-series evidence must not be overstated. The pre-implementation phase should identify the remaining gaps that materially affect the M4 coupled-system question and the later E09 synthesis, resolve their definitions and controls, and then freeze a bounded M4 implementation protocol and actual M4 entry gate.

This ledger records the programme-level discussion and the evidence lineage that the M4 plan must preserve.

## 2. Original research motivation: the Aberconics D2C relational-composition crisis

The wider motivation is the gap observed in the HierAberConic-D2C experiments: retaining historical information, retrieving a stored association, selecting a relevant relation, and correctly composing several relations are distinct capabilities. Success at one layer does not establish the next.

The D2C experiments exposed several versions of this gap:

1. **Decoder leakage in the initial D1 result.** An apparent 100% single-pair retrieval result was not a valid demonstration of query-conditioned relational binding. When the task was changed to multi-pair query-conditioned retrieval, performance fell to 18/64 (28.1%), exposing the missing binding mechanism.
2. **Supplied binding versus learned relational reasoning.** A deterministic, hand-designed outer-product binding mechanism recovered 64/64 retrieval at gap 32 (and 64/64 for full/collapsed at gap 64, against 0/64 for no-slow). This demonstrated retention and retrieval when binding was supplied; it did not establish that the system learned the binding or performed general relational composition.
3. **Free evolution.** D2 free evolution encoded elapsed time (duration discrimination 1.000 versus 0.500 for frozen), but did not improve passive retrieval. This was temporal encoding, not evidence of additional reasoning during silence.
4. **Distractors and credit assignment.** D3 distractor tests weakened or removed the clean full-versus-no-slow separation. Forced eligibility controls were upper bounds; REINFORCE was sparse/seed-sensitive; soft eligibility or attention-like selection was not equivalent to causal credit assignment.
5. **Substrate and hierarchy qualification.** D4 work distinguished the Python vector-χ contract from the C++ ABI scalar-χ implementation, with approximately 9% episode-level divergence at task scale. Later hierarchy findings also separated static weighting effects from genuine context-adaptive modulation.

The E01 investigations then isolated additional temporal-memory and path-composition failure modes:
- repeated-event accumulation distorted support and repeat suppression improved stressed results by 29.79 percentage points;
- noisy supports amplified false paths (with 16 entities, only 15.14% of true paths ranked at the top, and three-hop performance around 1%);
- slow decay could lose persistent facts over long gaps;
- an exact-fact oracle reached 100%, separating memory/scoring limitations from path-enumeration limitations.

These findings motivate a layered investigation rather than one undifferentiated “composition” metric. The research must distinguish:
- retention of individual facts or relation instances;
- query-conditioned retrieval;
- binding of entities, roles, contexts and relation identities;
- selection and ordering of relevant paths;
- application of a relation/operator to its arguments;
- composition across multiple relations;
- final readout and answer construction.

A failure at a later layer must not be attributed to memory alone, and a success at an earlier layer must not be described as compositional reasoning.

**Source lineage:** Aberconics framework [Context.md](https://github.com/johnsnowman488-oss/aberconics-framework/blob/main/Context.md), [D2C technical reference](https://github.com/johnsnowman488-oss/aberconics-framework/blob/main/D2C.md), and the D2C experiment implementations, including [learned binding](https://github.com/johnsnowman488-oss/aberconics-framework/blob/main/code/python/d2c/experiments/d3_learned_binding.py) and [D4A probe](https://github.com/johnsnowman488-oss/aberconics-framework/blob/main/code/python/d2c/experiments/d4a_probe.py). Historical results are context for this research programme, not evidence that M3 or M4 has already solved the D2C task.

## 3. E-series / M-series coverage crosswalk

The following is the current programme interpretation. “Substantially investigated” means meaningful implementation and/or controlled evidence exists within the stated scope; it does not mean the full original E-stage ambition is closed.

| Original objective | M-series contribution | Current assessment and remaining boundary |
|---|---|---|
| **E03 — Representation-neutral relational task diversity** | M3 F6-derived sequential benchmark, BM-0/BM-1 design and BM-2 generator: contexts, heterogeneous sources, correlation, missingness, drift, held-out compositions and world-level splits. | Benchmark infrastructure substantially developed. Still narrower than the original representation-neutral suite spanning explicit, higher-order and continuous domains. |
| **E04 — Relational structure discovery** | Context recognition, novelty handling, bounded context banks, abstention, context-conditioned operator estimation and evidence-based activation. | Context-conditioned acquisition investigated. M3 uses fixed candidate topology; open-ended topology discovery remains unestablished. |
| **E05 — Composition and generalisation** | Ordered primitive sequences, fit/validation/test separation, held-out pairs and triples, multi-world testing. | Strong constrained sequential-composition evidence. G2 achieved 54.49% relative reduction in held-out primary-composition loss (95% world-clustered CI 49.34%-59.73%; positive in 20/20 held-out worlds). However, M3 benchmark composition means ordered context-conditioned primitive episodes, not algebraic multiplication/composition of relational operators. |
| **E06 — Revision and adaptation** | Evidence-based activation/dormancy, drift detection, candidate fitting, independent validation, promotion/rejection, resource accounting; G2 and G3 campaigns. | Substantially investigated. Original G2 adaptation endpoint failed (-0.28004755%; CI -0.8008573% to 0%; 0/20 positive worlds); telemetry revealed detector problems. G3-v0.3 then showed 49.07% gradual and 78.63% abrupt improvement, 20/20 positive worlds in each, with stable negative control at zero alarms/promotions. The user-authorised 2% G3-defined gate revision is outcome-informed and does not retroactively pass the original G2 gate. Claims remain within the tested synthetic regimes and fixed topology. |
| **E07 — Partial observation, gaps and recovery** | Independent missingness, target gaps, extended all-observation outages, dormancy/reactivation, and safeguards against treating missing data as negative evidence. | Substantially represented and tested within the M3 synthetic envelope. General recovery under arbitrary interruptions, identity changes and long-term interference remains open. |
| **E08 — Cross-domain transfer** | Held-out worlds, factor profiles, contexts, source correlations, drift/noise conditions and unseen ordered compositions. | Within-family configuration/composition generalisation investigated. Broad transfer to a genuinely different task/domain with different semantics and observation structure remains unestablished. |
| **E09 — Temporal memory and relational organisation cooperation** | M3 C0-C4 architecture controls and predictive/resource comparisons; M4 will study coupled-system stability. | Significant foundation already exists. Full architecture-level synthesis remains a post-M4 E09 responsibility; no universal architecture winner is presumed. |

The crosswalk is intended to prevent both under-crediting completed research and over-claiming beyond the evidence.

## 4. M3 evidence that must be carried into M4

M4 planning must preserve the following facts and boundaries:

- M3's capability result passed its original frozen gate: 54.49% relative reduction in held-out primary-composition loss, paired 95% world-clustered CI 49.34%-59.73%, positive effects in 20/20 held-out worlds.
- M3's original G2 adaptation result failed its original frozen 5% untouched post-promotion-loss gate. Preserve the result as a failure under that endpoint.
- G2 detector telemetry exposed 765 alarms in stationary test streams and only two promoted/evaluated candidates across 100 test streams.
- G3-v0.3 supplied a calibrated follow-on adaptation result in gradual and abrupt synthetic environments and preserved a stable negative control.
- The authorised 2% G3-defined adaptation criterion is outcome-informed, explicitly scoped to G3's post-change-loss endpoint, and must not be described as prospective pre-registration or as a pass of the original G2 criterion.
- The resource ceilings, common comparator rules, world-clustered uncertainty and benchmark integrity contract remain part of the evidence.
- C0-C4 are architectural controls, not proof that separate temporal/relational memory or a unified state is universally superior.
- M3 fixed candidate topology and its composition benchmark's episode-sequence semantics remain explicit limitations.

Relevant records:
- [M3 benchmark protocol](hybrid_leptograph_m3_benchmark_protocol_bm0_bm1_v0_1.md)
- [M3 exit criteria and M4 entry gate](hlg_m3_exit_criteria_m4_entry_gate_v0_1.md)
- [G3 adaptation results](hybrid_leptograph_m3_g3_adaptation_results_v0_3.md)
- [G2 detector telemetry results](hlg_m3_g2_detector_telemetry_results_v0_1.md)
- [M3 adaptation gate revision](hlg_m3_adaptation_gate_revision_v0_1.md)
- [Relational adaptation ledger](relational_adaptation_ledger.md)

## 5. M4 pre-implementation phase: purpose

The pre-implementation phase should close most of the design and evidence gaps that would otherwise contaminate M4 or force avoidable redesign after its gate.

It is not an invitation to expand M4 into a new omnibus E03-E08 campaign. The work should be limited to:
1. resolving the meaning of composition that M4 is intended to stabilise and that E09 must eventually evaluate;
2. making the remaining E03-E08 limitations explicit and addressing only those that materially affect the M4 model, its operating envelope or the D2C research question;
3. defining the coupled adaptive system, its switching/update semantics and its stability claims;
4. ensuring the M3 architecture and benchmark controls can be carried forward fairly;
5. producing one integrated, versioned M4 implementation protocol and actual M4 gate proposal for review.

Pre-implementation completion does not itself authorise the M4 implementation campaign. The actual M4 gate remains a distinct decision after the protocol and evidence contracts have been reviewed and frozen.

## 6. Proposed pre-implementation work packages

These are design/refinement work packages, not yet frozen experiments. They should be refined into independent jobs only after their interfaces, common definitions and evidence dependencies are agreed.

### P0 — D2C composition target and evidence lineage

Define the specific D2C-inspired composition capability that the M4/E09 line should ultimately support. Distinguish:
- relation-instance retention;
- query/role binding;
- ordered path selection;
- primitive operator application;
- multi-relation composition;
- answer/readout.

Specify a ground-truth relational witness and a task-level composition definition that does not leak evaluator structure to the learner. Preserve a distinction between the existing M3 sequential-episode composition metric and true operator/path composition.

**Deliverable:** composition semantics and a claim ladder mapping each layer to observable evidence.

### P1 — Failure attribution and diagnostic controls

Define how a future composition task can tell whether failure originates in memory, retrieval, binding, path selection, operator application, composition or readout.

Consider exact-fact and exact-relation oracles as diagnostic upper bounds, alongside no-memory, no-binding, no-context, no-composition and shuffled/order-destroyed controls where each is scientifically appropriate. Oracles must diagnose a layer, not satisfy the learner's acceptance gate.

**Deliverable:** failure-attribution matrix, matched controls and non-leakage contract.

### P2 — Bounded relational acquisition beyond the current fixed candidate set

Specify a bounded, measurable test of whether the system can acquire a previously uninstantiated candidate relation/context without receiving the complete answer schema. Separate this from unrestricted topology birth/death.

Define discovery precision/recall, false-structure rate, identity/context ambiguity, stability and held-out relation-pattern metrics. Determine whether this belongs inside M4's coupled stability envelope or should remain an E04 follow-on.

**Deliverable:** a scope decision and, if relevant, a bounded discovery interface that does not silently change M3's fixed-topology claims.

### P3 — Missingness, interruption and recovery boundary

Keep distinct:
- learning while observations are corrupted or missing;
- learning from clean observations first, then experiencing an outage/degradation and recovering from retained state.

Clarify which outage, dormancy, reactivation and recovery cases are already covered by M3 and which are essential to the M4 coupled-state stability question. Do not duplicate M3's existing tests without a specific uncovered mechanism.

**Deliverable:** coverage matrix and a minimal recovery challenge, only if required for M4's stability claims.

### P4 — Transfer boundary relevant to M4/E09

Distinguish within-family world/configuration generalisation from transfer to a genuinely different task family. Decide whether M4 needs a small structurally distinct challenge to establish robustness of its stability envelope, or whether broad cross-domain transfer should remain explicitly deferred to E08.

**Deliverable:** transfer claim boundary and a minimal, justified test-domain specification if M4 requires one. Do not claim broad cross-domain transfer from synthetic factor variation.

### P5 — E09 architecture bridge

Map the M3 C0-C4 controls to the E09 architectural hypotheses:
- A: SOE-only with learned relational readout/dynamics;
- B: coupled SOE temporal memory and a separate relational state;
- C: unified augmented state;
- include a relational-only reference where it is informative.

Audit equal state/parameter/precision/update/query budgets, identical observation and supervision, ablations, composition metrics, retention/revision metrics and resource accounting. Separate “best on this task” from “architecturally necessary.”

**Deliverable:** E09 reuse/extension map. Avoid rebuilding already implemented C0-C4 controls without a demonstrated contract defect.

### P6 — Coupled M4 model and stability mathematics

Write the complete coupled state/update model before implementing it. Identify:
- continuous state variables and discrete modes;
- context routing and state-selection transitions;
- activation/dormancy/reactivation switching;
- detector and candidate-revision state;
- fit, validation, promotion and rollback transitions;
- memory/resource bounds and observation/missingness inputs;
- timing, ordering and any asynchronous/delay assumptions.

Select stability notions that match the model: boundedness, Lyapunov or multiple-Lyapunov stability, dwell-time or switching constraints, input-to-state stability, small-gain conditions, and finite-horizon amplification/recovery where asymptotic stability is too strong or inappropriate. Do not infer switched-system stability from individual frozen-mode spectral radii.

**Deliverable:** equations, assumptions, candidate proof obligations, adversarial counterexamples and measurable empirical diagnostics.

### P7 — Integrated protocol, implementation boundary and gate proposal

Integrate P0-P6 into one M4 specification. Freeze:
- the system boundary and supported operating envelope;
- task semantics and learner/evaluator separation;
- baseline/control architectures;
- state and resource accounting;
- deterministic and stochastic seed policy;
- primary stability and recovery metrics;
- uncertainty and world-level analysis;
- failure/abort conditions;
- exact evidence artifacts and aggregate verifier contract;
- explicit claim ceiling and exclusions.

The resulting M4 gate must be finite, measurable and decided before the confirmatory M4 results are visible. Do not change the accepted M3 exit record or its historical thresholds to accommodate M4.

**Deliverable:** HLG-M4 implementation protocol plus a separately versioned M4 gate/decision record for approval.

## 7. Proposed sequencing and parallelism

1. First agree the shared definitions for P0, P5 and P6: composition semantics, architecture mapping and the coupled-system boundary.
2. Then run independent mathematical/design jobs for failure attribution, bounded acquisition, recovery coverage, transfer boundary and stability proof challenges, provided their interfaces are frozen.
3. Reconcile the independent outputs, resolve disagreements and remove duplicated work.
4. Produce the integrated M4 protocol and gate proposal.
5. Review and freeze the actual M4 gate before implementation or confirmatory execution.

Parallel work must not cause multiple jobs to invent incompatible task semantics or state interfaces. No broad confirmatory campaign is authorised by this ledger.

## 8. Formal reintegration after M4: M4 -> E09

The intended convergence point is E09, not a return to E04 as though the M-series had not happened.

At the M4 close-out, prepare one evidence hand-off containing:
1. M0-M2 mathematical foundations, invariants and stability boundaries;
2. M3 mechanisms, benchmark protocol, capability result, original adaptation failure, G2 telemetry, G3 follow-on result and resource evidence;
3. M4 coupled-system equations, proof results, empirical stability envelope, negative findings and implementation limitations;
4. the E03-E08 crosswalk, including the remaining fixed-topology, representation-diversity and cross-domain limitations;
5. the C0-C4 to E09 A/B/C architecture mapping and any unresolved comparison requirements.

E09 then performs the architecture-level synthesis using the inherited evidence. It should not rerun M3 wholesale. It should run only comparisons or targeted tests needed to answer whether separate temporal and relational state adds value beyond SOE-only learned relational dynamics or a unified augmented state.

E10 remains the geometric-value investigation; geometry is not presumed to win. E11 remains the later hierarchical relational-adaptation investigation.

E-series and M-series CI/workflows remain separate. Evidence can be linked and reviewed at E09 without coupling the workflows or treating one programme's green CI as acceptance evidence for the other.

## 9. Guardrails for the M4 planning process

- Preserve original E-stage objectives and M-stage evidence lineage; do not silently rename an M3 result as an E-stage pass.
- Use “substantially investigated,” “partially evidenced,” “not tested” and “established within the declared scope” precisely.
- Never conflate stored-fact retrieval, query-conditioned binding, path selection, operator composition and answer generation.
- Never conflate M3's ordered primitive episode sequences with algebraic composition of relational operators.
- Preserve the original G2 adaptation failure and disclose the outcome-informed nature and endpoint of the revised G3 criterion.
- Do not claim open-ended topology discovery or broad cross-domain transfer from fixed-topology synthetic experiments.
- Do not claim a universal winner among SOE-only, coupled and unified memory architectures from a single task family.
- Do not infer global adaptive stability from bounded individual operators or frozen-mode spectral-radius checks.
- Do not create new campaigns, procedural gates or reports unless they close a named validity gap or are required by the accepted plan.
- Do not expand M4 into unrestricted topology birth/death, arbitrary asynchronous adaptation, or arbitrary nonlinear operator learning without a specific evidence-based need and explicit scope decision.
- Preserve E-series/M-series workflow separation.

## 10. Current planning decision

**Working programme decision:** M4 is the concluding M-series investigation. The M4 pre-implementation phase will address most of the remaining design gaps that materially affect the coupled stability question and the D2C composition lineage. After M4, the formal reintegration point is E09, where the accumulated E- and M-series evidence is used to complete the temporal-memory/relational-organisation architecture comparison.

**Not yet decided:** the detailed P0-P7 protocols, whether bounded acquisition/recovery/transfer challenges belong inside M4 or remain later E-stage work, the exact coupled-system equations and stability criteria, and the final M4 acceptance thresholds. These must be resolved before the actual M4 gate is frozen.

**Next action:** review this ledger as the starting M4 pre-implementation record, then agree the shared composition semantics, architecture mapping and coupled-system boundary before commissioning parallel design jobs.
