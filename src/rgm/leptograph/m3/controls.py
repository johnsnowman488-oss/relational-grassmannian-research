"""Explicit C0-C4 persistent-memory controls with resource instrumentation."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np

@dataclass
class MemoryArchitecture:
    """Small reference controls; no architecture is selected as the winner.

    C0: no persistent state; C1: mode-only; C2: relation-only;
    C3: independent mode and relation stores; C4: one shared latent state
    with two learned readouts and one shared write path.
    """
    name: str
    mode_dimension: int
    relation_dimension: int
    state_budget: int = 64
    precision: str = "float64"
    target_dimension: int = 2
    mode_state: np.ndarray = field(init=False)
    relation_state: np.ndarray = field(init=False)
    shared_state: np.ndarray = field(init=False)
    mode_readout: np.ndarray = field(init=False)
    relation_readout: np.ndarray = field(init=False)
    task_readout: np.ndarray = field(init=False)
    update_multiply_adds: int = 0
    query_multiply_adds: int = 0

    def __post_init__(self) -> None:
        if self.name not in {"C0", "C1", "C2", "C3", "C4"}:
            raise ValueError("architecture must be one of C0-C4")
        if self.mode_dimension < 1 or self.relation_dimension < 1 or self.state_budget < 1 or self.target_dimension < 1:
            raise ValueError("dimensions and state budget must be positive")
        if self.precision not in {"float32", "float64"}:
            raise ValueError("precision must be float32 or float64")
        dtype = np.float32 if self.precision == "float32" else np.float64
        zero = lambda n: np.zeros(n, dtype=dtype)
        self.mode_state, self.relation_state, self.shared_state = zero(0), zero(0), zero(0)
        self.mode_readout = np.zeros((self.mode_dimension, 0), dtype=dtype)
        self.relation_readout = np.zeros((self.relation_dimension, 0), dtype=dtype)
        if self.name == "C1":
            self.mode_state = zero(self.state_budget)
        elif self.name == "C2":
            self.relation_state = zero(self.state_budget)
        elif self.name == "C3":
            mode_n = self.state_budget // 2
            self.mode_state, self.relation_state = zero(mode_n), zero(self.state_budget - mode_n)
        elif self.name == "C4":
            self.shared_state = zero(self.state_budget)
            self.mode_readout = np.zeros((self.mode_dimension, self.state_budget), dtype=dtype)
            self.relation_readout = np.zeros((self.relation_dimension, self.state_budget), dtype=dtype)
        feature_width = (self.mode_state.size + self.relation_state.size
                         if self.name in {"C1", "C2", "C3"} else
                         self.mode_dimension + self.relation_dimension if self.name == "C4" else 0)
        self.task_readout = np.zeros((self.target_dimension, feature_width), dtype=dtype)

    @property
    def persistent_state_bytes(self) -> int:
        return int(self.mode_state.nbytes + self.relation_state.nbytes + self.shared_state.nbytes)

    @property
    def trainable_parameter_count(self) -> int:
        return int(self.mode_readout.size + self.relation_readout.size)

    @property
    def persistent_parameter_bytes(self) -> int:
        return int(self.mode_readout.nbytes + self.relation_readout.nbytes)

    @property
    def persistent_bytes(self) -> int:
        return self.persistent_state_bytes + self.persistent_parameter_bytes + int(self.task_readout.nbytes)

    def update_mode(self, signal: np.ndarray, rate: float = 0.1) -> None:
        x = np.asarray(signal, dtype=float).reshape(-1)
        if self.name in {"C1", "C3"} and x.size:
            n = min(x.size, self.mode_state.size)
            self.mode_state[:n] += rate * x[:n]
            self.update_multiply_adds += 2 * n
        elif self.name == "C4":
            self._shared_readout_update(x, self.mode_readout, rate)

    def update_relation(self, signal: np.ndarray, rate: float = 0.1) -> None:
        x = np.asarray(signal, dtype=float).reshape(-1)
        if self.name in {"C2", "C3"} and x.size:
            n = min(x.size, self.relation_state.size)
            self.relation_state[:n] += rate * x[:n]
            self.update_multiply_adds += 2 * n
        elif self.name == "C4":
            self._shared_readout_update(x, self.relation_readout, rate)

    def _shared_readout_update(self, signal: np.ndarray, readout: np.ndarray, rate: float) -> None:
        if not signal.size:
            return
        n = min(signal.size, readout.shape[0])
        # Both input types write into the same latent coordinates. Each readout
        # learns its own decoding from that common state after the shared write.
        self.shared_state[:] = (1.0 - rate) * self.shared_state
        self.shared_state[:min(signal.size, self.shared_state.size)] += (
            rate * signal[:min(signal.size, self.shared_state.size)]
        )
        readout[:n, :] += rate * np.outer(signal[:n], self.shared_state)
        width = readout.shape[1]
        self.update_multiply_adds += 3 * self.shared_state.size + 2 * n * width

    def read_mode(self) -> np.ndarray:
        if self.name in {"C1", "C3"}:
            return self.mode_state.copy()
        if self.name == "C4":
            self.query_multiply_adds += self.mode_readout.size
            return self.mode_readout @ self.shared_state
        return np.zeros(self.mode_dimension, dtype=self.shared_state.dtype)

    def read_relation(self) -> np.ndarray:
        if self.name in {"C2", "C3"}:
            return self.relation_state.copy()
        if self.name == "C4":
            self.query_multiply_adds += self.relation_readout.size
            return self.relation_readout @ self.shared_state
        return np.zeros(self.relation_dimension, dtype=self.shared_state.dtype)

    def _task_features(self) -> np.ndarray:
        """Return the architecture's currently retained predictive state."""
        if self.name == "C0":
            return np.zeros(0, dtype=self.shared_state.dtype)
        return np.concatenate((self.read_mode(), self.read_relation())).astype(
            self.shared_state.dtype, copy=False
        )

    def predict(self) -> np.ndarray:
        """Predict the common target from retained memory, before feedback."""
        features = self._task_features()
        self.query_multiply_adds += int(self.task_readout.size)
        if not features.size:
            return np.zeros(self.target_dimension, dtype=self.task_readout.dtype)
        return self.task_readout @ features

    def update_target(self, target: np.ndarray, rate: float = 0.1) -> None:
        """Update the common task readout after the target has been observed.

        The caller must call predict/score before this method to preserve
        prequential ordering. C0 intentionally remains a zero-state reference.
        """
        y = np.asarray(target, dtype=float).reshape(-1)
        if y.shape != (self.target_dimension,) or not np.all(np.isfinite(y)):
            raise ValueError("target has invalid shape or non-finite values")
        if not np.isfinite(rate) or not 0.0 < rate <= 1.0:
            raise ValueError("rate must be in (0, 1]")
        features = self._task_features()
        if not features.size:
            return
        prediction = self.task_readout @ features
        error = y - prediction
        scale = max(float(features @ features), 1.0)
        self.task_readout += (rate / scale) * np.outer(error, features)
        self.update_multiply_adds += int(2 * self.task_readout.size + features.size)

    def score_target(self, target: np.ndarray) -> float:
        """Return squared prediction loss without updating the architecture."""
        y = np.asarray(target, dtype=float).reshape(-1)
        if y.shape != (self.target_dimension,) or not np.all(np.isfinite(y)):
            raise ValueError("target has invalid shape or non-finite values")
        prediction = self.predict()
        return float(np.sum((y - prediction) ** 2))

    def resource_snapshot(self) -> dict[str, int | str]:
        return {
            "architecture": self.name, "precision": self.precision,
            "persistent_state_bytes": self.persistent_state_bytes,
            "trainable_parameter_count": self.trainable_parameter_count,
            "persistent_parameter_bytes": self.persistent_parameter_bytes,
            "task_readout_bytes": int(self.task_readout.nbytes),
            "task_readout_parameters": int(self.task_readout.size),
            "persistent_bytes_total": self.persistent_bytes,
            "update_multiply_adds_observed": self.update_multiply_adds,
            "query_multiply_adds_observed": self.query_multiply_adds,
        }
