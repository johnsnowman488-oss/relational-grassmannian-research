"""Explicit hierarchical prediction, attribution, eligibility and consolidation primitives.

These mechanisms are deliberately separate from H0 SOE/native dynamics. They
consume immutable pre-step snapshots and produce versioned candidates; they do
not rewrite evidence or alter the SOE/native configuration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy
from typing import Any, Callable, Iterable, Mapping, Sequence
import hashlib
import json
import math

import numpy as np


def fingerprint(value: Any) -> str:
    """Stable SHA-256 for JSON-compatible, finite experiment state."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Level(str, Enum):
    L0 = "L0_GROUNDING"
    L1 = "L1_RELATIONAL"
    L2 = "L2_CONTEXT"


class PredictionStatus(str, Enum):
    ISSUED = "ISSUED"
    SCORED = "SCORED"
    CONFIRMED = "CONFIRMED"
    CONTRADICTED = "CONTRADICTED"
    EXPIRED = "EXPIRED"
    WITHDRAWN = "WITHDRAWN"


class ErrorChannel(str, Enum):
    TEMPORAL = "temporal"
    RELATIONAL = "relational"
    ABSTRACTION = "abstraction"
    TASK = "task"


@dataclass(frozen=True)
class TargetSchema:
    """Declares a target's level, type, horizon and scoring semantics."""
    name: str
    level: Level
    target_type: str
    horizon_ticks: int
    metric: str

    def __post_init__(self) -> None:
        if not self.name or not self.target_type or self.horizon_ticks < 1:
            raise ValueError("target schema needs names and a positive horizon")
        allowed = {
            "continuous": {"mse", "mae"},
            "categorical": {"accuracy", "brier"},
            "relation": {"exact_match"},
            "context": {"accuracy", "brier"},
        }
        if self.target_type not in allowed or self.metric not in allowed[self.target_type]:
            raise ValueError("unsupported target type / metric combination")


@dataclass(frozen=True)
class Prediction:
    """A forecast record; never an observed or derived evidence record."""
    prediction_id: str
    level: Level
    target_name: str
    target_key: str
    issued_tick: int
    issued_at: float
    horizon_ticks: int
    evidence_cutoff: float
    value: Any
    model_fingerprint: str
    schema_fingerprint: str
    uncertainty: float | None = None
    status: PredictionStatus = PredictionStatus.ISSUED

    def __post_init__(self) -> None:
        if not self.prediction_id or not self.target_name or not self.target_key:
            raise ValueError("prediction identity and target are required")
        if self.issued_tick < 0 or self.horizon_ticks < 1:
            raise ValueError("prediction tick and horizon are invalid")
        if not math.isfinite(self.issued_at) or not math.isfinite(self.evidence_cutoff):
            raise ValueError("prediction times must be finite")
        if self.uncertainty is not None and (
            not math.isfinite(self.uncertainty) or self.uncertainty < 0
        ):
            raise ValueError("uncertainty must be finite and non-negative")


@dataclass(frozen=True)
class TargetObservation:
    target_name: str
    target_key: str
    value: Any
    event_time: float
    observed_at: float
    observed_tick: int
    source_id: str

    def __post_init__(self) -> None:
        if not self.target_name or not self.target_key or not self.source_id:
            raise ValueError("target observation requires identity and source")
        if self.observed_tick < 0 or not all(map(math.isfinite, (self.event_time, self.observed_at))):
            raise ValueError("observation time/tick is invalid")


@dataclass(frozen=True)
class PredictionScore:
    prediction_id: str
    target_source_id: str
    metric: str
    value: float
    evaluated_tick: int
    outcome: PredictionStatus


class PredictionJournal:
    """Append-only forecast journal with post-cutoff target eligibility."""
    def __init__(self) -> None:
        self._predictions: dict[str, Prediction] = {}
        self._scores: dict[str, PredictionScore] = {}

    def issue(self, prediction: Prediction) -> None:
        if prediction.status is not PredictionStatus.ISSUED:
            raise ValueError("new predictions must start in ISSUED state")
        if prediction.prediction_id in self._predictions:
            raise ValueError("prediction ID collision")
        self._predictions[prediction.prediction_id] = prediction

    def score(self, prediction_id: str, target: TargetObservation,
              schema: TargetSchema, *, evaluated_tick: int) -> PredictionScore:
        prediction = self._predictions[prediction_id]
        if prediction_id in self._scores:
            raise ValueError("prediction already scored")
        if prediction.status is not PredictionStatus.ISSUED:
            raise ValueError("prediction is not scoreable")
        if schema.name != prediction.target_name or schema.level != prediction.level:
            raise ValueError("prediction/schema mismatch")
        if fingerprint(schema.__dict__) != prediction.schema_fingerprint:
            raise ValueError("target schema fingerprint mismatch")
        if (target.target_name, target.target_key) != (prediction.target_name, prediction.target_key):
            raise ValueError("target identity mismatch")
        if target.observed_at <= prediction.evidence_cutoff:
            raise ValueError("target was already available at prediction cutoff")
        if target.observed_tick <= prediction.issued_tick:
            raise ValueError("target must become observable after prediction issue")
        if target.observed_tick > prediction.issued_tick + prediction.horizon_ticks:
            raise ValueError("target arrived outside prediction horizon")
        if evaluated_tick < target.observed_tick:
            raise ValueError("cannot score before target observation")
        if schema.target_type == "continuous":
            p, y = np.asarray(prediction.value, dtype=float), np.asarray(target.value, dtype=float)
            if p.shape != y.shape or not np.all(np.isfinite(p)) or not np.all(np.isfinite(y)):
                raise ValueError("continuous prediction/target shape or values invalid")
            error = p - y
            value = float(np.mean(error ** 2) if schema.metric == "mse" else np.mean(np.abs(error)))
        elif schema.target_type in ("categorical", "context"):
            if schema.metric == "accuracy":
                value = float(prediction.value == target.value)
            else:
                probs = np.asarray(prediction.value, dtype=float)
                if probs.ndim != 1 or np.any(probs < 0) or not np.isclose(probs.sum(), 1.0):
                    raise ValueError("Brier score requires a normalized probability vector")
                classes = list(target.value) if isinstance(target.value, (list, tuple)) else None
                if classes is None:
                    raise ValueError("Brier targets must be a one-hot vector")
                y = np.asarray(classes, dtype=float)
                if y.shape != probs.shape or not np.all(np.isin(y, [0.0, 1.0])) or y.sum() != 1:
                    raise ValueError("Brier target must be one-hot")
                value = float(np.mean((probs - y) ** 2))
        else:
            # Relation exact-match is an error/loss: zero is a correct witness.
            value = 0.0 if prediction.value == target.value else 1.0
        outcome = PredictionStatus.CONFIRMED if value == 0.0 or (
            schema.metric == "accuracy" and value == 1.0
        ) else PredictionStatus.CONTRADICTED
        score = PredictionScore(prediction_id, target.source_id, schema.metric,
                                value, evaluated_tick, outcome)
        self._scores[prediction_id] = score
        self._predictions[prediction_id] = Prediction(
            **{**prediction.__dict__, "status": PredictionStatus.SCORED}
        )
        return score

    def expire(self, prediction_id: str, *, current_tick: int) -> None:
        prediction = self._predictions[prediction_id]
        if prediction_id in self._scores or prediction.status is not PredictionStatus.ISSUED:
            raise ValueError("only unscored issued predictions can expire")
        if current_tick <= prediction.issued_tick + prediction.horizon_ticks:
            raise ValueError("prediction horizon has not elapsed")
        self._predictions[prediction_id] = Prediction(
            **{**prediction.__dict__, "status": PredictionStatus.EXPIRED}
        )

    def get(self, prediction_id: str) -> Prediction:
        return self._predictions[prediction_id]

    @property
    def scores(self) -> tuple[PredictionScore, ...]:
        return tuple(self._scores[k] for k in sorted(self._scores))


@dataclass(frozen=True)
class LearningSignals:
    """Independent error channels plus non-averagable integrity failures."""
    temporal: float = 0.0
    relational: float = 0.0
    abstraction: float = 0.0
    task: float = 0.0
    integrity_failures: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not all(math.isfinite(x) and x >= 0 for x in
                   (self.temporal, self.relational, self.abstraction, self.task)):
            raise ValueError("learning residuals must be finite and non-negative")
        if any(not item for item in self.integrity_failures):
            raise ValueError("integrity failure labels cannot be empty")

    def as_dict(self) -> dict[str, float]:
        return {ErrorChannel.TEMPORAL.value: self.temporal,
                ErrorChannel.RELATIONAL.value: self.relational,
                ErrorChannel.ABSTRACTION.value: self.abstraction,
                ErrorChannel.TASK.value: self.task}


@dataclass(frozen=True)
class ParameterRoute:
    parameter_family: str
    allowed_channels: frozenset[ErrorChannel]


class ErrorRouter:
    """Explicit error-to-parameter routing; integrity failures block updates."""
    def __init__(self, routes: Iterable[ParameterRoute]):
        declared = list(routes)
        self.routes = {r.parameter_family: r for r in declared}
        if not self.routes or len(self.routes) != len(declared):
            raise ValueError("at least one unique parameter route is required")

    def route(self, signals: LearningSignals) -> dict[str, dict[str, float]]:
        if signals.integrity_failures:
            return {}
        values = signals.as_dict()
        return {
            name: {channel.value: values[channel.value]
                   for channel in route.allowed_channels if values[channel.value] != 0.0}
            for name, route in sorted(self.routes.items())
        }


@dataclass(frozen=True)
class EligibilityEvent:
    event_id: str
    feature_id: str
    channel: str
    event_time: float
    observed_at: float
    observed_tick: int
    magnitude: float
    config_fingerprint: str

    def __post_init__(self) -> None:
        if not all((self.event_id, self.feature_id, self.channel, self.config_fingerprint)):
            raise ValueError("eligibility event identity/configuration required")
        if self.observed_tick < 0 or not math.isfinite(self.magnitude):
            raise ValueError("eligibility event tick/magnitude invalid")
        if not math.isfinite(self.event_time) or not math.isfinite(self.observed_at):
            raise ValueError("eligibility event times must be finite")


@dataclass
class _EligibilityState:
    event: EligibilityEvent
    value: float
    last_tick: int


class EligibilityLedger:
    """Bounded event-resolved temporal eligibility, separate from SOE χ.

    Late arrivals start eligibility at observed_tick; event_time is retained
    for analysis but never used to backfill prior credit.
    """
    def __init__(self, *, decay: float, capacity: int, config_fingerprint: str,
                 minimum_magnitude: float = 0.0):
        if not 0.0 <= decay < 1.0 or capacity < 1 or not config_fingerprint:
            raise ValueError("invalid eligibility configuration")
        if not math.isfinite(minimum_magnitude) or minimum_magnitude < 0:
            raise ValueError("minimum magnitude must be non-negative")
        self.decay, self.capacity = float(decay), int(capacity)
        self.config_fingerprint = config_fingerprint
        self.minimum_magnitude = float(minimum_magnitude)
        self._states: dict[tuple[str, str, str], _EligibilityState] = {}
        self._last_tick = -1

    def ingest(self, event: EligibilityEvent) -> None:
        if event.config_fingerprint != self.config_fingerprint:
            raise ValueError("eligibility kernel/config fingerprint mismatch")
        if event.observed_tick < self._last_tick:
            raise ValueError("late evidence must be ingested at current observed tick; no backfill")
        key = (event.event_id, event.feature_id, event.channel)
        if key in self._states:
            raise ValueError("duplicate eligibility event key")
        if len(self._states) >= self.capacity:
            raise OverflowError("eligibility capacity exhausted; no silent eviction")
        self._states[key] = _EligibilityState(event, event.magnitude, event.observed_tick)

    def advance(self, tick: int) -> None:
        if tick < self._last_tick:
            raise ValueError("eligibility ticks cannot move backwards")
        if tick == self._last_tick:
            return
        for state in self._states.values():
            if state.last_tick < tick:
                state.value *= self.decay ** (tick - state.last_tick)
                state.last_tick = tick
        self._last_tick = tick

    def values(self, *, prediction_cutoff_tick: int) -> dict[tuple[str, str, str], float]:
        return {
            key: state.value for key, state in sorted(self._states.items())
            if state.event.observed_tick <= prediction_cutoff_tick
            and abs(state.value) > self.minimum_magnitude
        }

    def expire(self, *, before_tick: int) -> tuple[tuple[str, str, str], ...]:
        removed = tuple(sorted(key for key, state in self._states.items()
                               if state.last_tick >= before_tick and abs(state.value) <= self.minimum_magnitude))
        for key in removed:
            del self._states[key]
        return removed

    def snapshot(self) -> dict:
        return {
            "schema": 1, "decay": self.decay, "capacity": self.capacity,
            "config_fingerprint": self.config_fingerprint,
            "minimum_magnitude": self.minimum_magnitude, "last_tick": self._last_tick,
            "states": [
                {"event": state.event.__dict__, "value": state.value, "last_tick": state.last_tick}
                for _, state in sorted(self._states.items())
            ],
        }

    def restore(self, snapshot: Mapping) -> None:
        if (snapshot.get("schema") != 1 or snapshot.get("decay") != self.decay
            or snapshot.get("capacity") != self.capacity
            or snapshot.get("config_fingerprint") != self.config_fingerprint
            or snapshot.get("minimum_magnitude") != self.minimum_magnitude):
            raise ValueError("eligibility snapshot configuration mismatch")
        states: dict[tuple[str, str, str], _EligibilityState] = {}
        for item in snapshot["states"]:
            event = EligibilityEvent(**item["event"])
            key = (event.event_id, event.feature_id, event.channel)
            if key in states or event.config_fingerprint != self.config_fingerprint:
                raise ValueError("invalid eligibility snapshot event")
            value = float(item["value"])
            last_tick = int(item["last_tick"])
            if not math.isfinite(value) or last_tick < event.observed_tick:
                raise ValueError("invalid eligibility snapshot value/tick")
            states[key] = _EligibilityState(event, value, last_tick)
        if len(states) > self.capacity:
            raise ValueError("eligibility snapshot exceeds capacity")
        self._states = states
        self._last_tick = int(snapshot["last_tick"])


def replay_eligibility(events: Sequence[EligibilityEvent], *, decay: float,
                       capacity: int, config_fingerprint: str,
                       through_tick: int) -> dict[tuple[str, str, str], float]:
    """Deterministic replay of the immutable observation journal."""
    ledger = EligibilityLedger(decay=decay, capacity=capacity,
                               config_fingerprint=config_fingerprint)
    for event in sorted(events, key=lambda e: (e.observed_tick, e.event_id, e.feature_id, e.channel)):
        if event.observed_tick > through_tick:
            continue
        ledger.advance(event.observed_tick)
        ledger.ingest(event)
    ledger.advance(through_tick)
    return ledger.values(prediction_cutoff_tick=through_tick)


@dataclass(frozen=True)
class ValidationReceipt:
    candidate_fingerprint: str
    parent_fingerprint: str
    protocol_fingerprint: str
    partition_fingerprint: str
    criteria_fingerprint: str
    evidence_watermark: int
    passed: bool
    metrics: Mapping[str, float]


class ConsolidationGate:
    """Candidate isolation and watermark-bound promotion/rollback."""
    def __init__(self, trusted_parameters: Mapping[str, Any], *, evidence_watermark: int = 0):
        if evidence_watermark < 0:
            raise ValueError("evidence watermark cannot be negative")
        self.trusted = deepcopy(dict(trusted_parameters))
        self.trusted_fingerprint = fingerprint(self.trusted)
        self.evidence_watermark = evidence_watermark
        self.candidate: dict[str, Any] | None = None
        self.candidate_fingerprint: str | None = None
        self.receipt: ValidationReceipt | None = None
        self.history: list[dict[str, Any]] = []

    def stage(self, parameters: Mapping[str, Any]) -> str:
        candidate = deepcopy(dict(parameters))
        candidate_fp = fingerprint(candidate)
        self.candidate = candidate
        self.candidate_fingerprint = candidate_fp
        self.receipt = None
        self.history.append({"state": "CANDIDATE", "fingerprint": candidate_fp})
        return candidate_fp

    def validate(self, *, protocol_fingerprint: str, partition_fingerprint: str,
                 criteria_fingerprint: str, evidence_watermark: int,
                 metrics: Mapping[str, float], passed: bool) -> ValidationReceipt:
        if self.candidate is None or self.candidate_fingerprint is None:
            raise RuntimeError("no candidate staged")
        if evidence_watermark != self.evidence_watermark:
            raise ValueError("validation evidence watermark is stale or from another journal state")
        if not all((protocol_fingerprint, partition_fingerprint, criteria_fingerprint)):
            raise ValueError("validation receipt fingerprints are required")
        clean_metrics = {str(k): float(v) for k, v in metrics.items()}
        if not clean_metrics or not all(math.isfinite(v) for v in clean_metrics.values()):
            raise ValueError("validation metrics must be non-empty and finite")
        receipt = ValidationReceipt(
            self.candidate_fingerprint, self.trusted_fingerprint,
            protocol_fingerprint, partition_fingerprint, criteria_fingerprint,
            evidence_watermark, bool(passed), clean_metrics,
        )
        self.receipt = receipt
        self.history.append({"state": "VALIDATED" if passed else "REJECTED",
                             "candidate": self.candidate_fingerprint,
                             "receipt": fingerprint(receipt.__dict__)})
        return receipt

    def observe_new_evidence(self, new_watermark: int) -> None:
        if new_watermark < self.evidence_watermark:
            raise ValueError("evidence watermark cannot move backwards")
        self.evidence_watermark = new_watermark

    def promote(self) -> str:
        receipt = self.receipt
        if self.candidate is None or receipt is None:
            raise ValueError("candidate lacks validation receipt")
        if not receipt.passed:
            raise ValueError("failed candidate cannot be promoted")
        if receipt.candidate_fingerprint != self.candidate_fingerprint:
            raise ValueError("receipt does not validate active candidate")
        if receipt.parent_fingerprint != self.trusted_fingerprint:
            raise ValueError("receipt parent differs from trusted incumbent")
        if receipt.evidence_watermark != self.evidence_watermark:
            raise ValueError("new evidence invalidated validation receipt")
        self.trusted = deepcopy(self.candidate)
        self.trusted_fingerprint = fingerprint(self.trusted)
        self.history.append({"state": "PROMOTED", "fingerprint": self.trusted_fingerprint})
        self.candidate = None
        self.candidate_fingerprint = None
        self.receipt = None
        return self.trusted_fingerprint

    def reject(self) -> None:
        self.history.append({"state": "REJECTED", "candidate": self.candidate_fingerprint})
        self.candidate = None
        self.candidate_fingerprint = None
        self.receipt = None

    def rollback(self) -> dict[str, Any]:
        self.candidate = None
        self.candidate_fingerprint = None
        self.receipt = None
        self.history.append({"state": "ROLLBACK", "trusted": self.trusted_fingerprint,
                             "evidence_watermark": self.evidence_watermark})
        return deepcopy(self.trusted)

    def snapshot(self) -> dict:
        return {"schema": 1, "trusted": deepcopy(self.trusted),
                "trusted_fingerprint": self.trusted_fingerprint,
                "evidence_watermark": self.evidence_watermark,
                "candidate": deepcopy(self.candidate),
                "candidate_fingerprint": self.candidate_fingerprint,
                "receipt": None if self.receipt is None else self.receipt.__dict__,
                "history": deepcopy(self.history)}


    def restore(self, snapshot: Mapping) -> None:
        """Restore a validated checkpoint without rolling back the evidence watermark."""
        if snapshot.get("schema") != 1:
            raise ValueError("unsupported consolidation checkpoint schema")
        trusted = deepcopy(dict(snapshot["trusted"]))
        trusted_fp = fingerprint(trusted)
        if snapshot.get("trusted_fingerprint") != trusted_fp:
            raise ValueError("trusted checkpoint fingerprint mismatch")
        watermark = int(snapshot["evidence_watermark"])
        if watermark < self.evidence_watermark:
            raise ValueError("checkpoint cannot discard newer observed evidence")
        candidate = snapshot.get("candidate")
        candidate_fp = snapshot.get("candidate_fingerprint")
        if candidate is None:
            if candidate_fp is not None or snapshot.get("receipt") is not None:
                raise ValueError("checkpoint has detached candidate metadata")
        else:
            candidate = deepcopy(dict(candidate))
            if fingerprint(candidate) != candidate_fp:
                raise ValueError("candidate checkpoint fingerprint mismatch")
        self.trusted = trusted
        self.trusted_fingerprint = trusted_fp
        self.evidence_watermark = watermark
        self.candidate = candidate
        self.candidate_fingerprint = candidate_fp
        # Receipts are intentionally not restored as promotable authority:
        # validation must be rerun against the restored process and journal.
        self.receipt = None
        self.history = deepcopy(list(snapshot.get("history", [])))
