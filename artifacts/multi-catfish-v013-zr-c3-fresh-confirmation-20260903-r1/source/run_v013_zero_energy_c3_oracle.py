#!/usr/bin/env python3
"""V0.13 fresh-world zero-energy-supported C3 TRAIN-only oracle gate.

The runner keeps frozen learned Q1 and exact execution-equivalent OPS3 O2,
then compares their shared action against the frozen current-slot ZR C3
teacher surface on fresh TRAIN worlds.  It performs no learner/optimizer
update and has no TEST path.  Active-beam and active-satellite counts are
diagnostics only; the resource guard is exact accumulated trajectory energy.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import copy
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import sys
import sysconfig
import tempfile
import time
from typing import Any

import numpy as np
import torch


REPO = Path(__file__).resolve().parents[2]
OLD_SCRATCH = REPO / ".scratch" / "c3-v04"
for _path in (OLD_SCRATCH, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v04_c3_500_update_screen as screen  # noqa: E402
import run_v04_c3_learnability_gate as old_gate  # noqa: E402
from mcrl.algorithms.ee_axis_v04_hybrid import (  # noqa: E402
    extract_frozen_meanmax_head,
)
from mcrl.env.action_contract import NUM_ACTIONS  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import (  # noqa: E402
    OPS3_KAPPA_BITS,
    OPS3_LAMBDA_BITS_PER_J,
)
from mcrl.runtime.ee_axis_ops3_live import (  # noqa: E402
    OPS3_LIVE_SCHEMA,
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_zero_marginal_c3 import (  # noqa: E402
    ZERO_MARGINAL_C3_SCHEMA,
    assert_surface_identity,
    build_zr_surface,
)
from mcrl.runtime.ee_axis_zero_marginal_c3_live import (  # noqa: E402
    ZERO_MARGINAL_C3_LIVE_SCHEMA,
    measure_zero_marginal_c3,
    physics_signature,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402


RESULT_SCHEMA = "multi-catfish-mcrl-v013-zero-energy-c3-oracle-result-v1"
EPISODE_SCHEMA = "multi-catfish-mcrl-v013-zero-energy-c3-oracle-episode-v1"
SHARD_SCHEMA = "multi-catfish-mcrl-v013-zero-energy-c3-oracle-shard-v1"
CONTRACT_SCHEMA = "multi-catfish-mcrl-v013-zero-energy-c3-oracle-contract-v1"
AUTHORITY_SCHEMA = "multi-catfish-mcrl-v013-executable-authority-v1"

WORLD_SEEDS = (2026104901, 2026104902, 2026104903, 2026104904)
LINEAGES = (2026092101, 2026092102, 2026092103)
ARMS = ("DROP_C3", "FULL_ZR")
USERS = 100
STEPS_PER_EPISODE = 10
FIELD_COMPONENT = "MCRL_V013_ZR_ACCEPTANCE_CONFIRMATION_V1"
FIELD_EXCLUDES = (
    "arm",
    "initialization_seed",
    "policy_label",
    "action",
    "target",
    "outcome",
)
CONTRACT_PATH = (
    REPO
    / "docs"
    / "MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md"
)
RUNTIME_PATHS = (
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3_live.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_zero_marginal_c3.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_zero_marginal_c3_live.py",
)
PYTHON_SOURCE_ROOTS = (
    REPO / "src",
    OLD_SCRATCH,
    REPO / "scripts",
    REPO / ".scratch" / "zero-energy-c3-v013",
)
PYTHON_SOURCE_SUFFIXES = {".py", ".pyi", ".so", ".pth"}
FROZEN_STATUS = "Status: **FROZEN BEFORE OUTCOME ACCESS**"
CONTRACT_RECEIPT_PREFIX = "Executable contract receipt SHA-256: `"
FROZEN_AUTHORITY_PATH = (
    REPO
    / "artifacts"
    / "multi-catfish-v013-zr-c3-fresh-confirmation-20260903-r1"
    / "FROZEN-AUTHORITY.json"
)
WRAPPER_PATHS = (
    REPO
    / ".scratch"
    / "zero-energy-c3-v013"
    / "launch_v013_zero_energy_c3_server.sh",
    REPO
    / ".scratch"
    / "zero-energy-c3-v013"
    / "run_v013_zero_energy_c3_panel_server.sh",
    REPO
    / ".scratch"
    / "zero-energy-c3-v013"
    / "finalize_v013_zero_energy_c3_server.sh",
    REPO
    / ".scratch"
    / "zero-energy-c3-v013"
    / "sync_v013_zero_energy_c3_server.sh",
)
EXPECTED_EXECUTION_ENVIRONMENT = {
    "python": "3.13.3",
    "implementation": "cpython",
    "cache_tag": "cpython-313",
    "soabi": "cpython-313-x86_64-linux-gnu",
    "machine": "x86_64",
    "numpy": "2.5.2",
    "numpy_config_sha256": (
        "67dfb7e234e361796a37141fe8465bb2f95d16bdd66033b3ca95d0ad266ff4c3"
    ),
    "torch": "2.13.0+cu130",
    "torch_distribution": "2.13.0",
    "torch_git": "cf30153c4c131c8164ee7798e5022d810682e2cb",
    "torch_cuda": "13.0",
    "torch_config_sha256": (
        "e100a7e4066820bfb7d99d6d8d7718604f04364f175d137350aa6bff20563fd0"
    ),
    "sgp4": "2.27",
    "pyyaml": "6.0.3",
    "distribution_count": 40,
    "distribution_set_sha256": (
        "9727663cc5c343e0a30b4f49a4e0de9062874582b8ada20104175c9a76360e20"
    ),
}


class V013OracleError(RuntimeError):
    """A V0.13 authority, mechanics, or acceptance condition failed closed."""


def _canonical_json_default(value: object) -> bool | int | float:
    """Normalize finite NumPy scalars without admitting arrays or objects."""

    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("NumPy floating scalar is not finite")
        return result
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=_canonical_json_default,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V013OracleError("payload is not finite canonical JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise V013OracleError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_canonical_json(path: Path) -> object:
    """Read one receipt only if its bytes are unique canonical JSON."""

    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V013OracleError(f"expected a regular JSON receipt: {source}")
    raw = source.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"), object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V013OracleError(f"invalid canonical JSON receipt: {source}") from error
    if raw != _canonical_bytes(payload):
        raise V013OracleError(f"receipt is not canonical JSON: {source}")
    return payload


def _require_exact(value: object, expected: object, *, field: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise V013OracleError(f"{field} does not match the frozen value")


def _exact_keys(value: object, expected: set[str], *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise V013OracleError(f"{field} has a noncanonical field set")
    return value


def _bool(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise V013OracleError(f"{field} is not Boolean")
    return value


def _nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise V013OracleError(f"{field} is not a nonnegative integer")
    return value


def _finite_number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V013OracleError(f"{field} is not numeric")
    result = float(value)
    if not math.isfinite(result):
        raise V013OracleError(f"{field} is not finite")
    return result


def _sha256_text(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V013OracleError(f"{field} is not a lowercase SHA-256 digest")
    return value


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V013OracleError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def python_source_authority() -> dict[str, Any]:
    """Seal every importable file reachable through the shipped import roots."""

    files: list[Path] = []
    for root in PYTHON_SOURCE_ROOTS:
        if root.is_symlink() or not root.is_dir():
            raise V013OracleError(f"expected a regular source directory: {root}")
        files.extend(
            path
            for path in root.rglob("*")
            if path.suffix in PYTHON_SOURCE_SUFFIXES
            and path.is_file()
            and not path.is_symlink()
            and "__pycache__" not in path.parts
        )
    relative_hashes = {
        str(path.relative_to(REPO)): file_sha256(path)
        for path in sorted(files, key=lambda item: str(item.relative_to(REPO)))
    }
    if not relative_hashes:
        raise V013OracleError("Python source authority set is empty")
    return {
        "python_source_file_count": len(relative_hashes),
        "python_source_file_set_sha256": canonical_sha256(relative_hashes),
    }


def execution_environment_receipt() -> dict[str, Any]:
    """Fingerprint the server numeric runtime that can affect strict comparisons."""

    distributions = sorted(
        (
            str(distribution.metadata.get("Name", "")).lower(),
            str(distribution.version),
        )
        for distribution in importlib.metadata.distributions()
    )
    numpy_config = np.show_config(mode="dicts")
    return {
        "python": platform.python_version(),
        "implementation": sys.implementation.name,
        "cache_tag": sys.implementation.cache_tag,
        "soabi": sysconfig.get_config_var("SOABI"),
        "machine": platform.machine(),
        "numpy": np.__version__,
        "numpy_config_sha256": hashlib.sha256(
            json.dumps(
                numpy_config,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest(),
        "torch": torch.__version__,
        "torch_distribution": importlib.metadata.version("torch"),
        "torch_git": torch.version.git_version,
        "torch_cuda": torch.version.cuda,
        "torch_config_sha256": hashlib.sha256(
            torch.__config__.show().encode("utf-8")
        ).hexdigest(),
        "sgp4": importlib.metadata.version("sgp4"),
        "pyyaml": importlib.metadata.version("PyYAML"),
        "distribution_count": len(distributions),
        "distribution_set_sha256": hashlib.sha256(
            json.dumps(distributions, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }


def assert_execution_environment() -> None:
    actual = execution_environment_receipt()
    if actual != EXPECTED_EXECUTION_ENVIRONMENT:
        raise V013OracleError(
            "numeric execution environment does not match the frozen server receipt"
        )


def assert_contract_frozen(contract_path: Path = CONTRACT_PATH) -> None:
    """Require the caller-provided V0.13 prereg to be frozen before outcomes."""

    path = Path(contract_path)
    if path.is_symlink() or not path.is_file():
        raise V013OracleError(f"V0.13 contract is missing: {path}")
    text = path.read_text(encoding="utf-8")
    status_lines = [line.rstrip() for line in text.splitlines() if line.startswith("Status:")]
    if status_lines != [FROZEN_STATUS]:
        raise V013OracleError(
            "V0.13 contract does not have exactly one frozen status line"
        )
    bindings = [
        line.removeprefix(CONTRACT_RECEIPT_PREFIX).removesuffix("`")
        for line in text.splitlines()
        if line.startswith(CONTRACT_RECEIPT_PREFIX) and line.endswith("`")
    ]
    expected = canonical_sha256(contract_receipt())
    if len(bindings) != 1 or bindings[0] != expected:
        raise V013OracleError(
            "V0.13 frozen contract does not bind the executable contract receipt"
        )


def array_sha256(*values: object) -> str:
    digest = hashlib.sha256()
    for value in values:
        array = np.ascontiguousarray(np.asarray(value))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(repr(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def field_for_world(world_seed: int) -> KeyedFadingField:
    if int(world_seed) not in WORLD_SEEDS:
        raise V013OracleError("world seed is outside the frozen V0.13 panel")
    return KeyedFadingField.from_components(FIELD_COMPONENT, int(world_seed))


def contract_receipt() -> dict[str, Any]:
    return {
        "schema": CONTRACT_SCHEMA,
        "world_seeds": list(WORLD_SEEDS),
        "lineages": list(LINEAGES),
        "arms": list(ARMS),
        "arm_heads": {
            "DROP_C3": ["Q1", "O2_OPS3"],
            "FULL_ZR": ["Q1", "O2_OPS3", "O3_ZR"],
        },
        "candidate_order": ["ZR"],
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "episodes": len(WORLD_SEEDS) * len(LINEAGES) * len(ARMS),
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "background": "MASKED_ARGMAX_Q1_PLUS_O2",
        "summation": "left_to_right_unweighted",
        "selection": "one_common_mask_one_argmax_one_action",
        "compatibility": {
            "role": "teacher_target_support_not_action_mask",
            "tolerance": 0.0,
            "components": [
                "served_vector",
                "active_beam_set",
                "active_satellite_set",
                "per_beam_rf_power",
                "canonical_network_power",
            ],
        },
        "field_components": [FIELD_COMPONENT, "world_seed"],
        "field_excludes": list(FIELD_EXCLUDES),
        "zero_marginal_c3_schema": ZERO_MARGINAL_C3_SCHEMA,
        "zero_marginal_c3_live_schema": ZERO_MARGINAL_C3_LIVE_SCHEMA,
        "ops3_live_schema": OPS3_LIVE_SCHEMA,
        "lambda_bits_per_j_hex": OPS3_LAMBDA_BITS_PER_J.hex(),
        "kappa_bits_hex": OPS3_KAPPA_BITS.hex(),
        "gate": {
            "pooled_full_strictly_above_drop_c3": True,
            "every_world_strictly_above_drop_c3": True,
            "positive_lineages_per_world_minimum": 2,
            "service_noninferior_pooled_and_every_world": True,
            "service_noninferior_lineages_per_world_minimum": 2,
            "one_user_step_shortfall_fails": True,
            "exact_total_trajectory_energy_nonincrease_pooled_or_world": True,
            "active_beam_steps_not_above_pooled_or_world": "diagnostic_only",
            "active_satellite_steps_not_above_pooled_or_world": "diagnostic_only",
            "nonzero_supported_positive_spread": True,
            "nonzero_executed_action_exposure": True,
            "every_changed_action_compatible": True,
            "executed_joint_adds_no_beam_or_satellite": True,
            "executed_joint_network_power_nonincrease": True,
        },
        "selection_table": {
            "ZR": "GO_ZR_C3_LEARNABILITY_PREREG_ONLY",
            "none": "STOP_ZR_C3_ORACLE",
        },
    }


def _q1_parameter_sha256(network: Any) -> str:
    digest = hashlib.sha256()
    for name, value in network.state_dict().items():
        tensor = value.detach().cpu()
        digest.update(str(name).encode("utf-8"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(repr(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest()


def load_frozen_q1(v03_root: Path, lineage: int) -> tuple[Any, dict[str, Any]]:
    if int(lineage) not in LINEAGES:
        raise V013OracleError("lineage is outside the frozen V0.13 set")
    config, _ = old_gate._config_pair()
    spec = old_gate._spec_for_seed(Path(v03_root), int(lineage))
    network, receipt = extract_frozen_meanmax_head(
        spec, config, head_index=0, device="cpu"
    )
    network.eval()
    network.requires_grad_(False)
    if any(parameter.requires_grad for parameter in network.parameters()):
        raise V013OracleError("frozen Q1 still has trainable parameters")
    payload = receipt.as_dict()
    payload["parameter_sha256"] = _q1_parameter_sha256(network)
    return network, payload


def executable_authority_snapshot(
    *,
    contract_path: Path,
    prereg_path: Path,
    v03_root: Path,
) -> dict[str, Any]:
    """Authenticate every file that may determine a V0.13 shard outcome."""

    record = read_prereg(Path(prereg_path))
    ephemeris = record.sections.get("ephemeris", {})
    if not isinstance(ephemeris, Mapping) or not isinstance(
        ephemeris.get("file_set_sha256"), str
    ):
        raise V013OracleError("frozen prereg omits the TLE file-set digest")
    checkpoint_hashes: dict[str, str] = {}
    for lineage in LINEAGES:
        checkpoint = (
            Path(v03_root)
            / "checkpoints"
            / f"init-{lineage}-rung-000010.pt"
        )
        checkpoint_hash = file_sha256(checkpoint)
        if checkpoint_hash != old_gate.EXPECTED_V03_CHECKPOINT_SHA256[lineage]:
            raise V013OracleError(f"sealed Q1 checkpoint drifted for lineage {lineage}")
        checkpoint_hashes[str(lineage)] = checkpoint_hash
    v03_receipts = {
        name: file_sha256(Path(v03_root) / name)
        for name in (
            "authority.json",
            "authority-seal.json",
            "result.json",
            "result-seal.json",
        )
    }
    if (
        v03_receipts["authority.json"]
        != old_gate.EXPECTED_V03_AUTHORITY_SHA256
        or v03_receipts["result.json"]
        != old_gate.EXPECTED_V03_RESULT_FILE_SHA256
        or v03_receipts["result-seal.json"]
        != old_gate.EXPECTED_V03_RESULT_SEAL_FILE_SHA256
    ):
        raise V013OracleError("sealed V0.3 source authority drifted")
    return {
        "schema": AUTHORITY_SCHEMA,
        "execution_environment": dict(EXPECTED_EXECUTION_ENVIRONMENT),
        "pyproject_file_sha256": file_sha256(REPO / "pyproject.toml"),
        "contract_receipt_sha256": canonical_sha256(contract_receipt()),
        "contract_file_sha256": file_sha256(Path(contract_path)),
        "runner_file_sha256": file_sha256(Path(__file__).resolve()),
        "runtime_file_sha256": {
            str(path.relative_to(REPO)): file_sha256(path) for path in RUNTIME_PATHS
        },
        "wrapper_file_sha256": {
            str(path.relative_to(REPO)): file_sha256(path) for path in WRAPPER_PATHS
        },
        "python_source_authority": python_source_authority(),
        "base_prereg": {
            "file_sha256": file_sha256(Path(prereg_path)),
            "record_digest": str(record.digest),
            "tle_file_set_sha256": str(ephemeris["file_set_sha256"]),
        },
        "v03_frozen": {
            "receipt_file_sha256": v03_receipts,
            "q1_checkpoint_file_sha256": checkpoint_hashes,
            "q1_head_index": 0,
            "checkpoint_rung": 10,
        },
    }


def validate_frozen_authority(
    authority_path: Path,
    *,
    contract_path: Path,
    prereg_path: Path,
    v03_root: Path,
) -> dict[str, Any]:
    """Require the sealed authority receipt to equal the current file state."""

    payload = read_canonical_json(Path(authority_path))
    if not isinstance(payload, dict):
        raise V013OracleError("frozen authority root is not an object")
    assert_execution_environment()
    expected = executable_authority_snapshot(
        contract_path=Path(contract_path),
        prereg_path=Path(prereg_path),
        v03_root=Path(v03_root),
    )
    if payload != expected:
        raise V013OracleError("frozen executable authority does not match current files")
    return payload


def write_frozen_authority(
    output_path: Path,
    *,
    contract_path: Path,
    prereg_path: Path,
    v03_root: Path,
) -> dict[str, Any]:
    """Create the one pre-outcome authority receipt; never overwrite it."""

    destination = Path(output_path)
    if destination.exists() or destination.is_symlink():
        raise V013OracleError(f"refusing to overwrite {destination}")
    assert_contract_frozen(Path(contract_path))
    payload = executable_authority_snapshot(
        contract_path=Path(contract_path),
        prereg_path=Path(prereg_path),
        v03_root=Path(v03_root),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(temporary_fd, "wb") as handle:
            handle.write(_canonical_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o444)
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            raise V013OracleError(f"refusing to overwrite {destination}") from error
        directory_fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)
    return payload


def _q1_values(network: Any, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
    values = network(
        torch.tensor(np.asarray(states, dtype=np.float32)),
        torch.tensor(np.asarray(masks, dtype=np.bool_)),
    ).detach().cpu().numpy()
    result = np.asarray(values, dtype=np.float64)
    if result.shape != masks.shape or not np.all(np.isfinite(result)):
        raise V013OracleError("Q1 surface is malformed")
    return result


def select_actions(
    q1: np.ndarray,
    o2: np.ndarray,
    o3: np.ndarray,
    mask: np.ndarray,
    *,
    include_c3: bool,
) -> np.ndarray:
    legal = np.asarray(mask)
    arrays = tuple(np.asarray(value, dtype=np.float64) for value in (q1, o2, o3))
    if legal.dtype != np.bool_ or legal.ndim != 2 or legal.shape[1] != NUM_ACTIONS:
        raise V013OracleError(
            f"mask must be a Boolean matrix with {NUM_ACTIONS} native actions"
        )
    if any(
        value.shape != legal.shape or not np.all(np.isfinite(value))
        for value in arrays
    ):
        raise V013OracleError("head surfaces are nonfinite or misaligned")
    if not np.all(np.any(legal, axis=1)):
        raise V013OracleError("each user must have a legal native action")
    scores = arrays[0] + arrays[1]
    if include_c3:
        scores = scores + arrays[2]
    return np.argmax(np.where(legal, scores, -np.inf), axis=1).astype(np.int64)


def _live_digest(environment: Any, rng: np.random.Generator) -> str:
    step_env = environment.environment if hasattr(environment, "environment") else environment
    digest = hashlib.sha256()
    for name, value in (
        ("step", step_env._step_index),
        ("driver_step", step_env.driver.step_index),
        ("previous_power", step_env._previous_link_power_w),
        ("previous_rate", step_env._previous_served_rate_bps),
        ("pending_age", step_env._pending_segment_age),
        ("user_ecef", step_env.driver.user_ecef_km()),
        ("candidate_identity", id(step_env._candidates)),
        ("driver_start_utc", step_env.driver._start_utc),
    ):
        digest.update(name.encode("ascii"))
        if isinstance(value, np.ndarray):
            digest.update(array_sha256(value).encode("ascii"))
        else:
            digest.update(repr(value).encode("utf-8"))
    digest.update(repr(copy.deepcopy(step_env._previous_association)).encode("utf-8"))
    digest.update(repr(copy.deepcopy(step_env._segments)).encode("utf-8"))
    digest.update(repr(copy.deepcopy(step_env._previous_demand)).encode("utf-8"))
    digest.update(
        repr(tuple(ledger.previous for ledger in step_env._ledgers)).encode("utf-8")
    )
    previous_radiating = step_env._previous_radiating
    for name, value in (
        ("previous_radiating_norad", previous_radiating.norad_ids),
        ("previous_radiating_cell", previous_radiating.cell_ids),
        ("previous_radiating_power", previous_radiating.power_w),
    ):
        digest.update(name.encode("ascii"))
        digest.update(array_sha256(value).encode("ascii"))
    digest.update(repr(copy.deepcopy(rng.bit_generator.state)).encode("utf-8"))
    tracker = getattr(step_env.driver, "_tracker", None)
    if tracker is not None:
        digest.update(repr(copy.deepcopy(tracker.__dict__)).encode("utf-8"))
    return digest.hexdigest()


def _initial_world_sha(environment: Any, observation: Any) -> str:
    return canonical_sha256(
        {
            "epoch": environment.epoch.isoformat(),
            "state": array_sha256(observation.state_matrix),
            "mask": array_sha256(observation.masks),
            "norads": array_sha256(
                np.stack(
                    [table.norad_ids for table in observation.candidates.slot_tables]
                )
            ),
            "cells": array_sha256(
                np.stack(
                    [table.cell_ids for table in observation.candidates.slot_tables]
                )
            ),
        }
    )


def _spread_count(values: np.ndarray, mask: np.ndarray) -> int:
    return sum(
        int(np.ptp(values[uid, np.flatnonzero(mask[uid])]) > 0.0)
        for uid in range(mask.shape[0])
    )


def _build_c3_surfaces(
    *,
    formula: str,
    measurements: Any,
    interval_s: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    if float(measurements.interval_s).hex() != float(interval_s).hex():
        raise V013OracleError("live measurement interval drifted from the anchor")
    users = measurements.reference_actions.size
    o3 = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
    identity_passed = True
    positive_count = 0
    positive_supported = 0
    unsupported_positive = 0
    for uid in range(users):
        kwargs = {
            "candidate_rate_bps": measurements.candidate_rate_bps[uid],
            "compatibility": measurements.compatible[uid],
            "legal_mask": measurements.legal_mask[uid],
            "reference_action": int(measurements.reference_actions[uid]),
            "interval_s": float(interval_s),
            "kappa_bits": OPS3_KAPPA_BITS,
        }
        if formula != "ZR":
            raise V013OracleError("unknown C3 formula")
        surface = build_zr_surface(
            baseline_rate_bps=measurements.reference_rate_bps[uid], **kwargs
        )
        identity = assert_surface_identity(surface)
        identity_passed = identity_passed and bool(identity.passed)
        row_positive = surface.q3_values > 0.0
        positive_count += int(np.count_nonzero(row_positive))
        positive_supported += int(
            np.count_nonzero(row_positive & measurements.compatible[uid])
        )
        unsupported_positive += int(
            np.count_nonzero(row_positive & ~measurements.compatible[uid])
        )
        o3[uid] = surface.q3_values
    if unsupported_positive:
        raise V013OracleError("a positive C3 target escaped compatibility support")
    components = {
        "served": int(np.count_nonzero(measurements.served_equal)),
        "active_beams": int(np.count_nonzero(measurements.active_beams_equal)),
        "active_satellites": int(
            np.count_nonzero(measurements.active_satellites_equal)
        ),
        "rf_power": int(np.count_nonzero(measurements.rf_power_equal)),
        "network_power": int(np.count_nonzero(measurements.network_power_equal)),
        "all": int(np.count_nonzero(measurements.compatible)),
    }
    hashed_measurements: list[object] = [
        measurements.reference_actions,
        measurements.legal_mask,
        measurements.reference_rate_bps,
        measurements.candidate_rate_bps,
        measurements.replacement_delta_bits,
        measurements.compatible,
        measurements.served_equal,
        measurements.active_beams_equal,
        measurements.active_satellites_equal,
        measurements.rf_power_equal,
        measurements.network_power_equal,
    ]
    if measurements.removed_rate_bps is not None:
        hashed_measurements.append(measurements.removed_rate_bps)
    if measurements.insertion_delta_bits is not None:
        hashed_measurements.append(measurements.insertion_delta_bits)
    return o3, {
        "formula": formula,
        "identity_passed": identity_passed,
        "positive_target_count": positive_count,
        "supported_positive_target_count": positive_supported,
        "unsupported_positive_target_count": unsupported_positive,
        "compatibility_component_counts": components,
        "counterfactual_evaluations": int(
            measurements.counterfactual_evaluations
        ),
        "reference_signature_sha256": measurements.reference_signature_sha256,
        "measurements_sha256": array_sha256(*hashed_measurements),
    }


def _joint_support_receipt(
    step_env: Any,
    rng: np.random.Generator,
    reference: np.ndarray,
    selected: np.ndarray,
    interval_s: float,
) -> dict[str, Any]:
    changed = int(np.count_nonzero(reference != selected))
    if changed == 0:
        return {
            "status": "NO_EXPOSURE",
            "changed_users": 0,
            "no_new_active_beam": True,
            "no_new_active_satellite": True,
            "network_power_nonincrease": True,
            "passed": True,
        }
    before = _live_digest(step_env, rng)
    baseline = step_env.evaluate_actions(reference, rng)
    treatment = step_env.evaluate_actions(selected, rng)
    after = _live_digest(step_env, rng)
    if before != after:
        raise V013OracleError("joint support diagnostic mutated environment or RNG")
    base_signature = physics_signature(baseline)
    full_signature = physics_signature(treatment)
    base_beams = {
        tuple(int(value) for value in row)
        for row in base_signature.active_beam_keys.tolist()
    }
    full_beams = {
        tuple(int(value) for value in row)
        for row in full_signature.active_beam_keys.tolist()
    }
    base_satellites = set(int(value) for value in base_signature.active_satellites)
    full_satellites = set(int(value) for value in full_signature.active_satellites)
    tolerance = 1024.0 * np.finfo(np.float64).eps * max(
        1.0,
        abs(base_signature.system_power_w),
        abs(full_signature.system_power_w),
    )
    no_new_beam = full_beams <= base_beams
    no_new_satellite = full_satellites <= base_satellites
    power_nonincrease = (
        full_signature.system_power_w
        <= base_signature.system_power_w + tolerance
    )
    delta_bits = float(interval_s) * math.fsum(
        float(value)
        for value in (
            np.asarray(treatment.link_rate_bps, dtype=np.float64)
            - np.asarray(baseline.link_rate_bps, dtype=np.float64)
        )
    )
    delta_energy = float(interval_s) * (
        float(treatment.system_power_w) - float(baseline.system_power_w)
    )
    return {
        "status": "OBSERVED",
        "changed_users": changed,
        "delta_bits": delta_bits,
        "delta_energy_j": delta_energy,
        "baseline_active_beams": len(base_beams),
        "selected_active_beams": len(full_beams),
        "baseline_active_satellites": len(base_satellites),
        "selected_active_satellites": len(full_satellites),
        "baseline_network_power_w": base_signature.system_power_w,
        "selected_network_power_w": full_signature.system_power_w,
        "power_tolerance_w": tolerance,
        "new_active_beams": sorted(full_beams - base_beams),
        "new_active_satellites": sorted(full_satellites - base_satellites),
        "no_new_active_beam": no_new_beam,
        "no_new_active_satellite": no_new_satellite,
        "network_power_nonincrease": power_nonincrease,
        "passed": bool(no_new_beam and no_new_satellite and power_nonincrease),
    }


def evaluate_episode(
    *,
    q1: Any,
    q1_receipt: Mapping[str, Any],
    archive: Any,
    world_seed: int,
    field: KeyedFadingField,
    lineage: int,
    arm: str,
) -> dict[str, Any]:
    if arm not in ARMS or int(lineage) not in LINEAGES:
        raise V013OracleError("episode arm/lineage is outside the frozen panel")
    if int(world_seed) not in WORLD_SEEDS:
        raise V013OracleError("episode world is outside the frozen panel")
    if field.root_digest != field_for_world(world_seed).root_digest:
        raise V013OracleError("episode does not use its frozen common field")

    environment = screen._make_environment(archive, users=USERS)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = screen._evaluation_rngs(
        int(world_seed)
    )
    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    step_env = environment.environment
    interval_s = float(step_env.driver.config.ephemeris.time_step_s)
    initial_world = _initial_world_sha(environment, observation)
    q1_before = _q1_parameter_sha256(q1)
    started = time.perf_counter()

    total_bits = 0.0
    total_energy = 0.0
    served_steps = 0
    active_beam_steps = 0
    active_satellite_steps = 0
    c3_spread = 0
    positive_targets = 0
    supported_positive_targets = 0
    action_exposure = 0
    compatible_action_count = 0
    changed_actions_compatible = True
    joint_support_passed = True
    method_passed = True
    per_step: list[dict[str, Any]] = []

    with torch.no_grad():
        for step_index in range(STEPS_PER_EPISODE):
            native = encode_ee_axis_state(step_env, observation)
            mask = np.asarray(native.action_masks, dtype=np.bool_)
            q1_values = _q1_values(q1, native.state_matrix, mask)
            zero = np.zeros_like(q1_values)
            q1_reference = select_actions(
                q1_values, zero, zero, mask, include_c3=False
            )
            before = _live_digest(environment, env_rng)
            anchor = snapshot_ops3_anchor(step_env, observation)
            projection = project_ops3_anchor(anchor)
            ops3 = build_ops3_live_surfaces(anchor, projection, q1_reference)
            o2 = np.stack(
                [np.asarray(surface.q2_values, dtype=np.float64) for surface in ops3]
            )
            o2_sha_before = array_sha256(o2)
            background = select_actions(
                q1_values, o2, zero, mask, include_c3=False
            )
            selected = np.array(background, dtype=np.int64, copy=True)
            o3 = np.zeros_like(q1_values)
            method: dict[str, Any] = {
                "kind": "DROP_C3",
                "identity_passed": True,
                "positive_target_count": 0,
                "supported_positive_target_count": 0,
                "compatibility_component_counts": {
                    name: 0
                    for name in (
                        "served",
                        "active_beams",
                        "active_satellites",
                        "rf_power",
                        "network_power",
                        "all",
                    )
                },
            }
            measurements = None

            if arm == "FULL_ZR":
                formula = "ZR"
                measurements = measure_zero_marginal_c3(
                    step_env,
                    observation=observation,
                    reference_actions=background,
                    rng=env_rng,
                    include_insertion=False,
                    interval_s=interval_s,
                )
                o3, method = _build_c3_surfaces(
                    formula=formula,
                    measurements=measurements,
                    interval_s=interval_s,
                )
                selected = select_actions(
                    q1_values, o2, o3, mask, include_c3=True
                )

            reference_zero = all(
                float(o2[uid, int(q1_reference[uid])]) == 0.0
                for uid in range(USERS)
            ) and all(
                float(o3[uid, int(background[uid])]) == 0.0
                for uid in range(USERS)
            )
            illegal_zero = bool(np.all(o3[~mask] == 0.0))
            base_evaluation = step_env.evaluate_actions(background, env_rng)
            opening_equal = all(
                bool(ops3[uid].opening_service_feasible[int(background[uid])])
                == bool(base_evaluation.resolution.served[uid])
                for uid in range(USERS)
            )
            after = _live_digest(environment, env_rng)
            changed = np.flatnonzero(selected != background)
            step_changed_compatible = True
            changed_positive = True
            if measurements is not None:
                for uid_raw in changed.tolist():
                    uid = int(uid_raw)
                    action = int(selected[uid])
                    step_changed_compatible = step_changed_compatible and bool(
                        measurements.compatible[uid, action]
                    )
                    changed_positive = changed_positive and bool(o3[uid, action] > 0.0)
            elif changed.size:
                raise V013OracleError("DROP_C3 changed from its own background")
            if not step_changed_compatible or not changed_positive:
                raise V013OracleError(
                    "a changed production action lacks positive compatible C3 credit"
                )
            joint_support = _joint_support_receipt(
                step_env, env_rng, background, selected, interval_s
            )
            mechanics = {
                "live_state_and_rng_unchanged": before == after,
                "common_mask": all(
                    np.array_equal(surface.legal_mask, mask[uid])
                    for uid, surface in enumerate(ops3)
                )
                and (measurements is None or np.array_equal(measurements.legal_mask, mask)),
                "reference_rows_exact_zero": reference_zero,
                "illegal_rows_exact_zero": illegal_zero,
                "opening_service_gate_equal": opening_equal,
                "o2_immutable": o2_sha_before == array_sha256(o2),
                "changed_actions_compatible": step_changed_compatible,
                "changed_actions_strictly_positive_c3": changed_positive,
                "joint_support_passed": bool(joint_support["passed"]),
                "background_sha256": array_sha256(background),
            }
            mechanics["passed"] = bool(
                all(
                    value
                    for key, value in mechanics.items()
                    if key
                    not in {
                        "background_sha256",
                        # This is a binding outcome gate, not a plumbing
                        # assertion.  Retain and execute the safe production
                        # action so a failing shard yields a complete receipt.
                        "joint_support_passed",
                        "passed",
                    }
                )
            )
            if not mechanics["passed"]:
                raise V013OracleError("binding per-step mechanics failed")

            flips = int(changed.size)
            step_spread = _spread_count(o3, mask)
            action_exposure += flips
            c3_spread += step_spread
            positive_targets += int(method["positive_target_count"])
            supported_positive_targets += int(
                method["supported_positive_target_count"]
            )
            compatible_action_count += int(
                method["compatibility_component_counts"]["all"]
            )
            changed_actions_compatible = (
                changed_actions_compatible and step_changed_compatible
            )
            joint_support_passed = joint_support_passed and bool(
                joint_support["passed"]
            )
            method_passed = method_passed and bool(method["identity_passed"])

            result = environment.step(selected, env_rng)
            outcome = environment.last_outcome
            rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
            power = float(outcome.system_power_w)
            if (
                rates.shape != (USERS,)
                or not np.all(np.isfinite(rates))
                or np.any(rates < 0.0)
                or not math.isfinite(power)
                or power <= 0.0
            ):
                raise V013OracleError("canonical EE inputs are malformed")
            bits = interval_s * math.fsum(float(value) for value in rates)
            energy = interval_s * power
            active_beams = int(outcome.radiating.count)
            active_satellites = len(
                {int(value) for value in outcome.radiating.norad_ids.tolist()}
            )
            total_bits += bits
            total_energy += energy
            served_steps += int(outcome.resolution.served_count)
            active_beam_steps += active_beams
            active_satellite_steps += active_satellites
            per_step.append(
                {
                    "step_index": step_index,
                    "total_bits": float(bits),
                    "total_energy_j": float(energy),
                    "served_user_steps": int(outcome.resolution.served_count),
                    "active_beam_count": active_beams,
                    "active_satellite_count": active_satellites,
                    "action_exposure": flips,
                    "c3_legal_spread_count": step_spread,
                    "selected_actions": [int(value) for value in selected.tolist()],
                    "surface_sha256": {
                        "q1": array_sha256(q1_values),
                        "o2": array_sha256(o2),
                        "o3": array_sha256(o3),
                        "mask": array_sha256(mask),
                        "q1_reference": array_sha256(q1_reference),
                        "background": array_sha256(background),
                    },
                    "mechanics": mechanics,
                    "method": method,
                    "joint_support": joint_support,
                }
            )
            if result.done:
                if step_index != STEPS_PER_EPISODE - 1:
                    raise V013OracleError("episode terminated before ten steps")
                break
            observation = outcome.observation

    q1_after = _q1_parameter_sha256(q1)
    if q1_before != q1_after:
        raise V013OracleError("frozen Q1 changed during oracle episode")
    return {
        "schema": EPISODE_SCHEMA,
        "arm": arm,
        "initialization_seed": int(lineage),
        "world_seed": int(world_seed),
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "users": USERS,
        "steps": STEPS_PER_EPISODE,
        "initial_world_sha256": initial_world,
        "field_root_digest": field.root_digest,
        "q1_checkpoint": dict(q1_receipt),
        "q1_parameter_sha256_before": q1_before,
        "q1_parameter_sha256_after": q1_after,
        "total_bits": float(total_bits),
        "total_energy_j": float(total_energy),
        "ratio_of_sums_ee_bits_per_j": float(total_bits / total_energy),
        "served_user_steps": served_steps,
        "served_fraction": served_steps / (USERS * STEPS_PER_EPISODE),
        "active_beam_steps": active_beam_steps,
        "active_satellite_steps": active_satellite_steps,
        "c3_legal_spread_count": c3_spread,
        "positive_target_count": positive_targets,
        "supported_positive_target_count": supported_positive_targets,
        "compatible_action_count": compatible_action_count,
        "action_exposure": action_exposure,
        "changed_actions_compatible": changed_actions_compatible,
        "joint_support_passed": joint_support_passed,
        "method_passed": method_passed,
        "candidate_specific_identity_passed": method_passed,
        "mechanics_passed": all(step["mechanics"]["passed"] for step in per_step),
        "per_step": per_step,
        "elapsed_s": time.perf_counter() - started,
    }


def run_shard(
    *,
    world_seed: int,
    arm: str,
    lineage: int,
    output_dir: Path,
    tle_root: Path,
    prereg_path: Path,
    v03_root: Path,
    contract_path: Path = CONTRACT_PATH,
    authority_path: Path = FROZEN_AUTHORITY_PATH,
) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V013OracleError(f"refusing to overwrite {output}")
    assert_contract_frozen(contract_path)
    authority_before = validate_frozen_authority(
        Path(authority_path),
        contract_path=Path(contract_path),
        prereg_path=Path(prereg_path),
        v03_root=Path(v03_root),
    )
    record = read_prereg(prereg_path)
    q1, q1_receipt = load_frozen_q1(v03_root, lineage)
    if q1_receipt.get("checkpoint_sha256") != authority_before["v03_frozen"][
        "q1_checkpoint_file_sha256"
    ][str(lineage)]:
        raise V013OracleError("loaded Q1 disagrees with frozen executable authority")
    field = field_for_world(world_seed)
    with tempfile.TemporaryDirectory(prefix="mcrl-v013-zero-energy-tle-") as temporary:
        archive = screen._frozen_archive(
            record, Path(tle_root), Path(temporary) / "frozen-tle"
        )
        row = evaluate_episode(
            q1=q1,
            q1_receipt=q1_receipt,
            archive=archive,
            world_seed=int(world_seed),
            field=field,
            lineage=int(lineage),
            arm=arm,
        )
    authority_after = executable_authority_snapshot(
        contract_path=Path(contract_path),
        prereg_path=Path(prereg_path),
        v03_root=Path(v03_root),
    )
    assert_execution_environment()
    if authority_after != authority_before:
        raise V013OracleError("executable authority changed while a shard was running")
    contract = contract_receipt()
    base_prereg = authority_before["base_prereg"]
    source_authority = {
        "prereg_file_sha256": base_prereg["file_sha256"],
        "prereg_record_digest": base_prereg["record_digest"],
        "tle_file_set_sha256": base_prereg["tle_file_set_sha256"],
        **authority_before["python_source_authority"],
    }
    payload = {
        "schema": SHARD_SCHEMA,
        "shard_id": f"{int(world_seed)}-{arm}-{int(lineage)}",
        "contract": contract,
        "contract_sha256": canonical_sha256(contract),
        "contract_file_sha256": file_sha256(Path(contract_path)),
        "runner_file_sha256": file_sha256(Path(__file__).resolve()),
        "runtime_file_sha256": {
            str(path.relative_to(REPO)): file_sha256(path) for path in RUNTIME_PATHS
        },
        "wrapper_file_sha256": authority_before["wrapper_file_sha256"],
        "source_authority": source_authority,
        "frozen_authority": authority_before,
        "frozen_authority_file_sha256": file_sha256(Path(authority_path)),
        "row": row,
    }
    payload["row_sha256"] = canonical_sha256(row)
    output.mkdir(parents=True, exist_ok=False)
    (output / "shard.json").write_bytes(_canonical_bytes(payload))
    print(
        f"{world_seed}/{arm}/{lineage}: "
        f"EE={row['ratio_of_sums_ee_bits_per_j']:.9g} "
        f"elapsed={row['elapsed_s']:.1f}s"
    )
    return payload


def _validate_step_receipt(
    step: object, *, row_index: int, step_index: int, arm: str
) -> None:
    receipt = _exact_keys(
        step,
        {
            "step_index",
            "total_bits",
            "total_energy_j",
            "served_user_steps",
            "active_beam_count",
            "active_satellite_count",
            "action_exposure",
            "c3_legal_spread_count",
            "selected_actions",
            "surface_sha256",
            "mechanics",
            "method",
            "joint_support",
        },
        field=f"row[{row_index}].step[{step_index}]",
    )
    _require_exact(receipt.get("step_index"), step_index, field="step_index")
    bits = _finite_number(receipt.get("total_bits"), field="step.total_bits")
    energy = _finite_number(
        receipt.get("total_energy_j"), field="step.total_energy_j"
    )
    if bits < 0.0 or energy <= 0.0:
        raise V013OracleError("step canonical EE inputs are invalid")
    served = _nonnegative_int(
        receipt.get("served_user_steps"), field="step.served_user_steps"
    )
    if served > USERS:
        raise V013OracleError("step served-user count exceeds the frozen population")
    for name in (
        "active_beam_count",
        "active_satellite_count",
        "action_exposure",
        "c3_legal_spread_count",
    ):
        count = _nonnegative_int(receipt.get(name), field=f"step.{name}")
        if name in {"action_exposure", "c3_legal_spread_count"} and count > USERS:
            raise V013OracleError(f"step.{name} exceeds the frozen population")

    actions = receipt.get("selected_actions")
    if (
        not isinstance(actions, list)
        or len(actions) != USERS
        or any(type(value) is not int or not 0 <= value < NUM_ACTIONS for value in actions)
    ):
        raise V013OracleError("step selected_actions is not 100 native actions")
    hashes = _exact_keys(
        receipt.get("surface_sha256"),
        {"q1", "o2", "o3", "mask", "q1_reference", "background"},
        field="step.surface_sha256",
    )
    for name, value in hashes.items():
        _sha256_text(value, field=f"step.surface_sha256.{name}")

    mechanics = _exact_keys(
        receipt.get("mechanics"),
        {
            "live_state_and_rng_unchanged",
            "common_mask",
            "reference_rows_exact_zero",
            "illegal_rows_exact_zero",
            "opening_service_gate_equal",
            "o2_immutable",
            "changed_actions_compatible",
            "changed_actions_strictly_positive_c3",
            "joint_support_passed",
            "background_sha256",
            "passed",
        },
        field="step.mechanics",
    )
    mechanic_flags = (
        "live_state_and_rng_unchanged",
        "common_mask",
        "reference_rows_exact_zero",
        "illegal_rows_exact_zero",
        "opening_service_gate_equal",
        "o2_immutable",
        "changed_actions_compatible",
        "changed_actions_strictly_positive_c3",
        "joint_support_passed",
        "passed",
    )
    for name in mechanic_flags:
        _bool(mechanics.get(name), field=f"step.mechanics.{name}")
    _sha256_text(mechanics.get("background_sha256"), field="step.mechanics.background")
    recomputed_mechanics = all(
        mechanics[name]
        for name in mechanic_flags
        if name not in {"joint_support_passed", "passed"}
    )
    if mechanics["passed"] is not recomputed_mechanics:
        raise V013OracleError("step mechanics.passed does not recompute")

    method = receipt.get("method")
    common_method_keys = {
        "identity_passed",
        "positive_target_count",
        "supported_positive_target_count",
        "compatibility_component_counts",
    }
    expected_method_keys = (
        common_method_keys | {"kind"}
        if arm == "DROP_C3"
        else common_method_keys
        | {
            "formula",
            "unsupported_positive_target_count",
            "counterfactual_evaluations",
            "reference_signature_sha256",
            "measurements_sha256",
        }
    )
    method_map = _exact_keys(method, expected_method_keys, field="step.method")
    _bool(method_map.get("identity_passed"), field="step.method.identity_passed")
    positive = _nonnegative_int(
        method_map.get("positive_target_count"), field="step.method.positive"
    )
    supported_positive = _nonnegative_int(
        method_map.get("supported_positive_target_count"),
        field="step.method.supported_positive",
    )
    if supported_positive > positive:
        raise V013OracleError("supported-positive count exceeds positive count")
    components = _exact_keys(
        method_map.get("compatibility_component_counts"),
        {"served", "active_beams", "active_satellites", "rf_power", "network_power", "all"},
        field="step.method.compatibility_component_counts",
    )
    component_counts = {
        name: _nonnegative_int(value, field=f"step.method.compatibility.{name}")
        for name, value in components.items()
    }
    if any(value > USERS * NUM_ACTIONS for value in component_counts.values()):
        raise V013OracleError("compatibility component count is out of bounds")
    if arm == "DROP_C3":
        _require_exact(method_map.get("kind"), "DROP_C3", field="step.method.kind")
        if (
            positive != 0
            or supported_positive != 0
            or any(component_counts.values())
            or receipt["action_exposure"] != 0
            or receipt["c3_legal_spread_count"] != 0
        ):
            raise V013OracleError("DROP_C3 contains C3 method activity")
        if hashes["background"] != mechanics["background_sha256"]:
            raise V013OracleError("DROP_C3 background hashes disagree")
        if array_sha256(np.asarray(actions, dtype=np.int64)) != hashes["background"]:
            raise V013OracleError("DROP_C3 selected actions differ from its background")
    else:
        _require_exact(method_map.get("formula"), "ZR", field="step.method.formula")
        unsupported = _nonnegative_int(
            method_map.get("unsupported_positive_target_count"),
            field="step.method.unsupported_positive",
        )
        if unsupported != 0:
            raise V013OracleError("positive C3 target escaped compatibility support")
        _nonnegative_int(
            method_map.get("counterfactual_evaluations"),
            field="step.method.counterfactual_evaluations",
        )
        _sha256_text(
            method_map.get("reference_signature_sha256"),
            field="step.method.reference_signature_sha256",
        )
        _sha256_text(
            method_map.get("measurements_sha256"),
            field="step.method.measurements_sha256",
        )

    joint = receipt.get("joint_support")
    if not isinstance(joint, Mapping):
        raise V013OracleError("step joint_support is not an object")
    status = joint.get("status")
    short_joint_keys = {
        "status",
        "changed_users",
        "no_new_active_beam",
        "no_new_active_satellite",
        "network_power_nonincrease",
        "passed",
    }
    observed_joint_keys = short_joint_keys | {
        "delta_bits",
        "delta_energy_j",
        "baseline_active_beams",
        "selected_active_beams",
        "baseline_active_satellites",
        "selected_active_satellites",
        "baseline_network_power_w",
        "selected_network_power_w",
        "power_tolerance_w",
        "new_active_beams",
        "new_active_satellites",
    }
    _exact_keys(
        joint,
        short_joint_keys if status == "NO_EXPOSURE" else observed_joint_keys,
        field="step.joint_support",
    )
    if status not in {"NO_EXPOSURE", "OBSERVED"}:
        raise V013OracleError("step joint_support status is invalid")
    changed_users = _nonnegative_int(
        joint.get("changed_users"), field="step.joint_support.changed_users"
    )
    if changed_users != receipt["action_exposure"] or (
        (status == "NO_EXPOSURE") != (changed_users == 0)
    ):
        raise V013OracleError("step joint-support exposure is inconsistent")
    for name in (
        "no_new_active_beam",
        "no_new_active_satellite",
        "network_power_nonincrease",
        "passed",
    ):
        _bool(joint.get(name), field=f"step.joint_support.{name}")
    if status == "OBSERVED":
        for name in (
            "delta_bits",
            "delta_energy_j",
            "baseline_network_power_w",
            "selected_network_power_w",
            "power_tolerance_w",
        ):
            number = _finite_number(joint.get(name), field=f"step.joint_support.{name}")
            if name.endswith("network_power_w") and number <= 0.0:
                raise V013OracleError("joint-support network power is not positive")
            if name == "power_tolerance_w" and number < 0.0:
                raise V013OracleError("joint-support power tolerance is negative")
        for name in (
            "baseline_active_beams",
            "selected_active_beams",
            "baseline_active_satellites",
            "selected_active_satellites",
        ):
            _nonnegative_int(joint.get(name), field=f"step.joint_support.{name}")
        new_beams = joint.get("new_active_beams")
        new_sats = joint.get("new_active_satellites")
        if (
            not isinstance(new_beams, list)
            or any(
                not isinstance(pair, list)
                or len(pair) != 2
                or any(type(value) is not int for value in pair)
                for pair in new_beams
            )
            or not isinstance(new_sats, list)
            or any(type(value) is not int for value in new_sats)
        ):
            raise V013OracleError("joint-support new-resource lists are malformed")
        if joint["no_new_active_beam"] != (len(new_beams) == 0) or joint[
            "no_new_active_satellite"
        ] != (len(new_sats) == 0):
            raise V013OracleError("joint-support resource flags do not recompute")
        recomputed_power = joint["selected_network_power_w"] <= (
            joint["baseline_network_power_w"] + joint["power_tolerance_w"]
        )
        if joint["network_power_nonincrease"] is not recomputed_power:
            raise V013OracleError("joint-support power flag does not recompute")
    recomputed_joint = bool(
        joint["no_new_active_beam"]
        and joint["no_new_active_satellite"]
        and joint["network_power_nonincrease"]
    )
    if joint["passed"] is not recomputed_joint:
        raise V013OracleError("step joint-support passed flag does not recompute")
    if mechanics["joint_support_passed"] is not joint["passed"]:
        raise V013OracleError("step mechanics and joint-support flags disagree")


def _validate_row_receipt(row: object, *, row_index: int) -> dict[str, Any]:
    receipt = _exact_keys(
        row,
        {
            "schema",
            "arm",
            "initialization_seed",
            "world_seed",
            "split",
            "test_split_opened",
            "episode_training",
            "learner_update",
            "users",
            "steps",
            "initial_world_sha256",
            "field_root_digest",
            "q1_checkpoint",
            "q1_parameter_sha256_before",
            "q1_parameter_sha256_after",
            "total_bits",
            "total_energy_j",
            "ratio_of_sums_ee_bits_per_j",
            "served_user_steps",
            "served_fraction",
            "active_beam_steps",
            "active_satellite_steps",
            "c3_legal_spread_count",
            "positive_target_count",
            "supported_positive_target_count",
            "compatible_action_count",
            "action_exposure",
            "changed_actions_compatible",
            "joint_support_passed",
            "method_passed",
            "candidate_specific_identity_passed",
            "mechanics_passed",
            "per_step",
            "elapsed_s",
        },
        field=f"row[{row_index}]",
    )
    _require_exact(receipt.get("schema"), EPISODE_SCHEMA, field="row.schema")
    world = receipt.get("world_seed")
    lineage = receipt.get("initialization_seed")
    arm = receipt.get("arm")
    if (
        type(world) is not int
        or world not in WORLD_SEEDS
        or type(lineage) is not int
        or lineage not in LINEAGES
        or type(arm) is not str
        or arm not in ARMS
    ):
        raise V013OracleError("row has an unfrozen world, arm, or lineage")
    _require_exact(receipt.get("split"), "TRAIN", field="row.split")
    for name in ("test_split_opened", "episode_training", "learner_update"):
        _require_exact(receipt.get(name), False, field=f"row.{name}")
    _require_exact(receipt.get("users"), USERS, field="row.users")
    _require_exact(receipt.get("steps"), STEPS_PER_EPISODE, field="row.steps")
    _sha256_text(receipt.get("initial_world_sha256"), field="row.initial_world")
    _sha256_text(receipt.get("field_root_digest"), field="row.field_root")

    checkpoint = _exact_keys(
        receipt.get("q1_checkpoint"),
        {
            "checkpoint_path",
            "checkpoint_sha256",
            "parameter_sha256",
            "authority_sha256",
            "initialization_seed",
            "rung",
            "head_index",
            "trainer_algorithm",
            "config_sha256",
        },
        field="row.q1_checkpoint",
    )
    checkpoint_path = checkpoint.get("checkpoint_path")
    if (
        not isinstance(checkpoint_path, str)
        or Path(checkpoint_path).name != f"init-{lineage}-rung-000010.pt"
    ):
        raise V013OracleError("row Q1 checkpoint path is not the frozen rung")
    for name in ("checkpoint_sha256", "parameter_sha256", "authority_sha256", "config_sha256"):
        _sha256_text(checkpoint.get(name), field=f"row.q1_checkpoint.{name}")
    _require_exact(checkpoint.get("initialization_seed"), lineage, field="Q1 lineage")
    _require_exact(checkpoint.get("rung"), 10, field="Q1 rung")
    _require_exact(checkpoint.get("head_index"), 0, field="Q1 head")
    if not isinstance(checkpoint.get("trainer_algorithm"), str) or not checkpoint[
        "trainer_algorithm"
    ]:
        raise V013OracleError("row Q1 trainer algorithm is malformed")
    before = _sha256_text(
        receipt.get("q1_parameter_sha256_before"), field="row.Q1.before"
    )
    after = _sha256_text(
        receipt.get("q1_parameter_sha256_after"), field="row.Q1.after"
    )
    if before != after or before != checkpoint["parameter_sha256"]:
        raise V013OracleError("row frozen Q1 hashes disagree")

    bits = _finite_number(receipt.get("total_bits"), field="row.total_bits")
    energy = _finite_number(receipt.get("total_energy_j"), field="row.total_energy_j")
    if bits < 0.0 or energy <= 0.0:
        raise V013OracleError("row canonical EE inputs are invalid")
    ratio = _finite_number(
        receipt.get("ratio_of_sums_ee_bits_per_j"), field="row.ratio_of_sums_ee"
    )
    if ratio != bits / energy:
        raise V013OracleError("row ratio-of-sums EE does not recompute")
    counts = {}
    for name in (
        "served_user_steps",
        "active_beam_steps",
        "active_satellite_steps",
        "c3_legal_spread_count",
        "positive_target_count",
        "supported_positive_target_count",
        "compatible_action_count",
        "action_exposure",
    ):
        counts[name] = _nonnegative_int(receipt.get(name), field=f"row.{name}")
    if counts["served_user_steps"] > USERS * STEPS_PER_EPISODE:
        raise V013OracleError("row served-user count is out of bounds")
    fraction = _finite_number(receipt.get("served_fraction"), field="row.served_fraction")
    if fraction != counts["served_user_steps"] / (USERS * STEPS_PER_EPISODE):
        raise V013OracleError("row served fraction does not recompute")
    flags = {}
    for name in (
        "changed_actions_compatible",
        "joint_support_passed",
        "method_passed",
        "candidate_specific_identity_passed",
        "mechanics_passed",
    ):
        flags[name] = _bool(receipt.get(name), field=f"row.{name}")
    elapsed = _finite_number(receipt.get("elapsed_s"), field="row.elapsed_s")
    if elapsed < 0.0:
        raise V013OracleError("row elapsed time is negative")

    per_step = receipt.get("per_step")
    if not isinstance(per_step, list) or len(per_step) != STEPS_PER_EPISODE:
        raise V013OracleError("row per-step coverage is not exactly ten")
    for step_index, step in enumerate(per_step):
        _validate_step_receipt(
            step, row_index=row_index, step_index=step_index, arm=arm
        )
    summed_bits = 0.0
    summed_energy = 0.0
    summed_counts = {
        "served_user_steps": 0,
        "active_beam_steps": 0,
        "active_satellite_steps": 0,
        "c3_legal_spread_count": 0,
        "positive_target_count": 0,
        "supported_positive_target_count": 0,
        "compatible_action_count": 0,
        "action_exposure": 0,
    }
    recomputed_flags = {
        "changed_actions_compatible": True,
        "joint_support_passed": True,
        "method_passed": True,
        "mechanics_passed": True,
    }
    for step in per_step:
        summed_bits += step["total_bits"]
        summed_energy += step["total_energy_j"]
        summed_counts["served_user_steps"] += step["served_user_steps"]
        summed_counts["active_beam_steps"] += step["active_beam_count"]
        summed_counts["active_satellite_steps"] += step["active_satellite_count"]
        summed_counts["c3_legal_spread_count"] += step["c3_legal_spread_count"]
        summed_counts["action_exposure"] += step["action_exposure"]
        method = step["method"]
        mechanics = step["mechanics"]
        joint = step["joint_support"]
        summed_counts["positive_target_count"] += method["positive_target_count"]
        summed_counts["supported_positive_target_count"] += method[
            "supported_positive_target_count"
        ]
        summed_counts["compatible_action_count"] += method[
            "compatibility_component_counts"
        ]["all"]
        recomputed_flags["changed_actions_compatible"] &= mechanics[
            "changed_actions_compatible"
        ]
        recomputed_flags["joint_support_passed"] &= joint["passed"]
        recomputed_flags["method_passed"] &= method["identity_passed"]
        recomputed_flags["mechanics_passed"] &= mechanics["passed"]
    if summed_bits != bits or summed_energy != energy:
        raise V013OracleError("row EE totals do not match its ten step receipts")
    if any(summed_counts[name] != counts[name] for name in summed_counts):
        raise V013OracleError("row count totals do not match its ten step receipts")
    if any(recomputed_flags[name] is not flags[name] for name in recomputed_flags):
        raise V013OracleError("row Boolean summaries do not match its step receipts")
    if flags["candidate_specific_identity_passed"] is not flags["method_passed"]:
        raise V013OracleError("row method and identity summaries disagree")
    if arm == "DROP_C3" and (
        counts["action_exposure"] != 0
        or counts["c3_legal_spread_count"] != 0
        or counts["positive_target_count"] != 0
        or counts["supported_positive_target_count"] != 0
        or counts["compatible_action_count"] != 0
    ):
        raise V013OracleError("DROP_C3 row contains C3 activity")
    return dict(receipt)


def _pool(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise V013OracleError("cannot pool an empty row set")
    bits = math.fsum(float(row["total_bits"]) for row in rows)
    energy = math.fsum(float(row["total_energy_j"]) for row in rows)
    served = sum(int(row["served_user_steps"]) for row in rows)
    return {
        "row_count": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "served_fraction": served / (len(rows) * USERS * STEPS_PER_EPISODE),
        "active_beam_steps": sum(int(row["active_beam_steps"]) for row in rows),
        "active_satellite_steps": sum(
            int(row["active_satellite_steps"]) for row in rows
        ),
        "c3_legal_spread_count": sum(
            int(row["c3_legal_spread_count"]) for row in rows
        ),
        "supported_positive_target_count": sum(
            int(row["supported_positive_target_count"]) for row in rows
        ),
        "compatible_action_count": sum(
            int(row["compatible_action_count"]) for row in rows
        ),
        "action_exposure": sum(int(row["action_exposure"]) for row in rows),
    }


def _pair_gate(
    *,
    label: str,
    full_arm: str,
    rows: Sequence[Mapping[str, Any]],
    pooled_by_arm: Mapping[str, Mapping[str, Any]],
    pooled_by_world_and_arm: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    drop_arm = "DROP_C3"
    indexed = {
        (
            int(row["world_seed"]),
            str(row["arm"]),
            int(row["initialization_seed"]),
        ): row
        for row in rows
    }
    full_pool = pooled_by_arm[full_arm]
    drop_pool = pooled_by_arm[drop_arm]
    full_ee = float(full_pool["ratio_of_sums_ee_bits_per_j"])
    drop_ee = float(drop_pool["ratio_of_sums_ee_bits_per_j"])
    pooled_delta = full_ee - drop_ee
    by_world: dict[str, Any] = {}
    every_world_positive = True
    every_world_service = True
    every_world_energy = True
    every_world_lineages = True
    every_world_service_lineages = True

    for world in WORLD_SEEDS:
        full_world = pooled_by_world_and_arm[str(world)][full_arm]
        drop_world = pooled_by_world_and_arm[str(world)][drop_arm]
        world_delta = float(full_world["ratio_of_sums_ee_bits_per_j"]) - float(
            drop_world["ratio_of_sums_ee_bits_per_j"]
        )
        positive_lineages = 0
        service_lineages = 0
        lineage_receipts: dict[str, Any] = {}
        for lineage in LINEAGES:
            full = indexed[(world, full_arm, lineage)]
            drop = indexed[(world, drop_arm, lineage)]
            delta = float(full["ratio_of_sums_ee_bits_per_j"]) - float(
                drop["ratio_of_sums_ee_bits_per_j"]
            )
            service_delta = int(full["served_user_steps"]) - int(
                drop["served_user_steps"]
            )
            positive_lineages += int(delta > 0.0)
            service_lineages += int(service_delta >= 0)
            lineage_receipts[str(lineage)] = {
                "delta_ee_bits_per_j": delta,
                "relative_delta_ee": delta
                / float(drop["ratio_of_sums_ee_bits_per_j"]),
                "delta_served_user_steps": service_delta,
                "delta_active_beam_steps": int(full["active_beam_steps"])
                - int(drop["active_beam_steps"]),
                "delta_active_satellite_steps": int(
                    full["active_satellite_steps"]
                )
                - int(drop["active_satellite_steps"]),
            }
        world_service = int(full_world["served_user_steps"]) >= int(
            drop_world["served_user_steps"]
        )
        # This is deliberately an exact trajectory-resource guard.  Unlike
        # active-beam/satellite counts, total energy is the quantity present
        # in the canonical EE denominator and is therefore binding here.
        world_energy = float(full_world["total_energy_j"]) <= float(
            drop_world["total_energy_j"]
        )
        every_world_positive = every_world_positive and world_delta > 0.0
        every_world_service = every_world_service and world_service
        every_world_energy = every_world_energy and world_energy
        every_world_lineages = every_world_lineages and positive_lineages >= 2
        every_world_service_lineages = (
            every_world_service_lineages and service_lineages >= 2
        )
        by_world[str(world)] = {
            "delta_ee_bits_per_j": world_delta,
            "relative_delta_ee": world_delta
            / float(drop_world["ratio_of_sums_ee_bits_per_j"]),
            "delta_served_user_steps": int(full_world["served_user_steps"])
            - int(drop_world["served_user_steps"]),
            "delta_active_beam_steps": int(full_world["active_beam_steps"])
            - int(drop_world["active_beam_steps"]),
            "delta_active_satellite_steps": int(
                full_world["active_satellite_steps"]
            )
            - int(drop_world["active_satellite_steps"]),
            "delta_total_energy_j": float(full_world["total_energy_j"])
            - float(drop_world["total_energy_j"]),
            "positive_lineages": positive_lineages,
            "service_noninferior_lineages": service_lineages,
            "pooled_service_noninferior": world_service,
            "total_trajectory_energy_nonincrease": world_energy,
            # Retained as diagnostics only; neither count can stop V0.13.
            "active_beam_steps_not_above_diagnostic": int(
                full_world["active_beam_steps"]
            )
            <= int(drop_world["active_beam_steps"]),
            "active_satellite_steps_not_above_diagnostic": int(
                full_world["active_satellite_steps"]
            )
            <= int(drop_world["active_satellite_steps"]),
            "by_lineage": lineage_receipts,
        }

    full_rows = [row for row in rows if str(row["arm"]) == full_arm]
    drop_rows = [row for row in rows if str(row["arm"]) == drop_arm]
    mechanics = all(
        bool(row["mechanics_passed"]) for row in (*full_rows, *drop_rows)
    )
    method = all(bool(row["method_passed"]) for row in full_rows)
    identity = all(
        bool(row["candidate_specific_identity_passed"]) for row in full_rows
    )
    spread = int(full_pool["c3_legal_spread_count"])
    supported_positive = int(full_pool["supported_positive_target_count"])
    exposure = int(full_pool["action_exposure"])
    changed_compatible = all(
        bool(row["changed_actions_compatible"]) for row in full_rows
    )
    joint_support = all(bool(row["joint_support_passed"]) for row in full_rows)
    pooled_service = int(full_pool["served_user_steps"]) >= int(
        drop_pool["served_user_steps"]
    )
    pooled_energy = float(full_pool["total_energy_j"]) <= float(
        drop_pool["total_energy_j"]
    )

    hard_stops: list[str] = []
    for passed, message in (
        (mechanics, f"{label} mechanics failed"),
        (method, f"{label} formula method failed"),
        (identity, f"{label} formula identity failed"),
        (spread > 0, f"{label} has zero legal-action C3 spread"),
        (
            supported_positive > 0,
            f"{label} has zero supported-positive targets",
        ),
        (exposure > 0, f"{label} has zero executed-action exposure"),
        (
            changed_compatible,
            f"{label} changed an action outside compatibility support",
        ),
        (
            joint_support,
            f"{label} joint action expanded current energy support",
        ),
        (pooled_delta > 0.0, f"{label} pooled EE is not strictly positive"),
        (
            every_world_positive,
            f"{label} is not EE-positive in every frozen world",
        ),
        (
            every_world_lineages,
            f"{label} has fewer than two positive lineages in a world",
        ),
        (pooled_service, f"{label} pooled service guard failed"),
        (every_world_service, f"{label} per-world service guard failed"),
        (
            every_world_service_lineages,
            f"{label} has fewer than two service-safe lineages in a world",
        ),
        (pooled_energy, f"{label} pooled trajectory energy increased"),
        (every_world_energy, f"{label} per-world trajectory energy increased"),
    ):
        if not passed:
            hard_stops.append(message)

    return {
        "label": label,
        "full_arm": full_arm,
        "drop_arm": drop_arm,
        "passed": not hard_stops,
        "pooled": {
            "delta_ee_bits_per_j": pooled_delta,
            "relative_delta_ee": pooled_delta / drop_ee,
            "delta_served_user_steps": int(full_pool["served_user_steps"])
            - int(drop_pool["served_user_steps"]),
            "delta_active_beam_steps": int(full_pool["active_beam_steps"])
            - int(drop_pool["active_beam_steps"]),
            "delta_active_satellite_steps": int(
                full_pool["active_satellite_steps"]
            )
            - int(drop_pool["active_satellite_steps"]),
            "delta_total_energy_j": float(full_pool["total_energy_j"])
            - float(drop_pool["total_energy_j"]),
        },
        "by_world": by_world,
        "mechanics_passed": mechanics,
        "method_passed": method,
        "candidate_specific_identity_passed": identity,
        "c3_legal_spread_count": spread,
        "supported_positive_target_count": supported_positive,
        "action_exposure": exposure,
        "changed_actions_compatible": changed_compatible,
        "joint_support_passed": joint_support,
        "pooled_service_noninferior": pooled_service,
        "pooled_total_trajectory_energy_nonincrease": pooled_energy,
        # Counts remain visible for diagnosis but are not acceptance gates.
        "pooled_active_beam_steps_not_above_diagnostic": int(
            full_pool["active_beam_steps"]
        )
        <= int(drop_pool["active_beam_steps"]),
        "pooled_active_satellite_steps_not_above_diagnostic": int(
            full_pool["active_satellite_steps"]
        )
        <= int(drop_pool["active_satellite_steps"]),
        "per_world_total_trajectory_energy_nonincrease": every_world_energy,
        "hard_stops": hard_stops,
    }


def ordered_decision(*, passed_zr: bool) -> str:
    """Apply the single-candidate V0.13 selection rule."""

    if passed_zr:
        return "GO_ZR_C3_LEARNABILITY_PREREG_ONLY"
    return "STOP_ZR_C3_ORACLE"


def _assert_current_authority(
    payload: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    """Reject mutually consistent shards that are stale against current files."""

    for field, value in expected.items():
        if payload.get(field) != value:
            raise V013OracleError(
                f"shard authority {field} does not match the current file state"
            )


def merge_shards(
    shard_files: Sequence[Path],
    output_dir: Path,
    *,
    tle_root: Path = screen.DEFAULT_TLE_ROOT,
    prereg_path: Path = screen.DEFAULT_PREREG,
    v03_root: Path = screen.DEFAULT_V03_ROOT,
    contract_path: Path = CONTRACT_PATH,
    authority_path: Path = FROZEN_AUTHORITY_PATH,
) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V013OracleError(f"refusing to overwrite {output}")
    assert_contract_frozen(contract_path)
    frozen_authority = validate_frozen_authority(
        Path(authority_path),
        contract_path=Path(contract_path),
        prereg_path=Path(prereg_path),
        v03_root=Path(v03_root),
    )
    expected_contract = contract_receipt()
    expected_runtime_hashes = frozen_authority["runtime_file_sha256"]
    record = read_prereg(prereg_path)
    ephemeris = record.sections.get("ephemeris", {})
    if not isinstance(ephemeris, Mapping) or not isinstance(
        ephemeris.get("file_set_sha256"), str
    ):
        raise V013OracleError("current prereg omits the TLE file-set digest")
    expected_source_authority = {
        "prereg_file_sha256": frozen_authority["base_prereg"]["file_sha256"],
        "prereg_record_digest": frozen_authority["base_prereg"]["record_digest"],
        "tle_file_set_sha256": frozen_authority["base_prereg"][
            "tle_file_set_sha256"
        ],
        **frozen_authority["python_source_authority"],
    }
    # Re-authenticate the current TLE source rather than trusting mutually
    # agreeing shard receipts from an older or foreign filesystem state.
    with tempfile.TemporaryDirectory(prefix="mcrl-v013-merge-tle-") as temporary:
        screen._frozen_archive(
            record, Path(tle_root), Path(temporary) / "frozen-tle"
        )
    payloads = [read_canonical_json(Path(path)) for path in shard_files]
    if any(not isinstance(payload, dict) for payload in payloads):
        raise V013OracleError("shard root is not an object")
    expected_count = len(WORLD_SEEDS) * len(ARMS) * len(LINEAGES)
    if len(payloads) != expected_count:
        raise V013OracleError(f"merge needs exactly {expected_count} shard files")
    expected_pairs = {
        (world, arm, lineage)
        for world in WORLD_SEEDS
        for arm in ARMS
        for lineage in LINEAGES
    }
    observed_pairs: set[tuple[int, str, int]] = set()
    first = payloads[0]
    expected_authority = {
        "contract": expected_contract,
        "contract_sha256": canonical_sha256(expected_contract),
        "contract_file_sha256": frozen_authority["contract_file_sha256"],
        "runner_file_sha256": frozen_authority["runner_file_sha256"],
        "runtime_file_sha256": expected_runtime_hashes,
        "wrapper_file_sha256": frozen_authority["wrapper_file_sha256"],
        "source_authority": expected_source_authority,
        "frozen_authority": frozen_authority,
        "frozen_authority_file_sha256": file_sha256(Path(authority_path)),
    }
    _assert_current_authority(first, expected_authority)
    validated_rows: list[dict[str, Any]] = []
    shard_keys = {
        "schema",
        "shard_id",
        "contract",
        "contract_sha256",
        "contract_file_sha256",
        "runner_file_sha256",
        "runtime_file_sha256",
        "wrapper_file_sha256",
        "source_authority",
        "frozen_authority",
        "frozen_authority_file_sha256",
        "row",
        "row_sha256",
    }
    for row_index, payload in enumerate(payloads):
        payload_map = _exact_keys(payload, shard_keys, field=f"shard[{row_index}]")
        _require_exact(payload_map.get("schema"), SHARD_SCHEMA, field="shard.schema")
        row = _validate_row_receipt(payload_map.get("row"), row_index=row_index)
        if canonical_sha256(row) != _sha256_text(
            payload_map.get("row_sha256"), field="shard.row_sha256"
        ):
            raise V013OracleError("shard row digest failed")
        if any(
            payload_map.get(field) != first.get(field)
            for field in (
                "contract",
                "contract_sha256",
                "contract_file_sha256",
                "runner_file_sha256",
                "runtime_file_sha256",
                "wrapper_file_sha256",
                "source_authority",
                "frozen_authority",
                "frozen_authority_file_sha256",
            )
        ):
            raise V013OracleError("shard authority hashes disagree")
        expected_shard_id = (
            f"{row['world_seed']}-{row['arm']}-{row['initialization_seed']}"
        )
        _require_exact(
            payload_map.get("shard_id"), expected_shard_id, field="shard.shard_id"
        )
        observed_pairs.add(
            (
                int(row["world_seed"]),
                str(row["arm"]),
                int(row["initialization_seed"]),
            )
        )
        validated_rows.append(row)
    if observed_pairs != expected_pairs:
        raise V013OracleError("shard world/arm/lineage coverage is not exact")

    rows = validated_rows
    for lineage in LINEAGES:
        current_q1, current_receipt = load_frozen_q1(v03_root, lineage)
        current_parameter_sha = _q1_parameter_sha256(current_q1)
        lineage_rows = [
            row for row in rows if int(row["initialization_seed"]) == lineage
        ]
        if not lineage_rows or any(
            str(row["q1_parameter_sha256_before"]) != current_parameter_sha
            or str(row["q1_parameter_sha256_after"]) != current_parameter_sha
            or row["q1_checkpoint"] != current_receipt
            for row in lineage_rows
        ):
            raise V013OracleError(
                f"lineage {lineage} Q1 receipt does not match the current checkpoint"
            )
    for world in WORLD_SEEDS:
        world_rows = [row for row in rows if int(row["world_seed"]) == world]
        if {str(row["field_root_digest"]) for row in world_rows} != {
            field_for_world(world).root_digest
        }:
            raise V013OracleError("world shards do not share their frozen field")
        if len({str(row["initial_world_sha256"]) for row in world_rows}) != 1:
            raise V013OracleError("world shards do not share one initial world")
    field_digests = [field_for_world(world).root_digest for world in WORLD_SEEDS]
    if len(set(field_digests)) != len(WORLD_SEEDS):
        raise V013OracleError("frozen worlds unexpectedly share one field")

    by_arm = {arm: [row for row in rows if str(row["arm"]) == arm] for arm in ARMS}
    pooled_by_arm = {arm: _pool(by_arm[arm]) for arm in ARMS}
    pooled_by_world_and_arm = {
        str(world): {
            arm: _pool(
                [
                    row
                    for row in rows
                    if int(row["world_seed"]) == world and str(row["arm"]) == arm
                ]
            )
            for arm in ARMS
        }
        for world in WORLD_SEEDS
    }
    gates = {
        "ZR": _pair_gate(
            label="ZR",
            full_arm="FULL_ZR",
            rows=rows,
            pooled_by_arm=pooled_by_arm,
            pooled_by_world_and_arm=pooled_by_world_and_arm,
        )
    }
    passed_zr = bool(gates["ZR"]["passed"])
    decision = ordered_decision(passed_zr=passed_zr)
    initial_worlds = {
        str(world): next(
            str(row["initial_world_sha256"])
            for row in rows
            if int(row["world_seed"]) == world
        )
        for world in WORLD_SEEDS
    }
    result = {
        "schema": RESULT_SCHEMA,
        "claim_ceiling": "FOUR_TRAIN_WORLD_ZR_ORACLE_NO_LEARNER_NO_TEST",
        "contract": first["contract"],
        "contract_sha256": first["contract_sha256"],
        "contract_file_sha256": first["contract_file_sha256"],
        "runner_file_sha256": first["runner_file_sha256"],
        "runtime_file_sha256": first["runtime_file_sha256"],
        "wrapper_file_sha256": first["wrapper_file_sha256"],
        "source_authority": first["source_authority"],
        "frozen_authority": first["frozen_authority"],
        "frozen_authority_file_sha256": first[
            "frozen_authority_file_sha256"
        ],
        "field_root_digest_by_world": {
            str(world): field_for_world(world).root_digest for world in WORLD_SEEDS
        },
        "initial_world_sha256": initial_worlds,
        "rows": sorted(
            rows,
            key=lambda row: (
                WORLD_SEEDS.index(int(row["world_seed"])),
                ARMS.index(str(row["arm"])),
                LINEAGES.index(int(row["initialization_seed"])),
            ),
        ),
        "summaries": {
            "pooled_by_arm": pooled_by_arm,
            "pooled_by_world_and_arm": pooled_by_world_and_arm,
            "candidate_gates": gates,
        },
        "gate": {
            "decision": decision,
            "pass_zr": passed_zr,
            "ordered_selection_zr_only": True,
        },
    }
    result["result_sha256"] = canonical_sha256(result)
    output.mkdir(parents=True, exist_ok=False)
    (output / "result.json").write_bytes(_canonical_bytes(result))
    print(
        f"decision={decision} "
        f"ZR={gates['ZR']['pooled']['relative_delta_ee']:+.6%}"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--json", action="store_true")
    freeze_authority = sub.add_parser("freeze-authority")
    freeze_authority.add_argument("--output", type=Path, required=True)
    freeze_authority.add_argument("--prereg", type=Path, default=screen.DEFAULT_PREREG)
    freeze_authority.add_argument("--v03-root", type=Path, default=screen.DEFAULT_V03_ROOT)
    freeze_authority.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    verify_authority = sub.add_parser("verify-authority")
    verify_authority.add_argument("--authority", type=Path, default=FROZEN_AUTHORITY_PATH)
    verify_authority.add_argument("--prereg", type=Path, default=screen.DEFAULT_PREREG)
    verify_authority.add_argument("--v03-root", type=Path, default=screen.DEFAULT_V03_ROOT)
    verify_authority.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    shard = sub.add_parser("shard")
    shard.add_argument("--world", type=int, choices=WORLD_SEEDS, required=True)
    shard.add_argument("--arm", choices=ARMS, required=True)
    shard.add_argument("--lineage", type=int, choices=LINEAGES, required=True)
    shard.add_argument("--output", type=Path, required=True)
    shard.add_argument("--tle-root", type=Path, default=screen.DEFAULT_TLE_ROOT)
    shard.add_argument("--prereg", type=Path, default=screen.DEFAULT_PREREG)
    shard.add_argument("--v03-root", type=Path, default=screen.DEFAULT_V03_ROOT)
    shard.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    shard.add_argument("--authority", type=Path, default=FROZEN_AUTHORITY_PATH)
    merge = sub.add_parser("merge")
    merge.add_argument("--shards", type=Path, nargs="+", required=True)
    merge.add_argument("--output", type=Path, required=True)
    merge.add_argument("--tle-root", type=Path, default=screen.DEFAULT_TLE_ROOT)
    merge.add_argument("--prereg", type=Path, default=screen.DEFAULT_PREREG)
    merge.add_argument("--v03-root", type=Path, default=screen.DEFAULT_V03_ROOT)
    merge.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    merge.add_argument("--authority", type=Path, default=FROZEN_AUTHORITY_PATH)
    args = parser.parse_args()
    if args.command == "plan":
        payload = contract_receipt()
        print(
            json.dumps(payload, indent=2, sort_keys=True)
            if args.json
            else canonical_sha256(payload)
        )
    elif args.command == "freeze-authority":
        payload = write_frozen_authority(
            args.output,
            contract_path=args.contract,
            prereg_path=args.prereg,
            v03_root=args.v03_root,
        )
        print(canonical_sha256(payload))
    elif args.command == "verify-authority":
        assert_contract_frozen(args.contract)
        payload = validate_frozen_authority(
            args.authority,
            contract_path=args.contract,
            prereg_path=args.prereg,
            v03_root=args.v03_root,
        )
        print(canonical_sha256(payload))
    elif args.command == "shard":
        run_shard(
            world_seed=args.world,
            arm=args.arm,
            lineage=args.lineage,
            output_dir=args.output,
            tle_root=args.tle_root,
            prereg_path=args.prereg,
            v03_root=args.v03_root,
            contract_path=args.contract,
            authority_path=args.authority,
        )
    else:
        merge_shards(
            args.shards,
            args.output,
            tle_root=args.tle_root,
            prereg_path=args.prereg,
            v03_root=args.v03_root,
            contract_path=args.contract,
            authority_path=args.authority,
        )


if __name__ == "__main__":
    main()
