# LG-01A Experiment Ledger

**Experiment:** LG-01A — Transient Mode Behaviour  
**Protocol:** LG-01A-v0.1  
**Status:** Specified; implementation not started; no runs recorded  
**Opened:** 2026-11-14

## 1. Purpose and claim boundary

Record whether fixed fast multidimensional leaky modes remain active under continuing bounded information refresh while individual tagged contributions decay. The experiment does not evaluate graph formation, routing, slow-history registration, adaptation or reasoning.

The conventional SOE auxiliary-state equation is the null baseline. If it matches the proposed lepto-mode equations, LG-01A validates only the operating premise and not a distinct primitive.

## 2. Frozen protocol snapshot

- Feature dimension: 16.
- Four vector channels with \(\gamma=(0.01,0.05,0.2,0.8)\).
- \(\gamma=0.01\) is the slow reference; 0.05, 0.2 and 0.8 are the fast test rates.
- 30 paired seeds: 101–130.
- Exact zero-order-hold update, \(\Delta t=0.125\), float64.
- Unit-norm tagged pulse; bounded seeded refresh input in \(\mathbb R^{16}\).
- Arms: pulse-only/no refresh, continuous refresh, matched-energy intermittent refresh, matched refresh-only shadows, conventional SOE null.
- Per-mode horizon: \(8\tau\) refresh pre-roll, \(4\tau\) observation after tag injection, then \(3\tau\) washout.
- Confirmation criteria and falsification rules are frozen in the LG-01A protocol.

No route, edge, slow-history registration, structural growth or Grassmannian update is allowed.

## 3. Decision and change log

### 2026-11-14 — LG-01A protocol opened

- Defined LG-01A as a transient-mode viability experiment, not a graph-emergence experiment.
- Reused the repository's 16-dimensional feature space and fixed four-rate SOE bank for continuity with the existing E-series.
- Separated the tagged historical contribution from the refresh-driven state analytically, so rapid decay and continuing activity can be measured independently.
- Added an equal-energy intermittent-refresh control and a conventional SOE null baseline.
- Set the pass rule over all three fast rates and 30 paired seeds. A partial pass does not silently narrow the declared parameter range.
- Recorded that an SOE-identical outcome is expected and does not establish novelty.

## 4. Run ledger

No runs have been executed.

| Run ID | Date | Source commit | Protocol | Seeds | Status | Artifact / hashes | Decision |
|---|---|---|---|---|---|---|---|
| — | — | — | LG-01A-v0.1 | 101–130 | Not run | — | Pending implementation |

## 5. Required run record

Append one subsection per run with:

- run ID and UTC start/end;
- source commit and clean/dirty worktree state;
- exact command, environment and dependency versions;
- protocol version and configuration hash;
- all 30 seed IDs and arm pairing;
- result file inventory and SHA-256 hashes;
- per-seed results and aggregate intervals;
- pass counts at each fast rate;
- any deviation, exclusions and reason;
- interpretation bounded by the registered question;
- one decision: pass, fail, inconclusive or invalid run.

## 6. Next action

Implement a minimal deterministic runner and tests directly from the LG-01A protocol. Validate exact update, analytic tagged decay, boundedness, energy matching, refresh input-response and reproducibility before executing the 30-seed campaign. No result may be entered from a smoke test as though it were a confirmation run.
