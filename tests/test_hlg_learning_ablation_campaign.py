from rgm.experiments.h1_learning_ablations import run_learning_ablation_campaign


def test_matched_learning_ablation_campaign_isolates_all_four_update_channels():
    result = run_learning_ablation_campaign()
    assert result["acceptance"] == "PASS"
    assert len(result["rows"]) == 6
    by_name = {row["variant"]: row for row in result["rows"]}
    assert by_name["full"]["relation_online_updates"] == 1
    assert by_name["without_relational"]["relation_online_updates"] == 0
    assert by_name["without_abstraction"]["event_role_online_updates"] == 0
    assert by_name["without_temporal"]["temporal_parameter_updates"] == 0
    assert by_name["without_task"]["task_outcome_updates"] == 0
    assert by_name["without_temporal"]["level0_feature_updates"] == 0
    assert by_name["without_abstraction"]["context_transition_online_updates"] == 0
    assert by_name["no_learning"]["relation_online_updates"] == 0
