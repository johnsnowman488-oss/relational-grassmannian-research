"""Grassmannian point represented by an orthonormal frame."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from numpy.typing import ArrayLike, NDArray
from .projection import orthonormalize
FloatArray = NDArray[np.float64]

@dataclass(frozen=True)
class GrassmannianPoint:
    """A point in Gr(k, R^n), represented by Q with Q.T @ Q = I."""
    frame: FloatArray

    def __init__(self, frame: ArrayLike) -> None:
        basis = orthonormalize(frame)
        basis.setflags(write=False)
        object.__setattr__(self, "frame", basis)

    @classmethod
    def random(cls, ambient_dim: int = 16, rank: int = 4, seed: int = 0) -> "GrassmannianPoint":
        if ambient_dim <= 0 or rank <= 0 or rank > ambient_dim:
            raise ValueError("require ambient_dim >= rank > 0")
        rng = np.random.default_rng(seed)
        return cls(rng.normal(size=(ambient_dim, rank)))

    @property
    def ambient_dim(self) -> int:
        return int(self.frame.shape[0])

    @property
    def rank(self) -> int:
        return int(self.frame.shape[1])

    @property
    def projector(self) -> FloatArray:
        return self.frame @ self.frame.T
