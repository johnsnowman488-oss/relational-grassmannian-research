import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "docs/experiments/HLG_BABI_TASK11_LEARNING_CAMPAIGN_v1_1.json"
BASELINES = ROOT / "docs/experiments/HLG_BABI_TASK11_NONORACLE_BASELINE_VALIDATION_v1_0.md"
WORKFLOW = ROOT / ".github/workflows/task11-full-scale-preflight.yml"
PREPARE = ROOT / "scripts/prepare_babi_task11_campaign.py"


def test_task11_campaign_is_exactly_120_units_and_keeps_other_tasks_locked():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["status"] == "FROZEN_STAGED_WAVE1"
    assert config["protocol_version"] == "1.1.0"
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
    assert config["native_runtime"]["top_down_gain"] == 1.0
    assert config["native_runtime"]["pinned_commit"] == "48228f8c326c0e8546855eb898d374453d705b77"
    assert '"HLG-BABI-TASK11-LEARNING-CAMPAIGN-v1.1"' in PREPARE.read_text(encoding="utf-8")


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


def test_wave1_is_four_of_the_120_campaign_units_and_has_frozen_limits():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    staged = config["staged_execution"]
    assert staged["mode"] == "WAVE1_THEN_REMAINING_116"
    assert staged["total_campaign_units"] == 120
    assert staged["wave1"]["seed"] == 953100
    assert staged["wave1"]["run_units"] == 4
    assert staged["wave1"]["counts_toward_total"] is True
    assert {(x["architecture"], x["condition"]) for x in staged["wave1"]["combinations"]} == {
        ("HLA", "full_learning"), ("HLA", "no_learning"),
        ("HLB", "full_learning"), ("HLB", "no_learning"),
    }
    assert staged["after_wave1"]["run_units"] == 116
    assert staged["ci_job_timeout_minutes"] == 180
    assert staged["run_unit_wall_limit_seconds"] == 3600
    assert "does not relax" in staged["timeout_distinction"]
    gate = config["resource_preflight"]
    assert gate["status"] == "SUPERSEDED_BY_IN_CAMPAIGN_WAVE1"
    assert gate["superseded_reserved_seed"] == 953099
    assert gate["limits"]["max_worker_rss_mb"] == 2048
    assert gate["limits"]["max_python_allocation_mb"] == 1024
    assert gate["limits"]["max_checkpoint_bytes"] == 536870912
    assert gate["limits"]["max_unit_wall_seconds"] == 3600
    assert gate["limits"]["max_unit_artifact_bytes"] == 268435456
    assert config["execution_gate"]["campaign_units_authorized"] is False
    assert any("Wave 1" in item for item in config["execution_gate"]["required_before_launch"])


def test_workflow_has_three_hour_timeouts_and_no_duplicate_preflight():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "wave1-units:" in workflow
    assert "accept-wave1:" in workflow
    assert "timeout-minutes: 180" in workflow
    assert "seed: 953100" in workflow
    assert "accept-full-scale-preflight" not in workflow
    assert "run-kind preflight" not in workflow
    assert "condition: full_learning\n            seed: 953100" in workflow
    assert "condition: no_learning\n            seed: 953100" in workflow


def test_task11_baseline_record_preserves_independent_evaluation_and_claim_limits():
    text = BASELINES.read_text(encoding="utf-8")
    assert "1.000 (1,000/1,000)" in text
    assert "0.704 (704/1,000)" in text
    assert "NOT INDEPENDENTLY EVALUABLE" in text
    assert "Tasks 14 and 19 remain locked" in text
