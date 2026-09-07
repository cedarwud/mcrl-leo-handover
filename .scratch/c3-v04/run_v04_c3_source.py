#!/usr/bin/env python3
"""Prepare, materialize, and independently verify V0.4 C3 source data.

The runner has an intentional two-phase seam.  ``prepare`` replays the
authenticated Main policy only far enough to collect outcome-blind
``C3V04ContextCandidate`` metadata and seals one schedule.  ``generate``
replays that schedule and evaluates exactly its unilateral branches through
the V0.4 producer.  ``verify`` is a receipt/dataset-only audit and never
loads a trainer or evaluates the environment.  ``smoke`` uses one disjoint
development seed to seal and exhaustively materialize a tiny non-opening
real-TLE schedule; its dataset is explicitly inadmissible for learning.

The default adapters below reuse the existing authenticated real-TLE/Main
loader.  Tests can inject :class:`C3V04RunnerRuntime` adapters, which keeps
the prepare seam testable without allowing a hidden physics call to sneak
into schedule construction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Callable, Iterable, Mapping, NamedTuple, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (HERE, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.env.action_contract import (  # noqa: E402
    Association,
    NO_OP_ACTION,
    SlotTable,
)
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_v04_c3_dataset import (  # noqa: E402
    V04C3OpeningDataset,
    read_v04_c3_dataset,
    write_v04_c3_dataset,
)
from mcrl.runtime.ee_axis_v04_c3_opening_source import (  # noqa: E402
    V04C3OpeningProvenance,
    V04C3OpeningComparison,
    produce_v04_c3_opening_comparison,
)
from mcrl.runtime.ee_axis_v04_c3_schedule import (  # noqa: E402
    C3_V04_INFORMED_SOURCE_RULE,
    C3_V04_MAX_CONTEXTS_PER_ANCHOR,
    C3_V04_SCHEDULE_SCHEMA,
    C3_V04_TRAIN_CONTEXTS,
    C3_V04_TRAIN_ROW_BUDGET,
    C3_V04_VALIDATION_CONTEXTS,
    C3_V04_VALIDATION_ROW_BUDGET,
    C3V04ContextCandidate,
    C3V04SourceSchedule,
    build_v04_c3_schedule,
    contexts_from_selection,
    read_v04_c3_schedule,
    write_v04_c3_schedule,
)
from mcrl.runtime.ee_axis_v04_c3_selector import (  # noqa: E402
    C3V04SourceSelection,
    select_v04_c3_source,
)
from mcrl.runtime.ee_axis_v04_c3_state import (  # noqa: E402
    EE_AXIS_V04_C3_STATE_SCHEMA,
    encode_ee_axis_v04_c3_state,
)
from mcrl.runtime.head_pivotality import masked_greedy_actions  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import _default_code_paths  # noqa: E402


# Frozen source protocol ---------------------------------------------------

SOURCE_SEED_SPLIT: dict[int, str] = {
    2026092301: "train",
    2026092302: "train",
    2026092303: "train",
    2026092304: "train",
    2026092305: "validation",
    2026092306: "validation",
    2026092307: "validation",
}
INITIALIZATION_SEEDS = (2026092101, 2026092102, 2026092103)
USERS = 100
MAX_SOURCE_STEPS = 10
SOURCE_POLICY_VERSION = 1
KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")
LAMBDA_BITS_PER_J = float.fromhex("0x1.443a8f481639ap+26")
KEYED_FIELD_SCHEMA = "multi-catfish-mcrl-v04-c3-keyed-field-v1"
ANCHOR_SCHEMA = "multi-catfish-mcrl-v04-c3-preoutcome-anchor-v1"

# Keep these names at the runner seam so a synthetic test can shrink the
# schedule while the production defaults remain the frozen 263/203 contract.
TRAIN_CONTEXT_GOAL = C3_V04_TRAIN_CONTEXTS
VALIDATION_CONTEXT_GOAL = C3_V04_VALIDATION_CONTEXTS
TRAIN_ROW_BUDGET = C3_V04_TRAIN_ROW_BUDGET
VALIDATION_ROW_BUDGET = C3_V04_VALIDATION_ROW_BUDGET
MAX_CONTEXTS_PER_ANCHOR = C3_V04_MAX_CONTEXTS_PER_ANCHOR

SOURCE_MANIFEST_SCHEMA = "multi-catfish-mcrl-v04-c3-source-manifest-v1"
PREPARE_RECEIPT_SCHEMA = "multi-catfish-mcrl-v04-c3-prepare-receipt-v1"
PREPARE_SEAL_SCHEMA = "multi-catfish-mcrl-v04-c3-prepare-receipt-seal-v1"
GENERATE_RECEIPT_SCHEMA = "multi-catfish-mcrl-v04-c3-generate-receipt-v1"
GENERATE_SEAL_SCHEMA = "multi-catfish-mcrl-v04-c3-generate-receipt-seal-v1"
CLAIM_CEILING = (
    "V04_C3_SOURCE_CONSTRUCTION_ONLY_NOT_LEARNABILITY_EE_EFFICACY_OR_TRAINING"
)

DEFAULT_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
DEFAULT_MAIN_DIR = (
    REPO / "artifacts" / "training-2026-08-25-rerun01" / "main"
)
DEFAULT_OUTPUT_DIR = REPO / "artifacts" / "multi-catfish-v04-c3-source-20260901"
SMOKE_SOURCE_SEED = 2026092299
SMOKE_SOURCE_SPLIT = "development_smoke"
SMOKE_MAX_CANDIDATES = 2
SMOKE_SCHEDULE_SCHEMA = "multi-catfish-mcrl-v04-c3-real-tle-smoke-schedule-v1"
SMOKE_RECEIPT_SCHEMA = "multi-catfish-mcrl-v04-c3-real-tle-smoke-receipt-v1"
SMOKE_SEAL_SCHEMA = "multi-catfish-mcrl-v04-c3-real-tle-smoke-seal-v1"
SMOKE_CLAIM_CEILING = (
    "V04_C3_DEVELOPMENT_REAL_TLE_SMOKE_ONLY_NO_TRAINING_NO_EE_EFFICACY"
)
DEFAULT_SMOKE_OUTPUT_DIR = (
    REPO / ".scratch" / "multi-catfish-v04-c3-real-smoke-20260901"
)

# Frozen source lineage.  A self-consistent replacement PREREG/Main run is
# still the wrong physical authority, so the V0.4 source runner pins the exact
# already-sealed files instead of trusting caller-selected paths alone.
EXPECTED_PREREG_FILE_SHA256 = (
    "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
)
EXPECTED_PREREG_DIGEST = (
    "3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4"
)
EXPECTED_EPHEMERIS_FILE_SET_SHA256 = (
    "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
)
EXPECTED_MAIN_STATUS_FILE_SHA256 = (
    "3e980bc8c47087ff313c5f5589dab053e0f52440fff692d0c88153af4cce7fa1"
)
EXPECTED_MAIN_EPISODE_LOGS_FILE_SHA256 = (
    "635e375fe04e890d22aed41eebd40c808b41635a2f15bdadfc4e85b5580769f0"
)
EXPECTED_MAIN_CHECKPOINT_SHA256 = (
    "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
)


class C3V04SourceRunnerError(RuntimeError):
    """The V0.4 C3 source authority or materialization failed closed."""


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
        raise C3V04SourceRunnerError(
            "payload is not finite canonical JSON"
        ) from error


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)[:-1]).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C3V04SourceRunnerError(f"{field} must be lowercase SHA-256")
    return value


def _file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise C3V04SourceRunnerError(
            f"expected a regular file for SHA-256: {path}"
        )
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_once_json(path: Path, payload: object) -> str:
    """Write canonical JSON exactly once and return its byte digest."""

    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise C3V04SourceRunnerError(
            f"refusing to overwrite sealed V0.4 file: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_bytes(payload)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
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
            raise C3V04SourceRunnerError(
                f"refusing to overwrite sealed V0.4 file: {destination}"
            ) from error
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(encoded).hexdigest()


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value}")


def _read_canonical_json(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise C3V04SourceRunnerError(
            f"sealed V0.4 file is missing or not regular: {source}"
        )
    raw = source.read_bytes()
    try:
        payload = json.loads(
            raw.decode("ascii"), parse_constant=_reject_json_constant
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise C3V04SourceRunnerError(
            f"sealed V0.4 file is invalid JSON: {source}"
        ) from error
    if not isinstance(payload, dict):
        raise C3V04SourceRunnerError(
            f"sealed V0.4 file must contain a JSON object: {source}"
        )
    if raw != _canonical_bytes(payload):
        raise C3V04SourceRunnerError(
            f"sealed V0.4 file is not canonical JSON: {source}"
        )
    return payload


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError as error:
        raise C3V04SourceRunnerError(
            f"source path lies outside repository: {path}"
        ) from error


def _source_paths() -> tuple[Path, ...]:
    """Return the authenticated code closure used by the runner."""

    paths: list[Path] = [Path(__file__)]
    # The loader is the only script-level helper used by the default runtime.
    # Keep its exact source path in the manifest instead of importing any
    # historical V0.3 runner from .scratch.  ``_default_code_paths`` below
    # supplies every Python module under src/mcrl plus the launcher and
    # pyproject authority; the explicit helper makes this boundary legible
    # and protects it if the loader ever becomes a package alias.
    paths.append(REPO / "scripts" / "run_head_pivotality_probe.py")
    loader_path = getattr(loader, "__file__", None)
    if loader_path is not None:
        paths.append(Path(loader_path))
    paths.extend(
        [
            # Direct helper used by the local Main policy inference.  It is
            # already included by _default_code_paths, but spelling it out
            # makes the provenance closure auditable at this seam.
            REPO / "src" / "mcrl" / "runtime" / "head_pivotality.py",
        ]
    )
    paths.extend(_default_code_paths())
    unique = tuple(sorted({path.resolve() for path in paths}, key=str))
    missing = [path for path in unique if not path.is_file()]
    if missing:
        raise C3V04SourceRunnerError(
            "source manifest has missing files: "
            + ", ".join(str(path) for path in missing)
        )
    return unique


def _build_source_manifest() -> dict[str, Any]:
    files = [
        {"path": _relative(path), "sha256": _file_sha256(path)}
        for path in _source_paths()
    ]
    body = {"schema": SOURCE_MANIFEST_SCHEMA, "files": files}
    return {**body, "source_manifest_sha256": _canonical_sha256(body)}


def _validate_source_manifest(payload: Mapping[str, Any]) -> str:
    current = _build_source_manifest()
    if dict(payload) != current:
        raise C3V04SourceRunnerError(
            "current source closure differs from sealed V0.4 manifest"
        )
    return _digest(
        payload.get("source_manifest_sha256"),
        field="source_manifest_sha256",
    )


def _expected_seed_split() -> dict[str, str]:
    return {str(seed): split for seed, split in sorted(SOURCE_SEED_SPLIT.items())}


def _seed_quotas(seeds: Iterable[int], goal: int) -> dict[str, int]:
    ordered = sorted(int(seed) for seed in seeds)
    if not ordered or goal < len(ordered):
        raise C3V04SourceRunnerError(
            "frozen context goal cannot cover every source seed"
        )
    base, remainder = divmod(goal, len(ordered))
    return {
        str(seed): base + (1 if index < remainder else 0)
        for index, seed in enumerate(ordered)
    }


def _check_schedule_contract(schedule: C3V04SourceSchedule) -> None:
    schedule.verify()
    if schedule.schema != C3_V04_SCHEDULE_SCHEMA:
        raise C3V04SourceRunnerError("schedule schema is stale")
    if tuple(schedule.seed_split) != tuple(sorted(SOURCE_SEED_SPLIT.items())):
        raise C3V04SourceRunnerError("schedule source seed split drifted")
    if (
        schedule.train_context_goal != TRAIN_CONTEXT_GOAL
        or schedule.validation_context_goal != VALIDATION_CONTEXT_GOAL
        or schedule.train_row_budget != TRAIN_ROW_BUDGET
        or schedule.validation_row_budget != VALIDATION_ROW_BUDGET
        or schedule.max_contexts_per_anchor != MAX_CONTEXTS_PER_ANCHOR
    ):
        raise C3V04SourceRunnerError("schedule context or row budget drifted")
    if any(
        row.step_index >= MAX_SOURCE_STEPS
        for row in (*schedule.train, *schedule.validation)
    ):
        raise C3V04SourceRunnerError(
            "schedule contains a context outside the bounded replay"
        )
    expected_train = _seed_quotas(
        (seed for seed, split in SOURCE_SEED_SPLIT.items() if split == "train"),
        TRAIN_CONTEXT_GOAL,
    )
    expected_validation = _seed_quotas(
        (
            seed
            for seed, split in SOURCE_SEED_SPLIT.items()
            if split == "validation"
        ),
        VALIDATION_CONTEXT_GOAL,
    )
    observed_train = {
        str(seed): sum(row.source_seed == seed for row in schedule.train)
        for seed in sorted(SOURCE_SEED_SPLIT)
        if SOURCE_SEED_SPLIT[seed] == "train"
    }
    observed_validation = {
        str(seed): sum(row.source_seed == seed for row in schedule.validation)
        for seed in sorted(SOURCE_SEED_SPLIT)
        if SOURCE_SEED_SPLIT[seed] == "validation"
    }
    if observed_train != expected_train:
        raise C3V04SourceRunnerError(
            f"TRAIN context balance drifted: {observed_train!r}"
        )
    if observed_validation != expected_validation:
        raise C3V04SourceRunnerError(
            f"validation context balance drifted: {observed_validation!r}"
        )
    if not any(
        row.step_index > 0 for row in (*schedule.train, *schedule.validation)
    ):
        raise C3V04SourceRunnerError(
            "fresh-source schedule has no non-opening anchor"
        )


def _anchor_sha256(
    *, source_seed: int, step_index: int, state: Any, reference_actions: np.ndarray
) -> str:
    state_digest = getattr(state, "state_sha256", None)
    if not isinstance(state_digest, str):
        raise C3V04SourceRunnerError(
            "V0.4 state encoder did not return a state digest"
        )
    body = {
        "schema": ANCHOR_SCHEMA,
        "source_seed": int(source_seed),
        "step_index": int(step_index),
        "state_observation_sha256": state_digest,
        "reference_actions": [int(value) for value in reference_actions.tolist()],
    }
    return _canonical_sha256(body)


def _environment_of(wrapped: Any) -> Any:
    environment = getattr(wrapped, "environment", wrapped)
    if environment is None:
        raise C3V04SourceRunnerError("runtime returned no StepEnvironment")
    return environment


def _bind_field(wrapped: Any, field: KeyedFadingField) -> Any:
    environment = _environment_of(wrapped)
    if bool(getattr(environment, "_started", False)):
        raise C3V04SourceRunnerError(
            "keyed fading must be bound before the source episode reset"
        )
    try:
        environment._fading_field = field
    except AttributeError as error:
        raise C3V04SourceRunnerError(
            "runtime environment cannot bind the keyed fading field"
        ) from error
    return environment


def _interval_from_environment(wrapped: Any) -> float:
    environment = _environment_of(wrapped)
    driver = getattr(environment, "driver", None)
    config = getattr(driver, "config", None)
    ephemeris = getattr(config, "ephemeris", None)
    value = getattr(ephemeris, "time_step_s", None)
    if value is None:
        value = getattr(config, "interval_s", None)
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.number)
    ):
        raise C3V04SourceRunnerError(
            "environment does not expose the frozen decision interval"
        )
    interval = float(value)
    if not math.isfinite(interval) or interval <= 0.0:
        raise C3V04SourceRunnerError("decision interval must be finite and positive")
    return interval


def _replay_size(trainer: Any) -> int:
    replay = getattr(trainer, "replay", None)
    if replay is None:
        raise C3V04SourceRunnerError("Main trainer has no replay boundary")
    try:
        return len(replay)
    except TypeError as error:
        raise C3V04SourceRunnerError("Main replay has no size boundary") from error


def _actions(value: object, *, users: int) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != (users,) or not np.issubdtype(array.dtype, np.integer):
        raise C3V04SourceRunnerError(
            f"Main action vector must be integer shape ({users},)"
        )
    return np.array(array, dtype=np.int64, copy=True)


def _physical_key(table: SlotTable, action: int) -> tuple[int, int] | None:
    if not isinstance(table, SlotTable):
        raise C3V04SourceRunnerError("source anchor contains a non-SlotTable")
    if action == NO_OP_ACTION:
        return None
    association = table.association(int(action))
    if not isinstance(association, Association):
        return None
    return int(association.norad_id), int(association.cell_id)


def _physical_key_payload(value: tuple[int, int] | None) -> list[int] | None:
    return None if value is None else [int(value[0]), int(value[1])]


def _objective_weights(trainer: Any) -> tuple[float, float, float]:
    """Read the deployed scalarization weights without changing the trainer."""

    config = getattr(trainer, "config", None)
    raw = getattr(config, "objective_weights", None)
    if raw is None:
        raise C3V04SourceRunnerError(
            "Main trainer lacks the deployed objective-weight authority"
        )
    try:
        weights = tuple(float(value) for value in raw)
    except (TypeError, ValueError) as error:
        raise C3V04SourceRunnerError(
            "Main objective weights are not numeric"
        ) from error
    if (
        len(weights) != 3
        or any(not math.isfinite(value) or value < 0.0 for value in weights)
        or sum(weights) <= 0.0
    ):
        raise C3V04SourceRunnerError(
            "Main objective weights must be three finite nonnegative values"
        )
    return weights  # type: ignore[return-value]


def _main_decision(
    trainer: Any,
    wrapped: Any,
    states: Any,
    masks: Any,
    observation: Any,
    env_rng: Any,
) -> np.ndarray:
    """Infer one deployed Main action vector using only read-only surfaces.

    This is deliberately self-contained so source construction cannot acquire
    a dependency on an archived runner.  The policy is exactly the
    deployment rule: encode the current user states, scalarize all three
    online Q surfaces with the configured weights, and apply one masked greedy
    choice to the observation's common mask matrix.  The wrapper masks and RNG
    are accepted for the runner adapter signature but are not consulted.
    """

    del wrapped, masks, env_rng
    state_rows = list(states)
    if not hasattr(trainer, "encode_states") or not callable(
        trainer.encode_states
    ):
        raise C3V04SourceRunnerError(
            "Main trainer lacks the read-only encode_states surface"
        )
    if not hasattr(trainer, "scalarized_q_values") or not callable(
        trainer.scalarized_q_values
    ):
        raise C3V04SourceRunnerError(
            "Main trainer lacks the read-only scalarized_q_values surface"
        )
    try:
        encoded = trainer.encode_states(state_rows)
        scalarized = trainer.scalarized_q_values(
            encoded, objective_weights=_objective_weights(trainer)
        )
    except C3V04SourceRunnerError:
        raise
    except Exception as error:  # pragma: no cover - trainer-specific context
        raise C3V04SourceRunnerError(
            f"read-only Main inference failed: {error}"
        ) from error
    values = np.asarray(scalarized, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] != len(state_rows):
        raise C3V04SourceRunnerError(
            "Main scalarized Q surface has an invalid user/action shape"
        )
    observation_masks = getattr(observation, "masks", None)
    if observation_masks is None:
        raise C3V04SourceRunnerError(
            "Main decision observation lacks the authoritative mask matrix"
        )
    supplied_masks = np.asarray(observation_masks)
    if supplied_masks.dtype != np.bool_ or supplied_masks.shape != values.shape:
        raise C3V04SourceRunnerError(
            "Main observation masks must be exact Boolean and match the Q surface"
        )
    valid_masks = np.array(supplied_masks, dtype=np.bool_, copy=True)
    try:
        selected = masked_greedy_actions(values, valid_masks)
    except Exception as error:  # pragma: no cover - helper contract
        raise C3V04SourceRunnerError(
            f"masked Main action inference failed: {error}"
        ) from error
    actions = np.asarray(selected, dtype=np.int64)
    if actions.shape != (len(state_rows),):
        raise C3V04SourceRunnerError(
            "Main policy returned an action vector of the wrong shape"
        )
    return np.array(actions, dtype=np.int64, copy=True)


def _network_snapshot(trainer: Any) -> tuple[dict[str, Any], ...]:
    """Capture exact CPU tensor values for a no-training mutation check."""

    networks = getattr(trainer, "q_nets", None)
    if networks is None:
        raise C3V04SourceRunnerError("Main trainer has no q_nets boundary")
    try:
        network_rows = tuple(networks)
    except TypeError as error:
        raise C3V04SourceRunnerError("Main q_nets boundary is not iterable") from error
    if len(network_rows) != 3:
        raise C3V04SourceRunnerError("Main trainer must expose exactly three q_nets")
    snapshots: list[dict[str, Any]] = []
    for index, network in enumerate(network_rows):
        state_dict = getattr(network, "state_dict", None)
        if not callable(state_dict):
            raise C3V04SourceRunnerError(
                f"Main q_net {index} lacks a state_dict boundary"
            )
        snapshot: dict[str, Any] = {}
        for name, value in state_dict().items():
            detach = getattr(value, "detach", None)
            if not callable(detach):
                raise C3V04SourceRunnerError(
                    f"Main q_net {index} contains a non-tensor state value"
                )
            cpu = detach().cpu()
            clone = getattr(cpu, "clone", None)
            if not callable(clone):
                raise C3V04SourceRunnerError(
                    f"Main q_net {index} state value cannot be cloned"
                )
            snapshot[str(name)] = clone()
        snapshots.append(snapshot)
    return tuple(snapshots)


def _networks_equal(
    trainer: Any, before: tuple[dict[str, Any], ...]
) -> bool:
    """Return whether every online-network tensor is bitwise unchanged."""

    try:
        current = _network_snapshot(trainer)
    except C3V04SourceRunnerError:
        return False
    if len(current) != len(before):
        return False
    for observed, expected in zip(current, before, strict=True):
        if set(observed) != set(expected):
            return False
        for name in observed:
            lhs = observed[name]
            rhs = expected[name]
            if getattr(lhs, "dtype", None) != getattr(rhs, "dtype", None):
                return False
            if getattr(lhs, "shape", None) != getattr(rhs, "shape", None):
                return False
            equal = getattr(lhs, "equal", None)
            if not callable(equal):
                return False
            if not bool(equal(rhs)):
                return False
    return True


def _step_forward(
    wrapped: Any,
    actions: np.ndarray,
    env_rng: np.random.Generator,
) -> tuple[list[Any], list[Any], Any] | None:
    try:
        result = wrapped.step(actions, env_rng)
    except Exception as error:  # pragma: no cover - adapter-specific context
        raise C3V04SourceRunnerError(
            f"bounded Main replay step failed: {error}"
        ) from error
    if bool(getattr(result, "done", False)):
        return None
    last_outcome = getattr(wrapped, "last_outcome", None)
    observation = getattr(last_outcome, "observation", None)
    if observation is None:
        raise C3V04SourceRunnerError(
            "runtime did not expose the next predecision observation"
        )
    return (
        list(getattr(result, "user_states")),
        list(getattr(result, "action_masks")),
        observation,
    )


class C3V04RunnerRuntime(NamedTuple):
    """Adapters at the runner seam; production defaults are below."""

    frozen_archive: Callable[[Any, Path, Path], Any]
    load_trainer: Callable[..., tuple[Any, Mapping[str, Any]]]
    make_environment: Callable[..., Any]
    evaluation_rngs: Callable[[int], tuple[np.random.Generator, ...]]
    main_actions: Callable[..., object]
    network_snapshot: Callable[[Any], Any]
    networks_equal: Callable[[Any, Any], bool]
    replay_size: Callable[[Any], int] = _replay_size
    interval_s: Callable[[Any], float] = _interval_from_environment


def _default_runtime() -> C3V04RunnerRuntime:
    """Use only the current loader and the local read-only Main policy."""

    return C3V04RunnerRuntime(
        frozen_archive=loader._frozen_archive,
        load_trainer=loader._verify_and_load_trainer,
        make_environment=loader._make_environment,
        evaluation_rngs=loader._evaluation_rngs,
        main_actions=_main_decision,
        network_snapshot=_network_snapshot,
        networks_equal=_networks_equal,
    )


def _runtime(value: C3V04RunnerRuntime | None) -> C3V04RunnerRuntime:
    if value is None:
        return _default_runtime()
    if not isinstance(value, C3V04RunnerRuntime):
        raise C3V04SourceRunnerError(
            "runtime must be C3V04RunnerRuntime or None"
        )
    return value


def _record_and_prereg(
    *, prereg_path: Path, record: Any | None
) -> tuple[Any, str]:
    path = Path(prereg_path)
    prereg_file_sha256 = _file_sha256(path)
    if prereg_file_sha256 != EXPECTED_PREREG_FILE_SHA256:
        raise C3V04SourceRunnerError(
            "PREREG file is not the frozen V0.4 source authority"
        )
    if record is None:
        try:
            record = read_prereg(path)
        except Exception as error:  # pragma: no cover - prereg implementation
            raise C3V04SourceRunnerError(
                f"cannot load frozen PREREG record: {path}"
            ) from error
    sections = getattr(record, "sections", None)
    ephemeris = sections.get("ephemeris") if isinstance(sections, Mapping) else None
    if (
        getattr(record, "digest", None) != EXPECTED_PREREG_DIGEST
        or not isinstance(ephemeris, Mapping)
        or ephemeris.get("file_set_sha256")
        != EXPECTED_EPHEMERIS_FILE_SET_SHA256
    ):
        raise C3V04SourceRunnerError(
            "PREREG digest or ephemeris file-set authority drifted"
        )
    return record, prereg_file_sha256


def _authenticate_main_authority(main_dir: Path) -> dict[str, str]:
    """Authenticate the exact completed Main run before loading any policy."""

    root = Path(main_dir)
    if root.is_symlink() or not root.is_dir():
        raise C3V04SourceRunnerError(
            f"frozen Main directory is missing or non-regular: {root}"
        )
    paths = {
        "status_file_sha256": root / "status.json",
        "episode_logs_file_sha256": root / "episode-logs.json",
        "checkpoint_file_sha256": root / "final-checkpoint.pt",
    }
    observed = {field: _file_sha256(path) for field, path in paths.items()}
    expected = {
        "status_file_sha256": EXPECTED_MAIN_STATUS_FILE_SHA256,
        "episode_logs_file_sha256": EXPECTED_MAIN_EPISODE_LOGS_FILE_SHA256,
        "checkpoint_file_sha256": EXPECTED_MAIN_CHECKPOINT_SHA256,
    }
    if observed != expected:
        raise C3V04SourceRunnerError(
            "Main status/log/checkpoint lineage is not the frozen authority"
        )
    return observed


def _checkpoint_sha256(checkpoint: Mapping[str, Any]) -> str:
    value = _digest(
        checkpoint.get("checkpoint_sha256"), field="checkpoint_sha256"
    )
    if value != EXPECTED_MAIN_CHECKPOINT_SHA256:
        raise C3V04SourceRunnerError(
            "loaded Main checkpoint is not the frozen V0.4 source authority"
        )
    return value


def _field_for_seed(checkpoint_sha256: str, source_seed: int) -> KeyedFadingField:
    return KeyedFadingField.from_components(
        KEYED_FIELD_SCHEMA,
        checkpoint_sha256,
        int(source_seed),
    )


def _scan_seed(
    *,
    runtime: C3V04RunnerRuntime,
    trainer: Any,
    archive: Any,
    checkpoint_sha256: str,
    source_seed: int,
    split: str,
    interval_s: float | None,
) -> tuple[tuple[C3V04ContextCandidate, ...], dict[str, Any], float]:
    field = _field_for_seed(checkpoint_sha256, source_seed)
    wrapped = runtime.make_environment(archive, users=USERS)
    environment = _bind_field(wrapped, field)
    current_interval = float(runtime.interval_s(wrapped))
    if interval_s is not None and current_interval != interval_s:
        raise C3V04SourceRunnerError(
            "source seeds disagree on the frozen decision interval"
        )
    env_rng, mobility_rng, _action_rng, _control_rng = runtime.evaluation_rngs(
        int(source_seed)
    )
    try:
        states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    except Exception as error:  # pragma: no cover - adapter-specific context
        raise C3V04SourceRunnerError(
            f"source seed {source_seed} reset failed: {error}"
        ) from error
    contexts: list[C3V04ContextCandidate] = []
    scanned = 0
    selected = 0
    for ordinal in range(MAX_SOURCE_STEPS):
        reference = _actions(
            runtime.main_actions(
                trainer, wrapped, states, masks, observation, env_rng
            ),
            users=USERS,
        )
        state = encode_ee_axis_v04_c3_state(
            environment,
            observation,
            interval_s=current_interval,
            kappa_bits=KAPPA_BITS,
        )
        anchor = _anchor_sha256(
            source_seed=source_seed,
            step_index=int(observation.step_index),
            state=state,
            reference_actions=reference,
        )
        plan = select_v04_c3_source(
            environment,
            observation,
            anchor_sha256=anchor,
            reference_actions=reference,
            interval_s=current_interval,
            kappa_bits=KAPPA_BITS,
            # ``None`` is deliberate: prepare must consider all eligible
            # focal users and cannot use an outcome-derived shortlist.
            max_focal_users=None,
            state=state,
        )
        scanned += 1
        if plan is not None:
            if not isinstance(plan, C3V04SourceSelection):
                raise C3V04SourceRunnerError(
                    "V0.4 selector returned a non-selection value"
                )
            rows = contexts_from_selection(
                source_seed=source_seed,
                split=split,
                selection=plan,
            )
            contexts.extend(rows)
            selected += len(rows)
        if ordinal + 1 >= MAX_SOURCE_STEPS:
            break
        following = _step_forward(wrapped, reference, env_rng)
        if following is None:
            break
        states, masks, observation = following
    receipt = {
        "source_seed": int(source_seed),
        "split": split,
        "keyed_field_sha256": field.root_digest,
        "anchors_scanned": scanned,
        "contexts_collected": selected,
        "counterfactual_outcomes_evaluated": False,
    }
    return tuple(contexts), receipt, current_interval


def _context_balance(schedule: C3V04SourceSchedule) -> dict[str, dict[str, int]]:
    return {
        "train": {
            str(seed): sum(row.source_seed == seed for row in schedule.train)
            for seed in sorted(SOURCE_SEED_SPLIT)
            if SOURCE_SEED_SPLIT[seed] == "train"
        },
        "validation": {
            str(seed): sum(row.source_seed == seed for row in schedule.validation)
            for seed in sorted(SOURCE_SEED_SPLIT)
            if SOURCE_SEED_SPLIT[seed] == "validation"
        },
    }


def _schedule_rows(schedule: C3V04SourceSchedule, *, source_seed: int) -> tuple[C3V04ContextCandidate, ...]:
    return tuple(
        row
        for row in (*schedule.train, *schedule.validation)
        if row.source_seed == source_seed
    )


def _smoke_key(value: object, *, field: str) -> tuple[int, int] | None:
    """Decode one physical key from the smoke schedule surface."""

    if value is None:
        return None
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(item) is not int for item in value)
    ):
        raise C3V04SourceRunnerError(f"{field} is not a physical key")
    return int(value[0]), int(value[1])


def _smoke_state_snapshot(state: Any) -> dict[str, Any]:
    """Capture the immutable V0.4 state arrays for a post-evaluation check."""

    state.verify()
    return {
        "state_sha256": state.state_sha256,
        "state_matrix": np.array(state.state_matrix, copy=True),
        "action_masks": np.array(state.action_masks, copy=True),
    }


def _smoke_state_unchanged(state: Any, before: Mapping[str, Any]) -> bool:
    try:
        state.verify()
    except Exception:
        return False
    return bool(
        state.state_sha256 == before["state_sha256"]
        and np.array_equal(state.state_matrix, before["state_matrix"])
        and np.array_equal(state.action_masks, before["action_masks"])
    )


def _smoke_context_from_selection(
    selection: C3V04SourceSelection,
    *,
    source_seed: int,
) -> dict[str, Any]:
    """Project one pre-outcome selector result into a smoke-only schedule row.

    This intentionally does not use :class:`C3V04ContextCandidate`: that type
    is restricted to the frozen TRAIN/validation source split.  Keeping the
    development seed in an explicit third split prevents a smoke receipt from
    being mistaken for production learning data.
    """

    if source_seed in SOURCE_SEED_SPLIT:
        raise C3V04SourceRunnerError(
            "smoke source seed overlaps the frozen TRAIN/validation split"
        )
    selection.verify()
    focal_users = tuple(sorted(selection.selected_focal_users))
    if not focal_users:
        raise C3V04SourceRunnerError(
            "smoke selector returned no selected focal user"
        )
    focal_user = focal_users[0]
    opportunities = sorted(
        (
            row
            for row in selection.opportunities
            if row.focal_user == focal_user
        ),
        key=lambda row: (row.candidate_action, row.focal_user),
    )
    if not opportunities:
        raise C3V04SourceRunnerError(
            "smoke selector returned no opportunity for its selected focal user"
        )
    opportunities = opportunities[:SMOKE_MAX_CANDIDATES]
    reference = opportunities[0]
    if any(
        row.reference_action != reference.reference_action
        or row.reference_physical_key != reference.reference_physical_key
        for row in opportunities
    ):
        raise C3V04SourceRunnerError(
            "smoke selector returned inconsistent reference metadata"
        )
    context = {
        "source_seed": int(source_seed),
        "split": SMOKE_SOURCE_SPLIT,
        "anchor_sha256": selection.anchor_sha256,
        "state_observation_sha256": selection.state.state_sha256,
        "step_index": int(selection.step_index),
        "focal_user": int(focal_user),
        "source_rule": selection.source_rule,
        "reference_action": int(reference.reference_action),
        "reference_physical_key": _physical_key_payload(
            reference.reference_physical_key
        ),
        "candidate_actions": [int(row.candidate_action) for row in opportunities],
        "candidate_physical_keys": [
            _physical_key_payload(row.candidate_physical_key)
            for row in opportunities
        ],
        "burden_deltas": [float(row.burden_delta).hex() for row in opportunities],
        "satellite_burden_deltas": [
            float(row.satellite_burden_delta).hex() for row in opportunities
        ],
        "victim_pressures": [float(row.victim_pressure).hex() for row in opportunities],
        "satellite_victim_pressures": [
            float(row.satellite_victim_pressure).hex() for row in opportunities
        ],
    }
    if int(context["step_index"]) <= 0:
        raise C3V04SourceRunnerError(
            "smoke schedule must contain a non-opening anchor"
        )
    if any(value is None for value in context["candidate_physical_keys"]):
        raise C3V04SourceRunnerError(
            "smoke schedule contains a candidate without a physical key"
        )
    return context


def _smoke_schedule_payload(
    context: Mapping[str, Any], *, source_manifest_sha256: str
) -> dict[str, Any]:
    """Build the mini schedule body and its digest before branch evaluation."""

    body: dict[str, Any] = {
        "schema": SMOKE_SCHEDULE_SCHEMA,
        "mode": "development_real_tle_smoke_only",
        "claim_ceiling": SMOKE_CLAIM_CEILING,
        "source_seed": SMOKE_SOURCE_SEED,
        "split": SMOKE_SOURCE_SPLIT,
        "source_manifest_sha256": source_manifest_sha256,
        "contexts": [dict(context)],
        "context_goal": 1,
        "row_budget": len(context["candidate_actions"]),
        "nonopening_required": True,
        "production_source_schedule_used": False,
        "train_split_present": False,
        "validation_split_present": False,
        "test_split_present": False,
        "counterfactual_outcomes_evaluated": False,
        "training": False,
        "held_out_ee_evaluated": False,
    }
    return {**body, "schedule_sha256": _canonical_sha256(body)}


def _validate_smoke_schedule(
    payload: Mapping[str, Any], *, source_manifest_sha256: str
) -> None:
    required = {
        "schema",
        "mode",
        "claim_ceiling",
        "source_seed",
        "split",
        "source_manifest_sha256",
        "contexts",
        "context_goal",
        "row_budget",
        "nonopening_required",
        "production_source_schedule_used",
        "train_split_present",
        "validation_split_present",
        "test_split_present",
        "counterfactual_outcomes_evaluated",
        "training",
        "held_out_ee_evaluated",
        "schedule_sha256",
    }
    if set(payload) != required:
        raise C3V04SourceRunnerError("smoke schedule schema is unexpected")
    if (
        payload["schema"] != SMOKE_SCHEDULE_SCHEMA
        or payload["mode"] != "development_real_tle_smoke_only"
        or payload["claim_ceiling"] != SMOKE_CLAIM_CEILING
        or payload["source_seed"] != SMOKE_SOURCE_SEED
        or payload["split"] != SMOKE_SOURCE_SPLIT
        or payload["source_manifest_sha256"] != source_manifest_sha256
        or payload["context_goal"] != 1
        or payload["nonopening_required"] is not True
        or payload["production_source_schedule_used"] is not False
        or payload["train_split_present"] is not False
        or payload["validation_split_present"] is not False
        or payload["test_split_present"] is not False
        or payload["counterfactual_outcomes_evaluated"] is not False
        or payload["training"] is not False
        or payload["held_out_ee_evaluated"] is not False
    ):
        raise C3V04SourceRunnerError("smoke schedule authority changed")
    contexts = payload["contexts"]
    if not isinstance(contexts, list) or len(contexts) != 1:
        raise C3V04SourceRunnerError("smoke schedule must contain one context")
    context = contexts[0]
    if not isinstance(context, dict):
        raise C3V04SourceRunnerError("smoke schedule context is malformed")
    if (
        context.get("source_seed") != SMOKE_SOURCE_SEED
        or context.get("split") != SMOKE_SOURCE_SPLIT
        or type(context.get("step_index")) is not int
        or context["step_index"] <= 0
    ):
        raise C3V04SourceRunnerError(
            "smoke schedule context is not a non-opening development row"
        )
    actions = context.get("candidate_actions")
    keys = context.get("candidate_physical_keys")
    if (
        not isinstance(actions, list)
        or not 1 <= len(actions) <= SMOKE_MAX_CANDIDATES
        or not isinstance(keys, list)
        or len(keys) != len(actions)
        or any(_smoke_key(value, field="candidate_physical_key") is None for value in keys)
    ):
        raise C3V04SourceRunnerError(
            "smoke schedule candidate actions or physical keys are malformed"
        )
    if payload["row_budget"] != len(actions):
        raise C3V04SourceRunnerError("smoke schedule row budget disagrees")
    body = dict(payload)
    supplied = _digest(body.pop("schedule_sha256"), field="schedule_sha256")
    if supplied != _canonical_sha256(body):
        raise C3V04SourceRunnerError("smoke schedule digest disagrees with payload")


def _validate_smoke_receipt(
    receipt: Mapping[str, Any],
    *,
    source_manifest_sha256: str,
    schedule: Mapping[str, Any],
) -> None:
    """Validate the receipt-only development smoke publication."""

    required = {
        "schema",
        "status",
        "mode",
        "claim_ceiling",
        "source_seed",
        "split",
        "source_manifest_sha256",
        "source_manifest_file_sha256",
        "prereg_file_sha256",
        "prereg_digest",
        "ephemeris_file_set_sha256",
        "main_authority",
        "checkpoint_sha256",
        "keyed_fading_field_schema",
        "keyed_fading_bound",
        "schedule_sha256",
        "schedule_file_sha256",
        "schedule_sealed_before_counterfactuals",
        "scan",
        "seed_receipt",
        "comparison_sha256s",
        "ephemeral_dataset_sha256",
        "ephemeral_dataset_round_trip_verified",
        "published_learning_data",
        "scheduled_contexts",
        "scheduled_rows",
        "materialized_rows",
        "all_scheduled_rows_materialized",
        "nonopening_anchor_present",
        "physical_keys_verified",
        "state_bitwise_unchanged",
        "main_networks_bitwise_unchanged",
        "main_replay_unchanged",
        "counterfactual_outcomes_evaluated",
        "target_sign_filter",
        "production_source_schedule_used",
        "production_output_touched",
        "train_split_present",
        "validation_split_present",
        "test_split_present",
        "test_split_opened",
        "held_out_ee_evaluated",
        "ee_evaluated",
        "training",
        "optimizer_called",
        "smoke_dataset_for_training",
        "elapsed_s",
    }
    if set(receipt) != required:
        raise C3V04SourceRunnerError("smoke receipt schema is unexpected")
    row_budget = int(schedule["row_budget"])
    expected_main = {
        "status_file_sha256": EXPECTED_MAIN_STATUS_FILE_SHA256,
        "episode_logs_file_sha256": EXPECTED_MAIN_EPISODE_LOGS_FILE_SHA256,
        "checkpoint_file_sha256": EXPECTED_MAIN_CHECKPOINT_SHA256,
    }
    if (
        receipt["schema"] != SMOKE_RECEIPT_SCHEMA
        or receipt["status"] != "PASS_SMOKE_ONLY"
        or receipt["mode"] != "development_real_tle_smoke_only"
        or receipt["claim_ceiling"] != SMOKE_CLAIM_CEILING
        or receipt["source_seed"] != SMOKE_SOURCE_SEED
        or receipt["split"] != SMOKE_SOURCE_SPLIT
        or receipt["source_manifest_sha256"] != source_manifest_sha256
        or receipt["prereg_file_sha256"] != EXPECTED_PREREG_FILE_SHA256
        or receipt["prereg_digest"] != EXPECTED_PREREG_DIGEST
        or receipt["ephemeris_file_set_sha256"]
        != EXPECTED_EPHEMERIS_FILE_SET_SHA256
        or receipt["main_authority"] != expected_main
        or receipt["checkpoint_sha256"] != EXPECTED_MAIN_CHECKPOINT_SHA256
        or receipt["keyed_fading_field_schema"] != KEYED_FIELD_SCHEMA
        or receipt["keyed_fading_bound"] is not True
        or receipt["schedule_sha256"] != schedule["schedule_sha256"]
        or receipt["schedule_sealed_before_counterfactuals"] is not True
        or receipt["published_learning_data"] is not False
        or receipt["scheduled_contexts"] != 1
        or receipt["scheduled_rows"] != row_budget
        or receipt["materialized_rows"] != row_budget
        or receipt["all_scheduled_rows_materialized"] is not True
        or receipt["nonopening_anchor_present"] is not True
        or receipt["physical_keys_verified"] is not True
        or receipt["state_bitwise_unchanged"] is not True
        or receipt["main_networks_bitwise_unchanged"] is not True
        or receipt["main_replay_unchanged"] is not True
        or receipt["counterfactual_outcomes_evaluated"] is not True
        or receipt["target_sign_filter"] is not False
        or receipt["production_source_schedule_used"] is not False
        or receipt["production_output_touched"] is not False
        or receipt["train_split_present"] is not False
        or receipt["validation_split_present"] is not False
        or receipt["test_split_present"] is not False
        or receipt["test_split_opened"] is not False
        or receipt["held_out_ee_evaluated"] is not False
        or receipt["ee_evaluated"] is not False
        or receipt["training"] is not False
        or receipt["optimizer_called"] is not False
        or receipt["smoke_dataset_for_training"] is not False
        or receipt["ephemeral_dataset_round_trip_verified"] is not True
    ):
        raise C3V04SourceRunnerError("smoke receipt authority changed")
    for field in (
        "source_manifest_file_sha256",
        "prereg_file_sha256",
        "prereg_digest",
        "ephemeris_file_set_sha256",
        "checkpoint_sha256",
        "schedule_sha256",
        "schedule_file_sha256",
        "ephemeral_dataset_sha256",
    ):
        _digest(receipt[field], field=f"smoke.{field}")
    comparisons = receipt["comparison_sha256s"]
    if (
        not isinstance(comparisons, list)
        or len(comparisons) != row_budget
        or len(set(comparisons)) != row_budget
    ):
        raise C3V04SourceRunnerError(
            "smoke comparison receipt does not cover the sealed row budget"
        )
    for index, digest in enumerate(comparisons):
        _digest(digest, field=f"smoke.comparison_sha256s[{index}]")
    elapsed = receipt["elapsed_s"]
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0.0
    ):
        raise C3V04SourceRunnerError("smoke elapsed time is invalid")


def _authenticate_smoke_authority(
    smoke_dir: Path,
    *,
    source_manifest_sha256: str,
    prereg_file_sha256: str,
) -> dict[str, Any]:
    """Authenticate a completed real-TLE smoke before production prepare."""

    root = Path(smoke_dir)
    if root.is_symlink() or not root.is_dir():
        raise C3V04SourceRunnerError(
            f"real-TLE smoke authority is missing or non-regular: {root}"
        )
    expected_files = {
        "source-manifest.json",
        "smoke-schedule.json",
        "smoke-schedule-seal.json",
        "receipt.json",
        "receipt-seal.json",
    }
    observed_files = {
        path.name for path in root.iterdir() if path.is_file() and not path.is_symlink()
    }
    if observed_files != expected_files or any(
        path.is_dir() or path.is_symlink() for path in root.iterdir()
    ):
        raise C3V04SourceRunnerError(
            "real-TLE smoke must publish receipt authority only, with no dataset"
        )
    manifest_path = root / "source-manifest.json"
    schedule_path = root / "smoke-schedule.json"
    schedule_seal_path = root / "smoke-schedule-seal.json"
    receipt_path = root / "receipt.json"
    receipt_seal_path = root / "receipt-seal.json"
    manifest = _read_canonical_json(manifest_path)
    if _validate_source_manifest(manifest) != source_manifest_sha256:
        raise C3V04SourceRunnerError("smoke source manifest differs from prepare")
    schedule = _read_canonical_json(schedule_path)
    _validate_smoke_schedule(
        schedule, source_manifest_sha256=source_manifest_sha256
    )
    schedule_file_sha256 = _file_sha256(schedule_path)
    schedule_seal = _read_canonical_json(schedule_seal_path)
    if (
        set(schedule_seal)
        != {
            "schema",
            "schedule_file_sha256",
            "schedule_sha256",
            "counterfactuals_evaluated",
        }
        or schedule_seal["schema"] != SMOKE_SEAL_SCHEMA
        or schedule_seal["schedule_file_sha256"] != schedule_file_sha256
        or schedule_seal["schedule_sha256"] != schedule["schedule_sha256"]
        or schedule_seal["counterfactuals_evaluated"] is not False
    ):
        raise C3V04SourceRunnerError("smoke schedule seal is invalid")
    receipt = _read_canonical_json(receipt_path)
    _validate_smoke_receipt(
        receipt,
        source_manifest_sha256=source_manifest_sha256,
        schedule=schedule,
    )
    if receipt["source_manifest_file_sha256"] != _file_sha256(manifest_path):
        raise C3V04SourceRunnerError("smoke source-manifest bytes changed")
    if receipt["schedule_file_sha256"] != schedule_file_sha256:
        raise C3V04SourceRunnerError("smoke schedule bytes changed")
    if receipt["prereg_file_sha256"] != prereg_file_sha256:
        raise C3V04SourceRunnerError("smoke and prepare PREREG bytes differ")
    receipt_file_sha256 = _file_sha256(receipt_path)
    schedule_seal_file_sha256 = _file_sha256(schedule_seal_path)
    receipt_seal = _read_canonical_json(receipt_seal_path)
    if (
        set(receipt_seal)
        != {
            "schema",
            "receipt_file_sha256",
            "source_manifest_file_sha256",
            "schedule_file_sha256",
            "schedule_seal_file_sha256",
        }
        or receipt_seal["schema"] != SMOKE_SEAL_SCHEMA
        or receipt_seal["receipt_file_sha256"] != receipt_file_sha256
        or receipt_seal["source_manifest_file_sha256"]
        != receipt["source_manifest_file_sha256"]
        or receipt_seal["schedule_file_sha256"] != schedule_file_sha256
        or receipt_seal["schedule_seal_file_sha256"]
        != schedule_seal_file_sha256
    ):
        raise C3V04SourceRunnerError("smoke receipt seal is invalid")
    return {
        "receipt_file_sha256": receipt_file_sha256,
        "receipt_seal_file_sha256": _file_sha256(receipt_seal_path),
        "source_manifest_file_sha256": receipt["source_manifest_file_sha256"],
        "schedule_file_sha256": schedule_file_sha256,
        "schedule_seal_file_sha256": schedule_seal_file_sha256,
        "schedule_sha256": schedule["schedule_sha256"],
        "checkpoint_sha256": receipt["checkpoint_sha256"],
        "prereg_file_sha256": receipt["prereg_file_sha256"],
        "materialized_rows": receipt["materialized_rows"],
        "published_learning_data": False,
    }


def _scan_smoke_seed(
    *,
    runtime: C3V04RunnerRuntime,
    trainer: Any,
    archive: Any,
    checkpoint_sha256: str,
    source_seed: int,
) -> tuple[dict[str, Any], dict[str, Any], float]:
    """Replay one disjoint development seed and select one non-opening context."""

    if source_seed in SOURCE_SEED_SPLIT:
        raise C3V04SourceRunnerError(
            "smoke source seed overlaps frozen TRAIN/validation seeds"
        )
    field = _field_for_seed(checkpoint_sha256, source_seed)
    wrapped = runtime.make_environment(archive, users=USERS)
    environment = _bind_field(wrapped, field)
    interval_s = float(runtime.interval_s(wrapped))
    env_rng, mobility_rng, _action_rng, _control_rng = runtime.evaluation_rngs(
        int(source_seed)
    )
    try:
        states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    except Exception as error:  # pragma: no cover - adapter-specific context
        raise C3V04SourceRunnerError(
            f"smoke source seed {source_seed} reset failed: {error}"
        ) from error
    scanned = 0
    for ordinal in range(int(MAX_SOURCE_STEPS)):
        reference = _actions(
            runtime.main_actions(
                trainer, wrapped, states, masks, observation, env_rng
            ),
            users=USERS,
        )
        state = encode_ee_axis_v04_c3_state(
            environment,
            observation,
            interval_s=interval_s,
            kappa_bits=KAPPA_BITS,
        )
        step = int(observation.step_index)
        anchor = _anchor_sha256(
            source_seed=source_seed,
            step_index=step,
            state=state,
            reference_actions=reference,
        )
        plan = select_v04_c3_source(
            environment,
            observation,
            anchor_sha256=anchor,
            reference_actions=reference,
            interval_s=interval_s,
            kappa_bits=KAPPA_BITS,
            max_focal_users=None,
            state=state,
        )
        scanned += 1
        if plan is not None and step > 0:
            return (
                _smoke_context_from_selection(
                    plan,
                    source_seed=source_seed,
                ),
                {
                    "source_seed": source_seed,
                    "anchors_scanned": scanned,
                    "selected_step_index": step,
                    "counterfactual_outcomes_evaluated": False,
                },
                interval_s,
            )
        if ordinal + 1 >= int(MAX_SOURCE_STEPS):
            break
        following = _step_forward(wrapped, reference, env_rng)
        if following is None:
            break
        states, masks, observation = following
    raise C3V04SourceRunnerError(
        "development real-TLE smoke found no eligible non-opening anchor"
    )


def _materialize_smoke_context(
    *,
    runtime: C3V04RunnerRuntime,
    trainer: Any,
    archive: Any,
    context: Mapping[str, Any],
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    interval_s: float,
) -> tuple[tuple[V04C3OpeningComparison, ...], dict[str, Any]]:
    """Replay the selected anchor and evaluate every sealed smoke sibling."""

    source_seed = int(context["source_seed"])
    if source_seed in SOURCE_SEED_SPLIT:
        raise C3V04SourceRunnerError(
            "smoke context overlaps frozen TRAIN/validation seeds"
        )
    target_step = int(context["step_index"])
    if target_step <= 0:
        raise C3V04SourceRunnerError("smoke materialization requires non-opening step")
    candidate_actions = tuple(int(value) for value in context["candidate_actions"])
    candidate_keys = tuple(
        _smoke_key(value, field="candidate_physical_key")
        for value in context["candidate_physical_keys"]
    )
    if any(value is None for value in candidate_keys):
        raise C3V04SourceRunnerError("smoke candidate physical key is missing")
    field = _field_for_seed(checkpoint_sha256, source_seed)
    wrapped = runtime.make_environment(archive, users=USERS)
    environment = _bind_field(wrapped, field)
    if float(runtime.interval_s(wrapped)) != interval_s:
        raise C3V04SourceRunnerError(
            "smoke replay decision interval differs from the selected anchor"
        )
    env_rng, mobility_rng, _action_rng, _control_rng = runtime.evaluation_rngs(
        source_seed
    )
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    comparisons: list[V04C3OpeningComparison] = []
    materialized_rows: list[dict[str, Any]] = []
    reached = False
    for ordinal in range(int(MAX_SOURCE_STEPS)):
        reference = _actions(
            runtime.main_actions(
                trainer, wrapped, states, masks, observation, env_rng
            ),
            users=USERS,
        )
        state = encode_ee_axis_v04_c3_state(
            environment,
            observation,
            interval_s=interval_s,
            kappa_bits=KAPPA_BITS,
        )
        step = int(observation.step_index)
        anchor = _anchor_sha256(
            source_seed=source_seed,
            step_index=step,
            state=state,
            reference_actions=reference,
        )
        if step == target_step:
            reached = True
            if (
                anchor != context["anchor_sha256"]
                or state.state_sha256 != context["state_observation_sha256"]
                or int(reference[int(context["focal_user"])])
                != int(context["reference_action"])
            ):
                raise C3V04SourceRunnerError(
                    "smoke replay anchor/state/Main action differs from sealed schedule"
                )
            focal_user = int(context["focal_user"])
            reference_key = _physical_key(
                observation.candidates.slot_tables[focal_user],
                int(context["reference_action"]),
            )
            if reference_key != _smoke_key(
                context["reference_physical_key"],
                field="reference_physical_key",
            ):
                raise C3V04SourceRunnerError(
                    "smoke replay reference physical key differs from schedule"
                )
            state_before = _smoke_state_snapshot(state)
            for candidate_action, expected_key in zip(
                candidate_actions, candidate_keys, strict=True
            ):
                if _physical_key(
                    observation.candidates.slot_tables[focal_user], candidate_action
                ) != expected_key:
                    raise C3V04SourceRunnerError(
                        "smoke replay candidate physical key differs from schedule"
                    )
                reference_actions = np.array(reference, dtype=np.int64, copy=True)
                candidate_vector = np.array(reference, dtype=np.int64, copy=True)
                candidate_vector[focal_user] = candidate_action
                provenance = V04C3OpeningProvenance(
                    source_policy_version=SOURCE_POLICY_VERSION,
                    anchor_sha256=str(context["anchor_sha256"]),
                    source_manifest_sha256=source_manifest_sha256,
                    checkpoint_sha256=checkpoint_sha256,
                    common_random_field_sha256=field.root_digest,
                    c3_source_rule=str(context["source_rule"]),
                )
                comparison = produce_v04_c3_opening_comparison(
                    environment,
                    observation=observation,
                    state_observation=state,
                    reference_actions=reference_actions,
                    candidate_actions=candidate_vector,
                    focal_user=focal_user,
                    common_random_field=field,
                    provenance=provenance,
                    rng=env_rng,
                    lambda_bits_per_j=LAMBDA_BITS_PER_J,
                    interval_s=interval_s,
                    kappa_bits=KAPPA_BITS,
                )
                comparison.verify()
                if (
                    comparison.pair.anchor_sha256 != context["anchor_sha256"]
                    or comparison.pair.candidate_action != candidate_action
                    or comparison.reference_physical_key != reference_key
                    or comparison.candidate_physical_key != expected_key
                    or comparison.state_observation_sha256
                    != context["state_observation_sha256"]
                ):
                    raise C3V04SourceRunnerError(
                        "smoke producer emitted an unscheduled comparison"
                    )
                if not _smoke_state_unchanged(state, state_before):
                    raise C3V04SourceRunnerError(
                        "smoke branch evaluation mutated the sealed state"
                    )
                comparisons.append(comparison)
                materialized_rows.append(
                    {
                        "source_seed": source_seed,
                        "split": SMOKE_SOURCE_SPLIT,
                        "anchor_sha256": str(context["anchor_sha256"]),
                        "step_index": step,
                        "focal_user": focal_user,
                        "reference_action": int(context["reference_action"]),
                        "candidate_action": candidate_action,
                        "reference_physical_key": _physical_key_payload(reference_key),
                        "candidate_physical_key": _physical_key_payload(expected_key),
                        "comparison_sha256": comparison.comparison_sha256,
                    }
                )
            if not _smoke_state_unchanged(state, state_before):
                raise C3V04SourceRunnerError(
                    "smoke branch evaluation changed the sealed state"
                )
            break
        if ordinal + 1 >= int(MAX_SOURCE_STEPS):
            break
        following = _step_forward(wrapped, reference, env_rng)
        if following is None:
            break
        states, masks, observation = following
    if not reached:
        raise C3V04SourceRunnerError(
            "smoke replay did not reach its sealed non-opening anchor"
        )
    if len(comparisons) != len(candidate_actions):
        raise C3V04SourceRunnerError(
            "smoke materialization omitted a scheduled comparison"
        )
    return tuple(comparisons), {
        "source_seed": source_seed,
        "split": SMOKE_SOURCE_SPLIT,
        "scheduled_rows": len(candidate_actions),
        "materialized_rows": len(comparisons),
        "materialized_nonopening_steps": 1,
        "materialized_steps": [target_step],
        "target_sign_filter": False,
        "rows": materialized_rows,
    }


def smoke(
    *,
    output_dir: Path = DEFAULT_SMOKE_OUTPUT_DIR,
    tle_root: Path,
    prereg_path: Path = DEFAULT_PREREG,
    main_dir: Path = DEFAULT_MAIN_DIR,
    runtime: C3V04RunnerRuntime | None = None,
    record: Any | None = None,
) -> dict[str, Any]:
    """Run one disjoint real-TLE engineering smoke before production prepare.

    The development seed is never admitted to ``SOURCE_SEED_SPLIT`` and the
    smoke output is intentionally separate from the production source
    schedule.  Branch targets are materialized only after a sealed mini
    schedule has been written; the resulting dataset is explicitly not
    training data and contains no held-out EE evaluation.
    """

    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(
            f"refusing to overwrite V0.4 smoke authority: {destination}"
        )
    if destination.resolve() == DEFAULT_OUTPUT_DIR.resolve():
        raise C3V04SourceRunnerError(
            "real-TLE smoke must not write the production V0.4 source output"
        )
    if SMOKE_SOURCE_SEED in SOURCE_SEED_SPLIT:
        raise C3V04SourceRunnerError(
            "development smoke seed overlaps production source split"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    runtime = _runtime(runtime)
    started = time.perf_counter()
    source_manifest = _build_source_manifest()
    source_manifest_sha256 = _validate_source_manifest(source_manifest)
    record, prereg_file_sha256 = _record_and_prereg(
        prereg_path=Path(prereg_path), record=record
    )
    main_authority = _authenticate_main_authority(Path(main_dir))
    with tempfile.TemporaryDirectory(
        prefix=f".{destination.name}.", dir=destination.parent
    ) as temporary:
        archive = runtime.frozen_archive(
            record, Path(tle_root), Path(temporary) / "frozen-tle"
        )
        trainer, checkpoint = runtime.load_trainer(
            record,
            archive,
            run_dir=Path(main_dir),
            users=USERS,
        )
        checkpoint_sha256 = _checkpoint_sha256(checkpoint)
        if checkpoint_sha256 != main_authority["checkpoint_file_sha256"]:
            raise C3V04SourceRunnerError(
                "smoke loader and frozen Main checkpoint disagree"
            )
        network_before = runtime.network_snapshot(trainer)
        replay_before = int(runtime.replay_size(trainer))
        context, scan_receipt, interval_s = _scan_smoke_seed(
            runtime=runtime,
            trainer=trainer,
            archive=archive,
            checkpoint_sha256=checkpoint_sha256,
            source_seed=SMOKE_SOURCE_SEED,
        )
        schedule = _smoke_schedule_payload(
            context,
            source_manifest_sha256=source_manifest_sha256,
        )
        staging = Path(temporary) / "smoke"
        staging.mkdir()
        source_manifest_file_sha256 = _write_once_json(
            staging / "source-manifest.json", source_manifest
        )
        schedule_file_sha256 = _write_once_json(
            staging / "smoke-schedule.json", schedule
        )
        schedule_seal_file_sha256 = _write_once_json(
            staging / "smoke-schedule-seal.json",
            {
                "schema": SMOKE_SEAL_SCHEMA,
                "schedule_file_sha256": schedule_file_sha256,
                "schedule_sha256": schedule["schedule_sha256"],
                "counterfactuals_evaluated": False,
            },
        )
        sealed_schedule = _read_canonical_json(staging / "smoke-schedule.json")
        _validate_smoke_schedule(
            sealed_schedule,
            source_manifest_sha256=source_manifest_sha256,
        )
        comparisons, seed_receipt = _materialize_smoke_context(
            runtime=runtime,
            trainer=trainer,
            archive=archive,
            context=sealed_schedule["contexts"][0],
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
            interval_s=interval_s,
        )
        if not runtime.networks_equal(trainer, network_before):
            raise C3V04SourceRunnerError(
                "smoke mutated Main network parameters"
            )
        if int(runtime.replay_size(trainer)) != replay_before:
            raise C3V04SourceRunnerError(
                "smoke wrote the Main replay buffer"
            )
        dataset = V04C3OpeningDataset.from_comparisons(comparisons)
        dataset.verify()
        # Exercise serialization and independent read-back, but keep the
        # target-bearing engineering dataset ephemeral.  The published smoke
        # authority contains hashes/receipts only and can never be consumed as
        # training data.
        smoke_data = Path(temporary) / "ephemeral-smoke-data"
        smoke_data.mkdir()
        dataset_path = smoke_data / f"c3-smoke-{SMOKE_SOURCE_SEED}.json"
        write_v04_c3_dataset(dataset_path, dataset)
        dataset_sha256 = dataset.verify()
        read_back = read_v04_c3_dataset(dataset_path)
        if read_back.verify() != dataset_sha256:
            raise C3V04SourceRunnerError(
                "smoke dataset round-trip digest changed"
            )
        receipt = {
            "schema": SMOKE_RECEIPT_SCHEMA,
            "status": "PASS_SMOKE_ONLY",
            "mode": "development_real_tle_smoke_only",
            "claim_ceiling": SMOKE_CLAIM_CEILING,
            "source_seed": SMOKE_SOURCE_SEED,
            "split": SMOKE_SOURCE_SPLIT,
            "source_manifest_sha256": source_manifest_sha256,
            "source_manifest_file_sha256": source_manifest_file_sha256,
            "prereg_file_sha256": prereg_file_sha256,
            "prereg_digest": EXPECTED_PREREG_DIGEST,
            "ephemeris_file_set_sha256": EXPECTED_EPHEMERIS_FILE_SET_SHA256,
            "main_authority": main_authority,
            "checkpoint_sha256": checkpoint_sha256,
            "keyed_fading_field_schema": KEYED_FIELD_SCHEMA,
            "keyed_fading_bound": True,
            "schedule_sha256": schedule["schedule_sha256"],
            "schedule_file_sha256": schedule_file_sha256,
            "schedule_sealed_before_counterfactuals": True,
            "scan": scan_receipt,
            "seed_receipt": seed_receipt,
            "comparison_sha256s": [
                value.comparison_sha256 for value in comparisons
            ],
            "ephemeral_dataset_sha256": dataset_sha256,
            "ephemeral_dataset_round_trip_verified": True,
            "published_learning_data": False,
            "scheduled_contexts": 1,
            "scheduled_rows": len(comparisons),
            "materialized_rows": len(comparisons),
            "all_scheduled_rows_materialized": True,
            "nonopening_anchor_present": True,
            "physical_keys_verified": True,
            "state_bitwise_unchanged": True,
            "main_networks_bitwise_unchanged": True,
            "main_replay_unchanged": True,
            "counterfactual_outcomes_evaluated": True,
            "target_sign_filter": False,
            "production_source_schedule_used": False,
            "production_output_touched": False,
            "train_split_present": False,
            "validation_split_present": False,
            "test_split_present": False,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "ee_evaluated": False,
            "training": False,
            "optimizer_called": False,
            "smoke_dataset_for_training": False,
            "elapsed_s": time.perf_counter() - started,
        }
        receipt_file_sha256 = _write_once_json(staging / "receipt.json", receipt)
        _write_once_json(
            staging / "receipt-seal.json",
            {
                "schema": SMOKE_SEAL_SCHEMA,
                "receipt_file_sha256": receipt_file_sha256,
                "source_manifest_file_sha256": source_manifest_file_sha256,
                "schedule_file_sha256": schedule_file_sha256,
                "schedule_seal_file_sha256": schedule_seal_file_sha256,
            },
        )
        try:
            os.replace(staging, destination)
        except FileExistsError as error:
            raise FileExistsError(
                f"refusing to overwrite V0.4 smoke authority: {destination}"
            ) from error
    authenticated = _authenticate_smoke_authority(
        destination,
        source_manifest_sha256=source_manifest_sha256,
        prereg_file_sha256=prereg_file_sha256,
    )
    return {
        "schema": SMOKE_RECEIPT_SCHEMA,
        "status": "PASS_SMOKE_ONLY",
        "claim_ceiling": SMOKE_CLAIM_CEILING,
        "source_seed": SMOKE_SOURCE_SEED,
        "split": SMOKE_SOURCE_SPLIT,
        "schedule_sha256": schedule["schedule_sha256"],
        "receipt_file_sha256": authenticated["receipt_file_sha256"],
        "dataset_rows": len(comparisons),
        "nonopening_anchor_present": True,
        "physical_keys_verified": True,
        "held_out_ee_evaluated": False,
        "training": False,
        "production_output_touched": False,
        "published_learning_data": False,
    }


def prepare(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    tle_root: Path,
    prereg_path: Path = DEFAULT_PREREG,
    main_dir: Path = DEFAULT_MAIN_DIR,
    smoke_dir: Path = DEFAULT_SMOKE_OUTPUT_DIR,
    runtime: C3V04RunnerRuntime | None = None,
    record: Any | None = None,
) -> dict[str, Any]:
    """Seal the outcome-blind source schedule before any branch evaluation."""

    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite V0.4 authority: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    runtime = _runtime(runtime)
    started = time.perf_counter()
    source_manifest = _build_source_manifest()
    source_manifest_sha256 = _validate_source_manifest(source_manifest)
    record, prereg_file_sha256 = _record_and_prereg(
        prereg_path=Path(prereg_path), record=record
    )
    main_authority = _authenticate_main_authority(Path(main_dir))
    smoke_authority = _authenticate_smoke_authority(
        Path(smoke_dir),
        source_manifest_sha256=source_manifest_sha256,
        prereg_file_sha256=prereg_file_sha256,
    )

    all_contexts: list[C3V04ContextCandidate] = []
    source_receipts: list[dict[str, Any]] = []
    checkpoint_sha256: str | None = None
    interval_s: float | None = None
    trainer: Any
    with tempfile.TemporaryDirectory(prefix="mcrl-v04-c3-prepare-") as temporary:
        archive = runtime.frozen_archive(
            record, Path(tle_root), Path(temporary) / "frozen-tle"
        )
        trainer, checkpoint = runtime.load_trainer(
            record,
            archive,
            run_dir=Path(main_dir),
            users=USERS,
        )
        checkpoint_sha256 = _checkpoint_sha256(checkpoint)
        if (
            checkpoint_sha256 != main_authority["checkpoint_file_sha256"]
            or checkpoint_sha256 != smoke_authority["checkpoint_sha256"]
        ):
            raise C3V04SourceRunnerError(
                "prepare loader, frozen Main, and real-TLE smoke disagree"
            )
        network_before = runtime.network_snapshot(trainer)
        replay_before = int(runtime.replay_size(trainer))
        for source_seed, split in sorted(SOURCE_SEED_SPLIT.items()):
            contexts, receipt, interval_s = _scan_seed(
                runtime=runtime,
                trainer=trainer,
                archive=archive,
                checkpoint_sha256=checkpoint_sha256,
                source_seed=source_seed,
                split=split,
                interval_s=interval_s,
            )
            all_contexts.extend(contexts)
            source_receipts.append(receipt)
        if not runtime.networks_equal(trainer, network_before):
            raise C3V04SourceRunnerError(
                "prepare mutated Main network parameters"
            )
        if int(runtime.replay_size(trainer)) != replay_before:
            raise C3V04SourceRunnerError("prepare wrote the Main replay buffer")

    if checkpoint_sha256 is None or interval_s is None:
        raise C3V04SourceRunnerError("prepare did not load a Main checkpoint")
    if not all_contexts:
        raise C3V04SourceRunnerError("prepare collected no C3 context candidates")
    schedule = build_v04_c3_schedule(
        all_contexts,
        seed_split=SOURCE_SEED_SPLIT,
        train_context_goal=TRAIN_CONTEXT_GOAL,
        validation_context_goal=VALIDATION_CONTEXT_GOAL,
        train_row_budget=TRAIN_ROW_BUDGET,
        validation_row_budget=VALIDATION_ROW_BUDGET,
        max_contexts_per_anchor=MAX_CONTEXTS_PER_ANCHOR,
    )
    _check_schedule_contract(schedule)

    with tempfile.TemporaryDirectory(
        prefix=f".{destination.name}.", dir=destination.parent
    ) as temporary:
        staging = Path(temporary) / "publish"
        staging.mkdir()
        source_manifest_file_sha256 = _write_once_json(
            staging / "source-manifest.json", source_manifest
        )
        schedule_file = staging / "schedule.json"
        write_v04_c3_schedule(schedule_file, schedule)
        schedule_file_sha256 = _file_sha256(schedule_file)
        receipt = {
            "schema": PREPARE_RECEIPT_SCHEMA,
            "status": "SEALED_PREOUTCOME",
            "claim_ceiling": CLAIM_CEILING,
            "training": False,
            "held_out_ee_evaluated": False,
            "test_split_present": False,
            "test_split_opened": False,
            "counterfactual_outcomes_evaluated": False,
            "candidate_reference_branches_evaluated": False,
            "main_networks_bitwise_unchanged": True,
            "main_replay_unchanged": True,
            "source_manifest_sha256": source_manifest_sha256,
            "source_manifest_file_sha256": source_manifest_file_sha256,
            "prereg_file_sha256": prereg_file_sha256,
            "prereg_digest": EXPECTED_PREREG_DIGEST,
            "ephemeris_file_set_sha256": EXPECTED_EPHEMERIS_FILE_SET_SHA256,
            "main_authority": main_authority,
            "real_tle_smoke": smoke_authority,
            "checkpoint_sha256": checkpoint_sha256,
            "keyed_field_schema": KEYED_FIELD_SCHEMA,
            "kappa_bits_hex": KAPPA_BITS.hex(),
            "lambda_bits_per_j_hex": LAMBDA_BITS_PER_J.hex(),
            "interval_s_hex": float(interval_s).hex(),
            "seed_split": _expected_seed_split(),
            "schedule_sha256": schedule.schedule_sha256,
            "schedule_file_sha256": schedule_file_sha256,
            "train_context_goal": TRAIN_CONTEXT_GOAL,
            "validation_context_goal": VALIDATION_CONTEXT_GOAL,
            "train_row_budget": TRAIN_ROW_BUDGET,
            "validation_row_budget": VALIDATION_ROW_BUDGET,
            "max_contexts_per_anchor": MAX_CONTEXTS_PER_ANCHOR,
            "context_balance": _context_balance(schedule),
            "source_seed_receipts": source_receipts,
            "nonopening_contexts": sum(
                row.step_index > 0
                for row in (*schedule.train, *schedule.validation)
            ),
            "elapsed_s": time.perf_counter() - started,
        }
        prepare_receipt_file_sha256 = _write_once_json(
            staging / "prepare-receipt.json", receipt
        )
        _write_once_json(
            staging / "prepare-receipt-seal.json",
            {
                "schema": PREPARE_SEAL_SCHEMA,
                "prepare_receipt_file_sha256": prepare_receipt_file_sha256,
                "source_manifest_file_sha256": source_manifest_file_sha256,
                "schedule_file_sha256": schedule_file_sha256,
                "smoke_receipt_file_sha256": smoke_authority[
                    "receipt_file_sha256"
                ],
                "smoke_receipt_seal_file_sha256": smoke_authority[
                    "receipt_seal_file_sha256"
                ],
            },
        )
        try:
            os.replace(staging, destination)
        except FileExistsError as error:
            raise FileExistsError(
                f"refusing to overwrite V0.4 authority: {destination}"
            ) from error
    return receipt


def _validate_prepare_receipt(
    receipt: Mapping[str, Any], *, source_manifest_sha256: str
) -> None:
    required = {
        "schema",
        "status",
        "claim_ceiling",
        "training",
        "held_out_ee_evaluated",
        "test_split_present",
        "test_split_opened",
        "counterfactual_outcomes_evaluated",
        "candidate_reference_branches_evaluated",
        "main_networks_bitwise_unchanged",
        "main_replay_unchanged",
        "source_manifest_sha256",
        "source_manifest_file_sha256",
        "prereg_file_sha256",
        "prereg_digest",
        "ephemeris_file_set_sha256",
        "main_authority",
        "real_tle_smoke",
        "checkpoint_sha256",
        "keyed_field_schema",
        "kappa_bits_hex",
        "lambda_bits_per_j_hex",
        "interval_s_hex",
        "seed_split",
        "schedule_sha256",
        "schedule_file_sha256",
        "train_context_goal",
        "validation_context_goal",
        "train_row_budget",
        "validation_row_budget",
        "max_contexts_per_anchor",
        "context_balance",
        "source_seed_receipts",
        "nonopening_contexts",
        "elapsed_s",
    }
    if set(receipt) != required:
        raise C3V04SourceRunnerError("prepare receipt schema is unexpected")
    if (
        receipt["schema"] != PREPARE_RECEIPT_SCHEMA
        or receipt["status"] != "SEALED_PREOUTCOME"
        or receipt["claim_ceiling"] != CLAIM_CEILING
        or receipt["training"] is not False
        or receipt["held_out_ee_evaluated"] is not False
        or receipt["test_split_present"] is not False
        or receipt["test_split_opened"] is not False
        or receipt["counterfactual_outcomes_evaluated"] is not False
        or receipt["candidate_reference_branches_evaluated"] is not False
        or receipt["main_networks_bitwise_unchanged"] is not True
        or receipt["main_replay_unchanged"] is not True
        or receipt["source_manifest_sha256"] != source_manifest_sha256
        or receipt["prereg_file_sha256"] != EXPECTED_PREREG_FILE_SHA256
        or receipt["prereg_digest"] != EXPECTED_PREREG_DIGEST
        or receipt["ephemeris_file_set_sha256"]
        != EXPECTED_EPHEMERIS_FILE_SET_SHA256
        or receipt["main_authority"]
        != {
            "status_file_sha256": EXPECTED_MAIN_STATUS_FILE_SHA256,
            "episode_logs_file_sha256": EXPECTED_MAIN_EPISODE_LOGS_FILE_SHA256,
            "checkpoint_file_sha256": EXPECTED_MAIN_CHECKPOINT_SHA256,
        }
        or receipt["checkpoint_sha256"] != EXPECTED_MAIN_CHECKPOINT_SHA256
        or receipt["keyed_field_schema"] != KEYED_FIELD_SCHEMA
        or receipt["seed_split"] != _expected_seed_split()
        or receipt["train_context_goal"] != TRAIN_CONTEXT_GOAL
        or receipt["validation_context_goal"] != VALIDATION_CONTEXT_GOAL
        or receipt["train_row_budget"] != TRAIN_ROW_BUDGET
        or receipt["validation_row_budget"] != VALIDATION_ROW_BUDGET
        or receipt["max_contexts_per_anchor"] != MAX_CONTEXTS_PER_ANCHOR
    ):
        raise C3V04SourceRunnerError("prepare receipt authority changed")
    for field in (
        "source_manifest_file_sha256",
        "prereg_file_sha256",
        "checkpoint_sha256",
        "schedule_sha256",
        "schedule_file_sha256",
    ):
        _digest(receipt[field], field=field)
    smoke = receipt["real_tle_smoke"]
    expected_smoke_fields = {
        "receipt_file_sha256",
        "receipt_seal_file_sha256",
        "source_manifest_file_sha256",
        "schedule_file_sha256",
        "schedule_seal_file_sha256",
        "schedule_sha256",
        "checkpoint_sha256",
        "prereg_file_sha256",
        "materialized_rows",
        "published_learning_data",
    }
    if (
        not isinstance(smoke, Mapping)
        or set(smoke) != expected_smoke_fields
        or smoke["checkpoint_sha256"] != EXPECTED_MAIN_CHECKPOINT_SHA256
        or smoke["prereg_file_sha256"] != EXPECTED_PREREG_FILE_SHA256
        or type(smoke["materialized_rows"]) is not int
        or smoke["materialized_rows"] <= 0
        or smoke["published_learning_data"] is not False
    ):
        raise C3V04SourceRunnerError("prepare smoke authority changed")
    for field in expected_smoke_fields - {
        "materialized_rows",
        "published_learning_data",
    }:
        _digest(smoke[field], field=f"real_tle_smoke.{field}")
    try:
        interval = float.fromhex(str(receipt["interval_s_hex"]))
        kappa = float.fromhex(str(receipt["kappa_bits_hex"]))
        multiplier = float.fromhex(str(receipt["lambda_bits_per_j_hex"]))
    except (TypeError, ValueError) as error:
        raise C3V04SourceRunnerError(
            "prepare receipt frozen constants are malformed"
        ) from error
    if (
        not math.isfinite(interval)
        or interval <= 0.0
        or not math.isfinite(kappa)
        or kappa != KAPPA_BITS
        or not math.isfinite(multiplier)
        or multiplier != LAMBDA_BITS_PER_J
    ):
        raise C3V04SourceRunnerError(
            "prepare receipt frozen constants drifted"
        )
    if not isinstance(receipt["context_balance"], dict):
        raise C3V04SourceRunnerError("prepare receipt context balance is malformed")
    elapsed = receipt["elapsed_s"]
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0.0
    ):
        raise C3V04SourceRunnerError("prepare receipt elapsed time is invalid")


def _load_prepared_authority(
    output_dir: Path, *, prereg_path: Path | None
) -> tuple[dict[str, Any], dict[str, Any], C3V04SourceSchedule]:
    destination = Path(output_dir)
    if destination.is_symlink() or not destination.is_dir():
        raise C3V04SourceRunnerError(
            f"V0.4 prepared authority is missing or not a directory: {destination}"
        )
    manifest = _read_canonical_json(destination / "source-manifest.json")
    source_manifest_sha256 = _validate_source_manifest(manifest)
    receipt = _read_canonical_json(destination / "prepare-receipt.json")
    _validate_prepare_receipt(
        receipt, source_manifest_sha256=source_manifest_sha256
    )
    if _file_sha256(destination / "source-manifest.json") != receipt[
        "source_manifest_file_sha256"
    ]:
        raise C3V04SourceRunnerError("sealed source manifest bytes changed")
    if prereg_path is not None and _file_sha256(Path(prereg_path)) != receipt[
        "prereg_file_sha256"
    ]:
        raise C3V04SourceRunnerError("frozen PREREG bytes changed")
    seal = _read_canonical_json(destination / "prepare-receipt-seal.json")
    if (
        set(seal)
        != {
            "schema",
            "prepare_receipt_file_sha256",
            "source_manifest_file_sha256",
            "schedule_file_sha256",
            "smoke_receipt_file_sha256",
            "smoke_receipt_seal_file_sha256",
        }
        or seal.get("schema") != PREPARE_SEAL_SCHEMA
        or seal.get("prepare_receipt_file_sha256")
        != _file_sha256(destination / "prepare-receipt.json")
        or seal.get("source_manifest_file_sha256")
        != receipt["source_manifest_file_sha256"]
        or seal.get("smoke_receipt_file_sha256")
        != receipt["real_tle_smoke"]["receipt_file_sha256"]
        or seal.get("smoke_receipt_seal_file_sha256")
        != receipt["real_tle_smoke"]["receipt_seal_file_sha256"]
    ):
        raise C3V04SourceRunnerError("prepare receipt seal is invalid")
    schedule_path = destination / "schedule.json"
    if _file_sha256(schedule_path) != receipt["schedule_file_sha256"]:
        raise C3V04SourceRunnerError("sealed C3 schedule bytes changed")
    schedule = read_v04_c3_schedule(schedule_path)
    _check_schedule_contract(schedule)
    if schedule.schedule_sha256 != receipt["schedule_sha256"]:
        raise C3V04SourceRunnerError("prepare receipt and schedule disagree")
    if seal.get("schedule_file_sha256") != receipt["schedule_file_sha256"]:
        raise C3V04SourceRunnerError("prepare seal and schedule disagree")
    return manifest, receipt, schedule


def _materialize_seed(
    *,
    runtime: C3V04RunnerRuntime,
    trainer: Any,
    archive: Any,
    schedule: C3V04SourceSchedule,
    source_seed: int,
    split: str,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    interval_s: float,
) -> tuple[V04C3OpeningDataset, list[dict[str, Any]], dict[str, Any]]:
    contexts = _schedule_rows(schedule, source_seed=source_seed)
    if not contexts:
        raise C3V04SourceRunnerError(
            f"sealed schedule has no contexts for source seed {source_seed}"
        )
    by_step: dict[int, list[C3V04ContextCandidate]] = {}
    expected: set[tuple[str, int, int, int]] = set()
    for context in contexts:
        by_step.setdefault(int(context.step_index), []).append(context)
        for candidate_action in context.candidate_actions:
            key = (
                context.anchor_sha256,
                context.focal_user,
                context.reference_action,
                int(candidate_action),
            )
            if key in expected:
                raise C3V04SourceRunnerError(
                    "sealed schedule repeats a materialization identity"
                )
            expected.add(key)
    field = _field_for_seed(checkpoint_sha256, source_seed)
    wrapped = runtime.make_environment(archive, users=USERS)
    environment = _bind_field(wrapped, field)
    current_interval = float(runtime.interval_s(wrapped))
    if current_interval != interval_s:
        raise C3V04SourceRunnerError(
            "replayed environment decision interval differs from prepare"
        )
    env_rng, mobility_rng, _action_rng, _control_rng = runtime.evaluation_rngs(
        int(source_seed)
    )
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    comparisons: list[V04C3OpeningComparison] = []
    materialized: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int, int]] = set()
    reached_steps: set[int] = set()
    for ordinal in range(MAX_SOURCE_STEPS):
        reference = _actions(
            runtime.main_actions(
                trainer, wrapped, states, masks, observation, env_rng
            ),
            users=USERS,
        )
        state = encode_ee_axis_v04_c3_state(
            environment,
            observation,
            interval_s=current_interval,
            kappa_bits=KAPPA_BITS,
        )
        step = int(observation.step_index)
        anchor = _anchor_sha256(
            source_seed=source_seed,
            step_index=step,
            state=state,
            reference_actions=reference,
        )
        current_contexts = by_step.get(step, [])
        for context in current_contexts:
            if context.anchor_sha256 != anchor:
                raise C3V04SourceRunnerError(
                    "replayed C3 anchor digest differs from sealed schedule"
                )
            if context.state_observation_sha256 != state.state_sha256:
                raise C3V04SourceRunnerError(
                    "replayed C3 state digest differs from sealed schedule"
                )
            if int(reference[context.focal_user]) != context.reference_action:
                raise C3V04SourceRunnerError(
                    "replayed Main reference action differs from sealed schedule"
                )
            table = observation.candidates.slot_tables[context.focal_user]
            reference_physical_key = _physical_key(
                table, context.reference_action
            )
            if reference_physical_key != context.reference_physical_key:
                raise C3V04SourceRunnerError(
                    "replayed Main reference physical key differs from schedule"
                )
            reached_steps.add(step)
            for candidate_action, candidate_physical_key in zip(
                context.candidate_actions,
                context.candidate_physical_keys,
                strict=True,
            ):
                replayed_candidate_key = _physical_key(table, candidate_action)
                if replayed_candidate_key != candidate_physical_key:
                    raise C3V04SourceRunnerError(
                        "replayed candidate physical key differs from schedule"
                    )
                identity = (
                    context.anchor_sha256,
                    context.focal_user,
                    context.reference_action,
                    int(candidate_action),
                )
                if identity in seen:
                    raise C3V04SourceRunnerError(
                        "replayed schedule emitted a duplicate comparison"
                    )
                reference_actions = np.array(reference, dtype=np.int64, copy=True)
                candidate_actions = np.array(reference, dtype=np.int64, copy=True)
                candidate_actions[context.focal_user] = int(candidate_action)
                provenance = V04C3OpeningProvenance(
                    source_policy_version=SOURCE_POLICY_VERSION,
                    anchor_sha256=context.anchor_sha256,
                    source_manifest_sha256=source_manifest_sha256,
                    checkpoint_sha256=checkpoint_sha256,
                    common_random_field_sha256=field.root_digest,
                    c3_source_rule=C3_V04_INFORMED_SOURCE_RULE,
                )
                comparison = produce_v04_c3_opening_comparison(
                    environment,
                    observation=observation,
                    state_observation=state,
                    reference_actions=reference_actions,
                    candidate_actions=candidate_actions,
                    focal_user=context.focal_user,
                    common_random_field=field,
                    provenance=provenance,
                    rng=env_rng,
                    lambda_bits_per_j=LAMBDA_BITS_PER_J,
                    interval_s=current_interval,
                    kappa_bits=KAPPA_BITS,
                )
                comparison.verify()
                pair = comparison.pair
                if (
                    pair.anchor_sha256 != context.anchor_sha256
                    or pair.focal_user != context.focal_user
                    or pair.reference_action != context.reference_action
                    or pair.candidate_action != int(candidate_action)
                    or comparison.reference_physical_key
                    != context.reference_physical_key
                    or comparison.candidate_physical_key
                    != candidate_physical_key
                    or comparison.state_observation_sha256 != state.state_sha256
                ):
                    raise C3V04SourceRunnerError(
                        "V0.4 producer emitted an unscheduled comparison"
                    )
                comparisons.append(comparison)
                seen.add(identity)
                materialized.append(
                    {
                        "source_seed": int(source_seed),
                        "split": split,
                        "anchor_sha256": context.anchor_sha256,
                        "step_index": step,
                        "focal_user": context.focal_user,
                        "reference_action": context.reference_action,
                        "candidate_action": int(candidate_action),
                        "reference_physical_key": _physical_key_payload(
                            context.reference_physical_key
                        ),
                        "candidate_physical_key": _physical_key_payload(
                            candidate_physical_key
                        ),
                        "comparison_sha256": comparison.comparison_sha256,
                    }
                )
        if seen == expected:
            # The schedule is sealed and sorted; no further materialization is
            # admissible after the final scheduled identity has been reached.
            break
        if ordinal + 1 >= MAX_SOURCE_STEPS:
            break
        following = _step_forward(wrapped, reference, env_rng)
        if following is None:
            break
        states, masks, observation = following
    if seen != expected:
        missing = sorted(expected - seen)
        raise C3V04SourceRunnerError(
            f"source seed {source_seed} omitted scheduled comparisons: {missing[:3]}"
        )
    if len(comparisons) != len(expected):
        raise C3V04SourceRunnerError(
            f"source seed {source_seed} materialized an unexpected row count"
        )
    dataset = V04C3OpeningDataset.from_comparisons(comparisons)
    if len(dataset.rows) != len(expected):
        raise C3V04SourceRunnerError(
            f"source seed {source_seed} dataset deduplicated scheduled rows"
        )
    seed_receipt = {
        "source_seed": int(source_seed),
        "split": split,
        "keyed_field_sha256": field.root_digest,
        "scheduled_rows": len(expected),
        "materialized_rows": len(comparisons),
        "materialized_steps": sorted(reached_steps),
        "materialized_nonopening_steps": sum(step > 0 for step in reached_steps),
        "target_sign_filter": False,
    }
    return dataset, materialized, seed_receipt


def generate(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    tle_root: Path,
    prereg_path: Path = DEFAULT_PREREG,
    main_dir: Path = DEFAULT_MAIN_DIR,
    runtime: C3V04RunnerRuntime | None = None,
    record: Any | None = None,
) -> dict[str, Any]:
    """Materialize every sealed C3 schedule row into one dataset per seed."""

    destination = Path(output_dir)
    if (destination / "source-data").exists() or (
        destination / "source-data"
    ).is_symlink():
        raise FileExistsError("refusing to overwrite generated V0.4 source data")
    runtime = _runtime(runtime)
    manifest, prepare_receipt, schedule = _load_prepared_authority(
        destination, prereg_path=Path(prereg_path)
    )
    record, prereg_file_sha256 = _record_and_prereg(
        prereg_path=Path(prereg_path), record=record
    )
    main_authority = _authenticate_main_authority(Path(main_dir))
    if (
        main_authority != prepare_receipt["main_authority"]
        or prereg_file_sha256 != prepare_receipt["prereg_file_sha256"]
    ):
        raise C3V04SourceRunnerError(
            "generate Main or PREREG lineage differs from sealed prepare"
        )
    source_manifest_sha256 = _digest(
        manifest["source_manifest_sha256"], field="source_manifest_sha256"
    )
    checkpoint_sha256 = _digest(
        prepare_receipt["checkpoint_sha256"], field="checkpoint_sha256"
    )
    interval_s = float.fromhex(str(prepare_receipt["interval_s_hex"]))
    started = time.perf_counter()
    datasets: dict[int, V04C3OpeningDataset] = {}
    all_rows: dict[str, list[dict[str, Any]]] = {}
    seed_receipts: list[dict[str, Any]] = []
    # Stage underneath the prepared authority directory so that the final
    # os.replace remains an atomic same-filesystem publish.  tempfile's
    # default /tmp root can be a different mount from the artifact tree and
    # therefore fail with EXDEV after all source rows have been generated.
    with tempfile.TemporaryDirectory(
        prefix=".source-data-staging-",
        dir=destination,
    ) as temporary:
        archive = runtime.frozen_archive(
            record, Path(tle_root), Path(temporary) / "frozen-tle"
        )
        trainer, checkpoint = runtime.load_trainer(
            record,
            archive,
            run_dir=Path(main_dir),
            users=USERS,
        )
        loaded_checkpoint_sha256 = _checkpoint_sha256(checkpoint)
        if (
            loaded_checkpoint_sha256 != checkpoint_sha256
            or loaded_checkpoint_sha256
            != main_authority["checkpoint_file_sha256"]
        ):
            raise C3V04SourceRunnerError(
                "loaded Main checkpoint differs from sealed prepare checkpoint"
            )
        network_before = runtime.network_snapshot(trainer)
        replay_before = int(runtime.replay_size(trainer))
        staging = Path(temporary) / "source-data"
        staging.mkdir()
        for source_seed, split in sorted(SOURCE_SEED_SPLIT.items()):
            dataset, rows, receipt = _materialize_seed(
                runtime=runtime,
                trainer=trainer,
                archive=archive,
                schedule=schedule,
                source_seed=source_seed,
                split=split,
                source_manifest_sha256=source_manifest_sha256,
                checkpoint_sha256=checkpoint_sha256,
                interval_s=interval_s,
            )
            datasets[source_seed] = dataset
            all_rows[str(source_seed)] = rows
            seed_receipts.append(receipt)
            write_v04_c3_dataset(
                staging / f"c3-{source_seed}.json", dataset
            )
        if not runtime.networks_equal(trainer, network_before):
            raise C3V04SourceRunnerError(
                "generate mutated Main network parameters"
            )
        if int(runtime.replay_size(trainer)) != replay_before:
            raise C3V04SourceRunnerError("generate wrote the Main replay buffer")
        dataset_file_sha256s = {
            str(seed): _file_sha256(staging / f"c3-{seed}.json")
            for seed in sorted(SOURCE_SEED_SPLIT)
        }
        dataset_sha256s = {
            str(seed): datasets[seed].verify()
            for seed in sorted(SOURCE_SEED_SPLIT)
        }
        receipt = {
            "schema": GENERATE_RECEIPT_SCHEMA,
            "status": "PASS",
            "claim_ceiling": CLAIM_CEILING,
            "training": False,
            "held_out_ee_evaluated": False,
            "test_split_present": False,
            "test_split_opened": False,
            "counterfactual_outcomes_evaluated": True,
            "target_sign_filter": False,
            "target_sign_filter_rule": "none",
            "source_manifest_sha256": source_manifest_sha256,
            "prereg_file_sha256": prereg_file_sha256,
            "main_authority": main_authority,
            "real_tle_smoke": prepare_receipt["real_tle_smoke"],
            "checkpoint_sha256": checkpoint_sha256,
            "schedule_sha256": schedule.schedule_sha256,
            "schedule_file_sha256": prepare_receipt["schedule_file_sha256"],
            "dataset_file_sha256s": dataset_file_sha256s,
            "dataset_sha256s": dataset_sha256s,
            "seed_split": _expected_seed_split(),
            "seed_receipts": seed_receipts,
            "materialized_rows": all_rows,
            "main_networks_bitwise_unchanged": True,
            "main_replay_unchanged": True,
            "elapsed_s": time.perf_counter() - started,
        }
        receipt_file_sha256 = _write_once_json(staging / "receipt.json", receipt)
        _write_once_json(
            staging / "receipt-seal.json",
            {
                "schema": GENERATE_SEAL_SCHEMA,
                "receipt_file_sha256": receipt_file_sha256,
            },
        )
        try:
            os.replace(staging, destination / "source-data")
        except FileExistsError as error:
            raise FileExistsError(
                "refusing to overwrite generated V0.4 source data"
            ) from error
    return {
        "schema": GENERATE_RECEIPT_SCHEMA,
        "status": "PASS_SOURCE_DATA_PUBLISHED",
        "claim_ceiling": CLAIM_CEILING,
        "source_manifest_sha256": source_manifest_sha256,
        "checkpoint_sha256": checkpoint_sha256,
        "schedule_sha256": schedule.schedule_sha256,
        "receipt_file_sha256": receipt_file_sha256,
        "dataset_rows": {
            str(seed): len(dataset.rows)
            for seed, dataset in sorted(datasets.items())
        },
        "target_sign_filter": False,
        "held_out_ee_evaluated": False,
        "training": False,
    }


def _row_identity(row: Mapping[str, Any]) -> tuple[str, int, int, int, int]:
    return (
        _digest(row.get("anchor_sha256"), field="materialized.anchor_sha256"),
        int(row["focal_user"]),
        int(row["reference_action"]),
        int(row["candidate_action"]),
        int(row["step_index"]),
    )


def _expected_materialized_identities(
    schedule: C3V04SourceSchedule, *, source_seed: int
) -> set[tuple[str, int, int, int, int]]:
    return {
        (
            context.anchor_sha256,
            context.focal_user,
            context.reference_action,
            int(candidate),
            context.step_index,
        )
        for context in _schedule_rows(schedule, source_seed=source_seed)
        for candidate in context.candidate_actions
    }


def _expected_materialized_physical_keys(
    schedule: C3V04SourceSchedule, *, source_seed: int
) -> dict[
    tuple[str, int, int, int, int],
    tuple[list[int] | None, list[int]],
]:
    return {
        (
            context.anchor_sha256,
            context.focal_user,
            context.reference_action,
            int(candidate_action),
            context.step_index,
        ): (
            _physical_key_payload(context.reference_physical_key),
            _physical_key_payload(candidate_physical_key),
        )
        for context in _schedule_rows(schedule, source_seed=source_seed)
        for candidate_action, candidate_physical_key in zip(
            context.candidate_actions,
            context.candidate_physical_keys,
            strict=True,
        )
    }


def _validate_generate_receipt(
    receipt: Mapping[str, Any],
    *,
    source_manifest_sha256: str,
    schedule: C3V04SourceSchedule,
) -> None:
    required = {
        "schema",
        "status",
        "claim_ceiling",
        "training",
        "held_out_ee_evaluated",
        "test_split_present",
        "test_split_opened",
        "counterfactual_outcomes_evaluated",
        "target_sign_filter",
        "target_sign_filter_rule",
        "source_manifest_sha256",
        "prereg_file_sha256",
        "main_authority",
        "real_tle_smoke",
        "checkpoint_sha256",
        "schedule_sha256",
        "schedule_file_sha256",
        "dataset_file_sha256s",
        "dataset_sha256s",
        "seed_split",
        "seed_receipts",
        "materialized_rows",
        "main_networks_bitwise_unchanged",
        "main_replay_unchanged",
        "elapsed_s",
    }
    if set(receipt) != required:
        raise C3V04SourceRunnerError("generate receipt schema is unexpected")
    if (
        receipt["schema"] != GENERATE_RECEIPT_SCHEMA
        or receipt["status"] != "PASS"
        or receipt["claim_ceiling"] != CLAIM_CEILING
        or receipt["training"] is not False
        or receipt["held_out_ee_evaluated"] is not False
        or receipt["test_split_present"] is not False
        or receipt["test_split_opened"] is not False
        or receipt["counterfactual_outcomes_evaluated"] is not True
        or receipt["target_sign_filter"] is not False
        or receipt["target_sign_filter_rule"] != "none"
        or receipt["source_manifest_sha256"] != source_manifest_sha256
        or receipt["prereg_file_sha256"] != EXPECTED_PREREG_FILE_SHA256
        or receipt["main_authority"]
        != {
            "status_file_sha256": EXPECTED_MAIN_STATUS_FILE_SHA256,
            "episode_logs_file_sha256": EXPECTED_MAIN_EPISODE_LOGS_FILE_SHA256,
            "checkpoint_file_sha256": EXPECTED_MAIN_CHECKPOINT_SHA256,
        }
        or receipt["checkpoint_sha256"] != EXPECTED_MAIN_CHECKPOINT_SHA256
        or receipt["schedule_sha256"] != schedule.schedule_sha256
        or receipt["seed_split"] != _expected_seed_split()
        or receipt["main_networks_bitwise_unchanged"] is not True
        or receipt["main_replay_unchanged"] is not True
    ):
        raise C3V04SourceRunnerError("generate receipt authority changed")
    for field in (
        "source_manifest_sha256",
        "prereg_file_sha256",
        "checkpoint_sha256",
        "schedule_sha256",
        "schedule_file_sha256",
    ):
        _digest(receipt[field], field=field)
    smoke = receipt["real_tle_smoke"]
    if (
        not isinstance(smoke, Mapping)
        or smoke.get("checkpoint_sha256") != EXPECTED_MAIN_CHECKPOINT_SHA256
        or smoke.get("prereg_file_sha256") != EXPECTED_PREREG_FILE_SHA256
        or smoke.get("published_learning_data") is not False
    ):
        raise C3V04SourceRunnerError("generate smoke lineage changed")
    for field in ("dataset_file_sha256s", "dataset_sha256s"):
        values = receipt[field]
        if not isinstance(values, dict) or set(values) != set(_expected_seed_split()):
            raise C3V04SourceRunnerError(
                f"generate receipt {field} map is incomplete"
            )
        for seed, value in values.items():
            _digest(value, field=f"{field}[{seed}]")
    elapsed = receipt["elapsed_s"]
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0.0
    ):
        raise C3V04SourceRunnerError("generate receipt elapsed time is invalid")


def verify(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    prereg_path: Path | None = DEFAULT_PREREG,
) -> dict[str, Any]:
    """Independently verify prepare/generate receipts and all C3 datasets."""

    destination = Path(output_dir)
    manifest, prepare_receipt, schedule = _load_prepared_authority(
        destination, prereg_path=Path(prereg_path) if prereg_path is not None else None
    )
    data_root = destination / "source-data"
    if data_root.is_symlink() or not data_root.is_dir():
        raise C3V04SourceRunnerError(
            "published V0.4 source-data is missing or not a directory"
        )
    receipt = _read_canonical_json(data_root / "receipt.json")
    source_manifest_sha256 = _digest(
        manifest["source_manifest_sha256"], field="source_manifest_sha256"
    )
    _validate_generate_receipt(
        receipt,
        source_manifest_sha256=source_manifest_sha256,
        schedule=schedule,
    )
    receipt_seal = _read_canonical_json(data_root / "receipt-seal.json")
    if (
        set(receipt_seal) != {"schema", "receipt_file_sha256"}
        or receipt_seal.get("schema") != GENERATE_SEAL_SCHEMA
        or receipt_seal.get("receipt_file_sha256")
        != _file_sha256(data_root / "receipt.json")
    ):
        raise C3V04SourceRunnerError("generate receipt seal is invalid")
    if receipt["schedule_file_sha256"] != prepare_receipt[
        "schedule_file_sha256"
    ]:
        raise C3V04SourceRunnerError(
            "generate receipt and prepare schedule seal disagree"
        )
    if (
        receipt["prereg_file_sha256"]
        != prepare_receipt["prereg_file_sha256"]
        or receipt["main_authority"] != prepare_receipt["main_authority"]
        or receipt["real_tle_smoke"] != prepare_receipt["real_tle_smoke"]
    ):
        raise C3V04SourceRunnerError(
            "generate and prepare frozen-source lineage disagree"
        )
    checkpoint_sha256 = _digest(
        prepare_receipt["checkpoint_sha256"], field="checkpoint_sha256"
    )
    if receipt["checkpoint_sha256"] != checkpoint_sha256:
        raise C3V04SourceRunnerError(
            "generate receipt checkpoint lineage disagrees"
        )

    materialized_rows = receipt["materialized_rows"]
    if not isinstance(materialized_rows, dict):
        raise C3V04SourceRunnerError("generate materialized rows are malformed")
    verified_rows: dict[str, int] = {}
    for source_seed, split in sorted(SOURCE_SEED_SPLIT.items()):
        seed_key = str(source_seed)
        dataset_path = data_root / f"c3-{source_seed}.json"
        expected_file_sha256 = receipt["dataset_file_sha256s"][seed_key]
        if _file_sha256(dataset_path) != expected_file_sha256:
            raise C3V04SourceRunnerError(
                f"published C3 dataset bytes changed for source seed {source_seed}"
            )
        dataset = read_v04_c3_dataset(dataset_path)
        if dataset.verify() != receipt["dataset_sha256s"][seed_key]:
            raise C3V04SourceRunnerError(
                f"published C3 dataset digest changed for source seed {source_seed}"
            )
        expected_field = _field_for_seed(checkpoint_sha256, source_seed)
        if (
            dataset.source_policy_version != SOURCE_POLICY_VERSION
            or dataset.source_manifest_sha256 != source_manifest_sha256
            or dataset.checkpoint_sha256 != checkpoint_sha256
            or dataset.common_random_field_sha256 != expected_field.root_digest
            or dataset.state_schema != EE_AXIS_V04_C3_STATE_SCHEMA
            or dataset.kappa_bits != KAPPA_BITS
            or any(row.pair.source_route != "C3" for row in dataset.rows)
        ):
            raise C3V04SourceRunnerError(
                f"dataset lineage changed for source seed {source_seed}"
            )
        rows = materialized_rows.get(seed_key)
        if not isinstance(rows, list):
            raise C3V04SourceRunnerError(
                f"materialized receipt rows missing for source seed {source_seed}"
            )
        observed_identities = {_row_identity(row) for row in rows}
        expected_identities = _expected_materialized_identities(
            schedule, source_seed=source_seed
        )
        expected_physical_keys = _expected_materialized_physical_keys(
            schedule, source_seed=source_seed
        )
        if observed_identities != expected_identities:
            raise C3V04SourceRunnerError(
                f"scheduled comparison identity set changed for source seed {source_seed}"
            )
        digest_by_identity: dict[tuple[str, int, int, int, int], str] = {}
        for row in rows:
            identity = _row_identity(row)
            expected_reference_key, expected_candidate_key = (
                expected_physical_keys[identity]
            )
            if (
                row.get("reference_physical_key") != expected_reference_key
                or row.get("candidate_physical_key")
                != expected_candidate_key
            ):
                raise C3V04SourceRunnerError(
                    "materialized physical keys disagree with schedule"
                )
            digest_by_identity[identity] = _digest(
                row.get("comparison_sha256"),
                field="materialized.comparison_sha256",
            )
            if row.get("source_seed") != source_seed or row.get("split") != split:
                raise C3V04SourceRunnerError(
                    "materialized receipt row disagrees with seed split"
                )
        pair_digests: dict[tuple[str, int, int, int, int], str] = {}
        for dataset_row in dataset.rows:
            pair = dataset_row.pair
            matching_receipts = [
                row
                for row in rows
                if row.get("comparison_sha256")
                == dataset_row.producer_comparison_sha256
            ]
            if len(matching_receipts) != 1:
                raise C3V04SourceRunnerError(
                    "dataset row has no unique producer receipt"
                )
            identity = (
                pair.anchor_sha256,
                pair.focal_user,
                pair.reference_action,
                pair.candidate_action,
                int(matching_receipts[0]["step_index"]),
            )
            if (
                matching_receipts[0].get("reference_physical_key")
                != _physical_key_payload(dataset_row.reference_physical_key)
                or matching_receipts[0].get("candidate_physical_key")
                != _physical_key_payload(dataset_row.candidate_physical_key)
            ):
                raise C3V04SourceRunnerError(
                    "dataset physical keys disagree with materialized receipt"
                )
            pair_digests[identity] = dataset_row.producer_comparison_sha256
        if pair_digests != digest_by_identity:
            raise C3V04SourceRunnerError(
                f"dataset rows disagree with materialized receipt for source seed {source_seed}"
            )
        verified_rows[seed_key] = len(dataset.rows)
    return {
        "schema": GENERATE_RECEIPT_SCHEMA,
        "status": "PASS_VERIFIED",
        "claim_ceiling": CLAIM_CEILING,
        "source_manifest_sha256": source_manifest_sha256,
        "checkpoint_sha256": checkpoint_sha256,
        "schedule_sha256": schedule.schedule_sha256,
        "dataset_rows": verified_rows,
        "test_split_present": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "training": False,
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase", choices=("prepare", "generate", "verify", "smoke")
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--main-dir", type=Path, default=DEFAULT_MAIN_DIR)
    parser.add_argument(
        "--smoke-dir", type=Path, default=DEFAULT_SMOKE_OUTPUT_DIR
    )
    parser.add_argument("--tle-root", type=Path, required=False)
    args = parser.parse_args(argv)
    if args.phase != "verify" and args.tle_root is None:
        parser.error("--tle-root is required for prepare/generate/smoke")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    output_dir = args.output_dir
    if output_dir is None:
        output_dir = (
            DEFAULT_SMOKE_OUTPUT_DIR
            if args.phase == "smoke"
            else DEFAULT_OUTPUT_DIR
        )
    if args.phase == "prepare":
        result = prepare(
            output_dir=output_dir,
            tle_root=args.tle_root,
            prereg_path=args.prereg,
            main_dir=args.main_dir,
            smoke_dir=args.smoke_dir,
        )
    elif args.phase == "generate":
        result = generate(
            output_dir=output_dir,
            tle_root=args.tle_root,
            prereg_path=args.prereg,
            main_dir=args.main_dir,
        )
    elif args.phase == "smoke":
        result = smoke(
            output_dir=output_dir,
            tle_root=args.tle_root,
            prereg_path=args.prereg,
            main_dir=args.main_dir,
        )
    else:
        result = verify(output_dir=output_dir, prereg_path=args.prereg)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI delegation
    raise SystemExit(main())


__all__ = [
    "ANCHOR_SCHEMA",
    "C3V04RunnerRuntime",
    "C3V04SourceRunnerError",
    "CLAIM_CEILING",
    "INITIALIZATION_SEEDS",
    "KAPPA_BITS",
    "KEYED_FIELD_SCHEMA",
    "LAMBDA_BITS_PER_J",
    "MAX_SOURCE_STEPS",
    "GENERATE_SEAL_SCHEMA",
    "DEFAULT_SMOKE_OUTPUT_DIR",
    "SMOKE_CLAIM_CEILING",
    "SMOKE_MAX_CANDIDATES",
    "SMOKE_RECEIPT_SCHEMA",
    "SMOKE_SCHEDULE_SCHEMA",
    "SMOKE_SOURCE_SEED",
    "SMOKE_SOURCE_SPLIT",
    "SOURCE_SEED_SPLIT",
    "SOURCE_POLICY_VERSION",
    "generate",
    "prepare",
    "smoke",
    "verify",
]
