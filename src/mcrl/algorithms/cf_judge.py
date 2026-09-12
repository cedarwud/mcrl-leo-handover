"""MC2: the training-only counterfactual judge and the judge-gated intervention.

Governing: ``.scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md``
(r1; sections 2, 3, 5 and 6).  **Development lane, training only.**  Nothing in
this module is deployed, nothing here is an EE claim, and a judge win is not an EE
improvement: ``B - eta0 * E`` is a fixed-price SURROGATE of one step's
contribution, read only as a gate.

The judge (section 2).  For user ``u`` at decision step ``t``, with ``x`` the
behaviour joint action about to be stepped and a candidate action ``a``::

    ev(a)    = StepEnvironment.evaluate_actions((a, x_-u), deepcopy(env_rng))
    kappa(a) = ( n_served(ev(a)),  B(ev(a)) - eta0 * E(ev(a)) )

``B, E = cf_credit.evaluation_bits_joules(ev, dt)`` (system bits and joules of the
step), ``n_served`` = served users of the step, ``eta0 = 110_507_234.83444457``
bit/J (the frozen E0 price).  ``>`` is STRICT lexicographic and a tie goes to
the incumbent.  All evaluations of one step run inside
``cf_credit.frozen_driver_positions`` (the B1 / T_DELTA path) and each one
deep-copies the environment generator, so nothing is committed and no
generator is advanced (``tests/test_mc2_judge.py`` pins both, end to end).

One exact reuse and nothing else: ``kappa_u(x_u)`` IS the evaluation of the
joint vector ``x`` (``(x_u, x_-u) == x``), and :meth:`StepEnvironment.evaluate_actions`
is a pure function of (action vector, deep copy of ``rng``), so the base
evaluation is computed once per step and served for every such query.  It is
also asserted equal to the committed step (bits, joules, served flags) after
``env.step`` -- the ruling-2 parity guard of the difference credit.

Rules (section 3), each with its own versioned identity in the config hash:

``MC2-JGO-v1`` (cells ``{A,B}`` FULL-v1, ``{A,R}`` B-null-v1)
    per user with a legal action the incumbent and target are ``a^A`` (the anchor
    stays unconditional); the challenger (``a^B`` = T_NEXT, or ``a^R`` = one
    uniform legal action) becomes the target only if ``kappa(c) > kappa(a^A)``.
    No call when ``c == a^A``.  ``A-only-v1`` is arm 4 (``D3-T0``) itself.
``MC2-ARB-v2`` (cells ``{A}`` A-only-v2, ``{A,B}`` FULL-v2, ``{A,R}`` B-null-v2)
    candidates ``{x_u, a^A, a^B}``; the winner is a sequence of strict
    comparisons in the declared order (``w = x_u``; ``a^A`` replaces ``w`` only if
    ``kappa(a^A) > kappa(w)``; then ``a^B`` likewise), i.e. max ``kappa`` with ties
    to ``x_u``, then A, then B; margin toward the winner only if it is not ``x_u``.
``MC2-B-ONLY-SHARED-v1`` (the shared ``{B}`` cell)
    rule-independent: without A both versions reduce to "``a^B`` is the target
    only where ``kappa(a^B) > kappa(x_u)``, else no target" (tested equal, labels
    and parameter sha256, for the v1 and the v2 code paths).

B and R are absent at the final step (``t = T-1``).

The loss: the single-target D3 large margin of :func:`cf_teacher.d3_margin_loss`,
statement for statement, with a per-row weight ``w = 1[target exists]`` and the
mean over the FULL batch -- rows without a target contribute exactly 0 and the
vacated dose is NOT refilled.  With every ``w = 1`` it is bit-identical to
``d3_margin_loss`` in value and gradient (tested), which is what makes FULL-v1
with the gate shut the frozen ``D3-T0``.
"""

from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import torch

from ..errors import MCRLContractError
from ..runtime.replay_buffer import ReplayBuffer
from . import cf_credit as cc
from .cf_teacher import MASK_FILL

# ------------------------------------------------------------------ identities
ETA0_JUDGE: float = 110_507_234.83444457
"""The frozen E0 price (``dev_e0_common.ETA0_EXPECTED``), bit/J.  The judge's own
constant: it is in the judge identity and never follows a learner's eta."""

JUDGE_ID: str = "MC2-KAPPA-LEX-v1"
JUDGE_DEFINITION: str = (
    "kappa_u(a) = (n_served, B - eta0*E) of StepEnvironment.evaluate_actions("
    "(a, x_-u), deepcopy(env_rng)) under cf_credit.frozen_driver_positions; "
    "B, E = cf_credit.evaluation_bits_joules (system totals of the step); strict "
    "lexicographic; ties -> incumbent; proposals restricted to {x_u, a^A, a^B}"
)

MECHANISM_NAME: str = "MC2"
"""``DevSettings.mechanism`` of the MC2 judge arm (arm 10).  Which rule it runs is
the :class:`~mcrl.algorithms.cf_dev.JudgeSpec` ``mechanism_id``."""

JGO_MECHANISM_ID: str = "MC2-JGO-v1"
ARB_MECHANISM_ID: str = "MC2-ARB-v2"
BONLY_MECHANISM_ID: str = "MC2-B-ONLY-SHARED-v1"
RULE_OF: dict[str, str] = {JGO_MECHANISM_ID: "v1", ARB_MECHANISM_ID: "v2",
                           BONLY_MECHANISM_ID: "shared"}
RULE_DEFINITIONS: dict[str, str] = {
    JGO_MECHANISM_ID: (
        "judge-gated override: incumbent = target = a^A (unconditional anchor); the "
        "challenger c (a^B or a^R) becomes the target iff kappa(c) > kappa(a^A) "
        "strictly; no call when c == a^A; challenger absent at t = T-1"),
    ARB_MECHANISM_ID: (
        "arbitration: candidates {x_u, a^A, c} (c = a^B or a^R, absent at t = T-1); "
        "w = x_u, then a^A, then c each replace w only if kappa > kappa(w) strictly "
        "(max kappa, ties x_u > A > c); margin toward w only if w != x_u"),
    BONLY_MECHANISM_ID: (
        "shared B-only (rule-independent): a^B is the target iff kappa(a^B) > "
        "kappa(x_u) strictly, else no target; no call when a^B == x_u; B absent at "
        "t = T-1"),
}
DECLARED_CELLS: dict[str, tuple[tuple[str, ...], ...]] = {
    JGO_MECHANISM_ID: (("A", "B"), ("A", "R")),
    ARB_MECHANISM_ID: (("A",), ("A", "B"), ("A", "R")),
    BONLY_MECHANISM_ID: (("B",),),
}
"""(rule, source set) cells of contract r1 section 6.  ``A-only-v1`` is arm 4
(``D3-T0``) itself and is refused here, so no second A-only-v1 identity can exist;
``{B}`` exists only under the rule-independent shared identity."""

SOURCE_A_ID: str = "T0"
SOURCE_B_ID: str = "T_NEXT"
NULL_ID: str = "MC2-UNIFORM-LEGAL-PROPOSAL-REPLACEMENT-v1"
"""The B-null: one uniform legal action per user with a legal action at
``t < T-1``, from a fresh generator at the declared composite key ``(9_243_000, k)``;
it replaces ``a^B`` and reads no T_NEXT quantity."""
NULL_BASE: int = 9_243_000

NO_TARGET: int = -1
TAG_NONE, TAG_A, TAG_B, TAG_R = 0, 1, 2, 3
TAG_NAMES: tuple[str, ...] = ("none", "A", "B", "R")


# ------------------------------------------------------------------ kappa
@dataclass(frozen=True)
class Kappa:
    """The judge's score of one joint vector: ``(served, B - eta0 E)`` plus B, E."""

    served: int
    surrogate: float
    bits: float
    joules: float


def kappa_of(ev, eta0: float, dt: float = cc.DT_S) -> Kappa:
    bits, joules = cc.evaluation_bits_joules(ev, dt)
    served = int(np.count_nonzero(np.asarray(ev.resolution.served, dtype=bool)))
    return Kappa(served=served, surrogate=float(bits - float(eta0) * joules),
                 bits=float(bits), joules=float(joules))


def strictly_better(a: Kappa, b: Kappa) -> bool:
    """``a > b`` STRICT lexicographic on ``(served, B - eta0 E)``.  Equal -> False
    (a tie goes to the incumbent).  The served count comes first, so no candidate
    can win by shedding a user."""
    if a.served != b.served:
        return a.served > b.served
    return a.surrogate > b.surrogate


# ------------------------------------------------------------------ the judge
class StepJudge:
    """The pre-step judge of ONE decision step (behaviour vector ``x`` fixed).

    Use as a context manager: the evaluations run inside
    ``cf_credit.frozen_driver_positions`` (restored on exit).  Every evaluation
    deep-copies ``rng`` (inside ``evaluate_actions``); the judge never writes the
    environment, the driver or any generator.
    """

    def __init__(self, env, x, rng, *, eta0: float = ETA0_JUDGE,
                 dt: float = cc.DT_S) -> None:
        self._se = cc.step_env(env)
        self._x = np.array(x, dtype=np.int64, copy=True)
        self._x.setflags(write=False)
        self._rng = rng
        self.eta0 = float(eta0)
        self.dt = float(dt)
        self._cache: dict[tuple[int, int], Kappa] = {}
        self._base: Kappa | None = None
        self._base_served: np.ndarray | None = None
        self.evaluations = 0
        self.wall_s = 0.0
        self._ctx = None

    def __enter__(self) -> "StepJudge":
        self._t_enter = time.perf_counter()
        self._ctx = cc.frozen_driver_positions(self._se)
        self._ctx.__enter__()
        return self

    def __exit__(self, *exc) -> None:
        ctx, self._ctx = self._ctx, None
        try:
            ctx.__exit__(*exc)
        finally:
            self.wall_s = time.perf_counter() - self._t_enter

    def _evaluate(self, vec: np.ndarray):
        if self._ctx is None:
            raise MCRLContractError("the judge evaluates only inside its step context")
        ev = self._se.evaluate_actions(vec, self._rng)
        self.evaluations += 1
        return ev

    @property
    def x(self) -> np.ndarray:
        return self._x

    def base(self) -> Kappa:
        """``kappa`` of the behaviour vector ``x`` itself (evaluated once)."""
        if self._base is None:
            ev = self._evaluate(self._x)
            self._base = kappa_of(ev, self.eta0, self.dt)
            self._base_served = np.array(ev.resolution.served, dtype=bool, copy=True)
        return self._base

    def kappa(self, u: int, a: int) -> Kappa:
        """``kappa_u(a)`` = the evaluation of ``(a, x_-u)``."""
        u, a = int(u), int(a)
        if a == int(self._x[u]):
            return self.base()                   # (x_u, x_-u) IS x: exact reuse
        key = (u, a)
        got = self._cache.get(key)
        if got is None:
            vec = np.array(self._x, dtype=np.int64, copy=True)
            vec[u] = a
            got = kappa_of(self._evaluate(vec), self.eta0, self.dt)
            self._cache[key] = got
        return got

    def evaluated(self, u: int, a: int) -> bool:
        """Was ``kappa_u(a)`` evaluated this step (a diagnostic never forces one)."""
        u, a = int(u), int(a)
        if a == int(self._x[u]):
            return self._base is not None
        return (u, a) in self._cache

    def assert_committed_parity(self, outcome) -> None:
        """The base evaluation must BE the committed step (bits, joules, served)."""
        if self._base is None:
            raise MCRLContractError("the judge's base evaluation was never taken")
        bits, joules = cc.evaluation_bits_joules(outcome, self.dt)
        served = np.asarray(outcome.resolution.served, dtype=bool)
        if ((bits, joules) != (self._base.bits, self._base.joules)
                or not np.array_equal(served, self._base_served)):
            raise MCRLContractError(
                "judge parity broken: the evaluated behaviour vector is not the "
                "committed step (the judge advanced a generator or the environment)"
            )


# ------------------------------------------------------------------ decisions
@dataclass
class StepLabels:
    """Per-user labels of one decision step (all arrays ``(U,)``)."""

    decision: np.ndarray        # bool: the user has a legal action
    challenger: np.ndarray      # int64: the challenger's action, NO_TARGET if none
    target: np.ndarray          # int64: the margin target, NO_TARGET if none
    tag: np.ndarray             # int8: TAG_NONE / TAG_A / TAG_B / TAG_R
    override: np.ndarray        # bool: the target is not the rule's default
    compared: np.ndarray        # bool: the judge compared two different actions
    lead_served: np.ndarray     # int64: kappa(winner or c).served - kappa(incumbent).served
    lead_surrogate: np.ndarray  # float64: same, surrogate (NaN where not compared)
    challenger_tag: int = TAG_NONE


def _empty_labels(users: int, challenger_tag: int) -> StepLabels:
    return StepLabels(
        decision=np.zeros(users, dtype=bool),
        challenger=np.full(users, NO_TARGET, dtype=np.int64),
        target=np.full(users, NO_TARGET, dtype=np.int64),
        tag=np.zeros(users, dtype=np.int8),
        override=np.zeros(users, dtype=bool),
        compared=np.zeros(users, dtype=bool),
        lead_served=np.zeros(users, dtype=np.int64),
        lead_surrogate=np.full(users, np.nan, dtype=np.float64),
        challenger_tag=challenger_tag,
    )


def jgo_labels(*, use_a: bool, challenger_tag: int, legal: np.ndarray, x: np.ndarray,
               a_a: np.ndarray, challenger: np.ndarray | None,
               kappa: Callable[[int, int], Kappa]) -> StepLabels:
    """``MC2-JGO-v1`` for one step (contract section 3).

    ``challenger`` is ``None`` when the challenger ABSTAINS (the final step); the
    caller decides abstention, this function only honours it.  ``kappa(u, a)`` is
    the judge.  It is called only for ``c != incumbent``.  With ``use_a=False``
    (the shared ``{B}`` cell) the incumbent is ``x_u`` and a row the challenger
    does not win carries no target.
    """
    legal = np.asarray(legal, dtype=bool)
    users = legal.shape[0]
    out = _empty_labels(users, challenger_tag)
    if challenger is not None:
        out.challenger[:] = np.asarray(challenger, dtype=np.int64)
    for u in range(users):
        if not bool(legal[u].any()):
            out.challenger[u] = NO_TARGET
            continue
        out.decision[u] = True
        if use_a:
            inc = int(a_a[u])
            out.target[u] = inc
            out.tag[u] = TAG_A
        else:
            inc = int(x[u])
        if challenger is None:
            continue
        c = int(challenger[u])
        if c == NO_TARGET or c == inc:
            continue
        k_c = kappa(u, c)
        k_i = kappa(u, inc)
        out.compared[u] = True
        out.lead_served[u] = int(k_c.served - k_i.served)
        out.lead_surrogate[u] = float(k_c.surrogate - k_i.surrogate)
        if strictly_better(k_c, k_i):
            out.target[u] = c
            out.tag[u] = challenger_tag
            out.override[u] = True
    return out


def arb_labels(*, use_a: bool, challenger_tag: int, legal: np.ndarray, x: np.ndarray,
               a_a: np.ndarray, challenger: np.ndarray | None,
               kappa: Callable[[int, int], Kappa]) -> StepLabels:
    """``MC2-ARB-v2`` for one step (contract section 3, declared second version).

    ``w = x_u``; then ``a^A`` (A enabled), then the challenger (not abstaining),
    each replaces ``w`` only on a STRICT ``kappa`` improvement -- max ``kappa``,
    ties ``x_u`` > A > challenger.  An action equal to the running winner is never
    re-compared (so ``a^B == a^A`` can only ever be an A win).  Margin toward ``w``
    only if ``w != x_u``.  ``lead`` = ``kappa(w) - kappa(x_u)`` on a win, else the
    best compared candidate's ``kappa`` minus ``kappa(x_u)``.
    """
    legal = np.asarray(legal, dtype=bool)
    users = legal.shape[0]
    out = _empty_labels(users, challenger_tag)
    if challenger is not None:
        out.challenger[:] = np.asarray(challenger, dtype=np.int64)
    for u in range(users):
        if not bool(legal[u].any()):
            out.challenger[u] = NO_TARGET
            continue
        out.decision[u] = True
        xu = int(x[u])
        cands: list[tuple[int, int]] = []
        if use_a:
            cands.append((TAG_A, int(a_a[u])))
        if challenger is not None and int(challenger[u]) != NO_TARGET:
            cands.append((challenger_tag, int(challenger[u])))
        w_tag, w_act, k_w = TAG_NONE, xu, None
        best: Kappa | None = None
        for tag, a in cands:
            if a == w_act:
                continue                    # the running winner itself: no call
            if k_w is None:
                k_w = kappa(u, xu)          # kappa(x_u): the base, never extra
            k_a = kappa(u, a)
            out.compared[u] = True
            if best is None or strictly_better(k_a, best):
                best = k_a
            if strictly_better(k_a, k_w):
                w_tag, w_act, k_w = tag, a, k_a
        if not out.compared[u]:
            continue
        k_x = kappa(u, xu)
        ref = k_w if w_tag != TAG_NONE else best
        out.lead_served[u] = int(ref.served - k_x.served)
        out.lead_surrogate[u] = float(ref.surrogate - k_x.surrogate)
        if w_tag != TAG_NONE:
            out.target[u] = w_act
            out.tag[u] = w_tag
            out.override[u] = True
    return out


def labeller_for(mechanism_id: str) -> Callable[..., StepLabels]:
    """The per-step labelling rule of a versioned mechanism identity."""
    if mechanism_id == JGO_MECHANISM_ID:
        return jgo_labels
    if mechanism_id == ARB_MECHANISM_ID:
        return arb_labels
    if mechanism_id == BONLY_MECHANISM_ID:
        # rule-independent: on {B} jgo_labels(use_a=False) == arb_labels (tested,
        # labels and parameter sha256); one code path runs the shared cell.
        return jgo_labels
    raise MCRLContractError(f"no labelling rule for {mechanism_id!r}")


# ------------------------------------------------------------------ the loss
def weighted_margin_loss(scores: torch.Tensor, mask: torch.Tensor,
                         a_target: torch.Tensor, weight: torch.Tensor,
                         margin: float) -> tuple[torch.Tensor, torch.Tensor]:
    """``(1/|batch|) sum_rows w [max_{a legal}(S + m 1(a != t)) - S(t)]`` and the rows.

    Statement for statement :func:`cf_teacher.d3_margin_loss`, then ``* w`` and the
    mean over the FULL batch: a row with ``w = 0`` contributes exactly 0 (its
    ``a_target`` is only a legal placeholder) and the vacated dose is not
    refilled.  With every ``w = 1`` the value and the gradient are those of
    ``d3_margin_loss`` bit for bit (multiplying by 1.0 is exact).
    """
    if margin < 0:
        raise MCRLContractError("margin must be >= 0")
    if weight.shape != (scores.shape[0],):
        raise MCRLContractError("one weight per row")
    a_col = a_target.view(-1, 1)
    if not bool(mask.gather(1, a_col).all()):
        raise MCRLContractError("MC2: a margin target is illegal in its state")
    marg = torch.full_like(scores, float(margin))
    marg.scatter_(1, a_col, 0.0)
    q = (scores + marg).masked_fill(~mask, MASK_FILL)
    per_row = q.max(dim=1).values - scores.gather(1, a_col).squeeze(1)
    return (per_row * weight).mean(), per_row


def tag_breakdown(per_row: torch.Tensor, weight: torch.Tensor, tags: np.ndarray,
                  lambda_e: float) -> dict[str, dict[str, float]]:
    """Sampled rows per tag and each tag's share of the (weighted, full-batch) loss."""
    contrib = (per_row.detach() * weight.detach()).double().numpy() / float(per_row.shape[0])
    tags = np.asarray(tags, dtype=np.int64)
    rows, loss = {}, {}
    for code, name in enumerate(TAG_NAMES):
        sel = tags == code
        rows[name] = int(sel.sum())
        loss[name] = float(lambda_e) * float(contrib[sel].sum())
    return {"rows": rows, "loss": loss}


# ------------------------------------------------------------------ replay
class JudgeReplayBuffer(ReplayBuffer):
    """FIFO replay whose rows carry the MC2 labels (``a^A``, challenger, target,
    tag, override, judge lead).  Same capacity, same sampling arithmetic (one
    ``rng.choice`` call, as :class:`ReplayBuffer`), so a judge arm draws the same
    minibatch indices as ``D3-T0`` on the same trajectory."""

    _JUDGE_STATE_FORMAT_VERSION = 1

    def __init__(self, capacity: int) -> None:
        super().__init__(capacity)
        self._labels: deque[tuple[int, int, int, int, bool, int, float]] = deque(
            maxlen=capacity
        )
        self._last: dict[str, np.ndarray] | None = None

    def push(self, *args, **kwargs):  # noqa: D102 - fail closed
        raise MCRLContractError("the MC2 replay stores judge labels: use push_judged()")

    def push_labeled(self, *args, **kwargs):  # noqa: D102 - fail closed
        raise MCRLContractError("the MC2 replay stores judge labels: use push_judged()")

    def push_judged(self, state, action, reward_3, next_state, mask, next_mask, done,
                    *, a_a: int, challenger: int, target: int, tag: int,
                    override: bool, lead_served: int, lead_surrogate: float) -> None:
        mask = np.asarray(mask, dtype=bool)
        if not (0 <= int(a_a) < mask.size and bool(mask[int(a_a)])):
            raise MCRLContractError("a^A is illegal in the stored state")
        if int(target) != NO_TARGET and not (
                0 <= int(target) < mask.size and bool(mask[int(target)])):
            raise MCRLContractError("the margin target is illegal in the stored state")
        if int(challenger) != NO_TARGET and not (
                0 <= int(challenger) < mask.size and bool(mask[int(challenger)])):
            raise MCRLContractError("the challenger is illegal in the stored state")
        if (int(target) == NO_TARGET) != (int(tag) == TAG_NONE):
            raise MCRLContractError("a row has a target iff its tag is not 'none'")
        if not (0 <= int(action) < mask.size and bool(mask[int(action)])):
            raise MCRLContractError("the executed action is illegal in the stored state")
        super().push(state, action, reward_3, next_state, mask, next_mask, done)
        self._labels.append((int(a_a), int(challenger), int(target), int(tag),
                             bool(override), int(lead_served), float(lead_surrogate)))

    def sample(self, batch_size: int, rng: np.random.Generator):
        """``ReplayBuffer.sample`` statement for statement, plus the labels."""
        indices = rng.choice(len(self._buf), size=batch_size, replace=False)
        batch = [self._buf[i] for i in indices]

        states = np.array([b[0] for b in batch], dtype=np.float32)
        actions = np.array([b[1] for b in batch], dtype=np.int64)
        rewards = np.array([b[2] for b in batch], dtype=np.float32)
        next_states = np.array([b[3] for b in batch], dtype=np.float32)
        masks = np.array([b[4] for b in batch])
        next_masks = np.array([b[5] for b in batch])
        dones = np.array([b[6] for b in batch], dtype=np.float32)

        labels = [self._labels[i] for i in indices]
        target = np.array([x[2] for x in labels], dtype=np.int64)
        a_a = np.array([x[0] for x in labels], dtype=np.int64)
        self._last = {
            "t0_action": a_a,
            # an order-free legal representative for the inherited diagnostics:
            # the target where one exists, else the executed action.  NO LOSS
            # READS IT (the MC2 loss reads judge_target and its weight).
            "teacher_action": np.where(target != NO_TARGET, target, actions),
            "teacher_scores": np.zeros((len(labels), masks.shape[1]), dtype=np.float64),
            "masks": masks,
            "judge_target": target,
            "judge_tag": np.array([x[3] for x in labels], dtype=np.int64),
            "judge_challenger": np.array([x[1] for x in labels], dtype=np.int64),
            "judge_override": np.array([x[4] for x in labels], dtype=bool),
        }
        return states, actions, rewards, next_states, masks, next_masks, dones

    def last_teacher(self) -> dict[str, np.ndarray]:
        if self._last is None:
            raise MCRLContractError("no sample has been drawn yet")
        return self._last

    def label_rows(self) -> list[tuple]:
        return list(self._labels)

    def state_dict(self) -> dict[str, Any]:
        state = super().state_dict()
        state["judge_format_version"] = self._JUDGE_STATE_FORMAT_VERSION
        state["judge_labels"] = [tuple(x) for x in self._labels]
        return state

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        if state.get("judge_format_version") != self._JUDGE_STATE_FORMAT_VERSION:
            raise MCRLContractError("replay state has no MC2 judge labels; refusing to resume")
        labels = state.get("judge_labels")
        if not isinstance(labels, (list, tuple)):
            raise MCRLContractError("judge_labels must be a sequence")
        super().load_state_dict(state)
        if len(labels) != len(self._buf):
            raise MCRLContractError(f"{len(labels)} judge labels for {len(self._buf)} rows")
        self._labels = deque(
            ((int(a), int(c), int(t), int(g), bool(o), int(ls), float(lv))
             for a, c, t, g, o, ls, lv in labels),
            maxlen=self._capacity,
        )
        self._last = None


# ------------------------------------------------------------------ episode log
@dataclass
class EpisodeJudgeLog:
    """Per-episode MC2 diagnostics.  No loss, gradient or target reads any of them."""

    steps: int
    challenger_tag: int = TAG_NONE
    decision_rows: int = 0
    challenger_rows: int = 0
    disagreements_vs_a: int = 0
    compared: int = 0
    overrides: int = 0
    challenger_wins: int = 0
    challenger_wins_c_ne_a: int = 0
    served_decisive_overrides: int = 0
    abstained_final_rows: int = 0
    evaluations: int = 0
    wall_s: float = 0.0
    a_vs_x_pairs: int = 0
    a_above_x: int = 0
    x_above_a: int = 0
    a_x_ties: int = 0
    rows_per_step: list[int] = field(default_factory=list)
    compared_per_step: list[int] = field(default_factory=list)
    overrides_per_step: list[int] = field(default_factory=list)
    tag_per_step: dict[str, list[int]] = field(default_factory=dict)
    override_lead_surrogate: list[float] = field(default_factory=list)
    override_lead_served: list[int] = field(default_factory=list)
    lead_surrogate_by_tag: dict[str, list[float]] = field(default_factory=dict)
    lead_served_by_tag: dict[str, list[int]] = field(default_factory=dict)
    served_decisive_by_tag: dict[str, int] = field(default_factory=dict)
    pushed_by_tag: dict[str, int] = field(default_factory=dict)
    sampled_by_tag: dict[str, int] = field(default_factory=dict)
    loss_by_tag: dict[str, float] = field(default_factory=dict)
    updates: int = 0

    def __post_init__(self) -> None:
        self.rows_per_step = [0] * int(self.steps)
        self.compared_per_step = [0] * int(self.steps)
        self.overrides_per_step = [0] * int(self.steps)
        self.tag_per_step = {n: [0] * int(self.steps) for n in TAG_NAMES}
        self.pushed_by_tag = {n: 0 for n in TAG_NAMES}
        self.sampled_by_tag = {n: 0 for n in TAG_NAMES}
        self.loss_by_tag = {n: 0.0 for n in TAG_NAMES}
        self.lead_surrogate_by_tag = {n: [] for n in TAG_NAMES}
        self.lead_served_by_tag = {n: [] for n in TAG_NAMES}
        self.served_decisive_by_tag = {n: 0 for n in TAG_NAMES}

    def add_step(self, t: int, labels: StepLabels, judge: StepJudge, *,
                 a_a: np.ndarray, x: np.ndarray, abstained: bool,
                 has_challenger_source: bool) -> None:
        dec = labels.decision
        n_dec = int(dec.sum())
        self.decision_rows += n_dec
        self.rows_per_step[t] += n_dec
        if abstained and has_challenger_source:
            self.abstained_final_rows += n_dec
        live = dec & (labels.challenger != NO_TARGET)
        self.challenger_rows += int(live.sum())
        self.disagreements_vs_a += int((live & (labels.challenger != a_a)).sum())
        n_cmp = int(labels.compared.sum())
        self.compared += n_cmp
        self.compared_per_step[t] += n_cmp
        n_ovr = int(labels.override.sum())
        self.overrides += n_ovr
        self.overrides_per_step[t] += n_ovr
        for code, name in enumerate(TAG_NAMES):
            self.tag_per_step[name][t] += int((dec & (labels.tag == code)).sum())
        if self.challenger_tag != TAG_NONE:
            won = dec & (labels.tag == self.challenger_tag)
            self.challenger_wins += int(won.sum())
            # lane B R1-3: B (or R) wins counted only where a^B != a^A (a tie
            # a^A == a^B is an A win by the tie order; by construction this equals
            # challenger_wins, logged separately so it can be checked)
            self.challenger_wins_c_ne_a += int(
                (won & (labels.challenger != np.asarray(a_a))).sum())
        for u in np.flatnonzero(labels.override).tolist():
            # split BY TAG: under v2 a win can be A's or the challenger's, and a
            # pooled lead would mix two different quantities (lane B CODE-READ)
            name = TAG_NAMES[int(labels.tag[u])]
            self.override_lead_surrogate.append(float(labels.lead_surrogate[u]))
            self.override_lead_served.append(int(labels.lead_served[u]))
            self.lead_surrogate_by_tag[name].append(float(labels.lead_surrogate[u]))
            self.lead_served_by_tag[name].append(int(labels.lead_served[u]))
            if int(labels.lead_served[u]) > 0:
                self.served_decisive_overrides += 1
                self.served_decisive_by_tag[name] += 1
        # Diagnostic only: where kappa(a^A) and kappa(x_u) were BOTH evaluated
        # (never forced), how does the judge rank the anchor against the learner?
        base = judge.base()
        for u in np.flatnonzero(dec).tolist():
            a = int(a_a[u])
            if a == int(x[u]) or not judge.evaluated(u, a):
                continue
            k_a = judge.kappa(u, a)
            self.a_vs_x_pairs += 1
            if strictly_better(k_a, base):
                self.a_above_x += 1
            elif strictly_better(base, k_a):
                self.x_above_a += 1
            else:
                self.a_x_ties += 1
        self.evaluations += int(judge.evaluations)
        self.wall_s += float(judge.wall_s)

    def add_push(self, tag: int) -> None:
        self.pushed_by_tag[TAG_NAMES[int(tag)]] += 1

    def add_update(self, stats: Mapping[str, Mapping[str, float]] | None) -> None:
        if stats is None:
            return
        self.updates += 1
        for name in TAG_NAMES:
            self.sampled_by_tag[name] += int(stats["rows"][name])
            self.loss_by_tag[name] += float(stats["loss"][name])

    def as_log(self) -> dict[str, Any]:
        sampled = sum(self.sampled_by_tag.values())
        leads = self.override_lead_surrogate
        return {
            # raw counts (lane B F-1 / R1-3): the denominator is every user-step
            # with >= 1 legal action over ALL t, including t = T-1
            "decision_rows_all_t": int(self.decision_rows),
            "judge_decision_rows": int(self.decision_rows),
            "judge_challenger_wins_c_ne_a": int(self.challenger_wins_c_ne_a),
            "judge_challenger_rows": int(self.challenger_rows),
            "judge_disagreements_vs_a": int(self.disagreements_vs_a),
            "judge_compared": int(self.compared),
            "judge_overrides": int(self.overrides),
            # NOTE: under v2 an "override" is any winner != x_u, so it counts A wins
            # too and is NOT comparable across rules; the contract's clause (vi)
            # quantity is judge_challenger_wins_c_ne_a / decision_rows_all_t.
            "judge_override_rate": float(self.overrides / max(self.decision_rows, 1)),
            "judge_override_rate_per_step": [
                (float(o / r) if r else None)
                for o, r in zip(self.overrides_per_step, self.rows_per_step)
            ],
            "judge_challenger_wins": int(self.challenger_wins),
            "judge_challenger_win_rate": float(
                self.challenger_wins / max(self.decision_rows, 1)),
            "judge_tag_counts": {n: int(sum(v)) for n, v in self.tag_per_step.items()},
            "judge_tag_per_step": {n: list(v) for n, v in self.tag_per_step.items()},
            "judge_rows_per_step": list(self.rows_per_step),
            "judge_compared_per_step": list(self.compared_per_step),
            "judge_overrides_per_step": list(self.overrides_per_step),
            "judge_served_decisive_overrides": int(self.served_decisive_overrides),
            "judge_override_lead_surrogate_mean": (
                float(np.mean(leads)) if leads else None),
            "judge_override_lead_surrogate_median": (
                float(np.median(leads)) if leads else None),
            "judge_override_lead_served_mean": (
                float(np.mean(self.override_lead_served))
                if self.override_lead_served else None),
            "judge_override_lead_surrogate_mean_by_tag": {
                n: (float(np.mean(v)) if v else None)
                for n, v in self.lead_surrogate_by_tag.items()},
            "judge_override_lead_surrogate_median_by_tag": {
                n: (float(np.median(v)) if v else None)
                for n, v in self.lead_surrogate_by_tag.items()},
            "judge_override_lead_served_mean_by_tag": {
                n: (float(np.mean(v)) if v else None)
                for n, v in self.lead_served_by_tag.items()},
            "judge_override_rows_by_tag": {
                n: int(len(v)) for n, v in self.lead_surrogate_by_tag.items()},
            "judge_served_decisive_overrides_by_tag": dict(self.served_decisive_by_tag),
            "judge_abstained_final_rows": int(self.abstained_final_rows),
            "judge_evaluations": int(self.evaluations),
            "judge_wall_s": float(self.wall_s),
            "judge_a_vs_x_pairs": int(self.a_vs_x_pairs),
            "judge_a_above_x": int(self.a_above_x),
            "judge_x_above_a": int(self.x_above_a),
            "judge_a_x_ties": int(self.a_x_ties),
            "judge_pushed_by_tag": dict(self.pushed_by_tag),
            "judge_sampled_rows_by_tag": dict(self.sampled_by_tag),
            "judge_margin_loss_by_tag": dict(self.loss_by_tag),
            "judge_margin_dose": (
                float((sampled - self.sampled_by_tag["none"]) / sampled)
                if sampled else None),
            "judge_updates": int(self.updates),
        }


def finite_or_none(x: float | None) -> float | None:
    return None if x is None or not math.isfinite(float(x)) else float(x)


def source_set_label(sources: Sequence[str]) -> str:
    return "+".join(sources)
