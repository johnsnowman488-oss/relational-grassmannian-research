import copy

from rgm.experiments.babi_expansion_adapters import (
    ExpansionStory, ExpansionQuery, GoldLabel,
    Task11MentionEvent, Task14TemporalEvent, Task19SpatialEdge,
)
from rgm.experiments.babi_expansion_runtime import (
    BabiExpansionRuntime, ExpansionForecasts, target_contract,
    to_nary_event, to_spatial_relation, to_task_relations,
)
from rgm.leptograph.m4.hierarchical import HLAAdapter, HLBAdapter
from rgm.leptograph.m4.soe_bridge import SOEHierarchyBridge
from rgm.leptograph.m4.learning import Level
from rgm.memory import SOEMemory


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

    def checkpoint(self):
        return self.get_state()

    def restore(self, state):
        self.state = copy.deepcopy(state)

    def step(self, feedback_by_level=None):
        candidate = self.get_state()
        for level, values in (feedback_by_level or {}).items():
            candidate["level_states"][level]["u"] = list(values)
        candidate["step_count"] += 1
        self.state = candidate
        return self.get_state()


def make_adapter(kind):
    banks = [
        SOEMemory(feature_dim=2, decay_rates=[0.1, 0.4]),
        SOEMemory(feature_dim=3, decay_rates=[0.2, 0.7]),
        SOEMemory(feature_dim=4, decay_rates=[0.05, 0.3]),
    ]
    bridge = SOEHierarchyBridge(Runtime(banks), banks, dt=0.01)
    return HLAAdapter(bridge, feature_dims=[2, 3, 4]) if kind == "HLA" else HLBAdapter(bridge)


def test_task_event_mapping_preserves_nary_roles_and_provenance():
    story = ExpansionStory("task11/fit/story000001", 11, (
        Task11MentionEvent("e1", "Mary", False, "kitchen", 1, "train#1"),
        Task11MentionEvent("e2", "she", True, "hallway", 2, "train#2"),
    ), ())
    mapped = to_nary_event(story, story.events[1])
    assert mapped.event_type == "ENTITY_LOCATION_MENTION"
    assert mapped.role("mention").entity_id == "she"
    assert mapped.role("location").entity_id == "hallway"
    assert not any(participant.role in {"entity", "antecedent"} for participant in mapped.participants)
    assert mapped.provenance == "babi-v1.2-task-11"
    assert mapped.source_locator == "train#2"
    assert len(mapped.payload_digest) == 64


def test_task14_event_time_is_not_observation_time():
    story = ExpansionStory("task14/fit/story000001", 14, (
        Task14TemporalEvent("e1", "mary", "kitchen", "yesterday", (0, 1), 1, "train#1"),
        Task14TemporalEvent("e2", "mary", "garden", "this evening", (3, 2), 2, "train#2"),
    ), ())
    mapped = to_nary_event(story, story.events[1])
    assert mapped.event_time == 0.003
    assert mapped.observed_at == 2.0
    assert mapped.observed_at >= mapped.event_time



def test_task11_coreference_is_not_fabricated_during_ingestion():
    story = ExpansionStory("task11/fit/story000001", 11, (
        Task11MentionEvent("m1", "Mary", False, "kitchen", 1, "train#1"),
        Task11MentionEvent("m2", "she", True, "hallway", 2, "train#2"),
    ), ())
    assert to_task_relations(story, story.events[1]) == ()


def test_task14_temporal_precedence_is_materialized_with_both_witnesses():
    story = ExpansionStory("task14/fit/story000001", 14, (
        Task14TemporalEvent("later", "mary", "garden", "this evening", (3, 1), 1, "train#1"),
        Task14TemporalEvent("earlier", "mary", "kitchen", "yesterday", (0, 2), 2, "train#2"),
    ), ())
    edge, = to_task_relations(story, story.events[1], prior_temporal_events=(story.events[0],))
    assert edge.relation_type.name == "before"
    assert edge.subject.entity_id == "earlier"
    assert edge.object.entity_id == "later"
    assert edge.provenance == "train#2|train#1"


def test_runtime_rejects_query_forecast_issued_at_or_after_query_cutoff():
    import pytest
    query = ExpansionQuery("q1", 11, 5, "train#5", entity="mary")
    forecasts = ExpansionForecasts(11)
    with pytest.raises(ValueError, match="query target and its evidence cutoff"):
        forecasts.issue_query_forecasts(
            query, issued_tick=4, issued_at=5.0, evidence_cutoff=5.0,
            l0_value="she", l1_value=("she", "mary"), l2_value="kitchen",
            answer_value="kitchen", model_fingerprint="model-v1",
        )

def test_task19_relation_orientation_is_encoded_in_typed_edge():
    event = Task19SpatialEdge("e1", "kitchen", "hallway", "east", 1, "train#1")
    relation = to_spatial_relation(event)
    assert relation.subject.entity_id == "kitchen"
    assert relation.object.entity_id == "hallway"
    assert relation.relation_type.name == "spatial_east"
    assert relation.provenance == "train#1"
    from rgm.experiments.babi_expansion_runtime import to_spatial_relations
    forward, inverse = to_spatial_relations(event)
    assert (forward.subject.entity_id, forward.object.entity_id) == ("kitchen", "hallway")
    assert (inverse.subject.entity_id, inverse.object.entity_id) == ("hallway", "kitchen")
    assert inverse.relation_type.name == "spatial_west"


def test_task_specific_prediction_contracts_bind_l0_l1_l2_and_answer_levels():
    expected = {
        11: ("mention_binding", "coreference_edge", "entity_state", "location_answer"),
        14: ("temporal_anchor", "temporal_precedence", "temporal_context", "before_location_answer"),
        19: ("spatial_edge", "path_composition", "route_context", "ordered_route_answer"),
    }
    for task_id, names in expected.items():
        contract = target_contract(task_id)
        assert tuple(s.name.rsplit(".", 1)[-1] for s in
                     (contract.l0, contract.l1, contract.l2, contract.answer)) == names
        assert (contract.l0.level, contract.l1.level, contract.l2.level, contract.answer.level) == (
            Level.L0, Level.L1, Level.L2, Level.L2
        )


def test_prediction_contract_rejects_same_cutoff_and_scores_only_post_cutoff_labels():
    query = ExpansionQuery("q1", 19, 4, "test#4", start_location="a", end_location="b")
    forecasts = ExpansionForecasts(19)
    predictions = forecasts.issue_query_forecasts(
        query, issued_tick=3, issued_at=3.0, evidence_cutoff=3.0,
        l0_value="east", l1_value=("east",), l2_value=("a", "b"),
        answer_value="e", model_fingerprint="model-v1",
    )
    assert len(predictions) == 4
    label = GoldLabel("q1", "e", (1, 2), "test#4")
    scored = forecasts.score_query(query, label, evaluated_tick=4, observed_at=4.0)
    assert scored["task19.answer.ordered_route_answer"]["value"] == 1.0
    assert forecasts.journal.scores[-1].target_source_id == "test#4"


def test_hla_hlb_runtime_ingestion_uses_same_task_contract_and_recovers_witnesses():
    story = ExpansionStory("task19/fit/story000001", 19, (
        Task19SpatialEdge("edge1", "a", "b", "east", 1, "train#1"),
        Task19SpatialEdge("edge2", "b", "c", "north", 2, "train#2"),
    ), ())
    results = []
    for kind in ("HLA", "HLB"):
        adapter = make_adapter(kind)
        runtime = BabiExpansionRuntime(adapter)
        outputs = runtime.ingest_story(story)
        assert [item["event_id"] for item in outputs] == ["edge1", "edge2"]
        assert all(not item["abstained"] for item in outputs)
        recovered = runtime.recover_witness("edge1", observation_cutoff=1.0)
        assert len(recovered) == 1
        assert recovered[0].role("direction").entity_id == "east"
        results.append([item["status"] for item in outputs])
    assert results[0] == results[1]


def test_runtime_is_story_scoped_and_cannot_leak_across_story_boundaries():
    first = ExpansionStory("task11/fit/story000001", 11, (
        Task11MentionEvent("e1", "Mary", False, "kitchen", 1, "train#1"),
    ), ())
    second = ExpansionStory("task11/fit/story000002", 11, (
        Task11MentionEvent("e2", "Mary", False, "garden", 1, "train#2"),
    ), ())
    runtime = BabiExpansionRuntime(make_adapter("HLA"))
    runtime.ingest_story(first)
    import pytest
    with pytest.raises(RuntimeError, match="story-scoped"):
        runtime.ingest_story(second)


def test_expansion_runtime_explicit_non_learning_mode_keeps_learner_parameters_frozen():
    story = ExpansionStory("task19/fit/story000003", 19, (
        Task19SpatialEdge("edge1", "a", "b", "east", 1, "train#1"),
        Task19SpatialEdge("edge2", "b", "c", "north", 2, "train#2"),
    ), ())
    adapter = make_adapter("HLB")
    runtime = BabiExpansionRuntime(adapter, learning_enabled=False)

    def learner_parameters():
        learning = adapter.learning
        return {
            "level0": learning.level0.snapshot(),
            "relations": learning.relations.snapshot(),
            "event_roles": learning.event_roles.snapshot(),
            "contexts": learning.context_transitions.snapshot(),
            "task": learning.task_outcomes.snapshot(),
            "temporal": learning.temporal_credit.snapshot(),
        }

    before = learner_parameters()
    outputs = runtime.ingest_story(story)
    after = learner_parameters()
    assert len(outputs) == 2
    assert all(not item["abstained"] for item in outputs)
    assert runtime.learning_enabled is False
    assert adapter.ticks == 2
    assert before == after


def _task11_learning_story(story_id="task11/fit/learning-only"):
    return ExpansionStory(story_id, 11, (
        Task11MentionEvent("m1", "Mary", False, "kitchen", 1, "train#1", "female"),
        Task11MentionEvent("m2", "John", False, "garden", 2, "train#2", "male"),
        Task11MentionEvent("m3", "she", True, "office", 3, "train#3", "female"),
        Task11MentionEvent("m4", "he", True, "hallway", 4, "train#4", "male"),
    ), ())


def _task11_parameter_state(adapter):
    return {
        "relations": adapter.learning.relations.snapshot(),
        "event_roles": adapter.learning.event_roles.snapshot(),
        "contexts": adapter.learning.context_transitions.snapshot(),
    }


def test_task11_l0_l1_l2_weak_targets_update_learners_but_never_source_evidence():
    story = _task11_learning_story()
    for kind in ("HLA", "HLB"):
        adapter = make_adapter(kind)
        runtime = BabiExpansionRuntime(adapter, learning_enabled=True)
        before = _task11_parameter_state(adapter)
        outputs = runtime.ingest_story(story)
        after = _task11_parameter_state(adapter)

        assert len(outputs) == 4
        assert all(not item["abstained"] for item in outputs)
        assert before["event_roles"] != after["event_roles"]
        assert before["relations"] != after["relations"]
        assert before["contexts"] != after["contexts"]

        # The derived binding/edge targets are routed only into LearningRuntime.
        # Evidence recovery returns source-grounded mention events without any
        # inferred entity or antecedent participant.
        for event_id in ("m1", "m2", "m3", "m4"):
            raw_event, = runtime.recover_witness(event_id, observation_cutoff=4.0)
            assert raw_event.event_id == event_id
            assert not any(
                participant.role in {"entity", "antecedent_event"}
                for participant in raw_event.participants
            )
        if kind == "HLB":
            assert adapter.store.count == 0

        journal = adapter.learning._observation_journal
        role_rows = [row for row in journal if row["kind"] == "event_role"]
        relation_rows = [row for row in journal if row["kind"] == "relation"]
        context_rows = [row for row in journal if row["kind"] == "context"]
        assert len(role_rows) == 4
        assert len(relation_rows) == 2
        assert len(context_rows) == 4
        assert all(row["source_id"].endswith(":task11-learning-target")
                   for row in role_rows)
        assert all(row.get("source_provenance", "").startswith("train#")
                   for row in relation_rows)
        assert all(row["current_context"].startswith("task11:entity:")
                   for row in context_rows)


def test_task11_ambiguous_pronoun_is_evidence_only_and_gets_no_learning_target():
    story = ExpansionStory("task11/fit/ambiguous-training-only", 11, (
        Task11MentionEvent("m1", "Mary", False, "kitchen", 1, "train#1", "female"),
        Task11MentionEvent("m2", "Sandra", False, "garden", 2, "train#2", "female"),
        Task11MentionEvent("m3", "she", True, "office", 3, "train#3", "female"),
    ), ())
    adapter = make_adapter("HLB")
    runtime = BabiExpansionRuntime(adapter, learning_enabled=True)
    outputs = runtime.ingest_story(story)
    assert len(outputs) == 3
    assert all(not row["abstained"] for row in outputs)
    journal = adapter.learning._observation_journal
    assert len([row for row in journal if row["kind"] == "event_role"]) == 2
    assert len([row for row in journal if row["kind"] == "relation"]) == 0
    assert len([row for row in journal if row["kind"] == "context"]) == 2
    assert adapter.store.count == 0
    raw_pronoun, = runtime.recover_witness("m3", observation_cutoff=3.0)
    assert raw_pronoun.role("mention").entity_id == "she"
    assert not any(p.role in {"entity", "antecedent_event"} for p in raw_pronoun.participants)


def test_task11_learning_only_targets_respect_explicit_non_learning_mode():
    story = _task11_learning_story("task11/fit/no-learning")
    for kind in ("HLA", "HLB"):
        adapter = make_adapter(kind)
        runtime = BabiExpansionRuntime(adapter, learning_enabled=False)
        before = _task11_parameter_state(adapter)
        outputs = runtime.ingest_story(story)
        after = _task11_parameter_state(adapter)
        assert len(outputs) == 4
        assert before == after
