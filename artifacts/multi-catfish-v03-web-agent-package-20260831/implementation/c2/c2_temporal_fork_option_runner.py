"""Complete H=3 plus release execution seam for a prepared C2 V0.3 fork.

The runner owns only the committed option and its immutable learning objects.
It does not update Q2F, Main, replay, or a ledger.  Forecast failure never
reaches this selected live seam; nonterminal physical expiry or missing
chronology is a contract error, while a true environment terminal retains its
actual observed prefix without padding.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from typing import Any

import numpy as np

import c2_temporal_fork_core as core
import c2_temporal_fork_forecast_adapter as forecast
import c2_temporal_fork_learning_adapter as learning
import c2_temporal_fork_trainer_backend as backend
from smc_er_core import AtomicBundle


CLAIM_CEILING = (
    "complete real C2 option and admitted learning-object construction only; "
    "no optimizer update or EE efficacy"
)


class C2OptionRunnerError(core.C2ContractError):
    """A prepared fork could not be closed through the real option seam."""


@dataclass(frozen=True)
class C2CommittedLearningUnit:
    certificate: core.TemporalForkCertificate
    chronology_receipt: object
    committed_payloads: tuple[forecast.ForecastStepPayload, ...]
    closure: forecast.CommittedOptionClosure
    bundles: tuple[AtomicBundle, ...]
    transition: learning.C2SMDPTransition | None
    sequence: learning.C2PrimitiveSequence | None
    termination_reason: str | None
    claim_ceiling: str = CLAIM_CEILING


def _bundle_id(option_id: str, anchor_sha256: str, offset: int) -> str:
    return hashlib.sha256(
        f"c2-v03:{option_id}:{anchor_sha256}:{offset}".encode("ascii")
    ).hexdigest()


def _opening_payload(
    prepared: backend.PreparedC2Fork,
    live_step: backend.C2LiveStep,
) -> forecast.ForecastStepPayload:
    anchor = prepared.anchor
    users = len(anchor.states)
    outcome = live_step.outcome
    result = live_step.result
    next_observation = getattr(outcome, "observation", None)
    if next_observation is None:
        raise C2OptionRunnerError("opening live outcome lacks successor observation")
    done = bool(getattr(result, "done", getattr(outcome, "done", False)))
    payload = forecast.ForecastStepPayload(
        offset=0,
        state_matrix=backend._state_matrix(anchor.observation),
        mask_matrix=backend._mask_matrix(anchor.observation, users=users),
        action_bindings_by_user=backend._bindings(anchor.observation, users=users),
        detached_main_actions=anchor.main_actions,
        detached_main_physical_actions=anchor.main_physical_actions,
        executed_actions=live_step.action_indices,
        executed_physical_actions=live_step.physical_actions,
        reward_matrix=backend._reward_matrix(outcome, users=users),
        served=backend._served(outcome, users=users),
        link_rate_bps=backend._rates(outcome, users=users),
        system_power_w=float(getattr(outcome, "system_power_w", float("nan"))),
        active_physical_ids=backend._active_physical_ids(outcome),
        next_state_matrix=backend._state_matrix(
            next_observation, field="next_state_matrix"
        ),
        next_mask_matrix=backend._mask_matrix(next_observation, users=users),
        done=done,
        held_physical_key=prepared.candidate_key,
        held_key_match_count=backend._candidate_support_count(
            anchor.observation,
            focal_user=anchor.focal_user,
            candidate_key=prepared.candidate_key,
        ),
        # The live branch may release at a different offset than the
        # pre-outcome twin; the final policy metadata is latched after the
        # observed prefix is built below.
        release_offset=None,
        release_reason=None,
    )
    if not np.isfinite(payload.system_power_w) or payload.system_power_w <= 0.0:
        raise C2OptionRunnerError("opening live step lacks positive finite power")
    return payload


def _atomic_bundle(
    *,
    certificate: core.TemporalForkCertificate,
    chronology_receipt_sha256: str,
    selection_receipt_sha256: str,
    payload: forecast.ForecastStepPayload,
    bundle_id: str,
    focal_user: int,
    opening_behavior_probability: float,
    anchor_step_index: int,
    block_id: int,
    source_policy_version: int,
) -> AtomicBundle:
    probabilities = np.ones(certificate.user_count, dtype=np.float64)
    if payload.offset == 0:
        probabilities[focal_user] = float(opening_behavior_probability)
    phase = (
        "hold"
        if payload.release_offset is None or payload.offset < payload.release_offset
        else "release"
    )
    reward_matrix = tuple(tuple(row) for row in payload.reward_matrix)
    provenance = {
        "option_id": certificate.option_id,
        "anchor_sha256": certificate.anchor_sha256,
        "evidence_sha256": certificate.evidence_sha256,
        "chronology_receipt_sha256": chronology_receipt_sha256,
        "selection_receipt_sha256": selection_receipt_sha256,
        "offset": payload.offset,
        "environment_step_index": anchor_step_index + payload.offset,
        "phase": phase,
        "state_sha256": learning.array_sha256(
            payload.state_matrix[focal_user]
        ),
        "state_mask_sha256": learning.array_sha256(
            payload.mask_matrix[focal_user]
        ),
        "next_state_sha256": learning.array_sha256(
            payload.next_state_matrix[focal_user]
        ),
        "next_mask_sha256": learning.array_sha256(
            payload.next_mask_matrix[focal_user]
        ),
        "reward_matrix_sha256": core.reward_matrix_sha256(reward_matrix),
        "r2_column_sha256": core.r2_column_sha256(
            tuple(row[core.C2_OBJECTIVE_INDEX] for row in reward_matrix)
        ),
        "reward_source_sha256": certificate.reward_source_sha256,
        "focal_served": bool(payload.served[focal_user]),
        "served": tuple(bool(value) for value in payload.served),
        "behavior_probability": float(probabilities[focal_user]),
        "c2_policy_version": core.CANDIDATE_VERSION,
        "held_physical_key": payload.held_physical_key,
        "held_key_match_count": payload.held_key_match_count,
        "release_offset": payload.release_offset,
        "release_reason": payload.release_reason,
    }
    return AtomicBundle(
        bundle_id=bundle_id,
        source_id="C2",
        source_policy_version=source_policy_version,
        block_id=block_id,
        step_index=anchor_step_index + payload.offset,
        states=np.asarray(payload.state_matrix, dtype=np.float32),
        actions=np.asarray(payload.executed_actions, dtype=np.int64),
        rewards=np.asarray(payload.reward_matrix, dtype=np.float64),
        next_states=np.asarray(payload.next_state_matrix, dtype=np.float32),
        masks=np.asarray(payload.mask_matrix, dtype=np.bool_),
        next_masks=np.asarray(payload.next_mask_matrix, dtype=np.bool_),
        done=bool(payload.done),
        focal_user=focal_user,
        behavior_probabilities=probabilities,
        provenance=provenance,
    )


def commit_prepared_option(
    prepared: backend.PreparedC2Fork,
    *,
    opening_behavior_probability: float,
    discount_factor: float,
    block_id: int,
    selection_receipt_sha256: str,
    source_policy_version: int = 3,
) -> C2CommittedLearningUnit:
    """Commit one prepared option and construct admitted Q2 learning objects."""

    if not isinstance(prepared, backend.PreparedC2Fork):
        raise C2OptionRunnerError("prepared must be PreparedC2Fork")
    if prepared.build is None or prepared.phase != "forecast_complete":
        raise C2OptionRunnerError("option commit requires a completed forecast")
    certificate = prepared.build.certificate
    if not certificate.passed:
        raise C2OptionRunnerError("failed certificate cannot open a live option")
    if (
        isinstance(opening_behavior_probability, bool)
        or not isinstance(opening_behavior_probability, (int, float))
        or not np.isfinite(opening_behavior_probability)
        or not 0.0 < float(opening_behavior_probability) <= 1.0
    ):
        raise C2OptionRunnerError("opening behavior probability must lie in (0,1]")
    if type(block_id) is not int or block_id < 0:
        raise C2OptionRunnerError("block_id must be a nonnegative exact integer")
    if type(source_policy_version) is not int or source_policy_version < 0:
        raise C2OptionRunnerError(
            "source_policy_version must be a nonnegative exact integer"
        )
    if (
        not isinstance(selection_receipt_sha256, str)
        or len(selection_receipt_sha256) != 64
        or selection_receipt_sha256 != selection_receipt_sha256.lower()
        or any(char not in "0123456789abcdef" for char in selection_receipt_sha256)
    ):
        raise C2OptionRunnerError(
            "selection_receipt_sha256 must be a lowercase SHA-256 digest"
        )

    opening, chronology_receipt = prepared.run_live_step()
    payloads: list[forecast.ForecastStepPayload] = [_opening_payload(prepared, opening)]
    termination_reason: str | None = None
    if payloads[0].done:
        termination_reason = "opening_step_terminal_before_release"

    anchor = prepared.anchor
    branch = backend.C2ForecastBranch(
        wrapped=anchor.wrapped,
        env_rng=anchor.env_rng,
        mobility_rng=anchor.mobility_rng,
        states=list(opening.result.user_states),
        masks=list(opening.result.action_masks),
        observation=opening.outcome.observation,
        trainer=anchor.trainer,
        focal_user=anchor.focal_user,
        role="live-option-commit",
        offset=1,
    )
    candidate_holding = True
    release_offset: int | None = None
    release_reason: str | None = None
    for offset in range(1, core.HORIZON_STEPS + 1):
        if termination_reason is not None:
            break
        main_actions, main_physical = backend._main_actions(anchor.trainer, branch)
        support_count = backend._candidate_support_count(
            branch.observation,
            focal_user=anchor.focal_user,
            candidate_key=prepared.candidate_key,
        )
        if candidate_holding:
            if support_count != 1:
                candidate_holding = False
                release_offset = offset
                release_reason = "support_expired"
            elif offset == core.HORIZON_STEPS:
                candidate_holding = False
                release_offset = offset
                release_reason = "horizon"
        executed, _executed_physical = backend._compose_candidate_actions(
            observation=branch.observation,
            main_actions=main_actions,
            main_physical=main_physical,
            candidate_key=prepared.candidate_key,
            focal_user=anchor.focal_user,
            offset=offset,
            hold=candidate_holding,
        )
        payload = backend._step_payload(
            branch,
            offset=offset,
            detached_main_actions=main_actions.tolist(),
            detached_main_physical=main_physical,
            executed_actions=executed.tolist(),
            held_physical_key=prepared.candidate_key,
            held_key_match_count=support_count,
        )
        payloads.append(payload)
        if payload.done and offset < core.HORIZON_STEPS:
            termination_reason = f"episode_ended_at_offset_{offset}"

    if release_offset is None:
        # A real terminal may end the observed prefix before the planned
        # release.  It is not itself a support-expiry event, but the rows still
        # need an explicit sealed policy so the V0.3B committed-row adapter
        # cannot mistake a partially populated legacy row for a new one.
        release_offset = core.HORIZON_STEPS
        release_reason = "horizon"
    if release_offset is not None and release_reason is not None:
        payloads = [
            replace(
                payload,
                release_offset=release_offset,
                release_reason=release_reason,
            )
            for payload in payloads
        ]

    bundle_ids = tuple(
        _bundle_id(certificate.option_id, certificate.anchor_sha256, payload.offset)
        for payload in payloads
    )
    probabilities = tuple(
        float(opening_behavior_probability) if payload.offset == 0 else 1.0
        for payload in payloads
    )
    closure = forecast.close_committed_option(
        certificate,
        bundle_ids=bundle_ids,
        committed_steps=payloads,
        behavior_probabilities=probabilities,
        reward_source_sha256=certificate.reward_source_sha256,
        discount_factor=discount_factor,
        chronology_receipt=chronology_receipt,
    )
    if not closure.plan.admitted:
        return C2CommittedLearningUnit(
            certificate=certificate,
            chronology_receipt=chronology_receipt,
            committed_payloads=tuple(payloads),
            closure=closure,
            bundles=(),
            transition=None,
            sequence=None,
            termination_reason=termination_reason,
        )

    chronology_sha256 = closure.plan.chronology_receipt_sha256
    if chronology_sha256 is None:
        raise C2OptionRunnerError("admitted closure lacks chronology digest")
    anchor_step_index = int(getattr(anchor.observation, "step_index"))
    bundles = tuple(
        _atomic_bundle(
            certificate=certificate,
            chronology_receipt_sha256=chronology_sha256,
            selection_receipt_sha256=selection_receipt_sha256,
            payload=payload,
            bundle_id=bundle_id,
            focal_user=anchor.focal_user,
            opening_behavior_probability=float(opening_behavior_probability),
            anchor_step_index=anchor_step_index,
            block_id=block_id,
            source_policy_version=source_policy_version,
        )
        for payload, bundle_id in zip(payloads, bundle_ids, strict=True)
    )
    sequence = learning.C2PrimitiveSequence.from_plan(
        closure.plan, certificate, bundles
    )
    transition = learning.C2SMDPTransition.from_plan(
        closure.plan,
        certificate,
        opening_state=payloads[0].state_matrix[anchor.focal_user],
        opening_mask=payloads[0].mask_matrix[anchor.focal_user],
        bootstrap_state=payloads[-1].next_state_matrix[anchor.focal_user],
        bootstrap_mask=payloads[-1].next_mask_matrix[anchor.focal_user],
        reward_matrices=tuple(payload.reward_matrix for payload in payloads),
        discount_factor=discount_factor,
        terminal=bool(payloads[-1].done),
        selection_receipt_sha256=selection_receipt_sha256,
    )
    return C2CommittedLearningUnit(
        certificate=certificate,
        chronology_receipt=chronology_receipt,
        committed_payloads=tuple(payloads),
        closure=closure,
        bundles=bundles,
        transition=transition,
        sequence=sequence,
        termination_reason=termination_reason,
    )


__all__ = [
    "C2CommittedLearningUnit",
    "C2OptionRunnerError",
    "CLAIM_CEILING",
    "commit_prepared_option",
]
