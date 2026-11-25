"""P6 controller closed around the actual HLA/HLB persistent hierarchy runtime.

The controller observes native upper-level state summaries and injects its
accepted two-dimensional control operator into the level-2 context feature.
The wrapper checkpoints and rolls back the hierarchy, native runtime and P6
controller as one transaction.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Mapping, Sequence

import numpy as np

from rgm.memory import SOEMemory
from rgm.leptograph.m3.activation import EvidenceActivation, RelationshipEvidence
from rgm.leptograph.m3.context import ContextBank, ContextSlot
from rgm.leptograph.m3.estimation import MultiSourceRidge
from rgm.leptograph.m3.revision import CUSUMDetector, CandidateRevision
from rgm.leptograph.m4.hierarchical import (
    CompositeLifecycle, HierarchicalRuntimeDirector,
)
from rgm.leptograph.m4.stability import AdaptiveMode, CoupledAdaptiveSystem


def _fingerprint(payload: Mapping) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _context_snapshot(bank: ContextBank) -> dict:
    return {
        "metric": bank.metric.tolist(), "capacity": int(bank.capacity),
        "regularisation": float(bank.regularisation),
        "accept_threshold": float(bank.accept_threshold),
        "novelty_threshold": float(bank.novelty_threshold),
        "ambiguity_margin": float(bank.ambiguity_margin),
        "novelty_repeats": int(bank.novelty_repeats),
        "full_bank_policy": bank.full_bank_policy,
        "store_scatter": bool(bank.store_scatter),
        "slots": [{
            "slot_id": int(slot.slot_id), "mean": slot.mean.tolist(),
            "scatter": slot.scatter.tolist(), "count": int(slot.count),
            "novelty_hits": int(slot.novelty_hits),
        } for slot in bank.slots],
        "next_id": int(bank._next_id),
        "pending": [np.asarray(value, dtype=np.float64).tolist() for value in bank._pending],
        "relation_operators": {
            str(slot_id): {key: value.tolist() for key, value in sorted(operators.items())}
            for slot_id, operators in sorted(bank._relation_operators.items())
        },
    }


def _context_from_snapshot(state: Mapping) -> ContextBank:
    bank = ContextBank(
        metric=np.asarray(state["metric"], dtype=np.float64),
        capacity=int(state["capacity"]),
        regularisation=float(state["regularisation"]),
        accept_threshold=float(state["accept_threshold"]),
        novelty_threshold=float(state["novelty_threshold"]),
        ambiguity_margin=float(state["ambiguity_margin"]),
        novelty_repeats=int(state["novelty_repeats"]),
        full_bank_policy=str(state["full_bank_policy"]),
        store_scatter=bool(state["store_scatter"]),
    )
    bank.slots = []
    for item in state["slots"]:
        mean = np.asarray(item["mean"], dtype=np.float64)
        scatter = np.asarray(item["scatter"], dtype=np.float64)
        if (mean.shape != (bank.dimension,) or not np.all(np.isfinite(mean))
                or scatter.shape not in ((0,), (bank.dimension, bank.dimension))
                or not np.all(np.isfinite(scatter)) or int(item["count"]) < 1
                or int(item["novelty_hits"]) < 0):
            raise ValueError("invalid P6 context slot checkpoint")
        bank.slots.append(ContextSlot(
            slot_id=int(item["slot_id"]), mean=mean, scatter=scatter,
            count=int(item["count"]), novelty_hits=int(item["novelty_hits"]),
        ))
    bank._next_id = int(state["next_id"])
    bank._pending = [np.asarray(value, dtype=np.float64) for value in state["pending"]]
    bank._relation_operators = {
        int(slot_id): {key: np.asarray(value, dtype=np.float64)
                       for key, value in operators.items()}
        for slot_id, operators in state["relation_operators"].items()
    }
    return bank


def _estimator_snapshot(estimator: MultiSourceRidge) -> dict:
    return {
        "source_dimensions": dict(estimator.source_dimensions),
        "context_dimension": int(estimator.context_dimension),
        "target_dimension": int(estimator.target_dimension),
        "ridge": float(estimator.ridge), "forgetting": float(estimator.forgetting),
        "gram_upper": estimator._gram_upper.tolist(), "cross": estimator.cross.tolist(),
        "sample_count": int(estimator.sample_count),
        "prediction_count": int(estimator.prediction_count),
        "update_count": int(estimator.update_count),
    }


def _estimator_from_snapshot(state: Mapping) -> MultiSourceRidge:
    estimator = MultiSourceRidge(
        source_dimensions={key: int(value) for key, value in state["source_dimensions"].items()},
        context_dimension=int(state["context_dimension"]),
        target_dimension=int(state["target_dimension"]),
        ridge=float(state["ridge"]), forgetting=float(state["forgetting"]),
    )
    gram_upper = np.asarray(state["gram_upper"], dtype=np.float64)
    cross = np.asarray(state["cross"], dtype=np.float64)
    if gram_upper.shape != estimator._gram_upper.shape or cross.shape != estimator.cross.shape:
        raise ValueError("P6 estimator checkpoint dimensions do not match its configuration")
    if not np.all(np.isfinite(gram_upper)) or not np.all(np.isfinite(cross)):
        raise ValueError("P6 estimator checkpoint contains non-finite sufficient statistics")
    estimator._gram_upper = gram_upper.copy()
    estimator.cross = cross.copy()
    estimator.sample_count = int(state["sample_count"])
    estimator.prediction_count = int(state["prediction_count"])
    estimator.update_count = int(state["update_count"])
    if min(estimator.sample_count, estimator.prediction_count, estimator.update_count) < 0:
        raise ValueError("P6 estimator checkpoint counters must be non-negative")
    return estimator


def _p6_snapshot(model: CoupledAdaptiveSystem) -> dict:
    activation = model.activation
    revision = model.revision
    return {
        "transition": model.transition.tolist(),
        "input_matrix": model.input_matrix.tolist(),
        "max_state_norm": float(model.max_state_norm),
        "state": model.state.tolist(),
        "memory": model.memory.to_dict(),
        "detector": {
            "allowance": float(model.detector.allowance),
            "threshold": float(model.detector.threshold),
            "statistic": float(model.detector.statistic),
            "observations": int(model.detector.observations),
            "alarms": int(model.detector.alarms),
        },
        "activation": {
            "on_threshold": float(activation.on_threshold),
            "off_threshold": float(activation.off_threshold),
            "evidence_rate": float(activation.evidence_rate),
            "usefulness_rate": float(activation.usefulness_rate),
            "minimum_observations": int(activation.minimum_observations),
            "context_score_limit": float(activation.context_score_limit),
            "states": {
                key: {
                    "positive_mass": float(value.positive_mass),
                    "negative_mass": float(value.negative_mass),
                    "usefulness": float(value.usefulness),
                    "observed_count": int(value.observed_count),
                    "active": bool(value.active),
                    "activation_score": float(value.activation_score),
                    "last_context_slot": int(value.last_context_slot)
                    if value.last_context_slot is not None else None,
                }
                for key, value in sorted(activation.states.items())
            },
        },
        "revision": {
            "accepted_operator": revision.accepted_operator.tolist(),
            "candidate_operator": None if revision.candidate_operator is None
            else revision.candidate_operator.tolist(),
            "candidate_active": bool(revision.candidate_active),
            "revision_count": int(revision.revision_count),
            "rejection_count": int(revision.rejection_count),
            "history": copy.deepcopy(revision.history),
        },
        "mode": model.mode.value,
        "trusted_snapshot": None if model.trusted_snapshot is None
        else model.trusted_snapshot.tolist(),
        "rollback_count": int(model.rollback_count),
        "step_count": int(model.step_count),
        "max_observed_norm": float(model.max_observed_norm),
        "context_bank": _context_snapshot(model.context_bank),
        "estimator": _estimator_snapshot(model.estimator),
        "last_context_slot": model.last_context_slot,
    }


def _p6_from_snapshot(state: Mapping) -> CoupledAdaptiveSystem:
    detector = CUSUMDetector(**dict(state["detector"]))
    activation_state = state["activation"]
    activation = EvidenceActivation(
        on_threshold=float(activation_state["on_threshold"]),
        off_threshold=float(activation_state["off_threshold"]),
        evidence_rate=float(activation_state["evidence_rate"]),
        usefulness_rate=float(activation_state["usefulness_rate"]),
        minimum_observations=int(activation_state["minimum_observations"]),
        context_score_limit=float(activation_state["context_score_limit"]),
    )
    for key, value in activation_state["states"].items():
        activation.states[str(key)] = RelationshipEvidence(
            positive_mass=np.float32(value["positive_mass"]),
            negative_mass=np.float32(value["negative_mass"]),
            usefulness=np.float32(value["usefulness"]),
            observed_count=np.int32(value["observed_count"]),
            active=bool(value["active"]),
            activation_score=np.float32(value["activation_score"]),
            last_context_slot=None if value["last_context_slot"] is None
            else np.int16(value["last_context_slot"]),
        )
    revision_state = state["revision"]
    revision = CandidateRevision(
        accepted_operator=np.asarray(revision_state["accepted_operator"], dtype=np.float64),
        candidate_operator=None if revision_state["candidate_operator"] is None
        else np.asarray(revision_state["candidate_operator"], dtype=np.float64),
        candidate_active=bool(revision_state["candidate_active"]),
        revision_count=int(revision_state["revision_count"]),
        rejection_count=int(revision_state["rejection_count"]),
        history=copy.deepcopy(list(revision_state["history"])),
    )
    trusted = state["trusted_snapshot"]
    context_bank = _context_from_snapshot(state["context_bank"])
    estimator = _estimator_from_snapshot(state["estimator"])
    model = CoupledAdaptiveSystem(
        transition=np.asarray(state["transition"], dtype=np.float64),
        input_matrix=np.asarray(state["input_matrix"], dtype=np.float64),
        max_state_norm=float(state["max_state_norm"]),
        state=np.asarray(state["state"], dtype=np.float64),
        memory=SOEMemory.from_dict(dict(state["memory"])),
        detector=detector,
        activation=activation,
        context_bank=context_bank,
        estimator=estimator,
        last_context_slot=None if state["last_context_slot"] is None else int(state["last_context_slot"]),
        revision=revision,
        mode=AdaptiveMode(state["mode"]),
        trusted_snapshot=None if trusted is None else np.asarray(trusted, dtype=np.float64),
        rollback_count=int(state["rollback_count"]),
        step_count=int(state["step_count"]),
        max_observed_norm=float(state["max_observed_norm"]),
    )
    if (not math.isfinite(model.max_observed_norm) or model.max_observed_norm < 0
            or not math.isfinite(model.max_state_norm) or model.max_state_norm <= 0
            or float(np.linalg.norm(model.state)) > model.max_state_norm):
        raise ValueError("invalid or out-of-envelope P6 state in checkpoint")
    return model


class P6RuntimeCoupler:
    """Closed-loop P6 execution and composite checkpoint/rollback manager."""
    schema_version = "P6-H1-0.3.0"

    def __init__(
        self,
        director: HierarchicalRuntimeDirector,
        *,
        model: CoupledAdaptiveSystem | None = None,
        hierarchy_lifecycle: CompositeLifecycle | None = None,
        readout_gain: float = 1.0,
        control_gain: float = 1.0,
        observation_transform: str = "identity",
    ):
        self.director = director
        self.hierarchy_lifecycle = hierarchy_lifecycle or CompositeLifecycle(director)
        self.model = model or CoupledAdaptiveSystem()
        if not np.isfinite(readout_gain) or readout_gain < 0:
            raise ValueError("readout_gain must be finite and non-negative")
        if not np.isfinite(control_gain) or control_gain < 0:
            raise ValueError("control_gain must be finite and non-negative")
        if observation_transform not in ("identity", "tanh"):
            raise ValueError("observation_transform must be 'identity' or 'tanh'")
        self.readout_gain = float(readout_gain)
        self.control_gain = float(control_gain)
        self.observation_transform = observation_transform
        self.version = 0
        self._trusted: dict | None = None
        self._rollback_point: dict | None = None

    def _capture(self) -> dict:
        hierarchy = self.hierarchy_lifecycle._capture_checkpoint()
        state = {
            "schema_version": self.schema_version,
            "hierarchy": hierarchy,
            "p6": _p6_snapshot(self.model),
            "coupling_config": {
                "readout_gain": self.readout_gain,
                "control_gain": self.control_gain,
                "observation_transform": self.observation_transform,
            },
            "version": self.version,
        }
        state["fingerprint"] = _fingerprint({
            "hierarchy": state["hierarchy"],
            "p6": state["p6"],
            "coupling_config": state["coupling_config"],
            "version": state["version"],
        })
        return state

    def snapshot(self) -> dict:
        return copy.deepcopy(self._capture())

    def checkpoint(self) -> dict:
        state = self._capture()
        self._trusted = copy.deepcopy(state)
        self._rollback_point = None
        return copy.deepcopy(state)

    def restore(self, state: Mapping) -> None:
        if state.get("schema_version") != self.schema_version:
            raise ValueError("P6 composite checkpoint schema mismatch")
        expected = _fingerprint({
            "hierarchy": state["hierarchy"],
            "p6": state["p6"],
            "coupling_config": state["coupling_config"],
            "version": int(state["version"]),
        })
        if state.get("fingerprint") != expected:
            raise ValueError("P6 composite checkpoint fingerprint mismatch")
        config = state.get("coupling_config", {})
        if (float(config.get("readout_gain", -1.0)) != self.readout_gain
                or float(config.get("control_gain", -1.0)) != self.control_gain
                or config.get("observation_transform") != self.observation_transform):
            raise ValueError("P6 coupling gain configuration mismatch")
        # Fully validate the controller candidate before native state changes.
        candidate_model = _p6_from_snapshot(state["p6"])
        self.hierarchy_lifecycle.restore(state["hierarchy"])
        self.model = candidate_model
        self.version = int(state["version"])

    def promote(self) -> int:
        if self._trusted is None:
            raise RuntimeError("P6 promotion requires an initial trusted composite checkpoint")
        previous = copy.deepcopy(self._trusted)
        prior_version = self.version
        self.version += 1
        try:
            candidate = self._capture()
        except Exception:
            self.version = prior_version
            raise
        self._rollback_point = previous
        self._trusted = copy.deepcopy(candidate)
        return self.version

    def rollback(self) -> None:
        target = self._rollback_point
        if target is None:
            raise RuntimeError("no pre-promotion P6 composite checkpoint exists")
        self.restore(target)
        self._trusted = copy.deepcopy(target)
        self._rollback_point = None

    def exchange(
        self,
        *,
        event_time: float,
        observed_at: float,
        event_features: Mapping[int, Sequence[float]],
        residual_score: float = 0.0,
        relation_records=(),
    ) -> dict:
        before = self._capture()
        control = None
        observation = None
        result = None
        try:
            supplied = {
                int(level): np.asarray(values, dtype=np.float64).reshape(-1).copy()
                for level, values in event_features.items()
            }
            if 0 not in supplied:
                raise ValueError("P6-coupled exchange requires a level-0 grounding feature")
            adapter = self.director.adapter
            mode_gain = (
                0.0 if self.model.mode == AdaptiveMode.DORMANT
                else 0.5 if self.model.mode == AdaptiveMode.RECOVERY
                else 1.0
            )
            control = (
                self.control_gain * mode_gain
                * (self.model.revision.accepted_operator @ self.model.state)
            )
            for level in (1, 2):
                readout = adapter.readouts[level - 1]
                relation_key = "lower" if level == 1 else "upper"
                relation_gate = float(
                    self.model.activation.is_active(relation_key)
                    and self.model.last_context_slot is not None
                )
                if readout.fitted and relation_gate > 0.0 and mode_gain > 0.0:
                    base = self.readout_gain * relation_gate * mode_gain * readout.predict(
                        adapter.bridge.memories[level - 1].snapshot().reshape(-1)
                    )
                else:
                    base = np.zeros(
                        adapter.bridge.memories[level].feature_dim, dtype=np.float64
                    )
                if level in supplied:
                    if supplied[level].shape != base.shape:
                        raise ValueError(f"level-{level} feature dimension mismatch")
                    supplied[level] = supplied[level] + base
                else:
                    supplied[level] = base

            control_feature = np.zeros(adapter.bridge.memories[2].feature_dim, dtype=np.float64)
            if control_feature.size < 2:
                raise ValueError("P6 context level requires at least two feature coordinates")
            control_feature[:2] = control
            supplied[2] = supplied[2] + control_feature

            result = self.director.exchange(
                event_time=event_time, observed_at=observed_at,
                event_features=supplied, relation_records=relation_records,
            )
            native_views = result["result"]["native_u_views"]
            raw_observation = np.asarray([
                float(np.mean(native_views[1])),
                float(np.mean(native_views[2])),
            ], dtype=np.float64)
            observation = (
                np.tanh(raw_observation)
                if self.observation_transform == "tanh"
                else raw_observation.copy()
            )
            grounding = supplied[0]
            if grounding.size >= 6:
                sources = {"lower": grounding[:2], "upper": grounding[2:4]}
                context_features = grounding[4:6]
            else:
                sources = {"lower": grounding[:2], "upper": grounding[:2]}
                context_features = np.zeros(2, dtype=np.float64)
            adaptive_state = self.model.observe_adaptive_state(
                sources, context_features, raw_observation
            )
            p6_state = self.model.step(observation, residual_score=float(residual_score))
            return {
                "hierarchy": result,
                "adaptive_state": adaptive_state,
                "p6_observation_raw": raw_observation.tolist(),
                "p6_observation": observation.tolist(),
                "p6_control": control.tolist(),
                "p6_mode_gain": float(mode_gain),
                "p6_state": p6_state.tolist(),
                "p6_state_norm": float(np.linalg.norm(p6_state)),
                "p6_mode": self.model.mode.value,
            }
        except Exception as exc:
            # Capture the failed post-native/pre-rollback state so an actual
            # coupled blow-up can be attributed to native feedback or P6.
            p6_state = np.asarray(self.model.state, dtype=np.float64)
            p6_norm = float(np.linalg.norm(p6_state))
            native_norms = []
            if result is not None:
                try:
                    native_levels = result["result"]["native"]["level_states"]
                    native_norms = [
                        {
                            "u_norm": float(np.linalg.norm(np.asarray(level["u"], dtype=np.float64))),
                            "chi_norm": float(np.linalg.norm(np.asarray(level["chi"], dtype=np.float64))),
                            "u_max_abs": float(np.max(np.abs(np.asarray(level["u"], dtype=np.float64)))),
                        }
                        for level in native_levels
                    ]
                except (KeyError, TypeError, ValueError):
                    native_norms = []
            diagnostic = (
                f"event_time={event_time}; p6_state_norm={p6_norm}; "
                f"p6_state={p6_state.tolist()}; control={None if control is None else np.asarray(control).tolist()}; "
                f"observation={None if observation is None else np.asarray(observation).tolist()}; "
                f"raw_observation={None if 'raw_observation' not in locals() else np.asarray(raw_observation).tolist()}; "
                f"native_level_norms={native_norms}; p6_step_count={self.model.step_count}"
            )
            self.restore(before)
            if isinstance(exc, (FloatingPointError, ValueError)):
                raise type(exc)(f"{exc}; coupled-runtime diagnostics: {diagnostic}") from exc
            raise

    def start_candidate(self, operator: Sequence[Sequence[float]]) -> None:
        if self._trusted is None:
            raise RuntimeError("P6 candidate fitting requires a trusted composite checkpoint")
        self.model.start_candidate(operator)

    def validate_candidate(self, *, incumbent_loss: float, candidate_loss: float,
                            identifiable: bool) -> bool:
        if self._trusted is None:
            raise RuntimeError("P6 candidate validation requires a trusted composite checkpoint")
        before = self._capture()
        try:
            promoted = self.model.validate_candidate(
                incumbent_loss=incumbent_loss,
                candidate_loss=candidate_loss,
                identifiable=identifiable,
            )
            if promoted:
                if self.model.last_context_slot is not None:
                    self.model.context_bank.set_operator(
                        int(self.model.last_context_slot), "lower",
                        self.model.revision.accepted_operator,
                    )
                self.promote()
            return promoted
        except Exception:
            self.restore(before)
            raise

    def update_relation_evidence(self, relation_id: str, predictive_improvement: float | None,
                                 *, observed: bool, identifiable: bool,
                                 context_score: float, context_slot: int | None = None):
        return self.model.update_relation_evidence(
            relation_id, predictive_improvement, observed=observed,
            identifiable=identifiable, context_score=context_score,
            context_slot=context_slot,
        )

    def close(self) -> None:
        self.director.close()
