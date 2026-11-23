"""M4 task semantics, adaptive architecture primitives, and H0 hierarchy bridge."""

from .soe_bridge import (
    H0_CONTRACT_VERSION,
    H0_DEFAULT_EDGES,
    H0_LEVEL_ROLES,
    SOEHierarchyBridge,
    SOEStateLayout,
    make_h0_chain_spec,
    make_native_level_spec,
)

__all__ = [
    "H0_CONTRACT_VERSION",
    "H0_DEFAULT_EDGES",
    "H0_LEVEL_ROLES",
    "SOEHierarchyBridge",
    "SOEStateLayout",
    "make_h0_chain_spec",
    "make_native_level_spec",
]
