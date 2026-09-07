"""W-47 — pre-decision C1 EXP/ACRM source selection."""

from __future__ import annotations

from dataclasses import fields

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.runtime.ee_axis_c1_selector import (
    C1_ACRM_PAIR_RULE,
    C1_CLUSTER_NEUTRAL_SOURCE_RULE,
    C1_INFORMED_SOURCE_RULE,
    C1_NEUTRAL_SOURCE_RULE,
    C1DullRolloutRecord,
    C1FrontierConfig,
    C1SelectorContractError,
    C1UnilateralOpportunity,
    _randomized_profile_anchor_matching,
    sample_c1_cluster_matched_neutral_source,
    sample_c1_neutral_source,
    select_c1_source,
)
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)


def _table(keys: dict[int, tuple[int, int]]) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    for action, (norad, cell) in keys.items():
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norads, cells, mask)


def _record(
    *,
    anchor: str,
    source_seed: int,
    step: int,
    frontier_score: float,
    user_scores: tuple[float, float],
    partition: str = "TRAIN",
) -> C1DullRolloutRecord:
    tables = (
        _table({0: (101, 1), 1: (202, 2), 2: (303, 3)}),
        # Action 2 aliases action 1 physically.  C1 must emit one physical
        # alternative, not duplicate a slot alias.
        _table({0: (101, 1), 1: (404, 4), 2: (404, 4), 3: (505, 5)}),
    )
    return C1DullRolloutRecord(
        record_id=f"dull-{source_seed}-{step}",
        anchor_sha256=anchor * 64 if len(anchor) == 1 else anchor,
        source_manifest_sha256="1" * 64,
        checkpoint_sha256="c" * 64,
        state_schema=EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
        source_seed=source_seed,
        step_index=step,
        partition=partition,
        rollout_kind="dull-rollout",
        policy_name="local-snr-greedy",
        frontier_score=frontier_score,
        user_frontier_scores=np.asarray(user_scores, dtype=np.float64),
        reference_actions=np.asarray([0, 0], dtype=np.int64),
        slot_tables=tables,
    )


def _records() -> tuple[C1DullRolloutRecord, ...]:
    return (
        _record(anchor="a", source_seed=30, step=2, frontier_score=3.0, user_scores=(3.0, 1.0)),
        _record(anchor="b", source_seed=10, step=1, frontier_score=1.0, user_scores=(3.0, 1.0)),
        _record(anchor="e", source_seed=20, step=0, frontier_score=2.0, user_scores=(1.0, 2.0)),
    )


def _heterogeneous_profile_records() -> tuple[C1DullRolloutRecord, ...]:
    one = _table({0: (101, 1), 1: (202, 2)})
    two = _table({0: (101, 1), 1: (202, 2), 2: (303, 3)})
    rows = (
        ("a", 1, 1.0, (one, two)),
        ("b", 2, 2.0, (two, one)),
        ("c", 3, 3.0, (one, two)),
        ("d", 4, 4.0, (two, one)),
    )
    return tuple(
        C1DullRolloutRecord(
            record_id=f"heterogeneous-{seed}",
            anchor_sha256=anchor * 64,
            source_manifest_sha256="1" * 64,
            checkpoint_sha256="c" * 64,
            state_schema=EE_AXIS_STATE_SCHEMA,
            state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
            source_seed=seed,
            step_index=0,
            partition="TRAIN",
            rollout_kind="dull-rollout",
            policy_name="local-snr-greedy",
            frontier_score=score,
            user_frontier_scores=np.asarray([1.0, 2.0], dtype=np.float64),
            reference_actions=np.asarray([0, 0], dtype=np.int64),
            slot_tables=tables,
        )
        for anchor, seed, score, tables in rows
    )


def test_informed_c1_selects_lower_frontier_and_enumerates_physical_alternatives() -> None:
    plan = select_c1_source(
        _records(),
        config=C1FrontierConfig(
            lower_anchor_fraction=0.5,
            lower_user_fraction=0.5,
        ),
    )

    assert plan is not None
    plan.verify()
    assert plan.source_rule == C1_INFORMED_SOURCE_RULE
    assert plan.acrm_pair_rule == C1_ACRM_PAIR_RULE
    # Scores 1 and 2 are the deterministic lower anchor stratum.
    assert plan.selected_anchor_sha256s == ("b" * 64, "e" * 64)
    # One lower-frontier user per selected anchor, two physical alternatives
    # for each selected user.  The alias (404,4) appears once.
    assert plan.budget == 4
    assert set(plan.selected_focal_users) == {
        ("b" * 64, 1),
        ("e" * 64, 0),
    }
    assert [(row.anchor_sha256, row.focal_user, row.candidate_physical_key) for row in plan.opportunities] == [
        ("b" * 64, 1, (404, 4)),
        ("b" * 64, 1, (505, 5)),
        ("e" * 64, 0, (202, 2)),
        ("e" * 64, 0, (303, 3)),
    ]
    for row in plan.opportunities:
        assert row.reference_physical_key == (101, 1)
        assert row.reference_actions[row.focal_user] == 0
        assert row.candidate_actions[row.focal_user] == row.candidate_action
        assert np.array_equal(
            np.delete(row.reference_actions, row.focal_user),
            np.delete(row.candidate_actions, row.focal_user),
        )
        assert not row.reference_actions.flags.writeable
        assert not row.candidate_actions.flags.writeable
        assert not row.action_mask.flags.writeable


def test_selection_is_deterministic_and_does_not_run_or_accept_outcomes() -> None:
    first = select_c1_source(_records())
    second = select_c1_source(tuple(reversed(_records())))
    assert first is not None and second is not None
    assert [row.opportunity_key for row in first.opportunities] == [
        row.opportunity_key for row in second.opportunities
    ]
    assert [row.candidate_actions.tolist() for row in first.opportunities] == [
        row.candidate_actions.tolist() for row in second.opportunities
    ]
    # Source records and opportunities contain no candidate outcome surface.
    forbidden = {"zeta", "reward", "rate", "power", "target"}
    assert not forbidden.intersection(field.name for field in fields(C1DullRolloutRecord))
    assert not forbidden.intersection(field.name for field in fields(C1UnilateralOpportunity))
    with pytest.raises(C1SelectorContractError, match="C1DullRolloutRecord"):
        select_c1_source([object()])  # type: ignore[list-item]


def test_neutral_is_equal_budget_uniform_and_keeps_acrm_lineage() -> None:
    informed = select_c1_source(_records())
    assert informed is not None
    neutral_a = sample_c1_neutral_source(
        informed,
        rng=np.random.default_rng(20260831),
    )
    neutral_b = sample_c1_neutral_source(
        informed,
        rng=np.random.default_rng(20260831),
    )
    assert neutral_a.source_rule == C1_NEUTRAL_SOURCE_RULE
    assert neutral_a.acrm_pair_rule == C1_ACRM_PAIR_RULE
    assert neutral_a.budget == informed.budget
    assert neutral_a.budget == 4
    assert [row.opportunity_key for row in neutral_a.opportunities] == [
        row.opportunity_key for row in neutral_b.opportunities
    ]
    assert all(
        row.source_rule == C1_NEUTRAL_SOURCE_RULE
        for row in neutral_a.all_opportunities + neutral_a.opportunities
    )
    assert set(row.opportunity_key for row in neutral_a.opportunities).issubset(
        {row.opportunity_key for row in informed.all_opportunities}
    )


def test_cluster_neutral_matches_anchor_user_and_alternative_budgets() -> None:
    informed = select_c1_source(_records())
    assert informed is not None

    neutral_a = sample_c1_cluster_matched_neutral_source(
        informed,
        rng=np.random.default_rng(20260831),
    )
    neutral_b = sample_c1_cluster_matched_neutral_source(
        informed,
        rng=np.random.default_rng(20260831),
    )

    assert neutral_a.source_rule == C1_CLUSTER_NEUTRAL_SOURCE_RULE
    assert neutral_a.budget == informed.budget
    assert len(neutral_a.selected_anchor_sha256s) == len(
        informed.selected_anchor_sha256s
    )
    assert len(neutral_a.selected_focal_users) == len(informed.selected_focal_users)
    assert [row.opportunity_key for row in neutral_a.opportunities] == [
        row.opportunity_key for row in neutral_b.opportunities
    ]
    for key in neutral_a.selected_focal_users:
        all_keys = {
            row.opportunity_key
            for row in neutral_a.all_opportunities
            if (row.anchor_sha256, row.focal_user) == key
        }
        selected_keys = {
            row.opportunity_key
            for row in neutral_a.opportunities
            if (row.anchor_sha256, row.focal_user) == key
        }
        assert selected_keys == all_keys

    informed_sizes = sorted(
        sum(
            (row.anchor_sha256, row.focal_user) == key
            for row in informed.opportunities
        )
        for key in informed.selected_focal_users
    )
    neutral_sizes = sorted(
        sum(
            (row.anchor_sha256, row.focal_user) == key
            for row in neutral_a.opportunities
        )
        for key in neutral_a.selected_focal_users
    )
    assert neutral_sizes == informed_sizes


def test_cluster_neutral_matches_heterogeneous_anchor_profiles_one_to_one() -> None:
    records = _heterogeneous_profile_records()
    informed = select_c1_source(
        records,
        config=C1FrontierConfig(
            lower_anchor_fraction=0.5,
            lower_user_fraction=0.5,
        ),
    )
    assert informed is not None

    neutral_a = sample_c1_cluster_matched_neutral_source(
        informed,
        rng=np.random.default_rng(20260906),
    )
    neutral_b = sample_c1_cluster_matched_neutral_source(
        informed,
        rng=np.random.default_rng(20260906),
    )
    reordered = select_c1_source(
        tuple(reversed(records)),
        config=C1FrontierConfig(
            lower_anchor_fraction=0.5,
            lower_user_fraction=0.5,
        ),
    )
    assert reordered is not None
    neutral_reordered = sample_c1_cluster_matched_neutral_source(
        reordered,
        rng=np.random.default_rng(20260906),
    )

    def profiles(plan):
        sizes = {
            key: sum(
                (row.anchor_sha256, row.focal_user) == key
                for row in plan.opportunities
            )
            for key in plan.selected_focal_users
        }
        return sorted(
            tuple(sorted(sizes[key] for key in plan.selected_focal_users if key[0] == anchor))
            for anchor in plan.selected_anchor_sha256s
        )

    assert profiles(informed) == [(1,), (2,)]
    assert profiles(neutral_a) == profiles(informed)
    assert neutral_a.budget == informed.budget == 3
    assert len(neutral_a.selected_anchor_sha256s) == 2
    assert [row.opportunity_key for row in neutral_a.opportunities] == [
        row.opportunity_key for row in neutral_b.opportunities
    ]
    assert [row.opportunity_key for row in neutral_a.opportunities] == [
        row.opportunity_key for row in neutral_reordered.opportunities
    ]


def test_profile_anchor_matcher_uses_augmenting_paths_not_greedy_assignment() -> None:
    # Profile 0 can use either anchor, while profile 1 can only use ``a``.
    # A greedy draw may consume ``a`` first; a complete matcher must then
    # reassign profile 0 to ``b`` rather than report false infeasibility.
    graph = (("a", "b"), ("a",))
    for seed in range(32):
        matched = _randomized_profile_anchor_matching(
            graph,
            rng=np.random.default_rng(seed),
        )
        assert matched == ("b", "a")


def test_selector_rejects_mixed_partition_duplicate_anchor_and_invalid_reference() -> None:
    with pytest.raises(C1SelectorContractError, match="TRAIN"):
        select_c1_source([_record(anchor="a", source_seed=1, step=0, frontier_score=1.0, user_scores=(1.0, 1.0), partition="TEST")])

    duplicate = _record(anchor="a", source_seed=2, step=1, frontier_score=2.0, user_scores=(1.0, 1.0))
    with pytest.raises(C1SelectorContractError, match="anchors must be disjoint"):
        select_c1_source([_records()[0], duplicate])

    bad = _records()[0]
    bad_actions = np.asarray([-1, 0], dtype=np.int64)
    malformed = C1DullRolloutRecord(
        **{
            **bad.__dict__,
            "reference_actions": bad_actions,
        }
    )
    with pytest.raises(C1SelectorContractError, match="no-op"):
        select_c1_source([malformed])


def test_config_and_lineage_are_fail_closed() -> None:
    with pytest.raises(C1SelectorContractError, match="lower_anchor_fraction"):
        select_c1_source(_records(), config=C1FrontierConfig(lower_anchor_fraction=0.0))

    stale = _record(anchor="a", source_seed=1, step=0, frontier_score=1.0, user_scores=(1.0, 1.0))
    with pytest.raises(C1SelectorContractError, match="source manifest|state schema"):
        select_c1_source(
            [
                stale,
                C1DullRolloutRecord(
                    **{
                        **stale.__dict__,
                        "record_id": "dull-other",
                        "anchor_sha256": "b" * 64,
                        "source_manifest_sha256": "3" * 64,
                    }
                ),
            ]
        )

    current = _record(
        anchor="c",
        source_seed=3,
        step=0,
        frontier_score=1.0,
        user_scores=(1.0, 1.0),
    )
    stale_schema = C1DullRolloutRecord(
        **{
            **current.__dict__,
            "state_schema": "multi-catfish-mcrl-v03-causal-state-v1",
            "state_schema_sha256": "2" * 64,
        }
    )
    with pytest.raises(C1SelectorContractError, match="current V0.3 causal state"):
        select_c1_source([stale_schema])
