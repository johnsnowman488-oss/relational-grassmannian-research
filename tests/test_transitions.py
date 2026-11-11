import numpy as np
import pytest
from rgm.transitions import CategoricalDistribution

def test_probability_distribution_is_valid_and_labelled():
    distribution = CategoricalDistribution(["A", "B", "C"], [0.2, 0.3, 0.5])
    assert distribution.as_dict() == {"A": 0.2, "B": 0.3, "C": 0.5}
    assert distribution.most_likely() == "C"
    assert float(distribution.probabilities.sum()) == pytest.approx(1.0)

def test_scores_are_converted_to_normalized_probabilities():
    distribution = CategoricalDistribution.from_scores([0, 1, 2], [0.0, 1.0, 2.0])
    assert distribution.most_likely() == 2
    assert np.all(distribution.probabilities >= 0.0)
    assert distribution.probabilities.sum() == pytest.approx(1.0)

@pytest.mark.parametrize(
    "labels, probabilities",
    [([], []), (["A"], [0.5]), (["A", "A"], [0.5, 0.5]), (["A", "B"], [-0.1, 1.1]), (["A", "B"], [np.nan, 1.0])],
)
def test_invalid_probabilities_are_rejected(labels, probabilities):
    with pytest.raises(ValueError):
        CategoricalDistribution(labels, probabilities)

def test_invalid_scores_and_temperature_are_rejected():
    with pytest.raises(ValueError):
        CategoricalDistribution.from_scores(["A"], [np.inf])
    with pytest.raises(ValueError):
        CategoricalDistribution.from_scores(["A"], [1.0], temperature=0.0)
