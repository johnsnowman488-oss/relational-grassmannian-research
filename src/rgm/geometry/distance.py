"""Principal angles and canonical Grassmannian distance."""
from __future__ import annotations
import numpy as np
from numpy.typing import ArrayLike, NDArray
from .projection import orthonormalize
FloatArray = NDArray[np.float64]

def principal_angles(first: ArrayLike, second: ArrayLike) -> FloatArray:
    """Return principal angles in radians for two subspaces of equal rank."""
    q1 = orthonormalize(first)
    q2 = orthonormalize(second)
    if q1.shape != q2.shape:
        raise ValueError("subspaces must have the same ambient dimension and rank")
    singular_values = np.linalg.svd(q1.T @ q2, compute_uv=False)
    singular_values = np.clip(singular_values, 0.0, 1.0)
    return np.arccos(singular_values)

def canonical_distance(first: ArrayLike, second: ArrayLike) -> float:
    """Canonical geodesic distance: sqrt(sum of squared principal angles)."""
    return float(np.linalg.norm(principal_angles(first, second)))
