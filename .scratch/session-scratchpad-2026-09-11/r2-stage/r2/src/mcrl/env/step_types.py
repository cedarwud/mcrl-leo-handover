"""Typed configuration and result containers for StepEnvironment."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------------------
# Reproduction-assumption defaults (used only as typed config defaults)
# ---------------------------------------------------------------------------

USER_HEADING_STRIDE_RAD: float = 2.3998277
"""ASSUME-MODQN-REP-020: irrational-multiple stride for deterministic
per-user heading spread.  ``heading = (uid * stride) mod 2π``.
Chosen so that moderate user counts get quasi-uniform angular coverage
without an RNG draw.  Paper does not specify a mobility heading model."""

USER_SCATTER_RADIUS_KM: float = 50.0
"""ASSUME-MODQN-REP-021: radius of the circular area in which users are
uniformly scattered around the configured ground point.  Paper does not
specify user spatial distribution; 50 km is a reasonable urban/suburban
coverage assumption."""

RANDOM_WANDERING_MAX_TURN_RAD: float = math.pi / 4.0
"""ASSUME-MODQN-REP-023: per-slot bounded turn magnitude for the
follow-on `random wandering` mobility rule. The paper names the mobility
family but does not disclose the exact turn-law details."""

# PATCH P-16 (W-17, ruling C-2): the HOBS power-surface vocabulary is GONE.
#
# Deleted here: ``_HOBS_ACTIVE_TX_EE_EPSILON_P_W``, the seven
# ``HOBS_POWER_SURFACE_*`` mode names, the three ``POWER_CODEBOOK_*`` profile
# sets, and the ``PowerSurfaceConfig`` dataclass that selected between them
# (~250 lines, none of it reachable).
#
# Ruling C-2 replaced the load-based PA with the paper's angle recurrence and
# said so in one line: "載量式 PA 整條移除".  Two of the deleted modes are
# named prohibitions rather than merely unused —
# ``active-load-concave`` is ``P_base + P_scale·N^exp``, the load form itself,
# and ``angle-aware-thesis-3.13-3.15a`` is the target-SINR required-power
# inversion with both caps, which (3.11) rules out in as many words.
#
# The remaining five were dead surfaces of the source project, on the same
# footing as the four ``TrainerConfig`` groups W-09 removed under P-05: a
# field defaulting to False is a socket, and "留著就會有人選到".  The live
# power model is ``env/step.PhysicsConfig`` plus ``env/link_budget``, and it
# has no mode switch at all.

# PATCH P-21 (W-18): ``StepConfig`` is deleted.  Zero consumers, and every
# field it held now has a real owner:
#
#   num_users, speed, area, turn bound  -> env/mobility.MobilityConfig
#   steps_per_episode                   -> env/scenario.ScenarioConfig
#   phi1, phi2                          -> env/action_contract.PHI1, PHI2
#   slot_duration_s                     -> env/constants.DECISION_STEP_S
#   r3_gap_scope                        -> superseded by B13's counting r3
#   action_mask_eligibility_mode        -> superseded by §4A.5's three terms
#
# Keeping it was not merely redundant.  Ruling §8 said to DELETE the two
# ported alternatives, "不要留著當選項 —— 留著就會有人選到"; PATCH P-15
# changed the defaults but left ``__post_init__`` still accepting
# ``uniform-circular`` and ``deterministic-heading``.  ``MobilityConfig``
# implements the §IV pair and offers no switch at all, so deleting the
# second home closes that gap and the drift risk together.

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UserState:
    """Per-user observation vector s_i(t).

    All beam-indexed arrays use satellite-major, beam-minor ordering
    (ASSUME-MODQN-REP-012).
    """

    access_vector: np.ndarray
    """One-hot current beam assignment, shape (L*K,)."""

    channel_quality: np.ndarray
    """SNR (linear) to every beam, shape (L*K,)."""

    beam_offsets: np.ndarray
    """Per-candidate-beam off-axis angle θ in radians, shape (L*K,).

    The legacy field name ``beam_offsets`` is retained at the dataclass seam
    so historical serializers remain readable; current producers must place
    θ, not an east/north kilometre pair, in this field.
    """

    beam_loads: np.ndarray
    """Global, ungated demand mapped to this user's L*K candidate slots.

    Each value is the pre-admission count for the physical beam represented by
    that slot.  It is shared across users and is the paper's global N(t)
    quantity rather than a per-user post-admission served-count proxy.

    PATCH P-07 (W-09): the original sentence carried a caveat about the
    value not being zeroed when a per-satellite activation ceiling darkened
    a beam.  No beam is ever darkened in this project — activation is
    derived, ``z = 1{U > 0}`` (ruling 2026-08-22 §7.4) — so the caveat
    described a mechanism that no longer exists.
    """

    contract_fields: np.ndarray | None = None
    """PATCH P-08 (W-10), revised by ruling C-1: the §4A.6 ablation block.

    ``is_incumbent[4] + d2_ttt_counter[4] + radial_rate[4] + dwell_phase[1]``,
    built by ``mcrl.env.action_contract.contract_state_fields``.

    ⚠ **It is NOT part of ``s_u``.**  The live state is (4.1)'s ``4C = 112``;
    this block is an **ablation switch, off by default**, on the same footing
    as ``χ_u`` — kept in the code, absent from the paper.  The earlier
    sentence here said SDD §3.6 made 125 authoritative and that ``None`` was
    illegal at the encoder; the controller withdrew both on 2026-08-22.

    ``None`` is therefore the **normal** value and ``encode_state`` must not
    raise on it.  It raises only when the ablation is explicitly enabled and
    the fields are missing, which is a real inconsistency rather than the
    ordinary case.
    """


@dataclass(frozen=True)
class ActionMask:
    """Valid-action mask for one user at time t.

    mask[j] = True means action j is eligible under the active
    visibility/beam-eligibility mode. Per ASSUME-MODQN-REP-012,
    ineligible actions get Q = -inf before argmax.
    """

    mask: np.ndarray
    """Boolean array, shape (L*K,)."""

    @property
    def num_valid(self) -> int:
        return int(np.sum(self.mask))


@dataclass(frozen=True)
class RewardComponents:
    """The three-objective reward vector for one user at one step.

    PATCH P-20 (W-18, ruling C-7): five ``r1`` variants are gone and the
    remaining two mean what their names say.

    ``r1`` is (3.25), ``r1_u = Σ_{s,v} x·η = (Σ x·R)/P^N`` — an **energy
    efficiency**, not a throughput.  It used to be selected out of five
    candidate fields by ``TrainerConfig.r1_reward_mode``, and the live one
    was ``r1_throughput``, whose name then contradicted the value the
    environment was putting in it.  A field named "throughput" holding
    bits/J is exactly the silent mismatch the rest of this project keeps
    tripping over, so the selector went and the two fields split apart.

    Removed with the selector: ``r1_energy_efficiency_credit`` and
    ``r1_kappa_allocated_ee_diagnostic`` (ruling C-7 withdrew the ``κ``
    power-share closure), ``r1_beam_power_efficiency_credit``,
    ``r1_hobs_active_tx_ee`` and ``r1_angle_aware_ee`` (Family-B surfaces
    that live in the source project and were never ported here).

    No normalization is applied.  Values are in natural units:

    - ``r1_system_ee_contribution``: bit/J, ``R_u/P^N`` — **this is r1**.
      Additive by construction: summing it over users recovers the system
      EE exactly, which is what makes it a decomposition of a global
      objective rather than a per-user proxy for one.
    - ``r1_throughput``: bit/s, ``R_u`` — the numerator, reported beside it
      because G-8 forbids quoting an EE without the service it bought.
      **Not r1.**
    - ``r2_handover``: dimensionless penalty (0, −φ1, or −φ2).
    - ``r3_load_balance``: PATCH P-13 (B13) — the count-based ``−U_{b_u}``,
      in whole users.  The original line described the superseded form, "a
      dimensionless ratio (negative gap / num_users)", which is a different
      quantity in different units.
    """

    r1_system_ee_contribution: float
    """``r1`` itself: ``R_u/P^N`` in bit/J, eq. (3.25)."""

    r1_throughput: float
    """``R_u`` in bit/s — the numerator, for G-8.  Never the reward."""

    r2_handover: float
    r3_load_balance: float


@dataclass
class StepResult:
    """Output of one environment step."""

    time_s: float
    step_index: int
    done: bool

    user_states: list[UserState]
    action_masks: list[ActionMask]
    rewards: list[RewardComponents]

    served: tuple[bool, ...] | None = None
    """B0 D-2: which users the environment actually served this step.

    ``RewardComponents`` alone cannot answer this — an unserved user scores
    ``r2 = 0`` and ``r3 = 0``, values a *served* user can also take — so the
    outage floor needs the flag rather than an inference from the rewards.
    ``None`` means "this container was built without the information" (test
    fixtures predating D-2); the floor is then not applied rather than
    guessed at.  ``runtime/trainer_env.py`` always fills it from
    ``StepOutcome.resolution.served``.
    """

    # PATCH P-21: ``beam_throughputs``, ``active_beam_mask`` and
    # ``beam_transmit_power_w`` are gone with them.  Nothing read any of the
    # three, and all were documented with shape ``(L*K,)`` — a fixed 28-wide
    # per-user candidate axis.  Beams are global ``(satellite, cell)`` pairs
    # whose count varies per step, so the declared shape had stopped
    # describing the physics.  The live per-beam quantities live on
    # ``env.step.StepOutcome.radiating`` with their real length.


# PATCH P-21: ``DiagnosticsReport`` is deleted — zero consumers, and it
# described a first-step reward-scale inspection built on the OLD
# environment's quantities (a single "zenith SNR", an r1/r3 ratio taken
# before r3 became a user count).  ``StepOutcome.diagnostics`` reports the
# live figures per step instead.
