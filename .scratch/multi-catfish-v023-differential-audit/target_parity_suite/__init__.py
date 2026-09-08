"""Importable parity checks for the V0.25 target/physics engine."""

from .declared_c3_oracle import (
    AtomicSelection,
    DecisionProfile,
    DeclaredC3Result,
    declared_c3_oracle,
    executed_unilateral_c3,
)
from .ops3_parity import build_ops3_surface_explicit
from .physics_extractor import (
    PhysicsSnapshotExtractor,
    assert_reward_endpoint_identity,
    reward_endpoint_residual,
)

__all__ = [
    "AtomicSelection",
    "DecisionProfile",
    "DeclaredC3Result",
    "PhysicsSnapshotExtractor",
    "assert_reward_endpoint_identity",
    "build_ops3_surface_explicit",
    "declared_c3_oracle",
    "executed_unilateral_c3",
    "reward_endpoint_residual",
]
