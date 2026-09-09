"""Synthetic first-slice episode-screen seam for MCRL V0.23.

This module deliberately contains no simulator, TLE, torch, or TEST-world
dependency.  It is a small plumbing seam that owns arm routing, deterministic
episode production, checkpoint persistence, resume, and ratio-of-sums receipt
construction.  The synthetic adapter is not an evaluation or efficacy
implementation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Protocol, runtime_checkable
from types import MappingProxyType


SCHEMA = "multi-catfish-mcrl-v023-episode-screen-v1"
SCHEMA_VERSION = 1
RECEIPT_SCHEMA = "multi-catfish-mcrl-v023-episode-screen-receipt-v1"
CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v023-episode-screen-checkpoint-v1"

PRIMARY_ARMS: tuple[str, ...] = (
    "FULL",
    "BASELINE",
    "DROP_C1",
    "DROP_C2",
    "DROP_C3",
)
ARMS = PRIMARY_ARMS

FIRST_SLICE_EPISODES = 200
CHECKPOINT_PERIOD = 100
SEALED_PENDING_GATE = "SEALED_PENDING_GATE"
SYNTHETIC_ADAPTER_IDENTITY = "synthetic-deterministic-adapter-v1"
SYNTHETIC_ADAPTER_BINDING = "synthetic-fixed-binding-v1"
CANONICALIZATION = "json-sort-keys-separators-ascii-v1"


class EpisodeScreenError(ValueError):
    """Base error for the fail-closed synthetic episode-screen seam."""


class ScreenPlanError(EpisodeScreenError):
    """The frozen screen request cannot be admitted."""


class CheckpointError(EpisodeScreenError):
    """A checkpoint is missing, stale, or has been modified."""


def _jsonable(value: object) -> object:
    """Convert immutable request values to a strict JSON-compatible tree."""

    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical JSON mapping keys must be strings")
            result[key] = _jsonable(item)
        return result
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON does not admit non-finite numbers")
        return value
    raise TypeError(f"value of type {type(value).__name__} is not JSON-compatible")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    """Return the SHA-256 of the frozen canonical JSON representation."""

    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {
                str(key): _freeze(item)
                for key, item in value.items()
            }
        )
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, list):
        return [_thaw(item) for item in value]
    return value


def _text(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScreenPlanError(f"{field_name} must be a non-empty string")
    return value


def _as_tuple(value: object, *, field_name: str) -> tuple[object, ...]:
    if isinstance(value, (str, bytes)):
        raise ScreenPlanError(f"{field_name} must be a sequence")
    try:
        return tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise ScreenPlanError(f"{field_name} must be a sequence") from error


@dataclass(frozen=True)
class ScreenRequest:
    """Caller-visible frozen request for the synthetic first slice."""

    screen_id: str
    schema_version: int = SCHEMA_VERSION
    arms: tuple[str, ...] = PRIMARY_ARMS
    episode_count: int = FIRST_SLICE_EPISODES
    split: str = "TRAIN"
    world_ids: tuple[str | int, ...] = ("synthetic-train-world",)
    training_seeds: tuple[int, ...] = (20260905,)
    common_random_field_binding: str = "synthetic-crf-v1"
    sweep_grid: tuple[Mapping[str, object], ...] = field(
        default_factory=lambda: (MappingProxyType({"sweep": "fixed"}),)
    )
    output_schema_version: int = 1
    checkpoint_period: int = CHECKPOINT_PERIOD
    bindings: Mapping[str, str] = field(default_factory=dict)
    execution_admission_token: str = ""

    def __post_init__(self) -> None:
        # Copy caller containers so the plan cannot drift after admission.
        object.__setattr__(self, "arms", tuple(self.arms))
        object.__setattr__(self, "world_ids", tuple(self.world_ids))
        object.__setattr__(self, "training_seeds", tuple(self.training_seeds))
        points: object
        if isinstance(self.sweep_grid, Mapping):
            points = (self.sweep_grid,)
        else:
            points = tuple(self.sweep_grid)
        object.__setattr__(self, "sweep_grid", tuple(_freeze(point) for point in points))
        object.__setattr__(self, "bindings", _freeze(self.bindings))

    @property
    def arm_bindings(self) -> Mapping[str, str]:
        """Alias matching the SDD's arm-binding terminology."""

        return self.bindings

    @property
    def episodes(self) -> int:
        """Compatibility alias for callers that use ``episodes``."""

        return self.episode_count


@dataclass(frozen=True)
class ScreenPlan:
    """Validated request plus its content-addressed run fingerprint."""

    request: ScreenRequest
    run_fingerprint: str
    arms: tuple[str, ...]
    episode_count: int
    checkpoint_period: int
    sweep_points: tuple[Mapping[str, object], ...]
    output_schema_version: int

    @property
    def sweep_grid(self) -> tuple[Mapping[str, object], ...]:
        return self.sweep_points

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "run_fingerprint": self.run_fingerprint,
            "request": _request_payload(self.request),
        }


@runtime_checkable
class OpaqueExecutionAdapter(Protocol):
    """Boundary used by the screen to obtain one deterministic episode row."""

    identity: str
    binding: str

    def episode(
        self,
        *,
        run_fingerprint: str,
        arm: str,
        episode: int,
        sweep_point: Mapping[str, object],
    ) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class SyntheticDeterministicAdapter:
    """A deterministic, simulator-free adapter for ``FIRST_SLICE_PASS``."""

    identity: str = SYNTHETIC_ADAPTER_IDENTITY
    binding: str = SYNTHETIC_ADAPTER_BINDING

    def episode(
        self,
        *,
        run_fingerprint: str,
        arm: str,
        episode: int,
        sweep_point: Mapping[str, object],
    ) -> Mapping[str, object]:
        if arm not in PRIMARY_ARMS:
            raise EpisodeScreenError(f"unknown synthetic arm: {arm}")
        if episode < 1:
            raise EpisodeScreenError("synthetic episode index must be positive")
        material = _canonical_bytes(
            {
                "adapter": self.binding,
                "run_fingerprint": run_fingerprint,
                "arm": arm,
                "episode": episode,
                "sweep_point": sweep_point,
            }
        )
        digest = hashlib.sha256(material).digest()
        arm_offset = PRIMARY_ARMS.index(arm) * 73
        bits = 1000 + arm_offset + int.from_bytes(digest[0:4], "big") % 401
        energy = 10 + (arm_offset // 73) + int.from_bytes(digest[4:8], "big") % 11
        service = 1.0 if digest[8] % 5 else 0.0
        return {
            "bits": int(bits),
            "energy": int(energy),
            "service": service,
        }

    # Explicit alias keeps the adapter boundary readable to external callers.
    def episode_result(
        self,
        *,
        run_fingerprint: str,
        arm: str,
        episode: int,
        sweep_point: Mapping[str, object],
    ) -> Mapping[str, object]:
        return self.episode(
            run_fingerprint=run_fingerprint,
            arm=arm,
            episode=episode,
            sweep_point=sweep_point,
        )


SyntheticAdapter = SyntheticDeterministicAdapter


@dataclass(frozen=True)
class ArmSweepReceipt:
    """One frozen aggregate for one arm and one sweep point."""

    run_fingerprint: str
    arm: str
    sweep_point: Mapping[str, object]
    episode_start: int
    episode_end: int
    total_bits_B: float
    total_energy_E: float
    ee_ratio_of_sums_eta: float
    service_fraction_S: float
    cumulative_receipt_sha256: str
    status: str = SEALED_PENDING_GATE

    def __post_init__(self) -> None:
        object.__setattr__(self, "sweep_point", _freeze(self.sweep_point))

    def to_dict(self) -> dict[str, object]:
        return {
            "run_fingerprint": self.run_fingerprint,
            "arm": self.arm,
            "sweep_point": _thaw(self.sweep_point),
            "episode_start": self.episode_start,
            "episode_end": self.episode_end,
            "total_bits_B": self.total_bits_B,
            "total_energy_E": self.total_energy_E,
            "ee_ratio_of_sums_eta": self.ee_ratio_of_sums_eta,
            "service_fraction_S": self.service_fraction_S,
            "cumulative_receipt_sha256": self.cumulative_receipt_sha256,
            "status": self.status,
        }


@dataclass(frozen=True)
class ArmReceipt:
    """Canonical cumulative receipt bytes for one arm."""

    arm: str
    run_fingerprint: str
    sweep_receipts: tuple[ArmSweepReceipt, ...]
    canonical_bytes: bytes
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": RECEIPT_SCHEMA,
            "run_fingerprint": self.run_fingerprint,
            "arm": self.arm,
            "sweep_receipts": [row.to_dict() for row in self.sweep_receipts],
            "receipt_sha256": self.receipt_sha256,
        }


@dataclass(frozen=True)
class CheckpointRef:
    """Content-addressed reference returned by execution and resume."""

    path: Path
    screen_id: str
    run_fingerprint: str
    completed_episode: int
    checkpoint_sha256: str

    @property
    def episode(self) -> int:
        return self.completed_episode


@dataclass(frozen=True)
class ReceiptDigest:
    """The only data exposed by the digest operation."""

    receipt_sha256: str
    status: str


@dataclass(frozen=True)
class SealedScreenReceipt:
    """Immutable sealed (but not scientifically opened) screen output."""

    screen_id: str
    run_fingerprint: str
    status: str
    episode_start: int
    episode_end: int
    arm_receipts: Mapping[str, ArmReceipt]
    checkpoints: tuple[CheckpointRef, ...]
    receipt_sha256: str
    canonical_bytes: bytes

    def __post_init__(self) -> None:
        object.__setattr__(self, "arm_receipts", MappingProxyType(dict(self.arm_receipts)))

    @property
    def checkpoint(self) -> CheckpointRef:
        return self.checkpoints[-1]

    @property
    def final_checkpoint(self) -> CheckpointRef:
        return self.checkpoint

    @property
    def arm_receipt_bytes(self) -> dict[str, bytes]:
        return {
            arm: receipt.canonical_bytes
            for arm, receipt in self.arm_receipts.items()
        }

    @property
    def cumulative_receipts(self) -> Mapping[str, bytes]:
        return MappingProxyType(self.arm_receipt_bytes)

    def digest(self) -> ReceiptDigest:
        return ReceiptDigest(self.receipt_sha256, self.status)


def _request_payload(request: ScreenRequest) -> dict[str, object]:
    return {
        "screen_id": request.screen_id,
        "schema_version": request.schema_version,
        "arms": list(request.arms),
        "episode_count": request.episode_count,
        "split": request.split,
        "world_ids": list(request.world_ids),
        "training_seeds": list(request.training_seeds),
        "common_random_field_binding": request.common_random_field_binding,
        "sweep_grid": [_thaw(point) for point in request.sweep_grid],
        "output_schema_version": request.output_schema_version,
        "checkpoint_period": request.checkpoint_period,
        "bindings": _thaw(request.bindings),
        "execution_admission_token": request.execution_admission_token,
    }


def _validate_request(request: ScreenRequest) -> tuple[tuple[str, ...], tuple[Mapping[str, object], ...]]:
    if not isinstance(request, ScreenRequest):
        raise ScreenPlanError("plan requires a ScreenRequest")
    _text(request.screen_id, field_name="screen_id")
    if "TEST" in request.screen_id.upper():
        raise ScreenPlanError("TEST identifiers are not admitted")
    if request.schema_version != SCHEMA_VERSION:
        raise ScreenPlanError(f"schema_version must be {SCHEMA_VERSION}")
    if request.split != "TRAIN":
        raise ScreenPlanError("split must be TRAIN")
    if request.episode_count != FIRST_SLICE_EPISODES:
        raise ScreenPlanError(
            f"synthetic first slice episode_count must be {FIRST_SLICE_EPISODES}"
        )
    if request.checkpoint_period != CHECKPOINT_PERIOD:
        raise ScreenPlanError(
            f"checkpoint_period must be {CHECKPOINT_PERIOD}"
        )
    if type(request.output_schema_version) is not int or request.output_schema_version < 1:
        raise ScreenPlanError("output_schema_version must be a positive integer")

    arms = tuple(request.arms)
    if not arms:
        raise ScreenPlanError("arms must be a non-empty ordered subset of primary arms")
    if len(set(arms)) != len(arms) or any(arm not in PRIMARY_ARMS for arm in arms):
        raise ScreenPlanError("arms must be a unique ordered subset of the five primary arms")
    if any(not isinstance(arm, str) for arm in arms):
        raise ScreenPlanError("arm names must be strings")

    world_ids = tuple(request.world_ids)
    if not world_ids:
        raise ScreenPlanError("world_ids must be non-empty")
    if any("TEST" in str(world).upper() for world in world_ids):
        raise ScreenPlanError("TEST worlds or identifiers are not admitted")
    seeds = tuple(request.training_seeds)
    if not seeds or any(type(seed) is not int for seed in seeds):
        raise ScreenPlanError("training_seeds must be a non-empty integer sequence")
    _text(
        request.common_random_field_binding,
        field_name="common_random_field_binding",
    )
    _text(request.execution_admission_token, field_name="execution_admission_token")

    bindings = request.bindings
    if not isinstance(bindings, Mapping):
        raise ScreenPlanError("bindings must be a mapping")
    for arm in arms:
        if arm not in bindings:
            raise ScreenPlanError(f"missing binding for arm {arm}")
        _text(bindings[arm], field_name=f"binding[{arm}]")

    points = tuple(request.sweep_grid)
    if not points:
        raise ScreenPlanError("sweep_grid must contain at least one point")
    for index, point in enumerate(points):
        if not isinstance(point, Mapping) or not point:
            raise ScreenPlanError(f"sweep_grid[{index}] must be a non-empty mapping")
        try:
            _canonical_bytes(point)
        except (TypeError, ValueError) as error:
            raise ScreenPlanError(f"sweep_grid[{index}] is not canonical JSON") from error
    return arms, points


def _run_fingerprint(request: ScreenRequest) -> str:
    return canonical_sha256(
        {
            "schema": SCHEMA,
            "schema_version": request.schema_version,
            "adapter_identity": SYNTHETIC_ADAPTER_IDENTITY,
            "adapter_binding": SYNTHETIC_ADAPTER_BINDING,
            "request": _request_payload(request),
        }
    )


def _validate_adapter(adapter: OpaqueExecutionAdapter) -> None:
    if not isinstance(adapter, SyntheticDeterministicAdapter):
        raise EpisodeScreenError(
            "FIRST_SLICE_PASS admits only SyntheticDeterministicAdapter"
        )
    if adapter.identity != SYNTHETIC_ADAPTER_IDENTITY:
        raise EpisodeScreenError("synthetic adapter identity is stale")
    if adapter.binding != SYNTHETIC_ADAPTER_BINDING:
        raise EpisodeScreenError("synthetic adapter binding is stale")


def _coerce_result(result: object, *, arm: str, episode: int) -> tuple[float, float, float]:
    if not isinstance(result, Mapping):
        raise EpisodeScreenError(f"adapter result for {arm}/{episode} must be a mapping")
    try:
        bits_raw = result["bits"]
        energy_raw = result["energy"]
        service_raw = result["service"]
    except KeyError as error:
        raise EpisodeScreenError(
            f"adapter result for {arm}/{episode} lacks bits, energy, or service"
        ) from error
    try:
        bits = float(bits_raw)
        energy = float(energy_raw)
        service = float(service_raw)
    except (TypeError, ValueError, OverflowError) as error:
        raise EpisodeScreenError(f"adapter result for {arm}/{episode} is not numeric") from error
    if not all(math.isfinite(value) for value in (bits, energy, service)):
        raise EpisodeScreenError(f"adapter result for {arm}/{episode} is non-finite")
    if bits < 0.0 or energy <= 0.0 or not 0.0 <= service <= 1.0:
        raise EpisodeScreenError(f"adapter result for {arm}/{episode} is out of bounds")
    return bits, energy, service


def _empty_state(plan: ScreenPlan) -> dict[str, object]:
    return {
        "episode_rows": {
            arm: {str(index): [] for index, _ in enumerate(plan.sweep_points)}
            for arm in plan.arms
        }
    }


def _state_rows(
    state: Mapping[str, object],
    *,
    arm: str,
    sweep_index: int,
) -> list[Mapping[str, object]]:
    all_rows = state.get("episode_rows")
    if not isinstance(all_rows, Mapping):
        raise CheckpointError("checkpoint episode_rows are missing")
    arm_rows = all_rows.get(arm)
    if not isinstance(arm_rows, Mapping):
        raise CheckpointError(f"checkpoint rows are missing arm {arm}")
    rows = arm_rows.get(str(sweep_index))
    if not isinstance(rows, list):
        raise CheckpointError(f"checkpoint rows are missing sweep point {sweep_index}")
    return rows


def _append_episode(
    plan: ScreenPlan,
    state: dict[str, object],
    adapter: OpaqueExecutionAdapter,
    episode: int,
) -> None:
    for arm in plan.arms:
        for sweep_index, sweep_point in enumerate(plan.sweep_points):
            method = getattr(adapter, "episode", None)
            if not callable(method):
                method = getattr(adapter, "episode_result", None)
            if not callable(method):
                raise EpisodeScreenError("adapter has no episode result method")
            result = method(
                run_fingerprint=plan.run_fingerprint,
                arm=arm,
                episode=episode,
                sweep_point=sweep_point,
            )
            bits, energy, service = _coerce_result(result, arm=arm, episode=episode)
            _state_rows(state, arm=arm, sweep_index=sweep_index).append(
                {
                    "episode": episode,
                    "bits": bits,
                    "energy": energy,
                    "service": service,
                }
            )


def _aggregate(
    plan: ScreenPlan,
    state: Mapping[str, object],
    *,
    arm: str,
    sweep_index: int,
    episode_end: int,
) -> ArmSweepReceipt:
    rows = _state_rows(state, arm=arm, sweep_index=sweep_index)
    if len(rows) != episode_end:
        raise CheckpointError(
            f"checkpoint rows for {arm}/{sweep_index} have {len(rows)} records, expected {episode_end}"
        )
    ordered = sorted(rows, key=lambda row: int(row["episode"]))
    if [int(row["episode"]) for row in ordered] != list(range(1, episode_end + 1)):
        raise CheckpointError(f"checkpoint episode cursor is not contiguous for {arm}/{sweep_index}")
    total_bits = sum(float(row["bits"]) for row in ordered)
    total_energy = sum(float(row["energy"]) for row in ordered)
    service_sum = sum(float(row["service"]) for row in ordered)
    if total_energy <= 0.0:
        raise CheckpointError(f"checkpoint energy is not positive for {arm}/{sweep_index}")
    unsigned = {
        "run_fingerprint": plan.run_fingerprint,
        "arm": arm,
        "sweep_index": sweep_index,
        "episode_start": 1,
        "episode_end": episode_end,
        "total_bits_B": total_bits,
        "total_energy_E": total_energy,
        "service_sum": service_sum,
    }
    cumulative = canonical_sha256(unsigned)
    return ArmSweepReceipt(
        run_fingerprint=plan.run_fingerprint,
        arm=arm,
        sweep_point=plan.sweep_points[sweep_index],
        episode_start=1,
        episode_end=episode_end,
        total_bits_B=total_bits,
        total_energy_E=total_energy,
        ee_ratio_of_sums_eta=total_bits / total_energy,
        service_fraction_S=service_sum / episode_end,
        cumulative_receipt_sha256=cumulative,
    )


def _build_arm_receipt(
    plan: ScreenPlan,
    state: Mapping[str, object],
    *,
    arm: str,
    episode_end: int,
) -> ArmReceipt:
    rows = tuple(
        _aggregate(
            plan,
            state,
            arm=arm,
            sweep_index=index,
            episode_end=episode_end,
        )
        for index in range(len(plan.sweep_points))
    )
    unsigned = {
        "schema": RECEIPT_SCHEMA,
        "run_fingerprint": plan.run_fingerprint,
        "arm": arm,
        "sweep_receipts": [row.to_dict() for row in rows],
    }
    body = dict(unsigned)
    body["receipt_sha256"] = canonical_sha256(unsigned)
    encoded = _canonical_bytes(body)
    return ArmReceipt(
        arm=arm,
        run_fingerprint=plan.run_fingerprint,
        sweep_receipts=rows,
        canonical_bytes=encoded,
        receipt_sha256=body["receipt_sha256"],  # type: ignore[arg-type]
    )


def _arm_receipts(
    plan: ScreenPlan,
    state: Mapping[str, object],
    *,
    episode_end: int,
) -> dict[str, ArmReceipt]:
    return {
        arm: _build_arm_receipt(plan, state, arm=arm, episode_end=episode_end)
        for arm in plan.arms
    }


def _arm_receipt_set_digest(arm_receipts: Mapping[str, ArmReceipt]) -> str:
    return canonical_sha256(
        [
            {"arm": arm, "receipt_sha256": arm_receipts[arm].receipt_sha256}
            for arm in arm_receipts
        ]
    )


def _build_receipt(
    plan: ScreenPlan,
    state: Mapping[str, object],
    *,
    episode_end: int,
    checkpoints: tuple[CheckpointRef, ...],
) -> SealedScreenReceipt:
    arms = _arm_receipts(plan, state, episode_end=episode_end)
    unsigned = {
        "schema": RECEIPT_SCHEMA,
        "screen_id": plan.request.screen_id,
        "run_fingerprint": plan.run_fingerprint,
        "status": SEALED_PENDING_GATE,
        "episode_start": 1,
        "episode_end": episode_end,
        "arms": [
            {"arm": arm, "receipt_sha256": arms[arm].receipt_sha256}
            for arm in plan.arms
        ],
        "checkpoints": [
            {
                "completed_episode": checkpoint.completed_episode,
                "checkpoint_sha256": checkpoint.checkpoint_sha256,
            }
            for checkpoint in checkpoints
        ],
    }
    body = dict(unsigned)
    body["receipt_sha256"] = canonical_sha256(unsigned)
    encoded = _canonical_bytes(body)
    return SealedScreenReceipt(
        screen_id=plan.request.screen_id,
        run_fingerprint=plan.run_fingerprint,
        status=SEALED_PENDING_GATE,
        episode_start=1,
        episode_end=episode_end,
        arm_receipts=arms,
        checkpoints=checkpoints,
        receipt_sha256=body["receipt_sha256"],  # type: ignore[arg-type]
        canonical_bytes=encoded,
    )


def _checkpoint_payload(
    plan: ScreenPlan,
    state: Mapping[str, object],
    *,
    completed_episode: int,
    arm_receipts: Mapping[str, ArmReceipt],
) -> dict[str, object]:
    return {
        "schema": CHECKPOINT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "screen_id": plan.request.screen_id,
        "run_fingerprint": plan.run_fingerprint,
        "completed_episode": completed_episode,
        "canonicalization": CANONICALIZATION,
        "adapter": {
            "identity": SYNTHETIC_ADAPTER_IDENTITY,
            "binding": SYNTHETIC_ADAPTER_BINDING,
        },
        "request": _request_payload(plan.request),
        "network_states": {
            arm: {"Q1": "synthetic-immutable", "Q2": "synthetic-immutable", "Q3": "synthetic-immutable"}
            for arm in plan.arms
        },
        "optimizer_states": {
            arm: {"Q1": "synthetic-not-applicable", "Q2": "synthetic-not-applicable", "Q3": "synthetic-not-applicable"}
            for arm in plan.arms
        },
        "rng_states": {
            "python": "synthetic-deterministic-no-rng",
            "numpy": "synthetic-deterministic-no-rng",
            "torch": "not-applicable",
            "environment": "synthetic-cursor-only",
            "mobility": "not-applicable",
            "fading": "not-applicable",
        },
        "environment_state": {
            "adapter_cursor": completed_episode + 1,
            "common_random_field_cursor": completed_episode + 1,
        },
        "episode_rows": _thaw(state["episode_rows"]),
        "last_sealed_receipt_digest": _arm_receipt_set_digest(arm_receipts),
    }


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(temporary_fd)
    temporary = Path(temporary_name)
    try:
        with temporary.open("wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_fd = -1
        if directory_fd >= 0:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_checkpoint(
    plan: ScreenPlan,
    state: Mapping[str, object],
    *,
    completed_episode: int,
    checkpoint_dir: Path,
) -> CheckpointRef:
    arm_receipts = _arm_receipts(plan, state, episode_end=completed_episode)
    unsigned = _checkpoint_payload(
        plan,
        state,
        completed_episode=completed_episode,
        arm_receipts=arm_receipts,
    )
    checkpoint_sha256 = canonical_sha256(unsigned)
    payload = dict(unsigned)
    payload["checkpoint_sha256"] = checkpoint_sha256
    path = checkpoint_dir / f"checkpoint-{completed_episode:06d}.json"
    _atomic_write(path, _canonical_bytes(payload) + b"\n")
    return CheckpointRef(
        path=path,
        screen_id=plan.request.screen_id,
        run_fingerprint=plan.run_fingerprint,
        completed_episode=completed_episode,
        checkpoint_sha256=checkpoint_sha256,
    )


def _read_checkpoint(checkpoint: CheckpointRef | Path | str) -> tuple[CheckpointRef, dict[str, object]]:
    if isinstance(checkpoint, CheckpointRef):
        reference = checkpoint
        path = checkpoint.path
    else:
        path = Path(checkpoint)
        reference = None
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CheckpointError(f"cannot read checkpoint: {path}") from error
    if not isinstance(payload, dict):
        raise CheckpointError("checkpoint must be a JSON object")
    expected = payload.get("checkpoint_sha256")
    if not isinstance(expected, str):
        raise CheckpointError("checkpoint digest is missing")
    unsigned = dict(payload)
    unsigned.pop("checkpoint_sha256", None)
    if canonical_sha256(unsigned) != expected:
        raise CheckpointError("checkpoint digest mismatch")
    if raw.rstrip(b"\n") != _canonical_bytes(payload):
        raise CheckpointError("checkpoint is not canonical")
    if payload.get("schema") != CHECKPOINT_SCHEMA:
        raise CheckpointError("checkpoint schema is stale")
    if payload.get("canonicalization") != CANONICALIZATION:
        raise CheckpointError("checkpoint canonicalization is stale")
    screen_id = payload.get("screen_id")
    fingerprint = payload.get("run_fingerprint")
    completed = payload.get("completed_episode")
    if not isinstance(screen_id, str) or not isinstance(fingerprint, str) or type(completed) is not int:
        raise CheckpointError("checkpoint identity is malformed")
    if completed not in (CHECKPOINT_PERIOD, FIRST_SLICE_EPISODES):
        raise CheckpointError("checkpoint episode is not an admitted boundary")
    if reference is not None:
        if reference.checkpoint_sha256 != expected:
            raise CheckpointError("checkpoint reference digest mismatch")
        if reference.run_fingerprint != fingerprint:
            raise CheckpointError("checkpoint reference fingerprint mismatch")
        if reference.completed_episode != completed:
            raise CheckpointError("checkpoint reference episode mismatch")
    return (
        CheckpointRef(
            path=path,
            screen_id=screen_id,
            run_fingerprint=fingerprint,
            completed_episode=completed,
            checkpoint_sha256=expected,
        ),
        payload,
    )


def _plan_from_checkpoint(payload: Mapping[str, object]) -> ScreenPlan:
    request_payload = payload.get("request")
    if not isinstance(request_payload, Mapping):
        raise CheckpointError("checkpoint request is missing")
    try:
        request = ScreenRequest(
            screen_id=request_payload["screen_id"],  # type: ignore[arg-type]
            schema_version=request_payload["schema_version"],  # type: ignore[arg-type]
            arms=tuple(request_payload["arms"]),  # type: ignore[arg-type]
            episode_count=request_payload["episode_count"],  # type: ignore[arg-type]
            split=request_payload["split"],  # type: ignore[arg-type]
            world_ids=tuple(request_payload["world_ids"]),  # type: ignore[arg-type]
            training_seeds=tuple(request_payload["training_seeds"]),  # type: ignore[arg-type]
            common_random_field_binding=request_payload["common_random_field_binding"],  # type: ignore[arg-type]
            sweep_grid=tuple(request_payload["sweep_grid"]),  # type: ignore[arg-type]
            output_schema_version=request_payload["output_schema_version"],  # type: ignore[arg-type]
            checkpoint_period=request_payload["checkpoint_period"],  # type: ignore[arg-type]
            bindings=request_payload["bindings"],  # type: ignore[arg-type]
            execution_admission_token=request_payload["execution_admission_token"],  # type: ignore[arg-type]
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CheckpointError("checkpoint request is malformed") from error
    plan = EpisodeScreen.plan(request)
    if plan.run_fingerprint != payload.get("run_fingerprint"):
        raise CheckpointError("checkpoint run fingerprint mismatch")
    return plan


def _resume_state(payload: Mapping[str, object], plan: ScreenPlan) -> dict[str, object]:
    raw_rows = payload.get("episode_rows")
    if not isinstance(raw_rows, Mapping):
        raise CheckpointError("checkpoint episode rows are missing")
    state = {"episode_rows": {}}
    episode_rows: dict[str, dict[str, list[Mapping[str, object]]]] = {}
    for arm in plan.arms:
        raw_arm = raw_rows.get(arm)
        if not isinstance(raw_arm, Mapping):
            raise CheckpointError(f"checkpoint rows are missing arm {arm}")
        arm_rows: dict[str, list[Mapping[str, object]]] = {}
        for index in range(len(plan.sweep_points)):
            raw_point = raw_arm.get(str(index))
            if not isinstance(raw_point, list):
                raise CheckpointError(f"checkpoint rows are missing sweep point {index}")
            checked: list[Mapping[str, object]] = []
            for row in raw_point:
                if not isinstance(row, Mapping):
                    raise CheckpointError("checkpoint episode row is malformed")
                checked.append(dict(row))
            arm_rows[str(index)] = checked
        episode_rows[arm] = arm_rows
    state["episode_rows"] = episode_rows
    return state


class EpisodeScreen:
    """Deep public seam for synthetic V0.23 episode-screen plumbing."""

    @staticmethod
    def plan(request: ScreenRequest) -> ScreenPlan:
        arms, points = _validate_request(request)
        fingerprint = _run_fingerprint(request)
        return ScreenPlan(
            request=request,
            run_fingerprint=fingerprint,
            arms=arms,
            episode_count=FIRST_SLICE_EPISODES,
            checkpoint_period=CHECKPOINT_PERIOD,
            sweep_points=points,
            output_schema_version=request.output_schema_version,
        )

    @staticmethod
    def execute(
        plan: ScreenPlan,
        adapter: OpaqueExecutionAdapter,
        *,
        checkpoint_dir: Path | str | None = None,
        stop_after: int | None = None,
    ) -> SealedScreenReceipt:
        if not isinstance(plan, ScreenPlan):
            raise EpisodeScreenError("execute requires a ScreenPlan")
        _validate_adapter(adapter)
        if stop_after is not None and stop_after != CHECKPOINT_PERIOD:
            raise EpisodeScreenError(
                f"synthetic stop_after must be {CHECKPOINT_PERIOD} or omitted"
            )
        destination = (
            Path(checkpoint_dir)
            if checkpoint_dir is not None
            else Path(tempfile.mkdtemp(prefix="mcrl-v023-episode-screen-"))
        )
        state = _empty_state(plan)
        checkpoints: list[CheckpointRef] = []
        end = stop_after if stop_after is not None else plan.episode_count
        for episode in range(1, end + 1):
            _append_episode(plan, state, adapter, episode)
            if episode % plan.checkpoint_period == 0:
                checkpoints.append(
                    _write_checkpoint(
                        plan,
                        state,
                        completed_episode=episode,
                        checkpoint_dir=destination,
                    )
                )
        if not checkpoints:
            raise EpisodeScreenError("execution did not reach a checkpoint boundary")
        return _build_receipt(
            plan,
            state,
            episode_end=end,
            checkpoints=tuple(checkpoints),
        )

    @staticmethod
    def resume(
        checkpoint: CheckpointRef | Path | str,
        adapter: OpaqueExecutionAdapter,
    ) -> SealedScreenReceipt:
        reference, payload = _read_checkpoint(checkpoint)
        _validate_adapter(adapter)
        plan = _plan_from_checkpoint(payload)
        state = _resume_state(payload, plan)
        completed = reference.completed_episode
        if completed > plan.episode_count:
            raise CheckpointError("checkpoint exceeds planned episode count")
        checkpoints: list[CheckpointRef] = [reference]
        destination = reference.path.parent
        for episode in range(completed + 1, plan.episode_count + 1):
            _append_episode(plan, state, adapter, episode)
            if episode % plan.checkpoint_period == 0:
                checkpoints.append(
                    _write_checkpoint(
                        plan,
                        state,
                        completed_episode=episode,
                        checkpoint_dir=destination,
                    )
                )
        if checkpoints[-1].completed_episode != plan.episode_count:
            raise CheckpointError("resume did not reach the planned final boundary")
        return _build_receipt(
            plan,
            state,
            episode_end=plan.episode_count,
            checkpoints=tuple(checkpoints),
        )

    @staticmethod
    def digest(receipt: SealedScreenReceipt) -> ReceiptDigest:
        if not isinstance(receipt, SealedScreenReceipt):
            raise EpisodeScreenError("digest requires a SealedScreenReceipt")
        return receipt.digest()


__all__ = [
    "ARMS",
    "ArmReceipt",
    "ArmSweepReceipt",
    "CANONICALIZATION",
    "CHECKPOINT_PERIOD",
    "CheckpointError",
    "CheckpointRef",
    "EpisodeScreen",
    "EpisodeScreenError",
    "FIRST_SLICE_EPISODES",
    "OpaqueExecutionAdapter",
    "PRIMARY_ARMS",
    "RECEIPT_SCHEMA",
    "ReceiptDigest",
    "SEALED_PENDING_GATE",
    "SCHEMA",
    "SCHEMA_VERSION",
    "ScreenPlan",
    "ScreenPlanError",
    "ScreenRequest",
    "SealedScreenReceipt",
    "SyntheticAdapter",
    "SyntheticDeterministicAdapter",
    "canonical_sha256",
]
