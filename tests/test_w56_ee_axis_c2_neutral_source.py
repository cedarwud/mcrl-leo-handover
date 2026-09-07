"""W-56 -- C2 equal-budget neutral pre-decision source selection."""

from __future__ import annotations

from dataclasses import fields
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.runtime.ee_axis_c2_neutral_source import (
    C2_HORIZON_STEPS,
    C2_NEUTRAL_SOURCE_RULE,
    C2_RELEASE_GRAMMAR,
    C2NeutralSourceContractError,
    C2PhysicalAlternative,
    C2PredecisionAnchor,
    C2PredecisionOpportunity,
    build_c2_predecision_universe,
    predecision_anchor_from_observation,
    prepare_selected_c2_candidate,
    sample_c2_neutral_source,
    select_c2_neutral_source,
)


def _anchor(
    digest: str,
    *,
    step: int,
    user: int,
    reference_action: int,
    alternatives: tuple[tuple[int, tuple[int, int]], ...],
) -> C2PredecisionAnchor:
    reference_key = (1000 + user, 0) if reference_action >= 0 else None
    return C2PredecisionAnchor(
        anchor_sha256=digest,
        step_index=step,
        focal_user=user,
        reference_action=reference_action,
        reference_physical_key=reference_key,
        legal_alternatives=tuple(
            C2PhysicalAlternative(action=action, physical_key=key)
            for action, key in alternatives
        ),
    )


def _universe() -> tuple[C2PredecisionOpportunity, ...]:
    anchors = (
        _anchor(
            "a" * 64,
            step=2,
            user=0,
            reference_action=0,
            alternatives=(
                (1, (2001, 1)),
                (2, (2002, 2)),
                (3, (2003, 3)),
            ),
        ),
        _anchor(
            "b" * 64,
            step=5,
            user=4,
            reference_action=4,
            alternatives=(
                (5, (3001, 1)),
                (6, (3002, 2)),
            ),
        ),
    )
    return build_c2_predecision_universe(anchors)


def _table(keys: dict[int, tuple[int, int]]) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    for action, (norad, cell) in keys.items():
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norads, cells, mask)


def test_universe_is_current_physical_table_only_and_excludes_reference() -> None:
    universe = _universe()
    assert len(universe) == 5
    assert all(row.reference_action != row.candidate_action for row in universe)
    assert [row.opportunity_key for row in universe] == sorted(
        row.opportunity_key for row in universe
    )
    assert all(row.horizon_steps == C2_HORIZON_STEPS for row in universe)
    assert all(row.release_grammar == C2_RELEASE_GRAMMAR for row in universe)

    fields_by_name = {field.name for field in fields(C2PredecisionOpportunity)}
    forbidden = {"target", "reward", "rate", "power", "outcome", "trace", "gate"}
    assert not forbidden.intersection(fields_by_name)


def test_neutral_sampling_is_deterministic_equal_budget_and_without_replacement() -> None:
    universe = _universe()
    first = sample_c2_neutral_source(
        tuple(reversed(universe)),
        informed_budget=3,
        rng=np.random.default_rng(20260831),
        random_seed=20260831,
    )
    second = sample_c2_neutral_source(
        universe,
        informed_budget=3,
        rng=np.random.default_rng(20260831),
        random_seed=20260831,
    )
    first.verify()
    assert first.source_rule == C2_NEUTRAL_SOURCE_RULE
    assert first.budget == first.informed_budget == 3
    assert first.selection_digest == second.selection_digest
    selected_keys = [row.opportunity_key for row in first.opportunities]
    assert len(selected_keys) == len(set(selected_keys))
    assert set(selected_keys).issubset({row.opportunity_key for row in universe})
    assert first.eligible_anchor_sha256s == ("a" * 64, "b" * 64)


def test_anchor_builder_reads_no_physics_or_postdecision_payload() -> None:
    tables = (_table({0: (1000, 0), 1: (2001, 1), 2: (2002, 2)}),)
    observation = SimpleNamespace(
        candidates=SimpleNamespace(slot_tables=tables),
        # Deliberately hostile fields: the selector must never read these.
        last_outcome=SimpleNamespace(
            target=property(lambda _: (_ for _ in ()).throw(AssertionError()))
        ),
        target=property(lambda _: (_ for _ in ()).throw(AssertionError())),
    )
    anchor = predecision_anchor_from_observation(
        anchor_sha256="c" * 64,
        step_index=3,
        focal_user=0,
        reference_action=0,
        observation=observation,
    )
    assert [row.action for row in anchor.legal_alternatives] == [1, 2]
    assert [row.physical_key for row in anchor.legal_alternatives] == [
        (2001, 1),
        (2002, 2),
    ]


def test_builder_drops_ambiguous_physical_aliases_before_prepare() -> None:
    tables = (_table({0: (1000, 0), 1: (2001, 1), 2: (2001, 1), 3: (2002, 2)}),)
    observation = SimpleNamespace(candidates=SimpleNamespace(slot_tables=tables))
    anchor = predecision_anchor_from_observation(
        anchor_sha256="d" * 64,
        step_index=3,
        focal_user=0,
        reference_action=0,
        observation=observation,
    )
    assert [row.physical_key for row in anchor.legal_alternatives] == [(2002, 2)]


def test_selected_opportunity_feeds_existing_prepare_one_candidate() -> None:
    opportunity = _universe()[1]
    events: list[tuple[str, object]] = []

    class Backend:
        anchor_sha256 = opportunity.anchor_sha256

        def prepare_one_candidate(self, *, focal_user: int, candidate_key, source_rule: str):
            events.append(("prepare", (focal_user, candidate_key, source_rule)))
            return SimpleNamespace(source_rule=source_rule)

    prepared = prepare_selected_c2_candidate(Backend(), opportunity)
    assert prepared.source_rule == C2_NEUTRAL_SOURCE_RULE
    assert events == [
        (
            "prepare",
            (
                opportunity.focal_user,
                opportunity.candidate_physical_key,
                C2_NEUTRAL_SOURCE_RULE,
            ),
        )
    ]


def test_invalid_empty_and_mismatched_cases_fail_closed() -> None:
    with pytest.raises(C2NeutralSourceContractError, match="empty"):
        select_c2_neutral_source(
            (), informed_budget=1, rng=np.random.default_rng(1)
        )
    with pytest.raises(C2NeutralSourceContractError, match="informed_budget"):
        sample_c2_neutral_source(
            _universe(), informed_budget=0, rng=np.random.default_rng(1)
        )
    with pytest.raises(C2NeutralSourceContractError, match="exceeds"):
        sample_c2_neutral_source(
            _universe(), informed_budget=6, rng=np.random.default_rng(1)
        )
    with pytest.raises(C2NeutralSourceContractError, match="numpy"):
        sample_c2_neutral_source(_universe(), informed_budget=1, rng=object())  # type: ignore[arg-type]
    with pytest.raises(C2NeutralSourceContractError, match="anchor"):
        prepare_selected_c2_candidate(
            SimpleNamespace(anchor_sha256="e" * 64), _universe()[0]
        )


def test_select_helper_preserves_fixed_horizon_and_release_grammar() -> None:
    selection = select_c2_neutral_source(
        (
            _anchor(
                "f" * 64,
                step=1,
                user=2,
                reference_action=2,
                alternatives=((3, (4001, 1)), (4, (4002, 2))),
            ),
        ),
        informed_budget=1,
        rng=np.random.default_rng(7),
    )
    assert selection.horizon_steps == C2_HORIZON_STEPS
    assert selection.release_grammar == C2_RELEASE_GRAMMAR
    assert selection.opportunities[0].source_rule == C2_NEUTRAL_SOURCE_RULE


def test_anchor_rejects_stale_horizon_or_release_grammar() -> None:
    base = _anchor(
        "1" * 64,
        step=1,
        user=0,
        reference_action=0,
        alternatives=((1, (4001, 1)),),
    )
    with pytest.raises(C2NeutralSourceContractError, match="horizon"):
        C2PredecisionAnchor(**{**base.__dict__, "horizon_steps": 3}).verify()
    with pytest.raises(C2NeutralSourceContractError, match="release"):
        C2PredecisionAnchor(**{**base.__dict__, "release_grammar": "fixed-hold"}).verify()
