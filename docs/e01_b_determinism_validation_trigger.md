# E01-B determinism validation trigger

The E01-B branch contains the QR sign canonicalization, numerical support floor, unit tests, and a two-run cross-worker comparison. This small stacked change requests execution of that validation workflow against the E01-B branch before the frontier result is treated as stable.

The target is the previously divergent entity-E4/current/world-402 cell. The comparison includes complete event records, labels, validation thresholds, scores and predictions.