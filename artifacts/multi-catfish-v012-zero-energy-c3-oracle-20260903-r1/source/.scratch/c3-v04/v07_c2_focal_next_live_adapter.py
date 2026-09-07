#!/usr/bin/env python3
"""Live matched-branch adapter for the V0.7 focal-next C2 source.

The adapter accepts an already authenticated runtime, frozen Q1/Q3 hybrid,
and either zero-Q2 (bootstrap) or one explicit fresh Q2 (refresh).  It replays
one behavior-policy decision, changes only the focal opening action, lets each
branch choose its own successor action vector, and measures the focal rate and
focal marginal network power without committing the successor evaluation.

It does not select worlds, inspect an EE endpoint, train a network, or invoke
the resident legacy Q2.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from mcrl.env.action_contract import NO_OP_ACTION, NUM_ACTIONS
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_state import encode_ee_axis_state
from mcrl.runtime.ee_axis_v04_c3_state import encode_ee_axis_v04_c3_state
from mcrl.runtime.ee_axis_v07_c2_state import (
    V07_C2_Q2_STATE_SCHEMA,
    V07_C2_Q2_STATE_SCHEMA_SHA256,
    encode_ee_axis_v07_c2_state,
)
from mcrl.runtime.ee_axis_v07_c2_dataset import (
    V07C2Dataset,
    V07C2DecisionCoverage,
    V07C2Row,
    canonical_sha256,
)
from mcrl.runtime.ee_axis_v07_c2_focal_next import focal_next_surplus_target
from mcrl.runtime.ee_axis_v07_c2_policy import (
    FreshQ2,
    V07C2BehaviorDecision,
    V07_C2_POLICY_SCHEMA,
    behavior_decision,
    focal_candidate_vector,
)


V07_C2_CAPTURE_SCHEMA = "multi-catfish-mcrl-v07-c2-decision-capture-v1"
BRANCH_RECEIPT_SCHEMA = "multi-catfish-mcrl-v07-c2-branch-receipt-v1"


class V07C2LiveAdapterError(MCRLContractError):
    """A matched branch cannot produce a trustworthy V0.7 source row."""


@dataclass(frozen=True)
class V07C2DecisionCapture:
    coverage: V07C2DecisionCoverage
    rows: tuple[V07C2Row, ...]
    receipt: Mapping[str, object]

    def verify(self) -> str:
        dataset = V07C2Dataset.from_records(
            rows=self.rows, coverage=(self.coverage,)
        )
        if not isinstance(self.receipt, Mapping):
            raise V07C2LiveAdapterError("capture receipt must be a mapping")
        body = dict(self.receipt)
        supplied = body.pop("receipt_sha256", None)
        if supplied != canonical_sha256(body):
            raise V07C2LiveAdapterError("capture receipt digest drifted")
        if body.get("schema") != V07_C2_CAPTURE_SCHEMA:
            raise V07C2LiveAdapterError("capture receipt schema drifted")
        if body.get("dataset_sha256") != dataset.corpus_sha256:
            raise V07C2LiveAdapterError("capture receipt dataset digest drifted")
        return str(supplied)


@dataclass(frozen=True)
class _SuccessorMeasurement:
    terminal_absorbing_zero: bool
    focal_rate_bps: float
    full_power_w: float
    without_focal_power_w: float
    successor_actions: np.ndarray
    successor_masks: np.ndarray
    successor_policy_sha256: str
    focal_already_noop: bool


def _array_sha256(value: object, *, dtype: np.dtype[Any]) -> str:
    array = np.ascontiguousarray(np.asarray(value, dtype=dtype))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(b"\0")
    digest.update(json.dumps(list(array.shape), separators=(",", ":")).encode("ascii"))
    digest.update(b"\0")
    digest.update(array.tobytes())
    return digest.hexdigest()


def frozen_network_digest(network: Any) -> str:
    """Digest one frozen Q-network's parameter bytes, independent of state."""

    state_dict = getattr(network, "state_dict", None)
    if not callable(state_dict):
        raise V07C2LiveAdapterError("frozen network has no state_dict boundary")
    digest = hashlib.sha256()
    try:
        items = sorted(state_dict().items(), key=lambda item: str(item[0]))
    except Exception as error:
        raise V07C2LiveAdapterError("frozen network state is not readable") from error
    for name, value in items:
        array = np.asarray(value.detach().cpu().numpy())
        digest.update(str(name).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(b"\0")
        digest.update(json.dumps(list(array.shape), separators=(",", ":")).encode("ascii"))
        digest.update(b"\0")
        digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def _environment(wrapped: Any) -> Any:
    environment = getattr(wrapped, "environment", wrapped)
    if environment is None:
        raise V07C2LiveAdapterError("runtime returned no StepEnvironment")
    return environment


def _reset(runtime: Any, archive: Any, *, source_seed: int, field: KeyedFadingField) -> tuple[Any, np.random.Generator, Any]:
    wrapped = runtime.make_environment(archive, users=int(runtime.users))
    runtime.bind_field(wrapped, field)
    rngs = runtime.evaluation_rngs(int(source_seed))
    if not isinstance(rngs, tuple) or len(rngs) < 2:
        raise V07C2LiveAdapterError("runtime did not provide environment/mobility RNGs")
    env_rng, mobility_rng = rngs[:2]
    try:
        _states, _masks, observation = wrapped.reset(env_rng, mobility_rng)
    except Exception as error:
        raise V07C2LiveAdapterError(f"branch reset failed: {error}") from error
    return wrapped, env_rng, observation


def _advance(wrapped: Any, actions: np.ndarray, rng: np.random.Generator) -> bool:
    try:
        result = wrapped.step(np.asarray(actions, dtype=np.int64), rng)
    except Exception as error:
        raise V07C2LiveAdapterError(f"matched branch step failed: {error}") from error
    return bool(getattr(result, "done", False))


def _decision(
    hybrid: object,
    fresh_q2: FreshQ2 | None,
    wrapped: Any,
    observation: Any,
    *,
    interval_s: float,
    kappa_bits: float,
    q2_user_scope: str = "all",
) -> tuple[V07C2BehaviorDecision, np.ndarray]:
    environment = _environment(wrapped)
    v03 = encode_ee_axis_state(environment, observation)
    v07_q2 = encode_ee_axis_v07_c2_state(environment, observation)
    v04 = encode_ee_axis_v04_c3_state(
        environment,
        observation,
        interval_s=interval_s,
        kappa_bits=kappa_bits,
    )
    decision = behavior_decision(
        hybrid=hybrid,
        fresh_q2=fresh_q2,
        states_v03=v03.state_matrix,
        states_v04_c3=v04.state_matrix,
        states_v07_c2_q2=v07_q2.state_matrix,
        masks=np.asarray(observation.masks, dtype=np.bool_),
        q2_user_scope=q2_user_scope,
    )
    return decision, np.asarray(v07_q2.state_matrix, dtype=np.float32)


def _decision_receipt_sha256(decision: V07C2BehaviorDecision) -> str:
    """Digest one state-dependent decision surface, not the frozen policy."""

    return canonical_sha256(
        {
            "schema": decision.schema,
            "actions_sha256": _array_sha256(decision.actions, dtype=np.dtype(np.int64)),
            "masks_sha256": _array_sha256(decision.masks, dtype=np.dtype(np.bool_)),
            "q1_sha256": _array_sha256(decision.q1, dtype=np.dtype(np.float64)),
            "q2_sha256": _array_sha256(decision.q2, dtype=np.dtype(np.float64)),
            "q3_sha256": _array_sha256(decision.q3, dtype=np.dtype(np.float64)),
            "scores_sha256": _array_sha256(decision.scores, dtype=np.dtype(np.float64)),
        }
    )


def _frozen_policy_sha256(
    hybrid: object,
    fresh_q2: FreshQ2 | None,
) -> str:
    """Digest the state-independent policy authority for one lineage."""

    q_nets_raw = getattr(hybrid, "q_nets", None)
    try:
        q_nets = None if q_nets_raw is None else tuple(q_nets_raw)
    except TypeError as error:
        raise V07C2LiveAdapterError(
            "frozen Q1/Q2/Q3 network container is malformed"
        ) from error
    if q_nets is not None and len(q_nets) == 3:
        network_identity: dict[str, object] = {
            "q1_network_sha256": frozen_network_digest(q_nets[0]),
            "q3_network_sha256": frozen_network_digest(q_nets[2]),
            "selected_q3_rung": int(getattr(hybrid, "selected_q3_rung")),
            "network_receipt_complete": True,
        }
    else:
        network_identity = {
            "stub_type": f"{type(hybrid).__module__}.{type(hybrid).__qualname__}",
            "network_receipt_complete": False,
        }
    fresh_identity: dict[str, object]
    if fresh_q2 is None:
        fresh_identity = {"q2": "exact-zero-bootstrap"}
    else:
        fresh_identity = {
            "q2": "explicit-fresh-q2",
            "fresh_q2_type": (
                f"{type(fresh_q2).__module__}.{type(fresh_q2).__qualname__}"
            ),
        }
    return canonical_sha256(
        {
            "schema": V07_C2_POLICY_SCHEMA,
            "composition": "unweighted-q1-plus-q2-plus-q3",
            "mask": "one-common-native-safe-mask",
            "selection": "one-deterministic-masked-argmax-lowest-index-tie",
            **network_identity,
            **fresh_identity,
        }
    )


def _replay_to_anchor(
    runtime: Any,
    archive: Any,
    *,
    source_seed: int,
    field: KeyedFadingField,
    history: Sequence[np.ndarray],
    target_step: int,
) -> tuple[Any, np.random.Generator, Any]:
    if type(target_step) is not int or target_step < 0:
        raise V07C2LiveAdapterError("target_step must be a nonnegative integer")
    if len(history) != target_step + 1:
        raise V07C2LiveAdapterError("history must include exactly the anchor action")
    wrapped, env_rng, observation = _reset(
        runtime, archive, source_seed=source_seed, field=field
    )
    for expected_step, actions in enumerate(history[:-1]):
        if int(observation.step_index) != expected_step:
            raise V07C2LiveAdapterError("history replay step index drifted")
        if _advance(wrapped, np.asarray(actions, dtype=np.int64), env_rng):
            raise V07C2LiveAdapterError("history terminated before the anchor")
        observation = wrapped.last_outcome.observation
    if int(observation.step_index) != target_step:
        raise V07C2LiveAdapterError("history replay did not reach the anchor")
    return wrapped, env_rng, observation


def bind_behavior_action_at_anchor(
    runtime: Any,
    archive: Any,
    hybrid: object,
    fresh_q2: FreshQ2 | None,
    *,
    source_seed: int,
    field: KeyedFadingField,
    carrier_history: Sequence[np.ndarray],
    target_step: int,
    interval_s: float,
    kappa_bits: float,
) -> tuple[tuple[np.ndarray, ...], V07C2BehaviorDecision, np.ndarray]:
    """Replace only the carrier's unexecuted anchor action by V0.7 behavior.

    ``carrier_history[:-1]`` determines the common predecision state.  Its
    final entry has not been executed and is replaced, so D2 can compare all
    frozen lineages on one outcome-blind carrier state.  D3 on-policy capture
    can pass a carrier already generated by the same behavior policy.
    """

    wrapped, _env_rng, observation = _replay_to_anchor(
        runtime,
        archive,
        source_seed=source_seed,
        field=field,
        history=carrier_history,
        target_step=target_step,
    )
    decision, states_v03 = _decision(
        hybrid,
        fresh_q2,
        wrapped,
        observation,
        interval_s=interval_s,
        kappa_bits=kappa_bits,
    )
    bound = tuple(
        np.asarray(actions, dtype=np.int64).copy()
        for actions in carrier_history[:-1]
    ) + (np.asarray(decision.actions, dtype=np.int64).copy(),)
    return bound, decision, np.array(states_v03, dtype=np.float32, copy=True)


def _measure_branch_successor(
    runtime: Any,
    archive: Any,
    hybrid: object,
    fresh_q2: FreshQ2 | None,
    *,
    source_seed: int,
    field: KeyedFadingField,
    history: Sequence[np.ndarray],
    target_step: int,
    focal_user: int,
    opening_actions: np.ndarray,
    interval_s: float,
    kappa_bits: float,
) -> _SuccessorMeasurement:
    wrapped, env_rng, _observation = _replay_to_anchor(
        runtime,
        archive,
        source_seed=source_seed,
        field=field,
        history=history,
        target_step=target_step,
    )
    terminal = _advance(wrapped, opening_actions, env_rng)
    if terminal:
        return _SuccessorMeasurement(
            terminal_absorbing_zero=True,
            focal_rate_bps=0.0,
            full_power_w=0.0,
            without_focal_power_w=0.0,
            successor_actions=np.full(int(runtime.users), NO_OP_ACTION, dtype=np.int64),
            successor_masks=np.zeros((int(runtime.users), NUM_ACTIONS), dtype=np.bool_),
            successor_policy_sha256=canonical_sha256(
                {"terminal_absorbing_zero": True}
            ),
            focal_already_noop=True,
        )

    observation = wrapped.last_outcome.observation
    successor, _state = _decision(
        hybrid,
        fresh_q2,
        wrapped,
        observation,
        interval_s=interval_s,
        kappa_bits=kappa_bits,
    )
    environment = _environment(wrapped)
    full = environment.evaluate_actions(successor.actions, env_rng)
    focal_action = int(successor.actions[focal_user])
    if focal_action == NO_OP_ACTION:
        removed = full
        focal_already_noop = True
    else:
        removed = environment.evaluate_actions_without_user(
            successor.actions, env_rng, focal_user=focal_user
        )
        focal_already_noop = False
    focal_rate = float(np.asarray(full.link_rate_bps, dtype=np.float64)[focal_user])
    full_power = float(full.system_power_w)
    without_power = float(removed.system_power_w)
    if not all(np.isfinite(value) and value >= 0.0 for value in (focal_rate, full_power, without_power)):
        raise V07C2LiveAdapterError("successor rate/power measurement is invalid")
    return _SuccessorMeasurement(
        terminal_absorbing_zero=False,
        focal_rate_bps=focal_rate,
        full_power_w=full_power,
        without_focal_power_w=without_power,
        successor_actions=np.array(successor.actions, dtype=np.int64, copy=True),
        successor_masks=np.array(successor.masks, dtype=np.bool_, copy=True),
        successor_policy_sha256=_decision_receipt_sha256(successor),
        focal_already_noop=focal_already_noop,
    )


def _measurement_payload(value: _SuccessorMeasurement) -> dict[str, object]:
    return {
        "terminal_absorbing_zero": value.terminal_absorbing_zero,
        "focal_rate_bps": value.focal_rate_bps.hex(),
        "full_power_w": value.full_power_w.hex(),
        "without_focal_power_w": value.without_focal_power_w.hex(),
        "successor_actions": [int(action) for action in value.successor_actions.tolist()],
        "successor_masks": [
            [bool(item) for item in row.tolist()]
            for row in value.successor_masks
        ],
        "successor_actions_sha256": _array_sha256(
            value.successor_actions, dtype=np.dtype(np.int64)
        ),
        "successor_masks_sha256": _array_sha256(
            value.successor_masks, dtype=np.dtype(np.bool_)
        ),
        "successor_policy_sha256": value.successor_policy_sha256,
        "focal_already_noop": value.focal_already_noop,
    }


def capture_one_decision(
    runtime: Any,
    archive: Any,
    hybrid: object,
    fresh_q2: FreshQ2 | None,
    *,
    lineage: str,
    refresh_round: str,
    world_id: int,
    source_seed: int,
    target_step: int,
    focal_user: int,
    history: Sequence[np.ndarray],
    field: KeyedFadingField,
    interval_s: float,
    kappa_bits: float,
    lambda_bits_per_j: float,
) -> V07C2DecisionCapture:
    """Enumerate one native focal mask into matched V0.7 training rows."""

    if refresh_round not in {"bootstrap", "refresh"}:
        raise V07C2LiveAdapterError("refresh_round must be bootstrap or refresh")
    q_nets_raw_before = getattr(hybrid, "q_nets", None)
    try:
        q_nets_before = (
            None if q_nets_raw_before is None else tuple(q_nets_raw_before)
        )
    except TypeError as error:
        raise V07C2LiveAdapterError(
            "frozen Q1/Q2/Q3 network container is malformed"
        ) from error
    if q_nets_before is not None and len(q_nets_before) == 3:
        q1_network_sha256_before = frozen_network_digest(q_nets_before[0])
        q3_network_sha256_before = frozen_network_digest(q_nets_before[2])
    else:
        q1_network_sha256_before = ""
        q3_network_sha256_before = ""
    wrapped, _env_rng, observation = _replay_to_anchor(
        runtime,
        archive,
        source_seed=source_seed,
        field=field,
        history=history,
        target_step=target_step,
    )
    anchor, states_v07_q2 = _decision(
        hybrid,
        fresh_q2,
        wrapped,
        observation,
        interval_s=interval_s,
        kappa_bits=kappa_bits,
    )
    reference_actions = np.asarray(history[-1], dtype=np.int64)
    if not np.array_equal(anchor.actions, reference_actions):
        raise V07C2LiveAdapterError(
            "history anchor action disagrees with the declared behavior policy"
        )
    if type(focal_user) is not int or not 0 <= focal_user < int(runtime.users):
        raise V07C2LiveAdapterError("focal_user is outside the runtime")
    mask = np.asarray(anchor.masks[focal_user], dtype=np.bool_)
    coverage = V07C2DecisionCoverage(
        lineage=lineage,
        refresh_round=refresh_round,
        world_id=world_id,
        step_index=target_step,
        focal_user=focal_user,
        action_mask=mask,
    )
    anchor_policy_sha256 = _frozen_policy_sha256(hybrid, fresh_q2)
    rows: list[V07C2Row] = []
    branch_receipts: list[dict[str, object]] = []
    if coverage.mask_count:
        reference_action = int(reference_actions[focal_user])
        reference_measurement = _measure_branch_successor(
            runtime,
            archive,
            hybrid,
            fresh_q2,
            source_seed=source_seed,
            field=field,
            history=history,
            target_step=target_step,
            focal_user=focal_user,
            opening_actions=reference_actions,
            interval_s=interval_s,
            kappa_bits=kappa_bits,
        )
        for action in coverage.legal_actions:
            opening = focal_candidate_vector(
                reference_actions=reference_actions,
                masks=anchor.masks,
                focal_user=focal_user,
                candidate_action=action,
            )
            candidate_measurement = (
                reference_measurement
                if action == reference_action
                else _measure_branch_successor(
                    runtime,
                    archive,
                    hybrid,
                    fresh_q2,
                    source_seed=source_seed,
                    field=field,
                    history=history,
                    target_step=target_step,
                    focal_user=focal_user,
                    opening_actions=opening,
                    interval_s=interval_s,
                    kappa_bits=kappa_bits,
                )
            )
            if (
                candidate_measurement.terminal_absorbing_zero
                != reference_measurement.terminal_absorbing_zero
            ):
                raise V07C2LiveAdapterError(
                    "matched branches disagree on the episode horizon"
                )
            target = focal_next_surplus_target(
                lambda_bits_per_j=lambda_bits_per_j,
                interval_s=interval_s,
                candidate_focal_rate_bps=candidate_measurement.focal_rate_bps,
                reference_focal_rate_bps=reference_measurement.focal_rate_bps,
                candidate_full_power_w=candidate_measurement.full_power_w,
                candidate_without_focal_power_w=(
                    candidate_measurement.without_focal_power_w
                ),
                reference_full_power_w=reference_measurement.full_power_w,
                reference_without_focal_power_w=(
                    reference_measurement.without_focal_power_w
                ),
            )
            row = V07C2Row.from_target(
                lineage=lineage,
                refresh_round=refresh_round,
                world_id=world_id,
                step_index=target_step,
                focal_user=focal_user,
                state=states_v07_q2[focal_user],
                action_mask=mask,
                reference_action=reference_action,
                candidate_action=action,
                target=target,
            )
            row.verify()
            rows.append(row)
            branch_receipts.append(
                {
                    "schema": BRANCH_RECEIPT_SCHEMA,
                    "candidate_action": action,
                    "opening_actions": [int(value) for value in opening.tolist()],
                    "opening_actions_sha256": _array_sha256(
                        opening, dtype=np.dtype(np.int64)
                    ),
                    "opening_focal_difference_count": int(
                        np.count_nonzero(opening != reference_actions)
                    ),
                    "candidate": _measurement_payload(candidate_measurement),
                    "reference": _measurement_payload(reference_measurement),
                    "target_row_sha256": row.row_sha256,
                }
            )

    dataset = V07C2Dataset.from_records(rows=rows, coverage=(coverage,))
    q_nets_raw = getattr(hybrid, "q_nets", None)
    try:
        q_nets = None if q_nets_raw is None else tuple(q_nets_raw)
    except TypeError as error:
        raise V07C2LiveAdapterError("frozen Q1/Q2/Q3 network container is malformed") from error
    if q_nets is not None and len(q_nets) == 3:
        q1_network_sha256 = frozen_network_digest(q_nets[0])
        q3_network_sha256 = frozen_network_digest(q_nets[2])
        if (
            q1_network_sha256 != q1_network_sha256_before
            or q3_network_sha256 != q3_network_sha256_before
        ):
            raise V07C2LiveAdapterError(
                "frozen Q1/Q3 network bytes changed during capture"
            )
        frozen_network_receipt_complete = True
        selected_q3_rung = int(getattr(hybrid, "selected_q3_rung"))
    else:
        # W-116 uses a decision stub to exercise branch mechanics.  It is not
        # admissible as a D2 shard: the runner's strict merge rejects these
        # explicit empty network receipts.
        q1_network_sha256 = ""
        q3_network_sha256 = ""
        frozen_network_receipt_complete = False
        selected_q3_rung = 100
    body: dict[str, object] = {
        "schema": V07_C2_CAPTURE_SCHEMA,
        "lineage": lineage,
        "refresh_round": refresh_round,
        "world_id": world_id,
        "source_seed": source_seed,
        "target_step": target_step,
        "focal_user": focal_user,
        "formula_constants": {
            "lambda_bits_per_j": float(lambda_bits_per_j).hex(),
            "interval_s": float(interval_s).hex(),
            "kappa_bits": float(kappa_bits).hex(),
        },
        "q2_state_schema": V07_C2_Q2_STATE_SCHEMA,
        "q2_state_schema_sha256": V07_C2_Q2_STATE_SCHEMA_SHA256,
        "crn_sha256": field.root_digest,
        "anchor_policy_sha256": anchor_policy_sha256,
        "anchor_reference_actions": [int(action) for action in reference_actions.tolist()],
        "anchor_state_sha256": _array_sha256(
            states_v07_q2[focal_user], dtype=np.dtype(np.float32)
        ),
        "anchor_reference_actions_sha256": _array_sha256(
            reference_actions, dtype=np.dtype(np.int64)
        ),
        "native_legal_actions": list(coverage.legal_actions),
        "empty_mask": coverage.mask_count == 0,
        "q1_focal_surface_hex": [
            float(value).hex() for value in np.asarray(anchor.q1[focal_user], dtype=np.float64).tolist()
        ],
        "q3_focal_surface_hex": [
            float(value).hex() for value in np.asarray(anchor.q3[focal_user], dtype=np.float64).tolist()
        ],
        "q1_focal_surface_array_sha256": _array_sha256(
            anchor.q1[focal_user], dtype=np.dtype(np.float64)
        ),
        "q3_focal_surface_array_sha256": _array_sha256(
            anchor.q3[focal_user], dtype=np.dtype(np.float64)
        ),
        "q1_network_sha256": q1_network_sha256,
        "q3_network_sha256": q3_network_sha256,
        "frozen_network_receipt_complete": frozen_network_receipt_complete,
        "frozen_network_bytes_unchanged": (
            frozen_network_receipt_complete
            and q1_network_sha256 == q1_network_sha256_before
            and q3_network_sha256 == q3_network_sha256_before
        ),
        "selected_q3_rung": selected_q3_rung,
        "branch_receipt_schema": BRANCH_RECEIPT_SCHEMA,
        "branch_rows": branch_receipts,
        "dataset_sha256": dataset.corpus_sha256,
        "resident_legacy_q2_evaluated": False,
        "target_or_ee_selected": False,
        "branch_local_successor_decisions": True,
        "full_evaluation_noncommitting": True,
        "without_focal_evaluation_noncommitting": True,
        "focal_removal_only": True,
        "selection_outcome_blind": True,
        "retry_count": 0,
        "replacement_used": False,
        "test_record_used": False,
    }
    receipt = body | {"receipt_sha256": canonical_sha256(body)}
    capture = V07C2DecisionCapture(
        coverage=coverage,
        rows=tuple(rows),
        receipt=receipt,
    )
    capture.verify()
    return capture


__all__ = [
    "V07C2DecisionCapture",
    "V07C2LiveAdapterError",
    "V07_C2_CAPTURE_SCHEMA",
    "bind_behavior_action_at_anchor",
    "capture_one_decision",
    "frozen_network_digest",
]
