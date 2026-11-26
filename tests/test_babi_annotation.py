import json
from pathlib import Path

import pytest
from types import SimpleNamespace

from rgm.experiments.babi_annotation import (
    _task3_query, _task5_query, _event, parse_source_file, split_fit_stories,
)
from rgm.experiments.babi_structured import (
    StructuredEvent, task3_object_location_before_move, task5_answer_role,
)


def test_task3_query_anchor_is_semantic_and_not_a_gold_support_input():
    events = [
        _event(3, "s", 1, "John picked up the apple."),
        _event(3, "s", 2, "John went to the office."),
        _event(3, "s", 3, "John went to the kitchen."),
    ]
    query = _task3_query("s", 4, "Where was the apple before the kitchen?", events)
    assert query.target_event_id == "s:line000003"
    assert query.object_id == "apple"
    assert not hasattr(query, "gold_answer")
    assert not hasattr(query, "support_event_ids")
    assert task3_object_location_before_move(
        events, object_id="apple", destination_id="kitchen",
        target_event_id=query.target_event_id, observation_cutoff=4,
    ) == "office"


@pytest.mark.parametrize("sentence,expected", [
    ("Mary gave the cake to Fred.", {"giver": "mary", "object": "cake", "recipient": "fred"}),
    ("Fred was given the milk by Bill.", {"giver": "bill", "object": "milk", "recipient": "fred"}),
    ("Mary handed the cake to Fred.", {"giver": "mary", "object": "cake", "recipient": "fred"}),
    ("Mary passed the cake to Fred.", {"giver": "mary", "object": "cake", "recipient": "fred"}),
])
def test_task5_active_and_passive_give_templates(sentence, expected):
    event = _event(5, "s", 1, sentence)
    assert event.event_type == "GIVE"
    assert event.role_map() == expected


@pytest.mark.parametrize("question,answer_role,bound", [
    ("Who gave the cake to Fred?", "giver", {"object": "cake", "recipient": "fred"}),
    ("Who gave the cake?", "giver", {"object": "cake"}),
    ("Who received the cake?", "recipient", {"object": "cake"}),
    ("Who did Fred give the cake to?", "recipient", {"giver": "fred", "object": "cake"}),
    ("What did Fred give to Bill?", "object", {"giver": "fred", "recipient": "bill"}),
    ("What did Jeff receive?", "object", {"recipient": "jeff"}),
])
def test_task5_query_templates(question, answer_role, bound):
    query = _task5_query("s", 4, question)
    assert query.answer_role == answer_role
    assert dict(query.bound_roles) == bound


def test_task5_parses_non_give_story_distractors():
    move = _event(5, "s", 1, "Bill travelled to the office.")
    pickup = _event(5, "s", 2, "Bill picked up the football there.")
    drop = _event(5, "s", 3, "Bill discarded the football there.")
    assert move.event_type == "MOVE"
    assert pickup.role_map()["object"] == "football"
    assert drop.event_type == "DROP"
    assert drop.role_map()["object"] == "football"


def test_task3_target_move_requires_object_holder_not_merely_matching_place():
    events = [
        _event(3, "s", 1, "John picked up the apple."),
        _event(3, "s", 2, "Mary went to the kitchen."),
        _event(3, "s", 3, "John went to the office."),
        _event(3, "s", 4, "John went to the kitchen."),
    ]
    query = _task3_query("s", 5, "Where was the apple before the kitchen?", events)
    assert query.target_event_id == "s:line000004"


def test_parser_separates_model_inputs_from_gold_labels(tmp_path: Path):
    source = tmp_path / "qa5.txt"
    source.write_text(
        "1 Mary gave the cake to Fred.\n"
        "2 Fred gave the cake to Bill.\n"
        "3 Who gave the cake to Fred?\tMary\t1\n",
        encoding="utf-8",
    )
    parsed = parse_source_file(source, task_id=5, split="fit")
    story, labels = parsed[0]
    assert len(story.events) == 2 and len(story.queries) == 1
    assert labels[0]["gold_answer"] == "mary"
    assert labels[0]["support_event_ids"] == ["task5/fit/story000001:line000001"]
    assert not hasattr(story.queries[0], "gold_answer")
    assert not hasattr(story.queries[0], "support_event_ids")


def test_fit_partition_split_is_deterministic_and_story_disjoint():
    stories = [
        (SimpleNamespace(story_id=f"task3/fit/story{i:06d}"), [{"query_id": f"q{i}"}])
        for i in range(12)
    ]
    warm, online = split_fit_stories(stories, task_id=3)
    warm_again, online_again = split_fit_stories(stories, task_id=3)
    assert len(warm) == 8
    assert len(online) == 4
    assert {row[0].story_id for row in warm}.isdisjoint(
        {row[0].story_id for row in online}
    )
    assert [row[0].story_id for row in warm] == [row[0].story_id for row in warm_again]
    assert [row[0].story_id for row in online] == [row[0].story_id for row in online_again]


def test_confirmatory_parser_does_not_read_or_emit_gold_labels(tmp_path: Path):
    source = tmp_path / "qa5_confirmatory.txt"
    source.write_text(
        "1 Mary gave the cake to Fred.\\n"
        "2 Who gave the cake to Fred?\\n",
        encoding="utf-8",
    )
    parsed = parse_source_file(source, task_id=5, split="confirmatory", include_labels=False)
    story, labels = parsed[0]
    assert len(story.queries) == 1
    assert labels == []
    assert not hasattr(story.queries[0], "gold_answer")
    assert not hasattr(story.queries[0], "support_event_ids")


def test_task3_there_adverb_is_not_part_of_object_identity():
    pickup = _event(3, "s", 1, "Mary picked up the football there.")
    drop = _event(3, "s", 2, "Mary dropped the football there.")
    discarded = _event(3, "s", 3, "Sandra discarded the milk there.")
    assert pickup.role_map()["object"] == "football"
    assert drop.role_map()["object"] == "football"
    assert discarded.role_map()["object"] == "milk"


def test_task3_unanchorable_query_fails_closed():
    with pytest.raises(ValueError, match="cannot independently anchor"):
        _task3_query(
            "s", 2, "Where was the apple before the kitchen?",
            [_event(3, "s", 1, "Mary went to the kitchen.")],
        )
