"""Versioned V0.25 radiation, rate, energy, and endpoint engine.

The package is intentionally independent of :mod:`mcrl.env`: V0.25 inputs are
plain immutable records and the historical environment remains a reproducible
control rather than an implicit dependency.
"""

from .architectures import (
    AngleTPC_FDM,
    AngleTPC_TDM,
    FixedRF,
    Geometry,
    Link,
    RadiationConfig,
    architecture_for,
)
from .matrix import MATRIX_SETTINGS, PhysicsSetting

__all__ = [
    "AngleTPC_FDM",
    "AngleTPC_TDM",
    "FixedRF",
    "Geometry",
    "Link",
    "MATRIX_SETTINGS",
    "PhysicsSetting",
    "RadiationConfig",
    "architecture_for",
]
