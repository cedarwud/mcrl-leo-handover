"""State encoding helpers for the runtime seam.

PATCH P-09 (W-10): ``UserState`` is now imported from ``env.step_types``,
its canonical home.  The original ``from ..env.step import UserState``
pointed at the OLD environment module, which this project replaces and never
ported — it was the reason the tree could not be imported at all
(``docs/PROVENANCE.md``).
"""

from __future__ import annotations

import numpy as np

from ..env.action_contract import CONTRACT_STATE_DIM
from ..env.step_types import UserState
from ..errors import MCRLContractError
from .trainer_spec import TrainerConfig


def encode_state(
    user_state: UserState,
    num_users: int,
    config: TrainerConfig,
) -> np.ndarray:
    """Encode a UserState into a flat numpy vector.

    ASSUME-MODQN-REP-013 state encoding contract, extended by SDD §4A.6:
        [access_vector, encoded_snr, theta_rad, encoded_loads, contract]

    PATCH P-10 (W-10): the 13-dimensional contract block is appended, making
    the authoritative state dimension ``4C + 13 = 125`` (SDD §3.6).  The four
    blocks stay exactly as they were and keep the same ``(l, j)`` ordering as
    the action index, so state and action remain aligned by construction
    (§4A.1); the contract block is environment-side accounting and sits after
    them rather than inside them.

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

    # PATCH P-10: fail loud rather than silently emitting a 112-vector.
    if user_state.contract_fields is None:
        raise MCRLContractError(
            "UserState.contract_fields is required (SDD §4A.6); build it with "
            "mcrl.env.action_contract.contract_state_fields()"
        )
    contract = np.asarray(user_state.contract_fields, dtype=np.float32)
    if contract.shape != (CONTRACT_STATE_DIM,):
        raise MCRLContractError(
            f"contract_fields must have shape ({CONTRACT_STATE_DIM},), "
            f"got {contract.shape}"
        )

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
    return np.concatenate([access, snr, theta, loads, contract])


def state_dim_for(num_beams_total: int) -> int:
    """Flat state dimension: ``4C + 13``.

    At the frozen ``C = 28`` this is **125**, the single authoritative value
    of SDD §3.6.
    """
    return 4 * num_beams_total + CONTRACT_STATE_DIM
