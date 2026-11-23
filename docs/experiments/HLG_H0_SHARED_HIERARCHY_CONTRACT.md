# H0 — Shared HLA/HLB Hierarchy Contract and SOE Representation Bridge

**Status:** Proposed implementation contract v0.1.0.

## Purpose

H0 defines the common numerical/event interface for HLA and HLB and resolves the mismatch between Leptograph's vector-valued SOE trace bank and the native hierarchy's per-level u/chi state. It does not modify the flat M4 A/B reference systems or the C++ ABI.

## Shared three-level topology

| Index | Role | Responsibility |
|---:|---|---|
| 0 | Grounding | Ingest typed observations and produce event-level features |
| 1 | Relational abstraction | Integrate lower-level evidence and produce intermediate features |
| 2 | Context and control | Maintain longer-horizon context and produce top-down control |

Matched HLA/HLB runs use identical level count, ordering, state dimensions, timestep, native kernels, edge topology and synchronisation. Architecture-owned state is measured separately.

## Architecture boundary

**HLA:** SOE temporal memory and learned readouts; no persistent relation-instance store at intermediate or context/control levels. Exact path claims still require current evidence and the shared witness validator. Missing evidence means abstention or a separately typed abstract prediction, never a fabricated witness.

**HLB:** the same SOE substrate plus one bounded canonical persistent typed relation-instance store, exposed through level-scoped indexes rather than duplicated per-level copies. Derived relations preserve witness references. Capacity exhaustion is explicit abstention; there is no silent eviction. Records are filtered by observation cutoff, event time, validity and context.

The native runtime is architecture-neutral. HLA/HLB policy remains in Python.

## Time and synchronisation

Each event carries event_time (when it occurred) and observed_at (when received). Queries carry query_time and observation_cutoff. A record is eligible only if it is observed by the cutoff, occurred by query_time, is valid at query_time and has compatible context.

The first hierarchy uses one fixed common dt across native levels. Each global cycle advances every SOE bank and the native hierarchy by exactly one dt. A gap of k ticks is k explicit silent cycles. Late arrivals are ingested at observation time and do not rewrite past native states.

**Synchronisation invariant:** calculate every level's feedback before the native step from the same pre-step snapshot and current event batch. Call runtime.step(feedback_by_level) exactly once. Never step levels sequentially or let a later level see partially updated state.

## SOE representation bridge

Leptograph SOE channels have shape (L, D), where L is channel count and D is feature dimension. Each channel decays and receives its own injection-matrix transform. The native custom-chain level instead has vector u, scalar-per-kernel-channel chi, and its own kernel dynamics. These are not the same state equations: native chi is not the SOE matrix, and native u is not the SOE trace bank.

H0 defines a lossless row-major embedding:

- Native u dimension = L * D.
- u[l * D + j] = SOE channels[l, j].
- Decoding reshapes u back to (L, D).

This encoding/decoding is lossless. **Native evolution after initialisation is not equivalent to a Python SOE update.** The native hierarchy applies its own configured dynamics, coupling and kernel feedback. Therefore:
1. The exact SOE embedding is the external feedback representation for each cycle.
2. A reshaped native u is a native evolved feature view, not the original SOE state.
3. Python SOE banks remain architecture-owned and are included in composite checkpoints.
4. Native chi, active kernels and spectral diagnostics remain native-owned and are included in native checkpoints.

Initial native level specs use flattened SOE state for u, zero chi with length equal to native kernel channel count, and gamma/w supplied by the frozen native config. No implicit truncation, averaging, broadcasting or padding is allowed.

## Feedback cycle

For each global cycle:
1. Validate every level index, feature dimension and finite value before mutating any bank.
2. For a supplied event feature, call SOEMemory.update(feature, dt); otherwise call SOEMemory.advance(dt).
3. Flatten each channel matrix row-major.
4. Submit all addressed vectors in one native step.
5. Return the native snapshot and per-level reshaped native-u views.

An empty event map is a silent cycle. H0 submits SOE embeddings only. Additional learned top-down control must be combined in an explicit, dimension-checked Python policy before the single native step; it is not implicitly mixed by this bridge.

## Native topology

Initial three-level chain:
- Bottom-up: 0 → 1 and 1 → 2.
- Top-down: 2 → 1 and 1 → 0.

HLA and HLB use identical edge directions, gains, normalisation and native dimensions in matched runs. Topology is frozen during a run.

## Composite checkpoint

A full architecture checkpoint contains native runtime checkpoint; all SOE configs and channel states; architecture identifier; hierarchy/bridge schema versions; event tick and dt; readout parameters and fingerprints; HLB relation records and witness references where applicable; controller/lifecycle and random-generator state when enabled. Native checkpoint alone is insufficient. Validate all component schemas and fingerprints before activating a restored session.

## H0 acceptance gates

- H0-01: versioned three-level contract and machine-readable topology.
- H0-02: exact SOE flatten/reshape across varied dimensions.
- H0-03: reject malformed dimensions, non-finite values, invalid indices and timestep mismatch before native mutation.
- H0-04: update all banks and invoke native runtime exactly once per cycle.
- H0-05: silent cycles decay every bank and advance native hierarchy once.
- H0-06: distinguish native evolved u from Python SOE state.
- H0-07: fake-runtime integration test verifies feedback and synchronisation.
- H0-08: both HLA and HLB consume the same bridge API.

## Non-claims

H0 does not establish numerical equivalence between Python SOE and native evolution, replacement of SOE by native hierarchy, optimality of three levels, superiority of HLA/HLB, or confirmatory task performance. H1 will test hierarchy contribution through level-count and coupling ablations.
