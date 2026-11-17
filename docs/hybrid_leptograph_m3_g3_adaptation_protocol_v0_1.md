# HLG-M3 G3 — Adaptive Relational Revision Across Environmental Regimes

**Protocol:** HLG-M3-G3-ADAPTATION-v0.1  
**Status:** authorised implementation and diagnostic campaign; amendable before execution.

## 1. Relationship to G2

G2 remains the immutable confirmatory baseline. Its 200-stream allocation, frozen thresholds, resource envelope, results and claim boundary are not modified. G3 is a separate focused diagnostic motivated by G2's strong capability result and unsuccessful aggregate adaptation endpoint.

G2 did execute the candidate-revision path and recorded promotions. G3 therefore does not assume adaptation was disabled. It tests whether revision is appropriately challenged and selective under known environmental demand.

## 2. Three environments, implemented concurrently

All variants use one generator contract, one learner/policy interface, the same held-out world identities and paired replicate seeds.

| Variant | Environment | Diagnostic |
|---|---|---|
| G3-S | Stable relation | Negative control: revision should generally remain inactive; false alarms or harmful revisions count against selectivity |
| G3-G | Gradual relation change | Tracking: determine whether detection and validated revision follow a slowly moving operator |
| G3-A | Abrupt relation change | Recovery: measure detection delay, candidate quality, promotion and post-change recovery |

These are independent CI jobs, not sequential stages.

## 3. Matched design

- Reuse the frozen G2 manifest's 20 held-out test-world identities and five replicate seeds per world.
- Each environment has 100 streams; the campaign has 300 environment-streams.
- Four policy arms receive identical observations and targets:
  1. no revision: retain the initial operator;
  2. immediate revision: fit on 32 post-alarm observations and promote without a separate validation gate;
  3. validated revision: 32 fit observations, 32 separate validation observations, promote only on positive validation improvement;
  4. delayed validated revision: wait 32 observations after alarm, then use the same 32/32 windows.
- Initial operator fitting uses only the first 128 observations. Every prediction is recorded before current target feedback is consumed.
- Stable keeps the operator fixed; gradual interpolates over steps 160–320; abrupt changes at step 160.
- No evaluator labels, future samples, or split metadata enter prediction, detection, fitting or validation.

## 4. Endpoints

Primary diagnostic: paired post-change loss reduction of validated revision relative to no revision, summarized by held-out-world means and a 95% world-cluster bootstrap interval.

Secondary endpoints: stable false alarms/promotions; gradual and abrupt detection delay; promotion frequency; validation loss; post-change loss for all policy arms; and overall loss.

The frozen G2 5% threshold is reported as a reference, not silently reused as a G3 pass/fail gate. G3 is diagnostic: stable may show revision is unnecessary, while gradual and abrupt reveal whether it helps when change is present.

## 5. Interpretation and claim limits

A stable no-revision result is a valid finding, not an adaptation failure. An alarm alone is not evidence of true change. Immediate revision is a permissive comparator, not the preferred policy. Candidate promotion and post-promotion benefit are separate outcomes.

This controlled two-dimensional experiment does not establish broad relational generalisation, causal attribution, or global coupled stability (M4). G2 protocol and results remain unchanged.

## 6. Parallel execution

Three environment jobs (G3-S/G3-G/G3-A) run concurrently. Python 3.10 and 3.12 full test suites run concurrently with them. One aggregate verifies exact environment coverage, 20 held-out worlds, five seeds per world, four policy arms, stream counts, integrity flags and evidence hashes. No environment job depends on another.
