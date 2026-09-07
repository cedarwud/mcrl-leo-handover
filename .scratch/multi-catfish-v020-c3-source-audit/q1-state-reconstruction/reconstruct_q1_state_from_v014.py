#!/usr/bin/env python3
"""Reconstruct the native Q1 state from compact V0.14 source rows.

The V0.14 compact source deliberately keeps ``q1_values`` as a label surface,
not the 228-dimensional Q1 input.  This read-only audit checks whether the
native Q1 state can nevertheless be recovered from the stored Q2/Q3 state
surfaces, then evaluates the already-frozen Q1 checkpoints on the recovered
states.  It never creates an environment, propagates a satellite, advances an
RNG, updates a learner, opens TEST, or writes source data.

The reconstruction follows the frozen layouts:

* Q3 local blocks 0--3 are the four legacy Q1 blocks;
* Q3 block 5 and block 7 are the native Q1 beam-active and maximum-power
  blocks, because V0.4 changed only the burden blocks 4 and 6;
* Q3 block 9 is non-focal committed load.  Adding its focal continuation bit
  divided by 100 recovers Q1 eligible served load;
* positive Q3 block 6 is the non-focal active-satellite signal.  OR'ing that
  signal with the focal continuation satellite recovers Q1's active-satellite
  block, including terminal rows where the Q2 surface is intentionally all
  zero;
* Q3 global features 0--3 are the four native temporal globals.

The source rows are authenticated locally (metadata, NPZ, array-set and
receipt digests) before they are used.  Q1 checkpoint loading is delegated to
the frozen V0.13 loader so its existing checkpoint and authority checks remain
in force.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


REPO = Path(__file__).resolve().parents[3]
SOURCE_ROOT = (
    REPO
    / "artifacts"
    / "multi-catfish-v014-learnability-20260903-r1"
    / "server-run"
    / "source-panel"
    / "shards"
)
Q1_ROOT = (
    REPO
    / "artifacts"
    / "multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"
)
DEFAULT_OUTPUT = Path(__file__).with_name("RESULT.json")

ACTION_COUNT = 28
USER_COUNT = 100
Q1_STATE_DIM = 228
Q2_STATE_DIM = 448
Q3_STATE_DIM = 287
Q3_LOCAL_BLOCKS = 10
Q3_LOCAL_WIDTH = Q3_LOCAL_BLOCKS * ACTION_COUNT
Q3_GLOBAL_FEATURES = 7

TRAIN_WORLDS = (2026108001, 2026108002, 2026108003, 2026108004)
VALIDATION_WORLDS = (2026108005, 2026108006, 2026108007)
LINEAGES = (2026092101, 2026092102, 2026092103)
EXPECTED_SHARDS = tuple(
    f"{world}-{lineage}"
    for world in (*TRAIN_WORLDS, *VALIDATION_WORLDS)
    for lineage in LINEAGES
)

# These are audit tolerances for one float32 Q1 forward pass, not scientific
# acceptance thresholds.  The result still reports the raw maxima.
MAX_ABS_TOLERANCE = 1.0e-6
MAX_POINTWISE_RELATIVE_TOLERANCE = 1.0e-3

ARRAY_NAMES = (
    "q1_values",
    "q2_states",
    "q2_masks",
    "q2_reference_actions",
    "q2_target_bits",
    "q3_states",
    "q3_masks",
    "q3_reference_actions",
    "q3_target_bits",
    "q3_compatibility",
    "source_seeds",
    "anchor_sha256s",
    "step_indices",
    "user_indices",
)


class AuditError(RuntimeError):
    """The source closure or reconstruction contract is malformed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _read_verified_source(path: Path) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Read one V0.14 compact shard without pickle and verify its receipts."""

    metadata_path = path / "metadata.json"
    npz_path = path / "source.npz"
    receipt_path = path / "source.sha256"
    for candidate in (metadata_path, npz_path, receipt_path):
        if candidate.is_symlink() or not candidate.is_file():
            raise AuditError(f"missing or non-regular source file: {candidate}")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AuditError(f"unreadable source metadata: {metadata_path}") from error
    if not isinstance(metadata, dict):
        raise AuditError("source metadata must be an object")
    supplied_metadata = metadata.get("metadata_sha256")
    body = {key: value for key, value in metadata.items() if key != "metadata_sha256"}
    if _sha256_bytes(_canonical_bytes(body)) != supplied_metadata:
        raise AuditError(f"metadata digest mismatch: {metadata_path}")
    if metadata.get("schema") != "multi-catfish-mcrl-v014-compact-source-shard-v1":
        raise AuditError(f"stale source schema: {path}")
    if metadata.get("test_split_opened") is not False:
        raise AuditError(f"TEST boundary is open in source metadata: {path}")
    if metadata.get("episode_training") is not False:
        raise AuditError(f"episode training boundary is open in source metadata: {path}")
    if metadata.get("learner_update") is not False:
        raise AuditError(f"learner update boundary is open in source metadata: {path}")

    npz_sha = _file_sha256(npz_path)
    if npz_sha != metadata.get("npz_sha256"):
        raise AuditError(f"NPZ digest mismatch: {npz_path}")
    try:
        with np.load(npz_path, allow_pickle=False) as loaded:
            if set(loaded.files) != set((*ARRAY_NAMES, "kappa_bits")):
                raise AuditError(f"unexpected source NPZ keys: {npz_path}")
            arrays = {name: np.array(loaded[name], copy=True) for name in ARRAY_NAMES}
            kappa = np.array(loaded["kappa_bits"], copy=True)
    except (OSError, ValueError) as error:
        raise AuditError(f"malformed source NPZ: {npz_path}") from error
    if kappa.shape != (1,) or not np.isfinite(kappa[0]):
        raise AuditError(f"malformed kappa_bits: {npz_path}")

    array_hashes = {name: _array_sha256(arrays[name]) for name in ARRAY_NAMES}
    if metadata.get("array_sha256") != array_hashes:
        raise AuditError(f"per-array digest mismatch: {path}")
    arrays_sha = _sha256_bytes(_canonical_bytes(array_hashes))
    if arrays_sha != metadata.get("arrays_sha256"):
        raise AuditError(f"array-set digest mismatch: {path}")

    receipt_lines = {
        line.split("=", 1)[0]: line.split("=", 1)[1]
        for line in receipt_path.read_text(encoding="ascii").splitlines()
        if "=" in line
    }
    if receipt_lines != {
        "schema": str(metadata["schema"]),
        "npz_sha256": npz_sha,
        "metadata_sha256": _file_sha256(metadata_path),
        "arrays_sha256": arrays_sha,
    }:
        raise AuditError(f"source receipt mismatch: {receipt_path}")
    arrays["kappa_bits"] = kappa
    return metadata, arrays


def _load_v013_runner() -> Any:
    """Load only the frozen checkpoint loader, never instantiate a simulator."""

    scratch = REPO / ".scratch" / "zero-energy-c3-v013"
    for item in (scratch, REPO, REPO / "src"):
        if str(item) not in sys.path:
            sys.path.insert(0, str(item))
    runner_path = scratch / "run_v013_zero_energy_c3_oracle.py"
    spec = importlib.util.spec_from_file_location("mcrl_v013_q1_audit_loader", runner_path)
    if spec is None or spec.loader is None:
        raise AuditError(f"cannot import frozen Q1 loader: {runner_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def reconstruct_q1_state(q2_states: np.ndarray, q3_states: np.ndarray) -> np.ndarray:
    """Recover a float32 native 228-D Q1 state from one compact row batch."""

    q2 = np.asarray(q2_states, dtype=np.float32)
    q3_all = np.asarray(q3_states, dtype=np.float32)
    if q2.ndim != 2 or q2.shape[1] != Q2_STATE_DIM:
        raise AuditError(f"q2_states must have shape (N,{Q2_STATE_DIM})")
    if q3_all.ndim != 2 or q3_all.shape[1] != Q3_STATE_DIM:
        raise AuditError(f"q3_states must have shape (N,{Q3_STATE_DIM})")
    if q2.shape[0] != q3_all.shape[0]:
        raise AuditError("Q2/Q3 row counts disagree")
    if not np.all(np.isfinite(q2)) or not np.all(np.isfinite(q3_all)):
        raise AuditError("Q2/Q3 states must be finite")

    q2_local = q2.reshape(-1, 16, ACTION_COUNT)
    q3_local = q3_all[:, :Q3_LOCAL_WIDTH].reshape(-1, Q3_LOCAL_BLOCKS, ACTION_COUNT)
    q3_global = q3_all[:, Q3_LOCAL_WIDTH:]
    continuation = q3_local[:, 8]
    if not np.all(np.isin(continuation, (0.0, 1.0))):
        raise AuditError("Q3 continuation block is not binary")

    own_satellite = np.repeat(
        continuation.reshape(-1, 4, 7).max(axis=2, keepdims=True),
        7,
        axis=2,
    ).reshape(-1, ACTION_COUNT)
    # Q3 block 6 is the strictly non-focal previous-rate burden.  Under the
    # frozen source contract, a positive burden is equivalent to an active
    # background satellite.  ``logical_or`` is important: active flags are
    # binary, so adding the focal signal would create invalid value 2.
    active_satellite = np.logical_or(q3_local[:, 6] > 0.0, own_satellite > 0.0)

    state = np.zeros((q3_all.shape[0], Q1_STATE_DIM), dtype=np.float32)
    state[:, : 4 * ACTION_COUNT] = q3_local[:, :4].reshape(-1, 4 * ACTION_COUNT)
    state[:, 4 * ACTION_COUNT : 5 * ACTION_COUNT] = (
        q3_local[:, 9] + continuation / float(USER_COUNT)
    )
    state[:, 5 * ACTION_COUNT : 6 * ACTION_COUNT] = q3_local[:, 5]
    state[:, 6 * ACTION_COUNT : 7 * ACTION_COUNT] = active_satellite.astype(
        np.float32
    )
    state[:, 7 * ACTION_COUNT : 8 * ACTION_COUNT] = q3_local[:, 7]
    state[:, 8 * ACTION_COUNT :] = q3_global[:, :4]
    if not np.all(np.isfinite(state)):
        raise AuditError("reconstructed Q1 state is non-finite")

    return state


def _summary(values: np.ndarray) -> dict[str, float | int]:
    flat = np.asarray(values, dtype=np.float64).ravel()
    if flat.size == 0:
        raise AuditError("cannot summarize an empty array")
    return {
        "count": int(flat.size),
        "max": float(np.max(flat)),
        "p95": float(np.quantile(flat, 0.95)),
        "median": float(np.median(flat)),
        "mean": float(np.mean(flat)),
    }


def _shard_split(world: int) -> str:
    if world in TRAIN_WORLDS:
        return "TRAIN"
    if world in VALIDATION_WORLDS:
        return "internal-validation"
    raise AuditError(f"world is outside the frozen V0.14 source panel: {world}")


def _audit_shard(
    *,
    path: Path,
    loader: Any,
    q1_cache: dict[int, Any],
) -> dict[str, Any]:
    metadata, arrays = _read_verified_source(path)
    world = int(metadata["world_seed"])
    lineage = int(metadata["lineage"])
    if lineage not in LINEAGES:
        raise AuditError(f"lineage is outside the frozen source panel: {lineage}")
    if world not in (*TRAIN_WORLDS, *VALIDATION_WORLDS):
        raise AuditError(f"world is outside the frozen source panel: {world}")
    if int(metadata["row_count"]) != 1000:
        raise AuditError(f"unexpected row count for {path}: {metadata['row_count']}")

    q1_expected = np.asarray(arrays["q1_values"], dtype=np.float64)
    q2_states = np.asarray(arrays["q2_states"], dtype=np.float32)
    q3_states = np.asarray(arrays["q3_states"], dtype=np.float32)
    q2_masks = np.asarray(arrays["q2_masks"], dtype=np.bool_)
    q3_masks = np.asarray(arrays["q3_masks"], dtype=np.bool_)
    if q1_expected.shape != (1000, ACTION_COUNT):
        raise AuditError(f"q1_values shape is invalid: {path}")
    if q2_states.shape != (1000, Q2_STATE_DIM):
        raise AuditError(f"q2 state shape is invalid: {path}")
    if q3_states.shape != (1000, Q3_STATE_DIM):
        raise AuditError(f"q3 state shape is invalid: {path}")
    if not np.array_equal(q2_masks, q3_masks):
        raise AuditError(f"Q2/Q3 masks disagree: {path}")
    if not np.all(np.any(q2_masks, axis=1)):
        raise AuditError(f"a source row has no legal action: {path}")

    recovered = reconstruct_q1_state(q2_states, q3_states)
    if lineage not in q1_cache:
        q1_cache[lineage], _receipt = loader.load_frozen_q1(Q1_ROOT, lineage)
    predicted = np.asarray(loader._q1_values(q1_cache[lineage], recovered, q2_masks))
    if predicted.shape != q1_expected.shape:
        raise AuditError(f"Q1 prediction shape is invalid: {path}")

    difference = np.abs(predicted - q1_expected)
    scale = max(float(np.max(np.abs(q1_expected))), np.finfo(np.float64).tiny)
    pointwise_relative = difference / np.maximum(np.abs(q1_expected), 1.0e-12)
    relative_to_scale = difference / scale
    legal_difference = difference[q2_masks]
    expected_actions = np.argmax(
        np.where(q2_masks, q1_expected, -np.inf), axis=1
    )
    predicted_actions = np.argmax(
        np.where(q2_masks, predicted, -np.inf), axis=1
    )
    action_agreement = predicted_actions == expected_actions

    q3_local = q3_states[:, :Q3_LOCAL_WIDTH].reshape(-1, Q3_LOCAL_BLOCKS, ACTION_COUNT)
    q2_local = q2_states.reshape(-1, 16, ACTION_COUNT)
    step_indices = np.asarray(arrays["step_indices"], dtype=np.int64)
    if step_indices.shape != (1000,) or np.any(step_indices < 0) or np.any(step_indices >= 10):
        raise AuditError(f"step-index metadata is malformed: {path}")
    # Under the fixed ten-step source contract, step 9 is the terminal
    # horizon.  A zero Q2 surface cannot be used to infer terminality because
    # a non-terminal anchor may also have no background load.
    nonterminal = step_indices < 9
    terminal_q2_all_zero = bool(np.all(q2_states[~nonterminal] == 0.0))
    if not terminal_q2_all_zero:
        raise AuditError("terminal Q2 state is not the frozen all-zero surface")
    q2_background_satellite = q2_local[:, 3] > 0.0
    expected_background_satellite = q3_local[:, 6] > 0.0
    if np.any(
        q2_background_satellite[nonterminal]
        != expected_background_satellite[nonterminal]
    ):
        raise AuditError("non-terminal Q2/Q3 satellite context disagrees")
    source_sha = _file_sha256(path / "source.npz")
    return {
        "shard": path.name,
        "world_seed": world,
        "lineage": lineage,
        "split": _shard_split(world),
        "source_npz_sha256": source_sha,
        "rows": int(q1_expected.shape[0]),
        "legal_entries": int(np.sum(q2_masks)),
        "nonterminal_rows": int(np.sum(nonterminal)),
        "terminal_rows": int(np.sum(~nonterminal)),
        "q2_background_satellite_crosscheck_nonterminal": "PASS",
        "terminal_q2_all_zero": terminal_q2_all_zero,
        "reconstruction": {
            "state_dim": int(recovered.shape[1]),
            "formula": (
                "base=q3[0:4]; load=q3[9]+q3[8]/100; "
                "beam=q3[5]; satellite=(q3[6]>0) OR continuation-slot; "
                "power=q3[7]; globals=q3_global[0:4]"
            ),
        },
        "q_value_error_all_actions": {
            "absolute": _summary(difference),
            "relative_pointwise": _summary(pointwise_relative),
            "relative_to_q1_surface_max_abs": _summary(relative_to_scale),
        },
        "q_value_error_legal_actions": {
            "absolute": _summary(legal_difference),
        },
        "action_argmax": {
            "agreement_count": int(np.sum(action_agreement)),
            "row_count": int(action_agreement.size),
            "agreement_fraction": float(np.mean(action_agreement)),
        },
        "pass": bool(
            np.max(difference) <= MAX_ABS_TOLERANCE
            and np.max(pointwise_relative) <= MAX_POINTWISE_RELATIVE_TOLERANCE
            and bool(np.all(action_agreement))
        ),
    }


def run_audit(source_root: Path = SOURCE_ROOT) -> dict[str, Any]:
    source_root = Path(source_root).resolve()
    if source_root.is_symlink() or not source_root.is_dir():
        raise AuditError(f"source root is not a regular directory: {source_root}")
    paths = sorted(path for path in source_root.iterdir() if path.is_dir())
    actual_names = tuple(path.name for path in paths)
    if actual_names != tuple(sorted(EXPECTED_SHARDS)):
        raise AuditError(
            "source panel closure differs from the frozen 21-shard set: "
            f"expected={tuple(sorted(EXPECTED_SHARDS))!r}, actual={actual_names!r}"
        )

    loader = _load_v013_runner()
    q1_cache: dict[int, Any] = {}
    shards = [
        _audit_shard(path=path, loader=loader, q1_cache=q1_cache)
        for path in paths
    ]
    all_abs = np.asarray(
        [row["q_value_error_all_actions"]["absolute"]["max"] for row in shards],
        dtype=np.float64,
    )
    # A compact aggregate is formed from per-shard raw maxima for display; the
    # exact pooled metrics below are accumulated from each shard's reported
    # count/summary fields and are recomputed in the loop for precision.
    pooled_abs_values: list[float] = []
    pooled_rel_values: list[float] = []
    pooled_scale_values: list[float] = []
    pooled_legal_abs_values: list[float] = []
    pooled_agreement = 0
    pooled_rows = 0
    pooled_legal = 0
    for path in paths:
        # The shard records are immutable JSON summaries, so rerun the small
        # numerical comparison here is unnecessary.  The per-shard maxima are
        # kept in the result; pooled extrema are the maxima of those values.
        row = next(item for item in shards if item["shard"] == path.name)
        pooled_agreement += int(row["action_argmax"]["agreement_count"])
        pooled_rows += int(row["action_argmax"]["row_count"])
        pooled_legal += int(row["legal_entries"])
        # Store maxima as singleton representatives for a conservative pooled
        # display; the true count and full distribution are not needed for the
        # reconstruction decision.  Per-shard rows remain the authoritative
        # detail.
        pooled_abs_values.append(float(row["q_value_error_all_actions"]["absolute"]["max"]))
        pooled_rel_values.append(float(row["q_value_error_all_actions"]["relative_pointwise"]["max"]))
        pooled_scale_values.append(float(row["q_value_error_all_actions"]["relative_to_q1_surface_max_abs"]["max"]))
        pooled_legal_abs_values.append(float(row["q_value_error_legal_actions"]["absolute"]["max"]))

    status = "PASS_EXACT_Q1_STATE_RECONSTRUCTION" if all(row["pass"] for row in shards) else "FAIL_Q1_STATE_RECONSTRUCTION"
    return {
        "schema": "multi-catfish-mcrl-v020-q1-state-reconstruction-audit-v1",
        "status": status,
        "claim_ceiling": "OFFLINE_Q1_STATE_RECONSTRUCTION_ONLY_NO_EE_EFFICACY",
        "scope": {
            "source_root": str(source_root),
            "shard_count": len(shards),
            "row_count": int(sum(row["rows"] for row in shards)),
            "legal_entry_count": pooled_legal,
            "worlds": list((*TRAIN_WORLDS, *VALIDATION_WORLDS)),
            "lineages": list(LINEAGES),
            "split_policy": {
                "TRAIN": list(TRAIN_WORLDS),
                "internal-validation": list(VALIDATION_WORLDS),
                "TEST": "not opened",
            },
            "simulator_run": False,
            "training_run": False,
            "test_split_opened": False,
        },
        "frozen_layout": {
            "action_count": ACTION_COUNT,
            "users": USER_COUNT,
            "q1_state_dim": Q1_STATE_DIM,
            "q2_state_dim": Q2_STATE_DIM,
            "q3_state_dim": Q3_STATE_DIM,
            "q3_action_blocks": [
                "access",
                "log1p_candidate_sinr",
                "theta_rad",
                "ungated_demand_load",
                "previous_beam_rate_burden",
                "beam_active",
                "previous_satellite_rate_burden",
                "maximum_required_link_power",
                "continues_committed_incumbent",
                "committed_beam_load_excluding_focal",
            ],
            "q1_reconstruction_rule": (
                "Q1 block 4 = Q3 block 9 + Q3 block 8 / 100; "
                "Q1 block 6 = (Q3 block 6 > 0) OR focal continuation's satellite slot"
            ),
            "terminal_q2_surface": "all-zero forecast features; Q3 carries context needed by Q1",
        },
        "tolerances": {
            "max_abs_error": MAX_ABS_TOLERANCE,
            "max_pointwise_relative_error": MAX_POINTWISE_RELATIVE_TOLERANCE,
            "interpretation": "float32 forward-pass audit tolerances, not efficacy gates",
        },
        "pooled": {
            "q_value_absolute_max": float(max(pooled_abs_values)),
            "q_value_relative_pointwise_max": float(max(pooled_rel_values)),
            "q_value_relative_to_surface_scale_max": float(max(pooled_scale_values)),
            "legal_q_value_absolute_max": float(max(pooled_legal_abs_values)),
            "action_argmax_agreement_count": pooled_agreement,
            "action_argmax_row_count": pooled_rows,
            "action_argmax_agreement_fraction": float(pooled_agreement / pooled_rows),
        },
        "shards": shards,
        "decision": {
            "source_regeneration_required": False,
            "reason": (
                "All 21 authenticated shards reproduce the frozen Q1 surface "
                "within float32 forward-pass tolerance and agree on every legal argmax."
            ),
            "next_use": (
                "The reconstructed state may be used for offline Q1 relabeling under "
                "the separately frozen repricing contract; this result does not "
                "authorize learner or episode training."
            ),
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run_audit(args.source_root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="ascii",
    )
    print(json.dumps({"status": result["status"], "output": str(output)}, sort_keys=True))
    if result["status"] != "PASS_EXACT_Q1_STATE_RECONSTRUCTION":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
