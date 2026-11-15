# HLG-M1 — Heterogeneous Dimensional Routing and Geometric Invariance

**Protocol:** HLG-M1-v0.1  
**Status:** Frozen for analytical/implementation verification  
**Date:** 2026-11-15  
**Prerequisite:** HLG-M0 analytical reference gate passed

## 1. Question and claim boundary

Do directed linear routing operators between heterogeneous finite-dimensional inner-product spaces, their compositions and their subspace-geometric signatures transform consistently under changes of coordinates, while preserving the intrinsic rank and metric structure of the represented maps?

M1 is an algebraic and geometric verification milestone. Routing operators are fixed inputs; M1 does not learn them. It does not test relation discovery, causal attribution, identity matching, confidence calibration, adaptive topology, online operator updates or full-network stability.

## 2. Mathematical setting

Let \(\mathcal E_s,\mathcal E_t\) be finite-dimensional real inner-product spaces with dimensions \(d_s,d_t\). A directed route is a linear map

\[
K:\mathcal E_s\to\mathcal E_t.
\]

Choose coordinates in each space. Vectors are columns, and the matrix of the route has shape \(d_t\times d_s\).

### 2.1 Orthonormal basis change

Let \(Q_s\in O(d_s)\) and \(Q_t\in O(d_t)\) be orthogonal coordinate changes. Adopt the passive-coordinate convention

\[
x_{\rm old}=Q_s x_{\rm new},\qquad
y_{\rm old}=Q_t y_{\rm new}.
\]

The same abstract map is represented by

\[
K_{\rm new}=Q_t^\top K_{\rm old}Q_s.
\tag{M1.1}
\]

Consequently,

\[
K_{\rm new}x_{\rm new}=Q_t^\top K_{\rm old}x_{\rm old}.
\]

Thus outputs are covariant, while Euclidean norms, Frobenius norm, rank and singular values are invariant. Source and target bases are transformed independently; the dimensions need not match.

### 2.2 General invertible coordinate change and metric transport

An arbitrary invertible coordinate change is not generally an isometry. Let \(A_s\in GL(d_s)\) and \(A_t\in GL(d_t)\) and write

\[
x_{\rm old}=A_s x_{\rm new},\qquad
y_{\rm old}=A_t y_{\rm new}.
\]

Then the map matrix transforms as

\[
K_{\rm new}=A_t^{-1}K_{\rm old}A_s.
\tag{M1.2}
\]

If the old coordinate Gram matrices for the inner products are positive definite \(G_s,G_t\), their new-coordinate matrices must be

\[
G_{s,\rm new}=A_s^\top G_{s,\rm old}A_s,\qquad
G_{t,\rm new}=A_t^\top G_{t,\rm old}A_t.
\tag{M1.3}
\]

This makes the represented abstract norms invariant:

\[
x_{\rm old}^\top G_{s,\rm old}x_{\rm old}
=x_{\rm new}^\top G_{s,\rm new}x_{\rm new}.
\]

Let \(G_s=C_s^\top C_s\) and \(G_t=C_t^\top C_t\) be Cholesky whitenings. The metric-aware singular values of \(K\) are the ordinary singular values of

\[
\widetilde K=C_tKC_s^{-1}.
\tag{M1.4}
\]

They are invariant under (M1.2)–(M1.3). The ordinary Euclidean singular values of \(K_{\rm new}\) need not be invariant under a general non-orthogonal coordinate change. M1 explicitly guards against conflating coordinate covariance with Euclidean isometry.

### 2.3 Composition across groups

For a chain

\[
\mathcal E_0\xrightarrow{K_1}\mathcal E_1
\xrightarrow{K_2}\cdots
\xrightarrow{K_n}\mathcal E_n,
\]

the composite is \(K_{n:0}=K_n\cdots K_2K_1\). Under independent orthogonal bases \(Q_0,\ldots,Q_n\),

\[
K'_{i+1,i}=Q_{i+1}^\top K_{i+1,i}Q_i.
\]

The internal basis changes cancel:

\[
K'_{n:0}=Q_n^\top K_{n:0}Q_0.
\tag{M1.5}
\]

Every adjacent source/target dimension must match. No common ambient dimension is required across the chain.

### 2.4 Interface factorisation and gauge freedom

For an interface space of dimension \(q\),

\[
S:\mathcal E_s\to\mathcal F,\qquad
D:\mathcal F\to\mathcal E_t,\qquad K=DS.
\]

Under arbitrary invertible coordinate changes \(A_s,A_f,A_t\),

\[
S'=A_f^{-1}SA_s,\qquad D'=A_t^{-1}DA_f,
\]

so \(D'S'=A_t^{-1}K A_s\). Under an orthonormal basis change, all three changes are orthogonal.

There is also an algebraic GL gauge freedom, distinct from a metric-preserving basis change. For any invertible \(R\in GL(q)\),

\[
S_R=RS,\qquad D_R=DR^{-1},\qquad D_RS_R=DS.
\tag{M1.6}
\]

The factors are not separately identifiable from the composite map without additional interface semantics, constraints or observations. The composite rank satisfies

\[
\operatorname{rank}(DS)\leq
\min\{\operatorname{rank}(D),\operatorname{rank}(S),q\}.
\tag{M1.7}
\]

### 2.5 Rank, nullity and information loss

For \(K:\mathbb R^{d_s}\to\mathbb R^{d_t}\) with rank \(r\),

\[
\dim\ker K=d_s-r,\qquad
\dim\operatorname{im}K=r,\qquad
\operatorname{codim}(\operatorname{im}K)=d_t-r.
\]

Therefore \(K\) is injective iff \(r=d_s\), and surjective iff \(r=d_t\). If \(d_s>d_t\), injectivity is impossible; if \(d_s<d_t\), surjectivity is impossible. A rank-deficient route discards source directions and cannot be inverted on the full source space. These are exact linear-algebraic statements, not a complete information-theoretic account of noisy or nonlinear representations.

### 2.6 Grassmannian subspaces

An element of \(\operatorname{Gr}(k,n)\) is represented by an orthonormal frame \(U\in\mathbb R^{n\times k}\), \(U^\top U=I_k\), or by its projector \(P=UU^\top\). A different orthonormal frame for the same subspace is \(UR\) for \(R\in O(k)\).

For two equal-rank subspaces with frames \(U,V\), principal angles satisfy

\[
\cos\theta_i=\sigma_i(U^\top V),\qquad
0\leq\theta_i\leq\frac{\pi}{2},
\]

and the canonical geodesic distance is

\[
d_{\rm Gr}(U,V)=\left(\sum_i\theta_i^2\right)^{1/2}.
\tag{M1.8}
\]

For a common ambient orthogonal basis change \(Q\), and independent changes of frame \(R,S\in O(k)\),

\[
U'=Q^\top UR,\qquad V'=Q^\top VS.
\]

The principal angles and geodesic distance are unchanged, and the projector transforms by conjugation:

\[
P'=Q^\top P Q.
\tag{M1.9}
\]

The two subspaces being compared must live in the same ambient inner-product space and have equal rank. A Grassmannian signature does not encode operator magnitude, and a subspace match alone does not establish relational identity.

## 3. Propositions and proof obligations

**Proposition 1 — route coordinate covariance.** Equations (M1.1) and (M1.2) preserve the abstract input-output mapping.

*Proof.* Substitute \(x_{\rm old}=A_sx_{\rm new}\) into \(y_{\rm old}=K_{\rm old}x_{\rm old}\), then use \(y_{\rm new}=A_t^{-1}y_{\rm old}\). For orthogonal \(A_s=Q_s,A_t=Q_t\), \(Q_t^{-1}=Q_t^\top\). \(\square\)

**Proposition 2 — metric singular-spectrum invariance.** The singular values in (M1.4) are unchanged when the coordinates and metrics are transformed by (M1.2)–(M1.3).

*Proof.* Let \(C_s,C_t\) whiten the old metrics and \(C'_s,C'_t\) whiten the transformed metrics. The matrices \(O_s=C_sA_s(C'_s)^{-1}\) and \(O_t=C_tA_t(C'_t)^{-1}\) are orthogonal because their Gram matrices are identity. Then
\[
C'_tK_{\rm new}(C'_s)^{-1}
=O_t^\top(C_tK_{\rm old}C_s^{-1})O_s.
\]
Left/right orthogonal multiplication preserves singular values. \(\square\)

**Proposition 3 — composition covariance.** The chain composite transforms as (M1.5).

*Proof.* Substitute each transformed edge into \(K'_n\cdots K'_1\); adjacent factors \(Q_iQ_i^\top=I\) cancel. \(\square\)

**Proposition 4 — factorisation gauge and rank bound.** (M1.6) preserves the composite map; (M1.7) bounds its rank.

*Proof.* \(D_R S_R=DR^{-1}RS=DS\). The image of \(DS\) is contained in the image of \(D\), and its rank cannot exceed the rank of \(S\) or the intermediate dimension \(q\). \(\square\)

**Proposition 5 — linear information dimensions.** Rank-nullity gives the kernel and image dimensions and the injective/surjective criteria above. Invertible coordinate changes preserve rank.

*Proof.* Standard rank-nullity; multiplication by invertible matrices does not change rank. \(\square\)

**Proposition 6 — Grassmannian invariance.** The principal angles, geodesic distance and projector properties are invariant as specified in (M1.8)–(M1.9).

*Proof.* \((U')^\top V'=R^\top U^\top QQ^\top V S=R^\top(U^\top V)S\). Left/right orthogonal factors preserve singular values. Also \(U'(U')^\top=Q^\top UU^\top Q\), which preserves symmetry, idempotence and rank. \(\square\)

## 4. Frozen M1 verification cases

All cases use deterministic NumPy PCG64 generators with case-specific seeds 1101–1106. Numerical comparisons use float64 and the case-specific maximum absolute error tolerances below. The cases are independent and may execute concurrently.

| Case | Scope | Frozen check |
|---|---|---|
| M1-A | Orthonormal basis covariance | Independently rotate a \(3\to6\) route; compare routed outputs, Frobenius norm and singular spectrum; tolerance \(2\times10^{-10}\) |
| M1-B | General coordinate covariance | Transform a \(3\to5\) route and both SPD metric tensors under non-orthogonal invertible changes; compare route coordinates, source/target norms and metric singular spectrum; tolerance \(2\times10^{-9}\) |
| M1-C | Heterogeneous chain composition | Transform every link in a \(2\to4\to3\to5\) chain independently; compare composed operator and route output; tolerance \(2\times10^{-10}\) |
| M1-D | Interface gauge | Apply a non-orthogonal GL(4) gauge to a \(2\to4\to5\) encoder/decoder factorisation; verify composite, routed output, three-space basis covariance and rank bound; tolerance \(2\times10^{-10}\) |
| M1-E | Rank/information diagnostics | Check a full-column-rank embedding, full-row-rank projection, rank-limited interface map, rank-nullity and orthogonal-basis rank invariance |
| M1-F | Grassmannian invariance | Check principal angles, geodesic distance, orthonormal frames, and projector conjugation for two 3-planes in \(\mathbb R^8\); tolerance \(2\times10^{-10}\) |

The runner emits one JSON result per case. The aggregate gate requires exactly one passing artifact for each of M1-A through M1-F. The complete repository test suite runs independently on Python 3.10 and 3.12.

## 5. Acceptance and interpretation

M1 passes only if every analytical case and the aggregate gate pass, and the full repository tests pass on both Python versions. Invalid dimensions, singular coordinate changes, non-SPD metrics or non-orthogonal matrices supplied to isometry-only operations must fail explicitly.

An M1 pass establishes implementation agreement with these algebraic invariance properties. It does not demonstrate that learned relational operators are accurate, that representations are semantically aligned, that a learned interface has a unique meaning, or that a dynamically coupled adaptive network is stable. Those require separate hypotheses and experiments.

## 6. Next proof obligations

M1 does not close the following problems:

1. stability and conditioning under long multi-route composition, including path multiplicity and cancellation;
2. operator estimation under noisy, correlated and partially observed source states;
3. identifiability of latent interface factors under explicit interface constraints;
4. non-Euclidean or indefinite state geometries, if scientifically justified;
5. temporal adaptation of \(K_e\), together with metric-compatible regularisation;
6. higher-order relational objects and the role of geometry beyond pairwise subspace signatures.
