"""S1 preflight: ``T0-XEP`` (Amendment 12) and the frozen S1 harness (Amendment 13).

Every test here was first run against a NAMED MUTANT of the implementation and seen to
FAIL (``S1_MUTANT=<name> .venv/bin/pytest tests/test_s1_harness.py -k ...``), then
against the real code and seen to PASS.  Mutants are applied by the autouse ``mutant``
fixture with ``monkeypatch``; no source file is edited.  The red/green log is in
``.scratch/dev-training/S1-PREFLIGHT-2026-09-12.md``.

**These tests never touch a formal evaluation, calibration or CONFIRM episode.**  The
S1 lane is exercised by construction and by its guards, never by rolling one.  The
launcher's "complete matrix or nothing" rule is tested as a pure function so that a
mutant which removes it cannot start a formal run from inside the test suite.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
import types
from pathlib import Path

import numpy as np
import pytest

from mcrl.algorithms import cf_dev as cfd
from mcrl.algorithms import cf_teacher as cft
from mcrl.algorithms import cf_xep as cfx
from mcrl.env.step_types import ActionMask
from mcrl.errors import MCRLContractError

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
PINNED_LOCAL = Path("/home/u24/mcrl-runtime/tle-pinned-427e6a91")
MUTANT = os.environ.get("S1_MUTANT", "")
CALIB = {"eta0_bit_per_J": 110_507_234.83444457,
         "bits_scale": 13_329_082_278.45065,
         "joules_scale": 120.61728174105066}
SEALED_XEP_SHA256 = "9bb0c01efdd403fb0e765bd133d718f7b07273a188c9f173b39fbb112ae1900c"


# ---------------------------------------------------------------- fixtures
def _reference_payload(*, users: int, steps: int, seed: int,
                       env_seed: int = 9_241_500, mobility_seed: int = 9_241_501,
                       policy: str = "T0") -> dict:
    rng = np.random.default_rng(seed)
    block = np.zeros((steps, users, 2, 28), dtype=np.float64)
    block[:, :, 0, :] = rng.gamma(2.0, 3.0, size=(steps, users, 28))
    block[:, :, 1, :] = (rng.random((steps, users, 28)) < 0.4) * rng.integers(
        1, 5, size=(steps, users, 28))
    payload = {"schema": cfx.SCHEMA, "policy": policy,
               "env_seed": int(env_seed), "mobility_seed": int(mobility_seed)}
    payload.update(cfx.encode_block(block))
    return payload


def _write_reference(tmp_path: Path, name="ref.json", **kw):
    payload = _reference_payload(**kw)
    path = tmp_path / name
    digest = cfx.write_reference(path, payload)
    return path, cfx.load_reference(path, digest)


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


def _real_env_factory(users):
    if not PINNED_LOCAL.is_dir():
        pytest.skip("pinned local TLE archive not present")
    os.environ["MCRL_TLE_ROOT"] = str(PINNED_LOCAL)
    from mcrl.runtime.training_pipeline import make_training_environment
    return lambda: make_training_environment(users=users)


def _config(**kw):
    from mcrl.runtime.trainer_config_validation import TD_BOOTSTRAP_SHARED
    from mcrl.runtime.trainer_spec import TrainerConfig
    base = dict(learning_rate=0.001, episodes=2, epsilon_decay_episodes=2,
                td_bootstrap_mode=TD_BOOTSTRAP_SHARED, batch_size=18,
                replay_capacity=5000, target_update_every_episodes=1,
                discount_factor=1.0)
    base.update(kw)
    return TrainerConfig(**base)


def _settings(**kw):
    from mcrl.algorithms.cf_ratio import CFRatioSettings
    base = dict(source_kind="none", rho=1.0 / 9.0, eta0=2.0, bits_scale=10.0,
                joules_scale=4.0, quarter_episodes=10**9,
                eta_first_update_episode=10**9, calibration_episodes=0,
                calibration_env_seed_base=0, calibration_mobility_seed_base=0)
    base.update(kw)
    return CFRatioSettings(**base)


def _xep_dev(reference, **kw):
    base = dict(mechanism="D3-XEP", teacher="T0-XEP", devval_episodes=1,
                xep_reference_sha256=reference.sha256,
                xep_reference_key=reference.key,
                xep_reference_policy=reference.policy)
    base.update(kw)
    return cfd.DevSettings(**base)


def _xep_trainer(reference, *, users=6, cfg_kw=None):
    factory = _real_env_factory(users)
    return cfd.CFDevTrainer(
        factory(), _config(**(cfg_kw or {})), _settings(), _xep_dev(reference),
        env_factory=factory, train_seed=9_201_000, env_seed=9_202_000,
        mobility_seed=9_203_000, xep_reference=reference,
    )


# ---------------------------------------------------------------- mutants
@pytest.fixture(autouse=True)
def mutant(monkeypatch, tmp_path_factory):
    T = cfd.CFDevTrainer
    if MUTANT == "xep_reference_state_not_substituted":
        real = T.teacher_labels

        def bad(self, states, masks, *, step=None):
            t0, used, sc, legal, raw = real(self, states, masks, step=step)
            if self.dev.mechanism == "D3-XEP":
                used, sc = t0, raw       # the CURRENT state's T0, not the reference's
            return t0, used, sc, legal, raw

        monkeypatch.setattr(T, "teacher_labels", bad)
    elif MUTANT == "xep_current_mask_not_applied":
        def bad(reference_states, current_mask, c=cft.T0_C):
            scores = cft.t0_score_matrix(reference_states, c)
            return scores, np.argmax(scores, axis=1).astype(np.int64)

        monkeypatch.setattr(cft, "t0_xep_labels", bad)
    elif MUTANT == "xep_reference_regenerated_per_episode":
        real = T.teacher_labels
        tmp = tmp_path_factory.mktemp("regen")
        counter = {"n": 0}

        def bad(self, states, masks, *, step=None):
            if self.dev.mechanism == "D3-XEP" and step == 0:
                counter["n"] += 1
                payload = _reference_payload(
                    users=self._xep_ref.users, steps=self._xep_ref.steps,
                    seed=1000 + counter["n"])
                path = tmp / f"regen-{counter['n']}.json"
                digest = cfx.write_reference(path, payload)
                self._xep_ref = cfx.load_reference(path, digest)
            return real(self, states, masks, step=step)

        monkeypatch.setattr(T, "teacher_labels", bad)
    elif MUTANT == "xep_agreement_against_itself":
        def bad(xep_actions, t0_actions, legal, t0_scores):
            return cfd.__dict__["_real_xep_leakage"](
                xep_actions, xep_actions, legal, t0_scores)

        monkeypatch.setitem(cfd.__dict__, "_real_xep_leakage", cfd.xep_leakage)
        monkeypatch.setattr(cfd, "xep_leakage", bad)
    elif MUTANT == "xep_reference_missing_from_config_hash":
        import dev_e0_common as D
        import s1_common as S
        for mod in (D, S):
            real = mod.arm_config_payload

            def make(real=real):
                def bad(*args, **kwargs):
                    payload = real(*args, **kwargs)
                    for key in ("xep_reference_sha256", "xep_reference_key",
                                "xep_reference_policy"):
                        payload.get("dev_settings", {}).pop(key, None)
                    return payload
                return bad

            monkeypatch.setattr(mod, "arm_config_payload", make())
    elif MUTANT == "s1_null_uses_dev_stream":
        import s1_common as S
        real = S.s1_dev_settings

        def bad(arm, k, *, eval_episodes=S.N_EVAL):
            d = real(arm, k, eval_episodes=eval_episodes)
            if d.mechanism == "D3-null":
                return dataclasses.replace(
                    d, lane=cfd.DEV_LANE, null_key=(9_241_000, int(k)),
                    devval_env_base=9_211_000, devval_mobility_base=9_212_000)
            return d

        monkeypatch.setattr(S, "s1_dev_settings", bad)
    elif MUTANT == "s1_reuses_dev_training_triple":
        import s1_common as S
        monkeypatch.setattr(S, "s1_triple",
                            lambda k: (9_201_000 + int(k), 9_202_000 + int(k),
                                       9_203_000 + int(k)))
    elif MUTANT == "s1_evaluates_on_calibration":
        import s1_common as S
        monkeypatch.setattr(S, "EVAL_ENV_BASE", 9_121_000)
        monkeypatch.setattr(S, "EVAL_MOB_BASE", 9_122_000)
        monkeypatch.setattr(cfd, "FORMAL_EVAL_ENV_BASE", 9_121_000)
        monkeypatch.setattr(cfd, "FORMAL_EVAL_MOB_BASE", 9_122_000)
    elif MUTANT == "s1_modqn_uses_shared_bootstrap":
        import cf3_common as C
        import dev_e0_common as D
        import s1_common as S

        def bad(record, arm, episodes):
            cfg = C.pilot_config(record, "A1", int(episodes))
            return dataclasses.replace(
                cfg, epsilon_decay_episodes=D.epsilon_decay_episodes(episodes))

        monkeypatch.setattr(S, "s1_config", bad)
    elif MUTANT == "s1_manifest_drops_arm_configs":
        import s1_common as S
        real = S.declared_manifest

        def bad(*args, **kwargs):
            m = real(*args, **kwargs)
            m.pop("arm_configs", None)
            m.pop("arm_payloads", None)
            return m

        monkeypatch.setattr(S, "declared_manifest", bad)
    elif MUTANT == "s1_partial_matrix_allowed":
        import s1_launch
        monkeypatch.setattr(s1_launch, "assert_complete_matrix",
                            lambda specs, **kw: None)
    elif MUTANT:
        raise AssertionError(f"unknown mutant {MUTANT}")
    yield


# ---------------------------------------------------------------- T0-XEP core
def test_t0_score_matrix_is_the_one_t0_expression():
    """``t0_scores`` and ``t0_score_matrix`` cannot drift apart.

    T0-XEP is only "T0's ordinary frozen score" if it computes it with T0's own
    arithmetic, so the two callers must share one expression exactly.
    """
    states, masks = _states(30, seed=7)
    scores, _acts, _legal = cft.t0_scores(states, masks)
    np.testing.assert_array_equal(scores, cft.t0_score_matrix(states))
    # c = 1, m = 0, unmodified: the penalty is exactly the unlit indicator
    for u, s in enumerate(states):
        gain = np.maximum(np.asarray(s.channel_quality, float), 0.0)
        load = np.asarray(s.beam_loads, float)
        np.testing.assert_allclose(
            scores[u], np.log2(1.0 + gain) - 1.0 * (load == 0.0))


def test_t0_xep_scores_the_reference_state_and_argmaxes_the_current_mask(tmp_path):
    """Amendment 12 section 2, the whole mechanism in one assertion.

    Red under: xep_reference_state_not_substituted, xep_current_mask_not_applied.
    """
    _path, ref = _write_reference(tmp_path, users=40, steps=10, seed=3)
    now_states, now_masks = _states(40, seed=11)
    t0_scores, t0_acts, legal = cft.t0_scores(now_states, now_masks)
    for step in (0, 4, 9):
        ref_states = ref.states_at(step)
        scores, acts = cft.t0_xep_labels(ref_states, legal)
        # scored on the REFERENCE state ...
        np.testing.assert_array_equal(scores, cft.t0_score_matrix(ref_states))
        assert not np.allclose(scores, t0_scores), "the reference was not substituted"
        # ... argmaxed over the LEARNER's CURRENT mask
        np.testing.assert_array_equal(acts, cft.masked_argmax_rows(scores, legal))
        for u in range(40):
            assert bool(legal[u][acts[u]]), "T0-XEP advised an illegal action"
        assert (acts != t0_acts).sum() > 0, "the null is not decorrelated at all"
    # a different reference step gives different advice: step t IS matched to step t
    a0 = cft.t0_xep_labels(ref.states_at(0), legal)[1]
    a5 = cft.t0_xep_labels(ref.states_at(5), legal)[1]
    assert not np.array_equal(a0, a5)


def test_t0_xep_fails_closed_off_the_end_and_on_a_user_count_mismatch(tmp_path):
    _path, ref = _write_reference(tmp_path, users=8, steps=10, seed=5)
    _states8, masks8 = _states(8, seed=1)
    legal8 = np.array([m.mask for m in masks8], dtype=bool)
    cft.t0_xep_labels(ref.states_at(9), legal8)
    with pytest.raises(MCRLContractError):
        ref.states_at(10)
    with pytest.raises(MCRLContractError):
        ref.states_at(-1)
    _states9, masks9 = _states(9, seed=1)
    legal9 = np.array([m.mask for m in masks9], dtype=bool)
    with pytest.raises(MCRLContractError):
        cft.t0_xep_labels(ref.states_at(0), legal9)


def test_the_reference_file_is_sealed_and_never_regenerated(tmp_path):
    """One file, one sha256, no overwrite, no silent substitution."""
    path, ref = _write_reference(tmp_path, users=4, steps=10, seed=2)
    assert ref.sha256 == cfx.file_sha256(path)
    with pytest.raises(MCRLContractError):          # never regenerated
        cfx.write_reference(path, _reference_payload(users=4, steps=10, seed=2))
    with pytest.raises(MCRLContractError):          # never a different file
        cfx.load_reference(path, "0" * 64)
    with pytest.raises(MCRLContractError):          # never an unverified file
        cfx.load_reference(path, "")
    tampered = tmp_path / "tampered.json"
    body = json.loads(path.read_text())
    body["policy"] = "RANDOM"
    tampered.write_text(cfx.serialise(body))
    assert cfx.file_sha256(tampered) != ref.sha256
    with pytest.raises(MCRLContractError):
        cfx.load_reference(tampered, ref.sha256)
    # the loaded arrays are read-only, so nothing can mutate the reference in place
    with pytest.raises(ValueError):
        ref.states_at(0)[0].channel_quality[0] = 1.0


def test_the_committed_reference_is_the_sealed_one():
    """The reference this project will actually run on: identity + sha256."""
    import dev_e0_common as D
    assert D.XEP_REFERENCE_SHA256 == SEALED_XEP_SHA256
    if not D.XEP_REFERENCE_PATH.is_file():
        pytest.skip("reference file not present in this checkout")
    ref = D.load_xep_reference()
    assert ref.sha256 == SEALED_XEP_SHA256
    assert ref.key == (9_241_500, 9_241_501)
    assert ref.policy == "T0"
    assert (ref.steps, ref.users) == (10, 100)
    for seed in ref.key:                    # DEV-NULL, never DEV / DEVVAL / formal
        assert cfd.assert_dev_seed(seed, "sealed reference") == seed
        assert any(base <= seed <= base + 999 for base in cfd.DEV_NULL_KEY_BASES)


def test_the_reference_identity_is_in_the_configuration_hash():
    """A different (or regenerated) reference is a different version.

    Red under: xep_reference_missing_from_config_hash.
    """
    import dev_e0_common as D
    import s1_common as S
    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)

    kw = dict(episodes=300, devval_episodes=24, calibration_sha256="deadbeef")
    base = D.arm_config_payload(record, CALIB, 8, 0, **kw)
    assert base["dev_settings"]["mechanism"] == "D3-XEP"
    assert base["dev_settings"]["teacher"] == "T0-XEP"
    assert base["dev_settings"]["xep_reference_sha256"] == SEALED_XEP_SHA256
    moved = D.arm_config_payload(record, CALIB, 8, 0, **kw)
    moved["dev_settings"] = dict(moved["dev_settings"],
                                 xep_reference_sha256="f" * 64)
    assert D.config_hash(base) != D.config_hash(moved), \
        "the reference sha256 is not in the configuration hash"
    repolicy = D.arm_config_payload(record, CALIB, 8, 0, **kw)
    repolicy["dev_settings"] = dict(repolicy["dev_settings"],
                                    xep_reference_policy="RANDOM")
    assert D.config_hash(base) != D.config_hash(repolicy)
    rekey = D.arm_config_payload(record, CALIB, 8, 0, **kw)
    rekey["dev_settings"] = dict(rekey["dev_settings"],
                                 xep_reference_key=[9_241_600, 9_241_601])
    assert D.config_hash(base) != D.config_hash(rekey)

    s1kw = dict(episodes=1000, eval_episodes=24, calibration_sha256="deadbeef")
    s1 = S.arm_config_payload(record, CALIB, 4, 0, **s1kw)
    assert s1["dev_settings"]["xep_reference_sha256"] == SEALED_XEP_SHA256
    s1_moved = S.arm_config_payload(record, CALIB, 4, 0, **s1kw)
    s1_moved["dev_settings"] = dict(s1_moved["dev_settings"],
                                    xep_reference_sha256="f" * 64)
    assert S.config_hash(s1) != S.config_hash(s1_moved)


def test_a_d3_xep_configuration_without_its_reference_is_refused(tmp_path):
    _path, ref = _write_reference(tmp_path, users=4, steps=10, seed=9)
    with pytest.raises(MCRLContractError):
        cfd.DevSettings(mechanism="D3-XEP", teacher="T0-XEP")
    with pytest.raises(MCRLContractError):
        cfd.DevSettings(mechanism="D3-XEP", teacher="T0")
    with pytest.raises(MCRLContractError):        # the reference must be DEV-NULL
        _xep_dev(ref, xep_reference_key=(9_111_000, 9_112_000))
    with pytest.raises(MCRLContractError):
        _xep_dev(ref, xep_reference_key=(9_201_000, 9_202_000))
    with pytest.raises(MCRLContractError):        # only D3-XEP carries one
        cfd.DevSettings(mechanism="D3-T0", teacher="T0",
                        xep_reference_sha256=ref.sha256,
                        xep_reference_key=ref.key, xep_reference_policy="T0")


# ---------------------------------------------------------------- trainer
def test_the_bound_reference_is_fixed_for_the_whole_run(tmp_path):
    """One reference, bound once, unchanged across episodes.

    Red under: xep_reference_regenerated_per_episode.
    """
    _path, ref = _write_reference(tmp_path, users=6, steps=10, seed=13)
    tr = _xep_trainer(ref, cfg_kw={"episodes": 2})
    before = np.array(ref._data, copy=True)
    logs = tr.train_cf(progress_every=0)
    assert len(logs) == 2
    assert tr._xep_ref is ref, "the reference was rebound during the run"
    assert tr.xep_reference_sha256 == ref.sha256
    shas = [log["xep_reference_sha256"] for log in logs]
    assert shas == [ref.sha256, ref.sha256], f"the reference changed: {shas}"
    np.testing.assert_array_equal(ref._data, before)


def test_a_mismatched_reference_is_refused_at_construction_and_on_resume(tmp_path):
    _p1, ref = _write_reference(tmp_path, users=6, steps=10, seed=21)
    _p2, other = _write_reference(tmp_path, "other.json", users=6, steps=10, seed=22)
    factory = _real_env_factory(6)
    with pytest.raises(MCRLContractError):        # sha does not match the declaration
        cfd.CFDevTrainer(factory(), _config(), _settings(), _xep_dev(ref),
                         env_factory=factory, train_seed=9_201_000,
                         env_seed=9_202_000, mobility_seed=9_203_000,
                         xep_reference=other)
    with pytest.raises(MCRLContractError):        # D3-XEP without a reference
        cfd.CFDevTrainer(factory(), _config(), _settings(), _xep_dev(ref),
                         env_factory=factory, train_seed=9_201_000,
                         env_seed=9_202_000, mobility_seed=9_203_000)
    with pytest.raises(MCRLContractError):        # a reference on a non-XEP arm
        cfd.CFDevTrainer(factory(), _config(), _settings(),
                         cfd.DevSettings(mechanism="D3-T0", teacher="T0",
                                         devval_episodes=1),
                         env_factory=factory, train_seed=9_201_000,
                         env_seed=9_202_000, mobility_seed=9_203_000,
                         xep_reference=ref)
    tr = _xep_trainer(ref, cfg_kw={"episodes": 1})
    state = tr.training_state_dict()
    assert state["dev"]["xep_reference_sha256"] == ref.sha256
    state["dev"] = dict(state["dev"], xep_reference_sha256="f" * 64)
    with pytest.raises(MCRLContractError):
        _xep_trainer(ref, cfg_kw={"episodes": 1}).load_training_state_dict(state)


def test_the_d3_xep_loss_is_the_d3_loss_pointed_at_the_reference_action(tmp_path):
    """Same margin loss, same weight, same masks -- only the target changes."""
    _path, ref = _write_reference(tmp_path, users=6, steps=10, seed=31)
    tr = _xep_trainer(ref, cfg_kw={"episodes": 1})
    assert tr.dev.teacher_weight == tr.dev.lambda_e == 1.0
    assert tr.dev.margin == 0.15
    factory = _real_env_factory(6)
    env = factory()
    states, masks = env.reset(np.random.default_rng(9_202_000),
                              np.random.default_rng(9_203_000))[:2]
    t0_acts, used_acts, used_scores, legal, raw = tr.teacher_labels(states, masks, step=0)
    ref_scores, ref_acts = cft.t0_xep_labels(ref.states_at(0), legal)
    np.testing.assert_array_equal(used_acts, ref_acts)
    np.testing.assert_array_equal(used_scores, ref_scores)
    np.testing.assert_array_equal(raw, cft.t0_score_matrix(states))
    for u in range(len(t0_acts)):
        if bool(legal[u].any()):
            assert bool(legal[u][used_acts[u]])
    with pytest.raises(MCRLContractError):        # the step index is mandatory
        tr.teacher_labels(states, masks)


def test_devval_reports_t0_xep_agreement_with_the_real_t0(tmp_path):
    """Amendment 12's residual-leakage diagnostic, independently recomputed.

    Red under: xep_agreement_against_itself, xep_reference_state_not_substituted.
    """
    _path, ref = _write_reference(tmp_path, users=6, steps=10, seed=41)
    tr = _xep_trainer(ref, cfg_kw={"episodes": 1})
    res = tr.devval()
    for key in ("t0_agreement", "t0_score_regret", "t0xep_agreement",
                "t0xep_score_regret", "t0xep_random_legal_agreement_expected"):
        assert key in res, key
    assert res["xep_reference"]["sha256"] == ref.sha256

    # recompute the diagnostic from scratch on the same episodes
    seeds = tr.devval_seeds()
    factory = _real_env_factory(6)
    agree = expected = 0.0
    decisions = 0
    for env_seed, mob_seed in seeds:
        env = factory()
        env_rng = np.random.default_rng(env_seed)
        mob_rng = np.random.default_rng(mob_seed)
        states, masks, _ = env.reset(env_rng, mob_rng)
        enc = tr.encode_at(states, 0)
        for t in range(env.config.steps_per_episode):
            _scores, t0_acts, legal = cft.t0_scores(states, masks)
            xep_acts = cft.t0_xep_labels(ref.states_at(t), legal)[1]
            for u in range(len(t0_acts)):
                if not bool(legal[u].any()):
                    continue
                decisions += 1
                agree += float(int(xep_acts[u]) == int(t0_acts[u]))
                expected += 1.0 / float(int(legal[u].sum()))
            out = env.step(tr.greedy_actions(enc, masks), env_rng)
            states, masks = out.user_states, out.action_masks
            enc = tr.encode_at(states, t + 1)
            if out.done:
                break
    assert decisions == res["t0xep_decisions"]
    assert res["t0xep_agreement"] == pytest.approx(agree / decisions)
    assert res["t0xep_random_legal_agreement_expected"] == pytest.approx(
        expected / decisions)
    assert res["t0xep_agreement"] < 1.0, "the null cannot BE the teacher"


def test_the_xep_probe_changes_no_number_it_observes(tmp_path):
    """The residual-leakage probe advises; it never acts."""
    _path, ref = _write_reference(tmp_path, users=6, steps=10, seed=43)
    tr = _xep_trainer(ref, cfg_kw={"episodes": 1})
    factory = _real_env_factory(6)
    greedy = (lambda enc, masks, states: tr.greedy_actions(enc, masks))
    with_probe = cfd.dev_rollout(lambda i: greedy, env_factory=factory,
                                 encode=tr.encode_at, seeds=tr.devval_seeds(),
                                 t0_agreement=True, xep_probe=tr.xep_probe())
    without = cfd.dev_rollout(lambda i: greedy, env_factory=factory,
                              encode=tr.encode_at, seeds=tr.devval_seeds(),
                              t0_agreement=True)
    for key in ("ee", "bits", "joules", "served", "t0_agreement", "t0_score_regret"):
        assert with_probe[key] == without[key], key
    assert "t0xep_agreement" not in without
    with pytest.raises(MCRLContractError):
        cfd.dev_rollout(lambda i: greedy, env_factory=factory, encode=tr.encode_at,
                        seeds=tr.devval_seeds(), xep_probe=tr.xep_probe())


def test_xep_leakage_scores_the_null_against_the_real_teacher():
    """The diagnostic's two arguments are two different teachers.

    Red under: xep_agreement_against_itself.
    """
    legal = np.zeros((3, 28), dtype=bool)
    legal[0, [1, 2, 3, 4]] = True
    legal[1, [5, 6]] = True
    legal[2, :] = False
    scores = np.zeros((3, 28))
    scores[0, 1], scores[0, 2] = 1.0, 0.25
    scores[1, 5], scores[1, 6] = 2.0, 0.5
    t0_acts = np.array([1, 5, -1])
    xep_acts = np.array([2, 5, -1])
    agree, regret, expected, decisions = cfd.xep_leakage(xep_acts, t0_acts, legal, scores)
    assert decisions == 2                     # the all-illegal row does not count
    assert agree == 1.0                       # one of two matches
    assert regret == pytest.approx(0.75)      # 1.0 - 0.25 on row 0, 0 on row 1
    assert expected == pytest.approx(1 / 4 + 1 / 2)


# ---------------------------------------------------------------- S1 lane
def test_s1_seed_guard_refuses_every_development_and_reserved_stream():
    """Amendment 13 sections 4 and 5: fresh formal namespaces, no reuse."""
    for k in (0, 1, 2):
        assert cfd.s1_triple(k) == (9_251_000 + k, 9_252_000 + k, 9_253_000 + k)
    for seed in (9_251_000, 9_252_002, 9_253_001, 9_111_000, 9_112_023,
                 9_321_001, 9_341_211):
        assert cfd.assert_s1_seed(seed, "test") == seed
    for seed in (9_201_000, 9_202_000, 9_203_000, 9_211_000, 9_212_023, 9_221_000,
                 9_231_000, 9_241_000, 9_241_500, 9_271_000, 9_291_000):
        with pytest.raises(MCRLContractError):
            cfd.assert_s1_seed(seed, "test")     # a development stream reused
    for seed in (9_121_000, 9_122_000, 9_301_000, 9_302_000, 9_303_000,
                 9_311_000, 9_312_000):
        with pytest.raises(MCRLContractError):
            cfd.assert_s1_seed(seed, "test")     # calibration / CONFIRM
    for seed in (42, 1337, 7, 9_131_000):
        with pytest.raises(MCRLContractError):
            cfd.assert_s1_seed(seed, "test")     # outside every S1 namespace
    with pytest.raises(MCRLContractError):
        cfd.s1_triple(3)
    # the DEV guard is unchanged and still refuses the S1 namespaces
    for seed in (9_251_000, 9_252_000, 9_253_000, 9_261_000):
        with pytest.raises(MCRLContractError):
            cfd.assert_dev_seed(seed, "test")


def test_s1_null_draws_from_the_fresh_formal_namespace():
    """``D3-null`` at S1 is ``(9_261_000, k)``; the development stream is refused.

    Red under: s1_null_uses_dev_stream.
    """
    import s1_common as S
    for k in (0, 1, 2):
        d = S.s1_dev_settings(3, k)
        assert d.lane == cfd.S1_LANE
        assert d.mechanism == "D3-null" and d.teacher == "random"
        assert d.null_key == (9_261_000, k)
        assert cfd.assert_s1_null_key(d.null_key, "test") == (9_261_000, k)
        # the loss shape is unchanged -- this is seed isolation, not a mechanism change
        assert (d.margin, d.lambda_e) == (0.15, 1.0)
    for bad in ((9_241_000, 0), (9_231_000, 0), (9_261_000, 3), (9_261_000, 9_111_000),
                (9_111_000, 0)):
        with pytest.raises(MCRLContractError):
            cfd.assert_s1_null_key(bad, "test")
    with pytest.raises(MCRLContractError):
        cfd.DevSettings(lane=cfd.S1_LANE, mechanism="D3-null", teacher="random",
                        null_key=(9_241_000, 0), devval_env_base=9_111_000,
                        devval_mobility_base=9_112_000)
    # the two lanes really do produce different draws
    dev_draw = np.random.default_rng((9_241_000, 0)).integers(0, 28, 20)
    s1_draw = np.random.default_rng((9_261_000, 0)).integers(0, 28, 20)
    assert not np.array_equal(dev_draw, s1_draw)


def test_s1_trains_on_the_s1_triple_and_evaluates_on_the_formal_set():
    """Red under: s1_reuses_dev_training_triple, s1_evaluates_on_calibration."""
    import s1_common as S
    seeds = S.eval_seeds(24)
    assert seeds[0] == (9_111_000, 9_112_000)
    assert seeds[-1] == (9_111_023, 9_112_023)
    for arm in (1, 2, 3, 4, 5):
        for k in (0, 1, 2):
            triple = S.s1_triple(k)
            assert triple == (9_251_000 + k, 9_252_000 + k, 9_253_000 + k)
            d = S.s1_dev_settings(arm, k)
            assert d.lane == cfd.S1_LANE
            assert (d.devval_env_base, d.devval_mobility_base) == (9_111_000, 9_112_000)
    with pytest.raises(MCRLContractError):     # calibration is never an S1 eval set
        cfd.DevSettings(lane=cfd.S1_LANE, mechanism="D0", teacher="none",
                        devval_env_base=9_121_000, devval_mobility_base=9_122_000)
    with pytest.raises(MCRLContractError):     # nor is DEVVAL
        cfd.DevSettings(lane=cfd.S1_LANE, mechanism="D0", teacher="none",
                        devval_env_base=9_211_000, devval_mobility_base=9_212_000)
    # and the development lane still evaluates on DEVVAL, unchanged
    import dev_e0_common as D
    assert D.e0_dev_settings("D0", 0).lane == cfd.DEV_LANE
    assert D.devval_seeds(24)[0] == (9_211_000, 9_212_000)


def test_the_s1_arm_list_is_the_six_declared_arms():
    """Amendment 13 section 3, verbatim -- no resurrected D1 / D4 / B2 / exact-DR."""
    import s1_common as S
    assert sorted(S.ARMS) == [1, 2, 3, 4, 5, 6]
    labels = [S.ARMS[a].name for a in sorted(S.ARMS)]
    assert labels == ["D0", "D3-T0", "D3-null", "D3-XEP", "D2-T0-tau0p3",
                      "MODQN-eq16"]
    assert S.ARMS[5].tau == 0.3
    assert S.ARMS[6].kind == "modqn"
    assert [S.ARMS[a].kind for a in (1, 2, 3, 4, 5)] == ["cf"] * 5
    assert len(S.SPECS) == 18
    assert S.EPISODES == 1000
    assert S.SEED_INDICES == (0, 1, 2)
    assert S.eval_at(1000) == (1000,), "the formal set is read once, at the end"


def test_the_modqn_arm_keeps_the_eq16_recipe_at_the_shared_budget():
    """Red under: s1_modqn_uses_shared_bootstrap."""
    import s1_common as S
    from mcrl.runtime import training_pipeline as tp
    from mcrl.runtime.trainer_config_validation import (
        TD_BOOTSTRAP_EQ16, TD_BOOTSTRAP_SHARED,
    )
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    frozen = tp._trainer_config(record, learning_rate=0.001)
    modqn = S.s1_config(record, 6, 1000)
    assert modqn.td_bootstrap_mode == TD_BOOTSTRAP_EQ16
    assert modqn.discount_factor == frozen.discount_factor
    assert modqn.episodes == 1000
    for arm in (1, 2, 3, 4, 5):
        cf = S.s1_config(record, arm, 1000)
        assert cf.td_bootstrap_mode == TD_BOOTSTRAP_SHARED
        assert cf.discount_factor == 1.0
        # the same budget-scaled exploration schedule on both sides of the win gate
        assert cf.epsilon_decay_episodes == modqn.epsilon_decay_episodes == 222


def test_the_frozen_manifest_carries_everything_that_must_be_hashed():
    """Amendment 13 section 7 item 7.

    Red under: s1_manifest_drops_arm_configs, xep_reference_missing_from_config_hash,
    s1_reuses_dev_training_triple.
    """
    import s1_common as S
    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    m = S.declared_manifest(record, CALIB, "deadbeef")
    assert m["lane"] == cfd.S1_LANE
    assert len(m["arm_configs"]) == 18
    assert len(set(m["arm_configs"].values())) == 18, "two runs share a config hash"
    assert m["episodes"] == 1000
    assert m["namespaces"]["S1_TRAIN"] == {"train": 9_251_000, "env": 9_252_000,
                                           "mobility": 9_253_000}
    assert m["namespaces"]["S1_NULL"][0] == 9_261_000
    assert m["namespaces"]["FORMAL_EVALUATION"] == {"env": 9_111_000,
                                                    "mobility": 9_112_000}
    assert m["namespaces"]["T0_XEP_REFERENCE"]["env"] == 9_241_500
    fh = m["frozen_hyperparameters"]
    assert fh["D3"] == {"margin": 0.15, "lambda_e": 1.0}
    assert fh["D2"]["tau"] == 0.3
    assert fh["credit_mode"] == "equal_share"
    assert fh["eta"] == "fixed at eta_0"
    assert fh["t0_xep_reference_sha256"] == SEALED_XEP_SHA256
    assert m["rolled_reference"]["checkpoint_sha256"].startswith("e6b063ef")
    assert m["rolled_reference"]["training"].startswith("none")
    assert m["code_digest"] and m["code"]["src_tree_sha256"]
    # the whole declaration hashes deterministically
    body = json.dumps(m, indent=2, sort_keys=True, default=str)
    again = json.dumps(S.declared_manifest(record, CALIB, "deadbeef"),
                       indent=2, sort_keys=True, default=str)
    assert body == again


def test_the_formal_set_is_opened_with_the_complete_matrix_or_not_at_all():
    """Amendment 13 section 7, as a pure function -- no process is ever started here.

    Red under: s1_partial_matrix_allowed.
    """
    import s1_common as S
    import s1_launch
    s1_launch.assert_complete_matrix(list(S.SPECS))
    for partial in (["1:0"], ["2:0", "2:1", "2:2"], list(S.SPECS)[:-1]):
        with pytest.raises(SystemExit):
            s1_launch.assert_complete_matrix(partial)
    with pytest.raises(SystemExit):
        s1_launch.assert_complete_matrix(["1:0", "1:0"])
    s1_launch.assert_complete_matrix(["1:0"], dry_run=True)
    s1_launch.assert_complete_matrix(["1:0"], resuming=True)
