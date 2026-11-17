"""Frozen chronological candidate-revision windows for HLG-M3.

The lifecycle accumulates sufficient statistics and losses online. It does not
retain raw window observations, shorten windows, or expose evaluator metadata.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from .revision import CandidateRevision


@dataclass
class CandidateLifecycle:
    """One non-overlapping 32/32/64 candidate lifecycle.

    Caller supplies the residual target after removing the incumbent predictor's
    other terms. Only an observed source/target pair contributes to fitting or
    scoring. The caller supplies the final conditional-identifiability result
    at the end of the validation window.
    """

    revision: CandidateRevision
    source_dimension: int
    target_dimension: int
    fit_slots: int = 32
    validation_slots: int = 32
    post_promotion_slots: int = 64
    minimum_observed_rows: int = 24
    improvement_margin: float = 1e-8
    fit_rcond: float = 1e-10
    phase: str = "IDLE"
    status: str = "NOT_STARTED"
    alarm_step: int | None = None
    next_step: int | None = None
    secondary_alarms: list[int] = field(default_factory=list)
    _incumbent_at_start: np.ndarray | None = field(init=False, default=None)
    _candidate: np.ndarray | None = field(init=False, default=None)
    _fit_gram: np.ndarray = field(init=False)
    _fit_cross: np.ndarray = field(init=False)
    _fit_slots_seen: int = 0
    _fit_observed: int = 0
    _fit_rank: int = 0
    _validation_slots_seen: int = 0
    _validation_observed: int = 0
    _validation_incumbent_sse: float = 0.0
    _validation_candidate_sse: float = 0.0
    _post_slots_seen: int = 0
    _post_observed: int = 0
    _post_incumbent_sse: float = 0.0
    _post_candidate_sse: float = 0.0
    _promoted: bool | None = None

    def __post_init__(self) -> None:
        if self.source_dimension < 1 or self.target_dimension < 1:
            raise ValueError("source and target dimensions must be positive")
        if min(self.fit_slots, self.validation_slots, self.post_promotion_slots) < 1:
            raise ValueError("window lengths must be positive")
        if not 1 <= self.minimum_observed_rows <= min(self.fit_slots, self.validation_slots, self.post_promotion_slots):
            raise ValueError("minimum_observed_rows must fit within every window")
        if self.improvement_margin < 0 or self.fit_rcond <= 0:
            raise ValueError("improvement margin and fit tolerance are invalid")
        expected_shape = (self.target_dimension, self.source_dimension)
        if self.revision.accepted_operator.shape != expected_shape:
            raise ValueError(f"incumbent operator must have shape {expected_shape}")
        self._fit_gram = np.zeros((self.source_dimension, self.source_dimension), dtype=np.float64)
        self._fit_cross = np.zeros((self.target_dimension, self.source_dimension), dtype=np.float64)

    @property
    def is_open(self) -> bool:
        return self.phase in {"FIT", "VALIDATION", "POST_PROMOTION"}

    def start(self, alarm_step: int) -> bool:
        """Begin immediately after alarm_step; never open overlapping lifecycles."""
        if self.phase != "IDLE":
            raise RuntimeError("candidate lifecycle can be started only once per instance")
        if alarm_step < 0:
            raise ValueError("alarm_step must be non-negative")
        self.alarm_step = int(alarm_step)
        self.next_step = int(alarm_step) + 1
        self._incumbent_at_start = self.revision.accepted_operator.copy()
        self.phase = "FIT"
        self.status = "IN_PROGRESS"
        return True

    def record_alarm(self, step_index: int) -> bool:
        """Record a secondary alarm while active; do not start a parallel fit."""
        if step_index < 0:
            raise ValueError("step_index must be non-negative")
        if self.is_open:
            self.secondary_alarms.append(int(step_index))
            return False
        if self.phase == "IDLE":
            return self.start(step_index)
        return False

    def _validate_row(
        self,
        source: Sequence[float] | None,
        residual_target: Sequence[float] | None,
        observed: bool,
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
        if not observed:
            return None, None
        if source is None or residual_target is None:
            raise ValueError("observed rows require source and residual target vectors")
        x = np.asarray(source, dtype=np.float64)
        y = np.asarray(residual_target, dtype=np.float64)
        if x.shape != (self.source_dimension,) or y.shape != (self.target_dimension,):
            raise ValueError("candidate row has an invalid source or target dimension")
        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
            raise ValueError("candidate row contains non-finite values")
        return x, y

    def observe(
        self,
        *,
        step_index: int,
        source: Sequence[float] | None,
        residual_target: Sequence[float] | None,
        observed: bool,
        identifiable: bool = False,
    ) -> dict | None:
        """Consume exactly one chronological time slot.

        Returns a decision record when a lifecycle closes, otherwise None.
        Missing rows occupy their scheduled slot but do not enter any statistic.
        """
        if not self.is_open or self.next_step is None:
            raise RuntimeError("no candidate lifecycle is currently open")
        if int(step_index) != self.next_step:
            raise ValueError(f"expected chronological step {self.next_step}, got {step_index}")
        x, y = self._validate_row(source, residual_target, bool(observed))
        current_step = self.next_step
        self.next_step += 1

        if self.phase == "FIT":
            self._fit_slots_seen += 1
            if x is not None and y is not None:
                self._fit_gram += np.outer(x, x)
                self._fit_cross += np.outer(y, x)
                self._fit_observed += 1
            if self._fit_slots_seen == self.fit_slots:
                return self._finish_fit()
            return None

        if self.phase == "VALIDATION":
            self._validation_slots_seen += 1
            if x is not None and y is not None:
                incumbent_error = y - self._incumbent_at_start @ x
                candidate_operator = self.revision.candidate_operator
                if candidate_operator is None:
                    raise RuntimeError("candidate operator missing during validation")
                candidate_error = y - candidate_operator @ x
                self._validation_incumbent_sse += float(incumbent_error @ incumbent_error)
                self._validation_candidate_sse += float(candidate_error @ candidate_error)
                self._validation_observed += 1
            if self._validation_slots_seen == self.validation_slots:
                return self._finish_validation(bool(identifiable))
            return None

        self._post_slots_seen += 1
        if x is not None and y is not None:
            incumbent_error = y - self._incumbent_at_start @ x
            promoted_operator = self.revision.accepted_operator
            candidate_error = y - promoted_operator @ x
            self._post_incumbent_sse += float(incumbent_error @ incumbent_error)
            self._post_candidate_sse += float(candidate_error @ candidate_error)
            self._post_observed += 1
        if self._post_slots_seen == self.post_promotion_slots:
            return self._finish_post_promotion()
        return None

    def _close(self, status: str) -> dict:
        self.phase = "COMPLETE"
        self.status = status
        result = self.result()
        self._candidate = None
        self._incumbent_at_start = None
        if self.revision.candidate_active:
            self.revision.candidate_operator = None
            self.revision.candidate_active = False
        return result

    def _finish_fit(self) -> dict | None:
        if self._fit_observed < self.minimum_observed_rows:
            return self._close("INSUFFICIENT_EVIDENCE_FIT")
        eigenvalues = np.linalg.eigvalsh(0.5 * (self._fit_gram + self._fit_gram.T))
        scale = max(float(np.max(np.abs(eigenvalues))), 1.0)
        self._fit_rank = int(np.sum(eigenvalues > self.fit_rcond * scale))
        self._candidate = self._fit_cross @ np.linalg.pinv(self._fit_gram, rcond=self.fit_rcond)
        self.revision.start_candidate(self._candidate)
        self._candidate = None
        self.phase = "VALIDATION"
        return None

    def _finish_validation(self, externally_identifiable: bool) -> dict | None:
        if self._validation_observed < self.minimum_observed_rows:
            return self._close("INSUFFICIENT_EVIDENCE_VALIDATION")
        candidate_identifiable = self._fit_rank == self.source_dimension and externally_identifiable
        incumbent_loss = self._validation_incumbent_sse / self._validation_observed
        candidate_loss = self._validation_candidate_sse / self._validation_observed
        self._promoted = self.revision.evaluate(
            incumbent_loss=incumbent_loss,
            candidate_loss=candidate_loss,
            identifiable=candidate_identifiable,
            improvement_margin=self.improvement_margin,
        )
        if not self._promoted:
            return self._close("REJECTED")
        self.phase = "POST_PROMOTION"
        return None

    def _finish_post_promotion(self) -> dict:
        if self._post_observed < self.minimum_observed_rows:
            return self._close("PROMOTED_POST_INSUFFICIENT_EVIDENCE")
        incumbent_loss = self._post_incumbent_sse / self._post_observed
        promoted_loss = self._post_candidate_sse / self._post_observed
        relative_improvement = (
            (incumbent_loss - promoted_loss) / incumbent_loss
            if incumbent_loss > 0 else float("nan")
        )
        return self._close("PROMOTED_EVALUATED")

    def result(self) -> dict:
        """Return window bounds and outcomes without raw learner/evaluator rows."""
        if self.alarm_step is None:
            return {"phase": self.phase, "status": self.status}
        result = {
            "phase": self.phase,
            "status": self.status,
            "alarm_step": self.alarm_step,
            "secondary_alarm_steps": list(self.secondary_alarms),
            "fit_window": {
                "start": self.alarm_step + 1,
                "end": self.alarm_step + self.fit_slots,
                "slots": self._fit_slots_seen,
                "observed_rows": self._fit_observed,
                "design_rank": self._fit_rank,
            },
            "validation_window": {
                "start": self.alarm_step + self.fit_slots + 1,
                "end": self.alarm_step + self.fit_slots + self.validation_slots,
                "slots": self._validation_slots_seen,
                "observed_rows": self._validation_observed,
                "incumbent_loss": (
                    self._validation_incumbent_sse / self._validation_observed
                    if self._validation_observed else None
                ),
                "candidate_loss": (
                    self._validation_candidate_sse / self._validation_observed
                    if self._validation_observed else None
                ),
            },
            "post_promotion_window": {
                "start": self.alarm_step + self.fit_slots + self.validation_slots + 1,
                "end": self.alarm_step + self.fit_slots + self.validation_slots + self.post_promotion_slots,
                "slots": self._post_slots_seen,
                "observed_rows": self._post_observed,
            },
            "promoted": self._promoted,
        }
        if self._post_observed:
            incumbent_loss = self._post_incumbent_sse / self._post_observed
            candidate_loss = self._post_candidate_sse / self._post_observed
            result["post_promotion_window"].update({
                "incumbent_loss": incumbent_loss,
                "promoted_loss": candidate_loss,
                "relative_improvement": (
                    (incumbent_loss - candidate_loss) / incumbent_loss
                    if incumbent_loss > 0 else None
                ),
            })
        return result

    def resource_snapshot(self) -> dict[str, int | str]:
        """Report numeric buffers held by this lifecycle, not Python allocator overhead."""
        # Candidate matrices are owned and counted once by CandidateRevision;
        # the lifecycle stores only its fit statistics and incumbent snapshot.
        candidate_bytes = 0
        incumbent_bytes = (
            int(self._incumbent_at_start.nbytes) if self._incumbent_at_start is not None else 0
        )
        return {
            "fit_gram_bytes": int(self._fit_gram.nbytes),
            "fit_cross_bytes": int(self._fit_cross.nbytes),
            "candidate_operator_bytes": candidate_bytes,
            "incumbent_snapshot_bytes": incumbent_bytes,
            "numeric_buffer_bytes_total": int(
                self._fit_gram.nbytes + self._fit_cross.nbytes + candidate_bytes + incumbent_bytes
            ),
            "window_slots": int(self.fit_slots + self.validation_slots + self.post_promotion_slots),
        }
