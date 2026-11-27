from __future__ import annotations

from pathlib import Path

import pytest

from rgm.experiments.babi_expansion_adapters import (
    AmbiguousPathError,
    parse_expansion_source,
    predict_task11,
    predict_task14,
    predict_task19,
)


def write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def test_task11_resolves_singular_pronoun_and_keeps_gold_separate(tmp_path):
    path = write(
        tmp_path, "task11.txt",
        "1 Mary went back to the bathroom.\n"
        "2 After that she went to the bedroom.\n"
        "3 Where is Mary? \tbedroom\t1 2\n"
        "1 John went to the garden.\n"
        "2 Following that he went to the office.\n"
        "3 Where is John? \toffice\t1 2\n",
    )
    stories, labels = parse_expansion_source(path, task_id=11, split="train")
    assert len(stories) == 2
    assert len(labels) == 2
    first = stories[0]
    assert first.events[1].actor_entity == "mary"
    assert first.events[1].is_pronoun is True
    assert first.events[1].antecedent_event_id == first.events[0].event_id
    prediction = predict_task11(first, first.queries[0])
    assert prediction.answer == "bedroom"
    assert prediction.witness_event_ids == tuple(event.event_id for event in first.events)
    assert labels[0].answer == "bedroom"
    # The label-free path parses exactly the same input without retaining labels.
    unlabeled, no_labels = parse_expansion_source(
        path, task_id=11, split="train", include_labels=False
    )
    assert no_labels == []
    assert unlabeled == stories


def test_task11_does_not_bind_pronoun_across_story_boundary(tmp_path):
    path = write(
        tmp_path, "task11_bad.txt",
        "1 Mary went to the kitchen.\n"
        "1 After that she went to the office.\n"
    )
    with pytest.raises(ValueError, match="unresolved singular pronoun"):
        parse_expansion_source(path, task_id=11, split="train")


def test_task14_uses_event_time_not_source_line_order(tmp_path):
    path = write(
        tmp_path, "task14.txt",
        "1 Bill went back to the cinema yesterday.\n"
        "2 Julie went to the school this morning.\n"
        "3 Fred went to the park yesterday.\n"
        "4 Yesterday Julie went to the office.\n"
        "5 Where was Julie before the school? \toffice\t2 4\n"
    )
    stories, labels = parse_expansion_source(path, task_id=14, split="train")
    prediction = predict_task14(stories[0], stories[0].queries[0])
    assert prediction.answer == "office"
    assert len(prediction.witness_event_ids) == 2
    assert prediction.witness_event_ids == (
        stories[0].events[3].event_id, stories[0].events[1].event_id
    )
    assert labels[0].support_line_numbers == (2, 4)


def test_task14_abstains_when_temporal_predecessor_is_missing(tmp_path):
    path = write(
        tmp_path, "task14_incomplete.txt",
        "1 This morning Julie went to the school.\n"
        "2 Where was Julie before the school? \tschool\t1\n"
    )
    stories, _ = parse_expansion_source(path, task_id=14, split="train")
    prediction = predict_task14(stories[0], stories[0].queries[0])
    assert prediction.abstained is True
    assert prediction.reason == "no_prior_temporal_location"


def test_task19_composes_oriented_edges_in_order(tmp_path):
    path = write(
        tmp_path, "task19.txt",
        "1 The office is east of the hallway.\n"
        "2 The kitchen is north of the office.\n"
        "3 The garden is west of the bedroom.\n"
        "4 The office is west of the garden.\n"
        "5 The bathroom is north of the garden.\n"
        "6 How do you go from the kitchen to the garden?\ts,e\t2 4\n"
    )
    stories, labels = parse_expansion_source(path, task_id=19, split="train")
    prediction = predict_task19(stories[0], stories[0].queries[0])
    assert prediction.answer == "s,e"
    assert len(prediction.witness_event_ids) == 2
    assert labels[0].answer == "s,e"


def test_task19_inverse_edge_is_explicit_and_no_path_abstains(tmp_path):
    path = write(
        tmp_path, "task19_inverse.txt",
        "1 The office is east of the hallway.\n"
        "2 How do you go from the office to the hallway?\tw\t1\n"
    )
    stories, _ = parse_expansion_source(path, task_id=19, split="train")
    prediction = predict_task19(stories[0], stories[0].queries[0])
    assert prediction.answer == "w"

    disconnected = write(
        tmp_path, "task19_disconnected.txt",
        "1 The office is east of the hallway.\n"
        "2 How do you go from the garden to the kitchen?\tn\t1\n"
    )
    stories, _ = parse_expansion_source(disconnected, task_id=19, split="train")
    prediction = predict_task19(stories[0], stories[0].queries[0])
    assert prediction.abstained is True
    assert prediction.reason == "no_observed_path"


def test_task19_ambiguous_shortest_paths_abstain(tmp_path):
    path = write(
        tmp_path, "task19_ambiguous.txt",
        "1 The garden is north of the hallway.\n"
        "2 The kitchen is east of the hallway.\n"
        "3 The office is east of the garden.\n"
        "4 The office is north of the kitchen.\n"
        "5 How do you go from the hallway to the office?\tn,e\t1 3\n"
    )
    stories, _ = parse_expansion_source(path, task_id=19, split="train")
    prediction = predict_task19(stories[0], stories[0].queries[0])
    assert prediction.abstained is True
    assert prediction.reason == "ambiguous_shortest_paths"


def test_task_adapters_reject_cross_task_inputs(tmp_path):
    path = write(tmp_path, "task11.txt", "1 Mary went to the kitchen.\n2 Where is Mary? \tkitchen\t1\n")
    stories, _ = parse_expansion_source(path, task_id=11, split="train")
    with pytest.raises(ValueError, match="another task"):
        predict_task14(stories[0], stories[0].queries[0])
