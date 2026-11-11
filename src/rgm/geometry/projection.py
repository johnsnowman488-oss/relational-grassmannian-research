"""Orthonormal frames and projection matrices."""
from __future__ import annotations
import numpy as np
from numpy.typing import ArrayLike, NDArray
FloatArray = NDArray[np.float64]

def orthonormalize(frame: ArrayLike, *, tolerance: float = 1e-12) -> FloatArray:
    """Return an orthonormal basis for the supplied full-column-rank matrix."""
    matrix = np.asarray(frame, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] < matrix.shape[1] or matrix.shape[1] == 0:
        raise ValueError("frame must be a 2-D matrix with rows >= columns > 0")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("frame must contain only finite values")
    u, singular_values, _ = np.linalg.svd(matrix, full_matrices=False)
    if singular_values.size == 0 or singular_values[-1] <= tolerance * singular_values[0]:
        raise ValueError("frame must have full column rank")
    return u[:, : matrix.shape[1]].copy()

def projector_from_frame(frame: ArrayLike) -> FloatArray:
    """Construct the orthogonal projector associated with a full-rank frame."""
    q = orthonormalize(frame)
    projector = q @ q.T
    return 0.5 * (projector + projector.T)
