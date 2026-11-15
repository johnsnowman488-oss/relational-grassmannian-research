"""Online multi-source ridge estimation with prequential sequencing."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np


@dataclass
class MultiSourceRidge:
    """Joint linear predictor over every declared heterogeneous source.

    Sources are concatenated in the constructor's fixed key order, followed by
    context nuisance features and an intercept. Predictions are made from the
    current sufficient statistics; update() is a separate subsequent action.
    Counterfactual ablations are predictive diagnostics, not causal effects.
    """

    source_dimensions: Mapping[str, int]
    context_dimension: int
    target_dimension: int
    ridge: float = 1e-5
    forgetting: float = 1.0
    gram: np.ndarray = field(init=False)
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
        width = offset + 1
        self.gram = np.zeros((width, width), dtype=float)
        self.cross = np.zeros((width, self.target_dimension), dtype=float)

    @property
    def feature_dimension(self) -> int:
        return int(self.gram.shape[0])

    def _features(self, sources: Mapping[str, Sequence[float]], context: Sequence[float]) -> np.ndarray:
        if set(sources) != set(self.source_dimensions):
            raise ValueError("every declared source must be supplied exactly once")
        chunks = []
        for key in sorted(self.source_dimensions):
            x = np.asarray(sources[key], dtype=float)
            if x.shape != (self.source_dimensions[key],) or not np.all(np.isfinite(x)):
                raise ValueError(f"invalid source vector for {key}")
            chunks.append(x)
        c = np.asarray(context, dtype=float)
        if c.shape != (self.context_dimension,) or not np.all(np.isfinite(c)):
            raise ValueError("invalid context feature vector")
        chunks.extend([c, np.ones(1)])
        return np.concatenate(chunks)

    def coefficients(self) -> np.ndarray:
        regularised = self.gram + self.ridge * np.eye(self.feature_dimension)
        return np.linalg.solve(regularised, self.cross)

    def predict(self, sources: Mapping[str, Sequence[float]], context: Sequence[float]) -> np.ndarray:
        phi = self._features(sources, context)
        self.prediction_count += 1
        return phi @ self.coefficients()

    def update(
        self,
        sources: Mapping[str, Sequence[float]],
        context: Sequence[float],
        target: Sequence[float],
    ) -> None:
        """Update only after the caller has obtained and scored a prediction."""
        phi = self._features(sources, context)
        y = np.asarray(target, dtype=float)
        if y.shape != (self.target_dimension,) or not np.all(np.isfinite(y)):
            raise ValueError("invalid target vector")
        self.gram *= self.forgetting
        self.cross *= self.forgetting
        self.gram += np.outer(phi, phi)
        self.cross += np.outer(phi, y)
        self.sample_count += 1
        self.update_count += 1

    def marginal_loss_contributions(
        self,
        sources: Mapping[str, Sequence[float]],
        context: Sequence[float],
        target: Sequence[float],
    ) -> dict[str, float]:
        """Return full-loss minus/against ablated-loss diagnostics per source.

        Positive values mean removing the source increases squared prediction
        loss. Correlation can make these contributions unstable or ambiguous;
        they are not causal attribution.
        """
        phi = self._features(sources, context)
        y = np.asarray(target, dtype=float)
        if y.shape != (self.target_dimension,) or not np.all(np.isfinite(y)):
            raise ValueError("invalid target vector")
        beta = self.coefficients()
        full_prediction = phi @ beta
        full_loss = float(np.sum((y - full_prediction) ** 2))
        values: dict[str, float] = {}
        for key, slc in self._source_slices.items():
            ablated = phi.copy()
            ablated[slc] = 0.0
            ablated_loss = float(np.sum((y - ablated @ beta) ** 2))
            values[key] = ablated_loss - full_loss
        return values

    def source_feature_usage(self, sources: Mapping[str, Sequence[float]]) -> dict[str, float]:
        """Report absolute contribution magnitude from each source block."""
        phi = self._features(sources, np.zeros(self.context_dimension))
        beta = self.coefficients()
        return {
            key: float(np.linalg.norm(phi[slc] @ beta[slc]))
            for key, slc in self._source_slices.items()
        }

    def resource_snapshot(self) -> dict[str, int | float]:
        return {
            "sufficient_statistic_bytes": int(self.gram.nbytes + self.cross.nbytes),
            "parameter_count": int(self.feature_dimension * self.target_dimension),
            "update_outer_product_multiply_adds": int(self.feature_dimension * self.feature_dimension + self.feature_dimension * self.target_dimension),
            "query_multiply_adds": int(self.feature_dimension * self.target_dimension),
            "sample_count": self.sample_count,
        }
