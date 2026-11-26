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
    subject_type: str
    object_type: str
    context: str | None

    def __post_init__(self) -> None:
        if not all((self.relation_type, self.subject_type, self.object_type)):
            raise ValueError("relation pattern requires a typed relation signature")


@dataclass(frozen=True)
class EventRolePattern:
    event_type: str
    roles: tuple[tuple[str, str], ...]
    context: str | None

    def __post_init__(self) -> None:
        if not self.event_type or len(self.roles) < 2:
            raise ValueError("event-role pattern requires an event type and at least two roles")
        names = [name for name, _ in self.roles]
        if len(names) != len(set(names)) or any(not a or not b for a, b in self.roles):
            raise ValueError("event-role pattern roles must be unique and typed")


class _PatternCounter:
    """Deterministic empirical learner for typed semantic patterns."""
    def __init__(self) -> None:
        self.counts: dict[str, dict[str, int]] = {}

    def observe(self, key: str, pattern: str) -> None:
        bucket = self.counts.setdefault(key, {})
        bucket[pattern] = bucket.get(pattern, 0) + 1

    def predict(self, key: str) -> str | None:
        bucket = self.counts.get(key, {})
        if not bucket:
            return None
        # Deterministic tie-break is lexical, never dependent on hash iteration.
        return min(bucket, key=lambda p: (-bucket[p], p))

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


class SemanticRelationLearner:
    """Predicts typed relation existence/signature, not numeric feature vectors."""
    def __init__(self) -> None:
        self._counter = _PatternCounter()

    @staticmethod
    def _key(subject_type: str, context: str | None) -> str:
        return fingerprint({"subject_type": subject_type, "context": context})

    @staticmethod
    def _encode(pattern: RelationPattern) -> str:
        return json.dumps(pattern.__dict__, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _decode(value: str) -> RelationPattern:
        return RelationPattern(**json.loads(value))

    def observe(self, record: Any) -> None:
        pattern = RelationPattern(record.relation_type.name, record.subject.entity_type,
                                  record.object.entity_type, record.context)
        self._counter.observe(self._key(record.subject.entity_type, record.context), self._encode(pattern))

    def predict(self, subject_type: str, context: str | None = None) -> RelationPattern | None:
        value = self._counter.predict(self._key(subject_type, context))
        return None if value is None else self._decode(value)

    def snapshot(self) -> dict:
        return self._counter.snapshot()

    def restore(self, state: Mapping) -> None:
        self._counter.restore(state)


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
        roles = tuple(sorted((p.role, p.entity_type) for p in event.participants))
        pattern = EventRolePattern(event.event_type, roles, event.context)
        self._counter.observe(self._key(event.context), self._encode(pattern))

    def predict(self, context: str | None = None) -> EventRolePattern | None:
        value = self._counter.predict(self._key(context))
        return None if value is None else self._decode(value)

    def snapshot(self) -> dict:
        return self._counter.snapshot()

    def restore(self, state: Mapping) -> None:
        self._counter.restore(state)


class TemporalCreditLearner:
    """Error-weighted temporal parameter learner driven by event-resolved eligibility."""
    def __init__(self, learning_rate: float = 0.01):
        if not math.isfinite(learning_rate) or learning_rate <= 0:
            raise ValueError("temporal learning rate must be positive and finite")
        self.learning_rate = float(learning_rate)
        self.weights: dict[str, float] = {}

    def update(self, error: float, eligibility: Mapping[tuple[str, str, str], float]) -> None:
        if not math.isfinite(error) or error < 0:
            raise ValueError("temporal error must be finite and non-negative")
        if error == 0:
            return
        for (event_id, feature_id, channel), trace in sorted(eligibility.items()):
            key = json.dumps((event_id, feature_id, channel), separators=(",", ":"))
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

    def observe_error(self, task_key: str, error: float) -> None:
        if not task_key or not math.isfinite(error) or error < 0:
            raise ValueError("task outcome requires a key and finite non-negative error")
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


class LearningRuntime:
    """Shared HLA/HLB prediction and learning cycle.

    The model checkpoint is rollback-scoped. The compact observation journal is
    append-only: restoring a candidate checkpoint restores the incumbent model,
    then deterministically replays labels received after that checkpoint into
    the incumbent learners. It stores typed learning labels, not HLA witnesses.
    """
    def __init__(self, *, eligibility_decay: float = 0.9, eligibility_capacity: int = 4096,
                 eligibility_config_fingerprint: str = "h1-soe-eligibility-v1"):
        self.schemas = {
            "next_relation_pattern": TargetSchema("next_relation_pattern", Level.L1, "relation", 1, "exact_match"),
            "next_event_role_pattern": TargetSchema("next_event_role_pattern", Level.L1, "relation", 1, "exact_match"),
        }
        self.predictions = PredictionJournal()
        self.relations = SemanticRelationLearner()
        self.event_roles = NaryEventRoleLearner()
        self.task_outcomes = TaskOutcomeLearner()
        self.temporal_credit = TemporalCreditLearner()
        self.eligibility = EligibilityLedger(decay=eligibility_decay, capacity=eligibility_capacity,
                                             config_fingerprint=eligibility_config_fingerprint)
        self.error_router = ErrorRouter([
            ParameterRoute("temporal_eligibility", frozenset({ErrorChannel.TEMPORAL})),
            ParameterRoute("semantic_relation_learner", frozenset({ErrorChannel.RELATIONAL})),
            ParameterRoute("nary_event_role_learner", frozenset({ErrorChannel.ABSTRACTION})),
            ParameterRoute("task_outcome_learner", frozenset({ErrorChannel.TASK})),
        ])
        self._observation_journal: list[dict] = []
        self._prediction_sequence = 0
        self._last_observed_at = 0.0
        self.last_signals = LearningSignals()

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

    def begin_tick(self, *, tick: int, observed_at: float, subject_type: str | None = None,
                   context: str | None = None) -> tuple[Prediction, ...]:
        if tick < 0 or not math.isfinite(observed_at) or observed_at < self._last_observed_at:
            raise ValueError("learning tick/time must be monotone")
        self._last_observed_at = observed_at
        issued = []
        if subject_type:
            pattern = self.relations.predict(subject_type, context)
            if pattern is not None:
                self._prediction_sequence += 1
                schema = self.schemas["next_relation_pattern"]
                prediction = Prediction(
                    f"lrn-rel-{self._prediction_sequence}", Level.L1, schema.name,
                    f"relation@{tick + 1}", tick, observed_at, schema.horizon_ticks,
                    observed_at, self.relations._encode(pattern), fingerprint(self.relations.snapshot()),
                    fingerprint(schema.__dict__),
                )
                self.predictions.issue(prediction)
                issued.append(prediction)
        role_pattern = self.event_roles.predict(context)
        if role_pattern is not None:
            self._prediction_sequence += 1
            schema = self.schemas["next_event_role_pattern"]
            prediction = Prediction(
                f"lrn-role-{self._prediction_sequence}", Level.L1, schema.name,
                f"event@{tick + 1}", tick, observed_at, schema.horizon_ticks,
                observed_at, self.event_roles._encode(role_pattern), fingerprint(self.event_roles.snapshot()),
                fingerprint(schema.__dict__),
            )
            self.predictions.issue(prediction)
            issued.append(prediction)
        return tuple(issued)

    def _score_and_update(self, name: str, key: str, value: Any, source_id: str,
                          event_time: float, observed_at: float, tick: int) -> float | None:
        matches = [p for p in self.predictions._predictions.values()
                   if p.target_name == name and p.target_key == key
                   and p.status is PredictionStatus.ISSUED]
        if not matches:
            return None
        prediction = max(matches, key=lambda p: p.issued_tick)
        schema = self.schemas[name]
        score = self.predictions.score(
            prediction.prediction_id,
            TargetObservation(name, key, value, event_time, observed_at, tick, source_id),
            schema, evaluated_tick=tick,
        )
        return score.value

    def observe_relation(self, record: Any, *, tick: int) -> float | None:
        pattern = RelationPattern(record.relation_type.name, record.subject.entity_type,
                                  record.object.entity_type, record.context)
        key = f"relation@{tick}"
        encoded = self.relations._encode(pattern)
        error = self._score_and_update("next_relation_pattern", key, encoded,
                                       record.instance_id, record.event_time,
                                       record.observed_at, tick)
        self._observation_journal.append({
            "kind": "relation", "value": encoded, "target_name": "next_relation_pattern",
            "target_key": key, "subject_type": record.subject.entity_type,
            "context": record.context, "source_id": record.instance_id,
            "event_time": record.event_time, "observed_at": record.observed_at, "tick": tick,
        })
        if error is not None:
            self.last_signals = LearningSignals(relational=error)
            routed = self.error_router.route(self.last_signals)
            if "semantic_relation_learner" in routed:
                self.relations.observe(record)
        return error

    def observe_nary_event(self, event: Any, *, tick: int) -> float | None:
        pattern = EventRolePattern(event.event_type,
                                   tuple(sorted((p.role, p.entity_type) for p in event.participants)),
                                   event.context)
        key = f"event@{tick}"
        encoded = self.event_roles._encode(pattern)
        error = self._score_and_update("next_event_role_pattern", key, encoded,
                                       event.event_id, event.event_time, event.observed_at, tick)
        self._observation_journal.append({
            "kind": "event_role", "value": encoded, "target_name": "next_event_role_pattern",
            "target_key": key, "context": event.context, "source_id": event.event_id,
            "event_time": event.event_time, "observed_at": event.observed_at, "tick": tick,
        })
        if error is not None:
            self.last_signals = LearningSignals(abstraction=error)
            routed = self.error_router.route(self.last_signals)
            if "nary_event_role_learner" in routed:
                self.event_roles.observe(event)
        return error

    def observe_eligibility(self, event: EligibilityEvent) -> None:
        self._observation_journal.append({"kind": "eligibility", "value": event.__dict__})
        self.eligibility.ingest(event)

    def advance_temporal(self, tick: int) -> dict:
        self.eligibility.advance(tick)
        values = self.eligibility.values(prediction_cutoff_tick=tick)
        return values

    def observe_temporal_error(self, error: float, *, tick: int) -> None:
        self._observation_journal.append({"kind": "temporal_error", "error": float(error), "tick": int(tick)})
        values = self.eligibility.values(prediction_cutoff_tick=tick)
        self.last_signals = LearningSignals(temporal=float(error))
        routed = self.error_router.route(self.last_signals)
        if "temporal_eligibility" in routed:
            self.temporal_credit.update(float(error), values)

    def observe_task_error(self, task_key: str, error: float) -> None:
        self._observation_journal.append({"kind": "task", "task_key": task_key, "error": float(error)})
        if error > 0:
            self.last_signals = LearningSignals(task=error)
            routed = self.error_router.route(self.last_signals)
            if "task_outcome_learner" in routed:
                self.task_outcomes.observe_error(task_key, error)

    def snapshot(self) -> dict:
        return {
            "schema": "h1-learning-runtime-v1",
            "predictions": self.predictions.snapshot(),
            "relations": self.relations.snapshot(),
            "event_roles": self.event_roles.snapshot(),
            "task_outcomes": self.task_outcomes.snapshot(),
            "temporal_credit": self.temporal_credit.snapshot(),
            "eligibility": self.eligibility.snapshot(),
            "journal_count": len(self._observation_journal),
            "observation_journal": deepcopy(self._observation_journal),
            "prediction_sequence": self._prediction_sequence,
            "last_observed_at": self._last_observed_at,
            "last_signals": self.last_signals.as_dict(),
        }

    def restore(self, state: Mapping) -> None:
        if state.get("schema") != "h1-learning-runtime-v1":
            raise ValueError("learning runtime checkpoint schema mismatch")
        local_journal = list(self._observation_journal)
        trusted_count = int(state["journal_count"])
        checkpoint_journal = deepcopy(list(state.get("observation_journal", ())))
        if trusted_count < 0 or trusted_count != len(checkpoint_journal):
            raise ValueError("learning checkpoint journal watermark is inconsistent")
        if len(local_journal) >= trusted_count:
            newer_journal = local_journal[trusted_count:]
        else:
            newer_journal = []
        replay_journal = checkpoint_journal + newer_journal
        self.predictions.restore(state["predictions"])
        self.relations.restore(state["relations"])
        self.event_roles.restore(state["event_roles"])
        self.task_outcomes.restore(state["task_outcomes"])
        self.temporal_credit.restore(state["temporal_credit"])
        self.eligibility.restore(state["eligibility"])
        self._prediction_sequence = int(state["prediction_sequence"])
        self._last_observed_at = float(state["last_observed_at"])
        # New labels received during candidate execution survive rollback and
        # are deterministically applied to the restored incumbent learners.
        self._observation_journal = replay_journal
        for item in newer_journal:
            if item["kind"] in ("relation", "event_role"):
                error = self._score_and_update(
                    item["target_name"], item["target_key"], item["value"],
                    item["source_id"], item["event_time"], item["observed_at"], item["tick"],
                )
                if error is not None and error > 0:
                    channel = ErrorChannel.RELATIONAL if item["kind"] == "relation" else ErrorChannel.ABSTRACTION
                    self.last_signals = LearningSignals(**{channel.value: error})
                    routed = self.error_router.route(self.last_signals)
                    if item["kind"] == "relation" and "semantic_relation_learner" in routed:
                        self.relations._counter.observe(
                            self.relations._key(item["subject_type"], item["context"]), item["value"])
                    if item["kind"] == "event_role" and "nary_event_role_learner" in routed:
                        self.event_roles._counter.observe(
                            self.event_roles._key(item["context"]), item["value"])
            elif item["kind"] == "task":
                if item["error"] > 0:
                    self.task_outcomes.observe_error(item["task_key"], item["error"])
            elif item["kind"] == "temporal_error":
                self.observe_temporal_error(item["error"], tick=int(item["tick"]))
            elif item["kind"] == "eligibility":
                event = EligibilityEvent(**item["value"])
                if event.observed_tick > self.eligibility._last_tick:
                    self.eligibility.advance(event.observed_tick)
                if (event.event_id, event.feature_id, event.channel) not in self.eligibility._states:
                    self.eligibility.ingest(event)
        self._last_observed_at = max(
            [self._last_observed_at] + [float(x.get("observed_at", 0.0)) for x in local_journal[trusted_count:]]
        )
