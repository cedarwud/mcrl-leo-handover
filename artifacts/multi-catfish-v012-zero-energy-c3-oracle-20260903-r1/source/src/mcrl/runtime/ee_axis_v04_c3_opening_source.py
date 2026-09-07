"""V0.4 C3-only matched opening-comparison producer.

This is a new source seam for the V0.4 victim-burden observation.  The
sealed V0.3 opening producer and state schema remain untouched.  Anchor and
action selection stay outside this module; this producer only admits a
sealed unilateral intervention, evaluates its two branches through the
canonical :meth:`StepEnvironment.evaluate_actions` seam, and projects the
unchanged non-focal rate target through ``build_opening_pair``.
"""

from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib
import json
import math
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
from .ee_axis_state import EEAxisStateContractError
from .ee_axis_v04_c3_state import (
    EE_AXIS_V04_C3_STATE_SCHEMA,
    EE_AXIS_V04_C3_STATE_SCHEMA_SHA256,
    EEAxisV04C3StateContractError,
    EEAxisV04C3StateObservation,
    encode_ee_axis_v04_c3_state,
)
from .ee_axis_v04_c3_selector import (
    C3_V04_INFORMED_SOURCE_RULE,
    C3_V04_NEUTRAL_SOURCE_RULE,
)


V04_C3_OPENING_SOURCE_SCHEMA = "multi-catfish-mcrl-v04-c3-opening-source-v2"
PhysicalKey = tuple[int, int]
PhysicalKeyOrNone = PhysicalKey | None


class V04C3OpeningSourceContractError(OpeningPairContractError):
    """A V0.4 C3 opening comparison is not admissible."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V04C3OpeningSourceContractError(
            f"{field} must be lowercase SHA-256"
        )
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise V04C3OpeningSourceContractError(
            f"{field} must be a nonempty trimmed string"
        )
    return value


def _positive(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.number)
    ):
        raise V04C3OpeningSourceContractError(
            f"{field} must be finite and positive"
        )
    converted = float(value)
    if not math.isfinite(converted) or converted <= 0.0:
        raise V04C3OpeningSourceContractError(
            f"{field} must be finite and positive"
        )
    return converted


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


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
            raise V04C3OpeningSourceContractError(
                f"{field} must be {ndim}-dimensional"
            )
        copied = np.array(array, dtype=dtype, copy=True, order="C")
    except V04C3OpeningSourceContractError:
        raise
    except (TypeError, ValueError) as error:
        raise V04C3OpeningSourceContractError(
            f"{field} has an invalid dtype"
        ) from error
    if np.issubdtype(copied.dtype, np.floating) and not np.all(
        np.isfinite(copied)
    ):
        raise V04C3OpeningSourceContractError(f"{field} must be finite")
    copied.setflags(write=False)
    return copied


def _action_vector(
    value: object, *, field: str, num_users: int
) -> np.ndarray:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise V04C3OpeningSourceContractError(
            f"{field} must be an integer vector"
        ) from error
    if array.ndim != 1 or array.shape != (num_users,):
        raise V04C3OpeningSourceContractError(
            f"{field} must have shape ({num_users},)"
        )
    if (
        not np.issubdtype(array.dtype, np.integer)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        raise V04C3OpeningSourceContractError(
            f"{field} must have integer dtype"
        )
    return np.array(array, dtype=np.int64, copy=True)


def _physical_key(table: SlotTable, action: int) -> PhysicalKeyOrNone:
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


def _physical_key_payload(value: PhysicalKeyOrNone) -> list[int] | None:
    return None if value is None else [int(value[0]), int(value[1])]


def _verify_physical_key(
    value: object, *, field: str, allow_none: bool
) -> PhysicalKeyOrNone:
    if value is None and allow_none:
        return None
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or any(type(item) is not int for item in value)
    ):
        raise V04C3OpeningSourceContractError(f"{field} is malformed")
    return value


def _assert_anchor(
    environment: StepEnvironment, observation: StepObservation
) -> tuple[SlotTable, ...]:
    if not isinstance(observation, StepObservation):
        raise V04C3OpeningSourceContractError(
            "observation must be the current StepObservation"
        )
    current = getattr(environment, "_candidates", None)
    if current is None or current is not observation.candidates:
        raise V04C3OpeningSourceContractError(
            "observation is not the environment current predecision anchor"
        )
    driver_step = getattr(environment.driver, "step_index", None)
    if observation.step_index != driver_step:
        raise V04C3OpeningSourceContractError(
            "observation step does not match the current anchor"
        )
    expected_masks = observation.candidates.masks
    if not np.array_equal(observation.masks, expected_masks):
        raise V04C3OpeningSourceContractError(
            "observation masks disagree with the candidate tables"
        )
    tables = tuple(observation.candidates.slot_tables)
    if len(tables) != observation.num_users or any(
        not isinstance(table, SlotTable) for table in tables
    ):
        raise V04C3OpeningSourceContractError(
            "anchor slot tables disagree with user count"
        )
    return tables


def _assert_single_focal_difference(
    reference: np.ndarray,
    candidate: np.ndarray,
    *,
    focal_user: int,
    slot_tables: tuple[SlotTable, ...],
) -> tuple[PhysicalKeyOrNone, PhysicalKey]:
    changed_indices = np.flatnonzero(reference != candidate).tolist()
    if changed_indices != [focal_user]:
        raise V04C3OpeningSourceContractError(
            "C3 opening branches must differ in exactly the focal action"
        )
    reference_keys = _physical_keys(reference, slot_tables)
    candidate_keys = _physical_keys(candidate, slot_tables)
    changed_physical = [
        uid
        for uid, (left, right) in enumerate(
            zip(reference_keys, candidate_keys, strict=True)
        )
        if left != right
    ]
    if changed_physical != [focal_user]:
        raise V04C3OpeningSourceContractError(
            "C3 opening branches must differ in exactly one focal physical action"
        )
    reference_key = reference_keys[focal_user]
    candidate_key = candidate_keys[focal_user]
    if candidate_key is None:
        raise V04C3OpeningSourceContractError(
            "C3 candidate must name a physical beam"
        )
    return reference_key, candidate_key


@dataclass(frozen=True)
class V04C3OpeningProvenance:
    """Sealed provenance for one V0.4 C3 informed source invocation."""

    source_policy_version: int
    anchor_sha256: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    common_random_field_sha256: str
    c3_source_rule: str

    def verify(self) -> None:
        if type(self.source_policy_version) is not int or self.source_policy_version <= 0:
            raise V04C3OpeningSourceContractError(
                "source_policy_version must be a positive exact integer"
            )
        for field in (
            "anchor_sha256",
            "source_manifest_sha256",
            "checkpoint_sha256",
            "common_random_field_sha256",
        ):
            _digest(getattr(self, field), field=field)
        _text(self.c3_source_rule, field="c3_source_rule")
        if self.c3_source_rule not in (
            C3_V04_INFORMED_SOURCE_RULE,
            C3_V04_NEUTRAL_SOURCE_RULE,
        ):
            raise V04C3OpeningSourceContractError(
                "c3_source_rule is not a V0.4 victim-burden rule"
            )


def _result_payload(result: "V04C3OpeningComparison") -> dict[str, object]:
    provenance = result.provenance
    return {
        "schema": V04_C3_OPENING_SOURCE_SCHEMA,
        "state_schema": result.state_schema,
        "state_schema_sha256": result.state_schema_sha256,
        "state_observation_sha256": result.state_observation_sha256,
        "kappa_bits": float(result.kappa_bits).hex(),
        "source_policy_version": provenance.source_policy_version,
        "anchor_sha256": provenance.anchor_sha256,
        "source_manifest_sha256": provenance.source_manifest_sha256,
        "checkpoint_sha256": provenance.checkpoint_sha256,
        "common_random_field_sha256": provenance.common_random_field_sha256,
        "c3_source_rule": provenance.c3_source_rule,
        "focal_user": result.pair.focal_user,
        "reference_physical_key": _physical_key_payload(
            result.reference_physical_key
        ),
        "candidate_physical_key": _physical_key_payload(
            result.candidate_physical_key
        ),
        "comparison_sha256": result.pair.comparison_sha256,
    }


@dataclass(frozen=True)
class V04C3OpeningComparison:
    """One immutable V0.4 C3 comparison and its matched evaluations."""

    state_schema: str
    state_schema_sha256: str
    state_observation_sha256: str
    kappa_bits: float
    provenance: V04C3OpeningProvenance
    pair: EEAxisOpeningPair
    reference_physical_key: PhysicalKeyOrNone
    candidate_physical_key: PhysicalKey
    reference_evaluation: ActionEvaluation
    candidate_evaluation: ActionEvaluation
    comparison_sha256: str

    def verify(self) -> str:
        if self.state_schema != EE_AXIS_V04_C3_STATE_SCHEMA:
            raise V04C3OpeningSourceContractError(
                "V0.4 C3 opening state schema is stale"
            )
        if self.state_schema_sha256 != EE_AXIS_V04_C3_STATE_SCHEMA_SHA256:
            raise V04C3OpeningSourceContractError(
                "V0.4 C3 opening state schema digest drifted"
            )
        _digest(
            self.state_observation_sha256,
            field="state_observation_sha256",
        )
        _positive(self.kappa_bits, field="kappa_bits")
        self.provenance.verify()
        if not isinstance(self.pair, EEAxisOpeningPair):
            raise V04C3OpeningSourceContractError("comparison pair is malformed")
        if self.pair.source_route != "C3":
            raise V04C3OpeningSourceContractError(
                "V0.4 C3 comparison must use source_route='C3'"
            )
        self.pair.verify()
        reference_key = _verify_physical_key(
            self.reference_physical_key,
            field="reference_physical_key",
            allow_none=True,
        )
        candidate_key = _verify_physical_key(
            self.candidate_physical_key,
            field="candidate_physical_key",
            allow_none=False,
        )
        if reference_key == candidate_key:
            raise V04C3OpeningSourceContractError(
                "C3 physical candidate matches its reference"
            )
        if (
            self.pair.source_policy_version
            != self.provenance.source_policy_version
            or self.pair.anchor_sha256 != self.provenance.anchor_sha256
            or self.pair.source_manifest_sha256
            != self.provenance.source_manifest_sha256
            or self.pair.checkpoint_sha256 != self.provenance.checkpoint_sha256
            or self.pair.common_random_field_sha256
            != self.provenance.common_random_field_sha256
            or self.pair.source_rule != self.provenance.c3_source_rule
        ):
            raise V04C3OpeningSourceContractError(
                "C3 pair provenance disagrees with V0.4 provenance"
            )
        if not np.array_equal(
            self.reference_evaluation.link_rate_bps,
            self.pair.reference_rates_bps,
        ) or not np.array_equal(
            self.candidate_evaluation.link_rate_bps,
            self.pair.candidate_rates_bps,
        ):
            raise V04C3OpeningSourceContractError(
                "matched evaluations disagree with C3 pair rates"
            )
        if (
            float(self.reference_evaluation.system_power_w)
            != self.pair.reference_system_power_w
            or float(self.candidate_evaluation.system_power_w)
            != self.pair.candidate_system_power_w
        ):
            raise V04C3OpeningSourceContractError(
                "matched evaluations disagree with C3 pair powers"
            )
        focal = self.pair.focal_user
        interval = self.pair.interval_s
        # Match the target constructor's numerically stable attribution:
        # subtract each matched user's rates before summing.  Computing
        # sum(candidate)-sum(reference) can erase a small unilateral effect
        # when both system totals are O(1e12) bit/s.
        delta_rates = (
            self.pair.candidate_rates_bps - self.pair.reference_rates_bps
        )
        expected_zeta3 = interval * math.fsum(
            float(value)
            for index, value in enumerate(delta_rates)
            if index != focal
        )
        if (
            self.pair.zeta3_nonfocal_externality_bits != expected_zeta3
            or self.pair.route_target_surplus_bits != expected_zeta3
        ):
            raise V04C3OpeningSourceContractError(
                "C3 target is not the non-focal delta-rate sum"
            )
        supplied = _digest(self.comparison_sha256, field="comparison_sha256")
        actual = _canonical_sha256(_result_payload(self))
        if supplied != actual:
            raise V04C3OpeningSourceContractError(
                "V0.4 C3 comparison digest disagrees with its payload"
            )
        return actual


def _state_digest_matches(
    environment: StepEnvironment,
    observation: StepObservation,
    supplied: EEAxisV04C3StateObservation,
    *,
    interval_s: float,
    kappa_bits: float,
) -> None:
    if not isinstance(supplied, EEAxisV04C3StateObservation):
        raise V04C3OpeningSourceContractError(
            "state_observation must be an EEAxisV04C3StateObservation"
        )
    try:
        supplied.verify()
        current = encode_ee_axis_v04_c3_state(
            environment,
            observation,
            interval_s=interval_s,
            kappa_bits=kappa_bits,
        )
    except (EEAxisV04C3StateContractError, EEAxisStateContractError) as error:
        raise V04C3OpeningSourceContractError(
            f"V0.4 state observation is invalid: {error}"
        ) from error
    if (
        supplied.state_sha256 != current.state_sha256
        or supplied.schema != current.schema
        or supplied.schema_sha256 != current.schema_sha256
        or not np.array_equal(supplied.action_masks, observation.masks)
    ):
        raise V04C3OpeningSourceContractError(
            "V0.4 state observation does not match the current sealed anchor"
        )


def _evaluation_snapshot(
    environment: StepEnvironment, rng: np.random.Generator
) -> dict[str, object]:
    radiating = getattr(environment, "_previous_radiating", None)
    return {
        "served_rates": np.array(
            getattr(environment, "_previous_served_rate_bps", np.empty(0)),
            dtype=np.float64,
            copy=True,
        ),
        "previous_association": tuple(
            getattr(environment, "_previous_association", ())
        ),
        "previous_demand": dict(getattr(environment, "_previous_demand", {})),
        "link_power": np.array(
            getattr(environment, "_previous_link_power_w", np.empty(0)),
            dtype=np.float64,
            copy=True,
        ),
        "radiating": None
        if radiating is None
        else (
            np.array(radiating.norad_ids, copy=True),
            np.array(radiating.cell_ids, copy=True),
            np.array(radiating.power_w, copy=True),
        ),
        "segments": tuple(getattr(environment, "_segments", ())),
        "step_index": getattr(environment, "_step_index", None),
        "driver_step_index": getattr(environment.driver, "step_index", None),
        "candidate_identity": id(getattr(environment, "_candidates", None)),
        "rng_state": copy.deepcopy(rng.bit_generator.state),
    }


def _assert_evaluation_neutral(
    environment: StepEnvironment,
    rng: np.random.Generator,
    before: dict[str, object],
) -> None:
    after = _evaluation_snapshot(environment, rng)
    for field in (
        "served_rates",
        "link_power",
        "radiating",
    ):
        left = before[field]
        right = after[field]
        if left is None or right is None:
            if left != right:
                raise V04C3OpeningSourceContractError(
                    "evaluate-only opening path changed previous state"
                )
        elif isinstance(left, tuple):
            if len(left) != len(right):
                raise V04C3OpeningSourceContractError(
                    "evaluate-only opening path changed previous radiating state"
                )
            for left_array, right_array in zip(left, right, strict=True):
                if not np.array_equal(left_array, right_array):
                    raise V04C3OpeningSourceContractError(
                        "evaluate-only opening path changed previous radiating state"
                    )
        elif not np.array_equal(left, right):
            raise V04C3OpeningSourceContractError(
                "evaluate-only opening path changed previous served state"
            )
    if (
        before["previous_association"] != after["previous_association"]
        or before["previous_demand"] != after["previous_demand"]
        or before["segments"] != after["segments"]
        or before["step_index"] != after["step_index"]
        or before["driver_step_index"] != after["driver_step_index"]
        or before["candidate_identity"] != after["candidate_identity"]
        or before["rng_state"] != after["rng_state"]
    ):
        raise V04C3OpeningSourceContractError(
            "evaluate-only opening path committed environment state"
        )


def produce_v04_c3_opening_comparison(
    environment: StepEnvironment,
    *,
    observation: StepObservation,
    state_observation: EEAxisV04C3StateObservation,
    reference_actions: object,
    candidate_actions: object,
    focal_user: int,
    common_random_field: KeyedFadingField,
    provenance: V04C3OpeningProvenance,
    rng: np.random.Generator,
    lambda_bits_per_j: float,
    interval_s: float,
    kappa_bits: float,
) -> V04C3OpeningComparison:
    """Produce one matched, unilateral, V0.4 C3 opening comparison."""

    if not isinstance(environment, StepEnvironment):
        raise V04C3OpeningSourceContractError(
            "environment must be StepEnvironment"
        )
    if not isinstance(provenance, V04C3OpeningProvenance):
        raise V04C3OpeningSourceContractError(
            "provenance must be V04C3OpeningProvenance"
        )
    provenance.verify()
    if not isinstance(common_random_field, KeyedFadingField):
        raise V04C3OpeningSourceContractError(
            "common_random_field must be KeyedFadingField"
        )
    if not isinstance(rng, np.random.Generator):
        raise V04C3OpeningSourceContractError(
            "rng must be numpy.random.Generator"
        )
    if common_random_field.root_digest != provenance.common_random_field_sha256:
        raise V04C3OpeningSourceContractError(
            "provenance common-random digest disagrees with supplied field"
        )
    bound_field = getattr(environment, "_fading_field", None)
    if (
        not isinstance(bound_field, KeyedFadingField)
        or bound_field != common_random_field
        or not bool(environment.physics.fading_enabled)
    ):
        raise V04C3OpeningSourceContractError(
            "environment must use the supplied keyed fading field"
        )

    interval = _positive(interval_s, field="interval_s")
    kappa = _positive(kappa_bits, field="kappa_bits")
    tables = _assert_anchor(environment, observation)
    _state_digest_matches(
        environment,
        observation,
        state_observation,
        interval_s=interval,
        kappa_bits=kappa,
    )
    num_users = observation.num_users
    if type(focal_user) is not int or not 0 <= focal_user < num_users:
        raise V04C3OpeningSourceContractError(
            "focal_user is outside the sealed anchor"
        )
    reference = _action_vector(
        reference_actions,
        field="reference_actions",
        num_users=num_users,
    )
    candidate = _action_vector(
        candidate_actions,
        field="candidate_actions",
        num_users=num_users,
    )
    try:
        reference = assert_selected_actions_valid(reference, tables)
        candidate = assert_selected_actions_valid(candidate, tables)
    except (MCRLContractError, ValueError) as error:
        raise V04C3OpeningSourceContractError(
            f"C3 opening actions are not legal at the sealed anchor: {error}"
        ) from error
    reference_physical_key, candidate_physical_key = _assert_single_focal_difference(
        reference,
        candidate,
        focal_user=focal_user,
        slot_tables=tables,
    )

    before = _evaluation_snapshot(environment, rng)
    try:
        reference_evaluation = environment.evaluate_actions(reference, rng)
        candidate_evaluation = environment.evaluate_actions(candidate, rng)
    except (MCRLContractError, ValueError, TypeError) as error:
        raise V04C3OpeningSourceContractError(
            f"matched V0.4 C3 opening evaluation failed: {error}"
        ) from error
    _assert_evaluation_neutral(environment, rng, before)

    try:
        pair = build_opening_pair(
            source_route="C3",
            source_rule=provenance.c3_source_rule,
            source_policy_version=provenance.source_policy_version,
            anchor_sha256=provenance.anchor_sha256,
            source_manifest_sha256=provenance.source_manifest_sha256,
            checkpoint_sha256=provenance.checkpoint_sha256,
            common_random_field_sha256=provenance.common_random_field_sha256,
            focal_user=focal_user,
            state=state_observation.state_matrix[focal_user],
            action_mask=state_observation.action_masks[focal_user],
            reference_action=int(reference[focal_user]),
            candidate_action=int(candidate[focal_user]),
            reference_joint_actions=reference,
            candidate_joint_actions=candidate,
            reference_rates_bps=reference_evaluation.link_rate_bps,
            candidate_rates_bps=candidate_evaluation.link_rate_bps,
            reference_system_power_w=float(reference_evaluation.system_power_w),
            candidate_system_power_w=float(candidate_evaluation.system_power_w),
            lambda_bits_per_j=float(lambda_bits_per_j),
            interval_s=interval,
        )
    except OpeningPairContractError as error:
        raise V04C3OpeningSourceContractError(
            f"V0.4 C3 opening pair construction failed: {error}"
        ) from error
    result_without_digest = V04C3OpeningComparison(
        state_schema=state_observation.schema,
        state_schema_sha256=state_observation.schema_sha256,
        state_observation_sha256=state_observation.state_sha256,
        kappa_bits=kappa,
        provenance=provenance,
        pair=pair,
        reference_physical_key=reference_physical_key,
        candidate_physical_key=candidate_physical_key,
        reference_evaluation=reference_evaluation,
        candidate_evaluation=candidate_evaluation,
        comparison_sha256="0" * 64,
    )
    digest = _canonical_sha256(_result_payload(result_without_digest))
    result = V04C3OpeningComparison(
        **{**result_without_digest.__dict__, "comparison_sha256": digest}
    )
    result.verify()
    return result


__all__ = [
    "V04_C3_OPENING_SOURCE_SCHEMA",
    "V04C3OpeningComparison",
    "V04C3OpeningProvenance",
    "V04C3OpeningSourceContractError",
    "produce_v04_c3_opening_comparison",
]
