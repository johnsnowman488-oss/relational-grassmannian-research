from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/experiments/HLG_BABI_TASK_EXPANSION_v1_0.json"


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_expansion_is_preparation_only_and_preserves_frozen_tasks():
    data = load_manifest()
    assert data["status"] == "PHASE_B_ADAPTERS_IMPLEMENTED_PENDING_SOURCE_WIDE_AUDIT"
    assert data["scope"]["phase_b_adapters_implemented"] is True
    assert data["scope"]["frozen_tasks"] == [3, 5]
    assert data["scope"]["execution_authorized"] is False
    assert data["campaign"]["first_wave_parallel_case_studies"] == [11, 14, 19]


def test_task_sequence_and_roles_are_explicit_and_unique():
    data = load_manifest()
    tasks = data["tasks"]
    ids = [task["task_id"] for task in tasks]
    assert ids == [11, 14, 19, 13, 2, 4]
    assert len(ids) == len(set(ids))
    assert [t["task_id"] for t in tasks if t["role"] == "primary_case_study_1" or t["role"] == "primary_case_study_2" or t["role"] == "primary_case_study_3"] == [11, 14, 19]
    assert [t["task_id"] for t in tasks if t["role"].startswith("control_")] == [2, 4]


def test_every_task_has_l0_l1_l2_and_task_specific_prediction_metrics():
    for task in load_manifest()["tasks"]:
        assert set(task["evidence"]) == {"L0", "L1", "L2"}
        assert task["prediction_targets"]
        assert task["metrics"]
        assert task["baseline_requirements"]
        assert task["risks"]


def test_source_contract_keeps_story_boundaries_and_gold_labels_separate():
    data = load_manifest()
    source = data["source"]
    assert "line number 1" in source["source_format"]
    shared = data["shared_contract"]
    assert shared["input_label_separation"] is True
    assert shared["story_scoped_event_and_query_ids"] is True
    assert shared["gold_answer_and_support_ids_evaluator_only"] is True
    assert shared["cross_story_retrieval_forbidden"] is True


def test_task19_route_answer_is_ordered_direction_sequence():
    task = next(t for t in load_manifest()["tasks"] if t["task_id"] == 19)
    assert "north/south/east/west" in task["answer_shape"]
    assert "token order exactly" in task["answer_shape"]
    assert "path_exact_match" in task["metrics"]


def test_task14_separates_event_time_from_observation_time():
    task = next(t for t in load_manifest()["tasks"] if t["task_id"] == 14)
    assert "observation time kept distinct" in task["evidence"]["L0"]
    assert "before_after_relation_f1" in task["metrics"]
    assert "causal_cutoff_violation_count" in task["metrics"]


def test_task13_uses_set_valued_coreference_not_scalar_binding():
    task = next(t for t in load_manifest()["tasks"] if t["task_id"] == 13)
    assert "plural COREFERS_TO links with set-valued antecedents" in task["evidence"]["L1"]
    assert "group_antecedent_exact_match" in task["metrics"]


def test_no_new_task_is_claimed_as_implemented():
    data = load_manifest()
    assert data["campaign"]["execution_gate"].startswith("No campaign execution")
    assert data["scope"]["execution_authorized"] is False
