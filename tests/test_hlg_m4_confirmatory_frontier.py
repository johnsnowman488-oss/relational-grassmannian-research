from rgm.experiments.m4_confirmatory_frontier import (\n    run_validation_frontier, _select_frontier_partition,\n)\nfrom rgm.experiments.m4_confirmatory_worlds import default_partitions


def test_memory_budgeted_frontier_is_validation_only_and_pairs_a_b():
    result = run_validation_frontier(world_count=3, capacities=(10, 1000))
    assert result["classification"] == "validation_only_memory_budgeted_frontier_not_confirmatory"
    assert result["confirmatory_test_accessed"] is False
    assert result["partition"] == "validation_heldout_half"
    assert len(result["world_seeds"]) == 3
    assert result["A_no_replay"]["correct"] == 0
    assert result["A_with_external_replay"]["correct"] == 3
    assert len(result["frontier"]) == 2
    assert all(row["A_within_same_upper_bound_budget"] for row in result["frontier"])
    assert result["frontier"][-1]["B_correct_retention"] == 3
    assert all(row["B_false_selections"] == 0 for row in result["frontier"])


def test_test_partition_frontier_requires_confirmatory_runner_authorization():
    import pytest

    with pytest.raises(ValueError, match="frozen confirmatory campaign runner"):
        run_validation_frontier(
            world_count=1, capacities=(10,), partition_name="test",
        )


def test_confirmatory_selector_maps_to_frozen_partition_name():
    partitions = default_partitions()
    selected = _select_frontier_partition(partitions, "test")
    assert selected.name == "confirmatory_test"
    assert selected.seeds[0] == 70000
    assert selected.seeds[-1] == 70119
