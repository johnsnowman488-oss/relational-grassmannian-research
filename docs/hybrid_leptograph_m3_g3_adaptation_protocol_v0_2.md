# HLG-M3 G3 — Adaptive Relational Revision Across Environmental Regimes

**Protocol:** HLG-M3-G3-ADAPTATION-v0.1  
**Status:** revised after the v0.1 detector pilot; calibration precedes held-out execution.

## 1. Relationship to G2 and G3-v0.1

G2 remains the immutable confirmatory baseline. Its allocation, thresholds, resource envelope, results and M4 gate are unchanged. G3 is a separate diagnostic.

G3-v0.1 exposed a detector-calibration defect: the threshold produced frequent alarms in stable streams and alarms before the programmed change in gradual/abrupt streams. Its apparent adaptation gains are not accepted as confirmatory evidence. Preserve its artifacts and findings as a pilot; do not pool them with v0.2.

## 2. Three environments, concurrently

The same stable, gradual and abrupt variants, generator, policy arms, held-out identities and paired seeds are retained. The only methodological refinement is that the detector threshold is calibrated without using held-out test outcomes.

## 3. Detector calibration and data separation

- Use the frozen 12 development-fit worlds and their five replicate seeds to select the smallest threshold from the predeclared grid [8, 12, 16, 20, 24, 32, 48, 64] with stable-negative-control false-alarm rate no greater than 5%.
- Verify that selected threshold on the separate eight development-validation worlds; require stable false-alarm rate no greater than 5%.
- If validation fails, do not execute or interpret the held-out environment campaign. Record calibration failure and discuss a new versioned detector design.
- Freeze the selected threshold across all three held-out environments. No per-environment tuning is allowed.
- The 20 held-out test worlds × five replicate seeds remain untouched until calibration passes.

## 4. Matched policy arms and endpoints

All four policy arms receive identical observations: no revision, immediate revision, validated revision (32 fit / 32 validation), and delayed validated revision (32-step delay followed by the same windows). Initial operator fit remains the first 128 observations. Prediction precedes current target feedback.

Primary diagnostic remains paired post-change loss reduction of validated revision relative to no revision, with a held-out-world bootstrap interval. Secondary endpoints include stable false alarms/promotions, detection delay, validation quality, promotion frequency and overall loss.

The G2 5% threshold remains a reference only, not a retroactive G3 pass gate.

## 5. Parallel execution

One detector-calibration job runs first using development splits only. After it passes, the three independent environment jobs run concurrently, alongside Python 3.10/3.12 full tests. One aggregate verifies the calibration artifact, exact environment coverage, 20 test worlds × five seeds, four policy arms, integrity flags and evidence hashes.

## 6. Claim ceiling

G3 is a controlled synthetic adaptation diagnostic. It does not establish general relational discovery, causal attribution, or global coupled stability (M4). A stable no-revision result is valid; adaptation should not be forced when no change is present.
