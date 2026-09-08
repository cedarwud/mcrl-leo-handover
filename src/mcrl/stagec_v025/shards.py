"""Authenticated TRAIN-only JSONL source shards."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Mapping

from .canonical import (
    StageCContractError,
    canonical_json_bytes,
    canonical_sha256,
    parse_float_hex,
    verify_sha256_sidecar,
    write_once_with_sha256,
)
from .state import (
    PhysicalAction,
    Q1_FEATURES,
    Q1_SCHEMA_SHA256,
    Q2_FEATURES,
    Q2_SCHEMA_SHA256,
    ROW_SCHEMA_VERSION,
    SourceRow,
)


SHARD_SCHEMA_VERSION = "mcrl-v025-stagec-source-shard-v1-draft"


@dataclass(frozen=True, slots=True)
class SourceShard:
    path: Path
    file_sha256: str
    rows_sha256: str
    rows: tuple[SourceRow, ...]


def _parse_digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise StageCContractError(f"{field} must be a lowercase SHA-256")
    return value


def _row_from_payload(payload: Mapping[str, object]) -> SourceRow:
    expected = {
        "schema", "split", "world_id", "world_seed", "learner_seed", "anchor_id",
        "anchor_index", "decision_time_utc", "decision_time_ns", "user_id",
        "action_index", "action", "reference_action", "action_mask", "q1_state",
        "q2_state", "q1_schema_sha256", "q2_schema_sha256", "setting_id",
        "code_digest", "physics_digest", "launch_digest", "catalogue_digest",
        "setting_digest", "calibration_digest",
        "provider_digest", "archive_digest",
        "allocation_manifest_digest", "lambda_bits_per_j_hex", "eta_ref_bits_per_j_hex",
        "kappa_normalization_bits_hex", "c1_label_bits_hex", "c1_phi_difference_hex", "c2_label_bits_hex",
        "c3_label_bits_hex", "c1_label_normalized_hex", "c2_label_normalized_hex",
        "c3_label_normalized_hex", "terminal", "null_action", "outage",
    }
    if set(payload) != expected:
        raise StageCContractError("source row schema drifted")
    action = payload["action"]
    if not isinstance(action, Mapping) or set(action) != {"norad_id", "beam_chain_id"}:
        raise StageCContractError("source row physical action schema drifted")
    q1 = payload["q1_state"]
    q2 = payload["q2_state"]
    mask = payload["action_mask"]
    if not isinstance(q1, list) or not isinstance(q2, list) or not isinstance(mask, list):
        raise StageCContractError("source row arrays must be JSON lists")
    if len(q1) != len(Q1_FEATURES) or len(q2) != len(Q2_FEATURES):
        raise StageCContractError("source row state vector dimension drifted")
    if not mask or any(not isinstance(value, bool) for value in mask):
        raise StageCContractError("source row action mask must contain booleans")
    float_fields = (
        "lambda_bits_per_j_hex", "eta_ref_bits_per_j_hex", "kappa_normalization_bits_hex",
        "c1_label_bits_hex", "c1_phi_difference_hex", "c2_label_bits_hex", "c3_label_bits_hex",
        "c1_label_normalized_hex", "c2_label_normalized_hex", "c3_label_normalized_hex",
    )
    for field in float_fields:
        parse_float_hex(payload[field], field=field)
    row = SourceRow(
        schema=str(payload["schema"]),
        split=str(payload["split"]),
        world_id=str(payload["world_id"]),
        world_seed=int(payload["world_seed"]),
        learner_seed=None if payload["learner_seed"] is None else int(payload["learner_seed"]),
        anchor_id=str(payload["anchor_id"]),
        anchor_index=int(payload["anchor_index"]),
        decision_time_utc=str(payload["decision_time_utc"]),
        decision_time_ns=int(payload["decision_time_ns"]),
        user_id=int(payload["user_id"]),
        action_index=int(payload["action_index"]),
        action=PhysicalAction(
            None if action["norad_id"] is None else int(action["norad_id"]),
            None if action["beam_chain_id"] is None else int(action["beam_chain_id"]),
        ),
        reference_action=bool(payload["reference_action"]),
        action_mask=tuple(bool(value) for value in mask),
        q1_state=tuple(parse_float_hex(value, field="q1_state") for value in q1),
        q2_state=tuple(parse_float_hex(value, field="q2_state") for value in q2),
        q1_schema_sha256=str(payload["q1_schema_sha256"]),
        q2_schema_sha256=str(payload["q2_schema_sha256"]),
        setting_id=str(payload["setting_id"]),
        code_digest=str(payload["code_digest"]),
        physics_digest=str(payload["physics_digest"]),
        launch_digest=str(payload["launch_digest"]),
        catalogue_digest=str(payload["catalogue_digest"]),
        setting_digest=str(payload["setting_digest"]),
        calibration_digest=str(payload["calibration_digest"]),
        provider_digest=str(payload["provider_digest"]),
        archive_digest=str(payload["archive_digest"]),
        allocation_manifest_digest=str(payload["allocation_manifest_digest"]),
        lambda_bits_per_j_hex=str(payload["lambda_bits_per_j_hex"]),
        eta_ref_bits_per_j_hex=str(payload["eta_ref_bits_per_j_hex"]),
        kappa_normalization_bits_hex=str(payload["kappa_normalization_bits_hex"]),
        c1_label_bits_hex=str(payload["c1_label_bits_hex"]),
        c1_phi_difference_hex=str(payload["c1_phi_difference_hex"]),
        c2_label_bits_hex=str(payload["c2_label_bits_hex"]),
        c3_label_bits_hex=str(payload["c3_label_bits_hex"]),
        c1_label_normalized_hex=str(payload["c1_label_normalized_hex"]),
        c2_label_normalized_hex=str(payload["c2_label_normalized_hex"]),
        c3_label_normalized_hex=str(payload["c3_label_normalized_hex"]),
        terminal=bool(payload["terminal"]),
        null_action=bool(payload["null_action"]),
        outage=bool(payload["outage"]),
    )
    if row.schema != ROW_SCHEMA_VERSION or row.split != "TRAIN":
        raise StageCContractError("source shard contains a non-TRAIN or unsupported row")
    if row.q1_schema_sha256 != Q1_SCHEMA_SHA256 or row.q2_schema_sha256 != Q2_SCHEMA_SHA256:
        raise StageCContractError("source row state schema digest drifted")
    for field in (
        "code_digest", "physics_digest", "launch_digest", "catalogue_digest",
        "setting_digest", "calibration_digest",
        "provider_digest", "archive_digest",
        "allocation_manifest_digest",
    ):
        _parse_digest(getattr(row, field), field=field)
    if row.null_action != row.action.is_null:
        raise StageCContractError("null-action flag disagrees with physical identity")
    if (
        row.action_index < 0
        or row.action_index >= len(row.action_mask)
        or not row.action_mask[row.action_index]
    ):
        raise StageCContractError("source row action index is absent or masked")
    if row.reference_action and not row.action_mask[row.action_index]:
        raise StageCContractError("source row BASE action is masked")
    lambda_bits_per_j = parse_float_hex(
        row.lambda_bits_per_j_hex, field="lambda_bits_per_j_hex"
    )
    eta_ref_bits_per_j = parse_float_hex(
        row.eta_ref_bits_per_j_hex, field="eta_ref_bits_per_j_hex"
    )
    kappa = parse_float_hex(
        row.kappa_normalization_bits_hex,
        field="kappa_normalization_bits_hex",
    )
    if lambda_bits_per_j <= 0.0 or lambda_bits_per_j != eta_ref_bits_per_j:
        raise StageCContractError("source row lambda and eta_ref must be equal and positive")
    if kappa <= 0.0:
        raise StageCContractError("source row kappa must be positive")
    expected_normalized = {
        "c1_label_normalized_hex": float.hex(
            parse_float_hex(row.c1_label_bits_hex, field="c1_label_bits_hex") / kappa
            + parse_float_hex(row.c1_phi_difference_hex, field="c1_phi_difference_hex")
        ),
        "c2_label_normalized_hex": float.hex(
            parse_float_hex(row.c2_label_bits_hex, field="c2_label_bits_hex") / kappa
        ),
        "c3_label_normalized_hex": float.hex(
            parse_float_hex(row.c3_label_bits_hex, field="c3_label_bits_hex") / kappa
        ),
    }
    for field, expected_value in expected_normalized.items():
        if getattr(row, field) != expected_value:
            raise StageCContractError(f"source row {field} was not recomputed from raw labels")
    return row


def write_source_shard(path: str | Path, rows: Iterable[SourceRow]) -> SourceShard:
    destination = Path(path)
    material = tuple(rows)
    if not material:
        raise StageCContractError("cannot write an empty source shard")
    payloads = [row.payload() for row in material]
    for payload in payloads:
        _row_from_payload(payload)
    rows_digest = canonical_sha256(payloads)
    header = {
        "schema": SHARD_SCHEMA_VERSION,
        "split": "TRAIN",
        "row_count": len(payloads),
        "rows_sha256": rows_digest,
        "q1_schema_sha256": Q1_SCHEMA_SHA256,
        "q2_schema_sha256": Q2_SCHEMA_SHA256,
        "settings": sorted({row.setting_digest for row in material}),
        "calibrations": sorted({row.calibration_digest for row in material}),
        "source_authority_sha256": canonical_sha256(
            [
                {
                    "code_digest": row.code_digest,
                    "physics_digest": row.physics_digest,
                    "launch_digest": row.launch_digest,
                    "catalogue_digest": row.catalogue_digest,
                    "provider_digest": row.provider_digest,
                    "archive_digest": row.archive_digest,
                    "setting_digest": row.setting_digest,
                    "calibration_digest": row.calibration_digest,
                    "allocation_manifest_digest": row.allocation_manifest_digest,
                }
                for row in material
            ]
        ),
    }
    encoded = b"\n".join(canonical_json_bytes(value) for value in (header, *payloads)) + b"\n"
    file_digest = write_once_with_sha256(destination, encoded)
    return SourceShard(destination, file_digest, rows_digest, material)


def read_source_shard(path: str | Path) -> SourceShard:
    source = Path(path)
    file_digest = verify_sha256_sidecar(source)
    try:
        raw_lines = source.read_bytes().splitlines()
        values = [json.loads(line.decode("ascii")) for line in raw_lines]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StageCContractError(f"cannot parse source shard: {source}") from error
    if not values or not isinstance(values[0], Mapping):
        raise StageCContractError("source shard header is missing")
    if any(
        line != canonical_json_bytes(value)
        for line, value in zip(raw_lines, values, strict=True)
    ):
        raise StageCContractError("source shard is not canonical JSONL")
    header = values[0]
    expected_header = {
        "schema", "split", "row_count", "rows_sha256", "q1_schema_sha256",
        "q2_schema_sha256", "settings", "calibrations", "source_authority_sha256",
    }
    if set(header) != expected_header or header["schema"] != SHARD_SCHEMA_VERSION:
        raise StageCContractError("source shard header schema drifted")
    if header["split"] != "TRAIN":
        raise StageCContractError("source shard is not TRAIN-only")
    rows = tuple(_row_from_payload(value) for value in values[1:] if isinstance(value, Mapping))
    if len(rows) != len(values) - 1 or len(rows) != int(header["row_count"]):
        raise StageCContractError("source shard row count drifted")
    rows_digest = canonical_sha256([row.payload() for row in rows])
    if rows_digest != header["rows_sha256"]:
        raise StageCContractError("source shard row digest drifted")
    if header["q1_schema_sha256"] != Q1_SCHEMA_SHA256 or header["q2_schema_sha256"] != Q2_SCHEMA_SHA256:
        raise StageCContractError("source shard header state schema drifted")
    if header["settings"] != sorted({row.setting_digest for row in rows}):
        raise StageCContractError("source shard setting inventory drifted")
    if header["calibrations"] != sorted({row.calibration_digest for row in rows}):
        raise StageCContractError("source shard calibration inventory drifted")
    expected_authority = canonical_sha256(
        [
            {
                "code_digest": row.code_digest,
                "physics_digest": row.physics_digest,
                "launch_digest": row.launch_digest,
                "catalogue_digest": row.catalogue_digest,
                "provider_digest": row.provider_digest,
                "archive_digest": row.archive_digest,
                "setting_digest": row.setting_digest,
                "calibration_digest": row.calibration_digest,
                "allocation_manifest_digest": row.allocation_manifest_digest,
            }
            for row in rows
        ]
    )
    if header["source_authority_sha256"] != expected_authority:
        raise StageCContractError("source shard authority digest drifted")
    return SourceShard(source, file_digest, rows_digest, rows)


__all__ = ["SHARD_SCHEMA_VERSION", "SourceShard", "read_source_shard", "write_source_shard"]
