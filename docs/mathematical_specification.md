# Mathematical specification — v0.1

## 1. Observable and event state

The observable state is \(X_n\in\mathcal X\). A relational event is

\[
e_n=(s_n,r_n,o_n,\tau_n),
\]

where subject \(s_n\), typed relation \(r_n\), object \(o_n\), and event time \(\tau_n\) are explicit.

A relational feature map is proposed as

\[
r_n=\phi(\mathcal R_n)\in\mathbb R^{16}.
\]

E00 does not prescribe or learn \(\phi\); the initial relation engine remains symbolic and interpretable.

## 2. Fixed SOE memory

For four channels, let \(\chi_{\ell,n}\in\mathbb R^{16}\), with initial fixed decay rates

\[
\gamma=(0.01,0.05,0.2,0.8)
\]

in normalized time units. On elapsed time \(\Delta t\geq0\), the update is

\[
\chi_{\ell,n+1}=e^{-\gamma_\ell\Delta t}\chi_{\ell,n}+B_\ell x_{n+1},
\]

where \(x_{n+1}\in\mathbb R^{16}\) is the supplied event feature and \(B_\ell\) is a fixed injection matrix (identity by default in E00). A channel therefore decays continuously over a time gap and receives the new event feature. The implementation stores channel states, not a kernel fit.

The rates are initial experimental values, not optimal or universal constants. The four-channel bank is a fixed approximation family; E00 checks its arithmetic and state handling.

## 3. Relational structure

A relation is an explicit directed typed tuple with event time and optional expiry. Composition and reversal require explicit schema rules; they are not inferred from arbitrary predicate strings. Contradictions are checked only for predicates declared functional in the schema (for example, one current \`located_at\` value per subject). Revision appends a new event and records which earlier event it supersedes; historical events are retained.

## 4. Grassmannian state

The initial point is in

\[
\operatorname{Gr}(4,\mathbb R^{16}),
\]

represented by an orthonormal frame \(Q\in\mathbb R^{16\times4}\), \(Q^\top Q=I_4\), or its projector

\[
P=QQ^\top.
\]

The projector must satisfy

\[
P^\top=P,\qquad P^2=P,\qquad \operatorname{rank}(P)=4.
\]

Principal angles are obtained from the singular values of \(Q_1^\top Q_2\), clamped to \([0,1]\) against floating-point drift. The canonical geodesic distance is the Euclidean norm of the principal-angle vector.

For a skew-symmetric generator \(\Omega^\top=-\Omega\), a candidate update is

\[
Q_{n+1}=\exp(\eta\Omega)Q_n,
\qquad P_{n+1}=\exp(\eta\Omega)P_n\exp(-\eta\Omega).
\]

The implementation uses a matrix exponential and re-orthonormalizes only to control numerical drift. This operation preserves the subspace dimension. E00 verifies the invariants; it does not claim that a particular \(\Omega\) is a scientifically appropriate coupling law.

## 5. Transition probabilities

For a finite set of next states, a transition interface returns

\[
\hat p_n=(\hat p_1,\ldots,\hat p_m),\quad
\hat p_i\geq0,\quad \sum_i\hat p_i=1.
\]

E00 validates probability construction and edge cases. Predictive performance belongs to E01 onward.

## 6. Markov/history distinction

The scientific question is whether

\[
P(X_{n+1}\mid X_n)\ne P(X_{n+1}\mid X_{0:n})
\]

for a suitable controlled process. This is an experimental proposition, not an assumption encoded in the primitives. Even if an augmented state is sufficient to make a process Markovian, that does not make the observable process first-order Markovian.


## 7. Augmented-state persistence

The E00 interoperability boundary is represented by `ResearchState`:

\[
Z_n=(X_n,\mathcal M_n,\mathcal R_n,P_n).
\]

It holds the JSON-compatible observable state, the SOE channel bank, the append-only relational event store plus its declared schema, and the Grassmannian frame. A versioned JSON snapshot can be reconstructed and must preserve each component and the next SOE trajectory. This is a persistence/interface contract only; it does not define a coupling update or imply that the augmented state is empirically sufficient.
