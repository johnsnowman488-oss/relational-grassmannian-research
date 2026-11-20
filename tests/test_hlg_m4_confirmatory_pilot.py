from rgm.experiments.m4_confirmatory_pilot import run_validation_pilot


def test_validation_pilot_never_reads_confirmatory_test_partition():
    result = run_validation_pilot(world_count=6)
    assert result["classification"] == "validation_only_software_pilot_not_confirmatory"
    assert result["partition"] == "validation"
    assert result["confirmatory_test_accessed"] is False
    assert result["training_world_count_per_mode"] == 120
    assert len(result["world_seeds"]) == 6
    assert {row["partition"] for row in result["rows"]} == {"validation"}
    assert {row["architecture"] for row in result["rows"]} == {"A", "B"}
    assert set(result["world_modes"]) == {"heterogeneous_typed_chain", "homogeneous_order_sensitive"}
    assert len(result["rows"]) == 6 * 2 * 2
    assert all(row["partition"] == "validation" for row in result["rows"])
    assert all(row["witness_valid"] for row in result["rows"] if row["status"] == "SELECTED")
