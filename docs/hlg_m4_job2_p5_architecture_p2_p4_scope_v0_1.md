# M4 Job 2 — P5 architecture comparison and P2-P4 scope decisions (working draft)

**Status:** Initial design result for review; not a frozen implementation contract.
**Parent issue:** [#34](https://github.com/johnsnowman488-oss/relational-grassmannian-research/issues/34)
**Foundation:** [M4 shared scaffold](hlg_m4_shared_foundation_scaffold_v0_1.md)

## 1. Main conclusion

The architecture comparison must test whether a separately persistent relational state contributes measurable value beyond temporal memory with learned relational dynamics, and whether a unified augmented state can provide the same capability at lower or comparable cost. It must not assume that “separate” is inherently better or that “unified” is inherently simpler.

A/B/C are distinguished by update, retention, revision and read/write semantics—not by names or tensor concatenation. The M4 stability envelope and the E09 architecture-value question overlap but are not identical: M4 asks whether the selected coupled adaptive system behaves safely within a bounded operating envelope; E09 makes the broader architecture comparison using inherited evidence.

## 2. Operational architecture hypotheses

### A — SOE-only with learned relational dynamics/readout

Persistent state is temporal state (s_t). There is no separately addressable persistent relational store (z_t). Relational behaviour must be encoded and retrieved through the temporal state transition and learned query-conditioned readout:
\[
s_{t+1}=F_A(s_t,o_t),\qquad \hat y_t=H_A(s_t,q_t).
\]
A model may internally form relational features, but if they are not separately persisted, revised or queried under a distinct state contract, they remain part of A.

### B — coupled temporal and relational state

Temporal state (s_t) and relational state (z_t) have separately specified persistence/update semantics and explicit coupling:
\[
s_{t+1}=F_s(s_t,z_t,o_t),\qquad
z_{t+1}=F_z(z_t,s_t,o_t).
\]
Queries may read both states through a defined interface. The contract must state which observations update which state, how relation evidence is consolidated, how context gates access, and how revision/dormancy/rollback affect each state. Merely storing two arrays is insufficient.

### C — unified augmented state

One persistent state (u_t) is jointly updated:
\[
u_{t+1}=F_C(u_t,o_t).
\]
The implementation may contain structured coordinates or subspaces, but it has no independently maintained relational state lifecycle unless the contract effectively makes it B. C must specify how relational organisation is retained, selected and revised within the unified update.

### R — relational-only reference

A relational memory/reference without the temporal mechanism under study. It helps quantify the contribution of temporal persistence and provides a task-specific lower/reference point. It is not assumed to be resource-equivalent by default; budgets must be disclosed.

## 3. Comparison protocol

### Match the information conditions first

All variants must receive identical:
- observation streams, timestamps and missingness signals;
- query schedule and query wording;
- supervision, feedback and update opportunities;
- entity/relation inventories and split assignments;
- task seeds, world-level train/validation/test partitions.

No architecture may receive hidden witnesses, extra labels or privileged future information.

### Resource fairness

Report and, where feasible, match:
- persistent state capacity (both raw and effective/active);
- trainable parameter count;
- numeric precision and quantisation;
- per-observation update budget;
- per-query compute and latency;
- memory traffic and retained metadata;
- detector/candidate-control overhead;
- wall-clock and total operation counts.

Because exact equality across fundamentally different state organisations may be artificial, use two views:
1. matched-budget comparisons at common resource points;
2. resource-performance curves showing capability/stability against state, parameter and compute cost.

Report resource differences rather than silently compensating one architecture with hidden extra compute.

### Outcomes

Primary outcomes should be task-layer metrics from P0 plus:
- old-relation retention under controlled revision;
- false relation activation and false-path rate;
- collateral damage to unrelated relations;
- detection-to-promotion efficiency;
- rollback/recovery success;
- state/resource growth and query/update cost;
- transient amplification and stability diagnostics from P6.

Do not collapse capability, stability and efficiency into one score without also reporting each separately.

## 4. C0-C4 reuse decision

The existing C0-C4 controls are the starting comparison family. The initial audit should map each existing control's actual update/readout behaviour to A/B/C/R and identify:
- which variant it instantiates;
- which state and resource budgets it uses;
- which ablations already exist;
- which task semantics and metrics it supports;
- whether its interface is adequate for the new P0 witness contract.

Do not rebuild C0-C4 wholesale. Extend only where the current interface cannot express the P0 composition witness, P6 transition instrumentation or fair resource accounting. If a control must change, preserve the original result and label the extension as a new version.

## 5. P2 — bounded relational acquisition

**Working scope decision: defer unrestricted topology discovery.** M4 should not become an open-ended relation-birth/death campaign. A bounded acquisition challenge may be included only if P6 shows that the coupled stability claim depends on the system admitting a previously unseen but bounded candidate relation/context.

If included, constrain it to:
- a fixed maximum candidate pool and fixed resource ceiling;
- a declared candidate-generation mechanism;
- no hidden answer schema or direct evaluator witness;
- independent validation before promotion;
- false-structure and collateral-damage accounting.

Metrics: candidate precision/recall, false-structure rate, time-to-detection, promotion precision, post-promotion old-knowledge damage, and resource overhead. If the stability question can be tested with the existing bounded candidate topology, defer P2 to E04/E09 and state that limitation.

## 6. P3 — missingness, interruption and recovery

Do not duplicate M3's missingness/outage coverage. The P3 audit must map existing tests into:
1. learning under corrupted/missing observations;
2. retaining learned state through a period of no observations;
3. reactivation after dormancy;
4. recovery after changed or degraded observations;
5. recovery after an incorrect candidate promotion or rollback.

The M4-specific minimal challenge should be the smallest uncovered case needed to validate the P6 mode transitions. In particular, a candidate-promotion/rollback sequence may be more informative than another generic outage test. Do not claim arbitrary-interruption robustness from a finite synthetic suite.

## 7. P4 — transfer boundary

**Working scope decision: broad cross-domain transfer remains deferred to E08.** M4 may need one structurally distinct stress condition only if the proposed stability theorem/claim depends on assumptions that a single synthetic family cannot test. That condition should challenge the stability envelope (e.g. changed observation noise or relation fan-out) without becoming a broad transfer campaign.

If no specific P6 assumption requires it, do not add a new domain. Explicitly state that the M4 stability envelope is established only within the declared synthetic operating family.

## 8. Proposed sequence

1. Audit C0-C4 actual code and contracts against the scaffold.
2. Map each to A/B/C/R without changing benchmark semantics.
3. Write the matched-information and resource contract.
4. Complete P2-P4 include/defer decisions using the actual P6 proof obligations and M3 coverage, not intuition.
5. Freeze interfaces only after Job 1 supplies the P0 witness/task contract and Job 3 supplies the state-transition needs.

## 9. Open questions

- Which C0-C4 controls are truly A/B/C/R, based on implementation rather than naming?
- Does any current C0-C4 condition already provide a valid multi-hop relational witness?
- Is separately persisted relational state independently resettable/revisable in B, and can C express equivalent semantics?
- Which resource dimensions are feasible to match exactly in the existing harness?
- Does P6 require a new relation acquisition transition, or can the bounded candidate set suffice?
- Which specific M3 recovery tests cover each P3 category?

## 10. Current result

P5 now has operational architecture definitions and a fair-comparison outline. P2/P3/P4 have provisional scope positions: unrestricted acquisition deferred, only uncovered recovery transitions added, broad cross-domain transfer deferred unless a named stability assumption requires a bounded stress condition. These are provisional until verified against actual C0-C4 code, M3 evidence and P6 analysis. No implementation or experiment is claimed.
