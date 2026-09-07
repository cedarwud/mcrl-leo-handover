"""W-104 -- target-free V0.6 C2-k1 learner preparation seam."""

from __future__ import annotations

import copy
import hashlib
import json

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.ee_axis_state import EE_AXIS_STATE_DIM
from mcrl.runtime.ee_axis_v06_c2_k1 import (
    POLICY_RULE,
    SCHEMA as V06_SCHEMA,
    SOURCE_RULE as V06_SOURCE_RULE,
)
from mcrl.runtime.ee_axis_v06_c2_k1_learner_prep import (
    C2K1LearnerPreparationError,
    FORMAL_LEARNER_VERDICT,
    LEARNER_PLAN_SCHEMA,
    LEARNER_SCOPE,
    PREPARE_LIVE_SCHEMA,
    STATE_SIDECAR_SCHEMA,
    build_state_sidecar,
    check_postgate_learner_plan,
    verify_state_sidecar,
)


def _sha(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _prepare() -> dict[str, object]:
    files = {"runner": _digest("runner"), "runtime": _digest("runtime")}
    anchors: list[dict[str, object]] = []
    for pool, start, step in (
        ("early", 2026101001, 1),
        ("mid", 2026101011, 3),
        ("late", 2026101021, 5),
    ):
        for world in range(start, start + 4):
            anchors.append(
                {
                    "pool": pool,
                    "world_id": world,
                    "step": step,
                    "focal_user": 0,
                    "reference_action": 2,
                    "world_anchor_sha256": _digest(f"world-{world}"),
                    "anchor_sha256": _digest(f"anchor-{world}"),
                    "checkpoint_sha256": _digest("checkpoint"),
                    "simulator_source_manifest_sha256": _digest("simulator"),
                    "policy_sha256": _digest(f"policy-{world}"),
                    "evaluation_seed": world,
                    "legal_action_mask": [True] * NUM_ACTIONS,
                }
            )
    body: dict[str, object] = {
        "schema": PREPARE_LIVE_SCHEMA,
        "algorithm_schema": V06_SCHEMA,
        "source_rule": V06_SOURCE_RULE,
        "policy_rule": POLICY_RULE,
        "simulator_source_manifest_sha256": _digest("simulator"),
        "q13_gate_source_manifest_sha256": _digest("q13"),
        "simulator_prereg_file_sha256": _digest("simulator-prereg"),
        "t1_prereg_file_sha256": _digest("t1-prereg"),
        "code_authority": {"files": files, "sha256": _sha(files)},
        "source_authority": {"scanner": "synthetic", "field": "synthetic"},
        "anchors": anchors,
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
        "prepared_before_generation": True,
    }
    return body | {"prepare_sha256": _sha(body)}


def _states(prepare: dict[str, object]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for index, anchor in enumerate(prepare["anchors"]):  # type: ignore[index]
        key = (
            f"{anchor['pool']}:{anchor['world_id']}:{anchor['step']}:{anchor['focal_user']}"
        )
        result[key] = {
            "state": np.arange(EE_AXIS_STATE_DIM, dtype=np.float32) + index,
            "action_mask": np.ones(NUM_ACTIONS, dtype=np.bool_),
        }
    return result


def _reseal(payload: dict[str, object]) -> dict[str, object]:
    body = dict(payload)
    body.pop("sidecar_sha256", None)
    return body | {"sidecar_sha256": _sha(body)}


def test_build_and_verify_sidecar_has_exact_12_worlds_and_28_actions() -> None:
    prepare = _prepare()
    sidecar = build_state_sidecar(prepare, _states(prepare))

    assert sidecar["schema"] == STATE_SIDECAR_SCHEMA
    assert sidecar["counts"] == {
        "worlds": 12,
        "anchors": 12,
        "actions_per_anchor": NUM_ACTIONS,
        "rows": 12 * NUM_ACTIONS,
    }
    assert len(sidecar["rows"]) == 12 * NUM_ACTIONS  # type: ignore[arg-type]
    assert verify_state_sidecar(sidecar, prepare=prepare) == sidecar["sidecar_sha256"]
    assert all(
        "target_surplus_bits" not in row and "z2_k1_bits" not in row
        for row in sidecar["rows"]  # type: ignore[union-attr]
    )


@pytest.mark.parametrize(
    "mutation, pattern",
    [
        ("state_shape", r"shape \(228,\)"),
        ("state_nan", "finite"),
        ("mask", "action_mask"),
        ("anchor", "anchor digest"),
        ("provenance", "provenance digest"),
        ("world_coverage", "unknown anchor"),
    ],
)
def test_sidecar_verifier_fails_closed_on_state_lineage_or_coverage(
    mutation: str, pattern: str
) -> None:
    prepare = _prepare()
    sidecar = build_state_sidecar(prepare, _states(prepare))
    tampered = copy.deepcopy(sidecar)
    row = tampered["rows"][0]  # type: ignore[index]
    if mutation == "state_shape":
        row["state"] = row["state"][:-1]
    elif mutation == "state_nan":
        # Finite JSON input that overflows the required float32 encoding.
        row["state"][0] = 1e39
    elif mutation == "mask":
        row["action_mask"][0] = False
    elif mutation == "anchor":
        row["anchor_sha256"] = _digest("different-anchor")
    elif mutation == "provenance":
        row["provenance_sha256"] = _digest("different-provenance")
    elif mutation == "world_coverage":
        row["anchor_key"] = "early:2026101001:1:99"
    else:  # pragma: no cover - protects the test itself
        raise AssertionError(mutation)
    with pytest.raises(C2K1LearnerPreparationError, match=pattern):
        verify_state_sidecar(_reseal(tampered), prepare=prepare)


def test_sidecar_rejects_target_or_outcome_fields() -> None:
    prepare = _prepare()
    sidecar = build_state_sidecar(prepare, _states(prepare))

    top_level = copy.deepcopy(sidecar)
    top_level["z2_k1_bits"] = []
    with pytest.raises(C2K1LearnerPreparationError, match="target/outcome"):
        verify_state_sidecar(top_level, prepare=prepare)

    row_level = copy.deepcopy(sidecar)
    row_level["rows"][0]["target_surplus_bits"] = 0.0  # type: ignore[index]
    with pytest.raises(C2K1LearnerPreparationError, match="target/outcome"):
        verify_state_sidecar(_reseal(row_level), prepare=prepare)


def test_state_sidecar_rejects_prepare_authority_drift() -> None:
    prepare = _prepare()
    sidecar = build_state_sidecar(prepare, _states(prepare))
    drifted = copy.deepcopy(prepare)
    drifted["t1_prereg_file_sha256"] = _digest("different-prereg")
    drifted_body = dict(drifted)
    drifted_body.pop("prepare_sha256", None)
    drifted["prepare_sha256"] = _sha(drifted_body)
    with pytest.raises(C2K1LearnerPreparationError, match="PREPARE"):
        verify_state_sidecar(sidecar, prepare=drifted)


def _plan() -> dict[str, object]:
    return {
        "schema": LEARNER_PLAN_SCHEMA,
        "formal_verdict": FORMAL_LEARNER_VERDICT,
        "scope": LEARNER_SCOPE,
        "q1_q3_frozen": True,
        "q2_only_updates": True,
        "source_sidecar_schema": STATE_SIDECAR_SCHEMA,
        "fresh_heldout_evaluation_required": True,
        "test_split_opened": False,
        "training_started": False,
        "hyperparameters_bound": False,
        "no_9000ep": True,
    }


def test_postgate_plan_requires_exact_verdict_and_does_not_launch_training() -> None:
    plan = _plan()
    with pytest.raises(C2K1LearnerPreparationError, match="exact formal verdict"):
        check_postgate_learner_plan(plan, formal_verdict="PASS")

    receipt = check_postgate_learner_plan(
        plan,
        formal_verdict=FORMAL_LEARNER_VERDICT,
    )
    assert receipt["accepted"] is True
    assert receipt["training_started"] is False
    assert receipt["hyperparameters_bound"] is False


def test_postgate_plan_rejects_unfrozen_hyperparameters() -> None:
    plan = _plan()
    plan["learning_rate"] = 0.001
    with pytest.raises(C2K1LearnerPreparationError, match="uncontracted"):
        check_postgate_learner_plan(
            plan,
            formal_verdict=FORMAL_LEARNER_VERDICT,
        )
