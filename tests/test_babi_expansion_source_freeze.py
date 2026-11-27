from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "freeze_babi_expansion_sources.py"
SPEC = spec_from_file_location("babi_expansion_freeze", SCRIPT)
MODULE = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_task19_audit_keeps_ordered_direction_answer_and_local_supports():
    source = (
        "1 The garden is north of the kitchen.\n"
        "2 The office is east of the garden.\n"
        "3 What is the path from the kitchen to the office?\tn,e\t1 2\n"
        "1 The kitchen is south of the garden.\n"
        "2 What is the path back?\tsouth\t1\n"
    ).encode()
    audit = MODULE.audit_member(
        source, task_id=19, member_name="qa19_path-finding_train.txt"
    )
    assert audit["story_count"] == 2
    assert audit["statement_count"] == 3
    assert audit["question_count"] == 2
    assert audit["support_reference_count"] == 3
    assert audit["support_references_valid_story_local_prior_statements"] is True


def test_support_reference_cannot_point_to_future_or_question_line():
    source = (
        "1 Mary moved to the bathroom.\n"
        "2 Where is Mary?\tbathroom\t3\n"
        "3 John went to the hallway.\n"
    ).encode()
    with pytest.raises(MODULE.SourceAuditError, match="support IDs"):
        MODULE.audit_member(
            source, task_id=11, member_name="qa11_basic-coreference_train.txt"
        )


def test_support_reference_cannot_cross_story_boundary():
    source = (
        "1 Mary moved to the bathroom.\n"
        "2 Where is Mary?\tbathroom\t1\n"
        "1 John went to the hallway.\n"
        "2 Where is John?\thallway\t3\n"
        "3 Where is Mary?\tbathroom\t1\n"
    ).encode()
    with pytest.raises(MODULE.SourceAuditError, match="support IDs"):
        MODULE.audit_member(
            source, task_id=11, member_name="qa11_basic-coreference_train.txt"
        )


def test_task19_rejects_destination_only_or_non_direction_answers():
    source = (
        "1 The garden is north of the kitchen.\n"
        "2 What is the path?\tgarden\t1\n"
    ).encode()
    with pytest.raises(MODULE.SourceAuditError, match="ordered comma-separated"):
        MODULE.audit_member(
            source, task_id=19, member_name="qa19_path-finding_train.txt"
        )


def test_line_numbers_must_be_contiguous_and_story_scoped():
    source = (
        "1 Mary moved to the bathroom.\n"
        "3 Where is Mary?\tbathroom\t1\n"
    ).encode()
    with pytest.raises(MODULE.SourceAuditError, match="expected story-local line"):
        MODULE.audit_member(
            source, task_id=11, member_name="qa11_basic-coreference_train.txt"
        )


def test_git_blob_crosscheck_uses_git_object_header():
    payload = b"bAbI source\n"
    assert MODULE.git_blob_sha1(payload) == "3d84619b180f58ebd0f11845637315bbe4463d0c"
