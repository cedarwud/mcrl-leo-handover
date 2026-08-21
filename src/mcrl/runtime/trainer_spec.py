"""Trainer-adjacent runtime types for Phase 04D."""

from __future__ import annotations

from dataclasses import dataclass, field


R1_REWARD_MODE_THROUGHPUT = "throughput"
R1_REWARD_MODE_PER_USER_EE_CREDIT = "per-user-ee-credit"
R1_REWARD_MODE_PER_USER_BEAM_EE_CREDIT = "per-user-beam-ee-credit"
R1_REWARD_MODE_HOBS_ACTIVE_TX_EE = "hobs-active-tx-ee"
R1_REWARD_MODE_ANGLE_AWARE_EE = "angle_aware_ee"
PHASE_04_B_SINGLE_CATFISH_KIND = "phase-04-b-single-catfish-feasibility"
HOBS_ACTIVE_TX_EE_MODQN_FEASIBILITY_KIND = "hobs-active-tx-ee-modqn-feasibility"
HOBS_ACTIVE_TX_EE_ANTI_COLLAPSE_KIND = (
    "hobs-active-tx-ee-anti-collapse-design-gate"
)
HOBS_ACTIVE_TX_EE_QOS_STICKY_BROADER_EFFECTIVENESS_KIND = (
    "hobs-active-tx-ee-qos-sticky-broader-effectiveness-gate"
)
HOBS_ACTIVE_TX_EE_NON_CODEBOOK_CONTINUOUS_POWER_IMPLEMENTATION_READINESS_KIND = (
    "hobs-active-tx-ee-non-codebook-continuous-power-implementation-readiness"
)
HOBS_ACTIVE_TX_EE_NON_CODEBOOK_CONTINUOUS_POWER_BOUNDED_PILOT_KIND = (
    "hobs-active-tx-ee-non-codebook-continuous-power-bounded-pilot"
)
PHASE_05_B_MULTI_CATFISH_KIND = "phase-05-b-multi-catfish-bounded-pilot"
V3_MULTI_CATFISH_KIND = "multi-catfish-v3-redesign-bounded"
PHASE_07_B_SINGLE_CATFISH_UTILITY_KIND = (
    "phase-07-b-single-catfish-intervention-utility"
)
PHASE_07_D_R2_GUARDED_ROBUSTNESS_KIND = (
    "phase-07-d-r2-guarded-single-catfish-robustness"
)


@dataclass(frozen=True)
class TrainerConfig:
    """All trainer hyperparameters — none may be hidden in code.

    Paper-backed (SDD §3.5):
        hidden_layers, activation, learning_rate, discount_factor,
        batch_size, episodes, objective_weights.

    Reproduction-assumption:
        epsilon_* (ASSUME-MODQN-REP-004),
        target_update_every_episodes (ASSUME-MODQN-REP-005),
        replay_capacity (ASSUME-MODQN-REP-006),
        policy_sharing_mode (ASSUME-MODQN-REP-007),
        state encoding fields (ASSUME-MODQN-REP-013).
    """

    # -- paper-backed (SDD §3.5) ------------------------------------------
    hidden_layers: tuple[int, ...] = (100, 50, 50)
    activation: str = "tanh"
    learning_rate: float = 0.01
    discount_factor: float = 0.9
    batch_size: int = 128
    episodes: int = 9000
    objective_weights: tuple[float, float, float] = (0.5, 0.3, 0.2)

    # -- ASSUME-MODQN-REP-004: epsilon schedule ----------------------------
    epsilon_start: float = 1.0
    epsilon_end: float = 0.01
    epsilon_decay_episodes: int = 7000

    # -- ASSUME-MODQN-REP-005: target-network update -----------------------
    target_update_every_episodes: int = 50

    # -- ASSUME-MODQN-REP-006: replay buffer -------------------------------
    replay_capacity: int = 50_000

    # -- ASSUME-MODQN-REP-007: policy sharing ------------------------------
    policy_sharing_mode: str = "shared"

    # -- ASSUME-MODQN-REP-013: state encoding / normalization --------------
    snr_encoding: str = "log1p"
    theta_encoding: str = "raw_radians"
    # Retained only so legacy resolved configs remain loadable.  Current
    # theta observations do not use a kilometre scale.
    offset_scale_km: float = 100.0
    load_normalization: str = "divide_by_num_users"

    # -- ASSUME-MODQN-REP-015: checkpoint selection rule -------------------
    checkpoint_assumption_id: str = "ASSUME-MODQN-REP-015"
    checkpoint_primary_report: str = "final-episode-policy"
    checkpoint_secondary_report: str = "best-weighted-reward-on-eval"

    # -- explicit experiment surface ---------------------------------------
    training_experiment_kind: str = "baseline"
    training_experiment_id: str = ""
    method_family: str = "MODQN-baseline"
    phase: str = "baseline"
    comparison_role: str = "not-applicable"
    r1_reward_mode: str = R1_REWARD_MODE_THROUGHPUT
    r1_reward_label: str = "throughput"
    r1_reward_provenance: str = "paper-backed MODQN throughput objective"
    reward_calibration_enabled: bool = False
    reward_calibration_mode: str = "raw-unscaled"
    reward_calibration_source: str = "raw-unscaled"
    reward_calibration_scales: tuple[float, float, float] = (1.0, 1.0, 1.0)
    reward_normalization_mode: str = "raw-unscaled"
    load_balance_calibration_mode: str = "baseline-paper-weight"

    # -- Phase 04-B Catfish-MODQN opt-in surface ---------------------------
    catfish_enabled: bool = False
    catfish_ablation: str = "none"
    catfish_discount_factor: float = 0.9
    catfish_replay_capacity: int = 50_000
    catfish_quality_weights: tuple[float, float, float] = (0.5, 0.3, 0.2)
    catfish_quality_threshold_mode: str = "quantile"
    catfish_quality_quantile: float = 0.8
    catfish_quality_fixed_threshold: float | None = None
    catfish_quality_threshold_window: int = 1_000
    catfish_warmup_transitions: int = 256
    catfish_warmup_trigger: str = "main-replay-size"
    catfish_partition_mode: str = "duplicate-high-value"
    catfish_intervention_enabled: bool = False
    catfish_intervention_period_updates: int = 1
    catfish_intervention_catfish_ratio: float = 0.3
    catfish_min_catfish_replay_size: int = 32
    catfish_competitive_shaping_enabled: bool = False

    # -- Phase 05-B Multi-Catfish opt-in surface --------------------------
    catfish_phase05b_variant: str = "not-applicable"
    catfish_objective_admission_rule: str = "disabled"
    catfish_objective_tie_policy: str = "not-applicable"
    catfish_source_ratios: tuple[float, float, float] = (0.0, 0.0, 0.0)
    catfish_total_intervention_ratio: float = 0.0
    catfish_specialist_mode: str = "disabled"
    catfish_r1_threshold: float = 131.66555786132812
    catfish_r1_r3_guardrail: float = -2.155817623138428
    catfish_r2_best_value: float = 0.0
    catfish_r3_threshold: float = -1.4955613708496094
    catfish_r3_r1_guardrail: float = 96.77507400512695
    catfish_random_buffer_admission_probability: float = 0.15
    catfish_phase05b_seed_triplets: tuple[tuple[int, int, int], ...] = ()

    # -- Multi-Catfish v3 method-machinery opt-in surface -----------------
    catfish_v3_role_weights: dict[str, dict[str, float]] = field(
        default_factory=lambda: {
            "catfish-ee": {"r1": 0.50, "r2": 0.30, "r3": 0.20},
            "catfish-ho": {"r1": 0.20, "r2": 0.60, "r3": 0.20},
            "catfish-qos": {"r1": 0.30, "r2": 0.20, "r3": 0.50},
        }
    )
    catfish_v3_role_quota_floor: dict[str, int] = field(
        default_factory=lambda: {
            "catfish-ee": 2,
            "catfish-ho": 1,
            "catfish-qos": 1,
        }
    )
    catfish_v3_flexible_quota_slots: int = 4
    catfish_v3_role_quota_cap: dict[str, int] = field(
        default_factory=lambda: {
            "catfish-ee": 4,
            "catfish-ho": 3,
            "catfish-qos": 4,
        }
    )
    catfish_v3_anti_starvation_threshold: int = 16
    catfish_v3_main_replay_min_share: float = 0.875
    catfish_v3_random_equal_budget_skip_enabled: bool = True
    catfish_v3_random_equal_budget_quality_tolerance: float = 1e-9
    catfish_v3_admission_warmup_transitions: int = 256
    catfish_v3_admission_quality_threshold: float = 0.0

    # -- Phase 07-B single-Catfish recovery opt-in surface ----------------
    catfish_phase07b_variant: str = "not-applicable"
    catfish_intervention_source_mode: str = "catfish-replay"
    catfish_challenger_enabled: bool = True
    catfish_lineage_tracking_enabled: bool = False
    catfish_phase07b_seed_triplets: tuple[tuple[int, int, int], ...] = ()

    # -- Phase 07-D r2-guarded single-Catfish robustness surface ----------
    catfish_phase07d_variant: str = "not-applicable"
    catfish_r2_guard_enabled: bool = False
    catfish_r2_admission_guard_enabled: bool = False
    catfish_r2_intervention_guard_enabled: bool = False
    catfish_r2_strict_no_handover_sample_guard: bool = False
    catfish_r2_guard_max_batch_attempts: int = 16
    catfish_handover_spike_guard_enabled: bool = False
    catfish_handover_spike_window: int = 5
    catfish_handover_spike_margin: float = 0.10
    catfish_handover_spike_min_windows: int = 3
    catfish_phase07d_seed_triplets: tuple[tuple[int, int, int], ...] = ()

    # -- HOBS active-TX EE anti-collapse opt-in surface --------------------
    anti_collapse_action_constraint_enabled: bool = False
    anti_collapse_constraint_mode: str = "disabled"
    anti_collapse_max_users_per_beam: int = 0
    anti_collapse_min_active_beams_target: int = 0
    anti_collapse_assignment_order: str = "user-index"
    anti_collapse_overload_threshold_users_per_beam: int = 0
    anti_collapse_qos_ratio_min: float = 0.95
    anti_collapse_allow_nonsticky_moves: bool = False
    anti_collapse_nonsticky_move_budget: int = 0

    # -- §6.2 PopArt online standardization opt-in surface -------------------
    popart_enabled: bool = False
    popart_sigma_floor: float = 1e-3
    popart_clip_value: float = 10.0
    popart_warmup_steps: int = 200

    # -- §6.2 training row capture opt-in surface ----------------------------
    section_6_2_row_capture_enabled: bool = False
    section_6_2_row_capture_path: str | None = None

    # -- compute device ------------------------------------------------------
    device: str = "cpu"

    def __post_init__(self) -> None:
        from .trainer_config_validation import validate_trainer_config

        validate_trainer_config(self)


@dataclass
class EpisodeLog:
    """Per-episode training metrics."""

    episode: int
    epsilon: float
    r1_mean: float
    r2_mean: float
    r3_mean: float
    scalar_reward: float
    total_handovers: int
    replay_size: int
    losses: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class EvalSummary:
    """Aggregated greedy-policy evaluation over the configured eval seeds."""

    episode: int
    evaluation_every_episodes: int
    eval_seeds: tuple[int, ...]
    mean_scalar_reward: float
    std_scalar_reward: float
    mean_r1: float
    std_r1: float
    mean_r2: float
    std_r2: float
    mean_r3: float
    std_r3: float
    mean_total_handovers: float
    std_total_handovers: float
