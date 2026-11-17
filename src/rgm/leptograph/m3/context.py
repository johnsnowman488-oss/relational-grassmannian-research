"""Bounded metric-aware context memory with explicit abstention semantics."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

import numpy as np


class ContextDecision(str, Enum):
    ACCEPT = "ACCEPT"
    ABSTAIN = "ABSTAIN"
    NOVEL = "NOVEL"


@dataclass
class ContextSlot:
    slot_id: int
    mean: np.ndarray
    scatter: np.ndarray
    count: int = 1
    novelty_hits: int = 0

    def update(self, point: np.ndarray) -> None:
        """Welford-style online mean/scatter update (population covariance)."""
        x = np.asarray(point, dtype=float)
        if x.shape != self.mean.shape or not np.all(np.isfinite(x)):
            raise ValueError("context point has invalid shape or non-finite values")
        old_mean = self.mean.copy()
        self.count += 1
        self.mean += (x - self.mean) / self.count
        self.scatter += np.outer(x - old_mean, x - self.mean)

    @property
    def covariance(self) -> np.ndarray:
        if self.count <= 1:
            return self.scatter.copy()
        return self.scatter / max(1, self.count - 1)


@dataclass
class ContextBank:
    """A fixed-capacity context bank.

    Scores use a regularised Mahalanobis term plus a generalised log-volume
    term. A full bank abstains; it never silently evicts an existing slot.
    Novel contexts require repeated observations before a slot is created.
    """

    metric: np.ndarray
    capacity: int = 8
    regularisation: float = 1e-6
    accept_threshold: float = 8.0
    novelty_threshold: float = 16.0
    ambiguity_margin: float = 0.25
    novelty_repeats: int = 3
    full_bank_policy: str = "abstain"
    slots: list[ContextSlot] = field(default_factory=list)
    _next_id: int = 0
    _pending: list[np.ndarray] = field(default_factory=list)
    _relation_operators: dict[int, dict[str, np.ndarray]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.metric = np.asarray(self.metric, dtype=float)
        if self.metric.ndim != 2 or self.metric.shape[0] != self.metric.shape[1]:
            raise ValueError("metric must be square")
        if not np.all(np.isfinite(self.metric)) or not np.allclose(self.metric, self.metric.T):
            raise ValueError("metric must be finite and symmetric")
        if np.min(np.linalg.eigvalsh(self.metric)) <= 0:
            raise ValueError("metric must be positive definite")
        if self.capacity < 1 or self.regularisation <= 0 or self.novelty_repeats < 1:
            raise ValueError("capacity, regularisation and novelty_repeats must be positive")
        if self.full_bank_policy not in {"abstain", "nearest_reuse"}:
            raise ValueError("full_bank_policy must be 'abstain' or 'nearest_reuse'")
        if self.novelty_threshold < self.accept_threshold:
            raise ValueError("novelty_threshold must be >= accept_threshold")

    @property
    def dimension(self) -> int:
        return int(self.metric.shape[0])

    def _score(self, point: np.ndarray, slot: ContextSlot) -> float:
        delta = point - slot.mean
        metric_inverse = np.linalg.solve(self.metric, np.eye(self.dimension))
        covariance = slot.covariance + self.regularisation * metric_inverse
        sign, logdet_product = np.linalg.slogdet(self.metric @ covariance)
        if sign <= 0:
            raise np.linalg.LinAlgError("generalised context covariance is not positive definite")
        return float(delta @ np.linalg.solve(covariance, delta) + logdet_product)

    def score(self, point: Sequence[float], slot_id: int) -> float:
        x = np.asarray(point, dtype=float)
        if x.shape != (self.dimension,) or not np.all(np.isfinite(x)):
            raise ValueError("context point has invalid shape or non-finite values")
        for slot in self.slots:
            if slot.slot_id == slot_id:
                return self._score(x, slot)
        raise KeyError(slot_id)

    def add_initial(self, point: Sequence[float], *, prior_covariance: np.ndarray | None = None) -> int:
        x = np.asarray(point, dtype=float)
        if x.shape != (self.dimension,) or not np.all(np.isfinite(x)):
            raise ValueError("context point has invalid shape or non-finite values")
        if len(self.slots) >= self.capacity:
            raise OverflowError("context bank is full; existing slots are not evicted")
        if prior_covariance is None:
            prior_covariance = self.regularisation * np.linalg.solve(self.metric, np.eye(self.dimension))
        cov = np.asarray(prior_covariance, dtype=float)
        if cov.shape != self.metric.shape or not np.allclose(cov, cov.T):
            raise ValueError("prior covariance has invalid shape or symmetry")
        if np.min(np.linalg.eigvalsh(cov)) <= 0:
            raise ValueError("prior covariance must be positive definite")
        slot_id = self._next_id
        self._next_id += 1
        self.slots.append(ContextSlot(slot_id, x.copy(), cov.copy(), count=1))
        return slot_id

    def route(self, point: Sequence[float]) -> tuple[ContextDecision, int | None, dict[int, float]]:
        x = np.asarray(point, dtype=float)
        if x.shape != (self.dimension,) or not np.all(np.isfinite(x)):
            raise ValueError("context point has invalid shape or non-finite values")
        if not self.slots:
            return ContextDecision.NOVEL, None, {}
        scores = {slot.slot_id: self._score(x, slot) for slot in self.slots}
        ordered = sorted(scores.items(), key=lambda pair: (pair[1], pair[0]))
        best_id, best_score = ordered[0]
        margin = float("inf") if len(ordered) == 1 else ordered[1][1] - best_score
        if best_score <= self.accept_threshold:
            if margin < self.ambiguity_margin:
                return ContextDecision.ABSTAIN, None, scores
            return ContextDecision.ACCEPT, best_id, scores
        if best_score >= self.novelty_threshold:
            return ContextDecision.NOVEL, None, scores
        return ContextDecision.ABSTAIN, None, scores

    def set_operator(self, slot_id: int, source_id: str, operator: Sequence[Sequence[float]]) -> None:
        """Store a learner-estimated source operator under an accepted context slot."""
        if not source_id:
            raise ValueError("source_id must be non-empty")
        if not any(slot.slot_id == slot_id for slot in self.slots):
            raise KeyError(slot_id)
        value = np.asarray(operator, dtype=float)
        if value.ndim != 2 or not np.all(np.isfinite(value)):
            raise ValueError("operator must be a finite matrix")
        self._relation_operators.setdefault(int(slot_id), {})[source_id] = value.copy()

    def operator_for_slot(self, slot_id: int) -> dict[str, np.ndarray]:
        """Return copies of operators learned for this accepted context slot."""
        if not any(slot.slot_id == slot_id for slot in self.slots):
            raise KeyError(slot_id)
        return {key: value.copy() for key, value in self._relation_operators.get(int(slot_id), {}).items()}

    def update_operator(
        self, slot_id: int, source_id: str, source: Sequence[float],
        residual_target: Sequence[float], *, rate: float = 0.1,
    ) -> None:
        """Apply a bounded online least-mean-squares update to one context relation."""
        x = np.asarray(source, dtype=float)
        y = np.asarray(residual_target, dtype=float)
        if x.ndim != 1 or y.ndim != 1 or not x.size or not y.size:
            raise ValueError("source and residual target must be non-empty vectors")
        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
            raise ValueError("source and residual target must be finite")
        if not np.isfinite(rate) or not 0.0 < rate <= 1.0:
            raise ValueError("rate must be in (0, 1]")
        operators = self._relation_operators.setdefault(int(slot_id), {})
        operator = operators.get(source_id)
        if operator is None:
            operator = np.zeros((y.size, x.size), dtype=float)
        if operator.shape != (y.size, x.size):
            raise ValueError("source/target dimensions differ from stored context operator")
        error = y - operator @ x
        operators[source_id] = operator + (rate / max(float(x @ x), 1.0)) * np.outer(error, x)

    def relation_resource_snapshot(self) -> dict[str, int]:
        """Count persistent numeric relation-operator buffers held by context slots."""
        return {
            "operator_count": sum(len(value) for value in self._relation_operators.values()),
            "operator_bytes": int(sum(item.nbytes for group in self._relation_operators.values()
                                       for item in group.values())),
        }

    def observe_novel(self, point: Sequence[float]) -> int | None:
        """Accumulate repeated novelty evidence and create a slot when safe.

        A full bank returns None and is left unchanged. The pending observations
        are only a compact novelty accumulator, not accepted context identity.
        """
        x = np.asarray(point, dtype=float)
        if x.shape != (self.dimension,) or not np.all(np.isfinite(x)):
            raise ValueError("context point has invalid shape or non-finite values")
        if len(self.slots) >= self.capacity:
            if self.full_bank_policy == "abstain":
                return None
            nearest = min(self.slots, key=lambda slot: (self._score(x, slot), slot.slot_id))
            nearest.update(x)
            nearest.novelty_hits += 1
            return nearest.slot_id
        self._pending.append(x.copy())
        if len(self._pending) < self.novelty_repeats:
            return None
        batch = np.vstack(self._pending[-self.novelty_repeats:])
        mean = batch.mean(axis=0)
        centered = batch - mean
        covariance = centered.T @ centered / max(1, len(batch) - 1)
        floor = self.regularisation * np.linalg.solve(self.metric, np.eye(self.dimension))
        covariance = covariance + floor
        self._pending.clear()
        return self.add_initial(mean, prior_covariance=covariance)
