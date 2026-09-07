#!/usr/bin/env python3
"""Independent numeric recomputation for the V0.23 LC-SRS gate.

This verifier deliberately imports neither the source/fit adapters nor any
simulator, teacher, learner, or policy implementation.  It reopens immutable
JSON/NPZ evidence with the standard library and NumPy, recomputes the LC-SRS
four-profile formula and held-out learner metrics from raw arrays, and fails
closed on provenance or arithmetic drift.  Full-roster composition is kept as
an explicit later seam because its write-once schema is owned by the W197
adapter.

Nothing in this module opens TEST, performs an optimizer update, or authorizes
episode training.  A passing world/fit result is development-gate evidence,
not an efficacy claim.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
from typing import Any, Mapping

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
R7_DECISION_PATH = HERE / "r7_balanced_successor_gate.py"
SOURCE_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1-source-shard"
FIT_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1-fit-shard"
SOURCE_ARTIFACT_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-source-artifact-v1"
SOURCE_ARTIFACT_VERSION = 1
SOURCE_ARRAY_DOMAIN = "source-array-v1"
FIT_PREDICTION_ARRAY_DOMAIN = "v023-fit-prediction-array-v1"
PROFILE_ORDER = ("00", "10", "01", "11")
TEACHER_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-two-user-teacher-v1"
DRAW_COUNT = 32
WORLDS = tuple(range(2026121801, 2026121809))
STUDENT_SEEDS = (2026135201, 2026135202, 2026135203)
FIT_ARMS = ("INFORMED", "MATCHED_PLACEBO")
LAMBDA_BITS_PER_J = float.fromhex("0x1.c3c0a7b6b86d3p+26")
KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")
SIGN_THRESHOLD = 0.02
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)
CONTRACT_SHA256 = "027e09a75a2e775b81b570cd49f6637dd10d55220d3ace2cf26a5b37ab002be5"
EXECUTION_ADDENDUM_SHA256 = "486568d017de84bfba5aa8bb65f634998446ac4b3ad471795b9055085e8f5070"
PLACEBO_KEY = "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1"
PLACEBO_KEY_SHA256 = "7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825"
FIELD_COMPONENT = "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1"
Q12_LINEAGE = 2026092101
Q12_CHECKPOINT_SHA256 = "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc"
Q12_AUTHORITY_FILE_SHA256 = "a05ee801c8f9d640b55f8ec984d874f149c30b868d1706d998f7e2053520078e"
Q12_AUTHORITY_BODY_SHA256 = "50d32dae11b2906bb23a25893f4ba5c11d0f88197ee94fe7cd216677e8703d48"
Q12_EXECUTION_CONTRACT_SHA256 = "ea36414aac87b3ef5ba48dbe753e73ff21a0e164d54cdb3edbb899b509edd48c"
Q12_REPRICING_CONTRACT_SHA256 = "34732dd3f65ffebf760313c2ffd235e0ecbd406ba6065dbce5635778550ef4a9"
Q12_FIT_RUNNER_SHA256 = "f55b882149ce49505c694423520a6a807d6a90babcbce340cb5ba449adea1814"
OPS3_FORMULA_SHA256 = "68251ff750410ff74abfb412df83bafef459831874abfcfbee6e1e04d1adea02"
OPS3_LIVE_SHA256 = "6847069235ce3789c9f2f76bfd1de9f7a4e02402788eed0fabcc0ab57faed35a"
Q2_STATE_FILE_SHA256 = "412ce464975e369e44cbb1825e02f1ce36b2ce84882bf110a63b351d63de07f7"
Q2_STATE_SCHEMA = "multi-catfish-mcrl-v014-ops3-q2-state-v1"
Q2_STATE_SCHEMA_SHA256 = "440f98a87b8a91be647e28a15a2509853f8566864a2be560b8602421185efc50"
Q2_STATE_DIM = 448
Q2_FEATURE_DIM = 16
OPS3_HORIZON = 3
OPS3_INTERVAL_S = float.fromhex("0x1.e147ae147ae15p+4")
OPS3_RUNTIME_DEFAULT_LAMBDA_HEX = "0x1.443a8f481639ap+26"
WORLD_PHASES = tuple(range(1, 10))
USER_COUNT = 100
ACTION_COUNT = 28
C3_VIEW_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-c3-view-v1"
C3_VIEW_SCHEMA_VERSION = 1
C3_VIEW_SCHEMA_SHA256 = "c1c455c7207048c29b3b58218a59dd67852ec8d2077c417181f1f7e07300cbe6"
C3_VIEW_CONFIG_SHA256 = "c406a6a2a0da78a855c8f850c45803cfa1763a3e7e40823693b39207f14c3324"


class V023ScientificVerificationError(RuntimeError):
    """Raw V0.23 evidence is missing, malformed, or numerically inconsistent."""


def _load_r7_decision() -> Any:
    target = R7_DECISION_PATH
    if target.is_symlink() or not target.is_file():
        raise V023ScientificVerificationError("R7 balanced decision module is missing")
    name = "v023_scientific_r7_balanced_decision"
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise V023ScientificVerificationError("R7 balanced decision module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise V023ScientificVerificationError(
            "R7 balanced decision module import failed"
        ) from error
    return module


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023ScientificVerificationError("value is not canonical finite JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023ScientificVerificationError(f"expected regular file: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path, *, field: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023ScientificVerificationError(f"{field} is missing or is a symlink")
    raw = target.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023ScientificVerificationError(f"{field} is not ASCII JSON") from error
    if not isinstance(value, dict):
        raise V023ScientificVerificationError(f"{field} root is not an object")
    canonical = _canonical_bytes(value)
    if raw not in (canonical, canonical + b"\n"):
        raise V023ScientificVerificationError(f"{field} is not canonical JSON")
    return value


def _mapping(value: object, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise V023ScientificVerificationError(f"{field} is not an object")
    return value


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023ScientificVerificationError(f"{field} is not lowercase SHA-256")
    return value


def _safe_child(root: Path, relative: object, *, field: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise V023ScientificVerificationError(f"{field} is not a safe relative path")
    base = Path(root).resolve()
    child = (base / relative).resolve()
    if not child.is_relative_to(base):
        raise V023ScientificVerificationError(f"{field} escapes its artifact directory")
    if child.is_symlink():
        raise V023ScientificVerificationError(f"{field} may not be a symlink")
    return child


def _safe_repo_child(relative: object, *, field: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise V023ScientificVerificationError(f"{field} is not a repository-relative path")
    child = (REPO / relative).resolve()
    if not child.is_relative_to(REPO.resolve()) or child.is_symlink():
        raise V023ScientificVerificationError(f"{field} escapes the repository or is a symlink")
    return child


def _load_relaxed_json(path: Path, *, field: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023ScientificVerificationError(f"{field} is missing or is a symlink")
    try:
        value = json.loads(target.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023ScientificVerificationError(f"{field} is not readable ASCII JSON") from error
    if not isinstance(value, dict):
        raise V023ScientificVerificationError(f"{field} root is not an object")
    return value


def _verify_q12_authority_binding(background: Mapping[str, Any]) -> None:
    binding = _mapping(background.get("q12_authority"), field="q12_authority")
    expected_scalars = {
        "schema": "multi-catfish-mcrl-v023-q12-authority-binding-v1",
        "authority_file_sha256": Q12_AUTHORITY_FILE_SHA256,
        "authority_body_sha256": Q12_AUTHORITY_BODY_SHA256,
        "execution_contract_sha256": Q12_EXECUTION_CONTRACT_SHA256,
        "repricing_contract_sha256": Q12_REPRICING_CONTRACT_SHA256,
        "fit_runner_sha256": Q12_FIT_RUNNER_SHA256,
        "checkpoint_sha256": Q12_CHECKPOINT_SHA256,
        "ops3_formula_sha256": OPS3_FORMULA_SHA256,
        "ops3_live_sha256": OPS3_LIVE_SHA256,
        "q2_state_file_sha256": Q2_STATE_FILE_SHA256,
        "lambda_bits_per_j_hex": LAMBDA_BITS_PER_J.hex(),
        "ops3_runtime_default_lambda_hex": OPS3_RUNTIME_DEFAULT_LAMBDA_HEX,
        "ops3_runtime_default_used_for_diagnostic_target": False,
        "ops3_horizon": OPS3_HORIZON,
        "ops3_interval_s_hex": float(OPS3_INTERVAL_S).hex(),
        "q2_state_schema": Q2_STATE_SCHEMA,
        "q2_state_schema_sha256": Q2_STATE_SCHEMA_SHA256,
        "q2_state_dim": Q2_STATE_DIM,
        "target_free_inference": True,
        "q2_target_file_count": 7,
    }
    for field, expected in expected_scalars.items():
        if binding.get(field) != expected:
            raise V023ScientificVerificationError(f"Q1/Q2 authority binding {field} drifted")
    path_hashes = (
        ("authority_path", "authority_file_sha256"),
        ("execution_contract_path", "execution_contract_sha256"),
        ("repricing_contract_path", "repricing_contract_sha256"),
        ("fit_runner_path", "fit_runner_sha256"),
        ("checkpoint_path", "checkpoint_sha256"),
        ("ops3_formula_path", "ops3_formula_sha256"),
        ("ops3_live_path", "ops3_live_sha256"),
        ("q2_state_path", "q2_state_file_sha256"),
    )
    resolved: dict[str, Path] = {}
    for path_field, hash_field in path_hashes:
        path = _safe_repo_child(binding.get(path_field), field=path_field)
        if file_sha256(path) != binding.get(hash_field):
            raise V023ScientificVerificationError(f"Q1/Q2 authority {path_field} bytes changed")
        resolved[path_field] = path

    authority = _load_relaxed_json(resolved["authority_path"], field="Q1/Q2 authority")
    if authority.get("authority_sha256") != Q12_AUTHORITY_BODY_SHA256:
        raise V023ScientificVerificationError("Q1/Q2 authority seal drifted")
    unsigned = dict(authority)
    unsigned.pop("authority_sha256", None)
    if canonical_sha256(unsigned) != Q12_AUTHORITY_BODY_SHA256:
        raise V023ScientificVerificationError("Q1/Q2 authority body does not authenticate")
    if (
        authority.get("schema")
        != "multi-catfish-mcrl-v020-repriced-q1-q2-source-fit-v1-authority"
        or authority.get("contract_sha256") != Q12_EXECUTION_CONTRACT_SHA256
        or authority.get("repricing_contract_sha256") != Q12_REPRICING_CONTRACT_SHA256
        or authority.get("lambda_bits_per_j_hex") != LAMBDA_BITS_PER_J.hex()
        or authority.get("lineage") != Q12_LINEAGE
        or authority.get("q1_updates") != 10
        or authority.get("q2_initialization") != 2026108101
        or authority.get("q2_rungs") != [3, 10, 30, 100, 300, 1000, 3000]
        or authority.get("test_split_opened") is not False
        or authority.get("simulator_run") is not False
        or authority.get("episode_training") is not False
    ):
        raise V023ScientificVerificationError("Q1/Q2 authority semantics drifted")
    code_hashes = _mapping(authority.get("code_file_sha256s"), field="Q1/Q2 code hashes")
    target_hashes = _mapping(
        authority.get("q2_repriced_target_file_sha256s"), field="Q2 target hashes"
    )
    if len(target_hashes) != 7 or canonical_sha256(dict(target_hashes)) != binding.get(
        "q2_target_files_sha256"
    ):
        raise V023ScientificVerificationError("Q2 target-file panel binding drifted")
    for label, entries in (("code", code_hashes), ("target", target_hashes)):
        for relative, digest in entries.items():
            path = _safe_repo_child(relative, field=f"Q1/Q2 {label} path")
            expected = _digest(digest, field=f"Q1/Q2 {label} SHA-256")
            if file_sha256(path) != expected:
                raise V023ScientificVerificationError(f"Q1/Q2 {label} bytes changed")
    if binding.get("source_sha256") != authority.get("source_sha256"):
        raise V023ScientificVerificationError("Q1/Q2 source digest binding drifted")

    q1_receipt = _mapping(background.get("q1_receipt"), field="Q1 receipt")
    q2_receipt = _mapping(background.get("q2_receipt"), field="Q2 receipt")
    if (
        q1_receipt.get("update_count") != 10
        or q2_receipt.get("update_count") != 3000
        or q1_receipt.get("train_seed") != Q12_LINEAGE
        or q2_receipt.get("train_seed") != 2026108101
        or q1_receipt.get("checkpoint_sha256") != Q12_CHECKPOINT_SHA256
        or q2_receipt.get("checkpoint_sha256") != Q12_CHECKPOINT_SHA256
        or q1_receipt.get("config") != authority.get("q1_config")
        or q2_receipt.get("config") != authority.get("q2_config")
    ):
        raise V023ScientificVerificationError("Q1/Q2 receipt-to-authority binding drifted")


def _array_digest(value: np.ndarray, *, domain: str) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(domain.encode("ascii"))
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _verify_receipt_seal(payload: Mapping[str, Any]) -> None:
    declared = _digest(payload.get("receipt_sha256"), field="receipt_sha256")
    unsigned = dict(payload)
    unsigned.pop("receipt_sha256", None)
    if canonical_sha256(unsigned) != declared:
        raise V023ScientificVerificationError("receipt seal disagrees with body")


def _verify_source_authority(payload: Mapping[str, Any]) -> str:
    """Authenticate immutable source identities without importing production code."""

    if payload.get("contract_sha256") != CONTRACT_SHA256:
        raise V023ScientificVerificationError("source contract digest drifted")
    preflight = _digest(
        payload.get("preflight_manifest_sha256"),
        field="preflight_manifest_sha256",
    )
    if payload.get("execution_addendum_sha256") != EXECUTION_ADDENDUM_SHA256:
        raise V023ScientificVerificationError("source execution addendum drifted")
    if (
        payload.get("placebo_key") != PLACEBO_KEY
        or payload.get("placebo_key_sha256") != PLACEBO_KEY_SHA256
    ):
        raise V023ScientificVerificationError("source placebo key drifted")
    if (
        payload.get("source_artifact_schema") != SOURCE_ARTIFACT_SCHEMA
        or payload.get("source_artifact_version") != SOURCE_ARTIFACT_VERSION
    ):
        raise V023ScientificVerificationError("source artifact schema/version drifted")
    world = payload.get("world")
    if type(world) is not int or world not in WORLDS:
        raise V023ScientificVerificationError("source world is outside the frozen panel")

    background = _mapping(payload.get("q12_background"), field="q12_background")
    if background.get("lineage") != Q12_LINEAGE:
        raise V023ScientificVerificationError("Q1/Q2 lineage drifted")
    for field in ("checkpoint_sha256", "q1_checkpoint_sha256", "q2_checkpoint_sha256"):
        if background.get(field) != Q12_CHECKPOINT_SHA256:
            raise V023ScientificVerificationError(f"{field} drifted")
    q1_parameter = _digest(
        background.get("q1_parameter_sha256"), field="q1_parameter_sha256"
    )
    q2_parameter = _digest(
        background.get("q2_parameter_sha256"), field="q2_parameter_sha256"
    )
    _digest(background.get("q12_model_sha256"), field="q12_model_sha256")
    if background.get("q12_unit") != "authenticated-normalized-q1-plus-q2-float32":
        raise V023ScientificVerificationError("Q1/Q2 output unit drifted")
    if background.get("state_schema") != "native-ee-axis-state-v1":
        raise V023ScientificVerificationError("Q1/Q2 state schema drifted")
    _verify_q12_authority_binding(background)

    world_receipt = _mapping(payload.get("world_receipt"), field="world_receipt")
    if (
        world_receipt.get("world") != world
        or world_receipt.get("field_component") != FIELD_COMPONENT
        or world_receipt.get("phase_count") != len(WORLD_PHASES)
        or world_receipt.get("test_split_opened") is not False
        or world_receipt.get("learner_update") is not False
        or world_receipt.get("episode_training") is not False
    ):
        raise V023ScientificVerificationError("world receipt boundary drifted")
    if (
        world_receipt.get("q1_parameter_sha256") != q1_parameter
        or world_receipt.get("q1_parameter_sha256_after") != q1_parameter
        or world_receipt.get("q2_parameter_sha256") != q2_parameter
        or world_receipt.get("q2_parameter_sha256_after") != q2_parameter
        or payload.get("c1_c2_parameter_unchanged") is not True
    ):
        raise V023ScientificVerificationError("Q1/Q2 mutation guard failed")
    for field in (
        "field_root_digest",
        "environment_initial_digest",
        "environment_final_digest",
        "rng_initial_digest",
        "rng_final_digest",
    ):
        _digest(world_receipt.get(field), field=f"world_receipt.{field}")
    anchor_ids = world_receipt.get("anchor_ids")
    if not isinstance(anchor_ids, list) or len(anchor_ids) != len(WORLD_PHASES):
        raise V023ScientificVerificationError("world receipt anchor schedule drifted")

    field_manifest = _mapping(payload.get("field_manifest"), field="field_manifest")
    if (
        field_manifest.get("family") != FIELD_COMPONENT
        or field_manifest.get("key_axes")
        != ["family", "world", "anchor", "draw", "event", "step_index", "norad_id"]
        or field_manifest.get("root_excludes") != ["pair", "profile"]
        or field_manifest.get("profile_order") != list(PROFILE_ORDER)
        or field_manifest.get("world_rollout_root_digest")
        != world_receipt.get("field_root_digest")
    ):
        raise V023ScientificVerificationError("keyed-field manifest drifted")
    if field_manifest.get("draw_root_rule") != (
        "KeyedFadingField.from_components(family, world, anchor_id, draw_index)"
    ):
        raise V023ScientificVerificationError("keyed-field draw rule drifted")

    ephemeris = _mapping(payload.get("ephemeris_validation"), field="ephemeris_validation")
    if ephemeris.get("file_set_sha256") != (
        "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
    ):
        raise V023ScientificVerificationError("ephemeris file set drifted")

    placebo = _mapping(payload.get("placebo_strata"), field="placebo_strata")
    if (
        placebo.get("placebo_key") != PLACEBO_KEY
        or placebo.get("placebo_key_sha256") != PLACEBO_KEY_SHA256
        or placebo.get("supported_count") != payload.get("supported_count")
        or placebo.get("placebo_eligible_count") != payload.get("placebo_eligible_count")
    ):
        raise V023ScientificVerificationError("source placebo receipt drifted")
    supported = payload.get("supported_count")
    if type(supported) is not int or supported < 0:
        raise V023ScientificVerificationError("source supported count is malformed")
    if supported > 0:
        _digest(placebo.get("content_digest"), field="placebo content digest")
    elif "content_digest" in placebo:
        raise V023ScientificVerificationError("empty placebo receipt unexpectedly has a digest")
    return preflight


def _verify_digest_file(path: Path, *, digest: str, target_name: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise V023ScientificVerificationError("NPZ digest sidecar is missing")
    expected = f"{digest}  {target_name}\n".encode("ascii")
    if path.read_bytes() != expected:
        raise V023ScientificVerificationError("NPZ digest sidecar disagrees")


def _load_npz(
    *,
    index_path: Path,
    binding: Mapping[str, Any],
    domain: str,
) -> dict[str, np.ndarray]:
    if binding.get("allow_pickle") is not False:
        raise V023ScientificVerificationError("NPZ binding does not forbid pickle")
    root = Path(index_path).parent.resolve()
    path = _safe_child(root, binding.get("npz_relative_path"), field="NPZ path")
    digest = _digest(binding.get("npz_sha256"), field="NPZ SHA-256")
    if file_sha256(path) != digest:
        raise V023ScientificVerificationError("NPZ byte hash disagrees")
    digest_path = _safe_child(
        root, binding.get("npz_sha256_file"), field="NPZ digest path"
    )
    _verify_digest_file(digest_path, digest=digest, target_name=path.name)
    metadata = _mapping(binding.get("array_metadata"), field="array metadata")
    try:
        with np.load(path, allow_pickle=False) as archive:
            arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    except (OSError, ValueError, KeyError) as error:
        raise V023ScientificVerificationError("NPZ cannot be loaded safely") from error
    if set(arrays) != set(metadata):
        raise V023ScientificVerificationError("NPZ keys disagree with metadata")
    for name, array in arrays.items():
        if array.dtype == object or not array.flags.c_contiguous:
            raise V023ScientificVerificationError(f"array {name} has unsafe dtype/order")
        entry = _mapping(metadata[name], field=f"metadata[{name}]")
        if entry.get("dtype") != array.dtype.str or entry.get("shape") != list(array.shape):
            raise V023ScientificVerificationError(f"array {name} shape/dtype drifted")
        if entry.get("sha256") != _array_digest(array, domain=domain):
            raise V023ScientificVerificationError(f"array {name} content digest drifted")
    return arrays


def comparison_tolerance(*values: float) -> float:
    converted = tuple(float(value) for value in values)
    if not converted or not all(math.isfinite(value) for value in converted):
        raise V023ScientificVerificationError("comparison inputs must be finite")
    return max(
        1.0e-12,
        1024.0
        * np.finfo(np.float64).eps
        * max(1.0, *(abs(value) for value in converted)),
    )


def strict_direction(left: float, right: float) -> int:
    tolerance = comparison_tolerance(left, right)
    delta = float(left) - float(right)
    return 1 if delta > tolerance else -1 if delta < -tolerance else 0


def action_sha256(actions: np.ndarray) -> str:
    values = np.ascontiguousarray(np.asarray(actions, dtype=np.int64))
    if values.ndim != 1 or values.size < 2:
        raise V023ScientificVerificationError("action vector is malformed")
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-profile-actions-v1")
    digest.update(struct.pack(">I", int(values.size)))
    digest.update(values.tobytes(order="C"))
    return digest.hexdigest()


def _digest_named_array(digest: Any, name: str, value: np.ndarray) -> None:
    array = np.ascontiguousarray(value)
    digest.update(name.encode("ascii"))
    digest.update(b"\0")
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))


def c3_view_sha256(
    action_context: np.ndarray,
    tokens: np.ndarray,
    token_mask: np.ndarray,
    action_mask: np.ndarray,
    reference_actions: np.ndarray,
) -> str:
    """Independently reproduce the frozen Interface-A content digest."""

    digest = hashlib.sha256()
    digest.update(C3_VIEW_SCHEMA.encode("ascii"))
    digest.update(struct.pack(">I", C3_VIEW_SCHEMA_VERSION))
    digest.update(C3_VIEW_SCHEMA_SHA256.encode("ascii"))
    digest.update(C3_VIEW_CONFIG_SHA256.encode("ascii"))
    for name, value in (
        ("action_context", action_context),
        ("tokens", tokens),
        ("token_mask", token_mask),
        ("action_mask", action_mask),
        ("reference_actions", reference_actions),
    ):
        _digest_named_array(digest, name, value)
    return digest.hexdigest()


def _assert_numeric_equal(actual: object, expected: object, *, field: str) -> None:
    left = np.asarray(actual, dtype=np.float64)
    right = np.asarray(expected, dtype=np.float64)
    if left.shape != right.shape or not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        raise V023ScientificVerificationError(f"{field} has malformed numeric shape/value")
    scale = max(1.0, float(np.max(np.abs(left), initial=0.0)), float(np.max(np.abs(right), initial=0.0)))
    tolerance = max(1.0e-12, 1024.0 * np.finfo(np.float64).eps * scale)
    if not np.all(np.abs(left - right) <= tolerance):
        raise V023ScientificVerificationError(f"{field} disagrees with raw recomputation")


def _decode_ascii(value: object, *, field: str) -> str:
    raw = np.asarray(value).item()
    if not isinstance(raw, (bytes, np.bytes_)):
        raise V023ScientificVerificationError(f"{field} is not fixed ASCII bytes")
    try:
        return bytes(raw).rstrip(b"\x00").decode("ascii")
    except UnicodeDecodeError as error:
        raise V023ScientificVerificationError(f"{field} is not ASCII") from error


def _active_set(keys: np.ndarray, count: int, *, field: str) -> set[tuple[int, int]]:
    if type(count) is not int or not 0 <= count <= keys.shape[0]:
        raise V023ScientificVerificationError(f"{field} count is invalid")
    active = np.asarray(keys[:count], dtype=np.int64)
    if active.shape != (count, 2):
        raise V023ScientificVerificationError(f"{field} keys are malformed")
    result = {tuple(int(item) for item in row) for row in active.tolist()}
    if len(result) != count:
        raise V023ScientificVerificationError(f"{field} repeats a beam key")
    return result


def _midranks(values: np.ndarray) -> np.ndarray:
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise V023ScientificVerificationError("rank input must be one finite vector")
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1) + 1.0
        start = end
    return ranks


def tie_aware_spearman(left: np.ndarray, right: np.ndarray) -> float | None:
    first = np.asarray(left, dtype=np.float64)
    second = np.asarray(right, dtype=np.float64)
    if first.ndim != 1 or second.shape != first.shape:
        raise V023ScientificVerificationError("Spearman inputs are not aligned")
    if first.size < 2 or not np.all(np.isfinite(first)) or not np.all(np.isfinite(second)):
        return None
    a = _midranks(first)
    b = _midranks(second)
    a -= float(np.mean(a))
    b -= float(np.mean(b))
    denominator = math.sqrt(float(np.dot(a, a)) * float(np.dot(b, b)))
    if denominator == 0.0 or not math.isfinite(denominator):
        return None
    value = float(np.dot(a, b) / denominator)
    return value if math.isfinite(value) else None


def sign_receipt(prediction: np.ndarray, target: np.ndarray) -> dict[str, Any]:
    """Recompute the copied raw sign receipt used by source/C1 checks."""

    predicted = np.asarray(prediction, dtype=np.float64)
    truth = np.asarray(target, dtype=np.float64)
    if predicted.ndim != 1 or truth.shape != predicted.shape:
        raise V023ScientificVerificationError("sign inputs are not aligned")
    if not np.all(np.isfinite(predicted)) or not np.all(np.isfinite(truth)):
        raise V023ScientificVerificationError("sign inputs are nonfinite")
    eligible = np.abs(truth) >= SIGN_THRESHOLD
    count = int(np.count_nonzero(eligible))
    correct = int(np.count_nonzero(np.sign(predicted[eligible]) == np.sign(truth[eligible])))
    return {
        "threshold": SIGN_THRESHOLD,
        "total_rows": int(truth.size),
        "evaluated_rows": count,
        "excluded_rows": int(truth.size - count),
        "correct_rows": correct,
        "accuracy": None if count == 0 else correct / count,
    }


def r7_fit_sign_receipt(prediction: np.ndarray, target: np.ndarray) -> dict[str, Any]:
    """Serialize raw sign counts plus the R7 class-balanced fit fields.

    The raw fields remain evidence only.  The final R7 panel independently
    recomputes and decides on the class-balanced fields from prediction and
    target arrays.
    """

    predicted = np.asarray(prediction, dtype=np.float64)
    truth = np.asarray(target, dtype=np.float64)
    receipt = sign_receipt(predicted, truth)
    eligible = np.abs(truth) >= SIGN_THRESHOLD
    positive = eligible & (truth > 0.0)
    negative = eligible & (truth < 0.0)
    positive_denominator = int(np.count_nonzero(positive))
    negative_denominator = int(np.count_nonzero(negative))
    correct_positive = int(np.count_nonzero(positive & (predicted > 0.0)))
    correct_negative = int(np.count_nonzero(negative & (predicted < 0.0)))
    positive_recall = None if positive_denominator == 0 else correct_positive / positive_denominator
    negative_recall = None if negative_denominator == 0 else correct_negative / negative_denominator
    receipt.update({
        "raw_correct_rows": receipt["correct_rows"],
        "raw_sign_accuracy": receipt["accuracy"],
        "positive_denominator": positive_denominator,
        "negative_denominator": negative_denominator,
        "correct_positive": correct_positive,
        "correct_negative": correct_negative,
        "positive_recall": positive_recall,
        "negative_recall": negative_recall,
        "balanced_accuracy": None
        if positive_recall is None or negative_recall is None
        else (positive_recall + negative_recall) / 2.0,
        "decision_role": "RAW_SERIALIZED_BALANCED_AGGREGATED_AT_FINAL_R7",
    })
    return receipt


def _masked_argmax_rows(values: np.ndarray, masks: np.ndarray, *, field: str) -> np.ndarray:
    scores = np.asarray(values, dtype=np.float64)
    legal = np.asarray(masks)
    if (
        scores.ndim != 2
        or scores.shape[1] != ACTION_COUNT
        or legal.dtype != np.bool_
        or legal.shape != scores.shape
        or not np.all(np.isfinite(scores))
        or not np.all(np.any(legal, axis=1))
    ):
        raise V023ScientificVerificationError(f"{field} is not a selectable masked surface")
    return np.argmax(np.where(legal, scores, -np.inf), axis=1).astype(np.int64)


def _q2_state_sha256(states: np.ndarray, masks: np.ndarray) -> str:
    """Reproduce the target-free V0.14 Q2 carrier digest independently."""

    state = np.asarray(states, dtype=np.float32)
    legal = np.asarray(masks)
    if (
        state.ndim != 2
        or state.shape[1] != Q2_STATE_DIM
        or legal.dtype != np.bool_
        or legal.shape != (state.shape[0], ACTION_COUNT)
        or not np.all(np.isfinite(state))
    ):
        raise V023ScientificVerificationError("Q2 state digest input is malformed")
    payload = {
        "schema_sha256": Q2_STATE_SCHEMA_SHA256,
        "state_float32_hex": [float(value).hex() for value in state.ravel()],
        "masks": legal.astype(np.uint8).tolist(),
    }
    return canonical_sha256(payload)


def _transition_class(
    physical_keys: np.ndarray, *, user: int, reference: int, candidate: int
) -> str:
    reference_key = tuple(int(value) for value in physical_keys[user, reference])
    candidate_key = tuple(int(value) for value in physical_keys[user, candidate])
    if reference_key == candidate_key:
        return "SAME_PHYSICAL_LINK"
    if reference_key[0] == candidate_key[0]:
        return "INTRA_SATELLITE_BEAM_MOVE"
    return "INTER_SATELLITE_MOVE"


def _parse_utc_sequence(value: object, *, field: str) -> tuple[dt.datetime, ...]:
    if not isinstance(value, list):
        raise V023ScientificVerificationError(f"{field} is not a timestamp list")
    result: list[dt.datetime] = []
    for item in value:
        if not isinstance(item, str):
            raise V023ScientificVerificationError(f"{field} contains a non-string timestamp")
        try:
            parsed = dt.datetime.fromisoformat(item)
        except ValueError as error:
            raise V023ScientificVerificationError(f"{field} contains invalid ISO time") from error
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise V023ScientificVerificationError(f"{field} timestamp is not timezone-aware")
        result.append(parsed)
    return tuple(result)


def _verify_q2_context(
    *,
    payload: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
    pair_anchor: np.ndarray,
    pair_users: np.ndarray,
    pair_actions: np.ndarray,
    pair_retained: np.ndarray,
) -> dict[str, Any]:
    """Authenticate the fixed learned-Q2 carrier and its repriced OPS-3 diagnostic."""

    phases = np.asarray(arrays["anchor_phase"])
    masks = np.asarray(arrays["action_mask"])
    opening = np.asarray(arrays["opening_feasibility"])
    physical_keys = np.asarray(arrays["physical_keys"])
    q1 = np.asarray(arrays["q1_values"])
    q2 = np.asarray(arrays["q2_values"])
    q12 = np.asarray(arrays["q12_values"])
    state = np.asarray(arrays["q2_state_matrix"])
    feature = np.asarray(arrays["q2_feature_surface"])
    teacher = np.asarray(arrays["q2_teacher_values"])
    persistence = np.asarray(arrays["q2_persistence"])
    rate = np.asarray(arrays["q2_rate_bps"])
    power = np.asarray(arrays["q2_marginal_power_w"])
    required = np.asarray(arrays["q2_required_power_w"])
    horizon = np.asarray(arrays["q2_horizon"])
    anchors = payload.get("anchors")

    anchor_count = int(phases.size)
    if (
        phases.dtype.kind not in "iu"
        or phases.shape != (anchor_count,)
        or not np.array_equal(phases.astype(np.int64), np.asarray(WORLD_PHASES, dtype=np.int64))
        or masks.dtype != np.bool_
        or masks.shape != (anchor_count, USER_COUNT, ACTION_COUNT)
        or opening.dtype != np.bool_
        or opening.shape != masks.shape
        or physical_keys.shape != (anchor_count, USER_COUNT, ACTION_COUNT, 2)
        or q1.shape != masks.shape
        or q2.shape != masks.shape
        or q12.shape != masks.shape
        or state.dtype != np.float32
        or state.shape != (anchor_count, USER_COUNT, Q2_STATE_DIM)
        or feature.shape != (anchor_count, USER_COUNT, ACTION_COUNT, Q2_FEATURE_DIM)
        or teacher.shape != masks.shape
        or persistence.shape != (anchor_count, USER_COUNT, OPS3_HORIZON, ACTION_COUNT)
        or rate.shape != persistence.shape
        or power.shape != persistence.shape
        or required.shape != persistence.shape
        or horizon.dtype.kind not in "iu"
        or horizon.shape != (anchor_count,)
        or not isinstance(anchors, list)
        or len(anchors) != anchor_count
    ):
        raise V023ScientificVerificationError("Q2 context shape/dtype/schedule drifted")
    numeric = (q1, q2, q12, state, feature, teacher, persistence, rate, power, required)
    if any(not np.all(np.isfinite(value)) for value in numeric):
        raise V023ScientificVerificationError("Q2 context contains a non-finite value")
    if not np.array_equal(
        q12.astype(np.float32),
        (q1.astype(np.float32) + q2.astype(np.float32)).astype(np.float32),
    ):
        raise V023ScientificVerificationError("Q1+Q2 float32 carrier identity drifted")
    if not np.all(np.any(masks, axis=2)) or np.any(opening & ~masks):
        raise V023ScientificVerificationError("Q2 legal/opening masks are invalid")
    if np.any((persistence != 0.0) & (persistence != 1.0)):
        raise V023ScientificVerificationError("Q2 persistence is not binary")
    if np.any(np.diff(persistence, axis=2) > 0.0):
        raise V023ScientificVerificationError("Q2 persistence is not absorbing")
    if np.any(rate < 0.0) or np.any(power < 0.0) or np.any(required < 0.0):
        raise V023ScientificVerificationError("Q2 projected physics is negative")

    reconstructed_state = feature.astype(np.float32).transpose(0, 1, 3, 2).reshape(
        anchor_count, USER_COUNT, Q2_STATE_DIM
    )
    if not np.array_equal(state, reconstructed_state):
        raise V023ScientificVerificationError("Q2 carrier is not exactly target-free OPS-3 features")

    q1_reference = np.stack(
        [_masked_argmax_rows(q1[index], masks[index], field="Q1") for index in range(anchor_count)]
    )
    q12_reference = np.stack(
        [_masked_argmax_rows(q12[index], masks[index], field="Q1+Q2") for index in range(anchor_count)]
    )
    expected_horizon = np.asarray(
        [min(OPS3_HORIZON, max(0, 9 - int(phase))) for phase in phases], dtype=np.int64
    )
    if not np.array_equal(horizon.astype(np.int64), expected_horizon):
        raise V023ScientificVerificationError("Q2 OPS-3 horizon schedule drifted")

    expected_teacher = np.zeros_like(teacher, dtype=np.float64)
    for anchor_index in range(anchor_count):
        h = int(horizon[anchor_index])
        illegal = ~masks[anchor_index]
        if (
            np.any(feature[anchor_index][illegal] != 0.0)
            or np.any(teacher[anchor_index][illegal] != 0.0)
            or any(
                np.any(np.where(illegal[:, None, :], value[anchor_index], 0.0) != 0.0)
                for value in (persistence, rate, power, required)
            )
        ):
            raise V023ScientificVerificationError("Q2 illegal rows are not zero-filled")
        if h < OPS3_HORIZON and (
            np.any(persistence[anchor_index, :, h:] != 0.0)
            or np.any(rate[anchor_index, :, h:] != 0.0)
            or np.any(power[anchor_index, :, h:] != 0.0)
            or np.any(required[anchor_index, :, h:] != 0.0)
        ):
            raise V023ScientificVerificationError("Q2 projection leaks beyond its horizon")
        if h == 0:
            if np.any(feature[anchor_index] != 0.0) or np.any(teacher[anchor_index] != 0.0):
                raise V023ScientificVerificationError("terminal Q2 feature/teacher surface is not zero")
            continue
        for offset in range(OPS3_HORIZON):
            valid_feature = feature[anchor_index, :, :, 4 + 4 * offset]
            persistence_feature = feature[anchor_index, :, :, 5 + 4 * offset]
            expected_valid = (
                masks[anchor_index].astype(np.float64)
                if offset < h
                else np.zeros_like(valid_feature)
            )
            expected_persistence = (
                persistence[anchor_index, :, offset]
                if offset < h
                else np.zeros_like(persistence_feature)
            )
            _assert_numeric_equal(
                valid_feature, expected_valid, field="Q2 valid-horizon feature"
            )
            _assert_numeric_equal(
                persistence_feature,
                expected_persistence,
                field="Q2 persistence feature",
            )
        if np.any(persistence[anchor_index, :, 0, :] > opening[anchor_index]):
            raise V023ScientificVerificationError("Q2 persistence bypasses opening feasibility")
        terms = (
            persistence[anchor_index, :, :h]
            * OPS3_INTERVAL_S
            * (rate[anchor_index, :, :h] - LAMBDA_BITS_PER_J * power[anchor_index, :, :h])
            - (1.0 - persistence[anchor_index, :, :h]) * KAPPA_BITS
        )
        raw = np.mean(terms, axis=1, dtype=np.float64)
        centered = raw - raw[np.arange(USER_COUNT), q1_reference[anchor_index]][:, None]
        normalized = centered / KAPPA_BITS
        expected_teacher[anchor_index] = np.where(masks[anchor_index], normalized, 0.0)
        if np.any(expected_teacher[anchor_index, np.arange(USER_COUNT), q1_reference[anchor_index]] != 0.0):
            raise V023ScientificVerificationError("Q2 diagnostic reference is not exact zero")
    _assert_numeric_equal(teacher, expected_teacher, field="repriced OPS-3 target")

    for anchor_index, entry_value in enumerate(anchors):
        entry = _mapping(entry_value, field=f"anchors[{anchor_index}]")
        context = _mapping(entry.get("q2_context"), field=f"anchors[{anchor_index}].q2_context")
        expected_scalars = {
            "schema": "multi-catfish-mcrl-v023-q2-context-v1",
            "q2_state_schema": Q2_STATE_SCHEMA,
            "q2_state_schema_sha256": Q2_STATE_SCHEMA_SHA256,
            "horizon": int(horizon[anchor_index]),
            "q1_to_q12_argmax_change_count": int(
                np.count_nonzero(q1_reference[anchor_index] != q12_reference[anchor_index])
            ),
            "served_user_count": int(np.count_nonzero(q12_reference[anchor_index] >= 0)),
            "target_free_inference": True,
            "absorbing_persistence_checked": True,
            "terminal_zero_checked": True,
            "opening_mask_checked": True,
            "frozen_background_formula_checked": True,
            "diagnostic_lambda_bits_per_j_hex": LAMBDA_BITS_PER_J.hex(),
            "ops3_runtime_default_lambda_hex": OPS3_RUNTIME_DEFAULT_LAMBDA_HEX,
            "runtime_default_lambda_used_for_target": False,
        }
        for name, expected in expected_scalars.items():
            if context.get(name) != expected:
                raise V023ScientificVerificationError(f"Q2 anchor receipt {name} drifted")
        for name in ("ops3_anchor_sha256", "ops3_tracker_seed_sha256", "ops3_projection_sha256"):
            _digest(context.get(name), field=f"Q2 anchor {name}")
        digest_checks = {
            "q2_state_sha256": _q2_state_sha256(state[anchor_index], masks[anchor_index]),
            "q1_reference_actions_sha256": _array_digest(
                q1_reference[anchor_index], domain="v023-q1-reference-actions"
            ),
            "q12_reference_actions_sha256": _array_digest(
                q12_reference[anchor_index], domain="v023-reference-actions"
            ),
            "target_values_sha256": _array_digest(
                teacher[anchor_index], domain="v023-repriced-ops3-target-values"
            ),
            "feature_surface_sha256": _array_digest(
                feature[anchor_index], domain="v023-ops3-feature-surface"
            ),
            "persistence_sha256": _array_digest(
                persistence[anchor_index], domain="v023-ops3-persistence"
            ),
        }
        for name, expected in digest_checks.items():
            if context.get(name) != expected:
                raise V023ScientificVerificationError(f"Q2 anchor receipt {name} disagrees")

        h = int(horizon[anchor_index])
        indices = context.get("future_d2_indices")
        if not isinstance(indices, list) or any(type(value) is not int for value in indices):
            raise V023ScientificVerificationError("Q2 future D2 indices are malformed")
        expected_indices = list(
            range((int(phases[anchor_index]) + 1) * 47, (int(phases[anchor_index]) + 1 + h) * 47)
        )
        if indices != expected_indices:
            raise V023ScientificVerificationError("Q2 future D2 index schedule drifted")
        sample_times = _parse_utc_sequence(
            context.get("sample_times_utc"), field="Q2 sample_times_utc"
        )
        offset_times = _parse_utc_sequence(
            context.get("offset_times_utc"), field="Q2 offset_times_utc"
        )
        if len(sample_times) != h * 47 or len(offset_times) != h:
            raise V023ScientificVerificationError("Q2 projection timestamp count drifted")
        if sample_times and any(
            abs((right - left).total_seconds() - 0.640) > 1.0e-9
            for left, right in zip(sample_times, sample_times[1:], strict=False)
        ):
            raise V023ScientificVerificationError("Q2 projection clock is not native 640 ms")
        if tuple(sample_times[(index + 1) * 47 - 1] for index in range(h)) != offset_times:
            raise V023ScientificVerificationError("Q2 offset timestamps are not decision endpoints")

    learned: list[float] = []
    target: list[float] = []
    transition: list[str] = []
    for pair in range(pair_anchor.size):
        if not bool(pair_retained[pair]):
            continue
        anchor = int(pair_anchor[pair])
        for user, candidate in zip(pair_users[pair], pair_actions[pair], strict=True):
            uid = int(user)
            action = int(candidate)
            reference = int(q12_reference[anchor, uid])
            if not bool(masks[anchor, uid, action]):
                raise V023ScientificVerificationError("retained C2 diagnostic candidate is illegal")
            learned.append(float(q2[anchor, uid, action] - q2[anchor, uid, reference]))
            target.append(float(teacher[anchor, uid, action] - teacher[anchor, uid, reference]))
            transition.append(
                _transition_class(
                    physical_keys[anchor], user=uid, reference=reference, candidate=action
                )
            )
    learned_array = np.asarray(learned, dtype=np.float64)
    target_array = np.asarray(target, dtype=np.float64)
    exposure = None if learned_array.size == 0 else float(
        np.count_nonzero(np.abs(learned_array) >= SIGN_THRESHOLD) / learned_array.size
    )
    transition_counts = {
        name: int(sum(item == name for item in transition))
        for name in (
            "SAME_PHYSICAL_LINK",
            "INTRA_SATELLITE_BEAM_MOVE",
            "INTER_SATELLITE_MOVE",
        )
    }
    transition_exposure: dict[str, dict[str, Any]] = {}
    for name in transition_counts:
        selected = np.asarray([item == name for item in transition], dtype=np.bool_)
        count = int(np.count_nonzero(selected))
        nontrivial = int(np.count_nonzero(np.abs(learned_array[selected]) >= SIGN_THRESHOLD))
        transition_exposure[name] = {
            "row_count": count,
            "nontrivial_count": nontrivial,
            "exposure": None if count == 0 else nontrivial / count,
        }
    return {
        "row_count": int(learned_array.size),
        "nontrivial_count": int(np.count_nonzero(np.abs(learned_array) >= SIGN_THRESHOLD)),
        "exposure": exposure,
        "spearman": tie_aware_spearman(learned_array, target_array),
        "sign": sign_receipt(learned_array, target_array),
        "q1_to_q12_argmax_change_count": int(np.count_nonzero(q1_reference != q12_reference)),
        "served_decision_count": int(q1_reference.size),
        "transition_counts": transition_counts,
        "transition_exposure": transition_exposure,
        "prediction": learned_array.tolist(),
        "target": target_array.tolist(),
        "finite": True,
        "provenance_authenticated": True,
        "mask_verified": True,
        "timing_verified": True,
        "target_free_verified": True,
        "opening_verified": True,
        "absorbing_persistence_verified": True,
        "terminal_zero_verified": True,
        "frozen_background_semantics": "AUTHORITY_BOUND_LIVE_OPS3_SNAPSHOT",
        "runtime_default_multiplier_used": False,
        "world_only_not_final_predicate": True,
        "deduplication": "one row per retained pair member",
    }


@dataclass(frozen=True)
class _Formula:
    own: np.ndarray
    nonfocal: np.ndarray
    d: np.ndarray
    joint_delta_bits: float
    joint_delta_energy: float
    joint_surplus: float
    interaction_bits: float
    interaction_energy: float
    interaction_surplus: float
    equal_share: float
    z3: np.ndarray
    residual: float


def _stable_sum(values: object) -> float:
    """Mirror the frozen formula's delta-domain stable summation independently."""

    array = np.asarray(values, dtype=np.float64)
    result = math.fsum(float(value) for value in array.reshape(-1).tolist())
    if not math.isfinite(result):
        raise V023ScientificVerificationError("formula summation is non-finite")
    return float(result)


def _formula(bits: np.ndarray, energy: np.ndarray, users: np.ndarray) -> _Formula:
    reference_bits = np.asarray(bits[0], dtype=np.float64)
    unilateral_bits = np.asarray(bits[1:3], dtype=np.float64)
    joint_bits = np.asarray(bits[3], dtype=np.float64)
    reference_energy = float(energy[0])
    unilateral_energy = np.asarray(energy[1:3], dtype=np.float64)
    joint_energy = float(energy[3])
    unilateral_delta_bits = unilateral_bits - reference_bits[None, :]
    joint_delta_bits_by_user = joint_bits - reference_bits
    unilateral_delta_energy = unilateral_energy - reference_energy
    joint_delta_energy = joint_energy - reference_energy
    own = np.empty(2, dtype=np.float64)
    nonfocal = np.empty(2, dtype=np.float64)
    for member in range(2):
        user = int(users[member])
        own[member] = (
            unilateral_delta_bits[member, user]
            - LAMBDA_BITS_PER_J * unilateral_delta_energy[member]
        )
        nonfocal[member] = _stable_sum(
            np.delete(unilateral_delta_bits[member], user)
        )
    d = own + nonfocal
    joint_delta_bits = _stable_sum(joint_delta_bits_by_user)
    joint_surplus = joint_delta_bits - LAMBDA_BITS_PER_J * joint_delta_energy
    unilateral_totals = np.asarray(
        [_stable_sum(row) for row in unilateral_delta_bits], dtype=np.float64
    )
    interaction_bits = joint_delta_bits - _stable_sum(unilateral_totals)
    interaction_energy = joint_delta_energy - _stable_sum(unilateral_delta_energy)
    interaction_surplus = interaction_bits - LAMBDA_BITS_PER_J * interaction_energy
    equal_share = 0.5 * interaction_surplus
    z3 = nonfocal + equal_share
    residual = _stable_sum(own + z3) - joint_surplus
    return _Formula(
        own=own,
        nonfocal=nonfocal,
        d=d,
        joint_delta_bits=joint_delta_bits,
        joint_delta_energy=joint_delta_energy,
        joint_surplus=joint_surplus,
        interaction_bits=interaction_bits,
        interaction_energy=interaction_energy,
        interaction_surplus=interaction_surplus,
        equal_share=equal_share,
        z3=z3,
        residual=residual,
    )


def _required_arrays(arrays: Mapping[str, np.ndarray]) -> None:
    required = {
        "anchor_phase", "anchor_status", "anchor_retained",
        "anchor_content_digest", "anchor_view_content_digest",
        "anchor_topology_content_digest", "action_context", "tokens",
        "token_mask", "action_mask", "opening_feasibility",
        "reference_actions", "physical_keys", "q1_values",
        "q2_values", "q12_values", "q2_state_matrix",
        "q2_feature_surface", "q2_teacher_values", "q2_persistence",
        "q2_rate_bps", "q2_marginal_power_w", "q2_required_power_w",
        "q2_horizon", "pair_anchor_index", "pair_retained",
        "pair_id", "pair_user_ids", "pair_action_ids", "pair_target_by_draw",
        "pair_target_mean", "pair_class", "draw_pair_index", "draw_pair_id",
        "draw_index", "profile_actions", "profile_bits", "profile_energy_j",
        "profile_g_bits", "profile_served", "profile_active_beam_keys",
        "profile_active_beam_counts", "z3_bits_by_draw",
        "z3_normalized_by_draw", "formula_identity_residual_bits",
        "ratio_identity_value_bits", "ratio_cross_product", "ratio_sign",
        "ratio_tolerance", "ratio_local_tolerance", "joint_ee_bits_per_j",
        "nonmutation_flags", "common_field_digest", "action_digest",
        "formula_own_bits", "formula_nonfocal_bits", "formula_d_bits",
        "formula_joint_delta_bits", "formula_joint_delta_energy_j",
        "formula_joint_surplus_bits", "formula_interaction_bits",
        "formula_interaction_energy_j", "formula_interaction_surplus_bits",
        "formula_equal_share_bits",
    }
    missing = sorted(required - set(arrays))
    if missing:
        raise V023ScientificVerificationError(f"source NPZ lacks arrays: {missing}")


def _teacher_digest(
    *,
    pair_id: str,
    users: np.ndarray,
    actions: np.ndarray,
    draws: list[Mapping[str, Any]],
    targets: np.ndarray,
) -> str:
    digest = hashlib.sha256()
    digest.update(TEACHER_SCHEMA.encode("ascii"))
    encoded = pair_id.encode("utf-8")
    digest.update(struct.pack(">I", len(encoded)))
    digest.update(encoded)
    digest.update(np.ascontiguousarray(users, dtype=np.int64).tobytes(order="C"))
    digest.update(np.ascontiguousarray(actions, dtype=np.int64).tobytes(order="C"))
    for draw in draws:
        draw_index = draw.get("draw_index")
        if type(draw_index) is not int:
            raise V023ScientificVerificationError("teacher draw index is not an integer")
        digest.update(struct.pack(">I", draw_index))
        digest.update(
            np.ascontiguousarray(draw.get("profile_actions"), dtype=np.int64).tobytes(
                order="C"
            )
        )
        digest.update(
            np.ascontiguousarray(draw.get("profile_bits"), dtype=np.float64).tobytes(
                order="C"
            )
        )
        digest.update(
            np.ascontiguousarray(
                draw.get("profile_energy_j"), dtype=np.float64
            ).tobytes(order="C")
        )
        fields = draw.get("common_field_sha256_by_profile")
        actions_sha = draw.get("action_sha256_by_profile")
        if not isinstance(fields, list) or len(fields) != 4:
            raise V023ScientificVerificationError("teacher common-field list drifted")
        if not isinstance(actions_sha, list) or len(actions_sha) != 4:
            raise V023ScientificVerificationError("teacher action-digest list drifted")
        digest.update(_digest(fields[0], field="teacher common field").encode("ascii"))
        for value in actions_sha:
            digest.update(_digest(value, field="teacher action digest").encode("ascii"))
    digest.update(np.ascontiguousarray(targets, dtype=np.float64).tobytes(order="C"))
    return digest.hexdigest()


def _verify_teacher_json(
    payload: Mapping[str, Any], arrays: Mapping[str, np.ndarray]
) -> None:
    """Bind the human-readable teacher receipt to the raw numeric sidecar."""

    for name in ("enumeration", "topology", "teacher", "surface"):
        value = _mapping(payload.get(name), field=name)
        if payload.get(f"{name}_sha256") != canonical_sha256(value):
            raise V023ScientificVerificationError(f"{name} canonical digest drifted")
    teacher_root = _mapping(payload.get("teacher"), field="teacher")
    anchors = teacher_root.get("anchors")
    if not isinstance(anchors, list):
        raise V023ScientificVerificationError("teacher anchor list is missing")
    pair_anchor = np.asarray(arrays["pair_anchor_index"], dtype=np.int64)
    pair_ids = np.asarray(arrays["pair_id"])
    pair_users = np.asarray(arrays["pair_user_ids"], dtype=np.int64)
    pair_actions = np.asarray(arrays["pair_action_ids"], dtype=np.int64)
    pair_targets = np.asarray(arrays["pair_target_by_draw"], dtype=np.float64)
    pair_means = np.asarray(arrays["pair_target_mean"], dtype=np.float64)
    decoded_pair_ids = [
        _decode_ascii(value, field="pair id") for value in pair_ids
    ]
    if len(decoded_pair_ids) != len(set(decoded_pair_ids)):
        raise V023ScientificVerificationError("pair ids are not unique")
    draw_pair = np.asarray(arrays["draw_pair_index"], dtype=np.int64)
    draw_index = np.asarray(arrays["draw_index"], dtype=np.int64)
    if draw_pair.shape != draw_index.shape or draw_pair.ndim != 1:
        raise V023ScientificVerificationError("teacher draw identity shape drifted")
    raw_identities = [
        (int(pair), int(draw))
        for pair, draw in zip(draw_pair, draw_index, strict=True)
    ]
    if (
        len(raw_identities) != len(set(raw_identities))
        or any(
            pair < 0
            or pair >= pair_anchor.size
            or draw < 0
            or draw >= DRAW_COUNT
            for pair, draw in raw_identities
        )
    ):
        raise V023ScientificVerificationError("teacher draw identities are invalid or repeated")
    row_lookup = {
        (int(pair), int(draw)): row
        for row, (pair, draw) in enumerate(
            zip(draw_pair, draw_index, strict=True)
        )
    }
    flattened: list[tuple[int, Mapping[str, Any]]] = []
    for anchor_index, anchor in enumerate(anchors):
        anchor_object = _mapping(anchor, field="teacher anchor")
        pairs = anchor_object.get("pairs")
        if not isinstance(pairs, list):
            raise V023ScientificVerificationError("teacher pair list is missing")
        flattened.extend(
            (anchor_index, _mapping(pair, field="teacher pair")) for pair in pairs
        )
    if len(flattened) != pair_anchor.size:
        raise V023ScientificVerificationError("teacher JSON/NPZ pair counts disagree")
    for pair_index, (anchor_index, teacher) in enumerate(flattened):
        if int(pair_anchor[pair_index]) != anchor_index:
            raise V023ScientificVerificationError("teacher pair anchor order drifted")
        pair_id = decoded_pair_ids[pair_index]
        if teacher.get("pair_id") != pair_id:
            raise V023ScientificVerificationError("teacher pair id drifted")
        users = np.asarray(teacher.get("member_users"), dtype=np.int64)
        actions = np.asarray(teacher.get("proposed_actions"), dtype=np.int64)
        targets = np.asarray(teacher.get("pair_targets_by_draw"), dtype=np.float64)
        means = np.asarray(teacher.get("pair_target_mean"), dtype=np.float64)
        if not np.array_equal(users, pair_users[pair_index]) or not np.array_equal(
            actions, pair_actions[pair_index]
        ):
            raise V023ScientificVerificationError("teacher pair identity drifted")
        _assert_numeric_equal(targets, pair_targets[pair_index], field="teacher targets")
        _assert_numeric_equal(means, pair_means[pair_index], field="teacher target mean")
        draws = teacher.get("draws")
        if not isinstance(draws, list) or len(draws) != DRAW_COUNT:
            raise V023ScientificVerificationError("teacher lacks exact 32 draws")
        for expected_draw, draw_value in enumerate(draws):
            draw = _mapping(draw_value, field="teacher draw")
            if draw.get("draw_index") != expected_draw:
                raise V023ScientificVerificationError("teacher draw order drifted")
            try:
                row = row_lookup[(pair_index, expected_draw)]
            except KeyError as error:
                raise V023ScientificVerificationError(
                    "teacher draw identity is missing from NPZ"
                ) from error
            _assert_numeric_equal(
                draw.get("profile_actions"),
                arrays["profile_actions"][row],
                field="teacher profile actions",
            )
            _assert_numeric_equal(
                draw.get("profile_bits"),
                arrays["profile_bits"][row],
                field="teacher profile bits",
            )
            _assert_numeric_equal(
                draw.get("profile_energy_j"),
                arrays["profile_energy_j"][row],
                field="teacher profile energy",
            )
            fields = draw.get("common_field_sha256_by_profile")
            if not isinstance(fields, list) or len(fields) != 4 or len(set(fields)) != 1:
                raise V023ScientificVerificationError("teacher profiles do not share a field")
            if fields[0] != _decode_ascii(
                arrays["common_field_digest"][row], field="common field"
            ):
                raise V023ScientificVerificationError("teacher common field drifted")
            action_digests = draw.get("action_sha256_by_profile")
            if not isinstance(action_digests, list) or len(action_digests) != 4:
                raise V023ScientificVerificationError("teacher action digests drifted")
            for profile in range(4):
                if action_digests[profile] != _decode_ascii(
                    arrays["action_digest"][row, profile], field="action digest"
                ):
                    raise V023ScientificVerificationError("teacher action digest drifted")
        content_digest = _digest(
            teacher.get("content_digest"), field="teacher content digest"
        )
        if content_digest != _teacher_digest(
            pair_id=pair_id,
            users=users,
            actions=actions,
            draws=[_mapping(value, field="teacher draw") for value in draws],
            targets=targets,
        ):
            raise V023ScientificVerificationError("teacher content digest drifted")


def _verify_interface_a_and_topology(
    payload: Mapping[str, Any], arrays: Mapping[str, np.ndarray]
) -> None:
    """Recompute native reference selection and exact-two topology from raw arrays."""

    phases = np.asarray(arrays["anchor_phase"])
    status = np.asarray(arrays["anchor_status"])
    retained = np.asarray(arrays["anchor_retained"])
    contexts = np.asarray(arrays["action_context"])
    tokens = np.asarray(arrays["tokens"])
    token_mask = np.asarray(arrays["token_mask"])
    action_mask = np.asarray(arrays["action_mask"])
    opening = np.asarray(arrays["opening_feasibility"])
    references = np.asarray(arrays["reference_actions"])
    physical = np.asarray(arrays["physical_keys"])
    q1 = np.asarray(arrays["q1_values"])
    q2 = np.asarray(arrays["q2_values"])
    q12 = np.asarray(arrays["q12_values"])
    expected_anchor_shape = (len(WORLD_PHASES), USER_COUNT, ACTION_COUNT)
    if phases.dtype != np.int64 or phases.shape != (len(WORLD_PHASES),):
        raise V023ScientificVerificationError("anchor phase array is malformed")
    if tuple(int(value) for value in phases.tolist()) != WORLD_PHASES:
        raise V023ScientificVerificationError("anchor phases are not exact 1..9")
    if status.dtype != np.uint8 or status.shape != (len(WORLD_PHASES),):
        raise V023ScientificVerificationError("anchor status array is malformed")
    if retained.dtype != np.bool_ or retained.shape != (len(WORLD_PHASES),):
        raise V023ScientificVerificationError("anchor retained array is malformed")
    if not np.array_equal(status, retained.astype(np.uint8)):
        raise V023ScientificVerificationError("anchor status/retention drifted")
    if contexts.dtype != np.float32 or contexts.shape != expected_anchor_shape + (29,):
        raise V023ScientificVerificationError("Interface-A action context shape/dtype drifted")
    if tokens.dtype != np.float32 or tokens.shape != (
        len(WORLD_PHASES), USER_COUNT, ACTION_COUNT, USER_COUNT + 1, 38
    ):
        raise V023ScientificVerificationError("Interface-A token shape/dtype drifted")
    if token_mask.dtype != np.bool_ or token_mask.shape != tokens.shape[:-1]:
        raise V023ScientificVerificationError("Interface-A token mask drifted")
    if action_mask.dtype != np.bool_ or action_mask.shape != expected_anchor_shape:
        raise V023ScientificVerificationError("native action mask shape/dtype drifted")
    if opening.dtype != np.bool_ or opening.shape != expected_anchor_shape:
        raise V023ScientificVerificationError("opening-feasibility shape/dtype drifted")
    if references.dtype != np.int64 or references.shape != expected_anchor_shape[:2]:
        raise V023ScientificVerificationError("reference action shape/dtype drifted")
    if physical.dtype != np.int64 or physical.shape != expected_anchor_shape + (2,):
        raise V023ScientificVerificationError("physical-key surface shape/dtype drifted")
    if any(value.dtype != np.float64 or value.shape != expected_anchor_shape for value in (q1, q2, q12)):
        raise V023ScientificVerificationError("Q1/Q2 surface shape/dtype drifted")
    if not all(np.all(np.isfinite(value)) for value in (contexts, tokens, q1, q2, q12)):
        raise V023ScientificVerificationError("Interface-A contains a nonfinite value")
    if np.any(opening & ~action_mask) or np.any(~np.any(action_mask, axis=2)):
        raise V023ScientificVerificationError("opening/native action masks are inconsistent")
    if np.any(references < 0) or np.any(references >= ACTION_COUNT):
        raise V023ScientificVerificationError("reference action is out of range")
    anchor_index = np.arange(len(WORLD_PHASES))[:, None]
    user_index = np.arange(USER_COUNT)[None, :]
    if not np.all(action_mask[anchor_index, user_index, references]):
        raise V023ScientificVerificationError("reference action is not native-legal")
    if not np.array_equal(
        q12,
        np.asarray(
            np.asarray(q1, dtype=np.float32) + np.asarray(q2, dtype=np.float32),
            dtype=np.float64,
        ),
    ):
        raise V023ScientificVerificationError("Q12 is not the exact float32 Q1+Q2 sum")
    expected_references = np.argmax(
        np.where(action_mask, q12, -np.inf), axis=2
    ).astype(np.int64)
    if not np.array_equal(references, expected_references):
        raise V023ScientificVerificationError("reference actions are not native masked Q1+Q2 argmax")
    rows = np.arange(USER_COUNT)
    for anchor in range(len(WORLD_PHASES)):
        expected_margin = np.asarray(
            np.tanh(q12[anchor] - q12[anchor, rows, references[anchor], None]),
            dtype=np.float32,
        )
        if not np.allclose(
            contexts[anchor, :, :, 23][action_mask[anchor]],
            expected_margin[action_mask[anchor]],
            rtol=0.0,
            atol=2.0 * np.finfo(np.float32).eps,
        ):
            raise V023ScientificVerificationError("encoded Q12 margin drifted")
    if not np.array_equal(contexts[:, :, :, 3] == np.float32(1.0), opening):
        raise V023ScientificVerificationError("opening predicate and Interface-A field drifted")
    if not np.array_equal(token_mask[:, :, :, USER_COUNT], action_mask):
        raise V023ScientificVerificationError("pair-token mask does not equal native action mask")
    if np.any(token_mask[:, :, :, :USER_COUNT] & ~action_mask[:, :, :, None]):
        raise V023ScientificVerificationError("ordinary token mask widens native action mask")
    if (
        np.any(contexts[~action_mask] != 0.0)
        or np.any(tokens[~action_mask] != 0.0)
        or np.any(tokens[~token_mask] != 0.0)
    ):
        raise V023ScientificVerificationError("masked Interface-A cells are not zero-filled")
    bound = np.float32(1.0 + 32.0 * np.finfo(np.float32).eps)
    if np.any(np.abs(contexts[action_mask]) > bound) or np.any(np.abs(tokens[token_mask]) > bound):
        raise V023ScientificVerificationError("Interface-A feature escaped [-1,1]")
    pair_tokens = tokens[:, :, :, USER_COUNT, :]
    if (
        np.any(pair_tokens[:, :, :, 0][action_mask] != 0.0)
        or np.any(pair_tokens[:, :, :, 1][action_mask] != 1.0)
    ):
        raise V023ScientificVerificationError("Interface-A pair token type drifted")

    for name in (
        "anchor_content_digest",
        "anchor_view_content_digest",
        "anchor_topology_content_digest",
    ):
        values = np.asarray(arrays[name])
        if values.shape != (len(WORLD_PHASES),) or values.dtype.kind != "S":
            raise V023ScientificVerificationError(f"{name} shape/dtype drifted")
        for anchor, value in enumerate(values):
            decoded = _decode_ascii(value, field=name)
            _digest(decoded, field=name)
            if name == "anchor_view_content_digest" and decoded != c3_view_sha256(
                contexts[anchor],
                tokens[anchor],
                token_mask[anchor],
                action_mask[anchor],
                references[anchor],
            ):
                raise V023ScientificVerificationError("C3View digest disagrees with Interface-A arrays")

    anchors = payload.get("anchors")
    receipt_anchor_ids = _mapping(payload.get("world_receipt"), field="world_receipt").get("anchor_ids")
    if not isinstance(anchors, list) or len(anchors) != len(WORLD_PHASES):
        raise V023ScientificVerificationError("source JSON anchor schedule is incomplete")
    for anchor, phase in enumerate(WORLD_PHASES):
        entry = _mapping(anchors[anchor], field="source anchor")
        if (
            entry.get("phase") != phase
            or entry.get("anchor_id") != receipt_anchor_ids[anchor]
            or entry.get("retained_for_fitting") is not bool(retained[anchor])
        ):
            raise V023ScientificVerificationError("source JSON/NPZ anchor identity drifted")

    pair_anchor = np.asarray(arrays["pair_anchor_index"], dtype=np.int64)
    pair_users = np.asarray(arrays["pair_user_ids"], dtype=np.int64)
    pair_actions = np.asarray(arrays["pair_action_ids"], dtype=np.int64)
    actual_by_anchor: dict[int, list[tuple[tuple[int, int], tuple[int, int]]]] = {
        anchor: [] for anchor in range(len(WORLD_PHASES))
    }
    for pair in range(pair_anchor.size):
        actual_by_anchor[int(pair_anchor[pair])].append(
            (
                tuple(int(value) for value in pair_users[pair]),
                tuple(int(value) for value in pair_actions[pair]),
            )
        )

    expected_by_anchor: dict[int, list[tuple[tuple[int, int], tuple[int, int]]]] = {}
    for anchor in range(len(WORLD_PHASES)):
        for user in range(USER_COUNT):
            legal = np.flatnonzero(action_mask[anchor, user])
            keys = [tuple(int(value) for value in physical[anchor, user, action]) for action in legal]
            if any(first < 0 or second < 0 for first, second in keys) or len(keys) != len(set(keys)):
                raise V023ScientificVerificationError("native legal physical keys are malformed or repeated")
            if np.any(physical[anchor, user, ~action_mask[anchor, user]] != -1):
                raise V023ScientificVerificationError("illegal physical keys are not -1 padded")
        source_users: dict[tuple[int, int], list[int]] = {}
        for user in range(USER_COUNT):
            key = tuple(int(value) for value in physical[anchor, user, references[anchor, user]])
            source_users.setdefault(key, []).append(user)
        expected: list[tuple[tuple[int, int], tuple[int, int]]] = []
        for source, members_raw in sorted(source_users.items()):
            members = tuple(sorted(members_raw))
            if len(members) != 2 or not all(
                bool(opening[anchor, user, references[anchor, user]]) for user in members
            ):
                continue
            nonmember_keys = {
                tuple(int(value) for value in physical[anchor, other, references[anchor, other]])
                for other in range(USER_COUNT)
                if other not in members
            }
            selected: list[int] = []
            for user in members:
                eligible = [
                    int(action)
                    for action in np.flatnonzero(action_mask[anchor, user] & opening[anchor, user])
                    if tuple(int(value) for value in physical[anchor, user, action]) != source
                    and tuple(int(value) for value in physical[anchor, user, action]) in nonmember_keys
                ]
                if not eligible:
                    selected = []
                    break
                selected.append(max(eligible, key=lambda action: (float(q12[anchor, user, action]), -action)))
            if len(selected) == 2:
                expected.append((members, (selected[0], selected[1])))
        expected_by_anchor[anchor] = expected
        supported = 2 * len(expected)
        reference_count = USER_COUNT
        control_count = int(np.count_nonzero(action_mask[anchor])) - reference_count - supported
        should_retain = bool(expected and supported > 0 and reference_count > 0 and control_count > 0)
        if bool(retained[anchor]) != should_retain:
            raise V023ScientificVerificationError("anchor retention is not exact S/R/C topology retention")
        if actual_by_anchor[anchor] != expected:
            raise V023ScientificVerificationError("pair table is not the canonical outcome-blind topology")
        for members, selected in expected:
            for user, action in zip(members, selected, strict=True):
                if not np.array_equal(
                    pair_tokens[anchor, user, action, 2:5],
                    np.asarray([1.0, 1.0, 1.0], dtype=np.float32),
                ):
                    raise V023ScientificVerificationError("supported pair cell lacks designated pair sentinel")

    if payload.get("pair_count") != pair_anchor.size:
        raise V023ScientificVerificationError("source pair count disagrees with canonical topology")


def _placebo_shift(stratum: tuple[int, int, int, int, int, int], size: int) -> int:
    if size < 2:
        raise V023ScientificVerificationError("placebo stratum needs at least two cells")
    encoded = json.dumps(
        {"key": PLACEBO_KEY, "stratum": stratum},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big") % (size - 1) + 1


def _verify_placebo_receipt(
    payload: Mapping[str, Any], arrays: Mapping[str, np.ndarray]
) -> tuple[int, int]:
    """Rebuild source-world strata, cyclic mappings, and their content digest."""

    world = int(payload["world"])
    retained = np.asarray(arrays["anchor_retained"], dtype=np.bool_)
    phases = np.asarray(arrays["anchor_phase"], dtype=np.int64)
    contexts = np.asarray(arrays["action_context"], dtype=np.float32)
    action_mask = np.asarray(arrays["action_mask"], dtype=np.bool_)
    references = np.asarray(arrays["reference_actions"], dtype=np.int64)
    q12 = np.asarray(arrays["q12_values"], dtype=np.float64)
    pair_anchor = np.asarray(arrays["pair_anchor_index"], dtype=np.int64)
    pair_retained = np.asarray(arrays["pair_retained"], dtype=np.bool_)
    pair_users = np.asarray(arrays["pair_user_ids"], dtype=np.int64)
    pair_actions = np.asarray(arrays["pair_action_ids"], dtype=np.int64)
    pair_means = np.asarray(arrays["pair_target_mean"], dtype=np.float64)
    anchors = payload.get("anchors")
    if not isinstance(anchors, list):
        raise V023ScientificVerificationError("source anchor table is missing")
    retained_anchors = np.flatnonzero(retained).tolist()
    record_index = {anchor: index for index, anchor in enumerate(retained_anchors)}
    record_digests: list[str] = []
    anchor_ids: list[str] = []
    targets: list[np.ndarray] = []
    for anchor in retained_anchors:
        entry = _mapping(anchors[anchor], field="retained source anchor")
        anchor_id = entry.get("anchor_id")
        if not isinstance(anchor_id, str) or not anchor_id:
            raise V023ScientificVerificationError("retained anchor id is malformed")
        surface = _mapping(entry.get("surface"), field="retained anchor surface")
        record = _mapping(surface.get("record"), field="retained anchor record")
        record_digests.append(
            _digest(record.get("content_digest"), field="anchor record content digest")
        )
        anchor_ids.append(anchor_id)
        targets.append(np.zeros((USER_COUNT, ACTION_COUNT), dtype=np.float32))

    groups: dict[tuple[int, int, int, int, int, int], list[tuple[int, int, int]]] = {}
    seen_cells: set[tuple[int, int, int]] = set()
    for pair in range(pair_anchor.size):
        if not bool(pair_retained[pair]):
            continue
        anchor = int(pair_anchor[pair])
        if anchor not in record_index:
            raise V023ScientificVerificationError("retained pair lacks a retained anchor record")
        local_anchor = record_index[anchor]
        for member in range(2):
            user = int(pair_users[pair, member])
            action = int(pair_actions[pair, member])
            cell = (local_anchor, user, action)
            if cell in seen_cells:
                raise V023ScientificVerificationError("SUPPORTED placebo cell is repeated")
            seen_cells.add(cell)
            if not bool(action_mask[anchor, user, action]) or float(contexts[anchor, user, action, 3]) != 1.0:
                raise V023ScientificVerificationError("SUPPORTED placebo cell is not legal-and-opening")
            scaled_occupancy = float(contexts[anchor, user, action, 27]) * USER_COUNT
            occupancy = int(round(scaled_occupancy))
            if occupancy < 1 or not math.isclose(
                scaled_occupancy,
                occupancy,
                rel_tol=0.0,
                abs_tol=2.0e-6 * USER_COUNT,
            ):
                raise V023ScientificVerificationError("SUPPORTED placebo occupancy is malformed")
            active = float(contexts[anchor, user, action, 12])
            if active not in (0.0, 1.0):
                raise V023ScientificVerificationError("SUPPORTED placebo activity is nonbinary")
            reference = int(references[anchor, user])
            q_reference = float(q12[anchor, user, reference])
            q_candidate = float(q12[anchor, user, action])
            gap = q_reference - q_candidate
            if abs(gap) <= comparison_tolerance(q_reference, q_candidate):
                gap = 0.0
            if gap < 0.0:
                raise V023ScientificVerificationError("SUPPORTED placebo base gap is negative")
            gap_bin = 0 if gap < 0.01 else 1 if gap < 0.05 else 2 if gap < 0.20 else 3
            stratum = (
                world,
                (int(phases[anchor]) - 1) // 3,
                1,
                1 if occupancy == 1 else 2,
                int(active),
                gap_bin,
            )
            groups.setdefault(stratum, []).append(cell)
            targets[local_anchor][user, action] = np.float32(pair_means[pair, member])

    strata: list[dict[str, Any]] = []
    mappings: list[dict[str, Any]] = []
    digest_mappings: list[tuple[tuple[int, int, int, int, int, int], int, tuple[int, int, int], tuple[int, int, int]]] = []
    eligible = 0
    for stratum, raw_cells in sorted(groups.items()):
        cells = sorted(
            raw_cells,
            key=lambda cell: (world, anchor_ids[cell[0]], cell[1], cell[2]),
        )
        rows = [
            {
                "anchor_index": anchor,
                "world": world,
                "anchor_id": anchor_ids[anchor],
                "user": user,
                "action": action,
            }
            for anchor, user, action in cells
        ]
        strata.append(
            {
                "stratum": list(stratum),
                "rows": rows,
                "count": len(cells),
                "placebo_eligible": len(cells) >= 2,
            }
        )
        if len(cells) < 2:
            continue
        eligible += len(cells)
        shift = _placebo_shift(stratum, len(cells))
        originals = [float(targets[a][u, x]) for a, u, x in cells]
        for destination_index, destination in enumerate(cells):
            source_index = (destination_index - shift) % len(cells)
            source = cells[source_index]
            da, du, dx = destination
            sa, su, sx = source
            targets[da][du, dx] = np.float32(originals[source_index])
            mapping = {
                "stratum": list(stratum),
                "source_anchor": sa,
                "source_user": su,
                "source_action": sx,
                "destination_anchor": da,
                "destination_user": du,
                "destination_action": dx,
                "shift": shift,
            }
            mappings.append(mapping)
            digest_mappings.append((stratum, shift, source, destination))

    total = len(seen_cells)
    expected: dict[str, Any] = {
        "schema": f"{SOURCE_ARTIFACT_SCHEMA}-placebo-strata-v1",
        "strata": strata,
        "mappings": mappings,
        "supported_count": total,
        "placebo_eligible_count": eligible,
        "coverage": 0.0 if total == 0 else eligible / total,
        "within_world_only": True,
        "placebo_key": PLACEBO_KEY,
        "placebo_key_sha256": PLACEBO_KEY_SHA256,
        "outcome_filter_applied": False,
    }
    if retained_anchors:
        digest = hashlib.sha256()
        digest.update(b"multi-catfish-mcrl-v023-matched-placebo-v1")
        digest.update(PLACEBO_KEY_SHA256.encode("ascii"))
        for record_digest, target in zip(record_digests, targets, strict=True):
            digest.update(record_digest.encode("ascii"))
            digest.update(np.ascontiguousarray(target, dtype=np.float32).tobytes(order="C"))
        for stratum, shift, source, destination in digest_mappings:
            digest.update(struct.pack(">6qI", *stratum, shift))
            digest.update(struct.pack(">6q", *source, *destination))
        expected["content_digest"] = digest.hexdigest()
    observed = _mapping(payload.get("placebo_strata"), field="placebo_strata")
    if dict(observed) != expected:
        raise V023ScientificVerificationError("placebo strata/mapping receipt disagrees with raw reconstruction")
    if payload.get("supported_count") != total or payload.get("placebo_eligible_count") != eligible:
        raise V023ScientificVerificationError("top-level placebo coverage counts drifted")
    return total, eligible


def verify_source_world_science(index_path: Path) -> dict[str, Any]:
    """Recompute one world's LC-SRS physics and C1/C2 context diagnostics."""

    path = Path(index_path)
    payload = _load_json(path, field="source index")
    if payload.get("schema") != SOURCE_SCHEMA or payload.get("status") != "PASS":
        raise V023ScientificVerificationError("source index schema/status drifted")
    if payload.get("claim_ceiling") != CLAIM_CEILING:
        raise V023ScientificVerificationError("source claim ceiling drifted")
    if (
        payload.get("split") != "TRAIN_DEVELOPMENT"
        or payload.get("test_split_opened") is not False
        or payload.get("episode_training") is not False
        or payload.get("learner_update") is not False
    ):
        raise V023ScientificVerificationError("source crossed a closed boundary")
    _verify_receipt_seal(payload)
    preflight_sha256 = _verify_source_authority(payload)
    background = _mapping(payload.get("q12_background"), field="q12_background")
    if float.fromhex(str(background.get("lambda_bits_per_j_hex"))) != LAMBDA_BITS_PER_J:
        raise V023ScientificVerificationError("source lambda drifted")
    if float.fromhex(str(background.get("kappa_bits_hex"))) != KAPPA_BITS:
        raise V023ScientificVerificationError("source kappa drifted")
    arrays = _load_npz(
        index_path=path,
        binding=_mapping(payload.get("arrays"), field="arrays"),
        domain=SOURCE_ARRAY_DOMAIN,
    )
    _required_arrays(arrays)
    _verify_teacher_json(payload, arrays)

    pair_anchor = np.asarray(arrays["pair_anchor_index"], dtype=np.int64)
    pair_users = np.asarray(arrays["pair_user_ids"], dtype=np.int64)
    pair_actions = np.asarray(arrays["pair_action_ids"], dtype=np.int64)
    pair_retained = np.asarray(arrays["pair_retained"], dtype=np.bool_)
    pair_class = np.asarray(arrays["pair_class"], dtype=np.uint8)
    pair_targets = np.asarray(arrays["pair_target_by_draw"], dtype=np.float64)
    pair_means = np.asarray(arrays["pair_target_mean"], dtype=np.float64)
    pair_count = pair_anchor.size
    if (
        pair_anchor.shape != (pair_count,)
        or pair_users.shape != (pair_count, 2)
        or pair_actions.shape != (pair_count, 2)
        or pair_retained.shape != (pair_count,)
        or pair_class.shape != (pair_count, 2)
        or pair_targets.shape != (pair_count, DRAW_COUNT, 2)
        or pair_means.shape != (pair_count, 2)
    ):
        raise V023ScientificVerificationError("pair table shape drifted")
    if not np.all(pair_class == 3):
        raise V023ScientificVerificationError("physical pair table class drifted")
    anchor_retained = np.asarray(arrays["anchor_retained"], dtype=np.bool_)
    if (
        anchor_retained.ndim != 1
        or np.any(pair_anchor < 0)
        or np.any(pair_anchor >= anchor_retained.size)
        or not np.array_equal(
        pair_retained, anchor_retained[pair_anchor]
        )
    ):
        raise V023ScientificVerificationError("pair-retained mapping drifted")
    _verify_interface_a_and_topology(payload, arrays)
    supported_count, placebo_eligible_count = _verify_placebo_receipt(payload, arrays)
    c2_result = _verify_q2_context(
        payload=payload,
        arrays=arrays,
        pair_anchor=pair_anchor,
        pair_users=pair_users,
        pair_actions=pair_actions,
        pair_retained=pair_retained,
    )
    _assert_numeric_equal(
        pair_means,
        np.mean(pair_targets, axis=1, dtype=np.float64),
        field="pair target means",
    )

    draw_pair = np.asarray(arrays["draw_pair_index"], dtype=np.int64)
    draw_index = np.asarray(arrays["draw_index"], dtype=np.int64)
    row_count = pair_count * DRAW_COUNT
    if draw_pair.shape != (row_count,) or draw_index.shape != (row_count,):
        raise V023ScientificVerificationError("draw identity shape drifted")
    expected_identities = {(pair, draw) for pair in range(pair_count) for draw in range(DRAW_COUNT)}
    actual_identities = {(int(pair), int(draw)) for pair, draw in zip(draw_pair, draw_index, strict=True)}
    if actual_identities != expected_identities or len(actual_identities) != row_count:
        raise V023ScientificVerificationError("draw panel is not exact P x 32")

    profile_actions = np.asarray(arrays["profile_actions"], dtype=np.int64)
    profile_bits = np.asarray(arrays["profile_bits"], dtype=np.float64)
    profile_energy = np.asarray(arrays["profile_energy_j"], dtype=np.float64)
    served = np.asarray(arrays["profile_served"], dtype=np.bool_)
    active_keys = np.asarray(arrays["profile_active_beam_keys"], dtype=np.int64)
    active_counts = np.asarray(arrays["profile_active_beam_counts"], dtype=np.int64)
    reference = np.asarray(arrays["reference_actions"], dtype=np.int64)
    physical_keys = np.asarray(arrays["physical_keys"], dtype=np.int64)
    q1 = np.asarray(arrays["q1_values"], dtype=np.float64)
    q2 = np.asarray(arrays["q2_values"], dtype=np.float64)
    q12 = np.asarray(arrays["q12_values"], dtype=np.float64)
    nonmutation_raw = np.asarray(arrays["nonmutation_flags"])
    nonmutation = np.asarray(nonmutation_raw, dtype=np.bool_)
    anchor_count, user_count = reference.shape
    if (
        profile_actions.shape != (row_count, 4, user_count)
        or profile_bits.shape != (row_count, 4, user_count)
        or profile_energy.shape != (row_count, 4)
        or served.shape != (row_count, 4, user_count)
        or active_keys.ndim != 4
        or active_keys.shape[:2] != (row_count, 4)
        or active_keys.shape[3] != 2
        or active_counts.shape != (row_count, 4)
        or physical_keys.shape[:2] != q1.shape[:2]
        or physical_keys.shape[2:] != (q1.shape[2], 2)
        or q2.shape != q1.shape
        or q12.shape != q1.shape
        or q1.shape[:2] != (anchor_count, user_count)
        or nonmutation_raw.dtype != np.dtype(np.bool_)
        or nonmutation.shape != (row_count, 5)
    ):
        raise V023ScientificVerificationError("profile/anchor surface shape drifted")
    if not np.all(np.isfinite(profile_bits)) or np.any(profile_bits < 0.0):
        raise V023ScientificVerificationError("profile bits are nonfinite/negative")
    if not np.all(np.isfinite(profile_energy)) or np.any(profile_energy <= 0.0):
        raise V023ScientificVerificationError("profile energy is nonfinite/nonpositive")
    if not bool(np.all(nonmutation)):
        raise V023ScientificVerificationError(
            "profile evaluation mutation flag failed; this is an integrity error"
        )

    pair_pass = np.ones(pair_count, dtype=np.bool_)
    pooled_bits = np.zeros(2, dtype=np.float64)
    pooled_energy = np.zeros(2, dtype=np.float64)
    c1_truth: list[float] = []
    c1_prediction: list[float] = []
    seen: set[tuple[int, int]] = set()
    ratio_identity_failure_count = 0
    for row in range(row_count):
        pair = int(draw_pair[row])
        draw = int(draw_index[row])
        anchor = int(pair_anchor[pair])
        if not 0 <= anchor < anchor_count:
            raise V023ScientificVerificationError("pair anchor index is invalid")
        users = pair_users[pair]
        actions = pair_actions[pair]
        if len(set(int(value) for value in users)) != 2:
            raise V023ScientificVerificationError("pair members are not distinct")
        if np.any(users < 0) or np.any(users >= user_count):
            raise V023ScientificVerificationError("pair member index is invalid")
        base = reference[anchor]
        expected = np.tile(base, (4, 1))
        expected[1, int(users[0])] = int(actions[0])
        expected[2, int(users[1])] = int(actions[1])
        expected[3, users] = actions
        if not np.array_equal(profile_actions[row], expected):
            raise V023ScientificVerificationError("00/10/01/11 action panel drifted")
        pair_id = _decode_ascii(arrays["pair_id"][pair], field="pair id")
        draw_pair_id = _decode_ascii(arrays["draw_pair_id"][row], field="draw pair id")
        if pair_id != draw_pair_id:
            raise V023ScientificVerificationError("draw pair id drifted")
        for profile in range(4):
            if _decode_ascii(arrays["action_digest"][row, profile], field="action digest") != action_sha256(expected[profile]):
                raise V023ScientificVerificationError("action digest disagrees")
        source_keys = {
            tuple(int(value) for value in physical_keys[anchor, int(user), int(base[int(user)])])
            for user in users
        }
        if len(source_keys) != 1:
            raise V023ScientificVerificationError("pair members do not share one source key")
        source_key = next(iter(source_keys))
        destinations = {
            tuple(int(value) for value in physical_keys[anchor, int(user), int(action)])
            for user, action in zip(users, actions, strict=True)
        }
        active = [
            _active_set(
                active_keys[row, profile],
                int(active_counts[row, profile]),
                field=f"active beams row {row} profile {profile}",
            )
            for profile in range(4)
        ]
        mechanics = (
            all(source_key in active[profile] for profile in (0, 1, 2))
            and source_key not in active[3]
            and destinations.issubset(active[0])
            and destinations.issubset(active[3])
            and active[3] == active[0] - {source_key}
            and all(bool(served[row, profile, int(user)]) for profile in range(4) for user in users)
            and int(np.count_nonzero(served[row, 3])) >= int(np.count_nonzero(served[row, 0]))
        )
        pair_pass[pair] &= mechanics

        bits = profile_bits[row]
        energy = profile_energy[row]
        totals = np.asarray(
            [math.fsum(float(value) for value in profile.tolist()) for profile in bits],
            dtype=np.float64,
        )
        _assert_numeric_equal(arrays["profile_g_bits"][row], totals - LAMBDA_BITS_PER_J * energy, field="G profile")
        recomputed = _formula(bits, energy, users)
        checks = {
            "formula_own_bits": recomputed.own,
            "formula_nonfocal_bits": recomputed.nonfocal,
            "formula_d_bits": recomputed.d,
            "formula_joint_delta_bits": recomputed.joint_delta_bits,
            "formula_joint_delta_energy_j": recomputed.joint_delta_energy,
            "formula_joint_surplus_bits": recomputed.joint_surplus,
            "formula_interaction_bits": recomputed.interaction_bits,
            "formula_interaction_energy_j": recomputed.interaction_energy,
            "formula_interaction_surplus_bits": recomputed.interaction_surplus,
            "formula_equal_share_bits": recomputed.equal_share,
            "z3_bits_by_draw": recomputed.z3,
            "z3_normalized_by_draw": recomputed.z3 / KAPPA_BITS,
            "formula_identity_residual_bits": recomputed.residual,
        }
        for name, value in checks.items():
            _assert_numeric_equal(arrays[name][row], value, field=name)
        identity_bound = 1.0e-12 * (
            1.0 + abs(recomputed.joint_surplus) + float(np.sum(np.abs(recomputed.own + recomputed.z3)))
        )
        if abs(recomputed.residual) > identity_bound:
            raise V023ScientificVerificationError("formula identity exceeds frozen bound")
        _assert_numeric_equal(pair_targets[pair, draw], recomputed.z3 / KAPPA_BITS, field="pair target by draw")

        left = float(totals[3] * energy[0])
        right = float(totals[0] * energy[3])
        cross = left - right
        tolerance = comparison_tolerance(left, right)
        direction = 1 if cross > tolerance else -1 if cross < -tolerance else 0
        local = float((totals[3] - totals[0]) - (totals[0] / energy[0]) * (energy[3] - energy[0]))
        local_tolerance = tolerance / float(energy[0])
        local_direction = 1 if local > local_tolerance else -1 if local < -local_tolerance else 0
        ratio_identity_pass = direction == local_direction
        # The ratio identity is a per-draw physical predicate.  Keep the
        # finite profile in the complete denominator and let the frozen
        # >=90%-mechanics rule decide STOP_PHYSICS.  Malformed/non-finite
        # profiles and formula/identity corruption still fail closed above.
        if not ratio_identity_pass:
            ratio_identity_failure_count += 1
            pair_pass[pair] = False
        ratio_checks = {
            "ratio_cross_product": cross,
            "ratio_tolerance": tolerance,
            "ratio_sign": direction,
            "ratio_identity_value_bits": local,
            "ratio_local_tolerance": local_tolerance,
            "joint_ee_bits_per_j": float(totals[3] / energy[3]),
        }
        for name, value in ratio_checks.items():
            _assert_numeric_equal(arrays[name][row], value, field=name)

        pooled_bits += (totals[0], totals[3])
        pooled_energy += (energy[0], energy[3])
        if (pair, draw) not in seen:
            seen.add((pair, draw))
        if draw == 0 and bool(pair_retained[pair]):
            for member in range(2):
                user = int(users[member])
                action = int(actions[member])
                ref_action = int(base[user])
                c1_truth.append(float(np.mean([
                    _formula(
                        profile_bits[np.flatnonzero((draw_pair == pair) & (draw_index == other_draw))[0]],
                        profile_energy[np.flatnonzero((draw_pair == pair) & (draw_index == other_draw))[0]],
                        users,
                    ).own[member] / KAPPA_BITS
                    for other_draw in range(DRAW_COUNT)
                ])))
                c1_prediction.append(float(q1[anchor, user, action] - q1[anchor, user, ref_action]))

    if seen != expected_identities:
        raise V023ScientificVerificationError("not every pair/draw was recomputed")
    mechanics_fraction = None if pair_count == 0 else float(np.count_nonzero(pair_pass) / pair_count)
    world_direction = strict_direction(
        float(pooled_bits[1] * pooled_energy[0]),
        float(pooled_bits[0] * pooled_energy[1]),
    )
    c1_truth_array = np.asarray(c1_truth, dtype=np.float64)
    c1_prediction_array = np.asarray(c1_prediction, dtype=np.float64)
    c1_sign = sign_receipt(c1_prediction_array, c1_truth_array)
    c1_spearman = tie_aware_spearman(c1_prediction_array, c1_truth_array)
    return {
        "status": "VERIFIED_SOURCE_NUMERICS",
        "gate_decision": None,
        "scientific_claim": False,
        "contract_sha256": CONTRACT_SHA256,
        "preflight_manifest_sha256": preflight_sha256,
        "execution_addendum_sha256": EXECUTION_ADDENDUM_SHA256,
        "world": int(payload["world"]),
        "pair_count": int(pair_count),
        "mechanics_pass_count": int(np.count_nonzero(pair_pass)),
        "mechanics_fraction": mechanics_fraction,
        "ratio_identity_failure_count": int(ratio_identity_failure_count),
        "world_joint_direction": int(world_direction),
        "joint_00_bits": float(pooled_bits[0]),
        "joint_11_bits": float(pooled_bits[1]),
        "joint_00_energy_j": float(pooled_energy[0]),
        "joint_11_energy_j": float(pooled_energy[1]),
        "c1": {
            "row_count": int(c1_truth_array.size),
            "spearman": c1_spearman,
            "sign": c1_sign,
            "world_only_not_final_predicate": True,
            "deduplication": "one mean-over-32 row per pair member",
            "prediction": c1_prediction_array.tolist(),
            "target": c1_truth_array.tolist(),
        },
        "c2": c2_result,
        "retained_supported_count": supported_count,
        "placebo_eligible_count": placebo_eligible_count,
        "target_support_count": int(
            np.count_nonzero(np.abs(pair_means[pair_retained]) >= SIGN_THRESHOLD)
        ),
    }


def _metric_sidecar_binding(receipt: Mapping[str, Any]) -> tuple[str, str, str]:
    metrics = _mapping(receipt.get("metrics"), field="fit metrics binding")
    path = metrics.get("npz_path")
    digest_path = metrics.get("npz_sha256_file")
    digest = _digest(metrics.get("npz_sha256"), field="fit metrics NPZ SHA-256")
    if not isinstance(path, str) or not isinstance(digest_path, str):
        raise V023ScientificVerificationError("fit metrics NPZ paths are malformed")
    return path, digest_path, digest


def verify_fit_science(receipt_path: Path) -> dict[str, Any]:
    """Independently recompute held-out rank/sign metrics from one fit shard."""

    path = Path(receipt_path)
    receipt = _load_json(path, field="fit receipt")
    if receipt.get("schema") != FIT_SCHEMA or receipt.get("status") != "PASS":
        raise V023ScientificVerificationError("fit schema/status drifted")
    if receipt.get("claim_ceiling") != CLAIM_CEILING:
        raise V023ScientificVerificationError("fit claim ceiling drifted")
    if (
        receipt.get("split") != "TRAIN_DEVELOPMENT"
        or receipt.get("test_split_opened") is not False
        or receipt.get("episode_training") is not False
        or receipt.get("learner_update") is not True
        or receipt.get("update_count") != 2000
    ):
        raise V023ScientificVerificationError("fit crossed or missed a frozen boundary")
    _verify_receipt_seal(receipt)
    relative, digest_relative, digest = _metric_sidecar_binding(receipt)
    root = path.parent.resolve()
    npz_path = _safe_child(root, relative, field="fit metrics NPZ")
    digest_path = _safe_child(root, digest_relative, field="fit metrics digest")
    if file_sha256(npz_path) != digest:
        raise V023ScientificVerificationError("fit metrics NPZ byte hash disagrees")
    _verify_digest_file(digest_path, digest=digest, target_name=npz_path.name)
    metrics_binding = _mapping(receipt.get("metrics"), field="fit metrics binding")
    metrics_json_path = _safe_child(root, metrics_binding.get("path"), field="fit metrics JSON")
    if file_sha256(metrics_json_path) != _digest(metrics_binding.get("sha256"), field="fit metrics JSON SHA-256"):
        raise V023ScientificVerificationError("fit metrics JSON byte hash disagrees")
    metrics = _load_json(metrics_json_path, field="fit metrics JSON")
    metadata = _mapping(metrics.get("arrays"), field="fit metric array metadata")
    try:
        with np.load(npz_path, allow_pickle=False) as archive:
            arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    except (OSError, ValueError, KeyError) as error:
        raise V023ScientificVerificationError("fit metrics NPZ cannot be loaded safely") from error
    if set(arrays) != set(metadata) or any(value.dtype == object for value in arrays.values()):
        raise V023ScientificVerificationError("fit metric arrays disagree or contain object dtype")
    for name, array in arrays.items():
        entry = _mapping(metadata[name], field=f"fit metadata[{name}]")
        if entry.get("dtype") != array.dtype.str or entry.get("shape") != list(array.shape):
            raise V023ScientificVerificationError(f"fit array {name} shape/dtype drifted")
        if entry.get("sha256") != _array_digest(array, domain=FIT_PREDICTION_ARRAY_DOMAIN):
            raise V023ScientificVerificationError(f"fit array {name} digest drifted")
    prediction = np.asarray(arrays.get("prediction"), dtype=np.float64)
    target = np.asarray(arrays.get("target"), dtype=np.float64)
    if prediction.ndim != 1 or target.shape != prediction.shape:
        raise V023ScientificVerificationError("held-out prediction/target shape drifted")
    if np.asarray(arrays.get("loss")).shape != (2000,):
        raise V023ScientificVerificationError("fit loss count drifted")
    spearman = tie_aware_spearman(prediction, target)
    sign = r7_fit_sign_receipt(prediction, target)
    reported_spearman = metrics.get("spearman")
    if (reported_spearman is None) != (spearman is None):
        raise V023ScientificVerificationError("reported Spearman nullability drifted")
    if spearman is not None:
        _assert_numeric_equal(reported_spearman, spearman, field="held-out Spearman")
    reported_sign = _mapping(metrics.get("sign"), field="reported sign")
    for key, value in sign.items():
        if value is None:
            if reported_sign.get(key) is not None:
                raise V023ScientificVerificationError("reported sign nullability drifted")
        elif isinstance(value, float):
            _assert_numeric_equal(reported_sign.get(key), value, field=f"sign {key}")
        elif reported_sign.get(key) != value:
            raise V023ScientificVerificationError(f"reported sign {key} drifted")
    return {
        "status": "PASS_FIT_NUMERIC_RECOMPUTATION",
        "scientific_claim": False,
        "held_out_world": int(receipt["held_out_world"]),
        "student_seed": int(receipt["student_seed"]),
        "arm": str(receipt["arm"]),
        "rows": int(target.size),
        "spearman": spearman,
        "sign": sign,
        "identity": [
            {
                "world": int(world),
                "anchor": _decode_ascii(anchor, field="fit anchor identity"),
                "user": int(user),
                "action": int(action),
            }
            for world, anchor, user, action in zip(
                arrays["identity_world"],
                arrays["identity_anchor"],
                arrays["identity_user"],
                arrays["identity_action"],
                strict=True,
            )
        ],
        "prediction": prediction.tolist(),
        "target": target.tolist(),
    }


def verify_source_panel_science(index_paths: list[Path] | tuple[Path, ...]) -> dict[str, Any]:
    """Aggregate the exact eight source worlds without treating them as seeds."""

    results = [verify_source_world_science(Path(path)) for path in index_paths]
    by_world = {int(result["world"]): result for result in results}
    if len(results) != len(WORLDS) or set(by_world) != set(WORLDS):
        raise V023ScientificVerificationError("source panel is not the exact eight worlds")
    preflights = {str(result["preflight_manifest_sha256"]) for result in results}
    if len(preflights) != 1:
        raise V023ScientificVerificationError("source worlds do not share one preflight manifest")
    preflight_sha256 = next(iter(preflights))
    ordered = [by_world[world] for world in WORLDS]
    pair_count = sum(int(result["pair_count"]) for result in ordered)
    mechanics_count = sum(int(result["mechanics_pass_count"]) for result in ordered)
    pair_coverage = pair_count >= 24 and all(int(result["pair_count"]) >= 1 for result in ordered)
    mechanics = pair_count > 0 and mechanics_count / pair_count >= 0.90
    pooled_00_bits = math.fsum(float(result["joint_00_bits"]) for result in ordered)
    pooled_11_bits = math.fsum(float(result["joint_11_bits"]) for result in ordered)
    pooled_00_energy = math.fsum(float(result["joint_00_energy_j"]) for result in ordered)
    pooled_11_energy = math.fsum(float(result["joint_11_energy_j"]) for result in ordered)
    pooled_direction = strict_direction(
        pooled_11_bits * pooled_00_energy,
        pooled_00_bits * pooled_11_energy,
    )
    positive_worlds = sum(int(result["world_joint_direction"]) == 1 for result in ordered)
    physical_signature = pooled_direction == 1 and positive_worlds >= 4
    target_support = sum(int(result["target_support_count"]) for result in ordered)

    placebo_folds: dict[str, dict[str, Any]] = {}
    placebo_pass = True
    for held_out in WORLDS:
        numerator = sum(
            int(result["placebo_eligible_count"])
            for result in ordered
            if int(result["world"]) != held_out
        )
        denominator = sum(
            int(result["retained_supported_count"])
            for result in ordered
            if int(result["world"]) != held_out
        )
        coverage = None if denominator == 0 else numerator / denominator
        passed = coverage is not None and coverage >= 0.80
        placebo_pass &= passed
        placebo_folds[str(held_out)] = {
            "eligible": numerator,
            "supported": denominator,
            "coverage": coverage,
            "passes": passed,
        }

    c1_prediction = np.asarray(
        [value for result in ordered for value in result["c1"]["prediction"]],
        dtype=np.float64,
    )
    c1_target = np.asarray(
        [value for result in ordered for value in result["c1"]["target"]],
        dtype=np.float64,
    )
    c1_rho = tie_aware_spearman(c1_prediction, c1_target)
    c1_sign = sign_receipt(c1_prediction, c1_target)
    c1_pass = (
        c1_rho is not None
        and c1_rho >= 0.20
        and int(c1_sign["evaluated_rows"]) >= 24
        and c1_sign["accuracy"] is not None
        and float(c1_sign["accuracy"]) >= 0.55
    )
    c2_prediction = np.asarray(
        [value for result in ordered for value in result["c2"]["prediction"]],
        dtype=np.float64,
    )
    c2_target = np.asarray(
        [value for result in ordered for value in result["c2"]["target"]],
        dtype=np.float64,
    )
    c2_exposure = None if c2_prediction.size == 0 else float(
        np.count_nonzero(np.abs(c2_prediction) >= SIGN_THRESHOLD) / c2_prediction.size
    )
    c2_rho = tie_aware_spearman(c2_prediction, c2_target)
    c2_sign = sign_receipt(c2_prediction, c2_target)
    c2_invariants = all(
        all(
            result["c2"].get(field) is True
            for field in (
                "finite",
                "provenance_authenticated",
                "mask_verified",
                "timing_verified",
                "target_free_verified",
                "opening_verified",
                "absorbing_persistence_verified",
                "terminal_zero_verified",
            )
        )
        and result["c2"].get("runtime_default_multiplier_used") is False
        and result["c2"].get("frozen_background_semantics")
        == "AUTHORITY_BOUND_LIVE_OPS3_SNAPSHOT"
        for result in ordered
    )
    c2_pass = c2_invariants and c2_exposure is not None and c2_exposure >= 0.10
    if c1_pass and c2_pass:
        context_status = "CONTEXT_DIAGNOSTICS_PASS"
    elif not c1_pass and c2_pass:
        context_status = "HOLD_C1"
    elif c1_pass and not c2_pass:
        context_status = "HOLD_C2"
    else:
        context_status = "HOLD_C1_C2"
    return {
        "status": "VERIFIED_SOURCE_PANEL_NUMERICS",
        "gate_decision": None,
        "scientific_claim": False,
        "contract_sha256": CONTRACT_SHA256,
        "preflight_manifest_sha256": preflight_sha256,
        "execution_addendum_sha256": EXECUTION_ADDENDUM_SHA256,
        "worlds": list(WORLDS),
        "world_results": ordered,
        "predicates": {
            "pair_coverage": bool(pair_coverage and placebo_pass),
            "mechanics": bool(mechanics),
            "physical_signature": bool(physical_signature),
            "target_support": bool(target_support >= 24),
        },
        "pair_count": pair_count,
        "mechanics_pass_count": mechanics_count,
        "pooled_joint_direction": pooled_direction,
        "positive_world_count": positive_worlds,
        "target_support_count": target_support,
        "placebo_folds": placebo_folds,
        "c1": {
            "spearman": c1_rho,
            "sign": c1_sign,
            "passes": bool(c1_pass),
        },
        "c2": {
            "row_count": int(c2_prediction.size),
            "nontrivial_count": int(
                np.count_nonzero(np.abs(c2_prediction) >= SIGN_THRESHOLD)
            ),
            "exposure": c2_exposure,
            "spearman": c2_rho,
            "sign": c2_sign,
            "prediction": c2_prediction.tolist(),
            "target": c2_target.tolist(),
            "q1_to_q12_argmax_change_count": sum(
                int(result["c2"]["q1_to_q12_argmax_change_count"])
                for result in ordered
            ),
            "served_decision_count": sum(
                int(result["c2"]["served_decision_count"]) for result in ordered
            ),
            "transition_counts": {
                name: sum(int(result["c2"]["transition_counts"][name]) for result in ordered)
                for name in (
                    "SAME_PHYSICAL_LINK",
                    "INTRA_SATELLITE_BEAM_MOVE",
                    "INTER_SATELLITE_MOVE",
                )
            },
            "all_invariants_pass": bool(c2_invariants),
            "numeric_exposure_passes": bool(
                c2_exposure is not None and c2_exposure >= 0.10
            ),
            "passes": bool(c2_pass),
            "qualification_claim": False,
        },
        "context_status": context_status,
    }


def verify_fit_panel_science(receipt_paths: list[Path] | tuple[Path, ...]) -> dict[str, Any]:
    """Aggregate the exact R7 8 x 3 x 2 panel under balanced semantics."""

    results = [verify_fit_science(Path(path)) for path in receipt_paths]
    r7 = _load_r7_decision()
    expected = {
        (world, seed, arm)
        for world in WORLDS
        for seed in STUDENT_SEEDS
        for arm in FIT_ARMS
    }
    by_identity: dict[tuple[int, int, str], Mapping[str, Any]] = {}
    for result in results:
        key = (
            int(result["held_out_world"]),
            int(result["student_seed"]),
            str(result["arm"]),
        )
        if key in by_identity or key not in expected:
            raise V023ScientificVerificationError(
                "fit panel has duplicate or out-of-panel identity"
            )
        by_identity[key] = result
    if set(by_identity) != expected:
        raise V023ScientificVerificationError(
            "fit panel is not the exact 8 x 3 x 2 schedule"
        )
    for world in WORLDS:
        reference = by_identity[(world, STUDENT_SEEDS[0], "INFORMED")]
        identities = reference["identity"]
        target = np.asarray(reference["target"], dtype=np.float64)
        for seed in STUDENT_SEEDS:
            for arm in FIT_ARMS:
                result = by_identity[(world, seed, arm)]
                if result["identity"] != identities or not np.array_equal(
                    np.asarray(result["target"], dtype=np.float64), target
                ):
                    raise V023ScientificVerificationError(
                        "held-out true labels/identities differ across seed or arm"
                    )
    shards = [
        r7.HeldOutShard(
            world=world,
            seed=seed,
            arm=arm,
            predictions=np.asarray(result["prediction"], dtype=np.float64),
            targets=np.asarray(result["target"], dtype=np.float64),
            spearman=result["spearman"],
        )
        for world in WORLDS
        for seed in STUDENT_SEEDS
        for arm in FIT_ARMS
        for result in (by_identity[(world, seed, arm)],)
    ]
    try:
        balanced = r7.evaluate_r7_panel(shards)
    except Exception as error:
        raise V023ScientificVerificationError(
            f"R7 balanced learner panel failed closed: {error}"
        ) from error
    first_seed = STUDENT_SEEDS[0]
    targets = np.concatenate(
        [
            np.asarray(
                next(
                    shard.targets
                    for shard in shards
                    if shard.world == world
                    and shard.seed == first_seed
                    and shard.arm == "INFORMED"
                ),
                dtype=np.float64,
            )
            for world in WORLDS
        ]
    )
    target_support_count = int(np.count_nonzero(np.abs(targets) >= SIGN_THRESHOLD))
    predicates = dict(balanced["predicates"])
    predicates["target_support"] = target_support_count >= 24
    return {
        "status": "PASS_R7_BALANCED_FIT_PANEL_NUMERIC_RECOMPUTATION",
        "scientific_claim": False,
        "fit_count": len(results),
        **balanced,
        "target_support_count": target_support_count,
        "predicates": predicates,
    }


__all__ = [
    "V023ScientificVerificationError",
    "verify_source_world_science",
    "verify_fit_science",
    "verify_source_panel_science",
    "verify_fit_panel_science",
    "tie_aware_spearman",
    "sign_receipt",
    "action_sha256",
]
