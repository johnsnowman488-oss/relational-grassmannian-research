

## 11. M1 — heterogeneous routing and geometric invariance

M1 formalises how a directed route \(K_e:\mathcal E_s\to\mathcal E_t\) is represented under independent basis changes in heterogeneous source and target spaces. Under orthonormal basis changes, \(K'=Q_t^\top KQ_s\); route outputs are covariant while Euclidean norms, rank and singular values are invariant. Under arbitrary invertible coordinate changes, \(K'=A_t^{-1}KA_s\), and the inner-product Gram matrices must be transported as \(G'_s=A_s^\top G_sA_s\) and \(G'_t=A_t^\top G_tA_t\). Metric-aware singular values are invariant; ordinary Euclidean singular values need not be.

M1 also establishes covariance of heterogeneous route-chain composition, GL gauge non-identifiability of interface factorisations, rank-nullity/injectivity/surjectivity diagnostics, interface-rank bounds, and Grassmannian principal-angle/projector invariance. The full frozen protocol, proofs and six verification cases are in [hybrid_leptograph_m1_protocol.md](hybrid_leptograph_m1_protocol.md). This milestone treats routing operators as fixed maps and does not establish learning, semantic alignment, causal validity or full adaptive-network stability.


## HLG-M2 — Multi-Route Stability, Conditioning and Information Preservation

M2 extends M1 from individual heterogeneous maps to fixed route banks and synchronous feedback networks. It distinguishes coalesced route summation from separate route observation: summing path operators can create destructive cancellation, while a vertically stacked observation can retain source information. It also measures route-erasure resilience, conditioning in cascades, and the spectral stability and transient amplification of a global heterogeneous block operator.

The frozen definitions and six reference cases are in [the M2 protocol](hybrid_leptograph_m2_protocol.md). Canonical run [43741891066](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43741891066) passed all six cases, aggregate verification and the full 198-test repository suites on Python 3.10 and 3.12.

M2's claim ceiling is fixed-matrix algebra and synchronous finite-dimensional LTI verification. It does not establish the stability of adaptive, delayed, nonlinear, stochastic or learned networks, nor semantic or information-theoretic retention. The case metrics and artifact hashes are recorded in the relational adaptation ledger.
