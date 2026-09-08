"""Five V0.25 radiation architectures behind one immutable interface."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal, Protocol

import numpy as np

from mcrl.errors import MCRLContractError

from .acm import ACMRate, rate_target_sinr
from .channel import noise_power_w
from .constants_v025 import (
    BEAM_BANDWIDTH_HZ,
    BEAM_RF_CAP_W,
    POWER_CONTROL_TARGET_LINEAR,
    RATE_TARGET_BPS,
    POWER_SOLVER_ITERATION_CAP,
    POWER_SOLVER_TOLERANCE_W,
)

BeamIdentity = tuple[int, int]
FieldKind = Literal["nominal", "realised"]
ArchitectureCode = Literal["b", "a-\u03b3", "a\u2032-\u03b3", "a-r", "a\u2032-r"]


@dataclass(frozen=True)
class Link:
    """One attempted user link and its physical beam identity."""

    user_id: int
    beam: BeamIdentity
    color: int
    nominal_gain: float
    realised_gain: float | None = None

    def __post_init__(self) -> None:
        if type(self.user_id) is not int or self.user_id < 0:
            raise MCRLContractError("user_id must be a nonnegative exact integer")
        if len(self.beam) != 2 or any(type(value) is not int for value in self.beam):
            raise MCRLContractError("beam must be the physical (NORAD, chain) identity")
        if type(self.color) is not int or self.color < 0:
            raise MCRLContractError("color must be a nonnegative exact integer")
        for label, value in (
            ("nominal_gain", self.nominal_gain),
            ("realised_gain", self.realised_gain),
        ):
            if value is not None and (not math.isfinite(value) or value <= 0.0):
                raise MCRLContractError(f"{label} must be finite and positive")


@dataclass(frozen=True)
class Geometry:
    """A history-free scheduled geometry sample.

    Cross-gain entry ``[victim, aggressor]`` is received watts per aggressor
    RF watt before colour, serving-beam, and waveform-overlap masks.
    """

    links: tuple[Link, ...]
    nominal_cross_gain: np.ndarray
    realised_cross_gain: np.ndarray | None = None

    def __post_init__(self) -> None:
        users = len(self.links)
        if users == 0:
            if np.asarray(self.nominal_cross_gain).shape != (0, 0):
                raise MCRLContractError("empty geometry needs a (0,0) cross-gain matrix")
            empty = np.zeros((0, 0), dtype=np.float64)
            empty.setflags(write=False)
            object.__setattr__(self, "nominal_cross_gain", empty)
            object.__setattr__(self, "realised_cross_gain", None)
            return
        ids = [link.user_id for link in self.links]
        if len(set(ids)) != users:
            raise MCRLContractError("user identities must be unique")
        for name in ("nominal_cross_gain", "realised_cross_gain"):
            value = getattr(self, name)
            if value is None:
                continue
            matrix = np.asarray(value, dtype=np.float64)
            if matrix.shape != (users, users):
                raise MCRLContractError(f"{name} must have shape ({users},{users})")
            if not np.all(np.isfinite(matrix)) or np.any(matrix < 0.0):
                raise MCRLContractError(f"{name} must be finite and nonnegative")
            frozen = np.array(matrix, copy=True)
            frozen.setflags(write=False)
            object.__setattr__(self, name, frozen)

    def gains(self, field: FieldKind) -> np.ndarray:
        if field == "nominal":
            return np.asarray([link.nominal_gain for link in self.links], dtype=np.float64)
        return np.asarray(
            [
                link.nominal_gain if link.realised_gain is None else link.realised_gain
                for link in self.links
            ],
            dtype=np.float64,
        )

    def cross(self, field: FieldKind) -> np.ndarray:
        if field == "realised" and self.realised_cross_gain is not None:
            return np.asarray(self.realised_cross_gain, dtype=np.float64)
        return np.asarray(self.nominal_cross_gain, dtype=np.float64)


@dataclass(frozen=True)
class RadiationConfig:
    bandwidth_hz: float = BEAM_BANDWIDTH_HZ
    beam_cap_w: float = BEAM_RF_CAP_W
    target_sinr: float = POWER_CONTROL_TARGET_LINEAR
    rate_target_bps: float = RATE_TARGET_BPS
    solver_tolerance_w: float = POWER_SOLVER_TOLERANCE_W
    solver_iteration_cap: int = POWER_SOLVER_ITERATION_CAP

    def __post_init__(self) -> None:
        scalars = (
            self.bandwidth_hz,
            self.beam_cap_w,
            self.target_sinr,
            self.rate_target_bps,
            self.solver_tolerance_w,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in scalars):
            raise MCRLContractError("radiation configuration values must be positive")
        if type(self.solver_iteration_cap) is not int or self.solver_iteration_cap < 1:
            raise MCRLContractError("solver_iteration_cap must be a positive integer")


@dataclass(frozen=True)
class PowerCertificate:
    status: Literal["FIXED", "CONVERGED", "INVALID"]
    iterations: int
    residual_w: float
    tolerance_w: float
    saturated_users: tuple[int, ...] = ()

    @property
    def valid(self) -> bool:
        return self.status != "INVALID"


@dataclass(frozen=True)
class Transmission:
    user_id: int
    beam: BeamIdentity
    rf_power_w: float
    wanted_w: float
    intra_interference_w: float
    inter_interference_w: float
    noise_w: float
    bandwidth_hz: float
    subband: tuple[float, float]
    rate_target_bps: float | None = None
    rate_target_sinr: float | None = None
    rate_target_feasible: bool | None = None

    @property
    def interference_w(self) -> float:
        return self.intra_interference_w + self.inter_interference_w

    @property
    def sinr(self) -> float:
        return self.wanted_w / (self.interference_w + self.noise_w)


@dataclass(frozen=True)
class RadiationSlot:
    start_fraction: float
    end_fraction: float
    beam_rf_w: tuple[tuple[BeamIdentity, float], ...]
    transmissions: tuple[Transmission, ...]
    certificate: PowerCertificate

    @property
    def fraction(self) -> float:
        return self.end_fraction - self.start_fraction


@dataclass(frozen=True)
class RadiationResult:
    architecture: ArchitectureCode
    field: FieldKind
    slots: tuple[RadiationSlot, ...]
    certificate: PowerCertificate
    rate_target_bps: float | None = None

    @property
    def valid(self) -> bool:
        return self.certificate.valid

    @property
    def per_user_wanted_w(self) -> dict[int, float]:
        result: dict[int, float] = {}
        for slot in self.slots:
            for tx in slot.transmissions:
                result[tx.user_id] = result.get(tx.user_id, 0.0) + slot.fraction * tx.wanted_w
        return result

    @property
    def per_user_interference_w(self) -> dict[int, tuple[float, float]]:
        result: dict[int, tuple[float, float]] = {}
        for slot in self.slots:
            for tx in slot.transmissions:
                old = result.get(tx.user_id, (0.0, 0.0))
                result[tx.user_id] = (
                    old[0] + slot.fraction * tx.intra_interference_w,
                    old[1] + slot.fraction * tx.inter_interference_w,
                )
        return result

    @property
    def per_user_rate_target_feasible(self) -> dict[int, bool] | None:
        """Controller feasibility by user, distinct from realised PHY service."""

        rows: dict[int, bool] = {}
        saw_target = False
        for slot in self.slots:
            for tx in slot.transmissions:
                if tx.rate_target_feasible is None:
                    continue
                saw_target = True
                rows[tx.user_id] = rows.get(tx.user_id, True) and tx.rate_target_feasible
        return rows if saw_target or self.rate_target_bps is not None else None

    @property
    def rate_target_attained(self) -> dict[int, bool] | None:
        """Realised achieved-ACM target status over this normalized user-step."""

        transmission_targets = {
            tx.rate_target_bps
            for slot in self.slots
            for tx in slot.transmissions
            if tx.rate_target_bps is not None
        }
        if self.rate_target_bps is None:
            if transmission_targets:
                raise MCRLContractError("non-target radiation contains a rate target")
            return None
        if transmission_targets and transmission_targets != {self.rate_target_bps}:
            raise MCRLContractError("radiation result contains inconsistent rate targets")
        target = self.rate_target_bps
        rates: dict[int, float] = {}
        model = ACMRate()
        for slot in self.slots:
            for tx in slot.transmissions:
                rates.setdefault(tx.user_id, 0.0)
                if model.served(tx.sinr, allocated=True):
                    rates[tx.user_id] += slot.fraction * model.rate_bps(
                        tx.sinr, tx.bandwidth_hz
                    )
        return {user: rate >= target for user, rate in rates.items()}


class RadiationArchitecture(Protocol):
    code: ArchitectureCode

    def radiate(
        self,
        config: RadiationConfig,
        geometry: Geometry,
        nominal_or_realised: FieldKind,
    ) -> RadiationResult: ...


def _beam_members(geometry: Geometry) -> dict[BeamIdentity, tuple[int, ...]]:
    grouped: dict[BeamIdentity, list[int]] = {}
    for index, link in enumerate(geometry.links):
        grouped.setdefault(link.beam, []).append(index)
    return {
        beam: tuple(sorted(indices, key=lambda index: geometry.links[index].user_id))
        for beam, indices in sorted(grouped.items())
    }


def _tdm_slots(geometry: Geometry) -> tuple[tuple[float, float, tuple[int, ...]], ...]:
    grouped = _beam_members(geometry)
    if not grouped:
        return ((0.0, 1.0, ()),)
    boundaries = {0.0, 1.0}
    for members in grouped.values():
        boundaries.update(offset / len(members) for offset in range(1, len(members)))
    ordered = sorted(boundaries)
    result = []
    for start, end in zip(ordered, ordered[1:]):
        midpoint = (start + end) / 2.0
        active = tuple(
            members[min(int(midpoint * len(members)), len(members) - 1)]
            for members in grouped.values()
        )
        result.append((start, end, active))
    return tuple(result)


def _masked_coupling(
    geometry: Geometry,
    active: tuple[int, ...],
    field: FieldKind,
    overlap: np.ndarray | None = None,
) -> np.ndarray:
    count = len(active)
    coupling = np.zeros((count, count), dtype=np.float64)
    cross = geometry.cross(field)
    for row, victim in enumerate(active):
        victim_link = geometry.links[victim]
        for column, aggressor in enumerate(active):
            aggressor_link = geometry.links[aggressor]
            if victim == aggressor or victim_link.beam == aggressor_link.beam:
                continue
            if victim_link.color != aggressor_link.color:
                continue
            factor = 1.0 if overlap is None else float(overlap[row, column])
            coupling[row, column] = cross[victim, aggressor] * factor
    return coupling


def _solve_power(
    direct: np.ndarray,
    coupling: np.ndarray,
    noise: np.ndarray,
    caps: np.ndarray,
    active_user_ids: tuple[int, ...],
    config: RadiationConfig,
    *,
    target_sinr: np.ndarray | None = None,
    force_cap: np.ndarray | None = None,
    enforce_target_clearance: bool = False,
) -> tuple[np.ndarray, PowerCertificate]:
    """Capped standard-interference fixed point, always initialised at zero."""

    targets = (
        np.full(len(active_user_ids), config.target_sinr, dtype=np.float64)
        if target_sinr is None
        else np.asarray(target_sinr, dtype=np.float64)
    )
    forced = (
        np.zeros(len(active_user_ids), dtype=np.bool_)
        if force_cap is None
        else np.asarray(force_cap, dtype=np.bool_)
    )
    if targets.shape != caps.shape or forced.shape != caps.shape:
        raise MCRLContractError("power target, forced-cap mask, and caps must share shape")
    power = np.zeros(len(active_user_ids), dtype=np.float64)
    residual = math.inf
    for iteration in range(1, config.solver_iteration_cap + 1):
        updated = np.minimum(caps, targets * (noise + coupling @ power) / direct)
        updated[forced] = caps[forced]
        residual = float(np.max(np.abs(updated - power))) if power.size else 0.0
        power = updated
        clears_target = True
        if enforce_target_clearance and power.size:
            achieved_sinr = power * direct / (noise + coupling @ power)
            clears_target = bool(
                np.all(
                    forced
                    | (power == caps)
                    | (achieved_sinr >= np.nextafter(targets, -np.inf))
                )
            )
        if residual <= config.solver_tolerance_w and clears_target:
            break
    else:
        certificate = PowerCertificate(
            "INVALID",
            config.solver_iteration_cap,
            residual,
            config.solver_tolerance_w,
            tuple(active_user_ids[index] for index in np.flatnonzero(power >= caps)),
        )
        return power, certificate
    final = np.minimum(caps, targets * (noise + coupling @ power) / direct)
    final[forced] = caps[forced]
    final_residual = float(np.max(np.abs(final - power))) if power.size else 0.0
    status: Literal["CONVERGED", "INVALID"] = (
        "CONVERGED" if final_residual <= config.solver_tolerance_w else "INVALID"
    )
    return power, PowerCertificate(
        status,
        iteration,
        final_residual,
        config.solver_tolerance_w,
        tuple(active_user_ids[index] for index in np.flatnonzero(power >= caps - config.solver_tolerance_w)),
    )


def _transmissions(
    geometry: Geometry,
    active: tuple[int, ...],
    power: np.ndarray,
    direct: np.ndarray,
    coupling: np.ndarray,
    noise: np.ndarray,
    bandwidth: np.ndarray,
    subbands: tuple[tuple[float, float], ...],
    *,
    rate_target_bps: float | None = None,
    rate_target_sinr_values: tuple[float | None, ...] | None = None,
    rate_target_feasible: tuple[bool, ...] | None = None,
) -> tuple[Transmission, ...]:
    rows = []
    for row, index in enumerate(active):
        link = geometry.links[index]
        intra = 0.0
        inter = 0.0
        for column, aggressor in enumerate(active):
            term = coupling[row, column] * power[column]
            if geometry.links[aggressor].beam[0] == link.beam[0]:
                intra += term
            else:
                inter += term
        rows.append(
            Transmission(
                user_id=link.user_id,
                beam=link.beam,
                rf_power_w=float(power[row]),
                wanted_w=float(power[row] * direct[row]),
                intra_interference_w=float(intra),
                inter_interference_w=float(inter),
                noise_w=float(noise[row]),
                bandwidth_hz=float(bandwidth[row]),
                subband=subbands[row],
                rate_target_bps=rate_target_bps,
                rate_target_sinr=(
                    None if rate_target_sinr_values is None else rate_target_sinr_values[row]
                ),
                rate_target_feasible=(
                    None if rate_target_feasible is None else rate_target_feasible[row]
                ),
            )
        )
    return tuple(rows)


def _aggregate_certificates(certificates: list[PowerCertificate]) -> PowerCertificate:
    if not certificates:
        return PowerCertificate("FIXED", 0, 0.0, POWER_SOLVER_TOLERANCE_W)
    invalid = any(c.status == "INVALID" for c in certificates)
    statuses = {c.status for c in certificates}
    status: Literal["FIXED", "CONVERGED", "INVALID"] = (
        "INVALID" if invalid else "FIXED" if statuses == {"FIXED"} else "CONVERGED"
    )
    return PowerCertificate(
        status,
        sum(c.iterations for c in certificates),
        max(c.residual_w for c in certificates),
        certificates[0].tolerance_w,
        tuple(sorted({uid for c in certificates for uid in c.saturated_users})),
    )


class FixedRF:
    """Architecture b: fixed 1.65-W RF per active full-band TDM beam."""

    code: Literal["b"] = "b"

    def radiate(
        self, config: RadiationConfig, geometry: Geometry, nominal_or_realised: FieldKind
    ) -> RadiationResult:
        direct_all = geometry.gains(nominal_or_realised)
        slots: list[RadiationSlot] = []
        certificates: list[PowerCertificate] = []
        for start, end, active in _tdm_slots(geometry):
            power = np.full(len(active), config.beam_cap_w, dtype=np.float64)
            direct = direct_all[list(active)] if active else np.zeros(0)
            coupling = _masked_coupling(geometry, active, nominal_or_realised)
            noise = np.full(len(active), noise_power_w(config.bandwidth_hz))
            bandwidth = np.full(len(active), config.bandwidth_hz)
            certificate = PowerCertificate("FIXED", 0, 0.0, config.solver_tolerance_w)
            certificates.append(certificate)
            slots.append(
                RadiationSlot(
                    start,
                    end,
                    tuple((geometry.links[index].beam, config.beam_cap_w) for index in active),
                    _transmissions(
                        geometry,
                        active,
                        power,
                        direct,
                        coupling,
                        noise,
                        bandwidth,
                        tuple((0.0, config.bandwidth_hz) for _ in active),
                    ),
                    certificate,
                )
            )
        return RadiationResult(self.code, nominal_or_realised, tuple(slots), _aggregate_certificates(certificates))


class AngleTPC_TDM:
    """Architecture a: nominal target-SINR power control with full-band TDM."""

    code: Literal["a-\u03b3"] = "a-\u03b3"

    def radiate(
        self, config: RadiationConfig, geometry: Geometry, nominal_or_realised: FieldKind
    ) -> RadiationResult:
        nominal_direct = geometry.gains("nominal")
        field_direct = geometry.gains(nominal_or_realised)
        slots: list[RadiationSlot] = []
        certificates: list[PowerCertificate] = []
        for start, end, active in _tdm_slots(geometry):
            nominal_coupling = _masked_coupling(geometry, active, "nominal")
            noise = np.full(len(active), noise_power_w(config.bandwidth_hz))
            power, certificate = _solve_power(
                nominal_direct[list(active)] if active else np.zeros(0),
                nominal_coupling,
                noise,
                np.full(len(active), config.beam_cap_w),
                tuple(geometry.links[index].user_id for index in active),
                config,
            )
            certificates.append(certificate)
            field_coupling = _masked_coupling(geometry, active, nominal_or_realised)
            bandwidth = np.full(len(active), config.bandwidth_hz)
            slots.append(
                RadiationSlot(
                    start,
                    end,
                    tuple((geometry.links[index].beam, float(power[row])) for row, index in enumerate(active)),
                    _transmissions(
                        geometry,
                        active,
                        power,
                        field_direct[list(active)] if active else np.zeros(0),
                        field_coupling,
                        noise,
                        bandwidth,
                        tuple((0.0, config.bandwidth_hz) for _ in active),
                    ),
                    certificate,
                )
            )
        return RadiationResult(self.code, nominal_or_realised, tuple(slots), _aggregate_certificates(certificates))


class AngleTPC_FDM:
    """Architecture a-prime: equal FDM subbands and per-user share caps."""

    code: Literal["a\u2032-\u03b3"] = "a\u2032-\u03b3"

    def radiate(
        self, config: RadiationConfig, geometry: Geometry, nominal_or_realised: FieldKind
    ) -> RadiationResult:
        members = _beam_members(geometry)
        active = tuple(index for beam in members.values() for index in beam)
        subband_by_index: dict[int, tuple[float, float]] = {}
        cap_by_index: dict[int, float] = {}
        for beam_members in members.values():
            width = config.bandwidth_hz / len(beam_members)
            for position, index in enumerate(beam_members):
                subband_by_index[index] = (position * width, (position + 1) * width)
                cap_by_index[index] = config.beam_cap_w / len(beam_members)
        subbands = tuple(subband_by_index[index] for index in active)
        bandwidth = np.asarray([high - low for low, high in subbands], dtype=np.float64)
        overlap = np.zeros((len(active), len(active)), dtype=np.float64)
        for row, (victim_low, victim_high) in enumerate(subbands):
            for column, (aggressor_low, aggressor_high) in enumerate(subbands):
                overlap_hz = max(0.0, min(victim_high, aggressor_high) - max(victim_low, aggressor_low))
                aggressor_bandwidth = aggressor_high - aggressor_low
                overlap[row, column] = overlap_hz / aggressor_bandwidth
        nominal_coupling = _masked_coupling(geometry, active, "nominal", overlap)
        noise = np.asarray([noise_power_w(value) for value in bandwidth])
        power, certificate = _solve_power(
            geometry.gains("nominal")[list(active)] if active else np.zeros(0),
            nominal_coupling,
            noise,
            np.asarray([cap_by_index[index] for index in active]),
            tuple(geometry.links[index].user_id for index in active),
            config,
        )
        beam_power: dict[BeamIdentity, float] = {}
        for row, index in enumerate(active):
            beam = geometry.links[index].beam
            beam_power[beam] = beam_power.get(beam, 0.0) + float(power[row])
        if any(value > config.beam_cap_w + config.solver_tolerance_w for value in beam_power.values()):
            raise MCRLContractError("FDM allocation exceeded the per-beam RF cap")
        field_coupling = _masked_coupling(geometry, active, nominal_or_realised, overlap)
        slot = RadiationSlot(
            0.0,
            1.0,
            tuple(sorted(beam_power.items())),
            _transmissions(
                geometry,
                active,
                power,
                geometry.gains(nominal_or_realised)[list(active)] if active else np.zeros(0),
                field_coupling,
                noise,
                bandwidth,
                subbands,
            ),
            certificate,
        )
        return RadiationResult(self.code, nominal_or_realised, (slot,), certificate)


def _rate_targets(
    config: RadiationConfig,
    geometry: Geometry,
    active: tuple[int, ...],
    members: dict[BeamIdentity, tuple[int, ...]],
) -> tuple[np.ndarray, np.ndarray, tuple[float | None, ...]]:
    """Build per-user ACM targets and the explicit no-mode forced-cap mask."""

    values: list[float] = []
    forced: list[bool] = []
    reported: list[float | None] = []
    for index in active:
        occupancy = len(members[geometry.links[index].beam])
        gamma = rate_target_sinr(
            config.rate_target_bps,
            config.bandwidth_hz,
            occupancy,
        )
        reported.append(gamma)
        forced.append(gamma is None)
        values.append(1.0 if gamma is None else gamma)
    return (
        np.asarray(values, dtype=np.float64),
        np.asarray(forced, dtype=np.bool_),
        tuple(reported),
    )


def _target_feasibility(
    power: np.ndarray,
    direct: np.ndarray,
    coupling: np.ndarray,
    noise: np.ndarray,
    target_sinr_values: tuple[float | None, ...],
) -> tuple[bool, ...]:
    denominators = noise + coupling @ power
    actual = power * direct / denominators
    return tuple(
        gamma is not None and value >= gamma
        for value, gamma in zip(actual, target_sinr_values)
    )


class AngleRateTPC_TDM:
    """Architecture a-r: per-user ACM rate target over full-band TDM."""

    code: Literal["a-r"] = "a-r"

    def radiate(
        self, config: RadiationConfig, geometry: Geometry, nominal_or_realised: FieldKind
    ) -> RadiationResult:
        members = _beam_members(geometry)
        nominal_direct_all = geometry.gains("nominal")
        field_direct_all = geometry.gains(nominal_or_realised)
        slots: list[RadiationSlot] = []
        certificates: list[PowerCertificate] = []
        for start, end, active in _tdm_slots(geometry):
            nominal_direct = nominal_direct_all[list(active)] if active else np.zeros(0)
            nominal_coupling = _masked_coupling(geometry, active, "nominal")
            noise = np.full(len(active), noise_power_w(config.bandwidth_hz))
            targets, forced, reported_targets = _rate_targets(
                config, geometry, active, members
            )
            caps = np.full(len(active), config.beam_cap_w)
            power, certificate = _solve_power(
                nominal_direct,
                nominal_coupling,
                noise,
                caps,
                tuple(geometry.links[index].user_id for index in active),
                config,
                target_sinr=targets,
                force_cap=forced,
                enforce_target_clearance=True,
            )
            certificates.append(certificate)
            field_coupling = _masked_coupling(geometry, active, nominal_or_realised)
            bandwidth = np.full(len(active), config.bandwidth_hz)
            slots.append(
                RadiationSlot(
                    start,
                    end,
                    tuple(
                        (geometry.links[index].beam, float(power[row]))
                        for row, index in enumerate(active)
                    ),
                    _transmissions(
                        geometry,
                        active,
                        power,
                        field_direct_all[list(active)] if active else np.zeros(0),
                        field_coupling,
                        noise,
                        bandwidth,
                        tuple((0.0, config.bandwidth_hz) for _ in active),
                        rate_target_bps=config.rate_target_bps,
                        rate_target_sinr_values=reported_targets,
                        rate_target_feasible=_target_feasibility(
                            power,
                            nominal_direct,
                            nominal_coupling,
                            noise,
                            reported_targets,
                        ),
                    ),
                    certificate,
                )
            )
        return RadiationResult(
            self.code,
            nominal_or_realised,
            tuple(slots),
            _aggregate_certificates(certificates),
            config.rate_target_bps,
        )


class AngleRateTPC_FDM:
    """Architecture a-prime-r: ACM rate target over equal physical sub-bands."""

    code: Literal["a\u2032-r"] = "a\u2032-r"

    def radiate(
        self, config: RadiationConfig, geometry: Geometry, nominal_or_realised: FieldKind
    ) -> RadiationResult:
        members = _beam_members(geometry)
        active = tuple(index for beam in members.values() for index in beam)
        subband_by_index: dict[int, tuple[float, float]] = {}
        cap_by_index: dict[int, float] = {}
        for beam_members in members.values():
            width = config.bandwidth_hz / len(beam_members)
            for position, index in enumerate(beam_members):
                subband_by_index[index] = (position * width, (position + 1) * width)
                cap_by_index[index] = config.beam_cap_w / len(beam_members)
        subbands = tuple(subband_by_index[index] for index in active)
        bandwidth = np.asarray([high - low for low, high in subbands], dtype=np.float64)
        overlap = np.zeros((len(active), len(active)), dtype=np.float64)
        for row, (victim_low, victim_high) in enumerate(subbands):
            for column, (aggressor_low, aggressor_high) in enumerate(subbands):
                overlap_hz = max(
                    0.0,
                    min(victim_high, aggressor_high) - max(victim_low, aggressor_low),
                )
                overlap[row, column] = overlap_hz / (aggressor_high - aggressor_low)
        nominal_direct = (
            geometry.gains("nominal")[list(active)] if active else np.zeros(0)
        )
        nominal_coupling = _masked_coupling(geometry, active, "nominal", overlap)
        noise = np.asarray([noise_power_w(value) for value in bandwidth])
        targets, forced, reported_targets = _rate_targets(
            config, geometry, active, members
        )
        caps = np.asarray([cap_by_index[index] for index in active])
        power, certificate = _solve_power(
            nominal_direct,
            nominal_coupling,
            noise,
            caps,
            tuple(geometry.links[index].user_id for index in active),
            config,
            target_sinr=targets,
            force_cap=forced,
            enforce_target_clearance=True,
        )
        beam_power: dict[BeamIdentity, float] = {}
        for row, index in enumerate(active):
            beam = geometry.links[index].beam
            beam_power[beam] = beam_power.get(beam, 0.0) + float(power[row])
        if any(
            value > config.beam_cap_w + config.solver_tolerance_w
            for value in beam_power.values()
        ):
            raise MCRLContractError("rate-target FDM allocation exceeded the per-beam RF cap")
        field_coupling = _masked_coupling(
            geometry, active, nominal_or_realised, overlap
        )
        slot = RadiationSlot(
            0.0,
            1.0,
            tuple(sorted(beam_power.items())),
            _transmissions(
                geometry,
                active,
                power,
                geometry.gains(nominal_or_realised)[list(active)]
                if active
                else np.zeros(0),
                field_coupling,
                noise,
                bandwidth,
                subbands,
                rate_target_bps=config.rate_target_bps,
                rate_target_sinr_values=reported_targets,
                rate_target_feasible=_target_feasibility(
                    power,
                    nominal_direct,
                    nominal_coupling,
                    noise,
                    reported_targets,
                ),
            ),
            certificate,
        )
        return RadiationResult(
            self.code,
            nominal_or_realised,
            (slot,),
            certificate,
            config.rate_target_bps,
        )


def architecture_for(code: str) -> RadiationArchitecture:
    """Return the declared architecture without aliases or module mutation."""

    if code == "b":
        return FixedRF()
    if code == "a-\u03b3":
        return AngleTPC_TDM()
    if code == "a\u2032-\u03b3":
        return AngleTPC_FDM()
    if code == "a-r":
        return AngleRateTPC_TDM()
    if code == "a\u2032-r":
        return AngleRateTPC_FDM()
    raise MCRLContractError(f"unknown V0.25 architecture {code!r}")


__all__ = [
    "AngleRateTPC_FDM",
    "AngleRateTPC_TDM",
    "AngleTPC_FDM",
    "AngleTPC_TDM",
    "ArchitectureCode",
    "BeamIdentity",
    "FieldKind",
    "FixedRF",
    "Geometry",
    "Link",
    "PowerCertificate",
    "RadiationArchitecture",
    "RadiationConfig",
    "RadiationResult",
    "RadiationSlot",
    "Transmission",
    "architecture_for",
]
