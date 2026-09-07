#!/usr/bin/env python3
"""Checkpointed F3 structured-Q3 observability and composition screen.

Each ``--job WORLD:SEED`` performs the paired INFORMED/NEUTRAL LOWO fit.
``--merge`` authenticates all twelve terminal jobs, applies the imported R7
learner arithmetic, then applies the mandatory R7-threshold composition veto.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys
import traceback
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import torch

import f3_common as common
import build_f3_source_artifact as source_builder
import r7_balanced_successor_gate as r7_metrics
from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3QNetwork
from mcrl.runtime.ee_axis_lcsrs_c3_learner import (
    lcsrs_c3_network_sha256,
    make_lcsrs_c3_student,
)
from mcrl.runtime.ee_axis_lcsrs_c3_state import C3View


HERE = common.HERE
DEFAULT_PREFLIGHT = HERE / "F3-PREFLIGHT-MANIFEST.json"
JOB_RECEIPT_SCHEMA = f"{common.SCHEMA}-learner-job-receipt"
CHECKPOINT_RECEIPT_SCHEMA = f"{common.SCHEMA}-checkpoint-receipt"
TERMINAL_RECEIPT_SCHEMA = f"{common.SCHEMA}-learner-terminal-receipt"
COMPOSITION_INPUT_SCHEMA = f"{common.SCHEMA}-composition-input"


@dataclass(frozen=True, order=True)
class JobKey:
    held_out_world: int
    seed: int

    @classmethod
    def parse(cls, value: str) -> "JobKey":
        try:
            world_text, seed_text = value.split(":", 1)
            key = cls(int(world_text), int(seed_text))
        except (AttributeError, TypeError, ValueError) as error:
            raise common.F3Error("job must be HELD_OUT_WORLD:LEARNER_SEED") from error
        key.verify()
        return key

    def verify(self) -> None:
        if self.held_out_world not in common.WORLDS or self.seed not in common.learner_seeds():
            raise common.F3Error("job is outside the exact four-world/three-seed schedule")

    @property
    def slug(self) -> str:
        self.verify()
        return f"world-{self.held_out_world}-seed-{self.seed}"


ALL_JOBS = tuple(
    JobKey(world, seed) for world in common.WORLDS for seed in common.learner_seeds()
)


@dataclass(frozen=True)
class HeldOutShard:
    world: int
    seed: int
    arm: str
    predictions: np.ndarray
    targets: np.ndarray
    spearman: float | None


@dataclass(frozen=True)
class LoadedSource:
    root: Path
    manifest_sha256: str
    survivor: str
    records: tuple[source_builder.F3SourceRecord, ...]
    neutral_targets_by_fold: Mapping[int, tuple[np.ndarray, ...]]


def _readonly_array(value: object, *, dtype: np.dtype[Any]) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _npz(path: Path, *, expected_sha256: str) -> dict[str, np.ndarray]:
    if common.file_sha256(path) != common.digest(expected_sha256, field="NPZ sha256"):
        raise common.F3Error(f"numeric sidecar digest disagrees: {path}")
    if path.stat().st_mode & 0o222:
        raise common.F3Error(f"numeric sidecar remains writable: {path}")
    try:
        with np.load(path, allow_pickle=False) as archive:
            return {name: np.array(archive[name], copy=True) for name in archive.files}
    except (OSError, ValueError) as error:
        raise common.F3Error(f"cannot load numeric sidecar: {path}") from error


def authenticate_source_artifact(
    root: Path,
    *,
    expected_survivor: str,
    expected_preflight_sha256: str,
    expected_f2_receipt_sha256: str,
) -> LoadedSource:
    source = Path(root)
    if source.is_symlink() or not source.is_dir():
        raise common.F3Error("source artifact root is missing or symlinked")
    manifest_path = source / "manifest.json"
    receipt_path = source / "receipt.json"
    complete_path = source / "COMPLETE"
    manifest = common.load_json(manifest_path, field="F3 source manifest")
    receipt = common.load_json(receipt_path, field="F3 source receipt")
    complete = common.load_json(complete_path, field="F3 source COMPLETE")
    manifest_sha = common.file_sha256(manifest_path)
    receipt_sha = common.file_sha256(receipt_path)
    if any(path.stat().st_mode & 0o222 for path in (manifest_path, receipt_path, complete_path)):
        raise common.F3Error("source seal files remain writable")
    if (
        complete
        != {
            "schema": f"{source_builder.SOURCE_SCHEMA}-complete",
            "manifest_sha256": manifest_sha,
            "receipt_sha256": receipt_sha,
        }
        or receipt.get("schema") != source_builder.SOURCE_RECEIPT_SCHEMA
        or receipt.get("status") != "COMPLETE"
        or receipt.get("claim_ceiling") != common.SOURCE_CLAIM_CEILING
        or receipt.get("observability_statement") != common.OBSERVABILITY_STATEMENT
        or receipt.get("manifest") != {"path": "manifest.json", "sha256": manifest_sha}
        or manifest.get("schema") != source_builder.SOURCE_MANIFEST_SCHEMA
        or manifest.get("status") != "SEALED_WRITE_ONCE"
        or manifest.get("claim_ceiling") != common.SOURCE_CLAIM_CEILING
        or manifest.get("survivor") != expected_survivor
        or manifest.get("preflight_manifest_sha256") != expected_preflight_sha256
        or not isinstance(manifest.get("f2_terminal_receipt"), Mapping)
        or manifest["f2_terminal_receipt"].get("sha256") != expected_f2_receipt_sha256
        or any(
            manifest.get(field) is not False
            for field in ("test_split_opened", "episode_training", "efficacy_claim")
        )
    ):
        raise common.F3Error("source artifact seal/bindings disagree")
    entries = manifest.get("records")
    if not isinstance(entries, list) or len(entries) != 108:
        raise common.F3Error("source artifact does not contain exactly 108 records")
    records = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise common.F3Error("source record manifest entry is malformed")
        metadata_path = source / str(entry["path"])
        arrays_path = source / str(entry["npz_path"])
        if common.file_sha256(metadata_path) != entry.get("sha256"):
            raise common.F3Error("source record metadata digest disagrees")
        metadata = common.load_json(metadata_path, field="source record metadata")
        arrays = _npz(arrays_path, expected_sha256=str(entry["npz_sha256"]))
        required = {
            "action_context",
            "tokens",
            "token_mask",
            "action_mask",
            "reference_actions",
            "q12",
            "targets_bits",
            "targets_normalized",
        }
        if set(arrays) != required:
            raise common.F3Error("source record numeric arrays have non-exact keys")
        view = C3View(
            action_context=arrays["action_context"],
            tokens=arrays["tokens"],
            token_mask=arrays["token_mask"],
            action_mask=arrays["action_mask"],
            reference_actions=arrays["reference_actions"],
            content_digest=str(metadata["view_content_digest"]),
        )
        shape = view.action_mask.shape
        record = source_builder.F3SourceRecord(
            world=int(metadata["world"]),
            lineage=int(metadata["lineage"]),
            step=int(metadata["step"]),
            anchor_id=str(metadata["anchor_id"]),
            view=view,
            q12=arrays["q12"],
            targets_bits=arrays["targets_bits"],
            targets_normalized=arrays["targets_normalized"],
            tape_sha256=str(metadata["f2_tape_sha256"]),
            state_sha256=str(metadata["state_sha256"]),
            action_physical_keys=tuple(tuple(None for _ in range(shape[1])) for _ in range(shape[0])),
        )
        if record.content_digest != entry.get("content_digest"):
            raise common.F3Error("source record content digest disagrees")
        records.append(record)
    expected_order = [
        (world, lineage, step)
        for world in common.WORLDS
        for lineage in common.LINEAGES
        for step in common.ANCHORS
    ]
    if [(r.world, r.lineage, r.step) for r in records] != expected_order:
        raise common.F3Error("source record ordering/coverage drifted")
    neutral_entries = manifest.get("neutral_folds")
    if not isinstance(neutral_entries, list) or [e.get("held_out_world") for e in neutral_entries] != list(common.WORLDS):
        raise common.F3Error("source neutral fold schedule drifted")
    neutral: dict[int, tuple[np.ndarray, ...]] = {}
    for entry in neutral_entries:
        world = int(entry["held_out_world"])
        fold_meta_path = source / str(entry["path"])
        if common.file_sha256(fold_meta_path) != entry.get("sha256"):
            raise common.F3Error("neutral fold metadata digest disagrees")
        fold_meta = common.load_json(fold_meta_path, field="neutral fold metadata")
        if (
            fold_meta.get("held_out_world") != world
            or float(fold_meta.get("coverage", -1.0)) < common.PLACEBO_COVERAGE_MIN
            or fold_meta.get("held_out_labels_moved") is not False
        ):
            raise common.F3Error("neutral fold coverage/leakage binding failed")
        arrays = _npz(source / str(entry["npz_path"]), expected_sha256=str(entry["npz_sha256"]))
        training_indices = [index for index, record in enumerate(records) if record.world != world]
        expected_names = [f"record_{index:03d}" for index in training_indices]
        if sorted(arrays) != sorted(expected_names):
            raise common.F3Error("neutral fold target keys disagree with training records")
        neutral[world] = tuple(
            _readonly_array(arrays[name], dtype=np.dtype(np.float32))
            for name in expected_names
        )
    return LoadedSource(
        root=source,
        manifest_sha256=manifest_sha,
        survivor=expected_survivor,
        records=tuple(records),
        neutral_targets_by_fold=neutral,
    )


def lowo_fold(records: Sequence[source_builder.F3SourceRecord], *, held_out_world: int) -> tuple[tuple[source_builder.F3SourceRecord, ...], tuple[source_builder.F3SourceRecord, ...]]:
    if held_out_world not in common.WORLDS:
        raise common.F3Error("held-out world is outside the F3 panel")
    frozen = tuple(records)
    if {(record.world, record.lineage, record.step) for record in frozen} != {
        (world, lineage, step)
        for world in common.WORLDS
        for lineage in common.LINEAGES
        for step in common.ANCHORS
    }:
        raise common.F3Error("LOWO input does not cover the exact F3 panel")
    training = tuple(record for record in frozen if record.world != held_out_world)
    heldout = tuple(record for record in frozen if record.world == held_out_world)
    if (
        {record.world for record in training} != set(common.WORLDS) - {held_out_world}
        or {record.lineage for record in heldout} != set(common.LINEAGES)
        or len(training) != 81
        or len(heldout) != 27
    ):
        raise common.F3Error("LOWO did not hold out all lineages of exactly one world")
    return training, heldout


def _legal_nonreference_cells(record: source_builder.F3SourceRecord) -> np.ndarray:
    mask = np.array(record.view.action_mask, copy=True)
    mask[np.arange(mask.shape[0]), record.view.reference_actions] = False
    cells = np.argwhere(mask).astype(np.int64, copy=False)
    if cells.size == 0:
        raise common.F3Error("training anchor has no legal nonreference cell")
    return cells


def draw_schedule(
    rng: np.random.Generator,
    records: Sequence[source_builder.F3SourceRecord],
    *,
    batch_size: int = common.BATCH_SIZE,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if type(batch_size) is not int or batch_size != common.BATCH_SIZE:
        raise common.F3Error("F3 batch size is frozen at 256")
    source = tuple(records)
    if not source:
        raise common.F3Error("sampler requires training records")
    anchors = rng.integers(0, len(source), size=batch_size, dtype=np.int64)
    users = np.empty(batch_size, dtype=np.int64)
    actions = np.empty(batch_size, dtype=np.int64)
    cell_cache = [_legal_nonreference_cells(record) for record in source]
    for index, anchor in enumerate(anchors.tolist()):
        cells = cell_cache[int(anchor)]
        selected = int(rng.integers(0, len(cells)))
        users[index], actions[index] = cells[selected]
    return anchors, users, actions


def _score_batch(
    network: LCSRSC3QNetwork,
    records: Sequence[source_builder.F3SourceRecord],
    anchors: np.ndarray,
    users: np.ndarray,
    actions: np.ndarray,
) -> torch.Tensor:
    chunks: list[torch.Tensor] = []
    order: list[int] = []
    for anchor in sorted(set(int(value) for value in anchors.tolist())):
        positions = np.flatnonzero(anchors == anchor)
        values = network.score_cells_view(
            records[anchor].view,
            users[positions],
            actions[positions],
        )
        chunks.append(values)
        order.extend(int(value) for value in positions.tolist())
    concatenated = torch.cat(chunks)
    inverse = torch.tensor(np.argsort(np.asarray(order)), dtype=torch.int64)
    return concatenated[inverse]


def train_one_update(
    network: LCSRSC3QNetwork,
    optimizer: torch.optim.Optimizer,
    records: Sequence[source_builder.F3SourceRecord],
    targets: Sequence[np.ndarray],
    schedule: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> float:
    anchors, users, actions = schedule
    target_values = np.asarray(
        [targets[int(a)][int(u), int(x)] for a, u, x in zip(anchors, users, actions, strict=True)],
        dtype=np.float32,
    )
    optimizer.zero_grad(set_to_none=True)
    predictions = _score_batch(network, records, anchors, users, actions)
    target_tensor = torch.tensor(target_values, dtype=torch.float32)
    loss = torch.mean(torch.square(predictions - target_tensor))
    if not bool(torch.isfinite(loss)):
        raise common.F3Error("F3 MSE became non-finite")
    loss.backward()
    if any(parameter.grad is not None and not bool(torch.isfinite(parameter.grad).all()) for parameter in network.parameters()):
        raise common.F3Error("F3 gradient became non-finite")
    optimizer.step()
    if any(not bool(torch.isfinite(parameter).all()) for parameter in network.parameters()):
        raise common.F3Error("F3 parameter became non-finite")
    return float(loss.detach().cpu())


def _torch_bytes(payload: Mapping[str, object]) -> bytes:
    buffer = io.BytesIO()
    torch.save(dict(payload), buffer)
    return buffer.getvalue()


def _rng_sha256(state: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(state, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    ).hexdigest()


def _schedule_digest(previous: str, schedule: tuple[np.ndarray, np.ndarray, np.ndarray]) -> str:
    common.digest(previous, field="consumed schedule digest")
    digest = hashlib.sha256()
    digest.update(previous.encode("ascii"))
    for array in schedule:
        value = np.ascontiguousarray(array, dtype=np.int64)
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _checkpoint_paths(job_dir: Path, cursor: int) -> tuple[Path, Path]:
    return (
        job_dir / f"checkpoint-{cursor:04d}.pt",
        job_dir / f"checkpoint-{cursor:04d}.receipt.json",
    )


def _load_checkpoint(job_dir: Path, cursor: int) -> dict[str, Any]:
    state_path, receipt_path = _checkpoint_paths(job_dir, cursor)
    receipt = common.load_json(receipt_path, field=f"checkpoint {cursor} receipt")
    if (
        receipt.get("schema") != CHECKPOINT_RECEIPT_SCHEMA
        or receipt.get("status") != "COMPLETE"
        or receipt.get("cursor") != cursor
        or receipt.get("claim_ceiling") != common.LEARNER_CLAIM_CEILING
        or receipt.get("observability_statement") != common.OBSERVABILITY_STATEMENT
        or receipt.get("state_sha256") != common.file_sha256(state_path)
        or state_path.stat().st_mode & 0o222
        or receipt_path.stat().st_mode & 0o222
    ):
        raise common.F3Error("checkpoint receipt/state binding disagrees")
    try:
        payload = torch.load(state_path, map_location="cpu", weights_only=False)
    except (OSError, RuntimeError, ValueError) as error:
        raise common.F3Error("checkpoint state cannot be loaded") from error
    if not isinstance(payload, dict) or payload.get("cursor") != cursor:
        raise common.F3Error("checkpoint cursor/state is malformed")
    if (
        payload.get("consumed_schedule_sha256")
        != receipt.get("consumed_schedule_sha256")
        or any(
            len(payload.get("losses", {}).get(arm, ())) != cursor
            for arm in common.ARMS
        )
    ):
        raise common.F3Error("checkpoint schedule/loss cursor disagrees")
    return payload


def resume_cursor(job_dir: Path) -> int | None:
    root = Path(job_dir)
    existing = []
    for cursor in common.CHECKPOINTS:
        state, receipt = _checkpoint_paths(root, cursor)
        if state.exists() or receipt.exists() or state.is_symlink() or receipt.is_symlink():
            if not state.is_file() or not receipt.is_file():
                raise common.F3Error("partial checkpoint exists")
            _load_checkpoint(root, cursor)
            existing.append(cursor)
    if existing and existing != list(common.CHECKPOINTS[: len(existing)]):
        raise common.F3Error("checkpoint sequence has a gap")
    return existing[-1] if existing else None


def _write_checkpoint(
    job_dir: Path,
    *,
    key: JobKey,
    cursor: int,
    networks: Mapping[str, LCSRSC3QNetwork],
    optimizers: Mapping[str, torch.optim.Optimizer],
    rng: np.random.Generator,
    losses: Mapping[str, Sequence[float]],
    source_manifest_sha256: str,
    consumed_schedule_sha256: str,
) -> None:
    state_path, receipt_path = _checkpoint_paths(job_dir, cursor)
    state = {
        "cursor": cursor,
        "job": {"held_out_world": key.held_out_world, "seed": key.seed},
        "networks": {arm: networks[arm].state_dict() for arm in common.ARMS},
        "optimizers": {arm: optimizers[arm].state_dict() for arm in common.ARMS},
        "rng_state": rng.bit_generator.state,
        "losses": {arm: list(losses[arm]) for arm in common.ARMS},
        "source_manifest_sha256": source_manifest_sha256,
        "consumed_schedule_sha256": consumed_schedule_sha256,
    }
    state_sha = common.write_once_bytes(state_path, _torch_bytes(state))
    receipt = {
        "schema": CHECKPOINT_RECEIPT_SCHEMA,
        "status": "COMPLETE",
        "claim_ceiling": common.LEARNER_CLAIM_CEILING,
        "observability_statement": common.OBSERVABILITY_STATEMENT,
        "held_out_world": key.held_out_world,
        "learner_seed": key.seed,
        "learner_seed_domain": common.SEED_DOMAINS[common.learner_seeds().index(key.seed)],
        "cursor": cursor,
        "state_sha256": state_sha,
        "source_manifest_sha256": source_manifest_sha256,
        "model_sha256": {arm: lcsrs_c3_network_sha256(networks[arm]) for arm in common.ARMS},
        "rng_state_sha256": _rng_sha256(rng.bit_generator.state),
        "consumed_schedule_sha256": consumed_schedule_sha256,
        "loss_count": {arm: len(losses[arm]) for arm in common.ARMS},
        "test_split_opened": False,
        "episode_training": False,
        "efficacy_claim": False,
    }
    common.write_once_json(receipt_path, receipt)


def run_paired_fit(
    job_dir: Path,
    *,
    key: JobKey,
    training: Sequence[source_builder.F3SourceRecord],
    neutral_targets: Sequence[np.ndarray],
    source_manifest_sha256: str,
    update_step: Callable[..., float] = train_one_update,
) -> tuple[dict[str, LCSRSC3QNetwork], dict[str, list[float]], int]:
    key.verify()
    root = Path(job_dir)
    root.mkdir(parents=True, exist_ok=True)
    informed_targets = tuple(record.targets_normalized for record in training)
    neutral = tuple(neutral_targets)
    if len(informed_targets) != 81 or len(neutral) != 81:
        raise common.F3Error("paired fit needs 81 informed and neutral training anchors")
    networks: dict[str, LCSRSC3QNetwork] = {}
    optimizers: dict[str, torch.optim.Optimizer] = {}
    for arm in common.ARMS:
        network, optimizer = make_lcsrs_c3_student(student_seed=key.seed)
        networks[arm], optimizers[arm] = network, optimizer
    if lcsrs_c3_network_sha256(networks["INFORMED"]) != lcsrs_c3_network_sha256(networks["NEUTRAL"]):
        raise common.F3Error("paired arms did not start from identical bytes")
    rng = np.random.Generator(np.random.PCG64(key.seed))
    losses: dict[str, list[float]] = {arm: [] for arm in common.ARMS}
    schedule_sha = hashlib.sha256(b"MCRL_V023_C3_F3_ROW_SCHEDULE_V1").hexdigest()
    cursor = resume_cursor(root)
    if cursor is not None:
        state = _load_checkpoint(root, cursor)
        if state.get("source_manifest_sha256") != source_manifest_sha256:
            raise common.F3Error("checkpoint source manifest changed")
        for arm in common.ARMS:
            networks[arm].load_state_dict(state["networks"][arm])
            optimizers[arm].load_state_dict(state["optimizers"][arm])
            losses[arm] = [float(value) for value in state["losses"][arm]]
        rng.bit_generator.state = state["rng_state"]
        schedule_sha = common.digest(
            state.get("consumed_schedule_sha256"), field="checkpoint schedule digest"
        )
    else:
        cursor = 0
        _write_checkpoint(
            root,
            key=key,
            cursor=0,
            networks=networks,
            optimizers=optimizers,
            rng=rng,
            losses=losses,
            source_manifest_sha256=source_manifest_sha256,
            consumed_schedule_sha256=schedule_sha,
        )
    resumed_from = cursor
    for checkpoint in common.CHECKPOINTS:
        if checkpoint <= cursor:
            continue
        while cursor < checkpoint:
            schedule = draw_schedule(rng, training)
            schedule_sha = _schedule_digest(schedule_sha, schedule)
            losses["INFORMED"].append(
                update_step(
                    networks["INFORMED"],
                    optimizers["INFORMED"],
                    training,
                    informed_targets,
                    schedule,
                )
            )
            losses["NEUTRAL"].append(
                update_step(
                    networks["NEUTRAL"],
                    optimizers["NEUTRAL"],
                    training,
                    neutral,
                    schedule,
                )
            )
            cursor += 1
        _write_checkpoint(
            root,
            key=key,
            cursor=cursor,
            networks=networks,
            optimizers=optimizers,
            rng=rng,
            losses=losses,
            source_manifest_sha256=source_manifest_sha256,
            consumed_schedule_sha256=schedule_sha,
        )
    return networks, losses, resumed_from


def evaluate_heldout(
    network: LCSRSC3QNetwork,
    records: Sequence[source_builder.F3SourceRecord],
) -> tuple[np.ndarray, np.ndarray]:
    predictions = []
    targets = []
    network.eval()
    with torch.no_grad():
        for record in records:
            values = network.forward_view(record.view).detach().cpu().numpy()
            cells = _legal_nonreference_cells(record)
            for user, action in cells.tolist():
                predictions.append(float(values[int(user), int(action)]))
                targets.append(float(record.targets_normalized[int(user), int(action)]))
    if not predictions:
        raise common.F3Error("held-out fold has no legal nonreference rows")
    return np.asarray(predictions, dtype=np.float64), np.asarray(targets, dtype=np.float64)


def execute_job(output: Path, *, key: JobKey, source: LoadedSource) -> tuple[Path, bool]:
    job_dir = Path(output) / "jobs" / key.slug
    terminal = job_dir / "receipt.json"
    if terminal.exists() or terminal.is_symlink():
        payload = common.load_json(terminal, field="learner job receipt")
        sidecar = payload.get("numeric_sidecar")
        if (
            payload.get("schema") != JOB_RECEIPT_SCHEMA
            or payload.get("status") != "COMPLETE"
            or payload.get("claim_ceiling") != common.LEARNER_CLAIM_CEILING
            or payload.get("observability_statement") != common.OBSERVABILITY_STATEMENT
            or payload.get("held_out_world") != key.held_out_world
            or payload.get("learner_seed") != key.seed
            or payload.get("source_manifest_sha256") != source.manifest_sha256
            or payload.get("survivor") != source.survivor
            or payload.get("updates_per_arm") != common.UPDATES
            or not isinstance(sidecar, Mapping)
            or set(sidecar) != {"path", "sha256"}
            or common.file_sha256(job_dir / str(sidecar["path"])) != sidecar["sha256"]
            or resume_cursor(job_dir) != common.UPDATES
            or terminal.stat().st_mode & 0o222
        ):
            raise common.F3Error("existing learner job receipt is invalid")
        return terminal, True
    common.validate_process_environment(os.environ)
    startup = job_dir / "startup-receipt.json"
    startup_payload = {
        "schema": f"{common.SCHEMA}-learner-startup-receipt",
        "status": "STARTED_OR_RESUMED",
        "claim_ceiling": common.LEARNER_CLAIM_CEILING,
        "observability_statement": common.OBSERVABILITY_STATEMENT,
        "held_out_world": key.held_out_world,
        "learner_seed": key.seed,
        "learner_seed_domain": common.SEED_DOMAINS[common.learner_seeds().index(key.seed)],
        "source_manifest_sha256": source.manifest_sha256,
        "test_split_opened": False,
        "episode_training": False,
        "efficacy_claim": False,
    }
    if startup.exists() or startup.is_symlink():
        if common.load_json(startup, field="learner startup receipt") != startup_payload:
            raise common.F3Error("learner startup receipt binding drifted")
    else:
        common.write_once_json(startup, startup_payload)
    training, heldout = lowo_fold(source.records, held_out_world=key.held_out_world)
    networks, losses, resumed_from = run_paired_fit(
        job_dir,
        key=key,
        training=training,
        neutral_targets=source.neutral_targets_by_fold[key.held_out_world],
        source_manifest_sha256=source.manifest_sha256,
    )
    arrays = {}
    arm_metrics = {}
    reference_targets = None
    for arm in common.ARMS:
        predictions, targets = evaluate_heldout(networks[arm], heldout)
        if reference_targets is None:
            reference_targets = targets
        elif not np.array_equal(reference_targets, targets):
            raise common.F3Error("paired held-out labels differ by arm")
        arrays[f"{arm.lower()}_predictions"] = predictions
        arrays[f"{arm.lower()}_targets"] = targets
        rho = r7_metrics.tie_aware_spearman(predictions, targets)
        sign = r7_metrics.balanced_sign_metrics(predictions, targets)
        arm_metrics[arm] = {"spearman": rho, "sign": sign}
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    numeric_sha = common.write_once_bytes(job_dir / "heldout.npz", buffer.getvalue())
    receipt = {
        "schema": JOB_RECEIPT_SCHEMA,
        "status": "COMPLETE",
        "claim_ceiling": common.LEARNER_CLAIM_CEILING,
        "observability_statement": common.OBSERVABILITY_STATEMENT,
        "held_out_world": key.held_out_world,
        "learner_seed": key.seed,
        "learner_seed_domain": common.SEED_DOMAINS[common.learner_seeds().index(key.seed)],
        "source_manifest_sha256": source.manifest_sha256,
        "survivor": source.survivor,
        "updates_per_arm": common.UPDATES,
        "resumed_from_checkpoint": resumed_from,
        "metrics": arm_metrics,
        "final_model_sha256": {
            arm: lcsrs_c3_network_sha256(networks[arm]) for arm in common.ARMS
        },
        "loss_count": {arm: len(losses[arm]) for arm in common.ARMS},
        "numeric_sidecar": {"path": "heldout.npz", "sha256": numeric_sha},
        "test_split_opened": False,
        "episode_training": False,
        "efficacy_claim": False,
    }
    common.write_once_json(terminal, receipt)
    return terminal, False


def evaluate_observability_panel(shards: Sequence[HeldOutShard]) -> dict[str, object]:
    expected = {
        (world, seed, arm)
        for world in common.WORLDS
        for seed in common.learner_seeds()
        for arm in common.ARMS
    }
    by_key = {(shard.world, shard.seed, shard.arm): shard for shard in shards}
    if len(shards) != len(expected) or set(by_key) != expected:
        raise common.F3Error("learner panel is not the exact 4 x 3 x 2 schedule")
    reference_targets: dict[int, np.ndarray] = {}
    seed_metrics: dict[str, object] = {}
    for seed in common.learner_seeds():
        seed_entry = {}
        for arm in common.ARMS:
            prediction_parts = []
            target_parts = []
            for world in common.WORLDS:
                shard = by_key[(world, seed, arm)]
                prediction = np.asarray(shard.predictions, dtype=np.float64)
                target = np.asarray(shard.targets, dtype=np.float64)
                recomputed = r7_metrics.tie_aware_spearman(prediction, target)
                if not r7_metrics._same_metric(shard.spearman, recomputed):
                    raise common.F3Error("shard Spearman disagrees with raw rows")
                if world not in reference_targets:
                    reference_targets[world] = target
                elif not np.array_equal(reference_targets[world], target):
                    raise common.F3Error("held-out labels differ across seed or arm")
                prediction_parts.append(prediction)
                target_parts.append(target)
            pooled_prediction = np.concatenate(prediction_parts)
            pooled_target = np.concatenate(target_parts)
            seed_entry[arm] = {
                "spearman": r7_metrics.tie_aware_spearman(pooled_prediction, pooled_target),
                "sign": r7_metrics.balanced_sign_metrics(pooled_prediction, pooled_target),
            }
        seed_metrics[str(seed)] = seed_entry
    world_metrics = {}
    wins = 0
    nonnegative = {seed: 0 for seed in common.learner_seeds()}
    for world in common.WORLDS:
        arm_means = {}
        for arm in common.ARMS:
            values = []
            for seed in common.learner_seeds():
                shard = by_key[(world, seed, arm)]
                rho = r7_metrics.tie_aware_spearman(shard.predictions, shard.targets)
                values.append(rho)
                if arm == "INFORMED" and rho is not None and rho >= 0.0:
                    nonnegative[seed] += 1
            arm_means[arm] = r7_metrics._mean(values)
        win = bool(
            arm_means["INFORMED"] is not None
            and arm_means["NEUTRAL"] is not None
            and r7_metrics._strictly_above(arm_means["INFORMED"], arm_means["NEUTRAL"])
        )
        wins += int(win)
        world_metrics[str(world)] = {"mean_spearman": arm_means, "informed_win": win}
    informed_bacc = [seed_metrics[str(seed)]["INFORMED"]["sign"]["balanced_accuracy"] for seed in common.learner_seeds()]
    neutral_bacc = [seed_metrics[str(seed)]["NEUTRAL"]["sign"]["balanced_accuracy"] for seed in common.learner_seeds()]
    informed_rho = [seed_metrics[str(seed)]["INFORMED"]["spearman"] for seed in common.learner_seeds()]
    informed_raw = [seed_metrics[str(seed)]["INFORMED"]["sign"]["raw_sign_accuracy"] for seed in common.learner_seeds()]
    neutral_raw = [seed_metrics[str(seed)]["NEUTRAL"]["sign"]["raw_sign_accuracy"] for seed in common.learner_seeds()]
    mean_bacc = r7_metrics._mean(informed_bacc)
    mean_neutral_bacc = r7_metrics._mean(neutral_bacc)
    mean_rho = r7_metrics._mean(informed_rho)
    class_support = r7_metrics.balanced_sign_metrics(
        np.zeros(sum(value.size for value in reference_targets.values())),
        np.concatenate([reference_targets[world] for world in common.WORLDS]),
    )
    denominators_valid = all(
        seed_metrics[str(seed)][arm]["sign"]["balanced_accuracy"] is not None
        for seed in common.learner_seeds()
        for arm in common.ARMS
    )
    world_stability = bool(
        wins >= common.INFORMED_WORLD_WINS_MIN
        and all(
            nonnegative[seed] >= common.PER_SEED_NONNEGATIVE_WORLDS_MIN
            for seed in common.learner_seeds()
        )
    )
    passes = observability_threshold_truth(
        denominators_valid=denominators_valid,
        positive_rows=int(class_support["positive_denominator"]),
        negative_rows=int(class_support["negative_denominator"]),
        mean_informed_spearman=mean_rho,
        mean_informed_balanced_accuracy=mean_bacc,
        mean_neutral_balanced_accuracy=mean_neutral_bacc,
        informed_world_wins=wins,
        per_seed_nonnegative_worlds=nonnegative,
    )
    return {
        "schema": f"{common.SCHEMA}-observability-metrics",
        "thresholds": common.threshold_bindings(),
        "seed_metrics": seed_metrics,
        "world_metrics": world_metrics,
        "aggregate": {
            "mean_informed_spearman": mean_rho,
            "mean_informed_balanced_accuracy": mean_bacc,
            "mean_neutral_balanced_accuracy": mean_neutral_bacc,
            "informed_minus_neutral_balanced_accuracy": (
                None if mean_bacc is None or mean_neutral_bacc is None else mean_bacc - mean_neutral_bacc
            ),
            "mean_informed_raw_sign_accuracy": r7_metrics._mean(informed_raw),
            "mean_neutral_raw_sign_accuracy": r7_metrics._mean(neutral_raw),
        },
        "pooled_eligible_denominators": {
            "positive": class_support["positive_denominator"],
            "negative": class_support["negative_denominator"],
        },
        "informed_world_wins": wins,
        "informed_seed_nonnegative_worlds": {
            str(seed): nonnegative[seed] for seed in common.learner_seeds()
        },
        "world_stability": world_stability,
        "passes": passes,
        "raw_sign_accuracy_role": "SERIALIZED_NONDECISIVE",
    }


def observability_threshold_truth(
    *,
    denominators_valid: bool,
    positive_rows: int,
    negative_rows: int,
    mean_informed_spearman: float | None,
    mean_informed_balanced_accuracy: float | None,
    mean_neutral_balanced_accuracy: float | None,
    informed_world_wins: int,
    per_seed_nonnegative_worlds: Mapping[int, int],
) -> bool:
    """Pure copied-threshold truth table used by the raw-panel evaluator."""

    values = (
        mean_informed_spearman,
        mean_informed_balanced_accuracy,
        mean_neutral_balanced_accuracy,
    )
    if any(value is None or not math.isfinite(float(value)) for value in values):
        return False
    if set(per_seed_nonnegative_worlds) != set(common.learner_seeds()):
        return False
    return bool(
        denominators_valid
        and positive_rows >= common.MIN_CLASS_ROWS
        and negative_rows >= common.MIN_CLASS_ROWS
        and float(mean_informed_spearman) >= common.MEAN_INFORMED_SPEARMAN_MIN
        and float(mean_informed_balanced_accuracy) >= common.MEAN_INFORMED_BACC_MIN
        and (
            float(mean_informed_balanced_accuracy)
            - float(mean_neutral_balanced_accuracy)
            >= common.BACC_GAP_MIN
            or math.isclose(
                float(mean_informed_balanced_accuracy)
                - float(mean_neutral_balanced_accuracy),
                common.BACC_GAP_MIN,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
        )
        and informed_world_wins >= common.INFORMED_WORLD_WINS_MIN
        and all(
            per_seed_nonnegative_worlds[seed]
            >= common.PER_SEED_NONNEGATIVE_WORLDS_MIN
            for seed in common.learner_seeds()
        )
    )


def native_composition_actions(q12: object, q3: object, mask: object) -> np.ndarray:
    """Use R7's native masked one-pass selector for Q1+Q2+Q3."""

    import v023_lcsrs_composition_adapter as composition_adapter

    q12_array = np.asarray(q12, dtype=np.float64)
    q3_array = np.asarray(q3, dtype=np.float64)
    if q12_array.shape != q3_array.shape:
        raise common.F3Error("composition Q12/Q3 shapes disagree")
    return composition_adapter.native_masked_argmax(q12_array + q3_array, mask).actions


def _profile(value: object, *, field: str) -> dict[str, float]:
    if not isinstance(value, Mapping) or set(value) != {"bits", "energy_j", "service_fraction"}:
        raise common.F3Error(f"{field} profile keys are not exact")
    result = {name: float(value[name]) for name in value}
    if (
        not all(math.isfinite(number) for number in result.values())
        or result["bits"] < 0.0
        or result["energy_j"] <= 0.0
        or not 0.0 <= result["service_fraction"] <= 1.0
    ):
        raise common.F3Error(f"{field} profile values are invalid")
    return result


def evaluate_composition_check(payload: Mapping[str, object]) -> dict[str, object]:
    """Apply the memo's four-world R7 composition thresholds without rescoring."""

    if payload.get("schema") != COMPOSITION_INPUT_SCHEMA or payload.get("integrity") is not True:
        return {"integrity": False, "passes": False}
    counts = payload.get("counts")
    worlds = payload.get("worlds")
    if not isinstance(counts, Mapping) or not isinstance(worlds, Mapping) or set(worlds) != {str(w) for w in common.WORLDS}:
        raise common.F3Error("composition input panel/counts are malformed")
    required_counts = {
        "pairs",
        "action_opportunities",
        "action_changes",
        "literal_11",
        "partial",
        "harmful_partial",
        "selected_11",
        "topology_consistent_11",
    }
    if set(counts) != required_counts or any(type(counts[name]) is not int or counts[name] < 0 for name in counts):
        raise common.F3Error("composition count keys/values are not exact")
    pairs = int(counts["pairs"])
    action_opportunities = int(counts["action_opportunities"])
    partial = int(counts["partial"])
    selected_11 = int(counts["selected_11"])
    action_fraction = None if action_opportunities == 0 else int(counts["action_changes"]) / action_opportunities
    literal_fraction = None if pairs == 0 else int(counts["literal_11"]) / pairs
    harmful_fraction = 0.0 if partial == 0 else int(counts["harmful_partial"]) / partial
    topology_fraction = None if selected_11 == 0 else int(counts["topology_consistent_11"]) / selected_11
    pooled = {arm: {"bits": 0.0, "energy_j": 0.0} for arm in ("BASE", "ORACLE", "INFORMED", "NEUTRAL")}
    teacher_positive = 0
    learned_positive = 0
    literal_worlds = 0
    service_ok = True
    pairs_per_world = True
    world_receipts = {}
    for world in common.WORLDS:
        row = worlds[str(world)]
        if not isinstance(row, Mapping) or set(row) != {"pairs", "literal_11", "profiles"}:
            raise common.F3Error("composition world keys are not exact")
        if type(row["pairs"]) is not int or type(row["literal_11"]) is not int:
            raise common.F3Error("composition world counts must be exact integers")
        pairs_per_world &= row["pairs"] >= 1
        literal_worlds += int(row["literal_11"] >= 1)
        profiles_raw = row["profiles"]
        if not isinstance(profiles_raw, Mapping) or set(profiles_raw) != set(pooled):
            raise common.F3Error("composition profiles omit a required arm")
        profiles = {arm: _profile(profiles_raw[arm], field=f"{world}.{arm}") for arm in pooled}
        for arm in pooled:
            pooled[arm]["bits"] += profiles[arm]["bits"]
            pooled[arm]["energy_j"] += profiles[arm]["energy_j"]
        base_ee = profiles["BASE"]["bits"] / profiles["BASE"]["energy_j"]
        teacher = profiles["ORACLE"]["bits"] / profiles["ORACLE"]["energy_j"] > base_ee
        learned = profiles["INFORMED"]["bits"] / profiles["INFORMED"]["energy_j"] > base_ee
        teacher_positive += int(teacher)
        learned_positive += int(learned)
        world_service = all(
            profiles[arm]["service_fraction"] >= profiles["BASE"]["service_fraction"] - 0.01
            for arm in ("ORACLE", "INFORMED", "NEUTRAL")
        )
        service_ok &= world_service
        world_receipts[str(world)] = {
            "teacher_above_base": teacher,
            "learned_above_base": learned,
            "service": world_service,
        }
    teacher_pooled = pooled["ORACLE"]["bits"] / pooled["ORACLE"]["energy_j"] > pooled["BASE"]["bits"] / pooled["BASE"]["energy_j"]
    learned_pooled = pooled["INFORMED"]["bits"] / pooled["INFORMED"]["energy_j"] > pooled["BASE"]["bits"] / pooled["BASE"]["energy_j"]
    predicates = {
        "pair_coverage": pairs >= 24 and pairs_per_world,
        "action_exposure": action_fraction is not None and action_fraction >= 0.10,
        "literal_11": literal_fraction is not None and literal_fraction >= 0.25 and literal_worlds >= 2,
        "harmful_partial": harmful_fraction <= 0.05,
        "topology_consistency": topology_fraction is not None and topology_fraction >= 0.80,
        "teacher_composition": teacher_pooled and teacher_positive >= 2,
        "learned_composition": learned_pooled and learned_positive >= 2,
        "service": service_ok,
    }
    return {
        "integrity": True,
        "thresholds": common.threshold_bindings()["composition"],
        "fractions": {
            "action_change": action_fraction,
            "literal_11": literal_fraction,
            "harmful_partial": harmful_fraction,
            "topology_consistency": topology_fraction,
        },
        "positive_worlds": {
            "literal_11": literal_worlds,
            "teacher": teacher_positive,
            "learned": learned_positive,
        },
        "pooled": pooled,
        "worlds": world_receipts,
        "predicates": predicates,
        "passes": all(predicates.values()),
    }


def adjudicate(*, integrity: bool, observability: bool, composition: bool) -> str:
    if not integrity:
        return "INVALID_RUN"
    if not observability:
        return "F3_STOP_OBSERVABILITY"
    if not composition:
        return "F3_STOP_COMPOSITION"
    return "F3_PASS"


def _load_job_shards(output: Path, *, source_manifest_sha256: str) -> tuple[list[HeldOutShard], list[dict[str, object]]]:
    shards = []
    receipts = []
    for key in ALL_JOBS:
        job_dir = Path(output) / "jobs" / key.slug
        receipt_path = job_dir / "receipt.json"
        receipt = common.load_json(receipt_path, field=f"job {key.slug} receipt")
        if (
            receipt.get("schema") != JOB_RECEIPT_SCHEMA
            or receipt.get("status") != "COMPLETE"
            or receipt.get("held_out_world") != key.held_out_world
            or receipt.get("learner_seed") != key.seed
            or receipt.get("source_manifest_sha256") != source_manifest_sha256
            or receipt.get("updates_per_arm") != common.UPDATES
            or receipt.get("observability_statement") != common.OBSERVABILITY_STATEMENT
            or receipt_path.stat().st_mode & 0o222
        ):
            raise common.F3Error("job receipt binding drifted")
        sidecar = receipt.get("numeric_sidecar")
        if not isinstance(sidecar, Mapping) or set(sidecar) != {"path", "sha256"}:
            raise common.F3Error("job numeric sidecar binding is malformed")
        arrays = _npz(job_dir / str(sidecar["path"]), expected_sha256=str(sidecar["sha256"]))
        for arm in common.ARMS:
            predictions = arrays[f"{arm.lower()}_predictions"]
            targets = arrays[f"{arm.lower()}_targets"]
            shards.append(
                HeldOutShard(
                    world=key.held_out_world,
                    seed=key.seed,
                    arm=arm,
                    predictions=predictions,
                    targets=targets,
                    spearman=receipt["metrics"][arm]["spearman"],
                )
            )
        receipts.append(
            {"path": f"jobs/{key.slug}/receipt.json", "sha256": common.file_sha256(receipt_path)}
        )
    return shards, receipts


def execute_merge(
    output: Path,
    *,
    source: LoadedSource,
    composition_input: Path,
    preflight_sha256: str,
    f2_receipt_sha256: str,
) -> tuple[Path, bool]:
    root = Path(output)
    terminal = root / "terminal-receipt.json"
    if terminal.exists() or terminal.is_symlink():
        receipt = common.load_json(terminal, field="F3 terminal receipt")
        if (
            receipt.get("schema") != TERMINAL_RECEIPT_SCHEMA
            or receipt.get("outcome") not in {"F3_PASS", "F3_STOP_OBSERVABILITY", "F3_STOP_COMPOSITION", "INVALID_RUN"}
            or receipt.get("observability_statement") != common.OBSERVABILITY_STATEMENT
            or terminal.stat().st_mode & 0o222
        ):
            raise common.F3Error("existing F3 terminal receipt is invalid")
        return terminal, True
    try:
        shards, job_receipts = _load_job_shards(root, source_manifest_sha256=source.manifest_sha256)
        observability = evaluate_observability_panel(shards)
        composition_payload = common.load_json(composition_input, field="F3 composition input")
        if Path(composition_input).stat().st_mode & 0o222:
            raise common.F3Error("composition input must be sealed read-only")
        composition = evaluate_composition_check(composition_payload)
        outcome = adjudicate(
            integrity=True,
            observability=bool(observability["passes"]),
            composition=bool(composition["passes"]),
        )
        payload = {
            "schema": TERMINAL_RECEIPT_SCHEMA,
            "status": "COMPLETE",
            "outcome": outcome,
            "claim_ceiling": common.LEARNER_CLAIM_CEILING,
            "observability_statement": common.OBSERVABILITY_STATEMENT,
            "survivor": source.survivor,
            "preflight_manifest_sha256": preflight_sha256,
            "f2_terminal_receipt_sha256": f2_receipt_sha256,
            "source_manifest_sha256": source.manifest_sha256,
            "learner_seeds": list(common.learner_seeds()),
            "job_receipts": job_receipts,
            "observability": observability,
            "composition": composition,
            "composition_input": {
                "path": str(Path(composition_input).resolve()),
                "sha256": common.file_sha256(composition_input),
            },
            "test_split_opened": False,
            "episode_training": False,
            "efficacy_claim": False,
        }
    except Exception as error:
        payload = {
            "schema": TERMINAL_RECEIPT_SCHEMA,
            "status": "INVALID_RUN",
            "outcome": "INVALID_RUN",
            "claim_ceiling": common.LEARNER_CLAIM_CEILING,
            "observability_statement": common.OBSERVABILITY_STATEMENT,
            "survivor": source.survivor,
            "preflight_manifest_sha256": preflight_sha256,
            "f2_terminal_receipt_sha256": f2_receipt_sha256,
            "source_manifest_sha256": source.manifest_sha256,
            "error_type": type(error).__name__,
            "error_sha256": hashlib.sha256(str(error).encode("utf-8")).hexdigest(),
            "test_split_opened": False,
            "episode_training": False,
            "efficacy_claim": False,
        }
    common.write_once_json(terminal, payload)
    return terminal, False


def run(args: argparse.Namespace) -> dict[str, object]:
    _preflight, preflight_sha = common.validate_preflight_manifest(args.preflight_manifest)
    if args.dry_run and args.launch_authority is None:
        return {"preflight": args.preflight_manifest}
    if args.launch_authority is None:
        raise common.F3Error("learner screen requires --launch-authority")
    authority, _f2_receipt = common.validate_launch_authority(
        args.launch_authority,
        preflight_path=args.preflight_manifest,
        preflight_sha256=preflight_sha,
    )
    if args.dry_run:
        return {"preflight": args.preflight_manifest, "authority": args.launch_authority}
    if args.source_artifact is None or args.output is None:
        raise common.F3Error("learner execution requires --source-artifact and --output")
    f2_sha = str(authority["f2_terminal_receipt"]["sha256"])
    source = authenticate_source_artifact(
        args.source_artifact,
        expected_survivor=str(authority["survivor"]),
        expected_preflight_sha256=preflight_sha,
        expected_f2_receipt_sha256=f2_sha,
    )
    if args.job is not None:
        receipt, skipped = execute_job(args.output, key=JobKey.parse(args.job), source=source)
        return {"mode": "job", "receipt": receipt, "skipped": skipped}
    if not args.merge or args.composition_input is None:
        raise common.F3Error("terminal merge requires --merge and --composition-input")
    receipt, skipped = execute_merge(
        args.output,
        source=source,
        composition_input=args.composition_input,
        preflight_sha256=preflight_sha,
        f2_receipt_sha256=f2_sha,
    )
    return {"mode": "merge", "receipt": receipt, "skipped": skipped}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--job")
    mode.add_argument("--merge", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preflight-manifest", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--source-artifact", type=Path)
    parser.add_argument("--composition-input", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run(args)
    except common.F3NotAdmitted as error:
        print(str(error), file=sys.stderr)
        return 3
    except Exception as error:
        print(f"F3_LEARNER_ERROR: {error}", file=sys.stderr)
        traceback.print_exception(error, file=sys.stderr)
        return 2
    if args.dry_run:
        print(
            "F3_LEARNER_DRY_RUN_PASS "
            f"preflight={result['preflight']} seeds={','.join(str(v) for v in common.learner_seeds())}"
        )
    else:
        state = "SKIPPED_COMPLETE" if result["skipped"] else "WRITTEN"
        print(f"F3_{str(result['mode']).upper()}_{state} receipt={result['receipt']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
