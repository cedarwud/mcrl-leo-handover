#!/usr/bin/env python3
"""Audited learner adapter for the V0.23 LC-SRS observability gate.

The staged runner deliberately contains no dynamic learner import.  This
module is the explicit server-side seam that may be injected into
``run_fit_stage`` after the eight source shards and their source manifest have
been authenticated.  Importing it is safe: no simulator, TLE, TEST split, or
optimizer update is opened during import.

The adapter has two intentionally separate responsibilities:

* reopen the exact JSON/NPZ source panel, fail closed on any provenance or
  reconstruction mismatch, and prepare one seven-world LOO fold; and
* call the frozen V0.23 fit function, evaluate its returned network on the
  untouched held-out world, and persist immutable model/metric/placebo
  sidecars before returning a runner-compatible receipt.

The default fit function is the production 2,000-update
``fit_lcsrs_loo_arm``.  Tests and a non-heavy dry-run may inject a function
with the exact same signature; the adapter still validates the resulting
network and receipt, and always performs held-out inference itself.  No
injected function may supply held-out metrics or bypass source loading.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Protocol, TypeAlias

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3QNetwork  # noqa: E402
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (  # noqa: E402
    LCSRSAnchorRecord,
)
from mcrl.runtime import ee_axis_lcsrs_c3_gate_fit as _gate_fit  # noqa: E402
from mcrl.runtime.ee_axis_lcsrs_c3_learner import (  # noqa: E402
    LCSRSC3FitReceipt,
    LCSRS_C3_LEARNER_CONFIG_SHA256,
    LCSRS_C3_UPDATE_COUNT,
    lcsrs_c3_network_sha256,
)
from mcrl.runtime import ee_axis_lcsrs_c3_source_artifact as _source_artifact  # noqa: E402


LCSRSC3FoldFit = _gate_fit.LCSRSC3FoldFit
LCSRSC3FoldSource = _gate_fit.LCSRSC3FoldSource
evaluate_lcsrs_heldout_rows = _gate_fit.evaluate_lcsrs_heldout_rows
V023_GATE_WORLDS = tuple(range(2026121801, 2026121809))
V023_STUDENT_SEEDS = (2026135201, 2026135202, 2026135203)
V023_PLACEBO_KEY = _gate_fit.V023_PLACEBO_KEY
V023_PLACEBO_KEY_SHA256 = _gate_fit.V023_PLACEBO_KEY_SHA256

V023_CONTRACT_SHA256 = "027e09a75a2e775b81b570cd49f6637dd10d55220d3ace2cf26a5b37ab002be5"
V023_EXECUTION_ADDENDUM_SHA256 = _source_artifact.V023_EXECUTION_ADDENDUM_SHA256
V023_SOURCE_ARTIFACT_SCHEMA = _source_artifact.V023_SOURCE_ARTIFACT_SCHEMA
V023_SOURCE_ARTIFACT_VERSION = _source_artifact.V023_SOURCE_ARTIFACT_VERSION
V023_SOURCE_CLAIM_CEILING = _source_artifact.V023_SOURCE_CLAIM_CEILING
V023_SOURCE_SHARD_SCHEMA = _source_artifact.V023_SOURCE_SHARD_SCHEMA
V023WorldSourceArtifact = _source_artifact.V023WorldSourceArtifact
LCSRSC3SourceArtifactError = _source_artifact.LCSRSC3SourceArtifactError


@contextmanager
def _r7_schedule(module: object):
    """Temporarily bind only the copied producer's panel identity.

    The production fit/source-artifact implementation remains byte-unchanged in
    ``src``.  Each fit worker is a separate process; restoring the module
    constants also keeps import-only tests from leaking the R7 schedule into
    unrelated callers.
    """

    old_worlds = getattr(module, "V023_GATE_WORLDS", None)
    world_name = "V023_GATE_WORLDS"
    if old_worlds is None:
        old_worlds = getattr(module, "V023_WORLDS")
        world_name = "V023_WORLDS"
    old_seeds = getattr(module, "V023_STUDENT_SEEDS", None)
    old_contract = getattr(module, "V023_CONTRACT_SHA256", None)
    setattr(module, world_name, V023_GATE_WORLDS)
    if old_seeds is not None:
        setattr(module, "V023_STUDENT_SEEDS", V023_STUDENT_SEEDS)
    if old_contract is not None:
        setattr(module, "V023_CONTRACT_SHA256", V023_CONTRACT_SHA256)
    try:
        yield
    finally:
        setattr(module, world_name, old_worlds)
        if old_seeds is not None:
            setattr(module, "V023_STUDENT_SEEDS", old_seeds)
        if old_contract is not None:
            setattr(module, "V023_CONTRACT_SHA256", old_contract)


def prepare_lcsrs_loo_fold(*args: Any, **kwargs: Any) -> LCSRSC3FoldSource:
    with _r7_schedule(_gate_fit):
        return _gate_fit.prepare_lcsrs_loo_fold(*args, **kwargs)


def fit_lcsrs_loo_arm(*args: Any, **kwargs: Any) -> LCSRSC3FoldFit:
    with _r7_schedule(_gate_fit):
        return _gate_fit.fit_lcsrs_loo_arm(*args, **kwargs)


def load_v023_world_source_artifact(*args: Any, **kwargs: Any) -> V023WorldSourceArtifact:
    with _r7_schedule(_source_artifact):
        return _source_artifact.load_v023_world_source_artifact(*args, **kwargs)


V023_GATE_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1"
V023_FIT_SCHEMA = f"{V023_GATE_SCHEMA}-fit-shard"
V023_FIT_ARTIFACT_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-fit-artifact-v1"
V023_FIT_METRICS_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-fit-metrics-v1"
V023_FIT_MODEL_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-fit-model-v1"
V023_FIT_PLACEBO_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-fit-placebo-v1"
V023_SOURCE_MANIFEST_SCHEMA = f"{V023_GATE_SCHEMA}-source-manifest"
V023_FIT_CLAIM_CEILING = V023_SOURCE_CLAIM_CEILING
V023_FIT_UPDATE_COUNT = LCSRS_C3_UPDATE_COUNT
V023_FIT_ARRAY_DOMAIN = "v023-fit-array-v1"
V023_FIT_MODEL_ARRAY_DOMAIN = "v023-fit-model-array-v1"
V023_FIT_PREDICTION_ARRAY_DOMAIN = "v023-fit-prediction-array-v1"


class V023LearnerAdapterError(RuntimeError):
    """A V0.23 source, fold, fit, or persistence boundary failed closed."""


class FitFunction(Protocol):
    """Exact injectable fit seam used by the audited adapter."""

    def __call__(
        self,
        source: LCSRSC3FoldSource,
        *,
        arm: str,
        student_seed: int,
        device: torch.device | str,
    ) -> tuple[LCSRSC3QNetwork, LCSRSC3FitReceipt] | LCSRSC3FoldFit:
        """Return a fitted Q3 network and its frozen fit receipt."""


FitFunctionType: TypeAlias = Callable[..., Any]


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023LearnerAdapterError("value is not finite canonical JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023LearnerAdapterError(f"expected regular file: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023LearnerAdapterError(f"{field} is not a lowercase SHA-256")
    return value


def _canonical_json(path: Path, *, field: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023LearnerAdapterError(f"{field} is missing or is a symlink")
    raw = target.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023LearnerAdapterError(f"{field} is not ASCII JSON") from error
    if not isinstance(payload, dict):
        raise V023LearnerAdapterError(f"{field} root is not an object")
    canonical = _canonical_bytes(payload)
    if raw not in (canonical, canonical + b"\n"):
        raise V023LearnerAdapterError(f"{field} is not canonical JSON")
    return payload


def _jsonable(value: object) -> object:
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (bool, int, str)) or value is None:
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise V023LearnerAdapterError("non-finite float in receipt")
        return value
    raise V023LearnerAdapterError(
        f"unsupported value in canonical receipt: {type(value).__name__}"
    )


def _array_digest(
    value: object,
    *,
    domain: str = V023_FIT_ARRAY_DOMAIN,
) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    if array.dtype == object:
        raise V023LearnerAdapterError("object dtype is forbidden in fit sidecars")
    digest = hashlib.sha256()
    digest.update(domain.encode("ascii"))
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _array_metadata(
    arrays: Mapping[str, np.ndarray],
    *,
    domain: str = V023_FIT_ARRAY_DOMAIN,
) -> dict[str, dict[str, object]]:
    metadata: dict[str, dict[str, object]] = {}
    for name in sorted(arrays):
        array = np.ascontiguousarray(np.asarray(arrays[name]))
        if array.dtype == object:
            raise V023LearnerAdapterError(
                f"fit array {name} has forbidden object dtype"
            )
        metadata[name] = {
            "dtype": array.dtype.str,
            "shape": list(array.shape),
            "sha256": _array_digest(array, domain=domain),
        }
    return metadata


def _write_once_bytes(path: Path, payload: bytes) -> str:
    """Atomically create a file and refuse an existing target.

    ``os.link`` publishes a fully fsynced temporary file without the overwrite
    race of a precheck followed by ``os.replace``.  The temporary file and
    target must be on the same filesystem, which is true for one shard
    directory.
    """

    target = Path(path)
    if target.exists() or target.is_symlink():
        raise V023LearnerAdapterError(f"refusing to overwrite fit artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_path, target)
        except FileExistsError as error:
            raise V023LearnerAdapterError(
                f"refusing to overwrite fit artifact: {target}"
            ) from error
        digest = hashlib.sha256(payload).hexdigest()
    finally:
        temporary_path.unlink(missing_ok=True)
    return digest


def _write_once_json(path: Path, payload: Mapping[str, Any]) -> str:
    return _write_once_bytes(path, _canonical_bytes(dict(payload)))


def _write_once_npz(
    path: Path,
    arrays: Mapping[str, np.ndarray],
    *,
    domain: str = V023_FIT_ARRAY_DOMAIN,
) -> tuple[str, dict[str, dict[str, object]]]:
    """Write a numeric-only NPZ and its immutable checksum sidecar."""

    metadata = _array_metadata(arrays, domain=domain)
    target = Path(path)
    digest_path = Path(f"{target}.sha256")
    if target.exists() or target.is_symlink():
        raise V023LearnerAdapterError(f"refusing to overwrite fit artifact: {target}")
    if digest_path.exists() or digest_path.is_symlink():
        raise V023LearnerAdapterError(
            f"refusing to overwrite fit artifact: {digest_path}"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            # Passing a file object prevents numpy from appending a second
            # .npz extension to the temporary filename.
            np.savez_compressed(handle, **{
                name: np.ascontiguousarray(np.asarray(value))
                for name, value in arrays.items()
            })
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_path, target)
        except FileExistsError as error:
            raise V023LearnerAdapterError(
                f"refusing to overwrite fit artifact: {target}"
            ) from error
    finally:
        temporary_path.unlink(missing_ok=True)
    digest = _file_sha256(target)
    _write_once_bytes(
        digest_path,
        f"{digest}  {target.name}\n".encode("ascii"),
    )
    return digest, metadata


def _verify_digest_file(path: Path, *, digest: str, target: Path) -> None:
    digest_path = Path(path)
    if digest_path.is_symlink() or not digest_path.is_file():
        raise V023LearnerAdapterError(
            f"fit digest sidecar is missing or is a symlink: {digest_path}"
        )
    expected = f"{digest}  {Path(target).name}\n".encode("ascii")
    if digest_path.read_bytes() != expected:
        raise V023LearnerAdapterError(
            f"fit digest sidecar disagrees with artifact: {digest_path}"
        )


def _safe_child(root: Path, relative: object, *, field: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise V023LearnerAdapterError(f"{field} is not a relative path")
    candidate = Path(root) / relative
    if candidate.is_symlink():
        raise V023LearnerAdapterError(f"{field} is a symlink")
    resolved_root = Path(root).resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise V023LearnerAdapterError(f"{field} escapes its root")
    return resolved


def _verify_receipt_seal(payload: Mapping[str, Any]) -> None:
    declared = _digest(payload.get("receipt_sha256"), field="receipt_sha256")
    unsigned = dict(payload)
    unsigned.pop("receipt_sha256", None)
    if canonical_sha256(unsigned) != declared:
        raise V023LearnerAdapterError("fit receipt seal disagrees with bytes")


def _safe_relative_name(root: Path, path: Path, *, field: str) -> str:
    root_resolved = Path(root).resolve()
    target = Path(path)
    if target.is_symlink():
        raise V023LearnerAdapterError(f"{field} is a symlink")
    resolved = target.resolve()
    if not resolved.is_relative_to(root_resolved):
        raise V023LearnerAdapterError(f"{field} escapes its root")
    return resolved.relative_to(root_resolved).as_posix()


def _verify_sealed_manifest(
    payload: Mapping[str, Any],
    *,
    preflight_manifest_sha256: str,
) -> str:
    """Authenticate the runner's two-hash source-manifest convention."""

    if payload.get("schema") != V023_SOURCE_MANIFEST_SCHEMA:
        raise V023LearnerAdapterError("source manifest schema drifted")
    if payload.get("status") != "PASS":
        raise V023LearnerAdapterError("source manifest is not PASS")
    if payload.get("claim_ceiling") != V023_FIT_CLAIM_CEILING:
        raise V023LearnerAdapterError("source manifest claim ceiling drifted")
    if payload.get("contract_sha256") != V023_CONTRACT_SHA256:
        raise V023LearnerAdapterError("source manifest contract hash drifted")
    if payload.get("preflight_manifest_sha256") != preflight_manifest_sha256:
        raise V023LearnerAdapterError("source manifest preflight hash drifted")
    if payload.get("split") != "TRAIN_DEVELOPMENT":
        raise V023LearnerAdapterError("source manifest is not TRAIN_DEVELOPMENT")
    if (
        payload.get("test_split_opened") is not False
        or payload.get("episode_training") is not False
        or payload.get("learner_update") is not False
    ):
        raise V023LearnerAdapterError("source manifest crossed a closed boundary")
    if payload.get("worlds") != list(V023_GATE_WORLDS):
        raise V023LearnerAdapterError("source manifest world panel drifted")
    if payload.get("source_count") != len(V023_GATE_WORLDS):
        raise V023LearnerAdapterError("source manifest count drifted")
    expected_shards = [
        {"world": world, "relative_name": f"source/world-{world}.json"}
        for world in V023_GATE_WORLDS
    ]
    if payload.get("shards") != expected_shards:
        raise V023LearnerAdapterError("source manifest shard schedule drifted")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != len(V023_GATE_WORLDS):
        raise V023LearnerAdapterError("source manifest entries are incomplete")
    for actual, expected in zip(entries, expected_shards, strict=True):
        if not isinstance(actual, Mapping):
            raise V023LearnerAdapterError("source manifest entry is malformed")
        if actual.get("world") != expected["world"]:
            raise V023LearnerAdapterError("source manifest entry world drifted")
        if actual.get("relative_name") != expected["relative_name"]:
            raise V023LearnerAdapterError("source manifest entry path drifted")
        _digest(actual.get("sha256"), field="source manifest entry sha256")
    source_hash = _digest(
        payload.get("source_manifest_sha256"),
        field="source_manifest_sha256",
    )
    unsigned = dict(payload)
    unsigned.pop("source_manifest_sha256", None)
    unsigned.pop("manifest_sha256", None)
    if canonical_sha256(unsigned) != source_hash:
        raise V023LearnerAdapterError("source manifest body hash disagrees")
    manifest_hash = _digest(payload.get("manifest_sha256"), field="manifest_sha256")
    unsigned_manifest = dict(payload)
    unsigned_manifest.pop("manifest_sha256", None)
    if canonical_sha256(unsigned_manifest) != manifest_hash:
        raise V023LearnerAdapterError("source manifest seal disagrees")
    return source_hash


@dataclass(frozen=True)
class V023SourcePanel:
    """Authenticated source artifacts and their fold-input manifest."""

    source_directory: Path
    source_manifest_path: Path
    source_manifest_sha256: str
    preflight_manifest_sha256: str
    artifacts: tuple[V023WorldSourceArtifact, ...]

    @property
    def records_by_world(self) -> dict[int, tuple[LCSRSAnchorRecord, ...]]:
        return {artifact.world: artifact.records for artifact in self.artifacts}

    @property
    def source_anchor_count(self) -> int:
        return sum(len(artifact.records) for artifact in self.artifacts)

    @property
    def source_pair_count(self) -> int:
        return sum(artifact.pair_count for artifact in self.artifacts)


def load_v023_source_panel(
    *,
    source_directory: Path,
    source_manifest: Path,
    preflight_manifest_sha256: str,
) -> V023SourcePanel:
    """Load and authenticate all eight JSON/NPZ source shards.

    Every child is reopened through the typed source-artifact loader.  The
    manifest's child byte hash is checked independently before reconstruction,
    so a fit worker cannot silently use a different source panel.
    """

    root_input = Path(source_directory)
    if root_input.is_symlink() or not root_input.is_dir():
        raise V023LearnerAdapterError("source directory is missing or is a symlink")
    root = root_input.resolve()
    manifest_input = Path(source_manifest)
    if manifest_input.is_symlink() or not manifest_input.is_file():
        raise V023LearnerAdapterError("source manifest is missing or is a symlink")
    manifest_path = manifest_input.resolve()
    if not manifest_path.is_relative_to(root):
        raise V023LearnerAdapterError("source manifest escapes source directory")
    preflight = _digest(
        preflight_manifest_sha256,
        field="preflight_manifest_sha256",
    )
    payload = _canonical_json(manifest_path, field="source manifest")
    source_hash = _verify_sealed_manifest(
        payload,
        preflight_manifest_sha256=preflight,
    )
    entries = payload["entries"]
    artifacts: list[V023WorldSourceArtifact] = []
    for world, entry in zip(V023_GATE_WORLDS, entries, strict=True):
        relative = str(entry["relative_name"])
        child_input = root / relative
        child_name = _safe_relative_name(root, child_input, field=f"world {world} source")
        if child_name != relative:
            raise V023LearnerAdapterError(f"world {world} source path is not canonical")
        declared_sha = _digest(entry["sha256"], field=f"world {world} source sha256")
        actual_sha = _file_sha256(child_input)
        if actual_sha != declared_sha:
            raise V023LearnerAdapterError(f"world {world} source byte hash disagrees")
        try:
            artifact = load_v023_world_source_artifact(
                child_input,
                expected_world=world,
                expected_preflight_sha256=preflight,
            )
        except (LCSRSC3SourceArtifactError, OSError, ValueError, TypeError) as error:
            raise V023LearnerAdapterError(
                f"world {world} source reconstruction failed: {error}"
            ) from error
        if artifact.index_sha256 != actual_sha:
            raise V023LearnerAdapterError(f"world {world} source digest was not retained")
        artifacts.append(artifact)
    if tuple(artifact.world for artifact in artifacts) != V023_GATE_WORLDS:
        raise V023LearnerAdapterError("source artifact world order drifted")
    return V023SourcePanel(
        source_directory=root,
        source_manifest_path=manifest_path,
        source_manifest_sha256=source_hash,
        preflight_manifest_sha256=preflight,
        artifacts=tuple(artifacts),
    )


def _target_source_digest(
    source: Sequence[LCSRSAnchorRecord],
    targets: Sequence[np.ndarray],
) -> str:
    if len(source) != len(targets):
        raise V023LearnerAdapterError("fit target/source count disagrees")
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-fitting-source-v1")
    for record, target in zip(source, targets, strict=True):
        digest.update(record.surface.content_digest.encode("ascii"))
        array = np.ascontiguousarray(np.asarray(target, dtype=np.float32))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _fit_result(
    result: object,
) -> tuple[LCSRSC3QNetwork, LCSRSC3FitReceipt]:
    if isinstance(result, LCSRSC3FoldFit):
        return result.network, result.fit_receipt
    if (
        isinstance(result, tuple)
        and len(result) == 2
        and isinstance(result[0], LCSRSC3QNetwork)
        and isinstance(result[1], LCSRSC3FitReceipt)
    ):
        return result[0], result[1]
    raise V023LearnerAdapterError(
        "fit function must return (LCSRSC3QNetwork, LCSRSC3FitReceipt)"
    )


def _expected_initial_network_sha256(student_seed: int) -> str:
    """Compute the frozen initialization digest without leaking RNG state."""

    from mcrl.runtime.ee_axis_lcsrs_c3_learner import make_lcsrs_c3_student

    state = torch.random.get_rng_state()
    try:
        network, _optimizer = make_lcsrs_c3_student(student_seed=student_seed)
        return lcsrs_c3_network_sha256(network)
    finally:
        torch.random.set_rng_state(state)


def _validate_fit_receipt(
    *,
    network: LCSRSC3QNetwork,
    receipt: LCSRSC3FitReceipt,
    fold: LCSRSC3FoldSource,
    arm: str,
    student_seed: int,
) -> tuple[np.ndarray, ...]:
    if receipt.arm != arm or receipt.student_seed != student_seed:
        raise V023LearnerAdapterError("fit receipt arm or seed drifted")
    if receipt.updates != V023_FIT_UPDATE_COUNT or receipt.batch_size != 256:
        raise V023LearnerAdapterError("fit receipt update budget drifted")
    if receipt.config_sha256 != LCSRS_C3_LEARNER_CONFIG_SHA256:
        raise V023LearnerAdapterError("fit learner config hash drifted")
    expected_anchors = tuple(
        record.content_digest for record in fold.training_records
    )
    if receipt.source_anchor_sha256s != expected_anchors:
        raise V023LearnerAdapterError("fit receipt training anchors drifted")
    if receipt.initial_network_sha256 != _expected_initial_network_sha256(student_seed):
        raise V023LearnerAdapterError("fit receipt initial model digest drifted")
    final_digest = lcsrs_c3_network_sha256(network)
    if receipt.final_network_sha256 != final_digest:
        raise V023LearnerAdapterError("fit receipt final model digest disagrees")
    losses = np.asarray(receipt.losses, dtype=np.float64)
    if losses.shape != (V023_FIT_UPDATE_COUNT,) or not np.all(np.isfinite(losses)):
        raise V023LearnerAdapterError("fit losses are incomplete or non-finite")
    targets: tuple[np.ndarray, ...]
    if arm == "INFORMED":
        targets = tuple(record.surface.normalized_targets for record in fold.training_records)
    elif arm == "MATCHED_PLACEBO":
        targets = tuple(fold.matched_placebo.normalized_targets_by_anchor)
    else:  # pragma: no cover - runner validates this first
        raise V023LearnerAdapterError("unknown fit arm")
    expected_target_digest = _target_source_digest(fold.training_records, targets)
    if receipt.target_source_sha256 != expected_target_digest:
        raise V023LearnerAdapterError("fit receipt target source digest disagrees")
    return targets


def _fixed_ascii(values: Sequence[str], *, width: int, field: str) -> np.ndarray:
    encoded: list[bytes] = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise V023LearnerAdapterError(f"{field} contains an empty identity")
        try:
            raw = value.encode("ascii")
        except UnicodeEncodeError as error:
            raise V023LearnerAdapterError(f"{field} contains non-ASCII identity") from error
        if len(raw) > width:
            raise V023LearnerAdapterError(f"{field} exceeds fixed-width storage")
        encoded.append(raw)
    return np.asarray(encoded, dtype=f"S{width}")


def _serialize_mapping(mapping: object) -> dict[str, object]:
    stratum = mapping.stratum
    return {
        "stratum": {
            "world_id": int(stratum.world_id),
            "phase_bin": int(stratum.phase_bin),
            "legal_opening": int(stratum.legal_opening),
            "destination_occupancy_bin": int(stratum.destination_occupancy_bin),
            "committed_destination_active": int(stratum.committed_destination_active),
            "base_gap_bin": int(stratum.base_gap_bin),
        },
        "source_anchor": int(mapping.source_anchor),
        "source_user": int(mapping.source_user),
        "source_action": int(mapping.source_action),
        "destination_anchor": int(mapping.destination_anchor),
        "destination_user": int(mapping.destination_user),
        "destination_action": int(mapping.destination_action),
        "shift": int(mapping.shift),
    }


def _fit_receipt_payload(
    receipt: LCSRSC3FitReceipt,
    *,
    losses_sha256: str,
) -> dict[str, object]:
    return {
        "schema": "multi-catfish-mcrl-v023-lcsrs-fit-receipt-v1",
        "arm": receipt.arm,
        "student_seed": int(receipt.student_seed),
        "source_anchor_sha256s": list(receipt.source_anchor_sha256s),
        "target_source_sha256": receipt.target_source_sha256,
        "initial_network_sha256": receipt.initial_network_sha256,
        "final_network_sha256": receipt.final_network_sha256,
        "config_sha256": receipt.config_sha256,
        "updates": int(receipt.updates),
        "batch_size": int(receipt.batch_size),
        "losses_count": int(np.asarray(receipt.losses).size),
        "losses_sha256": losses_sha256,
        # Keep the complete loss sequence in the fit receipt.  The NPZ copy
        # is the byte-addressable numeric audit surface.
        "losses": [float(value) for value in np.asarray(receipt.losses).tolist()],
    }


def _metric_payload(
    heldout: Any,
    *,
    fold: LCSRSC3FoldSource,
    arm: str,
    student_seed: int,
    source_manifest_sha256: str,
    metrics_npz_name: str,
    metrics_npz_sha256: str,
    fit_receipt: Mapping[str, object],
) -> dict[str, object]:
    sign = heldout.sign
    predictions = np.asarray(heldout.predictions, dtype=np.float64)
    targets = np.asarray(heldout.targets, dtype=np.float64)
    eligible = np.abs(targets) >= float(sign.threshold)
    positive = eligible & (targets > 0.0)
    negative = eligible & (targets < 0.0)
    predicted_positive = predictions > 0.0
    predicted_negative = predictions < 0.0
    positive_denominator = int(np.count_nonzero(positive))
    negative_denominator = int(np.count_nonzero(negative))
    correct_positive = int(np.count_nonzero(positive & predicted_positive))
    correct_negative = int(np.count_nonzero(negative & predicted_negative))
    positive_recall = (
        None if positive_denominator == 0 else correct_positive / positive_denominator
    )
    negative_recall = (
        None if negative_denominator == 0 else correct_negative / negative_denominator
    )
    balanced_accuracy = (
        None
        if positive_recall is None or negative_recall is None
        else (positive_recall + negative_recall) / 2.0
    )
    identities = [
        {
            "world": int(world),
            "anchor_id": anchor,
            "user": int(user),
            "action": int(action),
        }
        for world, anchor, user, action in heldout.identities
    ]
    return {
        "schema": V023_FIT_METRICS_SCHEMA,
        "claim_ceiling": V023_FIT_CLAIM_CEILING,
        "split": "TRAIN_DEVELOPMENT",
        "held_out_world": int(fold.held_out_world),
        "student_seed": int(student_seed),
        "arm": arm,
        "source_manifest_sha256": source_manifest_sha256,
        "training_worlds": sorted({int(record.world_id) for record in fold.training_records}),
        "training_anchor_count": len(fold.training_records),
        "heldout_anchor_count": len(fold.held_out_records),
        "heldout_supported_rows": int(len(heldout.identities)),
        "heldout_prediction_content_digest": heldout.content_digest,
        "spearman": None if heldout.spearman is None else float(heldout.spearman),
        "sign": {
            "threshold": float(sign.threshold),
            "total_rows": int(sign.total_rows),
            "evaluated_rows": int(sign.evaluated_rows),
            "excluded_rows": int(sign.excluded_rows),
            "correct_rows": int(sign.correct_rows),
            "accuracy": None if sign.accuracy is None else float(sign.accuracy),
            "raw_correct_rows": int(sign.correct_rows),
            "raw_sign_accuracy": None if sign.accuracy is None else float(sign.accuracy),
            "positive_denominator": positive_denominator,
            "negative_denominator": negative_denominator,
            "correct_positive": correct_positive,
            "correct_negative": correct_negative,
            "positive_recall": positive_recall,
            "negative_recall": negative_recall,
            "balanced_accuracy": balanced_accuracy,
            "decision_role": "RAW_SERIALIZED_BALANCED_AGGREGATED_AT_FINAL_R7",
        },
        "denominators": {
            "spearman_rows": int(len(heldout.predictions)),
            "sign_total_rows": int(sign.total_rows),
            "sign_evaluated_rows": int(sign.evaluated_rows),
            "sign_excluded_rows": int(sign.excluded_rows),
            "sign_positive_rows": positive_denominator,
            "sign_negative_rows": negative_denominator,
            "heldout_world_count": 1,
            "heldout_anchor_count": len(fold.held_out_records),
            "training_world_count": len(
                {record.world_id for record in fold.training_records}
            ),
        },
        "identities": identities,
        "sidecar": {
            "npz_relative_name": metrics_npz_name,
            "npz_sha256": metrics_npz_sha256,
            "array_domain": V023_FIT_PREDICTION_ARRAY_DOMAIN,
        },
        "fit_receipt_final_network_sha256": fit_receipt["final_network_sha256"],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": True,
    }


def _model_arrays(
    network: LCSRSC3QNetwork,
) -> tuple[dict[str, np.ndarray], dict[str, dict[str, object]]]:
    arrays: dict[str, np.ndarray] = {}
    metadata: dict[str, dict[str, object]] = {}
    for index, (name, tensor) in enumerate(sorted(network.state_dict().items())):
        if not isinstance(name, str) or not name:
            raise V023LearnerAdapterError("model parameter name is malformed")
        array = np.ascontiguousarray(tensor.detach().cpu().numpy())
        if array.dtype == object or not np.all(np.isfinite(array)):
            raise V023LearnerAdapterError("model state has nonfinite/object tensor")
        key = f"tensor_{index:04d}"
        arrays[key] = array
        metadata[name] = {
            "npz_key": key,
            "dtype": array.dtype.str,
            "shape": list(array.shape),
            "sha256": _array_digest(array, domain=V023_FIT_MODEL_ARRAY_DOMAIN),
        }
    if not arrays:
        raise V023LearnerAdapterError("model state is empty")
    return arrays, metadata


@dataclass(frozen=True)
class V023FitArtifacts:
    """Paths and hashes emitted by one immutable fit shard."""

    model_path: Path
    model_sha256: str
    network_sha256: str
    model_digest_path: Path
    model_array_metadata: Mapping[str, Mapping[str, object]]
    fit_receipt_path: Path
    fit_receipt_sha256: str
    metrics_path: Path
    metrics_sha256: str
    metrics_npz_path: Path
    metrics_npz_sha256: str
    metrics_npz_digest_path: Path
    placebo_path: Path
    placebo_sha256: str


class V023LearnerAdapter:
    """Explicit source-to-fit adapter for one runner ``FitShardSpec``."""

    def __init__(
        self,
        *,
        fit_function: FitFunctionType | None = None,
        device: torch.device | str = "cpu",
    ) -> None:
        self.fit_function = fit_lcsrs_loo_arm if fit_function is None else fit_function
        self.device = torch.device(device)

    @staticmethod
    def expected_fit_identities() -> tuple[tuple[int, int, str], ...]:
        """Return the exact 8 x 3 x 2 runner fit identity schedule."""

        return tuple(
            (world, seed, arm)
            for world in V023_GATE_WORLDS
            for seed in V023_STUDENT_SEEDS
            for arm in ("INFORMED", "MATCHED_PLACEBO")
        )

    def _check_spec(self, spec: Any) -> tuple[int, int, str, Path, Path, str]:
        try:
            held_out_world = int(spec.held_out_world)
            student_seed = int(spec.student_seed)
            arm = str(spec.arm)
            source_directory = Path(spec.source_directory)
            output = Path(spec.output)
            raw_source_manifest = spec.source_manifest
            source_manifest = (
                None
                if raw_source_manifest is None
                else Path(raw_source_manifest)
            )
            preflight = spec.preflight_manifest_sha256
        except (AttributeError, TypeError, ValueError) as error:
            raise V023LearnerAdapterError("FitShardSpec is malformed") from error
        if held_out_world not in V023_GATE_WORLDS:
            raise V023LearnerAdapterError("held-out world is outside frozen panel")
        if student_seed not in V023_STUDENT_SEEDS:
            raise V023LearnerAdapterError("student seed is outside frozen panel")
        if arm not in {"INFORMED", "MATCHED_PLACEBO"}:
            raise V023LearnerAdapterError("fit arm is outside frozen panel")
        if source_manifest is None:
            raise V023LearnerAdapterError("fit source manifest is required")
        if preflight is None:
            raise V023LearnerAdapterError("fit preflight digest is required")
        preflight_digest = _digest(preflight, field="preflight_manifest_sha256")
        if output.exists() or output.is_symlink():
            raise V023LearnerAdapterError(
                f"refusing to overwrite fit receipt: {output}"
            )
        return (
            held_out_world,
            student_seed,
            arm,
            source_directory,
            source_manifest,
            preflight_digest,
        )

    def _persist_sidecars(
        self,
        *,
        output: Path,
        network: LCSRSC3QNetwork,
        fit_receipt: LCSRSC3FitReceipt,
        fold: LCSRSC3FoldSource,
        heldout: Any,
        arm: str,
        student_seed: int,
        source_manifest_sha256: str,
    ) -> tuple[V023FitArtifacts, dict[str, object], dict[str, object]]:
        stem = output.with_suffix("")
        model_path = Path(f"{stem}.model.npz")
        model_digest_path = Path(f"{model_path}.sha256")
        fit_receipt_path = Path(f"{stem}.fit-receipt.json")
        metrics_path = Path(f"{stem}.metrics.json")
        metrics_npz_path = Path(f"{stem}.metrics.npz")
        metrics_npz_digest_path = Path(f"{metrics_npz_path}.sha256")
        placebo_path = Path(f"{stem}.placebo.json")
        targets = (
            tuple(record.surface.normalized_targets for record in fold.training_records)
            if arm == "INFORMED"
            else tuple(fold.matched_placebo.normalized_targets_by_anchor)
        )
        model_arrays, model_metadata = _model_arrays(network)
        model_npz_sha256, _unused_model_array_metadata = _write_once_npz(
            model_path,
            model_arrays,
            domain=V023_FIT_MODEL_ARRAY_DOMAIN,
        )
        # Keep the physical NPZ byte hash separate from the logical network
        # state hash.  The runner's model_sha256 is the artifact-byte hash;
        # model_state.logical_network_sha256 binds the typed state digest.
        model_logical_sha256 = lcsrs_c3_network_sha256(network)
        if model_logical_sha256 != fit_receipt.final_network_sha256:
            raise V023LearnerAdapterError("model state digest disagrees with receipt")

        identity_world = np.asarray(
            [int(world) for world, _anchor, _user, _action in heldout.identities],
            dtype=np.int64,
        )
        identity_anchor = _fixed_ascii(
            [anchor for _world, anchor, _user, _action in heldout.identities],
            width=256,
            field="heldout anchor identities",
        )
        identity_user = np.asarray(
            [int(user) for _world, _anchor, user, _action in heldout.identities],
            dtype=np.int64,
        )
        identity_action = np.asarray(
            [int(action) for _world, _anchor, _user, action in heldout.identities],
            dtype=np.int64,
        )
        losses = np.asarray(fit_receipt.losses, dtype=np.float64)
        prediction_arrays: dict[str, np.ndarray] = {
            "identity_world": identity_world,
            "identity_anchor": identity_anchor,
            "identity_user": identity_user,
            "identity_action": identity_action,
            "prediction": np.asarray(heldout.predictions, dtype=np.float64),
            "target": np.asarray(heldout.targets, dtype=np.float64),
            "loss": losses,
        }
        metrics_npz_sha256, prediction_metadata = _write_once_npz(
            metrics_npz_path,
            prediction_arrays,
            domain=V023_FIT_PREDICTION_ARRAY_DOMAIN,
        )
        losses_sha256 = _array_digest(
            losses,
            domain=V023_FIT_PREDICTION_ARRAY_DOMAIN,
        )
        fit_receipt_payload = _fit_receipt_payload(
            fit_receipt,
            losses_sha256=losses_sha256,
        )
        fit_receipt_sha256 = _write_once_json(fit_receipt_path, fit_receipt_payload)
        metrics_payload = _metric_payload(
            heldout,
            fold=fold,
            arm=arm,
            student_seed=student_seed,
            source_manifest_sha256=source_manifest_sha256,
            metrics_npz_name=metrics_npz_path.name,
            metrics_npz_sha256=metrics_npz_sha256,
            fit_receipt=fit_receipt_payload,
        )
        metrics_payload["fit_receipt_sidecar"] = {
            "relative_name": fit_receipt_path.name,
            "sha256": fit_receipt_sha256,
        }
        metrics_payload["arrays"] = prediction_metadata
        metrics_sha256 = _write_once_json(metrics_path, metrics_payload)

        placebo = fold.matched_placebo
        placebo_payload: dict[str, object] = {
            "schema": V023_FIT_PLACEBO_SCHEMA,
            "claim_ceiling": V023_FIT_CLAIM_CEILING,
            "held_out_world": int(fold.held_out_world),
            "arm": arm,
            "student_seed": int(student_seed),
            "source_manifest_sha256": source_manifest_sha256,
            "placebo_key": V023_PLACEBO_KEY,
            "placebo_key_sha256": V023_PLACEBO_KEY_SHA256,
            "content_digest": placebo.content_digest,
            "eligible_supported_rows": int(placebo.eligible_supported_rows),
            "total_supported_rows": int(placebo.total_supported_rows),
            "coverage": float(placebo.coverage),
            "meets_coverage_gate": bool(placebo.meets_coverage_gate),
            "training_anchor_identities": [
                {
                    "world": int(record.world_id),
                    "anchor_id": record.anchor_id,
                    "content_digest": record.content_digest,
                }
                for record in fold.training_records
            ],
            "mappings": [_serialize_mapping(mapping) for mapping in placebo.mappings],
            "target_source_sha256": fit_receipt.target_source_sha256
            if arm == "MATCHED_PLACEBO"
            else _target_source_digest(fold.training_records, targets),
            "target_array_count": len(targets),
            "target_array_shapes": [list(np.asarray(target).shape) for target in targets],
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": True,
        }
        placebo_sha256 = _write_once_json(placebo_path, placebo_payload)
        return (
            V023FitArtifacts(
                model_path=model_path,
                model_sha256=model_npz_sha256,
                network_sha256=model_logical_sha256,
                model_digest_path=model_digest_path,
                model_array_metadata=model_metadata,
                fit_receipt_path=fit_receipt_path,
                fit_receipt_sha256=fit_receipt_sha256,
                metrics_path=metrics_path,
                metrics_sha256=metrics_sha256,
                metrics_npz_path=metrics_npz_path,
                metrics_npz_sha256=metrics_npz_sha256,
                metrics_npz_digest_path=metrics_npz_digest_path,
                placebo_path=placebo_path,
                placebo_sha256=placebo_sha256,
            ),
            fit_receipt_payload,
            placebo_payload,
        )

    def fit_shard(self, spec: Any) -> Mapping[str, Any]:
        """Fit one exact shard and return a runner-sealable receipt.

        This is the only method that can invoke the injected/production fit
        function.  The runner still owns the final fit JSON seal and refuses
        to call this method unless a source manifest is present.
        """

        (
            held_out_world,
            student_seed,
            arm,
            source_directory,
            source_manifest,
            preflight,
        ) = self._check_spec(spec)
        panel = load_v023_source_panel(
            source_directory=source_directory,
            source_manifest=source_manifest,
            preflight_manifest_sha256=preflight,
        )
        if panel.preflight_manifest_sha256 != preflight:
            raise V023LearnerAdapterError("loaded panel preflight hash drifted")
        fold = prepare_lcsrs_loo_fold(
            panel.records_by_world,
            held_out_world=held_out_world,
        )
        if not fold.matched_placebo.meets_coverage_gate:
            raise V023LearnerAdapterError(
                "fold matched-placebo coverage is below the frozen 0.80 gate"
            )
        try:
            result = self.fit_function(
                fold,
                arm=arm,
                student_seed=student_seed,
                device=self.device,
            )
        except Exception as error:
            raise V023LearnerAdapterError("V0.23 fit function failed") from error
        network, fit_receipt = _fit_result(result)
        targets = _validate_fit_receipt(
            network=network,
            receipt=fit_receipt,
            fold=fold,
            arm=arm,
            student_seed=student_seed,
        )
        # ``targets`` is deliberately unused below: it was returned from the
        # validation step to make the arm-specific target binding explicit.
        del targets
        heldout = evaluate_lcsrs_heldout_rows(
            network,
            fold.held_out_records,
            device=self.device,
        )
        artifacts, fit_receipt_payload, placebo_payload = self._persist_sidecars(
            output=Path(spec.output),
            network=network,
            fit_receipt=fit_receipt,
            fold=fold,
            heldout=heldout,
            arm=arm,
            student_seed=student_seed,
            source_manifest_sha256=panel.source_manifest_sha256,
        )
        output_parent = Path(spec.output).parent
        relative = lambda path: _safe_relative_name(output_parent, path, field="fit sidecar")
        metrics_payload = _canonical_json(artifacts.metrics_path, field="fit metrics")
        # Reopen all sidecars after writing.  This catches accidental writer
        # truncation before the runner receives a PASS payload.
        if _file_sha256(artifacts.metrics_path) != artifacts.metrics_sha256:
            raise V023LearnerAdapterError("fit metrics hash changed after write")
        if _file_sha256(artifacts.metrics_npz_path) != artifacts.metrics_npz_sha256:
            raise V023LearnerAdapterError("fit metrics NPZ hash changed after write")
        if _file_sha256(artifacts.placebo_path) != artifacts.placebo_sha256:
            raise V023LearnerAdapterError("fit placebo hash changed after write")
        if _file_sha256(artifacts.fit_receipt_path) != artifacts.fit_receipt_sha256:
            raise V023LearnerAdapterError("fit receipt hash changed after write")
        _verify_digest_file(
            artifacts.model_digest_path,
            digest=_file_sha256(artifacts.model_path),
            target=artifacts.model_path,
        )
        _verify_digest_file(
            artifacts.metrics_npz_digest_path,
            digest=artifacts.metrics_npz_sha256,
            target=artifacts.metrics_npz_path,
        )
        payload: dict[str, Any] = {
            "schema": V023_FIT_SCHEMA,
            "status": "PASS",
            "claim_ceiling": V023_FIT_CLAIM_CEILING,
            "contract_sha256": V023_CONTRACT_SHA256,
            "preflight_manifest_sha256": preflight,
            "source_manifest_sha256": panel.source_manifest_sha256,
            "split": "TRAIN_DEVELOPMENT",
            "held_out_world": int(held_out_world),
            "student_seed": int(student_seed),
            "arm": arm,
            "update_count": V023_FIT_UPDATE_COUNT,
            "learner_update": True,
            "episode_training": False,
            "test_split_opened": False,
            "test_worlds": [],
            "source_panel": {
                "schema": V023_SOURCE_ARTIFACT_SCHEMA,
                "version": V023_SOURCE_ARTIFACT_VERSION,
                "worlds": list(V023_GATE_WORLDS),
                "source_manifest_sha256": panel.source_manifest_sha256,
                "source_manifest_path": _safe_relative_name(
                    source_directory,
                    panel.source_manifest_path,
                    field="source manifest",
                ),
                "source_pair_count": int(panel.source_pair_count),
                "source_anchor_count": int(panel.source_anchor_count),
                "source_index_sha256s": {
                    str(artifact.world): artifact.index_sha256
                    for artifact in panel.artifacts
                },
            },
            "fold": {
                "held_out_world": int(fold.held_out_world),
                "training_worlds": sorted(
                    {int(record.world_id) for record in fold.training_records}
                ),
                "training_anchor_count": len(fold.training_records),
                "heldout_anchor_count": len(fold.held_out_records),
                "training_anchor_sha256s": [
                    record.content_digest for record in fold.training_records
                ],
                "heldout_anchor_sha256s": [
                    record.content_digest for record in fold.held_out_records
                ],
                "heldout_anchor_ids": [
                    record.anchor_id for record in fold.held_out_records
                ],
                "heldout_is_untouched": True,
            },
            "placebo": {
                **placebo_payload,
                "path": relative(artifacts.placebo_path),
                "sha256": artifacts.placebo_sha256,
            },
            "fit_receipt": {
                **fit_receipt_payload,
                "path": relative(artifacts.fit_receipt_path),
                "sha256": artifacts.fit_receipt_sha256,
            },
            "model_state": {
                "schema": V023_FIT_MODEL_SCHEMA,
                "path": relative(artifacts.model_path),
                "npz_sha256": _file_sha256(artifacts.model_path),
                "npz_sha256_file": relative(artifacts.model_digest_path),
                "logical_network_sha256": artifacts.network_sha256,
                "array_domain": V023_FIT_MODEL_ARRAY_DOMAIN,
                "arrays": artifacts.model_array_metadata,
                "no_pickle": True,
            },
            "model_sha256": artifacts.model_sha256,
            "network_sha256": artifacts.network_sha256,
            "metrics": {
                "schema": V023_FIT_METRICS_SCHEMA,
                "path": relative(artifacts.metrics_path),
                "sha256": artifacts.metrics_sha256,
                "npz_path": relative(artifacts.metrics_npz_path),
                "npz_sha256": artifacts.metrics_npz_sha256,
                "npz_sha256_file": relative(artifacts.metrics_npz_digest_path),
                "content_digest": metrics_payload.get(
                    "heldout_prediction_content_digest"
                ),
                "spearman": metrics_payload.get("spearman"),
                "sign": metrics_payload.get("sign"),
                "denominators": metrics_payload.get("denominators"),
                "heldout_supported_rows": metrics_payload.get(
                    "heldout_supported_rows"
                ),
                "identities": metrics_payload.get("identities"),
            },
            "metrics_sha256": artifacts.metrics_sha256,
            "denominators": metrics_payload.get("denominators"),
            "no_rescue": {
                "early_stopping": False,
                "best_checkpoint_selection": False,
                "outcome_weighting": False,
                "heldout_target_permutation": False,
            },
            # The runner owns receipt_sha256.  Deliberately do not return it.
        }
        return _jsonable(payload)  # type: ignore[return-value]


def verify_v023_fit_sidecars(receipt_path: Path) -> dict[str, object]:
    """Reopen one runner-sealed fit receipt and verify every sidecar binding.

    This check is intentionally independent of the in-memory network returned
    by :class:`V023LearnerAdapter`.  It is suitable for the later scientific
    verifier and detects model/metrics/placebo/fit-receipt tampering before any
    composition predicate is evaluated.  It computes no EE decision.
    """

    receipt_file = Path(receipt_path)
    if receipt_file.is_symlink() or not receipt_file.is_file():
        raise V023LearnerAdapterError("fit receipt is missing or is a symlink")
    payload = _canonical_json(receipt_file, field="fit receipt")
    _verify_receipt_seal(payload)
    if payload.get("schema") != V023_FIT_SCHEMA:
        raise V023LearnerAdapterError("fit receipt schema drifted")
    if payload.get("claim_ceiling") != V023_FIT_CLAIM_CEILING:
        raise V023LearnerAdapterError("fit receipt claim ceiling drifted")
    if payload.get("split") != "TRAIN_DEVELOPMENT":
        raise V023LearnerAdapterError("fit receipt is not TRAIN_DEVELOPMENT")
    if (
        payload.get("test_split_opened") is not False
        or payload.get("episode_training") is not False
        or payload.get("test_worlds") != []
    ):
        raise V023LearnerAdapterError("fit receipt crossed a closed boundary")
    root = receipt_file.parent.resolve()
    model_state = payload.get("model_state")
    metrics = payload.get("metrics")
    placebo = payload.get("placebo")
    fit_receipt = payload.get("fit_receipt")
    for value, field in (
        (model_state, "model_state"),
        (metrics, "metrics"),
        (placebo, "placebo"),
        (fit_receipt, "fit_receipt"),
    ):
        if not isinstance(value, Mapping):
            raise V023LearnerAdapterError(f"fit receipt {field} object is missing")
    model_path = _safe_child(root, model_state["path"], field="model sidecar")
    model_digest_path = _safe_child(
        root,
        model_state["npz_sha256_file"],
        field="model digest sidecar",
    )
    metrics_path = _safe_child(root, metrics["path"], field="metrics JSON")
    metrics_npz_path = _safe_child(root, metrics["npz_path"], field="metrics NPZ")
    metrics_digest_path = _safe_child(
        root,
        metrics["npz_sha256_file"],
        field="metrics digest sidecar",
    )
    placebo_path = _safe_child(root, placebo["path"], field="placebo sidecar")
    fit_receipt_sidecar_path = _safe_child(
        root,
        fit_receipt["path"],
        field="fit receipt sidecar",
    )
    model_bytes_sha = _file_sha256(model_path)
    metrics_bytes_sha = _file_sha256(metrics_path)
    metrics_npz_sha = _file_sha256(metrics_npz_path)
    placebo_bytes_sha = _file_sha256(placebo_path)
    fit_receipt_bytes_sha = _file_sha256(fit_receipt_sidecar_path)
    if model_bytes_sha != payload.get("model_sha256"):
        raise V023LearnerAdapterError("model byte hash disagrees with receipt")
    if metrics_bytes_sha != payload.get("metrics_sha256"):
        raise V023LearnerAdapterError("metrics byte hash disagrees with receipt")
    if metrics_bytes_sha != metrics.get("sha256"):
        raise V023LearnerAdapterError("metrics nested hash disagrees")
    if model_bytes_sha != model_state.get("npz_sha256"):
        raise V023LearnerAdapterError("model state NPZ hash disagrees")
    if metrics_npz_sha != metrics.get("npz_sha256"):
        raise V023LearnerAdapterError("metrics NPZ hash disagrees")
    if placebo_bytes_sha != placebo.get("sha256"):
        raise V023LearnerAdapterError("placebo hash disagrees")
    if fit_receipt_bytes_sha != fit_receipt.get("sha256"):
        raise V023LearnerAdapterError("fit receipt sidecar hash disagrees")
    _verify_digest_file(model_digest_path, digest=model_bytes_sha, target=model_path)
    _verify_digest_file(
        metrics_digest_path,
        digest=metrics_npz_sha,
        target=metrics_npz_path,
    )

    model_metadata = model_state.get("arrays")
    if not isinstance(model_metadata, Mapping):
        raise V023LearnerAdapterError("model tensor metadata is missing")
    try:
        with np.load(model_path, allow_pickle=False) as archive:
            model_arrays = {
                name: np.array(archive[name], copy=True) for name in archive.files
            }
    except (OSError, ValueError, KeyError) as error:
        raise V023LearnerAdapterError("model NPZ cannot be loaded safely") from error
    if any(array.dtype == object for array in model_arrays.values()):
        raise V023LearnerAdapterError("model NPZ contains object dtype")
    expected_model_keys = {
        entry.get("npz_key") for entry in model_metadata.values()
        if isinstance(entry, Mapping)
    }
    if expected_model_keys != set(model_arrays):
        raise V023LearnerAdapterError("model tensor keys disagree with metadata")
    for name, entry in model_metadata.items():
        if not isinstance(name, str) or not isinstance(entry, Mapping):
            raise V023LearnerAdapterError("model tensor metadata is malformed")
        key = entry.get("npz_key")
        if not isinstance(key, str) or key not in model_arrays:
            raise V023LearnerAdapterError("model tensor NPZ key is missing")
        array = model_arrays[key]
        if entry.get("dtype") != array.dtype.str or entry.get("shape") != list(array.shape):
            raise V023LearnerAdapterError("model tensor shape/dtype disagrees")
        if entry.get("sha256") != _array_digest(
            array,
            domain=V023_FIT_MODEL_ARRAY_DOMAIN,
        ):
            raise V023LearnerAdapterError("model tensor digest disagrees")
    network = LCSRSC3QNetwork()
    state = network.state_dict()
    if set(state) != set(model_metadata):
        raise V023LearnerAdapterError("model parameter names disagree with head")
    for name, entry in model_metadata.items():
        array = model_arrays[str(entry["npz_key"])]
        tensor = torch.from_numpy(np.array(array, copy=True)).to(dtype=state[name].dtype)
        if tuple(tensor.shape) != tuple(state[name].shape):
            raise V023LearnerAdapterError("model parameter shape disagrees with head")
        state[name] = tensor
    network.load_state_dict(state, strict=True)
    logical = lcsrs_c3_network_sha256(network)
    if logical != model_state.get("logical_network_sha256"):
        raise V023LearnerAdapterError("logical model digest disagrees")
    if logical != payload.get("network_sha256"):
        raise V023LearnerAdapterError("network digest disagrees with fit receipt")

    metrics_payload = _canonical_json(metrics_path, field="fit metrics")
    if metrics_payload.get("schema") != V023_FIT_METRICS_SCHEMA:
        raise V023LearnerAdapterError("fit metrics schema drifted")
    if metrics_payload.get("source_manifest_sha256") != payload.get(
        "source_manifest_sha256"
    ):
        raise V023LearnerAdapterError("fit metrics source manifest drifted")
    sidecar_binding = metrics_payload.get("sidecar")
    if not isinstance(sidecar_binding, Mapping) or sidecar_binding.get(
        "npz_sha256"
    ) != metrics_npz_sha:
        raise V023LearnerAdapterError("fit metrics NPZ binding drifted")
    metric_arrays_metadata = metrics_payload.get("arrays")
    if not isinstance(metric_arrays_metadata, Mapping):
        raise V023LearnerAdapterError("fit metric array metadata is missing")
    try:
        with np.load(metrics_npz_path, allow_pickle=False) as archive:
            arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    except (OSError, ValueError, KeyError) as error:
        raise V023LearnerAdapterError("fit metrics NPZ cannot be loaded safely") from error
    if set(arrays) != set(metric_arrays_metadata) or any(
        array.dtype == object for array in arrays.values()
    ):
        raise V023LearnerAdapterError("fit metric arrays disagree or contain object dtype")
    for name, entry in metric_arrays_metadata.items():
        if not isinstance(entry, Mapping):
            raise V023LearnerAdapterError("fit metric array metadata is malformed")
        array = arrays[name]
        if entry.get("dtype") != array.dtype.str or entry.get("shape") != list(array.shape):
            raise V023LearnerAdapterError("fit metric array shape/dtype disagrees")
        if entry.get("sha256") != _array_digest(
            array,
            domain=V023_FIT_PREDICTION_ARRAY_DOMAIN,
        ):
            raise V023LearnerAdapterError("fit metric array digest disagrees")
    losses = np.asarray(arrays.get("loss"), dtype=np.float64)
    if losses.shape != (V023_FIT_UPDATE_COUNT,):
        raise V023LearnerAdapterError("fit metric loss array has wrong update count")
    receipt_sidecar = _canonical_json(
        fit_receipt_sidecar_path,
        field="fit receipt sidecar",
    )
    fit_receipt_body = dict(fit_receipt)
    fit_receipt_body.pop("path", None)
    fit_receipt_body.pop("sha256", None)
    if receipt_sidecar != fit_receipt_body:
        raise V023LearnerAdapterError("fit receipt sidecar disagrees")
    receipt_losses = np.asarray(fit_receipt.get("losses"), dtype=np.float64)
    if receipt_losses.shape != losses.shape or not np.array_equal(receipt_losses, losses):
        raise V023LearnerAdapterError("fit receipt losses disagree with metrics NPZ")
    placebo_payload = _canonical_json(placebo_path, field="placebo sidecar")
    placebo_body = dict(placebo)
    placebo_body.pop("path", None)
    placebo_body.pop("sha256", None)
    if placebo_payload != placebo_body:
        raise V023LearnerAdapterError("placebo sidecar disagrees")
    return {
        "status": "PASS_FIT_SIDECARS",
        "scientific_claim": False,
        "held_out_world": payload.get("held_out_world"),
        "student_seed": payload.get("student_seed"),
        "arm": payload.get("arm"),
        "heldout_rows": metrics_payload.get("heldout_supported_rows"),
    }


# Discoverable aliases for the explicit server launcher.
LearnerAdapter = V023LearnerAdapter


__all__ = [
    "V023_GATE_SCHEMA",
    "V023_FIT_SCHEMA",
    "V023_FIT_ARTIFACT_SCHEMA",
    "V023_FIT_METRICS_SCHEMA",
    "V023_FIT_MODEL_SCHEMA",
    "V023_FIT_PLACEBO_SCHEMA",
    "V023_FIT_UPDATE_COUNT",
    "V023LearnerAdapterError",
    "FitFunction",
    "V023SourcePanel",
    "V023FitArtifacts",
    "load_v023_source_panel",
    "V023LearnerAdapter",
    "LearnerAdapter",
    "verify_v023_fit_sidecars",
    "canonical_sha256",
]
