from rgm.experiments.hlg_m3_benchmark_contract import build_manifest
from rgm.experiments.hlg_m3_g2_confirmatory import _cluster_ci, _new_bundle, _run_stream


def test_cluster_interval_uses_world_cluster_values():
    result = _cluster_ci([0.1, 0.2, -0.1, 0.3])
    assert result["worlds"] == 4
    assert result["positive_worlds"] == 3
    assert result["ci95_lower"] <= result["mean"] <= result["ci95_upper"]


def test_confirmatory_stream_runs_prequentially_with_all_controls():
    manifest = build_manifest()
    world = next(
        item for item in manifest["worlds"]
        if item["split"] == "development_fit"
    )
    bundle = _new_bundle(world["factor_profile"]["context_bank_capacity"])
    row = _run_stream(world, world["replicate_seeds"][0], bundle)
    assert row["step_count"] > 200
    assert row["m3_observed_targets"] > 0
    assert row["m3_loss"] is not None
    assert set(row["control_losses"]) == {"C0", "C1", "C2", "C3", "C4"}
    assert all(value is not None for value in row["control_losses"].values())
    assert row["stream_sha256"]
