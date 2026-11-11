import numpy as np

from rgm.experiments.e01 import codebooks
from rgm.experiments.e01_a3 import (
    CODEBOOK_SEEDS, CONFIGURATIONS, WORLD_SEEDS, run,
)


def test_codebook_seed_is_reproducible_and_changes_relation_one_basis():
    a = codebooks(seed=27183)
    b = codebooks(seed=27183)
    c = codebooks(seed=65537)
    np.testing.assert_array_equal(a[0], b[0])
    np.testing.assert_array_equal(a[1], b[1])
    np.testing.assert_array_equal(a[0], c[0])
    assert not np.allclose(a[1], c[1])


def test_e01_a3_cell_records_seeded_world_and_codebook():
    result = run("full_max", world_seed=101, codebook_seed=9137, n=20)
    assert result["experiment"] == "E01-A3"
    assert result["world_seed"] == 101
    assert result["codebook_seed"] == 9137
    assert len(result["per_sequence"]) == 20
    assert result["per_sequence"][0]["candidate_facts"]
    assert result["per_sequence"][0]["composition_prediction"] in (0, 1)


def test_e01_a3_world_seed_changes_the_synthetic_cases():
    a = run("full_max", world_seed=101, codebook_seed=9137, n=20)
    b = run("full_max", world_seed=202, codebook_seed=9137, n=20)
    assert a["seed_ranges"]["test"] != b["seed_ranges"]["test"]
    assert a["per_sequence"][0]["events"] != b["per_sequence"][0]["events"]


def test_replication_matrix_is_frozen_at_six_configurations_nine_pairs():
    assert len(CONFIGURATIONS) == 6
    assert len(WORLD_SEEDS) == 3
    assert len(CODEBOOK_SEEDS) == 3
    assert len(CONFIGURATIONS) * len(WORLD_SEEDS) * len(CODEBOOK_SEEDS) == 54
