"""V0.25 DVB-S2 ACM selection and the separately named U diagnostic."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

from mcrl.errors import MCRLContractError

from .constants_v025 import (
    ACM_TABLE,
    IMPLEMENTATION_MARGIN_DB,
    ROLL_OFF,
    SHANNON_MIN,
    SINR_MIN,
)


@dataclass(frozen=True)
class ACMMode:
    name: str
    efficiency_bit_per_symbol: float
    ideal_esn0_db: float
    spectral_efficiency_bit_per_s_hz: float
    threshold_db: float
    threshold_linear: float


def _mode(row: tuple[str, float, float]) -> ACMMode:
    name, efficiency, ideal = row
    spectral_efficiency = efficiency / (1.0 + ROLL_OFF)
    threshold_db = ideal + IMPLEMENTATION_MARGIN_DB - 10.0 * math.log10(1.0 + ROLL_OFF)
    return ACMMode(
        name,
        efficiency,
        ideal,
        spectral_efficiency,
        threshold_db,
        10.0 ** (threshold_db / 10.0),
    )


ACM_MODES = tuple(_mode(row) for row in ACM_TABLE)


def served_phy(sinr_linear: float, *, allocated: bool = True) -> bool:
    """The service endpoint: allocated and at or above the lowest threshold."""

    if not math.isfinite(sinr_linear) or sinr_linear < 0.0:
        raise MCRLContractError("SINR must be finite and nonnegative")
    return bool(allocated and sinr_linear >= SINR_MIN)


def select_mode(sinr_linear: float) -> ACMMode | None:
    """Select the eligible mode with greatest efficiency, not table position."""

    if not math.isfinite(sinr_linear) or sinr_linear < 0.0:
        raise MCRLContractError("SINR must be finite and nonnegative")
    eligible = [mode for mode in ACM_MODES if sinr_linear >= mode.threshold_linear]
    return max(eligible, key=lambda mode: mode.efficiency_bit_per_symbol) if eligible else None


class RateModel(Protocol):
    name: str

    def rate_bps(self, sinr_linear: float, bandwidth_hz: float) -> float: ...

    def served(self, sinr_linear: float, *, allocated: bool = True) -> bool: ...


@dataclass(frozen=True)
class ACMRate:
    """Capped, margin-bearing DVB-S2 ACM model."""

    name: str = "ACM"

    def rate_bps(self, sinr_linear: float, bandwidth_hz: float) -> float:
        if not math.isfinite(bandwidth_hz) or bandwidth_hz <= 0.0:
            raise MCRLContractError("bandwidth must be finite and positive")
        if not served_phy(sinr_linear):
            return 0.0
        mode = select_mode(sinr_linear)
        return 0.0 if mode is None else bandwidth_hz * mode.spectral_efficiency_bit_per_s_hz

    def served(self, sinr_linear: float, *, allocated: bool = True) -> bool:
        return served_phy(sinr_linear, allocated=allocated)


@dataclass(frozen=True)
class UncappedShannonDiagnosticRate:
    """Treatment U: uncapped Shannon rate with the common margin removed.

    This is a diagnostic upper bound, not an ACM profile and not eligible as
    the primary model.  Its allocation boundary is the lowest ideal table
    threshold after the symbol-rate/bandwidth conversion, with margin off.
    """

    name: str = "U_UNCAPPED_SHANNON_MARGIN_OFF"

    def rate_bps(self, sinr_linear: float, bandwidth_hz: float) -> float:
        if not math.isfinite(sinr_linear) or sinr_linear < 0.0:
            raise MCRLContractError("SINR must be finite and nonnegative")
        if not math.isfinite(bandwidth_hz) or bandwidth_hz <= 0.0:
            raise MCRLContractError("bandwidth must be finite and positive")
        if sinr_linear < SHANNON_MIN:
            return 0.0
        return bandwidth_hz * math.log2(1.0 + sinr_linear)

    def served(self, sinr_linear: float, *, allocated: bool = True) -> bool:
        if not math.isfinite(sinr_linear) or sinr_linear < 0.0:
            raise MCRLContractError("SINR must be finite and nonnegative")
        return bool(allocated and sinr_linear >= SHANNON_MIN)


def rate_model(name: str) -> RateModel:
    if name == "ACM":
        return ACMRate()
    if name == "U":
        return UncappedShannonDiagnosticRate()
    raise MCRLContractError(f"unknown V0.25 rate model {name!r}")


__all__ = [
    "ACMMode",
    "ACMRate",
    "ACM_MODES",
    "RateModel",
    "UncappedShannonDiagnosticRate",
    "rate_model",
    "select_mode",
    "served_phy",
]
