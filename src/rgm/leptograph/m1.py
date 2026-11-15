"""Heterogeneous routing and geometric invariance primitives for HLG-M1."""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]


def _matrix(value: ArrayLike, *, name: str) -> FloatArray:
    result = np.asarray(value, dtype=np.float64)
    if result.ndim != 2 or min(result.shape, default=0) < 1:
        raise ValueError(f"{name} must be a non-empty two-dimensional matrix")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    return result


def _vector(value: ArrayLike, *, name: str) -> FloatArray:
    result = np.asarray(value, dtype=np.float64)
    if result.ndim != 1 or result.size < 1:
        raise ValueError(f"{name} must be a non-empty one-dimensional vector")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    return result


def _change_matrix(value: ArrayLike, dimension: int, *, name: str) -> FloatArray:
    result = _matrix(value, name=name)
    if result.shape != (dimension, dimension):
        raise ValueError(f"{name} must have shape ({dimension}, {dimension})")
    if np.linalg.matrix_rank(result) != dimension:
        raise ValueError(f"{name} must be invertible")
    return result


def _orthogonal_matrix(value: ArrayLike, dimension: int, *, name: str) -> FloatArray:
    result = _change_matrix(value, dimension, name=name)
    if not np.allclose(result.T @ result, np.eye(dimension), rtol=1e-10, atol=1e-10):
        raise ValueError(f"{name} must be orthogonal")
    return result


def _metric(value: ArrayLike, dimension: int, *, name: str) -> FloatArray:
    result = _matrix(value, name=name)
    if result.shape != (dimension, dimension):
        raise ValueError(f"{name} must have shape ({dimension}, {dimension})")
    if not np.allclose(result, result.T, rtol=1e-12, atol=1e-12):
        raise ValueError(f"{name} must be symmetric")
    try:
        np.linalg.cholesky(result)
    except np.linalg.LinAlgError as exc:
        raise ValueError(f"{name} must be positive definite") from exc
    return result


def route(operator: ArrayLike, source_state: ArrayLike) -> FloatArray:
    """Apply K: R^d_source -> R^d_target to a source coordinate vector."""
    matrix = _matrix(operator, name="operator")
    vector = _vector(source_state, name="source_state")
    if vector.shape[0] != matrix.shape[1]:
        raise ValueError("source_state dimension must match operator input dimension")
    return matrix @ vector


def compose_routes(*operators: ArrayLike) -> FloatArray:
    """Compose K1, K2, ... in traversal order as ... @ K2 @ K1."""
    if not operators:
        raise ValueError("at least one route operator is required")
    result = _matrix(operators[0], name="operator[0]").copy()
    for index, item in enumerate(operators[1:], start=1):
        next_operator = _matrix(item, name=f"operator[{index}]")
        if next_operator.shape[1] != result.shape[0]:
            raise ValueError(
                f"operator[{index}] expects dimension {next_operator.shape[1]}, "
                f"but preceding route produces {result.shape[0]}"
            )
        result = next_operator @ result
    return result


def transform_linear_map(
    operator: ArrayLike,
    source_change: ArrayLike,
    target_change: ArrayLike,
) -> FloatArray:
    """Return K' = A_target^{-1} K A_source.

    Coordinate convention: x_old = A_source @ x_new and
    y_old = A_target @ y_new. The represented abstract map is unchanged.
    """
    matrix = _matrix(operator, name="operator")
    source = _change_matrix(source_change, matrix.shape[1], name="source_change")
    target = _change_matrix(target_change, matrix.shape[0], name="target_change")
    return np.linalg.solve(target, matrix @ source)


def transform_inner_product(metric: ArrayLike, coordinate_change: ArrayLike) -> FloatArray:
    """Transform a metric covariantly: G' = A.T @ G @ A."""
    g = _matrix(metric, name="metric")
    if g.shape[0] != g.shape[1]:
        raise ValueError("metric must be square")
    g = _metric(g, g.shape[0], name="metric")
    change = _change_matrix(coordinate_change, g.shape[0], name="coordinate_change")
    return change.T @ g @ change


def metric_norm(vector: ArrayLike, metric: ArrayLike) -> float:
    """Return sqrt(x.T G x) for a positive-definite metric G."""
    x = _vector(vector, name="vector")
    g = _metric(metric, x.shape[0], name="metric")
    squared = float(x @ g @ x)
    return math.sqrt(max(0.0, squared))


def metric_singular_values(
    operator: ArrayLike,
    source_metric: ArrayLike,
    target_metric: ArrayLike,
) -> FloatArray:
    """Singular values of a map between the specified finite-dimensional metrics.

    If G = C.T C (Cholesky whitening), the Euclidean representative is
    C_target @ K @ inv(C_source). Its singular values are intrinsic to the
    linear map plus the two inner products.
    """
    matrix = _matrix(operator, name="operator")
    gs = _metric(source_metric, matrix.shape[1], name="source_metric")
    gt = _metric(target_metric, matrix.shape[0], name="target_metric")
    cs = np.linalg.cholesky(gs).T
    ct = np.linalg.cholesky(gt).T
    right_whitened = np.linalg.solve(cs.T, matrix.T).T
    whitened = ct @ right_whitened
    return np.linalg.svd(whitened, compute_uv=False)


def operator_diagnostics(operator: ArrayLike, *, relative_tolerance: float | None = None) -> dict:
    """Return rank, nullity, codimension and nonzero-spectrum conditioning."""
    matrix = _matrix(operator, name="operator")
    singular = np.linalg.svd(matrix, compute_uv=False)
    largest = float(singular[0]) if singular.size else 0.0
    if relative_tolerance is None:
        threshold = max(matrix.shape) * np.finfo(np.float64).eps * largest
    else:
        relative_tolerance = float(relative_tolerance)
        if not math.isfinite(relative_tolerance) or relative_tolerance < 0.0:
            raise ValueError("relative_tolerance must be finite and non-negative")
        threshold = relative_tolerance * largest
    rank = int(np.count_nonzero(singular > threshold))
    positive = singular[singular > threshold]
    effective_condition = (
        float(positive[0] / positive[-1]) if positive.size else None
    )
    source_dim = int(matrix.shape[1])
    target_dim = int(matrix.shape[0])
    return {
        "source_dimension": source_dim,
        "target_dimension": target_dim,
        "rank": rank,
        "nullity": source_dim - rank,
        "image_codimension": target_dim - rank,
        "injective": rank == source_dim,
        "surjective": rank == target_dim,
        "effective_condition_number": effective_condition,
        "singular_values": singular.tolist(),
        "rank_threshold": float(threshold),
    }


def factor_routing_operator(encoder: ArrayLike, decoder: ArrayLike) -> FloatArray:
    """Compose encoder S: source -> interface and decoder D: interface -> target."""
    s = _matrix(encoder, name="encoder")
    d = _matrix(decoder, name="decoder")
    if d.shape[1] != s.shape[0]:
        raise ValueError("decoder input dimension must equal encoder output dimension")
    return d @ s


def gauge_reparameterize_factorization(
    encoder: ArrayLike, decoder: ArrayLike, gauge: ArrayLike
) -> tuple[FloatArray, FloatArray]:
    """Apply S' = A S, D' = D A^{-1}; D'S' equals DS for invertible A."""
    s = _matrix(encoder, name="encoder")
    d = _matrix(decoder, name="decoder")
    if d.shape[1] != s.shape[0]:
        raise ValueError("encoder and decoder interface dimensions do not match")
    a = _change_matrix(gauge, s.shape[0], name="gauge")
    s_new = a @ s
    d_new = np.linalg.solve(a.T, d.T).T
    return s_new, d_new


def transform_factorization(
    encoder: ArrayLike,
    decoder: ArrayLike,
    source_change: ArrayLike,
    interface_change: ArrayLike,
    target_change: ArrayLike,
) -> tuple[FloatArray, FloatArray]:
    """Transform a factorized map under independent source/interface/target bases."""
    s = _matrix(encoder, name="encoder")
    d = _matrix(decoder, name="decoder")
    if d.shape[1] != s.shape[0]:
        raise ValueError("encoder and decoder interface dimensions do not match")
    a_s = _change_matrix(source_change, s.shape[1], name="source_change")
    a_f = _change_matrix(interface_change, s.shape[0], name="interface_change")
    a_t = _change_matrix(target_change, d.shape[0], name="target_change")
    s_new = np.linalg.solve(a_f, s @ a_s)
    d_new = np.linalg.solve(a_t, d @ a_f)
    return s_new, d_new


def _orthonormal_frame(value: ArrayLike, *, name: str) -> FloatArray:
    frame = _matrix(value, name=name)
    rows, columns = frame.shape
    if rows < columns:
        raise ValueError(f"{name} must have at least as many rows as columns")
    if np.linalg.matrix_rank(frame) != columns:
        raise ValueError(f"{name} must have full column rank")
    if not np.allclose(frame.T @ frame, np.eye(columns), rtol=1e-10, atol=1e-10):
        raise ValueError(f"{name} columns must be orthonormal")
    return frame


def projector_from_frame(frame: ArrayLike) -> FloatArray:
    """Return the orthogonal projector P = U U.T for an orthonormal frame U."""
    u = _orthonormal_frame(frame, name="frame")
    return u @ u.T


def transform_projector(projector: ArrayLike, ambient_change: ArrayLike) -> FloatArray:
    """Transform an orthogonal projector under an orthonormal basis change."""
    p = _matrix(projector, name="projector")
    if p.shape[0] != p.shape[1]:
        raise ValueError("projector must be square")
    q = _orthogonal_matrix(ambient_change, p.shape[0], name="ambient_change")
    return q.T @ p @ q


def principal_angles(first_frame: ArrayLike, second_frame: ArrayLike) -> FloatArray:
    """Return principal angles (radians) between equal-rank subspaces."""
    u = _orthonormal_frame(first_frame, name="first_frame")
    v = _orthonormal_frame(second_frame, name="second_frame")
    if u.shape != v.shape:
        raise ValueError("frames must have the same ambient dimension and subspace rank")
    cosines = np.linalg.svd(u.T @ v, compute_uv=False)
    return np.arccos(np.clip(cosines, 0.0, 1.0))


def grassmann_distance(first_frame: ArrayLike, second_frame: ArrayLike) -> float:
    """Canonical Grassmann geodesic distance from principal angles."""
    angles = principal_angles(first_frame, second_frame)
    return float(np.linalg.norm(angles))


def verify_factor_rank_bound(encoder: ArrayLike, decoder: ArrayLike) -> bool:
    """Verify rank(D S) <= min(rank(D), rank(S), interface dimension)."""
    s = _matrix(encoder, name="encoder")
    d = _matrix(decoder, name="decoder")
    if d.shape[1] != s.shape[0]:
        raise ValueError("encoder and decoder interface dimensions do not match")
    return (
        np.linalg.matrix_rank(d @ s)
        <= min(np.linalg.matrix_rank(d), np.linalg.matrix_rank(s), s.shape[0])
    )


def _qr_orthogonal(rng: np.random.Generator, dimension: int) -> FloatArray:
    raw = rng.standard_normal((dimension, dimension))
    q, r = np.linalg.qr(raw)
    signs = np.where(np.diag(r) < 0.0, -1.0, 1.0)
    return q * signs[None, :]


def _case_a() -> dict:
    rng = np.random.default_rng(1101)
    ds, dt = 3, 6
    k = rng.normal(size=(dt, ds))
    x = rng.normal(size=ds)
    qs, qt = _qr_orthogonal(rng, ds), _qr_orthogonal(rng, dt)
    x_new = qs.T @ x
    k_new = transform_linear_map(k, qs, qt)
    y_new = route(k_new, x_new)
    expected = qt.T @ route(k, x)
    covariance_error = float(np.max(np.abs(y_new - expected)))
    norm_error = abs(float(np.linalg.norm(k_new, ord="fro") - np.linalg.norm(k, ord="fro")))
    sv_error = float(np.max(np.abs(np.linalg.svd(k_new, compute_uv=False) - np.linalg.svd(k, compute_uv=False))))
    return {
        "case_id": "M1-A",
        "description": "Independent orthonormal source/target basis covariance",
        "operator_shape": list(k.shape),
        "covariance_error": covariance_error,
        "frobenius_norm_error": norm_error,
        "singular_spectrum_error": sv_error,
        "tolerance": 2e-10,
        "passed": bool(max(covariance_error, norm_error, sv_error) <= 2e-10),
    }


def _case_b() -> dict:
    rng = np.random.default_rng(1102)
    ds, dt = 3, 5
    k = rng.normal(size=(dt, ds))
    raw_s = rng.normal(size=(ds, ds))
    raw_t = rng.normal(size=(dt, dt))
    gs = raw_s.T @ raw_s + 0.8 * np.eye(ds)
    gt = raw_t.T @ raw_t + 1.1 * np.eye(dt)
    a_s = np.eye(ds) + 0.18 * rng.normal(size=(ds, ds))
    a_t = np.eye(dt) + 0.14 * rng.normal(size=(dt, dt))
    x_old = rng.normal(size=ds)
    y_old = route(k, x_old)
    x_new = np.linalg.solve(a_s, x_old)
    k_new = transform_linear_map(k, a_s, a_t)
    gs_new = transform_inner_product(gs, a_s)
    gt_new = transform_inner_product(gt, a_t)
    y_new = route(k_new, x_new)
    y_coordinates_old_basis = np.linalg.solve(a_t, y_old)
    source_norm_error = abs(metric_norm(x_old, gs) - metric_norm(x_new, gs_new))
    target_norm_error = abs(metric_norm(y_old, gt) - metric_norm(y_new, gt_new))
    route_error = float(np.max(np.abs(y_new - y_coordinates_old_basis)))
    sv_before = metric_singular_values(k, gs, gt)
    sv_after = metric_singular_values(k_new, gs_new, gt_new)
    sv_error = float(np.max(np.abs(sv_before - sv_after)))
    maximum = max(source_norm_error, target_norm_error, route_error, sv_error)
    return {
        "case_id": "M1-B",
        "description": "General invertible coordinate covariance with metric transport",
        "operator_shape": list(k.shape),
        "source_metric_norm_error": source_norm_error,
        "target_metric_norm_error": target_norm_error,
        "route_coordinate_error": route_error,
        "metric_singular_spectrum_error": sv_error,
        "tolerance": 2e-9,
        "passed": bool(maximum <= 2e-9),
    }


def _case_c() -> dict:
    rng = np.random.default_rng(1103)
    dimensions = (2, 4, 3, 5)
    links = [
        rng.normal(size=(dimensions[i + 1], dimensions[i]))
        for i in range(len(dimensions) - 1)
    ]
    bases = [_qr_orthogonal(rng, dimension) for dimension in dimensions]
    transformed = [
        transform_linear_map(k, bases[i], bases[i + 1])
        for i, k in enumerate(links)
    ]
    composite = compose_routes(*links)
    composite_new = compose_routes(*transformed)
    expected = transform_linear_map(composite, bases[0], bases[-1])
    chain_error = float(np.max(np.abs(composite_new - expected)))
    source = rng.normal(size=dimensions[0])
    output_old = route(composite, source)
    output_new = route(composite_new, bases[0].T @ source)
    output_expected = bases[-1].T @ output_old
    route_error = float(np.max(np.abs(output_new - output_expected)))
    return {
        "case_id": "M1-C",
        "description": "Covariant composition across a heterogeneous 2-4-3-5 dimensional chain",
        "dimensions": list(dimensions),
        "composite_shape": list(composite.shape),
        "composition_covariance_error": chain_error,
        "route_covariance_error": route_error,
        "tolerance": 2e-10,
        "passed": bool(max(chain_error, route_error) <= 2e-10),
    }


def _case_d() -> dict:
    rng = np.random.default_rng(1104)
    ds, q, dt = 2, 4, 5
    encoder = rng.normal(size=(q, ds))
    decoder = rng.normal(size=(dt, q))
    gauge = np.eye(q) + 0.25 * rng.normal(size=(q, q))
    k = factor_routing_operator(encoder, decoder)
    s_new, d_new = gauge_reparameterize_factorization(encoder, decoder, gauge)
    k_new = factor_routing_operator(s_new, d_new)
    source = rng.normal(size=ds)
    output_error = float(np.max(np.abs(route(k, source) - route(k_new, source))))
    composite_error = float(np.max(np.abs(k - k_new)))
    qs, qf, qt = (
        _qr_orthogonal(rng, ds), _qr_orthogonal(rng, q), _qr_orthogonal(rng, dt)
    )
    s_basis, d_basis = transform_factorization(encoder, decoder, qs, qf, qt)
    k_basis = factor_routing_operator(s_basis, d_basis)
    expected_basis = transform_linear_map(k, qs, qt)
    basis_error = float(np.max(np.abs(k_basis - expected_basis)))
    rank_bound = verify_factor_rank_bound(encoder, decoder)
    return {
        "case_id": "M1-D",
        "description": "Interface GL-gauge non-identifiability and three-space basis covariance",
        "encoder_shape": list(encoder.shape),
        "decoder_shape": list(decoder.shape),
        "composite_shape": list(k.shape),
        "gauge_composite_error": composite_error,
        "gauge_route_error": output_error,
        "basis_composition_error": basis_error,
        "factor_rank_bound": bool(rank_bound),
        "tolerance": 2e-10,
        "passed": bool(max(composite_error, output_error, basis_error) <= 2e-10 and rank_bound),
    }


def _case_e() -> dict:
    rng = np.random.default_rng(1105)
    embedding = rng.normal(size=(5, 3))
    projection = rng.normal(size=(2, 5))
    rank_limited_s = rng.normal(size=(2, 4))
    rank_limited_d = rng.normal(size=(6, 2))
    embedding_info = operator_diagnostics(embedding)
    projection_info = operator_diagnostics(projection)
    rank_limited = factor_routing_operator(rank_limited_s, rank_limited_d)
    factor_info = operator_diagnostics(rank_limited)
    basis_s, basis_t = _qr_orthogonal(rng, 3), _qr_orthogonal(rng, 5)
    embedding_rotated = transform_linear_map(embedding, basis_s, basis_t)
    rotated_info = operator_diagnostics(embedding_rotated)
    passed = bool(
        embedding_info["rank"] == rotated_info["rank"] == 3
        and embedding_info["injective"] is True
        and embedding_info["surjective"] is False
        and embedding_info["nullity"] == 0
        and embedding_info["image_codimension"] == 2
        and projection_info["rank"] == 2
        and projection_info["injective"] is False
        and projection_info["surjective"] is True
        and projection_info["nullity"] == 3
        and factor_info["rank"] <= 2
        and factor_info["nullity"] >= 2
    )
    return {
        "case_id": "M1-E",
        "description": "Rank-nullity, injectivity/surjectivity and interface rank bounds",
        "embedding": embedding_info,
        "projection": projection_info,
        "interface_composite": factor_info,
        "rotated_embedding_rank": rotated_info["rank"],
        "passed": passed,
    }


def _case_f() -> dict:
    rng = np.random.default_rng(1106)
    ambient, rank = 8, 3
    raw_u = rng.normal(size=(ambient, rank))
    raw_v = rng.normal(size=(ambient, rank))
    u, _ = np.linalg.qr(raw_u, mode="reduced")
    v, _ = np.linalg.qr(raw_v, mode="reduced")
    q = _qr_orthogonal(rng, ambient)
    r = _qr_orthogonal(rng, rank)
    s = _qr_orthogonal(rng, rank)
    angles_before = principal_angles(u, v)
    distance_before = grassmann_distance(u, v)
    u_new = q.T @ u @ r
    v_new = q.T @ v @ s
    angles_after = principal_angles(u_new, v_new)
    distance_after = grassmann_distance(u_new, v_new)
    projector_before = projector_from_frame(u)
    projector_after = projector_from_frame(u_new)
    expected_projector = transform_projector(projector_before, q)
    projector_error = float(np.max(np.abs(projector_after - expected_projector)))
    orthogonality_error = max(
        float(np.max(np.abs(u_new.T @ u_new - np.eye(rank)))),
        float(np.max(np.abs(v_new.T @ v_new - np.eye(rank)))),
    )
    angle_error = float(np.max(np.abs(angles_before - angles_after)))
    distance_error = abs(distance_before - distance_after)
    return {
        "case_id": "M1-F",
        "description": "Grassmannian principal-angle, projector and geodesic invariance",
        "ambient_dimension": ambient,
        "subspace_rank": rank,
        "principal_angle_error": angle_error,
        "geodesic_distance_error": distance_error,
        "projector_covariance_error": projector_error,
        "orthonormality_error": orthogonality_error,
        "distance_before": distance_before,
        "tolerance": 2e-10,
        "passed": bool(max(angle_error, distance_error, projector_error, orthogonality_error) <= 2e-10),
    }


CASE_IDS = ("M1-A", "M1-B", "M1-C", "M1-D", "M1-E", "M1-F")
_CASES = {
    "M1-A": _case_a,
    "M1-B": _case_b,
    "M1-C": _case_c,
    "M1-D": _case_d,
    "M1-E": _case_e,
    "M1-F": _case_f,
}


def run_case(case_id: str) -> dict:
    if case_id not in _CASES:
        raise ValueError(f"unknown M1 case {case_id!r}; expected {CASE_IDS}")
    result = _CASES[case_id]()
    result.update({"experiment_id": "HYBRID-LEPTOGRAPH-M1", "schema_version": "1.0"})
    return result
