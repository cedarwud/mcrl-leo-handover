"""Deterministic persistence for the V0.3 opening-comparison corpus.

The physical producer returns one route-independent raw comparison together
with two projections of that comparison (C1/Q1 and C3/Q3).  This module is a
small persistence boundary for those results.  A row stores the raw payload
once and keeps only route provenance and the two native-bit target values
beside it.  Route pairs are rebuilt through the existing opening-pair adapter
when a batch view is requested.

This module intentionally contains no source selector, trainer integration, or
state-schema policy.  It only validates lineage, deduplicates complete raw
comparisons, and writes/reads a deterministic JSON snapshot.
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
    build_opening_route_batch,
)
from .ee_axis_opening_source import (
    EEAxisOpeningRawPair,
    EEAxisOpeningSourceResult,
    OPENING_SOURCE_SCHEMA,
    OpeningSourceContractError,
)
from .ee_axis_state import EE_AXIS_STATE_SCHEMA, EE_AXIS_STATE_SCHEMA_SHA256


OPENING_DATASET_SCHEMA = "multi-catfish-mcrl-v03-opening-dataset-v3"
"""Schema of a persisted route-independent D^o snapshot."""


class OpeningDatasetContractError(OpeningPairContractError):
    """A persisted or proposed D^o dataset violates its lineage contract."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise OpeningDatasetContractError(f"{field} must be lowercase SHA-256")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise OpeningDatasetContractError(f"{field} must be a nonempty trimmed string")
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


def _hex_float(value: object, *, field: str) -> float:
    if not isinstance(value, str):
        raise OpeningDatasetContractError(f"{field} must be a hexadecimal float")
    try:
        result = float.fromhex(value)
    except ValueError as error:
        raise OpeningDatasetContractError(
            f"{field} must be a hexadecimal float"
        ) from error
    if not math.isfinite(result):
        raise OpeningDatasetContractError(f"{field} must be finite")
    return result


def _hex_float_list(value: object, *, field: str) -> np.ndarray:
    if not isinstance(value, list) or not value:
        raise OpeningDatasetContractError(f"{field} must be a nonempty float list")
    decoded = [_hex_float(item, field=f"{field}[{index}]") for index, item in enumerate(value)]
    return np.asarray(decoded, dtype=np.float64)


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
            raise OpeningDatasetContractError(
                f"{field} must be {ndim}-dimensional"
            )
        copied = np.array(array, dtype=dtype, copy=True, order="C")
    except OpeningDatasetContractError:
        raise
    except (TypeError, ValueError) as error:
        raise OpeningDatasetContractError(f"{field} has an invalid dtype") from error
    if np.issubdtype(copied.dtype, np.floating) and not np.all(np.isfinite(copied)):
        raise OpeningDatasetContractError(f"{field} must be finite")
    copied.setflags(write=False)
    return copied


def _strict_int(value: object, *, field: str, minimum: int | None = None) -> int:
    if type(value) is not int or (minimum is not None and value < minimum):
        suffix = f" >= {minimum}" if minimum is not None else ""
        raise OpeningDatasetContractError(f"{field} must be an exact integer{suffix}")
    return value


def _decode_int_vector(value: object, *, field: str) -> np.ndarray:
    if not isinstance(value, list) or not value:
        raise OpeningDatasetContractError(f"{field} must be a nonempty integer list")
    if any(type(item) is not int for item in value):
        raise OpeningDatasetContractError(f"{field} must contain exact integers")
    return _immutable_array(value, field=field, dtype=np.dtype(np.int64), ndim=1)


def _decode_mask(value: object, *, field: str) -> np.ndarray:
    if not isinstance(value, list) or not value:
        raise OpeningDatasetContractError(f"{field} must be a nonempty Boolean list")
    if any(type(item) is not bool for item in value):
        raise OpeningDatasetContractError(f"{field} must contain exact Booleans")
    return _immutable_array(value, field=field, dtype=np.dtype(np.bool_), ndim=1)


def _decode_physical_keys(value: object, *, field: str) -> tuple[tuple[int, int] | None, ...]:
    if not isinstance(value, list) or not value:
        raise OpeningDatasetContractError(
            f"{field} must be a nonempty physical-key list"
        )
    decoded: list[tuple[int, int] | None] = []
    for index, item in enumerate(value):
        if item is None:
            decoded.append(None)
            continue
        if (
            not isinstance(item, list)
            or len(item) != 2
            or any(type(component) is not int for component in item)
        ):
            raise OpeningDatasetContractError(
                f"{field}[{index}] must be null or [norad, cell]"
            )
        decoded.append((int(item[0]), int(item[1])))
    return tuple(decoded)


def _raw_payload(raw: EEAxisOpeningRawPair) -> dict[str, object]:
    return {
        "schema": OPENING_SOURCE_SCHEMA,
        "source_policy_version": raw.source_policy_version,
        "anchor_sha256": raw.anchor_sha256,
        "source_manifest_sha256": raw.source_manifest_sha256,
        "checkpoint_sha256": raw.checkpoint_sha256,
        "common_random_field_sha256": raw.common_random_field_sha256,
        "state_schema": raw.state_schema,
        "state_schema_sha256": raw.state_schema_sha256,
        "state_observation_sha256": raw.state_observation_sha256,
        "focal_user": raw.focal_user,
        "state": [float(value).hex() for value in raw.state.tolist()],
        "action_mask": [bool(value) for value in raw.action_mask.tolist()],
        "reference_action": raw.reference_action,
        "candidate_action": raw.candidate_action,
        "reference_joint_actions": [
            int(value) for value in raw.reference_joint_actions.tolist()
        ],
        "candidate_joint_actions": [
            int(value) for value in raw.candidate_joint_actions.tolist()
        ],
        "reference_physical_keys": [
            None if key is None else [int(key[0]), int(key[1])]
            for key in raw.reference_physical_keys
        ],
        "candidate_physical_keys": [
            None if key is None else [int(key[0]), int(key[1])]
            for key in raw.candidate_physical_keys
        ],
        "reference_rates_bps": [
            float(value).hex() for value in raw.reference_rates_bps.tolist()
        ],
        "candidate_rates_bps": [
            float(value).hex() for value in raw.candidate_rates_bps.tolist()
        ],
        "reference_system_power_w": float(raw.reference_system_power_w).hex(),
        "candidate_system_power_w": float(raw.candidate_system_power_w).hex(),
        "lambda_bits_per_j": float(raw.lambda_bits_per_j).hex(),
        "interval_s": float(raw.interval_s).hex(),
        "comparison_sha256": raw.comparison_sha256,
    }


def _decode_raw(payload: object) -> EEAxisOpeningRawPair:
    if not isinstance(payload, dict):
        raise OpeningDatasetContractError("row.raw must be an object")
    expected = {
        "schema",
        "source_policy_version",
        "anchor_sha256",
        "source_manifest_sha256",
        "checkpoint_sha256",
        "common_random_field_sha256",
        "state_schema",
        "state_schema_sha256",
        "state_observation_sha256",
        "focal_user",
        "state",
        "action_mask",
        "reference_action",
        "candidate_action",
        "reference_joint_actions",
        "candidate_joint_actions",
        "reference_physical_keys",
        "candidate_physical_keys",
        "reference_rates_bps",
        "candidate_rates_bps",
        "reference_system_power_w",
        "candidate_system_power_w",
        "lambda_bits_per_j",
        "interval_s",
        "comparison_sha256",
    }
    if set(payload) != expected:
        raise OpeningDatasetContractError("row.raw has an unexpected schema")
    if payload["schema"] != OPENING_SOURCE_SCHEMA:
        raise OpeningDatasetContractError("row.raw source schema is stale")
    source_policy_version = _strict_int(
        payload["source_policy_version"], field="source_policy_version", minimum=1
    )
    anchor = _digest(payload["anchor_sha256"], field="anchor_sha256")
    manifest = _digest(
        payload["source_manifest_sha256"], field="source_manifest_sha256"
    )
    checkpoint = _digest(payload["checkpoint_sha256"], field="checkpoint_sha256")
    field = _digest(
        payload["common_random_field_sha256"],
        field="common_random_field_sha256",
    )
    state_schema = _text(payload["state_schema"], field="state_schema")
    state_schema_sha256 = _digest(
        payload["state_schema_sha256"], field="state_schema_sha256"
    )
    state_observation_sha256 = _digest(
        payload["state_observation_sha256"], field="state_observation_sha256"
    )
    state_values = _hex_float_list(payload["state"], field="state")
    state = _immutable_array(
        state_values.astype(np.float32),
        field="state",
        dtype=np.dtype(np.float32),
        ndim=1,
    )
    action_mask = _decode_mask(payload["action_mask"], field="action_mask")
    reference_joint = _decode_int_vector(
        payload["reference_joint_actions"], field="reference_joint_actions"
    )
    candidate_joint = _decode_int_vector(
        payload["candidate_joint_actions"], field="candidate_joint_actions"
    )
    reference_rates = _hex_float_list(
        payload["reference_rates_bps"], field="reference_rates_bps"
    )
    candidate_rates = _hex_float_list(
        payload["candidate_rates_bps"], field="candidate_rates_bps"
    )
    reference_action = _strict_int(payload["reference_action"], field="reference_action")
    candidate_action = _strict_int(payload["candidate_action"], field="candidate_action")
    focal_user = _strict_int(payload["focal_user"], field="focal_user", minimum=0)
    reference_physical_keys = _decode_physical_keys(
        payload["reference_physical_keys"], field="reference_physical_keys"
    )
    candidate_physical_keys = _decode_physical_keys(
        payload["candidate_physical_keys"], field="candidate_physical_keys"
    )
    raw = EEAxisOpeningRawPair(
        source_policy_version=source_policy_version,
        anchor_sha256=anchor,
        source_manifest_sha256=manifest,
        checkpoint_sha256=checkpoint,
        common_random_field_sha256=field,
        state_schema=state_schema,
        state_schema_sha256=state_schema_sha256,
        state_observation_sha256=state_observation_sha256,
        focal_user=focal_user,
        state=state,
        action_mask=action_mask,
        reference_action=reference_action,
        candidate_action=candidate_action,
        reference_joint_actions=reference_joint,
        candidate_joint_actions=candidate_joint,
        reference_physical_keys=reference_physical_keys,
        candidate_physical_keys=candidate_physical_keys,
        reference_rates_bps=reference_rates,
        candidate_rates_bps=candidate_rates,
        reference_system_power_w=_hex_float(
            payload["reference_system_power_w"], field="reference_system_power_w"
        ),
        candidate_system_power_w=_hex_float(
            payload["candidate_system_power_w"], field="candidate_system_power_w"
        ),
        lambda_bits_per_j=_hex_float(
            payload["lambda_bits_per_j"], field="lambda_bits_per_j"
        ),
        interval_s=_hex_float(payload["interval_s"], field="interval_s"),
        comparison_sha256=_digest(
            payload["comparison_sha256"], field="comparison_sha256"
        ),
    )
    try:
        raw.verify()
    except OpeningSourceContractError as error:
        raise OpeningDatasetContractError(str(error)) from error
    if not (
        reference_joint.shape
        == candidate_joint.shape
        == reference_rates.shape
        == candidate_rates.shape
        == (len(reference_physical_keys),)
        == (len(candidate_physical_keys),)
    ):
        raise OpeningDatasetContractError("raw vectors disagree about user dimension")
    if focal_user >= reference_joint.size:
        raise OpeningDatasetContractError("focal_user lies outside raw user dimension")
    return raw


@dataclass(frozen=True)
class EEAxisOpeningDatasetRow:
    """One raw comparison plus compact C1/C3 route provenance."""

    raw_pair: EEAxisOpeningRawPair
    admitted_route: str
    c1_source_rule: str
    c3_source_rule: str
    c1_comparison_sha256: str
    c3_comparison_sha256: str
    zeta1_focal_surplus_bits: float
    zeta3_nonfocal_externality_bits: float
    identity_residual_bits: float

    @classmethod
    def from_result(cls, result: EEAxisOpeningSourceResult) -> "EEAxisOpeningDatasetRow":
        if not isinstance(result, EEAxisOpeningSourceResult):
            raise OpeningDatasetContractError(
                "dataset rows require EEAxisOpeningSourceResult"
            )
        try:
            result.verify()
        except OpeningSourceContractError as error:
            raise OpeningDatasetContractError(str(error)) from error
        c1 = result.c1.pair
        c3 = result.c3.pair
        if c1.identity_residual_bits != c3.identity_residual_bits:
            raise OpeningDatasetContractError(
                "C1 and C3 disagree about identity residual"
            )
        row = cls(
            raw_pair=result.raw_pair,
            admitted_route=result.admitted_route,
            c1_source_rule=c1.source_rule,
            c3_source_rule=c3.source_rule,
            c1_comparison_sha256=c1.comparison_sha256,
            c3_comparison_sha256=c3.comparison_sha256,
            zeta1_focal_surplus_bits=c1.zeta1_focal_surplus_bits,
            zeta3_nonfocal_externality_bits=c3.zeta3_nonfocal_externality_bits,
            identity_residual_bits=c1.identity_residual_bits,
        )
        row.verify()
        return row

    def _route_pair(self, route: str) -> EEAxisOpeningPair:
        if route == "C1":
            source_rule = self.c1_source_rule
            expected_digest = self.c1_comparison_sha256
        elif route == "C3":
            source_rule = self.c3_source_rule
            expected_digest = self.c3_comparison_sha256
        else:
            raise OpeningDatasetContractError("route must be C1 or C3")
        raw = self.raw_pair
        # Importing the builder locally keeps the public module dependency
        # explicit while avoiding a second serialized copy of the raw fields.
        from .ee_axis_opening_pairs import build_opening_pair

        pair = build_opening_pair(
            source_route=route,
            source_rule=source_rule,
            source_policy_version=raw.source_policy_version,
            anchor_sha256=raw.anchor_sha256,
            source_manifest_sha256=raw.source_manifest_sha256,
            checkpoint_sha256=raw.checkpoint_sha256,
            common_random_field_sha256=raw.common_random_field_sha256,
            focal_user=raw.focal_user,
            state=raw.state,
            action_mask=raw.action_mask,
            reference_action=raw.reference_action,
            candidate_action=raw.candidate_action,
            reference_joint_actions=raw.reference_joint_actions,
            candidate_joint_actions=raw.candidate_joint_actions,
            reference_rates_bps=raw.reference_rates_bps,
            candidate_rates_bps=raw.candidate_rates_bps,
            reference_system_power_w=raw.reference_system_power_w,
            candidate_system_power_w=raw.candidate_system_power_w,
            lambda_bits_per_j=raw.lambda_bits_per_j,
            interval_s=raw.interval_s,
        )
        if pair.comparison_sha256 != expected_digest:
            raise OpeningDatasetContractError(
                f"{route} route digest disagrees with persisted row"
            )
        return pair

    @property
    def c1_pair(self) -> EEAxisOpeningPair:
        return self._route_pair("C1")

    @property
    def c3_pair(self) -> EEAxisOpeningPair:
        return self._route_pair("C3")

    def verify(self) -> str:
        """Verify raw lineage and both compact route projections."""

        raw_digest = self.raw_pair.verify()
        if self.admitted_route not in ("C1", "C3"):
            raise OpeningDatasetContractError("row admitted_route must be C1 or C3")
        _text(self.c1_source_rule, field="c1_source_rule")
        _text(self.c3_source_rule, field="c3_source_rule")
        c1_digest = _digest(self.c1_comparison_sha256, field="c1_comparison_sha256")
        c3_digest = _digest(self.c3_comparison_sha256, field="c3_comparison_sha256")
        for field, value in (
            ("zeta1_focal_surplus_bits", self.zeta1_focal_surplus_bits),
            ("zeta3_nonfocal_externality_bits", self.zeta3_nonfocal_externality_bits),
            ("identity_residual_bits", self.identity_residual_bits),
        ):
            if not isinstance(value, (int, float, np.number)) or not math.isfinite(float(value)):
                raise OpeningDatasetContractError(f"{field} must be finite")
        c1 = self.c1_pair
        c3 = self.c3_pair
        if c1_digest != c1.comparison_sha256 or c3_digest != c3.comparison_sha256:
            raise OpeningDatasetContractError("route digest disagrees with rebuilt pair")
        if (
            c1.zeta1_focal_surplus_bits != float(self.zeta1_focal_surplus_bits)
            or c3.zeta3_nonfocal_externality_bits
            != float(self.zeta3_nonfocal_externality_bits)
            or c1.identity_residual_bits != float(self.identity_residual_bits)
            or c3.identity_residual_bits != float(self.identity_residual_bits)
        ):
            raise OpeningDatasetContractError("persisted route target disagrees with raw lineage")
        # The route-pair adapter does not carry the raw digest.  The pair's
        # common physical fields are rebuilt from exactly this raw digest;
        # comparing all fields is therefore the lineage check here.
        if c1.source_route != "C1" or c3.source_route != "C3":
            raise OpeningDatasetContractError("route provenance is malformed")
        return raw_digest


def _row_payload(row: EEAxisOpeningDatasetRow) -> dict[str, object]:
    return {
        "raw": _raw_payload(row.raw_pair),
        "admitted_route": row.admitted_route,
        "routes": {
            "C1": {
                "source_rule": row.c1_source_rule,
                "comparison_sha256": row.c1_comparison_sha256,
            },
            "C3": {
                "source_rule": row.c3_source_rule,
                "comparison_sha256": row.c3_comparison_sha256,
            },
        },
        "targets": {
            "zeta1_focal_surplus_bits": float(row.zeta1_focal_surplus_bits).hex(),
            "zeta3_nonfocal_externality_bits": float(
                row.zeta3_nonfocal_externality_bits
            ).hex(),
            "identity_residual_bits": float(row.identity_residual_bits).hex(),
        },
    }


def _decode_row(payload: object) -> EEAxisOpeningDatasetRow:
    if not isinstance(payload, dict) or set(payload) != {
        "raw",
        "admitted_route",
        "routes",
        "targets",
    }:
        raise OpeningDatasetContractError("dataset row has an unexpected schema")
    raw = _decode_raw(payload["raw"])
    routes = payload["routes"]
    if not isinstance(routes, dict) or set(routes) != {"C1", "C3"}:
        raise OpeningDatasetContractError("dataset row routes must contain C1 and C3")
    route_values: dict[str, dict[str, object]] = {}
    for route in ("C1", "C3"):
        value = routes[route]
        if not isinstance(value, dict) or set(value) != {"source_rule", "comparison_sha256"}:
            raise OpeningDatasetContractError(f"dataset {route} route has an unexpected schema")
        route_values[route] = value
    targets = payload["targets"]
    if not isinstance(targets, dict) or set(targets) != {
        "zeta1_focal_surplus_bits",
        "zeta3_nonfocal_externality_bits",
        "identity_residual_bits",
    }:
        raise OpeningDatasetContractError("dataset row targets have an unexpected schema")
    row = EEAxisOpeningDatasetRow(
        raw_pair=raw,
        admitted_route=_text(payload["admitted_route"], field="admitted_route"),
        c1_source_rule=_text(route_values["C1"]["source_rule"], field="c1_source_rule"),
        c3_source_rule=_text(route_values["C3"]["source_rule"], field="c3_source_rule"),
        c1_comparison_sha256=_digest(
            route_values["C1"]["comparison_sha256"], field="c1_comparison_sha256"
        ),
        c3_comparison_sha256=_digest(
            route_values["C3"]["comparison_sha256"], field="c3_comparison_sha256"
        ),
        zeta1_focal_surplus_bits=_hex_float(
            targets["zeta1_focal_surplus_bits"],
            field="zeta1_focal_surplus_bits",
        ),
        zeta3_nonfocal_externality_bits=_hex_float(
            targets["zeta3_nonfocal_externality_bits"],
            field="zeta3_nonfocal_externality_bits",
        ),
        identity_residual_bits=_hex_float(
            targets["identity_residual_bits"], field="identity_residual_bits"
        ),
    )
    try:
        row.verify()
    except OpeningPairContractError as error:
        raise OpeningDatasetContractError(str(error)) from error
    return row


@dataclass(frozen=True)
class EEAxisOpeningDataset:
    """An immutable, lineage-consistent set of shared D^o comparisons."""

    source_policy_version: int
    source_manifest_sha256: str
    checkpoint_sha256: str
    common_random_field_sha256: str
    state_schema: str
    state_schema_sha256: str
    rows: tuple[EEAxisOpeningDatasetRow, ...]
    schema: str = OPENING_DATASET_SCHEMA
    source_schema: str = OPENING_SOURCE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != OPENING_DATASET_SCHEMA:
            raise OpeningDatasetContractError("dataset schema is stale or unsupported")
        if self.source_schema != OPENING_SOURCE_SCHEMA:
            raise OpeningDatasetContractError("dataset source schema is stale")
        _strict_int(self.source_policy_version, field="source_policy_version", minimum=1)
        _digest(self.source_manifest_sha256, field="source_manifest_sha256")
        _digest(self.checkpoint_sha256, field="checkpoint_sha256")
        _digest(self.common_random_field_sha256, field="common_random_field_sha256")
        if self.state_schema != EE_AXIS_STATE_SCHEMA:
            raise OpeningDatasetContractError("dataset state schema is stale")
        if self.state_schema_sha256 != EE_AXIS_STATE_SCHEMA_SHA256:
            raise OpeningDatasetContractError("dataset state schema digest drifted")
        if not isinstance(self.rows, tuple):
            raise OpeningDatasetContractError("dataset rows must be an immutable tuple")
        seen: set[tuple[str, str]] = set()
        for row in self.rows:
            if not isinstance(row, EEAxisOpeningDatasetRow):
                raise OpeningDatasetContractError("dataset contains a non-row value")
            row.verify()
            raw = row.raw_pair
            if raw.source_policy_version != self.source_policy_version:
                raise OpeningDatasetContractError("mixed source policy versions")
            if raw.source_manifest_sha256 != self.source_manifest_sha256:
                raise OpeningDatasetContractError("mixed source manifest lineage")
            if raw.checkpoint_sha256 != self.checkpoint_sha256:
                raise OpeningDatasetContractError("mixed checkpoint lineage")
            if raw.common_random_field_sha256 != self.common_random_field_sha256:
                raise OpeningDatasetContractError("mixed common random field lineage")
            if raw.state_schema != self.state_schema:
                raise OpeningDatasetContractError("mixed state schema lineage")
            if raw.state_schema_sha256 != self.state_schema_sha256:
                raise OpeningDatasetContractError("mixed state schema digest lineage")
            identity = (raw.comparison_sha256, row.admitted_route)
            if identity in seen:
                raise OpeningDatasetContractError(
                    "duplicate raw comparison and admitted route"
                )
            seen.add(identity)
        if tuple(
            (row.raw_pair.comparison_sha256, row.admitted_route)
            for row in self.rows
        ) != tuple(sorted(seen)):
            raise OpeningDatasetContractError(
                "dataset rows must be digest-and-route sorted"
            )

    @classmethod
    def from_results(
        cls, results: Iterable[EEAxisOpeningSourceResult]
    ) -> "EEAxisOpeningDataset":
        iterator = iter(results)
        try:
            first = next(iterator)
        except StopIteration as error:
            raise OpeningDatasetContractError("D^o dataset cannot be empty") from error
        first_row = EEAxisOpeningDatasetRow.from_result(first)
        raw = first_row.raw_pair
        dataset = cls(
            source_policy_version=raw.source_policy_version,
            source_manifest_sha256=raw.source_manifest_sha256,
            checkpoint_sha256=raw.checkpoint_sha256,
            common_random_field_sha256=raw.common_random_field_sha256,
            state_schema=raw.state_schema,
            state_schema_sha256=raw.state_schema_sha256,
            rows=(first_row,),
        )
        for result in iterator:
            dataset = dataset.add(result)
        return dataset

    def add(self, result: EEAxisOpeningSourceResult) -> "EEAxisOpeningDataset":
        """Return a sorted dataset with one new raw comparison, or deduplicate it."""

        row = EEAxisOpeningDatasetRow.from_result(result)
        raw = row.raw_pair
        if raw.source_policy_version != self.source_policy_version:
            raise OpeningDatasetContractError("mixed source policy versions")
        if raw.source_manifest_sha256 != self.source_manifest_sha256:
            raise OpeningDatasetContractError("mixed source manifest lineage")
        if raw.checkpoint_sha256 != self.checkpoint_sha256:
            raise OpeningDatasetContractError("mixed checkpoint lineage")
        if raw.common_random_field_sha256 != self.common_random_field_sha256:
            raise OpeningDatasetContractError("mixed common random field lineage")
        if raw.state_schema != self.state_schema:
            raise OpeningDatasetContractError("mixed state schema lineage")
        if raw.state_schema_sha256 != self.state_schema_sha256:
            raise OpeningDatasetContractError("mixed state schema digest lineage")
        existing = next(
            (
                candidate
                for candidate in self.rows
                if candidate.raw_pair.comparison_sha256 == raw.comparison_sha256
                and candidate.admitted_route == row.admitted_route
            ),
            None,
        )
        if existing is not None:
            if _row_payload(existing) != _row_payload(row):
                raise OpeningDatasetContractError(
                    "duplicate raw comparison has conflicting route provenance"
                )
            return self
        rows = tuple(
            sorted(
                (*self.rows, row),
                key=lambda item: (
                    item.raw_pair.comparison_sha256,
                    item.admitted_route,
                ),
            )
        )
        return replace(self, rows=rows)

    @property
    def raw_comparison_sha256s(self) -> tuple[str, ...]:
        return tuple(row.raw_pair.comparison_sha256 for row in self.rows)

    @property
    def c1_pairs(self) -> tuple[EEAxisOpeningPair, ...]:
        return tuple(row.c1_pair for row in self.rows if row.admitted_route == "C1")

    @property
    def c3_pairs(self) -> tuple[EEAxisOpeningPair, ...]:
        return tuple(row.c3_pair for row in self.rows if row.admitted_route == "C3")

    def route_pairs(self, route: str) -> tuple[EEAxisOpeningPair, ...]:
        if route == "C1":
            return self.c1_pairs
        if route == "C3":
            return self.c3_pairs
        raise OpeningDatasetContractError("route must be C1 or C3")

    def route_batch(self, route: str) -> EEAxisOpeningRouteBatch:
        try:
            return build_opening_route_batch(self.route_pairs(route))
        except OpeningPairContractError as error:
            raise OpeningDatasetContractError(str(error)) from error

    def c1_batch(self) -> EEAxisOpeningRouteBatch:
        return self.route_batch("C1")

    def c3_batch(self) -> EEAxisOpeningRouteBatch:
        return self.route_batch("C3")

    def verify(self) -> str:
        """Verify the dataset body and return its deterministic body digest."""

        body = _dataset_body(self)
        return _canonical_sha256(body)


def _dataset_body(dataset: EEAxisOpeningDataset) -> dict[str, object]:
    return {
        "schema": dataset.schema,
        "source_schema": dataset.source_schema,
        "source_policy_version": dataset.source_policy_version,
        "source_manifest_sha256": dataset.source_manifest_sha256,
        "checkpoint_sha256": dataset.checkpoint_sha256,
        "common_random_field_sha256": dataset.common_random_field_sha256,
        "state_schema": dataset.state_schema,
        "state_schema_sha256": dataset.state_schema_sha256,
        "rows": [_row_payload(row) for row in dataset.rows],
    }


def _dataset_document(dataset: EEAxisOpeningDataset) -> dict[str, object]:
    body = _dataset_body(dataset)
    return body | {"dataset_sha256": _canonical_sha256(body)}


def write_opening_dataset(path: str | Path, dataset: EEAxisOpeningDataset) -> Path:
    """Atomically create one deterministic JSON snapshot without overwriting."""

    if not isinstance(dataset, EEAxisOpeningDataset):
        raise OpeningDatasetContractError("dataset must be EEAxisOpeningDataset")
    dataset.verify()
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = _dataset_document(dataset)
    encoded = (
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # A hard-link publish is atomic and refuses to replace a prior
            # receipt, unlike os.replace().  Both paths are on one directory.
            os.link(temporary_name, destination)
        except FileExistsError as error:
            raise OpeningDatasetContractError(
                "write-once dataset path already exists"
            ) from error
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    return destination


def read_opening_dataset(path: str | Path) -> EEAxisOpeningDataset:
    """Read and fully verify one deterministic JSON D^o snapshot."""

    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise OpeningDatasetContractError("cannot read opening dataset JSON") from error
    if not isinstance(payload, dict):
        raise OpeningDatasetContractError("opening dataset document must be an object")
    expected = {
        "schema",
        "source_schema",
        "source_policy_version",
        "source_manifest_sha256",
        "checkpoint_sha256",
        "common_random_field_sha256",
        "state_schema",
        "state_schema_sha256",
        "rows",
        "dataset_sha256",
    }
    if set(payload) != expected:
        raise OpeningDatasetContractError("opening dataset document has an unexpected schema")
    supplied_digest = _digest(payload["dataset_sha256"], field="dataset_sha256")
    body = {key: payload[key] for key in expected if key != "dataset_sha256"}
    if _canonical_sha256(body) != supplied_digest:
        raise OpeningDatasetContractError("opening dataset digest disagrees with payload")
    if payload["schema"] != OPENING_DATASET_SCHEMA:
        raise OpeningDatasetContractError("opening dataset schema is stale or unsupported")
    if payload["source_schema"] != OPENING_SOURCE_SCHEMA:
        raise OpeningDatasetContractError("opening dataset source schema is stale")
    rows_payload = payload["rows"]
    if not isinstance(rows_payload, list) or not rows_payload:
        raise OpeningDatasetContractError("opening dataset rows must be nonempty")
    rows = tuple(_decode_row(row) for row in rows_payload)
    try:
        dataset = EEAxisOpeningDataset(
            source_policy_version=_strict_int(
                payload["source_policy_version"],
                field="source_policy_version",
                minimum=1,
            ),
            source_manifest_sha256=_digest(
                payload["source_manifest_sha256"], field="source_manifest_sha256"
            ),
            checkpoint_sha256=_digest(
                payload["checkpoint_sha256"], field="checkpoint_sha256"
            ),
            common_random_field_sha256=_digest(
                payload["common_random_field_sha256"],
                field="common_random_field_sha256",
            ),
            state_schema=_text(payload["state_schema"], field="state_schema"),
            state_schema_sha256=_digest(
                payload["state_schema_sha256"], field="state_schema_sha256"
            ),
            rows=rows,
            schema=payload["schema"],
            source_schema=payload["source_schema"],
        )
    except OpeningPairContractError as error:
        raise OpeningDatasetContractError(str(error)) from error
    return dataset


__all__ = [
    "EEAxisOpeningDataset",
    "EEAxisOpeningDatasetRow",
    "OPENING_DATASET_SCHEMA",
    "OpeningDatasetContractError",
    "read_opening_dataset",
    "write_opening_dataset",
]
