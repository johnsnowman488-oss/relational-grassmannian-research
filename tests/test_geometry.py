import numpy as np
import pytest
from rgm.geometry import GrassmannianPoint, canonical_distance, evolve_subspace, principal_angles, projector_from_frame

def test_initialization_and_projector_invariants():
    point = GrassmannianPoint.random(ambient_dim=16, rank=4, seed=13)
    q = point.frame
    p = point.projector
    assert q.shape == (16, 4)
    np.testing.assert_allclose(q.T @ q, np.eye(4), atol=1e-12)
    np.testing.assert_allclose(p.T, p, atol=1e-12)
    np.testing.assert_allclose(p @ p, p, atol=1e-12)
    assert np.linalg.matrix_rank(p, tol=1e-10) == 4

def test_projector_is_invariant_under_basis_change():
    rng = np.random.default_rng(7)
    q = GrassmannianPoint(rng.normal(size=(8, 3))).frame
    rotation = GrassmannianPoint(rng.normal(size=(3, 3))).frame
    p1, p2 = projector_from_frame(q), projector_from_frame(q @ rotation)
    np.testing.assert_allclose(p1, p2, atol=1e-12)

def test_identical_subspaces_have_zero_distance_and_angles():
    point = GrassmannianPoint.random(10, 3, seed=5)
    assert canonical_distance(point.frame, point.frame) == pytest.approx(0.0, abs=1e-12)
    np.testing.assert_allclose(principal_angles(point.frame, point.frame), 0.0, atol=1e-12)

def test_distance_is_symmetric_and_non_negative():
    a, b = GrassmannianPoint.random(12, 4, seed=1), GrassmannianPoint.random(12, 4, seed=2)
    d_ab, d_ba = canonical_distance(a.frame, b.frame), canonical_distance(b.frame, a.frame)
    assert d_ab >= 0.0
    assert d_ab == pytest.approx(d_ba, abs=1e-12)

def test_skew_generator_update_preserves_grassmannian_invariants():
    rng = np.random.default_rng(11)
    raw = rng.normal(size=(16, 16))
    omega = raw - raw.T
    initial = GrassmannianPoint.random(16, 4, seed=4)
    updated = evolve_subspace(initial, omega, step_size=0.03)
    np.testing.assert_allclose(updated.frame.T @ updated.frame, np.eye(4), atol=1e-12)
    p = updated.projector
    np.testing.assert_allclose(p.T, p, atol=1e-12)
    np.testing.assert_allclose(p @ p, p, atol=1e-12)
    assert updated.rank == 4
    assert canonical_distance(initial.frame, updated.frame) > 0.0

def test_invalid_generator_and_rank_deficient_frames_are_rejected():
    point = GrassmannianPoint.random(6, 2, seed=3)
    with pytest.raises(ValueError, match="skew-symmetric"):
        evolve_subspace(point, np.eye(6))
    with pytest.raises(ValueError, match="full column rank"):
        GrassmannianPoint(np.array([[1.0, 2.0], [2.0, 4.0], [3.0, 6.0]]))

def test_grassmannian_frame_is_read_only():
    point = GrassmannianPoint.random(6, 2, seed=3)
    with pytest.raises(ValueError):
        point.frame[0, 0] = 10.0

def test_random_initialization_is_reproducible_for_fixed_seed():
    first = GrassmannianPoint.random(ambient_dim=16, rank=4, seed=2026)
    second = GrassmannianPoint.random(ambient_dim=16, rank=4, seed=2026)
    np.testing.assert_array_equal(first.frame, second.frame)
