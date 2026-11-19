"""Operational M4 P5 architecture variants; reuses the fixed SOE primitive."""
from __future__ import annotations
from dataclasses import dataclass,field
import numpy as np
from rgm.memory import SOEMemory
from rgm.leptograph.m3.context import ContextBank, ContextDecision

P4_TRANSFER_SCOPE = "deferred_to_E08"

@dataclass
class M4MemoryVariant:
    name:str
    relation_count:int=8
    mode_dimension:int=2
    decay:float=0.05
    soe:SOEMemory|None=field(init=False,default=None)
    unified:np.ndarray|None=field(init=False,default=None)
    relations:dict[int,float]=field(init=False,default_factory=dict)
    observations:int=0
    def __post_init__(self):
        if self.name not in {"A","B","C","R"}: raise ValueError("name must be A, B, C or R")
        if self.relation_count<1 or self.mode_dimension<1 or not 0<self.decay<=1: raise ValueError("invalid dimensions or decay")
        width=self.relation_count+self.mode_dimension
        if self.name in {"A","B"}: self.soe=SOEMemory(feature_dim=width)
        if self.name=="C": self.unified=np.zeros(width,dtype=float)
    def observe(self,relation_id:int,value:float,mode:np.ndarray|None=None):
        if not 0<=relation_id<self.relation_count or not np.isfinite(value): raise ValueError("invalid relation observation")
        m=np.zeros(self.mode_dimension) if mode is None else np.asarray(mode,dtype=float)
        if m.shape!=(self.mode_dimension,) or not np.all(np.isfinite(m)): raise ValueError("invalid mode vector")
        if self.name in {"A","B"}:
            feature=np.zeros(self.relation_count+self.mode_dimension); feature[relation_id]=value; feature[self.relation_count:]=m
            self.soe.update(feature,dt=1.0)
        elif self.name=="C":
            self.unified *= (1.0-self.decay); self.unified[relation_id]=value; self.unified[self.relation_count:]=m
        if self.name in {"B","R"}: self.relations[relation_id]=float(value)
        self.observations+=1
    def query(self,relation_id:int)->float:
        if not 0<=relation_id<self.relation_count: raise ValueError("unknown relation id")
        if self.name=="A": return float(np.mean(self.soe.channels[:,relation_id]))
        if self.name=="B": return float(self.relations.get(relation_id,0.0))
        if self.name=="C": return float(self.unified[relation_id])
        return float(self.relations.get(relation_id,0.0))
    def advance_gap(self, steps:int=1):
        """Advance through an observation outage without inventing observations."""
        if not isinstance(steps,int) or steps<0: raise ValueError("steps must be a non-negative integer")
        if self.name in {"A","B"}: self.soe.advance(float(steps))
        elif self.name=="C": self.unified *= (1.0-self.decay)**steps
        # Explicit relational stores in B/R persist unchanged through the gap.
    @property
    def persistent_state_bytes(self)->int:
        if self.name in {"A","B"}: base=self.soe.channels.nbytes
        elif self.name=="C": base=self.unified.nbytes
        else: base=0
        if self.name in {"B","R"}: base+=len(self.relations)*8
        return int(base)


@dataclass
class BoundedContextAcquisition:
    """P2 wrapper around the existing fixed-capacity ContextBank."""
    bank: ContextBank
    def observe(self,point):
        decision,slot_id,scores=self.bank.route(point)
        if decision==ContextDecision.ACCEPT: return {"status":"ACCEPT","slot_id":slot_id,"scores":scores}
        if decision==ContextDecision.NOVEL:
            created=self.bank.observe_novel(point)
            if created is not None: return {"status":"ACQUIRED","slot_id":created,"scores":scores}
            if len(self.bank.slots)>=self.bank.capacity: return {"status":"ABSTAIN_CAPACITY","slot_id":None,"scores":scores}
            return {"status":"PENDING_NOVELTY","slot_id":None,"scores":scores}
        return {"status":"ABSTAIN","slot_id":None,"scores":scores}
