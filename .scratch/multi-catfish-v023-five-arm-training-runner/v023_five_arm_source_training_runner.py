#!/usr/bin/env python3
"""Fail-closed source-training runner for the V0.23 five-arm learner seam.

This module only consumes deterministic source batches through the existing
``DeterministicRouteBatchProvider`` and advances the existing five independent
current ``EEAxisLCSRSThreeRoute`` learners.  One source-training epoch is
exactly C1 -> C2 -> C3 (three learner updates), and checkpoints are emitted
only after complete epochs 100, 200, ... .  It has no simulator, physical
episode, learner-evaluation, or TEST execution path.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import argparse
import importlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sys
from typing import Any

import torch

from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_v014_head import EEAxisV014HeadConfig
from mcrl.algorithms.ee_axis_lcsrs_three_route import (
    EEAxisLCSRSThreeRoute,
    LCSRS_THREE_ROUTE_ALGORITHM,
    LCSRSThreeRouteConfig,
)
from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3HeadConfig


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ORCHESTRATOR_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-five-arm-learner-orchestrator"
    / "v023_five_arm_learner_orchestrator.py"
)

RUNNER_SCHEMA = "multi-catfish-mcrl-v023-five-arm-source-training-runner-v2"
STATUS_SCHEMA = f"{RUNNER_SCHEMA}-canonical-status"
RECEIPT_SCHEMA = f"{RUNNER_SCHEMA}-canonical-receipt"
CHECKPOINT_SCHEMA = f"{RUNNER_SCHEMA}-checkpoint"
CHECKPOINT_RECEIPT_SCHEMA = f"{RUNNER_SCHEMA}-checkpoint-receipt"
EXPORT_MANIFEST_SCHEMA = f"{RUNNER_SCHEMA}-five-current-model-exports"
SOURCE_SPLIT = "SOURCE_TRAIN"
CLAIM_CEILING = (
    "IMPLEMENTATION_ONLY_SOURCE_TRAINING_NO_SIMULATOR_NO_EPISODE_NO_TEST_NO_EFFICACY"
)
FORMAL_CHECKPOINT_EPOCHS = 100
UPDATES_PER_EPOCH = 3
FORMAL_CHECKPOINT_UPDATES = FORMAL_CHECKPOINT_EPOCHS * UPDATES_PER_EPOCH
ARMS = ("ALL_NEUTRAL_CONTROL", "FULL", "DROP_C1", "DROP_C2", "DROP_C3")
ROUTES = ("C1", "C2", "C3")
SOURCE_MAP: Mapping[str, Mapping[str, str]] = {
    "ALL_NEUTRAL_CONTROL": {"C1": "neutral", "C2": "neutral", "C3": "neutral"},
    "FULL": {"C1": "informed", "C2": "informed", "C3": "informed"},
    "DROP_C1": {"C1": "neutral", "C2": "informed", "C3": "informed"},
    "DROP_C2": {"C1": "informed", "C2": "neutral", "C3": "informed"},
    "DROP_C3": {"C1": "informed", "C2": "informed", "C3": "neutral"},
}
SUPPORTED_FROZEN_EPOCH_BUDGETS = (100, 500, 1500, 3000, 9000)


class V023SourceTrainingRunnerError(RuntimeError):
    """The frozen source-training lifecycle contract was violated."""


def _load_orchestrator_module() -> Any:
    """Load the existing seam without copying or reimplementing its protocol."""

    if ORCHESTRATOR_PATH.is_symlink() or not ORCHESTRATOR_PATH.is_file():
        raise V023SourceTrainingRunnerError(
            "existing five-arm learner orchestrator source is unavailable"
        )
    module_name = "v023_five_arm_learner_orchestrator_for_training_runner"
    existing = sys.modules.get(module_name)
    if existing is not None:
        if Path(str(getattr(existing, "__file__", ""))).resolve() != ORCHESTRATOR_PATH.resolve():
            raise V023SourceTrainingRunnerError(
                "five-arm learner orchestrator was already imported from another path"
            )
        return existing
    wanted = ORCHESTRATOR_PATH.resolve()
    for module in tuple(sys.modules.values()):
        module_file = getattr(module, "__file__", None)
        if not isinstance(module_file, str):
            continue
        try:
            if Path(module_file).resolve() == wanted:
                sys.modules[module_name] = module
                return module
        except OSError:
            continue
    spec = importlib.util.spec_from_file_location(module_name, ORCHESTRATOR_PATH)
    if spec is None or spec.loader is None:
        raise V023SourceTrainingRunnerError("cannot import five-arm learner orchestrator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


ORCHESTRATOR = _load_orchestrator_module()


def _sha256_digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023SourceTrainingRunnerError(f"{field} must be a lowercase SHA-256")
    return value


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023SourceTrainingRunnerError("artifact is not canonical finite JSON") from error


def _jsonable(value: object) -> object:
    """Convert dataclass payloads to deterministic JSON-compatible trees."""

    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise V023SourceTrainingRunnerError(f"artifact is not a regular file: {path}")
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _torch_bytes(value: object) -> bytes:
    stream = BytesIO()
    torch.save(value, stream)
    return stream.getvalue()


def _read_torch(path: Path) -> Mapping[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise V023SourceTrainingRunnerError(f"checkpoint is not a regular file: {path}")
    try:
        value = torch.load(path, map_location="cpu", weights_only=False)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise V023SourceTrainingRunnerError(f"cannot deserialize checkpoint: {path}") from error
    if not isinstance(value, Mapping):
        raise V023SourceTrainingRunnerError("checkpoint root must be a mapping")
    return value


def _atomic_write_once(path: Path, payload: bytes) -> str:
    """Publish a complete file exactly once, without an overwrite race.

    A completed temporary inode is hard-linked into its final name.  ``link``
    fails atomically if the final name already exists, unlike ``replace``.
    """

    if path.exists() or path.is_symlink():
        raise V023SourceTrainingRunnerError(f"refusing to overwrite artifact: {path}")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise V023SourceTrainingRunnerError(f"artifact parent is unavailable: {path.parent}")
    temporary = path.parent / f".{path.name}.{secrets.token_hex(16)}.tmp"
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise V023SourceTrainingRunnerError(
                f"refusing to overwrite artifact: {path}"
            ) from error
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
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


def _write_digest_sidecar(path: Path, digest: str) -> None:
    _sha256_digest(digest, field=f"digest for {path.name}")
    _atomic_write_once(path.with_suffix(path.suffix + ".sha256"), f"{digest}\n".encode("ascii"))


def _verify_digest_sidecar(path: Path) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if sidecar.is_symlink() or not sidecar.is_file():
        raise V023SourceTrainingRunnerError(f"checkpoint digest sidecar is missing: {sidecar}")
    try:
        expected = sidecar.read_text(encoding="ascii")
    except OSError as error:
        raise V023SourceTrainingRunnerError("cannot read checkpoint digest sidecar") from error
    if not expected.endswith("\n"):
        raise V023SourceTrainingRunnerError("checkpoint digest sidecar is malformed")
    expected = expected[:-1]
    _sha256_digest(expected, field="checkpoint digest sidecar")
    actual = _file_sha256(path)
    if actual != expected:
        raise V023SourceTrainingRunnerError("checkpoint digest verification failed")
    return actual


def _source_map_payload() -> dict[str, dict[str, str]]:
    return {arm: dict(SOURCE_MAP[arm]) for arm in ARMS}


def _tree_equal(left: object, right: object) -> bool:
    """Compare checkpoint trees without invoking tensor truth-value coercion."""

    if type(left) is not type(right):
        return False
    if isinstance(left, torch.Tensor):
        return torch.equal(left, right)
    if isinstance(left, Mapping):
        return tuple(left) == tuple(right) and all(
            _tree_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(
            _tree_equal(first, second) for first, second in zip(left, right, strict=True)
        )
    return bool(left == right)


@dataclass(frozen=True, slots=True)
class RunAuthorityDigests:
    """Frozen external hash declarations that bind source-training artifacts."""

    authority_sha256: str
    code_sha256: str
    input_sha256: str

    def __post_init__(self) -> None:
        _sha256_digest(self.authority_sha256, field="authority_sha256")
        _sha256_digest(self.code_sha256, field="code_sha256")
        _sha256_digest(self.input_sha256, field="input_sha256")


@dataclass(frozen=True, slots=True)
class FrozenSourceTrainingConfig:
    """The complete pre-outcome source-training configuration.

    Later epoch budgets are represented but require a separate frozen budget
    authority digest.  This runner never promotes a budget by observed output.
    """

    epoch_budget: int
    orchestrator_config: Any
    provider_factory_spec: str
    authority_digests: RunAuthorityDigests
    source_split: str = SOURCE_SPLIT
    later_budget_authority_sha256: str | None = None

    def __post_init__(self) -> None:
        if type(self.epoch_budget) is not int or self.epoch_budget <= 0:
            raise V023SourceTrainingRunnerError("epoch_budget must be a positive exact integer")
        if self.epoch_budget % FORMAL_CHECKPOINT_EPOCHS != 0:
            raise V023SourceTrainingRunnerError(
                "epoch_budget must be divisible by 100 complete source-training epochs"
            )
        if self.epoch_budget not in SUPPORTED_FROZEN_EPOCH_BUDGETS:
            raise V023SourceTrainingRunnerError(
                "epoch_budget is not an authorized frozen V0.23 budget"
            )
        if not isinstance(self.orchestrator_config, ORCHESTRATOR.V023FiveArmOrchestratorConfig):
            raise TypeError("orchestrator_config must be the existing V0.23 formal config")
        if (
            not self.orchestrator_config.formal_use
            or self.orchestrator_config.checkpoint_cadence_updates
            != FORMAL_CHECKPOINT_UPDATES
        ):
            raise V023SourceTrainingRunnerError(
                "runner requires the existing formal 100-epoch / 300-update cadence"
            )
        if (
            not isinstance(self.provider_factory_spec, str)
            or not self.provider_factory_spec
            or self.provider_factory_spec != self.provider_factory_spec.strip()
        ):
            raise V023SourceTrainingRunnerError("provider_factory_spec must be explicit")
        if not isinstance(self.authority_digests, RunAuthorityDigests):
            raise TypeError("authority_digests must be RunAuthorityDigests")
        if self.source_split != SOURCE_SPLIT:
            raise V023SourceTrainingRunnerError("TEST or any non-source split is rejected")
        if self.epoch_budget == 100:
            if self.later_budget_authority_sha256 is not None:
                _sha256_digest(
                    self.later_budget_authority_sha256,
                    field="later_budget_authority_sha256",
                )
        elif self.later_budget_authority_sha256 is None:
            raise V023SourceTrainingRunnerError(
                "a later frozen budget requires later_budget_authority_sha256"
            )
        else:
            _sha256_digest(
                self.later_budget_authority_sha256,
                field="later_budget_authority_sha256",
            )

    def to_payload(self) -> dict[str, Any]:
        return {
            "epoch_budget": self.epoch_budget,
            "orchestrator_config": _jsonable(asdict(self.orchestrator_config)),
            "provider_factory_spec": self.provider_factory_spec,
            "authority_digests": asdict(self.authority_digests),
            "source_split": self.source_split,
            "later_budget_authority_sha256": self.later_budget_authority_sha256,
        }


def _provider_identity(provider: object) -> str:
    """Require an explicit stable provider identity in addition to its protocol."""

    candidate = getattr(provider, "provider_identity", None)
    identity = candidate() if callable(candidate) else candidate
    if (
        not isinstance(identity, str)
        or not identity
        or identity != identity.strip()
        or len(identity) > 512
    ):
        raise V023SourceTrainingRunnerError(
            "provider must expose a nonempty explicit provider_identity"
        )
    return identity


def _provider_epoch_budget(provider: object) -> int:
    """Require the source provider to declare its exact frozen epoch horizon."""

    candidate = getattr(provider, "planned_epoch_budget", None)
    budget = candidate() if callable(candidate) else candidate
    if type(budget) is not int or budget <= 0:
        raise V023SourceTrainingRunnerError(
            "provider must expose a positive integer planned epoch budget"
        )
    return budget


def _current_model_algorithm() -> str:
    if not isinstance(LCSRS_THREE_ROUTE_ALGORITHM, str) or not LCSRS_THREE_ROUTE_ALGORITHM:
        raise V023SourceTrainingRunnerError("current three-route model has no algorithm identity")
    return LCSRS_THREE_ROUTE_ALGORITHM


def _checkpoint_path(output_root: Path, epoch: int) -> Path:
    return output_root / "checkpoints" / f"epoch-{epoch:04d}.runner.pt"


def _checkpoint_receipt_path(output_root: Path, epoch: int) -> Path:
    return output_root / "checkpoint-receipts" / f"epoch-{epoch:04d}.json"


def _export_manifest_path(output_root: Path, epoch: int) -> Path:
    return output_root / "exports" / f"epoch-{epoch:04d}.json"


class V023FiveArmSourceTrainingRunner:
    """Write-once source-training lifecycle around the existing five-arm seam."""

    def __init__(self, config: FrozenSourceTrainingConfig, provider: object) -> None:
        if not isinstance(config, FrozenSourceTrainingConfig):
            raise TypeError("config must be FrozenSourceTrainingConfig")
        if not isinstance(provider, ORCHESTRATOR.DeterministicRouteBatchProvider):
            raise TypeError("provider does not satisfy DeterministicRouteBatchProvider")
        self.config = config
        self.provider = provider
        self.provider_identity = _provider_identity(provider)
        self.provider_epoch_budget = _provider_epoch_budget(provider)
        if self.provider_epoch_budget != config.epoch_budget:
            raise V023SourceTrainingRunnerError(
                "provider epoch budget disagrees with runner epoch budget"
            )
        self.orchestrator = ORCHESTRATOR.V023FiveArmLearnerOrchestrator(
            config.orchestrator_config,
            provider,
        )
        self.output_root: Path | None = None
        self._resumed = False

    @property
    def completed_epochs(self) -> int:
        return self.orchestrator.completed_source_training_epochs

    def _status_payload(self) -> dict[str, Any]:
        return {
            "schema": STATUS_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "source_split": SOURCE_SPLIT,
            "runner_schema": RUNNER_SCHEMA,
            "config": self.config.to_payload(),
            "provider_identity": self.provider_identity,
            "arm_order": list(ARMS),
            "route_order": list(ROUTES),
            "source_ablation_map": _source_map_payload(),
            "initialization_sha256": self.orchestrator.initialization_sha256,
            "updates_per_source_training_epoch": UPDATES_PER_EPOCH,
            "formal_checkpoint_cadence_epochs": FORMAL_CHECKPOINT_EPOCHS,
            "formal_checkpoint_cadence_updates": FORMAL_CHECKPOINT_UPDATES,
        }

    def begin_new(self, output_root: str | Path) -> Path:
        """Claim a fresh output root and publish its immutable initial status."""

        root = Path(output_root)
        if root.exists() or root.is_symlink():
            raise V023SourceTrainingRunnerError("output root already exists; overwrite is refused")
        if root.parent.is_symlink() or not root.parent.is_dir():
            raise V023SourceTrainingRunnerError("output root parent is unavailable")
        try:
            root.mkdir(mode=0o700)
            for relative in ("checkpoints", "checkpoint-receipts", "exports"):
                (root / relative).mkdir(mode=0o700)
        except FileExistsError as error:
            raise V023SourceTrainingRunnerError(
                "output root already exists; overwrite is refused"
            ) from error
        self.output_root = root
        _atomic_json_once(root / "canonical-status.json", self._status_payload())
        return root

    def _require_output_root(self) -> Path:
        if self.output_root is None:
            raise V023SourceTrainingRunnerError("begin_new or resume_from_checkpoint is required")
        return self.output_root

    def _advance_complete_epoch(self) -> None:
        before_updates = self.orchestrator.update_cursor
        if (
            self.orchestrator.next_route != ROUTES[0]
            or before_updates != self.completed_epochs * UPDATES_PER_EPOCH
        ):
            raise V023SourceTrainingRunnerError("partial source-training epoch is refused")
        observed = tuple(self.orchestrator.advance() for _ in ROUTES)
        if tuple(receipt.route for receipt in observed) != ROUTES:
            raise V023SourceTrainingRunnerError("source-training route order drifted")
        if self.orchestrator.next_route != ROUTES[0]:
            raise V023SourceTrainingRunnerError("complete source-training epoch did not close")
        if self.orchestrator.update_cursor != before_updates + UPDATES_PER_EPOCH:
            raise V023SourceTrainingRunnerError("source-training update count drifted")

    def _checkpoint_payload(self) -> dict[str, Any]:
        state = self.orchestrator.checkpoint_state()
        epoch = self.completed_epochs
        if epoch <= 0 or epoch % FORMAL_CHECKPOINT_EPOCHS != 0:
            raise V023SourceTrainingRunnerError("formal checkpoint requires a 100-epoch boundary")
        if self.orchestrator.update_cursor != epoch * UPDATES_PER_EPOCH:
            raise V023SourceTrainingRunnerError("checkpoint contains a partial epoch")
        if self.orchestrator.next_route != ROUTES[0]:
            raise V023SourceTrainingRunnerError("checkpoint is not positioned at C1")
        return {
            "schema": CHECKPOINT_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "source_split": SOURCE_SPLIT,
            "runner_schema": RUNNER_SCHEMA,
            "epoch": epoch,
            "update_count": self.orchestrator.update_cursor,
            "updates_per_source_training_epoch": UPDATES_PER_EPOCH,
            "formal_checkpoint_cadence_epochs": FORMAL_CHECKPOINT_EPOCHS,
            "formal_checkpoint_cadence_updates": FORMAL_CHECKPOINT_UPDATES,
            "config": self.config.to_payload(),
            "authority_digests": asdict(self.config.authority_digests),
            "provider_identity": self.provider_identity,
            "arm_order": list(ARMS),
            "route_order": list(ROUTES),
            "source_ablation_map": _source_map_payload(),
            "initialization_sha256": self.orchestrator.initialization_sha256,
            "models_and_optimizers": deepcopy(state["arms"]),
            "provider_sampler_state": deepcopy(state["provider_sampler_state"]),
            "consumed_file_order": deepcopy(state["file_order"]),
            "orchestrator_state": state,
        }

    def _write_current_exports(self, root: Path, epoch: int) -> tuple[dict[str, Any], str]:
        export_directory = root / "exports" / f"epoch-{epoch:04d}"
        if export_directory.exists() or export_directory.is_symlink():
            raise V023SourceTrainingRunnerError("checkpoint export directory already exists")
        export_directory.mkdir(mode=0o700)
        entries: list[dict[str, Any]] = []
        for index, arm in enumerate(ARMS):
            state = self.orchestrator.models[arm].checkpoint_state(
                update_count=self.orchestrator.update_cursor
            )
            if state.get("algorithm") != _current_model_algorithm():
                raise V023SourceTrainingRunnerError(
                    "D40 or another non-current model checkpoint was rejected"
                )
            filename = f"{index:02d}-{arm}.current-ee-axis-lcsrs-three-route.pt"
            destination = export_directory / filename
            digest = _atomic_write_once(destination, _torch_bytes(state))
            _write_digest_sidecar(destination, digest)
            entries.append(
                {
                    "arm": arm,
                    "path": str(destination.relative_to(root)),
                    "sha256": digest,
                    "algorithm": state["algorithm"],
                    "update_count": self.orchestrator.update_cursor,
                    "source_mapping": dict(SOURCE_MAP[arm]),
                }
            )
        manifest = {
            "schema": EXPORT_MANIFEST_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "epoch": epoch,
            "update_count": self.orchestrator.update_cursor,
            "arm_order": list(ARMS),
            "source_ablation_map": _source_map_payload(),
            "exports": entries,
        }
        manifest_digest = _atomic_json_once(_export_manifest_path(root, epoch), manifest)
        return manifest, manifest_digest

    def _write_checkpoint(self) -> dict[str, Any]:
        root = self._require_output_root()
        payload = self._checkpoint_payload()
        epoch = payload["epoch"]
        checkpoint_path = _checkpoint_path(root, epoch)
        checkpoint_digest = _atomic_write_once(checkpoint_path, _torch_bytes(payload))
        _write_digest_sidecar(checkpoint_path, checkpoint_digest)
        export_manifest, export_manifest_digest = self._write_current_exports(root, epoch)
        receipt = {
            "schema": CHECKPOINT_RECEIPT_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "epoch": epoch,
            "update_count": payload["update_count"],
            "checkpoint_path": str(checkpoint_path.relative_to(root)),
            "checkpoint_sha256": checkpoint_digest,
            "export_manifest_path": str(_export_manifest_path(root, epoch).relative_to(root)),
            "export_manifest_sha256": export_manifest_digest,
            "arm_order": list(ARMS),
            "exports": export_manifest["exports"],
        }
        _atomic_json_once(_checkpoint_receipt_path(root, epoch), receipt)
        return receipt

    def run_to_epoch(self, stop_epoch: int | None = None) -> dict[str, Any] | None:
        """Advance only full epochs, never writing a partial-epoch checkpoint.

        ``stop_epoch`` is a bounded interruption/resume seam for orchestration
        control.  It cannot exceed the frozen budget and only permits a whole
        epoch; production callers use ``run()`` to reach the frozen budget.
        """

        root = self._require_output_root()
        target = self.config.epoch_budget if stop_epoch is None else stop_epoch
        if type(target) is not int or not (self.completed_epochs <= target <= self.config.epoch_budget):
            raise V023SourceTrainingRunnerError("target epoch is outside the frozen budget")
        last_receipt: dict[str, Any] | None = None
        while self.completed_epochs < target:
            self._advance_complete_epoch()
            if self.completed_epochs % FORMAL_CHECKPOINT_EPOCHS == 0:
                last_receipt = self._write_checkpoint()
        if self.completed_epochs == self.config.epoch_budget:
            self._write_final_receipt(root)
        return last_receipt

    def _write_final_receipt(self, root: Path) -> None:
        destination = root / "canonical-receipt.json"
        if destination.exists() or destination.is_symlink():
            raise V023SourceTrainingRunnerError("canonical receipt already exists")
        completed = self.completed_epochs
        checkpoint_epochs = list(range(FORMAL_CHECKPOINT_EPOCHS, completed + 1, FORMAL_CHECKPOINT_EPOCHS))
        checkpoints = []
        for epoch in checkpoint_epochs:
            checkpoint_path = _checkpoint_path(root, epoch)
            checkpoints.append(
                {
                    "epoch": epoch,
                    "path": str(checkpoint_path.relative_to(root)),
                    "sha256": _verify_digest_sidecar(checkpoint_path),
                }
            )
        _atomic_json_once(
            destination,
            {
                "schema": RECEIPT_SCHEMA,
                "claim_ceiling": CLAIM_CEILING,
                "source_split": SOURCE_SPLIT,
                "epoch_budget": self.config.epoch_budget,
                "completed_epochs": completed,
                "completed_updates": self.orchestrator.update_cursor,
                "provider_identity": self.provider_identity,
                "initialization_sha256": self.orchestrator.initialization_sha256,
                "arm_order": list(ARMS),
                "route_order": list(ROUTES),
                "source_ablation_map": _source_map_payload(),
                "config": self.config.to_payload(),
                "authority_digests": asdict(self.config.authority_digests),
                "checkpoints": checkpoints,
            },
        )

    def run(self) -> dict[str, Any] | None:
        return self.run_to_epoch()

    @staticmethod
    def _read_json(path: Path, *, label: str) -> Mapping[str, Any]:
        if path.is_symlink() or not path.is_file():
            raise V023SourceTrainingRunnerError(f"{label} is missing: {path}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise V023SourceTrainingRunnerError(f"{label} is invalid") from error
        if not isinstance(value, Mapping):
            raise V023SourceTrainingRunnerError(f"{label} root must be a mapping")
        return value

    def _validate_export_receipt(self, root: Path, checkpoint: Mapping[str, Any]) -> None:
        epoch = checkpoint["epoch"]
        receipt = self._read_json(
            _checkpoint_receipt_path(root, epoch), label="checkpoint receipt"
        )
        expected_receipt_keys = {
            "schema", "claim_ceiling", "epoch", "update_count", "checkpoint_path",
            "checkpoint_sha256", "export_manifest_path", "export_manifest_sha256",
            "arm_order", "exports",
        }
        if set(receipt) != expected_receipt_keys or receipt["schema"] != CHECKPOINT_RECEIPT_SCHEMA:
            raise V023SourceTrainingRunnerError("checkpoint receipt schema drifted")
        if receipt["claim_ceiling"] != CLAIM_CEILING or receipt["epoch"] != epoch:
            raise V023SourceTrainingRunnerError("checkpoint receipt identity drifted")
        expected_update_count = epoch * UPDATES_PER_EPOCH
        if (
            receipt["update_count"] != checkpoint["update_count"]
            or receipt["update_count"] != expected_update_count
        ):
            raise V023SourceTrainingRunnerError("checkpoint receipt update count drifted")
        if receipt["arm_order"] != list(ARMS):
            raise V023SourceTrainingRunnerError("checkpoint receipt arm order drifted")
        checkpoint_path = _checkpoint_path(root, epoch)
        if receipt["checkpoint_path"] != str(checkpoint_path.relative_to(root)):
            raise V023SourceTrainingRunnerError("checkpoint receipt path drifted")
        if receipt["checkpoint_sha256"] != _verify_digest_sidecar(checkpoint_path):
            raise V023SourceTrainingRunnerError("checkpoint receipt digest drifted")
        manifest_path = _export_manifest_path(root, epoch)
        if receipt["export_manifest_path"] != str(manifest_path.relative_to(root)):
            raise V023SourceTrainingRunnerError("export manifest path drifted")
        if _file_sha256(manifest_path) != receipt["export_manifest_sha256"]:
            raise V023SourceTrainingRunnerError("export manifest digest drifted")
        manifest = self._read_json(manifest_path, label="export manifest")
        if manifest.get("claim_ceiling") != CLAIM_CEILING:
            raise V023SourceTrainingRunnerError("export manifest claim ceiling drifted")
        if (
            manifest.get("schema") != EXPORT_MANIFEST_SCHEMA
            or manifest.get("arm_order") != list(ARMS)
            or manifest.get("source_ablation_map") != _source_map_payload()
            or manifest.get("epoch") != epoch
            or manifest.get("update_count") != checkpoint["update_count"]
        ):
            raise V023SourceTrainingRunnerError("export manifest is not the exact current five-arm export")
        exports = manifest.get("exports")
        if not isinstance(exports, list) or len(exports) != len(ARMS):
            raise V023SourceTrainingRunnerError("five current model exports are incomplete")
        if exports != receipt["exports"]:
            raise V023SourceTrainingRunnerError("checkpoint receipt exports drifted")
        for expected_arm, export in zip(ARMS, exports, strict=True):
            if not isinstance(export, Mapping) or export.get("arm") != expected_arm:
                raise V023SourceTrainingRunnerError("five current model export order drifted")
            if export.get("algorithm") != _current_model_algorithm():
                raise V023SourceTrainingRunnerError("D40 or non-current model export rejected")
            if export.get("source_mapping") != dict(SOURCE_MAP[expected_arm]):
                raise V023SourceTrainingRunnerError("model export source mapping drifted")
            relative = export.get("path")
            if not isinstance(relative, str) or relative.startswith("/") or ".." in Path(relative).parts:
                raise V023SourceTrainingRunnerError("model export path is invalid")
            export_path = root / relative
            if _verify_digest_sidecar(export_path) != export.get("sha256"):
                raise V023SourceTrainingRunnerError("model export digest verification failed")
            exported_state = _read_torch(export_path)
            if exported_state.get("algorithm") != _current_model_algorithm():
                raise V023SourceTrainingRunnerError("exported model is not a current three-route checkpoint")

    def _validate_checkpoint(self, checkpoint: Mapping[str, Any]) -> None:
        expected_keys = {
            "schema", "claim_ceiling", "source_split", "runner_schema", "epoch",
            "update_count", "updates_per_source_training_epoch",
            "formal_checkpoint_cadence_epochs", "formal_checkpoint_cadence_updates",
            "config", "authority_digests", "provider_identity", "arm_order",
            "route_order", "source_ablation_map", "initialization_sha256",
            "models_and_optimizers", "provider_sampler_state", "consumed_file_order",
            "orchestrator_state",
        }
        if set(checkpoint) != expected_keys or checkpoint["schema"] != CHECKPOINT_SCHEMA:
            raise V023SourceTrainingRunnerError("unsupported runner checkpoint schema")
        if (
            checkpoint["claim_ceiling"] != CLAIM_CEILING
            or checkpoint["source_split"] != SOURCE_SPLIT
            or checkpoint["runner_schema"] != RUNNER_SCHEMA
        ):
            raise V023SourceTrainingRunnerError("TEST or checkpoint claim boundary rejected")
        if checkpoint["config"] != self.config.to_payload():
            raise V023SourceTrainingRunnerError("frozen runner config mismatch")
        if checkpoint["authority_digests"] != asdict(self.config.authority_digests):
            raise V023SourceTrainingRunnerError("checkpoint authority/input digest mismatch")
        if checkpoint["provider_identity"] != self.provider_identity:
            raise V023SourceTrainingRunnerError("checkpoint provider identity mismatch")
        if checkpoint["arm_order"] != list(ARMS) or checkpoint["route_order"] != list(ROUTES):
            raise V023SourceTrainingRunnerError("checkpoint arm or route order mismatch")
        if checkpoint["source_ablation_map"] != _source_map_payload():
            raise V023SourceTrainingRunnerError("checkpoint source map mismatch")
        epoch = checkpoint["epoch"]
        updates = checkpoint["update_count"]
        if (
            type(epoch) is not int
            or epoch <= 0
            or epoch % FORMAL_CHECKPOINT_EPOCHS != 0
            or epoch > self.config.epoch_budget
            or type(updates) is not int
            or updates != epoch * UPDATES_PER_EPOCH
        ):
            raise V023SourceTrainingRunnerError("partial, out-of-budget, or wrong-cadence checkpoint")
        if (
            checkpoint["updates_per_source_training_epoch"] != UPDATES_PER_EPOCH
            or checkpoint["formal_checkpoint_cadence_epochs"] != FORMAL_CHECKPOINT_EPOCHS
            or checkpoint["formal_checkpoint_cadence_updates"] != FORMAL_CHECKPOINT_UPDATES
        ):
            raise V023SourceTrainingRunnerError("checkpoint epoch/update cadence mismatch")
        state = checkpoint["orchestrator_state"]
        if not isinstance(state, Mapping):
            raise V023SourceTrainingRunnerError("orchestrator checkpoint state is missing")
        arms = checkpoint["models_and_optimizers"]
        if not isinstance(arms, Mapping) or tuple(arms) != ARMS:
            raise V023SourceTrainingRunnerError("checkpoint does not contain five ordered arm states")
        for arm in ARMS:
            arm_state = arms[arm]
            if not isinstance(arm_state, Mapping) or arm_state.get("algorithm") != _current_model_algorithm():
                raise V023SourceTrainingRunnerError(
                    "D40 or a non-current model checkpoint is rejected"
                )
        if (
            checkpoint["initialization_sha256"] != self.orchestrator.initialization_sha256
            or state.get("initialization", {}).get("sha256") != self.orchestrator.initialization_sha256
            or not _tree_equal(checkpoint["models_and_optimizers"], state.get("arms"))
            or not _tree_equal(checkpoint["provider_sampler_state"], state.get("provider_sampler_state"))
            or not _tree_equal(checkpoint["consumed_file_order"], state.get("file_order"))
            or state.get("update_cursor") != updates
            or state.get("next_route_index") != 0
        ):
            raise V023SourceTrainingRunnerError("checkpoint state binding drifted")

    def resume_from_checkpoint(self, checkpoint_path: str | Path) -> None:
        """Restore an authenticated, complete current checkpoint exactly once."""

        path = Path(checkpoint_path)
        root = path.parent.parent
        if path != _checkpoint_path(root, int(path.stem.split("-")[-1].split(".")[0])):
            raise V023SourceTrainingRunnerError("checkpoint path must use the canonical epoch filename")
        status = self._read_json(root / "canonical-status.json", label="canonical status")
        _verify_digest_sidecar(path)
        checkpoint = _read_torch(path)
        self._validate_checkpoint(checkpoint)
        if status != self._status_payload():
            raise V023SourceTrainingRunnerError("canonical status does not bind this runner")
        self._validate_export_receipt(root, checkpoint)
        try:
            self.orchestrator.load_checkpoint_state(deepcopy(checkpoint["orchestrator_state"]))
        except Exception as error:
            raise V023SourceTrainingRunnerError("exact orchestrator resume failed") from error
        if self.orchestrator.completed_source_training_epochs != checkpoint["epoch"]:
            raise V023SourceTrainingRunnerError("resumed epoch count drifted")
        self.output_root = root
        self._resumed = True


def _parse_factory_spec(specification: str) -> Callable[[], object]:
    module_name, separator, attribute = specification.partition(":")
    if not separator or not module_name or not attribute or "." in attribute:
        raise V023SourceTrainingRunnerError("provider factory must use module:callable")
    try:
        module = importlib.import_module(module_name)
    except Exception as error:
        raise V023SourceTrainingRunnerError("provider factory module cannot be imported") from error
    factory = getattr(module, attribute, None)
    if not callable(factory):
        raise V023SourceTrainingRunnerError("provider factory is not callable")
    return factory


def _load_model_config(path: str | Path) -> LCSRSThreeRouteConfig:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023SourceTrainingRunnerError("model config JSON is not a regular file")
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023SourceTrainingRunnerError("model config JSON is invalid") from error
    if (
        not isinstance(raw, Mapping)
        or not isinstance(raw.get("q1"), Mapping)
        or not isinstance(raw.get("q2"), Mapping)
        or ("q3" in raw and not isinstance(raw["q3"], Mapping))
    ):
        raise V023SourceTrainingRunnerError("model config JSON requires q1, q2 and optional q3 mappings")
    rest = {key: value for key, value in raw.items() if key not in {"q1", "q2", "q3", "q12"}}
    if "q3" in raw:
        rest["q3"] = LCSRSC3HeadConfig(**raw["q3"])
    try:
        return LCSRSThreeRouteConfig(
            q1=EEAxisActionSharedConfig(**raw["q1"]),
            q2=EEAxisV014HeadConfig(**raw["q2"]),
            **rest,
        )
    except (TypeError, ValueError) as error:
        raise V023SourceTrainingRunnerError("model config JSON is incompatible with current model") from error


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
    parser.add_argument("--later-budget-authority-sha256")
    parser.add_argument("--source-split", default=SOURCE_SPLIT)
    parser.add_argument(
        "--execute",
        action="store_true",
        required=True,
        help="required explicit acknowledgement; this command otherwise refuses to run",
    )
    return parser


def preflight_from_args(arguments: argparse.Namespace) -> V023FiveArmSourceTrainingRunner:
    """Construct but do not advance a strictly declared future run."""

    if not arguments.execute:
        raise V023SourceTrainingRunnerError("--execute is required")
    output_root = Path(arguments.output_root)
    if output_root.exists() or output_root.is_symlink():
        raise V023SourceTrainingRunnerError("output root must be explicit and absent")
    factory = _parse_factory_spec(arguments.provider_factory)
    provider = factory()
    model_config = _load_model_config(arguments.model_config_json)
    orchestrator_config = ORCHESTRATOR.V023FiveArmOrchestratorConfig.formal(
        model_config=model_config,
        train_seed=arguments.train_seed,
    )
    config = FrozenSourceTrainingConfig(
        epoch_budget=arguments.epochs,
        orchestrator_config=orchestrator_config,
        provider_factory_spec=arguments.provider_factory,
        authority_digests=RunAuthorityDigests(
            authority_sha256=arguments.authority_sha256,
            code_sha256=arguments.code_sha256,
            input_sha256=arguments.input_sha256,
        ),
        source_split=arguments.source_split,
        later_budget_authority_sha256=arguments.later_budget_authority_sha256,
    )
    return V023FiveArmSourceTrainingRunner(config, provider)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        arguments = parser.parse_args(argv)
        runner = preflight_from_args(arguments)
        runner.begin_new(arguments.output_root)
        runner.run()
    except V023SourceTrainingRunnerError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ARMS",
    "CHECKPOINT_SCHEMA",
    "CLAIM_CEILING",
    "FORMAL_CHECKPOINT_EPOCHS",
    "FORMAL_CHECKPOINT_UPDATES",
    "FrozenSourceTrainingConfig",
    "RUNNER_SCHEMA",
    "RunAuthorityDigests",
    "SOURCE_MAP",
    "SOURCE_SPLIT",
    "SUPPORTED_FROZEN_EPOCH_BUDGETS",
    "UPDATES_PER_EPOCH",
    "V023FiveArmSourceTrainingRunner",
    "V023SourceTrainingRunnerError",
    "build_parser",
    "main",
    "preflight_from_args",
]
