# HLG-M3 completion and M4 entry gate — proposal v0.1

**Status:** Proposed decision record; not frozen.  
**Applies to:** HLG-M3 broader benchmark BM-0 through confirmatory execution.  
**Purpose:** Define a finite completion target for M3 and a clear evidence gate for M4. Prevent open-ended inspections, repeated sensitivity sweeps, or scope expansion.

## 1. Programme boundary

HLG-M3 is the fixed-candidate-topology adaptive relational benchmark. It must establish whether the implemented mechanisms work on held-out compositions and multi-world sequential conditions, whether candidate revision is useful, and what the actual resource trade-offs are.

M3 does not claim global stability of the fully coupled adaptive system. That is the principal M4 question. M3 completion does not require every hypothesis to pass; negative and inconclusive findings are valid outcomes if the benchmark is complete and interpretable.

E-series experiments remain a separate research stream. Their tasks, evidence and experimental workflows are not M3 inputs or M3 acceptance evidence.

## 2. Finite M3 execution plan

There are only three remaining M3 gates.

### Gate M3-G1 — BM-2 generator acceptance

Accept BM-2 when all of the following are true:

1. The 21 predeclared OFAT profiles are generated: one baseline plus the 20 non-baseline factor-level profiles. Pilot outputs remain separate from confirmatory outputs.
2. The confirmatory allocation materialises exactly 40 world configurations and 200 streams: 12 fit worlds × 5 seeds, 8 validation worlds × 5 seeds, and 20 held-out test worlds × 5 seeds.
3. Every declared factor level occurs in every split. The held-out test split covers all required context-separation × capacity, source-correlation × independent-missingness, and drift-family × noise pairs specified in the BM-0/BM-1 protocol.
4. World-configuration seeds and stream seeds are unique and disjoint across splits. Pilot seeds are disjoint from confirmatory seeds.
5. Realised observation masks, factor values, composition IDs, world IDs, stream IDs, generator version and manifest hash are recorded.
6. Learner-side records contain no evaluator-only fields; the prediction-before-target chronology and missing-observation semantics are preserved.
7. Two independent executions from the same commit and manifest produce identical canonical configuration/stream evidence hashes.
8. Generator tests, schema checks, artifact-coverage checks and Python 3.10/3.12 repository tests pass.

**Decision:** pass or fail. A failure is repaired only at the failing contract point and the affected deterministic checks are rerun. No new factor levels or exploratory sweeps are added.

### Gate M3-G2 — one confirmatory benchmark

After G1 passes and the protocol/thresholds are frozen, execute the existing 200-stream allocation once, on one immutable implementation commit and one manifest hash.

Required evidence:
- M3-A context ambiguity/capacity;
- M3-B held-out composition, correlation and identifiability;
- M3-C missingness, dormancy and reactivation;
- M3-D drift detection and candidate revision;
- M3-E C0-C4 common-envelope/Pareto comparison;
- M3-I integrated sequential benchmark;
- full Python 3.10 and 3.12 test suites;
- one aggregate evidence verifier.

The aggregate must verify exact expected job/cell/stream coverage, artifact and commit identity, manifest identity, split and composition disjointness, learner/evaluator separation, chronological candidate windows, valid resource accounting and test outcomes.

No additional broad sensitivity sweep follows this run. A rerun is permitted only for an identified infrastructure or evidence-integrity failure, using the same frozen commit, manifest and seeds. A code or protocol change requires a new versioned campaign and an explicit reason.

### Gate M3-G3 — one scientific decision report

Produce one report from the confirmatory artifacts. It must:

- classify H1-H7 individually as supported, not supported, or inconclusive;
- report the predeclared primary endpoints, paired effects, 95% world-clustered intervals, per-world distributions and worst-decile outcomes;
- identify the strongest eligible C0-C4 comparator for each primary comparison;
- report actual state bytes, parameter count/bytes, update operations and query operations;
- identify one fixed-topology reference candidate, or explicitly conclude that no candidate qualifies;
- preserve negative results and all excluded/inconclusive conditions.

No further inspection phase is required after this report unless a specific integrity defect is found.

## 3. Proposed scientific thresholds to freeze before G2

The BM-0/BM-1 protocol currently defines metrics and hypotheses but does not yet state a single practical effect threshold for M4 entry. The following are proposed so the decision cannot be selected after seeing test results:

### Primary capability gate — held-out composition

The selected M3 candidate must achieve at least a **5% relative reduction in held-out primary-composition loss** against the strongest eligible matched C0-C4 comparator, with:

- the lower bound of the paired 95% world-clustered confidence interval for improvement above zero; and
- a positive paired effect in at least 15 of the 20 held-out world configurations.

The comparison uses the predeclared primary test compositions only. Optional REL-E primitive-OOD results cannot satisfy this gate.

### Adaptation gate — candidate revision

On the predeclared drift-eligible held-out streams, candidate promotion must achieve at least a **5% relative reduction in untouched post-promotion loss** against retaining the incumbent, with:

- the lower bound of the paired 95% world-clustered confidence interval for improvement above zero; and
- a positive paired effect in at least 15 held-out world configurations with sufficient eligible evidence.

Insufficient-evidence cases remain insufficient; they are not dropped silently or converted into failures.

### Resource gate

The selected candidate and the comparator used for the primary claim must both remain within the common ceilings:

- persistent state: 512 bytes;
- trainable parameters: 4,096;
- update compute: 8,192 multiply-adds per observed update;
- query compute: 4,096 multiply-adds per prediction;
- precision: float64.

An unmatched result cannot satisfy the M4 resource gate.

**These thresholds are proposals, not frozen protocol terms.** They must be accepted or amended before G2 starts. They must not be tuned after confirmatory results are visible.

## 4. M4 entry decision

M3 is **scientifically complete** when G1, G2 and G3 are complete, regardless of whether the hypotheses pass.

M4 is **authorised to proceed as an adaptive-system investigation** only when:
1. M3 benchmark integrity passes with no unresolved leakage, split, seed, chronology or artifact defect;
2. the primary capability gate passes;
3. the adaptation gate passes;
4. the resource gate passes; and
5. one fixed-topology M3 reference candidate, its comparator, configuration and operating envelope are frozen.

If M3 completes but one or more scientific entry gates fail, record M3 as a valid negative or inconclusive result. Do not promote the candidate into a full M4 adaptive-system claim. Any further work must be one narrowly specified experiment addressing the failed gate, not a new general sweep.

## 5. M4 initial scope

M4 begins with the global coupled stability of the frozen M3 reference candidate under its measured operating envelope. It should test the interaction of memory, context gating, activation/dormancy, detection and candidate revision as one coupled adaptive system.

Topology birth/death or additional adaptive mechanisms are not automatically included in the first M4 campaign. Each requires a separate explicit hypothesis and entry gate after the fixed-topology stability baseline is understood.

## 6. Decision discipline

- No E-series experiments are required for M3 completion or M4 entry.
- No E-series CI workflow is part of an M-series pull-request gate.
- No additional broad factor sweep after the single confirmatory 200-stream campaign.
- No changing thresholds, metrics, splits or comparators after test outcomes are inspected.
- No requirement that every H1-H7 hypothesis pass.
- No M4 advancement without a qualifying frozen M3 candidate.

**Current decision:** proposed; awaiting review and acceptance before BM-2 acceptance is declared and before the confirmatory campaign is authorised.
