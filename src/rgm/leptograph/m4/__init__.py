"""M4 task semantics, adaptive architecture primitives, and H0/H1 hierarchy APIs."""

from .soe_bridge import (
    H0_CONTRACT_VERSION,
    H0_DEFAULT_EDGES,
    H0_LEVEL_ROLES,
    SOEHierarchyBridge,
    SOEStateLayout,
    make_h0_chain_spec,
    make_native_level_spec,
)
from .hierarchical import (
    AbstractPrediction,
    H1_SCHEMA_VERSION,
    CanonicalRelationStore,
    CompositeLifecycle,
    EvaluationPartition,
    HLAAdapter,
    HLBAdapter,
    HierarchicalEvaluationRunner,
    HierarchicalRuntimeDirector,
    LinearReadout,
    ReadoutExample,
)

__all__ = [
    "H0_CONTRACT_VERSION", "H0_DEFAULT_EDGES", "H0_LEVEL_ROLES",
    "SOEHierarchyBridge", "SOEStateLayout", "make_h0_chain_spec",
    "make_native_level_spec", "AbstractPrediction", "H1_SCHEMA_VERSION", "CanonicalRelationStore",
    "CompositeLifecycle", "EvaluationPartition", "HLAAdapter", "HLBAdapter",
    "HierarchicalEvaluationRunner", "HierarchicalRuntimeDirector",
    "LinearReadout", "ReadoutExample",
]
