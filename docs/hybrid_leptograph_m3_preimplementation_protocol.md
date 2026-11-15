# HLG-M3 pre-implementation campaign — relational memory and adaptation

**Protocol:** HLG-M3-PREFLIGHT-v0.1  
**Status:** pre-implementation investigation; not an implementation authorisation  
**Date:** 2026-11-15  
**Prerequisites:** HLG-M0, HLG-M1 and HLG-M2 completed  
**Architecture policy:** incremental extension of the existing heterogeneous vector-space framework

## 1. Research question

Can the existing hybrid relational Leptograph acquire, retain, retrieve and revise relationship-specific historical information, and use that history to adapt heterogeneous routing in a bounded and useful way?

M3 is the first adaptive-learning investigation in this Leptograph line. A successful mathematical or numerical preflight does not by itself establish relation discovery, causal correctness, semantic memory, general learning or task generalisation.

The preflight deliberately reuses the provisional M0 relational-history and routing equations. It does not create a second competing memory model and does not add a production M3 API.

## 2. Existing foundation and provisional equations

The established architecture is retained:

- modes within a group share a local finite-dimensional inner-product space \(\mathcal E_g\);
- different groups may have different dimensions;
- directed relationships use dimension-compatible operators \(K_e:\mathcal E_g\to\mathcal E_h\);
- reverse relationships are independent;
- mode-level temporal memory and relationship-level history are distinct state variables.

For an edge \(e\), the provisional relationship-history state is \(H_e(t)\). New evidence is represented by an externally supplied scalar \(s_e(t)\). The provisional memory law is

\[
\dot H_e(t)=\lambda_e\big(s_e(t)-H_e(t)\big),
\qquad \lambda_e>0.
\tag{M3.1}
\]

The admissible signal and state range for this preflight is

\[
0\le s_e(t)\le1,\qquad 0\le H_e(0)\le1.
\tag{M3.2}
\]

Under these assumptions, the interval \([0,1]\) is invariant. The solution for measurable bounded evidence is

\[
H_e(t)=e^{-\lambda_e(t-t_0)}H_e(t_0)
+\lambda_e\int_{t_0}^{t}e^{-\lambda_e(t-\tau)}s_e(\tau)\,d\tau.
\tag{M3.3}
\]

For a constant evidence value \(s\),

\[
H_e(t)=s+\big(H_e(t_0)-s\big)e^{-\lambda_e(t-t_0)}.
\tag{M3.4}
\]

The provisional routing update already introduced in the M0 foundation is

\[
\dot K_e(t)=
\eta_e H_e(t)s_e(t)\big(\widehat K_e(t)-K_e(t)\big)
-\delta_e\big(1-s_e(t)\big)K_e(t),
\tag{M3.5}
\]

where \(\eta_e,\delta_e>0\) and \(\widehat K_e(t)\) is the supported target/reference operator. The target is not assumed to be known to a deployed learner: how it is estimated from non-circular evidence is an open scientific question. The preflight treats it as an externally supplied reference so that the update law can be isolated.

The evidence signal must not be silently defined from the same route output that it is supposed to validate. Evidence construction, confidence calibration and resistance to self-reinforcing false relations remain open design obligations.

M3 does not add a separate scalar \(W_e\) that duplicates the strength already represented by the adaptive operator \(K_e\). Nor does it silently assume that context or confidence already has a valid update law. Identity, context and confidence remain distinct design roles until their operational definitions are justified.

## 3. Boundedness proposition for the provisional route law

Let \(\|\cdot\|\) be a matrix norm. Suppose, for all \(t\),

\[
0\le H_e(t),s_e(t)\le1,\qquad
\|\widehat K_e(t)\|\le R,
\qquad
\|K_e(t_0)\|\le R.
\tag{M3.6}
\]

Set \(a(t)=\eta_eH_e(t)s_e(t)\ge0\) and \(b(t)=\delta_e(1-s_e(t))\ge0\). Equation (M3.5) becomes

\[
\dot K_e=a(t)\widehat K_e-(a(t)+b(t))K_e.
\]

At the boundary \(\|K_e\|=R\), the upper right directional derivative satisfies

\[
D^+\|K_e\|
\le a(t)\|\widehat K_e\|-(a(t)+b(t))\|K_e\|
\le -b(t)R\le0.
\tag{M3.7}
\]

Thus the closed norm ball \(\{K:\|K\|\le R\}\) is forward invariant under the stated assumptions. This is a boundedness result for an individual edge operator with a bounded target. It is **not** a stability theorem for a network whose block operator changes over time, and it is not a proof that the unknown target estimator is bounded.

## 4. Scope and hypotheses

| Case | Hypothesis / question | Preflight method |
|---|---|---|
| M3-A | Relationship history follows the specified low-pass evidence law and remains in its admissible interval | Piecewise-constant evidence; exact segment solution versus independent DOP853 integration |
| M3-B | History and route dormancy have distinct, independently selectable decay timescales | Closed-form half-life checks and parameter sweep |
| M3-C | Context-conditioned retrieval can distinguish separated contexts and exposes ambiguity for near-duplicates | Explicitly provisional similarity-kernel diagnostic; report margins and ambiguity |
| M3-D | Bounded history, evidence and target operators keep the adaptive edge operator in a declared norm ball | Switched bounded-target numerical probe plus the analytic invariant-ball argument |
| M3-E | Separate mode/relationship memory can be compared fairly with unified memory | Readiness audit; do not run a winner comparison until the unified control and equal-resource budget are specified |
| M3-F | Residual relationship history can assist reacquisition after a dormant interval | Small acquire–dormant–reactivate task against a reset-history control |
| M3-G | A per-instant spectral-radius check is insufficient for arbitrary switching | Explicit counterexample with individually Schur matrices and an unstable two-step product |

M3-G is an adversarial mathematical boundary check, not a claim that the proposed M3 law necessarily generates arbitrary switching.

## 5. Case-specific definitions and metrics

### M3-A — historical accumulation

Use the same scalar evidence law as (M3.1) with a predeclared sequence of constant evidence segments. Compute each segment from (M3.4), then compare against segmentwise high-accuracy DOP853 integration. Report maximum absolute discrepancy, minimum and maximum history, and monotonic movement toward the segment's evidence value.

Acceptance checks numerical consistency and interval invariance for these inputs only. It does not validate how \(s_e\) is generated.

### M3-B — persistence and decay

During zero evidence,

\[
H_e(t)=H_e(0)e^{-\lambda_e t},\qquad
K_e(t)=K_e(0)e^{-\delta_e t}
\]

for the dormant route equation. The corresponding half-lives are

\[
t_{1/2,H}=\frac{\ln2}{\lambda_e},\qquad
t_{1/2,K}=\frac{\ln2}{\delta_e}.
\]

The two rates must remain distinct parameters. No fixed ratio between them is assumed. The case checks exact half-life values, monotonic decay and the selected numerical examples.

### M3-C — contextual retrieval

A candidate diagnostic uses a bank of context-labelled history traces and the score

\[
S_e(c\,|\,c_i)=H_{e,c_i}
\exp\left(-\frac{\|c-c_i\|^2}{2\sigma^2}\right).
\tag{M3.8}
\]

This kernel is only a probe. It is not a frozen Leptograph retrieval rule. The case contrasts widely separated context vectors with near-duplicate context vectors and reports score margins.

A successful diagnostic means that the expected clean discrimination and ambiguity are both observed. It does not establish a suitable context representation, calibrated confidence, robust rejection threshold or correct identity matching. An abstain/reject policy must be designed before context retrieval can be considered implementation-ready.

### M3-D — adaptive routing boundedness

Use (M3.5) with bounded piecewise-constant target operators and evidence values in \([0,1]\). Record the maximum spectral norm of \(K_e(t)\), the history range, target norms and integration checks. The numerical trajectory is a challenge to the declared conditions, not a replacement for proposition (M3.7).

The test does not imply that the assembled global network is stable. M2's fixed-LTI spectral-radius criterion does not transfer automatically to a time-varying product.

### M3-E — memory architecture controls

This case is deliberately a design gate, not a performance run. Before comparing no memory, mode memory, relationship memory, separate memory and unified memory, specify:

1. an operational update law for the unified-memory control;
2. an equal state-dimension, precision and update-compute budget;
3. a shared task distribution and observation protocol;
4. a memory-interference metric that is not selected after seeing the outputs;
5. how mode memory and relationship history are addressed and read.

If these are absent, report the comparison as blocked. Do not infer that separate memory is better merely because it has separate registers or a larger effective capacity.

### M3-F — sequential reacquisition

Use a deterministic scalar reference task with three phases: acquire a target route, remove evidence and enter dormancy, then reactivate the same target. Compare the retained-history trajectory against a control that resets history at the start of reacquisition. Report final route error and relative error reduction.

The claim ceiling is narrow: residual history may speed reacquisition under this specific rule and task. No relation discovery, context transfer, compositional generalisation or general learning claim follows.

### M3-G — switched stability counterexample

Use

\[
A_1=\begin{bmatrix}0.8&1\\0&0.8\end{bmatrix},
\qquad
A_2=\begin{bmatrix}0.8&0\\1&0.8\end{bmatrix}.
\]

Both have spectral radius \(0.8\), while the alternating two-step product \(A_2A_1\) has spectral radius greater than one. This establishes that checking \(\rho(A_k)<1\) separately at each step is not a general stability proof for arbitrary switching. A stronger network claim would require an appropriate common Lyapunov argument, joint spectral-radius bound, dwell-time restriction or other explicit switching assumptions.

## 6. Parallel execution and evidence contract

Seven independent cases run as separate GitHub Actions matrix jobs. A separate aggregate job waits for the case jobs and both supported full-suite test jobs. Each case writes one JSON file containing experiment ID, schema version, case ID, declared metrics, interpretation and execution status. The aggregate requires exactly M3-A through M3-G.

A case may execute successfully while recording a scientific design blocker. In particular, M3-E is expected to execute its readiness audit and return BLOCKED_PENDING_CONTROL_DEFINITION. Therefore distinguish:

- **CI execution success:** all specified preflight jobs ran and the evidence set is complete;
- **scientific readiness:** all required design questions are actually specified and supported.

The aggregate is expected to report all jobs executed but M3 implementation readiness false while M3-E remains blocked. A green workflow is not an implementation authorisation.

## 7. Numerical policy

- Float64 arithmetic for all reference calculations.
- DOP853 comparison uses relative tolerance \(10^{-12}\) and absolute tolerance \(10^{-13}\).
- The preflight's declared maximum absolute comparison tolerance is \(2\times10^{-10}\), unless a stricter closed-form identity is checked.
- All output values must be finite; JSON serialization rejects NaN and infinity.
- Every case has a deterministic input schedule; random sampling is not used in v0.1.
- Case outputs are independent artifacts. The aggregate rejects missing, duplicate, malformed, wrong-identity or non-executed case evidence.

## 8. Interpretation ceiling and exclusions

Even if every executable case passes, this preflight does not establish:

- that evidence \(s_e\) can be inferred reliably from real interaction;
- that \(\widehat K_e\) can be estimated without circularity or bias;
- that context or relationship identity is represented adequately;
- that confidence is calibrated;
- that separate memory beats a capacity-matched unified memory;
- that M3 performs open-ended relation discovery or causal inference;
- that the full coupled network is stable under arbitrary adaptation, switching, delay or nonlinear interactions;
- that the framework improves general learning or transfer over conventional vector, graph or temporal-memory baselines.

M3 production implementation remains gated on analysis of this campaign, resolution of the M3-E comparison contract, a specified retrieval/abstention rule, and an agreed task protocol. M4 retains the broader coupled adaptive-stability investigation.
