from pathlib import Path

import pytest

from rgm.experiments.babi_expansion_adapters import (
    ExpansionQuery, ExpansionStory, Task11MentionEvent, parse_expansion_source,
)
from rgm.experiments.babi_expansion_baselines import (
    breadth_first_search_task19, direct_edge_only_task19,
    evaluate_baselines, lexical_temporal_cue_task14,
    predict_task11_supervision, recency_only_task11, source_order_only_task14,
)


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_task11_nearest_compatible_baseline_runs_after_raw_parser(tmp_path):
    source = write(tmp_path, "task11.txt",
        "1 Mary went to the kitchen.\n"
        "2 Sandra went to the garden.\n"
        "3 After that she went to the office.\n"
        "4 Where is Mary? \tkitchen\t1\n")
    stories, labels = parse_expansion_source(source, task_id=11, split="validation")
    story, query = stories[0], stories[0].queries[0]
    nearest = __import__("rgm.experiments.babi_expansion_adapters", fromlist=["predict_task11"]).predict_task11(story, query)
    recent = recency_only_task11(story, query)
    assert nearest.answer == "kitchen"
    assert recent.answer == "office"
    scored = evaluate_baselines(stories, labels, evaluate_labels=True)
    assert scored["task_results"]["11"]["nearest-compatible-antecedent"]["target_metrics"]["status"] == "NOT_AVAILABLE"
    assert not hasattr(story.events[2], "antecedent_event_id")
    assert labels[0].answer == "kitchen"


def test_task14_source_order_and_temporal_cue_are_distinct(tmp_path):
    source = write(tmp_path, "task14.txt",
        "1 Yesterday Julie went to the office.\n"
        "2 This evening Julie went to the school.\n"
        "3 This morning Julie went to the library.\n"
        "4 Where was Julie before the school? \tlibrary\t1 2 3\n")
    stories, labels = parse_expansion_source(source, task_id=14, split="validation")
    story, query = stories[0], stories[0].queries[0]
    assert source_order_only_task14(story, query).answer == "office"
    assert lexical_temporal_cue_task14(story, query).answer == "library"
    scored = evaluate_baselines(stories, labels, evaluate_labels=True)
    lexical_metrics = scored["task_results"]["14"]["lexical-temporal-cue-rule"]
    assert lexical_metrics["answer_exact_match"] == 1.0
    assert lexical_metrics["target_metrics"]["temporal_relation_exact_match"] == 1.0
    assert lexical_metrics["target_metrics"]["f1"] == 1.0
    assert scored["task_results"]["14"]["source-order-only"]["target_metrics"]["f1"] < 1.0


def test_task19_direct_edge_and_bfs_have_distinct_coverage(tmp_path):
    source = write(tmp_path, "task19.txt",
        "1 The hallway is east of the kitchen.\n"
        "2 The garden is north of the hallway.\n"
        "3 How do you go from the kitchen to the garden?\te,n\t1 2\n")
    stories, labels = parse_expansion_source(source, task_id=19, split="validation")
    story, query = stories[0], stories[0].queries[0]
    direct = direct_edge_only_task19(story, query)
    bfs = breadth_first_search_task19(story, query)
    assert direct.abstained
    assert bfs.answer == "e,n"
    scored = evaluate_baselines(stories, labels, evaluate_labels=True)
    bfs_metrics = scored["task_results"]["19"]["breadth-first-search"]
    assert bfs_metrics["answer_exact_match"] == 1.0
    assert bfs_metrics["target_metrics"]["f1"] == 1.0
    assert bfs_metrics["target_metrics"]["ordered_path_exact_match"] == 1.0
    assert bfs_metrics["target_metrics"]["target_exact_match"] == 1.0


def test_predictors_receive_no_evaluator_fields(tmp_path):
    source = write(tmp_path, "task11.txt",
        "1 Mary went to the kitchen.\n"
        "2 Where is Mary? \tkitchen\t1\n")
    stories, labels = parse_expansion_source(source, task_id=11, split="validation")
    assert stories[0].queries[0].__dataclass_fields__.keys() >= {"query_id", "task_id", "observed_at"}
    assert not hasattr(stories[0].queries[0], "answer")
    assert not hasattr(stories[0].queries[0], "support_line_numbers")
    assert labels[0].query_id == stories[0].queries[0].query_id


def test_task11_target_supervision_abstains_on_ambiguous_antecedents():
    story = ExpansionStory("task11/validation/ambiguous", 11, (
        Task11MentionEvent("mary", "mary", False, "kitchen", 1, "train#1", "female"),
        Task11MentionEvent("sandra", "sandra", False, "garden", 2, "train#2", "female"),
        Task11MentionEvent("pronoun", "she", True, "office", 3, "train#3", "female"),
    ), ())
    query = ExpansionQuery("query", 11, 4, "train#4", entity="mary")
    with pytest.raises(RuntimeError, match="abstains on ambiguous mentions"):
        predict_task11_supervision(story, query)
