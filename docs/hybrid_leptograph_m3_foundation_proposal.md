# HLG-M3 — proposed mathematical foundation

**Document:** HLG-M3-FOUNDATION-PROPOSAL-v0.1  
**Status:** Adopted as the proposed foundation for investigation; not frozen as the implementation protocol  
**Date:** 2026-11-15  
**Architecture policy:** incremental extension of the existing heterogeneous finite-dimensional vector-space framework

## 1. Purpose and decision boundary

M3 investigates whether a hybrid relational Leptograph can learn, retain, retrieve, revise and reuse candidate relationships from experience. It is a computational-learning investigation, not merely an operator representation exercise.

This architecture is adopted as the proposed HLG-M3 foundation. Seven independent mathematical design jobs must challenge it before an implementation protocol is frozen. A green campaign means reference analyses executed; it does not automatically authorise implementation or validate every proposed mechanism.

M3 freezes candidate topology during controlled experiments. Candidate directed relationships and endpoints are supplied by the benchmark. M3 learns relationship operators, contextual applicability, predictive usefulness, evidence and activation. Autonomous edge birth/death, group reorganisation, open-ended relation discovery and persistent identity across topology changes remain outside M3's claim boundary.

## 2. Inherited mathematical substrate

For each group \(g\), retain a finite-dimensional real inner-product space

\[
\mathcal E_g\cong\mathbb R^{d_g},\qquad x_g(t)\in\mathcal E_g.
\]

Different groups may have different dimensions. Modes within a group share the group's local state space. A candidate directed relation \(e:i\to j\) is a dimension-compatible linear operator

\[
\Theta_e:\mathcal E_i\to\mathcal E_j.
\]

Reverse relations remain independent. No inverse, transpose, symmetry or common coordinate dimension is assumed.

M1's coordinate/metric discipline applies to every new mechanism. If source and target coordinate changes are \(A_i,A_j\), then

\[
\Theta'_e=A_j^{-1}\Theta_e A_i,\qquad
G'_i=A_i^\top G_iA_i,\qquad G'_j=A_j^\top G_jA_j.
\]

Learning penalties, context distances, uncertainty and operator constraints must be metric-aware or expressed in whitened coordinates. Plain Euclidean penalties in arbitrary coordinate charts are not accepted as invariant M3 defaults.

## 3. Core architectural separation

M3 distinguishes four roles:

1. Stored relationship knowledge: a retained operator estimate and its estimation statistics.
2. Historical evidence: positive/negative predictive support and recent usefulness.
3. Context applicability: the conditions under which a relationship has been observed to be useful.
4. Current route activation: the extent to which stored knowledge participates in computation.

Dormancy is not erasure. A route can have near-zero computational influence while its stored operator remains available for later retrieval.

For target group \(h\), let In(h) be its fixed set of candidate incoming relations. Maintain a bounded context bank

\[
\mathcal C_h=\{c_{h,1},\ldots,c_{h,M_h}\}.
\]

A context slot is shared by incoming relation estimators for that target group, preventing different incoming relations from silently assigning one observation to incompatible contexts.

A context slot contains a context prototype \(\mu_m\) and covariance descriptor \(\Sigma_m\), joint online regression sufficient statistics for that target/context, residual/noise and estimator-uncertainty diagnostics, and a fixed set of incoming relation records.

For candidate relation \(e\in\mathrm{In}(h)\) and context slot \(m\), the relation record is

\[
\mathcal R_{e,m}=
(\Theta_{e,m},N^+_{e,m},N^-_{e,m},U_{e,m},a_{e,m},v_{e,m}),
\]

where \(\Theta\) is the stored operator, \(N^+,N^-\) are discounted positive/negative evidence masses, \(U\) is a recent signed usefulness trace, \(a\in[0,1]\) is route activation, and \(v\) is an operator version identifier. Operator-estimation uncertainty and conditional-identifiability diagnostics belong to the joint estimator, not to the relational-reliability score.

The scalar M0 history \(H_e\) remains a valid reference/control and may be reported as an aggregate diagnostic. It is not added as a redundant live state when its role is already represented by the evidence bank.

## 4. Context recognition, ambiguity and slot management

Map observed context to a documented feature vector

\[
z_t=\psi(o_t)\in\mathcal C,
\]

where \(\mathcal C\) is a declared finite-dimensional context feature space with Gram matrix \(G_c\). The first benchmark should use a fixed, auditable \(\psi\); learning a context encoder simultaneously would confound retrieval evaluation.

For a slot with prototype \(\mu_m\) and covariance \(\Sigma_m\), use metric-aware regularised covariance

\[
\bar\Sigma_m=\Sigma_m+\epsilon_cG_c^{-1}
\]

and squared Mahalanobis distance

\[
d_m^2(z_t)=(z_t-\mu_m)^\top
\bar\Sigma_m^{-1}(z_t-\mu_m).
\]

If slot covariances differ, compare properly normalised Gaussian scores, including the log-determinant term:

\[
L_m(z_t)=d_m^2(z_t)+\log\det\bar\Sigma_m.
\]

The additive Gaussian constant may be omitted for ranking. The log-determinant term must not be omitted when slot covariance volumes differ. Under invertible coordinate changes, transform the context covariance and metric together; distances and rankings must remain invariant.

Context resolution has three outcomes:

- Accept: the best slot satisfies a validation-derived absolute fit threshold and its margin over the runner-up is sufficiently large.
- Abstain: multiple slots are too similar, the best score is insufficient, required context fields are missing, or assignment is otherwise ambiguous. No relationship is activated and no context-specific estimator/evidence is updated for that sample.
- Novel candidate: no slot fits. Accumulate a novelty candidate; create a new initially inactive slot only after a predeclared repeated-novelty criterion is met and capacity remains.

No slot is silently overwritten when the bank is full. Overflow is explicit abstention and a recorded capacity event. Thresholds, novelty count and slot capacity must be chosen on training/validation data before held-out evaluation. Automatic context merging is not required in M3-v0.1.

## 5. Online heterogeneous operator estimation

For each target group/context slot, concatenate all incoming source states and context nuisance features:

\[
\phi_{h,t}=
\operatorname{col}\left(
x_{i(e_1)}(t),\ldots,x_{i(e_q)}(t),
z_t,1
\right).
\]

The target observation is \(y_{h,t+1}=x_h(t+1)\). Use the joint additive model

\[
y_{h,t+1}=W_{h,m}\phi_{h,t}+\varepsilon_{h,t}.
\]

Partition \(W_{h,m}\) into relation blocks \(\Theta_{e,m}\), a context nuisance block and an intercept. Estimate incoming source blocks jointly; otherwise the model can falsely imply that every route is separately identifiable when source trajectories are correlated. This is a controlled first-order additive predictor. Nonlinear interactions and higher-order relations remain later research questions.

Let \(G_\phi\) be the direct-sum Gram matrix of the concatenated feature space and \(G_h\) the target Gram matrix. Choose whitening factors \(C_\phi^\top C_\phi=G_\phi\) and \(C_h^\top C_h=G_h\). Define

\[
\widetilde\phi=C_\phi\phi,\quad
\widetilde y=C_hy,\quad
\widetilde W=C_hWC_\phi^{-1}.
\]

For valid accepted observations, update in whitened coordinates:

\[
S_t=\gamma S_{t-1}+\omega_t\widetilde\phi_t\widetilde\phi_t^\top,
\]

\[
T_t=\gamma T_{t-1}+\omega_t\widetilde y_t\widetilde\phi_t^\top,
\]

\[
\widehat{\widetilde W}_t
=
T_t(S_t+\lambda_r I)^{-1}.
\]

Use a stable linear solve, not an explicit numerical inverse. Translate back to the declared coordinates. The forgetting factor is applied per valid accepted observation (or a declared valid-observation clock), not merely because wall-clock time passed. If no target is observed or context is ambiguous, the operator statistics are not updated. This preserves the stored estimate through inactivity.

This is exponentially weighted regularised least squares, not an assertion that every block is identifiable. Residual covariance and estimator uncertainty must be reported separately from relational reliability. Any uncertainty interval used for gating requires independent coverage/calibration checks.

For relation feature block \(e\), let \(S_{ee}\) be its information block and \(S_{-e,-e}\) the information for all competing source/context nuisance features. Its conditional information is the Schur complement

\[
S_{e\mid-e}
=
S_{ee}-S_{e,-e}S_{-e,-e}^{\dagger}S_{-e,e}.
\]

Report numerical rank, minimum identifiable eigenvalue and condition number using a predeclared tolerance. If \(S_{e\mid-e}\) is rank deficient, do not describe the full operator as uniquely identified. Freeze unsupported directions or mark them as unidentified; regularisation can produce a finite estimate but cannot create missing information.

For \(G_i=C_i^\top C_i\) and \(G_j=C_j^\top C_j\), define the metric-aware operator norm

\[
\|\Theta_e\|_{G_i\to G_j}
=
\|C_j\Theta_e C_i^{-1}\|_2.
\]

Constrain the retained operator by projection in whitened coordinates into a declared norm ball, so that \(\|\Theta_e\|_{G_i\to G_j}\le R_e\). Plain Euclidean clipping is acceptable only in explicitly declared orthonormal-coordinate reference experiments.

## 6. Non-circular prequential relational evidence

Evaluate evidence before the current target observation updates the estimator. For a valid observed target, compute the pre-update full prediction and the counterfactual prediction with relation \(e\)'s contribution omitted:

\[
\widehat y^{-e,-}_{t+1}
=
\widehat y^{\mathrm{all},-}_{t+1}
-\widehat\Theta^{-}_{e,m}x_{i(e)}(t).
\]

For a declared loss \(\ell\), define

\[
\Delta_{e,t}
=
\ell(y_{t+1},\widehat y^{-e,-}_{t+1})
-
\ell(y_{t+1},\widehat y^{\mathrm{all},-}_{t+1}).
\]

Positive \(\Delta\) means the relation improved prediction in this prequential test; negative \(\Delta\) means it worsened prediction. This is a conditional marginal predictive contribution under the current joint model, not a causal effect or context-free value. Correlated sources can make attribution ambiguous. Causal claims require interventions or randomized route manipulations in the benchmark.

Only evaluate when the target is observed, required source features are valid, context is accepted and observation quality passes. Use the current prediction first; only then update the estimator. A shadow prediction remains available for inactive candidates so a dormant relationship can be evaluated for reactivation.

Let \(w_t\in[0,1]\) be declared observation/context quality, and \(z_{e,t}\in\{-1,0,+1\}\) the thresholded sign of \(\Delta_{e,t}\). Then

\[
N^+_{t+1}=\rho_q^{\Delta t}N^+_t+w_t\mathbf1[z=+1],
\quad
N^-_{t+1}=\rho_q^{\Delta t}N^-_t+w_t\mathbf1[z=-1].
\]

When there is no valid observation, no positive or negative event is added. Historical evidence may slowly discount with elapsed time, but this is not recorded as negative evidence. Recent usefulness obeys

\[
U_{t+1}=\rho_u^{\Delta t}U_t+
(1-\rho_u^{\Delta t})\operatorname{clip}(\Delta_{e,t}/s_\Delta,-1,1)
\]

for a valid observation, and decays toward zero without one.

Define positive-evidence balance and support sufficiency:

\[
Q_e=\frac{a_0+N^+_e}{a_0+b_0+N^+_e+N^-_e},\qquad
\chi_e=\frac{N^+_e+N^-_e}{N^+_e+N^-_e+n_0}.
\]

These are discounted pseudo-count scores. \(Q_e\) is not automatically a calibrated probability. Estimator uncertainty, evidence balance and evidence sufficiency remain separate quantities.

## 7. Dormancy, activation and retained knowledge

Let \(g_{e,m}(z_t)\in[0,1]\) be a validation-derived context-match score. Let \(I_{e,m}\in[0,1]\) be an identifiability/estimation-confidence gate whose construction must be justified by F2/F7. A provisional desired activation is

\[
a^*_{e,m}=
g_{e,m}(z_t)\,
\chi_{e,m}\,
\max(0,2Q_{e,m}-1)\,
\max(0,U_{e,m})\,
I_{e,m}.
\]

A hysteresis controller uses separate activation/deactivation thresholds \(\tau_{\rm on}>\tau_{\rm off}\). Smooth accepted activation with

\[
a_{t+1}=(1-\nu_a)a_t+\nu_a a^*_t,\qquad0<\nu_a\le1.
\]

Ambiguous or novel context abstention suppresses effective routing for that context. No evidence, insufficient support or failed identifiability prevents new activation. The effective route is

\[
K^{\rm eff}_{e,m}(t)=a_{e,m}(t)\Theta_{e,m}(t).
\]

Since \(0\le a\le1\), a metric-aware stored-operator bound also bounds each effective edge operator. The stored \(\Theta\) is not forced toward zero merely because \(a\) decays. This is the principal architectural separation between learned relationship knowledge and current computational activity.

## 8. Revision without destructive overwriting

A changed relationship must be revised without one noisy observation destroying a previously useful operator. The proposed two-phase revision is:

1. Detect persistent prequential residual deterioration/change using a declared detector such as CUSUM/EWMA, with false-alarm rate measured on stationary controls.
2. Start a bounded candidate estimator using a recent valid-observation window. Keep the last accepted operator version intact.
3. Require candidate identifiability, sufficient samples and predeclared held-out predictive improvement before promotion.
4. Promote a new version only after validation; otherwise reject the candidate and retain the previous version.

The current route may be conservatively down-weighted while revision is uncertain. One bounded previous version plus one candidate is sufficient for the first implementation proposal. F4/F6/F7 must examine detector false alarms, detection delay, stale-operator damage and collateral effects before this mechanism is frozen.

## 9. Memory architecture comparison

Compare C0 no persistent state; C1 mode-level temporal memory only; C2 relational memory only; C3 separate mode and relational stores; and C4 a unified shared state with common write/update dynamics and mode/relationship readouts.

C4 must be a substantive shared-state alternative, not a concatenation with block-diagonal updates. Its initial control may use a bounded learned state-space transition with shared latent coordinates and mode/relationship readouts.

C3 and C4 must be compared at matched persistent-state bytes and precision, with trainable parameter count, update compute and query compute reported. Exact equality at one architecture setting may be impossible; pre-register a common budget envelope and compare matched Pareto points within declared tolerances. Do not claim fairness from state dimension alone. Allocate C3's total state budget between its stores using validation data only.

Measure temporal retention, relational retention, interference, reactivation, revision, transfer, state bytes, parameter count, update cost and query cost separately. C0 is the zero-persistent-state reference. No architecture is selected in advance.

## 10. Integrated M3 learning task

The benchmark uses planted ground-truth relations and evaluator-only labels. The learner sees only allowed observations, context features, source/target states, observation masks and permitted task signals.

The task sequence includes: acquisition under adequate excitation; distractor/frequently activated but unhelpful relations; contexts where one relation has different usefulness or operators; near-duplicate/ambiguous and novel contexts; observation interruption with no false negative evidence; reactivation after a gap; persistent operator drift or sudden within-context change; unrelated relations that should not be damaged by local revision; and held-out combinations of known candidate relations.

Split by independent worlds/seeds and held-out relational configurations. Keep evaluator ground truth, planted operators, relation identity labels and future observations out of learner inputs. Prequential predictions precede target updates. Report relation estimation, evidence calibration, context acceptance/abstention, false activation, reactivation, revision, compositional transfer and computational cost separately.

M3 success establishes adaptation among supplied candidate relations in the tested synthetic task family. It does not establish open-ended topology discovery, causal understanding, unrestricted generalisation or global adaptive-network stability.

## 11. Mathematical proof and test obligations

Test coordinate covariance of context metrics, regression estimates and operator constraints; bounded context statistics, evidence masses, usefulness, activation and operator norms; no-observation semantics; prequential no-leakage sequencing; heterogeneous operator estimation under noise; conditional identifiability and rejection of rank-deficient claims; false attribution under correlated sources; context separation, ambiguity abstention, novelty and full-bank overflow; retention through inactivity; revision false alarms, delay and collateral damage; memory-control resource matching; and switched/non-normal network counterexamples.

M2's fixed LTI spectral-radius criterion is not a general criterion for time-varying adaptive systems. M3 proves only local subsystem/parameter bounds under stated assumptions. Coupled network stability belongs to M4.

## 12. Seven-job mathematical design campaign

| Job | Focus | Main outputs |
|---|---|---|
| F1 | Prequential evidence and attribution | True/decoy contributions; leakage and correlated-source ambiguity probes |
| F2 | Metric-aware online operator estimation | Heterogeneous operator recovery; coordinate covariance; conditional rank |
| F3 | Context memory and abstention | Metric-invariant retrieval; separated/ambiguous/novel contexts; bounded slots |
| F4 | Evidence, activation and revision | Bounded pseudo-counts; no-observation semantics; hysteresis; revision challenge |
| F5 | Fair memory architecture controls | C0-C4 contract; state/parameter/compute budget rules; comparison readiness |
| F6 | Integrated learning benchmark | Deterministic phases, evaluator-only truth, split/leakage audit |
| F7 | Independent mathematical/adversarial review | Counterexamples, metric invariance, identifiability and M4 boundary |

Each job writes one JSON evidence file. The aggregate requires exactly F1-F7 and reports execution validity separately from design readiness. This campaign does not automatically freeze the implementation protocol. Review its output, resolve outstanding choices, then author the implementation protocol.

## 13. Explicit unresolved design choices

Select from validation evidence and document before implementation protocol freeze: initial fixed context feature map and provenance; context covariance estimation and acceptance/margin/novelty thresholds; maximum context slots and repeated-novelty criterion; evidence loss, scale, dead-zone and observation-quality weight; forgetting rates; regularisation, identifiability tolerances and operator norm radii; uncertainty calibration and activation gating; activation thresholds, smoothing and hysteresis; residual change detector, candidate-window length and promotion rule; memory budget envelope and matched-comparison tolerances; task seeds, held-out splits, noise/drift schedules and minimum effect thresholds.

Parameters must be selected on training/validation data and frozen before held-out testing. No claim or threshold should be adjusted after inspection of the final test set.

## 14. Status

**Adopted as proposed foundation:** yes.  
**Mathematical design campaign:** pending seven parallel jobs and result analysis.  
**Implementation protocol:** not frozen.  
**Production M3 implementation:** not authorised by this document.
