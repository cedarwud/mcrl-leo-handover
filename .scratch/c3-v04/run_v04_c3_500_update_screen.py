#!/usr/bin/env python3
"""Run the one bounded post-GO V0.4 C3 update/evaluation screen.

The V0.4 learnability gate is deliberately a separate protocol.  It trains
only local Q3 and does not open an episode or an EE endpoint.  This consumer
starts *only* from a sealed ``GO_500EP_SCREEN_ONLY`` result.  Its primary
comparison is the sealed selected-rung hybrid itself (zero additional source
updates), evaluated as ``Q1+Q2+Q3`` versus ``Q1+Q2``.  It then applies exactly
500 additional full-batch C3 source-training updates and evaluates only the
100-update checkpoints as an exploratory trend.  Those updates are not
simulator episodes.  There is no TEST path and no post-action coordinator in
this file.

Importing this module is side-effect free.  In particular, it never starts a
gate, a source materializer, or a training process; the command-line entry
point is the only execution path.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (HERE, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v04_c3_learnability_gate as gate  # noqa: E402
from mcrl.algorithms.ee_axis_v04_hybrid import (  # noqa: E402
    HYBRID_ALGORITHM,
    HYBRID_CHECKPOINT_VERSION,
    EEAxisV04HybridTrainer,
    FrozenMeanMaxCheckpointSpec,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch  # noqa: E402
from mcrl.env.ephemeris import (  # noqa: E402
    TRAIN,
    BlockAlternatingSplit,
    EpisodeStartSampler,
)
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.env.mobility import MobilityConfig  # noqa: E402
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver  # noqa: E402
from mcrl.env.step import StepEnvironment  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_v04_c3_dataset import (  # noqa: E402
    V04C3OpeningDataset,
    read_v04_c3_dataset,
)
from mcrl.runtime.ee_axis_v04_c3_state import (  # noqa: E402
    encode_ee_axis_v04_c3_state,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _evaluation_rngs,
    assert_ephemeris_matches_record,
)
from mcrl.runtime.trainer_env import TrainerEnvironment  # noqa: E402


# Frozen consumer protocol -------------------------------------------------

SCREEN_SCHEMA = "multi-catfish-mcrl-v04-c3-500-update-screen-v1"
SCREEN_CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v04-c3-500-update-checkpoint-v1"
SCREEN_RESULT_SCHEMA = "multi-catfish-mcrl-v04-c3-500-update-screen-result-v1"
PRIMARY_RECEIPT_SCHEMA = "multi-catfish-mcrl-v04-c3-primary-evaluation-receipt-v1"

SUCCESS_STATUS = gate.SUCCESS_STATUS
REQUIRED_GATE_STATUS = "GO_500EP_SCREEN_ONLY"
AUTHORITY_SCHEMA = gate.AUTHORITY_SCHEMA
AUTHORITY_SEAL_SCHEMA = gate.AUTHORITY_SEAL_SCHEMA
RESULT_SCHEMA = gate.RESULT_SCHEMA
RESULT_SEAL_SCHEMA = gate.RESULT_SEAL_SCHEMA
SUCCESS_CLAIM_CEILING = gate.SUCCESS_CLAIM_CEILING
TRAIN_SOURCE_SEEDS = gate.TRAIN_SOURCE_SEEDS
VALIDATION_SOURCE_SEEDS = gate.VALIDATION_SOURCE_SEEDS
INITIALIZATION_SEEDS = gate.INITIALIZATION_SEEDS
EVALUATION_SPLIT = "TRAIN"
TEST_SPLIT_OPENED = False
SCREEN_UPDATE_COUNT = 500
SCREEN_CHECKPOINT_EVERY = 100
SCREEN_CHECKPOINT_UPDATES = (100, 200, 300, 400, 500)
PRIMARY_SCREEN_UPDATES = (0,)
EVALUATION_SCREEN_UPDATES = (0, *SCREEN_CHECKPOINT_UPDATES)
SCREEN_UPDATE_UNIT = "additional_full_batch_C3_source_training_update"
PRIMARY_EVALUATION_ROLE = "PRIMARY_SELECTED_GATE_RUNG"
EXPLORATORY_EVALUATION_ROLE = "EXPLORATORY_TREND_CHECKPOINT"
EVALUATION_SEEDS = tuple(range(2026092401, 2026092411))
USERS = 100
STEPS_PER_EPISODE = 10
SERVICE_GUARD_MARGIN = 0
FADING_SCHEMA = "multi-catfish-mcrl-v04-c3-matched-evaluation-v1"

DEFAULT_GATE_DIR = REPO / "artifacts" / "multi-catfish-v04-c3-learnability-20260901-r2"
DEFAULT_SOURCE_DIR = REPO / "artifacts" / "multi-catfish-v04-c3-source-20260901-r2"
DEFAULT_V03_ROOT = (
    REPO / "artifacts" / "multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"
)
DEFAULT_PREREG = gate.DEFAULT_PREREG
DEFAULT_TLE_ROOT = Path("~/demo/tle_data/starlink/tle").expanduser()
DEFAULT_OUTPUT_DIR = REPO / "artifacts" / "multi-catfish-v04-c3-500-update-screen-20260901"


class V04C3ScreenError(RuntimeError):
    """A source, gate, checkpoint, physics, or pairing contract failed closed."""


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
        raise V04C3ScreenError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    """Hash the canonical JSON body, matching the V0.4 authority convention."""

    return hashlib.sha256(_canonical_bytes(payload)[:-1]).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V04C3ScreenError(f"{field} must be lowercase SHA-256")
    return value


def _file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V04C3ScreenError(f"expected a regular non-symlink file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_canonical_json(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V04C3ScreenError(f"sealed JSON artifact is missing: {source}")
    raw = source.read_bytes()
    try:
        payload = json.loads(
            raw.decode("ascii"), parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant {value}")
            )
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise V04C3ScreenError(f"sealed JSON artifact is invalid: {source}") from error
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        raise V04C3ScreenError(f"sealed JSON artifact is not canonical: {source}")
    return payload


def _regular_artifact(path_value: object, *, field: str) -> Path:
    if isinstance(path_value, Path):
        path = path_value
    elif isinstance(path_value, str) and path_value.strip():
        path = Path(path_value)
    else:
        raise V04C3ScreenError(f"{field} must be a nonempty artifact path")
    if not path.is_absolute():
        path = REPO / path
    if path.is_symlink() or not path.is_file():
        raise V04C3ScreenError(f"{field} artifact is missing or non-regular: {path}")
    return path


def _require_false(payload: Mapping[str, Any], field: str, *, label: str) -> None:
    if payload.get(field) is not False:
        raise V04C3ScreenError(f"{label}.{field} must be exactly false; TEST is forbidden")


def _require_digest_match(
    left: Mapping[str, Any], left_field: str, right: Mapping[str, Any], right_field: str
) -> str:
    observed = _digest(left.get(left_field), field=left_field)
    expected = _digest(right.get(right_field), field=right_field)
    if observed != expected:
        raise V04C3ScreenError(
            f"authenticated digest mismatch: {left_field} != {right_field}"
        )
    return observed


def authenticate_gate(
    gate_dir: Path,
    *,
    source_dir: Path | None = None,
    prereg_path: Path | None = DEFAULT_PREREG,
) -> dict[str, Any]:
    """Authenticate a completed GO gate and selected Q3 artifact receipts.

    The source directory is optional for the pure receipt unit seam.  The
    production :func:`run_screen` path always supplies it, which additionally
    re-runs the gate's receipt-only source authentication before opening TRAIN
    dataset bytes.
    """

    root = Path(gate_dir)
    if root.is_symlink() or not root.is_dir():
        raise V04C3ScreenError(
            f"gate result result.json is missing because gate directory is missing or non-regular: {root}"
        )
    result_path = root / "result.json"
    if result_path.is_symlink() or not result_path.is_file():
        raise V04C3ScreenError(f"gate result result.json is missing: {result_path}")
    required = (
        "authority.json",
        "authority-seal.json",
        "result-seal.json",
    )
    for name in required:
        if (root / name).is_symlink() or not (root / name).is_file():
            raise V04C3ScreenError(f"gate artifact is missing: {root / name}")

    authority = _read_canonical_json(root / "authority.json")
    authority_seal = _read_canonical_json(root / "authority-seal.json")
    result = _read_canonical_json(result_path)
    result_seal = _read_canonical_json(root / "result-seal.json")

    authority_sha = _digest(authority.get("authority_sha256"), field="authority_sha256")
    authority_body = dict(authority)
    authority_body.pop("authority_sha256", None)
    if canonical_sha256(authority_body) != authority_sha:
        raise V04C3ScreenError("gate authority_sha256 does not authenticate authority.json")
    authority_file_sha = _file_sha256(root / "authority.json")
    authority_seal_file_sha = _file_sha256(root / "authority-seal.json")
    if (
        authority_seal.get("schema") != gate.AUTHORITY_SEAL_SCHEMA
        or authority_seal.get("authority_file_sha256") != authority_file_sha
        or authority_seal.get("authority_sha256") != authority_sha
    ):
        raise V04C3ScreenError("gate authority seal is invalid")
    _require_false(authority_seal, "test_split_opened", label="authority-seal")
    _require_false(authority_seal, "validation_dataset_bytes_opened", label="authority-seal")
    _require_false(authority_seal, "validation_metrics_computed", label="authority-seal")

    result_sha = _file_sha256(result_path)
    if (
        result_seal.get("schema") != gate.RESULT_SEAL_SCHEMA
        or result_seal.get("result_file_sha256") != result_sha
        or result_seal.get("authority_sha256") != authority_sha
        or result_seal.get("authority_file_sha256") != authority_file_sha
    ):
        raise V04C3ScreenError("gate result seal is invalid")
    _require_false(result_seal, "test_split_opened", label="result-seal")
    _require_false(result_seal, "held_out_ee_evaluated", label="result-seal")

    if (
        authority.get("schema") != gate.AUTHORITY_SCHEMA
        or authority.get("status") != "SEALED_BEFORE_VALIDATION_DATASET_AND_METRICS"
        or result.get("schema") != gate.RESULT_SCHEMA
        or result.get("status") != REQUIRED_GATE_STATUS
        or result.get("claim_ceiling") != gate.SUCCESS_CLAIM_CEILING
        or result.get("authority_sha256") != authority_sha
        or result.get("authority_file_sha256") != authority_file_sha
        or result.get("authority_seal_file_sha256") != authority_seal_file_sha
        or result.get("training_scope") != "Q3_PAIRWISE_LEARNABILITY_GATE_ONLY"
        or result.get("q3_pairwise_training_completed") is not True
        or result.get("training") is not True
        or result.get("episode_training") is not False
    ):
        raise V04C3ScreenError(
            "gate status must be exactly GO_500EP_SCREEN_ONLY with the Q3-only claim ceiling"
        )
    for payload, label in (
        (authority, "authority"),
        (result, "result"),
    ):
        _require_false(payload, "test_split_opened", label=label)
        _require_false(payload, "held_out_ee_evaluated", label=label)

    source_manifest_sha = _require_digest_match(
        result,
        "source_manifest_sha256",
        authority,
        "source_manifest_sha256",
    )
    schedule_sha = _digest(result.get("schedule_sha256"), field="result.schedule_sha256")
    source_schedule = authority.get("source_schedule")
    if not isinstance(source_schedule, Mapping):
        raise V04C3ScreenError("gate authority source_schedule is missing")
    if schedule_sha != _digest(
        source_schedule.get("schedule_sha256"), field="authority.source_schedule.schedule_sha256"
    ):
        raise V04C3ScreenError("gate schedule_sha256 is not authenticated")
    _digest(result.get("train_surface_sha256"), field="result.train_surface_sha256")

    source_receipt = authority.get("source")
    if not isinstance(source_receipt, Mapping):
        raise V04C3ScreenError("gate authority source receipt is missing")
    if source_receipt.get("source_manifest_sha256") != source_manifest_sha:
        raise V04C3ScreenError("gate source manifest lineage drifted")
    source_split = source_receipt.get("seed_split")
    expected_split = {
        **{str(seed): "train" for seed in gate.TRAIN_SOURCE_SEEDS},
        **{str(seed): "validation" for seed in gate.VALIDATION_SOURCE_SEEDS},
    }
    if source_split != expected_split or authority.get("source_seed_split") != expected_split:
        raise V04C3ScreenError("gate source split is not exactly 4/3/0")
    if authority.get("test_source_seeds") != []:
        raise V04C3ScreenError("gate authority contains TEST source seeds")

    selected_rung = result.get("selected_q3_rung")
    if type(selected_rung) is not int or selected_rung < 1:
        raise V04C3ScreenError("gate selected_q3_rung is invalid")
    selected = result.get("selected_hybrids")
    expected_seeds = {str(seed) for seed in gate.INITIALIZATION_SEEDS}
    if not isinstance(selected, Mapping) or set(selected) != expected_seeds:
        raise V04C3ScreenError("gate selected_hybrids does not contain exactly three initializations")
    selected_paths: dict[str, Path] = {}
    for seed_key in sorted(expected_seeds, key=int):
        receipt = selected[seed_key]
        if not isinstance(receipt, Mapping):
            raise V04C3ScreenError(f"selected hybrid receipt is malformed for {seed_key}")
        if (
            receipt.get("strict_reload") is not True
            or receipt.get("exact_three_networks") is not True
            or receipt.get("frozen_q1_q2_bit_identical") is not True
            or receipt.get("q3_trainable_only") is not True
            or receipt.get("q1_head_index") != 0
            or receipt.get("q2_head_index") != 1
        ):
            raise V04C3ScreenError(f"selected hybrid receipt is not an exact-three Q3 warm start: {seed_key}")
        selected_path = _regular_artifact(receipt.get("path"), field=f"selected_hybrids[{seed_key}].path")
        expected_sha = _digest(
            receipt.get("file_sha256"), field=f"selected_hybrids[{seed_key}].file_sha256"
        )
        if _file_sha256(selected_path) != expected_sha:
            raise V04C3ScreenError(f"selected hybrid artifact SHA drifted for {seed_key}")
        selected_paths[seed_key] = selected_path

    source_authority = None
    if source_dir is not None:
        try:
            source_authority, _schedule, _prepare, _generate = gate.authenticate_source(
                source_dir=Path(source_dir), prereg_path=prereg_path
            )
        except Exception as error:
            raise V04C3ScreenError(
                f"source authority is not ready; exact missing/invalid source artifact: {error}"
            ) from error
        if source_authority.as_dict() != dict(source_receipt):
            raise V04C3ScreenError("source receipt differs from the authenticated gate authority")

    return {
        "gate_dir": root,
        "status": result["status"],
        "authority": authority,
        "result": result,
        "authority_sha256": authority_sha,
        "authority_file_sha256": authority_file_sha,
        "authority_seal_file_sha256": authority_seal_file_sha,
        "result_file_sha256": result_sha,
        "source_manifest_sha256": source_manifest_sha,
        "schedule_sha256": schedule_sha,
        "train_surface_sha256": result["train_surface_sha256"],
        "selected_q3_rung": selected_rung,
        "selected_hybrid_paths": selected_paths,
        "source_authority": source_authority,
    }


def load_train_c3_batch(
    source_dir: Path,
    gate_receipt: Mapping[str, Any],
) -> tuple[EEAxisPairBatch, str]:
    """Open and verify only the four authenticated TRAIN C3 datasets."""

    source_authority = gate_receipt.get("source_authority")
    if source_authority is None or not hasattr(source_authority, "dataset_file_sha256s"):
        raise V04C3ScreenError(
            "TRAIN C3 source cannot be opened before receipt-only source authentication"
        )
    root = Path(source_dir)
    datasets: dict[int, V04C3OpeningDataset] = {}
    for seed in gate.TRAIN_SOURCE_SEEDS:
        path = root / "source-data" / f"c3-{seed}.json"
        if path.is_symlink() or not path.is_file():
            raise V04C3ScreenError(f"missing authenticated TRAIN C3 dataset: {path}")
        key = str(seed)
        expected_file = _digest(
            source_authority.dataset_file_sha256s[key],
            field=f"source.dataset_file_sha256s[{key}]",
        )
        if _file_sha256(path) != expected_file:
            raise V04C3ScreenError(f"TRAIN C3 dataset file SHA drifted for source seed {seed}")
        try:
            dataset = read_v04_c3_dataset(path)
        except Exception as error:
            raise V04C3ScreenError(f"TRAIN C3 dataset cannot be opened for source seed {seed}: {error}") from error
        expected_dataset = _digest(
            source_authority.dataset_sha256s[key],
            field=f"source.dataset_sha256s[{key}]",
        )
        if dataset.verify() != expected_dataset:
            raise V04C3ScreenError(f"TRAIN C3 dataset digest drifted for source seed {seed}")
        if (
            dataset.source_manifest_sha256 != gate_receipt["source_manifest_sha256"]
            or any(row.pair.source_route != "C3" for row in dataset.rows)
        ):
            raise V04C3ScreenError(f"TRAIN C3 dataset lineage drifted for source seed {seed}")
        datasets[seed] = dataset

    surface = gate._surface_from_datasets(
        datasets,
        ordered_seeds=gate.TRAIN_SOURCE_SEEDS,
    )
    surface_sha = gate._surface_digest(surface)
    if surface_sha != gate_receipt["train_surface_sha256"]:
        raise V04C3ScreenError("authenticated TRAIN C3 surface digest drifted")
    return surface.batch, surface_sha


def _validate_nonnegative_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise V04C3ScreenError(f"{field} must be an integer >= {minimum}")
    return value


def restore_screen_hybrid_state(
    trainer: EEAxisV04HybridTrainer,
    state: Mapping[str, Any],
    *,
    gate_selected_q3_rung: int,
    screen_updates_completed: int,
) -> int:
    """Reload a screen checkpoint while treating Q1/Q2 as immutable receipts.

    The existing hybrid loader intentionally requires
    ``q3_update_count == selected_q3_rung`` for a gate checkpoint.  A screen
    checkpoint has the same selected rung plus additional updates, so this
    consumer-specific seam keeps that strict gate loader unchanged and applies
    the only permitted relaxation explicitly.
    """

    gate_rung = _validate_nonnegative_int(
        gate_selected_q3_rung, field="gate_selected_q3_rung", minimum=1
    )
    completed = _validate_nonnegative_int(
        screen_updates_completed, field="screen_updates_completed"
    )
    if not isinstance(trainer, EEAxisV04HybridTrainer):
        raise V04C3ScreenError("screen reload requires EEAxisV04HybridTrainer")
    if trainer.selected_q3_rung != gate_rung:
        raise V04C3ScreenError("screen reload gate rung does not match trainer")
    if not isinstance(state, Mapping):
        raise V04C3ScreenError("screen hybrid checkpoint must be a mapping")
    expected_metadata = {
        "format_version": HYBRID_CHECKPOINT_VERSION,
        "algorithm": HYBRID_ALGORITHM,
        "initialization_seed": trainer.initialization_seed,
        "selected_q3_rung": gate_rung,
        "v03_config": asdict(trainer.v03_config),
        "v04_config": asdict(trainer.v04_config),
        "route_order": ["C1", "C2", "C3"],
        "frozen_lineage": [lineage.as_dict() for lineage in trainer.frozen_lineage],
    }
    if any(state.get(field) != expected for field, expected in expected_metadata.items()):
        raise V04C3ScreenError("screen hybrid checkpoint metadata mismatch")
    update_count = _validate_nonnegative_int(
        state.get("q3_update_count"), field="screen q3_update_count", minimum=gate_rung
    )
    expected_count = gate_rung + completed
    if update_count != expected_count:
        raise V04C3ScreenError(
            "screen hybrid checkpoint update count must equal gate rung plus completed updates"
        )
    networks = state.get("q_networks")
    if not isinstance(networks, list) or len(networks) != 3:
        raise V04C3ScreenError("screen hybrid checkpoint must contain exactly three heads")
    for index in (0, 1):
        supplied = networks[index]
        expected = trainer.q_nets[index].state_dict()
        if not isinstance(supplied, Mapping) or set(supplied) != set(expected):
            raise V04C3ScreenError("screen checkpoint frozen-head receipt mismatch")
        for name, expected_tensor in expected.items():
            observed = supplied[name]
            if not isinstance(observed, torch.Tensor) or not torch.equal(
                observed.detach().cpu(), expected_tensor.detach().cpu()
            ):
                raise V04C3ScreenError("screen checkpoint frozen-head tensor drifted")
    q3_state = networks[2]
    optimizer_state = state.get("q3_optimizer")
    if not isinstance(q3_state, Mapping) or not isinstance(optimizer_state, Mapping):
        raise V04C3ScreenError("screen checkpoint Q3 payload is malformed")
    try:
        trainer.q3.load_state_dict(q3_state, strict=True)
        trainer.q3_optimizer.load_state_dict(optimizer_state)
    except (RuntimeError, TypeError, ValueError) as error:
        raise V04C3ScreenError("screen checkpoint Q3 state is incompatible") from error
    trainer.q3_update_count = update_count
    trainer._assert_exact_three_networks()
    return update_count


def run_c3_update_screen(
    trainer: Any,
    batch: EEAxisPairBatch,
    *,
    updates: int = SCREEN_UPDATE_COUNT,
    checkpoint_every: int = SCREEN_CHECKPOINT_EVERY,
    on_checkpoint: Callable[[int, Any], None] | None = None,
) -> list[dict[str, Any]]:
    """Apply exactly one full-batch C3 update per screen update index."""

    count = _validate_nonnegative_int(updates, field="updates", minimum=1)
    every = _validate_nonnegative_int(checkpoint_every, field="checkpoint_every", minimum=1)
    if count != SCREEN_UPDATE_COUNT:
        raise V04C3ScreenError("the consumer is frozen to exactly 500 additional C3 updates")
    if every != SCREEN_CHECKPOINT_EVERY:
        raise V04C3ScreenError("the consumer is frozen to checkpoints every 100 updates")
    initial_count = _validate_nonnegative_int(
        getattr(trainer, "q3_update_count", 0),
        field="initial_q3_update_count",
    )
    metrics: list[dict[str, Any]] = []
    for update_index in range(1, count + 1):
        result = trainer.update_c3(batch)
        if not isinstance(result, Mapping) or result.get("route") != "C3":
            raise V04C3ScreenError("C3 update did not return a C3 metric receipt")
        observed_count = _validate_nonnegative_int(
            result.get("update_count"),
            field="update_count",
            minimum=initial_count + update_index,
        )
        if observed_count != initial_count + update_index:
            raise V04C3ScreenError("C3 update count is not sequential")
        metrics.append(dict(result))
        if update_index % every == 0:
            if on_checkpoint is not None:
                on_checkpoint(update_index, trainer)
    return metrics


def aggregate_policy_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate canonical EE by pooled ratio of sums, never mean episode EE."""

    if not rows:
        raise V04C3ScreenError("cannot aggregate an empty policy row set")
    bits = float(math.fsum(float(row["total_bits"]) for row in rows))
    energy = float(math.fsum(float(row["total_energy_j"]) for row in rows))
    decisions = sum(_validate_nonnegative_int(row["decision_count"], field="decision_count") for row in rows)
    served = sum(_validate_nonnegative_int(row["served_user_steps"], field="served_user_steps") for row in rows)
    if not math.isfinite(bits) or bits < 0.0 or not math.isfinite(energy) or energy < 0.0:
        raise V04C3ScreenError("policy rows contain malformed bits or energy")
    if decisions < 1 or served < 0 or served > decisions:
        raise V04C3ScreenError("policy service counts are malformed")
    return {
        "rows": len(rows),
        "decision_count": decisions,
        "served_user_steps": served,
        "served_fraction": served / decisions,
        "outage_fraction": 1.0 - served / decisions,
        "total_bits": bits,
        "total_energy_j": energy,
        "pooled_ratio_of_sums_ee_bits_per_j": bits / energy if energy else 0.0,
    }


def _pair_key(row: Mapping[str, Any]) -> tuple[int, int, int]:
    return (
        _validate_nonnegative_int(row.get("initialization_seed"), field="initialization_seed"),
        _validate_nonnegative_int(row.get("evaluation_seed"), field="evaluation_seed"),
        _validate_nonnegative_int(row.get("checkpoint_update"), field="checkpoint_update"),
    )


def enforce_zero_loss_service_guard(
    full_rows: Sequence[Mapping[str, Any]],
    drop_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Report the zero-loss service guard without hiding a negative result.

    Pairing/schema failures still fail closed because they invalidate the
    comparison.  A genuine service loss is scientific evidence, however, so
    it is returned as ``pass: false`` together with every violation; callers
    must still publish the EE rows and summaries.
    """

    full_by_key = {_pair_key(row): row for row in full_rows}
    drop_by_key = {_pair_key(row): row for row in drop_rows}
    if len(full_by_key) != len(full_rows) or len(drop_by_key) != len(drop_rows):
        raise V04C3ScreenError("service guard received duplicate paired evaluation rows")
    if set(full_by_key) != set(drop_by_key):
        raise V04C3ScreenError("service guard FULL/DROP_C3 pair keys do not match")
    violations = []
    for key in sorted(full_by_key):
        full_served = _validate_nonnegative_int(
            full_by_key[key].get("served_user_steps"), field="FULL.served_user_steps"
        )
        drop_served = _validate_nonnegative_int(
            drop_by_key[key].get("served_user_steps"), field="DROP_C3.served_user_steps"
        )
        if full_served + SERVICE_GUARD_MARGIN < drop_served:
            violations.append(
                {
                    "pair": list(key),
                    "full_served_user_steps": full_served,
                    "drop_c3_served_user_steps": drop_served,
                }
            )
    full_summary = aggregate_policy_rows(full_rows)
    drop_summary = aggregate_policy_rows(drop_rows)
    pooled_pass = (
        full_summary["served_user_steps"] + SERVICE_GUARD_MARGIN
        >= drop_summary["served_user_steps"]
    )
    passed = not violations and pooled_pass
    return {
        "margin_served_user_steps": SERVICE_GUARD_MARGIN,
        "pairs": len(full_rows),
        "pass": passed,
        "per_pair_pass": not violations,
        "pooled_pass": pooled_pass,
        "full_served_user_steps": full_summary["served_user_steps"],
        "drop_c3_served_user_steps": drop_summary["served_user_steps"],
        "violations": violations,
    }


def _write_once_torch(path: Path, payload: object) -> str:
    """Write one binary checkpoint without ever replacing an existing file."""

    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise V04C3ScreenError(f"refusing to overwrite screen checkpoint: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        os.close(descriptor)
        torch.save(payload, temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            raise V04C3ScreenError(
                f"refusing to overwrite screen checkpoint: {destination}"
            ) from error
    finally:
        temporary.unlink(missing_ok=True)
    return _file_sha256(destination)


def _relative(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(Path(path).resolve())


def load_gate_selected_hybrid(
    gate_receipt: Mapping[str, Any],
    *,
    v03_root: Path,
    initialization_seed: int,
) -> EEAxisV04HybridTrainer:
    """Warm-start one exact gate-selected Q3 together with frozen Q1/Q2."""

    seed = _validate_nonnegative_int(
        initialization_seed, field="initialization_seed", minimum=1
    )
    if seed not in gate.INITIALIZATION_SEEDS:
        raise V04C3ScreenError(f"initialization seed is outside the sealed gate: {seed}")
    selected_paths = gate_receipt.get("selected_hybrid_paths")
    if not isinstance(selected_paths, Mapping) or str(seed) not in selected_paths:
        raise V04C3ScreenError(f"selected Q3 checkpoint receipt is missing for {seed}")
    path = _regular_artifact(
        selected_paths[str(seed)], field=f"selected_hybrid_paths[{seed}]"
    )
    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as error:
        raise V04C3ScreenError(f"selected Q3 checkpoint cannot be loaded for {seed}: {path}") from error
    if not isinstance(payload, Mapping):
        raise V04C3ScreenError(f"selected Q3 checkpoint is malformed for {seed}")
    _require_false(payload, "test_split_opened", label=f"selected hybrid {seed}")
    _require_false(payload, "held_out_ee_evaluated", label=f"selected hybrid {seed}")
    if (
        payload.get("schema") != gate.HYBRID_CHECKPOINT_SCHEMA
        or payload.get("authority_sha256") != gate_receipt["authority_sha256"]
        or payload.get("initialization_seed") != seed
        or payload.get("selected_q3_rung") != gate_receipt["selected_q3_rung"]
        or payload.get("q3_pairwise_training") is not True
        or payload.get("episode_training") is not False
    ):
        raise V04C3ScreenError(f"selected Q3 checkpoint metadata is not authenticated for {seed}")
    hybrid_state = payload.get("hybrid")
    if not isinstance(hybrid_state, Mapping):
        raise V04C3ScreenError(f"selected Q3 hybrid state is missing for {seed}")
    try:
        spec: FrozenMeanMaxCheckpointSpec = gate._spec_for_seed(Path(v03_root), seed)
        v03_config, v04_config = gate._config_pair()
        trainer = EEAxisV04HybridTrainer.from_sealed_checkpoint(
            spec,
            v03_config=v03_config,
            v04_config=v04_config,
            selected_q3_rung=int(gate_receipt["selected_q3_rung"]),
        )
        # The gate may have been executed on the Ubuntu worker, where the
        # absolute V0.3 checkpoint prefix is ``/home/sat/...``.  That prefix
        # is not scientific lineage and is not portable to this checkout; the
        # checkpoint bytes, SHA, seed, rung, head indices and config are.  Do
        # not relax any of those fields.  Normalize only the path component
        # after proving its basename is the locally sealed rung-10 artifact.
        observed_lineage = hybrid_state.get("frozen_lineage")
        expected_lineage = [lineage.as_dict() for lineage in trainer.frozen_lineage]
        if not isinstance(observed_lineage, list) or len(observed_lineage) != 2:
            raise V04C3ScreenError(f"selected Q3 frozen lineage is malformed for {seed}")
        for observed, expected in zip(observed_lineage, expected_lineage, strict=True):
            if not isinstance(observed, Mapping):
                raise V04C3ScreenError(f"selected Q3 frozen lineage is malformed for {seed}")
            for field in expected:
                if field == "checkpoint_path":
                    observed_path = observed.get(field)
                    if (
                        not isinstance(observed_path, str)
                        or Path(observed_path).name != Path(expected[field]).name
                    ):
                        raise V04C3ScreenError(
                            f"selected Q3 frozen checkpoint filename drifted for {seed}"
                        )
                elif observed.get(field) != expected[field]:
                    raise V04C3ScreenError(
                        f"selected Q3 frozen lineage drifted in {field} for {seed}"
                    )
        portable_state = dict(hybrid_state)
        portable_state["frozen_lineage"] = expected_lineage
        loaded_count = trainer.load_checkpoint_state(portable_state)
    except Exception as error:
        raise V04C3ScreenError(
            f"selected Q3 checkpoint failed strict warm-start reload for {seed}"
        ) from error
    if loaded_count != int(gate_receipt["selected_q3_rung"]):
        raise V04C3ScreenError(f"selected Q3 warm-start rung drifted for {seed}")
    return trainer


def build_screen_checkpoint_payload(
    trainer: EEAxisV04HybridTrainer,
    gate_receipt: Mapping[str, Any],
    *,
    source_surface_sha256: str,
    screen_updates_completed: int,
) -> dict[str, Any]:
    """Build the authenticated outer envelope for one 100-update receipt."""

    completed = _validate_nonnegative_int(
        screen_updates_completed, field="screen_updates_completed", minimum=1
    )
    if completed not in SCREEN_CHECKPOINT_UPDATES:
        raise V04C3ScreenError("screen checkpoint index must be one of the five 100-update boundaries")
    source_surface_sha = _digest(source_surface_sha256, field="train_surface_sha256")
    gate_rung = _validate_nonnegative_int(
        gate_receipt.get("selected_q3_rung"), field="selected_q3_rung", minimum=1
    )
    expected_count = gate_rung + completed
    if (
        trainer.q3_update_count != expected_count
        or trainer.selected_q3_rung != gate_rung
    ):
        raise V04C3ScreenError("trainer count does not match gate rung plus screen checkpoint")
    return {
        "schema": SCREEN_CHECKPOINT_SCHEMA,
        "claim_ceiling": "ONE_500_UPDATE_TRAIN_SCREEN_NO_TEST",
        "screen_update_unit": SCREEN_UPDATE_UNIT,
        "gate_status": REQUIRED_GATE_STATUS,
        "gate_authority_sha256": gate_receipt["authority_sha256"],
        "gate_result_file_sha256": gate_receipt["result_file_sha256"],
        "source_manifest_sha256": gate_receipt["source_manifest_sha256"],
        "schedule_sha256": gate_receipt["schedule_sha256"],
        "train_surface_sha256": source_surface_sha,
        "initialization_seed": trainer.initialization_seed,
        "gate_selected_q3_rung": gate_rung,
        "screen_updates_completed": completed,
        "total_q3_update_count": expected_count,
        "evaluation_split": EVALUATION_SPLIT,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "q3_pairwise_training": True,
        "episode_training": False,
        "hybrid": trainer.checkpoint_state(),
    }


def load_screen_checkpoint(
    path: Path,
    gate_receipt: Mapping[str, Any],
    *,
    v03_root: Path,
    initialization_seed: int,
) -> EEAxisV04HybridTrainer:
    """Strictly reload one screen checkpoint and re-prove frozen Q1/Q2."""

    checkpoint = Path(path)
    expected_sha = None
    try:
        checkpoint_payload = torch.load(
            checkpoint, map_location="cpu", weights_only=False
        )
    except Exception as error:
        raise V04C3ScreenError(f"screen checkpoint cannot be loaded: {checkpoint}") from error
    if not isinstance(checkpoint_payload, Mapping):
        raise V04C3ScreenError(f"screen checkpoint is malformed: {checkpoint}")
    _require_false(checkpoint_payload, "test_split_opened", label="screen checkpoint")
    _require_false(checkpoint_payload, "held_out_ee_evaluated", label="screen checkpoint")
    if (
        checkpoint_payload.get("schema") != SCREEN_CHECKPOINT_SCHEMA
        or checkpoint_payload.get("screen_update_unit") != SCREEN_UPDATE_UNIT
        or checkpoint_payload.get("gate_status") != REQUIRED_GATE_STATUS
        or checkpoint_payload.get("gate_authority_sha256") != gate_receipt["authority_sha256"]
        or checkpoint_payload.get("gate_result_file_sha256") != gate_receipt["result_file_sha256"]
        or checkpoint_payload.get("source_manifest_sha256") != gate_receipt["source_manifest_sha256"]
        or checkpoint_payload.get("schedule_sha256") != gate_receipt["schedule_sha256"]
        or checkpoint_payload.get("train_surface_sha256") != gate_receipt["train_surface_sha256"]
        or checkpoint_payload.get("evaluation_split") != EVALUATION_SPLIT
        or checkpoint_payload.get("q3_pairwise_training") is not True
        or checkpoint_payload.get("episode_training") is not False
        or checkpoint_payload.get("initialization_seed") != initialization_seed
        or checkpoint_payload.get("gate_selected_q3_rung")
        != gate_receipt["selected_q3_rung"]
    ):
        raise V04C3ScreenError("screen checkpoint envelope is not authenticated")
    completed = _validate_nonnegative_int(
        checkpoint_payload.get("screen_updates_completed"),
        field="screen_updates_completed",
        minimum=1,
    )
    if completed not in SCREEN_CHECKPOINT_UPDATES:
        raise V04C3ScreenError("screen checkpoint index is outside the five frozen boundaries")
    expected_count = int(gate_receipt["selected_q3_rung"]) + completed
    if checkpoint_payload.get("total_q3_update_count") != expected_count:
        raise V04C3ScreenError("screen checkpoint total Q3 update count is not authenticated")
    trainer = load_gate_selected_hybrid(
        gate_receipt,
        v03_root=v03_root,
        initialization_seed=initialization_seed,
    )
    hybrid_state = checkpoint_payload.get("hybrid")
    if not isinstance(hybrid_state, Mapping):
        raise V04C3ScreenError("screen checkpoint hybrid state is missing")
    loaded = restore_screen_hybrid_state(
        trainer,
        hybrid_state,
        gate_selected_q3_rung=int(gate_receipt["selected_q3_rung"]),
        screen_updates_completed=completed,
    )
    if loaded != expected_count:
        raise V04C3ScreenError("screen checkpoint update count is not authenticated")
    expected_sha = checkpoint_payload.get("file_sha256")
    if expected_sha is not None and _file_sha256(checkpoint) != _digest(
        expected_sha, field="screen checkpoint file_sha256"
    ):
        raise V04C3ScreenError("screen checkpoint file SHA drifted")
    return trainer


def save_screen_checkpoint(
    path: Path,
    trainer: EEAxisV04HybridTrainer,
    gate_receipt: Mapping[str, Any],
    *,
    source_surface_sha256: str,
    screen_updates_completed: int,
) -> str:
    """Persist one 100-update checkpoint; the caller performs strict reload."""

    payload = build_screen_checkpoint_payload(
        trainer,
        gate_receipt,
        source_surface_sha256=source_surface_sha256,
        screen_updates_completed=screen_updates_completed,
    )
    return _write_once_torch(path, payload)


def _make_environment(archive: TleArchive, *, users: int = USERS) -> TrainerEnvironment:
    if type(users) is not int or users != USERS:
        raise V04C3ScreenError("the V0.4 screen is frozen to 100 users")
    driver = ScenarioDriver(
        archive,
        ScenarioConfig(
            mobility=MobilityConfig(num_users=users),
            steps_per_episode=STEPS_PER_EPISODE,
        ),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    return TrainerEnvironment(StepEnvironment(driver), sampler)


def _frozen_archive(record: Any, source_root: Path, target_root: Path) -> TleArchive:
    """Build a temporary hard-linked TLE view from the frozen prereg rows."""

    if target_root.exists() or target_root.is_symlink():
        raise V04C3ScreenError(f"temporary TLE view already exists: {target_root}")
    target_root.mkdir(parents=True, exist_ok=False)
    try:
        rows = record.sections["ephemeris"]["frozen_files"]
        for row in rows:
            if not isinstance(row, Mapping) or not isinstance(row.get("file"), str):
                raise V04C3ScreenError("preregistered frozen TLE file row is malformed")
            source = Path(source_root) / row["file"]
            target = target_root / row["file"]
            if source.is_symlink() or not source.is_file():
                raise V04C3ScreenError(f"frozen TLE source file is missing: {source}")
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(source, target)
            except OSError:
                target.symlink_to(source)
        archive = TleArchive(target_root)
        assert_ephemeris_matches_record(record, archive=archive)
        return archive
    except Exception:
        # The temporary directory is owned by the context manager in
        # ``run_screen``; leave cleanup to it while preserving the original
        # exception and never touching the user's TLE directory.
        raise


def _action_trace_sha256(
    *,
    policy_label: str,
    evaluation_seed: int,
    actions: Sequence[Sequence[int]],
) -> str:
    return canonical_sha256(
        {
            "schema": "multi-catfish-mcrl-v04-action-trace-v1",
            "policy_label": policy_label,
            "evaluation_seed": evaluation_seed,
            "actions": actions,
        }
    )


def evaluate_v04_episode(
    trainer: EEAxisV04HybridTrainer,
    archive: TleArchive,
    *,
    gate_authority_sha256: str,
    initialization_seed: int,
    checkpoint_update: int,
    evaluation_seed: int,
    drop_c3: bool,
    gate_selected_q3_rung: int | None = None,
    total_q3_update_count: int | None = None,
    evaluation_role: str | None = None,
) -> dict[str, Any]:
    """Evaluate one matched TRAIN episode under FULL or DROP_C3 deployment.

    ``checkpoint_update`` is the number of *additional full-batch C3
    source-training updates* after the selected gate rung.  Zero is reserved
    for the primary evaluation of the sealed gate-selected hybrid; it is not a
    simulator-episode count.
    """

    if not isinstance(trainer, EEAxisV04HybridTrainer):
        raise V04C3ScreenError("episode evaluation requires the V0.4 hybrid trainer")
    init = _validate_nonnegative_int(
        initialization_seed, field="initialization_seed", minimum=1
    )
    update = _validate_nonnegative_int(
        checkpoint_update, field="screen_updates_completed"
    )
    seed = _validate_nonnegative_int(evaluation_seed, field="evaluation_seed")
    gate_rung = _validate_nonnegative_int(
        trainer.selected_q3_rung if gate_selected_q3_rung is None else gate_selected_q3_rung,
        field="gate_selected_q3_rung",
        minimum=1,
    )
    total_count = _validate_nonnegative_int(
        trainer.q3_update_count if total_q3_update_count is None else total_q3_update_count,
        field="total_q3_update_count",
        minimum=gate_rung,
    )
    if trainer.selected_q3_rung != gate_rung or trainer.q3_update_count != total_count:
        raise V04C3ScreenError("evaluation trainer count does not match authenticated metadata")
    expected_count = gate_rung + update
    if total_count != expected_count:
        raise V04C3ScreenError(
            "evaluation total Q3 update count must equal gate rung plus screen updates"
        )
    role = evaluation_role or (
        PRIMARY_EVALUATION_ROLE if update == 0 else EXPLORATORY_EVALUATION_ROLE
    )
    expected_role = PRIMARY_EVALUATION_ROLE if update == 0 else EXPLORATORY_EVALUATION_ROLE
    if role != expected_role:
        raise V04C3ScreenError("evaluation role does not match screen update index")
    authority_sha = _digest(gate_authority_sha256, field="gate_authority_sha256")
    policy_label = "DROP_C3" if drop_c3 else "FULL"
    field = KeyedFadingField.from_components(
        FADING_SCHEMA,
        authority_sha,
        init,
        update,
        seed,
    )
    environment = _make_environment(archive)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(seed)
    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    interval_s = float(environment.environment.driver.config.ephemeris.time_step_s)
    if not math.isfinite(interval_s) or interval_s <= 0.0:
        raise V04C3ScreenError("TRAIN evaluation interval must be finite and positive")

    total_bits = 0.0
    total_energy = 0.0
    served_user_steps = 0
    steps = 0
    action_trace: list[list[int]] = []
    while True:
        legacy = encode_ee_axis_state(environment.environment, observation)
        c3_state = encode_ee_axis_v04_c3_state(
            environment.environment,
            observation,
            interval_s=interval_s,
            kappa_bits=float(trainer.v04_config.kappa_bits),
        )
        if not np.array_equal(legacy.action_masks, c3_state.action_masks):
            raise V04C3ScreenError("V0.3/V0.4 deployment masks differ on the matched episode")
        actions = trainer.select_greedy_actions(
            legacy.state_matrix,
            c3_state.state_matrix,
            c3_state.action_masks,
            drop_c3=drop_c3,
        )
        action_trace.append([int(value) for value in actions.tolist()])
        result = environment.step(actions, env_rng)
        outcome = environment.last_outcome
        rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
        power = float(outcome.system_power_w)
        system_rate = float(math.fsum(float(value) for value in rates))
        if (
            rates.shape != (USERS,)
            or not np.all(np.isfinite(rates))
            or np.any(rates < 0.0)
            or not math.isfinite(power)
            or power < 0.0
            or (power == 0.0 and system_rate > 0.0)
        ):
            raise V04C3ScreenError("TRAIN evaluation produced malformed physical EE inputs")
        total_bits += system_rate * interval_s
        total_energy += power * interval_s
        served_user_steps += int(outcome.resolution.served_count)
        steps += 1
        if result.done:
            break
        observation = outcome.observation

    if steps != STEPS_PER_EPISODE:
        raise V04C3ScreenError(
            f"TRAIN evaluation episode length drifted: expected {STEPS_PER_EPISODE}, got {steps}"
        )
    decisions = steps * USERS
    if total_energy == 0.0 and total_bits != 0.0:
        raise V04C3ScreenError("positive TRAIN throughput with zero energy is invalid")
    ee = total_bits / total_energy if total_energy else 0.0
    served_fraction = served_user_steps / decisions
    return {
        "schema": "multi-catfish-mcrl-v04-train-episode-v1",
        "policy_label": policy_label,
        "evaluation_split": EVALUATION_SPLIT,
        "initialization_seed": init,
        "checkpoint_update": update,
        "gate_selected_q3_rung": gate_rung,
        "screen_updates_completed": update,
        "total_q3_update_count": total_count,
        "evaluation_role": role,
        "screen_update_unit": SCREEN_UPDATE_UNIT,
        "evaluation_seed": seed,
        "fading_field_sha256": field.root_digest,
        "steps": steps,
        "users": USERS,
        "decision_count": decisions,
        "total_bits": total_bits,
        "total_energy_j": total_energy,
        "ratio_of_sums_ee_bits_per_j": ee,
        "served_user_steps": served_user_steps,
        "served_fraction": served_fraction,
        "outage_fraction": 1.0 - served_fraction,
        "action_trace_sha256": _action_trace_sha256(
            policy_label=policy_label,
            evaluation_seed=seed,
            actions=action_trace,
        ),
        "test_split_opened": TEST_SPLIT_OPENED,
        "held_out_ee_evaluated": True,
    }


def evaluate_matched_checkpoint(
    trainer: EEAxisV04HybridTrainer,
    archive: TleArchive,
    *,
    gate_receipt: Mapping[str, Any],
    initialization_seed: int,
    checkpoint_update: int,
    total_q3_update_count: int | None = None,
    evaluation_role: str | None = None,
    evaluation_seeds: Sequence[int] = EVALUATION_SEEDS,
) -> dict[str, Any]:
    """Run matched FULL/DROP_C3 arms and report, but never hide, the guard."""

    if tuple(int(seed) for seed in evaluation_seeds) != EVALUATION_SEEDS:
        raise V04C3ScreenError("evaluation seeds are frozen to 2026092401..2026092410")
    full_rows: list[dict[str, Any]] = []
    drop_rows: list[dict[str, Any]] = []
    update = _validate_nonnegative_int(
        checkpoint_update, field="screen_updates_completed"
    )
    gate_rung = _validate_nonnegative_int(
        gate_receipt.get("selected_q3_rung"),
        field="gate_selected_q3_rung",
        minimum=1,
    )
    total_count = _validate_nonnegative_int(
        trainer.q3_update_count if total_q3_update_count is None else total_q3_update_count,
        field="total_q3_update_count",
        minimum=gate_rung,
    )
    if trainer.selected_q3_rung != gate_rung or trainer.q3_update_count != total_count:
        raise V04C3ScreenError("matched checkpoint trainer count is not authenticated")
    if total_count != gate_rung + update:
        raise V04C3ScreenError(
            "matched checkpoint total Q3 update count must equal gate rung plus screen updates"
        )
    role = evaluation_role or (
        PRIMARY_EVALUATION_ROLE if update == 0 else EXPLORATORY_EVALUATION_ROLE
    )
    expected_role = PRIMARY_EVALUATION_ROLE if update == 0 else EXPLORATORY_EVALUATION_ROLE
    if role != expected_role:
        raise V04C3ScreenError("matched checkpoint role does not match screen update index")
    for seed in EVALUATION_SEEDS:
        full = evaluate_v04_episode(
            trainer,
            archive,
            gate_authority_sha256=str(gate_receipt["authority_sha256"]),
            initialization_seed=initialization_seed,
            checkpoint_update=checkpoint_update,
            evaluation_seed=seed,
            drop_c3=False,
            gate_selected_q3_rung=gate_rung,
            total_q3_update_count=total_count,
            evaluation_role=role,
        )
        drop = evaluate_v04_episode(
            trainer,
            archive,
            gate_authority_sha256=str(gate_receipt["authority_sha256"]),
            initialization_seed=initialization_seed,
            checkpoint_update=checkpoint_update,
            evaluation_seed=seed,
            drop_c3=True,
            gate_selected_q3_rung=gate_rung,
            total_q3_update_count=total_count,
            evaluation_role=role,
        )
        if (
            full["fading_field_sha256"] != drop["fading_field_sha256"]
            or full["evaluation_seed"] != drop["evaluation_seed"]
            or full["initialization_seed"] != drop["initialization_seed"]
            or full["checkpoint_update"] != drop["checkpoint_update"]
            or full["gate_selected_q3_rung"] != drop["gate_selected_q3_rung"]
            or full["screen_updates_completed"] != drop["screen_updates_completed"]
            or full["total_q3_update_count"] != drop["total_q3_update_count"]
            or full["evaluation_role"] != drop["evaluation_role"]
        ):
            raise V04C3ScreenError("FULL and DROP_C3 are not paired on one keyed field")
        full_rows.append(full)
        drop_rows.append(drop)
    guard = enforce_zero_loss_service_guard(full_rows, drop_rows)
    return {
        "initialization_seed": int(initialization_seed),
        "gate_selected_q3_rung": gate_rung,
        "screen_updates_completed": update,
        "total_q3_update_count": total_count,
        "checkpoint_update": update,
        "evaluation_role": role,
        "screen_update_unit": SCREEN_UPDATE_UNIT,
        "evaluation_split": EVALUATION_SPLIT,
        "full": full_rows,
        "drop_c3": drop_rows,
        "full_summary": aggregate_policy_rows(full_rows),
        "drop_c3_summary": aggregate_policy_rows(drop_rows),
        "service_guard": guard,
        "test_split_opened": TEST_SPLIT_OPENED,
        "held_out_ee_evaluated": True,
    }


def _evaluate_checkpoint_set(
    archive: TleArchive,
    *,
    gate_receipt: Mapping[str, Any],
    v03_root: Path,
    screen_updates_completed: int,
    load_trainer: Callable[[int], EEAxisV04HybridTrainer],
    evaluation_role: str,
    evaluation_source: str,
) -> dict[str, Any]:
    """Evaluate one immutable point across all three initializations.

    The zero-update point is intentionally kept in a separate result object
    by :func:`run_screen`; this helper only makes its metadata explicit and
    does not permit a later trend checkpoint to replace it.
    """

    update = _validate_nonnegative_int(
        screen_updates_completed, field="screen_updates_completed"
    )
    if update == 0:
        expected_role = PRIMARY_EVALUATION_ROLE
    elif update in SCREEN_CHECKPOINT_UPDATES:
        expected_role = EXPLORATORY_EVALUATION_ROLE
    else:
        raise V04C3ScreenError("evaluation point is outside the primary/trend protocol")
    if evaluation_role != expected_role:
        raise V04C3ScreenError("evaluation source role does not match its update point")
    gate_rung = _validate_nonnegative_int(
        gate_receipt.get("selected_q3_rung"),
        field="gate_selected_q3_rung",
        minimum=1,
    )
    full_rows: list[dict[str, Any]] = []
    drop_rows: list[dict[str, Any]] = []
    per_initialization: dict[str, Any] = {}
    for seed in INITIALIZATION_SEEDS:
        trainer = load_trainer(seed)
        expected_count = gate_rung + update
        if (
            trainer.selected_q3_rung != gate_rung
            or trainer.q3_update_count != expected_count
        ):
            raise V04C3ScreenError(
                f"{evaluation_source} trainer count is not gate rung plus screen updates for {seed}"
            )
        matched = evaluate_matched_checkpoint(
            trainer,
            archive,
            gate_receipt=gate_receipt,
            initialization_seed=seed,
            checkpoint_update=update,
            total_q3_update_count=expected_count,
            evaluation_role=evaluation_role,
        )
        full_rows.extend(matched["full"])
        drop_rows.extend(matched["drop_c3"])
        per_initialization[str(seed)] = matched
    guard = enforce_zero_loss_service_guard(full_rows, drop_rows)
    return {
        "evaluation_role": evaluation_role,
        "evaluation_source": evaluation_source,
        "screen_update_unit": SCREEN_UPDATE_UNIT,
        "gate_selected_q3_rung": gate_rung,
        "screen_updates_completed": update,
        "total_q3_update_count": gate_rung + update,
        "checkpoint_update": update,
        "evaluation_split": EVALUATION_SPLIT,
        "full": aggregate_policy_rows(full_rows),
        "drop_c3": aggregate_policy_rows(drop_rows),
        "service_guard": guard,
        "per_initialization": per_initialization,
        "test_split_opened": TEST_SPLIT_OPENED,
        "held_out_ee_evaluated": True,
    }


def _write_once_json(path: Path, payload: object) -> str:
    """Write a canonical JSON receipt exactly once."""

    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise V04C3ScreenError(f"refusing to overwrite screen JSON receipt: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_bytes(payload)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            raise V04C3ScreenError(
                f"refusing to overwrite screen JSON receipt: {destination}"
            ) from error
    finally:
        temporary.unlink(missing_ok=True)
    return _file_sha256(destination)


def _network_state_equal(left: Any, right: Any) -> bool:
    left_state = left.state_dict()
    right_state = right.state_dict()
    return set(left_state) == set(right_state) and all(
        isinstance(left_state[name], torch.Tensor)
        and isinstance(right_state[name], torch.Tensor)
        and torch.equal(left_state[name].detach().cpu(), right_state[name].detach().cpu())
        for name in left_state
    )


def _train_and_checkpoint(
    *,
    gate_receipt: Mapping[str, Any],
    source_batch: EEAxisPairBatch,
    source_surface_sha256: str,
    v03_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Warm-start all three gate hybrids and save/reload five boundaries."""

    checkpoint_root = Path(output_dir) / "checkpoints"
    checkpoint_receipts: dict[str, list[dict[str, Any]]] = {}
    training_receipts: dict[str, dict[str, Any]] = {}
    for seed in INITIALIZATION_SEEDS:
        trainer = load_gate_selected_hybrid(
            gate_receipt,
            v03_root=Path(v03_root),
            initialization_seed=seed,
        )
        initial_count = trainer.q3_update_count
        seed_receipts: list[dict[str, Any]] = []

        def checkpoint_callback(update_index: int, current: Any) -> None:
            if not isinstance(current, EEAxisV04HybridTrainer):
                raise V04C3ScreenError("C3 checkpoint callback received a non-hybrid trainer")
            checkpoint_path = checkpoint_root / (
                f"hybrid-{seed}-screen-update-{update_index:06d}.pt"
            )
            checkpoint_sha = save_screen_checkpoint(
                checkpoint_path,
                current,
                gate_receipt,
                source_surface_sha256=source_surface_sha256,
                screen_updates_completed=update_index,
            )
            # A checkpoint is not accepted until a fresh trainer reloads it.
            restored = load_screen_checkpoint(
                checkpoint_path,
                gate_receipt,
                v03_root=Path(v03_root),
                initialization_seed=seed,
            )
            if not _network_state_equal(current.q1, restored.q1) or not _network_state_equal(
                current.q2, restored.q2
            ) or not _network_state_equal(current.q3, restored.q3):
                raise V04C3ScreenError(
                    f"screen checkpoint reload is not bit-identical for seed {seed}, update {update_index}"
                )
            seed_receipts.append(
                {
                    "path": _relative(checkpoint_path),
                    "file_sha256": checkpoint_sha,
                    "gate_selected_q3_rung": initial_count,
                    "screen_updates_completed": update_index,
                    "total_q3_update_count": restored.q3_update_count,
                    "q3_update_count": restored.q3_update_count,
                    "strict_reload": True,
                    "exact_three_networks": len(restored.q_nets) == 3,
                    "frozen_q1_q2_bit_identical": True,
                }
            )

        metrics = run_c3_update_screen(
            trainer,
            source_batch,
            on_checkpoint=checkpoint_callback,
        )
        if trainer.q3_update_count != initial_count + SCREEN_UPDATE_COUNT:
            raise V04C3ScreenError(f"500-update count did not close for initialization {seed}")
        if len(seed_receipts) != len(SCREEN_CHECKPOINT_UPDATES):
            raise V04C3ScreenError(f"checkpoint schedule did not close for initialization {seed}")
        checkpoint_receipts[str(seed)] = seed_receipts
        training_receipts[str(seed)] = {
            "gate_selected_q3_rung": initial_count,
            "screen_updates_completed": SCREEN_UPDATE_COUNT,
            "screen_update_unit": SCREEN_UPDATE_UNIT,
            "screen_updates": SCREEN_UPDATE_COUNT,
            "total_q3_update_count": trainer.q3_update_count,
            "final_q3_update_count": trainer.q3_update_count,
            "last_loss": float(metrics[-1]["loss"]),
            "checkpoints": seed_receipts,
        }
    return {
        "initialization_seeds": list(INITIALIZATION_SEEDS),
        "screen_update_unit": SCREEN_UPDATE_UNIT,
        "screen_updates": SCREEN_UPDATE_COUNT,
        "screen_updates_completed": SCREEN_UPDATE_COUNT,
        "checkpoint_updates": list(SCREEN_CHECKPOINT_UPDATES),
        "checkpoints": checkpoint_receipts,
        "training": training_receipts,
    }


def run_screen(
    *,
    gate_dir: Path = DEFAULT_GATE_DIR,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    v03_root: Path = DEFAULT_V03_ROOT,
    prereg_path: Path = DEFAULT_PREREG,
    tle_root: Path = DEFAULT_TLE_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """Execute the one bounded post-GO C3 screen.

    This function is intentionally not called at import time.  It fails before
    any update if the gate/source receipts are not fully authenticated, and it
    refuses to reuse an existing output directory.
    """

    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise V04C3ScreenError(f"refusing to overwrite existing screen output: {destination}")
    started = __import__("time").perf_counter()
    gate_receipt = authenticate_gate(
        Path(gate_dir),
        source_dir=Path(source_dir),
        prereg_path=Path(prereg_path),
    )
    source_batch, source_surface_sha = load_train_c3_batch(
        Path(source_dir), gate_receipt
    )
    destination.mkdir(parents=True, exist_ok=False)

    # The primary conclusion is evaluated first from the sealed gate-selected
    # hybrid itself.  It has zero additional source updates and therefore
    # cannot be overwritten by any later exploratory trend point.  Its
    # immutable receipt is written before the first C3 update, so an
    # interrupted exploratory run cannot erase the primary evidence.
    record = read_prereg(Path(prereg_path))
    primary_evaluation: dict[str, Any]
    exploratory_trend: dict[str, Any] = {}
    primary_receipt_file_sha: str
    with tempfile.TemporaryDirectory(prefix="mcrl-v04-c3-screen-tle-") as temporary:
        archive = _frozen_archive(record, Path(tle_root), Path(temporary) / "frozen-tle")
        primary_evaluation = _evaluate_checkpoint_set(
            archive,
            gate_receipt=gate_receipt,
            v03_root=Path(v03_root),
            screen_updates_completed=0,
            load_trainer=lambda seed: load_gate_selected_hybrid(
                gate_receipt,
                v03_root=Path(v03_root),
                initialization_seed=seed,
            ),
            evaluation_role=PRIMARY_EVALUATION_ROLE,
            evaluation_source="sealed_gate_selected_hybrid",
        )
        primary_receipt_file_sha = _write_once_json(
            destination / "primary-evaluation.json",
            {
                "schema": PRIMARY_RECEIPT_SCHEMA,
                "status": "PRIMARY_EVALUATION_COMPLETE",
                "claim_ceiling": "PRIMARY_SELECTED_GATE_RUNG_TRAIN_EE_NO_TEST",
                "gate_status": REQUIRED_GATE_STATUS,
                "gate_authority_sha256": gate_receipt["authority_sha256"],
                "gate_result_file_sha256": gate_receipt["result_file_sha256"],
                "source_manifest_sha256": gate_receipt["source_manifest_sha256"],
                "schedule_sha256": gate_receipt["schedule_sha256"],
                "train_surface_sha256": source_surface_sha,
                "gate_selected_q3_rung": gate_receipt["selected_q3_rung"],
                "screen_updates_completed": 0,
                "total_q3_update_count": gate_receipt["selected_q3_rung"],
                "screen_update_unit": SCREEN_UPDATE_UNIT,
                "evaluation_split": EVALUATION_SPLIT,
                "test_split_opened": TEST_SPLIT_OPENED,
                "held_out_ee_evaluated": True,
                "evaluation": primary_evaluation,
            },
        )

        # No C3 update is allowed before the primary receipt above has been
        # durably linked into the output directory.
        training = _train_and_checkpoint(
            gate_receipt=gate_receipt,
            source_batch=source_batch,
            source_surface_sha256=source_surface_sha,
            v03_root=Path(v03_root),
            output_dir=destination,
        )

        # The saved checkpoints are exploratory trend points only.  Their
        # results are stored under a distinct mapping so no key collision can
        # replace the primary selected-rung result.
        for update_index in SCREEN_CHECKPOINT_UPDATES:
            exploratory_trend[str(update_index)] = _evaluate_checkpoint_set(
                archive,
                gate_receipt=gate_receipt,
                v03_root=Path(v03_root),
                screen_updates_completed=update_index,
                load_trainer=lambda seed, update_index=update_index: load_screen_checkpoint(
                    destination
                    / "checkpoints"
                    / f"hybrid-{seed}-screen-update-{update_index:06d}.pt",
                    gate_receipt,
                    v03_root=Path(v03_root),
                    initialization_seed=seed,
                ),
                evaluation_role=EXPLORATORY_EVALUATION_ROLE,
                evaluation_source="reloaded_screen_checkpoint",
            )

    result = {
        "schema": SCREEN_RESULT_SCHEMA,
        "status": "SCREEN_COMPLETE",
        "claim_ceiling": "ONE_PRIMARY_PLUS_EXPLORATORY_500_UPDATE_TRAIN_SCREEN_NO_TEST",
        "gate_status": REQUIRED_GATE_STATUS,
        "gate_authority_sha256": gate_receipt["authority_sha256"],
        "gate_result_file_sha256": gate_receipt["result_file_sha256"],
        "source_manifest_sha256": gate_receipt["source_manifest_sha256"],
        "schedule_sha256": gate_receipt["schedule_sha256"],
        "train_surface_sha256": source_surface_sha,
        "evaluation_split": EVALUATION_SPLIT,
        "evaluation_seeds": list(EVALUATION_SEEDS),
        "initialization_seeds": list(INITIALIZATION_SEEDS),
        "gate_selected_q3_rung": gate_receipt["selected_q3_rung"],
        "primary_screen_updates_completed": 0,
        "primary_receipt_file_sha256": primary_receipt_file_sha,
        "screen_update_unit": SCREEN_UPDATE_UNIT,
        "screen_update_count": SCREEN_UPDATE_COUNT,
        "checkpoint_updates": list(SCREEN_CHECKPOINT_UPDATES),
        "full_policy": "Q1+Q2+Q3",
        "drop_policy": "Q1+Q2",
        "deployment": "one_common_masked_argmax_direct_sum",
        "ratio_of_sums_ee": True,
        "service_guard": "zero_loss_per_pair_and_pooled",
        "test_split_opened": TEST_SPLIT_OPENED,
        "held_out_ee_evaluated": True,
        "episode_training": False,
        "training": training,
        "primary_evaluation": primary_evaluation,
        "exploratory_trend": exploratory_trend,
        "evaluations": {
            "primary": primary_evaluation,
            "exploratory_trend": exploratory_trend,
        },
        "elapsed_s": __import__("time").perf_counter() - started,
    }
    result_file_sha = _write_once_json(destination / "result.json", result)
    result_seal_sha = _write_once_json(
        destination / "result-seal.json",
        {
            "schema": "multi-catfish-mcrl-v04-c3-500-update-screen-result-seal-v1",
            "result_file_sha256": result_file_sha,
            "primary_receipt_file_sha256": primary_receipt_file_sha,
            "gate_authority_sha256": gate_receipt["authority_sha256"],
            "test_split_opened": TEST_SPLIT_OPENED,
            "held_out_ee_evaluated": True,
        },
    )
    return {
        "schema": SCREEN_RESULT_SCHEMA,
        "status": "SCREEN_COMPLETE",
        "result_file_sha256": result_file_sha,
        "result_seal_file_sha256": result_seal_sha,
        "gate_selected_q3_rung": gate_receipt["selected_q3_rung"],
        "primary_screen_updates_completed": 0,
        "primary_receipt_file_sha256": primary_receipt_file_sha,
        "screen_update_unit": SCREEN_UPDATE_UNIT,
        "screen_update_count": SCREEN_UPDATE_COUNT,
        "checkpoint_updates": list(SCREEN_CHECKPOINT_UPDATES),
        "evaluation_split": EVALUATION_SPLIT,
        "test_split_opened": TEST_SPLIT_OPENED,
        "held_out_ee_evaluated": True,
        "episode_training": False,
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate-dir", type=Path, default=DEFAULT_GATE_DIR)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--v03-root", type=Path, default=DEFAULT_V03_ROOT)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    receipt = run_screen(
        gate_dir=args.gate_dir,
        source_dir=args.source_dir,
        v03_root=args.v03_root,
        prereg_path=args.prereg,
        tle_root=args.tle_root,
        output_dir=args.output_dir,
    )
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":  # pragma: no cover - command-line seam
    raise SystemExit(main())
