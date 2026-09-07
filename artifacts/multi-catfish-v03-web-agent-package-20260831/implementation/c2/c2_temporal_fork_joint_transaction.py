"""Atomic C2 Q2F/Main joint transaction for the V0.3 carrier.

The two lower-level adapters remain useful as isolated contract fixtures, but
the training seam for a real C2 source unit is this module.  One call consumes
one admitted option exactly once and performs, in order, one fixed-window Q2F
update and one combined Main update.  The durable joint record is committed
last.  Every mutable object touched by either update is snapshotted before the
first optimizer step so a failure at any boundary restores the complete
pre-transaction state.

This file is intentionally append-only: it does not change the frozen Main
trainer or either V0.3 lower-level adapter.  It is an integration seam, not an
efficacy claim or a training runner.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SMC_DIR = HERE.parent / "smc-er-short-ep"
for _path in (HERE, SMC_DIR, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import c2_temporal_fork_combined_carrier as combined  # noqa: E402
import c2_temporal_fork_torch_adapter as torch_adapter  # noqa: E402
from c2_temporal_fork_learning_adapter import (  # noqa: E402
    C2PrimitiveSequence,
    C2SMDPTransition,
    array_sha256,
)
from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from smc_er_core import AtomicBundle, ConsumedBundleLedger, ObjectiveSpecialist  # noqa: E402


JOINT_POLICY_VERSION = "c2-v03-joint-transaction-v1"
JOINT_LEDGER_FORMAT_VERSION = 1
C2_OBJECTIVE_INDEX = 1


class JointTransactionContractError(
    torch_adapter.TorchAdapterContractError
):
    """The cross-adapter transaction contract was not satisfied."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value.lower() != value
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise JointTransactionContractError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise JointTransactionContractError(
            f"{field} must be a nonnegative exact integer"
        )
    return value


def _canonical(value: object) -> object:
    """Convert receipt/record values into deterministic JSON primitives."""

    if is_dataclass(value):
        return _canonical(asdict(value))
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        converted = float(value)
        if not math.isfinite(converted):
            raise JointTransactionContractError("receipt contains a non-finite float")
        return converted
    if isinstance(value, (bool, int, str)) or value is None:
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise JointTransactionContractError("receipt contains a non-finite float")
        return value
    raise JointTransactionContractError(
        f"receipt contains unsupported value type {type(value).__name__}"
    )


def _json_digest(value: object) -> str:
    payload = json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _bundle_authority(bundle: object, name: str, *, source: str) -> object:
    if hasattr(bundle, name):
        return getattr(bundle, name)
    provenance = getattr(bundle, "provenance", None)
    if isinstance(provenance, Mapping) and name in provenance:
        return provenance[name]
    raise JointTransactionContractError(f"{source} bundle lacks {name} authority")


def _bundle_lineage(bundle: object, *, source: str) -> tuple[int, int]:
    block_id = _exact_nonnegative_int(
        _bundle_authority(bundle, "block_id", source=source),
        field=f"{source}.block_id",
    )
    source_policy_version = _exact_nonnegative_int(
        _bundle_authority(bundle, "source_policy_version", source=source),
        field=f"{source}.source_policy_version",
    )
    return block_id, source_policy_version


def _q2_lineage(sequence: C2PrimitiveSequence) -> tuple[int, int]:
    lineages = tuple(
        _bundle_lineage(bundle, source="C2") for bundle in sequence.transitions
    )
    if not lineages or len(set(lineages)) != 1:
        raise JointTransactionContractError(
            "C2 constituents must share one source block and policy version"
        )
    return lineages[0]


def _snapshot_gradients(networks: Sequence[torch.nn.Module]) -> tuple[Any, ...]:
    return tuple(
        {
            name: None
            if parameter.grad is None
            else parameter.grad.detach().cpu().clone()
            for name, parameter in network.named_parameters()
        }
        for network in networks
    )


def _restore_gradients(
    networks: Sequence[torch.nn.Module], gradients: Sequence[Mapping[str, Any]]
) -> None:
    for network, saved in zip(networks, gradients, strict=True):
        for name, parameter in network.named_parameters():
            gradient = saved[name]
            parameter.grad = (
                None if gradient is None else gradient.to(parameter.device)
            )


def _snapshot_specialist(specialist: ObjectiveSpecialist) -> tuple[Any, ...]:
    """Capture all Q2F state that can affect a subsequent update."""

    return (
        copy.deepcopy(specialist.online.state_dict()),
        copy.deepcopy(specialist.target.state_dict()),
        copy.deepcopy(specialist.optimizer.state_dict()),
        int(specialist.updates),
        int(specialist.policy_version),
        copy.deepcopy(specialist.rng.bit_generator.state),
        copy.deepcopy(specialist.replay_rng.bit_generator.state),
        _snapshot_gradients((specialist.online,)),
    )


def _restore_specialist(
    specialist: ObjectiveSpecialist, snapshot: tuple[Any, ...]
) -> None:
    (
        online_state,
        target_state,
        optimizer_state,
        updates,
        policy_version,
        rng_state,
        replay_rng_state,
        gradients,
    ) = snapshot
    specialist.online.load_state_dict(online_state)
    specialist.target.load_state_dict(target_state)
    specialist.optimizer.load_state_dict(optimizer_state)
    specialist.updates = updates
    specialist.policy_version = policy_version
    specialist.rng.bit_generator.state = copy.deepcopy(rng_state)
    specialist.replay_rng.bit_generator.state = copy.deepcopy(replay_rng_state)
    _restore_gradients((specialist.online,), gradients)


def _main_counter_snapshot(main: MODQNTrainer) -> tuple[tuple[str, bool, Any], ...]:
    """Snapshot optional counter fields without assuming a trainer variant.

    The current MODQNTrainer exposes no persistent update counter.  Future
    runners and test doubles may expose one, so the seam snapshots the common
    scalar/list/dict spellings and restores their presence as well as values.
    """

    names = (
        "updates",
        "update_count",
        "update_counts",
        "_updates",
        "_update_count",
        "_update_counts",
        "_c2_joint_update_counters",
    )
    return tuple(
        (
            name,
            hasattr(main, name),
            copy.deepcopy(getattr(main, name)) if hasattr(main, name) else None,
        )
        for name in names
    )


def _restore_main_counters(
    main: MODQNTrainer, snapshot: Sequence[tuple[str, bool, Any]]
) -> None:
    for name, existed, value in snapshot:
        if existed:
            setattr(main, name, copy.deepcopy(value))
        elif hasattr(main, name):
            delattr(main, name)


def _snapshot_main(main: MODQNTrainer) -> tuple[Any, ...]:
    """Capture all three heads, optimizers, gradients, RNGs and counters."""

    return (
        tuple(copy.deepcopy(net.state_dict()) for net in main.q_nets),
        tuple(copy.deepcopy(net.state_dict()) for net in main.target_nets),
        tuple(copy.deepcopy(optimizer.state_dict()) for optimizer in main.optimizers),
        _snapshot_gradients(main.q_nets),
        copy.deepcopy(main._train_rng.bit_generator.state),
        copy.deepcopy(main._env_rng.bit_generator.state),
        copy.deepcopy(main._mobility_rng.bit_generator.state),
        _main_counter_snapshot(main),
    )


def _restore_main(main: MODQNTrainer, snapshot: tuple[Any, ...]) -> None:
    (
        q_states,
        target_states,
        optimizer_states,
        gradients,
        train_rng,
        env_rng,
        mobility_rng,
        counters,
    ) = snapshot
    for network, state in zip(main.q_nets, q_states, strict=True):
        network.load_state_dict(state)
    for network, state in zip(main.target_nets, target_states, strict=True):
        network.load_state_dict(state)
    for optimizer, state in zip(main.optimizers, optimizer_states, strict=True):
        optimizer.load_state_dict(state)
    _restore_gradients(main.q_nets, gradients)
    main._train_rng.bit_generator.state = copy.deepcopy(train_rng)
    main._env_rng.bit_generator.state = copy.deepcopy(env_rng)
    main._mobility_rng.bit_generator.state = copy.deepcopy(mobility_rng)
    _restore_main_counters(main, counters)


def _snapshot_process_rng() -> tuple[Any, Any]:
    return copy.deepcopy(np.random.get_state()), torch.get_rng_state().clone()


def _restore_process_rng(snapshot: tuple[Any, Any]) -> None:
    numpy_state, torch_state = snapshot
    np.random.set_state(copy.deepcopy(numpy_state))
    torch.set_rng_state(torch_state.clone())


def _snapshot_ledger(ledger: object | None) -> Any:
    if ledger is None:
        return None
    state_dict = getattr(ledger, "state_dict", None)
    if not callable(state_dict):
        raise JointTransactionContractError("ledger must expose state_dict")
    return copy.deepcopy(state_dict())


def _restore_ledger(ledger: object | None, snapshot: Any) -> None:
    if ledger is None or snapshot is None:
        return
    loader = getattr(ledger, "load_state_dict", None)
    if not callable(loader):
        raise JointTransactionContractError("ledger must expose load_state_dict")
    loader(copy.deepcopy(snapshot))


@dataclass(frozen=True)
class JointOptionRecord:
    """Hash-bound durable commit record for one C2 option/source unit."""

    option_id: str
    source_unit_id: str
    transition_sha256: str
    primitive_sequence_sha256: str
    selection_receipt_sha256: str
    constituent_bundle_ids: tuple[str, ...]
    source_block_id: int
    source_policy_version: int
    consumer_block_id: int
    q2f_receipt_sha256: str
    main_receipt_sha256: str
    policy_version: str
    record_sha256: str

    @classmethod
    def create(
        cls,
        *,
        option_id: str,
        source_unit_id: str,
        transition_sha256: str,
        primitive_sequence_sha256: str,
        selection_receipt_sha256: str,
        constituent_bundle_ids: Sequence[str],
        source_block_id: int,
        source_policy_version: int,
        consumer_block_id: int,
        q2f_receipt_sha256: str,
        main_receipt_sha256: str,
        policy_version: str = JOINT_POLICY_VERSION,
    ) -> "JointOptionRecord":
        values = dict(
            option_id=option_id,
            source_unit_id=source_unit_id,
            transition_sha256=transition_sha256,
            primitive_sequence_sha256=primitive_sequence_sha256,
            selection_receipt_sha256=selection_receipt_sha256,
            constituent_bundle_ids=tuple(constituent_bundle_ids),
            source_block_id=source_block_id,
            source_policy_version=source_policy_version,
            consumer_block_id=consumer_block_id,
            q2f_receipt_sha256=q2f_receipt_sha256,
            main_receipt_sha256=main_receipt_sha256,
            policy_version=policy_version,
        )
        digest = _json_digest(values)
        return cls(record_sha256=digest, **values)

    def __post_init__(self) -> None:
        if type(self.option_id) is not str or not self.option_id:
            raise JointTransactionContractError("record option_id must be nonempty")
        if type(self.source_unit_id) is not str or not self.source_unit_id:
            raise JointTransactionContractError(
                "record source_unit_id must be nonempty"
            )
        if self.option_id != self.source_unit_id:
            raise JointTransactionContractError(
                "record option/source-unit identity must match"
            )
        _digest(self.transition_sha256, field="record.transition_sha256")
        _digest(
            self.primitive_sequence_sha256,
            field="record.primitive_sequence_sha256",
        )
        _digest(
            self.selection_receipt_sha256,
            field="record.selection_receipt_sha256",
        )
        _digest(self.q2f_receipt_sha256, field="record.q2f_receipt_sha256")
        _digest(self.main_receipt_sha256, field="record.main_receipt_sha256")
        ids = tuple(self.constituent_bundle_ids)
        if (
            isinstance(self.constituent_bundle_ids, (str, bytes))
            or not 1 <= len(ids) <= 4
            or any(type(value) is not str or not value for value in ids)
            or len(set(ids)) != len(ids)
        ):
            raise JointTransactionContractError(
                "record constituent_bundle_ids must be one-to-four unique nonempty IDs"
            )
        _exact_nonnegative_int(self.source_block_id, field="record.source_block_id")
        _exact_nonnegative_int(
            self.source_policy_version, field="record.source_policy_version"
        )
        _exact_nonnegative_int(
            self.consumer_block_id, field="record.consumer_block_id"
        )
        if type(self.policy_version) is not str or not self.policy_version:
            raise JointTransactionContractError("record policy_version must be nonempty")
        _digest(self.record_sha256, field="record.record_sha256")
        body = {
            "option_id": self.option_id,
            "source_unit_id": self.source_unit_id,
            "transition_sha256": self.transition_sha256,
            "primitive_sequence_sha256": self.primitive_sequence_sha256,
            "selection_receipt_sha256": self.selection_receipt_sha256,
            "constituent_bundle_ids": self.constituent_bundle_ids,
            "source_block_id": self.source_block_id,
            "source_policy_version": self.source_policy_version,
            "consumer_block_id": self.consumer_block_id,
            "q2f_receipt_sha256": self.q2f_receipt_sha256,
            "main_receipt_sha256": self.main_receipt_sha256,
            "policy_version": self.policy_version,
        }
        if self.record_sha256 != _json_digest(body):
            raise JointTransactionContractError("record_sha256 does not match record payload")
        object.__setattr__(self, "constituent_bundle_ids", ids)


class JointOptionLedger:
    """Checkpointable at-most-once ledger for committed joint option units."""

    FORMAT_VERSION = JOINT_LEDGER_FORMAT_VERSION

    def __init__(self) -> None:
        self._records: dict[str, JointOptionRecord] = {}
        self._seen_bundle_ids: set[str] = set()

    def preflight_identity(
        self,
        *,
        option_id: str,
        source_unit_id: str,
        constituent_bundle_ids: Sequence[str],
    ) -> None:
        if type(option_id) is not str or not option_id:
            raise JointTransactionContractError("option_id must be nonempty")
        if type(source_unit_id) is not str or not source_unit_id:
            raise JointTransactionContractError("source_unit_id must be nonempty")
        if option_id != source_unit_id:
            raise JointTransactionContractError(
                "option/source-unit identity must match"
            )
        ids = tuple(constituent_bundle_ids)
        if (
            isinstance(constituent_bundle_ids, (str, bytes))
            or not 1 <= len(ids) <= 4
            or any(type(value) is not str or not value for value in ids)
            or len(set(ids)) != len(ids)
        ):
            raise JointTransactionContractError("joint option bundle identity is malformed")
        if option_id in self._records:
            raise JointTransactionContractError(
                f"joint option was already consumed: {option_id}"
            )
        repeated = sorted(set(ids) & self._seen_bundle_ids)
        if repeated:
            raise JointTransactionContractError(
                "joint option bundle was already consumed: " + ",".join(repeated)
            )

    def preflight(self, record: JointOptionRecord) -> JointOptionRecord:
        if not isinstance(record, JointOptionRecord):
            raise JointTransactionContractError("joint ledger accepts JointOptionRecord")
        self.preflight_identity(
            option_id=record.option_id,
            source_unit_id=record.source_unit_id,
            constituent_bundle_ids=record.constituent_bundle_ids,
        )
        return record

    def commit(self, record: JointOptionRecord) -> JointOptionRecord:
        pending = self.preflight(record)
        self._records[pending.option_id] = pending
        self._seen_bundle_ids.update(pending.constituent_bundle_ids)
        return pending

    def __len__(self) -> int:
        return len(self._records)

    def state_dict(self) -> dict[str, Any]:
        records = [
            _canonical(asdict(record))
            for record in sorted(self._records.values(), key=lambda value: value.option_id)
        ]
        return {
            "format_version": self.FORMAT_VERSION,
            "records": records,
            "seen_option_ids": [record["option_id"] for record in records],
            "seen_bundle_ids": sorted(self._seen_bundle_ids),
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        if not isinstance(state, Mapping):
            raise TypeError("joint ledger state must be a mapping")
        if state.get("format_version") != self.FORMAT_VERSION:
            raise ValueError("unsupported joint ledger format")
        raw_records = state.get("records")
        if isinstance(raw_records, (str, bytes)) or not isinstance(raw_records, Sequence):
            raise TypeError("joint ledger records must be a sequence")
        new_records: dict[str, JointOptionRecord] = {}
        new_bundles: set[str] = set()
        for raw in raw_records:
            if not isinstance(raw, Mapping):
                raise TypeError("joint ledger record must be a mapping")
            record = JointOptionRecord(**dict(raw))
            if record.option_id in new_records:
                raise ValueError("joint ledger contains duplicate option identity")
            if new_bundles.intersection(record.constituent_bundle_ids):
                raise ValueError("joint ledger contains duplicate bundle identity")
            new_records[record.option_id] = record
            new_bundles.update(record.constituent_bundle_ids)
        expected_options = state.get("seen_option_ids")
        expected_bundles = state.get("seen_bundle_ids")
        if (
            isinstance(expected_options, (str, bytes))
            or not isinstance(expected_options, Sequence)
            or tuple(expected_options) != tuple(sorted(new_records))
        ):
            raise ValueError("joint ledger seen_option_ids disagree with records")
        if (
            isinstance(expected_bundles, (str, bytes))
            or not isinstance(expected_bundles, Sequence)
            or tuple(expected_bundles) != tuple(sorted(new_bundles))
        ):
            raise ValueError("joint ledger seen_bundle_ids disagree with records")
        self._records = new_records
        self._seen_bundle_ids = new_bundles


@dataclass(frozen=True)
class JointTransactionReceipt:
    """Receipt for one warmup or committed Q2F/Main joint attempt."""

    mode: str
    updated: bool
    warmup: bool
    committed: bool
    option_id: str
    source_unit_id: str
    transition_sha256: str
    primitive_sequence_sha256: str
    selection_receipt_sha256: str
    constituent_bundle_ids: tuple[str, ...]
    source_block_id: int
    source_policy_version: int
    consumer_block_id: int
    policy_version: str
    q2f_receipt_sha256: str | None
    main_receipt_sha256: str | None
    record_sha256: str | None
    q2f_receipt: Any | None = None
    main_receipt: Any | None = None


def _validate_cross_payload(
    specialist: ObjectiveSpecialist,
    transition: C2SMDPTransition,
    main: MODQNTrainer,
    sequence: C2PrimitiveSequence,
    *,
    consumer_block_id: int,
    source_block_id: int | None,
    source_policy_version: int | None,
    transaction_ledger: JointOptionLedger,
    c2_option_ledger: torch_adapter.C2OptionLedger,
    consumed_ledger: ConsumedBundleLedger | None,
    c1_bundle: AtomicBundle | None,
    c3_bundle: AtomicBundle | None,
) -> tuple[tuple[int, int], tuple[AtomicBundle, ...]]:
    """Perform every deterministic identity/lineage check before mutation."""

    if not isinstance(specialist, ObjectiveSpecialist):
        raise JointTransactionContractError("joint transaction requires ObjectiveSpecialist")
    if not isinstance(transition, C2SMDPTransition):
        raise JointTransactionContractError("joint transaction requires C2SMDPTransition")
    if not isinstance(main, MODQNTrainer):
        raise JointTransactionContractError("joint transaction requires MODQNTrainer")
    if not isinstance(sequence, C2PrimitiveSequence):
        raise JointTransactionContractError("joint transaction requires C2PrimitiveSequence")
    if not isinstance(transaction_ledger, JointOptionLedger):
        raise JointTransactionContractError(
            "joint transaction requires a JointOptionLedger"
        )
    if not isinstance(c2_option_ledger, torch_adapter.C2OptionLedger):
        raise JointTransactionContractError(
            "joint transaction requires a C2 option ledger"
        )
    if source_block_id is not None:
        _exact_nonnegative_int(source_block_id, field="source_block_id")
    if source_policy_version is not None:
        _exact_nonnegative_int(source_policy_version, field="source_policy_version")
    if specialist.objective_index != C2_OBJECTIVE_INDEX:
        raise JointTransactionContractError("Q2F specialist must target objective 1")
    if transition.source_id != "C2" or transition.objective_index != C2_OBJECTIVE_INDEX:
        raise JointTransactionContractError("transition must be a Q2 C2 transition")
    if sequence.source_id != "C2" or sequence.target_objective != C2_OBJECTIVE_INDEX:
        raise JointTransactionContractError("sequence must target Q2 via C2")
    try:
        torch_adapter._ensure_q2_specialist(specialist, transition)
        torch_adapter.assert_admission_bound(sequence)
        combined._validate_c2(main, sequence)
    except Exception as error:
        raise JointTransactionContractError(
            "Q2F/sequence admission validation failed"
        ) from error
    if transition.option_id != sequence.option_id:
        raise JointTransactionContractError("transition and sequence option IDs disagree")
    if transition.source_unit_id != sequence.source_unit_id:
        raise JointTransactionContractError(
            "transition and sequence source-unit IDs disagree"
        )
    if transition.selection_receipt_sha256 != sequence.selection_receipt_sha256:
        raise JointTransactionContractError(
            "transition and sequence selection receipts disagree"
        )
    if transition.duration != len(sequence.transitions):
        raise JointTransactionContractError(
            "transition duration disagrees with primitive sequence"
        )
    if transition.action != int(sequence.transitions[0].actions[sequence.focal_user]):
        raise JointTransactionContractError(
            "transition opening action disagrees with primitive sequence"
        )
    if transition.terminal != bool(sequence.transitions[-1].done):
        raise JointTransactionContractError(
            "transition terminal flag disagrees with primitive sequence"
        )
    rows = torch_adapter._validated_focal_rows(main, sequence)
    focal_rewards = tuple(float(row["rewards"][sequence.focal_user, 1]) for row in rows)
    if tuple(transition.r2_rewards) != focal_rewards:
        raise JointTransactionContractError(
            "transition r2 rewards disagree with primitive sequence"
        )
    if array_sha256(sequence.transitions[0].states[sequence.focal_user]) != array_sha256(
        transition.opening_state
    ):
        raise JointTransactionContractError(
            "transition opening state disagrees with primitive sequence"
        )
    if array_sha256(sequence.transitions[0].masks[sequence.focal_user]) != array_sha256(
        transition.opening_mask
    ):
        raise JointTransactionContractError(
            "transition opening mask disagrees with primitive sequence"
        )

    lineage = _q2_lineage(sequence)
    if source_block_id is not None and source_block_id != lineage[0]:
        raise JointTransactionContractError(
            "declared source_block_id disagrees with C2 constituents"
        )
    if source_policy_version is not None and source_policy_version != lineage[1]:
        raise JointTransactionContractError(
            "declared source_policy_version disagrees with C2 constituents"
        )
    resolved_consumer_block = _exact_nonnegative_int(
        consumer_block_id, field="consumer_block_id"
    )
    age = resolved_consumer_block - lineage[0]
    if age < 0:
        raise JointTransactionContractError("consumer block precedes source block")
    if age > combined.FROZEN_MAX_SOURCE_AGE_BLOCKS["C2"]:
        raise JointTransactionContractError(
            "C2 source age exceeds the frozen joint-transaction maximum"
        )

    if c1_bundle is not None or c3_bundle is not None:
        if not isinstance(consumed_ledger, ConsumedBundleLedger):
            raise JointTransactionContractError(
                "C1/C3 joint sources require a consumed-bundle ledger"
            )
    c1_c3_bundles = tuple(
        item for item in (c1_bundle, c3_bundle) if item is not None
    )
    if c1_bundle is not None:
        combined._validate_bundle(main, c1_bundle, source="C1")
    if c3_bundle is not None:
        combined._validate_bundle(main, c3_bundle, source="C3")
    ids = tuple(sequence.constituent_bundle_ids)
    c1_c3_ids = tuple(item.bundle_id for item in c1_c3_bundles)
    if len(set(ids + c1_c3_ids)) != len(ids + c1_c3_ids):
        raise JointTransactionContractError(
            "one bundle cannot be consumed by two joint sources"
        )
    # Validate every optional combined-carrier lineage before the first Q2F
    # optimizer step.  The underlying carrier repeats these checks defensively
    # after replay warmup, but this seam must fail before any mutation.
    for source, bundle in (("C1", c1_bundle), ("C3", c3_bundle)):
        if bundle is None:
            continue
        source_lineage = combined._bundle_lineage(bundle, source=source)
        source_age = resolved_consumer_block - source_lineage[0]
        if source_age < 0:
            raise JointTransactionContractError(
                f"{source} source block comes from a future consumer block"
            )
        if source_age > combined.FROZEN_MAX_SOURCE_AGE_BLOCKS[source]:
            raise JointTransactionContractError(
                f"{source} source age exceeds the frozen joint-transaction maximum"
            )
    # These are all read-only preflights.  They intentionally precede the
    # specialist optimizer so no malformed or duplicate item can burn Q2F.
    transaction_ledger.preflight_identity(
        option_id=sequence.option_id,
        source_unit_id=sequence.source_unit_id,
        constituent_bundle_ids=ids,
    )
    c2_option_ledger.preflight(sequence)
    if consumed_ledger is not None:
        consumed_ledger.preflight(c1_c3_bundles)
    if set(c1_c3_ids) & combined._c2_seen_ids(c2_option_ledger):
        raise JointTransactionContractError(
            "C1/C3 bundle was already consumed by the C2 ledger"
        )
    if set(ids) & combined._ledger_seen_ids(consumed_ledger):
        raise JointTransactionContractError(
            "C2 bundle was already consumed by the C1/C3 ledger"
        )
    return lineage, c1_c3_bundles


def _empty_receipt(
    *,
    sequence: C2PrimitiveSequence,
    transition: C2SMDPTransition,
    lineage: tuple[int, int],
    consumer_block_id: int,
    policy_version: str,
) -> JointTransactionReceipt:
    return JointTransactionReceipt(
        mode="warmup_no_update",
        updated=False,
        warmup=True,
        committed=False,
        option_id=sequence.option_id,
        source_unit_id=sequence.source_unit_id,
        transition_sha256=transition.sequence_sha256,
        primitive_sequence_sha256=sequence.sequence_sha256,
        selection_receipt_sha256=sequence.selection_receipt_sha256,
        constituent_bundle_ids=sequence.constituent_bundle_ids,
        source_block_id=lineage[0],
        source_policy_version=lineage[1],
        consumer_block_id=consumer_block_id,
        policy_version=policy_version,
        q2f_receipt_sha256=None,
        main_receipt_sha256=None,
        record_sha256=None,
    )


def update_c2_joint_transaction(
    specialist: ObjectiveSpecialist,
    transition: C2SMDPTransition,
    main: MODQNTrainer,
    sequence: C2PrimitiveSequence,
    *,
    beta: float,
    c2_option_ledger: torch_adapter.C2OptionLedger,
    transaction_ledger: JointOptionLedger,
    consumer_block_id: int,
    source_block_id: int | None = None,
    source_policy_version: int | None = None,
    consumed_ledger: ConsumedBundleLedger | None = None,
    c1_bundle: AtomicBundle | None = None,
    c3_bundle: AtomicBundle | None = None,
    policy_version: str = JOINT_POLICY_VERSION,
) -> JointTransactionReceipt:
    """Commit exactly one C2 Q2F/Main option/source-unit transaction.

    All validation and read-only duplicate preflight occurs before the first
    optimizer step.  On a replay warmup, neither Q2F nor Main is sampled or
    updated.  Otherwise the fixed-window Q2F update runs once, followed by the
    combined Main update once, and the joint ledger is committed last.
    """

    if type(policy_version) is not str or not policy_version:
        raise JointTransactionContractError("policy_version must be nonempty")
    beta_value = combined._beta(beta)
    lineage, c1_c3_bundles = _validate_cross_payload(
        specialist,
        transition,
        main,
        sequence,
        consumer_block_id=consumer_block_id,
        source_block_id=source_block_id,
        source_policy_version=source_policy_version,
        transaction_ledger=transaction_ledger,
        c2_option_ledger=c2_option_ledger,
        consumed_ledger=consumed_ledger,
        c1_bundle=c1_bundle,
        c3_bundle=c3_bundle,
    )
    resolved_consumer = _exact_nonnegative_int(
        consumer_block_id, field="consumer_block_id"
    )

    # Warmup is checked after validation/preflight but before any RNG access or
    # optimizer call.  This keeps malformed/duplicate inputs fail-closed while
    # preserving the existing no-update replay schedule.
    if len(main.replay) < int(main.config.batch_size):
        return _empty_receipt(
            sequence=sequence,
            transition=transition,
            lineage=lineage,
            consumer_block_id=resolved_consumer,
            policy_version=policy_version,
        )

    specialist_snapshot = _snapshot_specialist(specialist)
    main_snapshot = _snapshot_main(main)
    process_rng_snapshot = _snapshot_process_rng()
    consumed_snapshot = _snapshot_ledger(consumed_ledger)
    c2_snapshot = _snapshot_ledger(c2_option_ledger)
    transaction_snapshot = _snapshot_ledger(transaction_ledger)

    try:
        q2f_receipt = torch_adapter.update_q2f_smdp(specialist, transition)
        main_receipt = combined.update_main_with_combined_carrier(
            main,
            c1_bundle=c1_bundle,
            c2_sequence=sequence,
            c3_bundle=c3_bundle,
            beta=beta_value,
            consumed_ledger=consumed_ledger,
            c2_option_ledger=c2_option_ledger,
            consumer_block_id=resolved_consumer,
        )
        q2f_digest = _json_digest(q2f_receipt)
        main_digest = _json_digest(main_receipt)
        record = JointOptionRecord.create(
            option_id=sequence.option_id,
            source_unit_id=sequence.source_unit_id,
            transition_sha256=transition.sequence_sha256,
            primitive_sequence_sha256=sequence.sequence_sha256,
            selection_receipt_sha256=sequence.selection_receipt_sha256,
            constituent_bundle_ids=sequence.constituent_bundle_ids,
            source_block_id=lineage[0],
            source_policy_version=lineage[1],
            consumer_block_id=resolved_consumer,
            q2f_receipt_sha256=q2f_digest,
            main_receipt_sha256=main_digest,
            policy_version=policy_version,
        )
        # This is the final durable mutation.  If a custom persistence layer
        # fails after partial mutation, all snapshots below still restore it.
        committed = transaction_ledger.commit(record)
        if committed != record:
            raise JointTransactionContractError(
                "joint ledger commit changed its preflight record"
            )
    except Exception:
        _restore_specialist(specialist, specialist_snapshot)
        _restore_main(main, main_snapshot)
        _restore_process_rng(process_rng_snapshot)
        _restore_ledger(consumed_ledger, consumed_snapshot)
        _restore_ledger(c2_option_ledger, c2_snapshot)
        _restore_ledger(transaction_ledger, transaction_snapshot)
        raise

    return JointTransactionReceipt(
        mode="q2f_once_plus_combined_main_once",
        updated=True,
        warmup=False,
        committed=True,
        option_id=sequence.option_id,
        source_unit_id=sequence.source_unit_id,
        transition_sha256=transition.sequence_sha256,
        primitive_sequence_sha256=sequence.sequence_sha256,
        selection_receipt_sha256=sequence.selection_receipt_sha256,
        constituent_bundle_ids=sequence.constituent_bundle_ids,
        source_block_id=lineage[0],
        source_policy_version=lineage[1],
        consumer_block_id=resolved_consumer,
        policy_version=policy_version,
        q2f_receipt_sha256=q2f_digest,
        main_receipt_sha256=main_digest,
        record_sha256=record.record_sha256,
        q2f_receipt=q2f_receipt,
        main_receipt=main_receipt,
    )


__all__ = [
    "JOINT_POLICY_VERSION",
    "JointOptionLedger",
    "JointOptionRecord",
    "JointTransactionContractError",
    "JointTransactionReceipt",
    "update_c2_joint_transaction",
]
