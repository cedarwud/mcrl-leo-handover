"""B0 D-3 — the headline curve must be the objective training actually uses.

**The defect.**  ``MODQNTrainer.train`` computed
``scalar = scalarize_objectives(avg_reward, cfg.objective_weights)`` from the
**uncalibrated** mean reward and logged it as ``EpisodeLog.scalar_reward``,
while training pushes ``apply_reward_calibration(reward_vec, cfg)`` into
replay.  With ``REWARD_SCALES = (2029238.43…, 1.0, 6.0)`` the uncalibrated
``ω₁r₁`` term is ~4.1e5 times ``ω₃r₃`` and ~7.6e6 times ``ω₂r₂``
(``trainer_spec.py:95-98``), so the logged curve is numerically ``0.5·r1``:
``r2`` and ``r3`` move it by about one part in 10⁶.  Every judgement ever made
from that curve saw one head of three.

**The fix.**  Log the **calibrated** scalar as the headline
(``scalar_reward_calibrated``), keep the old number under a clearly
deprecated name (``scalar_reward_uncalibrated_deprecated``) so old runs stay
comparable, and carry all three **calibrated** head means in the same record
so the curve can never again hide two of them.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.runtime.objective_math import (
    apply_reward_calibration,
    scalarize_objectives,
)
from mcrl.runtime.trainer_spec import EpisodeLog, TrainerConfig

from _fake_env import ScriptedEnv

NUM_BEAMS = 8
STEPS = 3


def _logs() -> tuple[list[EpisodeLog], TrainerConfig]:
    script = np.ones((STEPS, 2, NUM_BEAMS), dtype=bool)
    env = ScriptedEnv(script, num_beams=NUM_BEAMS, steps_per_episode=STEPS)
    config = TrainerConfig(
        batch_size=10_000,  # keep update() from firing; this is about logging
        episodes=2,
        epsilon_start=0.0,
        epsilon_end=0.0,
        epsilon_decay_episodes=1,
    )
    trainer = MODQNTrainer(env, config)
    return list(trainer.train()), config


# -- the headline scalar --------------------------------------------------


def test_the_logged_headline_scalar_is_the_calibrated_combination():
    """**This is D-3.**  It must equal Σ ωⱼ·rⱼ/cⱼ, not Σ ωⱼ·rⱼ."""
    logs, config = _logs()
    assert logs
    for log in logs:
        raw = np.array([log.r1_mean, log.r2_mean, log.r3_mean], dtype=np.float64)
        expected = scalarize_objectives(
            apply_reward_calibration(raw, config), config.objective_weights
        )
        assert log.scalar_reward_calibrated == pytest.approx(expected, rel=1e-12)


def test_the_headline_scalar_is_built_from_the_logged_calibrated_means():
    """Internal consistency: the two calibrated surfaces cannot drift apart."""
    logs, config = _logs()
    for log in logs:
        heads = (
            log.r1_mean_calibrated,
            log.r2_mean_calibrated,
            log.r3_mean_calibrated,
        )
        expected = sum(
            weight * head for weight, head in zip(config.objective_weights, heads)
        )
        assert log.scalar_reward_calibrated == pytest.approx(expected, rel=1e-12)


def test_the_old_uncalibrated_number_survives_under_a_deprecated_name():
    """Old runs stay comparable; the name says not to read it as the headline."""
    logs, config = _logs()
    for log in logs:
        raw = np.array([log.r1_mean, log.r2_mean, log.r3_mean], dtype=np.float64)
        assert log.scalar_reward_uncalibrated_deprecated == pytest.approx(
            scalarize_objectives(raw, config.objective_weights), rel=1e-12
        )
    assert "deprecated" in "".join(
        f.name for f in dataclasses.fields(EpisodeLog)
    ), "the old field must be renamed, not silently repurposed"
    assert not any(
        f.name == "scalar_reward" for f in dataclasses.fields(EpisodeLog)
    ), "the ambiguous name must not survive as a field"


def test_the_two_scalars_really_are_different_numbers():
    """Teeth: with calibration on, the uncalibrated scalar is ~0.5*r1 alone."""
    logs, config = _logs()
    assert config.reward_calibration_enabled
    for log in logs:
        assert log.scalar_reward_calibrated != pytest.approx(
            log.scalar_reward_uncalibrated_deprecated, rel=1e-6
        )


# -- the three head means, in the record ----------------------------------


def test_all_three_calibrated_head_means_are_in_the_log_record():
    """The curve can never again hide two heads of three."""
    logs, config = _logs()
    names = {f.name for f in dataclasses.fields(EpisodeLog)}
    for name in ("r1_mean_calibrated", "r2_mean_calibrated", "r3_mean_calibrated"):
        assert name in names

    for log in logs:
        raw = np.array([log.r1_mean, log.r2_mean, log.r3_mean], dtype=np.float64)
        calibrated = apply_reward_calibration(raw, config)
        record = dataclasses.asdict(log)  # this is exactly what is serialised
        for index, name in enumerate(
            ("r1_mean_calibrated", "r2_mean_calibrated", "r3_mean_calibrated")
        ):
            assert record[name] == pytest.approx(float(calibrated[index]), rel=1e-12)


def test_the_serialised_record_carries_both_scalars_and_both_scalings():
    """B17 Q2 needs ωⱼ/cⱼ, which needs both scalings present in one row."""
    logs, _ = _logs()
    record = dataclasses.asdict(logs[0])
    for name in (
        "scalar_reward_calibrated",
        "scalar_reward_uncalibrated_deprecated",
        "r1_mean",
        "r2_mean",
        "r3_mean",
        "r1_mean_calibrated",
        "r2_mean_calibrated",
        "r3_mean_calibrated",
    ):
        assert name in record, f"{name} is missing from the serialised episode log"
