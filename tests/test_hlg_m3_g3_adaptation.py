import numpy as np
import pytest
from rgm.experiments.hlg_m3_g3_adaptation import ENVIRONMENTS, POLICIES, calibrate_detector_threshold, evaluate_policy, generate_stream, run_environment

def test_environment_paths_are_deterministic_and_distinct():
    streams={n:generate_stream(world_seed=910001,replicate_seed=110001,environment=n) for n in ENVIRONMENTS}
    for n,s in streams.items():
        replay=generate_stream(world_seed=910001,replicate_seed=110001,environment=n)
        assert np.array_equal(s["x"],replay["x"]) and np.array_equal(s["y"],replay["y"])
    assert np.allclose(streams["stable"]["theta_path"][160],streams["stable"]["theta_path"][320])
    assert not np.allclose(streams["gradual"]["theta_path"][160],streams["gradual"]["theta_path"][320])
    assert not np.allclose(streams["abrupt"]["theta_path"][159],streams["abrupt"]["theta_path"][160])

def test_policy_arms_preserve_prequential_order():
    stream=generate_stream(world_seed=910002,replicate_seed=110002,environment="abrupt")
    results=[evaluate_policy(stream,p) for p in POLICIES]
    assert all(r["prequential_prediction_before_feedback"] for r in results)
    assert results[0]["promoted"] is False and results[0]["alarm_step"] is None
    assert {r["policy"] for r in results}==set(POLICIES)
    assert all(np.isfinite(r["overall_policy_mse"]) for r in results)

def test_runner_pairs_policy_arms_and_rejects_non_test_worlds():
    world={"world_id":"TEST-W01","split":"test","world_configuration_seed":910003,
        "replicate_seeds":[110003,110004],"factor_profile":{"observation_noise_multiplier":1.0}}
    report=run_environment([world],"gradual")
    assert report["world_count"]==1 and report["stream_count"]==2 and report["policy_arm_count"]==4
    assert len(report["streams"])==8 and report["integrity"]["same_streams_across_policy_arms"]
    with pytest.raises(ValueError,match="held-out test"):
        run_environment([{**world,"split":"development_fit"}],"stable")


def test_detector_calibration_uses_development_worlds_and_checks_validation():
    fit=[{"split":"development_fit","world_configuration_seed":920001,"replicate_seeds":[120001,120002],"factor_profile":{}}]
    validation=[{"split":"development_validation","world_configuration_seed":920002,"replicate_seeds":[120003,120004],"factor_profile":{}}]
    report=calibrate_detector_threshold(fit,validation,candidate_thresholds=(8,16,32,64,128))
    assert report["test_worlds_used"] is False
    assert report["selected_threshold"] in (8.0,16.0,32.0,64.0,128.0)
    assert report["fit_false_alarm_rate"] == 0.0
    assert report["fit_false_alarm_count"] == 0
    assert report["threshold_selection_rule"].startswith("lowest predeclared threshold with zero")
    assert 0 <= report["validation_false_alarm_rate"] <= 0.05
