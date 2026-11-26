import pytest

from rgm.experiments.babi_structured import (
    StructuredEvent, StructuredQuery, StructuredStory, task3_object_location_before_move, task5_answer_role,
)


def ev(event_id, kind, roles, order, observed=None):
    return StructuredEvent(event_id, kind, tuple(roles.items()), order,
                           order if observed is None else observed, f"source-line:{event_id}")


def test_task3_three_supporting_fact_temporal_object_state_fixture():
    story = [
        ev("1", "PICK_UP", {"actor": "john", "object": "apple"}, 1),
        ev("2", "MOVE", {"actor": "john", "destination": "office"}, 2),
        ev("3", "MOVE", {"actor": "john", "destination": "kitchen"}, 3),
        ev("4", "DROP", {"actor": "john", "object": "apple"}, 4),
    ]
    assert task3_object_location_before_move(
        story, object_id="apple", target_event_id="3",
        destination_id="kitchen", observation_cutoff=4,
    ) == "office"


def test_task3_late_observation_does_not_leak_into_earlier_cutoff():
    story = [
        ev("1", "PICK_UP", {"actor": "john", "object": "apple"}, 1),
        ev("2", "MOVE", {"actor": "john", "destination": "office"}, 2),
        ev("3", "MOVE", {"actor": "john", "destination": "kitchen"}, 3, observed=5),
    ]
    assert task3_object_location_before_move(
        story, object_id="apple", target_event_id="3",
        destination_id="kitchen", observation_cutoff=4,
    ) is None
    assert task3_object_location_before_move(
        story, object_id="apple", target_event_id="3",
        destination_id="kitchen", observation_cutoff=5,
    ) == "office"


def test_task5_three_argument_give_queries_bind_roles_within_one_event():
    events = [
        ev("1", "GIVE", {"giver": "mary", "object": "cake", "recipient": "fred"}, 1),
        ev("2", "GIVE", {"giver": "fred", "object": "cake", "recipient": "bill"}, 2),
        ev("3", "GIVE", {"giver": "bill", "object": "milk", "recipient": "jeff"}, 3),
    ]
    assert task5_answer_role(
        events, bound_roles={"object": "cake", "recipient": "fred"},
        answer_role="giver", observation_cutoff=4,
    ) == ("mary",)

    # Repeated matching object relations resolve to the latest event.
    assert task5_answer_role(
        events, bound_roles={"object": "cake"},
        answer_role="recipient", observation_cutoff=4,
    ) == ("bill",)
    assert task5_answer_role(
        events, bound_roles={"giver": "fred", "object": "cake"},
        answer_role="recipient", observation_cutoff=4,
    ) == ("bill",)
    # A cross-event combination must not be assembled from unrelated roles.
    assert task5_answer_role(
        events, bound_roles={"giver": "mary", "recipient": "bill"},
        answer_role="object", observation_cutoff=4,
    ) == ()


def test_task5_late_event_not_visible_before_observed_at():
    events = [ev("1", "GIVE", {"giver": "bill", "object": "milk", "recipient": "jeff"}, 1, observed=5)]
    assert task5_answer_role(
        events, bound_roles={"object": "milk", "recipient": "jeff"},
        answer_role="giver", observation_cutoff=4,
    ) == ()


def test_structured_event_rejects_duplicate_roles():
    with pytest.raises(ValueError, match="unique"):
        StructuredEvent("bad", "GIVE", (("giver", "mary"), ("giver", "fred")),
                        1, 1, "source")

def test_task3_exact_anchor_disambiguates_repeated_destination():
    story = [
        ev("1", "PICK_UP", {"actor": "john", "object": "apple"}, 1),
        ev("2", "MOVE", {"actor": "john", "destination": "office"}, 2),
        ev("3", "MOVE", {"actor": "john", "destination": "kitchen"}, 3),
        ev("4", "MOVE", {"actor": "john", "destination": "garden"}, 4),
        ev("5", "MOVE", {"actor": "john", "destination": "kitchen"}, 5),
    ]
    assert task3_object_location_before_move(
        story, object_id="apple", target_event_id="5",
        destination_id="kitchen", observation_cutoff=5,
    ) == "garden"

def test_structured_query_contract_excludes_gold_answers_and_support_witnesses():
    movement = ev("story-1:3", "MOVE", {"actor": "mary", "destination": "bathroom"}, 3)
    query = StructuredQuery(
        query_id="story-1:4", story_id="story-1", task_id=3,
        query_type="OBJECT_LOCATION_BEFORE_MOVE", object_id="football",
        destination_id="bathroom", target_event_id=movement.event_id,
        answer_role="location", observed_at=4, source_ref="story-1:4",
    )
    story = StructuredStory("story-1", (movement,), (query,))
    assert story.queries == (query,)
    assert not hasattr(query, "answer")
    assert not hasattr(query, "supporting_event_ids")


def test_task5_query_contract_rejects_answer_role_as_input():
    with pytest.raises(ValueError, match="cannot also be supplied"):
        StructuredQuery(
            query_id="s:4", story_id="s", task_id=5, query_type="GIVE_ROLE",
            bound_roles=(("object", "football"), ("recipient", "fred")),
            answer_role="recipient", observed_at=4, source_ref="s:4",
        )

def test_nary_give_event_requires_all_three_roles():
    with pytest.raises(ValueError, match="GIVE event roles"):
        StructuredEvent(
            "story-1:7", "GIVE",
            (("giver", "mary"), ("object", "football")),
            7, 7, "story-1:7",
        )
