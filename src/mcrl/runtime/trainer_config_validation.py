"""Fail-loud validation for :class:`~mcrl.runtime.trainer_spec.TrainerConfig`.

Written fresh rather than ported.  The source project's validator is 1,124
lines and most of it validates the Phase-04B..07D and collapse-pilot
surfaces that W-09 removed — porting it would have re-introduced, as
validation rules, the vocabulary SDD §8 forbids.

Everything here is a constraint on a field this project actually has, and
each one exists because violating it fails **silently** rather than loudly:

* weights that do not sum to 1 rescale the whole reward, and the run merely
  looks worse than it should;
* a replay smaller than the batch makes ``sample`` draw without replacement
  from too few items and raise deep inside training, long after the config
  that caused it;
* an epsilon schedule that rises turns exploration on over time, which reads
  as instability rather than as a typo;
* a non-positive discount silently deletes the future.

Range checks that would only ever be tripped by a value the dataclass
already types (a string where a float belongs) are left out — that is what
the type is for.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ..errors import MCRLContractError

if TYPE_CHECKING:
    from .trainer_spec import TrainerConfig

VALID_ACTIVATIONS = frozenset({"tanh", "relu"})
"""``tanh`` is MODQN §IV.  ``relu`` exists only as a named ablation arm."""

VALID_POLICY_SHARING = frozenset({"shared"})
"""ASSUME-MODQN-REP-007.  Per-user parameters were never this project's design."""

VALID_SNR_ENCODINGS = frozenset({"log1p", "raw"})
VALID_THETA_ENCODINGS = frozenset({"raw_radians"})
VALID_LOAD_NORMALIZATIONS = frozenset({"divide_by_num_users", "raw"})

_WEIGHT_SUM_TOLERANCE = 1e-9


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MCRLContractError(message)


def validate_trainer_config(config: TrainerConfig) -> None:
    """Raise :class:`MCRLContractError` on an unusable configuration."""

    # -- network ----------------------------------------------------------
    _require(
        len(config.hidden_layers) > 0,
        "hidden_layers must not be empty",
    )
    _require(
        all(int(width) > 0 for width in config.hidden_layers),
        f"hidden layer widths must be positive, got {config.hidden_layers}",
    )
    _require(
        config.activation in VALID_ACTIVATIONS,
        f"activation must be one of {sorted(VALID_ACTIVATIONS)}, "
        f"got {config.activation!r}",
    )

    # -- optimisation -----------------------------------------------------
    _require(
        math.isfinite(config.learning_rate) and config.learning_rate > 0.0,
        f"learning_rate must be finite and positive, got {config.learning_rate}",
    )
    _require(
        0.0 < config.discount_factor <= 1.0,
        f"discount_factor must lie in (0, 1], got {config.discount_factor}",
    )
    _require(config.batch_size >= 1, "batch_size must be >= 1")
    _require(config.episodes >= 1, "episodes must be >= 1")
    _require(
        config.replay_capacity >= config.batch_size,
        f"replay_capacity ({config.replay_capacity}) must be at least "
        f"batch_size ({config.batch_size}); sampling without replacement from "
        "a smaller buffer raises deep inside training",
    )

    # -- objectives -------------------------------------------------------
    weights = config.objective_weights
    _require(len(weights) == 3, "objective_weights must have three entries")
    _require(
        all(math.isfinite(w) and w >= 0.0 for w in weights),
        f"objective weights must be finite and non-negative, got {weights}",
    )
    _require(
        abs(sum(weights) - 1.0) <= _WEIGHT_SUM_TOLERANCE,
        f"objective_weights must sum to 1, got {sum(weights)} from {weights}; "
        "a different sum silently rescales the whole reward",
    )

    # -- exploration schedule (ASSUME-MODQN-REP-004) ----------------------
    _require(
        0.0 <= config.epsilon_end <= config.epsilon_start <= 1.0,
        "epsilon schedule must satisfy 0 <= end <= start <= 1, got "
        f"start={config.epsilon_start}, end={config.epsilon_end}",
    )
    _require(
        config.epsilon_decay_episodes >= 1,
        "epsilon_decay_episodes must be >= 1",
    )

    # -- target network (ASSUME-MODQN-REP-005) ----------------------------
    _require(
        config.target_update_every_episodes >= 1,
        "target_update_every_episodes must be >= 1",
    )

    # -- policy sharing and state encoding (REP-007, REP-013) -------------
    _require(
        config.policy_sharing_mode in VALID_POLICY_SHARING,
        f"policy_sharing_mode must be one of {sorted(VALID_POLICY_SHARING)}, "
        f"got {config.policy_sharing_mode!r}",
    )
    _require(
        config.snr_encoding in VALID_SNR_ENCODINGS,
        f"snr_encoding must be one of {sorted(VALID_SNR_ENCODINGS)}, "
        f"got {config.snr_encoding!r}",
    )
    _require(
        config.theta_encoding in VALID_THETA_ENCODINGS,
        f"theta_encoding must be one of {sorted(VALID_THETA_ENCODINGS)}, "
        f"got {config.theta_encoding!r}",
    )
    _require(
        config.load_normalization in VALID_LOAD_NORMALIZATIONS,
        f"load_normalization must be one of {sorted(VALID_LOAD_NORMALIZATIONS)}, "
        f"got {config.load_normalization!r}",
    )

    # -- reward calibration ----------------------------------------------
    scales = config.reward_calibration_scales
    _require(len(scales) == 3, "reward_calibration_scales must have three entries")
    _require(
        all(math.isfinite(scale) and scale > 0.0 for scale in scales),
        f"reward calibration scales must be finite and positive, got {scales}; "
        "a zero scale divides the objective away without an error",
    )
    if config.reward_calibration_enabled:
        # Imported lazily: config construction must not pull in the
        # environment, and this branch is off by default.
        from ..env.service import R3_SCALE_IS_FROZEN

        # This is the training-time gate the flag exists for: a PREREG may be
        # frozen with Q-D open, but a run may not consume a stale scale.
        _require(
            R3_SCALE_IS_FROZEN,
            "reward calibration cannot be enabled while the r3 scale is "
            "unfrozen (Q-D): B13 changed r3 from a normalised gap to a raw "
            "head count, so the inherited scale means nothing for it",
        )
