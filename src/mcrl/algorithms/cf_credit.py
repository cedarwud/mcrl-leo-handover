"""B1 credit for the CF-ratio learner: difference reward and analytic lighting price.

Brief: ``.scratch/b1-credit/PROMPT.md``.  Governing: ruling 2 section 3, stage **B1**
(``.scratch/multi-catfish-v025-physics-successor/
V025-CONTROLLER-RULING-CEILING-PARITY-B-CHAIN-AND-CATFISH-COUNT-2026-09-11.md``) and its
Amendments 1 (oracle-first screen) and 2.  Engineering lane: this module scores
steps, it never trains anything.

``CFRatioSettings.credit_mode`` selects how a user-step's ``(B, E)`` heads are
credited.  ``H`` (inter-satellite handover indicator) is the same in every mode.

``equal_share`` (default; CF3 as run)
    ``B_u = R_u dt`` (0 when unserved), ``E_u = P_sys dt / U``.  Implemented by
    :func:`mcrl.algorithms.cf_ratio.cf_reward_matrix`, which this module does
    not touch.

``difference``
    ``B_u^D = bits(a) - bits(a without u)`` and ``E_u^D = joules(a) - joules(a
    without u)``, both from the environment's own counterfactual evaluator
    (:meth:`StepEnvironment.evaluate_actions` /
    :meth:`~StepEnvironment.evaluate_actions_without_user`) on the pre-step
    state.  Common random numbers are exact: the evaluator deep-copies
    ``env_rng`` and the fading/shadowing draw is per satellite over the union
    of the candidate windows, which does not depend on the action vector; the
    evaluator restores the only state ``_resolve_physics`` writes (segments)
    and classifies handovers without advancing the ledgers.  The evaluator's
    base vector is asserted equal to the committed step (ruling 2 section 1
    parity) every step.

``lighting_price``
    ``B_u = R_u dt`` (own bits, as CF3); ``E_u`` = u's marginal joules from the
    power model, no counterfactual: the beam's supply-power change if u is its
    unique max-power user, the beam's circuit power if u is alone on the beam,
    the satellite's baseband if u is the only served user of its satellite.
    The LP(c, m) rule family is the greedy (one-step, own-bits) version of
    this credit.

What "without u" does (read from ``env/step.py``, ``service.py``,
``link_budget.py``, ``interference.py``; each item is asserted by
``tests/test_cf_credit.py``):

* u's own bits disappear.
* **Bandwidth share.**  A beam is time-shared, ``R_v = (B_w / U_b) log2(1 + g_v)``;
  u's beam-mates go from ``U_b`` to ``U_b - 1`` sharers, their SINR unchanged
  (a beam never interferes with its own users, and a user's wanted term uses
  its OWN link power, not the beam power).
* **Beam power.**  The beam radiates ``p_b = max`` over its served users' link
  powers.  If u is the unique max, ``p_b`` drops to the next-highest; tied or
  below the max, nothing changes.  If u is alone, the beam goes dark.
* **Co-channel interference.**  Beam b's radiated power reaches every
  co-colour victim (same satellite, other cell: 3.12a; other satellite, any
  cell: 3.12b) linearly in ``p_b``; a drop or a dark beam lowers their
  interference by ``(1 - p_b'/p_b) T[v, b]``.  Nothing else moves: link
  powers are per-user angle recurrences, feasibility is per link, the fading
  draw is common.  So removing u can only RAISE the others' rates:
  ``sum_u B_u^D <= system bits`` (the gap is the sum of the externalities),
  with ``B_u^D`` possibly negative when u's beam hurts co-colour users more
  than u gains.
* **Power.**  ``P_sys = sum_beams supply(p_b) + N_beams P_cir + N_sats P_BB``;
  nothing in it depends on SINR or interference (the recurrence depends only
  on the off-axis angle, 3.11/3.12).  Hence ``E_u^D`` equals the analytic
  lighting price exactly, ``E_u^D >= 0`` and ``sum_u E_u^D <= system joules``
  (shared circuit/baseband/sub-max supply is charged to nobody).

Outage (a user whose chosen link needs more than ``p_max``; ``service.py``):
it counts in the pre-admission demand (next step's observation) only -- not
in ``U_b``, not in the beam's max power, not in activation -- so its beam
radiates only for other users and it contributes 0 bits and 0 joules.  The
pure difference reward (and the lighting price) would therefore score an
outage exactly 0 while a served action can score below 0: the "outage free
ride" of CF3 Amendment 1 item 7.  The explicit charge (:func:`outage_charge`):

* ``E_out = E_max = (supply(p_max) + P_cir + P_BB) dt`` -- an upper bound on the
  E credit of ANY served action in both modes (a served link has
  ``p <= p_max``, supply is increasing with ``supply(0) = 0``, and u lights at
  most one circuit and one baseband);
* ``B_out = min(0, min over u's served legal alternatives a' (others fixed) of
  the mode's B credit)`` -- for the lighting price own bits are >= 0, so
  ``B_out = 0`` with no evaluation; for the difference credit it needs one
  evaluation per legal alternative of an outage user (rare: fresh segments
  start at ``p0 = p_max / 2``, so only drifted incumbents and step-0 warm-start
  links can be infeasible).

So ``B_out - eta E_out <= B(a') - eta E(a')`` for every served legal ``a'`` and
every ``eta >= 0`` -- the ordering does not depend on the Dinkelbach price the
learner is currently using.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np

from ..env.action_contract import NO_OP_ACTION, HandoverClass
from ..env.constants import DECISION_STEP_S
from ..env.link_budget import (
    BASEBAND_POWER_PER_SATELLITE_W,
    BEAM_BANDWIDTH_HZ,
    CIRCUIT_POWER_PER_BEAM_W,
    pa_efficiency,
    supply_power_w,
)
from ..errors import MCRLContractError
from .cf_sources import HEAD_B, HEAD_E, HEAD_H

__all__ = [
    "BEAM_BANDWIDTH_HZ", "CREDIT_MODES", "DEFAULT_CREDIT_MODE", "DT_S", "HEAD_B", "HEAD_E",
    "HEAD_H", "ActionCredits", "DifferenceContext", "PowerModel", "action_credits",
    "credit_matrix", "difference_context", "evaluation_bits_joules", "lighting_price_joules",
    "outage_charge", "own_bits", "step_env", "without_user_rates",
]

DT_S: float = float(DECISION_STEP_S)
CREDIT_MODES: tuple[str, ...] = ("equal_share", "difference", "lighting_price")
DEFAULT_CREDIT_MODE: str = "equal_share"


def step_env(env):
    """The :class:`StepEnvironment` behind a ``TrainerEnvironment`` (or ``env`` itself)."""
    return getattr(env, "environment", env)


@contextmanager
def frozen_driver_positions(se) -> Iterator[None]:
    """Memoize the step-0 warm-start geometry for one batch of pre-step evaluations.

    At step 0 every evaluation recomputes, per user and twice, the warm-start
    transmit gain ``G^T(theta(tau))`` (``StepEnvironment._warm_start_gain``: a
    scalar Bessel series each) after re-propagating the constellation back to
    every warm-start age (``driver.satellite_ecef_at``) -- ~10x the cost of a
    later-step evaluation.  Within one pre-step batch neither the driver nor
    the users move and the ages are fixed, so both are pure functions of their
    keys (offset; user, satellite, cell).  The caches live only inside the
    ``with`` block and the bound methods are restored on exit.  Later steps
    never call either.  Numbers are unchanged (tested bit-identical against
    the plain evaluator and against the committed step).
    """
    driver = se.driver
    if "satellite_ecef_at" in vars(driver) or "_warm_start_gain" in vars(se):
        yield                                           # nested use: already memoized
        return
    real_positions = driver.satellite_ecef_at
    real_gain = se._warm_start_gain
    positions: dict[int, dict[int, np.ndarray]] = {}
    gains: dict[tuple[int, int, int], float | None] = {}

    def cached_positions(offset_steps: int) -> dict[int, np.ndarray]:
        key = int(offset_steps)
        if key not in positions:
            positions[key] = real_positions(offset_steps)
        return positions[key]

    def cached_gain(uid, association, historical):
        key = (int(uid), int(association.norad_id), int(association.cell_id))
        if key not in gains:
            gains[key] = real_gain(uid, association, historical)
        return gains[key]

    driver.satellite_ecef_at = cached_positions
    se._warm_start_gain = cached_gain
    try:
        yield
    finally:
        del driver.satellite_ecef_at
        del se._warm_start_gain


# ------------------------------------------------------------------ power model
@dataclass(frozen=True)
class PowerModel:
    """The consumed-power constants of the environment the credit is computed on."""

    beam_power_max_w: float
    pa_max_efficiency: float
    pa_saturation_power_w: float
    circuit_w: float
    baseband_w: float

    @classmethod
    def of(cls, env) -> "PowerModel":
        phys = step_env(env).physics
        return cls(
            beam_power_max_w=float(phys.beam_power_max_w),
            pa_max_efficiency=float(phys.pa_max_efficiency),
            pa_saturation_power_w=float(phys.pa_saturation_power_w),
            circuit_w=float(CIRCUIT_POWER_PER_BEAM_W),
            baseband_w=float(BASEBAND_POWER_PER_SATELLITE_W),
        )

    def supply_w(self, beam_power_w: float) -> float:
        """(3.15) ``p / xi(p)`` with the environment's own arithmetic; 0 at ``p = 0``."""
        p = np.asarray([beam_power_w], dtype=np.float64)
        xi = pa_efficiency(p, max_efficiency=self.pa_max_efficiency,
                           saturation_power_w=self.pa_saturation_power_w)
        return float(supply_power_w(p, xi)[0])

    def outage_joules(self, dt: float = DT_S) -> float:
        """``E_max``: the largest E credit any served action can carry."""
        return (self.supply_w(self.beam_power_max_w) + self.circuit_w + self.baseband_w) * dt


# ------------------------------------------------------------------ per-step pieces
def evaluation_bits_joules(ev, dt: float = DT_S) -> tuple[float, float]:
    """``(bits, joules)`` of a committed step or an evaluation (the pooled-EE terms)."""
    e = ev.energy
    return float(e.system_throughput_bps) * dt, float(e.system_consumed_power_w) * dt


def own_bits(ev, dt: float = DT_S) -> np.ndarray:
    """``(U,)`` ``R_u dt`` for served users, 0 otherwise (CF3's ``B_u``)."""
    served = np.asarray(ev.resolution.served, dtype=bool)
    return np.where(served, np.asarray(ev.link_rate_bps, dtype=np.float64) * dt, 0.0)


def _max_without(values, i: int) -> float:
    """Max of ``values`` except position ``i``; 0.0 when ``i`` is the only entry."""
    others = np.delete(np.asarray(values, dtype=np.float64), i)
    return float(others.max()) if others.size else 0.0


def lighting_price_joules(resolution, link_power_w, model: PowerModel,
                          dt: float = DT_S) -> np.ndarray:
    """``(U,)`` analytic marginal joules of each served user (0 when unserved).

    ``supply(p_b) - supply(p_b without u)`` (+ ``P_cir`` if u is alone on its beam)
    (+ ``P_BB`` if u is the only served user of its satellite), times ``dt``.
    """
    served = np.asarray(resolution.served, dtype=bool)
    power = np.asarray(link_power_w, dtype=np.float64)
    sat = np.asarray(resolution.serving_satellite)
    cell = np.asarray(resolution.serving_cell)
    beams: dict[tuple[int, int], list[int]] = {}
    on_sat: dict[int, int] = {}
    for u in np.flatnonzero(served).tolist():
        key = (int(sat[u]), int(cell[u]))
        beams.setdefault(key, []).append(u)
        on_sat[key[0]] = on_sat.get(key[0], 0) + 1
    out = np.zeros(served.size, dtype=np.float64)
    for key, members in beams.items():
        powers = power[members]
        s_beam = model.supply_w(float(powers.max()))
        for k, u in enumerate(members):
            marginal = s_beam - model.supply_w(_max_without(powers, k))
            if len(members) == 1:
                marginal += model.circuit_w
                if on_sat[key[0]] == 1:
                    marginal += model.baseband_w
            out[u] = marginal * dt
    return out


def outage_charge(served_bit_credits: Sequence[float], model: PowerModel,
                  dt: float = DT_S) -> tuple[float, float]:
    """``(B_out, E_out)`` credited to an outage user (see the module docstring).

    ``served_bit_credits``: the mode's B credit of each of u's served legal
    alternatives (others' actions fixed); empty when there is none.
    """
    b = np.asarray(served_bit_credits, dtype=np.float64)
    b_out = min(0.0, float(b.min())) if b.size else 0.0
    return b_out, model.outage_joules(dt)


# ------------------------------------------------------------------ difference credit
@dataclass
class DifferenceContext:
    """Pre-step counterfactual evaluations for one action vector."""

    actions: np.ndarray
    base_bits: float
    base_joules: float
    served: np.ndarray
    without_bits: np.ndarray      # (U,), NaN where u emitted no action
    without_joules: np.ndarray
    outage_bits: np.ndarray       # (U,), the charge for users in outage, NaN elsewhere
    outage_joules: np.ndarray
    evaluations: int


def difference_context(env, actions, masks, rng, *, model: PowerModel,
                       dt: float = DT_S) -> DifferenceContext:
    """Evaluate ``a``, ``a without u`` for every acting u, and the legal
    alternatives of every user the base vector leaves in outage.  Call BEFORE
    ``env.step(actions, rng)``; nothing is committed and ``rng`` is not advanced.
    """
    se = step_env(env)
    with frozen_driver_positions(se):
        return _difference_context(se, np.asarray(actions, dtype=np.int64), masks, rng,
                                   model=model, dt=dt)


def _difference_context(se, a, masks, rng, *, model, dt) -> DifferenceContext:
    users = a.size
    base = se.evaluate_actions(a, rng)
    base_bits, base_joules = evaluation_bits_joules(base, dt)
    served = np.asarray(base.resolution.served, dtype=bool)
    wb = np.full(users, np.nan)
    wj = np.full(users, np.nan)
    ob = np.full(users, np.nan)
    oj = np.full(users, np.nan)
    n = 1
    for u in range(users):
        if int(a[u]) == NO_OP_ACTION:
            continue
        wb[u], wj[u] = evaluation_bits_joules(
            se.evaluate_actions_without_user(a, rng, focal_user=u), dt)
        n += 1
    for u in np.flatnonzero(~served & (a != NO_OP_ACTION)).tolist():
        credits = []
        for alt_action in np.flatnonzero(np.asarray(masks[u].mask, dtype=bool)).tolist():
            if alt_action == int(a[u]):
                continue
            alt = a.copy()
            alt[u] = alt_action
            ev = se.evaluate_actions(alt, rng)
            n += 1
            if bool(ev.resolution.served[u]):
                credits.append(evaluation_bits_joules(ev, dt)[0] - wb[u])
        ob[u], oj[u] = outage_charge(credits, model, dt)
    return DifferenceContext(actions=a, base_bits=base_bits, base_joules=base_joules,
                             served=served, without_bits=wb, without_joules=wj,
                             outage_bits=ob, outage_joules=oj, evaluations=n)


def difference_bits(ctx: DifferenceContext, u: int, own: float) -> float:
    """``B_u^D = bits(a) - bits(a without u)`` for a served user (``own`` unused)."""
    del own
    return ctx.base_bits - float(ctx.without_bits[u])


def credit_matrix(mode: str, result, outcome, *, model: PowerModel,
                  ctx: DifferenceContext | None = None, dt: float = DT_S) -> np.ndarray:
    """``(U, 3)`` raw ``(B, E, H)`` for one committed step, ``mode`` in
    ``{difference, lighting_price}`` (``equal_share`` is ``cf_reward_matrix``).

    ``result`` is the trainer's ``StepResult`` (unused beyond a shape check);
    ``outcome`` is ``env.last_outcome`` for the same step; ``ctx`` is
    :func:`difference_context` of the same action vector, evaluated before
    the step (difference mode only).
    """
    if mode not in ("difference", "lighting_price"):
        raise MCRLContractError(f"credit_matrix handles difference / lighting_price, not {mode!r}")
    res = outcome.resolution
    served = np.asarray(res.served, dtype=bool)
    users = served.size
    if len(result.rewards) != users:
        raise MCRLContractError("result and outcome describe different steps")
    outage = np.asarray(res.outage_infeasible, dtype=bool)
    out = np.zeros((users, 3), dtype=np.float64)
    out[:, HEAD_H] = [1.0 if c is HandoverClass.INTER_SATELLITE else 0.0
                      for c in outcome.handovers]
    own = own_bits(outcome, dt)
    if mode == "difference":
        if ctx is None:
            raise MCRLContractError("the difference credit needs its pre-step context")
        if (evaluation_bits_joules(outcome, dt) != (ctx.base_bits, ctx.base_joules)
                or not np.array_equal(served, ctx.served)):
            raise MCRLContractError(
                "counterfactual parity broken: the evaluated base vector is not the "
                "committed step (ruling 2 section 1)")
        for u in np.flatnonzero(served).tolist():
            out[u, HEAD_B] = difference_bits(ctx, u, float(own[u]))
            out[u, HEAD_E] = ctx.base_joules - float(ctx.without_joules[u])
        for u in np.flatnonzero(outage).tolist():
            out[u, HEAD_B] = ctx.outage_bits[u]
            out[u, HEAD_E] = ctx.outage_joules[u]
    else:
        lp = lighting_price_joules(res, outcome.link_power_w, model, dt)
        out[served, HEAD_B] = own[served]
        out[served, HEAD_E] = lp[served]
        for u in np.flatnonzero(outage).tolist():
            out[u, HEAD_B], out[u, HEAD_E] = outage_charge((), model, dt)
    return out


# ------------------------------------------------------------------ per-action credits
@dataclass
class ActionCredits:
    """Every legal action of one user scored with the others' actions fixed."""

    user: int
    num_users: int
    actions: np.ndarray       # (K,) legal actions a'
    served: np.ndarray        # (K,) u served under (a_-u, a')
    bits: np.ndarray          # (K,) system bits of (a_-u, a')
    joules: np.ndarray        # (K,) system joules of (a_-u, a')
    own_bits: np.ndarray      # (K,) u's own bits
    lp_joules: np.ndarray     # (K,) u's analytic lighting price
    without_bits: float
    without_joules: float
    model: PowerModel
    dt: float

    def credit(self, mode: str) -> tuple[np.ndarray, np.ndarray]:
        """``(B, E)`` over ``actions`` under ``mode``, outage charge applied."""
        s = self.served
        if mode == "equal_share":           # CF3: no outage charge, every user a share
            return self.own_bits.copy(), self.joules / self.num_users
        if mode == "difference":
            b = self.bits - self.without_bits
            e = self.joules - self.without_joules
        elif mode == "lighting_price":
            b = self.own_bits.copy()
            e = self.lp_joules.copy()
        else:
            raise MCRLContractError(f"unknown credit mode {mode!r}")
        b_out, e_out = outage_charge(b[s], self.model, self.dt)
        return np.where(s, b, b_out), np.where(s, e, e_out)


def action_credits(env, actions, masks, u: int, rng, *, model: PowerModel,
                   dt: float = DT_S) -> ActionCredits:
    """Score each legal action of user ``u`` against ``actions``' other entries
    (common random numbers, nothing committed).  ``1 + |legal|`` evaluations."""
    se = step_env(env)
    with frozen_driver_positions(se):
        return _action_credits(se, np.asarray(actions, dtype=np.int64), masks, int(u), rng,
                               model=model, dt=dt)


def _action_credits(se, a, masks, u, rng, *, model, dt) -> ActionCredits:
    legal = np.flatnonzero(np.asarray(masks[u].mask, dtype=bool))
    if int(a[u]) == NO_OP_ACTION:
        without = se.evaluate_actions(a, rng)
    else:
        without = se.evaluate_actions_without_user(a, rng, focal_user=int(u))
    wb, wj = evaluation_bits_joules(without, dt)
    k = legal.size
    served = np.zeros(k, dtype=bool)
    bits, joules, own, lp = (np.zeros(k) for _ in range(4))
    for i, alt_action in enumerate(legal.tolist()):
        alt = a.copy()
        alt[u] = alt_action
        ev = se.evaluate_actions(alt, rng)
        served[i] = bool(ev.resolution.served[u])
        bits[i], joules[i] = evaluation_bits_joules(ev, dt)
        own[i] = own_bits(ev, dt)[u]
        lp[i] = lighting_price_joules(ev.resolution, ev.link_power_w, model, dt)[u]
    return ActionCredits(user=int(u), num_users=a.size, actions=legal, served=served,
                         bits=bits, joules=joules, own_bits=own, lp_joules=lp,
                         without_bits=wb, without_joules=wj, model=model, dt=dt)


# ------------------------------------------------------------------ semantics
def without_user_rates(outcome, u: int, *, noise_power_w: float,
                       bandwidth_hz: float = BEAM_BANDWIDTH_HZ) -> np.ndarray:
    """``(U,)`` rates after removing ``u``, predicted from the committed step alone.

    The analytic statement of "without u" (module docstring): beam-mates share
    ``B_w`` among ``U_b - 1``; co-colour victims of u's beam lose
    ``(1 - p_b'/p_b) T[v, b]`` of interference (``p_b'`` = max of the remaining
    link powers, 0 if none); every other rate and every SINR is unchanged.
    ``tests/test_cf_credit.py`` checks it against the evaluator.
    """
    res = outcome.resolution
    served = np.asarray(res.served, dtype=bool)
    if not served[u]:
        return np.asarray(outcome.link_rate_bps, dtype=np.float64).copy()
    rad = outcome.radiating
    column = {(int(s), int(c)): j for j, (s, c) in
              enumerate(zip(rad.norad_ids.tolist(), rad.cell_ids.tolist()))}
    beam = np.array([column[(int(res.serving_satellite[v]), int(res.serving_cell[v]))]
                     if served[v] else -1 for v in range(served.size)], dtype=np.int64)
    j = int(beam[u])
    mates = served & (beam == j)
    mates[u] = False
    link_power = np.asarray(outcome.link_power_w, dtype=np.float64)
    p_left = float(link_power[mates].max()) if mates.any() else 0.0
    keep = p_left / float(rad.power_w[j])
    interference = np.asarray(outcome.interference.total_w, dtype=np.float64)
    sinr = np.asarray(outcome.link_sinr, dtype=np.float64)
    wanted = sinr * (interference + noise_power_w)
    colors = np.asarray(rad.colors)
    victims = served & (beam != j) & (colors[np.maximum(beam, 0)] == colors[j])
    terms = np.asarray(outcome.interference_terms_w, dtype=np.float64)[:, j]
    new_interference = np.where(victims, interference - (1.0 - keep) * terms, interference)
    new_sinr = np.where(victims, wanted / (new_interference + noise_power_w), sinr)
    load = res.user_beam_load() - mates.astype(np.float64)
    rate = np.where(served, bandwidth_hz / np.maximum(load, 1.0) * np.log2(1.0 + new_sinr), 0.0)
    rate[u] = 0.0
    return rate
