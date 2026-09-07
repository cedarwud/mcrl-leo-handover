"""Immutable V0.7 C2 focal-next training corpus.

The source side of V0.7 is a *decision* corpus, rather than a fixed action
table.  A decision is identified by ``(lineage, refresh_round, world, step,
focal_user)`` and carries one native boolean action mask.  Non-empty
decisions expand to exactly one pair row per legal candidate; empty decisions
remain in :class:`V07C2DecisionCoverage` so that missing coverage cannot be
silently mistaken for an empty mask.

This module only defines the immutable source/batch boundary.  It does not
run a simulator, select an action, perform an on-policy rollout, or train a
network.  The target receipt is the signed focal-next value produced by
``ee_axis_v07_c2_focal_next``; negative values are deliberately retained.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

import numpy as np

from ..algorithms.ee_axis_pairwise import EEAxisPairBatch
from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_v07_c2_state import (
    V07_C2_Q2_STATE_DIM,
    V07_C2_Q2_STATE_SCHEMA,
    V07_C2_Q2_STATE_SCHEMA_SHA256,
)
from .ee_axis_v07_c2_focal_next import (
    FocalNextSurplus,
    V07_C2_TARGET_SCHEMA,
)


V07_C2_DATASET_SCHEMA = "multi-catfish-mcrl-v07-c2-focal-next-dataset-v1"
V07_C2_ROW_SCHEMA = "multi-catfish-mcrl-v07-c2-focal-next-row-v1"
V07_C2_COVERAGE_SCHEMA = "multi-catfish-mcrl-v07-c2-decision-coverage-v1"
V07_C2_BATCH_SCHEMA = "multi-catfish-mcrl-v07-c2-focal-next-batch-v1"


class V07C2DatasetError(MCRLContractError):
    """A V0.7 C2 row, decision coverage, or corpus is malformed."""


def canonical_json_bytes(payload: object) -> bytes:
    """Encode finite canonical JSON used by all V0.7 C2 digests."""

    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V07C2DatasetError("payload is not canonical finite JSON") from error


def canonical_sha256(payload: object) -> str:
    """Return the SHA-256 of canonical JSON without a trailing newline."""

    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise V07C2DatasetError(f"{field} must be an exact integer >= {minimum}")
    return value


def _identity_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise V07C2DatasetError(f"{field} must be a nonempty trimmed string")
    return value


def _round_value(value: object) -> int | str:
    """Accept integer refresh counters and named bootstrap rounds.

    The type tag is retained in canonical ordering, so integer ``0`` and
    string ``"0"`` cannot collide or acquire an implementation-dependent
    order.
    """

    if type(value) is int:
        if value < 0:
            raise V07C2DatasetError("refresh_round must be an integer >= 0")
        return value
    if isinstance(value, str) and value and value == value.strip():
        return value
    raise V07C2DatasetError("refresh_round must be an integer or named round")


def _round_sort_key(value: int | str) -> tuple[int, int | str]:
    if type(value) is int:
        return (0, value)
    return (1, value)


def _state(value: object, *, field: str = "state") -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != (V07_C2_Q2_STATE_DIM,):
        raise V07C2DatasetError(
            f"{field} must have shape ({V07_C2_Q2_STATE_DIM},), got {raw.shape}"
        )
    try:
        copied = np.array(raw, dtype=np.float32, copy=True, order="C")
    except (TypeError, ValueError) as error:
        raise V07C2DatasetError(f"{field} must be float32-compatible") from error
    if not np.all(np.isfinite(copied)):
        raise V07C2DatasetError(f"{field} must be finite")
    copied.setflags(write=False)
    return copied


def _mask(value: object, *, field: str = "action_mask") -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != (NUM_ACTIONS,) or raw.dtype != np.bool_:
        raise V07C2DatasetError(
            f"{field} must be boolean shape ({NUM_ACTIONS},), got "
            f"{raw.shape} {raw.dtype}"
        )
    copied = np.array(raw, dtype=np.bool_, copy=True, order="C")
    copied.setflags(write=False)
    return copied


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise V07C2DatasetError(f"{field} must be a finite real number")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise V07C2DatasetError(f"{field} must be a finite real number") from error
    if not math.isfinite(result):
        raise V07C2DatasetError(f"{field} must be finite")
    return result


def _positive(value: object, *, field: str) -> float:
    result = _finite(value, field=field)
    if result <= 0.0:
        raise V07C2DatasetError(f"{field} must be strictly positive")
    return result


def _target(target: object) -> FocalNextSurplus:
    if not isinstance(target, FocalNextSurplus):
        raise V07C2DatasetError(
            "target must be a FocalNextSurplus receipt from the V0.7 formula"
        )
    if target.schema != V07_C2_TARGET_SCHEMA:
        raise V07C2DatasetError("target schema is stale")

    z2 = _finite(target.z2_focal_next_surplus_bits, field="target.z2")
    rate_delta = _finite(
        target.focal_next_rate_delta_bits,
        field="target.focal_next_rate_delta_bits",
    )
    candidate_rate = _finite(
        target.candidate_focal_rate_bps,
        field="target.candidate_focal_rate_bps",
    )
    reference_rate = _finite(
        target.reference_focal_rate_bps,
        field="target.reference_focal_rate_bps",
    )
    energy_delta = _finite(
        target.focal_next_marginal_energy_delta_j,
        field="target.focal_next_marginal_energy_delta_j",
    )
    candidate_full = _finite(
        target.candidate_full_power_w,
        field="target.candidate_full_power_w",
    )
    candidate_without = _finite(
        target.candidate_without_focal_power_w,
        field="target.candidate_without_focal_power_w",
    )
    reference_full = _finite(
        target.reference_full_power_w,
        field="target.reference_full_power_w",
    )
    reference_without = _finite(
        target.reference_without_focal_power_w,
        field="target.reference_without_focal_power_w",
    )
    candidate_marginal = _finite(
        target.candidate_focal_marginal_power_w,
        field="target.candidate_focal_marginal_power_w",
    )
    reference_marginal = _finite(
        target.reference_focal_marginal_power_w,
        field="target.reference_focal_marginal_power_w",
    )
    multiplier = _positive(target.lambda_bits_per_j, field="target.lambda_bits_per_j")
    interval = _positive(target.interval_s, field="target.interval_s")
    # Powers themselves are physical non-negative quantities.  Their
    # differences are signed estimands and are never clipped here.
    if any(
        value < 0.0
        for value in (
            candidate_rate,
            reference_rate,
            candidate_full,
            candidate_without,
            reference_full,
            reference_without,
        )
    ):
        raise V07C2DatasetError("target rate and power terms must be non-negative")
    if (
        candidate_marginal != candidate_full - candidate_without
        or reference_marginal != reference_full - reference_without
    ):
        raise V07C2DatasetError("target marginal power receipt is inconsistent")
    expected_rate = interval * (candidate_rate - reference_rate)
    expected_energy = interval * (
        candidate_marginal - reference_marginal
    )
    expected_z2 = rate_delta - multiplier * expected_energy
    if (
        rate_delta != expected_rate
        or energy_delta != expected_energy
        or z2 != expected_z2
    ):
        raise V07C2DatasetError("target receipt arithmetic is inconsistent")
    return target


def _float_hex(value: object) -> str:
    return _finite(value, field="float").hex()


def _decode_float(value: object, *, field: str) -> float:
    if not isinstance(value, str):
        raise V07C2DatasetError(f"{field} must be a hexadecimal float")
    try:
        result = float.fromhex(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise V07C2DatasetError(f"{field} must be a hexadecimal float") from error
    if not math.isfinite(result):
        raise V07C2DatasetError(f"{field} must be finite")
    if result.hex() != value:
        raise V07C2DatasetError(f"{field} is not canonical hexadecimal float")
    return result


def _target_payload(target: FocalNextSurplus) -> dict[str, object]:
    _target(target)
    return {
        "schema": target.schema,
        "z2_focal_next_surplus_bits": _float_hex(target.z2_focal_next_surplus_bits),
        "focal_next_rate_delta_bits": _float_hex(target.focal_next_rate_delta_bits),
        "focal_next_marginal_energy_delta_j": _float_hex(
            target.focal_next_marginal_energy_delta_j
        ),
        "candidate_focal_rate_bps": _float_hex(target.candidate_focal_rate_bps),
        "reference_focal_rate_bps": _float_hex(target.reference_focal_rate_bps),
        "candidate_focal_marginal_power_w": _float_hex(
            target.candidate_focal_marginal_power_w
        ),
        "reference_focal_marginal_power_w": _float_hex(
            target.reference_focal_marginal_power_w
        ),
        "candidate_full_power_w": _float_hex(target.candidate_full_power_w),
        "candidate_without_focal_power_w": _float_hex(
            target.candidate_without_focal_power_w
        ),
        "reference_full_power_w": _float_hex(target.reference_full_power_w),
        "reference_without_focal_power_w": _float_hex(
            target.reference_without_focal_power_w
        ),
        "lambda_bits_per_j": _float_hex(target.lambda_bits_per_j),
        "interval_s": _float_hex(target.interval_s),
    }


def _decode_target(value: object) -> FocalNextSurplus:
    if not isinstance(value, Mapping):
        raise V07C2DatasetError("target receipt must be an object")
    expected = {
        "schema",
        "z2_focal_next_surplus_bits",
        "focal_next_rate_delta_bits",
        "focal_next_marginal_energy_delta_j",
        "candidate_focal_rate_bps",
        "reference_focal_rate_bps",
        "candidate_focal_marginal_power_w",
        "reference_focal_marginal_power_w",
        "candidate_full_power_w",
        "candidate_without_focal_power_w",
        "reference_full_power_w",
        "reference_without_focal_power_w",
        "lambda_bits_per_j",
        "interval_s",
    }
    if set(value) != expected:
        raise V07C2DatasetError("target receipt schema is unexpected")
    target = FocalNextSurplus(
        z2_focal_next_surplus_bits=_decode_float(
            value["z2_focal_next_surplus_bits"],
            field="target.z2_focal_next_surplus_bits",
        ),
        focal_next_rate_delta_bits=_decode_float(
            value["focal_next_rate_delta_bits"],
            field="target.focal_next_rate_delta_bits",
        ),
        focal_next_marginal_energy_delta_j=_decode_float(
            value["focal_next_marginal_energy_delta_j"],
            field="target.focal_next_marginal_energy_delta_j",
        ),
        candidate_focal_rate_bps=_decode_float(
            value["candidate_focal_rate_bps"],
            field="target.candidate_focal_rate_bps",
        ),
        reference_focal_rate_bps=_decode_float(
            value["reference_focal_rate_bps"],
            field="target.reference_focal_rate_bps",
        ),
        candidate_focal_marginal_power_w=_decode_float(
            value["candidate_focal_marginal_power_w"],
            field="target.candidate_focal_marginal_power_w",
        ),
        reference_focal_marginal_power_w=_decode_float(
            value["reference_focal_marginal_power_w"],
            field="target.reference_focal_marginal_power_w",
        ),
        candidate_full_power_w=_decode_float(
            value["candidate_full_power_w"], field="target.candidate_full_power_w"
        ),
        candidate_without_focal_power_w=_decode_float(
            value["candidate_without_focal_power_w"],
            field="target.candidate_without_focal_power_w",
        ),
        reference_full_power_w=_decode_float(
            value["reference_full_power_w"], field="target.reference_full_power_w"
        ),
        reference_without_focal_power_w=_decode_float(
            value["reference_without_focal_power_w"],
            field="target.reference_without_focal_power_w",
        ),
        lambda_bits_per_j=_decode_float(
            value["lambda_bits_per_j"], field="target.lambda_bits_per_j"
        ),
        interval_s=_decode_float(value["interval_s"], field="target.interval_s"),
        schema=value["schema"],
    )
    _target(target)
    return target


def _row_sort_key(row: "V07C2Row") -> tuple[Any, ...]:
    return row.decision_key_sort + (row.candidate_action,)


@dataclass(frozen=True)
class V07C2DecisionCoverage:
    """The native mask for one pre-decision, including an empty mask."""

    lineage: str
    refresh_round: int | str
    world_id: int
    step_index: int
    focal_user: int
    action_mask: np.ndarray
    schema: str = V07_C2_COVERAGE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != V07_C2_COVERAGE_SCHEMA:
            raise V07C2DatasetError("decision coverage schema is stale")
        object.__setattr__(self, "lineage", _identity_text(self.lineage, field="lineage"))
        object.__setattr__(self, "refresh_round", _round_value(self.refresh_round))
        object.__setattr__(self, "world_id", _exact_int(self.world_id, field="world_id"))
        object.__setattr__(self, "step_index", _exact_int(self.step_index, field="step_index"))
        object.__setattr__(self, "focal_user", _exact_int(self.focal_user, field="focal_user"))
        object.__setattr__(self, "action_mask", _mask(self.action_mask))

    @property
    def user(self) -> int:
        """Alias matching the five-component decision identity."""

        return self.focal_user

    @property
    def key(self) -> tuple[str, int | str, int, int, int]:
        return (
            self.lineage,
            self.refresh_round,
            self.world_id,
            self.step_index,
            self.focal_user,
        )

    @property
    def decision_key_sort(self) -> tuple[Any, ...]:
        return (
            self.lineage,
            _round_sort_key(self.refresh_round),
            self.world_id,
            self.step_index,
            self.focal_user,
        )

    @property
    def legal_actions(self) -> tuple[int, ...]:
        return tuple(int(value) for value in np.flatnonzero(self.action_mask))

    @property
    def mask_count(self) -> int:
        return len(self.legal_actions)

    def verify(self) -> None:
        if self.schema != V07_C2_COVERAGE_SCHEMA:
            raise V07C2DatasetError("decision coverage schema is stale")
        _mask(self.action_mask)

    def to_payload(self) -> dict[str, object]:
        self.verify()
        return {
            "schema": self.schema,
            "lineage": self.lineage,
            "refresh_round": self.refresh_round,
            "world_id": self.world_id,
            "step_index": self.step_index,
            "focal_user": self.focal_user,
            "action_mask": [bool(value) for value in self.action_mask.tolist()],
        }


@dataclass(frozen=True)
class V07C2Row:
    """One candidate/reference row for one native-mask decision."""

    lineage: str
    refresh_round: int | str
    world_id: int
    step_index: int
    focal_user: int
    state: np.ndarray
    action_mask: np.ndarray
    reference_action: int
    candidate_action: int
    target: FocalNextSurplus
    schema: str = V07_C2_ROW_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != V07_C2_ROW_SCHEMA:
            raise V07C2DatasetError("dataset row schema is stale")
        object.__setattr__(self, "lineage", _identity_text(self.lineage, field="lineage"))
        object.__setattr__(self, "refresh_round", _round_value(self.refresh_round))
        object.__setattr__(self, "world_id", _exact_int(self.world_id, field="world_id"))
        object.__setattr__(self, "step_index", _exact_int(self.step_index, field="step_index"))
        object.__setattr__(self, "focal_user", _exact_int(self.focal_user, field="focal_user"))
        object.__setattr__(self, "state", _state(self.state))
        object.__setattr__(self, "action_mask", _mask(self.action_mask))
        object.__setattr__(self, "reference_action", _exact_int(self.reference_action, field="reference_action"))
        object.__setattr__(self, "candidate_action", _exact_int(self.candidate_action, field="candidate_action"))
        object.__setattr__(self, "target", _target(self.target))

    @classmethod
    def from_target(
        cls,
        *,
        lineage: str,
        refresh_round: int | str,
        world_id: int,
        step_index: int,
        focal_user: int,
        state: np.ndarray,
        action_mask: np.ndarray,
        reference_action: int,
        candidate_action: int,
        target: FocalNextSurplus,
    ) -> "V07C2Row":
        """Explicit constructor documenting the formula receipt boundary."""

        return cls(
            lineage=lineage,
            refresh_round=refresh_round,
            world_id=world_id,
            step_index=step_index,
            focal_user=focal_user,
            state=state,
            action_mask=action_mask,
            reference_action=reference_action,
            candidate_action=candidate_action,
            target=target,
        )

    @property
    def user(self) -> int:
        return self.focal_user

    @property
    def key(self) -> tuple[str, int | str, int, int, int]:
        return (
            self.lineage,
            self.refresh_round,
            self.world_id,
            self.step_index,
            self.focal_user,
        )

    @property
    def decision_key_sort(self) -> tuple[Any, ...]:
        return (
            self.lineage,
            _round_sort_key(self.refresh_round),
            self.world_id,
            self.step_index,
            self.focal_user,
        )

    @property
    def z2_focal_next_surplus_bits(self) -> float:
        return self.target.z2_focal_next_surplus_bits

    @property
    def target_surplus_bits(self) -> float:
        """Pair-batch naming alias for the formula's signed zeta2 value."""

        return self.z2_focal_next_surplus_bits

    def verify(self) -> None:
        if self.schema != V07_C2_ROW_SCHEMA:
            raise V07C2DatasetError("dataset row schema is stale")
        _state(self.state)
        mask = _mask(self.action_mask)
        _target(self.target)
        for field, action in (
            ("reference_action", self.reference_action),
            ("candidate_action", self.candidate_action),
        ):
            _exact_int(action, field=field)
            if action >= NUM_ACTIONS:
                raise V07C2DatasetError(f"{field} is outside the native action space")
            if not bool(mask[action]):
                raise V07C2DatasetError(f"{field} is illegal under the native mask")
        # Equal branches are a mandatory exact-zero control.  Do not apply an
        # absolute-value or positivity filter to unequal signed targets.
        if self.candidate_action == self.reference_action and self.z2_focal_next_surplus_bits != 0.0:
            raise V07C2DatasetError(
                "candidate==reference rows must have exact zero target"
            )

    def to_payload(self) -> dict[str, object]:
        self.verify()
        return {
            "schema": self.schema,
            "lineage": self.lineage,
            "refresh_round": self.refresh_round,
            "world_id": self.world_id,
            "step_index": self.step_index,
            "focal_user": self.focal_user,
            "state": [_float_hex(value) for value in self.state.tolist()],
            "action_mask": [bool(value) for value in self.action_mask.tolist()],
            "reference_action": self.reference_action,
            "candidate_action": self.candidate_action,
            "target": _target_payload(self.target),
        }

    @property
    def row_sha256(self) -> str:
        return canonical_sha256(self.to_payload())


def _decode_coverage(value: object) -> V07C2DecisionCoverage:
    if not isinstance(value, Mapping):
        raise V07C2DatasetError("coverage entry must be an object")
    expected = {
        "schema",
        "lineage",
        "refresh_round",
        "world_id",
        "step_index",
        "focal_user",
        "action_mask",
    }
    if set(value) != expected:
        raise V07C2DatasetError("coverage entry schema is unexpected")
    return V07C2DecisionCoverage(
        schema=value["schema"],
        lineage=value["lineage"],
        refresh_round=value["refresh_round"],
        world_id=value["world_id"],
        step_index=value["step_index"],
        focal_user=value["focal_user"],
        action_mask=value["action_mask"],
    )


def _decode_row(value: object) -> V07C2Row:
    if not isinstance(value, Mapping):
        raise V07C2DatasetError("dataset row must be an object")
    expected = {
        "schema",
        "lineage",
        "refresh_round",
        "world_id",
        "step_index",
        "focal_user",
        "state",
        "action_mask",
        "reference_action",
        "candidate_action",
        "target",
    }
    if set(value) != expected:
        raise V07C2DatasetError("dataset row schema is unexpected")
    state_value = value["state"]
    if not isinstance(state_value, list) or len(state_value) != V07_C2_Q2_STATE_DIM:
        raise V07C2DatasetError("dataset row state has the wrong dimension")
    state = np.asarray(
        [_decode_float(item, field=f"state[{index}]") for index, item in enumerate(state_value)],
        dtype=np.float32,
    )
    row = V07C2Row(
        schema=value["schema"],
        lineage=value["lineage"],
        refresh_round=value["refresh_round"],
        world_id=value["world_id"],
        step_index=value["step_index"],
        focal_user=value["focal_user"],
        state=state,
        action_mask=value["action_mask"],
        reference_action=value["reference_action"],
        candidate_action=value["candidate_action"],
        target=_decode_target(value["target"]),
    )
    return row


@dataclass(frozen=True)
class V07C2Dataset:
    """A deterministic, mask-complete V0.7 C2 corpus."""

    rows: tuple[V07C2Row, ...]
    coverage: tuple[V07C2DecisionCoverage, ...]
    schema: str = V07_C2_DATASET_SCHEMA
    target_schema: str = V07_C2_TARGET_SCHEMA
    state_schema: str = V07_C2_Q2_STATE_SCHEMA
    state_schema_sha256: str = V07_C2_Q2_STATE_SCHEMA_SHA256

    def __post_init__(self) -> None:
        if self.schema != V07_C2_DATASET_SCHEMA:
            raise V07C2DatasetError("dataset schema is stale")
        if self.target_schema != V07_C2_TARGET_SCHEMA:
            raise V07C2DatasetError("dataset target schema is stale")
        if (
            self.state_schema != V07_C2_Q2_STATE_SCHEMA
            or self.state_schema_sha256 != V07_C2_Q2_STATE_SCHEMA_SHA256
        ):
            raise V07C2DatasetError("dataset state schema is stale")
        rows = tuple(self.rows)
        coverage = tuple(self.coverage)
        if not coverage:
            raise V07C2DatasetError("dataset must declare at least one decision")
        if any(not isinstance(row, V07C2Row) for row in rows):
            raise V07C2DatasetError("dataset rows contain a non-row")
        if any(not isinstance(item, V07C2DecisionCoverage) for item in coverage):
            raise V07C2DatasetError("dataset coverage contains a non-coverage entry")
        object.__setattr__(self, "rows", tuple(sorted(rows, key=_row_sort_key)))
        object.__setattr__(
            self,
            "coverage",
            tuple(sorted(coverage, key=lambda item: item.decision_key_sort)),
        )
        self.verify()

    @classmethod
    def from_records(
        cls,
        rows: Iterable[V07C2Row],
        coverage: Iterable[V07C2DecisionCoverage],
    ) -> "V07C2Dataset":
        return cls(rows=tuple(rows), coverage=tuple(coverage))

    def verify(self) -> str:
        """Validate all rows and return the deterministic corpus digest."""

        row_groups: dict[tuple[str, int | str, int, int, int], list[V07C2Row]] = defaultdict(list)
        row_identities: set[tuple[tuple[str, int | str, int, int, int], int]] = set()
        for index, row in enumerate(self.rows):
            row.verify()
            if index and _row_sort_key(self.rows[index - 1]) > _row_sort_key(row):
                raise V07C2DatasetError("dataset rows are not deterministically ordered")
            identity = (row.key, row.candidate_action)
            if identity in row_identities:
                raise V07C2DatasetError("dataset contains duplicate decision/candidate rows")
            row_identities.add(identity)
            row_groups[row.key].append(row)

        coverage_by_key: dict[tuple[str, int | str, int, int, int], V07C2DecisionCoverage] = {}
        for index, item in enumerate(self.coverage):
            item.verify()
            if index and self.coverage[index - 1].decision_key_sort > item.decision_key_sort:
                raise V07C2DatasetError("decision coverage is not deterministically ordered")
            if item.key in coverage_by_key:
                raise V07C2DatasetError("dataset contains duplicate decision coverage")
            coverage_by_key[item.key] = item

        # Coverage is intentionally a superset of row groups: an empty native
        # mask has no pair rows but must still be represented.  Every emitted
        # row group, however, must have exactly one coverage record.
        if not set(row_groups).issubset(coverage_by_key):
            raise V07C2DatasetError("dataset has missing or orphaned decision coverage")

        for key, item in coverage_by_key.items():
            group = row_groups.get(key, [])
            expected_actions = item.legal_actions
            observed_actions = tuple(row.candidate_action for row in group)
            if observed_actions != tuple(sorted(observed_actions)):
                raise V07C2DatasetError("candidate rows are not deterministically ordered")
            if len(set(observed_actions)) != len(observed_actions):
                raise V07C2DatasetError("candidate action repeats within a decision")
            if observed_actions != expected_actions:
                raise V07C2DatasetError(
                    "candidate actions must equal the native legal mask exactly once"
                )
            if group:
                reference = group[0].reference_action
                state = group[0].state
                for row in group[1:]:
                    if row.reference_action != reference:
                        raise V07C2DatasetError(
                            "reference action drifted within one decision"
                        )
                    if not np.array_equal(row.state, state):
                        raise V07C2DatasetError(
                            "pre-decision state drifted within one decision"
                        )
            for row in group:
                if not np.array_equal(row.action_mask, item.action_mask):
                    raise V07C2DatasetError("decision mask drifted across candidate rows")
                if row.reference_action not in expected_actions:
                    raise V07C2DatasetError("reference action is outside the decision mask")
            if not expected_actions and group:
                raise V07C2DatasetError("empty-mask decisions must have no pair rows")

        return canonical_sha256(self._body())

    def _body(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "target_schema": self.target_schema,
            "state_schema": self.state_schema,
            "state_schema_sha256": self.state_schema_sha256,
            "coverage": [item.to_payload() for item in self.coverage],
            "rows": [row.to_payload() for row in self.rows],
        }

    @property
    def corpus_sha256(self) -> str:
        self.verify()
        return canonical_sha256(self._body())

    def to_document(self) -> dict[str, object]:
        """Return a canonical JSON-compatible document with its digest."""

        self.verify()
        body = self._body()
        return body | {"corpus_sha256": canonical_sha256(body)}

    @classmethod
    def from_document(cls, value: Mapping[str, object]) -> "V07C2Dataset":
        if not isinstance(value, Mapping):
            raise V07C2DatasetError("dataset document must be an object")
        expected = {
            "schema",
            "target_schema",
            "state_schema",
            "state_schema_sha256",
            "coverage",
            "rows",
            "corpus_sha256",
        }
        if set(value) != expected:
            raise V07C2DatasetError("dataset document schema is unexpected")
        body = {key: value[key] for key in expected if key != "corpus_sha256"}
        digest = value["corpus_sha256"]
        if not isinstance(digest, str) or digest != canonical_sha256(body):
            raise V07C2DatasetError("dataset corpus digest does not match payload")
        raw_coverage = value["coverage"]
        raw_rows = value["rows"]
        if not isinstance(raw_coverage, list) or not isinstance(raw_rows, list):
            raise V07C2DatasetError("dataset coverage and rows must be lists")
        dataset = cls(
            schema=value["schema"],
            target_schema=value["target_schema"],
            state_schema=value["state_schema"],
            state_schema_sha256=value["state_schema_sha256"],
            coverage=tuple(_decode_coverage(item) for item in raw_coverage),
            rows=tuple(_decode_row(item) for item in raw_rows),
        )
        if dataset.corpus_sha256 != digest:
            raise V07C2DatasetError("dataset digest changed on decode")
        return dataset


def build_v07_pair_batch(
    dataset: V07C2Dataset,
    *,
    lineage: str | None = None,
    refresh_round: int | str | None = None,
) -> EEAxisPairBatch:
    """Build the learner batch from non-empty decisions only.

    A filtered view is revalidated against its matching coverage before the
    arrays are assembled.  Thus a caller cannot use filtering to bypass the
    native-mask or duplicate/missing-row checks.
    """

    if not isinstance(dataset, V07C2Dataset):
        raise V07C2DatasetError("dataset must be V07C2Dataset")
    dataset.verify()
    if lineage is not None:
        _identity_text(lineage, field="lineage filter")
    if refresh_round is not None:
        refresh_round = _round_value(refresh_round)
    coverage = tuple(
        item
        for item in dataset.coverage
        if (lineage is None or item.lineage == lineage)
        and (refresh_round is None or item.refresh_round == refresh_round)
    )
    rows = tuple(
        row
        for row in dataset.rows
        if (lineage is None or row.lineage == lineage)
        and (refresh_round is None or row.refresh_round == refresh_round)
    )
    if not rows:
        raise V07C2DatasetError("selected batch has no non-empty decision rows")
    subset = V07C2Dataset.from_records(rows=rows, coverage=coverage)
    states = np.asarray([row.state for row in subset.rows], dtype=np.float32)
    references = np.asarray([row.reference_action for row in subset.rows], dtype=np.int64)
    candidates = np.asarray([row.candidate_action for row in subset.rows], dtype=np.int64)
    targets = np.asarray(
        [row.z2_focal_next_surplus_bits for row in subset.rows], dtype=np.float64
    )
    masks = np.asarray([row.action_mask for row in subset.rows], dtype=np.bool_)
    for value in (states, references, candidates, targets, masks):
        value.setflags(write=False)
    batch = EEAxisPairBatch(
        states=states,
        reference_actions=references,
        candidate_actions=candidates,
        target_surplus_bits=targets,
        action_masks=masks,
    )
    try:
        batch.validate(state_dim=V07_C2_Q2_STATE_DIM, action_dim=NUM_ACTIONS)
    except (MCRLContractError, TypeError, ValueError) as error:
        raise V07C2DatasetError("V0.7 pair batch failed pairwise validation") from error
    return batch


# Explicit aliases keep the module discoverable beside the older EE-axis
# dataset names while leaving one canonical implementation.
EEAxisV07C2Dataset = V07C2Dataset
EEAxisV07C2Row = V07C2Row
EEAxisV07C2DecisionCoverage = V07C2DecisionCoverage


__all__ = [
    "EEAxisV07C2Dataset",
    "EEAxisV07C2DecisionCoverage",
    "EEAxisV07C2Row",
    "V07C2Dataset",
    "V07C2DatasetError",
    "V07C2DecisionCoverage",
    "V07C2Row",
    "V07_C2_BATCH_SCHEMA",
    "V07_C2_COVERAGE_SCHEMA",
    "V07_C2_DATASET_SCHEMA",
    "V07_C2_ROW_SCHEMA",
    "canonical_json_bytes",
    "canonical_sha256",
    "build_v07_pair_batch",
]
