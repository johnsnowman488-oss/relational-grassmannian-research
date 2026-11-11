# E01-B — Capacity and interference frontier

## Purpose

E01-B measures where memory-only relational support degrades as the candidate space, event history, distractor load, temporal gaps and composition depth increase. It follows A2 diagnostics and A3 replication; it does not assume that the full four-channel SOE bank is the preferred memory.

## Memory arms

| Arm | State size | Definition |
|---|---:|---|
| `slow_only` | 16 scalars | SOE with decay 0.01; primary SOE arm |
| `current` | 16 | Most recent event vector |
| `window2` | 16 | Sum of last two event vectors |
| `window8` | 16 | Sum of last eight event vectors |
| `full_history` | 16 | Un-decayed sum of all event vectors |
| `full_soe` | 64 | Four-channel SOE; larger-state diagnostic only |

The five 16-scalar arms form the primary capacity-matched comparison. The 64-scalar full SOE arm is retained to check whether additional timescales become useful under heavier interference; it is not treated as capacity-matched.

All arms use the same fixed event encoder and candidate-path decoder within a condition/world. Finite-window and full-history controls ignore elapsed gaps; SOE arms decay according to event `dt`.

## One-factor conditions

Each sweep varies one factor while holding the others at a declared reference:

| Sweep | Values | Fixed factors |
|---|---|---|
| Entity scale | 4, 8, 16, 32 entities | 8 distinct facts, 16 distractor pulses, depth 2, medium gaps |
| Distinct-fact load | 4, 8, 16, 32, 64 facts | 16 entities, 16 distractors, depth 2, medium gaps |
| Distractor load | 0, 4, 16, 32 pulses | 16 entities, 16 facts, depth 2, medium gaps |
| Temporal gaps | short, medium, long | 16 entities, 16 facts, 16 distractors, depth 2 |
| Composition depth | 1, 2, 3 hops | 16 entities, 16 facts, 16 distractors, medium gaps |

Gap profiles are short (0.25, 0.5, 1), medium (2, 4, 8), and long (16, 32, 64) normalized time units.

This is a one-factor frontier, not a full factorial design. It does not estimate interactions between factors; selected interaction corners can be added after the frontier is reviewed.

## Generator and codebook

Each sequence contains a fixed number of distinct typed facts plus a declared number of additional distractor event pulses. Distractor pulses repeat facts outside the planted positive path; they increase event-history load without changing the underlying fact set. Positive cases contain a planted path. Negative cases are generated so no path of the requested depth connects the query endpoints.

Relations alternate 0, 1, 0 across path depth. The decoder enumerates candidate intermediate entities and scores each path by the product of its edge supports.

Feature dimension is fixed at 16. At four entities, the codebook preserves the orthogonal A2 construction. Above four entities, each relation uses normalized random codewords in R^16 because E² distinct codewords cannot remain mutually orthogonal in a 16-dimensional space. This deliberately exposes codebook crowding as entity count grows. Therefore the entity-scale sweep tests both larger candidate spaces and fixed-dimensional codebook interference; it is not a pure search-complexity-only test.

## Replication and execution

- Two independent synthetic-world seeds: 401 and 402.
- 19 one-factor conditions × 6 memory arms × 2 worlds = **228 CI cells**.
- 160 validation and 160 held-out test sequences per cell.
- Same cases are shared across memory arms within a condition/world.
- Composition and constituent-fact thresholds are fitted on validation data only.
- Per-sequence query scores, predictions, best path, edge supports, event history and state size are retained.
- Each cell uploads an immutable JSON artifact. A final job aggregates both worlds and reports paired per-world differences against the slow-only SOE arm.

Two worlds provide a first frontier estimate, not strong population-level inference. The report will show each world separately and avoid presenting pooled sequence tests as independent-world evidence.

## Interpretation

The primary question is whether 16-dimensional slow-only SOE preserves useful history better than equally sized current, finite-window and full-history controls as each factor increases. The full four-channel SOE is a secondary 64-scalar reference.

A fall in constituent retrieval suggests representation/readout interference; good constituent retrieval with poor path accuracy points to composition/search difficulty. These outcomes must be separated.

## Gate

Review the complete 228-cell frontier before adding interaction sweeps or changing the memory architecture. Do not proceed to E02-style explicit relation structures or Grassmannian geometry on the basis of an unreviewed aggregate accuracy alone.
