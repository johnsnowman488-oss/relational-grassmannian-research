"""Validated finite categorical transition distributions."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Hashable, Sequence
import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.special import softmax
FloatArray = NDArray[np.float64]

@dataclass(frozen=True)
class CategoricalDistribution:
    """A labelled finite probability distribution over next states."""
    labels: tuple[Hashable, ...]
    probabilities: FloatArray

    def __init__(self, labels: Sequence[Hashable], probabilities: ArrayLike) -> None:
        names = tuple(labels)
        values = np.asarray(probabilities, dtype=np.float64).reshape(-1)
        if not names or len(names) != values.size:
            raise ValueError("labels and probabilities must have the same non-zero length")
        if len(set(names)) != len(names):
            raise ValueError("labels must be unique")
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("probabilities must be finite and non-negative")
        total = float(values.sum())
        if not np.isclose(total, 1.0, atol=1e-10, rtol=0.0):
            raise ValueError("probabilities must sum to one")
        values = values / total
        values.setflags(write=False)
        object.__setattr__(self, "labels", names)
        object.__setattr__(self, "probabilities", values)

    @classmethod
    def from_scores(
        cls, labels: Sequence[Hashable], scores: ArrayLike, *, temperature: float = 1.0,
    ) -> "CategoricalDistribution":
        values = np.asarray(scores, dtype=np.float64).reshape(-1)
        if not np.isfinite(temperature) or temperature <= 0.0:
            raise ValueError("temperature must be finite and positive")
        if not np.all(np.isfinite(values)):
            raise ValueError("scores must contain only finite values")
        if len(labels) != values.size or values.size == 0:
            raise ValueError("labels and scores must have the same non-zero length")
        return cls(labels, softmax(values / temperature))

    def as_dict(self) -> dict[Hashable, float]:
        return dict(zip(self.labels, self.probabilities.tolist(), strict=True))

    def most_likely(self) -> Hashable:
        return self.labels[int(np.argmax(self.probabilities))]
