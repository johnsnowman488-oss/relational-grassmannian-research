"""Coupled hybrid adaptive-state model for HLG-M4 P6.

The implementation is an explicit synchronous, discrete-time operating model.
It reuses the repository SOE, CUSUM and candidate-revision primitives; it does
not claim a global stability theorem.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from rgm.memory import SOEMemory
from rgm.leptograph.m3.context import ContextBank, ContextSlot, ContextDecision
from rgm.leptograph.m3.estimation import MultiSourceRidge
from rgm.leptograph.m3.revision import CUSUMDetector, CandidateRevision
from rgm.leptograph.m3.activation import EvidenceActivation

class AdaptiveMode(str, Enum):
    NORMAL="NORMAL"; DETECT="DETECT"; FIT="FIT"; VALIDATE="VALIDATE"
    PROMOTED="PROMOTED"; ROLLBACK="ROLLBACK"; DORMANT="DORMANT"; RECOVERY="RECOVERY"


def _default_p6_context_bank() -> ContextBank:
    bank = ContextBank(
        np.eye(2), capacity=4, accept_threshold=10.0,
        novelty_threshold=25.0, ambiguity_margin=0.05, novelty_repeats=3,
    )
    bank.add_initial([0.0, 0.0], prior_covariance=0.2 * np.eye(2))
    return bank

@dataclass
class CoupledAdaptiveSystem:
    transition: np.ndarray = field(default_factory=lambda: np.array([[0.62,0.08],[0.05,0.58]],dtype=float))
    input_matrix: np.ndarray = field(default_factory=lambda: np.array([[0.15,0.0],[0.0,0.12]],dtype=float))
    max_state_norm: float = 25.0
    state: np.ndarray = field(default_factory=lambda: np.zeros(2,dtype=float))
    memory: SOEMemory = field(default_factory=lambda: SOEMemory(feature_dim=2))
    detector: CUSUMDetector = field(default_factory=lambda: CUSUMDetector(allowance=0.2,threshold=2.0))
    activation: EvidenceActivation = field(default_factory=EvidenceActivation)
    context_bank: ContextBank = field(default_factory=_default_p6_context_bank)
    estimator: MultiSourceRidge = field(default_factory=lambda: MultiSourceRidge({"lower": 2, "upper": 2}, 2, 2, ridge=1e-3, forgetting=0.995))
    last_context_slot: int | None = None
    revision: CandidateRevision = field(default_factory=lambda: CandidateRevision(np.eye(2)))
    mode: AdaptiveMode = AdaptiveMode.NORMAL
    trusted_snapshot: np.ndarray | None = None
    rollback_count: int = 0
    step_count: int = 0
    max_observed_norm: float = 0.0
    def __post_init__(self):
        self.transition=np.asarray(self.transition,dtype=float); self.input_matrix=np.asarray(self.input_matrix,dtype=float)
        self.state=np.asarray(self.state,dtype=float)
        if self.transition.shape!=(2,2) or self.input_matrix.shape!=(2,2) or self.state.shape!=(2,): raise ValueError("state matrices must be 2x2 and state length 2")
        if not np.all(np.isfinite(self.transition)) or not np.all(np.isfinite(self.input_matrix)) or not np.all(np.isfinite(self.state)): raise ValueError("system values must be finite")
        if self.max_state_norm<=0: raise ValueError("max_state_norm must be positive")
    def step(self, observation: np.ndarray, residual_score: float=0.0) -> np.ndarray:
        u=np.asarray(observation,dtype=float)
        if u.shape!=(2,) or not np.all(np.isfinite(u)): raise ValueError("observation must be a finite length-2 vector")
        if self.mode == AdaptiveMode.DORMANT:
            self.memory.advance(dt=1.0)
            self.state = self.transition @ self.state
            norm = float(np.linalg.norm(self.state))
            self.max_observed_norm = max(self.max_observed_norm, norm)
            if not np.all(np.isfinite(self.state)) or norm > self.max_state_norm:
                raise FloatingPointError("dormant P6 state exceeded declared finite-horizon envelope")
            self.step_count += 1
            return self.state.copy()
        self.memory.update(u,dt=1.0)
        # SOEMemory stores impulse responses, whose DC gain is
        # 1 / (1 - exp(-gamma)).  Normalize each channel by its inverse
        # DC gain before aggregation so slow traces do not amplify a
        # constant bounded observation by O(1/gamma).
        dc_normalizers = 1.0 - np.exp(-self.memory.decay_rates)
        memory_signal = np.mean(
            dc_normalizers[:, None] * self.memory.channels, axis=0
        )
        recovery_gain = 0.5 if self.mode == AdaptiveMode.RECOVERY else 1.0
        self.state=self.transition@self.state+recovery_gain*self.input_matrix@np.array([u[0],memory_signal[1]])
        norm=float(np.linalg.norm(self.state)); self.max_observed_norm=max(self.max_observed_norm,norm)
        if not np.all(np.isfinite(self.state)) or norm>self.max_state_norm: raise FloatingPointError("coupled state exceeded declared finite-horizon envelope")
        alarm=self.detector.update(float(residual_score))
        if alarm and self.mode in {AdaptiveMode.NORMAL,AdaptiveMode.DORMANT}: self.mode=AdaptiveMode.DETECT
        self.step_count+=1
        return self.state.copy()

    def observe_adaptive_state(self, sources: dict[str, np.ndarray], context: np.ndarray,
                               target: np.ndarray) -> dict:
        """Prequentially update context, estimator and relation evidence as one P6 state."""
        if self.mode == AdaptiveMode.DORMANT:
            return {"context_decision": "DORMANT", "context_slot": self.last_context_slot,
                    "active_relations": {key: self.activation.is_active(key) for key in sources}}
        point = np.asarray(context, dtype=np.float64)
        if point.shape != (self.context_bank.dimension,) or not np.all(np.isfinite(point)):
            raise ValueError("P6 context feature must be finite and match the context bank")
        decision, slot_id, scores = self.context_bank.route(point)
        if decision == ContextDecision.ACCEPT and slot_id is not None:
            safe_context = point
            context_score = float(scores[slot_id])
            for slot in self.context_bank.slots:
                if slot.slot_id == slot_id:
                    slot.update(point)
                    break
            self.last_context_slot = int(slot_id)
        elif decision == ContextDecision.NOVEL:
            self.context_bank.observe_novel(point)
            safe_context = np.zeros(self.context_bank.dimension, dtype=np.float64)
            context_score = float("inf")
            self.last_context_slot = None
        else:
            safe_context = np.zeros(self.context_bank.dimension, dtype=np.float64)
            context_score = float("inf")
            self.last_context_slot = None

        shadow_prediction = self.estimator.predict(
            sources, safe_context, source_gates={"lower": 1.0, "upper": 1.0}
        )
        y = np.asarray(target, dtype=np.float64)
        if y.shape != (self.estimator.target_dimension,) or not np.all(np.isfinite(y)):
            raise ValueError("P6 estimator target must be finite and match target dimension")
        baseline = max(float(np.dot(y, y)), 1e-10)
        error = float(np.dot(y - shadow_prediction, y - shadow_prediction))
        improvement = float(np.clip(1.0 - error / baseline, -1.0, 1.0))
        self.estimator.update(
            sources, safe_context, y, source_gates={"lower": 1.0, "upper": 1.0}
        )
        identifiability = self.estimator.conditional_identifiability()
        for key in ("lower", "upper"):
            state = self.activation.update(
                key, predictive_improvement=improvement, observed=True,
                identifiable=bool(identifiability[key]["identifiable"]),
                context_score=context_score, context_slot=slot_id,
            )
            if (slot_id is not None and bool(identifiability[key]["identifiable"])):
                self.context_bank.set_operator(
                    int(slot_id), key, self.estimator.source_operator(key)
                )
        return {
            "context_decision": decision.value,
            "context_slot": self.last_context_slot,
            "predictive_improvement": improvement,
            "identifiability": identifiability,
            "active_relations": {
                key: self.activation.is_active(key) for key in ("lower", "upper")
            },
            "estimator_samples": int(self.estimator.sample_count),
            "context_slot_count": len(self.context_bank.slots),
        }
    def start_candidate(self, operator: np.ndarray):
        if self.mode not in {AdaptiveMode.NORMAL,AdaptiveMode.DETECT,AdaptiveMode.RECOVERY}: raise RuntimeError("candidate cannot start in current mode")
        self.trusted_snapshot=self.revision.accepted_operator.copy()
        self.revision.start_candidate(operator); self.mode=AdaptiveMode.FIT
    def validate_candidate(self, incumbent_loss: float, candidate_loss: float, identifiable: bool) -> bool:
        if self.mode!=AdaptiveMode.FIT: raise RuntimeError("no candidate is being fitted")
        self.mode=AdaptiveMode.VALIDATE
        promoted=self.revision.evaluate(incumbent_loss=incumbent_loss,candidate_loss=candidate_loss,identifiable=identifiable)
        self.mode=AdaptiveMode.PROMOTED if promoted else AdaptiveMode.NORMAL
        return promoted
    def rollback(self):
        if self.mode!=AdaptiveMode.PROMOTED or self.trusted_snapshot is None: raise RuntimeError("rollback requires a promoted candidate and trusted snapshot")
        self.revision.accepted_operator=self.trusted_snapshot.copy()
        self.rollback_count+=1; self.mode=AdaptiveMode.ROLLBACK
    def update_relation_evidence(self, relation_id: str, predictive_improvement: float | None, *, observed: bool, identifiable: bool, context_score: float, context_slot: int | None=None):
        """Route post-query evidence through the existing M3 activation controller."""
        return self.activation.update(relation_id,predictive_improvement=predictive_improvement,observed=observed,identifiable=identifiable,context_score=context_score,context_slot=context_slot)
    def enter_dormancy(self):
        if self.mode not in {AdaptiveMode.NORMAL,AdaptiveMode.DETECT}: raise RuntimeError("cannot enter dormancy during candidate lifecycle")
        self.mode=AdaptiveMode.DORMANT
    def reactivate(self):
        if self.mode!=AdaptiveMode.DORMANT: raise RuntimeError("system is not dormant")
        self.mode=AdaptiveMode.RECOVERY
    def finish_recovery(self):
        if self.mode!=AdaptiveMode.RECOVERY: raise RuntimeError("system is not recovering")
        self.mode=AdaptiveMode.NORMAL
    @property
    def transition_spectral_radius(self) -> float:
        return float(np.max(np.abs(np.linalg.eigvals(self.transition))))
