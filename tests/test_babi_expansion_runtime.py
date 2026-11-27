import copy

from rgm.experiments.babi_expansion_adapters import (
    ExpansionStory, ExpansionQuery, GoldLabel,
    Task11MentionEvent, Task14TemporalEvent, Task19SpatialEdge,
)
from rgm.experiments.babi_expansion_runtime import (
    BabiExpansionRuntime, ExpansionForecasts, target_contract,
    to_nary_event, to_spatial_relation,
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
        Task11MentionEvent("e1", "mary", "Mary", False, "e1", "kitchen", 1, "train#1"),
        Task11MentionEvent("e2", "mary", "she", True, "e1", "hallway", 2, "train#2"),
    ), ())
    mapped = to_nary_event(story, story.events[1])
    assert mapped.event_type == "COREFERS_TO"
    assert mapped.role("entity").entity_id == "mary"
    assert mapped.role("antecedent").entity_id == "e1"
    assert mapped.role("location").entity_id == "hallway"
    assert mapped.provenance == "babi-v1.2-task-11"
    assert mapped.source_locator == "train#2"
    assert len(mapped.payload_digest) == 64


def test_task14_event_time_is_not_observation_time():
    story = ExpansionStory("task14/fit/story000001", 14, (
        Task14TemporalEvent("e1", "mary", "kitchen", "yesterday", (0, 1), 1, "train#1"),
        Task14TemporalEvent("e2", "mary", "garden", "this evening", (3, 2), 2, "train#2"),
    ), ())
    mapped = to_nary_event(story, story.events[1])
    assert mapped.event_time == 3.0
    assert mapped.observed_at == 2.0
    assert mapped.observed_at >= mapped.event_time


def test_task19_relation_orientation_is_encoded_in_typed_edge():
    event = Task19SpatialEdge("e1", "kitchen", "hallway", "east", 1, "train#1")
    relation = to_spatial_relation(event)
    assert relation.subject.entity_id == "kitchen"
    assert relation.object.entity_id == "hallway"
    assert relation.relation_type.name == "spatial_east"
    assert relation.provenance == "train#1"


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
    assert scored["task19.answer.ordered_route_answer"]["value"] == 0.0
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
        Task11MentionEvent("e1", "mary", "Mary", False, "e1", "kitchen", 1, "train#1"),
    ), ())
    second = ExpansionStory("task11/fit/story000002", 11, (
        Task11MentionEvent("e2", "mary", "Mary", False, "e2", "garden", 1, "train#2"),
    ), ())
    runtime = BabiExpansionRuntime(make_adapter("HLA"))
    runtime.ingest_story(first)
    import pytest
    with pytest.raises(RuntimeError, match="story-scoped"):
        runtime.ingest_story(second)
