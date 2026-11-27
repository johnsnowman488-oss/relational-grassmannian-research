from scripts.aggregate_babi_task11_campaign import _bootstrap_interval, _story_stats


def test_story_cluster_aggregation_uses_evaluator_schema_and_pooled_witness_counts(tmp_path):
    run_root = tmp_path / "seed"
    run_root.mkdir()
    (run_root / "prediction-journal.jsonl").write_text(
        "\\n".join([
            '{"query_id":"q1","story_id":"story-a"}',
            '{"query_id":"q2","story_id":"story-a"}',
            '{"query_id":"q3","story_id":"story-b"}',
        ]) + "\\n",
        encoding="utf-8",
    )
    row = {
        "evaluation": {
            "per_query": [
                {
                    "query_id": "q1", "answer_exact_match": True, "abstained": False,
                    "predicted_witness_lines": [1, 2], "gold_support_lines": [1],
                },
                {
                    "query_id": "q2", "answer_exact_match": False, "abstained": True,
                    "predicted_witness_lines": [], "gold_support_lines": [3, 4],
                },
                {
                    "query_id": "q3", "answer_exact_match": True, "abstained": False,
                    "predicted_witness_lines": [7], "gold_support_lines": [7],
                },
            ],
        },
    }
    stats = _story_stats([row], [run_root])
    assert stats["story-a"]["correct"] == 1
    assert stats["story-a"]["queries"] == 2
    assert stats["story-a"]["covered"] == 1
    assert stats["story-a"]["witness_true"] == 1
    assert stats["story-a"]["support_count"] == 3
    assert stats["story-a"]["false_witness"] == 1
    assert stats["story-a"]["predicted_witness"] == 2
    assert stats["story-b"]["correct"] == 1

    recall = _bootstrap_interval(stats, metric="support_witness_recall", draws=200, seed=1)
    false_rate = _bootstrap_interval(stats, metric="false_witness_rate", draws=200, seed=1)
    assert recall["cluster_unit"] == "whole validation story"
    assert 0.0 <= recall["lower_95"] <= recall["upper_95"] <= 1.0
    assert 0.0 <= false_rate["lower_95"] <= false_rate["upper_95"] <= 1.0
