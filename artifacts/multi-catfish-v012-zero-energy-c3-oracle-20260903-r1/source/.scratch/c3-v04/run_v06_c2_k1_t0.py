#!/usr/bin/env python3
"""V06 C2-k1 pivot T-0 receipt.

This is an additive, read-only diagnostic.  It authenticates the sealed V0.4
Phase-A and Phase-B inputs, then recomputes the temporal surplus directly
from the persisted per-offset rate/power traces.  It deliberately does not
train, open TEST, select an outcome, or modify either input artifact.

The diagnostic compares the proposed one-step C2 target (``k=1``) with the
existing all-downstream target (``k=1..3``), and reports whether Q13 targets
are invariant across its three initializations.  The result is evidence for
the next design decision only; its claim ceiling is DIAGNOSTIC_ONLY.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile
from types import ModuleType
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (HERE, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

PHASE_A_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-a-v1"
PHASE_A_ROW_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-a-row-v1"
PHASE_B_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-b-v1"
PHASE_B_SHARD_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-b-shard-v1"
PHASE_B_ROW_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-b-row-v1"
C3_DATASET_SCHEMA = "multi-catfish-mcrl-v04-c3-opening-dataset-v1"
INITIALIZATION_SEEDS = (2026092101, 2026092102, 2026092103)
ACTION_COUNT = 28
OFFSET_COUNT = 4
DOWNSTREAM_OFFSETS = (1, 2, 3)
KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")
CLAIM_CEILING = "DIAGNOSTIC_ONLY_NO_TRAINING_NO_TEST_NO_OUTCOME_SELECTION"
DIAGNOSTIC_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t0-diagnostic-v1"
SEAL_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t0-diagnostic-seal-v1"

DEFAULT_PHASE_A_DIR = REPO / "artifacts" / "multi-catfish-v04-c2-support-complete-census-20260901-r3"
DEFAULT_PHASE_B_DIR = REPO / "artifacts" / "multi-catfish-v04-c2-phase-b-merged-20260901-r1"
DEFAULT_C3_DIR = REPO / "artifacts" / "multi-catfish-v04-c3-source-20260901-r2"
DEFAULT_OUTPUT_DIR = REPO / "artifacts" / "multi-catfish-v06-c2-k1-t0-20260901-r1"


class DiagnosticError(RuntimeError):
    """An input, trace, or diagnostic receipt failed closed."""


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DiagnosticError(f"cannot load {name}: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_bytes(payload: object) -> bytes:
    try:
        return (json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise DiagnosticError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)[:-1]).hexdigest()


def _file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise DiagnosticError(f"expected a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> tuple[dict[str, Any], str]:
    if path.is_symlink() or not path.is_file():
        raise DiagnosticError(f"missing/non-regular JSON: {path}")
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise DiagnosticError(f"invalid JSON: {path}") from error
    if not isinstance(value, dict) or raw != _canonical_bytes(value):
        raise DiagnosticError(f"JSON is not canonical: {path}")
    return value, hashlib.sha256(raw).hexdigest()


def _write_once(path: Path, payload: object) -> str:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite diagnostic receipt: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _canonical_bytes(payload)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with open(fd, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    except FileExistsError as error:
        raise FileExistsError(f"refusing to overwrite diagnostic receipt: {path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(raw).hexdigest()


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, bool):
        raise DiagnosticError(f"{field} must be finite numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise DiagnosticError(f"{field} must be finite numeric") from error
    if not math.isfinite(result):
        raise DiagnosticError(f"{field} must be finite numeric")
    return result


def _matrix(value: object, *, field: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise DiagnosticError(f"{field} is not numeric") from error
    if result.ndim != 2 or result.shape[0] != OFFSET_COUNT or not np.all(np.isfinite(result)):
        raise DiagnosticError(f"{field} must be a finite 4xN matrix")
    return result


def _vector(value: object, *, field: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise DiagnosticError(f"{field} is not numeric") from error
    if result.ndim != 1 or result.shape[0] != OFFSET_COUNT or not np.all(np.isfinite(result)):
        raise DiagnosticError(f"{field} must be a finite length-4 vector")
    return result


def _sibling_key(value: object, *, field: str) -> tuple[int, str, str, int, tuple[int, int]]:
    if not isinstance(value, list) or len(value) != 5:
        raise DiagnosticError(f"{field} is malformed")
    if type(value[0]) is not int or value[0] < 0 or not isinstance(value[1], str) or not isinstance(value[2], str) or type(value[3]) is not int or value[3] < 0:
        raise DiagnosticError(f"{field} is malformed")
    physical = value[4]
    if not isinstance(physical, list) or len(physical) != 2 or any(type(item) is not int or item < 0 for item in physical):
        raise DiagnosticError(f"{field} physical key is malformed")
    return value[0], value[1], value[2], value[3], (physical[0], physical[1])


def _intervention(key: tuple[int, str, str, int, tuple[int, int]]) -> tuple[int, str, str, int]:
    return key[:4]


def _target_from_trace(trace: Mapping[str, Any], *, field: str) -> tuple[np.ndarray, np.ndarray]:
    required = ("candidate_rates_bps", "reference_rates_bps", "candidate_system_power_w",
                "reference_system_power_w", "interval_s", "lambda_bits_per_j")
    missing = [name for name in required if name not in trace]
    if missing:
        raise DiagnosticError(f"{field} lacks {','.join(missing)}")
    candidate_rates = _matrix(trace["candidate_rates_bps"], field=f"{field}.candidate_rates_bps")
    reference_rates = _matrix(trace["reference_rates_bps"], field=f"{field}.reference_rates_bps")
    if candidate_rates.shape != reference_rates.shape:
        raise DiagnosticError(f"{field} rate matrices disagree")
    candidate_power = _vector(trace["candidate_system_power_w"], field=f"{field}.candidate_system_power_w")
    reference_power = _vector(trace["reference_system_power_w"], field=f"{field}.reference_system_power_w")
    interval = _finite(trace["interval_s"], field=f"{field}.interval_s")
    multiplier = _finite(trace["lambda_bits_per_j"], field=f"{field}.lambda_bits_per_j")
    if interval <= 0 or multiplier <= 0 or np.any(candidate_power <= 0) or np.any(reference_power <= 0):
        raise DiagnosticError(f"{field} interval, lambda, and power must be positive")
    delta_rates = candidate_rates - reference_rates
    targets = np.asarray([
        interval * math.fsum(float(x) for x in delta_rates[offset])
        - multiplier * interval * float(candidate_power[offset] - reference_power[offset])
        for offset in DOWNSTREAM_OFFSETS
    ], dtype=np.float64)
    supplied = trace.get("offset_surplus_bits")
    if supplied is not None:
        supplied_array = np.asarray(supplied, dtype=np.float64)
        if supplied_array.shape != (3,) or not np.all(np.isfinite(supplied_array)) or not np.allclose(supplied_array, targets, rtol=0.0, atol=1e-6):
            raise DiagnosticError(f"{field}.offset_surplus_bits disagrees with raw rates/power")
    return targets, targets / KAPPA_BITS


def _row_targets(row: Mapping[str, Any], *, field: str) -> tuple[tuple[int, str, str, int, tuple[int, int]], int, np.ndarray, np.ndarray]:
    key = _sibling_key(row.get("sibling_key"), field=f"{field}.sibling_key")
    if row.get("row_status") != "ready":
        raise DiagnosticError(f"{field} is not ready")
    action = row.get("candidate_action")
    if type(action) is not int or action < 0 or action >= ACTION_COUNT:
        raise DiagnosticError(f"{field}.candidate_action is invalid")
    raw = row.get("raw_trace")
    if not isinstance(raw, Mapping):
        raise DiagnosticError(f"{field}.raw_trace is missing")
    raw_targets, normalized = _target_from_trace(raw, field=f"{field}.raw_trace")
    return key, action, raw_targets, normalized


def _spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise DiagnosticError("Spearman input is non-finite")
    def ranks(x: np.ndarray) -> np.ndarray:
        order = np.argsort(x, kind="mergesort")
        out = np.empty(len(x), dtype=np.float64)
        out[order] = np.arange(len(x), dtype=np.float64)
        for value in np.unique(x):
            indexes = np.flatnonzero(x == value)
            out[indexes] = float(np.mean(out[indexes]))
        return out
    ra, rb = ranks(a), ranks(b)
    da, db = ra - np.mean(ra), rb - np.mean(rb)
    denominator = float(np.linalg.norm(da) * np.linalg.norm(db))
    return None if denominator == 0.0 else float(np.dot(da, db) / denominator)


def _summary(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "mean_abs": None,
                "min": None, "max": None}
    numbers = [float(_finite(x, field="summary")) for x in values]
    return {"count": len(numbers), "mean": float(statistics.fmean(numbers)),
            "median": float(statistics.median(numbers)),
            "mean_abs": float(statistics.fmean(abs(x) for x in numbers)),
            "min": min(numbers), "max": max(numbers)}


def compute_diagnostic(
    phase_a_result: Mapping[str, Any],
    phase_b_shards: Mapping[int, Mapping[str, Any]],
    c3_targets_bits: Sequence[float],
    *,
    phase_a_file_sha256: str = "synthetic",
    phase_b_file_sha256: str = "synthetic",
    c3_file_sha256: str = "synthetic",
) -> dict[str, Any]:
    """Compute T-0 from authenticated payloads; no filesystem side effects."""
    rows = phase_a_result.get("rows")
    if phase_a_result.get("schema") != PHASE_A_SCHEMA or not isinstance(rows, list):
        raise DiagnosticError("Phase-A payload is not the expected sealed schema")
    if set(int(seed) for seed in phase_b_shards) != set(INITIALIZATION_SEEDS):
        raise DiagnosticError("Phase-B must contain all three Q13 initializations")
    main: dict[tuple[int, str, str, int], dict[int, np.ndarray]] = {}
    main_norm: dict[tuple[int, str, str, int], dict[int, np.ndarray]] = {}
    phase_a_nonready = 0
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise DiagnosticError(f"Phase-A.rows[{index}] is malformed")
        # Support-expired Phase-A rows are retained by the sealed census but
        # contain no physical trace.  They are censored for Main-vs-Q13
        # matching, never silently imputed.
        if row.get("row_status") != "ready":
            phase_a_nonready += 1
            continue
        key, action, target, normalized = _row_targets(row, field=f"Phase-A.rows[{index}]")
        intervention = _intervention(key)
        if action in main.setdefault(intervention, {}) or action in main_norm.setdefault(intervention, {}):
            raise DiagnosticError("Phase-A has duplicate intervention/action")
        main[intervention][action] = target
        main_norm[intervention][action] = normalized
    if len(main) == 0:
        raise DiagnosticError("Phase-A has no ready physical traces")
    # The reference action is the only action omitted from a complete
    # Phase-A anchor; incomplete/censored anchors remain out of Main-vs-Q13.
    reference_by_anchor: dict[tuple[int, str, str, int], int] = {}
    incomplete_main = {key for key, actions in main.items() if len(actions) != ACTION_COUNT - 1}
    for intervention in sorted(set(main) - incomplete_main):
        actions = main[intervention]
        missing = set(range(ACTION_COUNT)) - set(actions)
        if len(missing) != 1:
            raise DiagnosticError("Phase-A action census is not exactly 27+reference")
        reference_by_anchor[intervention] = missing.pop()
        actions[reference_by_anchor[intervention]] = np.zeros(3, dtype=np.float64)
        main_norm[intervention][reference_by_anchor[intervention]] = np.zeros(3, dtype=np.float64)

    q13: dict[int, dict[tuple[int, str, str, int], dict[int, np.ndarray]]] = {}
    q13_norm: dict[int, dict[tuple[int, str, str, int], dict[int, np.ndarray]]] = {}
    for raw_seed, shard in phase_b_shards.items():
        seed = int(raw_seed)
        if seed not in INITIALIZATION_SEEDS or not isinstance(shard, Mapping):
            raise DiagnosticError(f"unexpected Phase-B initialization {raw_seed}")
        shard_rows = shard.get("rows")
        if shard.get("schema") != PHASE_B_SHARD_SCHEMA or not isinstance(shard_rows, list):
            raise DiagnosticError(f"Phase-B shard {seed} is malformed")
        q13[seed], q13_norm[seed] = {}, {}
        for index, row in enumerate(shard_rows):
            if row.get("schema") != PHASE_B_ROW_SCHEMA or row.get("initialization_seed") != seed:
                raise DiagnosticError(f"Phase-B row {seed}/{index} schema/seed drift")
            key = _sibling_key(row.get("sibling_key"), field=f"Phase-B[{seed}].rows[{index}].sibling_key")
            if row.get("row_status") != "ready" or not isinstance(row.get("pair"), Mapping):
                raise DiagnosticError(f"Phase-B row {seed}/{index} is not ready")
            pair = row["pair"]
            # Phase-B has the same physical fields in pair as Phase-A has in raw_trace.
            target, normalized = _target_from_trace(pair, field=f"Phase-B[{seed}].rows[{index}].pair")
            intervention = _intervention(key)
            action = pair.get("candidate_action", row.get("candidate_action"))
            if type(action) is not int or action < 0 or action >= ACTION_COUNT:
                raise DiagnosticError(f"Phase-B row {seed}/{index} action is invalid")
            if action in q13[seed].setdefault(intervention, {}):
                raise DiagnosticError(f"Phase-B {seed} has duplicate intervention/action")
            q13[seed][intervention][action] = target
            q13_norm[seed].setdefault(intervention, {})[action] = normalized
        if set(q13[seed]) != set(main):
            raise DiagnosticError(f"Phase-B {seed} anchor census does not match Phase-A")
        for intervention in main:
            if len(q13[seed][intervention]) != ACTION_COUNT - 1:
                raise DiagnosticError(f"Phase-B {seed} anchor is not 27+reference")
            # The reference action is carried in each persisted pair.  Read it
            # from the first row instead of inferring it from censored Main.
            first = next(row for row in shard_rows if _intervention(_sibling_key(row["sibling_key"], field="Phase-B.sibling_key")) == intervention)
            pair = first.get("pair")
            ref = pair.get("reference_action") if isinstance(pair, Mapping) else None
            if type(ref) is not int or ref < 0 or ref >= ACTION_COUNT:
                raise DiagnosticError(f"Phase-B {seed} reference action is invalid")
            if intervention in reference_by_anchor and reference_by_anchor[intervention] != ref:
                raise DiagnosticError(f"Phase-B {seed} reference action disagrees with Main")
            reference_by_anchor[intervention] = ref
            if ref in q13[seed][intervention]:
                raise DiagnosticError(f"Phase-B {seed} sibling set contains reference action")
            q13[seed][intervention][ref] = np.zeros(3, dtype=np.float64)
            q13_norm[seed][intervention][ref] = np.zeros(3, dtype=np.float64)
    if set(q13) != set(INITIALIZATION_SEEDS):
        raise DiagnosticError("Phase-B must contain all three Q13 initializations")

    def axis(values: dict[int, np.ndarray], index: int) -> list[float]:
        return [float(values[action][index]) for action in range(ACTION_COUNT)]

    invariance: dict[str, Any] = {}
    main_q13: dict[str, Any] = {}
    for index, label in ((0, "k1"), (None, "k1_to_k3")):
        pairwise: list[float] = []
        mainwise: list[float] = []
        per_anchor: dict[str, Any] = {}
        for intervention in sorted(q13[INITIALIZATION_SEEDS[0]]):
            main_values = None if intervention in incomplete_main else ([float(np.sum(main_norm[intervention][a])) for a in range(ACTION_COUNT)] if index is None else axis(main_norm[intervention], index))
            init_values: dict[str, list[float]] = {}
            for seed in INITIALIZATION_SEEDS:
                vals = [float(np.sum(q13_norm[seed][intervention][a])) for a in range(ACTION_COUNT)] if index is None else axis(q13_norm[seed][intervention], index)
                init_values[str(seed)] = vals
                if main_values is not None:
                    corr = _spearman(main_values, vals)
                    if corr is not None:
                        mainwise.append(corr)
            for left, right in ((INITIALIZATION_SEEDS[0], INITIALIZATION_SEEDS[1]),
                                (INITIALIZATION_SEEDS[0], INITIALIZATION_SEEDS[2]),
                                (INITIALIZATION_SEEDS[1], INITIALIZATION_SEEDS[2])):
                corr = _spearman(init_values[str(left)], init_values[str(right)])
                if corr is not None:
                    pairwise.append(corr)
            per_anchor[json.dumps(list(intervention), separators=(",", ":"), ensure_ascii=True)] = {
                "main_vs_q13_spearman": {seed: (None if main_values is None else _spearman(main_values, init_values[str(seed)])) for seed in INITIALIZATION_SEEDS},
                "q13_pairwise_spearman": {f"{left}-{right}": _spearman(init_values[str(left)], init_values[str(right)]) for left, right in ((INITIALIZATION_SEEDS[0], INITIALIZATION_SEEDS[1]), (INITIALIZATION_SEEDS[0], INITIALIZATION_SEEDS[2]), (INITIALIZATION_SEEDS[1], INITIALIZATION_SEEDS[2]))},
            }
        invariance[label] = {"formula": "rho_s(rank(t_a^q), rank(t_a^q')) over 28 actions", "anchor_count": len(q13[INITIALIZATION_SEEDS[0]]), "pair_count": len(pairwise), "spearman": _summary(pairwise), "per_anchor": per_anchor}
        main_q13[label] = {"formula": "rho_s(rank(t_a^M), rank(t_a^q)) over matched 28 actions", "anchor_count": len(main) - len(incomplete_main), "comparison_count": len(mainwise), "spearman": _summary(mainwise), "censored_anchor_count": len(incomplete_main)}

    complete_main = set(main) - incomplete_main
    c2_main = [float(np.mean(np.abs(main_norm[intervention][action][0]))) for intervention in complete_main for action in range(ACTION_COUNT)]
    c2_main_all = [float(np.mean(np.abs(np.sum(main_norm[intervention][action])))) for intervention in complete_main for action in range(ACTION_COUNT)]
    c2_q13 = [float(np.mean(np.abs(q13_norm[seed][intervention][action][0]))) for seed in INITIALIZATION_SEEDS for intervention in main for action in range(ACTION_COUNT)]
    c2_q13_all = [float(np.mean(np.abs(np.sum(q13_norm[seed][intervention][action])))) for seed in INITIALIZATION_SEEDS for intervention in main for action in range(ACTION_COUNT)]
    c3_norm = [abs(_finite(value, field="c3 target") / KAPPA_BITS) for value in c3_targets_bits]
    if not c3_norm:
        raise DiagnosticError("sealed C3 target scale is empty")
    return {
        "schema": DIAGNOSTIC_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "status": "DIAGNOSTIC_COMPLETE",
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "formulas": {
            "per_offset_bits": "t_k = Delta_t * sum_i(R_i^C(k)-R_i^M(k)) - lambda * Delta_t * (P_C^N(k)-P_M^N(k))",
            "k1": "t^(1) = t_1",
            "k1_to_k3": "t^(1:3) = sum_{k=1}^3 t_k",
            "normalized": "t_hat = t / kappa",
            "invariance": "rho_s(rank(t_a^q), rank(t_a^q')) over matched 28 actions within an anchor",
            "main_vs_q13": "rho_s(rank(t_a^M), rank(t_a^q)) over matched 28 actions within an anchor",
            "mean_abs_scale": "mean_{anchor,action,q} |t_hat|; reference action has t_hat=0",
        },
        "inputs": {"phase_a_result_file_sha256": phase_a_file_sha256,
                   "phase_b_result_file_sha256": phase_b_file_sha256,
                   "c3_source_file_sha256": c3_file_sha256,
                   "kappa_bits": KAPPA_BITS,
                   "initialization_seeds": list(INITIALIZATION_SEEDS)},
        "counts": {"anchors": len(q13[INITIALIZATION_SEEDS[0]]), "main_complete_anchors": len(main) - len(incomplete_main), "main_censored_anchors": len(incomplete_main), "phase_a_nonready_rows": phase_a_nonready, "actions_per_anchor": ACTION_COUNT,
                   "phase_a_rows": len(rows), "phase_a_ready_rows": len(rows) - phase_a_nonready, "phase_b_rows_per_initialization": {str(seed): sum(len(v) for v in q13[seed].values()) - len(q13[seed]) for seed in INITIALIZATION_SEEDS},
                   "c3_target_rows": len(c3_norm)},
        "within_anchor_q13_invariance": invariance,
        "main_vs_q13": main_q13,
        "mean_absolute_normalized_target_scale": {
            "c2_main_k1": _summary(c2_main), "c2_q13_k1": _summary(c2_q13),
            "c2_main_k1_to_k3": _summary(c2_main_all), "c2_q13_k1_to_k3": _summary(c2_q13_all),
            "c3_sealed_route_target": _summary(c3_norm),
            "ratio_c2_main_to_c3": {"k1": float(statistics.fmean(c2_main) / statistics.fmean(c3_norm)), "k1_to_k3": float(statistics.fmean(c2_main_all) / statistics.fmean(c3_norm))},
        },
    }


def _authenticate_and_load(args: argparse.Namespace) -> tuple[dict[str, Any], dict[int, Mapping[str, Any]], list[float], dict[str, Any]]:
    screen = _load_module("mcrl_v04_c2_parallel_screen_for_v06", HERE / "run_v04_c2_parallel_screen.py")
    phase_b = screen.authenticate_phase_b(Path(args.phase_b_dir), phase_a_dir=Path(args.phase_a_dir))
    # Authenticate only the sealed C3 bytes needed for the scale comparison.
    # Do not call the C3 producer's current-source-closure verifier here: a
    # later checkout may legitimately differ from the sealed producer while
    # the persisted dataset bytes remain a valid comparison authority.
    c3_root = Path(args.c3_dir)
    manifest, manifest_file_sha = _read_json(c3_root / "source-manifest.json")
    manifest_body = dict(manifest)
    manifest_sha = manifest_body.pop("source_manifest_sha256", None)
    if manifest.get("schema") != "multi-catfish-mcrl-v04-c3-source-manifest-v1" or manifest_sha != canonical_sha256(manifest_body):
        raise DiagnosticError("C3 source manifest digest/schema is invalid")
    prepare, prepare_file_sha = _read_json(c3_root / "prepare-receipt.json")
    prepare_seal, prepare_seal_file_sha = _read_json(c3_root / "prepare-receipt-seal.json")
    if (prepare.get("schema") != "multi-catfish-mcrl-v04-c3-prepare-receipt-v1"
            or prepare.get("status") != "SEALED_PREOUTCOME"
            or prepare.get("source_manifest_file_sha256") != manifest_file_sha
            or prepare.get("source_manifest_sha256") != manifest_sha
            or prepare.get("training") is not False
            or prepare.get("test_split_opened") is not False
            or prepare.get("held_out_ee_evaluated") is not False
            or prepare_seal.get("schema") != "multi-catfish-mcrl-v04-c3-prepare-receipt-seal-v1"
            or prepare_seal.get("prepare_receipt_file_sha256") != prepare_file_sha):
        raise DiagnosticError("C3 prepare authority is invalid")
    c3_data_root = c3_root / "source-data"
    c3_receipt, c3_receipt_file_sha = _read_json(c3_data_root / "receipt.json")
    c3_receipt_seal, _ = _read_json(c3_data_root / "receipt-seal.json")
    if (c3_receipt.get("schema") != "multi-catfish-mcrl-v04-c3-generate-receipt-v1"
            or c3_receipt.get("status") not in {"PASS", "PASS_VERIFIED"}
            or c3_receipt.get("source_manifest_sha256") != manifest_sha
            or c3_receipt.get("target_sign_filter") is not False
            or c3_receipt.get("training") is not False
            or c3_receipt.get("test_split_opened") is not False
            or c3_receipt.get("held_out_ee_evaluated") is not False
            or c3_receipt_seal.get("receipt_file_sha256") != c3_receipt_file_sha):
        raise DiagnosticError("C3 generated receipt is invalid")
    phase_a_result = phase_b["phase_a"]["result"]
    shards = {int(seed): payload for seed, payload in phase_b["shards"].items()}
    c3_targets: list[float] = []
    c3_hashes: dict[str, str] = {}
    for path in sorted((Path(args.c3_dir) / "source-data").glob("c3-*.json")):
        payload, file_sha = _read_json(path)
        c3_hashes[path.name] = file_sha
        seed = path.stem.removeprefix("c3-")
        expected_file_sha = c3_receipt.get("dataset_file_sha256s", {}).get(seed)
        if expected_file_sha != file_sha:
            raise DiagnosticError(f"C3 dataset file hash disagrees for {seed}")
        expected_dataset_sha = c3_receipt.get("dataset_sha256s", {}).get(seed)
        if payload.get("schema") != "multi-catfish-mcrl-v04-c3-opening-dataset-v2" or payload.get("dataset_sha256") != expected_dataset_sha:
            raise DiagnosticError(f"C3 dataset digest/schema disagrees for {seed}")
        for index, row in enumerate(payload.get("rows", [])):
            pair = row.get("pair") if isinstance(row, Mapping) else None
            if not isinstance(pair, Mapping) or "route_target_surplus_bits" not in pair:
                raise DiagnosticError(f"C3 row lacks route target: {path}:{index}")
            raw = pair["route_target_surplus_bits"]
            c3_targets.append(float.fromhex(raw) if isinstance(raw, str) else _finite(raw, field="C3 route target"))
    if not c3_targets:
        raise DiagnosticError("C3 source data has no target rows")
    hashes = {
        "phase_a_result": phase_b["phase_a"]["result_file_sha256"],
        "phase_a_seal": phase_b["phase_a"]["seal_file_sha256"],
        "phase_b_result": phase_b["result_file_sha256"],
        "phase_b_seal": phase_b["seal_file_sha256"],
        "phase_b_shards": {str(seed): dict(phase_b["shard_receipts"][str(seed)]) for seed in INITIALIZATION_SEEDS},
        "c3_files": c3_hashes,
        "c3_files_sha256": canonical_sha256(c3_hashes),
        "c3_manifest_file": manifest_file_sha,
        "c3_prepare_file": prepare_file_sha,
        "c3_prepare_seal_file": prepare_seal_file_sha,
        "c3_receipt_file": c3_receipt_file_sha,
    }
    return phase_a_result, shards, c3_targets, hashes


def run(args: argparse.Namespace) -> dict[str, Any]:
    phase_a, shards, c3_targets, hashes = _authenticate_and_load(args)
    result = compute_diagnostic(phase_a, shards, c3_targets,
                                phase_a_file_sha256=hashes["phase_a_result"],
                                phase_b_file_sha256=hashes["phase_b_result"],
                                c3_file_sha256=hashes["c3_files_sha256"])
    result["inputs"]["phase_a_seal_file_sha256"] = hashes["phase_a_seal"]
    result["inputs"]["phase_b_seal_file_sha256"] = hashes["phase_b_seal"]
    result["inputs"]["phase_b_shards"] = hashes["phase_b_shards"]
    result["inputs"]["c3_manifest_file_sha256"] = hashes["c3_manifest_file"]
    result["inputs"]["c3_prepare_file_sha256"] = hashes["c3_prepare_file"]
    result["inputs"]["c3_prepare_seal_file_sha256"] = hashes["c3_prepare_seal_file"]
    result["inputs"]["c3_receipt_file_sha256"] = hashes["c3_receipt_file"]
    result["inputs"]["c3_dataset_file_sha256"] = hashes["c3_files"]
    root = Path(args.output_dir)
    result_sha = _write_once(root / "diagnostic-result.json", result)
    seal = {"schema": SEAL_SCHEMA, "status": "DIAGNOSTIC_COMPLETE",
            "claim_ceiling": CLAIM_CEILING, "result_sha256": canonical_sha256(result),
            "result_file_sha256": result_sha, "training": False,
            "test_split_opened": False, "outcome_selection": False}
    _write_once(root / "diagnostic-seal.json", seal)
    return result


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase-a-dir", type=Path, default=DEFAULT_PHASE_A_DIR)
    parser.add_argument("--phase-b-dir", type=Path, default=DEFAULT_PHASE_B_DIR)
    parser.add_argument("--c3-dir", type=Path, default=DEFAULT_C3_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        result = run(_arguments(argv))
    except (DiagnosticError, FileExistsError) as error:
        print(f"FAIL_CLOSED: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"status": result["status"], "schema": result["schema"], "claim_ceiling": result["claim_ceiling"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
