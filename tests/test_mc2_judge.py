"""MC2 preflight: the training-only judge, ``MC2-JGO-v1``, ``MC2-ARB-v2`` and the
shared B-only cell.

Governing: ``.scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md``
(r1 / r2) section 5 (the ten minimum new tests) and section 6 (the cells).
**Development lane; nothing here launches a learner arm.**  The tiny runs use the
DEV k = 0 triple and 6 users only; no formal, calibration, CONFIRM or S1 seed is
constructed, and the MC2 selection / confirmation / fallback indices (k >= 10) are
only ever used as identity arithmetic.

Mutants (``MC2_MUTANT=<name> pytest tests/test_mc2_judge.py``), applied with
``monkeypatch`` -- no source file is edited -- and each must turn the suite red:

* ``gate_ge``            -- the gate admits ties (``>=`` instead of ``>``);
* ``judge_advances_rng`` -- the judge advances the environment generator;
* ``b_no_abstain_final`` -- B proposes at the final step (its T0 fallback leaks);
* ``null_reads_tnext``   -- the B-null's proposal is read from T_NEXT;
* ``margin_refilled``    -- target-less rows are given weight 1 (dose refilled);
* ``arb_ties_to_a``      -- v2's tie order prefers A over ``x_u``.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

from mcrl.algorithms import cf_credit as cc
from mcrl.algorithms import cf_dev as cfd
from mcrl.algorithms import cf_judge as cfj
from mcrl.algorithms import cf_multi_sources as cfmulti
from mcrl.algorithms import cf_ratio as cfr
from mcrl.algorithms import cf_teacher as cft
from mcrl.errors import MCRLContractError
from mcrl.runtime.trainer_config_validation import TD_BOOTSTRAP_SHARED
from mcrl.runtime.trainer_spec import TrainerConfig

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
PINNED_LOCAL = Path("/home/u24/mcrl-runtime/tle-pinned-427e6a91")
MUTANT = os.environ.get("MC2_MUTANT", "")
BASE_COMMIT = "6136c5149c49875b985955456cce468702821018"
CALIB = {"eta0_bit_per_J": 110_507_234.83444457,
         "bits_scale": 13_329_082_278.45065,
         "joules_scale": 120.61728174105066}
CALIB_SHA = "59952214a68469d9eccef292fa0eadf41e897ff74abd4b6cbff0635ee1a4562d"
K8_LAUNCHED = {
    # /home/sat/mcrl-v025-cf2s-multi-ws/runs-k8/RUN-MANIFEST.json, commit f129e340
    (1, 8, ()): "ed4e507eb5b0f22ae7dc65257986050c791e1646e35cb1a232d13bffc0a4a6de",
    (4, 8, ()): "0cf6f6a11cecdc29a8b4b4d30c661c73ddb8b3248fcf637b750f40f4f011c056",
    (8, 8, (("teachers", ("T0", "T_NEXT")),)):
        "c46546611d2586b44bfd2427ebb493c1eea7043bfe87b296e04929bc65d9cdfb",
    (8, 8, (("teachers", ("T_NEXT",)),)):
        "1737d12354275d9903200fb01ed5572b561f621d97a51075ec350dfeccc9f2f8",
    (9, 8, (("n_proposals", 2), ("bernoulli", True))):
        "17b048b2b8ff791e96e448035b053307716de77962e39b1a1925dfbef2be0b25",
}
TNEXT_SHA = "86f0d6eef483612e28b27ddb5a472c6368563fc41c46feff177367e77df91e1f"
CELLS = ("v1-A+B", "v1-A+R", "v2-A", "v2-A+B", "v2-A+R", "B")
NA = 28


# ---------------------------------------------------------------- sources
@pytest.fixture(autouse=True, scope="module")
def _tnext_registered():
    cfmulti.register_candidate_sources(replace=True)
    yield
    cft.unregister_teacher_source(cfmulti.T_NEXT_ID)


# ---------------------------------------------------------------- mutants
@pytest.fixture(autouse=True)
def mutant(monkeypatch):
    if MUTANT == "gate_ge":
        monkeypatch.setattr(
            cfj, "strictly_better",
            lambda a, b: (a.served, a.surrogate) >= (b.served, b.surrogate),
        )
    elif MUTANT == "judge_advances_rng":
        real = cfj.StepJudge._evaluate

        def bad(self, vec):
            ev = real(self, vec)
            self._rng.random()
            return ev

        monkeypatch.setattr(cfj.StepJudge, "_evaluate", bad)
    elif MUTANT == "b_no_abstain_final":
        real = cfd.CFDevTrainer._challenger_actions

        def bad(self, states, masks, legal, is_final):
            return real(self, states, masks, legal, False)

        monkeypatch.setattr(cfd.CFDevTrainer, "_challenger_actions", bad)
    elif MUTANT == "null_reads_tnext":
        real = cfd.CFDevTrainer._challenger_actions

        def bad(self, states, masks, legal, is_final):
            if self.judge.uses_r and not is_final:
                slots = cft.teacher_action_slots(
                    (cfmulti.T_NEXT_ID,), states, masks, context=self._teacher_context)
                return np.asarray(slots[:, 0], dtype=np.int64)
            return real(self, states, masks, legal, is_final)

        monkeypatch.setattr(cfd.CFDevTrainer, "_challenger_actions", bad)
    elif MUTANT == "margin_refilled":
        real = cfj.weighted_margin_loss
        monkeypatch.setattr(
            cfj, "weighted_margin_loss",
            lambda s, m, a, w, margin: real(s, m, a, torch.ones_like(w), margin),
        )
    elif MUTANT == "arb_ties_to_a":
        def bad(a, b):
            return (a.served, a.surrogate) >= (b.served, b.surrogate)

        real_arb = cfj.arb_labels

        def arb(**kw):
            saved = cfj.strictly_better
            cfj.strictly_better = bad          # ties now go to the later candidate
            try:
                return real_arb(**kw)
            finally:
                cfj.strictly_better = saved

        monkeypatch.setattr(cfj, "arb_labels", arb)
        monkeypatch.setattr(cfj, "labeller_for",
                            lambda mid: (arb if mid == cfj.ARB_MECHANISM_ID
                                         else cfj.jgo_labels))
    elif MUTANT:
        raise AssertionError(f"unknown mutant {MUTANT}")
    yield


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
    base = dict(mechanism=mechanism,
                teacher=cfd.EXPECTED_TEACHER.get(mechanism, "T0"),
                null_key=(None if cfd.NULL_BASE_FOR.get(mechanism) is None
                          else (cfd.NULL_BASE_FOR[mechanism], 0)),
                devval_episodes=1)
    base.update(kw)
    return cfd.DevSettings(**base)


def _jspec(cell: str, k: int = 0) -> cfd.JudgeSpec:
    import dev_e0_common as D
    return D.judge_spec(10, cell, k)


def _real_env_factory(users):
    if not PINNED_LOCAL.is_dir():
        pytest.skip("pinned local TLE archive not present")
    os.environ["MCRL_TLE_ROOT"] = str(PINNED_LOCAL)
    from mcrl.runtime.training_pipeline import make_training_environment
    return lambda: make_training_environment(users=users)


def _trainer(mechanism="D0", *, judge=None, users=6, cfg_kw=None, dev_kw=None):
    factory = _real_env_factory(users)
    return cfd.CFDevTrainer(
        factory(), _config(**(cfg_kw or {})), _settings(),
        _dev(mechanism, **(dev_kw or {})), judge=judge, env_factory=factory,
        train_seed=9_201_000, env_seed=9_202_000, mobility_seed=9_203_000,
    )


def _judge(cell: str, **kw):
    return _trainer(cfj.MECHANISM_NAME, judge=_jspec(cell), **kw)


def _weights(tr):
    return [p.detach().clone() for net in tr.q_nets for p in net.parameters()]


def _weights_sha(tr) -> str:
    h = hashlib.sha256()
    for p in _weights(tr):
        h.update(p.numpy().tobytes())
    return h.hexdigest()


def _payload(arm, k, **kw):
    import dev_e0_common as D
    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    return D.arm_config_payload(record, CALIB, arm, k, episodes=300, devval_episodes=24,
                                calibration_sha256=CALIB_SHA, **kw)


def _env_fingerprint(env) -> str:
    """Everything the judge is forbidden to move (driver, users, ledgers, segments)."""
    se = cc.step_env(env)
    driver = se.driver
    h = hashlib.sha256()
    h.update(str(getattr(driver, "_step_index", None)).encode())
    h.update(str(getattr(driver, "_start_utc", None)).encode())
    h.update(np.ascontiguousarray(driver.user_ecef_km()).tobytes())
    pos = driver.satellite_ecef_at(0)
    for norad in sorted(pos):
        h.update(str(norad).encode())
        h.update(np.ascontiguousarray(pos[norad]).tobytes())
    h.update(str(se._step_index).encode())
    h.update(repr(se._segments).encode())
    h.update(repr(se._previous_association).encode())
    h.update(repr([getattr(x, "__dict__", None) or repr(x) for x in se._ledgers]).encode())
    h.update(np.ascontiguousarray(se._previous_link_power_w).tobytes())
    assert "satellite_ecef_at" not in vars(driver), "the frozen positions leaked"
    assert "_warm_start_gain" not in vars(se), "the frozen warm-start gain leaked"
    return h.hexdigest()


def _score_batch(n, seed):
    rng = np.random.default_rng(seed)
    scores = torch.tensor(rng.normal(size=(n, NA)), dtype=torch.float32)
    mask = torch.zeros(n, NA, dtype=torch.bool)
    a_t = torch.zeros(n, dtype=torch.long)
    for u in range(n):
        k = int(rng.integers(1, NA + 1))
        idx = rng.choice(NA, size=k, replace=False)
        mask[u, idx] = True
        a_t[u] = int(rng.choice(idx))
    return scores, mask, a_t


def K(served, surrogate):
    return cfj.Kappa(served, surrogate, 0.0, 0.0)


def _rows_equal(a, b) -> bool:
    """Replay label rows, with NaN (an uncompared row's judge lead) equal to NaN."""
    if len(a) != len(b):
        return False
    for ra, rb in zip(a, b):
        for xa, xb in zip(ra, rb):
            if isinstance(xa, float) and isinstance(xb, float):
                if not (xa == xb or (np.isnan(xa) and np.isnan(xb))):
                    return False
            elif xa != xb:
                return False
    return True


# ================================================================ 1
def test_01_arms_1_to_9_config_hashes_are_unchanged():
    """(1) Arms 1-9 hash exactly as the base commit's harness hashes them, and the
    five k = 8 cells hash to what was actually launched on sat (f129e340)."""
    import dev_e0_common as D
    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    kw = dict(episodes=300, devval_episodes=24, calibration_sha256=CALIB_SHA)
    old_src = subprocess.run(
        ["git", "show", f"{BASE_COMMIT}:scripts/dev_e0_common.py"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout
    ns: dict = {"__name__": "dev_e0_common_base", "__file__": str(REPO / "scripts/x.py")}
    exec(compile(old_src, "<base dev_e0_common>", "exec"), ns)   # noqa: S102
    cases = [(arm, k, {}) for arm in range(1, 8) for k in (0, 1, 8, 10, 11)]
    cases += [(8, 8, {"teachers": ("T0", "T_NEXT")}), (8, 8, {"teachers": ("T_NEXT",)}),
              (8, 1, {"teachers": ("T0",)}), (9, 8, {"n_proposals": 2, "bernoulli": True}),
              (9, 8, {"n_proposals": 2})]
    for arm, k, extra in cases:
        payload = D.arm_config_payload(record, CALIB, arm, k, **kw, **extra)
        new = D.config_hash(payload)
        old = ns["config_hash"](ns["arm_config_payload"](record, CALIB, arm, k, **kw, **extra))
        assert new == old, f"MC2 changed arm {arm} k{k} {extra}"
        assert "judge_spec" not in payload and "judge_rule_definition" not in payload
    for (arm, k, extra), want in K8_LAUNCHED.items():
        got = D.config_hash(D.arm_config_payload(record, CALIB, arm, k, **kw, **dict(extra)))
        assert got == want, f"launched k8 cell {arm} {extra} no longer hashes the same"


# ================================================================ 2
def test_02_v1_full_with_the_gate_forced_shut_is_d3_t0(monkeypatch):
    """(2) FULL-v1 with the gate forced shut IS the frozen D3-T0, parameter sha256
    for sha256, on the real environment: the judge (and T_NEXT) ran every step and
    moved nothing -- not the environment, not env_rng, not the driver, not the
    trainer's generators, not the loss."""
    frozen = _trainer("D3-T0")
    logs_f = frozen.train_cf(progress_every=0)
    calls = {"n": 0}

    def shut(a, b):
        calls["n"] += 1
        return False

    monkeypatch.setattr(cfj, "strictly_better", shut)
    full = _judge("v1-A+B")
    logs_j = full.train_cf(progress_every=0)
    assert calls["n"] > 0
    assert sum(r["judge_compared"] for r in logs_j) > 0
    assert sum(r["judge_evaluations"] for r in logs_j) > 0
    assert sum(r["judge_overrides"] for r in logs_j) == 0
    sha_f, sha_j = _weights_sha(frozen), _weights_sha(full)
    for x, y in zip(_weights(frozen), _weights(full)):
        assert torch.equal(x, y), "the judge path moved the learner"
    assert sha_f == sha_j
    print(f"\n[MC2-2] D3-T0 parameter sha256           = {sha_f}"
          f"\n[MC2-2] v1 FULL gate-shut parameter sha256 = {sha_j}")
    shared = (set(logs_f[0]) & set(logs_j[0])) - {"mechanism", "teacher"}
    assert {"losses", "teacher_loss", "bits", "joules", "served", "updates"} <= shared
    for a, b in zip(logs_f, logs_j):
        for key in sorted(shared):
            assert a[key] == b[key], key
    for r in logs_j:
        assert r["judge_margin_dose"] == 1.0
        assert r["judge_sampled_rows_by_tag"]["none"] == 0


def test_02b_v2_full_with_the_gate_forced_shut_is_d0(monkeypatch):
    """(2, v2) With the gate shut v2 keeps x_u everywhere, so no row carries a margin
    and the arm IS D0 bit for bit -- the same side-effect-freeness receipt for the
    arbitration path."""
    d0 = _trainer("D0")
    logs0 = d0.train_cf(progress_every=0)
    monkeypatch.setattr(cfj, "strictly_better", lambda a, b: False)
    v2 = _judge("v2-A+B")
    logs2 = v2.train_cf(progress_every=0)
    for x, y in zip(_weights(d0), _weights(v2)):
        assert torch.equal(x, y), "v2 at zero dose moved the learner"
    assert _weights_sha(d0) == _weights_sha(v2)
    for a, b in zip(logs0, logs2):
        assert a["bits"] == b["bits"] and a["losses"] == b["losses"]
        assert a["updates"] == b["updates"]
    for r in logs2:
        assert r["teacher_loss"] == 0.0
        assert r["judge_compared"] > 0
        assert r["judge_overrides"] == 0
        assert r["judge_margin_dose"] in (0.0, None)
        assert r["judge_tag_counts"]["none"] == r["decision_rows_all_t"]


# ================================================================ 3
def test_03_the_base_evaluation_is_the_committed_step():
    """(3) The judge's base evaluation of x equals the committed step's bits, joules
    and served flags EXACTLY; the reused kappa(x_u) equals a fresh evaluation of the
    same vector; a counterfactual under the frozen positions equals the plain
    evaluator; and no generator or environment state moves."""
    factory = _real_env_factory(8)
    env = factory()
    se = cc.step_env(env)
    env_rng = np.random.default_rng(9_202_000)
    mob_rng = np.random.default_rng(9_203_000)
    states, masks, _obs = env.reset(env_rng, mob_rng)
    pick = np.random.default_rng(9_201_000)
    checked_alt = 0
    for _t in range(4):
        legal = np.array([m.mask for m in masks], dtype=bool)
        x = np.full(len(masks), -1, dtype=np.int64)
        for u in range(len(masks)):
            ok = np.flatnonzero(legal[u])
            if ok.size:
                x[u] = int(pick.choice(ok))
        before = (copy.deepcopy(env_rng.bit_generator.state),
                  copy.deepcopy(mob_rng.bit_generator.state), _env_fingerprint(env))
        with cfj.StepJudge(env, x, env_rng) as judge:
            base = judge.base()
            fresh = se.evaluate_actions(x, env_rng)
            assert cfj.kappa_of(fresh, cfj.ETA0_JUDGE) == base
            for u in range(len(masks)):
                if x[u] >= 0:
                    assert judge.kappa(u, int(x[u])) is base      # exact reuse
            alt = None
            for u in range(len(masks)):
                ok = [a for a in np.flatnonzero(legal[u]).tolist() if a != int(x[u])]
                if ok:
                    alt = (u, ok[0])
                    break
            k_alt = judge.kappa(*alt) if alt else None
            n_eval = judge.evaluations
        assert n_eval == (2 if alt else 1)
        if alt:
            vec = x.copy()
            vec[alt[0]] = alt[1]
            plain = cfj.kappa_of(se.evaluate_actions(vec, env_rng), cfj.ETA0_JUDGE)
            assert plain == k_alt, "the frozen-position evaluation is not the plain one"
            checked_alt += 1
        after = (env_rng.bit_generator.state, mob_rng.bit_generator.state,
                 _env_fingerprint(env))
        assert after[0] == before[0], "the judge advanced env_rng"
        assert after[1] == before[1], "the judge advanced the mobility generator"
        assert after[2] == before[2], "the judge moved the environment / driver"
        res = env.step(x, env_rng)
        out = env.last_outcome
        bits, joules = cc.evaluation_bits_joules(out)
        assert (bits, joules) == (base.bits, base.joules)
        assert int(np.count_nonzero(out.resolution.served)) == base.served
        judge.assert_committed_parity(out)
        states, masks = res.user_states, res.action_masks
    assert checked_alt >= 3


# ================================================================ 4
def test_04_v1_gate_semantics_are_strict_lexicographic_and_b_abstains():
    """(4) Strict lexicographic (served first), ties -> incumbent, no call when
    c == incumbent, B abstains at T-1 -- as a table, and in a real B-only run."""
    assert cfj.strictly_better(K(3, 1.0), K(2, 99.0))
    assert not cfj.strictly_better(K(2, 99.0), K(3, 1.0))
    assert not cfj.strictly_better(K(3, 1.0), K(3, 1.0)), "a tie must go to the incumbent"
    assert cfj.strictly_better(K(3, 1.0 + 1e-6), K(3, 1.0))

    legal = np.zeros((6, NA), dtype=bool)
    legal[:5, :4] = True                                   # user 5: no legal action
    x = np.array([0, 1, 2, 3, 0, -1])
    a_a = np.array([0, 0, 1, 1, 2, -1])
    c = np.array([0, 2, 3, 2, 3, -1])
    table = {
        (1, 2): K(5, 0.0), (1, 0): K(5, -1.0),      # c wins on the surrogate
        (2, 3): K(5, 2.0), (2, 1): K(5, 2.0),       # exact tie -> incumbent
        (3, 2): K(4, 100.0), (3, 1): K(5, 0.0),     # c sheds a user -> loses
        (4, 3): K(6, -50.0), (4, 2): K(5, 0.0),     # c wins on the served count
    }
    calls: list[tuple[int, int]] = []

    def kappa(u, a):
        calls.append((int(u), int(a)))
        return table[(int(u), int(a))]

    lab = cfj.jgo_labels(use_a=True, challenger_tag=cfj.TAG_B, legal=legal, x=x,
                         a_a=a_a, challenger=c, kappa=kappa)
    assert lab.target.tolist() == [0, 2, 1, 1, 3, cfj.NO_TARGET]
    assert lab.tag.tolist() == [cfj.TAG_A, cfj.TAG_B, cfj.TAG_A, cfj.TAG_A, cfj.TAG_B,
                                cfj.TAG_NONE]
    assert lab.override.tolist() == [False, True, False, False, True, False]
    assert lab.compared.tolist() == [False, True, True, True, True, False]
    assert (lab.lead_served[4], lab.lead_served[3]) == (1, -1)
    assert sorted(set(calls)) == sorted(table), "the judge is asked about {c, inc} only"
    assert not any(u == 0 for u, _a in calls), "no call when c == incumbent"

    # B-only (the shared cell): the incumbent is x_u and a row the challenger does
    # not win has NO target.
    table_b = {(1, 2): K(5, 0.0), (1, 1): K(5, 0.0),        # tie -> none
               (2, 3): K(5, 1.0), (2, 2): K(5, 0.0),        # override
               (3, 2): K(5, 0.0), (3, 3): K(5, 3.0),        # loses -> none
               (4, 3): K(5, 0.0), (4, 0): K(5, 0.0)}
    calls.clear()
    lab_b = cfj.jgo_labels(use_a=False, challenger_tag=cfj.TAG_B, legal=legal, x=x,
                           a_a=a_a, challenger=c,
                           kappa=lambda u, a: (calls.append((u, a)), table_b[(u, a)])[1])
    assert lab_b.target.tolist() == [cfj.NO_TARGET, cfj.NO_TARGET, 3, cfj.NO_TARGET,
                                     cfj.NO_TARGET, cfj.NO_TARGET]
    assert lab_b.tag.tolist() == [0, 0, cfj.TAG_B, 0, 0, 0]
    assert not any(u == 0 for u, _a in calls)                # c == x_0: no call

    # the final step: the challenger abstains -> no judge call at all under v1
    calls.clear()
    fin = cfj.jgo_labels(use_a=True, challenger_tag=cfj.TAG_B, legal=legal, x=x, a_a=a_a,
                         challenger=None, kappa=lambda u, a: calls.append((u, a)))
    assert calls == [] and fin.target.tolist()[:5] == a_a.tolist()[:5]
    assert not fin.override.any()

    # ... and in a real B-only run: T_NEXT is never asked at T-1, and nothing is
    # compared or overridden there.
    seen_final: list[bool] = []

    def spy(states, masks, *, context):
        seen_final.append(bool(context.is_final_step))
        return cfmulti._tnext_source(states, masks, context=context)

    cft.register_teacher_source(cfmulti.T_NEXT_ID, spy, replace=True, needs_context=True)
    try:
        tr = _judge("B")
        logs = tr.train_cf(progress_every=0)
    finally:
        cfmulti.register_candidate_sources(replace=True)
    assert seen_final and not any(seen_final), "T_NEXT was asked at the final step"
    for r in logs:
        assert r["judge_compared_per_step"][-1] == 0
        assert r["judge_overrides_per_step"][-1] == 0
        assert r["judge_abstained_final_rows"] == r["judge_rows_per_step"][-1] > 0
        assert r["decision_rows_all_t"] == sum(r["judge_rows_per_step"])
    assert sum(r["judge_compared"] for r in logs) > 0


def test_04b_v2_arbitration_order_is_x_then_a_then_b():
    """(4, v2) The winner is max kappa with ties to x_u, then A, then the challenger;
    a margin exists only when the winner is not x_u; ``a^A == a^B`` is an A win."""
    legal = np.zeros((6, NA), dtype=bool)
    legal[:5, :4] = True
    x = np.array([0, 1, 2, 3, 0, -1])
    a_a = np.array([0, 0, 1, 1, 2, -1])
    c = np.array([0, 2, 3, 2, 2, -1])
    table = {
        (1, 1): K(5, 0.0), (1, 0): K(5, 1.0), (1, 2): K(5, 1.0),   # A wins, B ties A
        (2, 2): K(5, 0.0), (2, 1): K(5, 0.5), (2, 3): K(5, 2.0),   # B wins
        (3, 3): K(5, 5.0), (3, 1): K(5, 1.0), (3, 2): K(4, 100.0),  # x_u keeps it
        (4, 0): K(5, 0.0), (4, 2): K(5, 3.0),                       # a^A == a^B -> A
    }
    calls: list[tuple[int, int]] = []

    def kappa(u, a):
        calls.append((int(u), int(a)))
        return table[(int(u), int(a))]

    lab = cfj.arb_labels(use_a=True, challenger_tag=cfj.TAG_B, legal=legal, x=x, a_a=a_a,
                         challenger=c, kappa=kappa)
    assert lab.target.tolist() == [cfj.NO_TARGET, 0, 3, cfj.NO_TARGET, 2, cfj.NO_TARGET]
    assert lab.tag.tolist() == [cfj.TAG_NONE, cfj.TAG_A, cfj.TAG_B, cfj.TAG_NONE,
                                cfj.TAG_A, cfj.TAG_NONE]
    assert lab.override.tolist() == [False, True, True, False, True, False]
    assert lab.compared.tolist() == [False, True, True, True, True, False]
    assert not any(u == 0 for u, _a in calls), "x_u == a^A == a^B: no call at all"
    assert sorted(set(calls)) == sorted(table)
    assert lab.lead_surrogate[1] == pytest.approx(1.0)
    assert lab.lead_surrogate[3] == pytest.approx(-4.0)    # best compared vs x_u
    assert lab.lead_served[3] == 0

    # B absent at T-1: only A competes with x_u there
    calls.clear()
    fin = cfj.arb_labels(use_a=True, challenger_tag=cfj.TAG_B, legal=legal, x=x, a_a=a_a,
                         challenger=None, kappa=kappa)
    assert fin.tag.tolist() == [cfj.TAG_NONE, cfj.TAG_A, cfj.TAG_A, cfj.TAG_NONE,
                                cfj.TAG_A, cfj.TAG_NONE]
    for u in range(5):
        if int(c[u]) not in (int(x[u]), int(a_a[u])):
            assert (u, int(c[u])) not in calls, "the challenger was asked at T-1"

    # A-only-v2: candidates {x_u, a^A} -- a judge-gated T0, not D3-T0
    a_only = cfj.arb_labels(use_a=True, challenger_tag=cfj.TAG_NONE, legal=legal, x=x,
                            a_a=a_a, challenger=None, kappa=kappa)
    assert a_only.target.tolist() == [cfj.NO_TARGET, 0, 1, cfj.NO_TARGET, 2,
                                      cfj.NO_TARGET]

    # and in a real v2 run the anchor is still compared at the final step
    v2 = _judge("v2-A+B")
    logs = v2.train_cf(progress_every=0)
    for r in logs:
        assert r["judge_compared_per_step"][-1] > 0
        assert r["judge_tag_per_step"]["B"][-1] == 0, "B won at T-1"
        assert (r["judge_tag_counts"]["none"] + r["judge_tag_counts"]["A"]
                + r["judge_tag_counts"]["B"]) == r["decision_rows_all_t"]
        assert r["judge_challenger_wins"] == r["judge_challenger_wins_c_ne_a"]
        assert r["judge_margin_dose"] is None or 0.0 <= r["judge_margin_dose"] <= 1.0
        # the override leads are split by tag: under v2 an A win and a B win are
        # different quantities and must not be pooled
        by_tag = r["judge_override_rows_by_tag"]
        assert sum(by_tag.values()) == r["judge_overrides"]
        assert by_tag["A"] == r["judge_tag_counts"]["A"]
        assert by_tag["B"] == r["judge_challenger_wins"]
        assert sum(r["judge_served_decisive_overrides_by_tag"].values()) == \
            r["judge_served_decisive_overrides"]
        for tag in ("A", "B"):
            if by_tag[tag]:
                assert r["judge_override_lead_surrogate_mean_by_tag"][tag] is not None
                assert r["judge_override_lead_surrogate_mean_by_tag"][tag] > 0.0 or \
                    r["judge_override_lead_served_mean_by_tag"][tag] > 0.0


def test_04c_the_shared_b_only_cell_is_rule_independent():
    """r1 section 3 / lane B: on ``{B}`` the v1 and the v2 code paths produce identical
    labels AND identical parameters (sha256) after a few episodes."""
    legal = np.zeros((4, NA), dtype=bool)
    legal[:, :4] = True
    x = np.array([0, 1, 2, 3])
    a_a = np.array([3, 3, 3, 3])
    c = np.array([0, 2, 3, 1])
    table = {(1, 1): K(5, 0.0), (1, 2): K(5, 1.0),      # B wins
             (2, 2): K(5, 1.0), (2, 3): K(5, 1.0),      # tie -> x_u
             (3, 3): K(5, 1.0), (3, 1): K(6, -9.0)}     # B wins on served
    kap = lambda u, a: table[(int(u), int(a))]          # noqa: E731
    v1 = cfj.jgo_labels(use_a=False, challenger_tag=cfj.TAG_B, legal=legal, x=x,
                        a_a=a_a, challenger=c, kappa=kap)
    v2 = cfj.arb_labels(use_a=False, challenger_tag=cfj.TAG_B, legal=legal, x=x,
                        a_a=a_a, challenger=c, kappa=kap)
    for field in ("decision", "challenger", "target", "tag", "override", "compared",
                  "lead_served"):
        np.testing.assert_array_equal(getattr(v1, field), getattr(v2, field), field)
    np.testing.assert_allclose(v1.lead_surrogate, v2.lead_surrogate, equal_nan=True)

    import dev_e0_common as D
    spec = _jspec("B")
    assert spec.mechanism_id == cfj.BONLY_MECHANISM_ID
    assert "v1" not in spec.label() and "v2" not in spec.label()
    payload = json.dumps(_payload(10, 10, cell="B"))
    assert "JGO" not in payload and "ARB" not in payload
    assert D.config_hash(_payload(10, 10, cell="v1-B")) == \
        D.config_hash(_payload(10, 10, cell="B"))
    assert D.config_hash(_payload(10, 10, cell="v2-B")) == \
        D.config_hash(_payload(10, 10, cell="B"))

    shas = {}
    rows = {}
    for rule, fn in (("v1", cfj.jgo_labels), ("v2", cfj.arb_labels)):
        saved = cfj.labeller_for
        cfj.labeller_for = lambda _mid, _fn=fn: _fn
        try:
            tr = _judge("B", cfg_kw={"episodes": 3})
            tr.train_cf(progress_every=0)
        finally:
            cfj.labeller_for = saved
        shas[rule] = _weights_sha(tr)
        rows[rule] = tr.replay.label_rows()
    assert _rows_equal(rows["v1"], rows["v2"])
    assert shas["v1"] == shas["v2"], "the shared B-only cell is not rule-independent"
    print(f"\n[MC2-4c] shared B-only parameter sha256 (v1 path = v2 path) = {shas['v1']}")


# ================================================================ 5
@pytest.mark.parametrize("cell", ["v1-A+R", "v2-A+R"])
def test_05_the_b_null_reads_no_tnext_and_draws_once_per_legal_row(cell, monkeypatch):
    """(5) The B-null reads no T_NEXT, draws exactly one uniform legal action per
    user with a legal action at t < T-1 and nothing at T-1, and only from its own
    fresh stream at the declared key (9_243_000, k)."""
    def forbidden(states, masks, **kw):
        raise AssertionError("the B-null asked T_NEXT for an action")

    keys: list[tuple] = []
    real_rng = np.random.default_rng

    def recorder(seed=None, *a, **kw):
        if isinstance(seed, (tuple, list)):
            keys.append(tuple(int(v) for v in seed))
        return real_rng(seed, *a, **kw)

    draws: list[tuple[np.ndarray, np.ndarray, object]] = []
    real_draw = cft.random_legal_actions

    def spy(mask, rng):
        out = real_draw(mask, rng)
        draws.append((np.array(mask, dtype=bool, copy=True), out.copy(), rng))
        return out

    monkeypatch.setattr(np.random, "default_rng", recorder)
    monkeypatch.setattr(cft, "random_legal_actions", spy)
    cft.register_teacher_source(cfmulti.T_NEXT_ID, forbidden, replace=True,
                                needs_context=False)
    try:
        tr = _trainer(cfj.MECHANISM_NAME, judge=_jspec(cell, k=3),
                      cfg_kw={"episodes": 2})
        assert tr._needs_teacher_context is False
        logs = tr.train_cf(progress_every=0)
    finally:
        cfmulti.register_candidate_sources(replace=True)
    assert keys == [(9_243_000, 3)], f"composite generators built: {keys}"
    steps = tr.env.config.steps_per_episode
    assert len(draws) == 2 * (steps - 1), "one draw call per step at t < T-1, none at T-1"
    assert all(rng is tr._judge_null_rng for _m, _o, rng in draws)
    fresh = real_rng((9_243_000, 3))
    for mask, out, _rng in draws:
        np.testing.assert_array_equal(real_draw(mask, fresh), out)
        for u in range(mask.shape[0]):
            if mask[u].any():
                assert bool(mask[u, out[u]])
    assert fresh.bit_generator.state == tr._judge_null_rng.bit_generator.state, \
        "the null stream was consumed by something other than one draw per legal row"
    for r in logs:
        assert r["judge_challenger_rows"] == sum(r["judge_rows_per_step"][:-1])
        assert r["judge_abstained_final_rows"] == r["judge_rows_per_step"][-1]
        assert r["judge_tag_counts"]["B"] == 0
    assert all(row[3] in (cfj.TAG_NONE, cfj.TAG_A, cfj.TAG_R)
               for row in tr.replay.label_rows())


# ================================================================ 6
def test_06_mc2_seed_indices_are_inside_dev_and_disjoint_from_everything_else():
    """(6) Every derived seed of k = 10..17 is in a declared DEV range and disjoint
    from P0, the T0-XEP reference, formal, calibration, CONFIRM and S1."""
    import dev_e0_common as D
    p0 = {9_202_500 + i for i in range(24)} | {9_203_500 + i for i in range(24)}
    xep = {9_241_500, 9_241_501}
    closed = [(9_111_000, 9_112_999, "formal"), (9_121_000, 9_122_999, "calibration"),
              (9_301_000, 9_303_999, "CONFIRM train"), (9_311_000, 9_312_999, "CONFIRM eval"),
              (9_251_000, 9_253_999, "S1-TRAIN"), (9_261_000, 9_261_999, "S1-NULL")]
    seen: dict[int, str] = {}
    for k in range(10, 18):
        train, env, mob = D.dev_triple(k)
        # the streams an E0 / MC2 run actually constructs, and the declared but
        # UNUSED NULL-source offsets (source_kind is "none" in every E0 arm and
        # CFDevTrainer refuses source pools outright, so no run builds them; their
        # +80_000+j ladders overlap between adjacent k upstream, which is why only
        # the constructed streams are checked for collisions)
        built = {"train": train, "env": env, "mobility": mob,
                 "catfish(+70_001)": train + cfr.CATFISH_SAMPLING_RNG_OFFSET,
                 "penalty(+90_211)": train + 90_211}
        unused = {f"null-source(+80_000+{j})": train + cfr.NULL_RNG_OFFSET + j
                  for j in range(3)}
        for role, s in {**built, **unused}.items():
            assert cfd.assert_dev_seed(s, role) == s
            assert s not in p0 and s not in xep, (k, role, s)
            for lo, hi, name in closed:
                assert not lo <= s <= hi, (k, role, s, name)
        for role, s in built.items():
            assert s not in seen, f"{role} k{k} = {s} collides with {seen.get(s)}"
            seen[s] = f"{role} k{k}"
        for base in (9_231_000, 9_241_000, 9_243_000):
            assert cfd.assert_dev_null_key((base, k), "mc2") == (base, k)
    assert cfd.assert_dev_null_key((9_243_000, 19), "mc2") == (9_243_000, 19)
    for bad in ((9_243_000, 20), (9_261_000, 10), (9_251_000, 10), (9_243_000, 9_111_000)):
        with pytest.raises(MCRLContractError):
            cfd.assert_dev_null_key(bad, "mc2")
    for s in (9_251_000, 9_252_010, 9_253_017, 9_261_000, 9_261_017):
        with pytest.raises(MCRLContractError, match="S1"):
            cfd.assert_dev_seed(s, "mc2")
    assert 9_243_000 not in p0 | xep
    assert D.MAX_SEED_INDEX == cfd.MAX_DEV_SEED_INDEX == 19
    assert D.RESERVED_SEED_INDICES == (9,)
    # no MC2 arm can build a NULL-source stream at all
    assert D.e0_cf_settings(CALIB, "equal_share").source_kind == "none"
    assert _judge("v2-A").sources == []
    p = _payload(10, 11, cell="v1-A+R")
    assert p["seeds"] == {"train": 9_201_011, "env": 9_202_011, "mobility": 9_203_011}
    assert tuple(p["judge_spec"]["null_key"]) == (9_243_000, 11)


# ================================================================ 7
def test_07_config_hash_carries_rule_sources_judge_and_null_identity():
    """(7) rule id, source set, judge id + eta0, null id + key are all hashed; the six
    declared cells are six identities; the undeclared ones are refused."""
    import dev_e0_common as D
    full = _payload(10, 10, cell="v1-A+B")
    js = full["judge_spec"]
    assert js["mechanism_id"] == cfj.JGO_MECHANISM_ID
    assert tuple(js["sources"]) == ("A", "B")
    assert (js["source_a"], js["source_b"]) == ("T0", "T_NEXT")
    assert js["judge_id"] == cfj.JUDGE_ID and js["judge_definition"] == cfj.JUDGE_DEFINITION
    assert js["judge_eta0"] == 110_507_234.83444457
    assert js["null_id"] is None and js["null_key"] is None
    assert full["judge_rule_definition"] == cfj.RULE_DEFINITIONS[cfj.JGO_MECHANISM_ID]
    assert full["judge_source_identities"]["B"]["cf_tnext_sha256"] == TNEXT_SHA
    assert full["judge_source_identities"]["B"]["source_version"] == \
        "assoc-persistence-lookahead-v1"
    assert full["dev_settings"]["mechanism"] == cfj.MECHANISM_NAME == "MC2"
    assert full["dev_settings"]["teacher"] == "judge"
    assert (full["dev_settings"]["margin"], full["dev_settings"]["lambda_e"]) == (0.15, 1.0)
    assert full["dev_settings"]["null_key"] is None
    assert full["trainer_config"]["epsilon_decay_episodes"] == 67
    assert full["arm_name"] == "E0-10-MC2-v1-A+B-equal_share"
    null = _payload(10, 10, cell="v2-A+R")
    assert null["judge_spec"]["mechanism_id"] == cfj.ARB_MECHANISM_ID
    assert null["judge_spec"]["null_id"] == cfj.NULL_ID
    assert tuple(null["judge_spec"]["null_key"]) == (9_243_000, 10)
    assert "B" not in null["judge_source_identities"]
    assert null["judge_source_identities"]["R"]["null_key"] == [9_243_000, 10]

    h = D.config_hash
    hashes = {c: h(_payload(10, 10, cell=c)) for c in CELLS}
    assert len(set(hashes.values())) == 6, "two declared cells share a configuration hash"
    assert h(_payload(10, 10, cell="v1-B+A")) == hashes["v1-A+B"]          # canonical
    assert h(_payload(10, 11, cell="v1-A+B")) != hashes["v1-A+B"]
    assert h(_payload(10, 11, cell="v1-A+R")) != hashes["v1-A+R"]          # null key
    assert hashes["v1-A+B"] != h(_payload(4, 10))
    assert hashes["v2-A"] != h(_payload(4, 10))
    for field, value in (("mechanism_id", cfj.JGO_MECHANISM_ID), ("sources", ("A",)),
                         ("judge_id", "other"), ("judge_eta0", 1.0e8),
                         ("null_id", "other"), ("null_key", (9_243_000, 12))):
        p = copy.deepcopy(null)
        p["judge_spec"][field] = value
        assert h(p) != hashes["v2-A+R"], f"{field} is not in the configuration hash"
    p = copy.deepcopy(full)
    p.pop("judge_spec")
    assert h(p) != hashes["v1-A+B"]
    p = copy.deepcopy(full)
    p["judge_rule_definition"] = "something else"
    assert h(p) != hashes["v1-A+B"]
    for c in CELLS:
        assert D.spec_key(10, 10, cell=c) == f"10:10:{c}"

    refuse = [
        dict(sources=("A",), source_a="T0"),                              # A-only-v1
        dict(sources=("R",), null_id=cfj.NULL_ID, null_key=(9_243_000, 0)),
        dict(sources=("B",), source_b="T_NEXT"),                          # must be shared
        dict(sources=("B", "A"), source_a="T0", source_b="T_NEXT"),        # not canonical
        dict(sources=("A", "B"), source_a="T0", source_b="T_NEXT",
             mechanism_id="MC2-JGO-v3"),
        dict(sources=("A", "B"), source_a="T0", source_b="T_NEXT", judge_eta0=1.0e8),
        dict(sources=("A", "B"), source_a="T0", source_b="T_NEXT", judge_id="x"),
        dict(sources=("A", "R"), source_a="T0", null_id=cfj.NULL_ID,
             null_key=(9_241_000, 0)),
        dict(sources=("A", "R"), source_a="T0"),                           # no key
        dict(sources=("A", "B"), source_a="T0", source_b="T_NEXT",
             null_id=cfj.NULL_ID, null_key=(9_243_000, 0)),                # key w/o R
        dict(sources=("B",), source_b="T_TAIL", mechanism_id=cfj.BONLY_MECHANISM_ID),
        dict(sources=("A",), source_a="T0", mechanism_id=cfj.BONLY_MECHANISM_ID),
    ]
    for kw in refuse:
        with pytest.raises(MCRLContractError):
            cfd.JudgeSpec(**kw)
    assert cfd.JudgeSpec(mechanism_id=cfj.ARB_MECHANISM_ID, sources=("A",),
                         source_a="T0").label() == "v2-A"
    for bad in ("A", "R", "v1-A", "v1-B+R", "v2-A+B+R", "v1-A+A", "v3-A+B", "A+B"):
        with pytest.raises(SystemExit):
            D.judge_cell(bad)
    with pytest.raises(SystemExit):
        D.spec_key(10, 10)
    with pytest.raises(SystemExit):
        D.spec_key(4, 10, cell="v1-A+B")
    with pytest.raises(MCRLContractError):
        cfd.DevSettings(mechanism=cfj.MECHANISM_NAME, teacher="T0")
    with pytest.raises(MCRLContractError):
        _trainer(cfj.MECHANISM_NAME, judge=None)
    with pytest.raises(MCRLContractError):
        _trainer("D3-T0", judge=_jspec("v1-A+B"))


# ================================================================ 8
def test_08_a_full_checkpoint_runs_with_no_source_and_no_judge(tmp_path, monkeypatch):
    """(8) A checkpoint of a FULL arm acts with every source unregistered, T0 made
    to raise and the judge made to raise; the frozen files are untouched."""
    for f in ("src/mcrl/algorithms/cf_ratio.py", "src/mcrl/algorithms/modqn.py",
              "src/mcrl/algorithms/cf_credit.py", "src/mcrl/algorithms/cf_tnext.py",
              "src/mcrl/algorithms/cf_teacher.py", "src/mcrl/algorithms/cf_multi_sources.py",
              "src/mcrl/runtime/trainer_env.py", "src/mcrl/env/step.py"):
        base = subprocess.run(["git", "show", f"{BASE_COMMIT}:{f}"], cwd=REPO,
                              capture_output=True, check=True).stdout
        assert hashlib.sha256(base).digest() == hashlib.sha256(
            (REPO / f).read_bytes()).digest(), f
    assert hashlib.sha256(
        (REPO / "src/mcrl/algorithms/cf_tnext.py").read_bytes()).hexdigest() == TNEXT_SHA
    for name in ("greedy_actions", "select_actions", "encode_at", "save_policy"):
        assert getattr(cfd.CFDevTrainer, name) is getattr(cfr.CFRatioTrainer, name)

    full = _judge("v1-A+B")
    full.train_cf(progress_every=0)
    path = tmp_path / "policy.pt"
    full.save_policy(path, 1)
    payload = torch.load(path, map_location="cpu", weights_only=False)
    assert tuple(payload["judge_spec"]["sources"]) == ("A", "B")
    assert set(payload) >= {"q_networks", "target_networks", "eta"}

    factory = _real_env_factory(6)
    deployed = cfd.CFDevTrainer(factory(), _config(), _settings(), _dev("D0"),
                                env_factory=factory, train_seed=9_201_000,
                                env_seed=9_202_000, mobility_seed=9_203_000)
    saved = dict(cft._TEACHER_SOURCES)
    real_t0 = cft.t0_scores

    def no_teacher(*args, **kwargs):
        raise AssertionError("the deployment path asked a Catfish for an action")

    def no_judge(*args, **kwargs):
        raise AssertionError("the deployment path asked the judge")

    try:
        cft._TEACHER_SOURCES.clear()
        cft.t0_scores = no_teacher
        cft.t0_actions = no_teacher
        monkeypatch.setattr(cfj.StepJudge, "__init__", no_judge)
        monkeypatch.setattr(cfj, "kappa_of", no_judge)
        from mcrl.env.step import StepEnvironment
        monkeypatch.setattr(StepEnvironment, "evaluate_actions", no_judge)
        deployed.load_policy(path)
        env = factory()
        states, masks, _ = env.reset(np.random.default_rng(9_211_000),
                                     np.random.default_rng(9_212_000))
        enc = deployed.encode_at(states, 0)
        np.testing.assert_array_equal(deployed.greedy_actions(enc, masks),
                                      full.greedy_actions(enc, masks))
        out = cfd.dev_rollout(
            lambda i: (lambda e, m, s: deployed.greedy_actions(e, m)),
            env_factory=factory, encode=deployed.encode_at,
            seeds=[(9_211_000, 9_212_000), (9_211_001, 9_212_001)],
            t0_agreement=False,
        )
        assert out["n_episodes"] == 2 and np.isfinite(out["ee"])
    finally:
        cft.t0_scores = real_t0
        cft.t0_actions = lambda states, masks: real_t0(states, masks)[1]
        cft._TEACHER_SOURCES.clear()
        cft._TEACHER_SOURCES.update(saved)


# ================================================================ 9
JUDGE_LOG_KEYS = ("judge_overrides", "judge_compared", "judge_evaluations",
                  "judge_margin_loss_by_tag", "judge_sampled_rows_by_tag",
                  "judge_pushed_by_tag", "judge_tag_per_step",
                  "judge_challenger_wins", "judge_a_vs_x_pairs", "judge_a_above_x")


@pytest.mark.parametrize("cell", CELLS)
def test_09_stop_and_resume_are_deterministic(cell):
    """(9) Stop at an episode boundary, resume, land bit-identically -- weights, losses,
    judge labels, the B-null's own stream -- and a different cell is refused."""
    full = _judge(cell, cfg_kw={"episodes": 2})
    logs_full = full.train_cf(progress_every=0)
    part = _judge(cell, cfg_kw={"episodes": 2})
    part.config = dataclasses.replace(part.config, episodes=1)
    logs_a = part.train_cf(progress_every=0)
    state = copy.deepcopy(part.training_state_dict())
    fresh = _judge(cell, cfg_kw={"episodes": 2})
    fresh.config = dataclasses.replace(fresh.config, episodes=1)
    fresh.load_training_state_dict(state)
    fresh.config = dataclasses.replace(fresh.config, episodes=2)
    logs = fresh.train_cf(start_episode=1, initial_logs=logs_a, progress_every=0)
    assert [r["episode"] for r in logs] == [0, 1]
    for x, y in zip(_weights(full), _weights(fresh)):
        assert torch.equal(x, y), f"{cell} resume is not bit-identical"
    assert [r["losses"] for r in logs] == [r["losses"] for r in logs_full]
    assert [r["teacher_loss"] for r in logs] == [r["teacher_loss"] for r in logs_full]
    for key in JUDGE_LOG_KEYS:
        assert [r[key] for r in logs] == [r[key] for r in logs_full], key
    assert _rows_equal(full.replay.label_rows(), fresh.replay.label_rows())
    if "R" in cell:
        assert (full._judge_null_rng.bit_generator.state
                == fresh._judge_null_rng.bit_generator.state)
    other = _judge({"v1-A+B": "v2-A+B", "v1-A+R": "v2-A+R", "v2-A": "v1-A+B",
                    "v2-A+B": "v1-A+B", "v2-A+R": "v1-A+R", "B": "v2-A"}[cell],
                   cfg_kw={"episodes": 2})
    with pytest.raises(MCRLContractError):
        other.load_training_state_dict(state)
    d3 = _trainer("D3-T0", cfg_kw={"episodes": 2})
    with pytest.raises(MCRLContractError):
        d3.load_training_state_dict(state)


# ================================================================ 10
def test_10_rows_without_a_target_carry_zero_margin():
    """(10) The single-target weighted margin: w = 0 rows contribute exactly 0 (loss
    and gradient), the dose is NOT refilled, w = 1 is bit-identical to D3; and in a
    real B-only run the target-less rows carry zero margin."""
    scores, mask, a_t = _score_batch(128, 7)
    s0 = scores.clone().requires_grad_(True)
    loss0, _rows = cfj.weighted_margin_loss(s0, mask, a_t, torch.zeros(128), 0.15)
    loss0.backward()
    assert float(loss0) == 0.0 and float(s0.grad.abs().max()) == 0.0

    s1 = scores.clone().requires_grad_(True)
    s_ref = scores.clone().requires_grad_(True)
    loss1, _rows = cfj.weighted_margin_loss(s1, mask, a_t, torch.ones(128), 0.15)
    ref = cft.d3_margin_loss(s_ref, mask, a_t, 0.15)
    assert torch.equal(loss1, ref), "w = 1 is not the frozen D3 loss bit for bit"
    loss1.backward()
    ref.backward()
    assert torch.equal(s1.grad, s_ref.grad)

    w = torch.tensor([1.0 if i % 3 == 0 else 0.0 for i in range(128)])
    lm, _rows = cfj.weighted_margin_loss(scores.clone(), mask, a_t, w, 0.15)
    keep = w.bool()
    refilled = float(cft.d3_margin_loss(scores[keep], mask[keep], a_t[keep], 0.15))
    assert float(lm) == pytest.approx(refilled * int(keep.sum()) / 128.0, rel=1e-5)
    assert float(lm) < refilled, "the vacated dose was refilled"

    tr = _judge("B", cfg_kw={"episodes": 2})
    logs = tr.train_cf(progress_every=0)
    rows_ = tr.replay.label_rows()
    none_rows = [r for r in rows_ if r[3] == cfj.TAG_NONE]
    b_rows = [r for r in rows_ if r[3] == cfj.TAG_B]
    assert none_rows and b_rows
    assert all(r[2] == cfj.NO_TARGET and not r[4] for r in none_rows)
    assert all(r[2] == r[1] and r[4] for r in b_rows)
    assert not any(r[3] == cfj.TAG_A for r in rows_)
    for r in logs:
        assert r["judge_margin_loss_by_tag"]["none"] == 0.0
        assert r["judge_margin_loss_by_tag"]["A"] == 0.0
        assert r["judge_sampled_rows_by_tag"]["A"] == 0
        if r["judge_updates"]:
            assert r["judge_margin_dose"] < 1.0
            assert sum(r["judge_margin_loss_by_tag"].values()) == pytest.approx(
                r["teacher_loss"] * r["updates"], rel=1e-6, abs=1e-12)


# ================================================================ launcher
def test_launcher_fills_one_manifest_in_waves_and_caps_live_workers(tmp_path):
    """The 16-spec ep-100 root can be filled in waves without changing its manifest;
    k = 9 and k = 20 are refused; the live-worker cap refuses."""
    calib = tmp_path / "calibration.json"
    calib.write_text(json.dumps(CALIB))
    root = tmp_path / "runs-ep100"
    specs = [f"10:{k}:{c}" for k in (10, 11) for c in CELLS]
    specs += [f"{arm}:{k}" for k in (10, 11) for arm in (1, 4)]
    assert len(specs) == 16
    base = [sys.executable, "scripts/dev_e0_launch.py", "--root", str(root),
            "--calibration", str(calib), "--episodes", "300", "--stop-after", "100",
            "--worker-cwd-prefix", str(tmp_path / "no-workers-here")]
    r = subprocess.run(base + ["--init-manifest", "--dry-run", "--launch-limit", "8",
                               "--max-processes", "8", *specs],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("-> launch") == 8 and r.stdout.count("-> deferred") == 8
    manifest = json.loads((root / "RUN-MANIFEST.json").read_text())
    assert len(manifest["arm_configs"]) == 16
    assert len(set(manifest["arm_configs"].values())) == 16
    assert manifest["episodes"] == 300
    assert manifest["dev_seed_namespaces"]["DEV_NULL_MC2"] == 9_243_000
    assert not list(root.glob("*.pid"))
    again = subprocess.run(base + ["--dry-run", "--launch-limit", "8",
                                   "--max-processes", "8", *reversed(specs)],
                           cwd=REPO, capture_output=True, text=True)
    assert again.returncode == 0, again.stdout + again.stderr
    for bad in (["10:9:v1-A+B"], ["1:20"], ["10:10:v1-A"], ["10:10"], ["4:10:v1-A+B"],
                ["10:10:v3-A+B"]):
        b = subprocess.run(base + ["--dry-run", *bad], cwd=REPO, capture_output=True,
                           text=True)
        assert b.returncode != 0, bad
    cap = subprocess.run(base + ["--dry-run", "--launch-limit", "8", "--max-processes", "8",
                                 "--max-live-workers", "7", *specs],
                         cwd=REPO, capture_output=True, text=True)
    assert cap.returncode != 0 and "max-live-workers" in (cap.stdout + cap.stderr)
