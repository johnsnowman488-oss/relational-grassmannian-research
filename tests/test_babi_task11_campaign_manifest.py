from types import SimpleNamespace
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_babi_task11_campaign import seeded_warm_online_split


def test_task11_seed_specific_nested_partitions_are_whole_story_and_deterministic():
    stories = [SimpleNamespace(story_id=f"story-{index:03d}") for index in range(40)]
    warm_a, online_a = seeded_warm_online_split(stories, 953100)
    warm_a_repeat, online_a_repeat = seeded_warm_online_split(stories, 953100)
    warm_b, online_b = seeded_warm_online_split(stories, 953101)

    assert len(warm_a) == 32
    assert len(online_a) == 8
    assert {row.story_id for row in warm_a}.isdisjoint(
        {row.story_id for row in online_a}
    )
    assert {row.story_id for row in warm_a + online_a} == {
        row.story_id for row in stories
    }
    assert [row.story_id for row in warm_a] == [
        row.story_id for row in warm_a_repeat
    ]
    assert [row.story_id for row in online_a] == [
        row.story_id for row in online_a_repeat
    ]
    assert {row.story_id for row in warm_a} != {
        row.story_id for row in warm_b
    }
