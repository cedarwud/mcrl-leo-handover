"""Shared physical-tape adapter for the Track-B lever-matrix runner.

The adapter performs radiation once per architecture/boundary.  Standby,
interruption, and rate treatments rescore immutable radiation fields.  It is
simulator-inert until the caller supplies explicit synthetic or server-owned
geometry tapes.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from typing import Iterable, Mapping, Sequence

from mcrl.errors import MCRLContractError

from .acm import rate_model
from .architectures import FieldKind, Geometry, RadiationConfig, RadiationResult, architecture_for
from .energy import (
    HardwareInventory,
    PRIMARY_IDLE_POWER_W,
    SENSITIVITY_IDLE_POWER_W,
    schedule_energy,
)
from .integration import (
    BoundarySample,
    IntegrationReceipt,
    InterruptionEvent,
    integrate_47_subintervals,
    snapshot_left,
)
from .matrix import PhysicsSetting, shared_computation_plan


@dataclass(frozen=True)
class RadiationBoundary:
    time_s: float
    radiation: RadiationResult


@dataclass(frozen=True)
class SharedArchitectureTape:
    architecture: str
    inventory: HardwareInventory
    integrated: tuple[RadiationBoundary, ...]
    snapshot: RadiationBoundary


@dataclass(frozen=True)
class CellScore:
    setting: PhysicsSetting
    bits: dict[int, float]
    joules: float
    decoding_time_s: dict[int, float]
    useful_time_s: dict[int, float]
    served_phy: dict[int, bool]
    rate_target_attained: dict[int, bool] | None
    rate_target_feasible: dict[int, bool] | None
    rate_target_attainment_by_boundary: tuple[dict[int, bool], ...] | None
    rate_target_bps: float | None
    valid: bool
    certificate_residual_w: float

    def as_profile(self) -> dict[str, object]:
        users = sorted(self.bits)
        return {
            "setting": self.setting.payload(),
            "setting_digest": self.setting.digest,
            "bits": [self.bits[user].hex() for user in users],
            "energy_j": self.joules.hex(),
            "served_PHY": [self.served_phy[user] for user in users],
            "rate_target_attained": (
                None
                if self.rate_target_attained is None
                else [self.rate_target_attained[user] for user in users]
            ),
            "rate_target_feasible": (
                None
                if self.rate_target_feasible is None
                else [self.rate_target_feasible[user] for user in users]
            ),
            "rate_target_attainment_by_boundary": self.rate_target_attainment_by_boundary,
            "rate_target_bps": (
                None if self.rate_target_bps is None else self.rate_target_bps.hex()
            ),
            "users": users,
            "valid": self.valid,
            "solver_residual_w": self.certificate_residual_w.hex(),
        }


def build_shared_tape(
    architecture: str,
    geometry_samples: Sequence[tuple[float, Geometry]],
    inventory: HardwareInventory,
    *,
    config: RadiationConfig = RadiationConfig(),
    field: FieldKind = "realised",
) -> SharedArchitectureTape:
    """Build one 48-boundary tape and its separately named terminal snapshot."""

    engine = architecture_for(architecture)
    boundaries = tuple(
        RadiationBoundary(time_s, engine.radiate(config, geometry, field))
        for time_s, geometry in geometry_samples
    )
    if len(boundaries) != 48:
        raise MCRLContractError("shared integrated tape needs 48 D2 boundaries")
    if any(not boundary.radiation.valid for boundary in boundaries):
        # Keep the invalid certificate in memory for diagnostics but never
        # synthesize a zero-effect cell from it.
        return SharedArchitectureTape(architecture, inventory, boundaries, boundaries[-1])
    return SharedArchitectureTape(architecture, inventory, boundaries, boundaries[0])


def _rescore_boundary(
    boundary: RadiationBoundary,
    inventory: HardwareInventory,
    setting: PhysicsSetting,
) -> BoundarySample:
    model = rate_model(setting.rate)
    users = {
        transmission.user_id
        for slot in boundary.radiation.slots
        for transmission in slot.transmissions
    }
    rates = {user: 0.0 for user in users}
    decoded = {user: True for user in users}
    seen = {user: False for user in users}
    for slot in boundary.radiation.slots:
        for transmission in slot.transmissions:
            seen[transmission.user_id] = True
            passed = model.served(transmission.sinr, allocated=True)
            decoded[transmission.user_id] &= passed
            if passed:
                rates[transmission.user_id] += slot.fraction * model.rate_bps(
                    transmission.sinr, transmission.bandwidth_hz
                )
    decoded = {user: decoded[user] and seen[user] for user in users}
    idle = SENSITIVITY_IDLE_POWER_W if setting.standby == "f" else PRIMARY_IDLE_POWER_W
    energy = schedule_energy(
        inventory,
        ((slot.fraction, dict(slot.beam_rf_w)) for slot in boundary.radiation.slots),
        duration_s=1.0,
        idle_power_w=idle,
    )
    return BoundarySample(boundary.time_s, rates, energy.joules, decoded)


def score_setting(
    tape: SharedArchitectureTape,
    setting: PhysicsSetting,
    *,
    interruptions: Iterable[InterruptionEvent] = (),
) -> CellScore:
    """Rescore a declared cell without recomputing geometry or radiation."""

    if setting.architecture != tape.architecture:
        raise MCRLContractError("setting architecture does not match shared tape")
    residual = max(boundary.radiation.certificate.residual_w for boundary in tape.integrated)
    if any(not boundary.radiation.valid for boundary in tape.integrated):
        return CellScore(
            setting, {}, math.nan, {}, {}, {}, None, None, None, None, False, residual
        )
    if setting.integration == "T":
        point = _rescore_boundary(tape.snapshot, tape.inventory, setting)
        receipt = snapshot_left(point, end_s=tape.integrated[-1].time_s)
    else:
        points = tuple(_rescore_boundary(boundary, tape.inventory, setting) for boundary in tape.integrated)
        receipt = integrate_47_subintervals(
            points,
            interruptions=interruptions,
            interruption_enabled=setting.interruption == "on",
        )
    users = sorted(receipt.bits)
    duration_s = tape.integrated[-1].time_s - tape.integrated[0].time_s
    served_phy = {
        user: receipt.decoding_time_s[user] > 0.0
        for user in users
    }
    is_rate_target = setting.architecture in {"a-r", "a\u2032-r"}
    target_values = {
        boundary.radiation.rate_target_bps
        for boundary in tape.integrated
        if boundary.radiation.rate_target_bps is not None
    }
    if is_rate_target and len(target_values) != 1:
        raise MCRLContractError("rate-target tape must bind exactly one r-star value")
    config_target = next(iter(target_values)) if target_values else None
    attained = (
        {
            user: receipt.bits[user] >= float(config_target) * duration_s
            for user in users
        }
        if is_rate_target
        else None
    )
    feasibility_rows = [
        boundary.radiation.per_user_rate_target_feasible
        for boundary in tape.integrated
    ]
    feasible = (
        {
            user: all(
                row is not None and row.get(user, False)
                for row in feasibility_rows
            )
            for user in users
        }
        if is_rate_target
        else None
    )
    boundary_attainment = (
        tuple(
            boundary.radiation.rate_target_attained or {user: False for user in users}
            for boundary in tape.integrated
        )
        if is_rate_target
        else None
    )
    return CellScore(
        setting,
        receipt.bits,
        receipt.joules,
        receipt.decoding_time_s,
        receipt.useful_time_s,
        served_phy,
        attained,
        feasible,
        boundary_attainment,
        config_target,
        True,
        residual,
    )


def track_b_regeneration_adapter(**context: object) -> object:
    """Dependency-injection hook compatible with Track B's callable seam.

    The server runner supplies ``v025_setting``, ``v025_geometry_samples`` and
    ``v025_inventory``.  The legacy lever metadata is accepted and bound into
    the returned receipt, but never changes the V0.25 setting.
    """

    setting = context.get("v025_setting")
    geometry_samples = context.get("v025_geometry_samples")
    inventory = context.get("v025_inventory")
    if not isinstance(setting, PhysicsSetting):
        raise MCRLContractError("Track-B adapter requires v025_setting")
    if not isinstance(inventory, HardwareInventory):
        raise MCRLContractError("Track-B adapter requires v025_inventory")
    if not isinstance(geometry_samples, Sequence):
        raise MCRLContractError("Track-B adapter requires v025_geometry_samples")
    tape = build_shared_tape(setting.architecture, geometry_samples, inventory)
    score = score_setting(
        tape,
        setting,
        interruptions=context.get("v025_interruptions", ()),  # type: ignore[arg-type]
    )
    return {
        "schema": "mcrl-v025-track-b-adapter-receipt-v1.1",
        "lever_id": context.get("lever_id"),
        "lever_identity": context.get("identity"),
        "keyed_fading_event": context.get("keyed_fading_event"),
        "continuation": context.get("continuation"),
        "profile": score.as_profile() if score.valid else None,
        "status": "COMPLETE" if score.valid else "INVALID",
        "test_split_opened": False,
        "training": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--estimate", action="store_true")
    parser.add_argument("--q", type=float)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.estimate:
        raise SystemExit("only the simulator-inert --estimate mode is available in stage 1")
    print(json.dumps(shared_computation_plan(q=args.q), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CellScore",
    "RadiationBoundary",
    "SharedArchitectureTape",
    "build_shared_tape",
    "score_setting",
    "track_b_regeneration_adapter",
]
