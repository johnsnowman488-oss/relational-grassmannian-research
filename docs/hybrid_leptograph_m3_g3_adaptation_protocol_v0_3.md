# HLG-M3 G3 — Independent detector calibration and environmental adaptation

**Protocol:** HLG-M3-G3-ADAPTATION-v0.3  
**Status:** versioned refinement after the v0.2 calibration gate failed; held-out execution remains conditional on the fresh validation result.

## 1. Preservation and scope

G2 and the original G3-v0.1/v0.2 records remain unchanged. The v0.2 result is preserved: threshold 16 produced 1/60 fit false alarms (1.67%) and 6/40 validation false alarms (15%). Its three held-out environment jobs were correctly skipped. No v0.2 result is pooled with v0.3.

This refinement changes only detector calibration data separation and the fit-selection rule. The G3 generator, three environment definitions, four policy arms, 20 held-out world identities, five paired seeds, and policy endpoints remain unchanged. It does not modify G2 thresholds, results, the M3 exit criteria, or the M4 gate.

## 2. Independent calibration allocation

Use the dedicated `hybrid_leptograph_m3_g3_calibration_manifest_v0_1.json`:

- 12 calibration-fit worlds × 5 replicate seeds = 60 streams.
- 8 fresh calibration-validation worlds × 5 replicate seeds = 40 streams.
- All 20 world-configuration seeds and 100 replicate seeds are disjoint from the frozen BM0/BM1 fit, validation, test, and pilot allocations.
- Validation worlds are generated independently of the fit worlds and are not the previously observed G3-v0.2 validation worlds.
- The calibration manifest contains no held-out test worlds. The original frozen BM0/BM1 manifest remains the sole source for G3-S/G3-G/G3-A test-world identities.

Calibration uses the stable negative-control environment. Observation-noise multipliers follow the profiles recorded in the manifest. No G2 held-out test outcomes are read or used.

## 3. Threshold selection and one-time validation

The candidate threshold grid remains `[8, 12, 16, 20, 24, 32, 48, 64]`.

1. Evaluate the full grid on the 60 calibration-fit streams.
2. Select the **lowest threshold with zero observed fit false alarms**. If no threshold satisfies this rule, calibration fails; do not select the maximum by default.
3. Evaluate the selected threshold exactly once on the 40 fresh validation streams.
4. Require the observed fresh-validation false-alarm rate to be no greater than 5% (at most 2/40 streams).
5. If validation fails, stop before held-out environment execution. Do not retune against this validation set; any further detector change requires a new versioned protocol and new independent validation worlds.

The fit and validation counts, rates, world IDs, selected threshold, calibration-manifest hash, and evidence hash are mandatory output fields. A zero observed fit rate is a conservative selection rule, not a claim that the underlying false-alarm probability is zero; the finite sample size and uncertainty must be disclosed.

## 4. Conditional concurrent environment campaign

Only after the v0.3 calibration gate passes:

- Run G3-S stable, G3-G gradual, and G3-A abrupt as three independent concurrent jobs.
- Each environment uses the same 20 frozen held-out G2 world identities and five replicate seeds (100 streams).
- All four paired policy arms receive identical streams: no revision, immediate revision, validated revision, and delayed validated revision.
- Freeze the single selected detector threshold across all three environments. No environment-specific tuning.
- Run Python 3.10 and 3.12 full test suites concurrently.
- Aggregate only after all three environment artifacts and both test suites are complete.

The aggregate must verify calibration provenance, the fresh calibration split, exact environment coverage, 20 test worlds × 5 seeds, four policy arms, chronology/integrity flags, threshold equality, artifact hashes, and both test outcomes.

## 5. Interpretation

Calibration passing establishes only that the specified detector met the predeclared observed false-alarm limits on its independent stable calibration data. It does not establish detection power or useful adaptation.

Stable is a negative control: no revision may be correct. Gradual and abrupt environments test tracking and recovery. An alarm is not proof of a true change; promotion is not proof of improved future performance. Compare all policy arms on untouched post-change observations and report missed changes, false alarms, detection delay, promotion and validation outcomes.

G3 remains a controlled synthetic adaptation diagnostic. It does not establish general relational discovery, causal attribution, or global coupled stability (M4). M3-G3 remains the final scientific decision-report gate; this G3 adaptation diagnostic must not be confused with that milestone label.
