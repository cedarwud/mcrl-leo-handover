from __future__ import annotations

from copy import deepcopy
import ast
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "v023_c1c2_predecision_capture.py"
SPEC = importlib.util.spec_from_file_location(
    "v023_c1c2_predecision_capture_test", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

from mcrl.env.action_contract import Association, NUM_ACTIONS, SlotTable  # noqa: E402
from mcrl.runtime.ee_axis_c1_selector import C1DullRolloutRecord  # noqa: E402
from mcrl.runtime.ee_axis_state import (  # noqa: E402
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)


def _digest(number: int) -> str:
    return f"{number:064x}"


def _table(*, offset: int = 0, three: bool = True) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    count = 3 if three else 2
    for action in range(count):
        norads[action] = 1000 + offset + action
        cells[action] = 10 + action
        mask[action] = True
    return SlotTable(norads, cells, mask)


def _anchor(*, incumbent=(2000, 20), reference=(1000, 10), index=0):
    table = _table(offset=index)
    candidate_sinr = [0.0] * NUM_ACTIONS
    candidate_sinr[1] = 5.0
    candidate_sinr[2] = 4.0
    return module.build_c2_anchor_payload(
        world_id=2026121705 + index,
        source_seed=2026121705 + index,
        source_manifest_sha256="a" * 64,
        checkpoint_sha256="b" * 64,
        state_schema=EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
        state_sha256=_digest(100 + index),
        observation_sha256=_digest(200 + index),
        step_index=1,
        focal_user=0,
        reference_action=0,
        incumbent_physical_key=incumbent,
        candidate_sinr=candidate_sinr,
        slot_table=table,
    )


def _c1_state_sha256(index: int = 0) -> str:
    return _digest(50 + index)


def _c1_record(index: int = 0, *, three: bool = True) -> C1DullRolloutRecord:
    table = _table(offset=index, three=three)
    world = 2026121705 + index
    anchor_sha256 = module.load_materializer().c1_anchor_sha256(
        {
            "source_seed": world,
            "step_index": 0,
            "state_sha256": _c1_state_sha256(index),
            "reference_actions": [0, 0],
            "slot_tables": [
                module._slot_table_payload(table),
                module._slot_table_payload(table),
            ],
        }
    )
    return C1DullRolloutRecord(
        record_id=f"c1-record-{index}",
        anchor_sha256=anchor_sha256,
        source_manifest_sha256="a" * 64,
        checkpoint_sha256="b" * 64,
        state_schema=EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
        source_seed=world,
        step_index=0,
        partition="TRAIN",
        rollout_kind="dull-rollout",
        policy_name="local-snr-greedy-v1",
        frontier_score=1.0,
        user_frontier_scores=np.array([1.0, 2.0], dtype=np.float64),
        reference_actions=np.array([0, 0], dtype=np.int64),
        slot_tables=(table, table),
    )


def _world_payload(index: int):
    world = 2026121705 + index
    record = _c1_record(index)
    anchor = _anchor(index=index)
    return module.build_capture_payload(
        pool_id=f"v023-train-world-{world}-predecision",
        provenance={
            "source_manifest_sha256": "a" * 64,
            "checkpoint_sha256": "b" * 64,
            "state_schema": EE_AXIS_STATE_SCHEMA,
            "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        },
        frontier_config={
            "lower_anchor_fraction": 0.5,
            "lower_user_fraction": 0.5,
            "max_anchors": None,
            "max_focal_users_per_anchor": None,
        },
        c1_neutral_seed=world + 17,
        c1_records=(
            module.c1_record_payload(
                record,
                state_sha256=_c1_state_sha256(index),
            ),
        ),
        c2_neutral_seed=world + 31,
        c2_anchors=(anchor,),
        c2_informed=(module.c2_informed_payload(anchor),),
    )


def test_slot_table_alternatives_are_canonical_and_alias_free() -> None:
    assert module.CLAIM_CEILING == (
        "TRAIN_PREDECISION_SIMULATOR_SOURCE_ONLY_NO_LEARNER_NO_TEST_NO_EFFICACY"
    )
    table = _table()
    rows = module.legal_physical_alternatives(table, reference_action=0)
    assert rows == (
        {"action": 1, "physical_key": [1001, 11]},
        {"action": 2, "physical_key": [1002, 12]},
    )

    alias_norads = np.array(table.norad_ids, copy=True)
    alias_cells = np.array(table.cell_ids, copy=True)
    alias_mask = np.array(table.mask, copy=True)
    alias_norads[3] = alias_norads[1]
    alias_cells[3] = alias_cells[1]
    alias_mask[3] = True
    with pytest.raises(module.CaptureBridgeError, match="physical alias"):
        module.legal_physical_alternatives(
            SlotTable(alias_norads, alias_cells, alias_mask), reference_action=0
        )


def test_departure_detection_is_physical_and_ignores_unserved_or_same_key() -> None:
    table = _table()
    refs = np.array([0, 1, -1, 0], dtype=np.int64)
    previous = [
        Association(2000, 20),
        Association(1001, 11),
        None,
        Association(1000, 10),
    ]
    departures = module.detect_physical_departures(
        refs, previous, (table,) * 4, step_index=1
    )
    assert [(item.focal_user, item.reference_action) for item in departures] == [(0, 0)]
    assert departures[0].incumbent_physical_key == (2000, 20)

    with pytest.raises(module.CaptureBridgeError, match="step_index"):
        module.detect_physical_departures(refs, previous, (table,) * 4, step_index=0)


def test_c2_candidate_prefers_hold_then_uses_max_sinr_with_canonical_tie() -> None:
    alternatives = (
        {"action": 1, "physical_key": [2000, 20]},
        {"action": 2, "physical_key": [1000, 10]},
    )
    result = module.choose_c2_informed_candidate(
        incumbent_physical_key=(2000, 20),
        alternatives=alternatives,
        candidate_sinr=[0.0, 1.0, 9.0] + [0.0] * (NUM_ACTIONS - 3),
    )
    assert result == (1, (2000, 20), "incumbent-hold")

    result = module.choose_c2_informed_candidate(
        incumbent_physical_key=(9999, 99),
        alternatives=alternatives,
        candidate_sinr=[0.0, 9.0, 9.0] + [0.0] * (NUM_ACTIONS - 3),
    )
    # Equal SINR is resolved by physical key, then action.
    assert result == (2, (1000, 10), "max-lagged-candidate-sinr-rival")


def test_anchor_digest_uses_materializer_v2_helper() -> None:
    anchor = _anchor()
    assert anchor["anchor_sha256"] == module.c2_anchor_sha256(anchor)
    mutated = deepcopy(anchor)
    mutated["candidate_sinr"][1] = 5.5
    assert mutated["anchor_sha256"] != module.c2_anchor_sha256(mutated)


def test_capture_payload_materializes_against_v2_and_is_outcome_blind() -> None:
    c1 = module.c1_record_payload(
        _c1_record(), state_sha256=_c1_state_sha256()
    )
    anchor = _anchor()
    informed = module.c2_informed_payload(anchor)
    payload = module.build_capture_payload(
        pool_id="v023-train-world-2026121705-predecision",
        provenance={
            "source_manifest_sha256": "a" * 64,
            "checkpoint_sha256": "b" * 64,
            "state_schema": EE_AXIS_STATE_SCHEMA,
            "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        },
        frontier_config={
            "lower_anchor_fraction": 0.5,
            "lower_user_fraction": 0.5,
            "max_anchors": None,
            "max_focal_users_per_anchor": None,
        },
        c1_neutral_seed=37,
        c1_records=(c1,),
        c2_neutral_seed=53,
        c2_anchors=(anchor,),
        c2_informed=(informed,),
    )
    assert payload["schema"] == module.SCHEMA
    assert payload["split"] == "TRAIN"
    assert payload["pool_sha256"] == module.recompute_pool_sha256(payload)
    materializer = module.load_materializer()
    bundle = materializer.materialize_capture(payload)
    bundle.verify()
    assert bundle.c1_informed.budget == bundle.c1_neutral.budget
    assert bundle.c2_informed.budget == bundle.c2_neutral.budget

    bad = deepcopy(payload)
    bad["c2"]["target"] = 1  # type: ignore[index]
    with pytest.raises(module.CaptureBridgeError, match="forbidden field"):
        module.build_capture_payload(
            pool_id=bad["pool_id"],
            provenance=bad["provenance"],
            frontier_config=bad["c1"]["frontier_config"],
            c1_neutral_seed=bad["c1"]["neutral_seed"],
            c1_records=bad["c1"]["records"],
            c2_neutral_seed=bad["c2"]["neutral_seed"],
            c2_anchors=bad["c2"]["anchors"],
            c2_informed=bad["c2"]["informed"],
            extra_c2_fields={"target": 1},
        )


def test_write_capture_is_canonical_and_write_once(tmp_path: Path) -> None:
    c1 = module.c1_record_payload(
        _c1_record(), state_sha256=_c1_state_sha256()
    )
    anchor = _anchor()
    payload = module.build_capture_payload(
        pool_id="v023-train-world-2026121705-predecision",
        provenance={
            "source_manifest_sha256": "a" * 64,
            "checkpoint_sha256": "b" * 64,
            "state_schema": EE_AXIS_STATE_SCHEMA,
            "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        },
        frontier_config={
            "lower_anchor_fraction": 0.5,
            "lower_user_fraction": 0.5,
            "max_anchors": None,
            "max_focal_users_per_anchor": None,
        },
        c1_neutral_seed=37,
        c1_records=(c1,),
        c2_neutral_seed=53,
        c2_anchors=(anchor,),
        c2_informed=(module.c2_informed_payload(anchor),),
    )
    output = tmp_path / "capture.json"
    digest = module.write_capture(payload, output)
    assert output.read_bytes() == module.canonical_bytes(payload) + b"\n"
    assert digest == module.file_sha256(output)
    with pytest.raises(module.CaptureBridgeError, match="overwrite"):
        module.write_capture(payload, output)


def test_write_capture_validates_one_world_without_panel_neutral_sampling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A write-once world capture is not yet a panel selection population."""

    records = (
        module.c1_record_payload(
            _c1_record(0, three=True), state_sha256=_c1_state_sha256(0)
        ),
        module.c1_record_payload(
            _c1_record(1, three=False), state_sha256=_c1_state_sha256(1)
        ),
    )
    anchors = (_anchor(index=0), _anchor(index=1))
    payload = module.build_capture_payload(
        pool_id="v023-train-world-predecision-structural-only",
        provenance={
            "source_manifest_sha256": "a" * 64,
            "checkpoint_sha256": "b" * 64,
            "state_schema": EE_AXIS_STATE_SCHEMA,
            "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        },
        frontier_config={
            "lower_anchor_fraction": 1.0,
            "lower_user_fraction": 0.5,
            "max_anchors": None,
            "max_focal_users_per_anchor": None,
        },
        c1_neutral_seed=37,
        c1_records=records,
        c2_neutral_seed=53,
        c2_anchors=anchors,
        c2_informed=tuple(module.c2_informed_payload(anchor) for anchor in anchors),
    )
    # This is the exact staging distinction: the one-world capture is fully
    # authenticated, but it is not entitled to run a panel-level neutral draw.
    materializer = module.load_materializer()
    original_validate = materializer.validate_capture
    validation_calls = 0

    def record_validation(candidate):
        nonlocal validation_calls
        validation_calls += 1
        return original_validate(candidate)

    def reject_materialization(_candidate):
        raise AssertionError("panel materializer ran inside one-world write")

    monkeypatch.setattr(materializer, "validate_capture", record_validation)
    monkeypatch.setattr(materializer, "materialize_capture", reject_materialization)

    output = tmp_path / "one-world-capture.json"
    digest = module.write_capture(payload, output)
    assert digest == module.file_sha256(output)
    assert validation_calls == 1


def test_merge_world_captures_materializes_once_over_exact_frozen_panel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worlds = tuple(_world_payload(index) for index in range(8))
    materializer = module.load_materializer()
    original_materialize = materializer.materialize_capture

    def reject_per_world_materialization(_payload):
        raise AssertionError("panel materializer ran before the eight-world merge")

    monkeypatch.setattr(materializer, "materialize_capture", reject_per_world_materialization)
    panel = module.merge_world_captures(
        reversed(worlds),
        c1_neutral_seed=2026121791,
        c2_neutral_seed=2026121792,
    )
    monkeypatch.setattr(materializer, "materialize_capture", original_materialize)
    assert panel["pool_id"] == module.PANEL_POOL_ID
    assert len(panel["c1"]["records"]) == 8
    assert len(panel["c2"]["anchors"]) == 8
    assert panel["pool_sha256"] == module.recompute_pool_sha256(panel)
    bundle = materializer.materialize_capture(panel)
    bundle.verify()
    assert bundle.c1_informed.budget == bundle.c1_neutral.budget
    assert bundle.c2_informed.budget == bundle.c2_neutral.budget

    with pytest.raises(module.CaptureBridgeError, match="exactly the frozen worlds"):
        module.merge_world_captures(
            worlds[:-1],
            c1_neutral_seed=2026121791,
            c2_neutral_seed=2026121792,
        )


def test_server_entrypoint_is_import_inert() -> None:
    source = (HERE / "run_v023_c1c2_predecision_capture_server.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    top_level_imports = [
        node
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    imported_roots = set()
    for node in top_level_imports:
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif node.module:
            imported_roots.add(node.module.split(".")[0])
    assert not {"mcrl", "numpy", "torch", "scipy"} & imported_roots
    assert "if __name__ == \"__main__\"" in source


def test_panel_merge_entrypoint_is_import_inert() -> None:
    source = (HERE / "merge_v023_c1c2_predecision_captures.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    top_level_imports = [
        node
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    imported_roots = set()
    for node in top_level_imports:
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif node.module:
            imported_roots.add(node.module.split(".")[0])
    assert not {"mcrl", "numpy", "torch", "scipy"} & imported_roots
    assert "if __name__ == \"__main__\"" in source
