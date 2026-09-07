"""Pre-outcome Q2F choice consumer for the C2 V0.3 temporal fork.

This module is deliberately a small, append-only seam between a completed
forecast set and the live option runner.  It consumes only prepared forks and
their public, hash-bound certificates.  It never calls ``run_live_step`` (or
any other live/realised-payload API), never ranks Main fallback, and never
mutates Q2F or a prepared fork.

The public entry point is :func:`select_prepared_fork`:

* no passed certificate -> Main fallback (no C2 choice);
* one passed certificate -> a forced certificate control, with probability 1;
* two or more passed certificates -> one masked epsilon-greedy Q2F choice;
* ``mode="matched_random"`` -> uniform choice over the same sorted support.

The receipt is the pre-live authority handed to the option runner.  It binds
the complete sorted support, opening/global-anchor context, certificate and
evidence digests, Q2F policy/network state, behavior RNG transition, exact
probability, and a caller-supplied pre-outcome timestamp.  Its claim ceiling
is intentionally limited to choice provenance; it is not an EE result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Callable, Mapping, Protocol, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
for _path in (HERE, HERE.parents[1] / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import c2_temporal_fork_core as core  # noqa: E402
import c2_temporal_fork_forecast_adapter as forecast  # noqa: E402


SELECTION_SCHEMA = "c2-v03-preoutcome-q2f-choice-receipt-v1"
CLAIM_CEILING = "PREOUTCOME_CHOICE_ONLY_NOT_LIVE_OUTCOME_OR_EFFICACY"
CHOICE_MODE_Q2F = "q2f_epsilon_greedy"
CHOICE_MODE_RANDOM = "matched_random"
CHOICE_MODE_FALLBACK = "main_fallback"
CHOICE_MODE_FORCED = "forced_certificate_control"
CANDIDATE_OUTCOME_PASS = "certificate_pass"
CANDIDATE_OUTCOME_FAIL = "certificate_fail"
CANDIDATE_OUTCOME_SUPPORT_REJECTION = "support_rejection"
CANDIDATE_OUTCOME_CONTRACT_ERROR = "contract_error"
_CANDIDATE_OUTCOMES = frozenset(
    {
        CANDIDATE_OUTCOME_PASS,
        CANDIDATE_OUTCOME_FAIL,
        CANDIDATE_OUTCOME_SUPPORT_REJECTION,
        CANDIDATE_OUTCOME_CONTRACT_ERROR,
    }
)


class C2SelectionError(core.C2ContractError):
    """The candidate support or Q2F behavior policy is not admissible."""


class Q2FChoiceScorer(Protocol):
    """Minimal read-only surface accepted from the objective-2 specialist."""

    objective_index: int
    policy_version: int

    def q_values(self, states: np.ndarray) -> np.ndarray:
        """Return online logits/Q values for a batch of encoded states."""


@dataclass(frozen=True)
class C2ChoiceSupport:
    """One passed certificate in the deterministic sorted choice support."""

    focal_user: int
    action: int
    physical_key: core.PhysicalKey
    option_id: str
    certificate_sha256: str
    evidence_sha256: str
    anchor_sha256: str
    anchor_context_sha256: str
    opening_state_sha256: str
    opening_mask_sha256: str
    opening_action_table_sha256: str


@dataclass(frozen=True)
class C2CandidateScheduleRow:
    """One ordered, deterministic pass/fail/error forecast outcome."""

    schedule_index: int
    focal_user: int
    candidate_key: core.PhysicalKey | None
    outcome: str
    option_id: str | None = None
    certificate_sha256: str | None = None
    evidence_sha256: str | None = None
    failures: tuple[str, ...] = ()
    rejection_reason: str | None = None
    error_type: str | None = None
    error_message_sha256: str | None = None


@dataclass(frozen=True)
class C2ChoiceReceipt:
    """Hash-bound pre-live choice provenance."""

    schema: str
    receipt_sha256: str
    mode: str
    candidate_schedule_sha256: str
    candidate_schedule_size: int
    support: tuple[C2ChoiceSupport, ...]
    selected_index: int | None
    selected_option_id: str | None
    selected_focal_user: int | None
    selected_action: int | None
    selected_physical_key: core.PhysicalKey | None
    anchor_sha256: str | None
    anchor_context_sha256: str | None
    q2f_policy_version: int | None
    q2f_online_network_state_sha256: str | None
    epsilon: float
    scores: tuple[float, ...]
    greedy_index: int | None
    behavior_probability: float
    behavior_rng_before_sha256: str
    behavior_rng_after_sha256: str
    preoutcome_timestamp_ns: int
    claim_ceiling: str


@dataclass(frozen=True)
class C2PreparedForkSelection:
    """Selected prepared fork plus its pre-live receipt.

    ``prepared`` is ``None`` only for Main fallback.  The selected object is
    the exact prepared fork supplied by the caller; no copy or live step is
    performed here so the existing option runner can commit it afterwards.
    """

    prepared: Any | None
    receipt: C2ChoiceReceipt
    behavior_probability: float
    candidate_set: tuple[Any, ...] = field(repr=False, compare=False)
    candidate_schedule: tuple[C2CandidateScheduleRow, ...] = field(
        repr=False, compare=False
    )

    @property
    def selected_prepared_fork(self) -> Any | None:
        """Alias used by the option-runner integration."""

        return self.prepared

    @property
    def selected_option_id(self) -> str | None:
        return self.receipt.selected_option_id


def _jsonable(value: Any) -> Any:
    """Canonicalize JSON, numpy, and tensor-like values for receipt hashing."""

    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return {"int": str(int(value))}
    if isinstance(value, (float, np.floating)) and not isinstance(value, bool):
        converted = float(value)
        if not math.isfinite(converted):
            raise C2SelectionError("receipt payload contains a nonfinite number")
        return {"float_hex": converted.hex()}
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        if array.dtype.hasobject:
            raise C2SelectionError("receipt payload cannot contain object arrays")
        if np.issubdtype(array.dtype, np.number) and not np.all(np.isfinite(array)):
            raise C2SelectionError("receipt payload contains a nonfinite array")
        return {
            "ndarray_dtype": array.dtype.str,
            "ndarray_shape": list(array.shape),
            "ndarray_sha256": hashlib.sha256(array.tobytes(order="C")).hexdigest(),
        }
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise C2SelectionError("receipt mapping keys must be strings")
        return {key: _jsonable(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    # torch tensors are intentionally handled without importing torch.  This
    # keeps selection a lightweight read-only adapter while still hashing the
    # exact online network state when a real ObjectiveSpecialist is supplied.
    if hasattr(value, "detach") and hasattr(value, "cpu") and hasattr(value, "numpy"):
        return _jsonable(np.asarray(value.detach().cpu().numpy()))
    raise C2SelectionError(
        f"receipt payload contains unsupported type {type(value).__name__}"
    )


def _digest(value: Any) -> str:
    encoded = json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise C2SelectionError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise C2SelectionError(f"{field} must be a nonnegative exact integer")
    return int(value)


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise C2SelectionError(f"{field} must be finite")
    converted = float(value)
    if not math.isfinite(converted):
        raise C2SelectionError(f"{field} must be finite")
    return converted


def _rng_state(rng: np.random.Generator, *, field: str) -> Mapping[str, Any]:
    if not isinstance(rng, np.random.Generator):
        raise C2SelectionError(f"{field} must be numpy.random.Generator")
    return rng.bit_generator.state


def _anchor_context_payload(anchor_payload: object) -> Mapping[str, Any]:
    if not isinstance(anchor_payload, Mapping):
        raise C2SelectionError("prepared anchor_payload must be a mapping")
    if "focal_user" not in anchor_payload:
        raise C2SelectionError("anchor_payload must identify focal_user")
    # The focal user is the local choice coordinate; all other fields are the
    # global state/mask/Main/checkpoint/environment/reward/RNG context.
    return {key: anchor_payload[key] for key in anchor_payload if key != "focal_user"}


def _context_hash(anchor: object) -> str:
    return _digest(_anchor_context_payload(getattr(anchor, "anchor_payload", None)))


def _opening_state_mask_hashes(anchor: object, *, focal_user: int) -> tuple[str, str]:
    observation = getattr(anchor, "observation", None)
    states = getattr(observation, "state_matrix", None)
    masks = getattr(observation, "masks", None)
    if states is None:
        states = getattr(anchor, "states", None)
    if masks is None:
        masks = getattr(anchor, "masks", None)
    try:
        state = np.asarray(states[focal_user])
        mask = np.asarray(masks[focal_user])
    except (IndexError, KeyError, TypeError) as error:
        raise C2SelectionError("prepared anchor lacks focal opening state/mask") from error
    if (
        state.ndim != 1
        or not np.issubdtype(state.dtype, np.number)
        or not np.all(np.isfinite(state))
    ):
        raise C2SelectionError("prepared focal opening state must be a finite vector")
    if mask.ndim != 1 or mask.dtype != np.bool_:
        raise C2SelectionError("prepared focal opening mask must be Boolean")
    # ForecastStepPayload normalizes numeric matrices to float64 tuples and
    # Boolean masks to tuples before producing the certificate hashes.
    state_payload = tuple(float(value) for value in state.tolist())
    mask_payload = tuple(bool(value) for value in mask.tolist())
    return (
        forecast.canonical_payload_sha256(state_payload),
        forecast.canonical_payload_sha256(mask_payload),
    )


def _bindings_for_focal(anchor: object, *, focal_user: int) -> tuple[core.ActionBinding, ...]:
    try:
        bindings = getattr(anchor, "action_bindings_by_user")[focal_user]
    except (AttributeError, IndexError, KeyError, TypeError) as error:
        raise C2SelectionError("prepared anchor lacks focal opening action bindings") from error
    try:
        rows = tuple(bindings)
    except TypeError as error:
        raise C2SelectionError("focal opening action bindings are not iterable") from error
    if not rows or any(not isinstance(row, core.ActionBinding) for row in rows):
        raise C2SelectionError("focal opening action bindings are malformed")
    # Reuse the core's strict table validator/digest without importing a
    # trainer/backend implementation detail.
    table_sha256 = core.action_table_sha256(rows)
    return rows


def _binding_physical(
    bindings: Sequence[core.ActionBinding], action: int, *, field: str
) -> core.PhysicalKey:
    matches = [row.physical_key for row in bindings if row.action == action]
    if len(matches) != 1:
        raise C2SelectionError(f"{field} does not bind exactly one physical action")
    return tuple(matches[0])


def _certificate_payload(certificate: core.TemporalForkCertificate) -> Mapping[str, Any]:
    """Serialize every public certificate field, including failures/floors."""

    return {
        "version": certificate.version,
        "option_id": certificate.option_id,
        "evidence_sha256": certificate.evidence_sha256,
        "anchor_sha256": certificate.anchor_sha256,
        "reward_source_sha256": certificate.reward_source_sha256,
        "forecast_payload_sha256": certificate.forecast_payload_sha256,
        "focal_user": certificate.focal_user,
        "user_count": certificate.user_count,
        "reference_action": certificate.reference_action,
        "candidate_action": certificate.candidate_action,
        "reference_key": certificate.reference_key,
        "candidate_key": certificate.candidate_key,
        "opening_action_table_sha256": certificate.opening_action_table_sha256,
        "opening_state_sha256": certificate.opening_state_sha256,
        "opening_mask_sha256": certificate.opening_mask_sha256,
        "reference_branch_trace_sha256": certificate.reference_branch_trace_sha256,
        "candidate_branch_trace_sha256": certificate.candidate_branch_trace_sha256,
        "hold_steps": certificate.hold_steps,
        "release_offset": certificate.release_offset,
        "release_reason": certificate.release_reason,
        "horizon_steps": certificate.horizon_steps,
        "support_actions": certificate.support_actions,
        "passed": certificate.passed,
        "failures": tuple(failure.value for failure in certificate.failures),
        "reference_ee_bits_per_j": certificate.reference_ee_bits_per_j,
        "ee_surplus_bits": certificate.ee_surplus_bits,
        "ee_surplus_floor_bits": certificate.ee_surplus_floor_bits,
        "hold_r2_margin": certificate.hold_r2_margin,
        "full_r2_margin": certificate.full_r2_margin,
    }


def _schedule_row_payload(row: C2CandidateScheduleRow) -> Mapping[str, Any]:
    return {
        "schedule_index": row.schedule_index,
        "focal_user": row.focal_user,
        "candidate_key": row.candidate_key,
        "outcome": row.outcome,
        "option_id": row.option_id,
        "certificate_sha256": row.certificate_sha256,
        "evidence_sha256": row.evidence_sha256,
        "failures": row.failures,
        "rejection_reason": row.rejection_reason,
        "error_type": row.error_type,
        "error_message_sha256": row.error_message_sha256,
    }


def _schedule_identity_payload(row: C2CandidateScheduleRow) -> Mapping[str, Any]:
    payload = dict(_schedule_row_payload(row))
    payload.pop("schedule_index")
    return payload


def candidate_schedule_row_from_prepared(
    prepared: object,
    *,
    schedule_index: int,
) -> C2CandidateScheduleRow:
    """Build the exact schedule outcome for one completed forecast."""

    _prepared, certificate, _context = _validate_prepared(prepared)
    return C2CandidateScheduleRow(
        schedule_index=_exact_nonnegative_int(
            schedule_index, field="schedule_index"
        ),
        focal_user=certificate.focal_user,
        candidate_key=certificate.candidate_key,
        outcome=(
            CANDIDATE_OUTCOME_PASS
            if certificate.passed
            else CANDIDATE_OUTCOME_FAIL
        ),
        option_id=certificate.option_id,
        certificate_sha256=_digest(_certificate_payload(certificate)),
        evidence_sha256=certificate.evidence_sha256,
        failures=tuple(failure.value for failure in certificate.failures),
    )


def rejected_candidate_schedule_row(
    *,
    schedule_index: int,
    focal_user: int,
    candidate_key: core.PhysicalKey | None,
    outcome: str,
    rejection_reason: str | None = None,
    error: BaseException | None = None,
) -> C2CandidateScheduleRow:
    """Build a hash-stable pre-live support-rejection/error outcome."""

    if outcome not in {
        CANDIDATE_OUTCOME_SUPPORT_REJECTION,
        CANDIDATE_OUTCOME_CONTRACT_ERROR,
    }:
        raise C2SelectionError("rejected schedule row has the wrong outcome")
    if outcome == CANDIDATE_OUTCOME_SUPPORT_REJECTION:
        if not isinstance(rejection_reason, str) or not rejection_reason:
            raise C2SelectionError("support rejection requires a reason")
        if error is not None:
            raise C2SelectionError("support rejection cannot carry a contract error")
    else:
        if not isinstance(error, BaseException):
            raise C2SelectionError("contract-error schedule row requires an exception")
        if rejection_reason is not None:
            raise C2SelectionError("contract error cannot carry a rejection reason")
    normalized_key = (
        None
        if candidate_key is None
        else (int(candidate_key[0]), int(candidate_key[1]))
    )
    return C2CandidateScheduleRow(
        schedule_index=_exact_nonnegative_int(
            schedule_index, field="schedule_index"
        ),
        focal_user=_exact_nonnegative_int(focal_user, field="focal_user"),
        candidate_key=normalized_key,
        outcome=outcome,
        rejection_reason=rejection_reason,
        error_type=None if error is None else type(error).__name__,
        error_message_sha256=None if error is None else _digest(str(error)),
    )


def _validate_schedule_row(row: object, *, expected_index: int) -> C2CandidateScheduleRow:
    if not isinstance(row, C2CandidateScheduleRow):
        raise C2SelectionError("candidate schedule rows must be C2CandidateScheduleRow")
    if row.schedule_index != expected_index:
        raise C2SelectionError("candidate schedule indices must be consecutive and ordered")
    _exact_nonnegative_int(row.focal_user, field="schedule.focal_user")
    if row.candidate_key is not None:
        if (
            not isinstance(row.candidate_key, tuple)
            or len(row.candidate_key) != 2
            or any(type(value) is not int for value in row.candidate_key)
        ):
            raise C2SelectionError("schedule candidate_key must be one physical pair")
    if row.outcome not in _CANDIDATE_OUTCOMES:
        raise C2SelectionError("candidate schedule outcome is unknown")
    completed = row.outcome in {CANDIDATE_OUTCOME_PASS, CANDIDATE_OUTCOME_FAIL}
    if completed:
        if row.candidate_key is None or not row.option_id:
            raise C2SelectionError("completed schedule row lacks candidate identity")
        _sha256(row.certificate_sha256, field="schedule.certificate_sha256")
        _sha256(row.evidence_sha256, field="schedule.evidence_sha256")
        if row.rejection_reason is not None or row.error_type is not None or row.error_message_sha256 is not None:
            raise C2SelectionError("completed schedule row carries rejection/error fields")
    elif row.outcome == CANDIDATE_OUTCOME_SUPPORT_REJECTION:
        if not row.rejection_reason or row.error_type is not None or row.error_message_sha256 is not None:
            raise C2SelectionError("support-rejection schedule row is malformed")
    else:
        if row.rejection_reason is not None or not row.error_type:
            raise C2SelectionError("contract-error schedule row is malformed")
        _sha256(row.error_message_sha256, field="schedule.error_message_sha256")
    return row


def _normalize_candidate_schedule(
    candidates: Sequence[object],
    candidate_schedule: Sequence[C2CandidateScheduleRow] | None,
) -> tuple[C2CandidateScheduleRow, ...]:
    candidate_rows = tuple(candidates)
    if candidate_schedule is None:
        schedule = tuple(
            candidate_schedule_row_from_prepared(
                prepared, schedule_index=index
            )
            for index, prepared in enumerate(candidate_rows)
        )
    else:
        try:
            schedule = tuple(candidate_schedule)
        except TypeError as error:
            raise C2SelectionError("candidate_schedule must be a sequence") from error
        schedule = tuple(
            _validate_schedule_row(row, expected_index=index)
            for index, row in enumerate(schedule)
        )
    if len(schedule) < len(candidate_rows):
        raise C2SelectionError("candidate schedule omits a completed forecast")
    expected_completed = {
        _digest(
            _schedule_identity_payload(
                candidate_schedule_row_from_prepared(prepared, schedule_index=0)
            )
        )
        for prepared in candidate_rows
    }
    actual_completed = {
        _digest(_schedule_identity_payload(row))
        for row in schedule
        if row.outcome in {CANDIDATE_OUTCOME_PASS, CANDIDATE_OUTCOME_FAIL}
    }
    if expected_completed != actual_completed:
        raise C2SelectionError(
            "candidate schedule differs from its complete candidate set"
        )
    return schedule


def _validate_prepared(prepared: object) -> tuple[object, core.TemporalForkCertificate, str]:
    """Validate one forecast-complete prepared fork without touching live state."""

    if prepared is None:
        raise C2SelectionError("candidate set cannot contain None")
    if getattr(prepared, "phase", None) != "forecast_complete":
        raise C2SelectionError("every candidate must be forecast_complete")
    build = getattr(prepared, "build", None)
    if build is None:
        raise C2SelectionError("every candidate must have a completed forecast build")
    certificate = getattr(build, "certificate", None)
    if not isinstance(certificate, core.TemporalForkCertificate):
        raise C2SelectionError("forecast build lacks a TemporalForkCertificate")
    anchor = getattr(prepared, "anchor", None)
    if anchor is None:
        raise C2SelectionError("prepared fork lacks its opening anchor")
    focal_user = _exact_nonnegative_int(certificate.focal_user, field="certificate.focal_user")
    user_count = _exact_nonnegative_int(certificate.user_count, field="certificate.user_count")
    if user_count == 0 or focal_user >= user_count:
        raise C2SelectionError("certificate focal_user/user_count is invalid")
    if getattr(anchor, "focal_user", None) != focal_user:
        raise C2SelectionError("prepared anchor and certificate focal users disagree")

    # A completed build must be the public certificate's own evidence lineage.
    evidence = getattr(build, "evidence", None)
    authority = getattr(build, "authority", None)
    if not isinstance(evidence, core.TemporalForkEvidence):
        raise C2SelectionError("forecast build lacks TemporalForkEvidence")
    if not isinstance(authority, core.ForecastAuthority):
        raise C2SelectionError("forecast build lacks ForecastAuthority")
    if evidence.authority != authority:
        raise C2SelectionError("forecast evidence/authority lineage drifted")
    try:
        recomputed_certificate = core.certify_temporal_fork(evidence)
    except core.C2ContractError as error:
        raise C2SelectionError("forecast evidence is not certifiable") from error
    if recomputed_certificate != certificate:
        raise C2SelectionError("certificate is not the exact result of its evidence")
    if evidence.focal_user != certificate.focal_user or evidence.user_count != certificate.user_count:
        raise C2SelectionError("forecast evidence user context disagrees with certificate")
    for field in (
        "anchor_sha256",
        "reward_source_sha256",
        "forecast_payload_sha256",
        "reference_branch_trace_sha256",
        "candidate_branch_trace_sha256",
        "opening_action_table_sha256",
        "opening_state_sha256",
        "opening_mask_sha256",
    ):
        if field == "anchor_sha256":
            expected = authority.anchor_sha256
        elif field == "reward_source_sha256":
            expected = authority.reward_source_sha256
        elif field == "forecast_payload_sha256":
            expected = authority.forecast_payload_sha256
        else:
            expected = getattr(evidence, field)
        if getattr(certificate, field) != expected:
            raise C2SelectionError(f"certificate/{field} lineage drifted")
    if getattr(build, "reference_trace_sha256", certificate.reference_branch_trace_sha256) != certificate.reference_branch_trace_sha256:
        raise C2SelectionError("forecast reference trace lineage drifted")
    if getattr(build, "candidate_trace_sha256", certificate.candidate_branch_trace_sha256) != certificate.candidate_branch_trace_sha256:
        raise C2SelectionError("forecast candidate trace lineage drifted")
    if getattr(build, "forecast_payload_sha256", certificate.forecast_payload_sha256) != certificate.forecast_payload_sha256:
        raise C2SelectionError("forecast payload lineage drifted")
    if getattr(build, "forecast_request_sha256", authority.forecast_request_sha256) != authority.forecast_request_sha256:
        raise C2SelectionError("forecast request lineage drifted")

    # Certificate identity must agree with the actual immutable opening
    # anchor, not merely with another field copied into the certificate.
    anchor_sha256 = forecast.canonical_payload_sha256(getattr(anchor, "anchor_payload", None))
    if certificate.anchor_sha256 != anchor_sha256:
        raise C2SelectionError("certificate anchor hash differs from prepared anchor")
    context_sha256 = _context_hash(anchor)
    state_sha256, mask_sha256 = _opening_state_mask_hashes(anchor, focal_user=focal_user)
    if certificate.opening_state_sha256 != state_sha256:
        raise C2SelectionError("certificate opening state differs from live anchor")
    if certificate.opening_mask_sha256 != mask_sha256:
        raise C2SelectionError("certificate opening mask differs from live anchor")
    bindings = _bindings_for_focal(anchor, focal_user=focal_user)
    if certificate.opening_action_table_sha256 != core.action_table_sha256(bindings):
        raise C2SelectionError("certificate opening action table differs from live anchor")
    main_actions = tuple(getattr(anchor, "main_actions"))
    main_physical = tuple(getattr(anchor, "main_physical_actions"))
    if len(main_actions) != user_count or len(main_physical) != user_count:
        raise C2SelectionError("prepared Main action vectors disagree with certificate users")
    if main_actions[focal_user] != certificate.reference_action:
        raise C2SelectionError("certificate reference action differs from opening Main")
    if main_physical[focal_user] != certificate.reference_key:
        raise C2SelectionError("certificate reference physical ID differs from opening Main")
    if _binding_physical(bindings, certificate.reference_action, field="reference_action") != certificate.reference_key:
        raise C2SelectionError("certificate reference action binding is inconsistent")
    if _binding_physical(bindings, certificate.candidate_action, field="candidate_action") != certificate.candidate_key:
        raise C2SelectionError("certificate candidate action binding is inconsistent")
    opening_masks = getattr(getattr(anchor, "observation", None), "masks", None)
    if opening_masks is None:
        opening_masks = getattr(anchor, "masks", None)
    try:
        focal_mask = np.asarray(opening_masks[focal_user])
    except (IndexError, KeyError, TypeError, ValueError) as error:
        raise C2SelectionError("prepared anchor lacks a focal opening action mask") from error
    if focal_mask.dtype != np.bool_ or focal_mask.ndim != 1:
        raise C2SelectionError("prepared focal opening action mask is not Boolean")
    for action_name, action in (
        ("reference_action", certificate.reference_action),
        ("candidate_action", certificate.candidate_action),
    ):
        if action >= focal_mask.shape[0] or not bool(focal_mask[action]):
            raise C2SelectionError(f"certificate {action_name} is masked at the opening anchor")
    if getattr(prepared, "candidate_key", None) != certificate.candidate_key:
        raise C2SelectionError("prepared candidate physical ID differs from certificate")
    if certificate.candidate_action == certificate.reference_action or certificate.candidate_key == certificate.reference_key:
        raise C2SelectionError("C2 candidate cannot equal opening Main")
    if not isinstance(certificate.passed, bool):
        raise C2SelectionError("certificate.passed must be Boolean")
    if certificate.passed and tuple(certificate.support_actions) != (
        certificate.reference_action,
        certificate.candidate_action,
    ):
        raise C2SelectionError("passed certificate support does not contain its candidate")
    if not certificate.passed and tuple(certificate.support_actions) != (certificate.reference_action,):
        raise C2SelectionError("failed certificate support is not fail-closed")
    return prepared, certificate, context_sha256


def _network_state_hash(q2f: object) -> str:
    explicit = getattr(q2f, "online_network_state_hash", None)
    if explicit is not None:
        return _sha256(explicit, field="q2f.online_network_state_hash")
    online = getattr(q2f, "online", None)
    if online is not None and hasattr(online, "state_dict"):
        state = online.state_dict()
    elif hasattr(q2f, "state_dict"):
        state = q2f.state_dict()
    else:
        raise C2SelectionError(
            "Q2F must expose online_network_state_hash, online.state_dict, or state_dict"
        )
    return _digest(state)


def _policy_version(q2f: object) -> int:
    version = getattr(q2f, "policy_version", None)
    if type(version) is not int or version < 0:
        raise C2SelectionError("Q2F policy_version must be a nonnegative exact integer")
    return int(version)


def _score_pair(q2f: object, prepared: object, certificate: core.TemporalForkCertificate) -> float:
    """Read one online Q2F logit for one focal-state/action pair."""

    anchor = getattr(prepared, "anchor")
    focal = certificate.focal_user
    observation = getattr(anchor, "observation", None)
    states = getattr(observation, "state_matrix", None)
    if states is None:
        states = getattr(anchor, "states", None)
    try:
        focal_state = np.asarray(states[focal], dtype=np.float32)
    except (IndexError, KeyError, TypeError, ValueError) as error:
        raise C2SelectionError("Q2F focal state cannot be materialized") from error
    if focal_state.ndim != 1 or not np.all(np.isfinite(focal_state)):
        raise C2SelectionError("Q2F focal state must be a finite vector")
    action = int(certificate.candidate_action)

    # The real ObjectiveSpecialist exposes q_values.  The pair-level hooks are
    # accepted for small adapters/tests, while still requiring exactly one
    # finite online score per support element.
    if hasattr(q2f, "q_values"):
        try:
            raw = np.asarray(q2f.q_values(focal_state[None, :]))
        except Exception as error:  # pragma: no cover - adapter-specific
            raise C2SelectionError("Q2F online q_values call failed") from error
        if raw.ndim == 1:
            if raw.shape[0] <= action:
                raise C2SelectionError("Q2F online logits omit the candidate action")
            score = raw[action]
        elif raw.ndim == 2 and raw.shape[0] == 1:
            if raw.shape[1] <= action:
                raise C2SelectionError("Q2F online logits omit the candidate action")
            score = raw[0, action]
        else:
            raise C2SelectionError("Q2F q_values must return one action-logit row")
    elif hasattr(q2f, "online_logits"):
        try:
            score = q2f.online_logits(
                focal_state,
                action,
                focal_user=focal,
                physical_key=certificate.candidate_key,
            )
        except TypeError:
            score = q2f.online_logits(focal_state, action)
    elif hasattr(q2f, "score_pair"):
        score = q2f.score_pair(
            focal_state,
            action,
            focal_user=focal,
            physical_key=certificate.candidate_key,
        )
    elif callable(q2f):
        score = q2f(
            focal_state,
            action,
            focal_user=focal,
            physical_key=certificate.candidate_key,
        )
    else:
        raise C2SelectionError("Q2F lacks a read-only online logits surface")
    return _finite(score, field="q2f.online_logit")


def _support_payload(support: Sequence[C2ChoiceSupport]) -> list[Mapping[str, Any]]:
    return [
        {
            "focal_user": item.focal_user,
            "action": item.action,
            "physical_key": item.physical_key,
            "option_id": item.option_id,
            "certificate_sha256": item.certificate_sha256,
            "evidence_sha256": item.evidence_sha256,
            "anchor_sha256": item.anchor_sha256,
            "anchor_context_sha256": item.anchor_context_sha256,
            "opening_state_sha256": item.opening_state_sha256,
            "opening_mask_sha256": item.opening_mask_sha256,
            "opening_action_table_sha256": item.opening_action_table_sha256,
        }
        for item in support
    ]


def _support_from_validated(
    validated: Sequence[tuple[object, core.TemporalForkCertificate, str]],
) -> tuple[
    tuple[C2ChoiceSupport, ...],
    tuple[tuple[object, core.TemporalForkCertificate, str], ...],
]:
    passed = [row for row in validated if row[1].passed]
    passed.sort(
        key=lambda row: (
            row[1].candidate_key,
            row[1].focal_user,
            row[1].candidate_action,
            row[1].option_id,
        )
    )
    support = tuple(
        C2ChoiceSupport(
            focal_user=certificate.focal_user,
            action=certificate.candidate_action,
            physical_key=certificate.candidate_key,
            option_id=certificate.option_id,
            certificate_sha256=_digest(_certificate_payload(certificate)),
            evidence_sha256=certificate.evidence_sha256,
            anchor_sha256=certificate.anchor_sha256,
            anchor_context_sha256=context_sha256,
            opening_state_sha256=certificate.opening_state_sha256,
            opening_mask_sha256=certificate.opening_mask_sha256,
            opening_action_table_sha256=certificate.opening_action_table_sha256,
        )
        for _prepared, certificate, context_sha256 in passed
    )
    return support, tuple(passed)


def _make_receipt(
    *,
    mode: str,
    candidate_schedule_sha256: str,
    candidate_schedule_size: int,
    support: tuple[C2ChoiceSupport, ...],
    selected_index: int | None,
    q2f_policy_version: int | None,
    q2f_network_hash: str | None,
    epsilon: float,
    scores: tuple[float, ...],
    greedy_index: int | None,
    behavior_probability: float,
    rng_before: str,
    rng_after: str,
    timestamp_ns: int,
) -> C2ChoiceReceipt:
    candidate_schedule_sha256 = _sha256(
        candidate_schedule_sha256, field="candidate_schedule_sha256"
    )
    candidate_schedule_size = _exact_nonnegative_int(
        candidate_schedule_size, field="candidate_schedule_size"
    )
    selected = None if selected_index is None else support[selected_index]
    # A local certificate anchor includes its focal user.  Multi-user choices
    # consequently have multiple exact local anchors while sharing one global
    # pre-outcome context; every local value remains bound in ``support``.
    anchor_values = {item.anchor_sha256 for item in support}
    anchor_sha256 = next(iter(anchor_values)) if len(anchor_values) == 1 else None
    context_sha256 = None if not support else support[0].anchor_context_sha256
    payload = {
        "schema": SELECTION_SCHEMA,
        "mode": mode,
        "candidate_schedule_sha256": candidate_schedule_sha256,
        "candidate_schedule_size": candidate_schedule_size,
        "support": _support_payload(support),
        "selected_index": selected_index,
        "selected_option_id": None if selected is None else selected.option_id,
        "selected_focal_user": None if selected is None else selected.focal_user,
        "selected_action": None if selected is None else selected.action,
        "selected_physical_key": None if selected is None else selected.physical_key,
        "anchor_sha256": anchor_sha256,
        "anchor_context_sha256": context_sha256,
        "q2f_policy_version": q2f_policy_version,
        "q2f_online_network_state_sha256": q2f_network_hash,
        "epsilon": epsilon,
        "scores": scores,
        "greedy_index": greedy_index,
        "behavior_probability": behavior_probability,
        "behavior_rng_before_sha256": rng_before,
        "behavior_rng_after_sha256": rng_after,
        "preoutcome_timestamp_ns": timestamp_ns,
        "claim_ceiling": CLAIM_CEILING,
    }
    receipt_sha256 = _digest(payload)
    return C2ChoiceReceipt(
        schema=SELECTION_SCHEMA,
        receipt_sha256=receipt_sha256,
        mode=mode,
        candidate_schedule_sha256=candidate_schedule_sha256,
        candidate_schedule_size=candidate_schedule_size,
        support=support,
        selected_index=selected_index,
        selected_option_id=None if selected is None else selected.option_id,
        selected_focal_user=None if selected is None else selected.focal_user,
        selected_action=None if selected is None else selected.action,
        selected_physical_key=None if selected is None else selected.physical_key,
        anchor_sha256=anchor_sha256,
        anchor_context_sha256=context_sha256,
        q2f_policy_version=q2f_policy_version,
        q2f_online_network_state_sha256=q2f_network_hash,
        epsilon=epsilon,
        scores=scores,
        greedy_index=greedy_index,
        behavior_probability=behavior_probability,
        behavior_rng_before_sha256=rng_before,
        behavior_rng_after_sha256=rng_after,
        preoutcome_timestamp_ns=timestamp_ns,
        claim_ceiling=CLAIM_CEILING,
    )


def _timestamp(timestamp_ns: object | None) -> int:
    if timestamp_ns is None:
        value = time.time_ns()
    else:
        value = timestamp_ns
    return _exact_nonnegative_int(value, field="preoutcome_timestamp_ns")


def select_prepared_fork(
    candidates: Sequence[object],
    *,
    candidate_schedule: Sequence[C2CandidateScheduleRow] | None = None,
    behavior_rng: np.random.Generator,
    q2f: Q2FChoiceScorer | Callable[..., float] | None = None,
    epsilon: float = 0.0,
    mode: str = CHOICE_MODE_Q2F,
    preoutcome_timestamp_ns: int | None = None,
) -> C2PreparedForkSelection:
    """Select one completed, certificate-passed C2 fork before live outcome.

    ``candidates`` is the complete forecast set at one global anchor.  Failed
    certificates are validated for lineage but excluded from the support.  A
    q2f mode with at least two passed certificates evaluates one online logit
    for every sorted focal-state/action pair and samples exactly once.  The
    matched-random mode uses the same support and RNG contract but does not
    consult Q2F logits.
    """

    if isinstance(candidates, (str, bytes)):
        raise C2SelectionError("candidates must be a sequence of prepared forks")
    try:
        candidate_rows = tuple(candidates)
    except TypeError as error:
        raise C2SelectionError("candidates must be a sequence") from error
    if not isinstance(behavior_rng, np.random.Generator):
        raise C2SelectionError("behavior_rng must be numpy.random.Generator")
    epsilon_value = _finite(epsilon, field="epsilon")
    if not 0.0 <= epsilon_value <= 1.0:
        raise C2SelectionError("epsilon must lie in [0,1]")
    if mode not in {CHOICE_MODE_Q2F, CHOICE_MODE_RANDOM}:
        raise C2SelectionError(f"unknown C2 choice mode {mode!r}")
    timestamp = _timestamp(preoutcome_timestamp_ns)
    before_sha256 = _digest(_rng_state(behavior_rng, field="behavior_rng"))

    validated: list[tuple[object, core.TemporalForkCertificate, str]] = []
    for candidate in candidate_rows:
        validated.append(_validate_prepared(candidate))
    if validated:
        _first_prepared, first_certificate, first_context = validated[0]
        expected_user_count = first_certificate.user_count
        expected_reward = first_certificate.reward_source_sha256
        seen_candidates: set[tuple[int, int, core.PhysicalKey]] = set()
        seen_options: set[str] = set()
        for prepared, certificate, context_sha256 in validated:
            if context_sha256 != first_context:
                raise C2SelectionError("candidate set mixes global anchor contexts")
            if certificate.user_count != expected_user_count:
                raise C2SelectionError("candidate set mixes user counts")
            if certificate.reward_source_sha256 != expected_reward:
                raise C2SelectionError("candidate set mixes reward authorities")
            identity = (
                certificate.focal_user,
                certificate.candidate_action,
                certificate.candidate_key,
            )
            if identity in seen_candidates:
                raise C2SelectionError("candidate set repeats a focal/action/physical ID")
            seen_candidates.add(identity)
            if certificate.option_id in seen_options:
                raise C2SelectionError("candidate set repeats an option ID")
            seen_options.add(certificate.option_id)
    normalized_schedule = _normalize_candidate_schedule(
        candidate_rows, candidate_schedule
    )
    schedule_sha256 = _digest(
        tuple(_schedule_row_payload(row) for row in normalized_schedule)
    )
    support, passed = _support_from_validated(validated)
    k = len(passed)
    selected_index: int | None = None
    greedy_index: int | None = None
    scores: tuple[float, ...] = ()
    policy_version: int | None = None
    network_hash: str | None = None
    if k == 0:
        selected_prepared = None
        choice_mode = CHOICE_MODE_FALLBACK
        probability = 1.0
    elif k == 1:
        selected_index = 0
        selected_prepared = passed[0][0]
        choice_mode = CHOICE_MODE_FORCED
        probability = 1.0
    else:
        if mode == CHOICE_MODE_Q2F:
            if q2f is None:
                raise C2SelectionError("Q2F is required for a multi-candidate learned choice")
            if getattr(q2f, "objective_index", None) != core.C2_OBJECTIVE_INDEX:
                raise C2SelectionError("choice Q2F must target objective index 1")
            policy_version = _policy_version(q2f)
            network_hash = _network_state_hash(q2f)
            score_values = tuple(
                _score_pair(q2f, prepared, certificate)
                for prepared, certificate, _context_sha256 in passed
            )
            scores = score_values
            # Support is already deterministically sorted.  Keeping the first
            # equal score makes physical ID/focal/action the tie-breaker.
            greedy_index = 0
            for index in range(1, k):
                if score_values[index] > score_values[greedy_index]:
                    greedy_index = index
            if behavior_rng.random() < epsilon_value:
                selected_index = int(behavior_rng.integers(0, k))
            else:
                selected_index = greedy_index
            probability = epsilon_value / k
            if selected_index == greedy_index:
                probability += 1.0 - epsilon_value
            choice_mode = CHOICE_MODE_Q2F
        else:
            # Matched random deliberately does not use Q2F logits, but if a
            # caller supplies Q2F metadata we bind it to the receipt so the
            # comparison remains auditable against the same policy snapshot.
            if q2f is not None:
                if getattr(q2f, "objective_index", None) != core.C2_OBJECTIVE_INDEX:
                    raise C2SelectionError("choice Q2F must target objective index 1")
                policy_version = _policy_version(q2f)
                network_hash = _network_state_hash(q2f)
            selected_index = int(behavior_rng.integers(0, k))
            probability = 1.0 / k
            choice_mode = CHOICE_MODE_RANDOM
        selected_prepared = passed[selected_index][0]
    after_sha256 = _digest(_rng_state(behavior_rng, field="behavior_rng"))
    receipt = _make_receipt(
        mode=choice_mode,
        candidate_schedule_sha256=schedule_sha256,
        candidate_schedule_size=len(normalized_schedule),
        support=support,
        selected_index=selected_index,
        q2f_policy_version=policy_version,
        q2f_network_hash=network_hash,
        epsilon=epsilon_value,
        scores=scores,
        greedy_index=greedy_index,
        behavior_probability=float(probability),
        rng_before=before_sha256,
        rng_after=after_sha256,
        timestamp_ns=timestamp,
    )
    return C2PreparedForkSelection(
        prepared=selected_prepared,
        receipt=receipt,
        behavior_probability=float(probability),
        candidate_set=candidate_rows,
        candidate_schedule=normalized_schedule,
    )


def assert_prepared_selection_bound(
    value: C2PreparedForkSelection,
) -> C2ChoiceReceipt:
    """Revalidate a selection and its complete pre-live candidate support.

    This is the consumer-side seal used immediately before the option runner.
    It does not resample behavior RNG or reevaluate Q2F; it proves that the
    receipt hashes the exact complete forecast set carried by ``value`` and
    that its selected prepared fork/probability obey the frozen K=0/1/K>=2
    policy.
    """

    if not isinstance(value, C2PreparedForkSelection):
        raise C2SelectionError("selection must be C2PreparedForkSelection")
    receipt = value.receipt
    if not isinstance(receipt, C2ChoiceReceipt):
        raise C2SelectionError("selection lacks a C2ChoiceReceipt")
    if receipt.schema != SELECTION_SCHEMA or receipt.claim_ceiling != CLAIM_CEILING:
        raise C2SelectionError("selection receipt schema/claim ceiling drifted")
    if receipt.selected_index is not None and (
        type(receipt.selected_index) is not int
        or not 0 <= receipt.selected_index < len(receipt.support)
    ):
        raise C2SelectionError("selection receipt selected_index is invalid")
    expected_receipt = _make_receipt(
        mode=receipt.mode,
        candidate_schedule_sha256=receipt.candidate_schedule_sha256,
        candidate_schedule_size=receipt.candidate_schedule_size,
        support=receipt.support,
        selected_index=receipt.selected_index,
        q2f_policy_version=receipt.q2f_policy_version,
        q2f_network_hash=receipt.q2f_online_network_state_sha256,
        epsilon=receipt.epsilon,
        scores=receipt.scores,
        greedy_index=receipt.greedy_index,
        behavior_probability=receipt.behavior_probability,
        rng_before=receipt.behavior_rng_before_sha256,
        rng_after=receipt.behavior_rng_after_sha256,
        timestamp_ns=receipt.preoutcome_timestamp_ns,
    )
    if expected_receipt != receipt:
        raise C2SelectionError("selection receipt digest/payload is not self-consistent")
    probability = _finite(value.behavior_probability, field="behavior_probability")
    if probability != receipt.behavior_probability:
        raise C2SelectionError("selection probability differs from its receipt")

    normalized_schedule = _normalize_candidate_schedule(
        value.candidate_set, value.candidate_schedule
    )
    if len(normalized_schedule) != receipt.candidate_schedule_size:
        raise C2SelectionError("selection schedule size differs from its receipt")
    schedule_sha256 = _digest(
        tuple(_schedule_row_payload(row) for row in normalized_schedule)
    )
    if schedule_sha256 != receipt.candidate_schedule_sha256:
        raise C2SelectionError("selection schedule differs from its receipt")

    validated = tuple(_validate_prepared(item) for item in value.candidate_set)
    if validated:
        first_context = validated[0][2]
        expected_users = validated[0][1].user_count
        expected_reward = validated[0][1].reward_source_sha256
        identities: set[tuple[int, int, core.PhysicalKey]] = set()
        option_ids: set[str] = set()
        for _prepared, certificate, context_sha256 in validated:
            if context_sha256 != first_context:
                raise C2SelectionError("selection candidate set mixes global contexts")
            if certificate.user_count != expected_users:
                raise C2SelectionError("selection candidate set mixes user counts")
            if certificate.reward_source_sha256 != expected_reward:
                raise C2SelectionError("selection candidate set mixes reward authorities")
            identity = (
                certificate.focal_user,
                certificate.candidate_action,
                certificate.candidate_key,
            )
            if identity in identities or certificate.option_id in option_ids:
                raise C2SelectionError("selection candidate set repeats an identity")
            identities.add(identity)
            option_ids.add(certificate.option_id)
    support, passed = _support_from_validated(validated)
    if support != receipt.support:
        raise C2SelectionError("selection support differs from its complete candidate set")

    k = len(passed)
    selected_index = receipt.selected_index
    if k == 0:
        if (
            receipt.mode != CHOICE_MODE_FALLBACK
            or selected_index is not None
            or value.prepared is not None
            or probability != 1.0
        ):
            raise C2SelectionError("K=0 selection must be a unit-probability Main fallback")
    elif k == 1:
        if (
            receipt.mode != CHOICE_MODE_FORCED
            or selected_index != 0
            or value.prepared is not passed[0][0]
            or probability != 1.0
            or receipt.scores
            or receipt.greedy_index is not None
            or receipt.q2f_policy_version is not None
            or receipt.q2f_online_network_state_sha256 is not None
        ):
            raise C2SelectionError("K=1 selection must be an unranked forced control")
    else:
        if type(selected_index) is not int or not 0 <= selected_index < k:
            raise C2SelectionError("multi-candidate selected_index is invalid")
        if value.prepared is not passed[selected_index][0]:
            raise C2SelectionError("selected prepared fork differs from receipt support")
        if receipt.mode == CHOICE_MODE_Q2F:
            if (
                receipt.q2f_policy_version is None
                or receipt.q2f_online_network_state_sha256 is None
                or len(receipt.scores) != k
            ):
                raise C2SelectionError("learned choice lacks Q2F policy/scores")
            greedy = max(range(k), key=lambda index: receipt.scores[index])
            if receipt.greedy_index != greedy:
                raise C2SelectionError("learned choice greedy index disagrees with scores")
            expected_probability = receipt.epsilon / k
            if selected_index == greedy:
                expected_probability += 1.0 - receipt.epsilon
            if not math.isclose(probability, expected_probability, rel_tol=0.0, abs_tol=1e-15):
                raise C2SelectionError("learned choice probability is incorrect")
        elif receipt.mode == CHOICE_MODE_RANDOM:
            if receipt.scores or receipt.greedy_index is not None:
                raise C2SelectionError("matched-random control cannot carry learned scores")
            if not math.isclose(probability, 1.0 / k, rel_tol=0.0, abs_tol=1e-15):
                raise C2SelectionError("matched-random probability is incorrect")
        else:
            raise C2SelectionError("multi-candidate selection has the wrong mode")
    return receipt


# Explicit aliases make the seam easy to discover from the option runner
# without introducing a second implementation.
choose_prepared_fork = select_prepared_fork
select_certificate_option = select_prepared_fork


__all__ = [
    "C2CandidateScheduleRow",
    "C2ChoiceReceipt",
    "C2ChoiceSupport",
    "C2PreparedForkSelection",
    "C2SelectionError",
    "CHOICE_MODE_FALLBACK",
    "CHOICE_MODE_FORCED",
    "CHOICE_MODE_Q2F",
    "CHOICE_MODE_RANDOM",
    "CANDIDATE_OUTCOME_CONTRACT_ERROR",
    "CANDIDATE_OUTCOME_FAIL",
    "CANDIDATE_OUTCOME_PASS",
    "CANDIDATE_OUTCOME_SUPPORT_REJECTION",
    "CLAIM_CEILING",
    "SELECTION_SCHEMA",
    "Q2FChoiceScorer",
    "choose_prepared_fork",
    "candidate_schedule_row_from_prepared",
    "rejected_candidate_schedule_row",
    "assert_prepared_selection_bound",
    "select_certificate_option",
    "select_prepared_fork",
]
