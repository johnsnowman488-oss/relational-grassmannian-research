# HLG-M3 adaptation gate revision and M4 authorisation — v0.1

**Decision date:** 2026-11-18  
**Authority:** Explicit user-authorised revision following review of G2 and the planned G3 follow-on experiment  
**Status:** Adopted policy amendment; original G2 frozen record preserved

## 1. Why this revision exists

G3 was commissioned as the follow-on investigation of the adaptation shortfall exposed by G2. Its evidence must therefore be interpreted in that research lineage, rather than treated as an unrelated diagnostic solely because it used a separate campaign and controlled task.

The original G2 adaptation gate required at least a 5% relative reduction in untouched post-promotion loss. G2 recorded -0.28% improvement, a paired 95% world-clustered interval of -0.80% to 0%, and positive effects in 0/20 worlds. That result remains a valid failure under the original frozen endpoint and threshold. It is not rewritten.

G3-v0.3 measured validated revision against no revision on untouched post-change observations, including detection, fitting and validation latency. It is a different endpoint and controlled task; it is not numerically interchangeable with G2's pure post-promotion endpoint.

## 2. Revised adaptation criterion for M4 entry

For the G3-defined adaptation evidence, the replacement minimum is **2% relative reduction in post-change loss versus the no-revision policy**, with all of the following:

1. The effect is evaluated separately in the gradual-change and abrupt-change environments.
2. In each environment, the paired 95% world-clustered confidence interval lower bound must be above zero.
3. In each environment, the paired effect must be positive in at least 15 of the 20 held-out world configurations.
4. The stable negative control must remain dormant: zero detector alarms and zero candidate promotions.

This criterion deliberately replaces the prior G2-specific 5% endpoint for the M4 adaptation-entry decision. It does not alter the historical G2 report, G2 data, or G2 analysis.

## 3. Existing G3 evidence against the revised criterion

Canonical G3-v0.3 workflow: [44343380057](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44343380057).

| Environment | Relative improvement | 95% world-clustered CI | Positive worlds | Revised criterion |
|---|---:|---:|---:|---|
| Gradual | 49.07% | 46.13%–51.90% | 20/20 | Pass |
| Abrupt | 78.63% | 76.56%–80.33% | 20/20 | Pass |
| Stable | approximately 0% | approximately 0% | 0/20 strictly positive | Correctly dormant: 0 alarms, 0 promotions |

The G3 calibration selected threshold 24 using 60 independent fit streams and 40 fresh validation streams; both observed false-alarm counts were zero. The same threshold was used across all three environments.

The revised 2% floor is adopted after inspection of G3 outcomes. This is an explicit, outcome-informed policy decision authorised by the user. G3 is evidence supporting the revised decision, not an independent prospective confirmation of a threshold chosen before those outcomes were observed. The large separation from the 2% floor, positive clustered intervals, consistency across all 20 worlds in both changing environments, and stable negative control are the basis for accepting the existing evidence without another campaign.

## 4. M4 entry decision and boundaries

**Adaptation entry criterion: met under this v0.1 amendment.** Combined with the G2 capability and resource passes and the G2 integrity evidence, M4 is authorised to proceed as a bounded adaptive-system stability investigation.

The first M4 reference policy is the G3 validated-revision policy with detector threshold 24, applied to the existing fixed candidate topology. The comparator is no revision. The operating envelope is the controlled synthetic stable, gradual-change and abrupt-change family used by G3-v0.3.

M4 may now investigate coupled stability of memory, context, activation/dormancy, detector state, candidate fitting/validation/promotion and relational routing. Initial work remains fixed-topology and within the tested synthetic envelope. Do not infer arbitrary-environment generalisation, causal attribution, topology emergence, or global stability from G3 alone.

The G3 result does not establish that validated revision is universally optimal: delayed validated revision performed best in gradual change, while immediate revision performed best in abrupt change. M4 should retain this regime dependence as a measured property rather than silently selecting a universal policy winner.

## 5. Preservation and implementation

- The frozen M3 exit/entry document remains an immutable historical record of the original v0.2 gate.
- G2's original adaptation failure remains visible and unchanged.
- G3-v0.3 protocol, calibration, results and workflow evidence remain unchanged.
- The M4 entry policy is governed by this dated, versioned amendment.
- No additional G2 rerun or broad sensitivity campaign is required to enact this authorised policy decision.
