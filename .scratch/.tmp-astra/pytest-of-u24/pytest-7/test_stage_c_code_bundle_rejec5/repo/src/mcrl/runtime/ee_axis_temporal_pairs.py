"""Fail-closed C2/Q2 temporal pairs for Multi-Catfish MCRL V0.3.

The C2 replay runner owns physical execution.  This module is the narrow
boundary after that execution: it validates one complete matched temporal
trace, binds its opening state/action slots and provenance, and exposes the
native-bit :class:`~mcrl.algorithms.ee_axis_pairwise.EEAxisPairBatch` surface
for Q2 only.

This is intentionally not an adapter for the sealed gate JSON.  A row must
carry the current 228-dimensional state, both raw branches, the downstream
fixed-lambda per-offset surplus, and all lineage digests.  Consequently an
old receipt cannot be relabelled as training data by supplying only its
``z2`` value.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

import numpy as np

from ..algorithms.ee_axis_pairwise import EEAxisPairBatch
from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_state import (
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)


TEMPORAL_PAIR_SCHEMA = "multi-catfish-mcrl-v03-temporal-pair-v1"
TEMPORAL_BATCH_SCHEMA = "multi-catfish-mcrl-v03-temporal-route-batch-v1"
TEMPORAL_ROUTE = "C2"
TEMPORAL_HORIZON_STEPS = 4
TEMPORAL_DOWNSTREAM_OFFSETS = tuple(range(1, TEMPORAL_HORIZON_STEPS))
TEMPORAL_RELEASE_REASONS = ("horizon", "support_expired")
TEMPORAL_SOURCE_RULES = (
    "incumbent-hold",
    "max-lagged-candidate-sinr-rival",
    "c2-equal-budget-uniform-predecision-v1",
    "c2-support-complete-legal-nonmain-v1",
)
C2_NEUTRAL_SOURCE_RULE = "c2-equal-budget-uniform-predecision-v1"
"""Equal-budget neutral C2 source provenance admitted for ablations."""
C2_POLICY_VERSION = "C2_V0.3B_HOLD_WHILE_LEGAL_MONOTONE_RELEASE"


class TemporalPairContractError(MCRLContractError):
    """A proposed C2 temporal comparison is not admissible V0.3 data."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TemporalPairContractError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise TemporalPairContractError(f"{field} must be a nonempty trimmed string")
    return value


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise TemporalPairContractError(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _finite(value: object, *, field: str, positive: bool = False) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.number)
    ):
        raise TemporalPairContractError(f"{field} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted) or (positive and converted <= 0.0):
        qualifier = "positive finite" if positive else "finite"
        raise TemporalPairContractError(f"{field} must be {qualifier}")
    return converted


def _immutable_array(
    value: object,
    *,
    field: str,
    dtype: np.dtype[Any],
    ndim: int,
) -> np.ndarray:
    raw = np.asarray(value)
    if raw.ndim != ndim:
        raise TemporalPairContractError(
            f"{field} must be {ndim}-dimensional, got {raw.shape}"
        )
    try:
        copied = np.array(raw, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError) as error:
        raise TemporalPairContractError(f"{field} has an invalid dtype") from error
    if np.issubdtype(copied.dtype, np.floating) and not np.all(
        np.isfinite(copied)
    ):
        raise TemporalPairContractError(f"{field} must be finite")
    copied.setflags(write=False)
    return copied


def _immutable_boolean_array(
    value: object,
    *,
    field: str,
    ndim: int,
) -> np.ndarray:
    """Copy a Boolean payload without silently coercing integers to bool."""

    raw = np.asarray(value)
    if raw.dtype != np.bool_:
        raise TemporalPairContractError(f"{field} must have Boolean dtype")
    return _immutable_array(
        raw,
        field=field,
        dtype=np.dtype(np.bool_),
        ndim=ndim,
    )


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _float_hex(value: object) -> str:
    return float(value).hex()


def _float_hex_list(values: np.ndarray) -> list[str]:
    return [_float_hex(value) for value in np.asarray(values).ravel()]


def _physical_key(value: object, *, field: str) -> tuple[int, int]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise TemporalPairContractError(f"{field} must be a two-integer physical key")
    return (
        _exact_int(value[0], field=f"{field}.norad"),
        _exact_int(value[1], field=f"{field}.cell"),
    )


def _trace_digest_payload(pair: "EEAxisTemporalPair") -> dict[str, object]:
    """Return the complete payload used by the row content digest."""

    return {
        "schema": TEMPORAL_PAIR_SCHEMA,
        "source_route": TEMPORAL_ROUTE,
        "c2_policy_version": pair.c2_policy_version,
        "source_rule": pair.source_rule,
        "anchor_sha256": pair.anchor_sha256,
        "anchor_schedule_sha256": pair.anchor_schedule_sha256,
        "seed": pair.seed,
        "step_index": pair.step_index,
        "source_manifest_sha256": pair.source_manifest_sha256,
        "checkpoint_sha256": pair.checkpoint_sha256,
        "common_random_field_sha256": pair.common_random_field_sha256,
        "forecast_payload_sha256": pair.forecast_payload_sha256,
        "reference_trace_sha256": pair.reference_trace_sha256,
        "candidate_trace_sha256": pair.candidate_trace_sha256,
        "state_schema": pair.state_schema,
        "state_schema_sha256": pair.state_schema_sha256,
        "state_observation_sha256": pair.state_observation_sha256,
        "state": _float_hex_list(pair.state),
        "action_mask": [bool(value) for value in pair.action_mask.tolist()],
        "reference_action": pair.reference_action,
        "candidate_action": pair.candidate_action,
        "held_physical_key": [
            int(pair.held_physical_key[0]),
            int(pair.held_physical_key[1]),
        ],
        "held_key_match_counts": [int(value) for value in pair.held_key_match_counts],
        "release_offset": pair.release_offset,
        "release_reason": pair.release_reason,
        "lambda_bits_per_j": _float_hex(pair.lambda_bits_per_j),
        "interval_s": _float_hex(pair.interval_s),
        "reference_rates_bps": _float_hex_list(pair.reference_rates_bps),
        "candidate_rates_bps": _float_hex_list(pair.candidate_rates_bps),
        "reference_system_power_w": _float_hex_list(pair.reference_system_power_w),
        "candidate_system_power_w": _float_hex_list(pair.candidate_system_power_w),
        "reference_served": [bool(value) for value in pair.reference_served.ravel()],
        "candidate_served": [bool(value) for value in pair.candidate_served.ravel()],
        "offset_surplus_bits": _float_hex_list(pair.offset_surplus_bits),
        "zeta2_temporal_surplus_bits": _float_hex(pair.zeta2_temporal_surplus_bits),
        "provenance_sha256": pair.provenance_sha256,
    }


def _provenance_payload(pair: "EEAxisTemporalPair") -> dict[str, object]:
    """Return the lineage-only payload bound by ``provenance_sha256``."""

    return {
        "schema": TEMPORAL_PAIR_SCHEMA,
        "source_route": TEMPORAL_ROUTE,
        "c2_policy_version": pair.c2_policy_version,
        "source_rule": pair.source_rule,
        "anchor_sha256": pair.anchor_sha256,
        "anchor_schedule_sha256": pair.anchor_schedule_sha256,
        "seed": pair.seed,
        "step_index": pair.step_index,
        "source_manifest_sha256": pair.source_manifest_sha256,
        "checkpoint_sha256": pair.checkpoint_sha256,
        "common_random_field_sha256": pair.common_random_field_sha256,
        "forecast_payload_sha256": pair.forecast_payload_sha256,
        "reference_trace_sha256": pair.reference_trace_sha256,
        "candidate_trace_sha256": pair.candidate_trace_sha256,
        "state_schema": pair.state_schema,
        "state_schema_sha256": pair.state_schema_sha256,
        "state_observation_sha256": pair.state_observation_sha256,
        "focal_user": pair.focal_user,
        "reference_action": pair.reference_action,
        "candidate_action": pair.candidate_action,
        "held_physical_key": [
            int(pair.held_physical_key[0]),
            int(pair.held_physical_key[1]),
        ],
        "held_key_match_counts": [int(value) for value in pair.held_key_match_counts],
        "release_offset": pair.release_offset,
        "release_reason": pair.release_reason,
        "lambda_bits_per_j": _float_hex(pair.lambda_bits_per_j),
        "interval_s": _float_hex(pair.interval_s),
    }


def _pair_batch_payload(batch: EEAxisPairBatch) -> dict[str, object]:
    states = np.asarray(batch.states)
    references = np.asarray(batch.reference_actions)
    candidates = np.asarray(batch.candidate_actions)
    targets = np.asarray(batch.target_surplus_bits)
    masks = np.asarray(batch.action_masks)
    return {
        "states": [_float_hex_list(row) for row in states],
        "reference_actions": [int(value) for value in references.tolist()],
        "candidate_actions": [int(value) for value in candidates.tolist()],
        "target_surplus_bits": [_float_hex(value) for value in targets.tolist()],
        "action_masks": [[bool(value) for value in row] for row in masks.tolist()],
    }


def _array_close(left: np.ndarray, right: np.ndarray, *, field: str) -> None:
    if not np.allclose(left, right, rtol=0.0, atol=1e-9):
        raise TemporalPairContractError(f"{field} disagrees with its derived value")


def _validate_temporal_payload(pair: "EEAxisTemporalPair") -> None:
    """Validate all fields except the row content digest itself."""

    if pair.c2_policy_version != C2_POLICY_VERSION:
        raise TemporalPairContractError("C2 policy version is stale or unsupported")
    _text(pair.source_rule, field="source_rule")
    if pair.source_rule not in TEMPORAL_SOURCE_RULES:
        raise TemporalPairContractError("source_rule is stale or unsupported")
    for field in (
        "anchor_sha256",
        "anchor_schedule_sha256",
        "source_manifest_sha256",
        "checkpoint_sha256",
        "common_random_field_sha256",
        "forecast_payload_sha256",
        "reference_trace_sha256",
        "candidate_trace_sha256",
        "state_observation_sha256",
        "provenance_sha256",
    ):
        _digest(getattr(pair, field), field=field)
    _exact_int(pair.seed, field="seed")
    _exact_int(pair.step_index, field="step_index")

    if pair.state_schema != EE_AXIS_STATE_SCHEMA:
        raise TemporalPairContractError("state schema is stale or unsupported")
    if pair.state_schema_sha256 != EE_AXIS_STATE_SCHEMA_SHA256:
        raise TemporalPairContractError("state schema digest drifted")
    state = np.asarray(pair.state)
    if state.dtype != np.dtype(np.float32) or state.shape != (EE_AXIS_STATE_DIM,):
        raise TemporalPairContractError(
            f"state must be immutable float32 shape ({EE_AXIS_STATE_DIM},)"
        )
    if state.flags.writeable:
        raise TemporalPairContractError("state must be immutable")
    if not np.all(np.isfinite(state)):
        raise TemporalPairContractError("state must be finite")

    mask = np.asarray(pair.action_mask)
    if mask.dtype != np.bool_ or mask.shape != (NUM_ACTIONS,):
        raise TemporalPairContractError(
            f"action_mask must be immutable Boolean shape ({NUM_ACTIONS},)"
        )
    if mask.flags.writeable:
        raise TemporalPairContractError("action_mask must be immutable")
    for name in ("reference_action", "candidate_action"):
        action = getattr(pair, name)
        if type(action) is not int or not 0 <= action < NUM_ACTIONS:
            raise TemporalPairContractError(f"{name} is outside the action space")
        if not bool(mask[action]):
            raise TemporalPairContractError(f"{name} is illegal under action_mask")
    if pair.reference_action == pair.candidate_action:
        raise TemporalPairContractError("reference and candidate actions must differ")

    _exact_int(pair.focal_user, field="focal_user")
    _physical_key(pair.held_physical_key, field="held_physical_key")
    counts = tuple(pair.held_key_match_counts)
    if len(counts) != TEMPORAL_HORIZON_STEPS or any(
        type(value) is not int or value < 0 for value in counts
    ):
        raise TemporalPairContractError(
            "held_key_match_counts must contain four nonnegative exact integers"
        )
    release_offset = _exact_int(pair.release_offset, field="release_offset", minimum=1)
    if release_offset >= TEMPORAL_HORIZON_STEPS:
        raise TemporalPairContractError("release_offset must be within offsets 1..3")
    if pair.release_reason not in TEMPORAL_RELEASE_REASONS:
        raise TemporalPairContractError(
            "release_reason must be 'horizon' or 'support_expired'"
        )
    if counts[0] != 1:
        raise TemporalPairContractError("opening held key must have unique support")
    if any(value != 1 for value in counts[:release_offset]):
        raise TemporalPairContractError("hold support is not unique before release")
    if pair.release_reason == "horizon":
        if release_offset != TEMPORAL_HORIZON_STEPS - 1:
            raise TemporalPairContractError(
                "horizon release must occur at the final downstream offset"
            )
        if any(value != 1 for value in counts):
            raise TemporalPairContractError(
                "horizon release must retain unique support through the horizon"
            )
    else:
        if counts[release_offset] == 1:
            raise TemporalPairContractError(
                "support-expired release must occur at the first support loss"
            )
        # Support counts after release are observational only.  The policy
        # latch concerns executed actions, which are kept in the runner's
        # trace receipt; a physical key may remain absent or become visible
        # again without being reacquired by the candidate policy.

    reference_rates = np.asarray(pair.reference_rates_bps)
    candidate_rates = np.asarray(pair.candidate_rates_bps)
    if (
        reference_rates.dtype != np.dtype(np.float64)
        or candidate_rates.dtype != np.dtype(np.float64)
        or reference_rates.ndim != 2
        or candidate_rates.shape != reference_rates.shape
        or reference_rates.shape[0] != TEMPORAL_HORIZON_STEPS
        or reference_rates.shape[1] < 1
    ):
        raise TemporalPairContractError(
            "reference/candidate rates must be immutable float64 shape (4,U), U>=1"
        )
    if pair.focal_user >= reference_rates.shape[1]:
        raise TemporalPairContractError("focal_user is outside the trace user axis")
    if reference_rates.flags.writeable or candidate_rates.flags.writeable:
        raise TemporalPairContractError("trace rates must be immutable")
    if not np.all(np.isfinite(reference_rates)) or not np.all(
        np.isfinite(candidate_rates)
    ) or np.any(reference_rates < 0.0) or np.any(candidate_rates < 0.0):
        raise TemporalPairContractError("trace rates must be finite and nonnegative")

    reference_power = np.asarray(pair.reference_system_power_w)
    candidate_power = np.asarray(pair.candidate_system_power_w)
    if (
        reference_power.dtype != np.dtype(np.float64)
        or candidate_power.dtype != np.dtype(np.float64)
        or reference_power.shape != (TEMPORAL_HORIZON_STEPS,)
        or candidate_power.shape != reference_power.shape
        or reference_power.flags.writeable
        or candidate_power.flags.writeable
    ):
        raise TemporalPairContractError(
            "trace powers must be immutable float64 vectors of length 4"
        )
    if not np.all(np.isfinite(reference_power)) or not np.all(
        np.isfinite(candidate_power)
    ) or np.any(reference_power <= 0.0) or np.any(candidate_power <= 0.0):
        raise TemporalPairContractError("trace powers must be finite and strictly positive")

    reference_served = np.asarray(pair.reference_served)
    candidate_served = np.asarray(pair.candidate_served)
    if (
        reference_served.dtype != np.bool_
        or candidate_served.dtype != np.bool_
        or reference_served.shape != reference_rates.shape
        or candidate_served.shape != reference_rates.shape
        or reference_served.flags.writeable
        or candidate_served.flags.writeable
    ):
        raise TemporalPairContractError("served traces must be immutable Boolean shape (4,U)")

    multiplier = _finite(pair.lambda_bits_per_j, field="lambda_bits_per_j", positive=True)
    interval = _finite(pair.interval_s, field="interval_s", positive=True)
    surplus = np.asarray(pair.offset_surplus_bits)
    if (
        surplus.dtype != np.dtype(np.float64)
        or surplus.shape != (TEMPORAL_HORIZON_STEPS - 1,)
        or surplus.flags.writeable
        or not np.all(np.isfinite(surplus))
    ):
        raise TemporalPairContractError(
            "offset_surplus_bits must be immutable finite float64 length 3"
        )

    delta_rates = candidate_rates - reference_rates
    expected_surplus = np.asarray(
        [
            interval * math.fsum(float(value) for value in delta_rates[offset])
            - multiplier
            * interval
            * float(candidate_power[offset] - reference_power[offset])
            for offset in TEMPORAL_DOWNSTREAM_OFFSETS
        ],
        dtype=np.float64,
    )
    _array_close(surplus, expected_surplus, field="offset surplus")
    target = _finite(
        pair.zeta2_temporal_surplus_bits,
        field="zeta2_temporal_surplus_bits",
    )
    expected_target = math.fsum(float(value) for value in expected_surplus)
    tolerance = max(
        1e-9,
        512.0
        * np.finfo(np.float64).eps
        * max(1.0, abs(expected_target), float(np.abs(expected_surplus).sum())),
    )
    if not math.isclose(target, expected_target, rel_tol=0.0, abs_tol=tolerance):
        raise TemporalPairContractError(
            "zeta2 temporal surplus disagrees with downstream trace"
        )

    expected_provenance = _canonical_sha256(_provenance_payload(pair))
    if pair.provenance_sha256 != expected_provenance:
        raise TemporalPairContractError(
            "provenance digest disagrees with trace lineage"
        )


@dataclass(frozen=True)
class EEAxisTemporalPair:
    """One complete immutable C2 matched temporal comparison.

    ``state`` is the focal user's current predecision 228-D state.  The two
    action fields are opening-table slots, not physical IDs; the held physical
    key is retained separately for release-policy auditability.  ``zeta2`` and
    ``offset_surplus_bits`` are native bits after the fixed global multiplier,
    and are never normalized here.
    """

    c2_policy_version: str
    source_rule: str
    anchor_sha256: str
    anchor_schedule_sha256: str
    seed: int
    step_index: int
    source_manifest_sha256: str
    checkpoint_sha256: str
    common_random_field_sha256: str
    forecast_payload_sha256: str
    reference_trace_sha256: str
    candidate_trace_sha256: str
    state_schema: str
    state_schema_sha256: str
    state_observation_sha256: str
    focal_user: int
    state: np.ndarray
    action_mask: np.ndarray
    reference_action: int
    candidate_action: int
    held_physical_key: tuple[int, int]
    held_key_match_counts: tuple[int, ...]
    release_offset: int
    release_reason: str
    reference_rates_bps: np.ndarray
    candidate_rates_bps: np.ndarray
    reference_system_power_w: np.ndarray
    candidate_system_power_w: np.ndarray
    reference_served: np.ndarray
    candidate_served: np.ndarray
    lambda_bits_per_j: float
    interval_s: float
    offset_surplus_bits: np.ndarray
    zeta2_temporal_surplus_bits: float
    provenance_sha256: str
    comparison_sha256: str

    @property
    def source_route(self) -> str:
        """The only route admitted by this adapter: Q2/C2."""

        return TEMPORAL_ROUTE

    @property
    def z2_temporal_surplus_bits(self) -> float:
        """Implementation-field spelling used by existing C2 receipts."""

        return self.zeta2_temporal_surplus_bits

    def verify(self) -> str:
        """Revalidate arrays, formula, lineage, and the immutable row digest."""

        _validate_temporal_payload(self)
        supplied = _digest(self.comparison_sha256, field="comparison_sha256")
        actual = _canonical_sha256(_trace_digest_payload(self))
        if supplied != actual:
            raise TemporalPairContractError(
                "temporal comparison digest disagrees with its payload"
            )
        return actual

    def as_pair_batch(self) -> EEAxisPairBatch:
        """Project this verified temporal row onto the Q2 learner surface."""

        self.verify()
        states = np.asarray(self.state[None, :], dtype=np.float32).copy()
        references = np.asarray([self.reference_action], dtype=np.int64)
        candidates = np.asarray([self.candidate_action], dtype=np.int64)
        targets = np.asarray([self.zeta2_temporal_surplus_bits], dtype=np.float64)
        masks = np.asarray(self.action_mask[None, :], dtype=np.bool_).copy()
        for array in (states, references, candidates, targets, masks):
            array.setflags(write=False)
        batch = EEAxisPairBatch(
            states=states,
            reference_actions=references,
            candidate_actions=candidates,
            target_surplus_bits=targets,
            action_masks=masks,
        )
        batch.validate(state_dim=EE_AXIS_STATE_DIM, action_dim=NUM_ACTIONS)
        return batch


def build_temporal_pair(
    *,
    c2_policy_version: str,
    source_rule: str,
    anchor_sha256: str,
    anchor_schedule_sha256: str,
    seed: int,
    step_index: int,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    common_random_field_sha256: str,
    forecast_payload_sha256: str,
    reference_trace_sha256: str,
    candidate_trace_sha256: str,
    state_schema: str,
    state_schema_sha256: str,
    state_observation_sha256: str,
    focal_user: int,
    state: object,
    action_mask: object,
    reference_action: int,
    candidate_action: int,
    held_physical_key: object,
    held_key_match_counts: Iterable[int],
    release_offset: int,
    release_reason: str,
    reference_rates_bps: object,
    candidate_rates_bps: object,
    reference_system_power_w: object,
    candidate_system_power_w: object,
    reference_served: object,
    candidate_served: object,
    lambda_bits_per_j: float,
    interval_s: float,
    offset_surplus_bits: object,
    zeta2_temporal_surplus_bits: float,
) -> EEAxisTemporalPair:
    """Validate and materialize one current-policy C2/Q2 pair.

    The caller supplies the sealed replay result.  This function does not
    execute a simulator branch, inspect outcomes to choose a candidate, or
    read a gate JSON document.
    """

    counts = tuple(held_key_match_counts)
    pair = EEAxisTemporalPair(
        c2_policy_version=c2_policy_version,
        source_rule=source_rule,
        anchor_sha256=anchor_sha256,
        anchor_schedule_sha256=anchor_schedule_sha256,
        seed=seed,
        step_index=step_index,
        source_manifest_sha256=source_manifest_sha256,
        checkpoint_sha256=checkpoint_sha256,
        common_random_field_sha256=common_random_field_sha256,
        forecast_payload_sha256=forecast_payload_sha256,
        reference_trace_sha256=reference_trace_sha256,
        candidate_trace_sha256=candidate_trace_sha256,
        state_schema=state_schema,
        state_schema_sha256=state_schema_sha256,
        state_observation_sha256=state_observation_sha256,
        focal_user=focal_user,
        state=_immutable_array(
            state,
            field="state",
            dtype=np.dtype(np.float32),
            ndim=1,
        ),
        action_mask=_immutable_boolean_array(
            action_mask,
            field="action_mask",
            ndim=1,
        ),
        reference_action=reference_action,
        candidate_action=candidate_action,
        held_physical_key=_physical_key(held_physical_key, field="held_physical_key"),
        held_key_match_counts=counts,
        release_offset=release_offset,
        release_reason=release_reason,
        reference_rates_bps=_immutable_array(
            reference_rates_bps,
            field="reference_rates_bps",
            dtype=np.dtype(np.float64),
            ndim=2,
        ),
        candidate_rates_bps=_immutable_array(
            candidate_rates_bps,
            field="candidate_rates_bps",
            dtype=np.dtype(np.float64),
            ndim=2,
        ),
        reference_system_power_w=_immutable_array(
            reference_system_power_w,
            field="reference_system_power_w",
            dtype=np.dtype(np.float64),
            ndim=1,
        ),
        candidate_system_power_w=_immutable_array(
            candidate_system_power_w,
            field="candidate_system_power_w",
            dtype=np.dtype(np.float64),
            ndim=1,
        ),
        reference_served=_immutable_boolean_array(
            reference_served,
            field="reference_served",
            ndim=2,
        ),
        candidate_served=_immutable_boolean_array(
            candidate_served,
            field="candidate_served",
            ndim=2,
        ),
        lambda_bits_per_j=float(lambda_bits_per_j),
        interval_s=float(interval_s),
        offset_surplus_bits=_immutable_array(
            offset_surplus_bits,
            field="offset_surplus_bits",
            dtype=np.dtype(np.float64),
            ndim=1,
        ),
        zeta2_temporal_surplus_bits=float(zeta2_temporal_surplus_bits),
        provenance_sha256="0" * 64,
        comparison_sha256="0" * 64,
    )
    _validate_temporal_payload(
        EEAxisTemporalPair(
            **{
                **pair.__dict__,
                "provenance_sha256": _canonical_sha256(_provenance_payload(pair)),
            }
        )
    )
    with_provenance = EEAxisTemporalPair(
        **{
            **pair.__dict__,
            "provenance_sha256": _canonical_sha256(_provenance_payload(pair)),
        }
    )
    digest = _canonical_sha256(_trace_digest_payload(with_provenance))
    result = EEAxisTemporalPair(
        **{
            **with_provenance.__dict__,
            "comparison_sha256": digest,
        }
    )
    result.verify()
    return result


@dataclass(frozen=True)
class EEAxisTemporalRouteBatch:
    """A same-route immutable batch accepted only by Q2."""

    route: str
    rows: tuple[EEAxisTemporalPair, ...]
    pair_batch: EEAxisPairBatch
    temporal_pair_sha256s: tuple[str, ...]
    batch_sha256: str

    def verify(self) -> str:
        if self.route != TEMPORAL_ROUTE:
            raise TemporalPairContractError("temporal batch route must be C2")
        if not self.rows:
            raise TemporalPairContractError("temporal batch must contain rows")
        if len(self.rows) != len(self.temporal_pair_sha256s):
            raise TemporalPairContractError(
                "temporal batch row count disagrees with row receipts"
            )
        if len(set(self.temporal_pair_sha256s)) != len(self.temporal_pair_sha256s):
            raise TemporalPairContractError("temporal batch contains duplicate rows")
        for index, row in enumerate(self.rows):
            if not isinstance(row, EEAxisTemporalPair):
                raise TemporalPairContractError("temporal batch contains a non-pair row")
            if row.verify() != self.temporal_pair_sha256s[index]:
                raise TemporalPairContractError(
                    f"temporal row receipt disagrees at index {index}"
                )
        self.pair_batch.validate(state_dim=EE_AXIS_STATE_DIM, action_dim=NUM_ACTIONS)
        for field in (
            "states",
            "reference_actions",
            "candidate_actions",
            "target_surplus_bits",
            "action_masks",
        ):
            if np.asarray(getattr(self.pair_batch, field)).flags.writeable:
                raise TemporalPairContractError(
                    f"temporal pair batch {field} must be immutable"
                )
        expected = EEAxisPairBatch(
            states=np.asarray(
                [row.state for row in self.rows], dtype=np.float32
            ).copy(),
            reference_actions=np.asarray(
                [row.reference_action for row in self.rows], dtype=np.int64
            ),
            candidate_actions=np.asarray(
                [row.candidate_action for row in self.rows], dtype=np.int64
            ),
            target_surplus_bits=np.asarray(
                [row.zeta2_temporal_surplus_bits for row in self.rows],
                dtype=np.float64,
            ),
            action_masks=np.asarray(
                [row.action_mask for row in self.rows], dtype=np.bool_
            ).copy(),
        )
        for array in (
            expected.states,
            expected.reference_actions,
            expected.candidate_actions,
            expected.target_surplus_bits,
            expected.action_masks,
        ):
            array.setflags(write=False)
        expected.validate(state_dim=EE_AXIS_STATE_DIM, action_dim=NUM_ACTIONS)
        actual_values = (
            np.asarray(self.pair_batch.states),
            np.asarray(self.pair_batch.reference_actions),
            np.asarray(self.pair_batch.candidate_actions),
            np.asarray(self.pair_batch.target_surplus_bits),
            np.asarray(self.pair_batch.action_masks),
        )
        expected_values = (
            np.asarray(expected.states),
            np.asarray(expected.reference_actions),
            np.asarray(expected.candidate_actions),
            np.asarray(expected.target_surplus_bits),
            np.asarray(expected.action_masks),
        )
        if any(
            not np.array_equal(left, right)
            for left, right in zip(actual_values, expected_values, strict=True)
        ):
            raise TemporalPairContractError(
                "temporal pair batch arrays disagree with its rows"
            )
        payload = {
            "schema": TEMPORAL_BATCH_SCHEMA,
            "route": self.route,
            "temporal_pair_sha256s": list(self.temporal_pair_sha256s),
            "pair_batch": _pair_batch_payload(self.pair_batch),
        }
        actual = _canonical_sha256(payload)
        if _digest(self.batch_sha256, field="batch_sha256") != actual:
            raise TemporalPairContractError("temporal batch digest disagrees with payload")
        return actual


def build_temporal_route_batch(
    rows: Iterable[EEAxisTemporalPair],
) -> EEAxisTemporalRouteBatch:
    """Stack verified C2 rows into the exact Q2 pairwise learner surface."""

    materialized = tuple(rows)
    if not materialized:
        raise TemporalPairContractError("temporal route batch cannot be empty")
    if any(not isinstance(row, EEAxisTemporalPair) for row in materialized):
        raise TemporalPairContractError("temporal batch contains a non-pair row")
    digests = tuple(row.verify() for row in materialized)
    if len(set(digests)) != len(digests):
        raise TemporalPairContractError("temporal batch contains duplicate rows")
    pair_batches = tuple(row.as_pair_batch() for row in materialized)
    states = np.concatenate([batch.states for batch in pair_batches], axis=0)
    references = np.concatenate(
        [batch.reference_actions for batch in pair_batches], axis=0
    )
    candidates = np.concatenate(
        [batch.candidate_actions for batch in pair_batches], axis=0
    )
    targets = np.concatenate(
        [batch.target_surplus_bits for batch in pair_batches], axis=0
    )
    masks = np.concatenate([batch.action_masks for batch in pair_batches], axis=0)
    for array in (states, references, candidates, targets, masks):
        array.setflags(write=False)
    pair_batch = EEAxisPairBatch(
        states=states,
        reference_actions=references,
        candidate_actions=candidates,
        target_surplus_bits=targets,
        action_masks=masks,
    )
    pair_batch.validate(state_dim=EE_AXIS_STATE_DIM, action_dim=NUM_ACTIONS)
    payload = {
        "schema": TEMPORAL_BATCH_SCHEMA,
        "route": TEMPORAL_ROUTE,
        "temporal_pair_sha256s": list(digests),
        "pair_batch": _pair_batch_payload(pair_batch),
    }
    result = EEAxisTemporalRouteBatch(
        route=TEMPORAL_ROUTE,
        rows=materialized,
        pair_batch=pair_batch,
        temporal_pair_sha256s=digests,
        batch_sha256=_canonical_sha256(payload),
    )
    result.verify()
    return result


__all__ = [
    "C2_NEUTRAL_SOURCE_RULE",
    "C2_POLICY_VERSION",
    "EEAxisTemporalPair",
    "EEAxisTemporalRouteBatch",
    "TEMPORAL_BATCH_SCHEMA",
    "TEMPORAL_DOWNSTREAM_OFFSETS",
    "TEMPORAL_HORIZON_STEPS",
    "TEMPORAL_PAIR_SCHEMA",
    "TEMPORAL_RELEASE_REASONS",
    "TEMPORAL_ROUTE",
    "TemporalPairContractError",
    "build_temporal_pair",
    "build_temporal_route_batch",
]
