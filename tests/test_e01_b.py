import numpy as np

from rgm.experiments.e01_b import (
    CONDITIONS, MEMORY_ARMS, WORLD_SEEDS, _path_exists, codebooks, make_case, run,
)
from rgm.experiments.e01_b_analysis import _paired_world


def test_fixed_dimension_codebooks_expand_and_become_nonorthogonal():
    small = codebooks(4)
    large = codebooks(8)
    assert small[0].shape == (16, 16)
    assert large[0].shape == (64, 16)
    np.testing.assert_allclose(np.linalg.norm(large[0], axis=1), 1.0)
    gram = large[0] @ large[0].T
    assert not np.allclose(gram, np.eye(64))


def test_four_entity_codebook_is_canonical_and_repeatedly_deterministic():
    first = codebooks(4)
    second = codebooks(4)
    np.testing.assert_array_equal(first[0], second[0])
    np.testing.assert_array_equal(first[1], second[1])
    gram = first[1] @ first[1].T
    np.testing.assert_allclose(gram, np.eye(16), atol=1e-12)


def test_supports_remove_positive_roundoff_at_orthogonal_codewords():
    from rgm.experiments.e01_b import _support_tensors

    books = codebooks(4)
    channels = books[1][:2]
    supports = _support_tensors(channels, books, entities=4)
    assert np.count_nonzero(supports[1][0]) == 1
    assert supports[1][0, 0, 0] == 1.0


def test_generator_preserves_positive_and_negative_path_labels():
    positive = make_case(401, entities=4, fact_count=8, distractors=4, depth=2, gap="medium")
    negative = make_case(402, entities=4, fact_count=8, distractors=4, depth=2, gap="medium")
    assert positive.label == 1
    assert negative.label == 0
    assert _path_exists(set(positive.facts), positive.query_subject, positive.query_object, 2)
    assert not _path_exists(set(negative.facts), negative.query_subject, negative.query_object, 2)
    assert len(positive.events) == 12
    assert len(negative.events) == 12


def test_generator_supports_three_hop_paths_and_large_fact_sets():
    case = make_case(403, entities=16, fact_count=64, distractors=32, depth=3, gap="long")
    assert case.label == 1
    assert case.planted_path is not None
    assert len(case.planted_path) == 4
    assert len(case.facts) == 64
    assert len(case.events) == 96


def test_e01_b_run_records_capacity_and_frontier_metrics():
    small = run("entity_e4", "slow_only", world_seed=401, n=20)
    large = run("facts_f16", "full_soe", world_seed=402, n=20)
    assert small["sample_counts"]["test"] == 20
    assert small["parameters"]["state_scalar_count"] == 16
    assert large["parameters"]["state_scalar_count"] == 64
    assert len(small["per_sequence"]) == 20
    assert "constituent_retrieval" in small
    assert "composition" in small


def test_e01_b_frontier_matrix_is_frozen():
    assert len(CONDITIONS) == 19
    assert len(MEMORY_ARMS) == 6
    assert len(WORLD_SEEDS) == 2
    assert len(CONDITIONS) * len(MEMORY_ARMS) * len(WORLD_SEEDS) == 228


def test_paired_world_comparison_uses_matching_case_ids():
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
    result = _paired_world(baseline, comparison)
    assert result["n_paired_sequences"] == 4
    assert result["discordant_pairs"] == 3
    assert result["accuracy_difference"] == 0.25
