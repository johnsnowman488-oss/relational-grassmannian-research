import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "docs/experiments/HLG_BABI_EXPANSION_LEARNING_CAMPAIGN_v1_0.json"


def test_expansion_campaign_protocol_is_frozen_but_not_authorized():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["status"] == "FROZEN_NOT_AUTHORIZED"
    assert config["execution_gate"]["authorized"] is False
    assert config["execution_gate"]["launch_allowed"] is False
    assert config["scope"]["tasks"] == [11, 14, 19]
    assert config["scope"]["architectures"] == ["HLA", "HLB"]
    assert config["scope"]["conditions"] == [
        "full_learning", "no_temporal", "no_relational",
        "no_abstraction", "no_task", "no_learning",
    ]
    assert config["scope"]["seeds"] == list(range(953100, 953110))
    assert config["experimental_design"]["run_units"] == 360
    assert config["workload"]["query_presentations"] == 3_600_000
    assert config["sharding"]["worker_count"] == 4
    assert config["sharding"]["max_parallel"] == 4
    assert config["sharding"]["units_per_shard"] == 90
    assert config["sharding"]["cancel_in_progress"] is False
    assert config["scope"]["task3_task5_modified"] is False


def test_protocol_keeps_official_test_sealed_and_candidate_selection_task_local():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert "official test" in config["source"]["fit_validation_policy"].lower()
    assert config["experimental_design"]["candidate_selection"]["partition"] == "validation only"
    assert config["experimental_design"]["candidate_selection"]["scope"] == "independent per task and architecture"
    assert config["experimental_design"]["confirmatory"].startswith("A generated")
    assert config["execution_gate"]["authorized"] is False
