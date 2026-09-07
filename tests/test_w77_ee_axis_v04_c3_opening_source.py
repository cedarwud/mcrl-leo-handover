"""V0.4 C3 matched opening-comparison producer seam."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import Association, NUM_ACTIONS, SlotTable
from mcrl.env.interference import empty_radiating_beams
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.step import ActionEvaluation, StepEnvironment, StepObservation
from mcrl.runtime.ee_axis_state import encode_ee_axis_state
from mcrl.runtime.ee_axis_v04_c3_opening_source import (
    V04C3OpeningProvenance,
    V04C3OpeningSourceContractError,
    produce_v04_c3_opening_comparison,
)
from mcrl.runtime.ee_axis_v04_c3_selector import C3_V04_INFORMED_SOURCE_RULE
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


def _fixture() -> tuple[StepEnvironment, StepObservation, KeyedFadingField]:
    tables = (
        _table({0: (101, 1), 1: (202, 2)}),
        _table({0: (101, 1), 1: (303, 3)}),
        _table({0: (101, 2), 1: (404, 4)}),
    )
    masks = np.stack([table.mask for table in tables])
    candidates = SimpleNamespace(slot_tables=tables, masks=masks)
    observation = StepObservation(
        step_index=0,
        candidates=candidates,
        user_states=(object(), object(), object()),
        state_matrix=np.zeros((3, 112), dtype=np.float32),
        masks=masks,
        candidate_sinr=np.zeros((3, NUM_ACTIONS), dtype=np.float64),
    )
    field = KeyedFadingField.from_components("w77-test", 1, 3)
    environment = object.__new__(StepEnvironment)
    environment.num_users = 3
    environment._candidates = candidates
    environment._previous_association = [None, None, None]
    environment._previous_served_rate_bps = np.zeros(3, dtype=np.float64)
    environment._previous_link_power_w = np.zeros(3, dtype=np.float64)
    environment._previous_demand = {}
    environment._previous_radiating = empty_radiating_beams()
    environment._segments = [None, None, None]
    environment._step_index = 0
    environment._fading_field = field
    environment.physics = SimpleNamespace(
        beam_power_max_w=2.2,
        fading_enabled=True,
    )
    environment.driver = SimpleNamespace(
        grid=SimpleNamespace(),
        step_index=0,
        config=SimpleNamespace(steps_per_episode=10),
    )
    return environment, observation, field


def _provenance(field: KeyedFadingField) -> V04C3OpeningProvenance:
    return V04C3OpeningProvenance(
        source_policy_version=1,
        anchor_sha256="a" * 64,
        source_manifest_sha256="b" * 64,
        checkpoint_sha256="c" * 64,
        common_random_field_sha256=field.root_digest,
        c3_source_rule=C3_V04_INFORMED_SOURCE_RULE,
    )


def _evaluation(actions: np.ndarray) -> ActionEvaluation:
    if int(actions[0]) == 0:
        rates = np.asarray([100.0, 200.0, 300.0], dtype=np.float64)
        power = 10.0
    else:
        rates = np.asarray([110.0, 180.0, 330.0], dtype=np.float64)
        power = 12.0
    return ActionEvaluation(
        rewards=(),
        resolution=SimpleNamespace(),
        energy=SimpleNamespace(),
        interference=SimpleNamespace(),
        radiating=empty_radiating_beams(),
        link_power_w=np.zeros(3, dtype=np.float64),
        link_sinr=np.zeros(3, dtype=np.float64),
        link_rate_bps=rates,
        handovers=(),
        system_power_w=power,
        fixed_power_w=0.0,
    )


def _actions() -> tuple[np.ndarray, np.ndarray]:
    return (
        np.asarray([0, 0, 0], dtype=np.int64),
        np.asarray([1, 0, 0], dtype=np.int64),
    )


def _produce(environment, observation, field, state, monkeypatch):
    reference, candidate = _actions()
    calls = []

    def fake_evaluate(self, actions, rng):
        calls.append(np.array(actions, copy=True))
        return _evaluation(actions)

    monkeypatch.setattr(StepEnvironment, "evaluate_actions", fake_evaluate)
    result = produce_v04_c3_opening_comparison(
        environment,
        observation=observation,
        state_observation=state,
        reference_actions=reference,
        candidate_actions=candidate,
        focal_user=0,
        common_random_field=field,
        provenance=_provenance(field),
        rng=np.random.default_rng(77),
        lambda_bits_per_j=10.0,
        interval_s=2.0,
        kappa_bits=100.0,
    )
    assert [row.tolist() for row in calls] == [reference.tolist(), candidate.tolist()]
    return result


def test_v04_state_is_used_and_v03_state_is_rejected(monkeypatch):
    environment, observation, field = _fixture()
    state = encode_ee_axis_v04_c3_state(
        environment,
        observation,
        interval_s=2.0,
        kappa_bits=100.0,
    )
    result = _produce(environment, observation, field, state, monkeypatch)

    assert result.state_schema == state.schema
    assert result.state_schema_sha256 == state.schema_sha256
    assert result.state_observation_sha256 == state.state_sha256
    assert np.array_equal(result.pair.state, state.state_matrix[0])
    assert result.pair.source_route == "C3"
    assert result.reference_physical_key == (101, 1)
    assert result.candidate_physical_key == (202, 2)

    with pytest.raises(V04C3OpeningSourceContractError, match="V04C3StateObservation"):
        _produce(
            environment,
            observation,
            field,
            encode_ee_axis_state(environment, observation),
            monkeypatch,
        )


def test_c3_target_is_exact_nonfocal_delta_rate_sum(monkeypatch):
    environment, observation, field = _fixture()
    state = encode_ee_axis_v04_c3_state(
        environment,
        observation,
        interval_s=2.0,
        kappa_bits=100.0,
    )
    result = _produce(environment, observation, field, state, monkeypatch)

    # Non-focal delta = (180 + 330) - (200 + 300) = 10 bit/s; Δt=2 s.
    assert result.pair.zeta3_nonfocal_externality_bits == pytest.approx(20.0)
    assert result.pair.route_target_surplus_bits == pytest.approx(20.0)
    assert result.verify() == result.comparison_sha256


def test_c3_target_verification_subtracts_matched_users_before_summing(
    monkeypatch,
):
    """Large common rates must not erase a small unilateral externality."""

    environment, observation, field = _fixture()
    state = encode_ee_axis_v04_c3_state(
        environment,
        observation,
        interval_s=2.0,
        kappa_bits=100.0,
    )
    reference, candidate = _actions()

    def high_common_rate_evaluate(self, actions, rng):
        del self, rng
        if int(actions[0]) == 0:
            rates = np.asarray([100.0, 1.0e12, 1.0e12], dtype=np.float64)
        else:
            rates = np.asarray(
                [110.0, 1.0e12 + 0.1, 1.0e12 - 0.05],
                dtype=np.float64,
            )
        return ActionEvaluation(
            rewards=(),
            resolution=SimpleNamespace(),
            energy=SimpleNamespace(),
            interference=SimpleNamespace(),
            radiating=empty_radiating_beams(),
            link_power_w=np.zeros(3, dtype=np.float64),
            link_sinr=np.zeros(3, dtype=np.float64),
            link_rate_bps=rates,
            handovers=(),
            system_power_w=10.0,
            fixed_power_w=0.0,
        )

    monkeypatch.setattr(
        StepEnvironment, "evaluate_actions", high_common_rate_evaluate
    )
    result = produce_v04_c3_opening_comparison(
        environment,
        observation=observation,
        state_observation=state,
        reference_actions=reference,
        candidate_actions=candidate,
        focal_user=0,
        common_random_field=field,
        provenance=_provenance(field),
        rng=np.random.default_rng(7701),
        lambda_bits_per_j=10.0,
        interval_s=2.0,
        kappa_bits=100.0,
    )

    expected = 2.0 * float(
        (1.0e12 + 0.1 - 1.0e12) + (1.0e12 - 0.05 - 1.0e12)
    )
    assert result.pair.zeta3_nonfocal_externality_bits == expected
    assert result.verify() == result.comparison_sha256


def test_evaluate_only_path_does_not_commit_previous_state_or_burden(monkeypatch):
    environment, observation, field = _fixture()
    state = encode_ee_axis_v04_c3_state(
        environment,
        observation,
        interval_s=2.0,
        kappa_bits=100.0,
    )
    before_rates = environment._previous_served_rate_bps.copy()
    before_digest = state.state_sha256
    _produce(environment, observation, field, state, monkeypatch)
    after = encode_ee_axis_v04_c3_state(
        environment,
        observation,
        interval_s=2.0,
        kappa_bits=100.0,
    )

    assert np.array_equal(environment._previous_served_rate_bps, before_rates)
    assert after.state_sha256 == before_digest
    assert environment._step_index == 0
    assert environment.driver.step_index == 0


def test_source_fails_closed_on_stale_anchor_nonunilateral_actions_and_unbound_field(
    monkeypatch,
):
    environment, observation, field = _fixture()
    state = encode_ee_axis_v04_c3_state(
        environment,
        observation,
        interval_s=2.0,
        kappa_bits=100.0,
    )

    environment._candidates = object()
    with pytest.raises(V04C3OpeningSourceContractError, match="current.*anchor"):
        _produce(environment, observation, field, state, monkeypatch)

    environment, observation, field = _fixture()
    state = encode_ee_axis_v04_c3_state(
        environment,
        observation,
        interval_s=2.0,
        kappa_bits=100.0,
    )
    reference, candidate = _actions()
    candidate[1] = 1

    def fake_evaluate(self, actions, rng):
        return _evaluation(actions)

    monkeypatch.setattr(StepEnvironment, "evaluate_actions", fake_evaluate)
    with pytest.raises(V04C3OpeningSourceContractError, match="exactly the focal"):
        produce_v04_c3_opening_comparison(
            environment,
            observation=observation,
            state_observation=state,
            reference_actions=reference,
            candidate_actions=candidate,
            focal_user=0,
            common_random_field=field,
            provenance=_provenance(field),
            rng=np.random.default_rng(77),
            lambda_bits_per_j=10.0,
            interval_s=2.0,
            kappa_bits=100.0,
        )

    environment, observation, field = _fixture()
    state = encode_ee_axis_v04_c3_state(
        environment,
        observation,
        interval_s=2.0,
        kappa_bits=100.0,
    )
    environment._fading_field = None
    with pytest.raises(V04C3OpeningSourceContractError, match="keyed fading"):
        _produce(environment, observation, field, state, monkeypatch)


def test_source_rejects_stale_v04_schema(monkeypatch):
    environment, observation, field = _fixture()
    state = encode_ee_axis_v04_c3_state(
        environment,
        observation,
        interval_s=2.0,
        kappa_bits=100.0,
    )
    stale = replace(state, schema="multi-catfish-mcrl-v03-causal-state-v2")
    with pytest.raises(V04C3OpeningSourceContractError, match="V0.4 state observation"):
        _produce(environment, observation, field, stale, monkeypatch)


def test_provenance_rejects_a_v03_source_rule():
    _environment, _observation, field = _fixture()
    stale = replace(
        _provenance(field),
        c3_source_rule="c3-lagged-competitive-load-predecision-v1",
    )
    with pytest.raises(V04C3OpeningSourceContractError, match="V0.4 victim-burden"):
        stale.verify()
