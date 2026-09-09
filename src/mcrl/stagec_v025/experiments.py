"""Four non-conflated C3 experiment schemas from contract C3."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Mapping

from .canonical import StageCContractError, canonical_sha256


LEARNED_NEUTRAL_SCHEMA = "mcrl-v025-learned-neutral-source-experiment-v1"
ORACLE_REMOVAL_SCHEMA = "mcrl-v025-oracle-factor-score-removal-v1"
CHECKPOINT_KNOCKOUT_SCHEMA = "mcrl-v025-checkpoint-knockout-v1"
ARCHITECTURE_REMOVAL_SCHEMA = "mcrl-v025-architecture-removal-v1"


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
            self.schema != LEARNED_NEUTRAL_SCHEMA
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
            self.schema != ORACLE_REMOVAL_SCHEMA
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
            self.schema != CHECKPOINT_KNOCKOUT_SCHEMA
            or set(self.zeroed_deployed_routes) != {"C1", "C2", "C3"}
            or not self.decision_machinery_fixed
            or len(self.checkpoint_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.checkpoint_sha256)
        ):
            raise StageCContractError("checkpoint knockout experiment schema drifted")


@dataclass(frozen=True, slots=True)
class ArchitectureRemovalExperiment:
    schema: Literal["mcrl-v025-architecture-removal-v1"]
    status: Literal["NAMED_NOT_RUN"] = "NAMED_NOT_RUN"
    reason: str = "outside_stage_c_claim_scope"

    def __post_init__(self) -> None:
        if (
            self.schema != ARCHITECTURE_REMOVAL_SCHEMA
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


@dataclass(frozen=True, slots=True)
class BoundExperiment:
    """C3 execution authority carried by allocation, runner, and receipt."""

    experiment_id: str
    schema: str
    definition_sha256: str
    execution_kind: Literal[
        "learned_neutral_source",
        "oracle_factor_score_removal",
        "checkpoint_knockout",
        "architecture_removal_named_not_run",
    ]
    runnable: bool
    checkpoint_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.experiment_id:
            raise StageCContractError("bound experiment requires a run identity")
        if len(self.definition_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.definition_sha256
        ):
            raise StageCContractError("experiment definition digest is invalid")
        expected = {
            LEARNED_NEUTRAL_SCHEMA: ("learned_neutral_source", True),
            ORACLE_REMOVAL_SCHEMA: ("oracle_factor_score_removal", True),
            CHECKPOINT_KNOCKOUT_SCHEMA: ("checkpoint_knockout", True),
            ARCHITECTURE_REMOVAL_SCHEMA: (
                "architecture_removal_named_not_run",
                False,
            ),
        }.get(self.schema)
        if expected is None or expected != (self.execution_kind, self.runnable):
            raise StageCContractError("experiment schema/execution binding drifted")
        if self.execution_kind == "checkpoint_knockout":
            if (
                self.checkpoint_sha256 is None
                or len(self.checkpoint_sha256) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in self.checkpoint_sha256
                )
            ):
                raise StageCContractError("checkpoint knockout is not checkpoint-bound")
        elif self.checkpoint_sha256 is not None:
            raise StageCContractError("only knockout execution may bind a checkpoint")


def bind_experiment(experiment_id: str, experiment: Experiment) -> BoundExperiment:
    """Create the only allocation authority accepted for a named experiment."""

    if isinstance(experiment, LearnedNeutralSourceExperiment):
        kind = "learned_neutral_source"
        runnable = True
        checkpoint = None
    elif isinstance(experiment, OracleFactorScoreRemovalExperiment):
        kind = "oracle_factor_score_removal"
        runnable = True
        checkpoint = None
    elif isinstance(experiment, CheckpointKnockoutExperiment):
        kind = "checkpoint_knockout"
        runnable = True
        checkpoint = experiment.checkpoint_sha256
    else:
        kind = "architecture_removal_named_not_run"
        runnable = False
        checkpoint = None
    return BoundExperiment(
        experiment_id=experiment_id,
        schema=experiment.schema,
        definition_sha256=experiment_digest(experiment),
        execution_kind=kind,
        runnable=runnable,
        checkpoint_sha256=checkpoint,
    )


def validate_experiment_execution(
    binding: BoundExperiment,
    *,
    experiment_id: str,
    schema: str,
    definition_sha256: str,
    execution_kind: str,
    checkpoint_sha256: str | None,
) -> None:
    supplied: Mapping[str, object] = {
        "experiment_id": experiment_id,
        "schema": schema,
        "definition_sha256": definition_sha256,
        "execution_kind": execution_kind,
        "checkpoint_sha256": checkpoint_sha256,
    }
    expected: Mapping[str, object] = {
        "experiment_id": binding.experiment_id,
        "schema": binding.schema,
        "definition_sha256": binding.definition_sha256,
        "execution_kind": binding.execution_kind,
        "checkpoint_sha256": binding.checkpoint_sha256,
    }
    if supplied != expected or not binding.runnable:
        raise StageCContractError("allocation is mislabelled for its experiment execution")


__all__ = [
    "ArchitectureRemovalExperiment",
    "ARCHITECTURE_REMOVAL_SCHEMA",
    "BoundExperiment",
    "CHECKPOINT_KNOCKOUT_SCHEMA",
    "CheckpointKnockoutExperiment",
    "Experiment",
    "LEARNED_NEUTRAL_SCHEMA",
    "LearnedNeutralSourceExperiment",
    "ORACLE_REMOVAL_SCHEMA",
    "OracleFactorScoreRemovalExperiment",
    "bind_experiment",
    "experiment_digest",
    "validate_experiment_execution",
]
