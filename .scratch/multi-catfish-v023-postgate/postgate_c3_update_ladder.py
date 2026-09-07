"""Post-Gate V0.23 C3 source-update checkpoint plumbing.

This is an offline learner-update seam.  It deliberately starts *after* the
existing V0.23 source/learner Gate and does not alter that Gate, its frozen
2,000-update fit, or any deployment/evaluation path.  A caller must provide an
already authenticated source through :class:`AuthenticatedV023SourceProvider`.
There is no built-in source constructor, neutral-data generator, physical
environment, TEST split, evaluation, or checkpoint-selection policy here.

The production ladder is one fixed axis of learner updates
``0, 100, ..., 2000`` for the three frozen student seeds.  Every checkpoint
contains the model/optimizer/sampler/torch-RNG state needed for an exact
resume and a JSON receipt binding all state to the authenticated source
manifest and frozen learner configuration.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import io
import json
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
from typing import Protocol, runtime_checkable

import numpy as np
import torch

from mcrl.runtime.ee_axis_lcsrs_c3_dataset import LCSRSAnchorSurface
from mcrl.runtime.ee_axis_lcsrs_c3_learner import (
    LCSRS_C3_BATCH_SIZE,
    LCSRS_C3_LEARNER_CONFIG,
    LCSRS_C3_LEARNER_CONFIG_SHA256,
    LCSRS_C3_UPDATE_COUNT,
    LCSRSC3ClassBalancedSampler,
    LCSRSC3LearnerError,
    LCSRSC3QNetwork,
    lcsrs_c3_network_sha256,
    lcsrs_c3_training_step,
    make_lcsrs_c3_student,
)
from mcrl.runtime.ee_axis_lcsrs_c3_source_artifact import (
    V023_SOURCE_ARTIFACT_SCHEMA,
)


POSTGATE_C3_SCHEMA = "multi-catfish-mcrl-v023-c3-postgate-update-ladder-v1"
POSTGATE_C3_STATE_SCHEMA = (
    "multi-catfish-mcrl-v023-c3-postgate-update-ladder-state-v1"
)
POSTGATE_C3_CHECKPOINT_SCHEMA = (
    "multi-catfish-mcrl-v023-c3-postgate-update-ladder-checkpoint-v1"
)
POSTGATE_C3_CLAIM_CEILING = (
    "TRAIN_SOURCE_UPDATES_ONLY_NO_TEST_NO_PHYSICAL_EPISODES_NO_EVALUATION_NO_DEPLOYMENT"
)

# These values are aliases to the already frozen V0.23 learner contract.  Do
# not edit them here to make a faster test or a different experimental arm.
POSTGATE_C3_UPDATE_COUNT = LCSRS_C3_UPDATE_COUNT
POSTGATE_C3_BATCH_SIZE = LCSRS_C3_BATCH_SIZE
POSTGATE_C3_UPDATE_AXIS: tuple[int, ...] = tuple(
    range(0, POSTGATE_C3_UPDATE_COUNT + 1, 100)
)
POSTGATE_C3_STUDENT_SEEDS: tuple[int, ...] = (
    2026135101,
    2026135102,
    2026135103,
)
POSTGATE_C3_SOURCE_ARMS: tuple[str, ...] = ("INFORMED", "NEUTRAL_SOURCE")
POSTGATE_C3_SOURCE_ARTIFACT_SCHEMA = V023_SOURCE_ARTIFACT_SCHEMA
POSTGATE_C3_CHECKPOINT_KIND = "LEARNER_UPDATE"
POSTGATE_C3_STATE_SUFFIX = ".state.pt"
POSTGATE_C3_RECEIPT_SUFFIX = ".json"

# Friendly aliases make the contract easy to discover without creating a
# second source of truth.
UPDATE_AXIS = POSTGATE_C3_UPDATE_AXIS
SOURCE_UPDATE_AXIS = POSTGATE_C3_UPDATE_AXIS
CHECKPOINT_AXIS = POSTGATE_C3_UPDATE_AXIS
CHECKPOINT_UPDATES = POSTGATE_C3_UPDATE_AXIS
STUDENT_SEEDS = POSTGATE_C3_STUDENT_SEEDS
V023_STUDENT_SEEDS = POSTGATE_C3_STUDENT_SEEDS
SOURCE_ARMS = POSTGATE_C3_SOURCE_ARMS


class PostGateC3UpdateLadderError(RuntimeError):
    """A post-Gate source/update/checkpoint boundary was violated."""


def _jsonable(value: object) -> object:
    """Convert receipt values to strict canonical-JSON-compatible values."""

    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                # State digests preserve non-string mapping keys separately;
                # receipts themselves intentionally use string keys only.
                raise TypeError("canonical receipt mapping keys must be strings")
            result[key] = _jsonable(item)
        return result
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, Path):
        return value.as_posix()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical receipt JSON does not admit non-finite floats")
        return value
    raise TypeError(f"unsupported canonical receipt value: {type(value).__name__}")


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
        raise PostGateC3UpdateLadderError(
            "value is not canonical finite ASCII JSON"
        ) from error


def canonical_sha256(value: object) -> str:
    """Hash one canonical receipt-compatible value."""

    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PostGateC3UpdateLadderError(f"{field} is not a lowercase SHA-256")
    return value


def _optional_digest(value: object, *, field: str) -> str | None:
    """Validate a digest when a receipt carries an external file binding."""

    if value is None:
        return None
    return _digest(value, field=field)


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise PostGateC3UpdateLadderError(
            f"{field} must be a nonnegative integer"
        )
    return value


def _state_bytes(value: object) -> bytes:
    """Encode nested tensor/NumPy/Python state with explicit type framing.

    The framing is deliberately independent of pickle and of dictionary
    insertion order.  It is used for receipt hashes, while the adjacent
    ``.pt`` sidecar carries the actual state needed to resume.
    """

    def frame(tag: bytes, payload: bytes) -> bytes:
        return tag + struct.pack(">Q", len(payload)) + payload

    def encode(item: object) -> bytes:
        if isinstance(item, torch.Tensor):
            tensor = item.detach().cpu().contiguous()
            array = np.ascontiguousarray(tensor.numpy())
            payload = (
                frame(b"d", array.dtype.str.encode("ascii"))
                + frame(b"s", repr(tuple(array.shape)).encode("ascii"))
                + frame(b"v", array.tobytes(order="C"))
            )
            return frame(b"T", payload)
        if isinstance(item, np.ndarray):
            array = np.ascontiguousarray(item)
            if array.dtype == object:
                raise PostGateC3UpdateLadderError(
                    "object dtype is forbidden in learner state"
                )
            payload = (
                frame(b"d", array.dtype.str.encode("ascii"))
                + frame(b"s", repr(tuple(array.shape)).encode("ascii"))
                + frame(b"v", array.tobytes(order="C"))
            )
            return frame(b"A", payload)
        if isinstance(item, np.generic):
            return frame(b"N", encode(item.item()))
        if isinstance(item, Mapping):
            entries: list[bytes] = []
            for key, child in item.items():
                key_bytes = encode(key)
                entries.append(frame(b"k", key_bytes) + frame(b"v", encode(child)))
            entries.sort()
            return frame(b"M", b"".join(entries))
        if isinstance(item, tuple):
            return frame(b"t", b"".join(frame(b"i", encode(child)) for child in item))
        if isinstance(item, list):
            return frame(b"l", b"".join(frame(b"i", encode(child)) for child in item))
        if item is None:
            return frame(b"0", b"")
        if isinstance(item, bool):
            return frame(b"b", b"1" if item else b"0")
        if isinstance(item, int):
            return frame(b"i", str(item).encode("ascii"))
        if isinstance(item, float):
            if not math.isfinite(item):
                raise PostGateC3UpdateLadderError(
                    "non-finite float is forbidden in learner state"
                )
            return frame(b"f", struct.pack(">d", item))
        if isinstance(item, str):
            return frame(b"S", item.encode("utf-8"))
        raise PostGateC3UpdateLadderError(
            f"unsupported learner-state value: {type(item).__name__}"
        )

    return encode(value)


def state_sha256(value: object) -> str:
    """Hash optimizer, RNG, or nested learner state deterministically."""

    return hashlib.sha256(b"postgate-c3-state-v1" + _state_bytes(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise PostGateC3UpdateLadderError(f"expected a regular file: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def learner_config_payload() -> dict[str, object]:
    """Return the exact inherited learner configuration for a receipt."""

    return dict(asdict(LCSRS_C3_LEARNER_CONFIG))


def learner_config_sha256() -> str:
    """Return the inherited learner configuration digest."""

    return canonical_sha256(learner_config_payload())


def _target_source_sha256(
    source: Sequence[LCSRSAnchorSurface],
    targets: Sequence[np.ndarray],
) -> str:
    if len(source) != len(targets):
        raise PostGateC3UpdateLadderError("source/target anchor counts disagree")
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-fitting-source-v1")
    for surface, target in zip(source, targets, strict=True):
        digest.update(surface.content_digest.encode("ascii"))
        array = np.ascontiguousarray(np.asarray(target, dtype=np.float32))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _verify_surface(surface: LCSRSAnchorSurface, *, index: int) -> None:
    """Re-run the typed source-surface constructor to detect alias tampering."""

    try:
        LCSRSAnchorSurface(
            view=surface.view,
            normalized_targets=surface.normalized_targets,
            row_class=surface.row_class,
            pairs=surface.pairs,
            content_digest=surface.content_digest,
        )
    except Exception as error:
        raise PostGateC3UpdateLadderError(
            f"source anchor {index} is not authenticated"
        ) from error


def _readonly_target(value: object, *, expected: tuple[int, int]) -> np.ndarray:
    try:
        array = np.array(value, dtype=np.float32, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise PostGateC3UpdateLadderError(
            "neutral source target array is malformed"
        ) from error
    if array.shape != expected or not np.all(np.isfinite(array)):
        raise PostGateC3UpdateLadderError(
            "neutral source target array has the wrong shape or values"
        )
    array.setflags(write=False)
    return array


def _source_attestation_sha256(
    *,
    arm: str,
    source_manifest_sha256: str,
    source_manifest_file_sha256: str | None = None,
    result_sha256: str | None = None,
    result_manifest_sha256: str | None = None,
    provider_id: str,
    surface_sha256s: Sequence[str],
    target_source_sha256: str,
    source_row_count: int | None = None,
    update_budget: int = POSTGATE_C3_UPDATE_COUNT,
) -> str:
    return canonical_sha256(
        {
            "schema": "multi-catfish-mcrl-v023-authenticated-source-v1",
            "arm": arm,
            "source_manifest_sha256": source_manifest_sha256,
            "source_manifest_file_sha256": source_manifest_file_sha256,
            "result_sha256": result_sha256,
            "result_manifest_sha256": result_manifest_sha256,
            "provider_id": provider_id,
            "surface_sha256s": list(surface_sha256s),
            "target_source_sha256": target_source_sha256,
            "source_row_count": source_row_count,
            "update_budget": update_budget,
        }
    )


@dataclass(frozen=True)
class AuthenticatedV023Source:
    """External source payload admitted to the post-Gate learner seam.

    ``NEUTRAL_SOURCE`` deliberately has no implementation in this area.  The
    caller must bring an authenticated, equal-budget target source and bind it
    to the same frozen learner configuration.  For convenience, an omitted
    provider attestation is replaced by the deterministic content attestation;
    a real external provider should persist and return that value explicitly.
    """

    arm: str
    source_manifest_sha256: str
    surfaces: tuple[LCSRSAnchorSurface, ...]
    normalized_targets_by_anchor: tuple[np.ndarray, ...] | None = None
    provider_id: str = "external-authenticated-v023-source-provider-v1"
    provider_receipt_sha256: str | None = None
    source_manifest_file_sha256: str | None = None
    result_sha256: str | None = None
    result_manifest_sha256: str | None = None
    update_budget: int = POSTGATE_C3_UPDATE_COUNT
    source_artifact_schema: str = POSTGATE_C3_SOURCE_ARTIFACT_SCHEMA
    split: str = "TRAIN_DEVELOPMENT"
    test_split_opened: bool = False
    episode_training: bool = False

    def __post_init__(self) -> None:
        if self.arm not in POSTGATE_C3_SOURCE_ARMS:
            raise PostGateC3UpdateLadderError(
                "source arm must be INFORMED or NEUTRAL_SOURCE"
            )
        _digest(self.source_manifest_sha256, field="source_manifest_sha256")
        for field, value in (
            ("source_manifest_file_sha256", self.source_manifest_file_sha256),
            ("result_sha256", self.result_sha256),
            ("result_manifest_sha256", self.result_manifest_sha256),
        ):
            if value is not None:
                _digest(value, field=field)
        if type(self.update_budget) is not int or self.update_budget != POSTGATE_C3_UPDATE_COUNT:
            raise PostGateC3UpdateLadderError(
                "source update budget must remain the frozen 2,000 updates"
            )
        if not isinstance(self.provider_id, str) or not self.provider_id.strip():
            raise PostGateC3UpdateLadderError("provider_id must be nonempty")
        if self.split != "TRAIN_DEVELOPMENT":
            raise PostGateC3UpdateLadderError("post-Gate source must be TRAIN_DEVELOPMENT")
        if self.source_artifact_schema != POSTGATE_C3_SOURCE_ARTIFACT_SCHEMA:
            raise PostGateC3UpdateLadderError("source artifact schema drifted")
        if self.test_split_opened or self.episode_training:
            raise PostGateC3UpdateLadderError(
                "source provider crossed a closed split or episode boundary"
            )
        surfaces = tuple(self.surfaces)
        if not surfaces:
            raise PostGateC3UpdateLadderError("source provider returned no anchors")
        for index, surface in enumerate(surfaces):
            if not isinstance(surface, LCSRSAnchorSurface):
                raise PostGateC3UpdateLadderError(
                    f"source anchor {index} is not an LCSRSAnchorSurface"
                )
            _verify_surface(surface, index=index)
        object.__setattr__(self, "surfaces", surfaces)
        expected_shape = tuple(surfaces[0].normalized_targets.shape)
        if any(tuple(surface.normalized_targets.shape) != expected_shape for surface in surfaces):
            raise PostGateC3UpdateLadderError(
                "source anchors do not share a target surface shape"
            )
        for index, surface in enumerate(surfaces):
            if (
                tuple(surface.view.action_mask.shape) != expected_shape
                or tuple(surface.row_class.shape) != expected_shape
            ):
                raise PostGateC3UpdateLadderError(
                    f"source anchor {index} target/mask shapes disagree"
                )
        if self.arm == "INFORMED":
            if self.normalized_targets_by_anchor is not None:
                raise PostGateC3UpdateLadderError(
                    "INFORMED source must use authenticated surface targets"
                )
            targets = tuple(surface.normalized_targets for surface in surfaces)
        else:
            if self.normalized_targets_by_anchor is None:
                raise PostGateC3UpdateLadderError(
                    "NEUTRAL_SOURCE requires an external target source"
                )
            raw_targets = tuple(self.normalized_targets_by_anchor)
            if len(raw_targets) != len(surfaces):
                raise PostGateC3UpdateLadderError(
                    "neutral source target count disagrees with anchors"
                )
            targets = tuple(
                _readonly_target(value, expected=expected_shape)
                for value in raw_targets
            )
            for surface, target in zip(surfaces, targets, strict=True):
                if np.any(target[surface.row_class != 3] != 0.0):
                    raise PostGateC3UpdateLadderError(
                        "neutral source may be nonzero only on SUPPORTED cells"
                    )
        target_digest = _target_source_sha256(surfaces, targets)
        source_row_count = sum(
            int(np.count_nonzero(surface.row_class == 3)) for surface in surfaces
        )
        if source_row_count <= 0:
            raise PostGateC3UpdateLadderError("source provider returned no SUPPORTED rows")
        attestation = _source_attestation_sha256(
            arm=self.arm,
            source_manifest_sha256=self.source_manifest_sha256,
            source_manifest_file_sha256=self.source_manifest_file_sha256,
            result_sha256=self.result_sha256,
            result_manifest_sha256=self.result_manifest_sha256,
            provider_id=self.provider_id,
            surface_sha256s=tuple(surface.content_digest for surface in surfaces),
            target_source_sha256=target_digest,
            source_row_count=source_row_count,
            update_budget=self.update_budget,
        )
        declared = self.provider_receipt_sha256
        if declared is None:
            object.__setattr__(self, "provider_receipt_sha256", attestation)
        elif _digest(declared, field="provider_receipt_sha256") != attestation:
            raise PostGateC3UpdateLadderError(
                "source provider attestation disagrees with source contents"
            )
        object.__setattr__(self, "normalized_targets_by_anchor", targets if self.arm == "NEUTRAL_SOURCE" else None)

    @property
    def source_anchor_sha256s(self) -> tuple[str, ...]:
        return tuple(surface.content_digest for surface in self.surfaces)

    @property
    def targets(self) -> tuple[np.ndarray, ...]:
        if self.arm == "INFORMED":
            return tuple(surface.normalized_targets for surface in self.surfaces)
        assert self.normalized_targets_by_anchor is not None
        return self.normalized_targets_by_anchor

    @property
    def target_source_sha256(self) -> str:
        return _target_source_sha256(self.surfaces, self.targets)

    @property
    def source_row_count(self) -> int:
        """Number of SUPPORTED learner rows in this immutable source."""

        return sum(int(np.count_nonzero(surface.row_class == 3)) for surface in self.surfaces)

    @property
    def manifest_sha256(self) -> str | None:
        """Alias for the sealed result directory manifest digest."""

        return self.result_manifest_sha256

    @property
    def result_receipt_sha256(self) -> str | None:
        """Alias for the sealed ``result.json`` byte digest."""

        return self.result_sha256

    def verify(self) -> str:
        """Re-authenticate the complete source bundle and return its attestation."""

        # Re-run the constructor-level checks on every call.  ``dataclass``
        # freezing prevents normal field reassignment, but callers can still
        # mutate an object returned by a hostile provider via aliases.
        for index, surface in enumerate(self.surfaces):
            _verify_surface(surface, index=index)
        expected = _source_attestation_sha256(
            arm=self.arm,
            source_manifest_sha256=self.source_manifest_sha256,
            source_manifest_file_sha256=self.source_manifest_file_sha256,
            result_sha256=self.result_sha256,
            result_manifest_sha256=self.result_manifest_sha256,
            provider_id=self.provider_id,
            surface_sha256s=self.source_anchor_sha256s,
            target_source_sha256=self.target_source_sha256,
            source_row_count=self.source_row_count,
            update_budget=self.update_budget,
        )
        if self.provider_receipt_sha256 != expected:
            raise PostGateC3UpdateLadderError("source provider attestation drifted")
        return expected


@runtime_checkable
class AuthenticatedV023SourceProvider(Protocol):
    """External authenticated source seam; it receives no outcomes/metrics."""

    def provide(
        self, *, arm: str, student_seed: int
    ) -> AuthenticatedV023Source: ...


V023SourceProvider = AuthenticatedV023SourceProvider


def _provider_source(
    provider: object,
    *,
    arm: str,
    student_seed: int,
) -> AuthenticatedV023Source:
    if provider is None:
        raise PostGateC3UpdateLadderError(
            "an external authenticated source provider is required"
        )
    method = getattr(provider, "provide", None)
    if method is None:
        # Compatibility spellings are accepted for an external adapter; all
        # signatures remain outcome-free and keyword-bound.
        for name in ("load", "resolve", "get_source"):
            candidate = getattr(provider, name, None)
            if candidate is not None:
                method = candidate
                break
    if not callable(method):
        raise PostGateC3UpdateLadderError(
            "source provider must expose provide(arm=, student_seed=)"
        )
    try:
        source = method(arm=arm, student_seed=student_seed)
    except Exception as error:
        raise PostGateC3UpdateLadderError("authenticated source provider failed") from error
    if not isinstance(source, AuthenticatedV023Source) and not _is_owned_source_type(source):
        raise PostGateC3UpdateLadderError(
            "source provider returned an unauthenticated source payload"
        )
    if source.arm != arm:
        raise PostGateC3UpdateLadderError("source provider arm disagrees with request")
    try:
        source.verify()
    except PostGateC3UpdateLadderError:
        raise
    except Exception as error:
        raise PostGateC3UpdateLadderError("source provider verification failed") from error
    return source


def _is_owned_source_type(source: object) -> bool:
    """Accept the same source class loaded under another scratch-module name.

    Scratch adapters are commonly loaded with ``importlib`` under a test or
    worker-specific module name.  Identity-based ``isinstance`` would then
    reject a source whose implementation is still this exact file.  Require
    the class name and resolved source file before using the normal ``verify``
    checks; unrelated duck-typed objects remain unauthenticated.
    """

    source_type = type(source)
    if source_type.__name__ != "AuthenticatedV023Source":
        return False
    module = sys.modules.get(source_type.__module__)
    module_path = getattr(module, "__file__", None)
    if module_path is None:
        return False
    try:
        return Path(module_path).resolve() == Path(__file__).resolve()
    except OSError:
        return False


def authenticated_source_from_v023_panel(
    panel: object,
    *,
    arm: str,
    normalized_targets_by_anchor: Sequence[np.ndarray] | None = None,
    provider_id: str = "external-authenticated-v023-source-provider-v1",
    provider_receipt_sha256: str | None = None,
) -> AuthenticatedV023Source:
    """Adapt an already loaded V0.23 source panel into this update seam.

    The panel must come from the existing V0.23 fit/source-artifact loader;
    this helper does not open files, construct records, or synthesize neutral
    targets.  It merely flattens the panel's authenticated retained surfaces
    in artifact/record order and carries the panel's source-manifest digest.
    """

    manifest_digest = getattr(panel, "source_manifest_sha256", None)
    artifacts = getattr(panel, "artifacts", None)
    if manifest_digest is None or artifacts is None:
        raise PostGateC3UpdateLadderError(
            "panel must expose source_manifest_sha256 and artifacts"
        )
    try:
        artifact_tuple = tuple(artifacts)
    except TypeError as error:
        raise PostGateC3UpdateLadderError("source panel artifacts are not a sequence") from error
    surfaces: list[LCSRSAnchorSurface] = []
    for artifact_index, artifact in enumerate(artifact_tuple):
        records = getattr(artifact, "records", None)
        if records is None:
            raise PostGateC3UpdateLadderError(
                f"source panel artifact {artifact_index} has no records"
            )
        try:
            record_tuple = tuple(records)
        except TypeError as error:
            raise PostGateC3UpdateLadderError(
                f"source panel artifact {artifact_index} records are not a sequence"
            ) from error
        for record_index, record in enumerate(record_tuple):
            surface = getattr(record, "surface", None)
            if not isinstance(surface, LCSRSAnchorSurface):
                raise PostGateC3UpdateLadderError(
                    f"source panel record {artifact_index}/{record_index} has no typed surface"
                )
            surfaces.append(surface)
    return AuthenticatedV023Source(
        arm=arm,
        source_manifest_sha256=str(manifest_digest),
        surfaces=tuple(surfaces),
        normalized_targets_by_anchor=normalized_targets_by_anchor,
        provider_id=provider_id,
        provider_receipt_sha256=provider_receipt_sha256,
    )


# Alternate spelling for callers that treat the panel conversion as a bind.
bind_v023_source_panel = authenticated_source_from_v023_panel


def _sampler_for_source(
    source: AuthenticatedV023Source,
    *,
    student_seed: int,
) -> LCSRSC3ClassBalancedSampler:
    try:
        return LCSRSC3ClassBalancedSampler(
            source.surfaces,
            student_seed=student_seed,
            normalized_targets_by_anchor=(
                None
                if source.arm == "INFORMED"
                else source.normalized_targets_by_anchor
            ),
        )
    except (LCSRSC3LearnerError, TypeError, ValueError) as error:
        raise PostGateC3UpdateLadderError(
            "authenticated source cannot enter the frozen learner sampler"
        ) from error


def _torch_state_bytes(payload: Mapping[str, object]) -> bytes:
    stream = io.BytesIO()
    try:
        torch.save(dict(payload), stream)
    except Exception as error:
        raise PostGateC3UpdateLadderError("learner state serialization failed") from error
    return stream.getvalue()


def _write_once(path: Path, payload: bytes) -> str:
    """Publish one fsynced file without an overwrite race."""

    target = Path(path)
    if target.exists() or target.is_symlink():
        raise PostGateC3UpdateLadderError(f"refusing to overwrite artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError as error:
            raise PostGateC3UpdateLadderError(
                f"refusing to overwrite artifact: {target}"
            ) from error
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(payload).hexdigest()


def _write_once_json(path: Path, payload: Mapping[str, object]) -> str:
    return _write_once(path, _canonical_bytes(payload))


def _checkpoint_names(update_count: int) -> tuple[str, str]:
    return (
        f"checkpoint-{update_count:06d}{POSTGATE_C3_STATE_SUFFIX}",
        f"checkpoint-{update_count:06d}{POSTGATE_C3_RECEIPT_SUFFIX}",
    )


def _checkpoint_state_payload(
    *,
    arm: str,
    student_seed: int,
    source: AuthenticatedV023Source,
    initial_network_sha256: str,
    update_count: int,
    network: LCSRSC3QNetwork,
    optimizer: torch.optim.Optimizer,
    sampler: LCSRSC3ClassBalancedSampler,
) -> tuple[dict[str, object], dict[str, str]]:
    network_state = {
        name: tensor.detach().cpu().clone()
        for name, tensor in network.state_dict().items()
    }
    optimizer_state = deepcopy(optimizer.state_dict())
    sampler_rng_state = deepcopy(sampler.rng.bit_generator.state)
    torch_rng_state = torch.random.get_rng_state().clone()
    current_network_sha256 = lcsrs_c3_network_sha256(network)
    hashes = {
        "optimizer_state_sha256": state_sha256(optimizer_state),
        "sampler_rng_state_sha256": state_sha256(sampler_rng_state),
        "torch_rng_state_sha256": state_sha256(torch_rng_state),
        "network_state_sha256": state_sha256(network_state),
    }
    payload: dict[str, object] = {
        "schema": POSTGATE_C3_STATE_SCHEMA,
        "ladder_schema": POSTGATE_C3_SCHEMA,
        "arm": arm,
        "student_seed": student_seed,
        "source_manifest_sha256": source.source_manifest_sha256,
        "source_manifest_file_sha256": source.source_manifest_file_sha256,
        "result_sha256": source.result_sha256,
        "result_manifest_sha256": source.result_manifest_sha256,
        "manifest_sha256": source.result_manifest_sha256,
        "source_row_count": source.source_row_count,
        "update_budget": source.update_budget,
        "source_artifact_schema": source.source_artifact_schema,
        "learner_config_sha256": LCSRS_C3_LEARNER_CONFIG_SHA256,
        "initial_network_sha256": initial_network_sha256,
        "current_network_sha256": current_network_sha256,
        "update_count": update_count,
        "network_state": network_state,
        "optimizer_state": optimizer_state,
        "sampler_rng_state": sampler_rng_state,
        "torch_rng_state": torch_rng_state,
        "state_hashes": hashes,
        # State itself carries the boundary flags so loading a forged sidecar
        # cannot silently widen the JSON receipt's claim ceiling.
        "learner_update": True,
        "episode_checkpoint": False,
        "episode_training": False,
        "test_split_opened": False,
        "evaluation": False,
        "deployment": False,
    }
    return payload, hashes


def _checkpoint_receipt(
    *,
    arm: str,
    student_seed: int,
    source: AuthenticatedV023Source,
    initial_network_sha256: str,
    update_count: int,
    state_name: str,
    state_sha256_value: str,
    hashes: Mapping[str, str],
) -> dict[str, object]:
    source_manifest = {
        "sha256": source.source_manifest_sha256,
        "file_sha256": source.source_manifest_file_sha256,
        "result_sha256": source.result_sha256,
        "result_manifest_sha256": source.result_manifest_sha256,
        "artifact_schema": source.source_artifact_schema,
        "provider_id": source.provider_id,
        "provider_receipt_sha256": source.provider_receipt_sha256,
        "anchor_sha256s": list(source.source_anchor_sha256s),
        "target_source_sha256": source.target_source_sha256,
        "source_row_count": source.source_row_count,
        "update_budget": source.update_budget,
    }
    body: dict[str, object] = {
        "schema": POSTGATE_C3_CHECKPOINT_SCHEMA,
        "ladder_schema": POSTGATE_C3_SCHEMA,
        "status": "CHECKPOINTED",
        "claim_ceiling": POSTGATE_C3_CLAIM_CEILING,
        "checkpoint_kind": POSTGATE_C3_CHECKPOINT_KIND,
        "update_axis": "learner_updates",
        "update_count": update_count,
        "exact_update_count": update_count,
        "update_budget": source.update_budget,
        "arm": arm,
        "student_seed": student_seed,
        "source_manifest_sha256": source.source_manifest_sha256,
        "source_manifest_file_sha256": source.source_manifest_file_sha256,
        "result_sha256": source.result_sha256,
        "result_manifest_sha256": source.result_manifest_sha256,
        "manifest_sha256": source.result_manifest_sha256,
        "source_row_count": source.source_row_count,
        "source_artifact_schema": source.source_artifact_schema,
        "source_manifest": source_manifest,
        "target_source_sha256": source.target_source_sha256,
        "learner_config": learner_config_payload(),
        "learner_config_sha256": LCSRS_C3_LEARNER_CONFIG_SHA256,
        "initial_network_sha256": initial_network_sha256,
        "initial_model_sha256": initial_network_sha256,
        "current_network_sha256": hashes.get("current_network_sha256", ""),
        "current_model_sha256": hashes.get("current_network_sha256", ""),
        "network_state_sha256": hashes["network_state_sha256"],
        "optimizer_state_sha256": hashes["optimizer_state_sha256"],
        "sampler_rng_state_sha256": hashes["sampler_rng_state_sha256"],
        "torch_rng_state_sha256": hashes["torch_rng_state_sha256"],
        "rng_state_sha256": canonical_sha256(
            {
                "sampler": hashes["sampler_rng_state_sha256"],
                "torch": hashes["torch_rng_state_sha256"],
            }
        ),
        "state_path": state_name,
        "state_sha256": state_sha256_value,
        "state_format": "torch-state-dict-v1",
        "batch_size": POSTGATE_C3_BATCH_SIZE,
        "learner_update": True,
        "episode_checkpoint": False,
        "episode_training": False,
        "test_split_opened": False,
        "evaluation": False,
        "deployment": False,
        "selection": {
            "early_stopping": False,
            "best_checkpoint_selection": False,
            "outcome_dependent_selection": False,
            "selected_checkpoint": None,
        },
    }
    # ``current_network_sha256`` is filled by the caller through the hashes
    # mapping.  Keep the receipt constructor strict if a caller forgets it.
    if not hashes.get("current_network_sha256"):
        raise PostGateC3UpdateLadderError("current network digest is missing")
    body["receipt_sha256"] = canonical_sha256(body)
    return body


@dataclass(frozen=True)
class C3UpdateCheckpoint:
    """One JSON receipt and its bound state sidecar."""

    receipt_path: Path
    state_path: Path
    receipt: Mapping[str, object]

    @property
    def update_count(self) -> int:
        return int(self.receipt["update_count"])

    @property
    def current_model_sha256(self) -> str:
        return str(self.receipt["current_model_sha256"])


@dataclass(frozen=True)
class PostGateC3UpdateRun:
    """Non-evaluative result of one source-arm update ladder invocation."""

    arm: str
    student_seeds: tuple[int, ...]
    output_dir: Path
    checkpoints: tuple[C3UpdateCheckpoint, ...]
    status: str
    selected_checkpoint: None = None
    test_split_opened: bool = False
    episode_training: bool = False
    evaluation: bool = False
    deployment: bool = False


def _validate_ladder_constants() -> None:
    if POSTGATE_C3_UPDATE_COUNT != LCSRS_C3_UPDATE_COUNT:
        raise PostGateC3UpdateLadderError(
            "post-Gate plumbing cannot change the frozen 2,000-update budget"
        )
    expected = tuple(range(0, LCSRS_C3_UPDATE_COUNT + 1, 100))
    if POSTGATE_C3_UPDATE_AXIS != expected:
        raise PostGateC3UpdateLadderError(
            "post-Gate source-update axis drifted from 0..2000 by 100"
        )
    if POSTGATE_C3_STUDENT_SEEDS != (
        2026135101,
        2026135102,
        2026135103,
    ):
        raise PostGateC3UpdateLadderError("post-Gate student seed panel drifted")
    if learner_config_sha256() != LCSRS_C3_LEARNER_CONFIG_SHA256:
        raise PostGateC3UpdateLadderError("inherited learner configuration digest drifted")


def _validate_request(*, arm: str, student_seeds: Sequence[int]) -> tuple[int, ...]:
    _validate_ladder_constants()
    if arm not in POSTGATE_C3_SOURCE_ARMS:
        raise PostGateC3UpdateLadderError("source arm is outside the post-Gate seam")
    seeds = tuple(student_seeds)
    if seeds != POSTGATE_C3_STUDENT_SEEDS:
        raise PostGateC3UpdateLadderError(
            "post-Gate source ladder requires exactly the three frozen student seeds"
        )
    if any(type(seed) is not int or seed < 0 for seed in seeds):
        raise PostGateC3UpdateLadderError("student seeds must be nonnegative integers")
    return seeds


def _validate_stop_after(stop_after: int | None) -> int:
    if stop_after is None:
        return POSTGATE_C3_UPDATE_COUNT
    if stop_after not in POSTGATE_C3_UPDATE_AXIS:
        raise PostGateC3UpdateLadderError(
            "stop_after must be one of the fixed learner-update checkpoints"
        )
    return int(stop_after)


def _persist_checkpoint(
    *,
    directory: Path,
    arm: str,
    student_seed: int,
    source: AuthenticatedV023Source,
    initial_network_sha256: str,
    update_count: int,
    network: LCSRSC3QNetwork,
    optimizer: torch.optim.Optimizer,
    sampler: LCSRSC3ClassBalancedSampler,
) -> C3UpdateCheckpoint:
    if update_count not in POSTGATE_C3_UPDATE_AXIS:
        raise PostGateC3UpdateLadderError(
            "only the fixed learner-update axis may be checkpointed"
        )
    state_payload, state_hashes = _checkpoint_state_payload(
        arm=arm,
        student_seed=student_seed,
        source=source,
        initial_network_sha256=initial_network_sha256,
        update_count=update_count,
        network=network,
        optimizer=optimizer,
        sampler=sampler,
    )
    state_hashes = dict(state_hashes)
    state_hashes["current_network_sha256"] = lcsrs_c3_network_sha256(network)
    state_bytes = _torch_state_bytes(state_payload)
    state_name, receipt_name = _checkpoint_names(update_count)
    state_path = directory / state_name
    receipt_path = directory / receipt_name
    state_file_sha256 = _write_once(state_path, state_bytes)
    receipt = _checkpoint_receipt(
        arm=arm,
        student_seed=student_seed,
        source=source,
        initial_network_sha256=initial_network_sha256,
        update_count=update_count,
        state_name=state_name,
        state_sha256_value=state_file_sha256,
        hashes=state_hashes,
    )
    _write_once_json(receipt_path, receipt)
    return C3UpdateCheckpoint(
        receipt_path=receipt_path,
        state_path=state_path,
        receipt=receipt,
    )


def _seed_directory(output_dir: Path, *, arm: str, student_seed: int) -> Path:
    return output_dir / "checkpoints" / arm.lower() / f"seed-{student_seed}"


def _run_seed(
    *,
    source_provider: object,
    arm: str,
    student_seed: int,
    output_dir: Path,
    stop_after: int | None = None,
) -> tuple[C3UpdateCheckpoint, ...]:
    source = _provider_source(
        source_provider,
        arm=arm,
        student_seed=student_seed,
    )
    target_stop = _validate_stop_after(stop_after)
    network, optimizer = make_lcsrs_c3_student(student_seed=student_seed, device="cpu")
    initial_network_sha256 = lcsrs_c3_network_sha256(network)
    sampler = _sampler_for_source(source, student_seed=student_seed)
    directory = _seed_directory(output_dir, arm=arm, student_seed=student_seed)
    directory.mkdir(parents=True, exist_ok=False)
    checkpoints: list[C3UpdateCheckpoint] = []
    checkpoints.append(
        _persist_checkpoint(
            directory=directory,
            arm=arm,
            student_seed=student_seed,
            source=source,
            initial_network_sha256=initial_network_sha256,
            update_count=0,
            network=network,
            optimizer=optimizer,
            sampler=sampler,
        )
    )
    for update in range(1, target_stop + 1):
        batch = sampler.draw(POSTGATE_C3_BATCH_SIZE)
        try:
            lcsrs_c3_training_step(
                network,
                optimizer,
                source.surfaces,
                batch,
                device="cpu",
            )
        except Exception as error:
            raise PostGateC3UpdateLadderError(
                f"learner update {update} failed for seed {student_seed}"
            ) from error
        if update in POSTGATE_C3_UPDATE_AXIS:
            checkpoints.append(
                _persist_checkpoint(
                    directory=directory,
                    arm=arm,
                    student_seed=student_seed,
                    source=source,
                    initial_network_sha256=initial_network_sha256,
                    update_count=update,
                    network=network,
                    optimizer=optimizer,
                    sampler=sampler,
                )
            )
    return tuple(checkpoints)


def run_postgate_c3_update_ladder(
    source_provider: AuthenticatedV023SourceProvider,
    *,
    arm: str,
    output_dir: str | Path,
    student_seeds: Sequence[int] = POSTGATE_C3_STUDENT_SEEDS,
    stop_after: int | None = None,
) -> PostGateC3UpdateRun:
    """Run one source arm over all three seeds and the fixed update axis.

    ``stop_after`` is a resumable development/test cut at an already sealed
    axis point; omitting it runs the full 2,000 learner updates.  It never
    changes the axis or creates a partial result that can be mistaken for a
    selected/best model.
    """

    seeds = _validate_request(arm=arm, student_seeds=student_seeds)
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise PostGateC3UpdateLadderError(
            f"refusing to reuse post-Gate output directory: {destination}"
        )
    destination.mkdir(parents=True, exist_ok=False)
    all_checkpoints: list[C3UpdateCheckpoint] = []
    for seed in seeds:
        all_checkpoints.extend(
            _run_seed(
                source_provider=source_provider,
                arm=arm,
                student_seed=seed,
                output_dir=destination,
                stop_after=stop_after,
            )
        )
    target_stop = _validate_stop_after(stop_after)
    return PostGateC3UpdateRun(
        arm=arm,
        student_seeds=seeds,
        output_dir=destination,
        checkpoints=tuple(all_checkpoints),
        status="COMPLETE" if target_stop == POSTGATE_C3_UPDATE_COUNT else "PARTIAL",
    )


def _resolve_receipt_path(path: str | Path) -> Path:
    requested = Path(path)
    if requested.suffix == ".pt":
        stem = requested.name.removesuffix(".state.pt")
        requested = requested.with_name(stem + ".json")
    if requested.suffix != ".json":
        raise PostGateC3UpdateLadderError(
            "checkpoint path must point to its JSON receipt or state sidecar"
        )
    if requested.is_symlink() or not requested.is_file():
        raise PostGateC3UpdateLadderError("checkpoint receipt is missing or symlinked")
    return requested.resolve()


def _read_receipt(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PostGateC3UpdateLadderError("checkpoint receipt is not ASCII JSON") from error
    if not isinstance(payload, dict) or raw not in (
        _canonical_bytes(payload),
        _canonical_bytes(payload) + b"\n",
    ):
        raise PostGateC3UpdateLadderError("checkpoint receipt is not canonical JSON")
    declared = _digest(payload.get("receipt_sha256"), field="receipt_sha256")
    unsigned = dict(payload)
    unsigned.pop("receipt_sha256", None)
    if canonical_sha256(unsigned) != declared:
        raise PostGateC3UpdateLadderError("checkpoint receipt seal disagrees")
    return payload


def _safe_state_path(receipt_path: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise PostGateC3UpdateLadderError("checkpoint state path is not relative")
    candidate = receipt_path.parent / relative
    if candidate.is_symlink() or not candidate.is_file():
        raise PostGateC3UpdateLadderError("checkpoint state is missing or symlinked")
    resolved_parent = receipt_path.parent.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_parent):
        raise PostGateC3UpdateLadderError("checkpoint state path escapes receipt directory")
    return resolved


def _validate_receipt_payload(payload: Mapping[str, object]) -> None:
    if payload.get("schema") != POSTGATE_C3_CHECKPOINT_SCHEMA:
        raise PostGateC3UpdateLadderError("checkpoint schema drifted")
    if payload.get("ladder_schema") != POSTGATE_C3_SCHEMA:
        raise PostGateC3UpdateLadderError("checkpoint ladder schema drifted")
    if payload.get("status") != "CHECKPOINTED":
        raise PostGateC3UpdateLadderError("checkpoint status is not CHECKPOINTED")
    if payload.get("claim_ceiling") != POSTGATE_C3_CLAIM_CEILING:
        raise PostGateC3UpdateLadderError("checkpoint claim ceiling drifted")
    if payload.get("checkpoint_kind") != POSTGATE_C3_CHECKPOINT_KIND:
        raise PostGateC3UpdateLadderError("checkpoint is not a learner-update checkpoint")
    if payload.get("update_axis") != "learner_updates":
        raise PostGateC3UpdateLadderError("checkpoint axis is not learner updates")
    update = _exact_nonnegative_int(payload.get("update_count"), field="update_count")
    if update not in POSTGATE_C3_UPDATE_AXIS:
        raise PostGateC3UpdateLadderError("checkpoint update is outside the fixed axis")
    if payload.get("exact_update_count") != update:
        raise PostGateC3UpdateLadderError("exact update count disagrees")
    if payload.get("update_budget") != POSTGATE_C3_UPDATE_COUNT:
        raise PostGateC3UpdateLadderError("checkpoint update budget drifted")
    if payload.get("arm") not in POSTGATE_C3_SOURCE_ARMS:
        raise PostGateC3UpdateLadderError("checkpoint source arm drifted")
    seed = payload.get("student_seed")
    if type(seed) is not int or seed not in POSTGATE_C3_STUDENT_SEEDS:
        raise PostGateC3UpdateLadderError("checkpoint student seed drifted")
    _digest(payload.get("source_manifest_sha256"), field="source_manifest_sha256")
    for field in (
        "source_manifest_file_sha256",
        "result_sha256",
        "result_manifest_sha256",
        "manifest_sha256",
    ):
        _optional_digest(payload.get(field), field=field)
    source_manifest = payload.get("source_manifest")
    if not isinstance(source_manifest, Mapping):
        raise PostGateC3UpdateLadderError("checkpoint source manifest binding is missing")
    if source_manifest.get("sha256") != payload.get("source_manifest_sha256"):
        raise PostGateC3UpdateLadderError("checkpoint source manifest hash disagrees")
    for direct, nested in (
        ("source_manifest_file_sha256", "file_sha256"),
        ("result_sha256", "result_sha256"),
        ("result_manifest_sha256", "result_manifest_sha256"),
    ):
        if source_manifest.get(nested) != payload.get(direct):
            raise PostGateC3UpdateLadderError(
                f"checkpoint {direct} binding disagrees"
            )
    if payload.get("manifest_sha256") != payload.get("result_manifest_sha256"):
        raise PostGateC3UpdateLadderError(
            "checkpoint manifest hash alias disagrees"
        )
    if source_manifest.get("artifact_schema") != POSTGATE_C3_SOURCE_ARTIFACT_SCHEMA:
        raise PostGateC3UpdateLadderError("checkpoint source artifact schema drifted")
    if payload.get("source_artifact_schema") != POSTGATE_C3_SOURCE_ARTIFACT_SCHEMA:
        raise PostGateC3UpdateLadderError("checkpoint source artifact binding drifted")
    provider_id = source_manifest.get("provider_id")
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise PostGateC3UpdateLadderError("checkpoint source provider identity is missing")
    _digest(
        source_manifest.get("provider_receipt_sha256"),
        field="provider_receipt_sha256",
    )
    anchor_hashes = source_manifest.get("anchor_sha256s")
    if not isinstance(anchor_hashes, list) or not anchor_hashes:
        raise PostGateC3UpdateLadderError(
            "checkpoint source manifest anchor binding is missing"
        )
    for index, value in enumerate(anchor_hashes):
        _digest(value, field=f"source_manifest.anchor_sha256s[{index}]")
    _digest(payload.get("target_source_sha256"), field="target_source_sha256")
    if source_manifest.get("target_source_sha256") != payload.get("target_source_sha256"):
        raise PostGateC3UpdateLadderError("checkpoint target source binding disagrees")
    row_count = _exact_nonnegative_int(
        payload.get("source_row_count"), field="source_row_count"
    )
    if row_count <= 0 or source_manifest.get("source_row_count") != row_count:
        raise PostGateC3UpdateLadderError("checkpoint source row budget disagrees")
    if source_manifest.get("update_budget") != payload.get("update_budget"):
        raise PostGateC3UpdateLadderError("checkpoint update budget binding disagrees")
    if payload.get("learner_config_sha256") != LCSRS_C3_LEARNER_CONFIG_SHA256:
        raise PostGateC3UpdateLadderError("checkpoint learner configuration hash drifted")
    if canonical_sha256(payload.get("learner_config")) != LCSRS_C3_LEARNER_CONFIG_SHA256:
        raise PostGateC3UpdateLadderError("checkpoint learner configuration disagrees")
    for field in (
        "initial_network_sha256",
        "initial_model_sha256",
        "current_network_sha256",
        "current_model_sha256",
        "network_state_sha256",
        "optimizer_state_sha256",
        "sampler_rng_state_sha256",
        "torch_rng_state_sha256",
        "rng_state_sha256",
        "state_sha256",
    ):
        _digest(payload.get(field), field=field)
    if payload.get("initial_model_sha256") != payload.get("initial_network_sha256"):
        raise PostGateC3UpdateLadderError("initial model/network hashes disagree")
    if payload.get("current_model_sha256") != payload.get("current_network_sha256"):
        raise PostGateC3UpdateLadderError("current model/network hashes disagree")
    if payload.get("batch_size") != POSTGATE_C3_BATCH_SIZE:
        raise PostGateC3UpdateLadderError("checkpoint batch size drifted")
    for field, expected in (
        ("learner_update", True),
        ("episode_checkpoint", False),
        ("episode_training", False),
        ("test_split_opened", False),
        ("evaluation", False),
        ("deployment", False),
    ):
        if payload.get(field) is not expected:
            raise PostGateC3UpdateLadderError(
                f"checkpoint boundary flag {field} disagrees"
            )
    selection = payload.get("selection")
    expected_selection = {
        "early_stopping": False,
        "best_checkpoint_selection": False,
        "outcome_dependent_selection": False,
        "selected_checkpoint": None,
    }
    if selection != expected_selection:
        raise PostGateC3UpdateLadderError(
            "checkpoint contains outcome-dependent selection"
        )


def _load_state(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    try:
        loaded = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=False)
    except Exception as error:
        raise PostGateC3UpdateLadderError("checkpoint state cannot be loaded") from error
    if not isinstance(loaded, dict):
        raise PostGateC3UpdateLadderError("checkpoint state root is not a mapping")
    return loaded


def _restore_checkpoint(
    receipt_path: Path,
    *,
    source_provider: object | None = None,
) -> tuple[
    dict[str, object],
    AuthenticatedV023Source | None,
    LCSRSC3QNetwork,
    torch.optim.Optimizer,
    LCSRSC3ClassBalancedSampler | None,
]:
    receipt = _read_receipt(receipt_path)
    _validate_receipt_payload(receipt)
    state_path = _safe_state_path(receipt_path, receipt.get("state_path"))
    state_bytes = state_path.read_bytes()
    if hashlib.sha256(state_bytes).hexdigest() != receipt.get("state_sha256"):
        raise PostGateC3UpdateLadderError("checkpoint state byte hash disagrees")
    state = _load_state(state_path)
    for field in (
        "arm",
        "student_seed",
        "source_manifest_sha256",
        "source_manifest_file_sha256",
        "result_sha256",
        "result_manifest_sha256",
        "manifest_sha256",
        "source_row_count",
        "update_budget",
        "source_artifact_schema",
        "learner_config_sha256",
        "initial_network_sha256",
        "current_network_sha256",
        "update_count",
    ):
        if state.get(field) != receipt.get(field):
            raise PostGateC3UpdateLadderError(
                f"checkpoint state/receipt {field} disagrees"
            )
    if state.get("schema") != POSTGATE_C3_STATE_SCHEMA:
        raise PostGateC3UpdateLadderError("checkpoint state schema drifted")
    if state.get("ladder_schema") != POSTGATE_C3_SCHEMA:
        raise PostGateC3UpdateLadderError("checkpoint state ladder schema drifted")
    for field, expected in (
        ("learner_update", True),
        ("episode_checkpoint", False),
        ("episode_training", False),
        ("test_split_opened", False),
        ("evaluation", False),
        ("deployment", False),
    ):
        if state.get(field) is not expected:
            raise PostGateC3UpdateLadderError(
                f"checkpoint state boundary flag {field} disagrees"
            )
    state_hashes = state.get("state_hashes")
    if not isinstance(state_hashes, Mapping):
        raise PostGateC3UpdateLadderError("checkpoint state hashes are missing")
    network_state = state.get("network_state")
    optimizer_state = state.get("optimizer_state")
    sampler_rng_state = state.get("sampler_rng_state")
    torch_rng_state = state.get("torch_rng_state")
    if not isinstance(network_state, Mapping) or not isinstance(optimizer_state, Mapping):
        raise PostGateC3UpdateLadderError("checkpoint network/optimizer state is malformed")
    if state_sha256(network_state) != state_hashes.get("network_state_sha256"):
        raise PostGateC3UpdateLadderError("checkpoint network state hash disagrees")
    if state_sha256(optimizer_state) != state_hashes.get("optimizer_state_sha256"):
        raise PostGateC3UpdateLadderError("checkpoint optimizer state hash disagrees")
    if state_sha256(sampler_rng_state) != state_hashes.get("sampler_rng_state_sha256"):
        raise PostGateC3UpdateLadderError("checkpoint sampler RNG hash disagrees")
    if state_sha256(torch_rng_state) != state_hashes.get("torch_rng_state_sha256"):
        raise PostGateC3UpdateLadderError("checkpoint torch RNG hash disagrees")
    if state_hashes.get("optimizer_state_sha256") != receipt.get("optimizer_state_sha256"):
        raise PostGateC3UpdateLadderError("optimizer state hash is not receipt-bound")
    if state_hashes.get("sampler_rng_state_sha256") != receipt.get("sampler_rng_state_sha256"):
        raise PostGateC3UpdateLadderError("sampler RNG hash is not receipt-bound")
    if state_hashes.get("torch_rng_state_sha256") != receipt.get("torch_rng_state_sha256"):
        raise PostGateC3UpdateLadderError("torch RNG hash is not receipt-bound")
    if state_hashes.get("network_state_sha256") != receipt.get("network_state_sha256"):
        raise PostGateC3UpdateLadderError("network state hash is not receipt-bound")
    if canonical_sha256(
        {
            "sampler": receipt.get("sampler_rng_state_sha256"),
            "torch": receipt.get("torch_rng_state_sha256"),
        }
    ) != receipt.get("rng_state_sha256"):
        raise PostGateC3UpdateLadderError("combined RNG state hash disagrees")
    source: AuthenticatedV023Source | None = None
    if source_provider is not None:
        source = _provider_source(
            source_provider,
            arm=str(receipt["arm"]),
            student_seed=int(receipt["student_seed"]),
        )
        if source.source_manifest_sha256 != receipt.get("source_manifest_sha256"):
            raise PostGateC3UpdateLadderError("resume source manifest hash disagrees")
        for field in (
            "source_manifest_file_sha256",
            "result_sha256",
            "result_manifest_sha256",
            "manifest_sha256",
            "source_row_count",
            "update_budget",
        ):
            if getattr(source, field) != receipt.get(field):
                raise PostGateC3UpdateLadderError(
                    f"resume {field} binding disagrees"
                )
        if source.target_source_sha256 != receipt.get("target_source_sha256"):
            raise PostGateC3UpdateLadderError("resume target source hash disagrees")
        manifest = receipt["source_manifest"]
        if not isinstance(manifest, Mapping):  # pragma: no cover - validated above
            raise PostGateC3UpdateLadderError("resume source manifest binding malformed")
        if manifest.get("provider_id") != source.provider_id or manifest.get(
            "provider_receipt_sha256"
        ) != source.provider_receipt_sha256:
            raise PostGateC3UpdateLadderError("resume provider attestation disagrees")
        if manifest.get("anchor_sha256s") != list(source.source_anchor_sha256s):
            raise PostGateC3UpdateLadderError("resume source anchor binding disagrees")
    state_before = torch.random.get_rng_state()
    try:
        network, optimizer = make_lcsrs_c3_student(
            student_seed=int(receipt["student_seed"]), device="cpu"
        )
        expected_initial = lcsrs_c3_network_sha256(network)
        if expected_initial != receipt.get("initial_network_sha256"):
            raise PostGateC3UpdateLadderError("initial model hash is not seed-exact")
        network.load_state_dict(network_state, strict=True)
        if lcsrs_c3_network_sha256(network) != receipt.get("current_network_sha256"):
            raise PostGateC3UpdateLadderError("current model hash disagrees")
        try:
            optimizer.load_state_dict(optimizer_state)
        except Exception as error:
            raise PostGateC3UpdateLadderError(
                "checkpoint optimizer state cannot be restored"
            ) from error
    except PostGateC3UpdateLadderError:
        raise
    except Exception as error:
        raise PostGateC3UpdateLadderError("checkpoint model state cannot be restored") from error
    finally:
        torch.random.set_rng_state(state_before)
    if source is not None:
        assert source is not None
        sampler = _sampler_for_source(source, student_seed=int(receipt["student_seed"]))
        try:
            sampler.rng.bit_generator.state = deepcopy(sampler_rng_state)
        except Exception as error:
            raise PostGateC3UpdateLadderError(
                "checkpoint sampler RNG state cannot be restored"
            ) from error
        try:
            torch.random.set_rng_state(torch_rng_state)
        except Exception as error:
            raise PostGateC3UpdateLadderError(
                "checkpoint torch RNG state cannot be restored"
            ) from error
    else:
        sampler = None
    return receipt, source, network, optimizer, sampler


def verify_postgate_c3_checkpoint(
    checkpoint_path: str | Path,
    *,
    source_provider: AuthenticatedV023SourceProvider | None = None,
) -> Mapping[str, object]:
    """Verify a learner-update checkpoint without evaluating or selecting it."""

    receipt_path = _resolve_receipt_path(checkpoint_path)
    receipt, _source, _network, _optimizer, _sampler = _restore_checkpoint(
        receipt_path,
        source_provider=source_provider,
    )
    return receipt


def _existing_checkpoints(directory: Path) -> tuple[C3UpdateCheckpoint, ...]:
    receipts: list[C3UpdateCheckpoint] = []
    for receipt_path in sorted(directory.glob("checkpoint-*.json")):
        receipt = _read_receipt(receipt_path)
        _validate_receipt_payload(receipt)
        state_path = _safe_state_path(receipt_path, receipt.get("state_path"))
        receipts.append(
            C3UpdateCheckpoint(
                receipt_path=receipt_path,
                state_path=state_path,
                receipt=receipt,
            )
        )
    return tuple(sorted(receipts, key=lambda row: row.update_count))


def resume_postgate_c3_update_ladder(
    checkpoint_path: str | Path,
    source_provider: AuthenticatedV023SourceProvider,
    *,
    stop_after: int | None = None,
) -> PostGateC3UpdateRun:
    """Resume one seed/arm from a verified learner-update checkpoint."""

    receipt_path = _resolve_receipt_path(checkpoint_path)
    receipt, source, network, optimizer, sampler = _restore_checkpoint(
        receipt_path,
        source_provider=source_provider,
    )
    if source is None or sampler is None:  # pragma: no cover - provider required above
        raise PostGateC3UpdateLadderError("resume requires an authenticated source")
    target_stop = _validate_stop_after(stop_after)
    current = int(receipt["update_count"])
    if target_stop < current:
        raise PostGateC3UpdateLadderError(
            "resume stop_after cannot precede the checkpoint update"
        )
    output_dir = receipt_path.parents[3]
    arm = str(receipt["arm"])
    student_seed = int(receipt["student_seed"])
    directory = receipt_path.parent
    initial_network_sha256 = str(receipt["initial_network_sha256"])
    checkpoints = list(_existing_checkpoints(directory))
    if not checkpoints or checkpoints[-1].update_count != current:
        raise PostGateC3UpdateLadderError(
            "resume directory does not end at the requested checkpoint"
        )
    for update in range(current + 1, target_stop + 1):
        batch = sampler.draw(POSTGATE_C3_BATCH_SIZE)
        try:
            lcsrs_c3_training_step(
                network,
                optimizer,
                source.surfaces,
                batch,
                device="cpu",
            )
        except Exception as error:
            raise PostGateC3UpdateLadderError(
                f"resumed learner update {update} failed"
            ) from error
        if update in POSTGATE_C3_UPDATE_AXIS:
            checkpoints.append(
                _persist_checkpoint(
                    directory=directory,
                    arm=arm,
                    student_seed=student_seed,
                    source=source,
                    initial_network_sha256=initial_network_sha256,
                    update_count=update,
                    network=network,
                    optimizer=optimizer,
                    sampler=sampler,
                )
            )
    return PostGateC3UpdateRun(
        arm=arm,
        student_seeds=(student_seed,),
        output_dir=output_dir,
        checkpoints=tuple(sorted(checkpoints, key=lambda row: row.update_count)),
        status="COMPLETE" if target_stop == POSTGATE_C3_UPDATE_COUNT else "PARTIAL",
    )


# Explicit aliases for callers that prefer "checkpoint" in the verb.
run_update_ladder = run_postgate_c3_update_ladder
resume_update_ladder = resume_postgate_c3_update_ladder
verify_checkpoint = verify_postgate_c3_checkpoint


__all__ = [
    "POSTGATE_C3_SCHEMA",
    "POSTGATE_C3_STATE_SCHEMA",
    "POSTGATE_C3_CHECKPOINT_SCHEMA",
    "POSTGATE_C3_CLAIM_CEILING",
    "POSTGATE_C3_UPDATE_COUNT",
    "POSTGATE_C3_BATCH_SIZE",
    "POSTGATE_C3_UPDATE_AXIS",
    "POSTGATE_C3_STUDENT_SEEDS",
    "POSTGATE_C3_SOURCE_ARMS",
    "POSTGATE_C3_SOURCE_ARTIFACT_SCHEMA",
    "UPDATE_AXIS",
    "SOURCE_UPDATE_AXIS",
    "CHECKPOINT_AXIS",
    "CHECKPOINT_UPDATES",
    "STUDENT_SEEDS",
    "V023_STUDENT_SEEDS",
    "SOURCE_ARMS",
    "PostGateC3UpdateLadderError",
    "AuthenticatedV023Source",
    "AuthenticatedV023SourceProvider",
    "V023SourceProvider",
    "authenticated_source_from_v023_panel",
    "bind_v023_source_panel",
    "C3UpdateCheckpoint",
    "PostGateC3UpdateRun",
    "canonical_sha256",
    "state_sha256",
    "learner_config_payload",
    "learner_config_sha256",
    "run_postgate_c3_update_ladder",
    "resume_postgate_c3_update_ladder",
    "verify_postgate_c3_checkpoint",
    "run_update_ladder",
    "resume_update_ladder",
    "verify_checkpoint",
]
