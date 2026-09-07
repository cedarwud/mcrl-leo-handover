"""W-43 — real-environment V0.3 opening-source producer."""

from __future__ import annotations

import copy
import datetime as dt
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
from mcrl.runtime.ee_axis_opening_pairs import (
    OpeningPairContractError,
    build_opening_route_batch,
)
from mcrl.runtime.ee_axis_opening_source import (
    OpeningSourceContractError,
    OpeningSourceProvenance,
    produce_opening_comparison,
)
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
    encode_ee_axis_state,
)


_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)


def _environment(*, keyed: bool = True, users: int = 4):
    field = (
        KeyedFadingField.from_components("w43-test", 1, users)
        if keyed
        else None
    )
    environment = StepEnvironment(
        ScenarioDriver(
            TleArchive(_ARCHIVE),
            ScenarioConfig(mobility=MobilityConfig(num_users=users)),
        ),
        fading_field=field,
    )
    rng = np.random.default_rng(2026083101)
    observation = environment.reset(START, rng)
    return environment, observation, rng, field


def _physical_key(table, action: int) -> tuple[int, int] | None:
    if int(action) == NO_OP_ACTION:
        return None
    association = table.association(int(action))
    if not isinstance(association, Association):
        return None
    return int(association.norad_id), int(association.cell_id)


def _sealed_action_pair(observation):
    reference = np.full(observation.num_users, NO_OP_ACTION, dtype=np.int64)
    for uid, mask in enumerate(observation.masks):
        valid = np.flatnonzero(mask)
        if valid.size:
            reference[uid] = int(valid[0])

    for focal_user, table in enumerate(observation.candidates.slot_tables):
        reference_key = _physical_key(table, int(reference[focal_user]))
        valid = np.flatnonzero(observation.masks[focal_user])
        for action in valid.tolist():
            if _physical_key(table, int(action)) != reference_key:
                candidate = reference.copy()
                candidate[focal_user] = int(action)
                return focal_user, reference, candidate
    pytest.skip("fixture has no user with two distinct legal physical actions")


def _provenance(field: KeyedFadingField) -> OpeningSourceProvenance:
    return OpeningSourceProvenance(
        source_policy_version=7,
        anchor_sha256="a" * 64,
        source_manifest_sha256="b" * 64,
        checkpoint_sha256="c" * 64,
        common_random_field_sha256=field.root_digest,
        c1_source_rule="sealed-c1-test-rule",
        c3_source_rule="sealed-c3-test-rule",
        admitted_route="C1",
    )


def _produce(environment, observation, rng, field, reference, candidate, focal):
    assert field is not None
    return produce_opening_comparison(
        environment,
        observation=observation,
        state_observation=encode_ee_axis_state(environment, observation),
        reference_actions=reference,
        candidate_actions=candidate,
        focal_user=focal,
        common_random_field=field,
        provenance=_provenance(field),
        rng=rng,
        lambda_bits_per_j=10.0,
        interval_s=float(environment.driver.config.ephemeris.time_step_s),
    )


@requires_archive
def test_source_evaluates_both_branches_without_committing_or_consuming_rng():
    environment, observation, rng, field = _environment()
    focal, reference, candidate = _sealed_action_pair(observation)
    before_rng = copy.deepcopy(rng.bit_generator.state)
    before_user_ecef = environment.driver.user_ecef_km().copy()
    before_candidates = environment._candidates
    before_segments = list(environment._segments)
    before_step = environment.driver.step_index

    result = _produce(
        environment, observation, rng, field, reference, candidate, focal
    )

    assert result.reference_evaluation is not result.candidate_evaluation
    assert environment.driver.step_index == before_step
    assert environment._step_index == before_step
    assert environment._candidates is before_candidates
    assert environment._segments == before_segments
    assert np.array_equal(environment.driver.user_ecef_km(), before_user_ecef)
    assert rng.bit_generator.state == before_rng

    committed = environment.step(reference, rng)
    assert np.array_equal(
        result.reference_evaluation.link_rate_bps, committed.link_rate_bps
    )
    assert result.reference_evaluation.system_power_w == committed.system_power_w


@requires_archive
def test_source_requires_the_supplied_keyed_field_to_be_bound_to_environment():
    environment, observation, rng, field = _environment()
    focal, reference, candidate = _sealed_action_pair(observation)
    assert field is not None

    foreign = KeyedFadingField.from_components("w43-foreign", 1, 4)
    with pytest.raises(OpeningSourceContractError, match="keyed fading field"):
        produce_opening_comparison(
            environment,
            observation=observation,
            state_observation=encode_ee_axis_state(environment, observation),
            reference_actions=reference,
            candidate_actions=candidate,
            focal_user=focal,
            common_random_field=foreign,
            provenance=_provenance(foreign),
            rng=rng,
            lambda_bits_per_j=10.0,
            interval_s=float(environment.driver.config.ephemeris.time_step_s),
        )

    plain_environment, plain_observation, plain_rng, _ = _environment(keyed=False)
    plain_focal, plain_reference, plain_candidate = _sealed_action_pair(
        plain_observation
    )
    with pytest.raises(OpeningSourceContractError, match="keyed fading field"):
        produce_opening_comparison(
            plain_environment,
            observation=plain_observation,
            state_observation=encode_ee_axis_state(
                plain_environment, plain_observation
            ),
            reference_actions=plain_reference,
            candidate_actions=plain_candidate,
            focal_user=plain_focal,
            common_random_field=field,
            provenance=_provenance(field),
            rng=plain_rng,
            lambda_bits_per_j=10.0,
            interval_s=float(plain_environment.driver.config.ephemeris.time_step_s),
        )


@requires_archive
def test_result_preserves_one_raw_lineage_and_exposes_isolated_q1_q3_views():
    environment, observation, rng, field = _environment()
    focal, reference, candidate = _sealed_action_pair(observation)
    result = _produce(
        environment, observation, rng, field, reference, candidate, focal
    )

    assert result.raw_pair.state.shape == (EE_AXIS_STATE_DIM,)
    assert result.raw_pair.state_schema == EE_AXIS_STATE_SCHEMA
    assert result.raw_pair.state_schema_sha256 == EE_AXIS_STATE_SCHEMA_SHA256
    assert result.raw_pair.state_observation_sha256 == encode_ee_axis_state(
        environment, observation
    ).state_sha256
    assert result.verify() == result.raw_pair.comparison_sha256
    assert result.admitted_route == "C1"
    assert result.c1.route == "C1"
    assert result.c3.route == "C3"
    assert result.c1.raw_comparison_sha256 == result.raw_pair.comparison_sha256
    assert result.c3.raw_comparison_sha256 == result.raw_pair.comparison_sha256
    assert result.c1.pair.route_target_surplus_bits == pytest.approx(
        result.c1.pair.zeta1_focal_surplus_bits
    )
    assert result.c3.pair.route_target_surplus_bits == pytest.approx(
        result.c3.pair.zeta3_nonfocal_externality_bits
    )
    assert result.c1.pair.comparison_sha256 != result.c3.pair.comparison_sha256
    assert (
        result.raw_pair.reference_physical_keys[focal]
        != result.raw_pair.candidate_physical_keys[focal]
    )
    assert all(
        result.raw_pair.reference_physical_keys[uid]
        == result.raw_pair.candidate_physical_keys[uid]
        for uid in range(observation.num_users)
        if uid != focal
    )
    assert np.array_equal(
        result.c1.pair.reference_rates_bps,
        result.c3.pair.reference_rates_bps,
    )

    assert build_opening_route_batch([result.c1.as_pair()]).route == "C1"
    assert build_opening_route_batch([result.c3.as_pair()]).route == "C3"
    with pytest.raises(OpeningPairContractError, match="cannot mix"):
        build_opening_route_batch([result.c1.as_pair(), result.c3.as_pair()])


@requires_archive
def test_source_rejects_identical_or_illegal_opening_actions():
    environment, observation, rng, field = _environment()
    focal, reference, candidate = _sealed_action_pair(observation)
    assert field is not None

    identical = reference.copy()
    with pytest.raises(OpeningSourceContractError, match="focal"):
        _produce(environment, observation, rng, field, reference, identical, focal)

    illegal = candidate.copy()
    illegal[focal] = 28
    with pytest.raises(OpeningSourceContractError, match="legal|range"):
        _produce(environment, observation, rng, field, reference, illegal, focal)


@requires_archive
def test_source_rejects_more_than_one_physical_focal_change():
    environment, observation, rng, field = _environment()
    focal, reference, candidate = _sealed_action_pair(observation)
    other = next(
        (
            uid
            for uid, mask in enumerate(observation.masks)
            if uid != focal and np.count_nonzero(mask) > 1
        ),
        None,
    )
    if other is None:
        pytest.skip("fixture has no second user with multiple legal actions")
    alternate = np.flatnonzero(observation.masks[other])
    bad = candidate.copy()
    table = observation.candidates.slot_tables[other]
    reference_key = _physical_key(table, int(reference[other]))
    replacement = next(
        int(action)
        for action in alternate.tolist()
        if _physical_key(table, int(action)) != reference_key
    )
    bad[other] = replacement
    with pytest.raises(OpeningSourceContractError, match="exactly the focal"):
        _produce(environment, observation, rng, field, reference, bad, focal)
