"""Contract-v1 information interfaces and matched-catalogue authentication."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from .canonical import StageCContractError, canonical_sha256
from .state import PhysicalAction


def _digest(value: str, field: str) -> str:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise StageCContractError(f"{field} must be a lowercase SHA-256")
    return value


@dataclass(frozen=True, slots=True)
class HeadsInformation:
    """A1: all and only information exposed to Q1/Q2 for one user."""

    anchor_id: str
    decision_time_ns: int
    user_id: int
    legal_actions: tuple[PhysicalAction, ...]
    q1_rows: tuple[tuple[float, ...], ...]
    q2_rows: tuple[tuple[float, ...], ...]
    incumbent_context_nominal_decoding_margin_db: float
    current_nominal_geometry_sha256: str
    own_history_sha256: str
    previous_committed_excluding_focal_sha256: str
    derived_feature_schema_sha256: str
    model_access: str = "none"
    compute_limit: str = "one_forward_pass"

    def __post_init__(self) -> None:
        if self.decision_time_ns < 0 or not self.legal_actions:
            raise StageCContractError("I_heads requires a nonempty dated legal action table")
        if not (
            len(self.legal_actions) == len(self.q1_rows) == len(self.q2_rows)
        ):
            raise StageCContractError("I_heads action and feature rows disagree")
        for field in (
            "current_nominal_geometry_sha256",
            "own_history_sha256",
            "previous_committed_excluding_focal_sha256",
            "derived_feature_schema_sha256",
        ):
            _digest(getattr(self, field), field)
        if self.model_access != "none" or self.compute_limit != "one_forward_pass":
            raise StageCContractError("I_heads model/compute access exceeds A1")


@dataclass(frozen=True, slots=True)
class ReferenceProfiles:
    """A3: score reference a0 and event/history reference are distinct."""

    proposal_a0: tuple[PhysicalAction, ...]
    previous_committed: tuple[PhysicalAction, ...]

    def __post_init__(self) -> None:
        if not self.proposal_a0 or len(self.proposal_a0) != len(self.previous_committed):
            raise StageCContractError("reference profiles must be complete and roster-aligned")


@dataclass(frozen=True, slots=True)
class CatalogueProfile:
    """One complete physical profile; user order is explicit and stable."""

    assignments: tuple[tuple[int, PhysicalAction], ...]

    def __post_init__(self) -> None:
        users = tuple(user for user, _ in self.assignments)
        if not users or users != tuple(sorted(users)) or len(set(users)) != len(users):
            raise StageCContractError("catalogue profile users must be nonempty, unique, sorted")

    def payload(self) -> list[dict[str, object]]:
        return [
            {"user_id": user, "action": action.payload()}
            for user, action in self.assignments
        ]


@dataclass(frozen=True, slots=True)
class NominalProfileOutput:
    """A2 nominal-model output made available for every catalogue profile."""

    profile_sha256: str
    joint_load: tuple[tuple[str, float], ...]
    coupled_powers_w: tuple[tuple[str, float], ...]
    interference_w: tuple[tuple[str, float], ...]
    activation: tuple[tuple[str, bool], ...]
    service_by_user: tuple[tuple[int, bool], ...]
    bits: float
    energy_j: float
    continuation_normalized: float

    def __post_init__(self) -> None:
        _digest(self.profile_sha256, "profile_sha256")
        if self.bits < 0.0 or self.energy_j < 0.0:
            raise StageCContractError("nominal profile bits/energy must be nonnegative")


@dataclass(frozen=True, slots=True)
class CoordinatorInformation:
    """A2: complete nominal joint information supplied at one anchor."""

    anchor_id: str
    decision_time_ns: int
    global_nominal_geometry_sha256: str
    beam_specific_cross_gains_sha256: str
    legal_sets_sha256: str
    previous_committed_sha256: str
    references: ReferenceProfiles
    catalogue: tuple[CatalogueProfile, ...]
    catalogue_sha256: str
    nominal_model_sha256: str
    nominal_outputs: tuple[NominalProfileOutput, ...]
    realised_fading_access: str = "none"
    future_tle_access: str = "declared_forecast_horizon_only"
    compute_budget_wall_s: float = 10.0

    def __post_init__(self) -> None:
        if self.decision_time_ns < 0 or not self.catalogue:
            raise StageCContractError("I_coordinator requires a nonempty dated catalogue")
        for field in (
            "global_nominal_geometry_sha256",
            "beam_specific_cross_gains_sha256",
            "legal_sets_sha256",
            "previous_committed_sha256",
            "catalogue_sha256",
            "nominal_model_sha256",
        ):
            _digest(getattr(self, field), field)
        expected = canonical_sha256([profile.payload() for profile in self.catalogue])
        if expected != self.catalogue_sha256:
            raise StageCContractError("I_coordinator catalogue digest is not authentic")
        expected_profiles = {
            canonical_sha256(profile.payload()) for profile in self.catalogue
        }
        if {output.profile_sha256 for output in self.nominal_outputs} != expected_profiles:
            raise StageCContractError("nominal outputs do not cover the catalogue exactly")
        if self.realised_fading_access != "none" or self.compute_budget_wall_s != 10.0:
            raise StageCContractError("I_coordinator violates the A2/F2 information budget")


@dataclass(frozen=True, slots=True)
class ArmInformationInterface:
    """A4 declaration authenticated between FULL and every comparator arm."""

    arm: str
    anchor_id: str
    decision_time_ns: int
    primitive_access_sha256: str
    forecast_method_sha256: str
    physical_identity_schema_sha256: str
    catalogue_sha256: str
    joint_search_sha256: str
    guards_sha256: str
    tie_breaking_sha256: str
    validation_sha256: str
    deadline_sha256: str
    fallback_sha256: str
    learned_pruning: bool
    removed_score_may_affect_ranking_pruning_or_guards: bool = False

    def __post_init__(self) -> None:
        for field in (
            "primitive_access_sha256",
            "forecast_method_sha256",
            "physical_identity_schema_sha256",
            "catalogue_sha256",
            "joint_search_sha256",
            "guards_sha256",
            "tie_breaking_sha256",
            "validation_sha256",
            "deadline_sha256",
            "fallback_sha256",
        ):
            _digest(getattr(self, field), field)
        if self.removed_score_may_affect_ranking_pruning_or_guards:
            raise StageCContractError("an exact evaluator may not restore a removed score")


def authenticate_matched_catalogues(
    interfaces: Mapping[str, ArmInformationInterface],
    *,
    required_arms: Sequence[str],
) -> str:
    """Authenticate A4 equality at one matched anchor and return its digest."""

    required = tuple(required_arms)
    if set(interfaces) != set(required):
        raise StageCContractError("matched-anchor interface arm inventory drifted")
    rows = tuple(interfaces[arm] for arm in required)
    common_fields = (
        "anchor_id",
        "decision_time_ns",
        "primitive_access_sha256",
        "forecast_method_sha256",
        "physical_identity_schema_sha256",
        "catalogue_sha256",
        "joint_search_sha256",
        "guards_sha256",
        "tie_breaking_sha256",
        "validation_sha256",
        "deadline_sha256",
        "fallback_sha256",
    )
    for field in common_fields:
        if len({getattr(row, field) for row in rows}) != 1:
            raise StageCContractError(f"matched-anchor A4 mismatch: {field}")
    # Learned pruning is allowed only when it is itself the declared
    # intervention, never as an unrecorded arm-specific catalogue change.
    if len({row.learned_pruning for row in rows}) != 1:
        raise StageCContractError("matched-anchor learned-pruning declaration differs")
    return canonical_sha256(
        {
            "schema": "mcrl-v025-stagec-matched-information-interface-v1",
            "required_arms": list(required),
            "common": {field: getattr(rows[0], field) for field in common_fields},
            "learned_pruning": rows[0].learned_pruning,
            "arms": [asdict(row) for row in rows],
        }
    )


__all__ = [
    "ArmInformationInterface",
    "CatalogueProfile",
    "CoordinatorInformation",
    "HeadsInformation",
    "NominalProfileOutput",
    "ReferenceProfiles",
    "authenticate_matched_catalogues",
]
