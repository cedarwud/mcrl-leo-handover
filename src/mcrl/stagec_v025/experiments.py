"""Four non-conflated C3 experiment schemas from contract C3."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from .canonical import StageCContractError, canonical_sha256


@dataclass(frozen=True, slots=True)
class LearnedNeutralSourceExperiment:
    schema: Literal["mcrl-v025-learned-neutral-source-experiment-v1"]
    arms: tuple[str, ...]
    neutral_source_digests: tuple[tuple[str, str], ...]
    all_heads_retained_updated_deployed: bool
    estimand_wording: str

    def __post_init__(self) -> None:
        required = {"FULL", "DROP_C1", "DROP_C2", "DROP_C3", "ALL_NEUTRAL_CONTROL", "BASELINE"}
        if (
            self.schema != "mcrl-v025-learned-neutral-source-experiment-v1"
            or set(self.arms) != required
            or not self.all_heads_retained_updated_deployed
        ):
            raise StageCContractError("learned neutral-source experiment schema drifted")


@dataclass(frozen=True, slots=True)
class OracleFactorScoreRemovalExperiment:
    schema: Literal["mcrl-v025-oracle-factor-score-removal-v1"]
    removed_routes: tuple[str, ...]
    exact_score_terms: bool
    purpose: str = "physics_regime_map"

    def __post_init__(self) -> None:
        if (
            self.schema != "mcrl-v025-oracle-factor-score-removal-v1"
            or set(self.removed_routes) != {"C1", "C2", "C3"}
            or not self.exact_score_terms
        ):
            raise StageCContractError("oracle factor-score experiment schema drifted")


@dataclass(frozen=True, slots=True)
class CheckpointKnockoutExperiment:
    schema: Literal["mcrl-v025-checkpoint-knockout-v1"]
    checkpoint_sha256: str
    zeroed_deployed_routes: tuple[str, ...]
    decision_machinery_fixed: bool
    measures: str = "deployment_reliance_and_hidden_score_restoration"

    def __post_init__(self) -> None:
        if (
            self.schema != "mcrl-v025-checkpoint-knockout-v1"
            or set(self.zeroed_deployed_routes) != {"C1", "C2", "C3"}
            or not self.decision_machinery_fixed
        ):
            raise StageCContractError("checkpoint knockout experiment schema drifted")


@dataclass(frozen=True, slots=True)
class ArchitectureRemovalExperiment:
    schema: Literal["mcrl-v025-architecture-removal-v1"]
    status: Literal["NAMED_NOT_RUN"] = "NAMED_NOT_RUN"
    reason: str = "outside_stage_c_build_2"

    def __post_init__(self) -> None:
        if (
            self.schema != "mcrl-v025-architecture-removal-v1"
            or self.status != "NAMED_NOT_RUN"
        ):
            raise StageCContractError("architecture removal experiment schema drifted")


Experiment = (
    LearnedNeutralSourceExperiment
    | OracleFactorScoreRemovalExperiment
    | CheckpointKnockoutExperiment
    | ArchitectureRemovalExperiment
)


def experiment_digest(experiment: Experiment) -> str:
    return canonical_sha256(asdict(experiment))


__all__ = [
    "ArchitectureRemovalExperiment",
    "CheckpointKnockoutExperiment",
    "Experiment",
    "LearnedNeutralSourceExperiment",
    "OracleFactorScoreRemovalExperiment",
    "experiment_digest",
]
