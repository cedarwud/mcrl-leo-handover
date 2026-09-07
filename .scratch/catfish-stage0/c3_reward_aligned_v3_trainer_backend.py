"""Real ``TrainerEnvironment`` bridge for the C3 V3 shadow seam.

The backend in this module is deliberately development-only.  It takes a
live pre-outcome ``TrainerEnvironment`` anchor, makes two fresh branches by
copying only mutable episode state (the immutable TLE archive is shared), and
advances the branches through the generic C3 V3 candidate-support runner.

There is no learner, replay-buffer write, routing, seed census, outcome
selection, or training here.  Fading is disabled only on the detached
pre-outcome branches.  The caller's live environment, states, masks,
observation, and RNG are not advanced.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, is_dataclass, replace
import hashlib
import math
from numbers import Real
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

import c3_reward_aligned_v3_runtime_adapter as adapter  # noqa: E402
import c3_reward_aligned_v3_shadow_runner as shadow  # noqa: E402
import run_c3_stage0 as legacy  # noqa: E402
from mcrl.env.action_contract import Association, HandoverClass, NO_OP_ACTION  # noqa: E402


EXPECTED_OBJECTIVE_WEIGHTS = (0.5, 0.3, 0.2)
HOLD_OFFSETS = tuple(range(shadow.core.HOLD_STEPS))
RELEASE_OFFSET = shadow.core.FIRST_RELEASE_OFFSET
SCAN_SCHEMA = "smc-er-c3-v3-trainer-environment-support-scan-v1"
# These namespaces are intentionally not shared with the live episode or
# with one another.  The forecast stream is an evaluation artefact, not a
# continuation of the generator that will eventually drive the episode.
FORECAST_ENV_NAMESPACE = "SMC-ER-C3-V3-FORECAST-ENV-v1"
FORECAST_MOBILITY_NAMESPACE = "SMC-ER-C3-V3-FORECAST-MOBILITY-v1"
SCAN_CLAIM_CEILING = (
    "development-only capped pre-outcome support; no formal seed result, "
    "scientific efficacy, Main routing, deployment, or training authorization"
)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _rng_state_sha256(rng: np.random.Generator) -> str:
    if not isinstance(rng, np.random.Generator):
        raise ValueError("environment RNG must be a numpy Generator")
    return hashlib.sha256(
        legacy.canonical_json(rng.bit_generator.state)
    ).hexdigest()


def derive_forecast_rng(
    namespace: str,
    *,
    checkpoint_sha256: str,
    anchor_fingerprint_sha256: str,
    focal_user_id: int,
    step_index: int,
    evaluation_seed: int,
) -> np.random.Generator:
    """Derive one deterministic, domain-separated C3 V3 forecast stream.

    The stream is derived directly from immutable authority and anchor
    identity.  In particular, it never calls ``spawn`` or consumes the live
    episode generator, so a shadow scan cannot change the eventual episode.
    ``namespace`` is part of the digest input: environment/fading and user
    mobility therefore remain separate even when all other inputs match.
    """

    if namespace not in {
        FORECAST_ENV_NAMESPACE,
        FORECAST_MOBILITY_NAMESPACE,
    }:
        raise ValueError(f"unknown C3 V3 forecast RNG namespace: {namespace}")
    if not _is_sha256(checkpoint_sha256):
        raise ValueError("checkpoint authority must be a lowercase SHA-256 digest")
    if not _is_sha256(anchor_fingerprint_sha256):
        raise ValueError("anchor fingerprint must be a lowercase SHA-256 digest")
    for value, field_name in (
        (focal_user_id, "focal user ID"),
        (step_index, "step index"),
        (evaluation_seed, "evaluation seed"),
    ):
        if type(value) is not int or value < 0:
            raise ValueError(f"{field_name} must be a nonnegative exact integer")
    payload = legacy.canonical_json(
        [
            namespace,
            checkpoint_sha256,
            anchor_fingerprint_sha256,
            int(focal_user_id),
            int(step_index),
            int(evaluation_seed),
        ]
    )
    seed_integer = int.from_bytes(hashlib.sha256(payload).digest()[:16], "big")
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed_integer)))


def _forecast_rng_pair(
    *,
    checkpoint_sha256: str,
    anchor_fingerprint_sha256: str,
    focal_user_id: int,
    step_index: int,
    evaluation_seed: int,
) -> tuple[np.random.Generator, np.random.Generator]:
    """Return independent environment and mobility forecast generators."""

    return (
        derive_forecast_rng(
            FORECAST_ENV_NAMESPACE,
            checkpoint_sha256=checkpoint_sha256,
            anchor_fingerprint_sha256=anchor_fingerprint_sha256,
            focal_user_id=focal_user_id,
            step_index=step_index,
            evaluation_seed=evaluation_seed,
        ),
        derive_forecast_rng(
            FORECAST_MOBILITY_NAMESPACE,
            checkpoint_sha256=checkpoint_sha256,
            anchor_fingerprint_sha256=anchor_fingerprint_sha256,
            focal_user_id=focal_user_id,
            step_index=step_index,
            evaluation_seed=evaluation_seed,
        ),
    )


def live_anchor_fingerprint(
    wrapped: Any,
    *,
    env_rng: np.random.Generator,
    states: Sequence[Any],
    masks: Sequence[Any],
    observation: Any,
    checkpoint_sha256: str,
) -> str:
    """Hash only mutable anchor state; immutable TLE storage is not copied."""

    if not _is_sha256(checkpoint_sha256):
        raise ValueError("checkpoint authority must be a lowercase SHA-256 digest")
    if not hasattr(wrapped, "environment") or not hasattr(observation, "step_index"):
        raise ValueError("live anchor lacks TrainerEnvironment/observation seams")
    receipt = {
        "checkpoint_sha256": checkpoint_sha256,
        "epoch": (
            None
            if getattr(wrapped, "_epoch", None) is None
            else wrapped.epoch.isoformat()
        ),
        "step_index": int(observation.step_index),
        "wrapped_mutable_state": legacy._wrapped_mutable_state_receipt(wrapped),
        "environment_rng_sha256": _rng_state_sha256(env_rng),
        # ``states`` may contain dataclass-backed UserState objects; use the
        # existing pickle/object receipt instead of assuming JSON scalars.
        "states_sha256": legacy._object_sha(states),
        "masks_sha256": legacy._object_sha(masks),
        "observation_state_sha256": legacy._object_sha(observation.state_matrix),
        "observation_mask_sha256": legacy._object_sha(observation.masks),
        "candidate_tables_sha256": legacy._object_sha(
            observation.candidates.slot_tables
        ),
    }
    return legacy.state_sha256(receipt)


def _copy_driver_without_archive(driver: Any) -> Any:
    """Shallow-copy the driver and deep-copy only episode-mutated fields."""

    clone = copy.copy(driver)
    # ``archive``, ``config``, ``grid`` and the immutable SatelliteSet are
    # deliberately shared.  Copying the archive is the expensive mistake this
    # backend is designed to avoid.
    for field in ("_users", "_dwell", "_tracker"):
        setattr(clone, field, copy.deepcopy(getattr(driver, field)))
    frozen_window = getattr(driver, "_frozen_window_norad_ids", None)
    setattr(
        clone,
        "_frozen_window_norad_ids",
        None if frozen_window is None else np.array(frozen_window, copy=True),
    )
    return clone


def _copy_trainer_environment(wrapped: Any) -> Any:
    """Create an independent episode branch while sharing immutable TLE data."""

    if not hasattr(wrapped, "environment"):
        raise ValueError("wrapped object is not a TrainerEnvironment")
    source_environment = wrapped.environment
    clone = copy.copy(wrapped)
    environment = copy.copy(source_environment)
    environment.driver = _copy_driver_without_archive(source_environment.driver)

    mutable_fields = (
        "_ledgers",
        "_segments",
        "_previous_radiating",
        "_previous_demand",
        "_previous_association",
        "_candidates",
        "_mobility_rng",
        "_pending_segment_age",
        "_age_rng",
    )
    for field in mutable_fields:
        setattr(environment, field, copy.deepcopy(getattr(source_environment, field)))
    if is_dataclass(source_environment.physics):
        environment.physics = replace(source_environment.physics, fading_enabled=False)
    else:
        physics = copy.copy(source_environment.physics)
        physics.fading_enabled = False
        environment.physics = physics

    clone.environment = environment
    # The sampler holds the immutable archive and frozen start policy; share
    # it instead of recursively copying the TLE catalogue.
    clone.sampler = wrapped.sampler
    clone._epoch = getattr(wrapped, "_epoch", None)
    clone._last_outcome = copy.deepcopy(getattr(wrapped, "_last_outcome", None))
    return clone


@dataclass
class TrainerC3V3Branch:
    """Mutable branch containing only detached episode state."""

    wrapped: Any
    env_rng: np.random.Generator
    states: list[Any]
    masks: list[Any]
    observation: Any
    trainer: Any
    focal_user_id: int
    anchor_fingerprint_sha256: str
    next_offset: int = 0
    # ``checkpoint_sha256`` and the derivation fingerprint are carried on the
    # branch so a fingerprint call is self-contained and cannot silently
    # consult a stale backend claim.  Defaults preserve the small fixture
    # construction API used by the focused tests.
    checkpoint_sha256: str = ""
    derivation_anchor_fingerprint_sha256: str | None = None
    evaluation_seed: int = 0


def _physical_id_for_action(table: Any, action: int) -> shadow.core.PhysicalAction:
    if int(action) == NO_OP_ACTION:
        return None
    association = table.association(int(action))
    if not isinstance(association, Association):
        return None
    return int(association.norad_id), int(association.cell_id)


def _action_for_physical_id(table: Any, physical_id: shadow.core.PhysicalId) -> int | None:
    target = shadow.core.validate_physical_id(physical_id, field="physical candidate ID")
    valid = np.flatnonzero(np.asarray(table.mask, dtype=bool)).tolist()
    matches = [
        int(action)
        for action in valid
        if int(table.norad_ids[action]) == target[0]
        and int(table.cell_ids[action]) == target[1]
    ]
    if len(matches) > 1:
        raise RuntimeError(f"duplicate physical candidate ID {target}")
    return matches[0] if matches else None


def _unique_valid_physical_ids(table: Any) -> tuple[shadow.core.PhysicalId, ...]:
    found: dict[shadow.core.PhysicalId, int] = {}
    for action in np.flatnonzero(np.asarray(table.mask, dtype=bool)).tolist():
        physical_id = _physical_id_for_action(table, int(action))
        if physical_id is None:
            continue
        if physical_id in found:
            raise RuntimeError(f"duplicate physical candidate ID {physical_id}")
        found[physical_id] = int(action)
    return tuple(sorted(found))


def _served_physical_id(outcome: Any, user: int) -> shadow.core.PhysicalAction:
    if not bool(outcome.resolution.served[user]):
        return None
    return shadow.core.validate_physical_id(
        (
            int(outcome.resolution.serving_satellite[user]),
            int(outcome.resolution.serving_cell[user]),
        ),
        field="realised focal physical ID",
    )


def _event_class(value: HandoverClass) -> shadow.core.EventClass:
    if value is HandoverClass.NONE:
        return shadow.core.EventClass.NONE
    if value is HandoverClass.INTRA_SATELLITE:
        return shadow.core.EventClass.INTRA_SATELLITE
    if value is HandoverClass.INTER_SATELLITE:
        return shadow.core.EventClass.INTER_SATELLITE
    raise RuntimeError(f"unknown canonical handover class {value!r}")


def _preview_matches(preview: Any, outcome: Any) -> bool:
    """Compare all canonical fields consumed by the C3 certificate."""

    return bool(
        np.array_equal(preview.reward_matrix, outcome.reward_matrix)
        and np.array_equal(preview.resolution.served, outcome.resolution.served)
        and np.array_equal(
            preview.resolution.serving_satellite,
            outcome.resolution.serving_satellite,
        )
        and np.array_equal(preview.resolution.serving_cell, outcome.resolution.serving_cell)
        and np.array_equal(preview.link_power_w, outcome.link_power_w)
        and np.array_equal(preview.link_rate_bps, outcome.link_rate_bps)
        and preview.resolution.active_beams == outcome.resolution.active_beams
        and preview.resolution.eligible_load_by_beam
        == outcome.resolution.eligible_load_by_beam
        and preview.handovers == outcome.handovers
        and float(preview.system_power_w) == float(outcome.system_power_w)
        and float(preview.fixed_power_w) == float(outcome.fixed_power_w)
        and np.array_equal(preview.radiating.norad_ids, outcome.radiating.norad_ids)
        and np.array_equal(preview.radiating.cell_ids, outcome.radiating.cell_ids)
        and np.array_equal(preview.radiating.power_w, outcome.radiating.power_w)
    )


def _power_projection_evaluation(evaluation: Any) -> Any:
    """Expose consumed link power under the canonical adapter contract.

    The current ``StepEnvironment`` carries the required recurrence output in
    ``link_power_w`` even when service resolution subsequently marks a user
    unserved.  That value is not a consumed beam term (and is excluded by the
    canonical beam aggregation), while the C3 power adapter intentionally
    requires zero for unserved users.  Keep the real outcome untouched and
    provide the adapter a value-equivalent, immutable view with only those
    non-consumed entries zeroed.  Served rows, radiating beams, and complete
    power totals remain byte-for-byte canonical.
    """

    try:
        served = np.asarray(evaluation.resolution.served)
        link_power = np.asarray(evaluation.link_power_w)
    except AttributeError:
        return evaluation
    if served.ndim != 1 or served.dtype != np.bool_ or link_power.shape != served.shape:
        return evaluation
    if not np.any(~served & (link_power != 0.0)):
        return evaluation
    return replace(
        evaluation,
        link_power_w=np.where(served, link_power, 0.0),
    )


def _was_unserved(branch: TrainerC3V3Branch, user: int) -> bool:
    previous = branch.wrapped.environment._ledgers[user].previous
    return previous is not None and not isinstance(previous, Association)


def _main_decision(branch: TrainerC3V3Branch) -> adapter.ScalarizedMainDecision:
    return adapter.scalarized_main_decision(
        branch.trainer,
        branch.states,
        branch.masks,
        slot_tables=branch.observation.candidates.slot_tables,
    )


def _main_nonfocal_actions(
    decision: adapter.ScalarizedMainDecision, *, focal_user_id: int, user_count: int
) -> dict[int, shadow.core.PhysicalAction]:
    """Copy the branch-local Main physical proposal for diagnostics."""

    if decision.physical_actions is None:
        raise RuntimeError("C3 V3 Main decision has no physical action receipt")
    physical_actions = tuple(decision.physical_actions)
    if len(physical_actions) != user_count:
        raise RuntimeError("C3 V3 Main physical action receipt has the wrong user count")
    for physical_id in physical_actions:
        if physical_id is not None:
            shadow.core.validate_physical_id(
                physical_id, field="branch-local Main physical action"
            )
    return {
        user: physical_actions[user]
        for user in range(user_count)
        if user != focal_user_id
    }


def _action_for_reference_physical_id(
    table: Any, physical_id: shadow.core.PhysicalAction
) -> int:
    """Map one reference physical action onto a current branch table.

    ``None`` is the physical no-op identity.  It is executable only when the
    candidate's current mask has no valid action; silently choosing another
    action would invalidate the common-random, common-script comparison.
    """

    if physical_id is None:
        valid_count = int(np.count_nonzero(np.asarray(table.mask, dtype=bool)))
        if valid_count:
            raise RuntimeError(
                "reference nonfocal no-op is not remappable under candidate mask"
            )
        return int(NO_OP_ACTION)
    target = shadow.core.validate_physical_id(
        physical_id, field="reference nonfocal physical ID"
    )
    action = _action_for_physical_id(table, target)
    if action is None:
        raise RuntimeError(
            "reference nonfocal physical ID disappeared from current candidate table: "
            f"{target}"
        )
    return int(action)


def _actions_with_reference_nonfocal_script(
    branch: TrainerC3V3Branch,
    decision: adapter.ScalarizedMainDecision,
    *,
    reference_nonfocal_actions: Mapping[int, shadow.core.PhysicalAction] | None,
) -> tuple[np.ndarray, dict[int, shadow.core.PhysicalAction]]:
    """Build actions from local Main, replacing non-focal users by a script.

    The returned diagnostic map is always the branch-local Main proposal.  The
    returned action vector is what is actually sent to ``evaluate_actions`` and
    ``step``; the backend therefore cannot record a requested script while
    executing a different local action by accident.
    """

    actions = np.asarray(decision.actions, dtype=np.int32).copy()
    user_count = len(branch.states)
    if actions.shape != (user_count,):
        raise RuntimeError("C3 V3 Main action receipt has the wrong user count")
    local_nonfocal_actions = _main_nonfocal_actions(
        decision, focal_user_id=branch.focal_user_id, user_count=user_count
    )
    if reference_nonfocal_actions is None:
        return actions, local_nonfocal_actions
    if not isinstance(reference_nonfocal_actions, Mapping):
        raise RuntimeError("reference nonfocal script must be a mapping")
    expected_users = set(local_nonfocal_actions)
    if set(reference_nonfocal_actions) != expected_users or any(
        type(user) is not int for user in reference_nonfocal_actions
    ):
        raise RuntimeError(
            "reference nonfocal script must cover every non-focal user exactly"
        )
    tables = branch.observation.candidates.slot_tables
    if len(tables) != user_count:
        raise RuntimeError("candidate slot tables have the wrong user count")
    for user in sorted(expected_users):
        actions[user] = _action_for_reference_physical_id(
            tables[user], reference_nonfocal_actions[user]
        )
    return actions, local_nonfocal_actions


def _advance(
    branch: TrainerC3V3Branch,
    *,
    actions: np.ndarray,
    main_focal_action: shadow.core.PhysicalAction | None,
    offset: int,
    branch_main_nonfocal_actions: Mapping[int, shadow.core.PhysicalAction],
) -> shadow.ShadowStep:
    if branch.next_offset != offset:
        raise RuntimeError(
            f"C3 V3 branch expected offset {branch.next_offset}, got {offset}"
        )
    if branch.wrapped.environment.physics.fading_enabled:
        raise RuntimeError("C3 V3 shadow branch must keep fading disabled")
    physical_actions = adapter.physical_action_keys(
        np.asarray(actions, dtype=np.int32),
        branch.observation.candidates.slot_tables,
    )
    reentry_before = tuple(
        _was_unserved(branch, user) for user in range(len(branch.states))
    )
    preview = branch.wrapped.environment.evaluate_actions(actions, branch.env_rng)
    result = branch.wrapped.step(actions, branch.env_rng)
    outcome = branch.wrapped.last_outcome
    if offset < RELEASE_OFFSET and bool(result.done):
        raise RuntimeError("C3 V3 branch reached terminal before release offset")
    if not _preview_matches(preview, outcome):
        raise RuntimeError("C3 V3 preview/commit parity failed")
    served = tuple(bool(value) for value in outcome.resolution.served)
    reentry = tuple(
        before and current for before, current in zip(reentry_before, served, strict=True)
    )
    events = tuple(_event_class(value) for value in outcome.handovers)
    branch.states = list(result.user_states)
    branch.masks = list(result.action_masks)
    branch.observation = outcome.observation
    branch.next_offset += 1
    return shadow.ShadowStep(
        evaluation=_power_projection_evaluation(outcome),
        focal_action=_served_physical_id(outcome, branch.focal_user_id),
        nonfocal_actions={
            user: physical_id
            for user, physical_id in enumerate(physical_actions)
            if user != branch.focal_user_id
        },
        useful_bits=(
            float(np.asarray(outcome.link_rate_bps, dtype=np.float64).sum())
            * shadow.core.DECISION_INTERVAL_S
        ),
        reentry=reentry,
        events=events,
        preview_commit_equal=True,
        scalarized_main_action=main_focal_action,
        branch_main_nonfocal_actions=dict(branch_main_nonfocal_actions),
    )


class TrainerEnvironmentC3V3Backend:
    """Canonical backend implementing the generic C3 V3 shadow protocol."""

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
        anchor_fingerprint_sha256: str,
        focal_user_id: int,
        derivation_anchor_fingerprint_sha256: str | None = None,
    ) -> None:
        if not _is_sha256(checkpoint_sha256):
            raise ValueError("checkpoint authority must be a lowercase SHA-256 digest")
        if not _is_sha256(anchor_fingerprint_sha256):
            raise ValueError("anchor fingerprint must be a lowercase SHA-256 digest")
        if not hasattr(wrapped, "environment"):
            raise ValueError("wrapped object is not a TrainerEnvironment")
        if not isinstance(env_rng, np.random.Generator):
            raise ValueError("environment RNG must be a numpy Generator")
        if type(focal_user_id) is not int or not 0 <= focal_user_id < len(states):
            raise ValueError("focal user ID is outside the live state range")
        configured = tuple(float(value) for value in trainer.config.objective_weights)
        if configured != EXPECTED_OBJECTIVE_WEIGHTS:
            raise ValueError(
                "trainer objective weights drifted from (0.5,0.3,0.2): "
                f"{configured!r}"
            )
        if len(states) != len(masks) or len(states) != int(observation.num_users):
            raise ValueError("live states, masks, and observation disagree on user count")
        self.wrapped = wrapped
        self.states = list(states)
        self.masks = list(masks)
        self.observation = observation
        self.env_rng = env_rng
        self.trainer = trainer
        self.checkpoint_sha256 = checkpoint_sha256
        self.anchor_fingerprint_sha256 = anchor_fingerprint_sha256
        if derivation_anchor_fingerprint_sha256 is None:
            derivation_anchor_fingerprint_sha256 = anchor_fingerprint_sha256
        if not _is_sha256(derivation_anchor_fingerprint_sha256):
            raise ValueError(
                "forecast derivation anchor fingerprint must be a lowercase "
                "SHA-256 digest"
            )
        self.derivation_anchor_fingerprint_sha256 = (
            derivation_anchor_fingerprint_sha256
        )
        self.focal_user_id = focal_user_id

    def replay_prefix(self, anchor: shadow.C3V3ShadowAnchor) -> TrainerC3V3Branch:
        if type(anchor) is not shadow.C3V3ShadowAnchor:
            raise ValueError("backend received a foreign C3 V3 anchor")
        if anchor.checkpoint_sha256 != self.checkpoint_sha256:
            raise RuntimeError("C3 V3 anchor checkpoint authority drifted")
        if anchor.expected_anchor_fingerprint_sha256 != self.anchor_fingerprint_sha256:
            raise RuntimeError("C3 V3 anchor fingerprint authority drifted")
        if anchor.focal_user_id != self.focal_user_id:
            raise RuntimeError("C3 V3 anchor focal user drifted")
        if anchor.step_index != int(self.observation.step_index):
            raise RuntimeError("C3 V3 anchor step differs from live observation")
        # This bridge receives a materialized live anchor.  It deliberately
        # does not pretend that a caller-supplied action prefix was replayed;
        # a future fresh-init+prefix implementation must be a separate,
        # explicitly verified backend.
        if anchor.prefix_actions:
            raise RuntimeError(
                "live TrainerEnvironment backend accepts only an empty prefix"
            )
        if anchor.source_id != self._source_id:
            raise RuntimeError("C3 V3 anchor source differs from backend source")
        branch_wrapped = _copy_trainer_environment(self.wrapped)
        branch_states = copy.deepcopy(self.states)
        branch_masks = copy.deepcopy(self.masks)
        branch_observation = copy.deepcopy(self.observation)
        # Forecast streams are deterministic domain-separated children of the
        # live anchor authority.  They are created from immutable digest
        # inputs, never by spawning/advancing the eventual live RNG.  Each
        # replay call gets new objects with equal states, which gives the
        # reference/candidate twins common random numbers without aliasing.
        branch_rng, branch_mobility_rng = _forecast_rng_pair(
            checkpoint_sha256=self.checkpoint_sha256,
            anchor_fingerprint_sha256=self.derivation_anchor_fingerprint_sha256,
            focal_user_id=anchor.focal_user_id,
            step_index=anchor.step_index,
            evaluation_seed=anchor.evaluation_seed,
        )
        branch_wrapped.environment._mobility_rng = branch_mobility_rng
        return TrainerC3V3Branch(
            wrapped=branch_wrapped,
            env_rng=branch_rng,
            states=branch_states,
            masks=branch_masks,
            observation=branch_observation,
            trainer=self.trainer,
            focal_user_id=self.focal_user_id,
            anchor_fingerprint_sha256=self.anchor_fingerprint_sha256,
            checkpoint_sha256=self.checkpoint_sha256,
            derivation_anchor_fingerprint_sha256=(
                self.derivation_anchor_fingerprint_sha256
            ),
            evaluation_seed=anchor.evaluation_seed,
        )

    @property
    def _source_id(self) -> shadow.core.PhysicalId:
        try:
            return self._source_id_value
        except AttributeError as exc:
            raise RuntimeError("backend source physical ID was not bound") from exc

    @property
    def source_id(self) -> shadow.core.PhysicalId:
        return self._source_id

    @source_id.setter
    def source_id(self, value: shadow.core.PhysicalId) -> None:
        self._source_id_value = shadow.core.validate_physical_id(value)

    def fingerprint(self, branch: TrainerC3V3Branch) -> str:
        if type(branch) is not TrainerC3V3Branch:
            raise ValueError("C3 V3 backend received a foreign branch")
        if branch.wrapped is self.wrapped or branch.env_rng is self.env_rng:
            raise RuntimeError("C3 V3 branch aliases the live anchor")
        if branch.wrapped.environment is self.wrapped.environment:
            raise RuntimeError("C3 V3 branch shares mutable environment state")
        checkpoint_sha256 = branch.checkpoint_sha256 or self.checkpoint_sha256
        if checkpoint_sha256 != self.checkpoint_sha256:
            raise RuntimeError("C3 V3 branch checkpoint authority drifted")
        # Never return the branch's cached authority.  Recompute the digest
        # from the branch's actual mutable state, state/mask lists,
        # observation, and forecast environment RNG.  The generic runner then
        # compares this receipt against the anchor authority and against the
        # other fresh twin.
        return live_anchor_fingerprint(
            branch.wrapped,
            env_rng=branch.env_rng,
            states=branch.states,
            masks=branch.masks,
            observation=branch.observation,
            checkpoint_sha256=checkpoint_sha256,
        )

    def scalarized_main_decision(
        self, branch: TrainerC3V3Branch
    ) -> adapter.ScalarizedMainDecision:
        if type(branch) is not TrainerC3V3Branch:
            raise ValueError("C3 V3 backend received a foreign branch")
        return _main_decision(branch)

    def anchor_evaluation(
        self,
        branch: TrainerC3V3Branch,
        decision: adapter.ScalarizedMainDecision,
    ) -> Any:
        if decision.physical_actions is None:
            raise RuntimeError("C3 V3 Main anchor has no physical action receipt")
        environment = branch.wrapped.environment
        if environment.physics.fading_enabled:
            raise RuntimeError("C3 V3 anchor evaluation requires fading disabled")
        evaluation = environment.evaluate_actions(
            np.asarray(decision.actions, dtype=np.int32), branch.env_rng
        )
        return _power_projection_evaluation(evaluation)

    def force_focal(
        self,
        branch: TrainerC3V3Branch,
        focal_physical_id: shadow.core.PhysicalId,
        offset: int,
        *,
        reference_nonfocal_actions: Mapping[int, shadow.core.PhysicalAction] | None = None,
    ) -> shadow.ShadowStep:
        if offset not in HOLD_OFFSETS:
            raise ValueError("C3 V3 force_focal only accepts hold offsets 0,1,2")
        focal_id = shadow.core.validate_physical_id(
            focal_physical_id, field="forced focal physical ID"
        )
        decision = _main_decision(branch)
        actions, branch_main_nonfocal_actions = _actions_with_reference_nonfocal_script(
            branch,
            decision,
            reference_nonfocal_actions=reference_nonfocal_actions,
        )
        table = branch.observation.candidates.slot_tables[branch.focal_user_id]
        action = _action_for_physical_id(table, focal_id)
        if action is None:
            raise RuntimeError("forced focal physical ID disappeared from current table")
        actions[branch.focal_user_id] = int(action)
        return _advance(
            branch,
            actions=actions,
            main_focal_action=None,
            offset=offset,
            branch_main_nonfocal_actions=branch_main_nonfocal_actions,
        )

    def release_to_main(
        self,
        branch: TrainerC3V3Branch,
        offset: int,
        *,
        reference_nonfocal_actions: Mapping[int, shadow.core.PhysicalAction] | None = None,
    ) -> shadow.ShadowStep:
        if offset != RELEASE_OFFSET:
            raise ValueError("C3 V3 release must occur at offset 3")
        decision = _main_decision(branch)
        if decision.physical_actions is None:
            raise RuntimeError("C3 V3 release Main action has no physical receipt")
        actions, branch_main_nonfocal_actions = _actions_with_reference_nonfocal_script(
            branch,
            decision,
            reference_nonfocal_actions=reference_nonfocal_actions,
        )
        return _advance(
            branch,
            actions=actions,
            main_focal_action=decision.physical_actions[branch.focal_user_id],
            offset=offset,
            branch_main_nonfocal_actions=branch_main_nonfocal_actions,
        )


@dataclass(frozen=True)
class TrainerC3V3SupportScan:
    """Capped scan output, including raw receipts and gated exposed support."""

    schema: str
    status: str
    step_index: int
    steps_remaining: int
    scanned_focal_users: tuple[int, ...]
    scanned_candidates: int
    support_physical_ids_by_focal: Mapping[int, tuple[shadow.core.PhysicalId, ...]]
    support_action_indices_by_focal: Mapping[int, Mapping[shadow.core.PhysicalId, int]]
    receipts_by_focal: Mapping[int, tuple[shadow.C3V3ShadowReceipt, ...]]
    reasons: tuple[str, ...]
    candidate_wall_seconds_by_focal: Mapping[int, tuple[float, ...]] = field(
        default_factory=dict
    )
    claim_ceiling: str = SCAN_CLAIM_CEILING

    @property
    def support_ids_by_user(self) -> Mapping[int, tuple[shadow.core.PhysicalId, ...]]:
        """Alias matching the existing developmental support APIs."""

        return self.support_physical_ids_by_focal

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "step_index": self.step_index,
            "steps_remaining": self.steps_remaining,
            "scanned_focal_users": list(self.scanned_focal_users),
            "scanned_candidates": self.scanned_candidates,
            "support_physical_ids_by_focal": {
                str(user): [list(value) for value in ids]
                for user, ids in self.support_physical_ids_by_focal.items()
            },
            "support_action_indices_by_focal": {
                str(user): {
                    str(list(physical_id)): int(action)
                    for physical_id, action in actions.items()
                }
                for user, actions in self.support_action_indices_by_focal.items()
            },
            "receipts_by_focal": {
                str(user): [receipt.to_dict() for receipt in receipts]
                for user, receipts in self.receipts_by_focal.items()
            },
            "candidate_wall_seconds_by_focal": {
                str(user): [float(value) for value in values]
                for user, values in self.candidate_wall_seconds_by_focal.items()
            },
            "reasons": list(self.reasons),
            "claim_ceiling": self.claim_ceiling,
        }


def _failure_scan(
    *,
    status: str,
    step_index: int,
    steps_remaining: int,
    reasons: Sequence[str],
) -> TrainerC3V3SupportScan:
    return TrainerC3V3SupportScan(
        schema=SCAN_SCHEMA,
        status=status,
        step_index=step_index,
        steps_remaining=steps_remaining,
        scanned_focal_users=(),
        scanned_candidates=0,
        support_physical_ids_by_focal={},
        support_action_indices_by_focal={},
        receipts_by_focal={},
        reasons=tuple(dict.fromkeys(str(reason) for reason in reasons)),
    )


def _forecast_anchor_fingerprint(
    *,
    wrapped: Any,
    states: Sequence[Any],
    masks: Sequence[Any],
    observation: Any,
    checkpoint_sha256: str,
    derivation_anchor_fingerprint_sha256: str,
    focal_user_id: int,
    step_index: int,
    evaluation_seed: int,
) -> str:
    """Materialize the expected digest for a deterministic forecast twin.

    The live digest is the derivation authority.  Forecast RNGs are not a
    continuation of the live streams, so the generic runner's expected
    branch digest must be computed over the same detached forecast state that
    :meth:`TrainerEnvironmentC3V3Backend.replay_prefix` will construct.
    This helper only copies state and hashes it; it never advances the live
    environment or either live generator.
    """

    forecast_env_rng, forecast_mobility_rng = _forecast_rng_pair(
        checkpoint_sha256=checkpoint_sha256,
        anchor_fingerprint_sha256=derivation_anchor_fingerprint_sha256,
        focal_user_id=focal_user_id,
        step_index=step_index,
        evaluation_seed=evaluation_seed,
    )
    forecast_wrapped = _copy_trainer_environment(wrapped)
    forecast_wrapped.environment._mobility_rng = forecast_mobility_rng
    return live_anchor_fingerprint(
        forecast_wrapped,
        env_rng=forecast_env_rng,
        states=copy.deepcopy(states),
        masks=copy.deepcopy(masks),
        observation=copy.deepcopy(observation),
        checkpoint_sha256=checkpoint_sha256,
    )


def scan_current_support(
    *,
    wrapped: Any,
    states: Sequence[Any],
    masks: Sequence[Any],
    observation: Any,
    env_rng: np.random.Generator,
    trainer: Any,
    checkpoint_sha256: str,
    steps_remaining: int,
    max_focal_users: int = 1,
    max_candidates_per_focal: int = 2,
    scheduled_anchor: bool = True,
    evaluation_seed: int = 0,
) -> TrainerC3V3SupportScan:
    """Scan current-table C3 V3 support without touching the live trajectory.

    Only candidates with an already-active same-satellite destination and the
    exact current eligible-load gap are sent to the four-offset twin
    certificate.  ``support_*_by_focal`` remains empty unless at least two
    candidates certify for that focal user; this prevents one-choice support
    from being exposed as learned support.
    """

    try:
        if type(steps_remaining) is not int or steps_remaining < 0:
            raise ValueError("steps_remaining must be a nonnegative exact integer")
        if type(max_focal_users) is not int or max_focal_users < 1:
            raise ValueError("max_focal_users must be a positive exact integer")
        if type(max_candidates_per_focal) is not int or max_candidates_per_focal < 1:
            raise ValueError("max_candidates_per_focal must be a positive exact integer")
        if type(scheduled_anchor) is not bool:
            raise ValueError("scheduled_anchor must be an exact boolean")
        if type(evaluation_seed) is not int or evaluation_seed < 0:
            raise ValueError("evaluation_seed must be a nonnegative exact integer")
        if not isinstance(env_rng, np.random.Generator):
            raise ValueError("environment RNG must be a numpy Generator")
        user_count = len(states)
        if user_count < 1 or len(masks) != user_count:
            raise ValueError("live states and masks must share a nonempty user count")
        if int(observation.num_users) != user_count:
            raise ValueError("live observation user count disagrees with states")
        step_index = int(observation.step_index)
        if steps_remaining < shadow.core.CERTIFICATE_STEPS:
            return _failure_scan(
                status="INSUFFICIENT_HORIZON",
                step_index=step_index,
                steps_remaining=steps_remaining,
                reasons=("fewer_than_four_steps_remaining_for_hold_and_release",),
            )
        if not _is_sha256(checkpoint_sha256):
            raise ValueError("checkpoint authority must be a lowercase SHA-256 digest")

        main = adapter.scalarized_main_decision(
            trainer,
            states,
            masks,
            slot_tables=observation.candidates.slot_tables,
        )
        if main.physical_actions is None:
            raise RuntimeError("scalarized Main did not return physical action IDs")
        live_fingerprint = live_anchor_fingerprint(
            wrapped,
            env_rng=env_rng,
            states=states,
            masks=masks,
            observation=observation,
            checkpoint_sha256=checkpoint_sha256,
        )
        source_environment = wrapped.environment
        original_physics = source_environment.physics
        if is_dataclass(original_physics):
            source_environment.physics = replace(original_physics, fading_enabled=False)
        else:
            source_environment.physics = copy.copy(original_physics)
            source_environment.physics.fading_enabled = False
        try:
            baseline = source_environment.evaluate_actions(
                np.asarray(main.actions, dtype=np.int32), env_rng
            )
        finally:
            source_environment.physics = original_physics
        baseline_load = adapter.canonical_load_projection(baseline)
        adapter.canonical_power_projection(_power_projection_evaluation(baseline))
        associations = baseline_load.snapshot.served_associations
        active = set(baseline_load.snapshot.reported_active_beams)
        loads = dict(baseline_load.snapshot.reported_eligible_loads)

        candidate_focals: list[tuple[int, shadow.core.PhysicalId, tuple[shadow.core.PhysicalId, ...]]] = []
        tables = observation.candidates.slot_tables
        for focal_user, source_raw in enumerate(main.physical_actions):
            if len(candidate_focals) >= max_focal_users:
                break
            if source_raw is None:
                continue
            source = shadow.core.validate_physical_id(
                source_raw, field="Main source physical ID"
            )
            if associations[focal_user] != source:
                continue
            source_load = loads.get(source, 0)
            if source_load <= 0:
                continue
            candidate_ids: list[shadow.core.PhysicalId] = []
            for candidate in _unique_valid_physical_ids(tables[focal_user]):
                if candidate == source or candidate[0] != source[0] or candidate not in active:
                    continue
                if not any(
                    user != focal_user and association == candidate
                    for user, association in enumerate(associations)
                ):
                    continue
                destination_load = loads.get(candidate, 0)
                if source_load < destination_load + 2:
                    continue
                candidate_ids.append(candidate)
            if candidate_ids:
                candidate_focals.append((focal_user, source, tuple(sorted(candidate_ids))))

        support_ids: dict[int, tuple[shadow.core.PhysicalId, ...]] = {}
        support_actions: dict[int, dict[shadow.core.PhysicalId, int]] = {}
        receipts: dict[int, tuple[shadow.C3V3ShadowReceipt, ...]] = {}
        candidate_wall_seconds: dict[int, tuple[float, ...]] = {}
        scanned_candidates = 0
        any_fail_closed = False
        for focal_user, source, candidate_ids in candidate_focals:
            forecast_fingerprint = _forecast_anchor_fingerprint(
                wrapped=wrapped,
                states=states,
                masks=masks,
                observation=observation,
                checkpoint_sha256=checkpoint_sha256,
                derivation_anchor_fingerprint_sha256=live_fingerprint,
                focal_user_id=focal_user,
                step_index=step_index,
                evaluation_seed=evaluation_seed,
            )
            anchor = shadow.C3V3ShadowAnchor(
                checkpoint_sha256=checkpoint_sha256,
                expected_anchor_fingerprint_sha256=forecast_fingerprint,
                evaluation_seed=evaluation_seed,
                step_index=step_index,
                focal_user_id=focal_user,
                source_id=source,
                prefix_actions=(),
            )
            backend = TrainerEnvironmentC3V3Backend(
                wrapped=wrapped,
                states=states,
                masks=masks,
                observation=observation,
                env_rng=env_rng,
                trainer=trainer,
                checkpoint_sha256=checkpoint_sha256,
                anchor_fingerprint_sha256=forecast_fingerprint,
                focal_user_id=focal_user,
                derivation_anchor_fingerprint_sha256=live_fingerprint,
            )
            backend.source_id = source
            focal_receipts: list[shadow.C3V3ShadowReceipt] = []
            focal_timings: list[float] = []
            for candidate in candidate_ids[:max_candidates_per_focal]:
                scanned_candidates += 1
                candidate_started = time.perf_counter()
                receipt = shadow.certify_candidate_support(
                    backend,
                    anchor=anchor,
                    candidate_id=candidate,
                    expected_user_count=user_count,
                    scheduled_anchor=scheduled_anchor,
                )
                focal_timings.append(time.perf_counter() - candidate_started)
                focal_receipts.append(receipt)
                any_fail_closed = any_fail_closed or receipt.status == "FAIL_CLOSED"
            receipts[focal_user] = tuple(focal_receipts)
            candidate_wall_seconds[focal_user] = tuple(focal_timings)
            certified = tuple(
                receipt.candidate_id
                for receipt in focal_receipts
                if receipt.certified and receipt.candidate_id is not None
            )
            if len(certified) >= 2:
                unique_certified = tuple(sorted(set(certified)))
                support_ids[focal_user] = unique_certified
                support_actions[focal_user] = {
                    physical_id: _action_for_physical_id(tables[focal_user], physical_id)
                    for physical_id in unique_certified
                }
                if any(value is None for value in support_actions[focal_user].values()):
                    raise RuntimeError("certified physical support cannot be remapped")
                support_actions[focal_user] = {
                    physical_id: int(value)
                    for physical_id, value in support_actions[focal_user].items()
                }

        status = "FAIL_CLOSED" if any_fail_closed else "COMPLETE"
        return TrainerC3V3SupportScan(
            schema=SCAN_SCHEMA,
            status=status,
            step_index=step_index,
            steps_remaining=steps_remaining,
            scanned_focal_users=tuple(focal_user for focal_user, _, _ in candidate_focals),
            scanned_candidates=scanned_candidates,
            support_physical_ids_by_focal=support_ids,
            support_action_indices_by_focal=support_actions,
            receipts_by_focal=receipts,
            reasons=(
                ("backend_candidate_attempt_failed_closed",) if any_fail_closed else ()
            ),
            candidate_wall_seconds_by_focal=candidate_wall_seconds,
        )
    except (AttributeError, IndexError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        step_index = int(getattr(observation, "step_index", -1))
        return _failure_scan(
            status="FAIL_CLOSED",
            step_index=step_index,
            steps_remaining=steps_remaining,
            reasons=(f"{type(exc).__name__}:{exc}",),
        )


__all__ = [
    "EXPECTED_OBJECTIVE_WEIGHTS",
    "FORECAST_ENV_NAMESPACE",
    "FORECAST_MOBILITY_NAMESPACE",
    "HOLD_OFFSETS",
    "RELEASE_OFFSET",
    "SCAN_SCHEMA",
    "TrainerC3V3Branch",
    "TrainerEnvironmentC3V3Backend",
    "TrainerC3V3SupportScan",
    "derive_forecast_rng",
    "live_anchor_fingerprint",
    "scan_current_support",
]
