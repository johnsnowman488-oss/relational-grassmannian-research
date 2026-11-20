"""Operational M4 P5 architecture variants; reuses the fixed SOE primitive."""
from __future__ import annotations
from dataclasses import dataclass,field
import numpy as np
from rgm.memory import SOEMemory
from rgm.leptograph.m3.context import ContextBank, ContextDecision

P4_TRANSFER_SCOPE="deferred_to_E08"

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
    readout_gain:float=1.0
    mode_gain:float=1.0
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
            self.unified *= (1.0-self.decay); self.unified[relation_id]=value; self.unified[self.relation_count:]+=m
        if self.name in {"B","R"}: self.relations[relation_id]=float(value)
        self.observations+=1
    def fit_readout(self,trace_values,targets)->float:
        """Fit A's shared relational readout on an independent calibration set."""
        if self.name!="A": raise RuntimeError("only SOE-only A has this relational readout")
        self.readout_gain=self._fit_gain(trace_values,targets)
        return self.readout_gain
    def fit_mode_readout(self,trace_values,targets)->float:
        """Fit the shared temporal-mode readout used by A and B."""
        if self.name not in {"A","B"}: raise RuntimeError("only temporal-memory variants have a mode readout")
        self.mode_gain=self._fit_gain(trace_values,targets)
        return self.mode_gain
    @staticmethod
    def _fit_gain(trace_values,targets):
        x=np.asarray(trace_values,dtype=float).reshape(-1); y=np.asarray(targets,dtype=float).reshape(-1)
        if x.size==0 or x.shape!=y.shape or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)): raise ValueError("calibration arrays must be non-empty, finite and matched")
        denom=float(x@x)
        if denom<=0: raise ValueError("calibration has zero feature energy")
        return float((x@y)/denom)
    def query(self,relation_id:int)->float:
        if not 0<=relation_id<self.relation_count: raise ValueError("unknown relation id")
        if self.name=="A":
            relation=self.readout_gain*np.mean(self.soe.channels[:,relation_id])
            mode=self.mode_gain*np.mean(self.soe.channels[:,self.relation_count])
            return float(relation+0.5*mode)
        if self.name=="B":
            relation=self.relations.get(relation_id,0.0)
            mode=self.mode_gain*np.mean(self.soe.channels[:,self.relation_count])
            return float(relation+0.5*mode)
        if self.name=="C": return float(self.unified[relation_id]+0.5*self.unified[self.relation_count])
        return float(self.relations.get(relation_id,0.0))
    def advance_gap(self,steps:int=1):
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
    bank:ContextBank
    def observe(self,point):
        decision,slot_id,scores=self.bank.route(point)
        if decision==ContextDecision.ACCEPT: return {"status":"ACCEPT","slot_id":slot_id,"scores":scores}
        if decision==ContextDecision.NOVEL:
            created=self.bank.observe_novel(point)
            if created is not None: return {"status":"ACQUIRED","slot_id":created,"scores":scores}
            if len(self.bank.slots)>=self.bank.capacity: return {"status":"ABSTAIN_CAPACITY","slot_id":None,"scores":scores}
            return {"status":"PENDING_NOVELTY","slot_id":None,"scores":scores}
        return {"status":"ABSTAIN","slot_id":None,"scores":scores}
