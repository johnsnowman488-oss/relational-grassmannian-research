"""HLG-M3 adaptive relational learning reference implementation.

The package is an experimental, versioned research implementation. It does not
claim open-ended topology discovery or global adaptive-network stability.
"""
from .context import ContextBank, ContextDecision
from .estimation import MultiSourceRidge
from .activation import EvidenceActivation
from .revision import CUSUMDetector, CandidateRevision
from .revision_campaign import CandidateLifecycle
from .controls import MemoryArchitecture
from .resource import integrated_resource_snapshot

__all__ = [
    "ContextBank", "ContextDecision", "MultiSourceRidge", "EvidenceActivation",
    "CUSUMDetector", "CandidateRevision", "CandidateLifecycle", "MemoryArchitecture", "integrated_resource_snapshot",
]
