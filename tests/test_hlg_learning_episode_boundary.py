from rgm.leptograph.m4.learning import EligibilityEvent, LearningRuntime


def _event(event_id: str, tick: int) -> EligibilityEvent:
    return EligibilityEvent(
        event_id=event_id,
        feature_id="soe_l0_c0",
        channel="soe_l0_c0",
        event_time=float(tick),
        observed_at=float(tick),
        observed_tick=tick,
        magnitude=1.0,
        config_fingerprint="episode-test-soe",
    )


def test_episode_boundary_resets_eligibility_and_replays_deterministically():
    runtime = LearningRuntime(
        eligibility_decay=0.9,
        eligibility_capacity=8,
        eligibility_config_fingerprint="episode-test-soe",
    )
    checkpoint = runtime.snapshot()

    runtime.advance_temporal(1)
    runtime.observe_eligibility(_event("story-a:event-1", 1))
    runtime.reset_episode_eligibility(tick=1, observed_at=1.0)

    runtime.advance_temporal(2)
    runtime.observe_eligibility(_event("story-b:event-1", 2))
    runtime.observe_temporal_error(0.5, tick=2)

    expected_eligibility = runtime.eligibility.values(prediction_cutoff_tick=2)
    expected_credit = runtime.temporal_credit.snapshot()
    assert {key[0] for key in expected_eligibility} == {"story-b:event-1"}

    runtime.restore(checkpoint, preserve_observations=True)
    assert runtime.eligibility.values(prediction_cutoff_tick=2) == expected_eligibility
    assert runtime.temporal_credit.snapshot() == expected_credit


def test_episode_boundary_cannot_move_eligibility_clock_backwards():
    runtime = LearningRuntime(
        eligibility_decay=0.9,
        eligibility_capacity=8,
        eligibility_config_fingerprint="episode-test-soe",
    )
    runtime.advance_temporal(3)
    try:
        runtime.eligibility.reset(tick=2)
    except ValueError:
        pass
    else:
        raise AssertionError("episode reset must not move the eligibility clock backwards")
