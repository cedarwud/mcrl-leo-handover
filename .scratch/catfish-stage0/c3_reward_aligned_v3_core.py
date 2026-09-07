"""Pure deterministic core for the prospective C3 reward-aligned V3 gate.

Canonical rewards, associations, rates, and power-ledger terms are supplied by
the caller.  This module validates identities and support membership only.  It
has no environment, checkpoint, filesystem, RNG, learner, replay, runner,
census, or outcome dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from numbers import Real
from typing import Mapping, Sequence


PhysicalId = tuple[int, int]
PhysicalAction = PhysicalId | None

MAIN_WEIGHTS = (0.5, 0.3, 0.2)
HOLD_STEPS = 3
FIRST_RELEASE_OFFSET = 3
CERTIFICATE_STEPS = 4
DECISION_INTERVAL_S = 30.08
POWER_IDENTITY_REL_TOL = 1e-9


def validate_physical_id(value: object, *, field: str = "physical ID") -> PhysicalId:
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError(f"{field} must be a two-item tuple")
    norad_id, cell_id = value
    if type(norad_id) is not int or type(cell_id) is not int:
        raise ValueError(f"{field} components must be exact integers")
    if norad_id < 0 or cell_id < 0:
        raise ValueError(f"{field} components must be nonnegative")
    return norad_id, cell_id


def unique_physical_id_map(candidate_table: Sequence[object]) -> dict[PhysicalId, int]:
    result: dict[PhysicalId, int] = {}
    for index, raw_id in enumerate(candidate_table):
        physical_id = validate_physical_id(raw_id, field="candidate-table physical ID")
        if physical_id in result:
            raise ValueError("duplicate candidate-table physical ID")
        result[physical_id] = index
    return result


def remap_physical_id(candidate_table: Sequence[object], physical_id: object) -> int:
    target = validate_physical_id(physical_id, field="declared physical ID")
    mapping = unique_physical_id_map(candidate_table)
    if target not in mapping:
        raise ValueError("declared physical ID is not uniquely remappable")
    return mapping[target]


def validate_main_weights(weights: object) -> tuple[float, float, float]:
    if not isinstance(weights, tuple) or len(weights) != 3:
        raise ValueError("Main objective weights must be an exact three-item tuple")
    if any(type(value) is not float for value in weights):
        raise ValueError("Main objective weights must contain exact floats")
    if weights != MAIN_WEIGHTS:
        raise ValueError("Main objective weights drifted from (0.5, 0.3, 0.2)")
    return weights


def _finite_number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field} must be a finite real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be a finite real number")
    return result


def masked_scalarized_main_action(
    q1: Sequence[float],
    q2: Sequence[float],
    q3: Sequence[float],
    mask: Sequence[bool],
    *,
    weights: tuple[float, float, float],
) -> int | None:
    """Return the first masked maximum, matching stable masked-greedy ties."""

    w1, w2, w3 = validate_main_weights(weights)
    width = len(q1)
    if width == 0 or len(q2) != width or len(q3) != width or len(mask) != width:
        raise ValueError("Main Q rows and mask must have one equal nonzero width")
    valid_indices: list[int] = []
    scores: list[float] = []
    for index, allowed in enumerate(mask):
        if type(allowed) is not bool:
            raise ValueError("Main mask entries must be exact booleans")
        values = (q1[index], q2[index], q3[index])
        if any(not isinstance(value, (int, float)) or isinstance(value, bool)
               or not math.isfinite(float(value)) for value in values):
            raise ValueError("Main Q values must be finite numbers")
        if allowed:
            valid_indices.append(index)
            scores.append(w1 * float(values[0]) + w2 * float(values[1]) + w3 * float(values[2]))
    if not valid_indices:
        return None
    best = max(scores)
    return valid_indices[scores.index(best)]


@dataclass(frozen=True)
class ForcedInterval:
    reference_physical_id: PhysicalId | None
    candidate_physical_id: PhysicalId | None
    source_uniquely_remapped: bool = True
    destination_uniquely_remapped: bool = True
    reference_action_valid: bool = True
    candidate_action_valid: bool = True
    reference_recurrence_power_w: float = 0.0
    candidate_recurrence_power_w: float = 0.0
    canonical_link_ceiling_w: float = 1.0
    reference_served: bool = True
    candidate_served: bool = True
    hidden_fallback: bool = False
    expired: bool = False


@dataclass(frozen=True)
class GrammarDecision:
    passed: bool
    source_id: PhysicalId
    destination_id: PhysicalId
    failed_offset: int | None
    reason: str | None


def validate_relocation_grammar(
    *,
    source_id: object,
    destination_id: object,
    destination_already_active_without_focal: bool,
    forced_intervals: Sequence[ForcedInterval],
    reference_release_action: PhysicalAction,
    candidate_release_action: PhysicalAction,
    reference_scalarized_main_action: PhysicalAction,
    candidate_scalarized_main_action: PhysicalAction,
    release_present: bool,
) -> GrammarDecision:
    source = validate_physical_id(source_id, field="source physical ID")
    destination = validate_physical_id(destination_id, field="destination physical ID")
    if source == destination:
        return GrammarDecision(False, source, destination, None, "destination_not_distinct")
    if source[0] != destination[0]:
        return GrammarDecision(False, source, destination, None, "cross_satellite_destination")
    if type(destination_already_active_without_focal) is not bool:
        raise ValueError("already-active flag must be an exact boolean")
    if not destination_already_active_without_focal:
        return GrammarDecision(False, source, destination, None, "destination_not_already_active")
    if len(forced_intervals) != HOLD_STEPS:
        return GrammarDecision(False, source, destination, None, "hold_window_incomplete")
    if type(release_present) is not bool:
        raise ValueError("release-present flag must be an exact boolean")
    if not release_present:
        return GrammarDecision(False, source, destination, FIRST_RELEASE_OFFSET, "release_window_incomplete")
    normalized_release_actions: list[PhysicalAction] = []
    for action, field in (
        (reference_release_action, "reference release action"),
        (candidate_release_action, "candidate release action"),
        (reference_scalarized_main_action, "reference scalarized-Main action"),
        (candidate_scalarized_main_action, "candidate scalarized-Main action"),
    ):
        normalized_release_actions.append(
            None if action is None else validate_physical_id(action, field=field)
        )
    if normalized_release_actions[0] != normalized_release_actions[2]:
        return GrammarDecision(
            False, source, destination, FIRST_RELEASE_OFFSET,
            "reference_release_not_scalarized_main",
        )
    if normalized_release_actions[1] != normalized_release_actions[3]:
        return GrammarDecision(
            False, source, destination, FIRST_RELEASE_OFFSET,
            "candidate_release_not_scalarized_main",
        )

    for offset, interval in enumerate(forced_intervals):
        if not isinstance(interval, ForcedInterval):
            raise ValueError("forced intervals must be ForcedInterval values")
        for value in (
            interval.source_uniquely_remapped,
            interval.destination_uniquely_remapped,
            interval.reference_action_valid,
            interval.candidate_action_valid,
            interval.reference_served,
            interval.candidate_served,
            interval.hidden_fallback,
            interval.expired,
        ):
            if type(value) is not bool:
                raise ValueError("forced-interval flags must be exact booleans")
        if interval.hidden_fallback:
            return GrammarDecision(False, source, destination, offset, "hidden_fallback")
        if interval.expired:
            return GrammarDecision(False, source, destination, offset, "early_expiry")
        if interval.reference_physical_id is None or interval.candidate_physical_id is None:
            return GrammarDecision(False, source, destination, offset, "missing_forced_physical_id")
        reference_id = validate_physical_id(interval.reference_physical_id)
        candidate_id = validate_physical_id(interval.candidate_physical_id)
        if reference_id != source:
            return GrammarDecision(False, source, destination, offset, "reference_source_redraw")
        if candidate_id != destination:
            return GrammarDecision(False, source, destination, offset, "second_relocation_or_redraw")
        if not interval.source_uniquely_remapped or not interval.destination_uniquely_remapped:
            return GrammarDecision(False, source, destination, offset, "physical_id_not_unique")
        if not interval.reference_action_valid or not interval.candidate_action_valid:
            return GrammarDecision(False, source, destination, offset, "forced_action_invalid")
        try:
            reference_power = _finite_number(
                interval.reference_recurrence_power_w,
                field="reference recurrence power",
            )
            candidate_power = _finite_number(
                interval.candidate_recurrence_power_w,
                field="candidate recurrence power",
            )
            link_ceiling = _finite_number(
                interval.canonical_link_ceiling_w,
                field="canonical link ceiling",
            )
        except ValueError:
            return GrammarDecision(False, source, destination, offset, "link_power_nonfinite")
        if (
            link_ceiling < 0.0
            or reference_power < 0.0
            or candidate_power < 0.0
            or reference_power > link_ceiling
            or candidate_power > link_ceiling
        ):
            return GrammarDecision(False, source, destination, offset, "link_power_above_ceiling")
        if not interval.reference_served or not interval.candidate_served:
            return GrammarDecision(False, source, destination, offset, "focal_unserved")
    return GrammarDecision(True, source, destination, None, None)


def _validate_action_rows(
    rows: Sequence[Sequence[PhysicalAction]], *, field: str
) -> tuple[tuple[PhysicalAction, ...], ...]:
    if len(rows) != CERTIFICATE_STEPS:
        raise ValueError(f"{field} must contain exactly four offsets")
    width = len(rows[0])
    result: list[tuple[PhysicalAction, ...]] = []
    for row in rows:
        if len(row) != width:
            raise ValueError(f"{field} rows must have equal width")
        result.append(tuple(None if value is None else validate_physical_id(value, field=field)
                            for value in row))
    return tuple(result)


def nonfocal_physical_identity(
    reference_by_offset: Sequence[Sequence[PhysicalAction]],
    candidate_by_offset: Sequence[Sequence[PhysicalAction]],
) -> bool:
    reference = _validate_action_rows(reference_by_offset, field="reference non-focal actions")
    candidate = _validate_action_rows(candidate_by_offset, field="candidate non-focal actions")
    return reference == candidate


def reconstruct_eligible_loads(
    served_associations: Sequence[PhysicalAction],
) -> dict[PhysicalId, int]:
    loads: dict[PhysicalId, int] = {}
    for action in served_associations:
        if action is None:
            continue
        physical_id = validate_physical_id(action, field="served physical association")
        loads[physical_id] = loads.get(physical_id, 0) + 1
    return loads


def _validate_load_map(loads: Mapping[object, object], *, field: str) -> dict[PhysicalId, int]:
    result: dict[PhysicalId, int] = {}
    for raw_id, raw_count in loads.items():
        physical_id = validate_physical_id(raw_id, field=field)
        if type(raw_count) is not int or raw_count <= 0:
            raise ValueError(f"{field} counts must be positive exact integers")
        if physical_id in result:
            raise ValueError(f"{field} contains a duplicate physical ID")
        result[physical_id] = raw_count
    return result


@dataclass(frozen=True)
class LoadSnapshot:
    served_associations: tuple[PhysicalAction, ...]
    reported_eligible_loads: Mapping[PhysicalId, int]
    reported_active_beams: frozenset[PhysicalId]
    canonical_r3_by_user: tuple[float, ...]


@dataclass(frozen=True)
class LoadIdentityDecision:
    passed: bool
    reasons: tuple[str, ...]
    reconstructed_loads: Mapping[PhysicalId, int]
    canonical_r3_total: float
    squared_load_total: int


def validate_load_snapshot(snapshot: LoadSnapshot) -> LoadIdentityDecision:
    associations = tuple(
        None if value is None else validate_physical_id(value, field="served association")
        for value in snapshot.served_associations
    )
    if len(snapshot.canonical_r3_by_user) != len(associations):
        raise ValueError("canonical r3 row must align with all user associations")
    reported = _validate_load_map(snapshot.reported_eligible_loads, field="eligible-load map")
    active = frozenset(
        validate_physical_id(value, field="active beam") for value in snapshot.reported_active_beams
    )
    reconstructed = reconstruct_eligible_loads(associations)
    reasons: list[str] = []
    if reported != reconstructed:
        reasons.append("eligible_load_reconstruction_mismatch")
    if set(reported) != set(active):
        reasons.append("positive_load_active_beam_mismatch")
    if sum(reported.values()) != sum(action is not None for action in associations):
        reasons.append("load_sum_served_count_mismatch")
    expected_r3: list[float] = []
    for action in associations:
        expected_r3.append(0.0 if action is None else -float(reported.get(action, 0)))
    canonical: list[float] = []
    for value in snapshot.canonical_r3_by_user:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            raise ValueError("canonical r3 values must be finite numbers")
        canonical.append(float(value))
    if tuple(canonical) != tuple(expected_r3):
        reasons.append("canonical_r3_per_user_mismatch")
    canonical_total = sum(canonical)
    squared_total = sum(count * count for count in reported.values())
    if canonical_total != -float(squared_total):
        reasons.append("canonical_r3_squared_load_mismatch")
    return LoadIdentityDecision(
        not reasons, tuple(reasons), reconstructed, canonical_total, squared_total
    )


@dataclass(frozen=True)
class RelocationLoadDecision:
    passed: bool
    reasons: tuple[str, ...]
    source_load: int
    destination_load: int
    load_gap: int
    expected_system_r3_delta: int
    reported_system_r3_delta: float


def validate_relocation_load_identity(
    *,
    source_id: PhysicalId,
    destination_id: PhysicalId,
    reference: LoadSnapshot,
    candidate: LoadSnapshot,
) -> RelocationLoadDecision:
    source = validate_physical_id(source_id, field="source physical ID")
    destination = validate_physical_id(destination_id, field="destination physical ID")
    if source == destination or source[0] != destination[0]:
        raise ValueError("load identity requires distinct same-satellite beams")
    reference_result = validate_load_snapshot(reference)
    candidate_result = validate_load_snapshot(candidate)
    reference_loads = _validate_load_map(reference.reported_eligible_loads, field="reference loads")
    candidate_loads = _validate_load_map(candidate.reported_eligible_loads, field="candidate loads")
    source_load = reference_loads.get(source, 0)
    destination_load = reference_loads.get(destination, 0)
    expected_candidate = dict(reference_loads)
    if source_load <= 0:
        raise ValueError("reference source must include the focal user")
    if source_load == 1:
        del expected_candidate[source]
    else:
        expected_candidate[source] = source_load - 1
    expected_candidate[destination] = destination_load + 1
    reasons: list[str] = []
    if not reference_result.passed:
        reasons.append("reference_load_snapshot_invalid")
    if not candidate_result.passed:
        reasons.append("candidate_load_snapshot_invalid")
    if candidate_loads != expected_candidate:
        reasons.append("not_exact_source_minus_one_destination_plus_one")
    if source_load < destination_load + 2:
        reasons.append("strict_load_gap_failed")
    expected_delta = 2 * (source_load - destination_load - 1)
    reported_delta = candidate_result.canonical_r3_total - reference_result.canonical_r3_total
    if reported_delta != float(expected_delta):
        reasons.append("canonical_r3_delta_mismatch")
    if expected_delta <= 0:
        reasons.append("canonical_r3_delta_not_strictly_positive")
    return RelocationLoadDecision(
        not reasons, tuple(dict.fromkeys(reasons)), source_load, destination_load,
        source_load - destination_load, expected_delta, reported_delta,
    )


def _finite_nonnegative(value: object, *, field: str) -> float:
    result = _finite_number(value, field=field)
    if result < 0.0:
        raise ValueError(f"{field} must be finite and nonnegative")
    return result


def _rel_close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=POWER_IDENTITY_REL_TOL, abs_tol=0.0)


@dataclass(frozen=True)
class BeamPowerTerms:
    beam_id: PhysicalId
    recurrence_outputs_w: tuple[float, ...]
    reported_beam_max_w: float
    reported_pa_efficiency: float
    reported_pa_supply_w: float


@dataclass(frozen=True)
class PowerIntervalTerms:
    beams: tuple[BeamPowerTerms, ...]
    active_beam_counts_by_satellite: Mapping[int, int]
    circuit_power_per_active_beam_w: float
    baseband_power_per_active_satellite_w: float
    reported_fixed_power_w: float
    reported_system_power_w: float


@dataclass(frozen=True)
class PowerIdentityDecision:
    passed: bool
    reasons: tuple[str, ...]
    reconstructed_fixed_power_w: float
    reconstructed_system_power_w: float


def validate_power_identity(terms: PowerIntervalTerms) -> PowerIdentityDecision:
    reasons: list[str] = []
    circuit = _finite_nonnegative(terms.circuit_power_per_active_beam_w, field="circuit power")
    baseband = _finite_nonnegative(terms.baseband_power_per_active_satellite_w, field="baseband power")
    counts: dict[int, int] = {}
    for satellite, count in terms.active_beam_counts_by_satellite.items():
        if type(satellite) is not int or satellite < 0 or type(count) is not int or count < 0:
            raise ValueError("active-beam counts must use nonnegative exact integers")
        counts[satellite] = count
    seen: set[PhysicalId] = set()
    actual_counts: dict[int, int] = {}
    supply_total = 0.0
    for beam in terms.beams:
        beam_id = validate_physical_id(beam.beam_id, field="power beam")
        if beam_id in seen:
            raise ValueError("duplicate power beam")
        seen.add(beam_id)
        if not beam.recurrence_outputs_w:
            reasons.append(f"{beam_id}:missing_recurrence_output")
            recurrence_max = 0.0
        else:
            recurrence = tuple(
                _finite_nonnegative(value, field="canonical recurrence output")
                for value in beam.recurrence_outputs_w
            )
            recurrence_max = max(recurrence)
        beam_max = _finite_nonnegative(beam.reported_beam_max_w, field="beam max power")
        efficiency = _finite_number(
            beam.reported_pa_efficiency, field="PA efficiency"
        )
        if efficiency <= 0.0:
            raise ValueError("PA efficiency must be finite and positive")
        supply = _finite_nonnegative(beam.reported_pa_supply_w, field="PA supply power")
        if not _rel_close(beam_max, recurrence_max):
            reasons.append(f"{beam_id}:beam_max_mismatch")
        if not _rel_close(supply, beam_max / efficiency):
            reasons.append(f"{beam_id}:pa_supply_mismatch")
        supply_total += supply
        actual_counts[beam_id[0]] = actual_counts.get(beam_id[0], 0) + 1
    normalized_counts = {satellite: count for satellite, count in counts.items() if count > 0}
    if actual_counts != normalized_counts:
        reasons.append("active_beam_count_mismatch")
    fixed = sum(
        count * circuit + (baseband if count > 0 else 0.0)
        for count in counts.values()
    )
    system = fixed + supply_total
    reported_fixed = _finite_nonnegative(terms.reported_fixed_power_w, field="reported fixed power")
    reported_system = _finite_nonnegative(terms.reported_system_power_w, field="reported system power")
    if not _rel_close(reported_fixed, fixed):
        reasons.append("fixed_power_mismatch")
    if not _rel_close(reported_system, system):
        reasons.append("system_power_mismatch")
    return PowerIdentityDecision(not reasons, tuple(reasons), fixed, system)


@dataclass(frozen=True)
class PowerWindowDecision:
    passed: bool
    reasons: tuple[str, ...]
    reference_energy_j: float
    candidate_energy_j: float
    strict_decrease_offsets: tuple[int, ...]


def evaluate_power_window(
    reference: Sequence[PowerIntervalTerms], candidate: Sequence[PowerIntervalTerms]
) -> PowerWindowDecision:
    if len(reference) != CERTIFICATE_STEPS or len(candidate) != CERTIFICATE_STEPS:
        raise ValueError("power window must contain offsets 0 through 3")
    reasons: list[str] = []
    reference_totals: list[float] = []
    candidate_totals: list[float] = []
    strict: list[int] = []
    for offset, (reference_terms, candidate_terms) in enumerate(zip(reference, candidate)):
        reference_identity = validate_power_identity(reference_terms)
        candidate_identity = validate_power_identity(candidate_terms)
        if not reference_identity.passed:
            reasons.append(f"offset_{offset}:reference_power_identity_failed")
        if not candidate_identity.passed:
            reasons.append(f"offset_{offset}:candidate_power_identity_failed")
        reference_total = reference_identity.reconstructed_system_power_w
        candidate_total = candidate_identity.reconstructed_system_power_w
        reference_totals.append(reference_total)
        candidate_totals.append(candidate_total)
        if candidate_total > reference_total:
            reasons.append(f"offset_{offset}:candidate_power_increase")
        elif candidate_total < reference_total:
            strict.append(offset)
    reference_energy = DECISION_INTERVAL_S * sum(reference_totals)
    candidate_energy = DECISION_INTERVAL_S * sum(candidate_totals)
    if (
        not math.isfinite(reference_energy)
        or not math.isfinite(candidate_energy)
        or reference_energy <= 0.0
        or candidate_energy <= 0.0
    ):
        reasons.append("certificate_energy_not_finite_positive")
    return PowerWindowDecision(
        not reasons, tuple(reasons), reference_energy, candidate_energy, tuple(strict)
    )


class EventClass(str, Enum):
    NONE = "none"
    INTRA_SATELLITE = "phi1"
    INTER_SATELLITE = "phi2"


@dataclass(frozen=True)
class ReleaseReport:
    reference_focal_r3: float
    candidate_focal_r3: float
    reference_system_r3: float
    candidate_system_r3: float


@dataclass(frozen=True)
class RewardServiceEventDecision:
    passed: bool
    reasons: tuple[str, ...]
    reference_hold_r3: float
    candidate_hold_r3: float
    reference_full_r3: float
    candidate_full_r3: float
    release: ReleaseReport


def evaluate_reward_service_events(
    *,
    reference_r3: Sequence[Sequence[float]],
    candidate_r3: Sequence[Sequence[float]],
    focal_user: int,
    reference_served: Sequence[Sequence[bool]],
    candidate_served: Sequence[Sequence[bool]],
    reference_reentry: Sequence[Sequence[bool]],
    candidate_reentry: Sequence[Sequence[bool]],
    reference_events: Sequence[Sequence[EventClass]],
    candidate_events: Sequence[Sequence[EventClass]],
    release_report: ReleaseReport | None,
) -> RewardServiceEventDecision:
    matrices = (
        reference_r3, candidate_r3, reference_served, candidate_served,
        reference_reentry, candidate_reentry, reference_events, candidate_events,
    )
    if any(len(matrix) != CERTIFICATE_STEPS for matrix in matrices):
        raise ValueError("reward/service/event certificate must contain four offsets")
    user_count = len(reference_r3[0])
    if user_count < 1 or type(focal_user) is not int or not 0 <= focal_user < user_count:
        raise ValueError("focal user must index a nonempty user matrix")
    if any(len(row) != user_count for matrix in matrices for row in matrix):
        raise ValueError("reward/service/event rows must have identical user width")
    for matrix in (reference_r3, candidate_r3):
        for row in matrix:
            for value in row:
                _finite_number(value, field="canonical r3 value")
    for matrix in (
        reference_served, candidate_served, reference_reentry, candidate_reentry,
    ):
        for row in matrix:
            if any(type(value) is not bool for value in row):
                raise ValueError("service and reentry rows must contain exact booleans")
    for matrix in (reference_events, candidate_events):
        for row in matrix:
            if any(type(value) is not EventClass for value in row):
                raise ValueError("event rows must contain EventClass values")
    reference_hold = sum(sum(float(value) for value in row) for row in reference_r3[:3])
    candidate_hold = sum(sum(float(value) for value in row) for row in candidate_r3[:3])
    reference_full = reference_hold + sum(float(value) for value in reference_r3[3])
    candidate_full = candidate_hold + sum(float(value) for value in candidate_r3[3])
    actual_release = ReleaseReport(
        float(reference_r3[3][focal_user]),
        float(candidate_r3[3][focal_user]),
        sum(float(value) for value in reference_r3[3]),
        sum(float(value) for value in candidate_r3[3]),
    )
    reasons: list[str] = []
    if candidate_hold <= reference_hold:
        reasons.append("system_hold_r3_not_strictly_better")
    if candidate_full <= reference_full:
        reasons.append("system_full_r3_not_strictly_better")
    if release_report is None:
        reasons.append("release_row_omitted")
    else:
        if not isinstance(release_report, ReleaseReport):
            raise ValueError("release row must be a ReleaseReport")
        supplied_release = ReleaseReport(
            _finite_number(release_report.reference_focal_r3, field="release r3"),
            _finite_number(release_report.candidate_focal_r3, field="release r3"),
            _finite_number(release_report.reference_system_r3, field="release r3"),
            _finite_number(release_report.candidate_system_r3, field="release r3"),
        )
        if supplied_release != actual_release:
            reasons.append("release_row_mismatch")
    if any(
        not reference_served[offset][focal_user]
        or not candidate_served[offset][focal_user]
        for offset in range(CERTIFICATE_STEPS)
    ):
        reasons.append("focal_outage")
    if any(
        reference_reentry[offset][focal_user] or candidate_reentry[offset][focal_user]
        for offset in range(CERTIFICATE_STEPS)
    ):
        reasons.append("focal_reentry")
    if any(
        reference_served[offset][user] and not candidate_served[offset][user]
        for offset in range(CERTIFICATE_STEPS)
        for user in range(user_count)
    ):
        reasons.append("served_to_unserved")
    if any(
        bool(reference_served[offset][user]) != bool(candidate_served[offset][user])
        for offset in range(CERTIFICATE_STEPS)
        for user in range(user_count)
    ):
        reasons.append("served_user_set_mismatch")
    if any(
        event is not EventClass.NONE
        for row in reference_events
        for event in row
    ):
        reasons.append("undeclared_reference_event")
    if any(
        event is not (
            EventClass.INTRA_SATELLITE
            if offset == 0 and user == focal_user
            else EventClass.NONE
        )
        for offset, row in enumerate(candidate_events)
        for user, event in enumerate(row)
    ):
        reasons.append("undeclared_candidate_event")
    return RewardServiceEventDecision(
        not reasons, tuple(dict.fromkeys(reasons)), reference_hold, candidate_hold,
        reference_full, candidate_full, actual_release,
    )


@dataclass(frozen=True)
class HardSafeIdentityDecision:
    passed: bool
    reasons: tuple[str, ...]


def evaluate_hard_safe_identity(
    *,
    reference_nonfocal_actions: Sequence[Sequence[PhysicalAction]],
    candidate_nonfocal_actions: Sequence[Sequence[PhysicalAction]],
    reference_active_beams: Sequence[frozenset[PhysicalId]],
    candidate_active_beams: Sequence[frozenset[PhysicalId]],
    reference_active_satellites: Sequence[frozenset[int]],
    candidate_active_satellites: Sequence[frozenset[int]],
    preview_commit_equal: Sequence[bool],
) -> HardSafeIdentityDecision:
    if any(len(values) != CERTIFICATE_STEPS for values in (
        reference_active_beams, candidate_active_beams,
        reference_active_satellites, candidate_active_satellites,
        preview_commit_equal,
    )):
        raise ValueError("hard-safe identity must cover four offsets")
    reasons: list[str] = []
    if not nonfocal_physical_identity(reference_nonfocal_actions, candidate_nonfocal_actions):
        reasons.append("nonfocal_physical_action_mismatch")
    for offset in range(CERTIFICATE_STEPS):
        reference_beams = frozenset(validate_physical_id(value) for value in reference_active_beams[offset])
        candidate_beams = frozenset(validate_physical_id(value) for value in candidate_active_beams[offset])
        if reference_beams != candidate_beams:
            reasons.append(f"offset_{offset}:active_beam_set_mismatch")
        reference_satellites = frozenset(reference_active_satellites[offset])
        candidate_satellites = frozenset(candidate_active_satellites[offset])
        if any(type(value) is not int or value < 0 for value in reference_satellites | candidate_satellites):
            raise ValueError("active satellite IDs must be nonnegative exact integers")
        if reference_satellites != candidate_satellites:
            reasons.append(f"offset_{offset}:active_satellite_set_mismatch")
        if reference_satellites != frozenset(beam[0] for beam in reference_beams):
            reasons.append(f"offset_{offset}:reference_active_satellite_projection_mismatch")
        if candidate_satellites != frozenset(beam[0] for beam in candidate_beams):
            reasons.append(f"offset_{offset}:candidate_active_satellite_projection_mismatch")
        if type(preview_commit_equal[offset]) is not bool:
            raise ValueError("preview/commit flags must be exact booleans")
        if not preview_commit_equal[offset]:
            reasons.append(f"offset_{offset}:preview_commit_mismatch")
    return HardSafeIdentityDecision(not reasons, tuple(reasons))


@dataclass(frozen=True)
class BinaryProxyDecision:
    passed: bool
    reasons: tuple[str, ...]
    reference_ee_bits_per_j: float | None
    surplus_bits: float | None


def evaluate_binary_proxies(
    *,
    reference_useful_bits: float,
    candidate_useful_bits: float,
    reference_energy_j: float,
    candidate_energy_j: float,
) -> BinaryProxyDecision:
    values = tuple(
        _finite_number(value, field="binary-proxy accumulation")
        for value in (
            reference_useful_bits, candidate_useful_bits,
            reference_energy_j, candidate_energy_j,
        )
    )
    reference_useful_bits, candidate_useful_bits, reference_energy_j, candidate_energy_j = values
    reasons: list[str] = []
    if reference_useful_bits < 0.0 or candidate_useful_bits < 0.0:
        reasons.append("useful_bits_negative")
    if not reasons and (reference_energy_j <= 0.0 or candidate_energy_j <= 0.0):
        reasons.append("energy_not_strictly_positive")
    eta: float | None = None
    surplus: float | None = None
    if not reasons:
        eta = reference_useful_bits / reference_energy_j
        surplus = (
            candidate_useful_bits - reference_useful_bits
            - eta * (candidate_energy_j - reference_energy_j)
        )
        if candidate_useful_bits < reference_useful_bits:
            reasons.append("useful_bits_loss")
        if not math.isfinite(eta) or not math.isfinite(surplus):
            reasons.append("nonfinite_proxy")
        elif surplus <= 0.0:
            reasons.append("surplus_not_strictly_positive")
    return BinaryProxyDecision(not reasons, tuple(reasons), eta, surplus)


@dataclass(frozen=True)
class LayerEvidence:
    scheduled_anchor: bool
    qualifying_main_anchor: bool
    unique_candidate: bool
    hard_safe: bool
    strict_load: bool
    complete_power: bool
    binary_proxies: bool
    through_release: bool


_LAYER_FIELDS = (
    "scheduled_anchor", "qualifying_main_anchor", "unique_candidate", "hard_safe",
    "strict_load", "complete_power", "binary_proxies", "through_release",
)


@dataclass(frozen=True)
class LayerDecision:
    passed_layers: tuple[str, ...]
    certified: bool
    first_failed_layer: str | None


def evaluate_layers(evidence: LayerEvidence) -> LayerDecision:
    passed: list[str] = []
    for field in _LAYER_FIELDS:
        value = getattr(evidence, field)
        if type(value) is not bool:
            raise ValueError("layer evidence values must be exact booleans")
        if not value:
            return LayerDecision(tuple(passed), False, field)
        passed.append(field)
    passed.append("certified_choice")
    return LayerDecision(tuple(passed), True, None)


@dataclass(frozen=True)
class SupportSets:
    safe: frozenset[PhysicalId]
    load: frozenset[PhysicalId]
    certified: frozenset[PhysicalId]


def support_sets(candidates: Mapping[PhysicalId, LayerEvidence]) -> SupportSets:
    safe: set[PhysicalId] = set()
    load: set[PhysicalId] = set()
    certified: set[PhysicalId] = set()
    for raw_id, evidence in candidates.items():
        physical_id = validate_physical_id(raw_id)
        values = tuple(getattr(evidence, field) for field in _LAYER_FIELDS)
        if any(type(value) is not bool for value in values):
            raise ValueError("layer evidence values must be exact booleans")
        if all(values[:4]):
            safe.add(physical_id)
        if all(values[:5]):
            load.add(physical_id)
        if all(values):
            certified.add(physical_id)
    return SupportSets(frozenset(safe), frozenset(load), frozenset(certified))


class ControlArm(str, Enum):
    SAFE_RANDOM = "C3-SAFE-R"
    LOAD_RANDOM = "C3-LOAD-R"
    CERT_RANDOM = "C3-CERT-R"
    GAP = "C3-GAP"
    LEARNED = "C3-I"


def control_support(arm: ControlArm, supports: SupportSets) -> frozenset[PhysicalId]:
    safe = frozenset(validate_physical_id(value) for value in supports.safe)
    load = frozenset(validate_physical_id(value) for value in supports.load)
    certified = frozenset(validate_physical_id(value) for value in supports.certified)
    if not certified <= load <= safe:
        raise ValueError("C3 control supports must be nested CERT inside LOAD inside SAFE")
    if arm is ControlArm.SAFE_RANDOM:
        return safe
    if arm is ControlArm.LOAD_RANDOM:
        return load
    if arm in (ControlArm.CERT_RANDOM, ControlArm.GAP):
        return certified
    if arm is ControlArm.LEARNED:
        raise ValueError("C3-I is absent from Stage-0")
    raise ValueError("unknown C3 control arm")


def select_c3_gap(
    *,
    certified_support: Sequence[PhysicalId],
    cumulative_direct_load_gap: Mapping[PhysicalId, int],
) -> PhysicalId:
    """Rank only the direct load gap, then the frozen physical-ID order."""

    normalized_support = tuple(
        validate_physical_id(value) for value in certified_support
    )
    support = frozenset(normalized_support)
    if len(normalized_support) != len(support):
        raise ValueError("C3-GAP support contains a duplicate physical ID")
    if not support:
        raise ValueError("C3-GAP requires nonempty certified support")
    if set(cumulative_direct_load_gap) != set(support):
        raise ValueError("C3-GAP scores must exactly cover certified support")
    scores: dict[PhysicalId, int] = {}
    for raw_id, score in cumulative_direct_load_gap.items():
        physical_id = validate_physical_id(raw_id)
        if type(score) is not int or score <= 0:
            raise ValueError("cumulative direct load gap must be a positive exact integer")
        scores[physical_id] = score
    return min(support, key=lambda physical_id: (-scores[physical_id], physical_id))


@dataclass(frozen=True)
class AliasState:
    specialist_observation: tuple[float, ...]
    main_observation: tuple[float, ...]
    eligible_support: frozenset[PhysicalId]


@dataclass(frozen=True)
class DualAliasDecision:
    specialist_unresolved: bool
    main_unresolved: bool


def _channel_alias_unresolved(
    states: Sequence[AliasState], *, field: str
) -> bool:
    seen: dict[tuple[float, ...], frozenset[PhysicalId]] = {}
    width: int | None = None
    for state in states:
        observation = tuple(
            _finite_number(value, field=f"{field} observation")
            for value in getattr(state, field)
        )
        if not observation:
            raise ValueError(f"{field} observations must be nonempty")
        if width is None:
            width = len(observation)
        elif len(observation) != width:
            raise ValueError(f"{field} observations must have one fixed width")
        support = frozenset(validate_physical_id(value) for value in state.eligible_support)
        if observation in seen and seen[observation] != support:
            return True
        seen[observation] = support
    return False


def observational_alias_decision(states: Sequence[AliasState]) -> DualAliasDecision:
    """Audit specialist and Main observation channels independently."""

    return DualAliasDecision(
        specialist_unresolved=_channel_alias_unresolved(
            states, field="specialist_observation"
        ),
        main_unresolved=_channel_alias_unresolved(states, field="main_observation"),
    )


@dataclass(frozen=True)
class AnchorSupportRow:
    partition: int
    anchor_id: str
    certified_choices: frozenset[PhysicalId]


@dataclass(frozen=True)
class SupportFloorDecision:
    passed: bool
    qualifying_anchors_by_partition: Mapping[int, int]
    pooled_qualifying_anchors: int


def aggregate_support_floor(
    rows: Sequence[AnchorSupportRow],
    *,
    scheduled_anchor_ids_by_partition: Mapping[int, Sequence[str]],
    minimum_pooled_two_choice_anchors: int = 20,
) -> SupportFloorDecision:
    """Apply the frozen five-partition/two-choice floor without imputation."""

    if (
        type(minimum_pooled_two_choice_anchors) is not int
        or minimum_pooled_two_choice_anchors < 1
    ):
        raise ValueError("minimum pooled two-choice anchors must be a positive integer")
    if set(scheduled_anchor_ids_by_partition) != set(range(5)):
        raise ValueError("support floor requires exactly partitions 0 through 4")
    expected: set[tuple[int, str]] = set()
    for partition, raw_ids in scheduled_anchor_ids_by_partition.items():
        if type(partition) is not int:
            raise ValueError("support-floor partitions must be exact integers")
        ids = tuple(raw_ids)
        if any(type(anchor_id) is not str or not anchor_id for anchor_id in ids):
            raise ValueError("scheduled anchor IDs must be nonempty exact strings")
        if len(ids) != len(set(ids)):
            raise ValueError("scheduled anchor IDs must be unique within a partition")
        expected.update((partition, anchor_id) for anchor_id in ids)

    observed: dict[tuple[int, str], AnchorSupportRow] = {}
    for row in rows:
        if not isinstance(row, AnchorSupportRow):
            raise ValueError("support rows must be AnchorSupportRow values")
        if type(row.partition) is not int or row.partition not in range(5):
            raise ValueError("support-row partition must be an integer from 0 through 4")
        if type(row.anchor_id) is not str or not row.anchor_id:
            raise ValueError("support-row anchor ID must be a nonempty string")
        if type(row.certified_choices) is not frozenset:
            raise ValueError("certified choices must be a frozenset")
        choices = frozenset(
            validate_physical_id(value, field="certified choice physical ID")
            for value in row.certified_choices
        )
        key = (row.partition, row.anchor_id)
        if key in observed:
            raise ValueError("duplicate support row")
        observed[key] = AnchorSupportRow(row.partition, row.anchor_id, choices)
    if set(observed) != expected:
        raise ValueError("support rows must exactly cover the frozen schedule; no imputation")

    counts = {
        partition: sum(
            len(observed[(partition, anchor_id)].certified_choices) >= 2
            for anchor_id in anchor_ids
        )
        for partition, anchor_ids in scheduled_anchor_ids_by_partition.items()
    }
    pooled = sum(counts.values())
    return SupportFloorDecision(
        all(count >= 1 for count in counts.values())
        and pooled >= minimum_pooled_two_choice_anchors,
        counts,
        pooled,
    )


@dataclass(frozen=True)
class CandidateCertificateParts:
    scheduled_anchor: bool
    qualifying_main_anchor: bool
    grammar: GrammarDecision
    hard_safe: HardSafeIdentityDecision
    hold_loads: tuple[RelocationLoadDecision, ...]
    power: PowerWindowDecision
    binary_proxies: BinaryProxyDecision
    through_release: RewardServiceEventDecision


@dataclass(frozen=True)
class CompositeCertificateDecision:
    passed: bool
    first_failed_layer: str | None
    first_failed_offset: int | None
    reasons: tuple[str, ...]
    layer_evidence: LayerEvidence


def _first_offset_from_reasons(reasons: Sequence[str]) -> int | None:
    for reason in reasons:
        if reason.startswith("offset_") and ":" in reason:
            raw = reason.split(":", 1)[0].removeprefix("offset_")
            if raw.isdigit():
                return int(raw)
    return None


def compose_candidate_certificate(
    parts: CandidateCertificateParts,
) -> CompositeCertificateDecision:
    """Compose validated primitives in the frozen layer order."""

    if not isinstance(parts, CandidateCertificateParts):
        raise ValueError("certificate parts must be CandidateCertificateParts")
    if type(parts.scheduled_anchor) is not bool or type(parts.qualifying_main_anchor) is not bool:
        raise ValueError("anchor layer flags must be exact booleans")
    if not isinstance(parts.grammar, GrammarDecision):
        raise ValueError("grammar decision has the wrong type")
    if not isinstance(parts.hard_safe, HardSafeIdentityDecision):
        raise ValueError("hard-safe decision has the wrong type")
    if len(parts.hold_loads) != HOLD_STEPS or any(
        not isinstance(value, RelocationLoadDecision) for value in parts.hold_loads
    ):
        raise ValueError("hold-load decisions must cover exactly offsets 0 through 2")
    if not isinstance(parts.power, PowerWindowDecision):
        raise ValueError("power decision has the wrong type")
    if not isinstance(parts.binary_proxies, BinaryProxyDecision):
        raise ValueError("binary-proxy decision has the wrong type")
    if not isinstance(parts.through_release, RewardServiceEventDecision):
        raise ValueError("through-release decision has the wrong type")

    evidence = LayerEvidence(
        scheduled_anchor=parts.scheduled_anchor,
        qualifying_main_anchor=parts.qualifying_main_anchor,
        unique_candidate=parts.grammar.passed,
        hard_safe=parts.hard_safe.passed,
        strict_load=all(value.passed for value in parts.hold_loads),
        complete_power=parts.power.passed,
        binary_proxies=parts.binary_proxies.passed,
        through_release=parts.through_release.passed,
    )
    if not parts.scheduled_anchor:
        return CompositeCertificateDecision(
            False, "scheduled_anchor", None, ("anchor_not_scheduled",), evidence
        )
    if not parts.qualifying_main_anchor:
        return CompositeCertificateDecision(
            False, "qualifying_main_anchor", None,
            ("scalarized_main_anchor_not_qualified",), evidence,
        )
    if not parts.grammar.passed:
        return CompositeCertificateDecision(
            False, "unique_candidate", parts.grammar.failed_offset,
            (parts.grammar.reason or "candidate_grammar_failed",), evidence,
        )
    if not parts.hard_safe.passed:
        return CompositeCertificateDecision(
            False, "hard_safe", _first_offset_from_reasons(parts.hard_safe.reasons),
            parts.hard_safe.reasons, evidence,
        )
    for offset, decision in enumerate(parts.hold_loads):
        if not decision.passed:
            return CompositeCertificateDecision(
                False, "strict_load", offset, decision.reasons, evidence
            )
    if not parts.power.passed:
        return CompositeCertificateDecision(
            False, "complete_power", _first_offset_from_reasons(parts.power.reasons),
            parts.power.reasons, evidence,
        )
    if not parts.binary_proxies.passed:
        return CompositeCertificateDecision(
            False, "binary_proxies", None, parts.binary_proxies.reasons, evidence
        )
    if not parts.through_release.passed:
        return CompositeCertificateDecision(
            False, "through_release", None, parts.through_release.reasons, evidence
        )
    return CompositeCertificateDecision(True, None, None, (), evidence)
