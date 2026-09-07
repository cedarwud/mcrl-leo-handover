from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / ".scratch"
    / "multi-catfish-v014-learner"
    / "run_v014_q3_support_probe.py"
)
SPEC = importlib.util.spec_from_file_location("v014_q3_support_probe", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_append_reference_context_uses_feature_major_reference_values() -> None:
    states = np.zeros((2, 287), dtype=np.float32)
    local = states[:, :280].reshape(2, 10, 28)
    for row in range(2):
        for feature in range(10):
            local[row, feature] = 1000 * row + 100 * feature + np.arange(28)
    states[:, 280:] = np.array([[1] * 7, [2] * 7], dtype=np.float32)
    result = MODULE.append_reference_context(states, np.array([3, 7]))
    assert result.shape == (2, 297)
    np.testing.assert_array_equal(result[:, :287], states)
    np.testing.assert_array_equal(
        result[0, 287:], np.array([100 * feature + 3 for feature in range(10)])
    )
    np.testing.assert_array_equal(
        result[1, 287:],
        np.array([1000 + 100 * feature + 7 for feature in range(10)]),
    )


def test_balanced_logit_is_corrected_to_natural_prior() -> None:
    result = MODULE.natural_probability_from_balanced_logit(
        torch.tensor([0.0]), positive_prior=0.04
    )
    assert float(result[0]) == pytest.approx(0.04)


def test_binary_auc_handles_ties_and_perfect_order() -> None:
    assert MODULE.binary_auc(
        np.array([False, False, True, True]), np.array([0.0, 0.0, 1.0, 1.0])
    ) == pytest.approx(1.0)
    assert MODULE.binary_auc(
        np.array([False, True]), np.array([0.5, 0.5])
    ) == pytest.approx(0.5)


def test_adjudication_requires_both_q2_contexts() -> None:
    passing = [
        {"changed": 10, "supported_changed": 6},
        {"changed": 10, "supported_changed": 5},
        {"changed": 0, "supported_changed": 0},
    ]
    result = MODULE.adjudicate_probe(passing, passing)
    assert result["decision"] == "GO_REBALANCED_Q3_GATE"
    failing = [
        {"changed": 10, "supported_changed": 4},
        {"changed": 10, "supported_changed": 4},
        {"changed": 10, "supported_changed": 4},
    ]
    result = MODULE.adjudicate_probe(passing, failing)
    assert result["decision"] == "STOP_THREE_HEAD"


def test_mixture_update_is_finite_and_reference_is_zero() -> None:
    rng = np.random.default_rng(9)
    rows = 16
    states = rng.normal(size=(rows, 287)).astype(np.float32)
    masks = np.ones((rows, 28), dtype=np.bool_)
    references = np.zeros(rows, dtype=np.int64)
    kappa = float(MODULE.OPS3_KAPPA_BITS)
    targets = np.full((rows, 28), -kappa, dtype=np.float64)
    compatibility = np.zeros((rows, 28), dtype=np.bool_)
    targets[:, 1] = kappa
    compatibility[:, 1] = True
    targets[:, 0] = 0.0
    spec = MODULE.SupportProbeSpec(
        updates=1,
        batch_size=rows,
        hidden_layers=(8,),
        learning_rate=0.001,
        kappa_bits=kappa,
    )
    learner = MODULE.Q3SupportMixtureLearner(
        global_feature_dim=7,
        positive_prior=1.0 / 27.0,
        unsupported_mean=-1.0,
        spec=spec,
        seed=17,
    )
    metrics = learner.update(states, masks, references, targets, compatibility)
    assert all(np.isfinite(value) for value in metrics.values())
    probability, positive, expected = learner.predict(states, masks, references)
    assert probability.shape == positive.shape == expected.shape == (rows, 28)
    np.testing.assert_array_equal(expected[:, 0], np.zeros(rows))
