#!/usr/bin/env python3
"""Staged V0.23 LC-SRS observability-gate runner scaffold.

The gate is intentionally split into independently resumable units:

* ``source``: one all-pairs/controls source-generation shard per world;
* ``fit``: one LOO fold x student seed x arm shard (48 total); and
* ``merge``: deterministic completeness/decision assembly.

This file owns the scheduling, identity, atomic-output, and fail-closed
boundaries.  It does not create a simulator, open TLE, evaluate profiles, fit a
learner, or open TEST by itself.  A separately audited server adapter may be
injected into the Python stage functions and must return receipts to the typed
``write_*_shard`` functions.  Calling a physical stage without such an adapter
is an explicit error rather than an implicit fallback.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping, Protocol, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PREFLIGHT_NAME = "PREFLIGHT-MANIFEST.json"
PREFLIGHT_DIGEST_NAME = "PREFLIGHT-MANIFEST.sha256"
CONTRACT = REPO / "docs" / "MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md"
CONTRACT_SHA256 = "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
WORLDS = tuple(range(2026121705, 2026121713))
STUDENT_SEEDS = (2026135101, 2026135102, 2026135103)
ARMS = ("INFORMED", "MATCHED_PLACEBO")
FOLD_COUNT = 8
DRAW_COUNT = 32
STEPS_PER_EPISODE = 10
USERS = 100
ACTIONS = 28
FIT_UPDATES = 2000
FIELD_COMPONENT = "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1"
SCHEMA = "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1"
SOURCE_SCHEMA = f"{SCHEMA}-source-shard"
SOURCE_MANIFEST_SCHEMA = f"{SCHEMA}-source-manifest"
FIT_SCHEMA = f"{SCHEMA}-fit-shard"
MERGE_SCHEMA = f"{SCHEMA}-merge-receipt"
PLAN_SCHEMA = f"{SCHEMA}-plan"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)


class V023GateError(RuntimeError):
    """The staged V0.23 gate boundary or a shard receipt was violated."""


class V023PhysicalSourceAdapter(Protocol):
    """Future server-only adapter for one complete world source shard."""

    def generate_source_shard(self, spec: "SourceShardSpec") -> Mapping[str, Any]:
        """Return a complete source receipt; this scaffold supplies no adapter."""


class V023LearnerAdapter(Protocol):
    """Future server-only adapter for one fit/evaluation shard."""

    def fit_shard(self, spec: "FitShardSpec") -> Mapping[str, Any]:
        """Return one complete informed/placebo fit receipt."""


@dataclass(frozen=True)
class SourceShardSpec:
    world: int
    output: Path
    preflight_manifest_sha256: str | None = None


@dataclass(frozen=True)
class FitShardSpec:
    held_out_world: int
    student_seed: int
    arm: str
    source_directory: Path
    output: Path
    source_manifest: Path | None = None
    preflight_manifest_sha256: str | None = None


@dataclass(frozen=True)
class GatePlan:
    """Pure schedule description; constructing it performs no external I/O."""

    worlds: tuple[int, ...] = WORLDS
    student_seeds: tuple[int, ...] = STUDENT_SEEDS
    arms: tuple[str, ...] = ARMS
    draw_count: int = DRAW_COUNT
    steps_per_episode: int = STEPS_PER_EPISODE
    fold_count: int = FOLD_COUNT
    fit_updates: int = FIT_UPDATES
    split: str = "TRAIN_DEVELOPMENT"
    test_split_opened: bool = False
    episode_training: bool = False

    @property
    def source_count(self) -> int:
        return len(self.worlds)

    @property
    def fit_count(self) -> int:
        return len(self.worlds) * len(self.student_seeds) * len(self.arms)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PLAN_SCHEMA,
            "contract_sha256": CONTRACT_SHA256,
            "claim_ceiling": CLAIM_CEILING,
            "split": self.split,
            "worlds": list(self.worlds),
            "student_seeds": list(self.student_seeds),
            "arms": list(self.arms),
            "draw_count": self.draw_count,
            "steps_per_episode": self.steps_per_episode,
            "fold_count": self.fold_count,
            "fit_updates": self.fit_updates,
            "source_count": self.source_count,
            "fit_count": self.fit_count,
            "source_manifest": "source-manifest.json",
            "test_split_opened": self.test_split_opened,
            "episode_training": self.episode_training,
            "source_shards": [
                {
                    "world": world,
                    "relative_name": f"source/world-{world}.json",
                }
                for world in self.worlds
            ],
            "fit_shards": [
                {
                    "held_out_world": world,
                    "student_seed": seed,
                    "arm": arm,
                    "relative_name": (
                        f"fit/world-{world}/seed-{seed}/{arm.lower()}.json"
                    ),
                }
                for world in self.worlds
                for seed in self.student_seeds
                for arm in self.arms
            ],
        }


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023GateError(f"expected regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023GateError(f"receipt is missing or non-regular: {source}")
    raw = source.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023GateError(f"receipt is not ASCII JSON: {source}") from error
    if not isinstance(value, dict):
        raise V023GateError(f"receipt root is not an object: {source}")
    canonical = _canonical_bytes(value)
    if raw not in (canonical, canonical + b"\n"):
        raise V023GateError(f"receipt is not canonical JSON: {source}")
    return value


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023GateError(f"{field} is not a lowercase SHA-256")
    return value


def _int(value: object, *, field: str) -> int:
    if type(value) is not int:
        raise V023GateError(f"{field} must be an exact integer")
    return value


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> Path:
    """Atomically create one canonical receipt and refuse overwrites."""

    target = Path(path)
    if target.exists() or target.is_symlink():
        raise V023GateError(f"refusing to overwrite existing output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_bytes(dict(payload))
    fd, temporary = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        try:
            Path(temporary).unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return target


def _validate_plan(plan: GatePlan) -> None:
    if plan.worlds != WORLDS:
        raise V023GateError("world panel is not the frozen eight-world panel")
    if plan.student_seeds != STUDENT_SEEDS:
        raise V023GateError("student seed panel drifted")
    if plan.arms != ARMS:
        raise V023GateError("learner arm panel drifted")
    if plan.draw_count != DRAW_COUNT or plan.steps_per_episode != STEPS_PER_EPISODE:
        raise V023GateError("draw count or episode length drifted")
    if plan.fold_count != FOLD_COUNT or plan.fit_updates != FIT_UPDATES:
        raise V023GateError("fold count or learner update count drifted")
    if plan.split != "TRAIN_DEVELOPMENT":
        raise V023GateError("only TRAIN_DEVELOPMENT is permitted")
    if plan.test_split_opened or plan.episode_training:
        raise V023GateError("TEST and episode training are closed in this gate")


def build_plan() -> GatePlan:
    plan = GatePlan()
    _validate_plan(plan)
    return plan


def emit_plan(output: Path) -> dict[str, Any]:
    """Write a deterministic plan receipt without loading runtime modules."""

    plan = build_plan()
    payload = plan.to_dict()
    payload["plan_sha256"] = canonical_sha256(payload)
    _write_new_json(output, payload)
    return payload


def _validate_common_receipt(
    receipt: Mapping[str, Any], *, schema: str, preflight_sha256: str
) -> None:
    if receipt.get("schema") != schema:
        raise V023GateError(f"receipt schema is not {schema}")
    if receipt.get("claim_ceiling") != CLAIM_CEILING:
        raise V023GateError("receipt claim ceiling disagrees with frozen boundary")
    if receipt.get("contract_sha256") != CONTRACT_SHA256:
        raise V023GateError("receipt contract hash disagrees with frozen contract")
    if receipt.get("preflight_manifest_sha256") != preflight_sha256:
        raise V023GateError("receipt preflight hash disagrees with current manifest")
    if receipt.get("split") != "TRAIN_DEVELOPMENT":
        raise V023GateError("receipt is not TRAIN_DEVELOPMENT")
    if receipt.get("test_split_opened") is not False:
        raise V023GateError("receipt opened TEST")
    if receipt.get("episode_training") is not False:
        raise V023GateError("receipt performed episode training")
    learner_update = receipt.get("learner_update")
    if schema == SOURCE_SCHEMA and learner_update is not False:
        raise V023GateError("source receipt must attest learner_update=false")
    if schema == FIT_SCHEMA and learner_update is not True:
        raise V023GateError("fit receipt must attest learner_update=true")


def _payload_with_seal(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["receipt_sha256"] = canonical_sha256(result)
    return result


def validate_source_shard(
    payload: Mapping[str, Any], *, world: int, preflight_sha256: str
) -> dict[str, Any]:
    _validate_common_receipt(payload, schema=SOURCE_SCHEMA, preflight_sha256=preflight_sha256)
    if _int(payload.get("world"), field="world") != world or world not in WORLDS:
        raise V023GateError("source shard world is outside the frozen panel")
    if payload.get("status") != "PASS":
        raise V023GateError("source shard is not complete PASS")
    required = {
        "enumeration_sha256",
        "topology_sha256",
        "teacher_sha256",
        "surface_sha256",
        "record_count",
        "pair_count",
        "supported_count",
        "placebo_eligible_count",
    }
    missing = sorted(name for name in required if name not in payload)
    if missing:
        raise V023GateError("source shard omits required receipt fields: " + ", ".join(missing))
    for field in (
        "enumeration_sha256",
        "topology_sha256",
        "teacher_sha256",
        "surface_sha256",
    ):
        _digest(payload[field], field=field)
    for field in ("record_count", "pair_count", "supported_count", "placebo_eligible_count"):
        if _int(payload[field], field=field) < 0:
            raise V023GateError(f"{field} cannot be negative")
    return dict(payload)


def _expected_source_entries(source_root: Path) -> list[dict[str, Any]]:
    """Return the canonical source-shard paths for the frozen world panel."""

    root = Path(source_root).resolve()
    return [
        {
            "world": world,
            "path": (root / "source" / f"world-{world}.json").relative_to(root).as_posix(),
        }
        for world in WORLDS
    ]


def validate_source_manifest(
    payload: Mapping[str, Any], *, preflight_sha256: str
) -> dict[str, Any]:
    """Validate the deterministic manifest emitted after all source shards.

    The manifest hash is the canonical hash of the unsigned manifest body.  It
    is therefore available to fit workers before any fit shard is started and
    cannot depend on a later merge.
    """

    if payload.get("schema") != SOURCE_MANIFEST_SCHEMA:
        raise V023GateError("source manifest schema drifted")
    if payload.get("status") != "PASS":
        raise V023GateError("source manifest is not complete PASS")
    if payload.get("claim_ceiling") != CLAIM_CEILING:
        raise V023GateError("source manifest claim ceiling drifted")
    if payload.get("contract_sha256") != CONTRACT_SHA256:
        raise V023GateError("source manifest contract hash disagrees")
    if payload.get("preflight_manifest_sha256") != preflight_sha256:
        raise V023GateError("source manifest preflight hash disagrees")
    if payload.get("split") != "TRAIN_DEVELOPMENT":
        raise V023GateError("source manifest is not TRAIN_DEVELOPMENT")
    if payload.get("test_split_opened") is not False:
        raise V023GateError("source manifest opened TEST")
    if payload.get("episode_training") is not False:
        raise V023GateError("source manifest performed episode training")
    if payload.get("learner_update") is not False:
        raise V023GateError("source manifest performed a learner update")
    if payload.get("source_count") != len(WORLDS):
        raise V023GateError("source manifest source count drifted")
    shards = payload.get("shards")
    if not isinstance(shards, list):
        raise V023GateError("source manifest shards are not a list")
    expected = [
        {"world": world, "relative_name": f"source/world-{world}.json"}
        for world in WORLDS
    ]
    if shards != expected:
        raise V023GateError("source manifest shard schedule drifted")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != len(WORLDS):
        raise V023GateError("source manifest entries are incomplete")
    for item, expected_item in zip(entries, expected, strict=True):
        if not isinstance(item, Mapping):
            raise V023GateError("source manifest entry is not an object")
        if item.get("world") != expected_item["world"]:
            raise V023GateError("source manifest entry world order drifted")
        if item.get("relative_name") != expected_item["relative_name"]:
            raise V023GateError("source manifest entry path drifted")
        _digest(item.get("sha256"), field="source manifest entry sha256")
    source_hash = payload.get("source_manifest_sha256")
    _digest(source_hash, field="source_manifest_sha256")
    unsigned = dict(payload)
    unsigned.pop("source_manifest_sha256", None)
    unsigned.pop("manifest_sha256", None)
    if canonical_sha256(unsigned) != source_hash:
        raise V023GateError("source manifest hash disagrees with canonical body")
    manifest_hash = payload.get("manifest_sha256")
    _digest(manifest_hash, field="manifest_sha256")
    unsigned_manifest = dict(payload)
    unsigned_manifest.pop("manifest_sha256", None)
    if canonical_sha256(unsigned_manifest) != manifest_hash:
        raise V023GateError("source manifest seal disagrees with bytes")
    return dict(payload)


def emit_source_manifest(
    *,
    source_directory: Path,
    output: Path,
    preflight_sha256: str,
) -> dict[str, Any]:
    """Verify all eight source receipts and publish their fit-input manifest."""

    plan = build_plan()
    source_root = Path(source_directory).resolve()
    if not Path(output).resolve().is_relative_to(source_root):
        raise V023GateError("source manifest output must live under source directory")
    entries: list[dict[str, Any]] = []
    for world in plan.worlds:
        path = source_root / "source" / f"world-{world}.json"
        payload = _load_json(path)
        validate_source_shard(payload, world=world, preflight_sha256=preflight_sha256)
        entries.append(
            {
                "world": world,
                "relative_name": f"source/world-{world}.json",
                "sha256": file_sha256(path),
            }
        )
    body: dict[str, Any] = {
        "schema": SOURCE_MANIFEST_SCHEMA,
        "status": "PASS",
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": CONTRACT_SHA256,
        "preflight_manifest_sha256": preflight_sha256,
        "split": "TRAIN_DEVELOPMENT",
        "worlds": list(plan.worlds),
        "source_count": len(entries),
        "shards": [
            {"world": item["world"], "relative_name": item["relative_name"]}
            for item in entries
        ],
        "entries": entries,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    body["source_manifest_sha256"] = canonical_sha256(body)
    body["manifest_sha256"] = canonical_sha256(body)
    _write_new_json(output, body)
    return body


def validate_fit_shard(
    payload: Mapping[str, Any],
    *,
    held_out_world: int,
    student_seed: int,
    arm: str,
    preflight_sha256: str,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    _validate_common_receipt(payload, schema=FIT_SCHEMA, preflight_sha256=preflight_sha256)
    if held_out_world not in WORLDS or _int(payload.get("held_out_world"), field="held_out_world") != held_out_world:
        raise V023GateError("fit shard held-out world drifted")
    if student_seed not in STUDENT_SEEDS or _int(payload.get("student_seed"), field="student_seed") != student_seed:
        raise V023GateError("fit shard student seed drifted")
    if arm not in ARMS or payload.get("arm") != arm:
        raise V023GateError("fit shard learner arm drifted")
    if payload.get("source_manifest_sha256") != source_manifest_sha256:
        raise V023GateError("fit shard source manifest drifted")
    if payload.get("status") != "PASS":
        raise V023GateError("fit shard is not complete PASS")
    if _int(payload.get("update_count"), field="update_count") != FIT_UPDATES:
        raise V023GateError("fit shard update count drifted")
    if payload.get("test_worlds") not in ([], None):
        raise V023GateError("fit shard declares TEST worlds")
    for field in ("model_sha256", "metrics_sha256", "source_manifest_sha256"):
        _digest(payload[field], field=field)
    return dict(payload)


def write_source_shard(
    spec: SourceShardSpec,
    *,
    payload: Mapping[str, Any],
    preflight_sha256: str,
) -> Path:
    """Validate and atomically persist one source-generation result."""

    if "receipt_sha256" in payload:
        raise V023GateError(
            "source adapter must not provide receipt_sha256; the shard writer owns the seal"
        )
    validated = validate_source_shard(
        payload, world=spec.world, preflight_sha256=preflight_sha256
    )
    return _write_new_json(spec.output, _payload_with_seal(validated))


def write_fit_shard(
    spec: FitShardSpec,
    *,
    payload: Mapping[str, Any],
    preflight_sha256: str,
    source_manifest_sha256: str,
) -> Path:
    """Validate and atomically persist one fold/seed/arm result."""

    if "receipt_sha256" in payload:
        raise V023GateError(
            "learner adapter must not provide receipt_sha256; the shard writer owns the seal"
        )
    validated = validate_fit_shard(
        payload,
        held_out_world=spec.held_out_world,
        student_seed=spec.student_seed,
        arm=spec.arm,
        preflight_sha256=preflight_sha256,
        source_manifest_sha256=source_manifest_sha256,
    )
    return _write_new_json(spec.output, _payload_with_seal(validated))


def _relative_under(path: Path, root: Path, *, field: str) -> Path:
    root_resolved = Path(root).resolve()
    path_resolved = Path(path).resolve()
    if not path_resolved.is_relative_to(root_resolved):
        raise V023GateError(f"{field} escapes its shard root")
    return path_resolved


def _load_validated_source_manifest(
    *,
    source_manifest: Path,
    source_root: Path,
    preflight_sha256: str,
) -> dict[str, Any]:
    """Validate a source manifest and reopen every source child receipt."""

    root = Path(source_root).resolve()
    manifest_path = Path(source_manifest).resolve()
    if not manifest_path.is_relative_to(root):
        raise V023GateError("source manifest must live under the source directory")
    payload = validate_source_manifest(
        _load_json(manifest_path), preflight_sha256=preflight_sha256
    )
    entries = payload["entries"]
    for world, item in zip(WORLDS, entries, strict=True):
        if not isinstance(item, Mapping):
            raise V023GateError("source manifest entry is not an object")
        relative_name = item["relative_name"]
        if not isinstance(relative_name, str):
            raise V023GateError("source manifest entry path is not a string")
        path = _relative_under(root / relative_name, root, field="source child")
        if file_sha256(path) != item["sha256"]:
            raise V023GateError(f"source manifest child hash disagrees for world {world}")
        validate_source_shard(
            _load_json(path), world=world, preflight_sha256=preflight_sha256
        )
    return payload


def merge_shards(
    *,
    source_directory: Path,
    fit_directory: Path,
    output: Path,
    preflight_sha256: str,
    source_manifest: Path | None = None,
) -> dict[str, Any]:
    """Verify complete shard coverage and emit a no-claim merge receipt.

    The merge stage deliberately does not infer a scientific decision from
    summary numbers.  The future physical/learner adapter must provide the
    independently recomputable predicate table before this receipt can be
    promoted to a gate result.
    """

    plan = build_plan()
    source_root = Path(source_directory).resolve()
    fit_root = Path(fit_directory).resolve()
    if source_manifest is None:
        raise V023GateError(
            "merge requires the source-manifest stage; it cannot construct the fit input hash retroactively"
        )
    source_manifest_path = Path(source_manifest).resolve()
    source_manifest_payload = _load_validated_source_manifest(
        source_manifest=source_manifest_path,
        source_root=source_root,
        preflight_sha256=preflight_sha256,
    )
    source_manifest_sha256 = source_manifest_payload["source_manifest_sha256"]
    declared_entries = source_manifest_payload.get("entries")
    if not isinstance(declared_entries, list) or len(declared_entries) != len(plan.worlds):
        raise V023GateError("source manifest entries are incomplete")
    source_receipts: list[dict[str, Any]] = []
    source_entries: list[dict[str, Any]] = []
    for world in plan.worlds:
        path = _relative_under(
            source_root / "source" / f"world-{world}.json",
            source_root,
            field="source shard",
        )
        payload = _load_json(path)
        validate_source_shard(payload, world=world, preflight_sha256=preflight_sha256)
        declared = next(
            (
                item
                for item in declared_entries
                if isinstance(item, Mapping) and item.get("world") == world
            ),
            None,
        )
        if not isinstance(declared, Mapping):
            raise V023GateError(f"source manifest omits world {world}")
        if declared.get("relative_name") != path.relative_to(source_root).as_posix():
            raise V023GateError(f"source manifest path disagrees for world {world}")
        if declared.get("sha256") != file_sha256(path):
            raise V023GateError(f"source manifest hash disagrees for world {world}")
        source_receipts.append(payload)
        source_entries.append(
            {"world": world, "path": path.relative_to(source_root).as_posix(), "sha256": file_sha256(path)}
        )

    fit_receipts: list[dict[str, Any]] = []
    fit_entries: list[dict[str, Any]] = []
    for world in plan.worlds:
        for seed in plan.student_seeds:
            for arm in plan.arms:
                path = _relative_under(
                    fit_root / "fit" / f"world-{world}" / f"seed-{seed}" / f"{arm.lower()}.json",
                    fit_root,
                    field="fit shard",
                )
                payload = _load_json(path)
                validate_fit_shard(
                    payload,
                    held_out_world=world,
                    student_seed=seed,
                    arm=arm,
                    preflight_sha256=preflight_sha256,
                    source_manifest_sha256=source_manifest_sha256,
                )
                fit_receipts.append(payload)
                fit_entries.append(
                    {
                        "held_out_world": world,
                        "student_seed": seed,
                        "arm": arm,
                        "path": path.relative_to(fit_root).as_posix(),
                        "sha256": file_sha256(path),
                    }
                )

    payload: dict[str, Any] = {
        "schema": MERGE_SCHEMA,
        "status": "READY_FOR_INDEPENDENT_DECISION",
        "decision": None,
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": CONTRACT_SHA256,
        "preflight_manifest_sha256": preflight_sha256,
        "split": "TRAIN_DEVELOPMENT",
        "worlds": list(plan.worlds),
        "student_seeds": list(plan.student_seeds),
        "arms": list(plan.arms),
        "source_count": len(source_receipts),
        "fit_count": len(fit_receipts),
        "source_manifest": source_manifest_payload,
        "source_manifest_sha256": source_manifest_sha256,
        "source_shards": source_entries,
        "fit_shards": fit_entries,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "scientific_decision_opened": False,
        "note": "Scaffold merge only; no physical or learner result is claimed.",
    }
    sealed = _payload_with_seal(payload)
    _write_new_json(output, sealed)
    return sealed


def run_source_stage(
    spec: SourceShardSpec,
    *,
    adapter: V023PhysicalSourceAdapter | None,
) -> Path:
    """Run one source shard through an explicitly supplied server adapter.

    The CLI still supplies no adapter in this WSL-safe scaffold.  The Python
    seam is intentionally live, however: a server worker can inject an
    audited adapter and the writer will validate/seal its receipt atomically.
    """

    if adapter is None:
        raise V023GateError(
            "source stage is scaffold-only: no physical adapter is wired; "
            "no simulator or TLE was opened"
        )
    payload = adapter.generate_source_shard(spec)
    if not isinstance(payload, Mapping):
        raise V023GateError("physical source adapter did not return a mapping")
    preflight_sha256 = spec.preflight_manifest_sha256 or payload.get(
        "preflight_manifest_sha256"
    )
    _digest(preflight_sha256, field="preflight_manifest_sha256")
    return write_source_shard(
        spec,
        payload=payload,
        preflight_sha256=preflight_sha256,
    )


def run_fit_stage(
    spec: FitShardSpec,
    *,
    adapter: V023LearnerAdapter | None,
) -> Path:
    """Run one fit shard through an explicitly supplied server adapter."""

    if adapter is None:
        raise V023GateError(
            "fit stage is scaffold-only: no learner adapter is wired; "
            "no model update was performed"
        )
    if spec.source_manifest is None:
        raise V023GateError(
            "fit stage requires the source-manifest stage before fitting"
        )
    source_manifest_path = Path(spec.source_manifest).resolve()
    source_manifest_raw = _load_json(source_manifest_path)
    # The source manifest's preflight hash is the same frozen input used by
    # the fit adapter.  Verifying every child here makes a fit shard
    # independently resumable and prevents stale/partial source roots.
    preflight_sha256 = spec.preflight_manifest_sha256 or source_manifest_raw.get(
        "preflight_manifest_sha256"
    )
    _digest(preflight_sha256, field="preflight_manifest_sha256")
    source_manifest = _load_validated_source_manifest(
        source_manifest=source_manifest_path,
        source_root=spec.source_directory,
        preflight_sha256=preflight_sha256,
    )
    source_manifest_sha256 = source_manifest["source_manifest_sha256"]
    payload = adapter.fit_shard(spec)
    if not isinstance(payload, Mapping):
        raise V023GateError("learner adapter did not return a mapping")
    return write_fit_shard(
        spec,
        payload=payload,
        preflight_sha256=preflight_sha256,
        source_manifest_sha256=source_manifest_sha256,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="stage", required=True)
    plan = sub.add_parser("plan", help="emit the frozen staged schedule only")
    plan.add_argument("--output", type=Path, required=True)
    source = sub.add_parser("source", help="run one injected physical source adapter")
    source.add_argument("--world", type=int, choices=WORLDS, required=True)
    source.add_argument("--output", type=Path, required=True)
    source.add_argument("--preflight-sha256", required=True)
    source_manifest = sub.add_parser(
        "source-manifest",
        help="verify all source shards and emit the fit-input manifest",
    )
    source_manifest.add_argument("--source-directory", type=Path, required=True)
    source_manifest.add_argument("--output", type=Path, required=True)
    source_manifest.add_argument("--preflight-sha256", required=True)
    fit = sub.add_parser("fit", help="run one injected learner adapter")
    fit.add_argument("--held-out-world", type=int, choices=WORLDS, required=True)
    fit.add_argument("--student-seed", type=int, choices=STUDENT_SEEDS, required=True)
    fit.add_argument("--arm", choices=ARMS, required=True)
    fit.add_argument("--source-directory", type=Path, required=True)
    fit.add_argument("--source-manifest", type=Path, required=True)
    fit.add_argument("--preflight-sha256", required=True)
    fit.add_argument("--output", type=Path, required=True)
    merge = sub.add_parser("merge", help="verify all shard receipts and emit merge scaffold")
    merge.add_argument("--source-directory", type=Path, required=True)
    merge.add_argument("--fit-directory", type=Path, required=True)
    merge.add_argument("--source-manifest", type=Path, required=True)
    merge.add_argument("--output", type=Path, required=True)
    merge.add_argument("--preflight-sha256", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.stage == "plan":
        emit_plan(args.output)
        print(f"PLAN_ONLY: {args.output}")
        return 0
    if args.stage == "source":
        # No dynamic import is performed by the safe CLI.  A server launcher
        # should call run_source_stage(..., adapter=...) from Python after an
        # explicit launch contract is authenticated.
        run_source_stage(
            SourceShardSpec(
                args.world,
                args.output,
                preflight_manifest_sha256=args.preflight_sha256,
            ),
            adapter=None,
        )
    elif args.stage == "source-manifest":
        emit_source_manifest(
            source_directory=args.source_directory,
            output=args.output,
            preflight_sha256=_digest(
                args.preflight_sha256, field="preflight_sha256"
            ),
        )
        print(f"SOURCE_MANIFEST_PASS: {args.output}")
        return 0
    elif args.stage == "fit":
        run_fit_stage(
            FitShardSpec(
                args.held_out_world,
                args.student_seed,
                args.arm,
                args.source_directory,
                args.output,
                source_manifest=args.source_manifest,
                preflight_manifest_sha256=args.preflight_sha256,
            ),
            adapter=None,
        )
    elif args.stage == "merge":
        merge_shards(
            source_directory=args.source_directory,
            fit_directory=args.fit_directory,
            output=args.output,
            preflight_sha256=_digest(args.preflight_sha256, field="preflight_sha256"),
            source_manifest=args.source_manifest,
        )
        print(f"MERGE_READY_FOR_INDEPENDENT_DECISION: {args.output}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
