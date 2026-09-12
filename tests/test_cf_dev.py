"""DEVHARNESS E0 preflight (Amendment 6 section 5).

Every test here was first run against a NAMED MUTANT of the implementation and
seen to FAIL (``DEV_MUTANT=<name> pytest tests/test_cf_dev.py -k ...``), then
against the real code and seen to PASS.  Mutants are applied by the autouse
``mutant`` fixture with ``monkeypatch``; no source file is edited.  The red/green
log is in ``.scratch/dev-training/PROGRESS.md``.

Development lane: these tests may run optimizer steps on tiny runs (Amendment 6
lifts the formal lanes' no-training boundary for E0), but they never touch a
formal evaluation, calibration or CONFIRM episode.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import os
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import pytest
import torch

from mcrl.algorithms import cf_dev as cfd
from mcrl.algorithms import cf_ratio as cfr
from mcrl.algorithms import cf_teacher as cft
from mcrl.env.step_types import ActionMask
from mcrl.errors import MCRLContractError
from mcrl.runtime.replay_buffer import ReplayBuffer
from mcrl.runtime.trainer_config_validation import TD_BOOTSTRAP_SHARED
from mcrl.runtime.trainer_spec import TrainerConfig

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
PINNED_LOCAL = Path("/home/u24/mcrl-runtime/tle-pinned-427e6a91")
LP_COMMON = Path(
    "/home/u24/papers/mcrl-leo-handover/.scratch/h4-probe/scripts/lp_common.py"
)
MUTANT = os.environ.get("DEV_MUTANT", "")
CALIB = {"eta0_bit_per_J": 110_507_234.83444457,
         "bits_scale": 13_329_082_278.45065,
         "joules_scale": 120.61728174105066}


# ---------------------------------------------------------------- mutants
@pytest.fixture(autouse=True)
def mutant(monkeypatch):
    T = cfd.CFDevTrainer
    if MUTANT == "t0_from_encoded_observation":
        real = cft.t0_scores

        def bad(states, masks, c=cft.T0_C):
            scores, acts, legal = real(states, masks, c)
            # the log1p-encoded observation's float32 SINR block, decoded back
            for u, s in enumerate(states):
                g = np.asarray(s.channel_quality, dtype=np.float64)
                enc = np.log1p(g).astype(np.float32).astype(np.float64)
                load = np.asarray(s.beam_loads, dtype=np.float64)
                scores[u] = enc / float(np.log(2.0)) - c * (load == 0.0)
            return scores, acts, legal

        monkeypatch.setattr(cft, "t0_scores", bad)
    elif MUTANT == "t0_tie_break_last":
        def bad(states, masks, c=cft.T0_C):
            users = len(states)
            scores = np.zeros((users, 28), dtype=np.float64)
            legal_mask = np.zeros((users, 28), dtype=bool)
            acts = np.full(users, -1, dtype=np.int64)
            for u, s in enumerate(states):
                legal = np.asarray(masks[u].mask, dtype=bool)
                g = np.maximum(np.asarray(s.channel_quality, dtype=np.float64), 0.0)
                load = np.asarray(s.beam_loads, dtype=np.float64)
                sc = np.log2(1.0 + g) - c * (load == 0.0)
                scores[u], legal_mask[u] = sc, legal
                ok = np.flatnonzero(legal)
                if ok.size:
                    best = sc[ok].max()
                    acts[u] = int(ok[np.flatnonzero(sc[ok] == best)[-1]])
            return scores, acts, legal_mask

        monkeypatch.setattr(cft, "t0_scores", bad)
    elif MUTANT == "t0_no_prev_step_penalty":
        real = cft.t0_scores
        monkeypatch.setattr(cft, "t0_scores",
                            lambda states, masks, c=cft.T0_C: real(states, masks, 0.0))
    elif MUTANT == "t0_argmax_ignores_mask":
        def bad(states, masks, c=cft.T0_C):
            scores, acts, legal = cft.t0_scores.__wrapped__(states, masks, c) \
                if hasattr(cft.t0_scores, "__wrapped__") else _real_t0(states, masks, c)
            for u in range(len(states)):
                acts[u] = int(np.argmax(scores[u]))
            return scores, acts, legal

        monkeypatch.setattr(cft, "t0_scores", bad)
    elif MUTANT == "d2_sign_flipped":
        real = cft.d2_ce_loss
        monkeypatch.setattr(cft, "d2_ce_loss",
                            lambda s, m, p, ts: -real(s, m, p, ts))
    elif MUTANT == "d2_ignores_mask":
        def bad(scores, mask, p_target, tau_s):
            log_q = torch.nn.functional.log_softmax(scores / tau_s, dim=1)
            return -(p_target * log_q).sum(dim=1).mean()

        monkeypatch.setattr(cft, "d2_ce_loss", bad)
    elif MUTANT == "d2_target_not_normalised":
        monkeypatch.setattr(
            cft, "soft_targets",
            lambda s, m, tau: np.where(np.asarray(m, bool),
                                       np.asarray(s, np.float64) / tau, 0.0).astype(np.float32),
        )
    elif MUTANT == "d2_only_qb":
        monkeypatch.setattr(cft, "student_scores",
                            lambda qb, qe, qh, eta_tilde, lam: qb)
    elif MUTANT == "d3_margin_on_teacher_action":
        def bad(scores, mask, a_teacher, margin):
            a_col = a_teacher.view(-1, 1)
            marg = torch.zeros_like(scores)
            marg.scatter_(1, a_col, float(margin))
            q = (scores + marg).masked_fill(~mask, cft.MASK_FILL)
            return (q.max(dim=1).values - scores.gather(1, a_col).squeeze(1)).mean()

        monkeypatch.setattr(cft, "d3_margin_loss", bad)
    elif MUTANT == "d3_max_over_illegal":
        def bad(scores, mask, a_teacher, margin):
            a_col = a_teacher.view(-1, 1)
            marg = torch.full_like(scores, float(margin))
            marg.scatter_(1, a_col, 0.0)
            q = scores + marg
            return (q.max(dim=1).values - scores.gather(1, a_col).squeeze(1)).mean()

        monkeypatch.setattr(cft, "d3_margin_loss", bad)
    elif MUTANT == "d3_no_margin":
        real = cft.d3_margin_loss
        monkeypatch.setattr(cft, "d3_margin_loss",
                            lambda s, m, a, margin: real(s, m, a, 0.0))
    elif MUTANT == "null_permutes_across_the_mask":
        def bad(scores, mask, rng):
            out = np.array(scores, dtype=np.float64, copy=True)
            for u in range(out.shape[0]):
                out[u] = out[u][rng.permutation(out.shape[1])]
            return out

        monkeypatch.setattr(cft, "permute_scores_among_legal", bad)
    elif MUTANT == "null_keeps_the_argmax":
        real = cft.permute_scores_among_legal

        def bad(scores, mask, rng):
            out = real(scores, mask, rng)
            for u in range(out.shape[0]):
                idx = np.flatnonzero(mask[u])
                if idx.size > 1:
                    top = int(idx[int(np.argmax(np.asarray(scores[u])[idx]))])
                    hi = int(idx[int(np.argmax(out[u][idx]))])
                    out[u, top], out[u, hi] = out[u, hi], out[u, top]
            return out

        monkeypatch.setattr(cft, "permute_scores_among_legal", bad)
    elif MUTANT == "null_uses_train_rng":
        real = T.teacher_labels

        def bad(self, states, masks):
            if self.dev.mechanism == "D2-null":
                self._null_rng = self._train_rng
            return real(self, states, masks)

        monkeypatch.setattr(T, "teacher_labels", bad)
    elif MUTANT == "teacher_applied_at_zero_weight":
        def bad(self, batch, q_all):
            d = self.dev
            if not d.uses_teacher:
                return None
            mask = torch.tensor(np.asarray(batch["masks"], dtype=bool), dtype=torch.bool)
            scores = cft.student_scores(q_all[0], q_all[1], q_all[2],
                                        self.eta_tilde, self.lam)
            if d.mechanism.startswith("D2"):
                p = torch.tensor(cft.soft_targets(batch["teacher_scores"],
                                                  batch["masks"], d.tau))
                return cft.d2_ce_loss(scores, mask, p, d.tau_s)      # weight dropped
            a_t = torch.tensor(np.asarray(batch["teacher_action"], np.int64))
            return cft.d3_margin_loss(scores, mask, a_t, d.margin)   # weight dropped

        monkeypatch.setattr(T, "_teacher_loss", bad)
    elif MUTANT == "dev_loop_freezes_the_time_feature":
        real = T.encode_at
        monkeypatch.setattr(T, "encode_at",
                            lambda self, states, t: real(self, states, 0))
    elif MUTANT == "replay_labels_misaligned":
        real = cfd.TeacherReplayBuffer.sample

        def bad(self, batch_size, rng):
            out = real(self, batch_size, rng)
            for key in ("t0_action", "teacher_action", "teacher_scores"):
                self._last[key] = np.roll(self._last[key], 1, axis=0)
            return out

        monkeypatch.setattr(cfd.TeacherReplayBuffer, "sample", bad)
    elif MUTANT == "resume_drops_teacher_labels":
        real = cfd.TeacherReplayBuffer.state_dict

        def bad(self):
            state = real(self)
            state["teacher_labels"] = [
                (0, int(a1), np.zeros_like(s)) for _a0, a1, s in state["teacher_labels"]
            ]
            return state

        monkeypatch.setattr(cfd.TeacherReplayBuffer, "state_dict", bad)
    elif MUTANT == "devval_consumes_train_rng":
        real = T.devval

        def bad(self):
            self._train_rng.random()
            return real(self)

        monkeypatch.setattr(T, "devval", bad)
    elif MUTANT == "devval_uses_formal_evaluation_seeds":
        monkeypatch.setattr(cfd, "assert_dev_seed", lambda seed, what="": 0)
        monkeypatch.setattr(cfd, "assert_dev_seed_pairs", lambda seeds, what="": None)
        monkeypatch.setattr(
            T, "devval_seeds",
            lambda self: [(9_111_000 + i, 9_112_000 + i)
                          for i in range(self.dev.devval_episodes)],
        )
    elif MUTANT == "dev_trainer_reads_calibration":
        monkeypatch.setattr(T, "measure_on_calibration",
                            cfr.CFRatioTrainer.measure_on_calibration)
        monkeypatch.setattr(T, "quarter_update", cfr.CFRatioTrainer.quarter_update)
    elif MUTANT == "d3null_target_is_t0_action":
        real = T.teacher_labels

        def bad(self, states, masks):
            t0, used, scores, legal, raw = real(self, states, masks)
            if self.dev.mechanism == "D3-null":
                used = t0
            return t0, used, scores, legal, raw

        monkeypatch.setattr(T, "teacher_labels", bad)
    elif MUTANT == "d3null_target_may_be_illegal":
        def bad(mask, rng):
            return np.asarray(rng.integers(0, mask.shape[1], size=mask.shape[0]),
                              dtype=np.int64)

        monkeypatch.setattr(cft, "random_legal_actions", bad)
    elif MUTANT == "d3null_uses_train_rng":
        real = T.teacher_labels

        def bad(self, states, masks):
            if self.dev.mechanism == "D3-null":
                self._null_rng = self._train_rng
            return real(self, states, masks)

        monkeypatch.setattr(T, "teacher_labels", bad)
    elif MUTANT == "d3null_scores_carry_t0":
        real = T.teacher_labels

        def bad(self, states, masks):
            t0, used, scores, legal, raw = real(self, states, masks)
            if self.dev.mechanism == "D3-null":
                scores = raw
            return t0, used, scores, legal, raw

        monkeypatch.setattr(T, "teacher_labels", bad)
    elif MUTANT == "d3null_key_dropped_from_hash":
        import dev_e0_common as D
        real = D.arm_config_payload

        def bad(*args, **kwargs):
            payload = real(*args, **kwargs)
            payload["dev_settings"].pop("null_key", None)
            return payload

        monkeypatch.setattr(D, "arm_config_payload", bad)
    elif MUTANT == "manifest_ignores_dev_settings":
        import dev_e0_common as D
        real = D.arm_config_payload

        def bad(*args, **kwargs):
            payload = real(*args, **kwargs)
            payload.pop("dev_settings", None)
            return payload

        monkeypatch.setattr(D, "arm_config_payload", bad)
    elif MUTANT:
        raise AssertionError(f"unknown mutant {MUTANT}")
    yield


def _real_t0(states, masks, c=cft.T0_C):
    """The unmutated T0 arithmetic (used by one mutant that needs the original)."""
    users = len(states)
    scores = np.zeros((users, 28), dtype=np.float64)
    legal_mask = np.zeros((users, 28), dtype=bool)
    acts = np.full(users, -1, dtype=np.int64)
    for u, s in enumerate(states):
        legal = np.asarray(masks[u].mask, dtype=bool)
        g = np.maximum(np.asarray(s.channel_quality, dtype=np.float64), 0.0)
        load = np.asarray(s.beam_loads, dtype=np.float64)
        sc = np.log2(1.0 + g) - c * (load == 0.0)
        scores[u], legal_mask[u] = sc, legal
        ok = np.flatnonzero(legal)
        if ok.size:
            acts[u] = int(ok[int(np.argmax(sc[ok]))])
    return scores, acts, legal_mask


# ---------------------------------------------------------------- helpers
def _config(**kw) -> TrainerConfig:
    base = dict(learning_rate=0.001, episodes=2, epsilon_decay_episodes=2,
                td_bootstrap_mode=TD_BOOTSTRAP_SHARED, batch_size=18,
                replay_capacity=5000, target_update_every_episodes=1,
                discount_factor=1.0)
    base.update(kw)
    return TrainerConfig(**base)


def _settings(**kw) -> cfr.CFRatioSettings:
    base = dict(source_kind="none", rho=1.0 / 9.0, eta0=2.0, bits_scale=10.0,
                joules_scale=4.0, quarter_episodes=10**9,
                eta_first_update_episode=10**9, calibration_episodes=0,
                calibration_env_seed_base=0, calibration_mobility_seed_base=0)
    base.update(kw)
    return cfr.CFRatioSettings(**base)


def _dev(mechanism="D0", **kw) -> cfd.DevSettings:
    teacher = {"D0": "none", "D3-null": "random"}.get(mechanism, "T0")
    null_key = {"D2-null": (9_231_000, 0), "D3-null": (9_241_000, 0)}.get(mechanism)
    base = dict(mechanism=mechanism, teacher=teacher, null_key=null_key,
                devval_episodes=1)
    base.update(kw)
    return cfd.DevSettings(**base)


def _real_env_factory(users):
    if not PINNED_LOCAL.is_dir():
        pytest.skip("pinned local TLE archive not present")
    os.environ["MCRL_TLE_ROOT"] = str(PINNED_LOCAL)
    from mcrl.runtime.training_pipeline import make_training_environment
    return lambda: make_training_environment(users=users)


def _trainer(mechanism="D0", *, users=6, cfg_kw=None, dev_kw=None, st_kw=None):
    factory = _real_env_factory(users)
    return cfd.CFDevTrainer(
        factory(), _config(**(cfg_kw or {})), _settings(**(st_kw or {})),
        _dev(mechanism, **(dev_kw or {})), env_factory=factory,
        train_seed=9_201_000, env_seed=9_202_000, mobility_seed=9_203_000,
    )


def _weights(tr):
    return [p.detach().clone() for net in tr.q_nets for p in net.parameters()]


def _states(n=40, seed=0, n_legal=None):
    """Synthetic raw user states: only channel_quality / beam_loads are read."""
    rng = np.random.default_rng(seed)
    states, masks = [], []
    for _ in range(n):
        gain = rng.gamma(2.0, 3.0, size=28)
        load = (rng.random(28) < 0.4).astype(float) * rng.integers(1, 5, size=28)
        k = n_legal if n_legal is not None else int(rng.integers(2, 28))
        legal = np.zeros(28, dtype=bool)
        legal[rng.choice(28, size=k, replace=False)] = True
        states.append(types.SimpleNamespace(channel_quality=gain, beam_loads=load))
        masks.append(ActionMask(mask=legal))
    return states, masks


# ---------------------------------------------------------------- T0 labels
def test_t0_labels_reproduce_the_verified_rule():
    """T0 = LP-prev(c=1, m=0) on the RAW state, first index on ties, masked.

    Red under: t0_from_encoded_observation, t0_tie_break_last,
    t0_no_prev_step_penalty, t0_argmax_ignores_mask.
    """
    states, masks = _states(60, seed=7)
    scores, acts, legal = cft.t0_scores(states, masks)
    ref_scores, ref_acts, _ = _real_t0(states, masks)
    np.testing.assert_array_equal(scores, ref_scores)      # EXACT: raw, not encoded
    np.testing.assert_array_equal(acts, ref_acts)
    for u in range(len(states)):
        assert legal[u][acts[u]], "T0 chose an illegal action"

    # explicit tie fixture: equal scores -> the FIRST legal index wins
    gain = np.full(28, 5.0)
    load = np.ones(28)
    legal_row = np.zeros(28, dtype=bool)
    legal_row[[3, 9, 17]] = True
    tie_state = types.SimpleNamespace(channel_quality=gain, beam_loads=load)
    _s, tie_acts, _m = cft.t0_scores([tie_state], [ActionMask(mask=legal_row)])
    assert int(tie_acts[0]) == 3

    # the previous-step penalty is load-bearing: an unlit beam is charged 1 bit
    gain2 = np.zeros(28)
    gain2[[3, 9]] = [7.0, 6.0]
    load2 = np.zeros(28)
    load2[9] = 2.0                       # slot 3 is brighter but lights a new beam
    legal2 = np.zeros(28, dtype=bool)
    legal2[[3, 9]] = True
    st2 = types.SimpleNamespace(channel_quality=gain2, beam_loads=load2)
    s2, a2, _m2 = cft.t0_scores([st2], [ActionMask(mask=legal2)])
    assert int(a2[0]) == 9
    assert s2[0, 3] == pytest.approx(np.log2(8.0) - 1.0)
    assert s2[0, 9] == pytest.approx(np.log2(7.0))


@pytest.mark.skipif(not LP_COMMON.is_file(), reason="LP probe file not present")
def test_t0_actions_equal_the_lp_probe_rule_on_real_states():
    """Parity with the verified ``lp_common.lp_prev_rule_factory(1, 0)`` itself.

    Red under: t0_tie_break_last, t0_no_prev_step_penalty, t0_argmax_ignores_mask.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("lp_common_ref", LP_COMMON)
    module = importlib.util.module_from_spec(spec)
    sys.modules["lp_common_ref"] = module
    try:
        spec.loader.exec_module(module)
    except Exception:                                   # pragma: no cover
        pytest.skip("lp_common could not be imported in this tree")
    rule = module.lp_prev_rule_factory(1.0, 0.0)
    factory = _real_env_factory(20)
    env = factory()
    states, masks, _ = env.reset(np.random.default_rng(9_202_000),
                                 np.random.default_rng(9_203_000))
    for _t in range(5):
        _s, acts, _m = cft.t0_scores(states, masks)
        np.testing.assert_array_equal(np.asarray(acts, dtype=np.int64),
                                      np.asarray(rule(states, masks), dtype=np.int64))
        res = env.step(acts, np.random.default_rng(9_202_000))
        states, masks = res.user_states, res.action_masks


# ---------------------------------------------------------------- D2
def _score_tensor(n=6, seed=1, requires_grad=True):
    g = torch.Generator().manual_seed(seed)
    return torch.randn(n, 28, generator=g, requires_grad=requires_grad)


def test_d2_loss_shape_sign_mask_and_target():
    """CE over LEGAL actions only, minimised when S matches the teacher.

    Red under: d2_sign_flipped, d2_ignores_mask, d2_target_not_normalised.
    """
    states, masks = _states(12, seed=3)
    scores, acts, legal = cft.t0_scores(states, masks)
    p = cft.soft_targets(scores, legal, 3.0)
    np.testing.assert_allclose(p.sum(1), 1.0, rtol=1e-6)
    assert np.all(p[~legal] == 0.0)
    mask_t = torch.tensor(legal)

    # a student that matches the teacher exactly has the lowest attainable loss
    matched = torch.tensor(scores / 3.0, dtype=torch.float32)
    worse = matched.clone()
    for u in range(len(states)):
        worse[u, acts[u]] -= 5.0
    p_t = torch.tensor(p)
    loss_matched = cft.d2_ce_loss(matched, mask_t, p_t, 1.0)
    loss_worse = cft.d2_ce_loss(worse, mask_t, p_t, 1.0)
    assert float(loss_matched) > 0.0
    assert float(loss_worse) > float(loss_matched)

    # illegal actions cannot change the loss
    shifted = matched.clone()
    shifted[~mask_t] += 100.0
    assert float(cft.d2_ce_loss(shifted, mask_t, p_t, 1.0)) == pytest.approx(
        float(loss_matched), rel=1e-6
    )

    # hand computation on one row
    row = torch.zeros(1, 28)
    m = torch.zeros(1, 28, dtype=torch.bool)
    m[0, [2, 5]] = True
    row[0, 2], row[0, 5] = 1.0, 0.0
    target = torch.zeros(1, 28)
    target[0, 2] = 1.0
    expected = float(np.log(1.0 + np.exp(-1.0)))       # -log softmax([1,0])[0]
    assert float(cft.d2_ce_loss(row, m, target, 1.0)) == pytest.approx(expected, rel=1e-6)


def test_d2_gradient_reaches_the_deployed_score_heads():
    """The D2 gradient flows into Q_B and Q_E through S = Q_B - eta~ Q_E.

    Red under: d2_only_qb, d2_sign_flipped.
    """
    tr = _trainer("D2-T0", users=6)
    st = torch.zeros(4, 113)
    q_all = [net(st) for net in tr.q_nets]
    batch = {"masks": np.ones((4, 28), dtype=bool),
             "teacher_scores": np.tile(np.arange(28, dtype=np.float64), (4, 1)),
             "teacher_action": np.full(4, 27, dtype=np.int64)}
    loss = tr._teacher_loss(batch, q_all)
    loss.backward()
    grads = [max(float(p.grad.abs().max()) for p in net.parameters() if p.grad is not None)
             for net in tr.q_nets]
    assert grads[0] > 0.0, "no gradient reached Q_B"
    assert grads[1] > 0.0, "no gradient reached Q_E"


# ---------------------------------------------------------------- D2-null
def test_d2_null_preserves_dimensions_mask_and_schedule():
    """The null permutes score VALUES among the legal slots and nothing else.

    Red under: null_permutes_across_the_mask.
    """
    states, masks = _states(50, seed=11)
    scores, _acts, legal = cft.t0_scores(states, masks)
    rng = np.random.default_rng((9_231_000, 0))
    permuted = cft.permute_scores_among_legal(scores, legal, rng)
    assert permuted.shape == scores.shape
    for u in range(len(states)):
        idx = np.flatnonzero(legal[u])
        np.testing.assert_array_equal(np.sort(permuted[u][idx]), np.sort(scores[u][idx]))
        np.testing.assert_array_equal(permuted[u][~legal[u]], scores[u][~legal[u]])
    # same schedule: the soft target's probability multiset per row is unchanged
    p0 = cft.soft_targets(scores, legal, 3.0)
    p1 = cft.soft_targets(permuted, legal, 3.0)
    for u in range(len(states)):
        np.testing.assert_allclose(np.sort(p0[u]), np.sort(p1[u]), rtol=1e-6)


def test_d2_null_carries_no_t0_action_information():
    """The null's argmax agrees with T0's at the chance rate, not above it.

    Red under: null_keeps_the_argmax, null_permutes_across_the_mask.
    """
    states, masks = _states(4000, seed=13)
    scores, acts, legal = cft.t0_scores(states, masks)
    rng = np.random.default_rng((9_231_000, 0))
    permuted = cft.permute_scores_among_legal(scores, legal, rng)
    null_acts = cft.masked_argmax_rows(permuted, legal)
    agree = float(np.mean(null_acts == acts))
    chance = float(np.mean(1.0 / legal.sum(1)))
    n = len(states)
    tol = 4.0 * float(np.sqrt(chance * (1.0 - chance) / n)) + 1e-3
    assert abs(agree - chance) < tol, f"agreement {agree} vs chance {chance}"
    assert float(np.mean(cft.masked_argmax_rows(scores, legal) == acts)) == 1.0


def test_d2_null_uses_only_its_own_generator_and_ignores_the_t0_action():
    """The DEV-NULL draw never touches a trainer stream; the loss never reads a_T0.

    Red under: null_uses_train_rng, replay_labels_misaligned.
    """
    tr = _trainer("D2-null", users=6)
    factory = _real_env_factory(6)
    env = factory()
    states, masks, _ = env.reset(np.random.default_rng(9_202_000),
                                 np.random.default_rng(9_203_000))
    before_train = copy.deepcopy(tr._train_rng.bit_generator.state)
    before_env = copy.deepcopy(tr._env_rng.bit_generator.state)
    t0_acts, used_acts, used_scores, legal, raw_scores = tr.teacher_labels(states, masks)
    assert tr._train_rng.bit_generator.state == before_train
    assert tr._env_rng.bit_generator.state == before_env
    assert not np.array_equal(used_scores, raw_scores)
    # the D2 loss reads the scores only: corrupting the stored T0 action changes nothing
    st = torch.zeros(3, 113)
    q_all = [net(st) for net in tr.q_nets]
    batch = {"masks": legal[:3], "teacher_scores": used_scores[:3],
             "teacher_action": used_acts[:3], "t0_action": t0_acts[:3]}
    a = float(tr._teacher_loss(batch, q_all).detach())
    batch["t0_action"] = np.zeros(3, dtype=np.int64)
    b = float(tr._teacher_loss(batch, q_all).detach())
    assert a == b


# ---------------------------------------------------------------- D3
def test_d3_margin_loss_properties():
    """max over LEGAL actions of S + m*1(a != a_T), minus S(a_T); >= 0.

    Red under: d3_margin_on_teacher_action, d3_max_over_illegal, d3_no_margin.
    """
    scores = torch.zeros(1, 28)
    mask = torch.zeros(1, 28, dtype=torch.bool)
    mask[0, [1, 4, 9]] = True
    a_t = torch.tensor([4])
    scores[0, 4] = 1.0
    scores[0, 1] = 0.95                          # inside the margin: loss must be > 0
    scores[0, 9] = 0.2
    scores[0, 27] = 99.0                         # illegal: must not enter the max
    loss = float(cft.d3_margin_loss(scores, mask, a_t, 0.15))
    assert loss == pytest.approx(max(0.95 + 0.15, 0.2 + 0.15, 1.0) - 1.0, rel=1e-6)
    assert loss == pytest.approx(0.1, rel=1e-5)  # the margin itself is load-bearing
    assert loss >= 0.0
    # satisfied margin -> exactly zero
    scores[0, 4] = 1.0
    scores[0, 1] = 0.5
    assert float(cft.d3_margin_loss(scores, mask, a_t, 0.15)) == 0.0
    # violated margin -> positive and pushing S(a_T) up
    s2 = scores.clone().requires_grad_(True)
    with torch.no_grad():
        s2[0, 1] = 1.1
    loss2 = cft.d3_margin_loss(s2, mask, a_t, 0.15)
    assert float(loss2) > 0.0
    loss2.backward()
    assert float(s2.grad[0, 4]) < 0.0            # increase S(a_T) to lower the loss
    assert float(s2.grad[0, 1]) > 0.0
    assert float(s2.grad[0, 27]) == 0.0
    with pytest.raises(MCRLContractError):
        cft.d3_margin_loss(scores, mask, torch.tensor([27]), 0.15)


# ---------------------------------------------------------------- equivalence
def test_teacher_weight_zero_reproduces_d0_bit_identically():
    """alpha = 0 (D2) and lambda_E = 0 (D3) reproduce D0 exactly, weights and logs.

    Red under: teacher_applied_at_zero_weight.
    """
    d0 = _trainer("D0", users=6)
    logs0 = d0.train_cf(progress_every=0)
    for mech, kw in (("D2-T0", {"alpha": 0.0}), ("D3-T0", {"lambda_e": 0.0}),
                     ("D2-null", {"alpha": 0.0}), ("D3-null", {"lambda_e": 0.0})):
        other = _trainer(mech, users=6, dev_kw=kw)
        logs = other.train_cf(progress_every=0)
        for x, y in zip(_weights(d0), _weights(other)):
            assert torch.equal(x, y), f"{mech} at zero weight moved the weights"
        for a, b in zip(logs0, logs):
            assert a["bits"] == b["bits"] and a["losses"] == b["losses"]
            assert a["updates"] == b["updates"]


def test_d0_development_run_reproduces_the_pilot_a1_learner():
    """The development loop is the pilot loop: D0 == CFRatioTrainer (source none).

    Red under: dev_loop_freezes_the_time_feature.
    """
    factory = _real_env_factory(6)
    base = cfr.CFRatioTrainer(factory(), _config(), _settings(), env_factory=factory,
                              pools=None, train_seed=9_201_000, env_seed=9_202_000,
                              mobility_seed=9_203_000)
    logs_base = base.train_cf(progress_every=0)
    dev = _trainer("D0", users=6)
    logs_dev = dev.train_cf(progress_every=0)
    for x, y in zip(_weights(base), _weights(dev)):
        assert torch.equal(x, y)
    for a, b in zip(logs_base, logs_dev):
        for key in ("bits", "joules", "losses", "served", "h_inter", "h_intra",
                    "updates", "replay_size", "epsilon", "eta"):
            assert a[key] == b[key], key


# ---------------------------------------------------------------- replay
def test_replay_sampling_matches_the_pilot_buffer_and_labels_follow_rows():
    """Same indices, same arrays, same generator state; labels ride their rows.

    Red under: replay_labels_misaligned.
    """
    plain, labeled = ReplayBuffer(500), cfd.TeacherReplayBuffer(500)
    rng = np.random.default_rng(0)
    for i in range(200):
        state = np.full(113, float(i), dtype=np.float32)
        mask = np.zeros(28, dtype=bool)
        mask[[i % 28, (i + 3) % 28]] = True
        scores = np.arange(28, dtype=np.float64) + i
        plain.push(state, 1, np.array([1.0, 2.0, 0.0]), state.copy(), mask,
                   mask.copy(), False)
        labeled.push_labeled(state, 1, np.array([1.0, 2.0, 0.0]), state.copy(), mask,
                             mask.copy(), False, t0_action=int(i % 28),
                             teacher_action=int(i % 28), teacher_scores=scores)
    r1, r2 = np.random.default_rng(5), np.random.default_rng(5)
    a = plain.sample(16, r1)
    b = labeled.sample(16, r2)
    for x, y in zip(a, b):
        np.testing.assert_array_equal(x, y)
    assert r1.bit_generator.state == r2.bit_generator.state
    lab = labeled.last_teacher()
    idx = b[0][:, 0].astype(int)                     # the state carries its own index
    np.testing.assert_array_equal(lab["t0_action"], idx % 28)
    np.testing.assert_array_equal(lab["teacher_scores"][:, 0], idx.astype(np.float64))
    np.testing.assert_array_equal(lab["masks"], b[4])
    with pytest.raises(MCRLContractError):
        labeled.push(np.zeros(113, np.float32), 1, np.zeros(3), np.zeros(113, np.float32),
                     np.ones(28, bool), np.ones(28, bool), False)
    with pytest.raises(MCRLContractError):
        m = np.zeros(28, dtype=bool)
        m[0] = True
        labeled.push_labeled(np.zeros(113, np.float32), 1, np.zeros(3),
                             np.zeros(113, np.float32), m, m.copy(), False,
                             t0_action=1, teacher_action=1,
                             teacher_scores=np.zeros(28))


def test_stored_labels_are_the_collection_time_labels_of_their_own_state():
    """Every stored transition carries the labels computed at its own step."""
    tr = _trainer("D2-T0", users=6, cfg_kw={"episodes": 1})
    seen = []
    real = tr.teacher_labels_ext

    def record(states, masks):
        out = real(states, masks)
        seen.append((np.array(out[0]), np.array(out[2]), np.array(out[3])))
        return out

    tr.teacher_labels_ext = record
    tr.train_cf(progress_every=0)
    labels = list(tr.replay._labels)
    assert labels, "no transition was stored"
    flat = []
    for t0_acts, used_scores, legal in seen:
        for u in range(len(t0_acts)):
            flat.append((int(t0_acts[u]), used_scores[u], legal[u]))
    # every stored label must appear among the step labels, in order
    j = 0
    for a0, a1, scores, member in labels:
        assert member is None, "a single-teacher arm stored an A_CF"
        while j < len(flat) and not (flat[j][0] == a0
                                     and np.array_equal(flat[j][1], scores)):
            j += 1
        assert j < len(flat), "a stored label was never produced at collection time"
        assert a0 == a1                      # D2-T0: teacher action IS T0's action


def test_resume_keeps_the_labels_and_is_bit_identical():
    """Stop at episode 1, resume, land bit-identically on the uninterrupted run.

    Red under: resume_drops_teacher_labels.
    """
    full = _trainer("D2-T0", users=6, cfg_kw={"episodes": 3})
    logs_full = full.train_cf(progress_every=0)
    part = _trainer("D2-T0", users=6, cfg_kw={"episodes": 3})
    part.config = dataclasses.replace(part.config, episodes=1)
    logs_a = part.train_cf(progress_every=0)
    state = copy.deepcopy(part.training_state_dict())
    fresh = _trainer("D2-T0", users=6, cfg_kw={"episodes": 3})
    fresh.config = dataclasses.replace(fresh.config, episodes=1)
    fresh.load_training_state_dict(state)
    fresh.config = dataclasses.replace(fresh.config, episodes=3)
    logs = fresh.train_cf(start_episode=1, initial_logs=logs_a, progress_every=0)
    assert [r["episode"] for r in logs] == [0, 1, 2]
    for x, y in zip(_weights(full), _weights(fresh)):
        assert torch.equal(x, y)
    assert [r["losses"] for r in logs] == [r["losses"] for r in logs_full]
    assert [r["teacher_loss"] for r in logs] == [r["teacher_loss"] for r in logs_full]


# ---------------------------------------------------------------- DEVVAL
def test_devval_does_not_consume_training_rng_and_is_deterministic():
    """Reading DEVVAL between episodes changes no training state.

    Red under: devval_consumes_train_rng.
    """
    quiet = _trainer("D2-T0", users=6, cfg_kw={"episodes": 2})
    logs_quiet = quiet.train_cf(progress_every=0)
    noisy = _trainer("D2-T0", users=6, cfg_kw={"episodes": 2})
    reads = []
    logs_noisy = noisy.train_cf(progress_every=0,
                                episode_callback=lambda log: reads.append(noisy.devval()))
    assert len(reads) == 2
    for x, y in zip(_weights(quiet), _weights(noisy)):
        assert torch.equal(x, y)
    assert [r["losses"] for r in logs_quiet] == [r["losses"] for r in logs_noisy]
    again = noisy.devval()
    assert again["episodes"] == reads[-1]["episodes"]
    assert set(again) >= {"ee", "bits", "joules", "served", "beams", "h_inter",
                          "h_intra", "per_served_user_rate_mean_bps",
                          "per_served_user_rate_p10_bps", "per_served_user_rate_min_bps",
                          "t0_agreement"}


# ---------------------------------------------------------------- seeds
def test_dev_namespaces_are_disjoint_from_every_formal_set():
    """Amendment 6 section 3 ranges, checked as ranges and at the guard."""
    import dev_e0_common as D
    dev = {s for k in range(10) for s in D.dev_triple(k)}
    devval = {s for pair in D.devval_seeds(24) for s in pair}
    rnd = {D.DEVVAL_RANDOM_BASE + i for i in range(24)}
    formal = ({9_111_000 + i for i in range(24)} | {9_112_000 + i for i in range(24)}
              | {9_121_000 + i for i in range(24)} | {9_122_000 + i for i in range(24)}
              | {9_311_000 + i for i in range(24)} | {9_312_000 + i for i in range(24)}
              | {9_301_000 + k for k in range(10)} | {9_302_000 + k for k in range(10)}
              | {9_303_000 + k for k in range(10)})
    assert not (dev | devval | rnd) & formal
    for seed in (9_111_000, 9_112_003, 9_121_000, 9_122_023, 9_311_000, 9_312_005,
                 9_301_000, 9_302_001, 9_303_009):
        with pytest.raises(MCRLContractError):
            cfd.assert_dev_seed(seed, "test")
    for seed in (42, 1337, 7, 9_131_000, 9_141_000):
        with pytest.raises(MCRLContractError):
            cfd.assert_dev_seed(seed, "test")          # outside every DEV namespace
    for seed in (9_201_000, 9_202_009, 9_211_023, 9_221_000, 9_231_000):
        assert cfd.assert_dev_seed(seed, "test") == seed


def test_composite_dev_null_keys_are_validated_as_base_plus_index():
    """``(9_231_000, k)`` is ONE declared generator identity (base + seed index),
    and no formal namespace may appear in it -- base or index."""
    assert cfd.assert_dev_null_key((9_231_000, 0), "test") == (9_231_000, 0)
    assert cfd.assert_dev_null_key((9_241_000, 9), "test") == (9_241_000, 9)
    assert cfd.assert_dev_seed((9_231_000, 0), "test") == -1        # delegates
    for bad in ((9_111_000, 0), (9_112_000, 1), (9_121_000, 3), (9_122_000, 2),
                (9_301_000, 0), (9_311_000, 0), (9_312_000, 0)):
        with pytest.raises(MCRLContractError):
            cfd.assert_dev_null_key(bad, "test")
        with pytest.raises(MCRLContractError):
            cfd.assert_dev_seed(bad, "test")
    for bad in ((9_231_000, 9_111_000), (9_231_000, 9_121_000),
                (9_241_000, 9_311_000)):
        with pytest.raises(MCRLContractError):
            cfd.assert_dev_null_key(bad, "test")                    # formal index
    for bad in ((9_201_000, 0), (42, 0), (9_231_000, 10), (9_231_000, -1),
                (9_231_000,), (9_231_000, 0, 0), 9_231_000, ((9_231_000, 0), 0)):
        with pytest.raises(MCRLContractError):
            cfd.assert_dev_null_key(bad, "test")
    with pytest.raises(MCRLContractError):
        cfd.DevSettings(mechanism="D2-null", teacher="T0", null_key=(9_111_000, 0))
    assert cfd.DevSettings(mechanism="D2-null", teacher="T0",
                           null_key=(9_231_000, 0)).null_key == (9_231_000, 0)


def test_no_development_path_produces_a_formal_seed(monkeypatch):
    """Record every generator a real development run builds.

    Red under: devval_uses_formal_evaluation_seeds.
    """
    import dev_e0_common as D
    seen: list[int] = []
    keys: list[tuple] = []
    real = np.random.default_rng

    def recorder(seed=None, *a, **kw):
        # a tuple / list seed is ONE composite generator identity (base, k), not
        # two seeds: it is recorded and checked as such.
        if isinstance(seed, (tuple, list)):
            keys.append(tuple(int(x) for x in seed))
        elif isinstance(seed, (int, np.integer)):
            seen.append(int(seed))
        return real(seed, *a, **kw)

    monkeypatch.setattr(np.random, "default_rng", recorder)
    tr = _trainer("D2-null", users=6, cfg_kw={"episodes": 1})
    tr.train_cf(progress_every=0, episode_callback=lambda log: tr.devval())
    factory = _real_env_factory(6)
    cfd.dev_rollout(D.random_reference_factory(), env_factory=factory,
                    encode=tr.encode_at, seeds=D.devval_seeds(1))
    assert seen, "the recorder saw no generator at all"
    forbidden = [s for s in seen
                 for lo, hi, _n in cfd.FORBIDDEN_SEED_RANGES if lo <= s <= hi]
    assert not forbidden, f"formal seeds constructed: {sorted(set(forbidden))}"
    outside = [s for s in seen
               if not any(lo <= s <= hi for lo, hi, _n in cfd.ALLOWED_SEED_RANGES)]
    assert not outside, f"seeds outside every DEV namespace: {sorted(set(outside))}"
    assert {9_201_000, 9_202_000, 9_203_000, 9_211_000, 9_212_000} <= set(seen)
    # every composite generator identity is a declared DEV-NULL key
    assert keys, "the D2-null run built no composite key"
    for key in keys:
        assert cfd.assert_dev_null_key(key, "recorded") == key
    assert (9_231_000, 0) in keys


def test_formal_sets_are_refused_by_the_development_trainer():
    """Calibration reading and the eta quarter are hard errors here.

    Red under: dev_trainer_reads_calibration.
    """
    tr = _trainer("D0", users=6)
    with pytest.raises(MCRLContractError):
        tr.measure_on_calibration()
    with pytest.raises(MCRLContractError):
        tr.quarter_update(100)


# ---------------------------------------------------------------- manifest
def test_config_hash_is_deterministic_and_covers_the_whole_configuration():
    """One hash per arm over seeds, config, CF settings and development settings.

    Red under: manifest_ignores_dev_settings.
    """
    import dev_e0_common as D
    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    kw = dict(episodes=300, devval_episodes=24, calibration_sha256="deadbeef")
    base = D.config_hash(D.arm_config_payload(record, CALIB, 2, 0, **kw))
    assert base == D.config_hash(D.arm_config_payload(record, CALIB, 2, 0, **kw))
    assert base != D.config_hash(D.arm_config_payload(record, CALIB, 3, 0, **kw))
    assert base != D.config_hash(D.arm_config_payload(record, CALIB, 2, 1, **kw))
    assert base != D.config_hash(
        D.arm_config_payload(record, CALIB, 2, 0, **dict(kw, episodes=301))
    )
    tau_payload = D.arm_config_payload(record, CALIB, 2, 0, **kw)
    monkey = dataclasses.replace(D.e0_dev_settings("D2-T0", 0), tau=1.0)
    tau_payload["dev_settings"] = dataclasses.asdict(monkey)
    assert base != D.config_hash(tau_payload), "tau is not in the configuration hash"
    payload = D.arm_config_payload(record, CALIB, 2, 0, **kw)
    assert payload["dev_settings"]["tau"] == 3.0
    assert payload["dev_settings"]["alpha"] == 1.0
    assert payload["trainer_config"]["episodes"] == 300
    assert payload["trainer_config"]["epsilon_decay_episodes"] == 67
    assert payload["cf_settings"]["lambda0"] == 0.0
    assert payload["cf_settings"]["eta0"] == CALIB["eta0_bit_per_J"]
    assert payload["seeds"] == {"train": 9_201_000, "env": 9_202_000,
                                "mobility": 9_203_000}


def test_launcher_dry_run_plans_without_starting_anything(tmp_path):
    """The real launcher, --dry-run: a manifest, a plan, no process."""
    calib = tmp_path / "calibration.json"
    calib.write_text(json.dumps(CALIB))
    root = tmp_path / "root"
    r = subprocess.run(
        [sys.executable, "scripts/dev_e0_launch.py", "--root", str(root),
         "--calibration", str(calib), "--init-manifest", "--dry-run",
         "1:0", "2:0", "3:0", "4:0"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count(": fresh") == 4
    manifest = json.loads((root / "RUN-MANIFEST.json").read_text())
    assert set(manifest["arm_configs"]) == {"1:0", "2:0", "3:0", "4:0"}
    assert manifest["episodes"] == 300
    assert len(set(manifest["arm_configs"].values())) == 4
    assert not list(root.glob("*.pid"))
    bad = subprocess.run(
        [sys.executable, "scripts/dev_e0_launch.py", "--root", str(root),
         "--calibration", str(calib), "--dry-run", "--episodes", "301", "1:0"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert bad.returncode != 0 and "RUN-MANIFEST" in (bad.stdout + bad.stderr)


# ---------------------------------------------------------------- D3-null
def test_d3_null_target_is_legal_independent_of_t0_and_seeded():
    """The D3 matched null: a seeded uniform LEGAL action, no T0 quantity anywhere.

    Red under: d3null_target_is_t0_action, d3null_target_may_be_illegal,
    d3null_uses_train_rng, d3null_scores_carry_t0.
    """
    tr = _trainer("D3-null", users=6)
    factory = _real_env_factory(6)
    env = factory()
    states, masks, _ = env.reset(np.random.default_rng(9_202_000),
                                 np.random.default_rng(9_203_000))
    before_train = copy.deepcopy(tr._train_rng.bit_generator.state)
    before_env = copy.deepcopy(tr._env_rng.bit_generator.state)
    agree = total = 0
    draws = []
    for _t in range(6):
        t0_acts, used_acts, used_scores, legal, raw = tr.teacher_labels(states, masks)
        for u in range(len(t0_acts)):
            if not bool(legal[u].any()):
                continue
            total += 1
            assert legal[u][used_acts[u]], "the null target is illegal in its state"
            agree += int(used_acts[u] == t0_acts[u])
        assert np.all(used_scores == 0.0), "the null carries a T0 quantity"
        draws.append(np.array(used_acts))
        res = env.step(t0_acts, np.random.default_rng(9_202_000))
        states, masks = res.user_states, res.action_masks
    assert tr._train_rng.bit_generator.state == before_train
    assert tr._env_rng.bit_generator.state == before_env
    chance = 1.0 / 26.0
    assert agree / total < 0.25, f"the null agrees with T0 at {agree / total}"

    # legality is a property of the draw, checked where it can be seen: 200 rows
    # with only 3 legal actions of 28 (an unmasked draw could not stay legal)
    tight = np.zeros((200, 28), dtype=bool)
    rng_t = np.random.default_rng((9_241_000, 0))
    for u in range(200):
        tight[u, [u % 28, (u + 5) % 28, (u + 11) % 28]] = True
    tight_acts = cft.random_legal_actions(tight, rng_t)
    assert all(bool(tight[u, tight_acts[u]]) for u in range(200)), "an illegal null draw"
    hits = np.bincount([int(a_) for a_ in tight_acts], minlength=28).sum()
    assert hits == 200

    # the same declared key reproduces the draws; a different index does not
    same = cft.random_legal_actions(legal, np.random.default_rng((9_241_000, 0)))
    same2 = cft.random_legal_actions(legal, np.random.default_rng((9_241_000, 0)))
    other = cft.random_legal_actions(legal, np.random.default_rng((9_241_000, 1)))
    np.testing.assert_array_equal(same, same2)
    assert not np.array_equal(same, other)

    # the draw cannot depend on T0's scores: rerun the first step with the teacher's
    # scores multiplied, from the same generator state
    fresh_a = _trainer("D3-null", users=6)
    fresh_b = _trainer("D3-null", users=6)
    env2 = factory()
    s2, m2, _ = env2.reset(np.random.default_rng(9_202_000), np.random.default_rng(9_203_000))
    a1 = fresh_a.teacher_labels(s2, m2)[1]
    real_scores = cft.t0_scores
    try:
        cft.t0_scores = lambda states, masks, c=cft.T0_C: (
            (lambda s, a, m: (s * -7.0, a, m))(*real_scores(states, masks, c))
        )
        a2 = fresh_b.teacher_labels(s2, m2)[1]
    finally:
        cft.t0_scores = real_scores
    np.testing.assert_array_equal(a1, a2)


def test_d3_null_version_hash_covers_the_null_identity():
    """The DEV-NULL key is part of the configuration hash.

    Red under: d3null_key_dropped_from_hash, manifest_ignores_dev_settings.
    """
    import dev_e0_common as D
    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    kw = dict(episodes=300, devval_episodes=24, calibration_sha256="deadbeef")
    p0 = D.arm_config_payload(record, CALIB, 7, 0, **kw)
    p1 = D.arm_config_payload(record, CALIB, 7, 1, **kw)
    assert p0["dev_settings"]["mechanism"] == "D3-null"
    assert p0["dev_settings"]["teacher"] == "random"
    assert tuple(p0["dev_settings"]["null_key"]) == (9_241_000, 0)
    assert tuple(p1["dev_settings"]["null_key"]) == (9_241_000, 1)
    assert D.config_hash(p0) != D.config_hash(p1)
    assert D.config_hash(p0) != D.config_hash(
        D.arm_config_payload(record, CALIB, 4, 0, **kw)          # D3-T0, same seed
    )
    with pytest.raises(MCRLContractError):
        cfd.DevSettings(mechanism="D3-null", teacher="random", null_key=(9_231_000, 0))
    with pytest.raises(MCRLContractError):
        cfd.DevSettings(mechanism="D3-null", teacher="T0", null_key=(9_241_000, 0))
    with pytest.raises(MCRLContractError):
        cfd.DevSettings(mechanism="D3-null", teacher="random", null_key=None)
