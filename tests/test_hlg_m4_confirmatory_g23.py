from rgm.experiments.m4_confirmatory_g23 import run_validation_g23


def test_g2_g3_diagnostics_are_validation_only_and_cover_a_b():
    result = run_validation_g23(world_count=3)
    assert result["classification"] == "validation_only_G2_G3_diagnostics_not_confirmatory"
    assert result["confirmatory_test_accessed"] is False
    assert {row["architecture"] for row in result["G2"]["rows"]} == {"A", "B"}
    assert {row["architecture"] for row in result["G3"]["rows"]} == {"A", "B"}
    assert all(row["seed"] >= 30_000 and row["training_world_count"] == 120
               and len(row["training_corpus_sha256"]) == 64
               for group in (result["G2"]["rows"], result["G3"]["rows"])
               for row in group)
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
    assert result["G3"]["thresholds_frozen"] is False
    ambiguous_meta = result["training_corpora"]["heterogeneous_typed_chain"]
    ambiguous_rows = [row for row in result["G3"]["rows"]
                      if row["condition"] == "ambiguous_competing_paths"
                      and row["mode"] == "heterogeneous_typed_chain"]
    normal_rows = [row for row in result["G3"]["rows"]
                   if row["condition"] == "missing_target_edge"
                   and row["mode"] == "heterogeneous_typed_chain"]
    assert all(row["training_corpus_sha256"] == ambiguous_meta["ambiguous_corpus_sha256"]
               for row in ambiguous_rows)
    assert all(row["training_corpus_sha256"] == ambiguous_meta["training_corpus_sha256"]
               for row in normal_rows)
    for architecture in ("A", "B"):
        grid = result["G3"]["validation_threshold_sweep"][architecture]
        assert grid
        assert any(item["meets_validation_separation"] and item["positive_coverage"] == 1.0
                   for item in grid), grid
