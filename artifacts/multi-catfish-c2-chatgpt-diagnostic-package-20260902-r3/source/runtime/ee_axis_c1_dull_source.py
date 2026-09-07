"""Real-environment dull-rollout records for the V0.3 C1 selector.

The retained RIS lineage uses deterministic local-SNR experience as the
source-only EXP corpus.  V0.3 does not reuse those historical transition rows
as targets.  Instead, this module evaluates the same fixed dull policy at a
current keyed-fading anchor, records its lower-frontier system/user EE scores,
and separately binds the frozen Main reference actions used by ACRM.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

import numpy as np

from ..env.action_contract import (
    NO_OP_ACTION,
    SlotTable,
    assert_selected_actions_valid,
)
from ..env.keyed_fading import KeyedFadingField
from ..env.step import ActionEvaluation, StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_c1_selector import C1DullRolloutRecord
from .ee_axis_state import EEAxisStateObservation, encode_ee_axis_state


C1_DULL_POLICY = "local-snr-greedy-v1"


class C1DullSourceContractError(MCRLContractError):
    """A C1 dull-rollout anchor violates the current source contract."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C1DullSourceContractError(f"{field} must be lowercase SHA-256")
    return value


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _slot_payload(table: SlotTable) -> dict[str, object]:
    return {
        "norad_ids": [int(value) for value in table.norad_ids.tolist()],
        "cell_ids": [int(value) for value in table.cell_ids.tolist()],
        "mask": [bool(value) for value in table.mask.tolist()],
    }


def local_snr_dull_actions(observation: StepObservation) -> np.ndarray:
    """Return the fixed deterministic RIS-lineage local-SNR joint action."""

    if not isinstance(observation, StepObservation):
        raise C1DullSourceContractError("observation must be StepObservation")
    actions = np.full(observation.num_users, NO_OP_ACTION, dtype=np.int64)
    for uid, (state, table) in enumerate(
        zip(
            observation.user_states,
            observation.candidates.slot_tables,
            strict=True,
        )
    ):
        valid = np.flatnonzero(table.mask)
        if valid.size == 0:
            continue
        quality = np.asarray(state.channel_quality, dtype=np.float64)
        if quality.shape != table.mask.shape or not np.all(np.isfinite(quality[valid])):
            raise C1DullSourceContractError(
                "local-SNR quality must be finite and action aligned"
            )
        actions[uid] = min(
            (int(action) for action in valid.tolist()),
            key=lambda action: (-float(quality[action]), action),
        )
    actions.setflags(write=False)
    return actions


@dataclass(frozen=True)
class C1DullRolloutSample:
    """One selector record plus the dull action committed by its runner."""

    record: C1DullRolloutRecord
    state_observation: EEAxisStateObservation
    dull_actions: np.ndarray
    dull_evaluation: ActionEvaluation

    def verify(self) -> None:
        self.record.verify()
        self.state_observation.verify()
        if self.record.state_schema != self.state_observation.schema:
            raise C1DullSourceContractError("record/state schema disagrees")
        if self.record.state_schema_sha256 != self.state_observation.schema_sha256:
            raise C1DullSourceContractError("record/state schema digest disagrees")
        actions = np.asarray(self.dull_actions)
        if actions.shape != self.record.reference_actions.shape:
            raise C1DullSourceContractError("dull/reference user counts disagree")
        if actions.flags.writeable:
            raise C1DullSourceContractError("dull actions must be immutable")
        expected = np.asarray(
            [reward.r1_system_ee_contribution for reward in self.dull_evaluation.rewards],
            dtype=np.float64,
        )
        if not np.array_equal(expected, self.record.user_frontier_scores):
            raise C1DullSourceContractError("dull user frontier scores drifted")
        if self.record.frontier_score != float(
            self.dull_evaluation.energy.system_ee_bits_per_j
        ):
            raise C1DullSourceContractError("dull system frontier score drifted")


def capture_c1_dull_rollout_sample(
    environment: StepEnvironment,
    *,
    observation: StepObservation,
    reference_actions: object,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    source_seed: int,
    rng: np.random.Generator,
) -> C1DullRolloutSample:
    """Capture one current V0.3 C1 source record without committing physics."""

    if not isinstance(environment, StepEnvironment):
        raise C1DullSourceContractError("environment must be StepEnvironment")
    if not isinstance(observation, StepObservation):
        raise C1DullSourceContractError("observation must be StepObservation")
    if type(source_seed) is not int or source_seed < 0:
        raise C1DullSourceContractError("source_seed must be a nonnegative integer")
    if not isinstance(rng, np.random.Generator):
        raise C1DullSourceContractError("rng must be numpy.random.Generator")
    _digest(source_manifest_sha256, field="source_manifest_sha256")
    _digest(checkpoint_sha256, field="checkpoint_sha256")
    field = getattr(environment, "_fading_field", None)
    if not isinstance(field, KeyedFadingField) or not environment.physics.fading_enabled:
        raise C1DullSourceContractError(
            "C1 dull source requires the current keyed fading field"
        )
    try:
        state = encode_ee_axis_state(environment, observation)
        reference = assert_selected_actions_valid(
            np.asarray(reference_actions), observation.candidates.slot_tables
        )
        dull = local_snr_dull_actions(observation)
        dull = assert_selected_actions_valid(dull, observation.candidates.slot_tables)
        evaluation = environment.evaluate_actions(dull, rng)
    except (MCRLContractError, TypeError, ValueError) as error:
        raise C1DullSourceContractError(str(error)) from error
    reference = np.array(reference, dtype=np.int64, copy=True)
    reference.setflags(write=False)
    dull = np.array(dull, dtype=np.int64, copy=True)
    dull.setflags(write=False)
    slot_tables = tuple(observation.candidates.slot_tables)
    anchor_sha256 = _canonical_sha256(
        {
            "schema": "multi-catfish-mcrl-v03-c1-anchor-v1",
            "source_seed": source_seed,
            "step_index": int(observation.step_index),
            "state_observation_sha256": state.state_sha256,
            "reference_actions": [int(value) for value in reference.tolist()],
            "slot_tables": [_slot_payload(table) for table in slot_tables],
        }
    )
    user_scores = np.asarray(
        [reward.r1_system_ee_contribution for reward in evaluation.rewards],
        dtype=np.float64,
    )
    record = C1DullRolloutRecord(
        record_id=f"c1-dull-seed{source_seed}-step{int(observation.step_index):04d}",
        anchor_sha256=anchor_sha256,
        source_manifest_sha256=source_manifest_sha256,
        checkpoint_sha256=checkpoint_sha256,
        state_schema=state.schema,
        state_schema_sha256=state.schema_sha256,
        source_seed=source_seed,
        step_index=int(observation.step_index),
        partition="TRAIN",
        rollout_kind="dull-rollout",
        policy_name=C1_DULL_POLICY,
        frontier_score=float(evaluation.energy.system_ee_bits_per_j),
        user_frontier_scores=user_scores,
        reference_actions=reference,
        slot_tables=slot_tables,
    )
    sample = C1DullRolloutSample(
        record=record,
        state_observation=state,
        dull_actions=dull,
        dull_evaluation=evaluation,
    )
    sample.verify()
    return sample


__all__ = [
    "C1_DULL_POLICY",
    "C1DullRolloutSample",
    "C1DullSourceContractError",
    "capture_c1_dull_rollout_sample",
    "local_snr_dull_actions",
]
