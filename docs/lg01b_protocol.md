# LG-01B — Trajectory-Derived Directional Relations

**Protocol version:** LG-01B-v0.1-draft  
**Status:** Draft for scientific review; **not frozen**; no implementation or execution authorised  
**Research stream:** Lepto-Graph Development Hypothesis (LGDH)  
**Date prepared:** 2026-11-14  
**Prerequisite:** LG-01A-v0.1 completed; downstream operating envelope restricted to the two passing fast rates

## 1. Research question

Can a fixed population of transient multidimensional modes form a useful directed relational organisation from their own observed trajectories, without receiving the target adjacency, edge labels, or destination identities?

This experiment tests one narrow mechanism: whether the direction of a source mode's trajectory contains information that helps identify which other modes it causally influences, and whether a data-driven source-trajectory-to-destination mapping can recover those directed relations on held-out observations.

It does **not** test slow historical registration, contextual routing, mode birth/death, connection plasticity, changing topology, Grassmannian geometry, or general reasoning.

## 2. Hypotheses and claim boundary

### H1 — trajectory-derived directional relation formation

For a stable, fixed population of modes coupled through a hidden sparse directed structure:

1. the observed trajectory tangent of a source mode contains predictive information about the future state of its true destination modes;
2. a mapping fitted only from observed trajectories can rank the true destinations above non-destinations on independent held-out input sequences;
3. the resulting directed relations support valid multi-step path witnesses more reliably than direction-blind, temporally shuffled, reverse-time, and random controls.

### H0 — no useful directional mapping

After conditioning on a destination mode's own present state and the other candidate source trajectories, the source tangent provides no reproducible destination-specific predictive contribution. Any apparent topology recovery is at or near the declared controls.

### Interpretation ceiling

A pass would establish task-specific recovery of a hidden directed coupling structure from trajectories in this synthetic dynamical family. It would **not** establish open-ended graph emergence, universal destination mapping, autonomous reasoning, biological equivalence, or a distinct primitive beyond predictive system identification. The linear predictive mapping is deliberately a first falsifiable mechanism, not a claim that the final LGDH mapping must be linear.

## 3. Relationship to LG-01A

LG-01A-v0.1 remains a valid full-range scientific failure: γ=0.05 and 0.20 each passed 30/30 seeds, while γ=0.80 passed only 26/30 and failed the frozen 27/30 gate.

LG-01B is restricted to:

- γ = 0.05
- γ = 0.20

The failed γ=0.80 condition is excluded from this initial experiment. This is a downstream scope restriction, not a retrospective LG-01A pass, a change to LG-01A's acceptance threshold, or a claim about the failed rate's behaviour under a different protocol. Every LG-01B report must state this boundary.

## 4. Experimental world and hidden relational structure

### 4.1 Fixed mode population

Each world contains:

- N=8 modes;
- state dimension d=16 per mode;
- a fixed population for the entire run;
- no mode creation, deletion, merging, or adaptive decay.

Mode indices are opaque identifiers used only to maintain correspondence between trajectories. They carry no semantic class or destination information.

### 4.2 Hidden directed topology

For each independent world, generate a directed graph with:

- exactly two outgoing edges per source;
- no self-edges;
- destinations selected without replacement;
- a strongly connected graph, with rejected graph draws and rejection counts recorded.

The graph is represented by an evaluator-only adjacency matrix G, where G_ij=1 means source i influences destination j. The model-facing runner must never pass G, its edge list, edge labels, or graph-generation seed to the trajectory-mapping code.

The out-degree k=2 is a declared task prior used for top-k selection. The learner is not given the identity of any edge. This means the experiment tests destination identity recovery under a known out-degree, not simultaneous discovery of the degree distribution.

### 4.3 Coupled mode dynamics

Use a common, hidden orthogonal transformation R in R^(16×16) per world. Generate it deterministically from the world seed using QR factorisation, with a fixed sign convention. The learner is not given R.

For destination mode j, define:

\[
\frac{dz_j}{dt}
=
-\gamma z_j
+\gamma u_j(t)
+\gamma c\sum_{i=1}^{N}G_{ij}Rz_i(t),
\qquad c=0.05.
\]

Here z_j(t) is in R^16, and u_j(t) is an independent bounded input stream for mode j. The same decay rate is used across modes within a world. The graph determines only the hidden directed coupling; it is not exposed to the learner.

The coupling is deliberately weak and stable. Since every source has out-degree two, ||G||_2 ≤ sqrt(14); with orthogonal R, c||G||_2 < 1. Thus the symmetric-part stability bound remains strictly dissipative relative to the -I decay term. The implementation must still check finite-state behaviour and verify the numerical transition matrix is stable.

### 4.4 Dimensionless integration and input process

Use dimensionless time s=γt. The dynamics become:

\[
\frac{dz_j}{ds}
=
-z_j+u_j(s)+c\sum_iG_{ij}Rz_i.
\]

Use a fixed dimensionless step Δs=0.05 for both rates. Therefore physical Δt=Δs/γ. Hold each input constant over one integration step and use an exact zero-order-hold update from the full coupled linear system (matrix exponential / equivalent numerically verified exact transition). Do not use forward Euler.

For each mode, generate an independent smooth bounded vector input using a seeded first-order autoregressive process:

\[
v_{j,k+1}=\rho v_{j,k}+\sqrt{1-\rho^2}\,\xi_{j,k},
\qquad
\rho=e^{-\Delta s/2},
\qquad
u_{j,k}=\frac{v_{j,k}}{\|v_{j,k}\|_2}.
\]

The ξ vectors are independent standard-Gaussian innovations. The input process, graph, and R are deterministic from recorded seeds. Input streams are not supplied as features to the learner; only the resulting mode trajectories are visible.

## 5. Observation interface and leakage boundary

The trajectory-mapping learner may receive only:

- the ordered array of mode state observations z_i[k];
- the common sample interval;
- the declared mode count and feature dimension;
- the declared out-degree prior k=2;
- the training/validation split boundaries.

It may not receive:

- G, edge lists, edge labels, or target destinations;
- the graph seed, graph-generation rejection history, or R;
- the exogenous input vectors or their random seeds;
- evaluator truth, path sets, or test labels;
- any precomputed source-destination score derived from the hidden graph.

The evaluator retains the hidden topology separately. All model-facing inputs must be canonically serialised and hashed. The runner must make it possible to inspect the exact model-facing payload independently of evaluator data.

## 6. Trajectory features and destination mapping

### 6.1 Causal tangent estimate

Estimate the source tangent using a backward difference only:

\[
\dot z_i[k]\approx\frac{z_i[k]-z_i[k-1]}{\Delta s}.
\]

Do not use a centred difference, because it would use a future sample relative to the prediction origin.

The primary directional feature is the unit tangent:

\[
d_i[k]=\frac{\dot z_i[k]}{\|\dot z_i[k]\|_2+\epsilon},
\]

with a frozen numerical ε chosen from float64 machine-scale safeguards and recorded in the configuration. Samples with non-finite or numerically degenerate tangents must be counted and handled by a predeclared rule; they must not be silently dropped.

### 6.2 Primary mapping: conditional trajectory prediction

For each destination j, fit a multivariate ridge predictor of its future state at horizon h=0.25 dimensionless time units (five integration steps):

\[
\widehat z_j[k+5]
=
f_j\left(
z_j[k],d_j[k],
\{d_i[k]:i\ne j\}
\right).
\]

The destination's current state and its own current tangent are included as autoregressive controls. This is essential because the destination's smooth external drive is temporally correlated; without its own tangent, the learner could misattribute destination-local dynamics to an incoming relation. All other modes' tangents are included jointly so that a candidate source is evaluated conditional on competing source trajectories, rather than by isolated pairwise correlation alone.

Standardise features using training-set statistics only. Fit ridge regression on training data. Select the regularisation coefficient from the frozen grid {10^-4, 10^-3, 10^-2, 10^-1, 1, 10, 100} using validation prediction error only. The selected coefficient is then fixed before test evaluation.

For each ordered pair i≠j, calculate a validation group-ablation score:

\[
S_{i\to j}
=
\frac{
\operatorname{MSE}_{j,-i}^{\mathrm{val}}
-
\operatorname{MSE}_{j,\mathrm{full}}^{\mathrm{val}}
}{
\operatorname{MSE}_{j,\mathrm{target\ only}}^{\mathrm{val}}+\epsilon
}.
\]

Here MSE_j,-i is computed after setting source i's tangent feature group to its training mean while keeping the destination's own state and tangent and all other source features unchanged. The target-only comparator uses only z_j[k] and d_j[k]. Positive S_i→j means the source tangent contributes held-out predictive information about destination j beyond the destination's own current state and the other source tangents.

For each source i, rank all j≠i by S_i→j and select the top two destinations. No evaluator labels or graph truth may affect ranking.

This is the pre-registered operational meaning of the trajectory-to-destination map for LG-01B-v0.1. It tests whether a source's intrinsic directional trajectory can be mapped to candidate destinations through conditional predictive contribution. It does not assume that a tangent vector is itself a destination label.

### 6.3 Test-set confirmation

After destination ranking is frozen from validation, evaluate the fitted predictors and the selected directed pairs on the independent test episode. Report test group-ablation predictive gain for selected and unselected pairs, but do not revise the selected graph using test scores.

## 7. Controls and ablations

All controls receive the same trajectory observations, data splits, mode count, out-degree prior, and training budget.

1. **Destination-only autoregressive null:** predicts each destination from its own current state and own current tangent only.
2. **Source-state mapping:** replaces source tangent groups with source state vectors. This tests whether tangent direction contributes beyond ordinary source-state information.
3. **Direction-blind activity mapping:** replaces each 16D unit tangent with its scalar tangent magnitude. This tests whether vector direction adds value beyond activity level.
4. **Temporally shuffled tangent mapping:** block-shuffles each source tangent sequence within an episode, using blocks of one dimensionless time unit, preserving local marginal structure while breaking alignment to destination responses.
5. **Reverse-time mapping:** predicts destination past state from later source tangents using the same horizon. This tests whether the apparent relation is specifically forward-directed.
6. **Symmetric association baseline:** ranks pairs using direction-blind, symmetric association between mode activity traces; it cannot assign a direction from the association itself.
7. **Random top-two baseline:** selects two destinations uniformly for each source using a separately recorded evaluator seed.

The primary model must outperform the best non-directional / shuffled control, not merely random selection. The source-state control is separately reported because a successful result from state features alone would not establish the value of trajectory direction.

The E02 ObservedEventGraph is not treated as a competing learner here: it receives explicit observed edges and answers a different question. It may be used later as an interface/reference comparison, with that information advantage stated.

## 8. Worlds, seeds, and data splits

Use 30 independent graph worlds, with world seeds 301–330. Each world is evaluated at both γ=0.05 and γ=0.20, paired on the same hidden graph, orthogonal transformation, and dimensionless input-generation seeds. The two rate conditions are not counted as 60 independent worlds.

For each world/rate, generate independent train, validation, and test episodes with independent input innovations:

| Episode | Burn-in | Recorded duration | Purpose |
|---|---:|---:|---|
| Train | 10 dimensionless units | 80 units | Fit regression parameters |
| Validation | 10 units | 20 units | Select ridge coefficient and rank candidate destinations |
| Test | 10 units | 40 units | Final held-out evaluation only |

At Δs=0.05, the recorded episodes contain 1,600 training, 400 validation, and 800 test samples before causal-tangent and prediction-horizon boundary exclusions. No episode may share input innovations or state samples with another split.

The same graph and R persist across the three episodes within a world. The learner does not receive graph identity or evaluator seed values. Record all seed derivations and episode hashes.

## 9. Metrics

### Primary metrics

- **Macro precision@2 / recall@2:** fraction of recovered top-two directed edges that match evaluator truth, averaged over sources. Since the true out-degree is two, precision@2 and recall@2 are numerically equal at the world level.
- **World-level exact edge count:** number of correctly recovered directed edges out of 16.
- **Paired improvement over controls:** difference in precision@2 between the primary tangent model and each declared control, paired by world.
- **Test predictive contribution:** held-out group-ablation score for selected versus unselected pairs.
- **Directional asymmetry:** difference between forward source-to-destination score and the corresponding reverse-direction score.

### Path-witness metrics

Construct the inferred directed graph from the validation-selected top-two edges. Enumerate all length-two paths and all ordered source/destination pairs. Report:

- path precision: fraction of inferred length-two edge sequences that are true evaluator paths;
- path recall: fraction of evaluator length-two paths recovered;
- query coverage: fraction of ordered pairs with at least one inferred path;
- witness validity: whether every edge in each returned witness is supported by the hidden evaluator graph.

The learner is not given path queries or path truth during fitting. Path metrics are secondary and must not conceal poor edge recovery.

### Cost and diagnostics

Record parameter count, training samples, prediction operations, wall-clock time, peak memory if available, finite-state checks, matrix stability checks, and all failed/degenerate tangent counts. Report results separately for each rate and paired differences across rates.

## 10. Pre-registered acceptance and failure criteria (draft)

Each rate is evaluated independently over the 30 paired worlds.

A rate passes only if all of the following are met:

1. Mean primary macro precision@2 is at least **0.60**.
2. The lower bound of a 95% paired-world bootstrap confidence interval for mean precision@2 is above the random-selection expectation 2/7.
3. At least **24 of 30 worlds** achieve precision@2 of at least **0.50**.
4. Primary precision@2 exceeds the best of the source-state, direction-blind activity, temporally shuffled, reverse-time, and symmetric-association controls by at least **0.10 absolute**, with the paired 95% bootstrap confidence interval for the difference entirely above zero.
5. Test-set selected-edge predictive contribution is positive on average and greater than that of non-selected pairs.

Path-witness validity is reported as a secondary gate: inferred length-two witnesses must have precision of at least **0.30** and exceed the best control by at least **0.10 absolute**. The lower absolute threshold is intentional: a two-edge witness requires both constituent edges to be recovered, so its expected precision is lower than single-edge precision. Path recall and query coverage are reported regardless of pass/fail.

A failure at either rate blocks LG-01C. A pass at one rate does not imply a pass at the other. A mixed result must be reported as mixed, not averaged into an overall pass.

These numerical thresholds are proposed for review before freeze. They must not be altered after execution. Any revision after a run requires a dated protocol revision and a fresh confirmation campaign.

## 11. Reproducibility and implementation requirements

The eventual runner must produce:

- protocol and configuration snapshots with hashes;
- repository commit and clean/dirty working-tree status;
- environment and dependency versions;
- world, graph, transformation, and episode seed derivations;
- evaluator-only topology files stored separately from model-facing inputs;
- model-facing trajectory arrays or deterministic regeneration metadata and SHA-256 hashes;
- per-world/per-rate/per-control predictions and metrics;
- validation-selected destination rankings;
- held-out test metrics and path witnesses;
- summary JSON/Markdown and SHA256SUMS.

Mathematical/reproducibility tests must cover:

- exact coupled-system transition against an independent high-accuracy reference;
- stability bound and finite-state checks;
- causal tangent calculation and no future-sample leakage;
- absence of evaluator graph data from learner inputs;
- deterministic graph/input generation and replay;
- training-only feature standardisation;
- validation-only hyperparameter and destination selection;
- test-set non-interference with model selection;
- correct direction convention for G_ij;
- edge/path metric correctness on hand-constructed toy graphs;
- checksum verification and complete seed coverage.

No campaign runner, workflow, or result artifacts should be added until this protocol is reviewed and frozen.

## 12. Threats to validity and explicit limitations

1. **Known out-degree:** top-two selection uses a declared k=2 prior. This experiment does not discover unknown degree distributions.
2. **Synthetic linear coupling:** success may reflect recoverability of a stable linear system, not a general lepto-graph mechanism.
3. **Predictive relation versus causal proof:** hidden edges generate causal influence in the simulator, but observational prediction alone is not a general causal-identification guarantee.
4. **Tangent estimator sensitivity:** backward finite differences can amplify noise. The input process is smooth and bounded, but sensitivity to sampling and noise remains a later robustness question.
5. **Linear mapper:** ridge regression is a deliberately simple first mapping. A failure does not falsify every possible nonlinear or history-dependent destination map.
6. **Fixed population and topology:** no growth, pruning, reorganisation, or topology change is tested.
7. **Rate scope:** conclusions apply only to γ=0.05 and 0.20 under this protocol, not to γ=0.80 or arbitrary rates.

These limitations must appear in any report and must not be hidden by aggregate metrics.

## 13. Freeze checklist

Before implementation, scientific review must explicitly accept or revise:

- [ ] the eight-mode, 16D coupled linear world and two-outgoing-edge prior;
- [ ] the coupling orientation and stability argument;
- [ ] the smooth bounded input process and exact integration scheme;
- [ ] the causal tangent feature and conditional ridge mapping;
- [ ] the independent train/validation/test episode design;
- [ ] the direction-blind, shuffled, reverse-time, state-only, and random controls;
- [ ] the 30-world campaign and paired-rate interpretation;
- [ ] the numeric acceptance thresholds and path-witness criteria;
- [ ] the claim boundary and failure interpretation.

**Current decision:** draft prepared for review only. No protocol freeze, implementation, CI campaign, or scientific result is implied.


## 14. Internal protocol review notes

The first review pass identified and corrected three design issues before freeze:

- The destination's own tangent is now included in its autoregressive baseline to control for its temporally correlated local drive.
- The source-state-only mapping is included in the primary competing-control comparison; otherwise the protocol could incorrectly attribute state-based prediction to tangent direction.
- The length-two witness threshold is reduced to a level compatible with the single-edge acceptance threshold while still requiring a measurable advantage over controls.

Remaining review questions are whether the fixed k=2 prior is acceptable for this first mechanism test, whether the linear coupled world is sufficiently discriminating without being mistaken for general graph emergence, and whether the proposed 0.60 edge-recovery threshold is appropriately demanding. These are scientific freeze decisions, not implementation details.
