"""W-18 — the frozen trainer driving the real environment.

The trainer was ported byte-for-byte and its environment contract is
implicit: it is whatever attributes and call signatures the ported code
happens to touch.  An adapter that satisfies four of the five is not a
partial success, it is an ``AttributeError`` nine hundred episodes in — so
the contract is enumerated here as well as exercised end to end.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.ephemeris import TRAIN, BlockAlternatingSplit, EpisodeStartSampler
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.step_types import ActionMask, StepResult, UserState
from mcrl.env.tle import TleArchive
from mcrl.errors import MCRLContractError
from mcrl.runtime.trainer_env import TrainerEnvironment, TrainerEnvironmentConfig

torch = pytest.importorskip("torch")

_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
USERS = 8


@pytest.fixture(scope="module")
def adapter():
    archive = TleArchive(_ARCHIVE)
    driver = ScenarioDriver(
        archive, ScenarioConfig(mobility=MobilityConfig(num_users=USERS))
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    return TrainerEnvironment(StepEnvironment(driver), sampler)


# -- the contract, enumerated ---------------------------------------------


@requires_archive
def test_it_exposes_everything_the_ported_trainer_touches(adapter):
    """Five attributes and two methods.  Missing one fails at episode N."""
    assert adapter.config.num_users == USERS
    assert adapter.config.steps_per_episode >= 1
    assert adapter.num_users == USERS
    assert adapter.num_beams_total == NUM_ACTIONS == 28
    assert callable(adapter.reset)
    assert callable(adapter.step)


def test_the_adapter_config_holds_only_what_the_trainer_reads():
    """P-21: ``StepConfig``'s other fields all have owners elsewhere now."""
    fields = set(TrainerEnvironmentConfig.__dataclass_fields__)
    assert fields == {"num_users", "steps_per_episode"}


@requires_archive
def test_reset_returns_states_masks_and_the_full_observation(adapter):
    states, masks, observation = adapter.reset(
        np.random.default_rng(0), np.random.default_rng(1)
    )
    assert len(states) == USERS and isinstance(states[0], UserState)
    assert len(masks) == USERS and isinstance(masks[0], ActionMask)
    assert masks[0].mask.shape == (NUM_ACTIONS,)
    # The third element is discarded by the trainer but not by a run logger.
    assert observation.state_matrix.shape == (USERS, 112)


@requires_archive
def test_step_returns_the_container_the_trainer_destructures(adapter):
    _states, masks, _obs = adapter.reset(
        np.random.default_rng(0), np.random.default_rng(1)
    )
    actions = np.array(
        [int(np.flatnonzero(m.mask)[0]) for m in masks], dtype=np.int64
    )
    result = adapter.step(actions, np.random.default_rng(2))
    assert isinstance(result, StepResult)
    for attribute in ("rewards", "done", "user_states", "action_masks"):
        assert hasattr(result, attribute)
    assert len(result.rewards) == USERS
    assert result.time_s > 0.0


# -- the epoch is drawn, not chosen ---------------------------------------


@requires_archive
def test_the_epoch_comes_from_the_frozen_sampler(adapter):
    """The one thing the trainer's ``reset`` signature cannot supply.

    It must be a pre-registered draw rather than a value picked here, or the
    episode distribution stops being the one the PREREG froze.
    """
    adapter.reset(np.random.default_rng(11), np.random.default_rng(1))
    epoch = adapter.epoch
    assert epoch.tzinfo is dt.timezone.utc
    assert epoch.date() in set(adapter.sampler.available_dates)

    # A different env_rng draws a different epoch; the same one repeats it.
    adapter.reset(np.random.default_rng(12), np.random.default_rng(1))
    other = adapter.epoch
    adapter.reset(np.random.default_rng(11), np.random.default_rng(1))
    assert adapter.epoch == epoch
    assert other != epoch


@requires_archive
def test_the_two_generators_do_different_jobs(adapter):
    """Fading is ``env_rng``; the users are ``mobility_rng``.

    Holding the mobility stream fixed while changing the environment stream
    must move the SINR and leave the population where it was.  With one
    stream a fading ablation would silently re-seed everybody's position and
    the two effects could never be separated.
    """
    _s, _m, first = adapter.reset(
        np.random.default_rng(5), np.random.default_rng(99)
    )
    positions_a = adapter.environment.driver.user_xy_km.copy()
    sinr_a = first.candidate_sinr.copy()

    _s, _m, second = adapter.reset(
        np.random.default_rng(5), np.random.default_rng(99)
    )
    assert np.array_equal(adapter.environment.driver.user_xy_km, positions_a)
    assert np.array_equal(second.candidate_sinr, sinr_a)

    # Same mobility seed, different environment seed: same users elsewhere in
    # time is not a fair test, so compare the population only.
    adapter.reset(np.random.default_rng(5), np.random.default_rng(1234))
    assert not np.array_equal(
        adapter.environment.driver.user_xy_km, positions_a
    )


# -- the gate --------------------------------------------------------------


@requires_archive
def test_training_is_gated_on_the_open_questions(adapter, monkeypatch):
    """An open question must refuse — that is the gate working.

    Both closed on 2026-08-23, so one is reopened here.  Relying on the
    project's own state would have turned this into a test that passes
    because there is nothing to catch.
    """
    import mcrl.env.service as service

    monkeypatch.setattr(service, "R3_SCALE_IS_FROZEN", False)
    with pytest.raises(MCRLContractError, match="Q-D r3"):
        adapter.assert_ready_to_train()


@requires_archive
def test_with_both_questions_closed_the_adapter_lets_training_start(adapter):
    """The other branch: physics consistent, both questions closed."""
    adapter.assert_ready_to_train()


@requires_archive
def test_the_physics_gate_fires_first_when_the_constants_disagree():
    archive = TleArchive(_ARCHIVE)
    driver = ScenarioDriver(
        archive, ScenarioConfig(mobility=MobilityConfig(num_users=2))
    )
    environment = StepEnvironment(
        driver, physics=PhysicsConfig(segment_start_power_w=2.0)
    )
    split = BlockAlternatingSplit.for_archive(archive)
    broken = TrainerEnvironment(
        environment, EpisodeStartSampler.for_archive(archive, split, TRAIN)
    )
    with pytest.raises(MCRLContractError, match="exceeds p_max"):
        broken.assert_ready_to_train()


@requires_archive
def test_stepping_before_reset_is_refused(adapter):
    fresh = TrainerEnvironment(adapter.environment, adapter.sampler)
    with pytest.raises(MCRLContractError, match="not been reset"):
        fresh.step(np.zeros(USERS, dtype=np.int64), np.random.default_rng(0))
    with pytest.raises(MCRLContractError, match="no step has been taken"):
        _ = fresh.last_outcome


# -- end to end ------------------------------------------------------------


@requires_archive
def test_the_real_trainer_runs_real_episodes(adapter):
    """The whole point: the ported trainer, unmodified, on real ephemeris."""
    from mcrl.algorithms.modqn import MODQNTrainer
    from mcrl.runtime.trainer_spec import TrainerConfig

    config = TrainerConfig(episodes=2, batch_size=8, replay_capacity=256)
    trainer = MODQNTrainer(
        adapter, config, train_seed=0, env_seed=1, mobility_seed=2
    )
    logs = trainer.train()

    assert len(logs) == 2
    for log in logs:
        assert log.replay_size > 0, "transitions must reach replay"
        assert np.isfinite(log.scalar_reward)
        assert np.isfinite(log.r1_mean)
        # r1 is an ENERGY EFFICIENCY (3.25), so it is positive and large in
        # bit/J -- a throughput here would be ~1e8 too, which is why the
        # field it comes from had to stop being called r1_throughput (P-20).
        assert log.r1_mean > 0.0
        assert log.r2_mean <= 0.0
        assert log.r3_mean <= 0.0

    diagnostics = trainer.get_masking_diagnostics()
    assert diagnostics["decision_steps_seen"] == 2 * USERS * 10


@requires_archive
def test_r1_reaching_the_trainer_is_the_energy_efficiency_not_the_throughput(
    adapter,
):
    """PATCH P-20's whole point, checked where it would actually bite.

    Both quantities are order 1e7-1e8 here, so a mix-up would not look
    wrong — it would just silently optimise the wrong objective.
    """
    from mcrl.algorithms.modqn import MODQNTrainer
    from mcrl.runtime.trainer_spec import TrainerConfig

    _states, masks, _obs = adapter.reset(
        np.random.default_rng(0), np.random.default_rng(1)
    )
    actions = np.array(
        [int(np.flatnonzero(m.mask)[0]) for m in masks], dtype=np.int64
    )
    result = adapter.step(actions, np.random.default_rng(2))
    outcome = adapter.last_outcome

    trainer = MODQNTrainer(
        adapter, TrainerConfig(episodes=1), train_seed=0
    )
    for uid in range(USERS):
        vector = trainer.reward_vector_from_step_result(result, uid)
        assert vector[0] == result.rewards[uid].r1_system_ee_contribution
        assert vector[0] == outcome.reward_matrix[uid, 0]
        if outcome.resolution.served[uid]:
            # The two differ by P^N, which is far from 1.
            assert vector[0] != result.rewards[uid].r1_throughput
            assert result.rewards[uid].r1_throughput == pytest.approx(
                vector[0] * outcome.system_power_w
            )


@requires_archive
def test_a_real_run_produces_all_four_collapse_indicators(adapter):
    """W-28 §1: the numbers B17 Q1 needs must come out of an actual run.

    Asserting the dataclass has the fields is not enough — it would pass
    with the training loop never calling ``compute_collapse_metrics``,
    which is exactly the state the codebase was in until 2026-08-23.  So
    this drives real episodes and checks the values are finite and in
    range, per the rule that a test must put the system into the state it
    guards against rather than wait for it.
    """
    from mcrl.algorithms.modqn import MODQNTrainer
    from mcrl.runtime.collapse_metrics import assert_g3_complete
    from mcrl.runtime.trainer_spec import TrainerConfig

    trainer = MODQNTrainer(
        adapter,
        TrainerConfig(episodes=2, batch_size=8, replay_capacity=256),
        train_seed=0,
        env_seed=1,
        mobility_seed=2,
    )
    logs = trainer.train()
    assert len(logs) == 2

    for log in logs:
        assert_g3_complete(log.collapse_report())
        assert 0.0 <= log.active_beam_count <= adapter.num_beams_total
        assert 0.0 <= log.argmax_agreement <= 1.0
        # q_margin is NORMALISED by the Q range, so it is dimensionless.
        assert 0.0 <= log.q_margin <= 1.0 + 1e-9
        assert 0.0 <= log.q_entropy <= 1.0 + 1e-9
        assert np.isfinite(log.q_margin_raw) and np.isfinite(log.q_range)
        # A raw margin with no divisor recorded would be unauditable.
        assert log.q_range >= log.q_margin_raw - 1e-9

    # Both scalings, and they must actually differ: c_1 is 2.47e6, so a
    # calibrated r1 equal to the raw one would mean calibration never ran.
    for log in logs:
        for raw, calibrated in (
            (log.r1_mean, log.r1_mean_calibrated),
            (log.r3_mean, log.r3_mean_calibrated),
        ):
            if raw != 0.0:
                assert raw != calibrated
