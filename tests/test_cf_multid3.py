"""LANE-M preflight: the generic N-teacher set-valued MULTI-D3 and its matched null.

Governing: ``.scratch/multi-catfish-v025-physics-successor/
V025-CONTROLLER-AMENDMENT-15-PARALLEL-CATFISH-PORTFOLIO-2026-09-12.md`` section 6
(the twelve required identities) and section 7 (what the mechanism is used for),
and Amendment 14 section 8 (the two-proposal matched-null semantics).

**Development lane, and no learner arm is launched by anything in this file.**  The
tests run tiny optimizer steps on DEV / DEVVAL seeds only; the formal evaluation,
calibration and CONFIRM namespaces are never constructed (``cf_dev.assert_dev_seed``
enforces that, and ``tests/test_cf_dev.py`` proves it).

Every test here was first run against a NAMED MUTANT and seen to FAIL
(``MULTI_MUTANT=<name> pytest tests/test_cf_multid3.py``), then against the real
code and seen to PASS.  The red/green table is in
``.scratch/catfish2-successor/LANE-M-MULTID3-2026-09-12.md``.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

from mcrl.algorithms import cf_dev as cfd
from mcrl.algorithms import cf_ratio as cfr
from mcrl.algorithms import cf_teacher as cft
from mcrl.env.step_types import ActionMask
from mcrl.errors import MCRLContractError
from mcrl.runtime.trainer_config_validation import TD_BOOTSTRAP_SHARED
from mcrl.runtime.trainer_spec import TrainerConfig

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
PINNED_LOCAL = Path("/home/u24/mcrl-runtime/tle-pinned-427e6a91")
MUTANT = os.environ.get("MULTI_MUTANT", "")
BASE_COMMIT = "27f69edf84eefeb8874339bc6c8c533469fa7f4b"
CALIB = {"eta0_bit_per_J": 110_507_234.83444457,
         "bits_scale": 13_329_082_278.45065,
         "joules_scale": 120.61728174105066}
NA = 28


# ------------------------------------------------------- test-only teacher sources
def _t_minload(states, masks) -> np.ndarray:
    """A second teacher that disagrees with T0 a lot: least-loaded legal beam.

    TEST ONLY.  It is not a candidate, it makes no claim, and it is registered only
    for the duration of this module -- the point is that MULTI-D3 is agnostic to
    what produced an action, so the tests need SOME second source and must not need
    a particular one.
    """
    out = np.zeros(len(states), dtype=np.int64)
    for u, s in enumerate(states):
        legal = np.flatnonzero(np.asarray(masks[u].mask, dtype=bool))
        if not legal.size:
            continue
        load = np.asarray(s.beam_loads, dtype=np.float64)[legal]
        out[u] = int(legal[int(np.argmin(load))])
    return out


def _t_echo_t0(states, masks) -> np.ndarray:
    """A second teacher that always duplicates T0 (the collapse case)."""
    return cft.t0_actions(states, masks)


def _t_lastlegal(states, masks) -> np.ndarray:
    out = np.zeros(len(states), dtype=np.int64)
    for u in range(len(states)):
        legal = np.flatnonzero(np.asarray(masks[u].mask, dtype=bool))
        if legal.size:
            out[u] = int(legal[-1])
    return out


@pytest.fixture(autouse=True, scope="module")
def _sources():
    cft.register_teacher_source("T_MINLOAD", _t_minload, replace=True)
    cft.register_teacher_source("T_ECHO_T0", _t_echo_t0, replace=True)
    cft.register_teacher_source("T_LASTLEGAL", _t_lastlegal, replace=True)
    yield
    for name in ("T_MINLOAD", "T_ECHO_T0", "T_LASTLEGAL"):
        cft.unregister_teacher_source(name)


# ---------------------------------------------------------------- mutants
@pytest.fixture(autouse=True)
def mutant(monkeypatch):
    """Named mutants of the MULTI-D3 implementation, applied with monkeypatch."""
    if MUTANT == "teacher_weights_reintroduced":
        # The thing Amendment 15 forbids in so many words: per-teacher weights.
        def bad(scores, mask, member, margin):
            total, n = 0.0, 0
            for a in range(member.shape[1]):
                rows = member[:, a]
                if not bool(rows.any()):
                    continue
                a_t = torch.full((scores.shape[0],), a, dtype=torch.long)
                total = total + cft.d3_margin_loss(
                    scores[rows], mask[rows], a_t[rows], margin
                ) * float(rows.sum())
                n += int(rows.sum())
            return total / max(n, 1)

        monkeypatch.setattr(cft, "d3_set_margin_loss", bad)
    elif MUTANT == "acf_summed_over_members":
        def bad(scores, mask, member, margin):
            total = None
            for a in range(member.shape[1]):
                rows = member[:, a]
                if not bool(rows.any()):
                    continue
                a_t = torch.full((int(rows.sum()),), a, dtype=torch.long)
                part = cft.d3_margin_loss(scores[rows], mask[rows], a_t, margin)
                total = part if total is None else total + part
            return total

        monkeypatch.setattr(cft, "d3_set_margin_loss", bad)
    elif MUTANT == "acf_cardinality_counts_duplicates":
        # A_CF reported as a multiset: the matched-null argument silently breaks.
        def bad(member, n_slots):
            return [0] * int(n_slots) + [int(np.asarray(member, bool).any(1).sum())]

        monkeypatch.setattr(cft, "cardinality_histogram", bad)
        monkeypatch.setattr(cft, "duplicate_slot_fraction", lambda slots, member: 0.0)
    elif MUTANT == "illegal_teacher_actions_admitted":
        real = cft.membership_from_slots

        def bad(slots, legal_mask):
            slots = np.asarray(slots, dtype=np.int64)
            member = np.zeros_like(np.asarray(legal_mask, dtype=bool))
            for u in range(slots.shape[0]):
                for a in slots[u]:
                    if int(a) != cft.EMPTY_SLOT:
                        member[u, int(a)] = True          # no legality filter
            return member

        monkeypatch.setattr(cft, "membership_from_slots", bad)
    elif MUTANT == "margin_applied_to_members":
        def bad(scores, mask, member, margin):
            marg = torch.full_like(scores, float(margin))   # never zeroed on A_CF
            q = (scores + marg).masked_fill(~mask, cft.MASK_FILL)
            best = scores.masked_fill(~member, cft.MASK_FILL).max(dim=1).values
            return (q.max(dim=1).values - best).mean()

        monkeypatch.setattr(cft, "d3_set_margin_loss", bad)
    elif MUTANT == "order_dependence_introduced":
        def bad(slots, legal_mask):
            slots = np.asarray(slots, dtype=np.int64)
            legal = np.asarray(legal_mask, dtype=bool)
            member = np.zeros_like(legal)
            for u in range(slots.shape[0]):
                for a in slots[u]:                       # LAST legal slot wins
                    if int(a) != cft.EMPTY_SLOT and legal[u, int(a)]:
                        member[u] = False
                        member[u, int(a)] = True
            return member

        monkeypatch.setattr(cft, "membership_from_slots", bad)
    elif MUTANT == "loss_admits_illegal_members":
        real = cft.d3_set_margin_loss

        def bad(scores, mask, member, margin):
            return real(scores, mask, member & mask, margin)   # silently clipped

        monkeypatch.setattr(cft, "d3_set_margin_loss", bad)
    elif MUTANT == "teacher_identity_dropped_from_hash":
        import dev_e0_common as D
        real = D.arm_config_payload

        def bad(*args, **kwargs):
            payload = real(*args, **kwargs)
            if payload.pop("multi_spec", None) is not None:     # multi arms only
                mech, credit = D.ARMS[int(payload["arm"])]
                payload["arm_name"] = f"E0-{payload['arm']}-{mech}-{credit}"
            return payload

        monkeypatch.setattr(D, "arm_config_payload", bad)
    elif MUTANT == "deployment_path_touched":
        def bad(self, encoded, masks):
            return cft.t0_actions(self._last_raw_states, masks)

        monkeypatch.setattr(cfd.CFDevTrainer, "greedy_actions", bad, raising=False)
    elif MUTANT == "null_drawn_with_replacement":
        def bad(mask, rng, n_proposals):
            mask = np.asarray(mask, dtype=bool)
            out = np.full((mask.shape[0], int(n_proposals)), cft.EMPTY_SLOT, np.int64)
            for u in range(mask.shape[0]):
                valid = np.flatnonzero(mask[u])
                if valid.size:
                    out[u] = rng.choice(valid, size=int(n_proposals), replace=True)
            return out

        monkeypatch.setattr(cft, "random_legal_action_slots", bad)
    elif MUTANT == "null_single_proposal":
        real = cft.random_legal_action_slots
        monkeypatch.setattr(
            cft, "random_legal_action_slots",
            lambda mask, rng, n_proposals: real(mask, rng, 1),
        )
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


def _full(*teachers) -> cfd.MultiD3Spec:
    return cfd.MultiD3Spec(teachers=cft.canonical_teacher_set(teachers))


def _null(n: int) -> cfd.MultiD3Spec:
    return cfd.MultiD3Spec(n_proposals=n, null_id=cft.MULTI_NULL_ID)


def _real_env_factory(users):
    if not PINNED_LOCAL.is_dir():
        pytest.skip("pinned local TLE archive not present")
    os.environ["MCRL_TLE_ROOT"] = str(PINNED_LOCAL)
    from mcrl.runtime.training_pipeline import make_training_environment
    return lambda: make_training_environment(users=users)


def _trainer(mechanism="D0", *, multi=None, users=6, cfg_kw=None, dev_kw=None):
    factory = _real_env_factory(users)
    return cfd.CFDevTrainer(
        factory(), _config(**(cfg_kw or {})), _settings(),
        _dev(mechanism, **(dev_kw or {})), multi=multi, env_factory=factory,
        train_seed=9_201_000, env_seed=9_202_000, mobility_seed=9_203_000,
    )


def _weights(tr):
    return [p.detach().clone() for net in tr.q_nets for p in net.parameters()]


def _weights_sha(tr) -> str:
    h = hashlib.sha256()
    for p in _weights(tr):
        h.update(p.numpy().tobytes())
    return h.hexdigest()


def _states(n=40, seed=0, n_legal=None):
    """Synthetic raw user states: only channel_quality / beam_loads are read."""
    rng = np.random.default_rng(seed)
    states, masks = [], []
    for _ in range(n):
        gain = rng.gamma(2.0, 3.0, size=NA)
        load = (rng.random(NA) < 0.4).astype(float) * rng.integers(1, 5, size=NA)
        k = n_legal if n_legal is not None else int(rng.integers(2, NA))
        legal = np.zeros(NA, dtype=bool)
        legal[rng.choice(NA, size=k, replace=False)] = True
        import types
        states.append(types.SimpleNamespace(channel_quality=gain, beam_loads=load))
        masks.append(ActionMask(mask=legal))
    return states, masks


def _score_batch(n, seed, *, min_legal=1):
    """Random scores / legal masks / a legal teacher action per row."""
    rng = np.random.default_rng(seed)
    scores = torch.tensor(rng.normal(size=(n, NA)), dtype=torch.float32)
    mask = torch.zeros(n, NA, dtype=torch.bool)
    a_t = torch.zeros(n, dtype=torch.long)
    for u in range(n):
        k = int(rng.integers(min_legal, NA + 1))
        idx = rng.choice(NA, size=k, replace=False)
        mask[u, idx] = True
        a_t[u] = int(rng.choice(idx))
    return scores, mask, a_t


def _one_hot(a_t, n_rows):
    member = torch.zeros(n_rows, NA, dtype=torch.bool)
    member[torch.arange(n_rows), a_t] = True
    return member


# ================================================================ 1 + 2: identity
def test_02_singleton_generic_loss_is_bit_identical_loss_and_gradient():
    """REQUIREMENT 2 -- the generic path with |A_CF| = 1 IS the frozen D3.

    Not "close": ``torch.equal`` on the loss tensor and on the gradient, over 400
    randomised rows at three margins including the frozen m = 0.15, plus a sha256
    receipt over every loss and gradient byte produced by both implementations.

    Red under: margin_applied_to_members, teacher_weights_reintroduced,
    acf_summed_over_members.
    """
    h_old, h_new = hashlib.sha256(), hashlib.sha256()
    checked = 0
    for seed in range(20):
        for margin in (0.15, 0.0, 0.7):
            scores, mask, a_t = _score_batch(20, 1000 + seed)
            s_old = scores.clone().requires_grad_(True)
            s_new = scores.clone().requires_grad_(True)
            member = _one_hot(a_t, scores.shape[0])
            l_old = cft.d3_margin_loss(s_old, mask, a_t, margin)
            l_new = cft.d3_set_margin_loss(s_new, mask, member, margin)
            assert torch.equal(l_old, l_new), (
                f"loss differs at seed {seed} margin {margin}: "
                f"{l_old.item()!r} vs {l_new.item()!r}"
            )
            l_old.backward()
            l_new.backward()
            assert torch.equal(s_old.grad, s_new.grad), "gradient differs"
            h_old.update(l_old.detach().numpy().tobytes())
            h_old.update(s_old.grad.numpy().tobytes())
            h_new.update(l_new.detach().numpy().tobytes())
            h_new.update(s_new.grad.numpy().tobytes())
            checked += 1
    assert checked == 60
    assert h_old.hexdigest() == h_new.hexdigest()
    print(f"\n[T2] loss+grad sha256 (both implementations) = {h_new.hexdigest()}")


def test_01_singleton_multi_arm_is_bit_identical_to_the_frozen_d3_t0():
    """REQUIREMENT 1 -- the ARM ``FULL{T0}`` IS the frozen ``D3-T0``.

    End to end on the real environment: same seeds, same frozen m = 0.15 and
    lambda_E = 1.0, two training episodes.  Every learner parameter must be equal
    bit for bit (a sha256 over all parameter bytes is printed as the receipt), the
    stored replay labels must be the same, and every episode-log field the two arms
    share must be equal.

    Red under: margin_applied_to_members, teacher_weights_reintroduced,
    acf_summed_over_members, order_dependence_introduced.
    """
    frozen = _trainer("D3-T0", users=6)
    logs_frozen = frozen.train_cf(progress_every=0)
    generic = _trainer("D3-multi", multi=_full("T0"), users=6)
    logs_generic = generic.train_cf(progress_every=0)

    sha_frozen, sha_generic = _weights_sha(frozen), _weights_sha(generic)
    for x, y in zip(_weights(frozen), _weights(generic)):
        assert torch.equal(x, y), "FULL{T0} moved the weights differently from D3-T0"
    assert sha_frozen == sha_generic
    print(f"\n[T1] parameter sha256 D3-T0 = {sha_frozen}\n"
          f"[T1] parameter sha256 FULL[T0] = {sha_generic}")

    lf, lg = list(frozen.replay._labels), list(generic.replay._labels)
    assert lf and len(lf) == len(lg)
    for (a0, a1, sc, mem_f), (b0, b1, sc2, mem_g) in zip(lf, lg):
        assert (a0, a1) == (b0, b1)
        np.testing.assert_array_equal(sc, sc2)
        assert mem_f is None and mem_g is not None
        assert int(mem_g.sum()) == 1 and bool(mem_g[b1])

    # every shared log field except the two that ARE the arm's label
    labels = {"mechanism", "teacher"}
    shared = (set(logs_frozen[0]) & set(logs_generic[0])) - labels
    assert {"losses", "teacher_loss", "bits", "joules", "served", "updates"} <= shared
    for a, b in zip(logs_frozen, logs_generic):
        for key in sorted(shared):
            assert a[key] == b[key], key
        assert (a["mechanism"], b["mechanism"]) == ("D3-T0", "D3-multi")
    assert all(r["multi_set_cardinality_hist"][1] == r["multi_set_rows"]
               for r in logs_generic)


# ================================================================ 3: order
def test_03_teacher_order_is_a_permutation_invariance():
    """REQUIREMENT 3 -- permuting the teacher list changes nothing.

    Structural, not incidental: A_CF is carried as a membership mask that does not
    record which slot set which bit, and the CANONICAL identity is sorted, so the
    two orders are literally the same configuration and the same hash.

    Red under: order_dependence_introduced.
    """
    states, masks = _states(60, seed=3)
    _, _, legal = cft.t0_scores(states, masks)
    names = ("T0", "T_MINLOAD", "T_LASTLEGAL")
    ref = None
    for order in ((0, 1, 2), (2, 1, 0), (1, 0, 2), (2, 0, 1)):
        picked = tuple(names[i] for i in order)
        slots = cft.teacher_action_slots(picked, states, masks)
        member = cft.membership_from_slots(slots, legal)
        if ref is None:
            ref = member
        else:
            np.testing.assert_array_equal(ref, member)
        assert cft.canonical_teacher_set(picked) == cft.canonical_teacher_set(names)

    scores, mask, _ = _score_batch(60, 33)
    losses = []
    for order in ((0, 1, 2), (2, 1, 0), (1, 0, 2)):
        picked = tuple(names[i] for i in order)
        m = cft.membership_from_slots(
            cft.teacher_action_slots(picked, states, masks), legal
        )
        t_mask = torch.tensor(legal, dtype=torch.bool)
        t_mem = torch.tensor(m, dtype=torch.bool)
        s = scores.clone().requires_grad_(True)
        loss = cft.d3_set_margin_loss(s, t_mask, t_mem, 0.15)
        loss.backward()
        losses.append((loss.detach().clone(), s.grad.clone()))
    for loss, grad in losses[1:]:
        assert torch.equal(loss, losses[0][0])
        assert torch.equal(grad, losses[0][1])


# ================================================================ 4: duplicates
def test_04_duplicate_teacher_actions_collapse_to_one_action():
    """REQUIREMENT 4 -- a repeated action is ONE member, and it is then the D3.

    ``T_ECHO_T0`` proposes exactly what T0 proposes, so ``|A_CF| = 1`` everywhere and
    ``FULL{T0,T_ECHO_T0}`` must be the single-teacher D3 bit for bit -- which is
    also the sharpest available test that no per-teacher weight survives anywhere
    (a mean or a sum over teachers would double-count the duplicate).

    Red under: acf_cardinality_counts_duplicates, teacher_weights_reintroduced,
    acf_summed_over_members, order_dependence_introduced.
    """
    states, masks = _states(80, seed=4)
    _, t0_acts, legal = cft.t0_scores(states, masks)
    slots = cft.teacher_action_slots(("T0", "T_ECHO_T0"), states, masks)
    member = cft.membership_from_slots(slots, legal)
    live = np.flatnonzero(legal.any(axis=1))
    assert live.size >= 60
    assert set(cft.set_cardinalities(member)[live]) == {1}
    hist = cft.cardinality_histogram(member, 2)
    assert hist[1] == live.size and hist[2] == 0
    assert cft.duplicate_slot_fraction(slots, member) == 1.0

    scores, mask, _ = _score_batch(80, 44)
    t_mask = torch.tensor(legal, dtype=torch.bool)
    keep = torch.tensor(legal.any(axis=1))
    s_set = scores[keep].clone().requires_grad_(True)
    s_one = scores[keep].clone().requires_grad_(True)
    a_t = torch.tensor(t0_acts[live], dtype=torch.long)
    l_set = cft.d3_set_margin_loss(
        s_set, t_mask[keep], torch.tensor(member[live], dtype=torch.bool), 0.15
    )
    l_one = cft.d3_margin_loss(s_one, t_mask[keep], a_t, 0.15)
    assert torch.equal(l_set, l_one), "a duplicated teacher changed the loss"
    l_set.backward()
    l_one.backward()
    assert torch.equal(s_set.grad, s_one.grad)


def test_there_are_no_teacher_weights_anywhere():
    """Amendment 15 section 6: 'No teacher weights -- no 0.5/0.5, none at all.'

    A hand-computed two-member case pins the value of the set formula, which no
    weighted combination of the two singleton D3 losses reproduces.

    Red under: teacher_weights_reintroduced, acf_summed_over_members,
    margin_applied_to_members, order_dependence_introduced.
    """
    scores = torch.zeros(1, NA)
    mask = torch.zeros(1, NA, dtype=torch.bool)
    mask[0, [1, 4, 9, 20]] = True
    scores[0, 4], scores[0, 9], scores[0, 1], scores[0, 20] = 1.0, 0.8, 0.95, 0.2
    scores[0, 27] = 99.0                                     # illegal: never counted
    member = torch.zeros(1, NA, dtype=torch.bool)
    member[0, [4, 9]] = True                                 # A_CF = {4, 9}
    # max over legal of S + 0.15*1(a not in A_CF) = max(1.0, 0.8, 0.95+0.15, 0.2+0.15)
    # minus max over A_CF of S = 1.0   ->   1.10 - 1.00 = 0.10
    loss = float(cft.d3_set_margin_loss(scores, mask, member, 0.15))
    assert loss == pytest.approx(0.10, rel=1e-6)
    one_4 = float(cft.d3_margin_loss(scores, mask, torch.tensor([4]), 0.15))
    one_9 = float(cft.d3_margin_loss(scores, mask, torch.tensor([9]), 0.15))
    assert loss != pytest.approx(0.5 * one_4 + 0.5 * one_9, rel=1e-3)
    assert loss != pytest.approx(one_4 + one_9, rel=1e-3)
    assert loss < min(one_4, one_9) + 1e-9, "the set must be easier than either alone"
    # a member already winning by the margin -> exactly zero, whatever the other is
    scores[0, 4] = 3.0
    assert float(cft.d3_set_margin_loss(scores, mask, member, 0.15)) == 0.0


# ================================================================ 5 + 6: legality
def test_05_only_currently_legal_teacher_actions_enter_a_cf():
    """REQUIREMENT 5 -- an illegal proposal is dropped from A_CF, never admitted.

    Red under: illegal_teacher_actions_admitted.
    """
    legal = np.zeros((4, NA), dtype=bool)
    legal[0, [3, 7]] = True
    legal[1, [11]] = True
    legal[2, [0, 1, 2]] = True
    # row 3 has NO legal action at all
    slots = np.array([[3, 5], [11, 12], [1, 1], [4, 6]], dtype=np.int64)
    member = cft.membership_from_slots(slots, legal)
    assert list(np.flatnonzero(member[0])) == [3]        # 5 is illegal, dropped
    assert list(np.flatnonzero(member[1])) == [11]       # 12 is illegal, dropped
    assert list(np.flatnonzero(member[2])) == [1]        # duplicate collapsed
    assert not member[3].any()                           # no legal action: empty row
    assert not bool((member & ~legal).any())

    # every teacher illegal in a state that HAS legal actions is a contract error
    with pytest.raises(MCRLContractError):
        cft.membership_from_slots(np.array([[5, 6]], dtype=np.int64), legal[:1])
    with pytest.raises(MCRLContractError):
        cft.membership_from_slots(np.array([[NA + 4]], dtype=np.int64), legal[:1])

    # and it holds through the real teacher sources on real masks
    states, masks = _states(50, seed=5)
    _, _, real_legal = cft.t0_scores(states, masks)
    m = cft.membership_from_slots(
        cft.teacher_action_slots(("T0", "T_MINLOAD"), states, masks), real_legal
    )
    assert not bool((m & ~real_legal).any())


def test_06_an_illegal_action_can_never_become_a_target():
    """REQUIREMENT 6 -- the loss refuses an illegal member and never gradients one.

    Three independent gates: the loss raises, the replay refuses to store it, and
    the gradient at every illegal column is exactly zero.

    Red under: illegal_teacher_actions_admitted, margin_applied_to_members.
    """
    scores = torch.randn(3, NA, requires_grad=True)
    mask = torch.zeros(3, NA, dtype=torch.bool)
    mask[:, [2, 5, 8]] = True
    good = torch.zeros(3, NA, dtype=torch.bool)
    good[:, 5] = True
    bad = good.clone()
    bad[1, 17] = True                                     # 17 is illegal
    with pytest.raises(MCRLContractError):
        cft.d3_set_margin_loss(scores, mask, bad, 0.15)
    with pytest.raises(MCRLContractError):
        cft.d3_set_margin_loss(scores, mask, torch.zeros_like(good), 0.15)

    loss = cft.d3_set_margin_loss(scores, mask, good, 0.15)
    loss.backward()
    illegal = ~mask
    assert float(scores.grad[illegal].abs().max()) == 0.0

    buf = cfd.TeacherReplayBuffer(4)
    kw = dict(t0_action=5, teacher_action=5, teacher_scores=np.zeros(NA))
    row = np.zeros(NA, dtype=bool)
    row[17] = True
    with pytest.raises(MCRLContractError):
        buf.push_labeled(np.zeros(113, np.float32), 5, np.zeros(3),
                         np.zeros(113, np.float32), mask[0].numpy(),
                         mask[0].numpy(), False, teacher_member=row, **kw)
    with pytest.raises(MCRLContractError):
        buf.push_labeled(np.zeros(113, np.float32), 5, np.zeros(3),
                         np.zeros(113, np.float32), mask[0].numpy(),
                         mask[0].numpy(), False,
                         teacher_member=np.zeros(NA, bool), **kw)


# ================================================================ 7: ties
def test_07_tie_behaviour_is_deterministic_first_index():
    """REQUIREMENT 7 -- exact ties resolve to the FIRST index, reproducibly.

    Both reductions are ``torch.max(dim=1)``, whose CPU tie rule is the first
    maximal index -- the same convention as ``np.argmax`` in the frozen T0 rule and
    in ``masked_argmax_rows``.  Checked on both the outer max and the max over A_CF,
    on the value, on the index and on where the gradient lands.
    """
    mask = torch.zeros(1, NA, dtype=torch.bool)
    mask[0, [2, 6, 11, 19]] = True
    member = torch.zeros(1, NA, dtype=torch.bool)
    member[0, [6, 11]] = True                              # tied members
    scores = torch.zeros(1, NA)
    # a non-member wins the outer max, so the two tied members are separable
    scores[0, [2, 6, 11, 19]] = torch.tensor([1.5, 1.0, 1.0, 0.5])
    s = scores.clone().requires_grad_(True)
    loss = cft.d3_set_margin_loss(s, mask, member, 0.15)
    loss.backward()
    assert float(loss) == pytest.approx(1.65 - 1.0, rel=1e-6)
    assert float(s.grad[0, 2]) > 0.0
    assert float(s.grad[0, 6]) < 0.0, "the tie must resolve to the FIRST member"
    assert float(s.grad[0, 11]) == 0.0
    # outer max tied between two non-members
    scores2 = torch.zeros(1, NA)
    scores2[0, [2, 6, 11, 19]] = torch.tensor([1.0, 0.4, 0.4, 1.0])
    idx = ((scores2 + torch.where(member, 0.0, 0.15))
           .masked_fill(~mask, cft.MASK_FILL)).max(dim=1).indices
    assert int(idx[0]) == 2
    # and it is stable across repeats and across a permuted teacher list
    vals = [float(cft.d3_set_margin_loss(scores.clone(), mask, member, 0.15))
            for _ in range(5)]
    assert len(set(vals)) == 1
    assert cft.masked_argmax_rows(member.numpy().astype(float), mask.numpy())[0] == 6


# ================================================================ 8: disabled path
def test_08_a_disabled_multi_path_reproduces_the_frozen_control():
    """REQUIREMENT 8 -- lambda_E = 0 on a MULTI-D3 arm IS D0, bit for bit.

    And the mere presence of the multi code changes no frozen arm: arms 1-7 hash to
    exactly what the base commit's ``dev_e0_common.py`` produced.
    """
    d0 = _trainer("D0", users=6)
    logs0 = d0.train_cf(progress_every=0)
    for spec, mech in ((_full("T0", "T_MINLOAD"), "D3-multi"),
                       (_null(2), "D3-multi-null")):
        off = _trainer(mech, multi=spec, users=6, dev_kw={"lambda_e": 0.0})
        logs = off.train_cf(progress_every=0)
        for x, y in zip(_weights(d0), _weights(off)):
            assert torch.equal(x, y), f"{mech} at zero weight moved the weights"
        for a, b in zip(logs0, logs):
            assert a["bits"] == b["bits"] and a["losses"] == b["losses"]
            assert a["updates"] == b["updates"]

    import dev_e0_common as D
    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    kw = dict(episodes=300, devval_episodes=24, calibration_sha256="deadbeef")
    old_src = subprocess.run(
        ["git", "show", f"{BASE_COMMIT}:scripts/dev_e0_common.py"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout
    ns: dict = {"__name__": "dev_e0_common_base", "__file__": str(REPO / "scripts/x.py")}
    exec(compile(old_src, "<base dev_e0_common>", "exec"), ns)   # noqa: S102
    for arm in (1, 2, 3, 4, 5, 6, 7):
        for k in (0, 1):
            new = D.config_hash(D.arm_config_payload(record, CALIB, arm, k, **kw))
            old = ns["config_hash"](ns["arm_config_payload"](record, CALIB, arm, k, **kw))
            assert new == old, f"MULTI-D3 changed the frozen arm {arm} k{k} config hash"


# ================================================================ 9: config hash
def test_09_config_hash_covers_teacher_mechanism_and_null_identity():
    """REQUIREMENT 9 -- canonical teacher identities, mechanism id, null id.

    Red under: teacher_identity_dropped_from_hash.
    """
    import dev_e0_common as D
    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    kw = dict(episodes=100, devval_episodes=24, calibration_sha256="deadbeef")

    def h(arm, k, **extra):
        return D.config_hash(D.arm_config_payload(record, CALIB, arm, k, **kw, **extra))

    p = D.arm_config_payload(record, CALIB, 8, 8, **kw, teachers=("T_DELTA", "T0"))
    assert p["multi_spec"]["mechanism_id"] == cft.MULTI_MECHANISM_ID
    assert tuple(p["multi_spec"]["teachers"]) == ("T0", "T_DELTA")     # canonical
    assert p["multi_spec"]["null_id"] is None
    assert p["dev_settings"]["mechanism"] == "D3-multi"
    assert p["dev_settings"]["teacher"] == "multi"
    assert p["arm_name"] == "E0-8-D3-multi-T0+T_DELTA-equal_share"

    q = D.arm_config_payload(record, CALIB, 9, 8, **kw, n_proposals=2)
    assert q["multi_spec"]["null_id"] == cft.MULTI_NULL_ID
    assert q["multi_spec"]["n_proposals"] == 2
    assert tuple(q["multi_spec"]["teachers"]) == ()
    assert tuple(q["dev_settings"]["null_key"]) == (9_241_000, 8)
    assert q["arm_name"] == "E0-9-D3-multi-null-n2-equal_share"

    # teacher IDENTITY is in the hash; teacher ORDER is not
    assert h(8, 8, teachers=("T0", "T_DELTA")) == h(8, 8, teachers=("T_DELTA", "T0"))
    assert h(8, 8, teachers=("T0", "T_DELTA")) != h(8, 8, teachers=("T0", "T_NEXT"))
    assert h(8, 8, teachers=("T0",)) != h(8, 8, teachers=("T0", "T_DELTA"))
    # mechanism identity and null identity are in the hash
    assert h(8, 8, teachers=("T0",)) != h(4, 8)                    # vs frozen D3-T0
    assert h(9, 8, n_proposals=2) != h(7, 8)                       # vs one-action null
    assert h(9, 8, n_proposals=2) != h(9, 8, n_proposals=3)
    assert h(9, 8, n_proposals=2) != h(9, 9, n_proposals=2)        # DEV-NULL key
    # the matched null is matched to a CARDINALITY: one run, shared by candidates
    assert D.spec_key(9, 8, n_proposals=2) == "9:8:n2"
    assert D.spec_key(8, 8, ("T_DELTA", "T0")) == "8:8:T0+T_DELTA"
    assert D.spec_key(4, 8) == "4:8"

    # a non-canonical or unversioned spec is refused outright
    with pytest.raises(MCRLContractError):
        cfd.MultiD3Spec(teachers=("T_DELTA", "T0"))
    with pytest.raises(MCRLContractError):
        cfd.MultiD3Spec(teachers=("T0", "T0"))
    with pytest.raises(MCRLContractError):
        cfd.MultiD3Spec(mechanism_id="something-else", teachers=("T0",))
    with pytest.raises(MCRLContractError):
        cfd.MultiD3Spec(n_proposals=2, null_id="hand-rolled")
    with pytest.raises(MCRLContractError):
        cfd.MultiD3Spec(teachers=("T0",), n_proposals=2, null_id=cft.MULTI_NULL_ID)
    with pytest.raises(MCRLContractError):
        cfd.DevSettings(mechanism="D3-multi", teacher="T0")
    with pytest.raises(MCRLContractError):
        _trainer("D3-multi", multi=None, users=6)
    with pytest.raises(MCRLContractError):
        _trainer("D3-T0", multi=_full("T0"), users=6)


# ================================================================ 10: resume
def test_10_resume_and_stop_are_deterministic():
    """REQUIREMENT 10 -- stop at an episode boundary, resume, land bit-identically.

    Both MULTI-D3 arms, including the null's DEV-NULL generator state.  A resume
    whose MultiD3Spec differs is refused rather than silently accepted.
    """
    for mech, spec in (("D3-multi", _full("T0", "T_MINLOAD")),
                       ("D3-multi-null", _null(2))):
        full = _trainer(mech, multi=spec, users=6, cfg_kw={"episodes": 3})
        logs_full = full.train_cf(progress_every=0)
        part = _trainer(mech, multi=spec, users=6, cfg_kw={"episodes": 3})
        part.config = dataclasses.replace(part.config, episodes=1)
        logs_a = part.train_cf(progress_every=0)
        state = copy.deepcopy(part.training_state_dict())
        fresh = _trainer(mech, multi=spec, users=6, cfg_kw={"episodes": 3})
        fresh.config = dataclasses.replace(fresh.config, episodes=1)
        fresh.load_training_state_dict(state)
        fresh.config = dataclasses.replace(fresh.config, episodes=3)
        logs = fresh.train_cf(start_episode=1, initial_logs=logs_a, progress_every=0)
        assert [r["episode"] for r in logs] == [0, 1, 2]
        for x, y in zip(_weights(full), _weights(fresh)):
            assert torch.equal(x, y), f"{mech} resume is not bit-identical"
        assert _weights_sha(full) == _weights_sha(fresh)
        assert [r["losses"] for r in logs] == [r["losses"] for r in logs_full]
        assert [r["teacher_loss"] for r in logs] == [r["teacher_loss"] for r in logs_full]
        assert ([r["multi_set_cardinality_hist"] for r in logs]
                == [r["multi_set_cardinality_hist"] for r in logs_full])
        other = _trainer(mech, multi=(_full("T0") if mech == "D3-multi" else _null(3)),
                         users=6, cfg_kw={"episodes": 3})
        with pytest.raises(MCRLContractError):
            other.load_training_state_dict(state)


# ================================================================ 11 + 12: deploy
def test_11_the_multi_code_changes_no_inference_or_deployment_path():
    """REQUIREMENT 11 -- nothing that acts at inference time was touched.

    Three receipts: the deployed learner files are byte-identical to the base
    commit; the acting methods are the INHERITED ones (same function objects); and
    two trainers with the same weights but different mechanisms choose the same
    greedy actions on the same observations.

    Red under: deployment_path_touched.
    """
    for f in ("src/mcrl/algorithms/cf_ratio.py", "src/mcrl/algorithms/modqn.py",
              "src/mcrl/algorithms/cf_credit.py"):
        base = subprocess.run(["git", "show", f"{BASE_COMMIT}:{f}"], cwd=REPO,
                              capture_output=True, check=True).stdout
        now = (REPO / f).read_bytes()
        assert hashlib.sha256(base).hexdigest() == hashlib.sha256(now).hexdigest(), f

    for name in ("greedy_actions", "select_actions", "encode_at", "save_policy"):
        assert getattr(cfd.CFDevTrainer, name) is getattr(cfr.CFRatioTrainer, name), (
            f"CFDevTrainer overrides the inference method {name}"
        )

    frozen = _trainer("D3-T0", users=6)
    multi = _trainer("D3-multi", multi=_full("T0", "T_MINLOAD"), users=6)
    for net_a, net_b in zip(multi.q_nets, frozen.q_nets):
        net_b.load_state_dict(net_a.state_dict())
    multi.eta, frozen.eta = 3.0, 3.0
    factory = _real_env_factory(6)
    env = factory()
    states, masks, _ = env.reset(np.random.default_rng(9_202_000),
                                 np.random.default_rng(9_203_000))
    enc = multi.encode_at(states, 0)
    np.testing.assert_array_equal(multi.greedy_actions(enc, masks),
                                  frozen.greedy_actions(enc, masks))


def test_12_no_teacher_is_required_at_deployment(tmp_path):
    """REQUIREMENT 12 -- a trained MULTI-D3 policy runs with NO teacher present.

    The checkpoint is saved from a two-teacher arm, then every teacher source is
    unregistered and ``cft.t0_scores`` is made to raise; the policy must still load
    and act.  A teacher exists only inside the training loop.

    Red under: deployment_path_touched.
    """
    multi = _trainer("D3-multi", multi=_full("T0", "T_MINLOAD"), users=6)
    multi.train_cf(progress_every=0)
    path = tmp_path / "policy.pt"
    multi.save_policy(path, 1)
    payload = torch.load(path, map_location="cpu", weights_only=False)
    assert payload["multi_spec"]["teachers"] == ("T0", "T_MINLOAD")
    assert set(payload) >= {"q_networks", "target_networks", "eta"}

    factory = _real_env_factory(6)
    deployed = cfd.CFDevTrainer(factory(), _config(), _settings(), _dev("D0"),
                                env_factory=factory, train_seed=9_201_000,
                                env_seed=9_202_000, mobility_seed=9_203_000)
    saved = dict(cft._TEACHER_SOURCES)
    real_t0 = cft.t0_scores
    try:
        cft._TEACHER_SOURCES.clear()

        def no_teacher(*args, **kwargs):
            raise AssertionError("the deployment path asked a teacher for an action")

        cft.t0_scores = no_teacher
        cft.t0_actions = no_teacher
        deployed.load_policy(path)
        env = factory()
        states, masks, _ = env.reset(np.random.default_rng(9_211_000),
                                     np.random.default_rng(9_212_000))
        enc = deployed.encode_at(states, 0)
        acts = deployed.greedy_actions(enc, masks)
        assert len(acts) == 6
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


# ================================================================ the matched null
def test_the_matched_null_is_a_two_proposal_distinct_legal_set():
    """Amendment 14 section 8 / Amendment 15 section 6: the null's own semantics.

    Two DISTINCT legal actions without replacement when at least two exist,
    cardinality one when only one does; drawn from the arm's own declared DEV-NULL
    stream and from nothing else; reproducible from that identity alone.

    Red under: null_drawn_with_replacement, null_single_proposal.
    """
    legal = np.zeros((300, NA), dtype=bool)
    for u in range(300):
        if u % 10 == 0:
            legal[u, u % NA] = True                       # exactly one legal action
        else:
            legal[u, [u % NA, (u + 5) % NA, (u + 11) % NA]] = True
    rng = np.random.default_rng((9_241_000, 8))
    slots = cft.random_legal_action_slots(legal, rng, 2)
    member = cft.membership_from_slots(slots, legal)
    card = cft.set_cardinalities(member)
    for u in range(300):
        drawn = [int(x) for x in slots[u] if int(x) != cft.EMPTY_SLOT]
        assert all(bool(legal[u, a]) for a in drawn), "an illegal null proposal"
        assert len(set(drawn)) == len(drawn), "the null drew the same action twice"
        assert card[u] == (1 if int(legal[u].sum()) == 1 else 2)

    same = cft.random_legal_action_slots(legal, np.random.default_rng((9_241_000, 8)), 2)
    other = cft.random_legal_action_slots(legal, np.random.default_rng((9_241_000, 9)), 2)
    np.testing.assert_array_equal(slots, same)
    assert not np.array_equal(slots, other)

    # the draw reads no teacher: multiplying T0's scores cannot move it
    states, masks = _states(40, seed=12)
    a = _trainer("D3-multi-null", multi=_null(2), users=6)
    b = _trainer("D3-multi-null", multi=_null(2), users=6)
    m1 = a.teacher_labels_ext(states, masks)[5]
    real = cft.t0_scores
    try:
        cft.t0_scores = lambda st, mk, c=cft.T0_C: (
            (lambda s, ac, lg: (s * -7.0, ac, lg))(*real(st, mk, c))
        )
        m2 = b.teacher_labels_ext(states, masks)[5]
    finally:
        cft.t0_scores = real
    np.testing.assert_array_equal(m1, m2)
    assert np.all(a.teacher_labels_ext(states, masks)[2] == 0.0), "the null carries T0"


def cardinality_mismatch(full_member, null_member, n_slots) -> list[tuple[int, float]]:
    """The launcher's pre-k=8 gate: |A_CF| histogram of FULL vs its null.

    Returns the cardinalities whose share differs by more than 2 pp, with the
    difference.  Run it on the frozen P0 collection once the real candidate ``T_i``
    exists and BEFORE any learner arm starts; hand a non-empty result to the
    controller rather than proceeding.
    """
    a = cft.cardinality_histogram(full_member, n_slots)
    b = cft.cardinality_histogram(null_member, n_slots)
    n_a, n_b = max(sum(a[1:]), 1), max(sum(b[1:]), 1)
    out = []
    for c in range(1, int(n_slots) + 1):
        d = a[c] / n_a - b[c] / n_b
        if abs(d) > 0.02:
            out.append((c, float(d)))
    return out


def test_the_null_cardinality_distribution_vs_the_full_arms():
    """Amendment 15 section 6: is the declared 2-null cardinality-MATCHED?

    Measured here, prospectively, before any learner outcome exists.  **The answer is
    that it is matched only when the teachers NEVER agree**, because
    ``|A_CF|(FULL) = 2 - 1(the teachers named the same action)`` while
    ``|A_CF|(null) = min(2, n_legal)``.  Amendment 15 section 5 only requires
    disagreement >= 0.25, so a candidate may agree with T0 on up to 75 % of states
    and the declared null would then be a set of size two against a FULL arm that is
    a set of size one three-quarters of the time.

    The test therefore asserts the STRUCTURE (which is what a launcher can check
    before k = 8) rather than a match that does not hold, and shows that
    :func:`cardinality_mismatch` sees the defect.  The remedy is implemented and NOT
    selected: :data:`cft.MULTI_NULL_BERNOULLI_ID`, exercised below.

    Red under: null_single_proposal, null_drawn_with_replacement,
    acf_cardinality_counts_duplicates.
    """
    states, masks = _states(400, seed=7)
    _, _, legal = cft.t0_scores(states, masks)
    assert int((legal.sum(axis=1) >= 2).sum()) == 400          # every state, >= 2 legal

    def null_member(p=None, k=8):
        return cft.membership_from_slots(
            cft.random_legal_action_slots(
                legal, np.random.default_rng((9_241_000, k)), 2, p_singleton=p
            ), legal)

    def full_member(*teachers):
        return cft.membership_from_slots(
            cft.teacher_action_slots(teachers, states, masks), legal)

    declared = null_member()
    null_hist = cft.cardinality_histogram(declared, 2)
    print(f"\n[NULL] declared 2-null        |A_CF| hist = {null_hist}")
    # STRUCTURE of the declared null: always min(2, n_legal) = 2 here
    assert null_hist == [0, 0, 400]

    for pair in (("T0", "T_LASTLEGAL"), ("T0", "T_MINLOAD"), ("T0", "T_ECHO_T0")):
        m = full_member(*pair)
        hist = cft.cardinality_histogram(m, 2)
        collapse = hist[1] / sum(hist[1:])
        gap = cardinality_mismatch(m, declared, 2)
        print(f"[NULL] FULL{set(pair)} |A_CF| hist = {hist} "
              f"collapse={collapse:.4f} mismatch={gap}")
        # STRUCTURE of a FULL arm: cardinality 1 exactly on the agreement rows
        agree = int((cft.teacher_action_slots(pair, states, masks)[:, 0]
                     == cft.teacher_action_slots(pair, states, masks)[:, 1]).sum())
        assert hist[1] == agree and hist[1] + hist[2] == 400
        # ... and the gate SEES the mismatch whenever they ever agree
        assert bool(gap) == (collapse > 0.02), (pair, hist, gap)

    # the NOT-SELECTED remedy: declare p_singleton = the measured collapse rate and
    # the cardinality distributions line up.
    m = full_member("T0", "T_LASTLEGAL")
    p = cft.cardinality_histogram(m, 2)[1] / 400
    matched = null_member(p=p)
    assert cardinality_mismatch(m, matched, 2) == [], (
        cft.cardinality_histogram(m, 2), cft.cardinality_histogram(matched, 2)
    )
    print(f"[NULL] Bernoulli-matched null (p_singleton={p:.4f}) |A_CF| hist = "
          f"{cft.cardinality_histogram(matched, 2)}  -> matched")
    # it is a DIFFERENT declared identity with a different stream and hash
    assert not np.array_equal(declared, matched)
    num = cft.cardinality_histogram(m, 2)[1]
    prov = dict(p_singleton=p, p_singleton_numerator=num,
                p_singleton_denominator=400,
                p_singleton_rational=f"{num}/400",
                p_singleton_source="TEST:T_LASTLEGAL@synthetic")
    spec = cfd.MultiD3Spec(n_proposals=2, null_id=cft.MULTI_NULL_BERNOULLI_ID, **prov)
    assert spec.is_null and spec.n_slots == 2 and spec.is_bernoulli_null
    with pytest.raises(MCRLContractError):
        cfd.MultiD3Spec(n_proposals=2, null_id=cft.MULTI_NULL_ID, **prov)
    with pytest.raises(MCRLContractError):
        cfd.MultiD3Spec(n_proposals=2, null_id=cft.MULTI_NULL_BERNOULLI_ID)
    # the registered arm 9 is still the DECLARED two-proposal null, unchanged
    import dev_e0_common as D
    assert D.multi_spec(9, n_proposals=2).null_id == cft.MULTI_NULL_ID
    assert D.multi_spec(9, n_proposals=2).p_singleton is None
    assert D.MATCHED_NULL_ARM == {4: 7, 8: 9}, "the FULL arm's null is 9, never 7"


# ============================= k = 8 integration (controller record 716f104e)
def test_13_the_teacher_context_seam_is_training_only_and_additive():
    """716f104e section 7 -- the seam adds a training-only read and nothing else.

    A source that does not ask for the context is called exactly as before, the
    seam is not even constructed for such an arm, and registering a
    context-needing source changes no existing arm's behaviour or configuration.
    """
    from mcrl.algorithms import cf_multi_sources as cfmulti

    # the frozen environment wrapper is untouched
    for f in ("src/mcrl/runtime/trainer_env.py", "src/mcrl/algorithms/cf_ratio.py"):
        base = subprocess.run(["git", "show", f"{BASE_COMMIT}:{f}"], cwd=REPO,
                              capture_output=True, check=True).stdout
        assert hashlib.sha256(base).hexdigest() == hashlib.sha256(
            (REPO / f).read_bytes()).hexdigest(), f

    assert not cft.teacher_needs_context("T0")
    assert not cft.any_teacher_needs_context(("T0", "T_MINLOAD"))
    cfmulti.register_candidate_sources(replace=True)
    try:
        assert cft.teacher_needs_context(cfmulti.T_NEXT_ID)
        assert cft.any_teacher_needs_context(("T0", cfmulti.T_NEXT_ID))
        # a context-needing source refuses to run without the context, loudly
        states, masks = _states(4, seed=13)
        with pytest.raises(MCRLContractError):
            cft.teacher_action_slots((cfmulti.T_NEXT_ID,), states, masks)
        # ... and a context-free source is unaffected by the context being there
        a = cft.teacher_action_slots(("T0",), states, masks)
        b = cft.teacher_action_slots(("T0",), states, masks,
                                     context=cft.TeacherContext(None, None, 0, False))
        np.testing.assert_array_equal(a, b)

        # the seam is not even built for arms whose teachers do not ask for it
        for mech, multi in (("D0", None), ("D3-T0", None), ("D3-null", None),
                            ("D3-multi", _full("T0")),
                            ("D3-multi", _full("T0", "T_MINLOAD")),
                            ("D3-multi-null", _null(2))):
            tr = _trainer(mech, multi=multi, users=6)
            assert tr._needs_teacher_context is False, mech
        assert _trainer("D3-multi", multi=_full("T0", cfmulti.T_NEXT_ID),
                        users=6)._needs_teacher_context is True

        # registering the source changes no existing arm, behaviourally or in hash
        with_src = _trainer("D3-T0", users=6)
        with_src.train_cf(progress_every=0)
        sha_with = _weights_sha(with_src)
    finally:
        cft.unregister_teacher_source(cfmulti.T_NEXT_ID)
    without = _trainer("D3-T0", users=6)
    without.train_cf(progress_every=0)
    assert sha_with == _weights_sha(without), (
        "registering a context-needing source moved an existing arm's learner"
    )


def test_14_tnext_singleton_and_full_are_distinct_generic_configurations():
    """716f104e section 5 -- ``T_NEXT-only`` is the GENERIC singleton, not a new
    mechanism, and it is a different run from ``FULL{T0, T_NEXT}``."""
    import dev_e0_common as D
    from mcrl.algorithms import cf_multi_sources as cfmulti
    from mcrl.runtime import training_pipeline as tp
    cfmulti.register_candidate_sources(replace=True)
    try:
        record = tp.read_prereg(tp.CANONICAL_PREREG)
        kw = dict(episodes=300, devval_episodes=24, calibration_sha256="deadbeef")
        solo = D.arm_config_payload(record, CALIB, 8, 8, **kw, teachers=("T_NEXT",))
        full = D.arm_config_payload(record, CALIB, 8, 8, **kw,
                                    teachers=("T0", "T_NEXT"))
        assert solo["mechanism"] == full["mechanism"] == "D3-multi"
        assert "D3-T_NEXT" not in cft.MECHANISMS, "a redundant mechanism was invented"
        assert D.config_hash(solo) != D.config_hash(full)
        assert D.spec_key(8, 8, ("T_NEXT",)) == "8:8:T_NEXT"
        assert D.spec_key(8, 8, ("T_NEXT", "T0")) == "8:8:T0+T_NEXT"
        assert D.arm_name(8, ("T_NEXT",)) != D.arm_name(8, ("T0", "T_NEXT"))
        # the committed source's own identity is in both hashes
        for p in (solo, full):
            ident = p["multi_source_identities"]["T_NEXT"]
            assert ident["source_id"] == "T_NEXT"
            assert ident["source_version"] == "assoc-persistence-lookahead-v1"
        # and it is the committed Lane N file, not a reconstruction
        from mcrl.algorithms import cf_tnext as cftn
        assert cftn.SOURCE_ID == "T_NEXT"
        base = subprocess.run(
            ["git", "show", "25448632:src/mcrl/algorithms/cf_tnext.py"],
            cwd=REPO, capture_output=True, check=True).stdout
        assert hashlib.sha256(base).hexdigest() == hashlib.sha256(
            (REPO / "src/mcrl/algorithms/cf_tnext.py").read_bytes()).hexdigest()
    finally:
        cft.unregister_teacher_source(cfmulti.T_NEXT_ID)


def test_15_the_selected_bernoulli_null_identity_is_frozen_and_distinct():
    """716f104e sections 2 and 4 -- the SELECTED null, its exact ``p_singleton``,
    and no collision with the rejected fixed null."""
    import dev_e0_common as D
    from mcrl.algorithms import cf_multi_sources as cfmulti
    from mcrl.runtime import training_pipeline as tp
    cfmulti.register_candidate_sources(replace=True)
    try:
        assert (D.P_SINGLETON_TNEXT_NUM, D.P_SINGLETON_TNEXT_DEN) == (9395, 24000)
        assert D.P_SINGLETON_TNEXT == 9395 / 24000 == 0.39145833333333335
        spec = D.multi_spec(9, n_proposals=2, bernoulli=True)
        assert spec.null_id == cft.MULTI_NULL_BERNOULLI_ID and spec.is_bernoulli_null
        assert spec.p_singleton_rational == "9395/24000"
        assert "T_NEXT" in spec.p_singleton_source
        assert D.P0_DATASET_SHA256 in spec.p_singleton_source
        assert spec.label() == "n2-bernoulli-p9395_24000"

        record = tp.read_prereg(tp.CANONICAL_PREREG)
        kw = dict(episodes=300, devval_episodes=24, calibration_sha256="deadbeef")
        sel = D.arm_config_payload(record, CALIB, 9, 8, **kw, n_proposals=2,
                                   bernoulli=True)
        old = D.arm_config_payload(record, CALIB, 9, 8, **kw, n_proposals=2)
        assert D.config_hash(sel) != D.config_hash(old), "null identity collision"
        assert sel["arm_name"] != old["arm_name"]
        assert D.spec_key(9, 8, n_proposals=2, bernoulli=True) != \
            D.spec_key(9, 8, n_proposals=2)
        assert sel["multi_spec"]["p_singleton"] == 9395 / 24000
        assert sel["multi_spec"]["p_singleton_numerator"] == 9395

        # a mis-stated rational, a float without provenance, or a bare id: refused
        for bad in (
            dict(p_singleton=0.5, p_singleton_numerator=9395,
                 p_singleton_denominator=24000, p_singleton_rational="9395/24000",
                 p_singleton_source="x"),
            dict(p_singleton=9395 / 24000, p_singleton_numerator=9395,
                 p_singleton_denominator=24000, p_singleton_rational="0.39",
                 p_singleton_source="x"),
            dict(p_singleton=9395 / 24000),
        ):
            with pytest.raises(MCRLContractError):
                cfd.MultiD3Spec(n_proposals=2,
                                null_id=cft.MULTI_NULL_BERNOULLI_ID, **bad)

        # the null reads no per-state agreement information: only its own stream
        legal = np.ones((300, NA), dtype=bool)
        s1 = cft.random_legal_action_slots(
            legal, np.random.default_rng((9_241_000, 8)), 2,
            p_singleton=D.P_SINGLETON_TNEXT)
        s2 = cft.random_legal_action_slots(
            legal, np.random.default_rng((9_241_000, 8)), 2,
            p_singleton=D.P_SINGLETON_TNEXT)
        np.testing.assert_array_equal(s1, s2)
        card = cft.set_cardinalities(cft.membership_from_slots(s1, legal))
        assert abs(float((card == 1).mean()) - D.P_SINGLETON_TNEXT) < 0.06
    finally:
        cft.unregister_teacher_source(cfmulti.T_NEXT_ID)


def test_16_the_k8_schedule_is_300_episodes_stop_after_100():
    """716f104e section 6 -- never ``--episodes 100``: the epsilon schedule is a
    function of the CONFIGURED budget, so shortening it changes the learner."""
    import dev_e0_common as D
    assert D.epsilon_decay_episodes(300) == 67
    assert D.epsilon_decay_episodes(100) == 22
    assert D.epsilon_decay_episodes(300) != D.epsilon_decay_episodes(100)
    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    cfg300 = D.e0_config(record, 300)
    assert cfg300.episodes == 300 and cfg300.epsilon_decay_episodes == 67
    assert D.devval_at(300) == (100, 200, 300)


# ================================================================ arm registration
def test_multi_arms_are_registered_and_parameterised():
    """The runner can select the two arms by identity, over any teacher set.

    Registration only: nothing here launches anything.
    """
    import dev_e0_common as D
    assert D.ARMS[8] == ("D3-multi", "equal_share")
    assert D.ARMS[9] == ("D3-multi-null", "equal_share")
    assert D.MULTI_ARMS == {8: "FULL", 9: "NULL"}
    for teachers in (("T0", "T_DELTA"), ("T0", "T_NEXT"), ("T0", "T_TAIL"),
                     ("T0",), ("T0", "T_NEXT", "T_TAIL")):
        spec = D.multi_spec(8, teachers)
        assert spec.teachers == cft.canonical_teacher_set(teachers)
        assert spec.n_slots == len(teachers)
        assert D.arm_name(8, teachers).startswith("E0-8-D3-multi-")
    assert D.multi_spec(9, n_proposals=2).n_slots == 2
    assert D.multi_spec(9, ("T0", "T_DELTA")).n_proposals == 2
    assert D.multi_spec(4) is None
    with pytest.raises(SystemExit):
        D.multi_spec(4, ("T0",))
    with pytest.raises(SystemExit):
        D.multi_spec(8)
    # the driver still refuses to run without a matching RUN-MANIFEST (fail closed)
    r = subprocess.run(
        [sys.executable, "scripts/run_dev_e0.py", "--arm", "8", "--seed-index", "8",
         "--teachers", "T0+T_DELTA", "--root", "/nonexistent-lane-m",
         "--calibration", "/nonexistent-lane-m/calib.json"],
        cwd=REPO, capture_output=True, text=True,
        env=dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                 OPENBLAS_NUM_THREADS="1"),
    )
    assert r.returncode != 0
