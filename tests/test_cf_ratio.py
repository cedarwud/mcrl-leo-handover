"""CF3PILOT: the CF-ratio learner and its three sources (declaration + Amendment 1).

Every test here was first run against a named mutant of the implementation
and seen to FAIL (``CF_MUTANT=<name> pytest tests/test_cf_ratio.py -k ...``),
then against the real code and seen to PASS.  Mutants are applied by the
autouse ``mutant`` fixture with ``monkeypatch``; the source files are never
edited.  The red/green log is in ``.scratch/cf3-pilot/PROGRESS.md``.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import os
from pathlib import Path

import numpy as np
import pytest
import torch

from mcrl.algorithms import cf_ratio as cfr
from mcrl.algorithms import cf_sources as cfs
from mcrl.env.action_contract import HandoverClass
from mcrl.env.constants import DECISION_STEP_S
from mcrl.runtime.trainer_config_validation import TD_BOOTSTRAP_SHARED
from mcrl.runtime.trainer_spec import TrainerConfig

PINNED_LOCAL = Path("/home/u24/mcrl-runtime/tle-pinned-427e6a91")
FRONTIER = Path(
    "/home/u24/papers/mcrl-leo-handover/.scratch/feasible-frontier/scripts/frontier.py"
)
MUTANT = os.environ.get("CF_MUTANT", "")


# ---------------------------------------------------------------- mutants
@pytest.fixture(autouse=True)
def mutant(monkeypatch):
    T = cfr.CFRatioTrainer
    if MUTANT == "e_not_divided_by_u":
        real = cfr.cf_reward_matrix

        def bad(result, outcome, *, dt=cfr.DT_S):
            out = real(result, outcome, dt=dt)
            out[:, cfr.HEAD_E] *= len(result.rewards)
            return out

        monkeypatch.setattr(cfr, "cf_reward_matrix", bad)
    elif MUTANT == "per_head_max_bootstrap":
        def bad_targets(self, batch, head):
            ns = torch.tensor(batch["next_states"], dtype=torch.float32)
            nm = torch.tensor(batch["next_masks"], dtype=torch.bool)
            dn = torch.tensor(batch["dones"], dtype=torch.float32)
            r = torch.tensor(self._normalise(batch["rewards_raw"])[:, head])
            with torch.no_grad():
                q = self.target_nets[head](ns).masked_fill(~nm, -1e9)
                return r + self.config.discount_factor * q.max(dim=1).values * (1 - dn)

        monkeypatch.setattr(T, "head_targets", bad_targets)
    elif MUTANT == "eta_frozen_at_init":
        real_init = T.__init__

        def init(self, *a, **k):
            real_init(self, *a, **k)
            self._frozen = self.eta * self.settings.joules_scale / self.settings.bits_scale

        monkeypatch.setattr(T, "__init__", init)
        monkeypatch.setattr(T, "eta_tilde", property(lambda self: self._frozen))
    elif MUTANT in ("fraction_one_ninth_each", "min_one_source_sample",
                    "source_uses_main_env_rng"):
        real_init = T.__init__

        def init(self, *a, **k):
            real_init(self, *a, **k)
            if not self.sources:
                return
            if MUTANT == "fraction_one_ninth_each":
                self.n_per_source = round(self.settings.rho * self.config.batch_size)
                self.n_main = self.config.batch_size - 3 * self.n_per_source
            elif MUTANT == "min_one_source_sample":
                self.n_per_source = max(1, self.n_per_source)
                self.n_main = self.config.batch_size - 3 * self.n_per_source
            else:
                for src in self.sources:
                    src.env_rng = self._env_rng

        monkeypatch.setattr(T, "__init__", init)
    elif MUTANT == "null_smaller_buffer":
        real_build = cfr.build_sources

        def build(kind, **kw):
            if kind == "null3":
                kw = dict(kw, capacity=kw["capacity"] // 2)
            return real_build(kind, **kw)

        monkeypatch.setattr(cfr, "build_sources", build)
    elif MUTANT == "null_biased_to_first_legal":
        def biased(rng):
            def fn(states, masks):
                out = np.full(len(masks), -1, dtype=np.int64)
                for u, m in enumerate(masks):
                    v = np.flatnonzero(m.mask)
                    if v.size:
                        out[u] = int(v[0] if rng.random() < 0.2 else rng.choice(v))
                return out
            return fn

        monkeypatch.setattr(cfs, "random_legal", biased)
    elif MUTANT == "c2_margin_9db":
        real = cfs.cf3_policies

        def pol():
            p = real()
            p["C2_A_m12dB"] = cfs.make_rule(margin_db=9.0)
            return p

        monkeypatch.setattr(cfs, "cf3_policies", pol)
    elif MUTANT == "resume_forgets_catfish_rng":
        real_load = T.load_training_state_dict

        def load(self, state):
            keep = copy.deepcopy(self._catfish_rng.bit_generator.state)
            real_load(self, state)
            self._catfish_rng.bit_generator.state = keep

        monkeypatch.setattr(T, "load_training_state_dict", load)
    elif MUTANT == "eta_every_quarter":
        real_q = T.quarter_update

        def q(self, episode_done, *, final=False):
            self.settings = dataclasses.replace(self.settings, eta_first_update_episode=0)
            return real_q(self, episode_done, final=final)

        monkeypatch.setattr(T, "quarter_update", q)
    elif MUTANT == "b1_incumbent_fallback":
        real = cfs.pick

        def bad_pick(gain, legal, allowed, inc, margin_db):
            if inc >= 0 and legal[inc]:
                return inc
            return real(gain, legal, allowed, inc, margin_db)

        monkeypatch.setattr(cfs, "pick", bad_pick)
    elif MUTANT == "no_time_feature":
        real_enc = T.encode_at

        def enc(self, states, t):
            return real_enc(self, states, 0)

        monkeypatch.setattr(T, "encode_at", enc)
    elif MUTANT:
        raise AssertionError(f"unknown mutant {MUTANT}")
    yield


# ---------------------------------------------------------------- helpers
class _StubEnv:
    """Only what ``MODQNTrainer.__init__`` reads; never stepped."""

    num_beams_total = 28

    class config:  # noqa: N801
        num_users = 4
        steps_per_episode = 10

    def reset(self, *_a, **_k):  # pragma: no cover
        raise AssertionError("stub env is not stepped")


def _config(**kw) -> TrainerConfig:
    base = dict(learning_rate=0.001, episodes=3, epsilon_decay_episodes=2,
                td_bootstrap_mode=TD_BOOTSTRAP_SHARED, batch_size=18,
                replay_capacity=5000, target_update_every_episodes=1,
                discount_factor=1.0)
    base.update(kw)
    return TrainerConfig(**base)


def _settings(kind="cf3", **kw) -> cfr.CFRatioSettings:
    base = dict(source_kind=kind, eta0=2.0, bits_scale=10.0, joules_scale=4.0,
                quarter_episodes=10_000, catfish_buffer_capacity=5000,
                calibration_episodes=1)
    base.update(kw)
    return cfr.CFRatioSettings(**base)


def _push(buf, n, *, action, marker, rng, h=0.0, dim=113):
    for _ in range(n):
        s = rng.normal(size=dim).astype(np.float32)
        s[0] = marker
        m = np.ones(28, dtype=bool)
        buf.push(s, int(action), np.array([100.0, 8.0, h]), s.copy(), m, m.copy(), False)


def _real_env_factory(users):
    if not PINNED_LOCAL.is_dir():
        pytest.skip("pinned local TLE archive not present")
    os.environ["MCRL_TLE_ROOT"] = str(PINNED_LOCAL)
    from mcrl.runtime.training_pipeline import make_training_environment
    return lambda: make_training_environment(users=users)


def _trainer_real(kind, *, rho=1 / 9, cfg_kw=None, st_kw=None, users=6):
    factory = _real_env_factory(users)
    cfg = _config(**(cfg_kw or {}))
    return cfr.CFRatioTrainer(
        factory(), cfg, _settings(kind, rho=rho, **(st_kw or {})),
        env_factory=factory, train_seed=5, env_seed=6, mobility_seed=7,
    )


def _weights(tr):
    return [p.detach().clone() for net in tr.q_nets for p in net.parameters()]


def _fixed_bias_nets(trainer, biases):
    for net, b in zip(trainer.target_nets, biases):
        for layer in net.net:
            if isinstance(layer, torch.nn.Linear):
                torch.nn.init.zeros_(layer.weight)
                torch.nn.init.zeros_(layer.bias)
        net.net[-1].bias.data = torch.tensor(b, dtype=torch.float32)


def _batch(n=5):
    return {"states": np.zeros((n, 113), np.float32), "actions": np.zeros(n, np.int64),
            "rewards_raw": np.tile(np.array([10.0, 4.0, 1.0], np.float32), (n, 1)),
            "next_states": np.zeros((n, 113), np.float32),
            "next_masks": np.ones((n, 28), dtype=bool),
            "dones": np.zeros(n, np.float32), "source": np.full(n, -1)}


# ---------------------------------------------------------------- tests
def test_reward_vector_sums_to_evaluator_bits_and_joules():
    """sum_u B_u == evaluator bits, sum_u E_u == evaluator joules, H == phi2."""
    env = _real_env_factory(10)()
    rng = np.random.default_rng(3)
    env_rng, mob_rng = np.random.default_rng(11), np.random.default_rng(12)
    states, masks, _ = env.reset(env_rng, mob_rng)
    bits = joules = 0.0
    tot = np.zeros(3)
    n_inter = 0
    for _t in range(env.config.steps_per_episode):
        a = cfs.random_legal(rng)(states, masks)
        res = env.step(a, env_rng)
        out = env.last_outcome
        raw = cfr.cf_reward_matrix(res, out)
        bits += float(out.energy.system_throughput_bps) * DECISION_STEP_S
        joules += float(out.energy.system_consumed_power_w) * DECISION_STEP_S
        tot += raw.sum(axis=0)
        n_inter += sum(c is HandoverClass.INTER_SATELLITE for c in out.handovers)
        for uid, ok in enumerate(res.served):
            if not ok:
                assert raw[uid, cfr.HEAD_B] == 0.0
        states, masks = res.user_states, res.action_masks
    assert tot[cfr.HEAD_B] == pytest.approx(bits, rel=1e-12)
    assert tot[cfr.HEAD_E] == pytest.approx(joules, rel=1e-12)
    assert tot[cfr.HEAD_H] == n_inter


def test_three_heads_share_the_combined_continuation_action():
    tr = cfr.CFRatioTrainer(_StubEnv(), _config(), _settings("none"))
    qb = np.zeros(28); qe = np.zeros(28); qh = np.zeros(28)
    qb[3], qe[3] = 5.0, 4.0     # best bits, expensive in joules
    qb[7], qe[7] = 3.0, 0.5     # the combined winner
    qh[9] = 50.0                # Q_H's own max is elsewhere
    _fixed_bias_nets(tr, [qb, qe, qh])
    tr.eta, tr.lam = 2.0, 0.0   # eta~ = 2 * 4/10 = 0.8
    b = _batch()
    a_star = tr.continuation_actions(b).squeeze(1).numpy()
    assert (a_star == 7).all()  # 5-3.2=1.8 < 3-0.4=2.6
    ys = [tr.head_targets(b, k).numpy() for k in range(3)]
    np.testing.assert_allclose(ys[cfr.HEAD_B], 1.0 + 3.0, rtol=1e-6)   # gamma = 1
    np.testing.assert_allclose(ys[cfr.HEAD_E], 1.0 + 0.5, rtol=1e-6)
    np.testing.assert_allclose(ys[cfr.HEAD_H], 1.0 + 0.0, rtol=1e-6)
    b["dones"][:] = 1.0                                    # true terminal
    np.testing.assert_allclose(tr.head_targets(b, cfr.HEAD_B).numpy(), 1.0, rtol=1e-6)


def test_target_recomputed_when_eta_changes_and_stored_rewards_do_not():
    tr = cfr.CFRatioTrainer(_StubEnv(), _config(), _settings("none"))
    qb = np.zeros(28); qe = np.zeros(28)
    qb[3], qe[3] = 5.0, 4.0
    qb[7], qe[7] = 3.0, 0.5
    _fixed_bias_nets(tr, [qb, qe, np.zeros(28)])
    _push(tr.replay, 30, action=1, marker=0.0, rng=np.random.default_rng(0))
    before = [t[2].copy() for t in tr.replay._buf]
    b = _batch()
    tr.eta = 0.1                                  # eta~ = 0.04 -> a* = 3
    y_low = tr.head_targets(b, cfr.HEAD_E).numpy().copy()
    tr.eta = 2.0                                  # eta~ = 0.8  -> a* = 7
    y_high = tr.head_targets(b, cfr.HEAD_E).numpy().copy()
    np.testing.assert_allclose(y_low, 1.0 + 4.0, rtol=1e-6)
    np.testing.assert_allclose(y_high, 1.0 + 0.5, rtol=1e-6)
    after = [t[2] for t in tr.replay._buf]
    assert all(np.array_equal(x, y) for x, y in zip(before, after))
    assert all(np.array_equal(x, [100.0, 8.0, 0.0]) for x in after)  # raw, unshaped


def _filled(kind, seed=1):
    tr = cfr.CFRatioTrainer(_StubEnv(), _config(batch_size=128),
                            _settings(kind), env_factory=_StubEnv)
    rng = np.random.default_rng(seed)
    _push(tr.replay, 400, action=0, marker=-1.0, rng=rng)
    for i, src in enumerate(tr.sources):
        _push(src.buffer, 200, action=10 + i, marker=float(i + 1), rng=rng)
    return tr


def test_source_fractions_exact_common_to_all_heads_and_reproducible():
    tr = _filled("cf3")
    assert tr.n_per_source == 5 and tr.n_main == 113     # 128/27 = 4.74 -> 5
    assert [s.head for s in tr.sources] == [cfs.HEAD_B, cfs.HEAD_H, cfs.HEAD_E]
    b = tr._assemble_batch()
    markers = b["states"][:, 0]
    assert len(markers) == 128
    assert int(np.sum(markers == -1.0)) == 113
    for i in range(3):
        assert int(np.sum(markers == float(i + 1))) == 5
        assert int(np.sum(b["source"] == i)) == 5
    b2 = _filled("cf3")._assemble_batch()
    for k in b:
        np.testing.assert_array_equal(b[k], b2[k])
    seen = []
    orig = tr.head_targets
    tr.head_targets = lambda batch, head: (seen.append(id(batch)), orig(batch, head))[1]
    tr.update()
    assert len(seen) == 3 and len(set(seen)) == 1          # one batch, all heads


def test_rho_zero_cf3_is_bit_identical_to_off():
    off = _trainer_real("none", rho=0.0)
    logs_off = off.train_cf(progress_every=0)
    cf0 = _trainer_real("cf3", rho=0.0)
    logs_cf0 = cf0.train_cf(progress_every=0)
    assert cf0.n_per_source == 0
    assert all(len(s.buffer) > 0 for s in cf0.sources)   # sources did run
    for a, b in zip(_weights(off), _weights(cf0)):
        assert torch.equal(a, b)
    for x, y in zip(logs_off, logs_cf0):
        assert x["bits"] == y["bits"] and x["losses"] == y["losses"]


def test_a1_a2_main_rollouts_identical_before_first_source_sample():
    """Source envs do not perturb the main env's RNG or state."""
    big = {"batch_size": 5000, "episodes": 2}          # no update ever runs
    a1 = _trainer_real("none", cfg_kw=big)
    a2 = _trainer_real("cf3", cfg_kw=big)
    l1, l2 = a1.train_cf(progress_every=0), a2.train_cf(progress_every=0)
    assert all(x["updates"] == 0 for x in l1 + l2)
    for x, y in zip(l1, l2):
        for k in ("bits", "joules", "h_inter", "h_intra", "served", "beams"):
            assert x[k] == y[k]
    assert len(a1.replay) == len(a2.replay)
    for p, q in zip(a1.replay._buf, a2.replay._buf):
        assert np.array_equal(p[0], q[0]) and p[1] == q[1] and np.array_equal(p[2], q[2])
    assert a1._env_rng.bit_generator.state == a2._env_rng.bit_generator.state


def test_null3_differs_from_cf3_only_in_the_source_policy():
    a = cfr.CFRatioTrainer(_StubEnv(), _config(), _settings("cf3"), env_factory=_StubEnv)
    b = cfr.CFRatioTrainer(_StubEnv(), _config(), _settings("null3"), env_factory=_StubEnv)
    sa, sb = dataclasses.asdict(a.settings), dataclasses.asdict(b.settings)
    assert {k for k in sa if sa[k] != sb[k]} == {"source_kind"}
    assert (a.n_per_source, a.n_main) == (b.n_per_source, b.n_main)
    assert [s.head for s in a.sources] == [s.head for s in b.sources]
    assert [s.buffer.capacity for s in a.sources] == [s.buffer.capacity for s in b.sources]
    cf3 = _trainer_real("cf3")
    cf3.train_cf(progress_every=0)
    nul = _trainer_real("null3")
    for src, (name, _h) in zip(nul.sources, cfs.CF3_SPECS):
        src.policy = cfs.cf3_policies()[name]
    nul.train_cf(progress_every=0)
    for x, y in zip(_weights(cf3), _weights(nul)):
        assert torch.equal(x, y)
    raw_null = _trainer_real("null3")
    raw_null.train_cf(progress_every=0)
    assert any(not torch.equal(x, y) for x, y in zip(_weights(cf3), _weights(raw_null)))


def test_null3_is_uniform_over_legal_actions():
    from mcrl.env.step_types import ActionMask
    rng = np.random.default_rng(0)
    legal = np.zeros(28, dtype=bool)
    legal[[1, 4, 9, 27]] = True
    masks = [ActionMask(mask=legal.copy()) for _ in range(20_000)]
    acts = cfs.random_legal(rng)(None, masks)
    assert set(np.unique(acts)) == {1, 4, 9, 27}
    freq = np.bincount(acts, minlength=28)[[1, 4, 9, 27]] / len(acts)
    assert np.all(np.abs(freq - 0.25) < 0.015)
    empty = [ActionMask(mask=np.zeros(28, dtype=bool))]
    assert cfs.random_legal(rng)(None, empty)[0] == -1


def _frontier_rules():
    """frontier.py's own ``pick``/``make_rule``/``r_no_new_beam``, exec'd."""
    if not FRONTIER.is_file():
        pytest.skip("frontier.py not present")
    tree = ast.parse(FRONTIER.read_text())
    keep = [n for n in tree.body if isinstance(n, ast.FunctionDef)
            and n.name in {"incumbent_slot", "pick", "make_rule", "r_no_new_beam"}]
    from mcrl.env.action_contract import NO_OP_ACTION, NUM_BEAM_SLOTS, no_op_actions
    ns = {"np": np, "NO_OP_ACTION": NO_OP_ACTION, "NUM_BEAM_SLOTS": NUM_BEAM_SLOTS,
          "no_op_actions": no_op_actions}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(FRONTIER), "exec"), ns)
    return {
        "C1_A_m2dB": ns["make_rule"](margin_db=2.0),
        "C2_A_m12dB": ns["make_rule"](margin_db=12.0),
        "C3_B1_NO_NEW_BEAM": ns["make_rule"](restrict=ns["r_no_new_beam"]),
    }


def test_source_parity_with_feasfront_rules():
    ref = _frontier_rules()
    ours = cfs.cf3_policies()
    factory = _real_env_factory(20)
    for name in ours:
        env = factory()
        env_rng, mob = np.random.default_rng(21), np.random.default_rng(22)
        states, masks, _ = env.reset(env_rng, mob)
        for _t in range(6):
            a = ours[name](states, masks)
            np.testing.assert_array_equal(a, ref[name](None, None, masks, states))
            res = env.step(a, env_rng)
            states, masks = res.user_states, res.action_masks


def test_resume_does_not_repeat_episodes_and_is_bit_identical():
    full = _trainer_real("cf3", cfg_kw={"episodes": 4})
    logs_full = full.train_cf(progress_every=0)
    part = _trainer_real("cf3", cfg_kw={"episodes": 4})
    part.config = dataclasses.replace(part.config, episodes=2)
    logs_a = part.train_cf(progress_every=0)
    state = copy.deepcopy(part.training_state_dict())
    fresh = _trainer_real("cf3", cfg_kw={"episodes": 4})
    fresh.config = dataclasses.replace(fresh.config, episodes=2)
    fresh.load_training_state_dict(state)
    fresh.config = dataclasses.replace(fresh.config, episodes=4)
    logs = fresh.train_cf(start_episode=2, initial_logs=logs_a, progress_every=0)
    assert [r["episode"] for r in logs] == [0, 1, 2, 3]
    for x, y in zip(_weights(full), _weights(fresh)):
        assert torch.equal(x, y)
    assert [r["bits"] for r in logs] == [r["bits"] for r in logs_full]


def test_eta_and_lambda_change_only_at_declared_boundaries():
    tr = _trainer_real("none", cfg_kw={"episodes": 4},
                       st_kw={"quarter_episodes": 1, "eta_first_update_episode": 2,
                              "h_cap_inter": 0.0})       # cap 0 -> lambda must rise
    calls = []
    tr.learning_gate = lambda ep, row: calls.append(ep)
    logs = tr.train_cf(progress_every=0)
    etas = [r["eta"] for r in logs]
    lams = [r["lambda"] for r in logs]
    # log["eta"] is the value IN FORCE during that episode; the update at
    # episode_done = k (end of episode index k-1) governs episode index k.
    assert etas[0] == etas[1] == 2.0                      # held until the ep-2 update
    assert etas[2] == logs[1]["quarter"]["measured_ee"] != 2.0
    assert etas[3] == logs[2]["quarter"]["measured_ee"]
    assert lams[0] == 0.0 and lams[1] > 0.0               # lambda from quarter 1
    assert calls == [2]                                   # gate only at first eta update
    assert logs[3]["quarter"]["applied"] is False         # final measurement recorded only
    assert tr.eta == etas[3]

    def stop(ep, row):
        raise cfr.LearningCheckStop("fail")
    tr2 = _trainer_real("none", cfg_kw={"episodes": 4},
                        st_kw={"quarter_episodes": 1, "eta_first_update_episode": 2})
    tr2.learning_gate = stop
    with pytest.raises(cfr.LearningCheckStop):
        tr2.train_cf(progress_every=0)
    assert tr2.eta == 2.0                                 # no update applied


def test_remaining_steps_feature_is_appended():
    tr = cfr.CFRatioTrainer(_StubEnv(), _config(), _settings("none"))
    assert tr.state_dim == 113 and tr.q_nets[0].net[0].in_features == 113
    env = _real_env_factory(4)()
    states, _m, _ = env.reset(np.random.default_rng(1), np.random.default_rng(2))
    tr.env = env
    for t in (0, 3, 9):
        enc = tr.encode_at(states, t)
        assert enc.shape == (4, 113)
        np.testing.assert_allclose(enc[:, -1], (10 - t) / 10)
        np.testing.assert_array_equal(enc[:, :112], tr._encode_states(states))


def test_b1_never_undoes_its_restriction_by_an_incumbent_hold():
    gain = np.linspace(1.0, 2.0, 28)
    legal = np.ones(28, dtype=bool)
    load = np.zeros(28)
    load[[2, 5]] = 1.0
    inc = 20
    allowed = cfs.r_no_new_beam(gain, load, inc, legal)
    assert cfs.pick(gain, legal, allowed, inc, 0.0) == 5
