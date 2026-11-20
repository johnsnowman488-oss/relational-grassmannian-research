from rgm.experiments.m4_confirmatory_g23 import run_validation_g23


def test_g2_g3_diagnostics_are_validation_only_and_cover_a_b():
    result = run_validation_g23(world_count=3)
    assert result["classification"] == "validation_only_G2_G3_diagnostics_not_confirmatory"
    assert result["confirmatory_test_accessed"] is False
    assert {row["architecture"] for row in result["G2"]["rows"]} == {"A", "B"}
    assert {row["architecture"] for row in result["G3"]["rows"]} == {"A", "B"}
    assert {row["condition"] for row in result["G2"]["rows"]} == {
        "outage_no_replay", "outage_with_replay", "late_arrival"
    }
    assert {row["condition"] for row in result["G3"]["rows"]} == {
        "missing_target_edge", "wrong_context_target",
        "temporal_invalid_target", "multiple_target_witnesses",
        "ambiguous_competing_paths"
    }
    assert all(row["witness_valid"] for row in result["G3"]["rows"]
               if row["status"] == "SELECTED")
    ambiguous = [row for row in result["G3"]["rows"]
                 if row["condition"] == "ambiguous_competing_paths"]
    assert len(ambiguous) == 3 * 2 * 2
    assert all(row["status"] == "ABSTAIN_AMBIGUOUS" for row in ambiguous)
