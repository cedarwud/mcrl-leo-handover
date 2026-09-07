"""W-119 -- synthetic prepare/shard/merge integration for V0.7 D2."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path
import sys

import numpy as np

from mcrl.runtime.ee_axis_v07_c2_dataset import (
    V07C2Dataset,
    V07C2DecisionCoverage,
    V07C2Row,
    canonical_json_bytes,
)
from mcrl.runtime.ee_axis_v07_c2_d2 import (
    D2_INVALID_NO_INFERENCE,
    D2_PASS_AUTHORIZE_D3_IMPLEMENTATION,
    D2_SEEDS,
)
from mcrl.runtime.ee_axis_v07_c2_focal_next import focal_next_surplus_target


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / ".scratch" / "c3-v04" / "run_v07_c2_d2.py"
SPEC = importlib.util.spec_from_file_location("v07_c2_d2_runner_w119", RUNNER)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _mask(seed: int, *, late: bool) -> np.ndarray:
    result = np.zeros(28, dtype=np.bool_)
    result[[1, 4, 7, 9, 12] if seed % 2 else [0, 1, 2, 3]] = True
    return result


def _prepare() -> dict[str, object]:
    anchors: list[dict[str, object]] = []
    state = np.zeros(228, dtype=np.float32)
    state_payload = [float(value).hex() for value in state.tolist()]
    state_sha256 = runner._array_sha256(state, dtype=np.dtype(np.float32))
    for seed in D2_SEEDS:
        for window, step in (("early", 1), ("late", 5)):
            mask = _mask(seed, late=window == "late")
            mask_payload = [bool(value) for value in mask.tolist()]
            all_user_masks = np.zeros((2, 28), dtype=np.bool_)
            all_user_masks[0] = mask
            all_user_masks[1, 1] = True
            all_user_masks_payload = all_user_masks.tolist()
            selection = runner._selection_receipt_payload(
                window=window,
                eligible_users_by_step=((step, (0,)),),
            )
            carrier = [[0, 1]]
            carrier_sha256 = hashlib.sha256(canonical_json_bytes(carrier)).hexdigest()
            crn_sha256 = _digest(f"crn:{seed}:{step}")
            digest_payload = {
                "source_seed": seed,
                "window": window,
                "target_step": step,
                "focal_user": 0,
                "focal_mask": mask_payload,
                "all_user_masks": all_user_masks_payload,
                "all_user_masks_sha256": runner._array_sha256(
                    all_user_masks, dtype=np.dtype(np.bool_)
                ),
                "anchor_state": state_payload,
                "anchor_state_sha256": state_sha256,
                "carrier_history": carrier,
                "carrier_history_sha256": carrier_sha256,
                "crn_sha256": crn_sha256,
                "selection_receipt": selection,
            }
            anchors.append(
                digest_payload
                | {
                    "anchor_digest_payload": digest_payload,
                    "anchor_sha256": hashlib.sha256(
                        canonical_json_bytes(digest_payload)
                    ).hexdigest(),
                }
            )
    body: dict[str, object] = {
        "schema": runner.PREPARE_SCHEMA,
        "claim_ceiling": "TARGET_FREE_D2_PREPARE_ONLY",
        "attempt_id": runner.FORMAL_ATTEMPT_ID,
        "attempt_marker_sha256": _digest("prepare-attempt-marker"),
        "d2_prereg_file_sha256": _digest("d2-prereg"),
        "calibration_file_sha256": runner.SEALED_CALIBRATION_FILE_SHA256,
        "calibration_payload_sha256": runner.SEALED_CALIBRATION_PAYLOAD_SHA256,
        "formula_constants": runner._formula_constants(),
        "q2_state_schema": runner.V07_C2_Q2_STATE_SCHEMA,
        "q2_state_schema_sha256": runner.V07_C2_Q2_STATE_SCHEMA_SHA256,
        "source_seeds": list(D2_SEEDS),
        "windows": {key: list(value) for key, value in runner.D2_WINDOWS.items()},
        "anchors": anchors,
        "checkpoint_sha256": _digest("main-checkpoint"),
        "hybrid_sha256_by_lineage": {
            lineage: _digest(f"hybrid:{lineage}")
            for lineage in runner.LINEAGES
        },
        "counterfactual_outcomes_evaluated": False,
        "test_split_opened": False,
        "training": False,
    }
    return body | {
        "prepare_sha256": hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    }


def _measurement(rate: float) -> dict[str, object]:
    actions = np.asarray([0, 1], dtype=np.int64)
    masks = np.zeros((2, 28), dtype=np.bool_)
    masks[0, 0] = True
    masks[1, 1] = True
    return {
        "terminal_absorbing_zero": False,
        "focal_rate_bps": float(rate).hex(),
        "full_power_w": float(10.0).hex(),
        "without_focal_power_w": float(9.0).hex(),
        "successor_actions": actions.tolist(),
        "successor_masks": masks.tolist(),
        "successor_actions_sha256": runner._array_sha256(
            actions, dtype=np.dtype(np.int64)
        ),
        "successor_masks_sha256": runner._array_sha256(
            masks, dtype=np.dtype(np.bool_)
        ),
        "successor_policy_sha256": _digest("successor-policy"),
        "focal_already_noop": False,
    }


def _cell(
    anchor: dict[str, object],
    lineage: str,
    *,
    constant_q: bool,
) -> dict[str, object]:
    mask = np.asarray(anchor["focal_mask"], dtype=np.bool_)
    legal = tuple(int(value) for value in np.flatnonzero(mask))
    reference = legal[0] if constant_q else legal[-1]
    q1 = np.zeros(28, dtype=np.float64) if constant_q else np.arange(28, dtype=np.float64)
    q3 = np.zeros(28, dtype=np.float64)
    q1_payload = [float(value).hex() for value in q1.tolist()]
    q3_payload = [float(value).hex() for value in q3.tolist()]
    q1_sha256 = runner._array_sha256(q1, dtype=np.dtype(np.float64))
    q3_sha256 = runner._array_sha256(q3, dtype=np.dtype(np.float64))
    q1_network_sha256 = _digest(f"q1-network:{lineage}")
    q3_network_sha256 = _digest(f"q3-network:{lineage}")
    policy_sha256 = _digest(f"anchor-policy:{lineage}")
    state = np.zeros(228, dtype=np.float32)
    rows: list[V07C2Row] = []
    branches: list[dict[str, object]] = []
    reference_rate = 100.0
    for position, candidate in enumerate(legal):
        desired = 0.0 if candidate == reference else runner.KAPPA_BITS * (0.10 + 0.03 * position)
        candidate_rate = reference_rate + desired / runner.INTERVAL_S
        target = focal_next_surplus_target(
            lambda_bits_per_j=runner.LAMBDA_BITS_PER_J,
            interval_s=runner.INTERVAL_S,
            candidate_focal_rate_bps=candidate_rate,
            reference_focal_rate_bps=reference_rate,
            candidate_full_power_w=10.0,
            candidate_without_focal_power_w=9.0,
            reference_full_power_w=10.0,
            reference_without_focal_power_w=9.0,
        )
        row = V07C2Row.from_target(
            lineage=lineage,
            refresh_round="bootstrap",
            world_id=anchor["source_seed"],
            step_index=anchor["target_step"],
            focal_user=anchor["focal_user"],
            state=state,
            action_mask=mask,
            reference_action=reference,
            candidate_action=candidate,
            target=target,
        )
        row.verify()
        opening_reference = np.asarray([reference, 1], dtype=np.int64)
        opening_candidate = np.asarray([candidate, 1], dtype=np.int64)
        reference_measurement = _measurement(reference_rate)
        candidate_measurement = (
            reference_measurement
            if candidate == reference
            else _measurement(candidate_rate)
        )
        branches.append(
            {
                "schema": runner.BRANCH_RECEIPT_SCHEMA,
                "candidate_action": candidate,
                "opening_actions": opening_candidate.tolist(),
                "opening_actions_sha256": runner._array_sha256(
                    opening_candidate, dtype=np.dtype(np.int64)
                ),
                "opening_focal_difference_count": 0 if candidate == reference else 1,
                "candidate": candidate_measurement,
                "reference": reference_measurement,
                "target_row_sha256": row.row_sha256,
            }
        )
        rows.append(row)
    coverage = V07C2DecisionCoverage(
        lineage=lineage,
        refresh_round="bootstrap",
        world_id=anchor["source_seed"],
        step_index=anchor["target_step"],
        focal_user=anchor["focal_user"],
        action_mask=mask,
    )
    dataset = V07C2Dataset.from_records(rows=rows, coverage=(coverage,))
    receipt_body: dict[str, object] = {
        "schema": runner.CAPTURE_RECEIPT_SCHEMA,
        "lineage": lineage,
        "refresh_round": "bootstrap",
        "world_id": anchor["source_seed"],
        "source_seed": anchor["source_seed"],
        "target_step": anchor["target_step"],
        "focal_user": anchor["focal_user"],
        "formula_constants": runner._capture_formula_constants(),
        "q2_state_schema": runner.V07_C2_Q2_STATE_SCHEMA,
        "q2_state_schema_sha256": runner.V07_C2_Q2_STATE_SCHEMA_SHA256,
        "crn_sha256": anchor["crn_sha256"],
        "anchor_policy_sha256": policy_sha256,
        "anchor_reference_actions": [reference, 1],
        "anchor_state_sha256": anchor["anchor_state_sha256"],
        "anchor_reference_actions_sha256": runner._array_sha256(
            np.asarray([reference, 1], dtype=np.int64), dtype=np.dtype(np.int64)
        ),
        "native_legal_actions": list(legal),
        "empty_mask": False,
        "q1_focal_surface_hex": q1_payload,
        "q3_focal_surface_hex": q3_payload,
        "q1_focal_surface_array_sha256": q1_sha256,
        "q3_focal_surface_array_sha256": q3_sha256,
        "q1_network_sha256": q1_network_sha256,
        "q3_network_sha256": q3_network_sha256,
        "frozen_network_receipt_complete": True,
        "frozen_network_bytes_unchanged": True,
        "selected_q3_rung": 100,
        "branch_receipt_schema": runner.BRANCH_RECEIPT_SCHEMA,
        "branch_rows": branches,
        "dataset_sha256": dataset.corpus_sha256,
        "resident_legacy_q2_evaluated": False,
        "target_or_ee_selected": False,
        "branch_local_successor_decisions": True,
        "full_evaluation_noncommitting": True,
        "without_focal_evaluation_noncommitting": True,
        "focal_removal_only": True,
        "selection_outcome_blind": True,
        "retry_count": 0,
        "replacement_used": False,
        "test_record_used": False,
    }
    receipt = receipt_body | {
        "receipt_sha256": hashlib.sha256(canonical_json_bytes(receipt_body)).hexdigest()
    }
    return {
        "schema": "multi-catfish-mcrl-v07-c2-d2-lineage-cell-v1",
        "source_seed": anchor["source_seed"],
        "window": anchor["window"],
        "target_step": anchor["target_step"],
        "focal_user": anchor["focal_user"],
        "lineage": lineage,
        "anchor_sha256": anchor["anchor_sha256"],
        "anchor_state_sha256": anchor["anchor_state_sha256"],
        "carrier_history_sha256": anchor["carrier_history_sha256"],
        "crn_sha256": anchor["crn_sha256"],
        "focal_mask": mask.tolist(),
        "all_user_masks_sha256": anchor["all_user_masks_sha256"],
        "anchor_policy_sha256": policy_sha256,
        "anchor_reference_actions": [reference, 1],
        "anchor_reference_actions_sha256": receipt["anchor_reference_actions_sha256"],
        "q1_focal_surface_hex": q1_payload,
        "q3_focal_surface_hex": q3_payload,
        "q1_focal_surface_array_sha256": q1_sha256,
        "q3_focal_surface_array_sha256": q3_sha256,
        "q1_network_sha256": q1_network_sha256,
        "q3_network_sha256": q3_network_sha256,
        "frozen_network_receipt_complete": True,
        "frozen_network_bytes_unchanged": True,
        "selected_q3_rung": 100,
        "branch_rows": branches,
        "capture_receipt": receipt,
        "dataset": dataset.to_document(),
    }


def _shards(
    prepare: dict[str, object],
    *,
    constant_q: bool = False,
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for lineage in runner.LINEAGES:
        cells = [
            _cell(anchor, lineage, constant_q=constant_q)
            for anchor in prepare["anchors"]
        ]
        body: dict[str, object] = {
            "schema": runner.SHARD_SCHEMA,
            "claim_ceiling": "D2_FORMULA_SOURCE_ONLY_NO_LEARNING_NO_EE_EFFICACY",
            "attempt_id": runner.FORMAL_ATTEMPT_ID,
            "attempt_marker_sha256": _digest(f"shard-attempt-marker:{lineage}"),
            "lineage": lineage,
            "prepare_sha256": prepare["prepare_sha256"],
            "formula_constants": runner._formula_constants(),
            "q2_state_schema": runner.V07_C2_Q2_STATE_SCHEMA,
            "q2_state_schema_sha256": runner.V07_C2_Q2_STATE_SCHEMA_SHA256,
            "cells": cells,
            "checkpoint_sha256": prepare["checkpoint_sha256"],
            "lineage_hybrid_sha256": prepare["hybrid_sha256_by_lineage"][lineage],
            "test_split_opened": False,
            "training": False,
        }
        result.append(
            body
            | {"shard_sha256": hashlib.sha256(canonical_json_bytes(body)).hexdigest()}
        )
    return result


def test_prepare_and_three_shards_decode_to_a_d2_pass() -> None:
    prepare = _prepare()
    assert all(
        runner._validate_prepare_anchor(anchor)["selection_receipt"][
            "eligible_users_by_step"
        ][0][1]
        == [0]
        for anchor in prepare["anchors"]
    )
    shards = _shards(prepare)
    captures = runner._decode_d2_shards(prepare=prepare, shards=shards)
    assert len(captures) == 60
    result = runner._adjudication_document(
        prepare=prepare,
        shards=shards,
        attempt_marker_sha256=_digest("adjudication-attempt-marker"),
    )
    assert result["result"]["verdict"] == D2_PASS_AUTHORIZE_D3_IMPLEMENTATION
    assert result["test_split_opened"] is False
    assert result["training"] is False


def test_decoder_surfaces_a_scientific_fail_for_zero_q13_scale() -> None:
    prepare = _prepare()
    result = runner._adjudication_document(
        prepare=prepare,
        shards=_shards(prepare, constant_q=True),
        attempt_marker_sha256=_digest("adjudication-attempt-marker"),
    )
    assert result["result"]["verdict"].endswith("C2_FORMULA_OR_SOURCE_DESIGN")
    assert result["result"]["metrics"]["g_s_zero_denominator_cells"] == 60


def test_merge_rejects_tampered_receipt_and_duplicate_lineage() -> None:
    prepare = _prepare()
    shards = _shards(prepare)
    tampered = copy.deepcopy(shards)
    tampered[0]["cells"][0]["capture_receipt"]["q1_network_sha256"] = _digest("tampered")
    tampered_body = dict(tampered[0])
    tampered_body.pop("shard_sha256")
    tampered[0]["shard_sha256"] = hashlib.sha256(
        canonical_json_bytes(tampered_body)
    ).hexdigest()
    invalid = runner._adjudication_document(
        prepare=prepare,
        shards=tampered,
        attempt_marker_sha256=_digest("adjudication-attempt-marker"),
    )
    assert invalid["result"]["verdict"] == D2_INVALID_NO_INFERENCE

    duplicate = [shards[0], copy.deepcopy(shards[0]), shards[2]]
    duplicate_result = runner._adjudication_document(
        prepare=prepare,
        shards=duplicate,
        attempt_marker_sha256=_digest("adjudication-attempt-marker"),
    )
    assert duplicate_result["result"]["verdict"] == D2_INVALID_NO_INFERENCE
    assert duplicate_result == runner._adjudication_document(
        prepare=prepare,
        shards=tuple(reversed(duplicate)),
        attempt_marker_sha256=_digest("adjudication-attempt-marker"),
    )
