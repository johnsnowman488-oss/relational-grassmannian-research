# H1 implementation ledger — five hierarchical workstreams

**Status:** implementation candidate pushed; focused and full CI passed on Python 3.10 and 3.12. Real C++ runtime integration and confirmatory campaign remain pending.
**Base:** `research/h0-shared-hierarchy-contract-soe-bridge`
**Branch:** `research/h1-hla-hlb-five-workstreams`
**H0 contract:** 0.1.0
**H1 schema:** 0.1.0

## Workstream 1 — HLA adapter

- Added a three-level HLA adapter over the shared H0 SOE bridge.
- Upper levels use separately fitted linear readouts (0→1 and 1→2).
- Readout fitting accepts explicitly labelled calibration examples only.
- Missing/unfitted readouts do not fabricate an upper-level prediction.
- HLA has no relation-instance store; exact relational witnesses remain external evidence and are not inferred from readout outputs.

## Workstream 2 — HLB adapter

- Added one canonical relation-record map.
- Added level-scoped secondary indexes by subject and relation type; no per-level duplicate record copies.
- Enforces typed relation instances, immutable IDs, explicit capacity abstention and observation-cutoff retrieval.
- Composition delegates to the existing witness-preserving P0 composer; returned witnesses retain original instance IDs and entity sequence.

## Workstream 3 — persistent runtime integration

- Added a director that validates event and observation times and routes each global tick through exactly one adapter/bridge step.
- Late arrivals retain their original event time and are ingested at current observation time; historical native state is not rewritten.
- HLA rejects relation-store writes.
- Adapter snapshots now include all three Python SOE banks. Composite lifecycle snapshots also include the persistent native runtime checkpoint.

## Workstream 4 — common evaluation runner

- Added explicit fit/validation/confirmatory partition labels.
- The runner refuses to score the fit partition.
- Paired summaries require the same task ID, seed, partition and task order.
- This is a harness primitive, not yet a frozen confirmatory campaign or evidence of HLA/HLB performance.

## Workstream 5 — composite lifecycle and rollback

- Added composite checkpoint fingerprinting over director/adapter/SOE/native state.
- Restore validates architecture, schema, readout dimensions/fingerprints, canonical store capacity/records and SOE configuration before activating state.
- Native restore relies on the M4 runtime's compute-then-commit restore contract.
- Rollback returns to the last trusted composite checkpoint. Promotion increments a version and checkpoints it.

## Validation gates

- Unit tests added for readout fitting, HLA no-store boundary, HLB canonical indexing/capacity, witness preservation, director timing, composite rollback and paired evaluation.
- Dedicated H1 workflow [45712034356](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45712034356): focused H1/H0 tests and full repository suite passed on Python 3.10 and 3.12.
- Repository unit/invariant suite [45712033989](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45712033989): passed on Python 3.10 and 3.12.
- H0 contract/regression workflow [45712034002](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45712034002): passed on Python 3.10 and 3.12.
- G1–G5 development workflow [45712033907](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45712033907): passed on Python 3.10 and 3.12.
- Job 4 A/B integration workflow [45712033972](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45712033972): passed on Python 3.10 and 3.12.
- **Still pending:** actual persistent C++ runtime integration against the production runtime object, end-to-end HLA/HLB matched task campaign, confirmatory partition freeze, and P6 stability acceptance.
- The new implementation does not establish that HLA or HLB is superior. It establishes candidate software interfaces and testable contracts only.

## Important integration boundary

The director expects the persistent native runtime object already used by H0 and a runtime that exposes `checkpoint()` and `restore(checkpoint)`. The actual C++ runtime adapter must be supplied by the integration environment; the H1 fake-runtime tests only test orchestration semantics.
