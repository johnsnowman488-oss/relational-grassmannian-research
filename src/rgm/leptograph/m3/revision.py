"""Bounded drift detection and two-phase candidate operator revision."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence
import numpy as np

@dataclass
class CUSUMDetector:
    allowance: float = 0.25
    threshold: float = 5.0
    statistic: float = 0.0
    observations: int = 0
    alarms: int = 0

    def __post_init__(self) -> None:
        if self.allowance < 0 or self.threshold <= 0:
            raise ValueError("CUSUM allowance must be non-negative and threshold positive")

    def update(self, residual_score: float) -> bool:
        if not np.isfinite(residual_score):
            raise ValueError("residual_score must be finite")
        self.statistic = max(0.0, self.statistic + float(residual_score) - self.allowance)
        self.observations += 1
        alarm = self.statistic >= self.threshold
        if alarm:
            self.alarms += 1
            self.statistic = 0.0
        return alarm

@dataclass
class CandidateRevision:
    """Keep accepted parameters untouched until a candidate passes all gates."""
    accepted_operator: np.ndarray
    candidate_operator: np.ndarray | None = None
    candidate_active: bool = False
    revision_count: int = 0
    rejection_count: int = 0
    history: list[dict[str, float | bool | str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.accepted_operator = np.asarray(self.accepted_operator, dtype=float).copy()
        if self.accepted_operator.ndim != 2 or not np.all(np.isfinite(self.accepted_operator)):
            raise ValueError("accepted_operator must be a finite matrix")

    def start_candidate(self, operator: Sequence[Sequence[float]]) -> None:
        candidate = np.asarray(operator, dtype=float)
        if candidate.shape != self.accepted_operator.shape or not np.all(np.isfinite(candidate)):
            raise ValueError("candidate operator shape must match accepted operator")
        self.candidate_operator = candidate.copy()
        self.candidate_active = True

    def evaluate(self, *, incumbent_loss: float, candidate_loss: float,
                 identifiable: bool, improvement_margin: float = 1e-8) -> bool:
        if not self.candidate_active or self.candidate_operator is None:
            raise RuntimeError("no candidate revision is active")
        if not np.isfinite(incumbent_loss) or not np.isfinite(candidate_loss):
            raise ValueError("candidate losses must be finite")
        if improvement_margin < 0:
            raise ValueError("improvement_margin must be non-negative")
        improved = candidate_loss < incumbent_loss - improvement_margin
        promoted = bool(identifiable and improved)
        self.history.append({
            "incumbent_loss": float(incumbent_loss), "candidate_loss": float(candidate_loss),
            "identifiable": bool(identifiable), "improved": bool(improved),
            "promoted": promoted, "decision": "PROMOTED" if promoted else "REJECTED",
        })
        if promoted:
            self.accepted_operator = self.candidate_operator.copy()
            self.revision_count += 1
        else:
            self.rejection_count += 1
        self.candidate_operator = None
        self.candidate_active = False
        return promoted
