from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "materialize_v023_c1c2.py"
SPEC = importlib.util.spec_from_file_location("v023_c1c2_materialization_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

from mcrl.runtime.ee_axis_state import (  # noqa: E402
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)
from mcrl.env.action_contract import NUM_ACTIONS  # noqa: E402


def _digest(number: int) -> str:
    return f"{number:064x}"


def _slot_table(offset: int) -> dict[str, object]:
    # Two legal physical alternatives at every user; this gives every anchor
    # the same C1 cluster profile so the cluster-matched neutral can be drawn.
    norads = [-1] * NUM_ACTIONS
    cells = [-1] * NUM_ACTIONS
    mask = [False] * NUM_ACTIONS
    norads[0], cells[0], mask[0] = 100 + offset, 1, True
    norads[1], cells[1], mask[1] = 200 + offset, 2, True
    return {"norad_ids": norads, "cell_ids": cells, "mask": mask}


def _c1_record(index: int, *, source_manifest: str, checkpoint: str) -> dict[str, object]:
    state_sha256 = _digest(101 + index)
    reference_actions = [0, 0]
    slot_tables = [_slot_table(index * 10), _slot_table(index * 10 + 1)]
    anchor_sha256 = module.c1_anchor_sha256(
        {
            "source_seed": 1000 + index,
            "step_index": index,
            "state_sha256": state_sha256,
            "reference_actions": reference_actions,
            "slot_tables": slot_tables,
        }
    )
    return {
        "record_id": f"record-{index}",
        "anchor_sha256": anchor_sha256,
        "source_manifest_sha256": source_manifest,
        "checkpoint_sha256": checkpoint,
        "state_schema": EE_AXIS_STATE_SCHEMA,
        "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        "state_sha256": state_sha256,
        "source_seed": 1000 + index,
        "step_index": index,
        "partition": "TRAIN",
        "rollout_kind": "dull-rollout",
        "policy_name": "frozen-main",
        "frontier_score": float(index),
        "user_frontier_scores": [float(index), float(index) + 0.25],
        "reference_actions": reference_actions,
        "slot_tables": slot_tables,
    }


def _c2_anchor(index: int) -> dict[str, object]:
    source_manifest = "a" * 64
    checkpoint = "b" * 64
    norads = [-1] * NUM_ACTIONS
    cells = [-1] * NUM_ACTIONS
    mask = [False] * NUM_ACTIONS
    norads[0], cells[0], mask[0] = 1000 + index, 1, True
    norads[1], cells[1], mask[1] = 2000 + index, 2, True
    norads[2], cells[2], mask[2] = 3000 + index, 3, True
    slot_table = {"norad_ids": norads, "cell_ids": cells, "mask": mask}
    candidate_sinr = [0.0] * NUM_ACTIONS
    candidate_sinr[1] = 5.0
    candidate_sinr[2] = 4.0
    alternatives = [
        {"action": 1, "physical_key": [2000 + index, 2]},
        {"action": 2, "physical_key": [3000 + index, 3]},
    ]
    body = {
        "schema": module.C2_ANCHOR_SCHEMA,
        "world_id": 2026121705 + index,
        "source_seed": 2026121705 + index,
        "source_manifest_sha256": source_manifest,
        "checkpoint_sha256": checkpoint,
        "state_schema": EE_AXIS_STATE_SCHEMA,
        "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        "state_sha256": _digest(201 + index),
        "observation_sha256": _digest(301 + index),
        "step_index": index,
        "focal_user": 0,
        "reference_action": 0,
        "reference_physical_key": [1000 + index, 1],
        "incumbent_physical_key": [2000 + index, 2],
        "candidate_sinr": candidate_sinr,
        "slot_table": slot_table,
        "legal_alternatives": alternatives,
        "horizon_steps": module.C2_HORIZON_STEPS,
        "release_grammar": module.C2_POLICY_VERSION,
    }
    return {"anchor_sha256": module.canonical_sha256(body), **{k: v for k, v in body.items() if k != "schema"}}


def _c2_informed(index: int) -> dict[str, object]:
    anchor = _c2_anchor(index)
    return {
        "anchor_sha256": anchor["anchor_sha256"],
        "step_index": index,
        "focal_user": 0,
        "reference_action": 0,
        "reference_physical_key": [1000 + index, 1],
        "candidate_action": 1,
        "candidate_physical_key": [2000 + index, 2],
        "source_rule": "incumbent-hold",
    }


def _payload() -> dict[str, object]:
    source_manifest = "a" * 64
    checkpoint = "b" * 64
    c1_records = [
        _c1_record(index, source_manifest=source_manifest, checkpoint=checkpoint)
        for index in range(4)
    ]
    c2_anchors = [_c2_anchor(index) for index in range(4)]
    c2_informed = [_c2_informed(index) for index in range(4)]
    payload: dict[str, object] = {
        "schema": module.SCHEMA,
        "split": "TRAIN",
        "pool_id": "synthetic-train-pool",
        "pool_sha256": "0" * 64,
        "provenance": {
            "source_manifest_sha256": source_manifest,
            "checkpoint_sha256": checkpoint,
            "state_schema": EE_AXIS_STATE_SCHEMA,
            "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        },
        "c1": {
            "frontier_config": {
                "lower_anchor_fraction": 0.5,
                "lower_user_fraction": 1.0,
                "max_anchors": None,
                "max_focal_users_per_anchor": None,
            },
            "neutral_seed": 37,
            "records": c1_records,
        },
        "c2": {
            "neutral_seed": 53,
            "anchors": c2_anchors,
            "informed": c2_informed,
        },
    }
    payload["pool_sha256"] = module.canonical_sha256(module._pool_payload(payload))
    return payload


def _write_canonical(path: Path, payload: object) -> None:
    path.write_bytes(module.canonical_bytes(payload) + b"\n")


def test_materializes_both_routes_with_route_local_equal_budgets() -> None:
    bundle = module.materialize_capture(_payload())
    bundle.verify()
    assert bundle.pool_id == "synthetic-train-pool"
    assert bundle.c1_informed.budget == bundle.c1_neutral.budget == 4
    assert bundle.c2_informed.budget == bundle.c2_neutral.budget == 4
    assert bundle.c1_informed.source_rule == module.C1_INFORMED_SOURCE_RULE
    assert bundle.c1_neutral.source_rule == module.C1_CLUSTER_NEUTRAL_SOURCE_RULE
    assert bundle.c2_neutral.source_rule == module.C2_NEUTRAL_SOURCE_RULE
    assert all(row.source_rule in module.C2_INFORMED_ROW_RULES for row in bundle.c2_informed.opportunities)


def test_materialization_is_deterministic_for_frozen_neutral_seeds() -> None:
    first = module.materialize_capture(_payload())
    second = module.materialize_capture(_payload())
    assert [row.opportunity_key for row in first.c1_neutral.opportunities] == [
        row.opportunity_key for row in second.c1_neutral.opportunities
    ]
    assert [row.opportunity_key for row in first.c2_neutral.opportunities] == [
        row.opportunity_key for row in second.c2_neutral.opportunities
    ]


def test_writer_seals_files_and_refuses_overwrite(tmp_path: Path) -> None:
    bundle = module.materialize_capture(_payload())
    output = tmp_path / "materialized"
    report = module.write_materialization(bundle, output)
    assert report["manifest_entries"] == 5
    manifest = output / "MANIFEST.sha256"
    lines = manifest.read_text(encoding="ascii").splitlines()
    assert len(lines) == 5
    for line in lines:
        digest, name = line.split("  ", 1)
        assert module.file_sha256(output / name) == digest
    c2_informed = module.read_canonical_json(output / "c2-informed.json")
    assert c2_informed["provenance"] == _payload()["provenance"]
    for anchor in c2_informed["anchors"]:
        assert module.c2_anchor_sha256(anchor) == anchor["anchor_sha256"]
    receipt = module.read_canonical_json(output / "receipt.json")
    audit = receipt["c1_cluster_match_audit"]
    assert audit["matching_rule"] == module.C1_CLUSTER_NEUTRAL_SOURCE_RULE
    assert audit["predecision_only"] is True
    assert audit["uniform_over_all_feasible_matchings_claimed"] is False
    assert audit["exact_profile_multiset"] is True
    assert audit["informed_anchor_count"] == audit["neutral_anchor_count"] == 2
    assert audit["informed_focal_user_count"] == audit["neutral_focal_user_count"] == 4
    assert audit["informed_row_count"] == audit["neutral_row_count"] == 4
    assert len(audit["canonical_profile_pairing"]) == 2
    assert all(
        item["alternative_count_histogram"]
        == [{"alternative_count": 1, "focal_user_count": 2}]
        for item in audit["canonical_profile_pairing"]
    )
    with pytest.raises(module.MaterializationError, match="overwrite"):
        module.write_materialization(bundle, output)


def test_rejects_outcome_fields_and_test_split() -> None:
    with pytest.raises(module.MaterializationError, match="forbidden field target"):
        bad = _payload()
        bad["c2"] = {**bad["c2"], "target": 1}  # type: ignore[index]
        module.materialize_capture(bad)

    with pytest.raises(module.MaterializationError, match="split must be exactly TRAIN"):
        bad = _payload()
        bad["split"] = "TEST"
        module.materialize_capture(bad)


def test_rejects_pool_digest_drift_and_informed_budget_zero() -> None:
    bad = _payload()
    bad["pool_sha256"] = "c" * 64
    with pytest.raises(module.MaterializationError, match="pool_sha256 mismatch"):
        module.materialize_capture(bad)

    bad = _payload()
    bad["c2"] = {**bad["c2"], "informed": []}  # type: ignore[index]
    bad["pool_sha256"] = module.canonical_sha256(module._pool_payload(bad))
    with pytest.raises(module.MaterializationError, match="non-empty JSON array"):
        module.materialize_capture(bad)


def test_rejects_c2_candidate_not_in_anchor_pool() -> None:
    bad = deepcopy(_payload())
    bad_informed = bad["c2"]["informed"]  # type: ignore[index]
    bad_informed[0]["candidate_action"] = 3
    bad["pool_sha256"] = module.canonical_sha256(module._pool_payload(bad))
    with pytest.raises(module.MaterializationError, match="legal anchor alternative"):
        module.materialize_capture(bad)


def test_rejects_legal_but_unauthenticated_c2_choice_and_rule() -> None:
    bad = deepcopy(_payload())
    row = bad["c2"]["informed"][0]  # type: ignore[index]
    row["candidate_action"] = 2
    row["candidate_physical_key"] = [3000, 3]
    bad["pool_sha256"] = module.canonical_sha256(module._pool_payload(bad))
    with pytest.raises(module.MaterializationError, match="deterministic hold-or-best-rival"):
        module.materialize_capture(bad)

    bad = deepcopy(_payload())
    row = bad["c2"]["informed"][0]  # type: ignore[index]
    row["source_rule"] = "max-lagged-candidate-sinr-rival"
    bad["pool_sha256"] = module.canonical_sha256(module._pool_payload(bad))
    with pytest.raises(module.MaterializationError, match="source rule is not authenticated"):
        module.materialize_capture(bad)


def test_rejects_c2_lineage_and_slot_binding_drift() -> None:
    bad = deepcopy(_payload())
    bad["c2"]["anchors"][0]["checkpoint_sha256"] = "c" * 64  # type: ignore[index]
    bad["pool_sha256"] = module.canonical_sha256(module._pool_payload(bad))
    with pytest.raises(module.MaterializationError, match="checkpoint_sha256 disagrees"):
        module.materialize_capture(bad)


def test_rejects_unreconstructable_c1_anchor_and_c2_policy_or_alias_drift() -> None:
    bad = deepcopy(_payload())
    bad["c1"]["records"][0]["state_sha256"] = "c" * 64  # type: ignore[index]
    bad["pool_sha256"] = module.canonical_sha256(module._pool_payload(bad))
    with pytest.raises(module.MaterializationError, match="C1 authenticated anchor"):
        module.materialize_capture(bad)

    bad = deepcopy(_payload())
    anchor = bad["c2"]["anchors"][0]  # type: ignore[index]
    anchor["horizon_steps"] = module.C2_HORIZON_STEPS + 1
    anchor["anchor_sha256"] = module.c2_anchor_sha256(anchor)
    bad["c2"]["informed"][0]["anchor_sha256"] = anchor["anchor_sha256"]  # type: ignore[index]
    bad["pool_sha256"] = module.canonical_sha256(module._pool_payload(bad))
    with pytest.raises(module.MaterializationError, match="horizon or release grammar"):
        module.materialize_capture(bad)

    bad = deepcopy(_payload())
    anchor = bad["c2"]["anchors"][0]  # type: ignore[index]
    table = anchor["slot_table"]
    table["norad_ids"][3] = table["norad_ids"][1]
    table["cell_ids"][3] = table["cell_ids"][1]
    table["mask"][3] = True
    anchor["anchor_sha256"] = module.c2_anchor_sha256(anchor)
    bad["c2"]["informed"][0]["anchor_sha256"] = anchor["anchor_sha256"]  # type: ignore[index]
    bad["pool_sha256"] = module.canonical_sha256(module._pool_payload(bad))
    with pytest.raises(module.MaterializationError, match="physical alias"):
        module.materialize_capture(bad)

    bad = deepcopy(_payload())
    bad["c2"]["anchors"][0]["slot_table"]["norad_ids"][0] = 9999  # type: ignore[index]
    bad["pool_sha256"] = module.canonical_sha256(module._pool_payload(bad))
    with pytest.raises(module.MaterializationError, match="reference physical key disagrees"):
        module.materialize_capture(bad)


def test_pool_digest_binds_selection_configuration_and_seeds() -> None:
    for route, field in (("c1", "neutral_seed"), ("c2", "neutral_seed")):
        bad = deepcopy(_payload())
        bad[route][field] += 1  # type: ignore[index,operator]
        with pytest.raises(module.MaterializationError, match="pool_sha256 mismatch"):
            module.materialize_capture(bad)
    bad = deepcopy(_payload())
    bad["c1"]["frontier_config"]["lower_anchor_fraction"] = 0.75  # type: ignore[index]
    with pytest.raises(module.MaterializationError, match="pool_sha256 mismatch"):
        module.materialize_capture(bad)


def test_c1_no_op_reference_is_not_rejected_by_json_boundary() -> None:
    payload = deepcopy(_payload())
    for record in payload["c1"]["records"]:  # type: ignore[index]
        record["reference_actions"][0] = -1
        record["slot_tables"][0] = {
            "norad_ids": [-1] * NUM_ACTIONS,
            "cell_ids": [-1] * NUM_ACTIONS,
            "mask": [False] * NUM_ACTIONS,
        }
        record["anchor_sha256"] = module.c1_anchor_sha256(record)
    payload["pool_sha256"] = module.canonical_sha256(module._pool_payload(payload))
    bundle = module.materialize_capture(payload)
    assert bundle.c1_informed.budget > 0


def test_no_runtime_or_training_boundary_is_claimed() -> None:
    bundle = module.materialize_capture(_payload())
    output = Path("/tmp") / "unused-v023-c1c2-materialization-test"
    # The in-memory seam carries no simulator/training side effects; inspect
    # the writer receipt in a pytest temp directory in the writer test above.
    assert bundle.c1_informed.partition == "TRAIN"
    assert "NO_SIMULATOR" in module.CLAIM_CEILING
    assert not output.exists()
