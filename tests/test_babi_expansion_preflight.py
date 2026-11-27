from rgm.experiments.babi_expansion_adapters import ExpansionStory
from rgm.experiments.babi_expansion_preflight import (
    _fit_validation_split, _run_units, _warm_online_split,
)


def stories(n: int):
    return [ExpansionStory(f"task11/train/story{i:04d}", 11, (), ()) for i in range(n)]


def test_nested_partitions_are_whole_story_disjoint_and_complete():
    fit, validation = _fit_validation_split(stories(100), 11)
    warm, online = _warm_online_split(fit, 11)
    fit_ids = {row.story_id for row in fit}
    validation_ids = {row.story_id for row in validation}
    warm_ids = {row.story_id for row in warm}
    online_ids = {row.story_id for row in online}
    assert len(validation_ids) == 10
    assert len(warm_ids) == 72
    assert len(online_ids) == 18
    assert warm_ids.isdisjoint(online_ids)
    assert (warm_ids | online_ids) == fit_ids
    assert fit_ids.isdisjoint(validation_ids)


def test_nested_partition_assignment_is_deterministic_and_source_ordered():
    original = stories(30)
    fit_a, val_a = _fit_validation_split(original, 11)
    warm_a, online_a = _warm_online_split(fit_a, 11)
    fit_b, val_b = _fit_validation_split(original, 11)
    warm_b, online_b = _warm_online_split(fit_b, 11)
    assert [s.story_id for s in fit_a] == [s.story_id for s in fit_b]
    assert [s.story_id for s in val_a] == [s.story_id for s in val_b]
    assert [s.story_id for s in warm_a] == [s.story_id for s in warm_b]
    assert [s.story_id for s in online_a] == [s.story_id for s in online_b]


def test_frozen_run_manifest_has_360_unique_keys_and_four_equal_shards():
    units = _run_units()
    assert len(units) == len({row["run_unit_key"] for row in units}) == 360
    assert [sum(row["shard"] == shard for row in units) for shard in range(4)] == [90, 90, 90, 90]
    assert {row["task_id"] for row in units} == {11, 14, 19}
    assert {row["architecture"] for row in units} == {"HLA", "HLB"}
    assert {row["condition"] for row in units} == {
        "full_learning", "no_temporal", "no_relational",
        "no_abstraction", "no_task", "no_learning",
    }
    assert {row["seed"] for row in units} == set(range(953100, 953110))
