"""The S1 FORMAL screen's learner surface: lane-aware settings, and ``T0-XEP``.

Governing: Amendment 13 (the frozen S1 configuration), Amendment 12 (the
plausible-but-uninformative second null ``T0-XEP``) and, for this round's cells, the
MC2 Catfish identity / intervention contract.

**This module exists so that the S1 lane adds no field and no branch to the
development kernel.**  The MC2 development screen is being launched from the same
tree, and two things must stay true while S1 is prepared:

1. every development arm's configuration hash is byte-identical to the base commit's
   (:class:`mcrl.algorithms.cf_dev.DevSettings` therefore gains NO field -- the lane
   and the ``T0-XEP`` reference identity live on the subclass
   :class:`S1DevSettings`, exactly as the MC2 arm's identity lives on its
   ``JudgeSpec``);
2. the S1 run trains the mechanism the development screen screened -- so the
   mechanism code is used, never re-implemented here.

What S1 needs from the kernel is three lane-aware seed-guard call sites and a
``lane`` keyword on ``dev_rollout``; everything else is in this file.

``T0-XEP`` (Amendment 12 section 2): at step ``t`` of the learner's episode it
computes T0's ordinary frozen score on the state recorded at step ``t`` of ONE
pre-recorded reference episode (:mod:`mcrl.algorithms.cf_xep`), then restricts the
argmax to the learner's CURRENT legal mask.  Same functional form, same
hyperparameters, same score scale; decorrelated from the state the learner is in.
"""

from __future__ import annotations

import copy
import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError
from . import cf_dev as cfd
from . import cf_s1_lane as s1l
from . import cf_teacher as cft
from .cf_sources import HEAD_B, HEAD_E, HEAD_H

DEV_LANE, S1_LANE = s1l.DEV_LANE, s1l.S1_LANE

XEP_MECHANISM: str = "D3-XEP"
XEP_TEACHER: str = "T0-XEP"
"""Amendment 12's arm and teacher names.  ``D3-XEP`` is deliberately NOT added to
``cf_teacher.MECHANISMS``: it exists only in the S1 harness, so a plain
``DevSettings`` cannot name it and a development launcher cannot reach it."""

DEV_EVAL_BASES: tuple[int, int] = (9_211_000, 9_212_000)
"""DEVVAL, i.e. ``DevSettings``'s own defaults.  Used for the generic-validation
shadow below and asserted against the dataclass defaults by the test suite."""


# ------------------------------------------------------------------ T0-XEP
class _AllLegal:
    """A mask object whose every action is legal (duck-typed ``ActionMask``)."""

    __slots__ = ("mask",)

    def __init__(self, n: int = NUM_ACTIONS) -> None:
        self.mask = np.ones(int(n), dtype=bool)


_ALL_LEGAL = _AllLegal()


def t0_score_matrix(states) -> np.ndarray:
    """``(U, 28)`` float64 T0 scores of ``states`` -- by T0's OWN function.

    This calls :func:`mcrl.algorithms.cf_teacher.t0_scores` with an all-legal mask and
    keeps its score matrix, so ``T0-XEP`` cannot drift away from the deployed T0
    expression ``log2(1 + max(gamma_a, 0)) - c [N_a == 0]``: there is no second copy
    of it to drift.  The mask only drives ``t0_scores``'s argmax, which is discarded
    here -- ``T0-XEP``'s argmax is taken under the LEARNER's current mask.
    """
    return cft.t0_scores(states, [_ALL_LEGAL] * len(states))[0]


def t0_xep_labels(reference_states, current_mask: np.ndarray):
    """``T0-XEP`` (Amendment 12 section 2): ``(U, 28)`` scores, ``(U,)`` actions.

    T0's ordinary frozen score computed on ``reference_states`` (step ``t`` of the
    FIXED pre-recorded reference episode), with the resulting argmax restricted to
    ``current_mask``, the LEARNER's legal action mask at its own step ``t``.

    The two inputs come from different episodes on purpose: the 28 candidate slots
    are satellite-major beam-minor over the VISIBLE set, so slot ``k`` in the
    reference episode is not the same physical beam as slot ``k`` now, and user row
    ``u`` is not the same user.  That decorrelation IS the null.
    """
    mask = np.asarray(current_mask, dtype=bool)
    if mask.ndim != 2 or mask.shape[1] != NUM_ACTIONS:
        raise MCRLContractError(f"T0-XEP: current mask has shape {mask.shape}")
    if len(reference_states) != mask.shape[0]:
        raise MCRLContractError(
            f"T0-XEP: {len(reference_states)} reference rows for {mask.shape[0]} "
            "learner rows -- the reference episode must have the same user count"
        )
    scores = t0_score_matrix(reference_states)
    return scores, cft.masked_argmax_rows(scores, mask)


def xep_leakage(xep_actions, t0_actions, legal, t0_scores) -> tuple[float, float, float, int]:
    """Amendment 12's residual-leakage counters for ONE step.

    ``(agreement, T0-score regret, expected uniform-legal agreement, decisions)``,
    summed over the rows that have a legal action.

    The FIRST argument is what ``T0-XEP`` advised and the SECOND is what the **REAL**
    T0 would have done on the same state: the diagnostic exists precisely because
    those are two different teachers, and scoring the null against itself would
    report a meaningless 1.0.  ``t0_scores`` are the REAL T0's scores on the current
    state, so the regret is measured in T0's own units.
    """
    agree = regret = random_expected = 0.0
    decisions = 0
    for u in range(len(t0_actions)):
        if not bool(legal[u].any()):
            continue
        decisions += 1
        agree += float(int(xep_actions[u]) == int(t0_actions[u]))
        random_expected += 1.0 / float(int(legal[u].sum()))
        if 0 <= int(xep_actions[u]) < t0_scores.shape[1]:
            regret += float(
                t0_scores[u, int(t0_actions[u])] - t0_scores[u, int(xep_actions[u])]
            )
    return agree, regret, random_expected, decisions


@dataclass
class XepCounters:
    """Running residual-leakage counters (one episode, or one evaluation read)."""

    agree: float = 0.0
    regret: float = 0.0
    random_expected: float = 0.0
    decisions: int = 0

    def add(self, xep_actions, t0_actions, legal, t0_scores) -> None:
        a, r, x, n = xep_leakage(xep_actions, t0_actions, legal, t0_scores)
        self.agree += a
        self.regret += r
        self.random_expected += x
        self.decisions += n

    def reset(self) -> None:
        self.agree = self.regret = self.random_expected = 0.0
        self.decisions = 0

    def as_dict(self, prefix: str) -> dict[str, Any]:
        n = max(self.decisions, 1)
        return {
            f"{prefix}agreement": float(self.agree / n),
            f"{prefix}score_regret": float(self.regret / n),
            f"{prefix}random_legal_agreement_expected": float(self.random_expected / n),
            f"{prefix}decisions": int(self.decisions),
        }


class XepProbe:
    """The read-only ``T0-XEP`` observer for an evaluation read.

    It ADVISES and never acts: it is installed as a wrapper around the greedy policy,
    computes what ``T0-XEP`` would have advised on the same states and scores it
    against the REAL T0, and returns the greedy action unchanged.  Because the
    returned actions are the policy's own, a rollout with and without the probe is
    bit-identical (asserted by ``tests/test_s1_harness.py``).
    """

    def __init__(self, reference) -> None:
        self._ref = reference
        self.counters = XepCounters()
        self._t = 0

    def new_episode(self) -> None:
        self._t = 0

    def observe(self, states, masks) -> None:
        t0_scores, t0_acts, legal = cft.t0_scores(states, masks)
        xep_acts = t0_xep_labels(self._ref.states_at(self._t), legal)[1]
        self.counters.add(xep_acts, t0_acts, legal, t0_scores)
        self._t += 1

    def wrap(self, policy):
        def probed(enc, masks, states):
            actions = policy(enc, masks, states)
            self.observe(states, masks)
            return actions

        return probed

    def as_dict(self) -> dict[str, Any]:
        out = self.counters.as_dict("t0xep_")
        out["xep_reference"] = self._ref.identity()
        return out


# ------------------------------------------------------------------ settings
@dataclass(frozen=True)
class S1DevSettings(cfd.DevSettings):
    """:class:`~mcrl.algorithms.cf_dev.DevSettings` plus the lane and ``T0-XEP``.

    ``lane`` is ``S1-formal`` for the formal screen and ``E0-development`` for the
    harness's own DEV-seed preflight -- the SAME code path on the development seed
    contract, which is how the S1 driver is exercised end to end without touching a
    formal episode.  The lane is part of every S1 configuration payload, so a
    preflight configuration can never hash to a formal one.

    The three ``xep_reference_*`` fields ARE the second null's null key: a different
    (or regenerated) reference is a different version.  The reference FILE PATH is
    deliberately absent -- a path is a host fact, not an identity.
    """

    lane: str = S1_LANE
    xep_reference_sha256: str | None = None
    xep_reference_key: tuple[int, int] | None = None   # DEV-NULL (env, mobility)
    xep_reference_policy: str | None = None

    def __post_init__(self) -> None:
        if self.lane not in s1l.LANES:
            raise MCRLContractError(f"lane must be one of {s1l.LANES}")
        xep = (self.xep_reference_sha256, self.xep_reference_key,
               self.xep_reference_policy)

        # -- generic validation, performed by the DEVELOPMENT class itself ------
        # Everything that is not lane-specific (mechanism / teacher consistency, the
        # finiteness and range checks, the matched-null bookkeeping) is validated by
        # constructing a development-lane SHADOW of this configuration and letting
        # DevSettings.__post_init__ run on it.  The S1 lane therefore inherits every
        # rule the development kernel has -- including rules added to it later --
        # instead of carrying a second, drifting copy of them.
        shadow = {f.name: getattr(self, f.name)
                  for f in dataclasses.fields(cfd.DevSettings)}
        if self.mechanism == XEP_MECHANISM:
            # D3-XEP is D3's loss family with another target (Amendment 12: same
            # mechanism, same m, same lambda_E); the shadow says so.
            shadow["mechanism"], shadow["teacher"] = "D3-T0", "T0"
        if self.lane == S1_LANE:
            shadow["devval_env_base"], shadow["devval_mobility_base"] = DEV_EVAL_BASES
            if self.null_key is not None:
                dev_base = cfd.NULL_BASE_FOR.get(shadow["mechanism"])
                if dev_base is None:
                    raise MCRLContractError(
                        f"{self.mechanism} is not a matched null but carries a null key"
                    )
                shadow["null_key"] = (dev_base, int(tuple(self.null_key)[-1]))
        cfd.DevSettings(**shadow)

        # -- the lane's own evaluation episodes and null stream ----------------
        bases = (int(self.devval_env_base), int(self.devval_mobility_base))
        if self.lane == S1_LANE:
            if bases != (s1l.FORMAL_EVAL_ENV_BASE, s1l.FORMAL_EVAL_MOB_BASE):
                raise MCRLContractError(
                    f"the S1 lane evaluates on the formal evaluation episodes "
                    f"{(s1l.FORMAL_EVAL_ENV_BASE, s1l.FORMAL_EVAL_MOB_BASE)}, "
                    f"not {bases}"
                )
            if self.null_key is not None:
                s1l.assert_s1_null_key(
                    self.null_key, f"S1 {self.mechanism} key",
                    base=s1l.S1_NULL_BASE_FOR.get(self.mechanism),
                )
        elif bases != DEV_EVAL_BASES:
            # A DEV-lane S1 configuration is a PREFLIGHT: it evaluates on DEVVAL.
            raise MCRLContractError(
                f"a development-lane S1 configuration evaluates on DEVVAL "
                f"{DEV_EVAL_BASES}, not {bases}"
            )

        # -- the T0-XEP reference identity -------------------------------------
        if self.mechanism == XEP_MECHANISM:
            if self.teacher != XEP_TEACHER:
                raise MCRLContractError(
                    f"{XEP_MECHANISM} requires teacher {XEP_TEACHER!r}"
                )
            if any(x is None for x in xep):
                raise MCRLContractError(
                    f"{XEP_MECHANISM} needs its reference identity "
                    "(sha256, DEV-NULL key, policy)"
                )
            if not (isinstance(self.xep_reference_sha256, str)
                    and len(self.xep_reference_sha256) == 64):
                raise MCRLContractError("xep_reference_sha256 must be a sha256 hex digest")
            if (not isinstance(self.xep_reference_key, (tuple, list))
                    or len(self.xep_reference_key) != 2):
                raise MCRLContractError(
                    "xep_reference_key is the (env seed, mobility seed) pair the "
                    "reference episode was rolled on"
                )
            for seed in self.xep_reference_key:
                base = cfd.assert_dev_seed(seed, "T0-XEP reference seed")
                if not any(b <= base <= b + 999 for b in cfd.DEV_NULL_KEY_BASES):
                    raise MCRLContractError(
                        f"the T0-XEP reference seed {seed} is not in a declared "
                        f"DEV-NULL namespace {cfd.DEV_NULL_KEY_BASES} (Amendment 12 "
                        "section 2: never DEV, DEVVAL or CONFIRM)"
                    )
            if not str(self.xep_reference_policy or ""):
                raise MCRLContractError("the T0-XEP reference must name its policy")
        else:
            if self.teacher == XEP_TEACHER:
                raise MCRLContractError(f"only {XEP_MECHANISM} uses {XEP_TEACHER!r}")
            if any(x is not None for x in xep):
                raise MCRLContractError(
                    f"only {XEP_MECHANISM} may carry a reference-trajectory identity"
                )

    # -- properties the kernel reads ---------------------------------------
    @property
    def uses_teacher(self) -> bool:
        return self.mechanism != "D0"

    @property
    def teacher_weight(self) -> float:
        """The weight actually multiplying this mechanism's teacher loss."""
        if self.mechanism == XEP_MECHANISM:
            return float(self.lambda_e)
        return super().teacher_weight

    @property
    def is_xep(self) -> bool:
        return self.mechanism == XEP_MECHANISM

    @property
    def eval_env_base(self) -> int:
        """The lane's evaluation env base: the formal set, or DEVVAL in a preflight."""
        return int(self.devval_env_base)

    @property
    def eval_mobility_base(self) -> int:
        return int(self.devval_mobility_base)


def s1_dev_settings_from_payload(payload: Mapping[str, Any]) -> S1DevSettings:
    raw = dict(payload["dev_settings"])
    for key in ("null_key", "xep_reference_key"):
        if raw.get(key) is not None:
            raw[key] = tuple(int(x) for x in raw[key])
    return S1DevSettings(**raw)


# ------------------------------------------------------------------ trainer
class S1Trainer(cfd.CFDevTrainer):
    """The S1 screen's learner: the development learner on the S1 seed contract.

    Every mechanism the development screen screened runs here through the INHERITED
    code path -- this class adds the ``T0-XEP`` arm and the Amendment 12 diagnostics
    and changes nothing else.  ``D3-XEP`` is reachable only from here: a plain
    ``CFDevTrainer`` given a ``D3-XEP`` configuration fails closed at its first
    teacher loss instead of silently training ``D3-T0``.
    """

    def __init__(self, env, config, settings, dev, *, xep_reference=None, **kw) -> None:
        if not isinstance(dev, S1DevSettings):
            raise MCRLContractError(
                "the S1 harness runs on S1DevSettings (it carries the lane and, for "
                "D3-XEP, the sealed reference identity)"
            )
        super().__init__(env, config, settings, dev, **kw)
        self._xep_ref = self._bind_xep_reference(xep_reference)
        self._xep_counters = XepCounters()
        if self._xep_ref is not None:
            # The step index comes from the TRAINING-ONLY TeacherContext seam the
            # frozen loop already maintains (``step_index`` is one of its declared
            # fields).  T0-XEP reads nothing else from it -- no driver, no
            # candidates -- and if the seam is ever not built, the labels fail
            # closed rather than silently scoring the wrong reference step.
            self._needs_teacher_context = True

    # -- the sealed reference ----------------------------------------------
    def _bind_xep_reference(self, reference):
        """Bind the ONE fixed reference trajectory, or refuse.

        Amendment 12 section 2: the reference is recorded once, before the first S1
        run, and may not be regenerated.  It is bound here, ONCE, for the lifetime of
        the trainer -- never inside an episode -- and it must be the reference the
        configuration declares.
        """
        d = self.dev
        if not d.is_xep:
            if reference is not None:
                raise MCRLContractError(
                    f"only {XEP_MECHANISM} takes a T0-XEP reference trajectory"
                )
            return None
        if reference is None:
            raise MCRLContractError(
                f"{XEP_MECHANISM} needs its pre-recorded reference trajectory "
                "(cf_xep.load_reference)"
            )
        if reference.sha256 != d.xep_reference_sha256:
            raise MCRLContractError(
                f"the loaded T0-XEP reference is {reference.sha256}, the configuration "
                f"declares {d.xep_reference_sha256}"
            )
        if tuple(reference.key) != tuple(d.xep_reference_key):
            raise MCRLContractError(
                f"the T0-XEP reference was rolled on {reference.key}, the "
                f"configuration declares {tuple(d.xep_reference_key)}"
            )
        if reference.policy != d.xep_reference_policy:
            raise MCRLContractError(
                f"the T0-XEP reference policy is {reference.policy!r}, the "
                f"configuration declares {d.xep_reference_policy!r}"
            )
        if reference.users != self.num_users:
            raise MCRLContractError(
                f"the T0-XEP reference has {reference.users} users, this environment "
                f"has {self.num_users}"
            )
        if reference.steps < self.env.config.steps_per_episode:
            raise MCRLContractError(
                f"the T0-XEP reference is {reference.steps} steps, the episode is "
                f"{self.env.config.steps_per_episode}"
            )
        return reference

    @property
    def xep_reference_sha256(self) -> str | None:
        """The bound reference's sha256 -- the null key of the second null."""
        return None if self._xep_ref is None else self._xep_ref.sha256

    def _xep_step(self) -> int:
        ctx = self._teacher_context
        if ctx is None:
            raise MCRLContractError(
                "D3-XEP labels are step-indexed (step t of the learner's episode is "
                "matched to step t of the fixed reference episode) and the "
                "training-time step seam is not present on this path"
            )
        step = int(ctx.step_index)
        last = int(self.env.config.steps_per_episode) - 1
        if bool(ctx.is_final_step) != (step >= last):
            raise MCRLContractError(
                f"the step seam is inconsistent: step {step} of {last + 1}, "
                f"is_final_step={ctx.is_final_step}"
            )
        return step

    # -- teacher ------------------------------------------------------------
    def xep_labels_at(self, states, masks, step: int):
        """``T0-XEP``'s ``(scores, actions)`` for ``states`` at reference ``step``."""
        legal = cft.t0_scores(states, masks)[2]
        return t0_xep_labels(self._xep_ref.states_at(int(step)), legal)

    def teacher_labels_ext(self, states, masks):
        """The inherited labels, plus the ``D3-XEP`` branch (Amendment 12)."""
        if not self.dev.is_xep:
            return super().teacher_labels_ext(states, masks)
        scores, t0_acts, legal = cft.t0_scores(states, masks)
        used, used_acts = t0_xep_labels(
            self._xep_ref.states_at(self._xep_step()), legal
        )
        # Residual leakage at COLLECTION time, on exactly the rows that are labelled.
        self._xep_counters.add(used_acts, t0_acts, legal, scores)
        return t0_acts, used_acts, used, legal, scores, None, None

    def _teacher_loss(self, batch, q_all):
        """``D3-XEP`` is the D3 margin loss pointed at the reference action.

        Same ``cf_teacher.d3_margin_loss``, same frozen ``m`` and ``lambda_E``, same
        masks and gradient path as ``D3-T0`` -- only the target differs.  A test
        asserts bit-equality with the inherited ``D3-T0`` branch on the same batch.
        """
        if not self.dev.is_xep:
            return super()._teacher_loss(batch, q_all)
        d = self.dev
        mask = torch.tensor(np.asarray(batch["masks"], dtype=bool),
                            dtype=torch.bool, device=self.device)
        scores = cft.student_scores(q_all[HEAD_B], q_all[HEAD_E], q_all[HEAD_H],
                                   self.eta_tilde, self.lam)
        a_t = torch.tensor(np.asarray(batch["teacher_action"], dtype=np.int64),
                           dtype=torch.long, device=self.device)
        return d.lambda_e * cft.d3_margin_loss(scores, mask, a_t, d.margin)

    # -- evaluation ---------------------------------------------------------
    def xep_probe(self) -> XepProbe | None:
        """The read-only ``T0-XEP`` observer for an evaluation read, or ``None``."""
        return None if self._xep_ref is None else XepProbe(self._xep_ref)

    def devval(self) -> dict[str, Any]:
        """The lane's evaluation read: greedy deployed rule, no training RNG.

        ``S1-formal`` reads the 24 formal evaluation episodes; a DEV-lane preflight
        reads DEVVAL.  For ``D3-XEP`` the Amendment 12 residual-leakage probe rides
        along as an observer and is cross-checked against the rollout's own decision
        count, so a probe that silently saw different rows cannot be reported.
        """
        probe = self.xep_probe()
        if probe is None:
            return super().devval()
        if self._env_factory is None:
            raise MCRLContractError("the evaluation read needs an env_factory")
        greedy = lambda enc, masks, states: self.greedy_actions(enc, masks)  # noqa: E731

        def factory(i):
            probe.new_episode()
            return probe.wrap(greedy)

        res = cfd.dev_rollout(factory, env_factory=self._env_factory,
                              encode=self.encode_at, seeds=self.devval_seeds(),
                              t0_agreement=True, lane=cfd.lane_of(self.dev))
        out = probe.as_dict()
        if int(out["t0xep_decisions"]) != int(res["t0_decisions"]):
            raise MCRLContractError(
                f"the T0-XEP probe saw {out['t0xep_decisions']} decisions and the "
                f"rollout {res['t0_decisions']}: they are not the same rows"
            )
        res.update(out)
        return res

    # -- training loop ------------------------------------------------------
    def train_cf(self, *, episode_callback=None, **kw) -> list[dict]:
        """The inherited loop; for ``D3-XEP`` the per-episode log gains Amendment
        12's collection-time leakage counters and the bound reference's sha256."""
        if self._xep_ref is None:
            return super().train_cf(episode_callback=episode_callback, **kw)

        def cb(log: dict) -> None:
            log.update(self._xep_counters.as_dict("teacher_action_vs_t0_"),
                       xep_reference_sha256=self._xep_ref.sha256)
            self._xep_counters.reset()
            if episode_callback is not None:
                episode_callback(log)

        return super().train_cf(episode_callback=cb, **kw)

    # -- persistence --------------------------------------------------------
    def training_state_dict(self) -> dict[str, Any]:
        state = super().training_state_dict()
        state["dev"]["xep_reference_sha256"] = self.xep_reference_sha256
        state["dev"]["lane"] = cfd.lane_of(self.dev)
        return state

    def load_training_state_dict(self, state) -> None:
        dev = state.get("dev")
        if not isinstance(dev, Mapping):
            raise MCRLContractError("resume state carries no development block")
        if dev.get("xep_reference_sha256") != self.xep_reference_sha256:
            raise MCRLContractError(
                "resume state was written against a different T0-XEP reference "
                f"({dev.get('xep_reference_sha256')} vs {self.xep_reference_sha256})"
            )
        if dev.get("lane") != cfd.lane_of(self.dev):
            raise MCRLContractError(
                f"resume state was written in lane {dev.get('lane')!r}, this run is "
                f"{cfd.lane_of(self.dev)!r}"
            )
        super().load_training_state_dict(state)


# ------------------------------------------------------------------ purity
class sources_unregistered:
    """Unregister every teacher source for the duration of a block.

    The S1 evaluation read is the DEPLOYED rule -- the masked argmax of the three Q
    networks at the frozen ``eta`` -- and nothing else.  Wrapping the read in this
    context manager turns that claim into a runtime fact: if any evaluation path
    asked a Catfish source for an action, it would raise instead of quietly
    answering.  The registry is restored exactly as it was on exit.
    """

    def __init__(self) -> None:
        self._saved: dict[str, tuple[Any, bool]] = {}

    def __enter__(self) -> "sources_unregistered":
        for name in cft.registered_teachers():
            self._saved[name] = (cft.teacher_source(name),
                                 cft.teacher_needs_context(name))
        for name in self._saved:
            cft.unregister_teacher_source(name)
        return self

    def __exit__(self, *exc) -> None:
        for name, (fn, needs) in self._saved.items():
            cft.register_teacher_source(name, fn, replace=True, needs_context=needs)
        self._saved = {}


def judge_disabled():
    """A context manager that makes any judge construction raise.

    Used around the S1 evaluation read together with :class:`sources_unregistered`:
    the deployed policy may not consult the training-only judge, and this proves it
    for the run rather than for a test fixture.  It is a no-op when the judge module
    is not present in the tree (there is then nothing to disable).
    """
    try:
        from . import cf_judge as cfj
    except ImportError:                      # pragma: no cover - pre-merge trees
        class _Noop:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

        return _Noop()

    class _Disabled:
        def __enter__(self):
            self._real = cfj.StepJudge

            def refuse(*a, **kw):
                raise MCRLContractError(
                    "the S1 evaluation read is the deployed rule: the training-only "
                    "judge may not be constructed on it"
                )

            cfj.StepJudge = refuse
            return self

        def __exit__(self, *exc):
            cfj.StepJudge = self._real
            return None

    return _Disabled()


def copy_rng_state(rng) -> Any:
    return None if rng is None else copy.deepcopy(rng.bit_generator.state)
