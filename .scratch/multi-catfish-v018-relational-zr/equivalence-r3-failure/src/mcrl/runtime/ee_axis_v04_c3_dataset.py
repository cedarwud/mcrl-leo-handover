"""Deterministic V0.4 C3 opening-comparison persistence.

The V0.4 C3 producer keeps the physical comparison in the existing
``EEAxisOpeningPair`` adapter.  This module is the persistence boundary around
that pair: it binds the pair to the V0.4 source/state schemas and their
digests, rejects mixed lineage, and rebuilds a C3 route batch on read.  It
does not modify the V0.3 opening source or dataset modules.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable

import numpy as np

from .ee_axis_opening_pairs import (
    EEAxisOpeningPair,
    EEAxisOpeningRouteBatch,
    OpeningPairContractError,
    build_opening_pair,
    build_opening_route_batch,
)
from .ee_axis_v04_c3_opening_source import (
    V04_C3_OPENING_SOURCE_SCHEMA,
    V04C3OpeningComparison,
    V04C3OpeningProvenance,
    V04C3OpeningSourceContractError,
)
from .ee_axis_v04_c3_state import (
    EE_AXIS_V04_C3_STATE_SCHEMA,
    EE_AXIS_V04_C3_STATE_SCHEMA_SHA256,
)


V04_C3_DATASET_SCHEMA = "multi-catfish-mcrl-v04-c3-opening-dataset-v2"

PhysicalKey = tuple[int, int]


class V04C3DatasetContractError(OpeningPairContractError):
    """A V0.4 C3 dataset row or snapshot is not admissible."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V04C3DatasetContractError(f"{field} must be lowercase SHA-256")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise V04C3DatasetContractError(
            f"{field} must be a nonempty trimmed string"
        )
    return value


def _strict_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise V04C3DatasetContractError(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _positive_float(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.number)
    ):
        raise V04C3DatasetContractError(
            f"{field} must be finite and positive"
        )
    converted = float(value)
    if not math.isfinite(converted) or converted <= 0.0:
        raise V04C3DatasetContractError(
            f"{field} must be finite and positive"
        )
    return converted


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _hex_float(value: object, *, field: str) -> float:
    if not isinstance(value, str):
        raise V04C3DatasetContractError(f"{field} must be a hexadecimal float")
    try:
        converted = float.fromhex(value)
    except ValueError as error:
        raise V04C3DatasetContractError(
            f"{field} must be a hexadecimal float"
        ) from error
    if not math.isfinite(converted):
        raise V04C3DatasetContractError(f"{field} must be finite")
    return converted


def _hex_float_list(value: object, *, field: str) -> np.ndarray:
    if not isinstance(value, list) or not value:
        raise V04C3DatasetContractError(
            f"{field} must be a nonempty hexadecimal-float list"
        )
    return np.asarray(
        [
            _hex_float(item, field=f"{field}[{index}]")
            for index, item in enumerate(value)
        ],
        dtype=np.float64,
    )


def _immutable_array(
    value: object,
    *,
    field: str,
    dtype: np.dtype[Any],
    ndim: int,
) -> np.ndarray:
    try:
        array = np.asarray(value)
        if array.ndim != ndim:
            raise V04C3DatasetContractError(
                f"{field} must be {ndim}-dimensional"
            )
        copied = np.array(array, dtype=dtype, copy=True, order="C")
    except V04C3DatasetContractError:
        raise
    except (TypeError, ValueError) as error:
        raise V04C3DatasetContractError(f"{field} has an invalid dtype") from error
    if np.issubdtype(copied.dtype, np.floating) and not np.all(
        np.isfinite(copied)
    ):
        raise V04C3DatasetContractError(f"{field} must be finite")
    copied.setflags(write=False)
    return copied


def _decode_int_vector(value: object, *, field: str) -> np.ndarray:
    if not isinstance(value, list) or not value:
        raise V04C3DatasetContractError(
            f"{field} must be a nonempty integer list"
        )
    if any(type(item) is not int for item in value):
        raise V04C3DatasetContractError(f"{field} must contain exact integers")
    return _immutable_array(
        value,
        field=field,
        dtype=np.dtype(np.int64),
        ndim=1,
    )


def _decode_mask(value: object, *, field: str) -> np.ndarray:
    if not isinstance(value, list) or not value:
        raise V04C3DatasetContractError(
            f"{field} must be a nonempty Boolean list"
        )
    if any(type(item) is not bool for item in value):
        raise V04C3DatasetContractError(f"{field} must contain exact Booleans")
    return _immutable_array(
        value,
        field=field,
        dtype=np.dtype(np.bool_),
        ndim=1,
    )


def _physical_key_payload(value: PhysicalKey | None) -> list[int] | None:
    return None if value is None else [int(value[0]), int(value[1])]


def _decode_physical_key(
    value: object, *, field: str, allow_none: bool
) -> PhysicalKey | None:
    if value is None and allow_none:
        return None
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(item) is not int for item in value)
    ):
        raise V04C3DatasetContractError(f"{field} must be a physical key")
    return int(value[0]), int(value[1])


def _pair_payload(pair: EEAxisOpeningPair) -> dict[str, object]:
    """Encode all pair inputs and derived targets, without lossy decimals."""

    return {
        "source_route": pair.source_route,
        "source_rule": pair.source_rule,
        "source_policy_version": pair.source_policy_version,
        "anchor_sha256": pair.anchor_sha256,
        "source_manifest_sha256": pair.source_manifest_sha256,
        "checkpoint_sha256": pair.checkpoint_sha256,
        "common_random_field_sha256": pair.common_random_field_sha256,
        "focal_user": pair.focal_user,
        "state": [float(value).hex() for value in pair.state.tolist()],
        "action_mask": [bool(value) for value in pair.action_mask.tolist()],
        "reference_action": pair.reference_action,
        "candidate_action": pair.candidate_action,
        "reference_joint_actions": [
            int(value) for value in pair.reference_joint_actions.tolist()
        ],
        "candidate_joint_actions": [
            int(value) for value in pair.candidate_joint_actions.tolist()
        ],
        "reference_rates_bps": [
            float(value).hex() for value in pair.reference_rates_bps.tolist()
        ],
        "candidate_rates_bps": [
            float(value).hex() for value in pair.candidate_rates_bps.tolist()
        ],
        "reference_system_power_w": pair.reference_system_power_w.hex(),
        "candidate_system_power_w": pair.candidate_system_power_w.hex(),
        "lambda_bits_per_j": pair.lambda_bits_per_j.hex(),
        "interval_s": pair.interval_s.hex(),
        "zeta1_focal_surplus_bits": pair.zeta1_focal_surplus_bits.hex(),
        "zeta3_nonfocal_externality_bits": pair.zeta3_nonfocal_externality_bits.hex(),
        "route_target_surplus_bits": pair.route_target_surplus_bits.hex(),
        "identity_residual_bits": pair.identity_residual_bits.hex(),
        "comparison_sha256": pair.comparison_sha256,
    }


def _decode_pair(payload: object) -> EEAxisOpeningPair:
    if not isinstance(payload, dict):
        raise V04C3DatasetContractError("row.pair must be an object")
    expected = {
        "source_route",
        "source_rule",
        "source_policy_version",
        "anchor_sha256",
        "source_manifest_sha256",
        "checkpoint_sha256",
        "common_random_field_sha256",
        "focal_user",
        "state",
        "action_mask",
        "reference_action",
        "candidate_action",
        "reference_joint_actions",
        "candidate_joint_actions",
        "reference_rates_bps",
        "candidate_rates_bps",
        "reference_system_power_w",
        "candidate_system_power_w",
        "lambda_bits_per_j",
        "interval_s",
        "zeta1_focal_surplus_bits",
        "zeta3_nonfocal_externality_bits",
        "route_target_surplus_bits",
        "identity_residual_bits",
        "comparison_sha256",
    }
    if set(payload) != expected:
        raise V04C3DatasetContractError("row.pair has an unexpected schema")
    if payload["source_route"] != "C3":
        raise V04C3DatasetContractError(
            "V0.4 C3 dataset rejects non-C3 or legacy pair provenance"
        )
    state_values = _hex_float_list(payload["state"], field="pair.state")
    state = _immutable_array(
        state_values.astype(np.float32),
        field="pair.state",
        dtype=np.dtype(np.float32),
        ndim=1,
    )
    mask = _decode_mask(payload["action_mask"], field="pair.action_mask")
    reference_joint = _decode_int_vector(
        payload["reference_joint_actions"],
        field="pair.reference_joint_actions",
    )
    candidate_joint = _decode_int_vector(
        payload["candidate_joint_actions"],
        field="pair.candidate_joint_actions",
    )
    reference_rates = _hex_float_list(
        payload["reference_rates_bps"],
        field="pair.reference_rates_bps",
    )
    candidate_rates = _hex_float_list(
        payload["candidate_rates_bps"],
        field="pair.candidate_rates_bps",
    )
    source_policy_version = _strict_int(
        payload["source_policy_version"],
        field="pair.source_policy_version",
        minimum=1,
    )
    try:
        pair = build_opening_pair(
            source_route="C3",
            source_rule=_text(payload["source_rule"], field="pair.source_rule"),
            source_policy_version=source_policy_version,
            anchor_sha256=_digest(
                payload["anchor_sha256"], field="pair.anchor_sha256"
            ),
            source_manifest_sha256=_digest(
                payload["source_manifest_sha256"],
                field="pair.source_manifest_sha256",
            ),
            checkpoint_sha256=_digest(
                payload["checkpoint_sha256"], field="pair.checkpoint_sha256"
            ),
            common_random_field_sha256=_digest(
                payload["common_random_field_sha256"],
                field="pair.common_random_field_sha256",
            ),
            focal_user=_strict_int(
                payload["focal_user"], field="pair.focal_user"
            ),
            state=state,
            action_mask=mask,
            reference_action=_strict_int(
                payload["reference_action"],
                field="pair.reference_action",
            ),
            candidate_action=_strict_int(
                payload["candidate_action"],
                field="pair.candidate_action",
            ),
            reference_joint_actions=reference_joint,
            candidate_joint_actions=candidate_joint,
            reference_rates_bps=reference_rates,
            candidate_rates_bps=candidate_rates,
            reference_system_power_w=_hex_float(
                payload["reference_system_power_w"],
                field="pair.reference_system_power_w",
            ),
            candidate_system_power_w=_hex_float(
                payload["candidate_system_power_w"],
                field="pair.candidate_system_power_w",
            ),
            lambda_bits_per_j=_hex_float(
                payload["lambda_bits_per_j"],
                field="pair.lambda_bits_per_j",
            ),
            interval_s=_hex_float(
                payload["interval_s"], field="pair.interval_s"
            ),
        )
    except OpeningPairContractError as error:
        raise V04C3DatasetContractError(
            f"persisted C3 pair cannot be rebuilt: {error}"
        ) from error
    expected_derived = {
        "zeta1_focal_surplus_bits": pair.zeta1_focal_surplus_bits.hex(),
        "zeta3_nonfocal_externality_bits": pair.zeta3_nonfocal_externality_bits.hex(),
        "route_target_surplus_bits": pair.route_target_surplus_bits.hex(),
        "identity_residual_bits": pair.identity_residual_bits.hex(),
    }
    for field, expected_value in expected_derived.items():
        if payload[field] != expected_value:
            raise V04C3DatasetContractError(
                f"persisted pair {field} disagrees with rebuilt C3 target"
            )
    supplied_digest = _digest(
        payload["comparison_sha256"], field="pair.comparison_sha256"
    )
    if pair.comparison_sha256 != supplied_digest:
        raise V04C3DatasetContractError(
            "persisted pair comparison digest disagrees with rebuilt pair"
        )
    return pair


def _provenance_payload(provenance: V04C3OpeningProvenance) -> dict[str, object]:
    return {
        "source_policy_version": provenance.source_policy_version,
        "anchor_sha256": provenance.anchor_sha256,
        "source_manifest_sha256": provenance.source_manifest_sha256,
        "checkpoint_sha256": provenance.checkpoint_sha256,
        "common_random_field_sha256": provenance.common_random_field_sha256,
        "c3_source_rule": provenance.c3_source_rule,
    }


def _producer_comparison_payload(
    row: "V04C3OpeningDatasetRow",
) -> dict[str, object]:
    """The producer digest surface retained without storing evaluations."""

    provenance = row.provenance
    return {
        "schema": V04_C3_OPENING_SOURCE_SCHEMA,
        "state_schema": row.state_schema,
        "state_schema_sha256": row.state_schema_sha256,
        "state_observation_sha256": row.state_observation_sha256,
        "kappa_bits": float(row.kappa_bits).hex(),
        "source_policy_version": provenance.source_policy_version,
        "anchor_sha256": provenance.anchor_sha256,
        "source_manifest_sha256": provenance.source_manifest_sha256,
        "checkpoint_sha256": provenance.checkpoint_sha256,
        "common_random_field_sha256": provenance.common_random_field_sha256,
        "c3_source_rule": provenance.c3_source_rule,
        "focal_user": row.pair.focal_user,
        "reference_physical_key": _physical_key_payload(
            row.reference_physical_key
        ),
        "candidate_physical_key": _physical_key_payload(
            row.candidate_physical_key
        ),
        "comparison_sha256": row.pair.comparison_sha256,
    }


def _decode_provenance(value: object) -> V04C3OpeningProvenance:
    if not isinstance(value, dict) or set(value) != {
        "source_policy_version",
        "anchor_sha256",
        "source_manifest_sha256",
        "checkpoint_sha256",
        "common_random_field_sha256",
        "c3_source_rule",
    }:
        raise V04C3DatasetContractError(
            "row.provenance has an unexpected schema"
        )
    provenance = V04C3OpeningProvenance(
        source_policy_version=_strict_int(
            value["source_policy_version"],
            field="provenance.source_policy_version",
            minimum=1,
        ),
        anchor_sha256=_digest(
            value["anchor_sha256"], field="provenance.anchor_sha256"
        ),
        source_manifest_sha256=_digest(
            value["source_manifest_sha256"],
            field="provenance.source_manifest_sha256",
        ),
        checkpoint_sha256=_digest(
            value["checkpoint_sha256"],
            field="provenance.checkpoint_sha256",
        ),
        common_random_field_sha256=_digest(
            value["common_random_field_sha256"],
            field="provenance.common_random_field_sha256",
        ),
        c3_source_rule=_text(
            value["c3_source_rule"], field="provenance.c3_source_rule"
        ),
    )
    try:
        provenance.verify()
    except V04C3OpeningSourceContractError as error:
        raise V04C3DatasetContractError(str(error)) from error
    return provenance


@dataclass(frozen=True)
class V04C3OpeningDatasetRow:
    """One immutable V0.4 C3 comparison with its producer lineage."""

    state_schema: str
    state_schema_sha256: str
    state_observation_sha256: str
    kappa_bits: float
    producer_comparison_sha256: str
    provenance: V04C3OpeningProvenance
    reference_physical_key: PhysicalKey | None
    candidate_physical_key: PhysicalKey
    pair: EEAxisOpeningPair

    @classmethod
    def from_comparison(
        cls, comparison: V04C3OpeningComparison
    ) -> "V04C3OpeningDatasetRow":
        if not isinstance(comparison, V04C3OpeningComparison):
            raise V04C3DatasetContractError(
                "dataset rows require V04C3OpeningComparison"
            )
        try:
            comparison.verify()
        except V04C3OpeningSourceContractError as error:
            raise V04C3DatasetContractError(str(error)) from error
        row = cls(
            state_schema=comparison.state_schema,
            state_schema_sha256=comparison.state_schema_sha256,
            state_observation_sha256=comparison.state_observation_sha256,
            kappa_bits=comparison.kappa_bits,
            producer_comparison_sha256=comparison.comparison_sha256,
            provenance=comparison.provenance,
            reference_physical_key=comparison.reference_physical_key,
            candidate_physical_key=comparison.candidate_physical_key,
            pair=comparison.pair,
        )
        row.verify()
        return row

    @property
    def comparison_sha256(self) -> str:
        """The existing pair digest used as the deduplication identity."""

        return self.pair.comparison_sha256

    def verify(self) -> str:
        if self.state_schema != EE_AXIS_V04_C3_STATE_SCHEMA:
            raise V04C3DatasetContractError(
                "V0.4 dataset rejects stale or V0.3 state provenance"
            )
        if self.state_schema_sha256 != EE_AXIS_V04_C3_STATE_SCHEMA_SHA256:
            raise V04C3DatasetContractError(
                "V0.4 dataset state schema digest drifted"
            )
        _digest(
            self.state_observation_sha256,
            field="state_observation_sha256",
        )
        _positive_float(self.kappa_bits, field="kappa_bits")
        _digest(
            self.producer_comparison_sha256,
            field="producer_comparison_sha256",
        )
        self.provenance.verify()
        reference_key = _decode_physical_key(
            _physical_key_payload(self.reference_physical_key),
            field="reference_physical_key",
            allow_none=True,
        )
        candidate_key = _decode_physical_key(
            _physical_key_payload(self.candidate_physical_key),
            field="candidate_physical_key",
            allow_none=False,
        )
        if reference_key == candidate_key:
            raise V04C3DatasetContractError(
                "candidate physical key matches its reference"
            )
        if not isinstance(self.pair, EEAxisOpeningPair):
            raise V04C3DatasetContractError("dataset row pair is malformed")
        if self.pair.source_route != "C3":
            raise V04C3DatasetContractError(
                "V0.4 dataset rejects non-C3 or legacy pair provenance"
            )
        self.pair.verify()
        if (
            self.pair.source_policy_version
            != self.provenance.source_policy_version
            or self.pair.anchor_sha256 != self.provenance.anchor_sha256
            or self.pair.source_manifest_sha256
            != self.provenance.source_manifest_sha256
            or self.pair.checkpoint_sha256 != self.provenance.checkpoint_sha256
            or self.pair.common_random_field_sha256
            != self.provenance.common_random_field_sha256
            or self.pair.source_rule != self.provenance.c3_source_rule
        ):
            raise V04C3DatasetContractError(
                "C3 pair and producer provenance disagree"
            )
        expected_producer_digest = _canonical_sha256(
            _producer_comparison_payload(self)
        )
        if self.producer_comparison_sha256 != expected_producer_digest:
            raise V04C3DatasetContractError(
                "producer comparison digest disagrees with persisted lineage"
            )
        return self.comparison_sha256


def _row_payload(row: V04C3OpeningDatasetRow) -> dict[str, object]:
    return {
        "state_schema": row.state_schema,
        "state_schema_sha256": row.state_schema_sha256,
        "state_observation_sha256": row.state_observation_sha256,
        "kappa_bits": float(row.kappa_bits).hex(),
        "producer_comparison_sha256": row.producer_comparison_sha256,
        "provenance": _provenance_payload(row.provenance),
        "reference_physical_key": _physical_key_payload(
            row.reference_physical_key
        ),
        "candidate_physical_key": _physical_key_payload(
            row.candidate_physical_key
        ),
        "pair": _pair_payload(row.pair),
    }


def _decode_row(value: object) -> V04C3OpeningDatasetRow:
    if not isinstance(value, dict) or set(value) != {
        "state_schema",
        "state_schema_sha256",
        "state_observation_sha256",
        "kappa_bits",
        "producer_comparison_sha256",
        "provenance",
        "reference_physical_key",
        "candidate_physical_key",
        "pair",
    }:
        raise V04C3DatasetContractError("dataset row has an unexpected schema")
    row = V04C3OpeningDatasetRow(
        state_schema=_text(value["state_schema"], field="row.state_schema"),
        state_schema_sha256=_digest(
            value["state_schema_sha256"],
            field="row.state_schema_sha256",
        ),
        state_observation_sha256=_digest(
            value["state_observation_sha256"],
            field="row.state_observation_sha256",
        ),
        kappa_bits=_hex_float(value["kappa_bits"], field="row.kappa_bits"),
        producer_comparison_sha256=_digest(
            value["producer_comparison_sha256"],
            field="row.producer_comparison_sha256",
        ),
        provenance=_decode_provenance(value["provenance"]),
        reference_physical_key=_decode_physical_key(
            value["reference_physical_key"],
            field="row.reference_physical_key",
            allow_none=True,
        ),
        candidate_physical_key=_decode_physical_key(
            value["candidate_physical_key"],
            field="row.candidate_physical_key",
            allow_none=False,
        ),
        pair=_decode_pair(value["pair"]),
    )
    try:
        row.verify()
    except OpeningPairContractError as error:
        raise V04C3DatasetContractError(str(error)) from error
    return row


@dataclass(frozen=True)
class V04C3OpeningDataset:
    """An immutable, sorted, single-lineage V0.4 C3 corpus."""

    source_policy_version: int
    source_manifest_sha256: str
    checkpoint_sha256: str
    common_random_field_sha256: str
    state_schema: str
    state_schema_sha256: str
    kappa_bits: float
    rows: tuple[V04C3OpeningDatasetRow, ...]
    schema: str = V04_C3_DATASET_SCHEMA
    source_schema: str = V04_C3_OPENING_SOURCE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != V04_C3_DATASET_SCHEMA:
            raise V04C3DatasetContractError(
                "V0.4 C3 dataset schema is stale or unsupported"
            )
        if self.source_schema != V04_C3_OPENING_SOURCE_SCHEMA:
            raise V04C3DatasetContractError(
                "V0.4 C3 dataset rejects V0.3 source provenance"
            )
        _strict_int(self.source_policy_version, field="source_policy_version", minimum=1)
        _digest(self.source_manifest_sha256, field="source_manifest_sha256")
        _digest(self.checkpoint_sha256, field="checkpoint_sha256")
        _digest(
            self.common_random_field_sha256,
            field="common_random_field_sha256",
        )
        if self.state_schema != EE_AXIS_V04_C3_STATE_SCHEMA:
            raise V04C3DatasetContractError(
                "V0.4 C3 dataset state schema is stale"
            )
        if self.state_schema_sha256 != EE_AXIS_V04_C3_STATE_SCHEMA_SHA256:
            raise V04C3DatasetContractError(
                "V0.4 C3 dataset state schema digest drifted"
            )
        _positive_float(self.kappa_bits, field="kappa_bits")
        if not isinstance(self.rows, tuple) or not self.rows:
            raise V04C3DatasetContractError(
                "V0.4 C3 dataset rows must be a nonempty immutable tuple"
            )
        seen: set[str] = set()
        for row in self.rows:
            if not isinstance(row, V04C3OpeningDatasetRow):
                raise V04C3DatasetContractError(
                    "V0.4 C3 dataset contains a non-row value"
                )
            row.verify()
            if row.provenance.source_policy_version != self.source_policy_version:
                raise V04C3DatasetContractError("mixed source policy versions")
            if (
                row.provenance.source_manifest_sha256
                != self.source_manifest_sha256
            ):
                raise V04C3DatasetContractError("mixed source manifest lineage")
            if row.provenance.checkpoint_sha256 != self.checkpoint_sha256:
                raise V04C3DatasetContractError("mixed checkpoint lineage")
            if (
                row.provenance.common_random_field_sha256
                != self.common_random_field_sha256
            ):
                raise V04C3DatasetContractError("mixed common random field lineage")
            if row.state_schema != self.state_schema:
                raise V04C3DatasetContractError("mixed state schema lineage")
            if row.state_schema_sha256 != self.state_schema_sha256:
                raise V04C3DatasetContractError("mixed state schema digest lineage")
            if row.kappa_bits != self.kappa_bits:
                raise V04C3DatasetContractError("mixed kappa lineage")
            if row.comparison_sha256 in seen:
                raise V04C3DatasetContractError(
                    "duplicate C3 comparison identity"
                )
            seen.add(row.comparison_sha256)
        actual_order = tuple(row.comparison_sha256 for row in self.rows)
        if actual_order != tuple(sorted(seen)):
            raise V04C3DatasetContractError(
                "V0.4 C3 dataset rows must be comparison-digest sorted"
            )

    @classmethod
    def from_comparisons(
        cls,
        comparisons: Iterable[V04C3OpeningComparison],
    ) -> "V04C3OpeningDataset":
        iterator = iter(comparisons)
        try:
            first = next(iterator)
        except StopIteration as error:
            raise V04C3DatasetContractError(
                "V0.4 C3 dataset cannot be empty"
            ) from error
        first_row = V04C3OpeningDatasetRow.from_comparison(first)
        provenance = first_row.provenance
        dataset = cls(
            source_policy_version=provenance.source_policy_version,
            source_manifest_sha256=provenance.source_manifest_sha256,
            checkpoint_sha256=provenance.checkpoint_sha256,
            common_random_field_sha256=provenance.common_random_field_sha256,
            state_schema=first_row.state_schema,
            state_schema_sha256=first_row.state_schema_sha256,
            kappa_bits=first_row.kappa_bits,
            rows=(first_row,),
        )
        for comparison in iterator:
            dataset = dataset.add(comparison)
        return dataset

    def add(
        self, comparison: V04C3OpeningComparison
    ) -> "V04C3OpeningDataset":
        """Return a sorted dataset, idempotent for an identical pair digest."""

        row = V04C3OpeningDatasetRow.from_comparison(comparison)
        if row.provenance.source_policy_version != self.source_policy_version:
            raise V04C3DatasetContractError("mixed source policy versions")
        if row.provenance.source_manifest_sha256 != self.source_manifest_sha256:
            raise V04C3DatasetContractError("mixed source manifest lineage")
        if row.provenance.checkpoint_sha256 != self.checkpoint_sha256:
            raise V04C3DatasetContractError("mixed checkpoint lineage")
        if (
            row.provenance.common_random_field_sha256
            != self.common_random_field_sha256
        ):
            raise V04C3DatasetContractError("mixed common random field lineage")
        if row.state_schema != self.state_schema:
            raise V04C3DatasetContractError("mixed state schema lineage")
        if row.state_schema_sha256 != self.state_schema_sha256:
            raise V04C3DatasetContractError("mixed state schema digest lineage")
        if row.kappa_bits != self.kappa_bits:
            raise V04C3DatasetContractError("mixed kappa lineage")
        existing = next(
            (
                candidate
                for candidate in self.rows
                if candidate.comparison_sha256 == row.comparison_sha256
            ),
            None,
        )
        if existing is not None:
            if _row_payload(existing) != _row_payload(row):
                raise V04C3DatasetContractError(
                    "duplicate C3 comparison has conflicting lineage/payload"
                )
            return self
        rows = tuple(
            sorted(
                (*self.rows, row),
                key=lambda item: item.comparison_sha256,
            )
        )
        return replace(self, rows=rows)

    @property
    def comparison_sha256s(self) -> tuple[str, ...]:
        return tuple(row.comparison_sha256 for row in self.rows)

    @property
    def c3_pairs(self) -> tuple[EEAxisOpeningPair, ...]:
        return tuple(row.pair for row in self.rows)

    def c3_batch(self) -> EEAxisOpeningRouteBatch:
        try:
            return build_opening_route_batch(self.c3_pairs)
        except OpeningPairContractError as error:
            raise V04C3DatasetContractError(str(error)) from error

    def verify(self) -> str:
        return _canonical_sha256(_dataset_body(self))


def _dataset_body(dataset: V04C3OpeningDataset) -> dict[str, object]:
    return {
        "schema": dataset.schema,
        "source_schema": dataset.source_schema,
        "source_policy_version": dataset.source_policy_version,
        "source_manifest_sha256": dataset.source_manifest_sha256,
        "checkpoint_sha256": dataset.checkpoint_sha256,
        "common_random_field_sha256": dataset.common_random_field_sha256,
        "state_schema": dataset.state_schema,
        "state_schema_sha256": dataset.state_schema_sha256,
        "kappa_bits": float(dataset.kappa_bits).hex(),
        "rows": [_row_payload(row) for row in dataset.rows],
    }


def _dataset_document(dataset: V04C3OpeningDataset) -> dict[str, object]:
    body = _dataset_body(dataset)
    return body | {"dataset_sha256": _canonical_sha256(body)}


def write_v04_c3_dataset(
    path: str | Path, dataset: V04C3OpeningDataset
) -> Path:
    """Atomically create deterministic JSON without replacing evidence."""

    if not isinstance(dataset, V04C3OpeningDataset):
        raise V04C3DatasetContractError(
            "dataset must be V04C3OpeningDataset"
        )
    dataset.verify()
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(
            _dataset_document(dataset),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, destination)
        except FileExistsError as error:
            raise V04C3DatasetContractError(
                "write-once V0.4 C3 dataset path already exists"
            ) from error
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    return destination


def read_v04_c3_dataset(path: str | Path) -> V04C3OpeningDataset:
    """Read and fully verify one V0.4 C3 deterministic JSON snapshot."""

    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V04C3DatasetContractError(
            "cannot read V0.4 C3 dataset JSON"
        ) from error
    if not isinstance(payload, dict):
        raise V04C3DatasetContractError(
            "V0.4 C3 dataset document must be an object"
        )
    expected = {
        "schema",
        "source_schema",
        "source_policy_version",
        "source_manifest_sha256",
        "checkpoint_sha256",
        "common_random_field_sha256",
        "state_schema",
        "state_schema_sha256",
        "kappa_bits",
        "rows",
        "dataset_sha256",
    }
    if set(payload) != expected:
        raise V04C3DatasetContractError(
            "V0.4 C3 dataset document has an unexpected schema"
        )
    supplied_digest = _digest(
        payload["dataset_sha256"], field="dataset_sha256"
    )
    body = {key: payload[key] for key in expected if key != "dataset_sha256"}
    if _canonical_sha256(body) != supplied_digest:
        raise V04C3DatasetContractError(
            "V0.4 C3 dataset digest disagrees with payload"
        )
    if payload["schema"] != V04_C3_DATASET_SCHEMA:
        raise V04C3DatasetContractError(
            "V0.4 C3 dataset schema is stale or unsupported"
        )
    if payload["source_schema"] != V04_C3_OPENING_SOURCE_SCHEMA:
        raise V04C3DatasetContractError(
            "V0.4 C3 dataset rejects V0.3 source provenance"
        )
    rows_payload = payload["rows"]
    if not isinstance(rows_payload, list) or not rows_payload:
        raise V04C3DatasetContractError(
            "V0.4 C3 dataset rows must be nonempty"
        )
    rows = tuple(_decode_row(row) for row in rows_payload)
    try:
        dataset = V04C3OpeningDataset(
            source_policy_version=_strict_int(
                payload["source_policy_version"],
                field="source_policy_version",
                minimum=1,
            ),
            source_manifest_sha256=_digest(
                payload["source_manifest_sha256"],
                field="source_manifest_sha256",
            ),
            checkpoint_sha256=_digest(
                payload["checkpoint_sha256"],
                field="checkpoint_sha256",
            ),
            common_random_field_sha256=_digest(
                payload["common_random_field_sha256"],
                field="common_random_field_sha256",
            ),
            state_schema=_text(payload["state_schema"], field="state_schema"),
            state_schema_sha256=_digest(
                payload["state_schema_sha256"],
                field="state_schema_sha256",
            ),
            kappa_bits=_hex_float(
                payload["kappa_bits"], field="kappa_bits"
            ),
            rows=rows,
            schema=payload["schema"],
            source_schema=payload["source_schema"],
        )
    except OpeningPairContractError as error:
        raise V04C3DatasetContractError(str(error)) from error
    return dataset


__all__ = [
    "V04_C3_DATASET_SCHEMA",
    "V04C3DatasetContractError",
    "V04C3OpeningDataset",
    "V04C3OpeningDatasetRow",
    "read_v04_c3_dataset",
    "write_v04_c3_dataset",
]
