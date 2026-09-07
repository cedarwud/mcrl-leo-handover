"""Formal C2 V0.3 training-step orchestration seam.

This module is the first caller allowed to connect the pre-outcome selection,
the real option runner, and the Q2F/Main joint transaction.  It deliberately
does not implement another learning rule:

1. seal the complete selection before live execution;
2. classify the passed support as K=0, K=1, or K>=2;
3. for a learned K>=2 choice, prove that the Q2F policy version and online
   network state have not drifted since selection;
4. commit the selected real option once, passing its exact receipt and source
   policy metadata; and
5. if the runner returns an admitted transition/sequence, invoke the joint
   Q2F/Main transaction exactly once.

The option runner and joint transaction remain injectable seams for bounded
orchestration tests.  In production their module-level implementations are
the only defaults.  Under the prospective policy, physical support expiry is
a valid monotone release to branch-local Main; it is not a hard abort or a
zero-dose learning item.  A missing admitted suffix remains a runner-integrity
failure and is never converted into a learning item.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Callable

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SMC_DIR = HERE.parent / "smc-er-short-ep"
for _path in (HERE, SMC_DIR, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import c2_temporal_fork_joint_transaction as joint  # noqa: E402
import c2_temporal_fork_option_runner as option_runner  # noqa: E402
import c2_temporal_fork_selection as selection  # noqa: E402
from c2_temporal_fork_learning_adapter import (  # noqa: E402
    C2PrimitiveSequence,
    C2SMDPTransition,
)
from c2_temporal_fork_torch_adapter import (  # noqa: E402
    C2OptionLedger,
)
from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from smc_er_core import ConsumedBundleLedger, ObjectiveSpecialist  # noqa: E402


CHOICE_CLASS_K0 = "K0"
CHOICE_CLASS_K1 = "K1"
CHOICE_CLASS_K_GE_2 = "K>=2"


class C2TrainingStepError(joint.JointTransactionContractError):
    """The formal C2 training seam received an unsafe orchestration input."""


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise C2TrainingStepError(f"{field} must be a nonnegative exact integer")
    return value


def _finite_probability(value: object) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise C2TrainingStepError("selection behavior probability must be finite")
    result = float(value)
    if not np.isfinite(result) or not 0.0 < result <= 1.0:
        raise C2TrainingStepError(
            "selection behavior probability must lie in (0,1]"
        )
    return result


def _selection_digest(value: object) -> str:
    digest = getattr(value, "receipt_sha256", None)
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or digest != digest.lower()
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise C2TrainingStepError(
            "selection receipt must expose a lowercase SHA-256 receipt_sha256"
        )
    return digest


def _policy_version(specialist: ObjectiveSpecialist) -> int:
    value = getattr(specialist, "policy_version", None)
    return _exact_nonnegative_int(value, field="specialist.policy_version")


def _assert_learned_policy_current(
    choice: selection.C2PreparedForkSelection,
    specialist: ObjectiveSpecialist,
) -> int:
    """Seal K>=2 learned choice against policy/network drift immediately pre-live."""

    receipt = choice.receipt
    current_version = _policy_version(specialist)
    if receipt.q2f_policy_version != current_version:
        raise C2TrainingStepError(
            "selection Q2F policy_version drifted before live execution"
        )
    try:
        current_network_hash = selection._network_state_hash(specialist)
    except Exception as error:
        raise C2TrainingStepError(
            "current Q2F online network state cannot be hashed"
        ) from error
    if receipt.q2f_online_network_state_sha256 != current_network_hash:
        raise C2TrainingStepError(
            "selection Q2F online network state drifted before live execution"
        )
    return current_version


def _record_selection_digest(
    transaction_ledger: joint.JointOptionLedger,
    *,
    option_id: str,
    expected: str,
) -> None:
    """Check that the final durable record carries the same choice receipt."""

    state = transaction_ledger.state_dict()
    records = state.get("records")
    if not isinstance(records, (list, tuple)):
        raise C2TrainingStepError("joint ledger records are malformed")
    matches = [
        record
        for record in records
        if isinstance(record, dict) and record.get("option_id") == option_id
    ]
    if len(matches) != 1:
        raise C2TrainingStepError(
            "joint ledger lacks exactly one record for the selected option"
        )
    if matches[0].get("selection_receipt_sha256") != expected:
        raise C2TrainingStepError(
            "joint record selection receipt differs from the pre-live selection"
        )


def assert_real_candidate_main_identity(
    choice: selection.C2PreparedForkSelection,
    main: MODQNTrainer,
) -> None:
    """Bind every forecasted candidate to the exact Main updated afterwards.

    This public assertion is also used by the bounded episode runner before it
    installs a thin result-capturing wrapper around the real option runner.
    """

    if not choice.candidate_set:
        raise C2TrainingStepError(
            "production C2 selection lacks the forecasted candidate set"
        )
    for index, prepared in enumerate(choice.candidate_set):
        anchor = getattr(prepared, "anchor", None)
        if anchor is None or getattr(anchor, "trainer", None) is not main:
            raise C2TrainingStepError(
                "production C2 forecast/Main trainer identity mismatch "
                f"at candidate {index}"
            )


@dataclass(frozen=True)
class C2TrainingStepReceipt:
    """Frozen orchestration receipt for one pre-outcome choice attempt."""

    choice_class: str
    choice_mode: str
    candidate_count: int
    selected_option_id: str | None
    selection_receipt_sha256: str
    behavior_probability: float
    q2f_policy_version: int | None
    source_policy_version: int | None
    block_id: int | None
    live_committed: bool
    admitted: bool
    warmup: bool
    updated: bool
    joint_committed: bool
    termination_reason: str | None
    transition_sha256: str | None
    primitive_sequence_sha256: str | None
    q2f_receipt_sha256: str | None
    main_receipt_sha256: str | None
    joint_record_sha256: str | None


def _k0_receipt(
    choice: selection.C2PreparedForkSelection,
    *,
    candidate_count: int,
) -> C2TrainingStepReceipt:
    return C2TrainingStepReceipt(
        choice_class=CHOICE_CLASS_K0,
        choice_mode=choice.receipt.mode,
        candidate_count=candidate_count,
        selected_option_id=None,
        selection_receipt_sha256=_selection_digest(choice.receipt),
        behavior_probability=_finite_probability(choice.behavior_probability),
        q2f_policy_version=None,
        source_policy_version=None,
        block_id=None,
        live_committed=False,
        admitted=False,
        warmup=False,
        updated=False,
        joint_committed=False,
        termination_reason=None,
        transition_sha256=None,
        primitive_sequence_sha256=None,
        q2f_receipt_sha256=None,
        main_receipt_sha256=None,
        joint_record_sha256=None,
    )


def _no_admission_receipt(
    *,
    choice: selection.C2PreparedForkSelection,
    candidate_count: int,
    selected_option_id: str,
    selection_digest: str,
    behavior_probability: float,
    source_policy_version: int,
    block_id: int,
    termination_reason: str | None,
) -> C2TrainingStepReceipt:
    return C2TrainingStepReceipt(
        choice_class=(
            CHOICE_CLASS_K1
            if candidate_count == 1
            else CHOICE_CLASS_K_GE_2
        ),
        choice_mode=choice.receipt.mode,
        candidate_count=candidate_count,
        selected_option_id=selected_option_id,
        selection_receipt_sha256=selection_digest,
        behavior_probability=behavior_probability,
        q2f_policy_version=choice.receipt.q2f_policy_version,
        source_policy_version=source_policy_version,
        block_id=block_id,
        live_committed=True,
        admitted=False,
        warmup=False,
        updated=False,
        joint_committed=False,
        termination_reason=termination_reason,
        transition_sha256=None,
        primitive_sequence_sha256=None,
        q2f_receipt_sha256=None,
        main_receipt_sha256=None,
        joint_record_sha256=None,
    )


def run_c2_training_step(
    choice: selection.C2PreparedForkSelection,
    *,
    specialist: ObjectiveSpecialist | None,
    main: MODQNTrainer | None,
    beta: float,
    discount_factor: float,
    block_id: int,
    c2_option_ledger: C2OptionLedger | None,
    transaction_ledger: joint.JointOptionLedger | None,
    consumed_ledger: ConsumedBundleLedger | None = None,
    c1_bundle: Any | None = None,
    c3_bundle: Any | None = None,
    runner_fn: Callable[..., Any] | None = None,
    joint_fn: Callable[..., Any] | None = None,
) -> C2TrainingStepReceipt:
    """Run one formal C2 choice/live/joint-training seam.

    ``assert_prepared_selection_bound`` is intentionally the first operation:
    no live call, Q2F read, replay read, or ledger mutation can precede it.
    K=0 returns a Main-fallback receipt.  K=1 is an explicitly forced control;
    K>=2 learned choices are accepted only when the selection's Q2F policy and
    online-network digest still match immediately before live execution.
    """

    # This must remain first.  It revalidates the complete forecast support and
    # selected identity without resampling behavior RNG or touching live state.
    receipt = selection.assert_prepared_selection_bound(choice)
    candidate_count = len(receipt.support)
    if candidate_count == 0:
        return _k0_receipt(choice, candidate_count=candidate_count)
    if candidate_count == 1:
        choice_class = CHOICE_CLASS_K1
    else:
        choice_class = CHOICE_CLASS_K_GE_2

    if specialist is None or main is None:
        raise C2TrainingStepError(
            "K>=1 formal C2 step requires specialist and Main trainer"
        )
    if c2_option_ledger is None or transaction_ledger is None:
        raise C2TrainingStepError(
            "K>=1 formal C2 step requires C2 and joint ledgers"
        )
    if not isinstance(specialist, ObjectiveSpecialist):
        raise C2TrainingStepError("specialist must be ObjectiveSpecialist")
    if not isinstance(main, MODQNTrainer):
        raise C2TrainingStepError("main must be MODQNTrainer")
    if not isinstance(c2_option_ledger, C2OptionLedger):
        raise C2TrainingStepError("c2_option_ledger must be C2OptionLedger")
    if not isinstance(transaction_ledger, joint.JointOptionLedger):
        raise C2TrainingStepError("transaction_ledger must be JointOptionLedger")
    block_value = _exact_nonnegative_int(block_id, field="block_id")
    behavior_probability = _finite_probability(choice.behavior_probability)
    selection_digest = _selection_digest(receipt)
    selected = choice.selected_prepared_fork
    selected_option_id = receipt.selected_option_id
    if selected is None or selected_option_id is None:
        raise C2TrainingStepError(
            "K>=1 selection must expose one selected prepared fork and option ID"
        )

    if runner_fn is None:
        assert_real_candidate_main_identity(choice, main)

    # For K>=2 this is the last pre-live/pre-update read of Q2F.  K=1 is a
    # forced control and deliberately has no learned-choice assertion.
    current_policy_version = _policy_version(specialist)
    if choice_class == CHOICE_CLASS_K_GE_2 and receipt.mode == selection.CHOICE_MODE_Q2F:
        current_policy_version = _assert_learned_policy_current(choice, specialist)

    run_runner = option_runner.commit_prepared_option if runner_fn is None else runner_fn
    run_joint = joint.update_c2_joint_transaction if joint_fn is None else joint_fn

    # The runner is the sole live execution seam.  Its exact selection digest,
    # behavior probability, source policy, and block are explicit arguments.
    unit = run_runner(
        selected,
        opening_behavior_probability=behavior_probability,
        discount_factor=discount_factor,
        block_id=block_value,
        selection_receipt_sha256=selection_digest,
        source_policy_version=current_policy_version,
    )
    termination_reason = getattr(unit, "termination_reason", None)
    transition = getattr(unit, "transition", None)
    sequence = getattr(unit, "sequence", None)
    if transition is None or sequence is None:
        # A real environment terminal may close an option without an admitted
        # learning object.  It is reported explicitly and never passed as a
        # zero-dose transition.  A valid support expiry must instead arrive as
        # an admitted sequence with its branch-local Main release suffix.
        return _no_admission_receipt(
            choice=choice,
            candidate_count=candidate_count,
            selected_option_id=selected_option_id,
            selection_digest=selection_digest,
            behavior_probability=behavior_probability,
            source_policy_version=current_policy_version,
            block_id=block_value,
            termination_reason=termination_reason,
        )
    if not isinstance(transition, C2SMDPTransition):
        raise C2TrainingStepError("runner returned a non-C2 SMDP transition")
    if not isinstance(sequence, C2PrimitiveSequence):
        raise C2TrainingStepError("runner returned a non-C2 primitive sequence")
    if transition.selection_receipt_sha256 != selection_digest:
        raise C2TrainingStepError(
            "runner transition selection digest differs from the pre-live selection"
        )
    if sequence.selection_receipt_sha256 != selection_digest:
        raise C2TrainingStepError(
            "runner sequence selection digest differs from the pre-live selection"
        )

    # Exactly one call: the joint transaction owns Q2F update, combined Main
    # update, and the final at-most-once commit.  No lower-level update is
    # called directly by this formal seam.
    joint_receipt = run_joint(
        specialist,
        transition,
        main,
        sequence,
        beta=beta,
        c2_option_ledger=c2_option_ledger,
        transaction_ledger=transaction_ledger,
        consumer_block_id=block_value,
        source_block_id=block_value,
        source_policy_version=current_policy_version,
        consumed_ledger=consumed_ledger,
        c1_bundle=c1_bundle,
        c3_bundle=c3_bundle,
    )
    if getattr(joint_receipt, "selection_receipt_sha256", None) != selection_digest:
        raise C2TrainingStepError(
            "joint receipt selection digest differs from the pre-live selection"
        )
    joint_warmup = bool(getattr(joint_receipt, "warmup", False))
    joint_updated = bool(getattr(joint_receipt, "updated", False))
    joint_committed = bool(getattr(joint_receipt, "committed", False))
    if joint_committed:
        _record_selection_digest(
            transaction_ledger,
            option_id=sequence.option_id,
            expected=selection_digest,
        )
    elif not joint_warmup or joint_updated:
        raise C2TrainingStepError(
            "non-warmup joint attempt must end in one durable commit"
        )
    if transition.source_unit_id != sequence.source_unit_id:
        raise C2TrainingStepError("runner transition/sequence source-unit IDs disagree")
    return C2TrainingStepReceipt(
        choice_class=choice_class,
        choice_mode=receipt.mode,
        candidate_count=candidate_count,
        selected_option_id=selected_option_id,
        selection_receipt_sha256=selection_digest,
        behavior_probability=behavior_probability,
        q2f_policy_version=receipt.q2f_policy_version,
        source_policy_version=current_policy_version,
        block_id=block_value,
        live_committed=True,
        admitted=True,
        warmup=joint_warmup,
        updated=joint_updated,
        joint_committed=joint_committed,
        termination_reason=termination_reason,
        transition_sha256=transition.sequence_sha256,
        primitive_sequence_sha256=sequence.sequence_sha256,
        q2f_receipt_sha256=getattr(joint_receipt, "q2f_receipt_sha256", None),
        main_receipt_sha256=getattr(joint_receipt, "main_receipt_sha256", None),
        joint_record_sha256=getattr(joint_receipt, "record_sha256", None),
    )


__all__ = [
    "CHOICE_CLASS_K0",
    "CHOICE_CLASS_K1",
    "CHOICE_CLASS_K_GE_2",
    "C2TrainingStepError",
    "C2TrainingStepReceipt",
    "assert_real_candidate_main_identity",
    "run_c2_training_step",
]
