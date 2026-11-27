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

def _finite_vector(value: Sequence[float], *, name: str) -> np.ndarray:
    vector = np.asarray(value, dtype=np.float64).reshape(-1)
    if vector.size == 0 or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a non-empty finite vector")
    return vector.copy()


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
        self._active_by_target: dict[tuple[str, str], str] = {}
        self._transaction_log: list[tuple] | None = None

    def issue(self, prediction: Prediction) -> None:
        if prediction.status is not PredictionStatus.ISSUED:
            raise ValueError("new predictions must start in ISSUED state")
        if prediction.prediction_id in self._predictions:
            raise ValueError("prediction ID collision")
        target_key = (prediction.target_name, prediction.target_key)
        prior_active = self._active_by_target.get(target_key)
        if self._transaction_log is not None:
            self._transaction_log.append(("issue", prediction.prediction_id, target_key, prior_active))
        self._predictions[prediction.prediction_id] = prediction
        self._active_by_target[target_key] = prediction.prediction_id

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
        target_key = (prediction.target_name, prediction.target_key)
        prior_active = self._active_by_target.get(target_key)
        if self._transaction_log is not None:
            self._transaction_log.append(("score", prediction_id, prediction, target_key, prior_active))
        self._scores[prediction_id] = score
        self._predictions[prediction_id] = Prediction(
            **{**prediction.__dict__, "status": PredictionStatus.SCORED}
        )
        if self._active_by_target.get(target_key) == prediction_id:
            self._active_by_target.pop(target_key, None)
        return score

    def withdraw(self, prediction_id: str, *, current_tick: int) -> None:
        """Withdraw a forecast when its next target is not strictly post-cutoff.

        Equal-time or late targets remain valid observations, but they cannot
        score a forecast whose evidence cutoff already includes that time.
        Withdrawal records the non-scoreable lifecycle outcome without
        weakening the strict post-cutoff scoring contract.
        """
        prediction = self._predictions[prediction_id]
        if prediction_id in self._scores or prediction.status is not PredictionStatus.ISSUED:
            raise ValueError("only unscored issued predictions can be withdrawn")
        if current_tick <= prediction.issued_tick:
            raise ValueError("prediction cannot be withdrawn before a later observation tick")
        target_key = (prediction.target_name, prediction.target_key)
        prior_active = self._active_by_target.get(target_key)
        if self._transaction_log is not None:
            self._transaction_log.append(("withdraw", prediction_id, prediction, target_key, prior_active))
        self._predictions[prediction_id] = Prediction(
            **{**prediction.__dict__, "status": PredictionStatus.WITHDRAWN}
        )
        if self._active_by_target.get(target_key) == prediction_id:
            self._active_by_target.pop(target_key, None)

    def expire(self, prediction_id: str, *, current_tick: int) -> None:
        prediction = self._predictions[prediction_id]
        if prediction_id in self._scores or prediction.status is not PredictionStatus.ISSUED:
            raise ValueError("only unscored issued predictions can expire")
        if current_tick <= prediction.issued_tick + prediction.horizon_ticks:
            raise ValueError("prediction horizon has not elapsed")
        target_key = (prediction.target_name, prediction.target_key)
        prior_active = self._active_by_target.get(target_key)
        if self._transaction_log is not None:
            self._transaction_log.append(("expire", prediction_id, prediction, target_key, prior_active))
        self._predictions[prediction_id] = Prediction(
            **{**prediction.__dict__, "status": PredictionStatus.EXPIRED}
        )
        if self._active_by_target.get(target_key) == prediction_id:
            self._active_by_target.pop(target_key, None)

    def get(self, prediction_id: str) -> Prediction:
        return self._predictions[prediction_id]

    @property
    def scores(self) -> tuple[PredictionScore, ...]:
        return tuple(self._scores[k] for k in sorted(self._scores))

    def begin_transaction(self) -> None:
        if self._transaction_log is not None:
            raise RuntimeError("prediction journal transaction already active")
        self._transaction_log = []

    def commit_transaction(self) -> None:
        if self._transaction_log is None:
            raise RuntimeError("prediction journal has no active transaction")
        self._transaction_log = None

    def rollback_transaction(self) -> None:
        if self._transaction_log is None:
            raise RuntimeError("prediction journal has no active transaction")
        for change in reversed(self._transaction_log):
            kind = change[0]
            if kind == "issue":
                _, prediction_id, target_key, prior_active = change
                self._predictions.pop(prediction_id, None)
                self._scores.pop(prediction_id, None)
                if prior_active is None:
                    self._active_by_target.pop(target_key, None)
                else:
                    self._active_by_target[target_key] = prior_active
            elif kind == "score":
                _, prediction_id, prior_prediction, target_key, prior_active = change
                self._predictions[prediction_id] = prior_prediction
                self._scores.pop(prediction_id, None)
                if prior_active is None:
                    self._active_by_target.pop(target_key, None)
                else:
                    self._active_by_target[target_key] = prior_active
            elif kind in {"expire", "withdraw"}:
                _, prediction_id, prior_prediction, target_key, prior_active = change
                self._predictions[prediction_id] = prior_prediction
                if prior_active is None:
                    self._active_by_target.pop(target_key, None)
                else:
                    self._active_by_target[target_key] = prior_active
            else:
                raise RuntimeError(f"unknown prediction transaction change: {kind}")
        self._transaction_log = None

    def snapshot(self) -> dict:
        return {
            "predictions": [
                {**p.__dict__, "level": p.level.value, "status": p.status.value}
                for _, p in sorted(self._predictions.items())
            ],
            "scores": [s.__dict__ for _, s in sorted(self._scores.items())],
        }

    def restore(self, state: Mapping) -> None:
        predictions = {}
        for item in state.get("predictions", ()):
            row = dict(item)
            row["level"] = Level(row["level"])
            row["status"] = PredictionStatus(row["status"])
            p = Prediction(**row)
            if p.prediction_id in predictions:
                raise ValueError("duplicate prediction in checkpoint")
            predictions[p.prediction_id] = p
        scores = {}
        for item in state.get("scores", ()):
            score = PredictionScore(**item)
            if score.prediction_id not in predictions or score.prediction_id in scores:
                raise ValueError("invalid prediction score checkpoint")
            scores[score.prediction_id] = score
        self._predictions, self._scores = predictions, scores
        self._active_by_target = {
            (p.target_name, p.target_key): p.prediction_id
            for p in predictions.values() if p.status is PredictionStatus.ISSUED
        }
        self._transaction_log = None


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
        if len(self.routes) != len(declared):
            raise ValueError("parameter-family routes must be unique")

    def route(self, signals: LearningSignals) -> dict[str, dict[str, float]]:
        if signals.integrity_failures:
            return {}
        values = signals.as_dict()
        routed = {}
        for name, route in sorted(self.routes.items()):
            permitted = {channel.value: values[channel.value]
                         for channel in route.allowed_channels if values[channel.value] != 0.0}
            if permitted:
                routed[name] = permitted
        return routed


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

    def reset(self, *, tick: int) -> None:
        """Explicitly end an episode without silently evicting its eligibility."""
        if isinstance(tick, bool) or tick < self._last_tick:
            raise ValueError("eligibility reset tick cannot move backwards")
        self._states = {}
        self._last_tick = int(tick)

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


@dataclass(frozen=True)
class RelationPattern:
    relation_type: str
    subject_id: str
    subject_type: str
    object_id: str
    object_type: str
    context: str | None

    def __post_init__(self) -> None:
        if not all((self.relation_type, self.subject_id, self.subject_type,
                    self.object_id, self.object_type)):
            raise ValueError("relation pattern requires typed relation and entity bindings")


@dataclass(frozen=True)
class EventRolePattern:
    event_type: str
    roles: tuple[tuple[str, str, str], ...]
    context: str | None

    def __post_init__(self) -> None:
        if not self.event_type or len(self.roles) < 2:
            raise ValueError("event-role pattern requires an event type and at least two roles")
        names = [row[0] for row in self.roles if len(row) == 3]
        if len(names) != len(self.roles) or len(names) != len(set(names)) or any(
            not role or not entity_id or not entity_type
            for role, entity_id, entity_type in self.roles
        ):
            raise ValueError("event-role bindings require unique roles and entity identities/types")


class _PatternCounter:
    """Deterministic empirical learner for typed semantic patterns."""
    def __init__(self) -> None:
        self.counts: dict[str, dict[str, int]] = {}
        self._best_by_key: dict[str, str] = {}
        self._transaction_log: dict[tuple[str, str], int | None] | None = None
        self._best_transaction_log: dict[str, str | None] | None = None

    def begin_transaction(self) -> None:
        if self._transaction_log is not None:
            raise RuntimeError("pattern counter transaction already active")
        self._transaction_log = {}
        self._best_transaction_log = {}

    def commit_transaction(self) -> None:
        if self._transaction_log is None or self._best_transaction_log is None:
            raise RuntimeError("pattern counter has no active transaction")
        self._transaction_log = None
        self._best_transaction_log = None

    def rollback_transaction(self) -> None:
        if self._transaction_log is None or self._best_transaction_log is None:
            raise RuntimeError("pattern counter has no active transaction")
        for (key, pattern), prior_count in self._transaction_log.items():
            bucket = self.counts.get(key)
            if prior_count is None:
                if bucket is not None:
                    bucket.pop(pattern, None)
                    if not bucket:
                        self.counts.pop(key, None)
            else:
                self.counts.setdefault(key, {})[pattern] = prior_count
        for key, prior_best in self._best_transaction_log.items():
            if prior_best is None:
                self._best_by_key.pop(key, None)
            else:
                self._best_by_key[key] = prior_best
        self._transaction_log = None
        self._best_transaction_log = None

    def observe(self, key: str, pattern: str) -> None:
        bucket = self.counts.setdefault(key, {})
        if self._transaction_log is not None and self._best_transaction_log is not None:
            if (key, pattern) not in self._transaction_log:
                self._transaction_log[(key, pattern)] = bucket.get(pattern)
            if key not in self._best_transaction_log:
                self._best_transaction_log[key] = self._best_by_key.get(key)
        bucket[pattern] = bucket.get(pattern, 0) + 1
        best = self._best_by_key.get(key)
        if best is None or bucket[pattern] > bucket[best] or (
            bucket[pattern] == bucket[best] and pattern < best
        ):
            self._best_by_key[key] = pattern

    def predict(self, key: str) -> str | None:
        return self._best_by_key.get(key)

    def snapshot(self) -> dict:
        return {key: dict(sorted(values.items())) for key, values in sorted(self.counts.items())}

    def restore(self, state: Mapping) -> None:
        candidate = {}
        for key, values in state.items():
            if not isinstance(key, str) or not isinstance(values, Mapping):
                raise ValueError("invalid pattern learner checkpoint")
            clean = {str(p): int(n) for p, n in values.items()}
            if any(n < 1 for n in clean.values()):
                raise ValueError("pattern counts must be positive")
            candidate[key] = clean
        self.counts = candidate
        self._best_by_key = {
            key: min(values, key=lambda pattern: (-values[pattern], pattern))
            for key, values in candidate.items() if values
        }
        self._transaction_log = None
        self._best_transaction_log = None


class SemanticRelationLearner:
    """Predicts typed relation existence/signature, not numeric feature vectors."""
    def __init__(self) -> None:
        self._counter = _PatternCounter()

    @staticmethod
    def _key(context: str | None) -> str:
        return fingerprint({"context": context})

    @staticmethod
    def _encode(pattern: RelationPattern) -> str:
        return json.dumps(pattern.__dict__, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _decode(value: str) -> RelationPattern:
        return RelationPattern(**json.loads(value))

    def observe(self, record: Any) -> None:
        pattern = RelationPattern(record.relation_type.name, record.subject.entity_id,
                                  record.subject.entity_type, record.object.entity_id,
                                  record.object.entity_type, record.context)
        self._counter.observe(self._key(record.context), self._encode(pattern))

    def predict(self, context: str | None = None) -> RelationPattern | None:
        value = self._counter.predict(self._key(context))
        return None if value is None else self._decode(value)

    def snapshot(self) -> dict:
        return self._counter.snapshot()

    def restore(self, state: Mapping) -> None:
        self._counter.restore(state)

    def begin_transaction(self) -> None:
        self._counter.begin_transaction()

    def commit_transaction(self) -> None:
        self._counter.commit_transaction()

    def rollback_transaction(self) -> None:
        self._counter.rollback_transaction()


class NaryEventRoleLearner:
    """Predicts event type and the complete typed role schema as one object."""
    def __init__(self) -> None:
        self._counter = _PatternCounter()

    @staticmethod
    def _key(context: str | None) -> str:
        return fingerprint({"context": context})

    @staticmethod
    def _encode(pattern: EventRolePattern) -> str:
        return json.dumps(pattern.__dict__, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _decode(value: str) -> EventRolePattern:
        row = json.loads(value)
        row["roles"] = tuple(tuple(x) for x in row["roles"])
        return EventRolePattern(**row)

    def observe(self, event: Any) -> None:
        roles = tuple(sorted((p.role, p.entity_id, p.entity_type) for p in event.participants))
        pattern = EventRolePattern(event.event_type, roles, event.context)
        self._counter.observe(self._key(event.context), self._encode(pattern))

    def predict(self, context: str | None = None) -> EventRolePattern | None:
        value = self._counter.predict(self._key(context))
        return None if value is None else self._decode(value)

    def snapshot(self) -> dict:
        return self._counter.snapshot()

    def restore(self, state: Mapping) -> None:
        self._counter.restore(state)

    def begin_transaction(self) -> None:
        self._counter.begin_transaction()

    def commit_transaction(self) -> None:
        self._counter.commit_transaction()

    def rollback_transaction(self) -> None:
        self._counter.rollback_transaction()


class TemporalCreditLearner:
    """Error-weighted temporal parameter learner driven by event-resolved eligibility."""
    def __init__(self, learning_rate: float = 0.01):
        if not math.isfinite(learning_rate) or learning_rate <= 0:
            raise ValueError("temporal learning rate must be positive and finite")
        self.learning_rate = float(learning_rate)
        self.weights: dict[str, float] = {}
        self._transaction_log: dict[str, tuple[bool, float | None]] | None = None

    def begin_transaction(self) -> None:
        if self._transaction_log is not None:
            raise RuntimeError("temporal credit transaction already active")
        self._transaction_log = {}

    def commit_transaction(self) -> None:
        if self._transaction_log is None:
            raise RuntimeError("temporal credit has no active transaction")
        self._transaction_log = None

    def rollback_transaction(self) -> None:
        if self._transaction_log is None:
            raise RuntimeError("temporal credit has no active transaction")
        for key, (existed, value) in self._transaction_log.items():
            if existed:
                self.weights[key] = float(value)
            else:
                self.weights.pop(key, None)
        self._transaction_log = None

    def update(self, error: float, eligibility: Mapping[tuple[str, str, str], float]) -> None:
        if not math.isfinite(error) or error < 0:
            raise ValueError("temporal error must be finite and non-negative")
        if error == 0:
            return
        for (event_id, feature_id, channel), trace in sorted(eligibility.items()):
            key = json.dumps((event_id, feature_id, channel), separators=(",", ":"))
            if self._transaction_log is not None and key not in self._transaction_log:
                self._transaction_log[key] = (key in self.weights, self.weights.get(key))
            self.weights[key] = self.weights.get(key, 0.0) - self.learning_rate * error * float(trace)

    def snapshot(self) -> dict:
        return {"learning_rate": self.learning_rate, "weights": dict(sorted(self.weights.items()))}

    def restore(self, state: Mapping) -> None:
        if float(state["learning_rate"]) != self.learning_rate:
            raise ValueError("temporal learner learning-rate mismatch")
        weights = {str(k): float(v) for k, v in state["weights"].items()}
        if not all(math.isfinite(v) for v in weights.values()):
            raise ValueError("temporal learner checkpoint has non-finite weights")
        self.weights = weights


class TaskOutcomeLearner:
    """Small task-level calibration learner, updated only from task residuals."""
    def __init__(self) -> None:
        self.outcomes: dict[str, list[int]] = {}
        self._transaction_log: dict[str, int | None] | None = None

    def begin_transaction(self) -> None:
        if self._transaction_log is not None:
            raise RuntimeError("task outcome transaction already active")
        self._transaction_log = {}

    def commit_transaction(self) -> None:
        if self._transaction_log is None:
            raise RuntimeError("task outcomes have no active transaction")
        self._transaction_log = None

    def rollback_transaction(self) -> None:
        if self._transaction_log is None:
            raise RuntimeError("task outcomes have no active transaction")
        for key, prior_length in self._transaction_log.items():
            if prior_length is None:
                self.outcomes.pop(key, None)
            else:
                del self.outcomes[key][prior_length:]
        self._transaction_log = None

    def predict_error_probability(self, task_key: str) -> float:
        """Laplace-smoothed prior probability that this task channel errs."""
        if not task_key:
            raise ValueError("task outcome prediction requires a task key")
        values = self.outcomes.get(task_key, ())
        return float((sum(values) + 1) / (len(values) + 2))

    def observe_error(self, task_key: str, error: float) -> None:
        if not task_key or not math.isfinite(error) or error < 0:
            raise ValueError("task outcome requires a key and finite non-negative error")
        if self._transaction_log is not None and task_key not in self._transaction_log:
            prior = self.outcomes.get(task_key)
            self._transaction_log[task_key] = None if prior is None else len(prior)
        self.outcomes.setdefault(task_key, []).append(int(error > 0.0))

    def error_rate(self, task_key: str) -> float | None:
        values = self.outcomes.get(task_key)
        return None if not values else float(sum(values) / len(values))

    def snapshot(self) -> dict:
        return {k: list(v) for k, v in sorted(self.outcomes.items())}

    def restore(self, state: Mapping) -> None:
        candidate = {str(k): [int(v) for v in values] for k, values in state.items()}
        if any(v not in (0, 1) for values in candidate.values() for v in values):
            raise ValueError("task outcome checkpoint must contain binary errors")
        self.outcomes = candidate


class Level0FeaturePredictor:
    """Fit-partition mean predictor with error-driven online adaptation."""
    def __init__(self, learning_rate: float = 0.1):
        if not math.isfinite(learning_rate) or not 0 < learning_rate <= 1:
            raise ValueError("feature predictor learning rate must be in (0, 1]")
        self.learning_rate = float(learning_rate)
        self.mean: np.ndarray | None = None
        self.update_count = 0

    def fit(self, examples: Sequence[Sequence[float]]) -> None:
        if not examples:
            raise ValueError("level-0 predictor requires fit examples")
        rows = [_finite_vector(row, name="level-0 fit vector") for row in examples]
        if len({row.size for row in rows}) != 1:
            raise ValueError("level-0 fit vectors must have a fixed dimension")
        self.mean = np.mean(np.vstack(rows), axis=0)

    def predict(self) -> list[float] | None:
        return None if self.mean is None else self.mean.tolist()

    def update(self, target: Sequence[float]) -> None:
        values = _finite_vector(target, name="level-0 target")
        if self.mean is None or values.size != self.mean.size:
            raise ValueError("level-0 update requires a fitted predictor with matching dimension")
        self.mean = self.mean + self.learning_rate * (values - self.mean)
        self.update_count += 1

    def snapshot(self) -> dict:
        return {"learning_rate": self.learning_rate,
                "mean": None if self.mean is None else self.mean.tolist(),
                "update_count": self.update_count}

    def restore(self, state: Mapping) -> None:
        if float(state["learning_rate"]) != self.learning_rate:
            raise ValueError("level-0 predictor learning-rate mismatch")
        mean = state.get("mean")
        candidate = None if mean is None else _finite_vector(mean, name="level-0 checkpoint mean")
        if int(state["update_count"]) < 0 or (candidate is None and int(state["update_count"]) != 0):
            raise ValueError("level-0 update count is inconsistent with fitted state")
        self.mean = candidate
        self.update_count = int(state["update_count"])


class ContextTransitionLearner:
    """Context-conditioned categorical predictor for L2 regime/context transitions."""
    def __init__(self) -> None:
        self._counter = _PatternCounter()

    @staticmethod
    def _key(context: str | None) -> str:
        return fingerprint({"current_context": context})

    def observe(self, current_context: str | None, next_context: str | None) -> None:
        encoded = json.dumps(next_context, ensure_ascii=False, separators=(",", ":"))
        self._counter.observe(self._key(current_context), encoded)

    def predict(self, current_context: str | None) -> str | None:
        encoded = self._counter.predict(self._key(current_context))
        return None if encoded is None else json.loads(encoded)

    def snapshot(self) -> dict:
        return self._counter.snapshot()

    def restore(self, state: Mapping) -> None:
        self._counter.restore(state)

    def begin_transaction(self) -> None:
        self._counter.begin_transaction()

    def commit_transaction(self) -> None:
        self._counter.commit_transaction()

    def rollback_transaction(self) -> None:
        self._counter.rollback_transaction()


class LearningRuntime:
    """Shared HLA/HLB prediction and learning cycle.

    The model checkpoint is rollback-scoped. The compact observation journal is
    append-only: restoring a candidate checkpoint restores the incumbent model,
    then deterministically replays labels received after that checkpoint into
    the incumbent learners. It stores typed learning labels, not HLA witnesses.
    """
    def __init__(self, *, eligibility_decay: float = 0.9, eligibility_capacity: int = 4096,
                 eligibility_config_fingerprint: str = "h1-soe-eligibility-v1",
                 enabled_channels: Iterable[ErrorChannel] | None = None):
        self.enabled_channels = frozenset(ErrorChannel) if enabled_channels is None else frozenset(enabled_channels)
        if any(not isinstance(channel, ErrorChannel) for channel in self.enabled_channels):
            raise ValueError("enabled_channels must contain ErrorChannel values")
        self.schemas = {
            "next_l0_features": TargetSchema("next_l0_features", Level.L0, "continuous", 1, "mse"),
            "next_relation_pattern": TargetSchema("next_relation_pattern", Level.L1, "relation", 1, "exact_match"),
            "next_event_role_pattern": TargetSchema("next_event_role_pattern", Level.L1, "relation", 1, "exact_match"),
            "next_context": TargetSchema("next_context", Level.L2, "categorical", 1, "accuracy"),
        }
        self.predictions = PredictionJournal()
        self.level0 = Level0FeaturePredictor()
        self.relations = SemanticRelationLearner()
        self.event_roles = NaryEventRoleLearner()
        self.context_transitions = ContextTransitionLearner()
        self.task_outcomes = TaskOutcomeLearner()
        self.temporal_credit = TemporalCreditLearner()
        self.eligibility = EligibilityLedger(decay=eligibility_decay, capacity=eligibility_capacity,
                                             config_fingerprint=eligibility_config_fingerprint)
        self.error_router = ErrorRouter([
            route for route in (
                ParameterRoute("temporal_eligibility", frozenset({ErrorChannel.TEMPORAL})),
                ParameterRoute("temporal_feature_predictor", frozenset({ErrorChannel.TEMPORAL})),
                ParameterRoute("semantic_relation_learner", frozenset({ErrorChannel.RELATIONAL})),
                ParameterRoute("nary_event_role_learner", frozenset({ErrorChannel.ABSTRACTION})),
                ParameterRoute("context_transition_learner", frozenset({ErrorChannel.ABSTRACTION})),
                ParameterRoute("task_outcome_learner", frozenset({ErrorChannel.TASK})),
            ) if route.allowed_channels.issubset(self.enabled_channels)
        ])
        self._observation_journal: list[dict] = []
        self._prediction_sequence = 0
        self._last_observed_at = 0.0
        self.last_signals = LearningSignals()
        self._last_issue_context: dict[str, Any] | None = None

    def fit_level0_predictor(self, examples: Sequence[Sequence[float]], *, partition: str) -> int:
        if partition != "fit":
            raise ValueError("level-0 predictor fitting accepts the fit partition only")
        self.level0.fit(examples)
        return len(examples)

    def fit_context_transitions(self, transitions: Sequence[tuple[str | None, str | None]], *,
                                partition: str) -> int:
        if partition != "fit":
            raise ValueError("context transition fitting accepts the fit partition only")
        for current, following in transitions:
            self.context_transitions.observe(current, following)
        return len(transitions)

    def fit_relation_patterns(self, records: Sequence[Any], *, partition: str) -> int:
        if partition != "fit":
            raise ValueError("semantic relation learner fitting accepts the fit partition only")
        for record in records:
            self.relations.observe(record)
        return len(records)

    def fit_event_role_patterns(self, events: Sequence[Any], *, partition: str) -> int:
        if partition != "fit":
            raise ValueError("n-ary event-role learner fitting accepts the fit partition only")
        for event in events:
            self.event_roles.observe(event)
        return len(events)

    def begin_tick(self, *, tick: int, observed_at: float,
                   context: str | None = None) -> tuple[Prediction, ...]:
        if tick < 0 or not math.isfinite(observed_at) or observed_at < self._last_observed_at:
            raise ValueError("learning tick/time must be monotone")
        self._last_observed_at = observed_at
        self.last_signals = LearningSignals()
        self._last_issue_context = {
            "tick": tick, "cutoff": observed_at, "context": context,
        }
        issued = []
        level0_value = self.level0.predict()
        if level0_value is not None:
            self._prediction_sequence += 1
            schema = self.schemas["next_l0_features"]
            prediction = Prediction(
                f"lrn-l0-{self._prediction_sequence}", Level.L0, schema.name,
                f"level0@{tick + 1}", tick, observed_at, schema.horizon_ticks,
                observed_at, level0_value, fingerprint(self.level0.snapshot()),
                fingerprint(schema.__dict__),
            )
            self.predictions.issue(prediction)
            issued.append(prediction)
        pattern = self.relations.predict(context)
        self._prediction_sequence += 1
        schema = self.schemas["next_relation_pattern"]
        prediction = Prediction(
            f"lrn-rel-{self._prediction_sequence}", Level.L1, schema.name,
            f"relation@{tick + 1}", tick, observed_at, schema.horizon_ticks,
            observed_at,
            self.relations._encode(pattern) if pattern is not None else "__ABSTAIN__",
            fingerprint(self.relations.snapshot()), fingerprint(schema.__dict__),
        )
        self.predictions.issue(prediction)
        issued.append(prediction)
        next_context = self.context_transitions.predict(context)
        self._prediction_sequence += 1
        schema = self.schemas["next_context"]
        prediction = Prediction(
            f"lrn-l2-{self._prediction_sequence}", Level.L2, schema.name,
            f"context@{tick + 1}", tick, observed_at, schema.horizon_ticks,
            observed_at, next_context if next_context is not None else "__ABSTAIN__",
            fingerprint(self.context_transitions.snapshot()), fingerprint(schema.__dict__),
        )
        self.predictions.issue(prediction)
        issued.append(prediction)
        role_pattern = self.event_roles.predict(context)
        self._prediction_sequence += 1
        schema = self.schemas["next_event_role_pattern"]
        prediction = Prediction(
            f"lrn-role-{self._prediction_sequence}", Level.L1, schema.name,
            f"event@{tick + 1}", tick, observed_at, schema.horizon_ticks,
            observed_at,
            self.event_roles._encode(role_pattern) if role_pattern is not None else "__ABSTAIN__",
            fingerprint(self.event_roles.snapshot()), fingerprint(schema.__dict__),
        )
        self.predictions.issue(prediction)
        issued.append(prediction)
        return tuple(issued)

    def _score_and_update(self, name: str, key: str, value: Any, source_id: str,
                          event_time: float, observed_at: float, tick: int) -> float | None:
        prediction_id = self.predictions._active_by_target.get((name, key))
        if prediction_id is None:
            return None
        prediction = self.predictions.get(prediction_id)
        if prediction.status is not PredictionStatus.ISSUED:
            return None
        if observed_at <= prediction.evidence_cutoff:
            # Same-time and late observations are preserved in the observation
            # journal, but are not eligible targets for this forecast.
            self.predictions.withdraw(prediction_id, current_tick=tick)
            return None
        schema = self.schemas[name]
        score = self.predictions.score(
            prediction.prediction_id,
            TargetObservation(name, key, value, event_time, observed_at, tick, source_id),
            schema, evaluated_tick=tick,
        )
        return (1.0 - score.value) if schema.metric == "accuracy" else score.value

    def observe_level0_features(self, features: Sequence[float], *, event_time: float,
                                observed_at: float, tick: int, learn: bool = True) -> float | None:
        key = f"level0@{tick}"
        values = _finite_vector(features, name="observed level-0 features").tolist()
        error = self._score_and_update(
            "next_l0_features", key, values, f"level0-source-{tick}",
            event_time, observed_at, tick,
        )
        self._observation_journal.append({
            "kind": "level0", "value": values, "target_name": "next_l0_features",
            "target_key": key, "source_id": f"level0-source-{tick}",
            "event_time": event_time, "observed_at": observed_at, "tick": tick,
            "learn": bool(learn),
            "issue_context": deepcopy(self._last_issue_context),
        })
        if error is not None and error > 0:
            self.last_signals = LearningSignals(
                temporal=error, relational=self.last_signals.relational,
                abstraction=self.last_signals.abstraction, task=self.last_signals.task,
                integrity_failures=self.last_signals.integrity_failures,
            )
            routed = self.error_router.route(self.last_signals)
            if learn and "temporal_feature_predictor" in routed:
                self.level0.update(values)
            if learn and "temporal_eligibility" in routed:
                self.temporal_credit.update(error, self.eligibility.values(prediction_cutoff_tick=tick))
        return error

    def observe_context_transition(self, current_context: str | None, next_context: str | None, *,
                                   source_id: str, event_time: float, observed_at: float,
                                   tick: int, learn: bool = True) -> float | None:
        key = f"context@{tick}"
        error = self._score_and_update(
            "next_context", key, next_context, source_id, event_time, observed_at, tick,
        )
        self._observation_journal.append({
            "kind": "context", "value": next_context, "target_name": "next_context",
            "target_key": key, "current_context": current_context, "source_id": source_id,
            "event_time": event_time, "observed_at": observed_at, "tick": tick,
            "learn": bool(learn),
            "issue_context": deepcopy(self._last_issue_context),
        })
        if error is not None and error > 0:
            self.last_signals = LearningSignals(
                temporal=self.last_signals.temporal, relational=self.last_signals.relational,
                abstraction=error, task=self.last_signals.task,
                integrity_failures=self.last_signals.integrity_failures,
            )
            routed = self.error_router.route(self.last_signals)
            if learn and "context_transition_learner" in routed:
                self.context_transitions.observe(current_context, next_context)
        return error

    def observe_relation(self, record: Any, *, tick: int, learn: bool = True) -> float | None:
        pattern = RelationPattern(record.relation_type.name, record.subject.entity_id,
                                  record.subject.entity_type, record.object.entity_id,
                                  record.object.entity_type, record.context)
        key = f"relation@{tick}"
        encoded = self.relations._encode(pattern)
        error = self._score_and_update("next_relation_pattern", key, encoded,
                                       record.instance_id, record.event_time,
                                       record.observed_at, tick)
        self._observation_journal.append({
            "kind": "relation", "value": encoded, "target_name": "next_relation_pattern",
            "target_key": key, "context": record.context, "source_id": record.instance_id,
            "event_time": record.event_time, "observed_at": record.observed_at, "tick": tick,
            "learn": bool(learn),
            "issue_context": deepcopy(self._last_issue_context),
        })
        if error is not None:
            self.last_signals = LearningSignals(
                temporal=self.last_signals.temporal, relational=error,
                abstraction=self.last_signals.abstraction, task=self.last_signals.task,
                integrity_failures=self.last_signals.integrity_failures,
            )
            routed = self.error_router.route(self.last_signals)
            if learn and "semantic_relation_learner" in routed:
                self.relations.observe(record)
        return error

    def observe_nary_event(self, event: Any, *, tick: int, learn: bool = True) -> float | None:
        pattern = EventRolePattern(event.event_type,
                                   tuple(sorted((p.role, p.entity_id, p.entity_type) for p in event.participants)),
                                   event.context)
        key = f"event@{tick}"
        encoded = self.event_roles._encode(pattern)
        error = self._score_and_update("next_event_role_pattern", key, encoded,
                                       event.event_id, event.event_time, event.observed_at, tick)
        self._observation_journal.append({
            "kind": "event_role", "value": encoded, "target_name": "next_event_role_pattern",
            "target_key": key, "context": event.context, "source_id": event.event_id,
            "event_time": event.event_time, "observed_at": event.observed_at, "tick": tick,
            "learn": bool(learn),
            "issue_context": deepcopy(self._last_issue_context),
        })
        if error is not None:
            self.last_signals = LearningSignals(
                temporal=self.last_signals.temporal, relational=self.last_signals.relational,
                abstraction=error, task=self.last_signals.task,
                integrity_failures=self.last_signals.integrity_failures,
            )
            routed = self.error_router.route(self.last_signals)
            if learn and "nary_event_role_learner" in routed:
                self.event_roles.observe(event)
        return error

    def reset_episode_eligibility(self, *, tick: int, observed_at: float) -> None:
        """Reset transient temporal eligibility at an episode boundary.

        The boundary is journaled so checkpoint continuation and replay reproduce
        the same event-credit isolation while learned temporal weights persist.
        """
        if (isinstance(tick, bool) or tick < 0 or not math.isfinite(observed_at)
            or observed_at < self._last_observed_at):
            raise ValueError("episode boundary tick/time must be valid and monotone")
        self.eligibility.reset(tick=tick)
        self._observation_journal.append({
            "kind": "episode_boundary", "tick": int(tick),
            "observed_at": float(observed_at),
        })

    def observe_eligibility(self, event: EligibilityEvent) -> None:
        self.eligibility.ingest(event)
        self._observation_journal.append({"kind": "eligibility", "value": event.__dict__})

    def advance_temporal(self, tick: int) -> dict:
        self.eligibility.advance(tick)
        values = self.eligibility.values(prediction_cutoff_tick=tick)
        return values

    def observe_temporal_error(self, error: float, *, tick: int, learn: bool = True) -> None:
        if not math.isfinite(error) or error < 0:
            raise ValueError("temporal error must be finite and non-negative")
        self._observation_journal.append({
            "kind": "temporal_error", "error": float(error), "tick": int(tick),
            "learn": bool(learn),
        })
        values = self.eligibility.values(prediction_cutoff_tick=tick)
        self.last_signals = LearningSignals(
            temporal=float(error), relational=self.last_signals.relational,
            abstraction=self.last_signals.abstraction, task=self.last_signals.task,
            integrity_failures=self.last_signals.integrity_failures,
        )
        routed = self.error_router.route(self.last_signals)
        if learn and "temporal_eligibility" in routed:
            self.temporal_credit.update(float(error), values)

    def observe_task_error(self, task_key: str, error: float, *, learn: bool = True) -> None:
        """Score the task channel's prior error-probability forecast, then update it.

        The target is the committed binary task outcome (1=solver error, 0=correct).
        This calibrates task-level reliability; it does not train or claim to be
        the deterministic answer executor.
        """
        if not task_key or not math.isfinite(error) or error < 0 or error > 1:
            raise ValueError("task outcome requires a key and a binary-range error")
        target = float(error > 0.0)
        predicted = self.task_outcomes.predict_error_probability(task_key)
        brier_error = (predicted - target) ** 2
        self._observation_journal.append({
            "kind": "task", "task_key": task_key, "target_error": target,
            "predicted_error_probability": predicted, "brier_error": brier_error,
            "learn": bool(learn),
        })
        self.last_signals = LearningSignals(
            temporal=self.last_signals.temporal, relational=self.last_signals.relational,
            abstraction=self.last_signals.abstraction, task=brier_error,
            integrity_failures=self.last_signals.integrity_failures,
        )
        routed = self.error_router.route(self.last_signals)
        if learn and "task_outcome_learner" in routed:
            self.task_outcomes.observe_error(task_key, target)

    def transaction_checkpoint(self) -> dict[str, Any]:
        """Capture rollback-scoped state without copying append-only histories."""
        self.predictions.begin_transaction()
        self.relations.begin_transaction()
        self.event_roles.begin_transaction()
        self.context_transitions.begin_transaction()
        self.temporal_credit.begin_transaction()
        self.task_outcomes.begin_transaction()
        return {
            "level0": self.level0.snapshot(),
            "eligibility": self.eligibility.snapshot(),
            "journal_count": len(self._observation_journal),
            "prediction_sequence": self._prediction_sequence,
            "last_observed_at": self._last_observed_at,
            "last_signals": self.last_signals,
            "last_issue_context": deepcopy(self._last_issue_context),
        }

    def commit_transaction(self) -> None:
        self.predictions.commit_transaction()
        self.relations.commit_transaction()
        self.event_roles.commit_transaction()
        self.context_transitions.commit_transaction()
        self.temporal_credit.commit_transaction()
        self.task_outcomes.commit_transaction()

    def rollback_transaction(self, state: Mapping[str, Any]) -> None:
        self.predictions.rollback_transaction()
        self.level0.restore(state["level0"])
        self.relations.rollback_transaction()
        self.event_roles.rollback_transaction()
        self.context_transitions.rollback_transaction()
        self.temporal_credit.rollback_transaction()
        self.task_outcomes.rollback_transaction()
        self.eligibility.restore(state["eligibility"])
        del self._observation_journal[int(state["journal_count"]):]
        self._prediction_sequence = int(state["prediction_sequence"])
        self._last_observed_at = float(state["last_observed_at"])
        self.last_signals = state["last_signals"]
        self._last_issue_context = deepcopy(state["last_issue_context"])

    def snapshot(self) -> dict:
        return {
            "schema": "h1-learning-runtime-v1",
            "enabled_channels": sorted(channel.value for channel in self.enabled_channels),
            "predictions": self.predictions.snapshot(),
            "level0": self.level0.snapshot(),
            "relations": self.relations.snapshot(),
            "event_roles": self.event_roles.snapshot(),
            "context_transitions": self.context_transitions.snapshot(),
            "task_outcomes": self.task_outcomes.snapshot(),
            "temporal_credit": self.temporal_credit.snapshot(),
            "eligibility": self.eligibility.snapshot(),
            "journal_count": len(self._observation_journal),
            "observation_journal": deepcopy(self._observation_journal),
            "prediction_sequence": self._prediction_sequence,
            "last_observed_at": self._last_observed_at,
            "last_signals": self.last_signals.as_dict(),
            "integrity_failures": list(self.last_signals.integrity_failures),
        }

    def restore(self, state: Mapping, *, preserve_observations: bool = False) -> None:
        if state.get("schema") != "h1-learning-runtime-v1":
            raise ValueError("learning runtime checkpoint schema mismatch")
        if frozenset(state.get("enabled_channels", ())) != frozenset(c.value for c in self.enabled_channels):
            raise ValueError("learning ablation configuration mismatch")
        local_journal = list(self._observation_journal)
        trusted_count = int(state["journal_count"])
        checkpoint_journal = deepcopy(list(state.get("observation_journal", ())))
        if trusted_count < 0 or trusted_count != len(checkpoint_journal):
            raise ValueError("learning checkpoint journal watermark is inconsistent")
        if preserve_observations and len(local_journal) >= trusted_count:
            if local_journal[:trusted_count] != checkpoint_journal:
                raise ValueError("learning observation journal prefix differs from checkpoint")
            newer_journal = local_journal[trusted_count:]
        else:
            newer_journal = []
        replay_journal = checkpoint_journal + newer_journal
        self.predictions.restore(state["predictions"])
        self.level0.restore(state["level0"])
        self.relations.restore(state["relations"])
        self.event_roles.restore(state["event_roles"])
        self.context_transitions.restore(state["context_transitions"])
        self.task_outcomes.restore(state["task_outcomes"])
        self.temporal_credit.restore(state["temporal_credit"])
        self.eligibility.restore(state["eligibility"])
        self._prediction_sequence = int(state["prediction_sequence"])
        self._last_observed_at = float(state["last_observed_at"])
        saved_signals = state.get("last_signals", {})
        self.last_signals = LearningSignals(
            temporal=float(saved_signals.get("temporal", 0.0)),
            relational=float(saved_signals.get("relational", 0.0)),
            abstraction=float(saved_signals.get("abstraction", 0.0)),
            task=float(saved_signals.get("task", 0.0)),
            integrity_failures=tuple(state.get("integrity_failures", ())),
        )
        # New labels received during candidate execution survive rollback and
        # are deterministically applied to the restored incumbent learners.
        self._observation_journal = replay_journal
        replayed_prediction_ticks = set()
        for item in newer_journal:
            if item["kind"] in ("level0", "relation", "event_role", "context"):
                issue = item.get("issue_context") or {
                    "tick": int(item["tick"]) - 1,
                    "cutoff": float(item["observed_at"]),
                    "context": item.get("context"),
                }
                prediction_tick = int(issue["tick"])
                if prediction_tick not in replayed_prediction_ticks:
                    self.begin_tick(
                        tick=prediction_tick, observed_at=float(issue["cutoff"]),
                        context=issue.get("context"),
                    )
                    replayed_prediction_ticks.add(prediction_tick)
                error = self._score_and_update(
                    item["target_name"], item["target_key"], item["value"],
                    item["source_id"], item["event_time"], item["observed_at"], item["tick"],
                )
                if error is not None and error > 0 and item.get("learn", True):
                    channel = (ErrorChannel.TEMPORAL if item["kind"] == "level0" else
                               ErrorChannel.RELATIONAL if item["kind"] == "relation" else
                               ErrorChannel.ABSTRACTION)
                    current = self.last_signals.as_dict()
                    current[channel.value] = error
                    self.last_signals = LearningSignals(
                        temporal=current["temporal"], relational=current["relational"],
                        abstraction=current["abstraction"], task=current["task"],
                        integrity_failures=self.last_signals.integrity_failures,
                    )
                    routed = self.error_router.route(self.last_signals)
                    if item["kind"] == "level0" and "temporal_feature_predictor" in routed:
                        self.level0.update(item["value"])
                    if item["kind"] == "level0" and "temporal_eligibility" in routed:
                        self.temporal_credit.update(error, self.eligibility.values(
                            prediction_cutoff_tick=int(item["tick"])))
                    if item["kind"] == "relation" and "semantic_relation_learner" in routed:
                        self.relations._counter.observe(
                            self.relations._key(item["context"]), item["value"])
                    if item["kind"] == "event_role" and "nary_event_role_learner" in routed:
                        self.event_roles._counter.observe(
                            self.event_roles._key(item["context"]), item["value"])
                    if item["kind"] == "context" and "context_transition_learner" in routed:
                        self.context_transitions.observe(item["current_context"], item["value"])
            elif item["kind"] == "task":
                # v1.3 journals the forecast and binary target separately so
                # rollback replay can reconstruct the same prequential update.
                if "target_error" in item and item.get("learn", True):
                    target_error = float(item["target_error"])
                    current = self.last_signals.as_dict()
                    self.last_signals = LearningSignals(
                        temporal=current["temporal"], relational=current["relational"],
                        abstraction=current["abstraction"],
                        task=float(item["brier_error"]),
                        integrity_failures=self.last_signals.integrity_failures,
                    )
                    routed = self.error_router.route(self.last_signals)
                    if "task_outcome_learner" in routed:
                        self.task_outcomes.observe_error(item["task_key"], target_error)
                elif item.get("learn", True) and item.get("error", 0.0) > 0:
                    # Backward-compatible replay of pre-v1.3 journal records.
                    self.task_outcomes.observe_error(item["task_key"], item["error"])
            elif item["kind"] == "temporal_error":
                values = self.eligibility.values(prediction_cutoff_tick=int(item["tick"]))
                current = self.last_signals.as_dict()
                current["temporal"] = float(item["error"])
                signals = LearningSignals(
                    temporal=current["temporal"], relational=current["relational"],
                    abstraction=current["abstraction"], task=current["task"],
                    integrity_failures=self.last_signals.integrity_failures,
                )
                self.last_signals = signals
                routed = self.error_router.route(signals)
                if item.get("learn", True) and "temporal_eligibility" in routed:
                    self.temporal_credit.update(float(item["error"]), values)
            elif item["kind"] == "episode_boundary":
                self.eligibility.reset(tick=int(item["tick"]))
            elif item["kind"] == "eligibility":
                event = EligibilityEvent(**item["value"])
                if event.observed_tick > self.eligibility._last_tick:
                    self.eligibility.advance(event.observed_tick)
                if (event.event_id, event.feature_id, event.channel) not in self.eligibility._states:
                    self.eligibility.ingest(event)
        self._last_observed_at = max(
            [self._last_observed_at] + [float(x.get("observed_at", 0.0)) for x in newer_journal]
        )
