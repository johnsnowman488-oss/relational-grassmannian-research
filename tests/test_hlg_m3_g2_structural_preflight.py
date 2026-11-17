from rgm.experiments.hlg_m3_g2_structural_preflight import (
    build_structural_preflight_report,
)


def test_current_minimal_integrated_numeric_buffers_exceed_frozen_state_cap():
    report = build_structural_preflight_report()
    lower_bound = report["resource_lower_bound"]

    assert lower_bound["components_bytes"] == {
        "multi_source_ridge_sufficient_statistics_bytes": 504,
        "context_metric_bytes": 32,
        "one_context_slot_mean_and_scatter_bytes": 48,
    }
    assert lower_bound["numeric_buffer_lower_bound_bytes"] == 584
    assert lower_bound["persistent_state_cap_bytes"] == 512
    assert lower_bound["excess_bytes"] == 72
    assert lower_bound["lower_bound_only"] is True
    assert report["status"] == "BLOCKED_CURRENT_MINIMUM_EXCEEDS_FROZEN_STATE_CAP"
    assert report["scientific_benchmark_executed"] is False


def test_context_capacity_pressure_is_reported_without_assuming_all_slots_are_mandatory():
    report = build_structural_preflight_report()
    capacity = report["context_capacity_pressure"]

    assert capacity["distinct_prototype_count"] == 6
    assert capacity["declared_capacity_levels"] == [2, 4, 8]
    assert capacity["can_retain_one_slot_per_prototype"] == {
        "2": False,
        "4": False,
        "8": True,
    }
    assert "not" in capacity["interpretation"]
    assert report["m3_scientific_validation_complete"] is False
