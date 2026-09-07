"""W-46 — deterministic pre-decision C3 source selection."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import Association, NUM_ACTIONS, SlotTable
from mcrl.env.antenna import transmit_gain_linear
from mcrl.env.interference import RadiatingBeams
from mcrl.env.step import Segment, StepEnvironment, StepObservation
from mcrl.runtime.ee_axis_source_selectors import (
    C3_INFORMED_SOURCE_RULE,
    C3_NEUTRAL_SOURCE_RULE,
    C3SelectorContractError,
    C3UnilateralOpportunity,
    sample_c3_neutral_source,
    select_c3_source,
)
from mcrl.runtime.ee_axis_state import EE_AXIS_BASE_STATE_DIM
from mcrl.runtime.ee_axis_state import encode_ee_axis_state


def _table(keys: dict[int, tuple[int, int]]) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    for action, (norad, cell) in keys.items():
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norads, cells, mask)


def _fixture() -> tuple[StepEnvironment, StepObservation]:
    tables = (
        _table({0: (101, 1), 1: (202, 2), 2: (303, 3)}),
        _table({0: (101, 1), 1: (404, 4)}),
    )
    candidates = SimpleNamespace(slot_tables=tables)
    masks = np.stack([table.mask for table in tables])
    observation = StepObservation(
        step_index=2,
        candidates=candidates,
        user_states=(object(), object()),
        state_matrix=np.zeros((2, EE_AXIS_BASE_STATE_DIM), dtype=np.float32),
        masks=masks,
        candidate_sinr=np.zeros((2, NUM_ACTIONS), dtype=np.float64),
    )
    environment = object.__new__(StepEnvironment)
    environment.num_users = 2
    environment._candidates = candidates
    environment._previous_association = [
        Association(norad_id=101, cell_id=1),
        Association(norad_id=101, cell_id=1),
    ]
    start_gain = float(transmit_gain_linear(np.asarray([0.0]))[0])
    environment._segments = [
        Segment(101, 1, start_gain, age_steps=2),
        Segment(101, 1, start_gain, age_steps=2),
    ]
    environment._previous_link_power_w = np.array([1.1, 0.55], dtype=np.float64)
    environment._previous_radiating = RadiatingBeams(
        norad_ids=np.array([101, 202], dtype=np.int64),
        cell_ids=np.array([1, 2], dtype=np.int64),
        satellite_ecef_km=np.zeros((2, 3), dtype=np.float64),
        cell_centre_ecef_km=np.zeros((2, 3), dtype=np.float64),
        colors=np.array([0, 1], dtype=np.int64),
        power_w=np.array([1.1, 0.55], dtype=np.float64),
    )
    environment.physics = SimpleNamespace(beam_power_max_w=2.2)
    environment.driver = SimpleNamespace(config=SimpleNamespace(steps_per_episode=10))
    return environment, observation


def _reference(observation: StepObservation) -> np.ndarray:
    # The first legal action is the frozen Main action for this fixture.
    return np.array([0, 0], dtype=np.int64)


def test_informed_selector_uses_lagged_context_and_enumerates_all_actions() -> None:
    environment, observation = _fixture()
    reference = _reference(observation)
    before = tuple(environment._previous_association)

    plan = select_c3_source(
        environment,
        observation,
        anchor_sha256="a" * 64,
        reference_actions=reference,
        max_focal_users=1,
    )

    assert plan is not None
    plan.verify()
    assert plan.route == "C3"
    assert plan.source_rule == C3_INFORMED_SOURCE_RULE
    # Both users have multiple physical identities; user 0 wins the stable
    # user-id tie break because its lagged score is equal to user 1's score.
    assert plan.eligible_focal_users == (0, 1)
    assert plan.selected_focal_users == (0,)
    assert [(row.focal_user, row.candidate_action) for row in plan.opportunities] == [
        (0, 1),
        (0, 2),
    ]
    assert [row.candidate_physical_key for row in plan.opportunities] == [
        (202, 2),
        (303, 3),
    ]
    # The signal is explicitly taken from committed lagged features rather
    # than any outcome/target.
    first = plan.opportunities[0]
    assert first.lagged_eligible_load == 0.0
    assert first.previous_beam_active is True
    assert first.previous_satellite_active is True
    assert first.previous_max_required_link_power == pytest.approx(0.25)
    assert first.competitive_score == pytest.approx(2.25)
    assert tuple(environment._previous_association) == before


def test_selector_is_deterministic_and_never_calls_physics() -> None:
    environment, observation = _fixture()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("C3 source selection must be pre-outcome")

    environment.evaluate_actions = fail_if_called
    first = select_c3_source(
        environment,
        observation,
        anchor_sha256="b" * 64,
        reference_actions=_reference(observation),
    )
    second = select_c3_source(
        environment,
        observation,
        anchor_sha256="b" * 64,
        reference_actions=_reference(observation),
    )
    assert first is not None and second is not None
    assert [
        (row.focal_user, row.candidate_action, row.competitive_score)
        for row in first.opportunities
    ] == [
        (row.focal_user, row.candidate_action, row.competitive_score)
        for row in second.opportunities
    ]
    assert [row.candidate_actions.tolist() for row in first.opportunities] == [
        row.candidate_actions.tolist() for row in second.opportunities
    ]


def test_selector_counts_physical_identities_and_rejects_no_signal() -> None:
    environment, observation = _fixture()
    # All previous state is idle, so there is no lagged competitive anchor.
    environment._previous_association = [None, None]
    environment._segments = [None, None]
    environment._previous_link_power_w = np.zeros(2, dtype=np.float64)
    environment._previous_radiating = RadiatingBeams(
        norad_ids=np.array([], dtype=np.int64),
        cell_ids=np.array([], dtype=np.int64),
        satellite_ecef_km=np.empty((0, 3), dtype=np.float64),
        cell_centre_ecef_km=np.empty((0, 3), dtype=np.float64),
        colors=np.array([], dtype=np.int64),
        power_w=np.array([], dtype=np.float64),
    )
    assert (
        select_c3_source(
            environment,
            observation,
            anchor_sha256="c" * 64,
            reference_actions=_reference(observation),
        )
        is None
    )


def test_neutral_source_is_equal_budget_uniform_and_separate_route() -> None:
    environment, observation = _fixture()
    informed = select_c3_source(
        environment,
        observation,
        anchor_sha256="d" * 64,
        reference_actions=_reference(observation),
        max_focal_users=1,
    )
    assert informed is not None
    neutral_a = sample_c3_neutral_source(
        informed, rng=np.random.default_rng(20260831)
    )
    neutral_b = sample_c3_neutral_source(
        informed, rng=np.random.default_rng(20260831)
    )
    assert neutral_a.source_rule == C3_NEUTRAL_SOURCE_RULE
    assert neutral_a.budget == informed.budget == 2
    assert neutral_a.state_schema == informed.state_schema
    assert [
        (row.focal_user, row.candidate_action) for row in neutral_a.opportunities
    ] == [
        (row.focal_user, row.candidate_action) for row in neutral_b.opportunities
    ]
    assert all(
        row.source_rule == C3_NEUTRAL_SOURCE_RULE
        for row in neutral_a.opportunities
    )
    assert not {"zeta", "reward", "rate", "power"}.intersection(
        C3UnilateralOpportunity.__dataclass_fields__
    )


def test_selector_rejects_invalid_anchor_or_threshold() -> None:
    environment, observation = _fixture()
    with pytest.raises(C3SelectorContractError, match="anchor_sha256"):
        select_c3_source(
            environment,
            observation,
            anchor_sha256="not-a-digest",
            reference_actions=_reference(observation),
        )
    with pytest.raises(C3SelectorContractError, match="min_competitive_score"):
        select_c3_source(
            environment,
            observation,
            anchor_sha256="e" * 64,
            reference_actions=_reference(observation),
            min_competitive_score=4.0,
        )


def test_selector_rejects_a_stale_but_internally_valid_state() -> None:
    environment, observation = _fixture()
    stale = encode_ee_axis_state(environment, observation)
    environment._previous_link_power_w = np.array([0.8, 0.55], dtype=np.float64)
    with pytest.raises(C3SelectorContractError, match="current sealed"):
        select_c3_source(
            environment,
            observation,
            anchor_sha256="f" * 64,
            reference_actions=_reference(observation),
            state=stale,
        )
