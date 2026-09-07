"""Lazy, authenticated source adapter for a sealed V0.23 Gate output.

This module is the post-Gate external source seam.  It only reopens immutable
JSON/NPZ source artifacts and the already sealed Gate result directory; it
never creates a source, runs a simulator, trains a learner, evaluates a model,
or opens TEST.  ``NEUTRAL_SOURCE`` is the existing Gate matched-placebo
permutation over the same retained rows.  No neutral rows are invented here.

The adapter is deliberately path-oriented so a future server worker can use
it without changing the current Gate runner.  A successful ``provide`` call
returns the existing post-Gate ``AuthenticatedV023Source`` and binds all of:

* the source-manifest body and byte digests;
* the sealed ``result.json`` and ``MANIFEST.sha256`` byte digests;
* the exact source artifact schema, retained-row count, and 2,000-update
  learner budget; and
* the fixed matched-placebo key and every reconstructed source anchor.

The source and result trees are reopened on every call.  A file changed after
one arm was loaded therefore fails closed instead of being hidden by a cache.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

import numpy as np

# Scratch modules are also loaded directly by future server workers.  Add the
# repository package roots before importing the typed source artifact code;
# this only changes import resolution and performs no runtime work.
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.runtime.ee_axis_lcsrs_c3_dataset import LCSRSAnchorRecord
from mcrl.runtime.ee_axis_lcsrs_c3_placebo import (
    LCSRSMatchedPlacebo,
    build_lcsrs_matched_placebo,
)
from mcrl.runtime.ee_axis_lcsrs_c3_source_artifact import (
    LCSRSC3SourceArtifactError,
    V023_PLACEBO_KEY,
    V023_PLACEBO_KEY_SHA256,
    V023_SOURCE_ARTIFACT_SCHEMA,
    V023_SOURCE_ARTIFACT_VERSION,
    V023_SOURCE_CLAIM_CEILING,
    V023_WORLDS,
    V023WorldSourceArtifact,
    load_v023_world_source_artifact,
)


SEALED_V023_PROVIDER_SCHEMA = (
    "multi-catfish-mcrl-v023-postgate-sealed-source-provider-v1"
)
SEALED_SOURCE_PROVIDER_SCHEMA = SEALED_V023_PROVIDER_SCHEMA
V023_GATE_SOURCE_MANIFEST_SCHEMA = (
    "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1-source-manifest"
)
V023_GATE_RESULT_SCHEMAS = frozenset(
    {
        "multi-catfish-mcrl-v023-lcsrs-result-v1",
        "multi-catfish-mcrl-v023-lcsrs-final-verification-v1",
    }
)
V023_GATE_RESULT_STATUSES = frozenset(
    {
        "PASS_FINAL_INTEGRITY",
        "PASS_SOURCE_STAGE_INTEGRITY",
    }
)
V023_GATE_WORLDS = tuple(V023_WORLDS)
V023_STUDENT_SEEDS = (2026135101, 2026135102, 2026135103)
V023_POSTGATE_UPDATE_BUDGET = 2000
V023_POSTGATE_ARMS = ("INFORMED", "NEUTRAL_SOURCE")
V023_POSTGATE_CLAIM_CEILING = (
    "TRAIN_SOURCE_UPDATES_ONLY_NO_TEST_NO_PHYSICAL_EPISODES_NO_EVALUATION_NO_DEPLOYMENT"
)


class V023SealedSourceProviderError(RuntimeError):
    """A sealed source/result/manifest boundary failed closed."""


SealedV023SourceProviderError = V023SealedSourceProviderError


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
        raise V023SealedSourceProviderError(
            "value is not finite canonical ASCII JSON"
        ) from error


def canonical_sha256(value: object) -> str:
    """Hash one canonical JSON object using the Gate's compact encoding."""

    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023SealedSourceProviderError(f"{field} is not a lowercase SHA-256")
    return value


def file_sha256(path: str | Path) -> str:
    """Hash a regular file; symlinks and special files are never accepted."""

    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023SealedSourceProviderError(
            f"expected a regular file, not a symlink or missing path: {target}"
        )
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _regular_directory(path: str | Path, *, field: str) -> Path:
    requested = Path(path)
    if requested.is_symlink() or not requested.is_dir():
        raise V023SealedSourceProviderError(
            f"{field} is missing or is a symlink: {requested}"
        )
    return requested.resolve()


def _regular_file(path: str | Path, *, field: str) -> Path:
    requested = Path(path)
    if requested.is_symlink() or not requested.is_file():
        raise V023SealedSourceProviderError(
            f"{field} is missing or is a symlink: {requested}"
        )
    return requested.resolve()


def _reject_tree_symlinks(root: Path, *, field: str) -> None:
    """Reject symlinks anywhere in an authenticated artifact tree."""

    for path in root.rglob("*"):
        if path.is_symlink():
            raise V023SealedSourceProviderError(
                f"{field} contains a symlink: {path}"
            )


def _safe_relative_child(root: Path, relative: object, *, field: str) -> Path:
    if (
        not isinstance(relative, str)
        or not relative
        or Path(relative).is_absolute()
        or any(part in {"", ".", ".."} for part in Path(relative).parts)
    ):
        raise V023SealedSourceProviderError(
            f"{field} is not a safe relative path"
        )
    candidate = root / relative
    if candidate.is_symlink() or not candidate.is_file():
        raise V023SealedSourceProviderError(
            f"{field} is missing or is a symlink: {candidate}"
        )
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise V023SealedSourceProviderError(f"{field} escapes its root")
    return resolved


def _read_canonical_json(path: Path, *, field: str) -> dict[str, Any]:
    target = _regular_file(path, field=field)
    raw = target.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023SealedSourceProviderError(
            f"{field} is not canonical ASCII JSON"
        ) from error
    if not isinstance(payload, dict):
        raise V023SealedSourceProviderError(f"{field} root is not an object")
    canonical = _canonical_bytes(payload)
    if raw not in (canonical, canonical + b"\n"):
        raise V023SealedSourceProviderError(f"{field} is not canonical JSON")
    return payload


def _verify_source_manifest(
    payload: Mapping[str, Any], *, preflight_manifest_sha256: str
) -> str:
    """Verify the Gate two-hash source-manifest convention."""

    if payload.get("schema") != V023_GATE_SOURCE_MANIFEST_SCHEMA:
        raise V023SealedSourceProviderError("source manifest schema drifted")
    if payload.get("status") != "PASS":
        raise V023SealedSourceProviderError("source manifest is not PASS")
    if payload.get("claim_ceiling") != V023_SOURCE_CLAIM_CEILING:
        raise V023SealedSourceProviderError("source manifest claim ceiling drifted")
    if payload.get("preflight_manifest_sha256") != preflight_manifest_sha256:
        raise V023SealedSourceProviderError("source manifest preflight hash drifted")
    if payload.get("split") != "TRAIN_DEVELOPMENT":
        raise V023SealedSourceProviderError("source manifest is not TRAIN_DEVELOPMENT")
    for field in ("test_split_opened", "episode_training", "learner_update"):
        if payload.get(field) is not False:
            raise V023SealedSourceProviderError(
                f"source manifest crossed a closed {field} boundary"
            )
    if payload.get("worlds") != list(V023_GATE_WORLDS):
        raise V023SealedSourceProviderError("source manifest world panel drifted")
    if payload.get("source_count") != len(V023_GATE_WORLDS):
        raise V023SealedSourceProviderError("source manifest source count drifted")
    expected_shards = [
        {"world": world, "relative_name": f"source/world-{world}.json"}
        for world in V023_GATE_WORLDS
    ]
    if payload.get("shards") != expected_shards:
        raise V023SealedSourceProviderError("source manifest shard schedule drifted")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != len(expected_shards):
        raise V023SealedSourceProviderError("source manifest entries are incomplete")
    for actual, expected in zip(entries, expected_shards, strict=True):
        if not isinstance(actual, Mapping):
            raise V023SealedSourceProviderError("source manifest entry is malformed")
        if actual.get("world") != expected["world"]:
            raise V023SealedSourceProviderError("source manifest world order drifted")
        if actual.get("relative_name") != expected["relative_name"]:
            raise V023SealedSourceProviderError("source manifest path drifted")
        _digest(actual.get("sha256"), field="source manifest entry sha256")
    source_hash = _digest(
        payload.get("source_manifest_sha256"),
        field="source_manifest_sha256",
    )
    unsigned = dict(payload)
    unsigned.pop("source_manifest_sha256", None)
    unsigned.pop("manifest_sha256", None)
    if canonical_sha256(unsigned) != source_hash:
        raise V023SealedSourceProviderError(
            "source manifest body hash disagrees"
        )
    manifest_hash = _digest(payload.get("manifest_sha256"), field="manifest_sha256")
    unsigned_manifest = dict(payload)
    unsigned_manifest.pop("manifest_sha256", None)
    if canonical_sha256(unsigned_manifest) != manifest_hash:
        raise V023SealedSourceProviderError(
            "source manifest seal disagrees"
        )
    return source_hash


@dataclass(frozen=True)
class SealedV023SourcePanel:
    """A source-manifest-authenticated panel, before arm target binding."""

    source_directory: Path
    source_manifest_path: Path
    source_manifest_sha256: str
    source_manifest_file_sha256: str
    preflight_manifest_sha256: str
    artifacts: tuple[V023WorldSourceArtifact, ...]

    @property
    def records_by_world(self) -> dict[int, tuple[LCSRSAnchorRecord, ...]]:
        return {artifact.world: artifact.records for artifact in self.artifacts}

    @property
    def records(self) -> tuple[LCSRSAnchorRecord, ...]:
        return tuple(record for artifact in self.artifacts for record in artifact.records)

    @property
    def source_row_count(self) -> int:
        return sum(
            int(np.count_nonzero(record.surface.row_class == 3))
            for record in self.records
        )


def load_sealed_v023_source_panel(
    *,
    source_directory: str | Path,
    source_manifest: str | Path,
    preflight_manifest_sha256: str,
) -> SealedV023SourcePanel:
    """Reopen and authenticate the exact eight Gate source shards."""

    root = _regular_directory(source_directory, field="source directory")
    _reject_tree_symlinks(root, field="source directory")
    preflight = _digest(
        preflight_manifest_sha256,
        field="preflight_manifest_sha256",
    )
    manifest = _regular_file(source_manifest, field="source manifest")
    if not manifest.is_relative_to(root):
        raise V023SealedSourceProviderError(
            "source manifest escapes source directory"
        )
    payload = _read_canonical_json(manifest, field="source manifest")
    source_hash = _verify_source_manifest(
        payload,
        preflight_manifest_sha256=preflight,
    )
    artifacts: list[V023WorldSourceArtifact] = []
    entries = payload["entries"]
    for world, entry in zip(V023_GATE_WORLDS, entries, strict=True):
        if not isinstance(entry, Mapping):  # pragma: no cover - validated above
            raise V023SealedSourceProviderError("source manifest entry is malformed")
        relative = entry["relative_name"]
        child = _safe_relative_child(root, relative, field=f"world {world} source")
        if child.relative_to(root).as_posix() != relative:
            raise V023SealedSourceProviderError(
                f"world {world} source path is not canonical"
            )
        declared = _digest(
            entry["sha256"],
            field=f"world {world} source sha256",
        )
        actual = file_sha256(child)
        if actual != declared:
            raise V023SealedSourceProviderError(
                f"world {world} source byte hash disagrees"
            )
        try:
            artifact = load_v023_world_source_artifact(
                child,
                expected_world=world,
                expected_preflight_sha256=preflight,
            )
        except (LCSRSC3SourceArtifactError, OSError, ValueError, TypeError) as error:
            raise V023SealedSourceProviderError(
                f"world {world} source reconstruction failed: {error}"
            ) from error
        if artifact.index_sha256 != actual:
            raise V023SealedSourceProviderError(
                f"world {world} source digest was not retained"
            )
        if artifact.index.get("source_artifact_schema") != V023_SOURCE_ARTIFACT_SCHEMA:
            raise V023SealedSourceProviderError(
                f"world {world} source artifact schema drifted"
            )
        if artifact.index.get("source_artifact_version") != V023_SOURCE_ARTIFACT_VERSION:
            raise V023SealedSourceProviderError(
                f"world {world} source artifact version drifted"
            )
        artifacts.append(artifact)
    if tuple(artifact.world for artifact in artifacts) != V023_GATE_WORLDS:
        raise V023SealedSourceProviderError("source artifact world order drifted")
    if any(not artifact.records for artifact in artifacts):
        raise V023SealedSourceProviderError(
            "source panel has a world with no retained fitting anchors"
        )
    records = tuple(record for artifact in artifacts for record in artifact.records)
    identities = [(record.world_id, record.anchor_id) for record in records]
    if len(set(identities)) != len(identities):
        raise V023SealedSourceProviderError(
            "source panel repeats a world/anchor identity"
        )
    for artifact in artifacts:
        if any(record.world_id != artifact.world for record in artifact.records):
            raise V023SealedSourceProviderError(
                "source panel contains cross-world anchor leakage"
            )
    if not records or SealedV023SourcePanel(
        source_directory=root,
        source_manifest_path=manifest,
        source_manifest_sha256=source_hash,
        source_manifest_file_sha256=file_sha256(manifest),
        preflight_manifest_sha256=preflight,
        artifacts=tuple(artifacts),
    ).source_row_count <= 0:
        raise V023SealedSourceProviderError("source panel has no SUPPORTED learner rows")
    return SealedV023SourcePanel(
        source_directory=root,
        source_manifest_path=manifest,
        source_manifest_sha256=source_hash,
        source_manifest_file_sha256=file_sha256(manifest),
        preflight_manifest_sha256=preflight,
        artifacts=tuple(artifacts),
    )


def _verify_result_manifest(
    *,
    result_directory: Path,
    result_path: Path,
    result_manifest_path: Path,
    complete_path: Path,
) -> tuple[dict[str, Any], str, str]:
    """Verify result.json, MANIFEST.sha256, COMPLETE, and all listed files."""

    _reject_tree_symlinks(result_directory, field="result directory")
    result_payload = _read_canonical_json(result_path, field="result receipt")
    result_hash = file_sha256(result_path)
    manifest_raw = result_manifest_path.read_bytes()
    try:
        manifest_text = manifest_raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise V023SealedSourceProviderError(
            "result MANIFEST.sha256 is not ASCII"
        ) from error
    if not manifest_text.endswith("\n"):
        raise V023SealedSourceProviderError(
            "result MANIFEST.sha256 is not newline-terminated"
        )
    entries: dict[str, str] = {}
    for line in manifest_text.splitlines():
        if line.count("  ") != 1:
            raise V023SealedSourceProviderError(
                "result MANIFEST.sha256 has a malformed line"
            )
        digest, relative = line.split("  ", 1)
        _digest(digest, field=f"result manifest entry {relative}")
        if relative in entries:
            raise V023SealedSourceProviderError(
                f"result manifest repeats {relative}"
            )
        target = _safe_relative_child(
            result_directory,
            relative,
            field=f"result manifest entry {relative}",
        )
        if relative in {"MANIFEST.sha256", "COMPLETE"}:
            raise V023SealedSourceProviderError(
                "result manifest cannot list its own seal files"
            )
        if file_sha256(target) != digest:
            raise V023SealedSourceProviderError(
                f"result manifest digest disagrees for {relative}"
            )
        entries[relative] = digest
    result_relative = result_path.relative_to(result_directory).as_posix()
    if entries.get(result_relative) != result_hash:
        raise V023SealedSourceProviderError(
            "result manifest does not bind result.json"
        )
    listed = set(entries)
    actual_files = {
        path.relative_to(result_directory).as_posix()
        for path in result_directory.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    actual_files.difference_update({"MANIFEST.sha256", "COMPLETE"})
    if listed != actual_files:
        raise V023SealedSourceProviderError(
            "result manifest file set disagrees with the sealed result tree"
        )
    manifest_hash = file_sha256(result_manifest_path)
    expected_complete = f"{manifest_hash}  MANIFEST.sha256\n".encode("ascii")
    if complete_path.read_bytes() != expected_complete:
        raise V023SealedSourceProviderError(
            "COMPLETE does not bind MANIFEST.sha256"
        )
    return result_payload, result_hash, manifest_hash


def _find_source_manifest_hash(payload: Mapping[str, Any]) -> str:
    direct = payload.get("source_manifest_sha256")
    if direct is not None:
        return _digest(direct, field="result source_manifest_sha256")
    for container_name in ("source_panel", "source_manifest", "source_stage"):
        container = payload.get(container_name)
        if isinstance(container, Mapping) and container.get("source_manifest_sha256") is not None:
            return _digest(
                container.get("source_manifest_sha256"),
                field=f"result {container_name}.source_manifest_sha256",
            )
    raise V023SealedSourceProviderError(
        "result receipt does not bind source_manifest_sha256"
    )


def _verify_closed_result(
    payload: Mapping[str, Any],
    *,
    source_manifest_sha256: str,
    source_manifest_file_sha256: str,
    preflight_manifest_sha256: str,
    result_manifest_sha256: str,
    source_row_count: int,
) -> None:
    schema = payload.get("schema")
    if schema not in V023_GATE_RESULT_SCHEMAS:
        raise V023SealedSourceProviderError("result receipt schema is not V0.23")
    if payload.get("status") not in V023_GATE_RESULT_STATUSES:
        raise V023SealedSourceProviderError("result receipt is not an authenticated Gate result")
    if _find_source_manifest_hash(payload) != source_manifest_sha256:
        raise V023SealedSourceProviderError(
            "result/source manifest hash disagrees"
        )
    if payload.get("preflight_manifest_sha256") != preflight_manifest_sha256:
        raise V023SealedSourceProviderError(
            "result/preflight manifest hash disagrees"
        )
    for field in ("test_split_opened", "episode_training"):
        if payload.get(field) is not False:
            raise V023SealedSourceProviderError(
                f"result receipt crossed a closed {field} boundary"
            )
    if payload.get("split") not in (None, "TRAIN_DEVELOPMENT"):
        raise V023SealedSourceProviderError("result receipt split drifted")
    claim_ceiling = payload.get("claim_ceiling")
    if not isinstance(claim_ceiling, str) or "NO_TEST" not in claim_ceiling:
        raise V023SealedSourceProviderError("result receipt claim ceiling opens TEST")
    if "NO_EPISODE_TRAINING" not in claim_ceiling:
        raise V023SealedSourceProviderError(
            "result receipt claim ceiling opens episode training"
        )
    if payload.get("source_manifest_file_sha256") not in (None, source_manifest_file_sha256):
        raise V023SealedSourceProviderError(
            "result/source manifest byte hash disagrees"
        )
    if payload.get("result_manifest_sha256") not in (None, result_manifest_sha256):
        raise V023SealedSourceProviderError(
            "result directory manifest hash disagrees"
        )
    if payload.get("source_row_count") not in (None, source_row_count):
        raise V023SealedSourceProviderError("result source row count disagrees")
    for field in ("update_budget", "fit_updates", "learner_update_budget"):
        value = payload.get(field)
        if value is not None and (type(value) is not int or value != V023_POSTGATE_UPDATE_BUDGET):
            raise V023SealedSourceProviderError(
                f"result {field} disagrees with the frozen 2,000-update budget"
            )
    worlds = payload.get("worlds")
    if worlds is not None and worlds != list(V023_GATE_WORLDS):
        raise V023SealedSourceProviderError("result world panel drifted")
    source_count = payload.get("source_count")
    if source_count is not None and source_count != len(V023_GATE_WORLDS):
        raise V023SealedSourceProviderError("result source count drifted")
    arms = payload.get("arms")
    if arms is not None:
        if not isinstance(arms, list) or "INFORMED" not in arms or not any(
            value in arms for value in ("MATCHED_PLACEBO", "NEUTRAL_SOURCE")
        ):
            raise V023SealedSourceProviderError(
                "result arm panel does not bind informed and matched-placebo source"
            )
    nested_manifest = payload.get("source_manifest")
    if isinstance(nested_manifest, Mapping):
        nested_hash = nested_manifest.get("source_manifest_sha256")
        if nested_hash is not None and _digest(
            nested_hash,
            field="result nested source_manifest_sha256",
        ) != source_manifest_sha256:
            raise V023SealedSourceProviderError(
                "nested result/source manifest hash disagrees"
            )
    # The adapter does not consume outcomes, but it must never admit an
    # explicitly marked TEST or physical-episode artifact hidden in a nested
    # result receipt.
    def scan(value: object) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in {
                    "test_split_opened",
                    "episode_training",
                    "physical_episode",
                    "episode_checkpoint",
                } and child is not False:
                    raise V023SealedSourceProviderError(
                        f"result receipt nested {key} boundary is not closed"
                    )
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    scan(payload)


def _load_ladder_module() -> ModuleType:
    """Load the owned ladder definitions without importing it at module import."""

    target = Path(__file__).with_name("postgate_c3_update_ladder.py")
    if target.is_symlink() or not target.is_file():
        raise V023SealedSourceProviderError(
            f"post-Gate ladder module is missing or symlinked: {target}"
        )
    module_name = "mcrl_v023_postgate_update_ladder"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, target)
    if spec is None or spec.loader is None:
        raise V023SealedSourceProviderError(
            f"post-Gate ladder module cannot be loaded: {target}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        sys.modules.pop(module_name, None)
        raise V023SealedSourceProviderError(
            "post-Gate ladder module import failed"
        ) from error
    return module


def _flatten_panel_records(panel: SealedV023SourcePanel) -> tuple[LCSRSAnchorRecord, ...]:
    records = panel.records
    if tuple(artifact.world for artifact in panel.artifacts) != V023_GATE_WORLDS:
        raise V023SealedSourceProviderError("source panel world order drifted")
    seen: set[tuple[int, str]] = set()
    for record in records:
        if not isinstance(record, LCSRSAnchorRecord):
            raise V023SealedSourceProviderError(
                "source panel contains an unauthenticated anchor record"
            )
        identity = (record.world_id, record.anchor_id)
        if identity in seen:
            raise V023SealedSourceProviderError("source panel anchor identity repeated")
        seen.add(identity)
        if record.world_id not in V023_GATE_WORLDS:
            raise V023SealedSourceProviderError(
                "source panel contains a world outside the frozen panel"
            )
        try:
            record.surface.view.verify()
            LCSRSAnchorRecord(
                world_id=record.world_id,
                phase=record.phase,
                anchor_id=record.anchor_id,
                surface=record.surface,
                q12_values=record.q12_values,
                content_digest=record.content_digest,
            )
        except Exception as error:
            raise V023SealedSourceProviderError(
                f"source panel anchor reconstruction failed: {error}"
            ) from error
    return records


def build_authenticated_v023_sources(
    panel: SealedV023SourcePanel,
    *,
    result_sha256: str,
    result_manifest_sha256: str,
    provider_id: str = SEALED_V023_PROVIDER_SCHEMA,
) -> dict[str, object]:
    """Bind INFORMED and matched-placebo NEUTRAL_SOURCE to one source panel.

    The returned mapping is keyed by the post-Gate arm names.  This function
    accepts only a panel already authenticated by
    :func:`load_sealed_v023_source_panel`; callers cannot inject arbitrary
    rows or a hand-built neutral target through this seam.
    """

    result_sha = _digest(result_sha256, field="result_sha256")
    result_manifest_sha = _digest(
        result_manifest_sha256,
        field="result_manifest_sha256",
    )
    records = _flatten_panel_records(panel)
    if panel.source_row_count <= 0:
        raise V023SealedSourceProviderError("source panel has no SUPPORTED rows")
    shapes: list[tuple[int, ...]] = []
    for index, record in enumerate(records):
        surface = record.surface
        target_shape = tuple(surface.normalized_targets.shape)
        mask_shape = tuple(surface.view.action_mask.shape)
        class_shape = tuple(surface.row_class.shape)
        if target_shape != mask_shape or target_shape != class_shape:
            raise V023SealedSourceProviderError(
                f"source anchor {index} target/mask shape drifted"
            )
        if len(target_shape) != 2 or target_shape[1] != 28:
            raise V023SealedSourceProviderError(
                f"source anchor {index} has a non-C3 target shape"
            )
        shapes.append(target_shape)
    if len(set(shapes)) != 1:
        raise V023SealedSourceProviderError(
            "source anchors do not share one target/mask shape"
        )
    try:
        placebo: LCSRSMatchedPlacebo = build_lcsrs_matched_placebo(
            records,
            placebo_key=V023_PLACEBO_KEY,
        )
    except Exception as error:
        raise V023SealedSourceProviderError(
            f"matched-placebo source reconstruction failed: {error}"
        ) from error
    if placebo.placebo_key_sha256 != V023_PLACEBO_KEY_SHA256:
        raise V023SealedSourceProviderError("matched-placebo key digest drifted")
    if not placebo.meets_coverage_gate:
        raise V023SealedSourceProviderError(
            "matched-placebo source is below the frozen 0.80 coverage gate"
        )
    for mapping in placebo.mappings:
        source_world = records[mapping.source_anchor].world_id
        destination_world = records[mapping.destination_anchor].world_id
        if source_world != destination_world or source_world != mapping.stratum.world_id:
            raise V023SealedSourceProviderError(
                "matched-placebo mapping leaks across worlds"
            )
    ladder = _load_ladder_module()
    source_class = getattr(ladder, "AuthenticatedV023Source", None)
    if source_class is None:
        raise V023SealedSourceProviderError(
            "post-Gate ladder does not expose AuthenticatedV023Source"
        )
    shared = {
        "source_manifest_sha256": panel.source_manifest_sha256,
        "source_manifest_file_sha256": panel.source_manifest_file_sha256,
        "result_sha256": result_sha,
        "result_manifest_sha256": result_manifest_sha,
        "provider_id": provider_id,
        "update_budget": V023_POSTGATE_UPDATE_BUDGET,
    }
    try:
        informed = source_class(
            arm="INFORMED",
            surfaces=tuple(record.surface for record in records),
            **shared,
        )
        neutral = source_class(
            arm="NEUTRAL_SOURCE",
            surfaces=tuple(record.surface for record in records),
            normalized_targets_by_anchor=placebo.normalized_targets_by_anchor,
            **shared,
        )
    except Exception as error:
        raise V023SealedSourceProviderError(
            f"authenticated source arm construction failed: {error}"
        ) from error
    if informed.source_row_count != neutral.source_row_count:
        raise V023SealedSourceProviderError(
            "INFORMED and NEUTRAL_SOURCE row budgets disagree"
        )
    if informed.update_budget != neutral.update_budget:
        raise V023SealedSourceProviderError(
            "INFORMED and NEUTRAL_SOURCE update budgets disagree"
        )
    if informed.source_anchor_sha256s != neutral.source_anchor_sha256s:
        raise V023SealedSourceProviderError(
            "INFORMED and NEUTRAL_SOURCE anchor source differs"
        )
    return {"INFORMED": informed, "NEUTRAL_SOURCE": neutral}


def derive_v023_postgate_sources(
    panel: SealedV023SourcePanel,
    *,
    result_sha256: str,
    result_manifest_sha256: str,
    provider_id: str = SEALED_V023_PROVIDER_SCHEMA,
) -> dict[str, object]:
    """Alias emphasizing that the neutral arm is derived from Gate placebo."""

    return build_authenticated_v023_sources(
        panel,
        result_sha256=result_sha256,
        result_manifest_sha256=result_manifest_sha256,
        provider_id=provider_id,
    )


class SealedV023SourceProvider:
    """External provider for sealed V0.23 INFORMED/NEUTRAL_SOURCE inputs.

    Construction stores paths only.  ``provide`` is the first operation that
    reads any artifact and it re-authenticates the complete source and result
    trees on every call.  The ``student_seed`` argument is identity-only; it
    never affects source construction or target generation.
    """

    def __init__(
        self,
        *,
        source_directory: str | Path,
        source_manifest: str | Path,
        preflight_manifest_sha256: str,
        result_directory: str | Path | None = None,
        result_path: str | Path | None = None,
        result_manifest_path: str | Path | None = None,
        complete_path: str | Path | None = None,
        provider_id: str = SEALED_V023_PROVIDER_SCHEMA,
    ) -> None:
        self.source_directory = Path(source_directory)
        self.source_manifest = Path(source_manifest)
        self.preflight_manifest_sha256 = _digest(
            preflight_manifest_sha256,
            field="preflight_manifest_sha256",
        )
        self.result_directory = Path(
            result_directory
            if result_directory is not None
            else self.source_directory
        )
        self.result_path = Path(
            result_path if result_path is not None else self.result_directory / "result.json"
        )
        self.result_manifest_path = Path(
            result_manifest_path
            if result_manifest_path is not None
            else self.result_directory / "MANIFEST.sha256"
        )
        self.complete_path = Path(
            complete_path
            if complete_path is not None
            else self.result_directory / "COMPLETE"
        )
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise V023SealedSourceProviderError("provider_id must be nonempty")
        self.provider_id = provider_id

    def _load_bundle(self) -> dict[str, object]:
        source_root = _regular_directory(
            self.source_directory,
            field="source directory",
        )
        result_root = _regular_directory(
            self.result_directory,
            field="result directory",
        )
        manifest = _regular_file(self.source_manifest, field="source manifest")
        result = _regular_file(self.result_path, field="result receipt")
        result_manifest = _regular_file(
            self.result_manifest_path,
            field="result MANIFEST.sha256",
        )
        complete = _regular_file(self.complete_path, field="result COMPLETE")
        if not manifest.is_relative_to(source_root):
            raise V023SealedSourceProviderError(
                "source manifest escapes source directory"
            )
        for path, field in (
            (result, "result receipt"),
            (result_manifest, "result MANIFEST.sha256"),
            (complete, "result COMPLETE"),
        ):
            if not path.is_relative_to(result_root):
                raise V023SealedSourceProviderError(f"{field} escapes result directory")
        panel = load_sealed_v023_source_panel(
            source_directory=source_root,
            source_manifest=manifest,
            preflight_manifest_sha256=self.preflight_manifest_sha256,
        )
        result_payload, result_sha, result_manifest_sha = _verify_result_manifest(
            result_directory=result_root,
            result_path=result,
            result_manifest_path=result_manifest,
            complete_path=complete,
        )
        _verify_closed_result(
            result_payload,
            source_manifest_sha256=panel.source_manifest_sha256,
            source_manifest_file_sha256=panel.source_manifest_file_sha256,
            preflight_manifest_sha256=panel.preflight_manifest_sha256,
            result_manifest_sha256=result_manifest_sha,
            source_row_count=panel.source_row_count,
        )
        sources = build_authenticated_v023_sources(
            panel,
            result_sha256=result_sha,
            result_manifest_sha256=result_manifest_sha,
            provider_id=self.provider_id,
        )
        return sources

    def provide(self, *, arm: str, student_seed: int) -> object:
        if arm not in V023_POSTGATE_ARMS:
            raise V023SealedSourceProviderError(
                "source arm must be INFORMED or NEUTRAL_SOURCE"
            )
        if type(student_seed) is not int or student_seed not in V023_STUDENT_SEEDS:
            raise V023SealedSourceProviderError(
                "student seed is outside the frozen V0.23 panel"
            )
        sources = self._load_bundle()
        return sources[arm]

    load = provide
    resolve = provide


V023SealedSourceProvider = SealedV023SourceProvider
AuthenticatedV023SourceProviderAdapter = SealedV023SourceProvider


def load_sealed_v023_source_bundle(
    *,
    source_directory: str | Path,
    source_manifest: str | Path,
    preflight_manifest_sha256: str,
    result_directory: str | Path | None = None,
    result_path: str | Path | None = None,
    result_manifest_path: str | Path | None = None,
    complete_path: str | Path | None = None,
    provider_id: str = SEALED_V023_PROVIDER_SCHEMA,
) -> dict[str, object]:
    """Load both authenticated arms without choosing or evaluating either."""

    provider = SealedV023SourceProvider(
        source_directory=source_directory,
        source_manifest=source_manifest,
        preflight_manifest_sha256=preflight_manifest_sha256,
        result_directory=result_directory,
        result_path=result_path,
        result_manifest_path=result_manifest_path,
        complete_path=complete_path,
        provider_id=provider_id,
    )
    return provider._load_bundle()


__all__ = [
    "SEALED_V023_PROVIDER_SCHEMA",
    "SEALED_SOURCE_PROVIDER_SCHEMA",
    "V023_GATE_SOURCE_MANIFEST_SCHEMA",
    "V023_GATE_RESULT_SCHEMAS",
    "V023_GATE_RESULT_STATUSES",
    "V023_GATE_WORLDS",
    "V023_STUDENT_SEEDS",
    "V023_POSTGATE_UPDATE_BUDGET",
    "V023_POSTGATE_ARMS",
    "V023_POSTGATE_CLAIM_CEILING",
    "V023SealedSourceProviderError",
    "SealedV023SourceProviderError",
    "SealedV023SourcePanel",
    "load_sealed_v023_source_panel",
    "build_authenticated_v023_sources",
    "derive_v023_postgate_sources",
    "SealedV023SourceProvider",
    "V023SealedSourceProvider",
    "AuthenticatedV023SourceProviderAdapter",
    "load_sealed_v023_source_bundle",
    "canonical_sha256",
    "file_sha256",
]
