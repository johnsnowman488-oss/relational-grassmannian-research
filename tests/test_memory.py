import numpy as np
import pytest
from rgm.memory import DEFAULT_DECAY_RATES, SOEMemory

def test_default_configuration_has_four_channels_and_sixteen_features():
    memory = SOEMemory()
    assert memory.channel_count == 4
    assert memory.feature_dim == 16
    np.testing.assert_allclose(memory.decay_rates, DEFAULT_DECAY_RATES)
    np.testing.assert_array_equal(memory.snapshot(), np.zeros((4, 16)))

def test_channel_decay_matches_analytical_exponential():
    memory = SOEMemory(feature_dim=2, decay_rates=[0.1, 0.5])
    memory.update([1.0, -2.0], dt=0.0)
    result = memory.advance(2.0)
    expected = np.array([[1.0, -2.0], [1.0, -2.0]]) * np.exp(-np.array([0.1, 0.5])[:, None] * 2.0)
    np.testing.assert_allclose(result, expected, rtol=1e-13, atol=1e-13)

def test_new_event_is_injected_after_decay_and_rates_differ():
    memory = SOEMemory(feature_dim=1, decay_rates=[0.1, 0.9])
    memory.update([2.0], dt=0.0)
    updated = memory.update([1.0], dt=1.0)
    expected = 2.0 * np.exp(-np.array([0.1, 0.9])) + 1.0
    np.testing.assert_allclose(updated[:, 0], expected)
    assert updated[0, 0] > updated[1, 0]

def test_repeated_constant_input_has_predictable_trace():
    gamma = 0.2
    memory = SOEMemory(feature_dim=1, decay_rates=[gamma])
    outputs = [memory.update([1.0], dt=1.0)[0, 0] for _ in range(5)]
    expected = [sum(np.exp(-gamma * j) for j in range(k + 1)) for k in range(5)]
    np.testing.assert_allclose(outputs, expected)

def test_snapshot_is_a_defensive_copy_and_reset_clears_state():
    memory = SOEMemory(feature_dim=2)
    memory.update([1.0, 2.0])
    snapshot = memory.snapshot()
    snapshot[:] = 99.0
    assert not np.all(memory.channels == 99.0)
    memory.reset()
    np.testing.assert_array_equal(memory.channels, np.zeros((4, 2)))

def test_serialization_round_trip_preserves_next_trajectory():
    memory = SOEMemory(feature_dim=3)
    memory.update([0.1, 0.2, 0.3], dt=0.7)
    restored = SOEMemory.from_dict(memory.to_dict())
    np.testing.assert_array_equal(restored.channels, memory.channels)
    np.testing.assert_array_equal(restored.decay_rates, memory.decay_rates)
    next_a = memory.update([1.0, -1.0, 0.5], dt=1.25)
    next_b = restored.update([1.0, -1.0, 0.5], dt=1.25)
    np.testing.assert_array_equal(next_a, next_b)

@pytest.mark.parametrize("dt", [-1.0, np.nan, np.inf])
def test_invalid_elapsed_time_is_rejected(dt):
    with pytest.raises(ValueError):
        SOEMemory(feature_dim=2).advance(dt)

def test_invalid_feature_shape_and_non_finite_values_are_rejected():
    memory = SOEMemory(feature_dim=2)
    with pytest.raises(ValueError):
        memory.update([1.0])
    with pytest.raises(ValueError):
        memory.update([1.0, np.nan])

def test_invalid_rates_and_injection_shape_are_rejected():
    with pytest.raises(ValueError):
        SOEMemory(feature_dim=2, decay_rates=[0.0])
    with pytest.raises(ValueError):
        SOEMemory(feature_dim=2, decay_rates=[0.1], injection_matrices=np.ones((1, 2, 1)))
