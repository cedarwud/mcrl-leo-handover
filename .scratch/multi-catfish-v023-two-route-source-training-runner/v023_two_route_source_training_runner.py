#!/usr/bin/env python3
"""Write-once C1/C2 successor source-training lifecycle."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import argparse
import importlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
from typing import Any

import torch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from ee_axis_two_route_model import (
    EEAxisTwoRouteConfig,
    EEAxisTwoRouteModel,
    FORMAL_TRAIN_SEED,
    FROZEN_MODEL_CONFIG_SHA256,
    FROZEN_Q1_CONFIG,
    FROZEN_Q2_CONFIG,
    TWO_ROUTE_ALGORITHM,
    TWO_ROUTE_CHECKPOINT_SCHEMA,
)
from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_v014_head import EEAxisV014HeadConfig
from v023_two_route_learner_orchestrator import (
    ARMS,
    ROUTE_ORDER as ROUTES,
    SOURCE_ABLATION_MAP as ORCHESTRATOR_SOURCE_MAP,
    DeterministicRouteBatchProvider,
    V023TwoRouteLearnerOrchestrator,
    V023TwoRouteOrchestratorConfig,
    V023TwoRouteOrchestratorError,
    authenticate_factory_v3_provider_identity,
    validate_two_route_provider_identity,
)


RUNNER_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-two-route-source-training-runner-v1"
STATUS_SCHEMA = f"{RUNNER_SCHEMA}-canonical-status"
RECEIPT_SCHEMA = f"{RUNNER_SCHEMA}-canonical-receipt"
CHECKPOINT_SCHEMA = f"{RUNNER_SCHEMA}-checkpoint"
CHECKPOINT_RECEIPT_SCHEMA = f"{RUNNER_SCHEMA}-checkpoint-receipt"
EXPORT_MANIFEST_SCHEMA = f"{RUNNER_SCHEMA}-three-model-exports"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_C1C2_SUCCESSOR_SOURCE_TRAINING_NO_C3_NO_TEST_NO_EFFICACY"
)
SOURCE_SPLIT = "SOURCE_TRAIN"
SUPPORTED_EPOCH_BUDGETS = (100,)
FORMAL_CHECKPOINT_EPOCHS = (0, 100)
UPDATES_PER_EPOCH = 2
FORMAL_CHECKPOINT_UPDATES = 200
FORBIDDEN_ARMS = {"ALL_NEUTRAL_CONTROL", "FULL", "DROP_C3", "BASELINE"}
SOURCE_MAP: Mapping[str, tuple[str, str]] = {
    "FULL2": ("informed", "informed"),
    "DROP_C1": ("neutral", "informed"),
    "DROP_C2": ("informed", "neutral"),
}
PROVIDER_FACTORY_PATH = (
    HERE.parent
    / "multi-catfish-v023-c1c2-provider-factory-v3"
    / "v023_c1c2_provider_factory_v3.py"
)
EPOCH_100_INTEGRITY_DECISION = "PASS_EXACT_EPOCH_100_RESTORE"


def _validate_closed_topology() -> None:
    if ARMS != ("FULL2", "DROP_C1", "DROP_C2") or len(ARMS) != 3:
        raise V023TwoRouteSourceTrainingRunnerError("a forbidden or fourth arm was requested")
    if any(arm in FORBIDDEN_ARMS for arm in ARMS):
        raise V023TwoRouteSourceTrainingRunnerError("a forbidden arm was requested")
    if ROUTES != ("C1", "C2") or "C3" in ROUTES:
        raise V023TwoRouteSourceTrainingRunnerError("C3 or a third route was requested")
    if SOURCE_MAP != {
        "FULL2": ("informed", "informed"),
        "DROP_C1": ("neutral", "informed"),
        "DROP_C2": ("informed", "neutral"),
    }:
        raise V023TwoRouteSourceTrainingRunnerError("closed C1/C2 source map drifted")


class V023TwoRouteSourceTrainingRunnerError(RuntimeError):
    """The frozen two-route runner contract was violated."""


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023TwoRouteSourceTrainingRunnerError("artifact is not canonical finite JSON") from error


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _torch_bytes(value: object) -> bytes:
    stream = BytesIO()
    torch.save(value, stream)
    return stream.getvalue()


def _sha256_digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023TwoRouteSourceTrainingRunnerError(f"{field} must be a lowercase SHA-256")
    return value


def _file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise V023TwoRouteSourceTrainingRunnerError(f"artifact is not a regular file: {path}")
    digest_digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest_digest.update(block)
    return digest_digest.hexdigest()


def _atomic_write_once(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise V023TwoRouteSourceTrainingRunnerError(f"refusing to overwrite artifact: {path}")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise V023TwoRouteSourceTrainingRunnerError(f"artifact parent is unavailable: {path.parent}")
    temporary = path.parent / f".{path.name}.{secrets.token_hex(16)}.tmp"
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise V023TwoRouteSourceTrainingRunnerError(
                f"refusing to overwrite artifact: {path}"
            ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return sha256(payload).hexdigest()


def _atomic_json_once(path: Path, payload: Mapping[str, Any]) -> str:
    return _atomic_write_once(path, _canonical_json_bytes(_jsonable(payload)))


def _write_sidecar(path: Path, digest: str) -> None:
    _atomic_write_once(path.with_suffix(path.suffix + ".sha256"), f"{digest}\n".encode("ascii"))


def _verify_sidecar(path: Path) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if sidecar.is_symlink() or not sidecar.is_file():
        raise V023TwoRouteSourceTrainingRunnerError("checkpoint digest sidecar is missing")
    expected = sidecar.read_text(encoding="ascii")
    if not expected.endswith("\n"):
        raise V023TwoRouteSourceTrainingRunnerError("checkpoint digest sidecar is malformed")
    expected = _sha256_digest(expected[:-1], field="checkpoint digest sidecar")
    if _file_sha256(path) != expected:
        raise V023TwoRouteSourceTrainingRunnerError("checkpoint digest verification failed")
    return expected


def _read_torch(path: Path) -> Mapping[str, Any]:
    try:
        value = torch.load(path, map_location="cpu", weights_only=False)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise V023TwoRouteSourceTrainingRunnerError("cannot deserialize checkpoint") from error
    if not isinstance(value, Mapping):
        raise V023TwoRouteSourceTrainingRunnerError("checkpoint root must be a mapping")
    return value


def _tree_equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, torch.Tensor):
        return torch.equal(left, right)
    if isinstance(left, Mapping):
        return tuple(left) == tuple(right) and all(_tree_equal(left[key], right[key]) for key in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(
            _tree_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _source_map_payload() -> dict[str, dict[str, str]]:
    return {arm: dict(ORCHESTRATOR_SOURCE_MAP[arm]) for arm in ARMS}


def _reject_test(value: object, *, field: str) -> None:
    text = str(value).upper()
    if isinstance(value, Path) or "/" in text or "\\" in text:
        tokens = re.split(r"[/\\]+", text)
    else:
        tokens = re.split(r"[^A-Z0-9]+", text)
    if "TEST" in tokens:
        raise V023TwoRouteSourceTrainingRunnerError(f"TEST in {field} is rejected")


def _provider_identity(provider: object) -> str:
    candidate = getattr(provider, "provider_identity", None)
    identity = candidate() if callable(candidate) else candidate
    if not isinstance(identity, str) or not identity or identity != identity.strip() or len(identity) > 512:
        raise V023TwoRouteSourceTrainingRunnerError("provider must expose provider_identity")
    _reject_test(identity, field="provider identity")
    return identity


def _provider_budget(provider: object) -> int:
    candidate = getattr(provider, "planned_epoch_budget", None)
    budget = candidate() if callable(candidate) else candidate
    if type(budget) is not int or budget != 100:
        raise V023TwoRouteSourceTrainingRunnerError("provider epoch budget must be exactly 100")
    return budget


@dataclass(frozen=True, slots=True)
class RunAuthorityDigests:
    authority_sha256: str
    code_sha256: str
    input_sha256: str

    def __post_init__(self) -> None:
        _sha256_digest(self.authority_sha256, field="authority_sha256")
        _sha256_digest(self.code_sha256, field="code_sha256")
        _sha256_digest(self.input_sha256, field="input_sha256")


@dataclass(frozen=True, slots=True)
class FrozenSourceTrainingConfig:
    epoch_budget: int
    orchestrator_config: V023TwoRouteOrchestratorConfig
    provider_factory_spec: str
    authority_digests: RunAuthorityDigests
    provider_config_sha256: str
    source_split: str = SOURCE_SPLIT

    def __post_init__(self) -> None:
        if self.epoch_budget != 100:
            raise V023TwoRouteSourceTrainingRunnerError(
                "only epoch budget 100 is authorized; budget 500 requires later authority"
            )
        if not isinstance(self.orchestrator_config, V023TwoRouteOrchestratorConfig):
            raise TypeError("orchestrator_config must be V023TwoRouteOrchestratorConfig")
        if not self.orchestrator_config.formal_use or self.orchestrator_config.checkpoint_cadence_updates != 200:
            raise V023TwoRouteSourceTrainingRunnerError("formal cycle must be 100 epochs / 200 updates")
        if self.orchestrator_config.train_seed != FORMAL_TRAIN_SEED:
            raise V023TwoRouteSourceTrainingRunnerError("formal train seed drifted")
        if self.orchestrator_config.model_config_sha256 != FROZEN_MODEL_CONFIG_SHA256:
            raise V023TwoRouteSourceTrainingRunnerError("formal model config digest drifted")
        if not isinstance(self.provider_factory_spec, str) or not self.provider_factory_spec:
            raise V023TwoRouteSourceTrainingRunnerError("provider factory must be explicit")
        _reject_test(self.provider_factory_spec, field="provider factory path")
        if not isinstance(self.authority_digests, RunAuthorityDigests):
            raise TypeError("authority_digests must be RunAuthorityDigests")
        _sha256_digest(self.provider_config_sha256, field="provider_config_sha256")
        if self.source_split != SOURCE_SPLIT:
            raise V023TwoRouteSourceTrainingRunnerError("TEST or non-source split is rejected")

    def to_payload(self) -> dict[str, Any]:
        return {
            "epoch_budget": self.epoch_budget,
            "orchestrator_config": _jsonable(asdict(self.orchestrator_config)),
            "provider_factory_spec": self.provider_factory_spec,
            "authority_digests": asdict(self.authority_digests),
            "provider_config_sha256": self.provider_config_sha256,
            "source_split": self.source_split,
        }


def _checkpoint_path(root: Path, epoch: int) -> Path:
    return root / "checkpoints" / f"epoch-{epoch:04d}.runner.pt"


def _checkpoint_receipt_path(root: Path, epoch: int) -> Path:
    return root / "checkpoint-receipts" / f"epoch-{epoch:04d}.json"


def _export_manifest_path(root: Path, epoch: int) -> Path:
    return root / "exports" / f"epoch-{epoch:04d}.json"


class V023TwoRouteSourceTrainingRunner:
    def __init__(self, config: FrozenSourceTrainingConfig, provider: object) -> None:
        _validate_closed_topology()
        if not isinstance(config, FrozenSourceTrainingConfig):
            raise TypeError("config must be FrozenSourceTrainingConfig")
        if not isinstance(provider, DeterministicRouteBatchProvider):
            raise TypeError("provider does not satisfy DeterministicRouteBatchProvider")
        validate_two_route_provider_identity(provider)
        try:
            payload = authenticate_factory_v3_provider_identity(
                provider,
                expected_train_seed=config.orchestrator_config.train_seed,
                expected_model_config_sha256=(
                    config.orchestrator_config.model_config_sha256
                ),
            )
        except V023TwoRouteOrchestratorError as error:
            raise V023TwoRouteSourceTrainingRunnerError(
                "provider identity failed factory-v3 authentication"
            ) from error
        provider_type = type(provider)
        provider_module = sys.modules.get(provider_type.__module__)
        provider_origin = getattr(provider_module, "__file__", None)
        if (
            provider_type.__name__ != "V023C1C2Provider"
            or provider_type is not getattr(
                provider_module, "V023C1C2Provider", None
            )
            or not isinstance(provider_origin, str)
            or Path(provider_origin).resolve(strict=True)
            != PROVIDER_FACTORY_PATH.resolve(strict=True)
            or _file_sha256(PROVIDER_FACTORY_PATH) != payload["factory_code_sha256"]
        ):
            raise V023TwoRouteSourceTrainingRunnerError(
                "fallback or non-factory-v3 provider is forbidden"
            )
        target_identity = payload.get("arm_independent_target_identity")
        if not isinstance(target_identity, Mapping):
            raise V023TwoRouteSourceTrainingRunnerError("r8 target identity is missing")
        expected_bindings = {
            "authority_sha256": payload.get("contract_sha256"),
            "code_sha256": payload.get("learner_manifest_sha256"),
            "input_sha256": target_identity.get("manifest_sha256"),
        }
        if asdict(config.authority_digests) != expected_bindings:
            raise V023TwoRouteSourceTrainingRunnerError(
                "execution authority/code/r8 input digests are not cross-bound"
            )
        if config.provider_config_sha256 != payload.get("provider_config_sha256"):
            raise V023TwoRouteSourceTrainingRunnerError(
                "provider configuration digest is not cross-bound"
            )
        self.config = config
        self.provider = provider
        self.provider_identity = _provider_identity(provider)
        self.provider_epoch_budget = _provider_budget(provider)
        self.provider_identity_payload = deepcopy(dict(payload))
        self.orchestrator = V023TwoRouteLearnerOrchestrator(config.orchestrator_config, provider)
        self.output_root: Path | None = None

    @property
    def completed_epochs(self) -> int:
        return self.orchestrator.completed_source_training_epochs

    def _status_payload(self) -> dict[str, Any]:
        return {
            "schema": STATUS_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "source_split": SOURCE_SPLIT,
            "config": self.config.to_payload(),
            "provider_identity": self.provider_identity,
            "arm_order": list(ARMS),
            "route_order": list(ROUTES),
            "source_ablation_map": _source_map_payload(),
            "initialization_sha256": self.orchestrator.initialization_sha256,
            "formal_export_epochs": list(FORMAL_CHECKPOINT_EPOCHS),
            "updates_per_epoch": 2,
        }

    def begin_new(self, output_root: str | Path) -> Path:
        if self.output_root is not None:
            raise V023TwoRouteSourceTrainingRunnerError("runner is already started")
        if (
            self.orchestrator.update_cursor != 0
            or self.orchestrator.completed_source_training_epochs != 0
            or self.orchestrator.next_route != "C1"
            or self.orchestrator.route_update_counts != {"C1": 0, "C2": 0}
            or self.orchestrator._file_order
        ):
            raise V023TwoRouteSourceTrainingRunnerError(
                "begin_new requires a fresh epoch-zero orchestrator"
            )
        sampler = self.provider.sampler_state()
        if (
            not isinstance(sampler, Mapping)
            or sampler.get("next_update_cursor") != 0
            or sampler.get("next_source_index") != 0
            or sampler.get("consumed_file_order") != []
            or any(value != 0 for value in sampler.get("cursors", {}).values())
        ):
            raise V023TwoRouteSourceTrainingRunnerError(
                "begin_new requires a fresh epoch-zero provider"
            )
        initial = torch.load(
            BytesIO(self.orchestrator._initialization_bytes),
            map_location="cpu",
            weights_only=False,
        )
        for model in self.orchestrator.models.values():
            observed = model.checkpoint_state(
                update_count=0, route_update_counts={"C1": 0, "C2": 0}
            )
            if not _tree_equal(observed, initial):
                raise V023TwoRouteSourceTrainingRunnerError(
                    "begin_new requires unchanged epoch-zero parameters"
                )
        root = Path(output_root)
        _reject_test(root, field="output path")
        if root.exists() or root.is_symlink():
            raise V023TwoRouteSourceTrainingRunnerError("output root must be absent")
        if root.parent.is_symlink() or not root.parent.is_dir():
            raise V023TwoRouteSourceTrainingRunnerError("output root parent is unavailable")
        root.mkdir(mode=0o700)
        for relative in ("checkpoints", "checkpoint-receipts", "exports"):
            (root / relative).mkdir(mode=0o700)
        self.output_root = root
        _atomic_json_once(root / "canonical-status.json", self._status_payload())
        self._write_checkpoint(0)
        return root

    def _require_root(self) -> Path:
        if self.output_root is None:
            raise V023TwoRouteSourceTrainingRunnerError("begin_new or resume is required")
        return self.output_root

    def _checkpoint_payload(self, epoch: int) -> dict[str, Any]:
        state = self.orchestrator.checkpoint_state()
        if epoch not in FORMAL_CHECKPOINT_EPOCHS or epoch != self.completed_epochs:
            raise V023TwoRouteSourceTrainingRunnerError("checkpoint epoch is not authorized")
        updates = epoch * 2
        if self.orchestrator.update_cursor != updates or self.orchestrator.next_route != "C1":
            raise V023TwoRouteSourceTrainingRunnerError("checkpoint contains a partial epoch")
        return {
            "schema": CHECKPOINT_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "source_split": SOURCE_SPLIT,
            "epoch": epoch,
            "update_count": updates,
            "config": self.config.to_payload(),
            "authority_digests": asdict(self.config.authority_digests),
            "provider_identity": self.provider_identity,
            "arm_order": list(ARMS),
            "route_order": list(ROUTES),
            "source_ablation_map": _source_map_payload(),
            "initialization_sha256": self.orchestrator.initialization_sha256,
            "runner_schema": RUNNER_SCHEMA,
            "updates_per_source_training_epoch": UPDATES_PER_EPOCH,
            "formal_checkpoint_cadence_updates": FORMAL_CHECKPOINT_UPDATES,
            "models_and_optimizers": deepcopy(state["arms"]),
            "provider_sampler_state": deepcopy(state["provider_sampler_state"]),
            "consumed_file_order": deepcopy(state["file_order"]),
            "orchestrator_state": state,
        }

    def _write_exports(self, root: Path, epoch: int) -> tuple[list[dict[str, Any]], str]:
        directory = root / "exports" / f"epoch-{epoch:04d}"
        if directory.exists() or directory.is_symlink():
            raise V023TwoRouteSourceTrainingRunnerError("export directory already exists")
        directory.mkdir(mode=0o700)
        entries = []
        counts = self.orchestrator.route_update_counts
        for index, arm in enumerate(ARMS):
            state = self.orchestrator.models[arm].checkpoint_state(
                update_count=self.orchestrator.update_cursor,
                route_update_counts=counts,
            )
            filename = f"{index:02d}-{arm}.current-ee-axis-two-route.pt"
            path = directory / filename
            digest = _atomic_write_once(path, _torch_bytes(state))
            _write_sidecar(path, digest)
            entries.append(
                {
                    "arm": arm,
                    "path": str(path.relative_to(root)),
                    "sha256": digest,
                    "schema": TWO_ROUTE_CHECKPOINT_SCHEMA,
                    "algorithm": TWO_ROUTE_ALGORITHM,
                    "source_mapping": list(SOURCE_MAP[arm]),
                    "update_count": self.orchestrator.update_cursor,
                }
            )
        manifest = {
            "schema": EXPORT_MANIFEST_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "epoch": epoch,
            "update_count": self.orchestrator.update_cursor,
            "arm_order": list(ARMS),
            "route_order": list(ROUTES),
            "source_ablation_map": _source_map_payload(),
            "exports": entries,
        }
        return entries, _atomic_json_once(_export_manifest_path(root, epoch), manifest)

    def _write_checkpoint(self, epoch: int) -> dict[str, Any]:
        root = self._require_root()
        payload = self._checkpoint_payload(epoch)
        path = _checkpoint_path(root, epoch)
        digest = _atomic_write_once(path, _torch_bytes(payload))
        _write_sidecar(path, digest)
        exports, manifest_digest = self._write_exports(root, epoch)
        receipt = {
            "schema": CHECKPOINT_RECEIPT_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "epoch": epoch,
            "update_count": epoch * 2,
            "checkpoint_path": str(path.relative_to(root)),
            "checkpoint_sha256": digest,
            "export_manifest_path": str(_export_manifest_path(root, epoch).relative_to(root)),
            "export_manifest_sha256": manifest_digest,
            "arm_order": list(ARMS),
            "exports": exports,
        }
        _atomic_json_once(_checkpoint_receipt_path(root, epoch), receipt)
        return receipt

    def run_to_epoch(self, stop_epoch: int | None = None) -> dict[str, Any] | None:
        self._require_root()
        target = 100 if stop_epoch is None else stop_epoch
        if type(target) is not int or not (self.completed_epochs <= target <= 100):
            raise V023TwoRouteSourceTrainingRunnerError("target epoch is outside budget 100")
        receipt = None
        while self.completed_epochs < target:
            before = self.orchestrator.update_cursor
            rounds = tuple(self.orchestrator.advance() for _ in ROUTES)
            if tuple(item.route for item in rounds) != ROUTES:
                raise V023TwoRouteSourceTrainingRunnerError("route order drifted")
            if self.orchestrator.update_cursor != before + 2 or self.orchestrator.next_route != "C1":
                raise V023TwoRouteSourceTrainingRunnerError("epoch did not close")
            if self.completed_epochs == 100:
                receipt = self._write_checkpoint(100)
        if self.completed_epochs == 100:
            integrity = self._verify_epoch_100_integrity()
            self._write_final_receipt(integrity)
        return receipt

    def _write_final_receipt(self, integrity: Mapping[str, Any]) -> None:
        root = self._require_root()
        destination = root / "canonical-receipt.json"
        if destination.exists() or destination.is_symlink():
            raise V023TwoRouteSourceTrainingRunnerError("canonical receipt already exists")
        checkpoints = []
        for epoch in FORMAL_CHECKPOINT_EPOCHS:
            path = _checkpoint_path(root, epoch)
            checkpoints.append(
                {"epoch": epoch, "path": str(path.relative_to(root)), "sha256": _verify_sidecar(path)}
            )
        _atomic_json_once(
            destination,
            {
                "schema": RECEIPT_SCHEMA,
                "claim_ceiling": CLAIM_CEILING,
                "source_split": SOURCE_SPLIT,
                "epoch_budget": 100,
                "completed_epochs": 100,
                "completed_updates": 200,
                "provider_identity": self.provider_identity,
                "initialization_sha256": self.orchestrator.initialization_sha256,
                "arm_order": list(ARMS),
                "route_order": list(ROUTES),
                "source_ablation_map": _source_map_payload(),
                "config": self.config.to_payload(),
                "authority_digests": asdict(self.config.authority_digests),
                "checkpoints": checkpoints,
                "epoch_100_integrity": deepcopy(dict(integrity)),
            },
        )

    def run(self) -> dict[str, Any] | None:
        return self.run_to_epoch()

    @staticmethod
    def _read_json(path: Path) -> Mapping[str, Any]:
        if path.is_symlink() or not path.is_file():
            raise V023TwoRouteSourceTrainingRunnerError(
                "JSON artifact is not a regular file"
            )
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise V023TwoRouteSourceTrainingRunnerError("JSON artifact is invalid") from error
        if not isinstance(value, Mapping):
            raise V023TwoRouteSourceTrainingRunnerError("JSON artifact must be a mapping")
        return value

    def _validate_checkpoint(self, checkpoint: Mapping[str, Any]) -> None:
        expected = {
            "schema", "claim_ceiling", "source_split", "epoch", "update_count", "config",
            "authority_digests", "provider_identity", "arm_order", "route_order",
            "source_ablation_map", "initialization_sha256", "runner_schema",
            "updates_per_source_training_epoch", "formal_checkpoint_cadence_updates",
            "models_and_optimizers", "provider_sampler_state", "consumed_file_order",
            "orchestrator_state",
        }
        if set(checkpoint) != expected or checkpoint.get("schema") != CHECKPOINT_SCHEMA:
            raise V023TwoRouteSourceTrainingRunnerError("unsupported runner checkpoint schema")
        if (
            checkpoint["claim_ceiling"] != CLAIM_CEILING
            or checkpoint["source_split"] != SOURCE_SPLIT
            or checkpoint["runner_schema"] != RUNNER_SCHEMA
            or checkpoint["updates_per_source_training_epoch"] != UPDATES_PER_EPOCH
            or checkpoint["formal_checkpoint_cadence_updates"] != FORMAL_CHECKPOINT_UPDATES
        ):
            raise V023TwoRouteSourceTrainingRunnerError("TEST or claim boundary rejected")
        if checkpoint["config"] != self.config.to_payload() or checkpoint["authority_digests"] != asdict(self.config.authority_digests):
            raise V023TwoRouteSourceTrainingRunnerError("frozen config or authority digest mismatch")
        if checkpoint["provider_identity"] != self.provider_identity:
            raise V023TwoRouteSourceTrainingRunnerError("provider identity mismatch")
        if checkpoint["arm_order"] != list(ARMS) or any(arm in FORBIDDEN_ARMS for arm in checkpoint["arm_order"]):
            raise V023TwoRouteSourceTrainingRunnerError("arm order includes a forbidden or fourth arm")
        if checkpoint["route_order"] != list(ROUTES) or "C3" in checkpoint["route_order"]:
            raise V023TwoRouteSourceTrainingRunnerError("route order includes C3")
        if checkpoint["source_ablation_map"] != _source_map_payload():
            raise V023TwoRouteSourceTrainingRunnerError("source map drifted")
        epoch = checkpoint["epoch"]
        if epoch not in FORMAL_CHECKPOINT_EPOCHS or checkpoint["update_count"] != epoch * 2:
            raise V023TwoRouteSourceTrainingRunnerError("checkpoint cadence is invalid")
        state = checkpoint["orchestrator_state"]
        if (
            checkpoint["initialization_sha256"] != self.orchestrator.initialization_sha256
            or not isinstance(state, Mapping)
            or state.get("update_cursor") != epoch * 2
            or state.get("next_route_index") != 0
            or state.get("arm_order") != list(ARMS)
            or state.get("route_order") != list(ROUTES)
            or not _tree_equal(checkpoint["models_and_optimizers"], state.get("arms"))
            or not _tree_equal(
                checkpoint["provider_sampler_state"],
                state.get("provider_sampler_state"),
            )
            or not _tree_equal(checkpoint["consumed_file_order"], state.get("file_order"))
        ):
            raise V023TwoRouteSourceTrainingRunnerError("orchestrator state binding drifted")
        expected_counts = {"C1": epoch, "C2": epoch}
        if state.get("route_update_counts") != expected_counts:
            raise V023TwoRouteSourceTrainingRunnerError("orchestrator route counts drifted")
        arms = checkpoint["models_and_optimizers"]
        if not isinstance(arms, Mapping) or tuple(arms) != ARMS:
            raise V023TwoRouteSourceTrainingRunnerError("checkpoint arm closure drifted")
        for arm in ARMS:
            arm_state = arms[arm]
            if (
                not isinstance(arm_state, Mapping)
                or arm_state.get("update_count") != epoch * UPDATES_PER_EPOCH
                or arm_state.get("route_update_counts") != expected_counts
                or arm_state.get("train_seed") != FORMAL_TRAIN_SEED
                or arm_state.get("config") != asdict(self.config.orchestrator_config.model_config)
            ):
                raise V023TwoRouteSourceTrainingRunnerError(
                    "checkpoint arm config/update binding drifted"
                )
        self._validate_consumed_history(
            checkpoint["consumed_file_order"], checkpoint["provider_sampler_state"],
            updates=epoch * UPDATES_PER_EPOCH,
        )

    @staticmethod
    def _validate_consumed_history(
        file_order: object, sampler: object, *, updates: int
    ) -> None:
        if not isinstance(file_order, list) or len(file_order) != updates:
            raise V023TwoRouteSourceTrainingRunnerError("consumed-file history is incomplete")
        if not isinstance(sampler, Mapping):
            raise V023TwoRouteSourceTrainingRunnerError("provider sampler state is invalid")
        consumed = sampler.get("consumed_file_order")
        if (
            sampler.get("next_update_cursor") != updates
            or sampler.get("next_source_index") != 0
            or not isinstance(consumed, list)
            or len(consumed) != updates * 2
        ):
            raise V023TwoRouteSourceTrainingRunnerError("provider sampler cursor/history drifted")
        for update_cursor, order_entry in enumerate(file_order):
            expected_route = ROUTES[update_cursor % len(ROUTES)]
            if (
                not isinstance(order_entry, Mapping)
                or order_entry.get("update_cursor") != update_cursor
                or order_entry.get("route") != expected_route
            ):
                raise V023TwoRouteSourceTrainingRunnerError("consumed-file order drifted")
            source_files = order_entry.get("source_files")
            if not isinstance(source_files, list):
                raise V023TwoRouteSourceTrainingRunnerError("consumed-file order drifted")
            expected_source_files = []
            for offset, source in enumerate(("neutral", "informed")):
                record = consumed[update_cursor * 2 + offset]
                if (
                    not isinstance(record, Mapping)
                    or record.get("update_cursor") != update_cursor
                    or record.get("route") != expected_route
                    or record.get("source") != source
                    or not isinstance(record.get("file_id"), str)
                ):
                    raise V023TwoRouteSourceTrainingRunnerError(
                        "provider consumed-file history drifted"
                    )
                expected_source_files.append((source, record["file_id"]))
            if source_files != expected_source_files:
                raise V023TwoRouteSourceTrainingRunnerError(
                    "provider and orchestrator consumed-file histories disagree"
                )

    def _validate_exports(self, root: Path, checkpoint: Mapping[str, Any]) -> None:
        epoch = checkpoint["epoch"]
        receipt = self._read_json(_checkpoint_receipt_path(root, epoch))
        manifest_path = _export_manifest_path(root, epoch)
        manifest = self._read_json(manifest_path)
        expected_receipt_fields = {
            "schema", "claim_ceiling", "epoch", "update_count", "checkpoint_path",
            "checkpoint_sha256", "export_manifest_path", "export_manifest_sha256",
            "arm_order", "exports",
        }
        if (
            set(receipt) != expected_receipt_fields
            or receipt.get("schema") != CHECKPOINT_RECEIPT_SCHEMA
            or receipt.get("claim_ceiling") != CLAIM_CEILING
            or receipt.get("epoch") != epoch
            or receipt.get("update_count") != checkpoint["update_count"]
            or receipt.get("arm_order") != list(ARMS)
            or receipt.get("checkpoint_path")
            != str(_checkpoint_path(root, epoch).relative_to(root))
            or receipt.get("export_manifest_path")
            != str(manifest_path.relative_to(root))
        ):
            raise V023TwoRouteSourceTrainingRunnerError(
                "checkpoint/export receipt binding drifted"
            )
        if receipt.get("checkpoint_sha256") != _verify_sidecar(_checkpoint_path(root, epoch)):
            raise V023TwoRouteSourceTrainingRunnerError("checkpoint receipt digest drifted")
        if receipt.get("export_manifest_sha256") != _file_sha256(manifest_path):
            raise V023TwoRouteSourceTrainingRunnerError("export manifest digest drifted")
        if (
            manifest.get("schema") != EXPORT_MANIFEST_SCHEMA
            or manifest.get("claim_ceiling") != CLAIM_CEILING
            or manifest.get("arm_order") != list(ARMS)
            or manifest.get("route_order") != list(ROUTES)
            or manifest.get("source_ablation_map") != _source_map_payload()
            or manifest.get("epoch") != epoch
            or manifest.get("update_count") != epoch * 2
        ):
            raise V023TwoRouteSourceTrainingRunnerError("export manifest drifted")
        exports = manifest.get("exports")
        if not isinstance(exports, list) or len(exports) != 3 or exports != receipt.get("exports"):
            raise V023TwoRouteSourceTrainingRunnerError("three exports are incomplete")
        for arm, entry in zip(ARMS, exports, strict=True):
            if entry.get("arm") != arm or entry.get("source_mapping") != list(SOURCE_MAP[arm]):
                raise V023TwoRouteSourceTrainingRunnerError("export arm mapping drifted")
            relative = entry.get("path")
            if not isinstance(relative, str) or relative.startswith("/") or ".." in Path(relative).parts:
                raise V023TwoRouteSourceTrainingRunnerError("export path is invalid")
            path = root / relative
            if _verify_sidecar(path) != entry.get("sha256"):
                raise V023TwoRouteSourceTrainingRunnerError("export digest verification failed")
            state = _read_torch(path)
            checkpoint_arm = checkpoint["models_and_optimizers"][arm]
            if (
                state.get("schema") != TWO_ROUTE_CHECKPOINT_SCHEMA
                or state.get("routes") != list(ROUTES)
                or state.get("algorithm") != TWO_ROUTE_ALGORITHM
                or state.get("update_count") != checkpoint["update_count"]
                or state.get("route_update_counts") != {"C1": epoch, "C2": epoch}
                or state.get("train_seed") != FORMAL_TRAIN_SEED
                or state.get("config") != asdict(self.config.orchestrator_config.model_config)
                or not _tree_equal(state, checkpoint_arm)
            ):
                raise V023TwoRouteSourceTrainingRunnerError("export is not a two-route model")
            independent = EEAxisTwoRouteModel(
                self.config.orchestrator_config.model_config,
                train_seed=FORMAL_TRAIN_SEED,
            )
            try:
                loaded_count = independent.load_checkpoint_state(deepcopy(state))
            except Exception as error:
                raise V023TwoRouteSourceTrainingRunnerError(
                    "export model/Adam state failed exact reload"
                ) from error
            reexported = independent.checkpoint_state(
                update_count=loaded_count,
                route_update_counts={"C1": epoch, "C2": epoch},
            )
            if not _tree_equal(reexported, checkpoint_arm):
                raise V023TwoRouteSourceTrainingRunnerError(
                    "reloaded export does not equal its checkpoint arm"
                )

    def _verify_epoch_100_integrity(self) -> Mapping[str, Any]:
        root = self._require_root()
        path = _checkpoint_path(root, 100)
        checkpoint_sha256 = _verify_sidecar(path)
        checkpoint = _read_torch(path)
        self._validate_checkpoint(checkpoint)
        self._validate_exports(root, checkpoint)
        try:
            independent_provider = _parse_factory_spec(
                self.config.provider_factory_spec
            )()
            independent = V023TwoRouteSourceTrainingRunner(
                self.config, independent_provider
            )
            independent.resume_from_checkpoint(path)
        except Exception as error:
            raise V023TwoRouteSourceTrainingRunnerError(
                "independent epoch-100 model/optimizer/provider/sampler restore failed"
            ) from error
        restored = independent.orchestrator.checkpoint_state()
        if not _tree_equal(restored, checkpoint["orchestrator_state"]):
            raise V023TwoRouteSourceTrainingRunnerError(
                "independent epoch-100 state is not exact"
            )
        manifest_path = _export_manifest_path(root, 100)
        manifest = self._read_json(manifest_path)
        return {
            "decision": EPOCH_100_INTEGRITY_DECISION,
            "checkpoint_sha256": checkpoint_sha256,
            "export_manifest_sha256": _file_sha256(manifest_path),
            "export_sha256_by_arm": {
                entry["arm"]: entry["sha256"] for entry in manifest["exports"]
            },
            "restored_update_count": restored["update_cursor"],
            "restored_route_update_counts": deepcopy(
                restored["route_update_counts"]
            ),
            "provider_sampler_exact": True,
            "consumed_file_history_exact": True,
            "exports_reloaded_exact": True,
        }

    def resume_from_checkpoint(self, checkpoint_path: str | Path) -> None:
        path = Path(checkpoint_path)
        _reject_test(path, field="checkpoint path")
        root = path.parent.parent
        try:
            named_epoch = int(path.name.removeprefix("epoch-").removesuffix(".runner.pt"))
        except ValueError as error:
            raise V023TwoRouteSourceTrainingRunnerError(
                "checkpoint path is not canonical"
            ) from error
        if path != _checkpoint_path(root, named_epoch):
            raise V023TwoRouteSourceTrainingRunnerError(
                "checkpoint path is not canonical"
            )
        _verify_sidecar(path)
        checkpoint = _read_torch(path)
        self._validate_checkpoint(checkpoint)
        if self._read_json(root / "canonical-status.json") != self._status_payload():
            raise V023TwoRouteSourceTrainingRunnerError("canonical status drifted")
        self._validate_exports(root, checkpoint)
        try:
            self.orchestrator.load_checkpoint_state(deepcopy(checkpoint["orchestrator_state"]))
        except Exception as error:
            raise V023TwoRouteSourceTrainingRunnerError("exact orchestrator resume failed") from error
        if not _tree_equal(
            self.orchestrator.checkpoint_state(), checkpoint["orchestrator_state"]
        ):
            raise V023TwoRouteSourceTrainingRunnerError(
                "installed orchestrator state is not exact"
            )
        self.output_root = root


def _parse_factory_spec(specification: str) -> Callable[[], object]:
    _reject_test(specification, field="provider factory path")
    module_name, separator, attribute = specification.partition(":")
    if not separator or not module_name or not attribute or "." in attribute:
        raise V023TwoRouteSourceTrainingRunnerError("provider factory must use MODULE:CALLABLE")
    try:
        module = importlib.import_module(module_name)
    except Exception as error:
        raise V023TwoRouteSourceTrainingRunnerError("provider factory module cannot be imported") from error
    factory = getattr(module, attribute, None)
    if not callable(factory):
        raise V023TwoRouteSourceTrainingRunnerError("provider factory is not callable")
    return factory


def _load_model_config(path: str | Path) -> EEAxisTwoRouteConfig:
    source = Path(path)
    _reject_test(source, field="model config path")
    if source.is_symlink() or not source.is_file():
        raise V023TwoRouteSourceTrainingRunnerError("model config is not a regular file")
    if _file_sha256(source) != FROZEN_MODEL_CONFIG_SHA256:
        raise V023TwoRouteSourceTrainingRunnerError(
            "model config SHA-256 is not the frozen successor digest"
        )
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023TwoRouteSourceTrainingRunnerError("model config JSON is invalid") from error
    if not isinstance(raw, Mapping) or set(raw) != {"q1", "q2"}:
        raise V023TwoRouteSourceTrainingRunnerError("model config requires exactly q1 and q2; Q3 is forbidden")
    try:
        q1 = dict(raw["q1"])
        q2 = dict(raw["q2"])
        for values, fields in ((q1, ("hidden_layers", "loss_weights")), (q2, ("hidden_layers",))):
            for field in fields:
                if isinstance(values.get(field), list):
                    values[field] = tuple(values[field])
        if q1 != FROZEN_Q1_CONFIG or q2 != FROZEN_Q2_CONFIG:
            raise V023TwoRouteSourceTrainingRunnerError(
                "model config Q1/Q2 records drifted from the frozen authority"
            )
        return EEAxisTwoRouteConfig(
            q1=EEAxisActionSharedConfig(**q1),
            q2=EEAxisV014HeadConfig(**q2),
        )
    except V023TwoRouteSourceTrainingRunnerError:
        raise
    except (TypeError, ValueError) as error:
        raise V023TwoRouteSourceTrainingRunnerError("model config is incompatible") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--epochs", required=True, type=int)
    parser.add_argument("--provider-factory", required=True, metavar="MODULE:CALLABLE")
    parser.add_argument("--model-config-json", required=True)
    parser.add_argument("--train-seed", required=True, type=int)
    parser.add_argument("--authority-sha256", required=True)
    parser.add_argument("--code-sha256", required=True)
    parser.add_argument("--input-sha256", required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    return parser


def preflight_from_args(arguments: argparse.Namespace) -> V023TwoRouteSourceTrainingRunner:
    if not arguments.execute:
        raise V023TwoRouteSourceTrainingRunnerError("--execute is required")
    output_root = Path(arguments.output_root)
    _reject_test(output_root, field="output path")
    if output_root.exists() or output_root.is_symlink():
        raise V023TwoRouteSourceTrainingRunnerError("output root must be absent")
    model_config = _load_model_config(arguments.model_config_json)
    if arguments.train_seed != FORMAL_TRAIN_SEED:
        raise V023TwoRouteSourceTrainingRunnerError(
            f"train seed must be exactly {FORMAL_TRAIN_SEED}"
        )
    provider = _parse_factory_spec(arguments.provider_factory)()
    try:
        payload = authenticate_factory_v3_provider_identity(
            provider,
            expected_train_seed=FORMAL_TRAIN_SEED,
            expected_model_config_sha256=FROZEN_MODEL_CONFIG_SHA256,
        )
    except V023TwoRouteOrchestratorError as error:
        raise V023TwoRouteSourceTrainingRunnerError(
            "provider identity failed factory-v3 authentication"
        ) from error
    config = FrozenSourceTrainingConfig(
        epoch_budget=arguments.epochs,
        orchestrator_config=V023TwoRouteOrchestratorConfig.formal(
            model_config=model_config,
            train_seed=arguments.train_seed,
            model_config_sha256=FROZEN_MODEL_CONFIG_SHA256,
        ),
        provider_factory_spec=arguments.provider_factory,
        authority_digests=RunAuthorityDigests(
            arguments.authority_sha256, arguments.code_sha256, arguments.input_sha256
        ),
        provider_config_sha256=payload["provider_config_sha256"],
    )
    return V023TwoRouteSourceTrainingRunner(config, provider)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        arguments = parser.parse_args(argv)
        runner = preflight_from_args(arguments)
        runner.begin_new(arguments.output_root)
        runner.run()
    except V023TwoRouteSourceTrainingRunnerError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ARMS", "CHECKPOINT_SCHEMA", "CLAIM_CEILING", "FORMAL_CHECKPOINT_EPOCHS",
    "FORMAL_CHECKPOINT_UPDATES", "FrozenSourceTrainingConfig", "ROUTES", "RUNNER_SCHEMA",
    "RunAuthorityDigests", "SOURCE_MAP", "SOURCE_SPLIT", "SUPPORTED_EPOCH_BUDGETS",
    "UPDATES_PER_EPOCH", "V023TwoRouteSourceTrainingRunner",
    "EPOCH_100_INTEGRITY_DECISION", "FORMAL_TRAIN_SEED",
    "FROZEN_MODEL_CONFIG_SHA256",
    "V023TwoRouteSourceTrainingRunnerError", "build_parser", "main", "preflight_from_args",
]
