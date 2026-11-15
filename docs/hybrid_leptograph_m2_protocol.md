# HLG-M2 — Multi-Route Stability, Conditioning and Information Preservation

**Protocol version:** v0.1  
**Status:** frozen for implementation and deterministic analytical verification  
**Date:** 2026-11-15  
**Depends on:** HLG-M0 and HLG-M1  
**Scope:** fixed finite-dimensional linear operators; no operator learning or online adaptation

## 1. Question

When a source can reach a target through multiple heterogeneous routes, when does route multiplicity preserve information, when does coalescence create cancellation or ill-conditioning, and what conditions govern stability once routes close into feedback loops?

M2 moves from the single-map invariants of M1 to fixed multi-route networks. It does not introduce a learning law, relation discovery, semantic interpretation, or an adaptive topology.

## 2. Frozen mathematical model

Let node i have state x_i(k) in R^{d_i}. A synchronous fixed linear network is

\[
x_j(k+1)=\sum_i K_{ji}x_i(k)+u_j(k),
\]

where each K_{ji}: R^{d_i} -> R^{d_j} is dimension-compatible. Under the direct-sum state x=(x_1,...,x_n), this is

\[
x(k+1)=\mathcal A x(k)+u(k),
\qquad \mathcal A_{ji}=K_{ji}.
\]

Parallel edges between the same ordered pair add in the corresponding block. This synchronous block model is the only network timing convention in M2; delays and asynchronous updates are out of scope.

For a directed path p=(i_0,...,i_m), its transfer is

\[
K_p=K_{i_m i_{m-1}}\cdots K_{i_2i_1}K_{i_1i_0}.
\]

For several paths with common source and target spaces, two different observation semantics must not be conflated:

- **Coalesced output:** T=sum_p K_p. The path contributions add before measurement and may cancel.
- **Separately observed outputs:** O is the vertical stack of the path maps. Each route remains a distinct output channel in a direct-sum codomain. Its nullspace is the intersection of the route nullspaces; it can preserve information lost by summing.

The operator coherence ratio is

\[
c=\frac{\left\|\sum_pK_p\right\|_2}{\sum_p\|K_p\|_2},
\qquad 0\le c\le1,
\]

with cancellation fraction 1-c. It is a deterministic operator-level diagnostic, not a probability, information-theoretic mutual information, or semantic measure.

For a fixed discrete-time finite-dimensional LTI network, asymptotic stability is equivalent to

\[
\rho(\mathcal A)<1.
\]

The sufficient contraction condition \|\mathcal A\|_2<1 implies stability but is not necessary. A non-normal matrix may satisfy \rho(\mathcal A)<1 while exhibiting finite-horizon transient amplification. M2 therefore reports spectral radius and stability margin separately from induced norm and finite-horizon power norms.

For a full-column-rank linear observation operator O, its minimum singular value and condition number quantify worst-case linear sensitivity in the declared Euclidean coordinates. M1's metric-aware definitions remain the route for general coordinate systems; M2's deterministic cases use explicitly stated orthonormal / Euclidean coordinates only. No claim of Shannon information or noisy-channel capacity is made.

## 3. API and proof obligations

The implementation provides:
- path composition in traversal order;
- summation and vertical stacking of parallel route maps, with shape validation;
- operator-level multi-route coherence/cancellation and separate-versus-coalesced rank diagnostics;
- route-erasure diagnostics on the stacked observation operator;
- heterogeneous block-network assembly with explicit node dimensions and target/source block placement;
- feedback diagnostics including spectral radius, stability margin, induced 2-norm, finite-horizon power norms and peak transient gain.

Proof/implementation obligations:
1. Every edge K_{ji} has shape d_j × d_i.
2. Every coalesced route set has a common source and target space.
3. Stacked routes share a source space; their target spaces form a direct sum.
4. A single-route erasure test removes one row block at a time and recomputes rank/nullity and nonzero-spectrum conditioning.
5. For the declared fixed discrete-time LTI model, asymptotic stability is determined by rho(A)<1, not by a one-step norm threshold.
6. The finite-horizon transient statistic is descriptive over the fixed horizon only; it is not a substitute for the spectral stability criterion.

## 4. Frozen independent cases

| Case | Fixed question | Required outcome |
|---|---|---|
| M2-A | Multiple 3×2 paths partly reinforce and partly cancel before coalescence | Coherence and cancellation lie strictly between 0 and 1; aggregate retains rank 2 |
| M2-B | Two exact opposite 3×3 route maps are summed or retained separately | Sum has rank 0; stacked observation has rank 3 and nullity 0 |
| M2-C | A 3D route cascade compounds conditioning | Composite condition is bounded by the product of component conditions and remains full rank |
| M2-D | A non-normal 2×2 feedback transition has eigenvalues 0.8 | Spectral test says stable, induced norm is not contractive, and finite-horizon transient gain exceeds 1 |
| M2-E | A heterogeneous 2→3→2 block network with local retention and a directed cycle | Assembled 7×7 global operator has spectral radius below 0.5 and is asymptotically stable |
| M2-F | Three separate 3×2 observation routes are considered under any one route erasure | Baseline and every single-erasure bank retain source rank 2 with zero nullity |

Cases use fixed literal matrices and deterministic computations (no fitted parameters, random search, or hidden data). The runner writes one JSON result per case. CI executes all six cases independently, verifies the complete evidence set in an aggregate job, and runs the full test suite on Python 3.10 and 3.12.

## 5. Numerical and acceptance policy

- Float64 arithmetic throughout.
- Exact structural dimensions/rank/nullity are asserted for the frozen integer/simple-decimal reference matrices.
- Floating comparisons use 2e-12 absolute tolerance where an explicit comparison is needed; the implementation tests use 1e-10 or tighter where stated by NumPy test helpers.
- Every result JSON records the experiment ID, schema version, case ID and pass/fail state; non-finite JSON values are prohibited.
- A missing, malformed, duplicated, or failing case artifact fails aggregate verification.

## 6. Interpretation ceiling and exclusions

A pass validates the implemented fixed-matrix algebra, diagnostics, and reference cases only. It does not establish:
- stability of an adaptive, time-varying, delayed, nonlinear, stochastic or data-driven network;
- boundedness of every internal trajectory under arbitrary inputs;
- robustness to parameter uncertainty or unmodelled states;
- information-theoretic capacity, signal-to-noise performance or semantic information retention;
- that keeping routes separate is computationally or physically available in a target architecture;
- relation discovery, causal correctness, identity, learning, topology formation, or task performance.

No M1 result is altered. LG-01A/LG-01B frozen protocols and results remain untouched, LG-01C remains gated by its own entry criteria, and E03 remains the next mainline E-series milestone.
