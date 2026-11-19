# HLG-M4 acceptance gate proposal — v0.1

**Status:** Proposed for explicit review and freeze before confirmatory results.  
**Parent:** M4 Job 4 / issue #36.  
**No confirmatory M4 outcomes have been inspected or generated under this proposal.**

## 1. Decision structure

M4 is a bounded fixed-topology synthetic integration milestone. The gate separates:
1. semantic correctness of the shared reference contract;
2. learned relational composition and path selection;
3. temporal validity, outage behaviour and abstention;
4. adaptation/stability/recovery;
5. resource and reproducibility obligations.

A and B are both implemented and evaluated. B is the leading hypothesis, not the winner by assumption. C/R are not required primary implementations.

## 2. Proposed acceptance rules

### Gate S — reference semantics and information integrity

Required:
- 100% pass on the frozen deterministic contract suite.
- Zero invalid returned witnesses in all verifier cases.
- Zero future-observation leakage across candidate generation, ranking, memory update and readout.
- Zero acceptance of expired, wrong-context, wrong-type, event-order-violating or gap-violating witnesses.
- Every returned witness preserves exact ordered entity and relation-instance identities.
- Oracle/reference mode and learned mode remain separately labelled in every output.

Any failure here blocks scientific scoring because the task's truth boundary is compromised.

### Gate C — learned composition and selection

Primary test: held-out relational combinations at path depths 2–4, evaluated over 20 independent world clusters.

For each architecture:
- report exact path-selection accuracy and witness coverage by depth;
- report false-path selection and correct/unjustified abstention separately;
- compare against the strongest declared non-compositional baseline and a chance/shuffled-path baseline using paired world-level effects;
- require the paired 95% world-clustered confidence interval for the primary held-out composition improvement to have a lower bound above zero;
- require a positive paired effect in at least 15 of 20 held-out worlds;
- require zero invalid witnesses among returned paths (semantic validity is enforced by Gate S).

The primary endpoint and baseline construction must be fully specified in the frozen task manifest before test-world outcomes are visible. The 15/20 plus positive clustered-CI rule is carried forward from the adopted G3 evidence standard; it is not a post-hoc threshold chosen from M4 results.

M4 requires at least one architecture to pass Gate C. If neither passes, M4 composition fails. If only one passes, that architecture is the only supported M4 candidate. If both pass, compare their paired effect and resource frontier; do not force a winner when the interval for the A–B difference includes zero.

### Gate T — temporal validity, outages and abstention

Required:
- zero cutoff leakage and zero expired-fact use (also Gate S);
- report retention/retrieval separately at every frozen outage duration;
- B persistence must not override validity, context or observation-cutoff rules;
- A's decay and B's persistence must be characterised over the same event/query schedule;
- under ambiguous, incomplete or capacity-exhausted conditions, report correct abstention and false selection separately;
- no silent eviction in B; capacity exhaustion returns the declared abstention code.

No universal claim that B must outperform A on every delay is required. The architecture result must explain the measured persistence/decay trade-off.

### Gate A — adaptation and stability

Use the G3-derived fixed-topology policy and threshold 24 in stable, gradual and abrupt synthetic environments.

For both gradual and abrupt environments, separately:
- relative reduction in post-change loss versus no revision is at least 2%;
- paired 95% world-clustered CI lower bound is above zero;
- positive paired effect in at least 15/20 held-out worlds.

Stable negative control:
- zero detector alarms;
- zero candidate promotions.

Lifecycle and integrity:
- candidate fit and validation samples are independent;
- no candidate promotion without identifiability and validation improvement;
- complete trusted-state rollback is exact for every snapshotted component;
- rejected candidates leave trusted state unchanged;
- dormancy/reactivation and outage recovery follow the frozen state machine;
- no non-finite state and no breach of the architecture-specific finite-horizon envelope derived before confirmatory runs.

The 2%/CI/15-of-20/stable-control criterion is the user-authorised 18 November M4 entry policy carried into the integrated A/B system. It is not a retroactive pass of the original G2 5% endpoint. The G2 failure remains recorded unchanged.

### Gate R — resources and reproducibility

Required:
- complete populated-state bytes, parameter count/bytes, update/query operation counts and latency reported separately;
- native and matched-budget/Pareto views, with no false claim of exact matching;
- raw seed/world/query records and aggregate outputs reconcile exactly;
- complete manifest, source SHA, environment and artifact SHA-256 values;
- focused tests and full repository regression pass on Python 3.10 and 3.12.

Resource superiority is not a hard M4 pass condition. The evidence must be sufficient to make an honest architecture decision and to carry the resource trade-off into E09.

## 3. Architecture decision rule

- If B passes Gates S, C, T, A and R, B is supported as the M4 primary candidate.
- If B fails Gate C or A but A passes, do not retain B as primary merely because it was the leading hypothesis; select A within the demonstrated scope.
- If both pass, prefer B only if its paired held-out composition/adaptation performance or robustness advantage is supported and its resource cost is acceptable on the reported frontier. If the A–B interval includes zero, report no statistically resolved performance winner and make any engineering preference explicit.
- If neither passes Gate C, M4 does not pass composition.
- A failed gate remains visible; do not weaken thresholds after outcomes.

## 4. Stop/abort conditions

Pause confirmatory execution and report an integrity failure if:
- model inputs contain evaluator-only labels, hidden paths or future observations;
- world/split/seed manifest differs between A and B;
- the artifact verifier detects missing, duplicate or inconsistent records;
- the reference composer accepts an invalid witness;
- the architecture silently evicts persistent relational state;
- rollback fails to restore the full trusted snapshot;
- the source commit or task/protocol manifest changes after held-out results are opened.

A code/test failure may be repaired with a versioned implementation change and rerun of the affected predeclared checks. A scientific gate failure is not converted into a pass by code repair or threshold change; any new campaign requires a versioned amendment and new held-out evidence.

## 5. What a pass does and does not establish

A pass establishes integrated A/B relational composition, temporal handling, bounded adaptation/recovery and resource behaviour only on the declared fixed-topology synthetic task family and finite-horizon operating envelope.

It does not establish:
- E08 cross-domain transfer;
- arbitrary-depth or arbitrary predicate-algebra composition;
- endogenous relation/topology discovery outside the declared candidate topology;
- natural-language understanding or general reasoning;
- Grassmannian or geometric representation advantage;
- arbitrary asynchronous/delayed/switched stability or a global Lyapunov theorem.

## 6. Freeze checklist

Before confirmatory execution, record and freeze:
1. exact primary Gate C endpoint and strongest non-compositional baseline;
2. world-generation and held-out relation-combination manifest;
3. query/task counts and seed manifest;
4. architecture parameterization and training/calibration exposure;
5. resource budget definitions and accounting convention;
6. architecture-specific finite-horizon stability envelope;
7. artifact/verifier schema and source commit;
8. all decision thresholds above.

This proposal is measurable and bounded, but the exact Gate C primary endpoint/baseline and state-envelope derivation must be completed in the implementation protocol before the first confirmatory run. The user's approval of this gate is required before that run.
