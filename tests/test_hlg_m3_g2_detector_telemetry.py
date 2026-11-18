from rgm.experiments.hlg_m3_g2_detector_telemetry import classify_stream, _summarize_by_family


def _row(*, family, alarms, schedule=(), status=None):
    return {
        "world_id": f"{family}-W01",
        "world_configuration_seed": 1,
        "replicate_seed": 2,
        "split": "test",
        "stream_sha256": "a" * 64,
        "step_count": 300,
        "factor_profile": {"drift_family": family, "context_bank_capacity": 4},
        "alarm_steps": alarms,
        "detector_alarms": len(alarms),
        "detector_trace": [],
        "change_schedule": [{"step": step, "event": event} for step, event in schedule],
        "detector_baseline": {"observed_acquisition_rows": 20, "mean_squared_loss": 0.1, "scale": 0.01},
        "candidate_lifecycle": {"status": status} if status else None,
        "candidate_lifecycle_records": [],
        "candidate_revision_applied_to_fallback": status == "PROMOTED_EVALUATED",
        "resource": {},
    }


def test_classifies_pre_drift_alarm_separately_from_detection():
    result = classify_stream(_row(
        family="step",
        alarms=[90, 120],
        schedule=[(100, "drift:step")],
        status="PROMOTED_EVALUATED",
    ))
    assert result["pre_drift_alarm_steps"] == [90]
    assert result["post_drift_alarm_steps"] == [120]
    assert result["detection_delay_steps"] == 20
    assert result["missed_scheduled_change"] is False


def test_stationary_alarm_is_counted_as_false_alarm():
    result = classify_stream(_row(family="stationary", alarms=[50, 80]))
    assert result["stationary_false_alarm_stream"] is True
    assert result["stationary_false_alarm_count"] == 2
    assert result["drift_start_step_evaluator_only"] is None


def test_transient_detection_after_reversion_is_not_counted_as_timely():
    result = classify_stream(_row(
        family="transient",
        alarms=[112],
        schedule=[(100, "drift:transient"), (110, "transient_reversion")],
    ))
    assert result["detection_delay_steps"] == 12
    assert result["detected_before_transient_reversion"] is False
    assert result["first_detection_after_transient_reversion"] is True


def test_summary_keeps_false_alarms_and_pre_drift_alarms_distinct():
    rows = [
        classify_stream(_row(family="stationary", alarms=[50])),
        classify_stream(_row(family="step", alarms=[90, 120], schedule=[(100, "drift:step")])),
    ]
    summary = _summarize_by_family(rows)
    assert summary["stationary"]["stationary_false_alarm_streams"] == 1
    assert summary["step"]["pre_drift_alarm_events"] == 1
    assert summary["step"]["detected_change_streams"] == 1
    assert summary["step"]["detection_delay_steps"]["mean"] == 20.0
