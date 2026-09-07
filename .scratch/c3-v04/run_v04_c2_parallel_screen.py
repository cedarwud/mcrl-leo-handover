#!/usr/bin/env python3
"""Bounded, preregistered C2 candidate screen.

This consumer is intentionally separate from the Phase-B materializer.  It
authenticates the sealed Phase-B result, rebuilds exactly one of the frozen
P0/P1/P2 training corpora, and trains only Q2 for the fixed offline ladder
``100, 500, 1500``.  A command-line ``arm`` invocation owns one candidate and
one initialization lineage and one explicit target rung.  The 100-rung arm
starts from its deterministic initialization; 500/1500 resume only from the
same arm's preceding authenticated write-once checkpoint.  ``merge``
authenticates the requested rung and all required preceding receipts and
applies the fixed design-positive rule at that rung.

The default production evaluation uses the existing read-only deployment
seams on the frozen DESIGN-EVAL block.  It never opens TEST, never evaluates
the held-out EE block, and never performs simulator-episode training.  This
file does not modify the Phase-B artifact or any existing package/document.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import copy
from dataclasses import asdict
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
from typing import Any, Callable

import numpy as np
try:  # Contract-only imports and ``--help`` must work without the server env.
    import torch
except ModuleNotFoundError:  # pragma: no cover - exercised on the lightweight WSL env
    torch = None  # type: ignore[assignment]


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (HERE, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.env.action_contract import NUM_ACTIONS  # noqa: E402
from mcrl.runtime.ee_axis_state import EE_AXIS_STATE_DIM  # noqa: E402


# Keep the immutable candidate identity available in contract-only mode.  The
# torch-backed learner/config classes are imported lazily by arm/baseline
# execution after Phase-B authentication.
C2_MAIN_VALUE = "C2-P0-MAIN-VALUE"
C2_Q13_VALUE = "C2-P1-Q13-VALUE"
C2_Q13_HUBER = "C2-P2-Q13-HUBER"
C2_CANDIDATE_IDS = (C2_MAIN_VALUE, C2_Q13_VALUE, C2_Q13_HUBER)
C2ParallelCandidateSpec = Any
EEAxisV04C2Trainer = Any


def _c2_algorithm_types() -> tuple[Any, Any, Any, Any]:
    if torch is None:
        raise C2ParallelScreenError("torch-backed C2 learner is unavailable in this environment")
    from mcrl.algorithms.ee_axis_action_shared_meanmax import EEAxisMaskedMeanMaxConfig
    from mcrl.algorithms.ee_axis_v04_c2_parallel import (
        C2ParallelCandidateSpec as CandidateSpec,
        EEAxisV04C2Trainer as C2Trainer,
        frozen_c2_candidate_specs as candidate_specs,
    )

    return CandidateSpec, C2Trainer, candidate_specs, EEAxisMaskedMeanMaxConfig


# Frozen parallel-screen protocol ------------------------------------------

SCREEN_SCHEMA = "multi-catfish-mcrl-v04-c2-parallel-screen-v1"
ARM_SCHEMA = "multi-catfish-mcrl-v04-c2-parallel-screen-arm-v1"
ARM_CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v04-c2-parallel-screen-checkpoint-v1"
ARM_METRICS_SCHEMA = "multi-catfish-mcrl-v04-c2-parallel-screen-metrics-v1"
ARM_EVAL_SCHEMA = "multi-catfish-mcrl-v04-c2-parallel-screen-design-eval-v1"
RESULT_SCHEMA = "multi-catfish-mcrl-v04-c2-parallel-screen-result-v1"
SEAL_SCHEMA = "multi-catfish-mcrl-v04-c2-parallel-screen-result-seal-v1"
PREPARE_SCHEMA = "multi-catfish-mcrl-v04-c2-parallel-screen-prepare-v1"
PREPARE_SEAL_SCHEMA = "multi-catfish-mcrl-v04-c2-parallel-screen-prepare-seal-v1"
BASELINE_SCHEMA = "multi-catfish-mcrl-v04-c2-parallel-screen-shared-baseline-v1"
BASELINE_SEAL_SCHEMA = "multi-catfish-mcrl-v04-c2-parallel-screen-shared-baseline-seal-v1"
SHARED_BASELINE_CANDIDATE = "C2-SHARED-BASELINE"

PHASE_B_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-b-v1"
PHASE_B_SHARD_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-b-shard-v1"
PHASE_A_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-a-v1"
PHASE_A_SEAL_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-a-seal-v1"
PHASE_B_SHARD_SEAL_SCHEMA = (
    "multi-catfish-mcrl-v04-c2-support-complete-phase-b-shard-seal-v1"
)

CLAIM_CEILING = "DESIGN_SCREEN_ONLY_NO_FINAL_TEST_NO_EE_EFFICACY_CLAIM"
PHASE_B_CLAIM_CEILING = (
    "FRESH_TRAIN_DESIGN_PROBE_ONLY_NO_TRAINING_NO_TEST_NO_EE_EFFICACY"
)
SOURCE_RULE = "c2-support-complete-legal-nonmain-v1"
Q13_CONTINUATION = "frozen-q1-plus-q3-after-opening-v1"
INITIALIZATION_SEEDS = (2026092101, 2026092102, 2026092103)
EXPECTED_PHASE_A_ROWS = 324
EXPECTED_ROWS_PER_SHARD = 324
EXPECTED_PHASE_B_ROWS = EXPECTED_ROWS_PER_SHARD * len(INITIALIZATION_SEEDS)
ACTION_DIM = NUM_ACTIONS
STATE_DIM = EE_AXIS_STATE_DIM
UPDATE_LADDER = (100, 500, 1500)
CHECKPOINT_EVERY = 100
CHECKPOINT_UPDATES = tuple(range(CHECKPOINT_EVERY, UPDATE_LADDER[-1] + 1, CHECKPOINT_EVERY))
EVALUATION_UPDATES = UPDATE_LADDER
EVALUATION_SPLIT = "DESIGN-EVAL"
# Amendment 2026-09-01: this is an ordered, closed ten-world block.  It is
# intentionally independent of the Phase-B/initialization seed namespaces.
DESIGN_EVAL_SEEDS = tuple(range(2026092901, 2026092911))
USERS = 100
STEPS_PER_EPISODE = 10
TEST_SPLIT_OPENED = False
HELD_OUT_EE_EVALUATED = False
EPISODE_TRAINING = False
TRAINING_SCOPE = "Q2_OFFLINE_FULL_BATCH_PAIRWISE_ONLY"
SCREEN_UPDATE_UNIT = "offline_full_batch_q2_pairwise_update"
TRAIN_ORDER = "canonical-sorted-sibling-key-full-batch-v1"
FIELD_COMPONENT = "V04_C2_PARALLEL_SCREEN_V1"
DESIGN_POSITIVE_DECISION = "DESIGN_POSITIVE_C2_CANDIDATE"
NO_CANDIDATE_DECISION = "NEXT_C2_FORMULA_PHYSICS_BATCH_REQUIRED"

DEFAULT_PHASE_B_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-c2-phase-b-merged-20260901-r1"
)
DEFAULT_PHASE_A_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-c2-support-complete-census-20260901-r3"
)
DEFAULT_GATE_DIR = REPO / "artifacts" / "multi-catfish-v04-c3-learnability-20260901-r2"
DEFAULT_C3_SOURCE_DIR = REPO / "artifacts" / "multi-catfish-v04-c3-source-20260901-r2"
DEFAULT_V03_ROOT = REPO / "artifacts" / "multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"
DEFAULT_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
DEFAULT_TLE_ROOT = Path("~/demo/tle_data/starlink/tle").expanduser()
DEFAULT_MAIN_DIR = REPO / "artifacts" / "training-2026-08-25-rerun01" / "main"
DEFAULT_ARM_ROOT = REPO / "artifacts" / "multi-catfish-v04-c2-parallel-screen-20260901-r1"
DEFAULT_RESULT_DIR = REPO / "artifacts" / "multi-catfish-v04-c2-parallel-screen-result-20260901-r1"
DEFAULT_PREPARE_DIR = REPO / "artifacts" / "multi-catfish-v04-c2-parallel-screen-prepare-20260901-r1"
DEFAULT_BASELINE_DIR = REPO / "artifacts" / "multi-catfish-v04-c2-parallel-screen-baseline-20260901-r1"


class C2ParallelScreenError(RuntimeError):
    """An authenticated C2 parallel screen failed closed."""


def _target_update(value: object, *, field: str = "target_update") -> int:
    if type(value) is not int or value not in UPDATE_LADDER:
        raise C2ParallelScreenError(
            f"{field} must be one of the frozen update rungs {UPDATE_LADDER}"
        )
    return value


def _prior_update(target_update: int) -> int | None:
    target = _target_update(target_update)
    index = UPDATE_LADDER.index(target)
    return UPDATE_LADDER[index - 1] if index else None


def _rung_updates(target_update: int) -> tuple[int, ...]:
    target = _target_update(target_update)
    return tuple(update for update in UPDATE_LADDER if update <= target)


def _checkpoint_updates_for(target_update: int) -> tuple[int, ...]:
    target = _target_update(target_update)
    return tuple(update for update in CHECKPOINT_UPDATES if update <= target)


def expected_design_eval_episodes(
    eligible_arm_count: int, *, target_update: int = UPDATE_LADDER[-1]
) -> int:
    """Return the exact amendment budget through ``target_update``.

    Each eligible candidate/initialization arm contributes ten FULL episodes
    at each evaluated rung.  The 30 DROP-C2 and 10 Main controls are shared by
    all arms and are therefore counted once.
    """

    if type(eligible_arm_count) is not int or eligible_arm_count < 0 or eligible_arm_count > len(C2_CANDIDATE_IDS):
        raise C2ParallelScreenError("eligible arm count is outside P0/P1/P2")
    return 30 * len(_rung_updates(target_update)) * eligible_arm_count + 30 + 10


def _arm_receipt_paths(root: Path, target_update: int) -> tuple[Path, Path]:
    target = _target_update(target_update)
    stem = f"arm-{target:06d}"
    return Path(root) / f"{stem}-result.json", Path(root) / f"{stem}-seal.json"


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
        raise C2ParallelScreenError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)[:-1]).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C2ParallelScreenError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise C2ParallelScreenError(f"expected a regular artifact file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> tuple[dict[str, Any], str]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise C2ParallelScreenError(f"sealed JSON artifact is missing: {source}")
    raw = source.read_bytes()
    try:
        payload = json.loads(
            raw.decode("ascii"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise C2ParallelScreenError(f"sealed JSON artifact is invalid: {source}") from error
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        raise C2ParallelScreenError(f"sealed JSON artifact is not canonical: {source}")
    return payload, hashlib.sha256(raw).hexdigest()


def _write_once_json(path: Path, payload: object) -> str:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite screen receipt: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw = _canonical_bytes(payload)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, destination)
    except FileExistsError as error:
        raise FileExistsError(f"refusing to overwrite screen receipt: {destination}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(raw).hexdigest()


def _write_once_torch(path: Path, payload: object) -> str:
    if torch is None:
        raise C2ParallelScreenError("torch-backed checkpoint writing is unavailable in this environment")
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite screen checkpoint: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        torch.save(payload, temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.link(temporary, destination)
    except FileExistsError as error:
        raise FileExistsError(f"refusing to overwrite screen checkpoint: {destination}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return _file_sha256(destination)


def _strict_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise C2ParallelScreenError(f"{field} must be an integer >= {minimum}")
    return value


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, bool):
        raise C2ParallelScreenError(f"{field} must be finite numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise C2ParallelScreenError(f"{field} must be finite numeric") from error
    if not math.isfinite(result):
        raise C2ParallelScreenError(f"{field} must be finite numeric")
    return result


def _nonnegative(value: object, *, field: str) -> float:
    result = _finite(value, field=field)
    if result < 0.0:
        raise C2ParallelScreenError(f"{field} must be nonnegative")
    return result


def _sibling_key(value: object, *, field: str = "sibling_key") -> tuple[int, str, str, int, tuple[int, int]]:
    if not isinstance(value, list) or len(value) != 5:
        raise C2ParallelScreenError(f"{field} is malformed")
    if (
        type(value[0]) is not int
        or value[0] < 0
        or not isinstance(value[1], str)
        or not isinstance(value[2], str)
        or type(value[3]) is not int
        or value[3] < 0
    ):
        raise C2ParallelScreenError(f"{field} is malformed")
    physical = value[4]
    if not isinstance(physical, list) or len(physical) != 2 or any(
        type(item) is not int or item < 0 for item in physical
    ):
        raise C2ParallelScreenError(f"{field} physical key is malformed")
    return (value[0], value[1], value[2], value[3], (physical[0], physical[1]))


def _intervention_key(key: tuple[int, str, str, int, tuple[int, int]]) -> tuple[int, str, str, int]:
    return key[:4]


def _cluster_key_text(key: tuple[int, str, str, int]) -> str:
    return json.dumps(list(key), separators=(",", ":"), ensure_ascii=True)


def _array_sha256(*arrays: object) -> str:
    digest = hashlib.sha256()
    for raw in arrays:
        value = np.asarray(raw)
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(json.dumps(list(value.shape), separators=(",", ":")).encode("ascii"))
        digest.update(np.ascontiguousarray(value).tobytes(order="C"))
    return digest.hexdigest()


def _regular_dir(value: Path | str, *, field: str) -> Path:
    path = Path(value)
    if path.is_symlink() or not path.is_dir():
        raise C2ParallelScreenError(f"{field} must be a regular directory: {path}")
    return path


def _resolve_artifact(value: object, *, base: Path, field: str, directory: bool = False) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise C2ParallelScreenError(f"{field} path is missing")
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    if path.is_symlink() or (not path.is_dir() if directory else not path.is_file()):
        raise C2ParallelScreenError(f"{field} path is missing or non-regular: {path}")
    return path


def _require_false(payload: Mapping[str, Any], field: str, *, label: str) -> None:
    if payload.get(field) is not False:
        raise C2ParallelScreenError(f"{label}.{field} must be exactly false")


def _candidate_spec(candidate_id: str) -> C2ParallelCandidateSpec:
    if torch is None:
        # Contract-only callers can still validate the frozen identity set;
        # training commands re-enter through the lazy learner import below.
        if candidate_id in C2_CANDIDATE_IDS:
            return candidate_id  # type: ignore[return-value]
        raise C2ParallelScreenError(f"candidate is not one of the frozen P0/P1/P2 arms: {candidate_id}")
    _candidate_type, _trainer_type, candidate_specs, _config_type = _c2_algorithm_types()
    for spec in candidate_specs():
        if spec.candidate_id == candidate_id:
            return spec
    raise C2ParallelScreenError(f"candidate is not one of the frozen P0/P1/P2 arms: {candidate_id}")


def eligible_arms_from_gates(*, gc_passed: bool, q13_physical_pass_count: int) -> tuple[str, ...]:
    """Return the only arm set permitted by the Phase-B physical gates."""

    if type(gc_passed) is not bool:
        raise C2ParallelScreenError("G-C disposition must be exactly Boolean")
    if type(q13_physical_pass_count) is not int or not 0 <= q13_physical_pass_count <= len(INITIALIZATION_SEEDS):
        raise C2ParallelScreenError("Q13 physical pass count is outside the frozen three-lineage set")
    eligible: list[str] = []
    if gc_passed:
        eligible.append(C2_MAIN_VALUE)
    if q13_physical_pass_count >= 2:
        eligible.extend(("C2-P1-Q13-VALUE", "C2-P2-Q13-HUBER"))
    return tuple(eligible)


def _phase_a_rows(phase_a_dir: Path) -> tuple[dict[str, Any], dict[str, Mapping[str, Any]]]:
    root = _regular_dir(phase_a_dir, field="phase_a_dir")
    result, result_file_sha = _read_json(root / "phase-a-result.json")
    seal, seal_file_sha = _read_json(root / "phase-a-seal.json")
    body = dict(result)
    phase_a_sha = _digest(body.pop("phase_a_sha256", None), field="phase_a_sha256")
    if (
        result.get("schema") != PHASE_A_SCHEMA
        or result.get("claim_ceiling") != PHASE_B_CLAIM_CEILING
        or result.get("row_count") != EXPECTED_PHASE_A_ROWS
        or result.get("expected_row_count") != EXPECTED_PHASE_A_ROWS
        or result.get("training_run") is not False
        or result.get("test_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
        or phase_a_sha != canonical_sha256(body)
        or seal.get("schema") != PHASE_A_SEAL_SCHEMA
        or seal.get("phase_a_file_sha256") != result_file_sha
        or seal.get("phase_a_sha256") != phase_a_sha
        or seal.get("row_count") != EXPECTED_PHASE_A_ROWS
        or seal.get("training_run") is not False
        or seal.get("test_opened") is not False
        or seal.get("held_out_ee_evaluated") is not False
    ):
        raise C2ParallelScreenError("Phase-A result/seal is not an authenticated 324-row TRAIN-only artifact")
    rows = result.get("rows")
    if not isinstance(rows, list) or len(rows) != EXPECTED_PHASE_A_ROWS:
        raise C2ParallelScreenError("Phase-A rows are incomplete")
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise C2ParallelScreenError("Phase-A row is malformed")
        if row.get("schema") != "multi-catfish-mcrl-v04-c2-support-complete-phase-a-row-v1":
            raise C2ParallelScreenError("Phase-A row schema is stale")
        key = _sibling_key(row.get("sibling_key"))
        action = _strict_int(row.get("candidate_action"), field="Phase-A candidate_action")
        if action >= ACTION_DIM:
            raise C2ParallelScreenError("Phase-A candidate action is outside the action contract")
        status = row.get("row_status")
        if status not in {"ready", "row-failure", "support-expired"}:
            raise C2ParallelScreenError("Phase-A row status is invalid")
        if status == "ready":
            _finite(row.get("zeta2_temporal_surplus_bits"), field="Phase-A zeta2")
        text = json.dumps(list(key), separators=(",", ":"), ensure_ascii=True)
        if text in indexed:
            raise C2ParallelScreenError("Phase-A contains duplicate sibling identity")
        indexed[text] = row
    return (
        {
            "dir": root,
            "result": result,
            "result_file_sha256": result_file_sha,
            "seal": seal,
            "seal_file_sha256": seal_file_sha,
            "phase_a_sha256": phase_a_sha,
        },
        indexed,
    )


def _validate_phase_b_row(row: Mapping[str, Any], *, seed: int, index: int) -> None:
    if row.get("schema") != "multi-catfish-mcrl-v04-c2-support-complete-phase-b-row-v1":
        raise C2ParallelScreenError(f"Phase-B row schema drifted for initialization {seed}/{index}")
    if row.get("initialization_seed") != seed:
        raise C2ParallelScreenError(f"Phase-B row initialization drifted for {seed}/{index}")
    if row.get("source_route") != "C2" or row.get("continuation") != Q13_CONTINUATION:
        raise C2ParallelScreenError(f"Phase-B row route/continuation drifted for {seed}/{index}")
    row_digest = _digest(row.get("row_sha256"), field=f"Phase-B row {seed}/{index}.row_sha256")
    body = {key: value for key, value in row.items() if key != "row_sha256"}
    if row_digest != canonical_sha256(body):
        raise C2ParallelScreenError(f"Phase-B row digest drifted for {seed}/{index}")
    _sibling_key(row.get("sibling_key"), field=f"Phase-B row {seed}/{index}.sibling_key")
    status = row.get("row_status")
    if status not in {"ready", "row-failure", "support-expired"}:
        raise C2ParallelScreenError(f"Phase-B row status is invalid for {seed}/{index}")
    if status != "ready":
        if row.get("pair") is not None or row.get("raw_trace") is not None:
            raise C2ParallelScreenError(f"non-ready Phase-B row carries an unverified pair for {seed}/{index}")
        return
    pair = row.get("pair")
    if not isinstance(pair, Mapping):
        raise C2ParallelScreenError(f"ready Phase-B row lacks pair for {seed}/{index}")
    anchor_state = row.get("anchor_state")
    if not isinstance(anchor_state, Mapping):
        raise C2ParallelScreenError(f"ready Phase-B row lacks anchor_state for {seed}/{index}")
    anchor_digest = _digest(
        anchor_state.get("anchor_state_sha256"),
        field=f"Phase-B row {seed}/{index}.anchor_state_sha256",
    )
    anchor_body = {key: value for key, value in anchor_state.items() if key != "anchor_state_sha256"}
    if anchor_digest != canonical_sha256(anchor_body):
        raise C2ParallelScreenError(f"Phase-B anchor_state digest drifted for {seed}/{index}")
    if anchor_state.get("schema") != "multi-catfish-mcrl-v04-c2-support-complete-anchor-state-v1":
        raise C2ParallelScreenError(f"Phase-B anchor_state schema drifted for {seed}/{index}")
    anchor_values = np.asarray(anchor_state.get("state"), dtype=np.float32)
    anchor_mask = np.asarray(anchor_state.get("action_mask"))
    if anchor_values.shape != (STATE_DIM,) or not np.all(np.isfinite(anchor_values)):
        raise C2ParallelScreenError(f"Phase-B anchor_state is not finite {STATE_DIM}-D for {seed}/{index}")
    if anchor_mask.dtype != np.bool_ or anchor_mask.shape != (ACTION_DIM,) or not bool(np.all(anchor_mask)):
        raise C2ParallelScreenError(f"Phase-B anchor_state mask is not complete for {seed}/{index}")
    state = np.asarray(pair.get("state"), dtype=np.float32)
    mask = np.asarray(pair.get("action_mask"))
    if state.shape != (STATE_DIM,) or not np.all(np.isfinite(state)) or not np.array_equal(state, anchor_values):
        raise C2ParallelScreenError(f"Phase-B pair state is not finite {STATE_DIM}-D for {seed}/{index}")
    if mask.dtype != np.bool_ or mask.shape != (ACTION_DIM,) or not bool(np.all(mask)) or not np.array_equal(mask, anchor_mask):
        raise C2ParallelScreenError(f"Phase-B pair action mask is not complete {ACTION_DIM}-D for {seed}/{index}")
    for field in ("reference_action", "candidate_action"):
        action = _strict_int(pair.get(field), field=f"Phase-B pair {field}")
        if action >= ACTION_DIM or not bool(mask[action]):
            raise C2ParallelScreenError(f"Phase-B pair {field} is illegal for {seed}/{index}")
    _finite(pair.get("zeta2_temporal_surplus_bits"), field=f"Phase-B pair zeta2 {seed}/{index}")
    raw = row.get("raw_trace")
    if not isinstance(raw, Mapping):
        raise C2ParallelScreenError(f"Phase-B ready row raw_trace is missing for {seed}/{index}")
    # The physical trace is a receipt, not just a derived scalar.  Validate
    # the required fields here so downstream EE/action diagnostics cannot
    # silently consume a partial record.
    for field in (
        "reference",
        "candidate",
        "q13_reference_decisions",
        "q13_candidate_decisions",
        "support_counts",
        "continuation_start_offset",
        "release_offset",
        "release_reason",
    ):
        if field not in raw:
            raise C2ParallelScreenError(f"Phase-B raw trace lacks {field} for {seed}/{index}")
    rates_fields = (
        "reference_rates_bps",
        "candidate_rates_bps",
        "reference_system_power_w",
        "candidate_system_power_w",
        "interval_s",
        "lambda_bits_per_j",
        "offset_surplus_bits",
    )
    for field in rates_fields:
        if field not in pair:
            raise C2ParallelScreenError(f"Phase-B pair lacks {field} for {seed}/{index}")


def _authenticate_shard(
    shard_dir: Path,
    *,
    phase_b_result: Mapping[str, Any],
    phase_a_meta: Mapping[str, Any],
    seed: int,
) -> tuple[dict[str, Any], str, str]:
    root = _regular_dir(shard_dir, field=f"Phase-B shard {seed}")
    hybrid_refs = phase_b_result.get("q13_hybrid_file_sha256")
    if not isinstance(hybrid_refs, Mapping):
        raise C2ParallelScreenError("Phase-B q13_hybrid_file_sha256 receipt is not a seed mapping")
    result, result_file_sha = _read_json(root / "shard-result.json")
    seal, seal_file_sha = _read_json(root / "shard-seal.json")
    body = dict(result)
    shard_sha = _digest(body.pop("shard_sha256", None), field=f"shard[{seed}].shard_sha256")
    if (
        result.get("schema") != PHASE_B_SHARD_SCHEMA
        or result.get("status") != "PHASE_B_SHARD_COMPLETE"
        or result.get("claim_ceiling") != "FRESH_TRAIN_DESIGN_PROBE_ONLY_NO_TRAINING_NO_TEST_NO_EE_EFFICACY"
        or result.get("initialization_seed") != seed
        or result.get("row_count") != EXPECTED_ROWS_PER_SHARD
        or result.get("expected_row_count") != EXPECTED_ROWS_PER_SHARD
        or result.get("phase_a_result_file_sha256") != phase_a_meta["result_file_sha256"]
        or result.get("phase_a_sha256") != phase_a_meta["phase_a_sha256"]
        or result.get("phase_a_seal_file_sha256") != phase_a_meta["seal_file_sha256"]
        or result.get("prepare_sha256") != phase_b_result.get("prepare_sha256")
        or result.get("schedule_sha256") != phase_b_result.get("schedule_sha256")
        or result.get("q13_gate_authority_sha256") != phase_b_result.get("q13_gate_authority_sha256")
        or result.get("q13_gate_result_file_sha256") != phase_b_result.get("q13_gate_result_file_sha256")
        or result.get("q13_gate_source_manifest_sha256") != phase_b_result.get("q13_gate_source_manifest_sha256")
        or result.get("q13_gate_schedule_sha256") != phase_b_result.get("q13_gate_schedule_sha256")
        or result.get("q13_hybrid_file_sha256") != hybrid_refs.get(str(seed))
        or result.get("training_run") is not False
        or result.get("test_split_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
        or shard_sha != canonical_sha256(body)
        or seal.get("schema") != PHASE_B_SHARD_SEAL_SCHEMA
        or seal.get("status") != "PHASE_B_SHARD_COMPLETE"
        or seal.get("shard_sha256") != shard_sha
        or seal.get("shard_result_file_sha256") != result_file_sha
        or seal.get("initialization_seed") != seed
        or seal.get("phase_a_result_file_sha256") != phase_a_meta["result_file_sha256"]
        or seal.get("phase_a_sha256") != phase_a_meta["phase_a_sha256"]
        or seal.get("q13_gate_authority_sha256") != phase_b_result.get("q13_gate_authority_sha256")
        or seal.get("q13_hybrid_file_sha256") != result.get("q13_hybrid_file_sha256")
        or seal.get("phase_a_sha256") != phase_a_meta["phase_a_sha256"]
        or seal.get("row_count") != EXPECTED_ROWS_PER_SHARD
        or seal.get("training_run") is not False
        or seal.get("test_split_opened") is not False
        or seal.get("held_out_ee_evaluated") is not False
    ):
        raise C2ParallelScreenError(f"Phase-B shard authority mismatch for initialization {seed}")
    rows = result.get("rows")
    if not isinstance(rows, list) or len(rows) != EXPECTED_ROWS_PER_SHARD:
        raise C2ParallelScreenError(f"Phase-B shard row count mismatch for initialization {seed}")
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise C2ParallelScreenError(f"Phase-B shard row is malformed for initialization {seed}/{index}")
        _validate_phase_b_row(row, seed=seed, index=index)
        key = _sibling_key(row.get("sibling_key"))
        key_text = json.dumps(list(key), separators=(",", ":"), ensure_ascii=True)
        if key_text in seen:
            raise C2ParallelScreenError(f"Phase-B shard has duplicate sibling for initialization {seed}")
        seen.add(key_text)
    return result, result_file_sha, seal_file_sha


def authenticate_phase_b(
    phase_b_dir: Path,
    *,
    phase_a_dir: Path | None = DEFAULT_PHASE_A_DIR,
) -> dict[str, Any]:
    """Authenticate the complete Phase-B result and all three shard bytes."""

    root = _regular_dir(phase_b_dir, field="phase_b_dir")
    result, result_file_sha = _read_json(root / "phase-b-result.json")
    seal, seal_file_sha = _read_json(root / "phase-b-seal.json")
    body = dict(result)
    phase_b_sha = _digest(body.pop("phase_b_sha256", None), field="phase_b_sha256")
    for field in (
        "phase_a_result_file_sha256",
        "phase_a_sha256",
        "phase_a_seal_file_sha256",
        "prepare_sha256",
        "schedule_sha256",
        "q13_gate_authority_sha256",
        "q13_gate_result_file_sha256",
        "q13_gate_source_manifest_sha256",
        "q13_gate_schedule_sha256",
    ):
        _digest(result.get(field), field=f"Phase-B.{field}")
    if (
        result.get("schema") != PHASE_B_SCHEMA
        or result.get("status") != "PHASE_B_COMPLETE"
        or result.get("claim_ceiling") != PHASE_B_CLAIM_CEILING
        or result.get("continuation") != Q13_CONTINUATION
        or result.get("source_rule") != SOURCE_RULE
        or result.get("row_count") != EXPECTED_PHASE_B_ROWS
        or result.get("expected_row_count") != EXPECTED_PHASE_B_ROWS
        or result.get("initialization_seeds") != list(INITIALIZATION_SEEDS)
        or result.get("training_run") is not False
        or result.get("test_split_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
        or phase_b_sha != canonical_sha256(body)
        or seal.get("schema") != "multi-catfish-mcrl-v04-c2-support-complete-phase-b-seal-v1"
        or seal.get("status") != "PHASE_B_COMPLETE"
        or seal.get("phase_b_sha256") != phase_b_sha
        or seal.get("phase_b_result_file_sha256") != result_file_sha
        or seal.get("row_count") != EXPECTED_PHASE_B_ROWS
        or seal.get("initialization_seeds") != list(INITIALIZATION_SEEDS)
        or seal.get("eligible_arms") != result.get("eligible_arms")
        or seal.get("q13_gate_authority_sha256") != result.get("q13_gate_authority_sha256")
        or seal.get("training_run") is not False
        or seal.get("test_split_opened") is not False
        or seal.get("held_out_ee_evaluated") is not False
    ):
        raise C2ParallelScreenError("Phase-B result/seal is not the authenticated complete artifact")

    phase_a_value = phase_a_dir
    if phase_a_value is None:
        phase_a_value = Path(str(result.get("phase_a_dir", "")))
    phase_a_meta, phase_a_rows = _phase_a_rows(Path(phase_a_value))
    if (
        result.get("phase_a_result_file_sha256") != phase_a_meta["result_file_sha256"]
        or result.get("phase_a_sha256") != phase_a_meta["phase_a_sha256"]
        or result.get("phase_a_seal_file_sha256") != phase_a_meta["seal_file_sha256"]
    ):
        raise C2ParallelScreenError("Phase-B to Phase-A lineage differs")

    gates = result.get("gates")
    if not isinstance(gates, Mapping):
        raise C2ParallelScreenError("Phase-B gates are missing")
    gc = gates.get("G-C")
    physical = gates.get("Q13-PHYSICAL")
    authorized_inits = gates.get("Q13_PHYSICAL_AUTHORIZED_INITIALIZATIONS")
    authorized = gates.get("Q13_PHYSICAL_AUTHORIZED")
    if not isinstance(gc, Mapping) or type(gc.get("passed")) is not bool:
        raise C2ParallelScreenError("Phase-B G-C gate is malformed")
    if not isinstance(physical, Mapping) or set(physical) != {str(seed) for seed in INITIALIZATION_SEEDS}:
        raise C2ParallelScreenError("Phase-B Q13 physical gate does not contain three lineages")
    if any(not isinstance(physical[str(seed)], Mapping) or type(physical[str(seed)].get("passed")) is not bool for seed in INITIALIZATION_SEEDS):
        raise C2ParallelScreenError("Phase-B Q13 physical gate lineage disposition is malformed")
    if not isinstance(authorized_inits, list) or any(
        type(seed) is not int or seed not in INITIALIZATION_SEEDS for seed in authorized_inits
    ) or len(set(authorized_inits)) != len(authorized_inits):
        raise C2ParallelScreenError("Phase-B authorized initialization receipt is malformed")
    expected_authorized = [seed for seed in INITIALIZATION_SEEDS if physical[str(seed)].get("passed") is True]
    if authorized_inits != expected_authorized or type(authorized) is not bool or authorized != (len(expected_authorized) >= 2):
        raise C2ParallelScreenError("Phase-B physical authorization list is inconsistent")

    shards_receipt = result.get("shards")
    if not isinstance(shards_receipt, Mapping) or set(shards_receipt) != {str(seed) for seed in INITIALIZATION_SEEDS}:
        raise C2ParallelScreenError("Phase-B shard receipt set is incomplete")
    shards: dict[int, dict[str, Any]] = {}
    shard_receipts: dict[str, dict[str, str]] = {}
    expected_keys: set[str] | None = None
    for seed in INITIALIZATION_SEEDS:
        receipt = shards_receipt[str(seed)]
        if not isinstance(receipt, Mapping):
            raise C2ParallelScreenError(f"Phase-B shard receipt is malformed for {seed}")
        shard_path = _resolve_artifact(receipt.get("path"), base=root, field=f"shards[{seed}].path", directory=True)
        shard_result, shard_file_sha, shard_seal_sha = _authenticate_shard(
            shard_path,
            phase_b_result=result,
            phase_a_meta=phase_a_meta,
            seed=seed,
        )
        if (
            receipt.get("result_file_sha256") != shard_file_sha
            or receipt.get("seal_file_sha256") != shard_seal_sha
            or receipt.get("shard_sha256") != shard_result["shard_sha256"]
        ):
            raise C2ParallelScreenError(f"Phase-B shard receipt digest mismatch for {seed}")
        rows = shard_result["rows"]
        keys = {
            json.dumps(list(_sibling_key(row["sibling_key"])), separators=(",", ":"), ensure_ascii=True)
            for row in rows
        }
        if expected_keys is None:
            expected_keys = keys
        elif keys != expected_keys:
            raise C2ParallelScreenError("Phase-B initialization shards do not share one sibling census")
        shards[seed] = shard_result
        shard_receipts[str(seed)] = {
            "path": str(shard_path.resolve()),
            "result_file_sha256": shard_file_sha,
            "seal_file_sha256": shard_seal_sha,
            "shard_sha256": str(shard_result["shard_sha256"]),
        }
    if expected_keys is None or len(expected_keys) != EXPECTED_ROWS_PER_SHARD:
        raise C2ParallelScreenError("Phase-B sibling census is incomplete")

    # Phase B is the authority for arm eligibility.  Recompute the expected
    # set from its two physical dispositions and require the sealed result to
    # publish the same machine-readable receipt.  A missing/extra arm is an
    # authentication failure; do not silently infer eligibility downstream.
    expected_eligible = list(
        eligible_arms_from_gates(
            gc_passed=gc.get("passed") is True,
            q13_physical_pass_count=len(expected_authorized),
        )
    )
    eligible_arms = result.get("eligible_arms")
    if (
        not isinstance(eligible_arms, list)
        or eligible_arms != expected_eligible
        or any(arm not in C2_CANDIDATE_IDS for arm in eligible_arms)
        or (result.get("decision") == "AUTHORIZE_PARALLEL_SUPPORT_COMPLETE_C2_SCREEN" and not eligible_arms)
        or (not eligible_arms and result.get("decision") != "NEXT_C2_FORMULA_PHYSICS_BATCH_REQUIRED")
    ):
        raise C2ParallelScreenError("Phase-B eligible_arms is absent or inconsistent with sealed gates")
    return {
        "dir": root,
        "result": result,
        "result_file_sha256": result_file_sha,
        "seal": seal,
        "seal_file_sha256": seal_file_sha,
        "phase_b_sha256": phase_b_sha,
        "phase_a": phase_a_meta,
        "phase_a_rows": phase_a_rows,
        "shards": shards,
        "shard_receipts": shard_receipts,
        "gates": gates,
        "eligible_arms": tuple(eligible_arms),
        # Compatibility alias is deliberately not used by selection code;
        # receipts and merge always consume eligible_arms above.
        "eligible_candidates": tuple(eligible_arms),
    }


def _row_text(row: Mapping[str, Any]) -> str:
    return json.dumps(list(_sibling_key(row.get("sibling_key"))), separators=(",", ":"), ensure_ascii=True)


def _select_pair_target(
    candidate_id: str,
    phase_a_row: Mapping[str, Any],
    phase_b_pair: Mapping[str, Any],
    *,
    index: int,
) -> float:
    """Select the frozen target without conflating Phase-A support status.

    P0 is the only arm whose target is the Phase-A Main-continuation scalar,
    so it alone requires a ready Phase-A row.  P1/P2 retain the Phase-A row
    solely as a sibling-identity join and consume the ready Phase-B Q13 pair,
    including when the corresponding Phase-A support row is expired.
    """

    if candidate_id == C2_MAIN_VALUE:
        if phase_a_row.get("row_status") != "ready":
            raise C2ParallelScreenError(
                f"{candidate_id} cannot consume a non-ready Phase-A target at {index}"
            )
        raw_target = phase_a_row.get("zeta2_temporal_surplus_bits")
    elif candidate_id in (C2_Q13_VALUE, C2_Q13_HUBER):
        raw_target = phase_b_pair.get("zeta2_temporal_surplus_bits")
    else:
        raise C2ParallelScreenError(f"unknown C2 target candidate at {index}: {candidate_id}")
    return _finite(raw_target, field=f"{candidate_id}.target[{index}]")


def build_pair_batch(
    phase_b: Mapping[str, Any],
    *,
    candidate_id: str,
    initialization_seed: int,
) -> tuple[EEAxisPairBatch, tuple[dict[str, Any], ...], str]:
    """Join one complete Phase-B state corpus with the P0/P1/P2 target."""

    spec = _candidate_spec(candidate_id)
    if candidate_id not in tuple(phase_b.get("eligible_candidates", ())):
        raise C2ParallelScreenError(f"candidate is not physically eligible: {candidate_id}")
    if initialization_seed not in INITIALIZATION_SEEDS:
        raise C2ParallelScreenError(f"initialization seed is not frozen: {initialization_seed}")
    shard = phase_b.get("shards", {}).get(initialization_seed)
    if not isinstance(shard, Mapping):
        raise C2ParallelScreenError(f"Phase-B shard is missing for {initialization_seed}")
    rows = shard.get("rows")
    if not isinstance(rows, list) or len(rows) != EXPECTED_ROWS_PER_SHARD:
        raise C2ParallelScreenError("Phase-B training corpus must contain exactly 324 rows")
    phase_a_rows = phase_b.get("phase_a_rows")
    if not isinstance(phase_a_rows, Mapping):
        raise C2ParallelScreenError("Phase-A row join is missing")
    ordered = sorted(rows, key=lambda row: _sibling_key(row.get("sibling_key")))
    states: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    references: list[int] = []
    candidates: list[int] = []
    targets: list[float] = []
    metadata: list[dict[str, Any]] = []
    for index, row in enumerate(ordered):
        if not isinstance(row, Mapping) or row.get("row_status") != "ready":
            raise C2ParallelScreenError(f"{candidate_id} cannot train on a non-ready Phase-B row {index}")
        pair = row.get("pair")
        if not isinstance(pair, Mapping):
            raise C2ParallelScreenError(f"{candidate_id} pair is missing at {index}")
        phase_a_row = phase_a_rows.get(_row_text(row))
        if not isinstance(phase_a_row, Mapping):
            raise C2ParallelScreenError(f"Phase-A/Phase-B sibling join is missing at {index}")
        target = _select_pair_target(
            candidate_id, phase_a_row, pair, index=index
        )
        state = np.asarray(pair.get("state"), dtype=np.float32)
        mask = np.asarray(pair.get("action_mask"))
        reference = _strict_int(pair.get("reference_action"), field=f"{candidate_id}.reference[{index}")
        candidate = _strict_int(pair.get("candidate_action"), field=f"{candidate_id}.candidate[{index}")
        if state.shape != (STATE_DIM,) or mask.dtype != np.bool_ or mask.shape != (ACTION_DIM,):
            raise C2ParallelScreenError(f"{candidate_id} state/mask shape drifted at {index}")
        if reference >= ACTION_DIM or candidate >= ACTION_DIM or not mask[reference] or not mask[candidate]:
            raise C2ParallelScreenError(f"{candidate_id} illegal pair action at {index}")
        states.append(state)
        masks.append(mask)
        references.append(reference)
        candidates.append(candidate)
        targets.append(target)
        metadata.append(
            {
                "sibling_key": list(_sibling_key(row["sibling_key"])),
                "intervention_key": list(_intervention_key(_sibling_key(row["sibling_key"]))),
                "candidate_id": spec.candidate_id,
                "target_source": "phase-a-main-continuation" if candidate_id == C2_MAIN_VALUE else "phase-b-q13-continuation",
                "target_surplus_bits": target,
                "candidate_action": candidate,
                "reference_action": reference,
            }
        )
    if torch is None:
        raise C2ParallelScreenError("cannot build a torch-backed pair batch without the server environment")
    from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch

    batch = EEAxisPairBatch(
        states=np.asarray(states, dtype=np.float32),
        reference_actions=np.asarray(references, dtype=np.int64),
        candidate_actions=np.asarray(candidates, dtype=np.int64),
        target_surplus_bits=np.asarray(targets, dtype=np.float32),
        action_masks=np.asarray(masks, dtype=np.bool_),
    )
    batch.validate(state_dim=STATE_DIM, action_dim=ACTION_DIM)
    corpus_sha = _array_sha256(
        batch.states,
        batch.reference_actions,
        batch.candidate_actions,
        batch.target_surplus_bits,
        batch.action_masks,
    )
    return batch, tuple(metadata), corpus_sha


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


def spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    a = np.asarray(_rank(left), dtype=np.float64)
    b = np.asarray(_rank(right), dtype=np.float64)
    a -= float(np.mean(a))
    b -= float(np.mean(b))
    denominator = float(np.sqrt(np.sum(a * a) * np.sum(b * b)))
    if denominator == 0.0:
        return None
    return float(np.sum(a * b) / denominator)


def target_diagnostics(
    trainer: EEAxisV04C2Trainer,
    batch: EEAxisPairBatch,
    metadata: Sequence[Mapping[str, Any]],
    *,
    frozen_q13_surfaces: Mapping[str, Sequence[float]] | None = None,
) -> dict[str, Any]:
    """Report target regret, rank agreement, and Q2-vs-Q13 magnitude."""

    groups: dict[str, list[int]] = {}
    for index, row in enumerate(metadata):
        key = _cluster_key_text(tuple(row["intervention_key"]))  # type: ignore[arg-type]
        groups.setdefault(key, []).append(index)
    cluster_rows: dict[str, dict[str, Any]] = {}
    regrets: list[float] = []
    correlations: list[float] = []
    q2_magnitudes: list[float] = []
    q13_magnitudes: list[float] = []
    for key, indices in sorted(groups.items()):
        first = indices[0]
        state = batch.states[first : first + 1]
        mask = batch.action_masks[first : first + 1]
        q2 = trainer.q2_values(state, mask)[0]
        targets = {int(batch.reference_actions[first]): 0.0}
        for index in indices:
            targets[int(batch.candidate_actions[index])] = float(
                batch.target_surplus_bits[index] / trainer.config.kappa_bits
            )
        if set(targets) != set(range(ACTION_DIM)):
            raise C2ParallelScreenError(f"target diagnostic cluster lacks all {ACTION_DIM} actions: {key}")
        target_vector = [targets[action] for action in range(ACTION_DIM)]
        legal = np.asarray(mask[0], dtype=np.bool_)
        predicted_action = int(np.argmax(np.where(legal, q2, -np.inf)))
        regret = float(max(target_vector) - target_vector[predicted_action])
        correlation = spearman(q2.tolist(), target_vector)
        if correlation is None:
            raise C2ParallelScreenError(f"target diagnostic Spearman is undefined: {key}")
        q2_abs = float(np.median(np.abs(q2)))
        q2_magnitudes.append(q2_abs)
        regrets.append(regret)
        correlations.append(correlation)
        q13_abs: float | None = None
        if frozen_q13_surfaces is not None:
            surface = frozen_q13_surfaces.get(key)
            if surface is None or len(surface) != ACTION_DIM:
                raise C2ParallelScreenError(f"frozen Q1+Q3 surface is missing: {key}")
            q13_abs = float(np.median(np.abs(np.asarray(surface, dtype=np.float64))))
            q13_magnitudes.append(q13_abs)
        cluster_rows[key] = {
            "target_best_action": int(np.argmax(np.asarray(target_vector))),
            "predicted_action": predicted_action,
            "full_action_target_regret": regret,
            "spearman": correlation,
            "q2_median_abs": q2_abs,
            "q13_median_abs": q13_abs,
        }
    q13_median = float(np.median(q13_magnitudes)) if q13_magnitudes else None
    q2_median = float(np.median(q2_magnitudes)) if q2_magnitudes else None
    return {
        "clusters": cluster_rows,
        "cluster_count": len(cluster_rows),
        "full_action_target_regret": {
            "mean": float(np.mean(regrets)),
            "median": float(np.median(regrets)),
            "max": float(np.max(regrets)),
            "positive_count": sum(value > 0.0 for value in regrets),
        },
        "spearman": {
            "mean": float(np.mean(correlations)),
            "median": float(np.median(correlations)),
            "min": float(np.min(correlations)),
        },
        "q2_surface_magnitude": {
            "median_abs": q2_median,
            "q13_median_abs": q13_median,
            "relative_to_frozen_q1_plus_q3": (
                q2_median / q13_median if q13_median is not None and q13_median > 0.0 else None
            ),
        },
    }


def _same_state(left: Any, right: Any) -> bool:
    tensor_type = getattr(torch, "Tensor", ()) if torch is not None else ()
    if isinstance(left, tensor_type) or isinstance(right, tensor_type):
        return isinstance(left, tensor_type) and isinstance(right, tensor_type) and torch.equal(
            left.detach().cpu(), right.detach().cpu()
        )
    if isinstance(left, Mapping) or isinstance(right, Mapping):
        return isinstance(left, Mapping) and isinstance(right, Mapping) and set(left) == set(right) and all(
            _same_state(left[key], right[key]) for key in left
        )
    if isinstance(left, (tuple, list)) or isinstance(right, (tuple, list)):
        return isinstance(left, type(right)) and len(left) == len(right) and all(
            _same_state(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def _checkpoint_payload(
    trainer: EEAxisV04C2Trainer,
    *,
    phase_b: Mapping[str, Any],
    candidate_id: str,
    initialization_seed: int,
    update_count: int,
    train_corpus_sha256: str,
    prepare_file_sha256: str | None = None,
    baseline_file_sha256: str | None = None,
) -> dict[str, Any]:
    if update_count not in CHECKPOINT_UPDATES:
        raise C2ParallelScreenError("checkpoint update count is outside the frozen ladder")
    return {
        "schema": ARM_CHECKPOINT_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "candidate_id": candidate_id,
        "initialization_seed": initialization_seed,
        "phase_b_sha256": phase_b["phase_b_sha256"],
        "prepare_file_sha256": prepare_file_sha256,
        "baseline_file_sha256": baseline_file_sha256,
        "train_corpus_sha256": train_corpus_sha256,
        "screen_update_unit": SCREEN_UPDATE_UNIT,
        "train_order": TRAIN_ORDER,
        "update_count": update_count,
        "evaluation_split": EVALUATION_SPLIT,
        "test_split_opened": TEST_SPLIT_OPENED,
        "held_out_ee_evaluated": HELD_OUT_EE_EVALUATED,
        "episode_training": EPISODE_TRAINING,
        "trainer": trainer.checkpoint_state(update_count=update_count),
    }


def _reload_checkpoint(
    payload: Mapping[str, Any],
    *,
    config: EEAxisMaskedMeanMaxConfig,
    candidate: C2ParallelCandidateSpec,
    seed: int,
    batch: EEAxisPairBatch,
) -> EEAxisV04C2Trainer:
    for field, expected in (
        ("schema", ARM_CHECKPOINT_SCHEMA),
        ("candidate_id", candidate.candidate_id),
        ("initialization_seed", seed),
        ("evaluation_split", EVALUATION_SPLIT),
        ("test_split_opened", False),
        ("held_out_ee_evaluated", False),
        ("episode_training", False),
    ):
        if payload.get(field) != expected:
            raise C2ParallelScreenError(f"checkpoint metadata mismatch in {field}")
    _candidate_type, trainer_type, _candidate_specs, _config_type = _c2_algorithm_types()
    trainer = trainer_type(config, candidate=candidate, train_seed=seed)
    nested = payload.get("trainer")
    if not isinstance(nested, Mapping):
        raise C2ParallelScreenError("checkpoint trainer payload is missing")
    loaded = trainer.load_checkpoint_state(nested)
    if loaded != _strict_int(payload.get("update_count"), field="checkpoint.update_count", minimum=1):
        raise C2ParallelScreenError("checkpoint update count is inconsistent")
    return trainer


def _load_checkpoint_receipt(
    arm_root: Path,
    arm_result: Mapping[str, Any],
    *,
    update_count: int,
) -> Mapping[str, Any]:
    """Load one already-authenticated write-once checkpoint for resume."""

    if torch is None:
        raise C2ParallelScreenError("torch-backed checkpoint loading is unavailable in this environment")
    target = _target_update(update_count, field="resume_update")
    receipts = arm_result.get("checkpoint_receipts")
    if not isinstance(receipts, list):
        raise C2ParallelScreenError("resume arm has no checkpoint receipt list")
    matches = [
        receipt
        for receipt in receipts
        if isinstance(receipt, Mapping) and receipt.get("update_count") == target
    ]
    if len(matches) != 1:
        raise C2ParallelScreenError(f"resume checkpoint receipt is missing or duplicated at update {target}")
    receipt = matches[0]
    if receipt.get("strict_reload") is not True:
        raise C2ParallelScreenError(f"resume checkpoint at update {target} lacks strict-reload receipt")
    checkpoint_path = _resolve_artifact(
        receipt.get("path"), base=Path(arm_root), field=f"resume checkpoint {target}"
    )
    if _file_sha256(checkpoint_path) != _digest(
        receipt.get("file_sha256"), field=f"resume checkpoint {target}.file_sha256"
    ):
        raise C2ParallelScreenError(f"resume checkpoint digest drifted at update {target}")
    try:
        payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    except Exception as error:
        raise C2ParallelScreenError(f"resume checkpoint cannot be loaded at update {target}") from error
    if not isinstance(payload, Mapping):
        raise C2ParallelScreenError(f"resume checkpoint payload is malformed at update {target}")
    return payload


def _aggregate_policy(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise C2ParallelScreenError("cannot aggregate empty DESIGN-EVAL policy rows")
    bits = float(math.fsum(_nonnegative(row.get("total_bits"), field="total_bits") for row in rows))
    energy = float(math.fsum(_positive(row.get("total_energy_j"), field="total_energy_j") for row in rows))
    served = sum(_strict_int(row.get("served_user_steps"), field="served_user_steps") for row in rows)
    decisions = sum(_strict_int(row.get("decision_count"), field="decision_count", minimum=1) for row in rows)
    if served < 0 or served > decisions:
        raise C2ParallelScreenError("DESIGN-EVAL served count is malformed")
    return {
        "rows": len(rows),
        "decision_count": decisions,
        "served_user_steps": served,
        "served_fraction": served / decisions,
        "total_bits": bits,
        "total_energy_j": energy,
        "pooled_ratio_of_sums_ee_bits_per_j": bits / energy,
    }


def _positive(value: object, *, field: str) -> float:
    result = _finite(value, field=field)
    if result <= 0.0:
        raise C2ParallelScreenError(f"{field} must be strictly positive")
    return result


def _validate_design_row(
    row: Mapping[str, Any],
    *,
    candidate_id: str,
    update_count: int,
    phase_b_sha256: str | None = None,
) -> None:
    if row.get("schema") != ARM_EVAL_SCHEMA:
        raise C2ParallelScreenError("DESIGN-EVAL row schema drifted")
    if row.get("candidate_id") != candidate_id or row.get("checkpoint_update") != update_count:
        raise C2ParallelScreenError("DESIGN-EVAL candidate/update lineage drifted")
    if row.get("evaluation_split") != EVALUATION_SPLIT:
        raise C2ParallelScreenError("DESIGN-EVAL row crossed split boundary")
    _require_false(row, "test_split_opened", label="DESIGN-EVAL row")
    _require_false(row, "held_out_ee_evaluated", label="DESIGN-EVAL row")
    _require_false(row, "episode_training", label="DESIGN-EVAL row")
    seed = _strict_int(row.get("evaluation_seed"), field="evaluation_seed", minimum=1)
    if seed not in DESIGN_EVAL_SEEDS:
        raise C2ParallelScreenError("DESIGN-EVAL seed is outside the frozen block")
    policy = row.get("policy_label")
    if policy not in {"FULL", "DROP_C2", "MAIN"}:
        raise C2ParallelScreenError("DESIGN-EVAL policy label is invalid")
    if policy == "MAIN" and row.get("initialization_seed") is not None:
        raise C2ParallelScreenError("Main DESIGN-EVAL row must be initialization-independent")
    if policy != "MAIN" and row.get("initialization_seed") not in INITIALIZATION_SEEDS:
        raise C2ParallelScreenError("route DESIGN-EVAL row initialization is invalid")
    if row.get("steps") != STEPS_PER_EPISODE or row.get("users") != USERS:
        raise C2ParallelScreenError("DESIGN-EVAL dimensions drifted")
    components = row.get("fading_field_components")
    expected_components = [
        FIELD_COMPONENT,
        _digest(phase_b_sha256, field="phase_b_sha256") if phase_b_sha256 is not None else row.get("phase_b_sha256"),
        seed,
    ]
    if components != expected_components:
        raise C2ParallelScreenError("DESIGN-EVAL common-random-field components drifted")
    _digest(row.get("phase_b_sha256"), field="DESIGN-EVAL.phase_b_sha256")
    field_sha = _digest(row.get("fading_field_sha256"), field="fading_field_sha256")
    if field_sha != row.get("fading_field_sha256"):
        raise C2ParallelScreenError("DESIGN-EVAL fading-field receipt is malformed")
    decision_count = USERS * STEPS_PER_EPISODE
    if row.get("decision_count") != decision_count:
        raise C2ParallelScreenError("DESIGN-EVAL decision count drifted")
    _nonnegative(row.get("total_bits"), field="total_bits")
    energy = _positive(row.get("total_energy_j"), field="total_energy_j")
    bits = _nonnegative(row.get("total_bits"), field="total_bits")
    ee = _finite(row.get("ratio_of_sums_ee_bits_per_j"), field="ratio_of_sums_ee_bits_per_j")
    if not math.isclose(ee, bits / energy, rel_tol=1e-12, abs_tol=1e-12):
        raise C2ParallelScreenError("DESIGN-EVAL EE is not bits divided by energy")
    trace = row.get("actions")
    if not isinstance(trace, list) or len(trace) != STEPS_PER_EPISODE:
        raise C2ParallelScreenError("DESIGN-EVAL action trace is incomplete")
    if any(not isinstance(step, list) or len(step) != USERS for step in trace):
        raise C2ParallelScreenError("DESIGN-EVAL action trace dimensions drifted")
    actions_payload = {
        "schema": "multi-catfish-mcrl-v04-c2-parallel-action-trace-v1",
        "candidate_id": candidate_id,
        "checkpoint_update": update_count,
        "policy_label": policy,
        "initialization_seed": row.get("initialization_seed"),
        "evaluation_seed": seed,
        "actions": trace,
    }
    if _digest(row.get("action_trace_sha256"), field="action_trace_sha256") != canonical_sha256(actions_payload):
        raise C2ParallelScreenError("DESIGN-EVAL action trace digest drifted")
    flips = _strict_int(row.get("action_flip_count"), field="action_flip_count")
    if flips > decision_count:
        raise C2ParallelScreenError("DESIGN-EVAL action flip count exceeds decisions")
    flip_rate = _finite(row.get("action_flip_rate"), field="action_flip_rate")
    if not math.isclose(flip_rate, flips / decision_count, rel_tol=1e-12, abs_tol=1e-12):
        raise C2ParallelScreenError("DESIGN-EVAL action flip rate disagrees with count")
    if policy != "MAIN" and row.get("q2_surface_median_abs") is None:
        raise C2ParallelScreenError("candidate DESIGN-EVAL row lacks Q2 magnitude receipt")
    if policy == "FULL" and (
        row.get("q13_surface_median_abs") is None
        or row.get("q2_to_q13_magnitude") is None
    ):
        raise C2ParallelScreenError("FULL DESIGN-EVAL row lacks Q2-to-frozen-Q1+Q3 magnitude receipt")
    _nonnegative(row.get("q2_surface_median_abs") or 0.0, field="q2_surface_median_abs")
    if row.get("q13_surface_median_abs") is not None:
        _nonnegative(row.get("q13_surface_median_abs"), field="q13_surface_median_abs")
    if row.get("q2_to_q13_magnitude") is not None:
        _nonnegative(row.get("q2_to_q13_magnitude"), field="q2_to_q13_magnitude")


def _relabel_shared_eval_row(
    row: Mapping[str, Any],
    *,
    candidate_id: str,
    update_count: int,
) -> dict[str, Any]:
    """Bind a shared baseline episode to one arm/rung without rerunning it."""

    if row.get("policy_label") not in {"DROP_C2", "MAIN"}:
        raise C2ParallelScreenError("only shared DROP_C2/MAIN rows may be relabelled")
    output = dict(row)
    output["candidate_id"] = candidate_id
    output["checkpoint_update"] = update_count
    trace = output.get("actions")
    if not isinstance(trace, list):
        raise C2ParallelScreenError("shared baseline row has no action trace")
    output["action_trace_sha256"] = canonical_sha256(
        {
            "schema": "multi-catfish-mcrl-v04-c2-parallel-action-trace-v1",
            "candidate_id": candidate_id,
            "checkpoint_update": update_count,
            "policy_label": output["policy_label"],
            "initialization_seed": output.get("initialization_seed"),
            "evaluation_seed": output.get("evaluation_seed"),
            "actions": trace,
        }
    )
    return output


def aggregate_design_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    candidate_id: str,
    update_count: int,
    initialization_seeds: Sequence[int] = INITIALIZATION_SEEDS,
    phase_b_sha256: str | None = None,
) -> dict[str, Any]:
    """Aggregate paired FULL/DROP_C2/MAIN rows and apply the frozen arm gate."""

    for row in rows:
        _validate_design_row(
            row,
            candidate_id=candidate_id,
            update_count=update_count,
            phase_b_sha256=phase_b_sha256,
        )
    full = [row for row in rows if row.get("policy_label") == "FULL"]
    drop = [row for row in rows if row.get("policy_label") == "DROP_C2"]
    main = [row for row in rows if row.get("policy_label") == "MAIN"]
    seeds = tuple(initialization_seeds)
    expected_route = len(DESIGN_EVAL_SEEDS) * len(seeds)
    if len(full) != expected_route or len(drop) != expected_route or len(main) != len(DESIGN_EVAL_SEEDS):
        raise C2ParallelScreenError("DESIGN-EVAL rows do not contain the complete paired arm")
    full_keys = {(row.get("initialization_seed"), row.get("evaluation_seed")) for row in full}
    drop_keys = {(row.get("initialization_seed"), row.get("evaluation_seed")) for row in drop}
    if full_keys != drop_keys or len(full_keys) != expected_route:
        raise C2ParallelScreenError("FULL/DROP_C2 DESIGN-EVAL pairing is incomplete")
    main_by_world = {row.get("evaluation_seed"): row for row in main}
    if set(main_by_world) != set(DESIGN_EVAL_SEEDS):
        raise C2ParallelScreenError("MAIN DESIGN-EVAL world block is incomplete")
    full_summary = _aggregate_policy(full)
    drop_summary = _aggregate_policy(drop)
    main_summary_raw = _aggregate_policy(main)
    # Match the route arm's three initialization weight when contrasting Main.
    main_summary = dict(main_summary_raw)
    main_summary["total_bits"] *= len(seeds)
    main_summary["total_energy_j"] *= len(seeds)
    main_summary["pooled_ratio_of_sums_ee_bits_per_j"] = main_summary["total_bits"] / main_summary["total_energy_j"]
    per_initialization: dict[str, Any] = {}
    for seed in seeds:
        f_rows = [row for row in full if row.get("initialization_seed") == seed]
        d_rows = [row for row in drop if row.get("initialization_seed") == seed]
        f = _aggregate_policy(f_rows)
        d = _aggregate_policy(d_rows)
        f_ee = f["pooled_ratio_of_sums_ee_bits_per_j"]
        d_ee = d["pooled_ratio_of_sums_ee_bits_per_j"]
        per_initialization[str(seed)] = {
            "full": f,
            "drop_c2": d,
            "ee_difference_bits_per_j": f_ee - d_ee,
            "served_fraction_difference": f["served_fraction"] - d["served_fraction"],
            "delivered_bits_difference": f["total_bits"] - d["total_bits"],
        }
    per_world: list[dict[str, Any]] = []
    for world in DESIGN_EVAL_SEEDS:
        f_rows = [row for row in full if row.get("evaluation_seed") == world]
        d_rows = [row for row in drop if row.get("evaluation_seed") == world]
        f = _aggregate_policy(f_rows)
        d = _aggregate_policy(d_rows)
        m = _aggregate_policy([main_by_world[world]])
        shared = [*f_rows, *d_rows, main_by_world[world]]
        for field in (
            "initial_world_sha256",
            "start_epoch",
            "initial_state_sha256",
            "initial_mask_sha256",
            "fading_field_sha256",
            "fading_field_components",
        ):
            if len({json.dumps(row.get(field), sort_keys=True) for row in shared}) != 1:
                raise C2ParallelScreenError(
                    f"DESIGN-EVAL shared-world receipt drifted for {world}: {field}"
                )
        f_ee = f["pooled_ratio_of_sums_ee_bits_per_j"]
        d_ee = d["pooled_ratio_of_sums_ee_bits_per_j"]
        m_ee = m["pooled_ratio_of_sums_ee_bits_per_j"]
        per_world.append(
            {
                "evaluation_seed": world,
                "full_ee_bits_per_j": f_ee,
                "drop_c2_ee_bits_per_j": d_ee,
                "main_ee_bits_per_j": m_ee,
                "ee_difference_full_minus_drop_c2": f_ee - d_ee,
                "ee_difference_full_minus_main": f_ee - m_ee,
                "delivered_bits_difference": f["total_bits"] - d["total_bits"],
                "served_fraction_difference": f["served_fraction"] - d["served_fraction"],
            }
        )
    action_flip_counts = [
        _strict_int(row.get("action_flip_count"), field="action_flip_count") for row in full
    ]
    q2_magnitudes = [
        _nonnegative(row.get("q2_surface_median_abs"), field="q2_surface_median_abs")
        for row in full
        if row.get("q2_surface_median_abs") is not None
    ]
    q13_magnitudes = [
        _nonnegative(row.get("q13_surface_median_abs"), field="q13_surface_median_abs")
        for row in full
        if row.get("q13_surface_median_abs") is not None
    ]
    relative_magnitudes = [
        _nonnegative(row.get("q2_to_q13_magnitude"), field="q2_to_q13_magnitude")
        for row in full
        if row.get("q2_to_q13_magnitude") is not None
    ]
    checks = {
        "pooled_full_minus_drop_c2_positive": full_summary["pooled_ratio_of_sums_ee_bits_per_j"]
        > drop_summary["pooled_ratio_of_sums_ee_bits_per_j"],
        "at_least_two_initializations_full_minus_drop_c2_positive": sum(
            value["ee_difference_bits_per_j"] > 0.0 for value in per_initialization.values()
        ) >= 2,
        "at_least_two_initializations_delivered_bits_non_decreasing": sum(
            value["delivered_bits_difference"] >= 0.0 for value in per_initialization.values()
        ) >= 2,
        "no_invalid_action_flips": all(0 <= value <= USERS * STEPS_PER_EPISODE for value in action_flip_counts),
    }
    return {
        "candidate_id": candidate_id,
        "checkpoint_update": update_count,
        "phase_b_sha256": phase_b_sha256,
        "full": full_summary,
        "drop_c2": drop_summary,
        "main": main_summary,
        "per_initialization": per_initialization,
        "per_world": per_world,
        "action_flips": {
            "total": sum(action_flip_counts),
            "mean_rate": sum(action_flip_counts) / (len(action_flip_counts) * USERS * STEPS_PER_EPISODE),
        },
        "q2_surface_magnitude": {
            "median_abs": float(np.median(q2_magnitudes)) if q2_magnitudes else None,
            "q13_median_abs": float(np.median(q13_magnitudes)) if q13_magnitudes else None,
            "relative_to_frozen_q1_plus_q3": (
                float(np.median(relative_magnitudes)) if relative_magnitudes else None
            ),
        },
        "checks": checks,
        "design_positive": bool(all(checks.values())),
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }


def _load_runtime_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise C2ParallelScreenError(f"cannot import runtime module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _production_modules() -> dict[str, ModuleType]:
    return {
        "screen": _load_runtime_module(
            "mcrl_v04_c2_parallel_screen_c3_screen",
            HERE / "run_v04_c3_500_update_screen.py",
        ),
        "five": _load_runtime_module(
            "mcrl_v04_c2_parallel_screen_five",
            HERE / "run_v04_five_arm_ablation.py",
        ),
        "source": _load_runtime_module(
            "mcrl_v04_c2_parallel_screen_source",
            HERE / "run_v04_c3_source.py",
        ),
        "loader": _load_runtime_module(
            "mcrl_v04_c2_parallel_screen_loader",
            REPO / "scripts" / "run_head_pivotality_probe.py",
        ),
    }


def _phase_b_gate_binding(phase_b: Mapping[str, Any], gate: Mapping[str, Any]) -> None:
    """Require the selected Q1+Q3 gate to be the one sealed into Phase B."""

    checks = (
        ("selected_q3_rung", 100),
        ("authority_sha256", phase_b["result"].get("q13_gate_authority_sha256")),
        ("result_file_sha256", phase_b["result"].get("q13_gate_result_file_sha256")),
        ("source_manifest_sha256", phase_b["result"].get("q13_gate_source_manifest_sha256")),
        ("schedule_sha256", phase_b["result"].get("q13_gate_schedule_sha256")),
    )
    for field, expected in checks:
        observed = gate.get(field)
        if observed != expected:
            raise C2ParallelScreenError(f"Q1+Q3 gate lineage mismatch in {field}")


def _authenticate_frozen_source_gate(
    *,
    screen_module: ModuleType,
    gate_dir: Path,
    c3_source_dir: Path,
    prereg_path: Path,
) -> dict[str, Any]:
    """Authenticate the sealed gate against its frozen source manifest only.

    The gate receipt is deliberately consumed through ``source_dir=None``.
    The current checkout's C3 source closure may have advanced after the gate
    was sealed; reopening it here would invalidate an otherwise authenticated
    selected Q1+Q3 checkpoint.  We still read the frozen manifest bytes,
    verify its canonical self-digest, and require the gate receipt to carry
    exactly that manifest digest, matching the Phase-B authority seam.
    """

    source_root = _regular_dir(c3_source_dir, field="c3_source_dir")
    frozen_source, frozen_source_file_sha = _read_json(
        source_root / "source-manifest.json"
    )
    frozen_source_body = dict(frozen_source)
    frozen_source_sha = _digest(
        frozen_source_body.pop("source_manifest_sha256", None),
        field="frozen_source.source_manifest_sha256",
    )
    if canonical_sha256(frozen_source_body) != frozen_source_sha:
        raise C2ParallelScreenError("frozen C3 source manifest digest is invalid")
    try:
        receipt = screen_module.authenticate_gate(
            Path(gate_dir), source_dir=None, prereg_path=Path(prereg_path)
        )
    except Exception as error:
        raise C2ParallelScreenError("sealed Q1+Q3 gate authentication failed") from error
    if receipt.get("source_manifest_sha256") != frozen_source_sha:
        raise C2ParallelScreenError(
            "frozen C3 source manifest is not bound to the sealed Q1+Q3 gate"
        )
    return receipt | {
        "frozen_source_manifest_file_sha256": frozen_source_file_sha,
        "frozen_source_manifest_sha256": frozen_source_sha,
    }


def _require_regular_path(path: Path, *, field: str, directory: bool) -> Path:
    source = Path(path)
    resolved = source.resolve()
    if source.is_symlink() or (not source.is_dir() if directory else not source.is_file()):
        raise C2ParallelScreenError(f"{field} is missing or non-regular: {source}")
    return resolved


def prepare_screen(
    *,
    phase_b_dir: Path = DEFAULT_PHASE_B_DIR,
    phase_a_dir: Path = DEFAULT_PHASE_A_DIR,
    gate_dir: Path = DEFAULT_GATE_DIR,
    c3_source_dir: Path = DEFAULT_C3_SOURCE_DIR,
    v03_root: Path = DEFAULT_V03_ROOT,
    prereg_path: Path = DEFAULT_PREREG,
    tle_root: Path = DEFAULT_TLE_ROOT,
    main_dir: Path = DEFAULT_MAIN_DIR,
    output_dir: Path = DEFAULT_PREPARE_DIR,
) -> dict[str, Any]:
    """Seal the pre-episode DESIGN-EVAL contract without opening episodes."""

    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite C2 screen prepare receipt: {destination}")
    phase_b = authenticate_phase_b(Path(phase_b_dir), phase_a_dir=Path(phase_a_dir))
    modules = _production_modules()
    gate = _authenticate_frozen_source_gate(
        screen_module=modules["screen"],
        gate_dir=Path(gate_dir),
        c3_source_dir=Path(c3_source_dir),
        prereg_path=Path(prereg_path),
    )
    _phase_b_gate_binding(phase_b, gate)
    prereg = _require_regular_path(Path(prereg_path), field="prereg_path", directory=False)
    paths = {
        "phase_b_dir": str(Path(phase_b_dir).resolve()),
        "phase_a_dir": str(Path(phase_a_dir).resolve()),
        "gate_dir": str(Path(gate_dir).resolve()),
        "c3_source_dir": str(Path(c3_source_dir).resolve()),
        "v03_root": str(Path(v03_root).resolve()),
        "prereg_path": str(prereg),
        "tle_root": str(Path(tle_root).resolve()),
        "main_dir": str(Path(main_dir).resolve()),
    }
    eligible = list(phase_b["eligible_arms"])
    payload = {
        "schema": PREPARE_SCHEMA,
        "status": "PREPARED" if eligible else "NO_ELIGIBLE_ARMS",
        "claim_ceiling": CLAIM_CEILING,
        "phase_b_sha256": phase_b["phase_b_sha256"],
        "phase_b_result_file_sha256": phase_b["result_file_sha256"],
        "phase_b_seal_file_sha256": phase_b["seal_file_sha256"],
        "eligible_arms": eligible,
        "initialization_seeds": list(INITIALIZATION_SEEDS),
        "update_ladder": list(UPDATE_LADDER),
        "checkpoint_every": CHECKPOINT_EVERY,
        "evaluation_split": EVALUATION_SPLIT,
        "design_eval_seeds": list(DESIGN_EVAL_SEEDS),
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "episode_budget": expected_design_eval_episodes(len(eligible)),
        "field_components": [FIELD_COMPONENT, phase_b["phase_b_sha256"], "evaluation_seed"],
        "gate_binding": {
            "authority_sha256": gate["authority_sha256"],
            "authority_file_sha256": gate["authority_file_sha256"],
            "result_file_sha256": gate["result_file_sha256"],
            "source_manifest_sha256": gate["source_manifest_sha256"],
            "schedule_sha256": gate["schedule_sha256"],
            "selected_q3_rung": gate["selected_q3_rung"],
            "selected_hybrid_file_sha256": gate["result"].get("selected_hybrids"),
        },
        "prereg_file_sha256": _file_sha256(prereg),
        "paths": paths,
        "counterfactual_outcomes_evaluated": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }
    result_sha = _write_once_json(destination / "prepare.json", payload)
    seal_sha = _write_once_json(
        destination / "prepare-seal.json",
        {
            "schema": PREPARE_SEAL_SCHEMA,
            "status": payload["status"],
            "prepare_file_sha256": result_sha,
            "phase_b_sha256": phase_b["phase_b_sha256"],
            "eligible_arms": eligible,
            "episode_budget": payload["episode_budget"],
            "counterfactual_outcomes_evaluated": False,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "episode_training": False,
        },
    )
    return {
        "schema": PREPARE_SCHEMA,
        "status": payload["status"],
        "prepare_file_sha256": result_sha,
        "prepare_seal_file_sha256": seal_sha,
        "phase_b_sha256": phase_b["phase_b_sha256"],
        "eligible_arms": eligible,
        "episode_budget": payload["episode_budget"],
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }


def authenticate_prepare(path: Path, *, phase_b: Mapping[str, Any]) -> dict[str, Any]:
    root = _regular_dir(path, field="prepare_dir")
    payload, payload_sha = _read_json(root / "prepare.json")
    seal, seal_sha = _read_json(root / "prepare-seal.json")
    binding = payload.get("gate_binding")
    if not isinstance(binding, Mapping):
        raise C2ParallelScreenError("prepare gate binding is missing")
    phase_b_result = phase_b.get("result", phase_b)
    if not isinstance(phase_b_result, Mapping):
        raise C2ParallelScreenError("Phase-B result binding is missing")
    for field in (
        "authority_sha256",
        "authority_file_sha256",
        "result_file_sha256",
        "source_manifest_sha256",
        "schedule_sha256",
    ):
        _digest(binding.get(field), field=f"prepare.gate_binding.{field}")
    if (
        binding.get("authority_sha256") != phase_b_result.get("q13_gate_authority_sha256")
        or binding.get("result_file_sha256") != phase_b_result.get("q13_gate_result_file_sha256")
        or binding.get("source_manifest_sha256") != phase_b_result.get("q13_gate_source_manifest_sha256")
        or binding.get("schedule_sha256") != phase_b_result.get("q13_gate_schedule_sha256")
        or binding.get("selected_q3_rung") != 100
    ):
        raise C2ParallelScreenError("prepare gate binding disagrees with Phase-B authority")
    _digest(payload.get("prereg_file_sha256"), field="prepare.prereg_file_sha256")
    if (
        payload.get("schema") != PREPARE_SCHEMA
        or payload.get("claim_ceiling") != CLAIM_CEILING
        or payload.get("phase_b_sha256") != phase_b["phase_b_sha256"]
        or payload.get("eligible_arms") != list(phase_b["eligible_arms"])
        or payload.get("initialization_seeds") != list(INITIALIZATION_SEEDS)
        or payload.get("update_ladder") != list(UPDATE_LADDER)
        or payload.get("checkpoint_every") != CHECKPOINT_EVERY
        or payload.get("evaluation_split") != EVALUATION_SPLIT
        or payload.get("design_eval_seeds") != list(DESIGN_EVAL_SEEDS)
        or payload.get("users") != USERS
        or payload.get("steps_per_episode") != STEPS_PER_EPISODE
        or payload.get("episode_budget") != expected_design_eval_episodes(len(phase_b["eligible_arms"]))
        or payload.get("field_components") != [FIELD_COMPONENT, phase_b["phase_b_sha256"], "evaluation_seed"]
        or payload.get("counterfactual_outcomes_evaluated") is not False
        or payload.get("test_split_opened") is not False
        or payload.get("held_out_ee_evaluated") is not False
        or payload.get("episode_training") is not False
        or seal.get("schema") != PREPARE_SEAL_SCHEMA
        or seal.get("prepare_file_sha256") != payload_sha
        or seal.get("phase_b_sha256") != phase_b["phase_b_sha256"]
        or seal.get("eligible_arms") != payload.get("eligible_arms")
        or seal.get("episode_budget") != payload.get("episode_budget")
        or seal.get("counterfactual_outcomes_evaluated") is not False
        or seal.get("test_split_opened") is not False
        or seal.get("held_out_ee_evaluated") is not False
        or seal.get("episode_training") is not False
    ):
        raise C2ParallelScreenError("prepare receipt is not an authenticated pre-episode contract")
    return {
        "dir": root,
        "payload": payload,
        "payload_file_sha256": payload_sha,
        "seal": seal,
        "seal_file_sha256": seal_sha,
    }


def _design_field(seed: int, phase_b_sha256: str) -> Any:
    from mcrl.env.keyed_fading import KeyedFadingField

    return KeyedFadingField.from_components(FIELD_COMPONENT, phase_b_sha256, seed)


def _episode_row(
    *,
    candidate_id: str,
    checkpoint_update: int,
    policy_label: str,
    initialization_seed: int | None,
    evaluation_seed: int,
    phase_b_sha256: str,
    field: Any,
    start_epoch: str,
    initial_world_sha256: str,
    initial_state_sha256: str,
    initial_mask_sha256: str,
    actions: Sequence[Sequence[int]],
    total_bits: float,
    total_energy_j: float,
    served_user_steps: int,
    q2_magnitude_samples: Sequence[float] = (),
    q13_magnitude_samples: Sequence[float] = (),
) -> dict[str, Any]:
    decision_count = USERS * STEPS_PER_EPISODE
    if len(actions) != STEPS_PER_EPISODE or any(len(step) != USERS for step in actions):
        raise C2ParallelScreenError("DESIGN-EVAL action trace has wrong dimensions")
    if any(type(action) is not int or action < 0 or action >= ACTION_DIM for step in actions for action in step):
        raise C2ParallelScreenError("DESIGN-EVAL action trace contains an invalid action")
    phase_b_digest = _digest(phase_b_sha256, field="phase_b_sha256")
    q2_samples = [_finite(value, field="q2_magnitude") for value in q2_magnitude_samples]
    q13_samples = [_finite(value, field="q13_magnitude") for value in q13_magnitude_samples]
    return {
        "schema": ARM_EVAL_SCHEMA,
        "candidate_id": candidate_id,
        "checkpoint_update": checkpoint_update,
        "phase_b_sha256": phase_b_digest,
        "policy_label": policy_label,
        "initialization_seed": initialization_seed,
        "evaluation_seed": evaluation_seed,
        "evaluation_split": EVALUATION_SPLIT,
        "steps": STEPS_PER_EPISODE,
        "users": USERS,
        "decision_count": decision_count,
        "start_epoch": start_epoch,
        "initial_world_sha256": initial_world_sha256,
        "initial_state_sha256": initial_state_sha256,
        "initial_mask_sha256": initial_mask_sha256,
        "fading_field_sha256": field.root_digest,
        "fading_field_components": [FIELD_COMPONENT, phase_b_digest, evaluation_seed],
        "actions": [[int(value) for value in step] for step in actions],
        "action_trace_sha256": canonical_sha256(
            {
                "schema": "multi-catfish-mcrl-v04-c2-parallel-action-trace-v1",
                "candidate_id": candidate_id,
                "checkpoint_update": checkpoint_update,
                "policy_label": policy_label,
                "initialization_seed": initialization_seed,
                "evaluation_seed": evaluation_seed,
                "actions": actions,
            }
        ),
        "total_bits": float(total_bits),
        "total_energy_j": float(total_energy_j),
        "ratio_of_sums_ee_bits_per_j": float(total_bits / total_energy_j),
        "served_user_steps": int(served_user_steps),
        "q2_surface_median_abs": float(np.median(q2_samples)) if q2_samples else None,
        "q13_surface_median_abs": float(np.median(q13_samples)) if q13_samples else None,
        "q2_to_q13_magnitude": (
            float(np.median(q2_samples) / np.median(q13_samples))
            if q2_samples and q13_samples and float(np.median(q13_samples)) > 0.0
            else None
        ),
        "action_flip_count": 0,
        "action_flip_rate": 0.0,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }


def _candidate_episode(
    *,
    screen_module: ModuleType,
    hybrid: Any,
    candidate: EEAxisV04C2Trainer,
    archive: Any,
    field: Any,
    phase_b_sha256: str,
    evaluation_seed: int,
    checkpoint_update: int,
    candidate_id: str,
    drop_c2: bool,
) -> dict[str, Any]:
    from mcrl.runtime.ee_axis_state import encode_ee_axis_state
    from mcrl.runtime.ee_axis_v04_c3_state import encode_ee_axis_v04_c3_state

    environment = screen_module._make_environment(archive, users=USERS)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = screen_module._evaluation_rngs(evaluation_seed)
    states, masks, observation = environment.reset(env_rng, mobility_rng)
    interval_s = float(environment.environment.driver.config.ephemeris.time_step_s)
    kappa_bits = float(hybrid.v04_config.kappa_bits)
    first_legacy = encode_ee_axis_state(environment.environment, observation)
    first_v04 = encode_ee_axis_v04_c3_state(
        environment.environment, observation, interval_s=interval_s, kappa_bits=kappa_bits
    )
    initial_state_sha = _array_sha256(first_legacy.state_matrix, first_v04.state_matrix)
    initial_mask_sha = _array_sha256(first_v04.action_masks)
    start_epoch = str(environment.epoch.isoformat())
    initial_world_sha = canonical_sha256(
        {"start_epoch": start_epoch, "initial_state_sha256": initial_state_sha, "initial_mask_sha256": initial_mask_sha}
    )
    actions_trace: list[list[int]] = []
    total_bits = 0.0
    total_energy = 0.0
    served = 0
    steps = 0
    q2_magnitude_samples: list[float] = []
    q13_magnitude_samples: list[float] = []
    with torch.no_grad():
        while True:
            legacy = encode_ee_axis_state(environment.environment, observation)
            v04 = encode_ee_axis_v04_c3_state(
                environment.environment, observation, interval_s=interval_s, kappa_bits=kappa_bits
            )
            q1, _old_q2, q3 = hybrid.q_values_by_route(
                np.asarray(legacy.state_matrix), np.asarray(v04.state_matrix), np.asarray(v04.action_masks)
            )
            q2 = candidate.q2_values(np.asarray(legacy.state_matrix), np.asarray(v04.action_masks))
            q2_magnitude_samples.append(float(np.median(np.abs(q2))))
            q13_magnitude_samples.append(float(np.median(np.abs(q1 + q3))))
            scores = q1 + q3 + (0.0 if drop_c2 else q2)
            legal = np.asarray(v04.action_masks, dtype=np.bool_)
            actions = np.argmax(np.where(legal, scores, -np.inf), axis=1).astype(np.int64)
            actions_trace.append(actions.tolist())
            result = environment.step(actions, env_rng)
            outcome = environment.last_outcome
            rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
            power = float(outcome.system_power_w)
            if (
                rates.shape != (USERS,)
                or not np.all(np.isfinite(rates))
                or np.any(rates < 0.0)
                or not math.isfinite(power)
                or power < 0.0
            ):
                raise C2ParallelScreenError("DESIGN-EVAL physical output is malformed")
            total_bits += float(math.fsum(float(value) for value in rates)) * interval_s
            total_energy += power * interval_s
            served += int(outcome.resolution.served_count)
            steps += 1
            if result.done:
                break
            observation = outcome.observation
    if steps != STEPS_PER_EPISODE or total_energy <= 0.0:
        raise C2ParallelScreenError("DESIGN-EVAL episode did not close at the frozen horizon")
    return _episode_row(
        candidate_id=candidate_id,
        checkpoint_update=checkpoint_update,
        policy_label="DROP_C2" if drop_c2 else "FULL",
        initialization_seed=candidate.train_seed,
        evaluation_seed=evaluation_seed,
        phase_b_sha256=phase_b_sha256,
        field=field,
        start_epoch=start_epoch,
        initial_world_sha256=initial_world_sha,
        initial_state_sha256=initial_state_sha,
        initial_mask_sha256=initial_mask_sha,
        actions=actions_trace,
        total_bits=total_bits,
        total_energy_j=total_energy,
        served_user_steps=served,
        q2_magnitude_samples=q2_magnitude_samples,
        q13_magnitude_samples=q13_magnitude_samples,
    )


def _main_episode(
    *,
    screen_module: ModuleType,
    source_module: ModuleType,
    main_trainer: Any,
    archive: Any,
    field: Any,
    phase_b_sha256: str,
    evaluation_seed: int,
    candidate_id: str,
    checkpoint_update: int,
) -> dict[str, Any]:
    from mcrl.runtime.ee_axis_state import encode_ee_axis_state
    from mcrl.runtime.ee_axis_v04_c3_state import encode_ee_axis_v04_c3_state

    environment = screen_module._make_environment(archive, users=USERS)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = screen_module._evaluation_rngs(evaluation_seed)
    states, masks, observation = environment.reset(env_rng, mobility_rng)
    interval_s = float(environment.environment.driver.config.ephemeris.time_step_s)
    kappa_bits = float(
        getattr(getattr(main_trainer, "v04_config", None), "kappa_bits", 10_097_071_012.757404)
    )
    first_legacy = encode_ee_axis_state(environment.environment, observation)
    first_v04 = encode_ee_axis_v04_c3_state(
        environment.environment, observation, interval_s=interval_s, kappa_bits=kappa_bits
    )
    initial_state_sha = _array_sha256(first_legacy.state_matrix, first_v04.state_matrix)
    initial_mask_sha = _array_sha256(first_v04.action_masks)
    start_epoch = str(environment.epoch.isoformat())
    initial_world_sha = canonical_sha256(
        {"start_epoch": start_epoch, "initial_state_sha256": initial_state_sha, "initial_mask_sha256": initial_mask_sha}
    )
    actions_trace: list[list[int]] = []
    total_bits = 0.0
    total_energy = 0.0
    served = 0
    steps = 0
    before_networks = source_module._network_snapshot(main_trainer)
    before_replay = source_module._replay_size(main_trainer)
    with torch.no_grad():
        while True:
            actions = np.asarray(
                source_module._main_decision(main_trainer, environment, states, masks, observation, env_rng),
                dtype=np.int64,
            )
            actions_trace.append(actions.tolist())
            result = environment.step(actions, env_rng)
            outcome = environment.last_outcome
            rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
            power = float(outcome.system_power_w)
            if (
                rates.shape != (USERS,)
                or not np.all(np.isfinite(rates))
                or np.any(rates < 0.0)
                or not math.isfinite(power)
                or power < 0.0
            ):
                raise C2ParallelScreenError("Main DESIGN-EVAL physical output is malformed")
            total_bits += float(math.fsum(float(value) for value in rates)) * interval_s
            total_energy += power * interval_s
            served += int(outcome.resolution.served_count)
            steps += 1
            if result.done:
                break
            states = result.user_states
            masks = result.action_masks
            observation = outcome.observation
    if not source_module._networks_equal(main_trainer, before_networks) or source_module._replay_size(main_trainer) != before_replay:
        raise C2ParallelScreenError("Main changed during DESIGN-EVAL")
    if steps != STEPS_PER_EPISODE or total_energy <= 0.0:
        raise C2ParallelScreenError("Main DESIGN-EVAL episode did not close")
    return _episode_row(
        candidate_id=candidate_id,
        checkpoint_update=checkpoint_update,
        policy_label="MAIN",
        initialization_seed=None,
        evaluation_seed=evaluation_seed,
        phase_b_sha256=phase_b_sha256,
        field=field,
        start_epoch=start_epoch,
        initial_world_sha256=initial_world_sha,
        initial_state_sha256=initial_state_sha,
        initial_mask_sha256=initial_mask_sha,
        actions=actions_trace,
        total_bits=total_bits,
        total_energy_j=total_energy,
        served_user_steps=served,
    )


def run_shared_baseline(
    *,
    prepare_dir: Path = DEFAULT_PREPARE_DIR,
    phase_b_dir: Path = DEFAULT_PHASE_B_DIR,
    phase_a_dir: Path = DEFAULT_PHASE_A_DIR,
    gate_dir: Path = DEFAULT_GATE_DIR,
    c3_source_dir: Path = DEFAULT_C3_SOURCE_DIR,
    v03_root: Path = DEFAULT_V03_ROOT,
    prereg_path: Path = DEFAULT_PREREG,
    tle_root: Path = DEFAULT_TLE_ROOT,
    main_dir: Path = DEFAULT_MAIN_DIR,
    output_dir: Path = DEFAULT_BASELINE_DIR,
) -> dict[str, Any]:
    """Materialize the shared 30 DROP-C2 + 10 Main DESIGN-EVAL controls.

    The controls are intentionally run once and reused by every candidate and
    rung.  This is what makes the amendment's maximum budget 310 episodes,
    rather than silently multiplying controls by nine arm/lineage cells.
    """

    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite shared baseline: {destination}")
    phase_b = authenticate_phase_b(Path(phase_b_dir), phase_a_dir=Path(phase_a_dir))
    prepared = authenticate_prepare(Path(prepare_dir), phase_b=phase_b)
    eligible = tuple(phase_b["eligible_arms"])
    if not eligible:
        raise C2ParallelScreenError("cannot materialize DESIGN-EVAL controls without an eligible C2 arm")
    modules = _production_modules()
    screen_module = modules["screen"]
    _candidate_type, trainer_type, _candidate_specs, _config_type = _c2_algorithm_types()
    gate_receipt = _authenticate_frozen_source_gate(
        screen_module=screen_module,
        gate_dir=Path(gate_dir),
        c3_source_dir=Path(c3_source_dir),
        prereg_path=Path(prereg_path),
    )
    _phase_b_gate_binding(phase_b, gate_receipt)
    from mcrl.runtime.prereg import read_prereg

    record = read_prereg(Path(prereg_path))
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="mcrl-v04-c2-screen-baseline-tle-") as temporary:
        archive = screen_module._frozen_archive(
            record, Path(tle_root), Path(temporary) / "frozen-tle"
        )
        record_module = modules["loader"]
        main_trainer, _main_receipt = record_module._verify_and_load_trainer(
            record, archive, run_dir=Path(main_dir), users=USERS
        )
        before_networks = modules["source"]._network_snapshot(main_trainer)
        before_replay = modules["source"]._replay_size(main_trainer)
        for initialization_seed in INITIALIZATION_SEEDS:
            frozen_hybrid = screen_module.load_gate_selected_hybrid(
                gate_receipt,
                v03_root=Path(v03_root),
                initialization_seed=initialization_seed,
            )
            # Q2 is not consulted by DROP-C2, but using the exact frozen config
            # keeps the evaluator's state/mask path identical to an arm.
            drop_trainer = trainer_type(
                frozen_hybrid.v03_config,
                candidate=_candidate_spec(C2_MAIN_VALUE),
                train_seed=initialization_seed,
            )
            for evaluation_seed in DESIGN_EVAL_SEEDS:
                field = _design_field(evaluation_seed, str(phase_b["phase_b_sha256"]))
                rows.append(
                    _candidate_episode(
                        screen_module=screen_module,
                        hybrid=frozen_hybrid,
                        candidate=drop_trainer,
                        archive=archive,
                        field=field,
                        phase_b_sha256=str(phase_b["phase_b_sha256"]),
                        evaluation_seed=evaluation_seed,
                        checkpoint_update=0,
                        candidate_id=SHARED_BASELINE_CANDIDATE,
                        drop_c2=True,
                    )
                )
        for evaluation_seed in DESIGN_EVAL_SEEDS:
            field = _design_field(evaluation_seed, str(phase_b["phase_b_sha256"]))
            rows.append(
                _main_episode(
                    screen_module=screen_module,
                    source_module=modules["source"],
                    main_trainer=main_trainer,
                    archive=archive,
                    field=field,
                    phase_b_sha256=str(phase_b["phase_b_sha256"]),
                    evaluation_seed=evaluation_seed,
                    candidate_id=SHARED_BASELINE_CANDIDATE,
                    checkpoint_update=0,
                )
            )
        if not modules["source"]._networks_equal(main_trainer, before_networks) or modules["source"]._replay_size(main_trainer) != before_replay:
            raise C2ParallelScreenError("Main changed while materializing shared DESIGN-EVAL controls")
    if len(rows) != 40:
        raise C2ParallelScreenError("shared DESIGN-EVAL controls must contain exactly 40 rows")
    rows_sha = canonical_sha256(rows)
    payload = {
        "schema": BASELINE_SCHEMA,
        "status": "SHARED_BASELINE_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "phase_b_sha256": phase_b["phase_b_sha256"],
        "phase_b_result_file_sha256": phase_b["result_file_sha256"],
        "prepare_file_sha256": prepared["payload_file_sha256"],
        "eligible_arms": list(eligible),
        "initialization_seeds": list(INITIALIZATION_SEEDS),
        "evaluation_split": EVALUATION_SPLIT,
        "design_eval_seeds": list(DESIGN_EVAL_SEEDS),
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "episode_count": 40,
        "rows_sha256": rows_sha,
        "rows": rows,
        "counterfactual_outcomes_evaluated": True,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
        "elapsed_s": time.perf_counter() - started,
    }
    result_sha = _write_once_json(destination / "baseline.json", payload)
    seal_sha = _write_once_json(
        destination / "baseline-seal.json",
        {
            "schema": BASELINE_SEAL_SCHEMA,
            "status": "SHARED_BASELINE_COMPLETE",
            "baseline_file_sha256": result_sha,
            "phase_b_sha256": phase_b["phase_b_sha256"],
            "rows_sha256": rows_sha,
            "episode_count": 40,
            "counterfactual_outcomes_evaluated": True,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "episode_training": False,
        },
    )
    return {
        "schema": BASELINE_SCHEMA,
        "status": "SHARED_BASELINE_COMPLETE",
        "baseline_file_sha256": result_sha,
        "baseline_seal_file_sha256": seal_sha,
        "phase_b_sha256": phase_b["phase_b_sha256"],
        "episode_count": 40,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }


def authenticate_shared_baseline(
    path: Path, *, phase_b: Mapping[str, Any], prepare: Mapping[str, Any]
) -> dict[str, Any]:
    root = _regular_dir(path, field="baseline_dir")
    payload, payload_sha = _read_json(root / "baseline.json")
    seal, seal_sha = _read_json(root / "baseline-seal.json")
    rows = payload.get("rows")
    if (
        payload.get("schema") != BASELINE_SCHEMA
        or payload.get("status") != "SHARED_BASELINE_COMPLETE"
        or payload.get("claim_ceiling") != CLAIM_CEILING
        or payload.get("phase_b_sha256") != phase_b["phase_b_sha256"]
        or payload.get("prepare_file_sha256") != prepare["payload_file_sha256"]
        or payload.get("eligible_arms") != list(phase_b["eligible_arms"])
        or payload.get("initialization_seeds") != list(INITIALIZATION_SEEDS)
        or payload.get("evaluation_split") != EVALUATION_SPLIT
        or payload.get("design_eval_seeds") != list(DESIGN_EVAL_SEEDS)
        or payload.get("users") != USERS
        or payload.get("steps_per_episode") != STEPS_PER_EPISODE
        or payload.get("episode_count") != 40
        or payload.get("rows_sha256") != canonical_sha256(rows)
        or payload.get("counterfactual_outcomes_evaluated") is not True
        or payload.get("test_split_opened") is not False
        or payload.get("held_out_ee_evaluated") is not False
        or payload.get("episode_training") is not False
        or seal.get("schema") != BASELINE_SEAL_SCHEMA
        or seal.get("baseline_file_sha256") != payload_sha
        or seal.get("phase_b_sha256") != phase_b["phase_b_sha256"]
        or seal.get("rows_sha256") != payload.get("rows_sha256")
        or seal.get("episode_count") != 40
        or seal.get("counterfactual_outcomes_evaluated") is not True
        or seal.get("test_split_opened") is not False
        or seal.get("held_out_ee_evaluated") is not False
        or seal.get("episode_training") is not False
    ):
        raise C2ParallelScreenError("shared baseline receipt is not authenticated")
    if not isinstance(rows, list) or len(rows) != 40:
        raise C2ParallelScreenError("shared baseline row count is not exactly 40")
    full = [row for row in rows if isinstance(row, Mapping) and row.get("policy_label") == "FULL"]
    drop = [row for row in rows if isinstance(row, Mapping) and row.get("policy_label") == "DROP_C2"]
    main = [row for row in rows if isinstance(row, Mapping) and row.get("policy_label") == "MAIN"]
    if full or len(drop) != 30 or len(main) != 10:
        raise C2ParallelScreenError("shared baseline must contain 30 DROP_C2 and 10 Main rows only")
    for row in rows:
        if not isinstance(row, Mapping):
            raise C2ParallelScreenError("shared baseline row is malformed")
        _validate_design_row(
            row,
            candidate_id=SHARED_BASELINE_CANDIDATE,
            update_count=0,
            phase_b_sha256=str(phase_b["phase_b_sha256"]),
        )
    return {
        "dir": root,
        "payload": payload,
        "payload_file_sha256": payload_sha,
        "seal": seal,
        "seal_file_sha256": seal_sha,
        "rows": tuple(rows),
    }


def _attach_action_flips(full: Mapping[str, Any], drop: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if full.get("evaluation_seed") != drop.get("evaluation_seed") or full.get("initialization_seed") != drop.get("initialization_seed"):
        raise C2ParallelScreenError("FULL/DROP_C2 action pair identity drifted")
    for field in (
        "initial_world_sha256",
        "start_epoch",
        "initial_state_sha256",
        "initial_mask_sha256",
        "fading_field_sha256",
        "fading_field_components",
    ):
        if full.get(field) != drop.get(field):
            raise C2ParallelScreenError(f"FULL/DROP_C2 shared-world receipt drifted: {field}")
    full_copy = dict(full)
    drop_copy = dict(drop)
    full_actions = full.get("actions")
    drop_actions = drop.get("actions")
    if not isinstance(full_actions, list) or not isinstance(drop_actions, list):
        raise C2ParallelScreenError("FULL/DROP_C2 action trace is missing")
    flips = sum(
        int(a != b)
        for full_step, drop_step in zip(full_actions, drop_actions, strict=True)
        for a, b in zip(full_step, drop_step, strict=True)
    )
    rate = flips / (USERS * STEPS_PER_EPISODE)
    full_copy["action_flip_count"] = flips
    full_copy["action_flip_rate"] = rate
    drop_copy["action_flip_count"] = flips
    drop_copy["action_flip_rate"] = rate
    return full_copy, drop_copy


def _load_candidate_hybrid(
    *,
    screen_module: ModuleType,
    gate_receipt: Mapping[str, Any],
    v03_root: Path,
    candidate_trainer: EEAxisV04C2Trainer,
    seed: int,
) -> Any:
    frozen = screen_module.load_gate_selected_hybrid(
        gate_receipt, v03_root=Path(v03_root), initialization_seed=seed
    )
    from mcrl.algorithms.ee_axis_v04_hybrid import EEAxisV04HybridTrainer

    hybrid = EEAxisV04HybridTrainer(
        q1=copy.deepcopy(frozen.q1),
        q2=copy.deepcopy(candidate_trainer.q2),
        v03_config=frozen.v03_config,
        v04_config=frozen.v04_config,
        initialization_seed=seed,
        selected_q3_rung=frozen.selected_q3_rung,
        frozen_lineage=frozen.frozen_lineage,
    )
    hybrid.q3.load_state_dict(copy.deepcopy(frozen.q3.state_dict()), strict=True)
    hybrid.q3.eval()
    return hybrid


def run_arm(
    *,
    prepare_dir: Path = DEFAULT_PREPARE_DIR,
    baseline_dir: Path = DEFAULT_BASELINE_DIR,
    phase_b_dir: Path = DEFAULT_PHASE_B_DIR,
    phase_a_dir: Path = DEFAULT_PHASE_A_DIR,
    gate_dir: Path = DEFAULT_GATE_DIR,
    c3_source_dir: Path = DEFAULT_C3_SOURCE_DIR,
    v03_root: Path = DEFAULT_V03_ROOT,
    prereg_path: Path = DEFAULT_PREREG,
    tle_root: Path = DEFAULT_TLE_ROOT,
    main_dir: Path = DEFAULT_MAIN_DIR,
    candidate_id: str,
    initialization_seed: int,
    target_update: int = UPDATE_LADDER[-1],
    output_dir: Path,
) -> dict[str, Any]:
    """Run one candidate/initialization lineage through one staged rung.

    The 100-rung invocation starts a deterministic learner.  A later rung is
    admissible only when its same-arm preceding receipt authenticates and its
    preceding checkpoint is loaded; no earlier updates are replayed.
    """

    target_update = _target_update(target_update)
    prior_update = _prior_update(target_update)
    destination = Path(output_dir)
    if target_update == UPDATE_LADDER[0]:
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"refusing to overwrite fresh C2 screen arm: {destination}")
    elif destination.is_symlink() or not destination.is_dir():
        raise C2ParallelScreenError(
            f"resume target {target_update} requires an existing same-arm output directory: {destination}"
        )
    phase_b = authenticate_phase_b(Path(phase_b_dir), phase_a_dir=Path(phase_a_dir))
    prepared = authenticate_prepare(Path(prepare_dir), phase_b=phase_b)
    baseline = authenticate_shared_baseline(
        Path(baseline_dir), phase_b=phase_b, prepare=prepared
    )
    candidate_spec = _candidate_spec(candidate_id)
    if candidate_id not in phase_b["eligible_arms"]:
        raise C2ParallelScreenError(f"candidate is not eligible under sealed Phase-B gates: {candidate_id}")
    if initialization_seed not in INITIALIZATION_SEEDS:
        raise C2ParallelScreenError("initialization seed is outside the three frozen lineages")
    batch, metadata, corpus_sha = build_pair_batch(
        phase_b, candidate_id=candidate_id, initialization_seed=initialization_seed
    )
    # Do not leave an empty fresh-arm directory behind when any sealed
    # preflight above fails.  Resume targets already passed the directory
    # existence check at function entry.
    destination.mkdir(parents=True, exist_ok=True)

    # Gate/source authentication and simulator modules are loaded only after
    # all Phase-B rows and eligibility checks have passed.
    modules = _production_modules()
    screen_module = modules["screen"]
    gate_receipt = _authenticate_frozen_source_gate(
        screen_module=screen_module,
        gate_dir=Path(gate_dir),
        c3_source_dir=Path(c3_source_dir),
        prereg_path=Path(prereg_path),
    )
    _phase_b_gate_binding(phase_b, gate_receipt)
    frozen_hybrid = screen_module.load_gate_selected_hybrid(
        gate_receipt, v03_root=Path(v03_root), initialization_seed=initialization_seed
    )
    config = frozen_hybrid.v03_config
    _candidate_type, trainer_type, _candidate_specs, config_type = _c2_algorithm_types()
    if not isinstance(config, config_type):
        raise C2ParallelScreenError("frozen Q2 config is not the masked mean/max config")

    prior_result: dict[str, Any] | None = None
    prior_result_file_sha256: str | None = None
    if prior_update is None:
        trainer = trainer_type(config, candidate=candidate_spec, train_seed=initialization_seed)
    else:
        prior_result, _prior_evaluations = _authenticate_arm(
            destination,
            phase_b=phase_b,
            prepare=prepared,
            baseline=baseline,
            candidate_id=candidate_id,
            seed=initialization_seed,
            target_update=prior_update,
        )
        if prior_result.get("train_corpus_sha256") != corpus_sha:
            raise C2ParallelScreenError("resume checkpoint corpus differs from current Phase-B corpus")
        prior_payload = _load_checkpoint_receipt(
            destination, prior_result, update_count=prior_update
        )
        prior_result_path, _prior_seal_path = _arm_receipt_paths(destination, prior_update)
        prior_result_file_sha256 = _file_sha256(prior_result_path)
        trainer = _reload_checkpoint(
            prior_payload,
            config=config,
            candidate=candidate_spec,
            seed=initialization_seed,
            batch=batch,
        )

    from mcrl.runtime.prereg import read_prereg
    record = read_prereg(Path(prereg_path))
    started = time.perf_counter()
    checkpoint_root = destination / "checkpoints"
    metrics_root = destination / "metrics"
    evaluation_root = destination / "evaluations"
    checkpoint_receipts: list[dict[str, Any]] = list(
        prior_result.get("checkpoint_receipts", ()) if prior_result is not None else ()
    )
    metric_receipts: list[dict[str, Any]] = list(
        prior_result.get("metric_receipts", ()) if prior_result is not None else ()
    )
    evaluation_receipts: dict[str, dict[str, Any]] = dict(
        prior_result.get("evaluation_receipts", {}) if prior_result is not None else {}
    )
    pending_metrics: list[dict[str, Any]] = []
    update_count = prior_update or 0
    start_update = (prior_update + 1) if prior_update is not None else 1
    # Only FULL candidate episodes run here.  Shared DROP-C2 and Main controls
    # are consumed from the precomputed baseline so the exact amendment
    # budget is 90*|eligible_arms| + 30 + 10.
    with tempfile.TemporaryDirectory(prefix="mcrl-v04-c2-screen-tle-") as temporary:
        archive = screen_module._frozen_archive(record, Path(tle_root), Path(temporary) / "frozen-tle")
        for update_index in range(start_update, target_update + 1):
            raw_metric = dict(trainer.update(batch))
            if raw_metric.get("candidate_id") != candidate_id:
                raise C2ParallelScreenError("Q2 trainer metric candidate lineage drifted")
            update_count = update_index
            pending_metrics.append(raw_metric)
            if update_index % CHECKPOINT_EVERY != 0:
                continue
            checkpoint_payload = _checkpoint_payload(
                trainer,
                phase_b=phase_b,
                candidate_id=candidate_id,
                initialization_seed=initialization_seed,
                update_count=update_index,
                train_corpus_sha256=corpus_sha,
                prepare_file_sha256=prepared["payload_file_sha256"],
                baseline_file_sha256=baseline["payload_file_sha256"],
            )
            checkpoint_path = checkpoint_root / f"q2-{candidate_id}-init-{initialization_seed}-update-{update_index:06d}.pt"
            checkpoint_sha = _write_once_torch(checkpoint_path, checkpoint_payload)
            restored = _reload_checkpoint(
                checkpoint_payload,
                config=config,
                candidate=candidate_spec,
                seed=initialization_seed,
                batch=batch,
            )
            if not np.array_equal(trainer.q2_values(batch.states, batch.action_masks), restored.q2_values(batch.states, batch.action_masks)):
                raise C2ParallelScreenError(f"Q2 checkpoint reload is not bit-identical at update {update_index}")
            diagnostics = target_diagnostics(trainer, batch, metadata)
            checkpoint_receipts.append(
                {
                    "update_count": update_index,
                    "path": str(checkpoint_path.resolve()),
                    "file_sha256": checkpoint_sha,
                    "strict_reload": True,
                }
            )
            metric_payload = {
                "schema": ARM_METRICS_SCHEMA,
                "claim_ceiling": CLAIM_CEILING,
                "candidate_id": candidate_id,
                "initialization_seed": initialization_seed,
                "phase_b_sha256": phase_b["phase_b_sha256"],
                "train_corpus_sha256": corpus_sha,
                "screen_update_unit": SCREEN_UPDATE_UNIT,
                "train_order": TRAIN_ORDER,
                "minibatch_order_sha256": corpus_sha,
                "update_count": update_index,
                "raw_update_metrics": pending_metrics,
                "target_diagnostics": diagnostics,
                "checkpoint_file_sha256": checkpoint_sha,
                "evaluation_split": EVALUATION_SPLIT,
                "test_split_opened": False,
                "held_out_ee_evaluated": False,
                "episode_training": False,
            }
            metric_path = metrics_root / f"update-{update_index:06d}.json"
            metric_sha = _write_once_json(metric_path, metric_payload)
            metric_receipts.append(
                {
                    "update_count": update_index,
                    "path": str(metric_path.resolve()),
                    "file_sha256": metric_sha,
                    "raw_update_count": len(pending_metrics),
                }
            )
            pending_metrics = []
            if update_index not in EVALUATION_UPDATES:
                continue
            # Construct candidate deployment with this Q2 and frozen Q1/Q3.
            hybrid = _load_candidate_hybrid(
                screen_module=screen_module,
                gate_receipt=gate_receipt,
                v03_root=Path(v03_root),
                candidate_trainer=trainer,
                seed=initialization_seed,
            )
            full_rows: list[dict[str, Any]] = []
            for evaluation_seed in DESIGN_EVAL_SEEDS:
                field = _design_field(evaluation_seed, str(phase_b["phase_b_sha256"]))
                full_rows.append(
                    _candidate_episode(
                    screen_module=screen_module,
                    hybrid=hybrid,
                    candidate=trainer,
                    archive=archive,
                    field=field,
                    phase_b_sha256=str(phase_b["phase_b_sha256"]),
                    evaluation_seed=evaluation_seed,
                    checkpoint_update=update_index,
                    candidate_id=candidate_id,
                    drop_c2=False,
                    )
                )
            baseline_drop = {
                row["evaluation_seed"]: row
                for row in baseline["rows"]
                if row.get("policy_label") == "DROP_C2"
                and row.get("initialization_seed") == initialization_seed
            }
            baseline_main = {
                row["evaluation_seed"]: row
                for row in baseline["rows"]
                if row.get("policy_label") == "MAIN"
            }
            if set(baseline_drop) != set(DESIGN_EVAL_SEEDS) or set(baseline_main) != set(DESIGN_EVAL_SEEDS):
                raise C2ParallelScreenError("shared baseline controls are incomplete for this arm")
            eval_rows: list[dict[str, Any]] = []
            for evaluation_seed, full in zip(DESIGN_EVAL_SEEDS, full_rows, strict=True):
                drop = _relabel_shared_eval_row(
                    baseline_drop[evaluation_seed],
                    candidate_id=candidate_id,
                    update_count=update_index,
                )
                main = _relabel_shared_eval_row(
                    baseline_main[evaluation_seed],
                    candidate_id=candidate_id,
                    update_count=update_index,
                )
                full, drop = _attach_action_flips(full, drop)
                eval_rows.extend((full, drop, main))
            summary = aggregate_design_rows(
                eval_rows,
                candidate_id=candidate_id,
                update_count=update_index,
                initialization_seeds=(initialization_seed,),
                phase_b_sha256=str(phase_b["phase_b_sha256"]),
            )
            # The single-arm summary cannot pass the >=2-init gate; merge
            # recomputes the decision from all three authenticated lineages.
            eval_payload = {
                "schema": ARM_EVAL_SCHEMA,
                "claim_ceiling": CLAIM_CEILING,
                "candidate_id": candidate_id,
                "initialization_seed": initialization_seed,
                "phase_b_sha256": phase_b["phase_b_sha256"],
                "checkpoint_update": update_index,
                "evaluation_split": EVALUATION_SPLIT,
                "design_eval_seeds": list(DESIGN_EVAL_SEEDS),
                "rows": eval_rows,
                "summary_single_lineage": summary,
                "counterfactual_outcomes_evaluated": True,
                "test_split_opened": False,
                "held_out_ee_evaluated": False,
                "episode_training": False,
            }
            eval_path = evaluation_root / f"update-{update_index:06d}.json"
            eval_sha = _write_once_json(eval_path, eval_payload)
            evaluation_receipts[str(update_index)] = {
                "path": str(eval_path.resolve()),
                "file_sha256": eval_sha,
                "row_count": len(eval_rows),
            }
    required_rungs = _rung_updates(target_update)
    required_checkpoints = _checkpoint_updates_for(target_update)
    if (
        update_count != target_update
        or len(checkpoint_receipts) != len(required_checkpoints)
        or len(metric_receipts) != len(required_checkpoints)
    ):
        raise C2ParallelScreenError("C2 screen did not close all 100-update boundaries")
    result = {
        "schema": ARM_SCHEMA,
        "status": "ARM_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "candidate_id": candidate_id,
        "candidate_spec": asdict(candidate_spec),
        "target_update": target_update,
        "resumed_from_update": prior_update or 0,
        "parent_arm_result_file_sha256": prior_result_file_sha256,
        "prepare_file_sha256": prepared["payload_file_sha256"],
        "baseline_file_sha256": baseline["payload_file_sha256"],
        "initialization_seed": initialization_seed,
        "phase_b_sha256": phase_b["phase_b_sha256"],
        "phase_b_result_file_sha256": phase_b["result_file_sha256"],
        "train_corpus_sha256": corpus_sha,
        "state_dim": STATE_DIM,
        "action_dim": ACTION_DIM,
        "screen_update_unit": SCREEN_UPDATE_UNIT,
        "train_order": TRAIN_ORDER,
        "update_ladder": list(UPDATE_LADDER),
        "checkpoint_every": CHECKPOINT_EVERY,
        "checkpoint_updates": list(required_checkpoints),
        "training_scope": TRAINING_SCOPE,
        "evaluation_split": EVALUATION_SPLIT,
        "design_eval_seeds": list(DESIGN_EVAL_SEEDS),
        "evaluation_updates": list(required_rungs),
        "evaluation_episode_count": len(DESIGN_EVAL_SEEDS) * len(required_rungs),
        "episode_budget": expected_design_eval_episodes(
            len(phase_b["eligible_arms"]), target_update=target_update
        ),
        "checkpoint_receipts": checkpoint_receipts,
        "metric_receipts": metric_receipts,
        "evaluation_receipts": evaluation_receipts,
        "updates_completed": update_count,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
        "counterfactual_outcomes_evaluated": True,
        "elapsed_s": time.perf_counter() - started,
    }
    result_path, seal_path = _arm_receipt_paths(destination, target_update)
    result_sha = _write_once_json(result_path, result)
    seal_sha = _write_once_json(
        seal_path,
        {
            "schema": "multi-catfish-mcrl-v04-c2-parallel-screen-arm-seal-v1",
            "status": "ARM_COMPLETE",
            "arm_result_file_sha256": result_sha,
            "candidate_id": candidate_id,
            "initialization_seed": initialization_seed,
            "target_update": target_update,
            "resumed_from_update": prior_update or 0,
            "parent_arm_result_file_sha256": prior_result_file_sha256,
            "phase_b_sha256": phase_b["phase_b_sha256"],
            "prepare_file_sha256": prepared["payload_file_sha256"],
            "baseline_file_sha256": baseline["payload_file_sha256"],
            "updates_completed": target_update,
            "checkpoint_updates": list(required_checkpoints),
            "evaluation_updates": list(required_rungs),
            "episode_budget": expected_design_eval_episodes(
                len(phase_b["eligible_arms"]), target_update=target_update
            ),
            "counterfactual_outcomes_evaluated": True,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "episode_training": False,
        },
    )
    return {
        "schema": ARM_SCHEMA,
        "status": "ARM_COMPLETE",
        "candidate_id": candidate_id,
        "initialization_seed": initialization_seed,
        "target_update": target_update,
        "resumed_from_update": prior_update or 0,
        "parent_arm_result_file_sha256": prior_result_file_sha256,
        "arm_result_path": str(result_path.resolve()),
        "arm_seal_path": str(seal_path.resolve()),
        "arm_result_file_sha256": result_sha,
        "arm_seal_file_sha256": seal_sha,
        "updates_completed": update_count,
        "checkpoint_updates": list(required_checkpoints),
        "evaluation_updates": list(required_rungs),
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }


def _authenticate_arm(
    path: Path,
    *,
    phase_b: Mapping[str, Any],
    prepare: Mapping[str, Any],
    baseline: Mapping[str, Any],
    candidate_id: str,
    seed: int,
    target_update: int = UPDATE_LADDER[-1],
) -> tuple[dict[str, Any], dict[str, Any]]:
    target_update = _target_update(target_update)
    required_rungs = _rung_updates(target_update)
    required_checkpoints = _checkpoint_updates_for(target_update)
    root = _regular_dir(path, field=f"arm {candidate_id}/{seed}")
    result_path, seal_path = _arm_receipt_paths(root, target_update)
    result, result_sha = _read_json(result_path)
    seal, seal_sha = _read_json(seal_path)
    previous_update = _prior_update(target_update)
    expected_parent_result_sha: str | None = None
    if previous_update is not None:
        previous_result_path, _previous_seal_path = _arm_receipt_paths(root, previous_update)
        expected_parent_result_sha = _file_sha256(previous_result_path)
    if (
        result.get("schema") != ARM_SCHEMA
        or result.get("status") != "ARM_COMPLETE"
        or result.get("claim_ceiling") != CLAIM_CEILING
        or result.get("candidate_id") != candidate_id
        or result.get("initialization_seed") != seed
        or result.get("target_update") != target_update
        or result.get("resumed_from_update") != (previous_update or 0)
        or result.get("parent_arm_result_file_sha256") != expected_parent_result_sha
        or result.get("phase_b_sha256") != phase_b["phase_b_sha256"]
        or result.get("prepare_file_sha256") != prepare["payload_file_sha256"]
        or result.get("baseline_file_sha256") != baseline["payload_file_sha256"]
        or result.get("update_ladder") != list(UPDATE_LADDER)
        or result.get("checkpoint_every") != CHECKPOINT_EVERY
        or result.get("checkpoint_updates") != list(required_checkpoints)
        or result.get("evaluation_split") != EVALUATION_SPLIT
        or result.get("design_eval_seeds") != list(DESIGN_EVAL_SEEDS)
        or result.get("evaluation_updates") != list(required_rungs)
        or result.get("evaluation_episode_count") != len(DESIGN_EVAL_SEEDS) * len(required_rungs)
        or result.get("episode_budget") != expected_design_eval_episodes(
            len(phase_b["eligible_arms"]), target_update=target_update
        )
        or result.get("updates_completed") != target_update
        or result.get("counterfactual_outcomes_evaluated") is not True
        or result.get("test_split_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
        or result.get("episode_training") is not False
        or seal.get("schema") != "multi-catfish-mcrl-v04-c2-parallel-screen-arm-seal-v1"
        or seal.get("status") != "ARM_COMPLETE"
        or seal.get("arm_result_file_sha256") != result_sha
        or seal.get("candidate_id") != candidate_id
        or seal.get("initialization_seed") != seed
        or seal.get("target_update") != target_update
        or seal.get("resumed_from_update") != (previous_update or 0)
        or seal.get("parent_arm_result_file_sha256") != expected_parent_result_sha
        or seal.get("phase_b_sha256") != phase_b["phase_b_sha256"]
        or seal.get("prepare_file_sha256") != prepare["payload_file_sha256"]
        or seal.get("baseline_file_sha256") != baseline["payload_file_sha256"]
        or seal.get("updates_completed") != target_update
        or seal.get("checkpoint_updates") != list(required_checkpoints)
        or seal.get("evaluation_updates") != list(required_rungs)
        or seal.get("episode_budget") != expected_design_eval_episodes(
            len(phase_b["eligible_arms"]), target_update=target_update
        )
        or seal.get("counterfactual_outcomes_evaluated") is not True
        or seal.get("test_split_opened") is not False
        or seal.get("held_out_ee_evaluated") is not False
        or seal.get("episode_training") is not False
    ):
        raise C2ParallelScreenError(f"arm authority mismatch for {candidate_id}/{seed}")
    checkpoints = result.get("checkpoint_receipts")
    metrics = result.get("metric_receipts")
    evaluations = result.get("evaluation_receipts")
    if (
        not isinstance(checkpoints, list)
        or len(checkpoints) != len(required_checkpoints)
        or not isinstance(metrics, list)
        or len(metrics) != len(required_checkpoints)
        or not isinstance(evaluations, Mapping)
        or set(evaluations) != {str(update) for update in required_rungs}
    ):
        raise C2ParallelScreenError(f"arm receipt ladder is incomplete for {candidate_id}/{seed}")
    if torch is None:
        raise C2ParallelScreenError("torch-backed arm authentication is unavailable in this environment")
    for expected_update, checkpoint, metric in zip(required_checkpoints, checkpoints, metrics, strict=True):
        if checkpoint.get("update_count") != expected_update or metric.get("update_count") != expected_update:
            raise C2ParallelScreenError("arm checkpoint/metric update ladder drifted")
        checkpoint_path = _resolve_artifact(checkpoint.get("path"), base=root, field="checkpoint.path")
        metric_path = _resolve_artifact(metric.get("path"), base=root, field="metric.path")
        if _file_sha256(checkpoint_path) != _digest(checkpoint.get("file_sha256"), field="checkpoint.file_sha256") or _file_sha256(metric_path) != _digest(metric.get("file_sha256"), field="metric.file_sha256"):
            raise C2ParallelScreenError("arm checkpoint/metric file digest drifted")
        try:
            checkpoint_payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        except Exception as error:
            raise C2ParallelScreenError("arm checkpoint cannot be loaded") from error
        if not isinstance(checkpoint_payload, Mapping):
            raise C2ParallelScreenError("arm checkpoint payload is malformed")
        if (
            checkpoint_payload.get("schema") != ARM_CHECKPOINT_SCHEMA
            or checkpoint_payload.get("candidate_id") != candidate_id
            or checkpoint_payload.get("initialization_seed") != seed
            or checkpoint_payload.get("phase_b_sha256") != phase_b["phase_b_sha256"]
            or checkpoint_payload.get("prepare_file_sha256") != prepare["payload_file_sha256"]
            or checkpoint_payload.get("baseline_file_sha256") != baseline["payload_file_sha256"]
            or checkpoint_payload.get("update_count") != expected_update
            or checkpoint_payload.get("train_order") != TRAIN_ORDER
            or checkpoint_payload.get("evaluation_split") != EVALUATION_SPLIT
            or checkpoint_payload.get("test_split_opened") is not False
            or checkpoint_payload.get("held_out_ee_evaluated") is not False
            or checkpoint_payload.get("episode_training") is not False
        ):
            raise C2ParallelScreenError("arm checkpoint metadata is not authenticated")
        nested = checkpoint_payload.get("trainer")
        nested_candidate = nested.get("candidate") if isinstance(nested, Mapping) else None
        if (
            not isinstance(nested, Mapping)
            or not isinstance(nested_candidate, Mapping)
            or nested_candidate.get("candidate_id") != candidate_id
            or nested.get("train_seed") != seed
            or nested.get("update_count") != expected_update
        ):
            raise C2ParallelScreenError("arm checkpoint Q2 lineage is not authenticated")
        metric_payload, _ = _read_json(metric_path)
        raw_updates = metric_payload.get("raw_update_metrics")
        if (
            metric_payload.get("schema") != ARM_METRICS_SCHEMA
            or metric_payload.get("update_count") != expected_update
            or metric_payload.get("candidate_id") != candidate_id
            or metric_payload.get("initialization_seed") != seed
            or metric_payload.get("phase_b_sha256") != phase_b["phase_b_sha256"]
            or metric_payload.get("train_order") != TRAIN_ORDER
            or metric_payload.get("minibatch_order_sha256") != result.get("train_corpus_sha256")
            or metric_payload.get("test_split_opened") is not False
            or metric_payload.get("held_out_ee_evaluated") is not False
            or metric_payload.get("episode_training") is not False
            or not isinstance(raw_updates, list)
            or len(raw_updates) != CHECKPOINT_EVERY
        ):
            raise C2ParallelScreenError("arm metrics receipt is not authenticated")
        for raw_update in raw_updates:
            if not isinstance(raw_update, Mapping) or raw_update.get("candidate_id") != candidate_id:
                raise C2ParallelScreenError("arm raw update metrics lineage is not authenticated")
            for key, value in raw_update.items():
                if key == "candidate_id":
                    continue
                _finite(value, field=f"raw_update_metrics.{key}")
    eval_payloads: dict[str, dict[str, Any]] = {}
    for update in required_rungs:
        receipt = evaluations[str(update)]
        eval_path = _resolve_artifact(receipt.get("path"), base=root, field=f"evaluation[{update}].path")
        if _file_sha256(eval_path) != _digest(receipt.get("file_sha256"), field=f"evaluation[{update}].file_sha256"):
            raise C2ParallelScreenError("arm DESIGN-EVAL digest drifted")
        payload, _ = _read_json(eval_path)
        if payload.get("schema") != ARM_EVAL_SCHEMA or payload.get("candidate_id") != candidate_id or payload.get("initialization_seed") != seed or payload.get("phase_b_sha256") != phase_b["phase_b_sha256"] or payload.get("checkpoint_update") != update or payload.get("evaluation_split") != EVALUATION_SPLIT or payload.get("counterfactual_outcomes_evaluated") is not True or payload.get("test_split_opened") is not False or payload.get("held_out_ee_evaluated") is not False or payload.get("episode_training") is not False:
            raise C2ParallelScreenError("arm DESIGN-EVAL receipt is not authenticated")
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise C2ParallelScreenError("arm DESIGN-EVAL rows are missing")
        full = [row for row in rows if isinstance(row, Mapping) and row.get("policy_label") == "FULL"]
        drop = [row for row in rows if isinstance(row, Mapping) and row.get("policy_label") == "DROP_C2"]
        main = [row for row in rows if isinstance(row, Mapping) and row.get("policy_label") == "MAIN"]
        if len(rows) != 3 * len(DESIGN_EVAL_SEEDS) or len(full) != len(DESIGN_EVAL_SEEDS) or len(drop) != len(DESIGN_EVAL_SEEDS) or len(main) != len(DESIGN_EVAL_SEEDS):
            raise C2ParallelScreenError("arm DESIGN-EVAL row counts are incomplete")
        for row in rows:
            if not isinstance(row, Mapping):
                raise C2ParallelScreenError("arm DESIGN-EVAL row is malformed")
            _validate_design_row(row, candidate_id=candidate_id, update_count=update, phase_b_sha256=str(phase_b["phase_b_sha256"]))
        eval_payloads[str(update)] = payload
    return result, eval_payloads


def merge_screen(
    *,
    prepare_dir: Path = DEFAULT_PREPARE_DIR,
    baseline_dir: Path = DEFAULT_BASELINE_DIR,
    phase_b_dir: Path = DEFAULT_PHASE_B_DIR,
    phase_a_dir: Path = DEFAULT_PHASE_A_DIR,
    arm_root: Path = DEFAULT_ARM_ROOT,
    target_update: int = UPDATE_LADDER[-1],
    output_dir: Path = DEFAULT_RESULT_DIR,
) -> dict[str, Any]:
    """Merge all eligible arm receipts at one staged target rung.

    Authentication includes every checkpoint/metric/evaluation receipt needed
    through the target.  Selection itself is performed only from the target
    rung, so a 100-rung merge never waits for 500/1500 artifacts.
    """

    target_update = _target_update(target_update)
    required_rungs = _rung_updates(target_update)
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite C2 screen result: {destination}")
    phase_b = authenticate_phase_b(Path(phase_b_dir), phase_a_dir=Path(phase_a_dir))
    prepared = authenticate_prepare(Path(prepare_dir), phase_b=phase_b)
    baseline = authenticate_shared_baseline(
        Path(baseline_dir), phase_b=phase_b, prepare=prepared
    )
    arm_root_path = _regular_dir(arm_root, field="arm_root")
    candidate_results: dict[str, Any] = {}
    positive_options: list[tuple[float, int, str, int]] = []
    candidate_order = {candidate_id: index for index, candidate_id in enumerate(C2_CANDIDATE_IDS)}
    for candidate_id in phase_b["eligible_arms"]:
        _candidate_spec(candidate_id)
        lineage_results: dict[str, Any] = {}
        eval_by_update: dict[str, list[Mapping[str, Any]]] = {str(update): [] for update in required_rungs}
        for seed in INITIALIZATION_SEEDS:
            arm_dir = arm_root_path / candidate_id / f"init-{seed}"
            arm_result, eval_payloads = _authenticate_arm(
                arm_dir,
                phase_b=phase_b,
                prepare=prepared,
                baseline=baseline,
                candidate_id=candidate_id,
                seed=seed,
                target_update=target_update,
            )
            lineage_results[str(seed)] = {
                "path": str(arm_dir.resolve()),
                "arm_result": arm_result,
                "evaluation_receipts": eval_payloads,
            }
            for update in required_rungs:
                payload = eval_payloads[str(update)]
                rows = payload["rows"]
                for row in rows:
                    if row.get("policy_label") == "FULL":
                        eval_by_update[str(update)].append(row)
        summary_by_update: dict[str, Any] = {}
        for update in required_rungs:
            shared_rows = [
                _relabel_shared_eval_row(
                    row,
                    candidate_id=candidate_id,
                    update_count=update,
                )
                for row in baseline["rows"]
            ]
            all_rows = list(eval_by_update[str(update)]) + shared_rows
            summary = aggregate_design_rows(
                all_rows,
                candidate_id=candidate_id,
                update_count=update,
                phase_b_sha256=str(phase_b["phase_b_sha256"]),
            )
            summary_by_update[str(update)] = summary
            if update == target_update and summary["design_positive"]:
                margin = float(summary["full"]["pooled_ratio_of_sums_ee_bits_per_j"] - summary["drop_c2"]["pooled_ratio_of_sums_ee_bits_per_j"])
                positive_options.append((margin, update, candidate_id, candidate_order[candidate_id]))
        candidate_results[candidate_id] = {
            "lineages": lineage_results,
            "by_update": summary_by_update,
        }
    selected: dict[str, Any] | None = None
    if positive_options:
        positive_options.sort(key=lambda item: (-item[0], item[3], item[1]))
        margin, update, candidate_id, _order = positive_options[0]
        selected = {
            "candidate_id": candidate_id,
            "checkpoint_update": update,
            "pooled_full_minus_drop_c2_ee_bits_per_j": margin,
            "tie_break_order": list(C2_CANDIDATE_IDS),
        }
        decision = DESIGN_POSITIVE_DECISION
    else:
        decision = NO_CANDIDATE_DECISION
    result = {
        "schema": RESULT_SCHEMA,
        "status": "SCREEN_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "phase_b_sha256": phase_b["phase_b_sha256"],
        "phase_b_result_file_sha256": phase_b["result_file_sha256"],
        "eligible_arms": list(phase_b["eligible_arms"]),
        "eligible_candidates": list(phase_b["eligible_arms"]),
        "candidate_order": list(C2_CANDIDATE_IDS),
        "target_update": target_update,
        "initialization_seeds": list(INITIALIZATION_SEEDS),
        "update_ladder": list(UPDATE_LADDER),
        "checkpoint_every": CHECKPOINT_EVERY,
        "checkpoint_updates": list(_checkpoint_updates_for(target_update)),
        "evaluation_updates": list(required_rungs),
        "evaluation_split": EVALUATION_SPLIT,
        "design_eval_seeds": list(DESIGN_EVAL_SEEDS),
        "episode_budget": expected_design_eval_episodes(
            len(phase_b["eligible_arms"]), target_update=target_update
        ),
        "prepare_file_sha256": prepared["payload_file_sha256"],
        "baseline_file_sha256": baseline["payload_file_sha256"],
        "candidates": candidate_results,
        "positive_options": [
            {"pooled_margin": margin, "checkpoint_update": update, "candidate_id": candidate_id}
            for margin, update, candidate_id, _order in positive_options
        ],
        "selected": selected,
        "decision": decision,
        "training_scope": TRAINING_SCOPE,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
        "counterfactual_outcomes_evaluated": True,
    }
    result_sha = _write_once_json(destination / "result.json", result)
    seal_sha = _write_once_json(
        destination / "result-seal.json",
        {
            "schema": SEAL_SCHEMA,
            "status": "SCREEN_COMPLETE",
            "result_file_sha256": result_sha,
            "phase_b_sha256": phase_b["phase_b_sha256"],
            "prepare_file_sha256": prepared["payload_file_sha256"],
            "baseline_file_sha256": baseline["payload_file_sha256"],
            "target_update": target_update,
            "episode_budget": expected_design_eval_episodes(
                len(phase_b["eligible_arms"]), target_update=target_update
            ),
            "decision": decision,
            "counterfactual_outcomes_evaluated": True,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "episode_training": False,
        },
    )
    return {
        "schema": RESULT_SCHEMA,
        "status": "SCREEN_COMPLETE",
        "target_update": target_update,
        "result_file_sha256": result_sha,
        "result_seal_file_sha256": seal_sha,
        "decision": decision,
        "selected": selected,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(command: argparse.ArgumentParser) -> None:
        command.add_argument("--phase-b-dir", type=Path, default=DEFAULT_PHASE_B_DIR)
        command.add_argument("--phase-a-dir", type=Path, default=DEFAULT_PHASE_A_DIR)

    def runtime(command: argparse.ArgumentParser) -> None:
        command.add_argument("--gate-dir", type=Path, default=DEFAULT_GATE_DIR)
        command.add_argument("--c3-source-dir", type=Path, default=DEFAULT_C3_SOURCE_DIR)
        command.add_argument("--v03-root", type=Path, default=DEFAULT_V03_ROOT)
        command.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
        command.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)
        command.add_argument("--main-dir", type=Path, default=DEFAULT_MAIN_DIR)

    prepare = sub.add_parser("prepare", help="seal the pre-episode DESIGN-EVAL contract")
    common(prepare)
    runtime(prepare)
    prepare.add_argument("--output-dir", type=Path, default=DEFAULT_PREPARE_DIR)

    baseline = sub.add_parser("baseline", help="run the shared 30 DROP-C2 + 10 Main controls")
    common(baseline)
    runtime(baseline)
    baseline.add_argument("--prepare-dir", type=Path, default=DEFAULT_PREPARE_DIR)
    baseline.add_argument("--output-dir", type=Path, default=DEFAULT_BASELINE_DIR)

    arm = sub.add_parser("arm", help="run one candidate/initialization offline screen")
    common(arm)
    runtime(arm)
    arm.add_argument("--prepare-dir", type=Path, default=DEFAULT_PREPARE_DIR)
    arm.add_argument("--baseline-dir", type=Path, default=DEFAULT_BASELINE_DIR)
    arm.add_argument("--candidate-id", choices=C2_CANDIDATE_IDS, required=True)
    arm.add_argument("--initialization-seed", type=int, choices=INITIALIZATION_SEEDS, required=True)
    arm.add_argument(
        "--target-update",
        type=int,
        choices=UPDATE_LADDER,
        default=UPDATE_LADDER[-1],
        help="staged target rung; 500/1500 resume from the preceding same-arm checkpoint",
    )
    arm.add_argument("--output-dir", type=Path, required=True)

    merge = sub.add_parser("merge", help="merge all eligible candidate/initialization receipts")
    common(merge)
    merge.add_argument("--prepare-dir", type=Path, default=DEFAULT_PREPARE_DIR)
    merge.add_argument("--baseline-dir", type=Path, default=DEFAULT_BASELINE_DIR)
    merge.add_argument("--arm-root", type=Path, default=DEFAULT_ARM_ROOT)
    merge.add_argument(
        "--target-update",
        type=int,
        choices=UPDATE_LADDER,
        default=UPDATE_LADDER[-1],
        help="merge and select only at this rung; later receipts are not required",
    )
    merge.add_argument("--output-dir", type=Path, default=DEFAULT_RESULT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    if args.command == "prepare":
        result = prepare_screen(
            phase_b_dir=args.phase_b_dir,
            phase_a_dir=args.phase_a_dir,
            gate_dir=args.gate_dir,
            c3_source_dir=args.c3_source_dir,
            v03_root=args.v03_root,
            prereg_path=args.prereg,
            tle_root=args.tle_root,
            main_dir=args.main_dir,
            output_dir=args.output_dir,
        )
    elif args.command == "baseline":
        result = run_shared_baseline(
            prepare_dir=args.prepare_dir,
            phase_b_dir=args.phase_b_dir,
            phase_a_dir=args.phase_a_dir,
            gate_dir=args.gate_dir,
            c3_source_dir=args.c3_source_dir,
            v03_root=args.v03_root,
            prereg_path=args.prereg,
            tle_root=args.tle_root,
            main_dir=args.main_dir,
            output_dir=args.output_dir,
        )
    elif args.command == "arm":
        result = run_arm(
            prepare_dir=args.prepare_dir,
            baseline_dir=args.baseline_dir,
            phase_b_dir=args.phase_b_dir,
            phase_a_dir=args.phase_a_dir,
            gate_dir=args.gate_dir,
            c3_source_dir=args.c3_source_dir,
            v03_root=args.v03_root,
            prereg_path=args.prereg,
            tle_root=args.tle_root,
            main_dir=args.main_dir,
            candidate_id=args.candidate_id,
            initialization_seed=args.initialization_seed,
            target_update=args.target_update,
            output_dir=args.output_dir,
        )
    else:
        result = merge_screen(
            prepare_dir=args.prepare_dir,
            baseline_dir=args.baseline_dir,
            phase_b_dir=args.phase_b_dir,
            phase_a_dir=args.phase_a_dir,
            arm_root=args.arm_root,
            target_update=args.target_update,
            output_dir=args.output_dir,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "ACTION_DIM",
    "BASELINE_SCHEMA",
    "ARM_CHECKPOINT_SCHEMA",
    "ARM_EVAL_SCHEMA",
    "ARM_METRICS_SCHEMA",
    "ARM_SCHEMA",
    "CHECKPOINT_EVERY",
    "CHECKPOINT_UPDATES",
    "CLAIM_CEILING",
    "C2ParallelScreenError",
    "DESIGN_EVAL_SEEDS",
    "FIELD_COMPONENT",
    "EVALUATION_SPLIT",
    "EVALUATION_UPDATES",
    "INITIALIZATION_SEEDS",
    "NO_CANDIDATE_DECISION",
    "RESULT_SCHEMA",
    "SCREEN_SCHEMA",
    "STATE_DIM",
    "UPDATE_LADDER",
    "aggregate_design_rows",
    "authenticate_phase_b",
    "build_pair_batch",
    "canonical_sha256",
    "merge_screen",
    "run_arm",
    "spearman",
    "target_diagnostics",
    "authenticate_prepare",
    "authenticate_shared_baseline",
    "eligible_arms_from_gates",
    "expected_design_eval_episodes",
    "prepare_screen",
    "run_shared_baseline",
]
