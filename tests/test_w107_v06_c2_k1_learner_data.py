"""W-107 -- V0.6 C2-k1 source/state join and fixed efficacy gates."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.runtime.ee_axis_state import EE_AXIS_STATE_DIM
from mcrl.runtime.ee_axis_v06_c2_k1_learner import (
    C2K1LearnerDataError,
    DESIGN_EVAL_ROW_SCHEMA,
    G_L_RECEIPT_SCHEMA,
    adjudicate_design_eval,
    build_lineage_batch,
    canonical_sha256,
    compose_actions,
)
from mcrl.runtime.ee_axis_v06_c2_k1_learner_contract_v2 import (
    DESIGN_EVAL_SEEDS,
    KAPPA_BITS,
    LINEAGES,
)
from mcrl.runtime.ee_axis_v06_c2_k1_state_authority import SIDECAR_SCHEMA


def _g_l(*, passed: bool = True) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema": G_L_RECEIPT_SCHEMA,
        "formal_verdict_authenticated": True,
        "verifier_code_authority_authenticated": True,
        "simulator_closure_authenticated": True,
        "single_global_freeze_root": True,
        "source_rows": 1008,
        "rows_per_lineage": {lineage: 336 for lineage in LINEAGES},
        "optimizer_steps_by_lineage": {lineage: 100 for lineage in LINEAGES},
        "checkpoints": [0, 100],
        "update100_reloaded_by_lineage": {lineage: True for lineage in LINEAGES},
        "finite_all_steps": True,
        "q1_q3_byte_identical": True,
        "q1_q3_receive_no_gradient": True,
        "q2_unchanged_during_design_eval": True,
        "design_eval_rows": 60,
        "drop_c2_prepare_cells": 36,
        "resident_legacy_q2_evaluated_or_summed": False,
        "resident_legacy_q2_read_or_copied": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "retry": False,
        "replacement": False,
        "extra_arm": False,
        "passed": passed,
    }
    if not passed:
        receipt["simulator_closure_authenticated"] = False
    return receipt


def _sidecar() -> dict[str, object]:
    anchors = []
    for index in range(12):
        state = np.full(EE_AXIS_STATE_DIM, index / 10.0, dtype=np.float32)
        anchors.append(
            {
                "anchor_key": f"p:{index}:1:0",
                "reference_action": index % 28,
                "state_float32_hex": [float(value).hex() for value in state.tolist()],
                "action_mask": [True] * 28,
            }
        )
    return {"schema": SIDECAR_SCHEMA, "sidecar_sha256": "s" * 64, "anchors": anchors}


def _source() -> dict[str, object]:
    rows = []
    for index in range(12):
        anchor = {"pool": "p", "world_id": index, "step": 1, "focal_user": 0}
        for lineage in LINEAGES:
            for action in range(28):
                rows.append(
                    {
                        "anchor": anchor,
                        "lineage": lineage,
                        "opening_action": action,
                        "reference_action": index % 28,
                        "z2_k1_bits": float(action - index) * 1000.0,
                        "z2_k1_normalized": (
                            float(action - index) * 1000.0 / KAPPA_BITS
                        ),
                        "q2_consulted": False,
                        "sign_filter": False,
                        "policy_sha256": "p" * 64,
                        "crn_sha256": "c" * 64,
                    }
                )
    return {"source_sha256": "t" * 64, "rows": rows}


def test_lineage_join_is_exact_sidecar_order_then_action_order() -> None:
    batch, receipt = build_lineage_batch(
        source=_source(), sidecar=_sidecar(), lineage="q13-b"
    )
    assert batch.states.shape == (336, EE_AXIS_STATE_DIM)
    assert batch.action_masks.shape == (336, 28)
    assert batch.candidate_actions.tolist() == list(range(28)) * 12
    assert np.all(batch.states[:28] == 0.0)
    assert np.all(batch.states[28:56] == np.float32(0.1))
    assert receipt["lineage"] == "q13-b"
    assert receipt["rows"] == 336
    assert receipt["shuffle"] is False


def test_join_rejects_missing_row_or_sign_filtered_source() -> None:
    source = _source()
    source["rows"].pop()
    with pytest.raises(C2K1LearnerDataError, match="12x28"):
        build_lineage_batch(source=source, sidecar=_sidecar(), lineage="q13-c")

    source = _source()
    source["rows"][0]["sign_filter"] = True
    with pytest.raises(C2K1LearnerDataError, match="routing"):
        build_lineage_batch(source=source, sidecar=_sidecar(), lineage="q13-a")

    source = _source()
    source["rows"][0]["z2_k1_normalized"] = 1.0
    with pytest.raises(C2K1LearnerDataError, match="normalized target"):
        build_lineage_batch(source=source, sidecar=_sidecar(), lineage="q13-a")


def test_action_composition_uses_only_explicit_fresh_q2_and_handles_empty_mask() -> None:
    q1 = np.zeros((2, 28), dtype=np.float64)
    q3 = np.zeros((2, 28), dtype=np.float64)
    q1[:, 2] = 1.0
    fresh_q2 = np.zeros((2, 28), dtype=np.float64)
    fresh_q2[:, 5] = 2.0
    masks = np.asarray([[True] * 28, [False] * 28], dtype=np.bool_)
    assert compose_actions(q1=q1, q3=q3, masks=masks, q2=None).tolist() == [2, -1]
    assert compose_actions(q1=q1, q3=q3, masks=masks, q2=fresh_q2).tolist() == [5, -1]


def _eval_rows(*, full_better: bool = True) -> list[dict[str, object]]:
    rows = []
    for seed in DESIGN_EVAL_SEEDS:
        for lineage in LINEAGES:
            for arm in ("FULL", "DROP_C2"):
                full = arm == "FULL"
                bits = 110.0 if full and full_better else 90.0 if full else 100.0
                actions = [[1 if full else 0] * 100 for _ in range(10)]
                row: dict[str, object] = {
                        "schema": DESIGN_EVAL_ROW_SCHEMA,
                        "evaluation_seed": seed,
                        "lineage": lineage,
                        "arm": arm,
                        "steps": 10,
                        "users": 100,
                        "decision_count": 1000,
                        "total_bits": bits,
                        "total_energy_j": 10.0,
                        "served_user_steps": 900,
                        "ratio_of_sums_ee_bits_per_j": bits / 10.0,
                        "fading_field_sha256": "a" * 64,
                        "initial_state_sha256": "b" * 64,
                        "initial_c3_state_sha256": "d" * 64,
                        "initial_mask_sha256": "c" * 64,
                        "actions": actions,
                        "action_trace_sha256": canonical_sha256(actions),
                        "action_flip_count": 1000,
                        "action_flip_rate": 1.0,
                        "q2_surface_median_abs": 1.0 if full else 0.0,
                        "q13_surface_median_abs": 2.0,
                        "q2_to_q13_magnitude": 0.5 if full else 0.0,
                        "complete_28_action_support_fraction": 1.0,
                        "resident_legacy_q2_consulted": False,
                        "route_state_contract": "Q1_Q2_V03__Q3_V04C3",
                        "test_split_opened": False,
                        "episode_training": False,
                    }
                row["row_sha256"] = canonical_sha256(row)
                rows.append(row)
    return rows


def test_fixed_design_eval_gates_pass_only_when_full_improves_ee_and_service() -> None:
    positive = adjudicate_design_eval(
        _eval_rows(full_better=True), g_l_receipt=_g_l()
    )
    assert positive["gates"]["G-L"]["passed"] is True
    assert positive["gates"]["G-E"]["passed"] is True
    assert positive["gates"]["G-S"]["passed"] is True
    assert positive["gates"]["launchable"] is True
    negative = adjudicate_design_eval(
        _eval_rows(full_better=False), g_l_receipt=_g_l()
    )
    assert negative["gates"]["G-E"]["passed"] is False
    assert negative["gates"]["launchable"] is False


def test_design_eval_rejects_unmatched_c3_state_and_drop_q2_forward_receipt() -> None:
    rows = _eval_rows()
    rows[0]["initial_c3_state_sha256"] = "e" * 64
    unsigned = dict(rows[0])
    unsigned.pop("row_sha256")
    rows[0]["row_sha256"] = canonical_sha256(unsigned)
    with pytest.raises(C2K1LearnerDataError, match="initial_c3_state"):
        adjudicate_design_eval(rows, g_l_receipt=_g_l())

    rows = _eval_rows()
    dropped = next(row for row in rows if row["arm"] == "DROP_C2")
    dropped["q2_surface_median_abs"] = 1.0
    dropped["q2_to_q13_magnitude"] = 0.5
    unsigned = dict(dropped)
    unsigned.pop("row_sha256")
    dropped["row_sha256"] = canonical_sha256(unsigned)
    with pytest.raises(C2K1LearnerDataError, match="DROP_C2"):
        adjudicate_design_eval(rows, g_l_receipt=_g_l())


def test_failed_g_l_cannot_authorize_even_when_efficacy_and_service_pass() -> None:
    result = adjudicate_design_eval(
        _eval_rows(full_better=True), g_l_receipt=_g_l(passed=False)
    )
    assert result["gates"]["G-L"]["passed"] is False
    assert result["gates"]["G-E"]["passed"] is True
    assert result["gates"]["G-S"]["passed"] is True
    assert result["gates"]["launchable"] is False
