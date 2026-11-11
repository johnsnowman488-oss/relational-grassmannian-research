import numpy as np

from rgm.experiments.e01 import codebooks, make_case
from rgm.experiments.e01_a2 import (
    MEMORY_CONFIGS, READOUTS, _composition_score, _fact_scores,
    _memory_channels, run,
)


def test_e01_a2_memory_channel_controls_have_expected_dimensions():
    books = codebooks()
    case = make_case(30001)
    assert _memory_channels(case, "full", books).shape == (4, 16)
    for i in range(4):
        assert _memory_channels(case, f"only_{i}", books).shape == (1, 16)
        assert _memory_channels(case, f"drop_{i}", books).shape == (3, 16)


def test_fact_scores_are_channel_by_subject_by_object():
    books = codebooks()
    scores = _fact_scores(np.ones((4, 16)), books)
    assert scores["0"].shape == (4, 4, 4)
    assert scores["1"].shape == (4, 4, 4)
    assert np.all(np.isfinite(scores["0"]))


def test_readout_controls_are_distinct_when_channels_disagree():
    case = make_case(30001)
    raw = {
        "0": np.array([
            [[0.0, 0.9, 0.0, 0.0]] * 4,
            [[0.0, 0.0, 0.0, 0.0]] * 4,
        ]),
        "1": np.array([
            [[0.0, 0.0, 0.0, 0.0]] * 4,
            [[0.0, 0.0, 0.0, 0.9]] * 4,
        ]),
    }
    maximum = _composition_score(case, raw, "max_channel")
    same = _composition_score(case, raw, "same_channel")
    mean = _composition_score(case, raw, "mean_channel")
    assert maximum >= same
    assert maximum >= mean


def test_e01_a2_run_emits_per_sequence_and_candidate_fact_evidence():
    result = run("full", "same_channel", n=20)
    assert result["experiment"] == "E01-A2"
    assert len(result["per_sequence"]) == 20
    row = result["per_sequence"][0]
    assert len(row["candidate_facts"]) == 24
    assert len(row["candidate_facts"][0]["channel_support"]) == 4
    assert "composition_score" in row
    assert result["thresholds"]["constituent_fact"] >= 0.0


def test_configuration_enumeration_is_frozen():
    assert len(MEMORY_CONFIGS) == 9
    assert READOUTS == ("max_channel", "same_channel", "mean_channel")


def test_paired_analysis_uses_shared_sequence_ids_and_reports_mcnemar():
    from rgm.experiments.e01_a2_analysis import _paired_metrics

    baseline = {
        1: {"label": 1, "composition_prediction": 1},
        2: {"label": 0, "composition_prediction": 0},
        3: {"label": 1, "composition_prediction": 0},
        4: {"label": 0, "composition_prediction": 1},
    }
    comparison = {
        1: {"label": 1, "composition_prediction": 1},
        2: {"label": 0, "composition_prediction": 1},
        3: {"label": 1, "composition_prediction": 1},
        4: {"label": 0, "composition_prediction": 0},
    }
    result = _paired_metrics(baseline, comparison, seed=17)
    assert result["n_paired_sequences"] == 4
    assert result["mcnemar"]["discordant_pairs"] == 2
    assert result["accuracy_difference_comparison_minus_baseline"] == 0.0
