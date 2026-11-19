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


def test_outage_advancement_preserves_relational_store_but_decays_temporal_state():
    for name in ("A","B","C","R"):
        model=M4MemoryVariant(name,relation_count=4); model.observe(0,3.5)
        before=model.query(0); model.advance_gap(5); after=model.query(0)
        if name in ("B","R"): assert after==before
        else: assert abs(after)<abs(before)

def test_p2_context_acquisition_is_bounded_and_abstains_at_capacity():
    from rgm.leptograph.m3.context import ContextBank
    from rgm.leptograph.m4.architectures import BoundedContextAcquisition
    bank=ContextBank(metric=np.eye(2),capacity=2,novelty_repeats=2)
    bank.add_initial([0.0,0.0]); acquisition=BoundedContextAcquisition(bank)
    assert acquisition.observe([10.0,10.0])["status"]=="PENDING_NOVELTY"
    assert acquisition.observe([10.0,10.0])["status"]=="ACQUIRED"
    assert len(bank.slots)==2
    assert acquisition.observe([20.0,20.0])["status"]=="ABSTAIN_CAPACITY"
    assert len(bank.slots)==2


def test_A_fits_shared_readout_gain_on_calibration_examples():
    model=M4MemoryVariant("A",relation_count=4)
    assert model.fit_readout([0.5,1.0,1.5],[1.0,2.0,3.0])==2.0
    model.observe(0,2.0)
    assert model.query(0)==4.0
