import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "docs/experiments/HLG_BABI_TASK11_LEARNING_CAMPAIGN_v1_0.json"
BASELINES = ROOT / "docs/experiments/HLG_BABI_TASK11_NONORACLE_BASELINE_VALIDATION_v1_0.md"


def test_task11_campaign_is_exactly_120_units_and_keeps_other_tasks_locked():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["status"] == "FROZEN_AWAITING_FULL_SCALE_PREFLIGHT"
    assert config["scope"]["tasks"] == [11]
    assert config["scope"]["architectures"] == ["HLA", "HLB"]
    assert len(config["scope"]["conditions"]) == 6
    assert config["scope"]["seeds"] == list(range(953100, 953110))
    assert config["experimental_design"]["run_units"] == 120
    assert config["experimental_design"]["formula"] == (
        "1 task × 2 architectures × 6 conditions × 10 seeds"
    )
    assert config["scope"]["tasks14_19_locked"] is True
    assert config["scope"]["task3_task5_modified"] is False


def test_task11_protocol_uses_nested_whole_story_partitions_and_sealed_test():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    parts = config["partitions"]
    assert parts["fit"] == {"stories": 1800, "queries": 9000}
    assert parts["warm_start"]["stories"] == 1440
    assert parts["online_adaptation"]["stories"] == 360
    assert parts["validation"] == {"stories": 200, "queries": 1000}
    assert parts["official_test"]["loaded"] is False
    assert parts["unit"] == "whole story"
    assert "computed from exact whole-story assignment" in parts["warm_start"]["queries"]


def test_task11_protocol_has_measured_resource_preflight_and_no_oracle_shortcut():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    preflight = config["resource_preflight"]
    assert preflight["status"] == "REQUIRED_BEFORE_CAMPAIGN"
    assert preflight["reserved_seed"] not in config["scope"]["seeds"]
    assert preflight["run_units"] == 4
    assert preflight["max_parallel"] == 4
    assert preflight["pass_rule"]
    assert config["execution_gate"]["launch_allowed"] is True
    assert any("full repository" in item.lower() for item in config["execution_gate"]["required_before_launch"])
    assert any("full-scale reserved-seed resource preflight" in item.lower() for item in config["execution_gate"]["required_before_launch"])
    assert "campaign starts only if both pass" in config["execution_gate"]["freeze_boundary"].lower()
    assert config["baselines"]["strongest_non_oracle"] == "nearest-compatible-antecedent"
    assert config["baselines"]["validation_answer_exact_match"] == 1.0


def test_task11_baseline_record_preserves_independent_evaluation_and_claim_limits():
    text = BASELINES.read_text(encoding="utf-8")
    assert "1.000 (1,000/1,000)" in text
    assert "0.704 (704/1,000)" in text
    assert "NOT INDEPENDENTLY EVALUABLE" in text
    assert "Tasks 14 and 19 remain locked" in text
