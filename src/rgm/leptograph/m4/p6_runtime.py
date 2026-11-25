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
from rgm.leptograph.m3.revision import CUSUMDetector, CandidateRevision
from rgm.leptograph.m4.hierarchical import (
    CompositeLifecycle, HierarchicalRuntimeDirector,
)
from rgm.leptograph.m4.stability import AdaptiveMode, CoupledAdaptiveSystem


def _fingerprint(payload: Mapping) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


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
    model = CoupledAdaptiveSystem(
        transition=np.asarray(state["transition"], dtype=np.float64),
        input_matrix=np.asarray(state["input_matrix"], dtype=np.float64),
        max_state_norm=float(state["max_state_norm"]),
        state=np.asarray(state["state"], dtype=np.float64),
        memory=SOEMemory.from_dict(dict(state["memory"])),
        detector=detector,
        activation=activation,
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
    schema_version = "P6-H1-0.1.0"

    def __init__(
        self,
        director: HierarchicalRuntimeDirector,
        *,
        model: CoupledAdaptiveSystem | None = None,
        hierarchy_lifecycle: CompositeLifecycle | None = None,
    ):
        self.director = director
        self.hierarchy_lifecycle = hierarchy_lifecycle or CompositeLifecycle(director)
        self.model = model or CoupledAdaptiveSystem()
        self.version = 0
        self._trusted: dict | None = None
        self._rollback_point: dict | None = None

    def _capture(self) -> dict:
        hierarchy = self.hierarchy_lifecycle._capture_checkpoint()
        state = {
            "schema_version": self.schema_version,
            "hierarchy": hierarchy,
            "p6": _p6_snapshot(self.model),
            "version": self.version,
        }
        state["fingerprint"] = _fingerprint({
            "hierarchy": state["hierarchy"],
            "p6": state["p6"],
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
            "version": int(state["version"]),
        })
        if state.get("fingerprint") != expected:
            raise ValueError("P6 composite checkpoint fingerprint mismatch")
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
            control = self.model.revision.accepted_operator @ self.model.state
            control_feature = np.zeros(adapter.bridge.memories[2].feature_dim, dtype=np.float64)
            if control_feature.size < 2:
                raise ValueError("P6 context level requires at least two feature coordinates")
            control_feature[:2] = control
            if 2 in supplied:
                if supplied[2].shape != control_feature.shape:
                    raise ValueError("level-2 feature dimension mismatch")
                supplied[2] = supplied[2] + control_feature
            else:
                readout = adapter.readouts[1]
                if readout.fitted:
                    base = readout.predict(
                        adapter.bridge.memories[1].snapshot().reshape(-1)
                    )
                else:
                    base = np.zeros_like(control_feature)
                supplied[2] = base + control_feature

            result = self.director.exchange(
                event_time=event_time, observed_at=observed_at,
                event_features=supplied, relation_records=relation_records,
            )
            native_views = result["result"]["native_u_views"]
            observation = np.asarray([
                float(np.mean(native_views[1])),
                float(np.mean(native_views[2])),
            ], dtype=np.float64)
            p6_state = self.model.step(observation, residual_score=float(residual_score))
            return {
                "hierarchy": result,
                "p6_observation": observation.tolist(),
                "p6_control": control.tolist(),
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
