"""B1-CREDIT: difference-reward credit and analytic lighting price for the CF-ratio learner.

Brief: ``.scratch/b1-credit/PROMPT.md`` (ruling 2 section 3 stage B1; engineering lane, NO training).

Every test here was first run against a named mutant and seen to FAIL
(``CREDIT_MUTANT=<name> pytest tests/test_cf_credit.py -k ...``), then against
the real code and seen to PASS.  Mutants are applied by the autouse
``mutant`` fixture with ``monkeypatch``; no source file is edited.  The
red/green log is in ``.scratch/b1-credit/PROGRESS.md``.

Hard boundary: nothing here runs an optimizer step.  Trainer-level checks run
``train_cf`` with ``batch_size`` larger than any replay the episode can fill,
so ``update()`` returns before touching a network, and every such test
asserts ``updates == 0`` and unchanged weights.
"""

from __future__ import annotations

import dataclasses
import os
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import pytest
import torch

from mcrl.algorithms import cf_credit as cc
from mcrl.algorithms import cf_ratio as cfr
from mcrl.algorithms import cf_sources as cfs
from mcrl.env.link_budget import (
    BASEBAND_POWER_PER_SATELLITE_W,
    CIRCUIT_POWER_PER_BEAM_W,
    pa_efficiency,
    supply_power_w,
)
from mcrl.errors import MCRLContractError
from mcrl.runtime.trainer_config_validation import TD_BOOTSTRAP_SHARED
from mcrl.runtime.trainer_spec import TrainerConfig

REPO = Path(__file__).resolve().parents[1]
PINNED_LOCAL = Path("/home/u24/mcrl-runtime/tle-pinned-427e6a91")
CF3_BASE = "102b2d4d"          # tip of cf3/pilot-20260911: the CF3 learner as run
MUTANT = os.environ.get("CREDIT_MUTANT", "")
DT = cc.DT_S
# CF3 declared units (calibration, pinned archive): eta~ = eta * s_E / s_B.
S_B = 13_329_082_278.45065
S_E = 120.61728174105066


# ---------------------------------------------------------------- mutants
@pytest.fixture(autouse=True)
def mutant(monkeypatch):
    from mcrl.env import step as env_step

    if MUTANT == "default_credit_difference":
        real_init = cfr.CFRatioSettings.__init__

        def sinit(self, *a, **k):
            k.setdefault("credit_mode", "difference")
            real_init(self, *a, **k)

        monkeypatch.setattr(cfr.CFRatioSettings, "__init__", sinit)
    elif MUTANT == "e_share_over_served":
        real = cfr.cf_reward_matrix

        def bad(result, outcome, *, dt=cfr.DT_S):
            out = real(result, outcome, dt=dt)
            n = max(1, int(sum(bool(x) for x in result.served)))
            out[:, cfr.HEAD_E] *= len(result.rewards) / n
            return out

        monkeypatch.setattr(cfr, "cf_reward_matrix", bad)
    elif MUTANT == "cf_live_rng":
        real = env_step.StepEnvironment._evaluate_selected_actions

        def live(self, decision, selected, rng):
            segments = self._segments.copy()
            try:
                physics = self._resolve_physics(decision, selected, rng)  # no copy
            finally:
                self._segments = segments
            del physics
            return real(self, decision, selected, rng)

        monkeypatch.setattr(env_step.StepEnvironment, "_evaluate_selected_actions", live)
    elif MUTANT == "cf_commits_segments":
        import copy as _copy

        def leaky(self, decision, selected, rng):
            physics = self._resolve_physics(decision, selected, _copy.deepcopy(rng))
            rewards, handovers = self._rewards(decision, selected, physics, commit=False)
            return env_step.ActionEvaluation(
                rewards=rewards, resolution=physics["resolution"], energy=physics["energy"],
                interference=physics["interference"], radiating=physics["radiating"],
                link_power_w=physics["link_power_w"], link_sinr=physics["sinr"],
                link_rate_bps=physics["rate"], handovers=handovers,
                system_power_w=float(physics["system_power_w"]),
                fixed_power_w=float(physics["fixed_power_w"]),
            )

        monkeypatch.setattr(env_step.StepEnvironment, "_evaluate_selected_actions", leaky)
    elif MUTANT == "ed_supply_only":
        real = cc.evaluation_bits_joules

        def supply_only(ev, dt=cc.DT_S):
            bits, _ = real(ev, dt)
            return bits, (float(ev.system_power_w) - float(ev.fixed_power_w)) * dt

        monkeypatch.setattr(cc, "evaluation_bits_joules", supply_only)
    elif MUTANT == "ed_per_link_power":
        def per_link(ev, dt=cc.DT_S):
            bits = float(ev.energy.system_throughput_bps) * dt
            return bits, float(ev.diagnostics["superseded_link_charged_power_w"]) * dt

        monkeypatch.setattr(cc, "evaluation_bits_joules", per_link)
    elif MUTANT == "lp_no_baseband":
        monkeypatch.setattr(cc, "BASEBAND_POWER_PER_SATELLITE_W", 0.0)
    elif MUTANT == "lp_tie_as_max":
        def strict_below(values, i):
            others = np.delete(np.asarray(values, dtype=np.float64), i)
            below = others[others < values[i]]
            if others.size and np.max(others) > values[i]:
                return float(np.max(others))
            return float(np.max(below)) if below.size else 0.0

        monkeypatch.setattr(cc, "_max_without", strict_below)
    elif MUTANT == "no_outage_charge":
        monkeypatch.setattr(cc, "outage_charge", lambda served_b, model, dt=cc.DT_S: (0.0, 0.0))
    elif MUTANT == "bd_own_bits":
        monkeypatch.setattr(cc, "difference_bits", lambda ctx, u, own: own)
    elif MUTANT == "physics_bandwidth_not_shared":
        real = env_step.shannon_rate_bps

        def unshared(sinr, *, beam_load, bandwidth_hz=cc.BEAM_BANDWIDTH_HZ):
            return real(sinr, beam_load=np.minimum(beam_load, 1.0), bandwidth_hz=bandwidth_hz)

        monkeypatch.setattr(env_step, "shannon_rate_bps", unshared)
    elif MUTANT == "trainer_ignores_pool_credit":
        monkeypatch.setattr(cfr, "_check_pool_credit", lambda pools, mode: None)
    elif MUTANT == "resume_requires_flag":
        real_load = cfr.CFRatioTrainer.load_training_state_dict

        def strict(self, state):
            if "credit_mode" not in state["cf"]["settings"]:
                raise MCRLContractError("resume state CF settings do not match")
            return real_load(self, state)

        monkeypatch.setattr(cfr.CFRatioTrainer, "load_training_state_dict", strict)
    elif MUTANT:
        raise AssertionError(f"unknown mutant {MUTANT}")
    yield


# ---------------------------------------------------------------- helpers
_ARCHIVE = {}


def _factory(users):
    if not PINNED_LOCAL.is_dir():
        pytest.skip("pinned local TLE archive not present")
    os.environ["MCRL_TLE_ROOT"] = str(PINNED_LOCAL)
    if "a" not in _ARCHIVE:
        from mcrl.runtime.training_pipeline import assert_tle_archive_pinned
        from mcrl.env.tle import TleArchive
        assert_tle_archive_pinned(PINNED_LOCAL)
        _ARCHIVE["a"] = TleArchive(PINNED_LOCAL)
    return lambda: cfr.make_env_on(_ARCHIVE["a"], users)


def _config(**kw) -> TrainerConfig:
    base = dict(learning_rate=0.001, episodes=1, epsilon_decay_episodes=2,
                td_bootstrap_mode=TD_BOOTSTRAP_SHARED, batch_size=5000,
                replay_capacity=5000, target_update_every_episodes=1,
                discount_factor=1.0)
    base.update(kw)
    return TrainerConfig(**base)


def _settings(mod=cfr, **kw):
    base = dict(source_kind="none", eta0=2.0, bits_scale=10.0, joules_scale=4.0,
                quarter_episodes=10_000, catfish_buffer_capacity=5000,
                calibration_episodes=1)
    base.update(kw)
    return mod.CFRatioSettings(**base)


def _cf3_reference():
    """``cf_ratio.py`` exactly as CF3 ran it (``git show 102b2d4d:...``), as a module."""
    name = "mcrl.algorithms._cf3_reference_cf_ratio"
    if name in sys.modules:
        return sys.modules[name]
    try:
        src = subprocess.run(
            ["git", "-C", str(REPO), "show", f"{CF3_BASE}:src/mcrl/algorithms/cf_ratio.py"],
            capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("CF3 base commit not readable with git")
    mod = types.ModuleType(name)
    mod.__package__ = "mcrl.algorithms"
    sys.modules[name] = mod
    exec(compile(src, f"{CF3_BASE}:src/mcrl/algorithms/cf_ratio.py", "exec"), mod.__dict__)
    return mod


def _weights(tr):
    return [p.detach().clone() for net in tr.q_nets for p in net.parameters()]


def _rng_states(tr):
    return (tr._env_rng.bit_generator.state, tr._mobility_rng.bit_generator.state,
            tr._train_rng.bit_generator.state)


def _rollout(users, seeds, rule_name="C1_A_m2dB", steps=10, hook=None):
    """Roll a CF3 rule; ``hook(env, actions, masks, env_rng)`` runs before each step."""
    env = _factory(users)()
    er, mr = np.random.default_rng(seeds[0]), np.random.default_rng(seeds[1])
    states, masks, _ = env.reset(er, mr)
    rule = cfs.cf3_policies()[rule_name] if rule_name != "random" else cfs.random_legal(
        np.random.default_rng(seeds[0] + 7))
    rows = []
    for _t in range(steps):
        a = rule(states, masks)
        extra = hook(env, a, masks, er) if hook is not None else None
        res = env.step(a, er)
        rows.append((a, masks, res, env.last_outcome, extra))
        states, masks = res.user_states, res.action_masks
        if res.done:
            break
    return env, rows


def _beam_facts(outcome):
    """Per served user: beam key, beam load, users on its satellite, beam power, others' max."""
    r = outcome.resolution
    served = np.asarray(r.served)
    keys = [(int(r.serving_satellite[u]), int(r.serving_cell[u])) for u in range(served.size)]
    lp = np.asarray(outcome.link_power_w)
    facts = {}
    for u in np.flatnonzero(served):
        mates = [v for v in np.flatnonzero(served) if keys[v] == keys[u]]
        on_sat = [v for v in np.flatnonzero(served) if keys[v][0] == keys[u][0]]
        others = [lp[v] for v in mates if v != u]
        facts[int(u)] = dict(load=len(mates), on_sat=len(on_sat), p_u=float(lp[u]),
                             p_b=float(max(lp[v] for v in mates)),
                             p_others=float(max(others)) if others else 0.0)
    return facts


def _supply(p):
    p = np.asarray([p], dtype=np.float64)
    return float(supply_power_w(p, pa_efficiency(p))[0])


# ---------------------------------------------------------------- 1. equal_share == CF3
def test_equal_share_is_bit_identical_to_cf3():
    ref = _cf3_reference()
    # Fingerprint: the settings dict CF3 fingerprinted, plus only the new flag at its default.
    for kw in ({}, dict(source_kind="cf3", eta0=110_507_234.83444457, bits_scale=S_B,
                        joules_scale=S_E)):
        new = dataclasses.asdict(cfr.CFRatioSettings(**kw))
        old = dataclasses.asdict(ref.CFRatioSettings(**kw))
        assert new == {**old, "credit_mode": "equal_share"}
    with pytest.raises(MCRLContractError):
        cfr.CFRatioSettings(credit_mode="shapley")

    # Trainer rollout, no update (batch never fills): replay, logs, RNG streams identical.
    factory = _factory(6)
    runs = []
    for mod in (ref, cfr):
        tr = mod.CFRatioTrainer(factory(), _config(), _settings(mod), env_factory=factory,
                                train_seed=5, env_seed=6, mobility_seed=7)
        w0 = _weights(tr)
        logs = tr.train_cf(progress_every=0)
        assert all(x["updates"] == 0 for x in logs)
        assert all(torch.equal(a, b) for a, b in zip(w0, _weights(tr)))
        runs.append((tr, logs))
    (t_ref, l_ref), (t_new, l_new) = runs
    assert l_ref == l_new
    assert len(t_ref.replay) == len(t_new.replay) > 0
    for p, q in zip(t_ref.replay._buf, t_new.replay._buf):
        for x, y in zip(p, q):
            assert np.array_equal(np.asarray(x), np.asarray(y))
    assert _rng_states(t_ref) == _rng_states(t_new)
    assert dataclasses.asdict(t_new.settings)["credit_mode"] == "equal_share"
    assert {k: v for k, v in dataclasses.asdict(t_new.settings).items() if k != "credit_mode"} \
        == dataclasses.asdict(t_ref.settings)

    # Source pools generated with the default credit: bit-identical to CF3's generator.
    rule = cfs.cf3_policies()["C1_A_m2dB"]
    seeds = [(9_141_000, 9_142_000)]
    p_ref = ref.generate_pool(lambda i: rule, env_factory=factory, seeds=seeds, config=_config())
    p_new = cfr.generate_pool(lambda i: rule, env_factory=factory, seeds=seeds, config=_config())
    assert set(p_ref) == set(p_new)
    for f in p_ref:
        np.testing.assert_array_equal(p_ref[f], p_new[f])


# ---------------------------------------------------------------- 2. no RNG / state leak
def test_counterfactual_calls_leave_the_trajectory_bit_identical():
    def plain_hook(env, a, masks, er):
        return er.bit_generator.state

    model_box = {}

    def cf_hook(env, a, masks, er):
        before = er.bit_generator.state
        model = model_box.setdefault("m", cc.PowerModel.of(env))
        ctx = cc.difference_context(env, a, masks, er, model=model)
        se = env.environment
        assert "satellite_ecef_at" not in vars(se.driver)      # memo restored
        assert "_warm_start_gain" not in vars(se)
        for u in (0, 5, 11):                                  # memoized == plain evaluator
            wo = se.evaluate_actions_without_user(a, er, focal_user=u)
            assert (ctx.without_bits[u], ctx.without_joules[u]) == cc.evaluation_bits_joules(wo)
        # one full per-action sweep for one user, as the diagnostics do
        u = int(np.flatnonzero([m.mask.any() for m in masks])[0])
        cc.action_credits(env, a, masks, u, er, model=model)
        assert er.bit_generator.state == before
        return ctx

    _, plain = _rollout(12, (31, 32), hook=plain_hook)
    env_cf, withcf = _rollout(12, (31, 32), hook=cf_hook)
    assert len(plain) == len(withcf) == 10
    for (a0, _m0, r0, o0, _), (a1, _m1, r1, o1, ctx) in zip(plain, withcf):
        np.testing.assert_array_equal(a0, a1)
        assert o0.energy.system_throughput_bps == o1.energy.system_throughput_bps
        assert o0.energy.system_consumed_power_w == o1.energy.system_consumed_power_w
        np.testing.assert_array_equal(o0.resolution.served, o1.resolution.served)
        np.testing.assert_array_equal(o0.link_power_w, o1.link_power_w)
        np.testing.assert_array_equal(o0.link_rate_bps, o1.link_rate_bps)
        assert o0.handovers == o1.handovers
        np.testing.assert_array_equal(o0.observation.state_matrix, o1.observation.state_matrix)
        # parity: the evaluator's base vector IS the committed step (ruling 2 section 1)
        assert ctx.base_bits == float(o1.energy.system_throughput_bps) * DT
        assert ctx.base_joules == float(o1.energy.system_consumed_power_w) * DT

    # Trainer level: the difference credit changes rewards, never the trajectory.
    factory = _factory(6)
    runs = {}
    for mode in ("equal_share", "difference", "lighting_price"):
        tr = cfr.CFRatioTrainer(factory(), _config(), _settings(credit_mode=mode),
                                env_factory=factory, train_seed=5, env_seed=6, mobility_seed=7)
        w0 = _weights(tr)
        logs = tr.train_cf(progress_every=0)
        assert all(x["updates"] == 0 for x in logs)
        assert all(torch.equal(a, b) for a, b in zip(w0, _weights(tr)))
        runs[mode] = (tr, logs)
    ref_tr, ref_logs = runs["equal_share"]
    for mode in ("difference", "lighting_price"):
        tr, logs = runs[mode]
        assert _rng_states(tr) == _rng_states(ref_tr)
        for x, y in zip(ref_logs, logs):
            for k in ("served", "beams", "h_inter", "h_intra", "outage_user_steps"):
                assert x[k] == y[k]
            assert y["bits"] == pytest.approx(x["bits"], rel=1e-12)
            assert y["joules"] == pytest.approx(x["joules"], rel=1e-12)
        assert [p[1] for p in tr.replay._buf] == [p[1] for p in ref_tr.replay._buf]
        assert all(np.array_equal(p[0], q[0]) for p, q in zip(tr.replay._buf, ref_tr.replay._buf))
        assert any(not np.array_equal(p[2], q[2]) for p, q in zip(tr.replay._buf, ref_tr.replay._buf))


# ---------------------------------------------------------------- 3. E^D structure
def test_difference_energy_alone_on_beam_and_non_max_user():
    model = {}

    def hook(env, a, masks, er):
        m = model.setdefault("m", cc.PowerModel.of(env))
        return cc.difference_context(env, a, masks, er, model=m)

    counts = dict(alone=0, alone_sat=0, non_max=0, tie=0, unique_max=0)
    for seeds, rule in (((41, 42), "C1_A_m2dB"), ((43, 44), "random")):
        _, rows = _rollout(24, seeds, rule_name=rule, hook=hook)
        for _a, _m, _res, out, ctx in rows:
            for u, f in _beam_facts(out).items():
                ed = ctx.base_joules - ctx.without_joules[u]
                if f["load"] == 1:
                    want = (_supply(f["p_u"]) + CIRCUIT_POWER_PER_BEAM_W
                            + (BASEBAND_POWER_PER_SATELLITE_W if f["on_sat"] == 1 else 0.0)) * DT
                    assert ed == pytest.approx(want, rel=1e-9)
                    counts["alone"] += 1
                    counts["alone_sat"] += f["on_sat"] == 1
                elif f["p_u"] < f["p_b"]:
                    assert ed == 0.0
                    counts["non_max"] += 1
                elif f["p_others"] == f["p_u"]:
                    assert ed == 0.0                      # tied at the max: beam power unchanged
                    counts["tie"] += 1
                else:
                    want = (_supply(f["p_u"]) - _supply(f["p_others"])) * DT
                    assert ed == pytest.approx(want, rel=1e-6, abs=1e-9 * ctx.base_joules)
                    counts["unique_max"] += 1
    assert all(v > 0 for v in counts.values()), counts


# ---------------------------------------------------------------- 4. LP == D (joules)
def test_joules_ignore_interference_and_lighting_price_equals_difference():
    # (a) joules do not depend on the fading draw (hence not on interference or SINR).
    env = _factory(10)()
    er, mr = np.random.default_rng(51), np.random.default_rng(52)
    states, masks, _ = env.reset(er, mr)
    for _t in range(2):
        res = env.step(cfs.cf3_policies()["C1_A_m2dB"](states, masks), er)
        states, masks = res.user_states, res.action_masks
    a = cfs.cf3_policies()["C1_A_m2dB"](states, masks)
    evs = [env.environment.evaluate_actions(a, np.random.default_rng(s)) for s in (1, 2, 3)]
    assert len({e.energy.system_consumed_power_w for e in evs}) == 1
    assert len({e.energy.system_throughput_bps for e in evs}) == 3

    # (b) analytic lighting price == counterfactual E^D on every user-step.
    model = {}

    def hook(env, a, masks, er):
        m = model.setdefault("m", cc.PowerModel.of(env))
        return cc.difference_context(env, a, masks, er, model=m)

    n = n_alone_sat = n_tie = 0
    for seeds, rule in (((53, 54), "C1_A_m2dB"), ((55, 56), "random"), ((57, 58), "C2_A_m12dB")):
        _, rows = _rollout(24, seeds, rule_name=rule, hook=hook)
        for _a, _m, res, out, ctx in rows:
            m = model["m"]
            d = cc.credit_matrix("difference", res, out, model=m, ctx=ctx)
            lp = cc.credit_matrix("lighting_price", res, out, model=m)
            tol = 1e-12 * float(out.energy.system_consumed_power_w) * DT
            np.testing.assert_allclose(lp[:, cc.HEAD_E], d[:, cc.HEAD_E], rtol=0, atol=tol)
            facts = _beam_facts(out)
            for u, f in facts.items():                 # structural zeros are exact on both sides
                if f["load"] > 1 and (f["p_u"] < f["p_b"] or f["p_others"] == f["p_u"]):
                    assert lp[u, cc.HEAD_E] == 0.0 == d[u, cc.HEAD_E]
            n += len(facts)
            n_alone_sat += sum(f["on_sat"] == 1 for f in facts.values())
            n_tie += sum(f["load"] > 1 and f["p_u"] == f["p_b"] and f["p_others"] == f["p_u"]
                         for f in facts.values())
    assert n > 0 and n_alone_sat > 0 and n_tie > 0, (n, n_alone_sat, n_tie)


# ---------------------------------------------------------------- 5. outage charge
ETAS = (0.0, 0.5, 1.0, 2.0, 10.0)


def test_outage_is_never_preferred_over_the_worst_served_legal_action():
    tested = 0
    free_ride_possible = False
    for seeds in ((61, 62), (63, 64)):
        env = _factory(10)()
        er, mr = np.random.default_rng(seeds[0]), np.random.default_rng(seeds[1])
        states, masks, _ = env.reset(er, mr)       # step 0: warm-start ages -> infeasible links
        a = cfs.cf3_policies()["C1_A_m2dB"](states, masks)
        model = cc.PowerModel.of(env)
        pick = None
        for u in range(10):
            ac = cc.action_credits(env, a, masks, u, er, model=model)
            if ac.served.all() or not ac.served.any():
                continue
            tested += 1
            for mode in ("difference", "lighting_price"):
                b, e = ac.credit(mode)
                assert np.all(e[ac.served] <= model.outage_joules() * (1 + 1e-12))
                for eta in ETAS:
                    score = b / S_B - eta * e / S_E
                    assert score[~ac.served].max() <= score[ac.served].min(), (mode, eta, u)
                    if mode == "difference" and eta == 1.0 and score[ac.served].min() < 0.0:
                        free_ride_possible = True
            if pick is None:
                pick = (u, int(ac.actions[np.flatnonzero(~ac.served)[0]]), ac)
        # A realised outage in the credit matrix carries exactly the declared charge.
        u, bad_action, ac = pick
        alt = np.array(a, copy=True)
        alt[u] = bad_action
        ctx = cc.difference_context(env, alt, masks, er, model=model)
        res = env.step(alt, er)
        out = env.last_outcome
        assert not out.resolution.served[u]
        d = cc.credit_matrix("difference", res, out, model=model, ctx=ctx)
        lp = cc.credit_matrix("lighting_price", res, out, model=model)
        b_diff, _ = ac.credit("difference")
        assert d[u, cc.HEAD_B] == min(0.0, float(b_diff[ac.served].min()))
        assert d[u, cc.HEAD_E] == model.outage_joules() == lp[u, cc.HEAD_E]
        assert lp[u, cc.HEAD_B] == 0.0
    assert tested >= 5, tested
    assert free_ride_possible     # without a charge, some state WOULD prefer outage


# ---------------------------------------------------------------- 6. non-additivity
def test_difference_credit_is_not_additive_and_obeys_the_documented_relation():
    model = {}

    def hook(env, a, masks, er):
        m = model.setdefault("m", cc.PowerModel.of(env))
        ctx = cc.difference_context(env, a, masks, er, model=m)
        se = env.environment
        base = se.evaluate_actions(a, er)
        ext = np.zeros(len(a))
        for u in range(len(a)):
            if a[u] < 0:
                continue
            wo = se.evaluate_actions_without_user(a, er, focal_user=u)
            gain = np.asarray(wo.link_rate_bps) - np.asarray(base.link_rate_bps)
            gain[u] = 0.0
            ext[u] = float(gain.sum()) * DT
        return ctx, ext

    strict_b = strict_e = False
    for seeds, rule in (((71, 72), "C1_A_m2dB"), ((73, 74), "random")):
        _, rows = _rollout(12, seeds, rule_name=rule, hook=hook)
        for _a, _m, res, out, (ctx, ext) in rows:
            m = model["m"]
            d = cc.credit_matrix("difference", res, out, model=m, ctx=ctx)
            served = np.asarray(out.resolution.served)
            bits = float(out.energy.system_throughput_bps) * DT
            joules = float(out.energy.system_consumed_power_w) * DT
            own = np.where(served, np.asarray(out.link_rate_bps) * DT, 0.0)
            bd, ed = d[served, cc.HEAD_B], d[served, cc.HEAD_E]
            # every externality of a removal is a GAIN for the others
            assert np.all(ext >= -1e-12 * bits)
            assert np.all(bd <= own[served] + 1e-12 * bits)
            assert bd.sum() <= bits * (1 + 1e-12)
            # documented relation: system bits - sum_u B^D_u = sum_u (others' gain when u leaves)
            assert bits - bd.sum() == pytest.approx(ext[served].sum(), rel=1e-6, abs=1e-9 * bits)
            assert np.all(ed >= 0.0) and ed.sum() <= joules * (1 + 1e-12)
            strict_b |= bd.sum() < bits * (1 - 1e-6)
            strict_e |= ed.sum() < joules * (1 - 1e-6)
    assert strict_b and strict_e


# ---------------------------------------------------------------- 7. what "without u" does
def test_without_u_changes_only_bandwidth_share_and_interference_from_its_beam():
    pre = {}

    def hook(env, a, masks, er):
        se = env.environment
        return {u: se.evaluate_actions_without_user(a, er, focal_user=u)
                for u in range(len(a)) if a[u] >= 0}

    env, rows = _rollout(24, (81, 82), hook=hook, steps=6)
    phys = env.environment.physics
    seen = dict(mates=0, victims=0, dark=0, sat_dark=0)
    for _a, _m, _res, out, evs in rows:
        facts = _beam_facts(out)
        n_beams = int(out.radiating.count)
        for u, ev in evs.items():
            pred = cc.without_user_rates(out, u, noise_power_w=phys.noise_power_w,
                                         bandwidth_hz=phys.beam_bandwidth_hz)
            np.testing.assert_allclose(np.asarray(ev.link_rate_bps), pred, rtol=1e-9, atol=0.0)
            if u not in facts:                        # outage: removal changes nothing
                np.testing.assert_array_equal(ev.link_rate_bps, out.link_rate_bps)
                continue
            f = facts[u]
            assert int(ev.radiating.count) == n_beams - (f["load"] == 1)
            sats = lambda r: len(set(np.asarray(r.norad_ids).tolist()))  # noqa: E731
            assert sats(ev.radiating) == sats(out.radiating) - (f["on_sat"] == 1)
            seen["mates"] += f["load"] > 1
            seen["dark"] += f["load"] == 1
            seen["sat_dark"] += f["on_sat"] == 1
            changed = np.asarray(ev.interference.total_w) < np.asarray(out.interference.total_w)
            seen["victims"] += int(changed.sum())
    assert all(v > 0 for v in seen.values()), seen


# ---------------------------------------------------------------- pools carry their credit
def test_pool_credit_is_recorded_and_checked_by_the_trainer():
    factory = _factory(6)
    rule = cfs.cf3_policies()["C1_A_m2dB"]
    seeds = [(9_141_000, 9_142_000)]
    p_d = cfr.generate_pool(lambda i: rule, env_factory=factory, seeds=seeds, config=_config(),
                            credit_mode="difference")
    p_e = cfr.generate_pool(lambda i: rule, env_factory=factory, seeds=seeds, config=_config())
    assert str(p_d["credit_mode"]) == "difference" and "credit_mode" not in p_e
    for f in ("states", "actions", "next_states", "masks", "dones"):
        np.testing.assert_array_equal(p_d[f], p_e[f])
    assert not np.array_equal(p_d["rewards_raw"], p_e["rewards_raw"])
    pools = [(n, h, cfr.PoolBuffer(p_d, sha256=f"d{j}"))
             for j, (n, h) in enumerate(cfr.source_names("cf3"))]
    assert all(b.credit_mode == "difference" for _n, _h, b in pools)
    with pytest.raises(MCRLContractError):
        cfr.CFRatioTrainer(factory(), _config(), _settings(source_kind="cf3"), pools=pools,
                           env_factory=factory)
    cfr.CFRatioTrainer(factory(), _config(),
                       _settings(source_kind="cf3", credit_mode="difference"),
                       pools=pools, env_factory=factory)


def test_pre_b1_resume_state_resumes_an_equal_share_learner_only():
    """A CF3 resume state (settings without ``credit_mode``) is an equal_share state."""
    import copy
    factory = _factory(6)

    def make(**kw):
        return cfr.CFRatioTrainer(factory(), _config(), _settings(**kw), env_factory=factory,
                                  train_seed=5, env_seed=6, mobility_seed=7)

    state = make().training_state_dict()            # nothing run, nothing updated
    assert state["cf"]["settings"]["credit_mode"] == "equal_share"
    old = copy.deepcopy(state)
    del old["cf"]["settings"]["credit_mode"]
    make().load_training_state_dict(copy.deepcopy(old))
    diff = make(credit_mode="difference")
    for st in (old, state):
        with pytest.raises(MCRLContractError):
            diff.load_training_state_dict(copy.deepcopy(st))
