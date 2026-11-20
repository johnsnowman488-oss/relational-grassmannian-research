import numpy as np

from rgm.leptograph.m4.adaptive import M4AdaptiveController
from rgm.leptograph.m4.composition import RelationType
from rgm.leptograph.m4.system import M4ABSystem


def test_candidate_promotion_and_rollback_include_readout_bias():
    relation_types = (RelationType("r0", "Node", "Node"),)
    system = M4ABSystem("A", relation_types, max_path_depth=2)
    system.readout_weights = np.zeros_like(system.readout_weights)
    system.readout_bias = -0.75
    system.readout_fitted = True
    trusted = system.snapshot()

    candidate_weights = np.ones_like(system.readout_weights) * 0.125
    controller = M4AdaptiveController(system)
    controller.start_candidate(candidate_weights, bias=1.25)
    assert controller.validate_candidate(1.0, 0.25, identifiable=True)
    assert np.array_equal(system.readout_weights, candidate_weights)
    assert system.readout_bias == 1.25

    lifecycle = controller.lifecycle_snapshot()
    assert lifecycle["candidate_bias"] is None
    controller.rollback()
    assert np.array_equal(system.readout_weights, trusted["readout_weights"])
    assert system.readout_bias == trusted["readout_bias"]
    assert system.snapshot()["readout_bias"] == trusted["readout_bias"]


def test_rejected_candidate_does_not_change_readout_bias():
    system = M4ABSystem("A", (RelationType("r0", "Node", "Node"),), max_path_depth=2)
    system.readout_bias = -0.5
    before = system.snapshot()
    controller = M4AdaptiveController(system)
    controller.start_candidate(np.ones_like(system.readout_weights), bias=2.0)
    assert not controller.validate_candidate(0.1, 0.2, identifiable=True)
    assert system.readout_bias == before["readout_bias"]
    assert controller.lifecycle_snapshot()["candidate_bias"] is None
