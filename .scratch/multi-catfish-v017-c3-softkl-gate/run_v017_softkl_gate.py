#!/usr/bin/env python3
"""Run the frozen V0.17 B402 masked soft-KL C3 learnability gate.

This runner consumes authenticated TRAIN-only source shards.  It does not
construct or advance a simulator, open TEST, or evaluate trajectory EE.  For
each frozen Q1/Q2 lineage it trains one independent 402-dimensional Q3 head
on exactly balanced ``h=12``, ``h=1``, and ``h=2`` full-row batches.
Only update 3000 determines the mechanical PASS/FAIL result.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from typing import Any

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_v014_head import EEAxisV014HeadConfig  # noqa: E402
from mcrl.errors import MCRLContractError  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
from mcrl.runtime.ee_axis_b402_c3_softkl import (  # noqa: E402
    B402SoftKLBatch,
    EEAxisB402SoftKLLearner,
    build_b402_softkl_batch,
)
from mcrl.runtime.ee_axis_v016_c3_origin_state import (  # noqa: E402
    V016_C3_GLOBAL_START,
    V016_C3_ORIGIN_GLOBAL_FEATURES,
    V016_C3_ORIGIN_LOCAL_FEATURES,
    V016_C3_ORIGIN_STATE_DIM,
    V016_C3_ORIGIN_STATE_SCHEMA,
    V016_C3_REFERENCE_BEAM_GLOBAL_START,
    V016_C3_V015_GLOBAL_END,
)


SOURCE_RUNNER_PATH = HERE / "run_v017_softkl_source_shard.py"
CONTRACT_PATH = (
    REPO
    / "artifacts"
    / "multi-catfish-v017-c3-softkl-gate-20260903-r1"
    / "contracts"
    / "MULTI-CATFISH-MCRL-V017-C3-SOFTKL-GATE-PREREG-2026-09-03.md"
)
CONTRACT_SHA256 = "ef7e6abd3c2a657cf718a09b5169f652609f65c0c41e30b2257245920fdea70b"

RUNNER_SCHEMA = "multi-catfish-mcrl-v017-c3-softkl-learnability-gate-v1"
RESULT_SCHEMA = "multi-catfish-mcrl-v017-c3-softkl-learnability-result-v1"
CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v017-c3-softkl-learnability-checkpoint-v1"
CLAIM_CEILING = "TRAIN_VALIDATION_SOURCE_ONLY_NO_TRAJECTORY_EE_OR_EFFICACY_CLAIM"

ACTION_DIM = 28
CONTEXT_CODES = (12, 1, 2)
TRAIN_WORLD_SEEDS = (2026112001, 2026112002, 2026112003)
VALIDATION_WORLD_SEEDS = (2026112004, 2026112005, 2026112006)
SOURCE_LINEAGES = (2026092101, 2026092102, 2026092103)
INITIALIZATION_SEEDS = (2026112101, 2026112102, 2026112103)
UPDATE_RUNGS = (3, 10, 30, 100, 300, 1000, 3000)
BATCH_PER_CONTEXT = 170
Q2_CHECKPOINT_SHA256_BY_LINEAGE = {
    2026092101: "d981232a9e56e6ce71c8e8b1fda789efc69852d4a6a22e918a2992ddc58a533d",
    2026092102: "9a45f5bc125d6ba453d7d74dbc640ec3d2e927fffb161518e383e6b3aabbe8ef",
    2026092103: "8f9d2e5d1749515a0896137082b1430419ae1b8a794d28ea772a23c86648be81",
}


class V017SoftKLGateError(MCRLContractError):
    """A V0.17 soft-KL source, learner, or frozen decision boundary failed."""


def _file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V017SoftKLGateError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V017SoftKLGateError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def validate_frozen_contract() -> str:
    actual = _file_sha256(CONTRACT_PATH)
    if actual != CONTRACT_SHA256:
        raise V017SoftKLGateError("V0.17 soft-KL contract bytes drifted")
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    for phrase in (
        "Status: PRE-OUTCOME CONTRACT",
        "2026112001",
        "2026112006",
        "2026112101",
        "3000 updates",
        "New masked soft-KL objective",
        "14\\times 28+10=402",
    ):
        if phrase not in text:
            raise V017SoftKLGateError(
                f"V0.17 soft-KL contract lacks required binding: {phrase}"
            )
    return actual


def _readonly(value: object, *, dtype: np.dtype[Any]) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _masked_argmax(values: np.ndarray, masks: np.ndarray) -> np.ndarray:
    return np.argmax(np.where(masks, values, -np.inf), axis=1).astype(np.int64)


def _masked_mean_entropy(values: np.ndarray, masks: np.ndarray) -> float:
    logits = np.asarray(values, dtype=np.float64)
    legal = np.asarray(masks)
    if (
        logits.ndim != 2
        or legal.dtype != np.bool_
        or legal.shape != logits.shape
        or not np.all(np.isfinite(logits))
        or not np.all(np.any(legal, axis=1))
    ):
        raise V017SoftKLGateError("entropy surface is malformed")
    masked = np.where(legal, logits, -np.inf)
    shifted = masked - np.max(masked, axis=1, keepdims=True)
    exponent = np.where(legal, np.exp(shifted), 0.0)
    probability = exponent / np.sum(exponent, axis=1, keepdims=True)
    log_probability = np.zeros_like(probability)
    positive = legal & (probability > 0.0)
    log_probability[positive] = np.log(probability[positive])
    return float(np.mean(-np.sum(probability * log_probability, axis=1)))


def _context_components(
    q1_values: np.ndarray,
    q2_values: np.ndarray,
    context_code: int,
) -> tuple[np.ndarray, np.ndarray]:
    q1 = np.asarray(q1_values, dtype=np.float64)
    q2 = np.asarray(q2_values, dtype=np.float64)
    if q1.shape != q2.shape or q1.ndim != 2 or q1.shape[1] != ACTION_DIM:
        raise V017SoftKLGateError("Q1/Q2 source surfaces are malformed")
    if int(context_code) == 12:
        return q1, q2
    if int(context_code) == 1:
        return q1, np.zeros_like(q2)
    if int(context_code) == 2:
        return np.zeros_like(q1), q2
    raise V017SoftKLGateError(f"unknown reference context: {context_code}")


@dataclass(frozen=True)
class ReferenceRows:
    """Authenticated row-aligned source data for one lineage and split."""

    q3_states: np.ndarray
    action_masks: np.ndarray
    q1_values: np.ndarray
    learned_q2_values: np.ndarray
    z3_target_bits: np.ndarray
    q3_compatibility: np.ndarray
    context_codes: np.ndarray
    reference_actions: np.ndarray
    source_seeds: np.ndarray
    lineages: np.ndarray
    anchor_sha256s: np.ndarray
    step_indices: np.ndarray
    user_indices: np.ndarray
    shard_receipts: tuple[dict[str, object], ...] = ()

    @property
    def rows(self) -> int:
        return int(np.asarray(self.q3_states).shape[0])

    def verify(self, *, require_context_closure: bool = True) -> None:
        rows = self.rows
        states = np.asarray(self.q3_states)
        masks = np.asarray(self.action_masks)
        q1 = np.asarray(self.q1_values)
        q2 = np.asarray(self.learned_q2_values)
        z3 = np.asarray(self.z3_target_bits)
        compatibility = np.asarray(self.q3_compatibility)
        contexts = np.asarray(self.context_codes)
        references = np.asarray(self.reference_actions)
        if states.shape != (rows, V016_C3_ORIGIN_STATE_DIM) or rows < 1:
            raise V017SoftKLGateError("Q3 state rows are malformed")
        if not np.all(np.isfinite(states)):
            raise V017SoftKLGateError("Q3 state contains a non-finite value")
        if masks.dtype != np.bool_ or masks.shape != (rows, ACTION_DIM):
            raise V017SoftKLGateError("source masks are malformed")
        if not np.all(np.any(masks, axis=1)):
            raise V017SoftKLGateError("each source row needs a legal action")
        for name, values in (
            ("q1_values", q1),
            ("learned_q2_values", q2),
            ("z3_target_bits", z3),
        ):
            if values.shape != (rows, ACTION_DIM) or not np.all(np.isfinite(values)):
                raise V017SoftKLGateError(f"{name} is malformed")
        if compatibility.dtype != np.bool_ or compatibility.shape != (rows, ACTION_DIM):
            raise V017SoftKLGateError("Q3 compatibility rows are malformed")
        if np.any(compatibility & ~masks) or np.any(z3[~masks] != 0.0):
            raise V017SoftKLGateError("Q3 labels are nonzero outside the native mask")
        present_contexts = set(np.unique(contexts).tolist())
        if (
            contexts.shape != (rows,)
            or not np.issubdtype(contexts.dtype, np.integer)
            or not present_contexts
            or not present_contexts.issubset(set(CONTEXT_CODES))
        ):
            raise V017SoftKLGateError("source contains an unknown or empty context set")
        if require_context_closure and present_contexts != set(CONTEXT_CODES):
            raise V017SoftKLGateError("source must contain exactly contexts 12, 1, and 2")
        if references.shape != (rows,) or not np.issubdtype(references.dtype, np.integer):
            raise V017SoftKLGateError("reference actions are malformed")
        row_index = np.arange(rows)
        if np.any(references < 0) or np.any(references >= ACTION_DIM) or not np.all(
            masks[row_index, references]
        ):
            raise V017SoftKLGateError("source has an illegal reference action")
        if np.any(z3[row_index, references] != 0.0):
            raise V017SoftKLGateError("ZR reference targets must be exactly zero")
        for name, values in (
            ("source_seeds", self.source_seeds),
            ("lineages", self.lineages),
            ("step_indices", self.step_indices),
            ("user_indices", self.user_indices),
        ):
            array = np.asarray(values)
            if array.shape != (rows,) or not np.issubdtype(array.dtype, np.integer):
                raise V017SoftKLGateError(f"{name} is malformed")
        anchors = np.asarray(self.anchor_sha256s)
        if anchors.shape != (rows,) or anchors.dtype.kind not in "SU":
            raise V017SoftKLGateError("anchor SHA rows are malformed")
        for name in (
            "q3_states",
            "action_masks",
            "q1_values",
            "learned_q2_values",
            "z3_target_bits",
            "q3_compatibility",
            "context_codes",
            "reference_actions",
            "source_seeds",
            "lineages",
            "anchor_sha256s",
            "step_indices",
            "user_indices",
        ):
            if np.asarray(getattr(self, name)).flags.writeable:
                raise V017SoftKLGateError(f"{name} must be immutable")
        counts = {
            code: int(np.count_nonzero(contexts == code))
            for code in sorted(present_contexts)
        }
        if require_context_closure and len(set(counts.values())) != 1:
            raise V017SoftKLGateError(f"context rows are not balanced: {counts}")

        # Every physical (world,lineage,anchor,step,user) row must appear once
        # in each context.  Base surfaces and masks are context-independent.
        groups: dict[tuple[object, ...], list[int]] = {}
        for index in range(rows):
            key = (
                int(np.asarray(self.source_seeds)[index]),
                int(np.asarray(self.lineages)[index]),
                bytes(anchors[index]) if anchors.dtype.kind == "S" else str(anchors[index]),
                int(np.asarray(self.step_indices)[index]),
                int(np.asarray(self.user_indices)[index]),
            )
            groups.setdefault(key, []).append(index)
        for indices in groups.values():
            if require_context_closure and (
                len(indices) != 3
                or set(contexts[indices].tolist()) != set(CONTEXT_CODES)
            ):
                raise V017SoftKLGateError("physical source row lacks exact context closure")
            first = indices[0]
            for index in indices[1:]:
                if not (
                    np.array_equal(masks[first], masks[index])
                    and np.array_equal(q1[first], q1[index])
                    and np.array_equal(q2[first], q2[index])
                    and np.array_equal(states[first, :280], states[index, :280])
                    and np.array_equal(
                        states[first, V016_C3_GLOBAL_START:V016_C3_V015_GLOBAL_END],
                        states[index, V016_C3_GLOBAL_START:V016_C3_V015_GLOBAL_END],
                    )
                ):
                    raise V017SoftKLGateError(
                        "context copies disagree on native state or base-head surface"
                    )
            for index in indices:
                q1_context, q2_context = _context_components(
                    q1[index : index + 1], q2[index : index + 1], int(contexts[index])
                )
                expected = int(
                    _masked_argmax(q1_context + q2_context, masks[index : index + 1])[0]
                )
                if int(references[index]) != expected:
                    raise V017SoftKLGateError(
                        "stored reference is not the masked base-head argmax"
                    )

    def context(self, code: int) -> "ReferenceRows":
        self.verify()
        selected = np.flatnonzero(np.asarray(self.context_codes) == int(code))
        if selected.size < 1:
            raise V017SoftKLGateError(f"source lacks context {code}")
        fields: dict[str, object] = {}
        for name in (
            "q3_states",
            "action_masks",
            "q1_values",
            "learned_q2_values",
            "z3_target_bits",
            "q3_compatibility",
            "context_codes",
            "reference_actions",
            "source_seeds",
            "lineages",
            "anchor_sha256s",
            "step_indices",
            "user_indices",
        ):
            array = np.asarray(getattr(self, name))[selected]
            fields[name] = _readonly(array, dtype=array.dtype)
        result = ReferenceRows(**fields, shard_receipts=self.shard_receipts)
        result.verify(require_context_closure=False)
        return result


def _concat(values: Sequence[np.ndarray], *, dtype: np.dtype[Any]) -> np.ndarray:
    if not values:
        raise V017SoftKLGateError("cannot concatenate empty source arrays")
    return _readonly(np.concatenate([np.asarray(value) for value in values]), dtype=dtype)


def _source_module() -> ModuleType:
    if not SOURCE_RUNNER_PATH.is_file():
        raise V017SoftKLGateError(f"source runner is missing: {SOURCE_RUNNER_PATH}")
    spec = importlib.util.spec_from_file_location(
        "mcrl_v017_softkl_source_for_gate", SOURCE_RUNNER_PATH
    )
    if spec is None or spec.loader is None:
        raise V017SoftKLGateError("cannot construct source runner import")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_reference_rows(
    paths: Sequence[str | Path],
    *,
    lineage: int,
    worlds: Sequence[int],
) -> ReferenceRows:
    """Authenticate and merge one exact lineage/world source closure."""

    module = _source_module()
    reader = getattr(module, "read_source_shard", None)
    if not callable(reader):
        raise V017SoftKLGateError("source runner lacks read_source_shard")
    target_worlds = tuple(int(value) for value in worlds)
    if not target_worlds or len(set(target_worlds)) != len(target_worlds):
        raise V017SoftKLGateError("source world closure is malformed")
    selected: list[tuple[int, Any, Path]] = []
    receipts: list[dict[str, object]] = []
    seen: set[tuple[int, int]] = set()
    for raw_path in sorted({Path(value).resolve() for value in paths}, key=str):
        if raw_path.is_symlink() or not raw_path.is_dir():
            raise V017SoftKLGateError(f"source shard is not a regular directory: {raw_path}")
        source = reader(raw_path)
        metadata_path = raw_path / "metadata.json"
        try:
            metadata = json.loads(metadata_path.read_text(encoding="ascii"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise V017SoftKLGateError("authenticated source metadata cannot be reopened") from error
        if not isinstance(metadata, dict):
            raise V017SoftKLGateError("authenticated source metadata is not an object")
        world = int(getattr(source, "world_seed"))
        source_lineage = int(getattr(source, "lineage"))
        if source_lineage != int(lineage):
            continue
        if world not in target_worlds:
            continue
        key = (world, source_lineage)
        if key in seen:
            raise V017SoftKLGateError(f"duplicate source shard: {key}")
        seen.add(key)
        if float(getattr(source, "kappa_bits")).hex() != float(OPS3_KAPPA_BITS).hex():
            raise V017SoftKLGateError("source kappa differs from OPS3 authority")
        selected.append((world, source, raw_path))
        receipts.append(
            {
                "path": str(raw_path),
                "world_seed": world,
                "lineage": source_lineage,
                "arrays_sha256": str(source.arrays_sha256()),
                "q1_checkpoint_sha256": str(getattr(source, "q1_checkpoint_sha256")),
                "q2_checkpoint_sha256": str(getattr(source, "q2_checkpoint_sha256")),
                "field_root_digest": str(getattr(source, "field_root_digest")),
                "npz_sha256": str(metadata.get("npz_sha256")),
                "metadata_file_sha256": _file_sha256(metadata_path),
                "source_runner_sha256": str(metadata.get("source_runner_sha256")),
                "contract_sha256": str(metadata.get("contract_sha256")),
            }
        )
    if {world for world, _source, _path in selected} != set(target_worlds):
        raise V017SoftKLGateError(
            f"source closure for lineage {lineage} does not cover declared worlds"
        )
    selected.sort(key=lambda item: item[0])
    if len(
        {
            str(getattr(source, "q1_checkpoint_sha256"))
            for _world, source, _path in selected
        }
    ) != 1:
        raise V017SoftKLGateError("one lineage mixes Q1 checkpoint bytes across worlds")
    q2_digests = {
        str(getattr(source, "q2_checkpoint_sha256"))
        for _world, source, _path in selected
    }
    if q2_digests != {Q2_CHECKPOINT_SHA256_BY_LINEAGE[int(lineage)]}:
        raise V017SoftKLGateError("lineage Q2 checkpoint bytes differ from the frozen mapping")
    if any(
        receipt["source_runner_sha256"] != _file_sha256(SOURCE_RUNNER_PATH)
        or receipt["contract_sha256"] != CONTRACT_SHA256
        for receipt in receipts
    ):
        raise V017SoftKLGateError("source code or contract digest drifted across harvest")
    fields = {
        "q3_states": np.dtype(np.float32),
        "action_masks": np.dtype(np.bool_),
        "q1_values": np.dtype(np.float64),
        "learned_q2_values": np.dtype(np.float64),
        "z3_target_bits": np.dtype(np.float64),
        "q3_compatibility": np.dtype(np.bool_),
        "context_codes": np.dtype(np.int64),
        "reference_actions": np.dtype(np.int64),
        "source_seeds": np.dtype(np.int64),
        "lineages": np.dtype(np.int64),
        "anchor_sha256s": np.dtype("S64"),
        "step_indices": np.dtype(np.int64),
        "user_indices": np.dtype(np.int64),
    }
    arrays = {
        name: _concat(
            [np.asarray(getattr(source, name)) for _world, source, _path in selected],
            dtype=dtype,
        )
        for name, dtype in fields.items()
    }
    result = ReferenceRows(**arrays, shard_receipts=tuple(receipts))
    result.verify()
    if set(np.unique(result.source_seeds).tolist()) != set(target_worlds):
        raise V017SoftKLGateError("row worlds disagree with source closure")
    if set(np.unique(result.lineages).tolist()) != {int(lineage)}:
        raise V017SoftKLGateError("row lineages disagree with source closure")
    return result


def state_alias_diagnostics(rows: ReferenceRows) -> dict[str, object]:
    """Report exact B402 state/mask aliases without affecting the gate."""

    rows.verify()
    states = np.asarray(rows.q3_states)
    masks = np.asarray(rows.action_masks)
    q1 = np.asarray(rows.q1_values)
    q2 = np.asarray(rows.learned_q2_values)
    targets = np.asarray(rows.z3_target_bits)
    contexts = np.asarray(rows.context_codes)
    background = q1 + q2
    background = np.array(background, copy=True)
    background[contexts == 1] = q1[contexts == 1]
    background[contexts == 2] = q2[contexts == 2]
    teachers = _masked_argmax(
        background + targets / float(OPS3_KAPPA_BITS), masks
    )

    first: dict[bytes, tuple[np.ndarray, int]] = {}
    target_conflicts: set[bytes] = set()
    teacher_conflicts: set[bytes] = set()
    duplicate_groups: set[bytes] = set()
    duplicate_rows = 0
    max_target_difference = 0.0
    for index in range(rows.rows):
        key = states[index].tobytes(order="C") + masks[index].tobytes(order="C")
        if key not in first:
            first[key] = (np.array(targets[index], copy=True), int(teachers[index]))
            continue
        duplicate_rows += 1
        duplicate_groups.add(key)
        first_target, first_teacher = first[key]
        difference = float(np.max(np.abs(first_target - targets[index])))
        if difference > 0.0:
            target_conflicts.add(key)
            max_target_difference = max(max_target_difference, difference)
        if first_teacher != int(teachers[index]):
            teacher_conflicts.add(key)
    return {
        "rows": int(rows.rows),
        "unique_state_mask_rows": int(len(first)),
        "duplicate_rows": int(duplicate_rows),
        "duplicate_groups": int(len(duplicate_groups)),
        "target_conflicting_groups": int(len(target_conflicts)),
        "teacher_action_conflicting_groups": int(len(teacher_conflicts)),
        "max_abs_target_conflict_bits": float(max_target_difference),
        "decision_clause": False,
    }


def _batch_for_context(rows: ReferenceRows, code: int) -> B402SoftKLBatch:
    present = set(np.unique(np.asarray(rows.context_codes)).tolist())
    if present == {int(code)}:
        rows.verify(require_context_closure=False)
        context = rows
    else:
        context = rows.context(code)
    q1, q2 = _context_components(
        context.q1_values, context.learned_q2_values, int(code)
    )
    return build_b402_softkl_batch(
        states=context.q3_states,
        action_masks=context.action_masks,
        background_values=q1 + q2,
        z3_target_bits=context.z3_target_bits,
        reference_actions=context.reference_actions,
        kappa_bits=OPS3_KAPPA_BITS,
    )


def _take_balanced(
    batches_by_context: Mapping[int, B402SoftKLBatch],
    *,
    update: int,
    per_context: int = BATCH_PER_CONTEXT,
) -> B402SoftKLBatch:
    """Return one exact equal-size deterministic draw from every context."""

    if set(batches_by_context) != set(CONTEXT_CODES) or update < 1 or per_context < 1:
        raise V017SoftKLGateError("balanced batch declaration is malformed")
    batches: list[B402SoftKLBatch] = []
    for code in CONTEXT_CODES:
        batch = batches_by_context[code]
        start = ((int(update) - 1) * int(per_context)) % batch.rows
        indices = (start + np.arange(per_context, dtype=np.int64)) % batch.rows
        batches.append(batch.take(indices))

    def join(name: str, dtype: np.dtype[Any]) -> np.ndarray:
        return _concat([np.asarray(getattr(batch, name)) for batch in batches], dtype=dtype)

    merged = B402SoftKLBatch(
        states=join("states", np.dtype(np.float32)),
        action_masks=join("action_masks", np.dtype(np.bool_)),
        background_values=join("background_values", np.dtype(np.float64)),
        z3_target_bits=join("z3_target_bits", np.dtype(np.float64)),
        reference_actions=join("reference_actions", np.dtype(np.int64)),
        kappa_bits=float(OPS3_KAPPA_BITS),
    )
    merged.verify()
    return merged


def evaluate_context(
    learner: EEAxisB402SoftKLLearner,
    rows: ReferenceRows,
    code: int,
) -> dict[str, object]:
    """Compute the exact source-only decision metrics for one context."""

    context = rows.context(code)
    q1, q2 = _context_components(
        context.q1_values, context.learned_q2_values, int(code)
    )
    background = q1 + q2
    teacher_values = background + np.asarray(context.z3_target_bits) / float(
        OPS3_KAPPA_BITS
    )
    masks = np.asarray(context.action_masks)
    base = _masked_argmax(background, masks)
    teacher = _masked_argmax(teacher_values, masks)
    q3 = learner.q_values(context.q3_states, masks)
    student = _masked_argmax(background + q3, masks)
    pivotal = teacher != base
    stable = ~pivotal
    changed = student != base
    origin_peer_zero = (
        np.asarray(context.q3_states)[:, V016_C3_REFERENCE_BEAM_GLOBAL_START]
        == 0.0
    )
    changed_rows = np.flatnonzero(changed)
    support = np.zeros(changed_rows.size, dtype=np.bool_)
    if changed_rows.size:
        selected = student[changed_rows]
        references = base[changed_rows]
        positive = (
            np.asarray(context.z3_target_bits)[changed_rows, selected]
            - np.asarray(context.z3_target_bits)[changed_rows, references]
        ) > 0.0
        compatible = np.asarray(context.q3_compatibility)[changed_rows, selected]
        support = positive & compatible
    batch = _batch_for_context(context, int(code))
    measure = learner.measure(batch)
    return {
        "context_code": int(code),
        "rows": int(context.rows),
        "background_teacher_agreement": float(np.mean(base == teacher)),
        "learned_teacher_agreement": float(np.mean(student == teacher)),
        "pivotal_rows": int(np.count_nonzero(pivotal)),
        "pivotal_agreement": (
            float(np.mean(student[pivotal] == teacher[pivotal]))
            if np.any(pivotal)
            else None
        ),
        "stable_rows": int(np.count_nonzero(stable)),
        "stable_preservation": (
            float(np.mean(student[stable] == base[stable])) if np.any(stable) else None
        ),
        "student_change_count": int(changed_rows.size),
        "student_change_rate": float(np.mean(changed)),
        "origin_peer_zero_rows": int(np.count_nonzero(origin_peer_zero)),
        "student_change_count_when_origin_peer_zero": int(
            np.count_nonzero(changed & origin_peer_zero)
        ),
        "student_change_rate_when_origin_peer_zero": (
            float(np.mean(changed[origin_peer_zero]))
            if np.any(origin_peer_zero)
            else None
        ),
        "positive_compatible_support_count": int(np.count_nonzero(support)),
        "positive_compatible_support_fraction": (
            float(np.mean(support)) if support.size else None
        ),
        "teacher_distribution_mean_entropy": _masked_mean_entropy(
            teacher_values, masks
        ),
        "student_distribution_mean_entropy": _masked_mean_entropy(
            background + q3, masks
        ),
        "softkl_measure": measure,
    }


def _q3_config() -> EEAxisV014HeadConfig:
    config = EEAxisV014HeadConfig(
        action_dim=ACTION_DIM,
        local_feature_dim=V016_C3_ORIGIN_LOCAL_FEATURES,
        global_feature_dim=V016_C3_ORIGIN_GLOBAL_FEATURES,
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=0.001,
        kappa_bits=float(OPS3_KAPPA_BITS),
        beta=0.1,
    )
    if config.state_dim != V016_C3_ORIGIN_STATE_DIM:
        raise V017SoftKLGateError("Q3 config does not parse the 402-D state")
    return config


def _code_manifest() -> dict[str, object]:
    paths = (
        Path(__file__),
        SOURCE_RUNNER_PATH,
        REPO / "src" / "mcrl" / "algorithms" / "ee_axis_v014_head.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_b402_c3_softkl.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_v016_c3_origin_state.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_zero_marginal_c3.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_zero_marginal_c3_live.py",
    )
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise V017SoftKLGateError("V0.17 code closure is incomplete")
    files = [
        {
            "path": str(path.resolve().relative_to(REPO.resolve())),
            "sha256": _file_sha256(path),
        }
        for path in sorted(paths, key=lambda item: str(item))
    ]
    body = {"schema": "multi-catfish-mcrl-v017-c3-softkl-code-manifest-v1", "files": files}
    return {**body, "manifest_sha256": canonical_sha256(body)}


def adjudicate_rung_3000(context_reports: Mapping[int, Mapping[str, object]]) -> dict[str, object]:
    """Apply the frozen five-clause gate to one initialization."""

    if set(context_reports) != set(CONTEXT_CODES):
        raise V017SoftKLGateError("decision requires all three contexts")
    full = context_reports[12]
    h1 = context_reports[1]
    h2 = context_reports[2]
    clauses = {
        "full_teacher_agreement_improved": bool(
            float(full["learned_teacher_agreement"])
            > float(full["background_teacher_agreement"])
        ),
        "full_pivotal_agreement_at_least_0_50": bool(
            full["pivotal_agreement"] is not None
            and float(full["pivotal_agreement"]) >= 0.50
        ),
        "full_stable_preservation_at_least_0_95": bool(
            full["stable_preservation"] is not None
            and float(full["stable_preservation"]) >= 0.95
        ),
        "full_has_change_exposure": bool(int(full["student_change_count"]) > 0),
        "full_positive_compatible_support_at_least_0_80": bool(
            full["positive_compatible_support_fraction"] is not None
            and float(full["positive_compatible_support_fraction"]) >= 0.80
        ),
        "h1_teacher_agreement_noninferior": bool(
            float(h1["learned_teacher_agreement"])
            >= float(h1["background_teacher_agreement"])
        ),
        "h2_teacher_agreement_noninferior": bool(
            float(h2["learned_teacher_agreement"])
            >= float(h2["background_teacher_agreement"])
        ),
        # Reaching adjudication means source/schema/digest/context/split checks
        # and the finite learner boundary have already completed without an
        # exception.  Persist that mechanical fifth clause explicitly.
        "integrity_and_split_checks_passed": True,
    }
    return {"passed": bool(all(clauses.values())), "clauses": clauses}


def _write_once_bytes(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise V017SoftKLGateError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise V017SoftKLGateError(f"refusing to overwrite {path}") from error
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return _file_sha256(path)


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise V017SoftKLGateError("cannot serialize a non-finite metric")
        return parsed
    if isinstance(value, Path):
        return str(value)
    return value


def _write_once_json(path: Path, payload: Mapping[str, object]) -> str:
    encoded = (
        json.dumps(
            _jsonable(payload),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")
    return _write_once_bytes(path, encoded)


def _write_once_torch(path: Path, payload: Mapping[str, object]) -> str:
    if path.exists() or path.is_symlink():
        raise V017SoftKLGateError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    try:
        torch.save(dict(payload), temporary)
        with open(temporary, "rb") as handle:
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise V017SoftKLGateError(f"refusing to overwrite {path}") from error
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return _file_sha256(path)


def _train_one(
    *,
    train: ReferenceRows,
    validation: ReferenceRows,
    initialization_seed: int,
    lineage: int,
    destination: Path,
) -> dict[str, object]:
    train_batches = {code: _batch_for_context(train, code) for code in CONTEXT_CODES}
    learner = EEAxisB402SoftKLLearner(
        _q3_config(), train_seed=int(initialization_seed), device="cpu"
    )
    reports: dict[str, object] = {}
    train_source_sha256 = canonical_sha256(list(train.shard_receipts))
    validation_source_sha256 = canonical_sha256(list(validation.shard_receipts))
    completed = 0
    for rung in UPDATE_RUNGS:
        for update in range(completed + 1, int(rung) + 1):
            learner.update(_take_balanced(train_batches, update=update))
        completed = int(rung)
        contexts = {
            code: evaluate_context(learner, validation, code) for code in CONTEXT_CODES
        }
        decision = adjudicate_rung_3000(contexts) if rung == 3000 else None
        checkpoint = {
            "schema": CHECKPOINT_SCHEMA,
            "runner_schema": RUNNER_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "contract_sha256": CONTRACT_SHA256,
            "initialization_seed": int(initialization_seed),
            "source_lineage": int(lineage),
            "update_rung": int(rung),
            "batch_per_context": BATCH_PER_CONTEXT,
            "contexts_per_batch": list(CONTEXT_CODES),
            "train_source_sha256": train_source_sha256,
            "validation_source_sha256": validation_source_sha256,
            "q3": learner.checkpoint_state(update_count=int(rung)),
            "validation_contexts": contexts,
            "decision": decision,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "episode_training": False,
        }
        path = destination / "checkpoints" / (
            f"init-{initialization_seed}-rung-{rung:06d}.pt"
        )
        digest = _write_once_torch(path, checkpoint)
        reports[str(rung)] = {
            "validation_contexts": contexts,
            "decision": decision,
            "checkpoint": str(path),
            "checkpoint_sha256": digest,
        }
    return {
        "initialization_seed": int(initialization_seed),
        "source_lineage": int(lineage),
        "train_rows": train.rows,
        "validation_rows": validation.rows,
        "train_source_sha256": train_source_sha256,
        "validation_source_sha256": validation_source_sha256,
        "state_alias_diagnostics": {
            "train": state_alias_diagnostics(train),
            "validation": state_alias_diagnostics(validation),
        },
        "train_rows_by_context": {
            str(code): {
                "rows": train_batches[code].rows,
                "one_action_rows": int(
                    np.count_nonzero(
                        np.sum(train_batches[code].action_masks, axis=1) == 1
                    )
                ),
            }
            for code in CONTEXT_CODES
        },
        "rungs": reports,
    }


def run(*, source_paths: Sequence[str | Path], output_dir: str | Path) -> dict[str, object]:
    """Run the exact frozen source-only panel and write immutable receipts."""

    validate_frozen_contract()
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise V017SoftKLGateError(f"refusing to overwrite output directory {destination}")
    destination.mkdir(parents=True, exist_ok=False)
    reports: dict[str, object] = {}
    source_receipts: dict[str, object] = {}
    for initialization, lineage in zip(
        INITIALIZATION_SEEDS, SOURCE_LINEAGES, strict=True
    ):
        train = load_reference_rows(
            source_paths, lineage=lineage, worlds=TRAIN_WORLD_SEEDS
        )
        validation = load_reference_rows(
            source_paths, lineage=lineage, worlds=VALIDATION_WORLD_SEEDS
        )
        reports[str(initialization)] = _train_one(
            train=train,
            validation=validation,
            initialization_seed=initialization,
            lineage=lineage,
            destination=destination,
        )
        source_receipts[str(lineage)] = {
            "train": list(train.shard_receipts),
            "validation": list(validation.shard_receipts),
        }
    field_roots: dict[int, set[str]] = {}
    for by_split in source_receipts.values():
        for split in ("train", "validation"):
            for receipt in by_split[split]:
                field_roots.setdefault(int(receipt["world_seed"]), set()).add(
                    str(receipt["field_root_digest"])
                )
    if any(len(values) != 1 for values in field_roots.values()):
        raise V017SoftKLGateError(
            "one fresh world does not share a common keyed field across lineages"
        )
    per_init_pass = {
        seed: bool(
            reports[str(seed)]["rungs"]["3000"]["decision"]["passed"]
        )
        for seed in INITIALIZATION_SEEDS
    }
    passed = bool(all(per_init_pass.values()))
    result = {
        "schema": RESULT_SCHEMA,
        "runner_schema": RUNNER_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "contract_path": str(CONTRACT_PATH),
        "contract_sha256": CONTRACT_SHA256,
        "q3_state_schema": V016_C3_ORIGIN_STATE_SCHEMA,
        "q3_state_dim": V016_C3_ORIGIN_STATE_DIM,
        "train_world_seeds": list(TRAIN_WORLD_SEEDS),
        "validation_world_seeds": list(VALIDATION_WORLD_SEEDS),
        "source_lineages": list(SOURCE_LINEAGES),
        "initialization_seeds": list(INITIALIZATION_SEEDS),
        "update_rungs": list(UPDATE_RUNGS),
        "balanced_batch": {
            "context_order": list(CONTEXT_CODES),
            "per_context": BATCH_PER_CONTEXT,
            "total": BATCH_PER_CONTEXT * len(CONTEXT_CODES),
        },
        "objective": {
            "name": "masked-row-mean-soft-teacher-kl",
            "temperature": 1.0,
            "reference_gauge_beta": 0.1,
            "all_legal_actions": True,
            "one_action_rows_included": True,
        },
        "source_receipts": source_receipts,
        "field_root_digest_by_world": {
            str(world): next(iter(values)) for world, values in sorted(field_roots.items())
        },
        "code_manifest": _code_manifest(),
        "reports": reports,
        "per_initialization_pass": per_init_pass,
        "passed": passed,
        "decision": "PASS_SOFTKL_GATE" if passed else "FAIL_SOFTKL_GATE",
        "next_authority": (
            "AUTHORIZE_100EP_FIVE_ARM_PREREG_ONLY"
            if passed
            else "STOP_C3_B402_ACTION_SHARED_STRUCTURALLY"
        ),
        "source_only": True,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }
    result_path = destination / "result.json"
    result_sha256 = _write_once_json(result_path, result)
    _write_once_json(
        destination / "receipt.json",
        {
            "schema": "multi-catfish-mcrl-v017-c3-softkl-gate-receipt-v1",
            "result_path": str(result_path),
            "result_sha256": result_sha256,
            "decision": result["decision"],
            "claim_ceiling": CLAIM_CEILING,
        },
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    run(source_paths=args.source, output_dir=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
