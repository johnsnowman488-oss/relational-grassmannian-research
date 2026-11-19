"""Typed, witness-preserving relational path composition for HLG-M4 P0.

Task-layer reference implementation; legacy relation APIs remain unchanged.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import math

@dataclass(frozen=True)
class Entity:
    entity_id: str
    entity_type: str
    def __post_init__(self):
        if not self.entity_id or not self.entity_type: raise ValueError("entity identity and type must be non-empty")

@dataclass(frozen=True)
class RelationType:
    name: str
    domain: str
    codomain: str
    def __post_init__(self):
        if not self.name or not self.domain or not self.codomain: raise ValueError("relation name, domain and codomain must be non-empty")

@dataclass(frozen=True)
class RelationInstance:
    instance_id: str
    relation_type: RelationType
    subject: Entity
    object: Entity
    event_time: float
    observed_at: float
    context: str | None = None
    valid_until: float | None = None
    provenance: str | None = None
    def __post_init__(self):
        if not self.instance_id: raise ValueError("instance_id must be non-empty")
        if self.subject.entity_type != self.relation_type.domain: raise ValueError("subject type does not match relation domain")
        if self.object.entity_type != self.relation_type.codomain: raise ValueError("object type does not match relation codomain")
        if not math.isfinite(self.event_time) or not math.isfinite(self.observed_at): raise ValueError("event_time and observed_at must be finite")
        if self.event_time < 0 or self.observed_at < self.event_time: raise ValueError("observation cannot precede event time")
        if self.valid_until is not None and (not math.isfinite(self.valid_until) or self.valid_until <= self.event_time): raise ValueError("valid_until must be finite and later than event_time")

@dataclass(frozen=True)
class CompositionQuery:
    start_entity: Entity
    relation_path: tuple[RelationType, ...]
    context: str | None
    query_time: float
    observation_cutoff: float
    max_event_gap: float | None = None
    require_nondecreasing_event_time: bool = True
    def __post_init__(self):
        if not self.relation_path: raise ValueError("relation_path must not be empty")
        if not math.isfinite(self.query_time) or not math.isfinite(self.observation_cutoff): raise ValueError("query times must be finite")
        if self.query_time < 0 or self.observation_cutoff < 0: raise ValueError("query times must be non-negative")
        if self.observation_cutoff > self.query_time: raise ValueError("observation_cutoff cannot exceed query_time")
        if self.max_event_gap is not None and (not math.isfinite(self.max_event_gap) or self.max_event_gap < 0): raise ValueError("max_event_gap must be finite and non-negative")
        expected=self.start_entity.entity_type
        for relation in self.relation_path:
            if relation.domain != expected: raise ValueError("relation path has incompatible adjacent types")
            expected=relation.codomain

@dataclass(frozen=True)
class CompositionWitness:
    entities: tuple[Entity, ...]
    instances: tuple[RelationInstance, ...]
    def __post_init__(self):
        if len(self.entities) != len(self.instances) + 1 or not self.instances:
            raise ValueError("a witness must contain one more entity than relation instances")
        ids = [edge.instance_id for edge in self.instances]
        if len(ids) != len(set(ids)):
            raise ValueError("a witness cannot reuse a relation instance")
        for index, edge in enumerate(self.instances):
            if edge.subject != self.entities[index] or edge.object != self.entities[index + 1]:
                raise ValueError("witness edge endpoints do not match ordered entity sequence")
            if edge.subject.entity_type != edge.relation_type.domain or edge.object.entity_type != edge.relation_type.codomain:
                raise ValueError("witness edge types do not match relation signature")
            if index and edge.event_time < self.instances[index - 1].event_time:
                raise ValueError("witness event times must be nondecreasing")
    @property
    def endpoint(self): return self.entities[-1]
    @property
    def instance_ids(self): return tuple(edge.instance_id for edge in self.instances)

def compose_witnesses(first: CompositionWitness, second: CompositionWitness) -> CompositionWitness:
    """Binary extensional join; retain all intermediate identities and edge IDs."""
    if first.endpoint != second.entities[0]: raise ValueError("witnesses do not share the same typed intermediate entity")
    if set(first.instance_ids).intersection(second.instance_ids): raise ValueError("a path witness cannot reuse a relation instance")
    return CompositionWitness(first.entities + second.entities[1:], first.instances + second.instances)

@dataclass(frozen=True)
class CompositionResult:
    witnesses: tuple[CompositionWitness, ...]
    rejected: dict[str, int]
    @property
    def endpoints(self): return tuple(sorted({w.endpoint for w in self.witnesses},key=lambda e:(e.entity_type,e.entity_id)))

def compose_paths(instances: Iterable[RelationInstance], query: CompositionQuery) -> CompositionResult:
    """Enumerate valid ordered witnesses from learner-visible instances only.

    Validity uses half-open [event_time, valid_until) intervals. Observation
    cutoff blocks future-observed facts. Context is exact-match with global
    (None) facts allowed. Temporal order/gap constraints are path-level filters.
    """
    edges=tuple(instances)
    if len({e.instance_id for e in edges}) != len(edges): raise ValueError("instance ids must be unique in the supplied view")
    rejected={"not_observed":0,"not_current":0,"context":0,"type_or_path":0,"time_order":0,"gap":0}
    visible=[]
    for edge in edges:
        if edge.observed_at>query.observation_cutoff: rejected["not_observed"]+=1; continue
        if edge.event_time>query.query_time or (edge.valid_until is not None and query.query_time>=edge.valid_until): rejected["not_current"]+=1; continue
        if query.context is not None and edge.context not in (None,query.context): rejected["context"]+=1; continue
        visible.append(edge)
    by_type={}
    for edge in visible: by_type.setdefault(edge.relation_type.name,[]).append(edge)
    found=[]
    def visit(depth,current,path_edges,path_entities):
        if depth==len(query.relation_path): found.append(CompositionWitness(path_entities,path_edges)); return
        relation=query.relation_path[depth]
        if current.entity_type!=relation.domain: rejected["type_or_path"]+=1; return
        for edge in by_type.get(relation.name,()):
            if edge.relation_type!=relation or edge.subject!=current: continue
            if path_edges and query.require_nondecreasing_event_time and edge.event_time<path_edges[-1].event_time:
                rejected["time_order"]+=1; continue
            if path_edges and query.max_event_gap is not None and edge.event_time-path_edges[-1].event_time>query.max_event_gap:
                rejected["gap"]+=1; continue
            visit(depth+1,edge.object,path_edges+(edge,),path_entities+(edge.object,))
    visit(0,query.start_entity,(),(query.start_entity,))
    found.sort(key=lambda w:(w.endpoint.entity_type,w.endpoint.entity_id,w.instance_ids))
    return CompositionResult(tuple(found),rejected)

FAILURE_LAYERS=("retention","retrieval","binding","path_selection","operator_application","composition","readout")
def attribute_failure(layer_passes: dict[str,bool]) -> str:
    if set(layer_passes)!=set(FAILURE_LAYERS): raise ValueError("layer_passes must provide every P1 layer exactly once")
    for layer in FAILURE_LAYERS:
        if not bool(layer_passes[layer]): return layer
    return "none"
