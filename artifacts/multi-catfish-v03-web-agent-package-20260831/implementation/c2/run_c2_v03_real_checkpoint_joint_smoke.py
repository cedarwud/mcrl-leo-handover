#!/usr/bin/env python3
"""Bounded real-checkpoint C2 V0.3 selection-to-transaction smoke.

The existing ``run_c2_v03_real_backend_smoke.py`` proves that a real trained
Main checkpoint can produce a complete C2 option, but it intentionally stops
before replay warm-up and the optimizer seam.  This companion harness closes
that last bounded engineering gap:

* load the verified 9000-episode Main checkpoint, including its optimizers;
* populate Main replay only from real canonical environment transitions;
* find one real anchor and seal the complete candidate schedule, including
  failed/support-rejected/contract-error rows;
* require K>=2, then execute exactly one selection -> option-runner -> joint
  transaction path.

This file is opt-in.  Running it without ``--execute`` only prints a plan and
cannot load the checkpoint, step an environment, update a network, or write an
artifact.  Even an execution PASS is a mechanism/feasibility receipt, never an
EE, Chapter-5, novelty, or deployment claim.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STAGE0 = HERE.parent / "catfish-stage0"
SMC = HERE.parent / "smc-er-short-ep"
for _path in (HERE, STAGE0, SMC, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import c2_temporal_fork_core as core  # noqa: E402
import c2_temporal_fork_joint_transaction as joint  # noqa: E402
import c2_temporal_fork_learning_adapter as learning  # noqa: E402
import c2_temporal_fork_option_runner as option_runner  # noqa: E402
import c2_temporal_fork_selection as selection  # noqa: E402
import c2_temporal_fork_torch_adapter as torch_adapter  # noqa: E402
import c2_temporal_fork_training_step as training_step  # noqa: E402
import c2_temporal_fork_trainer_backend as backend  # noqa: E402
import run_short_ep as legacy  # noqa: E402
import scripts.run_head_pivotality_probe as checkpoint_loader  # noqa: E402
from mcrl.env.action_contract import Association, is_no_op  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    assert_ephemeris_matches_record,
)
from smc_er_core import ConsumedBundleLedger, ObjectiveSpecialist  # noqa: E402


SCHEMA = "c2-v03-real-checkpoint-joint-smoke-v1"
CLAIM_CEILING = (
    "one bounded real-checkpoint C2 V0.3 selection/option-runner/Q2F-Main "
    "joint-transaction mechanics receipt only; no EE efficacy, Chapter-5 "
    "result, novelty, or deployment authorization"
)
DEFAULT_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
DEFAULT_CHECKPOINT_DIR = (
    REPO / "artifacts" / "training-2026-08-25-rerun01" / "main"
)
DEFAULT_TLE_ROOT = Path("/tmp/mcrl-tle-frozen-20260820-v1")
DEFAULT_OUTPUT = (
    REPO / ".scratch" / "c2-v03" / "real-checkpoint-joint-smoke-20260829.json"
)
DEFAULT_ANCHOR_SEED = 2026082801
DEFAULT_PREFILL_SEED = 2026082991
DEFAULT_SPECIALIST_SEED = 2026082997
MAX_ANCHOR_STEPS = 6
MAX_PREFILL_EPISODES = 24


class SmokeGateError(RuntimeError):
    """A bounded smoke gate could not be closed without weakening a contract."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _network_digest(trainer: Any) -> str:
    """Hash all three Main online heads in the same order as the C2 seam."""

    digest = hashlib.sha256()
    for objective, network in enumerate(trainer.q_nets):
        for name, tensor in sorted(network.state_dict().items()):
            digest.update(f"{objective}:{name}".encode("utf-8"))
            digest.update(np.asarray(tensor.detach().cpu()).tobytes(order="C"))
    return digest.hexdigest()


def _specialist_network_digest(specialist: ObjectiveSpecialist) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(specialist.online.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(np.asarray(tensor.detach().cpu()).tobytes(order="C"))
    return digest.hexdigest()


def _hash_array(digest: Any, value: Any) -> None:
    array = np.ascontiguousarray(np.asarray(value))
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(json.dumps(list(array.shape), separators=(",", ":")).encode("ascii"))
    digest.update(array.tobytes(order="C"))


def _hash_replay_row(
    digest: Any,
    *,
    state: Any,
    action: int,
    reward: Any,
    next_state: Any,
    mask: Any,
    next_mask: Any,
    done: bool,
) -> None:
    """Add one exact stored Main row to the prefill lineage digest."""

    for value in (state, reward, next_state, mask, next_mask):
        _hash_array(digest, value)
    digest.update(str(int(action)).encode("ascii"))
    digest.update(b"1" if bool(done) else b"0")


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, tuple):
        return list(value)
    if hasattr(value, "value") and isinstance(value.value, str):
        return value.value
    return str(value)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _plan_payload(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "NOT_RUN",
        "execution_required": "pass --execute after root review",
        "would_load_checkpoint": str(args.checkpoint_dir / "final-checkpoint.pt"),
        "would_prefill_main_replay_from": "real canonical environment transitions only",
        "would_require": "K>=2 complete candidate support",
        "would_execute": "exactly one selected option and exactly one joint transaction",
        "heavy_training": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _departure_users(environment: Any, main_physical: Sequence[Any]) -> list[int]:
    previous = getattr(
        getattr(environment, "environment", None), "_previous_association", ()
    )
    result: list[int] = []
    for uid, (incumbent, physical) in enumerate(
        zip(previous, main_physical, strict=True)
    ):
        if (
            isinstance(incumbent, Association)
            and physical is not None
            and tuple(physical)
            != (int(incumbent.norad_id), int(incumbent.cell_id))
        ):
            result.append(uid)
    return result


def _prefill_main_replay(
    trainer: Any,
    environment: Any,
    *,
    seed: int,
    target_rows: int,
    checkpoint_episode: int,
) -> dict[str, Any]:
    """Fill Main replay with only real canonical Main environment rows."""

    if target_rows < 1:
        raise SmokeGateError("Main replay prefill target must be positive")
    before = len(trainer.replay)
    if before != 0:
        raise SmokeGateError(
            "verified final policy checkpoint unexpectedly contains Main replay rows"
        )

    env_rng, mobility_rng, _action_rng, _perturb_rng = checkpoint_loader._evaluation_rngs(
        seed
    )
    trajectory = legacy.Trajectory(environment, env_rng, mobility_rng)
    frozen_main = legacy.FrozenMainComparator.from_main(trainer)
    lineage_digest = hashlib.sha256()
    environment_steps = 0
    episode_count = 0
    accepted_rows = 0
    accepted_by_step: list[int] = []

    while len(trainer.replay) < target_rows:
        if episode_count >= MAX_PREFILL_EPISODES:
            raise SmokeGateError(
                "real canonical Main replay prefill exceeded bounded episode budget"
            )
        trajectory.reset()
        for step_index in range(int(environment.config.steps_per_episode)):
            if trajectory.states is None or trajectory.masks is None:
                raise SmokeGateError("prefill trajectory was not reset")
            encoded = trainer.encode_states(trajectory.states)
            # Greedy Main is a real policy action and does not consume the
            # trainer's training RNG while we are only constructing replay.
            actions = legacy.main_greedy_actions(
                frozen_main, encoded, trajectory.masks
            )
            probabilities = np.ones(len(actions), dtype=np.float64)
            result = trajectory.environment.step(actions, trajectory.env_rng)
            outcome = trajectory.environment.last_outcome
            next_encoded = trainer.encode_states(result.user_states)
            bundle = legacy._bundle(
                arm="real-checkpoint-prefill",
                train_seed=int(trainer.train_seed),
                source="Main",
                policy_version=int(checkpoint_episode),
                episode=episode_count,
                step_index=step_index,
                encoded=encoded,
                actions=actions,
                outcome=outcome,
                next_encoded=next_encoded,
                masks=trajectory.masks,
                next_masks=result.action_masks,
                focal_user=None,
                specialist_rewards=None,
                probabilities=probabilities,
                provenance={
                    "behavior": "real_checkpoint_greedy_main",
                    "source": "Main",
                    "prefill_seed": int(seed),
                    "lineage": "canonical_TrainerEnvironment_step",
                },
            )
            rows_before = len(trainer.replay)
            for uid in range(bundle.users):
                action = int(bundle.actions[uid])
                next_mask = bundle.next_masks[uid]
                admissible = not is_no_op(action) and (
                    bool(bundle.done) or bool(next_mask.any())
                )
                if admissible:
                    # The replay row is exactly the row that the unchanged
                    # Main admission helper stores (including calibration).
                    reward_train = legacy.apply_reward_calibration(
                        bundle.rewards[uid], trainer.config
                    )
                    _hash_replay_row(
                        lineage_digest,
                        state=bundle.states[uid],
                        action=action,
                        reward=reward_train.astype(np.float32),
                        next_state=bundle.next_states[uid],
                        mask=bundle.masks[uid],
                        next_mask=next_mask,
                        done=bundle.done,
                    )
            legacy._admit_main_rows_exactly_as_baseline(trainer, bundle)
            rows_after = len(trainer.replay)
            added = rows_after - rows_before
            if added < 0:
                raise SmokeGateError("Main replay length moved backwards during prefill")
            accepted_rows += added
            accepted_by_step.append(added)
            environment_steps += 1
            trajectory.advance(result)
            if bool(result.done):
                break
        episode_count += 1

    if accepted_rows != len(trainer.replay):
        raise SmokeGateError(
            "Main replay prefill accounting disagrees with the replay buffer"
        )
    return {
        "source": "canonical_TrainerEnvironment_step",
        "behavior": "greedy action from verified 9000-episode Main checkpoint",
        "seed": int(seed),
        "target_rows": int(target_rows),
        "replay_rows_before": int(before),
        "replay_rows_after": int(len(trainer.replay)),
        "replay_rows_added": int(accepted_rows),
        "environment_steps": int(environment_steps),
        "episodes": int(episode_count),
        "accepted_rows_by_environment_step": accepted_by_step,
        "stored_row_lineage_sha256": lineage_digest.hexdigest(),
        "synthetic_labels": False,
        "optimizer_updates_during_prefill": 0,
    }


def _find_anchor(
    trainer: Any,
    environment: Any,
    *,
    evaluation_seed: int,
) -> dict[str, Any]:
    env_rng, mobility_rng, selection_rng, _perturb_rng = checkpoint_loader._evaluation_rngs(
        evaluation_seed
    )
    states, masks, observation = environment.reset(env_rng, mobility_rng)
    for anchor_step in range(MAX_ANCHOR_STEPS + 1):
        branch = backend.C2ForecastBranch(
            wrapped=environment,
            env_rng=env_rng,
            mobility_rng=environment.environment._mobility_rng,
            states=list(states),
            masks=list(masks),
            observation=observation,
            trainer=trainer,
            focal_user=0,
            role="real-checkpoint-joint-anchor",
        )
        main_actions, main_physical = backend._main_actions(trainer, branch)
        departures = _departure_users(environment, main_physical)
        remaining_steps = int(environment.config.steps_per_episode) - int(
            observation.step_index
        )
        if departures and remaining_steps >= core.HOLD_STEPS + 1:
            return {
                "environment": environment,
                "env_rng": env_rng,
                "mobility_rng": environment.environment._mobility_rng,
                "selection_rng": selection_rng,
                "states": list(states),
                "masks": list(masks),
                "observation": observation,
                "anchor_step": int(anchor_step),
                "departure_users": departures,
                "remaining_steps": remaining_steps,
            }
        result = environment.step(main_actions, env_rng)
        if bool(result.done):
            break
        states = list(result.user_states)
        masks = list(result.action_masks)
        observation = environment.last_outcome.observation
    raise SmokeGateError(
        "bounded real-checkpoint anchor scan found no physical incumbent-hold departure"
    )


def _forecast_schedule(
    trainer: Any,
    anchor: Mapping[str, Any],
    *,
    checkpoint_sha256: str,
    environment_source_sha256: str,
    reward_source_sha256: str,
    evaluation_seed: int,
    max_candidates: int,
) -> tuple[list[Any], list[Any], list[dict[str, Any]]]:
    prepared_candidates: list[Any] = []
    schedule: list[Any] = []
    diagnostics: list[dict[str, Any]] = []
    wrapped = anchor["environment"]
    for schedule_index, focal_user in enumerate(
        list(anchor["departure_users"])[: int(max_candidates)]
    ):
        started = time.perf_counter()
        prepared = None
        try:
            service = backend.C2TemporalForkTrainerBackend(
                wrapped=wrapped,
                states=list(anchor["states"]),
                masks=list(anchor["masks"]),
                observation=anchor["observation"],
                env_rng=anchor["env_rng"],
                trainer=trainer,
                checkpoint_sha256=checkpoint_sha256,
                environment_source_sha256=environment_source_sha256,
                reward_source_sha256=reward_source_sha256,
                evaluation_seed=int(evaluation_seed),
                focal_user=int(focal_user),
            )
            prepared = service.prepare_incumbent_hold(focal_user=int(focal_user))
            built = prepared.run_forecast()
            prepared_candidates.append(prepared)
            schedule.append(
                selection.candidate_schedule_row_from_prepared(
                    prepared, schedule_index=schedule_index
                )
            )
            diagnostics.append(
                {
                    "schedule_index": int(schedule_index),
                    "focal_user": int(focal_user),
                    "candidate_key": list(prepared.candidate_key),
                    "passed": bool(built.certificate.passed),
                    "failures": [
                        failure.value for failure in built.certificate.failures
                    ],
                    "ee_surplus_bits": built.certificate.ee_surplus_bits,
                    "hold_r2_margin": built.certificate.hold_r2_margin,
                    "full_r2_margin": built.certificate.full_r2_margin,
                    "elapsed_s": time.perf_counter() - started,
                }
            )
        except backend.C2ForecastSupportRejection as error:
            schedule.append(
                selection.rejected_candidate_schedule_row(
                    schedule_index=schedule_index,
                    focal_user=int(focal_user),
                    candidate_key=(
                        None if prepared is None else prepared.candidate_key
                    ),
                    outcome=selection.CANDIDATE_OUTCOME_SUPPORT_REJECTION,
                    rejection_reason=error.reason,
                )
            )
            diagnostics.append(
                {
                    "schedule_index": int(schedule_index),
                    "focal_user": int(focal_user),
                    "passed": False,
                    "support_rejection": error.reason,
                    "forecast_offset": error.forecast_offset,
                    "affected_user": error.user,
                    "missing_physical_key": (
                        None
                        if error.physical_key is None
                        else list(error.physical_key)
                    ),
                    "elapsed_s": time.perf_counter() - started,
                }
            )
        except Exception as error:
            schedule.append(
                selection.rejected_candidate_schedule_row(
                    schedule_index=schedule_index,
                    focal_user=int(focal_user),
                    candidate_key=(
                        None if prepared is None else prepared.candidate_key
                    ),
                    outcome=selection.CANDIDATE_OUTCOME_CONTRACT_ERROR,
                    error=error,
                )
            )
            diagnostics.append(
                {
                    "schedule_index": int(schedule_index),
                    "focal_user": int(focal_user),
                    "passed": False,
                    "contract_error": f"{type(error).__name__}: {error}",
                    "elapsed_s": time.perf_counter() - started,
                }
            )
    return prepared_candidates, schedule, diagnostics


def _selection_payload(choice: Any) -> dict[str, Any]:
    receipt = choice.receipt
    return {
        "receipt": asdict(receipt),
        "candidate_schedule": [asdict(row) for row in choice.candidate_schedule],
        "candidate_schedule_sha256": receipt.candidate_schedule_sha256,
        "candidate_schedule_size": receipt.candidate_schedule_size,
        "support_count": len(receipt.support),
    }


def _run_transaction(
    trainer: Any,
    specialist: ObjectiveSpecialist,
    choice: Any,
    *,
    anchor_step: int,
    beta: float,
) -> dict[str, Any]:
    """Run one and only one formal C2 transaction and freeze its receipt."""

    if len(choice.receipt.support) < 2:
        raise SmokeGateError("transaction gate requires K>=2 learned support")
    training_step.assert_real_candidate_main_identity(choice, trainer)
    c2_ledger = torch_adapter.C2OptionLedger()
    transaction_ledger = joint.JointOptionLedger()
    consumed_ledger = ConsumedBundleLedger()
    call_counts = {"option_runner": 0, "joint_transaction": 0}
    holder: dict[str, Any] = {}

    def run_option(prepared: Any, **kwargs: Any) -> Any:
        call_counts["option_runner"] += 1
        if call_counts["option_runner"] != 1:
            raise SmokeGateError("more than one C2 option runner call")
        unit = option_runner.commit_prepared_option(prepared, **kwargs)
        holder["unit"] = unit
        return unit

    def run_joint(*args: Any, **kwargs: Any) -> Any:
        call_counts["joint_transaction"] += 1
        if call_counts["joint_transaction"] != 1:
            raise SmokeGateError("more than one C2 joint transaction call")
        receipt = joint.update_c2_joint_transaction(*args, **kwargs)
        holder["joint_receipt"] = receipt
        return receipt

    main_before = _network_digest(trainer)
    q2f_before = _specialist_network_digest(specialist)
    replay_before = len(trainer.replay)
    training_receipt = training_step.run_c2_training_step(
        choice,
        specialist=specialist,
        main=trainer,
        beta=float(beta),
        discount_factor=float(trainer.config.discount_factor),
        block_id=int(anchor_step),
        c2_option_ledger=c2_ledger,
        transaction_ledger=transaction_ledger,
        consumed_ledger=consumed_ledger,
        runner_fn=run_option,
        joint_fn=run_joint,
    )
    unit = holder.get("unit")
    raw_joint_receipt = holder.get("joint_receipt")
    if unit is None or raw_joint_receipt is None:
        raise SmokeGateError("formal C2 seam did not return both option and joint receipts")
    if call_counts != {"option_runner": 1, "joint_transaction": 1}:
        raise SmokeGateError(f"unexpected formal seam call counts: {call_counts}")
    if not (
        training_receipt.admitted
        and training_receipt.updated
        and training_receipt.joint_committed
        and raw_joint_receipt.committed
    ):
        raise SmokeGateError(
            "selected K>=2 option did not produce admitted/updated/committed receipts"
        )
    sequence = unit.sequence
    transition = unit.transition
    if sequence is None or transition is None:
        raise SmokeGateError("committed option lacks sequence or transition")
    if raw_joint_receipt.selection_receipt_sha256 != choice.receipt.receipt_sha256:
        raise SmokeGateError("joint receipt lost the selection receipt digest")
    if raw_joint_receipt.primitive_sequence_sha256 != sequence.sequence_sha256:
        raise SmokeGateError("joint receipt lost the primitive sequence digest")
    if raw_joint_receipt.transition_sha256 != transition.sequence_sha256:
        raise SmokeGateError("joint receipt lost the transition digest")
    if training_receipt.joint_record_sha256 != raw_joint_receipt.record_sha256:
        raise SmokeGateError("training and joint receipts disagree on record digest")
    records = transaction_ledger.state_dict().get("records", ())
    if len(records) != 1:
        raise SmokeGateError("joint ledger does not contain exactly one committed record")
    main_after = _network_digest(trainer)
    q2f_after = _specialist_network_digest(specialist)
    return {
        "call_counts": call_counts,
        "training_step": asdict(training_receipt),
        "option": {
            "admitted": bool(unit.closure.plan.admitted),
            "updated": bool(training_receipt.updated),
            "committed": bool(training_receipt.joint_committed),
            "committed_steps": len(unit.committed_payloads),
            "termination_reason": unit.termination_reason,
            "transition_sha256": transition.sequence_sha256,
            "primitive_sequence_sha256": sequence.sequence_sha256,
            "constituent_bundle_ids": list(sequence.constituent_bundle_ids),
        },
        "joint": {
            "receipt": asdict(raw_joint_receipt),
            "record": records[0],
            # JointOptionRecord deliberately binds the pre-live selection
            # receipt rather than duplicating every selection field.  Expose
            # the transitive schedule binding beside the exact record so a
            # smoke receipt consumer can verify schedule -> selection ->
            # joint-record without reconstructing that chain by hand.
            "record_selection_receipt_sha256": records[0][
                "selection_receipt_sha256"
            ],
            "candidate_schedule_binding": {
                "candidate_schedule_sha256": choice.receipt.candidate_schedule_sha256,
                "candidate_schedule_size": choice.receipt.candidate_schedule_size,
                "selection_receipt_sha256": records[0][
                    "selection_receipt_sha256"
                ],
                "record_sha256": records[0]["record_sha256"],
            },
            "q2f_receipt_sha256": raw_joint_receipt.q2f_receipt_sha256,
            "main_receipt_sha256": raw_joint_receipt.main_receipt_sha256,
            "record_sha256": raw_joint_receipt.record_sha256,
            "source_block_id": raw_joint_receipt.source_block_id,
            "source_policy_version": raw_joint_receipt.source_policy_version,
            "consumer_block_id": raw_joint_receipt.consumer_block_id,
            "policy_version": raw_joint_receipt.policy_version,
        },
        "ledgers": {
            "c2_option_count": len(c2_ledger),
            "joint_transaction_count": len(transaction_ledger),
            "consumed_c1_c3_count": len(consumed_ledger),
        },
        "main_replay_length_before_transaction": replay_before,
        "main_replay_length_after_transaction": len(trainer.replay),
        "networks": {
            "main_digest_before": main_before,
            "main_digest_after": main_after,
            "main_bitwise_equal_before_after": main_before == main_after,
            "q2f_digest_before": q2f_before,
            "q2f_digest_after": q2f_after,
            "q2f_bitwise_equal_before_after": q2f_before == q2f_after,
        },
    }


def run_real_checkpoint_joint_smoke(args: argparse.Namespace) -> dict[str, Any]:
    """Execute the bounded real-checkpoint smoke after explicit opt-in."""

    record = read_prereg(args.prereg)
    archive = TleArchive(Path(args.tle_root).expanduser().resolve())
    assert_ephemeris_matches_record(record, archive=archive)
    trainer, checkpoint = checkpoint_loader._verify_and_load_trainer(
        record,
        archive,
        run_dir=Path(args.checkpoint_dir).expanduser().resolve(),
        users=int(args.users),
    )
    checkpoint_path = Path(checkpoint["checkpoint_path"]).resolve()
    loaded = trainer.load_checkpoint(checkpoint_path, load_optimizers=True)
    metadata = getattr(trainer, "_loaded_checkpoint_metadata", {})
    optimizer_loaded = bool(metadata.get("optimizer_loaded", False))
    if not optimizer_loaded:
        raise SmokeGateError(
            "verified 9000 checkpoint did not load optimizer states; refusing fresh optimizer state"
        )
    if loaded.get("episode") != checkpoint["checkpoint_episode"]:
        raise SmokeGateError("checkpoint load episode disagrees with the verified receipt")
    if len(trainer.replay) != 0:
        raise SmokeGateError("final policy checkpoint unexpectedly carried replay rows")

    environment_source_sha256 = _code_sha256(_default_code_paths())
    reward_source_sha256 = _sha256_file(REPO / "src" / "mcrl" / "env" / "step.py")
    prefill_environment = checkpoint_loader._make_environment(
        archive, users=int(args.users)
    )
    prefill = _prefill_main_replay(
        trainer,
        prefill_environment,
        seed=int(args.prefill_seed),
        target_rows=int(trainer.config.batch_size),
        checkpoint_episode=int(checkpoint["checkpoint_episode"]),
    )
    live_environment = checkpoint_loader._make_environment(
        archive, users=int(args.users)
    )
    anchor = _find_anchor(
        trainer,
        live_environment,
        evaluation_seed=int(args.anchor_seed),
    )
    specialist = ObjectiveSpecialist(
        objective_index=core.C2_OBJECTIVE_INDEX,
        state_dim=trainer.state_dim,
        action_dim=trainer.action_dim,
        config=trainer.config,
        seed=int(args.specialist_seed),
    )
    prepared_candidates, schedule, diagnostics = _forecast_schedule(
        trainer,
        anchor,
        checkpoint_sha256=checkpoint["checkpoint_sha256"],
        environment_source_sha256=environment_source_sha256,
        reward_source_sha256=reward_source_sha256,
        evaluation_seed=int(args.anchor_seed),
        max_candidates=int(args.max_candidates),
    )
    choice = selection.select_prepared_fork(
        prepared_candidates,
        candidate_schedule=schedule,
        behavior_rng=anchor["selection_rng"],
        q2f=specialist,
        epsilon=0.0,
        mode=selection.CHOICE_MODE_Q2F,
        preoutcome_timestamp_ns=int(args.anchor_seed) * 1_000_000
        + int(anchor["anchor_step"]),
    )
    selection.assert_prepared_selection_bound(choice)
    selection_info = _selection_payload(choice)
    base = {
        "schema": SCHEMA,
        "status": "K_GE_2_SUPPORT_REQUIRED",
        "claim_ceiling": CLAIM_CEILING,
        "checkpoint": {
            **checkpoint,
            "path": str(checkpoint_path),
            "optimizer_loaded": optimizer_loaded,
            "main_checkpoint_optimizers_loaded": optimizer_loaded,
        },
        "main_checkpoint_optimizers_loaded": optimizer_loaded,
        "evaluation_seed": int(args.anchor_seed),
        "specialist": {
            "objective_index": core.C2_OBJECTIVE_INDEX,
            "seed": int(args.specialist_seed),
            "policy_version_before_live": int(specialist.policy_version),
            "network_digest_before_live": _specialist_network_digest(specialist),
        },
        "environment_source_sha256": environment_source_sha256,
        "reward_source_sha256": reward_source_sha256,
        "prefill": prefill,
        "anchor": {
            "anchor_step": int(anchor["anchor_step"]),
            "departure_users": list(anchor["departure_users"]),
            "remaining_steps": int(anchor["remaining_steps"]),
            "users": int(args.users),
        },
        "candidate_schedule": [asdict(row) for row in schedule],
        "candidate_diagnostics": diagnostics,
        "selection": selection_info,
    }
    if len(choice.receipt.support) < 2:
        base["status"] = "NO_K_GE_2_SUPPORT"
        base["support_count"] = len(choice.receipt.support)
        base["full_candidate_count"] = len(prepared_candidates)
        return base

    transaction = _run_transaction(
        trainer,
        specialist,
        choice,
        anchor_step=int(anchor["anchor_step"]),
        beta=float(args.beta),
    )
    base.update(
        {
            "status": "PASS",
            "support_count": len(choice.receipt.support),
            "full_candidate_count": len(prepared_candidates),
            "transaction": transaction,
            "training_or_replay_write": True,
            "one_selected_option": True,
            "one_joint_transaction": True,
        }
    )
    if transaction["networks"]["main_bitwise_equal_before_after"]:
        raise SmokeGateError("Main optimizer receipt says updated but network stayed bitwise equal")
    if transaction["networks"]["q2f_bitwise_equal_before_after"]:
        raise SmokeGateError("Q2F optimizer receipt says updated but network stayed bitwise equal")
    return base


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="opt in to the bounded real-checkpoint smoke; default is plan-only",
    )
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--checkpoint-dir", type=Path, default=DEFAULT_CHECKPOINT_DIR)
    parser.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--anchor-seed", type=int, default=DEFAULT_ANCHOR_SEED)
    parser.add_argument("--prefill-seed", type=int, default=DEFAULT_PREFILL_SEED)
    parser.add_argument("--specialist-seed", type=int, default=DEFAULT_SPECIALIST_SEED)
    parser.add_argument("--max-candidates", type=int, default=9)
    parser.add_argument("--beta", type=float, default=0.25)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    if not args.execute:
        print(json.dumps(_plan_payload(args), indent=2, sort_keys=True))
        return 0
    if args.users < 1 or args.max_candidates < 1:
        raise ValueError("--users and --max-candidates must be positive")
    if not 0.0 <= float(args.beta) <= 1.0:
        raise ValueError("--beta must lie in [0,1]")
    output = Path(args.output).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing smoke receipt: {output}")
    try:
        payload = run_real_checkpoint_joint_smoke(args)
    except SmokeGateError as error:
        payload = {
            "schema": SCHEMA,
            "status": "FAIL",
            "error_type": type(error).__name__,
            "error": str(error),
            "claim_ceiling": CLAIM_CEILING,
        }
    _write_json(output, payload)
    print(output)
    return 0 if payload.get("status") == "PASS" else 2


__all__ = [
    "CLAIM_CEILING",
    "DEFAULT_OUTPUT",
    "SCHEMA",
    "SmokeGateError",
    "_hash_replay_row",
    "_plan_payload",
    "_specialist_network_digest",
    "_network_digest",
    "run_real_checkpoint_joint_smoke",
]


if __name__ == "__main__":
    raise SystemExit(main())
