#!/usr/bin/env python3
"""C-C exact-primary-tie network-energy selector over immutable E1 tapes."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
E1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-existence-e1"
if str(E1_DIR) not in sys.path:
    sys.path.insert(0, str(E1_DIR))

import run_v023_c3_existence_e1 as e1  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v023-c3-candidate-cc-v1"
PREFLIGHT_SCHEMA = f"{SCHEMA}-preflight-manifest"
LAUNCH_AUTHORITY_SCHEMA = f"{SCHEMA}-launch-authority"
UNIT_RECEIPT_SCHEMA = f"{SCHEMA}-unit-receipt"
TERMINAL_RECEIPT_SCHEMA = f"{SCHEMA}-terminal-receipt"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_C3_CANDIDATE_CC_FAST_SCREEN_NO_LEARNER_NO_EFFICACY_NO_TEST"
)

CONTRACT_PATH = E1_DIR / "candidates" / "V023-C3-CANDIDATE-C-CONTRACT-2026-09-08.md"
CONTRACT_SIDECAR = Path(f"{CONTRACT_PATH}.sha256")
DEFAULT_PREFLIGHT = HERE / "CC-PREFLIGHT-MANIFEST.json"
DEFAULT_OUTPUT = HERE / "run-output"
DEFAULT_TERMINAL = "terminal-receipt.json"
DEFAULT_UNIT_RECEIPT = "receipt.json"
E1_TERMINAL = "terminal-receipt.json"
E1_TAPE = "e1-physical-tape.json"
E1_MANIFEST = "e1-physical-tape.manifest.json"
E1_RECEIPT = "receipt.json"
JQ = Path("/usr/bin/jq")
STEPS = (0, 1)
USERS = 100
NUM_ACTIONS = 28
OPPORTUNITIES = len(e1.ALL_UNITS) * len(STEPS) * USERS
SERVICE_MARGIN = Fraction(1, 1000)
OUTCOMES = ("C_C_FAST_SCREEN_SUPPORT", "C_C_FAST_SCREEN_NO_SUPPORT")
REASONS = (
    "NO_EXACT_TIE_EXPOSURE",
    "NO_LEGAL_CHANGE",
    "EE_NOT_ABOVE_BASE",
    "SERVICE_NONINFERIORITY_FAILED",
)
AUTHORITY_KEYS = {
    "schema", "status", "claim_ceiling", "preflight_manifest", "contract",
    "e1_input", "code_files", "output_root", "launch_arguments",
    "test_split_opened", "episode_training", "learner_update", "efficacy_claim",
}


class CCError(RuntimeError):
    """A C-C contract, authority, tape, or receipt failed closed."""


def pin_single_thread_runtime() -> None:
    """Use the E1 runner's required Torch pin before any inter-op work."""

    try:
        e1.pin_single_thread_runtime()
    except e1.E1Error as error:
        raise CCError(str(error)) from error


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as error:
        raise CCError("artifact is not canonical finite JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str) or len(value) != 64 or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CCError(f"{field} must be a lowercase SHA-256")
    return value


def _load_json(path: Path, *, field: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise CCError(f"{field} is missing or symlinked")
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CCError(f"{field} is not valid JSON") from error
    if not isinstance(value, dict):
        raise CCError(f"{field} must be a JSON object")
    return value


def _mode_0444(path: Path, *, field: str) -> None:
    target = Path(path)
    if target.is_symlink() or not target.is_file() or target.stat().st_mode & 0o777 != 0o444:
        raise CCError(f"{field} must be a regular mode-0444 file")


def _validate_sidecar(
    path: Path, *, digest: str, field: str, append_suffix: bool = False
) -> Path:
    target = Path(path)
    sidecar = Path(f"{target}.sha256") if append_suffix else target.with_suffix(".sha256")
    _mode_0444(target, field=field)
    _mode_0444(sidecar, field=f"{field} sidecar")
    if sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise CCError(f"{field} digest sidecar disagrees")
    if file_sha256(target) != digest:
        raise CCError(f"{field} SHA-256 disagrees")
    return sidecar


def sealed_contract_binding() -> dict[str, str]:
    message = "C-C contract is not sealed read-only with matching .sha256 sidecar"
    try:
        digest = file_sha256(CONTRACT_PATH)
        _validate_sidecar(
            CONTRACT_PATH, digest=digest, field="C-C contract", append_suffix=True
        )
    except (CCError, OSError, UnicodeError):
        raise CCError(message) from None
    return {"path": str(CONTRACT_PATH.resolve()), "sha256": digest}


def _candidate_local(path: Path, *, field: str) -> Path:
    target = Path(path)
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    else:
        target = target.resolve()
    if not target.is_relative_to(HERE.resolve()):
        raise CCError(f"{field} must remain inside {HERE}")
    return target


def expected_code_bindings() -> list[dict[str, str]]:
    paths = (
        ("cc_runner", HERE / "run_v023_c3_candidate_cc.py"),
        ("cc_preflight_builder", HERE / "build_cc_preflight_manifest.py"),
        ("cc_launch_authority_builder", HERE / "build_cc_launch_authority.py"),
        ("cc_tests", HERE / "test_run_v023_c3_candidate_cc.py"),
        ("cc_readme", HERE / "README.md"),
        ("e1_runner_thread_pin_import", E1_DIR / "run_v023_c3_existence_e1.py"),
        ("jq_tape_extractor", JQ),
    )
    result = []
    for role, path in paths:
        if path.is_symlink() or not path.is_file():
            raise CCError(f"required code binding is missing or symlinked: {path}")
        result.append({"role": role, "path": str(path.resolve()), "sha256": file_sha256(path)})
    return result


def panel_bindings() -> dict[str, object]:
    return {
        "worlds": list(e1.WORLDS),
        "lineages": list(e1.LINEAGES),
        "unit_count": len(e1.ALL_UNITS),
        "step_indices": list(STEPS),
        "anchor_count": len(e1.ALL_UNITS) * len(STEPS),
        "users": USERS,
        "service_opportunities": OPPORTUNITIES,
        "split": "TRAIN",
        "field_component": e1.FIELD_COMPONENT,
        "base_rule": "MIN_NATIVE_ACTION_IN_EXACT_FLOAT32_MASKED_MAXIMUM_SET",
        "focal_rule": "LOWEST_USER_WITH_TWO_PHYSICALLY_DISTINCT_EXACT_MAXIMIZERS",
        "secondary_rule": "MIN_NETWORK_INTERVAL_ENERGY_THEN_MIN_NATIVE_ACTION",
        "service_margin": {"numerator": 1, "denominator": 1000},
        "replayed_physics": False,
    }


def validate_static_bindings() -> dict[str, object]:
    contract = sealed_contract_binding()
    if (
        tuple(e1.WORLDS) != (
            861587764845384088, 3943897440191533562,
            5747196377242098234, 4004348767321774260,
        )
        or tuple(e1.LINEAGES) != (2026092101, 2026092102, 2026092103)
        or e1.FIELD_COMPONENT != "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1"
        or e1.USERS != USERS
    ):
        raise CCError("imported E1 panel binding drifted")
    try:
        process = e1.process_bindings()
    except e1.E1Error as error:
        raise CCError(f"E1 runtime binding failed: {error}") from error
    return {"contract": contract, "panel_bindings": panel_bindings(), "process_environment": process}


def validate_preflight_manifest(path: Path) -> tuple[dict[str, Any], str]:
    target = Path(path)
    payload = _load_json(target, field="C-C preflight manifest")
    expected = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": CLAIM_CEILING,
        **validate_static_bindings(),
        "code_files": expected_code_bindings(),
    }
    if payload != expected:
        raise CCError("C-C preflight manifest disagrees with exact bindings/code")
    digest = file_sha256(target)
    _validate_sidecar(target, digest=digest, field="C-C preflight manifest")
    return payload, digest


def _jq_json(path: Path, expression: str, *, field: str) -> dict[str, Any]:
    if JQ.is_symlink() or not JQ.is_file():
        raise CCError("bound jq tape extractor is missing or symlinked")
    try:
        completed = subprocess.run(
            [str(JQ), "-c", expression, str(path)], check=False,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise CCError(f"cannot execute jq for {field}") from error
    if completed.returncode != 0:
        raise CCError(f"jq could not extract {field}")
    try:
        value = json.loads(completed.stdout)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise CCError(f"jq returned malformed {field}") from error
    if not isinstance(value, dict):
        raise CCError(f"jq {field} must be an object")
    return value


_TERMINAL_JQ = (
    "{schema,status,outcome,claim_ceiling,integrity,preflight_manifest_sha256,"
    "unit_receipts,test_split_opened,episode_training,learner_update,efficacy_claim}"
)
_TAPE_JQ = """
{
 schema,status,claim_ceiling,unit,panel_bindings,preflight_manifest_sha256,
 test_split_opened,episode_training,learner_update,efficacy_claim,
 steps:[.steps[0:2][] | {
   step_index,state_sha256,q1_q2_float32,action_masks,action_physical_keys,
   reference_actions,reference_metrics,reference_f0_conservation,
   unilateral_candidates:[.unilateral_candidates[] | {
     focal_user,reference_action,candidate_action,reference_physical_key,
     candidate_physical_key,candidate_joint_actions,metrics,f0_conservation
   }]
 }]
}
"""


def _e1_terminal_metadata(root: Path) -> tuple[dict[str, Any], str]:
    terminal = root / E1_TERMINAL
    _mode_0444(terminal, field="E1 terminal receipt")
    metadata = _jq_json(terminal, _TERMINAL_JQ, field="E1 terminal receipt metadata")
    expected_keys = {
        "schema", "status", "outcome", "claim_ceiling", "integrity",
        "preflight_manifest_sha256", "unit_receipts", "test_split_opened",
        "episode_training", "learner_update", "efficacy_claim",
    }
    if set(metadata) != expected_keys:
        raise CCError("E1 terminal receipt metadata keys drifted")
    outcome = metadata.get("outcome")
    if (
        metadata.get("schema") != e1.TERMINAL_RECEIPT_SCHEMA
        or metadata.get("status") != "COMPLETE"
        or metadata.get("claim_ceiling") != e1.CLAIM_CEILING
        or metadata.get("integrity") is not True
        or not isinstance(outcome, Mapping)
        or outcome.get("unilateral") != "E1_UNILATERAL_HEADROOM"
        or outcome.get("joint") not in {"E1_JOINT_HEADROOM", "E1_JOINT_CLOSED"}
        or any(metadata.get(name) is not False for name in (
            "test_split_opened", "episode_training", "learner_update", "efficacy_claim"
        ))
    ):
        raise CCError("E1 terminal result does not admit the unilateral C-C family")
    _digest(metadata.get("preflight_manifest_sha256"), field="E1 preflight SHA-256")
    rows = metadata.get("unit_receipts")
    if not isinstance(rows, list) or len(rows) != len(e1.ALL_UNITS):
        raise CCError("E1 terminal receipt lacks the exact twelve-unit panel")
    return metadata, file_sha256(terminal)


def _unit_paths(root: Path, key: e1.UnitKey) -> tuple[Path, Path, Path]:
    base = root / "units" / key.slug
    return base / E1_TAPE, base / E1_MANIFEST, base / E1_RECEIPT


def discover_e1_input(root: Path, *, hash_tapes: bool) -> dict[str, object]:
    source = Path(root)
    if not source.is_absolute() or source.is_symlink() or not source.is_dir():
        raise CCError("--from-e1-root must be an absolute non-symlink directory")
    terminal, terminal_sha = _e1_terminal_metadata(source)
    terminal_rows = terminal["unit_receipts"]
    units = []
    for index, key in enumerate(e1.ALL_UNITS):
        tape_path, manifest_path, receipt_path = _unit_paths(source, key)
        for path, label in (
            (tape_path, "E1 tape"), (manifest_path, "E1 tape manifest"),
            (receipt_path, "E1 unit receipt"),
        ):
            _mode_0444(path, field=f"{label} {key.slug}")
        manifest = _load_json(manifest_path, field=f"E1 manifest {key.slug}")
        receipt = _load_json(receipt_path, field=f"E1 receipt {key.slug}")
        tape = manifest.get("tape")
        terminal_row = terminal_rows[index]
        if (
            manifest.get("schema") != e1.UNIT_TAPE_MANIFEST_SCHEMA
            or manifest.get("status") != "COMPLETE_IMMUTABLE_TAPE"
            or manifest.get("unit") != key.as_dict()
            or not isinstance(tape, Mapping)
            or set(tape) != {"path", "sha256", "bytes", "mode"}
            or tape.get("path") != E1_TAPE or tape.get("mode") != "0444"
            or tape.get("bytes") != tape_path.stat().st_size
            or receipt.get("schema") != e1.UNIT_RECEIPT_SCHEMA
            or receipt.get("status") != "COMPLETE" or receipt.get("integrity") is not True
            or receipt.get("unit") != key.as_dict()
            or receipt.get("tape_sha256") != tape.get("sha256")
            or not isinstance(terminal_row, Mapping)
            or terminal_row.get("unit") != key.as_dict()
            or terminal_row.get("path") != f"units/{key.slug}/{E1_RECEIPT}"
            or terminal_row.get("sha256") != file_sha256(receipt_path)
        ):
            raise CCError(f"E1 unit bundle {key.slug} is inconsistent")
        tape_sha = _digest(tape.get("sha256"), field=f"E1 tape {key.slug} SHA-256")
        if hash_tapes and file_sha256(tape_path) != tape_sha:
            raise CCError(f"E1 tape {key.slug} SHA-256 disagrees")
        units.append({
            "unit": {"world": key.world, "lineage": key.lineage},
            "tape": {
                "path": str(tape_path.resolve()), "sha256": tape_sha,
                "bytes": tape_path.stat().st_size, "mode": "0444",
            },
            "manifest": {
                "path": str(manifest_path.resolve()), "sha256": file_sha256(manifest_path),
                "mode": "0444",
            },
            "receipt": {
                "path": str(receipt_path.resolve()), "sha256": file_sha256(receipt_path),
                "mode": "0444",
            },
        })
    return {
        "root": str(source.resolve()),
        "terminal_receipt": {
            "path": str((source / E1_TERMINAL).resolve()), "sha256": terminal_sha,
            "bytes": (source / E1_TERMINAL).stat().st_size, "mode": "0444",
            "outcome": dict(terminal["outcome"]),
        },
        "units": units,
    }


def _validate_e1_binding(binding: object, *, root: Path, target: e1.UnitKey | None) -> dict[str, Any]:
    if not isinstance(binding, dict) or set(binding) != {"root", "terminal_receipt", "units"}:
        raise CCError("launch authority E1 input keys differ")
    source = Path(root)
    if str(source.resolve()) != binding.get("root"):
        raise CCError("runtime E1 root differs from launch authority")
    observed = discover_e1_input(source, hash_tapes=False)
    if observed != binding:
        raise CCError("E1 terminal/manifests/receipts differ from launch authority")
    if target is not None:
        index = e1.ALL_UNITS.index(target)
        tape = Path(binding["units"][index]["tape"]["path"])
        if file_sha256(tape) != binding["units"][index]["tape"]["sha256"]:
            raise CCError(f"E1 tape {target.slug} differs from launch authority")
    return binding


def validate_launch_authority(
    path: Path, *, preflight_path: Path, preflight_sha256: str,
    e1_root: Path | None = None, output_root: Path | None = None,
    launch_arguments: Sequence[str] | None = None, target: e1.UnitKey | None = None,
) -> dict[str, Any]:
    authority_path = Path(path)
    payload = _load_json(authority_path, field="C-C launch authority")
    digest = file_sha256(authority_path)
    _validate_sidecar(authority_path, digest=digest, field="C-C launch authority")
    if set(payload) != AUTHORITY_KEYS:
        raise CCError("launch authority keys differ from the exact C-C contract")
    expected = {
        "schema": LAUNCH_AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": CLAIM_CEILING,
        "preflight_manifest": {"path": str(Path(preflight_path).resolve()), "sha256": preflight_sha256},
        "contract": sealed_contract_binding(),
        "e1_input": payload.get("e1_input"),
        "code_files": expected_code_bindings(),
        "output_root": payload.get("output_root"),
        "launch_arguments": payload.get("launch_arguments"),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }
    if payload != expected:
        raise CCError("launch authority does not pin exact C-C bindings")
    arguments = payload.get("launch_arguments")
    if not isinstance(arguments, list) or any(not isinstance(value, str) for value in arguments):
        raise CCError("launch authority arguments are malformed")
    if launch_arguments is not None and list(launch_arguments) != arguments:
        raise CCError("runtime launch arguments differ from launch authority")
    bound_output = payload.get("output_root")
    if not isinstance(bound_output, str) or not Path(bound_output).is_absolute():
        raise CCError("launch authority output root is malformed")
    _candidate_local(Path(bound_output), field="launch authority output root")
    if output_root is not None and str(Path(output_root).resolve()) != str(Path(bound_output).resolve()):
        raise CCError("runtime output root differs from launch authority")
    if e1_root is not None:
        _validate_e1_binding(payload.get("e1_input"), root=Path(e1_root), target=target)
    return payload


def _float_hex(value: object, *, field: str, positive: bool = False) -> float:
    if not isinstance(value, str):
        raise CCError(f"{field} must be a lossless binary64 hex string")
    try:
        result = float.fromhex(value)
    except ValueError as error:
        raise CCError(f"{field} is not a binary64 hex string") from error
    if not math.isfinite(result) or (positive and result <= 0.0) or result.hex() != value:
        raise CCError(f"{field} is not canonical finite binary64 hex")
    return result


def _metrics(value: object, *, users: int, field: str) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != {
        "total_bits", "total_energy_j", "served", "opportunities"
    }:
        raise CCError(f"{field} metrics keys are malformed")
    bits = _float_hex(value["total_bits"], field=f"{field} bits")
    energy = _float_hex(value["total_energy_j"], field=f"{field} energy", positive=True)
    served = value["served"]
    opportunities = value["opportunities"]
    if bits < 0.0 or type(served) is not int or type(opportunities) is not int:
        raise CCError(f"{field} metrics values are malformed")
    if opportunities != users or not 0 <= served <= opportunities:
        raise CCError(f"{field} service counts are malformed")
    return {
        "total_bits": bits.hex(), "total_energy_j": energy.hex(),
        "served": served, "opportunities": opportunities,
    }


def _f0(value: object, *, field: str) -> str:
    expected_keys = {
        "f0_schema", "verified", "power_residual_w", "energy_residual_j"
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected_keys
        or value.get("f0_schema") != e1.f1.F0_SCHEMA
        or value.get("verified") is not True
    ):
        raise CCError(f"{field} lacks a verified corrected-F0 receipt")
    for name in ("power_residual_w", "energy_residual_j"):
        residual = _float_hex(value[name], field=f"{field} {name}")
        if residual != 0.0:
            raise CCError(f"{field} conservation residual is nonzero")
    return canonical_sha256(value)


def _decode_q12(value: object, *, users: int, actions: int) -> np.ndarray:
    if not isinstance(value, Mapping) or set(value) != {"dtype", "encoding", "shape", "data_hex"}:
        raise CCError("Q1+Q2 encoding keys are malformed")
    if (
        value.get("dtype") != "<f4"
        or value.get("encoding") != "base16-little-endian-c-order"
        or value.get("shape") != [users, actions]
        or not isinstance(value.get("data_hex"), str)
    ):
        raise CCError("Q1+Q2 encoding metadata is malformed")
    try:
        raw = bytes.fromhex(value["data_hex"])
    except ValueError as error:
        raise CCError("Q1+Q2 base16 bytes are malformed") from error
    if len(raw) != users * actions * 4 or value["data_hex"] != raw.hex():
        raise CCError("Q1+Q2 byte count or base16 canonical form is malformed")
    result = np.frombuffer(raw, dtype=np.dtype("<f4")).reshape(users, actions).copy()
    if result.dtype != np.dtype(np.float32) or not np.all(np.isfinite(result)):
        raise CCError("Q1+Q2 contains non-finite or non-float32 values")
    return result


def exact_tie_sets(q12: np.ndarray, masks: object) -> tuple[tuple[int, ...], ...]:
    values = np.asarray(q12)
    legal = np.asarray(masks)
    if values.ndim != 2 or values.dtype != np.dtype(np.float32):
        raise CCError("Q1+Q2 surface must be a float32 matrix")
    if legal.dtype != np.bool_ or legal.shape != values.shape:
        raise CCError("action masks must be a Boolean Q-shaped matrix")
    if not np.all(np.isfinite(values)):
        raise CCError("Q1+Q2 surface is non-finite")
    result = []
    for user in range(values.shape[0]):
        indices = np.flatnonzero(legal[user])
        if not len(indices):
            result.append(())
            continue
        maximum = np.max(values[user, indices])
        # NumPy numerical equality intentionally makes -0.0 equal +0.0.
        result.append(tuple(int(action) for action in indices[values[user, indices] == maximum]))
    return tuple(result)


def _physical_key(value: object, *, field: str) -> tuple[int, int]:
    if (
        not isinstance(value, list) or len(value) != 2
        or any(type(item) is not int for item in value)
    ):
        raise CCError(f"{field} must be [satellite, cell]")
    return value[0], value[1]


def _validate_key_table(
    masks: np.ndarray, key_table: object, reference: Sequence[int]
) -> list[list[tuple[int, int] | None]]:
    users, actions = masks.shape
    if not isinstance(key_table, list) or len(key_table) != users:
        raise CCError("action physical-key table is malformed")
    result: list[list[tuple[int, int] | None]] = []
    for user in range(users):
        raw_row = key_table[user]
        if not isinstance(raw_row, list) or len(raw_row) != actions:
            raise CCError("action physical-key row is malformed")
        row: list[tuple[int, int] | None] = []
        for action, raw in enumerate(raw_row):
            if bool(masks[user, action]):
                row.append(_physical_key(raw, field="legal action physical key"))
            elif raw is not None:
                raise CCError("illegal action must have a null physical key")
            else:
                row.append(None)
        if np.any(masks[user]):
            base = reference[user]
            if not 0 <= base < actions or not bool(masks[user, base]):
                raise CCError("BASE selected an illegal action")
            base_key = row[base]
            seen: set[tuple[int, int]] = set()
            for action in np.flatnonzero(masks[user]):
                key = row[int(action)]
                assert key is not None
                if key == base_key:
                    continue
                if key in seen:
                    raise CCError("two legal slots alias one non-BASE physical candidate")
                seen.add(key)
        elif reference[user] != -1:
            raise CCError("all-false mask user requires NO_OP_ACTION=-1")
        result.append(row)
    return result


def select_anchor(step: Mapping[str, object]) -> dict[str, object]:
    step_index = step.get("step_index")
    if type(step_index) is not int or step_index not in STEPS:
        raise CCError("candidate input must contain only canonical steps 0 and 1")
    masks = np.asarray(step.get("action_masks"))
    if masks.dtype != np.bool_ or masks.ndim != 2:
        raise CCError("action masks are malformed")
    users, actions = masks.shape
    q12 = _decode_q12(step.get("q1_q2_float32"), users=users, actions=actions)
    reference_raw = step.get("reference_actions")
    if (
        not isinstance(reference_raw, list) or len(reference_raw) != users
        or any(type(value) is not int for value in reference_raw)
    ):
        raise CCError("BASE action vector is malformed")
    reference = list(reference_raw)
    ties = exact_tie_sets(q12, masks)
    expected_base = [tie[0] if tie else -1 for tie in ties]
    if reference != expected_base:
        raise CCError("stored BASE is not min of the exact float32 tie sets")
    keys = _validate_key_table(masks, step.get("action_physical_keys"), reference)
    base_metrics = _metrics(step.get("reference_metrics"), users=users, field="BASE")
    base_f0 = _f0(step.get("reference_f0_conservation"), field="BASE")

    focal: int | None = None
    for user, tie in enumerate(ties):
        identities = {keys[user][action] for action in tie}
        if len(identities) >= 2:
            focal = user
            break

    rows = step.get("unilateral_candidates")
    if not isinstance(rows, list):
        raise CCError("unilateral candidate rows are malformed")
    by_key: dict[tuple[int, int], Mapping[str, object]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise CCError("unilateral candidate row is malformed")
        user = row.get("focal_user")
        action = row.get("candidate_action")
        if type(user) is not int or type(action) is not int or (user, action) in by_key:
            raise CCError("unilateral candidate identity is malformed or duplicate")
        by_key[(user, action)] = row

    selected = None if focal is None else reference[focal]
    selected_metrics = base_metrics
    selected_f0 = base_f0
    selected_profile_id = "BASE"
    selected_energy = _float_hex(base_metrics["total_energy_j"], field="BASE energy", positive=True)
    if focal is not None:
        candidates = []
        base_key = keys[focal][reference[focal]]
        for action in ties[focal]:
            key = keys[focal][action]
            if key == base_key:
                metrics, f0_sha, profile_id = base_metrics, base_f0, "BASE"
            else:
                row = by_key.get((focal, action))
                if row is None:
                    raise CCError("tied physical candidate is missing its E1 unilateral row")
                joint = row.get("candidate_joint_actions")
                expected_joint = list(reference)
                expected_joint[focal] = action
                if (
                    row.get("reference_action") != reference[focal]
                    or row.get("reference_physical_key") != list(base_key or ())
                    or row.get("candidate_physical_key") != list(key or ())
                    or joint != expected_joint
                ):
                    raise CCError("E1 unilateral row does not authenticate the tied complete profile")
                metrics = _metrics(row.get("metrics"), users=users, field="candidate")
                f0_sha = _f0(row.get("f0_conservation"), field="candidate")
                profile_id = f"U:{focal}:{action}"
            energy = _float_hex(metrics["total_energy_j"], field="candidate energy", positive=True)
            candidates.append((energy, action, metrics, f0_sha, profile_id))
        energy, selected, selected_metrics, selected_f0, selected_profile_id = min(candidates)
        selected_energy = energy

    changed = bool(
        focal is not None
        and selected is not None
        and keys[focal][selected] != keys[focal][reference[focal]]
    )
    return {
        "step_index": step_index,
        "state_sha256": _digest(step.get("state_sha256"), field="state SHA-256"),
        "base_actions_sha256": canonical_sha256(reference),
        "focal_user": focal,
        "focal_tied_actions": [] if focal is None else list(ties[focal]),
        "base_action": None if focal is None else reference[focal],
        "selected_action": selected,
        "selected_physical_key": None if focal is None else list(keys[focal][selected] or ()),
        "selected_profile_id": selected_profile_id,
        "c3_score_negative_energy_j_hex": (-selected_energy).hex(),
        "legal_physical_change": changed,
        "base_metrics": base_metrics,
        "selected_metrics": selected_metrics,
        "base_f0_sha256": base_f0,
        "selected_f0_sha256": selected_f0,
    }


def evaluate_unit_tape(tape: Mapping[str, object], *, key: e1.UnitKey, tape_sha256: str) -> dict[str, object]:
    expected_keys = {
        "schema", "status", "claim_ceiling", "unit", "panel_bindings",
        "preflight_manifest_sha256", "steps", "test_split_opened",
        "episode_training", "learner_update", "efficacy_claim",
    }
    if set(tape) != expected_keys:
        raise CCError("extracted E1 tape keys drifted")
    if (
        tape.get("schema") != e1.UNIT_TAPE_SCHEMA
        or tape.get("status") != "COMPLETE_IMMUTABLE_TAPE"
        or tape.get("claim_ceiling") != e1.CLAIM_CEILING
        or tape.get("unit") != key.as_dict()
        or tape.get("panel_bindings") != e1.panel_bindings()
        or any(tape.get(name) is not False for name in (
            "test_split_opened", "episode_training", "learner_update", "efficacy_claim"
        ))
    ):
        raise CCError("extracted E1 tape provenance drifted")
    _digest(tape.get("preflight_manifest_sha256"), field="E1 preflight SHA-256")
    steps = tape.get("steps")
    if not isinstance(steps, list) or [row.get("step_index") for row in steps if isinstance(row, Mapping)] != [0, 1]:
        raise CCError("extracted E1 tape must contain exactly steps 0 and 1")
    anchors = [select_anchor(step) for step in steps]
    return {
        "schema": UNIT_RECEIPT_SCHEMA,
        "status": "COMPLETE",
        "outcome": "C_C_UNIT_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "unit": {"world": key.world, "lineage": key.lineage},
        "source_e1_tape_sha256": _digest(tape_sha256, field="E1 tape SHA-256"),
        "source_e1_preflight_sha256": tape["preflight_manifest_sha256"],
        "anchors": anchors,
        "counts": {
            "anchors": len(anchors),
            "exact_tie_exposures": sum(row["focal_user"] is not None for row in anchors),
            "legal_physical_changes": sum(bool(row["legal_physical_change"]) for row in anchors),
            "service_opportunities": sum(int(row["base_metrics"]["opportunities"]) for row in anchors),
        },
        "integrity": True,
        "tape_only": True,
        "replayed_physics": False,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def fraction_payload(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _exact_metric(value: Mapping[str, object], name: str) -> Fraction:
    return Fraction.from_float(_float_hex(value[name], field=name, positive=name == "total_energy_j"))


def pool_unit_receipts(receipts: Sequence[Mapping[str, object]]) -> dict[str, object]:
    base_bits = Fraction(0)
    base_energy = Fraction(0)
    selected_bits = Fraction(0)
    selected_energy = Fraction(0)
    base_served = selected_served = opportunities = exposures = changes = 0
    for receipt in receipts:
        anchors = receipt.get("anchors")
        if not isinstance(anchors, list):
            raise CCError("unit receipt anchors are malformed")
        for anchor in anchors:
            if not isinstance(anchor, Mapping):
                raise CCError("unit receipt anchor is malformed")
            base = anchor.get("base_metrics")
            selected = anchor.get("selected_metrics")
            if not isinstance(base, Mapping) or not isinstance(selected, Mapping):
                raise CCError("unit receipt metrics are malformed")
            base_bits += _exact_metric(base, "total_bits")
            base_energy += _exact_metric(base, "total_energy_j")
            selected_bits += _exact_metric(selected, "total_bits")
            selected_energy += _exact_metric(selected, "total_energy_j")
            for metrics in (base, selected):
                if type(metrics.get("served")) is not int or type(metrics.get("opportunities")) is not int:
                    raise CCError("receipt service counts are malformed")
            if base["opportunities"] != selected["opportunities"]:
                raise CCError("BASE/C-C opportunities differ")
            base_served += int(base["served"])
            selected_served += int(selected["served"])
            opportunities += int(base["opportunities"])
            exposures += anchor.get("focal_user") is not None
            changes += bool(anchor.get("legal_physical_change"))
    if base_energy <= 0 or selected_energy <= 0 or opportunities <= 0:
        raise CCError("pooled energy/opportunity total is invalid")
    eta_base = base_bits / base_energy
    eta_selected = selected_bits / selected_energy
    service_base = Fraction(base_served, opportunities)
    service_selected = Fraction(selected_served, opportunities)
    reasons = []
    if exposures == 0:
        reasons.append("NO_EXACT_TIE_EXPOSURE")
    if changes == 0:
        reasons.append("NO_LEGAL_CHANGE")
    if eta_selected <= eta_base:
        reasons.append("EE_NOT_ABOVE_BASE")
    if service_selected < service_base - SERVICE_MARGIN:
        reasons.append("SERVICE_NONINFERIORITY_FAILED")
    outcome = OUTCOMES[0] if not reasons else OUTCOMES[1]
    return {
        "outcome": outcome,
        "reasons": reasons,
        "counts": {
            "anchors": sum(len(receipt["anchors"]) for receipt in receipts),
            "exact_tie_exposures": exposures,
            "legal_physical_changes": changes,
            "service_opportunities": opportunities,
            "base_served": base_served,
            "selected_served": selected_served,
        },
        "exact": {
            "base_bits": fraction_payload(base_bits),
            "base_energy_j": fraction_payload(base_energy),
            "selected_bits": fraction_payload(selected_bits),
            "selected_energy_j": fraction_payload(selected_energy),
            "eta_base": fraction_payload(eta_base),
            "eta_selected": fraction_payload(eta_selected),
            "service_base": fraction_payload(service_base),
            "service_selected": fraction_payload(service_selected),
            "service_floor": fraction_payload(service_base - SERVICE_MARGIN),
        },
    }


def build_terminal_receipt(receipts: Sequence[Mapping[str, object]], receipt_bindings: Sequence[Mapping[str, object]]) -> dict[str, object]:
    if len(receipts) != len(e1.ALL_UNITS) or len(receipt_bindings) != len(e1.ALL_UNITS):
        raise CCError("C-C merge requires exactly twelve unit receipts")
    pooled = pool_unit_receipts(receipts)
    if pooled["counts"]["anchors"] != 24 or pooled["counts"]["service_opportunities"] != OPPORTUNITIES:
        raise CCError("C-C merge does not cover 24 anchors and 2,400 opportunities")
    return {
        "schema": TERMINAL_RECEIPT_SCHEMA,
        "status": "COMPLETE",
        "outcome": pooled["outcome"],
        "reasons": pooled["reasons"],
        "claim_ceiling": CLAIM_CEILING,
        "panel_bindings": panel_bindings(),
        "unit_receipts": list(receipt_bindings),
        "counts": pooled["counts"],
        "exact_pooling": pooled["exact"],
        "integrity": True,
        "tape_only": True,
        "replayed_physics": False,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def invalid_receipt(*, scope: str, error: BaseException, key: e1.UnitKey | None = None) -> dict[str, object]:
    return {
        "schema": UNIT_RECEIPT_SCHEMA if key is not None else TERMINAL_RECEIPT_SCHEMA,
        "status": "INVALID_RUN", "outcome": "INVALID_RUN", "reasons": [],
        "scope": scope, "claim_ceiling": CLAIM_CEILING,
        "unit": None if key is None else {"world": key.world, "lineage": key.lineage},
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(str(error).encode("utf-8")).hexdigest(),
        "integrity": False, "tape_only": True, "replayed_physics": False,
        "test_split_opened": False, "episode_training": False,
        "learner_update": False, "efficacy_claim": False,
    }


def _write_once(path: Path, payload: Mapping[str, object]) -> str:
    target = _candidate_local(Path(path), field="write-once artifact")
    if target.exists() or target.is_symlink():
        raise CCError(f"refusing to overwrite write-once artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    with target.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    target.chmod(0o444)
    digest = file_sha256(target)
    if target.read_bytes() != encoded or target.stat().st_mode & 0o777 != 0o444:
        raise CCError(f"write-once artifact failed immutable readback: {target}")
    if _load_json(target, field="published artifact") != payload:
        raise CCError("write-once artifact payload changed on readback")
    return digest


def write_once_with_sidecar(path: Path, payload: Mapping[str, object]) -> tuple[Path, Path, str]:
    target = _candidate_local(Path(path), field="write-once artifact")
    sidecar = target.with_suffix(".sha256")
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise CCError("refusing to overwrite write-once artifact or digest sidecar")
    digest = _write_once(target, payload)
    try:
        with sidecar.open("xb") as handle:
            handle.write(f"{digest}  {target.name}\n".encode("ascii"))
            handle.flush()
            os.fsync(handle.fileno())
        sidecar.chmod(0o444)
        _validate_sidecar(target, digest=digest, field="published artifact")
    except Exception:
        if sidecar.exists() and not sidecar.is_symlink():
            sidecar.chmod(0o644)
            sidecar.unlink()
        raise
    return target, sidecar, digest


def _publish_unit(output: Path, *, key: e1.UnitKey, payload: Mapping[str, object]) -> tuple[Path, str]:
    root = _candidate_local(Path(output), field="output root")
    units = root / "units"
    units.mkdir(parents=True, exist_ok=True)
    final = units / key.slug
    if final.exists() or final.is_symlink():
        raise CCError(f"refusing to overwrite write-once C-C unit {key.slug}")
    stage = Path(tempfile.mkdtemp(prefix=f".stage-{key.slug}-", dir=units))
    try:
        receipt, _sidecar, digest = write_once_with_sidecar(stage / DEFAULT_UNIT_RECEIPT, payload)
        stage.chmod(0o555)
        os.rename(stage, final)
        published = final / receipt.name
        _validate_sidecar(published, digest=digest, field=f"C-C unit {key.slug}")
        return published, digest
    finally:
        if stage.exists() and not stage.is_symlink():
            stage.chmod(0o755)
            shutil.rmtree(stage)


def execute_unit(*, key: e1.UnitKey, e1_root: Path, output: Path, authority: Mapping[str, object]) -> tuple[Path, bool]:
    tape_binding = authority["e1_input"]["units"][e1.ALL_UNITS.index(key)]["tape"]
    tape_path = Path(tape_binding["path"])
    try:
        extracted = _jq_json(tape_path, _TAPE_JQ, field=f"E1 tape {key.slug} steps 0-1")
        payload = evaluate_unit_tape(extracted, key=key, tape_sha256=tape_binding["sha256"])
        receipt, _digest_value = _publish_unit(output, key=key, payload=payload)
        return receipt, True
    except Exception as error:
        payload = invalid_receipt(scope="unit", error=error, key=key)
        receipt, _digest_value = _publish_unit(output, key=key, payload=payload)
        return receipt, False


def _load_candidate_units(output: Path, authority: Mapping[str, object]) -> tuple[list[dict[str, Any]], list[dict[str, object]]]:
    receipts = []
    bindings = []
    for index, key in enumerate(e1.ALL_UNITS):
        path = Path(output) / "units" / key.slug / DEFAULT_UNIT_RECEIPT
        _mode_0444(path, field=f"C-C unit receipt {key.slug}")
        digest = file_sha256(path)
        _validate_sidecar(path, digest=digest, field=f"C-C unit receipt {key.slug}")
        payload = _load_json(path, field=f"C-C unit receipt {key.slug}")
        if (
            payload.get("schema") != UNIT_RECEIPT_SCHEMA
            or payload.get("status") != "COMPLETE"
            or payload.get("outcome") != "C_C_UNIT_COMPLETE"
            or payload.get("claim_ceiling") != CLAIM_CEILING
            or payload.get("unit") != {"world": key.world, "lineage": key.lineage}
            or payload.get("source_e1_tape_sha256")
            != authority["e1_input"]["units"][index]["tape"]["sha256"]
            or payload.get("integrity") is not True
        ):
            raise CCError(f"C-C unit receipt {key.slug} is invalid or incomplete")
        receipts.append(payload)
        bindings.append({
            "unit": {"world": key.world, "lineage": key.lineage},
            "path": f"units/{key.slug}/{DEFAULT_UNIT_RECEIPT}", "sha256": digest,
        })
    return receipts, bindings


def execute_merge(*, output: Path, authority: Mapping[str, object]) -> tuple[Path, bool]:
    root = _candidate_local(Path(output), field="output root")
    terminal = root / DEFAULT_TERMINAL
    try:
        receipts, bindings = _load_candidate_units(root, authority)
        payload = build_terminal_receipt(receipts, bindings)
        write_once_with_sidecar(terminal, payload)
        return terminal, True
    except Exception as error:
        payload = invalid_receipt(scope="merge", error=error)
        write_once_with_sidecar(terminal, payload)
        return terminal, False


def run(args: argparse.Namespace) -> dict[str, object]:
    # The prospective scientific contract is the first and clearest launch gate.
    sealed_contract_binding()
    _preflight, preflight_sha = validate_preflight_manifest(Path(args.preflight_manifest))
    if args.dry_run:
        result: dict[str, object] = {"mode": "dry-run", "panel": panel_bindings()}
        if args.launch_authority is not None:
            result["authority"] = validate_launch_authority(
                Path(args.launch_authority), preflight_path=Path(args.preflight_manifest),
                preflight_sha256=preflight_sha,
            )
        return result
    if args.launch_authority is None or args.from_e1_root is None or args.output is None:
        raise CCError("C-C execution requires authority, E1 root, and output root")
    key = None if args.unit is None else e1.UnitKey.parse(args.unit)
    authority = validate_launch_authority(
        Path(args.launch_authority), preflight_path=Path(args.preflight_manifest),
        preflight_sha256=preflight_sha, e1_root=Path(args.from_e1_root),
        output_root=Path(args.output), launch_arguments=args.raw_launch_arguments,
        target=key,
    )
    if key is not None:
        receipt, valid = execute_unit(
            key=key, e1_root=Path(args.from_e1_root), output=Path(args.output),
            authority=authority,
        )
        return {"mode": "unit", "receipt": receipt, "valid": valid}
    receipt, valid = execute_merge(output=Path(args.output), authority=authority)
    return {"mode": "merge", "receipt": receipt, "valid": valid}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-manifest", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--from-e1-root", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--unit")
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        pin_single_thread_runtime()
    except CCError as error:
        print(f"C_C_ERROR: {error}", file=sys.stderr)
        return 2
    raw = list(sys.argv[1:] if argv is None else argv)
    args = _parser().parse_args(raw)
    args.raw_launch_arguments = raw
    if not args.dry_run and (args.unit is None) == (not args.merge):
        print("C_C_ERROR: choose exactly one of --unit WORLD:LINEAGE or --merge", file=sys.stderr)
        return 2
    try:
        result = run(args)
    except Exception as error:
        print(f"C_C_ERROR: {error}", file=sys.stderr)
        return 2
    if args.dry_run:
        print("C_C_DRY_RUN_PASS")
        return 0
    print(f"C_C_{str(result['mode']).upper()} receipt={result['receipt']}")
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
