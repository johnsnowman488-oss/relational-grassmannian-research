# Lepto-Graph Development Hypothesis (LGDH)

**Research stream:** LG — parallel mechanism investigation  
**Status:** Hypothesis recorded; LG-01A protocol specified; no LGDH results yet  
**Opened:** 2026-11-14  
**Parent research project:** Independent Relational Grassmannian Research

## 1. Motivation

The E01/E02 work distinguishes temporal event retention from relational organisation. E02 showed the value and limitations of an explicit graph derived from observed events, but an observed-edge graph is a retrieval structure, not evidence that a memory system can form its own relational organisation.

The LGDH investigates a different question:

> Can relational pathways emerge endogenously from the trajectories of rapidly decaying, continuously refreshed, multidimensional memory modes, with slower memory channels registering trajectory history and supplying context for subsequent routing?

This is a parallel mechanism hypothesis. It does not replace E03, which remains the next mainline representation-neutral task-suite milestone.

## 2. Working definition

A **lepto-mode** is provisionally defined as a rapidly decaying, multidimensional dynamical state that remains operational under a continuing flow of information. It is not primarily intended to store each item permanently. Its proposed role is to participate in the organisation and routing of information.

A **lepto-graph** is the directed relational organisation hypothesised to emerge among such modes through their dynamics and contextual interactions. A collection of fast SOE channels is not automatically a lepto-graph: directed destination selection and relation formation must be demonstrated separately.

The terminology is provisional until the mechanism is operationally defined and tested.

## 3. Central mechanism hypothesis

The intended cycle is:

**Trajectory → historical registration → contextual recognition → routing adaptation → new trajectory**

The three core operations are distinct:

1. **Intrinsic trajectory signal.** A mode's direction is derived from its own successive states. It is not assigned an edge direction by an external graph.
2. **Historical registration.** Slower modes retain selected trajectory signatures and relational context beyond the fast mode's short decay horizon.
3. **Contextual destination selection.** A fast mode combines its current state and trajectory-derived direction with retrieved slower context to choose or update a destination.

A useful first mathematical scaffold is:

\[
\dot z_i(t)=-\gamma_i z_i(t)+B_i u_i(t),
\]

where \(z_i(t)\in\mathbb R^d\) is a fast mode, \(\gamma_i>0\) its decay rate, and \(u_i(t)\) the incoming signal. A trajectory-derived tangent is

\[
d_i(t)=\frac{\dot z_i(t)}{\|\dot z_i(t)\|+\varepsilon}.
\]

A slow channel may register trajectory features:

\[
M_i(t)=\int_0^t K_i(t-s)\,
\Phi\!\left(z_i(s),d_i(s)\right)\,ds.
\]

A later routing rule could be written abstractly as

\[
r_i(t)=F\!\left(z_i(t),d_i(t),M_i(t),\mathcal C_i(t)\right),
\]

where \(\mathcal C_i(t)\) is the candidate-destination set. The map from a direction in one mode's state space to a destination mode is a central unknown; it is not solved by taking a derivative alone.

A candidate timescale ordering is

\[
\tau_{\rm route}\lesssim\tau_{\rm lepto}\ll\tau_{\rm slow}.
\]

This is a design hypothesis to measure, not an established constraint of the repository's current implementation.

## 4. What is and is not claimed

- A fast mode can be continually refreshed while each earlier input contribution decays. This is the narrow premise tested first.
- A trajectory tangent provides direction in the mode's own state space; it does not by itself choose another mode.
- Slower memory registration may provide history that makes destination selection context-sensitive; this remains untested.
- A directed graph must emerge from the routing and relation-formation mechanism. Supplying the target graph would invalidate an endogenous-emergence claim.
- A pathway that adapts is not automatically reasoning. Later claims require held-out relational prediction, retrieval, revision or transfer.
- Neurogenesis and synaptogenesis are biological inspirations for two separable computational hypotheses. No biological equivalence is claimed.
- The Relational Grassmannian is a possible later analysis/representation tool for families of relational subspaces. It is not required for LGDH, and subspace geometry alone does not encode directed arrows.

## 5. Relationship to the existing E01/E02 line

- **E01** examined fixed SOE memory and candidate-path retrieval/composition under controlled synthetic conditions.
- **E02** compared dense memory with an explicit observed-event graph and a graph-plus-temporal-memory hybrid, including controlled corruption.
- **LGDH** asks whether the temporal-memory substrate can develop directed relational pathways from its own dynamical trajectories.

LGDH must reuse the established E02 lessons about leakage, observation/evaluator separation, path witnesses, duplicate handling and cost accounting. It must not describe an LG mode as a graph simply because it has a state vector or a trajectory.

The exact E02 architecture and limitations are specified in the E02 protocol. Any later claim of an E02-style comparator must use that implementation/protocol or explicitly label the comparator as a new graph baseline.

## 6. Programme placement

LG is an explicitly parallel mechanism stream. E03 remains the next mainline experiment in the existing E-series. LG experiments do not silently reorder E03–E11 or establish a commitment to integrate lepto-graphs into the Grassmannian model.

See the LG experiment spine, LG-01A protocol, LGDH cross-experiment ledger and LG-01A experiment ledger.
