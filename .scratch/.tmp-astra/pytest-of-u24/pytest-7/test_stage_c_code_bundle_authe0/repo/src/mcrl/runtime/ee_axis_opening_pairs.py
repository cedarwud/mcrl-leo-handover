"""Fail-closed opening-pair data path for Multi-Catfish MCRL V0.3.

An opening comparison is one sealed, unilateral focal-action intervention in
one physical system.  The same raw comparison exposes both V0.3 opening
components, but its sealed source route decides which component may enter a
gradient:

* a C1 source row carries focal opening EE surplus to Q1;
* a C3 source row carries non-focal opening rate externality to Q3.

The adapter never duplicates a row across routes and never consumes legacy
reward columns.  Targets remain in native bits; the pairwise learner applies
the shared kappa normalization.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Iterable, Mapping

import numpy as np

from ..algorithms.ee_axis_pairwise import EEAxisPairBatch, EEAxisPairwiseTrainer
from ..errors import MCRLContractError
from .ee_surplus_targets import ee_surplus_axis_targets_v03


OPENING_PAIR_SCHEMA = "multi-catfish-mcrl-v03-opening-pair-v1"
OPENING_BATCH_SCHEMA = "multi-catfish-mcrl-v03-opening-route-batch-v1"
OPENING_ROUTES = ("C1", "C3")


class OpeningPairContractError(MCRLContractError):
    """A proposed opening comparison is not admissible V0.3 data."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise OpeningPairContractError(f"{field} must be lowercase SHA-256")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise OpeningPairContractError(f"{field} must be a nonempty trimmed string")
    return value


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise OpeningPairContractError(
            f"{field} must be a nonnegative exact integer"
        )
    return value


def _positive_float(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.number)
    ):
        raise OpeningPairContractError(f"{field} must be finite and positive")
    converted = float(value)
    if not math.isfinite(converted) or converted <= 0.0:
        raise OpeningPairContractError(f"{field} must be finite and positive")
    return converted


def _nonnegative_float(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.number)
    ):
        raise OpeningPairContractError(f"{field} must be finite and nonnegative")
    converted = float(value)
    if not math.isfinite(converted) or converted < 0.0:
        raise OpeningPairContractError(f"{field} must be finite and nonnegative")
    return converted


def _immutable_array(
    value: object,
    *,
    field: str,
    dtype: np.dtype[Any],
    ndim: int,
) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim != ndim:
        raise OpeningPairContractError(f"{field} must be {ndim}-dimensional")
    try:
        copied = np.array(array, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError) as error:
        raise OpeningPairContractError(f"{field} has an invalid dtype") from error
    if np.issubdtype(copied.dtype, np.floating) and not np.all(np.isfinite(copied)):
        raise OpeningPairContractError(f"{field} must be finite")
    copied.setflags(write=False)
    return copied


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _float_list(values: np.ndarray) -> list[float]:
    return [float(value) for value in values.tolist()]


def _record_payload(record: "EEAxisOpeningPair") -> dict[str, object]:
    return {
        "schema": OPENING_PAIR_SCHEMA,
        "source_route": record.source_route,
        "source_rule": record.source_rule,
        "source_policy_version": record.source_policy_version,
        "anchor_sha256": record.anchor_sha256,
        "source_manifest_sha256": record.source_manifest_sha256,
        "checkpoint_sha256": record.checkpoint_sha256,
        "common_random_field_sha256": record.common_random_field_sha256,
        "focal_user": record.focal_user,
        "state": _float_list(record.state),
        "action_mask": [bool(value) for value in record.action_mask.tolist()],
        "reference_action": record.reference_action,
        "candidate_action": record.candidate_action,
        "reference_joint_actions": [
            int(value) for value in record.reference_joint_actions.tolist()
        ],
        "candidate_joint_actions": [
            int(value) for value in record.candidate_joint_actions.tolist()
        ],
        "reference_rates_bps": _float_list(record.reference_rates_bps),
        "candidate_rates_bps": _float_list(record.candidate_rates_bps),
        "reference_system_power_hex": record.reference_system_power_w.hex(),
        "candidate_system_power_hex": record.candidate_system_power_w.hex(),
        "lambda_bits_per_j_hex": record.lambda_bits_per_j.hex(),
        "interval_s_hex": record.interval_s.hex(),
        "zeta1_focal_surplus_bits_hex": record.zeta1_focal_surplus_bits.hex(),
        "zeta3_nonfocal_externality_bits_hex": (
            record.zeta3_nonfocal_externality_bits.hex()
        ),
        "route_target_surplus_bits_hex": record.route_target_surplus_bits.hex(),
        "identity_residual_bits_hex": record.identity_residual_bits.hex(),
    }


def _pair_batch_payload(batch: EEAxisPairBatch) -> dict[str, object]:
    states = np.asarray(batch.states)
    reference = np.asarray(batch.reference_actions)
    candidate = np.asarray(batch.candidate_actions)
    targets = np.asarray(batch.target_surplus_bits)
    masks = np.asarray(batch.action_masks)
    return {
        "states": [[float(value) for value in row] for row in states.tolist()],
        "reference_actions": [int(value) for value in reference.tolist()],
        "candidate_actions": [int(value) for value in candidate.tolist()],
        "target_surplus_bits_hex": [float(value).hex() for value in targets],
        "action_masks": [
            [bool(value) for value in row] for row in masks.tolist()
        ],
    }


@dataclass(frozen=True)
class EEAxisOpeningPair:
    """One immutable C1-or-C3 opening comparison and its raw audit surface."""

    source_route: str
    source_rule: str
    source_policy_version: int
    anchor_sha256: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    common_random_field_sha256: str
    focal_user: int
    state: np.ndarray
    action_mask: np.ndarray
    reference_action: int
    candidate_action: int
    reference_joint_actions: np.ndarray
    candidate_joint_actions: np.ndarray
    reference_rates_bps: np.ndarray
    candidate_rates_bps: np.ndarray
    reference_system_power_w: float
    candidate_system_power_w: float
    lambda_bits_per_j: float
    interval_s: float
    zeta1_focal_surplus_bits: float
    zeta3_nonfocal_externality_bits: float
    route_target_surplus_bits: float
    identity_residual_bits: float
    comparison_sha256: str

    def verify(self) -> str:
        """Revalidate the content digest before batching or learning."""

        supplied = _digest(self.comparison_sha256, field="comparison_sha256")
        actual = _canonical_sha256(_record_payload(self))
        if supplied != actual:
            raise OpeningPairContractError(
                "opening comparison digest disagrees with its payload"
            )
        return actual


@dataclass(frozen=True)
class EEAxisOpeningRouteBatch:
    """A route-bound batch that cannot silently mix C1 and C3 rows."""

    route: str
    pair_batch: EEAxisPairBatch
    comparison_sha256s: tuple[str, ...]
    batch_sha256: str

    def verify(self) -> str:
        if self.route not in OPENING_ROUTES:
            raise OpeningPairContractError("opening batch route must be C1 or C3")
        if not self.comparison_sha256s:
            raise OpeningPairContractError("opening batch must contain comparisons")
        for index, digest in enumerate(self.comparison_sha256s):
            _digest(digest, field=f"comparison_sha256s[{index}]")
        states = np.asarray(self.pair_batch.states)
        masks = np.asarray(self.pair_batch.action_masks)
        if states.ndim != 2 or masks.ndim != 2:
            raise OpeningPairContractError("opening batch arrays must be matrices")
        if states.shape[0] != len(self.comparison_sha256s):
            raise OpeningPairContractError(
                "opening batch row count disagrees with comparison receipts"
            )
        self.pair_batch.validate(
            state_dim=int(states.shape[1]), action_dim=int(masks.shape[1])
        )
        payload = {
            "schema": OPENING_BATCH_SCHEMA,
            "route": self.route,
            "comparison_sha256s": list(self.comparison_sha256s),
            "pair_batch": _pair_batch_payload(self.pair_batch),
        }
        actual = _canonical_sha256(payload)
        if _digest(self.batch_sha256, field="batch_sha256") != actual:
            raise OpeningPairContractError(
                "opening route batch digest disagrees with its comparisons"
            )
        return actual


def build_opening_pair(
    *,
    source_route: str,
    source_rule: str,
    source_policy_version: int,
    anchor_sha256: str,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    common_random_field_sha256: str,
    focal_user: int,
    state: object,
    action_mask: object,
    reference_action: int,
    candidate_action: int,
    reference_joint_actions: object,
    candidate_joint_actions: object,
    reference_rates_bps: object,
    candidate_rates_bps: object,
    reference_system_power_w: float,
    candidate_system_power_w: float,
    lambda_bits_per_j: float,
    interval_s: float,
) -> EEAxisOpeningPair:
    """Validate and materialize one native-bit opening comparison."""

    if source_route not in OPENING_ROUTES:
        raise OpeningPairContractError("source_route must be C1 or C3")
    rule = _text(source_rule, field="source_rule")
    policy_version = _exact_nonnegative_int(
        source_policy_version, field="source_policy_version"
    )
    if policy_version == 0:
        raise OpeningPairContractError("V0.3 source_policy_version must be positive")
    authority = {
        "anchor_sha256": _digest(anchor_sha256, field="anchor_sha256"),
        "source_manifest_sha256": _digest(
            source_manifest_sha256, field="source_manifest_sha256"
        ),
        "checkpoint_sha256": _digest(checkpoint_sha256, field="checkpoint_sha256"),
        "common_random_field_sha256": _digest(
            common_random_field_sha256, field="common_random_field_sha256"
        ),
    }
    focal = _exact_nonnegative_int(focal_user, field="focal_user")
    state_array = _immutable_array(
        state, field="state", dtype=np.dtype(np.float32), ndim=1
    )
    raw_mask = np.asarray(action_mask)
    if raw_mask.dtype != np.bool_:
        raise OpeningPairContractError("action_mask must have Boolean dtype")
    mask_array = _immutable_array(
        action_mask, field="action_mask", dtype=np.dtype(np.bool_), ndim=1
    )
    if state_array.size == 0 or mask_array.size == 0:
        raise OpeningPairContractError("state and action_mask must be nonempty")
    if type(reference_action) is not int or type(candidate_action) is not int:
        raise OpeningPairContractError("opening actions must be exact integers")
    if reference_action == candidate_action:
        raise OpeningPairContractError("opening candidate must differ from reference")
    for name, action in (
        ("reference_action", reference_action),
        ("candidate_action", candidate_action),
    ):
        if not 0 <= action < mask_array.size or not bool(mask_array[action]):
            raise OpeningPairContractError(
                f"{name} must be legal under the sealed opening mask"
            )

    raw_reference_joint = np.asarray(reference_joint_actions)
    raw_candidate_joint = np.asarray(candidate_joint_actions)
    if (
        not np.issubdtype(raw_reference_joint.dtype, np.integer)
        or np.issubdtype(raw_reference_joint.dtype, np.bool_)
        or not np.issubdtype(raw_candidate_joint.dtype, np.integer)
        or np.issubdtype(raw_candidate_joint.dtype, np.bool_)
    ):
        raise OpeningPairContractError("joint action vectors must have integer dtype")
    reference_joint = _immutable_array(
        reference_joint_actions,
        field="reference_joint_actions",
        dtype=np.dtype(np.int64),
        ndim=1,
    )
    candidate_joint = _immutable_array(
        candidate_joint_actions,
        field="candidate_joint_actions",
        dtype=np.dtype(np.int64),
        ndim=1,
    )
    if reference_joint.shape != candidate_joint.shape or reference_joint.size == 0:
        raise OpeningPairContractError(
            "reference and candidate joint actions must have the same nonempty shape"
        )
    if focal >= reference_joint.size:
        raise OpeningPairContractError("focal_user lies outside the joint action vector")
    changed = np.flatnonzero(reference_joint != candidate_joint)
    if changed.tolist() != [focal]:
        raise OpeningPairContractError(
            "opening branches must differ only in the focal user's action"
        )
    if (
        int(reference_joint[focal]) != reference_action
        or int(candidate_joint[focal]) != candidate_action
    ):
        raise OpeningPairContractError(
            "focal scalar actions disagree with the joint action vectors"
        )

    reference_rates = _immutable_array(
        reference_rates_bps,
        field="reference_rates_bps",
        dtype=np.dtype(np.float64),
        ndim=1,
    )
    candidate_rates = _immutable_array(
        candidate_rates_bps,
        field="candidate_rates_bps",
        dtype=np.dtype(np.float64),
        ndim=1,
    )
    if (
        reference_rates.shape != candidate_rates.shape
        or reference_rates.size != reference_joint.size
    ):
        raise OpeningPairContractError(
            "opening rate vectors must match the joint user dimension"
        )
    if np.any(reference_rates < 0.0) or np.any(candidate_rates < 0.0):
        raise OpeningPairContractError("opening rates must be nonnegative")
    reference_power = _nonnegative_float(
        reference_system_power_w, field="reference_system_power_w"
    )
    candidate_power = _nonnegative_float(
        candidate_system_power_w, field="candidate_system_power_w"
    )
    multiplier = _positive_float(lambda_bits_per_j, field="lambda_bits_per_j")
    interval = _positive_float(interval_s, field="interval_s")

    targets = ee_surplus_axis_targets_v03(
        lambda_bits_per_j=multiplier,
        interval_s=interval,
        focal_user=focal,
        reference_system_rates_bps=reference_rates[None, :],
        reference_system_power_w=np.asarray([reference_power], dtype=np.float64),
        candidate_system_rates_bps=candidate_rates[None, :],
        candidate_system_power_w=np.asarray([candidate_power], dtype=np.float64),
    )
    if targets.z2_temporal_surplus_bits != 0.0:
        raise OpeningPairContractError("an opening-only row cannot carry zeta2")
    target = (
        targets.z1_focal_surplus_bits
        if source_route == "C1"
        else targets.z3_nonfocal_externality_bits
    )
    placeholder = EEAxisOpeningPair(
        source_route=source_route,
        source_rule=rule,
        source_policy_version=policy_version,
        anchor_sha256=authority["anchor_sha256"],
        source_manifest_sha256=authority["source_manifest_sha256"],
        checkpoint_sha256=authority["checkpoint_sha256"],
        common_random_field_sha256=authority["common_random_field_sha256"],
        focal_user=focal,
        state=state_array,
        action_mask=mask_array,
        reference_action=reference_action,
        candidate_action=candidate_action,
        reference_joint_actions=reference_joint,
        candidate_joint_actions=candidate_joint,
        reference_rates_bps=reference_rates,
        candidate_rates_bps=candidate_rates,
        reference_system_power_w=reference_power,
        candidate_system_power_w=candidate_power,
        lambda_bits_per_j=multiplier,
        interval_s=interval,
        zeta1_focal_surplus_bits=float(targets.z1_focal_surplus_bits),
        zeta3_nonfocal_externality_bits=float(
            targets.z3_nonfocal_externality_bits
        ),
        route_target_surplus_bits=float(target),
        identity_residual_bits=float(targets.identity_residual_bits),
        comparison_sha256="0" * 64,
    )
    digest = _canonical_sha256(_record_payload(placeholder))
    record = EEAxisOpeningPair(
        **{
            **placeholder.__dict__,
            "comparison_sha256": digest,
        }
    )
    record.verify()
    return record


def build_opening_route_batch(
    records: Iterable[EEAxisOpeningPair],
) -> EEAxisOpeningRouteBatch:
    """Stack same-route records into the exact pairwise learner surface."""

    rows = tuple(records)
    if not rows:
        raise OpeningPairContractError("opening route batch cannot be empty")
    if any(not isinstance(row, EEAxisOpeningPair) for row in rows):
        raise OpeningPairContractError("opening batch contains a non-pair row")
    route = rows[0].source_route
    if route not in OPENING_ROUTES or any(row.source_route != route for row in rows):
        raise OpeningPairContractError("opening route batch cannot mix C1 and C3")
    for row in rows:
        row.verify()
    state_dim = rows[0].state.size
    action_dim = rows[0].action_mask.size
    if any(
        row.state.size != state_dim or row.action_mask.size != action_dim
        for row in rows
    ):
        raise OpeningPairContractError(
            "opening route batch has inconsistent state or action dimensions"
        )
    states = np.stack([row.state for row in rows]).astype(np.float32, copy=False)
    references = np.asarray([row.reference_action for row in rows], dtype=np.int64)
    candidates = np.asarray([row.candidate_action for row in rows], dtype=np.int64)
    targets = np.asarray(
        [row.route_target_surplus_bits for row in rows], dtype=np.float64
    )
    masks = np.stack([row.action_mask for row in rows]).astype(np.bool_, copy=False)
    for array in (states, references, candidates, targets, masks):
        array.setflags(write=False)
    pair_batch = EEAxisPairBatch(
        states=states,
        reference_actions=references,
        candidate_actions=candidates,
        target_surplus_bits=targets,
        action_masks=masks,
    )
    comparison_sha256s = tuple(row.comparison_sha256 for row in rows)
    digest = _canonical_sha256(
        {
            "schema": OPENING_BATCH_SCHEMA,
            "route": route,
            "comparison_sha256s": list(comparison_sha256s),
            "pair_batch": _pair_batch_payload(pair_batch),
        }
    )
    envelope = EEAxisOpeningRouteBatch(
        route=route,
        pair_batch=pair_batch,
        comparison_sha256s=comparison_sha256s,
        batch_sha256=digest,
    )
    envelope.verify()
    return envelope


def update_opening_route(
    trainer: EEAxisPairwiseTrainer,
    batch: EEAxisOpeningRouteBatch,
) -> Mapping[str, float | int | str]:
    """Update only the Q function bound by the sealed opening source route."""

    if not isinstance(trainer, EEAxisPairwiseTrainer):
        raise OpeningPairContractError("trainer must be EEAxisPairwiseTrainer")
    if not isinstance(batch, EEAxisOpeningRouteBatch):
        raise OpeningPairContractError("batch must be EEAxisOpeningRouteBatch")
    batch.verify()
    return trainer.update_route(batch.route, batch.pair_batch)


__all__ = [
    "EEAxisOpeningPair",
    "EEAxisOpeningRouteBatch",
    "OPENING_BATCH_SCHEMA",
    "OPENING_PAIR_SCHEMA",
    "OPENING_ROUTES",
    "OpeningPairContractError",
    "build_opening_pair",
    "build_opening_route_batch",
    "update_opening_route",
]
