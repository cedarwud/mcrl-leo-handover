"""V0.4 C3 victim-burden pre-outcome selector."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import Association, NUM_ACTIONS, SlotTable
from mcrl.env.interference import RadiatingBeams
from mcrl.env.step import Segment, StepEnvironment, StepObservation
from mcrl.runtime.ee_axis_state import EE_AXIS_BASE_STATE_DIM, encode_ee_axis_state
from mcrl.runtime import ee_axis_v04_c3_selector as selector_module
from mcrl.runtime.ee_axis_v04_c3_selector import (
    C3_V04_INFORMED_SOURCE_RULE,
    C3_V04_MAX_SIBLINGS_PER_CONTEXT,
    C3_V04_NEUTRAL_SOURCE_RULE,
    C3V04SelectorContractError,
    sample_v04_c3_neutral_source,
    select_v04_c3_source,
)
from mcrl.runtime.ee_axis_v04_c3_state import encode_ee_axis_v04_c3_state


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
        _table(
            {
                0: (101, 1),
                1: (202, 2),
                2: (303, 3),
                3: (101, 2),
                4: (404, 4),
                5: (505, 5),
            }
        ),
        _table({0: (101, 1), 1: (202, 2), 2: (303, 3)}),
        _table({0: (202, 2), 1: (101, 2), 2: (404, 4)}),
    )
    candidates = SimpleNamespace(slot_tables=tables)
    masks = np.stack([table.mask for table in tables])
    observation = StepObservation(
        step_index=2,
        candidates=candidates,
        user_states=(object(), object(), object()),
        state_matrix=np.zeros((3, EE_AXIS_BASE_STATE_DIM), dtype=np.float32),
        masks=masks,
        candidate_sinr=np.zeros((3, NUM_ACTIONS), dtype=np.float64),
    )
    environment = object.__new__(StepEnvironment)
    environment.num_users = 3
    environment._candidates = candidates
    environment._previous_association = [
        Association(101, 1),
        Association(101, 1),
        Association(202, 2),
    ]
    environment._previous_served_rate_bps = np.array(
        [100.0, 200.0, 300.0], dtype=np.float64
    )
    environment._segments = [
        Segment(association.norad_id, association.cell_id, 1.0, age_steps=2)
        for association in environment._previous_association
    ]
    environment._previous_link_power_w = np.array([0.4, 0.8, 1.2])
    environment._previous_radiating = RadiatingBeams(
        norad_ids=np.array([101, 202], dtype=np.int64),
        cell_ids=np.array([1, 2], dtype=np.int64),
        satellite_ecef_km=np.zeros((2, 3), dtype=np.float64),
        cell_centre_ecef_km=np.zeros((2, 3), dtype=np.float64),
        colors=np.array([0, 1], dtype=np.int64),
        power_w=np.array([0.8, 1.2], dtype=np.float64),
    )
    environment.physics = SimpleNamespace(beam_power_max_w=2.2)
    environment.driver = SimpleNamespace(config=SimpleNamespace(steps_per_episode=10))
    return environment, observation


def _select(environment: StepEnvironment, observation: StepObservation, **kwargs):
    return select_v04_c3_source(
        environment,
        observation,
        anchor_sha256="a" * 64,
        reference_actions=np.array([0, 0, 0], dtype=np.int64),
        interval_s=2.0,
        kappa_bits=100.0,
        **kwargs,
    )


def test_informed_selection_is_preoutcome_and_caps_each_context_at_four() -> None:
    environment, observation = _fixture()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("selector must not evaluate an outcome")

    environment.evaluate_actions = fail_if_called
    plan = _select(environment, observation, max_focal_users=1)

    assert plan is not None
    plan.verify()
    assert plan.source_rule == C3_V04_INFORMED_SOURCE_RULE
    assert plan.selected_focal_users == (0,)
    assert len(plan.opportunities) == C3_V04_MAX_SIBLINGS_PER_CONTEXT
    assert min(row.burden_delta for row in plan.opportunities) < 0.0
    assert max(row.burden_delta for row in plan.opportunities) > 0.0
    assert all(row.focal_user == 0 for row in plan.opportunities)
    assert "beam-primary" in plan.source_rule
    for row in plan.opportunities:
        assert row.burden_delta == pytest.approx(
            row.candidate_beam_burden - row.reference_beam_burden,
            abs=1e-12,
        )
        assert row.satellite_burden_delta == pytest.approx(
            row.candidate_satellite_burden
            - row.reference_satellite_burden,
            abs=1e-12,
        )


def test_episode_start_has_no_victim_pressure_and_is_not_admitted() -> None:
    environment, observation = _fixture()
    environment._previous_association = [None, None, None]
    environment._previous_served_rate_bps = np.zeros(3, dtype=np.float64)
    environment._segments = [None, None, None]
    environment._previous_link_power_w = np.zeros(3, dtype=np.float64)
    environment._previous_radiating = RadiatingBeams(
        norad_ids=np.empty(0, dtype=np.int64),
        cell_ids=np.empty(0, dtype=np.int64),
        satellite_ecef_km=np.empty((0, 3), dtype=np.float64),
        cell_centre_ecef_km=np.empty((0, 3), dtype=np.float64),
        colors=np.empty(0, dtype=np.int64),
        power_w=np.empty(0, dtype=np.float64),
    )

    assert _select(environment, observation) is None


def test_equal_budget_neutral_is_deterministic_and_respects_sibling_cap() -> None:
    environment, observation = _fixture()
    informed = _select(environment, observation)
    assert informed is not None

    first = sample_v04_c3_neutral_source(
        informed, rng=np.random.default_rng(20260901)
    )
    second = sample_v04_c3_neutral_source(
        informed, rng=np.random.default_rng(20260901)
    )

    assert first.source_rule == C3_V04_NEUTRAL_SOURCE_RULE
    assert first.budget == informed.budget
    assert [
        (row.focal_user, row.candidate_action) for row in first.opportunities
    ] == [
        (row.focal_user, row.candidate_action) for row in second.opportunities
    ]
    counts = {
        uid: sum(row.focal_user == uid for row in first.opportunities)
        for uid in first.selected_focal_users
    }
    assert max(counts.values()) <= C3_V04_MAX_SIBLINGS_PER_CONTEXT


def test_stale_v04_state_and_v03_state_are_both_rejected() -> None:
    environment, observation = _fixture()
    v04 = encode_ee_axis_v04_c3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    v03 = encode_ee_axis_state(environment, observation)
    environment._previous_served_rate_bps[1] = 250.0

    with pytest.raises(C3V04SelectorContractError, match="current sealed"):
        _select(environment, observation, state=v04)
    with pytest.raises(C3V04SelectorContractError, match="V0.4"):
        _select(environment, observation, state=v03)  # type: ignore[arg-type]


def test_selection_rejects_detached_or_formula_drifted_sibling() -> None:
    environment, observation = _fixture()
    plan = _select(environment, observation, max_focal_users=1)
    assert plan is not None
    original = plan.opportunities[0]
    detached = replace(original, burden_delta=original.burden_delta + 1.0)

    with pytest.raises(C3V04SelectorContractError, match="burden_delta"):
        detached.verify()
    with pytest.raises(C3V04SelectorContractError, match="outside universe"):
        replace(plan, opportunities=(replace(original), *plan.opportunities[1:])).verify()


def test_focal_user_rank_keeps_beam_pressure_ahead_of_satellite_contrast(
    monkeypatch,
) -> None:
    """A large satellite contrast cannot displace stronger beam pressure."""

    environment, observation = _fixture()
    beam = np.zeros((3, NUM_ACTIONS), dtype=np.float32)
    satellite = np.zeros((3, NUM_ACTIONS), dtype=np.float32)

    # Users 0 and 1 have the same maximum absolute beam contrast (10).
    # User 1 has the larger beam victim pressure (30 vs 20), while user 0
    # deliberately has a much larger satellite contrast.  The binding rank
    # therefore selects user 1.
    beam[0, 0] = 10.0
    beam[0, 1:6] = 20.0
    satellite[0, 1:6] = 100.0
    beam[1, 0] = 30.0
    beam[1, 1:3] = 20.0
    satellite[1, 1:3] = 1.0
    beam[2, :3] = 5.0

    monkeypatch.setattr(
        selector_module,
        "_burden_blocks",
        lambda _state: (beam, satellite),
    )
    plan = _select(environment, observation, max_focal_users=1)

    assert plan is not None
    assert plan.selected_focal_users == (1,)
