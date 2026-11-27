import copy
import hashlib

import pytest

from rgm.memory import SOEMemory
from rgm.leptograph.m4.composition import Entity, RelationInstance, RelationType
from rgm.leptograph.m4.evidence import NaryEvent, Participant
from rgm.leptograph.m4.hierarchical import (
    CompositeLifecycle, HLAAdapter, HLBAdapter, HierarchicalRuntimeDirector,
)
from rgm.leptograph.m4.learning import (
    EligibilityEvent, ErrorChannel, LearningRuntime,
)
from rgm.leptograph.m4.soe_bridge import SOEHierarchyBridge


class Runtime:
    def __init__(self, banks):
        self.state = {
            "level_states": [
                {"u": m.snapshot().reshape(-1).tolist(),
                 "chi": [0.0] * m.channel_count, "t": 0.0}
                for m in banks
            ],
            "step_count": 0,
        }

    def get_state(self):
        return copy.deepcopy(self.state)

    def step(self, feedback_by_level=None):
        candidate = self.get_state()
        for level, values in (feedback_by_level or {}).items():
            candidate["level_states"][level]["u"] = list(values)
        candidate["step_count"] += 1
        self.state = candidate
        return self.get_state()

    def checkpoint(self):
        return self.get_state()

    def restore(self, state):
        self.state = copy.deepcopy(state)


def system(architecture="HLB"):
    banks = [
        SOEMemory(feature_dim=2, decay_rates=[0.1, 0.4]),
        SOEMemory(feature_dim=3, decay_rates=[0.2, 0.7]),
        SOEMemory(feature_dim=4, decay_rates=[0.05, 0.3]),
    ]
    runtime = Runtime(banks)
    bridge = SOEHierarchyBridge(runtime, banks, dt=0.01)
    adapter = HLAAdapter(bridge, feature_dims=[2, 3, 4]) if architecture == "HLA" else HLBAdapter(bridge)
    return runtime, adapter, HierarchicalRuntimeDirector(adapter)


def relation(rid, name="located_at", *, context="home", observed_at=1.0, event_time=1.0):
    subject = Entity("person-1", "person")
    obj = Entity("place-1", "place")
    signature = RelationType(name, "person", "place")
    return RelationInstance(rid, signature, subject, obj, event_time, observed_at,
                            context=context, provenance=f"source:{rid}")


def nary(eid, event_type="gave", *, recipient="fred", context="home",
         observed_at=1.0, event_time=1.0):
    payload = eid.encode()
    return NaryEvent(
        eid, event_type,
        (Participant("giver", "mary", "person"),
         Participant("object", "cake", "object"),
         Participant("recipient", recipient, "person")),
        event_time, observed_at, "babi-fixture", f"fixture://{eid}",
        hashlib.sha256(payload).hexdigest(), context=context,
    )


def eligibility(event_id="e1", tick=1):
    return EligibilityEvent(event_id, "feature-1", "slow", float(tick), float(tick),
                            tick, 1.0, "h1-soe-eligibility-v1")


def seed(runtime):
    runtime.fit_relation_patterns([relation("fit-r", "located_at")], partition="fit")
    runtime.fit_event_role_patterns([nary("fit-e")], partition="fit")


def test_hla_and_hlb_issue_and_score_semantic_predictions_in_live_cycle():
    for architecture in ("HLA", "HLB"):
        _, adapter, director = system(architecture)
        seed(adapter.learning)
        observed_relation = relation("obs-r", "located_at", observed_at=1.0)
        observed_event = nary("obs-e", observed_at=1.0)
        kwargs = ({"learning_relations": (observed_relation,)}
                  if architecture == "HLA" else {"relation_records": ((0, observed_relation),)})
        result = director.exchange(
            event_time=1.0, observed_at=1.0, event_features={0: [0.5, 0.25]},
            prediction_context="home",
            nary_events=(observed_event,), **kwargs,
        )
        assert {p.target_name for p in result["predictions"]} == {
            "next_relation_pattern", "next_event_role_pattern"
        }
        scores = adapter.learning.predictions.scores
        assert len(scores) == 2
        assert all(score.value == 0.0 for score in scores)
        if architecture == "HLA":
            assert not hasattr(adapter, "store")
            assert adapter.learning.event_roles.predict("home").event_type == "gave"
        else:
            assert adapter.store.count == 1
            assert adapter.evidence.event_ids == ("obs-e",)


def test_score_only_exchange_scores_predictions_without_updating_learners():
    for architecture in ("HLA", "HLB"):
        _, adapter, director = system(architecture)
        seed(adapter.learning)
        roles_before = adapter.learning.event_roles.snapshot()
        relations_before = adapter.learning.relations.snapshot()
        temporal_before = adapter.learning.temporal_credit.snapshot()
        task_before = adapter.learning.task_outcomes.snapshot()
        eligibility_before = adapter.learning.eligibility.snapshot()

        result = director.exchange(
            event_time=1.0, observed_at=1.0, prediction_context="home",
            nary_events=(nary("score-only-event", event_type="moved", observed_at=1.0),),
            eligibility_events=(eligibility("score-only-credit"),),
            temporal_error=0.5, task_outcome=("babi-validation", 1.0),
            learn=False,
        )

        assert any(p.target_name == "next_event_role_pattern" for p in result["predictions"])
        assert len(adapter.learning.predictions.scores) == 1
        assert adapter.learning.event_roles.snapshot() == roles_before
        assert adapter.learning.relations.snapshot() == relations_before
        assert adapter.learning.temporal_credit.snapshot() == temporal_before
        assert adapter.learning.task_outcomes.snapshot() == task_before
        assert adapter.learning.eligibility.snapshot() == eligibility_before
        assert adapter.ticks == 1


def test_semantic_relation_and_nary_role_errors_update_only_their_own_learners():
    _, adapter, director = system("HLB")
    seed(adapter.learning)
    relation_before = adapter.learning.relations.snapshot()
    roles_before = adapter.learning.event_roles.snapshot()
    director.exchange(
        event_time=1.0, observed_at=1.0, prediction_context="home",
        relation_records=((0, relation("wrong-r", "visited")),),
        nary_events=(nary("wrong-e", event_type="moved",
                          recipient="destination", observed_at=1.0),),
    )
    scores = {score.metric: score.value for score in adapter.learning.predictions.scores}
    assert scores["exact_match"] == 1.0
    assert adapter.learning.relations.snapshot() != relation_before
    assert adapter.learning.event_roles.snapshot() != roles_before
    assert adapter.learning.last_signals.abstraction == 1.0


def test_fit_partition_is_required_for_semantic_learner_initialization():
    learner = LearningRuntime()
    with pytest.raises(ValueError, match="fit partition"):
        learner.fit_relation_patterns([relation("r")], partition="validation")
    with pytest.raises(ValueError, match="fit partition"):
        learner.fit_event_role_patterns([nary("e")], partition="confirmatory")


def test_prediction_error_replay_reissues_incumbent_forecasts_after_rollback():
    learner = LearningRuntime()
    seed(learner)
    checkpoint = learner.snapshot()
    learner.begin_tick(tick=0, observed_at=0.0, context="home")
    learner.observe_relation(relation("new-r", "visited", observed_at=1.0), tick=1)
    learner.observe_nary_event(nary("new-e", event_type="moved", observed_at=1.0), tick=1)
    assert len(learner.predictions.scores) == 2

    learner.restore(checkpoint, preserve_observations=True)
    assert len(learner.predictions.scores) == 2
    assert {s.value for s in learner.predictions.scores} == {1.0}
    assert len(learner.relations.snapshot()) == 1
    assert len(learner.event_roles.snapshot()) == 1


def test_error_channel_ablations_isolate_the_permitted_learner_updates():
    all_on = LearningRuntime()
    no_relational = LearningRuntime(enabled_channels=frozenset(ErrorChannel) - {ErrorChannel.RELATIONAL})
    seed(all_on)
    seed(no_relational)

    for index, learner in enumerate((all_on, no_relational)):
        learner.begin_tick(tick=0, observed_at=0.0, context="home")
        learner.observe_relation(relation(f"r-{index}", "visited", observed_at=1.0), tick=1)
    assert all_on.relations.snapshot() != no_relational.relations.snapshot()

    all_on.observe_eligibility(eligibility("temporal-on"))
    no_temporal = LearningRuntime(enabled_channels=frozenset(ErrorChannel) - {ErrorChannel.TEMPORAL})
    no_temporal.observe_eligibility(eligibility("temporal-off"))
    all_on.advance_temporal(1)
    no_temporal.advance_temporal(1)
    all_on.observe_temporal_error(0.5, tick=1)
    no_temporal.observe_temporal_error(0.5, tick=1)
    assert all_on.temporal_credit.snapshot()["weights"]
    assert not no_temporal.temporal_credit.snapshot()["weights"]

    no_task = LearningRuntime(enabled_channels=frozenset(ErrorChannel) - {ErrorChannel.TASK})
    all_on.observe_task_error("task-x", 1.0)
    no_task.observe_task_error("task-x", 1.0)
    assert all_on.task_outcomes.error_rate("task-x") == 1.0
    assert no_task.task_outcomes.error_rate("task-x") is None


def test_integrated_candidate_rollback_preserves_and_replays_all_observations():
    runtime, adapter, director = system("HLB")
    seed(adapter.learning)
    lifecycle = CompositeLifecycle(director)
    lifecycle.checkpoint()

    result = director.exchange(
        event_time=1.0, observed_at=1.0, event_features={0: [1.0, 0.0]},
        prediction_context="home",
        relation_records=((0, relation("source-rel", "visited", observed_at=1.0)),),
        nary_events=(nary("source-event", event_type="moved", observed_at=1.0),),
        eligibility_events=(eligibility("credit-e"),),
        temporal_error=0.5, task_outcome=("babi-task-5", 1.0),
    )
    assert len(result["predictions"]) == 2
    assert runtime.state["step_count"] == 1
    assert adapter.evidence.event_ids == ("source-event",)
    assert adapter.learning.temporal_credit.snapshot()["weights"]

    lifecycle.rollback()

    # Runtime inputs are replayed through the restored incumbent, while source
    # observations and their error-attributed learning updates remain available.
    assert runtime.state["step_count"] == 1
    assert director.event_tick == 1
    assert adapter.store.records(cutoff=2.0)[0].instance_id == "source-rel"
    assert adapter.evidence.event_ids == ("source-event",)
    assert adapter.learning.eligibility.values(prediction_cutoff_tick=1)
    assert adapter.learning.temporal_credit.snapshot()["weights"]
    assert adapter.learning.task_outcomes.error_rate("babi-task-5") == 1.0
    assert len(adapter.learning.predictions.scores) == 2


def test_independent_promotion_binds_learning_state_and_rejects_stale_candidate():
    _, adapter, director = system("HLB")
    seed(adapter.learning)
    lifecycle = CompositeLifecycle(director)
    lifecycle.checkpoint()
    director.exchange(event_time=1.0, observed_at=1.0, prediction_context="home",
                      relation_records=((0, relation("promotion-r", "located_at")),))
    record = {
        "validation_id": "independent-learning-validation",
        "passed": True, "independent": True, "partition": "validation",
        "candidate_fingerprint": lifecycle.candidate_fingerprint(),
        "protocol_fingerprint": "a" * 64,
        "criteria_fingerprint": "b" * 64,
        "data_manifest_fingerprint": "c" * 64,
        "metrics": {"relation_exact_match": 1.0},
    }
    assert lifecycle.promote(record) == 1
    assert "learning" in lifecycle._trusted["director"]["adapter"]
    director.exchange(event_time=2.0, observed_at=2.0,
                      relation_records=((0, relation("after-promotion-r", "visited", observed_at=2.0)),))
    with pytest.raises(ValueError, match="fingerprint"):
        lifecycle.promote(record)






def test_pattern_prediction_index_tracks_updates_and_transaction_rollback():
    from rgm.leptograph.m4.learning import _PatternCounter

    counter = _PatternCounter()
    counter.observe("context", "pattern-b")
    counter.observe("context", "pattern-b")
    counter.observe("context", "pattern-a")
    assert counter.predict("context") == "pattern-b"

    counter.begin_transaction()
    counter.observe("context", "pattern-a")
    counter.observe("context", "pattern-a")
    counter.observe("context", "pattern-c")
    assert counter.predict("context") == "pattern-a"
    counter.rollback_transaction()

    assert counter.counts["context"] == {"pattern-a": 1, "pattern-b": 2}
    assert counter.predict("context") == "pattern-b"

    restored = _PatternCounter()
    restored.restore(counter.snapshot())
    assert restored.predict("context") == "pattern-b"


def test_prediction_scoring_uses_index_not_full_prediction_scan():
    _, adapter, _ = system("HLA")
    learner = adapter.learning
    seed(learner)

    class NoValuesDict(dict):
        def values(self):
            raise AssertionError("prediction hot path scanned full prediction history")

    learner.predictions._predictions = NoValuesDict(learner.predictions._predictions)
    learner.begin_tick(tick=0, observed_at=0.0, context="home")
    learner.observe_relation(relation("indexed-rel", "visited", observed_at=1.0), tick=1)
    learner.observe_nary_event(
        nary("indexed-event", event_type="moved", observed_at=1.0), tick=1
    )
    assert len(learner.predictions.scores) == 2


def test_incremental_learning_transaction_rolls_back_only_touched_state():
    learner = LearningRuntime()
    learner.task_outcomes.observe_error("existing-task", 0.0)
    existing_key = '["prior-event","prior-feature","slow"]'
    learner.temporal_credit.weights[existing_key] = -0.25
    prior_journal_count = len(learner._observation_journal)

    checkpoint = learner.transaction_checkpoint()
    learner.temporal_credit.update(0.5, {
        ("prior-event", "prior-feature", "slow"): 0.5,
        ("new-event", "new-feature", "fast"): 1.0,
    })
    learner.task_outcomes.observe_error("existing-task", 1.0)
    learner.task_outcomes.observe_error("new-task", 1.0)
    learner._observation_journal.append({"kind": "test-only", "value": 1})

    learner.rollback_transaction(checkpoint)

    assert learner.temporal_credit.weights == {existing_key: -0.25}
    assert learner.task_outcomes.outcomes == {"existing-task": [0]}
    assert len(learner._observation_journal) == prior_journal_count
    assert learner.predictions._transaction_log is None
    assert learner.temporal_credit._transaction_log is None
    assert learner.task_outcomes._transaction_log is None


def test_failed_exchange_rolls_back_model_but_preserves_hlb_source_journals(monkeypatch):
    runtime, adapter, director = system("HLB")
    seed(adapter.learning)
    before_learning = adapter.learning.snapshot()
    before_runtime = runtime.get_state()
    before_ticks = adapter.ticks
    before_journal_count = len(director._observation_journal)

    original_observe_task_error = adapter.learning.observe_task_error

    def fail_after_task_observation(task_key, error, *, learn=True):
        original_observe_task_error(task_key, error, learn=learn)
        raise RuntimeError("injected post-learning failure")

    monkeypatch.setattr(
        adapter.learning, "observe_task_error", fail_after_task_observation
    )

    observed_relation = relation("persisted-source-relation", "visited")
    observed_event = nary("persisted-source-event", event_type="moved")
    with pytest.raises(RuntimeError, match="injected post-learning failure"):
        director.exchange(
            event_time=1.0, observed_at=1.0,
            event_features={0: [0.25, 0.75]},
            prediction_context="home", observed_context="work",
            relation_records=((0, observed_relation),),
            nary_events=(observed_event,),
            eligibility_events=(eligibility("exchange-credit"),),
            temporal_error=0.5,
            task_outcome=("injected-failure-task", 1.0),
        )

    assert runtime.get_state() == before_runtime
    assert adapter.ticks == before_ticks
    assert director.event_tick == 0
    assert len(director._observation_journal) == before_journal_count
    assert adapter.learning.snapshot() == before_learning
    # Source evidence intentionally survives candidate rollback.
    assert adapter.evidence.event_ids == ("persisted-source-event",)
    assert adapter.store.count == 1
    assert adapter.recover_evidence(
        "persisted-source-event", observation_cutoff=2.0
    ) == (observed_event,)


def test_forecast_context_is_not_inferred_from_the_current_target_observation():
    _, adapter, director = system("HLB")
    seed(adapter.learning)
    observed = relation("no-leak-r", "located_at", observed_at=1.0)
    result = director.exchange(
        event_time=1.0, observed_at=1.0,
        relation_records=((0, observed),),
        nary_events=(nary("no-leak-e", observed_at=1.0),),
    )
    assert result["predictions"] == ()
    assert adapter.learning.predictions.scores == ()


def test_semantic_predictions_include_exact_entity_and_role_bindings():
    learner = LearningRuntime()
    seed(learner)
    relation_pattern = learner.relations.predict("home")
    role_pattern = learner.event_roles.predict("home")
    assert relation_pattern.subject_id == "person-1"
    assert relation_pattern.object_id == "place-1"
    assert ("recipient", "fred", "person") in role_pattern.roles


def test_l0_feature_and_l2_context_predictions_are_issued_and_error_routed():
    learner = LearningRuntime()
    learner.fit_level0_predictor([[0.0, 0.0], [0.0, 2.0]], partition="fit")
    learner.fit_context_transitions([("home", "home")], partition="fit")
    issued = learner.begin_tick(tick=0, observed_at=0.0, context="home")
    assert {p.level.value for p in issued} == {"L0_GROUNDING", "L2_CONTEXT"}
    assert {p.target_name for p in issued} == {"next_l0_features", "next_context"}

    learner.advance_temporal(1)
    learner.observe_eligibility(eligibility("l0-credit"))
    feature_error = learner.observe_level0_features(
        [2.0, 1.0], event_time=1.0, observed_at=1.0, tick=1,
    )
    context_error = learner.observe_context_transition(
        "home", "work", source_id="context-event", event_time=1.0,
        observed_at=1.0, tick=1,
    )
    assert feature_error == pytest.approx(2.0)
    assert context_error == 1.0
    assert learner.level0.update_count == 1
    assert learner.temporal_credit.snapshot()["weights"]
    assert sum(sum(bucket.values()) for bucket in learner.context_transitions.snapshot().values()) == 2


def test_l0_and_l2_predictions_are_regenerated_and_learned_after_candidate_rollback():
    learner = LearningRuntime()
    learner.fit_level0_predictor([[0.0, 0.0]], partition="fit")
    learner.fit_context_transitions([("home", "home")], partition="fit")
    checkpoint = learner.snapshot()

    learner.begin_tick(tick=0, observed_at=0.0, context="home")
    learner.advance_temporal(1)
    learner.observe_eligibility(eligibility("rollback-credit"))
    learner.observe_level0_features([1.0, 0.0], event_time=1.0,
                                    observed_at=1.0, tick=1)
    learner.observe_context_transition("home", "work", source_id="rollback-context",
                                       event_time=1.0, observed_at=1.0, tick=1)
    learner.restore(checkpoint, preserve_observations=True)

    scored = {learner.predictions.get(s.prediction_id).target_name: s.value
              for s in learner.predictions.scores}
    assert scored["next_l0_features"] == pytest.approx(0.5)
    assert scored["next_context"] == 0.0
    assert learner.level0.update_count == 1
    assert sum(sum(bucket.values()) for bucket in learner.context_transitions.snapshot().values()) == 2


def test_director_runs_all_three_prediction_levels_before_observation_update():
    _, adapter, director = system("HLB")
    seed(adapter.learning)
    adapter.learning.fit_level0_predictor([[0.0, 0.0]], partition="fit")
    adapter.learning.fit_context_transitions([("home", "home")], partition="fit")
    result = director.exchange(
        event_time=1.0, observed_at=1.0,
        event_features={0: [1.0, 0.0]},
        prediction_context="home", observed_context="work",
        relation_records=((0, relation("three-level-r", "visited")),),
        nary_events=(nary("three-level-e", event_type="moved", recipient="bill"),),
        eligibility_events=(eligibility("three-level-credit"),),
    )
    assert {p.level.value for p in result["predictions"]} == {
        "L0_GROUNDING", "L1_RELATIONAL", "L2_CONTEXT"
    }
    assert len(result["predictions"]) == 4
    assert len(adapter.learning.predictions.scores) == 4
    assert result["learning_errors"] == {
        "relational": 1.0, "abstraction": 1.0, "temporal": 0.5, "task": 0.0
    }
    assert adapter.learning.level0.update_count == 1
    assert adapter.learning.temporal_credit.snapshot()["weights"]
