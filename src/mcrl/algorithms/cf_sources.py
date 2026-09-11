"""Scripted experience sources for the three-catfish pilot (CF3PILOT, 2026-09-11).

Declaration: ``.scratch/multi-catfish-v025-physics-successor/
V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md``.

The three rules are ported from FEASFRONT's
``.scratch/feasible-frontier/scripts/frontier.py`` (``incumbent_slot``,
``pick``, ``make_rule``, ``r_no_new_beam``) **with its fallback fix**: at
``margin_db <= 0`` the choice is the plain restricted argmax with NO incumbent
preference, so a family restriction is never silently undone by an incumbent
hold (the defect FEASFRONT caught in its smoke test, where B1 and B2 produced
identical actions).  The logic below is statement-for-statement that file's;
only the calling convention differs (``(states, masks) -> actions``).

| catfish | rule            | information               | feeds head |
|---------|-----------------|---------------------------|------------|
| C1      | ``A m=2dB``     | gain                      | ``Q_B``    |
| C2      | ``A m=12dB``    | gain + incumbent memory   | ``Q_H``    |
| C3      | ``B1_NO_NEW_BEAM`` | previous-step loads + gain | ``Q_E`` |

NULL3 replaces each rule with a uniformly random **legal** action drawn from
the source's own generator (never the trainer's), so the main agent's RNG
streams are untouched by any source.

Every rule reads only the 112-dim observation's raw blocks at decision time:
block 1 ``access_vector`` (incumbent slot), block 2 ``channel_quality``
(nominal gain / SINR proxy), block 4 ``beam_loads`` (``N_u(t-1)``).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np

from ..env.action_contract import NO_OP_ACTION, NUM_ACTIONS, no_op_actions
from ..env.step_types import ActionMask, UserState

SourcePolicy = Callable[[Sequence[UserState], Sequence[ActionMask]], np.ndarray]


# ---------------------------------------------------------------- primitives
def incumbent_slot(state: UserState) -> int:
    """Slot of the incumbent in the CURRENT candidate ordering, or -1."""
    inc = np.flatnonzero(np.asarray(state.access_vector) > 0.5)
    return int(inc[0]) if inc.size else -1


def pick(
    gain: np.ndarray,
    legal: np.ndarray,
    allowed: np.ndarray,
    inc: int,
    margin_db: float,
) -> int:
    """One user's choice (frontier.py ``pick``, post-fix).

    Fallback order: restricted-and-legal, then legal-unrestricted.  At
    ``margin_db <= 0`` there is no incumbent preference.  Hysteresis: the
    incumbent is held unless the best allowed legal challenger's nominal gain
    exceeds the incumbent's by ``margin_db`` dB.
    """
    ok = np.flatnonzero(legal & allowed)
    if ok.size == 0:
        ok = np.flatnonzero(legal)
        if ok.size == 0:
            return NO_OP_ACTION
    best = int(ok[int(np.argmax(gain[ok]))])
    if margin_db <= 0.0:
        return best
    if inc >= 0 and legal[inc]:
        if gain[best] > gain[inc] * (10.0 ** (margin_db / 10.0)):
            return best
        return inc
    return best


def r_no_new_beam(gain, load, inc, legal) -> np.ndarray:
    """B1: options whose beam carried demand last step (lights no new beam)."""
    return load > 0.5


def make_rule(margin_db: float = 0.0, restrict=None) -> SourcePolicy:
    """``restrict(gain, load, inc, legal) -> bool[28]`` allow-mask or None."""

    def fn(states: Sequence[UserState], masks: Sequence[ActionMask]) -> np.ndarray:
        out = no_op_actions(len(states))
        for u, s in enumerate(states):
            gain = np.asarray(s.channel_quality, dtype=np.float64)
            load = np.asarray(s.beam_loads, dtype=np.float64)
            legal = np.asarray(masks[u].mask, dtype=bool)
            inc = incumbent_slot(s)
            allowed = (
                np.ones(NUM_ACTIONS, dtype=bool)
                if restrict is None
                else restrict(gain, load, inc, legal)
            )
            out[u] = pick(gain, legal, allowed, inc, margin_db)
        return out

    return fn


def max_nominal_gain(states, masks) -> np.ndarray:
    """``MAX_NOMINAL_GAIN`` (= ``A m=0dB``): masked argmax of nominal gain.

    Same arithmetic as ``scripts/b0_pooled_ee_eval.py::arm_maxgain``
    (``argmax_masked`` over ``channel_quality``).
    """
    out = no_op_actions(len(masks))
    for u in range(len(masks)):
        valid = np.where(masks[u].mask)[0]
        if valid.size:
            q = np.asarray(states[u].channel_quality)
            out[u] = int(valid[int(np.argmax(q[valid]))])
    return out


def random_legal(rng: np.random.Generator) -> SourcePolicy:
    """NULL source: uniform over each user's legal actions, own generator."""

    def fn(states, masks) -> np.ndarray:
        out = no_op_actions(len(masks))
        for u in range(len(masks)):
            valid = np.where(masks[u].mask)[0]
            if valid.size:
                out[u] = int(rng.choice(valid))
        return out

    return fn


# Head indices of the new learner, fixed: (B, E, H).
HEAD_B, HEAD_E, HEAD_H = 0, 1, 2
HEAD_NAMES = ("Q_B", "Q_E", "Q_H")

# Declared routing: catfish -> head.
CF3_SPECS: tuple[tuple[str, int], ...] = (
    ("C1_A_m2dB", HEAD_B),
    ("C2_A_m12dB", HEAD_H),
    ("C3_B1_NO_NEW_BEAM", HEAD_E),
)


def cf3_policies() -> dict[str, SourcePolicy]:
    return {
        "C1_A_m2dB": make_rule(margin_db=2.0),
        "C2_A_m12dB": make_rule(margin_db=12.0),
        "C3_B1_NO_NEW_BEAM": make_rule(restrict=r_no_new_beam),
    }
