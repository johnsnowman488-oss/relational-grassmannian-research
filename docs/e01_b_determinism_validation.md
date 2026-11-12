# E01-B deterministic replica audit

This validation branch exists to execute the deterministic codebook correction and cross-run replica gate on the E01-B branch.

The original E01-B CI matrix completed all 228 cells, but two runs disagreed in one `entity_e4 / current / world 402` cell. The per-case artifacts had identical events while the composition threshold differed by many orders of magnitude near numerical residue.

The E01-B implementation now canonicalizes the sign orientation of the seeded QR basis and floors support values below `1e-12` to zero. The workflow repeats the affected cell in two independent CI jobs, compares the full JSON outputs with a `1e-12` numeric tolerance, and requires that comparison to pass before the aggregate 228-cell report is produced.

Acceptance requires identical structure, event streams, labels, thresholds, and predictions, with numeric evidence agreeing within tolerance.
