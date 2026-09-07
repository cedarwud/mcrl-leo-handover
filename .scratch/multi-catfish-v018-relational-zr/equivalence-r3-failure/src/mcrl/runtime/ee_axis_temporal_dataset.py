"""Deterministic persistence boundary for the V0.3 C2 temporal corpus.

The live C2 runner produces :class:`EEAxisTemporalPair` objects.  This module
stores those complete raw rows without reducing them to targets, and rebuilds
the only learner view they may enter: a C2/Q2 temporal route batch.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable

import numpy as np

from ..errors import MCRLContractError
from .ee_axis_state import EE_AXIS_STATE_SCHEMA, EE_AXIS_STATE_SCHEMA_SHA256
from .ee_axis_temporal_pairs import (
    C2_POLICY_VERSION,
    EEAxisTemporalPair,
    EEAxisTemporalRouteBatch,
    TEMPORAL_HORIZON_STEPS,
    TemporalPairContractError,
    build_temporal_pair,
    build_temporal_route_batch,
)


TEMPORAL_DATASET_SCHEMA = "multi-catfish-mcrl-v03-temporal-dataset-v1"


class TemporalDatasetContractError(MCRLContractError):
    """A proposed or persisted D^t corpus violates current lineage."""


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TemporalDatasetContractError(f"{field} must be lowercase SHA-256")
    return value


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise TemporalDatasetContractError(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _float_hex(value: object) -> str:
    return float(value).hex()


def _decode_float(value: object, *, field: str) -> float:
    if not isinstance(value, str):
        raise TemporalDatasetContractError(f"{field} must be a hexadecimal float")
    try:
        result = float.fromhex(value)
    except ValueError as error:
        raise TemporalDatasetContractError(
            f"{field} must be a hexadecimal float"
        ) from error
    if not np.isfinite(result):
        raise TemporalDatasetContractError(f"{field} must be finite")
    return result


def _float_vector(value: object, *, field: str, dtype: np.dtype[Any]) -> np.ndarray:
    if not isinstance(value, list) or not value:
        raise TemporalDatasetContractError(f"{field} must be a nonempty list")
    return np.asarray(
        [_decode_float(item, field=f"{field}[{index}]") for index, item in enumerate(value)],
        dtype=dtype,
    )


def _float_matrix(value: object, *, field: str) -> np.ndarray:
    if not isinstance(value, list) or len(value) != TEMPORAL_HORIZON_STEPS:
        raise TemporalDatasetContractError(
            f"{field} must contain {TEMPORAL_HORIZON_STEPS} rows"
        )
    rows = [
        _float_vector(row, field=f"{field}[{index}]", dtype=np.dtype(np.float64))
        for index, row in enumerate(value)
    ]
    if len({row.shape for row in rows}) != 1:
        raise TemporalDatasetContractError(f"{field} changes width across offsets")
    return np.stack(rows)


def _bool_vector(value: object, *, field: str) -> np.ndarray:
    if not isinstance(value, list) or not value or any(type(item) is not bool for item in value):
        raise TemporalDatasetContractError(f"{field} must be a nonempty Boolean list")
    return np.asarray(value, dtype=np.bool_)


def _bool_matrix(value: object, *, field: str) -> np.ndarray:
    if not isinstance(value, list) or len(value) != TEMPORAL_HORIZON_STEPS:
        raise TemporalDatasetContractError(
            f"{field} must contain {TEMPORAL_HORIZON_STEPS} rows"
        )
    rows = [_bool_vector(row, field=f"{field}[{index}]") for index, row in enumerate(value)]
    if len({row.shape for row in rows}) != 1:
        raise TemporalDatasetContractError(f"{field} changes width across offsets")
    return np.stack(rows)


def _pair_payload(pair: EEAxisTemporalPair) -> dict[str, object]:
    pair.verify()
    return {
        "c2_policy_version": pair.c2_policy_version,
        "source_rule": pair.source_rule,
        "anchor_sha256": pair.anchor_sha256,
        "anchor_schedule_sha256": pair.anchor_schedule_sha256,
        "seed": pair.seed,
        "step_index": pair.step_index,
        "source_manifest_sha256": pair.source_manifest_sha256,
        "checkpoint_sha256": pair.checkpoint_sha256,
        "common_random_field_sha256": pair.common_random_field_sha256,
        "forecast_payload_sha256": pair.forecast_payload_sha256,
        "reference_trace_sha256": pair.reference_trace_sha256,
        "candidate_trace_sha256": pair.candidate_trace_sha256,
        "state_schema": pair.state_schema,
        "state_schema_sha256": pair.state_schema_sha256,
        "state_observation_sha256": pair.state_observation_sha256,
        "focal_user": pair.focal_user,
        "state": [_float_hex(value) for value in pair.state.tolist()],
        "action_mask": [bool(value) for value in pair.action_mask.tolist()],
        "reference_action": pair.reference_action,
        "candidate_action": pair.candidate_action,
        "held_physical_key": [int(value) for value in pair.held_physical_key],
        "held_key_match_counts": [int(value) for value in pair.held_key_match_counts],
        "release_offset": pair.release_offset,
        "release_reason": pair.release_reason,
        "reference_rates_bps": [
            [_float_hex(value) for value in row] for row in pair.reference_rates_bps
        ],
        "candidate_rates_bps": [
            [_float_hex(value) for value in row] for row in pair.candidate_rates_bps
        ],
        "reference_system_power_w": [
            _float_hex(value) for value in pair.reference_system_power_w
        ],
        "candidate_system_power_w": [
            _float_hex(value) for value in pair.candidate_system_power_w
        ],
        "reference_served": [
            [bool(value) for value in row] for row in pair.reference_served
        ],
        "candidate_served": [
            [bool(value) for value in row] for row in pair.candidate_served
        ],
        "lambda_bits_per_j": _float_hex(pair.lambda_bits_per_j),
        "interval_s": _float_hex(pair.interval_s),
        "offset_surplus_bits": [
            _float_hex(value) for value in pair.offset_surplus_bits
        ],
        "zeta2_temporal_surplus_bits": _float_hex(
            pair.zeta2_temporal_surplus_bits
        ),
        "provenance_sha256": pair.provenance_sha256,
        "comparison_sha256": pair.comparison_sha256,
    }


def _decode_pair(payload: object) -> EEAxisTemporalPair:
    if not isinstance(payload, dict):
        raise TemporalDatasetContractError("temporal dataset row must be an object")
    expected = {
        "c2_policy_version", "source_rule", "anchor_sha256",
        "anchor_schedule_sha256", "seed", "step_index",
        "source_manifest_sha256", "checkpoint_sha256",
        "common_random_field_sha256", "forecast_payload_sha256",
        "reference_trace_sha256", "candidate_trace_sha256", "state_schema",
        "state_schema_sha256", "state_observation_sha256", "focal_user",
        "state", "action_mask", "reference_action", "candidate_action",
        "held_physical_key", "held_key_match_counts", "release_offset",
        "release_reason", "reference_rates_bps", "candidate_rates_bps",
        "reference_system_power_w", "candidate_system_power_w",
        "reference_served", "candidate_served", "lambda_bits_per_j",
        "interval_s", "offset_surplus_bits", "zeta2_temporal_surplus_bits",
        "provenance_sha256", "comparison_sha256",
    }
    if set(payload) != expected:
        raise TemporalDatasetContractError("temporal dataset row schema is unexpected")
    physical = payload["held_physical_key"]
    if (
        not isinstance(physical, list)
        or len(physical) != 2
        or any(type(value) is not int for value in physical)
    ):
        raise TemporalDatasetContractError("held_physical_key must be two integers")
    counts = payload["held_key_match_counts"]
    if not isinstance(counts, list) or any(type(value) is not int for value in counts):
        raise TemporalDatasetContractError("held_key_match_counts must be integers")
    try:
        pair = build_temporal_pair(
            c2_policy_version=str(payload["c2_policy_version"]),
            source_rule=str(payload["source_rule"]),
            anchor_sha256=_digest(payload["anchor_sha256"], field="anchor_sha256"),
            anchor_schedule_sha256=_digest(payload["anchor_schedule_sha256"], field="anchor_schedule_sha256"),
            seed=_exact_int(payload["seed"], field="seed"),
            step_index=_exact_int(payload["step_index"], field="step_index"),
            source_manifest_sha256=_digest(payload["source_manifest_sha256"], field="source_manifest_sha256"),
            checkpoint_sha256=_digest(payload["checkpoint_sha256"], field="checkpoint_sha256"),
            common_random_field_sha256=_digest(payload["common_random_field_sha256"], field="common_random_field_sha256"),
            forecast_payload_sha256=_digest(payload["forecast_payload_sha256"], field="forecast_payload_sha256"),
            reference_trace_sha256=_digest(payload["reference_trace_sha256"], field="reference_trace_sha256"),
            candidate_trace_sha256=_digest(payload["candidate_trace_sha256"], field="candidate_trace_sha256"),
            state_schema=str(payload["state_schema"]),
            state_schema_sha256=_digest(payload["state_schema_sha256"], field="state_schema_sha256"),
            state_observation_sha256=_digest(payload["state_observation_sha256"], field="state_observation_sha256"),
            focal_user=_exact_int(payload["focal_user"], field="focal_user"),
            state=_float_vector(payload["state"], field="state", dtype=np.dtype(np.float32)),
            action_mask=_bool_vector(payload["action_mask"], field="action_mask"),
            reference_action=_exact_int(payload["reference_action"], field="reference_action"),
            candidate_action=_exact_int(payload["candidate_action"], field="candidate_action"),
            held_physical_key=(int(physical[0]), int(physical[1])),
            held_key_match_counts=tuple(int(value) for value in counts),
            release_offset=_exact_int(payload["release_offset"], field="release_offset"),
            release_reason=str(payload["release_reason"]),
            reference_rates_bps=_float_matrix(payload["reference_rates_bps"], field="reference_rates_bps"),
            candidate_rates_bps=_float_matrix(payload["candidate_rates_bps"], field="candidate_rates_bps"),
            reference_system_power_w=_float_vector(payload["reference_system_power_w"], field="reference_system_power_w", dtype=np.dtype(np.float64)),
            candidate_system_power_w=_float_vector(payload["candidate_system_power_w"], field="candidate_system_power_w", dtype=np.dtype(np.float64)),
            reference_served=_bool_matrix(payload["reference_served"], field="reference_served"),
            candidate_served=_bool_matrix(payload["candidate_served"], field="candidate_served"),
            lambda_bits_per_j=_decode_float(payload["lambda_bits_per_j"], field="lambda_bits_per_j"),
            interval_s=_decode_float(payload["interval_s"], field="interval_s"),
            offset_surplus_bits=_float_vector(payload["offset_surplus_bits"], field="offset_surplus_bits", dtype=np.dtype(np.float64)),
            zeta2_temporal_surplus_bits=_decode_float(payload["zeta2_temporal_surplus_bits"], field="zeta2_temporal_surplus_bits"),
        )
    except (TemporalPairContractError, TypeError, ValueError) as error:
        raise TemporalDatasetContractError(str(error)) from error
    if pair.provenance_sha256 != _digest(payload["provenance_sha256"], field="provenance_sha256"):
        raise TemporalDatasetContractError("temporal provenance digest changed on decode")
    if pair.comparison_sha256 != _digest(payload["comparison_sha256"], field="comparison_sha256"):
        raise TemporalDatasetContractError("temporal comparison digest changed on decode")
    return pair


@dataclass(frozen=True)
class EEAxisTemporalDataset:
    """One immutable, lineage-consistent C2 source dataset."""

    source_manifest_sha256: str
    checkpoint_sha256: str
    lambda_bits_per_j: float
    interval_s: float
    rows: tuple[EEAxisTemporalPair, ...]
    schema: str = TEMPORAL_DATASET_SCHEMA
    c2_policy_version: str = C2_POLICY_VERSION
    state_schema: str = EE_AXIS_STATE_SCHEMA
    state_schema_sha256: str = EE_AXIS_STATE_SCHEMA_SHA256

    def __post_init__(self) -> None:
        if self.schema != TEMPORAL_DATASET_SCHEMA:
            raise TemporalDatasetContractError("temporal dataset schema is stale")
        if self.c2_policy_version != C2_POLICY_VERSION:
            raise TemporalDatasetContractError("temporal policy version is stale")
        if self.state_schema != EE_AXIS_STATE_SCHEMA or self.state_schema_sha256 != EE_AXIS_STATE_SCHEMA_SHA256:
            raise TemporalDatasetContractError("temporal state schema is stale")
        _digest(self.source_manifest_sha256, field="source_manifest_sha256")
        _digest(self.checkpoint_sha256, field="checkpoint_sha256")
        if not np.isfinite(self.lambda_bits_per_j) or self.lambda_bits_per_j <= 0.0:
            raise TemporalDatasetContractError("lambda_bits_per_j must be positive")
        if not np.isfinite(self.interval_s) or self.interval_s <= 0.0:
            raise TemporalDatasetContractError("interval_s must be positive")
        if not isinstance(self.rows, tuple) or not self.rows:
            raise TemporalDatasetContractError("temporal dataset rows must be a nonempty tuple")
        digests = []
        for row in self.rows:
            if not isinstance(row, EEAxisTemporalPair):
                raise TemporalDatasetContractError("temporal dataset contains a non-pair")
            digests.append(row.verify())
            if row.c2_policy_version != self.c2_policy_version:
                raise TemporalDatasetContractError("temporal dataset mixes policy versions")
            if row.source_manifest_sha256 != self.source_manifest_sha256:
                raise TemporalDatasetContractError("temporal dataset mixes source manifests")
            if row.checkpoint_sha256 != self.checkpoint_sha256:
                raise TemporalDatasetContractError("temporal dataset mixes checkpoints")
            if row.state_schema != self.state_schema or row.state_schema_sha256 != self.state_schema_sha256:
                raise TemporalDatasetContractError("temporal dataset mixes state schemas")
            if row.lambda_bits_per_j != self.lambda_bits_per_j or row.interval_s != self.interval_s:
                raise TemporalDatasetContractError("temporal dataset mixes formula constants")
        if len(set(digests)) != len(digests):
            raise TemporalDatasetContractError("temporal dataset contains duplicate rows")
        if tuple(digests) != tuple(sorted(digests)):
            raise TemporalDatasetContractError("temporal dataset rows must be digest sorted")

    @classmethod
    def from_pairs(cls, rows: Iterable[EEAxisTemporalPair]) -> "EEAxisTemporalDataset":
        materialized = tuple(rows)
        if not materialized:
            raise TemporalDatasetContractError("D^t dataset cannot be empty")
        ordered = tuple(sorted(materialized, key=lambda row: row.verify()))
        first = ordered[0]
        return cls(
            source_manifest_sha256=first.source_manifest_sha256,
            checkpoint_sha256=first.checkpoint_sha256,
            lambda_bits_per_j=first.lambda_bits_per_j,
            interval_s=first.interval_s,
            rows=ordered,
        )

    def route_batch(self) -> EEAxisTemporalRouteBatch:
        try:
            return build_temporal_route_batch(self.rows)
        except TemporalPairContractError as error:
            raise TemporalDatasetContractError(str(error)) from error

    def verify(self) -> str:
        return _canonical_sha256(_dataset_body(self))


def _dataset_body(dataset: EEAxisTemporalDataset) -> dict[str, object]:
    return {
        "schema": dataset.schema,
        "c2_policy_version": dataset.c2_policy_version,
        "state_schema": dataset.state_schema,
        "state_schema_sha256": dataset.state_schema_sha256,
        "source_manifest_sha256": dataset.source_manifest_sha256,
        "checkpoint_sha256": dataset.checkpoint_sha256,
        "lambda_bits_per_j": _float_hex(dataset.lambda_bits_per_j),
        "interval_s": _float_hex(dataset.interval_s),
        "rows": [_pair_payload(row) for row in dataset.rows],
    }


def write_temporal_dataset(path: str | Path, dataset: EEAxisTemporalDataset) -> Path:
    if not isinstance(dataset, EEAxisTemporalDataset):
        raise TemporalDatasetContractError("dataset must be EEAxisTemporalDataset")
    body = _dataset_body(dataset)
    document = body | {"dataset_sha256": _canonical_sha256(body)}
    encoded = (json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, destination)
        except FileExistsError as error:
            raise TemporalDatasetContractError("write-once temporal dataset already exists") from error
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    return destination


def read_temporal_dataset(path: str | Path) -> EEAxisTemporalDataset:
    try:
        payload = json.loads(Path(path).read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise TemporalDatasetContractError("cannot read temporal dataset JSON") from error
    if not isinstance(payload, dict):
        raise TemporalDatasetContractError("temporal dataset document must be an object")
    expected = {
        "schema", "c2_policy_version", "state_schema", "state_schema_sha256",
        "source_manifest_sha256", "checkpoint_sha256", "lambda_bits_per_j",
        "interval_s", "rows", "dataset_sha256",
    }
    if set(payload) != expected:
        raise TemporalDatasetContractError("temporal dataset document schema is unexpected")
    supplied = _digest(payload["dataset_sha256"], field="dataset_sha256")
    body = {key: payload[key] for key in expected if key != "dataset_sha256"}
    if _canonical_sha256(body) != supplied:
        raise TemporalDatasetContractError("temporal dataset digest disagrees with payload")
    rows_payload = payload["rows"]
    if not isinstance(rows_payload, list) or not rows_payload:
        raise TemporalDatasetContractError("temporal dataset rows must be nonempty")
    rows = tuple(_decode_pair(row) for row in rows_payload)
    try:
        return EEAxisTemporalDataset(
            schema=str(payload["schema"]),
            c2_policy_version=str(payload["c2_policy_version"]),
            state_schema=str(payload["state_schema"]),
            state_schema_sha256=_digest(payload["state_schema_sha256"], field="state_schema_sha256"),
            source_manifest_sha256=_digest(payload["source_manifest_sha256"], field="source_manifest_sha256"),
            checkpoint_sha256=_digest(payload["checkpoint_sha256"], field="checkpoint_sha256"),
            lambda_bits_per_j=_decode_float(payload["lambda_bits_per_j"], field="lambda_bits_per_j"),
            interval_s=_decode_float(payload["interval_s"], field="interval_s"),
            rows=rows,
        )
    except (TemporalPairContractError, TypeError, ValueError) as error:
        raise TemporalDatasetContractError(str(error)) from error


__all__ = [
    "EEAxisTemporalDataset",
    "TEMPORAL_DATASET_SCHEMA",
    "TemporalDatasetContractError",
    "read_temporal_dataset",
    "write_temporal_dataset",
]
