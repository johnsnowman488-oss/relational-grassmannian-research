"""Independent, typed relational-world generator for HLG-M4 confirmatory work.

The generator separates planted oracle labels from learner-visible events. Its
world-level partitions are disjoint by construction. It is a generator/preflight
module, not the confirmatory evaluator or an acceptance result.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random
from typing import Iterable

from rgm.leptograph.m4.composition import Entity, RelationType, RelationInstance
from rgm.leptograph.m4.system import PathTrainingExample


@dataclass(frozen=True)
class WorldPartition:
    name: str
    seeds: tuple[int, ...]


@dataclass(frozen=True)
class RelationalWorld:
    world_id: str
    seed: int
    schema_family: str
    depth: int
    relation_types: tuple[RelationType, ...]
    start: Entity
    goal: Entity
    events: tuple[RelationInstance, ...]
    oracle_target_path: tuple[str, ...]
    oracle_decoy_paths: tuple[tuple[str, ...], ...]
    training_examples: tuple[PathTrainingExample, ...]
    query_time: float
    observation_cutoff: float

    def learner_view(self) -> tuple[RelationInstance, ...]:
        """Return only observations; never expose planted target/decoy labels."""
        return self.events


def default_partitions(train_count: int = 120, validation_count: int = 60,
                       test_count: int = 120) -> tuple[WorldPartition, ...]:
    if min(train_count, validation_count, test_count) < 1:
        raise ValueError("every world partition must be non-empty")
    return (
        WorldPartition("train", tuple(range(10_000, 10_000 + train_count))),
        WorldPartition("validation", tuple(range(30_000, 30_000 + validation_count))),
        WorldPartition("confirmatory_test", tuple(range(70_000, 70_000 + test_count))),
    )


def validate_partitions(partitions: Iterable[WorldPartition]) -> None:
    parts = tuple(partitions)
    names = [p.name for p in parts]
    if len(names) != len(set(names)):
        raise ValueError("partition names must be unique")
    seen: set[int] = set()
    for part in parts:
        if not part.seeds or len(part.seeds) != len(set(part.seeds)):
            raise ValueError(f"partition {part.name} must contain unique non-empty seeds")
        overlap = seen.intersection(part.seeds)
        if overlap:
            raise ValueError(f"world seed leakage across partitions: {sorted(overlap)}")
        seen.update(part.seeds)


def _relation_schema(family_index: int) -> tuple[RelationType, ...]:
    # Different families use distinct typed entity namespaces. Relation names
    # remain in-vocabulary; this is not an OOV relation-transfer experiment.
    types = tuple(f"F{family_index}_T{i}" for i in range(5))
    relations = []
    for prefix in ("a", "b"):
        for i in range(4):
            relations.append(RelationType(f"{prefix}{i}", types[i], types[i + 1]))
    return tuple(relations)


def generate_world(seed: int, depth: int, schema_family: int | None = None) -> RelationalWorld:
    if depth not in (2, 3, 4):
        raise ValueError("confirmatory M4 currently bounds composition depth to 2, 3 or 4")
    rng = random.Random(int(seed))
    family_index = int(seed % 7 if schema_family is None else schema_family)
    if family_index < 0:
        raise ValueError("schema_family must be non-negative")
    schema = _relation_schema(family_index)
    relation_by_name = {r.name: r for r in schema}
    type_names = [f"F{family_index}_T{i}" for i in range(5)]
    world_id = f"m4-world-{seed:08d}-d{depth}-f{family_index}"
    start = Entity(f"{world_id}-source", type_names[0])
    goal = Entity(f"{world_id}-target", type_names[depth])

    facts: list[RelationInstance] = []
    target = tuple(f"a{i}" for i in range(depth))
    decoy = tuple(f"b{i}" for i in range(depth))
    event_index = 0

    def add_chain(prefix: str, sequence: tuple[str, ...], add_spurs: bool) -> None:
        nonlocal event_index
        entities = [start]
        for i in range(depth - 1):
            entities.append(Entity(f"{world_id}-{prefix}-node-{i}-{rng.randrange(1_000_000)}",
                                   type_names[i + 1]))
        entities.append(goal)
        for i, relation_name in enumerate(sequence):
            event_index += 1
            event_time = float(event_index)
            observed_at = event_time + rng.choice((0.0, 0.0, 0.25, 0.5))
            facts.append(RelationInstance(
                f"{world_id}-{prefix}-edge-{i}", relation_by_name[relation_name],
                entities[i], entities[i + 1], event_time, observed_at,
                context="ctx", provenance=f"world:{world_id}",
            ))
            if add_spurs and i < depth - 1 and rng.random() < 0.65:
                # A type-correct branch that does not reach the goal. The
                # branch count/location changes graph topology across worlds.
                event_index += 1
                leaf = Entity(f"{world_id}-{prefix}-spur-{i}-{rng.randrange(1_000_000)}",
                              type_names[i + 1])
                spur_relation = relation_by_name[relation_name]
                facts.append(RelationInstance(
                    f"{world_id}-{prefix}-spur-edge-{i}", spur_relation,
                    entities[i], leaf, float(event_index), float(event_index) + 0.25,
                    context="ctx", provenance=f"world:{world_id}",
                ))

    add_chain("target", target, add_spurs=True)
    add_chain("decoy", decoy, add_spurs=True)
    rng.shuffle(facts)
    cutoff = max(event.observed_at for event in facts)
    return RelationalWorld(
        world_id=world_id, seed=int(seed), schema_family=f"typed-family-{family_index}",
        depth=depth, relation_types=schema, start=start, goal=goal,
        events=tuple(facts), oracle_target_path=target,
        oracle_decoy_paths=(decoy,),
        training_examples=tuple(
            [PathTrainingExample(tuple(f"a{i}" for i in range(d)), 1)
             for d in (2, 3, 4)]
            + [PathTrainingExample(tuple(f"b{i}" for i in range(d)), 0)
               for d in (2, 3, 4)]
        ),
        query_time=cutoff + 1.0, observation_cutoff=cutoff,
    )


def structural_fingerprint(world: RelationalWorld) -> str:
    """Identity-invariant topology digest; captures branching and typed edges."""
    degree: dict[Entity, int] = {}
    typed_edges = []
    for event in world.events:
        degree[event.subject] = degree.get(event.subject, 0) + 1
        degree.setdefault(event.object, 0)
        typed_edges.append((
            event.relation_type.name,
            event.relation_type.domain,
            event.relation_type.codomain,
            degree[event.subject],
        ))
    descriptor = (
        world.depth,
        tuple(sorted(degree.values())),
        tuple(sorted((e.relation_type.name, e.subject.entity_type,
                      e.object.entity_type) for e in world.events)),
        tuple(sorted(typed_edges)),
    )
    return hashlib.sha256(repr(descriptor).encode("utf-8")).hexdigest()


def partition_manifest(partitions: Iterable[WorldPartition]) -> dict:
    parts = tuple(partitions)
    validate_partitions(parts)
    return {
        "generator": "m4-independent-typed-worlds-v1",
        "partition_world_ids": {
            part.name: [f"m4-world-{seed:08d}" for seed in part.seeds]
            for part in parts
        },
        "seed_sha256": {
            part.name: hashlib.sha256(",".join(map(str, part.seeds)).encode()).hexdigest()
            for part in parts
        },
        "world_counts": {part.name: len(part.seeds) for part in parts},
        "partition_disjoint": True,
    }


def preflight_audit(seed_count: int = 48) -> dict:
    if seed_count < 2:
        raise ValueError("seed_count must be at least two")
    fingerprints = set()
    type_signatures = set()
    world_count = 0
    for seed in range(90_000, 90_000 + seed_count):
        depth = (2, 3, 4)[seed % 3]
        world = generate_world(seed, depth)
        world_count += 1
        fingerprints.add(structural_fingerprint(world))
        type_signatures.add(tuple((r.domain, r.codomain) for r in world.relation_types))
        assert all(e.observed_at >= e.event_time for e in world.events)
        assert all(e.subject.entity_type == e.relation_type.domain
                   and e.object.entity_type == e.relation_type.codomain for e in world.events)
        assert world.oracle_target_path not in ()
        assert len(world.learner_view()) == len(world.events)
    return {
        "classification": "generator_preflight_only_no_model_performance",
        "world_count": world_count,
        "unique_identity_invariant_topologies": len(fingerprints),
        "typed_schema_families": len(type_signatures),
        "future_observation_invariant": True,
        "typed_edge_invariant": True,
        "oracle_labels_separate_from_learner_view": True,
    }
