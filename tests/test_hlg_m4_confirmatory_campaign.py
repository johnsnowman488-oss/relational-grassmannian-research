from rgm.experiments.m4_confirmatory_campaign import (
    _load_config, _partitions, _paired_bootstrap,
)


def test_frozen_confirmatory_config_has_disjoint_sealed_partitions():
    config, digest = _load_config()
    partitions = _partitions(config)
    assert len(digest) == 64
    assert len(partitions["train"].seeds) == 120
    assert len(partitions["validation"].seeds) == 60
    assert len(partitions["confirmatory_test"].seeds) == 120
    assert set(partitions["train"].seeds).isdisjoint(partitions["validation"].seeds)
    assert set(partitions["train"].seeds).isdisjoint(partitions["confirmatory_test"].seeds)
    assert set(partitions["validation"].seeds).isdisjoint(partitions["confirmatory_test"].seeds)
    assert config["confirmatory_test_accessed"] is False
    assert config["readout"]["min_probability"] == 0.75
    assert config["readout"]["min_margin"] == 0.25


def test_paired_bootstrap_uses_world_seed_as_cluster_unit():
    rows = []
    for seed in range(10):
        rows.extend([
            {"seed": seed, "architecture": "A", "correct": 0.0},
            {"seed": seed, "architecture": "B", "correct": 1.0},
        ])
    result = _paired_bootstrap(rows, "correct", resamples=250)
    assert result["available"]
    assert result["n_paired_worlds"] == 10
    assert result["mean_B_minus_A"] == 1.0
    assert result["ci95_world_cluster_bootstrap"] == [1.0, 1.0]
