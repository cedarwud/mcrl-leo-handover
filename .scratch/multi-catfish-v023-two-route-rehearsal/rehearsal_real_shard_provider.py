"""Authenticated, deterministic C1/C2 provider for non-formal rehearsals.

Every completed shard is authenticated independently by the producer
controller before the target adapter performs typed loading.
The provider deliberately tolerates different world sets in the informed and
neutral mode directories; it never manufactures or substitutes a missing
world.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import MappingProxyType, ModuleType
from typing import Any

import numpy as np

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v014_head import EEAxisV014NormalizedPairBatch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ADAPTER_DIR = REPO / ".scratch/multi-catfish-v023-target-batch-adapter"
CONTROLLER_DIR = REPO / ".scratch/multi-catfish-v023-c1c2-target-generation-launch"
TWO_ROUTE_DIR = REPO / ".scratch/multi-catfish-v023-two-route-source-training-runner"
ADAPTER_PATH = ADAPTER_DIR / "target_batch_adapter.py"
CONTROLLER_PATH = CONTROLLER_DIR / "run_v023_c1c2_targets_server.py"
ORCHESTRATOR_PATH = TWO_ROUTE_DIR / "v023_two_route_learner_orchestrator.py"

for _directory in (ADAPTER_DIR, CONTROLLER_DIR, TWO_ROUTE_DIR):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

_TARGET = importlib.import_module("target_batch_adapter")
_CONTROLLER = importlib.import_module("run_v023_c1c2_targets_server")
_ORCHESTRATOR = importlib.import_module("v023_two_route_learner_orchestrator")
DeterministicRouteBatchProvider = _ORCHESTRATOR.DeterministicRouteBatchProvider
ProvidedRouteBatch = _ORCHESTRATOR.ProvidedRouteBatch

ROUTES = ("C1", "C2")
# This is the source-call order required by the two-route orchestrator and by
# factory v3's sampler state.
SOURCES = ("neutral", "informed")
DISCOVERY_MODES = ("informed", "neutral")
IDENTITY_SCHEMA = "multi-catfish-mcrl-v023-two-route-rehearsal-provider-identity-v1"
PROVIDER_SCHEMA = "multi-catfish-mcrl-v023-two-route-rehearsal-provider-v1"
SAMPLER_SCHEMA = "multi-catfish-mcrl-v023-two-route-rehearsal-provider-sampler-v1"
CLAIM_CEILING = "ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT"


class RehearsalShardProviderError(RuntimeError):
    """A rehearsal shard or deterministic request is inadmissible."""


def _fail(message: str, *, cause: BaseException | None = None) -> None:
    if cause is None:
        raise RehearsalShardProviderError(message)
    raise RehearsalShardProviderError(message) from cause


def _file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        _fail(f"not a regular file: {path}")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as cause:
        _fail(f"cannot hash file: {path}", cause=cause)
    return digest.hexdigest()


def _canonical_sha256(value: object) -> str:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as cause:
        _fail("provider identity is not canonically encodable", cause=cause)
    return hashlib.sha256(encoded).hexdigest()


def _require_adapter_primitives() -> None:
    for name in (
        "_validate_receipt_header",
        "_load_mode",
        "_aggregate_pair_batches",
    ):
        if not callable(getattr(_TARGET, name, None)):
            _fail(f"target adapter lacks required authenticated shard primitive {name}")


def _require_controller_primitives() -> None:
    for name in ("_canonical", "_read_receipt", "_validate_shard"):
        if not callable(getattr(_CONTROLLER, name, None)):
            _fail(f"target controller lacks required shard primitive {name}")


def _manifest_listing(shard_root: Path) -> dict[str, str]:
    """Parse the controller-authenticated flat shard manifest for the adapter."""

    manifest = shard_root / "MANIFEST.sha256"
    try:
        raw = manifest.read_bytes()
        text = raw.decode("ascii")
    except (OSError, UnicodeDecodeError) as cause:
        _fail(f"cannot read shard manifest: {manifest}", cause=cause)
    if not raw or not raw.endswith(b"\n") or b"\r" in raw:
        _fail(f"shard manifest must be newline-terminated ASCII with LF endings: {manifest}")
    listed: dict[str, str] = {}
    names: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.count("  ") != 1:
            _fail(f"shard manifest line {line_number} is malformed: {manifest}")
        digest, name = line.split("  ", 1)
        if (
            len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or Path(name).name != name
            or name in {"", ".", "..", "MANIFEST.sha256", "COMPLETE", "FAILED"}
            or "/" in name
            or "\\" in name
            or name in listed
        ):
            _fail(f"shard manifest line {line_number} is unsafe: {manifest}")
        listed[name] = digest
        names.append(name)
    if names != sorted(names) or "receipt.json" not in listed:
        _fail(f"shard manifest closure is not canonical: {manifest}")
    return listed


def _status_path(shard_root: Path, *, mode: str, world: int) -> Path:
    return (
        shard_root.parent.parent
        / "shard-status"
        / f"{mode}-world-{world}.terminal.json"
    )


def _status_evidence(
    shard_root: Path,
    *,
    mode: str,
    world: int,
) -> Mapping[str, Any] | None:
    """Authenticate the controller terminal receipt adjacent to a shard tree."""

    status_path = _status_path(shard_root, mode=mode, world=world)
    if not status_path.exists():
        return None
    if status_path.is_symlink() or not status_path.is_file():
        _fail(f"shard terminal status is not a regular file: {status_path}")
    try:
        raw = status_path.read_bytes()
        payload = json.loads(raw.decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as cause:
        _fail(f"shard terminal status is malformed: {status_path}", cause=cause)
    if not isinstance(payload, dict) or raw != _CONTROLLER._canonical(payload):
        _fail(f"shard terminal status is not canonical: {status_path}")
    if (
        payload.get("schema") != _CONTROLLER.SHARD_STATUS_SCHEMA
        or payload.get("event") != "terminal"
        or payload.get("mode") != mode
        or payload.get("world") != world
        or not isinstance(payload.get("state"), str)
        or not payload["state"]
    ):
        _fail(f"shard terminal status identity drifted: {status_path}")
    return MappingProxyType(
        {
            "path": str(status_path.resolve(strict=True)),
            "sha256": _file_sha256(status_path),
            "state": payload["state"],
        }
    )


def _module_origin(module: ModuleType, expected: Path, *, label: str) -> None:
    origin = getattr(module, "__file__", None)
    if not isinstance(origin, str) or Path(origin).resolve() != expected.resolve():
        _fail(f"{label} loaded from an unexpected origin")


def _snapshot_from_authenticated(
    shard_root: Path,
    listed: Mapping[str, str],
    status: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "manifest_sha256": _file_sha256(shard_root / "MANIFEST.sha256"),
        "receipt_sha256": _file_sha256(shard_root / "receipt.json"),
        "status_path": status["path"],
        "status_sha256": status["sha256"],
        "status_state": status["state"],
        "files": dict(listed),
    }


def _load_authenticated_shard(
    shard_root: Path,
    *,
    expected_mode: str,
) -> tuple[Any, Mapping[str, object], Mapping[str, Any]] | None:
    """Load one shard solely through the adapter's authenticated primitives."""

    _require_adapter_primitives()
    _require_controller_primitives()
    try:
        receipt = _CONTROLLER._read_receipt(shard_root)
        listed = _manifest_listing(shard_root)
        source, _formula, lambda_bits, interval = _TARGET._validate_receipt_header(
            receipt
        )
    except Exception as cause:
        _fail(
            f"controller manifest/receipt authentication rejected shard "
            f"{shard_root}: {cause}",
            cause=cause,
        )

    shard_identity = receipt.get("shard")
    if not isinstance(shard_identity, dict) or set(shard_identity) != {
        "mode",
        "world",
    }:
        _fail(f"shard receipt lacks exact mode/world identity: {shard_root}")
    mode = shard_identity["mode"]
    world = shard_identity["world"]
    if mode != expected_mode or type(world) is not int or world < 1:
        _fail(f"shard receipt mode/world disagrees with its mode directory: {shard_root}")
    key = f"{mode}:{world}"
    schedule = receipt.get("schedule")
    if (
        not isinstance(schedule, dict)
        or not isinstance(schedule.get("shards"), dict)
        or set(schedule["shards"]) != {key}
    ):
        _fail(f"shard receipt schedule is not single-shard exact: {shard_root}")
    expected = schedule["shards"][key]
    if not isinstance(expected, Mapping):
        _fail(f"shard receipt schedule entry is malformed: {shard_root}")
    status = _status_evidence(shard_root, mode=mode, world=world)
    if status is None:
        return None

    try:
        _CONTROLLER._validate_shard(key, shard_root, receipt, expected)
    except Exception as cause:
        _fail(
            f"controller validation rejected shard {shard_root}: {cause}",
            cause=cause,
        )

    try:
        inputs = _TARGET._load_mode(
            destination=shard_root,
            listed=listed,
            receipt=receipt,
            source=source,
            lambda_bits=lambda_bits,
            interval=interval,
            mode=expected_mode,
        )
    except Exception as cause:
        _fail(f"adapter typed loading rejected shard {shard_root}", cause=cause)
    if tuple(entry.world for entry in inputs.c1_datasets) != (world,) or tuple(
        entry.world for entry in inputs.c2_datasets
    ) != (world,):
        _fail(f"adapter returned a non-exact world from shard {shard_root}")
    return inputs, MappingProxyType(dict(receipt)), MappingProxyType(
        _snapshot_from_authenticated(shard_root, listed, status)
    )


def _immutable(value: np.ndarray, *, dtype: np.dtype[Any]) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _copy_batch(
    batch: EEAxisPairBatch | EEAxisV014NormalizedPairBatch,
) -> EEAxisPairBatch | EEAxisV014NormalizedPairBatch:
    """Copy a typed batch exactly as provider factory v3 does."""

    if isinstance(batch, EEAxisPairBatch):
        return EEAxisPairBatch(
            states=_immutable(batch.states, dtype=np.dtype(np.float32)),
            reference_actions=_immutable(
                batch.reference_actions, dtype=np.dtype(np.int64)
            ),
            candidate_actions=_immutable(
                batch.candidate_actions, dtype=np.dtype(np.int64)
            ),
            target_surplus_bits=_immutable(
                batch.target_surplus_bits, dtype=np.dtype(np.float64)
            ),
            action_masks=_immutable(batch.action_masks, dtype=np.dtype(np.bool_)),
        )
    if not isinstance(batch, EEAxisV014NormalizedPairBatch):
        _fail("adapter returned an unexpected route batch type")
    return EEAxisV014NormalizedPairBatch(
        states=_immutable(batch.states, dtype=np.dtype(np.float32)),
        reference_actions=_immutable(
            batch.reference_actions, dtype=np.dtype(np.int64)
        ),
        candidate_actions=_immutable(
            batch.candidate_actions, dtype=np.dtype(np.int64)
        ),
        # This is already-normalized target_delta.  There is intentionally no
        # kappa operation anywhere on the C2 provider path.
        normalized_target_deltas=_immutable(
            batch.normalized_target_deltas, dtype=np.dtype(np.float64)
        ),
        action_masks=_immutable(batch.action_masks, dtype=np.dtype(np.bool_)),
    )


def _panel_id(
    *,
    route: str,
    source: str,
    members: Sequence[str],
    batch: EEAxisPairBatch | EEAxisV014NormalizedPairBatch,
) -> str:
    """Use factory v3's byte-level panel identity algorithm."""

    digest = hashlib.sha256()
    digest.update(b"MCRL_V023_C1C2_SUCCESSOR_AUTHENTICATED_PANEL_V3\0")
    digest.update(route.encode("ascii") + b"\0" + source.encode("ascii"))
    for member in members:
        digest.update(b"\0" + member.encode("ascii"))
    for field in (
        "states",
        "reference_actions",
        "candidate_actions",
        "target_surplus_bits"
        if isinstance(batch, EEAxisPairBatch)
        else "normalized_target_deltas",
        "action_masks",
    ):
        value = np.ascontiguousarray(np.asarray(getattr(batch, field)))
        digest.update(b"\0" + field.encode("ascii"))
        digest.update(value.dtype.str.encode("ascii"))
        digest.update(np.asarray(value.shape, dtype=np.int64).tobytes())
        digest.update(value.tobytes())
    return f"{route.lower()}-{source}-rehearsal-panel-{digest.hexdigest()}"


class RehearsalRealShardProvider:
    """Deterministic provider over all currently completed real shards."""

    routes = ROUTES
    route_order = ROUTES

    def __init__(self, shard_root: str | Path, *, planned_epoch_budget: int) -> None:
        if (
            isinstance(planned_epoch_budget, bool)
            or not isinstance(planned_epoch_budget, int)
            or planned_epoch_budget < 1
        ):
            _fail("planned_epoch_budget must be a positive integer")
        root = Path(shard_root)
        if root.is_symlink() or not root.is_dir():
            _fail("shard root must be an existing non-symlink directory")
        if any(part.upper() == "TEST" for part in root.parts):
            _fail("TEST shard roots are forbidden")
        _module_origin(_TARGET, ADAPTER_PATH, label="target adapter")
        _module_origin(_CONTROLLER, CONTROLLER_PATH, label="target controller")
        _module_origin(_ORCHESTRATOR, ORCHESTRATOR_PATH, label="two-route orchestrator")

        self._root = root.resolve()
        self._planned_epoch_budget = planned_epoch_budget
        self._shards: dict[tuple[str, int], dict[str, Any]] = {}
        self._skipped_incomplete: list[str] = []
        self._skipped_shards: list[dict[str, str]] = []
        mode_inputs: dict[str, list[Any]] = {mode: [] for mode in DISCOVERY_MODES}

        for mode in DISCOVERY_MODES:
            mode_root = self._root / mode
            if mode_root.is_symlink() or not mode_root.is_dir():
                _fail(f"required mode directory is missing or unsafe: {mode_root}")
            for candidate in sorted(mode_root.iterdir(), key=lambda path: path.name):
                is_symlink = candidate.is_symlink()
                if is_symlink:
                    try:
                        resolved = candidate.resolve(strict=True)
                    except (OSError, RuntimeError) as cause:
                        _fail(
                            f"mode directory contains an unsafe symlink: {candidate}",
                            cause=cause,
                        )
                    if not resolved.is_dir():
                        _fail(
                            f"mode directory symlink does not resolve to a directory: "
                            f"{candidate}"
                        )
                elif not candidate.is_dir():
                    continue
                else:
                    resolved = candidate.resolve(strict=True)
                required = tuple(
                    resolved / name for name in ("MANIFEST.sha256", "receipt.json")
                )
                if not all(path.is_file() and not path.is_symlink() for path in required):
                    relative = candidate.relative_to(self._root).as_posix()
                    self._skipped_incomplete.append(relative)
                    self._skipped_shards.append(
                        {
                            "shard_dir": relative,
                            "reason": "missing regular MANIFEST.sha256 or receipt.json",
                        }
                    )
                    continue
                loaded = _load_authenticated_shard(
                    resolved, expected_mode=mode
                )
                if loaded is None:
                    relative = candidate.relative_to(self._root).as_posix()
                    self._skipped_incomplete.append(relative)
                    self._skipped_shards.append(
                        {
                            "shard_dir": relative,
                            "reason": "missing sibling shard terminal status file",
                        }
                    )
                    continue
                inputs, receipt, snapshot = loaded
                world = int(receipt["shard"]["world"])
                key = (mode, world)
                if key in self._shards:
                    _fail(f"duplicate completed shard for {mode} world {world}")
                relative = candidate.relative_to(self._root).as_posix()
                self._shards[key] = {
                    "root": resolved,
                    "relative": relative,
                    "entry_path": str(candidate),
                    "resolved_path": str(resolved),
                    "is_symlink": is_symlink,
                    "snapshot": snapshot,
                    "receipt": receipt,
                    "inputs": inputs,
                }
                mode_inputs[mode].append(inputs)

        if any(not values for values in mode_inputs.values()):
            _fail("rehearsal requires at least one authenticated shard in each mode")

        self._batches: dict[
            tuple[str, str], EEAxisPairBatch | EEAxisV014NormalizedPairBatch
        ] = {}
        self._source_members: dict[str, list[str]] = {}
        self._source_files: dict[str, list[str]] = {}
        for source in SOURCES:
            inputs_for_source = sorted(
                mode_inputs[source], key=lambda item: item.c1_datasets[0].world
            )
            c1_route_batches = tuple(
                batch
                for inputs in inputs_for_source
                for batch in inputs.c1_route_batches
            )
            c2_route_batches = tuple(
                batch
                for inputs in inputs_for_source
                for batch in inputs.c2_route_batches
            )
            try:
                aggregated = {
                    "C1": _TARGET._aggregate_pair_batches(
                        c1_route_batches, route="C1"
                    ),
                    "C2": _TARGET._aggregate_pair_batches(
                        c2_route_batches, route="C2"
                    ),
                }
            except Exception as cause:
                _fail(f"adapter aggregation rejected {source} shards", cause=cause)
            for route in ROUTES:
                members = [
                    f"{record['relative']}/{entry.path.name}"
                    for (mode, _world), record in sorted(
                        self._shards.items(), key=lambda item: item[0][1]
                    )
                    if mode == source
                    for entry in (
                        record["inputs"].c1_datasets
                        if route == "C1"
                        else record["inputs"].c2_datasets
                    )
                ]
                batch = aggregated[route]
                file_id = _panel_id(
                    route=route, source=source, members=members, batch=batch
                )
                self._batches[(route, source)] = batch
                self._source_members[f"{route}:{source}"] = members
                self._source_files[f"{route}:{source}"] = [file_id]

        worlds_used = {
            mode: sorted(world for shard_mode, world in self._shards if shard_mode == mode)
            for mode in DISCOVERY_MODES
        }
        shard_digests = [
            {
                "mode": mode,
                "world": world,
                "shard_dir": record["relative"],
                "entry_path": record["entry_path"],
                "resolved_path": record["resolved_path"],
                "is_symlink": record["is_symlink"],
                "manifest_sha256": record["snapshot"]["manifest_sha256"],
                "receipt_sha256": record["snapshot"]["receipt_sha256"],
                "status_path": record["snapshot"]["status_path"],
                "status_sha256": record["snapshot"]["status_sha256"],
                "status_state": record["snapshot"]["status_state"],
            }
            for (mode, world), record in sorted(
                self._shards.items(),
                key=lambda item: (DISCOVERY_MODES.index(item[0][0]), item[0][1]),
            )
        ]
        identity_payload = {
            "schema": IDENTITY_SCHEMA,
            "formal": False,
            "rehearsal": True,
            "claim_ceiling": CLAIM_CEILING,
            "routes": list(ROUTES),
            "sources": list(SOURCES),
            "shard_root": str(self._root),
            "worlds_used_by_mode": worlds_used,
            "shard_digests_used": shard_digests,
            "skipped_incomplete_shard_dirs": list(self._skipped_incomplete),
            "skipped_shards": deepcopy(self._skipped_shards),
            "planned_epoch_budget": planned_epoch_budget,
            "target_adapter_sha256": _file_sha256(ADAPTER_PATH),
            "target_controller_sha256": _file_sha256(CONTROLLER_PATH),
        }
        self._identity_payload = MappingProxyType(deepcopy(identity_payload))
        self._identity = f"{PROVIDER_SCHEMA}:{_canonical_sha256(identity_payload)}"
        self._positions = {
            (route, source): 0 for route in ROUTES for source in SOURCES
        }
        self._next_update_cursor = 0
        self._next_source_index = 0
        self._consumed_file_order: list[dict[str, Any]] = []

        if not isinstance(self, DeterministicRouteBatchProvider):
            _fail("provider does not implement DeterministicRouteBatchProvider")

    @property
    def provider_identity(self) -> str:
        return self._identity

    @property
    def provider_identity_payload(self) -> Mapping[str, Any]:
        return deepcopy(dict(self._identity_payload))

    @property
    def planned_epoch_budget(self) -> int:
        return self._planned_epoch_budget

    @property
    def worlds_used_by_mode(self) -> Mapping[str, tuple[int, ...]]:
        return MappingProxyType(
            {
                mode: tuple(self._identity_payload["worlds_used_by_mode"][mode])
                for mode in DISCOVERY_MODES
            }
        )

    def _assert_integrity(self) -> None:
        _module_origin(_TARGET, ADAPTER_PATH, label="target adapter")
        if _file_sha256(ADAPTER_PATH) != self._identity_payload[
            "target_adapter_sha256"
        ]:
            _fail("target adapter changed after provider construction")
        _module_origin(_CONTROLLER, CONTROLLER_PATH, label="target controller")
        if _file_sha256(CONTROLLER_PATH) != self._identity_payload[
            "target_controller_sha256"
        ]:
            _fail("target controller changed after provider construction")
        for record in self._shards.values():
            try:
                receipt = _CONTROLLER._read_receipt(record["root"])
                listed = _manifest_listing(record["root"])
                shard = receipt.get("shard")
                if not isinstance(shard, Mapping):
                    _fail(f"shard identity disappeared: {record['root']}")
                status = _status_evidence(
                    record["root"],
                    mode=str(shard.get("mode")),
                    world=int(shard.get("world")),
                )
                if status is None:
                    _fail(f"shard terminal status disappeared: {record['root']}")
            except Exception as cause:
                _fail(
                    f"controller re-authentication rejected shard {record['root']}",
                    cause=cause,
                )
            current = _snapshot_from_authenticated(record["root"], listed, status)
            if current != dict(record["snapshot"]):
                _fail(f"authenticated shard changed after loading: {record['root']}")

    def _expected_positions(
        self, *, update_cursor: int, source_index: int
    ) -> dict[tuple[str, str], int]:
        counts = {(route, source): 0 for route in ROUTES for source in SOURCES}
        completed_cycles, remainder = divmod(update_cursor, len(ROUTES))
        for route_index, route in enumerate(ROUTES):
            route_count = completed_cycles + int(route_index < remainder)
            for source in SOURCES:
                counts[(route, source)] = route_count
        if source_index:
            counts[(ROUTES[remainder], SOURCES[0])] += 1
        return counts

    def next_batch(
        self, *, route: str, source: str, update_cursor: int
    ) -> ProvidedRouteBatch:
        self._assert_integrity()
        if route not in ROUTES or source not in SOURCES:
            _fail("request is outside the closed C1/C2 informed/neutral provider")
        if type(update_cursor) is not int or update_cursor < 0:
            _fail("update_cursor must be a nonnegative exact integer")
        expected_route = ROUTES[self._next_update_cursor % len(ROUTES)]
        expected_source = SOURCES[self._next_source_index]
        if (
            update_cursor != self._next_update_cursor
            or route != expected_route
            or source != expected_source
        ):
            _fail("provider request violates deterministic route/source order")
        key = (route, source)
        position = self._positions[key]
        if position >= self._planned_epoch_budget:
            _fail(f"{route}/{source} rehearsal schedule is exhausted")
        batch = _copy_batch(self._batches[key])
        file_id = self._source_files[f"{route}:{source}"][0]
        self._positions[key] = position + 1
        self._consumed_file_order.append(
            {
                "update_cursor": update_cursor,
                "route": route,
                "source": source,
                "file_id": file_id,
                "members": list(self._source_members[f"{route}:{source}"]),
            }
        )
        if self._next_source_index + 1 == len(SOURCES):
            self._next_source_index = 0
            self._next_update_cursor += 1
        else:
            self._next_source_index += 1
        return ProvidedRouteBatch(
            route=route, source=source, file_id=file_id, batch=batch
        )

    def sampler_state(self) -> Mapping[str, Any]:
        self._assert_integrity()
        return deepcopy(
            {
                "schema": SAMPLER_SCHEMA,
                "routes": list(ROUTES),
                "sources": list(SOURCES),
                "epoch_budget": self._planned_epoch_budget,
                "provider_identity": self._identity,
                "source_files": self._source_files,
                "source_members": self._source_members,
                "cursors": {
                    f"{route}:{source}": self._positions[(route, source)]
                    for route in ROUTES
                    for source in SOURCES
                },
                "next_update_cursor": self._next_update_cursor,
                "next_source_index": self._next_source_index,
                "consumed_file_order": self._consumed_file_order,
            }
        )

    def load_sampler_state(self, state: Mapping[str, Any]) -> None:
        self._assert_integrity()
        expected_fields = {
            "schema",
            "routes",
            "sources",
            "epoch_budget",
            "provider_identity",
            "source_files",
            "source_members",
            "cursors",
            "next_update_cursor",
            "next_source_index",
            "consumed_file_order",
        }
        if not isinstance(state, Mapping) or set(state) != expected_fields:
            _fail("provider sampler state schema drifted")
        if (
            state["schema"] != SAMPLER_SCHEMA
            or state["routes"] != list(ROUTES)
            or state["sources"] != list(SOURCES)
            or state["epoch_budget"] != self._planned_epoch_budget
            or state["provider_identity"] != self._identity
            or state["source_files"] != self._source_files
            or state["source_members"] != self._source_members
        ):
            _fail("provider sampler state identity drifted")
        update_cursor = state["next_update_cursor"]
        source_index = state["next_source_index"]
        if (
            type(update_cursor) is not int
            or not 0 <= update_cursor <= len(ROUTES) * self._planned_epoch_budget
            or type(source_index) is not int
            or source_index not in range(len(SOURCES))
        ):
            _fail("provider sampler state cursor is invalid")
        raw_cursors = state["cursors"]
        expected_keys = {
            f"{route}:{source}" for route in ROUTES for source in SOURCES
        }
        if not isinstance(raw_cursors, Mapping) or set(raw_cursors) != expected_keys:
            _fail("provider sampler state lacks route/source cursors")
        positions: dict[tuple[str, str], int] = {}
        for route in ROUTES:
            for source in SOURCES:
                value = raw_cursors[f"{route}:{source}"]
                if (
                    type(value) is not int
                    or not 0 <= value <= self._planned_epoch_budget
                ):
                    _fail("provider sampler position is invalid")
                positions[(route, source)] = value
        if positions != self._expected_positions(
            update_cursor=update_cursor, source_index=source_index
        ):
            _fail("provider sampler cursors are not route/source exact")
        consumed = state["consumed_file_order"]
        expected_length = update_cursor * len(SOURCES) + source_index
        if not isinstance(consumed, list) or len(consumed) != expected_length:
            _fail("provider consumed-file order length drifted")
        expected_consumed: list[dict[str, Any]] = []
        for call_index in range(expected_length):
            call_cursor, call_source_index = divmod(call_index, len(SOURCES))
            route = ROUTES[call_cursor % len(ROUTES)]
            source = SOURCES[call_source_index]
            expected_consumed.append(
                {
                    "update_cursor": call_cursor,
                    "route": route,
                    "source": source,
                    "file_id": self._source_files[f"{route}:{source}"][0],
                    "members": list(self._source_members[f"{route}:{source}"]),
                }
            )
        if consumed != expected_consumed:
            _fail("provider consumed-file order drifted")
        self._positions = positions
        self._next_update_cursor = update_cursor
        self._next_source_index = source_index
        self._consumed_file_order = deepcopy(consumed)


__all__ = [
    "CLAIM_CEILING",
    "DeterministicRouteBatchProvider",
    "RehearsalRealShardProvider",
    "RehearsalShardProviderError",
    "ROUTES",
    "SAMPLER_SCHEMA",
    "SOURCES",
]
