from rgm.experiments.m4_confirmatory_pilot import run_validation_pilot


def test_validation_pilot_never_reads_confirmatory_test_partition():
    result = run_validation_pilot(world_count=6)
    assert result["classification"] == "validation_only_software_pilot_not_confirmatory"
    assert result["partition"] == "validation"
    assert result["confirmatory_test_accessed"] is False
    assert len(result["world_seeds"]) == 6
    assert {row["partition"] for row in result["rows"]} == {"validation"}
    assert {row["architecture"] for row in result["rows"]} == {"A", "B"}
    assert all(row["witness_valid"] for row in result["rows"] if row["status"] == "SELECTED")
