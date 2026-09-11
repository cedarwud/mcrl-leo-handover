"""The seam between :class:`~mcrl.env.step.StepEnvironment` and the trainer.

``MODQNTrainer`` was ported byte-for-byte and its environment contract is
frozen with it.  That contract is small and entirely implicit — the trainer
never declares it — so it is written out here rather than left to be
rediscovered::

    env.config.num_users
    env.config.steps_per_episode
    env.num_beams_total                      -> the flat action width, C = 28
    env.reset(env_rng, mobility_rng) -> (states, masks, diagnostics)
    env.step(actions, env_rng)       -> object with .rewards .done
                                                   .user_states .action_masks

Three things it does **not** carry, and how each is supplied:

**An epoch.**  ``reset`` takes two generators and no time, but a real
episode has to start somewhere on the calendar.  The start is drawn from
:class:`~mcrl.env.ephemeris.EpisodeStartSampler`, whose distribution — date
uniform over the split part's *available* file dates, time-of-day uniform —
is frozen in the PREREG.  So the epoch is not a free choice made here; it
is a pre-registered draw, and drawing it from ``env_rng`` keeps the whole
episode reproducible from the trainer's own seed.

**Two generators, one environment.**  The trainer spawns ``env_rng`` and
``mobility_rng`` from one seed and hands both to ``reset``.  They are kept
apart: ``mobility_rng`` places and moves the users, ``env_rng`` draws the
epoch and the Rician fading.  Separating them means a fading ablation does
not also move the users, which is the only way the two effects can be told
apart afterwards.

**A gate.**  Two things must be true before a training run and neither is
the trainer's to check: the physics constants must be self-consistent
(``p⁰ ≤ p_max``), and Q-D/Q-E must be decided rather than merely frozen.
:meth:`TrainerEnvironment.assert_ready_to_train` runs both.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..env.ephemeris import EpisodeStartSampler
from ..env.step import StepEnvironment, StepObservation, StepOutcome
from ..env.step_types import ActionMask, StepResult, UserState
from ..errors import MCRLContractError


@dataclass(frozen=True)
class TrainerEnvironmentConfig:
    """Exactly the two fields ``MODQNTrainer`` reads off ``env.config``.

    Deliberately **not** ``StepConfig``, which used to hold these plus
    ``phi1``/``phi2``, the mobility model and the mask mode — every one of
    which now has an owner elsewhere.  A second home for a frozen value is
    how the two drift apart, so this carries the two the trainer actually
    reads and derives both rather than storing them again (P-21).
    """

    num_users: int
    steps_per_episode: int

    def __post_init__(self) -> None:
        if self.num_users < 1:
            raise ValueError("num_users must be >= 1")
        if self.steps_per_episode < 1:
            raise ValueError("steps_per_episode must be >= 1")


class TrainerEnvironment:
    """``StepEnvironment`` presented through the trainer's frozen contract."""

    def __init__(
        self,
        environment: StepEnvironment,
        sampler: EpisodeStartSampler,
    ) -> None:
        self.environment = environment
        self.sampler = sampler
        driver = environment.driver
        self.config = TrainerEnvironmentConfig(
            num_users=driver.config.mobility.num_users,
            steps_per_episode=driver.config.steps_per_episode,
        )
        self._last_outcome: StepOutcome | None = None
        self._epoch: dt.datetime | None = None

    # -- gates ------------------------------------------------------------

    def assert_ready_to_train(self) -> None:
        """Both gates, in one place a training entry point cannot skip."""
        from .prereg import assert_ready_to_train as assert_questions_closed

        self.environment.assert_ready_to_train()
        assert_questions_closed()

    # -- episode-boundary resume state -----------------------------------

    def training_state_dict(self) -> dict[str, object]:
        """Delegate the persistent resume seam to ``StepEnvironment``.

        The sampler epoch and the last outcome are episode-local and are
        intentionally omitted: the next call to ``reset`` draws a fresh
        epoch from the trainer's restored environment RNG.  The wrapped
        environment owns the only cross-episode stream, ``_age_rng``.
        """

        method = getattr(self.environment, "training_state_dict", None)
        if not callable(method):
            raise TypeError(
                "wrapped StepEnvironment does not expose training_state_dict"
            )
        state = method()
        if not isinstance(state, Mapping):
            raise TypeError("wrapped environment training state must be a mapping")
        return dict(state)

    def load_training_state_dict(self, state: Mapping[str, object]) -> None:
        """Restore the wrapped environment's persistent resume state."""

        if not isinstance(state, Mapping):
            raise TypeError("TrainerEnvironment training state must be a mapping")
        method = getattr(self.environment, "load_training_state_dict", None)
        if not callable(method):
            raise TypeError(
                "wrapped StepEnvironment does not expose load_training_state_dict"
            )
        method(state)

    def resume_state_dict(self) -> dict[str, object]:
        return self.training_state_dict()

    def load_resume_state_dict(self, state: Mapping[str, object]) -> None:
        self.load_training_state_dict(state)

    # -- the trainer's contract -------------------------------------------

    @property
    def num_users(self) -> int:
        return self.config.num_users

    @property
    def num_beams_total(self) -> int:
        """``C = 28`` — the network's output width, which never changes.

        The trainer uses it for both the action dimension and, through
        ``state_dim_for``, the input width.  It is the candidate-table size
        ``L_w·J_w``, **not** a count of physical beams: those are global
        ``(satellite, cell)`` pairs and there are ``V = 39`` positions per
        satellite.  The ported name is kept because the trainer reads it;
        the distinction is the one ``action_contract`` warns about.
        """
        return NUM_ACTIONS

    @property
    def epoch(self) -> dt.datetime:
        """The epoch the current episode was drawn at.  For the run log."""
        if self._epoch is None:
            raise MCRLContractError("no episode has been started")
        return self._epoch

    def reset(
        self,
        env_rng: np.random.Generator,
        mobility_rng: np.random.Generator,
    ) -> tuple[list[UserState], list[ActionMask], StepObservation]:
        """Draw an epoch, reset, and hand back the step-0 observation.

        The third element is the whole :class:`StepObservation`.  The trainer
        binds it to ``_diag`` and ignores it; a probe or a run logger wants
        the candidate table, the masks and the SINR block, and returning the
        object costs nothing versus rebuilding it.
        """
        self._epoch = self.sampler.draw(env_rng)
        observation = self.environment.reset(
            self._epoch, env_rng, mobility_rng=mobility_rng
        )
        self._last_outcome = None
        return (
            list(observation.user_states),
            _masks(observation),
            observation,
        )

    def step(
        self, actions: np.ndarray, env_rng: np.random.Generator
    ) -> StepResult:
        """One slot, returned in the container the trainer destructures."""
        if self._epoch is None:
            raise MCRLContractError("the environment has not been reset")
        outcome = self.environment.step(actions, env_rng)
        return self._record_outcome(outcome)

    def step_without_user(
        self,
        actions: np.ndarray,
        env_rng: np.random.Generator,
        *,
        focal_user: int,
    ) -> StepResult:
        """Commit one source-only focal-removal slot through the wrapper.

        The deployment-facing :meth:`step` contract is unchanged.  C2 source
        construction uses this explicit seam only after its focal physical
        action is no longer uniquely supported, while every non-focal native
        action remains the caller-supplied action.
        """
        if self._epoch is None:
            raise MCRLContractError("the environment has not been reset")
        outcome = self.environment.step_without_user(
            actions,
            env_rng,
            focal_user=focal_user,
        )
        return self._record_outcome(outcome)

    def _record_outcome(self, outcome: StepOutcome) -> StepResult:
        """Publish one committed outcome through the frozen trainer view."""
        self._last_outcome = outcome
        return StepResult(
            time_s=float(
                (outcome.step_index + 1)
                * self.environment.driver.config.ephemeris.time_step_s
            ),
            step_index=outcome.step_index,
            done=outcome.done,
            user_states=list(outcome.observation.user_states),
            action_masks=_masks(outcome.observation),
            rewards=list(outcome.rewards),
            # B0 D-2: the trainer needs to know who was actually served, or
            # it cannot tell an outage's free ``r2 = 0, r3 = 0`` apart from a
            # served user that happened to score the same.
            served=tuple(bool(flag) for flag in outcome.resolution.served),
        )

    # -- everything the contract discards ---------------------------------

    @property
    def last_outcome(self) -> StepOutcome:
        """The full physics of the step just taken.

        ``StepResult`` carries only what the trainer destructures.  The
        interference split, the radiating set, the realised SINR and rate,
        the consumed power and the diagnostics all live here — a run that
        reported only the reward vector would be unable to say *why* it
        moved.
        """
        if self._last_outcome is None:
            raise MCRLContractError("no step has been taken")
        return self._last_outcome


def _masks(observation: StepObservation) -> list[ActionMask]:
    """Wrap the ``(U, 28)`` boolean block in the per-user container.

    Copied per row on purpose: the trainer stores ``masks[uid].mask`` into
    replay, and a view onto the environment's own array would alias every
    stored transition to whatever the environment last computed.
    """
    return [ActionMask(mask=row.copy()) for row in observation.masks]
