"""S1 harness preflight, MC2 round: the lane, the cell table, and ``T0-XEP``.

Every test here was first run against a NAMED MUTANT of the implementation and seen to
FAIL (``S1_MUTANT=<name> .venv/bin/pytest tests/test_s1_harness.py``), then against the
real code and seen to PASS.  Mutants are applied by the autouse ``mutant`` fixture with
``monkeypatch``; no source file is edited.  The red/green log is in
``.scratch/mc2/S1/S1-MC2-PORT.md``.

**These tests never touch a formal evaluation, calibration or CONFIRM episode.**  The
S1 lane is exercised by construction and by its guards, never by rolling one.  The
launcher's "complete matrix or nothing" rule and the preflight / formal separation are
tested as pure functions, so that a mutant which removes either cannot start a formal
run from inside the test suite.
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
from mcrl.algorithms import cf_s1 as cfs1
from mcrl.algorithms import cf_s1_lane as s1l
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
V1, V2 = "MC2-JGO-v1", "MC2-ARB-v2"

DEV_IDENTITY_BASE_COMMIT = "6136c514"
DEV_IDENTITY_GOLDEN = {
    # Regenerate with the base tree (code identical at 6136c514 / 67e175bd):
    #   dev_e0_common.arm_config_payload(record, CALIB, arm, k,
    #       episodes=300, devval_episodes=24, calibration_sha256="deadbeef")
    # hashed with dev_e0_common.config_hash.  MULTI-D3 arms use the teacher set
    # ("T0","T_MINLOAD") / n_proposals = 2.
    "1:0": "aa3abfd984f70f3101449b99bc553060ef05d56cb18f3251881515d51d5aa5a8",
    "1:1": "bf353441c5819cd6f4f500d816ae493058e78fc2cc83292416d3aae0a671cfea",
    "2:0": "e9d84007b97b84aa24a3b15da3527661007186976cc5bd13861f9ee325c7f39d",
    "3:0": "b66d015cda120460f836868941180b3029fdacd62d9ff8fa7c301c4098b8a0f7",
    "4:0": "6ad6a24998514b68335ebf70adeff01f7fe66cfa78d1f8424c50ff503e8344c8",
    "4:1": "61076c17643aadb3288c46d21a09519fe9509108cfc25e5b7e73cf605f03843f",
    "5:0": "03f584c92de6769b97859164e4adb7599878683044354dc542de3ed6822d08df",
    "6:0": "dec7cb62d33f21c263eb7f10ce9445ac16ee8fb8aaeb253744cadb18e99cbba5",
    "7:0": "25c948ac052a45a145d0a7d1011e1a3c999f5404522ff3db4b26b4686165d168",
    "7:1": "0af776c3a5a9e858da458dcc23b8358cf1c2ebc40c0808aa383bad620b366e54",
    "8:0": "0a4d93e664c58b059b7eed09ecaf9d18d688df7fc356b2edab736750cba13168",
    "9:0": "3be79568186bc1a08364093341f16dcbcbd97492a11ea071021b3fad027ac2cf",
}
DEV_SETTINGS_FIELDS = (
    "mechanism", "teacher", "alpha", "tau", "tau_s", "margin", "lambda_e",
    "null_key", "devval_env_base", "devval_mobility_base", "devval_episodes",
)


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
    base = dict(lane=cfs1.DEV_LANE, mechanism=cfs1.XEP_MECHANISM,
                teacher=cfs1.XEP_TEACHER, devval_episodes=1,
                xep_reference_sha256=reference.sha256,
                xep_reference_key=reference.key,
                xep_reference_policy=reference.policy)
    base.update(kw)
    return cfs1.S1DevSettings(**base)


def _trainer(dev, *, users=6, cfg_kw=None, reference=None):
    factory = _real_env_factory(users)
    return cfs1.S1Trainer(
        factory(), _config(**(cfg_kw or {})), _settings(), dev,
        env_factory=factory, train_seed=9_201_000, env_seed=9_202_000,
        mobility_seed=9_203_000, xep_reference=reference,
    )


def _xep_trainer(reference, *, users=6, cfg_kw=None):
    return _trainer(_xep_dev(reference), users=users, cfg_kw=cfg_kw,
                    reference=reference)


def _ctx(step: int, last: int = 9):
    return cft.TeacherContext(driver=None, candidates=None, step_index=step,
                              is_final_step=(step >= last))


# ---------------------------------------------------------------- mutants
@pytest.fixture(autouse=True)
def mutant(monkeypatch, tmp_path_factory):
    T = cfs1.S1Trainer
    if MUTANT == "xep_reference_state_not_substituted":
        real = T.teacher_labels_ext

        def bad(self, states, masks):
            t0, used, sc, legal, raw, m, s = real(self, states, masks)
            if self.dev.is_xep:
                used, sc = t0, raw       # the CURRENT state's T0, not the reference's
            return t0, used, sc, legal, raw, m, s

        monkeypatch.setattr(T, "teacher_labels_ext", bad)
    elif MUTANT == "xep_current_mask_not_applied":
        def bad(reference_states, current_mask):
            scores = cfs1.t0_score_matrix(reference_states)
            return scores, np.argmax(scores, axis=1).astype(np.int64)

        monkeypatch.setattr(cfs1, "t0_xep_labels", bad)
    elif MUTANT == "xep_reference_regenerated_per_episode":
        real = T.teacher_labels_ext
        tmp = tmp_path_factory.mktemp("regen")
        counter = {"n": 0}

        def bad(self, states, masks):
            if self.dev.is_xep and self._teacher_context.step_index == 0:
                counter["n"] += 1
                payload = _reference_payload(
                    users=self._xep_ref.users, steps=self._xep_ref.steps,
                    seed=1000 + counter["n"])
                path = tmp / f"regen-{counter['n']}.json"
                digest = cfx.write_reference(path, payload)
                self._xep_ref = cfx.load_reference(path, digest)
            return real(self, states, masks)

        monkeypatch.setattr(T, "teacher_labels_ext", bad)
    elif MUTANT == "xep_agreement_against_itself":
        real = cfs1.xep_leakage

        def bad(xep_actions, t0_actions, legal, t0_scores):
            return real(xep_actions, xep_actions, legal, t0_scores)

        # every consumer (the probe and the collection-time counters) resolves
        # ``xep_leakage`` through the module, so one patch reaches all of them
        monkeypatch.setattr(cfs1, "xep_leakage", bad)
    elif MUTANT == "xep_reference_missing_from_config_hash":
        import s1_common as S
        real = S.cell_config_payload

        def bad(*args, **kwargs):
            payload = real(*args, **kwargs)
            for key in ("xep_reference_sha256", "xep_reference_key",
                        "xep_reference_policy"):
                payload.get("dev_settings", {}).pop(key, None)
            return payload

        monkeypatch.setattr(S, "cell_config_payload", bad)
    elif MUTANT == "s1_null_uses_dev_stream":
        import s1_common as S
        real = S.null_key

        def bad(spec, k, *, lane=S.S1_LANE):
            if spec.null_role == "D3-null":
                return (9_241_000, int(k))
            return real(spec, k, lane=lane)

        monkeypatch.setattr(S, "null_key", bad)
    elif MUTANT == "s1_bnull_uses_dev_stream":
        import s1_common as S
        real = S.null_key

        def bad(spec, k, *, lane=S.S1_LANE):
            if spec.null_role == "MC2-B-null":
                return (9_243_000, int(k))
            return real(spec, k, lane=lane)

        monkeypatch.setattr(S, "null_key", bad)
    elif MUTANT == "s1_reuses_dev_training_triple":
        import s1_common as S
        monkeypatch.setattr(S, "train_triple",
                            lambda k, *, lane=S.S1_LANE: (9_201_000 + int(k),
                                                          9_202_000 + int(k),
                                                          9_203_000 + int(k)))
    elif MUTANT == "s1_evaluates_on_calibration":
        import s1_common as S
        monkeypatch.setattr(S, "EVAL_ENV_BASE", 9_121_000)
        monkeypatch.setattr(S, "EVAL_MOB_BASE", 9_122_000)
        monkeypatch.setattr(S, "eval_bases",
                            lambda lane=S.S1_LANE: (9_121_000, 9_122_000))
        monkeypatch.setattr(s1l, "FORMAL_EVAL_ENV_BASE", 9_121_000)
        monkeypatch.setattr(s1l, "FORMAL_EVAL_MOB_BASE", 9_122_000)
    elif MUTANT == "s1_modqn_uses_shared_bootstrap":
        import cf3_common as C
        import dev_e0_common as D
        import s1_common as S

        def bad(record, spec, episodes):
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
                            lambda specs, declared, **kw: None)
    elif MUTANT == "s1_preflight_runs_the_formal_lane":
        import s1_common as S
        monkeypatch.setattr(S, "train_triple",
                            lambda k, *, lane=S.S1_LANE: s1l.s1_triple(k))
        monkeypatch.setattr(S, "eval_bases",
                            lambda lane=S.S1_LANE: (s1l.FORMAL_EVAL_ENV_BASE,
                                                    s1l.FORMAL_EVAL_MOB_BASE))
    elif MUTANT == "s1_v1_duplicates_a_only":
        import s1_common as S
        real = S.cells

        def bad(mechanism_id, *, optional=()):
            table = real(mechanism_id, optional=optional)
            if mechanism_id == V1:
                extra = dataclasses.replace(table["D3-T0"], name="A-only",
                                            serves=("FULL_vs_A_only[v1]",))
                table = {**table, "A-only": extra}
            return table

        monkeypatch.setattr(S, "cells", bad)
    elif MUTANT == "s1_v2_drop_one_is_d3t0":
        import s1_common as S
        monkeypatch.setitem(S.DROP_ONE_OF_B, V2, "D3-T0")
        real = S.cells

        def bad(mechanism_id, *, optional=()):
            table = dict(real(mechanism_id, optional=optional))
            table.pop("A-only-v2", None)
            return table

        monkeypatch.setattr(S, "cells", bad)
    elif MUTANT == "s1_eval_read_keeps_the_sources":
        class _Noop:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

        monkeypatch.setattr(cfs1, "sources_unregistered", lambda: _Noop())
    elif MUTANT == "s1_eval_at_adds_an_intermediate_read":
        import s1_common as S
        monkeypatch.setattr(S, "eval_at", lambda episodes: (500, int(episodes)))
    elif MUTANT:
        raise AssertionError(f"unknown mutant {MUTANT}")
    yield


# ---------------------------------------------------------------- T0-XEP core
def test_t0_score_matrix_is_t0s_own_expression():
    """``T0-XEP`` scores with T0's own function, so the two cannot drift apart."""
    states, masks = _states(30, seed=7)
    scores, _acts, _legal = cft.t0_scores(states, masks)
    np.testing.assert_array_equal(scores, cfs1.t0_score_matrix(states))
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
        scores, acts = cfs1.t0_xep_labels(ref_states, legal)
        np.testing.assert_array_equal(scores, cfs1.t0_score_matrix(ref_states))
        assert not np.allclose(scores, t0_scores), "the reference was not substituted"
        np.testing.assert_array_equal(acts, cft.masked_argmax_rows(scores, legal))
        for u in range(40):
            assert bool(legal[u][acts[u]]), "T0-XEP advised an illegal action"
        assert (acts != t0_acts).sum() > 0, "the null is not decorrelated at all"
    a0 = cfs1.t0_xep_labels(ref.states_at(0), legal)[1]
    a5 = cfs1.t0_xep_labels(ref.states_at(5), legal)[1]
    assert not np.array_equal(a0, a5), "step t is not matched to step t"


def test_t0_xep_fails_closed_off_the_end_and_on_a_user_count_mismatch(tmp_path):
    _path, ref = _write_reference(tmp_path, users=8, steps=10, seed=5)
    _s8, masks8 = _states(8, seed=1)
    legal8 = np.array([m.mask for m in masks8], dtype=bool)
    cfs1.t0_xep_labels(ref.states_at(9), legal8)
    with pytest.raises(MCRLContractError):
        ref.states_at(10)
    with pytest.raises(MCRLContractError):
        ref.states_at(-1)
    _s9, masks9 = _states(9, seed=1)
    legal9 = np.array([m.mask for m in masks9], dtype=bool)
    with pytest.raises(MCRLContractError):
        cfs1.t0_xep_labels(ref.states_at(0), legal9)


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
    with pytest.raises(ValueError):                 # the loaded arrays are read-only
        ref.states_at(0)[0].channel_quality[0] = 1.0


def test_the_committed_reference_is_the_sealed_one():
    """The reference carried over from the accepted harness: identity + sha256."""
    import s1_common as S
    assert S.XEP_REFERENCE_SHA256 == SEALED_XEP_SHA256
    if not S.XEP_REFERENCE_PATH.is_file():
        pytest.skip("reference file not present in this checkout")
    ref = S.load_xep_reference()
    assert ref.sha256 == SEALED_XEP_SHA256
    assert ref.key == (9_241_500, 9_241_501)
    assert ref.policy == "T0"
    assert (ref.steps, ref.users) == (10, 100)
    for seed in ref.key:                    # DEV-NULL, never DEV / DEVVAL / formal
        assert cfd.assert_dev_seed(seed, "sealed reference") == seed
        assert any(b <= seed <= b + 999 for b in cfd.DEV_NULL_KEY_BASES)
        with pytest.raises(MCRLContractError):
            s1l.assert_s1_seed(seed, "sealed reference")   # never an S1 SEED


def test_a_d3_xep_configuration_without_its_reference_is_refused(tmp_path):
    _path, ref = _write_reference(tmp_path, users=4, steps=10, seed=9)
    with pytest.raises(MCRLContractError):
        cfs1.S1DevSettings(lane=cfs1.DEV_LANE, mechanism=cfs1.XEP_MECHANISM,
                           teacher=cfs1.XEP_TEACHER)
    with pytest.raises(MCRLContractError):
        _xep_dev(ref, teacher="T0")
    with pytest.raises(MCRLContractError):        # the reference must be DEV-NULL
        _xep_dev(ref, xep_reference_key=(9_111_000, 9_112_000))
    with pytest.raises(MCRLContractError):
        _xep_dev(ref, xep_reference_key=(9_201_000, 9_202_000))
    with pytest.raises(MCRLContractError):        # only D3-XEP carries one
        cfs1.S1DevSettings(lane=cfs1.DEV_LANE, mechanism="D3-T0", teacher="T0",
                           xep_reference_sha256=ref.sha256,
                           xep_reference_key=ref.key, xep_reference_policy="T0")
    # and the DEVELOPMENT settings class cannot name the arm at all
    with pytest.raises(MCRLContractError):
        cfd.DevSettings(mechanism=cfs1.XEP_MECHANISM, teacher=cfs1.XEP_TEACHER)


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
    for log in logs:                       # the collection-time leakage counters
        assert log["teacher_action_vs_t0_decisions"] > 0
        assert 0.0 <= log["teacher_action_vs_t0_agreement"] < 1.0
        assert log["teacher_action_vs_t0_random_legal_agreement_expected"] > 0.0


def test_a_mismatched_reference_is_refused_at_construction_and_on_resume(tmp_path):
    _p1, ref = _write_reference(tmp_path, users=6, steps=10, seed=21)
    _p2, other = _write_reference(tmp_path, "other.json", users=6, steps=10, seed=22)
    with pytest.raises(MCRLContractError):        # sha does not match the declaration
        _trainer(_xep_dev(ref), reference=other)
    with pytest.raises(MCRLContractError):        # D3-XEP without a reference
        _trainer(_xep_dev(ref))
    with pytest.raises(MCRLContractError):        # a reference on a non-XEP arm
        _trainer(cfs1.S1DevSettings(lane=cfs1.DEV_LANE, mechanism="D3-T0",
                                    teacher="T0", devval_episodes=1),
                 reference=ref)
    tr = _xep_trainer(ref, cfg_kw={"episodes": 1})
    state = tr.training_state_dict()
    assert state["dev"]["xep_reference_sha256"] == ref.sha256
    assert state["dev"]["lane"] == cfs1.DEV_LANE
    state["dev"] = dict(state["dev"], xep_reference_sha256="f" * 64)
    with pytest.raises(MCRLContractError):
        _xep_trainer(ref, cfg_kw={"episodes": 1}).load_training_state_dict(state)
    state["dev"] = dict(state["dev"], xep_reference_sha256=ref.sha256,
                        lane=cfs1.S1_LANE)
    with pytest.raises(MCRLContractError):
        _xep_trainer(ref, cfg_kw={"episodes": 1}).load_training_state_dict(state)


def test_the_d3_xep_loss_is_the_d3_loss_pointed_at_the_reference_action(tmp_path):
    """Same margin loss, same weight, same masks -- only the target changes.

    Red under: xep_reference_state_not_substituted, xep_current_mask_not_applied.
    """
    import torch
    _path, ref = _write_reference(tmp_path, users=6, steps=10, seed=31)
    tr = _xep_trainer(ref, cfg_kw={"episodes": 1})
    assert tr.dev.teacher_weight == tr.dev.lambda_e == 1.0
    assert tr.dev.margin == 0.15
    factory = _real_env_factory(6)
    env = factory()
    states, masks = env.reset(np.random.default_rng(9_202_000),
                              np.random.default_rng(9_203_000))[:2]
    tr._teacher_context = _ctx(0, env.config.steps_per_episode - 1)
    t0_acts, used_acts, used_scores, legal, raw, member, slots = \
        tr.teacher_labels_ext(states, masks)
    ref_scores, ref_acts = cfs1.t0_xep_labels(ref.states_at(0), legal)
    np.testing.assert_array_equal(used_acts, ref_acts)
    np.testing.assert_array_equal(used_scores, ref_scores)
    np.testing.assert_array_equal(raw, cfs1.t0_score_matrix(states))
    assert member is None and slots is None
    for u in range(len(t0_acts)):
        if bool(legal[u].any()):
            assert bool(legal[u][used_acts[u]])
    tr._teacher_context = None
    with pytest.raises(MCRLContractError):       # the step seam is mandatory
        tr.teacher_labels_ext(states, masks)

    # the loss IS the inherited D3 branch: same batch, same target, same value
    batch = {"masks": np.array([m.mask for m in masks], dtype=bool),
             "teacher_action": np.asarray(ref_acts, dtype=np.int64)}
    q_all = [torch.randn(len(masks), 28, dtype=torch.float32,
                         generator=torch.Generator().manual_seed(7 + h))
             for h in range(3)]
    d3 = _trainer(cfs1.S1DevSettings(lane=cfs1.DEV_LANE, mechanism="D3-T0",
                                     teacher="T0", devval_episodes=1))
    mine = tr._teacher_loss(batch, q_all)
    theirs = cfd.CFDevTrainer._teacher_loss(d3, batch, q_all)
    assert torch.equal(mine, theirs), "D3-XEP is not the D3 loss on the same target"


def test_the_evaluation_read_reports_t0_xep_agreement_with_the_real_t0(tmp_path):
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
            xep_acts = cfs1.t0_xep_labels(ref.states_at(t), legal)[1]
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
    assert decisions == res["t0xep_decisions"] == res["t0_decisions"]
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
    probe = tr.xep_probe()

    def factory_with_probe(i):
        probe.new_episode()
        return probe.wrap(greedy)

    with_probe = cfd.dev_rollout(factory_with_probe, env_factory=factory,
                                 encode=tr.encode_at, seeds=tr.devval_seeds(),
                                 t0_agreement=True, lane=cfs1.DEV_LANE)
    without = cfd.dev_rollout(lambda i: greedy, env_factory=factory,
                              encode=tr.encode_at, seeds=tr.devval_seeds(),
                              t0_agreement=True, lane=cfs1.DEV_LANE)
    for key in ("ee", "bits", "joules", "served", "t0_agreement", "t0_score_regret"):
        assert with_probe[key] == without[key], key
    assert "t0xep_agreement" not in without


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
    agree, regret, expected, decisions = cfs1.xep_leakage(xep_acts, t0_acts, legal,
                                                         scores)
    assert decisions == 2                     # the all-illegal row does not count
    assert agree == 1.0                       # one of two matches
    assert regret == pytest.approx(0.75)      # 1.0 - 0.25 on row 0, 0 on row 1
    assert expected == pytest.approx(1 / 4 + 1 / 2)


# ---------------------------------------------------------------- the S1 lane
def test_s1_seed_guard_refuses_every_development_and_reserved_stream():
    """Amendment 13 sections 4 and 5: fresh formal namespaces, no reuse."""
    for k in (0, 1, 2):
        assert s1l.s1_triple(k) == (9_251_000 + k, 9_252_000 + k, 9_253_000 + k)
    for seed in (9_251_000, 9_252_002, 9_253_001, 9_111_000, 9_112_023,
                 9_321_001, 9_341_211):
        assert s1l.assert_s1_seed(seed, "test") == seed
    for seed in (9_201_000, 9_202_000, 9_203_000, 9_211_000, 9_212_023, 9_221_000,
                 9_231_000, 9_241_000, 9_241_500, 9_243_000, 9_271_000, 9_291_000):
        with pytest.raises(MCRLContractError):
            s1l.assert_s1_seed(seed, "test")     # a development stream reused
    for seed in (9_121_000, 9_122_000, 9_301_000, 9_302_000, 9_303_000,
                 9_311_000, 9_312_000):
        with pytest.raises(MCRLContractError):
            s1l.assert_s1_seed(seed, "test")     # calibration / CONFIRM
    for seed in (42, 1337, 7, 9_131_000, 9_261_000, 9_263_000):
        with pytest.raises(MCRLContractError):
            s1l.assert_s1_seed(seed, "test")     # outside every S1 namespace
    with pytest.raises(MCRLContractError):
        s1l.s1_triple(3)
    # the DEV guard is unchanged and still refuses every S1 namespace
    for seed in (9_251_000, 9_252_000, 9_253_000, 9_261_000, 9_263_000):
        with pytest.raises(MCRLContractError):
            cfd.assert_dev_seed(seed, "test")
    for key in ((9_261_000, 0), (9_263_000, 0)):
        with pytest.raises(MCRLContractError):
            cfd.assert_dev_null_key(key, "test")
    # an unknown lane is refused, never silently unguarded
    with pytest.raises(MCRLContractError):
        cfd.assert_lane_seed(9_251_000, "test", lane="whatever")


def test_the_s1_null_keys_are_declared_and_collide_with_nothing():
    """Every S1 null identity, as a STREAM and not only as an argument.

    Red under: s1_null_uses_dev_stream, s1_bnull_uses_dev_stream.

    Two hazards are checked here because both are silent:
    * a null whose base belongs to the other lane (seed isolation broken);
    * numpy's ``SeedSequence`` aliasing -- ``default_rng((B, 0))`` IS
      ``default_rng(B)`` -- which would make a composite key's k = 0 member share a
      stream with an integer seed ``B`` if ``B`` were ever a legal integer seed.
    """
    import s1_common as S
    assert s1l.S1_NULL_BASE_FOR == {"D3-null": 9_261_000, "MC2-B-null": 9_263_000}
    for k in (0, 1, 2):
        assert s1l.s1_null_key("D3-null", k) == (9_261_000, k)
        assert s1l.s1_null_key("MC2-B-null", k) == (9_263_000, k)
    for bad in ((9_241_000, 0), (9_243_000, 0), (9_231_000, 0), (9_261_000, 3),
                (9_261_000, 9_111_000), (9_111_000, 0), (9_121_000, 0)):
        with pytest.raises(MCRLContractError):
            s1l.assert_s1_null_key(bad, "test")
    with pytest.raises(MCRLContractError):      # the other null's base is refused
        s1l.assert_s1_null_key((9_263_000, 0), "test", base=9_261_000)
    with pytest.raises(MCRLContractError):
        s1l.assert_s1_null_key((9_261_000, 0), "test", base=9_263_000)

    # -- stream level: nothing any lane constructs may coincide ---------------
    def draws(seed):
        return tuple(int(x) for x in np.random.default_rng(seed).integers(0, 2**62, 8))

    streams: dict[str, tuple] = {}
    for k in (0, 1, 2):
        t = s1l.s1_triple(k)
        for name, seed in zip(("s1_train", "s1_env", "s1_mob"), t):
            streams[f"{name}:{k}"] = draws(seed)
        streams[f"s1_catfish:{k}"] = draws(t[0] + 70_001)
        streams[f"s1_null_d3:{k}"] = draws((9_261_000, k))
        streams[f"s1_null_mc2:{k}"] = draws((9_263_000, k))
    for k in range(20):
        if k == 9:
            continue
        for base, name in ((9_201_000, "dev_train"), (9_202_000, "dev_env"),
                           (9_203_000, "dev_mob")):
            streams[f"{name}:{k}"] = draws(base + k)
        for base, name in ((9_231_000, "dev_null_d2"), (9_241_000, "dev_null_d3"),
                           (9_243_000, "dev_null_mc2")):
            streams[f"{name}:{k}"] = draws((base, k))
    for i in range(24):
        streams[f"formal_env:{i}"] = draws(9_111_000 + i)
        streams[f"formal_mob:{i}"] = draws(9_112_000 + i)
        streams[f"devval_env:{i}"] = draws(9_211_000 + i)
        streams[f"devval_mob:{i}"] = draws(9_212_000 + i)
    seen: dict[tuple, str] = {}
    for name, stream in streams.items():
        clash = seen.get(stream)
        assert clash is None, f"{name} and {clash} are the same stream"
        seen[stream] = name

    # The aliasing itself, stated so it cannot be rediscovered as a surprise.
    # In the S1 lane it is structurally harmless: a null base is not a legal S1
    # INTEGER seed, in either lane's guard.
    import dev_e0_common as D
    for base in (9_261_000, 9_263_000):
        assert draws((base, 0)) == draws(base), "numpy changed its SeedSequence padding"
        with pytest.raises(MCRLContractError):
            s1l.assert_s1_seed(base, "test")
        with pytest.raises(MCRLContractError):
            cfd.assert_dev_seed(base, "test")
    # In the DEVELOPMENT lane the DEV-NULL bases ARE legal integer seeds (they sit
    # inside the declared DEV-NULL ranges), so there the aliasing is harmless only
    # because no declared development construction ever produces one.  Recorded as a
    # measured fact rather than assumed.
    dev_integers = {s for k in range(20) if k != 9 for s in D.dev_triple(k)}
    dev_integers |= {9_211_000 + i for i in range(24)}
    dev_integers |= {9_212_000 + i for i in range(24)}
    dev_integers |= {9_221_000 + i for i in range(24)}
    dev_integers |= {9_241_500, 9_241_501}          # the sealed T0-XEP reference
    for base in (9_231_000, 9_241_000, 9_243_000):
        assert draws((base, 0)) == draws(base)
        if any(lo <= base <= hi for lo, hi, _n in cfd.ALLOWED_SEED_RANGES):
            assert base not in dev_integers, (
                f"{base} is both a DEV-NULL base and a constructed integer seed: its "
                "k = 0 null stream would alias that seed's stream"
            )
    assert S.null_key(S.cell(V1, "B-null"), 0) == (9_263_000, 0)
    assert S.null_key(S.cell(V1, "D3-null", optional=("D3-null",)), 1) == (9_261_000, 1)


def test_s1_trains_on_the_s1_triple_and_evaluates_on_the_formal_set():
    """Red under: s1_reuses_dev_training_triple, s1_evaluates_on_calibration."""
    import s1_common as S
    seeds = S.eval_seeds(24)
    assert seeds[0] == (9_111_000, 9_112_000)
    assert seeds[-1] == (9_111_023, 9_112_023)
    for name in ("D0", "D3-T0", "D2-T0-tau0p3"):
        for k in (0, 1, 2):
            assert S.train_triple(k) == (9_251_000 + k, 9_252_000 + k, 9_253_000 + k)
            d = S.s1_dev_settings(V1, name, k)
            assert d.lane == cfs1.S1_LANE
            assert (d.devval_env_base, d.devval_mobility_base) == (9_111_000, 9_112_000)
    with pytest.raises(MCRLContractError):     # calibration is never an S1 eval set
        cfs1.S1DevSettings(mechanism="D0", teacher="none",
                           devval_env_base=9_121_000, devval_mobility_base=9_122_000)
    with pytest.raises(MCRLContractError):     # nor is DEVVAL, in the formal lane
        cfs1.S1DevSettings(mechanism="D0", teacher="none",
                           devval_env_base=9_211_000, devval_mobility_base=9_212_000)
    # and the development lane still evaluates on DEVVAL, unchanged
    import dev_e0_common as D
    assert cfd.lane_of(D.e0_dev_settings("D0", 0)) == cfd.DEV_LANE
    assert D.devval_seeds(24)[0] == (9_211_000, 9_212_000)


def test_the_preflight_lane_is_the_same_code_on_development_seeds():
    """The harness's own preflight: DEV triple, DEVVAL, development nulls.

    Red under: s1_preflight_runs_the_formal_lane, s1_reuses_dev_training_triple.
    """
    import s1_common as S
    import run_s1
    assert S.train_triple(0, lane=S.DEV_LANE) == (9_201_000, 9_202_000, 9_203_000)
    assert S.eval_bases(S.DEV_LANE) == (9_211_000, 9_212_000)
    assert S.eval_seeds(4, lane=S.DEV_LANE)[0] == (9_211_000, 9_212_000)
    d = S.s1_dev_settings(V1, "D3-T0", 0, eval_episodes=4, lane=S.DEV_LANE)
    assert d.lane == cfd.DEV_LANE
    assert (d.devval_env_base, d.devval_mobility_base) == (9_211_000, 9_212_000)
    # a preflight configuration can never hash to a formal one
    formal = S.s1_dev_settings(V1, "D3-T0", 0, eval_episodes=4)
    assert dataclasses.asdict(d) != dataclasses.asdict(formal)
    # the formal lane refuses the development seeds, and the preflight the formal ones
    with pytest.raises(MCRLContractError):
        cfd.assert_lane_seed(9_201_000, "test", lane=cfs1.S1_LANE)
    with pytest.raises(MCRLContractError):
        cfd.assert_lane_seed(9_251_000, "test", lane=cfd.DEV_LANE)
    with pytest.raises(MCRLContractError):
        cfd.assert_lane_seed(9_111_000, "test", lane=cfd.DEV_LANE)
    assert run_s1.PREFLIGHT_MAX_EPISODES <= 20
    assert run_s1.FORMAL_MANIFEST != run_s1.PREFLIGHT_MANIFEST


def test_the_cell_table_is_a_function_of_the_frozen_mechanism_id():
    """The matrix is parameterised by the version, and A-only is never duplicated.

    Red under: s1_v1_duplicates_a_only, s1_v2_drop_one_is_d3t0.
    """
    import s1_common as S
    v1 = S.cells(V1)
    assert list(v1) == ["D0", "D3-T0", "B-only", "FULL", "B-null",
                        "D2-T0-tau0p3", "MODQN-eq16"]
    assert S.DROP_ONE_OF_B[V1] == "D3-T0"
    assert len([c for c in v1.values() if c.mechanism == "D3-T0"]) == 1, \
        "A-only and the single-Catfish baseline are ONE cell under v1"
    v2 = S.cells(V2)
    assert list(v2) == ["D0", "D3-T0", "A-only-v2", "B-only", "FULL", "B-null",
                        "D2-T0-tau0p3", "MODQN-eq16"]
    assert S.DROP_ONE_OF_B[V2] == "A-only-v2"
    assert v2["A-only-v2"].sources == ("A",) and v2["A-only-v2"].is_judge
    assert len(S.specs(V1)) == 21 and len(S.specs(V2)) == 24
    for mid in (V1, V2):
        table = S.cells(mid)
        assert [c.sources for c in table.values() if c.is_judge].count(("A", "B")) == 1
        assert table["B-null"].null_role == "MC2-B-null"
        assert table["MODQN-eq16"].kind == "modqn"
        assert S.RULE_PREFIX[mid] and S.cells(mid, optional=("D3-null", "D3-XEP"))
        # B-only is rule-independent: ONE identity under both versions
        assert table["B-only"].rule_independent
        assert table["B-only"].rule_id(mid) == S.BONLY_RULE_ID
        assert table["FULL"].rule_id(mid) == mid
        assert table["B-null"].rule_id(mid) == mid
        assert table["FULL"].cell_label(mid) == f"{S.RULE_PREFIX[mid]}-A+B"
        assert table["B-only"].cell_label(mid) == "B"
    opt = S.cells(V1, optional=("D3-null", "D3-XEP"))
    assert list(opt)[-2:] == ["D3-null", "D3-XEP"]
    assert len(S.specs(V1, optional=("D3-null", "D3-XEP"))) == 27
    assert all(c.optional for c in S.OPTIONAL_CELLS)
    with pytest.raises(SystemExit):
        S.cells("MC2-SOMETHING-v3")
    with pytest.raises(SystemExit):
        S.cells(V1, optional=("D3-T0",))
    ids = {c["id"] for c in S.COMPARISONS}
    for cell in S.cells(V2, optional=("D3-null", "D3-XEP")).values():
        for served in cell.serves:
            assert served.split("[")[0] in ids, served


def test_the_modqn_cell_keeps_the_eq16_recipe_at_the_shared_budget():
    """Red under: s1_modqn_uses_shared_bootstrap."""
    import s1_common as S
    from mcrl.runtime import training_pipeline as tp
    from mcrl.runtime.trainer_config_validation import (
        TD_BOOTSTRAP_EQ16, TD_BOOTSTRAP_SHARED,
    )
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    frozen = tp._trainer_config(record, learning_rate=0.001)
    modqn = S.s1_config(record, S.cell(V1, "MODQN-eq16"), 1000)
    assert modqn.td_bootstrap_mode == TD_BOOTSTRAP_EQ16
    assert modqn.discount_factor == frozen.discount_factor
    assert modqn.episodes == 1000
    for name in ("D0", "D3-T0", "B-only", "FULL", "B-null", "D2-T0-tau0p3"):
        cf = S.s1_config(record, S.cell(V1, name), 1000)
        assert cf.td_bootstrap_mode == TD_BOOTSTRAP_SHARED
        assert cf.discount_factor == 1.0
        # the same budget-scaled exploration schedule on both sides of the win gate
        assert cf.epsilon_decay_episodes == modqn.epsilon_decay_episodes == 222


def test_the_evaluation_read_is_one_terminal_read_of_the_deployed_rule():
    """One read, one checkpoint, and no specialist or judge on the read.

    Red under: s1_eval_at_adds_an_intermediate_read, s1_eval_read_keeps_the_sources.
    """
    import s1_common as S
    assert S.eval_at(1000) == (1000,), "the formal set is read once, at the end"
    assert S.EPISODES == 1000 and S.SEED_INDICES == (0, 1, 2) and S.N_EVAL == 24

    # the purity guard: inside it, asking any registered source is impossible
    def fake(states, masks):
        return np.zeros(len(states), dtype=np.int64)

    cft.register_teacher_source("T_FAKE", fake, replace=True)
    try:
        assert "T_FAKE" in cft.registered_teachers()
        with cfs1.sources_unregistered(), cfs1.judge_disabled():
            assert cft.registered_teachers() == ()
            with pytest.raises(MCRLContractError):
                cft.teacher_source("T_FAKE")
            with pytest.raises(MCRLContractError):
                cft.teacher_source("T0")
        assert "T_FAKE" in cft.registered_teachers() and "T0" in cft.registered_teachers()
    finally:
        cft.unregister_teacher_source("T_FAKE")
    assert cft.teacher_source("T0") is not None


@dataclasses.dataclass(frozen=True)
class _StubJudgeSpec:
    """Stand-in for ``cf_dev.JudgeSpec`` while lane A's module is not yet merged.

    It carries exactly the identity fields the MANIFEST must hash, so the
    declaration's structure is tested in both trees; the real dataclass's own
    validation is tested only once it exists (see the ``real_judge`` branch).
    """

    mechanism_id: str
    sources: tuple[str, ...]
    null_id: str | None = None
    null_key: tuple[int, int] | None = None


def _stub_judge(monkeypatch) -> bool:
    """Return True if the real judge module is present; otherwise stub it."""
    try:
        from mcrl.algorithms import cf_judge  # noqa: F401
        if hasattr(cfd, "JudgeSpec"):
            return True
    except ImportError:
        pass
    import s1_common as S

    def fake_spec(mechanism_id, name, k, *, lane=S.S1_LANE, optional=()):
        spec = S.cell(mechanism_id, name, optional=optional)
        if not spec.is_judge:
            return None
        return _StubJudgeSpec(
            mechanism_id=str(mechanism_id), sources=tuple(spec.sources),
            null_id=("MC2-UNIFORM-LEGAL-PROPOSAL-REPLACEMENT-v1"
                     if "R" in spec.sources else None),
            null_key=(S.null_key(spec, k, lane=lane) if "R" in spec.sources else None),
        )

    monkeypatch.setattr(S, "judge_spec", fake_spec)
    monkeypatch.setattr(S, "judge_source_identities",
                        lambda spec: {s: {"source_id": s} for s in spec.sources})
    # The judge MECHANISM names are registered by the mechanism commit; pre-merge the
    # declaration can still be structure-tested by registering them here only.
    judge_mechs = ("MC2",)
    monkeypatch.setattr(cft, "MECHANISMS", cft.MECHANISMS + judge_mechs)
    monkeypatch.setattr(cft, "TEACHERS", cft.TEACHERS + ("judge",))
    monkeypatch.setattr(cfd, "EXPECTED_TEACHER",
                        {**cfd.EXPECTED_TEACHER, **{m: "judge" for m in judge_mechs}})
    return False


def test_the_frozen_manifest_carries_everything_that_must_be_hashed(tmp_path,
                                                                    monkeypatch):
    """Amendment 13 section 7 item 7, for the MC2 matrix.

    Red under: s1_manifest_drops_arm_configs, xep_reference_missing_from_config_hash,
    s1_reuses_dev_training_triple, s1_null_uses_dev_stream, s1_bnull_uses_dev_stream.
    """
    import s1_common as S
    from mcrl.runtime import training_pipeline as tp
    real_judge = _stub_judge(monkeypatch)
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    bonly: dict[str, str] = {}
    full: dict[str, str] = {}
    control: dict[str, str] = {}
    rules = tmp_path / "rules.md"
    rules.write_text("frozen reading rules\n")
    for mid in (V1, V2):
        m = S.declared_manifest(record, CALIB, "deadbeef", mechanism_id=mid,
                                optional=("D3-null", "D3-XEP"),
                                reading_rules={"document": str(rules),
                                               "sha256": "f" * 64})
        n = len(S.specs(mid, optional=("D3-null", "D3-XEP")))
        assert m["lane"] == cfs1.S1_LANE
        assert len(m["arm_configs"]) == n
        assert len(set(m["arm_configs"].values())) == n, "two runs share a config hash"
        assert m["episodes"] == 1000 and m["eval_at"] == [1000]
        assert m["mechanism_id"] == mid
        assert m["drop_one_of_B"] == S.DROP_ONE_OF_B[mid]
        assert m["namespaces"]["S1_TRAIN"] == {"train": 9_251_000, "env": 9_252_000,
                                               "mobility": 9_253_000}
        assert m["namespaces"]["S1_NULL"][0] == 9_261_000
        assert m["namespaces"]["S1_NULL_MC2"][0] == 9_263_000
        assert m["namespaces"]["FORMAL_EVALUATION"] == {"env": 9_111_000,
                                                        "mobility": 9_112_000}
        assert m["namespaces"]["T0_XEP_REFERENCE"]["env"] == 9_241_500
        fh = m["frozen_hyperparameters"]
        assert fh["D3"] == {"margin": 0.15, "lambda_e": 1.0}
        assert fh["D2"]["tau"] == 0.3
        assert fh["credit_mode"] == "equal_share"
        assert fh["eta"] == "fixed at eta_0"
        assert fh["epsilon_decay_episodes"] == 222
        assert fh["t0_xep_reference_sha256"] == SEALED_XEP_SHA256
        assert m["rolled_reference"]["checkpoint_sha256"].startswith("e6b063ef")
        assert m["rolled_reference"]["training"].startswith("none")
        assert m["code_digest"] and m["code"]["src_tree_sha256"]
        assert m["reading_rules"]["sha256"]
        judged = [p for p in m["arm_payloads"].values() if p["kind"] == "judge"]
        assert judged, "no judge cell in the declaration"
        for p in judged:
            srcs = tuple(p["judge_spec"]["sources"])
            # the frozen version's rule, except the rule-INDEPENDENT shared B-only
            assert p["judge_spec"]["mechanism_id"] == (
                S.BONLY_RULE_ID if srcs == ("B",) else mid)
            assert p["judge_source_identities"]
            if "R" in tuple(p["judge_spec"]["sources"]):
                assert tuple(p["judge_spec"]["null_key"]) == (
                    9_263_000, p["seed_index"])
        # the rule-INDEPENDENT B-only cell is the SAME configuration under both
        # versions; every rule-dependent judge cell is not
        bonly[mid] = m["arm_configs"]["B-only:0"]
        full[mid] = m["arm_configs"]["FULL:0"]
        control[mid] = m["arm_configs"]["D0:0"]
        if real_judge:      # the library's own dataclass, once it is in the tree
            import dev_e0_common as D
            import mcrl.algorithms.cf_judge as cfj
            assert cfj.RULE_OF[mid] == S.RULE_PREFIX[mid]
            assert S.BONLY_RULE_ID == cfj.BONLY_MECHANISM_ID
            assert S.judge_mechanism_name() == cfj.MECHANISM_NAME
            for p in judged:
                assert p["judge_spec"]["judge_id"] == cfj.JUDGE_ID
                assert p["judge_spec"]["judge_eta0"] == cfj.ETA0_JUDGE
                assert p["mechanism"] == cfj.MECHANISM_NAME
                # the rule id is the frozen version's, except for the shared B-only
                srcs = tuple(p["judge_spec"]["sources"])
                rid = p["judge_spec"]["mechanism_id"]
                assert rid == (cfj.BONLY_MECHANISM_ID if srcs == ("B",) else mid)
                assert rid == p["rule_id"]
                assert srcs in cfj.DECLARED_CELLS[rid], (rid, srcs)
                # the development lane's own parser agrees with this cell's label
                assert D.judge_cell(p["mc2_cell_label"]) == (rid, srcs)
        # the whole declaration hashes deterministically
        again = S.declared_manifest(record, CALIB, "deadbeef", mechanism_id=mid,
                                    optional=("D3-null", "D3-XEP"),
                                    reading_rules={"document": str(rules),
                                                   "sha256": "f" * 64})
        assert json.dumps(m, sort_keys=True, default=str) == json.dumps(
            again, sort_keys=True, default=str)
    # a cell's identity is what it computes, not where it sits in the table:
    assert bonly[V1] == bonly[V2], (
        "B-only is rule-independent and must be ONE configuration under both versions")
    assert control[V1] == control[V2], "D0 is the same control under both versions"
    assert full[V1] != full[V2], "FULL under v1 and v2 are different mechanisms"


def test_every_non_judge_cell_payload_is_distinct_and_carries_its_lane():
    """The part of the declaration that does not need the judge module."""
    import s1_common as S
    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    kw = dict(episodes=1000, eval_episodes=24, calibration_sha256="deadbeef")
    hashes = {}
    for name in ("D0", "D3-T0", "D2-T0-tau0p3", "MODQN-eq16", "D3-null", "D3-XEP"):
        for k in (0, 1, 2):
            p = S.cell_config_payload(record, CALIB, V1, name, k,
                                      optional=("D3-null", "D3-XEP"), **kw)
            assert p["lane"] == cfs1.S1_LANE
            assert p["eval_at"] == [1000]
            assert p["seeds"]["train"] == 9_251_000 + k
            hashes[f"{name}:{k}"] = S.config_hash(p)
    assert len(set(hashes.values())) == len(hashes)
    xep = S.cell_config_payload(record, CALIB, V1, "D3-XEP", 0,
                                optional=("D3-XEP",), **kw)
    assert xep["dev_settings"]["xep_reference_sha256"] == SEALED_XEP_SHA256
    moved = dict(xep, dev_settings=dict(xep["dev_settings"],
                                        xep_reference_sha256="f" * 64))
    assert S.config_hash(xep) != S.config_hash(moved), \
        "the reference sha256 is not in the configuration hash"
    null0 = S.cell_config_payload(record, CALIB, V1, "D3-null", 0,
                                  optional=("D3-null",), **kw)
    assert null0["dev_settings"]["null_key"] == (9_261_000, 0)
    # a preflight payload is a different configuration, always
    pre = S.cell_config_payload(record, CALIB, V1, "D3-T0", 0, lane=S.DEV_LANE,
                                **{**kw, "episodes": 2, "eval_episodes": 2})
    assert pre["lane"] == cfs1.DEV_LANE
    assert S.config_hash(pre) != hashes["D3-T0:0"]


def test_the_formal_set_is_opened_with_the_complete_matrix_or_not_at_all():
    """Amendment 13 section 7, as a pure function -- no process is ever started here.

    Red under: s1_partial_matrix_allowed.
    """
    import s1_common as S
    import s1_launch
    declared = list(S.specs(V1))
    s1_launch.assert_complete_matrix(declared, declared)
    for partial in (["D0:0"], ["FULL:0", "FULL:1", "FULL:2"], declared[:-1]):
        with pytest.raises(SystemExit):
            s1_launch.assert_complete_matrix(partial, declared)
    with pytest.raises(SystemExit):
        s1_launch.assert_complete_matrix(["D0:0", "D0:0"], declared)
    with pytest.raises(SystemExit):             # a cell of the other version
        s1_launch.assert_complete_matrix(declared + ["A-only-v2:0"], declared)
    s1_launch.assert_complete_matrix(["D0:0"], declared, dry_run=True)
    s1_launch.assert_complete_matrix(["D0:0"], declared, resuming=True)
    # a DEVELOPMENT-lane preflight may exercise a subset; a FORMAL declaration may not
    s1_launch.assert_complete_matrix(["D0:0"], declared, preflight=True)
    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    with pytest.raises(SystemExit):
        S.declared_manifest(record, CALIB, "deadbeef", mechanism_id=V1,
                            cell_names=("D0",),
                            reading_rules={"document": "x", "sha256": "f" * 64})
    # waves are not a partial matrix: the longest (judge) cells are scheduled first,
    # which changes wall time and nothing else
    assert s1_launch.launch_priority(S.cell(V1, "B-null"))[0] == 0
    assert s1_launch.launch_priority(S.cell(V1, "FULL"))[0] == 1
    assert s1_launch.launch_priority(S.cell(V1, "B-only"))[0] == 1
    assert s1_launch.launch_priority(S.cell(V1, "D0"))[0] == 2
    assert s1_launch.launch_priority(S.cell(V1, "MODQN-eq16"))[0] == 2


def test_the_s1_port_changed_no_development_identity():
    """The development lane is bit-identical: no field, no hash, no behaviour.

    This is the load-bearing test of the whole port: the MC2 development screen is
    launched from this same tree, so S1 may not move a single development
    configuration hash.
    """
    import dev_e0_common as D
    from mcrl.runtime import training_pipeline as tp
    assert tuple(f.name for f in dataclasses.fields(cfd.DevSettings)) == \
        DEV_SETTINGS_FIELDS, "the S1 port added a field to the DEVELOPMENT settings"
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    kw = dict(episodes=300, devval_episodes=24, calibration_sha256="deadbeef")
    for key, want in DEV_IDENTITY_GOLDEN.items():
        arm_s, k_s = key.split(":")
        arm, k = int(arm_s), int(k_s)
        extra = {}
        if arm in getattr(D, "MULTI_ARMS", {}):
            extra = ({"teachers": ("T0", "T_MINLOAD")}
                     if D.MULTI_ARMS[arm] == "FULL" else {"n_proposals": 2})
        got = D.config_hash(D.arm_config_payload(record, CALIB, arm, k, **kw, **extra))
        assert got == want, (
            f"development arm {key} hashes {got[:12]}, the base commit "
            f"{DEV_IDENTITY_BASE_COMMIT} produced {want[:12]}"
        )
