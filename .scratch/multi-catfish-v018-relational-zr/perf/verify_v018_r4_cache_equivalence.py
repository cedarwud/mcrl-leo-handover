#!/usr/bin/env python3
"""Bounded, non-aborting V0.18 R4 cache-equivalence check.

R4 retains the sealed R1/R2 implementations and all R3 data surfaces.  It
changes only the comparison instrument: primitive branch checks keep their
R3 tolerances, while the public ``delta`` surface uses the preregistered
scale-aware C=64 floating-point bound.  Every legal branch is collected for
all three contexts even when a comparison fails, so a STOP receipt contains
diagnostics rather than an early first-failure traceback.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import hashlib
import importlib.util
import json
import math
import multiprocessing as mp
import numbers
from pathlib import Path
import re
import sys
import tempfile
import time
import traceback
from typing import Any
from unittest.mock import patch

import numpy as np


REPO = Path(__file__).resolve().parents[3]
RUNNER_PATH = REPO / ".scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py"
R1_PATH = REPO / ".scratch/multi-catfish-v018-relational-zr/r1-abort/ee_axis_relational_zr_c3-r1.py"
CONTRACT_PATH = REPO / ".scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-R4-SCALE-AWARE-CACHE-EQUIVALENCE-2026-09-04.md"
R1_SHA256 = "6a3d61940175f0e4e422fa4ac9818fd64652dd4f6e699408f6189cec164425a2"
R2_SHA256 = "e66f61d7ad8833115eb0542ca2b4ea6718a23ecc26aa0729f5cf879c64cf6166"
PREREG_SHA256 = "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
WORLD_SEED = 2026104901
LINEAGE = 2026092101
CONTEXTS = (12, 1, 2)
MAX_WORKERS = 18
RESULT_SCHEMA = "multi-catfish-mcrl-v018-r4-scale-aware-cache-equivalence-v1"
DELTA_C = 64
DIAGNOSTIC_C = (1, 8, 64, 512, 4096)
DELTA_HARD_CEILING_BITS = 1e-3
PRIMITIVE_RATE_RTOL = 1e-12
PRIMITIVE_RATE_ATOL = 1e-9
PRIMITIVE_INTERFERENCE_RTOL = 1e-12
PRIMITIVE_INTERFERENCE_ATOL = 1e-18
Q3_RTOL = 1e-12
Q3_ATOL = 1e-9

for path in (REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from mcrl.env.action_contract import NUM_ACTIONS  # noqa: E402


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = _load_module("v018_r2_equivalence_runner", RUNNER_PATH)
R1 = _load_module("mcrl.runtime.ee_axis_relational_zr_c3_r1_reference", R1_PATH)

import mcrl.runtime.ee_axis_relational_zr_c3 as R2  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_ops3_live import (  # noqa: E402
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402


_WORK: dict[str, Any] = {}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bytes_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _finite_float_or_none(value: object) -> float | None:
    """Return a JSON-safe float, treating undefined/non-finite as ``None``."""

    if value is None or isinstance(value, bool) or not isinstance(value, numbers.Real):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _finite_max(*values: object) -> float | None:
    finite: list[float] = []
    for value in values:
        number = _finite_float_or_none(value)
        if number is None:
            return None
        finite.append(number)
    return max(finite) if finite else None


def _json_safe(value: object) -> object:
    """Recursively replace non-finite numeric values before JSON encoding."""

    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, numbers.Integral) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        return _finite_float_or_none(value)
    return value


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        _json_safe(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _absolute_regular_file(path: Path, label: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute() or candidate.is_symlink() or not candidate.is_file():
        raise RuntimeError(f"{label} must be an existing absolute regular file")
    return candidate.resolve()


def _validate_code_manifest(
    *,
    code_manifest: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    """Authenticate the manifest file and every repository file it names."""

    if not isinstance(expected_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", expected_sha256
    ):
        raise RuntimeError("code-manifest digest must be lowercase SHA-256")
    manifest_path = _absolute_regular_file(code_manifest, "code manifest")
    actual_sha256 = file_sha256(manifest_path)
    if actual_sha256 != expected_sha256:
        raise RuntimeError("code-manifest digest mismatch")

    entries: list[tuple[str, str]] = []
    for line_number, raw in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not raw.strip():
            continue
        fields = raw.split("  ", 1)
        if len(fields) != 2 or not re.fullmatch(r"[0-9a-f]{64}", fields[0]):
            raise RuntimeError(f"malformed code-manifest line {line_number}")
        relative = fields[1]
        if not relative or Path(relative).is_absolute():
            raise RuntimeError(f"code-manifest path is not repository-relative: {relative}")
        resolved = (REPO / relative).resolve()
        if not resolved.is_relative_to(REPO.resolve()):
            raise RuntimeError(f"code-manifest path escapes repository: {relative}")
        _absolute_regular_file(resolved, f"code-manifest entry {relative}")
        if file_sha256(resolved) != fields[0]:
            raise RuntimeError(f"code-manifest entry digest mismatch: {relative}")
        entries.append((relative, fields[0]))
    if not entries:
        raise RuntimeError("code manifest is empty")
    return {
        "path": str(manifest_path),
        "sha256": actual_sha256,
        "entry_count": len(entries),
    }


def _validate_preflight_receipt(
    *,
    preflight_receipt: Path,
    preflight_log: Path,
    expected_manifest_sha256: str,
) -> dict[str, str]:
    """Authenticate the write-once server preflight receipt and its log."""

    receipt_path = _absolute_regular_file(preflight_receipt, "server preflight receipt")
    log_path = _absolute_regular_file(preflight_log, "server preflight log")
    lines = receipt_path.read_text(encoding="utf-8").splitlines()
    if len(lines) != 4:
        raise RuntimeError("server preflight receipt is malformed")
    if lines[0] != "schema=multi-catfish-mcrl-v018-r4-equivalence-preflight-v1":
        raise RuntimeError("server preflight receipt schema mismatch")
    if lines[1] != f"manifest_sha256={expected_manifest_sha256}":
        raise RuntimeError("server preflight receipt manifest mismatch")
    if lines[2] != "pytest_exit=0":
        raise RuntimeError("server preflight receipt does not attest pytest success")
    log_match = re.fullmatch(r"log_sha256=([0-9a-f]{64})", lines[3])
    if log_match is None:
        raise RuntimeError("server preflight receipt log digest is malformed")
    log_sha256 = file_sha256(log_path)
    if log_sha256 != log_match.group(1):
        raise RuntimeError("server preflight log digest mismatch")
    return {
        "path": str(receipt_path),
        "sha256": file_sha256(receipt_path),
        "log_path": str(log_path),
        "log_sha256": log_sha256,
    }


def _authenticate_external_closure(
    *,
    code_manifest: Path,
    code_manifest_sha256: str,
    preflight_receipt: Path,
    preflight_log: Path,
) -> dict[str, Any]:
    manifest = _validate_code_manifest(
        code_manifest=code_manifest,
        expected_sha256=code_manifest_sha256,
    )
    preflight = _validate_preflight_receipt(
        preflight_receipt=preflight_receipt,
        preflight_log=preflight_log,
        expected_manifest_sha256=code_manifest_sha256,
    )
    return {
        "code_manifest_path": manifest["path"],
        "code_manifest_sha256": manifest["sha256"],
        "code_manifest_entry_count": manifest["entry_count"],
        "preflight_receipt_path": preflight["path"],
        "preflight_receipt_sha256": preflight["sha256"],
        "preflight_log_path": preflight["log_path"],
        "preflight_log_sha256": preflight["log_sha256"],
    }


def _safe_file_sha256(path: Path) -> str | None:
    """Return a digest only for an existing non-symlink regular file."""

    candidate = Path(path)
    try:
        if candidate.is_symlink() or not candidate.is_file():
            return None
        return file_sha256(candidate)
    except OSError:
        return None


def validate_contract() -> str:
    if not CONTRACT_PATH.is_file() or CONTRACT_PATH.is_symlink():
        raise RuntimeError("equivalence contract is missing or symlinked")
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    if "Status: `FROZEN_BEFORE_CHECK`" not in text:
        raise RuntimeError("equivalence contract is not frozen before check")
    if file_sha256(R1_PATH) != R1_SHA256:
        raise RuntimeError("sealed R1 reference hash mismatch")
    if file_sha256(Path(R2.__file__).resolve()) != R2_SHA256:
        raise RuntimeError("R2 cached runtime hash mismatch")
    if file_sha256(RUNNER.DEFAULT_PREREG) != PREREG_SHA256:
        raise RuntimeError("frozen base preregistration hash mismatch")
    return file_sha256(CONTRACT_PATH)


def _old_user_branches(uid: int) -> list[tuple[tuple[int, ...], np.ndarray, np.ndarray]]:
    refs = _WORK["refs"]
    opening = _WORK["opening"]
    legal = _WORK["legal"]
    results: list[tuple[tuple[int, ...], np.ndarray, np.ndarray]] = []
    for action_raw in np.flatnonzero(legal[uid]).tolist():
        action = int(action_raw)
        branch = R1._branch_actions(refs, focal_user=uid, focal_action=action)
        served = R1._branch_served(branch, opening, legal)
        rates, interference = R1._nominal_rates(
            environment=_WORK["environment"],
            actions=branch,
            served=served,
            required_power=_WORK["power"],
            signal_surface=_WORK["signal"],
            norads=_WORK["norads"],
            cells=_WORK["cells"],
            legal=legal,
            colours=_WORK["colours"],
            centres=_WORK["centres"],
            positions=_WORK["positions"],
            users_ecef=_WORK["users_ecef"],
        )
        results.append(
            (
                tuple(int(value) for value in branch.tolist()),
                np.asarray(rates, dtype=np.float64),
                np.asarray(interference, dtype=np.float64),
            )
        )
    return results


def _masked_argmax(scores: np.ndarray, masks: np.ndarray) -> np.ndarray:
    return np.argmax(np.where(masks, scores, -np.inf), axis=1).astype(np.int64)


def _minimum_top_two_margin(scores: np.ndarray, masks: np.ndarray) -> float | None:
    margins: list[float] = []
    for row, mask in zip(scores, masks, strict=True):
        legal = np.asarray(row)[np.asarray(mask)]
        if legal.size < 2:
            continue
        ordered = np.partition(legal, -2)
        margins.append(float(ordered[-1] - ordered[-2]))
    if not margins:
        return None
    minimum = min(margins)
    return _finite_float_or_none(minimum)


def _comparison_report(
    *,
    left: object,
    right: object,
    eligible: object | None = None,
    rtol: float = 0.0,
    atol: float = 0.0,
    bound: object | None = None,
    exact: bool = False,
    prefix: tuple[int, ...] = (),
    worst_limit: int = 5,
) -> dict[str, Any]:
    """Compare arrays without raising and retain actionable worst indices.

    This is intentionally independent of ``numpy.testing``.  The R4 runner
    must finish all contexts after a surface mismatch so that a STOP receipt
    distinguishes a single reassociation from a structural defect.
    """

    lhs = np.asarray(left)
    rhs = np.asarray(right)
    if lhs.shape != rhs.shape:
        return {
            "shape_left": list(lhs.shape),
            "shape_right": list(rhs.shape),
            "eligible_count": 0,
            "violation_count": 1,
            "max_abs_deviation": None,
            "max_normalized_deviation": None,
            "worst": [{"index": list(prefix), "reason": "shape_mismatch"}],
            "pass": False,
        }
    if eligible is None:
        mask = np.ones(lhs.shape, dtype=np.bool_)
    else:
        mask = np.asarray(eligible, dtype=np.bool_)
        if mask.shape != lhs.shape:
            return {
                "shape_left": list(lhs.shape),
                "shape_right": list(rhs.shape),
                "eligible_count": 0,
                "violation_count": 1,
                "max_abs_deviation": None,
                "max_normalized_deviation": None,
                "worst": [{"index": list(prefix), "reason": "eligibility_shape_mismatch"}],
                "pass": False,
            }

    numeric = np.issubdtype(lhs.dtype, np.number) and np.issubdtype(rhs.dtype, np.number)
    if numeric:
        with np.errstate(over="ignore", invalid="ignore"):
            diff = np.abs(lhs.astype(np.float64) - rhs.astype(np.float64))
        if bound is not None:
            threshold = np.asarray(bound, dtype=np.float64)
            if threshold.shape != lhs.shape:
                return {
                    "shape_left": list(lhs.shape),
                    "shape_right": list(rhs.shape),
                    "eligible_count": int(np.count_nonzero(mask)),
                    "violation_count": 1,
                    "max_abs_deviation": None,
                    "max_normalized_deviation": None,
                    "worst": [{"index": list(prefix), "reason": "bound_shape_mismatch"}],
                    "pass": False,
                }
        else:
            with np.errstate(over="ignore", invalid="ignore"):
                threshold = float(atol) + float(rtol) * np.abs(rhs.astype(np.float64))
        finite = np.isfinite(lhs) & np.isfinite(rhs) & np.isfinite(threshold)
        if exact:
            ok = finite & (lhs == rhs)
        else:
            ok = finite & (diff <= threshold)
        with np.errstate(divide="ignore", invalid="ignore"):
            normalized = np.divide(
                diff,
                threshold,
                out=np.full(lhs.shape, np.inf, dtype=np.float64),
                where=threshold > 0.0,
            )
        normalized = np.where(diff == 0.0, 0.0, normalized)
        max_abs = float(np.max(diff[mask])) if np.any(mask) else 0.0
        max_norm = float(np.max(normalized[mask])) if np.any(mask) else 0.0
        scale = float(np.max(np.maximum(np.abs(lhs[mask]), np.abs(rhs[mask])))) if np.any(mask) else 0.0
    else:
        equal = lhs == rhs
        ok = equal
        diff = np.where(equal, 0.0, 1.0).astype(np.float64)
        threshold = np.ones(lhs.shape, dtype=np.float64)
        normalized = diff
        max_abs = float(np.max(diff[mask])) if np.any(mask) else 0.0
        max_norm = float(np.max(normalized[mask])) if np.any(mask) else 0.0
        scale = max_abs

    violations = mask & ~ok
    indices = np.argwhere(violations)
    worst: list[dict[str, Any]] = []
    if indices.size:
        scores = normalized[violations]
        order = np.argsort(scores, kind="stable")[::-1][:worst_limit]
        for position in order.tolist():
            index = tuple(int(value) for value in indices[position].tolist())
            flat_index = tuple(prefix) + index
            worst.append(
                {
                    "index": list(flat_index),
                    "left": float(lhs[index]) if numeric else str(lhs[index]),
                    "right": float(rhs[index]) if numeric else str(rhs[index]),
                    "absolute_deviation": float(diff[index]),
                    "normalized_deviation": float(normalized[index]),
                    "threshold": float(threshold[index]),
                }
            )
    max_abs_value: float | None = (
        float(max_abs) if math.isfinite(float(max_abs)) else None
    )
    max_norm_value: float | None = (
        float(max_norm) if math.isfinite(float(max_norm)) else None
    )
    scale_value: float | None = (
        float(scale) if math.isfinite(float(scale)) else None
    )
    for item in worst:
        for field in ("left", "right", "absolute_deviation", "normalized_deviation", "threshold"):
            value = item.get(field)
            if isinstance(value, (int, float)) and not math.isfinite(float(value)):
                item[field] = None
    return {
        "shape_left": list(lhs.shape),
        "shape_right": list(rhs.shape),
        "eligible_count": int(np.count_nonzero(mask)),
        "violation_count": int(np.count_nonzero(violations)),
        "max_abs_deviation": max_abs_value,
        "max_normalized_deviation": max_norm_value,
        "scale": scale_value,
        "worst": worst,
        "pass": not bool(np.any(violations)),
    }


def _empty_aggregate() -> dict[str, Any]:
    return {
        "eligible_count": 0,
        "violation_count": 0,
        "max_abs_deviation": 0.0,
        "max_normalized_deviation": 0.0,
        "max_scale": 0.0,
        "worst": [],
        "pass": True,
    }


def _merge_aggregate(
    aggregate: dict[str, Any],
    report: Mapping[str, Any],
    *,
    worst_limit: int = 8,
) -> None:
    """Merge one non-raising comparison report into a context summary."""

    aggregate["eligible_count"] += int(report.get("eligible_count", 0))
    aggregate["violation_count"] += int(report.get("violation_count", 0))
    max_abs = report.get("max_abs_deviation")
    if isinstance(max_abs, (int, float)) and math.isfinite(float(max_abs)):
        aggregate["max_abs_deviation"] = max(
            float(aggregate["max_abs_deviation"]), float(max_abs)
        )
    max_norm = report.get("max_normalized_deviation")
    if isinstance(max_norm, (int, float)):
        if math.isfinite(float(max_norm)):
            aggregate["max_normalized_deviation"] = max(
                float(aggregate["max_normalized_deviation"]), float(max_norm)
            )
    scale = report.get("scale")
    if isinstance(scale, (int, float)) and math.isfinite(float(scale)):
        aggregate["max_scale"] = max(float(aggregate["max_scale"]), float(scale))
    aggregate["worst"].extend(report.get("worst", []))
    aggregate["worst"].sort(
        key=lambda item: (
            float(item.get("normalized_deviation", 0.0))
            if isinstance(item.get("normalized_deviation"), (int, float))
            else 0.0
        ),
        reverse=True,
    )
    del aggregate["worst"][worst_limit:]
    aggregate["pass"] = bool(aggregate["pass"] and report.get("pass", False))


def _branch_maps(
    *,
    actions: np.ndarray,
    served: np.ndarray,
    power: np.ndarray,
    norads: np.ndarray,
    cells: np.ndarray,
    legal: np.ndarray,
) -> tuple[dict[tuple[int, int], int], dict[tuple[int, int], float]]:
    """Reconstruct integer beam loads and max required powers from a branch."""

    keys = R1._branch_keys(actions, norads, cells, legal)
    loads: dict[tuple[int, int], int] = {}
    powers: dict[tuple[int, int], float] = {}
    for uid, key in enumerate(keys):
        if not bool(served[uid]) or key is None:
            continue
        action = int(actions[uid])
        loads[key] = loads.get(key, 0) + 1
        powers[key] = max(powers.get(key, 0.0), float(power[uid, action]))
    return loads, powers


def _cached_branch_maps(
    cache: Any,
    *,
    focal_user: int,
    focal_action: int,
    opening: np.ndarray,
    power: np.ndarray,
    norads: np.ndarray,
    cells: np.ndarray,
) -> tuple[dict[tuple[int, int], int], dict[tuple[int, int], float]]:
    """Reconstruct a candidate branch from the cache's detached peer maps."""

    focal = int(focal_user)
    action = int(focal_action)
    origin_key = (
        cache.reference_keys[focal]
        if bool(cache.reference_served[focal])
        else None
    )
    candidate_served = bool(opening[focal, action])
    candidate_key = (
        (int(norads[focal, action]), int(cells[focal, action]))
        if candidate_served
        else None
    )
    loads: dict[tuple[int, int], int] = {}
    powers: dict[tuple[int, int], float] = {
        key: float(value) for key, value in cache.peer_power_by_focal[focal].items()
    }
    for key, reference_load in cache.reference_load_by_key.items():
        load = int(reference_load)
        if origin_key == key:
            load -= 1
        if load > 0:
            loads[key] = load
    if candidate_key is not None:
        loads[candidate_key] = loads.get(candidate_key, 0) + 1
        powers[candidate_key] = max(
            powers.get(candidate_key, 0.0), float(power[focal, action])
        )
    powers = {key: value for key, value in powers.items() if key in loads}
    return loads, powers


def _changed_keys(
    *,
    focal_user: int,
    focal_action: int,
    refs: np.ndarray,
    opening: np.ndarray,
    norads: np.ndarray,
    cells: np.ndarray,
    legal: np.ndarray,
) -> set[tuple[int, int]]:
    focal = int(focal_user)
    result: set[tuple[int, int]] = set()
    reference = int(refs[focal])
    if reference >= 0 and bool(opening[focal, reference]):
        result.add((int(norads[focal, reference]), int(cells[focal, reference])))
    action = int(focal_action)
    if bool(opening[focal, action]) and bool(legal[focal, action]):
        result.add((int(norads[focal, action]), int(cells[focal, action])))
    return result


def _expected_victim_mask(
    *,
    refs: np.ndarray,
    opening: np.ndarray,
    norads: np.ndarray,
    cells: np.ndarray,
    legal: np.ndarray,
    colours: np.ndarray,
) -> np.ndarray:
    """Independent implementation of the physical victim predicate."""

    users = refs.size
    keys = R1._physical_keys(norads, cells, legal)
    ref_keys: list[tuple[int, int] | None] = [None] * users
    ref_open = np.zeros(users, dtype=np.bool_)
    for uid, raw in enumerate(refs.tolist()):
        action = int(raw)
        if action >= 0 and bool(opening[uid, action]):
            ref_keys[uid] = keys[uid][action]
            ref_open[uid] = True
    result = np.zeros((users, NUM_ACTIONS, users), dtype=np.bool_)
    for uid in range(users):
        for action_raw in np.flatnonzero(legal[uid]).tolist():
            action = int(action_raw)
            changed = _changed_keys(
                focal_user=uid,
                focal_action=action,
                refs=refs,
                opening=opening,
                norads=norads,
                cells=cells,
                legal=legal,
            )
            if not changed:
                continue
            for victim in range(users):
                if victim == uid or not bool(ref_open[victim]):
                    continue
                victim_key = ref_keys[victim]
                if victim_key is None:
                    continue
                for changed_key in changed:
                    same_beam = victim_key == changed_key
                    same_colour = int(colours[victim_key[1]]) == int(colours[changed_key[1]])
                    cochannel = same_colour and (
                        (victim_key[0] == changed_key[0] and victim_key[1] != changed_key[1])
                        or victim_key[0] != changed_key[0]
                    )
                    if same_beam or cochannel:
                        result[uid, action, victim] = True
                        break
    result[np.arange(users), :, np.arange(users)] = False
    result &= legal[:, :, None]
    return result


def _context_result(
    *,
    environment: Any,
    observation: Any,
    references: np.ndarray,
    background: np.ndarray,
    required: np.ndarray,
    opening: np.ndarray,
    workers: int,
) -> dict[str, Any]:
    tables, legal = R1._anchor(environment, observation)
    refs, power, opening_values, identity = R1._validate_context_inputs(
        tables, legal, references, required, opening
    )
    norads = identity[:, :, 0]
    cells = identity[:, :, 1]
    centres, colours, positions = R1._grid_data(
        environment, observation, norads, cells
    )
    users = len(tables)
    users_ecef = R1._user_positions(environment, users)
    theta, slant, elevation = R1._candidate_geometry(
        environment,
        observation,
        norads,
        cells,
        centres,
        positions,
        users_ecef,
    )
    signal = R1._nominal_signal_surface(
        theta=theta,
        slant=slant,
        elevation=elevation,
        required_power=power,
        legal=legal,
    )
    reference_branch = R1._branch_actions(refs)
    reference_served = R1._branch_served(reference_branch, opening_values, legal)
    reference_rates, reference_interference = R1._nominal_rates(
        environment=environment,
        actions=reference_branch,
        served=reference_served,
        required_power=power,
        signal_surface=signal,
        norads=norads,
        cells=cells,
        legal=legal,
        colours=colours,
        centres=centres,
        positions=positions,
        users_ecef=users_ecef,
    )

    interval_s = float(environment.driver.config.ephemeris.time_step_s)
    r2_delta, r2_q3 = R2.nominal_relational_zr_surface(
        environment,
        observation,
        reference_actions=refs,
        required_power_surface=power,
        opening_feasibility_surface=opening_values,
        interval_s=interval_s,
        kappa_bits=RUNNER.OPS3_KAPPA_BITS,
        pmax_w=RUNNER.BEAM_POWER_MAX_W,
    )
    r2_state = R2.encode_relational_zr_c3_state(
        environment,
        observation,
        reference_actions=refs,
        required_power_surface=power,
        opening_feasibility_surface=opening_values,
        pmax_w=RUNNER.BEAM_POWER_MAX_W,
    )

    global _WORK
    _WORK = {
        "environment": environment,
        "refs": refs,
        "opening": opening_values,
        "power": power,
        "signal": signal,
        "norads": norads,
        "cells": cells,
        "legal": legal,
        "colours": colours,
        "centres": centres,
        "positions": positions,
        "users_ecef": users_ecef,
    }
    started = time.perf_counter()
    reference_key = tuple(int(value) for value in reference_branch.tolist())
    branch_results: dict[tuple[int, ...], tuple[np.ndarray, np.ndarray]] = {
        reference_key: (
            np.asarray(reference_rates, dtype=np.float64),
            np.asarray(reference_interference, dtype=np.float64),
        )
    }
    context = mp.get_context("fork")
    duplicate_branch_arrays = 0
    inconsistent_duplicate_branch_arrays = 0
    with context.Pool(processes=workers) as pool:
        for rows in pool.imap_unordered(
            _old_user_branches, range(users), chunksize=1
        ):
            for key, rates, interference in rows:
                previous = branch_results.get(key)
                if previous is None:
                    branch_results[key] = (rates, interference)
                else:
                    duplicate_branch_arrays += 1
                    if not (
                        np.array_equal(previous[0], rates)
                        and np.array_equal(previous[1], interference)
                    ):
                        inconsistent_duplicate_branch_arrays += 1
    reference_elapsed_s = time.perf_counter() - started

    # Build the optimized reference cache only after the retained R1 branch
    # table is complete.  All comparisons below are non-raising and continue
    # through every legal branch and all three contexts.
    r2_cache = R2._build_nominal_reference_cache(
        environment=environment,
        refs=refs,
        opening=opening_values,
        power=power,
        signal=signal,
        norads=norads,
        cells=cells,
        legal=legal,
        colours=colours,
        centres=centres,
        positions=positions,
        users_ecef=users_ecef,
    )

    primitive_rate = _empty_aggregate()
    primitive_interference = _empty_aggregate()
    reference_rate_report = _comparison_report(
        left=reference_rates,
        right=r2_cache.reference_rates,
        rtol=PRIMITIVE_RATE_RTOL,
        atol=PRIMITIVE_RATE_ATOL,
    )
    reference_interference_report = _comparison_report(
        left=reference_interference,
        right=r2_cache.reference_interference,
        rtol=PRIMITIVE_INTERFERENCE_RTOL,
        atol=PRIMITIVE_INTERFERENCE_ATOL,
    )
    _merge_aggregate(primitive_rate, reference_rate_report)
    _merge_aggregate(primitive_interference, reference_interference_report)

    candidate_r1_interferences = np.zeros((users, NUM_ACTIONS, users), dtype=np.float64)
    candidate_interferences = np.zeros((users, NUM_ACTIONS, users), dtype=np.float64)
    candidate_rate_deviations = np.zeros((users, NUM_ACTIONS, users), dtype=np.float64)
    candidate_interference_deviations = np.zeros((users, NUM_ACTIONS, users), dtype=np.float64)
    branch_load_values = np.zeros((users, NUM_ACTIONS, users), dtype=np.float64)
    branch_maps_violations = 0
    branch_maps_worst: list[dict[str, Any]] = []
    focal_rate_violations = 0
    checked_nonfocal_values = 0
    clamp_count = 0
    clamp_invariant_violations = 0
    clamp_worst: list[dict[str, Any]] = []
    branch_occurrences: dict[tuple[int, ...], list[tuple[int, int]]] = {}
    for uid in range(users):
        nonfocal = np.arange(users) != uid
        for action_raw in np.flatnonzero(legal[uid]).tolist():
            action = int(action_raw)
            branch = R1._branch_actions(refs, focal_user=uid, focal_action=action)
            key = tuple(int(value) for value in branch.tolist())
            branch_occurrences.setdefault(key, []).append((uid, action))
            r1_rates, r1_interference = branch_results[key]
            cached_rates, cached_interference = R2._cached_nominal_nonfocal_branch(
                r2_cache,
                focal_user=uid,
                focal_action=action,
                opening=opening_values,
                power=power,
                norads=norads,
                cells=cells,
            )
            rate_report = _comparison_report(
                left=r1_rates,
                right=cached_rates,
                eligible=nonfocal,
                rtol=PRIMITIVE_RATE_RTOL,
                atol=PRIMITIVE_RATE_ATOL,
                prefix=(uid, action),
            )
            interference_report = _comparison_report(
                left=r1_interference,
                right=cached_interference,
                eligible=nonfocal,
                rtol=PRIMITIVE_INTERFERENCE_RTOL,
                atol=PRIMITIVE_INTERFERENCE_ATOL,
                prefix=(uid, action),
            )
            _merge_aggregate(primitive_rate, rate_report)
            _merge_aggregate(primitive_interference, interference_report)
            candidate_r1_interferences[uid, action] = r1_interference
            candidate_interferences[uid, action] = cached_interference
            candidate_rate_deviations[uid, action] = np.abs(r1_rates - cached_rates)
            candidate_interference_deviations[uid, action] = np.abs(
                r1_interference - cached_interference
            )
            checked_nonfocal_values += int(np.count_nonzero(nonfocal))
            focal_rate_violations += int(cached_rates[uid] != 0.0)

            r1_served = R1._branch_served(branch, opening_values, legal)
            r1_loads, r1_powers = _branch_maps(
                actions=branch,
                served=r1_served,
                power=power,
                norads=norads,
                cells=cells,
                legal=legal,
            )
            r2_loads, r2_powers = _cached_branch_maps(
                r2_cache,
                focal_user=uid,
                focal_action=action,
                opening=opening_values,
                power=power,
                norads=norads,
                cells=cells,
            )
            if r1_loads != r2_loads or r1_powers != r2_powers:
                branch_maps_violations += 1
                if len(branch_maps_worst) < 8:
                    branch_maps_worst.append(
                        {
                            "focal_user": uid,
                            "action": action,
                            "branch": list(key),
                            "r1_loads": {str(k): v for k, v in sorted(r1_loads.items())},
                            "r2_loads": {str(k): v for k, v in sorted(r2_loads.items())},
                            "r1_powers": {str(k): v for k, v in sorted(r1_powers.items())},
                            "r2_powers": {str(k): v for k, v in sorted(r2_powers.items())},
                        }
                    )
            for victim, victim_key in enumerate(
                R1._branch_keys(branch, norads, cells, legal)
            ):
                if victim_key is not None and bool(r1_served[victim]):
                    branch_load_values[uid, action, victim] = float(
                        r1_loads.get(victim_key, 0)
                    )

            # Recompute the cache's pre-clamp residual for the explicit clamp
            # invariant.  This mirrors the sealed helper but does not alter it.
            origin_key = (
                r2_cache.reference_keys[uid]
                if bool(r2_cache.reference_served[uid])
                else None
            )
            candidate_key = (
                (int(norads[uid, action]), int(cells[uid, action]))
                if bool(opening_values[uid, action])
                else None
            )
            raw_cached = np.array(r2_cache.reference_interference, copy=True)
            changed_keys = {key_item for key_item in (origin_key, candidate_key) if key_item is not None}
            peers = r2_cache.peer_power_by_focal[uid]
            for changed_key in changed_keys:
                old_power = float(r2_cache.reference_power_by_key.get(changed_key, 0.0))
                new_power = float(peers.get(changed_key, 0.0))
                if candidate_key == changed_key:
                    new_power = max(new_power, float(power[uid, action]))
                raw_cached += (new_power - old_power) * r2_cache.coupling_by_key[changed_key]
            clamp_tolerance = 64.0 * np.finfo(np.float64).eps * max(
                1.0, float(np.max(r2_cache.reference_interference, initial=0.0))
            )
            negative = raw_cached < 0.0
            active_clamp = negative & (cached_interference == 0.0)
            clamp_count += int(np.count_nonzero(active_clamp))
            bad_residual = active_clamp & (raw_cached < -clamp_tolerance)
            bad_physical_zero = active_clamp & (r1_interference != 0.0)
            clamp_invariant_violations += int(
                np.count_nonzero(bad_residual | bad_physical_zero)
            )
            if np.any(bad_residual | bad_physical_zero) and len(clamp_worst) < 8:
                for victim in np.flatnonzero(bad_residual | bad_physical_zero)[: 8 - len(clamp_worst)]:
                    clamp_worst.append(
                        {
                            "focal_user": uid,
                            "action": action,
                            "victim": int(victim),
                            "raw_residual": float(raw_cached[victim]),
                            "tolerance": float(clamp_tolerance),
                            "r1_interference": float(r1_interference[victim]),
                        }
                    )

    duplicate_branch_vectors = {
        "count": int(sum(max(0, len(values) - 1) for values in branch_occurrences.values())),
        "inconsistent_array_count": int(inconsistent_duplicate_branch_arrays),
        "worst": [],
    }
    for key, occurrences in sorted(branch_occurrences.items()):
        if len(occurrences) > 1 and len(duplicate_branch_vectors["worst"]) < 8:
            duplicate_branch_vectors["worst"].append(
                {"branch": list(key), "occurrences": [list(item) for item in occurrences]}
            )

    def rate_dispatch(*args: object, **kwargs: object) -> tuple[np.ndarray, np.ndarray]:
        actions = kwargs.get("actions", args[1] if len(args) > 1 else None)
        key = tuple(int(value) for value in np.asarray(actions).tolist())
        rates, interference = branch_results[key]
        return np.array(rates, copy=True), np.array(interference, copy=True)

    def interference_dispatch(*args: object, **kwargs: object) -> np.ndarray:
        actions = kwargs.get("actions", args[0] if args else None)
        key = tuple(int(value) for value in np.asarray(actions).tolist())
        return np.array(branch_results[key][1], copy=True)

    with patch.object(R1, "_nominal_rates", rate_dispatch):
        r1_delta, r1_q3 = R1.nominal_relational_zr_surface(
            environment,
            observation,
            reference_actions=refs,
            required_power_surface=power,
            opening_feasibility_surface=opening_values,
            interval_s=interval_s,
            kappa_bits=RUNNER.OPS3_KAPPA_BITS,
            pmax_w=RUNNER.BEAM_POWER_MAX_W,
        )
    with patch.object(R1, "_nominal_interference", interference_dispatch):
        r1_state = R1.encode_relational_zr_c3_state(
            environment,
            observation,
            reference_actions=refs,
            required_power_surface=power,
            opening_feasibility_surface=opening_values,
            pmax_w=RUNNER.BEAM_POWER_MAX_W,
        )

    expected_victims = _expected_victim_mask(
        refs=refs,
        opening=opening_values,
        norads=norads,
        cells=cells,
        legal=legal,
        colours=colours,
    )
    victim_predicate_report = _comparison_report(
        left=r1_state.victim_mask,
        right=expected_victims,
        exact=True,
    )
    victim_mask_cross_report = _comparison_report(
        left=r1_state.victim_mask,
        right=r2_state.victim_mask,
        exact=True,
    )

    focal_axis = np.arange(users, dtype=np.int64)[:, None, None]
    victim_axis = np.arange(users, dtype=np.int64)[None, None, :]
    delta_eligible = legal[:, :, None] & (focal_axis != victim_axis)
    delta_structural = ~delta_eligible
    delta_base_bound = np.zeros_like(np.asarray(r1_delta, dtype=np.float64))
    eps = np.finfo(np.float64).eps
    bandwidth = float(R1._bandwidth_from(environment))
    noise = float(R1._noise_from(environment))
    for uid in range(users):
        for action in np.flatnonzero(legal[uid]).tolist():
            action = int(action)
            r1_rates, r1_interference = branch_results[
                tuple(int(value) for value in R1._branch_actions(refs, focal_user=uid, focal_action=action).tolist())
            ]
            loads = branch_load_values[uid, action]
            for victim in range(users):
                load = max(float(loads[victim]), 1.0)
                r0 = float(reference_rates[victim])
                ra = float(r1_rates[victim])
                i0 = float(reference_interference[victim])
                ia = float(r1_interference[victim])
                delta_base_bound[uid, action, victim] = eps * interval_s * (
                    (bandwidth / load) / math.log(2.0)
                    * (1.0 + (abs(i0) + abs(ia)) / (noise + abs(ia)))
                    + max(abs(r0), abs(ra), 1.0)
                )
    delta_bound = DELTA_C * delta_base_bound
    delta_bound_report = _comparison_report(
        left=r1_delta,
        right=r2_delta,
        eligible=delta_eligible,
        bound=delta_bound,
    )
    delta_hard_report = _comparison_report(
        left=r1_delta,
        right=r2_delta,
        eligible=delta_eligible,
        bound=np.full_like(delta_bound, DELTA_HARD_CEILING_BITS),
    )
    delta_structural_report = _comparison_report(
        left=r1_delta,
        right=r2_delta,
        eligible=delta_structural,
        exact=True,
    )
    delta_structural_zero_report = _comparison_report(
        left=r1_delta,
        right=np.zeros_like(r1_delta),
        eligible=delta_structural,
        exact=True,
    )

    # Reconstruct the scale-aware victim-token bound from the same sealed R1
    # primitive values used above.  Columns 0--4 remain exact.
    token_base_bound = np.zeros_like(np.asarray(r1_state.victim_tokens[..., 5]), dtype=np.float64)
    for uid in range(users):
        for action in np.flatnonzero(legal[uid]).tolist():
            action = int(action)
            _r1_rates, r1_interference = branch_results[
                tuple(int(value) for value in R1._branch_actions(refs, focal_user=uid, focal_action=action).tolist())
            ]
            for victim in range(users):
                i0 = float(reference_interference[victim])
                ia = float(r1_interference[victim])
                token_left = float(r1_state.victim_tokens[uid, action, victim, 5])
                token_right = float(r2_state.victim_tokens[uid, action, victim, 5])
                token_base_bound[uid, action, victim] = eps * (
                    (abs(i0) + abs(ia)) / noise
                    + max(abs(token_left), abs(token_right), 1.0)
                )
    token_bound = DELTA_C * token_base_bound
    token_mask = np.asarray(r1_state.victim_mask, dtype=np.bool_)
    token5_report = _comparison_report(
        left=r1_state.victim_tokens[..., 5],
        right=r2_state.victim_tokens[..., 5],
        eligible=token_mask,
        bound=token_bound,
    )
    token5_masked_report = _comparison_report(
        left=r1_state.victim_tokens[..., 5],
        right=r2_state.victim_tokens[..., 5],
        eligible=~token_mask,
        exact=True,
    )
    token04_report = _comparison_report(
        left=r1_state.victim_tokens[..., :5],
        right=r2_state.victim_tokens[..., :5],
        exact=True,
    )
    action_context_report = _comparison_report(
        left=r1_state.action_context,
        right=r2_state.action_context,
        exact=True,
    )

    exact_reports = {
        "action_mask": _comparison_report(
            left=r1_state.action_mask, right=r2_state.action_mask, exact=True
        ),
        "victim_mask": victim_mask_cross_report,
        "positive_credit_compatible": _comparison_report(
            left=r1_state.positive_credit_compatible,
            right=r2_state.positive_credit_compatible,
            exact=True,
        ),
        "reference_actions": _comparison_report(
            left=r1_state.reference_actions,
            right=r2_state.reference_actions,
            exact=True,
        ),
    }
    with np.errstate(over="ignore", invalid="ignore"):
        r1_score = np.asarray(background, dtype=np.float64) + np.asarray(r1_q3)
        r2_score = np.asarray(background, dtype=np.float64) + np.asarray(r2_q3)
    legal_score_mask = np.asarray(legal, dtype=np.bool_)
    score_finite_mask = np.isfinite(r1_score) & np.isfinite(r2_score)
    nonfinite_score_count = int(np.count_nonzero(legal_score_mask & ~score_finite_mask))
    scores_finite = nonfinite_score_count == 0
    if scores_finite:
        r1_actions = _masked_argmax(r1_score, legal_score_mask)
        r2_actions = _masked_argmax(r2_score, legal_score_mask)
        selected_actions_equal = bool(np.array_equal(r1_actions, r2_actions))
        with np.errstate(over="ignore", invalid="ignore"):
            score_deviation = np.abs(r1_score - r2_score)
        maximum_score_deviation = _finite_float_or_none(
            np.max(score_deviation[legal_score_mask])
        )
        minimum_margin_json = _minimum_top_two_margin(r1_score, legal_score_mask)
        if maximum_score_deviation is None or maximum_score_deviation == 0.0:
            margin_ratio = None
        elif minimum_margin_json is None:
            margin_ratio = None
        else:
            margin_ratio = _finite_float_or_none(
                minimum_margin_json / maximum_score_deviation
            )
        selected_action_sha256: str | None = RUNNER.array_sha256(r1_actions)
    else:
        # Do not let NaN/Inf scores reach argmax: the score surface itself is
        # invalid, so the context must fail closed while the other contexts
        # continue and report their own diagnostics.
        selected_actions_equal = False
        maximum_score_deviation = None
        minimum_margin_json = None
        margin_ratio = None
        selected_action_sha256 = None

    # A same-satellite/same-cell pair is the same physical beam (load change,
    # not co-channel interference); different colours are never co-channel.
    same_cell_checks = 0
    same_cell_exclusion_violations = 0
    colour_exclusion_checks = 0
    colour_exclusion_violations = 0
    coupling_entries = 0
    zero_coupling_entries = 0
    zero_coupling_load_unchanged_entries = 0
    coupling_coverage_checks = 0
    coupling_coverage_missing = 0
    zero_coupling_delta_mask = np.zeros_like(delta_eligible)
    zero_coupling_interference_mask = np.zeros_like(delta_eligible)
    reference_loads = dict(r2_cache.reference_load_by_key)
    for uid in range(users):
        for action in np.flatnonzero(legal[uid]).tolist():
            action = int(action)
            changed = _changed_keys(
                focal_user=uid,
                focal_action=action,
                refs=refs,
                opening=opening_values,
                norads=norads,
                cells=cells,
                legal=legal,
            )
            for changed_key in changed:
                coupling_coverage_checks += 1
                if changed_key not in r2_cache.coupling_by_key:
                    coupling_coverage_missing += 1
            r1_branch = R1._branch_actions(refs, focal_user=uid, focal_action=action)
            served = R1._branch_served(r1_branch, opening_values, legal)
            r1_loads, _r1_powers = _branch_maps(
                actions=r1_branch,
                served=served,
                power=power,
                norads=norads,
                cells=cells,
                legal=legal,
            )
            for victim in range(users):
                if victim == uid or not bool(reference_served[victim]):
                    continue
                victim_key = R1._branch_keys(reference_branch, norads, cells, legal)[victim]
                if victim_key is None:
                    continue
                for changed_key in changed:
                    coupling_vector = r2_cache.coupling_by_key.get(changed_key)
                    if coupling_vector is None:
                        continue
                    same_colour = int(colours[victim_key[1]]) == int(colours[changed_key[1]])
                    if victim_key[0] == changed_key[0] and victim_key[1] == changed_key[1]:
                        same_cell_checks += 1
                        if float(coupling_vector[victim]) != 0.0:
                            same_cell_exclusion_violations += 1
                    if not same_colour:
                        colour_exclusion_checks += 1
                        if float(coupling_vector[victim]) != 0.0:
                            colour_exclusion_violations += 1
                coupled = any(
                    float(r2_cache.coupling_by_key[key][victim]) != 0.0
                    for key in changed
                    if key in r2_cache.coupling_by_key
                )
                candidate_load = r1_loads.get(victim_key, 0)
                reference_load = reference_loads.get(victim_key, 0)
                load_unchanged = candidate_load == reference_load
                is_eligible = bool(delta_eligible[uid, action, victim])
                if is_eligible and coupled:
                    coupling_entries += 1
                if is_eligible and not coupled:
                    zero_coupling_entries += 1
                    zero_coupling_interference_mask[uid, action, victim] = True
                    if load_unchanged:
                        zero_coupling_load_unchanged_entries += 1
                        zero_coupling_delta_mask[uid, action, victim] = True
    zero_coupling_delta_report = _comparison_report(
        left=r1_delta,
        right=r2_delta,
        eligible=zero_coupling_delta_mask,
        exact=True,
    )
    zero_coupling_delta_zero_report = _comparison_report(
        left=r1_delta,
        right=np.zeros_like(r1_delta),
        eligible=zero_coupling_delta_mask,
        exact=True,
    )
    zero_coupling_interference_report = _comparison_report(
        left=np.asarray(r1_delta, dtype=np.float64),
        right=np.asarray(r2_delta, dtype=np.float64),
        eligible=zero_coupling_interference_mask,
        exact=False,
        rtol=0.0,
        atol=0.0,
    )
    # The public delta is rate-derived; the previous report above verifies
    # exact delta only where load is also unchanged.  For all zero-coupling
    # entries, compare the primitive interference directly.
    zero_coupling_interference_report = _comparison_report(
        left=candidate_r1_interferences,
        right=candidate_interferences,
        eligible=zero_coupling_interference_mask,
        exact=True,
    )
    victim_diagonal_r1 = all(
        not bool(r1_state.victim_mask[i, :, i].any()) for i in range(users)
    )
    victim_diagonal_r2 = all(
        not bool(r2_state.victim_mask[i, :, i].any()) for i in range(users)
    )

    q3_report = _comparison_report(
        left=r1_q3,
        right=r2_q3,
        rtol=Q3_RTOL,
        atol=Q3_ATOL,
    )
    deviations = {
        "delta": _finite_float_or_none(delta_bound_report["max_abs_deviation"]),
        "q3": _finite_float_or_none(q3_report["max_abs_deviation"]),
        "action_context": _finite_float_or_none(
            action_context_report["max_abs_deviation"]
        ),
        "victim_tokens": _finite_max(
            token04_report["max_abs_deviation"],
            token5_report["max_abs_deviation"],
        ),
    }

    sensitivity: dict[str, Any] = {}
    for constant in DIAGNOSTIC_C:
        report = _comparison_report(
            left=r1_delta,
            right=r2_delta,
            eligible=delta_eligible,
            bound=constant * delta_base_bound,
        )
        sensitivity[str(constant)] = {
            "max_normalized_deviation": report["max_normalized_deviation"],
            "violation_count": report["violation_count"],
            "max_absolute_deviation": report["max_abs_deviation"],
            "bound_max_bits": _finite_float_or_none(
                np.max(constant * delta_base_bound)
            ),
        }

    context_pass = bool(
        primitive_rate["pass"]
        and primitive_interference["pass"]
        and delta_bound_report["pass"]
        and delta_hard_report["pass"]
        and q3_report["pass"]
        and action_context_report["pass"]
        and token04_report["pass"]
        and token5_report["pass"]
        and token5_masked_report["pass"]
        and all(report["pass"] for report in exact_reports.values())
        and victim_predicate_report["pass"]
        and delta_structural_report["pass"]
        and delta_structural_zero_report["pass"]
        and zero_coupling_delta_report["pass"]
        and zero_coupling_delta_zero_report["pass"]
        and zero_coupling_interference_report["pass"]
        and branch_maps_violations == 0
        and focal_rate_violations == 0
        and clamp_invariant_violations == 0
        and coupling_coverage_missing == 0
        and inconsistent_duplicate_branch_arrays == 0
        and same_cell_exclusion_violations == 0
        and colour_exclusion_violations == 0
        and victim_diagonal_r1
        and victim_diagonal_r2
        and scores_finite
        and selected_actions_equal
    )
    return {
        "pass": context_pass,
        "legal_branch_count": int(np.count_nonzero(legal)),
        "unique_branch_vector_count": len(branch_results),
        "reference_reconstruction_elapsed_s": reference_elapsed_s,
        "checked_nonfocal_rate_and_interference_values": checked_nonfocal_values,
        "maximum_nonfocal_rate_deviation_bps": primitive_rate["max_abs_deviation"],
        "maximum_nonfocal_interference_deviation_w": primitive_interference["max_abs_deviation"],
        "maximum_absolute_deviation": deviations,
        "state_content_digest_equal": r1_state.content_digest == r2_state.content_digest,
        "selected_actions_equal": selected_actions_equal,
        "selected_action_sha256": selected_action_sha256,
        "maximum_score_deviation": maximum_score_deviation,
        "minimum_top_two_margin": minimum_margin_json,
        "margin_to_deviation_ratio": margin_ratio,
        "score_check": {
            "scores_finite_on_legal_actions": scores_finite,
            "nonfinite_legal_score_count": nonfinite_score_count,
        },
        "primitive_checks": {
            "reference_rate": reference_rate_report,
            "reference_interference": reference_interference_report,
            "candidate_rate": primitive_rate,
            "candidate_interference": primitive_interference,
        },
        "delta_bound": {
            "mechanical_c": DELTA_C,
            "hard_ceiling_bits": DELTA_HARD_CEILING_BITS,
            "comparison": delta_bound_report,
            "hard_ceiling": delta_hard_report,
            "structural_exact": delta_structural_report,
            "structural_zero": delta_structural_zero_report,
            "sensitivity": sensitivity,
        },
        "q3_check": q3_report,
        "state_exact_checks": {
            "action_context": action_context_report,
            "victim_tokens_columns_0_4": token04_report,
            "victim_tokens_column_5": token5_report,
            "victim_tokens_column_5_masked_exact": token5_masked_report,
            **exact_reports,
        },
        "focal_exclusion": {
            "cached_focal_rate_zero_violations": focal_rate_violations,
            "delta_diagonal_exact_zero": delta_structural_zero_report["pass"],
            "victim_diagonal_r1_exact_false": victim_diagonal_r1,
            "victim_diagonal_r2_exact_false": victim_diagonal_r2,
        },
        "branch_maps": {
            "violations": branch_maps_violations,
            "worst": branch_maps_worst,
            "duplicate_branch_vector_count": duplicate_branch_arrays,
            "inconsistent_duplicate_array_count": inconsistent_duplicate_branch_arrays,
        },
        "clamp_invariant": {
            "activation_count": clamp_count,
            "violations": clamp_invariant_violations,
            "worst": clamp_worst,
        },
        "coupling_coverage": {
            "coupled_entries": coupling_entries,
            "zero_coupling_entries": zero_coupling_entries,
            "zero_coupling_load_unchanged_entries": zero_coupling_load_unchanged_entries,
            "changed_key_checks": coupling_coverage_checks,
            "changed_key_missing_from_cache": coupling_coverage_missing,
            "zero_coupling_delta_exact": zero_coupling_delta_report,
            "zero_coupling_delta_zero": zero_coupling_delta_zero_report,
            "zero_coupling_interference_exact": zero_coupling_interference_report,
        },
        "victim_predicate": {
            "independent_match": victim_predicate_report,
            "same_cell_checks": same_cell_checks,
            "same_cell_cochannel_violations": same_cell_exclusion_violations,
            "different_colour_checks": colour_exclusion_checks,
            "different_colour_cochannel_violations": colour_exclusion_violations,
        },
    }


def _context_error_report(context_code: int, error: BaseException) -> dict[str, Any]:
    """Persist one context exception without preventing later contexts."""

    return {
        "pass": False,
        "context_code": int(context_code),
        "comparison_completed": False,
        "error_type": type(error).__name__,
        "error": str(error)[:4000],
        "traceback": traceback.format_exc(limit=20)[:12000],
    }


def run(
    output: Path,
    *,
    workers: int,
    tle_root: Path,
    code_manifest: Path,
    code_manifest_sha256: str,
    preflight_receipt: Path,
    preflight_log: Path,
) -> dict[str, Any]:
    contract_sha256 = validate_contract()
    initial_runner_sha256 = file_sha256(Path(__file__).resolve())
    initial_r2_sha256 = file_sha256(Path(R2.__file__).resolve())
    if output.exists() or output.is_symlink():
        raise RuntimeError(f"refusing to overwrite output: {output}")
    if workers < 1 or workers > MAX_WORKERS:
        raise RuntimeError(f"workers must be in [1,{MAX_WORKERS}]")
    tle_source = Path(tle_root)
    if not tle_source.is_absolute() or tle_source.is_symlink() or not tle_source.is_dir():
        raise RuntimeError("TLE root must be an existing non-symlink absolute directory")
    external_closure = _authenticate_external_closure(
        code_manifest=code_manifest,
        code_manifest_sha256=code_manifest_sha256,
        preflight_receipt=preflight_receipt,
        preflight_log=preflight_log,
    )
    q2_gate = RUNNER._V015.validate_v014_gate_receipts(RUNNER.V014_GATE_ROOT)
    q1, q1_receipt = RUNNER._V015.load_frozen_q1(RUNNER.V03_ROOT, LINEAGE)
    q2, q2_receipt = RUNNER._V015.load_frozen_q2(
        RUNNER.V014_GATE_ROOT, lineage=LINEAGE, gate_receipt=q2_gate
    )
    record = RUNNER._V015._V013.read_prereg(RUNNER.DEFAULT_PREREG)
    tle_file_set_sha256 = hashlib.sha256(
        canonical_bytes(record.sections["ephemeris"]["frozen_files"])
    ).hexdigest()
    field = KeyedFadingField.from_components(RUNNER.FIELD_COMPONENT, WORLD_SEED)
    with tempfile.TemporaryDirectory(prefix="mcrl-v018-r4-equivalence-tle-") as temporary:
        archive = RUNNER._V015._V013.screen._frozen_archive(
            record, tle_source, Path(temporary) / "frozen-tle"
        )
        wrapper = RUNNER._V015._V013.screen._make_environment(
            archive, users=RUNNER.USERS
        )
        wrapper.environment._fading_field = field
        env_rng, mobility_rng, _action_rng, _control_rng = (
            RUNNER._V015._V013.screen._evaluation_rngs(WORLD_SEED)
        )
        _states, _masks, observation = wrapper.reset(env_rng, mobility_rng)
        environment = wrapper.environment
        initial_digest = RUNNER._live_digest(wrapper, env_rng)
        initial_world_sha256 = RUNNER._initial_world_sha(wrapper, observation)
        native = encode_ee_axis_state(environment, observation)
        masks = np.asarray(native.action_masks, dtype=np.bool_)
        q1_values = RUNNER._q1_values(q1, native.state_matrix, masks)
        q1_reference = RUNNER._V015.select_actions(
            q1_values,
            np.zeros_like(q1_values),
            np.zeros_like(q1_values),
            masks,
            include_c3=False,
        )
        anchor = snapshot_ops3_anchor(environment, observation)
        projection = project_ops3_anchor(anchor)
        ops3_surfaces = build_ops3_live_surfaces(anchor, projection, q1_reference)
        q2_state = RUNNER._V015.encode_ee_axis_v014_q2_states(ops3_surfaces)
        learned_q2 = RUNNER._q2_values(
            q2, q2_state.state_matrix, q2_state.action_masks
        )
        required, opening = RUNNER._current_required_power_and_opening(
            current_gain_linear=anchor.current_gain_linear,
            segment_start_gain_linear=anchor.segment_start_gain_linear,
            action_masks=masks,
        )
        backgrounds = {12: q1_values + learned_q2, 1: q1_values, 2: learned_q2}
        reports: dict[str, Any] = {}
        for context_code in CONTEXTS:
            background = np.asarray(backgrounds[context_code], dtype=np.float64)
            references = _masked_argmax(background, masks)
            try:
                reports[str(context_code)] = _context_result(
                    environment=environment,
                    observation=observation,
                    references=references,
                    background=background,
                    required=required,
                    opening=opening,
                    workers=workers,
                )
            except Exception as error:  # preserve later-context diagnostics
                reports[str(context_code)] = _context_error_report(
                    context_code, error
                )
        final_digest = RUNNER._live_digest(wrapper, env_rng)
        if final_digest != initial_digest:
            raise RuntimeError("equivalence check changed live environment or RNG")
    if file_sha256(Path(__file__).resolve()) != initial_runner_sha256:
        raise RuntimeError("equivalence runner changed during execution")
    if file_sha256(Path(R2.__file__).resolve()) != initial_r2_sha256:
        raise RuntimeError("R2 cached runtime changed during execution")
    if file_sha256(CONTRACT_PATH) != contract_sha256:
        raise RuntimeError("equivalence contract changed during execution")
    if file_sha256(R1_PATH) != R1_SHA256:
        raise RuntimeError("sealed R1 reference changed during execution")
    if file_sha256(RUNNER.DEFAULT_PREREG) != PREREG_SHA256:
        raise RuntimeError("frozen base preregistration changed during execution")
    final_external_closure = _authenticate_external_closure(
        code_manifest=code_manifest,
        code_manifest_sha256=code_manifest_sha256,
        preflight_receipt=preflight_receipt,
        preflight_log=preflight_log,
    )
    if final_external_closure != external_closure:
        raise RuntimeError("manifest or preflight closure changed during execution")
    result = {
        "schema": RESULT_SCHEMA,
        "execution_attempt": "r4",
        "decision": (
            "PASS_R2_CACHE_EQUIVALENCE"
            if all(bool(report.get("pass")) for report in reports.values())
            else "STOP_R2_CACHE_EQUIVALENCE"
        ),
        "passed": all(bool(report.get("pass")) for report in reports.values()),
        "split": "TRAIN_PREVIOUSLY_OPENED",
        "test_split_opened": False,
        "action_executed": False,
        "exact_teacher_opened": False,
        "learner_update": False,
        "episode_training": False,
        "world_seed": WORLD_SEED,
        "lineage": LINEAGE,
        "users": RUNNER.USERS,
        "contexts": list(CONTEXTS),
        "workers": workers,
        "tle_root": str(tle_source.resolve()),
        "prereg_sha256": file_sha256(RUNNER.DEFAULT_PREREG),
        "tle_file_set_sha256": tle_file_set_sha256,
        "field_component": RUNNER.FIELD_COMPONENT,
        "initial_world_sha256": initial_world_sha256,
        "initial_live_state_rng_sha256": initial_digest,
        "contract_sha256": contract_sha256,
        "r1_source_sha256": file_sha256(R1_PATH),
        "r2_source_sha256": initial_r2_sha256,
        "runner_sha256": initial_runner_sha256,
        **external_closure,
        "q1_checkpoint": q1_receipt,
        "q2_checkpoint": q2_receipt,
        "live_state_rng_unchanged": True,
        "reports": reports,
    }
    result_bytes = canonical_bytes(result)
    result_sha256 = bytes_sha256(result_bytes)
    receipt = {
        "schema": "multi-catfish-mcrl-v018-r4-equivalence-receipt-v1",
        "result_sha256": result_sha256,
        "contract_sha256": contract_sha256,
        "code_manifest_sha256": external_closure["code_manifest_sha256"],
        "preflight_receipt_sha256": external_closure["preflight_receipt_sha256"],
        "preflight_log_sha256": external_closure["preflight_log_sha256"],
        "runner_sha256": initial_runner_sha256,
        "r1_source_sha256": file_sha256(R1_PATH),
        "r2_source_sha256": initial_r2_sha256,
        "prereg_sha256": file_sha256(RUNNER.DEFAULT_PREREG),
        "world_seed": WORLD_SEED,
        "lineage": LINEAGE,
        "test_split_opened": False,
        "action_executed": False,
        "learner_update": False,
        "episode_training": False,
        "decision": result["decision"],
    }
    receipt_bytes = canonical_bytes(receipt)
    output.mkdir(parents=True, exist_ok=False)
    result_path = output / "result.json"
    result_path.write_bytes(result_bytes)
    (output / "receipt.json").write_bytes(receipt_bytes)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    execute = subparsers.add_parser("run")
    execute.add_argument("--output", type=Path, required=True)
    execute.add_argument("--workers", type=int, default=MAX_WORKERS)
    execute.add_argument(
        "--tle-root",
        type=Path,
        default=RUNNER.DEFAULT_TLE_ROOT,
    )
    execute.add_argument("--code-manifest", type=Path, required=True)
    execute.add_argument("--code-manifest-sha256", required=True)
    execute.add_argument("--preflight-receipt", type=Path, required=True)
    execute.add_argument("--preflight-log", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        print(
            json.dumps(
                {
                    "world_seed": WORLD_SEED,
                    "lineage": LINEAGE,
                    "users": RUNNER.USERS,
                    "contexts": list(CONTEXTS),
                    "max_workers": MAX_WORKERS,
                    "mechanical_delta_c": DELTA_C,
                    "diagnostic_delta_c": list(DIAGNOSTIC_C),
                    "delta_hard_ceiling_bits": DELTA_HARD_CEILING_BITS,
                    "primitive_rate_rtol": PRIMITIVE_RATE_RTOL,
                    "primitive_rate_atol": PRIMITIVE_RATE_ATOL,
                    "primitive_interference_rtol": PRIMITIVE_INTERFERENCE_RTOL,
                    "primitive_interference_atol": PRIMITIVE_INTERFERENCE_ATOL,
                    "q3_rtol": Q3_RTOL,
                    "q3_atol": Q3_ATOL,
                    "default_tle_root": str(RUNNER.DEFAULT_TLE_ROOT),
                    "test_split_opened": False,
                    "action_executed": False,
                },
                sort_keys=True,
            )
        )
        return
    try:
        result = run(
            args.output,
            workers=args.workers,
            tle_root=args.tle_root,
            code_manifest=args.code_manifest,
            code_manifest_sha256=args.code_manifest_sha256,
            preflight_receipt=args.preflight_receipt,
            preflight_log=args.preflight_log,
        )
    except Exception as error:
        if args.output.exists() or args.output.is_symlink():
            raise
        failure = {
            "schema": RESULT_SCHEMA,
            "execution_attempt": "r4",
            "decision": "STOP_R2_CACHE_EQUIVALENCE",
            "passed": False,
            "split": "TRAIN_PREVIOUSLY_OPENED",
            "test_split_opened": False,
            "action_executed": False,
            "exact_teacher_opened": False,
            "learner_update": False,
            "episode_training": False,
            "world_seed": WORLD_SEED,
            "lineage": LINEAGE,
            "users": RUNNER.USERS,
            "contexts": list(CONTEXTS),
            "workers": args.workers,
            "tle_root": str(Path(args.tle_root).resolve()),
            "contract_sha256": (
                file_sha256(CONTRACT_PATH) if CONTRACT_PATH.is_file() else None
            ),
            "code_manifest_sha256_expected": args.code_manifest_sha256,
            "code_manifest_sha256": _safe_file_sha256(args.code_manifest),
            "preflight_receipt_sha256": _safe_file_sha256(
                args.preflight_receipt
            ),
            "preflight_log_sha256": _safe_file_sha256(args.preflight_log),
            "r1_source_sha256": _safe_file_sha256(R1_PATH),
            "r2_source_sha256": _safe_file_sha256(
                Path(R2.__file__).resolve()
            ),
            "runner_sha256": _safe_file_sha256(Path(__file__).resolve()),
            "error_type": type(error).__name__,
            "error": str(error)[:4000],
            "traceback": traceback.format_exc(limit=20)[:12000],
        }
        failure_bytes = canonical_bytes(failure)
        failure_sha256 = bytes_sha256(failure_bytes)
        receipt = {
            "schema": "multi-catfish-mcrl-v018-r4-equivalence-receipt-v1",
            "result_sha256": failure_sha256,
            "contract_sha256": failure["contract_sha256"],
            "code_manifest_sha256": failure["code_manifest_sha256"],
            "preflight_receipt_sha256": failure["preflight_receipt_sha256"],
            "preflight_log_sha256": failure["preflight_log_sha256"],
            "runner_sha256": failure["runner_sha256"],
            "r1_source_sha256": failure["r1_source_sha256"],
            "r2_source_sha256": failure["r2_source_sha256"],
            "world_seed": WORLD_SEED,
            "lineage": LINEAGE,
            "test_split_opened": False,
            "action_executed": False,
            "learner_update": False,
            "episode_training": False,
            "decision": failure["decision"],
        }
        receipt_bytes = canonical_bytes(receipt)
        args.output.mkdir(parents=True, exist_ok=False)
        result_path = args.output / "result.json"
        result_path.write_bytes(failure_bytes)
        (args.output / "receipt.json").write_bytes(receipt_bytes)
        print(json.dumps({"decision": failure["decision"], "error": failure["error"]}, sort_keys=True))
        raise SystemExit(1) from error
    print(
        json.dumps(
            {"decision": result["decision"], "reports": result["reports"]},
            sort_keys=True,
        )
    )
    if not bool(result["passed"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
