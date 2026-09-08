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


def rate_target_mode(
    rate_target_bps: float,
    full_bandwidth_hz: float,
    occupancy: int,
) -> ACMMode | None:
    """Return the lowest-threshold frozen ACM mode that meets ``r*``.

    For TDM, ``full_bandwidth_hz / occupancy`` is effective airtime
    bandwidth.  For FDM it is the physical sub-band bandwidth.  Both therefore
    implement the sealed ``Gamma_r(n_b)`` definition with one helper.
    """

    if not math.isfinite(rate_target_bps) or rate_target_bps <= 0.0:
        raise MCRLContractError("rate target must be finite and positive")
    if not math.isfinite(full_bandwidth_hz) or full_bandwidth_hz <= 0.0:
        raise MCRLContractError("full bandwidth must be finite and positive")
    if type(occupancy) is not int or occupancy < 1:
        raise MCRLContractError("occupancy must be a positive exact integer")
    required_se = rate_target_bps * occupancy / full_bandwidth_hz
    eligible = [
        mode
        for mode in ACM_MODES
        if mode.spectral_efficiency_bit_per_s_hz >= required_se
    ]
    return min(eligible, key=lambda mode: mode.threshold_linear) if eligible else None


def rate_target_sinr(
    rate_target_bps: float,
    full_bandwidth_hz: float,
    occupancy: int,
) -> float | None:
    """Return ``Gamma_r(n_b)`` or ``None`` when the ACM table cannot meet it."""

    mode = rate_target_mode(rate_target_bps, full_bandwidth_hz, occupancy)
    if mode is None:
        return None
    # The separately frozen PHY service floor is rounded at its declared dB
    # precision and is a few parts in 1e10 above the derived first-mode value.
    # A controller target must clear both gates to avoid reporting a nominally
    # selected QPSK 1/4 mode as unserved.
    return max(mode.threshold_linear, SINR_MIN)


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
    "rate_target_mode",
    "rate_target_sinr",
    "select_mode",
    "served_phy",
]
