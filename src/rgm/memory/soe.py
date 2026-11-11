"""Deterministic fixed sum-of-exponentials memory bank."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

DEFAULT_DECAY_RATES = (0.01, 0.05, 0.2, 0.8)
FloatArray = NDArray[np.float64]


def _as_finite_array(value: ArrayLike, *, name: str) -> FloatArray:
    array = np.asarray(value, dtype=np.float64)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


@dataclass
class SOEMemory:
    """A bank of fixed exponential traces.

    Each channel is updated as
    exp(-decay_rates[l] * dt) * channels[l] + injection[l] @ feature.
    """

    decay_rates: FloatArray
    channels: FloatArray
    injection_matrices: FloatArray

    def __init__(
        self,
        feature_dim: int = 16,
        decay_rates: ArrayLike = DEFAULT_DECAY_RATES,
        injection_matrices: ArrayLike | None = None,
        initial_state: ArrayLike | None = None,
    ) -> None:
        rates = _as_finite_array(decay_rates, name="decay_rates").reshape(-1)
        if feature_dim <= 0:
            raise ValueError("feature_dim must be positive")
        if rates.size == 0 or np.any(rates <= 0.0):
            raise ValueError("decay_rates must be a non-empty sequence of positive values")
        count = rates.size
        if injection_matrices is None:
            injections = np.repeat(np.eye(feature_dim)[None, :, :], count, axis=0)
        else:
            injections = _as_finite_array(injection_matrices, name="injection_matrices")
            if injections.shape != (count, feature_dim, feature_dim):
                raise ValueError(
                    "injection_matrices must have shape "
                    f"({count}, {feature_dim}, {feature_dim})"
                )
        if initial_state is None:
            state = np.zeros((count, feature_dim), dtype=np.float64)
        else:
            state = _as_finite_array(initial_state, name="initial_state")
            if state.shape != (count, feature_dim):
                raise ValueError(f"initial_state must have shape ({count}, {feature_dim})")
        self.decay_rates = rates.copy()
        self.channels = state.copy()
        self.injection_matrices = injections.copy()

    @property
    def feature_dim(self) -> int:
        return int(self.channels.shape[1])

    @property
    def channel_count(self) -> int:
        return int(self.channels.shape[0])

    def update(self, event_feature: ArrayLike, dt: float = 1.0) -> FloatArray:
        """Advance all traces by elapsed time and inject one feature vector."""
        if not np.isfinite(dt) or dt < 0.0:
            raise ValueError("dt must be finite and non-negative")
        feature = _as_finite_array(event_feature, name="event_feature").reshape(-1)
        if feature.shape != (self.feature_dim,):
            raise ValueError(f"event_feature must have shape ({self.feature_dim},)")
        decay = np.exp(-self.decay_rates * float(dt))[:, None]
        injected = np.einsum("lij,j->li", self.injection_matrices, feature)
        self.channels = decay * self.channels + injected
        return self.snapshot()

    def advance(self, dt: float) -> FloatArray:
        """Decay the memory without injecting a new event."""
        if not np.isfinite(dt) or dt < 0.0:
            raise ValueError("dt must be finite and non-negative")
        self.channels *= np.exp(-self.decay_rates * float(dt))[:, None]
        return self.snapshot()

    def reset(self) -> None:
        """Reset all channels to zero without changing the fixed configuration."""
        self.channels.fill(0.0)

    def snapshot(self) -> FloatArray:
        """Return a defensive copy of the current channel states."""
        return self.channels.copy()

    def copy(self) -> "SOEMemory":
        return SOEMemory(
            feature_dim=self.feature_dim,
            decay_rates=self.decay_rates,
            injection_matrices=self.injection_matrices,
            initial_state=self.channels,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable configuration and state."""
        return {
            "feature_dim": self.feature_dim,
            "decay_rates": self.decay_rates.tolist(),
            "injection_matrices": self.injection_matrices.tolist(),
            "channels": self.channels.tolist(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SOEMemory":
        """Reconstruct a bank from serialized configuration and state."""
        required = {"feature_dim", "decay_rates", "injection_matrices", "channels"}
        missing = required.difference(payload)
        if missing:
            raise ValueError(f"missing SOE memory fields: {sorted(missing)}")
        return cls(
            feature_dim=int(payload["feature_dim"]),
            decay_rates=payload["decay_rates"],
            injection_matrices=payload["injection_matrices"],
            initial_state=payload["channels"],
        )
