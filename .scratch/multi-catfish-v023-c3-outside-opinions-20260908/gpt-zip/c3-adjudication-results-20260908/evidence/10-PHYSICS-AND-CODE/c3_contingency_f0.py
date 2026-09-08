"""Pure F0 cost-share mechanics for the V0.23 C3 contingency.

This file is intentionally isolated from the V0.23 runner.  It consumes one
complete current-slot physical profile and performs no action selection,
simulation, learning, masking, or deployment work.

The profile uses the same physical fields exposed by ``ActionEvaluation``:
realised user rates and service, the active ``(satellite, cell)`` beams and
their RF powers, and the canonical fixed/system power receipts.  The
per-beam supply power is recomputed with the canonical link-budget functions;
the declared fixed and system powers are then checked against that
recomputation.

Interval convention
-------------------

All profile power fields are watts.  ``interval_s`` is the one current-slot
duration, and multiplying a power by it produces joules.  Therefore the
frozen ladder's ``E(x)`` is ``profile.system_power_w * interval_s`` and the
cost-share function returns both power and interval-energy views.

For a served user ``u`` on beam ``b`` and satellite ``s``:

``share_u(x) =
    (P_supply_b + P_circuit) / U_b
    + P_baseband / U_s``

where ``U_b`` is served occupancy of the beam and ``U_s`` is served
occupancy of the satellite.  An unserved user has exactly zero share.
Summing the first term over users recovers every active beam's supply plus
circuit power; summing the second recovers one baseband charge per active
satellite.  This is the canonical ``P^N`` accounting, not a per-link power
sum.

The targets are exactly the frozen contingency-ladder formulas, expressed in
interval joules:

``z_D = dt * sum_{v != u}(R_v(c) - R_v(b))
       - lambda * ((share_u(c) - share_u(b)) - (E(c) - E(b)))``

``z_F = -lambda * ((share_u(c) - share_u(b)) - (E(c) - E(b)))``

Signed values are retained as computed.  There is no clipping, sign filter,
compatibility gate, or rescaling.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from mcrl.env.constants import DECISION_STEP_S
from mcrl.env.link_budget import (
    BASEBAND_POWER_PER_SATELLITE_W,
    CIRCUIT_POWER_PER_BEAM_W,
    fixed_power_w as _canonical_fixed_power_w,
    pa_efficiency as _canonical_pa_efficiency,
    supply_power_w as _canonical_supply_power_w,
    system_power_w as _canonical_system_power_w,
)
from mcrl.errors import MCRLContractError


F0_SCHEMA = "multi-catfish-mcrl-v023-c3-contingency-f0-cost-share-v1"
"""Schema marker for the isolated, formula-only F0 seam."""

INTERVAL_CONVENTION = "profile-power-w-times-one-interval-to-energy-j"
"""Declared unit convention used by :class:`PhysicalProfile`."""


class C3F0Error(MCRLContractError):
    """An F0 profile, conservation identity, or target violated its contract."""


# Descriptive aliases make the isolated seam discoverable without another
# implementation or a dependency on a runtime integration module.
C3ContingencyF0Error = C3F0Error
CostShareF0Error = C3F0Error


def _readonly(value: object, *, dtype: np.dtype | type, field: str) -> np.ndarray:
    """Copy an array into C order and make the owned copy read-only."""

    try:
        result = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise C3F0Error(f"{field} cannot be materialised") from error
    result.setflags(write=False)
    return result


def _float_scalar(
    value: object,
    *,
    field: str,
    nonnegative: bool = False,
    positive: bool = False,
) -> float:
    """Parse one finite numeric scalar with an explicit domain."""

    if isinstance(value, (bool, np.bool_)):
        raise C3F0Error(f"{field} must be a finite numeric scalar")
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise C3F0Error(f"{field} must be a finite numeric scalar") from error
    if raw.shape != () or raw.dtype == np.dtype("bool"):
        raise C3F0Error(f"{field} must be a finite numeric scalar")
    try:
        result = float(raw)
    except (TypeError, ValueError, OverflowError) as error:
        raise C3F0Error(f"{field} must be a finite numeric scalar") from error
    if not math.isfinite(result):
        raise C3F0Error(f"{field} must be finite")
    if positive and result <= 0.0:
        raise C3F0Error(f"{field} must be positive")
    if nonnegative and result < 0.0:
        raise C3F0Error(f"{field} must be non-negative")
    return result


def _float_vector(
    value: object,
    *,
    field: str,
    shape: tuple[int, ...] | None = None,
    nonnegative: bool = False,
) -> np.ndarray:
    """Parse a finite floating-point array without changing its shape."""

    try:
        raw = np.asarray(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise C3F0Error(f"{field} must be a numeric array") from error
    if raw.dtype == np.dtype("bool"):
        raise C3F0Error(f"{field} must be numeric, not Boolean")
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise C3F0Error(f"{field} must be a finite numeric array") from error
    if shape is not None and result.shape != shape:
        raise C3F0Error(f"{field} must have shape {shape}, got {result.shape}")
    if not np.all(np.isfinite(result)):
        raise C3F0Error(f"{field} must be finite")
    if nonnegative and np.any(result < 0.0):
        raise C3F0Error(f"{field} must be non-negative")
    return np.array(result, dtype=np.float64, copy=True, order="C")


def _bool_vector(value: object, *, field: str, shape: tuple[int, ...]) -> np.ndarray:
    """Parse an exact Boolean vector."""

    try:
        result = np.asarray(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise C3F0Error(f"{field} must be Boolean shape {shape}") from error
    if result.dtype != np.bool_ or result.shape != shape:
        raise C3F0Error(f"{field} must be Boolean shape {shape}")
    return np.array(result, dtype=np.bool_, copy=True, order="C")


def _integer_array(
    value: object,
    *,
    field: str,
    shape: tuple[int, ...] | None = None,
) -> np.ndarray:
    """Parse an exact integer array, rejecting Boolean and float arrays."""

    try:
        result = np.asarray(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise C3F0Error(f"{field} must be an integer array") from error
    if (
        result.dtype == np.dtype("bool")
        or not np.issubdtype(result.dtype, np.integer)
        or (shape is not None and result.shape != shape)
    ):
        suffix = f" shape {shape}" if shape is not None else ""
        raise C3F0Error(f"{field} must be an integer array{suffix}")
    return np.array(result, dtype=np.int64, copy=True, order="C")


def _exact_int(value: object, *, field: str) -> int:
    """Parse one exact Python/NumPy integer, not a Boolean or float."""

    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise C3F0Error(f"{field} must be an integer")
    return int(value)


def _safe_sum(values: object, *, field: str) -> float:
    """Use stable scalar summation and fail closed on non-finite arithmetic."""

    try:
        result = math.fsum(float(value) for value in np.asarray(values).reshape(-1).tolist())
    except (OverflowError, TypeError, ValueError) as error:
        raise C3F0Error(f"{field} arithmetic is non-finite") from error
    if not math.isfinite(result):
        raise C3F0Error(f"{field} arithmetic is non-finite")
    return float(result)


def _safe_difference(left: float, right: float, *, field: str) -> float:
    """Subtract two finite scalars and reject a non-finite result."""

    try:
        result = float(left) - float(right)
    except (OverflowError, TypeError, ValueError) as error:
        raise C3F0Error(f"{field} arithmetic is non-finite") from error
    if not math.isfinite(result):
        raise C3F0Error(f"{field} arithmetic is non-finite")
    return result


def _safe_product(left: float, right: float, *, field: str) -> float:
    """Multiply two finite scalars and reject overflow."""

    try:
        result = float(left) * float(right)
    except (OverflowError, TypeError, ValueError) as error:
        raise C3F0Error(f"{field} arithmetic is non-finite") from error
    if not math.isfinite(result):
        raise C3F0Error(f"{field} arithmetic is non-finite")
    return result


def _safe_array_product(values: np.ndarray, scalar: float, *, field: str) -> np.ndarray:
    """Multiply an array by one scalar under a finite arithmetic guard."""

    with np.errstate(over="raise", invalid="raise"):
        try:
            result = np.asarray(values, dtype=np.float64) * float(scalar)
        except FloatingPointError as error:
            raise C3F0Error(f"{field} arithmetic is non-finite") from error
    if not np.all(np.isfinite(result)):
        raise C3F0Error(f"{field} arithmetic is non-finite")
    return np.array(result, dtype=np.float64, copy=True, order="C")


def _roundoff_tolerance(*values: float) -> float:
    """Bound an identity at a scale appropriate for IEEE-754 summation."""

    scale = max((1.0, *(abs(float(value)) for value in values)))
    return max(1.0e-12, 1024.0 * np.finfo(np.float64).eps * scale)


def _assert_close(left: float, right: float, *, field: str) -> float:
    """Return ``left-right`` or reject a material conservation mismatch."""

    residual = _safe_difference(left, right, field=f"{field} residual")
    tolerance = _roundoff_tolerance(left, right)
    if abs(residual) > tolerance:
        raise C3F0Error(
            f"{field} conservation failed: left={float(left).hex()}, "
            f"right={float(right).hex()}, residual={residual.hex()}, "
            f"tolerance={tolerance.hex()}"
        )
    return residual


def _validate_key_pairs(keys: np.ndarray, *, field: str) -> None:
    """Require compact, non-negative, unique ``(satellite, cell)`` keys."""

    if keys.ndim != 2 or keys.shape[1:] != (2,):
        raise C3F0Error(f"{field} must have shape (B, 2)")
    if np.any(keys < 0):
        raise C3F0Error(f"{field} entries must be non-negative")
    pairs = [tuple(int(value) for value in row) for row in keys.tolist()]
    if len(set(pairs)) != len(pairs):
        raise C3F0Error(f"{field} contains a duplicate physical beam")


def _profile_key(profile: "PhysicalProfile", user: int) -> tuple[int, int]:
    """Return a served user's physical beam key."""

    return (int(profile.serving_satellite[user]), int(profile.serving_cell[user]))


@dataclass(frozen=True)
class PhysicalProfile:
    """One complete current-slot physical profile for the F0 formula seam.

    ``serving_satellite`` and ``serving_cell`` are the realised service
    identity from ``ServiceResolution``.  An unserved user is represented by
    ``served=False`` and both identity entries exactly ``-1``.  The active
    beam arrays are the compact ``RadiatingBeams`` rows; a beam is present iff
    at least one served user occupies it.  Thus beam extinction is represented
    by removing that key from the compact active-beam arrays.

    ``beam_power_w`` is RF power from ``RadiatingBeams.power_w``.  Canonical
    PA efficiency and per-beam supply power are derived from it when the
    profile is evaluated.  ``fixed_power_w`` and ``system_power_w`` are the
    declared receipts from the same physical evaluation and are checked by
    :func:`compute_cost_shares`.
    """

    link_rate_bps: np.ndarray
    served: np.ndarray
    serving_satellite: np.ndarray
    serving_cell: np.ndarray
    active_beam_satellites: np.ndarray
    active_beam_cells: np.ndarray
    beam_power_w: np.ndarray
    fixed_power_w: float
    system_power_w: float
    interval_s: float = DECISION_STEP_S
    schema: str = F0_SCHEMA

    def __post_init__(self) -> None:
        rates = _float_vector(self.link_rate_bps, field="link_rate_bps", nonnegative=True)
        if rates.ndim != 1 or rates.size < 1:
            raise C3F0Error("link_rate_bps must have shape (U,) with U >= 1")
        users = int(rates.size)
        service = _bool_vector(self.served, field="served", shape=(users,))
        serving_satellite = _integer_array(
            self.serving_satellite,
            field="serving_satellite",
            shape=(users,),
        )
        serving_cell = _integer_array(
            self.serving_cell,
            field="serving_cell",
            shape=(users,),
        )
        beam_satellites = _integer_array(
            self.active_beam_satellites,
            field="active_beam_satellites",
        )
        beam_cells = _integer_array(
            self.active_beam_cells,
            field="active_beam_cells",
        )
        if beam_satellites.ndim != 1 or beam_cells.ndim != 1:
            raise C3F0Error("active beam satellite and cell IDs must be one-dimensional")
        if beam_satellites.shape != beam_cells.shape:
            raise C3F0Error("active beam satellite and cell IDs must share a shape")
        beam_count = int(beam_satellites.size)
        beam_power = _float_vector(
            self.beam_power_w,
            field="beam_power_w",
            shape=(beam_count,),
            nonnegative=True,
        )
        _validate_key_pairs(
            np.column_stack((beam_satellites, beam_cells)),
            field="active beam keys",
        )
        fixed = _float_scalar(self.fixed_power_w, field="fixed_power_w", nonnegative=True)
        system = _float_scalar(self.system_power_w, field="system_power_w", nonnegative=True)
        interval = _float_scalar(self.interval_s, field="interval_s", positive=True)

        if np.any(service & ((serving_satellite < 0) | (serving_cell < 0))):
            raise C3F0Error("every served user must have a non-negative physical beam key")
        if np.any(~service & ((serving_satellite != -1) | (serving_cell != -1))):
            raise C3F0Error("unserved users must have serving satellite and cell equal to -1")
        if np.any(~service & (rates != 0.0)):
            raise C3F0Error("unserved users must have exactly zero link rate")

        active_keys = {
            (int(satellite), int(cell))
            for satellite, cell in zip(
                beam_satellites.tolist(), beam_cells.tolist(), strict=True
            )
        }
        occupied_keys: set[tuple[int, int]] = set()
        for user in range(users):
            if not bool(service[user]):
                continue
            key = (int(serving_satellite[user]), int(serving_cell[user]))
            if key not in active_keys:
                raise C3F0Error("a served user points to a beam absent from the active set")
            occupied_keys.add(key)
        if occupied_keys != active_keys:
            raise C3F0Error(
                "active beam set must equal the beams occupied by served users"
            )
        if self.schema != F0_SCHEMA:
            raise C3F0Error("F0 physical profile schema is stale")

        # Profile energy is derived under the declared interval convention;
        # reject finite-looking inputs whose product has already overflowed.
        _safe_product(system, interval, field="system energy")
        _safe_product(fixed, interval, field="fixed energy")

        object.__setattr__(self, "link_rate_bps", _readonly(rates, dtype=np.float64, field="link_rate_bps"))
        object.__setattr__(self, "served", _readonly(service, dtype=np.bool_, field="served"))
        object.__setattr__(self, "serving_satellite", _readonly(serving_satellite, dtype=np.int64, field="serving_satellite"))
        object.__setattr__(self, "serving_cell", _readonly(serving_cell, dtype=np.int64, field="serving_cell"))
        object.__setattr__(self, "active_beam_satellites", _readonly(beam_satellites, dtype=np.int64, field="active_beam_satellites"))
        object.__setattr__(self, "active_beam_cells", _readonly(beam_cells, dtype=np.int64, field="active_beam_cells"))
        object.__setattr__(self, "beam_power_w", _readonly(beam_power, dtype=np.float64, field="beam_power_w"))
        object.__setattr__(self, "fixed_power_w", fixed)
        object.__setattr__(self, "system_power_w", system)
        object.__setattr__(self, "interval_s", interval)

    @property
    def users(self) -> int:
        """Number of users in the profile."""

        return int(self.link_rate_bps.size)

    @property
    def active_beams(self) -> int:
        """Number of compact active/radiating beams."""

        return int(self.beam_power_w.size)

    @property
    def active_beam_keys(self) -> np.ndarray:
        """Read-only compact ``(B, 2)`` ``(satellite, cell)`` keys."""

        return _readonly(
            np.column_stack((self.active_beam_satellites, self.active_beam_cells)),
            dtype=np.int64,
            field="active_beam_keys",
        )

    @property
    def active_satellite_ids(self) -> np.ndarray:
        """Read-only sorted satellites represented by the active beam set."""

        return _readonly(
            np.unique(self.active_beam_satellites),
            dtype=np.int64,
            field="active_satellite_ids",
        )

    @property
    def network_energy_j(self) -> float:
        """Canonical declared network power converted to one interval joules."""

        return _safe_product(self.system_power_w, self.interval_s, field="network energy")

    @property
    def fixed_energy_j(self) -> float:
        """Declared fixed power converted to one interval joules."""

        return _safe_product(self.fixed_power_w, self.interval_s, field="fixed energy")

    def verify_canonical_power(self) -> tuple[float, float]:
        """Return canonical ``(fixed_power_w, system_power_w)`` after checking receipts."""

        canonical = _canonical_power_components(self)
        _assert_close(
            self.fixed_power_w,
            canonical.fixed_power_w,
            field="declared fixed power",
        )
        _assert_close(
            self.system_power_w,
            canonical.system_power_w,
            field="declared system power",
        )
        return canonical.fixed_power_w, canonical.system_power_w


@dataclass(frozen=True)
class _CanonicalPower:
    """Internal canonical per-beam and per-satellite cost ledger."""

    beam_supply_power_w: np.ndarray
    beam_cost_power_w: np.ndarray
    active_satellite_ids: np.ndarray
    fixed_power_w: float
    system_power_w: float


def _canonical_power_components(profile: PhysicalProfile) -> _CanonicalPower:
    """Recompute the source project's per-beam and fixed/system power ledger."""

    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            efficiency = _canonical_pa_efficiency(profile.beam_power_w)
            supply = _canonical_supply_power_w(profile.beam_power_w, efficiency)
            active_satellite_ids = np.unique(profile.active_beam_satellites)
            counts = np.asarray(
                [
                    np.count_nonzero(profile.active_beam_satellites == satellite)
                    for satellite in active_satellite_ids.tolist()
                ],
                dtype=np.float64,
            )
            fixed = _canonical_fixed_power_w(counts)
            system = _canonical_system_power_w(supply, counts)
            beam_cost = np.asarray(supply, dtype=np.float64) + CIRCUIT_POWER_PER_BEAM_W
    except (FloatingPointError, OverflowError, TypeError, ValueError) as error:
        raise C3F0Error("canonical power arithmetic is non-finite or malformed") from error

    if (
        not np.all(np.isfinite(supply))
        or not np.all(np.isfinite(beam_cost))
        or not math.isfinite(float(fixed))
        or not math.isfinite(float(system))
    ):
        raise C3F0Error("canonical power arithmetic is non-finite")
    return _CanonicalPower(
        beam_supply_power_w=_readonly(
            supply,
            dtype=np.float64,
            field="canonical beam supply power",
        ),
        beam_cost_power_w=_readonly(
            beam_cost,
            dtype=np.float64,
            field="canonical beam cost power",
        ),
        active_satellite_ids=_readonly(
            active_satellite_ids,
            dtype=np.int64,
            field="canonical active satellite IDs",
        ),
        fixed_power_w=float(fixed),
        system_power_w=float(system),
    )


@dataclass(frozen=True)
class CostShareResult:
    """Immutable served-user beam/satellite cost shares for one profile."""

    profile: PhysicalProfile
    beam_share_power_w: np.ndarray
    satellite_share_power_w: np.ndarray
    total_share_power_w: np.ndarray
    beam_share_energy_j: np.ndarray
    satellite_share_energy_j: np.ndarray
    total_share_energy_j: np.ndarray
    beam_occupancy: np.ndarray
    satellite_occupancy: np.ndarray
    active_satellite_ids: np.ndarray
    beam_cost_power_w: np.ndarray
    canonical_fixed_power_w: float
    canonical_network_power_w: float
    sum_beam_share_power_w: float
    sum_satellite_share_power_w: float
    sum_share_power_w: float
    conservation_residual_power_w: float
    sum_beam_share_energy_j: float
    sum_satellite_share_energy_j: float
    sum_share_energy_j: float
    conservation_residual_energy_j: float
    schema: str = F0_SCHEMA

    def __post_init__(self) -> None:
        if not isinstance(self.profile, PhysicalProfile):
            raise C3F0Error("CostShareResult.profile must be a PhysicalProfile")
        users = self.profile.users
        beams = self.profile.active_beams
        try:
            raw_active_satellites = np.asarray(self.active_satellite_ids)
        except (TypeError, ValueError, OverflowError) as error:
            raise C3F0Error("active_satellite_ids must be an integer vector") from error
        satellites = int(raw_active_satellites.size)

        vector_fields: tuple[tuple[str, tuple[int, ...], bool], ...] = (
            ("beam_share_power_w", (users,), True),
            ("satellite_share_power_w", (users,), True),
            ("total_share_power_w", (users,), True),
            ("beam_share_energy_j", (users,), True),
            ("satellite_share_energy_j", (users,), True),
            ("total_share_energy_j", (users,), True),
            ("beam_occupancy", (beams,), False),
            ("satellite_occupancy", (satellites,), False),
            ("active_satellite_ids", (satellites,), False),
            ("beam_cost_power_w", (beams,), True),
        )
        sealed: dict[str, np.ndarray] = {}
        for field, shape, nonnegative in vector_fields:
            value = getattr(self, field)
            if field in {"beam_occupancy", "satellite_occupancy", "active_satellite_ids"}:
                array = _integer_array(value, field=field, shape=shape)
                if field != "active_satellite_ids" and np.any(array <= 0):
                    raise C3F0Error(f"{field} must be strictly positive for active entries")
                if field == "active_satellite_ids" and np.any(array < 0):
                    raise C3F0Error("active_satellite_ids must be non-negative")
            else:
                array = _float_vector(
                    value,
                    field=field,
                    shape=shape,
                    nonnegative=nonnegative,
                )
            sealed[field] = array

        scalar_fields = (
            "canonical_fixed_power_w",
            "canonical_network_power_w",
            "sum_beam_share_power_w",
            "sum_satellite_share_power_w",
            "sum_share_power_w",
            "conservation_residual_power_w",
            "sum_beam_share_energy_j",
            "sum_satellite_share_energy_j",
            "sum_share_energy_j",
            "conservation_residual_energy_j",
        )
        scalar_values = {
            field: _float_scalar(
                getattr(self, field),
                field=field,
                nonnegative=field not in {
                    "conservation_residual_power_w",
                    "conservation_residual_energy_j",
                },
            )
            for field in scalar_fields
        }
        if self.schema != F0_SCHEMA:
            raise C3F0Error("cost-share result schema is stale")

        if not np.array_equal(
            sealed["total_share_power_w"],
            sealed["beam_share_power_w"] + sealed["satellite_share_power_w"],
        ):
            raise C3F0Error("total share power does not equal beam plus satellite share")
        expected_total_share_energy = (
            sealed["beam_share_energy_j"] + sealed["satellite_share_energy_j"]
        )
        total_share_energy_residual = np.abs(
            sealed["total_share_energy_j"] - expected_total_share_energy
        )
        total_share_energy_tolerance = _roundoff_tolerance(
            float(np.max(np.abs(sealed["total_share_energy_j"]), initial=0.0)),
            float(np.max(np.abs(expected_total_share_energy), initial=0.0)),
        )
        if np.any(total_share_energy_residual > total_share_energy_tolerance):
            raise C3F0Error("total share energy does not equal beam plus satellite share")
        if not np.array_equal(
            sealed["active_satellite_ids"],
            self.profile.active_satellite_ids,
        ):
            raise C3F0Error("active satellite IDs do not match the physical profile")

        for field, array in sealed.items():
            dtype = np.int64 if array.dtype.kind in "iu" else np.float64
            object.__setattr__(self, field, _readonly(array, dtype=dtype, field=field))
        for field, value in scalar_values.items():
            object.__setattr__(self, field, value)

    @property
    def served(self) -> np.ndarray:
        """The immutable execution-service mask carried by the input profile."""

        return self.profile.served

    @property
    def network_energy_j(self) -> float:
        """Declared canonical network energy for this interval."""

        return self.profile.network_energy_j

    def verify(self) -> float:
        """Recompute and verify the full share identity; return its residual."""

        expected = compute_cost_shares(self.profile)
        for field in (
            "beam_share_power_w",
            "satellite_share_power_w",
            "total_share_power_w",
            "beam_share_energy_j",
            "satellite_share_energy_j",
            "total_share_energy_j",
            "beam_occupancy",
            "satellite_occupancy",
            "active_satellite_ids",
            "beam_cost_power_w",
        ):
            if not np.array_equal(getattr(self, field), getattr(expected, field)):
                raise C3F0Error(f"{field} does not match the pure cost-share formula")
        for field in (
            "canonical_fixed_power_w",
            "canonical_network_power_w",
            "sum_beam_share_power_w",
            "sum_satellite_share_power_w",
            "sum_share_power_w",
            "conservation_residual_power_w",
            "sum_beam_share_energy_j",
            "sum_satellite_share_energy_j",
            "sum_share_energy_j",
            "conservation_residual_energy_j",
        ):
            if getattr(self, field) != getattr(expected, field):
                raise C3F0Error(f"{field} does not match the pure cost-share formula")
        return float(self.conservation_residual_energy_j)


def _build_cost_share_result(profile: PhysicalProfile) -> CostShareResult:
    """Build one result after all canonical and occupancy checks pass."""

    canonical = _canonical_power_components(profile)
    profile.verify_canonical_power()

    users = profile.users
    beams = profile.active_beams
    beam_keys = [
        (int(satellite), int(cell))
        for satellite, cell in zip(
            profile.active_beam_satellites.tolist(),
            profile.active_beam_cells.tolist(),
            strict=True,
        )
    ]
    beam_index = {key: index for index, key in enumerate(beam_keys)}
    satellite_ids = np.array(canonical.active_satellite_ids, dtype=np.int64, copy=True)
    satellite_index = {int(satellite): index for index, satellite in enumerate(satellite_ids.tolist())}

    beam_occupancy = np.zeros(beams, dtype=np.int64)
    satellite_occupancy = np.zeros(satellite_ids.size, dtype=np.int64)
    user_beam_index = np.full(users, -1, dtype=np.int64)
    user_satellite_index = np.full(users, -1, dtype=np.int64)
    for user in range(users):
        if not bool(profile.served[user]):
            continue
        key = _profile_key(profile, user)
        beam = beam_index[key]
        satellite = satellite_index[key[0]]
        user_beam_index[user] = beam
        user_satellite_index[user] = satellite
        beam_occupancy[beam] += 1
        satellite_occupancy[satellite] += 1

    if beams and np.any(beam_occupancy <= 0):
        raise C3F0Error("every active beam must have positive served occupancy")
    if satellite_ids.size and np.any(satellite_occupancy <= 0):
        raise C3F0Error("every active satellite must have positive served occupancy")

    beam_share = np.zeros(users, dtype=np.float64)
    satellite_share = np.zeros(users, dtype=np.float64)
    for user in range(users):
        beam = int(user_beam_index[user])
        satellite = int(user_satellite_index[user])
        if beam < 0 or satellite < 0:
            # Explicit unserved handling: no beam and no active-satellite
            # charge, with no numeric sentinel or post-hoc filter.
            continue
        beam_share[user] = float(canonical.beam_cost_power_w[beam]) / float(
            beam_occupancy[beam]
        )
        satellite_share[user] = BASEBAND_POWER_PER_SATELLITE_W / float(
            satellite_occupancy[satellite]
        )

    total_share = beam_share + satellite_share
    if not np.all(np.isfinite(total_share)):
        raise C3F0Error("cost-share power output is non-finite")

    beam_sum = _safe_sum(beam_share, field="served-user beam shares")
    satellite_sum = _safe_sum(satellite_share, field="active-satellite shares")
    total_sum = _safe_sum(total_share, field="all cost shares")
    expected_beam_sum = _safe_sum(canonical.beam_cost_power_w, field="canonical beam costs")
    expected_satellite_sum = _safe_product(
        BASEBAND_POWER_PER_SATELLITE_W,
        float(satellite_ids.size),
        field="canonical satellite baseband costs",
    )
    _assert_close(beam_sum, expected_beam_sum, field="beam share")
    _assert_close(satellite_sum, expected_satellite_sum, field="satellite share")
    _assert_close(total_sum, canonical.system_power_w, field="network share")

    interval = profile.interval_s
    beam_energy = _safe_array_product(beam_share, interval, field="beam share energy")
    satellite_energy = _safe_array_product(
        satellite_share,
        interval,
        field="satellite share energy",
    )
    total_energy = _safe_array_product(total_share, interval, field="total share energy")
    beam_energy_sum = _safe_sum(beam_energy, field="served-user beam share energy")
    satellite_energy_sum = _safe_sum(
        satellite_energy,
        field="active-satellite share energy",
    )
    total_energy_sum = _safe_sum(total_energy, field="all cost share energy")
    expected_network_energy = profile.network_energy_j
    _assert_close(
        total_energy_sum,
        expected_network_energy,
        field="network share energy",
    )

    return CostShareResult(
        profile=profile,
        beam_share_power_w=beam_share,
        satellite_share_power_w=satellite_share,
        total_share_power_w=total_share,
        beam_share_energy_j=beam_energy,
        satellite_share_energy_j=satellite_energy,
        total_share_energy_j=total_energy,
        beam_occupancy=beam_occupancy,
        satellite_occupancy=satellite_occupancy,
        active_satellite_ids=satellite_ids,
        beam_cost_power_w=canonical.beam_cost_power_w,
        canonical_fixed_power_w=canonical.fixed_power_w,
        canonical_network_power_w=canonical.system_power_w,
        sum_beam_share_power_w=beam_sum,
        sum_satellite_share_power_w=satellite_sum,
        sum_share_power_w=total_sum,
        conservation_residual_power_w=_safe_difference(
            total_sum,
            profile.system_power_w,
            field="declared network share",
        ),
        sum_beam_share_energy_j=beam_energy_sum,
        sum_satellite_share_energy_j=satellite_energy_sum,
        sum_share_energy_j=total_energy_sum,
        conservation_residual_energy_j=_safe_difference(
            total_energy_sum,
            expected_network_energy,
            field="declared network share energy",
        ),
    )


def compute_cost_shares(profile: PhysicalProfile) -> CostShareResult:
    """Compute deterministic equal-split beam and active-satellite shares.

    The declared profile power receipts are checked against the canonical
    ``fixed_power_w``/``system_power_w`` recomputation before any target is
    formed.  The returned per-user arrays preserve the service mask exactly;
    unserved users receive zeros and no other target entry is filtered.
    """

    if not isinstance(profile, PhysicalProfile):
        raise C3F0Error("compute_cost_shares requires a PhysicalProfile")
    return _build_cost_share_result(profile)


@dataclass(frozen=True)
class C3TargetPair:
    """Immutable raw signed ``D``/``F`` targets for one focal replacement."""

    focal_user: int
    lambda_bits_per_j: float
    interval_s: float
    nonfocal_delta_bits: float
    share_delta_energy_j: float
    network_delta_energy_j: float
    energy_correction_bits: float
    d_bits: float
    f_bits: float
    schema: str = F0_SCHEMA

    def __post_init__(self) -> None:
        focal = _exact_int(self.focal_user, field="focal_user")
        multiplier = _float_scalar(
            self.lambda_bits_per_j,
            field="lambda_bits_per_j",
            positive=True,
        )
        interval = _float_scalar(self.interval_s, field="interval_s", positive=True)
        scalar_fields = (
            "nonfocal_delta_bits",
            "share_delta_energy_j",
            "network_delta_energy_j",
            "energy_correction_bits",
            "d_bits",
            "f_bits",
        )
        values = {
            field: _float_scalar(getattr(self, field), field=field)
            for field in scalar_fields
        }
        if self.schema != F0_SCHEMA:
            raise C3F0Error("C3 target-pair schema is stale")
        expected_f = _safe_product(
            -multiplier,
            values["energy_correction_bits"],
            field="F target",
        )
        expected_d = _safe_sum(
            np.asarray([values["nonfocal_delta_bits"], expected_f]),
            field="D target",
        )
        if values["f_bits"] != expected_f or values["d_bits"] != expected_d:
            raise C3F0Error("D/F target pair does not match the frozen formulas")
        object.__setattr__(self, "focal_user", focal)
        object.__setattr__(self, "lambda_bits_per_j", multiplier)
        object.__setattr__(self, "interval_s", interval)
        for field, value in values.items():
            object.__setattr__(self, field, value)


def _validate_target_inputs(
    reference: PhysicalProfile,
    candidate: PhysicalProfile,
    focal_user: object,
    lambda_bits_per_j: object,
) -> tuple[CostShareResult, CostShareResult, int, float]:
    """Validate two profiles and the frozen scalar target inputs."""

    if not isinstance(reference, PhysicalProfile) or not isinstance(candidate, PhysicalProfile):
        raise C3F0Error("target functions require two PhysicalProfile inputs")
    if reference.users != candidate.users:
        raise C3F0Error("reference and candidate profiles must have the same user count")
    if reference.interval_s != candidate.interval_s:
        raise C3F0Error("reference and candidate profiles must use one identical interval")
    focal = _exact_int(focal_user, field="focal_user")
    if not 0 <= focal < reference.users:
        raise C3F0Error("focal_user is outside the profile user vector")
    multiplier = _float_scalar(
        lambda_bits_per_j,
        field="lambda_bits_per_j",
        positive=True,
    )
    return (
        compute_cost_shares(reference),
        compute_cost_shares(candidate),
        focal,
        multiplier,
    )


def compute_c3_targets(
    reference: PhysicalProfile,
    candidate: PhysicalProfile,
    *,
    focal_user: object,
    lambda_bits_per_j: object,
) -> C3TargetPair:
    """Return the exact frozen reference-centred CSE ``D`` and EC ``F`` targets.

    ``reference`` is ``b`` and ``candidate`` is ``c`` in the contingency
    ladder.  The candidate may serve or unserve the focal user; that status is
    represented by the profile and is not treated as a compatibility gate.
    """

    reference_share, candidate_share, focal, multiplier = _validate_target_inputs(
        reference,
        candidate,
        focal_user,
        lambda_bits_per_j,
    )
    interval = reference.interval_s
    nonfocal_rate_delta = _safe_sum(
        np.asarray(
            [
                float(candidate.link_rate_bps[user])
                - float(reference.link_rate_bps[user])
                for user in range(reference.users)
                if user != focal
            ],
            dtype=np.float64,
        ),
        field="nonfocal rate delta",
    )
    nonfocal_delta_bits = _safe_product(
        interval,
        nonfocal_rate_delta,
        field="nonfocal interval bits",
    )
    share_delta_energy = _safe_difference(
        float(candidate_share.total_share_energy_j[focal]),
        float(reference_share.total_share_energy_j[focal]),
        field="focal cost-share energy delta",
    )
    network_delta_energy = _safe_difference(
        candidate.network_energy_j,
        reference.network_energy_j,
        field="network energy delta",
    )
    energy_correction = _safe_difference(
        share_delta_energy,
        network_delta_energy,
        field="energy-share correction",
    )
    f_bits = _safe_product(
        -multiplier,
        energy_correction,
        field="F target",
    )
    d_bits = _safe_sum(
        np.asarray([nonfocal_delta_bits, f_bits], dtype=np.float64),
        field="D target",
    )
    return C3TargetPair(
        focal_user=focal,
        lambda_bits_per_j=multiplier,
        interval_s=interval,
        nonfocal_delta_bits=nonfocal_delta_bits,
        share_delta_energy_j=share_delta_energy,
        network_delta_energy_j=network_delta_energy,
        energy_correction_bits=energy_correction,
        d_bits=d_bits,
        f_bits=f_bits,
    )


def compute_d_target(
    reference: PhysicalProfile,
    candidate: PhysicalProfile,
    *,
    focal_user: object,
    lambda_bits_per_j: object,
) -> float:
    """Return the raw signed frozen CSE ``D`` target in bits."""

    return compute_c3_targets(
        reference,
        candidate,
        focal_user=focal_user,
        lambda_bits_per_j=lambda_bits_per_j,
    ).d_bits


def compute_f_target(
    reference: PhysicalProfile,
    candidate: PhysicalProfile,
    *,
    focal_user: object,
    lambda_bits_per_j: object,
) -> float:
    """Return the raw signed frozen energy-share-only EC ``F`` target in bits."""

    return compute_c3_targets(
        reference,
        candidate,
        focal_user=focal_user,
        lambda_bits_per_j=lambda_bits_per_j,
    ).f_bits


# Formula-name aliases are deliberately thin and do not introduce variants.
compute_cse_target = compute_d_target
compute_ec_target = compute_f_target
compute_D_target = compute_d_target
compute_F_target = compute_f_target


__all__ = [
    "BASEBAND_POWER_PER_SATELLITE_W",
    "C3ContingencyF0Error",
    "C3F0Error",
    "C3TargetPair",
    "CIRCUIT_POWER_PER_BEAM_W",
    "CostShareF0Error",
    "CostShareResult",
    "DECISION_STEP_S",
    "F0_SCHEMA",
    "INTERVAL_CONVENTION",
    "PhysicalProfile",
    "compute_D_target",
    "compute_F_target",
    "compute_cost_shares",
    "compute_c3_targets",
    "compute_cse_target",
    "compute_d_target",
    "compute_ec_target",
    "compute_f_target",
]
