from rgm.experiments.m4_confirmatory_g45 import run_validation_g45


def test_g4_g5_diagnostics_are_validation_only():
    result = run_validation_g45(world_count=2, resource_sizes=(10, 25))
    assert result["classification"] == "validation_only_G4_G5_diagnostics_not_confirmatory"
    assert result["confirmatory_test_accessed"] is False
    assert {row["architecture"] for row in result["G4"]["rows"]} == {"A", "B"}
    assert len(result["G5"]["rows"]) == 4
    assert all(row["serialized_snapshot_bytes"] > 0 for row in result["G5"]["rows"])
    assert all(row["update_latency_ns_p95"] >= row["update_latency_ns_p50"]
               for row in result["G5"]["rows"])
    assert all(row["query_latency_ns_p95"] >= row["query_latency_ns_p50"]
               for row in result["G5"]["rows"])
