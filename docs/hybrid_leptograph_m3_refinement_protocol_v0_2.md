# HLG-M3 final refinement protocol v0.2

**Campaign:** HLG-M3-FINAL-REFINEMENT-v0.2  
**Parent:** HLG-M3 implementation protocol v0.1 and implementation campaign v0.1  
**Status:** authorised investigation refinement; amendable; not frozen  
**Scope:** close the first integrated-slice gaps before the broader M3 sequential benchmark

## Why this revision exists

The v0.1 campaign executed all six packages and passed its declared tests, but its M3-I result exposed three unresolved connections: context decisions were recorded without gating context features; activation was recorded without gating effective route predictions; and the integrated detector never triggered, leaving candidate revision unexercised end to end. This version makes these connections executable and measures their behaviour. It does not erase or reinterpret v0.1 evidence.

## Final interface amendments

1. **Context applicability:** context features enter the estimator only after ACCEPT. For NOVEL and ABSTAIN, effective context features are zeroed and source routes are gated off. A newly created slot is eligible on a later accepted observation, not retroactively on the novelty-creation event.
2. **Shadow/effective separation:** a shadow predictor uses all declared source groups for prequential usefulness diagnostics. The effective predictor applies per-relationship activation gates. Dormant relationships remain stored and can be assessed through the shadow path; dormancy never deletes an operator.
3. **Accepted-operator override:** the effective predictor uses the accepted operator version. Candidate estimates do not replace it until validation and identifiability gates pass. The shadow estimator continues learning from all eligible observed source groups.
4. **Conditional identifiability:** source-block information is assessed using an unregularised Schur-complement residual Gram matrix after projection on all other source/context/intercept features. Ridge is excluded from this diagnostic and cannot manufacture rank.
5. **Candidate lifecycle:** an observed residual alarm starts candidate collection. The candidate is fitted on a post-alarm training segment and compared with the incumbent on a subsequent, disjoint sequential validation segment. Promotion requires conditional identifiability and held-out improvement; rejection preserves the incumbent.
6. **Memory controls:** C0-C4 costs remain explicit. Current C3/C4 settings are not resource matched; no equal-budget or architecture-winner claim is allowed.

## One-workflow concurrent execution

One GitHub Actions workflow fans out six independent package jobs concurrently: M3-A context routing, M3-B joint learning/identifiability, M3-C effective activation, M3-D candidate revision, M3-E memory controls, and M3-I integrated sequential probe. Python 3.10 and 3.12 full-suite jobs run alongside the six package jobs. One aggregate waits for all eight jobs, verifies the exact six package artifacts, and reports scientific checks separately from execution status.

M3-I is concurrent because it runs the integrated implementation in its own clean job; it does not consume mutable outputs from another package job. The jobs are six independent evaluations of a single committed implementation snapshot, not a serial set of refinement campaigns.

## Learner/evaluator boundary

The learner receives only current source vectors, the current context observation and decision, and the target after prediction. The synthetic generator retains its operator-change and context-switch schedule. Schedule labels and true operators are never passed into estimator, activation, detector or revision calls. Candidate fitting and subsequent validation use disjoint chronological segments.

## Interpretation ceiling

This is one deterministic integration-refinement campaign. Passing package execution means only that each probe ran and emitted valid evidence. Scientific checks may pass or fail and must be reported as measurements. This campaign does not establish held-out relation-composition generalisation, broad drift calibration, causal attribution, C0-C4 superiority, or global adaptive-network stability. Whole-network coupled stability remains M4.

**Protocol frozen:** no.  
**M3 investigation authorised:** yes.  
**M3 scientific outcome:** open.
