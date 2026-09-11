"""PENALTYARM acceptance: the OFF path is bit-identical, the arm actually fires.

Run:  /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest <this file> -q
      (locally: .venv/bin/python -m pytest ...)
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

import numpy as np
import pytest
import torch

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.runtime.collapse_penalty import (
    KUMAR_ALPHA,
    PenaltyConfig,
    SIBLING_PRESETS,
    preset_config,
    srank_diagnostic,
    srank_penalty,
)
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment


def _cfg() -> TrainerConfig:
    return TrainerConfig(learning_rate=0.001, episodes=1, batch_size=8)


def _trainer(penalty: PenaltyConfig | None) -> MODQNTrainer:
    env = make_training_environment(users=100)
    return MODQNTrainer(
        env, _cfg(), train_seed=42, env_seed=1337, mobility_seed=7,
        penalty_config=penalty,
    )


def _fill_replay(tr: MODQNTrainer, n: int = 64) -> None:
    rng = np.random.default_rng(11)
    d = tr.state_dim
    a = tr.action_dim
    for _ in range(n):
        mask = np.zeros(a, dtype=bool)
        mask[rng.integers(0, a, size=4)] = True
        nmask = np.zeros(a, dtype=bool)
        nmask[rng.integers(0, a, size=4)] = True
        tr.replay.push(
            rng.normal(size=d).astype(np.float32),
            int(np.flatnonzero(mask)[0]),
            rng.normal(size=3).astype(np.float32),
            rng.normal(size=d).astype(np.float32),
            mask, nmask, False,
        )


def _weights(tr: MODQNTrainer) -> list[torch.Tensor]:
    return [p.detach().clone() for p in tr.q_nets.parameters()]


def _run(penalty: PenaltyConfig | None, steps: int = 20):
    tr = _trainer(penalty)
    _fill_replay(tr)
    losses = []
    for _ in range(steps):
        losses.append(tr.update())
    return tr, losses


# --------------------------------------------------------------------------
def test_off_is_bit_identical_to_no_penalty_config():
    """kind='none' and no config at all must produce identical weights."""
    a, la = _run(None)
    b, lb = _run(PenaltyConfig())
    assert la == lb
    for x, y in zip(_weights(a), _weights(b)):
        assert torch.equal(x, y)


def test_diagnostics_do_not_perturb_the_off_path():
    """Read-only readouts consume no RNG and mutate nothing."""
    a, la = _run(None)
    b, lb = _run(PenaltyConfig(diagnostics=True))
    assert la == lb
    for x, y in zip(_weights(a), _weights(b)):
        assert torch.equal(x, y)
    stats = b.drain_penalty_stats()
    assert all(c > 0 for c in stats["diagnostic_updates"])
    assert all(s > 0 for s in stats["srank_diagnostic_mean"])


def test_penalty_arm_changes_the_weights_and_fires_every_update():
    off, _ = _run(None)
    pen, _ = _run(preset_config("TB-SRANK-kumar", diagnostics=True))
    same = [torch.equal(x, y) for x, y in zip(_weights(off), _weights(pen))]
    assert not all(same), "srank penalty had no effect on any parameter"
    stats = pen.drain_penalty_stats()
    assert stats["penalty_updates"] == [20, 20, 20], stats["penalty_updates"]
    assert all(v > 0 for v in stats["penalty_raw_mean"])
    assert all(v > 0 for v in stats["penalty_grad_norm_mean"])
    assert stats["penalty_coefficient"] == KUMAR_ALPHA


def test_null_grad_control_fires_and_injects_the_declared_norm():
    norms = (0.25, 0.25, 0.25)
    tr, _ = _run(PenaltyConfig(kind="null_grad", null_grad_norms=norms,
                               diagnostics=True))
    stats = tr.drain_penalty_stats()
    assert stats["penalty_updates"] == [20, 20, 20]
    for k in range(3):
        assert stats["penalty_grad_norm_mean"][k] == pytest.approx(norms[k])
    off, _ = _run(None)
    same = [torch.equal(x, y) for x, y in zip(_weights(off), _weights(tr))]
    assert not all(same), "null_grad control had no effect on any parameter"


def test_null_grad_does_not_disturb_the_torch_init_stream():
    """OFF and NULL_PENALTY must start from identical weights."""
    a = _trainer(None)
    b = _trainer(PenaltyConfig(kind="null_grad", null_grad_norms=(1.0, 1.0, 1.0)))
    for x, y in zip(_weights(a), _weights(b)):
        assert torch.equal(x, y)


def test_srank_penalty_matches_kumar_equation_6():
    g = torch.Generator().manual_seed(3)
    phi = torch.randn(128, 50, generator=g)
    s = torch.linalg.svdvals(phi)
    assert srank_penalty(phi).item() == pytest.approx(
        (s[0] ** 2 - s[-1] ** 2).item(), rel=1e-6
    )
    # rank-1 Phi: penalty is sigma_max^2, diagnostic is 1 after centering
    v = torch.randn(50, generator=g)
    rank1 = torch.outer(torch.arange(1.0, 129.0), v)
    assert srank_diagnostic(rank1) == 1


def test_all_six_sibling_presets_are_constructible():
    assert len(SIBLING_PRESETS) == 6
    for name in SIBLING_PRESETS:
        cfg = preset_config(name)
        assert cfg.active and cfg.is_loss_term and cfg.preset == name


def test_off_by_default():
    assert not PenaltyConfig().active
    assert not PenaltyConfig().is_loss_term
