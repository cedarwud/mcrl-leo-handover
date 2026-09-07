"""Fail-closed pure core for the C2 V0.3 temporal-fork candidate.

The frozen V0.2 runner does not import this module.  A future adapter must
produce hash-bound pre-outcome forecast evidence and committed transition
receipts.  This core then owns the EE-safe fork rule and complete
hold-plus-release option closure behind two public calls:

``certify_temporal_fork`` and ``close_temporal_option``.

The private C2 learner may consume the option-level SMDP return.  Main retains
primitive physical-action semantics and may consume only the receipted
one-step canonical-r2 sequence, targeted to objective index 1.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from enum import Enum
from typing import Sequence


PUBLIC_METHOD_NAME = "Multi-Catfish MCRL"
# V0.3B is the prospective post-gate source-policy amendment.  Keeping a
# distinct version is important: certificates/replay rows produced by the
# fixed-hold V0.3A policy must not silently enter a hold-while-legal run.
CANDIDATE_VERSION = "C2_V0.3B_HOLD_WHILE_LEGAL_MONOTONE_RELEASE"
FORECAST_AUTHORITY_SCHEMA = "c2-v03-domain-separated-forecast-authority-v5"
FORECAST_NAMESPACE_PREFIX = "c2-v03/"
FADING_MODE_DISABLED = "disabled"
FADING_MODE_KEYED = "keyed-branch-independent-v1"
FORECAST_FADING_MODES = frozenset((FADING_MODE_DISABLED, FADING_MODE_KEYED))
C2_OBJECTIVE_INDEX = 1
CANONICAL_R2_VALUES = (0.0, -0.5, -1.0)
ACTION_DIM = 28
HOLD_STEPS = 3
# ``HOLD_STEPS`` remains the public maximum downstream offset for compatibility.
# A V0.3B certificate may release earlier; its ``hold_steps`` is the release
# offset, while ``horizon_steps`` remains this maximum offset.
HORIZON_STEPS = HOLD_STEPS
RELEASE_REASONS = frozenset(("horizon", "support_expired"))
# Frozen certificate floors.  One useful bit is the smallest meaningful
# accumulated service quantum in this model.  The relative surplus floor is
# derived only from float64 precision, never from C2 support or outcomes.
MIN_REFERENCE_USEFUL_BITS = 1.0
MIN_EE_SURPLUS_FRACTION = math.sqrt(2.220446049250313e-16)
EE_SURPLUS_ULP_MULTIPLIER = 64.0
CHRONOLOGY_RECEIPT_SCHEMA = "c2-v03-preoutcome-chronology-receipt-v2"
CHRONOLOGY_SEQUENCE = (
    "anchor_captured",
    "detached_forecast_started",
    "detached_forecast_completed",
    "live_rng_nonadvancement_verified",
    "live_step_started",
    "live_step_completed",
)


PhysicalKey = tuple[int, int]
RewardRow = tuple[float, float, float]


class C2ContractError(ValueError):
    """The caller supplied malformed or scientifically inadmissible evidence."""


class C2LeakageError(C2ContractError):
    """Forecast provenance does not isolate the decision from the live future."""


class ForkFailure(str, Enum):
    """Semantic reasons that a well-formed alternative receives zero dose."""

    STRUCTURAL = "forecast_branch_structural_failure"
    NONFOCAL_POLICY_ALIGNMENT = "nonfocal_policy_alignment_failed"
    FOCAL_SERVICE = "focal_service_failed"
    NONFOCAL_OUTAGE = "new_nonfocal_outage"
    RELEASE = "first_release_missing"
    RESOURCE_PATH = "activation_or_complete_energy_path_failed"
    REFERENCE_BITS = "reference_useful_bits_below_frozen_floor"
    USEFUL_BITS = "useful_bits_loss"
    ENERGY_REGRESSION = "candidate_energy_exceeds_reference"
    EE_SURPLUS = "ee_surplus_not_above_frozen_robustness_floor"
    DIRECT_R2 = "canonical_r2_not_strictly_improved"


@dataclass(frozen=True)
class ForecastAuthority:
    """Hash-bound provenance for a domain-separated matched forecast."""

    schema: str
    anchor_sha256: str
    reference_checkpoint_sha256: str
    environment_source_sha256: str
    reward_source_sha256: str
    live_rng_state_sha256: str
    forecast_rng_state_sha256: str
    forecast_request_sha256: str
    forecast_payload_sha256: str
    forecast_namespace: str
    fading_mode: str
    generated_preoutcome: bool
    adapter_version: str


@dataclass(frozen=True)
class ActionBinding:
    """One valid focal action and its physical identity in one slot table."""

    action: int
    physical_key: PhysicalKey


@dataclass(frozen=True)
class TemporalForkEvidence:
    """Pre-outcome full-window evidence for one alternative versus Main."""

    authority: ForecastAuthority
    focal_user: int
    user_count: int
    reference_action: int
    candidate_action: int
    reference_key: PhysicalKey
    candidate_key: PhysicalKey
    opening_action_bindings: tuple[ActionBinding, ...]
    opening_action_table_sha256: str
    opening_state_sha256: str
    opening_mask_sha256: str
    reference_branch_trace_sha256: str
    candidate_branch_trace_sha256: str
    hold_steps: int
    release_observed: bool
    branch_structurally_valid: bool
    nonfocal_policy_aligned: bool
    focal_served_all_steps: bool
    no_new_nonfocal_outage: bool
    activation_or_energy_path: bool
    reference_useful_bits: float
    candidate_useful_bits: float
    reference_energy_j: float
    candidate_energy_j: float
    forecast_hold_r2_margin: float
    forecast_full_r2_margin: float
    # The old ``hold_steps`` field is retained as the release offset for
    # callers that already consume it.  These explicit fields make the
    # prospective policy auditable and distinguish a support-triggered
    # release from the planned horizon release.
    release_offset: int = HOLD_STEPS
    release_reason: str = "horizon"
    horizon_steps: int = HORIZON_STEPS


@dataclass(frozen=True)
class TemporalForkCertificate:
    """Fail-closed result exposed to action selection and option closure."""

    version: str
    option_id: str
    evidence_sha256: str
    anchor_sha256: str
    reward_source_sha256: str
    forecast_payload_sha256: str
    focal_user: int
    user_count: int
    reference_action: int
    candidate_action: int
    reference_key: PhysicalKey
    candidate_key: PhysicalKey
    opening_action_table_sha256: str
    opening_state_sha256: str
    opening_mask_sha256: str
    reference_branch_trace_sha256: str
    candidate_branch_trace_sha256: str
    hold_steps: int
    support_actions: tuple[int, ...]
    passed: bool
    failures: tuple[ForkFailure, ...]
    reference_ee_bits_per_j: float
    ee_surplus_bits: float
    ee_surplus_floor_bits: float
    hold_r2_margin: float
    full_r2_margin: float
    release_offset: int = HOLD_STEPS
    release_reason: str = "horizon"
    horizon_steps: int = HORIZON_STEPS


@dataclass(frozen=True)
class ExecutedOptionStep:
    """One immutable focal transition receipt from the committed C2 branch."""

    option_id: str
    anchor_sha256: str
    source_id: str
    bundle_id: str
    behavior_probability: float
    focal_user: int
    offset: int
    phase: str
    action: int
    physical_key: PhysicalKey
    detached_main_action: int
    detached_main_key: PhysicalKey
    executed_joint_physical_actions: tuple[PhysicalKey | None, ...]
    executed_joint_physical_sha256: str
    detached_main_joint_physical_actions: tuple[PhysicalKey | None, ...]
    detached_main_joint_physical_sha256: str
    action_bindings: tuple[ActionBinding, ...]
    action_table_sha256: str
    reward_matrix: tuple[RewardRow, ...]
    reward_matrix_sha256: str
    reward_source_sha256: str
    focal_served: bool
    served: tuple[bool, ...]
    state_sha256: str
    state_mask_sha256: str
    next_state_sha256: str
    next_mask_sha256: str
    done: bool = False
    # V0.3B policy receipts.  Defaults preserve construction of legacy test
    # fixtures, but newly generated rows always populate all four fields.
    held_physical_key: PhysicalKey | None = None
    held_key_match_count: int | None = None
    release_offset: int | None = None
    release_reason: str | None = None


@dataclass(frozen=True)
class C2ClosedOptionPlan:
    """Private option metadata plus primitive Main-Q2 sequence authority."""

    version: str
    option_id: str
    anchor_sha256: str
    objective_index: int
    focal_user: int
    action: int
    discount_factor: float
    specialist_target_enabled: bool
    specialist_option_return: float | None
    specialist_bootstrap_discount: float | None
    specialist_target_mode: str
    main_sequence_enabled: bool
    main_target_mode: str
    main_source_unit_id: str | None
    chronology_receipt_sha256: str | None
    observed_bundle_ids: tuple[str, ...]
    main_bundle_ids: tuple[str, ...]
    main_focal_actions: tuple[int, ...]
    main_behavior_probabilities: tuple[float, ...]
    main_reward_matrix_sha256: tuple[str, ...]
    main_r2_column_sha256: tuple[str, ...]
    opening_state_sha256: str | None
    bootstrap_state_sha256: str | None
    bootstrap_mask_sha256: str | None
    executed_steps: int
    planned_steps: int
    complete_hold_and_release: bool
    realised_focal_service_all: bool | None
    realised_served_by_step: tuple[tuple[bool, ...], ...]
    environment_terminal: bool
    admitted: bool
    disposition: str
    release_offset: int = HOLD_STEPS
    release_reason: str = "horizon"
    horizon_steps: int = HORIZON_STEPS


def _finite_number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise C2ContractError(f"{field} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted):
        raise C2ContractError(f"{field} must be finite")
    return converted


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise C2ContractError(f"{field} must be a nonnegative exact integer")
    return int(value)


def _physical_key(value: object, *, field: str) -> PhysicalKey:
    if not isinstance(value, tuple) or len(value) != 2:
        raise C2ContractError(f"{field} must be a two-integer physical key")
    norad = _exact_nonnegative_int(value[0], field=f"{field}.norad")
    cell = _exact_nonnegative_int(value[1], field=f"{field}.cell")
    return (norad, cell)


def _sha256(value: object, *, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise C2ContractError(f"{field} must be a 64-character SHA-256")
    if value != value.lower() or any(char not in "0123456789abcdef" for char in value):
        raise C2ContractError(f"{field} must be lowercase hexadecimal SHA-256")
    return value


def _nonempty_string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise C2ContractError(f"{field} must be a nonempty string")
    return value


def _json_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _float_hex(value: float) -> str:
    """Return an exact, platform-stable representation of a finite float."""

    return float(value).hex()


def _validate_joint_physical_actions(
    values: Sequence[PhysicalKey | None], *, user_count: int, field: str
) -> tuple[PhysicalKey | None, ...]:
    if isinstance(values, (str, bytes)):
        raise C2ContractError(f"{field} must be a per-user physical-action sequence")
    rows = tuple(values)
    if len(rows) != user_count:
        raise C2ContractError(f"{field} has the wrong user count")
    normalized: list[PhysicalKey | None] = []
    for user, value in enumerate(rows):
        normalized.append(
            None
            if value is None
            else _physical_key(value, field=f"{field}[{user}]")
        )
    return tuple(normalized)


def joint_physical_actions_sha256(
    values: Sequence[PhysicalKey | None], *, user_count: int
) -> str:
    """Hash a complete ordered per-user physical-action vector."""

    normalized = _validate_joint_physical_actions(
        values, user_count=user_count, field="joint_physical_actions"
    )
    return _json_sha256(
        [None if value is None else [value[0], value[1]] for value in normalized]
    )


def action_table_sha256(bindings: Sequence[ActionBinding]) -> str:
    """Return the canonical digest for an ordered focal action table."""

    normalized = _validate_action_bindings(bindings, field="action_bindings")
    return _json_sha256(
        [[row.action, row.physical_key[0], row.physical_key[1]] for row in normalized]
    )


def r2_column_sha256(values: Sequence[float]) -> str:
    """Return the canonical digest for an unchanged canonical-r2 column."""

    normalized = _validate_r2_column(values, field="r2_column")
    return _json_sha256(list(normalized))


def reward_matrix_sha256(values: Sequence[Sequence[float]]) -> str:
    """Return the canonical digest for a complete unchanged reward matrix."""

    normalized = _validate_reward_matrix(values, field="reward_matrix")
    return _json_sha256([list(row) for row in normalized])


def _validate_action_bindings(
    bindings: Sequence[ActionBinding], *, field: str
) -> tuple[ActionBinding, ...]:
    if isinstance(bindings, (str, bytes)):
        raise C2ContractError(f"{field} must be a sequence of ActionBinding")
    rows = tuple(bindings)
    if not rows:
        raise C2ContractError(f"{field} must not be empty")
    normalized: list[ActionBinding] = []
    for index, row in enumerate(rows):
        if not isinstance(row, ActionBinding):
            raise C2ContractError(f"{field}[{index}] must be ActionBinding")
        action = _exact_nonnegative_int(row.action, field=f"{field}[{index}].action")
        if action >= ACTION_DIM:
            raise C2ContractError(
                f"{field}[{index}].action must lie in [0, {ACTION_DIM})"
            )
        key = _physical_key(row.physical_key, field=f"{field}[{index}].physical_key")
        normalized.append(ActionBinding(action, key))
    actions = tuple(row.action for row in normalized)
    keys = tuple(row.physical_key for row in normalized)
    if actions != tuple(sorted(actions)) or len(set(actions)) != len(actions):
        raise C2ContractError(f"{field} actions must be strictly increasing")
    if len(set(keys)) != len(keys):
        raise C2ContractError(f"{field} cannot repeat a physical key")
    return tuple(normalized)


def _binding_key(
    bindings: Sequence[ActionBinding], action: int, *, field: str
) -> PhysicalKey:
    rows = _validate_action_bindings(bindings, field=field)
    matches = [row.physical_key for row in rows if row.action == action]
    if len(matches) != 1:
        raise C2ContractError(f"{field} does not bind action {action} exactly once")
    return matches[0]


def _validate_r2_column(values: Sequence[float], *, field: str) -> tuple[float, ...]:
    if isinstance(values, (str, bytes)):
        raise C2ContractError(f"{field} must be a reward sequence")
    rows = tuple(_finite_number(value, field=f"{field}[{index}]") for index, value in enumerate(values))
    if not rows:
        raise C2ContractError(f"{field} must not be empty")
    if any(value not in CANONICAL_R2_VALUES for value in rows):
        raise C2ContractError(
            f"{field} must contain only unchanged canonical r2 values "
            f"{CANONICAL_R2_VALUES}"
        )
    return rows


def _validate_reward_matrix(
    values: Sequence[Sequence[float]], *, field: str
) -> tuple[RewardRow, ...]:
    if isinstance(values, (str, bytes)):
        raise C2ContractError(f"{field} must be a U-by-3 reward matrix")
    rows: list[RewardRow] = []
    for user, raw_row in enumerate(values):
        if isinstance(raw_row, (str, bytes)):
            raise C2ContractError(f"{field}[{user}] must contain three objectives")
        raw_tuple = tuple(raw_row)
        if len(raw_tuple) != 3:
            raise C2ContractError(f"{field}[{user}] must contain three objectives")
        row = tuple(
            _finite_number(value, field=f"{field}[{user}][{objective}]")
            for objective, value in enumerate(raw_tuple)
        )
        rows.append((row[0], row[1], row[2]))
    if not rows:
        raise C2ContractError(f"{field} must not be empty")
    _validate_r2_column(
        tuple(row[C2_OBJECTIVE_INDEX] for row in rows), field=f"{field}.r2"
    )
    return tuple(rows)


def _validate_forecast_authority(authority: ForecastAuthority) -> ForecastAuthority:
    if not isinstance(authority, ForecastAuthority):
        raise C2ContractError("authority must be ForecastAuthority")
    if authority.schema != FORECAST_AUTHORITY_SCHEMA:
        raise C2ContractError("forecast authority schema drifted")
    for field in (
        "anchor_sha256",
        "reference_checkpoint_sha256",
        "environment_source_sha256",
        "reward_source_sha256",
        "live_rng_state_sha256",
        "forecast_rng_state_sha256",
        "forecast_request_sha256",
        "forecast_payload_sha256",
    ):
        _sha256(getattr(authority, field), field=f"authority.{field}")
    if authority.live_rng_state_sha256 == authority.forecast_rng_state_sha256:
        raise C2LeakageError("forecast RNG state aliases the live future RNG state")
    namespace = _nonempty_string(
        authority.forecast_namespace, field="authority.forecast_namespace"
    )
    if not namespace.startswith(FORECAST_NAMESPACE_PREFIX):
        raise C2LeakageError("forecast namespace is outside the C2 V0.3 domain")
    if authority.fading_mode not in FORECAST_FADING_MODES:
        raise C2LeakageError(
            "C2 V0.3 forecast fading_mode must be disabled or "
            "keyed-branch-independent-v1"
        )
    if type(authority.generated_preoutcome) is not bool:
        raise C2ContractError("authority.generated_preoutcome must be Boolean")
    if not authority.generated_preoutcome:
        raise C2LeakageError("forecast receipt was not generated pre-outcome")
    _nonempty_string(authority.adapter_version, field="authority.adapter_version")
    return authority


def _safe_ee_terms(
    *,
    reference_bits: float,
    candidate_bits: float,
    reference_energy: float,
    candidate_energy: float,
) -> tuple[float, float]:
    """Compute reference EE and surplus without NaN/overflow pass-through."""

    try:
        with localcontext() as context:
            context.prec = 80
            b_m = Decimal(str(reference_bits))
            b_f = Decimal(str(candidate_bits))
            e_m = Decimal(str(reference_energy))
            e_f = Decimal(str(candidate_energy))
            eta_m = b_m / e_m
            surplus = (b_f - b_m) - eta_m * (e_f - e_m)
        reference_ee = float(eta_m)
        surplus_bits = float(surplus)
    except (InvalidOperation, OverflowError, ZeroDivisionError) as error:
        raise C2ContractError("EE forecast arithmetic is not representable") from error
    if not math.isfinite(reference_ee) or not math.isfinite(surplus_bits):
        raise C2ContractError("EE forecast arithmetic must remain finite")
    return reference_ee, surplus_bits


def _release_policy(
    *,
    release_offset: object,
    release_reason: object,
    horizon_steps: object,
    field_prefix: str,
) -> tuple[int, str, int]:
    """Validate the sealed hold-while-legal release metadata.

    Offsets are decision intervals, so offset zero is the opening candidate
    itself and cannot be a release.  ``horizon`` is only valid at the final
    planned offset; an earlier release must be explicitly marked
    ``support_expired``.  This helper is shared by certificate and execution
    validation so old/falsely-labelled rows fail closed at both boundaries.
    """

    horizon = _exact_nonnegative_int(horizon_steps, field=f"{field_prefix}.horizon_steps")
    if horizon != HORIZON_STEPS:
        raise C2ContractError(
            f"{field_prefix}.horizon_steps must equal the frozen horizon H={HORIZON_STEPS}"
        )
    offset = _exact_nonnegative_int(
        release_offset, field=f"{field_prefix}.release_offset"
    )
    if not 1 <= offset <= horizon:
        raise C2ContractError(
            f"{field_prefix}.release_offset must lie in [1,{horizon}]"
        )
    if not isinstance(release_reason, str) or release_reason not in RELEASE_REASONS:
        raise C2ContractError(
            f"{field_prefix}.release_reason must be one of {sorted(RELEASE_REASONS)}"
        )
    if release_reason == "horizon" and offset != horizon:
        raise C2ContractError(
            f"{field_prefix}.horizon release must occur at offset {horizon}"
        )
    return offset, release_reason, horizon


def _step_release_policy(
    step: ExecutedOptionStep,
    *,
    certificate: TemporalForkCertificate,
) -> tuple[int, str, int]:
    """Return one row's policy metadata, with a compatibility fallback.

    Pre-V0.3B hand-built fixtures did not carry row-level release metadata.
    They are interpreted as the old planned-horizon sequence only so tests can
    still exercise unrelated core validation.  Any partially supplied V0.3B
    metadata is rejected instead of being silently completed.
    """

    supplied = (step.release_offset, step.release_reason)
    if all(value is None for value in supplied):
        return _release_policy(
            release_offset=certificate.release_offset,
            release_reason=certificate.release_reason,
            horizon_steps=certificate.horizon_steps,
            field_prefix="certificate",
        )
    if step.release_offset is None or step.release_reason is None:
        raise C2ContractError(
            "executed V0.3B row must bind release_offset and release_reason together"
        )
    return _release_policy(
        release_offset=step.release_offset,
        release_reason=step.release_reason,
        horizon_steps=certificate.horizon_steps,
        field_prefix="step",
    )


def certify_temporal_fork(
    evidence: TemporalForkEvidence,
) -> TemporalForkCertificate:
    """Certify a binary Main/temporal fork without ranking by EE magnitude."""

    if not isinstance(evidence, TemporalForkEvidence):
        raise C2ContractError("evidence must be TemporalForkEvidence")
    authority = _validate_forecast_authority(evidence.authority)
    focal_user = _exact_nonnegative_int(evidence.focal_user, field="focal_user")
    user_count = _exact_nonnegative_int(evidence.user_count, field="user_count")
    if user_count == 0 or focal_user >= user_count:
        raise C2ContractError("focal_user must be inside a positive user_count")
    reference_action = _exact_nonnegative_int(
        evidence.reference_action, field="reference_action"
    )
    candidate_action = _exact_nonnegative_int(
        evidence.candidate_action, field="candidate_action"
    )
    reference_key = _physical_key(evidence.reference_key, field="reference_key")
    candidate_key = _physical_key(evidence.candidate_key, field="candidate_key")
    if reference_action == candidate_action or reference_key == candidate_key:
        raise C2ContractError("a temporal fork requires two distinct physical actions")

    bindings = _validate_action_bindings(
        evidence.opening_action_bindings, field="opening_action_bindings"
    )
    table_digest = action_table_sha256(bindings)
    if _sha256(
        evidence.opening_action_table_sha256,
        field="opening_action_table_sha256",
    ) != table_digest:
        raise C2ContractError("opening action-table SHA-256 does not match bindings")
    if _binding_key(bindings, reference_action, field="opening_action_bindings") != reference_key:
        raise C2ContractError("reference action does not map to reference physical key")
    if _binding_key(bindings, candidate_action, field="opening_action_bindings") != candidate_key:
        raise C2ContractError("candidate action does not map to candidate physical key")

    hold_steps = _exact_nonnegative_int(evidence.hold_steps, field="hold_steps")
    release_offset, release_reason, horizon_steps = _release_policy(
        release_offset=evidence.release_offset,
        release_reason=evidence.release_reason,
        horizon_steps=evidence.horizon_steps,
        field_prefix="evidence",
    )
    # ``hold_steps`` is the compatibility spelling for the release offset.
    if hold_steps != release_offset:
        raise C2ContractError("evidence hold_steps disagrees with release_offset")
    opening_state_sha256 = _sha256(
        evidence.opening_state_sha256, field="opening_state_sha256"
    )
    opening_mask_sha256 = _sha256(
        evidence.opening_mask_sha256, field="opening_mask_sha256"
    )
    reference_trace_sha256 = _sha256(
        evidence.reference_branch_trace_sha256,
        field="reference_branch_trace_sha256",
    )
    candidate_trace_sha256 = _sha256(
        evidence.candidate_branch_trace_sha256,
        field="candidate_branch_trace_sha256",
    )
    if reference_trace_sha256 == candidate_trace_sha256:
        raise C2ContractError("reference and candidate branch traces must be distinct")
    for field in (
        "release_observed",
        "branch_structurally_valid",
        "nonfocal_policy_aligned",
        "focal_served_all_steps",
        "no_new_nonfocal_outage",
        "activation_or_energy_path",
    ):
        if type(getattr(evidence, field)) is not bool:
            raise C2ContractError(f"{field} must be Boolean")

    reference_bits = _finite_number(
        evidence.reference_useful_bits, field="reference_useful_bits"
    )
    candidate_bits = _finite_number(
        evidence.candidate_useful_bits, field="candidate_useful_bits"
    )
    reference_energy = _finite_number(
        evidence.reference_energy_j, field="reference_energy_j"
    )
    candidate_energy = _finite_number(
        evidence.candidate_energy_j, field="candidate_energy_j"
    )
    hold_r2_margin = _finite_number(
        evidence.forecast_hold_r2_margin, field="forecast_hold_r2_margin"
    )
    full_r2_margin = _finite_number(
        evidence.forecast_full_r2_margin, field="forecast_full_r2_margin"
    )
    if reference_bits < 0.0 or candidate_bits < 0.0:
        raise C2ContractError("useful bits must be nonnegative")
    if reference_energy <= 0.0 or candidate_energy <= 0.0:
        raise C2ContractError("forecast energy must be strictly positive")
    reference_ee, surplus = _safe_ee_terms(
        reference_bits=reference_bits,
        candidate_bits=candidate_bits,
        reference_energy=reference_energy,
        candidate_energy=candidate_energy,
    )
    numerical_surplus_floor = EE_SURPLUS_ULP_MULTIPLIER * math.ulp(
        max(
            reference_bits,
            candidate_bits,
            abs(reference_ee * (candidate_energy - reference_energy)),
            1.0,
        )
    )
    surplus_floor = max(
        MIN_EE_SURPLUS_FRACTION * reference_bits,
        numerical_surplus_floor,
    )

    failures: list[ForkFailure] = []
    if not evidence.branch_structurally_valid:
        failures.append(ForkFailure.STRUCTURAL)
    if not evidence.nonfocal_policy_aligned:
        failures.append(ForkFailure.NONFOCAL_POLICY_ALIGNMENT)
    if not evidence.focal_served_all_steps:
        failures.append(ForkFailure.FOCAL_SERVICE)
    if not evidence.no_new_nonfocal_outage:
        failures.append(ForkFailure.NONFOCAL_OUTAGE)
    if not evidence.release_observed:
        failures.append(ForkFailure.RELEASE)
    # ``activation_or_energy_path`` remains hash-bound diagnostic evidence,
    # not an admission gate.  With B_F >= B_M and a robustly positive EE
    # surplus, a throughput-dominant option may legitimately consume slightly
    # more energy while improving bits/J.  Requiring an activation pulse or a
    # componentwise energy reduction would reject that valid Pareto tradeoff.
    if reference_bits < MIN_REFERENCE_USEFUL_BITS:
        failures.append(ForkFailure.REFERENCE_BITS)
    if candidate_bits < reference_bits:
        failures.append(ForkFailure.USEFUL_BITS)
    if surplus <= surplus_floor:
        failures.append(ForkFailure.EE_SURPLUS)
    if hold_r2_margin <= 0.0 or full_r2_margin <= 0.0:
        failures.append(ForkFailure.DIRECT_R2)

    evidence_sha256 = _json_sha256(
        {
            "version": CANDIDATE_VERSION,
            "authority": {
                "schema": authority.schema,
                "anchor": authority.anchor_sha256,
                "reference_checkpoint": authority.reference_checkpoint_sha256,
                "environment_source": authority.environment_source_sha256,
                "reward_source": authority.reward_source_sha256,
                "live_rng_state": authority.live_rng_state_sha256,
                "forecast_rng_state": authority.forecast_rng_state_sha256,
                "forecast_request": authority.forecast_request_sha256,
                "forecast_payload": authority.forecast_payload_sha256,
                "forecast_namespace": authority.forecast_namespace,
                "fading_mode": authority.fading_mode,
                "generated_preoutcome": authority.generated_preoutcome,
                "adapter_version": authority.adapter_version,
            },
            "focal_user": focal_user,
            "user_count": user_count,
            "reference_action": reference_action,
            "candidate_action": candidate_action,
            "reference_key": list(reference_key),
            "candidate_key": list(candidate_key),
            "opening_action_table": table_digest,
            "opening_state": opening_state_sha256,
            "opening_mask": opening_mask_sha256,
            "reference_branch_trace": reference_trace_sha256,
            "candidate_branch_trace": candidate_trace_sha256,
            "hold_steps": hold_steps,
            "release_offset": release_offset,
            "release_reason": release_reason,
            "horizon_steps": horizon_steps,
            "flags": {
                "release_observed": evidence.release_observed,
                "branch_structurally_valid": evidence.branch_structurally_valid,
                "nonfocal_policy_aligned": evidence.nonfocal_policy_aligned,
                "focal_served_all_steps": evidence.focal_served_all_steps,
                "no_new_nonfocal_outage": evidence.no_new_nonfocal_outage,
                "activation_or_energy_path": evidence.activation_or_energy_path,
            },
            "metrics_hex": {
                "reference_useful_bits": _float_hex(reference_bits),
                "candidate_useful_bits": _float_hex(candidate_bits),
                "reference_energy_j": _float_hex(reference_energy),
                "candidate_energy_j": _float_hex(candidate_energy),
                "forecast_hold_r2_margin": _float_hex(hold_r2_margin),
                "forecast_full_r2_margin": _float_hex(full_r2_margin),
            },
            "frozen_certificate_floors_hex": {
                "min_reference_useful_bits": _float_hex(
                    MIN_REFERENCE_USEFUL_BITS
                ),
                "min_ee_surplus_fraction": _float_hex(
                    MIN_EE_SURPLUS_FRACTION
                ),
                "ee_surplus_ulp_multiplier": _float_hex(
                    EE_SURPLUS_ULP_MULTIPLIER
                ),
                "effective_ee_surplus_floor_bits": _float_hex(surplus_floor),
            },
        }
    )
    option_id = _json_sha256(
        {"version": CANDIDATE_VERSION, "evidence_sha256": evidence_sha256}
    )
    passed = not failures
    return TemporalForkCertificate(
        version=CANDIDATE_VERSION,
        option_id=option_id,
        evidence_sha256=evidence_sha256,
        anchor_sha256=authority.anchor_sha256,
        reward_source_sha256=authority.reward_source_sha256,
        forecast_payload_sha256=authority.forecast_payload_sha256,
        focal_user=focal_user,
        user_count=user_count,
        reference_action=reference_action,
        candidate_action=candidate_action,
        reference_key=reference_key,
        candidate_key=candidate_key,
        opening_action_table_sha256=table_digest,
        opening_state_sha256=opening_state_sha256,
        opening_mask_sha256=opening_mask_sha256,
        reference_branch_trace_sha256=reference_trace_sha256,
        candidate_branch_trace_sha256=candidate_trace_sha256,
        hold_steps=hold_steps,
        support_actions=(
            (reference_action, candidate_action) if passed else (reference_action,)
        ),
        passed=passed,
        failures=tuple(failures),
        reference_ee_bits_per_j=reference_ee,
        ee_surplus_bits=surplus,
        ee_surplus_floor_bits=surplus_floor,
        hold_r2_margin=hold_r2_margin,
        full_r2_margin=full_r2_margin,
        release_offset=release_offset,
        release_reason=release_reason,
        horizon_steps=horizon_steps,
    )


def _validate_executed_step(
    step: ExecutedOptionStep,
    *,
    certificate: TemporalForkCertificate,
    expected_offset: int,
) -> tuple[float, tuple[bool, ...]]:
    if not isinstance(step, ExecutedOptionStep):
        raise C2ContractError("every executed item must be ExecutedOptionStep")
    if step.option_id != certificate.option_id:
        raise C2ContractError("executed step belongs to a different option")
    if _sha256(step.anchor_sha256, field="step.anchor_sha256") != certificate.anchor_sha256:
        raise C2ContractError("executed step belongs to a different anchor")
    if step.source_id != "C2":
        raise C2ContractError("executed option step source must be C2")
    _nonempty_string(step.bundle_id, field="step.bundle_id")
    behavior_probability = _finite_number(
        step.behavior_probability, field="step.behavior_probability"
    )
    if not 0.0 < behavior_probability <= 1.0:
        raise C2ContractError("executed behavior probability must lie in (0,1]")
    if expected_offset > 0 and behavior_probability != 1.0:
        raise C2ContractError(
            "continuation and release behavior probability must equal one"
        )
    if step.focal_user != certificate.focal_user:
        raise C2ContractError("executed step focal user drifted")
    if _exact_nonnegative_int(step.offset, field="step.offset") != expected_offset:
        raise C2ContractError("executed option offsets must be contiguous from zero")
    release_offset, release_reason, horizon_steps = _step_release_policy(
        step, certificate=certificate
    )
    expected_phase = "hold" if expected_offset < release_offset else "release"
    if step.phase != expected_phase:
        raise C2ContractError("executed option phase disagrees with its release offset")
    if step.held_physical_key is not None:
        held_key = _physical_key(
            step.held_physical_key, field="step.held_physical_key"
        )
        if held_key != certificate.candidate_key:
            raise C2ContractError(
                "executed held physical key differs from certified candidate"
            )
    if step.held_key_match_count is not None:
        match_count = _exact_nonnegative_int(
            step.held_key_match_count, field="step.held_key_match_count"
        )
        if step.held_physical_key is None:
            raise C2ContractError(
                "held_key_match_count requires a bound held_physical_key"
            )
        if expected_offset < release_offset and match_count != 1:
            raise C2ContractError(
                "a held row must have exactly one contemporaneous support match"
            )
        if (
            expected_offset == release_offset
            and release_reason == "support_expired"
            and match_count == 1
        ):
            raise C2ContractError(
                "support-expired release row still has a unique support match"
            )
    action = _exact_nonnegative_int(step.action, field="step.action")
    if action >= ACTION_DIM:
        raise C2ContractError(f"step.action must lie in [0, {ACTION_DIM})")
    key = _physical_key(step.physical_key, field="step.physical_key")
    main_action = _exact_nonnegative_int(
        step.detached_main_action, field="step.detached_main_action"
    )
    if main_action >= ACTION_DIM:
        raise C2ContractError(
            f"step.detached_main_action must lie in [0, {ACTION_DIM})"
        )
    main_key = _physical_key(step.detached_main_key, field="step.detached_main_key")
    executed_joint = _validate_joint_physical_actions(
        step.executed_joint_physical_actions,
        user_count=certificate.user_count,
        field="step.executed_joint_physical_actions",
    )
    detached_main_joint = _validate_joint_physical_actions(
        step.detached_main_joint_physical_actions,
        user_count=certificate.user_count,
        field="step.detached_main_joint_physical_actions",
    )
    if _sha256(
        step.executed_joint_physical_sha256,
        field="step.executed_joint_physical_sha256",
    ) != joint_physical_actions_sha256(
        executed_joint, user_count=certificate.user_count
    ):
        raise C2ContractError("executed joint-physical SHA-256 does not match values")
    if _sha256(
        step.detached_main_joint_physical_sha256,
        field="step.detached_main_joint_physical_sha256",
    ) != joint_physical_actions_sha256(
        detached_main_joint, user_count=certificate.user_count
    ):
        raise C2ContractError(
            "detached-Main joint-physical SHA-256 does not match values"
        )
    if executed_joint[certificate.focal_user] != key:
        raise C2ContractError("executed focal physical ID disagrees with joint action")
    if detached_main_joint[certificate.focal_user] != main_key:
        raise C2ContractError("detached Main focal ID disagrees with joint action")
    nonfocal_users = tuple(
        user for user in range(certificate.user_count) if user != certificate.focal_user
    )
    if any(
        executed_joint[user] != detached_main_joint[user]
        for user in nonfocal_users
    ):
        raise C2ContractError("executed branch changed a nonfocal physical action")
    bindings = _validate_action_bindings(step.action_bindings, field="step.action_bindings")
    table_digest = action_table_sha256(bindings)
    if _sha256(step.action_table_sha256, field="step.action_table_sha256") != table_digest:
        raise C2ContractError("executed action-table SHA-256 does not match bindings")
    if _binding_key(bindings, action, field="step.action_bindings") != key:
        raise C2ContractError("executed action does not map to its physical key")
    if _binding_key(bindings, main_action, field="step.action_bindings") != main_key:
        raise C2ContractError("detached Main action does not map to its physical key")
    if expected_offset == 0:
        if action != certificate.candidate_action:
            raise C2ContractError("opening action differs from certified candidate action")
        if (
            main_action != certificate.reference_action
            or main_key != certificate.reference_key
        ):
            raise C2ContractError(
                "opening detached Main differs from certified reference action"
            )
        if table_digest != certificate.opening_action_table_sha256:
            raise C2ContractError("opening action table differs from certified table")
        if _sha256(step.state_sha256, field="step.state_sha256") != certificate.opening_state_sha256:
            raise C2ContractError("opening state differs from certified forecast anchor")
        if _sha256(step.state_mask_sha256, field="step.state_mask_sha256") != certificate.opening_mask_sha256:
            raise C2ContractError("opening mask differs from certified forecast anchor")
    if step.phase == "hold" and key != certificate.candidate_key:
        raise C2ContractError("hold interval changed the certified physical ID")
    if step.phase == "release" and (action != main_action or key != main_key):
        raise C2ContractError("release interval did not execute detached Main")
    if step.phase == "release" and executed_joint != detached_main_joint:
        raise C2ContractError("release interval did not execute the full detached Main joint action")

    reward_matrix = _validate_reward_matrix(
        step.reward_matrix, field="step.reward_matrix"
    )
    if len(reward_matrix) != certificate.user_count:
        raise C2ContractError("executed reward matrix has the wrong user count")
    if _sha256(
        step.reward_matrix_sha256, field="step.reward_matrix_sha256"
    ) != reward_matrix_sha256(reward_matrix):
        raise C2ContractError("executed reward-matrix SHA-256 does not match values")
    r2_values = tuple(row[C2_OBJECTIVE_INDEX] for row in reward_matrix)
    if _sha256(step.reward_source_sha256, field="step.reward_source_sha256") != certificate.reward_source_sha256:
        raise C2ContractError("executed reward implementation differs from forecast authority")
    if type(step.focal_served) is not bool:
        raise C2ContractError("executed focal_served must be Boolean")
    if (
        not isinstance(step.served, tuple)
        or len(step.served) != certificate.user_count
        or any(type(value) is not bool for value in step.served)
    ):
        raise C2ContractError(
            "executed served must be a Boolean tuple with one value per user"
        )
    if step.focal_served != step.served[certificate.focal_user]:
        raise C2ContractError(
            "executed focal_served disagrees with the full served vector"
        )
    _sha256(step.state_sha256, field="step.state_sha256")
    _sha256(step.state_mask_sha256, field="step.state_mask_sha256")
    _sha256(step.next_state_sha256, field="step.next_state_sha256")
    _sha256(step.next_mask_sha256, field="step.next_mask_sha256")
    if type(step.done) is not bool:
        raise C2ContractError("executed step done must be Boolean")
    # ``horizon_steps`` is deliberately consumed here even though the current
    # structural checks use only the release offset.  This keeps the bound
    # explicit and prevents an accidental future extension from accepting a
    # row outside the four-offset V0.3 policy.
    if expected_offset > horizon_steps:
        raise C2ContractError("executed option offset exceeds the sealed horizon")
    return r2_values[certificate.focal_user], step.served


def _chronology_receipt_sha256(
    receipt: object,
    *,
    certificate: TemporalForkCertificate,
) -> str:
    """Validate and bind the completed pre-outcome/live-step chronology.

    The chronology module imports this core, so this validator deliberately
    consumes its immutable receipt by value instead of importing that type back
    into the core.  A valid digest therefore proves the complete receipt was
    checked before any learning plan could be admitted.
    """

    required = (
        "schema",
        "option_id",
        "anchor_sha256",
        "live_rng_before_sha256",
        "live_rng_after_forecast_sha256",
        "forecast_rng_sha256",
        "forecast_request_sha256",
        "forecast_payload_sha256",
        "forecast_started_ns",
        "forecast_completed_ns",
        "live_step_started_ns",
        "live_step_completed_ns",
        "forecast_sequence",
        "live_rng_unchanged_during_forecast",
        "claim_ceiling",
    )
    if any(not hasattr(receipt, field) for field in required):
        raise C2ContractError("chronology receipt is incomplete")
    if getattr(receipt, "schema") != CHRONOLOGY_RECEIPT_SCHEMA:
        raise C2ContractError("chronology receipt schema drifted")
    if getattr(receipt, "option_id") != certificate.option_id:
        raise C2ContractError("chronology receipt belongs to a different option")
    if _sha256(
        getattr(receipt, "anchor_sha256"), field="chronology.anchor_sha256"
    ) != certificate.anchor_sha256:
        raise C2ContractError("chronology receipt belongs to a different anchor")
    digests = {
        field: _sha256(getattr(receipt, field), field=f"chronology.{field}")
        for field in (
            "live_rng_before_sha256",
            "live_rng_after_forecast_sha256",
            "forecast_rng_sha256",
            "forecast_request_sha256",
            "forecast_payload_sha256",
        )
    }
    if digests["live_rng_before_sha256"] != digests["live_rng_after_forecast_sha256"]:
        raise C2LeakageError("chronology receipt shows live RNG advancement during forecast")
    if digests["forecast_payload_sha256"] != certificate.forecast_payload_sha256:
        raise C2ContractError("chronology receipt forecast payload differs from certificate")
    if digests["forecast_rng_sha256"] == digests["live_rng_before_sha256"]:
        raise C2LeakageError("chronology receipt aliases forecast and live RNG state")
    times = tuple(
        _exact_nonnegative_int(getattr(receipt, field), field=f"chronology.{field}")
        for field in (
            "forecast_started_ns",
            "forecast_completed_ns",
            "live_step_started_ns",
            "live_step_completed_ns",
        )
    )
    if tuple(sorted(times)) != times:
        raise C2ContractError("chronology receipt timestamps are out of order")
    sequence = getattr(receipt, "forecast_sequence")
    if type(sequence) is not tuple or sequence != CHRONOLOGY_SEQUENCE:
        raise C2ContractError("chronology receipt sequence is not canonical")
    if getattr(receipt, "live_rng_unchanged_during_forecast") is not True:
        raise C2LeakageError("chronology receipt did not prove live RNG nonadvancement")
    claim = _nonempty_string(
        getattr(receipt, "claim_ceiling"), field="chronology.claim_ceiling"
    )
    if claim != "ORDER_AND_RNG_NONADVANCEMENT_NOT_EFFICACY":
        raise C2ContractError("chronology receipt claim ceiling drifted")
    return _json_sha256(
        {
            "schema": CHRONOLOGY_RECEIPT_SCHEMA,
            "option_id": certificate.option_id,
            "anchor_sha256": certificate.anchor_sha256,
            **digests,
            "forecast_started_ns": times[0],
            "forecast_completed_ns": times[1],
            "live_step_started_ns": times[2],
            "live_step_completed_ns": times[3],
            "forecast_sequence": sequence,
            "live_rng_unchanged_during_forecast": True,
            "claim_ceiling": claim,
        }
    )


def close_temporal_option(
    certificate: TemporalForkCertificate,
    executed: Sequence[ExecutedOptionStep],
    *,
    discount_factor: float,
    chronology_receipt: object | None = None,
) -> C2ClosedOptionPlan:
    """Validate and close a private option plus primitive Main donor sequence.

    A real terminal may close an observed prefix without padding.  Any other
    missing suffix after live execution is a runner-integrity error.  Corrupt,
    cross-option, noncanonical, or falsely labelled transitions fail closed.
    Realised reward or service outcomes are retained as training data and never
    decide admission after a certified option was executed.
    """

    if not isinstance(certificate, TemporalForkCertificate):
        raise C2ContractError("certificate must be TemporalForkCertificate")
    gamma = _finite_number(discount_factor, field="discount_factor")
    if not 0.0 <= gamma <= 1.0:
        raise C2ContractError("discount_factor must lie in [0,1]")
    if isinstance(executed, (str, bytes)):
        raise C2ContractError("executed must be a sequence of option steps")
    steps = tuple(executed)
    # The option always covers the sealed forecast horizon.  The release may
    # occur earlier, so using ``certificate.hold_steps + 1`` here would reject
    # valid rows after a support-triggered release.
    _release_policy(
        release_offset=certificate.release_offset,
        release_reason=certificate.release_reason,
        horizon_steps=certificate.horizon_steps,
        field_prefix="certificate",
    )
    expected_count = certificate.horizon_steps + 1
    if len(steps) > expected_count:
        raise C2ContractError("executed option contains transitions past first release")

    focal_rewards: list[float] = []
    realised_service: list[tuple[bool, ...]] = []
    for index, step in enumerate(steps):
        reward, served = _validate_executed_step(
            step, certificate=certificate, expected_offset=index
        )
        focal_rewards.append(reward)
        realised_service.append(served)
    if len({step.bundle_id for step in steps}) != len(steps):
        raise C2ContractError("executed option cannot repeat a bundle ID")
    if steps:
        policy = tuple(
            _step_release_policy(step, certificate=certificate) for step in steps
        )
        if len(set(policy)) != 1:
            raise C2ContractError(
                "executed option release offset/reason drifted across rows"
            )
        actual_release_offset, actual_release_reason, actual_horizon = policy[0]
        if actual_horizon != certificate.horizon_steps:
            raise C2ContractError("executed option horizon disagrees with certificate")
        release_rows = [
            index
            for index, step in enumerate(steps)
            if step.phase == "release"
        ]
        if release_rows and release_rows[0] != actual_release_offset:
            raise C2ContractError(
                "executed option release row does not match its release offset"
            )
        if release_rows and actual_release_reason == "support_expired":
            release_step = steps[release_rows[0]]
            if release_step.held_key_match_count == 1:
                raise C2ContractError(
                    "support-expired release was not triggered by support loss"
                )
        if len(steps) == expected_count and not release_rows:
            raise C2ContractError("complete option is missing its release row")
    for left, right in zip(steps, steps[1:], strict=False):
        if left.next_state_sha256 != right.state_sha256:
            raise C2ContractError("executed option state chain is discontinuous")
        if left.next_mask_sha256 != right.state_mask_sha256:
            raise C2ContractError("executed option mask chain is discontinuous")
        if left.done:
            raise C2ContractError("an option cannot continue after a terminal transition")

    complete = len(steps) == expected_count
    if complete and any(step.done for step in steps[:-1]):
        raise C2ContractError("hold interval terminated before the declared release")
    discounted = math.fsum(
        (gamma**index) * reward for index, reward in enumerate(focal_rewards)
    )
    if not math.isfinite(discounted):
        raise C2ContractError("specialist option return must remain finite")
    realised_focal_service_ok = (
        all(row[certificate.focal_user] for row in realised_service)
        if realised_service
        else None
    )
    chronology_sha256 = (
        None
        if chronology_receipt is None
        else _chronology_receipt_sha256(
            chronology_receipt, certificate=certificate
        )
    )
    if steps and not certificate.passed:
        raise C2ContractError(
            "a failed pre-outcome certificate cannot have an executed C2 branch"
        )
    if steps and chronology_sha256 is None:
        raise C2ContractError(
            "an executed C2 branch is missing its pre-outcome chronology receipt"
        )
    final_done = bool(steps and steps[-1].done)
    if steps and not complete and not final_done:
        raise C2ContractError(
            "a nonterminal C2 prefix is a runner-integrity error, not zero dose"
        )
    admitted = bool(certificate.passed and steps and chronology_sha256 is not None)
    specialist_return = discounted if admitted else None
    # Q2F ranks bounded certified options.  The ordinary post-release action
    # mask is not a certified C2 decision support, so it must never be used as
    # an off-support max-Q bootstrap.  A future event-level option process may
    # add a separately certified next-decision bootstrap.
    bootstrap = 0.0 if admitted else None
    if not certificate.passed:
        disposition = "zero_dose_preoutcome_certificate_failed"
    elif not steps:
        disposition = "zero_dose_no_live_intervention"
    elif not complete and final_done:
        disposition = "admit_realised_early_terminal_prefix_to_q2_only"
    else:
        disposition = "admit_complete_primitive_sequence_to_q2_only"

    return C2ClosedOptionPlan(
        version=CANDIDATE_VERSION,
        option_id=certificate.option_id,
        anchor_sha256=certificate.anchor_sha256,
        objective_index=C2_OBJECTIVE_INDEX,
        focal_user=certificate.focal_user,
        action=certificate.candidate_action,
        discount_factor=gamma,
        specialist_target_enabled=admitted,
        specialist_option_return=specialist_return,
        specialist_bootstrap_discount=bootstrap,
        specialist_target_mode=(
            "fixed_horizon_option_return_regression_private_only"
            if admitted
            else "disabled"
        ),
        main_sequence_enabled=admitted,
        main_target_mode=(
            "canonical_observed_primitive_mean_loss_single_source_unit"
            if admitted
            else "disabled"
        ),
        main_source_unit_id=certificate.option_id if admitted else None,
        chronology_receipt_sha256=chronology_sha256 if admitted else None,
        observed_bundle_ids=tuple(step.bundle_id for step in steps),
        main_bundle_ids=(
            tuple(step.bundle_id for step in steps) if admitted else ()
        ),
        main_focal_actions=(
            tuple(step.action for step in steps) if admitted else ()
        ),
        main_behavior_probabilities=(
            tuple(step.behavior_probability for step in steps) if admitted else ()
        ),
        main_reward_matrix_sha256=(
            tuple(step.reward_matrix_sha256 for step in steps) if admitted else ()
        ),
        main_r2_column_sha256=(
            tuple(
                r2_column_sha256(
                    tuple(row[C2_OBJECTIVE_INDEX] for row in step.reward_matrix)
                )
                for step in steps
            )
            if admitted
            else ()
        ),
        opening_state_sha256=steps[0].state_sha256 if admitted else None,
        bootstrap_state_sha256=steps[-1].next_state_sha256 if admitted else None,
        bootstrap_mask_sha256=steps[-1].next_mask_sha256 if admitted else None,
        executed_steps=len(steps),
        planned_steps=expected_count,
        complete_hold_and_release=complete,
        realised_focal_service_all=realised_focal_service_ok,
        realised_served_by_step=tuple(realised_service),
        environment_terminal=final_done,
        admitted=admitted,
        disposition=disposition,
        release_offset=(actual_release_offset if steps else certificate.release_offset),
        release_reason=(actual_release_reason if steps else certificate.release_reason),
        horizon_steps=(actual_horizon if steps else certificate.horizon_steps),
    )
