"""Environment-specific C2 V0.3 temporal-fork backend.

This is an append-only bridge between the real ``TrainerEnvironment`` and the
pure C2 V0.3 forecast/chronology contracts.  It deliberately stops at one
prepared, one-candidate fork:

* reference is detached Main at every offset;
* candidate holds the opening physical key while it remains uniquely legal in
  each contemporaneous predecision table, then releases once (at the first
  support expiry or at the horizon) to its branch-local detached Main;
* forecast and live use the same candidate-local Main compositor: only the
  focal action is overridden during hold and all non-focals remain on their
  contemporaneous branch-local Main actions;
* forecast work uses fresh twins and fresh RNG objects; the default remains
  fading-disabled for legacy diagnostics, while current V0.3 probes explicitly
  select one shared branch-independent keyed fading field;
* only ``PreparedC2Fork.run_live_step`` can advance the supplied live wrapper,
  and it can do so once, after the chronology gate has closed the forecast.

The module does not train, write replay, mutate Main/Q2F, select a winner, or
claim EE efficacy.  The real loader factory is intentionally explicit about
the checkpoint, environment, and reward source digests; a caller must provide
those authorities instead of allowing a convenient but unverifiable default.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, is_dataclass, replace
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STAGE0 = HERE.parent / "catfish-stage0"
for _path in (HERE, STAGE0, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import c2_temporal_fork_chronology as chronology  # noqa: E402
import c2_temporal_fork_core as core  # noqa: E402
import c2_temporal_fork_forecast_adapter as forecast  # noqa: E402
import c2_temporal_fork_runtime_adapter as runtime  # noqa: E402
from mcrl.env.action_contract import Association, NO_OP_ACTION  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.head_pivotality import masked_greedy_actions  # noqa: E402


USERS = 100
HOLD_STEPS = core.HORIZON_STEPS
RELEASE_OFFSET = HOLD_STEPS
CLAIM_CEILING = (
    "C2 V0.3 mechanism/feasibility only; no training result, Main/Q2F update, "
    "EE efficacy, or deployment authorization"
)
FORECAST_NAMESPACE = "c2-v03/trainer-backend-policy-aligned-v1"
FORECAST_SCHEMA = "c2-v03-trainer-backend-forecast-rng-v4"
ANCHOR_SCHEMA = "c2-v03-trainer-backend-anchor-v4"
MAIN_POLICY_VERSION = "masked-greedy-scalarized-main-v1"
POLICY_COMPOSITOR_VERSION = "candidate-local-main-hold-while-legal-release-v2"


class C2BackendError(core.C2ContractError):
    """The real environment could not satisfy the exact C2 V0.3 seam."""


class C2ForecastSupportRejection(C2BackendError):
    """A detached forecast candidate became physically unsupported.

    This is a pre-live failed-support outcome, not permission to substitute a
    different action.  The selected live-option path retains its separate hard
    expiry error.
    """

    def __init__(
        self,
        reason: str,
        *,
        forecast_offset: int,
        user: int,
        physical_key: core.PhysicalKey | None,
        detail: str,
    ) -> None:
        self.reason = str(reason)
        self.forecast_offset = int(forecast_offset)
        self.user = int(user)
        self.physical_key = None if physical_key is None else tuple(physical_key)
        super().__init__(
            f"{self.reason} at forecast offset={self.forecast_offset}, "
            f"user={self.user}, physical_key={self.physical_key!r}: {detail}"
        )


def _require_sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C2BackendError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _copy_rng(rng: np.random.Generator) -> np.random.Generator:
    if not isinstance(rng, np.random.Generator):
        raise C2BackendError("RNG seam requires numpy.random.Generator")
    copied = np.random.default_rng()
    copied.bit_generator.state = copy.deepcopy(rng.bit_generator.state)
    return copied


def _rng_state(rng: np.random.Generator) -> Mapping[str, Any]:
    if not isinstance(rng, np.random.Generator):
        raise C2BackendError("RNG seam requires numpy.random.Generator")
    return copy.deepcopy(rng.bit_generator.state)


def _state_matrix(observation: Any, *, field: str = "state_matrix") -> np.ndarray:
    if not hasattr(observation, "state_matrix"):
        raise C2BackendError("observation lacks canonical state_matrix")
    value = np.asarray(observation.state_matrix, dtype=np.float32)
    if value.ndim != 2 or value.shape[0] == 0 or value.shape[1] == 0:
        raise C2BackendError(f"{field} must be a non-empty U-by-D matrix")
    if not np.all(np.isfinite(value)):
        raise C2BackendError(f"{field} contains a nonfinite value")
    return np.array(value, dtype=np.float32, copy=True)


def _mask_matrix(observation: Any, *, users: int) -> np.ndarray:
    if not hasattr(observation, "masks"):
        raise C2BackendError("observation lacks canonical masks")
    value = np.asarray(observation.masks)
    if value.dtype != np.bool_ or value.shape != (users, core.ACTION_DIM):
        raise C2BackendError(
            f"observation masks must be Boolean ({users},{core.ACTION_DIM})"
        )
    return np.array(value, dtype=bool, copy=True)


def _supplied_mask_matrix(masks: Sequence[Any], *, users: int) -> np.ndarray:
    """Normalize the live trainer masks without silently coercing bad values."""

    if len(masks) != users:
        raise C2BackendError("supplied masks disagree with user count")
    rows: list[np.ndarray] = []
    for uid, supplied in enumerate(masks):
        raw = getattr(supplied, "mask", supplied)
        value = np.asarray(raw)
        if value.dtype != np.bool_ or value.shape != (core.ACTION_DIM,):
            raise C2BackendError(
                f"supplied mask {uid} must be Boolean ({core.ACTION_DIM},)"
            )
        rows.append(np.array(value, dtype=bool, copy=True))
    return np.stack(rows)


def _slot_tables(observation: Any, *, users: int) -> tuple[Any, ...]:
    candidates = getattr(observation, "candidates", None)
    tables = getattr(candidates, "slot_tables", None)
    if tables is None or len(tables) != users:
        raise C2BackendError("observation slot tables disagree with user count")
    return tuple(tables)


def _bindings(observation: Any, *, users: int) -> tuple[tuple[core.ActionBinding, ...], ...]:
    tables = _slot_tables(observation, users=users)
    return tuple(runtime.action_bindings_from_slot_table(table) for table in tables)


def _physical_for_action(table: Any, action: int) -> core.PhysicalKey | None:
    action = int(action)
    if action == int(NO_OP_ACTION):
        return None
    if not 0 <= action < core.ACTION_DIM:
        raise C2BackendError(f"action {action} is outside the frozen action space")
    bindings = runtime.action_bindings_from_slot_table(table)
    matches = [row.physical_key for row in bindings if row.action == action]
    if len(matches) != 1:
        raise C2BackendError(f"action {action} is not uniquely bound in the slot table")
    return matches[0]


def _physical_vector(actions: Sequence[int], observation: Any, *, users: int) -> tuple[core.PhysicalKey | None, ...]:
    if len(actions) != users:
        raise C2BackendError("action vector disagrees with user count")
    tables = _slot_tables(observation, users=users)
    return tuple(
        _physical_for_action(table, int(action))
        for table, action in zip(tables, actions, strict=True)
    )


def _action_for_physical(table: Any, physical: core.PhysicalKey | None) -> int:
    bindings = runtime.action_bindings_from_slot_table(table)
    if physical is None:
        if bindings:
            raise C2BackendError(
                "reference NO_OP cannot be remapped while a valid physical action exists"
            )
        return int(NO_OP_ACTION)
    matches = [row.action for row in bindings if row.physical_key == tuple(physical)]
    if len(matches) != 1:
        raise C2BackendError(
            "reference physical action disappeared or is duplicated in candidate table: "
            f"{tuple(physical)!r}"
        )
    return int(matches[0])


def _objective_weights(trainer: Any) -> tuple[float, float, float]:
    if not hasattr(trainer, "config") or not hasattr(
        trainer.config, "objective_weights"
    ):
        raise C2BackendError("trainer lacks objective-weight authority")
    weights = tuple(float(value) for value in trainer.config.objective_weights)
    if (
        len(weights) != 3
        or any(not np.isfinite(value) or value < 0.0 for value in weights)
        or sum(weights) <= 0.0
    ):
        raise C2BackendError(
            "objective weights must be three finite nonnegative values with positive sum"
        )
    return weights  # type: ignore[return-value]


def _main_actions(trainer: Any, branch: "C2ForecastBranch") -> tuple[np.ndarray, tuple[core.PhysicalKey | None, ...]]:
    """Evaluate the deployed scalarized Main policy without updating it."""

    if not hasattr(trainer, "encode_states") or not hasattr(trainer, "scalarized_q_values"):
        raise C2BackendError("trainer lacks the read-only Main inference surface")
    encoded = trainer.encode_states(branch.states)
    weights = _objective_weights(trainer)
    q_values = trainer.scalarized_q_values(encoded, objective_weights=weights)
    actions = np.asarray(
        masked_greedy_actions(q_values, _mask_matrix(branch.observation, users=len(branch.states))),
        dtype=np.int32,
    )
    if actions.shape != (len(branch.states),):
        raise C2BackendError("Main policy returned an action vector of the wrong shape")
    physical = _physical_vector(actions.tolist(), branch.observation, users=len(branch.states))
    return actions, physical


def _active_physical_ids(outcome: Any) -> tuple[core.PhysicalKey, ...]:
    resolution = getattr(outcome, "resolution", None)
    active = getattr(resolution, "active_beams", None)
    if active is None:
        raise C2BackendError("step outcome lacks exact active physical IDs")
    values = tuple(sorted((int(key[0]), int(key[1])) for key in active))
    if len(values) != len(set(values)):
        raise C2BackendError("step outcome repeats an active physical ID")
    return values


def _served(outcome: Any, *, users: int) -> tuple[bool, ...]:
    resolution = getattr(outcome, "resolution", None)
    values = np.asarray(getattr(resolution, "served", None))
    if values.dtype != np.bool_ or values.shape != (users,):
        raise C2BackendError("step outcome lacks an exact Boolean served vector")
    return tuple(bool(value) for value in values.tolist())


def _rates(outcome: Any, *, users: int) -> tuple[float, ...]:
    values = np.asarray(getattr(outcome, "link_rate_bps", None), dtype=np.float64)
    if values.shape != (users,) or not np.all(np.isfinite(values)) or np.any(values < 0.0):
        raise C2BackendError("step outcome lacks finite nonnegative link rates")
    return tuple(float(value) for value in values.tolist())


def _reward_matrix(outcome: Any, *, users: int) -> tuple[tuple[float, float, float], ...]:
    values = np.asarray(getattr(outcome, "reward_matrix", None), dtype=np.float64)
    if values.shape != (users, 3) or not np.all(np.isfinite(values)):
        raise C2BackendError("step outcome lacks a finite raw U-by-3 reward matrix")
    return tuple(tuple(float(value) for value in row) for row in values.tolist())


def _copy_detached_environment(
    wrapped: Any,
    *,
    fading_field: KeyedFadingField | None = None,
) -> Any:
    """Reuse the C3 V3 shallow immutable/deep mutable episode-copy seam."""

    environment = getattr(wrapped, "environment", None)
    if environment is None:
        raise C2BackendError("wrapped object lacks an environment")
    # The real TrainerEnvironment has a driver and benefits from the existing
    # immutable-TLE/shallow-copy seam.  Fixture environments intentionally use
    # a deepcopy; this branch is useful for bounded contract smoke only.
    if hasattr(environment, "driver"):
        try:
            from c3_reward_aligned_v3_trainer_backend import (  # noqa: PLC0415
                _copy_trainer_environment,
            )

            clone = _copy_trainer_environment(wrapped)
        except Exception as error:  # pragma: no cover - real adapter failure
            raise C2BackendError(
                "real detached TrainerEnvironment copy failed: "
                f"{type(error).__name__}: {error}"
            ) from error
    else:
        try:
            clone = copy.deepcopy(wrapped)
        except Exception as error:  # pragma: no cover - fixture diagnostic
            raise C2BackendError(
                f"detached environment copy failed: {type(error).__name__}: {error}"
            ) from error
    clone_environment = getattr(clone, "environment", None)
    if clone_environment is None:
        raise C2BackendError("detached clone lacks an environment")
    physics = getattr(clone_environment, "physics", None)
    if physics is None and fading_field is not None:
        raise C2BackendError("keyed detached clone lacks canonical physics")
    if physics is not None:
        enabled = fading_field is not None
        if is_dataclass(physics):
            clone_environment.physics = replace(physics, fading_enabled=enabled)
        else:
            clone_physics = copy.copy(physics)
            clone_physics.fading_enabled = enabled
            clone_environment.physics = clone_physics
    clone_environment._fading_field = fading_field
    return clone


@dataclass
class C2ForecastBranch:
    wrapped: Any
    env_rng: np.random.Generator
    mobility_rng: np.random.Generator
    states: list[Any]
    masks: list[Any]
    observation: Any
    trainer: Any
    focal_user: int
    role: str
    offset: int = 0


@dataclass(frozen=True)
class C2OpeningAnchor:
    """Materialized live pre-action anchor and its source authority."""

    wrapped: Any
    trainer: Any
    states: tuple[Any, ...]
    masks: tuple[Any, ...]
    observation: Any
    env_rng: np.random.Generator
    mobility_rng: np.random.Generator
    focal_user: int
    evaluation_seed: int
    checkpoint_sha256: str
    environment_source_sha256: str
    reward_source_sha256: str
    anchor_payload: Mapping[str, Any]
    anchor_sha256: str
    pre_active_physical_ids: tuple[core.PhysicalKey, ...]
    main_actions: tuple[int, ...]
    main_physical_actions: tuple[core.PhysicalKey | None, ...]
    action_bindings_by_user: tuple[tuple[core.ActionBinding, ...], ...]
    forecast_fading_mode: str


@dataclass(frozen=True)
class C2LiveStep:
    action_indices: tuple[int, ...]
    physical_actions: tuple[core.PhysicalKey | None, ...]
    result: Any
    outcome: Any


def _branch_from_anchor(
    anchor: C2OpeningAnchor,
    *,
    role: str,
    env_rng: np.random.Generator,
    mobility_rng: np.random.Generator,
    fading_field: KeyedFadingField | None = None,
) -> C2ForecastBranch:
    clone = _copy_detached_environment(
        anchor.wrapped,
        fading_field=fading_field,
    )
    clone.environment._mobility_rng = mobility_rng
    observation = copy.deepcopy(anchor.observation)
    return C2ForecastBranch(
        wrapped=clone,
        env_rng=env_rng,
        mobility_rng=mobility_rng,
        states=copy.deepcopy(list(anchor.states)),
        masks=copy.deepcopy(list(anchor.masks)),
        observation=observation,
        trainer=anchor.trainer,
        focal_user=anchor.focal_user,
        role=role,
    )


def _step_payload(
    branch: C2ForecastBranch,
    *,
    offset: int,
    detached_main_actions: Sequence[int],
    detached_main_physical: Sequence[core.PhysicalKey | None],
    executed_actions: Sequence[int],
    held_physical_key: core.PhysicalKey | None = None,
    held_key_match_count: int | None = None,
    release_offset: int | None = None,
    release_reason: str | None = None,
) -> forecast.ForecastStepPayload:
    if branch.offset != offset:
        raise C2BackendError(
            f"{branch.role} branch expected offset {branch.offset}, got {offset}"
        )
    users = len(branch.states)
    states = _state_matrix(branch.observation)
    masks = _mask_matrix(branch.observation, users=users)
    bindings = _bindings(branch.observation, users=users)
    main_actions = tuple(int(value) for value in detached_main_actions)
    main_physical = tuple(detached_main_physical)
    actions = tuple(int(value) for value in executed_actions)
    physical = _physical_vector(actions, branch.observation, users=users)
    if len(main_actions) != users or len(main_physical) != users or len(actions) != users:
        raise C2BackendError("forecast action vectors disagree with user count")
    try:
        result = branch.wrapped.step(np.asarray(actions, dtype=np.int32), branch.env_rng)
        outcome = branch.wrapped.last_outcome
    except Exception as error:
        raise C2BackendError(f"{branch.role} detached step failed at offset {offset}") from error
    if outcome is None:
        raise C2BackendError("detached step did not expose last_outcome")
    done = bool(getattr(result, "done", getattr(outcome, "done", False)))
    # Detached forecast branches must complete the certified horizon.  The
    # selected live option is different: a real environment terminal is an
    # observed, admissible prefix and must be returned to the option runner
    # without padding.  Nonterminal physical expiry is still handled as a
    # hard error by the caller.
    if offset < RELEASE_OFFSET and done and branch.role != "live-option-commit":
        raise C2BackendError(f"{branch.role} branch terminated before release")
    next_observation = getattr(outcome, "observation", None)
    if next_observation is None:
        raise C2BackendError("step outcome lacks the exact successor observation")
    next_states = _state_matrix(next_observation, field="next_state_matrix")
    next_masks = _mask_matrix(next_observation, users=users)
    payload = forecast.ForecastStepPayload(
        offset=offset,
        state_matrix=states,
        mask_matrix=masks,
        action_bindings_by_user=bindings,
        detached_main_actions=main_actions,
        detached_main_physical_actions=main_physical,
        executed_actions=actions,
        executed_physical_actions=physical,
        reward_matrix=_reward_matrix(outcome, users=users),
        served=_served(outcome, users=users),
        link_rate_bps=_rates(outcome, users=users),
        system_power_w=float(getattr(outcome, "system_power_w", float("nan"))),
        active_physical_ids=_active_physical_ids(outcome),
        next_state_matrix=next_states,
        next_mask_matrix=next_masks,
        done=done,
        held_physical_key=held_physical_key,
        held_key_match_count=held_key_match_count,
        release_offset=release_offset,
        release_reason=release_reason,
    )
    if not np.isfinite(payload.system_power_w) or payload.system_power_w <= 0.0:
        raise C2BackendError("detached step lacks a positive finite system power")
    # Update only the detached branch.  ``result`` is the canonical post-step
    # user-state/action-mask source; observation carries the encoded matrices.
    if not hasattr(result, "user_states") or not hasattr(result, "action_masks"):
        raise C2BackendError("step result lacks exact successor user states/masks")
    if len(result.user_states) != users or len(result.action_masks) != users:
        raise C2BackendError("step result successor arrays disagree with user count")
    branch.states = list(result.user_states)
    branch.masks = list(result.action_masks)
    branch.observation = next_observation
    branch.offset += 1
    return payload


def _candidate_support_count(
    observation: Any,
    *,
    focal_user: int,
    candidate_key: core.PhysicalKey,
) -> int:
    """Count exact focal matches in this offset's predecision slot table.

    This is intentionally a local observation-only operation.  It does not
    inspect a successor observation, a reference twin, reward/service data, or
    a later planned offset.  A valid canonical table normally yields 0 or 1;
    returning a count keeps the uniqueness rule explicit in the receipt.
    """

    users = int(getattr(observation, "num_users", 0))
    if users <= 0 or type(focal_user) is not int or not 0 <= focal_user < users:
        raise C2BackendError("candidate support query has an invalid focal user")
    bindings = _bindings(observation, users=users)[focal_user]
    return sum(1 for row in bindings if row.physical_key == tuple(candidate_key))


def _compose_candidate_actions(
    *,
    observation: Any,
    main_actions: Sequence[int],
    main_physical: Sequence[core.PhysicalKey | None],
    candidate_key: core.PhysicalKey,
    focal_user: int,
    offset: int,
    hold: bool | None = None,
) -> tuple[np.ndarray, tuple[core.PhysicalKey | None, ...]]:
    """Apply the one owned C2 intervention to branch-local frozen Main.

    This function is the shared forecast/live policy seam.  It never imports a
    future action from the reference counterfactual: non-focals execute the
    Main output evaluated on this branch's contemporaneous state and mask.
    """

    actions = np.asarray(tuple(main_actions), dtype=np.int32)
    users = int(actions.size)
    if actions.ndim != 1 or users <= 0:
        raise C2BackendError("Main action vector must be one-dimensional and nonempty")
    if not 0 <= int(focal_user) < users:
        raise C2BackendError("focal user lies outside the Main action vector")
    if type(offset) is not int or not 0 <= offset <= HOLD_STEPS:
        raise C2BackendError("candidate compositor offset lies outside hold plus release")
    if hold is None:
        # Compatibility for old direct callers; all V0.3B production paths
        # pass the sealed local support decision explicitly.
        hold = offset < HOLD_STEPS
    if type(hold) is not bool:
        raise C2BackendError("candidate compositor hold decision must be Boolean")
    expected_main_physical = tuple(main_physical)
    if len(expected_main_physical) != users:
        raise C2BackendError("Main physical vector disagrees with user count")
    mapped_main_physical = _physical_vector(
        actions.tolist(), observation, users=users
    )
    if mapped_main_physical != expected_main_physical:
        raise C2BackendError(
            "Main action and physical vectors disagree before C2 composition"
        )

    executed = actions.copy()
    if hold:
        focal_table = _slot_tables(observation, users=users)[focal_user]
        executed[focal_user] = _map_candidate_focal_hold(
            focal_table,
            candidate_key,
            focal_user=focal_user,
            offset=offset,
        )
    executed_physical = _physical_vector(
        executed.tolist(), observation, users=users
    )
    if any(
        executed[user] != actions[user]
        or executed_physical[user] != mapped_main_physical[user]
        for user in range(users)
        if user != focal_user
    ):
        raise C2BackendError("C2 compositor changed a nonfocal Main action")
    if not hold and (
        not np.array_equal(executed, actions)
        or executed_physical != mapped_main_physical
    ):
        raise C2BackendError("C2 release must execute complete branch-local Main")
    return executed, executed_physical


def _map_candidate_focal_hold(
    table: Any,
    candidate_key: core.PhysicalKey,
    *,
    focal_user: int,
    offset: int,
) -> int:
    try:
        return _action_for_physical(table, candidate_key)
    except C2BackendError as error:
        raise C2ForecastSupportRejection(
            "focal_hold_expired",
            forecast_offset=offset,
            user=focal_user,
            physical_key=candidate_key,
            detail=str(error),
        ) from error


def _derive_fading_field(
    anchor: C2OpeningAnchor,
) -> tuple[KeyedFadingField | None, Mapping[str, Any] | None]:
    """Derive the one immutable fading field shared by both matched twins."""

    if anchor.forecast_fading_mode == core.FADING_MODE_DISABLED:
        return None, None
    if anchor.forecast_fading_mode != core.FADING_MODE_KEYED:
        raise C2BackendError("unsupported C2 forecast fading mode")
    field = KeyedFadingField.from_components(
        FORECAST_SCHEMA,
        anchor.checkpoint_sha256,
        anchor.anchor_sha256,
        anchor.focal_user,
        anchor.evaluation_seed,
    )
    return field, field.receipt()


def _derive_forecast_rngs(
    anchor: C2OpeningAnchor,
    *,
    fading_field_receipt: Mapping[str, Any] | None = None,
) -> tuple[dict[str, np.random.Generator], dict[str, Any]]:
    """Create independent, common-random-number twin streams.

    The reference and candidate receive separate generator objects and
    domain-labelled receipts, but equal initial states.  This preserves the
    usual paired-forecast comparison without aliasing or advancing the live
    generators.
    """

    seed_material = forecast.canonical_payload_sha256(
        {
            "schema": FORECAST_SCHEMA,
            "checkpoint_sha256": anchor.checkpoint_sha256,
            "anchor_sha256": anchor.anchor_sha256,
            "focal_user": anchor.focal_user,
            "evaluation_seed": anchor.evaluation_seed,
        }
    )
    seed = int(seed_material[:32], 16)
    env = np.random.default_rng(np.random.SeedSequence(seed))
    mobility = np.random.default_rng(np.random.SeedSequence(seed ^ 0x5A17))
    # Distinct objects, equal states, and explicit role labels are intentional.
    reference_env = _copy_rng(env)
    candidate_env = _copy_rng(env)
    reference_mobility = _copy_rng(mobility)
    candidate_mobility = _copy_rng(mobility)
    initial = {
        "schema": FORECAST_SCHEMA,
        "fading_mode": anchor.forecast_fading_mode,
        "fading_field_receipt": fading_field_receipt,
        "reference": {
            "domain": "reference",
            "namespace": FORECAST_NAMESPACE + "/reference",
            "environment": _rng_state(reference_env),
            "mobility": _rng_state(reference_mobility),
        },
        "candidate": {
            "domain": "candidate",
            "namespace": FORECAST_NAMESPACE + "/candidate",
            "environment": _rng_state(candidate_env),
            "mobility": _rng_state(candidate_mobility),
        },
    }
    return (
        {
            "reference_env": reference_env,
            "candidate_env": candidate_env,
            "reference_mobility": reference_mobility,
            "candidate_mobility": candidate_mobility,
        },
        initial,
    )


def _forecast_rng_receipt(
    initial: Mapping[str, Any],
    branches: Sequence[C2ForecastBranch],
) -> Mapping[str, Any]:
    by_role = {branch.role: branch for branch in branches}
    output = copy.deepcopy(dict(initial))
    for role in ("reference", "candidate"):
        branch = by_role[role]
        output[role]["environment_final"] = _rng_state(branch.env_rng)
        output[role]["mobility_final"] = _rng_state(branch.mobility_rng)
    return output


def _pre_active_ids(wrapped: Any, supplied: Sequence[core.PhysicalKey] | None) -> tuple[core.PhysicalKey, ...]:
    if supplied is not None:
        return tuple(sorted((int(key[0]), int(key[1])) for key in supplied))
    previous = getattr(getattr(wrapped, "environment", None), "_previous_radiating", None)
    if previous is None:
        return ()
    norads = np.asarray(getattr(previous, "norad_ids", ()), dtype=np.int64)
    cells = np.asarray(getattr(previous, "cell_ids", ()), dtype=np.int64)
    if norads.shape != cells.shape:
        raise C2BackendError("previous radiating IDs have incompatible shapes")
    return tuple(sorted((int(norad), int(cell)) for norad, cell in zip(norads.tolist(), cells.tolist(), strict=True)))


def _incumbent_key(wrapped: Any, *, focal_user: int) -> core.PhysicalKey:
    environment = getattr(wrapped, "environment", None)
    previous = getattr(environment, "_previous_association", None)
    if previous is None or not 0 <= focal_user < len(previous):
        raise C2BackendError("live environment lacks the focal incumbent association")
    association = previous[focal_user]
    if not isinstance(association, Association):
        raise C2BackendError("C2 incumbent-hold requires a served physical incumbent")
    return int(association.norad_id), int(association.cell_id)


def _max_lagged_gain_rival(
    observation: Any,
    *,
    focal_user: int,
    main_key: core.PhysicalKey,
) -> core.PhysicalKey:
    """Choose the legal non-Main rival from predecision candidate SINR.

    ``candidate_sinr`` is evaluated with the previous radiating set, so it is
    the canonical lagged-interference channel-quality surface available before
    the current action.  Equal scores break by physical ID and then action ID.
    """

    tables = _slot_tables(observation, users=int(getattr(observation, "num_users")))
    table = tables[focal_user]
    values = np.asarray(getattr(observation, "candidate_sinr", None), dtype=np.float64)
    if values.shape != (len(tables), 28):
        raise C2BackendError("observation lacks the canonical candidate_sinr matrix")
    rows: list[tuple[float, core.PhysicalKey, int]] = []
    for binding in _bindings(observation, users=len(tables))[focal_user]:
        if binding.physical_key == tuple(main_key):
            continue
        score = float(values[focal_user, binding.action])
        if not np.isfinite(score):
            continue
        # Revalidate through the exact opening slot table before sealing.
        if table.association(binding.action) is None:
            continue
        rows.append((score, binding.physical_key, binding.action))
    if not rows:
        raise C2BackendError("no finite legal lagged-gain rival exists")
    rows.sort(key=lambda row: (-row[0], row[1][0], row[1][1], row[2]))
    return rows[0][1]


def _anchor_payload(
    *,
    observation: Any,
    states: Sequence[Any],
    masks: Sequence[Any],
    bindings: Sequence[Sequence[core.ActionBinding]],
    env_rng: np.random.Generator,
    mobility_rng: np.random.Generator,
    focal_user: int,
    evaluation_seed: int,
    checkpoint_sha256: str,
    environment_source_sha256: str,
    reward_source_sha256: str,
    objective_weights: Sequence[float],
    main_actions: Sequence[int],
    main_physical: Sequence[core.PhysicalKey | None],
    pre_active: Sequence[core.PhysicalKey],
    forecast_fading_mode: str,
) -> Mapping[str, Any]:
    return {
        "schema": ANCHOR_SCHEMA,
        "step_index": int(getattr(observation, "step_index")),
        "focal_user": int(focal_user),
        "evaluation_seed": int(evaluation_seed),
        "checkpoint_sha256": checkpoint_sha256,
        "environment_source_sha256": environment_source_sha256,
        "reward_source_sha256": reward_source_sha256,
        "forecast_fading_mode": forecast_fading_mode,
        "main_policy_contract": {
            "main_policy_version": MAIN_POLICY_VERSION,
            "compositor_version": POLICY_COMPOSITOR_VERSION,
            "checkpoint_sha256": checkpoint_sha256,
            "objective_weights": tuple(float(value) for value in objective_weights),
        },
        "state_matrix": _state_matrix(observation).tolist(),
        "mask_matrix": _mask_matrix(observation, users=len(states)).tolist(),
        "states_sha256": forecast.canonical_payload_sha256(_state_matrix(observation)),
        "masks_sha256": forecast.canonical_payload_sha256(_mask_matrix(observation, users=len(states))),
        "action_bindings_by_user": tuple(
            tuple((row.action, row.physical_key) for row in user_rows)
            for user_rows in bindings
        ),
        "main_actions": tuple(int(value) for value in main_actions),
        "main_physical_actions": tuple(main_physical),
        "pre_active_physical_ids": tuple(pre_active),
        "live_environment_rng_state": _rng_state(env_rng),
        "live_mobility_rng_state": _rng_state(mobility_rng),
    }


@dataclass
class PreparedC2Fork:
    """A one-candidate forecast prepared at a live anchor."""

    backend: "C2TemporalForkTrainerBackend"
    anchor: C2OpeningAnchor
    candidate_key: core.PhysicalKey
    gate: chronology.PreoutcomeForecastGate
    source_rule: str
    _build: forecast.AuthoritativeForecastBuild | None = field(default=None, init=False)
    _reference_trace: tuple[forecast.ForecastStepPayload, ...] = field(
        default=(), init=False, repr=False
    )
    _candidate_trace: tuple[forecast.ForecastStepPayload, ...] = field(
        default=(), init=False, repr=False
    )
    _forecast_rng_state: Mapping[str, Any] | None = field(
        default=None, init=False, repr=False
    )

    @property
    def build(self) -> forecast.AuthoritativeForecastBuild | None:
        return self._build

    @property
    def phase(self) -> str:
        return self.gate.phase

    @property
    def reference_trace(self) -> tuple[forecast.ForecastStepPayload, ...]:
        """Defensive copy of the exact detached-Main reference trace."""

        return copy.deepcopy(self._reference_trace)

    @property
    def candidate_trace(self) -> tuple[forecast.ForecastStepPayload, ...]:
        """Defensive copy of the exact monotone hold/release candidate trace."""

        return copy.deepcopy(self._candidate_trace)

    @property
    def forecast_rng_state(self) -> Mapping[str, Any] | None:
        """Defensive copy of the domain-labelled forecast RNG receipt."""

        return None if self._forecast_rng_state is None else copy.deepcopy(self._forecast_rng_state)

    def run_forecast(self) -> forecast.AuthoritativeForecastBuild:
        if self._build is not None:
            raise C2BackendError("C2 forecast can be produced exactly once")

        def producer(
            anchor_payload: Mapping[str, Any], live_state: Mapping[str, Any]
        ) -> forecast.AuthoritativeForecastBuild:
            if forecast.canonical_payload_sha256(anchor_payload) != self.anchor.anchor_sha256:
                raise C2BackendError("chronology gate supplied an anchor different from the live materialized anchor")
            build, forecast_state, reference_trace, candidate_trace = self.backend._produce_forecast(
                self.anchor,
                live_state,
                candidate_key=self.candidate_key,
                source_rule=self.source_rule,
            )
            self._forecast_rng_state = copy.deepcopy(forecast_state)
            self._reference_trace = tuple(copy.deepcopy(reference_trace))
            self._candidate_trace = tuple(copy.deepcopy(candidate_trace))
            return build

        self._build = self.gate.run_forecast(producer)
        return self._build

    def run_live_step(self) -> tuple[C2LiveStep, chronology.PreoutcomeForecastReceipt]:
        if self._build is None or self.gate.phase != "forecast_complete":
            raise C2BackendError("live C2 step requires a completed forecast")
        if not self._build.certificate.passed:
            raise C2BackendError("failed C2 certificate cannot be executed")

        def executor() -> C2LiveStep:
            actions, physical = _compose_candidate_actions(
                observation=self.anchor.observation,
                main_actions=self.anchor.main_actions,
                main_physical=self.anchor.main_physical_actions,
                candidate_key=self.candidate_key,
                focal_user=self.anchor.focal_user,
                offset=0,
            )
            if physical[self.anchor.focal_user] != self.candidate_key:
                raise C2BackendError("live focal action does not bind the candidate incumbent")
            result = self.anchor.wrapped.step(actions, self.anchor.env_rng)
            outcome = self.anchor.wrapped.last_outcome
            if outcome is None:
                raise C2BackendError("live step did not expose last_outcome")
            return C2LiveStep(tuple(int(value) for value in actions.tolist()), physical, result, outcome)

        return self.gate.run_live_step(executor)


class C2TemporalForkTrainerBackend:
    """One-candidate real ``TrainerEnvironment`` C2 V0.3 adapter."""

    def __init__(
        self,
        *,
        wrapped: Any,
        states: Sequence[Any],
        masks: Sequence[Any],
        observation: Any,
        env_rng: np.random.Generator,
        trainer: Any,
        checkpoint_sha256: str,
        environment_source_sha256: str,
        reward_source_sha256: str,
        evaluation_seed: int,
        focal_user: int = 0,
        pre_active_physical_ids: Sequence[core.PhysicalKey] | None = None,
        forecast_fading_mode: str = core.FADING_MODE_DISABLED,
    ) -> None:
        checkpoint_sha256 = _require_sha256(checkpoint_sha256, field="checkpoint_sha256")
        environment_source_sha256 = _require_sha256(
            environment_source_sha256, field="environment_source_sha256"
        )
        reward_source_sha256 = _require_sha256(
            reward_source_sha256, field="reward_source_sha256"
        )
        if not isinstance(env_rng, np.random.Generator):
            raise C2BackendError("env_rng must be a numpy Generator")
        if type(evaluation_seed) is not int or evaluation_seed < 0:
            raise C2BackendError("evaluation_seed must be a nonnegative exact integer")
        if forecast_fading_mode not in core.FORECAST_FADING_MODES:
            raise C2BackendError("unsupported forecast_fading_mode")
        if not hasattr(wrapped, "environment"):
            raise C2BackendError("wrapped object must expose a TrainerEnvironment")
        users = len(states)
        if users <= 0 or len(masks) != users:
            raise C2BackendError("live states and masks disagree on user count")
        if type(focal_user) is not int or not 0 <= focal_user < users:
            raise C2BackendError("focal_user lies outside the live anchor")
        if int(getattr(observation, "num_users", users)) != users:
            raise C2BackendError("live observation disagrees with user count")
        state_matrix = _state_matrix(observation)
        mask_matrix = _mask_matrix(observation, users=users)
        if state_matrix.shape[0] != users or len(getattr(observation, "user_states", states)) != users:
            raise C2BackendError("live observation state rows disagree with user count")
        objective_weights = _objective_weights(trainer)
        if not hasattr(trainer, "encode_states"):
            raise C2BackendError("trainer lacks the canonical state encoder")
        encoded_states = np.asarray(trainer.encode_states(list(states)), dtype=np.float32)
        if (
            encoded_states.shape != state_matrix.shape
            or not np.all(np.isfinite(encoded_states))
            or not np.array_equal(encoded_states, state_matrix)
        ):
            raise C2BackendError(
                "trainer-encoded live states disagree with the observation state_matrix"
            )
        supplied_masks = _supplied_mask_matrix(masks, users=users)
        if not np.array_equal(supplied_masks, mask_matrix):
            raise C2BackendError(
                "supplied live masks disagree with the observation mask_matrix"
            )
        mobility_rng = getattr(wrapped.environment, "_mobility_rng", None)
        if not isinstance(mobility_rng, np.random.Generator):
            raise C2BackendError("live environment lacks its mobility RNG")
        bindings = _bindings(observation, users=users)
        main = C2ForecastBranch(
            wrapped=wrapped,
            env_rng=env_rng,
            mobility_rng=mobility_rng,
            states=list(states),
            masks=list(masks),
            observation=observation,
            trainer=trainer,
            focal_user=focal_user,
            role="live",
        )
        main_actions, main_physical = _main_actions(trainer, main)
        pre_active = _pre_active_ids(wrapped, pre_active_physical_ids)
        payload = _anchor_payload(
            observation=observation,
            states=states,
            masks=masks,
            bindings=bindings,
            env_rng=env_rng,
            mobility_rng=mobility_rng,
            focal_user=focal_user,
            evaluation_seed=evaluation_seed,
            checkpoint_sha256=checkpoint_sha256,
            environment_source_sha256=environment_source_sha256,
            reward_source_sha256=reward_source_sha256,
            objective_weights=objective_weights,
            main_actions=main_actions.tolist(),
            main_physical=main_physical,
            pre_active=pre_active,
            forecast_fading_mode=forecast_fading_mode,
        )
        self.wrapped = wrapped
        self.states = tuple(states)
        self.masks = tuple(masks)
        self.observation = observation
        self.env_rng = env_rng
        self.mobility_rng = mobility_rng
        self.trainer = trainer
        self.checkpoint_sha256 = checkpoint_sha256
        self.environment_source_sha256 = environment_source_sha256
        self.reward_source_sha256 = reward_source_sha256
        self.evaluation_seed = evaluation_seed
        self.forecast_fading_mode = forecast_fading_mode
        self._default_focal_user = focal_user
        self._users = users
        self._pre_active_physical_ids = pre_active
        self._main_actions = tuple(int(value) for value in main_actions.tolist())
        self._main_physical_actions = tuple(main_physical)
        self._bindings = bindings
        self._anchor_payload = payload
        self._anchor_sha256 = forecast.canonical_payload_sha256(payload)

    @classmethod
    def from_replayed_anchor(
        cls,
        archive: Any,
        trainer: Any,
        *,
        evaluation_seed: int,
        focal_user: int,
        checkpoint_sha256: str,
        environment_source_sha256: str,
        reward_source_sha256: str,
        prefix_actions: Sequence[np.ndarray] = (),
        pre_active_physical_ids: Sequence[core.PhysicalKey] | None = None,
        forecast_fading_mode: str = core.FADING_MODE_DISABLED,
    ) -> "C2TemporalForkTrainerBackend":
        """Materialize one real anchor through the existing Stage-0 loader.

        The loader is imported lazily so deterministic contract tests do not
        load the 9000-episode checkpoint or the TLE archive.  This method only
        replays the caller-supplied prefix and never launches training.
        """

        if type(focal_user) is not int or focal_user < 0:
            raise C2BackendError("focal_user must be a nonnegative exact integer")
        try:
            import run_c2_stage0 as legacy  # noqa: PLC0415

            materialized = legacy._reconstruct_anchor(
                archive, seed=int(evaluation_seed), prefix_actions=prefix_actions
            )
        except Exception as error:
            raise C2BackendError("existing real TLE/checkpoint anchor loader failed") from error
        states = materialized["states"]
        if focal_user >= len(states):
            raise C2BackendError("focal_user lies outside the materialized anchor")
        backend = cls(
            wrapped=materialized["wrapped"],
            states=states,
            masks=materialized["masks"],
            observation=materialized["observation"],
            env_rng=materialized["env_rng"],
            trainer=trainer,
            checkpoint_sha256=checkpoint_sha256,
            environment_source_sha256=environment_source_sha256,
            reward_source_sha256=reward_source_sha256,
            evaluation_seed=evaluation_seed,
            focal_user=focal_user,
            pre_active_physical_ids=pre_active_physical_ids,
            forecast_fading_mode=forecast_fading_mode,
        )
        return backend

    @property
    def anchor_sha256(self) -> str:
        return self._anchor_sha256

    def _live_rng_state(self) -> Mapping[str, Any]:
        return {
            "schema": "c2-v03-live-rng-state-v1",
            "environment": _rng_state(self.env_rng),
            "mobility": _rng_state(self.mobility_rng),
        }

    def _prepare_physical_candidate(
        self,
        *,
        focal_user: int,
        candidate_key: core.PhysicalKey,
        source_rule: str,
    ) -> PreparedC2Fork:
        if focal_user is None:
            focal_user = int(getattr(self, "_default_focal_user", 0))
        if type(focal_user) is not int or not 0 <= focal_user < self._users:
            raise C2BackendError("focal_user lies outside the live anchor")
        if focal_user != self._default_focal_user:
            raise C2BackendError(
                "prepared focal_user must equal the focal authority materialized at construction"
            )
        main_key = self._main_physical_actions[focal_user]
        if main_key is None:
            raise C2BackendError("C2 requires a physical detached-Main handover anchor")
        candidate_key = (int(candidate_key[0]), int(candidate_key[1]))
        if tuple(main_key) == candidate_key:
            raise C2BackendError("C2 candidate equals opening Main; no fork exists")
        opening_table = _slot_tables(self.observation, users=self._users)[focal_user]
        candidate_action = _action_for_physical(opening_table, candidate_key)
        if candidate_action == int(NO_OP_ACTION):
            raise C2BackendError("candidate is not executable at the opening anchor")
        anchor = C2OpeningAnchor(
            wrapped=self.wrapped,
            trainer=self.trainer,
            states=self.states,
            masks=self.masks,
            observation=self.observation,
            env_rng=self.env_rng,
            mobility_rng=self.mobility_rng,
            focal_user=focal_user,
            evaluation_seed=self.evaluation_seed,
            checkpoint_sha256=self.checkpoint_sha256,
            environment_source_sha256=self.environment_source_sha256,
            reward_source_sha256=self.reward_source_sha256,
            anchor_payload=self._anchor_payload,
            anchor_sha256=self._anchor_sha256,
            pre_active_physical_ids=self._pre_active_physical_ids,
            main_actions=self._main_actions,
            main_physical_actions=self._main_physical_actions,
            action_bindings_by_user=self._bindings,
            forecast_fading_mode=self.forecast_fading_mode,
        )
        gate = chronology.PreoutcomeForecastGate(
            anchor_payload=anchor.anchor_payload,
            live_rng_state=self._live_rng_state,
        )
        return PreparedC2Fork(
            self,
            anchor,
            candidate_key,
            gate,
            source_rule,
        )

    def prepare_incumbent_hold(self, *, focal_user: int | None = None) -> PreparedC2Fork:
        if focal_user is None:
            focal_user = int(getattr(self, "_default_focal_user", 0))
        incumbent = _incumbent_key(self.wrapped, focal_user=focal_user)
        try:
            return self._prepare_physical_candidate(
                focal_user=focal_user,
                candidate_key=incumbent,
                source_rule="incumbent-hold",
            )
        except C2BackendError as error:
            raise C2ForecastSupportRejection(
                "opening_incumbent_unavailable",
                forecast_offset=0,
                user=focal_user,
                physical_key=incumbent,
                detail=str(error),
            ) from error

    def prepare_hold_or_max_lagged_gain_rival(
        self,
        *,
        focal_user: int | None = None,
    ) -> PreparedC2Fork:
        """Apply the sealed C2 source grammar without reading outcomes."""

        if focal_user is None:
            focal_user = int(getattr(self, "_default_focal_user", 0))
        incumbent = _incumbent_key(self.wrapped, focal_user=focal_user)
        opening_table = _slot_tables(self.observation, users=self._users)[focal_user]
        try:
            _action_for_physical(opening_table, incumbent)
            candidate_key = incumbent
            source_rule = "incumbent-hold"
        except C2BackendError:
            main_key = self._main_physical_actions[focal_user]
            if main_key is None:
                raise C2BackendError(
                    "C2 requires a physical detached-Main handover anchor"
                )
            candidate_key = _max_lagged_gain_rival(
                self.observation,
                focal_user=focal_user,
                main_key=main_key,
            )
            source_rule = "max-lagged-candidate-sinr-rival"
        return self._prepare_physical_candidate(
            focal_user=focal_user,
            candidate_key=candidate_key,
            source_rule=source_rule,
        )

    def prepare_one_candidate(
        self,
        *,
        focal_user: int,
        candidate_key: core.PhysicalKey,
    ) -> PreparedC2Fork:
        """Prepare an explicitly named physical candidate with same safeguards."""

        return self._prepare_physical_candidate(
            focal_user=focal_user,
            candidate_key=candidate_key,
            source_rule="explicit-preoutcome-candidate",
        )

    def _produce_forecast(
        self,
        anchor: C2OpeningAnchor,
        live_state: Mapping[str, Any],
        *,
        candidate_key: core.PhysicalKey,
        source_rule: str,
    ) -> tuple[
        forecast.AuthoritativeForecastBuild,
        Mapping[str, Any],
        tuple[forecast.ForecastStepPayload, ...],
        tuple[forecast.ForecastStepPayload, ...],
    ]:
        fading_field, fading_field_receipt = _derive_fading_field(anchor)
        rngs, initial_rng_receipt = _derive_forecast_rngs(
            anchor,
            fading_field_receipt=fading_field_receipt,
        )
        reference = _branch_from_anchor(
            anchor,
            role="reference",
            env_rng=rngs["reference_env"],
            mobility_rng=rngs["reference_mobility"],
            fading_field=fading_field,
        )
        candidate = _branch_from_anchor(
            anchor,
            role="candidate",
            env_rng=rngs["candidate_env"],
            mobility_rng=rngs["candidate_mobility"],
            fading_field=fading_field,
        )
        reference_trace: list[forecast.ForecastStepPayload] = []
        candidate_trace: list[forecast.ForecastStepPayload] = []
        candidate_support_counts: list[int] = []
        candidate_holding = True
        release_offset: int | None = None
        release_reason: str | None = None
        for offset in range(HOLD_STEPS + 1):
            ref_main, ref_main_physical = _main_actions(anchor.trainer, reference)
            ref_payload = _step_payload(
                reference,
                offset=offset,
                detached_main_actions=ref_main.tolist(),
                detached_main_physical=ref_main_physical,
                executed_actions=ref_main.tolist(),
            )
            reference_trace.append(ref_payload)

            cand_main, cand_main_physical = _main_actions(anchor.trainer, candidate)
            support_count = _candidate_support_count(
                candidate.observation,
                focal_user=anchor.focal_user,
                candidate_key=candidate_key,
            )
            candidate_support_counts.append(support_count)
            if candidate_holding:
                if offset == 0 and support_count != 1:
                    raise C2ForecastSupportRejection(
                        "opening_candidate_unavailable",
                        forecast_offset=offset,
                        user=anchor.focal_user,
                        physical_key=candidate_key,
                        detail=(
                            "opening candidate must be uniquely executable; "
                            f"observed match count={support_count}"
                        ),
                    )
                if offset > 0 and support_count != 1:
                    candidate_holding = False
                    release_offset = offset
                    release_reason = "support_expired"
                elif offset == HOLD_STEPS:
                    # No support expiry was observed in the downstream
                    # predecision tables; the planned horizon is the one-time
                    # release point.
                    candidate_holding = False
                    release_offset = offset
                    release_reason = "horizon"
            executed, _executed_physical = _compose_candidate_actions(
                observation=candidate.observation,
                main_actions=cand_main,
                main_physical=cand_main_physical,
                candidate_key=candidate_key,
                focal_user=anchor.focal_user,
                offset=offset,
                hold=candidate_holding,
            )
            cand_payload = _step_payload(
                candidate,
                offset=offset,
                detached_main_actions=cand_main.tolist(),
                detached_main_physical=cand_main_physical,
                executed_actions=executed.tolist(),
            )
            candidate_trace.append(cand_payload)
        if release_offset is None or release_reason is None:
            raise C2BackendError("C2 forecast did not produce a one-time release")
        candidate_trace = [
            replace(
                payload,
                held_physical_key=candidate_key,
                held_key_match_count=candidate_support_counts[payload.offset],
                release_offset=release_offset,
                release_reason=release_reason,
            )
            for payload in candidate_trace
        ]
        final_rng_receipt = _forecast_rng_receipt(initial_rng_receipt, (reference, candidate))
        source = forecast.ForecastSourcePayload(
            anchor_payload=anchor.anchor_payload,
            reference_checkpoint_sha256=anchor.checkpoint_sha256,
            environment_source_sha256=anchor.environment_source_sha256,
            reward_source_sha256=anchor.reward_source_sha256,
            # Bind the authority to the exact pre-forecast snapshot supplied
            # by PreoutcomeForecastGate, not to a later re-read of live state.
            live_rng_state=copy.deepcopy(dict(live_state)),
            forecast_rng_state=final_rng_receipt,
            forecast_namespace=FORECAST_NAMESPACE,
            adapter_version="c2_temporal_fork_trainer_backend-v2",
            fading_mode=anchor.forecast_fading_mode,
            fading_field_receipt=fading_field_receipt,
            source_rule=source_rule,
        )
        build = forecast.build_authoritative_forecast(
            source,
            focal_user=anchor.focal_user,
            user_count=self._users,
            pre_active_physical_ids=anchor.pre_active_physical_ids,
            reference_trace=reference_trace,
            candidate_trace=candidate_trace,
        )
        return build, final_rng_receipt, tuple(reference_trace), tuple(candidate_trace)


# A descriptive alias keeps callers that use the older C3 naming convention
# from accidentally importing the legacy C3 semantics.
TrainerEnvironmentC2V03Backend = C2TemporalForkTrainerBackend


__all__ = [
    "CLAIM_CEILING",
    "C2BackendError",
    "C2ForecastSupportRejection",
    "C2ForecastBranch",
    "C2LiveStep",
    "C2OpeningAnchor",
    "C2TemporalForkTrainerBackend",
    "PreparedC2Fork",
    "TrainerEnvironmentC2V03Backend",
]
