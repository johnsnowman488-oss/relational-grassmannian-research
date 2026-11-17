"""Joint heterogeneous online ridge estimator with effective route gates."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, Sequence
import numpy as np


@dataclass
class MultiSourceRidge:
    """All-source shadow estimator with separately gated effective predictions."""
    source_dimensions: Mapping[str, int]
    context_dimension: int
    target_dimension: int
    ridge: float = 1e-5
    forgetting: float = 1.0
    _gram_upper: np.ndarray = field(init=False, repr=False)
    cross: np.ndarray = field(init=False)
    sample_count: int = 0
    prediction_count: int = 0
    update_count: int = 0
    _source_slices: dict[str, slice] = field(init=False, default_factory=dict)
    _context_slice: slice = field(init=False)
    _intercept_index: int = field(init=False)

    def __post_init__(self) -> None:
        self.source_dimensions = dict(self.source_dimensions)
        if not self.source_dimensions or any(not k or int(v) < 1 for k, v in self.source_dimensions.items()):
            raise ValueError("at least one source with positive dimension is required")
        if self.context_dimension < 0 or self.target_dimension < 1 or self.ridge <= 0:
            raise ValueError("invalid context/target dimensions or ridge")
        if not (0 < self.forgetting <= 1):
            raise ValueError("forgetting must be in (0, 1]")
        offset = 0
        for key in sorted(self.source_dimensions):
            width = int(self.source_dimensions[key])
            self._source_slices[key] = slice(offset, offset + width)
            offset += width
        self._context_slice = slice(offset, offset + self.context_dimension)
        offset += self.context_dimension
        self._intercept_index = offset
        upper_rows, upper_cols = np.triu_indices(offset + 1)
        self._gram_upper = np.zeros(upper_rows.size, dtype=float)
        self.cross = np.zeros((offset + 1, self.target_dimension), dtype=float)

    @property
    def feature_dimension(self) -> int:
        return int(self.cross.shape[0])

    @property
    def gram(self) -> np.ndarray:
        """Materialise the symmetric Gram matrix from packed upper-triangle state."""
        matrix = np.zeros((self.feature_dimension, self.feature_dimension), dtype=float)
        upper_rows, upper_cols = np.triu_indices(self.feature_dimension)
        matrix[upper_rows, upper_cols] = self._gram_upper
        matrix[upper_cols, upper_rows] = self._gram_upper
        return matrix

    def _features(self, sources, context, source_gates=None) -> np.ndarray:
        if set(sources) != set(self.source_dimensions):
            raise ValueError("every declared source must be supplied exactly once")
        gates = dict(source_gates or {})
        if set(gates) - set(self.source_dimensions):
            raise ValueError("gate supplied for an undeclared source")
        chunks = []
        for key in sorted(self.source_dimensions):
            x = np.asarray(sources[key], dtype=float)
            if x.shape != (self.source_dimensions[key],) or not np.all(np.isfinite(x)):
                raise ValueError(f"invalid source vector for {key}")
            gate = float(gates.get(key, 1.0))
            if not np.isfinite(gate) or not 0.0 <= gate <= 1.0:
                raise ValueError(f"invalid source gate for {key}")
            chunks.append(gate * x)
        c = np.asarray(context, dtype=float)
        if c.shape != (self.context_dimension,) or not np.all(np.isfinite(c)):
            raise ValueError("invalid context feature vector")
        chunks.extend([c, np.ones(1)])
        return np.concatenate(chunks)

    def coefficients(self) -> np.ndarray:
        return np.linalg.solve(self.gram + self.ridge * np.eye(self.feature_dimension), self.cross)

    def source_operator(self, source_id: str) -> np.ndarray:
        if source_id not in self._source_slices:
            raise KeyError(source_id)
        return self.coefficients()[self._source_slices[source_id], :].T.copy()

    def predict(self, sources, context, *, source_gates=None, operator_overrides=None) -> np.ndarray:
        phi = self._features(sources, context, source_gates)
        beta = self.coefficients()
        overrides = dict(operator_overrides or {})
        if set(overrides) - set(self.source_dimensions):
            raise ValueError("operator override for undeclared source")
        if overrides:
            beta = beta.copy()
            for key, value in overrides.items():
                operator = np.asarray(value, dtype=float)
                if operator.shape != (self.target_dimension, self.source_dimensions[key]) or not np.all(np.isfinite(operator)):
                    raise ValueError(f"invalid operator override for {key}")
                beta[self._source_slices[key], :] = operator.T
        self.prediction_count += 1
        return phi @ beta

    def update(self, sources, context, target, *, source_gates=None) -> None:
        """Update from current observed inputs, with explicit per-source gates.

        Callers represent a missing source with a zero placeholder and a zero
        gate. This preserves the declared source layout without treating
        absence as a measured zero-valued relationship contribution.
        """
        phi = self._features(sources, context, source_gates)
        y = np.asarray(target, dtype=float)
        if y.shape != (self.target_dimension,) or not np.all(np.isfinite(y)):
            raise ValueError("invalid target vector")
        self._gram_upper *= self.forgetting
        self.cross *= self.forgetting
        upper_rows, upper_cols = np.triu_indices(self.feature_dimension)
        self._gram_upper += np.outer(phi, phi)[upper_rows, upper_cols]
        self.cross += np.outer(phi, y)
        self.sample_count += 1
        self.update_count += 1

    def marginal_loss_contributions(self, sources, context, target, *, source_gates=None) -> dict[str, float]:
        phi = self._features(sources, context, source_gates)
        y = np.asarray(target, dtype=float)
        if y.shape != (self.target_dimension,) or not np.all(np.isfinite(y)):
            raise ValueError("invalid target vector")
        beta = self.coefficients()
        full_loss = float(np.sum((y - phi @ beta) ** 2))
        out = {}
        for key, slc in self._source_slices.items():
            ablated = phi.copy()
            ablated[slc] = 0.0
            out[key] = float(np.sum((y - ablated @ beta) ** 2) - full_loss)
        return out

    def conditional_identifiability(self, *, tolerance: float = 1e-8, maximum_condition: float = 1e8):
        """Unregularised Schur-complement rank; ridge cannot manufacture identifiability."""
        if tolerance <= 0 or maximum_condition <= 1:
            raise ValueError("invalid identifiability tolerance")
        result = {}
        all_indices = np.arange(self.feature_dimension)
        for key, slc in self._source_slices.items():
            selected = np.arange(slc.start, slc.stop)
            other = np.setdiff1d(all_indices, selected, assume_unique=True)
            gss = self.gram[np.ix_(selected, selected)]
            if other.size:
                gcc = self.gram[np.ix_(other, other)]
                gcs = self.gram[np.ix_(other, selected)]
                projection, *_ = np.linalg.lstsq(gcc, gcs, rcond=tolerance)
                schur = gss - self.gram[np.ix_(selected, other)] @ projection
            else:
                schur = gss.copy()
            eigenvalues = np.linalg.eigvalsh(0.5 * (schur + schur.T))
            scale = max(float(np.max(np.abs(eigenvalues))), 1.0)
            positive = eigenvalues[eigenvalues > tolerance * scale]
            rank, dimension = int(positive.size), int(selected.size)
            condition = float(np.max(positive) / np.min(positive)) if rank == dimension and rank else None
            result[key] = {
                "rank": rank, "dimension": dimension, "condition_number": condition,
                "identifiable": bool(rank == dimension and condition is not None and condition <= maximum_condition),
            }
        return result

    def source_coefficient_norms(self) -> dict[str, float]:
        """Return coefficient-block norms keyed by source ID (v0.1 API compatibility)."""
        beta = self.coefficients()
        return {
            key: float(np.linalg.norm(beta[slc, :]))
            for key, slc in self._source_slices.items()
        }

    def resource_snapshot(self) -> dict[str, int | float]:
        return {
            "sufficient_statistic_bytes": int(self._gram_upper.nbytes + self.cross.nbytes),
            "packed_gram_bytes": int(self._gram_upper.nbytes),
            "equivalent_dense_gram_bytes": int(self.feature_dimension**2 * 8),
            "parameter_count": int(self.feature_dimension * self.target_dimension),
            "update_outer_product_multiply_adds": int(self.feature_dimension**2 + self.feature_dimension * self.target_dimension),
            "query_multiply_adds": int(self.feature_dimension * self.target_dimension),
            "sample_count": self.sample_count,
        }
