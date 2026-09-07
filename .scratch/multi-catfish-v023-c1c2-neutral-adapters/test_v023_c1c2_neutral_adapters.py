"""Synthetic checks for the V0.23 C1/C2 source-binding adapter."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.runtime.ee_axis_c1_selector import (
    C1_ACRM_PAIR_RULE,
    C1_CLUSTER_NEUTRAL_SOURCE_RULE,
    C1_INFORMED_SOURCE_RULE,
    C1SourceSelection,
    C1UnilateralOpportunity,
    sample_c1_cluster_matched_neutral_source,
)
from mcrl.runtime.ee_axis_c2_neutral_source import (
    C2_INFORMED_SOURCE_RULE,
    C2_NEUTRAL_SOURCE_RULE,
    C2PredecisionOpportunity,
    C2SourceSelection,
    sample_c2_neutral_source,
)
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "v023_c1c2_neutral_adapters.py"
SPEC = importlib.util.spec_from_file_location(
    "v023_c1c2_neutral_adapters_test", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


def _common() -> dict[str, object]:
    worlds = ("train-world-a", "train-world-b")
    seeds = (101, 202)
    return {
        "split": "TRAIN",
        "world_ids": worlds,
        "training_seeds": seeds,
        "world_sha256": adapter.canonical_sha256({"world_ids": list(worlds)}),
        "seed_sha256": adapter.canonical_sha256({"training_seeds": list(seeds)}),
    }


def _slot_table() -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    norads[0], cells[0], mask[0] = 101, 1, True
    norads[1], cells[1], mask[1] = 102, 2, True
    return SlotTable(norads, cells, mask)


def _c1_informed() -> C1SourceSelection:
    table = _slot_table()
    rows: list[C1UnilateralOpportunity] = []
    anchors = ("1" * 64, "2" * 64)
    for anchor_index, anchor in enumerate(anchors):
        for candidate_action, candidate_key, row_index in (
            (1, (102, 2), 0),
            (0, (101, 1), 1),
        ):
            # The second row uses a different physical reference/action so
            # candidate and reference remain a genuine unilateral change.
            reference_action = 0 if candidate_action == 1 else 1
            reference_key = (101, 1) if candidate_action == 1 else (102, 2)
            reference = np.array([reference_action, 0], dtype=np.int64)
            candidate = np.array([candidate_action, 0], dtype=np.int64)
            rows.append(
                C1UnilateralOpportunity(
                    anchor_sha256=anchor,
                    source_record_sha256=(str(3 + anchor_index * 2 + row_index) * 64)[:64],
                    source_manifest_sha256="a" * 64,
                    checkpoint_sha256="b" * 64,
                    state_schema=EE_AXIS_STATE_SCHEMA,
                    state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
                    step_index=0,
                    source_rule=C1_INFORMED_SOURCE_RULE,
                    acrm_pair_rule=C1_ACRM_PAIR_RULE,
                    anchor_rank=anchor_index,
                    anchor_stratum="lower",
                    focal_user=0,
                    user_rank=0,
                    user_stratum="lower",
                    reference_action=reference_action,
                    candidate_action=candidate_action,
                    reference_physical_key=reference_key,
                    candidate_physical_key=candidate_key,
                    reference_actions=reference,
                    candidate_actions=candidate,
                    action_mask=table.mask,
                )
            )
    return C1SourceSelection(
        selector_schema="multi-catfish-mcrl-v03-c1-predecision-selector-v1",
        source_rule=C1_INFORMED_SOURCE_RULE,
        acrm_pair_rule=C1_ACRM_PAIR_RULE,
        partition="TRAIN",
        source_manifest_sha256="a" * 64,
        checkpoint_sha256="b" * 64,
        state_schema=EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
        eligible_anchor_sha256s=anchors,
        selected_anchor_sha256s=anchors,
        eligible_focal_users=tuple((anchor, 0) for anchor in anchors),
        selected_focal_users=tuple((anchor, 0) for anchor in anchors),
        all_opportunities=tuple(rows),
        opportunities=tuple(rows),
    )


def _c2_universe() -> tuple[C2PredecisionOpportunity, ...]:
    rows: list[C2PredecisionOpportunity] = []
    for anchor_index, anchor in enumerate(("3" * 64, "4" * 64)):
        for action, key in ((1, (102 + anchor_index, 2)), (2, (103 + anchor_index, 3))):
            rows.append(
                C2PredecisionOpportunity(
                    anchor_sha256=anchor,
                    step_index=0,
                    focal_user=0,
                    reference_action=0,
                    reference_physical_key=(101 + anchor_index, 1),
                    candidate_action=action,
                    candidate_physical_key=key,
                    source_rule=C2_NEUTRAL_SOURCE_RULE,
                )
            )
    return tuple(rows)


class _SyntheticC2Informed:
    route = "C2"
    source_rule = C2_INFORMED_SOURCE_RULE
    budget = 2
    authenticated = True

    def __init__(self, *, all_opportunities=None, **metadata: object) -> None:
        self.metadata = metadata
        self.all_opportunities = tuple(
            _c2_universe() if all_opportunities is None else all_opportunities
        )
        self.verify_calls = 0

    def verify(self) -> None:
        self.verify_calls += 1


def _bundle(**kwargs: object):
    common = _common()
    c1 = _c1_informed()
    c1_neutral = sample_c1_cluster_matched_neutral_source(
        c1, rng=np.random.default_rng(9)
    )
    c2_universe = _c2_universe()
    c2_neutral = sample_c2_neutral_source(
        c2_universe,
        informed_budget=2,
        rng=np.random.default_rng(11),
        random_seed=11,
    )
    values = {
        "common": common,
        "c1_informed": c1,
        "c1_cluster_neutral": c1_neutral,
        "c2_informed": _SyntheticC2Informed(),
        "c2_equal_budget_neutral": c2_neutral,
        "c1_informed_sha256": "5" * 64,
        "c1_neutral_sha256": "6" * 64,
        "c2_informed_sha256": "7" * 64,
        "c2_neutral_sha256": None,
        "c1_informed_identity": "c1-informed",
        "c1_neutral_identity": "c1-neutral",
        "c2_informed_identity": "c2-informed",
        "c2_neutral_identity": "c2-neutral",
        "c1_learner_initialization_ids": (11, 12, 13),
        "c1_learner_config_sha256": "c" * 64,
        "c1_learner_update_count": 10,
        "c2_learner_initialization_ids": (21, 22, 23),
        "c2_learner_config_sha256": "d" * 64,
        "c2_learner_update_count": 3000,
    }
    values.update(kwargs)
    return adapter.bind_c1_c2_source_pairs(**values)


def test_binds_real_selector_outputs_with_equal_pair_budgets():
    bundle = _bundle()

    bundle.verify()
    assert bundle.schema == adapter.SCHEMA
    assert bundle.c1.row_budget == 4
    assert bundle.c2.row_budget == 2
    assert bundle.c1.informed.learner_initialization_ids == (11, 12, 13)
    assert bundle.c1.informed.learner_update_count == 10
    assert bundle.c2.informed.learner_initialization_ids == (21, 22, 23)
    assert bundle.c2.informed.learner_update_count == 3000
    assert bundle.c1.informed.source_rule == C1_INFORMED_SOURCE_RULE
    assert bundle.c1.neutral.source_rule == C1_CLUSTER_NEUTRAL_SOURCE_RULE
    assert bundle.c2.informed.source_rule == C2_INFORMED_SOURCE_RULE
    assert bundle.c2.neutral.source_rule == C2_NEUTRAL_SOURCE_RULE
    assert bundle.to_dict()["schema"] == adapter.SCHEMA
    assert bundle.to_dict()["route_learner_budgets"] == {
        "C1": {"initialization_count": 3, "update_count": 10},
        "C2": {"initialization_count": 3, "update_count": 3000},
    }


def test_adapter_rejects_digest_or_identity_aliasing():
    with pytest.raises(adapter.C1C2NeutralBindingError, match="aliases the informed digest"):
        _bundle(c1_neutral_sha256="5" * 64)

    with pytest.raises(adapter.C1C2NeutralBindingError, match="aliases the informed identity"):
        _bundle(c2_neutral_identity="c2-informed")

    with pytest.raises(adapter.C1C2NeutralBindingError, match="aliases distinct bindings"):
        _bundle(c2_informed_sha256="5" * 64)


def test_adapter_rejects_c1_cluster_profile_or_budget_drift():
    c1 = _c1_informed()
    neutral = sample_c1_cluster_matched_neutral_source(
        c1, rng=np.random.default_rng(9)
    )
    # Removing one opportunity makes the neutral object fail its own
    # cluster/ACRM verification before it can enter the pair.
    broken = replace(neutral, opportunities=neutral.opportunities[:-1])
    with pytest.raises(adapter.C1C2NeutralBindingError):
        _bundle(c1_cluster_neutral=broken)


def test_adapter_rejects_c2_universe_drift_even_when_budget_matches():
    universe = _c2_universe()
    neutral = sample_c2_neutral_source(
        universe,
        informed_budget=2,
        rng=np.random.default_rng(11),
        random_seed=11,
    )
    extra = C2PredecisionOpportunity(
        anchor_sha256="8" * 64,
        step_index=1,
        focal_user=0,
        reference_action=0,
        reference_physical_key=(301, 1),
        candidate_action=1,
        candidate_physical_key=(302, 2),
        source_rule=C2_NEUTRAL_SOURCE_RULE,
    )
    informed = _SyntheticC2Informed(all_opportunities=universe + (extra,))
    with pytest.raises(
        adapter.C1C2NeutralBindingError,
        match="exact physical universe",
    ):
        _bundle(
            c2_informed=informed,
            c2_equal_budget_neutral=neutral,
        )


@pytest.mark.parametrize(
    "metadata",
    (
        {"episode_count": 10},
        {"head_drop": True},
        {"test_split_opened": True},
        {"config_sha256": "b" * 64},
    ),
)
def test_adapter_rejects_forbidden_or_drifted_c2_metadata(metadata):
    with pytest.raises(adapter.C1C2NeutralBindingError):
        _bundle(c2_informed=_SyntheticC2Informed(**metadata))


def test_adapter_rejects_forbidden_fields_on_mapping_artifacts():
    source = {
        "route": "C2",
        "source_rule": C2_INFORMED_SOURCE_RULE,
        "budget": 2,
        "authenticated": True,
        "episode_count": 10,
    }
    with pytest.raises(adapter.C1C2NeutralBindingError, match="forbidden episode_count"):
        _bundle(c2_informed=source)


def test_adapter_rejects_test_common_binding():
    common = _common()
    common["split"] = "TEST"
    with pytest.raises(adapter.C1C2NeutralBindingError, match="TRAIN-only"):
        _bundle(common=common)

    common = _common()
    common["world_ids"] = ("train-world-a", "TEST-world")
    with pytest.raises(adapter.C1C2NeutralBindingError, match="TEST"):
        _bundle(common=common)

    common = _common()
    common["learner_update_count"] = 2000
    with pytest.raises(adapter.C1C2NeutralBindingError, match="non-common route fields"):
        _bundle(common=common)


def test_adapter_does_not_expose_execution_or_training_surface():
    bundle = _bundle()
    forbidden = {
        name
        for name in dir(bundle)
        if any(token in name.lower() for token in ("train", "execute", "simulate", "rollout", "step"))
    }
    assert forbidden == set()


def test_c2_neutral_selection_digest_can_be_bound_without_implicit_hashing():
    bundle = _bundle(c2_neutral_sha256=None)
    assert bundle.c2.neutral.selection_digest == bundle.c2.neutral.source_sha256
