"""Versioned Stage-C state schemas and the thin engine-output extractor."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
import math
from typing import Protocol, Sequence, runtime_checkable

from .canonical import StageCContractError, canonical_sha256, float_hex
from mcrl.physics_v025.constants_v025 import DECISION_INTERVAL_S


Q1_SCHEMA_VERSION = "mcrl-v025-stagec-q1-action-v1"
Q2_SCHEMA_VERSION = "mcrl-v025-stagec-q2-action-v1"
ROW_SCHEMA_VERSION = "mcrl-v025-stagec-source-row-v1"


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    name: str
    unit: str
    scale: float


# The exact draft list requested by contract section 2. Values are action-row
# local; historical vector blocks from V0.23 become the corresponding value for
# the candidate action. Controller-unsealed scales are called out in the spec.
Q1_FEATURES = (
    FeatureSpec("nominal_sinr_margin_at_rate_target", "dB", 20.0),
    FeatureSpec("nominal_required_power_over_cap", "ratio", 1.0),
    FeatureSpec("nominal_mode_spectral_efficiency", "bit/s/Hz", 4.0),
    FeatureSpec("background_occupancy_excluding_focal", "user", 10.0),
    FeatureSpec("beam_active_before_focal", "boolean", 1.0),
    FeatureSpec("satellite_active_before_focal", "boolean", 1.0),
    FeatureSpec("off_axis_angle", "rad", 1.0),
    FeatureSpec("remaining_d2_time", "s", 120.0),
    FeatureSpec("remaining_visibility_time", "s", 120.0),
    FeatureSpec("refresh_phase", "decision", 3.0),
    FeatureSpec("previous_served_association_for_action", "boolean", 1.0),
    FeatureSpec("previous_served_load_for_action", "user", 10.0),
    FeatureSpec("previous_beam_active_for_action", "boolean", 1.0),
    FeatureSpec("previous_satellite_active_for_action", "boolean", 1.0),
    FeatureSpec("previous_beam_max_rf_over_cap", "ratio", 1.0),
    FeatureSpec("missing_incumbent", "boolean", 1.0),
)

Q2_CURRENT_FEATURES = (
    FeatureSpec("candidate_current_nominal_decoding_margin", "dB", 20.0),
    FeatureSpec("forecast_se_trend", "bit/s/Hz/s", 0.1),
    FeatureSpec("remaining_d2_time", "s", 120.0),
    FeatureSpec("remaining_visibility_time", "s", 120.0),
    FeatureSpec("refresh_phase", "decision", 3.0),
    FeatureSpec("background_occupancy_excluding_focal", "user", 10.0),
    FeatureSpec("beam_active_before_focal", "boolean", 1.0),
    FeatureSpec("satellite_active_before_focal", "boolean", 1.0),
    FeatureSpec("required_power_cap_margin", "W", 1.65),
    FeatureSpec("missing_incumbent", "boolean", 1.0),
)

Q2_OFFSET_FEATURES = (
    FeatureSpec("valid", "boolean", 1.0),
    FeatureSpec("survival", "boolean", 1.0),
    FeatureSpec("minimum_decoding_margin", "dB", 20.0),
    FeatureSpec("mean_acm_spectral_efficiency", "bit/s/Hz", 4.0),
)


def _schema_payload(version: str, features: Sequence[FeatureSpec]) -> dict[str, object]:
    return {
        "schema": version,
        "normalization": "raw_value / positive_frozen_scale; signed values retained",
        "shape": [len(features)],
        "features": [
            {"name": item.name, "unit": item.unit, "scale_hex": float_hex(item.scale)}
            for item in features
        ],
        "removed": ["recurrence_power", "entry_gain_ratio", "segment_age"],
    }


Q2_FEATURES = Q2_CURRENT_FEATURES + tuple(
    FeatureSpec(f"offset_{offset}_{feature.name}", feature.unit, feature.scale)
    for offset in (1, 2, 3)
    for feature in Q2_OFFSET_FEATURES
)
Q1_SCHEMA = _schema_payload(Q1_SCHEMA_VERSION, Q1_FEATURES)
Q2_SCHEMA = _schema_payload(Q2_SCHEMA_VERSION, Q2_FEATURES)
Q1_SCHEMA_SHA256 = canonical_sha256(Q1_SCHEMA)
Q2_SCHEMA_SHA256 = canonical_sha256(Q2_SCHEMA)


@dataclass(frozen=True, slots=True)
class PhysicalAction:
    norad_id: int | None
    beam_chain_id: int | None

    def __post_init__(self) -> None:
        if (self.norad_id is None) != (self.beam_chain_id is None):
            raise StageCContractError("null action must have both physical identity fields null")

    @property
    def is_null(self) -> bool:
        return self.norad_id is None

    def payload(self) -> dict[str, int | None]:
        return {"norad_id": self.norad_id, "beam_chain_id": self.beam_chain_id}


@dataclass(frozen=True, slots=True)
class ForecastObservation:
    valid: bool
    survival: bool
    minimum_decoding_margin_db: float
    mean_acm_spectral_efficiency: float


@dataclass(frozen=True, slots=True)
class ActionEvaluation:
    """Engine-neutral values for one legal action at one matched anchor."""

    action: PhysicalAction
    nominal_sinr_margin_at_rate_target_db: float
    nominal_required_power_over_cap: float
    nominal_mode_spectral_efficiency: float
    background_occupancy_excluding_focal: int
    beam_active_before_focal: bool
    satellite_active_before_focal: bool
    off_axis_angle_rad: float
    remaining_d2_time_s: float
    remaining_visibility_time_s: float
    refresh_phase: int
    previous_served_association_for_action: bool
    previous_served_load_for_action: int
    previous_beam_active_for_action: bool
    previous_satellite_active_for_action: bool
    previous_beam_max_rf_over_cap: float
    missing_incumbent: bool
    candidate_current_nominal_decoding_margin_db: float
    incumbent_nominal_decoding_margin_db: float
    forecast_se_trend_bit_s_hz_per_s: float
    required_power_cap_margin_w: float
    forecasts: tuple[ForecastObservation, ForecastObservation, ForecastObservation]
    c1_label_bits: float
    c1_phi_difference: float
    c2_label_bits: float
    legal: bool = True
    terminal: bool = False
    outage: bool = False
    source_provenance_sha256: str = ""
    forecast_method_sha256: str = ""
    visible_primitives_sha256: str = ""
    tle_provenance: str = "nearest_epoch_retrospective_benchmark"
    future_tle_access: str = "declared_forecast_horizon_only"


def _action_visible_payload(item: ActionEvaluation) -> dict[str, object]:
    """Exact B1 dependency allowlist: every value consumed by Q1/Q2/labels."""

    omitted = {
        "source_provenance_sha256",
        "forecast_method_sha256",
        "visible_primitives_sha256",
        "tle_provenance",
        "future_tle_access",
    }
    payload = {
        name: value
        for name, value in asdict(item).items()
        if name not in omitted
    }
    payload["action"] = item.action.payload()
    return payload


def seal_action_evaluation(
    item: ActionEvaluation,
    *,
    source_provenance_sha256: str,
    forecast_method_sha256: str,
    tle_provenance: str = "nearest_epoch_retrospective_benchmark",
    future_tle_access: str = "declared_forecast_horizon_only",
) -> ActionEvaluation:
    """Bind one engine-adapter row to the exact visible primitive values."""

    for field, value in (
        ("source_provenance_sha256", source_provenance_sha256),
        ("forecast_method_sha256", forecast_method_sha256),
    ):
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise StageCContractError(f"{field} must be a lowercase SHA-256")
    return replace(
        item,
        source_provenance_sha256=source_provenance_sha256,
        forecast_method_sha256=forecast_method_sha256,
        visible_primitives_sha256=canonical_sha256(_action_visible_payload(item)),
        tle_provenance=tle_provenance,
        future_tle_access=future_tle_access,
    )


@runtime_checkable
class PerAnchorEvaluation(Protocol):
    """Only interface the moving engine must adapt to for Stage C."""

    world_id: str
    split: str
    world_seed: int
    anchor_id: str
    anchor_index: int
    decision_time_utc: str
    decision_time_ns: int
    user_id: int
    setting_id: str
    code_digest: str
    physics_digest: str
    launch_digest: str
    catalogue_digest: str
    setting_digest: str
    calibration_digest: str
    provider_digest: str
    archive_digest: str
    allocation_manifest_digest: str
    lambda_bits_per_j: float
    eta_ref_bits_per_j: float
    kappa_normalization_bits: float
    base_action_index: int
    actions: Sequence[ActionEvaluation]


@dataclass(frozen=True, slots=True)
class SourceRow:
    schema: str
    split: str
    world_id: str
    world_seed: int
    learner_seed: int | None
    anchor_id: str
    anchor_index: int
    decision_time_utc: str
    decision_time_ns: int
    user_id: int
    action_index: int
    action: PhysicalAction
    reference_action: bool
    action_mask: tuple[bool, ...]
    q1_state: tuple[float, ...]
    q2_state: tuple[float, ...]
    incumbent_context_nominal_decoding_margin_db_hex: str
    q1_schema_sha256: str
    q2_schema_sha256: str
    setting_id: str
    code_digest: str
    physics_digest: str
    launch_digest: str
    catalogue_digest: str
    setting_digest: str
    calibration_digest: str
    provider_digest: str
    archive_digest: str
    allocation_manifest_digest: str
    lambda_bits_per_j_hex: str
    eta_ref_bits_per_j_hex: str
    kappa_normalization_bits_hex: str
    c1_label_bits_hex: str
    c1_phi_difference_hex: str
    c2_label_bits_hex: str
    c1_label_normalized_hex: str
    c2_label_normalized_hex: str
    source_provenance_sha256: str
    forecast_method_sha256: str
    visible_primitives_sha256: str
    tle_provenance: str
    future_tle_access: str
    terminal: bool
    null_action: bool
    outage: bool

    def payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["action"] = self.action.payload()
        payload["action_mask"] = list(self.action_mask)
        payload["q1_state"] = [float_hex(value) for value in self.q1_state]
        payload["q2_state"] = [float_hex(value) for value in self.q2_state]
        return payload


def _normalize(raw: Sequence[float], specs: Sequence[FeatureSpec]) -> tuple[float, ...]:
    if len(raw) != len(specs):
        raise StageCContractError("state field count disagrees with schema")
    result = tuple(float(value) / spec.scale for value, spec in zip(raw, specs, strict=True))
    if not all(math.isfinite(value) for value in result):
        raise StageCContractError("state values must be finite")
    return result


def kappa_normalization_bits(kappa_bits_per_user_s: float) -> float:
    """Controller-sealed conversion from calibration rate to one user-step."""

    value = float(kappa_bits_per_user_s)
    if not math.isfinite(value) or value <= 0.0:
        raise StageCContractError("kappa bits/user-second must be positive and finite")
    return value * DECISION_INTERVAL_S


def _validate_anchor(anchor: PerAnchorEvaluation) -> None:
    if anchor.split != "TRAIN":
        raise StageCContractError("Stage C source construction is TRAIN-only")
    if not anchor.actions:
        raise StageCContractError("anchor must carry at least the explicit null action")
    if not 0 <= anchor.base_action_index < len(anchor.actions):
        raise StageCContractError("base_action_index is outside the action table")
    if not anchor.actions[anchor.base_action_index].legal:
        raise StageCContractError("BASE action must be legal")
    if not any(item.legal and item.action.is_null for item in anchor.actions):
        raise StageCContractError("anchor must include an explicit legal null action")
    if (
        not math.isfinite(anchor.kappa_normalization_bits)
        or anchor.kappa_normalization_bits <= 0.0
    ):
        raise StageCContractError("normalization kappa must be a positive bit scale")
    if (
        not math.isfinite(anchor.lambda_bits_per_j)
        or anchor.lambda_bits_per_j <= 0.0
        or anchor.lambda_bits_per_j != anchor.eta_ref_bits_per_j
    ):
        raise StageCContractError("lambda and eta_ref must be identical")
    if anchor.anchor_index < 0 or anchor.decision_time_ns < 0:
        raise StageCContractError("anchor indices/times must be nonnegative")
    identities = [item.action for item in anchor.actions]
    if len(set(identities)) != len(identities):
        raise StageCContractError("anchor has duplicate physical actions")
    for field in (
        "code_digest",
        "physics_digest",
        "launch_digest",
        "catalogue_digest",
        "setting_digest",
        "calibration_digest",
        "provider_digest",
        "archive_digest",
        "allocation_manifest_digest",
    ):
        digest = getattr(anchor, field)
        if (
            len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise StageCContractError(f"{field} must be a lowercase SHA-256")
    try:
        parsed = datetime.fromisoformat(anchor.decision_time_utc.replace("Z", "+00:00"))
    except ValueError as error:
        raise StageCContractError("decision_time_utc must be RFC3339") from error
    if parsed.tzinfo is None:
        raise StageCContractError("decision_time_utc must include a timezone")


def extract_source_rows(anchor: PerAnchorEvaluation) -> tuple[SourceRow, ...]:
    """Turn one engine adapter output into authenticated per-action rows."""

    _validate_anchor(anchor)
    legal_mask = tuple(bool(item.legal) for item in anchor.actions)
    rows: list[SourceRow] = []
    for action_index, item in enumerate(anchor.actions):
        if not item.legal:
            continue
        if len(item.forecasts) != 3:
            raise StageCContractError("Q2 requires exactly three forecast offsets")
        for field in (
            "source_provenance_sha256",
            "forecast_method_sha256",
            "visible_primitives_sha256",
        ):
            value = getattr(item, field)
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise StageCContractError(f"action {field} is not bound")
        if item.visible_primitives_sha256 != canonical_sha256(_action_visible_payload(item)):
            raise StageCContractError("dependency-allowlist provenance does not match consumed values")
        if item.future_tle_access != "declared_forecast_horizon_only":
            raise StageCContractError("future TLE access exceeds the declared horizon")
        if item.tle_provenance not in {
            "nearest_epoch_retrospective_benchmark",
            "causal_ephemeris_available_by_decision_time",
        }:
            raise StageCContractError("TLE provenance is undeclared")
        if (
            item.refresh_phase not in range(4)
            or item.background_occupancy_excluding_focal < 0
            or item.previous_served_load_for_action < 0
            or item.remaining_d2_time_s < 0.0
            or item.remaining_visibility_time_s < 0.0
            or item.nominal_required_power_over_cap < 0.0
            or item.previous_beam_max_rf_over_cap < 0.0
        ):
            raise StageCContractError("action state violates range invariants")
        q1_raw = (
            item.nominal_sinr_margin_at_rate_target_db,
            item.nominal_required_power_over_cap,
            item.nominal_mode_spectral_efficiency,
            float(item.background_occupancy_excluding_focal),
            float(item.beam_active_before_focal),
            float(item.satellite_active_before_focal),
            item.off_axis_angle_rad,
            item.remaining_d2_time_s,
            item.remaining_visibility_time_s,
            float(item.refresh_phase),
            float(item.previous_served_association_for_action),
            float(item.previous_served_load_for_action),
            float(item.previous_beam_active_for_action),
            float(item.previous_satellite_active_for_action),
            item.previous_beam_max_rf_over_cap,
            float(item.missing_incumbent),
        )
        q2_raw: list[float] = [
            item.candidate_current_nominal_decoding_margin_db,
            item.forecast_se_trend_bit_s_hz_per_s,
            item.remaining_d2_time_s,
            item.remaining_visibility_time_s,
            float(item.refresh_phase),
            float(item.background_occupancy_excluding_focal),
            float(item.beam_active_before_focal),
            float(item.satellite_active_before_focal),
            item.required_power_cap_margin_w,
            float(item.missing_incumbent),
        ]
        for forecast in item.forecasts:
            q2_raw.extend(
                (
                    float(forecast.valid),
                    float(forecast.survival),
                    forecast.minimum_decoding_margin_db,
                    forecast.mean_acm_spectral_efficiency,
                )
            )
        kappa = float(anchor.kappa_normalization_bits)
        labels = (item.c1_label_bits, item.c2_label_bits)
        if not all(math.isfinite(label) for label in (*labels, item.c1_phi_difference)):
            raise StageCContractError("labels must be finite")
        rows.append(
            SourceRow(
                schema=ROW_SCHEMA_VERSION,
                split=anchor.split,
                world_id=anchor.world_id,
                world_seed=anchor.world_seed,
                learner_seed=None,
                anchor_id=anchor.anchor_id,
                anchor_index=anchor.anchor_index,
                decision_time_utc=anchor.decision_time_utc,
                decision_time_ns=anchor.decision_time_ns,
                user_id=anchor.user_id,
                action_index=action_index,
                action=item.action,
                reference_action=action_index == anchor.base_action_index,
                action_mask=legal_mask,
                q1_state=_normalize(q1_raw, Q1_FEATURES),
                q2_state=_normalize(q2_raw, Q2_FEATURES),
                incumbent_context_nominal_decoding_margin_db_hex=float_hex(
                    item.incumbent_nominal_decoding_margin_db
                ),
                q1_schema_sha256=Q1_SCHEMA_SHA256,
                q2_schema_sha256=Q2_SCHEMA_SHA256,
                setting_id=anchor.setting_id,
                code_digest=anchor.code_digest,
                physics_digest=anchor.physics_digest,
                launch_digest=anchor.launch_digest,
                catalogue_digest=anchor.catalogue_digest,
                setting_digest=anchor.setting_digest,
                calibration_digest=anchor.calibration_digest,
                provider_digest=anchor.provider_digest,
                archive_digest=anchor.archive_digest,
                allocation_manifest_digest=anchor.allocation_manifest_digest,
                lambda_bits_per_j_hex=float_hex(anchor.lambda_bits_per_j),
                eta_ref_bits_per_j_hex=float_hex(anchor.eta_ref_bits_per_j),
                kappa_normalization_bits_hex=float_hex(kappa),
                c1_label_bits_hex=float_hex(labels[0]),
                c1_phi_difference_hex=float_hex(item.c1_phi_difference),
                c2_label_bits_hex=float_hex(labels[1]),
                c1_label_normalized_hex=float_hex(
                    labels[0] / kappa + item.c1_phi_difference
                ),
                c2_label_normalized_hex=float_hex(labels[1] / kappa),
                source_provenance_sha256=item.source_provenance_sha256,
                forecast_method_sha256=item.forecast_method_sha256,
                visible_primitives_sha256=item.visible_primitives_sha256,
                tle_provenance=item.tle_provenance,
                future_tle_access=item.future_tle_access,
                terminal=item.terminal,
                null_action=item.action.is_null,
                outage=item.outage,
            )
        )
    if not rows:
        raise StageCContractError("anchor has no retained legal action rows")
    return tuple(rows)


def schema_manifest() -> dict[str, object]:
    return {
        "q1": {**Q1_SCHEMA, "sha256": Q1_SCHEMA_SHA256},
        "q2": {**Q2_SCHEMA, "sha256": Q2_SCHEMA_SHA256},
        "row_schema": ROW_SCHEMA_VERSION,
        "background_semantics": {
            "source": "previous committed served set",
            "focal_user": "excluded",
            "timestamp": "decision instant",
            "activation": "before focal insertion",
        },
    }


__all__ = [
    "ActionEvaluation",
    "FeatureSpec",
    "ForecastObservation",
    "PerAnchorEvaluation",
    "PhysicalAction",
    "Q1_FEATURES",
    "Q1_SCHEMA_SHA256",
    "Q2_FEATURES",
    "Q2_SCHEMA_SHA256",
    "SourceRow",
    "extract_source_rows",
    "kappa_normalization_bits",
    "schema_manifest",
    "seal_action_evaluation",
]
