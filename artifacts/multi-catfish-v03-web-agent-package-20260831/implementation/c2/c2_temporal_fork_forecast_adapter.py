"""Authoritative payload producer for a C2 V0.3 temporal-fork certificate.

Unlike the legacy frontier bridge, this module derives every certificate
metric from two complete four-step forecast traces.  It also recomputes the
anchor, RNG, request, branch, and complete-payload hashes from the actual
payloads supplied by the runtime.  The live runtime remains responsible for
creating two fresh twins before the realised outcome and for binding either
the legacy diagnostic-disabled mode or the canonical keyed fading receipt.
"""

from __future__ import annotations

import hashlib
import json
import math
import numbers
from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

import numpy as np

import c2_temporal_fork_core as core


NO_OP_ACTION = -1
DECISION_INTERVAL_S = 30.08


@dataclass(frozen=True)
class ForecastSourcePayload:
    """Actual source payloads plus immutable implementation-file digests."""

    anchor_payload: Mapping[str, Any]
    reference_checkpoint_sha256: str
    environment_source_sha256: str
    reward_source_sha256: str
    live_rng_state: Mapping[str, Any]
    forecast_rng_state: Mapping[str, Any]
    forecast_namespace: str
    adapter_version: str
    fading_mode: str = core.FADING_MODE_DISABLED
    fading_field_receipt: Mapping[str, Any] | None = None
    source_rule: str = "unspecified-preoutcome-rule"


@dataclass(frozen=True)
class ForecastStepPayload:
    """One complete pre-state/action/outcome/post-state forecast interval."""

    offset: int
    state_matrix: Any
    mask_matrix: Any
    action_bindings_by_user: Sequence[Sequence[core.ActionBinding]]
    detached_main_actions: Sequence[int]
    detached_main_physical_actions: Sequence[core.PhysicalKey | None]
    executed_actions: Sequence[int]
    executed_physical_actions: Sequence[core.PhysicalKey | None]
    reward_matrix: Sequence[Sequence[float]]
    served: Sequence[bool]
    link_rate_bps: Sequence[float]
    system_power_w: float
    active_physical_ids: Sequence[core.PhysicalKey]
    next_state_matrix: Any
    next_mask_matrix: Any
    done: bool
    # V0.3B source-policy bindings.  They are populated for candidate rows;
    # reference rows may leave them empty because they do not hold a focal
    # alternative.
    held_physical_key: core.PhysicalKey | None = None
    held_key_match_count: int | None = None
    release_offset: int | None = None
    release_reason: str | None = None


@dataclass(frozen=True)
class AuthoritativeForecastBuild:
    authority: core.ForecastAuthority
    evidence: core.TemporalForkEvidence
    certificate: core.TemporalForkCertificate
    reference_trace_sha256: str
    candidate_trace_sha256: str
    forecast_request_sha256: str
    forecast_payload_sha256: str
    claim_ceiling: str = "PREOUTCOME_MECHANISM_CERTIFICATE_NOT_EFFICACY"


@dataclass(frozen=True)
class CommittedOptionClosure:
    receipts: tuple[core.ExecutedOptionStep, ...]
    plan: core.C2ClosedOptionPlan


@dataclass(frozen=True)
class _NormalizedStep:
    offset: int
    states: tuple[tuple[float, ...], ...]
    masks: tuple[tuple[bool, ...], ...]
    bindings: tuple[tuple[core.ActionBinding, ...], ...]
    main_actions: tuple[int, ...]
    main_physical: tuple[core.PhysicalKey | None, ...]
    executed_actions: tuple[int, ...]
    executed_physical: tuple[core.PhysicalKey | None, ...]
    rewards: tuple[core.RewardRow, ...]
    served: tuple[bool, ...]
    rates: tuple[float, ...]
    system_power_w: float
    active: tuple[core.PhysicalKey, ...]
    next_states: tuple[tuple[float, ...], ...]
    next_masks: tuple[tuple[bool, ...], ...]
    done: bool
    held_physical_key: core.PhysicalKey | None
    held_key_match_count: int | None
    release_offset: int | None
    release_reason: str | None
    canonical: Mapping[str, Any]


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, numbers.Integral) and not isinstance(value, bool):
        return {"int": str(int(value))}
    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        converted = float(value)
        if not math.isfinite(converted):
            raise core.C2ContractError("canonical payload contains a nonfinite number")
        return {"float_hex": converted.hex()}
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        if array.dtype.hasobject:
            raise core.C2ContractError("canonical payload cannot contain object arrays")
        if np.issubdtype(array.dtype, np.number) and not np.all(np.isfinite(array)):
            raise core.C2ContractError("canonical payload contains a nonfinite array")
        return {
            "ndarray_dtype": array.dtype.str,
            "ndarray_shape": list(array.shape),
            "ndarray_sha256": hashlib.sha256(array.tobytes(order="C")).hexdigest(),
        }
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise core.C2ContractError("canonical payload mapping keys must be strings")
        return {
            key: _canonicalize(value[key])
            for key in sorted(value)
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise core.C2ContractError(
        f"canonical payload contains unsupported type {type(value).__name__}"
    )


def canonical_payload_sha256(value: Any) -> str:
    encoded = json.dumps(
        _canonicalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise core.C2ContractError(f"{field} must be lowercase SHA-256")
    return value


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise core.C2ContractError(f"{field} must be an exact integer")
    return int(value)


def _number(value: object, *, field: str, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise core.C2ContractError(f"{field} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted) or (nonnegative and converted < 0.0):
        raise core.C2ContractError(f"{field} must be finite and nonnegative")
    return converted


def _physical(value: object, *, field: str) -> core.PhysicalKey:
    if not isinstance(value, tuple) or len(value) != 2:
        raise core.C2ContractError(f"{field} must be a two-integer physical ID")
    first = _integer(value[0], field=f"{field}.norad")
    second = _integer(value[1], field=f"{field}.cell")
    if first < 0 or second < 0:
        raise core.C2ContractError(f"{field} values must be nonnegative")
    return first, second


def _physical_vector(
    values: Sequence[core.PhysicalKey | None], *, users: int, field: str
) -> tuple[core.PhysicalKey | None, ...]:
    if isinstance(values, (str, bytes)) or len(values) != users:
        raise core.C2ContractError(f"{field} has the wrong user count")
    return tuple(
        None if value is None else _physical(value, field=f"{field}[{user}]")
        for user, value in enumerate(values)
    )


def _float_matrix(value: Any, *, users: int, field: str) -> tuple[tuple[float, ...], ...]:
    array = np.asarray(value)
    if array.ndim != 2 or array.shape[0] != users or array.shape[1] == 0:
        raise core.C2ContractError(f"{field} must have shape (U,D) with D>0")
    if not np.issubdtype(array.dtype, np.number):
        raise core.C2ContractError(f"{field} must be numeric")
    converted = np.asarray(array, dtype=np.float64)
    if not np.all(np.isfinite(converted)):
        raise core.C2ContractError(f"{field} must be finite")
    return tuple(tuple(float(item) for item in row) for row in converted)


def _mask_matrix(value: Any, *, users: int, field: str) -> tuple[tuple[bool, ...], ...]:
    array = np.asarray(value)
    if array.dtype != np.bool_ or array.shape != (users, core.ACTION_DIM):
        raise core.C2ContractError(
            f"{field} must be a Boolean (U,{core.ACTION_DIM}) matrix"
        )
    return tuple(tuple(bool(item) for item in row) for row in array)


def _normalize_bindings(
    values: Sequence[Sequence[core.ActionBinding]],
    *,
    masks: tuple[tuple[bool, ...], ...],
    users: int,
) -> tuple[tuple[core.ActionBinding, ...], ...]:
    if len(values) != users:
        raise core.C2ContractError("action bindings have the wrong user count")
    output: list[tuple[core.ActionBinding, ...]] = []
    for user, raw_rows in enumerate(values):
        rows: list[core.ActionBinding] = []
        for index, raw in enumerate(raw_rows):
            if not isinstance(raw, core.ActionBinding):
                raise core.C2ContractError(
                    f"action_bindings[{user}][{index}] must be ActionBinding"
                )
            action = _integer(raw.action, field="binding.action")
            if not 0 <= action < core.ACTION_DIM:
                raise core.C2ContractError("binding action is outside the frozen space")
            rows.append(
                core.ActionBinding(
                    action, _physical(raw.physical_key, field="binding.physical_key")
                )
            )
        normalized = tuple(sorted(rows, key=lambda item: item.action))
        actions = tuple(row.action for row in normalized)
        physical = tuple(row.physical_key for row in normalized)
        if len(actions) != len(set(actions)) or len(physical) != len(set(physical)):
            raise core.C2ContractError("one slot table repeats an action or physical ID")
        mask_actions = tuple(index for index, valid in enumerate(masks[user]) if valid)
        if actions != mask_actions:
            raise core.C2ContractError("action bindings do not exactly match the mask")
        output.append(normalized)
    return tuple(output)


def _actions(values: Sequence[int], *, users: int, field: str) -> tuple[int, ...]:
    if isinstance(values, (str, bytes)) or len(values) != users:
        raise core.C2ContractError(f"{field} has the wrong user count")
    output = tuple(_integer(value, field=f"{field}[{user}]") for user, value in enumerate(values))
    if any(value < NO_OP_ACTION or value >= core.ACTION_DIM for value in output):
        raise core.C2ContractError(f"{field} contains an invalid action")
    return output


def _verify_action_mapping(
    actions: tuple[int, ...],
    physical: tuple[core.PhysicalKey | None, ...],
    bindings: tuple[tuple[core.ActionBinding, ...], ...],
    masks: tuple[tuple[bool, ...], ...],
    *,
    field: str,
) -> None:
    for user, action in enumerate(actions):
        mapping = {row.action: row.physical_key for row in bindings[user]}
        if action == NO_OP_ACTION:
            if physical[user] is not None or any(masks[user]):
                raise core.C2ContractError(
                    f"{field}[{user}] uses NO_OP despite a valid physical action"
                )
        elif not masks[user][action] or mapping.get(action) != physical[user]:
            raise core.C2ContractError(
                f"{field}[{user}] action does not map to its physical ID"
            )


def _normalize_step(raw: ForecastStepPayload, *, users: int) -> _NormalizedStep:
    if not isinstance(raw, ForecastStepPayload):
        raise core.C2ContractError("every forecast step must be ForecastStepPayload")
    offset = _integer(raw.offset, field="step.offset")
    states = _float_matrix(raw.state_matrix, users=users, field="state_matrix")
    masks = _mask_matrix(raw.mask_matrix, users=users, field="mask_matrix")
    next_states = _float_matrix(raw.next_state_matrix, users=users, field="next_state_matrix")
    next_masks = _mask_matrix(raw.next_mask_matrix, users=users, field="next_mask_matrix")
    if len(states[0]) != len(next_states[0]):
        raise core.C2ContractError("state and next-state widths disagree")
    bindings = _normalize_bindings(
        raw.action_bindings_by_user, masks=masks, users=users
    )
    main_actions = _actions(raw.detached_main_actions, users=users, field="detached_main_actions")
    executed_actions = _actions(raw.executed_actions, users=users, field="executed_actions")
    main_physical = _physical_vector(
        raw.detached_main_physical_actions, users=users, field="detached_main_physical_actions"
    )
    executed_physical = _physical_vector(
        raw.executed_physical_actions, users=users, field="executed_physical_actions"
    )
    _verify_action_mapping(main_actions, main_physical, bindings, masks, field="detached_main")
    _verify_action_mapping(executed_actions, executed_physical, bindings, masks, field="executed")

    rewards = tuple(
        tuple(_number(value, field=f"reward_matrix[{user}][{objective}]") for objective, value in enumerate(row))
        for user, row in enumerate(raw.reward_matrix)
    )
    if len(rewards) != users or any(len(row) != 3 for row in rewards):
        raise core.C2ContractError("reward_matrix must have shape (U,3)")
    normalized_rewards = tuple((row[0], row[1], row[2]) for row in rewards)
    core.reward_matrix_sha256(normalized_rewards)
    if len(raw.served) != users or any(type(value) not in (bool, np.bool_) for value in raw.served):
        raise core.C2ContractError("served must be a Boolean vector of length U")
    served = tuple(bool(value) for value in raw.served)
    if len(raw.link_rate_bps) != users:
        raise core.C2ContractError("link_rate_bps has the wrong user count")
    rates = tuple(
        _number(value, field=f"link_rate_bps[{user}]", nonnegative=True)
        for user, value in enumerate(raw.link_rate_bps)
    )
    power = _number(raw.system_power_w, field="system_power_w", nonnegative=True)
    if power <= 0.0:
        raise core.C2ContractError("system_power_w must be strictly positive")
    active = tuple(sorted(_physical(value, field="active_physical_ids") for value in raw.active_physical_ids))
    if len(active) != len(set(active)):
        raise core.C2ContractError("active physical IDs cannot repeat")
    if type(raw.done) not in (bool, np.bool_):
        raise core.C2ContractError("done must be Boolean")
    done = bool(raw.done)
    held_key = None
    if raw.held_physical_key is not None:
        held_key = _physical(raw.held_physical_key, field="held_physical_key")
    match_count = raw.held_key_match_count
    if match_count is not None:
        match_count = _integer(match_count, field="held_key_match_count")
        if match_count < 0:
            raise core.C2ContractError("held_key_match_count must be nonnegative")
        if held_key is None:
            raise core.C2ContractError(
                "held_key_match_count requires held_physical_key"
            )
    release_offset = raw.release_offset
    release_reason = raw.release_reason
    if release_offset is not None or release_reason is not None:
        if release_offset is None or release_reason is None:
            raise core.C2ContractError(
                "release_offset and release_reason must be supplied together"
            )
        release_offset = _integer(release_offset, field="release_offset")
        if not isinstance(release_reason, str):
            raise core.C2ContractError("release_reason must be a string")
        # Validate syntax here; the certificate later binds the exact policy
        # and horizon.  This prevents malformed metadata from entering a
        # canonical trace digest first.
        core._release_policy(  # type: ignore[attr-defined]
            release_offset=release_offset,
            release_reason=release_reason,
            horizon_steps=core.HORIZON_STEPS,
            field_prefix="step",
        )
    canonical = {
        "offset": offset,
        "states": states,
        "masks": masks,
        "bindings": tuple(
            tuple((row.action, row.physical_key) for row in user_rows)
            for user_rows in bindings
        ),
        "detached_main_actions": main_actions,
        "detached_main_physical": main_physical,
        "executed_actions": executed_actions,
        "executed_physical": executed_physical,
        "reward_matrix": normalized_rewards,
        "served": served,
        "link_rate_bps": rates,
        "system_power_w": power,
        "active_physical_ids": active,
        "next_states": next_states,
        "next_masks": next_masks,
        "done": done,
        "held_physical_key": held_key,
        "held_key_match_count": match_count,
        "release_offset": release_offset,
        "release_reason": release_reason,
    }
    return _NormalizedStep(
        offset,
        states,
        masks,
        bindings,
        main_actions,
        main_physical,
        executed_actions,
        executed_physical,
        normalized_rewards,
        served,
        rates,
        power,
        active,
        next_states,
        next_masks,
        done,
        held_key,
        match_count,
        release_offset,
        release_reason,
        canonical,
    )


def _normalize_trace(
    values: Sequence[ForecastStepPayload], *, users: int, field: str
) -> tuple[_NormalizedStep, ...]:
    if isinstance(values, (str, bytes)) or len(values) != core.HORIZON_STEPS + 1:
        raise core.C2ContractError(f"{field} must contain exactly H+1 forecast steps")
    steps = tuple(_normalize_step(value, users=users) for value in values)
    if tuple(step.offset for step in steps) != tuple(range(core.HORIZON_STEPS + 1)):
        raise core.C2ContractError(
            f"{field} offsets must be 0..{core.HORIZON_STEPS}"
        )
    for left, right in zip(steps, steps[1:], strict=False):
        if left.next_states != right.states or left.next_masks != right.masks:
            raise core.C2ContractError(f"{field} state/mask chain is discontinuous")
        if left.done:
            raise core.C2ContractError(f"{field} terminates before first release")
    return steps


def _exact_reference_only_pulse(
    reference: Sequence[frozenset[Any]], candidate: Sequence[frozenset[Any]], item: Any
) -> bool:
    ref = tuple(item in row for row in reference)
    alt = tuple(item in row for row in candidate)
    if ref[0] or ref[-1] or any(alt):
        return False
    active = tuple(index for index, present in enumerate(ref[1:-1], start=1) if present)
    return bool(active) and active == tuple(range(active[0], active[-1] + 1))


def _activation_path(
    pre_active: tuple[core.PhysicalKey, ...],
    reference: tuple[_NormalizedStep, ...],
    candidate: tuple[_NormalizedStep, ...],
) -> bool:
    reference_beams = (frozenset(pre_active),) + tuple(frozenset(step.active) for step in reference)
    candidate_beams = (frozenset(pre_active),) + tuple(frozenset(step.active) for step in candidate)
    all_beams = frozenset().union(*reference_beams, *candidate_beams)
    if any(_exact_reference_only_pulse(reference_beams, candidate_beams, beam) for beam in all_beams):
        return True
    reference_sats = tuple(frozenset(key[0] for key in row) for row in reference_beams)
    candidate_sats = tuple(frozenset(key[0] for key in row) for row in candidate_beams)
    all_sats = frozenset().union(*reference_sats, *candidate_sats)
    return any(_exact_reference_only_pulse(reference_sats, candidate_sats, sat) for sat in all_sats)


def _candidate_release_metadata(
    candidate: tuple[_NormalizedStep, ...],
    *,
    focal_user: int,
    candidate_key: core.PhysicalKey,
) -> tuple[int, str, tuple[int, ...]]:
    """Validate and recover the sealed candidate-side release policy.

    The support count is recomputed from each candidate row's own
    predecision bindings.  No reference row, future row, service outcome, or
    reward is consulted to decide the trigger.
    """

    supplied = tuple((step.release_offset, step.release_reason) for step in candidate)
    explicit_metadata = not all(
        offset is None and reason is None for offset, reason in supplied
    )
    if not explicit_metadata:
        # Compatibility for pre-amendment hand-built fixtures.  New runtime
        # rows always carry explicit metadata; their candidate key/action
        # sequence is checked against the inferred horizon policy below.
        release_offset, release_reason, _ = core._release_policy(  # type: ignore[attr-defined]
            release_offset=core.HORIZON_STEPS,
            release_reason="horizon",
            horizon_steps=core.HORIZON_STEPS,
            field_prefix="candidate",
        )
    elif any(offset is None or reason is None for offset, reason in supplied):
        raise core.C2ContractError(
            "candidate release metadata must be bound on every forecast row"
        )
    else:
        release_offset, release_reason, _ = core._release_policy(  # type: ignore[attr-defined]
            release_offset=supplied[0][0],
            release_reason=supplied[0][1],
            horizon_steps=core.HORIZON_STEPS,
            field_prefix="candidate",
        )
        if any(
            (offset, reason) != (release_offset, release_reason)
            for offset, reason in supplied
        ):
            raise core.C2ContractError(
                "candidate release offset/reason drifted across forecast rows"
            )

    support_counts: list[int] = []
    for offset, step in enumerate(candidate):
        if explicit_metadata and (
            step.held_physical_key is None or step.held_key_match_count is None
        ):
            raise core.C2ContractError(
                "candidate V0.3B rows must bind held_physical_key and support count"
            )
        matches = tuple(
            row.physical_key
            for row in step.bindings[focal_user]
            if row.physical_key == candidate_key
        )
        count = len(matches)
        support_counts.append(count)
        if step.held_physical_key is not None and step.held_physical_key != candidate_key:
            raise core.C2ContractError(
                "candidate held_physical_key differs from opening candidate"
            )
        if step.held_key_match_count is not None and step.held_key_match_count != count:
            raise core.C2ContractError(
                "candidate held_key_match_count disagrees with its action table"
            )

        if explicit_metadata:
            holding = offset < release_offset
            if holding:
                if count != 1:
                    raise core.C2ContractError(
                        "candidate hold row lacks exactly one contemporaneous support match"
                    )
                if step.executed_physical[focal_user] != candidate_key:
                    raise core.C2ContractError(
                        "candidate hold row does not execute the held physical key"
                    )
            elif (
                step.executed_actions != step.main_actions
                or step.executed_physical != step.main_physical
            ):
                raise core.C2ContractError(
                    "candidate release suffix must execute complete branch-local Main"
                )

    # An expiry release must coincide with the first downstream loss of unique
    # support.  A horizon release must see the held key remain unique through
    # every downstream predecision table.
    downstream = tuple(support_counts[1:])
    first_expiry = next(
        (offset for offset, count in enumerate(support_counts) if offset >= 1 and count != 1),
        None,
    )
    if explicit_metadata and release_reason == "support_expired":
        if first_expiry is None or first_expiry != release_offset:
            raise core.C2ContractError(
                "support-expired release is not the first downstream support loss"
            )
    elif explicit_metadata and any(count != 1 for count in downstream):
        raise core.C2ContractError(
            "horizon release requires unique held-key support at every downstream offset"
        )
    return release_offset, release_reason, tuple(support_counts)


def build_authoritative_forecast(
    source: ForecastSourcePayload,
    *,
    focal_user: int,
    user_count: int,
    pre_active_physical_ids: Sequence[core.PhysicalKey],
    reference_trace: Sequence[ForecastStepPayload],
    candidate_trace: Sequence[ForecastStepPayload],
    decision_interval_s: float = DECISION_INTERVAL_S,
) -> AuthoritativeForecastBuild:
    """Derive and bind one binary temporal fork from exact twin traces."""

    if not isinstance(source, ForecastSourcePayload):
        raise core.C2ContractError("source must be ForecastSourcePayload")
    if source.fading_mode not in core.FORECAST_FADING_MODES:
        raise core.C2ContractError("source.fading_mode is not a supported C2 mode")
    if source.fading_mode == core.FADING_MODE_KEYED:
        if not isinstance(source.fading_field_receipt, Mapping):
            raise core.C2ContractError(
                "keyed C2 forecast requires a fading_field_receipt"
            )
        if source.fading_field_receipt.get("mode") != core.FADING_MODE_KEYED:
            raise core.C2ContractError(
                "fading_field_receipt mode disagrees with source.fading_mode"
            )
    elif source.fading_field_receipt is not None:
        raise core.C2ContractError(
            "disabled C2 forecast cannot carry a keyed fading_field_receipt"
        )
    if not isinstance(source.source_rule, str) or not source.source_rule:
        raise core.C2ContractError("source.source_rule must be a non-empty string")
    users = _integer(user_count, field="user_count")
    focal = _integer(focal_user, field="focal_user")
    if users <= 0 or not 0 <= focal < users:
        raise core.C2ContractError("focal_user must lie inside a positive user_count")
    interval = _number(decision_interval_s, field="decision_interval_s", nonnegative=True)
    if interval <= 0.0:
        raise core.C2ContractError("decision_interval_s must be strictly positive")
    reference = _normalize_trace(reference_trace, users=users, field="reference_trace")
    candidate = _normalize_trace(candidate_trace, users=users, field="candidate_trace")
    if reference[0].states != candidate[0].states or reference[0].masks != candidate[0].masks:
        raise core.C2LeakageError("forecast twins do not share the exact opening state and mask")
    if reference[0].bindings != candidate[0].bindings:
        raise core.C2LeakageError("forecast twins do not share the exact opening action tables")

    pre_active = tuple(sorted(_physical(value, field="pre_active_physical_ids") for value in pre_active_physical_ids))
    if len(pre_active) != len(set(pre_active)):
        raise core.C2ContractError("pre-active physical IDs cannot repeat")
    reference_action = reference[0].main_actions[focal]
    reference_key = reference[0].main_physical[focal]
    candidate_action = candidate[0].executed_actions[focal]
    candidate_key = candidate[0].executed_physical[focal]
    if reference_action == NO_OP_ACTION or reference_key is None:
        raise core.C2ContractError("C2 requires a physical detached-Main reference")
    if candidate_action == NO_OP_ACTION or candidate_key is None:
        raise core.C2ContractError("C2 requires a physical temporal alternative")
    opening_bindings = candidate[0].bindings[focal]

    reference_is_main = all(
        step.executed_actions == step.main_actions
        and step.executed_physical == step.main_physical
        for step in reference
    )
    release_offset, release_reason, _support_counts = _candidate_release_metadata(
        candidate,
        focal_user=focal,
        candidate_key=candidate_key,
    )
    holds_candidate = all(
        step.executed_physical[focal] == candidate_key
        for step in candidate[:release_offset]
    )
    release_observed = bool(
        candidate[release_offset].executed_actions
        == candidate[release_offset].main_actions
        and candidate[release_offset].executed_physical
        == candidate[release_offset].main_physical
    )
    branch_structurally_valid = bool(
        reference_is_main and holds_candidate and release_observed
    )
    # A counterfactual branch may put Main into a different state and therefore
    # legitimately produce different non-focal actions than the reference
    # branch.  C2 owns only the focal override: every non-focal action must be
    # the frozen Main output for the *same candidate-branch input*.
    nonfocal_policy_aligned = all(
        candidate[offset].executed_actions[user]
        == candidate[offset].main_actions[user]
        and candidate[offset].executed_physical[user]
        == candidate[offset].main_physical[user]
        for offset in range(core.HORIZON_STEPS + 1)
        for user in range(users)
        if user != focal
    )
    focal_served = all(step.served[focal] for step in candidate)
    no_new_nonfocal_outage = all(
        not reference[offset].served[user] or candidate[offset].served[user]
        for offset in range(core.HORIZON_STEPS + 1)
        for user in range(users)
        if user != focal
    )

    reference_energy = interval * math.fsum(step.system_power_w for step in reference)
    candidate_energy = interval * math.fsum(step.system_power_w for step in candidate)
    reference_bits = interval * math.fsum(math.fsum(step.rates) for step in reference)
    candidate_bits = interval * math.fsum(math.fsum(step.rates) for step in candidate)
    activation_path = _activation_path(pre_active, reference, candidate)
    activation_or_energy = bool(activation_path or candidate_energy < reference_energy)
    hold_r2_margin = math.fsum(
        math.fsum(candidate[offset].rewards[user][core.C2_OBJECTIVE_INDEX] for user in range(users))
        - math.fsum(reference[offset].rewards[user][core.C2_OBJECTIVE_INDEX] for user in range(users))
        for offset in range(release_offset)
    )
    full_r2_margin = hold_r2_margin + math.fsum(
        math.fsum(
            candidate[offset].rewards[user][core.C2_OBJECTIVE_INDEX]
            for user in range(users)
        )
        - math.fsum(
            reference[offset].rewards[user][core.C2_OBJECTIVE_INDEX]
            for user in range(users)
        )
        for offset in range(release_offset, core.HORIZON_STEPS + 1)
    )

    anchor_sha256 = canonical_payload_sha256(source.anchor_payload)
    live_rng_sha256 = canonical_payload_sha256(source.live_rng_state)
    forecast_rng_sha256 = canonical_payload_sha256(source.forecast_rng_state)
    if live_rng_sha256 == forecast_rng_sha256:
        raise core.C2LeakageError("forecast RNG payload aliases the live RNG payload")
    for field in (
        "reference_checkpoint_sha256",
        "environment_source_sha256",
        "reward_source_sha256",
    ):
        _sha256(getattr(source, field), field=f"source.{field}")
    reference_trace_sha256 = canonical_payload_sha256(
        tuple(step.canonical for step in reference)
    )
    candidate_trace_sha256 = canonical_payload_sha256(
        tuple(step.canonical for step in candidate)
    )
    request_payload = {
        "version": core.CANDIDATE_VERSION,
        "anchor_sha256": anchor_sha256,
        "opening_states": reference[0].states,
        "opening_masks": reference[0].masks,
        "opening_bindings": tuple(
            tuple((row.action, row.physical_key) for row in user_rows)
            for user_rows in reference[0].bindings
        ),
        "focal_user": focal,
        "reference_action": reference_action,
        "reference_key": reference_key,
        "candidate_action": candidate_action,
        "candidate_key": candidate_key,
        "hold_steps": release_offset,
        "release_offset": release_offset,
        "release_reason": release_reason,
        "horizon_steps": core.HORIZON_STEPS,
        "decision_interval_s": interval,
        "pre_active_physical_ids": pre_active,
        "fading_mode": source.fading_mode,
        "fading_field_receipt": source.fading_field_receipt,
        "source_rule": source.source_rule,
        "min_reference_useful_bits": core.MIN_REFERENCE_USEFUL_BITS,
        "min_ee_surplus_fraction": core.MIN_EE_SURPLUS_FRACTION,
        "ee_surplus_ulp_multiplier": core.EE_SURPLUS_ULP_MULTIPLIER,
    }
    forecast_request_sha256 = canonical_payload_sha256(request_payload)
    forecast_payload_sha256 = canonical_payload_sha256(
        {
            "request": request_payload,
            "reference_trace": tuple(step.canonical for step in reference),
            "candidate_trace": tuple(step.canonical for step in candidate),
        }
    )
    authority = core.ForecastAuthority(
        schema=core.FORECAST_AUTHORITY_SCHEMA,
        anchor_sha256=anchor_sha256,
        reference_checkpoint_sha256=source.reference_checkpoint_sha256,
        environment_source_sha256=source.environment_source_sha256,
        reward_source_sha256=source.reward_source_sha256,
        live_rng_state_sha256=live_rng_sha256,
        forecast_rng_state_sha256=forecast_rng_sha256,
        forecast_request_sha256=forecast_request_sha256,
        forecast_payload_sha256=forecast_payload_sha256,
        forecast_namespace=source.forecast_namespace,
        fading_mode=source.fading_mode,
        generated_preoutcome=True,
        adapter_version=source.adapter_version,
    )
    evidence = core.TemporalForkEvidence(
        authority=authority,
        focal_user=focal,
        user_count=users,
        reference_action=reference_action,
        candidate_action=candidate_action,
        reference_key=reference_key,
        candidate_key=candidate_key,
        opening_action_bindings=opening_bindings,
        opening_action_table_sha256=core.action_table_sha256(opening_bindings),
        opening_state_sha256=canonical_payload_sha256(reference[0].states[focal]),
        opening_mask_sha256=canonical_payload_sha256(reference[0].masks[focal]),
        reference_branch_trace_sha256=reference_trace_sha256,
        candidate_branch_trace_sha256=candidate_trace_sha256,
        hold_steps=release_offset,
        release_observed=release_observed,
        branch_structurally_valid=branch_structurally_valid,
        nonfocal_policy_aligned=nonfocal_policy_aligned,
        focal_served_all_steps=focal_served,
        no_new_nonfocal_outage=no_new_nonfocal_outage,
        activation_or_energy_path=activation_or_energy,
        reference_useful_bits=reference_bits,
        candidate_useful_bits=candidate_bits,
        reference_energy_j=reference_energy,
        candidate_energy_j=candidate_energy,
        forecast_hold_r2_margin=hold_r2_margin,
        forecast_full_r2_margin=full_r2_margin,
        release_offset=release_offset,
        release_reason=release_reason,
        horizon_steps=core.HORIZON_STEPS,
    )
    certificate = core.certify_temporal_fork(evidence)
    return AuthoritativeForecastBuild(
        authority,
        evidence,
        certificate,
        reference_trace_sha256,
        candidate_trace_sha256,
        forecast_request_sha256,
        forecast_payload_sha256,
    )


def build_executed_option_step(
    certificate: core.TemporalForkCertificate,
    *,
    bundle_id: str,
    committed_step: ForecastStepPayload,
    behavior_probability: float,
    reward_source_sha256: str,
) -> core.ExecutedOptionStep:
    """Recompute one committed receipt from actual state/action/outcome arrays."""

    if not isinstance(certificate, core.TemporalForkCertificate):
        raise core.C2ContractError("certificate must be TemporalForkCertificate")
    if not isinstance(bundle_id, str) or not bundle_id:
        raise core.C2ContractError("bundle_id must be a nonempty string")
    reward_source = _sha256(reward_source_sha256, field="reward_source_sha256")
    if reward_source != certificate.reward_source_sha256:
        raise core.C2ContractError("committed reward source differs from certificate")
    step = _normalize_step(committed_step, users=certificate.user_count)
    behavior = _number(
        behavior_probability, field="behavior_probability", nonnegative=True
    )
    if not 0.0 < behavior <= 1.0:
        raise core.C2ContractError("behavior_probability must lie in (0,1]")
    horizon_steps = int(certificate.horizon_steps)
    if not 0 <= step.offset <= horizon_steps:
        raise core.C2ContractError("committed offset lies outside the sealed horizon")
    # New live rows carry their own policy decision.  A missing metadata block
    # is accepted only for old hand-built fixtures and falls back to the
    # certificate's planned release.
    if all(
        value is None
        for value in (
            step.held_physical_key,
            step.held_key_match_count,
            step.release_offset,
            step.release_reason,
        )
    ):
        release_offset = int(certificate.release_offset)
        release_reason = certificate.release_reason
    else:
        if any(
            value is None
            for value in (
                step.held_physical_key,
                step.held_key_match_count,
                step.release_offset,
                step.release_reason,
            )
        ):
            raise core.C2ContractError(
                "committed V0.3B row must bind held key/count and release offset/reason"
            )
        release_offset, release_reason, _ = core._release_policy(  # type: ignore[attr-defined]
            release_offset=step.release_offset,
            release_reason=step.release_reason,
            horizon_steps=horizon_steps,
            field_prefix="committed_step",
        )
    expected_phase = "hold" if step.offset < release_offset else "release"
    focal = certificate.focal_user
    action = step.executed_actions[focal]
    physical = step.executed_physical[focal]
    main_action = step.main_actions[focal]
    main_physical = step.main_physical[focal]
    if action == NO_OP_ACTION or physical is None:
        raise core.C2ContractError("committed C2 focal action must be physical")
    if main_action == NO_OP_ACTION or main_physical is None:
        raise core.C2ContractError("committed detached-Main focal action must be physical")
    focal_bindings = step.bindings[focal]
    if step.held_physical_key is not None:
        if step.held_physical_key != certificate.candidate_key:
            raise core.C2ContractError(
                "committed held physical key differs from certificate candidate"
            )
        support_count = sum(
            row.physical_key == certificate.candidate_key for row in focal_bindings
        )
        if step.held_key_match_count != support_count:
            raise core.C2ContractError(
                "committed held_key_match_count disagrees with its action table"
            )
        if step.offset < release_offset and support_count != 1:
            raise core.C2ContractError(
                "committed hold row lacks exactly one contemporaneous support match"
            )
        if step.offset == release_offset:
            if release_reason == "horizon" and support_count != 1:
                raise core.C2ContractError(
                    "horizon release row lacks unique held-key support"
                )
            if release_reason == "support_expired" and support_count == 1:
                raise core.C2ContractError(
                    "support-expired release row still has unique held-key support"
                )
    reward_matrix = step.rewards
    return core.ExecutedOptionStep(
        option_id=certificate.option_id,
        anchor_sha256=certificate.anchor_sha256,
        source_id="C2",
        bundle_id=bundle_id,
        behavior_probability=behavior,
        focal_user=focal,
        offset=step.offset,
        phase=expected_phase,
        action=action,
        physical_key=physical,
        detached_main_action=main_action,
        detached_main_key=main_physical,
        executed_joint_physical_actions=step.executed_physical,
        executed_joint_physical_sha256=core.joint_physical_actions_sha256(
            step.executed_physical, user_count=certificate.user_count
        ),
        detached_main_joint_physical_actions=step.main_physical,
        detached_main_joint_physical_sha256=core.joint_physical_actions_sha256(
            step.main_physical, user_count=certificate.user_count
        ),
        action_bindings=focal_bindings,
        action_table_sha256=core.action_table_sha256(focal_bindings),
        reward_matrix=reward_matrix,
        reward_matrix_sha256=core.reward_matrix_sha256(reward_matrix),
        reward_source_sha256=reward_source,
        focal_served=step.served[focal],
        served=step.served,
        state_sha256=canonical_payload_sha256(step.states[focal]),
        state_mask_sha256=canonical_payload_sha256(step.masks[focal]),
        next_state_sha256=canonical_payload_sha256(step.next_states[focal]),
        next_mask_sha256=canonical_payload_sha256(step.next_masks[focal]),
        done=step.done,
        held_physical_key=step.held_physical_key,
        held_key_match_count=step.held_key_match_count,
        release_offset=release_offset,
        release_reason=release_reason,
    )


def close_committed_option(
    certificate: core.TemporalForkCertificate,
    *,
    bundle_ids: Sequence[str],
    committed_steps: Sequence[ForecastStepPayload],
    behavior_probabilities: Sequence[float],
    reward_source_sha256: str,
    discount_factor: float,
    chronology_receipt: object | None = None,
) -> CommittedOptionClosure:
    """Build actual receipts, then apply the fail-closed option closure."""

    if not (
        len(bundle_ids) == len(committed_steps) == len(behavior_probabilities)
    ):
        raise core.C2ContractError(
            "bundle IDs, committed steps, and behavior probabilities disagree in length"
        )
    receipts = tuple(
        build_executed_option_step(
            certificate,
            bundle_id=bundle_id,
            committed_step=step,
            behavior_probability=probability,
            reward_source_sha256=reward_source_sha256,
        )
        for bundle_id, step, probability in zip(
            bundle_ids, committed_steps, behavior_probabilities, strict=True
        )
    )
    return CommittedOptionClosure(
        receipts,
        core.close_temporal_option(
            certificate,
            receipts,
            discount_factor=discount_factor,
            chronology_receipt=chronology_receipt,
        ),
    )


__all__ = [
    "AuthoritativeForecastBuild",
    "CommittedOptionClosure",
    "DECISION_INTERVAL_S",
    "ForecastSourcePayload",
    "ForecastStepPayload",
    "build_authoritative_forecast",
    "build_executed_option_step",
    "close_committed_option",
    "canonical_payload_sha256",
]
