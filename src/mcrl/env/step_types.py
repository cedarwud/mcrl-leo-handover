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

_HOBS_ACTIVE_TX_EE_EPSILON_P_W: float = 1e-9
"""Numerical stability denominator floor for the HOBS-style active-TX EE formula.
Prevents 0/0 when all beams are inactive. Not a physical power floor."""

HOBS_POWER_SURFACE_STATIC_CONFIG = "static-config"
"""Default baseline path: keep the paper Table I scalar transmit power."""

HOBS_POWER_SURFACE_ACTIVE_LOAD_CONCAVE = "active-load-concave"
"""Historical Phase 02B negative control; never a current headline surface."""

HOBS_POWER_SURFACE_ANGLE_AWARE_THESIS = "angle-aware-thesis-3.13-3.15a"
"""Archived Family-B surface: target-SINR required power with both caps."""

HOBS_POWER_SURFACE_SINGLE_SINR_RECURRENT = "single-sinr-previous-step-power-v1"
"""Active Family-B surface: per-link previous-step gain compensation, no cap."""

HOBS_POWER_SURFACE_PHASE_03C_B_POWER_CODEBOOK = "phase-03c-b-power-codebook"
"""Opt-in Phase 03C-B/C new-extension: centralized discrete power codebook."""

HOBS_POWER_SURFACE_DPC_SIDECAR = "hobs-dpc-sidecar"
"""Opt-in Route B: HOBS-inspired Dynamic Power Control sidecar.
Each active beam's power evolves via P_b(t) = P_b(t-1) + xi_b(t-1) with
xi sign-flipped when per-beam EE decreases. Creates time-varying denominator
independent of interference or learning. Not a HOBS optimizer reproduction."""

HOBS_POWER_SURFACE_NON_CODEBOOK_CONTINUOUS_POWER = "non-codebook-continuous-power"
"""Opt-in CP-base implementation-readiness surface.

Active-beam power is computed analytically from post-action load and assigned
unit-power channel-quality features. It is not a finite codebook, profile
selector, optimizer, or post-hoc EE rescore.
"""

POWER_CODEBOOK_FIXED_PROFILES = {
    "fixed-low",
    "fixed-mid",
    "fixed-high",
    "load-concave",
    "qos-tail-boost",
    "budget-trim",
}
"""Concrete Phase 03C-B/C HOBS-inspired codebook profiles."""

POWER_CODEBOOK_RUNTIME_SELECTOR_PROFILE = "runtime-ee-selector"
"""Phase 03C-C opt-in runtime selector over concrete codebook profiles."""

POWER_CODEBOOK_PROFILES = POWER_CODEBOOK_FIXED_PROFILES | {
    POWER_CODEBOOK_RUNTIME_SELECTOR_PROFILE,
}
"""Supported Phase 03C-B/C HOBS-inspired power-codebook controller profiles."""

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
    user_scatter_distribution: str = "uniform-circular"
    user_area_width_km: float = 0.0
    user_area_height_km: float = 0.0
    mobility_model: str = "deterministic-heading"
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


@dataclass(frozen=True)
class PowerSurfaceConfig:
    """Opt-in per-beam transmit-power surface.

    The default ``static-config`` mode preserves the frozen MODQN baseline:
    channel/SINR uses ``ChannelConfig.tx_power_w`` exactly as before.

    ``active-load-concave`` is a historical Phase 02B negative control. It
    emits explicit linear-W ``P_b(t)`` values from the current active beam load:

    ``P_b(t) = min(max_w, active_base_power_w + load_scale_power_w * N_b^exponent)``

    for active beams and ``0 W`` for inactive beams.
    """

    hobs_power_surface_mode: str = HOBS_POWER_SURFACE_STATIC_CONFIG
    inactive_beam_policy: str = "excluded-from-active-beams"
    active_base_power_w: float = 0.25
    load_scale_power_w: float = 0.35
    load_exponent: float = 0.5
    max_power_w: float | None = 2.0
    power_codebook_profile: str = "fixed-mid"
    power_codebook_levels_w: tuple[float, ...] = (0.5, 1.0, 2.0)
    total_power_budget_w: float | None = 8.0
    sinr_intra_satellite_interference: bool = False
    """Route A audit opt-in: compute SINR with intra-satellite beam interference.

    When enabled, each active beam's SNR is replaced by:
        SINR_b = P_b * h_s / (I_intra_b + N0)
    where I_intra_b = sum_{b' != b, b' active on s} P_{b'} * h_s.

    Inactive beams contribute zero interference. Requires non-static
    hobs_power_surface_mode (per-beam P_b). This is an audit surface only,
    not a full HOBS SINR reproduction. Does not affect the static-config
    baseline path."""

    antenna_gain_in_channel: bool = False
    """Opt-in B-partial surface: multiply channel gain by per-beam G_T(theta).

    Default-off so the frozen static baseline and existing power-surface
    rollouts preserve their previous channel/SINR values unless explicitly
    enabled by a sibling-track config.
    """

    antenna_gain_g0_linear: float = 10_000.0
    """Peak transmit antenna gain G0 in linear units for G_T(theta)."""

    antenna_gain_theta_3db_rad: float = math.radians(2.0)
    """Half-power beamwidth parameter in radians for G_T(theta)."""

    # -- Route B: HOBS-inspired DPC sidecar config fields --------------------
    dpc_initial_power_w: float = 1.0
    """Initial per-beam transmit power at episode reset (W)."""

    dpc_step_size_w: float = 0.1
    """Power adjustment magnitude per step (|xi|, W). HOBS-inspired."""

    dpc_p_min_w: float = 0.1
    """Minimum per-beam transmit power floor (W). Must be > 0."""

    dpc_p_beam_max_w: float = 2.0
    """Per-beam transmit power cap (W). Paper S10: 10 dBW = 10W; default 2W."""

    dpc_p_sat_max_w: float | None = None
    """Per-satellite aggregate transmit power cap (W). None = no cap."""

    dpc_qos_thr_bps: float = 0.0
    """Per-user throughput QoS guard threshold (bps). 0 = guard disabled.
    When any served user on a beam has throughput below this threshold,
    xi is forced positive (power increases) regardless of EE direction."""

    dpc_epsilon_p_w: float = 1e-9
    """Stability floor for per-beam EE denominator (W). Prevents 0/0."""

    # -- CP-base: analytic non-codebook continuous-power sidecar ------------
    continuous_p_active_lo_w: float = 0.05
    """Lower active-beam transmit-power bound for CP-base sidecar (W)."""

    continuous_p_active_hi_w: float = 0.25
    """Upper active-beam transmit-power bound for CP-base sidecar (W)."""

    continuous_alpha: float = 0.85
    """Load-pressure coefficient for CP-base sidecar."""

    continuous_beta: float = 0.35
    """Assigned channel-pressure coefficient for CP-base sidecar."""

    continuous_kappa: float = 0.60
    """Overflow-pressure coefficient for CP-base sidecar."""

    continuous_bias: float = -2.0
    """Bias term for CP-base sidecar pressure score."""

    continuous_q_ref: float = 0.0
    """Reference unit-power link-quality feature for channel pressure."""

    continuous_n_qos: float = 50.0
    """QoS / overload reference load used in overflow pressure."""

    def __post_init__(self) -> None:
        if self.hobs_power_surface_mode not in {
            HOBS_POWER_SURFACE_STATIC_CONFIG,
            HOBS_POWER_SURFACE_ACTIVE_LOAD_CONCAVE,
            HOBS_POWER_SURFACE_ANGLE_AWARE_THESIS,
            HOBS_POWER_SURFACE_SINGLE_SINR_RECURRENT,
            HOBS_POWER_SURFACE_PHASE_03C_B_POWER_CODEBOOK,
            HOBS_POWER_SURFACE_DPC_SIDECAR,
            HOBS_POWER_SURFACE_NON_CODEBOOK_CONTINUOUS_POWER,
        }:
            raise ValueError(
                "hobs_power_surface_mode must be one of "
                f"{{{HOBS_POWER_SURFACE_STATIC_CONFIG!r}, "
                f"{HOBS_POWER_SURFACE_ACTIVE_LOAD_CONCAVE!r}, "
                f"{HOBS_POWER_SURFACE_ANGLE_AWARE_THESIS!r}, "
                f"{HOBS_POWER_SURFACE_SINGLE_SINR_RECURRENT!r}, "
                f"{HOBS_POWER_SURFACE_PHASE_03C_B_POWER_CODEBOOK!r}, "
                f"{HOBS_POWER_SURFACE_DPC_SIDECAR!r}, "
                f"{HOBS_POWER_SURFACE_NON_CODEBOOK_CONTINUOUS_POWER!r}}}, "
                f"got {self.hobs_power_surface_mode!r}"
            )
        if self.inactive_beam_policy not in {
            "excluded-from-active-beams",
            "zero-w",
        }:
            raise ValueError(
                "inactive_beam_policy must be one of "
                "{'excluded-from-active-beams', 'zero-w'}, "
                f"got {self.inactive_beam_policy!r}"
            )
        if self.active_base_power_w < 0:
            raise ValueError(
                "active_base_power_w must be >= 0, "
                f"got {self.active_base_power_w}"
            )
        if self.load_scale_power_w < 0:
            raise ValueError(
                "load_scale_power_w must be >= 0, "
                f"got {self.load_scale_power_w}"
            )
        if self.load_exponent <= 0:
            raise ValueError(f"load_exponent must be > 0, got {self.load_exponent}")
        if self.max_power_w is not None and self.max_power_w <= 0:
            raise ValueError(f"max_power_w must be > 0 when set, got {self.max_power_w}")
        if self.power_codebook_profile not in POWER_CODEBOOK_PROFILES:
            raise ValueError(
                "power_codebook_profile must be one of "
                f"{sorted(POWER_CODEBOOK_PROFILES)!r}, "
                f"got {self.power_codebook_profile!r}"
            )
        if not self.power_codebook_levels_w:
            raise ValueError("power_codebook_levels_w must contain at least one level.")
        if any(level <= 0 for level in self.power_codebook_levels_w):
            raise ValueError(
                "power_codebook_levels_w values must all be > 0, "
                f"got {self.power_codebook_levels_w!r}"
            )
        if tuple(self.power_codebook_levels_w) != tuple(sorted(self.power_codebook_levels_w)):
            raise ValueError(
                "power_codebook_levels_w must be sorted ascending, "
                f"got {self.power_codebook_levels_w!r}"
            )
        if (
            self.hobs_power_surface_mode
            == HOBS_POWER_SURFACE_PHASE_03C_B_POWER_CODEBOOK
            and
            self.max_power_w is not None
            and max(self.power_codebook_levels_w) > float(self.max_power_w)
        ):
            raise ValueError(
                "power_codebook_levels_w must not exceed max_power_w, "
                f"got levels={self.power_codebook_levels_w!r}, "
                f"max_power_w={self.max_power_w!r}"
            )
        if self.total_power_budget_w is not None and self.total_power_budget_w <= 0:
            raise ValueError(
                "total_power_budget_w must be > 0 when set, "
                f"got {self.total_power_budget_w}"
            )
        if (
            self.hobs_power_surface_mode == HOBS_POWER_SURFACE_ACTIVE_LOAD_CONCAVE
            and self.inactive_beam_policy != "zero-w"
        ):
            raise ValueError(
                "active-load-concave requires inactive_beam_policy='zero-w'."
            )
        if (
            self.hobs_power_surface_mode == HOBS_POWER_SURFACE_ANGLE_AWARE_THESIS
            and self.inactive_beam_policy != "zero-w"
        ):
            raise ValueError(
                "angle-aware-thesis-3.13-3.15a requires inactive_beam_policy='zero-w'."
            )
        if (
            self.hobs_power_surface_mode
            == HOBS_POWER_SURFACE_PHASE_03C_B_POWER_CODEBOOK
            and self.inactive_beam_policy != "zero-w"
        ):
            raise ValueError(
                "phase-03c-b-power-codebook requires inactive_beam_policy='zero-w'."
            )
        if (
            self.sinr_intra_satellite_interference
            and self.hobs_power_surface_mode == HOBS_POWER_SURFACE_STATIC_CONFIG
        ):
            raise ValueError(
                "sinr_intra_satellite_interference requires a non-static "
                "hobs_power_surface_mode (active-load-concave or "
                "phase-03c-b-power-codebook or non-codebook-continuous-power). "
                "Static-config uses a fixed scalar tx_power_w which cannot "
                "support meaningful per-beam interference audit."
            )
        if (
            self.antenna_gain_in_channel
            and self.hobs_power_surface_mode == HOBS_POWER_SURFACE_STATIC_CONFIG
        ):
            raise ValueError(
                "antenna_gain_in_channel requires a non-static "
                "hobs_power_surface_mode. Static-config preserves the frozen "
                "beam-agnostic channel path."
            )
        if self.antenna_gain_g0_linear <= 0.0:
            raise ValueError(
                "antenna_gain_g0_linear must be > 0, "
                f"got {self.antenna_gain_g0_linear}"
            )
        if self.antenna_gain_theta_3db_rad <= 0.0:
            raise ValueError(
                "antenna_gain_theta_3db_rad must be > 0, "
                f"got {self.antenna_gain_theta_3db_rad}"
            )
        if self.hobs_power_surface_mode == HOBS_POWER_SURFACE_DPC_SIDECAR:
            if self.inactive_beam_policy != "zero-w":
                raise ValueError(
                    "hobs-dpc-sidecar requires inactive_beam_policy='zero-w'."
                )
            if self.dpc_initial_power_w <= 0:
                raise ValueError(
                    f"dpc_initial_power_w must be > 0, got {self.dpc_initial_power_w}"
                )
            if self.dpc_step_size_w <= 0:
                raise ValueError(
                    f"dpc_step_size_w must be > 0, got {self.dpc_step_size_w}"
                )
            if self.dpc_p_min_w <= 0:
                raise ValueError(
                    f"dpc_p_min_w must be > 0, got {self.dpc_p_min_w}"
                )
            if self.dpc_p_beam_max_w < self.dpc_p_min_w:
                raise ValueError(
                    f"dpc_p_beam_max_w must be >= dpc_p_min_w, "
                    f"got max={self.dpc_p_beam_max_w} < min={self.dpc_p_min_w}"
                )
            if self.dpc_initial_power_w > self.dpc_p_beam_max_w:
                raise ValueError(
                    f"dpc_initial_power_w must be <= dpc_p_beam_max_w, "
                    f"got {self.dpc_initial_power_w} > {self.dpc_p_beam_max_w}"
                )
            if self.dpc_qos_thr_bps < 0:
                raise ValueError(
                    f"dpc_qos_thr_bps must be >= 0, got {self.dpc_qos_thr_bps}"
                )
            if self.dpc_epsilon_p_w <= 0:
                raise ValueError(
                    f"dpc_epsilon_p_w must be > 0, got {self.dpc_epsilon_p_w}"
                )
        if (
            self.hobs_power_surface_mode
            == HOBS_POWER_SURFACE_NON_CODEBOOK_CONTINUOUS_POWER
        ):
            if self.inactive_beam_policy != "zero-w":
                raise ValueError(
                    "non-codebook-continuous-power requires "
                    "inactive_beam_policy='zero-w'."
                )
            if self.total_power_budget_w is None:
                raise ValueError(
                    "non-codebook-continuous-power requires total_power_budget_w."
                )
            if self.continuous_p_active_lo_w < 0.0:
                raise ValueError(
                    "p_active_lo_w must be >= 0 for "
                    "non-codebook-continuous-power."
                )
            if self.continuous_p_active_hi_w <= self.continuous_p_active_lo_w:
                raise ValueError(
                    "p_active_hi_w must be > p_active_lo_w for "
                    "non-codebook-continuous-power."
                )
            if (
                self.max_power_w is not None
                and self.continuous_p_active_hi_w > float(self.max_power_w)
            ):
                raise ValueError(
                    "p_active_hi_w must not exceed max_power_w for "
                    "non-codebook-continuous-power."
                )
            if self.continuous_n_qos <= 0.0:
                raise ValueError(
                    "n_qos must be > 0 for non-codebook-continuous-power."
                )
            for name, value in {
                "alpha": self.continuous_alpha,
                "beta": self.continuous_beta,
                "kappa": self.continuous_kappa,
            }.items():
                if value < 0.0 or not math.isfinite(value):
                    raise ValueError(
                        f"{name} must be finite and >= 0 for "
                        "non-codebook-continuous-power."
                    )
            for name, value in {
                "bias": self.continuous_bias,
                "q_ref": self.continuous_q_ref,
            }.items():
                if not math.isfinite(value):
                    raise ValueError(
                        f"{name} must be finite for non-codebook-continuous-power."
                    )


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
    that slot.  It is shared across users and is not zeroed when ``k_cap``
    darkens a beam.  This is the paper's global N(t) quantity rather than the
    former per-user post-admission served-count proxy.
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
    - r3: dimensionless ratio (negative gap / num_users)
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
    """Explicit downlink per-beam transmit power ``P_b(t)`` in linear W."""

    selected_power_profile: str = HOBS_POWER_SURFACE_STATIC_CONFIG
    """Runtime power profile selected for this step."""

    total_active_beam_power_w: float = 0.0
    """Sum of active-beam transmit power in linear W."""

    power_budget_violation: bool = False
    """Whether total active beam power exceeded the configured budget."""

    power_budget_excess_w: float = 0.0
    """Amount by which active beam power exceeded the configured budget."""


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
