"""P6 lifecycle adapter for the integrated A/B system.

The controller snapshots and restores the complete architecture state, not
only a candidate operator. Stability claims remain finite-horizon and tied to
the declared input envelope.
"""
from __future__ import annotations
from dataclasses import dataclass
import copy
import numpy as np
from rgm.leptograph.m3.revision import CUSUMDetector

@dataclass
class M4AdaptiveController:
    system: object
    threshold: float = 24.0
    allowance: float = 0.2
    mode: str = "NORMAL"
    detector: CUSUMDetector | None = None
    trusted_snapshot: dict | None = None
    candidate_weights: np.ndarray | None = None
    revision_count: int = 0
    rejection_count: int = 0
    rollback_count: int = 0

    def __post_init__(self):
        self.detector = CUSUMDetector(allowance=self.allowance, threshold=self.threshold)

    def observe_residual(self, residual_score: float) -> bool:
        alarm = self.detector.update(float(residual_score))
        if alarm and self.mode in {"NORMAL", "DORMANT"}:
            self.mode = "DETECT"
        return alarm

    def start_candidate(self, weights):
        if self.mode not in {"NORMAL", "DETECT", "RECOVERY"}:
            raise RuntimeError("candidate cannot start in current lifecycle state")
        candidate = np.asarray(weights, dtype=float)
        if candidate.shape != self.system.readout_weights.shape or not np.all(np.isfinite(candidate)):
            raise ValueError("candidate weights must be finite and match the architecture readout")
        self.trusted_snapshot = copy.deepcopy(self.system.snapshot())
        self.candidate_weights = candidate.copy()
        self.mode = "FIT"

    def validate_candidate(self, incumbent_loss: float, candidate_loss: float, identifiable: bool) -> bool:
        if self.mode != "FIT" or self.candidate_weights is None:
            raise RuntimeError("no candidate is being fitted")
        if not np.isfinite(incumbent_loss) or not np.isfinite(candidate_loss):
            raise ValueError("validation losses must be finite")
        self.mode = "VALIDATE"
        promoted = bool(identifiable and candidate_loss < incumbent_loss - 1e-8)
        if promoted:
            self.system.readout_weights = self.candidate_weights.copy()
            self.system.readout_fitted = True
            self.revision_count += 1
            self.mode = "PROMOTED"
        else:
            self.rejection_count += 1
            self.mode = "NORMAL"
        self.candidate_weights = None
        return promoted

    def rollback(self):
        if self.mode != "PROMOTED" or self.trusted_snapshot is None:
            raise RuntimeError("rollback requires a promoted candidate and trusted snapshot")
        self.system.restore(copy.deepcopy(self.trusted_snapshot))
        self.rollback_count += 1
        self.mode = "ROLLBACK"

    def enter_dormancy(self):
        if self.mode not in {"NORMAL", "DETECT"}:
            raise RuntimeError("cannot enter dormancy during candidate lifecycle")
        self.mode = "DORMANT"

    def reactivate(self):
        if self.mode != "DORMANT":
            raise RuntimeError("system is not dormant")
        self.mode = "RECOVERY"

    def finish_recovery(self):
        if self.mode != "RECOVERY":
            raise RuntimeError("system is not recovering")
        self.mode = "NORMAL"

    def lifecycle_snapshot(self):
        return {
            "mode": self.mode,
            "detector": copy.deepcopy(self.detector.__dict__),
            "trusted_snapshot": copy.deepcopy(self.trusted_snapshot),
            "candidate_weights": None if self.candidate_weights is None else self.candidate_weights.copy(),
            "revision_count": self.revision_count,
            "rejection_count": self.rejection_count,
            "rollback_count": self.rollback_count,
        }
