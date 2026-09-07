"""Torch optimizer seams for the C2 V0.3 temporal fork.

This file is an append-only integration fixture.  It deliberately does not
change ``smc_er_core.py``, ``modqn.py``, or a runner.  The two public update
functions below are the smallest executable boundary needed to test whether
the C2 contract can reach real optimizers:

* ``update_q2f_smdp`` performs one private Q2F option-level update.  Its
  one-to-four-step observed return is a fixed-window regression target with
  zero off-support bootstrap; calibration is applied once.
* ``update_main_with_c2_sequence_once`` samples canonical Main replay once,
  leaves Q1 and Q3 at the baseline loss, and blends only Q2 with the mean of
  exactly four focal primitive TD losses.  The four bundle IDs and one option
  source-unit are committed together after all three optimizer steps.

The adapter has no C1/C3 path and no runner integration.  Its scientific
claim ceiling is therefore only ``C2-only integration fixture``; passing its
tests is not evidence of end-to-end training or EE improvement.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
import torch

import c2_temporal_fork_core as c2_core
from c2_temporal_fork_learning_adapter import (
    C2PrimitiveSequence,
    C2SMDPTransition,
    EXPECTED_DURATION,
    LearningContractError,
    assert_admission_bound,
    mean_primitive_loss,
)
from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NO_OP_ACTION
from mcrl.runtime.finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)
from smc_er_core import ObjectiveSpecialist


C2_OBJECTIVE_INDEX = 1
CLAIM_CEILING = "C2-only integration fixture"


class TorchAdapterContractError(LearningContractError):
    """The Torch seam received an invalid or unsafe learning item."""


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.number)
    ):
        raise TorchAdapterContractError(f"{field} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted):
        raise TorchAdapterContractError(f"{field} must be finite")
    return converted


def _beta(value: object) -> float:
    result = _finite(value, field="beta")
    if not 0.0 <= result < 1.0:
        raise TorchAdapterContractError("beta must satisfy 0 <= beta < 1")
    return result


def _calibration_scale(config: object, objective: int) -> float:
    enabled = getattr(config, "reward_calibration_enabled", None)
    if type(enabled) is not bool:
        raise TorchAdapterContractError(
            "config.reward_calibration_enabled must be Boolean"
        )
    try:
        raw_scale = getattr(config, "reward_calibration_scales")[objective]
    except (AttributeError, IndexError, TypeError) as error:
        raise TorchAdapterContractError(
            "config.reward_calibration_scales lacks the target objective"
        ) from error
    scale = _finite(raw_scale, field="reward_calibration_scale")
    if scale <= 0.0:
        raise TorchAdapterContractError("reward_calibration_scale must be positive")
    return scale if enabled else 1.0


def _ensure_q2_specialist(
    specialist: ObjectiveSpecialist, transition: C2SMDPTransition
) -> None:
    if not isinstance(specialist, ObjectiveSpecialist):
        raise TorchAdapterContractError(
            "update_q2f_smdp requires an ObjectiveSpecialist"
        )
    if specialist.objective_index != C2_OBJECTIVE_INDEX:
        raise TorchAdapterContractError(
            "Q2F SMDP update is restricted to objective index 1"
        )
    if not isinstance(transition, C2SMDPTransition):
        raise TorchAdapterContractError(
            "update_q2f_smdp requires a C2SMDPTransition"
        )
    assert_admission_bound(transition)
    if transition.objective_index != C2_OBJECTIVE_INDEX:
        raise TorchAdapterContractError(
            "C2 SMDP transition is restricted to objective index 1"
        )
    configured_gamma = _finite(
        specialist.config.discount_factor, field="config.discount_factor"
    )
    if not math.isclose(
        configured_gamma,
        float(transition.discount_factor),
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise TorchAdapterContractError(
            "specialist config discount_factor disagrees with C2 transition"
        )


def _masked_target(
    target_network: torch.nn.Module,
    next_states: torch.Tensor,
    next_masks: torch.Tensor,
    reward: torch.Tensor,
    bootstrap_discount: float,
    *,
    done: bool | torch.Tensor = False,
) -> torch.Tensor:
    """Build a masked target without introducing a second discount factor."""

    with torch.no_grad():
        next_values = target_network(next_states)
        next_values[~next_masks] = -1e9
        next_max = next_values.max(dim=1).values
        discount = float(bootstrap_discount)
        if isinstance(done, torch.Tensor):
            terminal_factor = 1.0 - done
        elif done:
            # A terminal transition's contract already carries zero
            # bootstrap discount.  Keeping this explicit prevents a future
            # caller from accidentally making terminal Q values matter.
            terminal_factor = 0.0
        else:
            terminal_factor = 1.0
        return reward + discount * next_max * terminal_factor


@dataclass(frozen=True)
class Q2FSMDPUpdateReceipt:
    """Auditable result of one private Q2F SMDP optimizer step."""

    source_id: str
    source_unit_id: str
    option_id: str
    objective_index: int
    duration: int
    discount_factor: float
    bootstrap_discount: float
    reward_calibration_scale: float
    calibrated_option_return: float
    target: float
    loss: float
    optimizer_steps: int
    specialist_updates: int
    claim_ceiling: str = CLAIM_CEILING


def update_q2f_smdp(
    specialist: ObjectiveSpecialist,
    transition: C2SMDPTransition,
) -> Q2FSMDPUpdateReceipt:
    """Apply one Q2F update from one complete C2 option.

    Validation is complete before any optimizer mutation.  The SMDP target
    uses the transition's already-authoritative ``gamma**4`` discount and a
    masked target network; it never loops over the four primitives and never
    calibrates the option return twice.
    """

    _ensure_q2_specialist(specialist, transition)
    scale = _calibration_scale(specialist.config, C2_OBJECTIVE_INDEX)
    calibrated_return = (
        float(transition.option_return) / scale
        if specialist.config.reward_calibration_enabled
        else float(transition.option_return)
    )
    if not math.isfinite(calibrated_return):
        raise TorchAdapterContractError("calibrated C2 option return must be finite")

    # Keep this private update atomic as well.  There is no durable ledger on
    # Q2F, but a failed optimizer step must not leave a partially updated
    # online network that could later be mistaken for a committed option.
    online_snapshot = copy.deepcopy(specialist.online.state_dict())
    optimizer_snapshot = copy.deepcopy(specialist.optimizer.state_dict())
    updates_before = int(specialist.updates)
    try:
        state = torch.tensor(
            transition.opening_state,
            dtype=torch.float32,
        ).unsqueeze(0)
        action = torch.tensor(
            [transition.action],
            dtype=torch.long,
        ).unsqueeze(1)
        next_state = torch.tensor(
            transition.bootstrap_state,
            dtype=torch.float32,
        ).unsqueeze(0)
        next_mask = torch.tensor(
            transition.bootstrap_mask,
            dtype=torch.bool,
        ).unsqueeze(0)
        reward = torch.tensor([calibrated_return], dtype=torch.float32)
        q_current = specialist.online(state).gather(1, action).squeeze(1)
        # The ordinary post-release/terminal state is not a certified next
        # C2 decision support.  Do not even evaluate target-network logits on
        # it: the frozen target is the observed bounded return itself.
        target = reward.detach().clone()
        loss = specialist.loss_fn(q_current, target)
        assert_finite_loss(loss, objective=C2_OBJECTIVE_INDEX)
        specialist.optimizer.zero_grad()
        loss.backward()
        assert_finite_gradients(
            specialist.online.parameters(), objective=C2_OBJECTIVE_INDEX
        )
        specialist.optimizer.step()
        assert_finite_parameters([specialist.online])
    except Exception:
        specialist.online.load_state_dict(online_snapshot)
        specialist.optimizer.load_state_dict(optimizer_snapshot)
        specialist.updates = updates_before
        raise

    specialist.updates += 1
    return Q2FSMDPUpdateReceipt(
        source_id=transition.source_id,
        source_unit_id=transition.source_unit_id,
        option_id=transition.option_id,
        objective_index=C2_OBJECTIVE_INDEX,
        duration=int(transition.duration),
        discount_factor=float(transition.discount_factor),
        bootstrap_discount=float(transition.bootstrap_discount),
        reward_calibration_scale=float(scale),
        calibrated_option_return=float(calibrated_return),
        target=float(target.detach().item()),
        loss=float(loss.detach().item()),
        optimizer_steps=1,
        specialist_updates=int(specialist.updates),
    )


@dataclass(frozen=True)
class C2OptionAdmission:
    """The atomic option/source-unit receipt stored by :class:`C2OptionLedger`."""

    option_id: str
    source_unit_id: str
    bundle_ids: tuple[str, ...]
    sequence_sha256: str


class C2OptionLedger:
    """Checkpointable at-most-once ledger for a complete C2 option.

    A record contains one option/source-unit and one-to-four constituent
    bundle IDs.  ``preflight`` never mutates.  ``commit`` revalidates all
    identities before changing either set, so a failed admission cannot leave
    a partial four-bundle dose behind.
    """

    # Version 2 binds the monotone hold/release policy.  A V0.3A or otherwise
    # unversioned checkpoint must fail closed instead of being replayed under
    # the V0.3B support-expiry semantics.
    FORMAT_VERSION = 2
    POLICY_VERSION = c2_core.CANDIDATE_VERSION

    def __init__(self) -> None:
        self._records: dict[str, C2OptionAdmission] = {}
        self._seen_bundle_ids: set[str] = set()

    @staticmethod
    def _admission(sequence: C2PrimitiveSequence) -> C2OptionAdmission:
        if not isinstance(sequence, C2PrimitiveSequence):
            raise TorchAdapterContractError(
                "C2 option ledger accepts only C2PrimitiveSequence"
            )
        assert_admission_bound(sequence)
        if sequence.source_id != "C2" or sequence.target_objective != C2_OBJECTIVE_INDEX:
            raise TorchAdapterContractError(
                "C2 option ledger cannot admit a non-C2/non-Q2 sequence"
            )
        bundle_ids = tuple(sequence.constituent_bundle_ids)
        if not 1 <= len(bundle_ids) <= EXPECTED_DURATION:
            raise TorchAdapterContractError(
                f"C2 option must contain 1..{EXPECTED_DURATION} bundle IDs"
            )
        if any(type(value) is not str or not value for value in bundle_ids):
            raise TorchAdapterContractError("C2 bundle IDs must be nonempty strings")
        if len(set(bundle_ids)) != len(bundle_ids):
            raise TorchAdapterContractError("C2 option cannot repeat a bundle ID")
        option_id = sequence.option_id
        source_unit_id = sequence.source_unit_id
        if (
            type(option_id) is not str
            or not option_id
            or type(source_unit_id) is not str
            or not source_unit_id
        ):
            raise TorchAdapterContractError(
                "C2 option and source-unit IDs must be nonempty strings"
            )
        if option_id != source_unit_id:
            raise TorchAdapterContractError(
                "C2 option source-unit identity must equal option_id"
            )
        return C2OptionAdmission(
            option_id=option_id,
            source_unit_id=source_unit_id,
            bundle_ids=bundle_ids,
            sequence_sha256=sequence.sequence_sha256,
        )

    def preflight(self, sequence: C2PrimitiveSequence) -> C2OptionAdmission:
        """Validate a new option without mutating checkpoint state."""

        admission = self._admission(sequence)
        if admission.option_id in self._records:
            raise TorchAdapterContractError(
                f"C2 option was already consumed: {admission.option_id}"
            )
        repeated = sorted(set(admission.bundle_ids) & self._seen_bundle_ids)
        if repeated:
            raise TorchAdapterContractError(
                "C2 bundle was already consumed: " + ",".join(repeated)
            )
        return admission

    def commit(self, sequence: C2PrimitiveSequence) -> C2OptionAdmission:
        """Atomically commit one option and all four bundle IDs."""

        admission = self.preflight(sequence)
        # All checks above happen before either collection changes.
        self._records[admission.option_id] = admission
        self._seen_bundle_ids.update(admission.bundle_ids)
        return admission

    def __len__(self) -> int:
        return len(self._records)

    def state_dict(self) -> dict[str, Any]:
        """Return a JSON/checkpoint-friendly immutable snapshot."""

        records = [
            {
                "option_id": item.option_id,
                "source_unit_id": item.source_unit_id,
                "bundle_ids": list(item.bundle_ids),
                "sequence_sha256": item.sequence_sha256,
            }
            for item in sorted(self._records.values(), key=lambda value: value.option_id)
        ]
        return {
            "format_version": self.FORMAT_VERSION,
            "c2_policy_version": self.POLICY_VERSION,
            "records": records,
            "seen_option_ids": [item["option_id"] for item in records],
            "seen_bundle_ids": sorted(self._seen_bundle_ids),
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        """Validate a checkpoint completely before replacing current state."""

        if not isinstance(state, Mapping):
            raise TypeError("C2 option ledger state must be a mapping")
        if state.get("format_version") != self.FORMAT_VERSION:
            raise ValueError("unsupported C2 option ledger format")
        if state.get("c2_policy_version") != self.POLICY_VERSION:
            raise ValueError("unsupported C2 option ledger policy version")
        raw_records = state.get("records")
        if isinstance(raw_records, (str, bytes)) or not isinstance(raw_records, Sequence):
            raise TypeError("C2 option ledger records must be a sequence")
        new_records: dict[str, C2OptionAdmission] = {}
        new_bundles: set[str] = set()
        for raw in raw_records:
            if not isinstance(raw, Mapping):
                raise TypeError("C2 option ledger record must be a mapping")
            option_id = raw.get("option_id")
            source_unit_id = raw.get("source_unit_id")
            bundle_ids = raw.get("bundle_ids")
            sequence_sha256 = raw.get("sequence_sha256")
            if (
                type(option_id) is not str
                or not option_id
                or type(source_unit_id) is not str
                or not source_unit_id
                or option_id != source_unit_id
            ):
                raise ValueError("C2 option ledger record has invalid option identity")
            if (
                isinstance(bundle_ids, (str, bytes))
                or not isinstance(bundle_ids, Sequence)
                or not 1 <= len(bundle_ids) <= EXPECTED_DURATION
            ):
                raise ValueError(
                    f"C2 option ledger record must contain 1..{EXPECTED_DURATION} bundle IDs"
                )
            normalized_bundles = tuple(bundle_ids)
            if any(type(value) is not str or not value for value in normalized_bundles):
                raise ValueError("C2 option ledger bundle IDs are invalid")
            if len(set(normalized_bundles)) != len(normalized_bundles):
                raise ValueError("C2 option ledger bundle IDs repeat")
            if option_id in new_records or new_bundles.intersection(normalized_bundles):
                raise ValueError("C2 option ledger contains duplicate identity")
            if (
                type(sequence_sha256) is not str
                or len(sequence_sha256) != 64
                or sequence_sha256.lower() != sequence_sha256
                or any(char not in "0123456789abcdef" for char in sequence_sha256)
            ):
                raise ValueError("C2 option ledger sequence hash is invalid")
            admission = C2OptionAdmission(
                option_id=option_id,
                source_unit_id=source_unit_id,
                bundle_ids=normalized_bundles,
                sequence_sha256=sequence_sha256,
            )
            new_records[option_id] = admission
            new_bundles.update(normalized_bundles)

        expected_options = state.get("seen_option_ids")
        expected_bundles = state.get("seen_bundle_ids")
        if (
            isinstance(expected_options, (str, bytes))
            or not isinstance(expected_options, Sequence)
            or tuple(expected_options) != tuple(sorted(new_records))
        ):
            raise ValueError("C2 option ledger seen_option_ids disagree with records")
        if (
            isinstance(expected_bundles, (str, bytes))
            or not isinstance(expected_bundles, Sequence)
            or tuple(expected_bundles) != tuple(sorted(new_bundles))
        ):
            raise ValueError("C2 option ledger seen_bundle_ids disagree with records")
        self._records = new_records
        self._seen_bundle_ids = new_bundles


@dataclass(frozen=True)
class MainC2UpdateReceipt:
    """Receipt for one canonical Main update with a Q2-only C2 blend."""

    mode: str
    updated: bool
    warmup: bool
    source_id: str
    source_unit_id: str
    option_id: str
    target_objective: int
    beta: float
    effective_beta: float
    primitive_count: int
    primitive_loss_mean: float
    main_losses: tuple[float, float, float]
    blended_q2_loss: float
    optimizer_steps_per_objective: tuple[int, int, int]
    canonical_sample_used: bool
    committed: bool
    constituent_bundle_ids: tuple[str, ...]
    claim_ceiling: str = CLAIM_CEILING
    dose_borrowing: bool = False


def _bundle_value(bundle: object, name: str) -> object:
    if hasattr(bundle, name):
        return getattr(bundle, name)
    provenance = getattr(bundle, "provenance", None)
    if isinstance(provenance, Mapping) and name in provenance:
        return provenance[name]
    raise TorchAdapterContractError(f"C2 constituent lacks {name}")


def _validated_focal_rows(main: MODQNTrainer, sequence: C2PrimitiveSequence) -> tuple[dict[str, Any], ...]:
    """Recheck actual arrays at the optimizer boundary, not only hashes."""

    rows: list[dict[str, Any]] = []
    for index, bundle in enumerate(sequence.transitions):
        try:
            states = np.asarray(_bundle_value(bundle, "states"), dtype=np.float32)
            actions = np.asarray(_bundle_value(bundle, "actions"), dtype=np.int64)
            rewards = np.asarray(_bundle_value(bundle, "rewards"), dtype=np.float64)
            next_states = np.asarray(
                _bundle_value(bundle, "next_states"), dtype=np.float32
            )
            masks = np.asarray(_bundle_value(bundle, "masks"), dtype=np.bool_)
            next_masks = np.asarray(
                _bundle_value(bundle, "next_masks"), dtype=np.bool_
            )
            done = _bundle_value(bundle, "done")
            focal_user = int(_bundle_value(bundle, "focal_user"))
        except (TypeError, ValueError, OverflowError) as error:
            raise TorchAdapterContractError(
                f"C2 constituent {index} cannot be converted to arrays"
            ) from error
        if states.ndim != 2 or states.shape[1] != int(main.state_dim):
            raise TorchAdapterContractError(
                f"C2 constituent {index} state width disagrees with Main"
            )
        users = states.shape[0]
        if (
            next_states.shape != states.shape
            or actions.shape != (users,)
            or rewards.shape != (users, 3)
            or masks.shape != (users, int(main.action_dim))
            or next_masks.shape != masks.shape
        ):
            raise TorchAdapterContractError(
                f"C2 constituent {index} has a malformed Main transition shape"
            )
        if not 0 <= focal_user < users:
            raise TorchAdapterContractError(
                f"C2 constituent {index} focal user is outside its arrays"
            )
        if type(done) is not bool:
            raise TorchAdapterContractError(
                f"C2 constituent {index} done must be Boolean"
            )
        action = int(actions[focal_user])
        if action == NO_OP_ACTION or not 0 <= action < int(main.action_dim):
            raise TorchAdapterContractError(
                f"C2 constituent {index} focal action is not executable"
            )
        if not bool(masks[focal_user, action]):
            raise TorchAdapterContractError(
                f"C2 constituent {index} focal action is outside its mask"
            )
        if not done and not bool(next_masks[focal_user].any()):
            raise TorchAdapterContractError(
                f"C2 constituent {index} has no valid nonterminal bootstrap action"
            )
        if (
            not np.all(np.isfinite(states))
            or not np.all(np.isfinite(next_states))
            or not np.all(np.isfinite(rewards))
        ):
            raise TorchAdapterContractError(
                f"C2 constituent {index} contains a non-finite payload"
            )
        rows.append(
            {
                "states": states,
                "actions": actions,
                "rewards": rewards,
                "next_states": next_states,
                "masks": masks,
                "next_masks": next_masks,
                "done": done,
                "focal_user": focal_user,
            }
        )
    if not 1 <= len(rows) <= EXPECTED_DURATION:
        raise TorchAdapterContractError(
            f"C2 Main sequence must expose 1..{EXPECTED_DURATION} rows"
        )
    return tuple(rows)


def _snapshot_main(main: MODQNTrainer) -> tuple[Any, ...]:
    return (
        [copy.deepcopy(net.state_dict()) for net in main.q_nets],
        [copy.deepcopy(optimizer.state_dict()) for optimizer in main.optimizers],
        copy.deepcopy(main._train_rng.bit_generator.state),
    )


def _restore_main(main: MODQNTrainer, snapshot: tuple[Any, ...]) -> None:
    network_states, optimizer_states, rng_state = snapshot
    for network, state in zip(main.q_nets, network_states, strict=True):
        network.load_state_dict(state)
    for optimizer, state in zip(main.optimizers, optimizer_states, strict=True):
        optimizer.load_state_dict(state)
    main._train_rng.bit_generator.state = copy.deepcopy(rng_state)


def _main_batch_tensors(
    main: MODQNTrainer,
) -> tuple[torch.Tensor, ...]:
    """Sample and tensorize exactly the canonical MODQN batch once."""

    (
        states,
        actions,
        rewards,
        next_states,
        _masks,
        next_masks,
        dones,
    ) = main.replay.sample(main.config.batch_size, main._train_rng)
    return (
        torch.tensor(states, dtype=torch.float32, device=main.device),
        torch.tensor(actions, dtype=torch.long, device=main.device).unsqueeze(1),
        torch.tensor(rewards, dtype=torch.float32, device=main.device),
        torch.tensor(next_states, dtype=torch.float32, device=main.device),
        torch.tensor(next_masks, dtype=torch.bool, device=main.device),
        torch.tensor(dones, dtype=torch.float32, device=main.device),
    )


def _canonical_main_losses(
    main: MODQNTrainer,
    batch: tuple[torch.Tensor, ...],
) -> tuple[torch.Tensor, ...]:
    states, actions, rewards, next_states, next_masks, dones = batch
    losses: list[torch.Tensor] = []
    for objective in range(3):
        q_current = main.q_nets[objective](states).gather(1, actions).squeeze(1)
        target = _masked_target(
            main.target_nets[objective],
            next_states,
            next_masks,
            rewards[:, objective],
            float(main.config.discount_factor),
            done=dones,
        )
        # The canonical Main update uses raw replay rewards.  C2 donor
        # calibration is independent and happens only in _primitive_loss.
        loss = main._loss_fn(q_current, target)
        assert_finite_loss(loss, objective=objective)
        losses.append(loss)
    return tuple(losses)


def _primitive_loss(
    main: MODQNTrainer,
    row: Mapping[str, Any],
    *,
    scale: float,
) -> torch.Tensor:
    focal = int(row["focal_user"])
    states = torch.tensor(
        row["states"][focal : focal + 1], dtype=torch.float32, device=main.device
    )
    actions = torch.tensor(
        [int(row["actions"][focal])], dtype=torch.long, device=main.device
    ).unsqueeze(1)
    next_states = torch.tensor(
        row["next_states"][focal : focal + 1],
        dtype=torch.float32,
        device=main.device,
    )
    next_masks = torch.tensor(
        row["next_masks"][focal : focal + 1],
        dtype=torch.bool,
        device=main.device,
    )
    raw_reward = float(row["rewards"][focal, C2_OBJECTIVE_INDEX])
    reward = raw_reward / scale if main.config.reward_calibration_enabled else raw_reward
    reward_t = torch.tensor([reward], dtype=torch.float32, device=main.device)
    done = bool(row["done"])
    q_current = main.q_nets[C2_OBJECTIVE_INDEX](states).gather(1, actions).squeeze(1)
    target = _masked_target(
        main.target_nets[C2_OBJECTIVE_INDEX],
        next_states,
        next_masks,
        reward_t,
        float(main.config.discount_factor),
        done=done,
    )
    loss = main._loss_fn(q_current, target)
    assert_finite_loss(loss, objective=C2_OBJECTIVE_INDEX)
    return loss


def _warmup_receipt(
    sequence: C2PrimitiveSequence,
    beta: float,
) -> MainC2UpdateReceipt:
    return MainC2UpdateReceipt(
        mode="warmup_no_update",
        updated=False,
        warmup=True,
        source_id="C2",
        source_unit_id=sequence.source_unit_id,
        option_id=sequence.option_id,
        target_objective=C2_OBJECTIVE_INDEX,
        beta=beta,
        effective_beta=0.0,
        primitive_count=len(sequence.transitions),
        primitive_loss_mean=0.0,
        main_losses=(0.0, 0.0, 0.0),
        blended_q2_loss=0.0,
        optimizer_steps_per_objective=(0, 0, 0),
        canonical_sample_used=False,
        committed=False,
        constituent_bundle_ids=sequence.constituent_bundle_ids,
    )


def update_main_with_c2_sequence_once(
    main: MODQNTrainer,
    sequence: C2PrimitiveSequence,
    beta: float,
    option_ledger: C2OptionLedger,
) -> MainC2UpdateReceipt:
    """Perform one Q2-only C2 blend on one canonical Main replay sample.

    The warmup check precedes replay sampling and ledger admission.  Once the
    batch is available, all validation and the two-phase ledger preflight are
    complete before mutation.  Network/optimizer/RNG state is restored if
    any optimizer or final commit fails, so a failed attempt does not burn an
    option source unit.
    """

    if not isinstance(main, MODQNTrainer):
        raise TorchAdapterContractError(
            "update_main_with_c2_sequence_once requires a MODQNTrainer"
        )
    if not isinstance(sequence, C2PrimitiveSequence):
        raise TorchAdapterContractError(
            "Main C2 update requires a C2PrimitiveSequence"
        )
    if sequence.source_id != "C2" or sequence.target_objective != C2_OBJECTIVE_INDEX:
        raise TorchAdapterContractError("Main C2 update is restricted to Q2")
    assert_admission_bound(sequence)
    beta_value = _beta(beta)
    if not isinstance(option_ledger, C2OptionLedger):
        raise TorchAdapterContractError(
            "Main C2 update requires a checkpointable C2OptionLedger"
        )
    rows = _validated_focal_rows(main, sequence)

    # Warmup must not sample RNG, run a forward pass, or consume the option.
    if len(main.replay) < int(main.config.batch_size):
        return _warmup_receipt(sequence, beta_value)

    pending = option_ledger.preflight(sequence)
    ledger_snapshot = copy.deepcopy(option_ledger.state_dict())
    snapshot = _snapshot_main(main)
    try:
        batch = _main_batch_tensors(main)
        canonical_losses = _canonical_main_losses(main, batch)
        scale = _calibration_scale(main.config, C2_OBJECTIVE_INDEX)
        primitive_losses = tuple(
            _primitive_loss(main, row, scale=scale) for row in rows
        )
        primitive_mean = torch.stack(primitive_losses).mean()
        assert_finite_loss(primitive_mean, objective=C2_OBJECTIVE_INDEX)
        blended_q2 = (
            (1.0 - beta_value) * canonical_losses[C2_OBJECTIVE_INDEX]
            + beta_value * primitive_mean
        )
        assert_finite_loss(blended_q2, objective=C2_OBJECTIVE_INDEX)
        update_losses = (
            canonical_losses[0],
            blended_q2,
            canonical_losses[2],
        )

        for objective, loss in enumerate(update_losses):
            main.optimizers[objective].zero_grad()
            loss.backward()
            assert_finite_gradients(main.q_nets[objective].parameters(), objective=objective)
            main.optimizers[objective].step()
        assert_finite_parameters(main.q_nets)

        # The ledger is deliberately the last mutating boundary.
        committed = option_ledger.commit(sequence)
        if committed != pending:
            raise TorchAdapterContractError("C2 ledger commit changed its preflight receipt")
    except Exception:
        _restore_main(main, snapshot)
        option_ledger.load_state_dict(ledger_snapshot)
        raise

    main_losses = tuple(float(loss.detach().item()) for loss in canonical_losses)
    return MainC2UpdateReceipt(
        mode="canonical_main_plus_c2_q2_donor",
        updated=True,
        warmup=False,
        source_id="C2",
        source_unit_id=sequence.source_unit_id,
        option_id=sequence.option_id,
        target_objective=C2_OBJECTIVE_INDEX,
        beta=beta_value,
        effective_beta=beta_value,
        primitive_count=EXPECTED_DURATION,
        primitive_loss_mean=float(primitive_mean.detach().item()),
        main_losses=main_losses,
        blended_q2_loss=float(blended_q2.detach().item()),
        optimizer_steps_per_objective=(1, 1, 1),
        canonical_sample_used=True,
        committed=True,
        constituent_bundle_ids=pending.bundle_ids,
    )


__all__ = [
    "C2OptionAdmission",
    "C2OptionLedger",
    "CLAIM_CEILING",
    "MainC2UpdateReceipt",
    "Q2FSMDPUpdateReceipt",
    "TorchAdapterContractError",
    "update_main_with_c2_sequence_once",
    "update_q2f_smdp",
]
