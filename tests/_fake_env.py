"""A scriptable environment double for W-16 trainer tests.

Not an implementation of the SDD environment — W-02/W-03 own that.  This
double only replays a caller-supplied mask/done script through the real
``mcrl.env.step_types`` containers so the trainer's decision and
replay-write paths can be exercised end to end.

It honours one production obligation from
``mcrl.env.action_contract``: a user whose action is ``NO_OP_ACTION`` is
recorded as unserved and contributes nothing to beam load.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mcrl.env.action_contract import (
    CONTRACT_STATE_DIM,
    NO_OP_ACTION,
)
from mcrl.env.step_types import (
    ActionMask,
    RewardComponents,
    StepResult,
    UserState,
)


@dataclass
class _EnvConfig:
    num_users: int
    steps_per_episode: int


@dataclass
class _ChannelConfig:
    bandwidth_hz: float = 500e6


class ScriptedEnv:
    """Replays a per-step boolean mask matrix supplied by the test.

    ``mask_script[t]`` has shape ``(num_users, num_beams)`` and is the mask
    handed out *before* the action at step ``t``.  ``reset`` serves
    ``mask_script[0]``; ``step`` at index ``t`` serves ``mask_script[t+1]``
    as the successor mask, or an all-False matrix past the end.
    """

    def __init__(
        self,
        mask_script: np.ndarray,
        *,
        num_beams: int,
        steps_per_episode: int | None = None,
    ) -> None:
        self._script = np.asarray(mask_script, dtype=bool)
        if self._script.ndim != 3:
            raise ValueError("mask_script must have shape (T, U, B)")
        self.num_beams_total = int(num_beams)
        num_users = int(self._script.shape[1])
        self.config = _EnvConfig(
            num_users=num_users,
            steps_per_episode=(
                int(self._script.shape[0])
                if steps_per_episode is None
                else int(steps_per_episode)
            ),
        )
        self.channel_config = _ChannelConfig()
        self._t = 0
        self.observed_actions: list[np.ndarray] = []

    # -- helpers ---------------------------------------------------------

    def _mask_at(self, index: int) -> np.ndarray:
        if index < len(self._script):
            return self._script[index]
        return np.zeros(
            (self.config.num_users, self.num_beams_total), dtype=bool
        )

    def _states(self) -> list[UserState]:
        n = self.num_beams_total
        return [
            UserState(
                access_vector=np.zeros(n, dtype=np.float64),
                channel_quality=np.full(n, 0.5, dtype=np.float64),
                beam_offsets=np.zeros(n, dtype=np.float64),
                beam_loads=np.zeros(n, dtype=np.float64),
                # SDD §4A.6's 13-dim block; zeros are fine for a double whose
                # job is to script masks, but it must be PRESENT — the encoder
                # refuses to emit a short state vector.
                contract_fields=np.zeros(CONTRACT_STATE_DIM, dtype=np.float32),
            )
            for _ in range(self.config.num_users)
        ]

    # -- StepEnvironment surface ----------------------------------------

    def reset(self, _env_rng, _mobility_rng):
        self._t = 0
        masks = [ActionMask(mask=row.copy()) for row in self._mask_at(0)]
        return self._states(), masks, None

    def step(self, actions, _env_rng) -> StepResult:
        actions = np.asarray(actions)
        self.observed_actions.append(actions.copy())

        served = actions != NO_OP_ACTION
        beam_loads = np.zeros(self.num_beams_total, dtype=np.float64)
        for action in actions[served].tolist():
            beam_loads[int(action)] += 1.0

        next_masks = [
            ActionMask(mask=row.copy()) for row in self._mask_at(self._t + 1)
        ]
        rewards = [
            RewardComponents(
                r1_throughput=1.0 if served[uid] else 0.0,
                r2_handover=0.0,
                r3_load_balance=0.0,
            )
            for uid in range(self.config.num_users)
        ]
        self._t += 1
        done = self._t >= self.config.steps_per_episode
        return StepResult(
            time_s=float(self._t),
            step_index=self._t,
            done=done,
            user_states=self._states(),
            action_masks=next_masks,
            rewards=rewards,
            beam_throughputs=np.zeros(self.num_beams_total, dtype=np.float64),
            active_beam_mask=beam_loads > 0.0,
            beam_transmit_power_w=np.zeros(
                self.num_beams_total, dtype=np.float64
            ),
        )
