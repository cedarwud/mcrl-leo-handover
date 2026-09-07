"""Minimal real-environment opening source for Multi-Catfish MCRL V0.3.

This module is deliberately a producer *seam*, not a Catfish policy.  The
caller supplies a sealed observation, a reference joint action, a candidate
joint action, and all source provenance.  The producer only validates the
unilateral intervention, evaluates both actions through the canonical
multi-user environment, and projects the one raw comparison into the C1 and
C3 route views.

Anchor/user/action selection remains outside this module.  In particular,
there is no C1 EXP/ACRM selector and no C3 load/activation selector here.
Those policies must choose inputs before this producer is called.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

import numpy as np

from ..env.action_contract import (
    Association,
    NO_OP_ACTION,
    SlotTable,
    assert_selected_actions_valid,
)
from ..env.keyed_fading import KeyedFadingField
from ..env.step import ActionEvaluation, StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_opening_pairs import (
    EEAxisOpeningPair,
    OpeningPairContractError,
    build_opening_pair,
)
from .ee_axis_state import (
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
    EEAxisStateContractError,
    EEAxisStateObservation,
    encode_ee_axis_state,
)


OPENING_SOURCE_SCHEMA = "multi-catfish-mcrl-v03-opening-source-v2"
"""Schema for the route-independent real-physics producer result."""

PhysicalKey = tuple[int, int]
PhysicalKeyOrNone = PhysicalKey | None


class OpeningSourceContractError(OpeningPairContractError):
    """A proposed real-environment opening source is not admissible."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise OpeningSourceContractError(f"{field} must be lowercase SHA-256")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise OpeningSourceContractError(f"{field} must be a nonempty trimmed string")
    return value


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _float_hex_list(value: np.ndarray) -> list[str]:
    return [float(item).hex() for item in np.asarray(value).tolist()]


def _immutable_array(
    value: object,
    *,
    field: str,
    dtype: np.dtype[Any],
    ndim: int,
) -> np.ndarray:
    try:
        array = np.asarray(value)
        if array.ndim != ndim:
            raise OpeningSourceContractError(
                f"{field} must be {ndim}-dimensional"
            )
        copied = np.array(array, dtype=dtype, copy=True, order="C")
    except OpeningSourceContractError:
        raise
    except (TypeError, ValueError) as error:
        raise OpeningSourceContractError(f"{field} has an invalid dtype") from error
    if np.issubdtype(copied.dtype, np.floating) and not np.all(np.isfinite(copied)):
        raise OpeningSourceContractError(f"{field} must be finite")
    copied.setflags(write=False)
    return copied


@dataclass(frozen=True)
class OpeningSourceProvenance:
    """Explicit provenance supplied by the sealed C1/C3 source scheduler."""

    source_policy_version: int
    anchor_sha256: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    common_random_field_sha256: str
    c1_source_rule: str
    c3_source_rule: str
    admitted_route: str

    def verify(self) -> None:
        if (
            type(self.source_policy_version) is not int
            or self.source_policy_version <= 0
        ):
            raise OpeningSourceContractError(
                "source_policy_version must be a positive exact integer"
            )
        for field in (
            "anchor_sha256",
            "source_manifest_sha256",
            "checkpoint_sha256",
            "common_random_field_sha256",
        ):
            _digest(getattr(self, field), field=field)
        _text(self.c1_source_rule, field="c1_source_rule")
        _text(self.c3_source_rule, field="c3_source_rule")
        if self.admitted_route not in ("C1", "C3"):
            raise OpeningSourceContractError("admitted_route must be C1 or C3")


@dataclass(frozen=True)
class EEAxisOpeningRawPair:
    """One route-independent physical comparison and its shared lineage."""

    source_policy_version: int
    anchor_sha256: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    common_random_field_sha256: str
    state_schema: str
    state_schema_sha256: str
    state_observation_sha256: str
    focal_user: int
    state: np.ndarray
    action_mask: np.ndarray
    reference_action: int
    candidate_action: int
    reference_joint_actions: np.ndarray
    candidate_joint_actions: np.ndarray
    reference_physical_keys: tuple[PhysicalKeyOrNone, ...]
    candidate_physical_keys: tuple[PhysicalKeyOrNone, ...]
    reference_rates_bps: np.ndarray
    candidate_rates_bps: np.ndarray
    reference_system_power_w: float
    candidate_system_power_w: float
    lambda_bits_per_j: float
    interval_s: float
    comparison_sha256: str

    def verify(self) -> str:
        """Verify the route-independent raw-comparison digest."""

        if self.state_schema != EE_AXIS_STATE_SCHEMA:
            raise OpeningSourceContractError("raw opening state schema is stale")
        if self.state_schema_sha256 != EE_AXIS_STATE_SCHEMA_SHA256:
            raise OpeningSourceContractError("raw opening state schema digest drifted")
        _digest(self.state_observation_sha256, field="state_observation_sha256")
        if np.asarray(self.state).shape != (EE_AXIS_STATE_DIM,):
            raise OpeningSourceContractError(
                f"raw opening state must have shape ({EE_AXIS_STATE_DIM},)"
            )
        supplied = _digest(self.comparison_sha256, field="comparison_sha256")
        actual = _canonical_sha256(_raw_payload(self))
        if supplied != actual:
            raise OpeningSourceContractError(
                "raw opening comparison digest disagrees with its payload"
            )
        return actual


@dataclass(frozen=True)
class EEAxisOpeningRouteView:
    """A Q1/Q3-compatible route projection of one raw comparison."""

    route: str
    raw_comparison_sha256: str
    pair: EEAxisOpeningPair

    def as_pair(self) -> EEAxisOpeningPair:
        """Return the existing adapter record for route batching/updating."""

        return self.pair

    def verify(self) -> str:
        if self.route not in ("C1", "C3"):
            raise OpeningSourceContractError("route view must be C1 or C3")
        if self.pair.source_route != self.route:
            raise OpeningSourceContractError(
                "route view and opening pair disagree about the source route"
            )
        _digest(self.raw_comparison_sha256, field="raw_comparison_sha256")
        return self.pair.verify()


@dataclass(frozen=True)
class EEAxisOpeningSourceResult:
    """Matched evaluations plus shared raw and route-qualified views."""

    raw_pair: EEAxisOpeningRawPair
    reference_evaluation: ActionEvaluation
    candidate_evaluation: ActionEvaluation
    c1: EEAxisOpeningRouteView
    c3: EEAxisOpeningRouteView
    admitted_route: str

    @property
    def route_views(self) -> tuple[EEAxisOpeningRouteView, EEAxisOpeningRouteView]:
        return self.c1, self.c3

    def route_view(self, route: str) -> EEAxisOpeningRouteView:
        if route == "C1":
            return self.c1
        if route == "C3":
            return self.c3
        raise OpeningSourceContractError("route must be C1 or C3")

    def verify(self) -> str:
        """Verify raw lineage, both adapter records, and evaluation parity."""

        raw_digest = self.raw_pair.verify()
        if self.admitted_route not in ("C1", "C3"):
            raise OpeningSourceContractError("admitted route must be C1 or C3")
        for view in self.route_views:
            if view.raw_comparison_sha256 != raw_digest:
                raise OpeningSourceContractError(
                    "route view is not attached to the shared raw comparison"
                )
            view.verify()
            _assert_pair_matches_raw(view.pair, self.raw_pair)
        if not np.array_equal(
            self.reference_evaluation.link_rate_bps,
            self.raw_pair.reference_rates_bps,
        ) or not np.array_equal(
            self.candidate_evaluation.link_rate_bps,
            self.raw_pair.candidate_rates_bps,
        ):
            raise OpeningSourceContractError(
                "raw opening rates disagree with matched evaluations"
            )
        if (
            float(self.reference_evaluation.system_power_w)
            != self.raw_pair.reference_system_power_w
            or float(self.candidate_evaluation.system_power_w)
            != self.raw_pair.candidate_system_power_w
        ):
            raise OpeningSourceContractError(
                "raw opening powers disagree with matched evaluations"
            )
        return raw_digest


def _raw_payload(raw: EEAxisOpeningRawPair) -> dict[str, object]:
    return {
        "schema": OPENING_SOURCE_SCHEMA,
        "source_policy_version": raw.source_policy_version,
        "anchor_sha256": raw.anchor_sha256,
        "source_manifest_sha256": raw.source_manifest_sha256,
        "checkpoint_sha256": raw.checkpoint_sha256,
        "common_random_field_sha256": raw.common_random_field_sha256,
        "state_schema": raw.state_schema,
        "state_schema_sha256": raw.state_schema_sha256,
        "state_observation_sha256": raw.state_observation_sha256,
        "focal_user": raw.focal_user,
        "state": _float_hex_list(raw.state),
        "action_mask": [bool(item) for item in raw.action_mask.tolist()],
        "reference_action": raw.reference_action,
        "candidate_action": raw.candidate_action,
        "reference_joint_actions": [
            int(item) for item in raw.reference_joint_actions.tolist()
        ],
        "candidate_joint_actions": [
            int(item) for item in raw.candidate_joint_actions.tolist()
        ],
        "reference_physical_keys": [
            None if key is None else [int(key[0]), int(key[1])]
            for key in raw.reference_physical_keys
        ],
        "candidate_physical_keys": [
            None if key is None else [int(key[0]), int(key[1])]
            for key in raw.candidate_physical_keys
        ],
        "reference_rates_bps": _float_hex_list(raw.reference_rates_bps),
        "candidate_rates_bps": _float_hex_list(raw.candidate_rates_bps),
        "reference_system_power_w": float(raw.reference_system_power_w).hex(),
        "candidate_system_power_w": float(raw.candidate_system_power_w).hex(),
        "lambda_bits_per_j": float(raw.lambda_bits_per_j).hex(),
        "interval_s": float(raw.interval_s).hex(),
    }


def _physical_key(table: SlotTable, action: int) -> tuple[int, int] | None:
    if action == NO_OP_ACTION:
        return None
    association = table.association(action)
    if not isinstance(association, Association):
        return None
    return int(association.norad_id), int(association.cell_id)


def _physical_keys(
    actions: np.ndarray, slot_tables: tuple[SlotTable, ...]
) -> tuple[PhysicalKeyOrNone, ...]:
    return tuple(
        _physical_key(table, int(action))
        for table, action in zip(slot_tables, actions.tolist(), strict=True)
    )


def _action_vector(
    value: object, *, field: str, num_users: int
) -> np.ndarray:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise OpeningSourceContractError(f"{field} must be an integer vector") from error
    if array.ndim != 1 or array.shape != (num_users,):
        raise OpeningSourceContractError(
            f"{field} must have shape ({num_users},)"
        )
    if (
        not np.issubdtype(array.dtype, np.integer)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        raise OpeningSourceContractError(f"{field} must have integer dtype")
    return np.array(array, dtype=np.int64, copy=True)


def _assert_current_anchor(
    environment: StepEnvironment, observation: StepObservation
) -> tuple[SlotTable, ...]:
    if not isinstance(observation, StepObservation):
        raise OpeningSourceContractError(
            "observation must be the sealed StepObservation returned by reset/step"
        )
    current = getattr(environment, "_candidates", None)
    if current is None or current is not observation.candidates:
        raise OpeningSourceContractError(
            "observation is not the environment's current sealed anchor"
        )
    if observation.step_index != environment.driver.step_index:
        raise OpeningSourceContractError("observation step does not match the anchor")
    expected_masks = observation.candidates.masks
    if not np.array_equal(observation.masks, expected_masks):
        raise OpeningSourceContractError(
            "observation masks disagree with the sealed candidate tables"
        )
    return observation.candidates.slot_tables


def _assert_single_focal_difference(
    reference: np.ndarray,
    candidate: np.ndarray,
    *,
    focal_user: int,
    slot_tables: tuple[SlotTable, ...],
) -> None:
    changed_indices = np.flatnonzero(reference != candidate).tolist()
    if changed_indices != [focal_user]:
        raise OpeningSourceContractError(
            "opening branches must differ in exactly the focal action"
        )
    reference_keys = tuple(
        _physical_key(table, int(action))
        for table, action in zip(slot_tables, reference.tolist(), strict=True)
    )
    candidate_keys = tuple(
        _physical_key(table, int(action))
        for table, action in zip(slot_tables, candidate.tolist(), strict=True)
    )
    changed_physical = [
        uid
        for uid, (left, right) in enumerate(zip(reference_keys, candidate_keys, strict=True))
        if left != right
    ]
    if changed_physical != [focal_user]:
        raise OpeningSourceContractError(
            "opening branches must differ in exactly one focal physical action"
        )


def _assert_pair_matches_raw(
    pair: EEAxisOpeningPair, raw: EEAxisOpeningRawPair
) -> None:
    fields = (
        "source_policy_version",
        "anchor_sha256",
        "source_manifest_sha256",
        "checkpoint_sha256",
        "common_random_field_sha256",
        "focal_user",
        "reference_action",
        "candidate_action",
        "reference_system_power_w",
        "candidate_system_power_w",
        "lambda_bits_per_j",
        "interval_s",
    )
    for field in fields:
        if getattr(pair, field) != getattr(raw, field):
            raise OpeningSourceContractError(
                f"route pair field {field} disagrees with raw lineage"
            )
    for field in (
        "state",
        "action_mask",
        "reference_joint_actions",
        "candidate_joint_actions",
        "reference_rates_bps",
        "candidate_rates_bps",
    ):
        if not np.array_equal(getattr(pair, field), getattr(raw, field)):
            raise OpeningSourceContractError(
                f"route pair array {field} disagrees with raw lineage"
            )


def _raw_from_evaluations(
    *,
    provenance: OpeningSourceProvenance,
    focal_user: int,
    state_observation: EEAxisStateObservation,
    slot_tables: tuple[SlotTable, ...],
    reference: np.ndarray,
    candidate: np.ndarray,
    reference_evaluation: ActionEvaluation,
    candidate_evaluation: ActionEvaluation,
    lambda_bits_per_j: float,
    interval_s: float,
) -> EEAxisOpeningRawPair:
    state = _immutable_array(
        state_observation.state_matrix[focal_user],
        field="focal state",
        dtype=np.dtype(np.float32),
        ndim=1,
    )
    action_mask = _immutable_array(
        state_observation.action_masks[focal_user],
        field="focal action mask",
        dtype=np.dtype(np.bool_),
        ndim=1,
    )
    raw = EEAxisOpeningRawPair(
        source_policy_version=provenance.source_policy_version,
        anchor_sha256=provenance.anchor_sha256,
        source_manifest_sha256=provenance.source_manifest_sha256,
        checkpoint_sha256=provenance.checkpoint_sha256,
        common_random_field_sha256=provenance.common_random_field_sha256,
        state_schema=state_observation.schema,
        state_schema_sha256=state_observation.schema_sha256,
        state_observation_sha256=state_observation.state_sha256,
        focal_user=focal_user,
        state=state,
        action_mask=action_mask,
        reference_action=int(reference[focal_user]),
        candidate_action=int(candidate[focal_user]),
        reference_joint_actions=_immutable_array(
            reference,
            field="reference_joint_actions",
            dtype=np.dtype(np.int64),
            ndim=1,
        ),
        candidate_joint_actions=_immutable_array(
            candidate,
            field="candidate_joint_actions",
            dtype=np.dtype(np.int64),
            ndim=1,
        ),
        reference_physical_keys=_physical_keys(reference, slot_tables),
        candidate_physical_keys=_physical_keys(candidate, slot_tables),
        reference_rates_bps=_immutable_array(
            reference_evaluation.link_rate_bps,
            field="reference_rates_bps",
            dtype=np.dtype(np.float64),
            ndim=1,
        ),
        candidate_rates_bps=_immutable_array(
            candidate_evaluation.link_rate_bps,
            field="candidate_rates_bps",
            dtype=np.dtype(np.float64),
            ndim=1,
        ),
        reference_system_power_w=float(reference_evaluation.system_power_w),
        candidate_system_power_w=float(candidate_evaluation.system_power_w),
        lambda_bits_per_j=float(lambda_bits_per_j),
        interval_s=float(interval_s),
        comparison_sha256="0" * 64,
    )
    digest = _canonical_sha256(_raw_payload(raw))
    return EEAxisOpeningRawPair(
        **{**raw.__dict__, "comparison_sha256": digest}
    )


def produce_opening_comparison(
    environment: StepEnvironment,
    *,
    observation: StepObservation,
    state_observation: EEAxisStateObservation,
    reference_actions: object,
    candidate_actions: object,
    focal_user: int,
    common_random_field: KeyedFadingField,
    provenance: OpeningSourceProvenance,
    rng: np.random.Generator,
    lambda_bits_per_j: float,
    interval_s: float,
) -> EEAxisOpeningSourceResult:
    """Produce one matched full-system opening comparison.

    The caller must already have selected the sealed anchor, focal user, and
    two joint action vectors.  No source policy is inferred here.  Both
    branches are evaluated at the current anchor through
    :meth:`StepEnvironment.evaluate_actions`; neither branch is committed.
    """

    if not isinstance(environment, StepEnvironment):
        raise OpeningSourceContractError("environment must be StepEnvironment")
    if not isinstance(provenance, OpeningSourceProvenance):
        raise OpeningSourceContractError(
            "provenance must be OpeningSourceProvenance"
        )
    provenance.verify()
    if not isinstance(common_random_field, KeyedFadingField):
        raise OpeningSourceContractError(
            "common_random_field must be KeyedFadingField"
        )
    if not isinstance(rng, np.random.Generator):
        raise OpeningSourceContractError("rng must be numpy.random.Generator")
    if common_random_field.root_digest != provenance.common_random_field_sha256:
        raise OpeningSourceContractError(
            "provenance common-random digest disagrees with supplied field"
        )
    bound_field = getattr(environment, "_fading_field", None)
    if (
        not isinstance(bound_field, KeyedFadingField)
        or bound_field != common_random_field
        or not bool(environment.physics.fading_enabled)
    ):
        raise OpeningSourceContractError(
            "environment must use the supplied keyed fading field"
        )

    slot_tables = _assert_current_anchor(environment, observation)
    if not isinstance(state_observation, EEAxisStateObservation):
        raise OpeningSourceContractError(
            "state_observation must be an EEAxisStateObservation"
        )
    try:
        state_observation.verify()
        current_state = encode_ee_axis_state(environment, observation)
    except EEAxisStateContractError as error:
        raise OpeningSourceContractError(
            f"V0.3 state observation is invalid: {error}"
        ) from error
    if (
        state_observation.state_sha256 != current_state.state_sha256
        or not np.array_equal(state_observation.action_masks, observation.masks)
    ):
        raise OpeningSourceContractError(
            "state_observation does not match the current sealed anchor"
        )
    num_users = observation.num_users
    if type(focal_user) is not int or not 0 <= focal_user < num_users:
        raise OpeningSourceContractError("focal_user is outside the sealed anchor")
    reference = _action_vector(
        reference_actions, field="reference_actions", num_users=num_users
    )
    candidate = _action_vector(
        candidate_actions, field="candidate_actions", num_users=num_users
    )
    try:
        reference = assert_selected_actions_valid(reference, slot_tables)
        candidate = assert_selected_actions_valid(candidate, slot_tables)
    except (MCRLContractError, ValueError) as error:
        raise OpeningSourceContractError(
            f"opening actions are not legal at the sealed anchor: {error}"
        ) from error
    _assert_single_focal_difference(
        reference,
        candidate,
        focal_user=focal_user,
        slot_tables=slot_tables,
    )

    try:
        reference_evaluation = environment.evaluate_actions(reference, rng)
        candidate_evaluation = environment.evaluate_actions(candidate, rng)
    except (MCRLContractError, ValueError, TypeError) as error:
        raise OpeningSourceContractError(
            f"matched opening evaluation failed: {error}"
        ) from error

    raw = _raw_from_evaluations(
        provenance=provenance,
        focal_user=focal_user,
        state_observation=state_observation,
        slot_tables=slot_tables,
        reference=reference,
        candidate=candidate,
        reference_evaluation=reference_evaluation,
        candidate_evaluation=candidate_evaluation,
        lambda_bits_per_j=lambda_bits_per_j,
        interval_s=interval_s,
    )
    raw.verify()

    common = {
        "source_rule": provenance.c1_source_rule,
        "source_policy_version": provenance.source_policy_version,
        "anchor_sha256": provenance.anchor_sha256,
        "source_manifest_sha256": provenance.source_manifest_sha256,
        "checkpoint_sha256": provenance.checkpoint_sha256,
        "common_random_field_sha256": provenance.common_random_field_sha256,
        "focal_user": raw.focal_user,
        "state": raw.state,
        "action_mask": raw.action_mask,
        "reference_action": raw.reference_action,
        "candidate_action": raw.candidate_action,
        "reference_joint_actions": raw.reference_joint_actions,
        "candidate_joint_actions": raw.candidate_joint_actions,
        "reference_rates_bps": raw.reference_rates_bps,
        "candidate_rates_bps": raw.candidate_rates_bps,
        "reference_system_power_w": raw.reference_system_power_w,
        "candidate_system_power_w": raw.candidate_system_power_w,
        "lambda_bits_per_j": raw.lambda_bits_per_j,
        "interval_s": raw.interval_s,
    }
    c1_pair = build_opening_pair(source_route="C1", **common)
    c3_pair = build_opening_pair(
        source_route="C3",
        source_rule=provenance.c3_source_rule,
        **{key: value for key, value in common.items() if key != "source_rule"},
    )
    result = EEAxisOpeningSourceResult(
        raw_pair=raw,
        reference_evaluation=reference_evaluation,
        candidate_evaluation=candidate_evaluation,
        c1=EEAxisOpeningRouteView(
            route="C1",
            raw_comparison_sha256=raw.comparison_sha256,
            pair=c1_pair,
        ),
        c3=EEAxisOpeningRouteView(
            route="C3",
            raw_comparison_sha256=raw.comparison_sha256,
            pair=c3_pair,
        ),
        admitted_route=provenance.admitted_route,
    )
    result.verify()
    return result


__all__ = [
    "EEAxisOpeningRawPair",
    "EEAxisOpeningRouteView",
    "EEAxisOpeningSourceResult",
    "OPENING_SOURCE_SCHEMA",
    "OpeningSourceContractError",
    "OpeningSourceProvenance",
    "produce_opening_comparison",
]
