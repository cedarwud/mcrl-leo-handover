"""Pure deterministic semantics for the C2 activation-churn V3 Stage-0 gate.

The module deliberately has no environment, checkpoint, RNG, filesystem,
learner, replay, or runner dependency.  Canonical interval values are inputs:
the helpers below validate identities and certificate inequalities, but do not
reimplement simulator physics or rewards.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Mapping, Sequence


PhysicalId = tuple[int, int]
PhysicalAction = PhysicalId | None

HOLD_STEPS = 3
FIRST_RELEASE_OFFSET = 3
CERTIFICATE_OFFSETS = (0, 1, 2, 3)
RELATIVE_IDENTITY_TOLERANCE = 1e-9


def _strict_bool(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} must be a Boolean")
    return value


def validate_physical_id(value: object, *, field: str = "physical ID") -> PhysicalId:
    """Return an exact nonnegative ``(norad_id, cell_id)`` identity."""

    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError(f"{field} must be a two-item tuple")
    norad_id, cell_id = value
    if type(norad_id) is not int or type(cell_id) is not int:
        raise ValueError(f"{field} components must be exact integers")
    if norad_id < 0 or cell_id < 0:
        raise ValueError(f"{field} components must be nonnegative")
    return norad_id, cell_id


def unique_physical_id_map(candidate_table: Sequence[object]) -> dict[PhysicalId, int]:
    """Map physical IDs to current indices, rejecting duplicate identities."""

    result: dict[PhysicalId, int] = {}
    for index, raw_id in enumerate(candidate_table):
        physical_id = validate_physical_id(raw_id, field="candidate-table physical ID")
        if physical_id in result:
            raise ValueError("duplicate candidate-table physical ID")
        result[physical_id] = index
    return result


def remap_physical_id(candidate_table: Sequence[object], physical_id: object) -> int:
    """Resolve a declared physical identity after a candidate-table rebuild."""

    target = validate_physical_id(physical_id, field="declared physical ID")
    mapping = unique_physical_id_map(candidate_table)
    if target not in mapping:
        raise ValueError("declared physical ID is not uniquely remappable")
    return mapping[target]


class CandidateForm(str, Enum):
    INCUMBENT_HOLD = "incumbent_hold"
    RELOCATION_HOLD = "relocation_plus_hold"


@dataclass(frozen=True)
class HoldInterval:
    physical_id: PhysicalId | None
    uniquely_remapped: bool = True
    action_valid: bool = True
    recurrence_power_w: float = 0.0
    canonical_link_ceiling_w: float = 1.0
    served: bool = True
    hidden_fallback: bool = False
    expired: bool = False


@dataclass(frozen=True)
class CandidateSequenceDecision:
    passed: bool
    form: CandidateForm | None
    declared_id: PhysicalId | None
    failed_offset: int | None
    reason: str | None


def validate_candidate_sequence(
    *,
    incumbent_id: object,
    declared_id: object,
    hold_intervals: Sequence[HoldInterval],
    release_action: PhysicalAction,
    release_from_main: bool,
    full_release_window: bool,
) -> CandidateSequenceDecision:
    """Validate the only two V3 candidate grammars and their hold conditions."""

    incumbent = validate_physical_id(incumbent_id, field="incumbent physical ID")
    declared = validate_physical_id(declared_id, field="declared physical ID")
    form = (
        CandidateForm.INCUMBENT_HOLD
        if declared == incumbent
        else CandidateForm.RELOCATION_HOLD
    )
    if len(hold_intervals) != HOLD_STEPS:
        return CandidateSequenceDecision(False, form, declared, None, "hold_window_incomplete")
    release_window_complete = _strict_bool(
        full_release_window, field="full-release-window flag"
    )
    released_by_main = _strict_bool(
        release_from_main, field="release-from-Main flag"
    )

    for offset, interval in enumerate(hold_intervals):
        if not isinstance(interval, HoldInterval):
            raise ValueError("hold intervals must be HoldInterval values")
        hidden_fallback = _strict_bool(
            interval.hidden_fallback, field="hidden-fallback flag"
        )
        expired = _strict_bool(interval.expired, field="expiry flag")
        uniquely_remapped = _strict_bool(
            interval.uniquely_remapped, field="unique-remapping flag"
        )
        action_valid = _strict_bool(interval.action_valid, field="action-valid flag")
        served = _strict_bool(interval.served, field="served flag")
        if hidden_fallback:
            return CandidateSequenceDecision(False, form, declared, offset, "hidden_fallback")
        if expired:
            return CandidateSequenceDecision(False, form, declared, offset, "early_expiry")
        if interval.physical_id is None:
            return CandidateSequenceDecision(False, form, declared, offset, "missing_physical_id")
        actual = validate_physical_id(interval.physical_id, field="hold physical ID")
        if actual != declared:
            return CandidateSequenceDecision(False, form, declared, offset, "second_relocation_or_redraw")
        if not uniquely_remapped:
            return CandidateSequenceDecision(False, form, declared, offset, "physical_id_not_unique")
        if not action_valid:
            return CandidateSequenceDecision(False, form, declared, offset, "action_invalid")
        if not math.isfinite(interval.recurrence_power_w):
            return CandidateSequenceDecision(False, form, declared, offset, "power_nonfinite")
        if (
            not math.isfinite(interval.canonical_link_ceiling_w)
            or interval.canonical_link_ceiling_w < 0.0
            or interval.recurrence_power_w < 0.0
            or interval.recurrence_power_w > interval.canonical_link_ceiling_w
        ):
            return CandidateSequenceDecision(False, form, declared, offset, "power_above_ceiling")
        if not served:
            return CandidateSequenceDecision(False, form, declared, offset, "focal_unserved")
    if not release_window_complete or not released_by_main:
        return CandidateSequenceDecision(False, form, declared, 3, "release_window_incomplete")
    if release_action is not None:
        validate_physical_id(release_action, field="release physical action")
    return CandidateSequenceDecision(True, form, declared, None, None)


def nonfocal_physical_identity(
    reference_by_offset: Sequence[Sequence[PhysicalAction]],
    candidate_by_offset: Sequence[Sequence[PhysicalAction]],
) -> bool:
    """Compare complete non-focal scripts by physical action, never table index."""

    if len(reference_by_offset) != 4 or len(candidate_by_offset) != 4:
        return False
    if any(len(left) != len(right) for left, right in zip(reference_by_offset, candidate_by_offset)):
        return False
    for left_row, right_row in zip(reference_by_offset, candidate_by_offset):
        for left, right in zip(left_row, right_row):
            left_id = None if left is None else validate_physical_id(left)
            right_id = None if right is None else validate_physical_id(right)
            if left_id != right_id:
                return False
    return True


@dataclass(frozen=True)
class ActivationPulseDecision:
    beam_pulses: frozenset[PhysicalId]
    satellite_pulses: frozenset[int]

    @property
    def any_pulse(self) -> bool:
        return bool(self.beam_pulses or self.satellite_pulses)


@dataclass(frozen=True)
class ActivationEnergyMechanismDecision:
    passed: bool
    beam_pulse: bool
    satellite_pulse: bool
    lower_complete_energy: bool


def _validated_active_sets(
    values: Sequence[Sequence[object]], *, field: str
) -> tuple[frozenset[PhysicalId], ...]:
    if len(values) != 5:
        raise ValueError(f"{field} must cover offsets -1 through 3")
    rows: list[frozenset[PhysicalId]] = []
    for raw_row in values:
        row = tuple(validate_physical_id(value, field=field) for value in raw_row)
        if len(set(row)) != len(row):
            raise ValueError(f"{field} contains a duplicate physical ID")
        rows.append(frozenset(row))
    return tuple(rows)


def _is_exact_pulse(reference_presence: Sequence[bool], candidate_presence: Sequence[bool]) -> bool:
    if len(reference_presence) != 5 or len(candidate_presence) != 5:
        return False
    if reference_presence[0] or reference_presence[4] or any(candidate_presence):
        return False
    hold = reference_presence[1:4]
    active = [index for index, present in enumerate(hold) if present]
    return bool(active) and active == list(range(active[0], active[-1] + 1))


def activation_pulses(
    reference_active_beams: Sequence[Sequence[object]],
    candidate_active_beams: Sequence[Sequence[object]],
) -> ActivationPulseDecision:
    """Find exact reference-only beam and satellite off-on-off pulses."""

    reference = _validated_active_sets(reference_active_beams, field="reference active beam")
    candidate = _validated_active_sets(candidate_active_beams, field="candidate active beam")
    all_beams = frozenset().union(*reference, *candidate)
    beam_pulses = frozenset(
        beam
        for beam in all_beams
        if _is_exact_pulse(
            [beam in row for row in reference], [beam in row for row in candidate]
        )
    )

    reference_satellites = tuple(frozenset(beam[0] for beam in row) for row in reference)
    candidate_satellites = tuple(frozenset(beam[0] for beam in row) for row in candidate)
    all_satellites = frozenset().union(*reference_satellites, *candidate_satellites)
    satellite_pulses = frozenset(
        satellite
        for satellite in all_satellites
        if _is_exact_pulse(
            [satellite in row for row in reference_satellites],
            [satellite in row for row in candidate_satellites],
        )
    )
    return ActivationPulseDecision(beam_pulses, satellite_pulses)


def evaluate_activation_energy_mechanism(
    pulses: ActivationPulseDecision,
    *,
    reference_complete_energy_j: float,
    candidate_complete_energy_j: float,
) -> ActivationEnergyMechanismDecision:
    """Apply the pulse-or-strictly-lower-complete-energy mechanism condition."""

    if (
        not math.isfinite(reference_complete_energy_j)
        or not math.isfinite(candidate_complete_energy_j)
        or reference_complete_energy_j <= 0.0
        or candidate_complete_energy_j <= 0.0
    ):
        raise ValueError("complete certificate energies must be finite and positive")
    lower_energy = reference_complete_energy_j > candidate_complete_energy_j
    beam_pulse = bool(pulses.beam_pulses)
    satellite_pulse = bool(pulses.satellite_pulses)
    return ActivationEnergyMechanismDecision(
        beam_pulse or satellite_pulse or lower_energy,
        beam_pulse,
        satellite_pulse,
        lower_energy,
    )


def _finite_nonnegative(value: float, *, field: str) -> float:
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{field} must be finite and nonnegative")
    return value


def _rel_close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=RELATIVE_IDENTITY_TOLERANCE, abs_tol=0.0)


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
    """Reconstruct identities from supplied canonical terms, not link physics."""

    reasons: list[str] = []
    circuit = _finite_nonnegative(
        terms.circuit_power_per_active_beam_w, field="circuit power"
    )
    baseband = _finite_nonnegative(
        terms.baseband_power_per_active_satellite_w, field="baseband power"
    )
    counts: dict[int, int] = {}
    for satellite, count in terms.active_beam_counts_by_satellite.items():
        if type(satellite) is not int or satellite < 0 or type(count) is not int or count < 0:
            raise ValueError("active-beam counts must map nonnegative integer IDs to counts")
        counts[satellite] = count

    seen: set[PhysicalId] = set()
    supply_total = 0.0
    actual_counts: dict[int, int] = {}
    for beam in terms.beams:
        beam_id = validate_physical_id(beam.beam_id, field="power beam physical ID")
        if beam_id in seen:
            raise ValueError("duplicate power beam physical ID")
        seen.add(beam_id)
        if not beam.recurrence_outputs_w:
            reasons.append(f"{beam_id}:missing_recurrence_output")
            recurrence_max = 0.0
        else:
            recurrence = tuple(
                _finite_nonnegative(value, field="recurrence output")
                for value in beam.recurrence_outputs_w
            )
            recurrence_max = max(recurrence)
        beam_max = _finite_nonnegative(beam.reported_beam_max_w, field="beam max power")
        efficiency = beam.reported_pa_efficiency
        if not math.isfinite(efficiency) or efficiency <= 0.0:
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
    reported_fixed = _finite_nonnegative(terms.reported_fixed_power_w, field="fixed power")
    reported_system = _finite_nonnegative(terms.reported_system_power_w, field="system power")
    if not _rel_close(reported_fixed, fixed):
        reasons.append("fixed_power_mismatch")
    if not _rel_close(reported_system, system):
        reasons.append("system_power_mismatch")
    return PowerIdentityDecision(not reasons, tuple(reasons), fixed, system)


@dataclass(frozen=True)
class ReleaseReport:
    reference_focal_r2: float
    candidate_focal_r2: float
    reference_system_r2: float
    candidate_system_r2: float


@dataclass(frozen=True)
class RewardServiceDecision:
    passed: bool
    reasons: tuple[str, ...]
    reference_hold_r2: float
    candidate_hold_r2: float
    reference_full_r2: float
    candidate_full_r2: float
    release: ReleaseReport


def evaluate_reward_release_service(
    *,
    reference_r2: Sequence[Sequence[float]],
    candidate_r2: Sequence[Sequence[float]],
    allowed_r2_values: Sequence[float],
    focal_user: int,
    reference_served: Sequence[Sequence[bool]],
    candidate_served: Sequence[Sequence[bool]],
    reference_reentry: Sequence[Sequence[bool]],
    candidate_reentry: Sequence[Sequence[bool]],
    release_report: ReleaseReport | None,
) -> RewardServiceDecision:
    """Apply system-total hold/release and service/re-entry guards."""

    matrices = (reference_r2, candidate_r2, reference_served, candidate_served,
                reference_reentry, candidate_reentry)
    if any(len(matrix) != 4 for matrix in matrices):
        raise ValueError("reward/service certificate must contain exactly four offsets")
    user_count = len(reference_r2[0])
    if user_count < 1 or type(focal_user) is not int or not 0 <= focal_user < user_count:
        raise ValueError("focal user must index a nonempty user matrix")
    if any(len(row) != user_count for matrix in matrices for row in matrix):
        raise ValueError("reward/service matrices must have identical complete user rows")
    allowed = frozenset(float(value) for value in allowed_r2_values)
    if not allowed or any(not math.isfinite(value) or value > 0.0 for value in allowed):
        raise ValueError("allowed canonical r2 values must be finite and nonpositive")
    for matrix in (reference_r2, candidate_r2):
        for row in matrix:
            for value in row:
                if not math.isfinite(value) or value not in allowed:
                    raise ValueError("r2 must be an allowed finite canonical value")
    for field, matrix in (
        ("reference served", reference_served),
        ("candidate served", candidate_served),
        ("reference re-entry", reference_reentry),
        ("candidate re-entry", candidate_reentry),
    ):
        for row in matrix:
            for value in row:
                _strict_bool(value, field=field)

    reference_hold = sum(sum(row) for row in reference_r2[:3])
    candidate_hold = sum(sum(row) for row in candidate_r2[:3])
    reference_full = reference_hold + sum(reference_r2[3])
    candidate_full = candidate_hold + sum(candidate_r2[3])
    actual_release = ReleaseReport(
        reference_focal_r2=reference_r2[3][focal_user],
        candidate_focal_r2=candidate_r2[3][focal_user],
        reference_system_r2=sum(reference_r2[3]),
        candidate_system_r2=sum(candidate_r2[3]),
    )
    reasons: list[str] = []
    if candidate_hold <= reference_hold:
        reasons.append("system_hold_r2_not_strictly_better")
    if candidate_full <= reference_full:
        reasons.append("system_full_r2_not_strictly_better")
    if release_report is None:
        reasons.append("release_event_omitted")
    elif release_report != actual_release:
        reasons.append("release_event_mismatch")

    for offset in CERTIFICATE_OFFSETS:
        if not reference_served[offset][focal_user] or not candidate_served[offset][focal_user]:
            reasons.append("focal_outage")
            break
    if any(reference_reentry[offset][focal_user] or candidate_reentry[offset][focal_user]
           for offset in CERTIFICATE_OFFSETS):
        reasons.append("focal_reentry")
    if any(
        reference_served[offset][user] and not candidate_served[offset][user]
        for offset in CERTIFICATE_OFFSETS
        for user in range(user_count)
    ):
        reasons.append("served_to_unserved")
    return RewardServiceDecision(
        not reasons,
        tuple(dict.fromkeys(reasons)),
        reference_hold,
        candidate_hold,
        reference_full,
        candidate_full,
        actual_release,
    )


@dataclass(frozen=True)
class BinaryProxyDecision:
    passed: bool
    reasons: tuple[str, ...]
    reference_useful_bits: float
    candidate_useful_bits: float
    reference_energy_j: float
    candidate_energy_j: float
    reference_ee_bits_per_j: float | None
    surplus_bits: float | None


def evaluate_binary_proxies(
    *, reference_useful_bits: float, candidate_useful_bits: float,
    reference_energy_j: float, candidate_energy_j: float,
) -> BinaryProxyDecision:
    """Evaluate exact useful-bits nonloss and strict EE-surplus inequalities."""

    values = (reference_useful_bits, candidate_useful_bits, reference_energy_j, candidate_energy_j)
    reasons: list[str] = []
    if any(not math.isfinite(value) for value in values):
        reasons.append("nonfinite_accumulation")
    if not reasons and (reference_useful_bits < 0.0 or candidate_useful_bits < 0.0):
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
    return BinaryProxyDecision(
        not reasons, tuple(reasons), reference_useful_bits, candidate_useful_bits,
        reference_energy_j, candidate_energy_j, eta, surplus,
    )


@dataclass(frozen=True)
class LayerEvidence:
    scheduled_anchor: bool
    qualifying_departure_anchor: bool
    unique_physical_candidate: bool
    hard_safe: bool
    nonfocal_identity: bool
    activation_or_energy: bool
    strict_system_r2: bool
    service_and_binary_proxies: bool


@dataclass(frozen=True)
class LayerDecision:
    passed_layers: tuple[str, ...]
    certified: bool
    first_failed_layer: str | None


_LAYER_FIELDS = (
    "scheduled_anchor", "qualifying_departure_anchor", "unique_physical_candidate",
    "hard_safe", "nonfocal_identity", "activation_or_energy", "strict_system_r2",
    "service_and_binary_proxies",
)


def evaluate_layers(evidence: LayerEvidence) -> LayerDecision:
    passed: list[str] = []
    for field in _LAYER_FIELDS:
        value = _strict_bool(getattr(evidence, field), field=f"{field} layer")
        if not value:
            return LayerDecision(tuple(passed), False, field)
        passed.append(field)
    passed.append("certified_choice")
    return LayerDecision(tuple(passed), True, None)


def certified_support(
    candidates: Mapping[PhysicalId, LayerEvidence],
) -> frozenset[PhysicalId]:
    """Return membership only; proxy magnitudes and input order are unavailable."""

    result: set[PhysicalId] = set()
    for raw_id, evidence in candidates.items():
        physical_id = validate_physical_id(raw_id)
        if evaluate_layers(evidence).certified:
            result.add(physical_id)
    return frozenset(result)


class ControlArm(str, Enum):
    PERSIST_RANDOM = "C2-PERSIST-R"
    STAY = "C2-STAY"
    CHURN_CERT_RANDOM = "C2-CHURN-CERT-R"
    LEARNED = "C2-I"


def control_support(
    arm: ControlArm,
    *,
    hard_safe_support: Sequence[PhysicalId],
    certified_choice_support: Sequence[PhysicalId],
    incumbent_id: PhysicalId,
) -> frozenset[PhysicalId]:
    """Expose the declared support for a control without ranking its members."""

    hard_safe = frozenset(validate_physical_id(value) for value in hard_safe_support)
    certified = frozenset(validate_physical_id(value) for value in certified_choice_support)
    incumbent = validate_physical_id(incumbent_id)
    if not certified <= hard_safe:
        raise ValueError("certified support must be nested inside hard-safe support")
    if arm is ControlArm.PERSIST_RANDOM:
        return hard_safe
    if arm is ControlArm.STAY:
        return frozenset({incumbent}) if incumbent in hard_safe else frozenset()
    if arm is ControlArm.CHURN_CERT_RANDOM:
        return certified
    if arm is ControlArm.LEARNED:
        raise ValueError("C2-I is absent from Stage-0")
    raise ValueError("unknown C2 control arm")


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
    """Aggregate the five-partition/two-choice floor without imputing rows."""

    if (
        type(minimum_pooled_two_choice_anchors) is not int
        or minimum_pooled_two_choice_anchors < 1
    ):
        raise ValueError("minimum pooled two-choice anchors must be a positive integer")
    if set(scheduled_anchor_ids_by_partition) != set(range(5)):
        raise ValueError("support floor requires exactly partitions 0 through 4")
    expected = {
        (partition, anchor_id)
        for partition, anchor_ids in scheduled_anchor_ids_by_partition.items()
        for anchor_id in anchor_ids
    }
    if len(expected) != sum(len(ids) for ids in scheduled_anchor_ids_by_partition.values()):
        raise ValueError("scheduled anchor IDs must be unique within their partition")
    observed: dict[tuple[int, str], AnchorSupportRow] = {}
    for row in rows:
        if type(row.partition) is not int or row.partition not in range(5):
            raise ValueError("support-row partition must be an integer from 0 through 4")
        if type(row.anchor_id) is not str or not row.anchor_id:
            raise ValueError("support-row anchor ID must be a nonempty string")
        key = (row.partition, row.anchor_id)
        if key in observed:
            raise ValueError("duplicate support row")
        for physical_id in row.certified_choices:
            validate_physical_id(physical_id, field="certified choice physical ID")
        observed[key] = row
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
    passed = (
        all(count >= 1 for count in counts.values())
        and pooled >= minimum_pooled_two_choice_anchors
    )
    return SupportFloorDecision(passed, counts, pooled)
