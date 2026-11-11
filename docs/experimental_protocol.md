# Experimental protocol

## General controls

- Use explicit configuration files and fixed, recorded random seeds.
- Split generated data by independent sequence, never by neighbouring transitions from the same sequence.
- Keep generator truth separate from model inputs and predictions.
- Report uncertainty and sample sizes; do not interpret one seed as decisive.
- Compare against baselines with matched access to information and adequate capacity.
- Preserve raw predictions, metrics, configurations, logs, and commit identifiers for each run.

## E00 — foundations

E00 is an implementation-validation milestone, not a predictive-performance experiment.

### E00-A: SOE memory

Check initialization, channel-wise decay, feature injection, differing rates, analytically predictable repeated updates, reset, snapshot, and serialization round trips.

### E00-B: symbolic relations

Check insertion, active/expired relation queries, rule-governed composition and reversal, revision history, and schema-scoped contradiction detection.

### E00-C: Grassmannian primitives

Check initialization, orthonormality, projector symmetry/idempotence/rank, principal angles, distance symmetry/non-negativity, and skew-generator updates.

### E00-D: transition interface

Check normalized finite probability vectors, score-to-probability conversion, labels, and invalid/empty inputs.

### Acceptance gate

E00 passes only when unit tests pass, geometric invariants are within tolerance, fixed-seed computations are deterministic, state round trips preserve subsequent trajectories, and components have stable documented interfaces. No performance or novelty claim is permitted.

## E01 — controlled history dependence (planned)

Construct paired sequences ending in the same observable query state but with earlier context events that imply different next-state distributions. Evaluate first-order, second-order, and third-order Markov models alongside fixed-SOE memory and SOE-plus-explicit-relations. Keep Grassmannian geometry disabled in E01 to isolate the memory contribution.

Report accuracy, log loss, conditional mutual information with estimator details and uncertainty, memory discrimination, and held-out sequence generalization. Controls include shuffled histories, memory reset, distractor events, variable temporal gaps, and alternative fixed decay banks.

A finding that a higher-order Markov model matches SOE performance is not failure: it may indicate compactness or computational utility rather than additional expressivity.
