"""Single V0.25 resolution order: schedule, radiate, interfere, decode."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .acm import RateModel
from .architectures import (
    FieldKind,
    Geometry,
    RadiationArchitecture,
    RadiationConfig,
    RadiationResult,
)
from .energy import EnergyReceipt, HardwareInventory, schedule_energy


@dataclass(frozen=True)
class ResolutionResult:
    radiation: RadiationResult
    average_rate_bps: dict[int, float] | None
    bits: dict[int, float] | None
    decoding_time_fraction: dict[int, float] | None
    complete_service: dict[int, bool] | None
    energy: EnergyReceipt | None

    @property
    def valid(self) -> bool:
        return self.radiation.valid


def resolve_configuration(
    architecture: RadiationArchitecture,
    radiation_config: RadiationConfig,
    geometry: Geometry,
    rate_model: RateModel,
    inventory: HardwareInventory,
    *,
    duration_s: float,
    field: FieldKind = "realised",
    idle_power_w: float = 0.0,
) -> ResolutionResult:
    """Resolve all attempts jointly; failed attempts remain in RF and energy."""

    if not math.isfinite(duration_s) or duration_s < 0.0:
        raise ValueError("duration_s must be finite and nonnegative")
    radiation = architecture.radiate(radiation_config, geometry, field)
    if not radiation.valid:
        return ResolutionResult(radiation, None, None, None, None, None)

    rates = {link.user_id: 0.0 for link in geometry.links}
    served_fraction = {link.user_id: 0.0 for link in geometry.links}
    allocated_fraction = {link.user_id: 0.0 for link in geometry.links}
    for slot in radiation.slots:
        for transmission in slot.transmissions:
            allocated_fraction[transmission.user_id] += slot.fraction
            served = rate_model.served(transmission.sinr, allocated=True)
            if served:
                served_fraction[transmission.user_id] += slot.fraction
                rates[transmission.user_id] += slot.fraction * rate_model.rate_bps(
                    transmission.sinr, transmission.bandwidth_hz
                )
            # No branch edits radiation: an unsuccessful attempt continues to
            # interfere and consume exactly the energy already scheduled.
    energy = schedule_energy(
        inventory,
        (
            (slot.fraction, dict(slot.beam_rf_w))
            for slot in radiation.slots
        ),
        duration_s=duration_s,
        idle_power_w=idle_power_w,
    )
    bits = {user: rate * duration_s for user, rate in rates.items()}
    complete = {
        user: allocated_fraction[user] > 0.0
        and math.isclose(served_fraction[user], allocated_fraction[user], rel_tol=0.0, abs_tol=1.0e-15)
        for user in rates
    }
    return ResolutionResult(radiation, rates, bits, served_fraction, complete, energy)


__all__ = ["ResolutionResult", "resolve_configuration"]
