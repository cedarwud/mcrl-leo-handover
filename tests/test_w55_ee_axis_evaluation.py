"""W-55 -- deployed three-Q ratio-of-sums EE evaluation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairwiseTrainer
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.ephemeris import TRAIN, BlockAlternatingSplit, EpisodeStartSampler
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.runtime.ee_axis_calibration import calibrate_ee_axis_pilot
from mcrl.runtime.ee_axis_evaluation import (
    EEAxisEvaluationError,
    evaluate_ee_axis_episode,
)
from mcrl.runtime.trainer_env import TrainerEnvironment


_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(not _ARCHIVE.is_dir(), reason="TLE archive absent")


def _trainer():
    calibration = calibrate_ee_axis_pilot(
        calibration_seed=1,
        useful_bits=1000.0,
        energy_j=10.0,
        steps=2,
        users=4,
    )
    return EEAxisPairwiseTrainer(
        calibration.pairwise_config(learning_rate=0.001, hidden_layers=(8,)),
        train_seed=7,
    )


def _environment(field: KeyedFadingField | None):
    archive = TleArchive(_ARCHIVE)
    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=4)),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    return TrainerEnvironment(StepEnvironment(driver, fading_field=field), sampler)


def _snapshot(trainer):
    return [
        {name: value.detach().clone() for name, value in network.state_dict().items()}
        for network in trainer.q_nets
    ]


@requires_archive
def test_evaluation_is_reproducible_ratio_of_sums_and_does_not_train():
    trainer = _trainer()
    before = _snapshot(trainer)
    first_field = KeyedFadingField.from_components("w55", 101)
    second_field = KeyedFadingField.from_components("w55", 101)
    first = evaluate_ee_axis_episode(
        trainer,
        _environment(first_field),
        env_rng=np.random.default_rng(11),
        mobility_rng=np.random.default_rng(12),
        evaluation_seed=101,
        policy_label="F111-smoke",
    )
    second = evaluate_ee_axis_episode(
        trainer,
        _environment(second_field),
        env_rng=np.random.default_rng(11),
        mobility_rng=np.random.default_rng(12),
        evaluation_seed=101,
        policy_label="F111-smoke",
    )
    assert first.payload() == second.payload()
    assert first.ratio_of_sums_ee_bits_per_j == pytest.approx(
        first.total_bits / first.total_energy_j
    )
    assert first.decision_count == first.steps * first.users
    assert first.served_fraction + first.outage_fraction == pytest.approx(1.0)
    after = _snapshot(trainer)
    assert all(
        torch.equal(before[index][name], after[index][name])
        for index in range(3)
        for name in before[index]
    )


@requires_archive
def test_evaluation_rejects_unkeyed_environment():
    with pytest.raises(EEAxisEvaluationError, match="keyed common fading"):
        evaluate_ee_axis_episode(
            _trainer(),
            _environment(None),
            env_rng=np.random.default_rng(11),
            mobility_rng=np.random.default_rng(12),
            evaluation_seed=101,
            policy_label="invalid",
        )
