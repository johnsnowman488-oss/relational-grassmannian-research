"""HLG-M2 multi-route, information and feedback stability tests."""
from __future__ import annotations

import numpy as np
import pytest

from rgm.leptograph.m2 import (
    assemble_network_operator,
    compose_path,
    feedback_diagnostics,
    multi_route_diagnostics,
    route_erasure_diagnostics,
    stack_parallel_routes,
    sum_parallel_routes,
)


def test_path_composition_uses_traversal_order() -> None:
    first = np.array([[1.0, 2.0], [0.0, 1.0]])
    second = np.array([[2.0, 0.0], [1.0, 3.0]])
    x = np.array([0.5, -1.0])
    np.testing.assert_allclose(compose_path(first, second) @ x, second @ (first @ x))


def test_parallel_routes_must_share_source_dimension() -> None:
    with pytest.raises(ValueError, match="same source dimension"):
        stack_parallel_routes(np.ones((2, 3)), np.ones((2, 4)))


def test_coalesced_and_stacked_route_banks_have_distinct_information() -> None:
    identity = np.eye(3)
    info = multi_route_diagnostics(identity, -identity)
    assert info["coalesced"]["rank"] == 0
    assert info["separately_observed"]["rank"] == 3
    assert info["cancellation_fraction"] == pytest.approx(1.0)
    np.testing.assert_allclose(sum_parallel_routes(identity, -identity), np.zeros((3, 3)))


def test_route_sum_requires_common_target_dimension() -> None:
    with pytest.raises(ValueError, match="target dimensions"):
        sum_parallel_routes(np.ones((2, 3)), np.ones((4, 3)))


def test_non_normal_feedback_can_be_asymptotically_stable_with_transient_growth() -> None:
    transition = np.array([[0.8, 6.0], [0.0, 0.8]])
    info = feedback_diagnostics(transition, horizon=12)
    assert info["spectral_radius"] == pytest.approx(0.8)
    assert info["asymptotically_stable"] is True
    assert info["one_step_contractive"] is False
    assert info["peak_transient_gain"] > 1.0


def test_spectral_radius_not_limited_to_induced_norm_threshold() -> None:
    transition = np.array([[1.2, 0.0], [0.0, 0.2]])
    info = feedback_diagnostics(transition)
    assert info["asymptotically_stable"] is False
    assert info["spectral_radius"] == pytest.approx(1.2)


def test_heterogeneous_network_operator_uses_target_source_block_order() -> None:
    dimensions = {"a": 2, "b": 3}
    edge_ab = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    edge_ba = np.array([[0.5, 0.0, 0.0], [0.0, 0.5, 0.0]])
    network = assemble_network_operator(dimensions, [("a", "b", edge_ab), ("b", "a", edge_ba)])
    assert network.shape == (5, 5)
    np.testing.assert_allclose(network[:2, 2:], edge_ba)
    np.testing.assert_allclose(network[2:, :2], edge_ab)


def test_parallel_edges_add_in_the_same_block() -> None:
    dimensions = {"a": 2, "b": 2}
    edge = np.eye(2) * 0.2
    network = assemble_network_operator(dimensions, [("a", "b", edge), ("a", "b", edge)])
    np.testing.assert_allclose(network[2:, :2], 2.0 * edge)


def test_network_rejects_incompatible_edge_shapes() -> None:
    with pytest.raises(ValueError, match="must have shape"):
        assemble_network_operator({"a": 2, "b": 3}, [("a", "b", np.eye(2))])


def test_route_erasure_reports_redundant_information_channels() -> None:
    routes = (
        np.array([[1.0, 0.0], [0.0, 0.0], [0.0, 0.0]]),
        np.array([[0.0, 0.0], [0.0, 1.0], [0.0, 0.0]]),
        np.array([[1.0, 1.0], [1.0, -1.0], [0.0, 1.0]]),
    )
    info = route_erasure_diagnostics(*routes)
    assert info["minimum_rank_after_single_erasure"] == 2
    assert info["maximum_nullity_after_single_erasure"] == 0


@pytest.mark.parametrize("bad_horizon", [-1, 1.5, True, 1001])
def test_invalid_feedback_horizon_is_rejected(bad_horizon: int) -> None:
    with pytest.raises(ValueError):
        feedback_diagnostics(np.eye(2), horizon=bad_horizon)


def test_feedback_requires_square_operator() -> None:
    with pytest.raises(ValueError, match="square"):
        feedback_diagnostics(np.ones((2, 3)))
