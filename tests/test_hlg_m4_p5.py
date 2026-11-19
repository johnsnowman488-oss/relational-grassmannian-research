import numpy as np
from rgm.leptograph.m4.architectures import M4MemoryVariant
from rgm.experiments.hlg_m4_job2 import run

def test_four_architectures_have_distinct_state_contracts():
    models={n:M4MemoryVariant(n,relation_count=4) for n in "ABCR"}
    for model in models.values(): model.observe(1,2.0)
    assert models["A"].soe is not None and models["A"].relations=={}
    assert models["B"].soe is not None and models["B"].relations[1]==2.0
    assert models["C"].unified is not None and models["C"].relations=={}
    assert models["R"].soe is None and models["R"].relations[1]==2.0

def test_relation_reference_persists_across_intervening_observations():
    for name in ("B","R"):
        model=M4MemoryVariant(name,relation_count=4); model.observe(0,3.5)
        for k in (1,2,3): model.observe(k,float(k))
        assert model.query(0)==3.5

def test_temporal_and_unified_states_decay_after_distractors():
    for name in ("A","C"):
        model=M4MemoryVariant(name,relation_count=4); model.observe(0,3.5)
        before=model.query(0)
        for k in (1,2,3): model.observe(k,float(k))
        assert abs(model.query(0)) < abs(before)

def test_preliminary_experiment_is_reproducible_and_reports_all_variants():
    a=run(seed_count=3,relation_count=4,delays=(0,2))
    b=run(seed_count=3,relation_count=4,delays=(0,2))
    assert a==b
    assert set(a["mean_squared_error_by_architecture_and_delay"])==set("ABCR")
    assert a["mean_squared_error_by_architecture_and_delay"]["B"]["2"]==0.0
