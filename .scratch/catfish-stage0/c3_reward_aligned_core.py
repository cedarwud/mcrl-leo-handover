"""Pure semantic core for the reward-aligned C3 Stage-0 replacement.

This module intentionally has no environment, checkpoint, filesystem, or seed
manifest integration.  It makes the v2 load identity, nested support masks,
arm selection, paired endpoints, and terminal directional rule executable in
isolation before any operational runner or formal seed reveal exists.

It is not Catfish runtime code and does not authorize training or Main replay
routing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
import re
import statistics
from typing import Iterable, Mapping, Sequence

import numpy as np


PhysicalId = tuple[int, int]

POWER_TOLERANCE_W = 1e-10
DECISION_INTERVAL_S = 30.08
EXPECTED_SEED_COUNT = 5
MIN_JOINT_ANCHORS = 20
MIN_POSITIVE_SEEDS = 4
MAX_SERVICE_DECLINE = 0.005
CIRCUIT_POWER_PER_BEAM_W = 0.338
BASEBAND_POWER_PER_SATELLITE_W = 0.200

PASS_RESULT = "C3_STAGE0_PASS_TO_IMPLEMENTATION_RULING_ONLY"
DROP_ROLE = "C3_STAGE0_FAIL_DROP_ROLE"
CERTIFICATE_FAILURE = "C3_STAGE0_CERTIFICATE_FAILURE"

PRIMARY_EFFECTS = (
    "Delta_R3_ref_extended",
    "Delta_R3_cert_extended",
    "Delta_R3_ref_episode",
    "Delta_R3_cert_episode",
)
SUPPORTING_EFFECTS = (
    "Delta_R3_load_safe_extended",
    "Delta_R3_cert_load_extended",
    "Delta_R3_load_safe_episode",
    "Delta_R3_cert_load_episode",
)


def validate_physical_id(value: object, *, field: str = "physical ID") -> PhysicalId:
    """Return an exact physical ``(satellite, beam)`` identity or fail closed."""

    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError(f"{field} must be a two-item physical ID tuple")
    satellite, beam = value
    if type(satellite) is not int or type(beam) is not int:
        raise ValueError(f"{field} components must be exact integers")
    if satellite < 0 or beam < 0:
        raise ValueError(f"{field} components must be nonnegative")
    return satellite, beam


def validate_candidate_pair(
    source_id: object, candidate_id: object
) -> tuple[PhysicalId, PhysicalId]:
    """Validate the physical C3 move: distinct beams on one satellite."""

    source = validate_physical_id(source_id, field="source physical ID")
    candidate = validate_physical_id(candidate_id, field="candidate physical ID")
    if source == candidate:
        raise ValueError("source and candidate physical IDs must differ")
    if source[0] != candidate[0]:
        raise ValueError("C3 source and candidate must be on the same satellite")
    return source, candidate


def _validate_user_id(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a nonnegative exact integer")
    return value


def validate_nonfocal_action_map(
    actions: object,
    *,
    focal_user_id: int,
    expected_user_count: int,
) -> dict[int, PhysicalId | None]:
    """Validate a full user-to-physical-action map for every non-focal user."""

    focal = _validate_user_id(focal_user_id, field="focal user ID")
    count = _validate_user_id(expected_user_count, field="expected user count")
    if count < 1 or focal >= count:
        raise ValueError("focal user ID must be inside the expected user range")
    if not isinstance(actions, Mapping):
        raise ValueError("nonfocal actions must be a complete mapping")
    expected = set(range(count)) - {focal}
    if set(actions) != expected:
        raise ValueError("nonfocal action map must be complete and exclude the focal user")
    validated: dict[int, PhysicalId | None] = {}
    for raw_user, raw_action in actions.items():
        user = _validate_user_id(raw_user, field="nonfocal user ID")
        validated[user] = (
            None
            if raw_action is None
            else validate_physical_id(raw_action, field="nonfocal physical ID")
        )
    return validated


class EventClass(str, Enum):
    """Only event classes that the C3 receipt may record."""

    NONE = "none"
    PHI1 = "phi1"
    PHI2 = "phi2"
    REENTRY = "reentry"
    REVERSAL = "reversal"


def validate_event_class(value: object) -> EventClass:
    if type(value) is not EventClass:
        raise ValueError("event class must be an EventClass value")
    return value


def expected_certificate_event(branch: str, interval: int) -> EventClass:
    if branch not in {"reference", "candidate"}:
        raise ValueError("unknown certificate event branch")
    if type(interval) is not int or interval not in {0, 1, 2}:
        raise ValueError("certificate event interval must be 0, 1, or 2")
    if branch == "candidate" and interval == 0:
        return EventClass.PHI1
    return EventClass.NONE


_DOMAIN_NAMESPACE = re.compile(r"SMC-ER-C3-[A-Z0-9-]+-v2\Z")
_SHA256_HEX = re.compile(r"[0-9a-f]{64}\Z")


def derive_domain_seed(
    namespace: str,
    checkpoint_sha256: str,
    evaluation_seed: int,
    step_index: int,
    focal_user: int,
) -> int:
    """Apply the v2 canonical-JSON/SHA-256 seed derivation exactly."""

    if type(namespace) is not str or _DOMAIN_NAMESPACE.fullmatch(namespace) is None:
        raise ValueError("C3 RNG namespace must match SMC-ER-C3-<DOMAIN>-v2")
    if (
        type(checkpoint_sha256) is not str
        or _SHA256_HEX.fullmatch(checkpoint_sha256) is None
    ):
        raise ValueError("checkpoint authority must be a lowercase SHA-256 hex digest")
    seed = _validate_user_id(evaluation_seed, field="evaluation seed")
    step = _validate_user_id(step_index, field="step index")
    focal = _validate_user_id(focal_user, field="focal user ID")
    encoded = json.dumps(
        [namespace, checkpoint_sha256, seed, step, focal],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(encoded).digest()[:16], "big")


def make_domain_rng(
    namespace: str,
    checkpoint_sha256: str,
    evaluation_seed: int,
    step_index: int,
    focal_user: int,
) -> np.random.Generator:
    """Return a fresh PCG64 object; no environment RNG object is accepted."""

    seed = derive_domain_seed(
        namespace,
        checkpoint_sha256,
        evaluation_seed,
        step_index,
        focal_user,
    )
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed)))


class OptionPhase(str, Enum):
    FORCED = "forced"
    RELEASED = "released"
    TERMINATED = "terminated"


@dataclass(frozen=True)
class OptionState:
    destination_id: PhysicalId
    phase: OptionPhase
    next_interval: int
    termination_reason: str | None = None

    @classmethod
    def start(cls, destination_id: PhysicalId) -> "OptionState":
        destination = validate_physical_id(
            destination_id, field="option destination physical ID"
        )
        return cls(destination, OptionPhase.FORCED, 0)


@dataclass(frozen=True)
class OptionStep:
    interval: int
    focal_action: PhysicalId | None
    event: EventClass
    main_controls: bool
    termination_reason: str | None = None


def advance_option(
    state: OptionState,
    *,
    interval: int,
    hold_valid: bool,
    service_feasible: bool,
    episode_done: bool,
) -> tuple[OptionStep, OptionState]:
    """Advance the explicit h0 move, h1/h2 hold, h3 release state machine."""

    if type(state) is not OptionState:
        raise ValueError("option state is malformed")
    validate_physical_id(state.destination_id, field="option destination physical ID")
    if type(state.phase) is not OptionPhase:
        raise ValueError("option phase is malformed")
    _validate_user_id(state.next_interval, field="option next interval")
    if state.phase is OptionPhase.TERMINATED:
        if type(state.termination_reason) is not str or not state.termination_reason:
            raise ValueError("terminated option requires a reason")
    elif state.termination_reason is not None:
        raise ValueError("non-terminated option cannot carry a termination reason")
    h = _validate_user_id(interval, field="option interval")
    if h != state.next_interval:
        raise ValueError("option intervals must advance sequentially")
    valid = _strict_bool(hold_valid, field="hold validity")
    feasible = _strict_bool(service_feasible, field="service feasibility")
    done = _strict_bool(episode_done, field="episode-done flag")

    if state.phase is OptionPhase.RELEASED:
        return (
            OptionStep(h, None, EventClass.NONE, True),
            OptionState(state.destination_id, state.phase, h + 1),
        )
    if state.phase is OptionPhase.TERMINATED:
        return (
            OptionStep(h, None, EventClass.NONE, True, state.termination_reason),
            OptionState(
                state.destination_id,
                state.phase,
                h + 1,
                state.termination_reason,
            ),
        )
    if h >= 3:
        return (
            OptionStep(h, None, EventClass.NONE, True),
            OptionState(state.destination_id, OptionPhase.RELEASED, h + 1),
        )

    termination_reason = None
    if done:
        termination_reason = "episode_end"
    elif not valid:
        termination_reason = "invalid_hold"
    elif not feasible:
        termination_reason = "service_failure"
    if termination_reason is not None:
        return (
            OptionStep(
                h,
                None,
                EventClass.NONE,
                False,
                termination_reason,
            ),
            OptionState(
                state.destination_id,
                OptionPhase.TERMINATED,
                h + 1,
                termination_reason,
            ),
        )

    event = EventClass.PHI1 if h == 0 else EventClass.NONE
    return (
        OptionStep(h, state.destination_id, event, False),
        OptionState(state.destination_id, OptionPhase.FORCED, h + 1),
    )


def _positive_loads(loads: Mapping[PhysicalId, int]) -> dict[PhysicalId, int]:
    """Canonicalize an eligible-load map and reject invalid counts."""

    if not isinstance(loads, Mapping):
        raise ValueError("eligible loads must be a mapping")
    result: dict[PhysicalId, int] = {}
    for raw_key, raw_value in loads.items():
        key = validate_physical_id(raw_key, field="eligible-load physical ID")
        if type(raw_value) is not int or raw_value < 0:
            raise ValueError("eligible loads must be nonnegative integers")
        value = raw_value
        if value:
            result[key] = value
    return result


def _finite_number(value: object, *, field: str, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be a finite number")
    if nonnegative and result < 0.0:
        raise ValueError(f"{field} must be nonnegative")
    return result


@dataclass(frozen=True)
class PowerSnapshot:
    """Runtime power observables sufficient to recompute canonical ``P^N``."""

    supply_power_w_by_beam: Mapping[PhysicalId, float]
    radiating_beams_by_satellite: Mapping[int, int]
    reported_fixed_power_w: float
    reported_system_power_w: float
    pa_identity_residual_w: float
    circuit_power_per_beam_w: float = CIRCUIT_POWER_PER_BEAM_W
    baseband_power_per_satellite_w: float = BASEBAND_POWER_PER_SATELLITE_W


@dataclass(frozen=True)
class PowerRecomputation:
    fixed_power_w: float
    system_power_w: float


def recompute_system_power(snapshot: PowerSnapshot) -> PowerRecomputation:
    """Independently reconstruct the full per-beam canonical system power."""

    if type(snapshot) is not PowerSnapshot:
        raise ValueError("power snapshot is malformed")
    if not isinstance(snapshot.supply_power_w_by_beam, Mapping):
        raise ValueError("power snapshot supply map is malformed")
    supply: dict[PhysicalId, float] = {}
    for raw_beam, raw_power in snapshot.supply_power_w_by_beam.items():
        beam = validate_physical_id(raw_beam, field="power physical ID")
        supply_power = _finite_number(
            raw_power, field="per-beam supply power", nonnegative=True
        )
        if supply_power <= 0.0:
            raise ValueError("per-radiating-beam supply power must be strictly positive")
        supply[beam] = supply_power
    if not isinstance(snapshot.radiating_beams_by_satellite, Mapping):
        raise ValueError("power snapshot satellite-count map is malformed")
    counts: dict[int, int] = {}
    for raw_satellite, raw_count in snapshot.radiating_beams_by_satellite.items():
        satellite = _validate_user_id(raw_satellite, field="satellite ID")
        if type(raw_count) is not int or raw_count < 1:
            raise ValueError("radiating-beam counts must be positive exact integers")
        counts[satellite] = raw_count
    observed_counts: dict[int, int] = {}
    for satellite, _beam in supply:
        observed_counts[satellite] = observed_counts.get(satellite, 0) + 1
    if counts != observed_counts:
        raise ValueError("power snapshot beam keys and satellite counts disagree")
    _finite_number(
        snapshot.circuit_power_per_beam_w,
        field="circuit power per beam",
        nonnegative=True,
    )
    _finite_number(
        snapshot.baseband_power_per_satellite_w,
        field="baseband power per satellite",
        nonnegative=True,
    )
    fixed = (
        CIRCUIT_POWER_PER_BEAM_W * sum(counts.values())
        + BASEBAND_POWER_PER_SATELLITE_W * len(counts)
    )
    return PowerRecomputation(
        fixed_power_w=fixed,
        system_power_w=fixed + sum(supply.values()),
    )


def validate_power_snapshot(
    snapshot: object, *, tolerance_w: float = POWER_TOLERANCE_W
) -> tuple[str, ...]:
    """Return named fail-closed reasons; totals never replace recomputation."""

    try:
        tolerance = _finite_number(tolerance_w, field="power tolerance", nonnegative=True)
        if type(snapshot) is not PowerSnapshot:
            raise ValueError("power snapshot is malformed")
        recomputed = recompute_system_power(snapshot)
        reported_fixed = _finite_number(
            snapshot.reported_fixed_power_w,
            field="reported fixed power",
            nonnegative=True,
        )
        reported_system = _finite_number(
            snapshot.reported_system_power_w,
            field="reported system power",
            nonnegative=True,
        )
        residual = _finite_number(
            snapshot.pa_identity_residual_w, field="PA identity residual"
        )
    except (TypeError, ValueError, OverflowError) as exc:
        return (f"malformed_power_snapshot:{exc}",)

    reasons: list[str] = []
    if snapshot.circuit_power_per_beam_w != CIRCUIT_POWER_PER_BEAM_W:
        reasons.append("circuit_power_constant_mismatch")
    if snapshot.baseband_power_per_satellite_w != BASEBAND_POWER_PER_SATELLITE_W:
        reasons.append("baseband_power_constant_mismatch")
    if abs(reported_fixed - recomputed.fixed_power_w) > tolerance:
        reasons.append("reported_fixed_power_mismatch")
    if abs(reported_system - recomputed.system_power_w) > tolerance:
        reasons.append("reported_system_power_mismatch")
    if abs(residual) > tolerance:
        reasons.append("pa_identity_failed")
    return tuple(reasons)


def canonical_r3_total(loads: Mapping[PhysicalId, int]) -> int:
    """Return the unchanged system total ``sum_u r3,u = -sum_b U_b^2``."""

    return -sum(value * value for value in _positive_loads(loads).values())


def expected_one_user_r3_delta(source_load: int, destination_load: int) -> int:
    """Exact C3 one-user total-R3 change under the reference-load convention."""

    if type(source_load) is not int or type(destination_load) is not int:
        raise ValueError("C3 loads must be exact integers")
    source = source_load
    destination = destination_load
    if source < 1 or destination < 0:
        raise ValueError("source must include the focal user; loads cannot be negative")
    return 2 * (source - destination - 1)


def strict_load_improvement(source_load: int, destination_load: int) -> bool:
    """The exact integer ``U_source >= U_destination + 2`` condition."""

    return expected_one_user_r3_delta(source_load, destination_load) > 0


def expected_candidate_loads(
    reference_loads: Mapping[PhysicalId, int],
    *,
    source_id: PhysicalId,
    destination_id: PhysicalId,
) -> dict[PhysicalId, int]:
    """Apply only the focal source ``-1`` and destination ``+1`` changes."""

    source_physical_id, destination_physical_id = validate_candidate_pair(
        source_id, destination_id
    )
    result = _positive_loads(reference_loads)
    source = result.get(source_physical_id, 0)
    if source < 1:
        raise ValueError("reference source load must include the focal user")
    destination = result.get(destination_physical_id, 0)
    if destination < 1:
        raise ValueError("C3 destination must already be active")
    if source == 1:
        del result[source_physical_id]
    else:
        result[source_physical_id] = source - 1
    result[destination_physical_id] = destination + 1
    return result


@dataclass(frozen=True)
class ForecastInterval:
    """One deterministic reference/candidate certificate interval."""

    reference_loads: Mapping[PhysicalId, int]
    candidate_loads: Mapping[PhysicalId, int]
    reference_r3_total: int
    candidate_r3_total: int
    reference_power: PowerSnapshot
    candidate_power: PowerSnapshot
    reference_nonfocal_actions: Mapping[int, PhysicalId | None]
    candidate_nonfocal_actions: Mapping[int, PhysicalId | None]
    reference_event: EventClass
    candidate_event: EventClass
    reference_hold_valid: bool = True
    candidate_hold_valid: bool = True
    reference_service: bool = True
    candidate_service: bool = True
    reference_served_users: tuple[int, ...] = ()
    candidate_served_users: tuple[int, ...] = ()
    reference_active_beams: tuple[PhysicalId, ...] = ()
    candidate_active_beams: tuple[PhysicalId, ...] = ()
    reference_active_satellites: tuple[int, ...] = ()
    candidate_active_satellites: tuple[int, ...] = ()
    hidden_fallback: bool = False


@dataclass(frozen=True)
class GuardResult:
    """A named, machine-readable guard result for receipts and audits."""

    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class CandidateEvidence:
    """Nested support result for one physical C3 destination."""

    candidate_id: PhysicalId
    hard_safe: bool
    strict_load: bool
    persistent_power: bool
    joint: bool
    reasons: tuple[str, ...]
    load_gap_score: int
    power_relief_j: float
    intervals: tuple[ForecastInterval, ...]
    power_delta_w: tuple[float | None, ...] = ()
    guard_ledger: tuple[GuardResult, ...] = ()


def _strict_bool(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} must be an exact boolean")
    return value


def _physical_id_set(values: object, *, field: str) -> frozenset[PhysicalId]:
    if not isinstance(values, tuple):
        raise ValueError(f"{field} must be a tuple")
    result = tuple(validate_physical_id(value, field=field) for value in values)
    if len(result) != len(set(result)):
        raise ValueError(f"{field} contains duplicate physical IDs")
    return frozenset(result)


def _integer_set(values: object, *, field: str) -> frozenset[int]:
    if not isinstance(values, tuple):
        raise ValueError(f"{field} must be a tuple")
    result = tuple(_validate_user_id(value, field=field) for value in values)
    if len(result) != len(set(result)):
        raise ValueError(f"{field} contains duplicates")
    return frozenset(result)


def _hard_safe_reasons(
    row: ForecastInterval,
    interval: int,
    *,
    focal_user_id: int,
    expected_user_count: int,
) -> list[str]:
    reasons: list[str] = []
    try:
        reference_actions = validate_nonfocal_action_map(
            row.reference_nonfocal_actions,
            focal_user_id=focal_user_id,
            expected_user_count=expected_user_count,
        )
        candidate_actions = validate_nonfocal_action_map(
            row.candidate_nonfocal_actions,
            focal_user_id=focal_user_id,
            expected_user_count=expected_user_count,
        )
        if reference_actions != candidate_actions:
            reasons.append(f"h{interval}:nonfocal_action_mismatch")

        if not _strict_bool(row.reference_hold_valid, field="reference hold"):
            reasons.append(f"h{interval}:invalid_reference_focal_hold")
        if not _strict_bool(row.candidate_hold_valid, field="candidate hold"):
            reasons.append(f"h{interval}:invalid_candidate_focal_hold")
        reference_service = _strict_bool(
            row.reference_service, field="reference service"
        )
        candidate_service = _strict_bool(
            row.candidate_service, field="candidate service"
        )
        if not reference_service:
            reasons.append(f"h{interval}:reference_focal_service_failure")
        if not candidate_service:
            reasons.append(f"h{interval}:candidate_focal_service_failure")

        reference_served = _integer_set(
            row.reference_served_users, field="reference served-user set"
        )
        candidate_served = _integer_set(
            row.candidate_served_users, field="candidate served-user set"
        )
        if any(user >= expected_user_count for user in reference_served | candidate_served):
            raise ValueError("served-user set contains an out-of-range user ID")
        if reference_service and focal_user_id not in reference_served:
            reasons.append(f"h{interval}:reference_focal_missing_from_served_set")
        if candidate_service and focal_user_id not in candidate_served:
            reasons.append(f"h{interval}:candidate_focal_missing_from_served_set")
        if reference_served != candidate_served:
            reasons.append(f"h{interval}:served_set_mismatch")

        reference_beams = _physical_id_set(
            row.reference_active_beams, field="reference active-beam set"
        )
        candidate_beams = _physical_id_set(
            row.candidate_active_beams, field="candidate active-beam set"
        )
        if reference_beams != candidate_beams:
            reasons.append(f"h{interval}:active_beam_set_mismatch")
        reference_satellites = _integer_set(
            row.reference_active_satellites,
            field="reference active-satellite set",
        )
        candidate_satellites = _integer_set(
            row.candidate_active_satellites,
            field="candidate active-satellite set",
        )
        if reference_satellites != candidate_satellites:
            reasons.append(f"h{interval}:active_satellite_set_mismatch")

        if type(row.reference_power) is PowerSnapshot:
            if reference_beams != frozenset(row.reference_power.supply_power_w_by_beam):
                reasons.append(f"h{interval}:reference_power_beam_set_mismatch")
            if reference_satellites != frozenset(
                row.reference_power.radiating_beams_by_satellite
            ):
                reasons.append(f"h{interval}:reference_power_satellite_set_mismatch")
        if type(row.candidate_power) is PowerSnapshot:
            if candidate_beams != frozenset(row.candidate_power.supply_power_w_by_beam):
                reasons.append(f"h{interval}:candidate_power_beam_set_mismatch")
            if candidate_satellites != frozenset(
                row.candidate_power.radiating_beams_by_satellite
            ):
                reasons.append(f"h{interval}:candidate_power_satellite_set_mismatch")

        reference_event = validate_event_class(row.reference_event)
        candidate_event = validate_event_class(row.candidate_event)
        if reference_event is not expected_certificate_event("reference", interval):
            reasons.append(f"h{interval}:reference_event_mismatch")
        if candidate_event is not expected_certificate_event("candidate", interval):
            reasons.append(f"h{interval}:candidate_event_mismatch")
        if _strict_bool(row.hidden_fallback, field="hidden fallback"):
            reasons.append(f"h{interval}:hidden_fallback")
    except (TypeError, ValueError, OverflowError) as exc:
        reasons.append(f"h{interval}:malformed_hard_safe_input:{exc}")
    return reasons


def certify_candidate(
    *,
    source_id: PhysicalId,
    candidate_id: PhysicalId,
    intervals: Sequence[ForecastInterval],
    focal_user_id: int,
    expected_user_count: int = 100,
    power_tolerance_w: float = POWER_TOLERANCE_W,
    decision_interval_s: float = DECISION_INTERVAL_S,
) -> CandidateEvidence:
    """Evaluate hard-safe, load, power, and joint support without score fusion."""

    source, candidate_physical_id = validate_candidate_pair(source_id, candidate_id)
    focal = _validate_user_id(focal_user_id, field="focal user ID")
    user_count = _validate_user_id(expected_user_count, field="expected user count")
    if user_count < 1 or focal >= user_count:
        raise ValueError("focal user ID must be inside the expected user range")
    tolerance = _finite_number(
        power_tolerance_w, field="power tolerance", nonnegative=True
    )
    interval_seconds = _finite_number(
        decision_interval_s, field="decision interval", nonnegative=True
    )
    if interval_seconds <= 0.0:
        raise ValueError("decision interval must be positive")
    try:
        rows = tuple(intervals)
    except TypeError as exc:
        raise ValueError("certificate intervals must be a finite sequence") from exc
    if len(rows) != 3:
        raise ValueError("certificate requires exactly three intervals")

    hard_reasons: list[str] = []
    load_reasons: list[str] = []
    power_reasons: list[str] = []
    gaps: list[int] = []
    relief: list[float] = []
    power_deltas: list[float | None] = []

    for h, row in enumerate(rows):
        if type(row) is not ForecastInterval:
            hard_reasons.append(f"h{h}:malformed_interval")
            load_reasons.append(f"h{h}:malformed_interval")
            power_reasons.append(f"h{h}:malformed_interval")
            power_deltas.append(None)
            continue
        hard_reasons.extend(
            _hard_safe_reasons(
                row,
                h,
                focal_user_id=focal,
                expected_user_count=user_count,
            )
        )

        try:
            reference = _positive_loads(row.reference_loads)
            candidate = _positive_loads(row.candidate_loads)
            reference_active_beams = _physical_id_set(
                row.reference_active_beams, field="reference active-beam set"
            )
            candidate_active_beams = _physical_id_set(
                row.candidate_active_beams, field="candidate active-beam set"
            )
            if frozenset(reference) != reference_active_beams:
                load_reasons.append(f"h{h}:reference_load_active_beam_mismatch")
            if frozenset(candidate) != candidate_active_beams:
                load_reasons.append(f"h{h}:candidate_load_active_beam_mismatch")
            reference_served = _integer_set(
                row.reference_served_users, field="reference served-user set"
            )
            candidate_served = _integer_set(
                row.candidate_served_users, field="candidate served-user set"
            )
            if sum(reference.values()) != len(reference_served):
                load_reasons.append(f"h{h}:reference_load_served_count_mismatch")
            if sum(candidate.values()) != len(candidate_served):
                load_reasons.append(f"h{h}:candidate_load_served_count_mismatch")
            reference_actions = validate_nonfocal_action_map(
                row.reference_nonfocal_actions,
                focal_user_id=focal,
                expected_user_count=user_count,
            )
            candidate_actions = validate_nonfocal_action_map(
                row.candidate_nonfocal_actions,
                focal_user_id=focal,
                expected_user_count=user_count,
            )

            def loads_from_actions(
                served_users: frozenset[int],
                nonfocal_actions: Mapping[int, PhysicalId | None],
                focal_beam: PhysicalId,
            ) -> dict[PhysicalId, int]:
                reconstructed: dict[PhysicalId, int] = {}
                for user in served_users:
                    beam = (
                        focal_beam
                        if user == focal
                        else nonfocal_actions.get(user)
                    )
                    if beam is None:
                        continue
                    reconstructed[beam] = reconstructed.get(beam, 0) + 1
                return reconstructed

            if reference != loads_from_actions(
                reference_served, reference_actions, source
            ):
                load_reasons.append(f"h{h}:reference_load_action_inclusion_mismatch")
            if candidate != loads_from_actions(
                candidate_served, candidate_actions, candidate_physical_id
            ):
                load_reasons.append(f"h{h}:candidate_load_action_inclusion_mismatch")
            if type(row.reference_r3_total) is not int:
                raise ValueError("reference R3 total must be an exact integer")
            if type(row.candidate_r3_total) is not int:
                raise ValueError("candidate R3 total must be an exact integer")
            source_load = reference.get(source, 0)
            destination_load = reference.get(candidate_physical_id, 0)
            if source_load < 1:
                load_reasons.append(f"h{h}:reference_source_missing_focal")
            elif destination_load < 1:
                load_reasons.append(f"h{h}:destination_not_already_active")
            else:
                gap = source_load - destination_load
                gaps.append(gap)
                if not strict_load_improvement(source_load, destination_load):
                    load_reasons.append(f"h{h}:strict_load_gap_failed")
                expected = expected_candidate_loads(
                    reference,
                    source_id=source,
                    destination_id=candidate_physical_id,
                )
                if candidate != expected:
                    load_reasons.append(f"h{h}:candidate_load_map_mismatch")
                if row.reference_r3_total != canonical_r3_total(reference):
                    load_reasons.append(f"h{h}:reference_r3_identity_failed")
                if row.candidate_r3_total != canonical_r3_total(candidate):
                    load_reasons.append(f"h{h}:candidate_r3_identity_failed")
                expected_delta = expected_one_user_r3_delta(
                    source_load, destination_load
                )
                if row.candidate_r3_total - row.reference_r3_total != expected_delta:
                    load_reasons.append(f"h{h}:one_user_r3_delta_failed")
        except (TypeError, ValueError, OverflowError) as exc:
            load_reasons.append(f"h{h}:malformed_load_or_r3:{exc}")

        reference_power_reasons = validate_power_snapshot(
            row.reference_power, tolerance_w=tolerance
        )
        candidate_power_reasons = validate_power_snapshot(
            row.candidate_power, tolerance_w=tolerance
        )
        power_reasons.extend(
            f"h{h}:reference_{reason}" for reason in reference_power_reasons
        )
        power_reasons.extend(
            f"h{h}:candidate_{reason}" for reason in candidate_power_reasons
        )
        if not reference_power_reasons and not candidate_power_reasons:
            delta_power = (
                recompute_system_power(row.reference_power).system_power_w
                - recompute_system_power(row.candidate_power).system_power_w
            )
            relief.append(delta_power)
            power_deltas.append(delta_power)
            if delta_power < -tolerance:
                power_reasons.append(f"h{h}:power_increase")
        else:
            power_deltas.append(None)

    if len(power_deltas) != 3 or any(value is None for value in power_deltas):
        power_reasons.append("incomplete_power_interval_recomputation")
    elif not any(value > tolerance for value in relief):
        power_reasons.append("no_strict_power_relief")

    hard_safe = not hard_reasons
    strict_load = hard_safe and not load_reasons
    persistent_power = hard_safe and not power_reasons
    joint = hard_safe and not load_reasons and not power_reasons
    reasons = tuple(hard_reasons + load_reasons + power_reasons)
    ledger = (
        GuardResult("physical_pair", True),
        GuardResult("three_interval_horizon", True),
        GuardResult("hard_safe", hard_safe, ";".join(hard_reasons)),
        GuardResult("strict_load", strict_load, ";".join(load_reasons)),
        GuardResult("persistent_power", persistent_power, ";".join(power_reasons)),
        GuardResult("joint", joint, ";".join(reasons)),
    )
    return CandidateEvidence(
        candidate_id=candidate_physical_id,
        hard_safe=hard_safe,
        strict_load=strict_load,
        persistent_power=persistent_power,
        joint=joint,
        reasons=reasons,
        load_gap_score=sum(gaps),
        power_relief_j=interval_seconds * sum(relief),
        intervals=rows,
        power_delta_w=tuple(power_deltas),
        guard_ledger=ledger,
    )


def support_waterfall(
    candidates: Iterable[CandidateEvidence],
) -> dict[str, int]:
    """Count nested and sign-disagreement support without mixing units."""

    rows = _validated_candidate_rows(candidates)
    return {
        "candidates": len(rows),
        "hard_safe": sum(row.hard_safe for row in rows),
        "strict_load": sum(row.strict_load for row in rows),
        "persistent_power": sum(row.persistent_power for row in rows),
        "joint": sum(row.joint for row in rows),
        "load_only": sum(row.strict_load and not row.persistent_power for row in rows),
        "power_only": sum(row.persistent_power and not row.strict_load for row in rows),
        "sign_disagreement": sum(
            row.strict_load != row.persistent_power
            for row in rows
            if row.hard_safe
        ),
    }


def _validate_candidate_evidence(row: object) -> CandidateEvidence:
    if type(row) is not CandidateEvidence:
        raise ValueError("candidate evidence is malformed")
    validate_physical_id(row.candidate_id, field="candidate physical ID")
    for field in ("hard_safe", "strict_load", "persistent_power", "joint"):
        _strict_bool(getattr(row, field), field=field)
    if row.joint != (row.hard_safe and row.strict_load and row.persistent_power):
        raise ValueError("candidate evidence violates nested support semantics")
    if (row.strict_load or row.persistent_power) and not row.hard_safe:
        raise ValueError("candidate evidence violates nested support semantics")
    if type(row.load_gap_score) is not int:
        raise ValueError("candidate load-gap score must be an exact integer")
    _finite_number(row.power_relief_j, field="candidate power relief")
    if not isinstance(row.reasons, tuple) or any(
        type(reason) is not str for reason in row.reasons
    ):
        raise ValueError("candidate reasons must be a tuple of strings")
    if not isinstance(row.power_delta_w, tuple) or len(row.power_delta_w) not in {0, 3}:
        raise ValueError("candidate power deltas must retain exactly three intervals")
    for value in row.power_delta_w:
        if value is not None:
            _finite_number(value, field="candidate power delta")
    if row.joint and any(value is None for value in row.power_delta_w):
        raise ValueError("joint evidence requires three finite power deltas")
    return row


def _validated_candidate_rows(
    candidates: Iterable[CandidateEvidence],
) -> tuple[CandidateEvidence, ...]:
    try:
        rows = tuple(candidates)
    except TypeError as exc:
        raise ValueError("candidate evidence must be a finite iterable") from exc
    seen: set[PhysicalId] = set()
    for row in rows:
        validated = _validate_candidate_evidence(row)
        if validated.candidate_id in seen:
            raise ValueError("duplicate C3 candidate physical ID")
        seen.add(validated.candidate_id)
    return rows


def select_c3_gap(candidates: Iterable[CandidateEvidence]) -> CandidateEvidence:
    """Maximum load gap, then power relief, then physical ID."""

    rows = _validated_candidate_rows(candidates)
    joint = [row for row in rows if row.joint]
    if not joint:
        raise ValueError("C3-GAP requires non-empty joint support")
    return min(
        joint,
        key=lambda row: (
            -row.load_gap_score,
            -row.power_relief_j,
            row.candidate_id,
        ),
    )


def select_uniform(
    candidates: Iterable[CandidateEvidence],
    *,
    layer: str,
    checkpoint_sha256: str,
    evaluation_seed: int,
    step_index: int,
    focal_user_id: int,
) -> CandidateEvidence:
    """Select from one layer using only its internally derived arm RNG."""

    namespaces = {
        "hard_safe": "SMC-ER-C3-SAFE-R-v2",
        "strict_load": "SMC-ER-C3-LOAD-R-v2",
        "joint": "SMC-ER-C3-CERT-R-v2",
    }
    if layer not in namespaces:
        raise ValueError("unknown C3 support layer")
    rows = _validated_candidate_rows(candidates)
    eligible = sorted(
        (row for row in rows if getattr(row, layer)),
        key=lambda row: row.candidate_id,
    )
    if not eligible:
        raise ValueError(f"C3 {layer} support is empty")
    rng = make_domain_rng(
        namespaces[layer],
        checkpoint_sha256,
        evaluation_seed,
        step_index,
        focal_user_id,
    )
    return eligible[int(rng.integers(0, len(eligible)))]


REQUIRED_ARMS = (
    "reference",
    "C3-SAFE-R",
    "C3-LOAD-R",
    "C3-CERT-R",
    "C3-GAP",
)

REQUIRED_ENGINEERING_GUARDS = (
    "authority_hashes",
    "clone_fingerprints",
    "prefix_replay",
    "physical_remapping",
    "preview_commit_parity",
    "rng_independence",
    "reward_load_identity",
    "pa_recurrence_identity",
    "outcome_timing",
)

WATERFALL_KEYS = (
    "candidates",
    "hard_safe",
    "strict_load",
    "persistent_power",
    "joint",
    "load_only",
    "power_only",
    "sign_disagreement",
)


@dataclass(frozen=True)
class BranchOutcome:
    """Retained five-arm outcomes used by the Stage-0 directional gate."""

    name: str
    r3_extended: float
    r3_episode: float
    forced_power: tuple[PowerSnapshot, ...]
    focal_service_by_interval: tuple[bool, ...]
    served_fraction: float
    nonfocal_actions_by_interval: tuple[Mapping[int, PhysicalId | None], ...]
    event_classes_by_interval: tuple[EventClass, ...]


@dataclass(frozen=True)
class AnchorOutcome:
    """One fully retained eligible anchor before any aggregate is computed."""

    evaluation_seed: int
    step_index: int
    focal_user_id: int
    anchor_id: str
    anchor_fingerprint_sha256: str
    support_waterfall: Mapping[str, int]
    branches: Mapping[str, BranchOutcome]


@dataclass(frozen=True)
class Stage0Receipt:
    """Machine-readable output with no operational-runner or Main authority."""

    arm_names: tuple[str, ...]
    anchors: tuple[AnchorOutcome, ...]
    paired_rows: tuple[Mapping[str, object], ...]
    aggregate: Mapping[str, object]
    guard_ledger: tuple[GuardResult, ...]
    decision: str


def _validate_branch_outcome(
    branch: object,
    *,
    expected_name: str,
    focal_user_id: int,
    expected_user_count: int,
    expected_trace_intervals: int,
) -> tuple[
    tuple[float, ...],
    tuple[dict[int, PhysicalId | None], ...],
    tuple[EventClass, ...],
]:
    if type(branch) is not BranchOutcome:
        raise ValueError(f"branch {expected_name} is malformed")
    if branch.name != expected_name:
        raise ValueError(f"branch key/name mismatch for {expected_name}")
    _finite_number(branch.r3_extended, field=f"{expected_name} extended R3")
    _finite_number(branch.r3_episode, field=f"{expected_name} episode R3")
    served_fraction = _finite_number(
        branch.served_fraction, field=f"{expected_name} served fraction"
    )
    if not 0.0 <= served_fraction <= 1.0:
        raise ValueError(f"{expected_name} served fraction must be in [0,1]")
    if not isinstance(branch.forced_power, tuple) or len(branch.forced_power) != 3:
        raise ValueError(f"{expected_name} must retain exactly three power intervals")
    power_totals: list[float] = []
    for h, snapshot in enumerate(branch.forced_power):
        reasons = validate_power_snapshot(snapshot)
        if reasons:
            raise ValueError(f"{expected_name} h{h} power invalid: {';'.join(reasons)}")
        power_totals.append(recompute_system_power(snapshot).system_power_w)
    if (
        not isinstance(branch.focal_service_by_interval, tuple)
        or len(branch.focal_service_by_interval) != expected_trace_intervals
    ):
        raise ValueError(
            f"{expected_name} must retain service through the exact episode end"
        )
    for value in branch.focal_service_by_interval:
        _strict_bool(value, field=f"{expected_name} focal service")
    if (
        not isinstance(branch.nonfocal_actions_by_interval, tuple)
        or len(branch.nonfocal_actions_by_interval)
        != len(branch.focal_service_by_interval)
    ):
        raise ValueError(f"{expected_name} nonfocal action trace is incomplete")
    action_trace = tuple(
        validate_nonfocal_action_map(
            actions,
            focal_user_id=focal_user_id,
            expected_user_count=expected_user_count,
        )
        for actions in branch.nonfocal_actions_by_interval
    )
    if (
        not isinstance(branch.event_classes_by_interval, tuple)
        or len(branch.event_classes_by_interval) != expected_trace_intervals
    ):
        raise ValueError(f"{expected_name} event trace is incomplete")
    event_trace = tuple(
        validate_event_class(event) for event in branch.event_classes_by_interval
    )
    return tuple(power_totals), action_trace, event_trace


def paired_effects(
    branches: Mapping[str, BranchOutcome],
    *,
    focal_user_id: int = 0,
    expected_user_count: int = 100,
    expected_trace_intervals: int = 4,
) -> dict[str, float | bool]:
    """Recompute five-arm paired effects, realised power, and causality guards."""

    if not isinstance(branches, Mapping) or set(branches) != set(REQUIRED_ARMS):
        raise ValueError("receipt must contain the exact five-arm C3 shape")
    trace_intervals = _validate_user_id(
        expected_trace_intervals, field="expected trace interval count"
    )
    if trace_intervals < 4:
        raise ValueError("C3 outcome trace must include h=0 through h=3")
    validated: dict[
        str,
        tuple[
            tuple[float, ...],
            tuple[dict[int, PhysicalId | None], ...],
            tuple[EventClass, ...],
        ],
    ] = {}
    for name in REQUIRED_ARMS:
        validated[name] = _validate_branch_outcome(
            branches[name],
            expected_name=name,
            focal_user_id=focal_user_id,
            expected_user_count=expected_user_count,
            expected_trace_intervals=trace_intervals,
        )

    reference = branches["reference"]
    safe = branches["C3-SAFE-R"]
    load = branches["C3-LOAD-R"]
    control = branches["C3-CERT-R"]
    gap = branches["C3-GAP"]
    reference_power = validated["reference"][0]
    gap_power = validated["C3-GAP"][0]
    relief = tuple(left - right for left, right in zip(reference_power, gap_power))
    power_guard = all(value >= -POWER_TOLERANCE_W for value in relief) and any(
        value > POWER_TOLERANCE_W for value in relief
    )
    reference_actions = validated["reference"][1]
    nonfocal_guard = all(
        validated[name][1] == reference_actions for name in REQUIRED_ARMS[1:]
    )
    event_guard = True
    for name in REQUIRED_ARMS:
        expected_forced_events = (
            (EventClass.NONE, EventClass.NONE, EventClass.NONE)
            if name == "reference"
            else (EventClass.PHI1, EventClass.NONE, EventClass.NONE)
        )
        if validated[name][2][:3] != expected_forced_events:
            event_guard = False
    return {
        "Delta_R3_ref_extended": gap.r3_extended - reference.r3_extended,
        "Delta_R3_cert_extended": gap.r3_extended - control.r3_extended,
        "Delta_R3_ref_episode": gap.r3_episode - reference.r3_episode,
        "Delta_R3_cert_episode": gap.r3_episode - control.r3_episode,
        "Delta_R3_load_safe_extended": load.r3_extended - safe.r3_extended,
        "Delta_R3_cert_load_extended": control.r3_extended - load.r3_extended,
        "Delta_R3_load_safe_episode": load.r3_episode - safe.r3_episode,
        "Delta_R3_cert_load_episode": control.r3_episode - load.r3_episode,
        "service_delta_ref": gap.served_fraction - reference.served_fraction,
        "service_delta_cert": gap.served_fraction - control.served_fraction,
        "focal_service_preserved": all(gap.focal_service_by_interval),
        "realised_power_guard": power_guard,
        "nonfocal_causality_guard": nonfocal_guard,
        "event_timing_guard": event_guard,
    }


def _validate_effect_rows(
    rows: Sequence[Mapping[str, object]],
) -> tuple[Mapping[str, object], ...]:
    try:
        retained = tuple(rows)
    except TypeError as exc:
        raise ValueError("effect rows must be a finite sequence") from exc
    numeric = (
        PRIMARY_EFFECTS
        + SUPPORTING_EFFECTS
        + ("service_delta_ref", "service_delta_cert")
    )
    boolean = (
        "focal_service_preserved",
        "realised_power_guard",
        "nonfocal_causality_guard",
        "event_timing_guard",
    )
    identities: set[tuple[int, str]] = set()
    for row in retained:
        if not isinstance(row, Mapping):
            raise ValueError("effect row is malformed")
        seed = _validate_user_id(row.get("evaluation_seed"), field="evaluation seed")
        anchor_id = row.get("anchor_id")
        if type(anchor_id) is not str or not anchor_id:
            raise ValueError("anchor ID must be a non-empty string")
        identity = (seed, anchor_id)
        if identity in identities:
            raise ValueError("duplicate retained anchor identity")
        identities.add(identity)
        for key in numeric:
            if key not in row:
                category = "supporting " if key in SUPPORTING_EFFECTS else ""
                raise ValueError(f"effect row missing {category}contrast {key}")
            _finite_number(row[key], field=key)
        for key in boolean:
            if key not in row:
                raise ValueError(f"effect row missing {key}")
            _strict_bool(row[key], field=key)
    return retained


def aggregate_effects(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Equal-anchor pooled means and equal-seed directions from retained rows."""

    retained = _validate_effect_rows(rows)
    if not retained:
        return {
            "eligible_anchors": 0,
            "support_by_seed": {},
            "pooled_mean": {},
            "seed_mean": {},
            "positive_seed_count": {},
        }
    by_seed: dict[int, list[Mapping[str, object]]] = {}
    for row in retained:
        by_seed.setdefault(int(row["evaluation_seed"]), []).append(row)
    numeric = PRIMARY_EFFECTS + ("service_delta_ref", "service_delta_cert")
    pooled = {
        key: statistics.fmean(float(row[key]) for row in retained) for key in numeric
    }
    seed_mean = {
        key: {
            seed: statistics.fmean(float(row[key]) for row in seed_rows)
            for seed, seed_rows in by_seed.items()
        }
        for key in numeric
    }
    return {
        "eligible_anchors": len(retained),
        "support_by_seed": {
            seed: len(seed_rows) for seed, seed_rows in by_seed.items()
        },
        "pooled_mean": pooled,
        "seed_mean": seed_mean,
        "positive_seed_count": {
            key: sum(value > 0.0 for value in values.values())
            for key, values in seed_mean.items()
        },
    }


def stage0_decision(
    rows: Sequence[Mapping[str, object]],
    aggregate: Mapping[str, object],
    *,
    engineering_ok: bool,
) -> str:
    """Recompute aggregates and apply the v2 rule without Main-routing authority."""

    if type(engineering_ok) is not bool or not engineering_ok:
        return CERTIFICATE_FAILURE
    try:
        retained = _validate_effect_rows(rows)
        recomputed = aggregate_effects(retained)
    except (KeyError, TypeError, ValueError, OverflowError):
        return CERTIFICATE_FAILURE
    if not isinstance(aggregate, Mapping) or aggregate != recomputed:
        return CERTIFICATE_FAILURE
    if any(row["nonfocal_causality_guard"] is not True for row in retained):
        return CERTIFICATE_FAILURE
    if any(row["event_timing_guard"] is not True for row in retained):
        return CERTIFICATE_FAILURE

    support = recomputed["support_by_seed"]
    if len(support) != EXPECTED_SEED_COUNT:
        return DROP_ROLE
    if any(value < 1 for value in support.values()):
        return DROP_ROLE
    if recomputed["eligible_anchors"] < MIN_JOINT_ANCHORS:
        return DROP_ROLE

    pooled = recomputed["pooled_mean"]
    directions = recomputed["positive_seed_count"]
    for key in PRIMARY_EFFECTS:
        if pooled[key] <= 0.0:
            return DROP_ROLE
        if directions[key] < MIN_POSITIVE_SEEDS:
            return DROP_ROLE

    if pooled["service_delta_ref"] < -MAX_SERVICE_DECLINE:
        return DROP_ROLE
    if pooled["service_delta_cert"] < -MAX_SERVICE_DECLINE:
        return DROP_ROLE
    if any(row["focal_service_preserved"] is not True for row in retained):
        return DROP_ROLE
    if any(row["realised_power_guard"] is not True for row in retained):
        return DROP_ROLE
    return PASS_RESULT


def _validate_waterfall(value: object) -> None:
    if not isinstance(value, Mapping) or set(value) != set(WATERFALL_KEYS):
        raise ValueError("support waterfall has the wrong schema")
    counts: dict[str, int] = {}
    for key in WATERFALL_KEYS:
        raw = value[key]
        if type(raw) is not int or raw < 0:
            raise ValueError("support waterfall counts must be nonnegative integers")
        counts[key] = raw
    if not (
        counts["joint"] <= counts["strict_load"] <= counts["hard_safe"]
        and counts["joint"] <= counts["persistent_power"] <= counts["hard_safe"]
        and counts["hard_safe"] <= counts["candidates"]
        and counts["load_only"] == counts["strict_load"] - counts["joint"]
        and counts["power_only"] == counts["persistent_power"] - counts["joint"]
        and counts["sign_disagreement"]
        == counts["load_only"] + counts["power_only"]
        and counts["joint"] >= 1
    ):
        raise ValueError("support waterfall violates nested-layer identities")


def build_stage0_receipt(
    anchors: Sequence[AnchorOutcome],
    engineering_guards: Mapping[str, bool],
) -> Stage0Receipt:
    """Build the five-arm receipt and make every structural failure explicit."""

    try:
        retained_anchors = tuple(anchors)
    except TypeError:
        retained_anchors = ()
    ledger: list[GuardResult] = []
    guard_schema_ok = isinstance(engineering_guards, Mapping) and set(
        engineering_guards
    ) == set(REQUIRED_ENGINEERING_GUARDS)
    for name in REQUIRED_ENGINEERING_GUARDS:
        passed = (
            guard_schema_ok
            and type(engineering_guards[name]) is bool
            and engineering_guards[name]
        )
        ledger.append(GuardResult(name, passed, "" if passed else "missing_or_false"))

    rows: list[Mapping[str, object]] = []
    shape_reasons: list[str] = []
    fingerprint_reasons: list[str] = []
    waterfall_reasons: list[str] = []
    identities: set[tuple[int, int, int]] = set()
    for index, anchor in enumerate(retained_anchors):
        if type(anchor) is not AnchorOutcome:
            shape_reasons.append(f"anchor[{index}]:malformed")
            continue
        try:
            seed = _validate_user_id(anchor.evaluation_seed, field="evaluation seed")
            step = _validate_user_id(anchor.step_index, field="anchor step index")
            focal = _validate_user_id(anchor.focal_user_id, field="focal user ID")
            if step > 6:
                raise ValueError("anchor step index must be in {0,...,6}")
            if focal >= 100:
                raise ValueError("focal user ID must be in {0,...,99}")
            if type(anchor.anchor_id) is not str or not anchor.anchor_id:
                raise ValueError("anchor ID must be a non-empty string")
            identity = (seed, step, focal)
            if identity in identities:
                raise ValueError("duplicate anchor identity")
            identities.add(identity)
            if (
                type(anchor.anchor_fingerprint_sha256) is not str
                or _SHA256_HEX.fullmatch(anchor.anchor_fingerprint_sha256) is None
            ):
                fingerprint_reasons.append(f"anchor[{index}]:invalid_fingerprint")
            try:
                _validate_waterfall(anchor.support_waterfall)
            except ValueError as exc:
                waterfall_reasons.append(f"anchor[{index}]:{exc}")
            effects = paired_effects(
                anchor.branches,
                focal_user_id=focal,
                expected_user_count=100,
                expected_trace_intervals=10 - step,
            )
            rows.append(
                {
                    "evaluation_seed": seed,
                    "anchor_id": anchor.anchor_id,
                    **effects,
                }
            )
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            shape_reasons.append(f"anchor[{index}]:{exc}")

    five_arm_ok = not shape_reasons and len(rows) == len(retained_anchors)
    fingerprints_ok = not fingerprint_reasons and bool(retained_anchors)
    waterfall_ok = not waterfall_reasons and bool(retained_anchors)
    ledger.extend(
        (
            GuardResult("five_arm_receipt", five_arm_ok, ";".join(shape_reasons)),
            GuardResult(
                "anchor_fingerprints",
                fingerprints_ok,
                ";".join(fingerprint_reasons),
            ),
            GuardResult(
                "support_waterfalls", waterfall_ok, ";".join(waterfall_reasons)
            ),
        )
    )
    try:
        aggregate = aggregate_effects(rows)
        aggregate_ok = True
        aggregate_detail = ""
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        aggregate = aggregate_effects(())
        aggregate_ok = False
        aggregate_detail = str(exc)
    nonfocal_ok = bool(rows) and all(
        row["nonfocal_causality_guard"] is True for row in rows
    )
    event_timing_ok = bool(rows) and all(
        row["event_timing_guard"] is True for row in rows
    )
    focal_service_ok = bool(rows) and all(
        row["focal_service_preserved"] is True for row in rows
    )
    realised_power_ok = bool(rows) and all(
        row["realised_power_guard"] is True for row in rows
    )
    service_fraction_ok = bool(rows) and aggregate_ok and (
        aggregate["pooled_mean"]["service_delta_ref"] >= -MAX_SERVICE_DECLINE
        and aggregate["pooled_mean"]["service_delta_cert"] >= -MAX_SERVICE_DECLINE
    )
    ledger.extend(
        (
            GuardResult("aggregate_recomputed", aggregate_ok, aggregate_detail),
            GuardResult("nonfocal_causality", nonfocal_ok),
            GuardResult("event_timing", event_timing_ok),
            GuardResult("focal_service_guard", focal_service_ok),
            GuardResult("realised_power_guard", realised_power_ok),
            GuardResult("service_fraction_guard", service_fraction_ok),
        )
    )
    engineering_ok = all(
        entry.passed
        for entry in ledger
        if entry.name
        in set(REQUIRED_ENGINEERING_GUARDS)
        | {
            "five_arm_receipt",
            "anchor_fingerprints",
            "support_waterfalls",
            "aggregate_recomputed",
            "nonfocal_causality",
            "event_timing",
        }
    )
    decision = stage0_decision(rows, aggregate, engineering_ok=engineering_ok)
    return Stage0Receipt(
        arm_names=REQUIRED_ARMS,
        anchors=retained_anchors,
        paired_rows=tuple(rows),
        aggregate=aggregate,
        guard_ledger=tuple(ledger),
        decision=decision,
    )
