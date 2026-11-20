from rgm.experiments.m4_confirmatory_worlds import (
    default_partitions, generate_world, generate_order_world, partition_manifest,
    preflight_audit, structural_fingerprint, validate_partitions,
)


def test_worlds_are_deterministic_but_structurally_varied():
    first = generate_world(10001, 2)
    again = generate_world(10001, 2)
    assert first.events == again.events
    same_graph_other_namespace = generate_world(10001, 2, schema_namespace=6)
    assert structural_fingerprint(first) == structural_fingerprint(same_graph_other_namespace)
    worlds = [generate_world(11000 + i, (2, 3, 4)[i % 3]) for i in range(36)]
    assert len({structural_fingerprint(w) for w in worlds}) > 1
    assert len({w.schema_namespace for w in worlds}) > 1


def test_partitions_are_disjoint_at_world_level():
    parts = default_partitions(12, 8, 10)
    validate_partitions(parts)
    manifest = partition_manifest(parts)
    assert manifest["partition_disjoint"] is True
    ids = [seed for part in parts for seed in part.seeds]
    assert len(ids) == len(set(ids))
    assert set(parts[-1].seeds).isdisjoint(parts[0].seeds)
    assert set(parts[-1].seeds).isdisjoint(parts[1].seeds)


def test_typed_world_and_oracle_separation():
    world = generate_world(70001, 4)
    assert len(world.relation_types) == 8
    assert len({r.domain for r in world.relation_types}) > 1
    assert all(e.subject.entity_type == e.relation_type.domain for e in world.events)
    assert all(e.object.entity_type == e.relation_type.codomain for e in world.events)
    view = world.learner_view()
    assert hasattr(view, "events")
    assert not hasattr(view, "oracle_target_path")
    assert all(hasattr(e, "instance_id") for e in view.events)
    early = world.learner_view(world.observation_cutoff - 0.1)
    assert all(e.observed_at <= early.observation_cutoff for e in early.events)
    assert len(early.events) <= len(view.events)
    assert world.oracle_target_path == ("a0", "a1", "a2", "a3")


def test_preflight_is_generator_only():
    result = preflight_audit(48)
    assert result["classification"] == "generator_preflight_only_no_model_performance"
    assert result["unique_identity_invariant_topologies"] > 1
    assert result["typed_edge_invariant"]
    assert result["mode_counts"]["heterogeneous_typed_chain"] == 24
    assert result["mode_counts"]["homogeneous_order_sensitive"] == 24
    assert result["future_observation_invariant"]


def test_order_sensitive_worlds_preserve_same_bag_different_order():
    world = generate_order_world(80001, 4)
    assert world.mode == "homogeneous_order_sensitive"
    assert sorted(world.oracle_target_path) == sorted(world.oracle_decoy_paths[0])
    assert world.oracle_target_path != world.oracle_decoy_paths[0]
    assert all(event.subject.entity_type == event.relation_type.domain
               and event.object.entity_type == event.relation_type.codomain
               for event in world.events)
