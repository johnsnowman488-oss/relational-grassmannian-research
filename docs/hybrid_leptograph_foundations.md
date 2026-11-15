# Mathematical foundations of the hybrid relational Leptograph

**Foundation version:** v0.1 (proposed mathematical baseline)  
**M0 scope:** analytical reference cases only  
**Status:** foundational definitions and selected propositions recorded; full coupled stability, identity recognition and endogenous topology remain open.

## 1. Research objective and claim boundary

The hybrid relational Leptograph is a proposed information-processing architecture in which:

1. modes receive, represent, process and route information across multiple dimensions;
2. modes within a group share a representational vector space;
3. different groups may have heterogeneous dimensions and communicate through directed, dimension-compatible transformations;
4. mode-level temporal memory and relationship-level historical state are distinct;
5. relational routing operators may adapt as evidence changes.

The architecture is a research hypothesis, not an established mathematical category or a demonstrated adaptive capability. It extends the Lepto-Graph Development Hypothesis (LGDH) research line; it does not modify the frozen LG-01A or LG-01B protocols or reinterpret their results. The E-series remains a separate research programme.

## 2. Modes, groups and spaces

Let the finite mode set be \(V\), partitioned into groups:

\[
V=\bigsqcup_{g=1}^{G} V_g.
\]

For \(g\ne h\), \(V_g\cap V_h=\varnothing\). Each group is assigned a finite-dimensional real inner-product space

\[
\mathcal E_g\cong\mathbb R^{d_g},\qquad d_g\geq1.
\]

For every mode \(i\in V_g\), its active state is \(x_i(t)\in\mathcal E_g\). Modes in the same group share the ambient coordinate space; they need not have identical intrinsic dynamics. Different groups may have different dimensions, bases and state semantics.

The global state space is the direct sum

\[
\mathcal X=\bigoplus_{g=1}^{G}\bigoplus_{i\in V_g}\mathcal E_g.
\]

This direct sum supplies a common mathematical state space for analysis without asserting that all modes share one representation. Group membership is fixed in v0.1. Adaptive group formation, splitting, merging and mode birth/death are deferred.

## 3. Directed relational interfaces and heterogeneous routing

For a directed candidate relation \(e:i\to j\), with source group \(g\) and target group \(h\), introduce an optional relation-specific interface space

\[
\mathcal F_e\cong\mathbb R^{q_e},\qquad q_e\geq1.
\]

Define an encoder and decoder:

\[
S_e:\mathcal E_g\to\mathcal F_e,
\qquad
D_e:\mathcal F_e\to\mathcal E_h.
\]

The composite routing operator is

\[
K_e=D_eS_e\in\mathcal L(\mathcal E_g,\mathcal E_h).
\]

In coordinates, \(S_e\in\mathbb R^{q_e\times d_g}\), \(D_e\in\mathbb R^{d_h\times q_e}\), and \(K_e\in\mathbb R^{d_h\times d_g}\). Applying it to a source state gives \(K_ex_i\in\mathcal E_h\). The reverse relation \(\bar e:j\to i\) has its own operator \(K_{\bar e}\in\mathcal L(\mathcal E_h,\mathcal E_g)\); no inverse, transpose or symmetry constraint is imposed by default.

The factorisation is not uniquely identifiable from \(K_e\) alone. For any invertible \(Q\in\mathbb R^{q_e\times q_e}\),

\[
S'_e=QS_e,\quad D'_e=D_eQ^{-1}
\]

has the same composite map \(D'_eS'_e=K_e\). Therefore M0 verifies the composite map and its dimensions, not a uniquely meaningful hidden interface basis. A physical interface semantics, normalization or additional measurements would be needed to identify the factors separately.

A map from a lower-dimensional space to a higher-dimensional space may be injective but cannot be surjective when dimensions differ in that direction. A map from a higher-dimensional space to a lower-dimensional space cannot be injective. Rank, nullspace, image and conditioning must therefore be reported when information preservation or compression is claimed. Not all routes are required to be lossless.

## 4. Mode dynamics and mode-level memory

For mode \(j\in V_h\), a dimensionally consistent candidate dynamics is

\[
\dot x_j=f_j(x_j,t)+B_ju_j(t)
+\sum_{e:t(e)=j}K_ex_{s(e)}
+\sum_r L_{jr}m_{jr}.
\tag{1}
\]

Here \(f_j:\mathcal E_h\times\mathbb R\to\mathcal E_h\), \(u_j\in\mathcal U_j\), \(B_j:\mathcal U_j\to\mathcal E_h\), and each memory readout \(L_{jr}:\mathcal M_{jr}\to\mathcal E_h\). Every summand belongs to the target mode's space.

A finite-dimensional mode-memory channel may obey

\[
\dot m_{jr}=-\nu_{jr}m_{jr}+C_{jr}\phi_{jr}(x_j,u_j,t),
\qquad \nu_{jr}>0,
\tag{2}
\]

where the injection \(C_{jr}\) maps the feature space into \(\mathcal M_{jr}\). The historical solution is an exponentially weighted integral. A finite bank gives a sum-of-exponentials memory kernel; it is a tractable finite-dimensional approximation family, not an exact representation of every possible memory kernel.

## 5. Relationship state and adaptive routing

For each directed relation \(e\), distinguish:

- \(I_e\): a lineage/identity field (provisionally supplied as a stable identifier, not inferred by M0);
- \(H_e(t)\in[0,1]\): historical evidence trace;
- \(K_e(t)\): current operational routing operator;
- \(C_e(t)\): context descriptor, whose state space and update remain open;
- \(Q_e(t)\): confidence/evidence-quality state, whose calibration and update remain open.

The v0.1 scalar historical trace is

\[
\dot H_e=\lambda_e(s_e-H_e),\qquad 0\leq s_e(t)\leq1,\quad \lambda_e>0.
\tag{3}
\]

The provisional routing adaptation law is

\[
\dot K_e=\eta_eH_es_e(\widehat K_e-K_e)
-\delta_e(1-s_e)K_e,
\qquad \eta_e,\delta_e>0.
\tag{4}
\]

Here \(s_e\) is a separately defined evidence signal and \(\widehat K_e\) is a supported target operator. Their derivation must not be circular: evidence generation, model adaptation and subsequent routing must be separately specified and leakage-controlled. M0 uses only constant evidence \(s_e=0\) and \(s_e=1\), with a fixed bounded target \(\widehat K_e\). Intermediate or time-varying evidence is explicitly outside M0.

The relationship is therefore more than a scalar edge weight: its operational state is an operator between potentially heterogeneous spaces, while its history is a separate state. This does not yet solve relational identity recognition. In particular, a decaying \(H_e\) cannot guarantee permanent identity retention; identity matching and false reactivation require separate mechanisms and experiments.

## 6. Propositions and proof obligations

### Proposition 1 — historical trace invariance

If \(H_e(0)\in[0,1]\), \(s_e(t)\in[0,1]\) is measurable and \(\lambda_e>0\), then the solution of (3) remains in \([0,1]\).

**Proof.** The variation-of-constants solution is

\[
H_e(t)=e^{-\lambda_et}H_e(0)+\lambda_e\int_0^te^{-\lambda_e(t-\tau)}s_e(\tau)d\tau.
\]

It is nonnegative. Replacing both initial history and evidence by their upper bound 1 gives \(H_e(t)\leq e^{-\lambda_et}+1-e^{-\lambda_et}=1\).

### Proposition 2 — routing-operator norm-ball invariance

Assume \(\|K_e(0)\|_F\leq M\) and \(\|\widehat K_e(t)\|_F\leq M\) for all times, with \(M\geq0\), and \(H_e,s_e\in[0,1]\). Then the closed Frobenius ball \(\|K_e(t)\|_F\leq M\) is positively invariant under (4).

**Proof.** On the boundary \(\|K_e\|_F=M\),

\[
\frac12\frac{d}{dt}\|K_e\|_F^2
=\eta H_es_e(\langle K_e,\widehat K_e\rangle_F-M^2)
-\delta(1-s_e)M^2\leq0,
\]

by Cauchy--Schwarz. The vector field cannot point out of the ball.

### Proposition 3 — exact dormancy

For constant \(s_e=0\),

\[
H_e(t)=H_e(0)e^{-\lambda_et},\qquad
K_e(t)=K_e(0)e^{-\delta_et}.
\]

The historical and operational states decay independently and may have different timescales.

### Proposition 4 — exact supported reactivation

For constant \(s_e=1\) and fixed \(\widehat K_e=K_e^*\),

\[
H_e(t)=1-(1-H_0)e^{-\lambda t},
\]

\[
K_e(t)=K_e^*+(K_e(0)-K_e^*)
\exp\left[-\eta\left(t-\frac{(1-H_0)(1-e^{-\lambda t})}{\lambda}\right)\right].
\]

The exponent's integral diverges as \(t\to\infty\), so \(K_e(t)\to K_e^*\). This proves recovery under renewed constant evidence and a fixed supported target; it does not prove that the system recognizes the returning relation as the same historical entity.

### Proposition 5 — conditional incremental stability of the mode subsystem

Write the stacked mode equation as \(\dot X=F(X,t)+\mathcal A(t)X+B(t)U(t)\). Suppose

\[
\langle X-Y,F(X,t)-F(Y,t)\rangle\leq-\mu\|X-Y\|^2
\]

for some \(\mu>0\), and

\[
\sup_t\lambda_{\max}\left(\frac{\mathcal A(t)+\mathcal A(t)^*}{2}\right)<\mu.
\]

Then two solutions under the same input contract exponentially with rate at least the difference between these bounds. This is a sufficient condition for the mode subsystem with a prescribed routing trajectory; it is not a theorem of stability for the fully coupled adaptive system.

### Proposition 6 — operator identifiability under full excitation

For the noiseless single-source residual model \(Y=KX\), if the source sample matrix \(X\in\mathbb R^{d_s\times m}\) has full row rank, then

\[
K=YX^\top(XX^\top)^{-1}
\]

is the unique operator consistent with the observations. If \(X\) is rank-deficient, only the action on its observed row space is identified. This elementary condition does not solve hidden-topology identification, noisy derivatives, correlated sources or unknown intrinsic dynamics.

## 7. Well-posedness assumptions

For a finite fixed set of modes and candidate relations, local existence and uniqueness follow under standard finite-dimensional Carathéodory conditions: the augmented vector field is measurable in time, locally Lipschitz in the augmented state almost everywhere, and locally integrably bounded. A global linear-growth bound (or an independently proven invariant compact region) is additionally required to conclude forward global existence. Bounded evidence and bounded targets support the scalar/operator invariance results above but do not, by themselves, prove global boundedness of the complete mode-memory system.

## 8. Geometric relational signatures

A candidate relational signature may be a subspace \(\mathcal S_e(t)\in\operatorname{Gr}(k,q)\), represented by an orthonormal frame \(U\in\mathbb R^{q\times k}\). For frames \(U,V\), principal angles satisfy \(\sigma_r(U^\top V)=\cos\theta_r\), and the canonical Grassmannian geodesic distance is

\[
d_{\mathrm{Gr}}(U,V)=\sqrt{\sum_r\theta_r^2}.
\]

This is basis-independent for the represented subspaces, but it is not a complete representation of a routing operator: it omits magnitude and may omit orientation or other semantics. Comparisons require a common ambient space and equal subspace rank. Geometric similarity alone is not historical identity. Geometry remains a candidate inductive bias, not a required assumption.

Higher-order relational states \(\mathcal R_{ijk}\) may be needed if group- or triple-level structure cannot be reduced to pairwise relations. This is an open extension, not part of M0.

## 9. Explicit open problems

1. Define non-circular, leakage-controlled evidence \(s_e(t)\) and target \(\widehat K_e(t)\).
2. Prove well-posedness and stability of the full augmented feedback system \((X,M,H,K)\).
3. Define relational identity, context, confidence, recurrence and false-reactivation control.
4. Establish identifiability with multiple correlated sources, unknown topology, noise and hidden interface maps.
5. Specify endogenous edge birth/death, topology revision, mode birth/death and group formation/splitting/merging.
6. Determine when higher-order relations add irreducible explanatory or predictive structure.
7. Compare shared-space, heterogeneous-space and hybrid models under matched information, supervision and compute budgets.

## 10. M0 analytical verification programme

M0 is a deterministic analytical-reference milestone, not a scientific-performance campaign. Each case is independently executable and emits one JSON result.

| Case | Reference problem | Required check |
|---|---|---|
| M0-A | One mode-level memory state, \(\dot m=-\nu m+g\), including zero-forcing washout | Exact closed form versus independent DOP853 integration |
| M0-B | One directed heterogeneous route \(\mathbb R^2\to\mathbb R^4\to\mathbb R^5\) | Operator composition, dimensions, routing and supported adaptation versus independent integration |
| M0-C | Independent forward and reverse operators | Different dimensions/rates/targets; no inverse or transpose assumption |
| M0-D | Dormancy with \(s=0\) | Exact independent exponential decay of \(H\) and \(K\) versus independent integration |
| M0-E | Reactivation with \(s=1\) after a dormant interval | Exact integrated-history solution, numerical comparison and convergence to the supported target |

The five cases are suitable for independent concurrent jobs. The final aggregation gate requires exactly one passing result for each case. M0 establishes code/formula agreement for these reference problems only. It does not establish relation discovery, identity recognition, causal correctness, adaptive topology, full-network stability or scientific utility.
