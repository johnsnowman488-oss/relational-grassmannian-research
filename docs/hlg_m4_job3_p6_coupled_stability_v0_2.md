# M4 Job 3 — P6 coupled adaptive-system model and stability analysis (working draft v0.2)

**Status:** v0.2 post-code-audit mathematical model and proof-obligation map; no theorem is claimed for the eventual implementation.
**Parent issue:** [#35](https://github.com/johnsnowman488-oss/relational-grassmannian-research/issues/35)
**Foundation:** [M4 shared scaffold v0.2](hlg_m4_shared_foundation_scaffold_v0_2.md)

## 1. Main conclusion

The M4 system is not merely a pair of stable memory subsystems. It is a coupled, mode-switching adaptive process in which observation, context routing, relation activation, candidate fitting, validation, promotion, rollback, dormancy and recovery can alter one another's dynamics.

The stability question must therefore be stated over the full admissible transition system. Stability of frozen components is insufficient. Numerical boundedness is also insufficient: the system can remain finite while silently damaging previously learned relational knowledge.

## 2. Minimal state roles

Use the following provisional state:
\[
X_t=(s_t,z_t,c_t,e_t,d_t,k_t,r_t),
\]
where:
- \(s_t\): temporal/history state;
- \(z_t\): relational organisation or relation-instance/operator state;
- \(c_t\): context and routing state;
- \(e_t\): evidence, confidence, support and activation state;
- \(d_t\): detector state and drift/change statistics;
- \(k_t\): candidate adaptation state (fit, validation, promotion, rollback);
- \(r_t\): resource/accounting state (capacity, budget, active/dormant counts).

The inclusion of \(r_t\) is deliberate: resource saturation can change the effective dynamics through eviction, throttling or refusal to promote. If resource policy is external and fixed, \(r_t\) may instead be an input/constraint, but the implementation must make this explicit.

Observation/input \(u_t\) should distinguish:
- observed data;
- query;
- missingness/outage indicators;
- external context;
- explicit intervention (e.g. controlled relation change);
- resource limits.

## 3. Hybrid transition model

Let the discrete mode be
\[
\sigma_t\in\{N,D,F,V,P,B,O,R\},
\]
where \(N\)=normal operation, \(D\)=detection, \(F\)=candidate fit, \(V\)=independent validation, \(P\)=promotion, \(B\)=rollback, \(O\)=dormancy/outage, and \(R\)=reactivation/recovery.

The system evolves as
\[
X_{t+1}=F_{\sigma_t}(X_t,u_t,\xi_t),
\qquad
\sigma_{t+1}=\Delta(\sigma_t,X_t,u_t,\xi_t),
\]
where \(\xi_t\) is bounded stochastic noise or a declared random input. The transition function must include guard conditions, minimum sample counts, validation thresholds, promotion rules, rollback triggers, dwell-time or cooldown rules, and resource ceilings. These cannot remain informal implementation details.

A candidate lifecycle should be explicit:
1. detection creates a candidate but does not modify trusted relational state;
2. fitting uses only designated fit data;
3. validation uses independent data and cannot be reused for fitting;
4. promotion is an atomic, auditable transition subject to resource and safety checks;
5. rollback restores the last trusted state or a specified safe approximation;
6. dormant/reactivated states have explicit retention and re-entry semantics.

## 4. Coupled local dynamics

For a local perturbation around a reference trajectory, the temporal and relational blocks may be approximated by
\[
\begin{bmatrix}\delta s_{t+1}\\\delta z_{t+1}\end{bmatrix}
=
\begin{bmatrix}A_{ss}&A_{sz}\\A_{zs}&A_{zz}\end{bmatrix}
\begin{bmatrix}\delta s_t\\\delta z_t\end{bmatrix}
+B\delta u_t.
\]
The off-diagonal blocks represent coupling. Even if \(A_{ss}\) and \(A_{zz}\) are individually Schur stable, the full block matrix need not be stable.

For example, let
\[
A=\begin{bmatrix}0.5&1.2\\1.2&0.5\end{bmatrix}.
\]
Each diagonal subsystem alone has eigenvalue \(0.5\), but the coupled matrix has eigenvalues \(1.7\) and \(-0.7\), so the coupled system is unstable. This counterexample is enough to reject the inference “each subsystem is stable, therefore the coupled system is stable.”

For switched dynamics, even stability of every frozen mode does not imply stability under arbitrary switching. A common Lyapunov function is sufficient for arbitrary switching when it decreases for every admissible mode. Where no common function exists, multiple-Lyapunov/dwell-time conditions may provide a narrower guarantee. The switching law itself must be included in the model.

## 5. Candidate small-gain condition

Suppose compatible norms yield uniform bounds:
\[
\|\delta s_{t+1}\|\le a\|\delta s_t\|+b\|\delta z_t\|+g_s\|\delta u_t\|,
\]
\[
\|\delta z_{t+1}\|\le c\|\delta s_t\|+d\|\delta z_t\|+g_z\|\delta u_t\|.
\]
Define
\[
G=\begin{bmatrix}a&b\\c&d\end{bmatrix}.
\]
A condition such as \(\rho(G)<1\) can be a sufficient contraction/small-gain condition under the stated uniform norm bounds and compatible state scaling. It is not automatic from fitted local Jacobians, average gains or sampled trajectories. P6 must establish bounds over the declared operating set or clearly downgrade the claim to an empirical local diagnostic.

For nonlinear systems, local Jacobian evidence does not establish global stability. The report must identify the region of validity, smoothness/Lipschitz assumptions, bounded inputs and mode-transition constraints.

## 6. Stability properties to distinguish

Do not use “stable” as one undifferentiated endpoint.

1. **State boundedness:** state and resource variables remain within declared limits.
2. **Perturbation stability:** bounded initial perturbations remain bounded or decay under specified inputs/modes.
3. **Input-to-state stability:** bounded observation disturbances produce bounded state deviation with a quantified gain.
4. **Switching stability:** admissible mode sequences do not destabilise the system; state the switching/dwell-time assumptions.
5. **Transient amplification:** quantify finite-horizon peak amplification even if asymptotic decay holds.
6. **Recovery:** return to a declared operating region/performance band after outage, drift, false candidate or rollback.
7. **Relational integrity:** unrelated trusted relations remain valid and retrievable through adaptation, except for explicitly targeted revisions.
8. **Resource stability:** state, candidate count, metadata and compute remain within bounds without unreported eviction or degradation.

A finite benchmark can establish an empirical envelope, not a universal theorem.

## 7. Relational integrity and legitimate revision

Let \(\mathcal R_{old}\) be the set of trusted relations before an adaptation event and \(\mathcal R_{target}\) the subset legitimately targeted by the event. Measure collateral damage on
\[
\mathcal R_{protected}=\mathcal R_{old}\setminus\mathcal R_{target}.
\]
A possible loss-based diagnostic is
\[
D_{protected}(k)=L_{protected}(t_0+k)-L_{protected}(t_0^-),
\]
with positive values indicating degradation under the chosen loss convention. Also report relation-instance survival, witness validity, retrieval and false activation. The target set must be evaluator-defined for scoring; the learner may only receive the permitted change evidence.

This prevents a system from appearing stable merely because its vector norm remains bounded while it corrupts old knowledge. Conversely, a correct targeted revision must not be counted as damage simply because the old relation changed.

## 8. Promotion and rollback proof obligations

For every transition into promotion, establish:
- validation data are independent from fit data;
- candidate evidence exceeds a frozen criterion;
- promotion is atomic or has a defined safe intermediate state;
- trusted-state snapshot/rollback semantics are explicit;
- protected-relation damage is measured before and after promotion;
- resource capacity is checked before committing;
- cooldown/dwell-time prevents uncontrolled repeated switching where needed.

For rollback, establish:
- the restored state is the intended trusted snapshot/version;
- rollback itself does not erase unrelated valid updates;
- the system re-enters a defined safe mode;
- subsequent reactivation does not immediately re-promote the rejected candidate without new evidence.

These are candidate obligations, not proof that any existing implementation satisfies them.

## 9. Adversarial counterexamples and required tests

| Failure mode | Why a naive test misses it | Required diagnostic |
|---|---|---|
| Stable isolated blocks, unstable coupling | Tests each subsystem separately | Coupled perturbation test and joint Jacobian/trajectory analysis |
| Stable frozen modes, unstable switching | Tests each mode without switching | Adversarial admissible mode-sequence test |
| Bounded state, damaged relations | Tracks only vector norms | Protected-relation integrity before/after adaptation |
| Repeated false detections | Measures detector accuracy on one event | Stationary negative-control streams and alarm/promotion rates |
| Candidate leakage | Uses validation data during fitting | Fit/validation provenance audit |
| Unsafe promotion | Measures candidate gain only | Promotion stress with protected relations and rollback |
| Resource saturation | Tests below capacity | Capacity-boundary and eviction/throttling tests |
| Outage/recovery oscillation | Tests one clean outage | Repeated outage/reactivation and dwell-time diagnostics |

## 10. M4 empirical diagnostics (candidate set)

- joint-state norm and per-block norm;
- maximum finite-horizon amplification after bounded perturbation;
- empirical recovery time and residual error;
- mode-transition counts, dwell times and oscillation rates;
- false alarm, candidate, promotion and rollback rates under stationary controls;
- candidate validation gain and post-promotion untouched loss;
- protected-relation integrity loss and witness survival;
- active/dormant/candidate/resource counts;
- memory, update, query and wall-clock cost.

Metrics must be tied to explicit denominators and world/seed-level uncertainty. Do not choose thresholds after viewing confirmatory outcomes.

## 11. Assumptions and claim ceiling

A future proof or empirical claim must state:
- state and input domains;
- norm and scaling;
- boundedness of observations/disturbances;
- regularity/Lipschitz assumptions where used;
- mode set and allowed transition graph;
- minimum/maximum dwell times and cooldowns;
- resource saturation/eviction policy;
- candidate validation and rollback semantics;
- whether the result is local, regional, global, asymptotic or finite-horizon.

Without these, a spectral-radius calculation or successful finite run is not a stability proof.

## 12. Open decisions for integration

1. Which of \(s,z,c,e,d,k,r\) are actual state variables in A/B/C/R, and which are external controls?
2. What exact mode-transition graph is implemented, and which transitions are forbidden?
3. Is the candidate lifecycle atomic? If not, what safe intermediate states exist?
4. Which stability properties can be proven for the bounded model, and which are empirical only?
5. What perturbation and protected-relation challenge is the minimum sufficient M4 test?
6. Does P5's B architecture use genuinely independent relational persistence, or is it only an internal coordinate partition?

## 13. Current result

P6 now has a candidate hybrid model, a coupled-instability counterexample, conditional small-gain framing, a stability taxonomy and proof/test obligations. No global stability theorem, implementation validation or M4 pass is claimed. The model must be reconciled with the actual P0 task contract and P5 architecture transitions before it can become the implementation specification.


## 14. Cross-check against the actual M3 state and transition implementation

### Refined state vector

The actual adaptive learner contains more persistent state than a two-block temporal/relational sketch. Use the scaffold v0.2 bookkeeping model:
\[
X_t=(m_t,z_t,c_t,\theta_t,e_t,d_t,k_t,r_t),
\]
where:
- \(m_t\): temporal SOE state, if the chosen M4 architecture actually includes the SOE primitive;
- \(z_t\): relation instances and/or stored per-context relation operators;
- \(c_t\): context prototypes, scatter/metric state, pending novelty and routing decision;
- \(\theta_t\): predictor sufficient statistics/learned parameters (for current M3, packed Gram and cross statistics in \`MultiSourceRidge\`);
- \(e_t\): per-relation evidence, usefulness, activation score, counts and active flag;
- \(d_t\): detector statistic, observation/alarm counts;
- \(k_t\): accepted/candidate operator versions, candidate fit/validation state, lifecycle phase and promotion/rejection record;
- \(r_t\): resource limits and accounting, as a state only if resource pressure changes dynamics through eviction, throttling or admission decisions.

Separate \(m_t\) from \(\theta_t\): a fixed exponential trace bank is not the same state as a learned estimator's accumulated Gram/cross statistics. Separate relation-instance truth from learned relation operators in \(z_t\).

### Existing state sources

| Component | State it actually maintains | P6 implication |
|---|---|---|
| \`SOEMemory\` | Fixed-rate exponential channels and injection matrices | Standalone stable linear memory primitive; it is not currently wired into the M3 integrated-refinement runner. |
| \`ContextBank\` | Context metric, slot means/scatter, pending novelty and per-slot relation operators | Context and relational/operator state are intertwined in one implementation object but conceptually separable. |
| \`MultiSourceRidge\` | Packed upper Gram statistic, target cross-statistic, sample/prediction/update counts; coefficients solved from those statistics | Explicit estimator state \(\theta_t\), updated sequentially with forgetting. |
| \`EvidenceActivation\` | Per-relation evidence masses, usefulness, count, activation score and active flag | Discrete activation gate plus numeric evidence state; missing observations return without update. |
| \`CUSUMDetector\` | One-sided residual statistic, observation count and alarm count | Detector state \(d_t\); an alarm resets the statistic. |
| \`CandidateRevision\` / \`CandidateLifecycle\` | Incumbent/candidate operators, candidate active status, fit/validation/post-promotion accumulators and lifecycle phase | Candidate state \(k_t\); promotion/rejection are explicit, but rollback is not supplied as a general operation. |
| \`MemoryArchitecture\` C0-C4 | The control-specific arrays/readouts audited in P5 | Reference memory-control states only; not a full M4 adaptive network. |

### Actual sequential mode path

The current \`run_integrated_refinement\` path is synchronous and step-indexed. It resolves context, computes shadow/effective predictions with context and activation gates, observes/scorers the target, updates estimator statistics, updates identifiability/evidence/activation, updates C3/C4 resource controls, then evaluates residual detection and candidate adaptation. Its coarse candidate phase is \`WAITING → TRAIN → VALIDATE → DONE\`; context decisions are ACCEPT/NOVEL/ABSTAIN and per-source activation is on/off.

The separate \`CandidateLifecycle\` class has \`IDLE → FIT → VALIDATION → POST_PROMOTION → COMPLETE\` with non-overlapping fit/validation/post-promotion windows. Do not conflate that windowed utility with the simpler list-based lifecycle in \`run_integrated_refinement\`.

\`CandidateRevision.evaluate\` promotes a validated candidate or rejects it while preserving the incumbent. It does not provide a general rollback-after-promotion API. Thus:
- promotion/rejection are present in the M3 code;
- safe rollback after a later detected regression is not established by this implementation;
- dormancy/reactivation exist at the relation activation/context level, but not as a general hybrid-system mode with a verified recovery theorem;
- arbitrary asynchronous updates and delays are not present in the current sequential harness.

These latter transitions may be added to M4 only if the accepted operating envelope includes them. They must be labelled new implementation work, not assumed pre-existing capabilities.

### Stability-relevant counterexamples

The current controls expose concrete reasons for full transition analysis:
- C1, C2 and C3 state coordinates add the input signal without decay or projection. Repeated constant nonzero input causes unbounded linear growth.
- C4's shared latent state has a per-write decay/write update and is contractive for bounded inputs under the default \(0<rate<1\), but the associated readout and task-readout matrices can accumulate updates without a built-in norm projection or parameter bound.
- The fixed SOE channels have exponential decay for positive rates, but this does not prove stability of the coupled learner, context, detector or candidate lifecycle.
- The local coupled-block counterexample in section 4 remains valid; switching and adaptive transitions must be analysed over the complete admissible mode graph.

### P6 obligations updated by the audit

1. Use the expanded \(m,z,c,\theta,e,d,k,r\) decomposition and identify which components exist in each A/B/C/R implementation.
2. Model the actual synchronous M3 transition order as the inherited baseline; do not introduce asynchronous/delay variables unless an M4 hypothesis explicitly requires them.
3. Keep promotion/rejection distinct from rollback. If rollback is included, specify the trusted snapshot/version and a test that rollback preserves unrelated valid updates.
4. Test boundedness of the selected M4 state under bounded inputs, including learned readout/estimator parameters—not just the decaying SOE or shared latent state.
5. Keep relational integrity separate from numeric state boundedness; evaluate protected relation/witness survival through promotion, rejection, optional rollback and context/activation changes.
6. Treat current resource accounting as a measured constraint contract; model resource pressure as a transition only if it can actually affect state updates.
7. Test switching sequences, transient amplification and recovery on the actual coupled A/B/C variants selected by P5, not only on isolated controls.

**P6 audit decision:** the hybrid-system framework remains appropriate, but the state vector and current-mode mapping required refinement. No M4 stability theorem or pass is inferred from existing M3 tests.
