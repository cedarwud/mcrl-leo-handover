"""CAPPENALTY acceptance for the per-satellite beam cap flag.

1. OFF (beam_cap=None) is bit-identical to the plain environment: per-step
   outcomes over full episodes AND trained weights after real training.
2. A cap larger than any satellite's beam count is a pure pass-through through
   the real pipeline (exercises apply_cap end to end with nothing darkened).
3. k=3 is enforced every step, darkens by the sibling's rule, leaves demand
   untouched, and only removes service (never adds any).
4. The live tree still carries no cap vocabulary (ruling §7.1-7.2 gate).

Run on the server workspace:
  /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest cap-penalty/test_beam_cap.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for base in HERE.parents:
    if (base / "src" / "mcrl").is_dir():
        SRC = base / "src"
        break
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(HERE))

import numpy as np
import pytest
import torch

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.service import ServiceResolution
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment

from beam_cap import (
    CappedServiceResolution,
    active_beams_per_satellite,
    apply_cap,
    make_capped_training_environment,
)

SEEDS = dict(train_seed=42, env_seed=1337, mobility_seed=7)


def _plain():
    return make_training_environment(users=100)


def _capped(k):
    return make_capped_training_environment(users=100, beam_cap=k)


def _trainer(env, episodes=1):
    cfg = TrainerConfig(learning_rate=0.001, episodes=episodes, batch_size=8)
    return MODQNTrainer(env, cfg, **SEEDS)


def _rollout(env, n_episodes=1, epsilon=0.3):
    """Record every step's outcome under the trainer's own RNG streams."""
    tr = _trainer(env)
    rows = []
    for _ in range(n_episodes):
        states, masks, _ = env.reset(tr._env_rng, tr._mobility_rng)
        enc = tr._encode_states(states)
        for _t in range(env.config.steps_per_episode):
            actions = tr.select_actions(enc, masks, epsilon)
            result = env.step(actions, tr._env_rng)
            o = env.last_outcome
            rows.append(dict(
                actions=np.array(actions, copy=True),
                served=o.resolution.served.copy(),
                serving_cell=o.resolution.serving_cell.copy(),
                demand=dict(o.resolution.demand_by_beam),
                eligible=dict(o.resolution.eligible_load_by_beam),
                reward=o.reward_matrix.copy(),
                bits=float(o.energy.system_throughput_bps),
                joules=float(o.energy.system_consumed_power_w),
                power=float(o.system_power_w),
                enc=tr._encode_states(result.user_states).copy(),
                resolution=o.resolution,
            ))
            states = result.user_states
            enc = tr._encode_states(states)
            masks = result.action_masks
            if result.done:
                break
    return rows


def _assert_rows_identical(a, b):
    assert len(a) == len(b)
    for x, y in zip(a, b):
        assert np.array_equal(x["actions"], y["actions"])
        assert np.array_equal(x["served"], y["served"])
        assert np.array_equal(x["serving_cell"], y["serving_cell"])
        assert x["demand"] == y["demand"]
        assert x["eligible"] == y["eligible"]
        assert np.array_equal(x["reward"], y["reward"])
        assert x["bits"] == y["bits"]
        assert x["joules"] == y["joules"]
        assert x["power"] == y["power"]
        assert np.array_equal(x["enc"], y["enc"])


# -- 1. OFF is bit-identical ----------------------------------------------

def test_off_rollout_is_bit_identical_to_plain_env():
    a = _rollout(_plain(), n_episodes=2)
    b = _rollout(_capped(None), n_episodes=2)
    _assert_rows_identical(a, b)
    assert all(type(r["resolution"]) is ServiceResolution for r in b), (
        "OFF must not even construct a capped resolution"
    )


def test_off_training_weights_are_bit_identical():
    def train(env):
        tr = _trainer(env, episodes=2)
        logs = []
        tr.train(progress_every=1000,
                 episode_callback=lambda log: logs.append(
                     (log.r1_mean, log.r2_mean, log.r3_mean,
                      log.total_handovers, tuple(log.losses))))
        return tr, logs

    ta, la = train(_plain())
    tb, lb = train(_capped(None))
    assert la == lb
    for x, y in zip(ta.q_nets.parameters(), tb.q_nets.parameters()):
        assert torch.equal(x, y)


# -- 2. a non-binding cap is a pure pass-through ---------------------------

def test_non_binding_cap_is_pass_through():
    a = _rollout(_plain(), n_episodes=1)
    b = _rollout(_capped(10**6), n_episodes=1)
    _assert_rows_identical(a, b)
    assert all(isinstance(r["resolution"], CappedServiceResolution) for r in b)
    assert all(not r["resolution"].cap_darkened.any() for r in b)


# -- 3. k = 3 is enforced by the sibling's rule ----------------------------

def test_cap3_enforced_every_step_and_only_removes_service():
    rows = _rollout(_capped(3), n_episodes=1, epsilon=1.0)
    darkened_total = 0
    for r in rows:
        res = r["resolution"]
        per_sat = active_beams_per_satellite(res)
        assert per_sat and max(per_sat.values()) <= 3
        # darkened users are unserved and flagged separately from outage
        assert not np.any(res.served & res.cap_darkened)
        assert not np.any(res.outage_infeasible & res.cap_darkened)
        darkened_total += int(res.cap_darkened.sum())
    assert darkened_total > 0, "k=3 must bind at 100 users (ruling measured p50=20)"


def test_cap3_first_step_matches_plain_env_minus_darkened_users():
    """Same step-0 actions: the capped step serves a subset, same demand."""
    a = _rollout(_plain(), n_episodes=1, epsilon=1.0)[0]
    b = _rollout(_capped(3), n_episodes=1, epsilon=1.0)[0]
    assert np.array_equal(a["actions"], b["actions"])
    assert a["demand"] == b["demand"], "pre-admission demand is untouched"
    assert np.all(b["served"] <= a["served"])
    res = b["resolution"]
    assert np.array_equal(a["served"] & ~res.cap_darkened, b["served"])
    # the kept beams are the top-3 of the plain eligible load per satellite
    by_sat = {}
    for (norad, cell), load in a["eligible"].items():
        by_sat.setdefault(norad, []).append((cell, load))
    expected = set()
    for norad, beams in by_sat.items():
        order = sorted(beams, key=lambda t: (-t[1], t[0]))[:3]
        expected.update((norad, c) for c, _ in order)
    assert set(b["eligible"]) == expected
    for key in expected:
        assert b["eligible"][key] == a["eligible"][key]


def test_apply_cap_unit_rule_and_ties():
    # satellite 1: cells 10:5, 11:3, 12:3, 13:1, 14:3  -> keep 10, 11, 12
    # satellite 2: cells 20:1                           -> keep 20
    layout = ([(1, 10)] * 5 + [(1, 11)] * 3 + [(1, 12)] * 3 + [(1, 13)]
              + [(1, 14)] * 3 + [(2, 20)])
    users = len(layout) + 1  # plus one unserved no-op user
    sat = np.array([s for s, _ in layout] + [-1])
    cell = np.array([c for _, c in layout] + [-1])
    served = np.array([True] * len(layout) + [False])
    eligible = {}
    for key in layout:
        eligible[key] = eligible.get(key, 0) + 1
    res = ServiceResolution(
        served=served, serving_cell=cell, serving_satellite=sat,
        demand_by_beam=dict(eligible), eligible_load_by_beam=dict(eligible),
        no_op_users=~served, outage_infeasible=np.zeros(users, dtype=bool),
    )
    out = apply_cap(res, 3)
    assert set(out.eligible_load_by_beam) == {(1, 10), (1, 11), (1, 12), (2, 20)}
    dark = out.cap_darkened
    assert dark.sum() == 1 + 3  # cell 13 (1 user) and cell 14 (3 users)
    assert np.all(cell[dark] >= 13)
    assert np.all(out.serving_cell[dark] == -1)
    assert out.demand_by_beam == res.demand_by_beam
    assert out.served_count == res.served_count - 4


# -- 4. the live tree stays ruling-compliant -------------------------------

CAP_VOCABULARY = (  # copied from tests/test_ruling_no_beam_count_cap.py
    "max_simultaneous_beams", "beams_per_satellite", "beam_count_cap",
    "activation_cap", "max_active_beams", "aggregate_cap",
    "satellite_aggregate",
)


def test_live_tree_has_no_cap_socket():
    offenders = [
        f"{p.relative_to(SRC)}: {t}"
        for p in sorted((SRC / "mcrl").rglob("*.py"))
        for t in CAP_VOCABULARY
        if t in p.read_text().lower()
    ]
    assert not offenders, offenders
