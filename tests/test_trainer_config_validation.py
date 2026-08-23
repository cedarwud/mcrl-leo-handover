"""Fail-loud TrainerConfig validation.

Written fresh rather than ported: the source validator is 1,124 lines and
most of it validates the surfaces W-09 removed, so porting it would have
brought §8's vocabulary back as validation rules.

Every check here exists because the violation fails **silently** otherwise.
"""

from __future__ import annotations

import pytest

from mcrl.errors import MCRLContractError
from mcrl.runtime.trainer_config_validation import (
    VALID_ACTIVATIONS,
    VALID_POLICY_SHARING,
    validate_trainer_config,
)
from mcrl.runtime.trainer_spec import TrainerConfig


def test_the_default_configuration_is_valid():
    validate_trainer_config(TrainerConfig())


def test_the_defaults_are_the_paper_values():
    config = TrainerConfig()
    assert config.hidden_layers == (100, 50, 50)
    assert config.activation == "tanh"
    assert config.discount_factor == 0.9
    assert config.batch_size == 128
    assert config.episodes == 9000
    assert config.objective_weights == (0.5, 0.3, 0.2)
    # W-09 / P-06: the stale REP-004 value of 7000 is gone.
    assert config.epsilon_decay_episodes == 2000


def test_validation_runs_at_construction():
    """A bad config must not survive long enough to start a run."""
    with pytest.raises(MCRLContractError):
        TrainerConfig(discount_factor=0.0)


# -- each check, and the silent failure it prevents -----------------------


def test_weights_that_do_not_sum_to_one_are_refused():
    """They rescale the whole reward; the run just looks worse."""
    with pytest.raises(MCRLContractError, match="must sum to 1"):
        TrainerConfig(objective_weights=(0.5, 0.5, 0.5))
    with pytest.raises(MCRLContractError, match="must sum to 1"):
        TrainerConfig(objective_weights=(0.2, 0.2, 0.2))
    # A different but valid convex combination is fine.
    validate_trainer_config(TrainerConfig(objective_weights=(1.0, 0.0, 0.0)))


def test_negative_weights_are_refused():
    with pytest.raises(MCRLContractError, match="non-negative"):
        TrainerConfig(objective_weights=(1.5, -0.5, 0.0))


def test_a_replay_smaller_than_the_batch_is_refused():
    """Otherwise sampling raises deep inside training, far from the cause."""
    with pytest.raises(MCRLContractError, match="at least"):
        TrainerConfig(batch_size=128, replay_capacity=64)
    validate_trainer_config(TrainerConfig(batch_size=64, replay_capacity=64))


def test_a_rising_epsilon_schedule_is_refused():
    """Exploration turning ON over time reads as instability, not a typo."""
    with pytest.raises(MCRLContractError, match="end <= start"):
        TrainerConfig(epsilon_start=0.01, epsilon_end=1.0)
    with pytest.raises(MCRLContractError, match="end <= start"):
        TrainerConfig(epsilon_start=1.5, epsilon_end=0.1)


def test_a_non_positive_discount_is_refused():
    """It silently deletes the future."""
    for value in (0.0, -0.5):
        with pytest.raises(MCRLContractError, match="discount_factor"):
            TrainerConfig(discount_factor=value)
    with pytest.raises(MCRLContractError, match="discount_factor"):
        TrainerConfig(discount_factor=1.5)
    validate_trainer_config(TrainerConfig(discount_factor=1.0))


def test_a_zero_calibration_scale_is_refused():
    """Dividing by it removes the objective without an error."""
    with pytest.raises(MCRLContractError, match="calibration scales"):
        TrainerConfig(reward_calibration_scales=(1.0, 0.0, 1.0))
    with pytest.raises(MCRLContractError, match="calibration scales"):
        TrainerConfig(reward_calibration_scales=(1.0, -2.0, 1.0))


def test_calibration_cannot_be_enabled_while_the_r3_scale_is_unfrozen(
    monkeypatch,
):
    """Q-D: B13 changed r3's units, so the inherited scale means nothing.

    The flag is patched rather than read: Q-D closed on 2026-08-23, so a
    test that relied on it being open would now pass vacuously while
    claiming to exercise the gate.  A guard is only tested by putting it in
    the state it guards against.
    """
    import mcrl.env.service as service

    monkeypatch.setattr(service, "R3_SCALE_IS_FROZEN", False)
    with pytest.raises(MCRLContractError, match="r3 scale is\\s+unfrozen"):
        TrainerConfig(reward_calibration_enabled=True)


def test_calibration_is_allowed_now_that_the_scale_is_frozen():
    """And the other side: with Q-D closed the gate must let it through."""
    from mcrl.env.service import R3_CALIBRATION_SCALE, R3_SCALE_IS_FROZEN

    assert R3_SCALE_IS_FROZEN is True
    config = TrainerConfig(
        reward_calibration_enabled=True,
        reward_calibration_mode="divide-by-fixed-scales",
        reward_calibration_scales=(1.0, 1.0, float(R3_CALIBRATION_SCALE)),
    )
    assert config.reward_calibration_scales[2] == 6.0


def test_learning_rate_must_be_finite_and_positive():
    for value in (0.0, -0.01, float("nan"), float("inf")):
        with pytest.raises(MCRLContractError, match="learning_rate"):
            TrainerConfig(learning_rate=value)


def test_empty_or_zero_width_hidden_layers_are_refused():
    with pytest.raises(MCRLContractError, match="must not be empty"):
        TrainerConfig(hidden_layers=())
    with pytest.raises(MCRLContractError, match="widths must be positive"):
        TrainerConfig(hidden_layers=(100, 0, 50))


def test_unknown_enumerations_are_refused():
    with pytest.raises(MCRLContractError, match="activation"):
        TrainerConfig(activation="gelu")
    with pytest.raises(MCRLContractError, match="policy_sharing_mode"):
        TrainerConfig(policy_sharing_mode="per-user")
    with pytest.raises(MCRLContractError, match="theta_encoding"):
        TrainerConfig(theta_encoding="degrees")
    with pytest.raises(MCRLContractError, match="snr_encoding"):
        TrainerConfig(snr_encoding="db")
    with pytest.raises(MCRLContractError, match="load_normalization"):
        TrainerConfig(load_normalization="softmax")


def test_counts_must_be_at_least_one():
    for kwargs in (
        {"batch_size": 0},
        {"episodes": 0},
        {"epsilon_decay_episodes": 0},
        {"target_update_every_episodes": 0},
    ):
        with pytest.raises(MCRLContractError):
            TrainerConfig(**kwargs)


# -- the validator itself is clean ----------------------------------------


def test_the_enumerations_are_the_paper_ones():
    assert "tanh" in VALID_ACTIVATIONS  # MODQN §IV
    assert VALID_POLICY_SHARING == {"shared"}  # ASSUME-MODQN-REP-007


def test_the_validator_carries_none_of_the_forbidden_vocabulary():
    """The reason it was written rather than ported."""
    import inspect

    from mcrl.runtime import trainer_config_validation

    source = inspect.getsource(trainer_config_validation).lower()
    for term in ("catfish", "v_max", "k_cap", "capacity_penalty", "popart"):
        assert term not in source


def test_it_is_no_longer_shimmed():
    """A permissive stand-in was masking it until this landed."""
    from mcrl.runtime import trainer_config_validation

    assert not getattr(trainer_config_validation, "__mcrl_test_shim__", False)
    assert trainer_config_validation.__file__.endswith(
        "trainer_config_validation.py"
    )
