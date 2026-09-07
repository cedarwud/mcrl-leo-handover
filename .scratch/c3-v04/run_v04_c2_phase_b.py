#!/usr/bin/env python3
"""Materialize the V0.4 C2 matched-Q1+Q3 continuation (Phase B).

This consumer is deliberately separate from the support-complete Phase-A
runner.  Phase A is an authenticated, shared Main-continuation census.  Phase
B replays the same sealed 324 sibling schedule under one frozen V0.4 hybrid
per invocation, where only Q1+Q3 select the continuation after the opening
intervention.  The three initialization shards have disjoint output
directories and can therefore run concurrently on the server.  ``merge`` is
the only command that combines them and it writes one deterministic result.

No command in this file trains a network, opens TEST, evaluates the held-out
EE endpoint, or modifies the Phase-A artifact.  The result is a physical
authorization/target artifact for the separately preregistered P1/P2 screen.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import copy
from dataclasses import replace
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from types import ModuleType
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (HERE, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def _load_file_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module {name}: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


support = _load_file_module(
    "mcrl_v04_c2_support_phase_b", HERE / "run_v04_c2_support_complete_census.py"
)
# The screen consumer imports torch and the checkpoint stack.  Keep it behind
# the server-only command boundary so contract/authentication helpers remain
# importable in the lightweight test environment.
screen: ModuleType | None = None


def _screen_module() -> ModuleType:
    global screen
    if screen is None:
        screen = _load_file_module(
            "mcrl_v04_c3_screen_phase_b", HERE / "run_v04_c3_500_update_screen.py"
        )
    return screen

from mcrl.env.action_contract import NUM_ACTIONS  # noqa: E402
from mcrl.runtime.ee_axis_state import (  # noqa: E402
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)
# These two runtime adapters import torch through the pairwise learner stack.
# Load them only once a server shard has passed all artifact authentication;
# contract tests and CLI help must remain usable without torch.
C2_POLICY_VERSION = "C2_V0.3B_HOLD_WHILE_LEGAL_MONOTONE_RELEASE"


def _select_frozen_q13_continuation(*args: Any, **kwargs: Any) -> Any:
    from mcrl.runtime.ee_axis_v04_c2_q13_continuation import (
        select_frozen_q13_continuation,
    )

    return select_frozen_q13_continuation(*args, **kwargs)


def _build_temporal_pair(*args: Any, **kwargs: Any) -> Any:
    from mcrl.runtime.ee_axis_temporal_pairs import build_temporal_pair

    return build_temporal_pair(*args, **kwargs)


# Frozen Phase-B protocol ---------------------------------------------------

PHASE_B_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-b-v1"
PHASE_B_ROW_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-b-row-v1"
PHASE_B_SHARD_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-b-shard-v1"
PHASE_B_SEAL_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-b-seal-v1"
PHASE_B_SHARD_SEAL_SCHEMA = (
    "multi-catfish-mcrl-v04-c2-support-complete-phase-b-shard-seal-v1"
)
PHASE_B_ANCHOR_STATE_SCHEMA = (
    "multi-catfish-mcrl-v04-c2-support-complete-anchor-state-v1"
)
PHASE_B_CLAIM_CEILING = (
    "FRESH_TRAIN_DESIGN_PROBE_ONLY_NO_TRAINING_NO_TEST_NO_EE_EFFICACY"
)
PHASE_B_DECISION = "AUTHORIZE_PARALLEL_SUPPORT_COMPLETE_C2_SCREEN"
PHASE_B_REDESIGN = "NEXT_C2_FORMULA_PHYSICS_BATCH_REQUIRED"
C2_P0_MAIN_VALUE = "C2-P0-MAIN-VALUE"
C2_P1_Q13_VALUE = "C2-P1-Q13-VALUE"
C2_P2_Q13_HUBER = "C2-P2-Q13-HUBER"
Q13_CONTINUATION = "frozen-q1-plus-q3-after-opening-v1"
Q13_INIT_SEEDS = tuple(support.Q2_INITIALIZATION_SEEDS)
EXPECTED_ROWS_PER_SHARD = support.EXPECTED_SIBLINGS
EXPECTED_TOTAL_ROWS = EXPECTED_ROWS_PER_SHARD * len(Q13_INIT_SEEDS)
HORIZON = 4
DOWNSTREAM_OFFSETS = (1, 2, 3)
GC_CORRELATION_THRESHOLD = 0.6
ALTERNATE_LAMBDA_BITS_PER_J = 105_010_574.08

DEFAULT_PHASE_A_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-c2-support-complete-census-20260901-r3"
)
DEFAULT_GATE_DIR = REPO / "artifacts" / "multi-catfish-v04-c3-learnability-20260901-r2"
DEFAULT_C3_SOURCE_DIR = REPO / "artifacts" / "multi-catfish-v04-c3-source-20260901-r2"
DEFAULT_V03_ROOT = (
    REPO / "artifacts" / "multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"
)
DEFAULT_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
DEFAULT_TLE_ROOT = Path("~/demo/tle_data/starlink/tle").expanduser()
DEFAULT_OUTPUT_ROOT = (
    REPO / "artifacts" / "multi-catfish-v04-c2-phase-b-20260901-r1"
)


class PhaseBError(RuntimeError):
    """A Phase-B input, physical pair, or artifact failed closed."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return (
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise PhaseBError("payload is not finite canonical JSON") from error


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)[:-1]).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PhaseBError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _read_json(path: Path) -> tuple[dict[str, Any], str]:
    if path.is_symlink() or not path.is_file():
        raise PhaseBError(f"sealed JSON artifact is missing or non-regular: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(
            raw.decode("ascii"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise PhaseBError(f"sealed JSON artifact is invalid: {path}") from error
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        raise PhaseBError(f"sealed JSON artifact is not canonical: {path}")
    return payload, hashlib.sha256(raw).hexdigest()


def _write_once(path: Path, payload: object) -> str:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite Phase-B artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _canonical_bytes(payload)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    except FileExistsError as error:
        raise FileExistsError(f"refusing to overwrite Phase-B artifact: {path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(raw).hexdigest()


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, bool):
        raise PhaseBError(f"{field} must be finite numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise PhaseBError(f"{field} must be finite numeric") from error
    if not math.isfinite(result):
        raise PhaseBError(f"{field} must be finite numeric")
    return result


def _positive(value: object, *, field: str) -> float:
    result = _finite(value, field=field)
    if result <= 0.0:
        raise PhaseBError(f"{field} must be positive")
    return result


def _float_matrix(value: object, *, field: str) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise PhaseBError(f"{field} is not numeric") from error
    if array.ndim != 2 or not np.all(np.isfinite(array)):
        raise PhaseBError(f"{field} must be a finite matrix")
    return array


def _bool_matrix(value: object, *, field: str) -> np.ndarray:
    array = np.asarray(value)
    if array.dtype != np.bool_ or array.ndim != 2:
        raise PhaseBError(f"{field} must be a Boolean matrix")
    return array


def _physical(value: object, *, field: str) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise PhaseBError(f"{field} must be a two-integer physical key")
    if any(type(item) is not int or item < 0 for item in value):
        raise PhaseBError(f"{field} must be a two-integer physical key")
    return int(value[0]), int(value[1])


def _sibling_key(value: object, *, field: str = "sibling_key") -> tuple[int, str, str, int, tuple[int, int]]:
    if not isinstance(value, (list, tuple)) or len(value) != 5:
        raise PhaseBError(f"{field} is malformed")
    if type(value[0]) is not int or value[0] < 0 or not isinstance(value[1], str) or not isinstance(value[2], str):
        raise PhaseBError(f"{field} is malformed")
    if type(value[3]) is not int or value[3] < 0:
        raise PhaseBError(f"{field} is malformed")
    return (int(value[0]), value[1], value[2], int(value[3]), _physical(value[4], field=f"{field}[4]"))


def _intervention_key(key: tuple[int, str, str, int, tuple[int, int]]) -> tuple[int, str, str, int]:
    return key[:4]


def _array_sha256(*arrays: object) -> str:
    digest = hashlib.sha256()
    for raw in arrays:
        value = np.asarray(raw)
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(json.dumps(list(value.shape), separators=(",", ":")).encode("ascii"))
        digest.update(np.ascontiguousarray(value).tobytes(order="C"))
    return digest.hexdigest()


def _error_text(error: BaseException) -> str:
    detail = " ".join(str(error).split()) or "unspecified"
    return f"{type(error).__name__}:{detail}"


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _code_manifest(paths: Sequence[Path]) -> dict[str, object]:
    files = []
    for path in sorted({Path(item).resolve() for item in paths}, key=str):
        if path.is_symlink() or not path.is_file():
            raise PhaseBError(f"Phase-B source file is missing/non-regular: {path}")
        files.append({"path": _relative(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    body = {"schema": "multi-catfish-mcrl-v04-c2-phase-b-code-manifest-v1", "files": files}
    return body | {"code_manifest_sha256": _canonical_sha256(body)}


def _phase_b_code_manifest() -> dict[str, object]:
    paths = [
        Path(__file__),
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_v04_c2_q13_continuation.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_temporal_pairs.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_temporal_capture.py",
        REPO / "src" / "mcrl" / "algorithms" / "ee_axis_v04_hybrid.py",
        HERE / "run_v04_c2_support_complete_census.py",
        HERE / "run_v04_c3_500_update_screen.py",
        HERE.parent / "c2-v03" / "c2_temporal_fork_trainer_backend.py",
        HERE.parent / "c2-v03" / "c2_temporal_fork_forecast_adapter.py",
        HERE.parent / "c2-v03" / "c2_temporal_fork_core.py",
        HERE.parent / "c2-v03" / "c2_temporal_fork_chronology.py",
    ]
    return _code_manifest(paths)


# Authenticated input boundaries -------------------------------------------

def _authenticate_phase_a(
    phase_a_dir: Path,
    *,
    prereg_path: Path,
) -> dict[str, Any]:
    """Authenticate the exact r3 Phase-A result and its shared schedule."""

    root = Path(phase_a_dir)
    modules = support._production_modules()
    try:
        prepared, prepare_receipt = support._authenticate_production_prepare(
            output_dir=root,
            prereg_path=Path(prereg_path),
            modules=modules,
        )
    except Exception as error:
        raise PhaseBError("Phase-A prepare authentication failed") from error
    result, result_file_sha = _read_json(root / "phase-a-result.json")
    seal, seal_file_sha = _read_json(root / "phase-a-seal.json")
    if (
        result.get("schema") != support.C2_V04_PHASE_A_SCHEMA
        or result.get("claim_ceiling") != support.CLAIM_CEILING
        or result.get("source_rule") != support.C2_V04_SUPPORT_COMPLETE_SOURCE_RULE
        or result.get("row_count") != support.EXPECTED_SIBLINGS
        or result.get("expected_row_count") != support.EXPECTED_SIBLINGS
        or result.get("counterfactual_outcomes_evaluated") is not True
        or result.get("training_run") is not False
        or result.get("test_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
        or result.get("decision") != support.V04_PHASE_A_DECISION
        or result.get("schedule_sha256") != prepared.schedule.schedule_sha256
        or result.get("prepare_sha256") != prepared.prepare_sha256
        or result.get("phase_a_sha256") != _canonical_sha256({key: value for key, value in result.items() if key != "phase_a_sha256"})
    ):
        raise PhaseBError("Phase-A result is not the authenticated passing r3 result")
    gates = result.get("gates")
    if not isinstance(gates, Mapping) or any(gates.get(name, {}).get("passed") is not True for name in ("G-S", "G-R", "G-V")):
        raise PhaseBError("Phase-A G-S/G-R/G-V did not all pass")
    if (
        seal.get("schema") != "multi-catfish-mcrl-v04-c2-support-complete-phase-a-seal-v1"
        or seal.get("status") != "PHASE_A_COMPLETE"
        or seal.get("phase_a_file_sha256") != result_file_sha
        or seal.get("phase_a_sha256") != result["phase_a_sha256"]
        or seal.get("prepare_sha256") != prepared.prepare_sha256
        or seal.get("schedule_sha256") != prepared.schedule.schedule_sha256
        or seal.get("row_count") != support.EXPECTED_SIBLINGS
        or seal.get("training_run") is not False
        or seal.get("test_opened") is not False
        or seal.get("held_out_ee_evaluated") is not False
    ):
        raise PhaseBError("Phase-A seal is invalid")
    expected_keys = {row.sibling_key for row in prepared.schedule.rows}
    rows = result.get("rows")
    if not isinstance(rows, list) or len(rows) != support.EXPECTED_SIBLINGS:
        raise PhaseBError("Phase-A does not retain exactly 324 rows")
    seen: set[tuple[int, str, str, int, tuple[int, int]]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise PhaseBError("Phase-A row is malformed")
        key = _sibling_key(row.get("sibling_key"))
        if key in seen or key not in expected_keys:
            raise PhaseBError("Phase-A row identity is duplicate or unscheduled")
        seen.add(key)
    if seen != expected_keys:
        raise PhaseBError("Phase-A row identity set is incomplete")
    return {
        "dir": root,
        "prepared": prepared,
        "prepare_receipt": prepare_receipt,
        "result": result,
        "result_file_sha256": result_file_sha,
        "seal": seal,
        "seal_file_sha256": seal_file_sha,
        "schedule_sha256": prepared.schedule.schedule_sha256,
        "prepare_sha256": prepared.prepare_sha256,
        "modules": modules,
    }


def _authenticate_q13_gate(
    gate_dir: Path,
    *,
    source_dir: Path,
    prereg_path: Path,
    v03_root: Path,
) -> dict[str, Any]:
    """Authenticate the exact r3/selected-rung-100 Q1+Q3 hybrids."""

    frozen_source, frozen_source_file_sha = _read_json(
        Path(source_dir) / "source-manifest.json"
    )
    frozen_source_body = dict(frozen_source)
    frozen_source_sha = _digest(
        frozen_source_body.pop("source_manifest_sha256", None),
        field="frozen_source.source_manifest_sha256",
    )
    if _canonical_sha256(frozen_source_body) != frozen_source_sha:
        raise PhaseBError("frozen Q1+Q3 source manifest digest is invalid")
    try:
        # Phase B consumes only the already sealed gate-selected checkpoints,
        # not the C3 TRAIN datasets.  Use the gate consumer's intentional
        # receipt-only seam so a later, separately preregistered C2 source-rule
        # addition cannot make the immutable C3 checkpoint lineage appear
        # invalid merely because the current checkout has advanced.
        receipt = _screen_module().authenticate_gate(
            Path(gate_dir), source_dir=None, prereg_path=Path(prereg_path)
        )
    except Exception as error:
        raise PhaseBError("Q1+Q3 gate authentication failed") from error
    if receipt.get("source_manifest_sha256") != frozen_source_sha:
        raise PhaseBError("frozen Q1+Q3 source manifest is not bound to the gate")
    if receipt.get("selected_q3_rung") != 100:
        raise PhaseBError("Q1+Q3 gate is not the selected rung-100 authority")
    selected = receipt.get("selected_hybrid_paths")
    if not isinstance(selected, Mapping) or set(selected) != {str(seed) for seed in Q13_INIT_SEEDS}:
        raise PhaseBError("Q1+Q3 gate does not contain exactly three initialization hybrids")
    hashes: dict[str, str] = {}
    paths: dict[str, str] = {}
    for seed in Q13_INIT_SEEDS:
        path = Path(selected[str(seed)])
        if not path.is_absolute():
            path = REPO / path
        if path.is_symlink() or not path.is_file():
            raise PhaseBError(f"selected Q1+Q3 hybrid is missing: {path}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        selected_receipts = receipt.get("result", {}).get("selected_hybrids", {})
        selected_receipt = selected_receipts.get(str(seed)) if isinstance(selected_receipts, Mapping) else None
        if not isinstance(selected_receipt, Mapping):
            raise PhaseBError(f"selected Q1+Q3 hybrid receipt is missing for {seed}")
        expected = _digest(
            selected_receipt.get("file_sha256"),
            field=f"selected_hybrids[{seed}].file_sha256",
        )
        # screen.authenticate_gate authenticates the selected artifact bytes;
        # this second explicit check binds the path we are about to load.
        if expected is not None and actual != expected:
            raise PhaseBError(f"selected Q1+Q3 hybrid SHA drifted for {seed}")
        paths[str(seed)] = str(path.resolve())
        hashes[str(seed)] = actual
    return receipt | {
        "gate_dir": Path(gate_dir),
        "source_dir": Path(source_dir),
        "v03_root": Path(v03_root),
        "selected_hybrid_paths": paths,
        "selected_hybrid_file_sha256": hashes,
        "frozen_source_manifest_file_sha256": frozen_source_file_sha,
    }


def _phase_a_rows_by_key(result: Mapping[str, Any]) -> dict[tuple[int, str, str, int, tuple[int, int]], Mapping[str, Any]]:
    rows = result.get("rows")
    if not isinstance(rows, list):
        raise PhaseBError("Phase-A rows are missing")
    return {_sibling_key(row["sibling_key"]): row for row in rows if isinstance(row, Mapping)}


def _state_and_mask(
    *,
    modules: Mapping[str, Any],
    wrapped: Any,
    observation: Any,
    focal_user: int,
) -> tuple[np.ndarray, np.ndarray, str, str, str]:
    encoded = modules["ee_axis_state"].encode_ee_axis_state(wrapped.environment, observation)
    state = np.asarray(encoded.state_matrix[focal_user], dtype=np.float32).copy()
    mask = np.asarray(encoded.action_masks[focal_user], dtype=np.bool_).copy()
    state.setflags(write=False)
    mask.setflags(write=False)
    if state.shape != (EE_AXIS_STATE_DIM,) or mask.shape != (NUM_ACTIONS,) or not np.all(np.isfinite(state)):
        raise PhaseBError("Q1+Q3 pair anchor is not a finite 228/28 state")
    if not np.all(mask):
        raise PhaseBError("Phase-B schedule requires a complete 28-action anchor")
    return state, mask, encoded.schema, encoded.schema_sha256, encoded.state_sha256


def _anchor_state_record(
    *,
    state: np.ndarray,
    mask: np.ndarray,
    state_schema: str,
    state_schema_sha256: str,
    state_observation_sha256: str,
) -> dict[str, object]:
    """Make the focal learner-state authority needed to join Phase A targets.

    Phase A intentionally retained only physical target traces.  Phase B
    therefore persists the exact state/mask reconstructed from the sealed
    schedule anchor.  The record is duplicated in every ready row and later
    collapsed/checked per cluster at merge; this makes a shard self-contained
    without mutating the sealed Phase-A artifact.
    """

    values = np.asarray(state, dtype=np.float32)
    masks = np.asarray(mask, dtype=np.bool_)
    if values.shape != (EE_AXIS_STATE_DIM,) or masks.shape != (NUM_ACTIONS,):
        raise PhaseBError("anchor state authority must be exactly 228-D/28-action")
    if not np.all(np.isfinite(values)) or not bool(np.all(masks)):
        raise PhaseBError("anchor state authority is nonfinite or incomplete")
    body: dict[str, object] = {
        "schema": PHASE_B_ANCHOR_STATE_SCHEMA,
        "state_schema": str(state_schema),
        "state_schema_sha256": _digest(state_schema_sha256, field="state_schema_sha256"),
        "state_observation_sha256": _digest(
            state_observation_sha256, field="state_observation_sha256"
        ),
        "state": values.tolist(),
        "action_mask": masks.tolist(),
        "state_row_sha256": _array_sha256(values),
        "mask_row_sha256": _array_sha256(masks),
    }
    body["anchor_state_sha256"] = _canonical_sha256(body)
    return body


def _validate_anchor_state_record(value: object, *, field: str) -> dict[str, object]:
    """Validate a persisted 228/28 anchor-state record without coercion gaps."""

    if not isinstance(value, Mapping):
        raise PhaseBError(f"{field} is missing or malformed")
    record = dict(value)
    digest = _digest(record.pop("anchor_state_sha256", None), field=f"{field}.anchor_state_sha256")
    if record.get("schema") != PHASE_B_ANCHOR_STATE_SCHEMA:
        raise PhaseBError(f"{field}.schema is stale")
    if record.get("state_schema") != EE_AXIS_STATE_SCHEMA:
        raise PhaseBError(f"{field}.state_schema is stale")
    if record.get("state_schema_sha256") != EE_AXIS_STATE_SCHEMA_SHA256:
        raise PhaseBError(f"{field}.state_schema_sha256 drifted")
    state = np.asarray(record.get("state"), dtype=np.float32)
    mask_raw = np.asarray(record.get("action_mask"))
    if state.shape != (EE_AXIS_STATE_DIM,) or not np.all(np.isfinite(state)):
        raise PhaseBError(f"{field}.state must be a finite 228-vector")
    if mask_raw.dtype != np.bool_ or mask_raw.shape != (NUM_ACTIONS,) or not bool(np.all(mask_raw)):
        raise PhaseBError(f"{field}.action_mask must be a complete Boolean 28-vector")
    if record.get("state_row_sha256") != _array_sha256(state):
        raise PhaseBError(f"{field}.state_row_sha256 drifted")
    if record.get("mask_row_sha256") != _array_sha256(mask_raw):
        raise PhaseBError(f"{field}.mask_row_sha256 drifted")
    if digest != _canonical_sha256(record):
        raise PhaseBError(f"{field}.anchor_state_sha256 drifted")
    record["anchor_state_sha256"] = digest
    return record


def _decision_mapping(decision: Any, *, offset: int) -> dict[str, object]:
    return {
        "offset": int(offset),
        "schema": decision.schema,
        "initialization_seed": int(decision.initialization_seed),
        "selected_q3_rung": int(decision.selected_q3_rung),
        "legacy_state_sha256": decision.legacy_state_sha256,
        "c3_state_sha256": decision.c3_state_sha256,
        "mask_sha256": decision.mask_sha256,
        "q1_sha256": decision.q1_sha256,
        "q3_sha256": decision.q3_sha256,
        "actions": [int(value) for value in decision.actions],
        "decision_sha256": decision.decision_sha256,
    }


def _trace_mapping(trace: Sequence[Any]) -> dict[str, object]:
    """Persist physical trace fields and all action/compositor lineage."""

    return {
        "offsets": [int(step.offset) for step in trace],
        "state_matrix_sha256": [_array_sha256(np.asarray(step.state_matrix)) for step in trace],
        "mask_matrix_sha256": [_array_sha256(np.asarray(step.mask_matrix)) for step in trace],
        "detached_main_actions": [[int(value) for value in step.detached_main_actions] for step in trace],
        "detached_main_physical_actions": [
            [None if value is None else [int(value[0]), int(value[1])] for value in step.detached_main_physical_actions]
            for step in trace
        ],
        "executed_actions": [[int(value) for value in step.executed_actions] for step in trace],
        "executed_physical_actions": [
            [None if value is None else [int(value[0]), int(value[1])] for value in step.executed_physical_actions]
            for step in trace
        ],
        "served": [[bool(value) for value in step.served] for step in trace],
        "link_rate_bps": [[float(value) for value in step.link_rate_bps] for step in trace],
        "system_power_w": [float(step.system_power_w) for step in trace],
        "active_physical_ids": [
            [[int(value[0]), int(value[1])] for value in step.active_physical_ids]
            for step in trace
        ],
        "done": [bool(step.done) for step in trace],
        "held_physical_key": [
            None if step.held_physical_key is None else [int(step.held_physical_key[0]), int(step.held_physical_key[1])]
            for step in trace
        ],
        "held_key_match_count": [
            None if step.held_key_match_count is None else int(step.held_key_match_count)
            for step in trace
        ],
        "release_offset": [None if step.release_offset is None else int(step.release_offset) for step in trace],
        "release_reason": [step.release_reason for step in trace],
    }


def _pair_mapping(pair: Any) -> dict[str, object]:
    return {
        "c2_policy_version": pair.c2_policy_version,
        "source_rule": pair.source_rule,
        "source_route": pair.source_route,
        "anchor_sha256": pair.anchor_sha256,
        "anchor_schedule_sha256": pair.anchor_schedule_sha256,
        "seed": int(pair.seed),
        "step_index": int(pair.step_index),
        "source_manifest_sha256": pair.source_manifest_sha256,
        "checkpoint_sha256": pair.checkpoint_sha256,
        "common_random_field_sha256": pair.common_random_field_sha256,
        "forecast_payload_sha256": pair.forecast_payload_sha256,
        "reference_trace_sha256": pair.reference_trace_sha256,
        "candidate_trace_sha256": pair.candidate_trace_sha256,
        "state_schema": pair.state_schema,
        "state_schema_sha256": pair.state_schema_sha256,
        "state_observation_sha256": pair.state_observation_sha256,
        "focal_user": int(pair.focal_user),
        "state": np.asarray(pair.state).tolist(),
        "action_mask": np.asarray(pair.action_mask).tolist(),
        "reference_action": int(pair.reference_action),
        "candidate_action": int(pair.candidate_action),
        "held_physical_key": [int(pair.held_physical_key[0]), int(pair.held_physical_key[1])],
        "held_key_match_counts": [int(value) for value in pair.held_key_match_counts],
        "release_offset": int(pair.release_offset),
        "release_reason": pair.release_reason,
        "reference_rates_bps": np.asarray(pair.reference_rates_bps).tolist(),
        "candidate_rates_bps": np.asarray(pair.candidate_rates_bps).tolist(),
        "reference_system_power_w": np.asarray(pair.reference_system_power_w).tolist(),
        "candidate_system_power_w": np.asarray(pair.candidate_system_power_w).tolist(),
        "reference_served": np.asarray(pair.reference_served).tolist(),
        "candidate_served": np.asarray(pair.candidate_served).tolist(),
        "lambda_bits_per_j": float(pair.lambda_bits_per_j),
        "interval_s": float(pair.interval_s),
        "offset_surplus_bits": np.asarray(pair.offset_surplus_bits).tolist(),
        "zeta2_temporal_surplus_bits": float(pair.zeta2_temporal_surplus_bits),
        "provenance_sha256": pair.provenance_sha256,
        "comparison_sha256": pair.comparison_sha256,
    }


def _downstream_surplus_from_traces(
    *,
    candidate_rates: np.ndarray,
    reference_rates: np.ndarray,
    candidate_power: np.ndarray,
    reference_power: np.ndarray,
    interval_s: float,
    lambda_bits_per_j: float,
) -> np.ndarray:
    """Use the temporal-pair contract's exact summation order."""

    candidate_rates = np.asarray(candidate_rates, dtype=np.float64)
    reference_rates = np.asarray(reference_rates, dtype=np.float64)
    candidate_power = np.asarray(candidate_power, dtype=np.float64)
    reference_power = np.asarray(reference_power, dtype=np.float64)
    if (
        candidate_rates.ndim != 2
        or candidate_rates.shape != reference_rates.shape
        or candidate_rates.shape[0] != HORIZON
        or candidate_power.shape != (HORIZON,)
        or reference_power.shape != (HORIZON,)
        or not np.all(np.isfinite(candidate_rates))
        or not np.all(np.isfinite(reference_rates))
        or not np.all(np.isfinite(candidate_power))
        or not np.all(np.isfinite(reference_power))
    ):
        raise PhaseBError("temporal traces are malformed before surplus derivation")
    interval = _positive(interval_s, field="interval_s")
    multiplier = _positive(lambda_bits_per_j, field="lambda_bits_per_j")
    delta_rates = candidate_rates - reference_rates
    return np.asarray(
        [
            interval * math.fsum(float(value) for value in delta_rates[offset])
            - multiplier
            * interval
            * float(candidate_power[offset] - reference_power[offset])
            for offset in DOWNSTREAM_OFFSETS
        ],
        dtype=np.float64,
    )


def _materialize_q13_pair(
    *,
    prepared: Any,
    hybrid: Any,
    modules: Mapping[str, Any],
    lambda_bits_per_j: float,
    interval_s: float,
    anchor_schedule_sha256: str,
    source_manifest_sha256: str,
) -> tuple[Any, dict[str, object]]:
    """Run one exact matched Q1+Q3 continuation pair.

    Offset zero is the scheduled Main-vs-candidate opening intervention.
    The frozen Q1+Q3 policy starts at offset one and independently re-decides
    on each branch thereafter.  Thus the pair remains a candidate-vs-Main
    target while its downstream continuation is deployment-context matched.
    """

    backend = modules["backend"]
    pair_smoke = modules["pair_smoke"]
    forecast = pair_smoke.forecast
    anchor = prepared.anchor
    field, field_receipt = backend._derive_fading_field(anchor)
    if field_receipt is None or field is None:
        raise PhaseBError("Phase-B requires keyed common-random fading")
    rngs, initial_rng_receipt = backend._derive_forecast_rngs(
        anchor, fading_field_receipt=field_receipt
    )
    reference = backend._branch_from_anchor(
        anchor,
        role="reference",
        env_rng=rngs["reference_env"],
        mobility_rng=rngs["reference_mobility"],
        fading_field=field,
    )
    candidate = backend._branch_from_anchor(
        anchor,
        role="candidate",
        env_rng=rngs["candidate_env"],
        mobility_rng=rngs["candidate_mobility"],
        fading_field=field,
    )
    reference_trace: list[Any] = []
    candidate_trace: list[Any] = []
    reference_decisions: list[dict[str, object]] = []
    candidate_decisions: list[dict[str, object]] = []
    support_counts: list[int] = []
    holding = True
    release_offset: int | None = None
    release_reason: str | None = None
    focal = int(anchor.focal_user)
    for offset in range(HORIZON):
        if offset == 0:
            ref_actions = np.asarray(anchor.main_actions, dtype=np.int32)
            ref_physical = tuple(anchor.main_physical_actions)
            cand_actions = ref_actions
            cand_physical = ref_physical
        else:
            ref_decision = _select_frozen_q13_continuation(
                hybrid,
                reference.wrapped,
                reference.observation,
                interval_s=interval_s,
                kappa_bits=float(hybrid.v04_config.kappa_bits),
            )
            cand_decision = _select_frozen_q13_continuation(
                hybrid,
                candidate.wrapped,
                candidate.observation,
                interval_s=interval_s,
                kappa_bits=float(hybrid.v04_config.kappa_bits),
            )
            reference_decisions.append(_decision_mapping(ref_decision, offset=offset))
            candidate_decisions.append(_decision_mapping(cand_decision, offset=offset))
            ref_actions = np.asarray(ref_decision.actions, dtype=np.int32)
            cand_actions = np.asarray(cand_decision.actions, dtype=np.int32)
            ref_physical = backend._physical_vector(
                ref_actions.tolist(), reference.observation, users=len(reference.states)
            )
            cand_physical = backend._physical_vector(
                cand_actions.tolist(), candidate.observation, users=len(candidate.states)
            )

        if holding:
            count = backend._candidate_support_count(
                candidate.observation, focal_user=focal, candidate_key=prepared.candidate_key
            )
            support_counts.append(int(count))
            if offset == 0 and count != 1:
                raise backend.C2ForecastSupportRejection(
                    "opening_candidate_unavailable",
                    forecast_offset=offset,
                    user=focal,
                    physical_key=prepared.candidate_key,
                    detail=f"opening candidate must be uniquely executable; observed match count={count}",
                )
            if offset > 0 and count != 1:
                holding = False
                release_offset = offset
                release_reason = "support_expired"
            elif offset == HORIZON - 1:
                holding = False
                release_offset = offset
                release_reason = "horizon"
        else:
            # Once support has expired the latch is never reacquired.  The
            # trace still records the observed count for auditability.
            count = backend._candidate_support_count(
                candidate.observation, focal_user=focal, candidate_key=prepared.candidate_key
            )
            support_counts.append(int(count))
        executed, executed_physical = backend._compose_candidate_actions(
            observation=candidate.observation,
            main_actions=cand_actions,
            main_physical=cand_physical,
            candidate_key=prepared.candidate_key,
            focal_user=focal,
            offset=offset,
            hold=holding,
        )
        reference_trace.append(
            backend._step_payload(
                reference,
                offset=offset,
                detached_main_actions=ref_actions.tolist(),
                detached_main_physical=ref_physical,
                executed_actions=ref_actions.tolist(),
            )
        )
        candidate_trace.append(
            backend._step_payload(
                candidate,
                offset=offset,
                detached_main_actions=cand_actions.tolist(),
                detached_main_physical=cand_physical,
                executed_actions=executed.tolist(),
                held_physical_key=prepared.candidate_key,
                held_key_match_count=int(support_counts[-1]),
                release_offset=release_offset,
                release_reason=release_reason,
            )
        )
    if release_offset is None or release_reason is None:
        raise PhaseBError("Q1+Q3 continuation did not produce one release")
    if len(support_counts) != HORIZON:
        raise PhaseBError("Q1+Q3 continuation support receipt is incomplete")
    # The forecast adapter requires the one release decision to be bound on
    # every candidate row.  The decision is only known after the final
    # downstream table has been observed, so normalize the provisional per-
    # step payloads exactly as the canonical V0.3 backend does.
    candidate_trace = [
        replace(
            payload,
            held_physical_key=prepared.candidate_key,
            held_key_match_count=support_counts[payload.offset],
            release_offset=release_offset,
            release_reason=release_reason,
        )
        for payload in candidate_trace
    ]
    final_rng_receipt = backend._forecast_rng_receipt(
        initial_rng_receipt, (reference, candidate)
    )
    source = forecast.ForecastSourcePayload(
        anchor_payload=anchor.anchor_payload,
        reference_checkpoint_sha256=anchor.checkpoint_sha256,
        environment_source_sha256=anchor.environment_source_sha256,
        reward_source_sha256=anchor.reward_source_sha256,
        live_rng_state=prepared.backend._live_rng_state(),
        forecast_rng_state=final_rng_receipt,
        forecast_namespace=backend.FORECAST_NAMESPACE + "/q13-continuation",
        adapter_version="c2_temporal_fork_trainer_backend-v2/q13-continuation-v1",
        fading_mode=anchor.forecast_fading_mode,
        fading_field_receipt=field_receipt,
        source_rule=prepared.source_rule,
    )
    build = forecast.build_authoritative_forecast(
        source,
        focal_user=focal,
        user_count=len(reference.states),
        pre_active_physical_ids=anchor.pre_active_physical_ids,
        reference_trace=reference_trace,
        candidate_trace=candidate_trace,
        decision_interval_s=interval_s,
    )
    state, mask, state_schema, state_schema_sha, state_obs_sha = _state_and_mask(
        modules=modules,
        wrapped=anchor.wrapped,
        observation=anchor.observation,
        focal_user=focal,
    )
    anchor_state = _anchor_state_record(
        state=state,
        mask=mask,
        state_schema=state_schema,
        state_schema_sha256=state_schema_sha,
        state_observation_sha256=state_obs_sha,
    )
    reference_rates = np.asarray([step.link_rate_bps for step in reference_trace], dtype=np.float64)
    candidate_rates = np.asarray([step.link_rate_bps for step in candidate_trace], dtype=np.float64)
    reference_power = np.asarray([step.system_power_w for step in reference_trace], dtype=np.float64)
    candidate_power = np.asarray([step.system_power_w for step in candidate_trace], dtype=np.float64)
    reference_served = np.asarray([step.served for step in reference_trace], dtype=np.bool_)
    candidate_served = np.asarray([step.served for step in candidate_trace], dtype=np.bool_)
    offsets = _downstream_surplus_from_traces(
        candidate_rates=candidate_rates,
        reference_rates=reference_rates,
        candidate_power=candidate_power,
        reference_power=reference_power,
        interval_s=interval_s,
        lambda_bits_per_j=lambda_bits_per_j,
    )
    pair = _build_temporal_pair(
        c2_policy_version=C2_POLICY_VERSION,
        source_rule=prepared.source_rule,
        anchor_sha256=anchor.anchor_sha256,
        anchor_schedule_sha256=anchor_schedule_sha256,
        seed=int(anchor.evaluation_seed),
        step_index=int(anchor.observation.step_index),
        source_manifest_sha256=source_manifest_sha256,
        checkpoint_sha256=anchor.checkpoint_sha256,
        common_random_field_sha256=str(field.root_digest),
        forecast_payload_sha256=build.forecast_payload_sha256,
        reference_trace_sha256=build.reference_trace_sha256,
        candidate_trace_sha256=build.candidate_trace_sha256,
        state_schema=state_schema,
        state_schema_sha256=state_schema_sha,
        state_observation_sha256=state_obs_sha,
        focal_user=focal,
        state=state,
        action_mask=mask,
        reference_action=int(reference_trace[0].executed_actions[focal]),
        candidate_action=int(candidate_trace[0].executed_actions[focal]),
        held_physical_key=prepared.candidate_key,
        held_key_match_counts=tuple(support_counts),
        release_offset=int(release_offset),
        release_reason=str(release_reason),
        reference_rates_bps=reference_rates,
        candidate_rates_bps=candidate_rates,
        reference_system_power_w=reference_power,
        candidate_system_power_w=candidate_power,
        reference_served=reference_served,
        candidate_served=candidate_served,
        lambda_bits_per_j=float(lambda_bits_per_j),
        interval_s=float(interval_s),
        offset_surplus_bits=offsets,
        zeta2_temporal_surplus_bits=float(math.fsum(float(value) for value in offsets)),
    )
    if not np.array_equal(np.asarray(pair.state, dtype=np.float32), state) or not np.array_equal(
        np.asarray(pair.action_mask), mask
    ):
        raise PhaseBError("temporal pair state is not the sealed focal anchor state")
    if (
        pair.state_schema != state_schema
        or pair.state_schema_sha256 != state_schema_sha
        or pair.state_observation_sha256 != state_obs_sha
    ):
        raise PhaseBError("temporal pair state lineage disagrees with anchor state authority")
    pair.verify()
    raw = {
        "reference": _trace_mapping(reference_trace),
        "candidate": _trace_mapping(candidate_trace),
        "q13_reference_decisions": reference_decisions,
        "q13_candidate_decisions": candidate_decisions,
        "support_counts": [int(value) for value in support_counts],
        "continuation_start_offset": 1,
        "opening_reference_rule": "frozen-main-opening",
        "opening_candidate_rule": "scheduled-physical-sibling",
        "release_offset": int(release_offset),
        "release_reason": str(release_reason),
    }
    certificate = build.certificate
    return pair, {
        "schema": PHASE_B_ROW_SCHEMA,
        "source_route": "C2",
        "continuation": Q13_CONTINUATION,
        "initialization_seed": int(hybrid.initialization_seed),
        "sibling_key": None,
        "anchor_state": anchor_state,
        "pair": _pair_mapping(pair),
        "raw_trace": raw,
        "certificate": {
            "passed": bool(certificate.passed),
            "failures": [str(value.value) for value in certificate.failures],
            "option_id": certificate.option_id,
            "evidence_sha256": certificate.evidence_sha256,
            "forecast_payload_sha256": certificate.forecast_payload_sha256,
            "reference_ee_bits_per_j": float(certificate.reference_ee_bits_per_j),
            "ee_surplus_bits": float(certificate.ee_surplus_bits),
            "hold_r2_margin": float(certificate.hold_r2_margin),
            "full_r2_margin": float(certificate.full_r2_margin),
        },
    }


def _materialize_shard(
    *,
    phase_a: Mapping[str, Any],
    q13_gate: Mapping[str, Any],
    initialization_seed: int,
    v03_root: Path,
    output_dir: Path,
) -> dict[str, object]:
    if initialization_seed not in Q13_INIT_SEEDS:
        raise PhaseBError(f"initialization seed is outside the frozen Q13 set: {initialization_seed}")
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite Phase-B shard: {output_dir}")
    modules = dict(phase_a["modules"])
    # Reuse the exact authenticated C3 hybrid loader; it proves the selected
    # hybrid has three networks, frozen Q1/Q2, and only Q3 at rung 100.
    hybrid = _screen_module().load_gate_selected_hybrid(
        q13_gate,
        v03_root=Path(v03_root),
        initialization_seed=initialization_seed,
    )
    if hybrid.selected_q3_rung != 100 or len(hybrid.q_nets) != 3:
        raise PhaseBError("loaded Q1+Q3 hybrid is not exact rung-100 three-network state")
    for network in hybrid.q_nets:
        network.eval()
    before_hybrid = _snapshot_hybrid(hybrid)
    main_trainer = phase_a["context"]["trainer"] if "context" in phase_a else None
    if main_trainer is None:
        raise PhaseBError("Phase-B production context is missing Main trainer")
    backend_smoke = modules["backend_smoke"]
    main_before = backend_smoke._network_snapshot(main_trainer)
    replay_before = len(main_trainer.replay)
    lambda_bits_per_j, interval_s, _calibration_sha = support._production_calibration(modules)
    context = phase_a["context"]
    prepared = phase_a["prepared"]
    rows_by_key = _phase_a_rows_by_key(phase_a["result"])
    anchors_by_seed: dict[int, tuple[Any, ...]] = {
        seed: tuple(sorted((anchor for anchor in prepared.schedule.anchors if anchor.source_seed == seed), key=lambda value: (value.anchor_step, value.focal_user, value.anchor_sha256)))
        for seed in prepared.selected_source_seeds
    }
    rows: list[dict[str, object]] = []
    started = time.perf_counter()
    for source_seed in prepared.selected_source_seeds:
        for anchor in anchors_by_seed[source_seed]:
            replay = support._replay_main_to_step(
                source_seed=source_seed,
                target_step=anchor.anchor_step,
                modules=modules,
                context=context,
            )
            service = support._real_service_for_sealed_anchor(
                anchor=anchor,
                replay=replay,
                modules=modules,
                context=context,
            )
            for sibling in prepared.schedule.rows:
                if sibling.intervention_key != anchor.intervention_key:
                    continue
                row: dict[str, object] = {
                    "schema": PHASE_B_ROW_SCHEMA,
                    "source_route": "C2",
                    "continuation": Q13_CONTINUATION,
                    "initialization_seed": int(initialization_seed),
                    "sibling_key": [sibling.source_seed, sibling.world_anchor_sha256, sibling.anchor_sha256, sibling.focal_user, list(sibling.candidate_physical_key)],
                    "candidate_action": int(sibling.candidate_action),
                    "candidate_physical_key": list(sibling.candidate_physical_key),
                    "anchor_schedule_sha256": sibling.anchor_schedule_sha256,
                    "anchor_sha256": sibling.anchor_sha256,
                    "common_random_field_sha256": sibling.common_random_field_sha256,
                    "row_status": "ready",
                }
                try:
                    prepared_fork = service.prepare_one_candidate(
                        focal_user=anchor.focal_user,
                        candidate_key=sibling.candidate_physical_key,
                        source_rule=support.C2_V04_SUPPORT_COMPLETE_SOURCE_RULE,
                    )
                    pair, materialized = _materialize_q13_pair(
                        prepared=prepared_fork,
                        hybrid=hybrid,
                        modules=modules,
                        lambda_bits_per_j=lambda_bits_per_j,
                        interval_s=interval_s,
                        anchor_schedule_sha256=sibling.anchor_schedule_sha256,
                        source_manifest_sha256=context["source_manifest_sha256"],
                    )
                    materialized["sibling_key"] = row["sibling_key"]
                    materialized["candidate_action"] = int(sibling.candidate_action)
                    materialized["candidate_physical_key"] = list(sibling.candidate_physical_key)
                    materialized["anchor_schedule_sha256"] = sibling.anchor_schedule_sha256
                    materialized["anchor_sha256"] = sibling.anchor_sha256
                    materialized["common_random_field_sha256"] = sibling.common_random_field_sha256
                    materialized["row_status"] = "ready"
                    for field in (
                        "anchor_sha256",
                        "anchor_schedule_sha256",
                        "source_manifest_sha256",
                        "checkpoint_sha256",
                        "common_random_field_sha256",
                    ):
                        if materialized["pair"].get(field) != getattr(sibling, field):
                            raise PhaseBError(
                                f"Q13 pair {field} disagrees with sealed sibling"
                            )
                    if int(materialized["pair"]["candidate_action"]) != sibling.candidate_action:
                        raise PhaseBError("Q13 pair candidate action disagrees with sealed sibling")
                    if materialized["pair"]["common_random_field_sha256"] != sibling.common_random_field_sha256:
                        raise PhaseBError("Q13 pair common-random field disagrees with sealed sibling")
                    row = materialized
                except Exception as error:
                    row.update(
                        {
                            "row_status": "row-failure",
                            "failure_code": _error_text(error),
                            "pair": None,
                            "raw_trace": None,
                            "certificate": None,
                        }
                    )
                row_body = {key: value for key, value in row.items() if key != "row_sha256"}
                row["row_sha256"] = _canonical_sha256(row_body)
                rows.append(row)
    rows.sort(key=lambda row: _sibling_key(row["sibling_key"]))
    expected = {row.sibling_key for row in prepared.schedule.rows}
    observed = {_sibling_key(row["sibling_key"]) for row in rows}
    if len(rows) != EXPECTED_ROWS_PER_SHARD or observed != expected:
        raise PhaseBError("Phase-B shard did not retain exactly one row per 324 sibling")
    anchor_state_authority = _collect_anchor_state_authority(
        rows,
        prepared.schedule.anchors,
        require_complete=False,
    )
    if not backend_smoke._networks_equal(main_trainer, main_before) or len(main_trainer.replay) != replay_before:
        raise PhaseBError("Phase-B changed Main trainer parameters or replay")
    _assert_hybrid_unchanged(hybrid, before_hybrid)
    code_manifest = _phase_b_code_manifest()
    shard_body = {
        "schema": PHASE_B_SHARD_SCHEMA,
        "claim_ceiling": PHASE_B_CLAIM_CEILING,
        "status": "PHASE_B_SHARD_COMPLETE",
        "continuation": Q13_CONTINUATION,
        "source_rule": support.C2_V04_SUPPORT_COMPLETE_SOURCE_RULE,
        "initialization_seed": int(initialization_seed),
        "selected_q3_rung": 100,
        "phase_a_dir": str(Path(phase_a["dir"]).resolve()),
        "phase_a_result_file_sha256": phase_a["result_file_sha256"],
        "phase_a_sha256": phase_a["result"]["phase_a_sha256"],
        "phase_a_seal_file_sha256": phase_a["seal_file_sha256"],
        "prepare_sha256": phase_a["prepare_sha256"],
        "schedule_sha256": phase_a["schedule_sha256"],
        "q13_gate_authority_sha256": q13_gate["authority_sha256"],
        "q13_gate_result_file_sha256": q13_gate["result_file_sha256"],
        "q13_gate_source_manifest_sha256": q13_gate["source_manifest_sha256"],
        "q13_gate_schedule_sha256": q13_gate["schedule_sha256"],
        "q13_hybrid_file_sha256": q13_gate["selected_hybrid_file_sha256"][str(initialization_seed)],
        "code_manifest": code_manifest,
        "lambda_bits_per_j": float(lambda_bits_per_j),
        "interval_s": float(interval_s),
        "row_count": len(rows),
        "expected_row_count": EXPECTED_ROWS_PER_SHARD,
        "anchor_state_authority": anchor_state_authority,
        "rows": rows,
        "elapsed_s": time.perf_counter() - started,
        "training_run": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    shard_body["shard_sha256"] = _canonical_sha256(shard_body)
    output_dir.mkdir(parents=True)
    file_sha = _write_once(output_dir / "shard-result.json", shard_body)
    seal = {
        "schema": PHASE_B_SHARD_SEAL_SCHEMA,
        "status": "PHASE_B_SHARD_COMPLETE",
        "shard_sha256": shard_body["shard_sha256"],
        "shard_result_file_sha256": file_sha,
        "initialization_seed": int(initialization_seed),
        "phase_a_result_file_sha256": phase_a["result_file_sha256"],
        "phase_a_sha256": phase_a["result"]["phase_a_sha256"],
        "q13_gate_authority_sha256": q13_gate["authority_sha256"],
        "q13_hybrid_file_sha256": q13_gate["selected_hybrid_file_sha256"][str(initialization_seed)],
        "row_count": EXPECTED_ROWS_PER_SHARD,
        "training_run": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    seal_file_sha = _write_once(output_dir / "shard-seal.json", seal)
    return {
        "status": "PHASE_B_SHARD_COMPLETE",
        "initialization_seed": int(initialization_seed),
        "row_count": EXPECTED_ROWS_PER_SHARD,
        "shard_sha256": shard_body["shard_sha256"],
        "shard_result_file_sha256": file_sha,
        "shard_seal_file_sha256": seal_file_sha,
        "elapsed_s": shard_body["elapsed_s"],
        "training_run": False,
        "test_split_opened": False,
    }


def _snapshot_hybrid(trainer: Any) -> dict[str, Any]:
    q_nets = getattr(trainer, "q_nets", None)
    if q_nets is None or len(q_nets) != 3:
        raise PhaseBError("hybrid must expose exactly three Q networks")
    optimizer = getattr(trainer, "q3_optimizer", None)
    if optimizer is None:
        raise PhaseBError("hybrid lacks Q3 optimizer boundary")
    return {
        "q_networks": [
            {str(name): value.detach().cpu().clone() for name, value in network.state_dict().items()}
            for network in q_nets
        ],
        "optimizer": copy.deepcopy(optimizer.state_dict()),
        "q3_update_count": trainer.q3_update_count,
        "training_flags": [bool(network.training) for network in q_nets],
    }


def _state_equal(left: Any, right: Any) -> bool:
    if hasattr(left, "shape") and hasattr(right, "shape"):
        try:
            return bool(np.array_equal(left, right))
        except Exception:
            pass
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(_state_equal(left[k], right[k]) for k in left)
    if isinstance(left, (tuple, list)) and isinstance(right, (tuple, list)):
        return type(left) is type(right) and len(left) == len(right) and all(_state_equal(a, b) for a, b in zip(left, right, strict=True))
    return left == right


def _assert_hybrid_unchanged(trainer: Any, before: Mapping[str, Any]) -> None:
    after = _snapshot_hybrid(trainer)
    for field in before:
        if not _state_equal(after[field], before[field]):
            raise PhaseBError(f"Q1+Q3 hybrid changed during Phase-B replay: {field}")


def _collect_anchor_state_authority(
    rows: Sequence[Mapping[str, Any]],
    anchors: Sequence[Any],
    *,
    require_complete: bool,
) -> dict[str, dict[str, object]]:
    """Collapse and cross-check the duplicated focal state per intervention.

    The Phase-A receipt deliberately has no learner-state payload.  A Phase-B
    shard therefore carries the verified temporal-pair state on each ready
    row.  This function turns those copies into one cluster-level join record
    and rejects contradictory states before P0/P1/P2 can consume them.
    """

    expected_by_key = {
        anchor.intervention_key: anchor for anchor in anchors
    }
    rows_by_key: dict[tuple[int, str, str, int], list[Mapping[str, Any]]] = {
        key: [] for key in expected_by_key
    }
    for row in rows:
        key = _intervention_key(_sibling_key(row.get("sibling_key")))
        rows_by_key.setdefault(key, []).append(row)
    output: dict[str, dict[str, object]] = {}
    for key, anchor in expected_by_key.items():
        cluster_rows = rows_by_key.get(key, [])
        ready = [
            row
            for row in cluster_rows
            if row.get("row_status") == "ready" and row.get("anchor_state") is not None
        ]
        records: list[dict[str, object]] = []
        for index, row in enumerate(ready):
            records.append(
                _validate_anchor_state_record(
                    row.get("anchor_state"),
                    field=f"anchor_state[{_cluster_key_text(key)}][{index}]",
                )
            )
        digests = {str(record["anchor_state_sha256"]) for record in records}
        complete = len(cluster_rows) == support.SIBLINGS_PER_CLUSTER and len(ready) == support.SIBLINGS_PER_CLUSTER
        if len(digests) > 1:
            raise PhaseBError(
                f"contradictory 228-D anchor states in cluster {_cluster_key_text(key)}"
            )
        if require_complete and not complete:
            raise PhaseBError(
                f"cluster {_cluster_key_text(key)} lacks a complete Phase-B anchor-state authority"
            )
        state = records[0] if records else None
        output[_cluster_key_text(key)] = {
            "schema": "multi-catfish-mcrl-v04-c2-anchor-state-authority-v1",
            "intervention_key": list(key),
            "source_seed": int(anchor.source_seed),
            "anchor_sha256": anchor.anchor_sha256,
            "focal_user": int(anchor.focal_user),
            "phase_a_join": {
                "anchor_sha256": anchor.anchor_sha256,
                "anchor_schedule_sha256": anchor.anchor_schedule_sha256,
                "target_source": "phase-a-main-continuation-zeta2",
            },
            "status": "COMPLETE" if complete and state is not None else "INCOMPLETE",
            "row_count": len(cluster_rows),
            "ready_row_count": len(ready),
            "anchor_state": state,
        }
    return output


def _merge_anchor_state_authority(
    authorities: Mapping[int, Mapping[str, Mapping[str, object]]],
    anchors: Sequence[Any],
) -> dict[str, dict[str, object]]:
    """Authenticate one identical anchor state across all three shards."""

    output: dict[str, dict[str, object]] = {}
    for anchor in anchors:
        key = anchor.intervention_key
        key_text = _cluster_key_text(key)
        per_init: dict[str, object] = {}
        records: list[Mapping[str, object]] = []
        complete = True
        for seed in Q13_INIT_SEEDS:
            entry = authorities[seed].get(key_text)
            if not isinstance(entry, Mapping):
                raise PhaseBError(f"missing anchor-state authority for {key_text} / {seed}")
            per_init[str(seed)] = {
                "status": entry.get("status"),
                "row_count": entry.get("row_count"),
                "ready_row_count": entry.get("ready_row_count"),
                "anchor_state_sha256": (
                    entry.get("anchor_state", {}).get("anchor_state_sha256")
                    if isinstance(entry.get("anchor_state"), Mapping)
                    else None
                ),
            }
            if entry.get("status") != "COMPLETE" or not isinstance(entry.get("anchor_state"), Mapping):
                complete = False
            else:
                records.append(entry["anchor_state"])
        digests = {str(record.get("anchor_state_sha256")) for record in records}
        if len(digests) > 1:
            raise PhaseBError(f"cross-initialization anchor state drifted for {key_text}")
        state = dict(records[0]) if records else None
        if state is not None:
            state = _validate_anchor_state_record(state, field=f"merged_anchor_state[{key_text}]")
        output[key_text] = {
            "schema": "multi-catfish-mcrl-v04-c2-anchor-state-merge-v1",
            "intervention_key": list(key),
            "source_seed": int(anchor.source_seed),
            "anchor_sha256": anchor.anchor_sha256,
            "focal_user": int(anchor.focal_user),
            "phase_a_join": {
                "anchor_sha256": anchor.anchor_sha256,
                "anchor_schedule_sha256": anchor.anchor_schedule_sha256,
                "target_source": "phase-a-main-continuation-zeta2",
                "phase_a_state_reconstructed_in": "phase-b-q13-shards",
            },
            "status": "COMPLETE" if complete and state is not None else "INCOMPLETE",
            "initializations": per_init,
            "anchor_state": state,
        }
    return output


# Gate and deterministic merge layer --------------------------------------

def _rank(values: Sequence[float]) -> tuple[float, ...]:
    ordered = sorted((float(value), index) for index, value in enumerate(values))
    output = [0.0] * len(values)
    position = 0
    while position < len(ordered):
        end = position + 1
        while end < len(ordered) and ordered[end][0] == ordered[position][0]:
            end += 1
        average = (position + 1 + end) / 2.0
        for _, index in ordered[position:end]:
            output[index] = average
        position = end
    return tuple(output)


def _spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    a = np.asarray(_rank(left), dtype=np.float64)
    b = np.asarray(_rank(right), dtype=np.float64)
    a -= float(np.mean(a))
    b -= float(np.mean(b))
    denom = float(np.sqrt(np.sum(a * a) * np.sum(b * b)))
    if denom == 0.0:
        return None
    return float(np.sum(a * b) / denom)


def _row_metrics(row: Mapping[str, Any]) -> tuple[float | None, float | None, int | None]:
    pair = row.get("pair")
    if not isinstance(pair, Mapping):
        return None, None, None
    target = pair.get("zeta2_temporal_surplus_bits")
    delivered = None
    try:
        candidate = _float_matrix(pair.get("candidate_rates_bps"), field="pair.candidate_rates_bps")
        reference = _float_matrix(pair.get("reference_rates_bps"), field="pair.reference_rates_bps")
        interval = _positive(pair.get("interval_s"), field="pair.interval_s")
        delivered = interval * float(np.sum(candidate[1:] - reference[1:], dtype=np.float64))
    except PhaseBError:
        delivered = None
    try:
        normalized = _finite(target, field="pair.zeta2") / float(support.KAPPA_BITS)
    except PhaseBError:
        normalized = None
    release = row.get("pair", {}).get("release_offset") if isinstance(row.get("pair"), Mapping) else None
    release_value = int(release) if type(release) is int else None
    # Incumbency is a property of the sealed anchor schedule, not of the
    # pair's held key (which is intentionally equal to every row's candidate
    # key).  The caller receives the anchor and performs that comparison.
    return normalized, delivered, release_value


def _cluster_key_text(key: tuple[int, str, str, int]) -> str:
    """Stable JSON text for a structured intervention key."""

    return json.dumps(list(key), separators=(",", ":"), ensure_ascii=True)


def _physical_gate(rows: Sequence[Mapping[str, Any]], anchors: Sequence[Any]) -> dict[str, object]:
    anchors_by_key = {anchor.intervention_key: anchor for anchor in anchors}
    by_cluster: dict[tuple[int, str, str, int], list[Mapping[str, Any]]] = {
        anchor.intervention_key: [] for anchor in anchors
    }
    for row in rows:
        key = _intervention_key(_sibling_key(row.get("sibling_key")))
        by_cluster.setdefault(key, []).append(row)
    all_metrics: dict[tuple[int, str, str, int], list[tuple[float | None, float | None, int | None]]] = {}
    non_metrics: dict[tuple[int, str, str, int], list[tuple[float | None, float | None, int | None]]] = {}
    missing: list[tuple[tuple[int, str, str, int], Mapping[str, Any]]] = []
    for key, cluster_rows in by_cluster.items():
        all_metrics[key] = []
        non_metrics[key] = []
        anchor = anchors_by_key.get(key)
        for row in cluster_rows:
            metrics = _row_metrics(row)
            all_metrics[key].append(metrics)
            if any(value is None for value in metrics):
                missing.append((key, row))
            if anchor is not None and tuple(_physical(row.get("candidate_physical_key"), field="candidate_physical_key")) != tuple(anchor.incumbent_physical_key):
                non_metrics[key].append(metrics)
    non_incumbent = [item for values in non_metrics.values() for item in values]
    valid = [item for item in non_incumbent if item[0] is not None and item[1] is not None and item[2] is not None]
    release_good = [item for item in valid if int(item[2]) >= 2]
    world_fraction: dict[str, float] = {}
    for seed in sorted({anchor.source_seed for anchor in anchors}):
        world = [item for key, values in non_metrics.items() if key[0] == seed for item in values]
        world_fraction[str(seed)] = (
            sum(int(item[2] is not None and item[2] >= 2) for item in world)
            / len(world)
            if world
            else 0.0
        )
    cluster_iqrs: dict[str, float | None] = {}
    cluster_pass: dict[str, bool] = {}
    for key, values in all_metrics.items():
        targets = sorted(float(item[0]) for item in values if item[0] is not None)
        if len(targets) != support.SIBLINGS_PER_CLUSTER:
            cluster_iqrs[_cluster_key_text(key)] = None
            cluster_pass[_cluster_key_text(key)] = False
        else:
            q1 = float(np.percentile(targets, 25))
            q3 = float(np.percentile(targets, 75))
            cluster_iqrs[_cluster_key_text(key)] = q3 - q1
            cluster_pass[_cluster_key_text(key)] = (q3 - q1) >= 0.5
    top3: dict[str, bool] = {}
    for key, values in all_metrics.items():
        ranked = sorted((item for item in values if item[0] is not None and item[1] is not None), key=lambda item: -float(item[0]))[:3]
        top3[_cluster_key_text(key)] = len(ranked) == 3 and any(float(item[1]) >= 0.0 for item in ranked)
    world_top3 = {
        str(seed): sum(value for key, value in top3.items() if json.loads(key)[0] == seed)
        for seed in sorted({anchor.source_seed for anchor in anchors})
    }
    expected_non_incumbent = sum(
        support.SIBLINGS_PER_CLUSTER
        - int(anchor.incumbent_physical_key in anchor.candidate_physical_keys)
        for anchor in anchors
    )
    passed = bool(
        not missing
        and len(non_incumbent) == expected_non_incumbent
        and len(release_good) / len(non_incumbent) >= 0.70
        and all(value >= 0.60 for value in world_fraction.values())
        and valid
        and statistics.median(abs(float(item[0])) for item in valid) >= 0.5
        and sum(cluster_pass.values()) >= 9
        and sum(value >= 3 for value in world_top3.values()) >= 2
    )
    return {
        "passed": passed,
        "row_count": len(rows),
        "missing_outcome_count": len(missing),
        "non_incumbent_count": len(non_incumbent),
        "pooled_release_ge_2_fraction": len(release_good) / len(non_incumbent) if non_incumbent else 0.0,
        "world_release_ge_2_fraction": world_fraction,
        "pooled_median_abs_normalized_zeta2": statistics.median(abs(float(item[0])) for item in valid) if valid else None,
        "cluster_target_iqr": cluster_iqrs,
        "clusters_iqr_ge_0p5": sum(cluster_pass.values()),
        "clusters_top3_with_nonnegative_delivered_delta": top3,
        "world_cluster_pass_counts": world_top3,
        "worlds_with_at_least_three_passing_clusters": sum(value >= 3 for value in world_top3.values()),
    }


def _main_target_map(phase_a_result: Mapping[str, Any], *, key: tuple[int, str, str, int]) -> dict[int, float]:
    anchors = phase_a_result.get("rows", [])
    target: dict[int, float] = {}
    for row in anchors:
        if not isinstance(row, Mapping):
            continue
        sibling = _sibling_key(row.get("sibling_key"))
        if _intervention_key(sibling) != key:
            continue
        if row.get("zeta2_temporal_surplus_bits") is not None:
            target[int(row["candidate_action"])] = _finite(row["zeta2_temporal_surplus_bits"], field="Phase-A target") / float(support.KAPPA_BITS)
    anchor = next((item for item in phase_a_result.get("_anchors", ()) if item.intervention_key == key), None)
    if anchor is not None:
        target[int(anchor.reference_action)] = 0.0
    return target


def _q13_target_map(rows: Sequence[Mapping[str, Any]], *, key: tuple[int, str, str, int]) -> dict[int, float]:
    output: dict[int, float] = {}
    for row in rows:
        sibling = _sibling_key(row.get("sibling_key"))
        if _intervention_key(sibling) == key:
            target, _delivered, _release = _row_metrics(row)
            if target is not None:
                output[int(row["candidate_action"])] = float(target)
    return output


def _gc_gate(
    phase_a_result: Mapping[str, Any],
    shards: Mapping[int, Sequence[Mapping[str, Any]]],
    anchors: Sequence[Any],
) -> dict[str, object]:
    phase_a_result = dict(phase_a_result)
    phase_a_result["_anchors"] = tuple(anchors)
    per_init: dict[str, dict[str, object]] = {}
    for seed in Q13_INIT_SEEDS:
        rows = shards[seed]
        per_cluster: dict[str, float | None] = {}
        for anchor in anchors:
            key = anchor.intervention_key
            main_targets = _main_target_map(phase_a_result, key=key)
            q13_targets = _q13_target_map(rows, key=key)
            # The 27 stored rows are non-Main siblings.  The shared reference
            # action is the preregistered zero anchor and must be added before
            # the 28-action ranking comparison.
            q13_targets[int(anchor.reference_action)] = 0.0
            actions = tuple(range(NUM_ACTIONS))
            if set(main_targets) != set(actions) or set(q13_targets) != set(actions):
                per_cluster[str(key)] = None
            else:
                per_cluster[str(key)] = _spearman(
                    [main_targets[action] for action in actions],
                    [q13_targets[action] for action in actions],
                )
        observed = [value for value in per_cluster.values() if value is not None]
        passed_count = sum(value is not None and value >= GC_CORRELATION_THRESHOLD for value in per_cluster.values())
        per_init[str(seed)] = {
            "median_cluster_spearman": statistics.median(observed) if observed else None,
            "clusters_spearman_ge_0p6": passed_count,
            "cluster_spearman": per_cluster,
            "passed": bool(observed and statistics.median(observed) >= GC_CORRELATION_THRESHOLD and passed_count >= 8),
        }
    passing = [seed for seed in Q13_INIT_SEEDS if per_init[str(seed)]["passed"]]
    per_world: dict[str, dict[str, object]] = {}
    for source_seed in sorted({anchor.source_seed for anchor in anchors}):
        values = []
        for seed in passing:
            clusters = [
                value
                for anchor in anchors
                if anchor.source_seed == source_seed
                for value in [per_init[str(seed)]["cluster_spearman"].get(str(anchor.intervention_key))]
                if value is not None
            ]
            if clusters:
                values.append(float(statistics.median(clusters)))
        per_world[str(source_seed)] = {
            "passing_initializations": len(values),
            "median_over_passing_initializations": statistics.median(values) if values else None,
            "passed": bool(values and statistics.median(values) >= GC_CORRELATION_THRESHOLD),
        }
    passed_worlds = sum(value["passed"] for value in per_world.values())
    return {
        "passed": bool(len(passing) >= 2 and passed_worlds >= 2),
        "threshold": GC_CORRELATION_THRESHOLD,
        "passing_initializations": passing,
        "initialization": per_init,
        "world": per_world,
        "worlds_passing": passed_worlds,
    }


def _sensitivity_gc(
    phase_a_result: Mapping[str, Any],
    shards: Mapping[int, Sequence[Mapping[str, Any]]],
    anchors: Sequence[Any],
) -> dict[str, object]:
    phase_a_result = dict(phase_a_result)
    phase_a_result["_anchors"] = tuple(anchors)
    output: dict[str, dict[str, float | None]] = {}
    for seed in Q13_INIT_SEEDS:
        by_cluster: dict[str, float | None] = {}
        for anchor in anchors:
            key = anchor.intervention_key
            main: dict[int, float] = {}
            for row in phase_a_result["rows"]:
                if not isinstance(row, Mapping):
                    continue
                parsed = _sibling_key(row.get("sibling_key"))
                if _intervention_key(parsed) == key and row.get("raw_trace"):
                    trace = row["raw_trace"]
                    if isinstance(trace, Mapping):
                        rates_c = _float_matrix(trace.get("candidate_rates_bps"), field="Phase-A candidate rates")
                        rates_r = _float_matrix(trace.get("reference_rates_bps"), field="Phase-A reference rates")
                        power_c = np.asarray(trace.get("candidate_system_power_w"), dtype=np.float64)
                        power_r = np.asarray(trace.get("reference_system_power_w"), dtype=np.float64)
                        interval = _positive(trace.get("interval_s"), field="Phase-A interval")
                        main[int(row["candidate_action"])] = interval * float(np.sum(rates_c[1:] - rates_r[1:], dtype=np.float64)) - ALTERNATE_LAMBDA_BITS_PER_J * interval * float(np.sum(power_c[1:] - power_r[1:]))
            main[int(anchor.reference_action)] = 0.0
            q13: dict[int, float] = {}
            for row in shards[seed]:
                parsed = _sibling_key(row.get("sibling_key"))
                if _intervention_key(parsed) == key:
                    pair = row.get("pair")
                    if isinstance(pair, Mapping):
                        rates_c = _float_matrix(pair.get("candidate_rates_bps"), field="Q13 candidate rates")
                        rates_r = _float_matrix(pair.get("reference_rates_bps"), field="Q13 reference rates")
                        power_c = np.asarray(pair.get("candidate_system_power_w"), dtype=np.float64)
                        power_r = np.asarray(pair.get("reference_system_power_w"), dtype=np.float64)
                        interval = _positive(pair.get("interval_s"), field="Q13 interval")
                        q13[int(row["candidate_action"])] = interval * float(np.sum(rates_c[1:] - rates_r[1:], dtype=np.float64)) - ALTERNATE_LAMBDA_BITS_PER_J * interval * float(np.sum(power_c[1:] - power_r[1:]))
            q13[int(anchor.reference_action)] = 0.0
            actions = tuple(range(NUM_ACTIONS))
            by_cluster[str(key)] = _spearman([main[a] for a in actions], [q13[a] for a in actions]) if set(main) == set(actions) and set(q13) == set(actions) else None
        output[str(seed)] = by_cluster
    return {"lambda_bits_per_j": ALTERNATE_LAMBDA_BITS_PER_J, "per_initialization_cluster_spearman": output}


def _eligible_arms(*, gc_passed: bool, q13_physical_pass_count: int) -> tuple[str, ...]:
    """Apply the preregistered arm-specific Phase-B authorization boundary."""

    if type(gc_passed) is not bool:
        raise PhaseBError("G-C disposition must be exactly Boolean")
    if (
        type(q13_physical_pass_count) is not int
        or q13_physical_pass_count < 0
        or q13_physical_pass_count > len(Q13_INIT_SEEDS)
    ):
        raise PhaseBError("Q13 physical pass count is outside the frozen initialization set")
    eligible: list[str] = []
    if gc_passed:
        eligible.append(C2_P0_MAIN_VALUE)
    if q13_physical_pass_count >= 2:
        eligible.extend((C2_P1_Q13_VALUE, C2_P2_Q13_HUBER))
    return tuple(eligible)


def _authenticate_shard(
    path: Path,
    *,
    phase_a: Mapping[str, Any],
    q13_gate: Mapping[str, Any],
) -> tuple[int, dict[str, Any], str, str]:
    root = Path(path)
    result, result_file_sha = _read_json(root / "shard-result.json")
    seal, seal_file_sha = _read_json(root / "shard-seal.json")
    seed = result.get("initialization_seed")
    if type(seed) is not int or seed not in Q13_INIT_SEEDS:
        raise PhaseBError(f"shard seed is outside the frozen set: {seed!r}")
    if (
        result.get("schema") != PHASE_B_SHARD_SCHEMA
        or result.get("status") != "PHASE_B_SHARD_COMPLETE"
        or result.get("claim_ceiling") != PHASE_B_CLAIM_CEILING
        or result.get("row_count") != EXPECTED_ROWS_PER_SHARD
        or result.get("expected_row_count") != EXPECTED_ROWS_PER_SHARD
        or result.get("phase_a_result_file_sha256") != phase_a["result_file_sha256"]
        or result.get("phase_a_sha256") != phase_a["result"]["phase_a_sha256"]
        or result.get("prepare_sha256") != phase_a["prepare_sha256"]
        or result.get("schedule_sha256") != phase_a["schedule_sha256"]
        or result.get("q13_gate_authority_sha256") != q13_gate["authority_sha256"]
        or result.get("q13_gate_result_file_sha256") != q13_gate["result_file_sha256"]
        or result.get("q13_hybrid_file_sha256") != q13_gate["selected_hybrid_file_sha256"][str(seed)]
        or result.get("training_run") is not False
        or result.get("test_split_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
    ):
        raise PhaseBError(f"shard authority mismatch for initialization {seed}")
    body = dict(result)
    shard_sha = _digest(body.pop("shard_sha256", None), field="shard_sha256")
    if shard_sha != _canonical_sha256(body):
        raise PhaseBError(f"shard digest mismatch for initialization {seed}")
    rows = result.get("rows")
    if not isinstance(rows, list) or len(rows) != EXPECTED_ROWS_PER_SHARD:
        raise PhaseBError(f"shard row count mismatch for initialization {seed}")
    expected = {row.sibling_key for row in phase_a["prepared"].schedule.rows}
    observed = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise PhaseBError(f"shard row is malformed for initialization {seed}")
        key = _sibling_key(row.get("sibling_key"))
        if key in observed or key not in expected:
            raise PhaseBError(f"shard row identity mismatch for initialization {seed}")
        observed.add(key)
        row_body = {key_name: value for key_name, value in row.items() if key_name != "row_sha256"}
        if _digest(row.get("row_sha256"), field="row_sha256") != _canonical_sha256(row_body):
            raise PhaseBError(f"shard row digest mismatch for initialization {seed}")
    if observed != expected:
        raise PhaseBError(f"shard row identity set incomplete for initialization {seed}")
    # A ready target is admissible only with a verified temporal-pair state
    # and the duplicated cluster-level anchor-state record.  Failure rows are
    # retained for the physical gate and may not be turned into zero targets.
    for index, row in enumerate(rows):
        if row.get("row_status") != "ready":
            if row.get("pair") is not None or row.get("raw_trace") is not None:
                raise PhaseBError(f"failure row retains an unverified target for initialization {seed}")
            continue
        pair = row.get("pair")
        state_record = _validate_anchor_state_record(
            row.get("anchor_state"),
            field=f"shard[{seed}].rows[{index}].anchor_state",
        )
        if not isinstance(pair, Mapping):
            raise PhaseBError(f"ready row lacks its temporal pair for initialization {seed}")
        pair_state = np.asarray(pair.get("state"), dtype=np.float32)
        pair_mask = np.asarray(pair.get("action_mask"))
        state = np.asarray(state_record["state"], dtype=np.float32)
        mask = np.asarray(state_record["action_mask"])
        if not np.array_equal(pair_state, state) or pair_mask.dtype != np.bool_ or not np.array_equal(pair_mask, mask):
            raise PhaseBError(f"ready row pair state disagrees with anchor state for initialization {seed}")
        if (
            pair.get("state_schema") != state_record["state_schema"]
            or pair.get("state_schema_sha256") != state_record["state_schema_sha256"]
            or pair.get("state_observation_sha256") != state_record["state_observation_sha256"]
        ):
            raise PhaseBError(f"ready row state lineage disagrees with anchor state for initialization {seed}")
    computed_state_authority = _collect_anchor_state_authority(
        rows,
        phase_a["prepared"].schedule.anchors,
        require_complete=False,
    )
    if result.get("anchor_state_authority") != computed_state_authority:
        raise PhaseBError(f"anchor-state authority mismatch for initialization {seed}")
    if (
        seal.get("schema") != PHASE_B_SHARD_SEAL_SCHEMA
        or seal.get("status") != "PHASE_B_SHARD_COMPLETE"
        or seal.get("shard_sha256") != shard_sha
        or seal.get("shard_result_file_sha256") != result_file_sha
        or seal.get("initialization_seed") != seed
        or seal.get("phase_a_result_file_sha256") != phase_a["result_file_sha256"]
        or seal.get("q13_gate_authority_sha256") != q13_gate["authority_sha256"]
        or seal.get("q13_hybrid_file_sha256") != q13_gate["selected_hybrid_file_sha256"][str(seed)]
        or seal.get("row_count") != EXPECTED_ROWS_PER_SHARD
        or seal.get("training_run") is not False
        or seal.get("test_split_opened") is not False
        or seal.get("held_out_ee_evaluated") is not False
    ):
        raise PhaseBError(f"shard seal mismatch for initialization {seed}")
    return int(seed), result, result_file_sha, seal_file_sha


def _merge_shards(
    *,
    phase_a: Mapping[str, Any],
    q13_gate: Mapping[str, Any],
    shard_root: Path,
    output_dir: Path,
) -> dict[str, object]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite Phase-B result: {output_dir}")
    shards: dict[int, dict[str, Any]] = {}
    shard_receipts: dict[str, dict[str, str]] = {}
    for seed in Q13_INIT_SEEDS:
        shard_dir = Path(shard_root) / f"init-{seed}"
        parsed_seed, result, result_sha, seal_sha = _authenticate_shard(
            shard_dir, phase_a=phase_a, q13_gate=q13_gate
        )
        if parsed_seed != seed:
            raise PhaseBError("shard directory and sealed initialization disagree")
        shards[seed] = result
        shard_receipts[str(seed)] = {
            "path": str(shard_dir.resolve()),
            "result_file_sha256": result_sha,
            "seal_file_sha256": seal_sha,
            "shard_sha256": str(result["shard_sha256"]),
            "code_manifest_sha256": str(
                result.get("code_manifest", {}).get("code_manifest_sha256")
            ),
        }
    rows_by_init = {seed: tuple(shards[seed]["rows"]) for seed in Q13_INIT_SEEDS}
    anchors = phase_a["prepared"].schedule.anchors
    state_authority_by_init = {
        seed: _collect_anchor_state_authority(
            rows_by_init[seed],
            anchors,
            require_complete=False,
        )
        for seed in Q13_INIT_SEEDS
    }
    anchor_state_authority = _merge_anchor_state_authority(
        state_authority_by_init,
        anchors,
    )
    gc = _gc_gate(phase_a["result"], rows_by_init, anchors)
    physical = {str(seed): _physical_gate(rows_by_init[seed], anchors) for seed in Q13_INIT_SEEDS}
    physical_pass = [seed for seed in Q13_INIT_SEEDS if physical[str(seed)]["passed"] is True]
    eligible_arms = _eligible_arms(
        gc_passed=gc["passed"] is True,
        q13_physical_pass_count=len(physical_pass),
    )
    sensitivity = _sensitivity_gc(phase_a["result"], rows_by_init, anchors)
    merge_code_manifest = _phase_b_code_manifest()
    result_body: dict[str, object] = {
        "schema": PHASE_B_SCHEMA,
        "claim_ceiling": PHASE_B_CLAIM_CEILING,
        "status": "PHASE_B_COMPLETE",
        "continuation": Q13_CONTINUATION,
        "source_rule": support.C2_V04_SUPPORT_COMPLETE_SOURCE_RULE,
        "phase_a_dir": str(Path(phase_a["dir"]).resolve()),
        "phase_a_result_file_sha256": phase_a["result_file_sha256"],
        "phase_a_sha256": phase_a["result"]["phase_a_sha256"],
        "phase_a_seal_file_sha256": phase_a["seal_file_sha256"],
        "prepare_sha256": phase_a["prepare_sha256"],
        "schedule_sha256": phase_a["schedule_sha256"],
        "q13_gate_dir": str(Path(q13_gate["gate_dir"]).resolve()),
        "q13_gate_authority_sha256": q13_gate["authority_sha256"],
        "q13_gate_result_file_sha256": q13_gate["result_file_sha256"],
        "q13_gate_source_manifest_sha256": q13_gate["source_manifest_sha256"],
        "q13_gate_schedule_sha256": q13_gate["schedule_sha256"],
        "q13_hybrid_file_sha256": q13_gate["selected_hybrid_file_sha256"],
        "code_manifest": merge_code_manifest,
        "shards": shard_receipts,
        "row_count": EXPECTED_TOTAL_ROWS,
        "expected_row_count": EXPECTED_TOTAL_ROWS,
        "initialization_seeds": list(Q13_INIT_SEEDS),
        "anchor_state_authority": anchor_state_authority,
        "gates": {
            "G-C": gc,
            "Q13-PHYSICAL": physical,
            "Q13_PHYSICAL_AUTHORIZED_INITIALIZATIONS": physical_pass,
            "Q13_PHYSICAL_AUTHORIZED": len(physical_pass) >= 2,
        },
        "eligible_arms": list(eligible_arms),
        "diagnostics": {"alternate_lambda_g_c": sensitivity},
        "decision": PHASE_B_DECISION if eligible_arms else PHASE_B_REDESIGN,
        "training_run": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    result_body["phase_b_sha256"] = _canonical_sha256(result_body)
    output_dir.mkdir(parents=True)
    result_sha = _write_once(output_dir / "phase-b-result.json", result_body)
    seal = {
        "schema": PHASE_B_SEAL_SCHEMA,
        "status": "PHASE_B_COMPLETE",
        "phase_b_sha256": result_body["phase_b_sha256"],
        "phase_b_result_file_sha256": result_sha,
        "phase_a_result_file_sha256": phase_a["result_file_sha256"],
        "phase_a_sha256": phase_a["result"]["phase_a_sha256"],
        "q13_gate_authority_sha256": q13_gate["authority_sha256"],
        "row_count": EXPECTED_TOTAL_ROWS,
        "initialization_seeds": list(Q13_INIT_SEEDS),
        "eligible_arms": list(eligible_arms),
        "code_manifest_sha256": merge_code_manifest["code_manifest_sha256"],
        "decision": result_body["decision"],
        "training_run": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    seal_sha = _write_once(output_dir / "phase-b-seal.json", seal)
    return {
        "status": "PHASE_B_COMPLETE",
        "decision": result_body["decision"],
        "row_count": EXPECTED_TOTAL_ROWS,
        "phase_b_sha256": result_body["phase_b_sha256"],
        "phase_b_result_file_sha256": result_sha,
        "phase_b_seal_file_sha256": seal_sha,
        "physical_authorized_initializations": physical_pass,
        "eligible_arms": list(eligible_arms),
        "training_run": False,
        "test_split_opened": False,
    }


def _run_shard_command(args: argparse.Namespace) -> dict[str, object]:
    phase_a = _authenticate_phase_a(Path(args.phase_a_dir), prereg_path=Path(args.prereg))
    q13_gate = _authenticate_q13_gate(
        Path(args.gate_dir),
        source_dir=Path(args.c3_source_dir),
        prereg_path=Path(args.prereg),
        v03_root=Path(args.v03_root),
    )
    modules = phase_a["modules"]
    # The frozen TLE archive must remain live for the complete shard; do not
    # return a context whose temporary archive has already been deleted.
    with tempfile.TemporaryDirectory(prefix="mcrl-v04-c2-phase-b-tle-") as temporary:
        context = support._production_main_context(
            modules=modules,
            prereg_path=Path(args.prereg),
            tle_root=Path(args.tle_root),
            temporary=Path(temporary),
        )
        # _production_main_context creates its own archive; use that exact
        # context archive, whose temporary directory is still alive.
        phase_a = dict(phase_a)
        phase_a["context"] = context
        result = _materialize_shard(
            phase_a=phase_a,
            q13_gate=q13_gate,
            initialization_seed=int(args.initialization_seed),
            v03_root=Path(args.v03_root),
            output_dir=Path(args.output_dir),
        )
    return result


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    shard = sub.add_parser("phase-b-shard", help="materialize one 324-row initialization shard")
    shard.add_argument("--phase-a-dir", type=Path, default=DEFAULT_PHASE_A_DIR)
    shard.add_argument("--gate-dir", type=Path, default=DEFAULT_GATE_DIR)
    shard.add_argument("--c3-source-dir", type=Path, default=DEFAULT_C3_SOURCE_DIR)
    shard.add_argument("--v03-root", type=Path, default=DEFAULT_V03_ROOT)
    shard.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    shard.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)
    shard.add_argument("--initialization-seed", type=int, required=True, choices=Q13_INIT_SEEDS)
    shard.add_argument("--output-dir", type=Path, required=True)
    merge = sub.add_parser("merge", help="authenticate three shards and write one deterministic Phase-B result")
    merge.add_argument("--phase-a-dir", type=Path, default=DEFAULT_PHASE_A_DIR)
    merge.add_argument("--gate-dir", type=Path, default=DEFAULT_GATE_DIR)
    merge.add_argument("--c3-source-dir", type=Path, default=DEFAULT_C3_SOURCE_DIR)
    merge.add_argument("--v03-root", type=Path, default=DEFAULT_V03_ROOT)
    merge.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    merge.add_argument("--shard-root", type=Path, required=True)
    merge.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "phase-b-shard":
        result = _run_shard_command(args)
    elif args.command == "merge":
        phase_a = _authenticate_phase_a(Path(args.phase_a_dir), prereg_path=Path(args.prereg))
        q13_gate = _authenticate_q13_gate(
            Path(args.gate_dir),
            source_dir=Path(args.c3_source_dir),
            prereg_path=Path(args.prereg),
            v03_root=Path(args.v03_root),
        )
        result = _merge_shards(
            phase_a=phase_a,
            q13_gate=q13_gate,
            shard_root=Path(args.shard_root),
            output_dir=Path(args.output_dir),
        )
    else:  # pragma: no cover
        raise PhaseBError("unknown Phase-B command")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli())


__all__ = [
    "DEFAULT_PHASE_A_DIR",
    "EXPECTED_ROWS_PER_SHARD",
    "EXPECTED_TOTAL_ROWS",
    "PHASE_B_CLAIM_CEILING",
    "PHASE_B_DECISION",
    "PHASE_B_REDESIGN",
    "PHASE_B_ROW_SCHEMA",
    "PHASE_B_SCHEMA",
    "PHASE_B_SHARD_SCHEMA",
    "PhaseBError",
    "_authenticate_phase_a",
    "_authenticate_q13_gate",
    "_gc_gate",
    "_merge_shards",
    "_materialize_q13_pair",
    "_physical_gate",
]
