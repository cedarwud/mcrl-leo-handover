"""Authenticated, target-free state authority for the V0.6 C2-k1 learner.

The source gate intentionally does not persist learner states.  This module
defines the write-once sidecar produced by replaying the exact sealed
``PREPARE_LIVE`` anchors.  Structural verification alone is not an
authorization: a learner must also consume a sealed live-replay verification
receipt produced by the production state-authority command.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from .ee_axis_state import (
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)
from .ee_axis_v06_c2_k1 import (
    ACTION_COUNT,
    CLAIM_CEILING,
    POLICY_RULE,
    SCHEMA as ALGORITHM_SCHEMA,
    SOURCE_RULE,
    TRAIN_STEP_WINDOWS,
    TRAIN_WORLD_POOLS,
)


PREPARE_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t1-prepare-live-v2"
PREPARE_SEAL_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t1-prepare-live-seal-v2"
SIDECAR_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-state-sidecar-v2"
SIDECAR_SEAL_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-state-sidecar-seal-v2"
LIVE_VERIFICATION_SCHEMA = (
    "multi-catfish-mcrl-v06-c2-k1-state-live-verification-v1"
)
LIVE_VERIFICATION_SEAL_SCHEMA = (
    "multi-catfish-mcrl-v06-c2-k1-state-live-verification-seal-v1"
)
STATE_SOURCE_RULE = "authenticated-main-replay-focal-predecision-state-v2"
LINEAGES = ("q13-a", "q13-b", "q13-c")
LINEAGE_SEEDS = (2026092101, 2026092102, 2026092103)
WORLD_COUNT = 12
USER_COUNT = 100

KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")
LAMBDA_BITS_PER_J = float.fromhex("0x1.443a8f481639ap+26")
FORMULA_CONTRACT = {
    "interval_s": 30.08,
    "lambda_bits_per_j": LAMBDA_BITS_PER_J,
    "kappa_bits": KAPPA_BITS,
    "z1": "dt*delta_rate_focal_k0-lambda*dt*delta_power_k0",
    "z3": "dt*sum_delta_rate_nonfocal_k0",
    "z2_k1": "dt*sum_delta_rate_k1-lambda*dt*delta_power_k1",
    "oracle": "argmax_masked(Q1_k0+Q3_k0+z2_k1/kappa)",
    "drop": "argmax_masked(Q1_k0+Q3_k0)",
    "ee": "sum_canonical_rates/sum_energy",
}
GATE_CONTRACT = {
    "pairs": 1008,
    "controls": 36,
    "positive_lineages": 2,
    "positive_worlds": 8,
    "service_nonnegative_lineages": 2,
    "users": USER_COUNT,
    "identity_relative_tolerance": 1e-9,
    "claim_ceiling": CLAIM_CEILING,
}
SOURCE_AUTHORITY = {
    "scanner": "run_v04_c2_support_complete_census._real_seed_topology",
    "simulator_manifest": (
        "run_v04_c2_support_complete_census._production_source_manifest"
    ),
    "loader": "run_v04_c3_source._default_runtime",
    "q13_gate": "run_v04_c2_phase_b._authenticate_q13_gate",
    "q13_gate_manifest": "q13_gate.source_manifest_sha256",
    "field": "mcrl.env.keyed_fading.KeyedFadingField",
}

_PREPARE_FIELDS = frozenset(
    {
        "algorithm_schema",
        "anchors",
        "claim_ceiling",
        "code_authority",
        "counts",
        "formula_contract",
        "gate_contract",
        "lineage_bindings",
        "lineages",
        "main_checkpoint_sha256",
        "main_dir",
        "outcome_selection",
        "policy_rule",
        "prepare_sha256",
        "prepared_before_generation",
        "q13_gate_source_manifest_sha256",
        "q2_consulted",
        "schema",
        "simulator_prereg_file_sha256",
        "simulator_source_manifest_sha256",
        "source_authority",
        "source_rule",
        "t1_prereg_file_sha256",
        "test_split_opened",
        "training",
    }
)
_ANCHOR_FIELDS = frozenset(
    {
        "anchor_sha256",
        "candidate_actions",
        "candidate_physical_keys",
        "checkpoint_sha256",
        "complete_forecast_horizon",
        "evaluation_seed",
        "focal_user",
        "incumbent_physical_key",
        "legal_action_mask",
        "physical_main_departure",
        "policy_sha256",
        "pool",
        "predecision_only",
        "reference_action",
        "reference_physical_key",
        "simulator_source_manifest_sha256",
        "step",
        "world_anchor_sha256",
        "world_id",
    }
)
_BINDING_FIELDS = frozenset(
    {
        "a_D",
        "crn_sha256",
        "hybrid_sha256",
        "initialization_seed",
        "q13_score_vector",
        "q1_sha256",
        "q3_sha256",
    }
)
_CAPTURE_FIELDS = frozenset(
    {
        "anchor_key",
        "pool",
        "world_id",
        "step",
        "focal_user",
        "reference_action",
        "anchor_sha256",
        "world_anchor_sha256",
        "checkpoint_sha256",
        "policy_sha256",
        "simulator_source_manifest_sha256",
        "crn_sha256",
        "lineage_binding_sha256",
        "state_schema",
        "state_schema_sha256",
        "state_float32_hex",
        "action_mask",
        "state_sha256",
        "mask_sha256",
        "all_user_encoder_sha256",
        "main_reference_vector_sha256",
    }
)
_SIDECAR_FIELDS = frozenset(
    {
        "schema",
        "source_rule",
        "algorithm_schema",
        "state_schema",
        "state_schema_sha256",
        "prepare_sha256",
        "prepare_file_sha256",
        "prepare_seal_file_sha256",
        "t1_prereg_file_sha256",
        "learner_prereg_file_sha256",
        "capture_code_authority",
        "lineage_authority_sha256",
        "counts",
        "anchors",
        "target_free",
        "training",
        "test_split_opened",
        "outcome_selection",
        "q2_consulted",
        "sidecar_sha256",
    }
)


class C2K1StateAuthorityError(ValueError):
    """The state authority is malformed, stale, or unauthenticated."""


def canonical_sha256(payload: object) -> str:
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise C2K1StateAuthorityError("payload is not canonical finite JSON") from error
    return hashlib.sha256(encoded).hexdigest()


def regular_file_bytes(path: Path) -> bytes:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise C2K1StateAuthorityError(f"missing regular file: {source}")
    return source.read_bytes()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(regular_file_bytes(path)).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C2K1StateAuthorityError(f"{field} must be a lowercase SHA-256")
    return value


def _exact_keys(value: object, expected: frozenset[str], *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        actual = sorted(value) if isinstance(value, Mapping) else type(value).__name__
        raise C2K1StateAuthorityError(
            f"{field} schema drifted; expected {sorted(expected)}, got {actual}"
        )
    return value


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise C2K1StateAuthorityError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_exact_json(path: Path) -> dict[str, Any]:
    raw = regular_file_bytes(path)
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_json_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise C2K1StateAuthorityError(f"invalid JSON: {path}") from error
    if not isinstance(payload, dict):
        raise C2K1StateAuthorityError(f"JSON root must be an object: {path}")
    return payload


def _anchor_key(anchor: Mapping[str, Any]) -> str:
    return (
        f"{anchor['pool']}:{anchor['world_id']}:{anchor['step']}:"
        f"{anchor['focal_user']}"
    )


def _physical_key(value: object, *, field: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(item) is not int for item in value)
    ):
        raise C2K1StateAuthorityError(f"{field} must be a two-integer list")
    return int(value[0]), int(value[1])


def _validate_prepare_payload(prepare: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(prepare, _PREPARE_FIELDS, field="PREPARE")
    unsigned = dict(prepare)
    supplied = _digest(unsigned.pop("prepare_sha256"), field="prepare_sha256")
    if canonical_sha256(unsigned) != supplied:
        raise C2K1StateAuthorityError("PREPARE payload hash drifted")
    expected_scalars = {
        "schema": PREPARE_SCHEMA,
        "algorithm_schema": ALGORITHM_SCHEMA,
        "source_rule": SOURCE_RULE,
        "policy_rule": POLICY_RULE,
        "claim_ceiling": CLAIM_CEILING,
        "formula_contract": FORMULA_CONTRACT,
        "gate_contract": GATE_CONTRACT,
        "lineages": list(LINEAGES),
        "source_authority": SOURCE_AUTHORITY,
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
        "prepared_before_generation": True,
    }
    for field, expected in expected_scalars.items():
        if prepare.get(field) != expected:
            raise C2K1StateAuthorityError(f"PREPARE {field} drifted")
    if not isinstance(prepare.get("main_dir"), str) or not prepare["main_dir"].startswith("/"):
        raise C2K1StateAuthorityError("PREPARE main_dir is not absolute")
    for field in (
        "main_checkpoint_sha256",
        "simulator_source_manifest_sha256",
        "q13_gate_source_manifest_sha256",
        "simulator_prereg_file_sha256",
        "t1_prereg_file_sha256",
    ):
        _digest(prepare.get(field), field=f"PREPARE.{field}")
    counts = _exact_keys(
        prepare.get("counts"),
        frozenset(
            {
                "expected_controls",
                "expected_pairs",
                "lineages",
                "openings_per_anchor_lineage",
                "pools",
                "users",
                "worlds",
            }
        ),
        field="PREPARE.counts",
    )
    if dict(counts) != {
        "expected_controls": 36,
        "expected_pairs": 1008,
        "lineages": 3,
        "openings_per_anchor_lineage": 28,
        "pools": 3,
        "users": USER_COUNT,
        "worlds": WORLD_COUNT,
    }:
        raise C2K1StateAuthorityError("PREPARE counts drifted")
    code = _exact_keys(
        prepare.get("code_authority"),
        frozenset({"files", "sha256"}),
        field="PREPARE.code_authority",
    )
    files = _exact_keys(
        code.get("files"),
        frozenset(
            {
                "live_adapter",
                "main_loader",
                "phase_b_loader",
                "runner",
                "runtime",
                "server_launcher",
                "support_scanner",
            }
        ),
        field="PREPARE.code_authority.files",
    )
    for name, digest in files.items():
        _digest(digest, field=f"PREPARE.code_authority.files.{name}")
    if _digest(code.get("sha256"), field="PREPARE.code_authority.sha256") != canonical_sha256(dict(files)):
        raise C2K1StateAuthorityError("PREPARE code authority hash drifted")

    anchors = prepare.get("anchors")
    if not isinstance(anchors, list) or len(anchors) != WORLD_COUNT:
        raise C2K1StateAuthorityError("PREPARE must contain exactly 12 anchors")
    pool_order = {"early": 0, "mid": 1, "late": 2}
    expected_pool_counts = {name: 0 for name in pool_order}
    anchor_map: dict[str, Mapping[str, Any]] = {}
    previous_sort: tuple[int, int] | None = None
    for index, raw in enumerate(anchors):
        anchor = _exact_keys(raw, _ANCHOR_FIELDS, field=f"PREPARE.anchor[{index}]")
        pool, world = anchor.get("pool"), anchor.get("world_id")
        if pool not in pool_order or type(world) is not int or world not in TRAIN_WORLD_POOLS[pool]:
            raise C2K1StateAuthorityError("PREPARE anchor is outside frozen pools")
        step, focal, reference = (
            anchor.get("step"),
            anchor.get("focal_user"),
            anchor.get("reference_action"),
        )
        if type(step) is not int or not TRAIN_STEP_WINDOWS[pool][0] <= step <= TRAIN_STEP_WINDOWS[pool][1]:
            raise C2K1StateAuthorityError("PREPARE anchor step is outside frozen window")
        if type(focal) is not int or not 0 <= focal < USER_COUNT:
            raise C2K1StateAuthorityError("PREPARE focal user is malformed")
        if type(reference) is not int or not 0 <= reference < ACTION_COUNT:
            raise C2K1StateAuthorityError("PREPARE reference action is malformed")
        if anchor.get("evaluation_seed") != world:
            raise C2K1StateAuthorityError("PREPARE evaluation seed drifted")
        if any(
            anchor.get(field) is not True
            for field in (
                "predecision_only",
                "physical_main_departure",
                "complete_forecast_horizon",
            )
        ):
            raise C2K1StateAuthorityError("PREPARE anchor eligibility drifted")
        for field in (
            "anchor_sha256",
            "world_anchor_sha256",
            "checkpoint_sha256",
            "policy_sha256",
            "simulator_source_manifest_sha256",
        ):
            _digest(anchor.get(field), field=f"PREPARE.anchor.{field}")
        if anchor["checkpoint_sha256"] != prepare["main_checkpoint_sha256"]:
            raise C2K1StateAuthorityError("PREPARE anchor checkpoint drifted")
        if anchor["simulator_source_manifest_sha256"] != prepare["simulator_source_manifest_sha256"]:
            raise C2K1StateAuthorityError("PREPARE anchor simulator authority drifted")
        mask = anchor.get("legal_action_mask")
        if not isinstance(mask, list) or len(mask) != ACTION_COUNT or any(type(item) is not bool for item in mask) or not all(mask):
            raise C2K1StateAuthorityError("PREPARE anchor lacks complete native mask")
        actions = anchor.get("candidate_actions")
        if (
            not isinstance(actions, list)
            or len(actions) != ACTION_COUNT - 1
            or any(type(action) is not int for action in actions)
            or set(actions) != set(range(ACTION_COUNT)) - {reference}
            or len(set(actions)) != ACTION_COUNT - 1
        ):
            raise C2K1StateAuthorityError("PREPARE candidate action coverage drifted")
        reference_key = _physical_key(anchor.get("reference_physical_key"), field="reference_physical_key")
        _physical_key(anchor.get("incumbent_physical_key"), field="incumbent_physical_key")
        candidate_keys = anchor.get("candidate_physical_keys")
        if not isinstance(candidate_keys, list) or len(candidate_keys) != ACTION_COUNT - 1:
            raise C2K1StateAuthorityError("PREPARE candidate physical keys drifted")
        parsed_keys = [
            _physical_key(value, field="candidate_physical_key")
            for value in candidate_keys
        ]
        if len(set(parsed_keys)) != ACTION_COUNT - 1 or reference_key in parsed_keys:
            raise C2K1StateAuthorityError("PREPARE physical action mapping aliases")
        sort_key = (pool_order[pool], world)
        if previous_sort is not None and sort_key <= previous_sort:
            raise C2K1StateAuthorityError("PREPARE anchors are not canonical")
        previous_sort = sort_key
        key = _anchor_key(anchor)
        if key in anchor_map:
            raise C2K1StateAuthorityError("PREPARE anchor key repeats")
        anchor_map[key] = anchor
        expected_pool_counts[pool] += 1
    if expected_pool_counts != {"early": 4, "mid": 4, "late": 4}:
        raise C2K1StateAuthorityError("PREPARE pool allocation drifted")

    bindings = prepare.get("lineage_bindings")
    if not isinstance(bindings, Mapping) or set(bindings) != set(anchor_map):
        raise C2K1StateAuthorityError("PREPARE lineage binding coverage drifted")
    for key, anchor in anchor_map.items():
        cell = bindings[key]
        if not isinstance(cell, Mapping) or set(cell) != set(LINEAGES):
            raise C2K1StateAuthorityError(f"PREPARE lineage cell drifted: {key}")
        crn_values: set[str] = set()
        for lineage, seed in zip(LINEAGES, LINEAGE_SEEDS, strict=True):
            item = _exact_keys(cell[lineage], _BINDING_FIELDS, field=f"PREPARE.{key}.{lineage}")
            for field in ("crn_sha256", "hybrid_sha256", "q1_sha256", "q3_sha256"):
                _digest(item.get(field), field=f"PREPARE.{key}.{lineage}.{field}")
            if item.get("initialization_seed") != seed:
                raise C2K1StateAuthorityError("PREPARE Q13 lineage seed drifted")
            scores = item.get("q13_score_vector")
            if not isinstance(scores, list) or len(scores) != ACTION_COUNT or any(type(value) not in (int, float) or not math.isfinite(float(value)) for value in scores):
                raise C2K1StateAuthorityError("PREPARE Q13 score vector drifted")
            expected_action = min(
                range(ACTION_COUNT),
                key=lambda action: (-float(scores[action]), action),
            )
            if item.get("a_D") != expected_action:
                raise C2K1StateAuthorityError("PREPARE Q13 argmax drifted")
            crn_values.add(str(item["crn_sha256"]))
        if len(crn_values) != 1:
            raise C2K1StateAuthorityError("PREPARE lineages do not share one CRN")
    return {
        "prepare": prepare,
        "anchor_map": anchor_map,
        "prepare_sha256": supplied,
        "lineage_authority_sha256": canonical_sha256(bindings),
    }


def verify_formal_prepare_files(
    *,
    prepare_path: Path,
    prepare_seal_path: Path,
    t1_prereg_path: Path,
) -> dict[str, Any]:
    """Authenticate the exact PREPARE bytes, seal, and current T1 prereg."""

    prepare = read_exact_json(prepare_path)
    authority = _validate_prepare_payload(prepare)
    seal = _exact_keys(
        read_exact_json(prepare_seal_path),
        frozenset(
            {
                "schema",
                "prepare_sha256",
                "prepare_file_sha256",
                "training",
                "test_split_opened",
                "outcome_selection",
            }
        ),
        field="PREPARE seal",
    )
    if seal != {
        "schema": PREPARE_SEAL_SCHEMA,
        "prepare_sha256": authority["prepare_sha256"],
        "prepare_file_sha256": file_sha256(prepare_path),
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
    }:
        raise C2K1StateAuthorityError("PREPARE file seal is invalid")
    t1_sha = file_sha256(t1_prereg_path)
    if prepare.get("t1_prereg_file_sha256") != t1_sha:
        raise C2K1StateAuthorityError("current T1 prereg differs from PREPARE")
    return authority | {
        "prepare_file_sha256": file_sha256(prepare_path),
        "prepare_seal_file_sha256": file_sha256(prepare_seal_path),
        "t1_prereg_file_sha256": t1_sha,
    }


def capture_code_authority(files: Mapping[str, Path]) -> dict[str, Any]:
    if not isinstance(files, Mapping) or not files:
        raise C2K1StateAuthorityError("capture code authority is empty")
    manifest: dict[str, str] = {}
    for name, path in sorted(files.items()):
        if not isinstance(name, str) or not name:
            raise C2K1StateAuthorityError("capture code authority name is malformed")
        manifest[name] = file_sha256(Path(path))
    return {"files": manifest, "sha256": canonical_sha256(manifest)}


def _float32_hex(values: object, *, field: str) -> tuple[np.ndarray, list[str]]:
    raw = np.asarray(values)
    if raw.shape != (EE_AXIS_STATE_DIM,) or raw.dtype.kind not in "fiu":
        raise C2K1StateAuthorityError(
            f"{field} must be numeric shape ({EE_AXIS_STATE_DIM},)"
        )
    encoded = np.asarray(raw, dtype=np.float32)
    if not np.all(np.isfinite(encoded)):
        raise C2K1StateAuthorityError(f"{field} must be finite float32")
    return encoded, [float(value).hex() for value in encoded.tolist()]


def _parse_float32_hex(values: object, *, field: str) -> tuple[np.ndarray, list[str]]:
    if not isinstance(values, list) or len(values) != EE_AXIS_STATE_DIM or any(not isinstance(value, str) for value in values):
        raise C2K1StateAuthorityError(
            f"{field} must contain {EE_AXIS_STATE_DIM} hexadecimal strings"
        )
    try:
        array = np.asarray([float.fromhex(value) for value in values], dtype=np.float32)
    except (ValueError, OverflowError) as error:
        raise C2K1StateAuthorityError(f"{field} contains malformed hex") from error
    canonical = [float(value).hex() for value in array.tolist()]
    if canonical != values or not np.all(np.isfinite(array)):
        raise C2K1StateAuthorityError(f"{field} is not canonical finite float32 hex")
    return array, canonical


def _mask(value: object, *, field: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != (NUM_ACTIONS,) or raw.dtype != np.bool_ or not bool(np.all(raw)):
        raise C2K1StateAuthorityError(f"{field} must be the complete Boolean mask")
    return np.array(raw, dtype=np.bool_, copy=True)


def _state_sha(hex_values: Sequence[str], mask: Sequence[bool]) -> str:
    return canonical_sha256(
        {
            "state_schema": EE_AXIS_STATE_SCHEMA,
            "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
            "state_float32_hex": list(hex_values),
            "action_mask": list(mask),
        }
    )


def _mask_sha(mask: Sequence[bool]) -> str:
    return canonical_sha256({"action_dim": NUM_ACTIONS, "action_mask": list(mask)})


def build_state_sidecar(
    *,
    authority: Mapping[str, Any],
    learner_prereg_file_sha256: str,
    code_authority: Mapping[str, Any],
    captures: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Seal twelve states already derived by the production replay command."""

    learner_sha = _digest(
        learner_prereg_file_sha256,
        field="learner_prereg_file_sha256",
    )
    code = _exact_keys(
        code_authority,
        frozenset({"files", "sha256"}),
        field="capture_code_authority",
    )
    files = code.get("files")
    if not isinstance(files, Mapping) or not files:
        raise C2K1StateAuthorityError("capture code files are empty")
    for name, digest in files.items():
        if not isinstance(name, str) or not name:
            raise C2K1StateAuthorityError("capture code file name is malformed")
        _digest(digest, field=f"capture code {name}")
    if _digest(code.get("sha256"), field="capture code sha256") != canonical_sha256(dict(files)):
        raise C2K1StateAuthorityError("capture code authority hash drifted")
    anchor_map = authority.get("anchor_map")
    prepare = authority.get("prepare")
    if not isinstance(anchor_map, Mapping) or not isinstance(prepare, Mapping):
        raise C2K1StateAuthorityError("formal PREPARE authority is missing")
    if not isinstance(captures, Mapping) or set(captures) != set(anchor_map):
        raise C2K1StateAuthorityError("capture must cover exactly 12 PREPARE anchors")
    rows: list[dict[str, Any]] = []
    for key, anchor in anchor_map.items():
        capture = captures[key]
        if not isinstance(capture, Mapping):
            raise C2K1StateAuthorityError(f"capture {key} is malformed")
        if set(capture) != {
            "state",
            "action_mask",
            "crn_sha256",
            "all_user_encoder_sha256",
            "main_reference_vector_sha256",
        }:
            raise C2K1StateAuthorityError(f"capture {key} schema drifted")
        _, state_hex = _float32_hex(capture["state"], field=f"capture {key}.state")
        mask = _mask(capture["action_mask"], field=f"capture {key}.action_mask")
        expected_mask = np.asarray(anchor["legal_action_mask"], dtype=np.bool_)
        if not np.array_equal(mask, expected_mask):
            raise C2K1StateAuthorityError(f"capture {key} mask disagrees with PREPARE")
        cell = prepare["lineage_bindings"][key]
        crn_values = {item["crn_sha256"] for item in cell.values()}
        crn = _digest(capture["crn_sha256"], field=f"capture {key}.crn_sha256")
        if crn_values != {crn}:
            raise C2K1StateAuthorityError(f"capture {key} CRN disagrees with PREPARE")
        for field in ("all_user_encoder_sha256", "main_reference_vector_sha256"):
            _digest(capture[field], field=f"capture {key}.{field}")
        mask_list = [bool(value) for value in mask.tolist()]
        rows.append(
            {
                "anchor_key": key,
                "pool": anchor["pool"],
                "world_id": anchor["world_id"],
                "step": anchor["step"],
                "focal_user": anchor["focal_user"],
                "reference_action": anchor["reference_action"],
                "anchor_sha256": anchor["anchor_sha256"],
                "world_anchor_sha256": anchor["world_anchor_sha256"],
                "checkpoint_sha256": anchor["checkpoint_sha256"],
                "policy_sha256": anchor["policy_sha256"],
                "simulator_source_manifest_sha256": anchor[
                    "simulator_source_manifest_sha256"
                ],
                "crn_sha256": crn,
                "lineage_binding_sha256": canonical_sha256(cell),
                "state_schema": EE_AXIS_STATE_SCHEMA,
                "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
                "state_float32_hex": state_hex,
                "action_mask": mask_list,
                "state_sha256": _state_sha(state_hex, mask_list),
                "mask_sha256": _mask_sha(mask_list),
                "all_user_encoder_sha256": capture["all_user_encoder_sha256"],
                "main_reference_vector_sha256": capture[
                    "main_reference_vector_sha256"
                ],
            }
        )
    body: dict[str, Any] = {
        "schema": SIDECAR_SCHEMA,
        "source_rule": STATE_SOURCE_RULE,
        "algorithm_schema": ALGORITHM_SCHEMA,
        "state_schema": EE_AXIS_STATE_SCHEMA,
        "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        "prepare_sha256": authority["prepare_sha256"],
        "prepare_file_sha256": authority["prepare_file_sha256"],
        "prepare_seal_file_sha256": authority["prepare_seal_file_sha256"],
        "t1_prereg_file_sha256": authority["t1_prereg_file_sha256"],
        "learner_prereg_file_sha256": learner_sha,
        "capture_code_authority": dict(code),
        "lineage_authority_sha256": authority["lineage_authority_sha256"],
        "counts": {"worlds": WORLD_COUNT, "anchors": WORLD_COUNT, "actions": NUM_ACTIONS},
        "anchors": rows,
        "target_free": True,
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
    }
    result = body | {"sidecar_sha256": canonical_sha256(body)}
    verify_state_sidecar(
        result,
        authority=authority,
        learner_prereg_file_sha256=learner_sha,
        code_authority=code,
    )
    return result


def verify_state_sidecar(
    payload: Mapping[str, Any],
    *,
    authority: Mapping[str, Any],
    learner_prereg_file_sha256: str,
    code_authority: Mapping[str, Any],
    live_captures: Mapping[str, Mapping[str, Any]] | None = None,
) -> str:
    """Verify structure and, when supplied, exact independent live replay."""

    sidecar = _exact_keys(payload, _SIDECAR_FIELDS, field="state sidecar")
    unsigned = dict(sidecar)
    supplied = _digest(unsigned.pop("sidecar_sha256"), field="sidecar_sha256")
    if canonical_sha256(unsigned) != supplied:
        raise C2K1StateAuthorityError("state sidecar payload hash drifted")
    expected_scalars = {
        "schema": SIDECAR_SCHEMA,
        "source_rule": STATE_SOURCE_RULE,
        "algorithm_schema": ALGORITHM_SCHEMA,
        "state_schema": EE_AXIS_STATE_SCHEMA,
        "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        "prepare_sha256": authority["prepare_sha256"],
        "prepare_file_sha256": authority["prepare_file_sha256"],
        "prepare_seal_file_sha256": authority["prepare_seal_file_sha256"],
        "t1_prereg_file_sha256": authority["t1_prereg_file_sha256"],
        "learner_prereg_file_sha256": _digest(
            learner_prereg_file_sha256,
            field="learner_prereg_file_sha256",
        ),
        "capture_code_authority": dict(code_authority),
        "lineage_authority_sha256": authority["lineage_authority_sha256"],
        "counts": {"worlds": WORLD_COUNT, "anchors": WORLD_COUNT, "actions": NUM_ACTIONS},
        "target_free": True,
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
    }
    for field, expected in expected_scalars.items():
        if sidecar.get(field) != expected:
            raise C2K1StateAuthorityError(f"state sidecar {field} drifted")
    rows = sidecar.get("anchors")
    anchor_map = authority.get("anchor_map")
    prepare = authority.get("prepare")
    if not isinstance(rows, list) or len(rows) != WORLD_COUNT or not isinstance(anchor_map, Mapping) or not isinstance(prepare, Mapping):
        raise C2K1StateAuthorityError("state sidecar anchor coverage drifted")
    observed: list[str] = []
    for index, row_raw in enumerate(rows):
        row = _exact_keys(row_raw, _CAPTURE_FIELDS, field=f"state sidecar anchor[{index}]")
        key = row.get("anchor_key")
        if not isinstance(key, str) or key not in anchor_map:
            raise C2K1StateAuthorityError("state sidecar has unknown anchor")
        observed.append(key)
        anchor = anchor_map[key]
        for field in (
            "pool",
            "world_id",
            "step",
            "focal_user",
            "reference_action",
            "anchor_sha256",
            "world_anchor_sha256",
            "checkpoint_sha256",
            "policy_sha256",
            "simulator_source_manifest_sha256",
        ):
            if row.get(field) != anchor[field]:
                raise C2K1StateAuthorityError(f"state sidecar {key} {field} drifted")
        if row.get("state_schema") != EE_AXIS_STATE_SCHEMA or row.get("state_schema_sha256") != EE_AXIS_STATE_SCHEMA_SHA256:
            raise C2K1StateAuthorityError("state sidecar state schema drifted")
        _, state_hex = _parse_float32_hex(
            row.get("state_float32_hex"), field=f"state sidecar {key}.state"
        )
        mask = _mask(row.get("action_mask"), field=f"state sidecar {key}.mask")
        mask_list = [bool(value) for value in mask.tolist()]
        if mask_list != anchor["legal_action_mask"]:
            raise C2K1StateAuthorityError("state sidecar mask disagrees with PREPARE")
        if row.get("state_sha256") != _state_sha(state_hex, mask_list):
            raise C2K1StateAuthorityError("state sidecar state hash drifted")
        if row.get("mask_sha256") != _mask_sha(mask_list):
            raise C2K1StateAuthorityError("state sidecar mask hash drifted")
        cell = prepare["lineage_bindings"][key]
        if row.get("lineage_binding_sha256") != canonical_sha256(cell):
            raise C2K1StateAuthorityError("state sidecar lineage authority drifted")
        crn_values = {item["crn_sha256"] for item in cell.values()}
        if {row.get("crn_sha256")} != crn_values:
            raise C2K1StateAuthorityError("state sidecar CRN drifted")
        for field in ("all_user_encoder_sha256", "main_reference_vector_sha256"):
            _digest(row.get(field), field=f"state sidecar {key}.{field}")
    if observed != list(anchor_map):
        raise C2K1StateAuthorityError("state sidecar anchors are not canonical")
    if live_captures is not None:
        rebuilt = build_state_sidecar(
            authority=authority,
            learner_prereg_file_sha256=learner_prereg_file_sha256,
            code_authority=code_authority,
            captures=live_captures,
        )
        if rebuilt != dict(sidecar):
            raise C2K1StateAuthorityError(
                "independent live replay does not reproduce the state sidecar"
            )
    return supplied


def write_once_json(path: Path, payload: Mapping[str, Any]) -> None:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise C2K1StateAuthorityError(f"refusing to overwrite: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    with destination.open("xb") as stream:
        stream.write(data)


def sidecar_seal(payload: Mapping[str, Any], *, sidecar_path: Path) -> dict[str, Any]:
    return {
        "schema": SIDECAR_SEAL_SCHEMA,
        "sidecar_sha256": payload["sidecar_sha256"],
        "sidecar_file_sha256": file_sha256(sidecar_path),
        "prepare_sha256": payload["prepare_sha256"],
        "learner_prereg_file_sha256": payload["learner_prereg_file_sha256"],
        "target_free": True,
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
    }


def verify_sidecar_file_seal(
    *, sidecar: Mapping[str, Any], sidecar_path: Path, seal_path: Path
) -> str:
    expected = sidecar_seal(sidecar, sidecar_path=sidecar_path)
    actual = read_exact_json(seal_path)
    if actual != expected:
        raise C2K1StateAuthorityError("state sidecar file seal is invalid")
    return file_sha256(sidecar_path)


def live_verification_receipt(
    *,
    sidecar: Mapping[str, Any],
    sidecar_path: Path,
    sidecar_seal_path: Path,
) -> dict[str, Any]:
    body = {
        "schema": LIVE_VERIFICATION_SCHEMA,
        "sidecar_sha256": sidecar["sidecar_sha256"],
        "sidecar_file_sha256": file_sha256(sidecar_path),
        "sidecar_seal_file_sha256": file_sha256(sidecar_seal_path),
        "prepare_sha256": sidecar["prepare_sha256"],
        "learner_prereg_file_sha256": sidecar["learner_prereg_file_sha256"],
        "capture_code_authority_sha256": sidecar["capture_code_authority"]["sha256"],
        "anchors_replayed": WORLD_COUNT,
        "q13_cells_reproduced": WORLD_COUNT * 3,
        "resident_legacy_q2_consulted": False,
        "live_replay_verified": True,
        "target_free": True,
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
    }
    return body | {"verification_sha256": canonical_sha256(body)}


def live_verification_seal(
    receipt: Mapping[str, Any], *, receipt_path: Path
) -> dict[str, Any]:
    return {
        "schema": LIVE_VERIFICATION_SEAL_SCHEMA,
        "verification_sha256": receipt["verification_sha256"],
        "verification_file_sha256": file_sha256(receipt_path),
        "sidecar_sha256": receipt["sidecar_sha256"],
        "live_replay_verified": True,
        "training": False,
    }


def verify_live_verification_bundle(
    *,
    receipt_path: Path,
    seal_path: Path,
    sidecar: Mapping[str, Any],
    sidecar_path: Path,
    sidecar_seal_path: Path,
) -> str:
    """Authenticate the mandatory independent live-replay receipt and seal."""

    receipt = read_exact_json(receipt_path)
    seal = read_exact_json(seal_path)
    expected_receipt_fields = {
        "schema",
        "sidecar_sha256",
        "sidecar_file_sha256",
        "sidecar_seal_file_sha256",
        "prepare_sha256",
        "learner_prereg_file_sha256",
        "capture_code_authority_sha256",
        "anchors_replayed",
        "q13_cells_reproduced",
        "resident_legacy_q2_consulted",
        "live_replay_verified",
        "target_free",
        "training",
        "test_split_opened",
        "outcome_selection",
        "q2_consulted",
        "verification_sha256",
    }
    if set(receipt) != expected_receipt_fields:
        raise C2K1StateAuthorityError("live verification receipt schema drifted")
    body = dict(receipt)
    supplied = _digest(
        body.pop("verification_sha256"), field="live verification sha256"
    )
    if canonical_sha256(body) != supplied:
        raise C2K1StateAuthorityError("live verification receipt hash drifted")
    expected_values = {
        "schema": LIVE_VERIFICATION_SCHEMA,
        "sidecar_sha256": sidecar.get("sidecar_sha256"),
        "sidecar_file_sha256": file_sha256(sidecar_path),
        "sidecar_seal_file_sha256": file_sha256(sidecar_seal_path),
        "prepare_sha256": sidecar.get("prepare_sha256"),
        "learner_prereg_file_sha256": sidecar.get(
            "learner_prereg_file_sha256"
        ),
        "capture_code_authority_sha256": sidecar.get(
            "capture_code_authority", {}
        ).get("sha256"),
        "anchors_replayed": WORLD_COUNT,
        "q13_cells_reproduced": WORLD_COUNT * 3,
        "resident_legacy_q2_consulted": False,
        "live_replay_verified": True,
        "target_free": True,
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
    }
    for field, expected in expected_values.items():
        if receipt.get(field) != expected:
            raise C2K1StateAuthorityError(
                f"live verification receipt {field} drifted"
            )
    expected_seal = live_verification_seal(receipt, receipt_path=receipt_path)
    if seal != expected_seal:
        raise C2K1StateAuthorityError("live verification file seal is invalid")
    return supplied


__all__ = [
    "C2K1StateAuthorityError",
    "LIVE_VERIFICATION_SCHEMA",
    "PREPARE_SCHEMA",
    "SIDECAR_SCHEMA",
    "STATE_SOURCE_RULE",
    "build_state_sidecar",
    "canonical_sha256",
    "capture_code_authority",
    "file_sha256",
    "live_verification_receipt",
    "live_verification_seal",
    "read_exact_json",
    "sidecar_seal",
    "verify_formal_prepare_files",
    "verify_live_verification_bundle",
    "verify_sidecar_file_seal",
    "verify_state_sidecar",
    "write_once_json",
]
