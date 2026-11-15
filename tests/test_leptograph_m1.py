"""HLG-M1 algebraic invariance, rank and Grassmannian tests."""
from __future__ import annotations

import numpy as np
import pytest

from rgm.leptograph.m1 import (
    compose_routes,
    factor_routing_operator,
    gauge_reparameterize_factorization,
    grassmann_distance,
    metric_norm,
    metric_singular_values,
    operator_diagnostics,
    principal_angles,
    projector_from_frame,
    route,
    transform_factorization,
    transform_inner_product,
    transform_linear_map,
    transform_projector,
    verify_factor_rank_bound,
)


def _orthogonal(rng: np.random.Generator, n: int) -> np.ndarray:
    q, r = np.linalg.qr(rng.normal(size=(n, n)))
    return q * np.where(np.diag(r) < 0.0, -1.0, 1.0)[None, :]


@pytest.mark.parametrize("seed", range(10))
def test_orthonormal_basis_changes_preserve_route_and_singular_values(seed: int) -> None:
    rng = np.random.default_rng(seed)
    ds, dt = 2 + seed % 4, 5 + seed % 3
    k, x = rng.normal(size=(dt, ds)), rng.normal(size=ds)
    qs, qt = _orthogonal(rng, ds), _orthogonal(rng, dt)
    k_new = transform_linear_map(k, qs, qt)
    x_new = qs.T @ x
    y_new = route(k_new, x_new)
    np.testing.assert_allclose(y_new, qt.T @ route(k, x), rtol=1e-11, atol=1e-11)
    np.testing.assert_allclose(
        np.linalg.svd(k_new, compute_uv=False),
        np.linalg.svd(k, compute_uv=False), rtol=1e-11, atol=1e-11,
    )
    assert np.linalg.norm(k_new, ord="fro") == pytest.approx(np.linalg.norm(k, ord="fro"))


@pytest.mark.parametrize("seed", range(8))
def test_general_coordinate_changes_transport_metrics_and_preserve_intrinsic_spectrum(seed: int) -> None:
    rng = np.random.default_rng(100 + seed)
    ds, dt = 2 + seed % 3, 4 + seed % 4
    k = rng.normal(size=(dt, ds))
    bs, bt = rng.normal(size=(ds, ds)), rng.normal(size=(dt, dt))
    gs, gt = bs.T @ bs + np.eye(ds), bt.T @ bt + np.eye(dt)
    a_s = np.eye(ds) + 0.12 * rng.normal(size=(ds, ds))
    a_t = np.eye(dt) + 0.12 * rng.normal(size=(dt, dt))
    assert np.linalg.matrix_rank(a_s) == ds
    assert np.linalg.matrix_rank(a_t) == dt
    x_old = rng.normal(size=ds)
    x_new = np.linalg.solve(a_s, x_old)
    y_old = route(k, x_old)
    k_new = transform_linear_map(k, a_s, a_t)
    gs_new, gt_new = transform_inner_product(gs, a_s), transform_inner_product(gt, a_t)
    y_new = route(k_new, x_new)
    np.testing.assert_allclose(y_new, np.linalg.solve(a_t, y_old), rtol=1e-10, atol=1e-10)
    assert metric_norm(x_old, gs) == pytest.approx(metric_norm(x_new, gs_new), rel=1e-10, abs=1e-10)
    assert metric_norm(y_old, gt) == pytest.approx(metric_norm(y_new, gt_new), rel=1e-10, abs=1e-10)
    np.testing.assert_allclose(
        metric_singular_values(k, gs, gt),
        metric_singular_values(k_new, gs_new, gt_new),
        rtol=1e-9, atol=1e-9,
    )


def test_heterogeneous_chain_composition_is_basis_covariant() -> None:
    rng = np.random.default_rng(202)
    dims = (2, 5, 3, 6)
    maps = [rng.normal(size=(dims[i+1], dims[i])) for i in range(3)]
    bases = [_orthogonal(rng, d) for d in dims]
    maps_new = [transform_linear_map(k, bases[i], bases[i+1]) for i, k in enumerate(maps)]
    composed = compose_routes(*maps)
    composed_new = compose_routes(*maps_new)
    expected = transform_linear_map(composed, bases[0], bases[-1])
    np.testing.assert_allclose(composed_new, expected, rtol=1e-11, atol=1e-11)


def test_route_composition_rejects_incompatible_dimensions() -> None:
    with pytest.raises(ValueError, match="preceding route"):
        compose_routes(np.ones((3, 2)), np.ones((4, 5)))


@pytest.mark.parametrize("seed", range(8))
def test_interface_gl_gauge_changes_factors_not_composite(seed: int) -> None:
    rng = np.random.default_rng(300 + seed)
    ds, q, dt = 2 + seed % 2, 4, 5 + seed % 3
    encoder, decoder = rng.normal(size=(q, ds)), rng.normal(size=(dt, q))
    gauge = np.eye(q) + 0.2 * rng.normal(size=(q, q))
    s_new, d_new = gauge_reparameterize_factorization(encoder, decoder, gauge)
    np.testing.assert_allclose(d_new @ s_new, decoder @ encoder, rtol=1e-10, atol=1e-10)
    assert not np.allclose(s_new, encoder)


def test_factorization_transforms_covariantly_across_all_three_spaces() -> None:
    rng = np.random.default_rng(405)
    ds, q, dt = 3, 4, 5
    s, d = rng.normal(size=(q, ds)), rng.normal(size=(dt, q))
    qs, qf, qt = _orthogonal(rng, ds), _orthogonal(rng, q), _orthogonal(rng, dt)
    s_new, d_new = transform_factorization(s, d, qs, qf, qt)
    expected = transform_linear_map(d @ s, qs, qt)
    np.testing.assert_allclose(d_new @ s_new, expected, rtol=1e-11, atol=1e-11)
    assert verify_factor_rank_bound(s, d)


def test_factor_rank_bound_holds_for_rank_limited_interface() -> None:
    rng = np.random.default_rng(406)
    s = rng.normal(size=(2, 5))
    d = rng.normal(size=(7, 2))
    assert np.linalg.matrix_rank(d @ s) <= 2
    assert verify_factor_rank_bound(s, d)


def test_operator_diagnostics_report_rectangular_information_loss() -> None:
    rng = np.random.default_rng(501)
    embedding = rng.normal(size=(6, 3))
    projection = rng.normal(size=(2, 5))
    e, p = operator_diagnostics(embedding), operator_diagnostics(projection)
    assert e["rank"] == 3 and e["injective"] and not e["surjective"]
    assert e["nullity"] == 0 and e["image_codimension"] == 3
    assert p["rank"] == 2 and not p["injective"] and p["surjective"]
    assert p["nullity"] == 3 and p["image_codimension"] == 0


@pytest.mark.parametrize("seed", range(8))
def test_grassmannian_principal_angles_and_distance_are_invariant(seed: int) -> None:
    rng = np.random.default_rng(600 + seed)
    n, k = 7 + seed % 3, 2 + seed % 2
    u, _ = np.linalg.qr(rng.normal(size=(n, k)), mode="reduced")
    v, _ = np.linalg.qr(rng.normal(size=(n, k)), mode="reduced")
    q, r, s = _orthogonal(rng, n), _orthogonal(rng, k), _orthogonal(rng, k)
    before_angles = principal_angles(u, v)
    after_angles = principal_angles(q.T @ u @ r, q.T @ v @ s)
    np.testing.assert_allclose(before_angles, after_angles, rtol=1e-11, atol=1e-11)
    assert grassmann_distance(u, v) == pytest.approx(
        grassmann_distance(q.T @ u @ r, q.T @ v @ s), abs=1e-11
    )


def test_projector_transforms_by_conjugation_and_keeps_invariants() -> None:
    rng = np.random.default_rng(701)
    u, _ = np.linalg.qr(rng.normal(size=(8, 3)), mode="reduced")
    q = _orthogonal(rng, 8)
    p = projector_from_frame(u)
    p_new = transform_projector(p, q)
    u_new = q.T @ u
    np.testing.assert_allclose(p_new, projector_from_frame(u_new), atol=1e-11)
    np.testing.assert_allclose(p_new, p_new.T, atol=1e-11)
    np.testing.assert_allclose(p_new @ p_new, p_new, atol=1e-11)
    assert np.linalg.matrix_rank(p_new) == 3


@pytest.mark.parametrize("bad_metric", [
    np.array([[1.0, 2.0], [2.0, 1.0]]),
    np.array([[1.0, 0.0], [0.0, 0.0]]),
    np.array([[1.0, 0.1], [0.0, 1.0]]),
])
def test_invalid_metrics_are_rejected(bad_metric: np.ndarray) -> None:
    with pytest.raises(ValueError):
        metric_singular_values(np.eye(2), bad_metric, np.eye(2))


def test_singular_coordinate_changes_are_rejected() -> None:
    with pytest.raises(ValueError, match="invertible"):
        transform_linear_map(np.eye(2), np.array([[1.0, 0.0], [0.0, 0.0]]), np.eye(2))


def test_nonorthogonal_ambient_transform_is_rejected_for_projector_invariance() -> None:
    with pytest.raises(ValueError, match="orthogonal"):
        transform_projector(np.eye(2), np.diag([2.0, 1.0]))


def test_frames_with_nonorthonormal_columns_are_rejected() -> None:
    with pytest.raises(ValueError, match="orthonormal"):
        projector_from_frame(np.array([[1.0, 0.0], [0.0, 2.0], [0.0, 0.0]]))
