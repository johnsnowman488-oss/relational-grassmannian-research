"""HLG-M3 adaptive relational learning reference implementation.

The package is an experimental, versioned research implementation. It does not
claim open-ended topology discovery or global adaptive-network stability.
"""
from .context import ContextBank, ContextDecision
from .estimation import MultiSourceRidge
from .activation import EvidenceActivation
from .revision import CUSUMDetector, CandidateRevision
from .controls import MemoryArchitecture

__all__ = [
    "ContextBank", "ContextDecision", "MultiSourceRidge", "EvidenceActivation",
    "CUSUMDetector", "CandidateRevision", "MemoryArchitecture",
]
