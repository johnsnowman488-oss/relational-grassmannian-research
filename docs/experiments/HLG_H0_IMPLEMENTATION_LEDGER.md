# H0 Implementation Ledger — Shared HLA/HLB Contract and SOE Bridge

**Status:** H0 contract and bridge implementation complete; architecture adapter adoption remains pending.
**Branch:** research/h0-shared-hierarchy-contract-soe-bridge
**PR:** #47 (draft; no merge requested)
**Implementation head:** ea6c043a280497338b60fe917c9926279c929a7b
**Contract version:** 0.1.0
**Bridge schema version:** 0.1.0

## Delivered

- Shared three-level roles: grounding, relational abstraction, context/control.
- Frozen initial bidirectional chain topology: 0→1→2 bottom-up and 2→1→0 top-down.
- Fixed common timestep and explicit silent ticks for gaps.
- Event-time and observation-time separation; late arrivals do not rewrite prior native states.
- Architecture boundary: HLA uses learned upper-level readouts without persistent relation stores; HLB preserves typed relations and witness references through the hierarchy.
- SOE channel matrix (L,D) embeds losslessly into native u of length L*D using row-major order.
- Native chi is kept separate from SOE channels.
- Native u after stepping is explicitly treated as native evolved hierarchy state, not as a reconstructed Python SOE bank.
- Bridge validates all inputs before mutation, computes candidate SOE updates on copies, makes one native step per global tick, and commits Python SOE state only after native step success.
- Three-level native chain-spec builder checks dimensions, finite values, positive weights and descending native gamma order.

## Representation decision

The Python SOE memory bank and native custom-chain hierarchy are different dynamical systems. The bridge does not claim numerical equivalence. The lossless operation is only the row-major embedding/reshape. Python SOE banks remain architecture-owned state; native u/chi/kernels remain native-owned state.

This avoids changing the already-tested flat M4 A/B reference implementation or expanding the native ABI to mimic a matrix-valued SOE trace bank.

## Validation evidence

All required workflows completed successfully on the final implementation head:

| Workflow | Run | Result |
|---|---:|---|
| Full repository unit/invariant suite, Python 3.10 | [45182678406](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45182678406) | 371 passed |
| Full repository unit/invariant suite, Python 3.12 | [45182678406](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45182678406) | 371 passed |
| Dedicated H0 contract/bridge workflow, Python 3.10 and 3.12 | [45182678630](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45182678630) | Both passed |
| Existing G1–G5 development campaign, Python 3.10 and 3.12 | [45182678412](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45182678412) | Both passed |
| Existing Job 4 A/B integration, Python 3.10 and 3.12 | [45182679469](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/45182679469) | Both passed |

The full suite collected 371 tests and passed on both Python versions. The dedicated H0 workflow also ran the complete suite and passed on both versions.

An earlier run exposed one test-fixture inconsistency: a silent-cycle test pre-populated the SOE banks but left the fake native u state at zero. The fixture was corrected to initialise native u from the same SOE snapshot, matching the contract. The final runs above are green.

## Acceptance status

- H0-01 shared versioned contract/topology: **PASS**
- H0-02 reversible SOE embedding: **PASS**
- H0-03 validation before state mutation: **PASS**
- H0-04 one native step per cycle: **PASS**
- H0-05 silent-cycle semantics: **PASS**
- H0-06 native evolved u distinguished from Python SOE: **PASS**
- H0-07 fake-runtime synchronisation and failure-atomicity tests: **PASS**
- H0-08 HLA and HLB adapters both consume the common API: **PENDING** — the shared bridge is architecture-neutral, but the separate HLA/HLB adapter work packages have not yet been implemented against it.

## Next

Proceed to the parallel implementation work packages:
1. HLA hierarchical adapter and learned upper-level readouts.
2. HLB hierarchical persistent relation store and witness-preserving composition.
3. Native runtime bridge integration into the execution director and composite checkpoint.
4. Common hierarchical task/evaluation runner.
5. P6 composite lifecycle and rollback.

Do not use the existing flat confirmatory test partition to tune the hierarchical adapters. Freeze new validation and confirmatory partitions before the new hierarchical campaign.
