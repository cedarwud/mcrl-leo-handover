"""T0 teacher and the E0 teacher-injection losses (DEVHARNESS, development lane).

Governing: ``.scratch/multi-catfish-v025-physics-successor/
V025-CONTROLLER-AMENDMENT-6-DEVELOPMENT-FIRST-TRAINING-2026-09-12.md`` (a copy is
in ``docs/dev-e0/``), sections 2, 5 and 6.  **Development lane**: nothing computed
with this module is formal screening evidence.

Teacher **T0 = LP-prev(c = 1, m = 0)**, the non-privileged anchor teacher verified in
``.scratch/h4-probe/LP-PROBE-2026-09-11.md`` and re-verified bit-for-bit by T0REPR::

    score(a) = log2(1 + max(gamma_a, 0)) - c * [N_a == 0],   c = 1

``gamma_a`` = the RAW ``UserState.channel_quality`` (nominal SINR of candidate slot
``a``), ``N_a`` = the RAW ``UserState.beam_loads[a]`` (previous-step user count on
that beam).  The action is the masked argmax, **first index on ties**
(``np.argmax`` over the legal subset); ``m = 0`` means there is no incumbent hold.
Both the action and the 28-score vector are computed from the RAW user state at
collection time -- never from the log1p-encoded observation (whose float32 SINR
block reproduces the action but not the score: T0REPR measured 2.4e-7 relative
error on the decode).

Mechanisms (Amendment 6 section 2), all on the deployed scalar score
``S(s, a) = Q~_B - eta~ Q~_E - lambda Q~_H`` (``lambda = 0`` in E0):

``D0``
    no teacher.
``D2`` (primary; on-student-state soft distillation)
    ``alpha * CE(softmax(T0 scores / tau) , softmax(S / tau_s))`` over the LEGAL
    actions of the student-visited state.
``D2-null``
    identical, with T0's score vector randomly permuted **among the legal actions
    of that state** (DEV-NULL generator).  Dimensions, masks and schedule are
    preserved; which action carries which score is destroyed.
``D3`` (DQfD-style unconditional large margin)
    ``lambda_E * (max_a [S(s, a) + m * 1(a != a_T)] - S(s, a_T))`` over legal
    actions.
``D3-null``
    the same margin loss with ``a_T`` replaced by a seeded uniform random LEGAL
    action (DEV-NULL generator) -- the matched null for "does D3's gain need T0's
    action", with no T0 quantity in any loss input.
``D3-multi`` (Amendment 15 section 6 / Amendment 14 section 8)
    the GENERIC N-teacher SET-VALUED large margin.  With
    ``A_CF(s) = unique({a_T0, a_Ti, ...})`` restricted to the CURRENTLY LEGAL
    actions of that state::

        L_multi = max_{a legal} [ S(s,a) + m * 1(a not in A_CF) ]
                  - max_{a in A_CF} S(s,a)

    at the frozen ``m = 0.15`` and the unchanged ``lambda_E = 1``.  **There are no
    teacher weights** -- not 0.5/0.5, not any: the set is a set, every member is an
    acceptable target, and the learner's own score decides which member it prefers.
    With ``|A_CF| = 1`` the expression is the single-teacher D3 above, and
    :func:`d3_set_margin_loss` is bit-identical to :func:`d3_margin_loss` in both
    the loss tensor and the gradient (``tests/test_cf_multid3.py``).
``D3-multi-null``
    the MATCHED set-valued null for a ``D3-multi`` arm of cardinality ``n``: the
    same set-valued margin loss whose ``A_CF`` is ``n`` DISTINCT legal actions drawn
    WITHOUT REPLACEMENT from the arm's own declared DEV-NULL stream (cardinality one
    when only one legal action exists).  Comparing an ``n``-teacher set-valued loss
    against the one-action ``D3-null`` is NOT a matched comparison: a set of size
    two is mechanically easier to satisfy than a set of size one.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F

from ..env.action_contract import NUM_ACTIONS, no_op_actions
from ..errors import MCRLContractError

SINGLE_MECHANISMS: tuple[str, ...] = ("D0", "D2-T0", "D2-null", "D3-T0", "D3-null")
MULTI_MECHANISMS: tuple[str, ...] = ("D3-multi", "D3-multi-null")
MECHANISMS: tuple[str, ...] = SINGLE_MECHANISMS + MULTI_MECHANISMS
TEACHERS: tuple[str, ...] = ("none", "T0", "random", "multi", "random-set")
T0_C: float = 1.0
MASK_FILL: float = -1e9
"""Finite fill for illegal actions (never -inf: 0 * -inf would be NaN)."""

MULTI_MECHANISM_ID: str = "MULTI-D3-SETVALUED-v1"
"""Canonical identity of the generic N-teacher set-valued MULTI-D3 mechanism.

It is a VERSIONED identity and it goes into the configuration hash: a change to
the loss, to how ``A_CF`` is built, or to the legality rule is a different
mechanism and must be a different string, never a silent edit under this one.
"""

MULTI_NULL_ID: str = "RANDOM-LEGAL-SET-NO-REPLACEMENT-v1"
"""Canonical identity of the DECLARED matched set-valued null's proposal rule.

Amendment 14 section 8 / Amendment 15 section 6: ``n`` distinct legal actions
without replacement when at least ``n`` exist, cardinality one when only one legal
action exists.  This is the null that is registered as an arm.
"""

MULTI_NULL_BERNOULLI_ID: str = "RANDOM-LEGAL-SET-BERNOULLI-MATCHED-v1"
"""IMPLEMENTED BUT NOT SELECTED -- the cardinality-matched variant.

Amendment 15 section 6 keeps the two-proposal semantics "unless a test demonstrates
an actual matching defect".  ``tests/test_cf_multid3.py`` demonstrates the defect
MECHANISM prospectively: a FULL arm's ``|A_CF|`` is 1 whenever its teachers name the
same action, while the declared null's is 1 only when the state has a single legal
action, so the two cardinality distributions cannot agree for any teacher pair with
a non-zero agreement rate -- and Amendment 15 section 5 only requires disagreement
>= 0.25, i.e. agreement up to 0.75.

This variant collapses to cardinality one with a DECLARED marginal probability
``p_singleton``, measured on the frozen P0 collection BEFORE any training and put in
the configuration hash.  It leaks only that one pre-declared marginal, never
per-state teacher information.  **It is not registered as an arm and must not be
used unless the controller selects it -- before k = 8, never after a learner
result.**
"""

EMPTY_SLOT: int = -1
"""Padding in a teacher-action slot row: 'this slot proposed nothing'."""


# ------------------------------------------------------------------ T0 labels
def t0_scores(states, masks, c: float = T0_C):
    """``(U, 28)`` float64 scores, ``(U,)`` int64 actions, ``(U, 28)`` legal mask.

    Statement-for-statement ``lp_common.lp_prev_rule_factory(c, 0)`` /
    ``t0_common.t0_scores`` -- from the RAW user state.
    """
    users = len(states)
    scores = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
    legal_mask = np.zeros((users, NUM_ACTIONS), dtype=bool)
    acts = np.asarray(no_op_actions(users), dtype=np.int64)
    for u, s in enumerate(states):
        legal = np.asarray(masks[u].mask, dtype=bool)
        gain = np.asarray(s.channel_quality, dtype=np.float64)
        load = np.asarray(s.beam_loads, dtype=np.float64)
        gain_floor = np.maximum(gain, 0.0)
        penalty = c * (load == 0.0).astype(np.float64)
        score = np.log2(1.0 + gain_floor) - penalty
        scores[u] = score
        legal_mask[u] = legal
        ok = np.flatnonzero(legal)
        if ok.size:
            acts[u] = int(ok[int(np.argmax(score[ok]))])
    return scores, acts, legal_mask


def t0_policy():
    """T0 as a ``pooled_rollout`` policy (reads the raw states, no generator)."""

    def pol(enc, masks, states):
        return t0_scores(states, masks)[1]

    return pol


def masked_argmax_rows(scores: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Row-wise masked argmax, first index on ties; ``NO_OP`` for an empty row."""
    scores = np.asarray(scores, dtype=np.float64)
    out = np.asarray(no_op_actions(scores.shape[0]), dtype=np.int64)
    for u in range(scores.shape[0]):
        ok = np.flatnonzero(mask[u])
        if ok.size:
            out[u] = int(ok[int(np.argmax(scores[u][ok]))])
    return out


def permute_scores_among_legal(
    scores: np.ndarray, mask: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    """DEV-NULL: per row, permute the score VALUES among that row's LEGAL slots.

    Illegal slots keep their own values (they are masked out of every loss), so
    the permutation can neither move a legal score onto an illegal slot nor the
    reverse.  One permutation per state, drawn at collection time from the
    DEV-NULL generator only.
    """
    out = np.array(scores, dtype=np.float64, copy=True)
    for u in range(out.shape[0]):
        idx = np.flatnonzero(mask[u])
        if idx.size > 1:
            out[u, idx] = np.asarray(scores[u], dtype=np.float64)[idx][
                rng.permutation(idx.size)
            ]
    return out


def random_legal_actions(mask: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """DEV-NULL: one uniform LEGAL action per row, drawn from ``rng`` only.

    The matched null for D3: the margin loss keeps its shape, weight, margin,
    schedule, mask and gradient path, and only the action it points at changes --
    from T0's to a seeded random legal one, which carries no T0 information at all
    (the same draw ``cf_sources.random_legal`` makes for the NULL3 sources).
    """
    mask = np.asarray(mask, dtype=bool)
    out = np.asarray(no_op_actions(mask.shape[0]), dtype=np.int64)
    for u in range(mask.shape[0]):
        valid = np.flatnonzero(mask[u])
        if valid.size:
            out[u] = int(rng.choice(valid))
    return out


# ------------------------------------------------- generic teacher-source registry
def t0_actions(states, masks) -> np.ndarray:
    """T0's action per user -- T0 exposed through the generic source protocol."""
    return t0_scores(states, masks)[1]


TeacherSource = Callable[..., np.ndarray]
"""A teacher source is ``(states, masks) -> (U,) int64 currently-legal actions``.

The MULTI-D3 mechanism is AGNOSTIC to what produced an action: a source may be a
rule, a counterfactual evaluation, a lookahead, or anything else, as long as it
returns one legal action per user from the state it is given and consumes no
learner generator.  Nothing about a source's provenance reaches the loss.

A source registered with ``needs_context=True`` is additionally handed the
TRAINING-ONLY :class:`TeacherContext` as a keyword: the live scenario driver, the
current ``StepObservation.candidates`` and the step / final-step identity.  These
already exist in the frozen trainer environment (``TrainerEnvironment.reset``
already returns the observation and the trainer merely discarded it); the seam is
additive and **training only**.  It does not touch the 113-dim learner
observation, the replay state, the network, the inference or deployment path, the
environment physics or the RNG schedule, and a source that does not ask for it --
``T0`` and every other existing source -- is called exactly as before.
"""


@dataclass(frozen=True)
class TeacherContext:
    """What a privileged TRAINING-TIME source may read about the live step.

    Read-only by contract.  A source that mutates the driver, consumes a generator
    or advances the environment violates Amendment 15 section 2A clause 3, and the
    source-identity receipt (Lane M) is what proves it did not.
    """

    driver: Any
    candidates: Any
    step_index: int
    is_final_step: bool


_TEACHER_SOURCES: dict[str, tuple[TeacherSource, bool]] = {"T0": (t0_actions, False)}


def register_teacher_source(
    name: str, fn: TeacherSource, *, replace: bool = False, needs_context: bool = False
) -> None:
    """Register a candidate teacher under its CANONICAL identity.

    The identity string is what lands in the configuration hash, so it must be
    stable and it may not be silently rebound: re-registering an existing name is
    a contract error unless ``replace=True`` is asked for explicitly.
    """
    key = str(name)
    if not key or any(ch in key for ch in "+, \t\n/"):
        raise MCRLContractError(f"teacher identity {name!r} is not a canonical name")
    if key in _TEACHER_SOURCES and not replace:
        raise MCRLContractError(f"teacher {key!r} is already registered")
    if not callable(fn):
        raise MCRLContractError(f"teacher {key!r} is not callable")
    _TEACHER_SOURCES[key] = (fn, bool(needs_context))


def unregister_teacher_source(name: str) -> None:
    """Remove a registered source (used by the deployment-independence tests)."""
    _TEACHER_SOURCES.pop(str(name), None)


def teacher_source(name: str) -> TeacherSource:
    return _teacher_entry(name)[0]


def teacher_needs_context(name: str) -> bool:
    return _teacher_entry(name)[1]


def any_teacher_needs_context(names: Iterable[str]) -> bool:
    return any(teacher_needs_context(n) for n in names)


def _teacher_entry(name: str) -> tuple[TeacherSource, bool]:
    try:
        return _TEACHER_SOURCES[str(name)]
    except KeyError:
        raise MCRLContractError(
            f"teacher {name!r} is not registered; registered: "
            f"{tuple(sorted(_TEACHER_SOURCES))}"
        ) from None


def registered_teachers() -> tuple[str, ...]:
    return tuple(sorted(_TEACHER_SOURCES))


def canonical_teacher_set(names: Iterable[str]) -> tuple[str, ...]:
    """The canonical, order-free identity of a teacher SET.

    Sorted and duplicate-free, so ``{T0, Ti}`` and ``{Ti, T0}`` are the SAME
    configuration and hash to the same value -- the identity mirrors the loss's
    permutation invariance instead of merely happening to agree with it.  A
    repeated identity is a configuration error (a repeated *action* at run time is
    a different thing and collapses silently, as it must).  Availability is NOT
    checked here: an identity may be declared before its source is registered.
    """
    listed = [str(n) for n in names]
    if not listed:
        raise MCRLContractError("a MULTI-D3 teacher set may not be empty")
    for n in listed:
        if not n or any(ch in n for ch in "+, \t\n/"):
            raise MCRLContractError(f"teacher identity {n!r} is not a canonical name")
    if len(set(listed)) != len(listed):
        raise MCRLContractError(f"teacher set {tuple(listed)} repeats an identity")
    return tuple(sorted(listed))


def teacher_action_slots(
    names: Sequence[str], states, masks, *,
    cache: Mapping[str, np.ndarray] | None = None,
    context: "TeacherContext | None" = None,
) -> np.ndarray:
    """``(U, len(names))`` int64: each teacher's action, one column per teacher.

    Columns follow ``names``; the SET built from them does not (see
    :func:`membership_from_slots`).  ``cache`` lets a caller hand in an action
    column it has already computed for its own diagnostics (T0's, typically) so
    the same source is never evaluated twice in a step.  ``context`` is passed
    ONLY to sources registered with ``needs_context=True``; every other source is
    called with the historical two-argument signature and is bit-for-bit
    unaffected.
    """
    cache = dict(cache or {})
    cols: list[np.ndarray] = []
    for name in names:
        col = cache.get(str(name))
        if col is None:
            fn, needs = _teacher_entry(name)
            if needs:
                if context is None:
                    raise MCRLContractError(
                        f"teacher {name!r} needs the training-time TeacherContext "
                        "(live driver, current candidates, final-step flag) and none "
                        "was supplied; it cannot be evaluated on this path"
                    )
                col = fn(states, masks, context=context)
            else:
                col = fn(states, masks)
        col = np.asarray(col, dtype=np.int64)
        if col.shape != (len(states),):
            raise MCRLContractError(
                f"teacher {name!r} returned {col.shape}, expected {(len(states),)}"
            )
        cols.append(col)
    if not cols:
        raise MCRLContractError("a MULTI-D3 teacher set may not be empty")
    return np.stack(cols, axis=1)


def membership_from_slots(slots: np.ndarray, legal_mask: np.ndarray) -> np.ndarray:
    """``(U, 28)`` boolean ``A_CF`` from a ``(U, n_slots)`` row of proposals.

    Three properties are STRUCTURAL here rather than incidental, which is why the
    set is carried as a membership mask and never as a list:

    * **deduplication** -- two teachers proposing the same action set the same bit;
    * **order invariance** -- the mask does not record which slot set which bit;
    * **legality** -- only CURRENTLY legal actions may enter; an illegal proposal is
      dropped from the set, never admitted and never turned into a target.

    ``EMPTY_SLOT`` (-1) means the slot proposed nothing.  A row with no legal action
    at all yields an all-false row (such rows are never pushed to the replay); a row
    that HAS legal actions but ends up with an empty set is a contract error.
    """
    slots = np.asarray(slots, dtype=np.int64)
    legal = np.asarray(legal_mask, dtype=bool)
    if slots.ndim != 2 or legal.ndim != 2 or slots.shape[0] != legal.shape[0]:
        raise MCRLContractError(
            f"slots {slots.shape} and legal mask {legal.shape} do not line up"
        )
    member = np.zeros_like(legal)
    for u in range(slots.shape[0]):
        if not bool(legal[u].any()):
            continue
        for a in slots[u]:
            a = int(a)
            if a == EMPTY_SLOT:
                continue
            if not 0 <= a < legal.shape[1]:
                raise MCRLContractError(f"teacher proposed action {a} outside 0..{legal.shape[1] - 1}")
            if bool(legal[u, a]):
                member[u, a] = True
        if not bool(member[u].any()):
            raise MCRLContractError(
                "A_CF is empty in a state that has legal actions: every teacher "
                "proposed an illegal action"
            )
    return member


def random_legal_action_slots(
    mask: np.ndarray, rng: np.random.Generator, n_proposals: int,
    *, p_singleton: float | None = None,
) -> np.ndarray:
    """The MATCHED set-valued null's proposals: ``(U, n_proposals)`` int64.

    Per row, ``min(n_proposals, n_legal)`` DISTINCT legal actions drawn WITHOUT
    REPLACEMENT from ``rng`` alone (Amendment 14 section 8 / Amendment 15 section 6),
    padded with :data:`EMPTY_SLOT`.  When only one legal action exists the set has
    cardinality one.  Exactly one generator call per row with a legal action, the
    same schedule as :func:`random_legal_actions`, so the null's stream is a
    declared identity and nothing else.

    ``p_singleton`` selects the NOT-SELECTED cardinality-matched variant
    (:data:`MULTI_NULL_BERNOULLI_ID`): a row that has at least two legal actions
    collapses to cardinality one with that declared marginal probability, drawn from
    the SAME stream immediately before the action draw.  It changes the stream, so it
    is a different null identity and a different configuration hash.
    """
    mask = np.asarray(mask, dtype=bool)
    n = int(n_proposals)
    if n < 1:
        raise MCRLContractError("the matched set-valued null needs >= 1 proposal")
    if p_singleton is not None and not 0.0 <= float(p_singleton) <= 1.0:
        raise MCRLContractError("p_singleton must be a probability")
    out = np.full((mask.shape[0], n), EMPTY_SLOT, dtype=np.int64)
    for u in range(mask.shape[0]):
        valid = np.flatnonzero(mask[u])
        if not valid.size:
            continue
        k = min(n, int(valid.size))
        if p_singleton is not None and k > 1 and float(rng.random()) < float(p_singleton):
            k = 1
        drawn = rng.choice(valid, size=k, replace=False)
        out[u, :k] = np.asarray(drawn, dtype=np.int64)
    return out


def set_cardinalities(member: np.ndarray) -> np.ndarray:
    """``(U,)`` int: ``|A_CF|`` per row (0 where the row has no legal action)."""
    return np.asarray(member, dtype=bool).sum(axis=1).astype(np.int64)


def cardinality_histogram(member: np.ndarray, n_slots: int) -> list[int]:
    """Counts of ``|A_CF| = 0, 1, ..., n_slots`` -- the quantity a matched null
    must reproduce, and a required report field (Amendment 15 section 7)."""
    card = set_cardinalities(member)
    return [int((card == c).sum()) for c in range(int(n_slots) + 1)]


def duplicate_slot_fraction(slots: np.ndarray, member: np.ndarray) -> float:
    """Fraction of rows where the proposals collapsed (``|A_CF| < filled slots``).

    Amendment 15 section 7's "duplicate-teacher frequency": how often the teachers
    named the same action, measured on rows that have at least one legal action.
    """
    slots = np.asarray(slots, dtype=np.int64)
    card = set_cardinalities(member)
    filled = (slots != EMPTY_SLOT).sum(axis=1)
    rows = np.flatnonzero(np.asarray(member, dtype=bool).any(axis=1))
    if not rows.size:
        return 0.0
    return float((card[rows] < filled[rows]).mean())


def soft_targets(scores: np.ndarray, mask: np.ndarray, tau: float) -> np.ndarray:
    """``softmax(score / tau)`` over the legal actions; 0 on illegal ones.

    Statement-for-statement T0REPR's ``t0_clone.soft_targets`` (the fit whose VAL
    selection chose ``tau = 3``).
    """
    if not (np.isfinite(tau) and tau > 0):
        raise MCRLContractError("tau must be finite and positive")
    scores = np.asarray(scores, dtype=np.float64)
    mask = np.asarray(mask, dtype=bool)
    z = np.where(mask, scores / tau, -np.inf)
    z = z - z.max(1, keepdims=True)
    p = np.where(mask, np.exp(z), 0.0)
    p /= p.sum(1, keepdims=True)
    return p.astype(np.float32)


# ------------------------------------------------------------------ student
def student_scores(
    q_b: torch.Tensor, q_e: torch.Tensor, q_h: torch.Tensor,
    eta_tilde: float, lam: float,
) -> torch.Tensor:
    """The DEPLOYED scalar score ``S = Q~_B - eta~ Q~_E - lambda Q~_H``.

    Same combination as ``CFRatioTrainer._combine`` (the rule that acts), so the
    teacher losses shape exactly the quantity the greedy policy ranks.  With the
    E0 ``lambda = 0`` the ``Q_H`` term is identically zero and no teacher gradient
    reaches ``Q_H``.
    """
    return q_b - eta_tilde * q_e - lam * q_h


# ------------------------------------------------------------------ losses
def d2_ce_loss(
    scores: torch.Tensor, mask: torch.Tensor, p_target: torch.Tensor, tau_s: float
) -> torch.Tensor:
    """``CE(p_target, softmax(S / tau_s))`` over legal actions, mean over rows.

    ``p_target`` must be zero on illegal actions (``soft_targets`` guarantees it),
    so illegal actions contribute nothing; the log-softmax normalises over the
    legal set only (illegal logits are pushed to ``MASK_FILL``).
    """
    if not (np.isfinite(tau_s) and tau_s > 0):
        raise MCRLContractError("tau_s must be finite and positive")
    logits = (scores / tau_s).masked_fill(~mask, MASK_FILL)
    log_q = F.log_softmax(logits, dim=1)
    return -(p_target * log_q).sum(dim=1).mean()


def d3_margin_loss(
    scores: torch.Tensor, mask: torch.Tensor, a_teacher: torch.Tensor, margin: float
) -> torch.Tensor:
    """``mean_s [ max_{a legal} (S(s,a) + m 1(a != a_T)) - S(s, a_T) ]`` (>= 0).

    The teacher action must be legal in its own state (it is the masked argmax of
    the teacher's scores on that state's mask); a violation is a contract error,
    never a silently clipped loss.
    """
    if margin < 0:
        raise MCRLContractError("margin must be >= 0")
    a_col = a_teacher.view(-1, 1)
    if not bool(mask.gather(1, a_col).all()):
        raise MCRLContractError("D3: the teacher action is illegal in its state")
    marg = torch.full_like(scores, float(margin))
    marg.scatter_(1, a_col, 0.0)
    q = (scores + marg).masked_fill(~mask, MASK_FILL)
    return (q.max(dim=1).values - scores.gather(1, a_col).squeeze(1)).mean()


def d3_set_margin_loss(
    scores: torch.Tensor, mask: torch.Tensor, member: torch.Tensor, margin: float
) -> torch.Tensor:
    """``mean_s [ max_{a legal}(S + m 1(a not in A_CF)) - max_{a in A_CF} S ]`` (>= 0).

    The generic N-teacher MULTI-D3 of Amendment 15 section 6.  ``member`` is the
    boolean ``A_CF`` membership mask of :func:`membership_from_slots`, so the loss
    never sees how many teachers there were, in what order they ran, or which of
    them proposed what: **there are no teacher weights anywhere in this function.**

    Written to be bit-identical to :func:`d3_margin_loss` when ``|A_CF| = 1``:

    * the margin tensor is the same ``full_like(margin)`` with zeros written at the
      set's members (one member reproduces the single ``scatter_``);
    * the first term is the SAME ``(scores + marg).masked_fill(~mask).max(dim=1)``;
    * the second term is ``max`` over the set instead of ``gather`` at one action,
      and with one member the ``max`` returns that member's score exactly and
      routes exactly the same unit gradient to it.

    An illegal member is a contract error, never a silently clipped loss: an
    illegal action can never become a target.
    """
    if margin < 0:
        raise MCRLContractError("margin must be >= 0")
    if member.shape != scores.shape or mask.shape != scores.shape:
        raise MCRLContractError(
            f"MULTI-D3: A_CF {tuple(member.shape)} / mask {tuple(mask.shape)} do not "
            f"match the scores {tuple(scores.shape)}"
        )
    if bool((member & ~mask).any()):
        raise MCRLContractError("MULTI-D3: an illegal action is in A_CF")
    if not bool(member.any(dim=1).all()):
        raise MCRLContractError("MULTI-D3: A_CF is empty in some state")
    marg = torch.full_like(scores, float(margin))
    marg.masked_fill_(member, 0.0)
    q = (scores + marg).masked_fill(~mask, MASK_FILL)
    best_in_set = scores.masked_fill(~member, MASK_FILL).max(dim=1).values
    return (q.max(dim=1).values - best_in_set).mean()
