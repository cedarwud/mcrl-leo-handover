#!/usr/bin/env python3
"""V0.23 provisional physical episode adapter.

This file is an execution seam, not a new simulator.  A caller supplies a
frozen TLE archive, a factory for the repository's :class:`TrainerEnvironment`
and the deterministic environment RNG factory.  The adapter then executes
only the already-authenticated V0.20 Q1/Q2 background on two paired labels:

``BASELINE``
    the frozen Q1+Q2 decision;
``DROP_C3``
    the same decision with no third component evaluated or called.

There is intentionally no optimizer, replay buffer, source collection,
TEST split, or authority mutation here.  The returned receipts are explicitly
``PROVISIONAL_PRE_GATE`` and are evidence for a later controller decision,
not a gate verdict.  The module has no default run or launch side effect.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, TypeAlias

import numpy as np

try:  # torch is an optional project dependency outside the train extra.
    import torch
except ImportError:  # pragma: no cover - exercised by non-train installs
    torch = None  # type: ignore[assignment]


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

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


SCHEMA = "multi-catfish-mcrl-v023-provisional-physical-episode-v1"
RECEIPT_SCHEMA = f"{SCHEMA}-receipt"
CHECKPOINT_SCHEMA = f"{SCHEMA}-checkpoint"
RESULT_SCHEMA = f"{SCHEMA}-result"
STATUS = "PROVISIONAL_PRE_GATE"
EVALUATION_SPLIT = "EVALUATION_DEVELOPMENT"
ARMS = ("BASELINE", "DROP_C3")
DROP_C3_ONLY_ARMS = ("DROP_C3",)
CHECKPOINT_EVERY = 100
USERS = 100
STEPS = 10
LINEAGE = 2026092101
Q1_UPDATES = 10
Q2_UPDATES = 3000
Q2_INITIALIZATION = 2026108101
FIELD_COMPONENT = "MCRL_V020_REPRICED_C3_GATE_V1"
V020_CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v020-repriced-q1-q2-source-fit-v1-checkpoint"
V020_CHECKPOINT_SHA256 = (
    "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc"
)
V020_AUTHORITY_SHA256 = (
    "50d32dae11b2906bb23a25893f4ba5c11d0f88197ee94fe7cd216677e8703d48"
)
V020_AUTHORITY_FILE_SHA256 = (
    "a05ee801c8f9d640b55f8ec984d874f149c30b868d1706d998f7e2053520078e"
)
V020_SOURCE_CONTRACT_SHA256 = (
    "ea36414aac87b3ef5ba48dbe753e73ff21a0e164d54cdb3edbb899b509edd48c"
)
V020_REPRICING_CONTRACT_SHA256 = (
    "34732dd3f65ffebf760313c2ffd235e0ecbd406ba6065dbce5635778550ef4a9"
)
V020_CHECKPOINT_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v020-c3-source-audit"
    / "repriced-q1-q2-fit"
    / "lineage-2026092101"
    / "checkpoints"
    / "lineage-2026092101-q2init-2026108101-rung-003000.pt"
)
V020_AUTHORITY_PATH = V020_CHECKPOINT_PATH.parents[1] / "authority.json"
V020_SOURCE_CONTRACT_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v020-c3-source-audit"
    / "Q1-Q2-REPRICED-SUPERVISED-EXECUTION-CONTRACT-2026-09-04.md"
)
V020_REPRICING_CONTRACT_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v020-c3-source-audit"
    / "Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md"
)
DEVELOPMENT_CONTRACT_SCHEMA = (
    "multi-catfish-mcrl-v023-drop-c3-development-evaluation-contract-v1"
)
DEVELOPMENT_CONTRACT_PATH = (
    HERE / "V023-DROPC3-DEVELOPMENT-EVALUATION-CONTRACT-2026-09-06.md"
)
DEVELOPMENT_CONTRACT_SHA256 = (
    "7ff5d639cef0310bdbf66a54b6a8513aff0ff9460554543cf33e8c39e5673885"
)
DEVELOPMENT_PREREG_PATH = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
DEVELOPMENT_PREREG_SHA256 = (
    "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
)
DEVELOPMENT_PREREG_RECORD_DIGEST = (
    "3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4"
)


class V023PhysicalError(RuntimeError):
    """The provisional physical boundary or receipt contract failed."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023PhysicalError(f"{field} must be a lowercase SHA-256")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise V023PhysicalError(f"{field} must be a positive integer")
    result = int(value)
    if result <= 0:
        raise V023PhysicalError(f"{field} must be a positive integer")
    return result


def file_sha256(path: str | Path) -> str:
    """Hash one regular file without following a symlink target silently."""

    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023PhysicalError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    try:
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise V023PhysicalError(f"cannot read file: {source}") from error
    return digest.hexdigest()


def _jsonable(value: object) -> object:
    """Convert NumPy/Torch state into lossless, finite JSON values."""

    if isinstance(value, np.ndarray):
        return {
            "__ndarray__": True,
            "dtype": value.dtype.str,
            "shape": list(value.shape),
            "values": [_jsonable(item) for item in value.tolist()],
        }
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if torch is not None and isinstance(value, torch.Tensor):
        return _jsonable(value.detach().cpu().numpy())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise V023PhysicalError("canonical JSON cannot contain non-finite floats")
        return value
    raise V023PhysicalError(f"unsupported canonical JSON value: {type(value).__name__}")


def _restore_jsonable(value: object) -> object:
    if isinstance(value, list):
        return [_restore_jsonable(item) for item in value]
    if isinstance(value, Mapping):
        if value.get("__ndarray__") is True:
            try:
                dtype = np.dtype(str(value["dtype"]))
                shape = tuple(int(item) for item in value["shape"])
                array = np.asarray(
                    [_restore_jsonable(item) for item in value["values"]],
                    dtype=dtype,
                ).reshape(shape)
            except (KeyError, TypeError, ValueError) as error:
                raise V023PhysicalError("invalid encoded ndarray state") from error
            return array
        return {key: _restore_jsonable(item) for key, item in value.items()}
    return value


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            _jsonable(payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023PhysicalError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _read_json(path: str | Path, *, field: str) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V023PhysicalError(f"cannot read {field}: {source}") from error
    if not isinstance(payload, dict):
        raise V023PhysicalError(f"{field} must be a JSON object")
    return payload


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
        raise V023PhysicalError("frozen network has no state_dict")
    digest = hashlib.sha256()
    try:
        values = state()
        for name, value in values.items():
            tensor = value.detach().cpu().contiguous()
            digest.update(str(name).encode("utf-8"))
            digest.update(str(tensor.dtype).encode("ascii"))
            digest.update(repr(tuple(tensor.shape)).encode("ascii"))
            digest.update(tensor.numpy().tobytes(order="C"))
    except (AttributeError, TypeError, ValueError, RuntimeError) as error:
        raise V023PhysicalError("cannot hash frozen network parameters") from error
    return digest.hexdigest()


def _surface(network: Any, states: object, masks: object, *, field: str) -> np.ndarray:
    if torch is None:
        raise V023PhysicalError("physical Q1/Q2 inference requires torch")
    values = np.asarray(states, dtype=np.float32)
    legal = np.asarray(masks)
    if values.ndim != 2 or legal.dtype != np.bool_ or legal.shape != (
        values.shape[0],
        28,
    ):
        raise V023PhysicalError(f"{field} state/mask input is malformed")
    if not np.all(np.isfinite(values)) or not np.all(np.any(legal, axis=1)):
        raise V023PhysicalError(f"{field} state/mask input is invalid")
    try:
        network.eval()
        network.requires_grad_(False)
        with torch.no_grad():
            output = network(
                torch.tensor(values, dtype=torch.float32),
                torch.tensor(legal, dtype=torch.bool),
            )
    except (AttributeError, TypeError, RuntimeError, ValueError) as error:
        raise V023PhysicalError(f"{field} inference failed") from error
    try:
        result = np.asarray(output.detach().cpu().numpy(), dtype=np.float64)
    except (AttributeError, TypeError, ValueError) as error:
        raise V023PhysicalError(f"{field} inference returned a non-tensor") from error
    if result.shape != legal.shape or not np.all(np.isfinite(result)):
        raise V023PhysicalError(f"{field} surface is malformed")
    return result


def _masked_argmax(scores: object, masks: object) -> np.ndarray:
    values = np.asarray(scores, dtype=np.float64)
    legal = np.asarray(masks)
    if values.ndim != 2 or values.shape[1] != 28:
        raise V023PhysicalError("score surface must have shape (U,28)")
    if legal.dtype != np.bool_ or legal.shape != values.shape:
        raise V023PhysicalError("score mask is not a native Boolean surface")
    if not np.all(np.isfinite(values)) or not np.all(np.any(legal, axis=1)):
        raise V023PhysicalError("score surface is non-finite or has an empty row")
    return np.argmax(np.where(legal, values, -np.inf), axis=1).astype(np.int64)


def _action_trace_update(digest: "hashlib._Hash", actions: object) -> None:
    values = np.ascontiguousarray(np.asarray(actions, dtype=np.int64))
    digest.update(values.dtype.str.encode("ascii"))
    digest.update(repr(tuple(values.shape)).encode("ascii"))
    digest.update(values.tobytes(order="C"))


def _rng_state(rng: object) -> object:
    bit_generator = getattr(rng, "bit_generator", None)
    state = getattr(bit_generator, "state", None)
    if state is None:
        raise V023PhysicalError("RNG factory returned an object without bit_generator.state")
    return copy.deepcopy(_jsonable(state))


def _restore_rng_state(rng: object, state: object) -> None:
    bit_generator = getattr(rng, "bit_generator", None)
    if bit_generator is None:
        raise V023PhysicalError("RNG object has no bit_generator")
    try:
        bit_generator.state = _restore_jsonable(copy.deepcopy(state))
    except (KeyError, TypeError, ValueError) as error:
        raise V023PhysicalError("cannot restore RNG state") from error


def _validate_actions(actions: object, masks: object) -> np.ndarray:
    values = np.asarray(actions)
    legal = np.asarray(masks)
    if values.ndim != 1 or values.dtype.kind not in "iu" or values.dtype == np.bool_:
        raise V023PhysicalError("action vector is malformed")
    if legal.dtype != np.bool_ or legal.ndim != 2 or legal.shape[0] != values.size:
        raise V023PhysicalError("action mask is malformed")
    if legal.shape[1] != 28 or not np.all(np.any(legal, axis=1)):
        raise V023PhysicalError("action mask is empty or has the wrong width")
    result = np.asarray(values, dtype=np.int64)
    rows = np.arange(result.size)
    if np.any(result < 0) or np.any(result >= 28) or np.any(~legal[rows, result]):
        raise V023PhysicalError("selected action is outside the common safe mask")
    return np.array(result, dtype=np.int64, copy=True, order="C")


@dataclass(frozen=True)
class V020CheckpointBinding:
    """Exact bytes and metadata binding for the current V0.20 Q1/Q2 merge."""

    checkpoint_path: Path = V020_CHECKPOINT_PATH
    checkpoint_sha256: str = V020_CHECKPOINT_SHA256
    authority_path: Path = V020_AUTHORITY_PATH
    authority_sha256: str = V020_AUTHORITY_SHA256
    authority_file_sha256: str = V020_AUTHORITY_FILE_SHA256
    source_contract_path: Path = V020_SOURCE_CONTRACT_PATH
    source_contract_sha256: str = V020_SOURCE_CONTRACT_SHA256
    repricing_contract_path: Path = V020_REPRICING_CONTRACT_PATH
    repricing_contract_sha256: str = V020_REPRICING_CONTRACT_SHA256
    lineage: int = LINEAGE
    q1_update_count: int = Q1_UPDATES
    q2_update_count: int = Q2_UPDATES
    q2_initialization: int = Q2_INITIALIZATION

    def verify_files(self) -> None:
        expected_identity = {
            "lineage": LINEAGE,
            "q1_update_count": Q1_UPDATES,
            "q2_update_count": Q2_UPDATES,
            "q2_initialization": Q2_INITIALIZATION,
            "checkpoint_sha256": V020_CHECKPOINT_SHA256,
            "authority_sha256": V020_AUTHORITY_SHA256,
            "authority_file_sha256": V020_AUTHORITY_FILE_SHA256,
            "source_contract_sha256": V020_SOURCE_CONTRACT_SHA256,
            "repricing_contract_sha256": V020_REPRICING_CONTRACT_SHA256,
        }
        if any(getattr(self, key) != value for key, value in expected_identity.items()):
            raise V023PhysicalError("checkpoint binding is not the current V0.20 lineage")
        _digest(self.checkpoint_sha256, field="checkpoint_sha256")
        _digest(self.authority_sha256, field="authority_sha256")
        _digest(self.authority_file_sha256, field="authority_file_sha256")
        _digest(self.source_contract_sha256, field="source_contract_sha256")
        _digest(self.repricing_contract_sha256, field="repricing_contract_sha256")
        if file_sha256(self.checkpoint_path) != self.checkpoint_sha256:
            raise V023PhysicalError("V0.20 checkpoint bytes changed after authentication")
        if file_sha256(self.authority_path) != self.authority_file_sha256:
            raise V023PhysicalError("V0.20 authority bytes changed after authentication")
        if file_sha256(self.source_contract_path) != self.source_contract_sha256:
            raise V023PhysicalError("V0.20 source contract bytes changed after authentication")
        if file_sha256(self.repricing_contract_path) != self.repricing_contract_sha256:
            raise V023PhysicalError("V0.20 repricing contract bytes changed after authentication")

    def as_dict(self) -> dict[str, object]:
        return {
            "lineage": self.lineage,
            "q1_update_count": self.q1_update_count,
            "q2_update_count": self.q2_update_count,
            "q2_initialization": self.q2_initialization,
            "checkpoint_path": str(Path(self.checkpoint_path).resolve()),
            "checkpoint_sha256": self.checkpoint_sha256,
            "authority_path": str(Path(self.authority_path).resolve()),
            "authority_sha256": self.authority_sha256,
            "authority_file_sha256": self.authority_file_sha256,
            "source_contract_path": str(Path(self.source_contract_path).resolve()),
            "source_contract_sha256": self.source_contract_sha256,
            "repricing_contract_path": str(Path(self.repricing_contract_path).resolve()),
            "repricing_contract_sha256": self.repricing_contract_sha256,
        }


@dataclass(frozen=True)
class FrozenV020Q12:
    """Frozen Q1/Q2 networks loaded from one authenticated merged checkpoint."""

    q1: Any
    q2: Any
    binding: V020CheckpointBinding
    q1_parameter_sha256: str
    q2_parameter_sha256: str
    q1_receipt: Mapping[str, object]
    q2_receipt: Mapping[str, object]

    def verify(self) -> None:
        self.binding.verify_files()
        for name, network, claimed in (
            ("Q1", self.q1, self.q1_parameter_sha256),
            ("Q2", self.q2, self.q2_parameter_sha256),
        ):
            try:
                network.eval()
                network.requires_grad_(False)
                observed = _parameter_sha256(network)
            except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                raise V023PhysicalError(f"{name} network is not a frozen torch module") from error
            if any(parameter.requires_grad for parameter in network.parameters()):
                raise V023PhysicalError(f"{name} network remains trainable")
            if observed != _digest(claimed, field=f"{name} parameter_sha256"):
                raise V023PhysicalError(f"{name} parameter digest disagrees with bundle")


def _tuple_fields(payload: Mapping[str, object], names: Sequence[str]) -> dict[str, object]:
    result = dict(payload)
    for name in names:
        value = result.get(name)
        if isinstance(value, list):
            result[name] = tuple(value)
    return result


def load_v020_q12(binding: V020CheckpointBinding | None = None) -> FrozenV020Q12:
    """Load and freeze only Q1 and Q2 from the authenticated V0.20 merge."""

    if torch is None:
        raise V023PhysicalError("loading the V0.20 checkpoint requires torch")
    selected = binding or V020CheckpointBinding()
    selected.verify_files()
    try:
        payload = torch.load(selected.checkpoint_path, map_location="cpu", weights_only=False)
    except (OSError, EOFError, RuntimeError, TypeError, ValueError) as error:
        raise V023PhysicalError("cannot load V0.20 Q1/Q2 checkpoint") from error
    if not isinstance(payload, Mapping):
        raise V023PhysicalError("V0.20 checkpoint must be a mapping")
    expected = {
        "schema": V020_CHECKPOINT_SCHEMA,
        "lineage": selected.lineage,
        "q2_initialization": selected.q2_initialization,
        "q1_update_count": selected.q1_update_count,
        "q2_update_count": selected.q2_update_count,
        "q1_head_index": 0,
        "authority_sha256": selected.authority_sha256,
        "test_split_opened": False,
        "simulator_run": False,
        "episode_training": False,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise V023PhysicalError(f"V0.20 checkpoint metadata mismatch: {field}")
    q1_payload = payload.get("q1")
    q2_payload = payload.get("q2")
    if not isinstance(q1_payload, Mapping) or not isinstance(q2_payload, Mapping):
        raise V023PhysicalError("V0.20 checkpoint lacks Q1/Q2 payloads")
    try:
        from mcrl.algorithms.ee_axis_action_shared_meanmax import (
            EEAxisMaskedMeanMaxConfig,
            EEAxisMaskedMeanMaxTrainer,
        )
        from mcrl.algorithms.ee_axis_v014_head import (
            EEAxisV014HeadConfig,
            EEAxisV014PairwiseLearner,
        )

        q1_config_raw = q1_payload.get("config")
        q2_config_raw = q2_payload.get("config")
        if not isinstance(q1_config_raw, Mapping) or not isinstance(q2_config_raw, Mapping):
            raise V023PhysicalError("V0.20 Q1/Q2 config is malformed")
        q1_config = EEAxisMaskedMeanMaxConfig(
            **_tuple_fields(q1_config_raw, ("hidden_layers", "loss_weights"))
        )
        q1_trainer = EEAxisMaskedMeanMaxTrainer(
            q1_config, train_seed=selected.lineage, device="cpu"
        )
        if q1_trainer.load_checkpoint_state(q1_payload) != selected.q1_update_count:
            raise V023PhysicalError("V0.20 Q1 update count drifted")
        q1 = q1_trainer.q_nets[0]
        q2_config = EEAxisV014HeadConfig(
            **_tuple_fields(q2_config_raw, ("hidden_layers",))
        )
        q2_learner = EEAxisV014PairwiseLearner(
            q2_config, train_seed=selected.q2_initialization, device="cpu"
        )
        if q2_learner.load_checkpoint_state(q2_payload) != selected.q2_update_count:
            raise V023PhysicalError("V0.20 Q2 update count drifted")
        q2 = q2_learner.q
    except V023PhysicalError:
        raise
    except (ImportError, KeyError, TypeError, ValueError, RuntimeError) as error:
        raise V023PhysicalError("V0.20 Q1/Q2 network state is malformed") from error
    q1.eval()
    q2.eval()
    q1.requires_grad_(False)
    q2.requires_grad_(False)
    q1_receipt = {
        "checkpoint_path": str(Path(selected.checkpoint_path).resolve()),
        "checkpoint_sha256": selected.checkpoint_sha256,
        "combined_checkpoint": True,
        "head_index": 0,
        "update_count": selected.q1_update_count,
        "train_seed": selected.lineage,
        "config": _jsonable(asdict(q1_config)),
    }
    q2_receipt = {
        "checkpoint_path": str(Path(selected.checkpoint_path).resolve()),
        "checkpoint_sha256": selected.checkpoint_sha256,
        "combined_checkpoint": True,
        "update_count": selected.q2_update_count,
        "train_seed": selected.q2_initialization,
        "config": _jsonable(asdict(q2_config)),
    }
    bundle = FrozenV020Q12(
        q1=q1,
        q2=q2,
        binding=selected,
        q1_parameter_sha256=_parameter_sha256(q1),
        q2_parameter_sha256=_parameter_sha256(q2),
        q1_receipt=q1_receipt,
        q2_receipt=q2_receipt,
    )
    bundle.verify()
    return bundle


@dataclass(frozen=True)
class V023WorldBinding:
    """One paired world identity shared by both arms."""

    episode_index: int
    world_id: str
    world_seed: int
    field_root_digest: str

    def verify(self, *, component: str) -> None:
        if _positive_int(self.episode_index, field="episode_index") != self.episode_index:
            raise V023PhysicalError("episode_index is malformed")
        if not isinstance(self.world_id, str) or not self.world_id:
            raise V023PhysicalError("world_id must be a non-empty string")
        seed = _positive_int(self.world_seed, field="world_seed")
        expected = KeyedFadingField.from_components(component, seed).root_digest
        if _digest(self.field_root_digest, field="field_root_digest") != expected:
            raise V023PhysicalError("world field root does not match keyed components")


@dataclass(frozen=True)
class V023EpisodePlan:
    """Frozen world grid for one provisional fixed-policy evaluation run.

    The default is the paired BASELINE/DROP_C3 panel.  A production
    development timing run may explicitly select ``DROP_C3_ONLY_ARMS``; it
    then emits no BASELINE artifact and performs no cross-arm comparison.
    """

    worlds: tuple[V023WorldBinding, ...]
    checkpoint_every: int = CHECKPOINT_EVERY
    integration_only: bool = False
    field_component: str = FIELD_COMPONENT
    lineage: int = LINEAGE
    arms: tuple[str, ...] = ARMS
    evaluation_contract_sha256: str = DEVELOPMENT_CONTRACT_SHA256

    def verify(self, *, checkpoint: V020CheckpointBinding) -> None:
        if self.field_component != FIELD_COMPONENT:
            raise V023PhysicalError("V0.23 field component is not the V0.20 namespace")
        if self.lineage != checkpoint.lineage:
            raise V023PhysicalError("plan lineage disagrees with checkpoint lineage")
        if self.arms not in (ARMS, DROP_C3_ONLY_ARMS):
            raise V023PhysicalError(
                "plan arms must be BASELINE/DROP_C3 or explicit DROP_C3-only"
            )
        if _digest(
            self.evaluation_contract_sha256,
            field="evaluation_contract_sha256",
        ) != DEVELOPMENT_CONTRACT_SHA256:
            raise V023PhysicalError("plan is not bound to the development contract")
        if file_sha256(DEVELOPMENT_CONTRACT_PATH) != DEVELOPMENT_CONTRACT_SHA256:
            raise V023PhysicalError("development contract bytes changed")
        if self.checkpoint_every != CHECKPOINT_EVERY:
            raise V023PhysicalError("checkpoint cadence is fixed at every 100 episodes")
        if not self.worlds:
            raise V023PhysicalError("paired world grid must not be empty")
        if self.integration_only and len(self.worlds) != 1:
            raise V023PhysicalError("integration_only is reserved for one episode")
        indices = tuple(int(world.episode_index) for world in self.worlds)
        if indices != tuple(range(1, len(self.worlds) + 1)):
            raise V023PhysicalError("world episode indices must be contiguous from one")
        ids = tuple(world.world_id for world in self.worlds)
        seeds = tuple(int(world.world_seed) for world in self.worlds)
        if len(set(ids)) != len(ids) or len(set(seeds)) != len(seeds):
            raise V023PhysicalError("paired world ids and seeds must be unique")
        for world in self.worlds:
            world.verify(component=self.field_component)
        if len(self.worlds) % self.checkpoint_every and not self.integration_only:
            raise V023PhysicalError(
                "production plans must contain complete 100-episode checkpoint blocks"
            )

    @property
    def plan_sha256(self) -> str:
        return canonical_sha256(
            {
                "schema": SCHEMA,
                "field_component": self.field_component,
                "lineage": self.lineage,
                "checkpoint_every": self.checkpoint_every,
                "integration_only": self.integration_only,
                "arms": list(self.arms),
                "evaluation_contract_sha256": self.evaluation_contract_sha256,
                "worlds": [asdict(world) for world in self.worlds],
            }
        )


@dataclass(frozen=True)
class V023EpisodeReceipt:
    schema: str
    status: str
    split: str
    arm: str
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
    checkpoint_binding: Mapping[str, object]
    q1_parameter_sha256: str
    q2_parameter_sha256: str
    q3_evaluated: bool
    test_split_opened: bool
    episode_training: bool
    learner_update: bool
    evaluation_contract_sha256: str = DEVELOPMENT_CONTRACT_SHA256

    def verify(self) -> None:
        if self.schema != RECEIPT_SCHEMA or self.status != STATUS:
            raise V023PhysicalError("episode receipt schema/status is not provisional")
        if self.split != EVALUATION_SPLIT or self.arm not in ARMS:
            raise V023PhysicalError("episode receipt split or arm is outside V0.23")
        if self.field_component != FIELD_COMPONENT:
            raise V023PhysicalError("episode receipt field is outside V0.23")
        if _digest(
            self.evaluation_contract_sha256,
            field="evaluation_contract_sha256",
        ) != DEVELOPMENT_CONTRACT_SHA256:
            raise V023PhysicalError("episode receipt is not bound to development contract")
        _positive_int(self.episode_index, field="episode_index")
        _positive_int(self.world_seed, field="world_seed")
        if not isinstance(self.world_id, str) or not self.world_id:
            raise V023PhysicalError("episode receipt world_id is malformed")
        if self.users != USERS or self.steps != STEPS:
            raise V023PhysicalError("V0.23 physical episode dimensions drifted")
        for field in (
            "initial_world_sha256",
            "field_root_digest",
            "action_trace_sha256",
            "q1_parameter_sha256",
            "q2_parameter_sha256",
        ):
            _digest(getattr(self, field), field=field)
        if not math.isfinite(self.decision_interval_s) or self.decision_interval_s <= 0:
            raise V023PhysicalError("decision interval is not finite and positive")
        if not math.isfinite(self.total_bits) or self.total_bits < 0:
            raise V023PhysicalError("total_bits is not finite and non-negative")
        if not math.isfinite(self.total_energy_j) or self.total_energy_j <= 0:
            raise V023PhysicalError("total_energy_j is not finite and positive")
        expected_ratio = self.total_bits / self.total_energy_j
        if not math.isfinite(self.ratio_of_sums_ee_bits_per_j) or not math.isclose(
            self.ratio_of_sums_ee_bits_per_j, expected_ratio, rel_tol=0.0, abs_tol=1e-12
        ):
            raise V023PhysicalError("episode EE is not the pooled ratio of sums")
        if self.service_opportunities != self.users * self.steps:
            raise V023PhysicalError("service opportunity count is not U times H")
        if not 0 <= self.served_user_steps <= self.service_opportunities:
            raise V023PhysicalError("served count is outside service opportunities")
        if not math.isclose(
            self.service_fraction,
            self.served_user_steps / self.service_opportunities,
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise V023PhysicalError("service fraction is inconsistent with counts")
        if self.q3_evaluated or self.test_split_opened or self.episode_training or self.learner_update:
            raise V023PhysicalError("receipt crossed a forbidden pre-gate boundary")
        binding = self.checkpoint_binding
        if not isinstance(binding, Mapping):
            raise V023PhysicalError("receipt is missing checkpoint binding")
        expected_binding = {
            "lineage": LINEAGE,
            "q1_update_count": Q1_UPDATES,
            "q2_update_count": Q2_UPDATES,
            "q2_initialization": Q2_INITIALIZATION,
            "checkpoint_sha256": V020_CHECKPOINT_SHA256,
            "authority_sha256": V020_AUTHORITY_SHA256,
            "authority_file_sha256": V020_AUTHORITY_FILE_SHA256,
            "source_contract_sha256": V020_SOURCE_CONTRACT_SHA256,
            "repricing_contract_sha256": V020_REPRICING_CONTRACT_SHA256,
        }
        if any(binding.get(key) != value for key, value in expected_binding.items()):
            raise V023PhysicalError("receipt checkpoint binding is not current V0.20 lineage")
        expected_field = KeyedFadingField.from_components(
            FIELD_COMPONENT, self.world_seed
        ).root_digest
        if binding.get("checkpoint_path") is None or self.field_root_digest != expected_field:
            raise V023PhysicalError("receipt field/checkpoint binding is not canonical")

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["checkpoint_binding"] = dict(self.checkpoint_binding)
        return payload


def _observation_digest(native: Any) -> str:
    try:
        state = np.asarray(native.state_matrix, dtype=np.float32)
        masks = np.asarray(native.action_masks, dtype=np.bool_)
    except (AttributeError, TypeError, ValueError) as error:
        raise V023PhysicalError("native initial observation is malformed") from error
    if state.ndim != 2 or masks.shape != (state.shape[0], 28):
        raise V023PhysicalError("native initial observation has the wrong shape")
    return canonical_sha256(
        {
            "state_dtype": state.dtype.str,
            "state_shape": list(state.shape),
            "state_sha256": _array_sha256(state),
            "mask_sha256": _array_sha256(masks),
        }
    )


EnvironmentFactory: TypeAlias = Callable[[Any, int], TrainerEnvironment]
RngFactory: TypeAlias = Callable[[int], Sequence[np.random.Generator]]
FieldFactory: TypeAlias = Callable[[str, int], KeyedFadingField]


class V023PhysicalEpisodeAdapter:
    """Execute one real TrainerEnvironment episode for BASELINE or DROP_C3."""

    def __init__(
        self,
        *,
        frozen: FrozenV020Q12,
        archive: Any,
        environment_factory: EnvironmentFactory,
        rng_factory: RngFactory,
        field_factory: FieldFactory | None = None,
        users: int = USERS,
        steps: int = STEPS,
    ) -> None:
        frozen.verify()
        if not callable(environment_factory) or not callable(rng_factory):
            raise V023PhysicalError("environment_factory and rng_factory are required")
        if users != USERS or steps != STEPS:
            raise V023PhysicalError("V0.23 physical episodes use 100 users and ten steps")
        self.frozen = frozen
        self.archive = archive
        self.environment_factory = environment_factory
        self.rng_factory = rng_factory
        self.field_factory = field_factory or (
            lambda component, seed: KeyedFadingField.from_components(component, seed)
        )
        if not callable(self.field_factory):
            raise V023PhysicalError("field_factory must be callable")
        self.users = int(users)
        self.steps = int(steps)
        self._resume_by_arm: dict[str, Mapping[str, object]] = {}

    def field_for(self, *, world_seed: int, expected_root_digest: str) -> KeyedFadingField:
        seed = _positive_int(world_seed, field="world_seed")
        expected = _digest(expected_root_digest, field="field_root_digest")
        try:
            field = self.field_factory(FIELD_COMPONENT, seed)
        except (TypeError, ValueError, RuntimeError) as error:
            raise V023PhysicalError("field_factory failed") from error
        if not isinstance(field, KeyedFadingField):
            raise V023PhysicalError("field_factory must return KeyedFadingField")
        canonical = KeyedFadingField.from_components(FIELD_COMPONENT, seed)
        if field.root_digest != canonical.root_digest or field.root_digest != expected:
            raise V023PhysicalError("field root does not match common keyed world")
        return field

    def _make_environment(self, field: KeyedFadingField) -> tuple[TrainerEnvironment, Any]:
        try:
            environment = self.environment_factory(self.archive, self.users)
        except Exception as error:  # pragma: no cover - factory is runtime-specific
            raise V023PhysicalError("TrainerEnvironment factory failed") from error
        if not isinstance(environment, TrainerEnvironment):
            raise V023PhysicalError("environment_factory must return TrainerEnvironment")
        step_environment = getattr(environment, "environment", None)
        if step_environment is None or not hasattr(step_environment, "_fading_field"):
            raise V023PhysicalError("TrainerEnvironment lacks fading-field boundary")
        step_environment._fading_field = field
        config = getattr(environment, "config", None)
        if config is None or config.num_users != self.users or config.steps_per_episode != self.steps:
            raise V023PhysicalError("TrainerEnvironment dimensions are not 100 by 10")
        return environment, step_environment

    def _rngs(self, world_seed: int) -> tuple[Sequence[np.random.Generator], np.random.Generator]:
        try:
            values = tuple(self.rng_factory(int(world_seed)))
        except Exception as error:  # pragma: no cover - factory is runtime-specific
            raise V023PhysicalError("RNG factory failed") from error
        if len(values) < 2:
            raise V023PhysicalError("rng_factory must return environment and mobility RNGs")
        if any(not isinstance(value, np.random.Generator) for value in values[:2]):
            raise V023PhysicalError("environment RNGs must be NumPy Generators")
        return values, values[0]

    def _restore_resume(self, environment: TrainerEnvironment, state: Mapping[str, object] | None) -> None:
        if not state:
            return
        saved_environment = state.get("environment_training_state")
        if not isinstance(saved_environment, Mapping):
            raise V023PhysicalError("resume state lacks environment_training_state")
        loader = getattr(environment, "load_training_state_dict", None)
        if not callable(loader):
            loader = getattr(environment, "load_resume_state_dict", None)
        if not callable(loader):
            raise V023PhysicalError("TrainerEnvironment cannot restore training state")
        try:
            loader(_restore_jsonable(saved_environment))
        except (KeyError, TypeError, ValueError, RuntimeError) as error:
            raise V023PhysicalError("TrainerEnvironment resume state is invalid") from error
        if torch is not None and state.get("torch_rng_state") is not None:
            try:
                torch_state = _restore_jsonable(state["torch_rng_state"])
                if not isinstance(torch_state, np.ndarray):
                    torch_state = np.asarray(torch_state, dtype=np.uint8)
                torch.set_rng_state(torch.tensor(torch_state, dtype=torch.uint8))
            except (KeyError, TypeError, ValueError, RuntimeError) as error:
                raise V023PhysicalError("checkpoint torch RNG state is invalid") from error

    def resume_state_for(self, arm: str) -> Mapping[str, object] | None:
        if arm not in ARMS:
            raise V023PhysicalError(f"unknown arm: {arm}")
        return self._resume_by_arm.get(arm)

    def restore_resume_states(self, states: Mapping[str, object]) -> None:
        if not isinstance(states, Mapping):
            raise V023PhysicalError("checkpoint resume states must be a mapping")
        for arm in ARMS:
            value = states.get(arm)
            if value is not None and not isinstance(value, Mapping):
                raise V023PhysicalError(f"resume state for {arm} is malformed")
            if isinstance(value, Mapping):
                self._resume_by_arm[arm] = dict(value)

    def run_episode(
        self,
        *,
        arm: str,
        world: V023WorldBinding,
        resume_state: Mapping[str, object] | None = None,
    ) -> V023EpisodeReceipt:
        if arm not in ARMS:
            raise V023PhysicalError(f"unknown V0.23 arm: {arm}")
        world.verify(component=FIELD_COMPONENT)
        if resume_state is not None:
            if not isinstance(resume_state, Mapping):
                raise V023PhysicalError("resume state must be a mapping")
            if resume_state.get("schema") != f"{SCHEMA}-resume-state":
                raise V023PhysicalError("resume state schema is not provisional")
            if resume_state.get("arm") != arm:
                raise V023PhysicalError("resume state arm disagrees with episode arm")
            if resume_state.get("episode_index") != world.episode_index - 1:
                raise V023PhysicalError("resume state is not from the preceding world")
            if not isinstance(resume_state.get("world_id"), str) or not resume_state.get("world_id"):
                raise V023PhysicalError("resume state lacks preceding world identity")
            previous_seed = _positive_int(
                resume_state.get("world_seed"), field="resume world_seed"
            )
            previous_root = _digest(
                resume_state.get("field_root_digest"),
                field="resume field_root_digest",
            )
            if previous_root != KeyedFadingField.from_components(
                FIELD_COMPONENT, previous_seed
            ).root_digest:
                raise V023PhysicalError("resume state field root is not canonical")
            if (
                resume_state.get("q1_parameter_sha256") != self.frozen.q1_parameter_sha256
                or resume_state.get("q2_parameter_sha256") != self.frozen.q2_parameter_sha256
            ):
                raise V023PhysicalError("resume state network digest disagrees")
        field = self.field_for(
            world_seed=world.world_seed,
            expected_root_digest=world.field_root_digest,
        )
        environment, step_environment = self._make_environment(field)
        rngs, env_rng = self._rngs(world.world_seed)
        if resume_state is not None:
            saved_rng_states = resume_state.get("rng_states")
            if not isinstance(saved_rng_states, Sequence) or isinstance(
                saved_rng_states, (str, bytes)
            ) or len(saved_rng_states) != len(rngs):
                raise V023PhysicalError("resume state RNG stream count drifted")
            for encoded_state in saved_rng_states:
                probe = np.random.default_rng()
                _restore_rng_state(probe, encoded_state)
        self._restore_resume(environment, resume_state)
        try:
            reset_result = environment.reset(rngs[0], rngs[1])
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            raise V023PhysicalError("canonical TrainerEnvironment reset failed") from error
        if not isinstance(reset_result, tuple) or len(reset_result) != 3:
            raise V023PhysicalError("TrainerEnvironment.reset must return three values")
        _states, _masks, observation = reset_result
        if getattr(observation, "num_users", self.users) != self.users:
            raise V023PhysicalError("reset observation user count drifted")
        try:
            interval_s = float(step_environment.driver.config.ephemeris.time_step_s)
        except (AttributeError, TypeError, ValueError) as error:
            raise V023PhysicalError("real environment lacks canonical decision interval") from error
        if not math.isfinite(interval_s) or interval_s <= 0.0:
            raise V023PhysicalError("decision interval is not finite and positive")

        total_bits = 0.0
        total_energy_j = 0.0
        served_user_steps = 0
        trace = hashlib.sha256()
        initial_native: Any | None = None
        initial_world_sha256: str | None = None
        with torch.no_grad() if torch is not None else _nullcontext():
            for step_index in range(self.steps):
                try:
                    native = encode_ee_axis_state(step_environment, observation)
                except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                    raise V023PhysicalError("native Q1 state encoding failed") from error
                if step_index == 0:
                    initial_native = native
                    initial_world_sha256 = _observation_digest(native)
                masks = np.asarray(native.action_masks, dtype=np.bool_)
                q1_values = _surface(
                    self.frozen.q1, native.state_matrix, masks, field="Q1"
                )
                # The V0.20 carrier uses the Q1-only reference action.  It is
                # an input to the frozen Q2 state, never an outcome or target.
                q1_reference = _masked_argmax(q1_values, masks)
                try:
                    anchor = snapshot_ops3_anchor(step_environment, observation)
                    projection = project_ops3_anchor(anchor)
                    q2_surfaces = build_ops3_live_surfaces(
                        anchor, projection, q1_reference
                    )
                    q2_state = encode_ee_axis_v014_q2_states(q2_surfaces)
                    q2_state.verify()
                except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                    raise V023PhysicalError("canonical Q2 state carrier failed") from error
                q2_masks = np.asarray(q2_state.action_masks, dtype=np.bool_)
                if not np.array_equal(q2_masks, masks):
                    raise V023PhysicalError("Q2 carrier mask differs from native mask")
                q2_values = _surface(
                    self.frozen.q2,
                    q2_state.state_matrix,
                    q2_masks,
                    field="Q2",
                )
                actions = _validate_actions(_masked_argmax(q1_values + q2_values, masks), masks)
                _action_trace_update(trace, actions)
                try:
                    environment.step(actions, env_rng)
                    outcome = environment.last_outcome
                    next_observation = outcome.observation
                except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                    raise V023PhysicalError("canonical TrainerEnvironment step failed") from error
                try:
                    rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
                    power = float(outcome.system_power_w)
                except (AttributeError, TypeError, ValueError) as error:
                    raise V023PhysicalError("step outcome lacks physical rate/power receipt") from error
                if rates.shape != (self.users,) or not np.all(np.isfinite(rates)) or np.any(rates < 0.0):
                    raise V023PhysicalError("realised link rates are malformed")
                if not math.isfinite(power) or power <= 0.0:
                    raise V023PhysicalError("realised system power is not finite and positive")
                total_bits += float(
                    interval_s * math.fsum(float(value) for value in rates)
                )
                total_energy_j += float(interval_s * power)
                try:
                    served = int(outcome.resolution.served_count)
                except (AttributeError, TypeError, ValueError) as error:
                    raise V023PhysicalError("step outcome lacks service resolution") from error
                if served < 0 or served > self.users:
                    raise V023PhysicalError("served count is outside user count")
                served_user_steps += served
                if step_index < self.steps - 1:
                    if bool(getattr(outcome, "done", False)):
                        raise V023PhysicalError("environment terminated before ten steps")
                    observation = next_observation
                elif not bool(getattr(outcome, "done", False)):
                    raise V023PhysicalError("environment did not terminate after ten steps")
        if initial_native is None or initial_world_sha256 is None:
            raise V023PhysicalError("episode did not produce an initial observation")
        q1_parameter = _parameter_sha256(self.frozen.q1)
        q2_parameter = _parameter_sha256(self.frozen.q2)
        if q1_parameter != self.frozen.q1_parameter_sha256 or q2_parameter != self.frozen.q2_parameter_sha256:
            raise V023PhysicalError("frozen network parameters changed during inference")
        if not math.isfinite(total_bits) or total_bits < 0.0:
            raise V023PhysicalError("episode total bits are not finite")
        if not math.isfinite(total_energy_j) or total_energy_j <= 0.0:
            raise V023PhysicalError("episode total energy is not finite and positive")
        receipt = V023EpisodeReceipt(
            schema=RECEIPT_SCHEMA,
            status=STATUS,
            split=EVALUATION_SPLIT,
            arm=arm,
            episode_index=world.episode_index,
            world_id=world.world_id,
            world_seed=world.world_seed,
            users=self.users,
            steps=self.steps,
            decision_interval_s=interval_s,
            total_bits=total_bits,
            total_energy_j=total_energy_j,
            ratio_of_sums_ee_bits_per_j=total_bits / total_energy_j,
            served_user_steps=served_user_steps,
            service_opportunities=self.users * self.steps,
            service_fraction=served_user_steps / (self.users * self.steps),
            initial_world_sha256=initial_world_sha256,
            field_component=FIELD_COMPONENT,
            field_root_digest=field.root_digest,
            action_trace_sha256=trace.hexdigest(),
            checkpoint_binding=self.frozen.binding.as_dict(),
            q1_parameter_sha256=q1_parameter,
            q2_parameter_sha256=q2_parameter,
            q3_evaluated=False,
            test_split_opened=False,
            episode_training=False,
            learner_update=False,
            evaluation_contract_sha256=DEVELOPMENT_CONTRACT_SHA256,
        )
        receipt.verify()
        environment_state = getattr(environment, "training_state_dict", None)
        if not callable(environment_state):
            raise V023PhysicalError("TrainerEnvironment lacks deterministic resume state")
        try:
            training_state = environment_state()
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            raise V023PhysicalError("cannot capture TrainerEnvironment resume state") from error
        if not isinstance(training_state, Mapping):
            raise V023PhysicalError("TrainerEnvironment resume state must be a mapping")
        self._resume_by_arm[arm] = {
            "schema": f"{SCHEMA}-resume-state",
            "arm": arm,
            "episode_index": world.episode_index,
            "world_id": world.world_id,
            "world_seed": world.world_seed,
            "field_root_digest": world.field_root_digest,
            "environment_training_state": _jsonable(training_state),
            "rng_states": [_rng_state(rng) for rng in rngs],
            "q1_parameter_sha256": q1_parameter,
            "q2_parameter_sha256": q2_parameter,
            "torch_rng_state": (
                _jsonable(torch.get_rng_state()) if torch is not None else None
            ),
        }
        return receipt


class _nullcontext:
    """Tiny local context manager for imports without torch."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, *_args: object) -> None:
        return None


def _receipt_from_mapping(value: V023EpisodeReceipt | Mapping[str, object]) -> V023EpisodeReceipt:
    if isinstance(value, V023EpisodeReceipt):
        value.verify()
        return value
    if not isinstance(value, Mapping):
        raise V023PhysicalError("receipt must be V023EpisodeReceipt or mapping")
    try:
        receipt = V023EpisodeReceipt(**dict(value))
    except (TypeError, ValueError) as error:
        raise V023PhysicalError("receipt mapping is malformed") from error
    receipt.verify()
    return receipt


def pool_receipts(
    receipts: Sequence[V023EpisodeReceipt | Mapping[str, object]],
    *,
    arm: str | None = None,
) -> dict[str, object]:
    """Pool additive physical quantities before taking one EE ratio."""

    rows = tuple(_receipt_from_mapping(value) for value in receipts)
    if not rows:
        raise V023PhysicalError("cannot pool an empty receipt set")
    selected_arm = arm or rows[0].arm
    if selected_arm not in ARMS or any(row.arm != selected_arm for row in rows):
        raise V023PhysicalError("pooled receipts contain multiple arms")
    keys = {(row.arm, row.episode_index, row.world_id) for row in rows}
    if len(keys) != len(rows):
        raise V023PhysicalError("pooled receipts contain duplicate episode keys")
    binding = rows[0].checkpoint_binding
    if any(row.checkpoint_binding != binding for row in rows):
        raise V023PhysicalError("pooled receipts disagree on checkpoint binding")
    if any(row.field_component != FIELD_COMPONENT for row in rows):
        # Each row still carries the exact root that paired verification can
        # compare.  A caller may intentionally repeat a seed in a standalone
        # pool; uniqueness belongs to V023EpisodePlan, not this reducer.
        raise V023PhysicalError("pooled receipts have an invalid field binding")
    if any(
        row.q1_parameter_sha256 != rows[0].q1_parameter_sha256
        or row.q2_parameter_sha256 != rows[0].q2_parameter_sha256
        or row.evaluation_contract_sha256 != rows[0].evaluation_contract_sha256
        for row in rows
    ):
        raise V023PhysicalError(
            "pooled receipts disagree on frozen network or contract parameters"
        )
    total_bits = math.fsum(row.total_bits for row in rows)
    total_energy = math.fsum(row.total_energy_j for row in rows)
    served = sum(row.served_user_steps for row in rows)
    opportunities = sum(row.service_opportunities for row in rows)
    if not math.isfinite(total_energy) or total_energy <= 0.0:
        raise V023PhysicalError("pooled energy is not finite and positive")
    return {
        "schema": f"{SCHEMA}-pooled",
        "status": STATUS,
        "split": EVALUATION_SPLIT,
        "arm": selected_arm,
        "episodes": len(rows),
        "users": USERS,
        "steps": STEPS,
        "total_bits": total_bits,
        "total_energy_j": total_energy,
        "ratio_of_sums_ee_bits_per_j": total_bits / total_energy,
        "served_user_steps": served,
        "service_opportunities": opportunities,
        "service_fraction": served / opportunities,
        "world_ids": [row.world_id for row in rows],
        "world_seeds": [row.world_seed for row in rows],
        "field_root_digests": [row.field_root_digest for row in rows],
        "checkpoint_binding": dict(binding),
        "q1_parameter_sha256": rows[0].q1_parameter_sha256,
        "q2_parameter_sha256": rows[0].q2_parameter_sha256,
        "evaluation_contract_sha256": rows[0].evaluation_contract_sha256,
        "q3_evaluated": False,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }


def _verify_pair(left: V023EpisodeReceipt, right: V023EpisodeReceipt) -> None:
    if left.arm != "BASELINE" or right.arm != "DROP_C3":
        raise V023PhysicalError("paired rows must be BASELINE then DROP_C3")
    for field in ("episode_index", "world_id", "world_seed", "field_root_digest", "initial_world_sha256"):
        if getattr(left, field) != getattr(right, field):
            raise V023PhysicalError(f"paired worlds disagree on {field}")
    if left.action_trace_sha256 != right.action_trace_sha256:
        raise V023PhysicalError("paired arms selected different Q1+Q2 actions")
    if left.checkpoint_binding != right.checkpoint_binding:
        raise V023PhysicalError("paired arms disagree on checkpoint binding")


def _write_once(path: Path, payload: object) -> None:
    if path.exists() or path.is_symlink():
        raise V023PhysicalError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise V023PhysicalError(f"output parent is not a regular directory: {path.parent}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # A hard link gives write-once publication: a concurrent writer
            # cannot replace an already published receipt/checkpoint.
            os.link(temporary_name, path)
        except FileExistsError as error:
            raise V023PhysicalError(
                f"refusing to overwrite concurrently-created output: {path}"
            ) from error
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def _read_checkpoint(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise V023PhysicalError(f"checkpoint is not a regular file: {path}")
    payload = _read_json(path, field="V0.23 checkpoint")
    claimed = payload.pop("checkpoint_sha256", None)
    if _digest(claimed, field="checkpoint_sha256") != canonical_sha256(payload):
        raise V023PhysicalError("checkpoint canonical hash disagrees with bytes")
    if payload.get("schema") != CHECKPOINT_SCHEMA or payload.get("status") != STATUS:
        raise V023PhysicalError("checkpoint schema/status is not provisional")
    return payload


class V023PhysicalEpisodeRunner:
    """Run a frozen paired grid with checkpoint/resume at 100 episodes."""

    def __init__(
        self,
        *,
        adapter: V023PhysicalEpisodeAdapter,
        plan: V023EpisodePlan,
    ) -> None:
        plan.verify(checkpoint=adapter.frozen.binding)
        self.adapter = adapter
        self.plan = plan

    def _checkpoint_payload(
        self,
        *,
        completed_episode: int,
        receipts: Sequence[V023EpisodeReceipt],
    ) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": CHECKPOINT_SCHEMA,
            "status": STATUS,
            "split": EVALUATION_SPLIT,
            "completed_episode": completed_episode,
            "plan_sha256": self.plan.plan_sha256,
            "evaluation_contract_sha256": self.plan.evaluation_contract_sha256,
            "checkpoint_binding": self.adapter.frozen.binding.as_dict(),
            "arms": list(self.plan.arms),
            "checkpoint_every": CHECKPOINT_EVERY,
            "receipts": [row.as_dict() for row in receipts],
            "resume_states": {
                arm: self.adapter.resume_state_for(arm) for arm in self.plan.arms
            },
            "q1_parameter_sha256": self.adapter.frozen.q1_parameter_sha256,
            "q2_parameter_sha256": self.adapter.frozen.q2_parameter_sha256,
            "q3_evaluated": False,
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
        }
        body["checkpoint_sha256"] = canonical_sha256(body)
        return body

    def _validate_resume_payload(self, payload: Mapping[str, object]) -> tuple[int, list[V023EpisodeReceipt]]:
        if payload.get("split") != EVALUATION_SPLIT:
            raise V023PhysicalError("resume checkpoint split is not evaluation")
        if payload.get("evaluation_contract_sha256") != self.plan.evaluation_contract_sha256:
            raise V023PhysicalError("resume checkpoint contract disagrees")
        if payload.get("plan_sha256") != self.plan.plan_sha256:
            raise V023PhysicalError("checkpoint plan hash disagrees with current plan")
        if payload.get("checkpoint_binding") != self.adapter.frozen.binding.as_dict():
            raise V023PhysicalError("checkpoint binding disagrees with current V0.20 merge")
        completed = _positive_int(payload.get("completed_episode"), field="completed_episode")
        if completed % CHECKPOINT_EVERY:
            raise V023PhysicalError("resume checkpoint is not on the 100-episode cadence")
        if completed > len(self.plan.worlds):
            raise V023PhysicalError("resume checkpoint exceeds plan world grid")
        if payload.get("arms") != list(self.plan.arms) or payload.get("checkpoint_every") != CHECKPOINT_EVERY:
            raise V023PhysicalError("resume checkpoint arm/cadence metadata drifted")
        if any(bool(payload.get(field, False)) for field in ("q3_evaluated", "test_split_opened", "episode_training", "learner_update")):
            raise V023PhysicalError("resume checkpoint crossed forbidden boundary")
        raw_rows = payload.get("receipts")
        if not isinstance(raw_rows, list) or len(raw_rows) != completed * len(self.plan.arms):
            raise V023PhysicalError("resume checkpoint receipt count is incomplete")
        rows = [_receipt_from_mapping(row) for row in raw_rows]
        for index in range(completed):
            pair = rows[
                index * len(self.plan.arms) : (index + 1) * len(self.plan.arms)
            ]
            if len(pair) != len(self.plan.arms):
                raise V023PhysicalError("resume checkpoint episode arm coverage is incomplete")
            if self.plan.arms == ARMS:
                _verify_pair(pair[0], pair[1])
            elif pair[0].arm != DROP_C3_ONLY_ARMS[0]:
                raise V023PhysicalError("resume checkpoint contains a non-DROP_C3 arm")
            world = self.plan.worlds[index]
            if (
                pair[0].episode_index != world.episode_index
                or pair[0].world_id != world.world_id
                or pair[0].world_seed != world.world_seed
                or pair[0].field_root_digest != world.field_root_digest
            ):
                raise V023PhysicalError("resume checkpoint world grid disagrees")
        states = payload.get("resume_states")
        if not isinstance(states, Mapping):
            raise V023PhysicalError("resume checkpoint lacks full resume states")
        if any(not isinstance(states.get(arm), Mapping) for arm in self.plan.arms):
            raise V023PhysicalError("resume checkpoint lacks one state per arm")
        self.adapter.restore_resume_states(states)
        if payload.get("q1_parameter_sha256") != self.adapter.frozen.q1_parameter_sha256 or payload.get("q2_parameter_sha256") != self.adapter.frozen.q2_parameter_sha256:
            raise V023PhysicalError("resume checkpoint network digest disagrees")
        return completed, rows

    def run(
        self,
        *,
        output_dir: str | Path,
        resume_checkpoint: str | Path | None = None,
        stop_after: int | None = None,
    ) -> dict[str, object]:
        output = Path(output_dir)
        if output.exists():
            if output.is_symlink() or not output.is_dir():
                raise V023PhysicalError(f"output is not a regular directory: {output}")
            if resume_checkpoint is None and any(output.iterdir()):
                raise V023PhysicalError(f"refusing to overwrite non-empty output: {output}")
            if resume_checkpoint is not None and (output / "result.json").exists():
                raise V023PhysicalError(f"refusing to resume a completed output: {output}")
        else:
            output.mkdir(parents=True, exist_ok=False)
        checkpoint_dir = output / "checkpoints"
        receipts: list[V023EpisodeReceipt] = []
        start = 0
        if resume_checkpoint is not None:
            checkpoint = Path(resume_checkpoint)
            payload = _read_checkpoint(checkpoint)
            start, receipts = self._validate_resume_payload(payload)
        target = len(self.plan.worlds) if stop_after is None else _positive_int(stop_after, field="stop_after")
        if target > len(self.plan.worlds) or target < start:
            raise V023PhysicalError("stop_after is outside the plan/resume range")
        for index in range(start, target):
            world = self.plan.worlds[index]
            pair: list[V023EpisodeReceipt] = []
            for arm in self.plan.arms:
                row = self.adapter.run_episode(
                    arm=arm,
                    world=world,
                    resume_state=self.adapter.resume_state_for(arm),
                )
                pair.append(row)
                receipts.append(row)
            if self.plan.arms == ARMS:
                _verify_pair(pair[0], pair[1])
            episode_number = index + 1
            if episode_number % CHECKPOINT_EVERY == 0:
                checkpoint_payload = self._checkpoint_payload(
                    completed_episode=episode_number,
                    receipts=receipts,
                )
                _write_once(
                    checkpoint_dir / f"checkpoint-{episode_number:06d}.json",
                    checkpoint_payload,
                )
        completed = target
        result = {
            "schema": RESULT_SCHEMA,
            "status": STATUS,
            "split": EVALUATION_SPLIT,
            "completed_episode": completed,
            "planned_episodes": len(self.plan.worlds),
            "plan_sha256": self.plan.plan_sha256,
            "evaluation_contract_sha256": self.plan.evaluation_contract_sha256,
            "checkpoint_binding": self.adapter.frozen.binding.as_dict(),
            "arms": list(self.plan.arms),
            "pooled_by_arm": {
                arm: pool_receipts(
                    [row for row in receipts if row.arm == arm], arm=arm
                )
                for arm in self.plan.arms
            }
            if receipts
            else {},
            "receipt_count": len(receipts),
            "checkpoints": sorted(
                str(path.relative_to(output)) for path in checkpoint_dir.glob("*.json")
            )
            if checkpoint_dir.exists()
            else [],
            "q3_evaluated": False,
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
            "baseline_artifact_emitted": self.plan.arms == ARMS,
            "between_arm_comparison_performed": self.plan.arms == ARMS,
            "claim_ceiling": "EVALUATION_PROVISIONAL_PRE_GATE_NO_C3_NO_TEST_NO_EFFICACY",
        }
        if completed == len(self.plan.worlds):
            _write_once(output / "result.json", result)
        return result


def make_world_binding(
    *, episode_index: int, world_seed: int, world_id: str | None = None
) -> V023WorldBinding:
    """Construct a paired world binding from the frozen keyed-field namespace."""

    seed = _positive_int(world_seed, field="world_seed")
    return V023WorldBinding(
        episode_index=_positive_int(episode_index, field="episode_index"),
        world_id=world_id or f"world-{seed}",
        world_seed=seed,
        field_root_digest=KeyedFadingField.from_components(FIELD_COMPONENT, seed).root_digest,
    )


__all__ = [
    "ARMS",
    "CHECKPOINT_EVERY",
    "CHECKPOINT_SCHEMA",
    "DEVELOPMENT_CONTRACT_PATH",
    "DEVELOPMENT_CONTRACT_SCHEMA",
    "DEVELOPMENT_CONTRACT_SHA256",
    "DEVELOPMENT_PREREG_PATH",
    "DEVELOPMENT_PREREG_RECORD_DIGEST",
    "DEVELOPMENT_PREREG_SHA256",
    "DROP_C3_ONLY_ARMS",
    "FIELD_COMPONENT",
    "FrozenV020Q12",
    "LINEAGE",
    "RECEIPT_SCHEMA",
    "RESULT_SCHEMA",
    "SCHEMA",
    "STATUS",
    "STEPS",
    "EVALUATION_SPLIT",
    "USERS",
    "V020_AUTHORITY_FILE_SHA256",
    "V020_AUTHORITY_SHA256",
    "V020_CHECKPOINT_PATH",
    "V020_CHECKPOINT_SHA256",
    "V020_REPRICING_CONTRACT_SHA256",
    "V020_SOURCE_CONTRACT_SHA256",
    "V020CheckpointBinding",
    "V023EpisodePlan",
    "V023EpisodeReceipt",
    "V023PhysicalEpisodeAdapter",
    "V023PhysicalEpisodeRunner",
    "V023PhysicalError",
    "V023WorldBinding",
    "canonical_sha256",
    "file_sha256",
    "load_v020_q12",
    "make_world_binding",
    "pool_receipts",
]
