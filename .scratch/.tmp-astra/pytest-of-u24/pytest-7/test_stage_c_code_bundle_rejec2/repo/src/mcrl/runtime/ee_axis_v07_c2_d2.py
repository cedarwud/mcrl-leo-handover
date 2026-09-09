"""Pure-data adjudicator for the V0.7 C2 D2 source/formula gate.

The D2 preregistration is deliberately a data boundary.  This module does
not run an environment, evaluate a carrier, call a policy, or train Q2.  A
runner supplies already sealed lineage/decision captures and this module
checks the receipts before computing the five preregistered diagnostics.

The records are intentionally a little verbose.  A D2 result is useful only
when a later reviewer can reconstruct the signed target from the persisted
raw terms and distinguish a source/provenance failure from a scientific gate
failure.  NumPy arrays are copied and made read-only at construction; all
digests use canonical JSON and all floating point values in JSON are encoded
with ``float.hex``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

import numpy as np

from ..env.action_contract import NUM_ACTIONS, NO_OP_ACTION
from ..errors import MCRLContractError
from .ee_axis_v07_c2_focal_next import (
    FocalNextSurplus,
    V07_C2_TARGET_SCHEMA,
    focal_next_surplus_target,
)


D2_SCHEMA = "multi-catfish-mcrl-v07-c2-d2-adjudicator-v2"
D2_SELECTION_SCHEMA = "multi-catfish-mcrl-v07-c2-d2-selection-v1"
D2_ANCHOR_SCHEMA = "multi-catfish-mcrl-v07-c2-d2-physical-anchor-v1"
D2_Q13_SCHEMA = "multi-catfish-mcrl-v07-c2-d2-q13-receipt-v1"
D2_MECHANICS_SCHEMA = "multi-catfish-mcrl-v07-c2-d2-mechanics-v1"
D2_ROW_SCHEMA = "multi-catfish-mcrl-v07-c2-d2-action-row-v1"
D2_CAPTURE_SCHEMA = "multi-catfish-mcrl-v07-c2-d2-lineage-capture-v1"
D2_RESULT_SCHEMA = "multi-catfish-mcrl-v07-c2-d2-result-v2"

D2_PASS_AUTHORIZE_D3_IMPLEMENTATION = "D2_PASS_AUTHORIZE_D3_IMPLEMENTATION"
D2_FAIL_RETURN_TO_C2_FORMULA_OR_SOURCE_DESIGN = (
    "D2_FAIL_RETURN_TO_C2_FORMULA_OR_SOURCE_DESIGN"
)
D2_INVALID_NO_INFERENCE = "D2_INVALID_NO_INFERENCE"
D2_VERDICTS = (
    D2_PASS_AUTHORIZE_D3_IMPLEMENTATION,
    D2_FAIL_RETURN_TO_C2_FORMULA_OR_SOURCE_DESIGN,
    D2_INVALID_NO_INFERENCE,
)

D2_LINEAGES = ("q13-a", "q13-b", "q13-c")
D2_LINEAGE_PAIRS = (("q13-a", "q13-b"), ("q13-a", "q13-c"), ("q13-b", "q13-c"))
D2_SEEDS = tuple(range(2026104001, 2026104011))
D2_EARLY_STEPS = (1, 2)
D2_LATE_STEPS = (5, 6)
D2_EXPECTED_ANCHORS = 20
D2_EXPECTED_CELLS = 60
D2_EXPECTED_ACTIONS_PER_CELL_MIN = 3
D2_G_R_MIN = 0.60
D2_G_S_MAX = 3.0
D2_G_V_MIN_IQR_KAPPA = 0.05
D2_G_V_REQUIRED_CELLS = 30
D2_G_P_REQUIRED_ANCHORS = 6
D2_G_P_REQUIRED_LINEAGES = 2
D2_LAMBDA_BITS_PER_J = float.fromhex("0x1.443a8f481639ap+26")
D2_INTERVAL_S = float.fromhex("0x1.e147ae147ae14p+4")
D2_DEFAULT_KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")
D2_IQR_METHOD = "linear"

_OPENING_POLICY = "bootstrap-direct-q1-plus-zero-q2-plus-q3-masked-argmax"
_TARGET_FIELDS = (
    "z2_focal_next_surplus_bits",
    "focal_next_rate_delta_bits",
    "focal_next_marginal_energy_delta_j",
    "candidate_focal_rate_bps",
    "reference_focal_rate_bps",
    "candidate_focal_marginal_power_w",
    "reference_focal_marginal_power_w",
    "candidate_full_power_w",
    "candidate_without_focal_power_w",
    "reference_full_power_w",
    "reference_without_focal_power_w",
    "lambda_bits_per_j",
    "interval_s",
    "schema",
)


class D2AdjudicatorError(MCRLContractError):
    """A D2 receipt or adjudication input violates the frozen contract."""


def canonical_json_bytes(payload: object) -> bytes:
    """Encode the one canonical JSON representation used by D2 digests."""

    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise D2AdjudicatorError("payload is not canonical finite JSON") from error


def canonical_sha256(payload: object) -> str:
    """Return a lower-case SHA-256 for canonical JSON without a newline."""

    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _exact_int(value: object, *, field: str, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise D2AdjudicatorError(f"{field} must be an exact integer")
    if minimum is not None and value < minimum:
        raise D2AdjudicatorError(f"{field} must be >= {minimum}")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise D2AdjudicatorError(f"{field} must be a nonempty trimmed string")
    return value


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise D2AdjudicatorError(f"{field} must be a lower-case SHA-256 digest")
    return value


def _bool(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise D2AdjudicatorError(f"{field} must be a boolean")
    return value


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise D2AdjudicatorError(f"{field} must be finite")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise D2AdjudicatorError(f"{field} must be finite") from error
    if not math.isfinite(result):
        raise D2AdjudicatorError(f"{field} must be finite")
    return result


def _positive(value: object, *, field: str) -> float:
    result = _finite(value, field=field)
    if result <= 0.0:
        raise D2AdjudicatorError(f"{field} must be strictly positive")
    return result


def _float_hex(value: object, *, field: str = "float") -> str:
    return _finite(value, field=field).hex()


def _readonly_float_vector(value: object, *, field: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.ndim != 1:
        raise D2AdjudicatorError(f"{field} must be a one-dimensional vector")
    try:
        result = np.array(raw, dtype=np.float64, copy=True, order="C")
    except (TypeError, ValueError) as error:
        raise D2AdjudicatorError(f"{field} must be float-compatible") from error
    result.setflags(write=False)
    return result


def _readonly_action_vector(value: object, *, field: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.ndim != 1:
        raise D2AdjudicatorError(f"{field} must be a one-dimensional vector")
    if raw.dtype == np.bool_ or not np.issubdtype(raw.dtype, np.integer):
        raise D2AdjudicatorError(f"{field} must contain integer actions")
    result = np.array(raw, dtype=np.int64, copy=True, order="C")
    result.setflags(write=False)
    return result


def _readonly_native_mask(value: object, *, field: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != (NUM_ACTIONS,) or raw.dtype != np.bool_:
        raise D2AdjudicatorError(
            f"{field} must be boolean shape ({NUM_ACTIONS},), got "
            f"{raw.shape} {raw.dtype}"
        )
    result = np.array(raw, dtype=np.bool_, copy=True, order="C")
    result.setflags(write=False)
    return result


def _legal_actions(mask: np.ndarray) -> tuple[int, ...]:
    return tuple(int(value) for value in np.flatnonzero(mask))


def _target_payload(target: FocalNextSurplus) -> dict[str, object]:
    _strict_target(target)
    return {
        "schema": target.schema,
        **{
            field: _float_hex(getattr(target, field), field=f"target.{field}")
            for field in _TARGET_FIELDS[:-1]
        },
    }


def _target_fields_equal(left: FocalNextSurplus, right: FocalNextSurplus) -> bool:
    return all(getattr(left, field) == getattr(right, field) for field in _TARGET_FIELDS)


def _strict_target(target: object) -> FocalNextSurplus:
    if not isinstance(target, FocalNextSurplus):
        raise D2AdjudicatorError("target must be a FocalNextSurplus receipt")
    if target.schema != V07_C2_TARGET_SCHEMA:
        raise D2AdjudicatorError("target schema is stale")
    for field in _TARGET_FIELDS[:-1]:
        _finite(getattr(target, field), field=f"target.{field}")
    if target.candidate_focal_rate_bps < 0.0 or target.reference_focal_rate_bps < 0.0:
        raise D2AdjudicatorError("focal rates must be non-negative")
    if any(
        getattr(target, field) < 0.0
        for field in (
            "candidate_full_power_w",
            "candidate_without_focal_power_w",
            "reference_full_power_w",
            "reference_without_focal_power_w",
        )
    ):
        raise D2AdjudicatorError("power terms must be non-negative")
    if target.candidate_focal_marginal_power_w != (
        target.candidate_full_power_w - target.candidate_without_focal_power_w
    ):
        raise D2AdjudicatorError("candidate focal marginal power is inconsistent")
    if target.reference_focal_marginal_power_w != (
        target.reference_full_power_w - target.reference_without_focal_power_w
    ):
        raise D2AdjudicatorError("reference focal marginal power is inconsistent")
    reconstructed = focal_next_surplus_target(
        lambda_bits_per_j=target.lambda_bits_per_j,
        interval_s=target.interval_s,
        candidate_focal_rate_bps=target.candidate_focal_rate_bps,
        reference_focal_rate_bps=target.reference_focal_rate_bps,
        candidate_full_power_w=target.candidate_full_power_w,
        candidate_without_focal_power_w=target.candidate_without_focal_power_w,
        reference_full_power_w=target.reference_full_power_w,
        reference_without_focal_power_w=target.reference_without_focal_power_w,
    )
    if not _target_fields_equal(target, reconstructed):
        raise D2AdjudicatorError("stored target does not reconstruct from raw terms")
    return target


@dataclass(frozen=True)
class D2SelectionReceipt:
    """Outcome-blind native-mask scan receipt for one anchor window."""

    window: str
    eligible_users_by_step: tuple[tuple[int, tuple[int, ...]], ...]
    selection_rule: str = "predecision-native-mask-user-id-only"
    outcome_blind: bool = True
    schema: str = D2_SELECTION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != D2_SELECTION_SCHEMA:
            raise D2AdjudicatorError("selection receipt schema is stale")
        object.__setattr__(self, "window", _text(self.window, field="window"))
        entries: list[tuple[int, tuple[int, ...]]] = []
        try:
            raw_entries = tuple(self.eligible_users_by_step)
        except TypeError as error:
            raise D2AdjudicatorError("eligible_users_by_step must be iterable") from error
        for entry in raw_entries:
            if not isinstance(entry, Sequence) or len(entry) != 2:
                raise D2AdjudicatorError("each eligible step entry must be (step, users)")
            step = _exact_int(entry[0], field="eligible step", minimum=0)
            try:
                users = tuple(entry[1])
            except TypeError as error:
                raise D2AdjudicatorError("eligible users must be iterable") from error
            users_tuple = tuple(
                _exact_int(user, field="eligible user", minimum=0) for user in users
            )
            entries.append((step, users_tuple))
        object.__setattr__(self, "eligible_users_by_step", tuple(entries))
        object.__setattr__(self, "selection_rule", _text(self.selection_rule, field="selection_rule"))
        object.__setattr__(self, "outcome_blind", _bool(self.outcome_blind, field="outcome_blind"))

    def verify(self, *, anchor_step: int, focal_user: int) -> None:
        if self.schema != D2_SELECTION_SCHEMA:
            raise D2AdjudicatorError("selection receipt schema is stale")
        expected_steps = D2_EARLY_STEPS if self.window == "early" else D2_LATE_STEPS if self.window == "late" else ()
        if not expected_steps:
            raise D2AdjudicatorError("anchor window is not early or late")
        if anchor_step not in expected_steps:
            raise D2AdjudicatorError("anchor step is outside its frozen window")
        selected_index = expected_steps.index(anchor_step)
        expected_prefix = expected_steps[: selected_index + 1]
        if tuple(step for step, _ in self.eligible_users_by_step) != expected_prefix:
            raise D2AdjudicatorError(
                "selection receipt must stop at the first eligible anchor"
            )
        if self.selection_rule != "predecision-native-mask-user-id-only":
            raise D2AdjudicatorError("selection receipt uses a non-frozen rule")
        if self.outcome_blind is not True:
            raise D2AdjudicatorError("anchor selection must be outcome blind")
        for _, users in self.eligible_users_by_step:
            if tuple(sorted(set(users))) != users:
                raise D2AdjudicatorError("eligible user IDs must be sorted and unique")
        if any(users for _, users in self.eligible_users_by_step[:-1]):
            raise D2AdjudicatorError("an earlier eligible anchor was skipped")
        users = dict(self.eligible_users_by_step)[anchor_step]
        if not users:
            raise D2AdjudicatorError("selected step has no eligible user")
        if focal_user != users[0] or focal_user not in users:
            raise D2AdjudicatorError("anchor user is not the lowest eligible user")

    def to_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "window": self.window,
            "eligible_users_by_step": [
                [step, list(users)] for step, users in self.eligible_users_by_step
            ],
            "selection_rule": self.selection_rule,
            "outcome_blind": self.outcome_blind,
        }


@dataclass(frozen=True)
class D2PhysicalAnchor:
    """One of the twenty outcome-blind physical D2 anchors."""

    seed: int
    step_index: int
    focal_user: int
    window: str
    native_action_mask: np.ndarray
    selection: D2SelectionReceipt
    anchor_sha256: str
    state_sha256: str
    carrier_sha256: str
    schema: str = D2_ANCHOR_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != D2_ANCHOR_SCHEMA:
            raise D2AdjudicatorError("physical anchor schema is stale")
        object.__setattr__(self, "seed", _exact_int(self.seed, field="seed", minimum=0))
        object.__setattr__(self, "step_index", _exact_int(self.step_index, field="step_index", minimum=0))
        object.__setattr__(self, "focal_user", _exact_int(self.focal_user, field="focal_user", minimum=0))
        object.__setattr__(self, "window", _text(self.window, field="window"))
        object.__setattr__(self, "native_action_mask", _readonly_native_mask(self.native_action_mask, field="native_action_mask"))
        if not isinstance(self.selection, D2SelectionReceipt):
            raise D2AdjudicatorError("anchor selection is not a typed receipt")
        object.__setattr__(self, "anchor_sha256", _digest(self.anchor_sha256, field="anchor_sha256"))
        object.__setattr__(self, "state_sha256", _digest(self.state_sha256, field="state_sha256"))
        object.__setattr__(self, "carrier_sha256", _digest(self.carrier_sha256, field="carrier_sha256"))

    @property
    def key(self) -> tuple[int, int, int]:
        return (self.seed, self.step_index, self.focal_user)

    @property
    def legal_actions(self) -> tuple[int, ...]:
        return _legal_actions(self.native_action_mask)

    def verify(self) -> None:
        if self.schema != D2_ANCHOR_SCHEMA:
            raise D2AdjudicatorError("physical anchor schema is stale")
        if self.seed not in D2_SEEDS:
            raise D2AdjudicatorError("physical anchor seed is outside the frozen D2 block")
        if self.window not in ("early", "late"):
            raise D2AdjudicatorError("physical anchor window is invalid")
        if len(self.legal_actions) < D2_EXPECTED_ACTIONS_PER_CELL_MIN:
            raise D2AdjudicatorError("physical anchor mask has fewer than three legal actions")
        self.selection.verify(anchor_step=self.step_index, focal_user=self.focal_user)
        if self.selection.window != self.window:
            raise D2AdjudicatorError("anchor and selection windows differ")
        if self.selection.eligible_users_by_step:
            selected_users = dict(self.selection.eligible_users_by_step)[self.step_index]
            if self.focal_user not in selected_users:
                raise D2AdjudicatorError("focal user is absent from native eligibility receipt")

    def to_payload(self) -> dict[str, object]:
        self.verify()
        return {
            "schema": self.schema,
            "seed": self.seed,
            "step_index": self.step_index,
            "focal_user": self.focal_user,
            "window": self.window,
            "native_action_mask": [bool(value) for value in self.native_action_mask.tolist()],
            "selection": self.selection.to_payload(),
            "anchor_sha256": self.anchor_sha256,
            "state_sha256": self.state_sha256,
            "carrier_sha256": self.carrier_sha256,
        }


@dataclass(frozen=True)
class D2Q13SurfaceReceipt:
    """Frozen Q1/Q3 surfaces and policy/provenance receipt for one lineage."""

    q1_surface: np.ndarray
    q3_surface: np.ndarray
    q1_checkpoint_sha256: str
    q3_checkpoint_sha256: str
    policy_sha256: str
    q1_surface_sha256: str = ""
    q3_surface_sha256: str = ""
    selected_q3_rung: int = 100
    bootstrap_q2_zero: bool = True
    resident_legacy_q2_evaluated: bool = False
    schema: str = D2_Q13_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != D2_Q13_SCHEMA:
            raise D2AdjudicatorError("Q1/Q3 receipt schema is stale")
        q1 = _readonly_float_vector(self.q1_surface, field="q1_surface")
        q3 = _readonly_float_vector(self.q3_surface, field="q3_surface")
        object.__setattr__(self, "q1_surface", q1)
        object.__setattr__(self, "q3_surface", q3)
        object.__setattr__(self, "q1_checkpoint_sha256", _digest(self.q1_checkpoint_sha256, field="q1_checkpoint_sha256"))
        object.__setattr__(self, "q3_checkpoint_sha256", _digest(self.q3_checkpoint_sha256, field="q3_checkpoint_sha256"))
        object.__setattr__(self, "policy_sha256", _digest(self.policy_sha256, field="policy_sha256"))
        if self.q1_surface_sha256:
            object.__setattr__(self, "q1_surface_sha256", _digest(self.q1_surface_sha256, field="q1_surface_sha256"))
        elif np.all(np.isfinite(q1)):
            object.__setattr__(
                self,
                "q1_surface_sha256",
                canonical_sha256({"surface": [_float_hex(value) for value in q1.tolist()]}),
            )
        if self.q3_surface_sha256:
            object.__setattr__(self, "q3_surface_sha256", _digest(self.q3_surface_sha256, field="q3_surface_sha256"))
        elif np.all(np.isfinite(q3)):
            object.__setattr__(
                self,
                "q3_surface_sha256",
                canonical_sha256({"surface": [_float_hex(value) for value in q3.tolist()]}),
            )
        object.__setattr__(self, "selected_q3_rung", _exact_int(self.selected_q3_rung, field="selected_q3_rung", minimum=0))
        object.__setattr__(self, "bootstrap_q2_zero", _bool(self.bootstrap_q2_zero, field="bootstrap_q2_zero"))
        object.__setattr__(self, "resident_legacy_q2_evaluated", _bool(self.resident_legacy_q2_evaluated, field="resident_legacy_q2_evaluated"))

    def verify(self) -> None:
        if self.schema != D2_Q13_SCHEMA:
            raise D2AdjudicatorError("Q1/Q3 receipt schema is stale")
        if self.q1_surface.shape != (NUM_ACTIONS,) or self.q3_surface.shape != (NUM_ACTIONS,):
            raise D2AdjudicatorError("Q1/Q3 surfaces must have the native 28-action shape")
        if not np.all(np.isfinite(self.q1_surface)) or not np.all(np.isfinite(self.q3_surface)):
            raise D2AdjudicatorError("Q1/Q3 surfaces must be finite")
        if not np.all(np.isfinite(self.q1_surface + self.q3_surface)):
            raise D2AdjudicatorError("Q1+Q3 surface must be finite")
        q1_digest = canonical_sha256({"surface": [_float_hex(value) for value in self.q1_surface.tolist()]})
        q3_digest = canonical_sha256({"surface": [_float_hex(value) for value in self.q3_surface.tolist()]})
        if self.q1_surface_sha256 != q1_digest:
            raise D2AdjudicatorError("Q1 surface digest does not match the receipt")
        if self.q3_surface_sha256 != q3_digest:
            raise D2AdjudicatorError("Q3 surface digest does not match the receipt")
        if self.selected_q3_rung != 100:
            raise D2AdjudicatorError("D2 requires the frozen Q3 rung 100")
        if self.bootstrap_q2_zero is not True or self.resident_legacy_q2_evaluated is not False:
            raise D2AdjudicatorError("D2 Q13 receipt evaluated a forbidden Q2 surface")

    @property
    def surface_digests(self) -> tuple[str, str]:
        return (
            canonical_sha256({"surface": [_float_hex(value) for value in self.q1_surface.tolist()]}),
            canonical_sha256({"surface": [_float_hex(value) for value in self.q3_surface.tolist()]}),
        )

    def to_payload(self) -> dict[str, object]:
        self.verify()
        q1_digest, q3_digest = self.surface_digests
        return {
            "schema": self.schema,
            "q1_surface": [_float_hex(value) for value in self.q1_surface.tolist()],
            "q3_surface": [_float_hex(value) for value in self.q3_surface.tolist()],
            "q1_surface_sha256": q1_digest,
            "q3_surface_sha256": q3_digest,
            "q1_checkpoint_sha256": self.q1_checkpoint_sha256,
            "q3_checkpoint_sha256": self.q3_checkpoint_sha256,
            "policy_sha256": self.policy_sha256,
            "selected_q3_rung": self.selected_q3_rung,
            "bootstrap_q2_zero": self.bootstrap_q2_zero,
            "resident_legacy_q2_evaluated": self.resident_legacy_q2_evaluated,
        }


@dataclass(frozen=True)
class D2MechanicsReceipt:
    """Matched branch and provenance receipt attached to one action row."""

    opening_reference_actions: np.ndarray
    opening_candidate_actions: np.ndarray
    successor_reference_action_sha256: str
    successor_candidate_action_sha256: str
    crn_sha256: str
    policy_sha256: str
    reference_branch_local: bool = True
    candidate_branch_local: bool = True
    full_evaluation_noncommitting: bool = True
    without_focal_evaluation_noncommitting: bool = True
    focal_removal_only: bool = True
    selection_outcome_blind: bool = True
    retry_count: int = 0
    replacement_used: bool = False
    test_record_used: bool = False
    successor_present: bool = True
    terminal_absorbing_zero: bool = False
    opening_policy: str = _OPENING_POLICY
    schema: str = D2_MECHANICS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != D2_MECHANICS_SCHEMA:
            raise D2AdjudicatorError("mechanics receipt schema is stale")
        object.__setattr__(self, "opening_reference_actions", _readonly_action_vector(self.opening_reference_actions, field="opening_reference_actions"))
        object.__setattr__(self, "opening_candidate_actions", _readonly_action_vector(self.opening_candidate_actions, field="opening_candidate_actions"))
        for field in (
            "successor_reference_action_sha256",
            "successor_candidate_action_sha256",
            "crn_sha256",
            "policy_sha256",
        ):
            object.__setattr__(self, field, _digest(getattr(self, field), field=field))
        for field in (
            "reference_branch_local",
            "candidate_branch_local",
            "full_evaluation_noncommitting",
            "without_focal_evaluation_noncommitting",
            "focal_removal_only",
            "selection_outcome_blind",
            "replacement_used",
            "test_record_used",
            "successor_present",
            "terminal_absorbing_zero",
        ):
            object.__setattr__(self, field, _bool(getattr(self, field), field=field))
        object.__setattr__(self, "retry_count", _exact_int(self.retry_count, field="retry_count", minimum=0))
        object.__setattr__(self, "opening_policy", _text(self.opening_policy, field="opening_policy"))

    def verify(
        self,
        *,
        anchor: D2PhysicalAnchor,
        focal_user: int,
        reference_action: int,
        candidate_action: int,
        policy_sha256: str,
    ) -> None:
        if self.schema != D2_MECHANICS_SCHEMA:
            raise D2AdjudicatorError("mechanics receipt schema is stale")
        if self.opening_reference_actions.shape != self.opening_candidate_actions.shape:
            raise D2AdjudicatorError("opening branch vectors have different shapes")
        if self.opening_reference_actions.ndim != 1 or not self.opening_reference_actions.size:
            raise D2AdjudicatorError("opening branch vectors are empty")
        if np.any(self.opening_reference_actions < NO_OP_ACTION) or np.any(self.opening_reference_actions >= NUM_ACTIONS):
            raise D2AdjudicatorError("opening reference vector has an out-of-space action")
        if np.any(self.opening_candidate_actions < NO_OP_ACTION) or np.any(self.opening_candidate_actions >= NUM_ACTIONS):
            raise D2AdjudicatorError("opening candidate vector has an out-of-space action")
        if type(focal_user) is not int or not 0 <= focal_user < self.opening_reference_actions.size:
            raise D2AdjudicatorError("focal user is outside the opening vectors")
        if self.opening_reference_actions[focal_user] != reference_action:
            raise D2AdjudicatorError("reference action does not match the opening receipt")
        if self.opening_candidate_actions[focal_user] != candidate_action:
            raise D2AdjudicatorError("candidate action does not match the opening receipt")
        changed = np.flatnonzero(self.opening_reference_actions != self.opening_candidate_actions)
        expected_changed = () if candidate_action == reference_action else (focal_user,)
        if tuple(int(value) for value in changed) != expected_changed:
            raise D2AdjudicatorError("candidate opening changes a non-focal user")
        if not self.reference_branch_local or not self.candidate_branch_local:
            raise D2AdjudicatorError("successor policy decisions are not branch local")
        if not self.full_evaluation_noncommitting or not self.without_focal_evaluation_noncommitting:
            raise D2AdjudicatorError("D2 physics evaluation committed state")
        if not self.focal_removal_only:
            raise D2AdjudicatorError("without-focal branch removed more than the focal user")
        if not self.selection_outcome_blind:
            raise D2AdjudicatorError("selection receipt is outcome dependent")
        if self.retry_count != 0 or self.replacement_used or self.test_record_used:
            raise D2AdjudicatorError("D2 contains a retry, replacement, or TEST record")
        if not self.successor_present or self.terminal_absorbing_zero:
            raise D2AdjudicatorError("D2 cell does not contain a usable successor")
        if self.opening_policy != _OPENING_POLICY:
            raise D2AdjudicatorError("D2 opening policy is not direct Q1+0+Q3")
        if self.policy_sha256 != _digest(policy_sha256, field="policy_sha256"):
            raise D2AdjudicatorError("mechanics and Q13 policy digests differ")
        anchor.verify()
        if not bool(anchor.native_action_mask[reference_action]) or not bool(anchor.native_action_mask[candidate_action]):
            raise D2AdjudicatorError("opening action is illegal under the native anchor mask")

    def to_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "opening_reference_actions": self.opening_reference_actions.tolist(),
            "opening_candidate_actions": self.opening_candidate_actions.tolist(),
            "successor_reference_action_sha256": self.successor_reference_action_sha256,
            "successor_candidate_action_sha256": self.successor_candidate_action_sha256,
            "crn_sha256": self.crn_sha256,
            "policy_sha256": self.policy_sha256,
            "reference_branch_local": self.reference_branch_local,
            "candidate_branch_local": self.candidate_branch_local,
            "full_evaluation_noncommitting": self.full_evaluation_noncommitting,
            "without_focal_evaluation_noncommitting": self.without_focal_evaluation_noncommitting,
            "focal_removal_only": self.focal_removal_only,
            "selection_outcome_blind": self.selection_outcome_blind,
            "retry_count": self.retry_count,
            "replacement_used": self.replacement_used,
            "test_record_used": self.test_record_used,
            "successor_present": self.successor_present,
            "terminal_absorbing_zero": self.terminal_absorbing_zero,
            "opening_policy": self.opening_policy,
        }


@dataclass(frozen=True)
class D2ActionRecord:
    """One legal candidate action and its raw signed focal-next target."""

    candidate_action: int
    reference_action: int
    target: FocalNextSurplus
    mechanics: D2MechanicsReceipt
    schema: str = D2_ROW_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != D2_ROW_SCHEMA:
            raise D2AdjudicatorError("D2 action row schema is stale")
        object.__setattr__(self, "candidate_action", _exact_int(self.candidate_action, field="candidate_action", minimum=0))
        object.__setattr__(self, "reference_action", _exact_int(self.reference_action, field="reference_action", minimum=0))
        if not isinstance(self.target, FocalNextSurplus):
            raise D2AdjudicatorError("D2 action row target is not typed")
        if not isinstance(self.mechanics, D2MechanicsReceipt):
            raise D2AdjudicatorError("D2 action row mechanics is not typed")

    def verify(self, *, anchor: D2PhysicalAnchor, q13: D2Q13SurfaceReceipt) -> None:
        if self.schema != D2_ROW_SCHEMA:
            raise D2AdjudicatorError("D2 action row schema is stale")
        anchor.verify()
        q13.verify()
        legal = anchor.native_action_mask
        if self.candidate_action >= NUM_ACTIONS or self.reference_action >= NUM_ACTIONS:
            raise D2AdjudicatorError("D2 action is outside the native action space")
        if not bool(legal[self.candidate_action]) or not bool(legal[self.reference_action]):
            raise D2AdjudicatorError("D2 action is illegal under the native mask")
        _strict_target(self.target)
        self.mechanics.verify(
            anchor=anchor,
            focal_user=anchor.focal_user,
            reference_action=self.reference_action,
            candidate_action=self.candidate_action,
            policy_sha256=q13.policy_sha256,
        )
        if self.candidate_action == self.reference_action and self.target.z2_focal_next_surplus_bits != 0.0:
            raise D2AdjudicatorError("candidate==reference row must be exact zero")
        if self.candidate_action == self.reference_action:
            for candidate_field, reference_field in (
                ("candidate_focal_rate_bps", "reference_focal_rate_bps"),
                ("candidate_focal_marginal_power_w", "reference_focal_marginal_power_w"),
                ("candidate_full_power_w", "reference_full_power_w"),
                ("candidate_without_focal_power_w", "reference_without_focal_power_w"),
            ):
                if getattr(self.target, candidate_field) != getattr(self.target, reference_field):
                    raise D2AdjudicatorError("equal-action row has different branch raw terms")

    def to_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "candidate_action": self.candidate_action,
            "reference_action": self.reference_action,
            "target": _target_payload(self.target),
            "mechanics": self.mechanics.to_payload(),
        }


@dataclass(frozen=True)
class D2LineageDecisionCapture:
    """All native legal-action rows for one physical anchor and lineage."""

    anchor: D2PhysicalAnchor
    lineage: str
    q13: D2Q13SurfaceReceipt
    rows: tuple[D2ActionRecord, ...]
    schema: str = D2_CAPTURE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != D2_CAPTURE_SCHEMA:
            raise D2AdjudicatorError("D2 lineage capture schema is stale")
        if not isinstance(self.anchor, D2PhysicalAnchor):
            raise D2AdjudicatorError("capture anchor is not typed")
        object.__setattr__(self, "lineage", _text(self.lineage, field="lineage"))
        if not isinstance(self.q13, D2Q13SurfaceReceipt):
            raise D2AdjudicatorError("capture Q13 receipt is not typed")
        raw_rows = tuple(self.rows)
        if any(not isinstance(row, D2ActionRecord) for row in raw_rows):
            raise D2AdjudicatorError("capture contains a non-row record")
        object.__setattr__(self, "rows", tuple(sorted(raw_rows, key=lambda row: row.candidate_action)))

    @property
    def key(self) -> tuple[tuple[int, int, int], str]:
        return (self.anchor.key, self.lineage)

    def verify(self) -> None:
        if self.schema != D2_CAPTURE_SCHEMA:
            raise D2AdjudicatorError("D2 lineage capture schema is stale")
        if self.lineage not in D2_LINEAGES:
            raise D2AdjudicatorError("lineage is not one of the three frozen Q13 lineages")
        self.anchor.verify()
        self.q13.verify()
        if len(self.rows) != len(self.anchor.legal_actions):
            raise D2AdjudicatorError("lineage cell does not enumerate every native legal action")
        observed = tuple(row.candidate_action for row in self.rows)
        if observed != self.anchor.legal_actions:
            raise D2AdjudicatorError("candidate actions do not equal the native mask exactly once")
        if len(set(observed)) != len(observed):
            raise D2AdjudicatorError("candidate action is duplicated")
        expected_reference = int(
            np.argmax(
                np.where(
                    self.anchor.native_action_mask,
                    self.q13.q1_surface + self.q13.q3_surface,
                    -np.inf,
                )
            )
        )
        references = {row.reference_action for row in self.rows}
        if references != {expected_reference}:
            raise D2AdjudicatorError("reference action is not the direct Q1+0+Q3 masked argmax")
        reference_opening: np.ndarray | None = None
        crn: str | None = None
        reference_signature: tuple[object, ...] | None = None
        for row in self.rows:
            row.verify(anchor=self.anchor, q13=self.q13)
            if reference_opening is None:
                reference_opening = row.mechanics.opening_reference_actions
                crn = row.mechanics.crn_sha256
            elif not np.array_equal(reference_opening, row.mechanics.opening_reference_actions):
                raise D2AdjudicatorError("reference opening vector drifted within the cell")
            if row.mechanics.crn_sha256 != crn:
                raise D2AdjudicatorError("CRN root drifted within the cell")
            signature = (
                row.target.reference_focal_rate_bps,
                row.target.reference_focal_marginal_power_w,
                row.target.reference_full_power_w,
                row.target.reference_without_focal_power_w,
                row.mechanics.successor_reference_action_sha256,
            )
            if reference_signature is None:
                reference_signature = signature
            elif signature != reference_signature:
                raise D2AdjudicatorError(
                    "reference successor measurement drifted within the cell"
                )

    def to_payload(self) -> dict[str, object]:
        self.verify()
        return {
            "schema": self.schema,
            "anchor": self.anchor.to_payload(),
            "lineage": self.lineage,
            "q13": self.q13.to_payload(),
            "rows": [row.to_payload() for row in self.rows],
        }


@dataclass(frozen=True)
class D2Metrics:
    """Deterministic D2 gate metrics; finite arrays are kept in cell order."""

    g_m_pass: bool = False
    g_r_pass: bool = False
    g_s_pass: bool = False
    g_v_pass: bool = False
    g_p_pass: bool = False
    physical_anchors: int = 0
    lineage_cells: int = 0
    g_r_median_spearman: float | None = None
    g_r_undefined_pairs: int = 0
    g_s_median_ratio: float | None = None
    g_s_zero_denominator_cells: int = 0
    g_v_iqr_cells: int = 0
    g_p_positive_anchors: int = 0
    rank_correlations: tuple[float, ...] = ()
    scale_ratios: tuple[float, ...] = ()
    target_iqrs: tuple[float, ...] = ()
    positive_lineages_by_anchor: tuple[int, ...] = ()

    def to_payload(self) -> dict[str, object]:
        def metric(value: float | None) -> str | None:
            return None if value is None else _float_hex(value, field="metric")

        return {
            "g_m_pass": self.g_m_pass,
            "g_r_pass": self.g_r_pass,
            "g_s_pass": self.g_s_pass,
            "g_v_pass": self.g_v_pass,
            "g_p_pass": self.g_p_pass,
            "physical_anchors": self.physical_anchors,
            "lineage_cells": self.lineage_cells,
            "g_r_median_spearman": metric(self.g_r_median_spearman),
            "g_r_undefined_pairs": self.g_r_undefined_pairs,
            "g_s_median_ratio": metric(self.g_s_median_ratio),
            "g_s_zero_denominator_cells": self.g_s_zero_denominator_cells,
            "g_v_iqr_cells": self.g_v_iqr_cells,
            "g_p_positive_anchors": self.g_p_positive_anchors,
            "rank_correlations": [metric(value) for value in self.rank_correlations],
            "scale_ratios": [metric(value) for value in self.scale_ratios],
            "target_iqrs": [metric(value) for value in self.target_iqrs],
            "positive_lineages_by_anchor": list(self.positive_lineages_by_anchor),
        }


@dataclass(frozen=True)
class D2AdjudicationResult:
    """One of the three fixed D2 verdicts plus canonical evidence metrics."""

    verdict: str
    metrics: D2Metrics
    reasons: tuple[str, ...] = ()
    input_sha256: str | None = None
    schema: str = D2_RESULT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != D2_RESULT_SCHEMA:
            raise D2AdjudicatorError("D2 result schema is stale")
        if self.verdict not in D2_VERDICTS:
            raise D2AdjudicatorError("D2 result verdict is not fixed")
        if not isinstance(self.metrics, D2Metrics):
            raise D2AdjudicatorError("D2 result metrics are not typed")
        reasons = tuple(self.reasons)
        if any(not isinstance(reason, str) or not reason for reason in reasons):
            raise D2AdjudicatorError("D2 result reasons must be nonempty strings")
        object.__setattr__(self, "reasons", reasons)
        if self.input_sha256 is not None:
            object.__setattr__(self, "input_sha256", _digest(self.input_sha256, field="input_sha256"))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "verdict": self.verdict,
            "formula_constants": {
                "lambda_bits_per_j": D2_LAMBDA_BITS_PER_J.hex(),
                "interval_s": D2_INTERVAL_S.hex(),
                "kappa_bits": D2_DEFAULT_KAPPA_BITS.hex(),
                "iqr_method": D2_IQR_METHOD,
            },
            "metrics": self.metrics.to_payload(),
            "reasons": list(self.reasons),
            "input_sha256": self.input_sha256,
        }

    @property
    def result_sha256(self) -> str:
        return canonical_sha256(self.to_payload())

    def to_document(self) -> dict[str, object]:
        body = self.to_payload()
        return body | {"result_sha256": canonical_sha256(body)}

    def as_dict(self) -> dict[str, object]:
        return self.to_document()


def _invalid_result(reason: str = "D2 input verification failed") -> D2AdjudicationResult:
    return D2AdjudicationResult(
        verdict=D2_INVALID_NO_INFERENCE,
        metrics=D2Metrics(),
        reasons=(reason,),
        input_sha256=None,
    )


def average_ranks(values: Sequence[float] | np.ndarray) -> np.ndarray:
    """Return one-based average ranks, with deterministic tie handling."""

    raw = np.asarray(values, dtype=np.float64)
    if raw.ndim != 1 or not raw.size or not np.all(np.isfinite(raw)):
        raise D2AdjudicatorError("rank input must be a nonempty finite vector")
    order = np.argsort(raw, kind="mergesort")
    ranks = np.empty(raw.size, dtype=np.float64)
    start = 0
    while start < raw.size:
        stop = start + 1
        while stop < raw.size and raw[order[stop]] == raw[order[start]]:
            stop += 1
        ranks[order[start:stop]] = (float(start + 1) + float(stop)) / 2.0
        start = stop
    return ranks


def spearman_rank_correlation(
    left: Sequence[float] | np.ndarray,
    right: Sequence[float] | np.ndarray,
) -> float | None:
    """Compute Spearman rho with average ranks; ``None`` means undefined."""

    first = np.asarray(left, dtype=np.float64)
    second = np.asarray(right, dtype=np.float64)
    if first.shape != second.shape or first.ndim != 1 or not first.size:
        raise D2AdjudicatorError("Spearman inputs must be matching nonempty vectors")
    first_ranks = average_ranks(first)
    second_ranks = average_ranks(second)
    first_centered = first_ranks - np.mean(first_ranks)
    second_centered = second_ranks - np.mean(second_ranks)
    denominator = float(np.linalg.norm(first_centered) * np.linalg.norm(second_centered))
    if denominator == 0.0:
        return None
    result = float(np.dot(first_centered, second_centered) / denominator)
    if not math.isfinite(result):
        raise D2AdjudicatorError("Spearman arithmetic is non-finite")
    return result


def _capture_sort_key(capture: D2LineageDecisionCapture) -> tuple[Any, ...]:
    anchor = capture.anchor
    lineage_order = D2_LINEAGES.index(capture.lineage)
    return (anchor.seed, anchor.step_index, anchor.focal_user, lineage_order)


def _input_payload(captures: Sequence[D2LineageDecisionCapture]) -> dict[str, object]:
    ordered = tuple(sorted(captures, key=_capture_sort_key))
    return {
        "schema": D2_SCHEMA,
        "formula_constants": {
            "lambda_bits_per_j": D2_LAMBDA_BITS_PER_J.hex(),
            "interval_s": D2_INTERVAL_S.hex(),
            "kappa_bits": D2_DEFAULT_KAPPA_BITS.hex(),
            "iqr_method": D2_IQR_METHOD,
        },
        "captures": [capture.to_payload() for capture in ordered],
    }


def _validate_complete_input(
    captures: Sequence[D2LineageDecisionCapture],
) -> tuple[
    tuple[D2LineageDecisionCapture, ...],
    dict[tuple[int, int, int], dict[str, D2LineageDecisionCapture]],
]:
    if len(captures) != D2_EXPECTED_CELLS:
        raise D2AdjudicatorError("D2 must contain exactly 60 lineage-decision cells")
    ordered = tuple(sorted(captures, key=_capture_sort_key))
    by_anchor: dict[tuple[int, int, int], dict[str, D2LineageDecisionCapture]] = {}
    seen_cells: set[tuple[tuple[int, int, int], str]] = set()
    for capture in ordered:
        if not isinstance(capture, D2LineageDecisionCapture):
            raise D2AdjudicatorError("D2 input contains a non-capture record")
        capture.verify()
        if capture.key in seen_cells:
            raise D2AdjudicatorError("D2 contains a duplicate lineage-decision cell")
        seen_cells.add(capture.key)
        by_anchor.setdefault(capture.anchor.key, {})[capture.lineage] = capture
    if len(by_anchor) != D2_EXPECTED_ANCHORS:
        raise D2AdjudicatorError("D2 must contain exactly 20 physical anchors")
    if {seed for seed, _, _ in by_anchor} != set(D2_SEEDS):
        raise D2AdjudicatorError("D2 physical anchors do not use exactly the frozen seeds")
    for seed in D2_SEEDS:
        seed_anchors = [key for key in by_anchor if key[0] == seed]
        if len(seed_anchors) != 2 or {by_anchor[key][D2_LINEAGES[0]].anchor.window for key in seed_anchors} != {"early", "late"}:
            raise D2AdjudicatorError("each D2 seed must have exactly one early and one late anchor")
    for key, lineages in by_anchor.items():
        if set(lineages) != set(D2_LINEAGES):
            raise D2AdjudicatorError("each physical anchor must have all three lineages")
        anchor_payload = lineages[D2_LINEAGES[0]].anchor.to_payload()
        for lineage in D2_LINEAGES[1:]:
            if lineages[lineage].anchor.to_payload() != anchor_payload:
                raise D2AdjudicatorError("lineages disagree on the physical anchor or native mask")
        crn_digests = {
            row.mechanics.crn_sha256
            for capture in lineages.values()
            for row in capture.rows
        }
        if len(crn_digests) != 1:
            raise D2AdjudicatorError("lineages do not share one keyed CRN root per anchor")
    lineage_policy: dict[str, tuple[str, str, str]] = {}
    for capture in ordered:
        signature = (
            capture.q13.q1_checkpoint_sha256,
            capture.q13.q3_checkpoint_sha256,
            capture.q13.policy_sha256,
        )
        previous = lineage_policy.setdefault(capture.lineage, signature)
        if previous != signature:
            raise D2AdjudicatorError("a frozen lineage changes its Q13/checkpoint receipt")
        for row in capture.rows:
            row_signature = (row.target.lambda_bits_per_j, row.target.interval_s)
            if row_signature != (D2_LAMBDA_BITS_PER_J, D2_INTERVAL_S):
                raise D2AdjudicatorError(
                    "D2 target lambda or interval differs from the frozen constants"
                )
    return ordered, by_anchor


def _scientific_metrics(
    ordered: Sequence[D2LineageDecisionCapture],
    by_anchor: dict[tuple[int, int, int], dict[str, D2LineageDecisionCapture]],
    *,
    kappa_bits: float,
) -> D2Metrics:
    kappa = _positive(kappa_bits, field="kappa_bits")
    rank_correlations: list[float] = []
    undefined_pairs = 0
    scale_ratios: list[float] = []
    target_iqrs: list[float] = []
    positive_by_anchor: list[int] = []

    for key in sorted(by_anchor):
        cells = by_anchor[key]
        target_vectors = {
            lineage: np.asarray(
                [row.target.z2_focal_next_surplus_bits for row in cells[lineage].rows],
                dtype=np.float64,
            )
            for lineage in D2_LINEAGES
        }
        positive_lineages = 0
        for lineage in D2_LINEAGES:
            values = target_vectors[lineage]
            reference = cells[lineage].rows[0].reference_action
            non_reference = np.asarray(
                [value for row, value in zip(cells[lineage].rows, values) if row.candidate_action != reference],
                dtype=np.float64,
            )
            if bool(np.any(non_reference > 0.0)):
                positive_lineages += 1
        positive_by_anchor.append(positive_lineages)
        for first, second in D2_LINEAGE_PAIRS:
            rho = spearman_rank_correlation(target_vectors[first], target_vectors[second])
            if rho is None:
                undefined_pairs += 1
            else:
                rank_correlations.append(rho)

    # G-S and G-V use the same deterministic cell order but are independent
    # gates: a zero Q1+Q3 denominator fails G-S while the target IQR remains a
    # valid G-V statistic.
    g_v_iqr_cells = 0
    g_s_zero_denominator_cells = 0
    for capture in ordered:
        values = np.asarray(
            [row.target.z2_focal_next_surplus_bits for row in capture.rows],
            dtype=np.float64,
        )
        q13_values = capture.q13.q1_surface[capture.anchor.native_action_mask] + capture.q13.q3_surface[capture.anchor.native_action_mask]
        target_std = float(np.std(values / kappa))
        q13_std = float(np.std(q13_values))
        if not math.isfinite(target_std) or not math.isfinite(q13_std):
            raise D2AdjudicatorError("G-S standard deviation is non-finite")
        if q13_std == 0.0:
            g_s_zero_denominator_cells += 1
        else:
            ratio = target_std / q13_std
            if not math.isfinite(ratio):
                raise D2AdjudicatorError("G-S ratio is non-finite")
            scale_ratios.append(ratio)
        q1, q3 = np.quantile(values, (0.25, 0.75), method=D2_IQR_METHOD)
        iqr = float(q3 - q1)
        if not math.isfinite(iqr):
            raise D2AdjudicatorError("G-V target IQR is non-finite")
        target_iqrs.append(iqr)
        if iqr >= D2_G_V_MIN_IQR_KAPPA * kappa:
            g_v_iqr_cells += 1

    g_r_median = float(np.median(rank_correlations)) if rank_correlations else None
    g_s_median = float(np.median(scale_ratios)) if scale_ratios else None
    g_r_pass = undefined_pairs == 0 and g_r_median is not None and g_r_median >= D2_G_R_MIN
    g_s_pass = (
        g_s_zero_denominator_cells == 0
        and g_s_median is not None
        and g_s_median <= D2_G_S_MAX
    )
    g_v_pass = g_v_iqr_cells >= D2_G_V_REQUIRED_CELLS
    g_p_positive_anchors = sum(
        count >= D2_G_P_REQUIRED_LINEAGES for count in positive_by_anchor
    )
    g_p_pass = g_p_positive_anchors >= D2_G_P_REQUIRED_ANCHORS
    return D2Metrics(
        g_m_pass=True,
        g_r_pass=g_r_pass,
        g_s_pass=g_s_pass,
        g_v_pass=g_v_pass,
        g_p_pass=g_p_pass,
        physical_anchors=len(by_anchor),
        lineage_cells=len(ordered),
        g_r_median_spearman=g_r_median,
        g_r_undefined_pairs=undefined_pairs,
        g_s_median_ratio=g_s_median,
        g_s_zero_denominator_cells=g_s_zero_denominator_cells,
        g_v_iqr_cells=g_v_iqr_cells,
        g_p_positive_anchors=g_p_positive_anchors,
        rank_correlations=tuple(rank_correlations),
        scale_ratios=tuple(scale_ratios),
        target_iqrs=tuple(target_iqrs),
        positive_lineages_by_anchor=tuple(positive_by_anchor),
    )


def adjudicate_d2(
    captures: Iterable[D2LineageDecisionCapture],
    *,
    kappa_bits: float = D2_DEFAULT_KAPPA_BITS,
) -> D2AdjudicationResult:
    """Validate merged D2 captures and return exactly one fixed verdict."""

    try:
        if _positive(kappa_bits, field="kappa_bits") != D2_DEFAULT_KAPPA_BITS:
            raise D2AdjudicatorError("D2 kappa differs from the frozen constant")
        if isinstance(captures, (str, bytes)):
            raise D2AdjudicatorError("D2 captures must be typed records, not text")
        materialized = tuple(captures)
        ordered, by_anchor = _validate_complete_input(materialized)
        input_payload = _input_payload(ordered)
        input_digest = canonical_sha256(input_payload)
        metrics = _scientific_metrics(ordered, by_anchor, kappa_bits=kappa_bits)
        reasons: list[str] = []
        if not metrics.g_r_pass:
            reasons.append("G-R rank stability gate failed")
        if not metrics.g_s_pass:
            reasons.append("G-S scale compatibility gate failed")
        if not metrics.g_v_pass:
            reasons.append("G-V target variation gate failed")
        if not metrics.g_p_pass:
            reasons.append("G-P positive headroom gate failed")
        verdict = (
            D2_PASS_AUTHORIZE_D3_IMPLEMENTATION
            if not reasons
            else D2_FAIL_RETURN_TO_C2_FORMULA_OR_SOURCE_DESIGN
        )
        return D2AdjudicationResult(
            verdict=verdict,
            metrics=metrics,
            reasons=tuple(reasons),
            input_sha256=input_digest,
        )
    except Exception:
        return _invalid_result()


# A short class facade is convenient for callers that keep adjudicators as a
# dependency in a data pipeline; it remains stateless and pure.
class D2Adjudicator:
    """Stateless facade around :func:`adjudicate_d2`."""

    @staticmethod
    def adjudicate(
        captures: Iterable[D2LineageDecisionCapture],
        *,
        kappa_bits: float = D2_DEFAULT_KAPPA_BITS,
    ) -> D2AdjudicationResult:
        return adjudicate_d2(captures, kappa_bits=kappa_bits)


adjudicate = adjudicate_d2
D2Result = D2AdjudicationResult
D2Capture = D2LineageDecisionCapture


__all__ = [
    "D2AdjudicationResult",
    "D2Adjudicator",
    "D2AdjudicatorError",
    "D2ActionRecord",
    "D2Capture",
    "D2LineageDecisionCapture",
    "D2MechanicsReceipt",
    "D2Metrics",
    "D2PhysicalAnchor",
    "D2Q13SurfaceReceipt",
    "D2Result",
    "D2SelectionReceipt",
    "D2_DEFAULT_KAPPA_BITS",
    "D2_ANCHOR_SCHEMA",
    "D2_CAPTURE_SCHEMA",
    "D2_EARLY_STEPS",
    "D2_EXPECTED_ANCHORS",
    "D2_EXPECTED_CELLS",
    "D2_FAIL_RETURN_TO_C2_FORMULA_OR_SOURCE_DESIGN",
    "D2_G_P_REQUIRED_ANCHORS",
    "D2_G_P_REQUIRED_LINEAGES",
    "D2_G_R_MIN",
    "D2_G_S_MAX",
    "D2_G_V_MIN_IQR_KAPPA",
    "D2_G_V_REQUIRED_CELLS",
    "D2_INVALID_NO_INFERENCE",
    "D2_LATE_STEPS",
    "D2_LINEAGE_PAIRS",
    "D2_LINEAGES",
    "D2_MECHANICS_SCHEMA",
    "D2_PASS_AUTHORIZE_D3_IMPLEMENTATION",
    "D2_Q13_SCHEMA",
    "D2_RESULT_SCHEMA",
    "D2_ROW_SCHEMA",
    "D2_SELECTION_SCHEMA",
    "D2_SCHEMA",
    "D2_SEEDS",
    "D2_VERDICTS",
    "adjudicate",
    "adjudicate_d2",
    "average_ranks",
    "canonical_json_bytes",
    "canonical_sha256",
    "spearman_rank_correlation",
]
