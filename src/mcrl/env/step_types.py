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

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StepConfig:
    """Top-level configuration for one environment run.

    Paper-backed: num_users, slot_duration_s, episode_duration_s,
    handover phi1/phi2 bounds.
    Reproduction-assumption: concrete phi1/phi2 (ASSUME-MODQN-REP-003).
    """

    num_users: int = 100
    slot_duration_s: float = 1.0
    episode_duration_s: float = 10.0
    user_speed_kmh: float = 30.0

    # ASSUME-MODQN-REP-003: handover penalty values
    phi1: float = 0.5   # intra-satellite beam change
    phi2: float = 1.0   # inter-satellite handover

    # User ground position — reproduction-assumption (not specified in paper).
    # Default: equator, visible to polar-orbit sats.
    user_lat_deg: float = 0.0
    user_lon_deg: float = 0.0

    # ASSUME-MODQN-REP-019: r3 gap semantics
    r3_gap_scope: str = "all-reachable-beams"
    r3_empty_beam_throughput: float = 0.0

    # ASSUME-MODQN-REP-020/021: user mobility and scatter
    action_mask_eligibility_mode: str = "satellite-visible-all-beams"
    user_heading_stride_rad: float = USER_HEADING_STRIDE_RAD
    user_scatter_radius_km: float = USER_SCATTER_RADIUS_KM
    # PATCH P-15 (ruling §8): §IV gives a 200 x 90 km rectangle, so the
    # circular default is wrong and is not kept as an option — "留著就會有
    # 人選到".
    user_scatter_distribution: str = "uniform-rectangle"
    user_area_width_km: float = 0.0
    user_area_height_km: float = 0.0
    # PATCH P-15 (ruling §8): §IV says "random wandering".
    mobility_model: str = "random-wandering"
    random_wandering_max_turn_rad: float = RANDOM_WANDERING_MAX_TURN_RAD

    def __post_init__(self) -> None:
        if self.num_users < 1:
            raise ValueError(f"num_users must be >= 1, got {self.num_users}")
        if self.slot_duration_s <= 0:
            raise ValueError(f"slot_duration_s must be > 0, got {self.slot_duration_s}")
        if self.episode_duration_s <= 0:
            raise ValueError(
                f"episode_duration_s must be > 0, got {self.episode_duration_s}"
            )
        if not (0 < self.phi1 < self.phi2):
            raise ValueError(
                f"Paper requires 0 < phi1 < phi2, got phi1={self.phi1}, phi2={self.phi2}"
            )
        if self.r3_gap_scope not in {
            "all-reachable-beams",
            "occupied-beams-only",
        }:
            raise ValueError(
                "r3_gap_scope must be one of "
                "{'all-reachable-beams', 'occupied-beams-only'}, "
                f"got {self.r3_gap_scope!r}"
            )
        if self.action_mask_eligibility_mode not in {
            "satellite-visible-all-beams",
            "nearest-beam-per-visible-satellite",
        }:
            raise ValueError(
                "action_mask_eligibility_mode must be one of "
                "{'satellite-visible-all-beams', "
                "'nearest-beam-per-visible-satellite'}, "
                f"got {self.action_mask_eligibility_mode!r}"
            )
        if self.user_scatter_radius_km < 0:
            raise ValueError(
                "user_scatter_radius_km must be >= 0, "
                f"got {self.user_scatter_radius_km}"
            )
        if self.user_scatter_distribution not in {
            "uniform-circular",
            "uniform-rectangle",
        }:
            raise ValueError(
                "user_scatter_distribution must be one of "
                "{'uniform-circular', 'uniform-rectangle'}, "
                f"got {self.user_scatter_distribution!r}"
            )
        if self.user_scatter_distribution == "uniform-rectangle":
            if self.user_area_width_km <= 0 or self.user_area_height_km <= 0:
                raise ValueError(
                    "uniform-rectangle requires positive user_area_width_km "
                    f"and user_area_height_km, got width={self.user_area_width_km}, "
                    f"height={self.user_area_height_km}"
                )
        if self.mobility_model not in {
            "deterministic-heading",
            "random-wandering",
        }:
            raise ValueError(
                "mobility_model must be one of "
                "{'deterministic-heading', 'random-wandering'}, "
                f"got {self.mobility_model!r}"
            )
        if self.random_wandering_max_turn_rad < 0:
            raise ValueError(
                "random_wandering_max_turn_rad must be >= 0, "
                f"got {self.random_wandering_max_turn_rad}"
            )

    @property
    def steps_per_episode(self) -> int:
        return int(self.episode_duration_s / self.slot_duration_s)


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
    """Raw reward vector r1/r2/r3 for one user at one step.

    The paper-backed MODQN r1 throughput is always preserved.  The active
    Family-B system-EE objective is the additive contribution ``R_u/P_system``;
    summing that field across users exactly recovers the step-level system EE.
    The older kappa-allocated quantity is retained only as a named diagnostic
    and compatibility surface and must not drive active training or verdicts.

    No normalization is applied. Values are in natural units:
    - r1_throughput: bits/s (throughput)
    - r1_system_ee_contribution: bits/J using the shared system consumed-power
      denominator, ``R_u/P_system`` (active Family-B objective)
    - r1_kappa_allocated_ee_diagnostic: bits/J using the legacy
      ``R_u/(kappa_u P_beam_total)`` denominator (diagnostic only)
    - r1_energy_efficiency_credit: compatibility alias value for the same
      legacy kappa-allocated diagnostic
    - r1_beam_power_efficiency_credit: bits/s/W using full selected-beam
      ``P_b`` denominator (Phase 03B credit-assignment sensitivity)
    - r2: dimensionless penalty (0, -phi1, or -phi2)
    - r3: PATCH P-13 (B13) — the count-based ``-U_{b_u}``, in whole users.
      The original line described the superseded form, "dimensionless ratio
      (negative gap / num_users)", which is a different quantity in
      different units; leaving it would have made the typed contract
      disagree with ``service.r3_counting``.
    """

    r1_throughput: float
    r2_handover: float
    r3_load_balance: float
    r1_energy_efficiency_credit: float = 0.0
    r1_beam_power_efficiency_credit: float = 0.0
    r1_hobs_active_tx_ee: float = 0.0
    """HOBS-style active-TX system EE: sum_u(R_u) / (sum_active_b(P_b) + eps).
    Same value for all users in the step. Opt-in feasibility gate only."""
    # Phase 01 angle-aware EE per-UE reward; emitted only when R1_REWARD_MODE_ANGLE_AWARE_EE active.
    r1_angle_aware_ee: float | None = None
    r1_system_ee_contribution: float | None = None
    """Additive instantaneous system-EE contribution ``R_u/P_system``.

    ``None`` means the producing environment does not implement this reward
    surface.  Active system-EE selection must fail closed on that value; a
    numeric zero is reserved for a real zero-throughput contribution.
    """
    r1_kappa_allocated_ee_diagnostic: float = 0.0
    """Legacy kappa-allocated EE value; diagnostic/compatibility only."""


@dataclass
class StepResult:
    """Output of one environment step."""

    time_s: float
    step_index: int
    done: bool

    user_states: list[UserState]
    action_masks: list[ActionMask]
    rewards: list[RewardComponents]

    # Per-beam aggregate throughput for load balance computation.
    beam_throughputs: np.ndarray
    """Total throughput per beam, shape (L*K,)."""

    active_beam_mask: np.ndarray
    """Boolean active-beam mask derived from post-action beam loads, shape (L*K,)."""

    beam_transmit_power_w: np.ndarray
    """Explicit downlink per-beam transmit power ``p_{s,v}(t)`` in linear W.

    PATCH P-16: the four fields that used to follow — ``selected_power_profile``,
    ``total_active_beam_power_w``, ``power_budget_violation`` and
    ``power_budget_excess_w`` — went with ``PowerSurfaceConfig``.  There is no
    profile to select and no aggregate budget: ruling C-2 leaves exactly one
    ceiling, the per-**link** feasibility test, and it produces an outage for
    one user rather than a violation flag for the step.
    """


@dataclass
class DiagnosticsReport:
    """First-step diagnostics for reward scale inspection.

    Emitted once per environment reset to expose reward magnitudes
    before any hidden normalization could mask calibration issues.
    """

    zenith_snr_db: float
    zenith_throughput_bps: float
    sample_r1: float
    sample_r2_beam_change: float
    sample_r2_sat_change: float
    sample_r3: float
    r1_r2_ratio: float
    r1_r3_ratio: float
    dominance_warnings: list[str] = field(default_factory=list)
