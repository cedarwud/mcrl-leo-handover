"""Single-sample, single-step Main carrier for C1/C2/C3.

The frozen ``smc_er_core.update_main_with_role_targeted_donors`` API accepts
one AtomicBundle per source.  C2 V0.3 is different: its Main source unit is a
four-bundle ``C2PrimitiveSequence`` whose donor loss must be the *mean* of
four focal primitive losses.  Calling the old carrier and the C2-only torch
adapter in succession would consume two replay samples and take two rounds of
Main optimizer steps.  This append-only carrier is the explicit combined seam:

* one canonical Main replay sample is shared by all three objective losses;
* C1 contributes only to Q1, C2 contributes only to Q2, and C3 contributes
  only to Q3;
* each present source is blended once as ``(1-beta)L_main + beta L_source``;
* C2's four primitive losses are reduced by mean before that one blend;
* one optimizer step is taken for each Main objective;
* the C1/C3 consumed-bundle ledger and C2 option ledger commit only after all
  steps, with network, optimizer, RNG, and ledger rollback on any failure.

This module does not alter ``src/mcrl`` or the frozen short-episode carrier,
does not update specialists, and makes no efficacy or EE claim.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
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

import c2_temporal_fork_torch_adapter as c2_torch
from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NO_OP_ACTION
from mcrl.runtime.finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)
from smc_er_core import AtomicBundle, ConsumedBundleLedger


ROLE_TO_OBJECTIVE = {"C1": 0, "C2": 1, "C3": 2}
SOURCE_IDS = ("C1", "C2", "C3")
FROZEN_MAX_SOURCE_AGE_BLOCKS = {"C1": 0, "C2": 0, "C3": 0}
CLAIM_CEILING = (
    "C1/C2/C3 combined Main optimizer seam only; no training result or EE efficacy"
)


class CombinedCarrierContractError(c2_torch.TorchAdapterContractError):
    """The combined source-unit contract was not satisfied."""


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.number)
    ):
        raise CombinedCarrierContractError(f"{field} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted):
        raise CombinedCarrierContractError(f"{field} must be finite")
    return converted


def _beta(value: object) -> float:
    result = _finite(value, field="beta")
    if not 0.0 <= result < 1.0:
        raise CombinedCarrierContractError("beta must satisfy 0 <= beta < 1")
    return result


def _objective(source: str) -> int:
    try:
        return ROLE_TO_OBJECTIVE[source]
    except (KeyError, TypeError) as error:
        raise CombinedCarrierContractError(
            f"unknown catfish source {source!r}"
        ) from error


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise CombinedCarrierContractError(
            f"{field} must be a nonnegative exact integer"
        )
    return value


def _bundle_field(bundle: AtomicBundle, name: str) -> Any:
    if hasattr(bundle, name):
        return getattr(bundle, name)
    provenance = getattr(bundle, "provenance", None)
    if isinstance(provenance, Mapping) and name in provenance:
        return provenance[name]
    raise CombinedCarrierContractError(f"bundle lacks {name} authority")


def _validate_bundle(
    main: MODQNTrainer,
    bundle: object,
    *,
    source: str,
) -> tuple[AtomicBundle, np.ndarray]:
    """Validate source/objective/focal authority before sampling Main replay."""

    if not isinstance(bundle, AtomicBundle):
        raise CombinedCarrierContractError(
            f"{source} source must be an smc_er_core.AtomicBundle"
        )
    if bundle.source_id != source:
        raise CombinedCarrierContractError(
            f"{source} bundle source_id is {bundle.source_id!r}"
        )
    if bundle.behavior_probabilities is None:
        raise CombinedCarrierContractError(
            f"{source} bundle lacks behavior-probability authority"
        )
    if source == "C1":
        if bundle.focal_user is not None:
            raise CombinedCarrierContractError("C1 is a joint source and cannot have focal_user")
    elif source == "C3":
        if bundle.focal_user is None:
            raise CombinedCarrierContractError("C3 requires focal_user authority")
        if type(bundle.focal_user) is not int:
            raise CombinedCarrierContractError("C3 focal_user must be an exact integer")
    else:  # pragma: no cover - guarded by the public source list
        _objective(source)

    if bundle.states.ndim != 2 or bundle.states.shape[1] != int(main.state_dim):
        raise CombinedCarrierContractError(
            f"{source} state width disagrees with Main"
        )
    if bundle.masks.shape != (bundle.users, int(main.action_dim)):
        raise CombinedCarrierContractError(
            f"{source} mask width disagrees with Main"
        )
    rows = bundle.admissible_rows()
    if source == "C3":
        focal = int(bundle.focal_user)
        if not np.any(rows == focal):
            raise CombinedCarrierContractError(
                "C3 focal row is not an admissible transition"
            )
        rows = np.asarray([focal], dtype=np.int64)
    if rows.size == 0:
        raise CombinedCarrierContractError(
            f"{source} bundle has no admissible rows; refusing to burn a source unit"
        )
    return bundle, np.asarray(rows, dtype=np.int64)


def _bundle_lineage(bundle: object, *, source: str) -> tuple[int, int]:
    block_id = _exact_nonnegative_int(
        _bundle_field(bundle, "block_id"), field=f"{source}.block_id"
    )
    policy_version = _exact_nonnegative_int(
        _bundle_field(bundle, "source_policy_version"),
        field=f"{source}.source_policy_version",
    )
    return block_id, policy_version


def _c2_lineage(
    sequence: c2_torch.C2PrimitiveSequence,
) -> tuple[int, int]:
    values = tuple(
        _bundle_lineage(bundle, source="C2") for bundle in sequence.transitions
    )
    if not values or len(set(values)) != 1:
        raise CombinedCarrierContractError(
            "all C2 constituents must share one source block and policy version"
        )
    return values[0]


def _validate_c2(
    main: MODQNTrainer,
    sequence: object,
) -> tuple[c2_torch.C2PrimitiveSequence, tuple[dict[str, Any], ...]]:
    if not isinstance(sequence, c2_torch.C2PrimitiveSequence):
        raise CombinedCarrierContractError(
            "C2 source must be an admitted C2PrimitiveSequence"
        )
    if sequence.source_id != "C2" or sequence.target_objective != 1:
        raise CombinedCarrierContractError("C2 source must target Q2 only")
    if type(sequence.focal_user) is not int or sequence.focal_user < 0:
        raise CombinedCarrierContractError("C2 focal_user must be an exact nonnegative integer")
    # Admission is a sealed authority boundary.  Hash/shape checks alone must
    # not let a direct or failed-plan object reach Main, especially during
    # warmup where no later ledger preflight would run.
    try:
        c2_torch.assert_admission_bound(sequence)
    except Exception as error:
        raise CombinedCarrierContractError(
            "C2 primitive sequence lacks a valid admission proof"
        ) from error
    try:
        rows = c2_torch._validated_focal_rows(main, sequence)
    except Exception as error:
        raise CombinedCarrierContractError(
            "C2 primitive sequence is not Main-compatible"
        ) from error
    for index, row in enumerate(rows):
        if int(row["focal_user"]) != sequence.focal_user:
            raise CombinedCarrierContractError(
                f"C2 focal authority disagrees at primitive offset {index}"
            )
    return sequence, rows


def _ledger_seen_ids(ledger: object | None) -> set[str]:
    if ledger is None:
        return set()
    state = ledger.state_dict()
    values = state.get("seen_bundle_ids", ())
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise CombinedCarrierContractError("bundle ledger state is malformed")
    return {str(value) for value in values}


def _c2_seen_ids(ledger: c2_torch.C2OptionLedger | None) -> set[str]:
    if ledger is None:
        return set()
    state = ledger.state_dict()
    values = state.get("seen_bundle_ids", ())
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise CombinedCarrierContractError("C2 option ledger state is malformed")
    return {str(value) for value in values}


def _snapshot_main(main: MODQNTrainer) -> tuple[Any, ...]:
    gradients: list[dict[str, torch.Tensor | None]] = []
    for network in main.q_nets:
        gradients.append(
            {
                name: None if parameter.grad is None else parameter.grad.detach().cpu().clone()
                for name, parameter in network.named_parameters()
            }
        )
    return (
        [copy.deepcopy(network.state_dict()) for network in main.q_nets],
        [copy.deepcopy(optimizer.state_dict()) for optimizer in main.optimizers],
        copy.deepcopy(main._train_rng.bit_generator.state),
        gradients,
    )


def _restore_main(main: MODQNTrainer, snapshot: tuple[Any, ...]) -> None:
    network_states, optimizer_states, rng_state, gradients = snapshot
    for network, state in zip(main.q_nets, network_states, strict=True):
        network.load_state_dict(state)
    for optimizer, state in zip(main.optimizers, optimizer_states, strict=True):
        optimizer.load_state_dict(state)
    main._train_rng.bit_generator.state = copy.deepcopy(rng_state)
    for network, saved in zip(main.q_nets, gradients, strict=True):
        for name, parameter in network.named_parameters():
            gradient = saved[name]
            parameter.grad = None if gradient is None else gradient.to(parameter.device)


def _atomic_donor_loss(
    main: MODQNTrainer,
    bundle: AtomicBundle,
    rows: np.ndarray,
    *,
    objective: int,
    scale: float,
) -> torch.Tensor:
    states = torch.tensor(bundle.states[rows], dtype=torch.float32, device=main.device)
    actions = torch.tensor(bundle.actions[rows], dtype=torch.long, device=main.device).unsqueeze(1)
    next_states = torch.tensor(bundle.next_states[rows], dtype=torch.float32, device=main.device)
    next_masks = torch.tensor(bundle.next_masks[rows], dtype=torch.bool, device=main.device)
    natural_rewards = bundle.rewards[rows, objective]
    rewards = natural_rewards / scale if main.config.reward_calibration_enabled else natural_rewards
    reward_t = torch.tensor(rewards, dtype=torch.float32, device=main.device)
    done = torch.full((rows.size,), float(bundle.done), dtype=torch.float32, device=main.device)
    q_current = main.q_nets[objective](states).gather(1, actions).squeeze(1)
    with torch.no_grad():
        q_next = main.target_nets[objective](next_states)
        q_next[~next_masks] = -1e9
        target = reward_t + float(main.config.discount_factor) * q_next.max(dim=1).values * (1.0 - done)
    loss = main._loss_fn(q_current, target)
    assert_finite_loss(loss, objective=objective)
    return loss


def _c2_donor_mean(
    main: MODQNTrainer,
    rows: Sequence[Mapping[str, Any]],
    *,
    scale: float,
) -> torch.Tensor:
    primitive_losses = tuple(
        c2_torch._primitive_loss(main, row, scale=scale) for row in rows
    )
    if not 1 <= len(primitive_losses) <= 4:
        raise CombinedCarrierContractError(
            "C2 donor must contain one to four real primitive losses"
        )
    mean = torch.stack(primitive_losses).mean()
    assert_finite_loss(mean, objective=1)
    return mean


def _canonical_main_loss(
    main: MODQNTrainer,
    batch: tuple[torch.Tensor, ...],
    objective: int,
) -> torch.Tensor:
    """Build one canonical objective loss in the frozen MODQN order."""

    states, actions, rewards, next_states, next_masks, dones = batch
    q_current = main.q_nets[objective](states).gather(1, actions).squeeze(1)
    target = c2_torch._masked_target(
        main.target_nets[objective],
        next_states,
        next_masks,
        rewards[:, objective],
        float(main.config.discount_factor),
        done=dones,
    )
    loss = main._loss_fn(q_current, target)
    assert_finite_loss(loss, objective=objective)
    return loss


@dataclass(frozen=True)
class CombinedMainUpdateReceipt:
    """Auditable result of one combined Main update."""

    mode: str
    updated: bool
    warmup: bool
    beta: float
    active_sources: tuple[str, ...]
    source_to_objective: Mapping[str, int]
    effective_beta: Mapping[str, float]
    canonical_main_losses: tuple[float, float, float]
    donor_losses: Mapping[str, float]
    blended_losses: tuple[float, float, float]
    c2_primitive_count: int
    canonical_sample_used: bool
    canonical_sample_count: int
    optimizer_steps_per_objective: tuple[int, int, int]
    committed_c1_c3_bundle_ids: tuple[str, ...]
    committed_c2_bundle_ids: tuple[str, ...]
    committed_c2_option_id: str | None
    source_block_id: Mapping[str, int]
    source_policy_version: Mapping[str, int]
    consumer_block_id: int | None
    source_age_blocks: Mapping[str, int]
    max_source_age_blocks: Mapping[str, int]
    claim_ceiling: str = CLAIM_CEILING
    dose_borrowing: bool = False


def _warmup_receipt(
    *,
    beta: float,
    active_sources: Sequence[str],
    c2_sequence: c2_torch.C2PrimitiveSequence | None,
    lineages: Mapping[str, tuple[int, int]],
    consumer_block_id: int,
    source_ages: Mapping[str, int],
) -> CombinedMainUpdateReceipt:
    return CombinedMainUpdateReceipt(
        mode="warmup_no_update",
        updated=False,
        warmup=True,
        beta=beta,
        active_sources=tuple(active_sources),
        source_to_objective={source: ROLE_TO_OBJECTIVE[source] for source in SOURCE_IDS},
        effective_beta={source: 0.0 for source in SOURCE_IDS},
        canonical_main_losses=(0.0, 0.0, 0.0),
        donor_losses={},
        blended_losses=(0.0, 0.0, 0.0),
        c2_primitive_count=(
            0 if c2_sequence is None else len(c2_sequence.transitions)
        ),
        canonical_sample_used=False,
        canonical_sample_count=0,
        optimizer_steps_per_objective=(0, 0, 0),
        committed_c1_c3_bundle_ids=(),
        committed_c2_bundle_ids=(),
        committed_c2_option_id=None,
        source_block_id={source: value[0] for source, value in lineages.items()},
        source_policy_version={
            source: value[1] for source, value in lineages.items()
        },
        consumer_block_id=consumer_block_id,
        source_age_blocks=dict(source_ages),
        max_source_age_blocks=dict(FROZEN_MAX_SOURCE_AGE_BLOCKS),
    )


def update_main_with_combined_carrier(
    main: MODQNTrainer,
    *,
    c1_bundle: AtomicBundle | None = None,
    c2_sequence: c2_torch.C2PrimitiveSequence | None = None,
    c3_bundle: AtomicBundle | None = None,
    beta: float = 0.25,
    consumed_ledger: ConsumedBundleLedger | None = None,
    c2_option_ledger: c2_torch.C2OptionLedger | None = None,
    consumer_block_id: int | None = None,
) -> CombinedMainUpdateReceipt:
    """Apply all present catfish donors in one canonical Main update.

    ``None`` means that source is absent for this update.  C1 and C3 share the
    existing consumed-bundle ledger; C2 uses its four-bundle option ledger.
    Both ledgers are snapshotted and restored together with Main state.
    """

    if not isinstance(main, MODQNTrainer):
        raise CombinedCarrierContractError("combined carrier requires a MODQNTrainer")
    beta_value = _beta(beta)
    if consumer_block_id is not None and (
        type(consumer_block_id) is not int or consumer_block_id < 0
    ):
        raise CombinedCarrierContractError("consumer_block_id must be nonnegative")

    active: list[str] = []
    c1_rows: tuple[AtomicBundle, np.ndarray] | None = None
    c3_rows: tuple[AtomicBundle, np.ndarray] | None = None
    c2_rows: tuple[c2_torch.C2PrimitiveSequence, tuple[dict[str, Any], ...]] | None = None
    if c1_bundle is not None:
        c1_rows = _validate_bundle(main, c1_bundle, source="C1")
        active.append("C1")
    if c2_sequence is not None:
        c2_rows = _validate_c2(main, c2_sequence)
        active.append("C2")
    if c3_bundle is not None:
        c3_rows = _validate_bundle(main, c3_bundle, source="C3")
        active.append("C3")

    if not active:
        # This is the exact frozen MODQN baseline path, including its replay
        # sampling order, loss construction, and optimizer schedule.
        had_batch = len(main.replay) >= int(main.config.batch_size)
        losses = main.update()
        return CombinedMainUpdateReceipt(
            mode="exact_baseline_delegate",
            updated=had_batch,
            warmup=not had_batch,
            beta=beta_value,
            active_sources=(),
            source_to_objective={source: ROLE_TO_OBJECTIVE[source] for source in SOURCE_IDS},
            effective_beta={source: 0.0 for source in SOURCE_IDS},
            canonical_main_losses=tuple(float(value) for value in losses),
            donor_losses={},
            blended_losses=tuple(float(value) for value in losses),
            c2_primitive_count=0,
            canonical_sample_used=had_batch,
            canonical_sample_count=1 if had_batch else 0,
            optimizer_steps_per_objective=(1, 1, 1) if had_batch else (0, 0, 0),
            committed_c1_c3_bundle_ids=(),
            committed_c2_bundle_ids=(),
            committed_c2_option_id=None,
            source_block_id={},
            source_policy_version={},
            consumer_block_id=None,
            source_age_blocks={},
            max_source_age_blocks=dict(FROZEN_MAX_SOURCE_AGE_BLOCKS),
        )

    if c1_rows is not None or c3_rows is not None:
        if not isinstance(consumed_ledger, ConsumedBundleLedger):
            raise CombinedCarrierContractError(
                "C1/C3 source requires a consumed-bundle ledger"
            )
    if c2_rows is not None and not isinstance(c2_option_ledger, c2_torch.C2OptionLedger):
        raise CombinedCarrierContractError("C2 source requires a C2 option ledger")

    if consumer_block_id is None:
        raise CombinedCarrierContractError(
            "active donors require explicit consumer_block_id authority"
        )
    resolved_consumer_block = _exact_nonnegative_int(
        consumer_block_id, field="consumer_block_id"
    )
    lineages: dict[str, tuple[int, int]] = {}
    if c1_rows is not None:
        lineages["C1"] = _bundle_lineage(c1_rows[0], source="C1")
    if c2_rows is not None:
        lineages["C2"] = _c2_lineage(c2_rows[0])
    if c3_rows is not None:
        lineages["C3"] = _bundle_lineage(c3_rows[0], source="C3")
    source_ages: dict[str, int] = {}
    for source, (source_block, _policy_version) in lineages.items():
        age = resolved_consumer_block - source_block
        if age < 0:
            raise CombinedCarrierContractError(
                f"{source} source bundle comes from a future consumer block"
            )
        maximum = FROZEN_MAX_SOURCE_AGE_BLOCKS[source]
        if age > maximum:
            raise CombinedCarrierContractError(
                f"{source} source age {age} exceeds frozen maximum {maximum}"
            )
        source_ages[source] = age

    c1_c3_bundles = tuple(
        item[0] for item in (c1_rows, c3_rows) if item is not None
    )
    c1_c3_ids = tuple(bundle.bundle_id for bundle in c1_c3_bundles)
    c2_ids = () if c2_rows is None else tuple(c2_rows[0].constituent_bundle_ids)
    all_ids = c1_c3_ids + c2_ids
    if len(all_ids) != len(set(all_ids)):
        raise CombinedCarrierContractError("one bundle cannot be consumed by two combined sources")
    if set(c1_c3_ids) & _c2_seen_ids(c2_option_ledger):
        raise CombinedCarrierContractError("C1/C3 bundle is already consumed by the C2 option ledger")
    if set(c2_ids) & _ledger_seen_ids(consumed_ledger):
        raise CombinedCarrierContractError("C2 bundle is already consumed by the C1/C3 ledger")
    # Complete contract checks happen before the warmup return.  Warmup does
    # not preflight/consume either ledger and does not consume Main RNG.
    if len(main.replay) < int(main.config.batch_size):
        return _warmup_receipt(
            beta=beta_value,
            active_sources=active,
            c2_sequence=None if c2_rows is None else c2_rows[0],
            lineages=lineages,
            consumer_block_id=resolved_consumer_block,
            source_ages=source_ages,
        )

    assert consumed_ledger is None or isinstance(consumed_ledger, ConsumedBundleLedger)
    assert c2_option_ledger is None or isinstance(c2_option_ledger, c2_torch.C2OptionLedger)
    pending_c1_c3 = () if consumed_ledger is None else consumed_ledger.preflight(c1_c3_bundles)
    pending_c2 = () if c2_option_ledger is None or c2_rows is None else c2_option_ledger.preflight(c2_rows[0])
    main_snapshot = _snapshot_main(main)
    ledger_snapshot = None if consumed_ledger is None else copy.deepcopy(consumed_ledger.state_dict())
    c2_ledger_snapshot = None if c2_option_ledger is None else copy.deepcopy(c2_option_ledger.state_dict())

    try:
        # Exactly one call to canonical replay.sample, shared by all three
        # Main objective losses.
        batch = c2_torch._main_batch_tensors(main)
        scale_by_objective = {
            objective: c2_torch._calibration_scale(main.config, objective)
            for objective in range(3)
        }
        canonical_losses: list[torch.Tensor] = []
        donor_tensors: dict[str, torch.Tensor] = {}
        blended: list[torch.Tensor] = []
        for source, objective in ROLE_TO_OBJECTIVE.items():
            canonical_loss = _canonical_main_loss(main, batch, objective)
            canonical_losses.append(canonical_loss)
            if source == "C1" and c1_rows is not None:
                donor_tensors[source] = _atomic_donor_loss(
                    main,
                    c1_rows[0],
                    c1_rows[1],
                    objective=objective,
                    scale=scale_by_objective[objective],
                )
            elif source == "C2" and c2_rows is not None:
                donor_tensors[source] = _c2_donor_mean(
                    main,
                    c2_rows[1],
                    scale=scale_by_objective[objective],
                )
            elif source == "C3" and c3_rows is not None:
                donor_tensors[source] = _atomic_donor_loss(
                    main,
                    c3_rows[0],
                    c3_rows[1],
                    objective=objective,
                    scale=scale_by_objective[objective],
                )
            loss = (
                (1.0 - beta_value) * canonical_loss
                + beta_value * donor_tensors[source]
                if source in donor_tensors
                else canonical_loss
            )
            assert_finite_loss(loss, objective=objective)
            blended.append(loss)
            main.optimizers[objective].zero_grad()
            loss.backward()
            assert_finite_gradients(main.q_nets[objective].parameters(), objective=objective)
            main.optimizers[objective].step()
        assert_finite_parameters(main.q_nets)

        committed_c1_c3 = () if consumed_ledger is None else consumed_ledger.commit(pending_c1_c3)
        committed_c2 = () if c2_option_ledger is None or c2_rows is None else c2_option_ledger.commit(c2_rows[0]).bundle_ids
    except Exception:
        _restore_main(main, main_snapshot)
        if consumed_ledger is not None and ledger_snapshot is not None:
            consumed_ledger.load_state_dict(ledger_snapshot)
        if c2_option_ledger is not None and c2_ledger_snapshot is not None:
            c2_option_ledger.load_state_dict(c2_ledger_snapshot)
        raise

    return CombinedMainUpdateReceipt(
        mode="canonical_main_plus_combined_role_targeted_donors",
        updated=True,
        warmup=False,
        beta=beta_value,
        active_sources=tuple(active),
        source_to_objective={source: ROLE_TO_OBJECTIVE[source] for source in SOURCE_IDS},
        effective_beta={source: beta_value if source in donor_tensors else 0.0 for source in SOURCE_IDS},
        canonical_main_losses=tuple(float(loss.detach().item()) for loss in canonical_losses),
        donor_losses={source: float(loss.detach().item()) for source, loss in donor_tensors.items()},
        blended_losses=tuple(float(loss.detach().item()) for loss in blended),
        c2_primitive_count=(
            0 if c2_rows is None else len(c2_rows[0].transitions)
        ),
        canonical_sample_used=True,
        canonical_sample_count=1,
        optimizer_steps_per_objective=(1, 1, 1),
        committed_c1_c3_bundle_ids=tuple(committed_c1_c3),
        committed_c2_bundle_ids=tuple(committed_c2),
        committed_c2_option_id=None if c2_rows is None else c2_rows[0].option_id,
        source_block_id={source: value[0] for source, value in lineages.items()},
        source_policy_version={
            source: value[1] for source, value in lineages.items()
        },
        consumer_block_id=resolved_consumer_block,
        source_age_blocks=source_ages,
        max_source_age_blocks=dict(FROZEN_MAX_SOURCE_AGE_BLOCKS),
    )


# Names are intentionally explicit aliases for downstream runner drafts.
update_main_with_all_catfish_once = update_main_with_combined_carrier
update_main_with_c1_c2_c3_once = update_main_with_combined_carrier


__all__ = [
    "CLAIM_CEILING",
    "CombinedCarrierContractError",
    "CombinedMainUpdateReceipt",
    "FROZEN_MAX_SOURCE_AGE_BLOCKS",
    "ROLE_TO_OBJECTIVE",
    "update_main_with_all_catfish_once",
    "update_main_with_c1_c2_c3_once",
    "update_main_with_combined_carrier",
]
