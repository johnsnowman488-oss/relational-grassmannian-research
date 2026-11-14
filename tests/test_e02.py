import json

from rgm.experiments.e01_b import make_case
from rgm.experiments.e02 import (
    CODEBOOK_SEEDS, CONDITIONS, CORRUPTION_PROFILES, FORBIDDEN_MODEL_KEYS,
    MEMORY_ARMS, WORLD_SEEDS, ModelInput, _corrupt_input, _to_pair_with_entities,
    build_event_graph, graph_query, run_b, run_c, run_contract,
)


def _pair(seed=7_700_001, condition="baseline_e4"):
    params = CONDITIONS[condition]
    case = make_case(
        seed, entities=params["entities"], fact_count=params["facts"],
        distractors=params["distractors"], depth=params["depth"], gap=params["gap"],
    )
    return _to_pair_with_entities(case, params["entities"], params["depth"])


def test_e02_frozen_design_reuses_six_e01_c_conditions_and_seed_sets():
    assert len(CONDITIONS) == 6
    assert MEMORY_ARMS == ("slow_only", "full_history")
    assert len(WORLD_SEEDS) == len(CODEBOOK_SEEDS) == 3
    assert set(CORRUPTION_PROFILES) == {"clean", "missing_10", "spurious_10", "mixed_10"}


def test_model_input_contract_excludes_evaluator_truth_and_hash_is_stable():
    model_input, truth = _pair()
    payload = model_input.to_payload()
    assert isinstance(model_input, ModelInput)
    assert not (set(payload) & FORBIDDEN_MODEL_KEYS)
    assert "facts" not in json.dumps(payload)
    assert "label" not in json.dumps(payload)
    assert len(model_input.input_sha256) == 64
    assert model_input.input_sha256 == model_input.input_sha256
    # Generator seed parity determines the synthetic label; never expose it.
    assert isinstance(model_input.case_id, str)
    assert model_input.case_id != "7700001"
    assert len(model_input.case_id) == 24
    assert truth.label in (0, 1)


def test_event_graph_is_built_from_observations_and_tracks_repeated_events():
    model_input, _ = _pair(seed=7_700_001, condition="repeat_e4")
    graph = build_event_graph(model_input)
    assert len(graph.event_store.events) == len(model_input.events)
    assert graph.edge_set
    assert sum(x["occurrence_count"] for x in graph.edge_records) == len(model_input.events)
    assert any(x["occurrence_count"] > 1 for x in graph.edge_records)
    prediction, _, operations = graph_query(model_input, graph)
    assert isinstance(prediction, bool)
    assert operations >= 0


def test_clean_graph_path_query_matches_generator_label():
    positive_input, positive_truth = _pair(seed=7_700_001, condition="baseline_e4")
    negative_input, negative_truth = _pair(seed=7_700_002, condition="baseline_e4")
    positive, _, _ = graph_query(positive_input, build_event_graph(positive_input))
    negative, _, _ = graph_query(negative_input, build_event_graph(negative_input))
    assert positive == bool(positive_truth.label)
    assert negative == bool(negative_truth.label)


def test_corruption_is_reproducible_and_audit_is_not_in_model_payload():
    model_input, truth = _pair(seed=7_700_003, condition="candidate_e16")
    first, audit_a = _corrupt_input(model_input, truth, "candidate_e16", "mixed_10", salt=42)
    second, audit_b = _corrupt_input(model_input, truth, "candidate_e16", "mixed_10", salt=42)
    assert first.input_sha256 == second.input_sha256
    assert audit_a == audit_b
    assert audit_a["removed_unique_edge_count"] > 0
    assert audit_a["added_spurious_edge_count"] > 0
    assert not (set(first.to_payload()) & {"corruption_audit", "corruption_mask", "truth", "facts"})
    assert set(tuple(x) for x in audit_a["added_edges"]).isdisjoint(truth.facts)


def test_e02_a_contract_receipt_passes():
    result = run_contract()
    assert result["status"] == "passed"
    assert result["forbidden_fields_found"] == []
    assert result["evaluator_truth_stored_separately"] is True


def test_e02_b_smoke_run_emits_paired_architecture_metrics():
    result = run_b("baseline_e4", 501, 9137, n=20)
    assert result["stage"] == "E02-B"
    assert set(result["architectures"]) == {"graph", "memory_slow_only", "memory_full_history"}
    assert result["architectures"]["graph"]["metrics"]["accuracy"] == 1.0
    assert len(result["per_sequence"]) == 20
    assert result["contract"]["thresholds_fit_on_validation_only"] is True


def test_e02_c_smoke_run_emits_all_corruption_and_hybrid_arms():
    result = run_c("baseline_e4", 501, 9137, n=20)
    assert result["stage"] == "E02-C"
    assert set(result["profiles"]) == set(CORRUPTION_PROFILES)
    for profile in CORRUPTION_PROFILES:
        architectures = result["profiles"][profile]["architectures"]
        assert set(architectures) == {
            "graph", "memory_slow_only", "memory_full_history",
            "hybrid_slow_only", "hybrid_full_history",
        }
        assert len(result["profiles"][profile]["per_sequence"]) == 20


def test_provisional_model_input_keeps_minimum_entity_domain():
    from rgm.experiments.e02 import _to_pair
    case = make_case(7_700_001, entities=4, fact_count=8, distractors=0, depth=2, gap="medium")
    model_input, _ = _to_pair(case, 2)
    assert model_input.entity_count == 4


def test_contract_receipt_does_not_publish_evaluator_label():
    result = run_contract()
    assert "truth_label_for_contract_check_only" not in result


def test_e02_summary_aggregates_full_metrics_and_storage_costs():
    from rgm.experiments.e02_analysis import _aggregate_architecture

    def cell(accuracy, state_bytes):
        metrics = {
            "accuracy": accuracy, "balanced_accuracy": accuracy,
            "precision": accuracy, "recall": accuracy,
            "false_positive_rate": 1.0 - accuracy,
            "false_negative_rate": 1.0 - accuracy,
        }
        cost = {
            "mean_model_state_bytes": state_bytes,
            "mean_common_input_bytes": 500.0,
            "mean_query_edge_evaluations": 8.0,
            "mean_observed_event_count": 8.0,
            "mean_unique_observed_edges": 8.0,
        }
        return {"architectures": {"graph": {"metrics": metrics, "cost": cost}}}

    summary = _aggregate_architecture([cell(1.0, 700.0), cell(0.8, 900.0)], "graph")
    assert summary["metrics"]["accuracy"]["mean"] == 0.9
    assert summary["metrics"]["balanced_accuracy"]["n_cells"] == 2
    assert summary["cost"]["mean_model_state_bytes"]["mean"] == 800.0
    assert summary["cost"]["mean_common_input_bytes"]["mean"] == 500.0
