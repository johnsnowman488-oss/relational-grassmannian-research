import numpy as np

from rgm.experiments.e01_b import codebooks, make_case
from rgm.experiments.e01_c import (
    CODEBOOK_SEEDS, CONDITIONS, MEMORY_ARMS, VARIANTS, WORLD_SEEDS,
    _memory_state, _paths, _supports, run,
)


def test_e01_c_design_is_frozen():
    assert len(CONDITIONS) == 6
    assert MEMORY_ARMS == ("slow_only", "full_history")
    assert VARIANTS == ("observed", "repeat_suppressed", "oracle_facts")
    assert len(WORLD_SEEDS) == len(CODEBOOK_SEEDS) == 3
    assert len(CONDITIONS) * len(MEMORY_ARMS) * len(WORLD_SEEDS) * len(CODEBOOK_SEEDS) == 108


def test_repeat_suppression_preserves_time_updates_but_changes_state():
    case = make_case(501, entities=4, fact_count=8, distractors=12, depth=2, gap="medium")
    books = codebooks(4, 9137)
    actual = _memory_state(case, "slow_only", books, 4, suppress=False)
    filtered = _memory_state(case, "slow_only", books, 4, suppress=True)
    assert actual.shape == filtered.shape == (1, 16)
    assert len(case.events) == len(case.facts) + case.distractor_count
    assert not np.array_equal(actual, filtered)


def test_exact_fact_oracle_yields_correct_true_and_negative_paths():
    positive = make_case(503, entities=4, fact_count=8, distractors=4, depth=2, gap="medium")
    negative = make_case(502, entities=4, fact_count=8, distractors=4, depth=2, gap="medium")
    ps = _supports(positive, "oracle_facts", "slow_only", codebooks(4, 9137), 4)
    ns = _supports(negative, "oracle_facts", "slow_only", codebooks(4, 9137), 4)
    pe, ne = _paths(positive, ps, 2), _paths(negative, ns, 2)
    assert pe["best_true"]["score"] == 1.0
    assert ne["best_any"]["score"] == 0.0


def test_run_emits_all_interventions_and_per_sequence_path_evidence():
    result = run("baseline_e4", "slow_only", 501, 9137, n=20)
    assert set(result["variants"]) == set(VARIANTS)
    for variant in VARIANTS:
        item = result["variants"][variant]
        assert len(item["per_sequence"]) == 20
        assert "path_evidence" in item["per_sequence"][0]
        assert "fact_probes" in item["per_sequence"][0]
    assert result["variants"]["oracle_facts"]["composition"]["accuracy"] == 1.0
    assert result["variants"]["oracle_facts"]["constituent_retrieval"]["accuracy"] == 1.0
