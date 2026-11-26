from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_SPEC = spec_from_file_location(
    "babi_freeze_script",
    Path(__file__).resolve().parents[1] / "scripts" / "freeze_babi_tasks.py",
)
_MODULE = module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)


def test_story_split_is_deterministic_and_never_splits_a_story():
    source = b"".join(
        f"1 fact-{i}a\n2 question-{i}\tanswer-{i}\t1\n".encode()
        for i in range(20)
    )
    fit_a, valid_a, record_a = _MODULE.split_story_blocks(source, task_id=3)
    fit_b, valid_b, record_b = _MODULE.split_story_blocks(source, task_id=3)

    assert (fit_a, valid_a, record_a) == (fit_b, valid_b, record_b)
    assert record_a["source_story_count"] == 20
    assert record_a["validation_story_count"] == 2
    assert record_a["fit_story_count"] == 18
    assert fit_a + valid_a != source  # partitions preserve source order independently

    fit_stories = fit_a.split(b"1 fact-")[1:]
    valid_stories = valid_a.split(b"1 fact-")[1:]
    fit_ids = {story.split(b"a", 1)[0] for story in fit_stories}
    valid_ids = {story.split(b"a", 1)[0] for story in valid_stories}
    assert fit_ids.isdisjoint(valid_ids)
    assert len(fit_ids | valid_ids) == 20


def test_story_split_rejects_malformed_source_without_story_reset():
    import pytest

    with pytest.raises(ValueError, match="before first story reset"):
        _MODULE.split_story_blocks(b"2 orphaned line\n", task_id=5)
