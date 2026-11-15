# HLG-M3 implementation campaign plan

**Campaign:** HLG-M3-IMPLEMENTATION-v0.1  
**Authorisation:** GO — M3 investigation authorised  
**Protocol:** v0.1, amendable  
**Claim level:** first executable reference implementation and integration smoke; not complete M3 validation

## Execution design

Run five independent component jobs (M3-A to M3-E) concurrently. Run M3-I only after all five complete. Run the full repository test suite concurrently on Python 3.10 and 3.12. An aggregate job waits for all six work-package artifacts and both test jobs.

| Work package | Primary evidence file | Dependencies |
|---|---|---|
| M3-A | M3-A.json | shared contract only |
| M3-B | M3-B.json | shared contract only |
| M3-C | M3-C.json | shared contract only |
| M3-D | M3-D.json | shared contract only |
| M3-E | M3-E.json | shared contract only |
| M3-I | M3-I.json | M3-A to M3-E |

## Aggregate interpretation

The aggregate verifies exactly six package IDs, valid JSON, matching campaign identity and successful execution of the declared smoke checks. It must also record implementation_protocol_frozen=false and m3_scientific_validation_complete=false.

Execution failure, scientific probe failure, missing evidence and protocol readiness are distinct states. A green CI workflow does not establish held-out generalisation, calibrated context identity, causal relation attribution, memory architecture superiority or global adaptive stability.

## Next campaign beyond v0.1

After reviewing this first integrated slice, expand the same interfaces into the existing eight-world family with independent training/validation/test seeds and genuinely held-out relation compositions. Add correlation sweeps, noisy context boundaries, missing-observation intervals, multiple simultaneous relation groups, abrupt/gradual/variance/transient drift, and measured C0-C4 memory interference and Pareto comparisons. Keep M4 global coupled stability outside M3.
