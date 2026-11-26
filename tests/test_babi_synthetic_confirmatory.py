import json
import random
from pathlib import Path

from rgm.experiments.babi_synthetic_confirmatory import (
    TASK3_SEED, TASK5_SEED, _story_payload, _task3_story, _task5_story,
    write_confirmatory_inputs,
)


def test_synthetic_task3_is_deterministic_and_contains_only_input_annotations():
    a = _task3_story(1, random.Random(TASK3_SEED))
    b = _task3_story(1, random.Random(TASK3_SEED))
    assert _story_payload(a) == _story_payload(b)
    assert len(a.queries) == 5
    events = {event.event_id: event for event in a.events}
    for query in a.queries:
        target = events[query.target_event_id]
        assert target.event_type == "MOVE"
        assert target.role_map()["destination"] == query.destination_id
        assert not hasattr(query, "gold_answer")
        assert not hasattr(query, "support_event_ids")


def test_synthetic_task5_contains_nary_give_and_decoy_context_without_label_fields():
    story = _task5_story(1, random.Random(TASK5_SEED))
    assert len(story.queries) == 5
    assert sum(event.event_type == "GIVE" for event in story.events) == 20
    assert sum(event.event_type == "PASS" for event in story.events) == 5
    assert any(event.event_type == "MOVE" for event in story.events)
    assert any(event.event_type == "PICK_UP" for event in story.events)
    assert any(event.event_type == "DROP" for event in story.events)
    for query in story.queries:
        assert query.answer_role not in dict(query.bound_roles)
        assert not hasattr(query, "gold_answer")
        assert not hasattr(query, "support_event_ids")


def test_confirmatory_bundle_is_inputs_only_and_uses_novel_entities(tmp_path: Path):
    annotations = tmp_path / "annotations"
    annotations.mkdir()
    official_story = {
        "story_id": "task3/fit/story000001",
        "task_id": 3,
        "events": [{"roles": [["actor", "mary"], ["destination", "office"]]}],
        "queries": [],
    }
    (annotations / "task3-fit.inputs.jsonl").write_text(
        json.dumps(official_story) + "\n", encoding="utf-8"
    )
    output = tmp_path / "confirmatory"
    report = write_confirmatory_inputs(output, annotations)
    assert report["labels_emitted"] is False
    assert report["official_entity_vocabulary_overlap"] == []
    assert report["tasks"]["3"]["story_count"] == 200
    assert report["tasks"]["3"]["query_count"] == 1000
    assert report["tasks"]["5"]["story_count"] == 200
    assert report["tasks"]["5"]["query_count"] == 1000
    assert not list(output.glob("*.labels.jsonl"))
    for task_id in (3, 5):
        path = output / f"task{task_id}-confirmatory.inputs.jsonl"
        first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        assert set(first) == {"story_id", "task_id", "events", "queries"}
        assert all("gold_answer" not in query and "support_event_ids" not in query
                   for query in first["queries"])
