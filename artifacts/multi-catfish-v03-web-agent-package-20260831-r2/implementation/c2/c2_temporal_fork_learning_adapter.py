"""Append-only learning seams for the C2 V0.3 temporal fork.

This module deliberately does not import or mutate the frozen short-episode
runner.  It turns an admitted :class:`C2ClosedOptionPlan` into two explicitly
different learning objects:

* :class:`C2SMDPTransition` is one private Q2F fixed-window transition.  Its
  target is the observed canonical-r2 option return with no off-support
  post-release bootstrap.
* :class:`C2PrimitiveSequence` is one Main-Q2 source unit containing one to
  four real primitive receipts.  Its donor loss is reduced by mean, so option
  duration never changes the C2 dose and an early terminal needs no padding.

The adapter is intentionally a pure contract/target seam.  The eventual
runner can call these functions from a new integration layer without changing
the existing ``smc_er_core.py`` API.  State and mask hashes are computed from
the actual arrays here; a hash supplied only as metadata is never treated as
the payload itself.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

import c2_temporal_fork_core as core
from c2_temporal_fork_forecast_adapter import (  # noqa: E402
    canonical_payload_sha256 as _canonical_payload_sha256,
)


EXPECTED_DURATION = int(core.HOLD_STEPS) + 1
C2_OBJECTIVE_INDEX = int(core.C2_OBJECTIVE_INDEX)
ROLE_TO_OBJECTIVE: dict[str, int] = {"C1": 0, "C2": 1, "C3": 2}


class LearningContractError(core.C2ContractError):
    """A learning item does not satisfy the C2 V0.3 admission contract."""


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.number)
    ):
        raise LearningContractError(f"{field} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted):
        raise LearningContractError(f"{field} must be finite")
    return converted


def _exact_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise LearningContractError(f"{field} must be a nonnegative exact integer")
    return int(value)


def _digest(value: object, *, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise LearningContractError(f"{field} must be a 64-character SHA-256")
    if value != value.lower() or any(
        char not in "0123456789abcdef" for char in value
    ):
        raise LearningContractError(f"{field} must be lowercase hexadecimal SHA-256")
    return value


def _json_digest(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


_ADMISSION_SEAL = object()


@dataclass(frozen=True)
class C2AdmissionProof:
    """Module-sealed proof that a learning item came from an admitted plan."""

    admitted: bool
    option_id: str
    evidence_sha256: str
    chronology_receipt_sha256: str
    plan_sha256: str
    proof_sha256: str
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _ADMISSION_SEAL:
            raise LearningContractError(
                "C2 admission proof may only be created from an admitted plan"
            )
        if self.admitted is not True:
            raise LearningContractError("C2 admission proof must be admitted")
        if not isinstance(self.option_id, str) or not self.option_id:
            raise LearningContractError("admission option_id must be nonempty")
        for name in (
            "evidence_sha256",
            "chronology_receipt_sha256",
            "plan_sha256",
            "proof_sha256",
        ):
            _digest(getattr(self, name), field=f"admission.{name}")
        expected = _json_digest(
            {
                "admitted": True,
                "option_id": self.option_id,
                "evidence_sha256": self.evidence_sha256,
                "chronology_receipt_sha256": self.chronology_receipt_sha256,
                "plan_sha256": self.plan_sha256,
            }
        )
        if self.proof_sha256 != expected:
            raise LearningContractError("admission proof digest does not match")


def _float_hex(value: float) -> str:
    return float(value).hex()


def _immutable_array(value: object, *, field: str) -> np.ndarray:
    array = np.asarray(value)
    if array.dtype.hasobject:
        raise LearningContractError(f"{field} cannot have object dtype")
    if not (
        np.issubdtype(array.dtype, np.number)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        raise LearningContractError(f"{field} must be numeric or Boolean")
    copied = np.array(array, copy=True, order="C")
    copied.setflags(write=False)
    return copied


def array_sha256(value: object) -> str:
    """Hash an actual array with its dtype and shape bound to the payload.

    The core intentionally stores only receipt hashes.  This helper defines
    the adapter-side payload binding used when a runtime supplies the actual
    opening/bootstrap arrays.  Callers generating new V0.3 evidence should use
    the same helper for the corresponding core evidence hashes.
    """

    array = np.asarray(value)
    if array.dtype.hasobject:
        raise LearningContractError("array cannot have object dtype")
    if not (
        np.issubdtype(array.dtype, np.number)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        raise LearningContractError("array must be numeric or Boolean")
    def tuple_values(item: np.ndarray) -> object:
        if item.ndim == 0:
            return item.item()
        return tuple(tuple_values(np.asarray(child)) for child in item)

    # The authoritative forecast adapter canonicalizes focal vectors as a
    # tuple of scalar values.  Do the same here; hashing raw ndarray bytes
    # would make the learning recheck disagree with the execution receipt.
    return _canonical_payload_sha256(tuple_values(array))


def state_sha256(value: object) -> str:
    """Alias documenting that the value is a state payload."""

    return array_sha256(value)


def mask_sha256(value: object) -> str:
    """Alias documenting that the value is an action-mask payload."""

    array = np.asarray(value)
    if array.dtype != np.bool_:
        raise LearningContractError("mask must have Boolean dtype")
    return array_sha256(array)


def _require_digest_match(
    actual: object, expected: object, *, field: str
) -> None:
    actual_digest = _digest(actual, field=f"{field}.actual")
    expected_digest = _digest(expected, field=f"{field}.expected")
    if actual_digest != expected_digest:
        raise LearningContractError(f"{field} hash does not match the actual payload")


def _normalize_reward_matrix(
    value: object, *, field: str
) -> tuple[tuple[float, float, float], ...]:
    if isinstance(value, (str, bytes)):
        raise LearningContractError(f"{field} must be a U-by-3 reward matrix")
    try:
        rows = tuple(
            tuple(_finite(item, field=f"{field}[{user}][{objective}]") for objective, item in enumerate(row))
            for user, row in enumerate(value)  # type: ignore[arg-type]
        )
    except TypeError as error:
        raise LearningContractError(f"{field} must be a U-by-3 reward matrix") from error
    if not rows or any(len(row) != 3 for row in rows):
        raise LearningContractError(f"{field} must be a nonempty U-by-3 reward matrix")
    try:
        # The core validator owns the canonical-r2 set.  Calling its public
        # hash helper also makes this seam reject positive/arbitrary r2 values.
        core.reward_matrix_sha256(rows)
    except Exception as error:  # core raises its contract error type
        raise LearningContractError(f"{field} is not canonical") from error
    return rows


def _reward_hashes(
    value: object, *, field: str
) -> tuple[tuple[tuple[float, float, float], ...], str, str]:
    matrix = _normalize_reward_matrix(value, field=field)
    r2_column = tuple(row[C2_OBJECTIVE_INDEX] for row in matrix)
    return (
        matrix,
        core.reward_matrix_sha256(matrix),
        core.r2_column_sha256(r2_column),
    )


def _metadata(bundle: object, name: str) -> object | None:
    """Read a field first, then the immutable AtomicBundle provenance map."""

    if hasattr(bundle, name):
        value = getattr(bundle, name)
        if value is not None:
            return value
    provenance = getattr(bundle, "provenance", None)
    if isinstance(provenance, Mapping) and name in provenance:
        return provenance[name]
    return None


def _metadata_required(bundle: object, name: str) -> object:
    value = _metadata(bundle, name)
    if value is None:
        raise LearningContractError(f"constituent lacks {name} authority")
    return value


def _validate_optional_step_authority(step: object) -> None:
    """Honor newer core fields without making the seam version-fragile."""

    if hasattr(step, "focal_served"):
        value = getattr(step, "focal_served")
        if type(value) is not bool:
            raise LearningContractError("executed focal_served authority is malformed")
    if hasattr(step, "behavior_probability"):
        probability = _finite(
            getattr(step, "behavior_probability"), field="step.behavior_probability"
        )
        if not 0.0 <= probability <= 1.0:
            raise LearningContractError("step.behavior_probability must lie in [0,1]")


def _assert_admitted(
    plan: object, certificate: object
) -> tuple[core.C2ClosedOptionPlan, core.TemporalForkCertificate]:
    if not isinstance(plan, core.C2ClosedOptionPlan):
        raise LearningContractError("plan must be C2ClosedOptionPlan")
    if not isinstance(certificate, core.TemporalForkCertificate):
        raise LearningContractError("certificate must be TemporalForkCertificate")
    if plan.version != core.CANDIDATE_VERSION or certificate.version != core.CANDIDATE_VERSION:
        raise LearningContractError("C2 plan and certificate version drifted")
    if not certificate.passed or not plan.admitted:
        raise LearningContractError("only an admitted C2 plan can create learning data")
    if not plan.specialist_target_enabled:
        raise LearningContractError("plan has no enabled Q2F target")
    if not plan.main_sequence_enabled:
        raise LearningContractError("plan has no enabled Main sequence")
    if plan.objective_index != C2_OBJECTIVE_INDEX:
        raise LearningContractError("C2 plan objective must be canonical objective 1")
    if plan.option_id != certificate.option_id:
        raise LearningContractError("plan and certificate option IDs disagree")
    if plan.anchor_sha256 != certificate.anchor_sha256:
        raise LearningContractError("plan and certificate anchors disagree")
    if plan.focal_user != certificate.focal_user:
        raise LearningContractError("plan and certificate focal users disagree")
    if plan.action != certificate.candidate_action:
        raise LearningContractError("plan action is not the certified candidate action")
    try:
        plan_policy = core._release_policy(  # type: ignore[attr-defined]
            release_offset=plan.release_offset,
            release_reason=plan.release_reason,
            horizon_steps=plan.horizon_steps,
            field_prefix="plan",
        )
        certificate_policy = core._release_policy(  # type: ignore[attr-defined]
            release_offset=certificate.release_offset,
            release_reason=certificate.release_reason,
            horizon_steps=certificate.horizon_steps,
            field_prefix="certificate",
        )
    except core.C2ContractError as error:
        raise LearningContractError("C2 plan/certificate release policy is malformed") from error
    if plan_policy != certificate_policy:
        raise LearningContractError("plan and certificate release policies disagree")
    if plan.main_source_unit_id != plan.option_id:
        raise LearningContractError("C2 source unit must be the option identity")
    duration = int(plan.executed_steps)
    if not 1 <= duration <= EXPECTED_DURATION:
        raise LearningContractError("C2 plan must expose one to four real transitions")
    if plan.planned_steps != EXPECTED_DURATION:
        raise LearningContractError("C2 plan planned duration drifted")
    if len(plan.main_bundle_ids) != duration:
        raise LearningContractError("C2 plan bundle count disagrees with duration")
    if len(plan.main_focal_actions) != duration:
        raise LearningContractError("C2 plan action count disagrees with duration")
    _digest(
        plan.chronology_receipt_sha256,
        field="plan.chronology_receipt_sha256",
    )
    for field in ("anchor_sha256", "reward_source_sha256", "forecast_payload_sha256"):
        if hasattr(certificate, field):
            _digest(getattr(certificate, field), field=f"certificate.{field}")
    _digest(certificate.evidence_sha256, field="certificate.evidence_sha256")
    return plan, certificate


def _plan_admission_digest(
    plan: core.C2ClosedOptionPlan,
    certificate: core.TemporalForkCertificate,
) -> str:
    return _json_digest(
        {
            "version": plan.version,
            "option_id": plan.option_id,
            "anchor_sha256": plan.anchor_sha256,
            "evidence_sha256": certificate.evidence_sha256,
            "chronology_receipt_sha256": plan.chronology_receipt_sha256,
            "objective_index": plan.objective_index,
            "focal_user": plan.focal_user,
            "action": plan.action,
            "discount_factor": _float_hex(plan.discount_factor),
            "main_source_unit_id": plan.main_source_unit_id,
            "main_bundle_ids": plan.main_bundle_ids,
            "main_focal_actions": plan.main_focal_actions,
            "main_reward_matrix_sha256": plan.main_reward_matrix_sha256,
            "main_r2_column_sha256": plan.main_r2_column_sha256,
            "opening_state_sha256": plan.opening_state_sha256,
            "bootstrap_state_sha256": plan.bootstrap_state_sha256,
            "bootstrap_mask_sha256": plan.bootstrap_mask_sha256,
            "executed_steps": plan.executed_steps,
            "planned_steps": plan.planned_steps,
            "release_offset": plan.release_offset,
            "release_reason": plan.release_reason,
            "horizon_steps": plan.horizon_steps,
            "complete_hold_and_release": plan.complete_hold_and_release,
            "realised_focal_service_all": plan.realised_focal_service_all,
            "realised_served_by_step": plan.realised_served_by_step,
            "environment_terminal": plan.environment_terminal,
            "admitted": plan.admitted,
            "disposition": plan.disposition,
        }
    )


def _admission_proof(
    plan: core.C2ClosedOptionPlan,
    certificate: core.TemporalForkCertificate,
) -> C2AdmissionProof:
    plan, certificate = _assert_admitted(plan, certificate)
    plan_sha256 = _plan_admission_digest(plan, certificate)
    chronology_sha256 = _digest(
        plan.chronology_receipt_sha256,
        field="plan.chronology_receipt_sha256",
    )
    payload = {
        "admitted": True,
        "option_id": plan.option_id,
        "evidence_sha256": certificate.evidence_sha256,
        "chronology_receipt_sha256": chronology_sha256,
        "plan_sha256": plan_sha256,
    }
    return C2AdmissionProof(
        admitted=True,
        option_id=plan.option_id,
        evidence_sha256=certificate.evidence_sha256,
        chronology_receipt_sha256=chronology_sha256,
        plan_sha256=plan_sha256,
        proof_sha256=_json_digest(payload),
        _seal=_ADMISSION_SEAL,
    )


def _validate_admission_binding(
    proof: object,
    *,
    admitted: object,
    option_id: str,
    evidence_sha256: str,
    chronology_receipt_sha256: str,
) -> C2AdmissionProof:
    if admitted is not True:
        raise LearningContractError("C2 learning item is not admitted")
    if not isinstance(proof, C2AdmissionProof):
        raise LearningContractError("C2 learning item lacks an admission proof")
    if proof._seal is not _ADMISSION_SEAL or proof.admitted is not True:
        raise LearningContractError("C2 learning admission proof is not sealed")
    if proof.option_id != option_id:
        raise LearningContractError("C2 learning admission option_id disagrees")
    if proof.evidence_sha256 != evidence_sha256:
        raise LearningContractError("C2 learning admission evidence disagrees")
    if proof.chronology_receipt_sha256 != chronology_receipt_sha256:
        raise LearningContractError("C2 learning admission chronology disagrees")
    return proof


def assert_admission_bound(item: object) -> C2AdmissionProof:
    """Fail closed unless a transition/sequence carries sealed admission."""

    for name in (
        "admission_proof",
        "admitted",
        "option_id",
        "evidence_sha256",
        "chronology_receipt_sha256",
        "selection_receipt_sha256",
    ):
        if not hasattr(item, name):
            raise LearningContractError(f"C2 learning item lacks {name}")
    _digest(
        getattr(item, "selection_receipt_sha256"),
        field="selection_receipt_sha256",
    )
    return _validate_admission_binding(
        getattr(item, "admission_proof"),
        admitted=getattr(item, "admitted"),
        option_id=getattr(item, "option_id"),
        evidence_sha256=getattr(item, "evidence_sha256"),
        chronology_receipt_sha256=getattr(item, "chronology_receipt_sha256"),
    )


def _validate_vector(
    value: object, *, field: str, boolean: bool = False
) -> np.ndarray:
    array = _immutable_array(value, field=field)
    if array.ndim != 1 or array.size == 0:
        raise LearningContractError(f"{field} must be a nonempty one-dimensional array")
    if boolean and array.dtype != np.bool_:
        raise LearningContractError(f"{field} must have Boolean dtype")
    if not boolean and not np.all(np.isfinite(array)):
        raise LearningContractError(f"{field} must be finite")
    return array


def _validate_action(action: object, mask: np.ndarray, *, field: str) -> int:
    normalized = _exact_int(action, field=field)
    if normalized >= mask.size:
        raise LearningContractError(f"{field} lies outside its mask")
    if not bool(mask[normalized]):
        raise LearningContractError(f"{field} is false under the opening mask")
    return normalized


def _transition_digest(
    *,
    source_unit_id: str,
    option_id: str,
    anchor_sha256: str,
    evidence_sha256: str,
    chronology_receipt_sha256: str,
    selection_receipt_sha256: str,
    admission_proof_sha256: str,
    admitted: bool,
    focal_user: int,
    opening_state_sha256: str,
    opening_mask_sha256: str,
    bootstrap_state_sha256: str,
    bootstrap_mask_sha256: str,
    action: int,
    r2_rewards: Sequence[float],
    option_return: float,
    bootstrap_discount: float,
    discount_factor: float,
    terminal: bool,
    duration: int,
) -> str:
    return _json_digest(
        {
            "source_unit_id": source_unit_id,
            "option_id": option_id,
            "anchor_sha256": anchor_sha256,
            "evidence_sha256": evidence_sha256,
            "chronology_receipt_sha256": chronology_receipt_sha256,
            "selection_receipt_sha256": selection_receipt_sha256,
            "admission_proof_sha256": admission_proof_sha256,
            "admitted": admitted,
            "focal_user": focal_user,
            "opening_state_sha256": opening_state_sha256,
            "opening_mask_sha256": opening_mask_sha256,
            "bootstrap_state_sha256": bootstrap_state_sha256,
            "bootstrap_mask_sha256": bootstrap_mask_sha256,
            "action": action,
            "r2_rewards": [_float_hex(value) for value in r2_rewards],
            "option_return": _float_hex(option_return),
            "bootstrap_discount": _float_hex(bootstrap_discount),
            "discount_factor": _float_hex(discount_factor),
            "terminal": terminal,
            "duration": duration,
        }
    )


@dataclass(frozen=True)
class C2SMDPTransition:
    """One admitted private Q2F SMDP transition.

    ``option_return`` is the raw canonical-r2 return.  Calibration, when
    enabled by the caller, is applied exactly once by :func:`c2_smdp_target`.
    """

    objective_index: int
    source_id: str
    source_unit_id: str
    option_id: str
    anchor_sha256: str
    evidence_sha256: str
    chronology_receipt_sha256: str
    selection_receipt_sha256: str
    admitted: bool
    admission_proof: C2AdmissionProof
    reward_source_sha256: str
    focal_user: int
    opening_state: np.ndarray
    opening_mask: np.ndarray
    action: int
    r2_rewards: tuple[float, ...]
    option_return: float
    bootstrap_state: np.ndarray
    bootstrap_mask: np.ndarray
    bootstrap_discount: float
    discount_factor: float
    terminal: bool
    duration: int
    sequence_sha256: str

    def __post_init__(self) -> None:
        if self.objective_index != C2_OBJECTIVE_INDEX:
            raise LearningContractError("C2SMDPTransition is Q2-only (objective 1)")
        if self.source_id != "C2":
            raise LearningContractError("C2SMDPTransition source must be C2")
        for field in (
            "source_unit_id",
            "option_id",
            "anchor_sha256",
            "evidence_sha256",
            "chronology_receipt_sha256",
            "selection_receipt_sha256",
            "reward_source_sha256",
        ):
            if field in {"source_unit_id", "option_id"}:
                if not isinstance(getattr(self, field), str) or not getattr(self, field):
                    raise LearningContractError(f"{field} must be nonempty")
            else:
                _digest(getattr(self, field), field=field)
        if self.source_unit_id != self.option_id:
            raise LearningContractError("C2 source unit must equal option_id")
        proof = _validate_admission_binding(
            self.admission_proof,
            admitted=self.admitted,
            option_id=self.option_id,
            evidence_sha256=self.evidence_sha256,
            chronology_receipt_sha256=self.chronology_receipt_sha256,
        )
        focal_user = _exact_int(self.focal_user, field="focal_user")
        opening_state = _validate_vector(self.opening_state, field="opening_state")
        opening_mask = _validate_vector(
            self.opening_mask, field="opening_mask", boolean=True
        )
        bootstrap_state = _validate_vector(
            self.bootstrap_state, field="bootstrap_state"
        )
        bootstrap_mask = _validate_vector(
            self.bootstrap_mask, field="bootstrap_mask", boolean=True
        )
        action = _validate_action(self.action, opening_mask, field="action")
        duration = _exact_int(self.duration, field="duration")
        if not 1 <= duration <= EXPECTED_DURATION:
            raise LearningContractError(
                f"duration must lie in [1,H+1={EXPECTED_DURATION}]"
            )
        gamma = _finite(self.discount_factor, field="discount_factor")
        if not 0.0 <= gamma <= 1.0:
            raise LearningContractError("discount_factor must lie in [0,1]")
        if opening_state.shape != bootstrap_state.shape:
            raise LearningContractError("opening and bootstrap state widths disagree")
        if opening_mask.shape != bootstrap_mask.shape:
            raise LearningContractError("opening and bootstrap action widths disagree")
        if type(self.terminal) is not bool:
            raise LearningContractError("terminal must be Boolean")
        rewards = tuple(
            _finite(value, field=f"r2_rewards[{index}]")
            for index, value in enumerate(self.r2_rewards)
        )
        if len(rewards) != duration:
            raise LearningContractError(
                "r2_rewards count must equal the realised option duration"
            )
        if any(value not in core.CANONICAL_R2_VALUES for value in rewards):
            raise LearningContractError("r2_rewards must remain canonical")
        option_return = _finite(self.option_return, field="option_return")
        expected_return = math.fsum(
            (gamma**index) * value for index, value in enumerate(rewards)
        )
        if not math.isclose(
            option_return, expected_return, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise LearningContractError("option_return disagrees with canonical r2 rewards")
        bootstrap_discount = _finite(
            self.bootstrap_discount, field="bootstrap_discount"
        )
        expected_discount = 0.0
        if not math.isclose(
            bootstrap_discount, expected_discount, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise LearningContractError(
                "fixed-window Q2F regression must have zero bootstrap"
            )
        _digest(self.sequence_sha256, field="sequence_sha256")
        expected_sequence = _transition_digest(
            source_unit_id=self.source_unit_id,
            option_id=self.option_id,
            anchor_sha256=self.anchor_sha256,
            evidence_sha256=self.evidence_sha256,
            chronology_receipt_sha256=self.chronology_receipt_sha256,
            selection_receipt_sha256=self.selection_receipt_sha256,
            admission_proof_sha256=proof.proof_sha256,
            admitted=True,
            focal_user=focal_user,
            opening_state_sha256=array_sha256(opening_state),
            opening_mask_sha256=array_sha256(opening_mask),
            bootstrap_state_sha256=array_sha256(bootstrap_state),
            bootstrap_mask_sha256=array_sha256(bootstrap_mask),
            action=action,
            r2_rewards=rewards,
            option_return=option_return,
            bootstrap_discount=bootstrap_discount,
            discount_factor=gamma,
            terminal=self.terminal,
            duration=duration,
        )
        if self.sequence_sha256 != expected_sequence:
            raise LearningContractError("sequence_sha256 does not match transition payload")
        object.__setattr__(self, "focal_user", focal_user)
        object.__setattr__(self, "opening_state", opening_state)
        object.__setattr__(self, "opening_mask", opening_mask)
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "r2_rewards", rewards)
        object.__setattr__(self, "option_return", option_return)
        object.__setattr__(self, "bootstrap_state", bootstrap_state)
        object.__setattr__(self, "bootstrap_mask", bootstrap_mask)
        object.__setattr__(self, "bootstrap_discount", bootstrap_discount)
        object.__setattr__(self, "discount_factor", gamma)
        object.__setattr__(self, "duration", duration)

    @classmethod
    def from_plan(
        cls,
        plan: object,
        certificate: object,
        *,
        opening_state: object,
        opening_mask: object,
        bootstrap_state: object,
        bootstrap_mask: object,
        reward_matrices: Sequence[Sequence[Sequence[float]]],
        discount_factor: float,
        terminal: bool,
        selection_receipt_sha256: str,
    ) -> "C2SMDPTransition":
        plan, certificate = _assert_admitted(plan, certificate)
        admission_proof = _admission_proof(plan, certificate)
        selection_digest = _digest(
            selection_receipt_sha256,
            field="selection_receipt_sha256",
        )
        gamma = _finite(discount_factor, field="discount_factor")
        if not 0.0 <= gamma <= 1.0:
            raise LearningContractError("discount_factor must lie in [0,1]")
        if hasattr(plan, "discount_factor"):
            plan_gamma = _finite(plan.discount_factor, field="plan.discount_factor")
            if not math.isclose(
                gamma, plan_gamma, rel_tol=1e-12, abs_tol=1e-12
            ):
                raise LearningContractError(
                    "configured discount_factor disagrees with the admitted plan"
                )
        opening_state_array = _validate_vector(
            opening_state, field="opening_state"
        )
        opening_mask_array = _validate_vector(
            opening_mask, field="opening_mask", boolean=True
        )
        bootstrap_state_array = _validate_vector(
            bootstrap_state, field="bootstrap_state"
        )
        bootstrap_mask_array = _validate_vector(
            bootstrap_mask, field="bootstrap_mask", boolean=True
        )
        _require_digest_match(
            array_sha256(opening_state_array),
            certificate.opening_state_sha256,
            field="opening_state",
        )
        _require_digest_match(
            array_sha256(opening_mask_array),
            certificate.opening_mask_sha256,
            field="opening_mask",
        )
        if plan.opening_state_sha256 != certificate.opening_state_sha256:
            raise LearningContractError("plan opening state hash disagrees with certificate")
        if plan.bootstrap_state_sha256 is None or plan.bootstrap_mask_sha256 is None:
            raise LearningContractError("admitted plan lacks bootstrap hashes")
        _require_digest_match(
            array_sha256(bootstrap_state_array),
            plan.bootstrap_state_sha256,
            field="bootstrap_state",
        )
        _require_digest_match(
            array_sha256(bootstrap_mask_array),
            plan.bootstrap_mask_sha256,
            field="bootstrap_mask",
        )
        action = _validate_action(
            plan.action, opening_mask_array, field="candidate_action"
        )
        duration = int(plan.executed_steps)
        if len(reward_matrices) != duration:
            raise LearningContractError(
                "reward_matrices count must equal the realised option duration"
            )
        if plan.specialist_option_return is None:
            raise LearningContractError("admitted plan lacks specialist option return")
        if plan.specialist_bootstrap_discount is None:
            raise LearningContractError("admitted plan lacks specialist bootstrap discount")

        focal_rewards: list[float] = []
        for index, matrix_value in enumerate(reward_matrices):
            matrix, matrix_hash, r2_hash = _reward_hashes(
                matrix_value, field=f"reward_matrices[{index}]"
            )
            if matrix_hash != plan.main_reward_matrix_sha256[index]:
                raise LearningContractError(
                    f"reward matrix hash disagrees at offset {index}"
                )
            if r2_hash != plan.main_r2_column_sha256[index]:
                raise LearningContractError(
                    f"r2 column hash disagrees at offset {index}"
                )
            if certificate.focal_user >= len(matrix):
                raise LearningContractError("reward matrix lacks focal user")
            focal_rewards.append(matrix[certificate.focal_user][C2_OBJECTIVE_INDEX])
        raw_return = math.fsum(
            (gamma**index) * reward
            for index, reward in enumerate(focal_rewards)
        )
        if not math.isclose(
            raw_return,
            float(plan.specialist_option_return),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise LearningContractError("plan option return disagrees with reward matrices")
        if type(terminal) is not bool:
            raise LearningContractError("terminal must be Boolean")
        if terminal != bool(plan.environment_terminal):
            raise LearningContractError(
                "terminal flag disagrees with the admitted realised outcome"
            )
        expected_bootstrap = 0.0
        if not math.isclose(
            expected_bootstrap,
            float(plan.specialist_bootstrap_discount),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise LearningContractError(
                "plan bootstrap discount must be zero for fixed-window regression"
            )
        sequence_sha256 = _transition_digest(
            source_unit_id=plan.main_source_unit_id or plan.option_id,
            option_id=plan.option_id,
            anchor_sha256=plan.anchor_sha256,
            evidence_sha256=certificate.evidence_sha256,
            chronology_receipt_sha256=admission_proof.chronology_receipt_sha256,
            selection_receipt_sha256=selection_digest,
            admission_proof_sha256=admission_proof.proof_sha256,
            admitted=True,
            focal_user=certificate.focal_user,
            opening_state_sha256=array_sha256(opening_state_array),
            opening_mask_sha256=array_sha256(opening_mask_array),
            bootstrap_state_sha256=array_sha256(bootstrap_state_array),
            bootstrap_mask_sha256=array_sha256(bootstrap_mask_array),
            action=action,
            r2_rewards=focal_rewards,
            option_return=float(plan.specialist_option_return),
            bootstrap_discount=float(plan.specialist_bootstrap_discount),
            discount_factor=gamma,
            terminal=terminal,
            duration=duration,
        )
        return cls(
            objective_index=C2_OBJECTIVE_INDEX,
            source_id="C2",
            source_unit_id=plan.main_source_unit_id or plan.option_id,
            option_id=plan.option_id,
            anchor_sha256=plan.anchor_sha256,
            evidence_sha256=certificate.evidence_sha256,
            chronology_receipt_sha256=admission_proof.chronology_receipt_sha256,
            selection_receipt_sha256=selection_digest,
            admitted=True,
            admission_proof=admission_proof,
            reward_source_sha256=certificate.reward_source_sha256,
            focal_user=certificate.focal_user,
            opening_state=opening_state_array,
            opening_mask=opening_mask_array,
            action=action,
            r2_rewards=tuple(focal_rewards),
            option_return=float(plan.specialist_option_return),
            bootstrap_state=bootstrap_state_array,
            bootstrap_mask=bootstrap_mask_array,
            bootstrap_discount=float(plan.specialist_bootstrap_discount),
            discount_factor=gamma,
            terminal=terminal,
            duration=duration,
            sequence_sha256=sequence_sha256,
        )


def c2_smdp_target(
    transition: C2SMDPTransition,
    bootstrap_q_values: Sequence[float] | np.ndarray,
    *,
    reward_calibration_enabled: bool = False,
    reward_calibration_scale: float = 1.0,
) -> float:
    """Compute the private Q2F target without a second discount or scaling."""

    if not isinstance(transition, C2SMDPTransition):
        raise LearningContractError("transition must be C2SMDPTransition")
    assert_admission_bound(transition)
    q_values = np.asarray(bootstrap_q_values, dtype=np.float64)
    if q_values.ndim != 1 or q_values.shape != transition.bootstrap_mask.shape:
        raise LearningContractError("bootstrap Q values must match bootstrap mask")
    if not np.all(np.isfinite(q_values)):
        raise LearningContractError("bootstrap Q values must be finite")
    if type(reward_calibration_enabled) is not bool:
        raise LearningContractError("reward_calibration_enabled must be Boolean")
    scale = _finite(reward_calibration_scale, field="reward_calibration_scale")
    if scale <= 0.0:
        raise LearningContractError("reward_calibration_scale must be positive")
    calibrated_return = (
        transition.option_return / scale
        if reward_calibration_enabled
        else transition.option_return
    )
    # The immediate post-release mask is an ordinary action mask, not a
    # certified next-C2-option support.  The frozen V0.3 target is therefore
    # a finite-window return regression with no max-Q bootstrap.
    target = calibrated_return
    if not math.isfinite(target):
        raise LearningContractError("C2 SMDP target must be finite")
    return float(target)


@dataclass(frozen=True)
class _ConstituentSummary:
    bundle_id: str
    source_id: str
    option_id: str
    anchor_sha256: str
    evidence_sha256: str
    selection_receipt_sha256: str
    focal_user: int
    block_id: int
    source_policy_version: int
    offset: int
    environment_step_index: int
    phase: str
    state_sha256: str
    state_mask_sha256: str
    next_state_sha256: str
    next_mask_sha256: str
    reward_matrix_sha256: str
    r2_column_sha256: str
    done: bool
    focal_action: int
    focal_behavior_probability: float | None
    served: tuple[bool, ...]
    reward_source_sha256: str
    release_offset: int
    release_reason: str
    held_key_match_count: int | None
    c2_policy_version: str | None


def _constituent_summary(bundle: object) -> _ConstituentSummary:
    source_id = _metadata_required(bundle, "source_id")
    if source_id != "C2":
        raise LearningContractError("C2 sequence constituent source must be C2")
    bundle_id = _metadata_required(bundle, "bundle_id")
    if not isinstance(bundle_id, str) or not bundle_id:
        raise LearningContractError("constituent bundle_id must be nonempty")
    option_id = _metadata_required(bundle, "option_id")
    anchor_sha256 = _metadata_required(bundle, "anchor_sha256")
    evidence_sha256 = _metadata_required(bundle, "evidence_sha256")
    selection_receipt_sha256 = _metadata_required(
        bundle, "selection_receipt_sha256"
    )
    if not isinstance(option_id, str) or not option_id:
        raise LearningContractError("constituent option_id must be nonempty")
    _digest(anchor_sha256, field="constituent.anchor_sha256")
    _digest(evidence_sha256, field="constituent.evidence_sha256")
    _digest(
        selection_receipt_sha256,
        field="constituent.selection_receipt_sha256",
    )
    focal_user = _exact_int(
        _metadata_required(bundle, "focal_user"), field="constituent.focal_user"
    )
    block_id = _exact_int(
        _metadata_required(bundle, "block_id"), field="constituent.block_id"
    )
    source_policy_version = _exact_int(
        _metadata_required(bundle, "source_policy_version"),
        field="constituent.source_policy_version",
    )
    c2_policy_version = _metadata(bundle, "c2_policy_version")
    if c2_policy_version is not None:
        if (
            not isinstance(c2_policy_version, str)
            or c2_policy_version != core.CANDIDATE_VERSION
        ):
            raise LearningContractError(
                "constituent c2_policy_version is not the active V0.3B policy"
            )
    states = np.asarray(_metadata_required(bundle, "states"))
    actions = np.asarray(_metadata_required(bundle, "actions"))
    rewards = _metadata_required(bundle, "rewards")
    next_states = np.asarray(_metadata_required(bundle, "next_states"))
    masks = np.asarray(_metadata_required(bundle, "masks"))
    next_masks = np.asarray(_metadata_required(bundle, "next_masks"))
    if states.ndim != 2 or next_states.shape != states.shape:
        raise LearningContractError("constituent states must share shape (U,D)")
    users = states.shape[0]
    if not 0 <= focal_user < users:
        raise LearningContractError("constituent focal_user is outside states")
    if actions.shape != (users,):
        raise LearningContractError("constituent actions must have shape (U,)")
    if masks.ndim != 2 or masks.shape[0] != users or next_masks.shape != masks.shape:
        raise LearningContractError("constituent masks must share shape (U,A)")
    if masks.dtype != np.bool_ or next_masks.dtype != np.bool_:
        raise LearningContractError("constituent masks must be Boolean")
    if not np.all(np.isfinite(states)) or not np.all(np.isfinite(next_states)):
        raise LearningContractError("constituent states must be finite")
    focal_action = _exact_int(
        int(actions[focal_user]), field="constituent.focal_action"
    )
    if not 0 <= focal_action < masks.shape[1] or not bool(masks[focal_user, focal_action]):
        raise LearningContractError("constituent focal action is invalid under its mask")
    _, matrix_hash, r2_hash = _reward_hashes(rewards, field="constituent.rewards")
    state_hash = array_sha256(states[focal_user])
    state_mask_hash = array_sha256(masks[focal_user])
    next_state_hash = array_sha256(next_states[focal_user])
    next_mask_hash = array_sha256(next_masks[focal_user])
    supplied_hashes = {
        "state_sha256": state_hash,
        "state_mask_sha256": state_mask_hash,
        "next_state_sha256": next_state_hash,
        "next_mask_sha256": next_mask_hash,
        "reward_matrix_sha256": matrix_hash,
        "r2_column_sha256": r2_hash,
    }
    for name, actual in supplied_hashes.items():
        supplied = _metadata(bundle, name)
        if supplied is not None:
            _require_digest_match(actual, supplied, field=f"constituent.{name}")
    offset_value = _metadata(bundle, "offset")
    if offset_value is None:
        raise LearningContractError("C2 constituent lacks option-relative offset")
    offset = _exact_int(offset_value, field="constituent.offset")
    raw_step_index = getattr(bundle, "step_index", None)
    if raw_step_index is None:
        raise LearningContractError("C2 constituent lacks environment step_index")
    environment_step_index = _exact_int(
        raw_step_index, field="constituent.step_index"
    )
    claimed_step_index = _metadata(bundle, "environment_step_index")
    if claimed_step_index is not None and _exact_int(
        claimed_step_index, field="constituent.environment_step_index"
    ) != environment_step_index:
        raise LearningContractError(
            "constituent environment_step_index disagrees with AtomicBundle"
        )
    raw_release_offset = _metadata(bundle, "release_offset")
    raw_release_reason = _metadata(bundle, "release_reason")
    if (raw_release_offset is None) != (raw_release_reason is None):
        raise LearningContractError(
            "constituent release_offset and release_reason must be supplied together"
        )
    if raw_release_offset is None:
        if c2_policy_version is not None:
            raise LearningContractError(
                "V0.3B constituent with a policy version lacks release metadata"
            )
        # Hand-built pre-V0.3B fixtures have no row policy metadata.  Treat
        # those rows as the old planned-horizon sequence only for compatibility
        # with unrelated learning-seam tests; generated V0.3B rows always bind
        # the explicit policy and therefore do not use this fallback.
        release_offset, release_reason, _ = core._release_policy(  # type: ignore[attr-defined]
            release_offset=core.HORIZON_STEPS,
            release_reason="horizon",
            horizon_steps=core.HORIZON_STEPS,
            field_prefix="constituent",
        )
    else:
        if c2_policy_version != core.CANDIDATE_VERSION:
            raise LearningContractError(
                "V0.3B constituent release metadata lacks active policy version"
            )
        try:
            release_offset, release_reason, _ = core._release_policy(  # type: ignore[attr-defined]
                release_offset=raw_release_offset,
                release_reason=raw_release_reason,
                horizon_steps=core.HORIZON_STEPS,
                field_prefix="constituent",
            )
        except core.C2ContractError as error:
            raise LearningContractError("constituent release policy is malformed") from error
    expected_phase = "hold" if offset < release_offset else "release"
    phase_value = _metadata(bundle, "phase")
    phase = expected_phase if phase_value is None else phase_value
    if phase != expected_phase:
        raise LearningContractError("constituent phase disagrees with offset")
    held_key_value = _metadata(bundle, "held_physical_key")
    held_count_value = _metadata(bundle, "held_key_match_count")
    if (held_key_value is None) != (held_count_value is None):
        raise LearningContractError(
            "constituent held_physical_key and held_key_match_count must be supplied together"
        )
    held_key_match_count: int | None = None
    if held_key_value is not None:
        try:
            core._physical_key(  # type: ignore[attr-defined]
                tuple(held_key_value), field="constituent.held_physical_key"
            )
        except (TypeError, core.C2ContractError) as error:
            raise LearningContractError("constituent held_physical_key is malformed") from error
        held_key_match_count = _exact_int(
            held_count_value, field="constituent.held_key_match_count"
        )
        if offset < release_offset and held_key_match_count != 1:
            raise LearningContractError(
                "a held constituent must have exactly one support match"
            )
        if (
            offset == release_offset
            and release_reason == "support_expired"
            and held_key_match_count == 1
        ):
            raise LearningContractError(
                "support-expired release constituent still has a unique support match"
            )
    done_value = _metadata(bundle, "done")
    if type(done_value) is not bool:
        raise LearningContractError("constituent done must be Boolean")
    probability_value = _metadata(bundle, "behavior_probability")
    behavior_probabilities = getattr(bundle, "behavior_probabilities", None)
    array_probability: float | None = None
    if probability_value is None and behavior_probabilities is not None:
        probabilities = np.asarray(behavior_probabilities)
        if probabilities.shape == (users,):
            probability_value = probabilities[focal_user]
    elif behavior_probabilities is not None:
        probabilities = np.asarray(behavior_probabilities)
        if probabilities.shape == (users,):
            array_probability = _finite(
                probabilities[focal_user],
                field="constituent.behavior_probabilities[focal_user]",
            )
    probability = None
    if probability_value is not None:
        probability = _finite(
            probability_value, field="constituent.behavior_probability"
        )
        if not 0.0 <= probability <= 1.0:
            raise LearningContractError(
                "constituent.behavior_probability must lie in [0,1]"
            )
    if array_probability is not None and probability is not None and not math.isclose(
        array_probability, probability, rel_tol=1e-12, abs_tol=1e-12
    ):
        raise LearningContractError(
            "constituent behavior probability disagrees with its array payload"
        )
    served_value = _metadata_required(bundle, "focal_served")
    if type(served_value) is not bool:
        raise LearningContractError("constituent focal_served authority is malformed")
    raw_served = _metadata_required(bundle, "served")
    if (
        isinstance(raw_served, (str, bytes))
        or not isinstance(raw_served, Sequence)
    ):
        raise LearningContractError("constituent served authority is malformed")
    served = tuple(raw_served)
    if len(served) != users or any(type(value) is not bool for value in served):
        raise LearningContractError(
            "constituent served must contain one Boolean per user"
        )
    if served[focal_user] != served_value:
        raise LearningContractError(
            "constituent focal service disagrees with full served vector"
        )
    reward_source_value = _metadata_required(bundle, "reward_source_sha256")
    reward_source_sha256 = _digest(
        reward_source_value, field="constituent.reward_source_sha256"
    )
    return _ConstituentSummary(
        bundle_id=bundle_id,
        source_id=source_id,
        option_id=option_id,
        anchor_sha256=anchor_sha256,
        evidence_sha256=evidence_sha256,
        selection_receipt_sha256=selection_receipt_sha256,
        focal_user=focal_user,
        block_id=block_id,
        source_policy_version=source_policy_version,
        offset=offset,
        environment_step_index=environment_step_index,
        phase=phase,
        state_sha256=state_hash,
        state_mask_sha256=state_mask_hash,
        next_state_sha256=next_state_hash,
        next_mask_sha256=next_mask_hash,
        reward_matrix_sha256=matrix_hash,
        r2_column_sha256=r2_hash,
        done=done_value,
        focal_action=focal_action,
        focal_behavior_probability=probability,
        served=served,
        reward_source_sha256=reward_source_sha256,
        release_offset=release_offset,
        release_reason=release_reason,
        held_key_match_count=held_key_match_count,
        c2_policy_version=c2_policy_version,
    )


def _sequence_digest(
    *,
    source_unit_id: str,
    option_id: str,
    anchor_sha256: str,
    evidence_sha256: str,
    chronology_receipt_sha256: str,
    selection_receipt_sha256: str,
    admission_proof_sha256: str,
    admitted: bool,
    focal_user: int,
    summaries: Sequence[_ConstituentSummary],
) -> str:
    return _json_digest(
        {
            "source_unit_id": source_unit_id,
            "option_id": option_id,
            "anchor_sha256": anchor_sha256,
            "evidence_sha256": evidence_sha256,
            "chronology_receipt_sha256": chronology_receipt_sha256,
            "selection_receipt_sha256": selection_receipt_sha256,
            "admission_proof_sha256": admission_proof_sha256,
            "admitted": admitted,
            "focal_user": focal_user,
            "constituents": [
                {
                    "bundle_id": summary.bundle_id,
                    "source_id": summary.source_id,
                    "block_id": summary.block_id,
                    "source_policy_version": summary.source_policy_version,
                    "selection_receipt_sha256": summary.selection_receipt_sha256,
                    "offset": summary.offset,
                    "environment_step_index": summary.environment_step_index,
                    "phase": summary.phase,
                    "state_sha256": summary.state_sha256,
                    "state_mask_sha256": summary.state_mask_sha256,
                    "next_state_sha256": summary.next_state_sha256,
                    "next_mask_sha256": summary.next_mask_sha256,
                    "reward_matrix_sha256": summary.reward_matrix_sha256,
                    "r2_column_sha256": summary.r2_column_sha256,
                    "done": summary.done,
                    "focal_action": summary.focal_action,
                    "focal_behavior_probability": (
                        None
                        if summary.focal_behavior_probability is None
                        else _float_hex(summary.focal_behavior_probability)
                    ),
                    "served": summary.served,
                    "reward_source_sha256": summary.reward_source_sha256,
                    "release_offset": summary.release_offset,
                    "release_reason": summary.release_reason,
                    "held_key_match_count": summary.held_key_match_count,
                    "c2_policy_version": summary.c2_policy_version,
                }
                for summary in summaries
            ],
        }
    )


@dataclass(frozen=True)
class C2PrimitiveSequence:
    """One to four real C2 receipts represented as one Main source unit."""

    source_id: str
    source_unit_id: str
    option_id: str
    anchor_sha256: str
    evidence_sha256: str
    chronology_receipt_sha256: str
    selection_receipt_sha256: str
    admitted: bool
    admission_proof: C2AdmissionProof
    focal_user: int
    transitions: tuple[object, ...]
    sequence_sha256: str

    def __post_init__(self) -> None:
        if self.source_id != "C2":
            raise LearningContractError("C2PrimitiveSequence source must be C2")
        if not isinstance(self.source_unit_id, str) or not self.source_unit_id:
            raise LearningContractError("sequence source_unit_id must be nonempty")
        if not isinstance(self.option_id, str) or not self.option_id:
            raise LearningContractError("sequence option_id must be nonempty")
        if self.source_unit_id != self.option_id:
            raise LearningContractError("C2 source unit must equal option_id")
        if not 1 <= len(self.transitions) <= EXPECTED_DURATION:
            raise LearningContractError(
                f"C2PrimitiveSequence must contain 1..{EXPECTED_DURATION} transitions"
            )
        _digest(self.anchor_sha256, field="sequence.anchor_sha256")
        _digest(self.evidence_sha256, field="sequence.evidence_sha256")
        _digest(
            self.chronology_receipt_sha256,
            field="sequence.chronology_receipt_sha256",
        )
        _digest(
            self.selection_receipt_sha256,
            field="sequence.selection_receipt_sha256",
        )
        proof = _validate_admission_binding(
            self.admission_proof,
            admitted=self.admitted,
            option_id=self.option_id,
            evidence_sha256=self.evidence_sha256,
            chronology_receipt_sha256=self.chronology_receipt_sha256,
        )
        focal_user = _exact_int(self.focal_user, field="sequence.focal_user")
        summaries = tuple(_constituent_summary(item) for item in self.transitions)
        if len({(summary.block_id, summary.source_policy_version) for summary in summaries}) != 1:
            raise LearningContractError(
                "C2 constituents must share one source block and policy version"
            )
        release_policies = {
            (summary.release_offset, summary.release_reason) for summary in summaries
        }
        if len(release_policies) != 1:
            raise LearningContractError(
                "C2 constituents must share one monotone release policy"
            )
        if {summary.selection_receipt_sha256 for summary in summaries} != {
            self.selection_receipt_sha256
        }:
            raise LearningContractError(
                "C2 constituents must share the sequence selection receipt"
            )
        if len({summary.bundle_id for summary in summaries}) != len(summaries):
            raise LearningContractError("C2 sequence cannot repeat a bundle_id")
        for index, summary in enumerate(summaries):
            if summary.option_id != self.option_id:
                raise LearningContractError(
                    f"constituent option_id disagrees at offset {index}"
                )
            if summary.anchor_sha256 != self.anchor_sha256:
                raise LearningContractError(
                    f"constituent anchor disagrees at offset {index}"
                )
            if summary.evidence_sha256 != self.evidence_sha256:
                raise LearningContractError(
                    f"constituent evidence disagrees at offset {index}"
                )
            if summary.focal_user != focal_user:
                raise LearningContractError(
                    f"constituent focal user disagrees at offset {index}"
                )
            if summary.offset != index:
                raise LearningContractError("constituent offsets must be contiguous")
            if summary.phase != (
                "hold" if index < summary.release_offset else "release"
            ):
                raise LearningContractError("constituent phase disagrees with offset")
            if summary.done and index != len(summaries) - 1:
                raise LearningContractError(
                    "terminal constituent must be the realised sequence suffix"
                )
        for left, right in zip(summaries, summaries[1:], strict=False):
            if left.next_state_sha256 != right.state_sha256:
                raise LearningContractError("state hash chain is discontinuous")
            if left.next_mask_sha256 != right.state_mask_sha256:
                raise LearningContractError("mask hash chain is discontinuous")
        if len(summaries) < EXPECTED_DURATION and not summaries[-1].done:
            raise LearningContractError(
                "a shortened C2 sequence must end at a real environment terminal"
            )
        expected = _sequence_digest(
            source_unit_id=self.source_unit_id,
            option_id=self.option_id,
            anchor_sha256=self.anchor_sha256,
            evidence_sha256=self.evidence_sha256,
            chronology_receipt_sha256=self.chronology_receipt_sha256,
            selection_receipt_sha256=self.selection_receipt_sha256,
            admission_proof_sha256=proof.proof_sha256,
            admitted=True,
            focal_user=focal_user,
            summaries=summaries,
        )
        if self.sequence_sha256 != expected:
            raise LearningContractError("sequence_sha256 does not match constituents")
        object.__setattr__(self, "focal_user", focal_user)
        object.__setattr__(self, "transitions", tuple(self.transitions))

    @property
    def constituent_bundle_ids(self) -> tuple[str, ...]:
        return tuple(
            str(_metadata_required(item, "bundle_id")) for item in self.transitions
        )

    @property
    def target_objective(self) -> int:
        return target_objective_for_source(self.source_id)

    @classmethod
    def from_plan(
        cls,
        plan: object,
        certificate: object,
        transitions: Sequence[object],
    ) -> "C2PrimitiveSequence":
        plan, certificate = _assert_admitted(plan, certificate)
        admission_proof = _admission_proof(plan, certificate)
        if not 1 <= len(transitions) <= EXPECTED_DURATION:
            raise LearningContractError(
                f"C2 sequence must contain 1..{EXPECTED_DURATION} constituents"
            )
        items = tuple(transitions)
        summaries = tuple(_constituent_summary(item) for item in items)
        if len({(summary.block_id, summary.source_policy_version) for summary in summaries}) != 1:
            raise LearningContractError(
                "C2 constituents must share one source block and policy version"
            )
        release_policies = {
            (summary.release_offset, summary.release_reason) for summary in summaries
        }
        if len(release_policies) != 1:
            raise LearningContractError(
                "C2 constituents must share one monotone release policy"
            )
        release_offset, release_reason = next(iter(release_policies))
        plan_policy = (int(plan.release_offset), str(plan.release_reason))
        certificate_policy = (
            int(certificate.release_offset),
            str(certificate.release_reason),
        )
        if (release_offset, release_reason) not in {
            plan_policy,
            certificate_policy,
        } or plan_policy != certificate_policy:
            raise LearningContractError(
                "constituent release policy disagrees with admitted plan"
            )
        selection_receipts = {
            summary.selection_receipt_sha256 for summary in summaries
        }
        if len(selection_receipts) != 1:
            raise LearningContractError(
                "C2 constituents must share one selection receipt"
            )
        selection_receipt_sha256 = next(iter(selection_receipts))
        expected_ids = tuple(plan.main_bundle_ids)
        actual_ids = tuple(summary.bundle_id for summary in summaries)
        if actual_ids != expected_ids:
            raise LearningContractError("constituent bundle IDs disagree with plan")
        for index, summary in enumerate(summaries):
            if summary.option_id != certificate.option_id:
                raise LearningContractError(
                    f"constituent option_id disagrees at offset {index}"
                )
            if summary.anchor_sha256 != certificate.anchor_sha256:
                raise LearningContractError(
                    f"constituent anchor disagrees at offset {index}"
                )
            if summary.evidence_sha256 != certificate.evidence_sha256:
                raise LearningContractError(
                    f"constituent evidence disagrees at offset {index}"
                )
            if summary.reward_source_sha256 != certificate.reward_source_sha256:
                raise LearningContractError(
                    f"constituent reward source disagrees at offset {index}"
                )
            if summary.served != tuple(plan.realised_served_by_step[index]):
                raise LearningContractError(
                    f"constituent served vector disagrees with plan at offset {index}"
                )
            if summary.focal_user != certificate.focal_user:
                raise LearningContractError(
                    f"constituent focal user disagrees at offset {index}"
                )
            if summary.offset != index:
                raise LearningContractError("constituent offsets must be contiguous")
            expected_action = plan.main_focal_actions[index]
            if summary.focal_action != expected_action:
                raise LearningContractError(
                    f"constituent focal action disagrees at offset {index}"
                )
            if summary.done and index != len(summaries) - 1:
                raise LearningContractError(
                    "terminal constituent must be the realised sequence suffix"
                )
            if index < release_offset and summary.phase != "hold":
                raise LearningContractError("hold constituent phase is malformed")
            if index >= release_offset and summary.phase != "release":
                raise LearningContractError("release constituent phase is malformed")
            if summary.reward_matrix_sha256 != plan.main_reward_matrix_sha256[index]:
                raise LearningContractError(
                    f"reward matrix hash disagrees at offset {index}"
                )
            if summary.r2_column_sha256 != plan.main_r2_column_sha256[index]:
                raise LearningContractError(
                    f"r2 column hash disagrees at offset {index}"
                )
        for left, right in zip(summaries, summaries[1:], strict=False):
            if left.next_state_sha256 != right.state_sha256:
                raise LearningContractError("state hash chain is discontinuous")
            if left.next_mask_sha256 != right.state_mask_sha256:
                raise LearningContractError("mask hash chain is discontinuous")
        if len(summaries) < EXPECTED_DURATION and not summaries[-1].done:
            raise LearningContractError(
                "a shortened C2 sequence must end at a real environment terminal"
            )
        if summaries[0].state_sha256 != certificate.opening_state_sha256:
            raise LearningContractError("opening state hash disagrees with certificate")
        if summaries[0].state_mask_sha256 != certificate.opening_mask_sha256:
            raise LearningContractError("opening mask hash disagrees with certificate")
        if plan.bootstrap_state_sha256 is None or plan.bootstrap_mask_sha256 is None:
            raise LearningContractError("admitted plan lacks bootstrap hashes")
        if summaries[-1].next_state_sha256 != plan.bootstrap_state_sha256:
            raise LearningContractError("bootstrap state hash disagrees with plan")
        if summaries[-1].next_mask_sha256 != plan.bootstrap_mask_sha256:
            raise LearningContractError("bootstrap mask hash disagrees with plan")
        planned_probabilities = getattr(plan, "main_behavior_probabilities", None)
        if planned_probabilities is not None:
            if len(planned_probabilities) != len(summaries):
                raise LearningContractError(
                    "plan behavior-probability count must equal realised duration"
                )
            for index, summary in enumerate(summaries):
                actual = summary.focal_behavior_probability
                if actual is None:
                    raise LearningContractError(
                        "constituent lacks behavior probability required by plan"
                    )
                if not math.isclose(
                    actual,
                    _finite(
                        planned_probabilities[index],
                        field=f"plan.main_behavior_probabilities[{index}]",
                    ),
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ):
                    raise LearningContractError(
                        f"behavior probability disagrees at offset {index}"
                    )
        sequence_sha256 = _sequence_digest(
            source_unit_id=plan.main_source_unit_id or plan.option_id,
            option_id=plan.option_id,
            anchor_sha256=plan.anchor_sha256,
            evidence_sha256=certificate.evidence_sha256,
            chronology_receipt_sha256=admission_proof.chronology_receipt_sha256,
            selection_receipt_sha256=selection_receipt_sha256,
            admission_proof_sha256=admission_proof.proof_sha256,
            admitted=True,
            focal_user=certificate.focal_user,
            summaries=summaries,
        )
        return cls(
            source_id="C2",
            source_unit_id=plan.main_source_unit_id or plan.option_id,
            option_id=plan.option_id,
            anchor_sha256=plan.anchor_sha256,
            evidence_sha256=certificate.evidence_sha256,
            chronology_receipt_sha256=admission_proof.chronology_receipt_sha256,
            selection_receipt_sha256=selection_receipt_sha256,
            admitted=True,
            admission_proof=admission_proof,
            focal_user=certificate.focal_user,
            transitions=items,
            sequence_sha256=sequence_sha256,
        )


def target_objective_for_source(source_id: str) -> int:
    if source_id not in ROLE_TO_OBJECTIVE:
        raise LearningContractError(
            f"source {source_id!r} is not a C1/C2/C3 role source"
        )
    return ROLE_TO_OBJECTIVE[source_id]


def mean_primitive_loss(losses: Sequence[float]) -> float:
    """Reduce one to four real primitive losses to one C2 source-unit loss."""

    if (
        isinstance(losses, (str, bytes))
        or not 1 <= len(losses) <= EXPECTED_DURATION
    ):
        raise LearningContractError(
            f"primitive_losses must contain 1..{EXPECTED_DURATION} values"
        )
    values = tuple(
        _finite(value, field=f"primitive_losses[{index}]")
        for index, value in enumerate(losses)
    )
    result = math.fsum(values) / len(values)
    if not math.isfinite(result):
        raise LearningContractError("primitive loss mean must be finite")
    return float(result)


@dataclass(frozen=True)
class MainQ2BlendReceipt:
    source_id: str
    source_unit_id: str
    target_objective: int
    primitive_count: int
    primitive_loss_mean: float
    beta: float
    effective_beta: float
    unit_weight: float
    main_loss: float
    blended_loss: float
    q1_q3_donor_targets: tuple[int, ...]
    sequence_sha256: str
    constituent_bundle_ids: tuple[str, ...]
    dose_borrowing: bool


def blend_main_q2_single_beta(
    sequence: C2PrimitiveSequence,
    *,
    main_loss: float,
    primitive_losses: Sequence[float],
    beta: float,
) -> MainQ2BlendReceipt:
    """Return the one-dose Main-Q2 blend receipt without updating a network."""

    if not isinstance(sequence, C2PrimitiveSequence):
        raise LearningContractError("sequence must be C2PrimitiveSequence")
    assert_admission_bound(sequence)
    if target_objective_for_source(sequence.source_id) != C2_OBJECTIVE_INDEX:
        raise LearningContractError("C2 sequence cannot target Q1 or Q3")
    main_value = _finite(main_loss, field="main_loss")
    beta_value = _finite(beta, field="beta")
    if not 0.0 <= beta_value < 1.0:
        raise LearningContractError("beta must satisfy 0 <= beta < 1")
    donor_value = mean_primitive_loss(primitive_losses)
    blended = (1.0 - beta_value) * main_value + beta_value * donor_value
    if not math.isfinite(blended):
        raise LearningContractError("blended Main-Q2 loss must be finite")
    return MainQ2BlendReceipt(
        source_id="C2",
        source_unit_id=sequence.source_unit_id,
        target_objective=C2_OBJECTIVE_INDEX,
        primitive_count=len(sequence.transitions),
        primitive_loss_mean=donor_value,
        beta=beta_value,
        effective_beta=beta_value,
        unit_weight=1.0,
        main_loss=main_value,
        blended_loss=float(blended),
        q1_q3_donor_targets=(),
        sequence_sha256=sequence.sequence_sha256,
        constituent_bundle_ids=sequence.constituent_bundle_ids,
        dose_borrowing=False,
    )


__all__ = [
    "C2AdmissionProof",
    "C2PrimitiveSequence",
    "C2SMDPTransition",
    "EXPECTED_DURATION",
    "LearningContractError",
    "MainQ2BlendReceipt",
    "ROLE_TO_OBJECTIVE",
    "array_sha256",
    "assert_admission_bound",
    "blend_main_q2_single_beta",
    "c2_smdp_target",
    "mask_sha256",
    "mean_primitive_loss",
    "state_sha256",
    "target_objective_for_source",
]
