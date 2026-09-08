"""Partial-payload energy accounting for the V0.25 engine."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping

from mcrl.errors import MCRLContractError

from .architectures import BeamIdentity
from .constants_v025 import (
    BASEBAND_POWER_PER_ACTIVE_SATELLITE_W,
    BEAM_RF_CAP_W,
    CIRCUIT_POWER_PER_CHAIN_W,
    PA_MAX_EFFICIENCY,
    PA_SATURATION_POWER_W,
    P_BUS_W,
    STANDBY_FRACTION,
)


def pa_efficiency(rf_power_w: float) -> float:
    """Square-root PA efficiency; zero RF has zero efficiency."""

    if not math.isfinite(rf_power_w) or rf_power_w < 0.0:
        raise MCRLContractError("RF power must be finite and nonnegative")
    if rf_power_w == 0.0:
        return 0.0
    return min(PA_MAX_EFFICIENCY, PA_MAX_EFFICIENCY * math.sqrt(rf_power_w / PA_SATURATION_POWER_W))


def pa_supply_power_w(rf_power_w: float) -> float:
    """``sqrt(p*p_sat)/eta_max`` for positive RF, exactly zero at zero."""

    if not math.isfinite(rf_power_w) or rf_power_w < 0.0:
        raise MCRLContractError("RF power must be finite and nonnegative")
    return 0.0 if rf_power_w == 0.0 else math.sqrt(rf_power_w * PA_SATURATION_POWER_W) / PA_MAX_EFFICIENCY


PRIMARY_IDLE_POWER_W = 0.0
SENSITIVITY_IDLE_POWER_W = STANDBY_FRACTION * pa_supply_power_w(BEAM_RF_CAP_W)


@dataclass(frozen=True)
class HardwareInventory:
    """Physical beam-chain identities fixed before actions and horizons."""

    chains: tuple[BeamIdentity, ...]

    def __post_init__(self) -> None:
        if len(set(self.chains)) != len(self.chains):
            raise MCRLContractError("hardware inventory contains duplicate identities")
        if tuple(sorted(self.chains)) != self.chains:
            raise MCRLContractError("hardware inventory must use frozen sorted identity order")
        if any(len(identity) != 2 for identity in self.chains):
            raise MCRLContractError("inventory identities must be (NORAD, beam-chain)")

    @classmethod
    def fixed(cls, identities: Iterable[BeamIdentity]) -> "HardwareInventory":
        return cls(tuple(sorted((int(norad), int(chain)) for norad, chain in identities)))


@dataclass(frozen=True)
class EnergyInterval:
    duration_s: float
    beam_rf_w: Mapping[BeamIdentity, float]


@dataclass(frozen=True)
class EnergyReceipt:
    joules: float
    pa_j: float
    circuit_j: float
    standby_j: float
    baseband_j: float
    bus_j: float

    def verify(self) -> None:
        components = (self.pa_j, self.circuit_j, self.standby_j, self.baseband_j, self.bus_j)
        if any(not math.isfinite(value) or value < 0.0 for value in components):
            raise MCRLContractError("energy components must be finite and nonnegative")
        if not math.isclose(math.fsum(components), self.joules, rel_tol=0.0, abs_tol=1.0e-12):
            raise MCRLContractError("energy receipt components do not sum to joules")


def interval_energy(
    inventory: HardwareInventory,
    interval: EnergyInterval,
    *,
    idle_power_w: float = PRIMARY_IDLE_POWER_W,
    bus_power_w: float = P_BUS_W,
) -> EnergyReceipt:
    """Evaluate the declared physical-inventory formula for one interval."""

    if not math.isfinite(interval.duration_s) or interval.duration_s < 0.0:
        raise MCRLContractError("interval duration must be finite and nonnegative")
    if not math.isfinite(idle_power_w) or idle_power_w < 0.0:
        raise MCRLContractError("idle power must be finite and nonnegative")
    if bus_power_w != 0.0:
        raise MCRLContractError("V0.25 stage-1 endpoint declares P_bus=0 exclusion")
    inventory_set = set(inventory.chains)
    supplied = set(interval.beam_rf_w)
    if not supplied <= inventory_set:
        raise MCRLContractError("radiation names a chain outside the fixed inventory")
    if any(not math.isfinite(value) or value < 0.0 for value in interval.beam_rf_w.values()):
        raise MCRLContractError("beam RF values must be finite and nonnegative")
    duration = interval.duration_s
    pa_j = circuit_j = standby_j = 0.0
    active_satellites: set[int] = set()
    for identity in inventory.chains:
        rf = float(interval.beam_rf_w.get(identity, 0.0))
        if rf > 0.0:
            active_satellites.add(identity[0])
            pa_j += max(idle_power_w, pa_supply_power_w(rf)) * duration
            circuit_j += CIRCUIT_POWER_PER_CHAIN_W * duration
        else:
            standby_j += idle_power_w * duration
    baseband_j = len(active_satellites) * BASEBAND_POWER_PER_ACTIVE_SATELLITE_W * duration
    receipt = EnergyReceipt(
        math.fsum((pa_j, circuit_j, standby_j, baseband_j)),
        pa_j,
        circuit_j,
        standby_j,
        baseband_j,
        0.0,
    )
    receipt.verify()
    return receipt


def schedule_energy(
    inventory: HardwareInventory,
    slots: Iterable[tuple[float, Mapping[BeamIdentity, float]]],
    *,
    duration_s: float,
    idle_power_w: float = PRIMARY_IDLE_POWER_W,
) -> EnergyReceipt:
    """Integrate a slot schedule, preserving nonlinear PA averaging."""

    schedule = tuple(slots)
    if any(not math.isfinite(fraction) or fraction < 0.0 for fraction, _ in schedule):
        raise MCRLContractError("slot fractions must be finite and nonnegative")
    if not math.isclose(math.fsum(fraction for fraction, _ in schedule), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise MCRLContractError("slot fractions must sum to one")
    receipts = [
        interval_energy(
            inventory,
            EnergyInterval(duration_s * fraction, beam_rf),
            idle_power_w=idle_power_w,
        )
        for fraction, beam_rf in schedule
    ]
    result = EnergyReceipt(
        *(math.fsum(getattr(receipt, field) for receipt in receipts) for field in (
            "joules", "pa_j", "circuit_j", "standby_j", "baseband_j", "bus_j"
        ))
    )
    result.verify()
    return result


def event_energy_sensitivity(
    event_counts: Mapping[str, int], event_cost_j: Mapping[str, float]
) -> float:
    """Separately named extension; primary V0.25 energy never calls this."""

    if set(event_counts) != set(event_cost_j):
        raise MCRLContractError("event counts and sensitivity costs must share keys")
    if any(type(count) is not int or count < 0 for count in event_counts.values()):
        raise MCRLContractError("event counts must be nonnegative exact integers")
    if any(not math.isfinite(cost) or cost < 0.0 for cost in event_cost_j.values()):
        raise MCRLContractError("event sensitivity costs must be finite and nonnegative")
    return math.fsum(event_counts[name] * event_cost_j[name] for name in sorted(event_counts))


__all__ = [
    "EnergyInterval",
    "EnergyReceipt",
    "HardwareInventory",
    "PRIMARY_IDLE_POWER_W",
    "SENSITIVITY_IDLE_POWER_W",
    "interval_energy",
    "pa_efficiency",
    "pa_supply_power_w",
    "schedule_energy",
    "event_energy_sensitivity",
]
