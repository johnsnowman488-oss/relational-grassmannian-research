from rgm.experiments.h1_hierarchical_campaign import (
    load_frozen_partitions,
    _paired_bootstrap,
)


def test_h1_hierarchical_partitions_are_frozen_disjoint_and_separate_from_flat_ab():
    config, partitions, config_sha = load_frozen_partitions()
    assert len(config_sha) == 64
    assert len(partitions["train"].seeds) == 120
    assert len(partitions["validation"].seeds) == 60
    assert len(partitions["confirmatory_test"].seeds) == 120
    train = set(partitions["train"].seeds)
    validation = set(partitions["validation"].seeds)
    confirmatory = set(partitions["confirmatory_test"].seeds)
    assert train.isdisjoint(validation)
    assert train.isdisjoint(confirmatory)
    assert validation.isdisjoint(confirmatory)
    assert config["confirmatory_test_accessed"] is False
    assert config["prior_partition_separation"]["overlap_with_new_partitions"] is False
    assert config["confirmatory_authorized"] is True


def test_h1_paired_bootstrap_clusters_two_task_modes_by_world_seed():
    rows = []
    for seed in range(10):
        for mode in ("heterogeneous_typed_chain", "homogeneous_order_sensitive"):
            rows.extend([
                {"seed": seed, "mode": mode, "architecture": "HLA", "correct": 0.0},
                {"seed": seed, "mode": mode, "architecture": "HLB", "correct": 1.0},
            ])
    result = _paired_bootstrap(rows, "correct", condition=None)
    assert result["paired_world_seeds"] == 10
    assert result["mean_HLB_minus_HLA"] == 1.0
    assert result["ci95_world_cluster_bootstrap"] == [1.0, 1.0]
