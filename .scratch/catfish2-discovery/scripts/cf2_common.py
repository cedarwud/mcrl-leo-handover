"""CATFISH2-DISCOVERY Stage 0: candidate rules and shared machinery.

Stage 0 is DISCOVERY ONLY: rollouts and counterfactual diagnostics.  Nothing
here trains, and no optimizer step exists anywhere in this lane.

Namespaces: DEVVAL only (env ``9_211_000+i``, mobility ``9_212_000+i``), enforced
by ``cf_dev.assert_dev_seed_pairs`` inside ``cf_dev.dev_rollout``.

Every candidate below is an exact function of the DEPLOYABLE per-user
observation, i.e. of the four beam-indexed blocks of the 112-dim MODQN state
(``runtime/state_encoding.py::encode_state``):

    block 1  access_vector[28]   one-hot incumbent slot
    block 2  channel_quality[28] nominal SINR gamma_a (linear); encoded log1p
    block 3  beam_offsets[28]    off-axis angle theta (rad)
    block 4  beam_loads[28]      previous-step per-beam demand n_a
                                 (encoded as n_a / num_users)

plus the 113th feature ``(T - t)/T`` added by ``cf_ratio.encode_with_time``.
The rules read the RAW ``UserState`` fields, exactly as ``cf_sources.py`` and
``cf_teacher.t0_scores`` already do; the encoded array is ignored.  ``B_w`` and
``num_users`` are fixed configuration constants, not observations.
"""

from __future__ import annotations

import numpy as np

from mcrl.algorithms import cf_sources as cfs
from mcrl.algorithms import cf_teacher as cft
from mcrl.env.action_contract import NO_OP_ACTION, no_op_actions
from mcrl.env.link_budget import BEAM_BANDWIDTH_HZ

# eta_0, the frozen deployed price (E0 freeze section 2).
ETA0: float = 110_507_234.83444457

# B^w per colour, link_budget.py:28 -- 166.666... MHz.  Configuration constant.
B_W_HZ: float = float(BEAM_BANDWIDTH_HZ)

T0_C: float = 1.0  # cf_teacher.T0_C


def _blocks(state):
    gain = np.asarray(state.channel_quality, dtype=np.float64)
    load = np.asarray(state.beam_loads, dtype=np.float64)
    return gain, load


def spectral_eff(gain: np.ndarray) -> np.ndarray:
    """``log2(1 + max(gamma_a, 0))`` -- the LP family's gain term, verbatim."""
    return np.log2(1.0 + np.maximum(gain, 0.0))


def r_hat(gain: np.ndarray, load: np.ndarray) -> np.ndarray:
    """The user's OWN observation-level predicted share, brief section 1:

        r_hat(a) = (B_w / (n_a + 1)) * log2(1 + gamma_a)

    It approximates the rate this user would receive if it joined beam ``a``
    and the beam's airtime were shared equally by the ``n_a`` users that were
    on it last step plus this user.  What it cannot see: the beam's other
    users' rates (so it is NOT the beam's weakest-user rate), this step's
    simultaneous arrivals and departures, the realised (post-fading,
    post-interference) SINR, and the per-link power feasibility gate.
    """
    return (B_W_HZ / (load + 1.0)) * spectral_eff(gain)


def t0_score(gain: np.ndarray, load: np.ndarray, c: float = T0_C) -> np.ndarray:
    """T0 = LP-prev(c = 1, m = 0): ``log2(1 + gamma_a) - c * [n_a == 0]``."""
    return spectral_eff(gain) - c * (load == 0.0).astype(np.float64)


# --------------------------------------------------------------- candidates
def cq_rule(r_min: float):
    """C-Q -- QoS / rate-tail specialist (brief section 1, verbatim).

    ``argmax_a T0-score(a)`` over ``{a legal : r_hat(a) >= R_min}``;
    if that set is empty, ``argmax_a r_hat(a)`` over the legal actions.
    """

    def fn(states, masks):
        out = no_op_actions(len(states))
        for u, s in enumerate(states):
            legal = np.asarray(masks[u].mask, dtype=bool)
            ok = np.flatnonzero(legal)
            if ok.size == 0:
                continue
            gain, load = _blocks(s)
            rh = r_hat(gain, load)
            clear = ok[rh[ok] >= r_min]
            if clear.size:
                sc = t0_score(gain, load)
                out[u] = int(clear[int(np.argmax(sc[clear]))])
            else:
                out[u] = int(ok[int(np.argmax(rh[ok]))])
        return out

    return fn


def crc_rule(r_min: float):
    """C-RC -- rate-qualified consolidation (brief section 1, verbatim).

    Among candidates clearing ``r_hat(a) >= R_min``, prefer one whose beam was
    already lit (``n_a > 0``), breaking ties by ``log2(1 + gamma_a)``; if no lit
    candidate clears ``R_min``, take ``argmax log2(1 + gamma_a)`` among the
    clearing set; if none clears, take the unrestricted
    ``argmax log2(1 + gamma_a)``.
    """

    def fn(states, masks):
        out = no_op_actions(len(states))
        for u, s in enumerate(states):
            legal = np.asarray(masks[u].mask, dtype=bool)
            ok = np.flatnonzero(legal)
            if ok.size == 0:
                continue
            gain, load = _blocks(s)
            se = spectral_eff(gain)
            clear = ok[r_hat(gain, load)[ok] >= r_min]
            lit = clear[load[clear] > 0.0] if clear.size else clear
            if lit.size:
                out[u] = int(lit[int(np.argmax(se[lit]))])
            elif clear.size:
                out[u] = int(clear[int(np.argmax(se[clear]))])
            else:
                out[u] = int(ok[int(np.argmax(se[ok]))])
        return out

    return fn


def lp_prev_rule(c: float):
    """LP-prev(c, m = 0): the T0 family, used for the decomposition endpoints.

    ``c = 0`` is MAX_NOMINAL_GAIN's arithmetic; ``c = 1`` is T0; ``c -> inf`` is
    B1_NO_NEW_BEAM's arithmetic.
    """

    def fn(states, masks):
        out = no_op_actions(len(states))
        for u, s in enumerate(states):
            legal = np.asarray(masks[u].mask, dtype=bool)
            ok = np.flatnonzero(legal)
            if ok.size == 0:
                continue
            gain, load = _blocks(s)
            sc = t0_score(gain, load, c)
            out[u] = int(ok[int(np.argmax(sc[ok]))])
        return out

    return fn


def raw_policies(r_min: float | None) -> dict:
    """``name -> (states, masks) -> actions``.  The R_min-dependent entries are
    omitted when ``r_min is None`` (used by the R_min-independent lanes)."""
    pol = {
        "T0_LP_prev_c1_m0": lambda st, mk: cft.t0_scores(st, mk)[1],
        "MAX_NOMINAL_GAIN": cfs.max_nominal_gain,
        "B1_NO_NEW_BEAM": cfs.cf3_policies()["C3_B1_NO_NEW_BEAM"],
        "A_m2dB": cfs.cf3_policies()["C1_A_m2dB"],
        "A_m12dB": cfs.cf3_policies()["C2_A_m12dB"],
        "LPend_c0": lp_prev_rule(0.0),
        "LPend_chigh": lp_prev_rule(1.0e9),
    }
    if r_min is not None:
        pol["C_Q"] = cq_rule(r_min)
        pol["C_RC"] = crc_rule(r_min)
    pol.update(a11_policies())
    return pol


def as_rollout_policy(fn):
    """Wrap a ``(states, masks) -> actions`` rule for ``cf_dev.dev_rollout``."""
    return lambda enc, masks, states: fn(states, masks)


# ------------------------------------------- Amendment 11 re-specification
# No absolute rate threshold (Amendment 11 section 1).  The qualifying set is
# defined by the project's own 10th-percentile tail convention applied to the
# very quantity being compared, as a SAME-STEP order statistic.  `np.percentile`
# with the default linear interpolation is the project's existing estimator
# (`cf_dev._rate_stats`, `lp_common._rate_stats` both use `np.percentile(a, 10)`).
TAIL_PCT: float = 10.0


def q10_local(gain: np.ndarray, load: np.ndarray, ok: np.ndarray) -> float:
    """``q10^u(t)``: 10th percentile of ``r_hat_u(a)`` over user u's OWN masked
    candidate actions.  Deployable: it uses nothing but that user's observation."""
    return float(np.percentile(r_hat(gain, load)[ok], TAIL_PCT))


def cq_local_rule():
    """C-Q'-local (Amendment 11 section 2), deployable.

    ``argmax_a T0-score(a)`` over ``{a : r_hat_u(a) >= q10^u(t)}``; if that set is
    empty, ``argmax_a r_hat_u(a)``.
    """

    def fn(states, masks):
        out = no_op_actions(len(states))
        for u, s in enumerate(states):
            legal = np.asarray(masks[u].mask, dtype=bool)
            ok = np.flatnonzero(legal)
            if ok.size == 0:
                continue
            gain, load = _blocks(s)
            rh = r_hat(gain, load)
            q = float(np.percentile(rh[ok], TAIL_PCT))
            clear = ok[rh[ok] >= q]
            if clear.size:
                sc = t0_score(gain, load)
                out[u] = int(clear[int(np.argmax(sc[clear]))])
            else:
                out[u] = int(ok[int(np.argmax(rh[ok]))])
        return out

    return fn


def crc_local_rule():
    """C-RC' (Amendment 11 section 2), deployable, local tail only."""

    def fn(states, masks):
        out = no_op_actions(len(states))
        for u, s in enumerate(states):
            legal = np.asarray(masks[u].mask, dtype=bool)
            ok = np.flatnonzero(legal)
            if ok.size == 0:
                continue
            gain, load = _blocks(s)
            se = spectral_eff(gain)
            rh = r_hat(gain, load)
            q = float(np.percentile(rh[ok], TAIL_PCT))
            clear = ok[rh[ok] >= q]
            lit = clear[load[clear] > 0.0] if clear.size else clear
            if lit.size:
                out[u] = int(lit[int(np.argmax(se[lit]))])
            elif clear.size:
                out[u] = int(clear[int(np.argmax(se[clear]))])
            else:
                out[u] = int(ok[int(np.argmax(se[ok]))])
        return out

    return fn


def q10_global(states, a_t0, served_ref) -> float:
    """``q10(t)``: 10th percentile of ``r_hat`` over the users **T0's own joint
    action serves at that step** -- a cross-user order statistic, therefore NOT
    deployable.  ``served_ref`` is ``resolution.served`` from evaluating T0's
    joint action at that step (the `oracle_cells.py::best_response_step`
    reference assignment).  Returns ``-inf`` when T0 serves nobody, which makes
    the restriction vacuous rather than undefined.
    """
    vals = []
    for u, s in enumerate(states):
        if not bool(served_ref[u]):
            continue
        a = int(a_t0[u])
        if a < 0:
            continue
        gain, load = _blocks(s)
        vals.append(float(r_hat(gain, load)[a]))
    if not vals:
        return float("-inf")
    return float(np.percentile(np.asarray(vals, dtype=np.float64), TAIL_PCT))


def cq_global_actions(states, masks, q: float) -> np.ndarray:
    """C-Q'-global's action vector at one step, given that step's ``q10(t)``."""
    out = no_op_actions(len(states))
    for u, s in enumerate(states):
        legal = np.asarray(masks[u].mask, dtype=bool)
        ok = np.flatnonzero(legal)
        if ok.size == 0:
            continue
        gain, load = _blocks(s)
        rh = r_hat(gain, load)
        clear = ok[rh[ok] >= q]
        if clear.size:
            sc = t0_score(gain, load)
            out[u] = int(clear[int(np.argmax(sc[clear]))])
        else:
            out[u] = int(ok[int(np.argmax(rh[ok]))])
    return out


def a11_policies() -> dict:
    """The Amendment 11 deployable candidates (C-Q'-global needs the env)."""
    return {"C_Q_local": cq_local_rule(), "C_RC_local": crc_local_rule()}
