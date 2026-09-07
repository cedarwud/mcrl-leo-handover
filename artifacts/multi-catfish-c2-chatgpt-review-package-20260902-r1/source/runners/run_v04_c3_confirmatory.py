#!/usr/bin/env python3
"""Frozen, no-training V0.4 C3 confirmatory evaluator.

This consumer is intentionally separate from the bounded 500-update screen.
It has three explicit phases:

``prepare``
    authenticate the exact sealed V0.4 source/gate and prior screen, then seal
    the evaluator code manifest.  No dataset bytes, TLE bytes, trainer, or
    simulator episode are opened.

``run``
    re-authenticate the prepared receipts, prove the candidate tensors and
    common keyed physical world, and then run the pre-registered frozen
    FULL/DROP_C3 matched block.  There is no gradient, replay, checkpoint, or
    TEST path.

``verify``
    verify the write-once receipts, rows, pair identities, pooled endpoint,
    decision rule, and deterministic bootstrap without opening a trainer,
    source dataset, TLE archive, or simulator episode.

The module is import-safe.  Importing it never authenticates an artifact or
starts an episode.  The production defaults are the exact V0.4 r2/r1
artifacts named by the frozen confirmatory preregistration.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping, Sequence
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Callable, NamedTuple

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (HERE, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v04_c3_500_update_screen as screen  # noqa: E402
import run_v04_c3_learnability_gate as gate  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_v04_c3_state import (  # noqa: E402
    encode_ee_axis_v04_c3_state,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _default_code_paths,
    _evaluation_rngs,
)


# Frozen confirmatory protocol ---------------------------------------------

CONFIRMATORY_SCHEMA = "multi-catfish-mcrl-v04-c3-confirmatory-v1"
PREPARE_SCHEMA = "multi-catfish-mcrl-v04-c3-confirmatory-prepare-v1"
PREPARE_SEAL_SCHEMA = "multi-catfish-mcrl-v04-c3-confirmatory-prepare-seal-v1"
CODE_MANIFEST_SCHEMA = "multi-catfish-mcrl-v04-c3-confirmatory-code-manifest-v1"
RESULT_SCHEMA = "multi-catfish-mcrl-v04-c3-confirmatory-result-v1"
RESULT_SEAL_SCHEMA = "multi-catfish-mcrl-v04-c3-confirmatory-result-seal-v1"

STATUS_PREPARED = "PREPARED_NO_EPISODE"
STATUS_COMPLETE = "CONFIRMATORY_COMPLETE"
STATUS_CONFIRM = "CONFIRM_C3"
STATUS_NOT_CONFIRMED = "C3_PROMISING_NOT_CONFIRMED"
STATUS_INVALID = "INVALID_CONFIRMATORY_RUN"

EVALUATION_SEEDS = tuple(range(2026092501, 2026092531))
INITIALIZATION_SEEDS = tuple(gate.INITIALIZATION_SEEDS)
SELECTED_Q3_RUNG = 100
USERS = 100
STEPS_PER_EPISODE = 10
EVALUATION_SPLIT = "TRAIN"
TEST_SPLIT_OPENED = False
HELD_OUT_EE_EVALUATED = True
EPISODE_TRAINING = False
ARMS = ("FULL", "DROP_C3")
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 2026092599
FIELD_COMPONENT = "V04_C3_CONFIRMATORY_V1"
FIELD_KEY_AXES = (FIELD_COMPONENT, "gate_authority_sha256", "evaluation_seed")

DEFAULT_GATE_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-c3-learnability-20260901-r2"
)
DEFAULT_SOURCE_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-c3-source-20260901-r2"
)
DEFAULT_PRIOR_SCREEN_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-c3-500-update-screen-20260901-r1"
)
DEFAULT_V03_ROOT = (
    REPO / "artifacts" / "multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"
)
DEFAULT_PREREG = gate.DEFAULT_PREREG
DEFAULT_TLE_ROOT = Path("~/demo/tle_data/starlink/tle").expanduser()
DEFAULT_OUTPUT_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-c3-confirmatory-20260901-r1"
)

EXPECTED_GATE_BASENAME = "multi-catfish-v04-c3-learnability-20260901-r2"
EXPECTED_SOURCE_BASENAME = "multi-catfish-v04-c3-source-20260901-r2"
EXPECTED_PRIOR_SCREEN_BASENAME = (
    "multi-catfish-v04-c3-500-update-screen-20260901-r1"
)
PRIOR_SCREEN_RESULT_SEAL_SCHEMA = (
    "multi-catfish-mcrl-v04-c3-500-update-screen-result-seal-v1"
)
PRIOR_SCREEN_RESULT_SHA256 = (
    "ab232f72e562e5a9aa4b68ec8074c5556691ffb1272ae92ec5efd651e76a2177"
)


class V04C3ConfirmatoryError(RuntimeError):
    """A frozen confirmatory authority, pairing, physics, or receipt failed."""


class AuthorityContext(NamedTuple):
    """The minimum authenticated lineage carried into the run receipt."""

    gate_authority_sha256: str
    gate_result_file_sha256: str
    gate_result_seal_file_sha256: str
    source_manifest_sha256: str
    schedule_sha256: str
    train_surface_sha256: str
    selected_q3_rung: int
    prior_screen_result_file_sha256: str
    prior_screen_result_seal_file_sha256: str
    prior_primary_receipt_file_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate_authority_sha256": self.gate_authority_sha256,
            "gate_result_file_sha256": self.gate_result_file_sha256,
            "gate_result_seal_file_sha256": self.gate_result_seal_file_sha256,
            "source_manifest_sha256": self.source_manifest_sha256,
            "schedule_sha256": self.schedule_sha256,
            "train_surface_sha256": self.train_surface_sha256,
            "selected_q3_rung": self.selected_q3_rung,
            "prior_screen_result_file_sha256": self.prior_screen_result_file_sha256,
            "prior_screen_result_seal_file_sha256": self.prior_screen_result_seal_file_sha256,
            "prior_primary_receipt_file_sha256": self.prior_primary_receipt_file_sha256,
        }


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
        raise V04C3ConfirmatoryError(
            "payload is not finite canonical JSON"
        ) from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)[:-1]).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V04C3ConfirmatoryError(f"{field} must be lowercase SHA-256")
    return value


def _file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V04C3ConfirmatoryError(
            f"expected a regular non-symlink file: {source}"
        )
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_canonical_json(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V04C3ConfirmatoryError(f"sealed JSON is missing: {source}")
    raw = source.read_bytes()
    try:
        payload = json.loads(
            raw.decode("ascii"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise V04C3ConfirmatoryError(f"sealed JSON is invalid: {source}") from error
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        raise V04C3ConfirmatoryError(f"sealed JSON is not canonical: {source}")
    return payload


def _write_once_json(path: Path, payload: object) -> str:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise V04C3ConfirmatoryError(
            f"refusing to overwrite confirmatory receipt: {destination}"
        )
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
            raise V04C3ConfirmatoryError(
                f"refusing to overwrite confirmatory receipt: {destination}"
            ) from error
    finally:
        temporary.unlink(missing_ok=True)
    return _file_sha256(destination)


def _regular_dir(path: Path, *, field: str) -> Path:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_dir():
        raise V04C3ConfirmatoryError(f"{field} must be a regular directory: {candidate}")
    return candidate


def _require_exact_basename(path: Path, expected: str, *, field: str) -> Path:
    candidate = _regular_dir(path, field=field)
    if candidate.name != expected:
        raise V04C3ConfirmatoryError(
            f"{field} must be the sealed {expected} artifact, got {candidate.name}"
        )
    return candidate


def _require_false(payload: Mapping[str, Any], field: str, *, label: str) -> None:
    if payload.get(field) is not False:
        raise V04C3ConfirmatoryError(
            f"{label}.{field} must be exactly false; TEST is forbidden"
        )


def _validate_positive_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 1:
        raise V04C3ConfirmatoryError(f"{field} must be an integer >= 1")
    return value


def _validate_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise V04C3ConfirmatoryError(f"{field} must be an integer >= 0")
    return value


def _relative(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(Path(path).resolve())


def _manifest_paths() -> tuple[Path, ...]:
    """Return every code file that can affect this consumer's computation."""

    paths: list[Path] = [
        Path(__file__),
        Path(screen.__file__).resolve(),
        Path(gate.__file__).resolve(),
        HERE / "run_v04_c3_source.py",
    ]
    paths.extend(Path(path) for path in _default_code_paths())
    unique: dict[str, Path] = {}
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise V04C3ConfirmatoryError(
                f"evaluator code manifest path is missing or non-regular: {path}"
            )
        unique[str(path.resolve())] = path.resolve()
    return tuple(sorted(unique.values(), key=lambda item: _relative(item)))


def build_evaluator_code_manifest() -> dict[str, Any]:
    files = {_relative(path): _file_sha256(path) for path in _manifest_paths()}
    body = {
        "schema": CODE_MANIFEST_SCHEMA,
        "files": files,
    }
    return {**body, "manifest_sha256": canonical_sha256(body)}


def _validate_code_manifest(payload: Mapping[str, Any], *, current: bool) -> str:
    if payload.get("schema") != CODE_MANIFEST_SCHEMA:
        raise V04C3ConfirmatoryError("evaluator code manifest schema drifted")
    files = payload.get("files")
    if not isinstance(files, Mapping) or not files:
        raise V04C3ConfirmatoryError("evaluator code manifest files are missing")
    body = {"schema": payload["schema"], "files": dict(files)}
    observed = _digest(payload.get("manifest_sha256"), field="manifest_sha256")
    if canonical_sha256(body) != observed:
        raise V04C3ConfirmatoryError("evaluator code manifest digest is invalid")
    for name, digest in files.items():
        if not isinstance(name, str):
            raise V04C3ConfirmatoryError("evaluator code manifest path is malformed")
        _digest(digest, field=f"manifest.files[{name}]")
        if current:
            path = Path(name)
            if not path.is_absolute():
                path = REPO / path
            if _file_sha256(path) != digest:
                raise V04C3ConfirmatoryError(
                    f"evaluator code changed after manifest seal: {name}"
                )
    return observed


def _assert_r2_authority_paths(
    gate_dir: Path,
    source_dir: Path,
    prior_screen_dir: Path,
) -> tuple[Path, Path, Path]:
    return (
        _require_exact_basename(
            gate_dir, EXPECTED_GATE_BASENAME, field="gate_dir"
        ),
        _require_exact_basename(
            source_dir, EXPECTED_SOURCE_BASENAME, field="source_dir"
        ),
        _require_exact_basename(
            prior_screen_dir,
            EXPECTED_PRIOR_SCREEN_BASENAME,
            field="prior_screen_dir",
        ),
    )


def authenticate_prior_screen(
    prior_screen_dir: Path,
    *,
    gate_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate the exact sealed prior result, seal, and primary receipt."""

    root = _require_exact_basename(
        prior_screen_dir,
        EXPECTED_PRIOR_SCREEN_BASENAME,
        field="prior_screen_dir",
    )
    result_path = root / "result.json"
    seal_path = root / "result-seal.json"
    primary_path = root / "primary-evaluation.json"
    result = _read_canonical_json(result_path)
    seal = _read_canonical_json(seal_path)
    primary = _read_canonical_json(primary_path)
    result_sha = _file_sha256(result_path)
    seal_sha = _file_sha256(seal_path)
    primary_sha = _file_sha256(primary_path)
    if result_sha != PRIOR_SCREEN_RESULT_SHA256:
        raise V04C3ConfirmatoryError(
            "prior screen result bytes do not match the preregistered SHA-256"
        )
    if (
        result.get("schema") != screen.SCREEN_RESULT_SCHEMA
        or result.get("status") != "SCREEN_COMPLETE"
        or result.get("gate_status") != screen.REQUIRED_GATE_STATUS
        or result.get("gate_authority_sha256") != gate_receipt["authority_sha256"]
        or result.get("gate_result_file_sha256") != gate_receipt["result_file_sha256"]
        or result.get("source_manifest_sha256") != gate_receipt["source_manifest_sha256"]
        or result.get("schedule_sha256") != gate_receipt["schedule_sha256"]
        or result.get("gate_selected_q3_rung") != SELECTED_Q3_RUNG
        or result.get("evaluation_split") != EVALUATION_SPLIT
        or result.get("primary_screen_updates_completed") != 0
        or result.get("primary_receipt_file_sha256") != primary_sha
    ):
        raise V04C3ConfirmatoryError("prior screen result is not the sealed primary screen")
    _require_false(result, "test_split_opened", label="prior screen result")
    if result.get("episode_training") is not False:
        raise V04C3ConfirmatoryError("prior screen episode_training is not false")
    if (
        seal.get("schema") != PRIOR_SCREEN_RESULT_SEAL_SCHEMA
        or seal.get("result_file_sha256") != result_sha
        or seal.get("gate_authority_sha256") != gate_receipt["authority_sha256"]
        or seal.get("primary_receipt_file_sha256") != primary_sha
        or seal.get("test_split_opened") is not False
        or seal.get("held_out_ee_evaluated") is not True
    ):
        raise V04C3ConfirmatoryError("prior screen result seal is invalid")
    if (
        primary.get("schema") != screen.PRIMARY_RECEIPT_SCHEMA
        or primary.get("status") != "PRIMARY_EVALUATION_COMPLETE"
        or primary.get("gate_authority_sha256") != gate_receipt["authority_sha256"]
        or primary.get("gate_result_file_sha256") != gate_receipt["result_file_sha256"]
        or primary.get("gate_selected_q3_rung") != SELECTED_Q3_RUNG
        or primary.get("screen_updates_completed") != 0
        or primary.get("total_q3_update_count") != SELECTED_Q3_RUNG
        or primary.get("evaluation_split") != EVALUATION_SPLIT
        or primary.get("held_out_ee_evaluated") is not True
    ):
        raise V04C3ConfirmatoryError("prior primary receipt is invalid")
    _require_false(primary, "test_split_opened", label="prior primary receipt")
    return {
        "result_file_sha256": result_sha,
        "result_seal_file_sha256": seal_sha,
        "primary_receipt_file_sha256": primary_sha,
        "status": result["status"],
        "gate_selected_q3_rung": result["gate_selected_q3_rung"],
    }


def authenticate_current_authority(
    *,
    gate_dir: Path,
    source_dir: Path,
    prior_screen_dir: Path,
    prereg_path: Path,
) -> AuthorityContext:
    """Authenticate current r2 source/gate plus the frozen prior screen."""

    gate_root, source_root, prior_root = _assert_r2_authority_paths(
        gate_dir, source_dir, prior_screen_dir
    )
    gate_receipt = screen.authenticate_gate(
        gate_root,
        source_dir=source_root,
        prereg_path=prereg_path,
    )
    if gate_receipt.get("selected_q3_rung") != SELECTED_Q3_RUNG:
        raise V04C3ConfirmatoryError("authenticated gate did not select rung 100")
    source_authority = gate_receipt.get("source_authority")
    if source_authority is None or Path(source_authority.source_dir).name != EXPECTED_SOURCE_BASENAME:
        raise V04C3ConfirmatoryError("authenticated source authority is not the exact r2 source")
    prior = authenticate_prior_screen(prior_root, gate_receipt=gate_receipt)
    return AuthorityContext(
        gate_authority_sha256=str(gate_receipt["authority_sha256"]),
        gate_result_file_sha256=str(gate_receipt["result_file_sha256"]),
        gate_result_seal_file_sha256=str(gate_receipt["authority_seal_file_sha256"]),
        source_manifest_sha256=str(gate_receipt["source_manifest_sha256"]),
        schedule_sha256=str(gate_receipt["schedule_sha256"]),
        train_surface_sha256=str(gate_receipt["train_surface_sha256"]),
        selected_q3_rung=SELECTED_Q3_RUNG,
        prior_screen_result_file_sha256=prior["result_file_sha256"],
        prior_screen_result_seal_file_sha256=prior["result_seal_file_sha256"],
        prior_primary_receipt_file_sha256=prior["primary_receipt_file_sha256"],
    )


def _field_for_seed(*, gate_authority_sha256: str, evaluation_seed: int) -> KeyedFadingField:
    """Build the one field shared by both arms and all frozen initializations."""

    _digest(gate_authority_sha256, field="gate_authority_sha256")
    seed = _validate_positive_int(evaluation_seed, field="evaluation_seed")
    return KeyedFadingField.from_components(
        FIELD_COMPONENT,
        gate_authority_sha256,
        seed,
    )


def common_field_receipt(*, gate_authority_sha256: str, evaluation_seed: int) -> dict[str, Any]:
    field = _field_for_seed(
        gate_authority_sha256=gate_authority_sha256,
        evaluation_seed=evaluation_seed,
    )
    return {
        "components": [FIELD_COMPONENT, gate_authority_sha256, int(evaluation_seed)],
        "excluded_components": ["initialization_seed", "policy_label"],
        "receipt": field.receipt(),
        "root_digest": field.root_digest,
    }


def _array_sha256(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for value in arrays:
        array = np.ascontiguousarray(np.asarray(value))
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(repr(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _action_trace_sha256(*, policy_label: str, evaluation_seed: int, actions: Sequence[Sequence[int]]) -> str:
    return canonical_sha256(
        {
            "schema": "multi-catfish-mcrl-v04-action-trace-v1",
            "policy_label": policy_label,
            "evaluation_seed": int(evaluation_seed),
            "actions": actions,
        }
    )


def _make_environment(archive: Any) -> Any:
    # Keep the only environment construction seam in the existing, audited
    # screen consumer.  It is called only after all receipt and code guards.
    return screen._make_environment(
        archive,
        users=USERS,
    )


def _frozen_archive(record: Any, source_root: Path, target_root: Path) -> Any:
    return screen._frozen_archive(record, source_root, target_root)


def _tensor_state(network: Any) -> dict[str, Any]:
    return {
        str(name): value.detach().cpu().clone()
        for name, value in network.state_dict().items()
    }


def _deep_state(value: Any) -> Any:
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, Mapping):
        return {key: _deep_state(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_state(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_deep_state(item) for item in value)
    return copy.deepcopy(value)


def _state_equal(left: Any, right: Any) -> bool:
    if isinstance(left, torch.Tensor) or isinstance(right, torch.Tensor):
        return (
            isinstance(left, torch.Tensor)
            and isinstance(right, torch.Tensor)
            and torch.equal(left.detach().cpu(), right.detach().cpu())
        )
    if isinstance(left, Mapping) or isinstance(right, Mapping):
        return (
            isinstance(left, Mapping)
            and isinstance(right, Mapping)
            and set(left) == set(right)
            and all(_state_equal(left[key], right[key]) for key in left)
        )
    if isinstance(left, (list, tuple)) or isinstance(right, (list, tuple)):
        return (
            isinstance(left, type(right))
            and len(left) == len(right)
            and all(_state_equal(a, b) for a, b in zip(left, right, strict=True))
        )
    return left == right


def _snapshot_trainer(trainer: Any) -> dict[str, Any]:
    q_nets = getattr(trainer, "q_nets", None)
    if q_nets is None or len(q_nets) != 3:
        raise V04C3ConfirmatoryError("confirmatory trainer must contain exactly three Q networks")
    optimizer = getattr(trainer, "q3_optimizer", None)
    if optimizer is None:
        raise V04C3ConfirmatoryError("confirmatory trainer has no Q3 optimizer receipt")
    return {
        "q_networks": [_tensor_state(network) for network in q_nets],
        "q3_optimizer": _deep_state(optimizer.state_dict()),
        "q3_update_count": getattr(trainer, "q3_update_count", None),
        "training_flags": [bool(network.training) for network in q_nets],
        "gradients": [
            {
                str(index): None if parameter.grad is None else parameter.grad.detach().cpu().clone()
                for index, parameter in enumerate(network.parameters())
            }
            for network in q_nets
        ],
    }


def _assert_trainer_unchanged(trainer: Any, before: Mapping[str, Any]) -> None:
    after = _snapshot_trainer(trainer)
    for field in (
        "q_networks",
        "q3_optimizer",
        "q3_update_count",
        "training_flags",
        "gradients",
    ):
        if not _state_equal(after[field], before[field]):
            raise V04C3ConfirmatoryError(
                f"frozen trainer changed during confirmatory evaluation: {field}"
            )


def _prepare_trainer_for_eval(trainer: Any) -> None:
    if not isinstance(trainer, screen.EEAxisV04HybridTrainer):
        raise V04C3ConfirmatoryError("confirmatory evaluation requires V0.4 hybrid trainer")
    if (
        trainer.selected_q3_rung != SELECTED_Q3_RUNG
        or trainer.q3_update_count != SELECTED_Q3_RUNG
        or len(trainer.q_nets) != 3
    ):
        raise V04C3ConfirmatoryError(
            "only the sealed selected rung-100 hybrid is admissible"
        )
    if any(parameter.requires_grad for network in trainer.q_nets[:2] for parameter in network.parameters()):
        raise V04C3ConfirmatoryError("Q1/Q2 must remain frozen in confirmatory evaluation")
    for network in trainer.q_nets:
        network.eval()


def _validate_physics(outcome: Any, *, interval_s: float) -> tuple[np.ndarray, float]:
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
        or not math.isfinite(interval_s)
        or interval_s <= 0.0
    ):
        raise V04C3ConfirmatoryError("confirmatory episode produced malformed physical EE inputs")
    return rates, power


def evaluate_episode(
    trainer: Any,
    archive: Any,
    *,
    gate_authority_sha256: str,
    initialization_seed: int,
    evaluation_seed: int,
    policy_label: str,
    field: KeyedFadingField | None = None,
) -> dict[str, Any]:
    """Evaluate one frozen arm; never update the trainer or replay."""

    if policy_label not in ARMS:
        raise V04C3ConfirmatoryError(f"unsupported confirmatory policy: {policy_label}")
    init = _validate_positive_int(initialization_seed, field="initialization_seed")
    seed = _validate_positive_int(evaluation_seed, field="evaluation_seed")
    _prepare_trainer_for_eval(trainer)
    expected_field = _field_for_seed(
        gate_authority_sha256=gate_authority_sha256,
        evaluation_seed=seed,
    )
    if field is not None and field.root_digest != expected_field.root_digest:
        raise V04C3ConfirmatoryError("episode field is not the preregistered common keyed field")
    field = expected_field
    before = _snapshot_trainer(trainer)
    environment = _make_environment(archive)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(seed)
    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    interval_s = float(environment.environment.driver.config.ephemeris.time_step_s)
    if not math.isfinite(interval_s) or interval_s <= 0.0:
        raise V04C3ConfirmatoryError("TRAIN interval is not finite and positive")
    legacy = encode_ee_axis_state(environment.environment, observation)
    c3_state = encode_ee_axis_v04_c3_state(
        environment.environment,
        observation,
        interval_s=interval_s,
        kappa_bits=float(trainer.v04_config.kappa_bits),
    )
    if not np.array_equal(legacy.action_masks, c3_state.action_masks):
        raise V04C3ConfirmatoryError("V0.3/V0.4 initial deployment masks differ")
    initial_state_sha = _array_sha256(
        legacy.state_matrix,
        c3_state.state_matrix,
    )
    initial_mask_sha = _array_sha256(c3_state.action_masks)
    start_epoch = environment.epoch.isoformat()

    total_bits = 0.0
    total_energy = 0.0
    served_user_steps = 0
    steps = 0
    action_trace: list[list[int]] = []
    with torch.no_grad():
        while True:
            legacy = encode_ee_axis_state(environment.environment, observation)
            c3_state = encode_ee_axis_v04_c3_state(
                environment.environment,
                observation,
                interval_s=interval_s,
                kappa_bits=float(trainer.v04_config.kappa_bits),
            )
            if not np.array_equal(legacy.action_masks, c3_state.action_masks):
                raise V04C3ConfirmatoryError(
                    "V0.3/V0.4 deployment masks differ during matched episode"
                )
            actions = trainer.select_greedy_actions(
                legacy.state_matrix,
                c3_state.state_matrix,
                c3_state.action_masks,
                drop_c3=policy_label == "DROP_C3",
            )
            action_trace.append([int(value) for value in actions.tolist()])
            result = environment.step(actions, env_rng)
            outcome = environment.last_outcome
            rates, power = _validate_physics(outcome, interval_s=interval_s)
            total_bits += float(math.fsum(float(value) for value in rates)) * interval_s
            total_energy += power * interval_s
            served_user_steps += int(outcome.resolution.served_count)
            steps += 1
            if result.done:
                break
            observation = outcome.observation
    _assert_trainer_unchanged(trainer, before)
    if steps != STEPS_PER_EPISODE:
        raise V04C3ConfirmatoryError(
            f"TRAIN episode length drifted: expected {STEPS_PER_EPISODE}, got {steps}"
        )
    decision_count = steps * USERS
    if total_energy <= 0.0:
        raise V04C3ConfirmatoryError("confirmatory episode must consume positive total energy")
    ee = total_bits / total_energy
    served_fraction = served_user_steps / decision_count
    return {
        "schema": "multi-catfish-mcrl-v04-confirmatory-episode-v1",
        "policy_label": policy_label,
        "evaluation_split": EVALUATION_SPLIT,
        "initialization_seed": init,
        "evaluation_seed": seed,
        "selected_q3_rung": SELECTED_Q3_RUNG,
        "total_q3_update_count": SELECTED_Q3_RUNG,
        "steps": steps,
        "users": USERS,
        "decision_count": decision_count,
        "start_epoch": start_epoch,
        "initial_state_sha256": initial_state_sha,
        "initial_mask_sha256": initial_mask_sha,
        "fading_field_sha256": field.root_digest,
        "fading_field_components": [FIELD_COMPONENT, gate_authority_sha256, seed],
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
        "held_out_ee_evaluated": HELD_OUT_EE_EVALUATED,
        "episode_training": EPISODE_TRAINING,
    }


def _validate_row(row: Mapping[str, Any], *, policy: str | None = None) -> None:
    if row.get("schema") != "multi-catfish-mcrl-v04-confirmatory-episode-v1":
        raise V04C3ConfirmatoryError("confirmatory episode row schema drifted")
    if policy is not None and row.get("policy_label") != policy:
        raise V04C3ConfirmatoryError("confirmatory episode policy label drifted")
    if row.get("evaluation_split") != EVALUATION_SPLIT:
        raise V04C3ConfirmatoryError("confirmatory episode is not TRAIN-only")
    if row.get("selected_q3_rung") != SELECTED_Q3_RUNG or row.get("total_q3_update_count") != SELECTED_Q3_RUNG:
        raise V04C3ConfirmatoryError("confirmatory row is not frozen rung 100")
    if row.get("steps") != STEPS_PER_EPISODE or row.get("users") != USERS:
        raise V04C3ConfirmatoryError("confirmatory row dimensions drifted")
    if row.get("test_split_opened") is not False or row.get("episode_training") is not False:
        raise V04C3ConfirmatoryError("confirmatory row opened TEST or trained in episode")
    if row.get("held_out_ee_evaluated") is not True:
        raise V04C3ConfirmatoryError("confirmatory row must carry the declared TRAIN EE endpoint")
    _validate_positive_int(row.get("initialization_seed"), field="initialization_seed")
    _validate_positive_int(row.get("evaluation_seed"), field="evaluation_seed")
    _digest(row.get("fading_field_sha256"), field="fading_field_sha256")
    _digest(row.get("initial_state_sha256"), field="initial_state_sha256")
    _digest(row.get("initial_mask_sha256"), field="initial_mask_sha256")
    _digest(row.get("action_trace_sha256"), field="action_trace_sha256")
    _validate_nonnegative_int(row.get("decision_count"), field="decision_count")
    served = _validate_nonnegative_int(row.get("served_user_steps"), field="served_user_steps")
    if row["decision_count"] != USERS * STEPS_PER_EPISODE or served > row["decision_count"]:
        raise V04C3ConfirmatoryError("confirmatory service counts are malformed")
    for field in ("total_bits", "total_energy_j", "ratio_of_sums_ee_bits_per_j"):
        value = row.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) < 0.0:
            raise V04C3ConfirmatoryError(f"confirmatory row {field} is malformed")
    if float(row["total_energy_j"]) <= 0.0:
        raise V04C3ConfirmatoryError("confirmatory row must have positive total energy")


def aggregate_policy_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise V04C3ConfirmatoryError("cannot aggregate empty confirmatory rows")
    for row in rows:
        _validate_row(row)
    bits = float(math.fsum(float(row["total_bits"]) for row in rows))
    energy = float(math.fsum(float(row["total_energy_j"]) for row in rows))
    decisions = sum(int(row["decision_count"]) for row in rows)
    served = sum(int(row["served_user_steps"]) for row in rows)
    if energy <= 0.0:
        raise V04C3ConfirmatoryError("aggregated confirmatory energy must be positive")
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


def _pair_key(row: Mapping[str, Any]) -> tuple[int, int]:
    return (
        _validate_positive_int(row.get("initialization_seed"), field="initialization_seed"),
        _validate_positive_int(row.get("evaluation_seed"), field="evaluation_seed"),
    )


def _pair_rows(
    full_rows: Sequence[Mapping[str, Any]],
    drop_rows: Sequence[Mapping[str, Any]],
    *,
    gate_authority_sha256: str | None = None,
) -> None:
    full = {_pair_key(row): row for row in full_rows}
    drop = {_pair_key(row): row for row in drop_rows}
    if len(full) != len(full_rows) or len(drop) != len(drop_rows):
        raise V04C3ConfirmatoryError("duplicate FULL/DROP_C3 pair row")
    if set(full) != set(drop):
        raise V04C3ConfirmatoryError("FULL/DROP_C3 pair key sets differ")
    for key in sorted(full):
        left, right = full[key], drop[key]
        for field in ("evaluation_seed", "initialization_seed", "start_epoch", "initial_state_sha256", "initial_mask_sha256", "fading_field_sha256"):
            if left.get(field) != right.get(field):
                raise V04C3ConfirmatoryError(f"matched pair differs in {field}: {key}")
        if left.get("fading_field_components") != right.get("fading_field_components"):
            raise V04C3ConfirmatoryError(f"matched pair fading components differ: {key}")
        components = left.get("fading_field_components")
        if (
            not isinstance(components, list)
            or len(components) != 3
            or components[0] != FIELD_COMPONENT
            or components[2] != key[1]
            or (gate_authority_sha256 is not None and components[1] != gate_authority_sha256)
        ):
            raise V04C3ConfirmatoryError(f"fading field components are not preregistered: {key}")


def _validate_common_world_identity(
    rows: Sequence[Mapping[str, Any]],
    *,
    gate_authority_sha256: str | None = None,
) -> None:
    """Ensure all three initializations see one physical world per seed."""

    groups: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[int(row["evaluation_seed"])].append(row)
    if set(groups) != set(EVALUATION_SEEDS):
        raise V04C3ConfirmatoryError("common physical-world seed block is incomplete")
    for seed, group in groups.items():
        anchor = group[0]
        fields = (
            "start_epoch",
            "initial_state_sha256",
            "initial_mask_sha256",
            "fading_field_sha256",
            "fading_field_components",
        )
        for row in group[1:]:
            for field in fields:
                if row.get(field) != anchor.get(field):
                    raise V04C3ConfirmatoryError(
                        f"initialization/policy physical world differs in {field}: {seed}"
                    )
        components = anchor.get("fading_field_components")
        if (
            not isinstance(components, list)
            or len(components) != 3
            or components[0] != FIELD_COMPONENT
            or components[2] != seed
            or (gate_authority_sha256 is not None and components[1] != gate_authority_sha256)
        ):
            raise V04C3ConfirmatoryError(
                f"physical world {seed} does not use the preregistered field root"
            )


def _per_initialization(full_rows: Sequence[Mapping[str, Any]], drop_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    full_groups: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    drop_groups: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in full_rows:
        full_groups[int(row["initialization_seed"])].append(row)
    for row in drop_rows:
        drop_groups[int(row["initialization_seed"])].append(row)
    if set(full_groups) != set(drop_groups) or set(full_groups) != set(INITIALIZATION_SEEDS):
        raise V04C3ConfirmatoryError("confirmatory initialization groups are incomplete")
    result: dict[str, Any] = {}
    for seed in INITIALIZATION_SEEDS:
        full = aggregate_policy_rows(full_groups[seed])
        drop = aggregate_policy_rows(drop_groups[seed])
        result[str(seed)] = {
            "full": full,
            "drop_c3": drop,
            "ee_difference_bits_per_j": full["pooled_ratio_of_sums_ee_bits_per_j"] - drop["pooled_ratio_of_sums_ee_bits_per_j"],
            "ee_difference_percent": (full["pooled_ratio_of_sums_ee_bits_per_j"] / drop["pooled_ratio_of_sums_ee_bits_per_j"] - 1.0) * 100.0 if drop["pooled_ratio_of_sums_ee_bits_per_j"] else 0.0,
            "served_fraction_difference": full["served_fraction"] - drop["served_fraction"],
        }
    return result


def _per_world(
    full_rows: Sequence[Mapping[str, Any]],
    drop_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    full_groups: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    drop_groups: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in full_rows:
        full_groups[int(row["evaluation_seed"])].append(row)
    for row in drop_rows:
        drop_groups[int(row["evaluation_seed"])].append(row)
    if set(full_groups) != set(drop_groups) or set(full_groups) != set(EVALUATION_SEEDS):
        raise V04C3ConfirmatoryError("confirmatory physical-world groups are incomplete")
    result: list[dict[str, Any]] = []
    for seed in EVALUATION_SEEDS:
        full = aggregate_policy_rows(full_groups[seed])
        drop = aggregate_policy_rows(drop_groups[seed])
        result.append(
            {
                "evaluation_seed": seed,
                "full_ee_bits_per_j": full["pooled_ratio_of_sums_ee_bits_per_j"],
                "drop_c3_ee_bits_per_j": drop["pooled_ratio_of_sums_ee_bits_per_j"],
                "ee_difference_bits_per_j": full["pooled_ratio_of_sums_ee_bits_per_j"] - drop["pooled_ratio_of_sums_ee_bits_per_j"],
                "full_served_user_steps": full["served_user_steps"],
                "drop_c3_served_user_steps": drop["served_user_steps"],
                "served_difference": full["served_user_steps"] - drop["served_user_steps"],
            }
        )
    return result


def paired_world_bootstrap(
    full_rows: Sequence[Mapping[str, Any]],
    drop_rows: Sequence[Mapping[str, Any]],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    if replicates != BOOTSTRAP_REPLICATES or seed != BOOTSTRAP_SEED:
        raise V04C3ConfirmatoryError("bootstrap replicates and seed are frozen")
    for row in [*full_rows, *drop_rows]:
        _validate_row(row)
    _pair_rows(full_rows, drop_rows)
    worlds = tuple(EVALUATION_SEEDS)
    full_by_world = {
        world: [row for row in full_rows if int(row["evaluation_seed"]) == world]
        for world in worlds
    }
    drop_by_world = {
        world: [row for row in drop_rows if int(row["evaluation_seed"]) == world]
        for world in worlds
    }
    if any(not full_by_world[world] or not drop_by_world[world] for world in worlds):
        raise V04C3ConfirmatoryError("bootstrap world clusters are incomplete")
    # Validate each row once, then resample the already pooled world totals.
    # Re-running JSON/schema validation for every one of 10,000 replicates is
    # both unnecessary and needlessly expensive, while this preserves the
    # preregistered cluster unit and ratio-of-sums estimator exactly.
    full_bits = np.asarray(
        [math.fsum(float(row["total_bits"]) for row in full_by_world[world]) for world in worlds],
        dtype=np.float64,
    )
    full_energy = np.asarray(
        [math.fsum(float(row["total_energy_j"]) for row in full_by_world[world]) for world in worlds],
        dtype=np.float64,
    )
    drop_bits = np.asarray(
        [math.fsum(float(row["total_bits"]) for row in drop_by_world[world]) for world in worlds],
        dtype=np.float64,
    )
    drop_energy = np.asarray(
        [math.fsum(float(row["total_energy_j"]) for row in drop_by_world[world]) for world in worlds],
        dtype=np.float64,
    )
    if (
        not np.all(np.isfinite(full_energy))
        or not np.all(np.isfinite(drop_energy))
        or np.any(full_energy <= 0.0)
        or np.any(drop_energy <= 0.0)
    ):
        raise V04C3ConfirmatoryError(
            "bootstrap FULL and DROP_C3 world energies must be positive"
        )
    rng = np.random.default_rng(seed)
    sampled = rng.integers(0, len(worlds), size=(replicates, len(worlds)))
    sampled_full_bits = np.sum(full_bits[sampled], axis=1, dtype=np.float64)
    sampled_full_energy = np.sum(full_energy[sampled], axis=1, dtype=np.float64)
    sampled_drop_bits = np.sum(drop_bits[sampled], axis=1, dtype=np.float64)
    sampled_drop_energy = np.sum(drop_energy[sampled], axis=1, dtype=np.float64)
    if (
        not np.all(np.isfinite(sampled_full_energy))
        or not np.all(np.isfinite(sampled_drop_energy))
        or np.any(sampled_full_energy <= 0.0)
        or np.any(sampled_drop_energy <= 0.0)
    ):
        raise V04C3ConfirmatoryError(
            "bootstrap sampled FULL and DROP_C3 energies must be positive"
        )
    sampled_drop_ee = sampled_drop_bits / sampled_drop_energy
    if not np.all(np.isfinite(sampled_drop_ee)) or np.any(sampled_drop_ee <= 0.0):
        raise V04C3ConfirmatoryError(
            "bootstrap DROP_C3 EE denominator must be positive"
        )
    values = (
        (sampled_full_bits / sampled_full_energy) / sampled_drop_ee - 1.0
    ) * 100.0
    if not np.all(np.isfinite(values)):
        raise V04C3ConfirmatoryError("bootstrap produced non-finite values")
    return {
        "replicates": replicates,
        "seed": seed,
        "world_count": len(worlds),
        "lower_percent": float(np.percentile(values, 2.5)),
        "upper_percent": float(np.percentile(values, 97.5)),
        "median_percent": float(np.percentile(values, 50.0)),
        "samples_sha256": hashlib.sha256(values.tobytes()).hexdigest(),
    }


def apply_decision_rule(
    *,
    full_summary: Mapping[str, Any],
    drop_summary: Mapping[str, Any],
    per_initialization: Mapping[str, Mapping[str, Any]],
    per_world: Sequence[Mapping[str, Any]],
    bootstrap: Mapping[str, Any],
) -> dict[str, Any]:
    init_ee_positive = sum(
        float(per_initialization[str(seed)]["ee_difference_bits_per_j"]) > 0.0
        for seed in INITIALIZATION_SEEDS
    )
    init_service_nonnegative = sum(
        float(per_initialization[str(seed)]["served_fraction_difference"]) >= 0.0
        for seed in INITIALIZATION_SEEDS
    )
    world_differences = [float(row["ee_difference_bits_per_j"]) for row in per_world]
    median_world = float(np.median(np.asarray(world_differences, dtype=np.float64)))
    positive_worlds = sum(value > 0.0 for value in world_differences)
    pooled_ee_difference = float(
        full_summary["pooled_ratio_of_sums_ee_bits_per_j"]
        - drop_summary["pooled_ratio_of_sums_ee_bits_per_j"]
    )
    pooled_ee_percent = (
        float(full_summary["pooled_ratio_of_sums_ee_bits_per_j"])
        / float(drop_summary["pooled_ratio_of_sums_ee_bits_per_j"])
        - 1.0
    ) * 100.0 if float(drop_summary["pooled_ratio_of_sums_ee_bits_per_j"]) else 0.0
    checks = {
        "pooled_full_ee_greater": pooled_ee_difference > 0.0,
        "at_least_two_initializations_ee_positive": init_ee_positive >= 2,
        "median_per_world_ee_positive": median_world > 0.0,
        "bootstrap_lower_bound_positive": float(bootstrap["lower_percent"]) > 0.0,
        "pooled_service_noninferior": float(full_summary["served_fraction"]) >= float(drop_summary["served_fraction"]),
        "at_least_two_initializations_service_nonnegative": init_service_nonnegative >= 2,
    }
    return {
        "status": STATUS_CONFIRM if all(checks.values()) else STATUS_NOT_CONFIRMED,
        "checks": checks,
        "pooled_ee_difference_bits_per_j": pooled_ee_difference,
        "pooled_ee_difference_percent": pooled_ee_percent,
        "median_per_world_ee_difference_bits_per_j": median_world,
        "positive_per_world_ee_count": positive_worlds,
        "positive_initializations": init_ee_positive,
        "service_nonnegative_initializations": init_service_nonnegative,
        "per_world_service_loss_count": sum(
            int(float(row["served_difference"]) < 0.0) for row in per_world
        ),
    }


def _prepare_payload(
    *,
    authority: AuthorityContext,
    manifest_file_sha256: str,
    manifest_sha256: str,
    gate_dir: Path,
    source_dir: Path,
    prior_screen_dir: Path,
    prereg_path: Path,
) -> dict[str, Any]:
    return {
        "schema": PREPARE_SCHEMA,
        "status": STATUS_PREPARED,
        "claim_ceiling": "FROZEN_C3_CONFIRMATORY_TRAIN_ONLY_NO_TEST_NO_TRAINING",
        "authority": authority.as_dict(),
        "gate_dir_basename": Path(gate_dir).name,
        "source_dir_basename": Path(source_dir).name,
        "prior_screen_dir_basename": Path(prior_screen_dir).name,
        "prereg_file_sha256": _file_sha256(prereg_path),
        "evaluator_code_manifest_file_sha256": manifest_file_sha256,
        "evaluator_code_manifest_sha256": manifest_sha256,
        "arms": list(ARMS),
        "evaluation_seeds": list(EVALUATION_SEEDS),
        "initialization_seeds": list(INITIALIZATION_SEEDS),
        "selected_q3_rung": SELECTED_Q3_RUNG,
        "evaluation_split": EVALUATION_SPLIT,
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "common_keyed_field": {
            "component": FIELD_COMPONENT,
            "key_axes": list(FIELD_KEY_AXES),
            "excluded_axes": ["initialization_seed", "policy_label"],
        },
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "resampling_unit": "physical_world_seed_with_all_three_initializations",
        },
        "test_split_opened": TEST_SPLIT_OPENED,
        "held_out_ee_evaluated": False,
        "episode_training": EPISODE_TRAINING,
        "gate_dir": str(Path(gate_dir).resolve()),
        "source_dir": str(Path(source_dir).resolve()),
        "prior_screen_dir": str(Path(prior_screen_dir).resolve()),
        "prereg_path": str(Path(prereg_path).resolve()),
    }


def prepare_confirmatory(
    *,
    gate_dir: Path = DEFAULT_GATE_DIR,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    prior_screen_dir: Path = DEFAULT_PRIOR_SCREEN_DIR,
    prereg_path: Path = DEFAULT_PREREG,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """Authenticate and seal the no-episode confirmatory work order."""

    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise V04C3ConfirmatoryError(
            f"refusing to overwrite confirmatory output: {destination}"
        )
    authority = authenticate_current_authority(
        gate_dir=Path(gate_dir),
        source_dir=Path(source_dir),
        prior_screen_dir=Path(prior_screen_dir),
        prereg_path=Path(prereg_path),
    )
    manifest = build_evaluator_code_manifest()
    manifest_path = destination / "evaluator-code-manifest.json"
    manifest_file_sha = _write_once_json(manifest_path, manifest)
    manifest_sha = _validate_code_manifest(manifest, current=True)
    payload = _prepare_payload(
        authority=authority,
        manifest_file_sha256=manifest_file_sha,
        manifest_sha256=manifest_sha,
        gate_dir=Path(gate_dir),
        source_dir=Path(source_dir),
        prior_screen_dir=Path(prior_screen_dir),
        prereg_path=Path(prereg_path),
    )
    prepare_path = destination / "prepare.json"
    prepare_file_sha = _write_once_json(prepare_path, payload)
    seal = {
        "schema": PREPARE_SEAL_SCHEMA,
        "prepare_file_sha256": prepare_file_sha,
        "evaluator_code_manifest_file_sha256": manifest_file_sha,
        "evaluator_code_manifest_sha256": manifest_sha,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }
    seal_file_sha = _write_once_json(destination / "prepare-seal.json", seal)
    return {
        "status": STATUS_PREPARED,
        "output_dir": str(destination.resolve()),
        "prepare_file_sha256": prepare_file_sha,
        "prepare_seal_file_sha256": seal_file_sha,
        "evaluator_code_manifest_file_sha256": manifest_file_sha,
        "evaluator_code_manifest_sha256": manifest_sha,
        "episode_opened": False,
    }


def _load_prepared(
    output_dir: Path,
    *,
    require_current_code: bool = True,
) -> tuple[dict[str, Any], AuthorityContext]:
    root = _regular_dir(output_dir, field="output_dir")
    manifest_path = root / "evaluator-code-manifest.json"
    prepare_path = root / "prepare.json"
    seal_path = root / "prepare-seal.json"
    manifest = _read_canonical_json(manifest_path)
    prepare = _read_canonical_json(prepare_path)
    seal = _read_canonical_json(seal_path)
    manifest_sha = _validate_code_manifest(manifest, current=require_current_code)
    manifest_file_sha = _file_sha256(manifest_path)
    prepare_sha = _file_sha256(prepare_path)
    if (
        prepare.get("schema") != PREPARE_SCHEMA
        or prepare.get("status") != STATUS_PREPARED
        or prepare.get("evaluator_code_manifest_file_sha256") != manifest_file_sha
        or prepare.get("evaluator_code_manifest_sha256") != manifest_sha
        or prepare.get("test_split_opened") is not False
        or prepare.get("held_out_ee_evaluated") is not False
        or prepare.get("episode_training") is not False
    ):
        raise V04C3ConfirmatoryError("prepare receipt is not authenticated")
    if (
        seal.get("schema") != PREPARE_SEAL_SCHEMA
        or seal.get("prepare_file_sha256") != prepare_sha
        or seal.get("evaluator_code_manifest_file_sha256") != manifest_file_sha
        or seal.get("evaluator_code_manifest_sha256") != manifest_sha
        or seal.get("test_split_opened") is not False
        or seal.get("held_out_ee_evaluated") is not False
        or seal.get("episode_training") is not False
    ):
        raise V04C3ConfirmatoryError("prepare seal is invalid")
    authority_payload = prepare.get("authority")
    if not isinstance(authority_payload, Mapping):
        raise V04C3ConfirmatoryError("prepare authority payload is missing")
    authority = AuthorityContext(
        gate_authority_sha256=str(authority_payload["gate_authority_sha256"]),
        gate_result_file_sha256=str(authority_payload["gate_result_file_sha256"]),
        gate_result_seal_file_sha256=str(authority_payload["gate_result_seal_file_sha256"]),
        source_manifest_sha256=str(authority_payload["source_manifest_sha256"]),
        schedule_sha256=str(authority_payload["schedule_sha256"]),
        train_surface_sha256=str(authority_payload["train_surface_sha256"]),
        selected_q3_rung=int(authority_payload["selected_q3_rung"]),
        prior_screen_result_file_sha256=str(authority_payload["prior_screen_result_file_sha256"]),
        prior_screen_result_seal_file_sha256=str(authority_payload["prior_screen_result_seal_file_sha256"]),
        prior_primary_receipt_file_sha256=str(authority_payload["prior_primary_receipt_file_sha256"]),
    )
    if (
        tuple(prepare.get("arms", [])) != ARMS
        or tuple(prepare.get("evaluation_seeds", [])) != EVALUATION_SEEDS
        or tuple(prepare.get("initialization_seeds", [])) != INITIALIZATION_SEEDS
        or prepare.get("selected_q3_rung") != SELECTED_Q3_RUNG
        or prepare.get("evaluation_split") != EVALUATION_SPLIT
        or prepare.get("users") != USERS
        or prepare.get("steps_per_episode") != STEPS_PER_EPISODE
    ):
        raise V04C3ConfirmatoryError("prepare protocol fields drifted")
    return prepare, authority


def _compare_authority(expected: AuthorityContext, observed: AuthorityContext) -> None:
    if expected != observed:
        raise V04C3ConfirmatoryError(
            "current authenticated authority differs from the sealed prepare receipt"
        )


def _result_payload(
    *,
    prepare: Mapping[str, Any],
    authority: AuthorityContext,
    full_rows: Sequence[Mapping[str, Any]],
    drop_rows: Sequence[Mapping[str, Any]],
    elapsed_s: float,
) -> dict[str, Any]:
    expected_rows = len(EVALUATION_SEEDS) * len(INITIALIZATION_SEEDS)
    if len(full_rows) != expected_rows or len(drop_rows) != expected_rows:
        raise V04C3ConfirmatoryError(
            "confirmatory result requires exactly 90 rows per arm"
        )
    _pair_rows(
        full_rows,
        drop_rows,
        gate_authority_sha256=authority.gate_authority_sha256,
    )
    _validate_common_world_identity(
        [*full_rows, *drop_rows],
        gate_authority_sha256=authority.gate_authority_sha256,
    )
    full_summary = aggregate_policy_rows(full_rows)
    drop_summary = aggregate_policy_rows(drop_rows)
    per_initialization = _per_initialization(full_rows, drop_rows)
    per_world = _per_world(full_rows, drop_rows)
    bootstrap = paired_world_bootstrap(full_rows, drop_rows)
    decision = apply_decision_rule(
        full_summary=full_summary,
        drop_summary=drop_summary,
        per_initialization=per_initialization,
        per_world=per_world,
        bootstrap=bootstrap,
    )
    return {
        "schema": RESULT_SCHEMA,
        "status": STATUS_COMPLETE,
        "scientific_status": decision["status"],
        "claim_ceiling": "FROZEN_C3_CONFIRMATORY_TRAIN_EE_NO_TEST",
        "authority": authority.as_dict(),
        "arms": list(ARMS),
        "evaluation_seeds": list(EVALUATION_SEEDS),
        "initialization_seeds": list(INITIALIZATION_SEEDS),
        "selected_q3_rung": SELECTED_Q3_RUNG,
        "evaluation_split": EVALUATION_SPLIT,
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "full": {
            "summary": full_summary,
            "rows": list(full_rows),
        },
        "drop_c3": {
            "summary": drop_summary,
            "rows": list(drop_rows),
        },
        "per_initialization": per_initialization,
        "per_world": per_world,
        "bootstrap": bootstrap,
        "decision": decision,
        "elapsed_s": float(elapsed_s),
        "test_split_opened": TEST_SPLIT_OPENED,
        "held_out_ee_evaluated": HELD_OUT_EE_EVALUATED,
        "episode_training": EPISODE_TRAINING,
        "evaluator_code_manifest_file_sha256": prepare["evaluator_code_manifest_file_sha256"],
        "evaluator_code_manifest_sha256": prepare["evaluator_code_manifest_sha256"],
    }


def run_confirmatory(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    gate_dir: Path | None = None,
    source_dir: Path | None = None,
    prior_screen_dir: Path | None = None,
    v03_root: Path = DEFAULT_V03_ROOT,
    prereg_path: Path = DEFAULT_PREREG,
    tle_root: Path = DEFAULT_TLE_ROOT,
    episode_runner: Callable[..., dict[str, Any]] = evaluate_episode,
) -> dict[str, Any]:
    """Run the frozen 180-episode block after all no-episode guards pass."""

    started = time.perf_counter()
    prepare, prepared_authority = _load_prepared(Path(output_dir), require_current_code=True)
    gate_path = Path(gate_dir) if gate_dir is not None else Path(prepare["gate_dir"])
    source_path = Path(source_dir) if source_dir is not None else Path(prepare["source_dir"])
    prior_path = Path(prior_screen_dir) if prior_screen_dir is not None else Path(prepare["prior_screen_dir"])
    current_authority = authenticate_current_authority(
        gate_dir=gate_path,
        source_dir=source_path,
        prior_screen_dir=prior_path,
        prereg_path=Path(prereg_path),
    )
    _compare_authority(prepared_authority, current_authority)
    if _file_sha256(Path(prereg_path)) != prepare["prereg_file_sha256"]:
        raise V04C3ConfirmatoryError("PREREG bytes changed after prepare")
    # ``authenticate_current_authority`` deliberately returns only the
    # compact lineage context.  The selected-checkpoint loader additionally
    # needs the authenticated per-initialization paths, so obtain that full
    # receipt again without opening a dataset or episode.
    gate_receipt = screen.authenticate_gate(
        Path(gate_path),
        source_dir=Path(source_path),
        prereg_path=Path(prereg_path),
    )
    observed_again = AuthorityContext(
        gate_authority_sha256=str(gate_receipt["authority_sha256"]),
        gate_result_file_sha256=str(gate_receipt["result_file_sha256"]),
        gate_result_seal_file_sha256=str(gate_receipt["authority_seal_file_sha256"]),
        source_manifest_sha256=str(gate_receipt["source_manifest_sha256"]),
        schedule_sha256=str(gate_receipt["schedule_sha256"]),
        train_surface_sha256=str(gate_receipt["train_surface_sha256"]),
        selected_q3_rung=int(gate_receipt["selected_q3_rung"]),
        prior_screen_result_file_sha256=current_authority.prior_screen_result_file_sha256,
        prior_screen_result_seal_file_sha256=current_authority.prior_screen_result_seal_file_sha256,
        prior_primary_receipt_file_sha256=current_authority.prior_primary_receipt_file_sha256,
    )
    _compare_authority(current_authority, observed_again)
    record = read_prereg(Path(prereg_path))
    result_path = Path(output_dir) / "result.json"
    seal_path = Path(output_dir) / "result-seal.json"
    if result_path.exists() or result_path.is_symlink() or seal_path.exists() or seal_path.is_symlink():
        raise V04C3ConfirmatoryError("refusing to overwrite confirmatory result or seal")

    # The TLE view is not opened until every authority, code, seed, and
    # no-TEST guard above has passed.
    full_rows: list[dict[str, Any]] = []
    drop_rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="mcrl-v04-c3-confirmatory-tle-") as temporary:
        archive = _frozen_archive(record, Path(tle_root), Path(temporary) / "frozen-tle")
        for evaluation_seed in EVALUATION_SEEDS:
            field = _field_for_seed(
                gate_authority_sha256=current_authority.gate_authority_sha256,
                evaluation_seed=evaluation_seed,
            )
            for initialization_seed in INITIALIZATION_SEEDS:
                trainer = screen.load_gate_selected_hybrid(
                    gate_receipt,
                    v03_root=Path(v03_root),
                    initialization_seed=initialization_seed,
                )
                _prepare_trainer_for_eval(trainer)
                for policy_label in ARMS:
                    row = episode_runner(
                        trainer,
                        archive,
                        gate_authority_sha256=current_authority.gate_authority_sha256,
                        initialization_seed=initialization_seed,
                        evaluation_seed=evaluation_seed,
                        policy_label=policy_label,
                        field=field,
                    )
                    _validate_row(row, policy=policy_label)
                    if row["fading_field_sha256"] != field.root_digest:
                        raise V04C3ConfirmatoryError("episode row field digest drifted")
                    (full_rows if policy_label == "FULL" else drop_rows).append(row)
    # Recheck the manifest immediately before sealing the scientific result.
    manifest = _read_canonical_json(Path(output_dir) / "evaluator-code-manifest.json")
    _validate_code_manifest(manifest, current=True)
    elapsed_s = time.perf_counter() - started
    result = _result_payload(
        prepare=prepare,
        authority=current_authority,
        full_rows=full_rows,
        drop_rows=drop_rows,
        elapsed_s=elapsed_s,
    )
    result_file_sha = _write_once_json(result_path, result)
    seal = {
        "schema": RESULT_SEAL_SCHEMA,
        "result_file_sha256": result_file_sha,
        "prepare_file_sha256": _file_sha256(Path(output_dir) / "prepare.json"),
        "prepare_seal_file_sha256": _file_sha256(Path(output_dir) / "prepare-seal.json"),
        "evaluator_code_manifest_file_sha256": prepare["evaluator_code_manifest_file_sha256"],
        "evaluator_code_manifest_sha256": prepare["evaluator_code_manifest_sha256"],
        "test_split_opened": TEST_SPLIT_OPENED,
        "held_out_ee_evaluated": HELD_OUT_EE_EVALUATED,
        "episode_training": EPISODE_TRAINING,
    }
    seal_file_sha = _write_once_json(seal_path, seal)
    return {
        "status": result["scientific_status"],
        "result_file_sha256": result_file_sha,
        "result_seal_file_sha256": seal_file_sha,
        "episodes": len(full_rows) + len(drop_rows),
        "episode_training": False,
        "test_split_opened": False,
    }


def _close_float(left: object, right: object) -> bool:
    return isinstance(left, (int, float)) and isinstance(right, (int, float)) and math.isclose(
        float(left), float(right), rel_tol=0.0, abs_tol=1e-9
    )


def _verify_summary(expected: Mapping[str, Any], actual: Mapping[str, Any], *, label: str) -> None:
    if set(expected) != set(actual):
        raise V04C3ConfirmatoryError(f"{label} summary fields changed")
    for key in expected:
        if isinstance(expected[key], (int, float)):
            if not _close_float(expected[key], actual[key]):
                raise V04C3ConfirmatoryError(f"{label} summary changed in {key}")
        elif expected[key] != actual[key]:
            raise V04C3ConfirmatoryError(f"{label} summary changed in {key}")


def verify_confirmatory(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Receipt-only verification; never opens source, TLE, trainer, or episodes."""

    root = _regular_dir(output_dir, field="output_dir")
    prepare, authority = _load_prepared(root, require_current_code=True)
    result_path = root / "result.json"
    seal_path = root / "result-seal.json"
    result = _read_canonical_json(result_path)
    seal = _read_canonical_json(seal_path)
    result_sha = _file_sha256(result_path)
    if (
        seal.get("schema") != RESULT_SEAL_SCHEMA
        or seal.get("result_file_sha256") != result_sha
        or seal.get("prepare_file_sha256") != _file_sha256(root / "prepare.json")
        or seal.get("prepare_seal_file_sha256") != _file_sha256(root / "prepare-seal.json")
        or seal.get("evaluator_code_manifest_file_sha256") != prepare["evaluator_code_manifest_file_sha256"]
        or seal.get("evaluator_code_manifest_sha256") != prepare["evaluator_code_manifest_sha256"]
        or seal.get("test_split_opened") is not False
        or seal.get("held_out_ee_evaluated") is not True
        or seal.get("episode_training") is not False
    ):
        raise V04C3ConfirmatoryError("confirmatory result seal is invalid")
    if (
        result.get("schema") != RESULT_SCHEMA
        or result.get("status") != STATUS_COMPLETE
        or result.get("authority") != authority.as_dict()
        or tuple(result.get("arms", [])) != ARMS
        or tuple(result.get("evaluation_seeds", [])) != EVALUATION_SEEDS
        or tuple(result.get("initialization_seeds", [])) != INITIALIZATION_SEEDS
        or result.get("selected_q3_rung") != SELECTED_Q3_RUNG
        or result.get("evaluation_split") != EVALUATION_SPLIT
        or result.get("users") != USERS
        or result.get("steps_per_episode") != STEPS_PER_EPISODE
        or result.get("test_split_opened") is not False
        or result.get("held_out_ee_evaluated") is not True
        or result.get("episode_training") is not False
    ):
        raise V04C3ConfirmatoryError("confirmatory result envelope is invalid")
    full_block = result.get("full")
    drop_block = result.get("drop_c3")
    if not isinstance(full_block, Mapping) or not isinstance(drop_block, Mapping):
        raise V04C3ConfirmatoryError("confirmatory arm blocks are missing")
    full_rows = full_block.get("rows")
    drop_rows = drop_block.get("rows")
    if not isinstance(full_rows, list) or not isinstance(drop_rows, list):
        raise V04C3ConfirmatoryError("confirmatory arm rows are missing")
    if len(full_rows) != len(EVALUATION_SEEDS) * len(INITIALIZATION_SEEDS) or len(drop_rows) != len(full_rows):
        raise V04C3ConfirmatoryError("confirmatory row budget is not exactly 30x3 per arm")
    for row in full_rows:
        if not isinstance(row, Mapping):
            raise V04C3ConfirmatoryError("FULL row is malformed")
        _validate_row(row, policy="FULL")
    for row in drop_rows:
        if not isinstance(row, Mapping):
            raise V04C3ConfirmatoryError("DROP_C3 row is malformed")
        _validate_row(row, policy="DROP_C3")
    _pair_rows(
        full_rows,
        drop_rows,
        gate_authority_sha256=authority.gate_authority_sha256,
    )
    _validate_common_world_identity(
        [*full_rows, *drop_rows],
        gate_authority_sha256=authority.gate_authority_sha256,
    )
    full_summary = aggregate_policy_rows(full_rows)
    drop_summary = aggregate_policy_rows(drop_rows)
    _verify_summary(full_block.get("summary", {}), full_summary, label="FULL")
    _verify_summary(drop_block.get("summary", {}), drop_summary, label="DROP_C3")
    per_initialization = _per_initialization(full_rows, drop_rows)
    per_world = _per_world(full_rows, drop_rows)
    bootstrap = paired_world_bootstrap(full_rows, drop_rows)
    decision = apply_decision_rule(
        full_summary=full_summary,
        drop_summary=drop_summary,
        per_initialization=per_initialization,
        per_world=per_world,
        bootstrap=bootstrap,
    )
    if result.get("per_initialization") != per_initialization or result.get("per_world") != per_world:
        raise V04C3ConfirmatoryError("confirmatory paired summaries changed")
    if result.get("bootstrap") != bootstrap or result.get("decision") != decision:
        raise V04C3ConfirmatoryError("confirmatory endpoint or decision changed")
    if result.get("scientific_status") != decision["status"]:
        raise V04C3ConfirmatoryError("confirmatory scientific status changed")
    return {
        "status": result["scientific_status"],
        "result_file_sha256": result_sha,
        "rows_per_arm": len(full_rows),
        "episode_opened": False,
        "receipt_only": True,
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="phase", required=True)

    prepare = subparsers.add_parser("prepare", help="authenticate and seal without episodes")
    prepare.add_argument("--gate-dir", type=Path, default=DEFAULT_GATE_DIR)
    prepare.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    prepare.add_argument("--prior-screen-dir", type=Path, default=DEFAULT_PRIOR_SCREEN_DIR)
    prepare.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    prepare.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)

    run = subparsers.add_parser("run", help="run the frozen confirmatory block")
    run.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    run.add_argument("--gate-dir", type=Path, default=None)
    run.add_argument("--source-dir", type=Path, default=None)
    run.add_argument("--prior-screen-dir", type=Path, default=None)
    run.add_argument("--v03-root", type=Path, default=DEFAULT_V03_ROOT)
    run.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    run.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)

    verify = subparsers.add_parser("verify", help="receipt-only verification")
    verify.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    if args.phase == "prepare":
        result = prepare_confirmatory(
            gate_dir=args.gate_dir,
            source_dir=args.source_dir,
            prior_screen_dir=args.prior_screen_dir,
            prereg_path=args.prereg,
            output_dir=args.output_dir,
        )
    elif args.phase == "run":
        result = run_confirmatory(
            output_dir=args.output_dir,
            gate_dir=args.gate_dir,
            source_dir=args.source_dir,
            prior_screen_dir=args.prior_screen_dir,
            v03_root=args.v03_root,
            prereg_path=args.prereg,
            tle_root=args.tle_root,
        )
    else:
        result = verify_confirmatory(args.output_dir)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":  # pragma: no cover - command-line seam
    raise SystemExit(main())
