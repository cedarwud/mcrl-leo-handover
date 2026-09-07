#!/usr/bin/env python3
"""Refit the frozen Q1/Q2 learners at the one predeclared lambda prime.

This is a source-only development runner.  It authenticates and reuses the
already-opened C1 and V0.14 OPS3 sources, verifies that both old targets and
the old Q1 surfaces can be reconstructed, and then trains one fixed Q1/Q2
lineage.  It never imports a simulator environment, opens TEST, trains an
episode policy, or evaluates trajectory EE.

Run one ``train`` process for each frozen lineage and then one ``merge``.
Every output directory is write-once.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_action_shared_meanmax import (  # noqa: E402
    EEAxisMaskedMeanMaxConfig,
    EEAxisMaskedMeanMaxTrainer,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch  # noqa: E402
from mcrl.algorithms.ee_axis_v014_head import EEAxisV014PairwiseLearner  # noqa: E402
from mcrl.runtime.ee_axis_v014_learnability import (  # noqa: E402
    CompactHeadSurfaceDataset,
)
from mcrl.runtime.ee_axis_v04_c3_learnability import (  # noqa: E402
    compute_anchor_seed_balanced_generalization,
)


CONTRACT = HERE / "Q1-Q2-REPRICED-SUPERVISED-EXECUTION-CONTRACT-2026-09-04.md"
CONTRACT_SHA256 = "ea36414aac87b3ef5ba48dbe753e73ff21a0e164d54cdb3edbb899b509edd48c"
REPRICING_CONTRACT = HERE / "Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md"
REPRICING_CONTRACT_SHA256 = "34732dd3f65ffebf760313c2ffd235e0ecbd406ba6065dbce5635778550ef4a9"
Q1_REPRICE_PATH = HERE / "q1-repricing" / "reprice_c1.py"
Q2_GATE_PATH = REPO / ".scratch" / "multi-catfish-v014-learner" / "run_v014_learner_gate.py"
V015_PATH = REPO / ".scratch" / "multi-catfish-v015-c3-learned-context" / "run_v015_c3_learned_context_oracle.py"
Q1_AUTHORITY = REPO / "artifacts" / "multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1" / "authority.json"
Q2_SOURCE_ROOT = REPO / "artifacts" / "multi-catfish-v014-learnability-20260903-r1" / "server-run" / "source-panel" / "shards"
Q2_REPRICE_ROOT = HERE / "q2-batch-repricing" / "shards"

SCHEMA = "multi-catfish-mcrl-v020-repriced-q1-q2-source-fit-v1"
AUTHORITY_SCHEMA = f"{SCHEMA}-authority"
CHECKPOINT_SCHEMA = f"{SCHEMA}-checkpoint"
RESULT_SCHEMA = f"{SCHEMA}-result"
MERGE_SCHEMA = f"{SCHEMA}-merge-v1"
CLAIM_CEILING = "SOURCE_ONLY_NO_SIMULATOR_NO_TEST_NO_EPISODE_EE"

NEW_LAMBDA = float.fromhex("0x1.c3c0a7b6b86d3p+26")
Q1_INITIALIZATIONS = (2026092101, 2026092102, 2026092103)
Q2_INITIALIZATIONS = (2026108101, 2026108102, 2026108103)
LINEAGE_TO_Q2_INIT = dict(zip(Q1_INITIALIZATIONS, Q2_INITIALIZATIONS, strict=True))
Q1_TRAIN_WORLDS = tuple(range(2026092001, 2026092005))
Q1_VALIDATION_WORLDS = tuple(range(2026092005, 2026092008))
Q2_TRAIN_WORLDS = tuple(range(2026108001, 2026108005))
Q2_VALIDATION_WORLDS = tuple(range(2026108005, 2026108008))
Q1_UPDATES = 10
Q2_RUNGS = (3, 10, 30, 100, 300, 1000, 3000)
Q2_BATCH_SIZE = 512
TORCH_THREADS = 1
Q1_PARAMETER_REPRODUCTION_TOLERANCE = 1.0e-6
Q1_SURFACE_RECONSTRUCTION_TOLERANCE = 1.0e-6


class RepricedFitError(RuntimeError):
    """A fixed source, configuration, or execution invariant failed."""


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RepricedFitError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise RepricedFitError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _write_once_json(path: Path, payload: Mapping[str, object]) -> str:
    if path.exists() or path.is_symlink():
        raise RepricedFitError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("ascii")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary_name, path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    return _sha256(path)


def _write_status(path: Path, payload: Mapping[str, object]) -> None:
    data = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("ascii")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def _write_once_torch(path: Path, payload: Mapping[str, object]) -> str:
    if path.exists() or path.is_symlink():
        raise RepricedFitError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    try:
        torch.save(dict(payload), temporary_name)
        with open(temporary_name, "rb") as handle:
            os.fsync(handle.fileno())
        os.link(temporary_name, path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    return _sha256(path)


def _float_hex_vector(values: Sequence[object], *, field: str) -> np.ndarray:
    try:
        result = np.asarray([float.fromhex(str(value)) for value in values], dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise RepricedFitError(f"{field} is not a hexadecimal float vector") from error
    if not np.all(np.isfinite(result)):
        raise RepricedFitError(f"{field} is non-finite")
    return result


@dataclass(frozen=True)
class Q1PairData:
    batch: EEAxisPairBatch
    source_seeds: np.ndarray
    anchor_sha256s: np.ndarray
    old_targets: np.ndarray
    new_targets: np.ndarray


def _q1_config() -> EEAxisMaskedMeanMaxConfig:
    payload = json.loads(Q1_AUTHORITY.read_text(encoding="ascii"))
    raw = dict(payload["fallback_config"])
    raw["hidden_layers"] = tuple(raw["hidden_layers"])
    raw["loss_weights"] = tuple(raw["loss_weights"])
    return EEAxisMaskedMeanMaxConfig(**raw)


def _load_q1_split(worlds: Sequence[int]) -> Q1PairData:
    module = _load_module("v020_q1_reprice_for_fit", Q1_REPRICE_PATH)
    receipt = module._load_source_receipt()
    states: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    references: list[int] = []
    candidates: list[int] = []
    old_targets: list[float] = []
    new_targets: list[float] = []
    seeds: list[int] = []
    anchors: list[str] = []
    for seed in worlds:
        source = module._load_source(int(seed), receipt)
        for row_index, row in enumerate(source["rows"]):
            if row.get("admitted_route") != "C1":
                continue
            record = module._validate_admitted_c1_row(
                row, seed=int(seed), row_index=int(row_index)
            )
            raw = row["raw"]
            state = _float_hex_vector(raw["state"], field="Q1 state").astype(np.float32)
            mask = np.asarray(raw["action_mask"])
            if state.shape != (228,) or mask.dtype != np.bool_ or mask.shape != (28,):
                raise RepricedFitError("Q1 source state/mask shape drifted")
            states.append(state)
            masks.append(mask)
            references.append(int(raw["reference_action"]))
            candidates.append(int(raw["candidate_action"]))
            old_targets.append(float.fromhex(record["persisted_old_target_hex"]))
            new_targets.append(float.fromhex(record["repriced_new_target_hex"]))
            seeds.append(int(seed))
            anchors.append(str(raw["anchor_sha256"]))
    old = np.asarray(old_targets, dtype=np.float64)
    new = np.asarray(new_targets, dtype=np.float64)
    if not states or not np.all(np.isfinite(old)) or not np.all(np.isfinite(new)):
        raise RepricedFitError("Q1 split is empty or non-finite")
    batch = EEAxisPairBatch(
        states=np.stack(states),
        action_masks=np.stack(masks),
        reference_actions=np.asarray(references, dtype=np.int64),
        candidate_actions=np.asarray(candidates, dtype=np.int64),
        target_surplus_bits=new,
    )
    batch.validate(state_dim=228, action_dim=28)
    return Q1PairData(
        batch=batch,
        source_seeds=np.asarray(seeds, dtype=np.int64),
        anchor_sha256s=np.asarray(anchors, dtype="U64"),
        old_targets=old,
        new_targets=new,
    )


def _batch_with_targets(data: Q1PairData, targets: np.ndarray) -> EEAxisPairBatch:
    return EEAxisPairBatch(
        states=data.batch.states,
        action_masks=data.batch.action_masks,
        reference_actions=data.batch.reference_actions,
        candidate_actions=data.batch.candidate_actions,
        target_surplus_bits=np.asarray(targets, dtype=np.float64),
    )


def _train_q1(
    *, seed: int, train: Q1PairData, targets: np.ndarray
) -> EEAxisMaskedMeanMaxTrainer:
    trainer = EEAxisMaskedMeanMaxTrainer(_q1_config(), train_seed=seed, device="cpu")
    batch = _batch_with_targets(train, targets)
    for _update in range(Q1_UPDATES):
        trainer.update_route("C1", batch)
    return trainer


def _q1_old_parameter_reproduction(
    *, seed: int, train: Q1PairData, old_network: Any
) -> dict[str, object]:
    reproduced = _train_q1(seed=seed, train=train, targets=train.old_targets)
    actual = reproduced.q_nets[0].state_dict()
    expected = old_network.state_dict()
    if set(actual) != set(expected):
        raise RepricedFitError("old Q1 parameter names changed")
    per_tensor = {
        name: float(torch.max(torch.abs(actual[name] - expected[name])).cpu())
        for name in actual
    }
    maximum = max(per_tensor.values())
    return {
        "maximum_absolute_parameter_error": maximum,
        "tolerance": Q1_PARAMETER_REPRODUCTION_TOLERANCE,
        "passed": maximum <= Q1_PARAMETER_REPRODUCTION_TOLERANCE,
        "per_tensor_maximum_absolute_error": per_tensor,
    }


def _q1_report(
    trainer: EEAxisMaskedMeanMaxTrainer,
    *,
    train: Q1PairData,
    validation: Q1PairData,
) -> dict[str, object]:
    q = trainer.q_values(validation.batch.states, validation.batch.action_masks)[0]
    report = compute_anchor_seed_balanced_generalization(
        train_batch=train.batch,
        validation_batch=validation.batch,
        validation_source_seeds=validation.source_seeds,
        validation_anchor_sha256s=validation.anchor_sha256s,
        heldout_q_surface=q,
        state_dim=228,
        action_dim=28,
        kappa_bits=trainer.config.kappa_bits,
    )
    return report.as_dict()


def reconstruct_q1_states_from_v014_q3(q3_states: object) -> np.ndarray:
    """Recover the sealed V0.3 228-D state from the richer V0.14 Q3 view."""

    q3 = np.asarray(q3_states, dtype=np.float32)
    if q3.ndim != 2 or q3.shape[1] != 287 or not np.all(np.isfinite(q3)):
        raise RepricedFitError("V0.14 Q3 states must be finite shape (N,287)")
    continuation = q3[:, 8 * 28 : 9 * 28]
    nonfocal_load = q3[:, 9 * 28 : 10 * 28]
    beam_active = q3[:, 5 * 28 : 6 * 28]
    satellite_burden = q3[:, 6 * 28 : 7 * 28]
    satellite_active = np.zeros_like(beam_active)
    for slot in range(4):
        start = slot * 7
        stop = start + 7
        active = (
            np.max(beam_active[:, start:stop], axis=1) > 0.0
        ) | (
            np.max(satellite_burden[:, start:stop], axis=1) > 0.0
        )
        satellite_active[:, start:stop] = active[:, None]
    result = np.concatenate(
        (
            q3[:, : 4 * 28],
            nonfocal_load + continuation / 100.0,
            beam_active,
            satellite_active,
            q3[:, 7 * 28 : 8 * 28],
            q3[:, 10 * 28 : 10 * 28 + 4],
        ),
        axis=1,
        dtype=np.float32,
    )
    if result.shape != (q3.shape[0], 228):
        raise RepricedFitError("reconstructed Q1 state has the wrong shape")
    return result


def _v014_q1_surface_reconstruction(
    *, source: Any, old_network: Any
) -> tuple[dict[str, object], np.ndarray, np.ndarray]:
    split_outputs: list[np.ndarray] = []
    maximum = 0.0
    agreements = 0
    rows = 0
    legal_cells = 0
    for split in (source.train, source.validation):
        states = reconstruct_q1_states_from_v014_q3(split.q3.states)
        with torch.no_grad():
            predicted = old_network(
                torch.tensor(states, dtype=torch.float32),
                torch.tensor(split.q3.masks, dtype=torch.bool),
            ).detach().cpu().numpy().astype(np.float64)
        stored = np.asarray(split.q1_values, dtype=np.float64)
        masks = np.asarray(split.q3.masks, dtype=np.bool_)
        error = np.abs(predicted - stored)
        maximum = max(maximum, float(np.max(error[masks])))
        old_action = np.argmax(np.where(masks, stored, -np.inf), axis=1)
        new_action = np.argmax(np.where(masks, predicted, -np.inf), axis=1)
        agreements += int(np.count_nonzero(old_action == new_action))
        rows += int(states.shape[0])
        legal_cells += int(np.count_nonzero(masks))
        split_outputs.append(states)
    agreement = agreements / rows
    receipt = {
        "rows": rows,
        "legal_cells": legal_cells,
        "maximum_absolute_legal_q_error": maximum,
        "masked_argmax_agreement": agreement,
        "error_tolerance": Q1_SURFACE_RECONSTRUCTION_TOLERANCE,
        "passed": maximum <= Q1_SURFACE_RECONSTRUCTION_TOLERANCE and agreement == 1.0,
    }
    return receipt, split_outputs[0], split_outputs[1]


def _all_q2_source_paths() -> list[Path]:
    paths = sorted(path for path in Q2_SOURCE_ROOT.iterdir() if path.is_dir())
    if len(paths) != 21:
        raise RepricedFitError(f"expected 21 V0.14 shards, found {len(paths)}")
    return paths


def _repriced_q2_targets(worlds: Sequence[int], lineage: int) -> np.ndarray:
    arrays: list[np.ndarray] = []
    for world in worlds:
        path = Q2_REPRICE_ROOT / f"{int(world)}-{int(lineage)}" / "q2_target_bits_repriced.npy"
        if path.is_symlink() or not path.is_file():
            raise RepricedFitError(f"missing repriced Q2 target: {path}")
        value = np.asarray(np.load(path, allow_pickle=False), dtype=np.float64)
        if value.shape != (1000, 28) or not np.all(np.isfinite(value)):
            raise RepricedFitError(f"repriced Q2 target shape/finiteness drifted: {path}")
        arrays.append(value)
    return np.concatenate(arrays, axis=0)


def _replace_q2_targets(dataset: CompactHeadSurfaceDataset, targets: np.ndarray) -> CompactHeadSurfaceDataset:
    value = np.asarray(targets, dtype=np.float64)
    if value.shape != dataset.target_surfaces_bits.shape:
        raise RepricedFitError("repriced Q2 rows do not align with source rows")
    if np.any(value[~dataset.masks] != 0.0):
        raise RepricedFitError("repriced Q2 target is nonzero outside legal actions")
    return CompactHeadSurfaceDataset(
        states=dataset.states,
        masks=dataset.masks,
        reference_actions=dataset.reference_actions,
        target_surfaces_bits=value,
        source_seeds=dataset.source_seeds,
        anchor_sha256s=dataset.anchor_sha256s,
    )


def _masked_actions(scores: np.ndarray, masks: np.ndarray) -> np.ndarray:
    return np.argmax(np.where(masks, scores, -np.inf), axis=1).astype(np.int64)


def _run_lineage(*, lineage: int, q2_init: int, output: Path) -> dict[str, object]:
    if LINEAGE_TO_Q2_INIT.get(lineage) != q2_init:
        raise RepricedFitError("lineage/Q2 initialization mapping is not frozen")
    if output.exists() or output.is_symlink():
        raise RepricedFitError(f"refusing to overwrite output {output}")
    if _sha256(CONTRACT) != CONTRACT_SHA256 or _sha256(REPRICING_CONTRACT) != REPRICING_CONTRACT_SHA256:
        raise RepricedFitError("execution or repricing contract bytes changed")
    torch.set_num_threads(TORCH_THREADS)
    torch.set_num_interop_threads(1)

    q1_train = _load_q1_split(Q1_TRAIN_WORLDS)
    q1_validation = _load_q1_split(Q1_VALIDATION_WORLDS)
    v014 = _load_module("v020_v014_gate_for_fit", Q2_GATE_PATH)
    source = v014.load_source_shards(
        _all_q2_source_paths(),
        train_world_seeds=Q2_TRAIN_WORLDS,
        validation_world_seeds=Q2_VALIDATION_WORLDS,
        lineage=lineage,
    )
    q2_train = _replace_q2_targets(
        source.train.q2, _repriced_q2_targets(Q2_TRAIN_WORLDS, lineage)
    )
    q2_validation = _replace_q2_targets(
        source.validation.q2, _repriced_q2_targets(Q2_VALIDATION_WORLDS, lineage)
    )
    v015 = _load_module("v020_v015_for_fit", V015_PATH)
    old_q1, old_q1_receipt = v015.load_frozen_q1(v015.V03_ROOT, lineage)
    parameter_reproduction = _q1_old_parameter_reproduction(
        seed=lineage, train=q1_train, old_network=old_q1
    )
    state_reconstruction, q1_panel_train_states, q1_panel_validation_states = (
        _v014_q1_surface_reconstruction(source=source, old_network=old_q1)
    )
    if not parameter_reproduction["passed"] or not state_reconstruction["passed"]:
        raise RepricedFitError("Q1 source/state reproduction gate failed before refit")

    code_files = (Path(__file__), Q1_REPRICE_PATH, Q2_GATE_PATH, V015_PATH)
    q2_target_files = [
        Q2_REPRICE_ROOT / f"{world}-{lineage}" / "q2_target_bits_repriced.npy"
        for world in (*Q2_TRAIN_WORLDS, *Q2_VALIDATION_WORLDS)
    ]
    authority_body: dict[str, object] = {
        "schema": AUTHORITY_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": CONTRACT_SHA256,
        "repricing_contract_sha256": REPRICING_CONTRACT_SHA256,
        "lambda_bits_per_j": NEW_LAMBDA,
        "lambda_bits_per_j_hex": NEW_LAMBDA.hex(),
        "lineage": lineage,
        "q2_initialization": q2_init,
        "q1_updates": Q1_UPDATES,
        "q2_rungs": list(Q2_RUNGS),
        "q2_batch_size": Q2_BATCH_SIZE,
        "torch_threads": TORCH_THREADS,
        "q1_config": asdict(_q1_config()),
        "q2_config": asdict(v014.V014GateSpec().q2_config()),
        "source_sha256": source.source_sha256,
        "q2_repriced_target_file_sha256s": {
            str(path.relative_to(REPO)): _sha256(path) for path in q2_target_files
        },
        "code_file_sha256s": {
            str(path.relative_to(REPO)): _sha256(path) for path in code_files
        },
        "test_split_opened": False,
        "simulator_run": False,
        "episode_training": False,
    }
    authority_body["authority_sha256"] = _canonical_sha256(authority_body)
    output.mkdir(parents=True, exist_ok=False)
    checkpoints = output / "checkpoints"
    checkpoints.mkdir()
    authority_file_sha256 = _write_once_json(output / "authority.json", authority_body)
    _write_status(
        output / "status.json",
        {
            "schema": SCHEMA,
            "status": "RUNNING",
            "lineage": lineage,
            "q2_initialization": q2_init,
            "last_completed_q2_rung": 0,
        },
    )

    q1 = _train_q1(seed=lineage, train=q1_train, targets=q1_train.new_targets)
    q1_report = _q1_report(q1, train=q1_train, validation=q1_validation)
    q2 = EEAxisV014PairwiseLearner(
        v014.V014GateSpec().q2_config(), train_seed=q2_init, device="cpu"
    )
    q2_reports: dict[int, dict[str, object]] = {}
    checkpoint_hashes: dict[int, str] = {}
    completed = 0
    for rung in Q2_RUNGS:
        for update in range(completed + 1, rung + 1):
            indices = v014._batch_indices(
                rows=q2_train.rows, batch_size=Q2_BATCH_SIZE, update=update
            )
            q2.update_surfaces(
                q2_train.states[indices],
                q2_train.masks[indices],
                q2_train.reference_actions[indices],
                q2_train.target_surfaces_bits[indices],
            )
        completed = rung
        report = v014._head_report(
            q2,
            train=q2_train,
            validation=q2_validation,
            kappa_bits=float(v014.OPS3_KAPPA_BITS),
        )
        q2_reports[rung] = report.as_dict()
        checkpoint_payload = {
            "schema": CHECKPOINT_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "authority_sha256": authority_body["authority_sha256"],
            "lineage": lineage,
            "q2_initialization": q2_init,
            "q1_update_count": Q1_UPDATES,
            "q2_update_count": rung,
            "q1_head_index": 0,
            "q1": q1.checkpoint_state(update_count=Q1_UPDATES),
            "q2": q2.checkpoint_state(update_count=rung),
            "q1_report": q1_report,
            "q2_report": q2_reports[rung],
            "test_split_opened": False,
            "simulator_run": False,
            "episode_training": False,
        }
        checkpoint_hashes[rung] = _write_once_torch(
            checkpoints / f"lineage-{lineage}-q2init-{q2_init}-rung-{rung:06d}.pt",
            checkpoint_payload,
        )
        _write_status(
            output / "status.json",
            {
                "schema": SCHEMA,
                "status": "RUNNING",
                "lineage": lineage,
                "q2_initialization": q2_init,
                "last_completed_q2_rung": rung,
                "q1_skill": q1_report["skill_vs_strongest_null"],
                "q2_skill": q2_reports[rung]["skill_vs_strongest_null"],
            },
        )

    q1_train_surface = q1.q_values(q1_panel_train_states, source.train.q2.masks)[0]
    q1_validation_surface = q1.q_values(
        q1_panel_validation_states, source.validation.q2.masks
    )[0]
    q2_train_surface = q2.q_values(q2_train.states, q2_train.masks)
    q2_validation_surface = q2.q_values(q2_validation.states, q2_validation.masks)
    train_actions = _masked_actions(q1_train_surface + q2_train_surface, q2_train.masks)
    validation_actions = _masked_actions(
        q1_validation_surface + q2_validation_surface, q2_validation.masks
    )
    reference_path = output / "repriced-q1-q2-reference-actions.npz"
    np.savez_compressed(
        reference_path,
        train_actions=train_actions,
        validation_actions=validation_actions,
        train_source_seeds=q2_train.source_seeds,
        validation_source_seeds=q2_validation.source_seeds,
        train_anchor_sha256s=q2_train.anchor_sha256s.astype("S64"),
        validation_anchor_sha256s=q2_validation.anchor_sha256s.astype("S64"),
    )
    reference_sha256 = _sha256(reference_path)
    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "status": "COMPLETE_SOURCE_ONLY",
        "claim_ceiling": CLAIM_CEILING,
        "authority_sha256": authority_body["authority_sha256"],
        "authority_file_sha256": authority_file_sha256,
        "lineage": lineage,
        "q2_initialization": q2_init,
        "q1_old_parameter_reproduction": parameter_reproduction,
        "q1_v014_state_surface_reconstruction": state_reconstruction,
        "q1_report": q1_report,
        "q2_reports": {str(rung): value for rung, value in q2_reports.items()},
        "fixed_deployment_rungs": {"q1": Q1_UPDATES, "q2": Q2_RUNGS[-1]},
        "checkpoint_file_sha256s": {
            str(rung): value for rung, value in checkpoint_hashes.items()
        },
        "reference_actions_file": reference_path.name,
        "reference_actions_file_sha256": reference_sha256,
        "reference_action_counts": {
            "train": np.bincount(train_actions, minlength=28).tolist(),
            "validation": np.bincount(validation_actions, minlength=28).tolist(),
        },
        "test_split_opened": False,
        "simulator_run": False,
        "episode_training": False,
    }
    result_sha256 = _write_once_json(output / "result.json", result)
    _write_status(output / "status.json", {**result, "result_file_sha256": result_sha256})
    return {**result, "result_file_sha256": result_sha256}


def _gate_skills(skills: Sequence[float]) -> dict[str, object]:
    values = np.asarray(skills, dtype=np.float64)
    if values.shape != (3,) or not np.all(np.isfinite(values)):
        raise RepricedFitError("gate requires exactly three finite skills")
    positive = int(np.count_nonzero(values > 0.0))
    mean = float(np.mean(values))
    return {
        "skills": values.tolist(),
        "positive_initializations": positive,
        "mean_skill": mean,
        "passed": positive >= 2 and mean > 0.0,
    }


def _merge(inputs: Sequence[Path], output: Path) -> dict[str, object]:
    if output.exists() or output.is_symlink():
        raise RepricedFitError(f"refusing to overwrite merge output {output}")
    rows: list[dict[str, Any]] = []
    for root in inputs:
        path = root / "result.json"
        payload = json.loads(path.read_text(encoding="ascii"))
        if payload.get("schema") != RESULT_SCHEMA or payload.get("status") != "COMPLETE_SOURCE_ONLY":
            raise RepricedFitError(f"incomplete lineage result: {path}")
        payload["result_file_sha256"] = _sha256(path)
        rows.append(payload)
    rows.sort(key=lambda row: int(row["lineage"]))
    if [int(row["lineage"]) for row in rows] != list(Q1_INITIALIZATIONS):
        raise RepricedFitError("merge inputs do not cover the three frozen lineages")
    if [int(row["q2_initialization"]) for row in rows] != list(Q2_INITIALIZATIONS):
        raise RepricedFitError("merge inputs do not cover the three Q2 initializations")
    q1_gate = _gate_skills(
        [float(row["q1_report"]["skill_vs_strongest_null"]) for row in rows]
    )
    q2_gate = _gate_skills(
        [float(row["q2_reports"][str(Q2_RUNGS[-1])]["skill_vs_strongest_null"]) for row in rows]
    )
    reconstruction_rows = sum(
        int(row["q1_v014_state_surface_reconstruction"]["rows"]) for row in rows
    )
    reconstruction_max = max(
        float(row["q1_v014_state_surface_reconstruction"]["maximum_absolute_legal_q_error"])
        for row in rows
    )
    reconstruction_agreement = min(
        float(row["q1_v014_state_surface_reconstruction"]["masked_argmax_agreement"])
        for row in rows
    )
    reproduction_max = max(
        float(row["q1_old_parameter_reproduction"]["maximum_absolute_parameter_error"])
        for row in rows
    )
    passed = bool(
        q1_gate["passed"]
        and q2_gate["passed"]
        and reconstruction_rows == 21000
        and reconstruction_max <= Q1_SURFACE_RECONSTRUCTION_TOLERANCE
        and reconstruction_agreement == 1.0
        and reproduction_max <= Q1_PARAMETER_REPRODUCTION_TOLERANCE
    )
    result: dict[str, object] = {
        "schema": MERGE_SCHEMA,
        "status": "GO_MATCHED_C3_GATE" if passed else "STOP_REPRICED_Q1_Q2",
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": CONTRACT_SHA256,
        "lambda_bits_per_j": NEW_LAMBDA,
        "lambda_bits_per_j_hex": NEW_LAMBDA.hex(),
        "q1_gate": q1_gate,
        "q2_gate": q2_gate,
        "q1_old_parameter_reproduction_maximum_error": reproduction_max,
        "q1_v014_state_reconstruction": {
            "rows": reconstruction_rows,
            "maximum_absolute_legal_q_error": reconstruction_max,
            "minimum_masked_argmax_agreement": reconstruction_agreement,
        },
        "lineage_results": [
            {
                "lineage": row["lineage"],
                "q2_initialization": row["q2_initialization"],
                "result_file_sha256": row["result_file_sha256"],
                "authority_sha256": row["authority_sha256"],
                "checkpoint_rung_3000_sha256": row["checkpoint_file_sha256s"]["3000"],
            }
            for row in rows
        ],
        "next_action": "one predeclared matched C3 gate" if passed else "stop and report the failed fixed head gate",
        "test_split_opened": False,
        "simulator_run": False,
        "episode_training": False,
    }
    output.mkdir(parents=True, exist_ok=False)
    result_sha256 = _write_once_json(output / "result.json", result)
    _write_once_json(
        output / "result-seal.json",
        {"schema": f"{MERGE_SCHEMA}-seal", "result_file_sha256": result_sha256},
    )
    return {**result, "result_file_sha256": result_sha256}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    train = commands.add_parser("train")
    train.add_argument("--lineage", type=int, required=True)
    train.add_argument("--q2-init", type=int, required=True)
    train.add_argument("--output", type=Path, required=True)
    merge = commands.add_parser("merge")
    merge.add_argument("--input", type=Path, action="append", required=True)
    merge.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "train":
        result = _run_lineage(lineage=args.lineage, q2_init=args.q2_init, output=args.output)
    else:
        result = _merge(args.input, args.output)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
