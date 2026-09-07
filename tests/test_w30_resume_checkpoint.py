"""W-30 — episode-boundary resume state is exact and public.

These tests intentionally use a tiny scripted environment.  The production
ephemeris is covered by the W-17/W-18 tests; this file is about the state
boundary between two trainer processes, where a many-hour run must resume
without changing the policy trajectory.
"""

from __future__ import annotations

import copy

import numpy as np
import pytest

from mcrl.env.action_contract import CONTRACT_STATE_DIM
from mcrl.env.step_types import ActionMask, RewardComponents, StepResult, UserState
from mcrl.runtime.replay_buffer import ReplayBuffer
from mcrl.runtime.trainer_spec import TrainerConfig

torch = pytest.importorskip("torch")
from mcrl.algorithms.modqn import MODQNTrainer


class _ResumeEnv:
    """Small deterministic environment with persistent state outside reset."""

    num_beams_total = 2

    class _Config:
        num_users = 1
        steps_per_episode = 2

    config = _Config()

    def __init__(self) -> None:
        self._step = 0
        self._persistent_rng = np.random.default_rng(8128)

    def _states(self) -> list[UserState]:
        return [
            UserState(
                access_vector=np.zeros(2, dtype=np.float64),
                channel_quality=np.full(2, 0.5, dtype=np.float64),
                beam_offsets=np.zeros(2, dtype=np.float64),
                beam_loads=np.zeros(2, dtype=np.float64),
                contract_fields=np.zeros(CONTRACT_STATE_DIM, dtype=np.float32),
            )
        ]

    def _masks(self) -> list[ActionMask]:
        return [ActionMask(np.array([True, True], dtype=bool))]

    def reset(self, _env_rng, _mobility_rng):
        self._step = 0
        # This draw is deliberately owned by the environment, not by the
        # trainer RNGs.  Resume must restore it through the public seam.
        self._persistent_rng.random()
        return self._states(), self._masks(), None

    def step(self, actions, _env_rng) -> StepResult:
        self._step += 1
        draw = float(self._persistent_rng.random())
        served = int(actions[0]) >= 0
        reward = RewardComponents(
            r1_system_ee_contribution=draw + (1.0 if served else 0.0),
            r1_throughput=draw,
            r2_handover=0.0,
            r3_load_balance=0.0,
        )
        return StepResult(
            time_s=float(self._step),
            step_index=self._step,
            done=self._step >= self.config.steps_per_episode,
            user_states=self._states(),
            action_masks=self._masks(),
            rewards=[reward],
        )

    def training_state_dict(self):
        return {
            "persistent_rng_state": copy.deepcopy(
                self._persistent_rng.bit_generator.state
            )
        }

    def load_training_state_dict(self, state):
        if not isinstance(state, dict):
            raise TypeError("environment training state must be a mapping")
        rng = np.random.default_rng()
        rng.bit_generator.state = copy.deepcopy(state["persistent_rng_state"])
        self._persistent_rng = rng


def _config(*, episodes: int = 4) -> TrainerConfig:
    return TrainerConfig(
        hidden_layers=(8,),
        learning_rate=0.003,
        discount_factor=0.9,
        batch_size=1,
        replay_capacity=32,
        episodes=episodes,
        target_update_every_episodes=2,
        epsilon_decay_episodes=3,
    )


def _trainer() -> MODQNTrainer:
    return MODQNTrainer(
        _ResumeEnv(),
        _config(),
        train_seed=101,
        env_seed=202,
        mobility_seed=303,
    )


def _network_state(trainer: MODQNTrainer):
    return [
        {
            key: value.detach().cpu().clone()
            for key, value in net.state_dict().items()
        }
        for net in trainer.q_nets
    ]


def test_replay_state_round_trips_fifo_and_rejects_incompatible_payloads():
    source = ReplayBuffer(2)
    for value in (1.0, 2.0, 3.0):
        source.push(
            np.array([value]),
            int(value),
            np.array([value, -value, 0.0]),
            np.array([value + 1.0]),
            np.array([True, False]),
            np.array([True, True]),
            False,
        )

    state = source.state_dict()
    restored = ReplayBuffer(2)
    restored.load_state_dict(state)
    assert len(restored) == 2
    batch = restored.sample(2, np.random.default_rng(0))
    assert sorted(batch[0].reshape(-1).tolist()) == [2.0, 3.0]

    with pytest.raises(ValueError, match="capacity"):
        ReplayBuffer(3).load_state_dict(state)
    broken = copy.deepcopy(state)
    broken["buffer"].append(broken["buffer"][0])
    with pytest.raises(ValueError, match="capacity"):
        restored.load_state_dict(broken)


def test_training_state_resume_matches_uninterrupted_training():
    uninterrupted = _trainer()
    full_logs = uninterrupted.train(progress_every=0)
    full_networks = _network_state(uninterrupted)
    full_targets = _network_state(
        type("TargetView", (), {"q_nets": uninterrupted.target_nets})()
    )

    interrupted = _trainer()
    captured: dict[str, object] = {}

    def stop_after_first(log):
        captured["log"] = log
        captured["state"] = interrupted.training_state_dict()
        raise RuntimeError("intentional interruption at episode boundary")

    with pytest.raises(RuntimeError, match="intentional interruption"):
        interrupted.train(progress_every=0, episode_callback=stop_after_first)

    resumed = _trainer()
    resumed.load_training_state_dict(captured["state"])
    resumed_logs = resumed.train(
        progress_every=0,
        start_episode=1,
        initial_logs=[captured["log"]],
    )

    assert resumed_logs == full_logs
    for actual, expected in zip(_network_state(resumed), full_networks):
        for key in expected:
            assert torch.equal(actual[key], expected[key]), key
    for actual, expected in zip(
        _network_state(type("TargetView", (), {"q_nets": resumed.target_nets})()),
        full_targets,
    ):
        for key in expected:
            assert torch.equal(actual[key], expected[key]), key


def test_train_rejects_inconsistent_resume_log_boundary():
    trainer = _trainer()
    with pytest.raises(ValueError, match="start_episode"):
        trainer.train(progress_every=0, start_episode=1)
    with pytest.raises(TypeError, match="initial_logs"):
        trainer.train(
            progress_every=0,
            start_episode=1,
            initial_logs=[object()],
        )
