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
import math
import os
from pathlib import Path
import re
import secrets
import shutil
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
CHECKPOINT_SCHEMA = f"{RUNNER_SCHEMA}-checkpoint-v1.1"
CHECKPOINT_RECEIPT_SCHEMA = f"{RUNNER_SCHEMA}-checkpoint-receipt"
EXPORT_MANIFEST_SCHEMA = f"{RUNNER_SCHEMA}-three-model-exports"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_C1C2_SUCCESSOR_SOURCE_TRAINING_NO_C3_NO_TEST_NO_EFFICACY"
)
SOURCE_SPLIT = "SOURCE_TRAIN"
SUPPORTED_EPOCH_BUDGETS = (100,)
FORMAL_CHECKPOINT_EPOCHS = (0, 100)
NONFORMAL_CHECKPOINT_EPOCHS = tuple(range(0, 101, 10))
UPDATES_PER_EPOCH = 2
FORMAL_CHECKPOINT_UPDATES = 200
NONFORMAL_CHECKPOINT_UPDATES = 20
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


_CANONICAL_TYPE_KEY = "__runner_canonical_type__"


def _canonical_tree_payload(value: object) -> object:
    """Encode non-tensor state without pickle object-identity side effects."""

    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise V023TwoRouteSourceTrainingRunnerError(
                "canonical checkpoint mapping keys must be strings"
            )
        return {
            _CANONICAL_TYPE_KEY: "mapping",
            "items": [
                [key, _canonical_tree_payload(item)] for key, item in value.items()
            ],
        }
    if isinstance(value, list):
        return [_canonical_tree_payload(item) for item in value]
    if isinstance(value, tuple):
        return {
            _CANONICAL_TYPE_KEY: "tuple",
            "items": [_canonical_tree_payload(item) for item in value],
        }
    if isinstance(value, bytes):
        return {_CANONICAL_TYPE_KEY: "bytes", "hex": value.hex()}
    if isinstance(value, Path):
        return {_CANONICAL_TYPE_KEY: "path", "value": str(value)}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise V023TwoRouteSourceTrainingRunnerError(
        f"unsupported canonical checkpoint value: {type(value).__name__}"
    )


def _restore_canonical_tree(value: object) -> object:
    if isinstance(value, list):
        return [_restore_canonical_tree(item) for item in value]
    if isinstance(value, Mapping):
        marker = value.get(_CANONICAL_TYPE_KEY)
        if marker is None:
            raise V023TwoRouteSourceTrainingRunnerError(
                "canonical checkpoint mapping marker is missing"
            )
        if marker == "mapping" and set(value) == {_CANONICAL_TYPE_KEY, "items"}:
            items = value["items"]
            if not isinstance(items, list):
                raise V023TwoRouteSourceTrainingRunnerError(
                    "canonical mapping payload is malformed"
                )
            restored: dict[str, object] = {}
            for pair in items:
                if (
                    not isinstance(pair, list)
                    or len(pair) != 2
                    or not isinstance(pair[0], str)
                    or pair[0] in restored
                ):
                    raise V023TwoRouteSourceTrainingRunnerError(
                        "canonical mapping payload is malformed"
                    )
                restored[pair[0]] = _restore_canonical_tree(pair[1])
            return restored
        if marker == "tuple" and set(value) == {_CANONICAL_TYPE_KEY, "items"}:
            items = value["items"]
            if not isinstance(items, list):
                raise V023TwoRouteSourceTrainingRunnerError(
                    "canonical tuple payload is malformed"
                )
            return tuple(_restore_canonical_tree(item) for item in items)
        if marker == "bytes" and set(value) == {_CANONICAL_TYPE_KEY, "hex"}:
            encoded = value["hex"]
            if not isinstance(encoded, str):
                raise V023TwoRouteSourceTrainingRunnerError(
                    "canonical bytes payload is malformed"
                )
            try:
                return bytes.fromhex(encoded)
            except ValueError as error:
                raise V023TwoRouteSourceTrainingRunnerError(
                    "canonical bytes payload is malformed"
                ) from error
        if marker == "path" and set(value) == {_CANONICAL_TYPE_KEY, "value"}:
            encoded = value["value"]
            if not isinstance(encoded, str):
                raise V023TwoRouteSourceTrainingRunnerError(
                    "canonical path payload is malformed"
                )
            return Path(encoded)
        raise V023TwoRouteSourceTrainingRunnerError(
            "canonical checkpoint type marker is malformed"
        )
    return value


def _canonical_tree_bytes(value: object) -> bytes:
    return _canonical_json_bytes(_canonical_tree_payload(value))


def _read_canonical_tree(value: object, *, field: str) -> object:
    if not isinstance(value, bytes):
        raise V023TwoRouteSourceTrainingRunnerError(
            f"{field} must be canonical JSON bytes"
        )
    try:
        encoded = json.loads(value.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise V023TwoRouteSourceTrainingRunnerError(
            f"{field} canonical JSON is invalid"
        ) from error
    if _canonical_json_bytes(encoded) != value:
        raise V023TwoRouteSourceTrainingRunnerError(
            f"{field} canonical JSON bytes are non-canonical"
        )
    return _restore_canonical_tree(encoded)


def decode_checkpoint_ledger(checkpoint: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = _read_canonical_tree(
        checkpoint.get("update_ledger_rows"), field="update ledger rows"
    )
    if not isinstance(rows, list):
        raise V023TwoRouteSourceTrainingRunnerError(
            "update ledger rows canonical payload must be a list"
        )
    return rows


def decode_checkpoint_orchestrator_state(
    checkpoint: Mapping[str, Any],
) -> dict[str, Any]:
    state = _read_canonical_tree(
        checkpoint.get("orchestrator_state"), field="orchestrator state"
    )
    if not isinstance(state, dict) or "arms" in state:
        raise V023TwoRouteSourceTrainingRunnerError(
            "orchestrator canonical payload is malformed"
        )
    state["arms"] = checkpoint.get("models_and_optimizers")
    return state


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
        if path.exists() or path.is_symlink():
            raise V023TwoRouteSourceTrainingRunnerError(
                f"refusing to overwrite artifact: {path}"
            )
        os.rename(temporary, path)
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
        expected_cadence = (
            FORMAL_CHECKPOINT_UPDATES
            if self.orchestrator_config.formal_use
            else NONFORMAL_CHECKPOINT_UPDATES
        )
        if self.orchestrator_config.checkpoint_cadence_updates != expected_cadence:
            raise V023TwoRouteSourceTrainingRunnerError(
                "formal cadence must be 200 updates and non-formal cadence 20 updates"
            )
        if (
            not self.orchestrator_config.formal_use
            and "REHEARSAL-NONFORMAL" not in self.orchestrator_config.lineage.upper()
        ):
            raise V023TwoRouteSourceTrainingRunnerError(
                "non-formal runner lineage must be REHEARSAL-NONFORMAL"
            )
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
        self.update_ledger_rows: list[dict[str, Any]] = []

    @property
    def formal(self) -> bool:
        return self.config.orchestrator_config.formal_use

    @property
    def checkpoint_epochs(self) -> tuple[int, ...]:
        return FORMAL_CHECKPOINT_EPOCHS if self.formal else NONFORMAL_CHECKPOINT_EPOCHS

    @property
    def checkpoint_cadence_updates(self) -> int:
        return FORMAL_CHECKPOINT_UPDATES if self.formal else NONFORMAL_CHECKPOINT_UPDATES

    @property
    def completed_epochs(self) -> int:
        return self.orchestrator.completed_source_training_epochs

    def _status_payload(self) -> dict[str, Any]:
        return {
            "schema": STATUS_SCHEMA,
            "formal": self.formal,
            "claim_ceiling": CLAIM_CEILING,
            "source_split": SOURCE_SPLIT,
            "config": self.config.to_payload(),
            "provider_identity": self.provider_identity,
            "arm_order": list(ARMS),
            "route_order": list(ROUTES),
            "source_ablation_map": _source_map_payload(),
            "initialization_sha256": self.orchestrator.initialization_sha256,
            "formal_export_epochs": list(FORMAL_CHECKPOINT_EPOCHS),
            "checkpoint_epochs": list(self.checkpoint_epochs),
            "checkpoint_cadence_updates": self.checkpoint_cadence_updates,
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
        if (not self.formal) != ("REHEARSAL-NONFORMAL" in root.name.upper()):
            raise V023TwoRouteSourceTrainingRunnerError(
                "non-formal output basename must contain REHEARSAL-NONFORMAL"
            )
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
        if epoch not in self.checkpoint_epochs or epoch != self.completed_epochs:
            raise V023TwoRouteSourceTrainingRunnerError("checkpoint epoch is not authorized")
        updates = epoch * 2
        if self.orchestrator.update_cursor != updates or self.orchestrator.next_route != "C1":
            raise V023TwoRouteSourceTrainingRunnerError("checkpoint contains a partial epoch")
        return {
            "schema": CHECKPOINT_SCHEMA,
            "formal": self.formal,
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
            "checkpoint_cadence_updates": self.checkpoint_cadence_updates,
            "update_ledger_rows": _canonical_tree_bytes(self.update_ledger_rows),
            "models_and_optimizers": deepcopy(state["arms"]),
            "provider_sampler_state": _canonical_tree_bytes(
                state["provider_sampler_state"]
            ),
            "consumed_file_order": _canonical_tree_bytes(state["file_order"]),
            "orchestrator_state": _canonical_tree_bytes(
                {key: value for key, value in state.items() if key != "arms"}
            ),
        }

    @staticmethod
    def _checkpoint_prefix_paths(root: Path, epoch: int) -> tuple[Path, ...]:
        checkpoint = _checkpoint_path(root, epoch)
        return (
            root / "exports" / f"epoch-{epoch:04d}",
            _export_manifest_path(root, epoch),
            _checkpoint_receipt_path(root, epoch),
            checkpoint,
            checkpoint.with_suffix(checkpoint.suffix + ".sha256"),
        )

    @classmethod
    def _has_complete_sealed_prefix(cls, root: Path, epoch: int) -> bool:
        export_dir, manifest, receipt, checkpoint, sidecar = cls._checkpoint_prefix_paths(
            root, epoch
        )
        for path in (export_dir, manifest, receipt, checkpoint, sidecar):
            if path.is_symlink():
                raise V023TwoRouteSourceTrainingRunnerError(
                    "checkpoint publication prefix contains a symlink"
                )
        present = (
            export_dir.is_dir()
            and manifest.is_file()
            and receipt.is_file()
            and checkpoint.is_file()
            and sidecar.is_file()
        )
        if sidecar.exists():
            _verify_sidecar(checkpoint)
        return present

    @classmethod
    def _clear_unsealed_checkpoint_prefix(cls, root: Path, epoch: int) -> None:
        if cls._has_complete_sealed_prefix(root, epoch):
            raise V023TwoRouteSourceTrainingRunnerError(
                "refusing to replace a sealed checkpoint epoch"
            )
        _, _, receipt, checkpoint, sidecar = cls._checkpoint_prefix_paths(root, epoch)
        for path in (sidecar, checkpoint, receipt):
            if path.is_symlink() or (path.exists() and not path.is_file()):
                raise V023TwoRouteSourceTrainingRunnerError(
                    "unsealed checkpoint prefix contains a non-file artifact"
                )
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def _write_exports(self, root: Path, epoch: int) -> tuple[list[dict[str, Any]], str]:
        directory = root / "exports" / f"epoch-{epoch:04d}"
        manifest_path = _export_manifest_path(root, epoch)
        if self._has_complete_sealed_prefix(root, epoch):
            raise V023TwoRouteSourceTrainingRunnerError(
                "refusing to replace a sealed epoch export directory"
            )
        if directory.is_symlink() or manifest_path.is_symlink():
            raise V023TwoRouteSourceTrainingRunnerError(
                "unsealed export prefix contains a symlink"
            )
        if directory.exists() and not directory.is_dir():
            raise V023TwoRouteSourceTrainingRunnerError(
                "unsealed export path is not a directory"
            )
        if manifest_path.exists() and not manifest_path.is_file():
            raise V023TwoRouteSourceTrainingRunnerError(
                "unsealed export manifest is not a file"
            )
        if directory.is_dir():
            shutil.rmtree(directory)
        try:
            manifest_path.unlink()
        except FileNotFoundError:
            pass
        for stale in directory.parent.glob(f".{directory.name}.*.tmp"):
            if stale.is_symlink() or not stale.is_dir():
                raise V023TwoRouteSourceTrainingRunnerError(
                    "unsealed temporary export path is invalid"
                )
            shutil.rmtree(stale)
        temporary_directory = (
            directory.parent / f".{directory.name}.{secrets.token_hex(16)}.tmp"
        )
        temporary_directory.mkdir(mode=0o700)
        entries = []
        counts = self.orchestrator.route_update_counts
        try:
            for index, arm in enumerate(ARMS):
                state = self.orchestrator.models[arm].checkpoint_state(
                    update_count=self.orchestrator.update_cursor,
                    route_update_counts=counts,
                )
                filename = f"{index:02d}-{arm}.current-ee-axis-two-route.pt"
                temporary_path = temporary_directory / filename
                final_path = directory / filename
                digest = _atomic_write_once(temporary_path, _torch_bytes(state))
                _write_sidecar(temporary_path, digest)
                entries.append(
                    {
                        "arm": arm,
                        "path": str(final_path.relative_to(root)),
                        "sha256": digest,
                        "schema": TWO_ROUTE_CHECKPOINT_SCHEMA,
                        "algorithm": TWO_ROUTE_ALGORITHM,
                        "source_mapping": list(SOURCE_MAP[arm]),
                        "update_count": self.orchestrator.update_cursor,
                    }
                )
            os.rename(temporary_directory, directory)
        finally:
            if temporary_directory.is_dir():
                shutil.rmtree(temporary_directory)
        manifest = {
            "schema": EXPORT_MANIFEST_SCHEMA,
            "formal": self.formal,
            "claim_ceiling": CLAIM_CEILING,
            "epoch": epoch,
            "update_count": self.orchestrator.update_cursor,
            "arm_order": list(ARMS),
            "route_order": list(ROUTES),
            "source_ablation_map": _source_map_payload(),
            "exports": entries,
        }
        return entries, _atomic_json_once(manifest_path, manifest)

    def _write_checkpoint(self, epoch: int) -> dict[str, Any]:
        root = self._require_root()
        payload = self._checkpoint_payload(epoch)
        path = _checkpoint_path(root, epoch)
        checkpoint_bytes = _torch_bytes(payload)
        digest = sha256(checkpoint_bytes).hexdigest()
        self._clear_unsealed_checkpoint_prefix(root, epoch)
        exports, manifest_digest = self._write_exports(root, epoch)
        receipt = {
            "schema": CHECKPOINT_RECEIPT_SCHEMA,
            "formal": self.formal,
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
        _atomic_write_once(path, checkpoint_bytes)
        _write_sidecar(path, digest)
        return receipt

    @staticmethod
    def _ledger_row(receipt: object) -> dict[str, Any]:
        cursor = getattr(receipt, "update_cursor")
        updates = []
        for update in getattr(receipt, "arm_updates"):
            metrics = {
                key: value
                for key, value in update.update.items()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            }
            if "loss" not in metrics or any(
                not math.isfinite(float(value)) for value in metrics.values()
            ):
                raise V023TwoRouteSourceTrainingRunnerError(
                    f"update {cursor} has a missing or non-finite loss/metric"
                )
            updates.append(
                {
                    "arm": update.arm,
                    "route": update.route,
                    "source": update.source,
                    "file_id": update.file_id,
                    "metrics": metrics,
                }
            )
        return {
            "update_cursor": cursor,
            "route": getattr(receipt, "route"),
            "source_files": [list(item) for item in receipt.source_files],
            "arm_updates": updates,
        }

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
            self.update_ledger_rows.extend(self._ledger_row(item) for item in rounds)
            if self.completed_epochs in self.checkpoint_epochs:
                receipt = self._write_checkpoint(self.completed_epochs)
        if self.completed_epochs == 100:
            integrity = self._verify_epoch_100_integrity()
            self._write_final_receipt(integrity)
        return receipt

    def _write_final_receipt(self, integrity: Mapping[str, Any]) -> None:
        root = self._require_root()
        destination = root / "canonical-receipt.json"
        checkpoints = []
        for epoch in self.checkpoint_epochs:
            path = _checkpoint_path(root, epoch)
            checkpoints.append(
                {"epoch": epoch, "path": str(path.relative_to(root)), "sha256": _verify_sidecar(path)}
            )
        payload = {
            "schema": RECEIPT_SCHEMA,
            "formal": self.formal,
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
        }
        if destination.exists() or destination.is_symlink():
            if destination.is_symlink() or self._read_json(destination) != payload:
                raise V023TwoRouteSourceTrainingRunnerError(
                    "canonical receipt already exists with different content"
                )
            return
        _atomic_json_once(destination, payload)

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
            "schema", "formal", "claim_ceiling", "source_split", "epoch", "update_count", "config",
            "authority_digests", "provider_identity", "arm_order", "route_order",
            "source_ablation_map", "initialization_sha256", "runner_schema",
            "updates_per_source_training_epoch", "formal_checkpoint_cadence_updates",
            "checkpoint_cadence_updates", "update_ledger_rows",
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
            or checkpoint["formal"] is not self.formal
            or checkpoint["checkpoint_cadence_updates"] != self.checkpoint_cadence_updates
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
        if epoch not in self.checkpoint_epochs or checkpoint["update_count"] != epoch * 2:
            raise V023TwoRouteSourceTrainingRunnerError("checkpoint cadence is invalid")
        state = decode_checkpoint_orchestrator_state(checkpoint)
        sampler = _read_canonical_tree(
            checkpoint["provider_sampler_state"], field="provider sampler state"
        )
        file_order = _read_canonical_tree(
            checkpoint["consumed_file_order"], field="consumed file order"
        )
        ledger_rows = decode_checkpoint_ledger(checkpoint)
        if (
            checkpoint["initialization_sha256"] != self.orchestrator.initialization_sha256
            or not isinstance(state, Mapping)
            or state.get("update_cursor") != epoch * 2
            or state.get("next_route_index") != 0
            or state.get("arm_order") != list(ARMS)
            or state.get("route_order") != list(ROUTES)
            or not _tree_equal(checkpoint["models_and_optimizers"], state.get("arms"))
            or not _tree_equal(sampler, state.get("provider_sampler_state"))
            or not _tree_equal(file_order, state.get("file_order"))
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
                or arm_state.get("formal") is not self.formal
                or arm_state.get("train_seed") != FORMAL_TRAIN_SEED
                or arm_state.get("config") != asdict(self.config.orchestrator_config.model_config)
            ):
                raise V023TwoRouteSourceTrainingRunnerError(
                    "checkpoint arm config/update binding drifted"
                )
        self._validate_consumed_history(
            file_order, sampler,
            updates=epoch * UPDATES_PER_EPOCH,
        )
        self._validate_ledger_rows(
            ledger_rows, updates=epoch * UPDATES_PER_EPOCH
        )

    def _validate_ledger_rows(self, rows: object, *, updates: int) -> None:
        if not isinstance(rows, list) or len(rows) != updates:
            raise V023TwoRouteSourceTrainingRunnerError(
                "checkpoint update ledger is incomplete"
            )
        for cursor, row in enumerate(rows):
            if (
                not isinstance(row, Mapping)
                or row.get("update_cursor") != cursor
                or row.get("route") != ROUTES[cursor % 2]
            ):
                raise V023TwoRouteSourceTrainingRunnerError(
                    "checkpoint update ledger order drifted"
                )
            arm_updates = row.get("arm_updates")
            if (
                not isinstance(arm_updates, list)
                or [item.get("arm") for item in arm_updates] != list(ARMS)
            ):
                raise V023TwoRouteSourceTrainingRunnerError(
                    "checkpoint update ledger arm order drifted"
                )
            source_files = row.get("source_files")
            if not isinstance(source_files, list):
                raise V023TwoRouteSourceTrainingRunnerError(
                    "checkpoint update ledger sources drifted"
                )
            source_by_name = dict(source_files)
            for item in arm_updates:
                arm = item.get("arm")
                metrics = item.get("metrics")
                if (
                    item.get("route") != row["route"]
                    or arm not in SOURCE_MAP
                    or item.get("source") != SOURCE_MAP[arm][cursor % 2]
                    or item.get("file_id") != source_by_name.get(item.get("source"))
                    or not isinstance(metrics, Mapping)
                    or "loss" not in metrics
                    or any(
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(float(value))
                        for value in metrics.values()
                    )
                ):
                    raise V023TwoRouteSourceTrainingRunnerError(
                        "checkpoint update ledger binding drifted"
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
            "schema", "formal", "claim_ceiling", "epoch", "update_count", "checkpoint_path",
            "checkpoint_sha256", "export_manifest_path", "export_manifest_sha256",
            "arm_order", "exports",
        }
        if (
            set(receipt) != expected_receipt_fields
            or receipt.get("schema") != CHECKPOINT_RECEIPT_SCHEMA
            or receipt.get("formal") is not self.formal
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
            or manifest.get("formal") is not self.formal
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
                or state.get("formal") is not self.formal
                or state.get("train_seed") != FORMAL_TRAIN_SEED
                or state.get("config") != asdict(self.config.orchestrator_config.model_config)
                or not _tree_equal(state, checkpoint_arm)
            ):
                raise V023TwoRouteSourceTrainingRunnerError("export is not a two-route model")
            independent = EEAxisTwoRouteModel(
                self.config.orchestrator_config.model_config,
                train_seed=FORMAL_TRAIN_SEED,
                formal=self.formal,
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
        checkpoint_state = decode_checkpoint_orchestrator_state(checkpoint)
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
        if not _tree_equal(restored, checkpoint_state):
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
        checkpoint_state = decode_checkpoint_orchestrator_state(checkpoint)
        try:
            self.orchestrator.load_checkpoint_state(deepcopy(checkpoint_state))
        except Exception as error:
            raise V023TwoRouteSourceTrainingRunnerError("exact orchestrator resume failed") from error
        if not _tree_equal(
            self.orchestrator.checkpoint_state(), checkpoint_state
        ):
            raise V023TwoRouteSourceTrainingRunnerError(
                "installed orchestrator state is not exact"
            )
        self.update_ledger_rows = deepcopy(decode_checkpoint_ledger(checkpoint))
        self.output_root = root

    def resume_from_root(self, output_root: str | Path) -> Path:
        root = Path(output_root)
        _reject_test(root, field="resume output path")
        if (not self.formal) != ("REHEARSAL-NONFORMAL" in root.name.upper()):
            raise V023TwoRouteSourceTrainingRunnerError(
                "resume root formal mode/name mismatch"
            )
        if root.is_symlink() or not root.is_dir():
            raise V023TwoRouteSourceTrainingRunnerError(
                "resume output root must be an existing non-symlink directory"
            )
        allowed_names = {
            _checkpoint_path(root, epoch).name for epoch in self.checkpoint_epochs
        }
        observed = list((root / "checkpoints").glob("*.runner.pt"))
        if any(
            path.name not in allowed_names or path.is_symlink() or not path.is_file()
            for path in observed
        ):
            raise V023TwoRouteSourceTrainingRunnerError(
                "resume output root contains an unauthorized checkpoint"
            )
        sealed = [
            epoch
            for epoch in self.checkpoint_epochs
            if self._has_complete_sealed_prefix(root, epoch)
        ]
        if not sealed:
            raise V023TwoRouteSourceTrainingRunnerError(
                "resume output root has no fully sealed authorized checkpoint"
            )
        path = _checkpoint_path(root, max(sealed))
        self.resume_from_checkpoint(path)
        return path


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
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output-root")
    destination.add_argument("--resume", metavar="OUTPUT_ROOT")
    parser.add_argument("--epochs", required=True, type=int)
    parser.add_argument("--provider-factory", required=True, metavar="MODULE:CALLABLE")
    parser.add_argument("--model-config-json", required=True)
    parser.add_argument("--train-seed", required=True, type=int)
    parser.add_argument("--authority-sha256", required=True)
    parser.add_argument("--code-sha256", required=True)
    parser.add_argument("--input-sha256", required=True)
    parser.add_argument("--nonformal", action="store_true")
    parser.add_argument("--execute", action="store_true", required=True)
    return parser


def preflight_from_args(arguments: argparse.Namespace) -> V023TwoRouteSourceTrainingRunner:
    if not arguments.execute:
        raise V023TwoRouteSourceTrainingRunnerError("--execute is required")
    resume_root = getattr(arguments, "resume", None)
    output_value = resume_root or getattr(arguments, "output_root", None)
    if output_value is None:
        raise V023TwoRouteSourceTrainingRunnerError(
            "exactly one of --output-root or --resume is required"
        )
    output_root = Path(output_value)
    _reject_test(output_root, field="output path")
    nonformal = bool(getattr(arguments, "nonformal", False))
    if nonformal != ("REHEARSAL-NONFORMAL" in output_root.name.upper()):
        raise V023TwoRouteSourceTrainingRunnerError(
            "--nonformal requires an output-root basename containing REHEARSAL-NONFORMAL"
        )
    if resume_root is None:
        if output_root.exists() or output_root.is_symlink():
            raise V023TwoRouteSourceTrainingRunnerError("output root must be absent")
    elif output_root.is_symlink() or not output_root.is_dir():
        raise V023TwoRouteSourceTrainingRunnerError(
            "resume output root must be an existing non-symlink directory"
        )
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
        orchestrator_config=(
            V023TwoRouteOrchestratorConfig(
                model_config=model_config,
                train_seed=arguments.train_seed,
                model_config_sha256=FROZEN_MODEL_CONFIG_SHA256,
                lineage="v023-c1c2-successor-REHEARSAL-NONFORMAL",
                checkpoint_cadence_updates=NONFORMAL_CHECKPOINT_UPDATES,
                formal_use=False,
            )
            if nonformal
            else V023TwoRouteOrchestratorConfig.formal(
                model_config=model_config,
                train_seed=arguments.train_seed,
                model_config_sha256=FROZEN_MODEL_CONFIG_SHA256,
            )
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
        if arguments.resume:
            runner.resume_from_root(arguments.resume)
        else:
            runner.begin_new(arguments.output_root)
        runner.run()
    except V023TwoRouteSourceTrainingRunnerError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ARMS", "CHECKPOINT_SCHEMA", "CLAIM_CEILING", "FORMAL_CHECKPOINT_EPOCHS",
    "FORMAL_CHECKPOINT_UPDATES", "NONFORMAL_CHECKPOINT_EPOCHS",
    "NONFORMAL_CHECKPOINT_UPDATES", "FrozenSourceTrainingConfig", "ROUTES", "RUNNER_SCHEMA",
    "RunAuthorityDigests", "SOURCE_MAP", "SOURCE_SPLIT", "SUPPORTED_EPOCH_BUDGETS",
    "UPDATES_PER_EPOCH", "V023TwoRouteSourceTrainingRunner",
    "EPOCH_100_INTEGRITY_DECISION", "FORMAL_TRAIN_SEED",
    "FROZEN_MODEL_CONFIG_SHA256",
    "V023TwoRouteSourceTrainingRunnerError", "build_parser", "main", "preflight_from_args",
    "decode_checkpoint_ledger", "decode_checkpoint_orchestrator_state",
]
