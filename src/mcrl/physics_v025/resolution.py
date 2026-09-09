"""Single V0.25 resolution order: schedule, radiate, interfere, decode."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

import numpy as np

from .acm import RateModel
from .architectures import (
    FieldKind,
    Geometry,
    RadiationArchitecture,
    RadiationConfig,
    RadiationResult,
)
from .energy import EnergyReceipt, HardwareInventory, schedule_energy
from .tapes import PrimitiveStepArrays

if TYPE_CHECKING:
    from .batch import BatchARResult


@dataclass(frozen=True)
class ResolutionResult:
    radiation: RadiationResult
    average_rate_bps: dict[int, float] | None
    bits: dict[int, float] | None
    decoding_time_fraction: dict[int, float] | None
    complete_service: dict[int, bool] | None
    rate_target_attained: dict[int, bool] | None
    rate_target_feasible: dict[int, bool] | None
    energy: EnergyReceipt | None

    @property
    def valid(self) -> bool:
        return self.radiation.valid


def resolve_configuration(
    architecture: RadiationArchitecture | None = None,
    radiation_config: RadiationConfig | None = None,
    geometry: Geometry | None = None,
    rate_model: RateModel | None = None,
    inventory: HardwareInventory | None = None,
    *,
    duration_s: float | None = None,
    field: FieldKind = "realised",
    idle_power_w: float = 0.0,
    batch_arrays: PrimitiveStepArrays | None = None,
    batch_selected_rows: np.ndarray | None = None,
    batch_chunk_size: int = 256,
    batch_rate_target_bps: float | None = None,
    batch_circuit_power_per_active_chain_w: float | None = None,
    batch_boundary_indices: tuple[int, ...] = tuple(range(48)),
) -> ResolutionResult | "BatchARResult":
    """Resolve one scalar configuration or one dense catalogue request."""

    if batch_arrays is not None or batch_selected_rows is not None:
        if batch_arrays is None or batch_selected_rows is None:
            raise ValueError("dense resolution needs arrays and selected rows together")
        if any(
            value is not None
            for value in (architecture, radiation_config, geometry, rate_model, inventory)
        ) or duration_s is not None:
            raise ValueError("dense and scalar resolution inputs cannot be mixed")
        if idle_power_w != 0.0:
            raise ValueError("idle_power_w is a scalar-only resolution input")
        from .batch import _evaluate_ar_tdm_catalogue_core

        kwargs: dict[str, object] = {
            "field": field,
            "chunk_size": batch_chunk_size,
            "boundary_indices": batch_boundary_indices,
        }
        if batch_rate_target_bps is not None:
            kwargs["rate_target_bps"] = batch_rate_target_bps
        if batch_circuit_power_per_active_chain_w is not None:
            kwargs["circuit_power_per_active_chain_w"] = (
                batch_circuit_power_per_active_chain_w
            )
        return _evaluate_ar_tdm_catalogue_core(
            batch_arrays,
            batch_selected_rows,
            **kwargs,
        )

    if (
        batch_chunk_size != 256
        or batch_rate_target_bps is not None
        or batch_circuit_power_per_active_chain_w is not None
        or batch_boundary_indices != tuple(range(48))
    ):
        raise ValueError("batch resolution inputs require arrays and selected rows")

    if any(
        value is None
        for value in (
            architecture,
            radiation_config,
            geometry,
            rate_model,
            inventory,
            duration_s,
        )
    ):
        raise ValueError("scalar resolution inputs are incomplete")

    if not math.isfinite(duration_s) or duration_s < 0.0:
        raise ValueError("duration_s must be finite and nonnegative")
    radiation = architecture.radiate(radiation_config, geometry, field)
    if not radiation.valid:
        return ResolutionResult(radiation, None, None, None, None, None, None, None)

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
    return ResolutionResult(
        radiation,
        rates,
        bits,
        served_fraction,
        complete,
        radiation.rate_target_attained,
        radiation.per_user_rate_target_feasible,
        energy,
    )


__all__ = ["ResolutionResult", "resolve_configuration"]
