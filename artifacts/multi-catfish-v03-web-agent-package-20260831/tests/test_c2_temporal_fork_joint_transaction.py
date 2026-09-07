"""Contract tests for the append-only C2 Q2F/Main transaction seam."""

from __future__ import annotations

import copy
from pathlib import Path
import sys

import numpy as np
import pytest
import torch


HERE = Path(__file__).resolve().parent
SMC_DIR = HERE.parent / "smc-er-short-ep"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SMC_DIR))
sys.path.insert(0, str(HERE.parents[1] / "src"))

import c2_temporal_fork_joint_transaction as J  # noqa: E402
import c2_temporal_fork_torch_adapter as A  # noqa: E402
import smc_er_core  # noqa: E402
import test_c2_temporal_fork_combined_carrier as combined_test  # noqa: E402
import test_c2_temporal_fork_torch_adapter as torch_test  # noqa: E402


def _case(*, replay: bool = True):
    main = combined_test._main()
    if replay:
        combined_test._populate_replay(main)
    _certificate, _plan, _steps, _bundles, transition, sequence = (
        torch_test._admitted_items()
    )
    specialist = torch_test._specialist()
    c1 = combined_test._bundle("C1", "joint-c1")
    c3 = combined_test._bundle("C3", "joint-c3", focal=0)
    consumed = smc_er_core.ConsumedBundleLedger()
    c2_ledger = A.C2OptionLedger()
    transaction_ledger = J.JointOptionLedger()
    return (
        specialist,
        transition,
        main,
        sequence,
        c1,
        c3,
        consumed,
        c2_ledger,
        transaction_ledger,
    )


def _deep_equal(left: object, right: object) -> bool:
    if isinstance(left, torch.Tensor) or isinstance(right, torch.Tensor):
        return isinstance(left, torch.Tensor) and isinstance(right, torch.Tensor) and torch.equal(left, right)
    if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
        return isinstance(left, np.ndarray) and isinstance(right, np.ndarray) and np.array_equal(left, right)
    if isinstance(left, dict) or isinstance(right, dict):
        return (
            isinstance(left, dict)
            and isinstance(right, dict)
            and left.keys() == right.keys()
            and all(_deep_equal(left[key], right[key]) for key in left)
        )
    if isinstance(left, (list, tuple)) or isinstance(right, (list, tuple)):
        return (
            type(left) is type(right)
            and len(left) == len(right)
            and all(_deep_equal(a, b) for a, b in zip(left, right, strict=True))
        )
    return left == right


def _snapshot(case):
    specialist, _transition, main, _sequence, _c1, _c3, consumed, c2, joint = case
    return {
        "specialist": copy.deepcopy(specialist.state_dict()),
        "main_q": tuple(copy.deepcopy(net.state_dict()) for net in main.q_nets),
        "main_target": tuple(copy.deepcopy(net.state_dict()) for net in main.target_nets),
        "main_optimizers": tuple(
            copy.deepcopy(optimizer.state_dict()) for optimizer in main.optimizers
        ),
        "main_train_rng": copy.deepcopy(main._train_rng.bit_generator.state),
        "main_env_rng": copy.deepcopy(main._env_rng.bit_generator.state),
        "main_mobility_rng": copy.deepcopy(main._mobility_rng.bit_generator.state),
        "consumed": copy.deepcopy(consumed.state_dict()),
        "c2": copy.deepcopy(c2.state_dict()),
        "joint": copy.deepcopy(joint.state_dict()),
        "global_np": copy.deepcopy(np.random.get_state()),
        "global_torch": torch.get_rng_state().clone(),
    }


def _assert_snapshot(case, before) -> None:
    after = _snapshot(case)
    assert _deep_equal(after, before)


def _run(case, *, transaction_ledger=None, **kwargs):
    specialist, transition, main, sequence, c1, c3, consumed, c2, joint = case
    consumer_block_id = kwargs.pop("consumer_block_id", 0)
    return J.update_c2_joint_transaction(
        specialist,
        transition,
        main,
        sequence,
        beta=0.5,
        c2_option_ledger=c2,
        transaction_ledger=joint if transaction_ledger is None else transaction_ledger,
        consumer_block_id=consumer_block_id,
        consumed_ledger=consumed,
        c1_bundle=c1,
        c3_bundle=c3,
        **kwargs,
    )


def test_success_is_exactly_one_q2f_one_combined_main_and_one_joint_commit():
    case = _case()
    specialist, _transition, main, sequence, _c1, _c3, consumed, c2, joint = case
    receipt = _run(case)

    assert receipt.mode == "q2f_once_plus_combined_main_once"
    assert receipt.updated and not receipt.warmup and receipt.committed
    assert receipt.option_id == sequence.option_id
    assert receipt.source_unit_id == sequence.source_unit_id
    assert receipt.transition_sha256 == case[1].sequence_sha256
    assert receipt.primitive_sequence_sha256 == sequence.sequence_sha256
    assert receipt.constituent_bundle_ids == sequence.constituent_bundle_ids
    assert receipt.source_block_id == 0
    assert receipt.source_policy_version == 1
    assert receipt.consumer_block_id == 0
    assert receipt.policy_version == J.JOINT_POLICY_VERSION
    assert receipt.q2f_receipt_sha256
    assert receipt.main_receipt_sha256
    assert receipt.record_sha256
    assert receipt.q2f_receipt.optimizer_steps == 1
    assert receipt.main_receipt.optimizer_steps_per_objective == (1, 1, 1)
    assert specialist.updates == 1
    assert len(consumed) == 2
    assert len(c2) == 1
    assert len(joint) == 1
    record = joint.state_dict()["records"][0]
    assert record["record_sha256"] == receipt.record_sha256
    assert record["q2f_receipt_sha256"] == receipt.q2f_receipt_sha256
    assert record["main_receipt_sha256"] == receipt.main_receipt_sha256


def test_duplicate_preflight_has_no_mutation_or_rng_advance():
    case = _case()
    _run(case)
    before = _snapshot(case)
    with pytest.raises(J.JointTransactionContractError, match="already consumed"):
        _run(case)
    _assert_snapshot(case, before)


def test_warmup_updates_neither_q2f_nor_main_and_burns_no_ledgers():
    case = _case(replay=False)
    before = _snapshot(case)
    receipt = _run(case)
    assert receipt.mode == "warmup_no_update"
    assert receipt.warmup and not receipt.updated and not receipt.committed
    assert receipt.q2f_receipt is None and receipt.main_receipt is None
    assert case[0].updates == 0
    _assert_snapshot(case, before)


def test_q2f_failure_rolls_back_everything(monkeypatch):
    case = _case()
    before = _snapshot(case)

    def fail_q2f(specialist, transition):
        with torch.no_grad():
            next(specialist.online.parameters()).add_(123.0)
        specialist.updates += 17
        specialist.rng.random()
        case[2]._train_rng.random()
        raise RuntimeError("synthetic Q2F failure")

    monkeypatch.setattr(J.torch_adapter, "update_q2f_smdp", fail_q2f)
    with pytest.raises(RuntimeError, match="synthetic Q2F failure"):
        _run(case)
    _assert_snapshot(case, before)


@pytest.mark.parametrize("objective", [1, 2])
def test_main_second_or_third_head_failure_rolls_back_q2f_main_rng_and_ledgers(
    monkeypatch, objective
):
    case = _case()
    before = _snapshot(case)
    main = case[2]

    def fail_main_head(*_args, **_kwargs):
        with torch.no_grad():
            next(main.q_nets[objective].parameters()).add_(321.0)
        main._train_rng.random()
        raise RuntimeError(f"synthetic Main head {objective} failure")

    monkeypatch.setattr(main.optimizers[objective], "step", fail_main_head)
    with pytest.raises(RuntimeError, match=f"synthetic Main head {objective} failure"):
        _run(case)
    _assert_snapshot(case, before)


class _FailingCommitLedger(J.JointOptionLedger):
    def commit(self, record):
        self._records[record.option_id] = record
        self._seen_bundle_ids.update(record.constituent_bundle_ids)
        raise RuntimeError("synthetic final joint commit failure")


def test_final_joint_commit_failure_rolls_back_q2f_main_and_all_ledgers():
    case = _case()
    failing = _FailingCommitLedger()
    case = (*case[:-1], failing)
    before = _snapshot(case)
    with pytest.raises(RuntimeError, match="synthetic final joint commit failure"):
        _run(case, transaction_ledger=failing)
    _assert_snapshot(case, before)


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        ({"source_block_id": 9}, "source_block_id"),
        ({"source_policy_version": 9}, "source_policy_version"),
        ({"consumer_block_id": 1}, "source age"),
    ],
)
def test_tampered_source_or_consumer_metadata_is_rejected_before_q2f(
    metadata, message
):
    case = _case()
    before = _snapshot(case)
    with pytest.raises(J.JointTransactionContractError, match=message):
        _run(case, **metadata)
    _assert_snapshot(case, before)


def test_record_hash_binds_all_cross_adapter_identity_fields():
    case = _case()
    receipt = _run(case)
    record = case[-1].state_dict()["records"][0]
    for field in (
        "option_id",
        "source_unit_id",
        "transition_sha256",
        "primitive_sequence_sha256",
        "constituent_bundle_ids",
        "source_block_id",
        "source_policy_version",
        "consumer_block_id",
        "q2f_receipt_sha256",
        "main_receipt_sha256",
        "policy_version",
    ):
        assert field in record
    assert record["record_sha256"] == receipt.record_sha256

    tampered = dict(record)
    tampered["consumer_block_id"] = 999
    with pytest.raises(JointRecordError):
        _load_single_record(tampered)


class JointRecordError(Exception):
    """Local marker used to keep the tamper test independent of ledger state."""


def _load_single_record(raw):
    try:
        return J.JointOptionRecord(**raw)
    except J.JointTransactionContractError as error:
        raise JointRecordError from error
