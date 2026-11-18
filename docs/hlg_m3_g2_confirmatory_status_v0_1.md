# HLG-M3 G2 confirmatory status correction

**Status:** G2 confirmatory campaign executed; M3 remains open.  
**Canonical workflow:** [44146576208](https://github.com/johnsnowman488-oss/relational-grassmannian-research/actions/runs/44146576208)  
**Execution commit:** `65b3db7a8a548bbc0c08bca477d34ab88b80895f`  
**Frozen manifest SHA-256:** `8548f2a72de09a81f79a57a19b3cd8196dbeae185db9432619e6ac5cc2f49101`  
**Aggregate evidence SHA-256:** `61d48145f0d46b65373bd2b6290e41b2f9afe5f388d261032be24c1837b6a177`

## Correct current status

| Item | Result |
|---|---|
| Confirmatory execution | 200 streams across 20 held-out worlds; executed |
| Capability gate | Passed: +54.49%; 95% world-clustered CI 49.34%–59.73%; 20/20 positive worlds |
| Adaptation gate | Failed: -0.28%; CI -0.80%–0%; 0/20 positive worlds |
| Resource gate | Passed |
| M3 scientific validation | Incomplete; final decision report remains open |
| M4 authorisation | Not authorised |

## Reporting discrepancy

The readiness aggregate produced by the same workflow contains the decision label `G2_IMPLEMENTATION_READY; CONFIRMATORY_RUN_NOT_YET_TRIGGERED`. That label describes the pre-execution readiness snapshot, but it is stale when carried into the post-execution aggregate alongside the completed confirmatory results.

Do not edit or reinterpret the historical readiness artifact. The current status is the confirmatory aggregate above: `G2_CONFIRMATORY_EXECUTED; CAPABILITY_AND_RESOURCE_GATES_PASSED; ADAPTATION_GATE_FAILED; M3_OPEN; M4_NOT_AUTHORISED`.

This correction changes no generator, learner, detector, threshold, manifest, test allocation, scientific gate or historical result. It does not trigger or require another 200-stream campaign.
