"""Trainer-adjacent runtime types for Phase 04D."""

from __future__ import annotations

from dataclasses import dataclass, field


# PATCH P-20 (W-18): the five ``R1_REWARD_MODE_*`` constants are gone.
#
# (3.25) defines r1 as one thing — ``Σ x·η`` — so there was nothing for a
# mode to select between.  Four of the five named Family-B surfaces this
# repository does not contain, and the fifth ("throughput") pointed at a
# field the environment had started filling with bits/J.  Same reasoning as
# P-05 and P-16: a switch with one live position is not a switch, and the
# dead positions are sockets.
# NOTE (W-09): the Phase-04B/05B/07B/07D and HOBS collapse-pilot
# experiment-kind constants are removed.  SDD §8 keeps that code for later
# ablation, but it lives in the source project and was deliberately not
# ported here (docs/PROVENANCE.md).  Constants naming experiments this repo
# cannot run retain none of the ablation value and all of the trap: a reader
# sets one and nothing happens.


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
    # Ruling C-13: a CONTROLLED VARIABLE, not a value. SDD §2.3 makes it the
    # only X-level deviation (Table I says 0.01, this study ran 0.001), P6
    # sweeps {0.01, 0.003, 0.001}, and the PREREG records the sweep rather
    # than either side's default. The dataclass still needs *a* number to
    # construct; it must be supplied explicitly by whatever sets up a run.
    learning_rate: float = 0.01
    discount_factor: float = 0.9
    batch_size: int = 128
    episodes: int = 9000
    objective_weights: tuple[float, float, float] = (0.5, 0.3, 0.2)

    # -- ASSUME-MODQN-REP-004: epsilon schedule ----------------------------
    epsilon_start: float = 1.0
    epsilon_end: float = 0.01
    # PATCH P-06 (W-09): the register's REP-004 value of 7000 is stale.
    # ``family_b_r3/common_trainer.py:296`` uses 2000, 8 of the source
    # project's 9 resolved configs use 2000, and the parameter spec §6.1
    # names 7000 as out of date.  A stale default is exactly what the
    # freeze flags elsewhere exist to stop being frozen by inertia.
    epsilon_decay_episodes: int = 2000

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
    r1_reward_label: str = "system-energy-efficiency"
    r1_reward_provenance: str = "paper eq. (3.25): r1 = sum_{s,v} x * eta"
    # ⚠ ON by default since 2026-08-23, and it has to be.  Uncalibrated,
    # the omega_1 r_1 term is 4.1e5 times the omega_3 r_3 term and 7.6e6
    # times omega_2 r_2 -- the three-objective problem degenerates into
    # single-objective r_1, and freezing it that way would freeze a
    # degenerate training setup.  See runtime/reward_calibration.py.
    reward_calibration_enabled: bool = True
    reward_calibration_mode: str = "divide-by-fixed-scales"
    reward_calibration_source: str = "probe-P3-and-analytic-bound"
    reward_calibration_scales: tuple[float, float, float] = field(
        default_factory=lambda: __import__(
            "mcrl.runtime.reward_calibration", fromlist=["REWARD_SCALES"]
        ).REWARD_SCALES
    )
    reward_normalization_mode: str = "raw-unscaled"
    load_balance_calibration_mode: str = "baseline-paper-weight"

    # -- W-09: four opt-in surfaces removed -----------------------------------
    #
    # Gone: the Phase-04B/05B/v3/07B/07D surfaces (44 fields), the HOBS
    # collapse-pilot action-constraint surface (9 fields), the online
    # reward-standardisation surface (4 fields), and the §6.2 row-capture
    # surface (2 fields).
    #
    # None of them had a consumer here.  ``algorithms/modqn.py`` never read a
    # single field of the first group; the trainers that would have live in the
    # source project and were not ported.  The second group fed two dormant
    # selectors W-09 also removed — the family SDD §2.2 deletes, and the
    # 2026-08-22 ruling forbids leaving a socket for a deleted mechanism.  The
    # third was always disabled and its module was never ported.  The fourth
    # reached into the OLD environment's private members.
    #
    # SDD §7's PREREG delta asks for a "disabled" flag.  "Not implemented in
    # this repository" is the stronger statement, and it is what
    # docs/PREREG-DRAFT.md now records.

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
