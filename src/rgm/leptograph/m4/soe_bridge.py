"""H0 bridge between Leptograph SOE banks and the persistent native hierarchy.

SOE traces are embedded losslessly into native u by row-major flattening.
Native evolution is a different dynamical system; reshaping later native u
does not reconstruct or update the Python SOE bank.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite
from typing import Mapping, Protocol, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from rgm.memory import SOEMemory

FloatArray = NDArray[np.float64]
H0_CONTRACT_VERSION = "0.1.0"
H0_LEVEL_ROLES = ("grounding", "relational_abstraction", "context_control")


class PersistentRuntime(Protocol):
    def step(self, feedback_by_level: dict[int, Sequence[float]] | None = None) -> dict: ...
    def get_state(self) -> dict: ...


@dataclass(frozen=True)
class SOEStateLayout:
    channel_count: int
    feature_dim: int

    def __post_init__(self) -> None:
        if self.channel_count < 1 or self.feature_dim < 1:
            raise ValueError("SOE layout dimensions must be positive")

    @property
    def native_state_dim(self) -> int:
        return self.channel_count * self.feature_dim

    def encode(self, channels: ArrayLike) -> FloatArray:
        matrix = np.asarray(channels, dtype=np.float64)
        expected = (self.channel_count, self.feature_dim)
        if matrix.shape != expected or not np.all(np.isfinite(matrix)):
            raise ValueError(f"SOE channels must be finite with shape {expected}")
        return np.ascontiguousarray(matrix).reshape(-1).copy()

    def decode(self, native_u: ArrayLike) -> FloatArray:
        vector = np.asarray(native_u, dtype=np.float64).reshape(-1)
        if vector.shape != (self.native_state_dim,) or not np.all(np.isfinite(vector)):
            raise ValueError(f"native u must be finite with length {self.native_state_dim}")
        return vector.reshape(self.channel_count, self.feature_dim).copy()


def make_native_level_spec(
    memory: SOEMemory, *, name: str, gamma: Sequence[float],
    weights: Sequence[float], dt: float,
    linear_decay: Sequence[float] | None = None,
    forcing_bias: Sequence[float] | None = None,
    form: int = 1, coupling_index: int = 0,
) -> dict:
    """Build a native level whose u vector embeds the current SOE state."""
    layout = SOEStateLayout(memory.channel_count, memory.feature_dim)
    gamma_values = np.asarray(gamma, dtype=np.float64).reshape(-1)
    weight_values = np.asarray(weights, dtype=np.float64).reshape(-1)
    if gamma_values.shape != (memory.channel_count,) or weight_values.shape != (memory.channel_count,):
        raise ValueError("native gamma and weights must match SOE channel count")
    if not np.all(np.isfinite(gamma_values)) or np.any(gamma_values <= 0):
        raise ValueError("native gamma must be finite and positive")
    if np.any(gamma_values[:-1] < gamma_values[1:]):
        raise ValueError("native gamma must be sorted in descending order")
    if not np.all(np.isfinite(weight_values)) or np.any(weight_values < 0) or weight_values.sum() <= 0:
        raise ValueError("native weights must be finite, non-negative and have positive sum")
    if not isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and positive")
    dim = layout.native_state_dim
    decay = np.ones(dim) if linear_decay is None else np.asarray(linear_decay, dtype=np.float64).reshape(-1)
    bias = np.zeros(dim) if forcing_bias is None else np.asarray(forcing_bias, dtype=np.float64).reshape(-1)
    if decay.shape != (dim,) or bias.shape != (dim,):
        raise ValueError(f"linear_decay and forcing_bias must each have length {dim}")
    if not np.all(np.isfinite(decay)) or not np.all(np.isfinite(bias)):
        raise ValueError("linear_decay and forcing_bias must be finite")
    if not isinstance(name, str) or not name:
        raise ValueError("level name must be non-empty")
    if isinstance(coupling_index, bool) or not isinstance(coupling_index, int) or coupling_index < 0:
        raise ValueError("coupling_index must be a non-negative integer")
    return {
        "name": name, "gamma": gamma_values.tolist(), "w": weight_values.tolist(),
        "u": layout.encode(memory.snapshot()).tolist(),
        "chi": [0.0] * memory.channel_count, "t": 0.0, "dt": float(dt),
        "linear_decay": decay.tolist(), "forcing_bias": bias.tolist(),
        "form": int(form), "coupling_index": coupling_index,
    }


class SOEHierarchyBridge:
    """Synchronise three SOE banks with one persistent native step per tick."""

    def __init__(self, runtime: PersistentRuntime, memories: Sequence[SOEMemory], *, dt: float):
        if len(memories) != 3:
            raise ValueError("H0 requires exactly three SOE memory banks")
        if not isfinite(dt) or dt <= 0:
            raise ValueError("dt must be finite and positive")
        self.runtime = runtime
        self.memories = tuple(memories)
        self.layouts = tuple(SOEStateLayout(m.channel_count, m.feature_dim) for m in self.memories)
        self.dt = float(dt)
        initial_snapshot = runtime.get_state()
        self._validate_native_state(initial_snapshot)
        for index, (state, memory, layout) in enumerate(zip(
            initial_snapshot["level_states"], self.memories, self.layouts
        )):
            if not np.array_equal(
                np.asarray(state["u"], dtype=np.float64),
                layout.encode(memory.snapshot()),
            ):
                raise ValueError(
                    f"native level {index} must be initialised from its matching SOE snapshot"
                )

    def _validate_native_state(self, snapshot: dict) -> None:
        try:
            states = snapshot["level_states"]
        except (KeyError, TypeError) as exc:
            raise ValueError("runtime snapshot must contain level_states") from exc
        if len(states) != 3:
            raise ValueError("native runtime must have exactly three levels")
        for i, (state, layout) in enumerate(zip(states, self.layouts)):
            u = np.asarray(state["u"], dtype=np.float64).reshape(-1)
            if u.shape != (layout.native_state_dim,) or not np.all(np.isfinite(u)):
                raise ValueError(f"native level {i} u dimension or values are invalid")

    def step(self, event_features: Mapping[int, ArrayLike] | None = None, *, dt: float | None = None) -> dict:
        tick = self.dt if dt is None else float(dt)
        if not isfinite(tick) or not isclose(tick, self.dt, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("H0 v0.1 requires every cycle to use the configured fixed dt")
        features = {} if event_features is None else dict(event_features)
        # Validate the whole batch before changing any SOE bank.
        for index, feature in features.items():
            if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 3:
                raise ValueError(f"invalid H0 level index: {index!r}")
            vector = np.asarray(feature, dtype=np.float64).reshape(-1)
            if vector.shape != (self.memories[index].feature_dim,) or not np.all(np.isfinite(vector)):
                raise ValueError(f"event feature for level {index} has invalid dimension or values")

        # Work on copies so a native-step failure cannot leave Python SOE
        # state advanced while the persistent C++ hierarchy remains unchanged.
        candidates = [memory.copy() for memory in self.memories]
        for index, memory in enumerate(candidates):
            if index in features:
                memory.update(features[index], dt=tick)
            else:
                memory.advance(tick)
        feedback = {
            i: self.layouts[i].encode(memory.snapshot()).tolist()
            for i, memory in enumerate(candidates)
        }
        result = self.runtime.step(feedback)
        self._validate_native_state(result)
        for memory, candidate in zip(self.memories, candidates):
            memory.channels = candidate.channels.copy()
        return {
            "native": result,
            "native_u_views": [
                self.layouts[i].decode(level["u"])
                for i, level in enumerate(result["level_states"])
            ],
            "soe_feedback": {
                i: np.asarray(values).reshape(self.layouts[i].channel_count, self.layouts[i].feature_dim)
                for i, values in feedback.items()
            },
        }

    def silent_steps(self, count: int) -> list[dict]:
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("count must be a non-negative integer")
        return [self.step() for _ in range(count)]


H0_DEFAULT_EDGES = (
    {"source_level": 0, "target_level": 1, "relation": 0, "gain": 1.0, "normalize_weights": True},
    {"source_level": 1, "target_level": 2, "relation": 0, "gain": 1.0, "normalize_weights": True},
    {"source_level": 2, "target_level": 1, "relation": 1, "gain": 1.0, "normalize_weights": True},
    {"source_level": 1, "target_level": 0, "relation": 1, "gain": 1.0, "normalize_weights": True},
)


def make_h0_chain_spec(
    memories: Sequence[SOEMemory],
    kernels: Sequence[Mapping[str, object]],
    *,
    dt: float,
) -> tuple[list[dict], list[dict]]:
    """Build the matched three-level native chain specification.

    Native relation values follow the M4 ABI: 0 is bottom-up and 1 is
    top-down. Each kernel mapping must provide gamma and w; optional
    linear_decay, forcing_bias, form and coupling_index are forwarded.
    """
    if len(memories) != 3 or len(kernels) != 3:
        raise ValueError("H0 requires exactly three memories and three kernel specifications")
    if not isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and positive")
    levels = []
    for index, (memory, kernel) in enumerate(zip(memories, kernels)):
        if "gamma" not in kernel or "w" not in kernel:
            raise ValueError(f"kernel specification {index} must provide gamma and w")
        levels.append(make_native_level_spec(
            memory,
            name=H0_LEVEL_ROLES[index],
            gamma=kernel["gamma"],
            weights=kernel["w"],
            dt=dt,
            linear_decay=kernel.get("linear_decay"),
            forcing_bias=kernel.get("forcing_bias"),
            form=int(kernel.get("form", 1)),
            coupling_index=int(kernel.get("coupling_index", 0)),
        ))
    return levels, [dict(edge) for edge in H0_DEFAULT_EDGES]
