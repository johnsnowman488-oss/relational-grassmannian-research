import numpy as np
import pytest
from rgm.experiments.e01 import VARIANTS, codebooks, event_vector, make_case, run_variant

def test_generator_is_deterministic_and_balanced():
    assert make_case(12345) == make_case(12345)
    assert make_case(12345).label == 1
    assert make_case(12344).label == 0

def test_codebooks_are_orthonormal_within_relation():
    for book in codebooks():
        np.testing.assert_allclose(book @ book.T, np.eye(16), atol=1e-12)

def test_event_encoding_is_finite_and_unit_norm():
    vector = event_vector(make_case(12345).events[0], codebooks())
    assert vector.shape == (16,)
    assert np.all(np.isfinite(vector))
    assert np.isclose(np.linalg.norm(vector), 1.0)

@pytest.mark.parametrize("variant", VARIANTS)
def test_variant_is_reproducible(variant):
    a = run_variant(variant, validation_n=24, test_n=24)
    b = run_variant(variant, validation_n=24, test_n=24)
    assert a == b
    assert 0.0 <= a["test"]["accuracy"] <= 1.0
    assert len(a["test"]["accuracy_wilson_95"]) == 2
