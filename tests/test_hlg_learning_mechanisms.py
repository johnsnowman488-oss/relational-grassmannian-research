import copy

import numpy as np
import pytest

from rgm.leptograph.m4.learning import (
    ConsolidationGate, EligibilityEvent, EligibilityLedger, ErrorChannel,
    ErrorRouter, LearningSignals, Level, ParameterRoute, Prediction,
    PredictionJournal, PredictionStatus, TargetObservation, TargetSchema,
    ValidationReceipt, fingerprint, replay_eligibility,
)


def schema(level=Level.L0, target_type="continuous", metric="mse", horizon=3):
    return TargetSchema("next_state", level, target_type, horizon, metric)


def prediction(target_schema, value=1.0, *, tick=2, cutoff=10.0):
    return Prediction(
        "p-1", target_schema.level, target_schema.name, "target-7",
        tick, 9.0, target_schema.horizon_ticks, cutoff, value,
        "model-fp", fingerprint(target_schema.__dict__),
    )


def target(value=1.5, *, observed_tick=3, observed_at=11.0):
    return TargetObservation("next_state", "target-7", value, 8.0,
                             observed_at, observed_tick, "source-1")


def event(event_id, tick, magnitude=1.0, *, event_time=None, observed_at=None,
          feature="f0", channel="c0", config="kernel-v1"):
    return EligibilityEvent(event_id, feature, channel,
                            float(tick if event_time is None else event_time),
                            float(tick if observed_at is None else observed_at),
                            tick, magnitude, config)


def test_prediction_is_distinct_and_starts_issued():
    p = prediction(schema())
    assert p.status is PredictionStatus.ISSUED
    assert p.level is Level.L0


def test_prediction_scoring_requires_future_observation():
    s = schema()
    journal = PredictionJournal()
    journal.issue(prediction(s))
    with pytest.raises(ValueError, match="already available"):
        journal.score("p-1", target(observed_at=10.0), s, evaluated_tick=3)


def test_prediction_scoring_rejects_pre_issue_tick():
    s = schema()
    journal = PredictionJournal()
    journal.issue(prediction(s))
    with pytest.raises(ValueError, match="after prediction issue"):
        journal.score("p-1", target(observed_tick=2), s, evaluated_tick=3)


def test_prediction_scoring_rejects_target_beyond_horizon():
    s = schema(horizon=1)
    journal = PredictionJournal()
    journal.issue(prediction(s, tick=2))
    with pytest.raises(ValueError, match="outside prediction horizon"):
        journal.score("p-1", target(observed_tick=4), s, evaluated_tick=4)


def test_prediction_scoring_records_outcome_without_turning_prediction_into_evidence():
    s = schema()
    journal = PredictionJournal()
    journal.issue(prediction(s, value=1.5))
    score = journal.score("p-1", target(1.5), s, evaluated_tick=3)
    assert score.value == 0.0
    assert score.outcome is PredictionStatus.CONFIRMED
    assert journal.get("p-1").status is PredictionStatus.SCORED
    assert journal.scores[0].target_source_id == "source-1"


def test_prediction_schema_fingerprint_is_enforced():
    s = schema()
    journal = PredictionJournal()
    journal.issue(prediction(s))
    changed = TargetSchema("next_state", Level.L0, "continuous", 3, "mae")
    with pytest.raises(ValueError, match="schema fingerprint"):
        journal.score("p-1", target(), changed, evaluated_tick=3)


def test_prediction_expiry_requires_elapsed_horizon():
    s = schema(horizon=2)
    journal = PredictionJournal()
    journal.issue(prediction(s, tick=2))
    with pytest.raises(ValueError):
        journal.expire("p-1", current_tick=4)
    journal.expire("p-1", current_tick=5)
    assert journal.get("p-1").status is PredictionStatus.EXPIRED


def test_categorical_accuracy_and_relation_exact_match():
    s = TargetSchema("next_state", Level.L1, "categorical", 2, "accuracy")
    journal = PredictionJournal()
    p = prediction(s, value="MOVE")
    journal.issue(p)
    score = journal.score("p-1", target("MOVE"), s, evaluated_tick=3)
    assert score.value == 1.0
    relation = TargetSchema("next_state", Level.L1, "relation", 2, "exact_match")
    journal2 = PredictionJournal()
    journal2.issue(prediction(relation, value=("A", "MOVE", "B")))
    assert journal2.score("p-1", target(("A", "MOVE", "B")), relation,
                          evaluated_tick=3).value == 0.0


def test_brier_score_requires_normalized_probabilities_and_one_hot_target():
    s = TargetSchema("next_state", Level.L2, "context", 2, "brier")
    journal = PredictionJournal()
    journal.issue(prediction(s, value=[0.8, 0.2]))
    score = journal.score("p-1", target([1.0, 0.0]), s, evaluated_tick=3)
    assert score.value == pytest.approx(0.04)


def test_learning_signals_remain_separate():
    signals = LearningSignals(temporal=0.1, relational=0.2, abstraction=0.3, task=0.4)
    assert signals.as_dict() == {
        "temporal": 0.1, "relational": 0.2, "abstraction": 0.3, "task": 0.4
    }


def test_error_router_only_updates_declared_parameter_families():
    router = ErrorRouter([
        ParameterRoute("temporal_readout", frozenset({ErrorChannel.TEMPORAL})),
        ParameterRoute("relation_encoder", frozenset({ErrorChannel.RELATIONAL})),
        ParameterRoute("context_head", frozenset({ErrorChannel.ABSTRACTION, ErrorChannel.TASK})),
    ])
    result = router.route(LearningSignals(0.1, 0.2, 0.3, 0.4))
    assert result["temporal_readout"] == {"temporal": 0.1}
    assert result["relation_encoder"] == {"relational": 0.2}
    assert result["context_head"] == {"abstraction": 0.3, "task": 0.4}


def test_integrity_failures_block_all_parameter_updates():
    router = ErrorRouter([ParameterRoute("all", frozenset(ErrorChannel))])
    assert router.route(LearningSignals(1, 1, 1, 1, ("FALSE_WITNESS",))) == {}


@pytest.mark.parametrize("values", [(-1, 0, 0, 0), (float("nan"), 0, 0, 0)])
def test_invalid_learning_residuals_rejected(values):
    with pytest.raises(ValueError):
        LearningSignals(*values)


def test_eligibility_is_event_resolved_and_decays_per_channel():
    ledger = EligibilityLedger(decay=0.5, capacity=4, config_fingerprint="kernel-v1")
    ledger.ingest(event("e1", 0, 2.0, feature="x", channel="slow"))
    ledger.ingest(event("e2", 0, 3.0, feature="x", channel="fast"))
    ledger.advance(2)
    values = ledger.values(prediction_cutoff_tick=2)
    assert values[("e1", "x", "slow")] == pytest.approx(0.5)
    assert values[("e2", "x", "fast")] == pytest.approx(0.75)


def test_late_arrival_does_not_backfill_event_time_credit():
    ledger = EligibilityLedger(decay=0.5, capacity=4, config_fingerprint="kernel-v1")
    ledger.advance(5)
    ledger.ingest(event("late", 5, 1.0, event_time=1.0, observed_at=5.0))
    assert ledger.values(prediction_cutoff_tick=4) == {}
    ledger.advance(6)
    assert ledger.values(prediction_cutoff_tick=6)[("late", "f0", "c0")] == pytest.approx(0.5)


def test_late_arrival_from_old_observed_tick_is_rejected():
    ledger = EligibilityLedger(decay=0.9, capacity=4, config_fingerprint="kernel-v1")
    ledger.advance(8)
    with pytest.raises(ValueError, match="no backfill"):
        ledger.ingest(event("late", 7))


def test_eligibility_capacity_exhaustion_is_explicit():
    ledger = EligibilityLedger(decay=0.9, capacity=1, config_fingerprint="kernel-v1")
    ledger.ingest(event("e1", 0))
    with pytest.raises(OverflowError):
        ledger.ingest(event("e2", 0))


def test_eligibility_configuration_fingerprint_is_enforced():
    ledger = EligibilityLedger(decay=0.9, capacity=2, config_fingerprint="kernel-v1")
    with pytest.raises(ValueError, match="fingerprint"):
        ledger.ingest(event("e1", 0, config="kernel-v2"))


def test_eligibility_snapshot_round_trip_and_tamper_detection():
    ledger = EligibilityLedger(decay=0.8, capacity=4, config_fingerprint="kernel-v1")
    ledger.ingest(event("e1", 0))
    ledger.advance(3)
    snap = ledger.snapshot()
    restored = EligibilityLedger(decay=0.8, capacity=4, config_fingerprint="kernel-v1")
    restored.restore(snap)
    assert restored.snapshot() == snap
    bad = copy.deepcopy(snap)
    bad["states"][0]["value"] = float("nan")
    with pytest.raises(ValueError):
        restored.restore(bad)


def test_deterministic_replay_matches_incremental_ledger():
    events = [event("e1", 0, 1.0), event("e2", 2, 2.0)]
    replay = replay_eligibility(events, decay=0.5, capacity=4,
                                config_fingerprint="kernel-v1", through_tick=3)
    ledger = EligibilityLedger(decay=0.5, capacity=4, config_fingerprint="kernel-v1")
    ledger.ingest(events[0])
    ledger.advance(2)
    ledger.ingest(events[1])
    ledger.advance(3)
    assert replay == ledger.values(prediction_cutoff_tick=3)


def test_candidate_is_inert_until_independent_pass_receipt():
    gate = ConsolidationGate({"weights": [1.0]}, evidence_watermark=10)
    original = gate.trusted_fingerprint
    candidate = gate.stage({"weights": [2.0]})
    assert gate.trusted_fingerprint == original
    receipt = gate.validate(protocol_fingerprint="protocol", partition_fingerprint="holdout",
                            criteria_fingerprint="criteria", evidence_watermark=10,
                            metrics={"loss": 0.1}, passed=True)
    assert receipt.candidate_fingerprint == candidate
    assert gate.promote() != original


def test_failed_candidate_cannot_promote():
    gate = ConsolidationGate({"w": [0.0]})
    gate.stage({"w": [1.0]})
    gate.validate(protocol_fingerprint="p", partition_fingerprint="v",
                   criteria_fingerprint="c", evidence_watermark=0,
                   metrics={"loss": 1.0}, passed=False)
    with pytest.raises(ValueError, match="failed"):
        gate.promote()
    gate.rollback()
    assert gate.trusted == {"w": [0.0]}


def test_new_evidence_invalidates_existing_validation_receipt():
    gate = ConsolidationGate({"w": [0.0]}, evidence_watermark=4)
    gate.stage({"w": [1.0]})
    gate.validate(protocol_fingerprint="p", partition_fingerprint="v",
                  criteria_fingerprint="c", evidence_watermark=4,
                  metrics={"loss": 0.1}, passed=True)
    gate.observe_new_evidence(5)
    with pytest.raises(ValueError, match="invalidated"):
        gate.promote()


def test_receipt_cannot_be_reused_for_different_candidate():
    gate = ConsolidationGate({"w": [0.0]})
    gate.stage({"w": [1.0]})
    gate.validate(protocol_fingerprint="p", partition_fingerprint="v",
                  criteria_fingerprint="c", evidence_watermark=0,
                  metrics={"loss": 0.1}, passed=True)
    gate.stage({"w": [2.0]})
    with pytest.raises(ValueError):
        gate.promote()


def test_rollback_preserves_newer_evidence_watermark_and_trusted_model():
    gate = ConsolidationGate({"w": [0.0]}, evidence_watermark=2)
    gate.stage({"w": [1.0]})
    gate.observe_new_evidence(3)
    assert gate.rollback() == {"w": [0.0]}
    assert gate.evidence_watermark == 3


def test_candidate_parameter_mutation_cannot_mutate_trusted_incumbent():
    initial = {"weights": [1.0]}
    gate = ConsolidationGate(initial)
    initial["weights"][0] = 99.0
    assert gate.trusted == {"weights": [1.0]}
    candidate = {"weights": [2.0]}
    gate.stage(candidate)
    candidate["weights"][0] = 88.0
    assert gate.candidate == {"weights": [2.0]}




def test_task_channel_scores_prior_error_probability_and_learns_even_on_correct_outcome():
    from rgm.leptograph.m4.learning import LearningRuntime

    learning = LearningRuntime()
    before = learning.task_outcomes.snapshot()
    assert learning.task_outcomes.predict_error_probability("task3") == pytest.approx(0.5)

    learning.observe_task_error("task3", 0.0, learn=True)

    assert learning.last_signals.task == pytest.approx(0.25)
    assert learning.task_outcomes.snapshot() != before
    assert learning.task_outcomes.error_rate("task3") == 0.0
    assert learning.task_outcomes.predict_error_probability("task3") == pytest.approx(1 / 3)


def test_no_task_ablation_suppresses_task_calibration_updates_but_keeps_error_measurement():
    from rgm.leptograph.m4.learning import LearningRuntime

    learning = LearningRuntime(enabled_channels={
        ErrorChannel.TEMPORAL, ErrorChannel.RELATIONAL, ErrorChannel.ABSTRACTION,
    })
    learning.observe_task_error("task5", 0.0, learn=True)

    assert learning.last_signals.task == pytest.approx(0.25)
    assert learning.task_outcomes.snapshot() == {}


def test_task_channel_rejects_non_binary_outcome_targets():
    from rgm.leptograph.m4.learning import LearningRuntime

    with pytest.raises(ValueError, match="binary-range"):
        LearningRuntime().observe_task_error("task3", 1.5)
