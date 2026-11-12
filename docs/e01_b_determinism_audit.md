# E01-B deterministic replica audit

## Why this audit was added

The first E01-B matrix completed, but its two CI executions disagreed in one cell:
`entity_e4 / current / world 402`.

The two artifacts had identical event records, but the composition threshold differed from approximately `1.08e-17` to `0.3975`, producing a 1.25 percentage-point accuracy difference. The support scores were otherwise numerically almost identical. This points to a threshold instability around tiny floating-point residuals, not a change in the generated synthetic world.

For four entities, the seeded relation-1 codebook is generated with QR decomposition. QR bases have a column-sign ambiguity. The implementation now canonicalizes signs using the diagonal of R. The support tensor also maps values below `1e-12` to zero before clipping, preventing numerical residue from becoming a threshold candidate.

## Validation added

The E01-B workflow now:

1. Repeats the previously divergent `entity_e4 / current / world 402` cell in two independent CI jobs.
2. Uploads both full per-sequence JSON outputs.
3. Compares all fields recursively, allowing only `1e-12` absolute/relative numeric tolerance.
4. Gates the 228-cell summary job on a successful determinism comparison.

The audit is intentionally a cross-run comparison rather than two executions in one Python process. It checks generated events, validation thresholds, scores, predictions and all recorded evidence.

## Acceptance

The audit passes only if both outputs are structurally equal and all numeric fields agree within tolerance. Any prediction, label, event, threshold or material score difference fails the workflow.
