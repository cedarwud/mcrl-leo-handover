"""W-93 -- V0.4 parallel C2 learner contract."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from mcrl.algorithms.ee_axis_action_shared_meanmax import EEAxisMaskedMeanMaxConfig
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v04_c2_parallel import (
    C2_MAIN_VALUE,
    C2_Q13_HUBER,
    C2_Q13_VALUE,
    C2ParallelCandidateSpec,
    EEAxisV04C2Trainer,
    frozen_c2_candidate_specs,
)
from mcrl.errors import MCRLContractError


def _config() -> EEAxisMaskedMeanMaxConfig:
    return EEAxisMaskedMeanMaxConfig(
        state_dim=228,
        action_dim=28,
        hidden_layers=(8,),
        activation="tanh",
        learning_rate=1e-3,
        kappa_bits=10.0,
        beta=0.1,
        loss_weights=(1.0, 1.0, 1.0),
    )


def _batch() -> EEAxisPairBatch:
    states = np.zeros((2, 228), dtype=np.float32)
    states[:, 224:] = np.asarray([[0.1, 0.2, 0.3, 0.4]], dtype=np.float32)
    masks = np.ones((2, 28), dtype=np.bool_)
    return EEAxisPairBatch(
        states=states,
        reference_actions=np.asarray([0, 0], dtype=np.int64),
        candidate_actions=np.asarray([1, 2], dtype=np.int64),
        target_surplus_bits=np.asarray([100.0, -100.0], dtype=np.float32),
        action_masks=masks,
    )


def test_frozen_candidate_set_and_field_combinations() -> None:
    specs = frozen_c2_candidate_specs()
    assert tuple(spec.candidate_id for spec in specs) == (
        C2_MAIN_VALUE,
        C2_Q13_VALUE,
        C2_Q13_HUBER,
    )
    assert tuple(spec.continuation for spec in specs) == (
        "frozen-main",
        "matched-frozen-q1-plus-q3",
        "matched-frozen-q1-plus-q3",
    )
    with pytest.raises(ValueError, match="disagree"):
        C2ParallelCandidateSpec(C2_MAIN_VALUE, "frozen-main", "huber", 1.0)


def test_huber_arm_limits_extreme_residual_without_clipping_target() -> None:
    specs = {spec.candidate_id: spec for spec in frozen_c2_candidate_specs()}
    value = EEAxisV04C2Trainer(
        _config(),
        candidate=specs[C2_Q13_VALUE],
        train_seed=2026092101,
    )
    robust = EEAxisV04C2Trainer(
        _config(),
        candidate=specs[C2_Q13_HUBER],
        train_seed=2026092101,
    )
    value_metrics = value.update(_batch())
    robust_metrics = robust.update(_batch())
    assert value_metrics["pair_mse_diagnostic"] == pytest.approx(
        robust_metrics["pair_mse_diagnostic"]
    )
    assert robust_metrics["pair_objective"] < value_metrics["pair_objective"]
    assert robust_metrics["candidate_id"] == C2_Q13_HUBER


def test_checkpoint_round_trip_is_candidate_and_seed_strict() -> None:
    spec = frozen_c2_candidate_specs()[0]
    trainer = EEAxisV04C2Trainer(_config(), candidate=spec, train_seed=11)
    trainer.update(_batch())
    state = trainer.checkpoint_state(update_count=1)
    restored = EEAxisV04C2Trainer(_config(), candidate=spec, train_seed=11)
    assert restored.load_checkpoint_state(state) == 1
    np.testing.assert_allclose(
        trainer.q2_values(_batch().states, _batch().action_masks),
        restored.q2_values(_batch().states, _batch().action_masks),
    )

    wrong = EEAxisV04C2Trainer(
        _config(),
        candidate=frozen_c2_candidate_specs()[1],
        train_seed=11,
    )
    with pytest.raises(MCRLContractError, match="candidate mismatch"):
        wrong.load_checkpoint_state(state)

    damaged = deepcopy(state)
    damaged["train_seed"] = 12
    with pytest.raises(MCRLContractError, match="train_seed mismatch"):
        restored.load_checkpoint_state(damaged)


def test_trainer_owns_exactly_one_q2_network() -> None:
    trainer = EEAxisV04C2Trainer(
        _config(),
        candidate=frozen_c2_candidate_specs()[0],
        train_seed=3,
    )
    assert hasattr(trainer, "q2")
    assert not hasattr(trainer, "q_nets")
    assert len(tuple(trainer.q2.parameters())) > 0
