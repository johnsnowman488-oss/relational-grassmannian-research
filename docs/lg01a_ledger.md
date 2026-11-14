# LG-01A Experiment Ledger

**Experiment:** LG-01A — Transient Mode Behaviour  
**Protocol:** LG-01A-v0.1  
**Status:** Implemented; 30-seed campaign complete; valid scientific fail under LG-01A-v0.1  
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

### LG-01A / GitHub Actions campaign

| Field | Recorded value |
|---|---|
| Run ID | lg01a_43652121470_1 |
| Workflow | https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/43652121470 |
| Artifact | lg01a-43652121470-1; artifact ID 14136786352 |
| Source branch / commit | research/lgdh-lg01a-spine / 5fd9b5169bda1617ad3093d5bcd6f5b2877a44a0 |
| Protocol / configuration | LG-01A-v0.1 / SHA-256 f7b6a940c95e443351ca2779f58d75dc3a103fa685cd9d2a1303530189c91e89 |
| Seeds / rates | 101–130 (30 paired seeds); 0.01, 0.05, 0.2, 0.8 |
| Runtime | Python 3.12.16, NumPy 2.5.4, SciPy 1.18.1, Ubuntu x86_64 |
| Execution interval | 2026-11-14 23:13:56–23:14:09 UTC |
| Status | Runner completed; artifact uploaded; pre-registered scientific gate failed |
| Decision | FAIL — fast rate 0.8 does not meet the 27/30-seed activity gate |

The dedicated GitHub workflow's Python 3.10 and 3.12 full-suite jobs both passed: 122 tests passed in each environment. The campaign command completed and the result bundle uploaded. The workflow is marked failed because it intentionally propagates the failed scientific gate after preserving the artifact; this is not a runner crash or an invalid run.

### Results

| Decay rate | Role | Seeds passing the per-seed window criterion | Mean activity ratio (95% CI) | Mean reference ratio (95% CI) | Gate |
|---:|---|---:|---:|---:|---|
| 0.01 | Slow reference | 30/30 (not a fast-rate gate) | 84.5641 [80.7515, 88.3766] | 0.99977 [0.99912, 1.00043] | Reference |
| 0.05 | Fast | 30/30 | 34.5572 [33.2518, 35.8626] | 0.99819 [0.99550, 1.00088] | Pass |
| 0.20 | Fast | 30/30 | 18.4591 [17.2169, 19.7013] | 1.00468 [0.99945, 1.00991] | Pass |
| 0.80 | Fast | 26/30 | 9.26482 [8.84306, 9.68658] | 1.01451 [1.00660, 1.02242] | FAIL |

The four seeds that fail the per-seed threshold of at least 90% passing activity windows at gamma=0.8 are 105, 112, 114 and 116. Seven windows fail in total:
- seed 105: activity ratio 4.8285, reference ratio 1.0570 (one window);
- seed 112: activity ratios 3.5443, 4.1496 and 4.7707; reference ratios 1.0169, 1.0236 and 1.0222 (three windows);
- seed 114: activity ratios 4.1427 and 4.6597; reference ratios 0.9975 and 1.0301 (two windows);
- seed 116: activity ratio 4.9484, reference ratio 1.0009 (one window).

All missed windows are below the frozen activity-ratio threshold of 5.0; their reference-tracking ratios remain within [0.8, 1.2]. The aggregate mean activity ratio does not override the per-window/per-seed gate.

### Mathematical and reproducibility checks

- Tagged-contribution decay and residual at 3 tau: passed; residual is approximately exp(-3)=0.0497871.
- Post-refresh washout at 3 tau: passed; approximately 0.0497871.
- Exact input-perturbation response: passed.
- Analytic boundedness envelope and finite-state checks: passed for all arms, rates and seeds.
- Continuous vs. intermittent refresh total input energy: exact match; maximum absolute energy difference 0.
- Candidate vs. independently stepped conventional SOE null: passed; maximum relative trace difference 2.02055e-15, below tolerance 1e-10.
- Full run bundle checksum verification: all entries in SHA256SUMS verified.

The result shows that the tested candidate dynamics are reproducible as conventional leaky-SOE dynamics. It does not distinguish a distinct lepto-mode primitive.

### Artifact hashes

The authoritative bundle contains config.json, seed_metrics.csv, window_metrics.csv, null_comparison.csv, trace_samples.jsonl, summary.json, summary.md, run_manifest.json and SHA256SUMS.

Selected SHA-256 entries:
- seed_metrics.csv: 407fb97eb3c8539396258c4264885972b5e2bccf101b7487717c918c2824178c
- window_metrics.csv: 6fb2ca1fec8e2898fcf290a583a02044e6d255ea5621797e90fa0929e8985b58
- summary.json: 890c3eb64d9a173632a012825741c287d17e69373f60fd88982faa13eb6b60b1
- trace_samples.jsonl: a21b042be502e9cd39605f8256004801555e9c1bc2497fcff571e6c03139164e

A same-protocol campaign was also launched from workflow-only commit b29a6df4b81653c0ac1055d068dee5ecdee40183 as run 43652352159. It is tracked separately from the canonical source-code run above.

## 5. Interpretation and next decision

LG-01A-v0.1 is a valid negative result for the declared rate range: the activity requirement is met at 0.05 and 0.2, but not at 0.8 under the frozen 27-of-30 seed rule. This is not evidence that transient refresh is impossible in general; it falsifies the current operational threshold for the fastest tested mode under this input protocol. No seed was excluded and no acceptance threshold was changed after observing the data.

Do not proceed to LG-01B yet. First review whether the intended lepto-mode function requires the fastest tested timescale, whether the refresh-input scale and window threshold reflect a defensible operational definition, and whether a revised question is needed. Any revised rate range, input scaling or activity criterion requires a dated LG-01A-v0.2 protocol, a reasoned mathematical justification, and a fresh independent confirmation campaign. Do not relabel this v0.1 failure as a pass.

## 6. Next action

Retain the runner, tests and v0.1 result as a reproducible baseline. Resolve the fast-rate failure scientifically before proposing a protocol revision. LG-01B remains blocked until this decision is made and the corresponding gate is honestly closed.
