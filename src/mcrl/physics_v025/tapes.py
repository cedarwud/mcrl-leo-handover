"""Fresh TRAIN world and immutable exogenous-tape construction for V0.25.

The builder consumes only primitive snapshots from an injected provider.  In
particular it never copies, pickles, or retains an environment (or a Skyfield
``Satrec``).  The provider's physical inventory is read and frozen before the
first action is formed; every arm and every matrix cell subsequently shares
the same detached tape.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Callable, Iterable, Mapping, Protocol, Sequence

import numpy as np

from mcrl.errors import MCRLContractError

from .architectures import BeamIdentity, Geometry, Link
from .channel import interference_receive_gain_linear, keyed_fading_gain
from .constants_v025 import (
    D2_MEASUREMENT_STEP_S,
    D2_SUBINTERVALS,
    DECISION_INTERVAL_S,
    IDENTITY_REFRESH_DECISIONS,
    MINIMUM_ELEVATION_DEG,
    RX_GAIN_MAX_DBI,
    SINR_MIN,
)
from .energy import HardwareInventory


PROBE_WORLD_DOMAINS = tuple(f"V025_PROBE/world/{index}" for index in range(1, 5))
CALIBRATION_WORLD_DOMAINS = tuple(f"V025_CAL/world/{index}" for index in range(1, 3))
REFERENCE_CARRIERS = ("nearest-eligible", "stay-if-possible", "random-masked")
CANDIDATE_REFRESH_N = 4


def seed_from_domain(domain: str) -> int:
    """Apply the repository's prospective SHA-256 domain seed rule."""

    if not isinstance(domain, str) or not domain or not domain.isascii():
        raise MCRLContractError("seed domain must be nonempty ASCII")
    return int.from_bytes(hashlib.sha256(domain.encode("ascii")).digest()[:8], "big") & (
        (1 << 63) - 1
    )


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise MCRLContractError("tape payload is not canonical finite ASCII JSON") from error


def digest_payload(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _step_array_digest(step: "PrimitiveStepArrays", *, boundary_zero_only: bool = False) -> str:
    """Canonical digest for an array snapshot without multi-gigabyte JSON."""

    digest = hashlib.sha256()
    for name in step.__dataclass_fields__:
        value = np.asarray(getattr(step, name))
        if boundary_zero_only and value.ndim > 0 and value.shape[0] == 48:
            value = value[:1]
        contiguous = np.ascontiguousarray(value)
        header = canonical_bytes(
            {"name": name, "dtype": contiguous.dtype.str, "shape": list(contiguous.shape)}
        )
        digest.update(len(header).to_bytes(8, "big"))
        digest.update(header)
        payload = contiguous.tobytes(order="C")
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def reference_policy_manifest() -> dict[str, object]:
    definitions = {
        "nearest-eligible": "minimum slant among visible D2-eligible physical candidates; physical-ID tie",
        "stay-if-possible": "retain incumbent physical identity while legal, else nearest-eligible",
        "random-masked": "uniform index from a SHA-256 world/step/user key over sorted legal identities",
    }
    return {
        "schema": "mcrl-v025-fixed-reference-carriers-v1",
        "order": list(REFERENCE_CARRIERS),
        "definitions": definitions,
        "sha256": digest_payload(definitions),
    }


def _f(value: float) -> str:
    if not math.isfinite(value):
        raise MCRLContractError("tape scalar must be finite")
    return float(value).hex()


@dataclass(frozen=True)
class UserLayout:
    user_id: int
    latitude_deg: float
    longitude_deg: float

    def payload(self) -> dict[str, object]:
        return {
            "user_id": self.user_id,
            "latitude_deg": _f(self.latitude_deg),
            "longitude_deg": _f(self.longitude_deg),
        }


@dataclass(frozen=True)
class PrimitiveCandidate:
    """Detached candidate/link state at one absolute boundary."""

    user_id: int
    identity: BeamIdentity
    color: int
    elevation_deg: float
    d2_entry_elevation_deg: float
    slant_km: float
    d2_distance_km: float
    visible: bool
    d2_eligible: bool
    nominal_gain: float
    realised_gain: float
    # Received watts per aggressor RF watt, indexed by physical aggressor NORAD.
    nominal_cross_gain_by_norad: tuple[tuple[int, float], ...]
    realised_cross_gain_by_norad: tuple[tuple[int, float], ...]
    remaining_visibility_s: float
    remaining_d2_s: float
    cell_reachable: bool = True
    # Stage-4 protocol: the physical aggressor key is (NORAD, cell), not
    # merely NORAD.  The legacy fields remain as compatibility views for
    # synthetic fixtures; real providers populate these identity-keyed rows.
    nominal_cross_gain_by_identity: tuple[tuple[BeamIdentity, float], ...] = ()
    realised_cross_gain_by_identity: tuple[tuple[BeamIdentity, float], ...] = ()
    visibility_right_censored: bool = False
    d2_right_censored: bool = False

    def __post_init__(self) -> None:
        if self.visible != (self.elevation_deg >= MINIMUM_ELEVATION_DEG):
            raise MCRLContractError("candidate visibility disagrees with live 10-degree floor")
        if len(self.identity) != 2:
            raise MCRLContractError("candidate identity must be (NORAD, cell_id)")
        if any(value < 0.0 or not math.isfinite(value) for value in (
            self.slant_km,
            self.d2_distance_km,
            self.nominal_gain,
            self.realised_gain,
            self.remaining_visibility_s,
            self.remaining_d2_s,
        )):
            raise MCRLContractError("candidate physical values must be finite and nonnegative")
        if self.nominal_gain <= 0.0 or self.realised_gain <= 0.0:
            raise MCRLContractError("direct channel gains must be positive")
        for name in ("nominal_cross_gain_by_norad", "realised_cross_gain_by_norad"):
            rows = getattr(self, name)
            if tuple(sorted(rows)) != rows or len({norad for norad, _ in rows}) != len(rows):
                raise MCRLContractError("cross-gain fields must use unique sorted NORAD order")
            if any(type(norad) is not int or not math.isfinite(gain) or gain < 0.0 for norad, gain in rows):
                raise MCRLContractError("cross-gain fields must be finite and nonnegative")
        for name in (
            "nominal_cross_gain_by_identity",
            "realised_cross_gain_by_identity",
        ):
            rows = getattr(self, name)
            if tuple(sorted(rows)) != rows or len({identity for identity, _ in rows}) != len(rows):
                raise MCRLContractError(
                    "identity cross-gain fields must use unique sorted physical identities"
                )
            if any(
                len(identity) != 2
                or any(type(value) is not int for value in identity)
                or not math.isfinite(gain)
                or gain < 0.0
                for identity, gain in rows
            ):
                raise MCRLContractError(
                    "identity cross-gain fields must be finite and nonnegative"
                )

    @property
    def legal(self) -> bool:
        return self.visible and self.d2_eligible and self.cell_reachable

    def payload(self) -> dict[str, object]:
        return {
            "user_id": self.user_id,
            "identity": list(self.identity),
            "color": self.color,
            "elevation_deg": _f(self.elevation_deg),
            "d2_entry_elevation_deg": _f(self.d2_entry_elevation_deg),
            "slant_km": _f(self.slant_km),
            "d2_distance_km": _f(self.d2_distance_km),
            "visible_10deg": self.visible,
            "d2_eligible": self.d2_eligible,
            "nominal_gain": _f(self.nominal_gain),
            "realised_gain": _f(self.realised_gain),
            "nominal_cross_gain_by_norad": [
                [norad, _f(gain)] for norad, gain in self.nominal_cross_gain_by_norad
            ],
            "realised_cross_gain_by_norad": [
                [norad, _f(gain)] for norad, gain in self.realised_cross_gain_by_norad
            ],
            "remaining_visibility_s": _f(self.remaining_visibility_s),
            "remaining_d2_s": _f(self.remaining_d2_s),
            "cell_reachable": self.cell_reachable,
            "nominal_cross_gain_by_identity": [
                [list(identity), _f(gain)]
                for identity, gain in self.nominal_cross_gain_by_identity
            ],
            "realised_cross_gain_by_identity": [
                [list(identity), _f(gain)]
                for identity, gain in self.realised_cross_gain_by_identity
            ],
            "visibility_right_censored": self.visibility_right_censored,
            "d2_right_censored": self.d2_right_censored,
        }


@dataclass(frozen=True)
class PrimitiveBoundary:
    absolute_time_s: float
    candidates: tuple[PrimitiveCandidate, ...]

    def __post_init__(self) -> None:
        keys = [(row.user_id, row.identity) for row in self.candidates]
        if len(keys) != len(set(keys)):
            raise MCRLContractError("boundary has duplicate user/physical candidates")

    def payload(self) -> dict[str, object]:
        return {
            "absolute_time_s": _f(self.absolute_time_s),
            "candidates": [row.payload() for row in self.candidates],
        }


@dataclass(frozen=True)
class PrimitiveStepArrays:
    """One 48-boundary step in compact, immutable NumPy form.

    Cross-gain storage is factorised by victim user, wanted-satellite slot,
    and physical aggressor.  This preserves the exact per-beam quantity
    without materialising millions of Python tuples.  Object boundaries are
    generated only by :meth:`boundary_view`, the audit/KAT compatibility
    seam; engine geometry is assembled directly from these arrays.
    """

    absolute_time_s: np.ndarray
    users: np.ndarray
    row_user_column: np.ndarray
    legacy_action_index: np.ndarray
    identities: np.ndarray
    colors: np.ndarray
    elevations_deg: np.ndarray
    d2_entry_elevations_deg: np.ndarray
    slants_km: np.ndarray
    d2_distances_km: np.ndarray
    visible: np.ndarray
    d2_eligible: np.ndarray
    cell_reachable: np.ndarray
    nominal_gain: np.ndarray
    realised_gain: np.ndarray
    remaining_visibility_s: np.ndarray
    remaining_d2_s: np.ndarray
    visibility_right_censored: np.ndarray
    d2_right_censored: np.ndarray
    aggressor_identities: np.ndarray
    aggressor_colors: np.ndarray
    aggressor_satellite_column: np.ndarray
    row_wanted_slot: np.ndarray
    cross_base_nominal: np.ndarray
    fading_by_satellite: np.ndarray
    receive_gain_by_wanted_slot: np.ndarray

    def __post_init__(self) -> None:
        arrays = {
            name: np.asarray(getattr(self, name))
            for name in self.__dataclass_fields__
        }
        times = arrays["absolute_time_s"]
        rows = arrays["identities"].shape[0]
        users = arrays["users"].shape[0]
        aggressors = arrays["aggressor_identities"].shape[0]
        satellites = arrays["fading_by_satellite"].shape[2]
        if times.shape != (D2_SUBINTERVALS + 1,):
            raise MCRLContractError("step arrays need exactly 48 boundary times")
        if arrays["identities"].shape != (rows, 2):
            raise MCRLContractError("step identities must have shape (R,2)")
        if arrays["aggressor_identities"].shape != (aggressors, 2):
            raise MCRLContractError("aggressor identities must have shape (A,2)")
        for name in (
            "row_user_column", "legacy_action_index", "colors", "row_wanted_slot"
        ):
            if arrays[name].shape != (rows,):
                raise MCRLContractError(f"{name} must have shape (R,)")
        for name in (
            "elevations_deg", "d2_entry_elevations_deg", "slants_km",
            "d2_distances_km", "visible", "d2_eligible", "cell_reachable",
            "nominal_gain", "realised_gain", "remaining_visibility_s",
            "remaining_d2_s", "visibility_right_censored",
            "d2_right_censored",
        ):
            if arrays[name].shape != (D2_SUBINTERVALS + 1, rows):
                raise MCRLContractError(f"{name} must have shape (48,R)")
        if arrays["aggressor_colors"].shape != (aggressors,):
            raise MCRLContractError("aggressor_colors must have shape (A,)")
        if arrays["aggressor_satellite_column"].shape != (aggressors,):
            raise MCRLContractError("aggressor satellite columns must have shape (A,)")
        if arrays["cross_base_nominal"].shape != (48, users, aggressors):
            raise MCRLContractError("cross_base_nominal must have shape (48,U,A)")
        if arrays["fading_by_satellite"].shape[:2] != (48, users):
            raise MCRLContractError("fading_by_satellite must have shape (48,U,S)")
        slots = arrays["receive_gain_by_wanted_slot"].shape[2]
        if arrays["receive_gain_by_wanted_slot"].shape != (48, users, slots, satellites):
            raise MCRLContractError(
                "receive_gain_by_wanted_slot must have shape (48,U,L,S)"
            )
        if np.any(arrays["row_user_column"] < 0) or np.any(arrays["row_user_column"] >= users):
            raise MCRLContractError("row user column is outside the user array")
        if np.any(arrays["aggressor_satellite_column"] < 0) or np.any(
            arrays["aggressor_satellite_column"] >= satellites
        ):
            raise MCRLContractError("aggressor satellite column is invalid")
        if not np.all(np.isfinite(times)):
            raise MCRLContractError("step boundary times must be finite")
        for name, value in arrays.items():
            frozen = np.array(value, copy=True)
            frozen.setflags(write=False)
            object.__setattr__(self, name, frozen)

    def __len__(self) -> int:
        return D2_SUBINTERVALS + 1

    def _row_index(self) -> dict[tuple[int, BeamIdentity], int]:
        return {
            (int(self.users[int(self.row_user_column[row])]),
             (int(identity[0]), int(identity[1]))): row
            for row, identity in enumerate(self.identities)
        }

    def _aggressor_index(self) -> dict[BeamIdentity, int]:
        return {
            (int(identity[0]), int(identity[1])): index
            for index, identity in enumerate(self.aggressor_identities)
        }

    def _cross(self, boundary_index: int, victim_row: int, aggressor: BeamIdentity) -> tuple[float, float]:
        aggressor_index = self._aggressor_index().get(aggressor)
        if aggressor_index is None:
            return 0.0, 0.0
        return self._cross_at_index(boundary_index, victim_row, aggressor_index)

    def _cross_at_index(
        self, boundary_index: int, victim_row: int, aggressor_index: int
    ) -> tuple[float, float]:
        aggressor = tuple(
            int(value) for value in self.aggressor_identities[aggressor_index]
        )
        if tuple(int(value) for value in self.identities[victim_row]) == aggressor:
            return 0.0, 0.0
        if int(self.colors[victim_row]) != int(self.aggressor_colors[aggressor_index]):
            return 0.0, 0.0
        user = int(self.row_user_column[victim_row])
        wanted_slot = int(self.row_wanted_slot[victim_row])
        satellite = int(self.aggressor_satellite_column[aggressor_index])
        nominal = float(
            self.cross_base_nominal[boundary_index, user, aggressor_index]
            * self.receive_gain_by_wanted_slot[boundary_index, user, wanted_slot, satellite]
        )
        realised = nominal * float(self.fading_by_satellite[boundary_index, user, satellite])
        return nominal, realised

    def boundary_view(self, boundary_index: int) -> PrimitiveBoundary:
        """Materialise the expensive object view only for audit/KAT callers."""

        if type(boundary_index) is not int or not 0 <= boundary_index < len(self):
            raise MCRLContractError("boundary index must be in 0..47")
        aggressors = [
            (int(identity[0]), int(identity[1]))
            for identity in self.aggressor_identities
        ]
        rows: list[PrimitiveCandidate] = []
        for row, raw_identity in enumerate(self.identities):
            identity = (int(raw_identity[0]), int(raw_identity[1]))
            nominal_identity = []
            realised_identity = []
            user = int(self.row_user_column[row])
            wanted_slot = int(self.row_wanted_slot[row])
            satellite_columns = self.aggressor_satellite_column
            nominal_all = (
                self.cross_base_nominal[boundary_index, user]
                * self.receive_gain_by_wanted_slot[
                    boundary_index, user, wanted_slot, satellite_columns
                ]
            )
            realised_all = nominal_all * self.fading_by_satellite[
                boundary_index, user, satellite_columns
            ]
            for aggressor_index, aggressor in enumerate(aggressors):
                if aggressor == identity or int(self.aggressor_colors[aggressor_index]) != int(self.colors[row]):
                    continue
                nominal_identity.append((aggressor, float(nominal_all[aggressor_index])))
                realised_identity.append((aggressor, float(realised_all[aggressor_index])))
            # Compatibility view: NORAD-only maps cannot represent multiple
            # beams, so aggregate all emitted physical terms by NORAD.
            nominal_norad: dict[int, float] = {}
            realised_norad: dict[int, float] = {}
            for (norad, _cell), gain in nominal_identity:
                nominal_norad[norad] = nominal_norad.get(norad, 0.0) + gain
            for (norad, _cell), gain in realised_identity:
                realised_norad[norad] = realised_norad.get(norad, 0.0) + gain
            rows.append(
                PrimitiveCandidate(
                    user_id=int(self.users[int(self.row_user_column[row])]),
                    identity=identity,
                    color=int(self.colors[row]),
                    elevation_deg=float(self.elevations_deg[boundary_index, row]),
                    d2_entry_elevation_deg=float(self.d2_entry_elevations_deg[boundary_index, row]),
                    slant_km=float(self.slants_km[boundary_index, row]),
                    d2_distance_km=float(self.d2_distances_km[boundary_index, row]),
                    visible=bool(self.visible[boundary_index, row]),
                    d2_eligible=bool(self.d2_eligible[boundary_index, row]),
                    nominal_gain=float(self.nominal_gain[boundary_index, row]),
                    realised_gain=float(self.realised_gain[boundary_index, row]),
                    nominal_cross_gain_by_norad=tuple(sorted(nominal_norad.items())),
                    realised_cross_gain_by_norad=tuple(sorted(realised_norad.items())),
                    remaining_visibility_s=float(self.remaining_visibility_s[boundary_index, row]),
                    remaining_d2_s=float(self.remaining_d2_s[boundary_index, row]),
                    cell_reachable=bool(self.cell_reachable[boundary_index, row]),
                    nominal_cross_gain_by_identity=tuple(nominal_identity),
                    realised_cross_gain_by_identity=tuple(realised_identity),
                    visibility_right_censored=bool(self.visibility_right_censored[boundary_index, row]),
                    d2_right_censored=bool(self.d2_right_censored[boundary_index, row]),
                )
            )
        return PrimitiveBoundary(float(self.absolute_time_s[boundary_index]), tuple(rows))

    def geometry_at(
        self,
        *,
        boundary_index: int,
        assignments: Mapping[int, BeamIdentity | None],
    ) -> Geometry:
        """Build selected geometry directly from arrays and physical keys."""

        row_of = self._row_index()
        selected: list[int] = []
        identities: list[BeamIdentity] = []
        for user in sorted(assignments):
            identity = assignments[user]
            if identity is None:
                continue
            try:
                row = row_of[(user, identity)]
            except KeyError:
                raise MCRLContractError("assignment is absent from the exogenous tape") from None
            if boundary_index == 0 and not (
                bool(self.visible[0, row])
                and bool(self.d2_eligible[0, row])
                and bool(self.cell_reachable[0, row])
            ):
                raise MCRLContractError("assignment is not legal at the decision instant")
            selected.append(row)
            identities.append(identity)
        nominal_cross = np.zeros((len(selected), len(selected)), dtype=np.float64)
        realised_cross = np.zeros_like(nominal_cross)
        aggressor_of = self._aggressor_index()
        for victim_index, victim_row in enumerate(selected):
            for aggressor_index, aggressor in enumerate(identities):
                if victim_index == aggressor_index:
                    continue
                physical_column = aggressor_of.get(aggressor)
                if physical_column is not None:
                    nominal_cross[victim_index, aggressor_index], realised_cross[
                        victim_index, aggressor_index
                    ] = self._cross_at_index(
                        boundary_index, victim_row, physical_column
                    )
        return Geometry(
            tuple(
                Link(
                    int(self.users[int(self.row_user_column[row])]),
                    identities[index],
                    int(self.colors[row]),
                    float(self.nominal_gain[boundary_index, row]),
                    float(self.realised_gain[boundary_index, row]),
                )
                for index, row in enumerate(selected)
            ),
            nominal_cross,
            realised_cross,
        )


@dataclass(frozen=True)
class StepTape:
    step_index: int
    refresh_phase: int
    boundaries: tuple[PrimitiveBoundary, ...] = ()
    arrays: PrimitiveStepArrays | None = None

    def __post_init__(self) -> None:
        if (self.arrays is None) == (len(self.boundaries) == 0):
            raise MCRLContractError(
                "step tape needs exactly one of object boundaries or compact arrays"
            )
        times = (
            np.asarray([boundary.absolute_time_s for boundary in self.boundaries])
            if self.arrays is None
            else self.arrays.absolute_time_s
        )
        if times.shape != (D2_SUBINTERVALS + 1,):
            raise MCRLContractError("each step tape needs t plus 47 boundary samples")
        start = float(times[0])
        for index, actual in enumerate(times):
            expected = start + index * D2_MEASUREMENT_STEP_S
            if not math.isclose(float(actual), expected, abs_tol=1e-12):
                raise MCRLContractError("D2 samples are not aligned to t + k*0.640, k=0..47")
        if not 0 <= self.refresh_phase < IDENTITY_REFRESH_DECISIONS:
            raise MCRLContractError("refresh phase is outside the frozen four-decision cadence")

    def boundary_at(self, boundary_index: int) -> PrimitiveBoundary:
        if self.arrays is not None:
            return self.arrays.boundary_view(boundary_index)
        return self.boundaries[boundary_index]

    @property
    def boundary_count(self) -> int:
        return D2_SUBINTERVALS + 1

    def payload(self) -> dict[str, object]:
        if self.arrays is not None:
            # Full sub-boundary arrays are intentionally not JSON-serialized.
            # The compact input digest binds their generator and the k=0 bytes.
            return {
                "step_index": self.step_index,
                "refresh_phase": self.refresh_phase,
                "array_sha256": _step_array_digest(self.arrays),
            }
        return {
            "step_index": self.step_index,
            "refresh_phase": self.refresh_phase,
            "boundaries": [row.payload() for row in self.boundaries],
        }


@dataclass(frozen=True)
class CarrierAction:
    carrier: str
    step_index: int
    assignments: tuple[tuple[int, BeamIdentity | None], ...]

    def payload(self) -> dict[str, object]:
        return {
            "carrier": self.carrier,
            "step_index": self.step_index,
            "assignments": [
                [user, None if identity is None else list(identity)]
                for user, identity in self.assignments
            ],
        }


@dataclass(frozen=True)
class ExogenousWorldTape:
    domain: str
    seed: int
    split: str
    tle_date: str
    training_seed: int
    user_layout: tuple[UserLayout, ...]
    inventory: HardwareInventory
    steps: tuple[StepTape, ...]
    carriers: tuple[CarrierAction, ...]
    generating_input_digest: str | None = None
    tle_files: tuple[tuple[str, str], ...] = ()
    step_user_layouts: tuple[tuple[UserLayout, ...], ...] = ()

    def __post_init__(self) -> None:
        if self.seed != seed_from_domain(self.domain) or self.split != "TRAIN":
            raise MCRLContractError("world identity does not match the fresh TRAIN domain rule")
        if not self.tle_date or type(self.training_seed) is not int or self.training_seed < 0:
            raise MCRLContractError("world needs a TLE-date x training-seed cluster identity")
        inventory = set(self.inventory.chains)
        for step in self.steps:
            if step.arrays is not None:
                legal = (
                    step.arrays.visible
                    & step.arrays.d2_eligible
                    & step.arrays.cell_reachable
                )
                identities = {
                    tuple(int(value) for value in step.arrays.identities[row])
                    for row in np.flatnonzero(np.any(legal, axis=0)).tolist()
                }
                if not identities <= inventory:
                    raise MCRLContractError("legal candidate expanded the hardware inventory")
            else:
                for boundary in step.boundaries:
                    if any(row.legal and row.identity not in inventory for row in boundary.candidates):
                        raise MCRLContractError("legal candidate expanded the hardware inventory")

    @property
    def inventory_digest(self) -> str:
        return digest_payload([list(identity) for identity in self.inventory.chains])

    @property
    def tape_digest(self) -> str:
        if self.generating_input_digest is not None:
            return self.generating_input_digest
        return digest_payload([step.payload() for step in self.steps])

    @property
    def layout_digest(self) -> str:
        return digest_payload([user.payload() for user in self.user_layout])

    @property
    def carrier_digest(self) -> str:
        return digest_payload([row.payload() for row in self.carriers])

    @property
    def digest(self) -> str:
        return digest_payload(self.manifest())

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "mcrl-v025-exogenous-world-tape-v1",
            "domain": self.domain,
            "seed": self.seed,
            "split": self.split,
            "cluster": {"tle_date": self.tle_date, "training_seed": self.training_seed},
            "steps": len(self.steps),
            "samples_per_interval": D2_SUBINTERVALS + 1,
            "subintervals_per_interval": D2_SUBINTERVALS,
            "inventory_sha256": self.inventory_digest,
            "layout_sha256": self.layout_digest,
            "tape_sha256": self.tape_digest,
            "carriers_sha256": self.carrier_digest,
            "reference_policies": reference_policy_manifest(),
            "candidate_refresh_period_n": CANDIDATE_REFRESH_N,
            "visibility_elevation_deg": _f(MINIMUM_ELEVATION_DEG),
            "d2_entry_elevation_deg_by_candidate": True,
            "cross_gain_key": "(NORAD,cell_id)",
            "boundary_storage": "numpy-float64",
            "tle_files": [[name, digest] for name, digest in self.tle_files],
            "step_user_layout_sha256": (
                None
                if not self.step_user_layouts
                else digest_payload(
                    [
                        [row.payload() for row in layout]
                        for layout in self.step_user_layouts
                    ]
                )
            ),
        }

    def geometry_for(
        self,
        *,
        step_index: int,
        assignments: Mapping[int, BeamIdentity | None],
    ) -> tuple[tuple[float, Geometry], ...]:
        """Materialize one selected configuration without mutating the tape."""

        step = self.steps[step_index]
        if step.arrays is not None:
            return tuple(
                (
                    float(step.arrays.absolute_time_s[boundary_index]),
                    step.arrays.geometry_at(
                        boundary_index=boundary_index,
                        assignments=assignments,
                    ),
                )
                for boundary_index in range(step.boundary_count)
            )
        result: list[tuple[float, Geometry]] = []
        for boundary_index, boundary in enumerate(step.boundaries):
            by_key = {(row.user_id, row.identity): row for row in boundary.candidates}
            chosen = []
            for user in sorted(assignments):
                identity = assignments[user]
                if identity is None:
                    continue
                try:
                    row = by_key[(user, identity)]
                except KeyError:
                    raise MCRLContractError("assignment is absent from the exogenous tape") from None
                if boundary_index == 0 and not row.legal:
                    raise MCRLContractError("assignment is not visible and D2-eligible")
                chosen.append(row)
            nominal_cross = np.zeros((len(chosen), len(chosen)), dtype=np.float64)
            realised_cross = np.zeros_like(nominal_cross)
            for victim_index, victim in enumerate(chosen):
                nominal_map = (
                    dict(victim.nominal_cross_gain_by_identity)
                    if victim.nominal_cross_gain_by_identity
                    else dict(victim.nominal_cross_gain_by_norad)
                )
                realised_map = (
                    dict(victim.realised_cross_gain_by_identity)
                    if victim.realised_cross_gain_by_identity
                    else dict(victim.realised_cross_gain_by_norad)
                )
                for aggressor_index, aggressor in enumerate(chosen):
                    if victim_index == aggressor_index:
                        continue
                    key: object = (
                        aggressor.identity
                        if victim.nominal_cross_gain_by_identity
                        else aggressor.identity[0]
                    )
                    nominal_cross[victim_index, aggressor_index] = nominal_map.get(key, 0.0)
                    realised_cross[victim_index, aggressor_index] = realised_map.get(key, 0.0)
            geometry = Geometry(
                tuple(
                    Link(
                        row.user_id,
                        row.identity,
                        row.color,
                        row.nominal_gain,
                        row.realised_gain,
                    )
                    for row in chosen
                ),
                nominal_cross,
                realised_cross,
            )
            result.append((boundary.absolute_time_s, geometry))
        return tuple(result)


class PrimitiveWorldProvider(Protocol):
    """Server injection seam. Returned values must contain primitives only."""

    def inventory(self, *, world_seed: int) -> Iterable[BeamIdentity]: ...

    def cluster_identity(self, *, world_seed: int) -> tuple[str, int]: ...

    def user_layout(self, *, world_seed: int) -> Iterable[UserLayout]: ...

    def boundary(
        self, *, world_seed: int, step_index: int, boundary_index: int, absolute_time_s: float
    ) -> PrimitiveBoundary: ...


def _legal_by_user(boundary: PrimitiveBoundary) -> dict[int, tuple[PrimitiveCandidate, ...]]:
    result: dict[int, list[PrimitiveCandidate]] = {}
    for row in boundary.candidates:
        if row.legal:
            result.setdefault(row.user_id, []).append(row)
    return {user: tuple(sorted(rows, key=lambda row: (row.slant_km, row.identity))) for user, rows in result.items()}


def _legal_arrays_by_user(step: StepTape) -> dict[int, tuple[tuple[float, BeamIdentity], ...]]:
    assert step.arrays is not None
    arrays = step.arrays
    result: dict[int, list[tuple[float, BeamIdentity]]] = {}
    legal = arrays.visible[0] & arrays.d2_eligible[0] & arrays.cell_reachable[0]
    for row in np.flatnonzero(legal).tolist():
        user = int(arrays.users[int(arrays.row_user_column[row])])
        identity = tuple(int(value) for value in arrays.identities[row])
        result.setdefault(user, []).append((float(arrays.slants_km[0, row]), identity))
    return {
        user: tuple(sorted(rows, key=lambda item: (item[0], item[1])))
        for user, rows in result.items()
    }


def fixed_carrier_actions(
    *, domain: str, steps: Sequence[StepTape], users: Sequence[int]
) -> tuple[CarrierAction, ...]:
    """Build the three prospectively fixed reference carriers."""

    state: dict[str, dict[int, BeamIdentity | None]] = {
        carrier: {user: None for user in users} for carrier in REFERENCE_CARRIERS
    }
    rows: list[CarrierAction] = []
    world_seed = seed_from_domain(domain)
    for step in steps:
        object_legal = None if step.arrays is not None else _legal_by_user(step.boundaries[0])
        array_legal = _legal_arrays_by_user(step) if step.arrays is not None else None
        for carrier in REFERENCE_CARRIERS:
            assignments: list[tuple[int, BeamIdentity | None]] = []
            for user in sorted(users):
                if array_legal is not None:
                    options = tuple(
                        _CarrierOption(identity=identity)
                        for _slant, identity in array_legal.get(user, ())
                    )
                else:
                    assert object_legal is not None
                    options = object_legal.get(user, ())
                selected: BeamIdentity | None = None
                if options:
                    if carrier == "stay-if-possible":
                        incumbent = state[carrier][user]
                        selected = next(
                            (row.identity for row in options if row.identity == incumbent),
                            options[0].identity,
                        )
                    elif carrier == "random-masked":
                        key = f"{world_seed}|{step.step_index}|{user}|random-masked".encode("ascii")
                        index = int.from_bytes(hashlib.sha256(key).digest()[:8], "big") % len(options)
                        selected = options[index].identity
                    else:
                        selected = options[0].identity
                state[carrier][user] = selected
                assignments.append((user, selected))
            rows.append(CarrierAction(carrier, step.step_index, tuple(assignments)))
    return tuple(rows)


@dataclass(frozen=True)
class _CarrierOption:
    identity: BeamIdentity


def build_world_tape(
    *,
    domain: str,
    provider: PrimitiveWorldProvider,
    steps: int,
    start_time_s: float,
) -> ExogenousWorldTape:
    """Detach a provider into one immutable common-random-number TRAIN tape."""

    if domain not in PROBE_WORLD_DOMAINS + CALIBRATION_WORLD_DOMAINS:
        raise MCRLContractError("world domain is outside the declared V025 TRAIN inventories")
    if type(steps) is not int or steps < 1 or not math.isfinite(start_time_s):
        raise MCRLContractError("steps and start time are invalid")
    seed = seed_from_domain(domain)
    # This call is deliberately first: hardware exists before candidates/actions.
    inventory = HardwareInventory.fixed(provider.inventory(world_seed=seed))
    tle_date, training_seed = provider.cluster_identity(world_seed=seed)
    layout = tuple(sorted(provider.user_layout(world_seed=seed), key=lambda row: row.user_id))
    if not layout or len({row.user_id for row in layout}) != len(layout):
        raise MCRLContractError("user layout must be nonempty with unique identities")
    step_rows = []
    array_builder = getattr(provider, "step_arrays", None)
    for step_index in range(steps):
        step_start = start_time_s + step_index * DECISION_INTERVAL_S
        if callable(array_builder):
            arrays = array_builder(
                world_seed=seed,
                step_index=step_index,
                start_time_s=start_time_s,
            )
            step_rows.append(
                StepTape(
                    step_index,
                    step_index % IDENTITY_REFRESH_DECISIONS,
                    arrays=arrays,
                )
            )
        else:
            boundaries = tuple(
                provider.boundary(
                    world_seed=seed,
                    step_index=step_index,
                    boundary_index=boundary_index,
                    absolute_time_s=step_start + boundary_index * D2_MEASUREMENT_STEP_S,
                )
                for boundary_index in range(D2_SUBINTERVALS + 1)
            )
            step_rows.append(
                StepTape(step_index, step_index % IDENTITY_REFRESH_DECISIONS, boundaries)
            )
    users = tuple(row.user_id for row in layout)
    carriers = fixed_carrier_actions(domain=domain, steps=step_rows, users=users)
    manifest_digest_builder = getattr(provider, "manifest_input_digest", None)
    generating_input_digest = (
        manifest_digest_builder(world_seed=seed)
        if callable(manifest_digest_builder)
        else None
    )
    tle_binding = getattr(provider, "tle_binding", None)
    tle_files = tuple(tle_binding(world_seed=seed)) if callable(tle_binding) else ()
    layout_at_step = getattr(provider, "user_layout_at_step", None)
    step_user_layouts = (
        tuple(layout_at_step(world_seed=seed, step_index=index) for index in range(steps))
        if callable(layout_at_step)
        else ()
    )
    return ExogenousWorldTape(
        domain,
        seed,
        "TRAIN",
        tle_date,
        training_seed,
        layout,
        inventory,
        tuple(step_rows),
        carriers,
        generating_input_digest,
        tle_files,
        step_user_layouts,
    )


class TinySyntheticProvider:
    """Small deterministic provider used only by KATs, dry-run, and rehearsal."""

    def __init__(self, *, users: int = 2) -> None:
        if users not in {2, 3}:
            raise MCRLContractError("tiny provider supports two or three users")
        self.users = users
        self._inventory = tuple((80_001 + sat, chain) for sat in range(3) for chain in range(2))

    def inventory(self, *, world_seed: int) -> Iterable[BeamIdentity]:
        del world_seed
        return self._inventory

    def cluster_identity(self, *, world_seed: int) -> tuple[str, int]:
        return ("synthetic-tle", world_seed)

    def user_layout(self, *, world_seed: int) -> Iterable[UserLayout]:
        rng = np.random.default_rng(world_seed)
        return tuple(
            UserLayout(user, 35.0 + float(rng.uniform(-0.1, 0.1)), -120.0 + 0.2 * user)
            for user in range(self.users)
        )

    def boundary(
        self, *, world_seed: int, step_index: int, boundary_index: int, absolute_time_s: float
    ) -> PrimitiveBoundary:
        candidates: list[PrimitiveCandidate] = []
        time_ns = int(round(absolute_time_s * 1e9))
        rx_peak = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
        for user in range(self.users):
            for option in range(3):
                norad = 80_001 + option
                identity = (norad, user % 2)
                phase = 0.09 * boundary_index + 0.31 * step_index + 0.7 * user + option
                elevation = 20.0 + 11.0 * option + 3.0 * math.sin(phase)
                slant = 1_000.0 - 85.0 * option + 8.0 * user + 0.35 * boundary_index
                # Chosen to place synthetic links around useful ACM/rate-target regimes.
                nominal = (4.4e-13 + 0.55e-13 * option) * (1.0 + 0.025 * math.sin(phase))
                fading = keyed_fading_gain(
                    world=world_seed,
                    user=user,
                    norad=norad,
                    absolute_time_ns=time_ns,
                    elevation_deg=elevation,
                )
                realised = nominal * fading
                nominal_cross = []
                realised_cross = []
                for aggressor_option in range(3):
                    aggressor_norad = 80_001 + aggressor_option
                    separation = 1.0 if aggressor_norad == norad else 2.043298703 + 3.0 * abs(aggressor_option - option)
                    rx_ratio = float(
                        interference_receive_gain_linear(
                            separation,
                            same_satellite=aggressor_norad == norad,
                        )
                    ) / rx_peak
                    cross = (1.2e-13 + 0.1e-13 * user) * rx_ratio
                    nominal_cross.append((aggressor_norad, cross))
                    cross_fading = keyed_fading_gain(
                        world=world_seed,
                        user=user,
                        norad=aggressor_norad,
                        absolute_time_ns=time_ns,
                        elevation_deg=elevation,
                    )
                    realised_cross.append((aggressor_norad, cross * cross_fading))
                d2_entry = (19.7, 23.4, 27.7)[option]
                candidates.append(
                    PrimitiveCandidate(
                        user,
                        identity,
                        (option + user) % 3,
                        elevation,
                        d2_entry,
                        slant,
                        950.0 + 20.0 * option,
                        elevation >= MINIMUM_ELEVATION_DEG,
                        elevation >= d2_entry,
                        nominal,
                        realised,
                        tuple(nominal_cross),
                        tuple(realised_cross),
                        max(0.0, (elevation - MINIMUM_ELEVATION_DEG) * 12.0),
                        max(0.0, (elevation - d2_entry) * 10.0),
                    )
                )
        return PrimitiveBoundary(absolute_time_s, tuple(candidates))


def corrected_boundary_rekey_rate(*, rekeys: int, eligible_boundaries: int) -> float:
    """Report rekeys conditional on boundaries that can re-key (never step 0)."""

    if type(rekeys) is not int or type(eligible_boundaries) is not int:
        raise MCRLContractError("rekey counts must be exact integers")
    if rekeys < 0 or eligible_boundaries <= 0 or rekeys > eligible_boundaries:
        raise MCRLContractError("invalid boundary-conditional rekey counts")
    return rekeys / eligible_boundaries


__all__ = [
    "CALIBRATION_WORLD_DOMAINS",
    "CarrierAction",
    "CANDIDATE_REFRESH_N",
    "ExogenousWorldTape",
    "PrimitiveBoundary",
    "PrimitiveCandidate",
    "PrimitiveStepArrays",
    "PrimitiveWorldProvider",
    "PROBE_WORLD_DOMAINS",
    "REFERENCE_CARRIERS",
    "StepTape",
    "TinySyntheticProvider",
    "UserLayout",
    "build_world_tape",
    "canonical_bytes",
    "corrected_boundary_rekey_rate",
    "digest_payload",
    "fixed_carrier_actions",
    "reference_policy_manifest",
    "seed_from_domain",
]
