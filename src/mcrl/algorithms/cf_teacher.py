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
``D3-XEP`` (Amendment 12)
    the same margin loss with ``a_T`` replaced by ``T0-XEP``'s action: T0's ordinary
    frozen score computed on the state recorded at step ``t`` of a FIXED pre-recorded
    reference episode, argmax restricted to the learner's CURRENT legal mask.  The
    plausible-but-uninformative second null: same functional form, same
    hyperparameters, same score scale, decorrelated from the current state.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F

from ..env.action_contract import NUM_ACTIONS, no_op_actions
from ..errors import MCRLContractError

MECHANISMS: tuple[str, ...] = ("D0", "D2-T0", "D2-null", "D3-T0", "D3-null", "D3-XEP")
TEACHERS: tuple[str, ...] = ("none", "T0", "random", "T0-XEP")
T0_C: float = 1.0
MASK_FILL: float = -1e9
"""Finite fill for illegal actions (never -inf: 0 * -inf would be NaN)."""


# ------------------------------------------------------------------ T0 labels
def t0_score_matrix(states, c: float = T0_C) -> np.ndarray:
    """``(U, 28)`` float64 T0 scores from the RAW user states -- no mask, no action.

    THE single expression of ``score(a) = log2(1 + max(gamma_a, 0)) - c [N_a == 0]``
    in this tree.  :func:`t0_scores` is this plus the masked argmax, and ``T0-XEP``
    (Amendment 12) is this on a DIFFERENT state with the CURRENT mask's argmax, so
    both teachers are guaranteed to score with the same unmodified arithmetic.
    """
    users = len(states)
    scores = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
    for u, s in enumerate(states):
        gain = np.asarray(s.channel_quality, dtype=np.float64)
        load = np.asarray(s.beam_loads, dtype=np.float64)
        gain_floor = np.maximum(gain, 0.0)
        penalty = c * (load == 0.0).astype(np.float64)
        scores[u] = np.log2(1.0 + gain_floor) - penalty
    return scores


def t0_scores(states, masks, c: float = T0_C):
    """``(U, 28)`` float64 scores, ``(U,)`` int64 actions, ``(U, 28)`` legal mask.

    Statement-for-statement ``lp_common.lp_prev_rule_factory(c, 0)`` /
    ``t0_common.t0_scores`` -- from the RAW user state.
    """
    users = len(states)
    scores = t0_score_matrix(states, c)
    legal_mask = np.zeros((users, NUM_ACTIONS), dtype=bool)
    acts = np.asarray(no_op_actions(users), dtype=np.int64)
    for u in range(users):
        legal = np.asarray(masks[u].mask, dtype=bool)
        legal_mask[u] = legal
        ok = np.flatnonzero(legal)
        if ok.size:
            acts[u] = int(ok[int(np.argmax(scores[u][ok]))])
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


def t0_xep_labels(reference_states, current_mask: np.ndarray, c: float = T0_C):
    """``T0-XEP`` (Amendment 12 section 2): ``(U, 28)`` scores, ``(U,)`` actions.

    T0's ordinary frozen score -- :func:`t0_score_matrix`, ``c = 1``, ``m = 0``,
    unmodified -- computed on ``reference_states`` (step ``t`` of the FIXED
    pre-recorded reference episode), with the resulting argmax restricted to
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
    scores = t0_score_matrix(reference_states, c)
    return scores, masked_argmax_rows(scores, mask)


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
