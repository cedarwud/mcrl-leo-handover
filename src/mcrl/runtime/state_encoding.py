"""State encoding helpers for the runtime seam."""

from __future__ import annotations

import numpy as np

from ..env.step import UserState
from .trainer_spec import TrainerConfig


def encode_state(
    user_state: UserState,
    num_users: int,
    config: TrainerConfig,
) -> np.ndarray:
    """Encode a UserState into a flat numpy vector.

    ASSUME-MODQN-REP-013 state encoding contract:
        [access_vector, encoded_snr, theta_rad, encoded_loads]

    Encoding rules (all explicitly configured, no hidden transforms):
        - access_vector: raw one-hot (already 0/1)
        - channel_quality: log1p(snr_linear) — bounded, monotonic
        - beam_offsets: one off-axis angle in radians per candidate beam;
          the legacy field name is retained at the UserState boundary
        - beam_loads: global, ungated per-beam demand / num_users

    A two-column ``beam_offsets`` array is accepted only as a legacy
    compatibility path for pre-M-04 fixtures and returns the historical
    5*N representation.  Current environment producers emit one-dimensional
    theta arrays and therefore use the 4*N representation below.
    """
    access = user_state.access_vector.astype(np.float32)

    snr = user_state.channel_quality.astype(np.float64)
    if config.snr_encoding == "log1p":
        snr = np.log1p(np.maximum(snr, 0.0)).astype(np.float32)
    else:
        snr = snr.astype(np.float32)

    offsets = np.asarray(user_state.beam_offsets, dtype=np.float32)
    legacy_offsets = False
    if offsets.ndim == 1:
        if config.theta_encoding != "raw_radians":
            raise ValueError(
                "current theta observations require theta_encoding='raw_radians'"
            )
        theta = offsets
    elif offsets.ndim == 2 and offsets.shape[1] == 2:
        # Historical pre-M-04 fixture compatibility.  No current producer
        # may reach this branch; keeping it preserves old artifact replay.
        if config.offset_scale_km > 0:
            offsets = offsets / config.offset_scale_km
        legacy_offsets = True
        theta = offsets.reshape(-1)
    else:
        raise ValueError(
            "UserState.beam_offsets must have shape (N,) for theta radians "
            "or legacy shape (N, 2); got "
            f"{offsets.shape!r}"
        )

    loads = user_state.beam_loads.astype(np.float32)
    if config.load_normalization == "divide_by_num_users" and num_users > 0:
        loads = loads / num_users

    if not (access.size == snr.size == loads.size):
        raise ValueError(
            "UserState beam-indexed arrays must have equal lengths: "
            f"access={access.size}, snr={snr.size}, theta={theta.size}, "
            f"loads={loads.size}"
        )
    if not legacy_offsets and theta.size != access.size:
        raise ValueError(
            "Current theta observations must have one value per beam: "
            f"access={access.size}, theta={theta.size}"
        )
    return np.concatenate([access, snr, theta, loads])


def state_dim_for(num_beams_total: int) -> int:
    """Compute the flat state dimension for a given topology."""
    return 4 * num_beams_total
