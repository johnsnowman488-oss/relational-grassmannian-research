from pathlib import Path

import numpy as np

from rgm.experiments.hlg_m3_g2_readiness import build_readiness_report
from rgm.leptograph.m3.controls import MemoryArchitecture
from rgm.leptograph.m3.estimation import MultiSourceRidge


ROOT = Path(__file__).resolve().parents[1]


def test_masked_source_update_keeps_absent_block_out_of_sufficient_statistics():
    model = MultiSourceRidge({"a": 1, "b": 1}, 0, 1, ridge=1e-6)
    sources = {"a": np.array([2.0]), "b": np.array([0.0])}
    model.update(sources, [], [1.0], source_gates={"a": 1.0, "b": 0.0})

    absent = model._source_slices["b"]
    assert np.all(model.gram[absent, :] == 0.0)
    assert np.all(model.gram[:, absent] == 0.0)
    assert np.all(model.cross[absent, :] == 0.0)

    contributions = model.marginal_loss_contributions(
        sources, [], [1.0], source_gates={"a": 1.0, "b": 0.0}
    )
    assert contributions["b"] == 0.0


def test_g2_readiness_audit_fails_closed_on_missing_confirmatory_interfaces():
    report = build_readiness_report(ROOT)
    blockers = {item["id"] for item in report["blockers"]}

    assert report["g1"]["accepted"] is True
    assert report["g1"]["manifest_identity_matches"] is True
    assert report["g1"]["manifest_validation_passed"] is True
    assert report["g1"]["world_configuration_count"] == 40
    assert report["g1"]["replicate_stream_count"] == 200
    assert report["observed_interfaces"]["masked_online_update_available"] is True
    assert report["scientific_benchmark_executed"] is False
    assert report["m3_scientific_validation_complete"] is False

    assert "masked_online_update_missing" not in blockers
    assert "g2_confirmatory_runner_missing" in blockers
    assert "c0_c4_task_prediction_adapter_missing" not in blockers
    assert "integrated_candidate_resource_ledger_missing" in blockers
    assert "current_candidate_exceeds_frozen_persistent_state_cap" not in blockers
    assert "candidate_lifecycle_contract_missing" not in blockers
    assert "candidate_lifecycle_campaign_integration_missing" in blockers
    assert report["observed_interfaces"]["candidate_lifecycle_api_available"] is True
    assert "context_conditioned_relation_store_missing" in blockers
    assert report["observed_interfaces"]["context_conditioned_methods"] == {
        "context_slot_operator_lookup": False,
        "context_conditioned_prediction": False,
    }
    assert report["observed_interfaces"]["structural_preflight"]["resource_lower_bound"]["numeric_buffer_lower_bound_bytes"] == 416
    assert report["observed_interfaces"]["structural_preflight"]["resource_lower_bound"]["persistent_state_cap_bytes"] == 512
    assert report["ready_to_start_g2"] is False
    assert report["readiness_status"] == "BLOCKED_G2_NOT_STARTED"


def test_c0_c4_controls_expose_common_task_prediction_api():
    assert hasattr(MemoryArchitecture, "read_mode")
    assert hasattr(MemoryArchitecture, "read_relation")
    assert hasattr(MemoryArchitecture, "resource_snapshot")
    assert hasattr(MemoryArchitecture, "predict")
    assert hasattr(MemoryArchitecture, "update_target")
    assert hasattr(MemoryArchitecture, "score_target")
