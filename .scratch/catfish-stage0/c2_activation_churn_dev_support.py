"""Bounded in-memory C2 V3 support scan for developmental short-EP runs.

This module is deliberately narrower than the formal 150-row Stage-0 census.
It deep-copies the live *pre-outcome* training anchor, evaluates a capped set
of physical-ID candidates with fading disabled, and returns only candidates
that pass the frozen four-offset C2 activation-churn certificate.  It never
uses a realised candidate outcome to admit or reject a bundle, never changes
the canonical reward, and never updates a learner or Main.

The cap makes this suitable for an early trend screen.  It is not a formal
support-frequency result and cannot replace the closure-bound census.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

import c2_activation_churn_core as core  # noqa: E402
import c2_activation_churn_runtime_adapter as adapter  # noqa: E402
from mcrl.env.action_contract import (  # noqa: E402
    Association,
    HANDOVER_COST,
    NO_OP_ACTION,
)


DECISION_INTERVAL_S = 30.08
MAX_FOCAL_USERS = 1
MAX_CANDIDATES_PER_FOCAL = 4


PhysicalId = core.PhysicalId
PhysicalAction = core.PhysicalAction


@dataclass
class _Branch:
    wrapped: Any
    env_rng: np.random.Generator
    states: list[Any]
    masks: list[Any]
    observation: Any


@dataclass(frozen=True)
class EpisodeReplayAuthority:
    """Minimum episode-start material needed for fresh prefix replay twins."""

    environment_factory: Callable[[], Any]
    episode_env_rng: np.random.Generator
    episode_mobility_rng: np.random.Generator
    environment_training_state: Mapping[str, Any]
    prefix_actions: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class CandidateReceipt:
    focal_user: int
    incumbent_id: PhysicalId
    reference_departure_id: PhysicalId
    candidate_id: PhysicalId
    certified: bool
    first_failed_layer: str | None
    reasons: tuple[str, ...]
    hold_system_r2_delta: float
    full_system_r2_delta: float
    reference_energy_j: float
    candidate_energy_j: float
    reference_useful_bits: float
    candidate_useful_bits: float
    beam_pulses: tuple[PhysicalId, ...]
    satellite_pulses: tuple[int, ...]


@dataclass(frozen=True)
class C2DevelopmentSupport:
    support_actions_by_user: Mapping[int, tuple[int, ...]]
    support_ids_by_user: Mapping[int, tuple[PhysicalId, ...]]
    receipts: tuple[CandidateReceipt, ...]
    qualifying_departure_users: int
    scanned_candidates: int
    claim_ceiling: str = "DEVELOPMENT_ONLY_CAPPED_PREOUTCOME_SUPPORT"


def _rng_state_sha256(rng: np.random.Generator) -> str:
    return hashlib.sha256(repr(rng.bit_generator.state).encode("utf-8")).hexdigest()


def _replay_branch(
    authority: EpisodeReplayAuthority,
    *,
    expected_env_rng: np.random.Generator,
    expected_wrapped: Any,
    expected_observation: Any,
) -> _Branch:
    if not callable(authority.environment_factory):
        raise ValueError("episode replay environment factory must be callable")
    wrapped = authority.environment_factory()
    wrapped.load_training_state_dict(copy.deepcopy(dict(authority.environment_training_state)))
    if not isinstance(authority.episode_env_rng, np.random.Generator):
        raise ValueError("episode replay environment RNG must be a Generator")
    if not isinstance(authority.episode_mobility_rng, np.random.Generator):
        raise ValueError("episode replay mobility RNG must be a Generator")
    if authority.episode_env_rng is authority.episode_mobility_rng:
        raise ValueError("episode replay environment and mobility RNGs must be distinct")
    # Copy the complete Generator, not only bit_generator.state.  Generator
    # spawn lineage (used by the environment's age RNG) is not represented by
    # that state mapping and silently changes the warm-start segment ages.
    env_rng = copy.deepcopy(authority.episode_env_rng)
    mobility_rng = copy.deepcopy(authority.episode_mobility_rng)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    for expected_step, raw_actions in enumerate(authority.prefix_actions):
        if int(observation.step_index) != expected_step:
            raise RuntimeError("C2 prefix replay step index drifted")
        actions = np.asarray(raw_actions, dtype=np.int32)
        if actions.shape != (len(states),):
            raise RuntimeError("C2 prefix replay action row has wrong user count")
        result = wrapped.step(actions, env_rng)
        if result.done:
            raise RuntimeError("C2 prefix replay ended before the declared anchor")
        states = result.user_states
        masks = result.action_masks
        observation = wrapped.last_outcome.observation
    if int(observation.step_index) != int(expected_observation.step_index):
        raise RuntimeError("C2 replayed anchor step differs from live anchor")
    if not np.array_equal(observation.state_matrix, expected_observation.state_matrix):
        left = np.asarray(observation.state_matrix, dtype=np.float64)
        right = np.asarray(expected_observation.state_matrix, dtype=np.float64)
        finite_delta = np.abs(left - right)
        block_width = left.shape[1] // 4 if left.ndim == 2 and left.shape[1] % 4 == 0 else left.shape[1]
        block_mismatches = [
            int(np.count_nonzero(left[:, start : start + block_width] != right[:, start : start + block_width]))
            for start in range(0, left.shape[1], block_width)
        ]
        block_max_abs = [
            float(np.nanmax(finite_delta[:, start : start + block_width]))
            for start in range(0, left.shape[1], block_width)
        ]
        raise RuntimeError(
            "C2 replayed anchor state matrix differs from live anchor: "
            f"shape={left.shape}/{right.shape}, "
            f"mismatches={int(np.count_nonzero(left != right))}, "
            f"max_abs={float(np.nanmax(finite_delta))}, "
            f"block_mismatches={block_mismatches}, "
            f"block_max_abs={block_max_abs}"
        )
    if not np.array_equal(observation.masks, expected_observation.masks):
        raise RuntimeError("C2 replayed anchor masks differ from live anchor")
    if _rng_state_sha256(env_rng) != _rng_state_sha256(expected_env_rng):
        raise RuntimeError("C2 replayed environment RNG differs from live anchor")
    expected_mobility = expected_wrapped.environment._mobility_rng
    if not isinstance(expected_mobility, np.random.Generator):
        raise RuntimeError("live C2 anchor has no mobility RNG")
    replayed_mobility = wrapped.environment._mobility_rng
    if not isinstance(replayed_mobility, np.random.Generator):
        raise RuntimeError("replayed C2 anchor has no mobility RNG")
    if _rng_state_sha256(replayed_mobility) != _rng_state_sha256(expected_mobility):
        raise RuntimeError("C2 replayed mobility RNG differs from live anchor")
    wrapped.environment.physics = type(wrapped.environment.physics)(
        **{**wrapped.environment.physics.__dict__, "fading_enabled": False}
    )
    return _Branch(wrapped, env_rng, list(states), list(masks), observation)


def _physical_id_for_action(table: Any, action: int) -> PhysicalAction:
    if int(action) == NO_OP_ACTION:
        return None
    association = table.association(int(action))
    if not isinstance(association, Association):
        raise RuntimeError("valid physical action did not resolve to Association")
    return int(association.norad_id), int(association.cell_id)


def _action_for_physical_id(table: Any, physical_id: PhysicalAction) -> int | None:
    if physical_id is None:
        return NO_OP_ACTION if int(table.num_valid) == 0 else None
    target = core.validate_physical_id(physical_id)
    valid = np.flatnonzero(np.asarray(table.mask, dtype=bool)).tolist()
    matches = [
        int(action)
        for action in valid
        if int(table.norad_ids[action]) == target[0]
        and int(table.cell_ids[action]) == target[1]
    ]
    if len(matches) > 1:
        raise RuntimeError("duplicate physical ID in one candidate table")
    return matches[0] if matches else None


def _physical_actions(actions: Sequence[int], observation: Any) -> tuple[PhysicalAction, ...]:
    tables = observation.candidates.slot_tables
    if len(actions) != len(tables):
        raise ValueError("action row and candidate tables disagree on user count")
    return tuple(
        _physical_id_for_action(table, int(action))
        for action, table in zip(actions, tables, strict=True)
    )


def _unique_valid_ids(table: Any) -> tuple[PhysicalId, ...]:
    values: dict[PhysicalId, int] = {}
    for action in np.flatnonzero(np.asarray(table.mask, dtype=bool)).tolist():
        physical_id = _physical_id_for_action(table, int(action))
        if physical_id is None:
            continue
        if physical_id in values:
            raise RuntimeError("duplicate physical ID in one candidate table")
        values[physical_id] = int(action)
    return tuple(sorted(values))


def _active_ids_from_radiating(radiating: Any) -> tuple[PhysicalId, ...]:
    norads = np.asarray(radiating.norad_ids)
    cells = np.asarray(radiating.cell_ids)
    if norads.shape != cells.shape or norads.ndim != 1:
        raise ValueError("previous radiating physical-ID arrays drifted")
    return tuple(
        sorted((int(norad), int(cell)) for norad, cell in zip(norads, cells, strict=True))
    )


def _active_ids(outcome: Any) -> tuple[PhysicalId, ...]:
    return tuple(
        sorted(
            core.validate_physical_id(value, field="active physical ID")
            for value in outcome.resolution.active_beams
        )
    )


def _preview_matches(preview: Any, outcome: Any) -> bool:
    return bool(
        np.array_equal(preview.reward_matrix, outcome.reward_matrix)
        and np.array_equal(preview.resolution.served, outcome.resolution.served)
        and preview.resolution.active_beams == outcome.resolution.active_beams
        and np.array_equal(preview.link_power_w, outcome.link_power_w)
        and np.array_equal(preview.link_rate_bps, outcome.link_rate_bps)
        and preview.handovers == outcome.handovers
        and preview.system_power_w == outcome.system_power_w
        and preview.fixed_power_w == outcome.fixed_power_w
    )


def _reentry_before_step(branch: _Branch, user: int) -> bool:
    previous = branch.wrapped.environment._ledgers[user].previous
    return previous is not None and not isinstance(previous, Association)


def _advance(branch: _Branch, actions: np.ndarray) -> tuple[Any, bool]:
    preview = branch.wrapped.environment.evaluate_actions(actions, branch.env_rng)
    result = branch.wrapped.step(actions, branch.env_rng)
    outcome = branch.wrapped.last_outcome
    parity = _preview_matches(preview, outcome)
    branch.states = list(result.user_states)
    branch.masks = list(result.action_masks)
    branch.observation = outcome.observation
    return outcome, parity


def _main_decision(trainer: Any, branch: _Branch) -> adapter.ScalarizedMainDecision:
    return adapter.scalarized_main_decision(
        trainer,
        branch.states,
        branch.masks,
        slot_tables=branch.observation.candidates.slot_tables,
    )


def _certificate(
    trainer: Any,
    *,
    wrapped: Any,
    env_rng: np.random.Generator,
    states: Sequence[Any],
    masks: Sequence[Any],
    observation: Any,
    focal_user: int,
    incumbent_id: PhysicalId,
    reference_departure_id: PhysicalId,
    candidate_id: PhysicalId,
    replay_authority: EpisodeReplayAuthority,
) -> CandidateReceipt:
    reference = _replay_branch(
        replay_authority,
        expected_env_rng=env_rng,
        expected_wrapped=wrapped,
        expected_observation=observation,
    )
    candidate = _replay_branch(
        replay_authority,
        expected_env_rng=env_rng,
        expected_wrapped=wrapped,
        expected_observation=observation,
    )
    if reference.wrapped is candidate.wrapped or reference.env_rng is candidate.env_rng:
        raise RuntimeError("C2 forecast branches must be distinct deep twins")

    pre_active = _active_ids_from_radiating(
        reference.wrapped.environment._previous_radiating
    )
    reference_active: list[tuple[PhysicalId, ...]] = [pre_active]
    candidate_active: list[tuple[PhysicalId, ...]] = [pre_active]
    reference_r2: list[tuple[float, ...]] = []
    candidate_r2: list[tuple[float, ...]] = []
    reference_served: list[tuple[bool, ...]] = []
    candidate_served: list[tuple[bool, ...]] = []
    reference_reentry: list[tuple[bool, ...]] = []
    candidate_reentry: list[tuple[bool, ...]] = []
    hold_intervals: list[core.HoldInterval] = []
    reference_nonfocal: list[tuple[PhysicalAction, ...]] = []
    candidate_nonfocal: list[tuple[PhysicalAction, ...]] = []
    reference_energy = 0.0
    candidate_energy = 0.0
    reference_bits = 0.0
    candidate_bits = 0.0
    power_identity_passed = True
    parity_passed = True
    structural_reasons: list[str] = []
    release_action: PhysicalAction = None

    for offset in core.CERTIFICATE_OFFSETS:
        reference_decision = _main_decision(trainer, reference)
        candidate_decision = _main_decision(trainer, candidate)
        if reference_decision.physical_actions is None or candidate_decision.physical_actions is None:
            raise RuntimeError("C2 forecast requires physical Main action receipts")
        reference_physical = reference_decision.physical_actions
        candidate_main_physical = candidate_decision.physical_actions
        reference_nonfocal.append(
            tuple(value for uid, value in enumerate(reference_physical) if uid != focal_user)
        )
        candidate_nonfocal.append(
            tuple(value for uid, value in enumerate(candidate_main_physical) if uid != focal_user)
        )
        if reference_nonfocal[-1] != candidate_nonfocal[-1]:
            structural_reasons.append(f"nonfocal_divergence_offset_{offset}")

        reference_actions = np.asarray(reference_decision.actions, dtype=np.int32)
        candidate_actions = np.asarray(candidate_decision.actions, dtype=np.int32)
        candidate_tables = candidate.observation.candidates.slot_tables
        # Execute the reference non-focal physical script in both forks after
        # independently proving that branch-local Main agrees with it.
        for uid, physical_id in enumerate(reference_physical):
            if uid == focal_user:
                continue
            remapped = _action_for_physical_id(candidate_tables[uid], physical_id)
            if remapped is None:
                structural_reasons.append(
                    f"reference_nonfocal_unmappable_offset_{offset}_user_{uid}"
                )
                continue
            candidate_actions[uid] = int(remapped)

        if offset < core.HOLD_STEPS:
            mapped = _action_for_physical_id(candidate_tables[focal_user], candidate_id)
            if mapped is None:
                structural_reasons.append(f"candidate_unmappable_offset_{offset}")
            else:
                candidate_actions[focal_user] = int(mapped)
        else:
            release_action = candidate_main_physical[focal_user]

        reference_was_unserved = tuple(
            _reentry_before_step(reference, uid) for uid in range(len(reference.states))
        )
        candidate_was_unserved = tuple(
            _reentry_before_step(candidate, uid) for uid in range(len(candidate.states))
        )
        reference_outcome, reference_parity = _advance(reference, reference_actions)
        candidate_outcome, candidate_parity = _advance(candidate, candidate_actions)
        parity_passed = parity_passed and reference_parity and candidate_parity

        reference_power = adapter.canonical_power_projection(
            reference_outcome,
            pa_max_efficiency=float(
                reference.wrapped.environment.physics.pa_max_efficiency
            ),
            pa_saturation_power_w=float(
                reference.wrapped.environment.physics.pa_saturation_power_w
            ),
        )
        candidate_power = adapter.canonical_power_projection(
            candidate_outcome,
            pa_max_efficiency=float(
                candidate.wrapped.environment.physics.pa_max_efficiency
            ),
            pa_saturation_power_w=float(
                candidate.wrapped.environment.physics.pa_saturation_power_w
            ),
        )
        power_identity_passed = bool(
            power_identity_passed
            and reference_power.identity.passed
            and candidate_power.identity.passed
        )
        reference_energy += DECISION_INTERVAL_S * float(reference_outcome.system_power_w)
        candidate_energy += DECISION_INTERVAL_S * float(candidate_outcome.system_power_w)
        reference_bits += DECISION_INTERVAL_S * float(
            np.asarray(reference_outcome.link_rate_bps, dtype=np.float64).sum()
        )
        candidate_bits += DECISION_INTERVAL_S * float(
            np.asarray(candidate_outcome.link_rate_bps, dtype=np.float64).sum()
        )
        reference_active.append(_active_ids(reference_outcome))
        candidate_active.append(_active_ids(candidate_outcome))
        reference_r2.append(
            tuple(float(value) for value in reference_outcome.reward_matrix[:, 1])
        )
        candidate_r2.append(
            tuple(float(value) for value in candidate_outcome.reward_matrix[:, 1])
        )
        reference_served.append(
            tuple(bool(value) for value in reference_outcome.resolution.served)
        )
        candidate_served.append(
            tuple(bool(value) for value in candidate_outcome.resolution.served)
        )
        reference_reentry.append(
            tuple(
                was_unserved and served
                for was_unserved, served in zip(
                    reference_was_unserved,
                    reference_served[-1],
                    strict=True,
                )
            )
        )
        candidate_reentry.append(
            tuple(
                was_unserved and served
                for was_unserved, served in zip(
                    candidate_was_unserved,
                    candidate_served[-1],
                    strict=True,
                )
            )
        )
        if offset < core.HOLD_STEPS:
            realised_id: PhysicalAction = None
            if bool(candidate_outcome.resolution.served[focal_user]):
                realised_id = (
                    int(candidate_outcome.resolution.serving_satellite[focal_user]),
                    int(candidate_outcome.resolution.serving_cell[focal_user]),
                )
            hold_intervals.append(
                core.HoldInterval(
                    physical_id=realised_id,
                    uniquely_remapped=not any(
                        reason == f"candidate_unmappable_offset_{offset}"
                        for reason in structural_reasons
                    ),
                    action_valid=True,
                    recurrence_power_w=float(candidate_outcome.link_power_w[focal_user]),
                    canonical_link_ceiling_w=float(
                        candidate.wrapped.environment.physics.beam_power_max_w
                    ),
                    served=bool(candidate_outcome.resolution.served[focal_user]),
                )
            )

    sequence = core.validate_candidate_sequence(
        incumbent_id=incumbent_id,
        declared_id=candidate_id,
        hold_intervals=hold_intervals,
        release_action=release_action,
        release_from_main=True,
        full_release_window=True,
    )
    nonfocal_identity = core.nonfocal_physical_identity(
        reference_nonfocal, candidate_nonfocal
    )
    pulses = core.activation_pulses(reference_active, candidate_active)
    mechanism = core.evaluate_activation_energy_mechanism(
        pulses,
        reference_complete_energy_j=reference_energy,
        candidate_complete_energy_j=candidate_energy,
    )
    release_report = core.ReleaseReport(
        reference_focal_r2=reference_r2[3][focal_user],
        candidate_focal_r2=candidate_r2[3][focal_user],
        reference_system_r2=sum(reference_r2[3]),
        candidate_system_r2=sum(candidate_r2[3]),
    )
    reward = core.evaluate_reward_release_service(
        reference_r2=reference_r2,
        candidate_r2=candidate_r2,
        allowed_r2_values=tuple(-float(value) for value in sorted(set(HANDOVER_COST.values()))),
        focal_user=focal_user,
        reference_served=reference_served,
        candidate_served=candidate_served,
        reference_reentry=reference_reentry,
        candidate_reentry=candidate_reentry,
        release_report=release_report,
    )
    proxies = core.evaluate_binary_proxies(
        reference_useful_bits=reference_bits,
        candidate_useful_bits=candidate_bits,
        reference_energy_j=reference_energy,
        candidate_energy_j=candidate_energy,
    )
    strict_system_r2 = bool(
        reward.candidate_hold_r2 > reward.reference_hold_r2
        and reward.candidate_full_r2 > reward.reference_full_r2
    )
    service_reasons = {
        "focal_outage",
        "focal_reentry",
        "served_to_unserved",
        "release_event_omitted",
        "release_event_mismatch",
    }
    service_passed = not any(reason in service_reasons for reason in reward.reasons)
    hard_safe = bool(
        sequence.passed
        and power_identity_passed
        and parity_passed
        and not structural_reasons
    )
    layers = core.evaluate_layers(
        core.LayerEvidence(
            scheduled_anchor=True,
            qualifying_departure_anchor=True,
            unique_physical_candidate=True,
            hard_safe=hard_safe,
            nonfocal_identity=nonfocal_identity,
            activation_or_energy=mechanism.passed,
            strict_system_r2=strict_system_r2,
            service_and_binary_proxies=service_passed and proxies.passed,
        )
    )
    reasons = list(structural_reasons)
    if not sequence.passed and sequence.reason is not None:
        reasons.append(sequence.reason)
    if not power_identity_passed:
        reasons.append("canonical_power_identity_failed")
    if not parity_passed:
        reasons.append("preview_commit_mismatch")
    if not nonfocal_identity:
        reasons.append("nonfocal_physical_identity_failed")
    if not mechanism.passed:
        reasons.append("activation_or_energy_failed")
    reasons.extend(reward.reasons)
    reasons.extend(proxies.reasons)
    if layers.first_failed_layer is not None:
        reasons.append(f"layer:{layers.first_failed_layer}")
    return CandidateReceipt(
        focal_user=focal_user,
        incumbent_id=incumbent_id,
        reference_departure_id=reference_departure_id,
        candidate_id=candidate_id,
        certified=layers.certified,
        first_failed_layer=layers.first_failed_layer,
        reasons=tuple(dict.fromkeys(reasons)),
        hold_system_r2_delta=reward.candidate_hold_r2 - reward.reference_hold_r2,
        full_system_r2_delta=reward.candidate_full_r2 - reward.reference_full_r2,
        reference_energy_j=reference_energy,
        candidate_energy_j=candidate_energy,
        reference_useful_bits=reference_bits,
        candidate_useful_bits=candidate_bits,
        beam_pulses=tuple(sorted(pulses.beam_pulses)),
        satellite_pulses=tuple(sorted(pulses.satellite_pulses)),
    )


def scan_c2_development_support(
    trainer: Any,
    *,
    wrapped: Any,
    env_rng: np.random.Generator,
    states: Sequence[Any],
    masks: Sequence[Any],
    observation: Any,
    steps_remaining: int,
    replay_authority: EpisodeReplayAuthority | None = None,
    max_focal_users: int = MAX_FOCAL_USERS,
    max_candidates_per_focal: int = MAX_CANDIDATES_PER_FOCAL,
    focal_user_ids: Sequence[int] | None = None,
) -> C2DevelopmentSupport:
    """Return capped, full-certificate C2 support for one live anchor."""

    if type(steps_remaining) is not int or steps_remaining < 0:
        raise ValueError("steps_remaining must be a nonnegative exact integer")
    if type(max_focal_users) is not int or max_focal_users < 1:
        raise ValueError("max_focal_users must be a positive exact integer")
    if type(max_candidates_per_focal) is not int or max_candidates_per_focal < 1:
        raise ValueError("max_candidates_per_focal must be a positive exact integer")
    selected_focal_users: frozenset[int] | None = None
    if focal_user_ids is not None:
        normalized_focal_users: list[int] = []
        for value in focal_user_ids:
            if type(value) is not int or value < 0:
                raise ValueError("focal_user_ids must contain nonnegative exact integers")
            normalized_focal_users.append(value)
        if not normalized_focal_users:
            raise ValueError("focal_user_ids must not be empty")
        if len(set(normalized_focal_users)) != len(normalized_focal_users):
            raise ValueError("focal_user_ids must not contain duplicates")
        selected_focal_users = frozenset(normalized_focal_users)
    if steps_remaining < len(core.CERTIFICATE_OFFSETS):
        return C2DevelopmentSupport({}, {}, (), 0, 0)
    if replay_authority is None:
        raise ValueError("full-horizon C2 scan requires episode replay authority")
    if type(replay_authority) is not EpisodeReplayAuthority:
        raise ValueError("replay_authority must be EpisodeReplayAuthority")
    main = adapter.scalarized_main_decision(
        trainer,
        states,
        masks,
        slot_tables=observation.candidates.slot_tables,
    )
    if main.physical_actions is None:
        raise RuntimeError("C2 development scan requires physical Main actions")

    departure_users: list[tuple[int, PhysicalId, PhysicalId]] = []
    previous = wrapped.environment._previous_association
    for uid, (incumbent, departure) in enumerate(
        zip(previous, main.physical_actions, strict=True)
    ):
        if not isinstance(incumbent, Association) or departure is None:
            continue
        incumbent_id = (int(incumbent.norad_id), int(incumbent.cell_id))
        if departure != incumbent_id:
            departure_users.append((uid, incumbent_id, departure))

    receipts: list[CandidateReceipt] = []
    support_actions: dict[int, tuple[int, ...]] = {}
    support_ids: dict[int, tuple[PhysicalId, ...]] = {}
    selected_departures = (
        departure_users
        if selected_focal_users is None
        else [row for row in departure_users if row[0] in selected_focal_users]
    )
    for uid, incumbent_id, departure_id in selected_departures[:max_focal_users]:
        table = observation.candidates.slot_tables[uid]
        ids = _unique_valid_ids(table)
        ordered = tuple(
            dict.fromkeys(
                ([incumbent_id] if incumbent_id in ids else [])
                + [value for value in ids if value != incumbent_id]
            )
        )[:max_candidates_per_focal]
        certified_ids: list[PhysicalId] = []
        certified_actions: list[int] = []
        for candidate_id in ordered:
            receipt = _certificate(
                trainer,
                wrapped=wrapped,
                env_rng=env_rng,
                states=states,
                masks=masks,
                observation=observation,
                focal_user=uid,
                incumbent_id=incumbent_id,
                reference_departure_id=departure_id,
                candidate_id=candidate_id,
                replay_authority=replay_authority,
            )
            receipts.append(receipt)
            if receipt.certified:
                action = _action_for_physical_id(table, candidate_id)
                if action is None:
                    raise RuntimeError("certified C2 physical ID no longer maps at anchor")
                certified_ids.append(candidate_id)
                certified_actions.append(action)
        # A learned Catfish needs a genuine within-support choice.  Singleton
        # support remains in receipts but is not routed into C2-I training.
        if len(certified_ids) >= 2:
            support_ids[uid] = tuple(certified_ids)
            support_actions[uid] = tuple(certified_actions)
    return C2DevelopmentSupport(
        support_actions_by_user=support_actions,
        support_ids_by_user=support_ids,
        receipts=tuple(receipts),
        qualifying_departure_users=len(departure_users),
        scanned_candidates=len(receipts),
    )


__all__ = [
    "CandidateReceipt",
    "C2DevelopmentSupport",
    "EpisodeReplayAuthority",
    "scan_c2_development_support",
]
