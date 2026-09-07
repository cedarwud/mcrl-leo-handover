"""W-49 — route-safe selector-to-opening materialization."""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.action_contract import Association, NO_OP_ACTION
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.runtime.ee_axis_c1_selector import (
    C1_ACRM_PAIR_RULE,
    C1_CLUSTER_NEUTRAL_SOURCE_RULE,
    C1_INFORMED_SOURCE_RULE,
    C1UnilateralOpportunity,
)
from mcrl.runtime.ee_axis_opening_runner import (
    OpeningRunnerContractError,
    materialize_opening_opportunity,
)
from mcrl.runtime.ee_axis_source_selectors import (
    C3_INFORMED_SOURCE_RULE,
    C3UnilateralOpportunity,
)
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
    encode_ee_axis_state,
)


_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)
MANIFEST = "b" * 64
CHECKPOINT = "c" * 64


def _environment():
    field = KeyedFadingField.from_components("w49-test", 1, 4)
    environment = StepEnvironment(
        ScenarioDriver(
            TleArchive(_ARCHIVE),
            ScenarioConfig(mobility=MobilityConfig(num_users=4)),
        ),
        fading_field=field,
    )
    rng = np.random.default_rng(2026083109)
    observation = environment.reset(START, rng)
    return environment, observation, rng, field


def _physical_key(table, action: int) -> tuple[int, int] | None:
    if int(action) == NO_OP_ACTION:
        return None
    association = table.association(int(action))
    if not isinstance(association, Association):
        return None
    return int(association.norad_id), int(association.cell_id)


def _c1_opportunity(observation) -> C1UnilateralOpportunity:
    reference = np.full(observation.num_users, NO_OP_ACTION, dtype=np.int64)
    for uid, mask in enumerate(observation.masks):
        valid = np.flatnonzero(mask)
        if valid.size:
            reference[uid] = int(valid[0])
    for focal_user, table in enumerate(observation.candidates.slot_tables):
        reference_key = _physical_key(table, int(reference[focal_user]))
        for action in np.flatnonzero(table.mask).tolist():
            candidate_key = _physical_key(table, int(action))
            if candidate_key is None or candidate_key == reference_key:
                continue
            candidate = reference.copy()
            candidate[focal_user] = int(action)
            return C1UnilateralOpportunity(
                anchor_sha256="a" * 64,
                source_record_sha256="d" * 64,
                source_manifest_sha256=MANIFEST,
                checkpoint_sha256=CHECKPOINT,
                state_schema=EE_AXIS_STATE_SCHEMA,
                state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
                step_index=int(observation.step_index),
                source_rule=C1_INFORMED_SOURCE_RULE,
                acrm_pair_rule=C1_ACRM_PAIR_RULE,
                anchor_rank=0,
                anchor_stratum="lower",
                focal_user=focal_user,
                user_rank=0,
                user_stratum="lower",
                reference_action=int(reference[focal_user]),
                candidate_action=int(action),
                reference_physical_key=reference_key,
                candidate_physical_key=candidate_key,
                reference_actions=reference,
                candidate_actions=candidate,
                action_mask=table.mask,
            )
    pytest.skip("fixture has no unilateral physical alternative")


def _c3_opportunity(environment, observation) -> C3UnilateralOpportunity:
    c1 = _c1_opportunity(observation)
    state = encode_ee_axis_state(environment, observation)
    return C3UnilateralOpportunity(
        anchor_sha256=c1.anchor_sha256,
        step_index=c1.step_index,
        source_rule=C3_INFORMED_SOURCE_RULE,
        focal_user=c1.focal_user,
        reference_action=c1.reference_action,
        candidate_action=c1.candidate_action,
        reference_physical_key=c1.reference_physical_key,
        candidate_physical_key=c1.candidate_physical_key,
        reference_actions=c1.reference_actions,
        candidate_actions=c1.candidate_actions,
        state=state.state_matrix[c1.focal_user],
        action_mask=state.action_masks[c1.focal_user],
        lagged_eligible_load=0.0,
        previous_beam_active=False,
        previous_satellite_active=False,
        previous_max_required_link_power=0.0,
        competitive_score=0.0,
    )


@requires_archive
def test_c1_opportunity_materializes_only_as_c1_admission() -> None:
    environment, observation, rng, field = _environment()
    opportunity = _c1_opportunity(observation)
    state = encode_ee_axis_state(environment, observation)
    result = materialize_opening_opportunity(
        environment,
        observation=observation,
        state_observation=state,
        opportunity=opportunity,
        source_policy_version=1,
        source_manifest_sha256=MANIFEST,
        checkpoint_sha256=CHECKPOINT,
        common_random_field=field,
        other_route_source_rule="c3-audit-view-only-v1",
        rng=rng,
        lambda_bits_per_j=10.0,
        interval_s=float(environment.driver.config.ephemeris.time_step_s),
    )
    assert result.admitted_route == "C1"
    assert result.c1.pair.source_rule == C1_INFORMED_SOURCE_RULE
    assert result.c3.pair.source_rule == "c3-audit-view-only-v1"


@requires_archive
def test_cluster_matched_c1_neutral_rule_materializes_as_c1() -> None:
    environment, observation, rng, field = _environment()
    opportunity = replace(
        _c1_opportunity(observation),
        source_rule=C1_CLUSTER_NEUTRAL_SOURCE_RULE,
    )
    state = encode_ee_axis_state(environment, observation)
    result = materialize_opening_opportunity(
        environment,
        observation=observation,
        state_observation=state,
        opportunity=opportunity,
        source_policy_version=1,
        source_manifest_sha256=MANIFEST,
        checkpoint_sha256=CHECKPOINT,
        common_random_field=field,
        other_route_source_rule="c3-audit-view-only-v1",
        rng=rng,
        lambda_bits_per_j=10.0,
        interval_s=float(environment.driver.config.ephemeris.time_step_s),
    )
    assert result.admitted_route == "C1"
    assert result.c1.pair.source_rule == C1_CLUSTER_NEUTRAL_SOURCE_RULE


@requires_archive
def test_c3_opportunity_materializes_only_as_c3_admission() -> None:
    environment, observation, rng, field = _environment()
    opportunity = _c3_opportunity(environment, observation)
    state = encode_ee_axis_state(environment, observation)
    result = materialize_opening_opportunity(
        environment,
        observation=observation,
        state_observation=state,
        opportunity=opportunity,
        source_policy_version=1,
        source_manifest_sha256=MANIFEST,
        checkpoint_sha256=CHECKPOINT,
        common_random_field=field,
        other_route_source_rule="c1-audit-view-only-v1",
        rng=rng,
        lambda_bits_per_j=10.0,
        interval_s=float(environment.driver.config.ephemeris.time_step_s),
    )
    assert result.admitted_route == "C3"
    assert result.c1.pair.source_rule == "c1-audit-view-only-v1"
    assert result.c3.pair.source_rule == C3_INFORMED_SOURCE_RULE


@requires_archive
def test_runner_rejects_stale_step_and_lineage() -> None:
    environment, observation, rng, field = _environment()
    opportunity = _c1_opportunity(observation)
    state = encode_ee_axis_state(environment, observation)
    with pytest.raises(OpeningRunnerContractError, match="source manifest"):
        materialize_opening_opportunity(
            environment,
            observation=observation,
            state_observation=state,
            opportunity=opportunity,
            source_policy_version=1,
            source_manifest_sha256="e" * 64,
            checkpoint_sha256=CHECKPOINT,
            common_random_field=field,
            other_route_source_rule="c3-audit-view-only-v1",
            rng=rng,
            lambda_bits_per_j=10.0,
            interval_s=30.0,
        )

    environment.step(opportunity.reference_actions, rng)
    with pytest.raises(
        OpeningRunnerContractError,
        match="current (?:predecision|opening) anchor",
    ):
        materialize_opening_opportunity(
            environment,
            observation=observation,
            state_observation=state,
            opportunity=opportunity,
            source_policy_version=1,
            source_manifest_sha256=MANIFEST,
            checkpoint_sha256=CHECKPOINT,
            common_random_field=field,
            other_route_source_rule="c3-audit-view-only-v1",
            rng=rng,
            lambda_bits_per_j=10.0,
            interval_s=30.0,
        )
