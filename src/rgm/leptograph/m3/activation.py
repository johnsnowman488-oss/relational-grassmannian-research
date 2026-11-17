"""Predictive evidence, sufficiency and stateful activation are separated."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np

@dataclass
class RelationshipEvidence:
    # Compact numeric state: float32 masses/scores, int32 count, int16 slot.
    positive_mass: np.float32 = np.float32(0.0)
    negative_mass: np.float32 = np.float32(0.0)
    usefulness: np.float32 = np.float32(0.0)
    observed_count: np.int32 = np.int32(0)
    active: bool = False
    activation_score: np.float32 = np.float32(0.0)
    last_context_slot: np.int16 | None = None

    @property
    def balance(self) -> float:
        return self.positive_mass - self.negative_mass

    @property
    def sufficiency(self) -> float:
        return self.observed_count / (self.observed_count + 10.0)

@dataclass
class EvidenceActivation:
    """Per-relationship evidence ledger and hysteretic activation controller."""
    on_threshold: float = 0.35
    off_threshold: float = 0.20
    evidence_rate: float = 0.08
    usefulness_rate: float = 0.12
    minimum_observations: int = 5
    context_score_limit: float = 8.0
    states: dict[str, RelationshipEvidence] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (0 <= self.off_threshold < self.on_threshold <= 1):
            raise ValueError("activation thresholds must satisfy 0 <= off < on <= 1")
        if not (0 < self.evidence_rate <= 1 and 0 < self.usefulness_rate <= 1):
            raise ValueError("evidence rates must be in (0, 1]")
        if self.minimum_observations < 1:
            raise ValueError("minimum_observations must be positive")

    def update(self, relation_id: str, *, predictive_improvement: float | None,
               observed: bool, identifiable: bool, context_score: float,
               context_slot: int | None = None) -> RelationshipEvidence:
        """Update after prediction and target observation.

        Predictive improvement is a prequential diagnostic, not a causal effect.
        Missing observations do not count as negative evidence.
        """
        if not relation_id:
            raise ValueError("relation_id must be non-empty")
        state = self.states.setdefault(relation_id, RelationshipEvidence())
        if not observed or predictive_improvement is None:
            return state
        if not (-1.0 <= predictive_improvement <= 1.0):
            raise ValueError("predictive_improvement must be in [-1, 1]")
        state.observed_count = np.int32(int(state.observed_count) + 1)
        positive = max(0.0, predictive_improvement)
        negative = max(0.0, -predictive_improvement)
        rate = self.evidence_rate
        state.positive_mass = np.float32((1 - rate) * float(state.positive_mass) + rate * positive)
        state.negative_mass = np.float32((1 - rate) * float(state.negative_mass) + rate * negative)
        urate = self.usefulness_rate
        state.usefulness = np.float32((1 - urate) * float(state.usefulness) + urate * predictive_improvement)
        state.last_context_slot = np.int16(context_slot) if context_slot is not None else None
        confidence = 1.0 - (1.0 / (state.observed_count + 1.0) ** 0.5)
        evidence_strength = max(0.0, float(state.balance))
        state.activation_score = np.float32(
            max(0.0, min(1.0, 0.65 * float(state.usefulness) + 0.35 * evidence_strength)) * confidence
        )
        admissible = identifiable and context_score <= self.context_score_limit
        if state.active:
            if (not admissible) or state.activation_score <= self.off_threshold:
                state.active = False
        elif (admissible and state.observed_count >= self.minimum_observations
              and state.activation_score >= self.on_threshold):
            state.active = True
        return state

    def is_active(self, relation_id: str) -> bool:
        return self.states.get(relation_id, RelationshipEvidence()).active

    def snapshot(self, relation_id: str) -> dict[str, float | int | bool | None]:
        state = self.states[relation_id]
        return {
            "positive_mass": float(state.positive_mass), "negative_mass": float(state.negative_mass),
            "balance": float(state.balance), "usefulness": float(state.usefulness),
            "observed_count": int(state.observed_count), "sufficiency": float(state.sufficiency),
            "activation_score": float(state.activation_score), "active": state.active,
            "last_context_slot": int(state.last_context_slot) if state.last_context_slot is not None else None,
        }
