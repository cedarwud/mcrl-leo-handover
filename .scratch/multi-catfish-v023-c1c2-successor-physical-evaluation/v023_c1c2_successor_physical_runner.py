#!/usr/bin/env python3
"""Four-arm fixed-policy physical evaluation for the V0.23 C1/C2 successor.

The module is an evaluation seam.  It contains no optimizer, replay buffer,
episode learner, TEST path, Q3/C3 carrier, server launcher, or default run.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import copy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, TypeAlias

import numpy as np

try:
    import torch
except ImportError:  # pragma: no cover - project train extra is required at runtime
    torch = None  # type: ignore[assignment]


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE_RUNNER = REPO / ".scratch" / "multi-catfish-v023-two-route-source-training-runner"
BASELINE_ADAPTER = REPO / ".scratch" / "multi-catfish-v023-baseline-adapter"
for _path in (HERE, REPO, REPO / "src", SOURCE_RUNNER, BASELINE_ADAPTER):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from build_v023_c1c2_successor_world_plan import (  # noqa: E402
    ARMS,
    EPISODES as PLAN_EPISODES,
    FIELD_COMPONENT,
    read_world_plan,
)
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_ops3_live import (  # noqa: E402
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_v014_q2_state import (  # noqa: E402
    encode_ee_axis_v014_q2_states,
)
from mcrl.runtime.trainer_env import TrainerEnvironment  # noqa: E402
from ee_axis_two_route_model import deploy_q12_action  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1"
RECEIPT_SCHEMA = f"{SCHEMA}-episode-receipt"
CHECKPOINT_SCHEMA = f"{SCHEMA}-checkpoint"
RUNG_SCHEMA = f"{SCHEMA}-rung-receipt"
RESULT_SCHEMA = f"{SCHEMA}-result"
CONTINUATION_RESULT_SCHEMA = f"{SCHEMA}-continuation-result"
INTEGRITY_SCHEMA = f"{SCHEMA}-integrity-stop"
CONTINUATION_AUTHORITY_SCHEMA = f"{SCHEMA}-continuation-authority-v1"
REPAIR_AUTHORITY_SCHEMA = f"{SCHEMA}-repair-authority-v1"
TWO_ROUTE_CHECKPOINT_SCHEMA = (
    "multi-catfish-mcrl-v023-c1c2-successor-two-route-checkpoint-v1"
)
STATUS = "FIXED_POLICY_EVALUATION"
SPLIT = "TRAIN"
LEARNED_ARMS = ARMS[:3]
ROUTES = ("C1", "C2")
CHECKPOINT_EVERY = 100
PAUSE_BOUNDARIES = (100, 500, 1500, 3000)
TERMINAL_BOUNDARIES = (3000, 9000)
USERS = 100
STEPS = 10
SERVICE_MARGIN = 0.001
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_C1C2_SUCCESSOR_PHYSICAL_EVALUATION_"
    "NO_C3_NO_TEST_NO_EFFICACY"
)
HELD = "C1C2_DEVELOPMENT_PREDICTION_HELD"
FALSIFIED = "C1C2_DEVELOPMENT_PREDICTION_FALSIFIED"
INTEGRITY_STOP = "STOP_PHYSICAL_EVALUATION_INTEGRITY"
BASELINE_CHECKPOINT_SHA256 = (
    "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
)
HELD_TOKEN_SHA256 = hashlib.sha256(HELD.encode("ascii")).hexdigest()


class C1C2PhysicalError(RuntimeError):
    """A fixed-policy evaluation integrity boundary failed."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C1C2PhysicalError(f"{field} must be a lowercase SHA-256")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 1:
        raise C1C2PhysicalError(f"{field} must be a positive exact integer")
    return value


def _utc_timestamp(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise C1C2PhysicalError(f"{field} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise C1C2PhysicalError(f"{field} must be an ISO-8601 UTC timestamp") from error
    if parsed.tzinfo != timezone.utc:
        raise C1C2PhysicalError(f"{field} must be UTC")
    return parsed


def _contains_c3(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key).upper() in {"C3", "Q3"} or _contains_c3(child)
            for key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_c3(child) for child in value)
    return isinstance(value, str) and value.upper() in {"C3", "Q3"}


def file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise C1C2PhysicalError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    try:
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise C1C2PhysicalError(f"cannot read file: {source}") from error
    return digest.hexdigest()


def _jsonable(value: object) -> object:
    if isinstance(value, np.ndarray):
        return {
            "__ndarray__": True,
            "dtype": value.dtype.str,
            "shape": list(value.shape),
            "values": [_jsonable(child) for child in value.tolist()],
        }
    if isinstance(value, np.generic):
        return value.item()
    if torch is not None and isinstance(value, torch.Tensor):
        return value.detach().cpu().tolist()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(child) for child in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise C1C2PhysicalError("canonical JSON cannot contain non-finite values")
        return value
    raise C1C2PhysicalError(f"unsupported canonical value: {type(value).__name__}")


def _restore_jsonable(value: object) -> object:
    if isinstance(value, list):
        return [_restore_jsonable(child) for child in value]
    if isinstance(value, Mapping):
        if value.get("__ndarray__") is True:
            try:
                return np.asarray(
                    _restore_jsonable(value["values"]),
                    dtype=np.dtype(str(value["dtype"])),
                ).reshape(tuple(int(item) for item in value["shape"]))
            except (KeyError, TypeError, ValueError) as error:
                raise C1C2PhysicalError("encoded ndarray resume state is malformed") from error
        return {key: _restore_jsonable(child) for key, child in value.items()}
    return value


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            _jsonable(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise C1C2PhysicalError("payload is not finite canonical JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _array_sha256(value: object) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _parameter_sha256(network: Any) -> str:
    state = getattr(network, "state_dict", None)
    if not callable(state):
        raise C1C2PhysicalError("frozen network has no state_dict")
    digest = hashlib.sha256()
    try:
        for name, value in state().items():
            tensor = value.detach().cpu().contiguous()
            digest.update(str(name).encode("utf-8"))
            digest.update(str(tensor.dtype).encode("ascii"))
            digest.update(repr(tuple(tensor.shape)).encode("ascii"))
            digest.update(tensor.numpy().tobytes(order="C"))
    except (AttributeError, TypeError, ValueError, RuntimeError) as error:
        raise C1C2PhysicalError("cannot hash frozen network parameters") from error
    return digest.hexdigest()


def _write_once(path: Path, payload: object) -> None:
    if path.exists() or path.is_symlink():
        raise C1C2PhysicalError(f"refusing to overwrite output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise C1C2PhysicalError(f"output parent is not a directory: {path.parent}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, path)
        except FileExistsError as error:
            raise C1C2PhysicalError(f"output was published concurrently: {path}") from error
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise C1C2PhysicalError(f"{label} is missing or symlinked: {path}")
    try:
        payload = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise C1C2PhysicalError(f"{label} is not ASCII JSON: {path}") from error
    if not isinstance(payload, dict):
        raise C1C2PhysicalError(f"{label} must be a JSON object")
    return payload


def _read_sealed_json(
    path: str | Path, *, expected_sha256: str, label: str
) -> tuple[dict[str, Any], str]:
    """Read a file whose bytes are bound both by its caller and sidecar."""

    source = Path(path)
    expected = _digest(expected_sha256, field=f"{label}_sha256")
    actual = file_sha256(source)
    if actual != expected:
        raise C1C2PhysicalError(f"{label} bytes disagree with bound digest")
    sidecar = source.with_name(source.name + ".sha256")
    if sidecar.is_symlink() or not sidecar.is_file():
        raise C1C2PhysicalError(f"{label} digest sidecar is missing")
    try:
        raw = sidecar.read_text(encoding="ascii")
    except (OSError, UnicodeError) as error:
        raise C1C2PhysicalError(f"{label} digest sidecar is unreadable") from error
    if raw not in {f"{actual}\n", f"{actual}  {source.name}\n"}:
        raise C1C2PhysicalError(f"{label} digest sidecar disagrees")
    return _read_json(source, label=label), actual


def _bound_file(record: object, *, base: Path, label: str) -> tuple[Path, str]:
    if not isinstance(record, Mapping):
        raise C1C2PhysicalError(f"{label} binding is missing")
    raw_path = record.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise C1C2PhysicalError(f"{label}.path is missing")
    path = Path(raw_path)
    if not path.is_absolute():
        path = base / path
    expected = _digest(record.get("sha256"), field=f"{label}.sha256")
    if file_sha256(path) != expected:
        raise C1C2PhysicalError(f"{label} bytes disagree with binding")
    return path, expected


def authenticate_runtime_admission(
    path: str | Path,
    *,
    expected_sha256: str,
    expected_statuses: Sequence[str],
) -> dict[str, Any]:
    """Authenticate frozen PREREG/TLE/configuration and predecessor PASS inputs."""

    source = Path(path)
    payload, digest = _read_sealed_json(
        source, expected_sha256=expected_sha256, label="runtime admission"
    )
    if (
        payload.get("schema") != f"{SCHEMA}-runtime-admission-v1"
        or payload.get("status") != "FORMAL_RUNTIME_ADMITTED"
        or payload.get("split") != SPLIT
    ):
        raise C1C2PhysicalError("runtime admission identity drifted")
    base = source.parent
    for name in ("prereg", "tle_manifest", "execution_configuration"):
        _bound_file(payload.get(name), base=base, label=name)
    receipts = payload.get("predecessor_pass_receipts")
    if not isinstance(receipts, list) or len(receipts) != len(expected_statuses):
        raise C1C2PhysicalError("runtime admission predecessor PASS coverage drifted")
    observed: list[str] = []
    for index, record in enumerate(receipts):
        receipt_path, _ = _bound_file(
            record, base=base, label=f"predecessor_pass_receipts[{index}]"
        )
        receipt = _read_json(receipt_path, label="predecessor PASS receipt")
        status = receipt.get("status", receipt.get("overall_token"))
        declared = record.get("status") if isinstance(record, Mapping) else None
        if status != declared:
            raise C1C2PhysicalError("predecessor PASS status disagrees with receipt")
        observed.append(str(status))
    if tuple(observed) != tuple(expected_statuses):
        raise C1C2PhysicalError("runtime admission predecessor PASS order/status drifted")
    sampler = payload.get("sampler")
    if not isinstance(sampler, Mapping) or sampler.get("part") != "train":
        raise C1C2PhysicalError("runtime admission does not bind the TRAIN sampler")
    if payload.get("physical_configuration") != {
        "users": USERS,
        "steps": STEPS,
        "split": SPLIT,
        "field_component": FIELD_COMPONENT,
        "tle_root": "/home/sat/mcrl-runtime/tle-frozen-20260820",
    }:
        raise C1C2PhysicalError("runtime admission physical configuration drifted")
    _digest(
        payload.get("admitted_evaluation_sha256"),
        field="admitted_evaluation_sha256",
    )
    result = dict(payload)
    result["admission_sha256"] = digest
    result["admission_path"] = str(source.resolve())
    result["authenticated_predecessor_statuses"] = observed
    return result


def authenticate_tle_archive(archive: Any, admission: Mapping[str, object]) -> None:
    """Verify every current TLE file against the admitted freeze manifest bytes."""

    record = admission.get("tle_manifest")
    if not isinstance(record, Mapping):
        raise C1C2PhysicalError("runtime admission lacks TLE manifest binding")
    raw_path = record.get("path")
    if not isinstance(raw_path, str):
        raise C1C2PhysicalError("TLE manifest path is malformed")
    admission_path = Path(str(admission.get("admission_path", "")))
    manifest_path = Path(raw_path)
    if not manifest_path.is_absolute():
        manifest_path = admission_path.parent / manifest_path
    manifest = _read_json(manifest_path, label="frozen TLE manifest")
    rows = manifest.get("frozen_files")
    if not isinstance(rows, list) or not rows:
        raise C1C2PhysicalError("frozen TLE manifest lacks file rows")
    try:
        from mcrl.env.ephemeris import file_set_hash

        actual_rows = archive.manifest_rows(list(archive.dates))
        expected_hash = _digest(manifest.get("file_set_sha256"), field="tle.file_set_sha256")
        bound_hash = _digest(record.get("file_set_sha256"), field="tle.bound_file_set_sha256")
    except (AttributeError, TypeError, ValueError) as error:
        raise C1C2PhysicalError("cannot authenticate TLE archive file set") from error
    if rows != actual_rows or file_set_hash(actual_rows) != expected_hash or expected_hash != bound_hash:
        raise C1C2PhysicalError("TLE archive bytes disagree with frozen manifest")


@dataclass(frozen=True, slots=True)
class FrozenLearnedPolicy:
    arm: str
    q1: Any
    q2: Any
    checkpoint_path: Path
    checkpoint_sha256: str
    train_seed: int
    update_count: int
    q1_parameter_sha256: str
    q2_parameter_sha256: str
    initialization_sha256: str
    training_provenance: Mapping[str, object] | None = None
    routes: tuple[str, ...] = ROUTES

    def verify(self) -> None:
        if self.arm not in LEARNED_ARMS:
            raise C1C2PhysicalError("learned policy arm is outside the three-arm design")
        if self.routes != ROUTES:
            raise C1C2PhysicalError("learned policy routes must be exactly C1 and C2")
        if self.update_count != 200:
            raise C1C2PhysicalError("learned policy must be the epoch-100/200-update export")
        if file_sha256(self.checkpoint_path) != _digest(
            self.checkpoint_sha256, field=f"{self.arm}.checkpoint_sha256"
        ):
            raise C1C2PhysicalError(f"{self.arm} checkpoint bytes changed")
        for route, network, expected in (
            ("C1", self.q1, self.q1_parameter_sha256),
            ("C2", self.q2, self.q2_parameter_sha256),
        ):
            if _parameter_sha256(network) != _digest(
                expected, field=f"{self.arm}.{route}.parameter_sha256"
            ):
                raise C1C2PhysicalError(f"{self.arm} {route} parameters changed")
            if any(parameter.requires_grad for parameter in network.parameters()):
                raise C1C2PhysicalError(f"{self.arm} {route} remains trainable")
        _digest(self.initialization_sha256, field=f"{self.arm}.initialization_sha256")
        if self.training_provenance is not None:
            if (
                self.training_provenance.get("arm") != self.arm
                or self.training_provenance.get("source_mapping")
                != {
                    "FULL2": ["informed", "informed"],
                    "DROP_C1": ["neutral", "informed"],
                    "DROP_C2": ["informed", "neutral"],
                }[self.arm]
                or self.training_provenance.get("checkpoint_sha256")
                != self.checkpoint_sha256
                or self.training_provenance.get("stage_a_status")
                != "PASS_SOURCE_TRAINING_INTEGRITY"
            ):
                raise C1C2PhysicalError(f"{self.arm} training provenance drifted")
            _digest(
                self.training_provenance.get("manifest_sha256"),
                field=f"{self.arm}.training_provenance.manifest_sha256",
            )

    def binding(self) -> dict[str, object]:
        self.verify()
        result = {
            "arm": self.arm,
            "policy_family": "C1C2_SUCCESSOR_TWO_ROUTE",
            "checkpoint_path": str(self.checkpoint_path.resolve()),
            "checkpoint_sha256": self.checkpoint_sha256,
            "train_seed": self.train_seed,
            "update_count": self.update_count,
            "routes": list(self.routes),
            "q1_parameter_sha256": self.q1_parameter_sha256,
            "q2_parameter_sha256": self.q2_parameter_sha256,
            "initialization_sha256": self.initialization_sha256,
            "fixed_policy": True,
            "checkpoint_selected_from_outcome": False,
        }
        if self.training_provenance is not None:
            result["training_provenance"] = dict(self.training_provenance)
        return result


@dataclass(frozen=True, slots=True)
class FrozenBaselinePolicy:
    adapter: Any
    checkpoint_path: Path
    status_path: Path
    checkpoint_sha256: str
    authentication_sha256: str
    routes: tuple[str, ...] = ()
    arm: str = "BASELINE"

    def verify(self) -> None:
        if self.arm != "BASELINE" or self.routes:
            raise C1C2PhysicalError("BASELINE must carry routes = []")
        if self.checkpoint_sha256 != BASELINE_CHECKPOINT_SHA256:
            raise C1C2PhysicalError("BASELINE checkpoint is not the admitted policy")
        if file_sha256(self.checkpoint_path) != self.checkpoint_sha256:
            raise C1C2PhysicalError("BASELINE checkpoint bytes changed")
        if file_sha256(self.status_path) != _digest(
            self.authentication_sha256, field="BASELINE.authentication_sha256"
        ):
            raise C1C2PhysicalError("BASELINE authentication bytes changed")
        if self.checkpoint_sha256 == self.authentication_sha256:
            raise C1C2PhysicalError("BASELINE policy/authentication digests must differ")
        if getattr(self.adapter, "checkpoint_sha256", None) != self.checkpoint_sha256:
            raise C1C2PhysicalError("BASELINE adapter checkpoint binding drifted")
        if getattr(self.adapter, "state_dim", None) != 112:
            raise C1C2PhysicalError("BASELINE state dimension drifted")

    def binding(self) -> dict[str, object]:
        self.verify()
        return {
            "arm": "BASELINE",
            "policy_family": "AUTHENTICATED_PRE_CATFISH_MODQN",
            "checkpoint_path": str(self.checkpoint_path.resolve()),
            "checkpoint_sha256": self.checkpoint_sha256,
            "authentication_path": str(self.status_path.resolve()),
            "authentication_sha256": self.authentication_sha256,
            "state_dim": 112,
            "training_episodes": 9000,
            "routes": [],
            "fixed_policy": True,
            "checkpoint_selected_from_outcome": False,
        }


Policy: TypeAlias = FrozenLearnedPolicy | FrozenBaselinePolicy


def load_learned_two_route_checkpoint(
    path: str | Path,
    *,
    arm: str,
    expected_sha256: str,
    training_provenance: Mapping[str, object] | None = None,
) -> FrozenLearnedPolicy:
    """The single bindable seam for producer two-route checkpoint exports."""

    if arm not in LEARNED_ARMS:
        raise C1C2PhysicalError(f"cannot load learned checkpoint for arm {arm!r}")
    source = Path(path)
    expected = _digest(expected_sha256, field=f"{arm}.checkpoint_sha256")
    if file_sha256(source) != expected:
        raise C1C2PhysicalError(f"{arm} checkpoint digest mismatch")
    if torch is None:
        raise C1C2PhysicalError("loading learned checkpoints requires torch")
    try:
        payload = torch.load(BytesIO(source.read_bytes()), map_location="cpu", weights_only=False)
    except (OSError, EOFError, RuntimeError, TypeError, ValueError) as error:
        raise C1C2PhysicalError(f"cannot deserialize {arm} checkpoint") from error
    if not isinstance(payload, Mapping):
        raise C1C2PhysicalError("two-route checkpoint root must be a mapping")
    if _contains_c3(payload):
        raise C1C2PhysicalError("Q3/C3 state is forbidden in successor evaluation")
    if payload.get("schema") != TWO_ROUTE_CHECKPOINT_SCHEMA:
        raise C1C2PhysicalError("two-route checkpoint schema drifted")
    if payload.get("routes") != list(ROUTES):
        raise C1C2PhysicalError("checkpoint routes must be exactly C1 and C2")
    if payload.get("update_count") != 200 or payload.get("route_update_counts") != {
        "C1": 100,
        "C2": 100,
    }:
        raise C1C2PhysicalError("checkpoint is not the epoch-100 two-route export")
    try:
        from ee_axis_two_route_model import (
            EEAxisTwoRouteConfig,
            EEAxisTwoRouteModel,
        )
        from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
        from mcrl.algorithms.ee_axis_v014_head import EEAxisV014HeadConfig

        config = payload["config"]
        if not isinstance(config, Mapping) or set(config) != {"q1", "q2"}:
            raise C1C2PhysicalError("checkpoint configuration is not exactly Q1/Q2")
        q1_raw = dict(config["q1"])
        q2_raw = dict(config["q2"])
        for raw in (q1_raw, q2_raw):
            if isinstance(raw.get("hidden_layers"), list):
                raw["hidden_layers"] = tuple(raw["hidden_layers"])
        if isinstance(q1_raw.get("loss_weights"), list):
            q1_raw["loss_weights"] = tuple(q1_raw["loss_weights"])
        model_config = EEAxisTwoRouteConfig(
            q1=EEAxisActionSharedConfig(**q1_raw),
            q2=EEAxisV014HeadConfig(**q2_raw),
        )
        train_seed = payload["train_seed"]
        if type(train_seed) is not int:
            raise C1C2PhysicalError("checkpoint train_seed is malformed")
        model = EEAxisTwoRouteModel(model_config, train_seed=train_seed, device="cpu")
        if model.load_checkpoint_state(payload) != 200:
            raise C1C2PhysicalError("producer checkpoint loader returned the wrong update")
        model.eval()
        model.requires_grad_(False)
        initialization = payload["initialization"]
        if not isinstance(initialization, Mapping):
            raise C1C2PhysicalError("checkpoint initialization binding is malformed")
        initialization_sha256 = initialization.get("bytes_sha256")
    except C1C2PhysicalError:
        raise
    except (ImportError, KeyError, TypeError, ValueError, RuntimeError) as error:
        raise C1C2PhysicalError("producer two-route checkpoint validation failed") from error
    policy = FrozenLearnedPolicy(
        arm=arm,
        q1=model.q1,
        q2=model.q2,
        checkpoint_path=source,
        checkpoint_sha256=expected,
        train_seed=train_seed,
        update_count=200,
        q1_parameter_sha256=_parameter_sha256(model.q1),
        q2_parameter_sha256=_parameter_sha256(model.q2),
        initialization_sha256=_digest(
            initialization_sha256, field=f"{arm}.initialization.bytes_sha256"
        ),
        training_provenance=(
            None if training_provenance is None else dict(training_provenance)
        ),
    )
    policy.verify()
    return policy


def load_baseline_policy(
    *,
    checkpoint_path: str | Path,
    status_path: str | Path,
    expected_status_sha256: str,
) -> FrozenBaselinePolicy:
    """Admit BASELINE only through the existing authenticated adapter."""

    try:
        from baseline_adapter import BaselineAdapter

        adapter = BaselineAdapter.from_artifacts(
            checkpoint_path=checkpoint_path,
            status_path=status_path,
        )
    except Exception as error:
        raise C1C2PhysicalError("authenticated BASELINE adapter admission failed") from error
    policy = FrozenBaselinePolicy(
        adapter=adapter,
        checkpoint_path=Path(checkpoint_path),
        status_path=Path(status_path),
        checkpoint_sha256=BASELINE_CHECKPOINT_SHA256,
        authentication_sha256=_digest(
            expected_status_sha256, field="BASELINE.authentication_sha256"
        ),
    )
    policy.verify()
    return policy


@dataclass(frozen=True, slots=True)
class WorldBinding:
    episode_index: int
    world_id: str
    world_seed: int
    field_root_digest: str

    def verify(self) -> None:
        index = _positive_int(self.episode_index, field="episode_index")
        if self.world_id != f"world-{index:06d}" or "TEST" in self.world_id.upper():
            raise C1C2PhysicalError("world id differs from the declared TRAIN rule")
        if self.world_seed != 2026090600 + index:
            raise C1C2PhysicalError("world seed differs from the declared rule")
        expected = KeyedFadingField.from_components(
            FIELD_COMPONENT, self.world_seed
        ).root_digest
        if self.field_root_digest != expected:
            raise C1C2PhysicalError("world keyed-field root drifted")


@dataclass(frozen=True, slots=True)
class EvaluationPlan:
    worlds: tuple[WorldBinding, ...]
    plan_sha256: str
    arms: tuple[str, ...] = ARMS
    split: str = SPLIT
    field_component: str = FIELD_COMPONENT

    @classmethod
    def from_file(cls, path: str | Path) -> "EvaluationPlan":
        payload = read_world_plan(path)
        worlds = tuple(WorldBinding(**row) for row in payload["worlds"])
        plan = cls(
            worlds=worlds,
            plan_sha256=payload["plan_sha256"],
            arms=tuple(payload["arms"]),
            split=payload["split"],
            field_component=payload["field_component"],
        )
        plan.verify()
        return plan

    def verify(self) -> None:
        if self.arms != ARMS:
            raise C1C2PhysicalError("plan arm order/coverage is not the fixed four-arm order")
        if self.split != SPLIT or "TEST" in self.split.upper():
            raise C1C2PhysicalError("physical evaluation must remain TRAIN-only")
        if self.field_component != FIELD_COMPONENT:
            raise C1C2PhysicalError("keyed-field namespace drifted")
        if len(self.worlds) != PLAN_EPISODES:
            raise C1C2PhysicalError("plan must contain exactly 9000 worlds")
        for world in self.worlds:
            world.verify()
        expected = read_world_plan_from_value(self)
        if expected["plan_sha256"] != _digest(self.plan_sha256, field="plan_sha256"):
            raise C1C2PhysicalError("plan identity disagrees with declared contents")


def read_world_plan_from_value(plan: EvaluationPlan) -> dict[str, object]:
    """Reconstruct and verify the plan payload without accepting alternate grids."""

    from build_v023_c1c2_successor_world_plan import build_world_plan

    payload = build_world_plan()
    if [asdict(world) for world in plan.worlds] != payload["worlds"]:
        raise C1C2PhysicalError("plan world grid differs from the declared builder")
    return payload


@dataclass(frozen=True, slots=True)
class EpisodeReceipt:
    schema: str
    status: str
    split: str
    arm: str
    routes: tuple[str, ...]
    episode_index: int
    world_id: str
    world_seed: int
    users: int
    steps: int
    decision_interval_s: float
    total_bits: float
    total_energy_j: float
    ratio_of_sums_ee_bits_per_j: float
    served_user_steps: int
    service_opportunities: int
    service_fraction: float
    initial_world_sha256: str
    field_component: str
    field_root_digest: str
    action_trace_sha256: str
    plan_sha256: str
    policy_binding: Mapping[str, object]
    q3_evaluated: bool = False
    test_split_opened: bool = False
    episode_training: bool = False
    learner_update: bool = False
    claim_ceiling: str = CLAIM_CEILING

    def verify(self) -> None:
        if self.schema != RECEIPT_SCHEMA or self.status != STATUS or self.split != SPLIT:
            raise C1C2PhysicalError("episode receipt identity drifted")
        if self.arm not in ARMS:
            raise C1C2PhysicalError("episode receipt contains an unknown/fifth arm")
        expected_routes = () if self.arm == "BASELINE" else ROUTES
        if self.routes != expected_routes:
            raise C1C2PhysicalError(f"{self.arm} routes binding drifted")
        if self.users != USERS or self.steps != STEPS:
            raise C1C2PhysicalError("episode dimensions are not 100 users by ten steps")
        if self.field_component != FIELD_COMPONENT:
            raise C1C2PhysicalError("episode keyed-field namespace drifted")
        for field in (
            "initial_world_sha256",
            "field_root_digest",
            "action_trace_sha256",
            "plan_sha256",
        ):
            _digest(getattr(self, field), field=field)
        if not math.isfinite(self.decision_interval_s) or self.decision_interval_s <= 0:
            raise C1C2PhysicalError("decision interval is not positive finite")
        if not math.isfinite(self.total_bits) or self.total_bits < 0:
            raise C1C2PhysicalError("total bits are not finite non-negative")
        if not math.isfinite(self.total_energy_j) or self.total_energy_j <= 0:
            raise C1C2PhysicalError("total energy is not positive finite")
        if not math.isclose(
            self.ratio_of_sums_ee_bits_per_j,
            self.total_bits / self.total_energy_j,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise C1C2PhysicalError("episode EE is not a ratio of additive sums")
        if self.service_opportunities != USERS * STEPS:
            raise C1C2PhysicalError("service denominator is not pooled opportunity")
        if not 0 <= self.served_user_steps <= self.service_opportunities:
            raise C1C2PhysicalError("served count is outside pooled opportunity")
        if not math.isclose(
            self.service_fraction,
            self.served_user_steps / self.service_opportunities,
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise C1C2PhysicalError("service fraction is inconsistent with counts")
        if self.claim_ceiling != CLAIM_CEILING:
            raise C1C2PhysicalError("claim ceiling drifted")
        if self.q3_evaluated or self.test_split_opened or self.episode_training or self.learner_update:
            raise C1C2PhysicalError("receipt crossed Q3, TEST, or learning boundary")
        if not isinstance(self.policy_binding, Mapping):
            raise C1C2PhysicalError("receipt lacks policy binding")
        if _contains_c3(self.policy_binding):
            raise C1C2PhysicalError("receipt policy binding contains Q3/C3 state")
        if self.policy_binding.get("arm") != self.arm:
            raise C1C2PhysicalError("receipt policy arm drifted")
        if tuple(self.policy_binding.get("routes", ())) != self.routes:
            raise C1C2PhysicalError("receipt policy routes drifted")

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["routes"] = list(self.routes)
        result["policy_binding"] = dict(self.policy_binding)
        return result


def _receipt_from_mapping(value: EpisodeReceipt | Mapping[str, object]) -> EpisodeReceipt:
    if isinstance(value, EpisodeReceipt):
        value.verify()
        return value
    if not isinstance(value, Mapping):
        raise C1C2PhysicalError("receipt must be a mapping")
    payload = dict(value)
    routes = payload.get("routes")
    if isinstance(routes, list):
        payload["routes"] = tuple(routes)
    try:
        receipt = EpisodeReceipt(**payload)
    except (TypeError, ValueError) as error:
        raise C1C2PhysicalError("episode receipt mapping is malformed") from error
    receipt.verify()
    return receipt


def pool_receipts(
    receipts: Sequence[EpisodeReceipt | Mapping[str, object]], *, arm: str
) -> dict[str, object]:
    rows = tuple(_receipt_from_mapping(value) for value in receipts)
    if arm not in ARMS or not rows or any(row.arm != arm for row in rows):
        raise C1C2PhysicalError("pooled receipts are empty or contain mixed arms")
    if len({row.episode_index for row in rows}) != len(rows):
        raise C1C2PhysicalError("pooled receipts contain duplicate episodes")
    bits = math.fsum(row.total_bits for row in rows)
    energy = math.fsum(row.total_energy_j for row in rows)
    served = sum(row.served_user_steps for row in rows)
    opportunities = sum(row.service_opportunities for row in rows)
    if energy <= 0 or opportunities <= 0:
        raise C1C2PhysicalError("pooled endpoint denominator is not positive")
    return {
        "arm": arm,
        "routes": [] if arm == "BASELINE" else list(ROUTES),
        "episodes": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "service_opportunities": opportunities,
        "service_fraction": served / opportunities,
        "episode_training": False,
        "learner_update": False,
    }


def adjudicate_physical_disposition(
    pooled_by_arm: Mapping[str, Mapping[str, object]],
    *,
    completed_episodes: int,
    expected_episodes: int,
    integrity_ok: bool = True,
) -> dict[str, object]:
    """Apply contract section 6 without exclusive/short-circuit reasons."""

    if not integrity_ok:
        return {"overall_token": INTEGRITY_STOP, "reasons": []}
    if completed_episodes != expected_episodes or expected_episodes not in TERMINAL_BOUNDARIES:
        return {"overall_token": INTEGRITY_STOP, "reasons": []}
    try:
        if set(pooled_by_arm) != set(ARMS) or len(pooled_by_arm) != len(ARMS):
            raise C1C2PhysicalError("pooled arm coverage drifted")
        ee = {
            arm: float(pooled_by_arm[arm]["ratio_of_sums_ee_bits_per_j"])
            for arm in ARMS
        }
        service = {arm: float(pooled_by_arm[arm]["service_fraction"]) for arm in ARMS}
        episodes = {arm: int(pooled_by_arm[arm]["episodes"]) for arm in ARMS}
        if any(not math.isfinite(value) for value in (*ee.values(), *service.values())):
            raise C1C2PhysicalError("pooled endpoint is non-finite")
        if any(value != expected_episodes for value in episodes.values()):
            raise C1C2PhysicalError("pooled episode coverage is incomplete")
        if any(value < 0.0 or value > 1.0 for value in service.values()):
            raise C1C2PhysicalError("pooled service fraction is invalid")
    except (KeyError, TypeError, ValueError, C1C2PhysicalError):
        return {"overall_token": INTEGRITY_STOP, "reasons": []}
    reasons: list[str] = []
    baseline = ee["BASELINE"]
    for arm in LEARNED_ARMS:
        if ee[arm] <= baseline:
            reasons.append(f"{arm}_NOT_ABOVE_BASELINE")
    for arm in ("DROP_C1", "DROP_C2"):
        if ee[arm] >= ee["FULL2"]:
            reasons.append(f"{arm}_NOT_BELOW_FULL2")
    for arm in LEARNED_ARMS:
        if service[arm] < service["BASELINE"] - SERVICE_MARGIN:
            reasons.append(f"SERVICE_NONINFERIORITY_FAILED:{arm}")
    return {
        "overall_token": HELD if not reasons else FALSIFIED,
        "reasons": reasons,
    }


def aggregate_last_outcomes(
    outcomes: Sequence[object], *, decision_interval_s: float
) -> dict[str, float | int]:
    """Apply the runner's terminal reduction to real-shaped last_outcome rows."""

    if len(outcomes) != STEPS or not math.isfinite(decision_interval_s) or decision_interval_s <= 0:
        raise C1C2PhysicalError("last_outcome aggregation requires ten positive-time steps")
    total_bits = 0.0
    total_energy = 0.0
    served_user_steps = 0
    for outcome in outcomes:
        try:
            rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
            power = float(outcome.system_power_w)
            served = int(outcome.resolution.served_count)
        except (AttributeError, TypeError, ValueError) as error:
            raise C1C2PhysicalError("last_outcome lacks physical endpoint fields") from error
        if rates.shape != (USERS,) or not np.all(np.isfinite(rates)) or np.any(rates < 0):
            raise C1C2PhysicalError("last_outcome link rates are malformed")
        if not math.isfinite(power) or power <= 0:
            raise C1C2PhysicalError("last_outcome energy is not positive finite")
        if served < 0 or served > USERS:
            raise C1C2PhysicalError("last_outcome served count is invalid")
        total_bits += decision_interval_s * math.fsum(float(value) for value in rates)
        total_energy += decision_interval_s * power
        served_user_steps += served
    return {
        "total_bits": total_bits,
        "total_energy_j": total_energy,
        "ratio_of_sums_ee_bits_per_j": total_bits / total_energy,
        "served_user_steps": served_user_steps,
        "service_opportunities": USERS * STEPS,
        "service_fraction": served_user_steps / (USERS * STEPS),
    }


def _observation_digest(native: Any) -> str:
    try:
        states = np.asarray(native.state_matrix, dtype=np.float32)
        masks = np.asarray(native.action_masks, dtype=np.bool_)
    except (AttributeError, TypeError, ValueError) as error:
        raise C1C2PhysicalError("native observation is malformed") from error
    if states.shape != (USERS, 228) or masks.shape != (USERS, 28):
        raise C1C2PhysicalError("native initial observation dimensions drifted")
    return canonical_sha256(
        {
            "state_sha256": _array_sha256(states),
            "mask_sha256": _array_sha256(masks),
        }
    )


def select_learned_q12_actions(
    q1_values: object,
    q2_values: object,
    masks: object,
) -> np.ndarray:
    """Masked, unweighted float64 Q1+Q2 with lowest-legal-index ties."""

    try:
        return deploy_q12_action(q1_values, q2_values, masks)
    except Exception as error:
        raise C1C2PhysicalError("imported Q1+Q2 deployment rule refused input") from error


def _learned_actions(policy: FrozenLearnedPolicy, step_environment: Any, observation: Any) -> np.ndarray:
    if torch is None:
        raise C1C2PhysicalError("learned inference requires torch")
    try:
        native = encode_ee_axis_state(step_environment, observation)
        masks = np.asarray(native.action_masks, dtype=np.bool_)
        states = np.asarray(native.state_matrix, dtype=np.float32)
        with torch.no_grad():
            q1 = policy.q1(torch.tensor(states, dtype=torch.float32)).cpu().numpy()
        if (
            q1.shape != (USERS, 28)
            or not np.all(np.isfinite(q1))
            or not np.all(np.any(masks, axis=1))
        ):
            raise C1C2PhysicalError("learned Q1 surface/mask is malformed")
        q1_reference = np.argmax(np.where(masks, q1, -np.inf), axis=1).astype(np.int64)
        anchor = snapshot_ops3_anchor(step_environment, observation)
        projection = project_ops3_anchor(anchor)
        surfaces = build_ops3_live_surfaces(anchor, projection, q1_reference)
        q2_state = encode_ee_axis_v014_q2_states(surfaces)
        q2_state.verify()
        q2_masks = np.asarray(q2_state.action_masks, dtype=np.bool_)
        if not np.array_equal(q2_masks, masks):
            raise C1C2PhysicalError("Q2 mask differs from the common native mask")
        with torch.no_grad():
            q2 = policy.q2(
                torch.tensor(q2_state.state_matrix, dtype=torch.float32),
                torch.tensor(masks, dtype=torch.bool),
            ).cpu().numpy()
    except C1C2PhysicalError:
        raise
    except (AttributeError, RuntimeError, TypeError, ValueError) as error:
        raise C1C2PhysicalError("learned Q1/Q2 inference failed") from error
    return select_learned_q12_actions(q1, q2, masks)


def _native_masks(masks: Sequence[Any]) -> np.ndarray:
    try:
        values = np.stack([np.asarray(mask.mask) for mask in masks], axis=0)
    except (AttributeError, TypeError, ValueError) as error:
        raise C1C2PhysicalError("native action-mask batch is malformed") from error
    if values.dtype != np.bool_ or values.shape != (USERS, 28):
        raise C1C2PhysicalError("native action-mask batch dimensions drifted")
    return values


def _validate_actions(actions: object, masks: np.ndarray) -> np.ndarray:
    values = np.asarray(actions)
    if values.shape != (USERS,) or values.dtype.kind not in "iu":
        raise C1C2PhysicalError("action vector is malformed")
    selected = values.astype(np.int64, copy=True)
    rows = np.arange(USERS)
    if np.any(selected < 0) or np.any(selected >= 28) or np.any(~masks[rows, selected]):
        raise C1C2PhysicalError("selected action is outside the common safe mask")
    return selected


EnvironmentFactory: TypeAlias = Callable[[Any, int], TrainerEnvironment]
RngFactory: TypeAlias = Callable[[int], Sequence[np.random.Generator]]


class FixedPolicyEpisodeAdapter:
    """Run one fresh real environment for each arm/world pair."""

    def __init__(
        self,
        *,
        policies: Sequence[Policy],
        archive: Any,
        environment_factory: EnvironmentFactory,
        rng_factory: RngFactory,
        runtime_admission: Mapping[str, object] | None = None,
        required_predecessor_statuses: Sequence[str] = (
            "PASS_SOURCE_TRAINING_INTEGRITY",
            "PASS_PLUMBING_INTEGRITY",
        ),
    ) -> None:
        if tuple(policy.arm for policy in policies) != ARMS:
            raise C1C2PhysicalError("policy arm order/coverage is not the fixed four-arm order")
        for policy in policies:
            policy.verify()
        if not callable(environment_factory) or not callable(rng_factory):
            raise C1C2PhysicalError("environment_factory and rng_factory are required")
        if not isinstance(runtime_admission, Mapping):
            raise C1C2PhysicalError("formal runtime admission is required")
        self.policies = {policy.arm: policy for policy in policies}
        self.archive = archive
        self.environment_factory = environment_factory
        self.rng_factory = rng_factory
        self.runtime_admission = dict(runtime_admission)
        admission_path = self.runtime_admission.get("admission_path")
        admission_sha = self.runtime_admission.get("admission_sha256")
        if not isinstance(admission_path, str):
            raise C1C2PhysicalError("runtime admission was not loaded from a sealed file")
        sealed_payload, _ = _read_sealed_json(
            admission_path,
            expected_sha256=_digest(admission_sha, field="runtime_admission_sha256"),
            label="runtime admission",
        )
        authenticated_payload = dict(self.runtime_admission)
        authenticated_payload.pop("admission_path", None)
        authenticated_payload.pop("admission_sha256", None)
        authenticated_statuses = authenticated_payload.pop(
            "authenticated_predecessor_statuses", None
        )
        if sealed_payload != authenticated_payload:
            raise C1C2PhysicalError("runtime admission payload changed after authentication")
        if authenticated_statuses != list(required_predecessor_statuses):
            raise C1C2PhysicalError("runtime admission predecessor PASS coverage is insufficient")
        provenance = self.runtime_admission.get("learned_training_provenance")
        if not isinstance(provenance, Mapping) or set(provenance) != set(LEARNED_ARMS):
            raise C1C2PhysicalError("learned-arm training provenance coverage drifted")
        expected_sources = {
            "FULL2": ["informed", "informed"],
            "DROP_C1": ["neutral", "informed"],
            "DROP_C2": ["informed", "neutral"],
        }
        for arm in LEARNED_ARMS:
            record = provenance[arm]
            policy = self.policies[arm]
            if (
                not isinstance(record, Mapping)
                or record.get("checkpoint_sha256") != policy.checkpoint_sha256
                or record.get("source_mapping") != expected_sources[arm]
                or record.get("stage_a_status") != "PASS_SOURCE_TRAINING_INTEGRITY"
            ):
                raise C1C2PhysicalError(f"{arm} training provenance drifted")
            _digest(record.get("manifest_sha256"), field=f"{arm}.manifest_sha256")
        self._resume_by_arm: dict[str, Mapping[str, object]] = {}

    @property
    def policy_bindings(self) -> dict[str, Mapping[str, object]]:
        result: dict[str, Mapping[str, object]] = {}
        provenance = self.runtime_admission["learned_training_provenance"]
        assert isinstance(provenance, Mapping)
        for arm in ARMS:
            binding = self.policies[arm].binding()
            if arm in LEARNED_ARMS:
                binding["training_provenance"] = dict(provenance[arm])  # type: ignore[arg-type]
            result[arm] = binding
        return result

    def resume_state_for(self, arm: str) -> Mapping[str, object] | None:
        if arm not in ARMS:
            raise C1C2PhysicalError(f"unknown arm: {arm}")
        return self._resume_by_arm.get(arm)

    def restore_resume_states(self, states: Mapping[str, object]) -> None:
        if set(states) != set(ARMS) or any(not isinstance(states[arm], Mapping) for arm in ARMS):
            raise C1C2PhysicalError("resume checkpoint lacks one state per arm")
        self._resume_by_arm = {arm: dict(states[arm]) for arm in ARMS}  # type: ignore[arg-type]

    def run_episode(
        self,
        *,
        arm: str,
        world: WorldBinding,
        plan_sha256: str,
        resume_state: Mapping[str, object] | None = None,
    ) -> EpisodeReceipt:
        if arm not in ARMS:
            raise C1C2PhysicalError(f"unknown/fifth arm: {arm}")
        world.verify()
        policy = self.policies[arm]
        policy.verify()
        policy_binding = self.policy_bindings[arm]
        if self.runtime_admission.get("admitted_evaluation_sha256") != plan_sha256:
            raise C1C2PhysicalError("runtime admission does not bind this evaluation identity")
        if resume_state is not None:
            if (
                not isinstance(resume_state, Mapping)
                or resume_state.get("arm") != arm
                or resume_state.get("episode_index") != world.episode_index - 1
                or resume_state.get("plan_sha256") != plan_sha256
                or resume_state.get("policy_binding") != policy_binding
            ):
                raise C1C2PhysicalError("resume state identity drifted")
        field = KeyedFadingField.from_components(FIELD_COMPONENT, world.world_seed)
        if field.root_digest != world.field_root_digest:
            raise C1C2PhysicalError("keyed-field root differs from frozen plan")
        try:
            environment = self.environment_factory(self.archive, USERS)
        except Exception as error:  # pragma: no cover - runtime factory boundary
            raise C1C2PhysicalError("TrainerEnvironment factory failed") from error
        if not isinstance(environment, TrainerEnvironment):
            raise C1C2PhysicalError("environment_factory must return TrainerEnvironment")
        sampler = getattr(environment, "sampler", None)
        sampler_binding = self.runtime_admission.get("sampler")
        if (
            sampler is None
            or getattr(sampler, "part", None) != "train"
            or not callable(getattr(sampler, "as_dict", None))
            or not isinstance(sampler_binding, Mapping)
            or sampler_binding.get("part") != "train"
            or sampler_binding.get("as_dict_sha256")
            != canonical_sha256(sampler.as_dict())
        ):
            raise C1C2PhysicalError("environment sampler is not the frozen TRAIN sampler")
        step_environment = getattr(environment, "environment", None)
        if step_environment is None or not hasattr(step_environment, "_fading_field"):
            raise C1C2PhysicalError("TrainerEnvironment lacks keyed-field boundary")
        step_environment._fading_field = field
        if environment.config.num_users != USERS or environment.config.steps_per_episode != STEPS:
            raise C1C2PhysicalError("TrainerEnvironment dimensions drifted")
        try:
            rngs = tuple(self.rng_factory(world.world_seed))
        except Exception as error:  # pragma: no cover
            raise C1C2PhysicalError("RNG factory failed") from error
        if len(rngs) < 2 or any(not isinstance(rng, np.random.Generator) for rng in rngs[:2]):
            raise C1C2PhysicalError("RNG factory must return environment and mobility generators")
        if resume_state is not None:
            loader = getattr(environment, "load_training_state_dict", None)
            if not callable(loader) or not isinstance(
                resume_state.get("environment_training_state"), Mapping
            ):
                raise C1C2PhysicalError("environment resume state is unavailable")
            try:
                loader(
                    _restore_jsonable(
                        copy.deepcopy(resume_state["environment_training_state"])
                    )
                )
            except (KeyError, TypeError, ValueError, RuntimeError) as error:
                raise C1C2PhysicalError("environment resume state is invalid") from error
        try:
            states, masks, observation = environment.reset(rngs[0], rngs[1])
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            raise C1C2PhysicalError("TrainerEnvironment reset failed") from error
        native = encode_ee_axis_state(step_environment, observation)
        initial_world_sha256 = _observation_digest(native)
        try:
            interval_s = float(step_environment.driver.config.ephemeris.time_step_s)
        except (AttributeError, TypeError, ValueError) as error:
            raise C1C2PhysicalError("decision interval is unavailable") from error
        outcomes: list[object] = []
        trace = hashlib.sha256()
        for step_index in range(STEPS):
            mask_values = _native_masks(masks)
            if arm == "BASELINE":
                # The baseline decision has exactly one route: its admitted adapter.
                actions = policy.adapter.select_actions(states, masks)  # type: ignore[union-attr]
            else:
                actions = _learned_actions(policy, step_environment, observation)  # type: ignore[arg-type]
            actions = _validate_actions(actions, mask_values)
            trace.update(actions.astype(np.int64, copy=False).tobytes(order="C"))
            try:
                step_result = environment.step(actions, rngs[0])
                outcome = environment.last_outcome
            except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                raise C1C2PhysicalError("TrainerEnvironment step failed") from error
            outcomes.append(outcome)
            done = bool(getattr(outcome, "done", getattr(step_result, "done", False)))
            if step_index < STEPS - 1 and done:
                raise C1C2PhysicalError("environment ended before ten committed steps")
            if step_index == STEPS - 1 and not done:
                raise C1C2PhysicalError("environment did not end after ten committed steps")
            states = list(step_result.user_states)
            masks = list(step_result.action_masks)
            observation = outcome.observation
        policy.verify()
        aggregate = aggregate_last_outcomes(outcomes, decision_interval_s=interval_s)
        receipt = EpisodeReceipt(
            schema=RECEIPT_SCHEMA,
            status=STATUS,
            split=SPLIT,
            arm=arm,
            routes=policy.routes,
            episode_index=world.episode_index,
            world_id=world.world_id,
            world_seed=world.world_seed,
            users=USERS,
            steps=STEPS,
            decision_interval_s=interval_s,
            total_bits=float(aggregate["total_bits"]),
            total_energy_j=float(aggregate["total_energy_j"]),
            ratio_of_sums_ee_bits_per_j=float(aggregate["ratio_of_sums_ee_bits_per_j"]),
            served_user_steps=int(aggregate["served_user_steps"]),
            service_opportunities=int(aggregate["service_opportunities"]),
            service_fraction=float(aggregate["service_fraction"]),
            initial_world_sha256=initial_world_sha256,
            field_component=FIELD_COMPONENT,
            field_root_digest=field.root_digest,
            action_trace_sha256=trace.hexdigest(),
            plan_sha256=plan_sha256,
            policy_binding=policy_binding,
        )
        receipt.verify()
        state_method = getattr(environment, "training_state_dict", None)
        if not callable(state_method):
            raise C1C2PhysicalError("TrainerEnvironment lacks resume state")
        state = state_method()
        if not isinstance(state, Mapping):
            raise C1C2PhysicalError("TrainerEnvironment resume state is malformed")
        self._resume_by_arm[arm] = {
            "schema": f"{SCHEMA}-resume-state",
            "arm": arm,
            "episode_index": world.episode_index,
            "world_id": world.world_id,
            "world_seed": world.world_seed,
            "field_root_digest": world.field_root_digest,
            "plan_sha256": plan_sha256,
            "policy_binding": policy_binding,
            "environment_training_state": copy.deepcopy(dict(state)),
        }
        return receipt


def _verify_matched_episode(rows: Sequence[EpisodeReceipt], world: WorldBinding) -> None:
    if tuple(row.arm for row in rows) != ARMS:
        raise C1C2PhysicalError("episode lacks complete ordered four-arm coverage")
    for row in rows:
        row.verify()
        if (
            row.episode_index != world.episode_index
            or row.world_id != world.world_id
            or row.world_seed != world.world_seed
            or row.field_root_digest != world.field_root_digest
        ):
            raise C1C2PhysicalError("matched receipt disagrees with frozen world")
    if len({row.initial_world_sha256 for row in rows}) != 1:
        raise C1C2PhysicalError("matched arms do not share one initial world")


def _read_checkpoint(path: Path) -> dict[str, Any]:
    payload = _read_json(path, label="evaluation checkpoint")
    claimed = payload.pop("checkpoint_sha256", None)
    if _digest(claimed, field="checkpoint_sha256") != canonical_sha256(payload):
        raise C1C2PhysicalError("checkpoint digest disagrees with contents")
    if payload.get("schema") != CHECKPOINT_SCHEMA or payload.get("status") != STATUS:
        raise C1C2PhysicalError("checkpoint identity drifted")
    return payload


def _authenticate_continuation_authority(
    path: str | Path,
    *,
    expected_sha256: str,
    plan_sha256: str,
    policy_bindings: Mapping[str, object],
) -> dict[str, Any]:
    source = Path(path)
    payload, digest = _read_sealed_json(
        source,
        expected_sha256=expected_sha256,
        label="continuation authority",
    )
    if (
        payload.get("schema") != CONTINUATION_AUTHORITY_SCHEMA
        or payload.get("status") != "AUTHORIZED_CONTINUATION_TO_9000"
        or payload.get("continuation_from_episode") != 3000
        or payload.get("continuation_to_episode") != 9000
        or payload.get("plan_sha256") != plan_sha256
        or payload.get("policy_bindings_sha256") != canonical_sha256(policy_bindings)
        or payload.get("held_terminal_token_sha256") != HELD_TOKEN_SHA256
    ):
        raise C1C2PhysicalError("continuation authority identity/bindings drifted")
    _digest(payload.get("result_3000_sha256"), field="result_3000_sha256")
    _digest(payload.get("checkpoint_3000_sha256"), field="checkpoint_3000_sha256")
    notification = payload.get("owner_notification")
    if not isinstance(notification, Mapping) or notification.get("status") != "OWNER_NOTIFIED":
        raise C1C2PhysicalError("continuation authority lacks explicit owner notification")
    notification_path, notification_sha = _bound_file(
        notification, base=source.parent, label="owner_notification"
    )
    marker, _ = _read_sealed_json(
        notification_path,
        expected_sha256=notification_sha,
        label="owner notification marker",
    )
    reply = marker.get("owner_reply_verbatim")
    required_marker_strings = (
        "notification_sent_utc",
        "owner_reply_received_utc",
        "notification_channel",
        "recorded_by",
    )
    if (
        marker.get("formal") is not True
        or marker.get("status") != "OWNER_NOTIFIED_FOR_9000_CONTINUATION"
        or marker.get("plan_sha256") != plan_sha256
        or marker.get("result_3000_sha256") != payload.get("result_3000_sha256")
        or not isinstance(reply, str)
        or len(reply.strip()) < 20
        or any(
            not isinstance(marker.get(field), str) or not str(marker[field]).strip()
            for field in required_marker_strings
        )
        or payload.get("owner_reply_sha256")
        != hashlib.sha256(reply.encode("utf-8")).hexdigest()
        or payload.get("recorded_by") != marker.get("recorded_by")
    ):
        raise C1C2PhysicalError("continuation authority owner marker drifted")
    sent = _utc_timestamp(marker["notification_sent_utc"], field="notification_sent_utc")
    received = _utc_timestamp(
        marker["owner_reply_received_utc"], field="owner_reply_received_utc"
    )
    if received < sent:
        raise C1C2PhysicalError("owner reply predates the recorded notification")
    result = dict(payload)
    result["authority_sha256"] = digest
    result["authority_path"] = str(source.resolve())
    result["owner_notification_path"] = str(notification_path.resolve())
    result["owner_notification_sha256"] = notification_sha
    return result


def _authenticate_repair_authority(
    path: str | Path,
    *,
    expected_sha256: str,
    plan_sha256: str,
    stop_path: Path,
    resume_checkpoint: Path,
) -> dict[str, Any]:
    source = Path(path)
    payload, digest = _read_sealed_json(
        source, expected_sha256=expected_sha256, label="repair authority"
    )
    if (
        payload.get("schema") != REPAIR_AUTHORITY_SCHEMA
        or payload.get("status") != "AUTHORIZED_INFRASTRUCTURE_REPAIR"
        or payload.get("plan_sha256") != plan_sha256
        or payload.get("integrity_stop_sha256") != file_sha256(stop_path)
        or payload.get("resume_checkpoint_sha256") != file_sha256(resume_checkpoint)
        or payload.get("preserve_valid_history") is not True
        or not isinstance(payload.get("smallest_invalid_unit"), str)
        or not payload["smallest_invalid_unit"]
    ):
        raise C1C2PhysicalError("repair authority does not bind STOP and resume unit")
    result = dict(payload)
    result["authority_sha256"] = digest
    return result


class FixedPolicyEvaluationRunner:
    """Execute cumulative administrative rungs under one 9000-world identity."""

    def __init__(
        self,
        *,
        adapter: FixedPolicyEpisodeAdapter,
        plan: EvaluationPlan,
        terminal_boundary: int = 3000,
        continuation_authority_path: str | Path | None = None,
        continuation_authority_sha256: str | None = None,
        repair_authority_path: str | Path | None = None,
        repair_authority_sha256: str | None = None,
        admission_mapping: Mapping[str, object] | None = None,
    ) -> None:
        plan.verify()
        if terminal_boundary not in TERMINAL_BOUNDARIES:
            raise C1C2PhysicalError("terminal boundary must be 3000 or 9000")
        if terminal_boundary == 9000:
            if continuation_authority_path is None:
                raise C1C2PhysicalError(
                    "9000 continuation requires a sealed continuation authority file"
                )
            continuation_authority = _authenticate_continuation_authority(
                continuation_authority_path,
                expected_sha256=_digest(
                    continuation_authority_sha256,
                    field="continuation_authority_sha256",
                ),
                plan_sha256=plan.plan_sha256,
                policy_bindings=adapter.policy_bindings,
            )
        elif continuation_authority_path is not None or continuation_authority_sha256 is not None:
            raise C1C2PhysicalError("continuation authority is valid only for boundary 9000")
        else:
            continuation_authority = None
        if (repair_authority_path is None) != (repair_authority_sha256 is None):
            raise C1C2PhysicalError("repair authority path and digest must be supplied together")
        if tuple(adapter.policy_bindings) != ARMS:
            raise C1C2PhysicalError("adapter policy binding order drifted")
        self.adapter = adapter
        self.plan = plan
        self.terminal_boundary = terminal_boundary
        self.continuation_authority = continuation_authority
        self.repair_authority_path = repair_authority_path
        self.repair_authority_sha256 = repair_authority_sha256
        if admission_mapping is None and not isinstance(adapter, FixedPolicyEpisodeAdapter):
            # Compatibility for isolated persistence-test doubles only. Formal
            # runtime adapters must receive the file-backed mapping explicitly.
            admission_mapping = {
                arm: {"policy_binding": adapter.policy_bindings[arm]} for arm in ARMS
            }
        if not isinstance(admission_mapping, Mapping) or tuple(admission_mapping) != ARMS:
            raise C1C2PhysicalError("Stage-C admission mapping order/coverage drifted")
        for arm in ARMS:
            record = admission_mapping[arm]
            if not isinstance(record, Mapping) or record.get("policy_binding") != adapter.policy_bindings[arm]:
                raise C1C2PhysicalError(f"Stage-C admission mapping drifted: {arm}")
        self.admission_mapping = dict(admission_mapping)

    def _checkpoint_payload(
        self, completed: int, receipts: Sequence[EpisodeReceipt]
    ) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": CHECKPOINT_SCHEMA,
            "status": STATUS,
            "split": SPLIT,
            "completed_episode": completed,
            "plan_sha256": self.plan.plan_sha256,
            "arms": list(ARMS),
            "checkpoint_every": CHECKPOINT_EVERY,
            "policy_bindings": self.adapter.policy_bindings,
            "admission_mapping": self.admission_mapping,
            "receipts": [row.as_dict() for row in receipts],
            "resume_states": {
                arm: self.adapter.resume_state_for(arm) for arm in ARMS
            },
            "q3_evaluated": False,
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
            "claim_ceiling": CLAIM_CEILING,
        }
        body["checkpoint_sha256"] = canonical_sha256(body)
        return body

    def _validate_resume(
        self, payload: Mapping[str, object]
    ) -> tuple[int, list[EpisodeReceipt]]:
        if _contains_c3(payload):
            raise C1C2PhysicalError("resume checkpoint contains Q3/C3 state")
        if (
            payload.get("split") != SPLIT
            or payload.get("plan_sha256") != self.plan.plan_sha256
            or payload.get("arms") != list(ARMS)
            or payload.get("checkpoint_every") != CHECKPOINT_EVERY
            or payload.get("policy_bindings") != self.adapter.policy_bindings
            or payload.get("admission_mapping") != self.admission_mapping
            or payload.get("claim_ceiling") != CLAIM_CEILING
        ):
            raise C1C2PhysicalError("resume checkpoint plan/policy identity drifted")
        if any(
            bool(payload.get(field, False))
            for field in (
                "q3_evaluated",
                "test_split_opened",
                "episode_training",
                "learner_update",
            )
        ):
            raise C1C2PhysicalError("resume checkpoint crossed a forbidden boundary")
        completed = _positive_int(payload.get("completed_episode"), field="completed_episode")
        if completed % CHECKPOINT_EVERY or completed > self.terminal_boundary:
            raise C1C2PhysicalError("resume is not on the admitted 100-episode cadence")
        raw = payload.get("receipts")
        if not isinstance(raw, list) or len(raw) != completed * len(ARMS):
            raise C1C2PhysicalError("resume checkpoint receipt coverage is incomplete")
        rows = [_receipt_from_mapping(value) for value in raw]
        for index in range(completed):
            matched = rows[index * 4 : index * 4 + 4]
            _verify_matched_episode(matched, self.plan.worlds[index])
            for row in matched:
                if (
                    row.plan_sha256 != self.plan.plan_sha256
                    or row.policy_binding != self.adapter.policy_bindings[row.arm]
                ):
                    raise C1C2PhysicalError("resume receipt plan/policy binding drifted")
        states = payload.get("resume_states")
        if not isinstance(states, Mapping):
            raise C1C2PhysicalError("resume checkpoint lacks states")
        self.adapter.restore_resume_states(states)
        return completed, rows

    def _validate_history(
        self, output: Path, completed: int, receipts: Sequence[EpisodeReceipt]
    ) -> None:
        checkpoint_paths = sorted((output / "checkpoints").glob("checkpoint-*.json"))
        rung_paths = sorted((output / "rungs").glob("rung-*.json"))
        expected_names = [
            f"{index:06d}.json" for index in range(CHECKPOINT_EVERY, completed + 1, CHECKPOINT_EVERY)
        ]
        if [path.name.removeprefix("checkpoint-") for path in checkpoint_paths] != expected_names:
            raise C1C2PhysicalError("output checkpoint history is incomplete or ahead")
        if [path.name.removeprefix("rung-") for path in rung_paths] != expected_names:
            raise C1C2PhysicalError("output rung history is incomplete or ahead")
        for checkpoint_path, rung_path in zip(checkpoint_paths, rung_paths, strict=True):
            boundary = int(checkpoint_path.stem.split("-")[-1])
            prefix = list(receipts[: boundary * len(ARMS)])
            checkpoint = _read_checkpoint(checkpoint_path)
            history = checkpoint.get("receipts")
            if (
                checkpoint.get("completed_episode") != boundary
                or checkpoint.get("plan_sha256") != self.plan.plan_sha256
                or checkpoint.get("policy_bindings") != self.adapter.policy_bindings
                or checkpoint.get("admission_mapping") != self.admission_mapping
                or history != [row.as_dict() for row in prefix]
            ):
                raise C1C2PhysicalError("authenticated checkpoint history drifted")
            rung = _read_json(rung_path, label="rung receipt")
            if rung != self._rung_payload(boundary, prefix):
                raise C1C2PhysicalError("authenticated rung history drifted")

    def _validate_3000_continuation_anchor(self, output: Path, checkpoint: Path) -> None:
        if self.continuation_authority is None:
            raise C1C2PhysicalError("9000 continuation authority is unavailable")
        result_path = output / "result.json"
        result = _read_json(result_path, label="preserved 3000 result")
        authority = self.continuation_authority
        if (
            checkpoint.name != "checkpoint-003000.json"
            or file_sha256(checkpoint) != authority["checkpoint_3000_sha256"]
            or file_sha256(result_path) != authority["result_3000_sha256"]
            or result.get("schema") != RESULT_SCHEMA
            or result.get("status") != STATUS
            or result.get("split") != SPLIT
            or result.get("completed_episode") != 3000
            or result.get("terminal_boundary") != 3000
            or result.get("plan_sha256") != self.plan.plan_sha256
            or result.get("arms") != list(ARMS)
            or result.get("overall_token") != HELD
            or result.get("reasons") != []
            or result.get("scientific_disposition_emitted") is not True
            or result.get("claim_ceiling") != CLAIM_CEILING
        ):
            raise C1C2PhysicalError("preserved 3000 HELD result is not continuation authority")

    def _rung_payload(
        self, completed: int, receipts: Sequence[EpisodeReceipt]
    ) -> dict[str, object]:
        pooled = {
            arm: pool_receipts([row for row in receipts if row.arm == arm], arm=arm)
            for arm in ARMS
        }
        return {
            "schema": RUNG_SCHEMA,
            "status": STATUS,
            "split": SPLIT,
            "completed_episode": completed,
            "plan_sha256": self.plan.plan_sha256,
            "arms": list(ARMS),
            "pooled_by_arm": pooled,
            "admission_mapping": self.admission_mapping,
            "scientific_disposition_emitted": False,
            "q3_evaluated": False,
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    def _integrity_stop(self, output: Path, error: Exception) -> None:
        if not output.exists() or not output.is_dir():
            return
        path = output / (
            "continuation-integrity-stop.json"
            if self.terminal_boundary == 9000
            else "integrity-stop.json"
        )
        if path.exists() or path.is_symlink():
            return
        try:
            _write_once(
                path,
                {
                    "schema": INTEGRITY_SCHEMA,
                    "overall_token": INTEGRITY_STOP,
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "plan_sha256": self.plan.plan_sha256,
                    "scientific_token_emitted": False,
                    "claim_ceiling": CLAIM_CEILING,
                },
            )
        except C1C2PhysicalError:
            return

    def run(
        self,
        *,
        output_dir: str | Path,
        pause_at: int,
        resume_checkpoint: str | Path | None = None,
    ) -> dict[str, object]:
        output = Path(output_dir)
        try:
            if self.terminal_boundary == 9000 and resume_checkpoint is None:
                raise C1C2PhysicalError(
                    "9000 continuation must resume the authenticated 3000 checkpoint"
                )
            allowed = set(PAUSE_BOUNDARIES)
            if self.terminal_boundary == 9000:
                allowed.add(9000)
            if pause_at not in allowed or pause_at > self.terminal_boundary:
                raise C1C2PhysicalError("pause boundary is outside the cumulative ladder")
            if output.exists():
                if output.is_symlink() or not output.is_dir():
                    raise C1C2PhysicalError("output root is not a regular directory")
                if (output / "continuation-result.json").exists():
                    raise C1C2PhysicalError("refusing to overwrite continuation result")
                if (output / "result.json").exists() and self.terminal_boundary != 9000:
                    raise C1C2PhysicalError("refusing to resume a root containing terminal result")
                if resume_checkpoint is None and any(output.iterdir()):
                    raise C1C2PhysicalError("fresh run requires an empty output root")
            else:
                output.mkdir(parents=True, exist_ok=False)
            receipts: list[EpisodeReceipt] = []
            start = 0
            if resume_checkpoint is not None:
                checkpoint = Path(resume_checkpoint)
                if not checkpoint.resolve(strict=False).is_relative_to(output.resolve(strict=False)):
                    raise C1C2PhysicalError("resume checkpoint must be below the output root")
                start, receipts = self._validate_resume(_read_checkpoint(checkpoint))
                if pause_at <= start:
                    raise C1C2PhysicalError("pause boundary must advance the resume checkpoint")
                self._validate_history(output, start, receipts)
                stop_paths = sorted(output.glob("*integrity-stop.json"))
                if stop_paths:
                    if (
                        len(stop_paths) != 1
                        or self.repair_authority_path is None
                        or self.repair_authority_sha256 is None
                    ):
                        raise C1C2PhysicalError(
                            "resume after integrity STOP requires sealed repair authority"
                        )
                    _authenticate_repair_authority(
                        self.repair_authority_path,
                        expected_sha256=self.repair_authority_sha256,
                        plan_sha256=self.plan.plan_sha256,
                        stop_path=stop_paths[0],
                        resume_checkpoint=checkpoint,
                    )
                elif self.repair_authority_path is not None:
                    raise C1C2PhysicalError("repair authority supplied without an integrity STOP")
                if self.terminal_boundary == 9000:
                    if start != 3000:
                        raise C1C2PhysicalError("9000 continuation must resume checkpoint 3000")
                    self._validate_3000_continuation_anchor(output, checkpoint)
            for index in range(start, pause_at):
                world = self.plan.worlds[index]
                rows: list[EpisodeReceipt] = []
                for arm in ARMS:
                    row = self.adapter.run_episode(
                        arm=arm,
                        world=world,
                        plan_sha256=self.plan.plan_sha256,
                        resume_state=self.adapter.resume_state_for(arm),
                    )
                    rows.append(row)
                    receipts.append(row)
                _verify_matched_episode(rows, world)
                completed = index + 1
                if completed % CHECKPOINT_EVERY == 0:
                    _write_once(
                        output / "checkpoints" / f"checkpoint-{completed:06d}.json",
                        self._checkpoint_payload(completed, receipts),
                    )
                    _write_once(
                        output / "rungs" / f"rung-{completed:06d}.json",
                        self._rung_payload(completed, receipts),
                    )
            pooled = {
                arm: pool_receipts([row for row in receipts if row.arm == arm], arm=arm)
                for arm in ARMS
            }
            summary: dict[str, object] = {
                "completed_episode": pause_at,
                "planned_episodes": PLAN_EPISODES,
                "terminal_boundary": self.terminal_boundary,
                "plan_sha256": self.plan.plan_sha256,
                "arms": list(ARMS),
                "pooled_by_arm": pooled,
                "receipt_count": len(receipts),
                "terminal_result_emitted": False,
            }
            if pause_at == self.terminal_boundary:
                if self.terminal_boundary == 3000:
                    disposition = adjudicate_physical_disposition(
                        pooled,
                        completed_episodes=pause_at,
                        expected_episodes=3000,
                    )
                    if disposition["overall_token"] == INTEGRITY_STOP:
                        raise C1C2PhysicalError("terminal receipts failed integrity adjudication")
                    result: dict[str, object] = {
                        "schema": RESULT_SCHEMA,
                        "overall_token": disposition["overall_token"],
                        "reasons": disposition["reasons"],
                        "scientific_disposition_emitted": True,
                    }
                else:
                    result = {
                        "schema": CONTINUATION_RESULT_SCHEMA,
                        "authorized_from_3000_token": HELD,
                        "scientific_disposition_emitted": False,
                    }
                result.update({
                    "status": STATUS,
                    "split": SPLIT,
                    "completed_episode": pause_at,
                    "terminal_boundary": self.terminal_boundary,
                    "plan_sha256": self.plan.plan_sha256,
                    "arms": list(ARMS),
                    "pooled_by_arm": pooled,
                    "admission_mapping": self.admission_mapping,
                    "continuation_authority_sha256": (
                        None
                        if self.continuation_authority is None
                        else self.continuation_authority["authority_sha256"]
                    ),
                    "q3_evaluated": False,
                    "test_split_opened": False,
                    "episode_training": False,
                    "learner_update": False,
                    "claim_ceiling": CLAIM_CEILING,
                })
                if self.continuation_authority is not None:
                    result.update(
                        {
                            "continuation_authority": {
                                "path": self.continuation_authority["authority_path"],
                                "sha256": self.continuation_authority["authority_sha256"],
                            },
                            "owner_notification": {
                                "path": self.continuation_authority["owner_notification_path"],
                                "sha256": self.continuation_authority["owner_notification_sha256"],
                            },
                            "result_3000_sha256": self.continuation_authority["result_3000_sha256"],
                            "checkpoint_3000_sha256": self.continuation_authority["checkpoint_3000_sha256"],
                        }
                    )
                result_name = (
                    "continuation-result.json"
                    if self.terminal_boundary == 9000
                    else "result.json"
                )
                _write_once(output / result_name, result)
                summary["terminal_result_emitted"] = True
                if self.terminal_boundary == 3000:
                    summary["overall_token"] = result["overall_token"]
                    summary["reasons"] = result["reasons"]
                else:
                    summary["authorized_from_3000_token"] = HELD
            return summary
        except Exception as error:
            self._integrity_stop(output, error)
            if isinstance(error, C1C2PhysicalError):
                raise
            raise C1C2PhysicalError("physical evaluation failed integrity") from error


__all__ = [
    "ARMS",
    "BASELINE_CHECKPOINT_SHA256",
    "CHECKPOINT_EVERY",
    "CLAIM_CEILING",
    "CONTINUATION_AUTHORITY_SCHEMA",
    "CONTINUATION_RESULT_SCHEMA",
    "C1C2PhysicalError",
    "EpisodeReceipt",
    "EvaluationPlan",
    "FALSIFIED",
    "FIELD_COMPONENT",
    "FixedPolicyEpisodeAdapter",
    "FixedPolicyEvaluationRunner",
    "FrozenBaselinePolicy",
    "FrozenLearnedPolicy",
    "HELD",
    "HELD_TOKEN_SHA256",
    "INTEGRITY_STOP",
    "LEARNED_ARMS",
    "PAUSE_BOUNDARIES",
    "RECEIPT_SCHEMA",
    "REPAIR_AUTHORITY_SCHEMA",
    "ROUTES",
    "RESULT_SCHEMA",
    "SCHEMA",
    "SPLIT",
    "STATUS",
    "STEPS",
    "TERMINAL_BOUNDARIES",
    "USERS",
    "WorldBinding",
    "aggregate_last_outcomes",
    "adjudicate_physical_disposition",
    "authenticate_runtime_admission",
    "canonical_sha256",
    "file_sha256",
    "load_baseline_policy",
    "load_learned_two_route_checkpoint",
    "pool_receipts",
    "select_learned_q12_actions",
]
