#!/usr/bin/env python3
"""V0.23 C3 contingency F1 shared two-step kill screen.

Imports and ``--dry-run`` are simulator-inert.  A real run requires a
separately frozen launch-authority document and writes one immutable physical
tape, one tape manifest, and one result receipt.  D and F are both derived
from the same unilateral tape through the existing F0 implementation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import traceback
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SRC = REPO / "src"
F0_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency"
PHYSICAL_DIR = REPO / ".scratch" / "multi-catfish-v023-physical"
R7_DIR = REPO / ".scratch" / "multi-catfish-v023-r7-launch-ready"
for _path in (SRC, F0_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from c3_contingency_f0 import (  # noqa: E402
    F0_SCHEMA,
    PhysicalProfile,
    compute_c3_targets,
)
from mcrl.env.action_contract import (  # noqa: E402
    Association,
    NO_OP_ACTION,
    NUM_ACTIONS,
)
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v023-c3-contingency-f1-v1"
TAPE_SCHEMA = f"{SCHEMA}-physical-tape"
TAPE_MANIFEST_SCHEMA = f"{SCHEMA}-physical-tape-manifest"
PREFLIGHT_SCHEMA = f"{SCHEMA}-preflight-manifest"
LAUNCH_AUTHORITY_SCHEMA = f"{SCHEMA}-launch-authority"
RECEIPT_SCHEMA = f"{SCHEMA}-receipt"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_C3_CONTINGENCY_F1_KILL_SCREEN_NO_EFFICACY_NO_TEST"
)

WORLD = 2026121721
LINEAGE = 2026092101
CANONICAL_STEP_INDICES = (0, 1)
STEP_COUNT = 2
USERS = 100
SPLIT = "TRAIN"
FIELD_COMPONENT = "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1"
SERVICE_MARGIN = 0.001
LAMBDA_BITS_PER_J = float.fromhex("0x1.c3c0a7b6b86d3p+26")

# The ladder does not state a separate composition operator.  This constant
# names its plain reading and is deliberately the only deployment choice:
# masked argmax(Q1 + Q2 + z), with z in the same normalized score units and
# no scale, clip, sign filter, compatibility gate, or tie override.
F1_DEPLOYMENT_RULE = "MASKED_ARGMAX_Q1_PLUS_Q2_PLUS_Z_NO_SCALING"
REFERENCE_DEPLOYMENT_RULE = "MASKED_ARGMAX_Q1_PLUS_Q2"
CANDIDATE_ENUMERATION_RULE = (
    "ALL_MASK_LEGAL_NON_NOOP_UNILATERAL_PHYSICAL_CHANGES_BY_USER_THEN_ACTION"
)

CHECKPOINT_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v020-c3-source-audit"
    / "repriced-q1-q2-fit"
    / "lineage-2026092101"
    / "checkpoints"
    / "lineage-2026092101-q2init-2026108101-rung-003000.pt"
)
CHECKPOINT_SHA256 = "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc"
AUTHORITY_PATH = CHECKPOINT_PATH.parents[1] / "authority.json"
AUTHORITY_BODY_SHA256 = "50d32dae11b2906bb23a25893f4ba5c11d0f88197ee94fe7cd216677e8703d48"
AUTHORITY_FILE_SHA256 = "a05ee801c8f9d640b55f8ec984d874f149c30b868d1706d998f7e2053520078e"
SOURCE_CONTRACT_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v020-c3-source-audit"
    / "Q1-Q2-REPRICED-SUPERVISED-EXECUTION-CONTRACT-2026-09-04.md"
)
SOURCE_CONTRACT_SHA256 = "ea36414aac87b3ef5ba48dbe753e73ff21a0e164d54cdb3edbb899b509edd48c"
REPRICING_CONTRACT_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v020-c3-source-audit"
    / "Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md"
)
REPRICING_CONTRACT_SHA256 = "34732dd3f65ffebf760313c2ffd235e0ecbd406ba6065dbce5635778550ef4a9"
PREREG_PATH = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
PREREG_SHA256 = "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
PREREG_RECORD_DIGEST = "3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4"

LADDER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v023-c3-observability"
    / "V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md"
)
LADDER_SHA256 = "e75222c27cf10c8197f022344d726d0614109d534acaf73f20fa75175531161b"
F0_PATH = F0_DIR / "c3_contingency_f0.py"
F0_SHA256 = "658e4072fb2457aee81800d97eda89b4890cdfe85ac7b0154f7d207ff7fbe673"
R7_RESULT_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v023-controller-handoff-20260907"
    / "r7-sealed-receipts"
    / "result.json"
)
R7_RESULT_SHA256 = "dfcc70e441e2ec2c3be20608124c704c6d5c80b4d902a1aa7b75328faadbd2f7"
R7_MANIFEST_PATH = R7_RESULT_PATH.parent / "MANIFEST.sha256"
R7_MANIFEST_SHA256 = "63ecb5a8ec08f8fe89c5e656871fd019493e0eb6fdb7777e152c9fef85b8c01f"
R7_COMPLETE_PATH = R7_RESULT_PATH.parent / "COMPLETE"
R7_COMPLETE_SHA256 = "bb5adae2a6eb73c16a08dc87a5c2c5d5fcacff7b306407bde3e7c9e0390835b2"

DEFAULT_PREFLIGHT = HERE / "F1-PREFLIGHT-MANIFEST.json"
DEFAULT_TAPE_NAME = "physical-unilateral-tape.json"
DEFAULT_TAPE_MANIFEST_NAME = "physical-unilateral-tape.manifest.json"
DEFAULT_RECEIPT_NAME = "receipt.json"

CODE_BINDING_PATHS = (
    ("f1_runner", HERE / "run_v023_c3_contingency_f1.py"),
    ("f1_preflight_builder", HERE / "build_f1_preflight_manifest.py"),
    ("f0_formula", F0_PATH),
    ("action_evaluation", REPO / "src/mcrl/env/step.py"),
    ("action_contract", REPO / "src/mcrl/env/action_contract.py"),
    ("service_resolution", REPO / "src/mcrl/env/service.py"),
    ("keyed_field", REPO / "src/mcrl/env/keyed_fading.py"),
    ("unilateral_enumerator", REPO / "src/mcrl/runtime/ee_axis_source_selectors.py"),
    ("unilateral_evaluator", REPO / "src/mcrl/runtime/ee_axis_opening_source.py"),
    ("q12_source_stage", R7_DIR / "v023_lcsrs_source_adapter.py"),
    ("q12_physical_loader", PHYSICAL_DIR / "v023_physical_episode_runner.py"),
    ("canonical_environment_glue", PHYSICAL_DIR / "run_v023_dropc3_evaluation_server.py"),
    ("ops3_live", REPO / "src/mcrl/runtime/ee_axis_ops3_live.py"),
    ("q2_state", REPO / "src/mcrl/runtime/ee_axis_v014_q2_state.py"),
)


class F1Error(RuntimeError):
    """The F1 binding, tape, or kill-screen contract failed closed."""


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise F1Error("value is not finite canonical ASCII JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise F1Error(f"required regular file is missing or symlinked: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repo_relative(path: Path) -> str:
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(REPO.resolve()):
        raise F1Error(f"binding escapes repository: {path}")
    return resolved.relative_to(REPO.resolve()).as_posix()


def _load_json(path: Path, *, field: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise F1Error(f"{field} is missing or symlinked: {target}")
    try:
        value = json.loads(target.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise F1Error(f"{field} is not ASCII JSON: {target}") from error
    if not isinstance(value, dict):
        raise F1Error(f"{field} must be a JSON object")
    return value


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise F1Error(f"{field} must be a lowercase SHA-256")
    return value


@dataclass(frozen=True)
class F1Bindings:
    world: int = WORLD
    lineage: int = LINEAGE
    canonical_step_indices: tuple[int, ...] = CANONICAL_STEP_INDICES
    step_count: int = STEP_COUNT
    split: str = SPLIT
    field_component: str = FIELD_COMPONENT
    users: int = USERS

    def verify(self) -> None:
        if type(self.world) is not int or self.world != WORLD:
            raise F1Error(f"F1 permits only world {WORLD}")
        if type(self.lineage) is not int or self.lineage != LINEAGE:
            raise F1Error(f"F1 permits only lineage {LINEAGE}")
        if tuple(self.canonical_step_indices) != CANONICAL_STEP_INDICES:
            raise F1Error("F1 permits only canonical steps 0 and 1")
        if type(self.step_count) is not int or self.step_count != STEP_COUNT:
            raise F1Error("F1 permits exactly two canonical decision steps")
        if self.split != SPLIT:
            raise F1Error("F1 permits only the TRAIN split")
        if self.field_component != FIELD_COMPONENT:
            raise F1Error("F1 keyed-field component drifted from the R7 source stage")
        if type(self.users) is not int or self.users != USERS:
            raise F1Error("F1 uses the frozen 100-user physical carrier")

    def as_dict(self) -> dict[str, object]:
        self.verify()
        field = KeyedFadingField.from_components(self.field_component, self.world)
        return {
            "world": self.world,
            "lineage": self.lineage,
            "canonical_step_indices": list(self.canonical_step_indices),
            "step_count": self.step_count,
            "split": self.split,
            "field_component": self.field_component,
            "field_root_digest": field.root_digest,
            "users": self.users,
            "reference_deployment_rule": REFERENCE_DEPLOYMENT_RULE,
            "candidate_deployment_rule": F1_DEPLOYMENT_RULE,
            "candidate_enumeration_rule": CANDIDATE_ENUMERATION_RULE,
            "service_margin": SERVICE_MARGIN,
            "ee_rule": "POOLED_RATIO_OF_SUMS_STRICTLY_ABOVE_BASE",
            "candidate_priority": ["D", "F"],
        }


def authority_bindings() -> dict[str, object]:
    return {
        "checkpoint": {
            "path": _repo_relative(CHECKPOINT_PATH),
            "sha256": CHECKPOINT_SHA256,
            "role": "V020_REPRICED_LINEAGE_2026092101_RUNG_003000",
        },
        "q12_authority": {
            "path": _repo_relative(AUTHORITY_PATH),
            "file_sha256": AUTHORITY_FILE_SHA256,
            "body_sha256": AUTHORITY_BODY_SHA256,
        },
        "source_contract": {
            "path": _repo_relative(SOURCE_CONTRACT_PATH),
            "sha256": SOURCE_CONTRACT_SHA256,
        },
        "repricing_contract": {
            "path": _repo_relative(REPRICING_CONTRACT_PATH),
            "sha256": REPRICING_CONTRACT_SHA256,
        },
        "preregistration": {
            "path": _repo_relative(PREREG_PATH),
            "sha256": PREREG_SHA256,
            "record_digest": PREREG_RECORD_DIGEST,
        },
        "contingency_ladder": {
            "path": _repo_relative(LADDER_PATH),
            "sha256": LADDER_SHA256,
        },
        "f0_formula": {
            "path": _repo_relative(F0_PATH),
            "sha256": F0_SHA256,
            "schema": F0_SCHEMA,
        },
        "r7_stop_receipt": {
            "path": _repo_relative(R7_RESULT_PATH),
            "sha256": R7_RESULT_SHA256,
            "manifest_path": _repo_relative(R7_MANIFEST_PATH),
            "manifest_sha256": R7_MANIFEST_SHA256,
            "complete_path": _repo_relative(R7_COMPLETE_PATH),
            "complete_sha256": R7_COMPLETE_SHA256,
            "required_decision": "STOP_PHYSICS_R7",
        },
        "lambda_bits_per_j_hex": LAMBDA_BITS_PER_J.hex(),
    }


def formula_digests() -> dict[str, str]:
    source = inspect.getsource(compute_c3_targets).encode("utf-8")
    deployment = (
        "selected=argmax(where(legal,Q1+Q2+z,-inf));scale=1;"
        "numpy-first-index-tie"
    ).encode("ascii")
    kill = canonical_bytes(
        {
            "integrity": "all",
            "mutation": "any-legal-action-changed",
            "service": "candidate>=base-0.001",
            "ee": "candidate-ratio-of-sums>base-ratio-of-sums",
            "priority": ["D", "F"],
        }
    )
    return {
        "f0_file_sha256": file_sha256(F0_PATH),
        "compute_c3_targets_source_sha256": hashlib.sha256(source).hexdigest(),
        "deployment_formula_sha256": hashlib.sha256(deployment).hexdigest(),
        "kill_rule_sha256": hashlib.sha256(kill).hexdigest(),
    }


def validate_static_bindings() -> dict[str, object]:
    bindings = F1Bindings()
    bindings.verify()
    expected_files = (
        (CHECKPOINT_PATH, CHECKPOINT_SHA256, "checkpoint"),
        (AUTHORITY_PATH, AUTHORITY_FILE_SHA256, "authority"),
        (SOURCE_CONTRACT_PATH, SOURCE_CONTRACT_SHA256, "source contract"),
        (REPRICING_CONTRACT_PATH, REPRICING_CONTRACT_SHA256, "repricing contract"),
        (PREREG_PATH, PREREG_SHA256, "TRAIN PREREG"),
        (LADDER_PATH, LADDER_SHA256, "contingency ladder"),
        (F0_PATH, F0_SHA256, "F0 formula"),
        (R7_RESULT_PATH, R7_RESULT_SHA256, "R7 result"),
        (R7_MANIFEST_PATH, R7_MANIFEST_SHA256, "R7 manifest"),
        (R7_COMPLETE_PATH, R7_COMPLETE_SHA256, "R7 COMPLETE"),
    )
    for path, expected, label in expected_files:
        if file_sha256(path) != expected:
            raise F1Error(f"{label} bytes changed")
    matching_checkpoints = tuple(
        CHECKPOINT_PATH.parent.glob("lineage-2026092101-*-rung-003000.pt")
    )
    if matching_checkpoints != (CHECKPOINT_PATH,):
        raise F1Error("lineage 2026092101 rung-003000 checkpoint is ambiguous")

    manifest_lines = R7_MANIFEST_PATH.read_text(encoding="ascii").splitlines()
    if f"{R7_RESULT_SHA256}  result.json" not in manifest_lines:
        raise F1Error("sealed R7 manifest does not bind result.json")
    if R7_COMPLETE_PATH.read_text(encoding="ascii").split() != [
        R7_MANIFEST_SHA256,
        "MANIFEST.sha256",
    ]:
        raise F1Error("sealed R7 COMPLETE does not bind MANIFEST.sha256")

    authority = _load_json(AUTHORITY_PATH, field="Q1/Q2 authority")
    unsigned = dict(authority)
    seal = unsigned.pop("authority_sha256", None)
    if seal != AUTHORITY_BODY_SHA256 or canonical_sha256(unsigned) != seal:
        raise F1Error("Q1/Q2 authority body seal disagrees")
    if (
        authority.get("lineage") != LINEAGE
        or authority.get("q1_updates") != 10
        or authority.get("q2_initialization") != 2026108101
        or authority.get("q2_rungs") != [3, 10, 30, 100, 300, 1000, 3000]
        or authority.get("lambda_bits_per_j_hex") != LAMBDA_BITS_PER_J.hex()
        or authority.get("contract_sha256") != SOURCE_CONTRACT_SHA256
        or authority.get("repricing_contract_sha256") != REPRICING_CONTRACT_SHA256
        or authority.get("test_split_opened") is not False
        or authority.get("simulator_run") is not False
        or authority.get("episode_training") is not False
    ):
        raise F1Error("Q1/Q2 authority semantics drifted")

    r7 = _load_json(R7_RESULT_PATH, field="sealed R7 result")
    if (
        r7.get("integrity_status") != "VERIFIED"
        or r7.get("status") != "PASS_FINAL_INTEGRITY"
        or r7.get("c3_decision") != "STOP_PHYSICS_R7"
        or r7.get("no_rescue") is not True
        or r7.get("test_split_opened") is not False
    ):
        raise F1Error("sealed R7 result does not open the STOP_PHYSICS branch")
    return {
        "bindings": bindings.as_dict(),
        "authority": authority_bindings(),
        "formula_digests": formula_digests(),
    }


def expected_code_bindings() -> list[dict[str, str]]:
    rows = []
    for role, path in CODE_BINDING_PATHS:
        rows.append(
            {
                "role": role,
                "path": _repo_relative(path),
                "sha256": file_sha256(path),
            }
        )
    return rows


def validate_preflight_manifest(path: Path) -> tuple[dict[str, Any], str]:
    target = Path(path)
    payload = _load_json(target, field="F1 preflight manifest")
    if payload.get("schema") != PREFLIGHT_SCHEMA or payload.get("status") != "FROZEN_PREFLIGHT":
        raise F1Error("F1 preflight schema/status drifted")
    static = validate_static_bindings()
    expected = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": CLAIM_CEILING,
        **static,
        "code_files": expected_code_bindings(),
    }
    if payload != expected:
        raise F1Error("F1 preflight manifest disagrees with current exact bindings/code")
    digest = file_sha256(target)
    sidecar = target.with_suffix(".sha256")
    if sidecar.is_symlink() or not sidecar.is_file():
        raise F1Error("F1 preflight digest sidecar is missing or symlinked")
    if sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise F1Error("F1 preflight digest sidecar disagrees")
    return payload, digest


def _float_hex(value: object, *, field: str, nonnegative: bool = False) -> str:
    if isinstance(value, (bool, np.bool_)):
        raise F1Error(f"{field} must be finite")
    try:
        converted = float(value)
    except (TypeError, ValueError) as error:
        raise F1Error(f"{field} must be finite") from error
    if not math.isfinite(converted) or (nonnegative and converted < 0.0):
        raise F1Error(f"{field} must be finite{' and nonnegative' if nonnegative else ''}")
    return converted.hex()


def _hex_float(value: object, *, field: str, nonnegative: bool = False) -> float:
    if not isinstance(value, str):
        raise F1Error(f"{field} must be a hexadecimal float string")
    try:
        converted = float.fromhex(value)
    except ValueError as error:
        raise F1Error(f"{field} is not a hexadecimal float") from error
    if not math.isfinite(converted) or (nonnegative and converted < 0.0):
        raise F1Error(f"{field} is invalid")
    return converted


def _float_vector_payload(value: object, *, field: str, nonnegative: bool = False) -> list[str]:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 1 or not np.all(np.isfinite(array)):
        raise F1Error(f"{field} must be a finite vector")
    if nonnegative and np.any(array < 0.0):
        raise F1Error(f"{field} must be nonnegative")
    return [float(item).hex() for item in array.tolist()]


def profile_from_evaluation(evaluation: Any, *, interval_s: float) -> tuple[PhysicalProfile, np.ndarray]:
    try:
        resolution = evaluation.resolution
        radiating = evaluation.radiating
        link_power = np.asarray(evaluation.link_power_w, dtype=np.float64)
        profile = PhysicalProfile(
            link_rate_bps=np.asarray(evaluation.link_rate_bps, dtype=np.float64),
            served=np.asarray(resolution.served, dtype=np.bool_),
            serving_satellite=np.asarray(resolution.serving_satellite, dtype=np.int64),
            serving_cell=np.asarray(resolution.serving_cell, dtype=np.int64),
            active_beam_satellites=np.asarray(radiating.norad_ids, dtype=np.int64),
            active_beam_cells=np.asarray(radiating.cell_ids, dtype=np.int64),
            beam_power_w=np.asarray(radiating.power_w, dtype=np.float64),
            fixed_power_w=float(evaluation.fixed_power_w),
            system_power_w=float(evaluation.system_power_w),
            interval_s=float(interval_s),
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise F1Error("ActionEvaluation cannot form a complete PhysicalProfile") from error
    if link_power.shape != (profile.users,) or not np.all(np.isfinite(link_power)) or np.any(link_power < 0.0):
        raise F1Error("ActionEvaluation.link_power_w is not a nonnegative user vector")
    profile.verify_canonical_power()
    return profile, np.array(link_power, dtype=np.float64, copy=True)


def profile_to_payload(profile: PhysicalProfile, *, link_power_w: object | None = None) -> dict[str, object]:
    if not isinstance(profile, PhysicalProfile):
        raise F1Error("profile_to_payload requires PhysicalProfile")
    profile.verify_canonical_power()
    link_power = (
        np.zeros(profile.users, dtype=np.float64)
        if link_power_w is None
        else np.asarray(link_power_w, dtype=np.float64)
    )
    if link_power.shape != (profile.users,) or not np.all(np.isfinite(link_power)) or np.any(link_power < 0.0):
        raise F1Error("link_power_w must be a nonnegative user vector")
    active_beams = [
        {
            "serving_satellite": int(satellite),
            "serving_cell": int(cell),
            "link_power_w": float(power).hex(),
        }
        for satellite, cell, power in zip(
            profile.active_beam_satellites.tolist(),
            profile.active_beam_cells.tolist(),
            profile.beam_power_w.tolist(),
            strict=True,
        )
    ]
    return {
        "schema": F0_SCHEMA,
        "link_rate_bps": _float_vector_payload(profile.link_rate_bps, field="link_rate_bps", nonnegative=True),
        "link_power_w": _float_vector_payload(link_power, field="link_power_w", nonnegative=True),
        "served": [bool(value) for value in profile.served.tolist()],
        "serving_satellite": [int(value) for value in profile.serving_satellite.tolist()],
        "serving_cell": [int(value) for value in profile.serving_cell.tolist()],
        "active_beams": active_beams,
        "fixed_power_w": float(profile.fixed_power_w).hex(),
        "system_power_w": float(profile.system_power_w).hex(),
        "interval_s": float(profile.interval_s).hex(),
    }


def profile_from_payload(payload: object) -> PhysicalProfile:
    if not isinstance(payload, Mapping) or payload.get("schema") != F0_SCHEMA:
        raise F1Error("physical profile payload schema drifted")
    try:
        raw_served = payload["served"]
        raw_satellites = payload["serving_satellite"]
        raw_cells = payload["serving_cell"]
        if (
            not isinstance(raw_served, list)
            or any(type(value) is not bool for value in raw_served)
            or not isinstance(raw_satellites, list)
            or any(type(value) is not int for value in raw_satellites)
            or not isinstance(raw_cells, list)
            or any(type(value) is not int for value in raw_cells)
        ):
            raise F1Error("physical profile service arrays have non-canonical types")
        rates = np.asarray(
            [_hex_float(value, field="link_rate_bps", nonnegative=True) for value in payload["link_rate_bps"]],
            dtype=np.float64,
        )
        link_power = np.asarray(
            [_hex_float(value, field="link_power_w", nonnegative=True) for value in payload["link_power_w"]],
            dtype=np.float64,
        )
        served = np.asarray(raw_served, dtype=np.bool_)
        satellites = np.asarray(raw_satellites, dtype=np.int64)
        cells = np.asarray(raw_cells, dtype=np.int64)
        beams = payload["active_beams"]
    except (KeyError, TypeError, ValueError) as error:
        raise F1Error("physical profile payload arrays are malformed") from error
    if not isinstance(beams, list):
        raise F1Error("active_beams must be a list")
    beam_satellites: list[int] = []
    beam_cells: list[int] = []
    beam_power: list[float] = []
    for row in beams:
        if not isinstance(row, Mapping):
            raise F1Error("active beam row must be an object")
        if type(row.get("serving_satellite")) is not int or type(row.get("serving_cell")) is not int:
            raise F1Error("active beam identity must use exact integers")
        beam_satellites.append(row["serving_satellite"])
        beam_cells.append(row["serving_cell"])
        beam_power.append(_hex_float(row.get("link_power_w"), field="beam link_power_w", nonnegative=True))
    profile = PhysicalProfile(
        link_rate_bps=rates,
        served=served,
        serving_satellite=satellites,
        serving_cell=cells,
        active_beam_satellites=np.asarray(beam_satellites, dtype=np.int64),
        active_beam_cells=np.asarray(beam_cells, dtype=np.int64),
        beam_power_w=np.asarray(beam_power, dtype=np.float64),
        fixed_power_w=_hex_float(payload.get("fixed_power_w"), field="fixed_power_w", nonnegative=True),
        system_power_w=_hex_float(payload.get("system_power_w"), field="system_power_w", nonnegative=True),
        interval_s=_hex_float(payload.get("interval_s"), field="interval_s", nonnegative=True),
    )
    if link_power.shape != (profile.users,):
        raise F1Error("profile link_power_w length disagrees with users")
    profile.verify_canonical_power()
    return profile


def _physical_key(table: Any, action: int) -> tuple[int, int] | None:
    if action == NO_OP_ACTION:
        return None
    association = table.association(action)
    if not isinstance(association, Association):
        return None
    return int(association.norad_id), int(association.cell_id)


def enumerate_unilateral_candidates(observation: Any, reference_actions: object) -> tuple[dict[str, object], ...]:
    reference = np.asarray(reference_actions)
    tables = tuple(observation.candidates.slot_tables)
    if reference.dtype.kind not in "iu" or reference.shape != (len(tables),):
        raise F1Error("reference action vector is malformed")
    rows: list[dict[str, object]] = []
    for focal_user, table in enumerate(tables):
        mask = np.asarray(table.mask)
        if mask.dtype != np.bool_ or mask.shape != (NUM_ACTIONS,):
            raise F1Error("unilateral legality mask is not Boolean width 28")
        reference_action = int(reference[focal_user])
        if not 0 <= reference_action < NUM_ACTIONS or not bool(mask[reference_action]):
            raise F1Error("reference action is not legal under the current mask")
        reference_key = _physical_key(table, reference_action)
        seen: set[tuple[int, int]] = set()
        for candidate_action in np.flatnonzero(mask).tolist():
            action = int(candidate_action)
            key = _physical_key(table, action)
            if key is None or key == reference_key:
                continue
            if key in seen:
                raise F1Error("two legal action slots alias one candidate physical configuration")
            seen.add(key)
            candidate = np.array(reference, dtype=np.int64, copy=True)
            candidate[focal_user] = action
            rows.append(
                {
                    "focal_user": focal_user,
                    "reference_action": reference_action,
                    "candidate_action": action,
                    "reference_physical_key": None if reference_key is None else list(reference_key),
                    "candidate_physical_key": list(key),
                    "candidate_joint_actions": [int(value) for value in candidate.tolist()],
                }
            )
    return tuple(rows)


def action_physical_keys(observation: Any) -> list[list[list[int] | None]]:
    """Materialize the SlotTable physical identity behind every action slot."""

    result: list[list[list[int] | None]] = []
    for table in tuple(observation.candidates.slot_tables):
        mask = np.asarray(table.mask)
        if mask.dtype != np.bool_ or mask.shape != (NUM_ACTIONS,):
            raise F1Error("action physical-key table has a malformed legality mask")
        result.append(
            [
                None
                if not bool(mask[action]) or _physical_key(table, action) is None
                else list(_physical_key(table, action) or ())
                for action in range(NUM_ACTIONS)
            ]
        )
    return result


def masked_argmax_q12_plus_z(q12: object, z: object, action_masks: object) -> np.ndarray:
    values = np.asarray(q12, dtype=np.float64)
    target = np.asarray(z, dtype=np.float64)
    masks = np.asarray(action_masks)
    if values.ndim != 2 or values.shape[1] != NUM_ACTIONS or target.shape != values.shape:
        raise F1Error("Q1+Q2 and z surfaces must share shape (U,28)")
    if masks.dtype != np.bool_ or masks.shape != values.shape:
        raise F1Error("deployment mask must be a Boolean Q-surface mask")
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(target)) or not np.all(np.any(masks, axis=1)):
        raise F1Error("deployment surface is non-finite or unselectable")
    return np.argmax(np.where(masks, values + target, -np.inf), axis=1).astype(np.int64)


def _hex_matrix(value: object, *, field: str) -> list[list[str]]:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 2 or not np.all(np.isfinite(array)):
        raise F1Error(f"{field} must be a finite matrix")
    return [[float(item).hex() for item in row] for row in array.tolist()]


def _matrix_from_hex(value: object, *, field: str) -> np.ndarray:
    if not isinstance(value, list) or not value or any(not isinstance(row, list) for row in value):
        raise F1Error(f"{field} must be a nonempty matrix")
    try:
        array = np.asarray(
            [[_hex_float(item, field=field) for item in row] for row in value],
            dtype=np.float64,
        )
    except ValueError as error:
        raise F1Error(f"{field} rows are ragged") from error
    if array.ndim != 2 or not np.all(np.isfinite(array)):
        raise F1Error(f"{field} matrix is malformed")
    return array


def target_surfaces_from_step(step: Mapping[str, object]) -> tuple[np.ndarray, np.ndarray]:
    reference = profile_from_payload(step.get("reference_profile"))
    masks = np.asarray(step.get("action_masks"))
    actions = np.asarray(step.get("reference_actions"))
    if masks.dtype != np.bool_ or masks.shape != (reference.users, NUM_ACTIONS):
        raise F1Error("step action masks are malformed")
    if actions.dtype.kind not in "iu" or actions.shape != (reference.users,):
        raise F1Error("step reference actions are malformed")
    d = np.zeros(masks.shape, dtype=np.float64)
    f = np.zeros(masks.shape, dtype=np.float64)
    covered = {(user, int(actions[user])) for user in range(reference.users)}
    physical_keys = step.get("action_physical_keys")
    if (
        not isinstance(physical_keys, list)
        or len(physical_keys) != reference.users
        or any(not isinstance(row, list) or len(row) != NUM_ACTIONS for row in physical_keys)
    ):
        raise F1Error("step action physical-key table is malformed")
    candidates = step.get("unilateral_candidates")
    if not isinstance(candidates, list):
        raise F1Error("step unilateral candidates must be a list")
    for row in candidates:
        if not isinstance(row, Mapping):
            raise F1Error("unilateral candidate row is malformed")
        focal = row.get("focal_user")
        action = row.get("candidate_action")
        if type(focal) is not int or type(action) is not int:
            raise F1Error("unilateral candidate indices must be exact integers")
        key = (focal, action)
        if key in covered or not 0 <= focal < reference.users or not 0 <= action < NUM_ACTIONS or not bool(masks[focal, action]):
            raise F1Error("unilateral candidate is duplicate, out of range, or illegal")
        candidate_joint = np.asarray(row.get("candidate_joint_actions"))
        if candidate_joint.dtype.kind not in "iu" or candidate_joint.shape != actions.shape:
            raise F1Error("candidate joint action vector is malformed")
        if np.flatnonzero(candidate_joint != actions).tolist() != [focal] or int(candidate_joint[focal]) != action:
            raise F1Error("candidate joint action is not one legal focal mutation")
        raw_candidate_key = row.get("candidate_physical_key")
        if raw_candidate_key != physical_keys[focal][action]:
            raise F1Error("candidate physical key disagrees with the SlotTable identity")
        reference_action = int(actions[focal])
        if row.get("reference_physical_key") != physical_keys[focal][reference_action]:
            raise F1Error("reference physical key disagrees with the SlotTable identity")
        candidate = profile_from_payload(row.get("profile"))
        targets = compute_c3_targets(
            reference,
            candidate,
            focal_user=focal,
            lambda_bits_per_j=LAMBDA_BITS_PER_J,
        )
        d[focal, action] = targets.d_bits
        f[focal, action] = targets.f_bits
        covered.add(key)
    expected = {(user, int(actions[user])) for user in range(reference.users)}
    for user in range(reference.users):
        reference_key = physical_keys[user][int(actions[user])]
        seen_keys: set[tuple[int, int]] = set()
        for action in np.flatnonzero(masks[user]).tolist():
            raw_key = physical_keys[user][int(action)]
            if raw_key is None or raw_key == reference_key:
                continue
            if not isinstance(raw_key, list) or len(raw_key) != 2 or any(type(value) is not int for value in raw_key):
                raise F1Error("action physical key must be [satellite, cell] or null")
            key_tuple = (raw_key[0], raw_key[1])
            if key_tuple in seen_keys:
                raise F1Error("two legal action slots alias one candidate physical configuration")
            seen_keys.add(key_tuple)
            expected.add((user, int(action)))
    if covered != expected:
        raise F1Error("unilateral tape does not cover every legal action exactly once")
    return d, f


def build_step_payload(
    *,
    step_index: int,
    q12: object,
    action_masks: object,
    reference_actions: object,
    reference_profile: PhysicalProfile,
    reference_link_power_w: object,
    candidates: Sequence[Mapping[str, object]],
    deployment_actions: Mapping[str, object],
    deployment_profiles: Mapping[str, tuple[PhysicalProfile, object]],
    state_sha256: str,
    action_physical_key_table: Sequence[Sequence[Sequence[int] | None]],
) -> dict[str, object]:
    if type(step_index) is not int or step_index not in CANONICAL_STEP_INDICES:
        raise F1Error("step payload index is outside the two canonical steps")
    masks = np.asarray(action_masks)
    actions = np.asarray(reference_actions)
    q = np.asarray(q12, dtype=np.float64)
    if masks.dtype != np.bool_ or masks.shape != (reference_profile.users, NUM_ACTIONS):
        raise F1Error("step masks are malformed")
    if actions.dtype.kind not in "iu" or actions.shape != (reference_profile.users,):
        raise F1Error("step reference actions are malformed")
    if q.shape != masks.shape or not np.all(np.isfinite(q)):
        raise F1Error("step Q1+Q2 surface is malformed")
    _digest(state_sha256, field="state_sha256")
    rows = []
    for candidate in candidates:
        row = dict(candidate)
        profile = row.pop("profile", None)
        link_power = row.pop("link_power_w", None)
        if not isinstance(profile, PhysicalProfile):
            raise F1Error("candidate row lacks a PhysicalProfile")
        row["profile"] = profile_to_payload(profile, link_power_w=link_power)
        rows.append(row)
    deployments: dict[str, object] = {}
    for name in ("D", "F"):
        if name not in deployment_actions or name not in deployment_profiles:
            raise F1Error("both D and F deployment profiles are required")
        profile, link_power = deployment_profiles[name]
        deployments[name] = {
            "actions": [int(value) for value in np.asarray(deployment_actions[name]).tolist()],
            "profile": profile_to_payload(profile, link_power_w=link_power),
        }
    return {
        "step_index": step_index,
        "state_sha256": state_sha256,
        "q12": _hex_matrix(q, field="q12"),
        "action_masks": [[bool(item) for item in row] for row in masks.tolist()],
        "action_physical_keys": [
            [None if key is None else [int(key[0]), int(key[1])] for key in row]
            for row in action_physical_key_table
        ],
        "reference_actions": [int(value) for value in actions.tolist()],
        "reference_profile": profile_to_payload(reference_profile, link_power_w=reference_link_power_w),
        "unilateral_candidates": rows,
        "deployments": deployments,
    }


def build_tape_payload(
    steps: Sequence[Mapping[str, object]],
    *,
    q1_parameter_sha256: str,
    q2_parameter_sha256: str,
    preflight_manifest_sha256: str,
) -> dict[str, object]:
    return {
        "schema": TAPE_SCHEMA,
        "status": "COMPLETE_IMMUTABLE_TAPE",
        "claim_ceiling": CLAIM_CEILING,
        "bindings": F1Bindings().as_dict(),
        "authority": authority_bindings(),
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": _digest(preflight_manifest_sha256, field="preflight_manifest_sha256"),
        "q1_parameter_sha256": _digest(q1_parameter_sha256, field="q1_parameter_sha256"),
        "q2_parameter_sha256": _digest(q2_parameter_sha256, field="q2_parameter_sha256"),
        "steps": [dict(step) for step in steps],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def verify_tape_payload(tape: Mapping[str, object]) -> dict[str, tuple[np.ndarray, ...]]:
    if tape.get("schema") != TAPE_SCHEMA or tape.get("status") != "COMPLETE_IMMUTABLE_TAPE":
        raise F1Error("physical tape schema/status drifted")
    if tape.get("claim_ceiling") != CLAIM_CEILING:
        raise F1Error("physical tape claim ceiling drifted")
    if tape.get("bindings") != F1Bindings().as_dict() or tape.get("authority") != authority_bindings():
        raise F1Error("physical tape binding drifted")
    if tape.get("formula_digests") != formula_digests():
        raise F1Error("physical tape formula digest drifted")
    for field in ("preflight_manifest_sha256", "q1_parameter_sha256", "q2_parameter_sha256"):
        _digest(tape.get(field), field=field)
    if any(tape.get(field) is not False for field in ("test_split_opened", "episode_training", "learner_update", "efficacy_claim")):
        raise F1Error("physical tape crossed a forbidden boundary")
    steps = tape.get("steps")
    if not isinstance(steps, list) or [row.get("step_index") for row in steps if isinstance(row, Mapping)] != list(CANONICAL_STEP_INDICES):
        raise F1Error("physical tape does not contain exactly canonical steps 0 and 1")
    selected: dict[str, list[np.ndarray]] = {"BASE": [], "D": [], "F": []}
    targets_by_name: dict[str, list[np.ndarray]] = {"D": [], "F": []}
    for step in steps:
        if not isinstance(step, Mapping):
            raise F1Error("physical tape step is malformed")
        q12 = _matrix_from_hex(step.get("q12"), field="q12")
        masks = np.asarray(step.get("action_masks"))
        reference = np.asarray(step.get("reference_actions"))
        profile = profile_from_payload(step.get("reference_profile"))
        if q12.shape != (profile.users, NUM_ACTIONS) or masks.dtype != np.bool_ or masks.shape != q12.shape:
            raise F1Error("step Q/mask/profile dimensions disagree")
        if reference.dtype.kind not in "iu" or reference.shape != (profile.users,):
            raise F1Error("step reference action vector is malformed")
        base = masked_argmax_q12_plus_z(q12, np.zeros_like(q12), masks)
        if not np.array_equal(base, reference):
            raise F1Error("BASE is not the masked Q1+Q2 argmax")
        d, f = target_surfaces_from_step(step)
        deployments = step.get("deployments")
        if not isinstance(deployments, Mapping):
            raise F1Error("step deployment map is malformed")
        selected["BASE"].append(base)
        for name, z in (("D", d), ("F", f)):
            expected = masked_argmax_q12_plus_z(q12, z, masks)
            row = deployments.get(name)
            if not isinstance(row, Mapping):
                raise F1Error(f"step lacks {name} deployment")
            observed = np.asarray(row.get("actions"))
            if observed.dtype.kind not in "iu" or not np.array_equal(observed, expected):
                raise F1Error(f"{name} deployment is not masked Q1+Q2+z argmax")
            profile_from_payload(row.get("profile"))
            selected[name].append(expected)
            targets_by_name[name].append(z)
    return {
        "BASE": tuple(selected["BASE"]),
        "D": tuple(selected["D"]),
        "F": tuple(selected["F"]),
        "D_targets": tuple(targets_by_name["D"]),
        "F_targets": tuple(targets_by_name["F"]),
    }


def _write_once(path: Path, payload: Mapping[str, object], *, readonly: bool = True) -> str:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise F1Error(f"refusing to overwrite write-once artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    with target.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    if readonly:
        target.chmod(0o444)
    return hashlib.sha256(encoded).hexdigest()


def write_tape_bundle(output: Path, tape: Mapping[str, object]) -> tuple[Path, Path, str]:
    verify_tape_payload(tape)
    root = Path(output)
    if root.is_symlink():
        raise F1Error("output directory must not be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    tape_path = root / DEFAULT_TAPE_NAME
    manifest_path = root / DEFAULT_TAPE_MANIFEST_NAME
    tape_sha = _write_once(tape_path, tape)
    manifest = {
        "schema": TAPE_MANIFEST_SCHEMA,
        "status": "COMPLETE_IMMUTABLE_TAPE",
        "claim_ceiling": CLAIM_CEILING,
        "bindings": F1Bindings().as_dict(),
        "tape": {
            "path": tape_path.name,
            "sha256": tape_sha,
            "bytes": tape_path.stat().st_size,
            "mode": "0444",
        },
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": tape["preflight_manifest_sha256"],
    }
    _write_once(manifest_path, manifest)
    return tape_path, manifest_path, tape_sha


def read_tape_bundle(tape_path: Path, manifest_path: Path) -> dict[str, Any]:
    tape = _load_json(tape_path, field="physical unilateral tape")
    manifest = _load_json(manifest_path, field="physical tape manifest")
    if manifest.get("schema") != TAPE_MANIFEST_SCHEMA or manifest.get("status") != "COMPLETE_IMMUTABLE_TAPE":
        raise F1Error("physical tape manifest schema/status drifted")
    record = manifest.get("tape")
    if not isinstance(record, Mapping):
        raise F1Error("physical tape manifest lacks tape binding")
    if record.get("path") != Path(tape_path).name or record.get("sha256") != file_sha256(tape_path):
        raise F1Error("physical tape manifest digest disagrees")
    if record.get("bytes") != Path(tape_path).stat().st_size or record.get("mode") != "0444":
        raise F1Error("physical tape manifest size/mode declaration drifted")
    if Path(tape_path).stat().st_mode & 0o222 or Path(manifest_path).stat().st_mode & 0o222:
        raise F1Error("physical tape or manifest is writable")
    if manifest.get("bindings") != F1Bindings().as_dict() or manifest.get("formula_digests") != formula_digests():
        raise F1Error("physical tape manifest bindings drifted")
    verify_tape_payload(tape)
    return tape


def _profile_metrics(profiles: Sequence[PhysicalProfile]) -> dict[str, float | int]:
    if len(profiles) != STEP_COUNT:
        raise F1Error("pooled metric requires exactly two step profiles")
    total_bits = math.fsum(
        profile.interval_s * math.fsum(float(value) for value in profile.link_rate_bps)
        for profile in profiles
    )
    total_energy = math.fsum(profile.network_energy_j for profile in profiles)
    served = sum(int(np.count_nonzero(profile.served)) for profile in profiles)
    opportunities = sum(profile.users for profile in profiles)
    if not math.isfinite(total_bits) or total_bits < 0.0 or not math.isfinite(total_energy) or total_energy <= 0.0:
        raise F1Error("pooled bits/energy are invalid")
    return {
        "total_bits": total_bits,
        "total_energy_j": total_energy,
        "ratio_of_sums_ee_bits_per_j": total_bits / total_energy,
        "served_user_steps": served,
        "service_opportunities": opportunities,
        "service_fraction": served / opportunities,
    }


def evaluate_kill_rules(
    *,
    base_metrics: Mapping[str, object],
    candidate_metrics: Mapping[str, object],
    action_changed: bool,
    integrity_ok: bool,
) -> dict[str, bool]:
    try:
        base_service = float(base_metrics["service_fraction"])
        candidate_service = float(candidate_metrics["service_fraction"])
        base_ee = float(base_metrics["ratio_of_sums_ee_bits_per_j"])
        candidate_ee = float(candidate_metrics["ratio_of_sums_ee_bits_per_j"])
    except (KeyError, TypeError, ValueError) as error:
        raise F1Error("kill-rule metrics are incomplete") from error
    finite = all(math.isfinite(value) for value in (base_service, candidate_service, base_ee, candidate_ee))
    service_ok = finite and candidate_service >= base_service - SERVICE_MARGIN
    ee_ok = finite and candidate_ee > base_ee
    mutation_ok = action_changed is True
    integrity = integrity_ok is True and finite
    return {
        "integrity": integrity,
        "action_changed": mutation_ok,
        "service_noninferior": service_ok,
        "ee_strictly_above_base": ee_ok,
        "survives": integrity and mutation_ok and service_ok and ee_ok,
    }


def adjudicate_outcome(rules: Mapping[str, Mapping[str, object]], *, integrity_ok: bool = True) -> str:
    """Apply the frozen D-before-F outcome order without score comparison."""

    if integrity_ok is not True:
        return "INVALID_RUN"
    if set(rules) != {"D", "F"}:
        raise F1Error("adjudication requires exactly D and F rule bundles")
    if rules["D"].get("survives") is True:
        return "F1_SURVIVES_D"
    if rules["F"].get("survives") is True:
        return "F1_SURVIVES_F"
    return "FAST_SCREEN_NO_SUPPORT"


def screen_tape(tape: Mapping[str, object], *, tape_sha256: str) -> dict[str, object]:
    selected = verify_tape_payload(tape)
    steps = tape["steps"]
    assert isinstance(steps, list)
    profiles: dict[str, list[PhysicalProfile]] = {"BASE": [], "D": [], "F": []}
    for step in steps:
        assert isinstance(step, Mapping)
        profiles["BASE"].append(profile_from_payload(step["reference_profile"]))
        deployments = step["deployments"]
        assert isinstance(deployments, Mapping)
        for name in ("D", "F"):
            row = deployments[name]
            assert isinstance(row, Mapping)
            profiles[name].append(profile_from_payload(row["profile"]))
    metrics = {name: _profile_metrics(rows) for name, rows in profiles.items()}
    rules: dict[str, dict[str, bool]] = {}
    for name in ("D", "F"):
        changed = any(
            not np.array_equal(candidate, base)
            for candidate, base in zip(selected[name], selected["BASE"], strict=True)
        )
        rules[name] = evaluate_kill_rules(
            base_metrics=metrics["BASE"],
            candidate_metrics=metrics[name],
            action_changed=changed,
            integrity_ok=True,
        )
    outcome = adjudicate_outcome(rules)
    return {
        "schema": RECEIPT_SCHEMA,
        "status": "COMPLETE",
        "outcome": outcome,
        "claim_ceiling": CLAIM_CEILING,
        "bindings": F1Bindings().as_dict(),
        "authority": authority_bindings(),
        "formula_digests": formula_digests(),
        "tape_sha256": _digest(tape_sha256, field="tape_sha256"),
        "preflight_manifest_sha256": tape["preflight_manifest_sha256"],
        "metrics": metrics,
        "kill_rules": rules,
        "priority_applied": ["D", "F"],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def invalid_run_receipt(
    *,
    error: BaseException,
    preflight_manifest_sha256: str,
    tape_sha256: str | None,
) -> dict[str, object]:
    """Return an honest fail-closed receipt after an authorized run starts."""

    return {
        "schema": RECEIPT_SCHEMA,
        "status": "INVALID_RUN",
        "outcome": "INVALID_RUN",
        "claim_ceiling": CLAIM_CEILING,
        "bindings": F1Bindings().as_dict(),
        "authority": authority_bindings(),
        "formula_digests": formula_digests(),
        "tape_sha256": None if tape_sha256 is None else _digest(tape_sha256, field="tape_sha256"),
        "tape_complete": tape_sha256 is not None,
        "preflight_manifest_sha256": _digest(
            preflight_manifest_sha256, field="preflight_manifest_sha256"
        ),
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(str(error).encode("utf-8")).hexdigest(),
        "metrics": None,
        "kill_rules": None,
        "priority_applied": ["D", "F"],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def _validate_launch_authority(path: Path, *, preflight_sha256: str) -> dict[str, Any]:
    payload = _load_json(path, field="F1 launch authority")
    expected = {
        "schema": LAUNCH_AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": CLAIM_CEILING,
        "preflight_manifest": {
            "path": _repo_relative(DEFAULT_PREFLIGHT),
            "sha256": preflight_sha256,
        },
        "bindings": F1Bindings().as_dict(),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    if payload != expected:
        raise F1Error("launch authority does not pin the exact F1 preflight/bindings")
    return payload


def _runtime_modules() -> tuple[Any, Any]:
    for path in (PHYSICAL_DIR,):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    try:
        import run_v023_dropc3_evaluation_server as server
        import v023_physical_episode_runner as physical
    except ImportError as error:
        raise F1Error("canonical physical runtime modules cannot be imported") from error
    return physical, server


def _q12_surface(physical: Any, frozen: Any, step_env: Any, observation: Any) -> tuple[Any, np.ndarray, np.ndarray]:
    from mcrl.runtime.ee_axis_ops3_live import (
        build_ops3_live_surfaces,
        project_ops3_anchor,
        snapshot_ops3_anchor,
    )
    from mcrl.runtime.ee_axis_state import encode_ee_axis_state
    from mcrl.runtime.ee_axis_v014_q2_state import encode_ee_axis_v014_q2_states

    native = encode_ee_axis_state(step_env, observation)
    native.verify()
    masks = np.asarray(native.action_masks, dtype=np.bool_)
    q1 = physical._surface(frozen.q1, native.state_matrix, masks, field="Q1")
    q1_reference = physical._masked_argmax(q1, masks)
    anchor = snapshot_ops3_anchor(step_env, observation)
    projection = project_ops3_anchor(anchor)
    surfaces = build_ops3_live_surfaces(anchor, projection, q1_reference)
    q2_state = encode_ee_axis_v014_q2_states(surfaces)
    q2_state.verify()
    if not np.array_equal(q2_state.action_masks, masks):
        raise F1Error("Q2 carrier mask differs from native mask")
    q2 = physical._surface(frozen.q2, q2_state.state_matrix, masks, field="Q2")
    # Match the R7 DetachedQ12Snapshot precision exactly.
    q12 = np.asarray(np.asarray(q1, dtype=np.float32) + np.asarray(q2, dtype=np.float32), dtype=np.float32)
    reference = physical._masked_argmax(q12, masks)
    return native, q12, reference


def _generate_physical_tape(*, tle_root: Path, preflight_sha256: str) -> dict[str, object]:
    physical, server = _runtime_modules()
    static = validate_static_bindings()
    del static
    from mcrl.runtime.prereg import read_prereg
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    record = read_prereg(PREREG_PATH)
    if record.digest != PREREG_RECORD_DIGEST:
        raise F1Error("TRAIN PREREG record digest changed")
    frozen = physical.load_v020_q12()
    if frozen.binding.lineage != LINEAGE or frozen.binding.checkpoint_sha256 != CHECKPOINT_SHA256:
        raise F1Error("loaded Q1/Q2 bundle is not the bound lineage/checkpoint")
    q1_before = frozen.q1_parameter_sha256
    q2_before = frozen.q2_parameter_sha256
    field = KeyedFadingField.from_components(FIELD_COMPONENT, WORLD)
    with tempfile.TemporaryDirectory(prefix="mcrl-v023-c3-f1-tle-") as temporary:
        archive = server._freeze_archive(record, Path(tle_root), Path(temporary) / "frozen", physical)
        environment = server._make_environment(archive)
        step_env = environment.environment
        if getattr(step_env, "_started", False):
            raise F1Error("environment started before common keyed field binding")
        step_env._fading_field = field
        rngs = tuple(_evaluation_rngs(WORLD))
        if len(rngs) < 2:
            raise F1Error("canonical RNG factory did not return environment/mobility streams")
        _states, _masks, observation = environment.reset(rngs[0], rngs[1])
        interval_s = float(step_env.driver.config.ephemeris.time_step_s)
        if not math.isfinite(interval_s) or interval_s <= 0.0:
            raise F1Error("canonical decision interval is invalid")
        steps: list[dict[str, object]] = []
        for step_index in CANONICAL_STEP_INDICES:
            if int(observation.step_index) != step_index:
                raise F1Error("canonical replay reached the wrong step")
            native, q12, reference = _q12_surface(physical, frozen, step_env, observation)
            masks = np.asarray(native.action_masks, dtype=np.bool_)
            reference_eval = step_env.evaluate_actions(reference, rngs[0])
            reference_profile, reference_link_power = profile_from_evaluation(
                reference_eval, interval_s=interval_s
            )
            skeletons = enumerate_unilateral_candidates(observation, reference)
            candidate_rows: list[dict[str, object]] = []
            d = np.zeros_like(np.asarray(q12, dtype=np.float64))
            f = np.zeros_like(d)
            for skeleton in skeletons:
                candidate_actions = np.asarray(skeleton["candidate_joint_actions"], dtype=np.int64)
                evaluation = step_env.evaluate_actions(candidate_actions, rngs[0])
                candidate_profile, link_power = profile_from_evaluation(evaluation, interval_s=interval_s)
                focal = int(skeleton["focal_user"])
                action = int(skeleton["candidate_action"])
                target = compute_c3_targets(
                    reference_profile,
                    candidate_profile,
                    focal_user=focal,
                    lambda_bits_per_j=LAMBDA_BITS_PER_J,
                )
                d[focal, action] = target.d_bits
                f[focal, action] = target.f_bits
                candidate_rows.append(
                    {**skeleton, "profile": candidate_profile, "link_power_w": link_power}
                )
            selected = {
                "D": masked_argmax_q12_plus_z(q12, d, masks),
                "F": masked_argmax_q12_plus_z(q12, f, masks),
            }
            cache: dict[tuple[int, ...], tuple[PhysicalProfile, np.ndarray]] = {
                tuple(int(value) for value in reference.tolist()): (reference_profile, reference_link_power)
            }
            deployment_profiles: dict[str, tuple[PhysicalProfile, np.ndarray]] = {}
            for name in ("D", "F"):
                key = tuple(int(value) for value in selected[name].tolist())
                if key not in cache:
                    evaluation = step_env.evaluate_actions(selected[name], rngs[0])
                    cache[key] = profile_from_evaluation(evaluation, interval_s=interval_s)
                deployment_profiles[name] = cache[key]
            step_payload = build_step_payload(
                step_index=step_index,
                q12=q12,
                action_masks=masks,
                reference_actions=reference,
                reference_profile=reference_profile,
                reference_link_power_w=reference_link_power,
                candidates=candidate_rows,
                deployment_actions=selected,
                deployment_profiles=deployment_profiles,
                state_sha256=native.state_sha256,
                action_physical_key_table=action_physical_keys(observation),
            )
            # Recompute targets from the serializable tape surface before any
            # committed advance; this catches writer/reader formula drift.
            rd, rf = target_surfaces_from_step(step_payload)
            if not np.array_equal(rd, d) or not np.array_equal(rf, f):
                raise F1Error("serialized unilateral tape changed D/F targets")
            environment.step(reference, rngs[0])
            committed = environment.last_outcome
            committed_profile, committed_link_power = profile_from_evaluation(
                committed, interval_s=interval_s
            )
            if profile_to_payload(committed_profile, link_power_w=committed_link_power) != step_payload["reference_profile"]:
                raise F1Error("BASE counterfactual evaluation disagrees with committed reference step")
            if step_index < CANONICAL_STEP_INDICES[-1]:
                if bool(committed.done):
                    raise F1Error("canonical episode terminated before step 1")
                observation = committed.observation
            steps.append(step_payload)
    q1_after = physical._parameter_sha256(frozen.q1)
    q2_after = physical._parameter_sha256(frozen.q2)
    if q1_after != q1_before or q2_after != q2_before:
        raise F1Error("frozen Q1/Q2 parameters changed during F1 inference")
    tape = build_tape_payload(
        steps,
        q1_parameter_sha256=q1_before,
        q2_parameter_sha256=q2_before,
        preflight_manifest_sha256=preflight_sha256,
    )
    verify_tape_payload(tape)
    return tape


def run(args: argparse.Namespace) -> dict[str, Path]:
    _manifest, preflight_sha = validate_preflight_manifest(Path(args.preflight_manifest))
    if args.dry_run:
        return {"preflight": Path(args.preflight_manifest)}
    if args.launch_authority is None or args.tle_root is None or args.output is None:
        raise F1Error("real F1 execution requires --launch-authority, --tle-root, and --output")
    _validate_launch_authority(Path(args.launch_authority), preflight_sha256=preflight_sha)
    output = Path(args.output)
    if output.exists() and (output.is_symlink() or not output.is_dir() or any(output.iterdir())):
        raise F1Error("real F1 output must be a fresh absent or empty regular directory")
    output.mkdir(parents=True, exist_ok=True)
    tape_path = output / DEFAULT_TAPE_NAME
    manifest_path = output / DEFAULT_TAPE_MANIFEST_NAME
    receipt_path = output / DEFAULT_RECEIPT_NAME
    tape_sha: str | None = None
    try:
        tape = _generate_physical_tape(tle_root=Path(args.tle_root), preflight_sha256=preflight_sha)
        tape_path, manifest_path, tape_sha = write_tape_bundle(output, tape)
        reopened = read_tape_bundle(tape_path, manifest_path)
        receipt = screen_tape(reopened, tape_sha256=tape_sha)
        _write_once(receipt_path, receipt)
    except Exception as error:
        if tape_path.is_file():
            tape_sha = file_sha256(tape_path)
        if not receipt_path.exists() and not receipt_path.is_symlink():
            _write_once(
                receipt_path,
                invalid_run_receipt(
                    error=error,
                    preflight_manifest_sha256=preflight_sha,
                    tape_sha256=tape_sha,
                ),
            )
        raise
    return {"tape": tape_path, "tape_manifest": manifest_path, "receipt": receipt_path}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preflight-manifest", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--tle-root", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        paths = run(args)
    except Exception as error:
        print(f"F1_ERROR: {error}", file=sys.stderr)
        traceback.print_exception(error, file=sys.stderr)
        return 2
    if args.dry_run:
        print(f"F1_DRY_RUN_PASS preflight={paths['preflight']}")
    else:
        print(
            "F1_PASS "
            f"tape={paths['tape']} tape_manifest={paths['tape_manifest']} receipt={paths['receipt']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
