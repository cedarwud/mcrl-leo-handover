"""Pure V0.22 named-coalition C3 residual mechanics.

This module consumes one already matched current-slot reference profile,
unilateral coalition branches, and joint coalition branch.  It performs no
physics evaluation, action selection, learning, rollout, or deployment
work.  The returned target is a named-coalition identity only.  It is **NOT**
exact for partial adoption, arbitrary hybrid profiles, learned Q sums, or
deployment closure.  For this provisional probe the interaction surplus is
allocated with a fixed equal interaction share; that allocation is not
tunable.

For coalition member ``i`` with user ``u`` the formula is

``own_i = Bu[i,u] - B0[u] - lambda * (Eu[i] - E0)``

``nonfocal_i = sum_v!=u(Bu[i,v] - B0[v])``

``d_i = own_i + nonfocal_i``

The joint surplus is decomposed into unilateral terms and the residual
interaction term.  Each member receives one equal share of that interaction
surplus, added to its non-focal bits as ``z3_i``.  The sparse Q3 surface puts
only ``z3_i / kappa`` at each proposed member action; references, illegal
cells, non-members, and all other actions are exact zeros.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from ..env.action_contract import NO_OP_ACTION, NUM_ACTIONS
from ..errors import MCRLContractError


COALITION_RESIDUAL_C3_SCHEMA = "multi-catfish-mcrl-v022-c3-coalition-residual-v1"
"""Canonical schema for the provisional V0.22 coalition residual result."""

COALITION_RESIDUAL_C3_SCHEMA_VERSION = 1
"""Schema revision for :data:`COALITION_RESIDUAL_C3_SCHEMA`."""

COALITION_RESIDUAL_C3_DEFAULT_ACTION_COUNT = NUM_ACTIONS
"""Native action width used when no explicit ``A`` is supplied."""

# Descriptive aliases make the schema easy to discover from either the
# versioned route name or the formula name.
V022_C3_COALITION_RESIDUAL_SCHEMA = COALITION_RESIDUAL_C3_SCHEMA
V022_C3_COALITION_RESIDUAL_SCHEMA_VERSION = COALITION_RESIDUAL_C3_SCHEMA_VERSION


class CoalitionResidualC3Error(MCRLContractError):
    """A V0.22 named-coalition C3 input or identity violated the contract."""


CoalitionResidualC3ContractError = CoalitionResidualC3Error


def _readonly(value: object, *, dtype: np.dtype | type) -> np.ndarray:
    """Copy an array into C order and make the copy read-only."""

    try:
        result = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise CoalitionResidualC3Error("array cannot be materialised") from error
    result.setflags(write=False)
    return result


def _float_scalar(value: object, *, field: str, positive: bool = False) -> float:
    """Parse one finite scalar, optionally requiring strict positivity."""

    if isinstance(value, (bool, np.bool_)):
        requirement = "finite and positive" if positive else "finite"
        raise CoalitionResidualC3Error(f"{field} must be {requirement}")
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError, OverflowError) as error:
        requirement = "finite and positive" if positive else "finite"
        raise CoalitionResidualC3Error(f"{field} must be {requirement}") from error
    if raw.shape != () or raw.dtype == np.dtype("bool"):
        requirement = "finite and positive" if positive else "finite"
        raise CoalitionResidualC3Error(f"{field} must be a scalar {requirement} value")
    try:
        result = float(raw)
    except (TypeError, ValueError, OverflowError) as error:
        requirement = "finite and positive" if positive else "finite"
        raise CoalitionResidualC3Error(f"{field} must be {requirement}") from error
    requirement = "finite and positive" if positive else "finite"
    if not math.isfinite(result) or (positive and result <= 0.0):
        raise CoalitionResidualC3Error(f"{field} must be {requirement}")
    return result


def _float_array(
    value: object,
    *,
    field: str,
    shape: tuple[int, ...] | None = None,
    nonnegative: bool = False,
) -> np.ndarray:
    """Parse a finite float array with optional non-negative domain guard."""

    try:
        raw = np.asarray(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise CoalitionResidualC3Error(f"{field} must be a numeric array") from error
    if raw.dtype == np.dtype("bool"):
        raise CoalitionResidualC3Error(f"{field} must be numeric, not Boolean")
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise CoalitionResidualC3Error(f"{field} must be a finite numeric array") from error
    if shape is not None and result.shape != shape:
        raise CoalitionResidualC3Error(f"{field} must have shape {shape}, got {result.shape}")
    if not np.all(np.isfinite(result)):
        raise CoalitionResidualC3Error(f"{field} must be finite")
    if nonnegative and np.any(result < 0.0):
        raise CoalitionResidualC3Error(f"{field} must be non-negative")
    return np.array(result, dtype=np.float64, copy=True, order="C")


def _int_vector(value: object, *, field: str, size: int | None = None) -> np.ndarray:
    """Parse an exact integer vector, rejecting Boolean and float actions."""

    try:
        result = np.asarray(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise CoalitionResidualC3Error(f"{field} must be an integer vector") from error
    if (
        result.ndim != 1
        or result.dtype == np.dtype("bool")
        or not np.issubdtype(result.dtype, np.integer)
    ):
        shape = f" shape ({size},)" if size is not None else ""
        raise CoalitionResidualC3Error(f"{field} must be an integer vector{shape}")
    if size is not None and result.shape != (size,):
        raise CoalitionResidualC3Error(f"{field} must have shape ({size},), got {result.shape}")
    return np.array(result, dtype=np.int64, copy=True, order="C")


def _action_count(value: object, *, field: str = "action_count") -> int:
    """Parse a positive native action width."""

    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise CoalitionResidualC3Error(f"{field} must be a positive integer")
    result = int(value)
    if result < 1:
        raise CoalitionResidualC3Error(f"{field} must be a positive integer")
    return result


def _legal_mask(value: object, *, users: int, actions: int) -> np.ndarray:
    """Parse the exact Boolean ``(U, A)`` legal-action mask."""

    try:
        result = np.asarray(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise CoalitionResidualC3Error("legal_mask must be Boolean") from error
    if result.dtype != np.bool_ or result.shape != (users, actions):
        raise CoalitionResidualC3Error(
            f"legal_mask must be Boolean shape ({users}, {actions})"
        )
    return np.array(result, dtype=np.bool_, copy=True, order="C")


def _safe_sum(values: object, *, field: str) -> float:
    """Use stable summation and reject overflow in derived quantities."""

    try:
        result = math.fsum(float(value) for value in np.asarray(values).reshape(-1).tolist())
    except (OverflowError, TypeError, ValueError) as error:
        raise CoalitionResidualC3Error(f"{field} arithmetic is non-finite") from error
    if not math.isfinite(result):
        raise CoalitionResidualC3Error(f"{field} arithmetic is non-finite")
    return float(result)


def _finite_derived(value: object, *, field: str) -> float:
    """Normalize a derived scalar while rejecting arithmetic overflow."""

    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise CoalitionResidualC3Error(f"{field} arithmetic is non-finite") from error
    if not math.isfinite(result):
        raise CoalitionResidualC3Error(f"{field} arithmetic is non-finite")
    return result


def _validate_action_profile(
    *,
    reference_actions: np.ndarray,
    legal_mask: np.ndarray,
    coalition_user_ids: np.ndarray,
    proposed_actions: np.ndarray,
) -> None:
    """Enforce reference legality and named-coalition proposal legality."""

    users, actions = legal_mask.shape
    if reference_actions.shape != (users,):
        raise CoalitionResidualC3Error(
            f"reference_actions must have shape ({users},), got {reference_actions.shape}"
        )
    for user, action in enumerate(reference_actions.tolist()):
        if int(action) == NO_OP_ACTION:
            if bool(np.any(legal_mask[user])):
                raise CoalitionResidualC3Error(
                    "reference_actions may be -1 only for an all-empty legal row"
                )
            continue
        if int(action) < 0 or int(action) >= actions:
            raise CoalitionResidualC3Error(
                "reference_actions contain an out-of-range action"
            )
        if not bool(legal_mask[user, int(action)]):
            raise CoalitionResidualC3Error("every reference action must be legal")

    members = coalition_user_ids.size
    if members < 2:
        raise CoalitionResidualC3Error("coalition must contain at least two members")
    if proposed_actions.shape != (members,):
        raise CoalitionResidualC3Error(
            f"proposed_actions must have shape ({members},), got {proposed_actions.shape}"
        )
    if np.any(coalition_user_ids < 0) or np.any(coalition_user_ids >= users):
        raise CoalitionResidualC3Error("coalition_user_ids contain an invalid user")
    if np.unique(coalition_user_ids).size != members:
        raise CoalitionResidualC3Error("coalition_user_ids must be unique")
    if np.any(proposed_actions < 0) or np.any(proposed_actions >= actions):
        raise CoalitionResidualC3Error("proposed_actions contain an out-of-range action")
    for index, (user, action) in enumerate(
        zip(coalition_user_ids.tolist(), proposed_actions.tolist())
    ):
        if not bool(legal_mask[int(user), int(action)]):
            raise CoalitionResidualC3Error(
                f"proposed_actions[{index}] is illegal for coalition user {int(user)}"
            )
        if int(action) == int(reference_actions[int(user)]):
            raise CoalitionResidualC3Error(
                f"proposed_actions[{index}] must differ from the reference action"
            )


def _validate_inputs(
    *,
    reference_bits: object,
    reference_energy_j: object,
    unilateral_bits: object,
    unilateral_energy_j: object,
    joint_bits: object,
    joint_energy_j: object,
    coalition_user_ids: object,
    proposed_actions: object,
    lambda_bits_per_j: object,
    kappa_bits: object,
    action_count: object,
    reference_actions: object,
    legal_mask: object,
) -> dict[str, Any]:
    """Materialize and validate all formula inputs once."""

    b0 = _float_array(reference_bits, field="reference_bits", nonnegative=True)
    if b0.ndim != 1 or b0.size < 1:
        raise CoalitionResidualC3Error("reference_bits must have shape (U,) with U >= 1")
    users = int(b0.size)
    actions = _action_count(action_count)
    legal = _legal_mask(legal_mask, users=users, actions=actions)
    refs = _int_vector(reference_actions, field="reference_actions", size=users)
    ids = _int_vector(coalition_user_ids, field="coalition_user_ids")
    if ids.size < 2:
        raise CoalitionResidualC3Error("coalition must contain at least two members")
    members = int(ids.size)
    proposed = _int_vector(proposed_actions, field="proposed_actions", size=members)
    bu = _float_array(
        unilateral_bits,
        field="unilateral_bits",
        shape=(members, users),
        nonnegative=True,
    )
    eu = _float_array(
        unilateral_energy_j,
        field="unilateral_energy_j",
        shape=(members,),
    )
    if np.any(eu <= 0.0):
        raise CoalitionResidualC3Error("unilateral_energy_j must be positive")
    bc = _float_array(
        joint_bits,
        field="joint_bits",
        shape=(users,),
        nonnegative=True,
    )
    e0 = _float_scalar(reference_energy_j, field="reference_energy_j", positive=True)
    ec = _float_scalar(joint_energy_j, field="joint_energy_j", positive=True)
    multiplier = _float_scalar(
        lambda_bits_per_j, field="lambda_bits_per_j", positive=True
    )
    kappa = _float_scalar(kappa_bits, field="kappa_bits", positive=True)
    _validate_action_profile(
        reference_actions=refs,
        legal_mask=legal,
        coalition_user_ids=ids,
        proposed_actions=proposed,
    )
    return {
        "reference_bits": b0,
        "reference_energy_j": e0,
        "unilateral_bits": bu,
        "unilateral_energy_j": eu,
        "joint_bits": bc,
        "joint_energy_j": ec,
        "coalition_user_ids": ids,
        "proposed_actions": proposed,
        "lambda_bits_per_j": multiplier,
        "kappa_bits": kappa,
        "action_count": actions,
        "reference_actions": refs,
        "legal_mask": legal,
    }


def _compute_components(
    *,
    reference_bits: np.ndarray,
    reference_energy_j: float,
    unilateral_bits: np.ndarray,
    unilateral_energy_j: np.ndarray,
    joint_bits: np.ndarray,
    joint_energy_j: float,
    coalition_user_ids: np.ndarray,
    lambda_bits_per_j: float,
) -> dict[str, Any]:
    """Compute the named-coalition algebra from already validated inputs."""

    members, users = unilateral_bits.shape
    try:
        unilateral_delta_bits = unilateral_bits - reference_bits[None, :]
        joint_delta = joint_bits - reference_bits
        energy_delta = unilateral_energy_j - reference_energy_j
        joint_delta_energy = joint_energy_j - reference_energy_j
    except (FloatingPointError, OverflowError, ValueError) as error:
        raise CoalitionResidualC3Error("delta arithmetic is non-finite") from error
    if (
        not np.all(np.isfinite(unilateral_delta_bits))
        or not np.all(np.isfinite(joint_delta))
        or not np.all(np.isfinite(energy_delta))
        or not math.isfinite(float(joint_delta_energy))
    ):
        raise CoalitionResidualC3Error("delta arithmetic is non-finite")

    joint_delta_bits = _safe_sum(joint_delta, field="joint_delta_bits")
    unilateral_totals = np.asarray(
        [_safe_sum(row, field="unilateral_delta_bits") for row in unilateral_delta_bits],
        dtype=np.float64,
    )
    sum_unilateral_totals = _safe_sum(
        unilateral_totals, field="sum_unilateral_delta_bits"
    )
    sum_unilateral_energy = _safe_sum(energy_delta, field="sum_unilateral_delta_energy")

    own = np.empty(members, dtype=np.float64)
    nonfocal = np.empty(members, dtype=np.float64)
    for index, user in enumerate(coalition_user_ids.tolist()):
        user_index = int(user)
        own[index] = (
            unilateral_delta_bits[index, user_index]
            - lambda_bits_per_j * energy_delta[index]
        )
        nonfocal[index] = _safe_sum(
            np.delete(unilateral_delta_bits[index], user_index),
            field="nonfocal_bits",
        )
    d = own + nonfocal

    joint_surplus = joint_delta_bits - lambda_bits_per_j * joint_delta_energy
    interaction_bits = joint_delta_bits - sum_unilateral_totals
    interaction_energy = joint_delta_energy - sum_unilateral_energy
    interaction_surplus = interaction_bits - lambda_bits_per_j * interaction_energy
    equal_share = interaction_surplus / float(members)
    z3 = nonfocal + equal_share
    combined = own + z3
    identity_residual = _safe_sum(combined, field="identity") - joint_surplus

    scalar_values = {
        "joint_delta_bits": joint_delta_bits,
        "joint_delta_energy_j": joint_delta_energy,
        "joint_surplus_bits": joint_surplus,
        "interaction_bits": interaction_bits,
        "interaction_energy_j": interaction_energy,
        "interaction_surplus_bits": interaction_surplus,
        "equal_share_bits": equal_share,
        "identity_residual_bits": identity_residual,
    }
    for field, value in scalar_values.items():
        scalar_values[field] = _finite_derived(value, field=field)
    for field, values in (
        ("own_bits", own),
        ("nonfocal_bits", nonfocal),
        ("d_bits", d),
        ("z3_bits", z3),
        ("combined_bits", combined),
    ):
        if not np.all(np.isfinite(values)):
            raise CoalitionResidualC3Error(f"{field} arithmetic is non-finite")
    return {
        "own_bits": np.array(own, dtype=np.float64, copy=True),
        "nonfocal_bits": np.array(nonfocal, dtype=np.float64, copy=True),
        "d_bits": np.array(d, dtype=np.float64, copy=True),
        **scalar_values,
        "z3_bits": np.array(z3, dtype=np.float64, copy=True),
        "combined_bits": np.array(combined, dtype=np.float64, copy=True),
    }


def _expected_q3(
    *,
    users: int,
    actions: int,
    coalition_user_ids: np.ndarray,
    proposed_actions: np.ndarray,
    z3_bits: np.ndarray,
    kappa_bits: float,
) -> np.ndarray:
    """Construct the sparse native action surface with exact zero fill."""

    result = np.zeros((users, actions), dtype=np.float64)
    for index, (user, action) in enumerate(
        zip(coalition_user_ids.tolist(), proposed_actions.tolist())
    ):
        value = float(z3_bits[index]) / kappa_bits
        if value != 0.0:
            result[int(user), int(action)] = value
    if not np.all(np.isfinite(result)):
        raise CoalitionResidualC3Error("q3_values arithmetic is non-finite")
    return result


def _close(left: float, right: float, *, scale: float = 1.0) -> bool:
    """Use a tight floating comparison for independently supplied scalars."""

    magnitude = max(1.0, abs(float(left)), abs(float(right)))
    tolerance = max(1.0e-12 * scale, 1024.0 * np.finfo(np.float64).eps * magnitude)
    return math.isfinite(float(left)) and math.isfinite(float(right)) and abs(left - right) <= tolerance


def _identity_roundoff_scale(
    result: "CoalitionResidualC3Result", computed: dict[str, Any]
) -> float:
    """Return the absolute work scale of the coalition identity arithmetic.

    The identity can be a small residual of much larger unilateral, joint,
    and energy-priced terms.  Scaling its floating-point guard only by the
    final left and right sides therefore produces a false failure under
    ordinary cancellation.  This scale contains the actual delta-domain
    operands and derived components, without using the much larger common
    reference totals that algebraically cancel before the identity is formed.
    """

    reference_bits = np.asarray(result.reference_bits, dtype=np.float64)
    unilateral_delta_bits = (
        np.asarray(result.unilateral_bits, dtype=np.float64)
        - reference_bits[None, :]
    )
    joint_delta_bits_by_user = (
        np.asarray(result.joint_bits, dtype=np.float64) - reference_bits
    )
    unilateral_delta_energy = (
        np.asarray(result.unilateral_energy_j, dtype=np.float64)
        - float(result.reference_energy_j)
    )
    joint_delta_energy = float(result.joint_energy_j) - float(result.reference_energy_j)
    multiplier = float(result.lambda_bits_per_j)

    terms: list[float] = [
        *(abs(float(value)) for value in unilateral_delta_bits.reshape(-1)),
        *(abs(float(value)) for value in joint_delta_bits_by_user.reshape(-1)),
        *(multiplier * abs(float(value)) for value in unilateral_delta_energy),
        multiplier * abs(joint_delta_energy),
    ]
    for field in ("own_bits", "nonfocal_bits", "z3_bits", "combined_bits"):
        terms.extend(
            abs(float(value))
            for value in np.asarray(computed[field], dtype=np.float64).reshape(-1)
        )
    for field in (
        "joint_delta_bits",
        "joint_surplus_bits",
        "interaction_bits",
        "interaction_surplus_bits",
        "equal_share_bits",
    ):
        terms.append(abs(float(computed[field])))
    terms.extend(
        (
            multiplier * abs(float(computed["joint_delta_energy_j"])),
            multiplier * abs(float(computed["interaction_energy_j"])),
        )
    )
    return max(1.0, _safe_sum(terms, field="identity_roundoff_scale"))


@dataclass(frozen=True)
class CoalitionResidualC3Result:
    """Immutable named-coalition V0.22 C3 residual and sparse Q3 surface.

    The object describes one complete named coalition at one current slot.
    It does not assert correctness for a partially adopted or arbitrary
    hybrid profile, a learned sum of Q heads, or deployment closure.
    """

    reference_bits: np.ndarray
    reference_energy_j: float
    unilateral_bits: np.ndarray
    unilateral_energy_j: np.ndarray
    joint_bits: np.ndarray
    joint_energy_j: float
    coalition_user_ids: np.ndarray
    proposed_actions: np.ndarray
    lambda_bits_per_j: float
    kappa_bits: float
    action_count: int
    reference_actions: np.ndarray
    legal_mask: np.ndarray
    own_bits: np.ndarray
    nonfocal_bits: np.ndarray
    d_bits: np.ndarray
    joint_delta_bits: float
    joint_delta_energy_j: float
    joint_surplus_bits: float
    interaction_bits: float
    interaction_energy_j: float
    interaction_surplus_bits: float
    equal_share_bits: float
    z3_bits: np.ndarray
    combined_bits: np.ndarray
    identity_residual_bits: float
    q3_values: np.ndarray
    schema: str = COALITION_RESIDUAL_C3_SCHEMA

    def __post_init__(self) -> None:
        """Seal all arrays and reject forged or inconsistent target fields."""

        # Validate and normalize structural inputs before deriving the user
        # and action dimensions used by every other field.
        b0 = _float_array(self.reference_bits, field="reference_bits", nonnegative=True)
        if b0.ndim != 1 or b0.size < 1:
            raise CoalitionResidualC3Error("reference_bits must have shape (U,) with U >= 1")
        users = int(b0.size)
        actions = _action_count(self.action_count)
        legal = _legal_mask(self.legal_mask, users=users, actions=actions)
        refs = _int_vector(self.reference_actions, field="reference_actions", size=users)
        ids = _int_vector(self.coalition_user_ids, field="coalition_user_ids")
        proposed = _int_vector(
            self.proposed_actions,
            field="proposed_actions",
            size=int(ids.size),
        )
        bu = _float_array(
            self.unilateral_bits,
            field="unilateral_bits",
            shape=(int(ids.size), users),
            nonnegative=True,
        )
        eu = _float_array(
            self.unilateral_energy_j,
            field="unilateral_energy_j",
            shape=(int(ids.size),),
        )
        if np.any(eu <= 0.0):
            raise CoalitionResidualC3Error("unilateral_energy_j must be positive")
        bc = _float_array(self.joint_bits, field="joint_bits", shape=(users,), nonnegative=True)
        e0 = _float_scalar(self.reference_energy_j, field="reference_energy_j", positive=True)
        ec = _float_scalar(self.joint_energy_j, field="joint_energy_j", positive=True)
        multiplier = _float_scalar(
            self.lambda_bits_per_j, field="lambda_bits_per_j", positive=True
        )
        kappa = _float_scalar(self.kappa_bits, field="kappa_bits", positive=True)
        _validate_action_profile(
            reference_actions=refs,
            legal_mask=legal,
            coalition_user_ids=ids,
            proposed_actions=proposed,
        )

        component_arrays: dict[str, np.ndarray] = {}
        for field in (
            "own_bits",
            "nonfocal_bits",
            "d_bits",
            "z3_bits",
            "combined_bits",
        ):
            component_arrays[field] = _float_array(
                getattr(self, field),
                field=field,
                shape=(int(ids.size),),
            )
        q3 = _float_array(
            self.q3_values,
            field="q3_values",
            shape=(users, actions),
        )
        scalar_values: dict[str, float] = {}
        for field in (
            "joint_delta_bits",
            "joint_delta_energy_j",
            "joint_surplus_bits",
            "interaction_bits",
            "interaction_energy_j",
            "interaction_surplus_bits",
            "equal_share_bits",
            "identity_residual_bits",
        ):
            scalar_values[field] = _float_scalar(getattr(self, field), field=field)
        if self.schema != COALITION_RESIDUAL_C3_SCHEMA:
            raise CoalitionResidualC3Error("coalition residual C3 schema is stale")

        object.__setattr__(self, "reference_bits", _readonly(b0, dtype=np.float64))
        object.__setattr__(self, "reference_energy_j", e0)
        object.__setattr__(self, "unilateral_bits", _readonly(bu, dtype=np.float64))
        object.__setattr__(self, "unilateral_energy_j", _readonly(eu, dtype=np.float64))
        object.__setattr__(self, "joint_bits", _readonly(bc, dtype=np.float64))
        object.__setattr__(self, "joint_energy_j", ec)
        object.__setattr__(self, "coalition_user_ids", _readonly(ids, dtype=np.int64))
        object.__setattr__(self, "proposed_actions", _readonly(proposed, dtype=np.int64))
        object.__setattr__(self, "lambda_bits_per_j", multiplier)
        object.__setattr__(self, "kappa_bits", kappa)
        object.__setattr__(self, "action_count", actions)
        object.__setattr__(self, "reference_actions", _readonly(refs, dtype=np.int64))
        object.__setattr__(self, "legal_mask", _readonly(legal, dtype=np.bool_))
        for field, value in component_arrays.items():
            object.__setattr__(self, field, _readonly(value, dtype=np.float64))
        for field, value in scalar_values.items():
            object.__setattr__(self, field, value)
        object.__setattr__(self, "q3_values", _readonly(q3, dtype=np.float64))

        # The public frozen constructor is guarded as well as the builder: a
        # caller cannot forge a sparse surface or a mismatched formula result.
        self.verify()

    @property
    def users(self) -> int:
        """Number of users in the reference profile."""

        return int(self.reference_bits.size)

    @property
    def members(self) -> int:
        """Number of named coalition members."""

        return int(self.coalition_user_ids.size)

    @property
    def A(self) -> int:
        """Action width alias for the mathematical ``A`` notation."""

        return self.action_count

    # Mathematical notation aliases retained as read-only properties for
    # formula audits and small probes.
    @property
    def B0_v(self) -> np.ndarray:
        return self.reference_bits

    @property
    def E0(self) -> float:
        return self.reference_energy_j

    @property
    def Bu(self) -> np.ndarray:
        return self.unilateral_bits

    @property
    def Eu(self) -> np.ndarray:
        return self.unilateral_energy_j

    @property
    def BC(self) -> np.ndarray:
        return self.joint_bits

    @property
    def EC(self) -> float:
        return self.joint_energy_j

    @property
    def own_i(self) -> np.ndarray:
        return self.own_bits

    @property
    def nonfocal_i(self) -> np.ndarray:
        return self.nonfocal_bits

    @property
    def d_i(self) -> np.ndarray:
        return self.d_bits

    @property
    def z3_i(self) -> np.ndarray:
        return self.z3_bits

    @property
    def combined_i(self) -> np.ndarray:
        return self.combined_bits

    @property
    def joint_delta_energy(self) -> float:
        return self.joint_delta_energy_j

    @property
    def interaction_energy(self) -> float:
        return self.interaction_energy_j

    def verify(self) -> float:
        """Fail closed unless every formula component and sparse cell agrees.

        Returns the sealed identity residual in bits.  A small residual is
        accepted only at floating-point roundoff scale; a material residual
        raises :class:`CoalitionResidualC3Error`.
        """

        computed = _compute_components(
            reference_bits=np.asarray(self.reference_bits, dtype=np.float64),
            reference_energy_j=float(self.reference_energy_j),
            unilateral_bits=np.asarray(self.unilateral_bits, dtype=np.float64),
            unilateral_energy_j=np.asarray(self.unilateral_energy_j, dtype=np.float64),
            joint_bits=np.asarray(self.joint_bits, dtype=np.float64),
            joint_energy_j=float(self.joint_energy_j),
            coalition_user_ids=np.asarray(self.coalition_user_ids, dtype=np.int64),
            lambda_bits_per_j=float(self.lambda_bits_per_j),
        )
        for field in (
            "own_bits",
            "nonfocal_bits",
            "d_bits",
            "z3_bits",
            "combined_bits",
        ):
            supplied = np.asarray(getattr(self, field), dtype=np.float64)
            expected = np.asarray(computed[field], dtype=np.float64)
            if not np.array_equal(supplied, expected):
                raise CoalitionResidualC3Error(f"{field} does not match the coalition formula")
        for field in (
            "joint_delta_bits",
            "joint_delta_energy_j",
            "joint_surplus_bits",
            "interaction_bits",
            "interaction_energy_j",
            "interaction_surplus_bits",
            "equal_share_bits",
        ):
            supplied = float(getattr(self, field))
            expected = float(computed[field])
            if not _close(supplied, expected):
                raise CoalitionResidualC3Error(f"{field} does not match the coalition formula")

        expected_q3 = _expected_q3(
            users=self.users,
            actions=self.action_count,
            coalition_user_ids=np.asarray(self.coalition_user_ids, dtype=np.int64),
            proposed_actions=np.asarray(self.proposed_actions, dtype=np.int64),
            z3_bits=np.asarray(self.z3_bits, dtype=np.float64),
            kappa_bits=float(self.kappa_bits),
        )
        if not np.array_equal(np.asarray(self.q3_values), expected_q3):
            raise CoalitionResidualC3Error("q3_values do not match the sparse coalition surface")

        lhs = _safe_sum(self.combined_bits, field="identity")
        rhs = float(self.joint_surplus_bits)
        residual = lhs - rhs
        work_scale = _identity_roundoff_scale(self, computed)
        tolerance = max(1.0e-12, 1024.0 * np.finfo(np.float64).eps * work_scale)
        if not math.isfinite(residual) or abs(residual) > tolerance:
            raise CoalitionResidualC3Error(
                "coalition C3 identity failed: sum(combined_i) does not equal "
                "joint_surplus "
                f"(lhs={lhs.hex()}, rhs={rhs.hex()}, residual={residual.hex()}, "
                f"tolerance={tolerance.hex()}, work_scale={work_scale.hex()})"
            )
        if not _close(float(self.identity_residual_bits), residual, scale=1.0):
            raise CoalitionResidualC3Error(
                "identity_residual_bits disagrees with the coalition formula"
            )
        return float(self.identity_residual_bits)


def build_coalition_residual_c3(
    B0_v: object,
    E0: object,
    Bu: object,
    Eu: object,
    BC: object,
    EC: object,
    coalition_user_ids: object,
    proposed_actions: object,
    lambda_bits_per_j: object,
    kappa_bits: object,
    reference_actions: object,
    legal_mask: object,
    action_count: object = COALITION_RESIDUAL_C3_DEFAULT_ACTION_COUNT,
    *,
    A: object | None = None,
) -> CoalitionResidualC3Result:
    """Build one immutable V0.22 named-coalition C3 residual target.

    ``B0_v``, ``E0``, ``Bu``, ``Eu``, ``BC``, and ``EC`` are respectively the
    reference user-bit vector and energy, unilateral member-by-user bit
    matrix and energies, and joint coalition user-bit vector and energy.
    ``A`` is accepted as a spelling alias for ``action_count``.  Every
    proposed action must be legal for its named user and differ from that
    user's reference action.

    This builder is a pure formula adapter.  The identity is for one complete
    named coalition only; it is not exact for partial adoption, arbitrary
    hybrid profiles, learned Q sums, or deployment closure.  The equal
    interaction share is fixed for this probe and is not tunable.
    """

    if A is not None:
        explicit = _action_count(action_count)
        alias = _action_count(A, field="A")
        # The default width is intentionally replaceable through A, while a
        # conflicting explicit non-default width is rejected as ambiguous.
        if explicit != COALITION_RESIDUAL_C3_DEFAULT_ACTION_COUNT and explicit != alias:
            raise CoalitionResidualC3Error("action_count and A disagree")
        action_count = alias
    values = _validate_inputs(
        reference_bits=B0_v,
        reference_energy_j=E0,
        unilateral_bits=Bu,
        unilateral_energy_j=Eu,
        joint_bits=BC,
        joint_energy_j=EC,
        coalition_user_ids=coalition_user_ids,
        proposed_actions=proposed_actions,
        lambda_bits_per_j=lambda_bits_per_j,
        kappa_bits=kappa_bits,
        action_count=action_count,
        reference_actions=reference_actions,
        legal_mask=legal_mask,
    )
    components = _compute_components(
        reference_bits=values["reference_bits"],
        reference_energy_j=values["reference_energy_j"],
        unilateral_bits=values["unilateral_bits"],
        unilateral_energy_j=values["unilateral_energy_j"],
        joint_bits=values["joint_bits"],
        joint_energy_j=values["joint_energy_j"],
        coalition_user_ids=values["coalition_user_ids"],
        lambda_bits_per_j=values["lambda_bits_per_j"],
    )
    q3 = _expected_q3(
        users=values["reference_bits"].size,
        actions=values["action_count"],
        coalition_user_ids=values["coalition_user_ids"],
        proposed_actions=values["proposed_actions"],
        z3_bits=components["z3_bits"],
        kappa_bits=values["kappa_bits"],
    )
    return CoalitionResidualC3Result(
        reference_bits=values["reference_bits"],
        reference_energy_j=values["reference_energy_j"],
        unilateral_bits=values["unilateral_bits"],
        unilateral_energy_j=values["unilateral_energy_j"],
        joint_bits=values["joint_bits"],
        joint_energy_j=values["joint_energy_j"],
        coalition_user_ids=values["coalition_user_ids"],
        proposed_actions=values["proposed_actions"],
        lambda_bits_per_j=values["lambda_bits_per_j"],
        kappa_bits=values["kappa_bits"],
        action_count=values["action_count"],
        reference_actions=values["reference_actions"],
        legal_mask=values["legal_mask"],
        **components,
        q3_values=q3,
    )


# Descriptive/versioned aliases keep this pure seam discoverable without
# adding another implementation.
build_c3_coalition_residual = build_coalition_residual_c3
build_coalition_residual_surface = build_coalition_residual_c3
build_v022_c3_coalition_residual = build_coalition_residual_c3
compute_coalition_residual_c3 = build_coalition_residual_c3
CoalitionResidualC3 = CoalitionResidualC3Result
V022CoalitionResidualC3Result = CoalitionResidualC3Result


__all__ = [
    "COALITION_RESIDUAL_C3_DEFAULT_ACTION_COUNT",
    "COALITION_RESIDUAL_C3_SCHEMA",
    "COALITION_RESIDUAL_C3_SCHEMA_VERSION",
    "CoalitionResidualC3",
    "CoalitionResidualC3ContractError",
    "CoalitionResidualC3Error",
    "CoalitionResidualC3Result",
    "V022_C3_COALITION_RESIDUAL_SCHEMA",
    "V022_C3_COALITION_RESIDUAL_SCHEMA_VERSION",
    "V022CoalitionResidualC3Result",
    "build_c3_coalition_residual",
    "build_coalition_residual_c3",
    "build_coalition_residual_surface",
    "build_v022_c3_coalition_residual",
    "compute_coalition_residual_c3",
]
