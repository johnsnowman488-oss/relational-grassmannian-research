import copy

import numpy as np
import pytest

from rgm.memory import SOEMemory
from rgm.leptograph.m4.composition import Entity, RelationInstance, RelationType
from rgm.leptograph.m4.learning import ErrorChannel, LearningRuntime
from rgm.leptograph.m4.hierarchical import (
    CanonicalRelationStore, CompositeLifecycle, EvaluationPartition,
    HLAAdapter, HLBAdapter, HierarchicalEvaluationRunner,
    HierarchicalRuntimeDirector, ReadoutExample,
    create_hla_adapter, create_hlb_adapter,
)
from rgm.leptograph.m4.soe_bridge import SOEHierarchyBridge


class FakePersistentRuntime:
    def __init__(self, memories):
        self.state = {"level_states": [
            {"u": m.snapshot().reshape(-1).tolist(), "chi": [0.0] * m.channel_count, "t": 0.0}
            for m in memories
        ], "step_count": 0}

    def get_state(self):
        return copy.deepcopy(self.state)

    def step(self, feedback_by_level=None):
        candidate = copy.deepcopy(self.state)
        for level, values in (feedback_by_level or {}).items():
            candidate["level_states"][level]["u"] = list(values)
        candidate["step_count"] += 1
        self.state = candidate
        return self.get_state()

    def checkpoint(self):
        return self.get_state()

    def restore(self, checkpoint):
        if len(checkpoint["level_states"]) != 3:
            raise ValueError("bad native checkpoint")
        self.state = copy.deepcopy(checkpoint)


def make_bridge():
    banks = [
        SOEMemory(feature_dim=2, decay_rates=[0.1, 0.4]),
        SOEMemory(feature_dim=3, decay_rates=[0.2, 0.7]),
        SOEMemory(feature_dim=4, decay_rates=[0.05, 0.3]),
    ]
    runtime = FakePersistentRuntime(banks)
    return SOEHierarchyBridge(runtime, banks, dt=0.01), runtime


def test_hla_uses_two_learned_upper_readouts_without_relation_store():
    bridge, _ = make_bridge()
    hla = HLAAdapter(bridge, feature_dims=[2, 3, 4])
    hla.fit_upper_readouts(
        [ReadoutExample((0, 0, 0, 0), (0, 0, 0)),
         ReadoutExample((1, 1, 1, 1), (1, 1, 1))],
        [ReadoutExample((0, 0, 0, 0, 0, 0), (0, 0, 0, 0)),
         ReadoutExample((1, 1, 1, 1, 1, 1), (1, 1, 1, 1))],
    )
    result = hla.step({0: [0.5, -0.5]})
    assert result["architecture"] == "HLA"
    assert hla.ticks == 1
    assert not hasattr(hla, "store")
    assert hla.query_readout(1, [0.5, -0.5, 0.5, -0.5]).shape == (3,)
    abstract = hla.predict_abstract(2, [0.5] * 6)
    assert abstract.kind == "ABSTRACT_PREDICTION"
    assert len(abstract.features) == 4


def test_hla_abstains_if_upper_readout_is_untrained():
    bridge, _ = make_bridge()
    hla = HLAAdapter(bridge, feature_dims=[2, 3, 4])
    with pytest.raises(RuntimeError, match="not fitted"):
        hla.query_readout(1, [1, 2, 3, 4])
    assert hla.abstentions == 1


def test_hlb_canonical_store_has_level_scoped_indexes_and_no_duplicate_records():
    store = CanonicalRelationStore(capacity=2)
    person = Entity("p1", "person")
    place = Entity("x1", "place")
    located = RelationType("located_at", "person", "place")
    record = RelationInstance("r1", located, person, place, 1.0, 1.0)
    assert store.insert(0, record) == "STORED"
    assert store.insert(0, record) == "ALREADY_STORED"
    assert store.count == 1
    assert store.by_subject(0, person, cutoff=2.0) == (record,)
    assert store.by_subject(1, person, cutoff=2.0) == ()
    assert store.insert(1, RelationInstance("r2", located, person, place, 1.0, 1.0)) == "STORED"
    assert store.insert(2, RelationInstance("r3", located, person, place, 1.0, 1.0)) == "ABSTAIN_CAPACITY"


def test_hlb_composition_preserves_original_relation_instance_witnesses():
    bridge, _ = make_bridge()
    hlb = HLBAdapter(bridge)
    person, org, city = Entity("p", "person"), Entity("o", "org"), Entity("c", "city")
    employed = RelationType("employed_by", "person", "org")
    based = RelationType("based_in", "org", "city")
    first = RelationInstance("edge-1", employed, person, org, 1.0, 1.0)
    second = RelationInstance("edge-2", based, org, city, 2.0, 2.0)
    assert hlb.observe(0, first) == "STORED"
    assert hlb.observe(1, second) == "STORED"
    witnesses = hlb.query(person, [employed, based], context=None,
                           query_time=3.0, observation_cutoff=3.0)
    assert len(witnesses) == 1
    assert witnesses[0].instance_ids == ("edge-1", "edge-2")
    assert witnesses[0].entities == (person, org, city)


def test_director_executes_one_bridge_step_and_records_event_and_observation_times():
    bridge, runtime = make_bridge()
    director = HierarchicalRuntimeDirector(HLBAdapter(bridge))
    director.exchange(event_time=1.0, observed_at=2.0,
                      event_features={0: [1.0, 0.0]})
    assert runtime.state["step_count"] == 1
    assert director.event_log == [{"event_time": 1.0, "observed_at": 2.0, "tick": 1}]
    with pytest.raises(ValueError, match="nondecreasing"):
        director.exchange(event_time=1.5, observed_at=1.5)


def test_director_rejects_relation_storage_for_hla():
    bridge, _ = make_bridge()
    director = HierarchicalRuntimeDirector(HLAAdapter(bridge, feature_dims=[2, 3, 4]))
    edge = RelationInstance("r", RelationType("r", "a", "b"),
                            Entity("a", "a"), Entity("b", "b"), 1.0, 1.0)
    with pytest.raises(ValueError, match="cannot retain"):
        director.exchange(event_time=1.0, observed_at=1.0, relation_records=[(0, edge)])


def test_composite_checkpoint_restore_and_rollback_restore_native_and_python_state():
    bridge, runtime = make_bridge()
    director = HierarchicalRuntimeDirector(HLBAdapter(bridge))
    lifecycle = CompositeLifecycle(director)
    trusted = lifecycle.checkpoint()
    director.exchange(event_time=1.0, observed_at=1.0,
                      event_features={0: [1.0, 0.0]})
    assert runtime.state["step_count"] == 1
    lifecycle.rollback()
    # The candidate's observed input is replayed through the restored incumbent.
    assert runtime.state["step_count"] == 1
    assert director.event_tick == 1
    assert runtime.state["level_states"][0]["u"] == [1.0, 0.0, 1.0, 0.0]
    damaged = copy.deepcopy(trusted)
    damaged["director"]["event_tick"] = 99
    with pytest.raises(ValueError):
        lifecycle.restore(damaged)


def test_evaluation_runner_keeps_confirmatory_partition_and_pairs_same_task_order():
    bridge_a, _ = make_bridge()
    bridge_b, _ = make_bridge()
    a = HLAAdapter(bridge_a, feature_dims=[2, 3, 4])
    b = HLBAdapter(bridge_b)
    runner = HierarchicalEvaluationRunner(
        lambda adapter, task: {"loss": float(task), "success": float(task == 0)},
        task_id="h1-smoke", seed=17,
    )
    partition = EvaluationPartition("confirmatory", (0, 1, 2))
    result_a, result_b = runner.run(a, partition), runner.run(b, partition)
    paired = runner.paired_summary(result_a, result_b)
    assert result_a["partition"] == "confirmatory"
    assert result_a["task_count"] == 3
    assert paired["differences"] == {"loss": 0.0, "success": 0.0}
    with pytest.raises(ValueError, match="fit partition"):
        runner.run(a, EvaluationPartition("fit", (0,)))
    different_tasks = runner.run(b, EvaluationPartition("confirmatory", (0, 1, 99)))
    with pytest.raises(ValueError, match="identical task"):
        runner.paired_summary(result_a, different_tasks)



def test_production_runtime_factories_create_one_native_handle_per_adapter():
    banks_a = [
        SOEMemory(feature_dim=2, decay_rates=[0.1, 0.4]),
        SOEMemory(feature_dim=3, decay_rates=[0.2, 0.7]),
        SOEMemory(feature_dim=4, decay_rates=[0.05, 0.3]),
    ]
    calls = []

    class ClosableRuntime(FakePersistentRuntime):
        def __init__(self, memories):
            super().__init__(memories)
            self.closed = False

        def close(self):
            self.closed = True

    def factory(library, levels, edges):
        calls.append((library, levels, edges))
        return ClosableRuntime(banks_a)

    library = object()
    kernels = [
        {"gamma": sorted(bank.decay_rates.tolist(), reverse=True),
         "w": [1.0] * bank.channel_count}
        for bank in banks_a
    ]
    hla = create_hla_adapter(library, banks_a, kernels, dt=0.01,
                             runtime_factory=factory)
    director = HierarchicalRuntimeDirector(hla)
    assert len(calls) == 1
    assert len(calls[0][1]) == 3
    assert len(calls[0][2]) == 4
    director.close()
    assert hla.bridge.runtime.closed

    banks_b = [memory.copy() for memory in banks_a]
    hlb = create_hlb_adapter(library, banks_b, kernels, dt=0.01,
                             runtime_factory=factory, capacity=10)
    assert isinstance(hlb, HLBAdapter)
    assert len(calls) == 2



def validation_record(lifecycle):
    return {
        "validation_id": "unit-validation-1",
        "passed": True,
        "independent": True,
        "partition": "validation",
        "candidate_fingerprint": lifecycle.candidate_fingerprint(),
        "protocol_fingerprint": "a" * 64,
        "criteria_fingerprint": "b" * 64,
        "data_manifest_fingerprint": "c" * 64,
        "metrics": {"exact_accuracy": 1.0},
    }

def test_lifecycle_rollback_after_promotion_restores_previous_trusted_version():
    bridge, runtime = make_bridge()
    director = HierarchicalRuntimeDirector(HLBAdapter(bridge))
    lifecycle = CompositeLifecycle(director)
    lifecycle.checkpoint()
    director.exchange(event_time=1.0, observed_at=1.0,
                      event_features={0: [1.0, 0.0]})
    assert lifecycle.promote(validation_record(lifecycle)) == 1
    assert runtime.state["step_count"] == 1
    director.exchange(event_time=2.0, observed_at=2.0,
                      event_features={0: [0.0, 1.0]})
    assert runtime.state["step_count"] == 2
    lifecycle.rollback()
    # Both observations survive rollback and are replayed through the prior model.
    assert runtime.state["step_count"] == 2
    assert director.event_tick == 2
    assert lifecycle.version == 0



def test_hla_and_hlb_share_upper_readouts_but_have_different_relation_retention():
    bridge_a, _ = make_bridge()
    bridge_b, _ = make_bridge()
    hla = HLAAdapter(bridge_a, feature_dims=[2, 3, 4])
    hlb = HLBAdapter(bridge_b)
    level1 = [
        ReadoutExample((0, 0, 0, 0), (0, 0, 0)),
        ReadoutExample((1, 1, 1, 1), (1, 1, 1)),
    ]
    level2 = [
        ReadoutExample((0, 0, 0, 0, 0, 0), (0, 0, 0, 0)),
        ReadoutExample((1, 1, 1, 1, 1, 1), (1, 1, 1, 1)),
    ]
    hla.fit_upper_readouts(level1, level2)
    hlb.fit_upper_readouts(level1, level2)
    assert [r.fingerprint for r in hla.readouts] == [r.fingerprint for r in hlb.readouts]
    assert hla.predict_abstract(1, [0.5] * 4).features == hlb.predict_abstract(1, [0.5] * 4).features

    person, org, city = Entity("p-match", "person"), Entity("o-match", "org"), Entity("c-match", "city")
    employed = RelationType("employed_by", "person", "org")
    based = RelationType("based_in", "org", "city")
    first = RelationInstance("match-edge-1", employed, person, org, 1.0, 1.0)
    second = RelationInstance("match-edge-2", based, org, city, 2.0, 2.0)
    evidence = (first, second)
    assert hla.query(person, [employed, based], evidence=evidence, context=None,
                     query_time=3.0, observation_cutoff=3.0)
    assert not hasattr(hla, "store")
    hlb.observe(0, first)
    hlb.observe(1, second)
    assert hla.query(person, [employed, based], evidence=evidence, context=None,
                     query_time=3.0, observation_cutoff=3.0) == hlb.query(
                         person, [employed, based], context=None,
                         query_time=3.0, observation_cutoff=3.0)
    assert hlb.store.count == 2



@pytest.mark.parametrize("adapter_type", [HLAAdapter, HLBAdapter])
@pytest.mark.parametrize(
    "channels",
    [frozenset(), frozenset({ErrorChannel.TEMPORAL})],
)
def test_adapter_snapshot_validation_uses_frozen_ablation_and_eligibility_config(
    adapter_type, channels,
):
    bridge, _ = make_bridge()
    if adapter_type is HLAAdapter:
        adapter = HLAAdapter(bridge, feature_dims=[2, 3, 4])
    else:
        adapter = HLBAdapter(bridge, capacity=262144)
    adapter.learning = LearningRuntime(
        enabled_channels=channels,
        eligibility_capacity=131072,
    )

    snapshot = adapter.snapshot()
    adapter.validate_snapshot(snapshot)
