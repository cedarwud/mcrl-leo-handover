"""Real ``TrainerEnvironment`` backend for the fail-closed C3 H3 adapter.

This module is an operational bridge only.  It rebuilds each pre-outcome
branch from the frozen physical-action prefix, runs the deployed masked-greedy
scalarized Main reference policy for every non-focal user, forces one focal
physical association, and converts the resulting committed step into the
complete evidence expected by :mod:`c3_h3_runtime_adapter`.

It does not select a C3 candidate, reveal a formal seed, route C3 experience
to Main, or evaluate a realised post-selection outcome.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STAGE0 = HERE.parent / "catfish-stage0"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STAGE0))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

import c3_h3_runtime_adapter as h3  # noqa: E402
import run_c3_stage0 as legacy  # noqa: E402
from mcrl.env.action_contract import (  # noqa: E402
    HandoverClass,
    NO_OP_ACTION,
    NUM_ACTIONS,
)
from mcrl.env.link_budget import pa_efficiency, supply_power_w  # noqa: E402


DEFAULT_OBJECTIVE_WEIGHTS = (0.5, 0.3, 0.2)
"""Objective weights embedded in the corrected Main checkpoint/config."""

MAIN_BEHAVIOR_WEIGHTS = DEFAULT_OBJECTIVE_WEIGHTS
"""Deployed Main comparator weights embedded in the corrected checkpoint."""


@dataclass
class TrainerH3Branch:
    """One freshly replayed, mutable forecast branch."""

    wrapped: Any
    env_rng: np.random.Generator
    states: Sequence[Any]
    masks: Sequence[Any]
    observation: Any
    fingerprint_sha256: str
    focal_user_id: int
    next_interval: int = 0
    forecast_rng: np.random.Generator | None = None


def _physical_id(value: tuple[int, int] | None) -> tuple[int, int] | None:
    if value is None:
        return None
    return int(value[0]), int(value[1])


def _event(value: HandoverClass) -> Any:
    if value is HandoverClass.NONE:
        return h3.EventClass.NONE
    if value is HandoverClass.INTRA_SATELLITE:
        return h3.EventClass.PHI1
    if value is HandoverClass.INTER_SATELLITE:
        return h3.EventClass.PHI2
    raise RuntimeError(f"unknown handover class: {value!r}")


def _power_snapshot(outcome: Any, physics: Any) -> Any:
    """Build evidence from the actual radiating-beam vector, not totals alone."""

    radiated = np.asarray(outcome.radiating.power_w, dtype=np.float64)
    efficiency = pa_efficiency(
        radiated,
        max_efficiency=physics.pa_max_efficiency,
        saturation_power_w=physics.pa_saturation_power_w,
    )
    supply = supply_power_w(radiated, efficiency)
    keys = tuple(
        (int(norad), int(cell))
        for norad, cell in zip(
            outcome.radiating.norad_ids.tolist(),
            outcome.radiating.cell_ids.tolist(),
            strict=True,
        )
    )
    if len(keys) != len(set(keys)) or len(keys) != int(supply.size):
        raise RuntimeError("radiating-beam power vector has duplicate or missing keys")
    supply_by_beam = {
        key: float(value) for key, value in zip(keys, supply.tolist(), strict=True)
    }
    counts = Counter(key[0] for key in keys)
    independently_fixed = (
        h3.core.CIRCUIT_POWER_PER_BEAM_W * len(keys)
        + h3.core.BASEBAND_POWER_PER_SATELLITE_W * len(counts)
    )
    independently_total = independently_fixed + float(np.sum(supply))
    return h3.PowerSnapshot(
        supply_power_w_by_beam=supply_by_beam,
        radiating_beams_by_satellite=dict(sorted(counts.items())),
        reported_fixed_power_w=float(outcome.fixed_power_w),
        reported_system_power_w=float(outcome.system_power_w),
        pa_identity_residual_w=float(outcome.system_power_w) - independently_total,
    )


class TrainerEnvironmentH3Backend:
    """Execute H3 forecasts through fresh canonical environment replays."""

    def __init__(
        self,
        archive: Any,
        trainer: Any,
        *,
        expected_user_count: int = 100,
        objective_weights: Sequence[float] = DEFAULT_OBJECTIVE_WEIGHTS,
    ) -> None:
        weights = tuple(float(value) for value in objective_weights)
        if weights != DEFAULT_OBJECTIVE_WEIGHTS:
            raise ValueError(
                "C3 H3 backend requires corrected Main checkpoint weights "
                f"{DEFAULT_OBJECTIVE_WEIGHTS}"
            )
        if type(expected_user_count) is not int or expected_user_count < 1:
            raise ValueError("expected user count must be a positive exact integer")
        # ``_reconstruct_anchor`` is the frozen 100-user legacy seam.  A
        # caller cannot safely ask this backend to certify another population:
        # the replay would still construct 100 slot tables while frame
        # validation would use the caller's count.
        if expected_user_count != legacy.USERS:
            raise ValueError(
                "C3 H3 backend is frozen to the legacy 100-user environment"
            )
        configured = tuple(float(value) for value in trainer.config.objective_weights)
        if configured != weights:
            raise ValueError(
                f"trainer objective weights drifted: expected {weights}, got {configured}"
            )
        self.archive = archive
        self.trainer = trainer
        self.expected_user_count = expected_user_count
        self.objective_weights = weights

    def replay_prefix(self, anchor: h3.PreOutcomeAnchor) -> TrainerH3Branch:
        if anchor.checkpoint_sha256 != legacy.EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("C3 H3 anchor checkpoint does not match frozen Main")
        # The frozen H3 campaign censuses steps 0..7 so all three forecast
        # intervals remain inside the ten-step episode.  Without this guard,
        # StepEnvironment accepts a post-terminal call and would produce a
        # plausible-looking extra row instead of a three-interval forecast.
        if (
            type(anchor.step_index) is not int
            or anchor.step_index not in legacy.ANCHOR_STEPS
        ):
            raise RuntimeError(
                "C3 H3 anchor step is outside the three-interval episode window"
            )
        if type(anchor.evaluation_seed) is not int or anchor.evaluation_seed < 0:
            raise RuntimeError("C3 H3 evaluation seed must be a nonnegative integer")
        if (
            type(anchor.focal_user_id) is not int
            or not 0 <= anchor.focal_user_id < self.expected_user_count
        ):
            raise RuntimeError("C3 H3 focal user ID is outside the frozen user range")
        if len(anchor.prefix_actions) != anchor.step_index:
            raise RuntimeError("C3 H3 prefix length does not match anchor step")
        prefix: list[np.ndarray] = []
        for interval, actions in enumerate(anchor.prefix_actions):
            if len(actions) != self.expected_user_count:
                raise RuntimeError(
                    f"C3 H3 prefix h{interval} does not contain every user action"
                )
            for action in actions:
                if type(action) is not int:
                    raise RuntimeError(
                        f"C3 H3 prefix h{interval} action must be an exact integer"
                    )
                if action != NO_OP_ACTION and not 0 <= action < NUM_ACTIONS:
                    raise RuntimeError(
                        f"C3 H3 prefix h{interval} action {action} is out of range"
                    )
            prefix.append(np.asarray(actions, dtype=np.int32))
        replayed = legacy._reconstruct_anchor(
            self.archive,
            seed=anchor.evaluation_seed,
            prefix_actions=prefix,
        )
        if int(replayed["observation"].step_index) != anchor.step_index:
            raise RuntimeError("C3 H3 replayed anchor step index drifted")
        return TrainerH3Branch(
            wrapped=replayed["wrapped"],
            env_rng=replayed["env_rng"],
            states=replayed["states"],
            masks=replayed["masks"],
            observation=replayed["observation"],
            fingerprint_sha256=str(replayed["fingerprint_sha256"]),
            focal_user_id=anchor.focal_user_id,
        )

    def fingerprint(self, branch: TrainerH3Branch) -> str:
        if type(branch) is not TrainerH3Branch:
            raise ValueError("C3 H3 backend received a foreign branch object")
        return branch.fingerprint_sha256

    def _main_actions(self, branch: TrainerH3Branch) -> np.ndarray:
        encoded = self.trainer.encode_states(list(branch.states))
        masks = np.stack([row.mask for row in branch.masks])
        q_values = self.trainer.scalarized_q_values(
            encoded,
            objective_weights=MAIN_BEHAVIOR_WEIGHTS,
        )
        return np.asarray(
            legacy.masked_greedy_actions(q_values, masks), dtype=np.int32
        )

    def roll_forward(
        self,
        branch: TrainerH3Branch,
        focal_physical_id: tuple[int, int],
        interval: int,
        forecast_rng: np.random.Generator,
    ) -> h3.ForecastFrame:
        if type(branch) is not TrainerH3Branch:
            raise ValueError("C3 H3 backend received a foreign branch object")
        if type(interval) is not int or interval != branch.next_interval:
            raise RuntimeError("C3 H3 intervals must be sequential within each branch")
        if not isinstance(forecast_rng, np.random.Generator):
            raise ValueError("C3 H3 forecast RNG must be a numpy Generator")
        focal_id = h3.validate_physical_id(
            focal_physical_id, field="C3 H3 focal physical ID"
        )
        environment = branch.wrapped.environment
        if interval == 0:
            if branch.forecast_rng is not None:
                raise RuntimeError("C3 H3 branch forecast RNG was already installed")
            actual_mobility_rng = environment._mobility_rng
            if not isinstance(actual_mobility_rng, np.random.Generator):
                raise RuntimeError("C3 H3 replay has no canonical mobility RNG")
            if actual_mobility_rng is forecast_rng or (
                h3.rng_state_sha256(actual_mobility_rng)
                == h3.rng_state_sha256(forecast_rng)
            ):
                raise RuntimeError(
                    "C3 H3 forecast RNG must be object/state-independent from mobility"
                )
            branch.forecast_rng = forecast_rng
            environment._mobility_rng = forecast_rng
            environment.physics = replace(environment.physics, fading_enabled=False)
        elif branch.forecast_rng is not forecast_rng or environment._mobility_rng is not forecast_rng:
            raise RuntimeError("C3 H3 branch changed forecast RNG object")
        if environment.physics.fading_enabled:
            raise RuntimeError("C3 H3 deterministic forecast must keep fading disabled")

        actions = self._main_actions(branch)
        focal_user = branch.focal_user_id
        table = branch.observation.candidates.slot_tables[focal_user]
        focal_action = legacy._action_for_key(table, focal_id)
        if focal_action is None:
            raise RuntimeError("C3 H3 committed physical association disappeared")
        actions[focal_user] = int(focal_action)
        physical_actions = tuple(
            _physical_id(value)
            for value in legacy._physical_key_rows(actions, branch.observation)
        )

        preview = environment.evaluate_actions(actions, branch.env_rng)
        result = branch.wrapped.step(actions, branch.env_rng)
        if result.done and interval < h3.H3_INTERVALS - 1:
            raise RuntimeError(
                "C3 H3 forecast reached episode end before three intervals"
            )
        outcome = branch.wrapped.last_outcome
        parity, parity_error = legacy._preview_parity(preview, outcome)
        if not parity:
            raise RuntimeError(f"C3 H3 preview/commit parity failed: {parity_error}")

        served = tuple(int(value) for value in np.flatnonzero(outcome.resolution.served))
        active_beams = tuple(
            sorted(
                (int(key[0]), int(key[1]))
                for key in outcome.resolution.active_beams
            )
        )
        loads = {
            (int(key[0]), int(key[1])): int(value)
            for key, value in outcome.resolution.eligible_load_by_beam.items()
        }
        nonfocal = {
            uid: physical_actions[uid]
            for uid in range(self.expected_user_count)
            if uid != focal_user
        }
        realised_focal = (
            None
            if not bool(outcome.resolution.served[focal_user])
            else (
                int(outcome.resolution.serving_satellite[focal_user]),
                int(outcome.resolution.serving_cell[focal_user]),
            )
        )
        frame = h3.ForecastFrame(
            focal_action=focal_id,
            nonfocal_actions=nonfocal,
            served_users=served,
            active_beams=active_beams,
            active_satellites=tuple(sorted({key[0] for key in active_beams})),
            loads=loads,
            r3_total=-sum(value * value for value in loads.values()),
            power=_power_snapshot(outcome, environment.physics),
            event=_event(outcome.handovers[focal_user]),
            hold_valid=realised_focal == focal_id,
            service=bool(outcome.resolution.served[focal_user]),
        )
        branch.states = result.user_states
        branch.masks = result.action_masks
        branch.observation = outcome.observation
        branch.next_interval += 1
        return frame
__all__ = [
    "DEFAULT_OBJECTIVE_WEIGHTS",
    "MAIN_BEHAVIOR_WEIGHTS",
    "TrainerEnvironmentH3Backend",
    "TrainerH3Branch",
]
