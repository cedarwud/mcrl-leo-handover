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
    *,
    include_contract_block: bool = False,
) -> np.ndarray:
    """Encode a UserState into a flat numpy vector.

    ASSUME-MODQN-REP-013 state encoding contract, extended by SDD §4A.6:
        [access_vector, encoded_snr, theta_rad, encoded_loads, contract]

    PATCH P-10, revised by ruling C-1 (2026-08-22): the state is **112** on
    the live path.  The 13-dimensional §4A.6 block is an **ablation switch**,
    off by default, exactly as ``χ_u`` was handled — kept in the code, absent
    from the paper.

    The precedent is the point: ``χ_u`` (84 dims) was deleted from the paper
    on the same day while being explicitly retained as a code-level ablation
    switch.  The contract block is the same kind of thing — a state extension
    with an implementation rationale that (4.1) does not contain — so it gets
    the same treatment rather than re-entering by another door.

    Where the four fields went instead of into ``s_u``:

    * ``d2_ttt_counter`` and ``dwell_phase`` are **environment accounting**;
      D2's trigger condition belongs to the mask ``A_u(t)``, and the re-key
      boundary to the dwell controller.  Both already live there.
    * ``radial_rate`` is a convenience feature, not a Markov necessity: the
      rate of change of ``θ`` is recoverable from two consecutive steps.
    * ``is_incumbent`` is the one that carried weight, and the controller
      agreed — but the resolution is a wording fix in (4.1) rather than an
      extra dimension.  See :func:`assert_incumbent_is_recoverable`.

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

    # Ruling C-1: the contract block is an ablation switch, not part of s_u.
    # Absent is the normal case and must NOT raise.
    contract = np.zeros(0, dtype=np.float32)
    if include_contract_block:
        if user_state.contract_fields is None:
            raise MCRLContractError(
                "the contract-block ablation is enabled but the state carries "
                "no contract_fields; build them with "
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


def state_dim_for(
    num_beams_total: int, *, include_contract_block: bool = False
) -> int:
    """Flat state dimension: ``4C`` — **112** at the frozen ``C = 28``.

    That is (4.1) and ch5 §5.1, and ruling C-1 makes it the live value.  The
    ablation adds 13 and is off by default.
    """
    return 4 * num_beams_total + (
        CONTRACT_STATE_DIM if include_contract_block else 0
    )


def assert_incumbent_is_recoverable(
    previous_connection: np.ndarray, incumbent_action: int | None
) -> None:
    """The one §4A.6 field that was load-bearing, resolved without a dimension.

    ``Ψ_u(t)`` must distinguish ``φ1`` from ``φ2``, which needs last step's
    **physical** association ``(ρ_u, δ_u)``.  ``x_u(t−1)`` is laid out in the
    *current* candidate order, and that table changes between steps, so the
    association is recoverable only if the incumbent still occupies a
    candidate slot and is flagged there.

    Ruling C-1: this is an under-specification in (4.1)'s indexing prose, not
    a missing dimension — the candidate table must retain the incumbent.
    This check makes the requirement enforceable instead of assumed.
    """
    previous = np.asarray(previous_connection)
    if incumbent_action is None:
        if np.any(previous > 0.0):
            raise MCRLContractError(
                "x_u(t-1) marks a previous connection but no candidate slot "
                "holds the incumbent; Psi could not be recovered from s_u"
            )
        return
    if not 0 <= int(incumbent_action) < previous.size:
        raise MCRLContractError("the incumbent action is out of range")
    if previous[int(incumbent_action)] <= 0.0:
        raise MCRLContractError(
            "the incumbent occupies a candidate slot but x_u(t-1) does not "
            "mark it; (4.1) requires the previous association to be "
            "recoverable from the candidate ordering"
        )
