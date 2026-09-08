"""Versioned V0.25 radiation, rate, energy, and endpoint engine.

The package is intentionally independent of :mod:`mcrl.env`: V0.25 inputs are
plain immutable records and the historical environment remains a reproducible
control rather than an implicit dependency.
"""

from .architectures import (
    AngleRateTPC_FDM,
    AngleRateTPC_TDM,
    AngleTPC_FDM,
    AngleTPC_TDM,
    FixedRF,
    Geometry,
    Link,
    RadiationConfig,
    architecture_for,
)
from .endpoint import assert_same_energy_price, reward_core
from .matrix import MATRIX_SETTINGS, PhysicsSetting
from .calibration import CalibrationValues, nominal_greedy_reference
from .state_v025 import SCHEMA_SHA256 as C2_STATE_SCHEMA_SHA256
from .tapes import ExogenousWorldTape, build_world_tape, seed_from_domain
from .targets import c1_difference_surplus, c2_persistence_forecast, c3_lcsrs_interaction

__all__ = [
    "AngleRateTPC_FDM",
    "AngleRateTPC_TDM",
    "AngleTPC_FDM",
    "AngleTPC_TDM",
    "FixedRF",
    "Geometry",
    "Link",
    "MATRIX_SETTINGS",
    "CalibrationValues",
    "C2_STATE_SCHEMA_SHA256",
    "ExogenousWorldTape",
    "PhysicsSetting",
    "RadiationConfig",
    "architecture_for",
    "assert_same_energy_price",
    "build_world_tape",
    "c1_difference_surplus",
    "c2_persistence_forecast",
    "c3_lcsrs_interaction",
    "nominal_greedy_reference",
    "reward_core",
    "seed_from_domain",
]
