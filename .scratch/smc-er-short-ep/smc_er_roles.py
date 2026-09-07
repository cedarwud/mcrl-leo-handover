"""Pre-outcome role decisions for the Multi-Catfish MCRL carrier.

The helpers in this module never update Main and never inspect a realised
reward.  They translate relative action slots to physical associations, build
the C1 source, and maintain the C2/C3 training-only option commitments.  The
runner remains responsible for executing and retaining every outcome.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))

from mcrl.env.action_contract import NO_OP_ACTION, Association  # noqa: E402
from mcrl.runtime.head_pivotality import masked_greedy_actions  # noqa: E402


PhysicalKey = tuple[int, int]


def physical_key_for_action(table: Any, action: int) -> PhysicalKey | None:
    """Return the stable physical identity behind one relative action."""

    if int(action) == NO_OP_ACTION:
        return None
    association = table.association(int(action))
    if not isinstance(association, Association):
        return None
    return int(association.norad_id), int(association.cell_id)


def action_for_physical_key(table: Any, key: PhysicalKey) -> int | None:
    """Remap a committed physical identity after candidate-table reorder."""

    matches = [
        int(action)
        for action in np.flatnonzero(np.asarray(table.mask, dtype=bool)).tolist()
        if int(table.norad_ids[action]) == int(key[0])
        and int(table.cell_ids[action]) == int(key[1])
    ]
    if len(matches) > 1:
        raise RuntimeError(f"duplicate physical association in slot table: {key}")
    return matches[0] if matches else None


def unique_valid_actions(table: Any) -> tuple[int, ...]:
    """One deterministic action per physical association in a slot table."""

    by_key: dict[PhysicalKey, int] = {}
    for action in np.flatnonzero(np.asarray(table.mask, dtype=bool)).tolist():
        key = physical_key_for_action(table, int(action))
        if key is None:
            continue
        by_key.setdefault(key, int(action))
    return tuple(by_key[key] for key in sorted(by_key))


def main_greedy_actions(
    main: Any, encoded: np.ndarray, wrapped_masks: Sequence[Any]
) -> np.ndarray:
    """Read frozen scalarized Main without consuming Main's training RNG."""

    masks = np.stack([np.asarray(row.mask, dtype=bool) for row in wrapped_masks])
    return masked_greedy_actions(main.scalarized_q_values(encoded), masks)


def epsilon_greedy_probabilities(
    main: Any,
    encoded: np.ndarray,
    wrapped_masks: Sequence[Any],
    actions: np.ndarray,
    *,
    epsilon: float,
) -> np.ndarray:
    """Marginal probability of each executed canonical Main action."""

    if not np.isfinite(epsilon) or not 0.0 <= float(epsilon) <= 1.0:
        raise ValueError("epsilon must be finite in [0,1]")
    masks = np.stack([np.asarray(row.mask, dtype=bool) for row in wrapped_masks])
    greedy = masked_greedy_actions(main.scalarized_q_values(encoded), masks)
    chosen = np.asarray(actions)
    if chosen.shape != greedy.shape:
        raise ValueError("actions and Main state batch disagree")
    probabilities = np.ones(chosen.size, dtype=np.float64)
    for uid, mask in enumerate(masks):
        valid = np.flatnonzero(mask)
        if valid.size == 0:
            if int(chosen[uid]) != NO_OP_ACTION:
                raise ValueError("non-no-op action under an empty Main mask")
            continue
        action = int(chosen[uid])
        if action not in valid:
            raise ValueError("executed Main action is outside its mask")
        probability = float(epsilon) / float(valid.size)
        if action == int(greedy[uid]):
            probability += 1.0 - float(epsilon)
        probabilities[uid] = probability
    return probabilities


def local_snr_greedy_actions(
    raw_states: Sequence[Any], wrapped_masks: Sequence[Any]
) -> tuple[np.ndarray, np.ndarray]:
    """LEO-native C1 source: largest pre-action candidate SNR per user."""

    users = len(raw_states)
    actions = np.full(users, NO_OP_ACTION, dtype=np.int32)
    probabilities = np.ones(users, dtype=np.float64)
    for uid, (state, wrapped) in enumerate(
        zip(raw_states, wrapped_masks, strict=True)
    ):
        valid = np.flatnonzero(np.asarray(wrapped.mask, dtype=bool))
        if valid.size == 0:
            continue
        quality = np.asarray(state.channel_quality, dtype=np.float64)
        if quality.shape != np.asarray(wrapped.mask).shape:
            raise ValueError("C1 channel-quality row and action mask disagree")
        finite = valid[np.isfinite(quality[valid])]
        if finite.size != valid.size:
            raise ValueError("C1 source requires finite SNR on every valid action")
        actions[uid] = min(
            (int(action) for action in valid.tolist()),
            key=lambda action: (-float(quality[action]), action),
        )
    return actions, probabilities


def masked_uniform_actions(
    wrapped_masks: Sequence[Any], rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Dose-matched neutral source over each post-mask support."""

    users = len(wrapped_masks)
    actions = np.full(users, NO_OP_ACTION, dtype=np.int32)
    probabilities = np.ones(users, dtype=np.float64)
    for uid, wrapped in enumerate(wrapped_masks):
        valid = np.flatnonzero(np.asarray(wrapped.mask, dtype=bool))
        if valid.size == 0:
            continue
        actions[uid] = int(valid[int(rng.integers(0, valid.size))])
        probabilities[uid] = 1.0 / float(valid.size)
    return actions, probabilities


def specialist_joint_actions(
    specialist: Any,
    encoded: np.ndarray,
    wrapped_masks: Sequence[Any],
    *,
    epsilon: float,
    informed: bool,
) -> tuple[np.ndarray, np.ndarray]:
    """Select a complete C1 joint action with one independent specialist."""

    users = len(wrapped_masks)
    actions = np.full(users, NO_OP_ACTION, dtype=np.int32)
    probabilities = np.ones(users, dtype=np.float64)
    for uid, wrapped in enumerate(wrapped_masks):
        support = tuple(
            int(action)
            for action in np.flatnonzero(np.asarray(wrapped.mask, dtype=bool))
        )
        action, probability = specialist.select_row(
            encoded[uid], support, epsilon=epsilon, informed=informed
        )
        actions[uid] = int(action)
        probabilities[uid] = float(probability)
    return actions, probabilities


@dataclass
class OptionCommitment:
    """Training-only physical association commitment for C2 or C3."""

    focal_user: int | None = None
    physical_key: PhysicalKey | None = None
    remaining: int = 0
    opened_step: int | None = None

    @property
    def open(self) -> bool:
        return (
            self.focal_user is not None
            and self.physical_key is not None
            and self.remaining > 0
        )

    def close(self) -> None:
        self.focal_user = None
        self.physical_key = None
        self.remaining = 0
        self.opened_step = None


@dataclass(frozen=True)
class RoleDecision:
    actions: np.ndarray
    probabilities: np.ndarray
    focal_user: int | None
    trigger: str
    support_actions: tuple[int, ...]
    selected_key: PhysicalKey | None
    option_open_before: bool
    option_open_after_selection: bool
    termination: str | None = None


def c2_persistence_decision(
    *,
    specialist: Any,
    encoded: np.ndarray,
    main_actions: np.ndarray,
    slot_tables: Sequence[Any],
    incumbents: Sequence[PhysicalKey | None],
    commitment: OptionCommitment,
    epsilon: float,
    informed: bool,
    step_index: int,
    horizon: int = 3,
) -> RoleDecision:
    """Open or continue the C2 option using only pre-outcome information."""

    actions = np.asarray(main_actions, dtype=np.int32).copy()
    probabilities = np.ones(actions.size, dtype=np.float64)
    open_before = commitment.open
    termination: str | None = None

    if commitment.open:
        assert commitment.focal_user is not None
        assert commitment.physical_key is not None
        focal = int(commitment.focal_user)
        mapped = action_for_physical_key(
            slot_tables[focal], commitment.physical_key
        )
        if mapped is not None:
            actions[focal] = int(mapped)
            return RoleDecision(
                actions=actions,
                probabilities=probabilities,
                focal_user=focal,
                trigger="option_continuation",
                support_actions=(int(mapped),),
                selected_key=commitment.physical_key,
                option_open_before=True,
                option_open_after_selection=True,
            )
        commitment.close()
        termination = "bound_physical_id_invalid"

    trigger_users: list[tuple[int, tuple[int, ...]]] = []
    for uid, (table, incumbent) in enumerate(
        zip(slot_tables, incumbents, strict=True)
    ):
        support = unique_valid_actions(table)
        if incumbent is None or len(support) < 2:
            continue
        main_key = physical_key_for_action(table, int(actions[uid]))
        if main_key is not None and main_key != incumbent:
            trigger_users.append((uid, support))

    if trigger_users:
        chosen = int(specialist.rng.integers(0, len(trigger_users)))
        focal, support = trigger_users[chosen]
        action, probability = specialist.select_row(
            encoded[focal], support, epsilon=epsilon, informed=informed
        )
        key = physical_key_for_action(slot_tables[focal], int(action))
        if key is None:
            raise RuntimeError("C2 selected a non-physical action")
        actions[focal] = int(action)
        probabilities[focal] = float(probability)
        commitment.focal_user = int(focal)
        commitment.physical_key = key
        commitment.remaining = int(horizon)
        commitment.opened_step = int(step_index)
        return RoleDecision(
            actions=actions,
            probabilities=probabilities,
            focal_user=int(focal),
            trigger="main_change_boundary",
            support_actions=tuple(support),
            selected_key=key,
            option_open_before=open_before,
            option_open_after_selection=True,
            termination=termination,
        )

    return RoleDecision(
        actions=actions,
        probabilities=probabilities,
        focal_user=None,
        trigger="no_trigger_main_fallback",
        support_actions=(),
        selected_key=None,
        option_open_before=open_before,
        option_open_after_selection=False,
        termination=termination,
    )


def c2_activation_churn_decision(
    *,
    specialist: Any,
    encoded: np.ndarray,
    main_actions: np.ndarray,
    slot_tables: Sequence[Any],
    certified_supports: Mapping[int, Sequence[int]],
    commitment: OptionCommitment,
    epsilon: float,
    informed: bool,
    step_index: int,
    horizon: int = 3,
) -> RoleDecision:
    """Open or continue C2 only inside the full activation-churn support."""

    actions = np.asarray(main_actions, dtype=np.int32).copy()
    probabilities = np.ones(actions.size, dtype=np.float64)
    open_before = commitment.open
    termination: str | None = None

    if commitment.open:
        assert commitment.focal_user is not None
        assert commitment.physical_key is not None
        focal = int(commitment.focal_user)
        mapped = action_for_physical_key(slot_tables[focal], commitment.physical_key)
        if mapped is not None:
            actions[focal] = int(mapped)
            return RoleDecision(
                actions=actions,
                probabilities=probabilities,
                focal_user=focal,
                trigger="activation_churn_option_continuation",
                support_actions=(int(mapped),),
                selected_key=commitment.physical_key,
                option_open_before=True,
                option_open_after_selection=True,
            )
        commitment.close()
        termination = "bound_physical_id_invalid"

    candidates = [
        (int(uid), tuple(int(action) for action in support))
        for uid, support in sorted(certified_supports.items())
        if len(tuple(support)) >= 2
    ]
    if candidates:
        chosen = int(specialist.rng.integers(0, len(candidates)))
        focal, support = candidates[chosen]
        action, probability = specialist.select_row(
            encoded[focal], support, epsilon=epsilon, informed=informed
        )
        key = physical_key_for_action(slot_tables[focal], int(action))
        if key is None:
            raise RuntimeError("C2 selected a non-physical certified action")
        actions[focal] = int(action)
        probabilities[focal] = float(probability)
        commitment.focal_user = int(focal)
        commitment.physical_key = key
        commitment.remaining = int(horizon)
        commitment.opened_step = int(step_index)
        return RoleDecision(
            actions=actions,
            probabilities=probabilities,
            focal_user=int(focal),
            trigger="activation_churn_certificate_nonempty",
            support_actions=support,
            selected_key=key,
            option_open_before=open_before,
            option_open_after_selection=True,
            termination=termination,
        )

    return RoleDecision(
        actions=actions,
        probabilities=probabilities,
        focal_user=None,
        trigger="empty_activation_churn_certificate_main_fallback",
        support_actions=(),
        selected_key=None,
        option_open_before=open_before,
        option_open_after_selection=False,
        termination=termination,
    )


def c2_observable_decision(
    *,
    specialist: Any,
    encoded: np.ndarray,
    main_actions: np.ndarray,
    slot_tables: Sequence[Any],
    eligible_supports: Mapping[int, Sequence[int]],
    commitment: OptionCommitment,
    epsilon: float,
    informed: bool,
    step_index: int,
    horizon: int = 3,
) -> RoleDecision:
    """Open/continue C2 using only V0.2 observable activation support."""

    decision = c2_activation_churn_decision(
        specialist=specialist,
        encoded=encoded,
        main_actions=main_actions,
        slot_tables=slot_tables,
        certified_supports=eligible_supports,
        commitment=commitment,
        epsilon=epsilon,
        informed=informed,
        step_index=step_index,
        horizon=horizon,
    )
    trigger = {
        "activation_churn_option_continuation": (
            "activation_onset_option_continuation"
        ),
        "activation_churn_certificate_nonempty": (
            "observable_activation_onset_choice"
        ),
        "empty_activation_churn_certificate_main_fallback": (
            "empty_observable_activation_support_main_fallback"
        ),
    }[decision.trigger]
    return RoleDecision(
        actions=decision.actions,
        probabilities=decision.probabilities,
        focal_user=decision.focal_user,
        trigger=trigger,
        support_actions=decision.support_actions,
        selected_key=decision.selected_key,
        option_open_before=decision.option_open_before,
        option_open_after_selection=decision.option_open_after_selection,
        termination=decision.termination,
    )


def strict_load_actions(
    *,
    table: Any,
    source_key: PhysicalKey,
    active_keys: Sequence[PhysicalKey],
    eligible_loads: Mapping[PhysicalKey, int],
) -> tuple[int, ...]:
    """C3's exact one-user R3-improving same-satellite pre-screen."""

    source_load = int(eligible_loads.get(source_key, 0))
    active = set((int(key[0]), int(key[1])) for key in active_keys)
    supported: list[int] = []
    for action in unique_valid_actions(table):
        key = physical_key_for_action(table, action)
        if key is None or key == source_key:
            continue
        if key[0] != source_key[0] or key not in active:
            continue
        destination_load = int(eligible_loads.get(key, 0))
        if source_load >= destination_load + 2:
            supported.append(int(action))
    return tuple(supported)


def _lagged_demand_row(state: Any, table: Any) -> np.ndarray:
    """Validate the state-visible, per-action lagged ungated demand row."""

    if not hasattr(state, "beam_loads"):
        raise ValueError("observable support requires state beam_loads")
    loads = np.asarray(state.beam_loads, dtype=np.float64)
    mask = np.asarray(table.mask, dtype=bool)
    if loads.ndim != 1 or loads.shape != mask.shape:
        raise ValueError("state beam_loads and action mask disagree")
    valid = loads[mask]
    if np.any(~np.isfinite(valid)) or np.any(valid < 0.0):
        raise ValueError("valid lagged beam demands must be finite and nonnegative")
    if np.any(valid != np.rint(valid)):
        raise ValueError("valid lagged beam demands must be integer-valued")
    return loads


def observable_c2_supports(
    *,
    states: Sequence[Any],
    main_actions: Sequence[int],
    slot_tables: Sequence[Any],
    incumbents: Sequence[PhysicalKey | None],
) -> dict[int, tuple[int, ...]]:
    """Return C2 V0.2 activation-onset supports from observable state inputs.

    C2 is eligible when Main proposes to leave a still-valid incumbent for a
    cold destination whose lagged demand is zero.  Its support is the
    incumbent plus other currently valid warm beams.  The cold Main target is
    deliberately excluded; no future outcome or forecast is consulted.
    """

    if not (
        len(states) == len(main_actions) == len(slot_tables) == len(incumbents)
    ):
        raise ValueError("C2 support inputs disagree on user count")
    supports: dict[int, tuple[int, ...]] = {}
    for uid, (state, raw_main_action, table, incumbent) in enumerate(
        zip(states, main_actions, slot_tables, incumbents, strict=True)
    ):
        if incumbent is None:
            continue
        incumbent_key = (int(incumbent[0]), int(incumbent[1]))
        incumbent_action = action_for_physical_key(table, incumbent_key)
        if incumbent_action is None:
            continue
        main_action = int(raw_main_action)
        main_key = physical_key_for_action(table, main_action)
        if main_key is None or main_key == incumbent_key:
            continue
        loads = _lagged_demand_row(state, table)
        if loads[main_action] != 0.0:
            continue
        warm = tuple(
            action
            for action in unique_valid_actions(table)
            if action != incumbent_action and loads[action] >= 1.0
        )
        support = tuple(dict.fromkeys((int(incumbent_action), *warm)))
        if len(support) >= 2:
            supports[int(uid)] = support
    return supports


def observable_c3_supports(
    *,
    states: Sequence[Any],
    main_actions: Sequence[int],
    slot_tables: Sequence[Any],
    incumbents: Sequence[PhysicalKey | None],
) -> dict[int, tuple[int, ...]]:
    """Build C3 V0.2 support from pre-outcome load and feasibility only.

    A focal is eligible only when scalarized Main proposes to retain its
    current physical association.  The support contains that explicit
    defer-to-Main action plus every warm, same-satellite beam whose lagged
    ungated demand is at least two users lower.  Future rewards, fading,
    counterfactual outcomes, and release outcomes are deliberately absent.
    """

    if not (
        len(states) == len(main_actions) == len(slot_tables) == len(incumbents)
    ):
        raise ValueError("C3 support inputs disagree on user count")
    supports: dict[int, tuple[int, ...]] = {}
    for uid, (state, raw_main_action, table, source) in enumerate(
        zip(states, main_actions, slot_tables, incumbents, strict=True)
    ):
        if source is None:
            continue
        source_key = (int(source[0]), int(source[1]))
        main_action = int(raw_main_action)
        if physical_key_for_action(table, main_action) != source_key:
            continue
        source_action = action_for_physical_key(table, source_key)
        if source_action is None:
            continue
        loads = _lagged_demand_row(state, table)
        source_load = loads[source_action]
        interventions = tuple(
            action
            for action in unique_valid_actions(table)
            if (
                (key := physical_key_for_action(table, action)) is not None
                and key != source_key
                and key[0] == source_key[0]
                and loads[action] >= 1.0
                and source_load >= loads[action] + 2.0
            )
        )
        if interventions:
            supports[int(uid)] = tuple(
                dict.fromkeys((int(source_action), *interventions))
            )
    return supports


def c3_relocation_decision(
    *,
    specialist: Any,
    encoded: np.ndarray,
    main_actions: np.ndarray,
    slot_tables: Sequence[Any],
    eligible_supports: Mapping[int, Sequence[int]],
    commitment: OptionCommitment,
    epsilon: float,
    informed: bool,
    step_index: int,
    horizon: int = 3,
) -> RoleDecision:
    """Choose defer or a feasible load relocation from pre-outcome support."""

    actions = np.asarray(main_actions, dtype=np.int32).copy()
    probabilities = np.ones(actions.size, dtype=np.float64)
    open_before = commitment.open
    termination: str | None = None

    if commitment.open:
        assert commitment.focal_user is not None
        assert commitment.physical_key is not None
        focal = int(commitment.focal_user)
        mapped = action_for_physical_key(
            slot_tables[focal], commitment.physical_key
        )
        if mapped is not None:
            actions[focal] = int(mapped)
            return RoleDecision(
                actions=actions,
                probabilities=probabilities,
                focal_user=focal,
                trigger="load_option_continuation",
                support_actions=(int(mapped),),
                selected_key=commitment.physical_key,
                option_open_before=True,
                option_open_after_selection=True,
            )
        commitment.close()
        termination = "bound_physical_id_invalid"

    candidates = [
        (int(uid), tuple(int(action) for action in support))
        for uid, support in sorted(eligible_supports.items())
        if len(tuple(support)) >= 2
    ]
    if candidates:
        chosen = int(specialist.rng.integers(0, len(candidates)))
        focal, support = candidates[chosen]
        action, probability = specialist.select_row(
            encoded[focal], support, epsilon=epsilon, informed=informed
        )
        key = physical_key_for_action(slot_tables[focal], int(action))
        if key is None:
            raise RuntimeError("C3 selected a non-physical action")
        actions[focal] = int(action)
        probabilities[focal] = float(probability)
        deferred = int(action) == int(main_actions[focal])
        if not deferred:
            commitment.focal_user = int(focal)
            commitment.physical_key = key
            commitment.remaining = int(horizon)
            commitment.opened_step = int(step_index)
        return RoleDecision(
            actions=actions,
            probabilities=probabilities,
            focal_user=int(focal),
            trigger=(
                "load_support_defer_to_main"
                if deferred
                else "load_support_relocation"
            ),
            support_actions=support,
            selected_key=key,
            option_open_before=open_before,
            option_open_after_selection=not deferred,
            termination=termination,
        )

    return RoleDecision(
        actions=actions,
        probabilities=probabilities,
        focal_user=None,
        trigger="empty_load_support_main_fallback",
        support_actions=(),
        selected_key=None,
        option_open_before=open_before,
        option_open_after_selection=False,
        termination=termination,
    )


def advance_option_after_execution(
    commitment: OptionCommitment,
    *,
    focal_served: bool,
    done: bool,
) -> str | None:
    """Advance exactly one executed hold and close explicitly on termination."""

    if not commitment.open:
        return None
    if not focal_served:
        commitment.close()
        return "realised_service_failure"
    commitment.remaining -= 1
    if done:
        commitment.close()
        return "episode_end"
    if commitment.remaining <= 0:
        commitment.close()
        return "horizon_exhausted"
    return None
