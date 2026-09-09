"""Frozen C2 observation schema for the memoryless V0.25 engine."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
from typing import Sequence

from mcrl.errors import MCRLContractError

from .calibration import assert_calibration_prices
from .constants_v025 import BEAM_RF_CAP_W, FORECAST_OFFSETS, IDENTITY_REFRESH_DECISIONS


SCHEMA_VERSION = "mcrl-v025-c2-state-v1"
ACTION_FEATURES = (
    ("incumbent_nominal_decoding_margin", "dB", 20.0),
    ("forecast_se_trend", "bit/s/Hz/s", 0.1),
    ("remaining_d2_time", "s", 120.0),
    ("remaining_visibility_time", "s", 120.0),
    ("refresh_phase", "decision", float(IDENTITY_REFRESH_DECISIONS - 1)),
    ("background_occupancy", "user", 10.0),
    ("beam_activation", "boolean", 1.0),
    ("satellite_activation", "boolean", 1.0),
    ("required_power_cap_margin", "W", BEAM_RF_CAP_W),
)
OFFSET_FEATURES = (
    ("valid", "boolean", 1.0),
    ("survival", "boolean", 1.0),
    ("minimum_decoding_margin", "dB", 20.0),
    ("mean_acm_spectral_efficiency", "bit/s/Hz", 4.0),
)
STATE_SHAPE = (len(ACTION_FEATURES) + FORECAST_OFFSETS * len(OFFSET_FEATURES),)


def _schema_payload() -> dict[str, object]:
    return {
        "schema": SCHEMA_VERSION,
        "shape": list(STATE_SHAPE),
        "normalization": "divide-by-frozen-positive-scale; booleans unchanged; signed values retained",
        "action_features": [
            {"name": name, "unit": unit, "scale": float(scale).hex()}
            for name, unit, scale in ACTION_FEATURES
        ],
        "offsets": FORECAST_OFFSETS,
        "offset_features": [
            {"name": name, "unit": unit, "scale": float(scale).hex()}
            for name, unit, scale in OFFSET_FEATURES
        ],
        "rate_architecture_rule": (
            "required_power_cap_margin=cap-required_nominal_power; "
            "zero placeholder only for non-rate architectures"
        ),
        "removed_legacy_features": [
            "previous_recurrence_power",
            "gain_to_entry_ratio",
            "segment_age",
        ],
        "price_binding": "explicit lambda=eta_ref and positive kappa on every encoding",
    }


SCHEMA_SHA256 = hashlib.sha256(
    json.dumps(_schema_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
).hexdigest()


@dataclass(frozen=True)
class ForecastOffsetState:
    valid: bool
    survival: bool
    minimum_decoding_margin_db: float
    mean_acm_se_bit_s_hz: float

    def values(self) -> tuple[float, ...]:
        values = (
            float(self.valid),
            float(self.survival),
            self.minimum_decoding_margin_db,
            self.mean_acm_se_bit_s_hz,
        )
        if not all(math.isfinite(value) for value in values):
            raise MCRLContractError("offset state must be finite")
        return values


@dataclass(frozen=True)
class C2ActionState:
    incumbent_nominal_decoding_margin_db: float
    forecast_se_trend_bit_s_hz_per_s: float
    remaining_d2_time_s: float
    remaining_visibility_time_s: float
    refresh_phase: int
    background_occupancy_users: int
    beam_active: bool
    satellite_active: bool
    required_power_cap_margin_w: float | None
    offsets: tuple[ForecastOffsetState, ...]

    def __post_init__(self) -> None:
        if len(self.offsets) != FORECAST_OFFSETS:
            raise MCRLContractError("C2 state needs exactly three forecast offsets")
        if not 0 <= self.refresh_phase < IDENTITY_REFRESH_DECISIONS:
            raise MCRLContractError("refresh phase is outside 0..3")
        if type(self.background_occupancy_users) is not int or self.background_occupancy_users < 0:
            raise MCRLContractError("background occupancy must be a nonnegative integer")
        physical = (
            self.incumbent_nominal_decoding_margin_db,
            self.forecast_se_trend_bit_s_hz_per_s,
            self.remaining_d2_time_s,
            self.remaining_visibility_time_s,
        )
        if not all(math.isfinite(value) for value in physical):
            raise MCRLContractError("C2 physical state values must be finite")
        if self.remaining_d2_time_s < 0.0 or self.remaining_visibility_time_s < 0.0:
            raise MCRLContractError("remaining times must be nonnegative")


@dataclass(frozen=True)
class EncodedC2State:
    values: tuple[float, ...]
    schema_sha256: str
    lambda_bits_per_j: Fraction
    eta_ref: Fraction
    kappa_bits_per_user_step: Fraction


def encode_c2_state(
    state: C2ActionState,
    *,
    architecture: str,
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_step: int | float | str | Fraction,
) -> EncodedC2State:
    """Normalize one action row and bind its per-setting calibration."""

    eta, kappa = assert_calibration_prices(
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_step=kappa_bits_per_user_step,
    )
    is_rate = architecture in {"a-r", "a′-r"}
    if is_rate and state.required_power_cap_margin_w is None:
        raise MCRLContractError("rate-target C2 state requires power/cap margin")
    if not is_rate and state.required_power_cap_margin_w is not None:
        raise MCRLContractError("non-rate state must use the declared zero placeholder")
    margin = 0.0 if state.required_power_cap_margin_w is None else state.required_power_cap_margin_w
    raw = (
        state.incumbent_nominal_decoding_margin_db,
        state.forecast_se_trend_bit_s_hz_per_s,
        state.remaining_d2_time_s,
        state.remaining_visibility_time_s,
        float(state.refresh_phase),
        float(state.background_occupancy_users),
        float(state.beam_active),
        float(state.satellite_active),
        margin,
    )
    normalized = [value / ACTION_FEATURES[index][2] for index, value in enumerate(raw)]
    for offset in state.offsets:
        normalized.extend(
            value / OFFSET_FEATURES[index][2]
            for index, value in enumerate(offset.values())
        )
    if len(normalized) != STATE_SHAPE[0] or not all(math.isfinite(value) for value in normalized):
        raise MCRLContractError("encoded C2 state violates frozen shape/finiteness")
    return EncodedC2State(tuple(normalized), SCHEMA_SHA256, eta, eta, kappa)


def schema_manifest() -> dict[str, object]:
    return {**_schema_payload(), "schema_sha256": SCHEMA_SHA256}


__all__ = [
    "ACTION_FEATURES",
    "C2ActionState",
    "EncodedC2State",
    "ForecastOffsetState",
    "OFFSET_FEATURES",
    "SCHEMA_SHA256",
    "SCHEMA_VERSION",
    "STATE_SHAPE",
    "encode_c2_state",
    "schema_manifest",
]
