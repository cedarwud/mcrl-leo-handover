#!/usr/bin/env python3
"""Run the mandatory non-formal real-provider C1-to-C2 diagnostic."""

from __future__ import annotations

from collections.abc import Mapping
import argparse
from copy import deepcopy
import importlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any

from successor_launch_common import (
    BUNDLE_REL, FACTORY_REL, LEARNER_MANIFEST_NAME, ROUTE_ORDER, RUNNER_REL,
    TRAIN_SEED, SuccessorLaunchError, canonical_bytes, file_sha256,
    sidecar_path, write_once,
)


SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-one-epoch-diagnostic-v1"
STATUS_PASS = "PASS_ONE_EPOCH_C1C2_SUCCESSOR_DIAGNOSTIC"
STATUS_FAIL = "FAIL_ONE_EPOCH_C1C2_SUCCESSOR_DIAGNOSTIC"
RECEIPT_NAME = "one-epoch-diagnostic.json"
CHECKPOINT_NAME = "one-epoch-full2-checkpoint.pt"


def _load(repo: Path) -> tuple[Any, Any, Any]:
    for path in (repo / "src", repo / FACTORY_REL, repo / RUNNER_REL):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    return (
        importlib.import_module("v023_c1c2_provider_factory_v3"),
        importlib.import_module("v023_two_route_source_training_runner"),
        importlib.import_module("v023_two_route_learner_orchestrator"),
    )


def _identity(provider: object) -> tuple[str, Mapping[str, Any]]:
    identity = getattr(provider, "provider_identity", None)
    payload = getattr(provider, "provider_identity_payload", None)
    if callable(identity):
        identity = identity()
    if callable(payload):
        payload = payload()
    if not isinstance(identity, str) or not identity or not isinstance(payload, Mapping):
        raise SuccessorLaunchError("provider identity is incomplete")
    if payload.get("routes") != ["C1", "C2"]:
        raise SuccessorLaunchError("provider routes are not exactly C1/C2")
    return identity, payload


def _consume_epoch(provider: object, trainer: object, *, start_cursor: int) -> tuple[list[dict[str, Any]], dict[str, object]]:
    rows: list[dict[str, Any]] = []
    delivered: dict[str, object] = {}
    for offset, route in enumerate(ROUTE_ORDER):
        cursor = start_cursor + offset
        batches = {
            source: provider.next_batch(route=route, source=source, update_cursor=cursor)
            for source in ("neutral", "informed")
        }
        selected = batches["informed"]
        update = trainer.update_route(route, selected.batch)
        if not all(
            not isinstance(value, float) or math.isfinite(value)
            for value in update.values()
        ):
            raise SuccessorLaunchError("diagnostic update produced a non-finite metric")
        delivered[route] = selected.batch
        rows.append(
            {
                "update_cursor": cursor,
                "route": route,
                "source": "informed",
                "file_id": selected.file_id,
                "update": dict(update),
            }
        )
    return rows, delivered


def _q2_loss(network: object, config: object, batch: object) -> dict[str, float]:
    import numpy as np
    import torch
    network.eval()
    with torch.no_grad():
        states = torch.tensor(np.asarray(batch.states), dtype=torch.float32)
        masks = torch.tensor(np.asarray(batch.action_masks), dtype=torch.bool)
        reference = torch.tensor(np.asarray(batch.reference_actions), dtype=torch.int64)
        candidate = torch.tensor(np.asarray(batch.candidate_actions), dtype=torch.int64)
        deltas = torch.tensor(np.asarray(batch.normalized_target_deltas), dtype=torch.float32)
        surface = network(states, masks)
        rows = torch.arange(states.shape[0])
        q_reference = surface[rows, reference]
        residual = surface[rows, candidate] - q_reference - deltas
        pair_mse = float(torch.mean(residual.square()))
        gauge_mse = float(torch.mean(q_reference.square()))
        return {
            "pair_mse": pair_mse,
            "gauge_mse": gauge_mse,
            "loss": pair_mse + float(config.beta) * gauge_mse,
        }


def _close(left: object, right: object) -> bool:
    try:
        a, b = float(left), float(right)
    except (TypeError, ValueError):
        return False
    return abs(a - b) <= 1.0e-6 * max(1.0, abs(a))


def _write_receipt(root: Path, payload: dict[str, Any]) -> None:
    path = root / RECEIPT_NAME
    raw = canonical_bytes(payload)
    value = write_once(path, raw)
    write_once(sidecar_path(path), f"{value}  {path.name}\n".encode("ascii"))


def run_diagnostic(
    *, repo: Path, provider_config: Path, model_config: Path,
    output_root: Path, train_seed: int = TRAIN_SEED,
) -> dict[str, Any]:
    if output_root.exists() or output_root.is_symlink():
        raise SuccessorLaunchError("diagnostic scratch root must be absent")
    output_root.mkdir(mode=0o700)
    started = time.perf_counter()
    phase: dict[str, float] = {}
    checks: dict[str, bool] = {}
    payload: dict[str, Any] = {
        "schema": SCHEMA, "status": STATUS_FAIL, "formal": False,
        "claim_ceiling": "NON_FORMAL_C1C2_PROVIDER_DIAGNOSTIC_NO_SCIENTIFIC_CLAIM",
        "train_seed": train_seed, "route_order": list(ROUTE_ORDER),
        "arm": "FULL2", "failed_checks": [], "phase_timings_s": phase,
    }
    try:
        point = time.perf_counter()
        factory, runner, orchestrator = _load(repo)
        provider_sha = file_sha256(provider_config)
        learner_manifest = repo / BUNDLE_REL / LEARNER_MANIFEST_NAME
        os.environ[factory.CONFIG_PATH_ENV] = str(provider_config.resolve())
        os.environ[factory.CONFIG_SHA256_ENV] = provider_sha
        os.environ[factory.LEARNER_MANIFEST_PATH_ENV] = str(learner_manifest.resolve())
        provider_a = factory.make_provider()
        identity, identity_payload = _identity(provider_a)
        config = runner._load_model_config(model_config)
        model_a = orchestrator.EEAxisTwoRouteModel(config, train_seed=train_seed)
        trainer_a = orchestrator.V023TwoRouteTrainer(model_a)
        phase["factory_v3_real_target_load"] = round(time.perf_counter() - point, 6)
        payload["provider_identity"] = identity
        payload["provider_identity_payload"] = dict(identity_payload)
        checks["factory_v3_real_target_loaded"] = True

        point = time.perf_counter()
        q2_before = deepcopy(model_a.q2.state_dict())
        epoch_one, delivered = _consume_epoch(provider_a, trainer_a, start_cursor=0)
        phase["one_c1_to_c2_epoch"] = round(time.perf_counter() - point, 6)
        payload["epoch_one_updates"] = epoch_one
        checks["one_epoch_route_order"] = [row["route"] for row in epoch_one] == list(ROUTE_ORDER)
        checks["one_epoch_losses_finite"] = all(math.isfinite(float(row["update"]["loss"])) for row in epoch_one)

        point = time.perf_counter()
        from mcrl.algorithms.ee_axis_v014_head import V014ActionSetQNetwork
        pre_network = V014ActionSetQNetwork(config.q2)
        pre_network.load_state_dict(q2_before)
        recomputed = _q2_loss(pre_network, config.q2, delivered["C2"])
        reported = epoch_one[1]["update"]
        pre_match = all(_close(recomputed[key], reported.get(key)) for key in ("pair_mse", "gauge_mse", "loss"))
        post_network = V014ActionSetQNetwork(config.q2)
        post_network.load_state_dict(model_a.q2.state_dict())
        mutated = _q2_loss(post_network, config.q2, delivered["C2"])
        mutation_rejected = not all(_close(mutated[key], reported.get(key)) for key in ("pair_mse", "gauge_mse", "loss"))
        checks["c2_loss_uses_pre_update_q2_weights"] = pre_match
        checks["c2_post_update_weight_mutation_is_rejected"] = mutation_rejected
        payload["c2_behavioural_check"] = {
            "reported": {key: reported.get(key) for key in ("pair_mse", "gauge_mse", "loss")},
            "recomputed_pre_update": recomputed,
            "mutation_post_update": mutated,
            "pre_update_match": pre_match,
            "mutation_rejected": mutation_rejected,
        }
        phase["c2_pre_update_behavioural_check"] = round(time.perf_counter() - point, 6)

        point = time.perf_counter()
        checkpoint = {
            "model": model_a.checkpoint_state(update_count=2, route_update_counts={"C1": 1, "C2": 1}),
            "provider_sampler_state": dict(provider_a.sampler_state()),
        }
        import torch
        checkpoint_path = output_root / CHECKPOINT_NAME
        with checkpoint_path.open("xb") as stream:
            torch.save(checkpoint, stream)
            stream.flush()
            os.fsync(stream.fileno())
        checkpoint_sha = file_sha256(checkpoint_path)
        write_once(sidecar_path(checkpoint_path), f"{checkpoint_sha}  {checkpoint_path.name}\n".encode("ascii"))
        loaded = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        provider_b = factory.make_provider()
        identity_b, _ = _identity(provider_b)
        provider_b.load_sampler_state(deepcopy(loaded["provider_sampler_state"]))
        model_b = orchestrator.EEAxisTwoRouteModel(config, train_seed=train_seed)
        model_b.load_checkpoint_state(deepcopy(loaded["model"]))
        trainer_b = orchestrator.V023TwoRouteTrainer(model_b)
        reload_exact = runner._tree_equal(checkpoint["model"], model_b.checkpoint_state(update_count=2, route_update_counts={"C1": 1, "C2": 1}))
        reload_exact &= dict(provider_a.sampler_state()) == dict(provider_b.sampler_state()) and identity_b == identity
        checks["export_reload_exact"] = bool(reload_exact)
        phase["export_and_reload"] = round(time.perf_counter() - point, 6)
        payload["checkpoint"] = {"path": CHECKPOINT_NAME, "sha256": checkpoint_sha}

        point = time.perf_counter()
        continuation_a, _ = _consume_epoch(provider_a, trainer_a, start_cursor=2)
        continuation_b, _ = _consume_epoch(provider_b, trainer_b, start_cursor=2)
        continuation_exact = continuation_a == continuation_b and runner._tree_equal(
            model_a.checkpoint_state(update_count=4, route_update_counts={"C1": 2, "C2": 2}),
            model_b.checkpoint_state(update_count=4, route_update_counts={"C1": 2, "C2": 2}),
        ) and dict(provider_a.sampler_state()) == dict(provider_b.sampler_state())
        checks["exact_continuation_after_reload"] = bool(continuation_exact)
        payload["continuation_updates"] = continuation_b
        phase["exact_continuation"] = round(time.perf_counter() - point, 6)
        payload["checks"] = checks
        payload["failed_checks"] = sorted(key for key, passed in checks.items() if not passed)
        payload["status"] = STATUS_PASS if not payload["failed_checks"] else STATUS_FAIL
    except Exception as error:
        payload["error"] = f"{type(error).__name__}: {error}"
        payload["traceback_tail"] = traceback.format_exc()[-3000:]
        payload["checks"] = checks
        payload["failed_checks"] = sorted(key for key, passed in checks.items() if not passed) or ["diagnostic_exception"]
    phase["total"] = round(time.perf_counter() - started, 6)
    _write_receipt(output_root, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--provider-config", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--train-seed", type=int, default=TRAIN_SEED)
    arguments = parser.parse_args(argv)
    try:
        receipt = run_diagnostic(
            repo=arguments.repo.resolve(), provider_config=arguments.provider_config,
            model_config=arguments.model_config, output_root=arguments.output_root,
            train_seed=arguments.train_seed,
        )
    except Exception as error:
        print(f"DIAGNOSTIC_FAIL error={type(error).__name__}:{error}")
        return 3
    if receipt["status"] == STATUS_PASS:
        print(f"DIAGNOSTIC_PASS receipt={arguments.output_root / RECEIPT_NAME}")
        return 0
    print(f"DIAGNOSTIC_FAIL receipt={arguments.output_root / RECEIPT_NAME} failed_checks={receipt['failed_checks']}")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
