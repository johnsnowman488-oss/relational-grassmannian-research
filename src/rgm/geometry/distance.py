"""Principal angles and canonical Grassmannian distance."""
from __future__ import annotations
import numpy as np
from numpy.typing import ArrayLike, NDArray
from .projection import orthonormalize
FloatArray = NDArray[np.float64]

def principal_angles(first: ArrayLike, second: ArrayLike, *, unit_tolerance: float = 1e-12) -> FloatArray:
    """Return principal angles in radians for two subspaces of equal rank.

    Singular values within unit_tolerance of one are snapped to one. This
    removes tiny positive angles introduced when numerically re-orthogonalizing
    the same subspace, without changing resolvable geometric differences.
    """
    if not np.isfinite(unit_tolerance) or unit_tolerance < 0.0:
        raise ValueError("unit_tolerance must be finite and non-negative")
    q1 = orthonormalize(first)
    q2 = orthonormalize(second)
    if q1.shape != q2.shape:
        raise ValueError("subspaces must have the same ambient dimension and rank")
    singular_values = np.linalg.svd(q1.T @ q2, compute_uv=False)
    singular_values = np.clip(singular_values, 0.0, 1.0)
    singular_values = np.where(singular_values >= 1.0 - unit_tolerance, 1.0, singular_values)
    return np.arccos(singular_values)

def canonical_distance(first: ArrayLike, second: ArrayLike) -> float:
    """Canonical geodesic distance: sqrt(sum of squared principal angles)."""
    return float(np.linalg.norm(principal_angles(first, second)))
