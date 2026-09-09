"""Route-safe materialization of sealed C1/C3 opening opportunities.

Selectors decide *which* unilateral comparison belongs to a Catfish route;
``ee_axis_opening_source`` evaluates the two actions.  This module is the
small fail-closed seam between those responsibilities.  In particular, it
binds the selector's admitted route to the current V0.3 state and prevents a
C1-selected row from being relabelled C3 (or vice versa).
"""

from __future__ import annotations

import numpy as np

from ..env.keyed_fading import KeyedFadingField
from ..env.step import StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_c1_selector import (
    C1_CLUSTER_NEUTRAL_SOURCE_RULE,
    C1_INFORMED_SOURCE_RULE,
    C1_NEUTRAL_SOURCE_RULE,
    C1UnilateralOpportunity,
)
from .ee_axis_opening_source import (
    EEAxisOpeningSourceResult,
    OpeningSourceProvenance,
    produce_opening_comparison,
)
from .ee_axis_source_selectors import (
    C3_INFORMED_SOURCE_RULE,
    C3_NEUTRAL_SOURCE_RULE,
    C3UnilateralOpportunity,
)
from .ee_axis_state import EEAxisStateObservation, encode_ee_axis_state


class OpeningRunnerContractError(MCRLContractError):
    """A selected opportunity cannot be materialized at this anchor."""


OpeningOpportunity = C1UnilateralOpportunity | C3UnilateralOpportunity


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise OpeningRunnerContractError(f"{field} must be lowercase SHA-256")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise OpeningRunnerContractError(f"{field} must be a nonempty trimmed string")
    return value


def materialize_opening_opportunity(
    environment: StepEnvironment,
    *,
    observation: StepObservation,
    state_observation: EEAxisStateObservation,
    opportunity: OpeningOpportunity,
    source_policy_version: int,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    common_random_field: KeyedFadingField,
    other_route_source_rule: str,
    rng: np.random.Generator,
    lambda_bits_per_j: float,
    interval_s: float,
) -> EEAxisOpeningSourceResult:
    """Evaluate one selector-emitted opportunity under its sealed route.

    ``other_route_source_rule`` names the audit-only projection of the same
    raw comparison.  It never changes the admitted gradient route.
    """

    if not isinstance(environment, StepEnvironment):
        raise OpeningRunnerContractError("environment must be StepEnvironment")
    if not isinstance(observation, StepObservation):
        raise OpeningRunnerContractError("observation must be StepObservation")
    if not isinstance(state_observation, EEAxisStateObservation):
        raise OpeningRunnerContractError(
            "state_observation must be EEAxisStateObservation"
        )
    if not isinstance(common_random_field, KeyedFadingField):
        raise OpeningRunnerContractError(
            "common_random_field must be KeyedFadingField"
        )
    if not isinstance(rng, np.random.Generator):
        raise OpeningRunnerContractError("rng must be numpy.random.Generator")
    if type(source_policy_version) is not int or source_policy_version <= 0:
        raise OpeningRunnerContractError(
            "source_policy_version must be a positive exact integer"
        )
    _digest(source_manifest_sha256, field="source_manifest_sha256")
    _digest(checkpoint_sha256, field="checkpoint_sha256")
    _text(other_route_source_rule, field="other_route_source_rule")

    try:
        opportunity.verify()
        state_observation.verify()
        current_state = encode_ee_axis_state(environment, observation)
    except MCRLContractError as error:
        raise OpeningRunnerContractError(str(error)) from error
    if state_observation.state_sha256 != current_state.state_sha256:
        raise OpeningRunnerContractError(
            "state observation does not match the current opening anchor"
        )
    if opportunity.step_index != int(observation.step_index):
        raise OpeningRunnerContractError(
            "opportunity step does not match the current opening anchor"
        )
    focal_user = opportunity.focal_user
    if not 0 <= focal_user < observation.num_users:
        raise OpeningRunnerContractError("opportunity focal user is outside anchor")
    if not np.array_equal(
        opportunity.action_mask, state_observation.action_masks[focal_user]
    ):
        raise OpeningRunnerContractError(
            "opportunity mask does not match the current opening anchor"
        )

    if isinstance(opportunity, C1UnilateralOpportunity):
        admitted_route = "C1"
        if opportunity.source_rule not in (
            C1_CLUSTER_NEUTRAL_SOURCE_RULE,
            C1_INFORMED_SOURCE_RULE,
            C1_NEUTRAL_SOURCE_RULE,
        ):
            raise OpeningRunnerContractError("unsupported C1 opportunity source rule")
        if opportunity.source_manifest_sha256 != source_manifest_sha256:
            raise OpeningRunnerContractError(
                "C1 opportunity source manifest disagrees with runner"
            )
        if opportunity.checkpoint_sha256 != checkpoint_sha256:
            raise OpeningRunnerContractError(
                "C1 opportunity checkpoint disagrees with runner"
            )
        if (
            opportunity.state_schema != state_observation.schema
            or opportunity.state_schema_sha256 != state_observation.schema_sha256
        ):
            raise OpeningRunnerContractError("C1 opportunity state lineage drifted")
        c1_source_rule = opportunity.source_rule
        c3_source_rule = other_route_source_rule
    elif isinstance(opportunity, C3UnilateralOpportunity):
        admitted_route = "C3"
        if opportunity.source_rule not in (
            C3_INFORMED_SOURCE_RULE,
            C3_NEUTRAL_SOURCE_RULE,
        ):
            raise OpeningRunnerContractError("unsupported C3 opportunity source rule")
        if not np.array_equal(
            opportunity.state, state_observation.state_matrix[focal_user]
        ):
            raise OpeningRunnerContractError(
                "C3 opportunity state does not match the current opening anchor"
            )
        c1_source_rule = other_route_source_rule
        c3_source_rule = opportunity.source_rule
    else:  # pragma: no cover - kept explicit for fail-closed public callers
        raise OpeningRunnerContractError(
            "opportunity must be a C1 or C3 unilateral opportunity"
        )

    provenance = OpeningSourceProvenance(
        source_policy_version=source_policy_version,
        anchor_sha256=opportunity.anchor_sha256,
        source_manifest_sha256=source_manifest_sha256,
        checkpoint_sha256=checkpoint_sha256,
        common_random_field_sha256=common_random_field.root_digest,
        c1_source_rule=c1_source_rule,
        c3_source_rule=c3_source_rule,
        admitted_route=admitted_route,
    )
    try:
        result = produce_opening_comparison(
            environment,
            observation=observation,
            state_observation=state_observation,
            reference_actions=opportunity.reference_actions,
            candidate_actions=opportunity.candidate_actions,
            focal_user=focal_user,
            common_random_field=common_random_field,
            provenance=provenance,
            rng=rng,
            lambda_bits_per_j=lambda_bits_per_j,
            interval_s=interval_s,
        )
    except MCRLContractError as error:
        raise OpeningRunnerContractError(str(error)) from error
    if result.admitted_route != admitted_route:
        raise OpeningRunnerContractError("opening producer changed admitted route")
    return result


__all__ = [
    "OpeningOpportunity",
    "OpeningRunnerContractError",
    "materialize_opening_opportunity",
]
