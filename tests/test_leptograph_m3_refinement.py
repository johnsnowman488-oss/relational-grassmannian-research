"""Tests for the HLG-M3 final refinement interfaces."""
import numpy as np
import pytest
from rgm.leptograph.m3 import MultiSourceRidge
from rgm.leptograph.m3.integration_refinement import run_integrated_refinement
from rgm.experiments.leptograph_m3_refinement import WORK_PACKAGES, run_package


def test_source_gate_masks_effective_prediction_but_preserves_operator():
    rng=np.random.default_rng(81); model=MultiSourceRidge({"a":1},0,1,ridge=1e-7)
    for _ in range(100):
        x=float(rng.normal()); model.update({"a":[x]},[],[2*x])
    active=model.predict({"a":[1.]},[],source_gates={"a":1.})
    dormant=model.predict({"a":[1.]},[],source_gates={"a":0.})
    assert abs(float(active[0]-dormant[0]))>0.5
    assert np.linalg.norm(model.source_operator("a"))>1.


def test_operator_override_controls_effective_prediction():
    model=MultiSourceRidge({"a":1},0,1,ridge=1e-6)
    for x in np.linspace(-2,2,80): model.update({"a":[x]},[],[x])
    ordinary=model.predict({"a":[1.]},[])
    revised=model.predict({"a":[1.]},[],operator_overrides={"a":[[3.]]})
    assert float(revised[0])>float(ordinary[0])+1.


def test_schur_identifiability_rejects_collinear_source_blocks():
    rng=np.random.default_rng(82); model=MultiSourceRidge({"a":1,"b":1},0,1)
    for _ in range(200):
        x=float(rng.normal()); model.update({"a":[x],"b":[2*x]},[],[3*x])
    report=model.conditional_identifiability()
    assert report["a"]["identifiable"] is False and report["b"]["identifiable"] is False
    assert report["a"]["rank"]==0 and report["b"]["rank"]==0


def test_schur_identifiability_accepts_independent_sources():
    rng=np.random.default_rng(83); model=MultiSourceRidge({"a":2,"b":3},2,2)
    for _ in range(400):
        a,b,c=rng.normal(size=2),rng.normal(size=3),rng.normal(size=2)
        model.update({"a":a,"b":b},c,0.2*a+0.1*b[:2]+0.05*c)
    report=model.conditional_identifiability()
    assert report["a"]["identifiable"] is True and report["b"]["identifiable"] is True


def test_integrated_refinement_outputs_context_activation_and_revision_findings():
    result=run_integrated_refinement(seed=1604,steps=300)
    assert result["steps"]==300
    assert result["context"]["gated_steps"]>0
    assert np.isfinite(result["prequential"]["effective_mean_mse"])
    assert "candidate_revision" in result
    assert result["memory_resources"]["resource_matched"] is False


@pytest.mark.parametrize("package_id",WORK_PACKAGES)
def test_all_refinement_packages_emit_json_safe_records(package_id):
    record=run_package(package_id)
    assert record["campaign_id"]=="HLG-M3-FINAL-REFINEMENT-v0.2"
    assert record["package_id"]==package_id
    assert record["execution_passed"] is True
    assert "measurements" in record
