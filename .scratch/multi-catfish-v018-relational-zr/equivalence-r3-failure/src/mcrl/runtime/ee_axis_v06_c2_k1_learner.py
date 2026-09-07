"""Pure joins, action composition, and gates for the V0.6 C2-k1 screen."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import math
from typing import Any

import numpy as np

from ..algorithms.ee_axis_pairwise import EEAxisPairBatch
from ..env.action_contract import NO_OP_ACTION, NUM_ACTIONS
from .ee_axis_state import EE_AXIS_STATE_DIM
from .ee_axis_v06_c2_k1_learner_contract_v2 import (
    DESIGN_EVAL_SEEDS,
    KAPPA_BITS,
    LINEAGES,
    ROWS_PER_LINEAGE,
    TOTAL_SOURCE_ROWS,
    TRAINING_CHECKPOINTS,
    TRAINING_STEPS,
)
from .ee_axis_v06_c2_k1_state_authority import SIDECAR_SCHEMA


LEARNER_DATA_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-learner-data-v1"
DESIGN_EVAL_ROW_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-design-eval-row-v1"
DESIGN_EVAL_RESULT_SCHEMA = (
    "multi-catfish-mcrl-v06-c2-k1-bounded-learner-result-v1"
)
G_L_RECEIPT_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-g-l-receipt-v1"
_G_L_FIELDS = frozenset(
    {
        "schema",
        "formal_verdict_authenticated",
        "verifier_code_authority_authenticated",
        "simulator_closure_authenticated",
        "single_global_freeze_root",
        "source_rows",
        "rows_per_lineage",
        "optimizer_steps_by_lineage",
        "checkpoints",
        "update100_reloaded_by_lineage",
        "finite_all_steps",
        "q1_q3_byte_identical",
        "q1_q3_receive_no_gradient",
        "q2_unchanged_during_design_eval",
        "design_eval_rows",
        "drop_c2_prepare_cells",
        "resident_legacy_q2_evaluated_or_summed",
        "resident_legacy_q2_read_or_copied",
        "test_split_opened",
        "outcome_selection",
        "retry",
        "replacement",
        "extra_arm",
        "passed",
    }
)
_DESIGN_EVAL_ROW_FIELDS = frozenset(
    {
        "schema",
        "evaluation_seed",
        "lineage",
        "arm",
        "steps",
        "users",
        "decision_count",
        "total_bits",
        "total_energy_j",
        "served_user_steps",
        "ratio_of_sums_ee_bits_per_j",
        "fading_field_sha256",
        "initial_state_sha256",
        "initial_c3_state_sha256",
        "initial_mask_sha256",
        "actions",
        "action_trace_sha256",
        "action_flip_count",
        "action_flip_rate",
        "q2_surface_median_abs",
        "q13_surface_median_abs",
        "q2_to_q13_magnitude",
        "complete_28_action_support_fraction",
        "resident_legacy_q2_consulted",
        "route_state_contract",
        "test_split_opened",
        "episode_training",
        "row_sha256",
    }
)


class C2K1LearnerDataError(ValueError):
    """A source/state join or matched-evaluation result is malformed."""


def canonical_sha256(payload: object) -> str:
    try:
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise C2K1LearnerDataError("payload is not canonical finite JSON") from error
    return hashlib.sha256(raw).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C2K1LearnerDataError(f"{field} is not a lowercase SHA-256")
    return value


def anchor_key(anchor: Mapping[str, Any]) -> str:
    try:
        return (
            f"{anchor['pool']}:{anchor['world_id']}:{anchor['step']}:"
            f"{anchor['focal_user']}"
        )
    except KeyError as error:
        raise C2K1LearnerDataError("source anchor identity is incomplete") from error


def _state_from_hex(values: object) -> np.ndarray:
    if not isinstance(values, list) or len(values) != EE_AXIS_STATE_DIM or any(not isinstance(value, str) for value in values):
        raise C2K1LearnerDataError("sidecar state is not 228 float32 hex values")
    try:
        state = np.asarray([float.fromhex(value) for value in values], dtype=np.float32)
    except (ValueError, OverflowError) as error:
        raise C2K1LearnerDataError("sidecar state contains malformed hex") from error
    if [float(value).hex() for value in state.tolist()] != values or not np.all(np.isfinite(state)):
        raise C2K1LearnerDataError("sidecar state is not canonical finite float32")
    return state


def build_lineage_batch(
    *,
    source: Mapping[str, Any],
    sidecar: Mapping[str, Any],
    lineage: str,
) -> tuple[EEAxisPairBatch, dict[str, Any]]:
    """Join one exact 12x28 lineage to the common opening-state sidecar."""

    if lineage not in LINEAGES:
        raise C2K1LearnerDataError("lineage is not one of the frozen three")
    if sidecar.get("schema") != SIDECAR_SCHEMA:
        raise C2K1LearnerDataError("state sidecar schema is stale")
    side_rows = sidecar.get("anchors")
    if not isinstance(side_rows, list) or len(side_rows) != 12:
        raise C2K1LearnerDataError("state sidecar must contain exactly 12 anchors")
    side_index: dict[str, Mapping[str, Any]] = {}
    for row in side_rows:
        if not isinstance(row, Mapping):
            raise C2K1LearnerDataError("state sidecar anchor is malformed")
        key = row.get("anchor_key")
        if not isinstance(key, str) or key in side_index:
            raise C2K1LearnerDataError("state sidecar anchor key repeats")
        side_index[key] = row
    rows = source.get("rows")
    if not isinstance(rows, list):
        raise C2K1LearnerDataError("T1 source rows are missing")
    source_index: dict[tuple[str, int], Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or row.get("lineage") != lineage:
            continue
        anchor = row.get("anchor")
        if not isinstance(anchor, Mapping):
            raise C2K1LearnerDataError("T1 source row anchor is malformed")
        key = anchor_key(anchor)
        action = row.get("opening_action")
        if type(action) is not int or not 0 <= action < NUM_ACTIONS:
            raise C2K1LearnerDataError("T1 source opening action is malformed")
        identity = (key, action)
        if identity in source_index:
            raise C2K1LearnerDataError("T1 source lineage/action repeats")
        source_index[identity] = row
    expected = {(key, action) for key in side_index for action in range(NUM_ACTIONS)}
    if set(source_index) != expected or len(source_index) != ROWS_PER_LINEAGE:
        raise C2K1LearnerDataError("T1 source lineage is not exact 12x28 coverage")

    states: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    references: list[int] = []
    candidates: list[int] = []
    targets: list[float] = []
    row_authorities: list[str] = []
    for key, side_row in side_index.items():
        state = _state_from_hex(side_row.get("state_float32_hex"))
        mask = np.asarray(side_row.get("action_mask"))
        if mask.shape != (NUM_ACTIONS,) or mask.dtype != np.bool_ or not bool(np.all(mask)):
            raise C2K1LearnerDataError("training sidecar mask is not complete")
        reference = side_row.get("reference_action")
        if type(reference) is not int or not 0 <= reference < NUM_ACTIONS:
            raise C2K1LearnerDataError("sidecar reference action is malformed")
        for action in range(NUM_ACTIONS):
            row = source_index[(key, action)]
            if (
                row.get("reference_action") != reference
                or row.get("opening_action") != action
                or row.get("q2_consulted") is not False
                or row.get("sign_filter") is not False
            ):
                raise C2K1LearnerDataError("T1 training row routing drifted")
            bits = row.get("z2_k1_bits")
            normalized = row.get("z2_k1_normalized")
            if isinstance(bits, bool) or isinstance(normalized, bool):
                raise C2K1LearnerDataError("T1 target is not numeric")
            try:
                target = float(bits)
                normalized_value = float(normalized)
            except (TypeError, ValueError) as error:
                raise C2K1LearnerDataError("T1 target is not numeric") from error
            if not math.isfinite(target) or not math.isfinite(normalized_value):
                raise C2K1LearnerDataError("T1 target is nonfinite")
            tolerance = 1e-12 * max(abs(normalized_value), 1.0)
            if abs(normalized_value - target / KAPPA_BITS) > tolerance:
                raise C2K1LearnerDataError("T1 normalized target disagrees with bits")
            states.append(state)
            masks.append(mask)
            references.append(reference)
            candidates.append(action)
            targets.append(target)
            row_authorities.append(
                canonical_sha256(
                    {
                        "anchor_key": key,
                        "lineage": lineage,
                        "action": action,
                        "target_bits": target,
                        "target_normalized": normalized_value,
                        "policy_sha256": row.get("policy_sha256"),
                        "crn_sha256": row.get("crn_sha256"),
                    }
                )
            )
    batch = EEAxisPairBatch(
        states=np.asarray(states, dtype=np.float32),
        reference_actions=np.asarray(references, dtype=np.int64),
        candidate_actions=np.asarray(candidates, dtype=np.int64),
        target_surplus_bits=np.asarray(targets, dtype=np.float64),
        action_masks=np.asarray(masks, dtype=np.bool_),
    )
    batch.validate(state_dim=EE_AXIS_STATE_DIM, action_dim=NUM_ACTIONS)
    receipt = {
        "schema": LEARNER_DATA_SCHEMA,
        "lineage": lineage,
        "rows": ROWS_PER_LINEAGE,
        "anchors": 12,
        "actions": NUM_ACTIONS,
        "order": "prepare_anchor_order_then_action_0_to_27",
        "source_sha256": source.get("source_sha256"),
        "sidecar_sha256": sidecar.get("sidecar_sha256"),
        "row_authority_sha256": canonical_sha256(row_authorities),
        "sign_filter": False,
        "shuffle": False,
        "training_started": False,
    }
    return batch, receipt | {"batch_receipt_sha256": canonical_sha256(receipt)}


def compose_actions(
    *,
    q1: np.ndarray,
    q3: np.ndarray,
    masks: np.ndarray,
    q2: np.ndarray | None,
) -> np.ndarray:
    """Compose FULL or DROP_C2 without ever importing a resident Q2."""

    first = np.asarray(q1, dtype=np.float64)
    third = np.asarray(q3, dtype=np.float64)
    legal = np.asarray(masks)
    if first.ndim != 2 or first.shape != third.shape:
        raise C2K1LearnerDataError("Q1/Q3 surfaces disagree")
    if legal.shape != first.shape or legal.dtype != np.bool_:
        raise C2K1LearnerDataError("deployment masks disagree with Q surfaces")
    scores = first + third
    if q2 is not None:
        second = np.asarray(q2, dtype=np.float64)
        if second.shape != scores.shape or not np.all(np.isfinite(second)):
            raise C2K1LearnerDataError("fresh Q2 surface is malformed")
        scores = scores + second
    if not np.all(np.isfinite(first + third)):
        raise C2K1LearnerDataError("Q1/Q3 surface is nonfinite")
    actions = np.full(first.shape[0], NO_OP_ACTION, dtype=np.int64)
    eligible = np.any(legal, axis=1)
    if bool(np.any(eligible)):
        actions[eligible] = np.argmax(
            np.where(legal[eligible], scores[eligible], -np.inf), axis=1
        )
    return actions


def _positive_ratio(left_bits: float, left_energy: float, right_bits: float, right_energy: float) -> bool:
    if left_energy <= 0.0 or right_energy <= 0.0:
        raise C2K1LearnerDataError("DESIGN-EVAL energy must be positive")
    return left_bits / left_energy > right_bits / right_energy


def _adjudicate_g_l(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, Mapping) or set(receipt) != _G_L_FIELDS:
        raise C2K1LearnerDataError("G-L receipt fields drifted")
    expected = {
        "schema": G_L_RECEIPT_SCHEMA,
        "formal_verdict_authenticated": True,
        "verifier_code_authority_authenticated": True,
        "simulator_closure_authenticated": True,
        "single_global_freeze_root": True,
        "source_rows": TOTAL_SOURCE_ROWS,
        "rows_per_lineage": {lineage: ROWS_PER_LINEAGE for lineage in LINEAGES},
        "optimizer_steps_by_lineage": {
            lineage: TRAINING_STEPS for lineage in LINEAGES
        },
        "checkpoints": list(TRAINING_CHECKPOINTS),
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
    }
    observed = dict(receipt)
    supplied_pass = observed.pop("passed")
    if type(supplied_pass) is not bool:
        raise C2K1LearnerDataError("G-L passed field is malformed")
    checks = {field: observed.get(field) == value for field, value in expected.items()}
    passed = all(checks.values())
    if supplied_pass is not passed:
        raise C2K1LearnerDataError("G-L passed field disagrees with its receipt")
    return {
        "passed": passed,
        "checks": checks,
        "receipt_sha256": canonical_sha256(dict(receipt)),
    }


def adjudicate_design_eval(
    rows: Sequence[Mapping[str, Any]],
    *,
    g_l_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply explicit G-L/G-E/G-S gates to 60 matched episode rows."""

    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or len(rows) != 60:
        raise C2K1LearnerDataError("DESIGN-EVAL must contain exactly 60 rows")
    g_l = _adjudicate_g_l(g_l_receipt)
    indexed: dict[tuple[int, str, str], Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or row.get("schema") != DESIGN_EVAL_ROW_SCHEMA:
            raise C2K1LearnerDataError("DESIGN-EVAL row schema drifted")
        if set(row) != _DESIGN_EVAL_ROW_FIELDS:
            raise C2K1LearnerDataError("DESIGN-EVAL row fields drifted")
        row_digest = _digest(row.get("row_sha256"), field="DESIGN-EVAL row_sha256")
        unsigned = dict(row)
        unsigned.pop("row_sha256", None)
        if canonical_sha256(unsigned) != row_digest:
            raise C2K1LearnerDataError("DESIGN-EVAL row digest drifted")
        seed, lineage, arm = row.get("evaluation_seed"), row.get("lineage"), row.get("arm")
        if seed not in DESIGN_EVAL_SEEDS or lineage not in LINEAGES or arm not in {"FULL", "DROP_C2"}:
            raise C2K1LearnerDataError("DESIGN-EVAL identity drifted")
        key = (int(seed), str(lineage), str(arm))
        if key in indexed:
            raise C2K1LearnerDataError("DESIGN-EVAL identity repeats")
        if row.get("steps") != 10 or row.get("users") != 100 or row.get("decision_count") != 1000:
            raise C2K1LearnerDataError("DESIGN-EVAL episode dimensions drifted")
        if row.get("test_split_opened") is not False or row.get("episode_training") is not False:
            raise C2K1LearnerDataError("DESIGN-EVAL crossed a forbidden boundary")
        for field in ("total_bits", "total_energy_j"):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) < 0.0:
                raise C2K1LearnerDataError(f"DESIGN-EVAL {field} is malformed")
        if (
            type(row.get("served_user_steps")) is not int
            or not 0 <= int(row["served_user_steps"]) <= 1000
            or float(row["total_energy_j"]) <= 0.0
        ):
            raise C2K1LearnerDataError("DESIGN-EVAL energy/service is malformed")
        ratio = row.get("ratio_of_sums_ee_bits_per_j")
        if (
            isinstance(ratio, bool)
            or not isinstance(ratio, (int, float))
            or not math.isfinite(float(ratio))
            or float(ratio)
            != float(row["total_bits"]) / float(row["total_energy_j"])
        ):
            raise C2K1LearnerDataError("DESIGN-EVAL EE ratio drifted")
        for field in (
            "fading_field_sha256",
            "initial_state_sha256",
            "initial_c3_state_sha256",
            "initial_mask_sha256",
            "action_trace_sha256",
        ):
            _digest(row.get(field), field=f"DESIGN-EVAL {field}")
        actions = row.get("actions")
        if (
            not isinstance(actions, list)
            or len(actions) != 10
            or any(
                not isinstance(step_actions, list)
                or len(step_actions) != 100
                or any(
                    type(action) is not int or not -1 <= action < NUM_ACTIONS
                    for action in step_actions
                )
                for step_actions in actions
            )
            or row.get("action_trace_sha256") != canonical_sha256(actions)
        ):
            raise C2K1LearnerDataError("DESIGN-EVAL action trace drifted")
        flips = row.get("action_flip_count")
        flip_rate = row.get("action_flip_rate")
        if (
            type(flips) is not int
            or not 0 <= flips <= 1000
            or isinstance(flip_rate, bool)
            or not isinstance(flip_rate, (int, float))
            or not math.isfinite(float(flip_rate))
            or float(flip_rate) != flips / 1000
        ):
            raise C2K1LearnerDataError("DESIGN-EVAL action-flip receipt drifted")
        diagnostics: dict[str, float] = {}
        for field in (
            "q2_surface_median_abs",
            "q13_surface_median_abs",
            "q2_to_q13_magnitude",
            "complete_28_action_support_fraction",
        ):
            value = row.get(field)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0.0
            ):
                raise C2K1LearnerDataError(f"DESIGN-EVAL {field} is malformed")
            diagnostics[field] = float(value)
        if diagnostics["complete_28_action_support_fraction"] > 1.0:
            raise C2K1LearnerDataError("DESIGN-EVAL support fraction is malformed")
        expected_magnitude = (
            diagnostics["q2_surface_median_abs"]
            / diagnostics["q13_surface_median_abs"]
            if diagnostics["q13_surface_median_abs"] > 0.0
            else 0.0
        )
        if diagnostics["q2_to_q13_magnitude"] != expected_magnitude:
            raise C2K1LearnerDataError("DESIGN-EVAL Q2/Q13 diagnostic drifted")
        if arm == "DROP_C2" and (
            diagnostics["q2_surface_median_abs"] != 0.0
            or diagnostics["q2_to_q13_magnitude"] != 0.0
        ):
            raise C2K1LearnerDataError("DROP_C2 evaluated a Q2 surface")
        if (
            row.get("resident_legacy_q2_consulted") is not False
            or row.get("route_state_contract") != "Q1_Q2_V03__Q3_V04C3"
        ):
            raise C2K1LearnerDataError("DESIGN-EVAL route-state contract drifted")
        indexed[key] = row
    expected = {
        (seed, lineage, arm)
        for seed in DESIGN_EVAL_SEEDS
        for lineage in LINEAGES
        for arm in ("FULL", "DROP_C2")
    }
    if set(indexed) != expected:
        raise C2K1LearnerDataError("DESIGN-EVAL does not cover the fixed cross-product")
    for seed in DESIGN_EVAL_SEEDS:
        for lineage in LINEAGES:
            full = indexed[(seed, lineage, "FULL")]
            dropped = indexed[(seed, lineage, "DROP_C2")]
            for field in (
                "fading_field_sha256",
                "initial_state_sha256",
                "initial_c3_state_sha256",
                "initial_mask_sha256",
            ):
                if full[field] != dropped[field]:
                    raise C2K1LearnerDataError(
                        f"matched DESIGN-EVAL {field} drifted"
                    )
            full_actions = np.asarray(full["actions"], dtype=np.int64)
            dropped_actions = np.asarray(dropped["actions"], dtype=np.int64)
            flips = int(np.count_nonzero(full_actions != dropped_actions))
            if (
                full["action_flip_count"] != flips
                or dropped["action_flip_count"] != flips
            ):
                raise C2K1LearnerDataError(
                    "matched DESIGN-EVAL action-flip count drifted"
                )

    def totals(keys: Sequence[tuple[int, str, str]]) -> tuple[float, float, int, int]:
        selected = [indexed[key] for key in keys]
        return (
            math.fsum(float(row["total_bits"]) for row in selected),
            math.fsum(float(row["total_energy_j"]) for row in selected),
            sum(int(row["served_user_steps"]) for row in selected),
            sum(int(row["decision_count"]) for row in selected),
        )

    all_full = [(seed, lineage, "FULL") for seed in DESIGN_EVAL_SEEDS for lineage in LINEAGES]
    all_drop = [(seed, lineage, "DROP_C2") for seed in DESIGN_EVAL_SEEDS for lineage in LINEAGES]
    fb, fe, fs, fd = totals(all_full)
    db, de, ds, dd = totals(all_drop)
    pooled_positive = _positive_ratio(fb, fe, db, de)
    lineage_contrasts: dict[str, bool] = {}
    lineage_service: dict[str, bool] = {}
    for lineage in LINEAGES:
        left = totals([(seed, lineage, "FULL") for seed in DESIGN_EVAL_SEEDS])
        right = totals([(seed, lineage, "DROP_C2") for seed in DESIGN_EVAL_SEEDS])
        lineage_contrasts[lineage] = _positive_ratio(left[0], left[1], right[0], right[1])
        lineage_service[lineage] = left[2] / left[3] >= right[2] / right[3]
    world_contrasts: dict[str, bool] = {}
    for seed in DESIGN_EVAL_SEEDS:
        left = totals([(seed, lineage, "FULL") for lineage in LINEAGES])
        right = totals([(seed, lineage, "DROP_C2") for lineage in LINEAGES])
        world_contrasts[str(seed)] = _positive_ratio(left[0], left[1], right[0], right[1])
    pooled_service = fs / fd >= ds / dd
    g_e = pooled_positive and sum(lineage_contrasts.values()) >= 2 and sum(world_contrasts.values()) >= 7
    g_s = pooled_service and sum(lineage_service.values()) >= 2
    result = {
        "schema": DESIGN_EVAL_RESULT_SCHEMA,
        "counts": {"rows": 60, "worlds": 10, "lineages": 3, "arms": 2},
        "pooled": {
            "full_bits": fb,
            "full_energy_j": fe,
            "full_ee_bits_per_j": fb / fe,
            "drop_c2_bits": db,
            "drop_c2_energy_j": de,
            "drop_c2_ee_bits_per_j": db / de,
            "full_gt_drop_c2": pooled_positive,
            "full_served_fraction": fs / fd,
            "drop_c2_served_fraction": ds / dd,
            "service_noninferior": pooled_service,
        },
        "lineage_ee_positive": lineage_contrasts,
        "lineage_service_nonnegative": lineage_service,
        "world_ee_positive": world_contrasts,
        "gates": {
            "G-L": g_l,
            "G-E": {"passed": g_e, "positive_lineages": sum(lineage_contrasts.values()), "positive_worlds": sum(world_contrasts.values())},
            "G-S": {"passed": g_s, "nonnegative_lineages": sum(lineage_service.values())},
            "launchable": g_l["passed"] and g_e and g_s,
        },
        "test_split_opened": False,
        "episode_training": False,
    }
    return result | {"result_sha256": canonical_sha256(result)}


__all__ = [
    "C2K1LearnerDataError",
    "DESIGN_EVAL_RESULT_SCHEMA",
    "DESIGN_EVAL_ROW_SCHEMA",
    "G_L_RECEIPT_SCHEMA",
    "LEARNER_DATA_SCHEMA",
    "adjudicate_design_eval",
    "anchor_key",
    "build_lineage_batch",
    "canonical_sha256",
    "compose_actions",
]
