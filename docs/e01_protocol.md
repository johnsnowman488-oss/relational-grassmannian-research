# E01-A — Memory-only compositional inference

## Question

Can fixed-dimensional SOE traces preserve enough event-history information to support a two-relation compositional query, and how do they compare with current-event, finite-window, single-timescale, reset, shuffled-history, and full-history controls?

This is a memory-sufficiency experiment, not a novelty claim for SOE. D2C/Aberconics already contains delayed retrieval, temporal traces, and sequential slot-value association. E01-A targets the narrower boundary between scoring constituent event evidence and composing two relation supports from an SOE-only event trace.

## Task and representation

Each sequence contains up to four entities and two typed directed relations. The query asks whether there exists an intermediate entity b such that relation-0(subject,b) and relation-1(b,object) both occurred. Positive sequences contain a planted two-edge path; negative sequences are generated without one. Additional facts act as distractors; each sequence contains 9–12 facts so the eight-event window is not equivalent to full history. Event order is randomized and inter-event gaps are sampled from 0.5, 1, 4, 12, and 16 normalized units.

The encoder is fixed and non-learned. Each relation has a 16-vector codebook orthonormal within that relation. Relation-0 uses the standard basis; relation-1 uses a fixed seeded orthogonal basis. Memory receives only event vectors. At query time a common decoder scores candidate facts and composes supports over the four possible intermediate entities. No graph, path, or answer is inserted into memory. For SOE, candidate support is evaluated independently across channels and the maximum channel support is used; this is a declared readout rule, not an optimized parameter.

## Independent CI arms

| Arm | Definition |
|---|---|
| soe | Four fixed channels at rates 0.01, 0.05, 0.2, 0.8 |
| current | Most recent event only |
| window2 | Sum of last two event vectors |
| window8 | Sum of last eight event vectors |
| reset | No retained state at query time |
| slow_only | Single SOE rate 0.01 |
| fast_only | Single SOE rate 0.8 |
| shuffled | Same SOE channels after deterministic event-order permutation |
| full_history | Un-decayed sum of all event vectors; information-available reference, not capacity-matched |

All arms share validation and test seed ranges. Threshold selection uses validation only; test sequences use disjoint seeds. GitHub Actions runs all nine arms as independent matrix jobs with fail-fast disabled.

## Metrics and limits

Primary: held-out exact query accuracy and balanced accuracy. Also report Wilson 95% accuracy interval, raw bounded-support Brier score (descriptive only; not a calibrated probability), mean composition score by class, and the fraction of positive queries with nonzero composition support. This score diagnostic is not an independent constituent-fact retrieval probe and must not be described as proof that both facts were independently decoded.

Frozen configuration: feature dimension 16; four entities; composition depth two; validation/test 160/160; fixed SOE rates (0.01, 0.05, 0.2, 0.8); no learned encoder/readout, graph, geometry, or adaptive rate fitting.

The codebooks are a representational aid. This small task family does not establish broad relational reasoning. A low score across all arms may indicate an encoding/decoder limitation, not specifically an SOE limitation. A high full-history score with lower SOE score indicates loss from temporal weighting. E01-B capacity/interference sweeps follow only after this result is reviewed. No E02/E03 conclusion follows automatically.
