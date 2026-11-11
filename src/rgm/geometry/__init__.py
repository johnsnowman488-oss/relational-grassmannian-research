"""Fixed-rank Grassmannian primitives."""
from .grassmannian import GrassmannianPoint
from .distance import canonical_distance, principal_angles
from .projection import projector_from_frame
from .update import evolve_subspace
__all__ = ["GrassmannianPoint", "canonical_distance", "principal_angles", "projector_from_frame", "evolve_subspace"]
