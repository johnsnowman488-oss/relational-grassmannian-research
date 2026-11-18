# HLG-M3 G3-v0.1 pilot — execution note

**Workflow:** [44163665511](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44163665511)  
**Commit:** 56d678b6caa91af86cafa1c05c942fa074d3d902  
**Status:** implementation and CI passed; pilot is not confirmatory.

## Execution

The stable, gradual and abrupt jobs each executed 100 streams across the same 20 held-out world identities and five paired seeds. Four policy arms were evaluated per stream. Python 3.10 and 3.12 full repository tests passed.

## Pilot finding: detector selectivity is inadequate

- Stable: 73/100 streams alarmed; validated revision promoted 20/100 and immediate revision 68/100.
- Gradual: all 100 streams alarmed and promoted; mean alarm delay was 22.57 steps, but some alarms preceded the programmed change.
- Abrupt: all 100 streams alarmed and promoted; mean alarm delay was -0.31 steps, with alarm times spanning 131–165 against a change at step 160.

The apparent validated-revision post-change relative improvements were -0.36% in stable, +38.96% in gradual and +78.28% in abrupt. These values are **not accepted as adaptation effects** because false/pre-change alarms allow candidate fitting before the true change. Immediate and delayed arms have the same detection defect.

## Decision

Preserve the pilot artifacts. Do not pool or report its apparent adaptation gains as confirmatory findings. G3-v0.2 adds development-fit threshold selection and independent development-validation of the stable false-alarm rate. Held-out execution proceeds only if calibration passes. G2 remains unchanged.
