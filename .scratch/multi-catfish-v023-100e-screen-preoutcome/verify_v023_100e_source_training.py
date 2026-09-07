#!/usr/bin/env python3
"""Rebuild and seal one completed V0.23 100-epoch source-training run.

The runner is the sole writer of learner state.  This module is a read-only
auditor until all frozen inputs, the current provider, the current runner,
the epoch-100 checkpoint, and the five current-model exports have been
authenticated.  It then publishes ``verification.json``, a complete
write-once ``MANIFEST.sha256``, and a ``COMPLETE`` marker.  Any failed seal
attempt publishes a terminal ``FAILED`` marker when a real output root is
available.

No simulator, physical episode, TEST split, or unsealed prerequisite result
is opened here.  The post-R7 provider factory performs the prerequisite
authentication and is rebuilt for the exact same runner configuration used
by the source-training controller.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
from types import ModuleType
from typing import Any


SCHEMA = "multi-catfish-mcrl-v023-100e-source-training-final-verification-v1"
FAILURE_SCHEMA = f"{SCHEMA}-failure"
STATUS = "PASS_SOURCE_TRAINING_INTEGRITY"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_TO_LEARNER_AND_ONE_WORLD_PLUMBING_ONLY_NO_TEST_NO_EFFICACY"
)
PREFLIGHT_CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_TO_LEARNER_ONLY_NO_SIMULATOR_NO_EPISODE_NO_TEST_NO_EFFICACY"
)
PREFLIGHT_SCHEMA = "multi-catfish-mcrl-v023-100e-source-training-preflight-v1"
PREFLIGHT_STATUS = "PASS_FROZEN_PREOUTCOME_100E_PREFLIGHT"
SOURCE_RUNNER_CLAIM_CEILING = (
    "IMPLEMENTATION_ONLY_SOURCE_TRAINING_NO_SIMULATOR_NO_EPISODE_NO_TEST_NO_EFFICACY"
)
SOURCE_SPLIT = "SOURCE_TRAIN"
EXPECTED_EPOCHS = 100
EXPECTED_ROUTE_UPDATES = 300
EXPECTED_TRAIN_SEED = 2927175120652069826
EXPECTED_SCHEDULE_SEED = 1113171504590631764
EXPECTED_CONTRACT_SHA256 = (
    "7f417ca66d935ba3748dc7204a0ee241ad70ff491ed6cdae69a92e7f71ae20b6"
)
EXPECTED_MODEL_CONFIG_SHA256 = (
    "2fab1e4a0b61bf88a428709815d078d9b613b06b645c4d9cef7e46b2220b78ec"
)
EXPECTED_PROVIDER_CONFIG_SHA256 = (
    "939582ffb8537eef865c1a71d8c324ad475059a0d96dd29e36da39ea18ee9f7b"
)
EXPECTED_OUTPUT_ROOT = Path(
    "/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r1"
)
EXPECTED_PROVIDER_CONFIG = {
    "epoch_budget": 100,
    "r7_root": "/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1",
    "schedule_seed": EXPECTED_SCHEDULE_SEED,
    "schema": "multi-catfish-mcrl-v023-post-r7-provider-factory-config-v1",
    "target_root": "/home/sat/mcrl-v023-c1c2-targets-20260906-d40-r4",
}
PROVIDER_FACTORY_MODULE = "v023_post_r7_provider_factory"
PROVIDER_FACTORY_CALLABLE = "make_provider"
PROVIDER_CONFIG_ENV = "MCRL_V023_POST_R7_PROVIDER_CONFIG_PATH"
PROVIDER_CONFIG_SHA_ENV = "MCRL_V023_POST_R7_PROVIDER_CONFIG_SHA256"
PREFLIGHT_INPUT_SCHEMA = "multi-catfish-mcrl-v023-100e-source-training-preflight-v1-input-binding"
PACKAGE_RELATIVE = Path(".scratch/multi-catfish-v023-100e-screen-preoutcome")
RUNNER_RELATIVE = Path(
    ".scratch/multi-catfish-v023-five-arm-training-runner"
)
FACTORY_RELATIVE = Path(
    ".scratch/multi-catfish-v023-post-r7-provider-factory"
)
ARMS = (
    "ALL_NEUTRAL_CONTROL",
    "FULL",
    "DROP_C1",
    "DROP_C2",
    "DROP_C3",
)
ROUTES = ("C1", "C2", "C3")
SOURCE_MAP = {
    "ALL_NEUTRAL_CONTROL": {"C1": "neutral", "C2": "neutral", "C3": "neutral"},
    "FULL": {"C1": "informed", "C2": "informed", "C3": "informed"},
    "DROP_C1": {"C1": "neutral", "C2": "informed", "C3": "informed"},
    "DROP_C2": {"C1": "informed", "C2": "neutral", "C3": "informed"},
    "DROP_C3": {"C1": "informed", "C2": "informed", "C3": "neutral"},
}
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SAFE_RELATIVE = re.compile(r"^[A-Za-z0-9._/-]+$")


class V023SourceTrainingSealError(RuntimeError):
    """The frozen source-training result boundary failed closed."""


def _fail(message: str, *, cause: BaseException | None = None) -> None:
    if cause is None:
        raise V023SourceTrainingSealError(message)
    raise V023SourceTrainingSealError(message) from cause


def _digest(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        _fail(f"{field} must be a lowercase SHA-256")
    return value


def _regular_file(path: Path, *, field: str) -> None:
    if path.is_symlink() or not path.is_file():
        _fail(f"{field} must be a regular non-symlink file: {path}")


def _regular_dir(path: Path, *, field: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        _fail(f"{field} must be a regular non-symlink directory: {path}")
    return path.resolve()


def _sha256_file(path: Path, *, field: str = "file") -> str:
    _regular_file(path, field=field)
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        _fail(f"cannot read {field}: {path}", cause=error)
    return digest.hexdigest()


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii") + b"\n"
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        _fail("value is not finite canonical ASCII JSON", cause=error)


def _read_canonical_json(path: Path, *, field: str) -> dict[str, Any]:
    _regular_file(path, field=field)
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        _fail(f"{field} is not readable canonical JSON", cause=error)
    if not isinstance(value, dict):
        _fail(f"{field} root must be an object")
    canonical = _canonical_bytes(value)
    # Runner JSON is canonical without a newline; the preflight and this
    # sealer use one trailing newline.  Accept exactly either representation.
    if raw not in (canonical, canonical.rstrip(b"\n")):
        _fail(f"{field} is not canonical JSON")
    return value


def _write_once(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        _fail(f"refusing to overwrite artifact: {path}")
    if not path.parent.is_dir() or path.parent.is_symlink():
        _fail(f"artifact parent is unavailable: {path.parent}")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        _fail(f"cannot publish write-once artifact: {path}", cause=error)
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
    return hashlib.sha256(payload).hexdigest()


def _safe_relative(root: Path, relative: str, *, field: str) -> Path:
    if (
        not isinstance(relative, str)
        or not relative
        or Path(relative).is_absolute()
        or "\\" in relative
        or ".." in Path(relative).parts
        or not _SAFE_RELATIVE.fullmatch(relative)
    ):
        _fail(f"{field} is not a safe relative path")
    candidate = root / relative
    _regular_file(candidate, field=field)
    if not candidate.resolve().is_relative_to(root.resolve()):
        _fail(f"{field} escapes its root")
    return candidate


def verify_launch_manifest(repo: Path, manifest: Path, expected_sha256: str) -> str:
    """Authenticate the launch-manifest file and every source entry."""

    root = _regular_dir(repo, field="repository root")
    _regular_file(manifest, field="100E launch manifest")
    actual_manifest_sha = _sha256_file(manifest, field="100E launch manifest")
    if actual_manifest_sha != _digest(expected_sha256, field="launch manifest sha256"):
        _fail("100E launch manifest digest disagrees")
    try:
        lines = manifest.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as error:
        _fail("100E launch manifest is unreadable", cause=error)
    if not lines:
        _fail("100E launch manifest is empty")
    seen: set[str] = set()
    for line in lines:
        parts = line.split("  ")
        if len(parts) != 2:
            _fail("100E launch manifest line is malformed")
        declared, relative = parts
        _digest(declared, field=f"launch manifest entry {relative}")
        if relative in seen:
            _fail(f"100E launch manifest repeats {relative}")
        seen.add(relative)
        target = _safe_relative(root, relative, field=f"launch manifest entry {relative}")
        if _sha256_file(target, field=f"launch manifest entry {relative}") != declared:
            _fail(f"100E launch manifest entry drifted: {relative}")
    required = {
        str(PACKAGE_RELATIVE / "V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md"),
        str(PACKAGE_RELATIVE / "V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.sha256"),
        str(PACKAGE_RELATIVE / "V023-100E-MODEL-CONFIG.json"),
        str(PACKAGE_RELATIVE / "V023-100E-MODEL-CONFIG.sha256"),
        str(PACKAGE_RELATIVE / "V023-100E-POST-R7-PROVIDER-CONFIG.json"),
        str(PACKAGE_RELATIVE / "V023-100E-POST-R7-PROVIDER-CONFIG.sha256"),
        str(PACKAGE_RELATIVE / "preflight_v023_100e_source_training.py"),
        str(PACKAGE_RELATIVE / "verify_v023_100e_source_training.py"),
        str(PACKAGE_RELATIVE / "sync_launch_v023_100e_source_training_server.sh"),
        str(PACKAGE_RELATIVE / "test_v023_100e_source_training_server.py"),
        str(RUNNER_RELATIVE / "v023_five_arm_source_training_runner.py"),
        str(FACTORY_RELATIVE / "v023_post_r7_provider_factory.py"),
    }
    missing = sorted(required - seen)
    if missing:
        _fail(f"100E launch manifest omits required binding(s): {', '.join(missing)}")
    return actual_manifest_sha


def _verify_digest_sidecar(path: Path, *, field: str) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    _regular_file(sidecar, field=f"{field} digest sidecar")
    try:
        content = sidecar.read_text(encoding="ascii")
    except (OSError, UnicodeError) as error:
        _fail(f"{field} digest sidecar is unreadable", cause=error)
    if not content.endswith("\n"):
        _fail(f"{field} digest sidecar is malformed")
    declared = content[:-1]
    _digest(declared, field=f"{field} digest sidecar")
    actual = _sha256_file(path, field=field)
    if actual != declared:
        _fail(f"{field} digest sidecar disagrees")
    return actual


def _frozen_sidecar(path: Path) -> Path:
    """Return the frozen package's existing basename-only digest sidecar."""

    return path.with_suffix(".sha256")


def _verify_named_digest_sidecar(path: Path, *, field: str) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    _regular_file(sidecar, field=f"{field} digest sidecar")
    actual = _sha256_file(path, field=field)
    try:
        content = sidecar.read_text(encoding="ascii")
    except (OSError, UnicodeError) as error:
        _fail(f"{field} digest sidecar is unreadable", cause=error)
    if content != f"{actual}  {path.name}\n":
        _fail(f"{field} digest sidecar disagrees")
    return actual


def _verify_frozen_file(path: Path, expected: str, *, field: str) -> str:
    actual = _sha256_file(path, field=field)
    if actual != _digest(expected, field=f"{field} expected sha256"):
        _fail(f"{field} digest drifted")
    return actual


def _verify_frozen_inputs(
    *,
    repo: Path,
    manifest: Path,
    manifest_sha256: str,
    provider_config: Path,
    model_config: Path,
    contract: Path,
) -> dict[str, Any]:
    launch_sha = verify_launch_manifest(repo, manifest, manifest_sha256)
    contract_sha = _verify_frozen_file(
        contract, EXPECTED_CONTRACT_SHA256, field="100E contract"
    )
    model_sha = _verify_frozen_file(
        model_config, EXPECTED_MODEL_CONFIG_SHA256, field="100E model config"
    )
    provider_sha = _verify_frozen_file(
        provider_config, EXPECTED_PROVIDER_CONFIG_SHA256, field="100E provider config"
    )

    contract_sidecar = _frozen_sidecar(contract)
    _regular_file(contract_sidecar, field="100E contract digest sidecar")
    if contract_sidecar.read_text(encoding="ascii") != (
        f"{contract_sha}  {contract.name}\n"
    ):
        _fail("100E contract digest sidecar disagrees")
    model_sidecar = _frozen_sidecar(model_config)
    _regular_file(model_sidecar, field="100E model-config digest sidecar")
    if model_sidecar.read_text(encoding="ascii") != f"{model_sha}  {model_config.name}\n":
        _fail("100E model-config digest sidecar disagrees")
    provider_sidecar = _frozen_sidecar(provider_config)
    _regular_file(provider_sidecar, field="100E provider-config digest sidecar")
    if provider_sidecar.read_text(encoding="ascii") != (
        f"{provider_sha}  {provider_config.name}\n"
    ):
        _fail("100E provider-config digest sidecar disagrees")

    provider_payload = _read_canonical_json(
        provider_config, field="100E post-R7 provider config"
    )
    if provider_payload != EXPECTED_PROVIDER_CONFIG:
        _fail("100E post-R7 provider config drifted from the frozen contract")
    if not provider_config.is_absolute():
        _fail("100E provider config path must be absolute")
    return {
        "authority_sha256": contract_sha,
        "code_sha256": launch_sha,
        "model_config_sha256": model_sha,
        "provider_config_sha256": provider_sha,
        "provider_config": provider_payload,
    }


def _verify_preflight_receipt(
    path: Path,
    *,
    expected_binding: Mapping[str, Any],
    authority_sha256: str,
    code_sha256: str,
    input_sha256: str,
) -> dict[str, str]:
    receipt = _read_canonical_json(path, field="100E preflight receipt")
    expected = {
        "schema": PREFLIGHT_SCHEMA,
        "status": PREFLIGHT_STATUS,
        "claim_ceiling": PREFLIGHT_CLAIM_CEILING,
        "epoch_budget": EXPECTED_EPOCHS,
        "route_updates": EXPECTED_ROUTE_UPDATES,
        "checkpoint_epochs": [EXPECTED_EPOCHS],
        "train_seed": EXPECTED_TRAIN_SEED,
        "schedule_seed": EXPECTED_SCHEDULE_SEED,
        "source_split": SOURCE_SPLIT,
        "test_split_opened": False,
        "simulator_episode_opened": False,
        "authority_sha256": authority_sha256,
        "code_sha256": code_sha256,
        "input_sha256": input_sha256,
        "input_binding": dict(expected_binding),
        "output_root": str(EXPECTED_OUTPUT_ROOT),
    }
    if receipt != expected:
        _fail("100E preflight receipt disagrees with the rebuilt frozen inputs")
    receipt_sha = _verify_named_digest_sidecar(path, field="100E preflight receipt")
    return {"path": str(path), "sha256": receipt_sha}


def _load_module(name: str, path: Path, *, repo: Path | None = None) -> ModuleType:
    _regular_file(path, field=f"required module {path.name}")
    if repo is not None:
        src = repo / "src"
        factory_dir = repo / FACTORY_RELATIVE
        for candidate in (src, factory_dir, repo):
            if candidate.is_dir() and not candidate.is_symlink():
                text = str(candidate.resolve())
                if text not in sys.path:
                    sys.path.insert(0, text)
    spec = importlib.util.spec_from_file_location(name, path.resolve())
    if spec is None or spec.loader is None:
        _fail(f"cannot import required module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        _fail(f"required module import failed: {path}", cause=error)
    return module


def _factory_module(repo: Path) -> ModuleType:
    src = (repo / "src").resolve()
    factory_dir = (repo / FACTORY_RELATIVE).resolve()
    for candidate in (src, repo.resolve(), factory_dir):
        if candidate.is_dir() and not candidate.is_symlink() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
    if str(factory_dir) not in sys.path:
        sys.path.insert(0, str(factory_dir))
    existing = sys.modules.get(PROVIDER_FACTORY_MODULE)
    if existing is not None:
        existing_path = getattr(existing, "__file__", None)
        if not isinstance(existing_path, str) or Path(existing_path).resolve() != (
            factory_dir / "v023_post_r7_provider_factory.py"
        ).resolve():
            _fail("provider factory module was already imported from another path")
        return existing
    try:
        module = importlib.import_module(PROVIDER_FACTORY_MODULE)
    except Exception as error:
        _fail("post-R7 provider factory import failed", cause=error)
    return module


def _build_runner(
    *,
    repo: Path,
    provider_config: Path,
    model_config: Path,
    authority_sha256: str,
    code_sha256: str,
    input_sha256: str,
    provider_config_sha256: str,
) -> tuple[Any, ModuleType, Mapping[str, Any]]:
    """Reconstruct the exact provider and formal runner without advancing it."""

    factory = _factory_module(repo)
    make_provider = getattr(factory, PROVIDER_FACTORY_CALLABLE, None)
    if not callable(make_provider):
        _fail("post-R7 provider factory callable is unavailable")
    old_path = os.environ.get(PROVIDER_CONFIG_ENV)
    old_sha = os.environ.get(PROVIDER_CONFIG_SHA_ENV)
    os.environ[PROVIDER_CONFIG_ENV] = str(provider_config.resolve())
    os.environ[PROVIDER_CONFIG_SHA_ENV] = provider_config_sha256
    try:
        provider = make_provider()
    except Exception as error:
        _fail("post-R7 provider reconstruction failed", cause=error)
    finally:
        if old_path is None:
            os.environ.pop(PROVIDER_CONFIG_ENV, None)
        else:
            os.environ[PROVIDER_CONFIG_ENV] = old_path
        if old_sha is None:
            os.environ.pop(PROVIDER_CONFIG_SHA_ENV, None)
        else:
            os.environ[PROVIDER_CONFIG_SHA_ENV] = old_sha

    runner_path = repo / RUNNER_RELATIVE / "v023_five_arm_source_training_runner.py"
    runner = _load_module("v023_five_arm_source_training_runner_for_100e_seal", runner_path, repo=repo)
    mcrl_module = sys.modules.get("mcrl")
    mcrl_path = getattr(mcrl_module, "__file__", None)
    if not isinstance(mcrl_path, str) or not Path(mcrl_path).resolve().is_relative_to(repo.resolve()):
        _fail("rebuilt runner imported mcrl outside the dedicated checkout")
    try:
        model = runner._load_model_config(model_config)
        orchestrator_config = runner.ORCHESTRATOR.V023FiveArmOrchestratorConfig.formal(
            model_config=model,
            train_seed=EXPECTED_TRAIN_SEED,
        )
        config = runner.FrozenSourceTrainingConfig(
            epoch_budget=EXPECTED_EPOCHS,
            orchestrator_config=orchestrator_config,
            provider_factory_spec=(
                f"{PROVIDER_FACTORY_MODULE}:{PROVIDER_FACTORY_CALLABLE}"
            ),
            authority_digests=runner.RunAuthorityDigests(
                authority_sha256=authority_sha256,
                code_sha256=code_sha256,
                input_sha256=input_sha256,
            ),
            source_split=SOURCE_SPLIT,
            later_budget_authority_sha256=None,
        )
        rebuilt = runner.V023FiveArmSourceTrainingRunner(config, provider)
    except Exception as error:
        _fail("formal 100E runner reconstruction failed", cause=error)
    identity = getattr(provider, "provider_identity", None)
    identity = identity() if callable(identity) else identity
    identity_payload = getattr(provider, "provider_identity_payload", None)
    if callable(identity_payload):
        identity_payload = identity_payload()
    if not isinstance(identity, str) or not identity:
        _fail("rebuilt provider identity is incomplete")
    if not isinstance(identity_payload, Mapping):
        _fail("rebuilt provider identity payload is incomplete")
    return rebuilt, runner, {
        "provider_identity": identity,
        "provider_identity_payload": dict(identity_payload),
    }


def _assert_finite(value: object, *, field: str) -> None:
    """Reject NaN/Inf in serialized tensors and scalar training receipts."""

    try:
        import torch
    except ImportError:
        torch = None
    if torch is not None and isinstance(value, torch.Tensor):
        if not bool(torch.isfinite(value).all()):
            _fail(f"{field} contains a non-finite tensor")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _assert_finite(item, field=f"{field}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _assert_finite(item, field=f"{field}[{index}]")
        return
    if isinstance(value, float) and not math.isfinite(value):
        _fail(f"{field} contains a non-finite scalar")


def _verify_consumed_file_order(checkpoint: Mapping[str, Any]) -> None:
    state = checkpoint.get("orchestrator_state")
    if not isinstance(state, Mapping):
        _fail("checkpoint orchestrator state is missing")
    file_order = state.get("file_order")
    if not isinstance(file_order, list) or len(file_order) != EXPECTED_ROUTE_UPDATES:
        _fail("checkpoint does not contain exactly 300 route-update file records")
    for cursor, entry in enumerate(file_order):
        if not isinstance(entry, Mapping) or set(entry) != {
            "update_cursor",
            "route",
            "source_files",
        }:
            _fail(f"checkpoint consumed-file record {cursor} is malformed")
        if entry["update_cursor"] != cursor or entry["route"] != ROUTES[cursor % 3]:
            _fail(f"checkpoint consumed-file route order drifted at update {cursor}")
        source_files = entry["source_files"]
        if not isinstance(source_files, list) or len(source_files) != 2:
            _fail(f"checkpoint consumed-file source order drifted at update {cursor}")
        for source, pair in zip(("neutral", "informed"), source_files, strict=True):
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or pair[0] != source
                or not isinstance(pair[1], str)
                or not pair[1].strip()
            ):
                _fail(f"checkpoint consumed-file identity drifted at update {cursor}")


def _verify_checkpoint_and_receipts(
    *,
    root: Path,
    runner: Any,
    runner_module: ModuleType,
    provider_identity: str,
    expected_authority: Mapping[str, str],
) -> dict[str, Any]:
    checkpoint_dir = root / "checkpoints"
    receipt_dir = root / "checkpoint-receipts"
    export_dir = root / "exports"
    for directory, field in (
        (checkpoint_dir, "checkpoint directory"),
        (receipt_dir, "checkpoint-receipt directory"),
        (export_dir, "export directory"),
    ):
        _regular_dir(directory, field=field)
    checkpoints = sorted(checkpoint_dir.glob("*.runner.pt"))
    if [path.name for path in checkpoints] != ["epoch-0100.runner.pt"]:
        _fail("result must contain exactly the epoch-100 runner checkpoint")
    checkpoint_receipts = sorted(receipt_dir.glob("*.json"))
    if [path.name for path in checkpoint_receipts] != ["epoch-0100.json"]:
        _fail("result must contain exactly the epoch-100 checkpoint receipt")
    export_subdirectories = sorted(path for path in export_dir.iterdir() if path.is_dir())
    if [path.name for path in export_subdirectories] != ["epoch-0100"]:
        _fail("result must contain exactly the epoch-100 export directory")
    checkpoint_path = checkpoints[0]
    checkpoint_sha = _verify_digest_sidecar(
        checkpoint_path, field="epoch-100 runner checkpoint"
    )
    try:
        checkpoint = runner_module._read_torch(checkpoint_path)
        runner._validate_checkpoint(checkpoint)
        runner._validate_export_receipt(root, checkpoint)
        # Exercise the runner's exact restore path as an in-memory
        # reauthentication step.  This verifies the provider sampler cursor,
        # all five model/optimizer states, consumed-file order, and canonical
        # status binding together; it does not advance or write the run.
        runner.resume_from_checkpoint(checkpoint_path)
    except Exception as error:
        if isinstance(error, V023SourceTrainingSealError):
            raise
        _fail("runner checkpoint/export/resume reauthentication failed", cause=error)
    if checkpoint.get("epoch") != EXPECTED_EPOCHS:
        _fail("checkpoint epoch is not 100")
    if checkpoint.get("update_count") != EXPECTED_ROUTE_UPDATES:
        _fail("checkpoint update count is not 300")
    if checkpoint.get("provider_identity") != provider_identity:
        _fail("checkpoint provider identity disagrees with rebuilt provider")
    if checkpoint.get("source_split") != SOURCE_SPLIT:
        _fail("checkpoint crossed the SOURCE_TRAIN boundary")
    if checkpoint.get("claim_ceiling") != SOURCE_RUNNER_CLAIM_CEILING:
        _fail("checkpoint claim ceiling drifted")
    if checkpoint.get("authority_digests") != dict(expected_authority):
        _fail("checkpoint authority digest binding drifted")
    if checkpoint.get("arm_order") != list(ARMS):
        _fail("checkpoint arm order drifted")
    if checkpoint.get("route_order") != list(ROUTES):
        _fail("checkpoint route order drifted")
    if checkpoint.get("source_ablation_map") != SOURCE_MAP:
        _fail("checkpoint source ablation map drifted")
    if checkpoint.get("initialization_sha256") != runner.orchestrator.initialization_sha256:
        _fail("checkpoint initialization digest disagrees with rebuilt runner")
    _verify_consumed_file_order(checkpoint)
    _assert_finite(checkpoint, field="epoch-100 checkpoint")

    export_manifest_path = export_dir / "epoch-0100.json"
    export_manifest = _read_canonical_json(
        export_manifest_path, field="epoch-100 export manifest"
    )
    if export_manifest.get("claim_ceiling") != SOURCE_RUNNER_CLAIM_CEILING:
        _fail("export manifest claim ceiling drifted")
    if export_manifest.get("epoch") != EXPECTED_EPOCHS:
        _fail("export manifest epoch drifted")
    if export_manifest.get("update_count") != EXPECTED_ROUTE_UPDATES:
        _fail("export manifest update count drifted")
    if export_manifest.get("arm_order") != list(ARMS):
        _fail("export manifest arm order drifted")
    if export_manifest.get("source_ablation_map") != SOURCE_MAP:
        _fail("export manifest source map drifted")
    exports = export_manifest.get("exports")
    if not isinstance(exports, list) or len(exports) != len(ARMS):
        _fail("exactly five current-model exports are required")
    export_payloads: list[dict[str, Any]] = []
    for arm, entry in zip(ARMS, exports, strict=True):
        if not isinstance(entry, Mapping):
            _fail(f"export entry for {arm} is malformed")
        if (
            entry.get("arm") != arm
            or entry.get("update_count") != EXPECTED_ROUTE_UPDATES
            or entry.get("source_mapping") != SOURCE_MAP[arm]
            or not isinstance(entry.get("path"), str)
        ):
            _fail(f"export entry for {arm} drifted")
        export_path = root / entry["path"]
        if not export_path.is_relative_to(root):
            _fail(f"export path escapes output root: {entry['path']}")
        export_sha = _verify_digest_sidecar(export_path, field=f"{arm} export")
        if entry.get("sha256") != export_sha:
            _fail(f"export digest disagrees for {arm}")
        try:
            state = runner_module._read_torch(export_path)
        except Exception as error:
            _fail(f"cannot deserialize current-model export for {arm}", cause=error)
        if state.get("algorithm") != runner_module._current_model_algorithm():
            _fail(f"export for {arm} is not the current three-route model")
        if state.get("update_count") != EXPECTED_ROUTE_UPDATES:
            _fail(f"export update count drifted for {arm}")
        _assert_finite(state, field=f"{arm} current-model export")
        export_payloads.append(
            {
                "arm": arm,
                "path": entry["path"],
                "sha256": export_sha,
                "algorithm": state["algorithm"],
                "update_count": EXPECTED_ROUTE_UPDATES,
                "source_mapping": dict(SOURCE_MAP[arm]),
            }
        )
    return {
        "export_manifest": {
            "path": str(export_manifest_path.relative_to(root)),
            "sha256": _sha256_file(export_manifest_path, field="epoch-100 export manifest"),
        },
        "exports": export_payloads,
        "checkpoint": {
            "epoch": EXPECTED_EPOCHS,
            "path": str(checkpoint_path.relative_to(root)),
            "sha256": checkpoint_sha,
            "update_count": EXPECTED_ROUTE_UPDATES,
        },
    }


def _verify_canonical_receipts(
    *,
    root: Path,
    runner: Any,
    provider_identity: str,
    expected_authority: Mapping[str, str],
    initialization_sha256: str,
    checkpoint_info: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    status_path = root / "canonical-status.json"
    receipt_path = root / "canonical-receipt.json"
    status = _read_canonical_json(status_path, field="canonical-status.json")
    receipt = _read_canonical_json(receipt_path, field="canonical-receipt.json")
    expected_status = runner._status_payload()
    if status != expected_status:
        _fail("canonical status does not bind the rebuilt runner")
    if status.get("source_split") != SOURCE_SPLIT:
        _fail("canonical status crossed the SOURCE_TRAIN boundary")
    if status.get("claim_ceiling") != SOURCE_RUNNER_CLAIM_CEILING:
        _fail("canonical status claim ceiling drifted")
    expected_receipt_keys = {
        "schema",
        "claim_ceiling",
        "source_split",
        "epoch_budget",
        "completed_epochs",
        "completed_updates",
        "provider_identity",
        "initialization_sha256",
        "arm_order",
        "route_order",
        "source_ablation_map",
        "config",
        "authority_digests",
        "checkpoints",
    }
    if set(receipt) != expected_receipt_keys:
        _fail("canonical receipt schema drifted")
    if (
        receipt.get("schema") != runner.RECEIPT_SCHEMA
        or receipt.get("claim_ceiling") != SOURCE_RUNNER_CLAIM_CEILING
        or receipt.get("source_split") != SOURCE_SPLIT
        or receipt.get("epoch_budget") != EXPECTED_EPOCHS
        or receipt.get("completed_epochs") != EXPECTED_EPOCHS
        or receipt.get("completed_updates") != EXPECTED_ROUTE_UPDATES
        or receipt.get("provider_identity") != provider_identity
        or receipt.get("initialization_sha256") != initialization_sha256
        or receipt.get("arm_order") != list(ARMS)
        or receipt.get("route_order") != list(ROUTES)
        or receipt.get("source_ablation_map") != SOURCE_MAP
        or receipt.get("config") != runner.config.to_payload()
        or receipt.get("authority_digests") != dict(expected_authority)
    ):
        _fail("canonical receipt identity or boundary drifted")
    checkpoints = receipt.get("checkpoints")
    expected_checkpoint = {
        "epoch": EXPECTED_EPOCHS,
        "path": checkpoint_info["path"],
        "sha256": checkpoint_info["sha256"],
    }
    if checkpoints != [expected_checkpoint]:
        _fail("canonical receipt does not bind exactly the epoch-100 checkpoint")
    _assert_finite(receipt, field="canonical receipt")
    return status, receipt


def _assert_no_test_or_simulator(root: Path, values: Sequence[Mapping[str, Any]]) -> None:
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_symlink():
            _fail(f"result tree contains a symlink: {relative}")
        if path.is_dir():
            if path.name == "TEST" or path.name.lower() in {"simulator", "episodes"}:
                _fail(f"result tree contains a forbidden boundary directory: {relative}")
            continue
        mode = path.stat(follow_symlinks=False).st_mode
        if not stat.S_ISREG(mode):
            _fail(f"result tree contains a special node: {relative}")
        if relative.name == "TEST" or any(part == "TEST" for part in relative.parts):
            _fail(f"result tree contains a TEST artifact: {relative}")
    for payload in values:
        if payload.get("source_split") != SOURCE_SPLIT:
            _fail("sealed receipt crossed the SOURCE_TRAIN boundary")
        for field in ("test_split_opened", "simulator_episode_opened", "episode_training"):
            if field in payload and payload[field] is not False:
                _fail(f"sealed receipt permits {field}")


def _expected_preseal_files() -> set[str]:
    files = {
        "canonical-status.json",
        "canonical-receipt.json",
        "checkpoints/epoch-0100.runner.pt",
        "checkpoints/epoch-0100.runner.pt.sha256",
        "checkpoint-receipts/epoch-0100.json",
        "exports/epoch-0100.json",
    }
    for index, arm in enumerate(ARMS):
        relative = (
            f"exports/epoch-0100/{index:02d}-{arm}."
            "current-ee-axis-lcsrs-three-route.pt"
        )
        files.add(relative)
        files.add(f"{relative}.sha256")
    return files


def _assert_exact_preseal_tree(root: Path) -> None:
    actual: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_symlink():
            _fail(f"preseal result tree contains a symlink: {relative}")
        if path.is_dir():
            continue
        mode = path.stat(follow_symlinks=False).st_mode
        if not stat.S_ISREG(mode):
            _fail(f"preseal result tree contains a special node: {relative}")
        actual.add(relative.as_posix())
    expected = _expected_preseal_files()
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        _fail(
            "preseal result tree differs from its exact source-training allowlist; "
            f"missing={missing}; unexpected={unexpected}"
        )


def _tree_manifest(root: Path) -> bytes:
    entries: list[tuple[str, str]] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_symlink():
            _fail(f"cannot seal a tree containing a symlink: {relative}")
        if path.is_dir():
            continue
        mode = path.stat(follow_symlinks=False).st_mode
        if not stat.S_ISREG(mode):
            _fail(f"cannot seal a tree containing a special node: {relative}")
        if relative.as_posix() in {"MANIFEST.sha256", "COMPLETE", "FAILED"}:
            continue
        entries.append((relative.as_posix(), _sha256_file(path, field=f"tree file {relative}")))
    if not entries:
        _fail("result tree has no files to seal")
    return "".join(f"{digest}  {relative}\n" for relative, digest in sorted(entries)).encode(
        "ascii"
    )


def _write_failed(root: Path, error: BaseException) -> None:
    """Publish one concise terminal failure marker without masking the cause."""

    try:
        if root.is_symlink() or not root.is_dir():
            return
        marker = root / "FAILED"
        if marker.exists() or marker.is_symlink() or (root / "COMPLETE").exists():
            return
        reason = " ".join(str(error).split()) or type(error).__name__
        payload = {
            "schema": FAILURE_SCHEMA,
            "status": "FAILED_SOURCE_TRAINING_INTEGRITY",
            "reason": reason[:1000],
        }
        _write_once(marker, _canonical_bytes(payload))
    except Exception:
        # The original exception is the actionable failure.  A missing or
        # unwritable root must not be turned into a misleading success.
        return


def verify_and_seal(
    *,
    repo: Path,
    output_root: Path,
    launch_manifest: Path,
    launch_manifest_sha256: str,
    provider_config: Path,
    model_config: Path,
    contract: Path,
    authority_sha256: str,
    code_sha256: str,
    input_sha256: str,
    preflight_receipt: Path,
    verify_only: bool = False,
) -> dict[str, Any]:
    """Authenticate the completed runner output and optionally publish seals."""

    root = _regular_dir(output_root, field="100E output root")
    if output_root != EXPECTED_OUTPUT_ROOT or root != EXPECTED_OUTPUT_ROOT:
        _fail("100E output root drifted from the frozen contract")
    if (root / "COMPLETE").exists() or (root / "COMPLETE").is_symlink():
        _fail("100E output is already COMPLETE")
    if (root / "FAILED").exists() or (root / "FAILED").is_symlink():
        _fail("100E output is already terminal FAILED")
    if (root / "MANIFEST.sha256").exists() or (root / "MANIFEST.sha256").is_symlink():
        _fail("100E output already has a whole-tree MANIFEST.sha256")
    # Refuse symlinked/special output members before any checkpoint or JSON is
    # opened; an attacker must not be able to redirect the reauthentication
    # reads outside this write-once root.
    _assert_no_test_or_simulator(root, [])
    _assert_exact_preseal_tree(root)
    _digest(authority_sha256, field="authority sha256")
    _digest(code_sha256, field="code sha256")
    _digest(input_sha256, field="input sha256")
    if authority_sha256 != EXPECTED_CONTRACT_SHA256:
        _fail("authority sha256 is not the frozen 100E contract digest")

    frozen = _verify_frozen_inputs(
        repo=repo,
        manifest=launch_manifest,
        manifest_sha256=launch_manifest_sha256,
        provider_config=provider_config,
        model_config=model_config,
        contract=contract,
    )
    if code_sha256 != frozen["code_sha256"]:
        _fail("declared code sha256 disagrees with the launch manifest")
    expected_authority = {
        "authority_sha256": authority_sha256,
        "code_sha256": code_sha256,
        "input_sha256": input_sha256,
    }
    rebuilt, runner_module, provider_info = _build_runner(
        repo=repo,
        provider_config=provider_config,
        model_config=model_config,
        authority_sha256=authority_sha256,
        code_sha256=code_sha256,
        input_sha256=input_sha256,
        provider_config_sha256=frozen["provider_config_sha256"],
    )
    identity_payload = provider_info["provider_identity_payload"]
    expected_input_binding = {
        "schema": PREFLIGHT_INPUT_SCHEMA,
        "provider_identity": provider_info["provider_identity"],
        "provider_identity_payload": identity_payload,
        "provider_config_sha256": frozen["provider_config_sha256"],
        "model_config_sha256": frozen["model_config_sha256"],
    }
    computed_input_sha = hashlib.sha256(_canonical_bytes(expected_input_binding)).hexdigest()
    if computed_input_sha != input_sha256:
        _fail("input sha256 does not bind the rebuilt provider and model config")
    preflight_info = _verify_preflight_receipt(
        preflight_receipt,
        expected_binding=expected_input_binding,
        authority_sha256=authority_sha256,
        code_sha256=code_sha256,
        input_sha256=input_sha256,
    )
    checkpoint_info = _verify_checkpoint_and_receipts(
        root=root,
        runner=rebuilt,
        runner_module=runner_module,
        provider_identity=provider_info["provider_identity"],
        expected_authority=expected_authority,
    )
    _verify_canonical_receipts(
        root=root,
        runner=rebuilt,
        provider_identity=provider_info["provider_identity"],
        expected_authority=expected_authority,
        initialization_sha256=rebuilt.orchestrator.initialization_sha256,
        checkpoint_info=checkpoint_info["checkpoint"],
    )
    values = [
        _read_canonical_json(root / "canonical-status.json", field="canonical status"),
        _read_canonical_json(root / "canonical-receipt.json", field="canonical receipt"),
        dict(rebuilt.config.to_payload()),
    ]
    _assert_no_test_or_simulator(root, values)
    verification = {
        "schema": SCHEMA,
        "status": STATUS,
        "claim_ceiling": CLAIM_CEILING,
        "preflight_claim_ceiling": PREFLIGHT_CLAIM_CEILING,
        "source_split": SOURCE_SPLIT,
        "epoch_budget": EXPECTED_EPOCHS,
        "completed_epochs": EXPECTED_EPOCHS,
        "completed_updates": EXPECTED_ROUTE_UPDATES,
        "updates_per_source_training_epoch": 3,
        "formal_checkpoint_cadence_epochs": 100,
        "formal_checkpoint_cadence_updates": 300,
        "test_split_opened": False,
        "simulator_episode_opened": False,
        "episode_training": False,
        "scientific_claim": False,
        "provider_factory": f"{PROVIDER_FACTORY_MODULE}:{PROVIDER_FACTORY_CALLABLE}",
        "provider_identity": provider_info["provider_identity"],
        "provider_identity_payload": identity_payload,
        "initialization_sha256": rebuilt.orchestrator.initialization_sha256,
        "arm_order": list(ARMS),
        "route_order": list(ROUTES),
        "source_ablation_map": SOURCE_MAP,
        "authority_digests": expected_authority,
        "contract_sha256": frozen["authority_sha256"],
        "model_config_sha256": frozen["model_config_sha256"],
        "provider_config_sha256": frozen["provider_config_sha256"],
        "launch_manifest_sha256": frozen["code_sha256"],
        "input_binding_sha256": input_sha256,
        "preflight_receipt": preflight_info,
        "checkpoint": checkpoint_info["checkpoint"],
        "export_manifest": checkpoint_info["export_manifest"],
        "exports": checkpoint_info["exports"],
    }
    _assert_finite(verification, field="final verification")
    if not verify_only:
        verification_path = root / "verification.json"
        _write_once(verification_path, _canonical_bytes(verification))
        manifest_path = root / "MANIFEST.sha256"
        manifest_bytes = _tree_manifest(root)
        manifest_sha = _write_once(manifest_path, manifest_bytes)
        if _tree_manifest(root) != manifest_bytes:
            _fail("result tree changed while its whole-tree manifest was being sealed")
        _write_once(root / "COMPLETE", f"{manifest_sha}  MANIFEST.sha256\n".encode("ascii"))
    return verification


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--launch-manifest", required=True, type=Path)
    parser.add_argument("--launch-manifest-sha256", required=True)
    parser.add_argument("--provider-config", required=True, type=Path)
    parser.add_argument("--model-config", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--authority-sha256", required=True)
    parser.add_argument("--code-sha256", required=True)
    parser.add_argument("--input-sha256", required=True)
    parser.add_argument("--preflight-receipt", required=True, type=Path)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="authenticate without publishing verification/manifest/COMPLETE",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        verification = verify_and_seal(
            repo=arguments.repo,
            output_root=arguments.output_root,
            launch_manifest=arguments.launch_manifest,
            launch_manifest_sha256=arguments.launch_manifest_sha256,
            provider_config=arguments.provider_config,
            model_config=arguments.model_config,
            contract=arguments.contract,
            authority_sha256=arguments.authority_sha256,
            code_sha256=arguments.code_sha256,
            input_sha256=arguments.input_sha256,
            preflight_receipt=arguments.preflight_receipt,
            verify_only=arguments.verify_only,
        )
    except Exception as error:
        if not arguments.verify_only:
            _write_failed(arguments.output_root, error)
        print(f"V023_100E_SOURCE_TRAINING_FAILED: {error}", file=sys.stderr)
        return 2
    print(
        f"V023_100E_SOURCE_TRAINING_VERIFIED: epochs={verification['completed_epochs']} "
        f"updates={verification['completed_updates']} status={verification['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "EXPECTED_CONTRACT_SHA256",
    "EXPECTED_EPOCHS",
    "EXPECTED_OUTPUT_ROOT",
    "EXPECTED_PROVIDER_CONFIG_SHA256",
    "EXPECTED_MODEL_CONFIG_SHA256",
    "STATUS",
    "V023SourceTrainingSealError",
    "build_parser",
    "main",
    "verify_and_seal",
    "verify_launch_manifest",
]
