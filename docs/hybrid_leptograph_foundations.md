

## 11. M1 — heterogeneous routing and geometric invariance

M1 formalises how a directed route \(K_e:\mathcal E_s\to\mathcal E_t\) is represented under independent basis changes in heterogeneous source and target spaces. Under orthonormal basis changes, \(K'=Q_t^\top KQ_s\); route outputs are covariant while Euclidean norms, rank and singular values are invariant. Under arbitrary invertible coordinate changes, \(K'=A_t^{-1}KA_s\), and the inner-product Gram matrices must be transported as \(G'_s=A_s^\top G_sA_s\) and \(G'_t=A_t^\top G_tA_t\). Metric-aware singular values are invariant; ordinary Euclidean singular values need not be.

M1 also establishes covariance of heterogeneous route-chain composition, GL gauge non-identifiability of interface factorisations, rank-nullity/injectivity/surjectivity diagnostics, interface-rank bounds, and Grassmannian principal-angle/projector invariance. The full frozen protocol, proofs and six verification cases are in [hybrid_leptograph_m1_protocol.md](hybrid_leptograph_m1_protocol.md). This milestone treats routing operators as fixed maps and does not establish learning, semantic alignment, causal validity or full adaptive-network stability.
