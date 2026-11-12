# E01-B determinism validation trigger

This branch carries the E01-B frontier implementation and its deterministic-codebook correction. The initial 228-cell run exposed one inconsistent entity-E4/current/world-402 threshold caused by QR sign ambiguity and tiny positive support residuals.

The corrected implementation canonicalizes QR column signs and suppresses support values below 1e-12. CI repeats the affected cell in two independent jobs, compares complete per-sequence outputs within 1e-12 numeric tolerance, and gates the 228-cell summary on that check.