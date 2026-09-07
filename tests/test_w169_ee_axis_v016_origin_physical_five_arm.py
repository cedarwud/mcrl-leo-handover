"""W-169 -- synthetic-only V0.16 B402 physical adapter boundaries."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import torch


REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v016-c3-origin-gate"
    / "run_v016_origin_physical_five_arm.py"
)
SPEC = importlib.util.spec_from_file_location("mcrl_v016_origin_physical_w169", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def _masked_argmax(values: np.ndarray, masks: np.ndarray) -> np.ndarray:
    return np.argmax(np.where(masks, values, -np.inf), axis=1)


def test_b402_config_and_gate_names_are_the_only_accepted_seam() -> None:
    config = runner._expected_q3_config()
    assert config.action_dim == 28
    assert config.local_feature_dim == 14
    assert config.global_feature_dim == 10
    assert config.state_dim == 402
    assert runner.Q3_STATE_DIM == 402
    assert runner.GATE_DECISION == "PASS_ORIGIN_GATE"
    assert runner.GATE_RUNNER_SCHEMA == (
        "multi-catfish-mcrl-v016-c3-origin-learnability-gate-v1"
    )
    assert runner.LINEAGE_BY_INITIALIZATION == {
        2026111101: 2026092101,
        2026111102: 2026092102,
        2026111103: 2026092103,
    }


def test_decoder_uses_one_context_reference_and_one_final_argmax() -> None:
    masks = np.zeros((2, 28), dtype=np.bool_)
    masks[:, :4] = True
    q1 = np.zeros((2, 28), dtype=np.float64)
    q2 = np.zeros_like(q1)
    q1[:, 0] = 2.0
    q1[:, 1] = 1.0
    q2[:, 1] = 2.5
    q2[:, 2] = 1.0
    calls: list[tuple[int, np.ndarray]] = []

    def provider(*, context_code: int, reference_actions: np.ndarray) -> np.ndarray:
        calls.append((context_code, reference_actions.copy()))
        q3 = np.zeros_like(q1)
        q3[:, 3] = 4.0
        return q3

    decoder = runner.V016OriginAnchorDecoder()
    full = decoder.decode(
        arm="FULL", q1_values=q1, q2_values=q2, masks=masks, q3_provider=provider
    )
    assert calls[0][0] == 12
    np.testing.assert_array_equal(
        calls[0][1], _masked_argmax(q1 + q2, masks)
    )
    np.testing.assert_array_equal(
        full.selected_actions, _masked_argmax(q1 + q2 + full.q3_values, masks)
    )
    assert full.q3_evaluated is True

    drop_c1 = decoder.decode(
        arm="DROP_C1", q1_values=q1, q2_values=q2, masks=masks, q3_provider=provider
    )
    assert calls[1][0] == 2
    np.testing.assert_array_equal(calls[1][1], _masked_argmax(q2, masks))
    np.testing.assert_array_equal(
        drop_c1.selected_actions, _masked_argmax(q2 + drop_c1.q3_values, masks)
    )

    drop_c2 = decoder.decode(
        arm="DROP_C2", q1_values=q1, q2_values=q2, masks=masks, q3_provider=provider
    )
    assert calls[2][0] == 1
    np.testing.assert_array_equal(calls[2][1], _masked_argmax(q1, masks))
    np.testing.assert_array_equal(
        drop_c2.selected_actions, _masked_argmax(q1 + drop_c2.q3_values, masks)
    )


def test_drop_c3_never_calls_q3() -> None:
    masks = np.zeros((1, 28), dtype=np.bool_)
    masks[:, :2] = True
    q1 = np.zeros((1, 28), dtype=np.float64)
    q2 = np.zeros_like(q1)
    q1[:, 0] = 1.0
    q2[:, 1] = 2.0

    def forbidden_provider(**_kwargs: object) -> np.ndarray:
        raise AssertionError("DROP_C3 called Q3")

    decoded = runner.V016OriginAnchorDecoder().decode(
        arm="DROP_C3",
        q1_values=q1,
        q2_values=q2,
        masks=masks,
        q3_provider=forbidden_provider,
    )
    assert decoded.q3_evaluated is False
    assert decoded.q3_values is None
    np.testing.assert_array_equal(decoded.selected_actions, np.asarray([1]))


def _write_gate_panel(tmp_path: Path) -> tuple[Path, Path, dict[int, Path]]:
    contract_sha = "a" * 64
    checkpoints: dict[int, Path] = {}
    reports: dict[str, object] = {}
    for seed, lineage in runner.LINEAGE_BY_INITIALIZATION.items():
        learner = runner.EEAxisV015C3PivotalLearner(
            runner._expected_q3_config(), train_seed=seed, device="cpu"
        )
        payload = {
            "schema": runner.GATE_CHECKPOINT_SCHEMA,
            "runner_schema": runner.GATE_RUNNER_SCHEMA,
            "claim_ceiling": runner.GATE_CLAIM_CEILING,
            "contract_sha256": contract_sha,
            "initialization_seed": seed,
            "source_lineage": lineage,
            "update_rung": runner.ORIGIN_GATE_RUNG,
            "q3": learner.checkpoint_state(update_count=runner.ORIGIN_GATE_RUNG),
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "episode_training": False,
        }
        path = tmp_path / f"init-{seed}-rung-003000.pt"
        torch.save(payload, path)
        checkpoints[seed] = path
        reports[str(seed)] = {
            "source_lineage": lineage,
            "rungs": {
                "3000": {
                    "decision": {"passed": True},
                    "checkpoint_sha256": runner.file_sha256(path),
                }
            },
        }
    result = {
        "schema": runner.GATE_RESULT_SCHEMA,
        "decision": runner.GATE_DECISION,
        "passed": True,
        "claim_ceiling": runner.GATE_CLAIM_CEILING,
        "contract_sha256": contract_sha,
        "q3_state_schema": runner.Q3_STATE_SCHEMA,
        "q3_state_dim": runner.Q3_STATE_DIM,
        "source_lineages": list(runner.SOURCE_LINEAGES),
        "initialization_seeds": list(runner.INITIALIZATION_SEEDS),
        "update_rungs": [3, 10, 30, 100, 300, 1000, 3000],
        "next_authority": "AUTHORIZE_100EP_FIVE_ARM_PREREG_ONLY",
        "per_initialization_pass": {
            str(seed): True for seed in runner.INITIALIZATION_SEEDS
        },
        "reports": reports,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(result, sort_keys=True), encoding="ascii")
    receipt = {
        "schema": runner.GATE_RECEIPT_SCHEMA,
        "decision": runner.GATE_DECISION,
        "claim_ceiling": runner.GATE_CLAIM_CEILING,
        "result_sha256": runner.file_sha256(result_path),
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="ascii")
    return result_path, receipt_path, checkpoints


def test_authentication_accepts_only_the_complete_b402_pass_panel(tmp_path: Path) -> None:
    result, receipt, checkpoints = _write_gate_panel(tmp_path)
    selection = runner.authenticate_origin_gate_selection(
        result_path=result,
        receipt_path=receipt,
        expected_result_sha256=runner.file_sha256(result),
        expected_receipt_sha256=runner.file_sha256(receipt),
        checkpoint_paths_by_initialization=checkpoints,
    )
    selection.verify()
    assert set(selection.heads_by_initialization) == set(runner.INITIALIZATION_SEEDS)
    assert all(
        head.q3.config.state_dim == 402
        for head in selection.heads_by_initialization.values()
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("q3_state_dim", 371, "402-D"),
        ("decision", "PASS_REFERENCE_GATE", "PASS_ORIGIN_GATE"),
        ("next_authority", "MAY_PREREGISTER_100_EPISODE_TRAIN_FIVE_ARM", "authorize"),
    ),
)
def test_authentication_rejects_stale_v015_gate_semantics(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    result, receipt, checkpoints = _write_gate_panel(tmp_path)
    payload = json.loads(result.read_text(encoding="ascii"))
    payload[field] = value
    result.write_text(json.dumps(payload, sort_keys=True), encoding="ascii")
    receipt_payload = json.loads(receipt.read_text(encoding="ascii"))
    receipt_payload["result_sha256"] = runner.file_sha256(result)
    if field == "decision":
        receipt_payload["decision"] = value
    receipt.write_text(json.dumps(receipt_payload, sort_keys=True), encoding="ascii")
    with pytest.raises(runner.V016PhysicalRunnerError, match=message):
        runner.authenticate_origin_gate_selection(
            result_path=result,
            receipt_path=receipt,
            expected_result_sha256=runner.file_sha256(result),
            expected_receipt_sha256=runner.file_sha256(receipt),
            checkpoint_paths_by_initialization=checkpoints,
        )
