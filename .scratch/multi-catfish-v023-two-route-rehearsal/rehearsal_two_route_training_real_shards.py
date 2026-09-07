"""Run a conspicuously non-formal C1/C2 training rehearsal on real shards.

This module imports the two-route model and learner orchestrator directly.  It
does not import or invoke the formal source-training runner CLI.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TWO_ROUTE_DIR = REPO / ".scratch/multi-catfish-v023-two-route-source-training-runner"
DEFAULT_MODEL_CONFIG = (
    REPO
    / ".scratch/multi-catfish-v023-c1c2-successor/"
    "V023-C1C2-SUCCESSOR-MODEL-CONFIG.json"
)
DEFAULT_SHARD_ROOT = Path("/home/sat/mcrl-v023-real-shards-rehearsal")
DEFAULT_TRAIN_SEED = 2927175120652069826
REQUIRED_OUTPUT_TOKEN = "REHEARSAL-NONFORMAL"
CLAIM_CEILING = "ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT"
RECEIPT_SCHEMA = "multi-catfish-mcrl-v023-two-route-rehearsal-receipt-v1"

if str(TWO_ROUTE_DIR) not in sys.path:
    sys.path.insert(0, str(TWO_ROUTE_DIR))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from ee_axis_two_route_model import EEAxisTwoRouteConfig
from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_v014_head import EEAxisV014HeadConfig
from rehearsal_real_shard_provider import RehearsalRealShardProvider
from v023_two_route_learner_orchestrator import (
    ARMS,
    ROUTE_ORDER,
    SOURCE_ABLATION_MAP,
    V023TwoRouteLearnerOrchestrator,
    V023TwoRouteOrchestratorConfig,
)


class RehearsalTrainingError(RuntimeError):
    """The non-formal rehearsal could not complete safely."""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_output_root(value: str | Path) -> Path:
    root = Path(value)
    if REQUIRED_OUTPUT_TOKEN not in root.name:
        raise RehearsalTrainingError(
            f"output-root basename must contain {REQUIRED_OUTPUT_TOKEN}"
        )
    if root.exists() or root.is_symlink():
        raise RehearsalTrainingError("output root must not exist beforehand")
    parent = root.parent
    if parent.is_symlink() or not parent.is_dir():
        raise RehearsalTrainingError(
            "output-root parent must already be an existing non-symlink directory"
        )
    return root


def _load_model_config(path: str | Path) -> EEAxisTwoRouteConfig:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise RehearsalTrainingError("model config must be a regular file")
    if any(part.upper() == "TEST" for part in source.parts):
        raise RehearsalTrainingError("TEST model-config paths are forbidden")
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as cause:
        raise RehearsalTrainingError("model config JSON is invalid") from cause
    if not isinstance(raw, Mapping) or set(raw) != {"q1", "q2"}:
        raise RehearsalTrainingError("model config must contain exactly q1 and q2")
    try:
        q1 = dict(raw["q1"])
        q2 = dict(raw["q2"])
        for values, fields in (
            (q1, ("hidden_layers", "loss_weights")),
            (q2, ("hidden_layers",)),
        ):
            for field in fields:
                if isinstance(values.get(field), list):
                    values[field] = tuple(values[field])
        return EEAxisTwoRouteConfig(
            q1=EEAxisActionSharedConfig(**q1),
            q2=EEAxisV014HeadConfig(**q2),
        )
    except (TypeError, ValueError) as cause:
        raise RehearsalTrainingError("model config is incompatible") from cause


def _tree_exact(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, torch.Tensor):
        return torch.equal(left, right)
    if isinstance(left, np.ndarray):
        return np.array_equal(left, right)
    if isinstance(left, Mapping):
        return tuple(left) == tuple(right) and all(
            _tree_exact(left[key], right[key]) for key in left
        )
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(
            _tree_exact(first, second)
            for first, second in zip(left, right, strict=True)
        )
    return bool(left == right)


def _json_write(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = (
        json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
    )
    with path.open("xb") as handle:
        handle.write(encoded)


def _torch_write(path: Path, payload: object) -> str:
    if path.exists() or path.is_symlink():
        raise RehearsalTrainingError(f"refusing to overwrite rehearsal export: {path}")
    torch.save(payload, path)
    return _file_sha256(path)


def _loss_checks(round_receipt: object, *, phase: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for arm_update in round_receipt.arm_updates:
        loss = arm_update.update.get("loss")
        finite = (
            not isinstance(loss, bool)
            and isinstance(loss, (int, float))
            and math.isfinite(float(loss))
        )
        checks.append(
            {
                "phase": phase,
                "update_cursor": round_receipt.update_cursor,
                "route": round_receipt.route,
                "arm": arm_update.arm,
                "source": arm_update.source,
                "loss": float(loss) if finite else None,
                "finite": finite,
                "interpretation": "NON_DECISIONAL_ENGINEERING_REHEARSAL_LOSS",
            }
        )
    if not all(item["finite"] for item in checks):
        raise RehearsalTrainingError("non-finite rehearsal loss observed")
    return checks


def _advance_epoch(
    orchestrator: V023TwoRouteLearnerOrchestrator,
    *,
    phase: str,
    epoch_number: int,
    update_timings: list[dict[str, Any]],
    epoch_timings: list[dict[str, Any]],
    loss_checks: list[dict[str, Any]],
) -> None:
    epoch_started = time.perf_counter()
    for _ in ROUTE_ORDER:
        route = orchestrator.next_route
        cursor = orchestrator.update_cursor
        update_started = time.perf_counter()
        result = orchestrator.advance()
        elapsed = time.perf_counter() - update_started
        update_timings.append(
            {
                "phase": phase,
                "epoch": epoch_number,
                "update_cursor": cursor,
                "route": route,
                "wall_seconds": elapsed,
            }
        )
        loss_checks.extend(_loss_checks(result, phase=phase))
    epoch_timings.append(
        {
            "phase": phase,
            "epoch": epoch_number,
            "wall_seconds": time.perf_counter() - epoch_started,
        }
    )


def _base_receipt(
    *,
    output_root: Path,
    shard_root: Path,
    epochs: int,
    train_seed: int,
) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "status": "REHEARSAL_FAIL",
        "formal": False,
        "rehearsal": True,
        "claim_ceiling": CLAIM_CEILING,
        "scientific_claim": False,
        "episode_training": False,
        "loss_interpretation": "NON_DECISIONAL_ENGINEERING_REHEARSAL_ONLY",
        "output_root": str(output_root),
        "shard_root_read_only": str(shard_root),
        "requested_epochs": epochs,
        "resume_verification_epochs": 1,
        "train_seed": train_seed,
        "train_seed_context": "REHEARSAL_NONFORMAL",
        "arm_order": list(ARMS),
        "route_order": list(ROUTE_ORDER),
        "source_ablation_map": {
            arm: dict(SOURCE_ABLATION_MAP[arm]) for arm in ARMS
        },
        "complete_marker_written": False,
    }


def run_rehearsal(
    *,
    shard_root: str | Path,
    output_root: str | Path,
    model_config_path: str | Path = DEFAULT_MODEL_CONFIG,
    epochs: int = 3,
    train_seed: int = DEFAULT_TRAIN_SEED,
) -> dict[str, Any]:
    if isinstance(epochs, bool) or not isinstance(epochs, int) or epochs < 1:
        raise RehearsalTrainingError("epochs must be a positive integer")
    if isinstance(train_seed, bool) or not isinstance(train_seed, int):
        raise RehearsalTrainingError("train seed must be an integer")
    root = _validate_output_root(output_root)
    shards = Path(shard_root)
    if any(part.upper() == "TEST" for part in shards.parts):
        raise RehearsalTrainingError("TEST shard roots are forbidden")
    model_path = Path(model_config_path)
    receipt = _base_receipt(
        output_root=root,
        shard_root=shards,
        epochs=epochs,
        train_seed=train_seed,
    )
    root.mkdir()
    update_timings: list[dict[str, Any]] = []
    epoch_timings: list[dict[str, Any]] = []
    finite_checks: list[dict[str, Any]] = []
    phase_timings: dict[str, float] = {}

    try:
        model_config = _load_model_config(model_path)
        load_started = time.perf_counter()
        provider = RehearsalRealShardProvider(
            shards, planned_epoch_budget=epochs + 1
        )
        phase_timings["shard_load_seconds"] = time.perf_counter() - load_started

        orchestrator_config = V023TwoRouteOrchestratorConfig(
            model_config=model_config,
            train_seed=train_seed,
            lineage="v023-c1c2-REHEARSAL-NONFORMAL",
            checkpoint_cadence_updates=2,
            formal_use=False,
        )
        orchestrator = V023TwoRouteLearnerOrchestrator(
            orchestrator_config, provider
        )

        training_started = time.perf_counter()
        for epoch in range(1, epochs + 1):
            _advance_epoch(
                orchestrator,
                phase="initial_rehearsal_training",
                epoch_number=epoch,
                update_timings=update_timings,
                epoch_timings=epoch_timings,
                loss_checks=finite_checks,
            )
        phase_timings["initial_training_seconds"] = (
            time.perf_counter() - training_started
        )

        checkpoint = orchestrator.checkpoint_state()
        export_started = time.perf_counter()
        export_dir = root / f"REHEARSAL-EXPORT-EPOCH-{epochs:04d}"
        export_dir.mkdir()
        exports: list[dict[str, Any]] = []
        counts = orchestrator.route_update_counts
        for arm in ARMS:
            path = export_dir / f"{arm}.REHEARSAL-NONFORMAL.pt"
            state = orchestrator.models[arm].checkpoint_state(
                update_count=orchestrator.update_cursor,
                route_update_counts=counts,
            )
            exports.append(
                {
                    "arm": arm,
                    "path": str(path.relative_to(root)),
                    "sha256": _torch_write(path, state),
                }
            )
        checkpoint_path = root / "REHEARSAL-NONFORMAL-CHECKPOINT.pt"
        checkpoint_sha256 = _torch_write(checkpoint_path, checkpoint)
        phase_timings["export_seconds"] = time.perf_counter() - export_started

        _advance_epoch(
            orchestrator,
            phase="uninterrupted_continuation_reference",
            epoch_number=epochs + 1,
            update_timings=update_timings,
            epoch_timings=epoch_timings,
            loss_checks=finite_checks,
        )
        expected_continuation = orchestrator.checkpoint_state()

        reload_started = time.perf_counter()
        loaded_checkpoint = torch.load(
            checkpoint_path, map_location="cpu", weights_only=False
        )
        reloaded_provider = RehearsalRealShardProvider(
            shards, planned_epoch_budget=epochs + 1
        )
        reloaded = V023TwoRouteLearnerOrchestrator(
            orchestrator_config, reloaded_provider
        )
        reloaded.load_checkpoint_state(loaded_checkpoint)
        phase_timings["reload_seconds"] = time.perf_counter() - reload_started

        resume_started = time.perf_counter()
        _advance_epoch(
            reloaded,
            phase="reloaded_resume_verification",
            epoch_number=epochs + 1,
            update_timings=update_timings,
            epoch_timings=epoch_timings,
            loss_checks=finite_checks,
        )
        phase_timings["resumed_epoch_seconds"] = time.perf_counter() - resume_started
        actual_continuation = reloaded.checkpoint_state()
        exact_continuation = _tree_exact(
            expected_continuation, actual_continuation
        )
        if not exact_continuation:
            raise RehearsalTrainingError(
                "reloaded one-epoch continuation was not bitwise exact"
            )
        resumed_path = root / "REHEARSAL-NONFORMAL-RESUMED-ONE-EPOCH.pt"
        resumed_sha256 = _torch_write(resumed_path, actual_continuation)
        provider_identity_payload = provider.provider_identity_payload

        receipt.update(
            {
                "status": "REHEARSAL_PASS",
                "provider_identity": provider.provider_identity,
                "provider_identity_payload": provider_identity_payload,
                "shard_catalogue": provider_identity_payload[
                    "shard_digests_used"
                ],
                "planned_epoch_budget": provider.planned_epoch_budget,
                "model_config_path": str(model_path.resolve()),
                "model_config_sha256": _file_sha256(model_path),
                "completed_initial_epochs": epochs,
                "completed_initial_updates": epochs * len(ROUTE_ORDER),
                "exact_continuation_verified": True,
                "exact_continuation_mode": "BITWISE_TREE_EQUAL_AFTER_ONE_EPOCH",
                "exports": exports,
                "orchestrator_checkpoint": {
                    "path": checkpoint_path.name,
                    "sha256": checkpoint_sha256,
                },
                "resumed_checkpoint": {
                    "path": resumed_path.name,
                    "sha256": resumed_sha256,
                },
                "timings": {
                    "phases": phase_timings,
                    "per_update": update_timings,
                    "per_epoch": epoch_timings,
                },
                "finite_loss_checks": {
                    "all_finite": all(item["finite"] for item in finite_checks),
                    "count": len(finite_checks),
                    "checks": finite_checks,
                },
                "orchestrator_config": asdict(orchestrator_config),
            }
        )
    except Exception as cause:
        receipt.update(
            {
                "error_type": type(cause).__name__,
                "error": str(cause),
                "exact_continuation_verified": False,
                "timings": {
                    "phases": phase_timings,
                    "per_update": update_timings,
                    "per_epoch": epoch_timings,
                },
                "finite_loss_checks": {
                    "all_finite": all(item["finite"] for item in finite_checks),
                    "count": len(finite_checks),
                    "checks": finite_checks,
                },
            }
        )
        _json_write(root / "REHEARSAL-RECEIPT.json", receipt)
        raise

    _json_write(root / "REHEARSAL-RECEIPT.json", receipt)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard-root", type=Path, default=DEFAULT_SHARD_ROOT)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, default=DEFAULT_MODEL_CONFIG)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--train-seed", type=int, default=DEFAULT_TRAIN_SEED)
    return parser


def _final_timing_line(status: str, timings: Mapping[str, Any]) -> str:
    phases = timings.get("phases", {}) if isinstance(timings, Mapping) else {}
    summary = {
        "status": status,
        "formal": False,
        "claim_ceiling": CLAIM_CEILING,
        "phase_timings_seconds": phases,
    }
    return f"REHEARSAL_TWO_ROUTE_{status} " + json.dumps(
        summary, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        receipt = run_rehearsal(
            shard_root=arguments.shard_root,
            output_root=arguments.output_root,
            model_config_path=arguments.model_config,
            epochs=arguments.epochs,
            train_seed=arguments.train_seed,
        )
    except Exception as cause:
        timings: Mapping[str, Any] = {}
        receipt_path = Path(arguments.output_root) / "REHEARSAL-RECEIPT.json"
        if receipt_path.is_file():
            try:
                failed = json.loads(receipt_path.read_text(encoding="ascii"))
                timings = failed.get("timings", {})
            except (OSError, UnicodeError, json.JSONDecodeError):
                timings = {}
        print(
            f"NONFORMAL_REHEARSAL_ERROR {type(cause).__name__}: {cause}",
            file=sys.stderr,
        )
        print(_final_timing_line("FAIL", timings))
        return 2
    print(_final_timing_line("PASS", receipt["timings"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CLAIM_CEILING",
    "DEFAULT_TRAIN_SEED",
    "REQUIRED_OUTPUT_TOKEN",
    "RehearsalTrainingError",
    "build_parser",
    "main",
    "run_rehearsal",
]
