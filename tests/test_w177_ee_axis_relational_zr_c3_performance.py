"""W-177 -- differential and call-budget checks for nominal relational C3.

The slow reference below intentionally mirrors the original branch-by-branch
implementation.  Production code must remain numerically equivalent while it
avoids rebuilding full-network interference for every focal action.
"""

from __future__ import annotations

import math
import runpy
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS
import mcrl.runtime.ee_axis_relational_zr_c3 as relational


_W173 = runpy.run_path(
    str(Path(__file__).with_name("test_w173_ee_axis_relational_zr_c3.py"))
)


def _slow_nominal_surface(
    environment: object,
    observation: object,
    references: np.ndarray,
    opening: np.ndarray,
    powers: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    tables, legal = relational._anchor(environment, observation)
    refs, power, opening_values, identity = relational._validate_context_inputs(
        tables,
        legal,
        references,
        powers,
        opening,
    )
    norads = identity[:, :, 0]
    cells = identity[:, :, 1]
    centres, colours, positions = relational._grid_data(
        environment, observation, norads, cells
    )
    users_ecef = relational._user_positions(environment, len(tables))
    theta, slant, elevation = relational._candidate_geometry(
        environment,
        observation,
        norads,
        cells,
        centres,
        positions,
        users_ecef,
    )
    signal = relational._nominal_signal_surface(
        theta=theta,
        slant=slant,
        elevation=elevation,
        required_power=power,
        legal=legal,
    )
    ref_branch = relational._branch_actions(refs)
    ref_served = relational._branch_served(ref_branch, opening_values, legal)
    ref_rates, _ = relational._nominal_rates(
        environment=environment,
        actions=ref_branch,
        served=ref_served,
        required_power=power,
        signal_surface=signal,
        norads=norads,
        cells=cells,
        legal=legal,
        colours=colours,
        centres=centres,
        positions=positions,
        users_ecef=users_ecef,
    )
    users = len(tables)
    candidate_rates = np.zeros((users, NUM_ACTIONS, users), dtype=np.float64)
    for uid in range(users):
        for action_raw in np.flatnonzero(legal[uid]).tolist():
            action = int(action_raw)
            branch = relational._branch_actions(
                refs, focal_user=uid, focal_action=action
            )
            served = relational._branch_served(branch, opening_values, legal)
            rates, _ = relational._nominal_rates(
                environment=environment,
                actions=branch,
                served=served,
                required_power=power,
                signal_surface=signal,
                norads=norads,
                cells=cells,
                legal=legal,
                colours=colours,
                centres=centres,
                positions=positions,
                users_ecef=users_ecef,
            )
            candidate_rates[uid, action] = rates
            candidate_rates[uid, action, uid] = 0.0
    delta = candidate_rates - ref_rates[None, None, :]
    delta = np.where(legal[:, :, None], delta, 0.0)
    delta[np.arange(users), :, np.arange(users)] = 0.0
    victim_mask = relational.compute_victim_mask(
        reference_actions=refs,
        action_mask=legal,
        opening_feasibility_surface=opening_values,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
        cell_colors=colours,
    )
    compatible = relational.compute_positive_credit_compatible(
        reference_actions=refs,
        action_mask=legal,
        opening_feasibility_surface=opening_values,
        required_power_surface=power,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
    )
    aggregated = np.sum(
        victim_mask
        * (
            np.minimum(delta, 0.0)
            + compatible[:, :, None] * np.maximum(delta, 0.0)
        ),
        axis=2,
    )
    reference_aggregate = aggregated[np.arange(users), np.maximum(refs, 0)]
    q3 = aggregated - reference_aggregate[:, None]
    q3 = np.where(legal, q3, 0.0)
    q3[refs == -1] = 0.0
    return delta, q3


def test_nominal_surface_matches_branch_by_branch_reference() -> None:
    environment, observation, references, opening, powers = _W173["_base_fixture"]()
    expected_delta, expected_q3 = _slow_nominal_surface(
        environment, observation, references, opening, powers
    )
    actual_delta, actual_q3 = relational.nominal_relational_zr_surface(
        environment,
        observation,
        reference_actions=references,
        required_power_surface=powers,
        opening_feasibility_surface=opening,
        interval_s=1.0,
        kappa_bits=1.0,
    )
    np.testing.assert_allclose(actual_delta, expected_delta, rtol=1e-12, atol=1e-9)
    np.testing.assert_allclose(actual_q3, expected_q3, rtol=1e-12, atol=1e-9)


def test_nominal_surface_builds_full_network_interference_once() -> None:
    environment, observation, references, opening, powers = _W173["_base_fixture"]()
    calls = 0
    original = relational._nominal_interference

    def counted(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    with patch.object(relational, "_nominal_interference", counted):
        relational.nominal_relational_zr_surface(
            environment,
            observation,
            reference_actions=references,
            required_power_surface=powers,
            opening_feasibility_surface=opening,
            interval_s=1.0,
            kappa_bits=1.0,
        )
    assert calls <= 1


def _slow_interference_shift_tokens(
    environment: object,
    observation: object,
    references: np.ndarray,
    opening: np.ndarray,
    powers: np.ndarray,
) -> np.ndarray:
    tables, legal = relational._anchor(environment, observation)
    refs, power, opening_values, identity = relational._validate_context_inputs(
        tables,
        legal,
        references,
        powers,
        opening,
    )
    norads = identity[:, :, 0]
    cells = identity[:, :, 1]
    centres, colours, positions = relational._grid_data(
        environment, observation, norads, cells
    )
    users_ecef = relational._user_positions(environment, len(tables))
    victims = relational.compute_victim_mask(
        reference_actions=refs,
        action_mask=legal,
        opening_feasibility_surface=opening_values,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
        cell_colors=colours,
    )
    reference_branch = relational._branch_actions(refs)
    reference_served = relational._branch_served(
        reference_branch, opening_values, legal
    )
    reference_interference = relational._nominal_interference(
        actions=reference_branch,
        served=reference_served,
        required_power=power,
        norads=norads,
        cells=cells,
        legal=legal,
        colours=colours,
        centres=centres,
        positions=positions,
        users_ecef=users_ecef,
    )
    noise = relational._noise_from(environment)
    expected = np.zeros((len(tables), NUM_ACTIONS, len(tables)), dtype=np.float64)
    for uid in range(len(tables)):
        for action_raw in np.flatnonzero(legal[uid]).tolist():
            action = int(action_raw)
            branch = relational._branch_actions(
                refs, focal_user=uid, focal_action=action
            )
            served = relational._branch_served(branch, opening_values, legal)
            candidate_interference = relational._nominal_interference(
                actions=branch,
                served=served,
                required_power=power,
                norads=norads,
                cells=cells,
                legal=legal,
                colours=colours,
                centres=centres,
                positions=positions,
                users_ecef=users_ecef,
            )
            for victim in np.flatnonzero(victims[uid, action]).tolist():
                expected[uid, action, victim] = math.asinh(
                    (float(candidate_interference[victim])
                     - float(reference_interference[victim]))
                    / noise
                )
    return expected


def test_state_encoder_interference_tokens_match_branch_reference() -> None:
    environment, observation, references, opening, powers = _W173["_base_fixture"]()
    expected = _slow_interference_shift_tokens(
        environment, observation, references, opening, powers
    )
    encoded = relational.encode_relational_zr_c3_state(
        environment,
        observation,
        reference_actions=references,
        required_power_surface=powers,
        opening_feasibility_surface=opening,
    )
    np.testing.assert_allclose(
        encoded.victim_tokens[..., 5], expected, rtol=1e-12, atol=1e-12
    )


def test_state_encoder_builds_full_network_interference_once() -> None:
    environment, observation, references, opening, powers = _W173["_base_fixture"]()
    calls = 0
    original = relational._nominal_interference

    def counted(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    with patch.object(relational, "_nominal_interference", counted):
        relational.encode_relational_zr_c3_state(
            environment,
            observation,
            reference_actions=references,
            required_power_surface=powers,
            opening_feasibility_surface=opening,
        )
    assert calls <= 1


@pytest.mark.parametrize("seed", range(8))
def test_cached_nominal_matches_reference_across_branch_contexts(seed: int) -> None:
    environment, observation, _references, _opening, _powers = _W173["_base_fixture"]()
    rng = np.random.default_rng(seed)
    legal = np.asarray(observation.masks, dtype=np.bool_)
    opening = legal & (rng.random(legal.shape) >= 0.25)
    powers = np.where(legal, rng.uniform(0.05, 1.5, size=legal.shape), 0.0)
    references = np.asarray(
        [rng.choice(np.flatnonzero(row)) for row in legal], dtype=np.int64
    )

    expected_delta, expected_q3 = _slow_nominal_surface(
        environment, observation, references, opening, powers
    )
    actual_delta, actual_q3 = relational.nominal_relational_zr_surface(
        environment,
        observation,
        reference_actions=references,
        required_power_surface=powers,
        opening_feasibility_surface=opening,
        interval_s=1.0,
        kappa_bits=1.0,
    )
    np.testing.assert_allclose(actual_delta, expected_delta, rtol=1e-12, atol=1e-9)
    np.testing.assert_allclose(actual_q3, expected_q3, rtol=1e-12, atol=1e-9)

    expected_tokens = _slow_interference_shift_tokens(
        environment, observation, references, opening, powers
    )
    encoded = relational.encode_relational_zr_c3_state(
        environment,
        observation,
        reference_actions=references,
        required_power_surface=powers,
        opening_feasibility_surface=opening,
    )
    np.testing.assert_allclose(
        encoded.victim_tokens[..., 5], expected_tokens, rtol=1e-12, atol=1e-12
    )


def test_nominal_cache_is_anchor_local_and_has_no_cross_call_state() -> None:
    environment, observation, references, opening, powers = _W173["_base_fixture"]()
    first_delta, first_q3 = relational.nominal_relational_zr_surface(
        environment,
        observation,
        reference_actions=references,
        required_power_surface=powers,
        opening_feasibility_surface=opening,
        interval_s=1.0,
        kappa_bits=1.0,
    )
    first_state = relational.encode_relational_zr_c3_state(
        environment,
        observation,
        reference_actions=references,
        required_power_surface=powers,
        opening_feasibility_surface=opening,
    )

    alternate_references = np.roll(references, 1)
    alternate_opening = np.array(opening, copy=True)
    alternate_opening[:, 0] = False
    relational.nominal_relational_zr_surface(
        environment,
        observation,
        reference_actions=alternate_references,
        required_power_surface=powers * 0.75,
        opening_feasibility_surface=alternate_opening,
        interval_s=1.0,
        kappa_bits=1.0,
    )
    relational.encode_relational_zr_c3_state(
        environment,
        observation,
        reference_actions=alternate_references,
        required_power_surface=powers * 0.75,
        opening_feasibility_surface=alternate_opening,
    )

    repeated_delta, repeated_q3 = relational.nominal_relational_zr_surface(
        environment,
        observation,
        reference_actions=references,
        required_power_surface=powers,
        opening_feasibility_surface=opening,
        interval_s=1.0,
        kappa_bits=1.0,
    )
    repeated_state = relational.encode_relational_zr_c3_state(
        environment,
        observation,
        reference_actions=references,
        required_power_surface=powers,
        opening_feasibility_surface=opening,
    )
    np.testing.assert_array_equal(repeated_delta, first_delta)
    np.testing.assert_array_equal(repeated_q3, first_q3)
    np.testing.assert_array_equal(
        repeated_state.action_context, first_state.action_context
    )
    np.testing.assert_array_equal(
        repeated_state.victim_tokens, first_state.victim_tokens
    )
    assert repeated_state.content_digest == first_state.content_digest
