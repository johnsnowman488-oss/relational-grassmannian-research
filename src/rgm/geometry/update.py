"""Candidate Grassmannian evolution under a skew-symmetric generator."""
from __future__ import annotations
import numpy as np
from numpy.typing import ArrayLike
from scipy.linalg import expm
from .grassmannian import GrassmannianPoint

def evolve_subspace(
    point: GrassmannianPoint, omega: ArrayLike, step_size: float = 1.0,
    *, skew_tolerance: float = 1e-10,
) -> GrassmannianPoint:
    """Apply Q_next = exp(step_size * Omega) Q for skew-symmetric Omega.

    This operation is mathematically valid, but does not define a coupling law.
    """
    generator = np.asarray(omega, dtype=np.float64)
    if generator.shape != (point.ambient_dim, point.ambient_dim):
        raise ValueError("omega must be square with dimension equal to the ambient space")
    if not np.all(np.isfinite(generator)) or not np.isfinite(step_size):
        raise ValueError("omega and step_size must be finite")
    if not np.allclose(generator.T, -generator, atol=skew_tolerance, rtol=0.0):
        raise ValueError("omega must be skew-symmetric")
    rotation = expm(float(step_size) * generator)
    return GrassmannianPoint(rotation @ point.frame)
