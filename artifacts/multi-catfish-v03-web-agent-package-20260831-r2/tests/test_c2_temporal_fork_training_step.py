from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


HERE = Path(__file__).resolve().parent
SMC_DIR = HERE.parent / "smc-er-short-ep"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SMC_DIR))
sys.path.insert(0, str(HERE.parents[1] / "src"))

import c2_temporal_fork_joint_transaction as joint  # noqa: E402
import c2_temporal_fork_option_runner as option_runner  # noqa: E402
import c2_temporal_fork_selection as selection  # noqa: E402
import c2_temporal_fork_training_step as step  # noqa: E402
import test_c2_temporal_fork_combined_carrier as combined_test  # noqa: E402
import test_c2_temporal_fork_selection as selection_test  # noqa: E402
import test_c2_temporal_fork_torch_adapter as torch_test  # noqa: E402
import test_c2_temporal_fork_trainer_backend as backend_test  # noqa: E402
from smc_er_core import ConsumedBundleLedger  # noqa: E402
import c2_temporal_fork_torch_adapter as torch_adapter  # noqa: E402


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _k0_choice():
    failed = selection_test._candidate(
        action=3, key=(50001, 1), passed=False
    )
    return selection.select_prepared_fork(
        [failed],
        behavior_rng=__import__("numpy").random.default_rng(601),
        preoutcome_timestamp_ns=601,
    )


def _k1_backend_choice():
    service, wrapped, trainer = backend_test._backend()
    prepared = service.prepare_incumbent_hold(focal_user=0)
    prepared.run_forecast()
    choice = selection.select_prepared_fork(
        [prepared],
        behavior_rng=__import__("numpy").random.default_rng(602),
        preoutcome_timestamp_ns=602,
    )
    return choice, service, wrapped, trainer


def _k1_case():
    choice, service, wrapped, trainer = _k1_backend_choice()
    specialist = torch_test._specialist()
    main = combined_test._main()
    c2_ledger = torch_adapter.C2OptionLedger()
    consumed = ConsumedBundleLedger()
    transaction_ledger = joint.JointOptionLedger()
    return (
        choice,
        service,
        wrapped,
        trainer,
        specialist,
        main,
        c2_ledger,
        consumed,
        transaction_ledger,
    )


def _fake_joint_commit(calls: dict[str, int]):
    def run(
        specialist,
        transition,
        main,
        sequence,
        *,
        beta,
        c2_option_ledger,
        transaction_ledger,
        consumer_block_id,
        source_block_id,
        source_policy_version,
        consumed_ledger,
        c1_bundle,
        c3_bundle,
    ):
        del main, beta, c2_option_ledger, consumed_ledger, c1_bundle, c3_bundle
        calls["joint"] += 1
        selection_digest = sequence.selection_receipt_sha256
        record = joint.JointOptionRecord.create(
            option_id=sequence.option_id,
            source_unit_id=sequence.source_unit_id,
            transition_sha256=transition.sequence_sha256,
            primitive_sequence_sha256=sequence.sequence_sha256,
            selection_receipt_sha256=selection_digest,
            constituent_bundle_ids=sequence.constituent_bundle_ids,
            source_block_id=source_block_id,
            source_policy_version=source_policy_version,
            consumer_block_id=consumer_block_id,
            q2f_receipt_sha256=_digest("q2f-receipt"),
            main_receipt_sha256=_digest("main-receipt"),
        )
        transaction_ledger.commit(record)
        return SimpleNamespace(
            selection_receipt_sha256=selection_digest,
            warmup=False,
            updated=True,
            committed=True,
            q2f_receipt_sha256=record.q2f_receipt_sha256,
            main_receipt_sha256=record.main_receipt_sha256,
            record_sha256=record.record_sha256,
        )

    return run


def test_k0_main_fallback_makes_no_runner_or_joint_call():
    choice = _k0_choice()
    calls = {"runner": 0, "joint": 0}

    def forbidden(*_args, **_kwargs):
        calls["runner"] += 1
        raise AssertionError("K0 must not call a live runner")

    receipt = step.run_c2_training_step(
        choice,
        specialist=None,
        main=None,
        beta=0.5,
        discount_factor=0.9,
        block_id=0,
        c2_option_ledger=None,
        transaction_ledger=None,
        runner_fn=forbidden,
        joint_fn=forbidden,
    )
    assert receipt.choice_class == step.CHOICE_CLASS_K0
    assert receipt.choice_mode == selection.CHOICE_MODE_FALLBACK
    assert receipt.live_committed is False
    assert receipt.updated is False
    assert calls == {"runner": 0, "joint": 0}


def test_k1_uses_exact_forced_probability_and_current_source_policy():
    (
        choice,
        _service,
        _wrapped,
        _trainer,
        specialist,
        main,
        c2_ledger,
        consumed,
        transaction_ledger,
    ) = _k1_case()
    calls = {"runner": 0, "joint": 0}
    captured = {}
    real_runner = option_runner.commit_prepared_option

    def runner(prepared, **kwargs):
        calls["runner"] += 1
        captured.update(kwargs)
        return real_runner(prepared, **kwargs)

    receipt = step.run_c2_training_step(
        choice,
        specialist=specialist,
        main=main,
        beta=0.5,
        discount_factor=0.9,
        block_id=7,
        c2_option_ledger=c2_ledger,
        transaction_ledger=transaction_ledger,
        consumed_ledger=consumed,
        runner_fn=runner,
        joint_fn=_fake_joint_commit(calls),
    )
    assert receipt.choice_class == step.CHOICE_CLASS_K1
    assert receipt.choice_mode == selection.CHOICE_MODE_FORCED
    assert receipt.behavior_probability == 1.0
    assert receipt.q2f_policy_version is None
    assert receipt.source_policy_version == specialist.policy_version
    assert captured["opening_behavior_probability"] == 1.0
    assert captured["selection_receipt_sha256"] == choice.receipt.receipt_sha256
    assert captured["source_policy_version"] == specialist.policy_version
    assert captured["block_id"] == 7
    assert calls == {"runner": 1, "joint": 1}
    assert receipt.selection_receipt_sha256 == choice.receipt.receipt_sha256
    assert receipt.joint_record_sha256


def test_production_runner_rejects_forecast_main_identity_mismatch_pre_live():
    (
        choice,
        _service,
        _wrapped,
        _forecast_trainer,
        specialist,
        main,
        c2_ledger,
        consumed,
        transaction_ledger,
    ) = _k1_case()

    with pytest.raises(step.C2TrainingStepError, match="trainer identity mismatch"):
        step.run_c2_training_step(
            choice,
            specialist=specialist,
            main=main,
            beta=0.5,
            discount_factor=0.9,
            block_id=7,
            c2_option_ledger=c2_ledger,
            transaction_ledger=transaction_ledger,
            consumed_ledger=consumed,
            joint_fn=lambda *_args, **_kwargs: pytest.fail(
                "identity mismatch must fail before the joint transaction"
            ),
        )
    assert choice.selected_prepared_fork.phase == "forecast_complete"


def _learned_choice():
    left = selection_test._candidate(action=3, key=(50001, 1))
    right = selection_test._candidate(action=4, key=(50001, 2))
    q2f = selection_test.FakeQ2F({3: 9.0, 4: 1.0})
    return selection.select_prepared_fork(
        [left, right],
        q2f=q2f,
        behavior_rng=__import__("numpy").random.default_rng(603),
        epsilon=0.2,
        preoutcome_timestamp_ns=603,
    )


@pytest.mark.parametrize("drift", ["policy", "network"])
def test_k_ge_2_learned_choice_rejects_policy_or_network_drift_pre_live(
    monkeypatch, drift
):
    choice = _learned_choice()
    specialist = torch_test._specialist()
    main = combined_test._main()
    c2_ledger = torch_adapter.C2OptionLedger()
    transaction_ledger = joint.JointOptionLedger()
    if drift == "network":
        specialist.policy_version = choice.receipt.q2f_policy_version
        monkeypatch.setattr(
            selection,
            "_network_state_hash",
            lambda _specialist: _digest("drifted-network"),
        )
    calls = {"runner": 0}

    def forbidden(*_args, **_kwargs):
        calls["runner"] += 1
        raise AssertionError("policy/hash drift must fail before live")

    with pytest.raises(step.C2TrainingStepError, match="drifted"):
        step.run_c2_training_step(
            choice,
            specialist=specialist,
            main=main,
            beta=0.5,
            discount_factor=0.9,
            block_id=0,
            c2_option_ledger=c2_ledger,
            transaction_ledger=transaction_ledger,
            runner_fn=forbidden,
            joint_fn=forbidden,
        )
    assert calls["runner"] == 0


def test_admitted_selection_digest_is_propagated_and_joint_called_exactly_once():
    (
        choice,
        _service,
        _wrapped,
        _trainer,
        specialist,
        main,
        c2_ledger,
        consumed,
        transaction_ledger,
    ) = _k1_case()
    calls = {"runner": 0, "joint": 0}
    real_runner = option_runner.commit_prepared_option

    def runner(prepared, **kwargs):
        calls["runner"] += 1
        return real_runner(prepared, **kwargs)

    result = step.run_c2_training_step(
        choice,
        specialist=specialist,
        main=main,
        beta=0.5,
        discount_factor=0.9,
        block_id=8,
        c2_option_ledger=c2_ledger,
        transaction_ledger=transaction_ledger,
        consumed_ledger=consumed,
        runner_fn=runner,
        joint_fn=_fake_joint_commit(calls),
    )
    record = transaction_ledger.state_dict()["records"][0]
    assert calls == {"runner": 1, "joint": 1}
    assert result.selection_receipt_sha256 == choice.receipt.receipt_sha256
    assert record["selection_receipt_sha256"] == choice.receipt.receipt_sha256
    assert result.transition_sha256
    assert result.primitive_sequence_sha256


def test_joint_warmup_keeps_live_receipt_but_requires_no_durable_record():
    (
        choice,
        _service,
        _wrapped,
        _trainer,
        specialist,
        main,
        c2_ledger,
        consumed,
        transaction_ledger,
    ) = _k1_case()
    real_runner = option_runner.commit_prepared_option

    def warmup_joint(_specialist, transition, _main, sequence, **_kwargs):
        return SimpleNamespace(
            selection_receipt_sha256=sequence.selection_receipt_sha256,
            warmup=True,
            updated=False,
            committed=False,
            q2f_receipt_sha256=None,
            main_receipt_sha256=None,
            record_sha256=None,
        )

    result = step.run_c2_training_step(
        choice,
        specialist=specialist,
        main=main,
        beta=0.5,
        discount_factor=0.9,
        block_id=9,
        c2_option_ledger=c2_ledger,
        transaction_ledger=transaction_ledger,
        consumed_ledger=consumed,
        runner_fn=real_runner,
        joint_fn=warmup_joint,
    )

    assert result.live_committed and result.admitted
    assert result.warmup and not result.updated and not result.joint_committed
    assert len(transaction_ledger) == 0


def test_candidate_expiry_without_admitted_suffix_is_reported_without_learning():
    choice, *_ = _k1_case()
    specialist = torch_test._specialist()
    main = combined_test._main()
    result = step.run_c2_training_step(
        choice,
        specialist=specialist,
        main=main,
        beta=0.5,
        discount_factor=0.9,
        block_id=0,
        c2_option_ledger=torch_adapter.C2OptionLedger(),
        transaction_ledger=joint.JointOptionLedger(),
        runner_fn=lambda *_args, **_kwargs: SimpleNamespace(
            transition=None,
            sequence=None,
            termination_reason="candidate_physical_expired_at_offset_1",
        ),
        joint_fn=lambda *_args, **_kwargs: pytest.fail(
            "a non-admitted expiry prefix must not call joint transaction"
        ),
    )
    assert result.live_committed
    assert not result.admitted
    assert result.termination_reason == "candidate_physical_expired_at_offset_1"


@pytest.mark.parametrize("boundary", ["runner", "joint"])
def test_runner_or_joint_failures_propagate(monkeypatch, boundary):
    (
        choice,
        _service,
        _wrapped,
        _trainer,
        specialist,
        main,
        c2_ledger,
        consumed,
        transaction_ledger,
    ) = _k1_case()
    if boundary == "runner":
        def fail_runner(*_args, **_kwargs):
            raise RuntimeError("synthetic runner failure")

        runner_fn = fail_runner
        joint_fn = lambda *_args, **_kwargs: pytest.fail("joint must not run")
        expected = "synthetic runner failure"
    else:
        real_runner = option_runner.commit_prepared_option

        def runner_fn(prepared, **kwargs):
            return real_runner(prepared, **kwargs)

        def fail_joint(*_args, **_kwargs):
            raise RuntimeError("synthetic joint failure")

        joint_fn = fail_joint
        expected = "synthetic joint failure"
    with pytest.raises(RuntimeError, match=expected):
        step.run_c2_training_step(
            choice,
            specialist=specialist,
            main=main,
            beta=0.5,
            discount_factor=0.9,
            block_id=0,
            c2_option_ledger=c2_ledger,
            transaction_ledger=transaction_ledger,
            consumed_ledger=consumed,
            runner_fn=runner_fn,
            joint_fn=joint_fn,
        )
