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

    def __post_init__(self) -> None:
        if self.visible != (self.elevation_deg >= MINIMUM_ELEVATION_DEG):
            raise MCRLContractError("candidate visibility disagrees with live 10-degree floor")
        if len(self.identity) != 2:
            raise MCRLContractError("candidate identity must be (NORAD, beam-chain)")
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

    @property
    def legal(self) -> bool:
        return self.visible and self.d2_eligible

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
class StepTape:
    step_index: int
    refresh_phase: int
    boundaries: tuple[PrimitiveBoundary, ...]

    def __post_init__(self) -> None:
        if len(self.boundaries) != D2_SUBINTERVALS + 1:
            raise MCRLContractError("each step tape needs t plus 47 boundary samples")
        start = self.boundaries[0].absolute_time_s
        for index, boundary in enumerate(self.boundaries):
            expected = start + index * D2_MEASUREMENT_STEP_S
            if not math.isclose(boundary.absolute_time_s, expected, abs_tol=1e-12):
                raise MCRLContractError("D2 samples are not aligned to t + k*0.640, k=0..47")
        if not 0 <= self.refresh_phase < IDENTITY_REFRESH_DECISIONS:
            raise MCRLContractError("refresh phase is outside the frozen four-decision cadence")

    def payload(self) -> dict[str, object]:
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

    def __post_init__(self) -> None:
        if self.seed != seed_from_domain(self.domain) or self.split != "TRAIN":
            raise MCRLContractError("world identity does not match the fresh TRAIN domain rule")
        if not self.tle_date or type(self.training_seed) is not int or self.training_seed < 0:
            raise MCRLContractError("world needs a TLE-date x training-seed cluster identity")
        inventory = set(self.inventory.chains)
        for step in self.steps:
            for boundary in step.boundaries:
                if any(row.identity not in inventory for row in boundary.candidates):
                    raise MCRLContractError("candidate expanded the pre-action hardware inventory")

    @property
    def inventory_digest(self) -> str:
        return digest_payload([list(identity) for identity in self.inventory.chains])

    @property
    def tape_digest(self) -> str:
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
        }

    def geometry_for(
        self,
        *,
        step_index: int,
        assignments: Mapping[int, BeamIdentity | None],
    ) -> tuple[tuple[float, Geometry], ...]:
        """Materialize one selected configuration without mutating the tape."""

        step = self.steps[step_index]
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
                nominal_map = dict(victim.nominal_cross_gain_by_norad)
                realised_map = dict(victim.realised_cross_gain_by_norad)
                for aggressor_index, aggressor in enumerate(chosen):
                    if victim_index == aggressor_index:
                        continue
                    nominal_cross[victim_index, aggressor_index] = nominal_map.get(
                        aggressor.identity[0], 0.0
                    )
                    realised_cross[victim_index, aggressor_index] = realised_map.get(
                        aggressor.identity[0], 0.0
                    )
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
        legal = _legal_by_user(step.boundaries[0])
        for carrier in REFERENCE_CARRIERS:
            assignments: list[tuple[int, BeamIdentity | None]] = []
            for user in sorted(users):
                options = legal.get(user, ())
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
    for step_index in range(steps):
        step_start = start_time_s + step_index * DECISION_INTERVAL_S
        boundaries = tuple(
            provider.boundary(
                world_seed=seed,
                step_index=step_index,
                boundary_index=boundary_index,
                absolute_time_s=step_start + boundary_index * D2_MEASUREMENT_STEP_S,
            )
            for boundary_index in range(D2_SUBINTERVALS + 1)
        )
        step_rows.append(StepTape(step_index, step_index % IDENTITY_REFRESH_DECISIONS, boundaries))
    users = tuple(row.user_id for row in layout)
    carriers = fixed_carrier_actions(domain=domain, steps=step_rows, users=users)
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
