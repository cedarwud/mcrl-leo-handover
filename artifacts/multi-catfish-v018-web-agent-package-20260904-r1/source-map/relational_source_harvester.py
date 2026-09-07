"""Fail-closed V0.18 relational-Q3 source shard harvester.

The physics and model adapters live outside this module.  An adapter supplies
one predecision frame per physical step; this module fixes the ordering around
that frame and persists the resulting source, capture receipt, and evaluation
only background sidecar.  In particular, no source row is selected by target
sign, action change, or support.  The only accepted label is the native-bit
``z3_bits`` surface produced by the caller's exact-ZR adapter.

This is an implementation seam, not run authority.  The caller must provide a
frozen contract/config binding and all world, lineage, checkpoint, and field
identities.  Importing the module never opens a simulator or starts a run.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

import numpy as np

from relational_source_bridge import (
    BRIDGE_METADATA_FILENAME,
    CAPTURE_ORDER,
    IMPLEMENTATION_STATUS,
    PredecisionCapture,
    RelationalSourceBridgeError,
    RelationalSourceCapture,
    attach_exact_zr_target,
    capture_predecision,
    read_source_closure,
    write_source_closure_for_source,
)
from relational_source_schema import (
    ACTION_CONTEXT_DIM,
    ACTION_DIM,
    ALLOWED_SPLITS,
    FEATURE_FIELDS,
    RelationalZRC3Source,
    VICTIM_TOKEN_DIM,
)

try:
    from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS
except ImportError:  # pragma: no cover - standalone source-only import
    OPS3_KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")


HARVESTER_SCHEMA = "multi-catfish-mcrl-v018-relational-zr-source-harvester-v1"
HARVESTER_SCHEMA_VERSION = 1
HARVEST_METADATA_FILENAME = "harvest.json"
HARVEST_RECEIPT_FILENAME = "harvest.sha256"
CAPTURE_SEQUENCE_SCHEMA = (
    "multi-catfish-mcrl-v018-relational-zr-capture-sequence-v1"
)
CAPTURE_SEQUENCE_FILENAME = "capture-sequence.json"
CAPTURE_SEQUENCE_RECEIPT_FILENAME = "capture-sequence.sha256"
DECISION_CONTEXT_SCHEMA = (
    "multi-catfish-mcrl-v018-relational-zr-decision-context-v1"
)
DECISION_CONTEXT_METADATA_FILENAME = "decision-context.json"
DECISION_CONTEXT_NPZ_FILENAME = "decision-context.npz"
DECISION_CONTEXT_RECEIPT_FILENAME = "decision-context.sha256"

SEQUENCE_RECEIPT_FIELDS = (
    "schema",
    "metadata_sha256",
    "sequence_sha256",
)
SIDECAR_RECEIPT_FIELDS = (
    "schema",
    "metadata_sha256",
    "npz_sha256",
    "arrays_sha256",
    "decision_context_sha256",
)
HARVEST_RECEIPT_FIELDS = (
    "schema",
    "metadata_sha256",
    "source_arrays_sha256",
    "capture_sequence_sha256",
    "decision_context_sha256",
    "harvest_metadata_sha256",
)

EXPECTED_STEPS = 10
EXPECTED_USERS = 100
EXPECTED_ROWS = EXPECTED_STEPS * EXPECTED_USERS
NATIVE_BITS_LABEL = "z3_bits"
NATIVE_BITS_SCALE = "native_bits"
TARGET_SEMANTICS = "exact-ZR-centered-surface-label-only"
NO_FILTERING = "none"
FROZEN_CONTRACT_STATUS = "FROZEN_BEFORE_OUTCOME"
HARVEST_STATUS = "IMPLEMENTATION_ONLY_NO_OUTCOME"
_SIDECAR_ARRAY_NAMES = (
    "background_q12",
    "action_mask",
    "reference_actions",
    "step_indices",
    "user_indices",
)


class SourceHarvesterError(ValueError):
    """A source, ordering, identity, or receipt boundary failed."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise SourceHarvesterError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise SourceHarvesterError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise SourceHarvesterError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _array_sha256(value: object) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _arrays_sha256(arrays: Mapping[str, object]) -> str:
    return canonical_sha256(
        {name: _array_sha256(value) for name, value in arrays.items()}
    )


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise SourceHarvesterError(f"{field} must be a positive integer")
    result = int(value)
    if result <= 0:
        raise SourceHarvesterError(f"{field} must be a positive integer")
    return result


def _finite_positive(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise SourceHarvesterError(f"{field} must be finite and positive") from error
    if not math.isfinite(result) or result <= 0.0:
        raise SourceHarvesterError(f"{field} must be finite and positive")
    return result


def _owned_array(value: object, *, dtype: np.dtype[Any], field: str) -> np.ndarray:
    try:
        result = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise SourceHarvesterError(f"{field} cannot be materialised") from error
    if not np.all(np.isfinite(result)) if np.issubdtype(result.dtype, np.number) else False:
        raise SourceHarvesterError(f"{field} must be finite")
    result.setflags(write=False)
    return result


def _native_surface(value: object, *, field: str) -> np.ndarray:
    result = _owned_array(value, dtype=np.dtype(np.float64), field=field)
    if result.shape != (EXPECTED_USERS, ACTION_DIM):
        raise SourceHarvesterError(
            f"{field} must have shape ({EXPECTED_USERS},{ACTION_DIM})"
        )
    if not np.all(np.isfinite(result)):
        raise SourceHarvesterError(f"{field} must be finite")
    return result


def _native_mask(value: object) -> np.ndarray:
    raw = np.asarray(value)
    if raw.dtype != np.bool_ or raw.shape != (EXPECTED_USERS, ACTION_DIM):
        raise SourceHarvesterError(
            f"action_mask must be Boolean shape ({EXPECTED_USERS},{ACTION_DIM})"
        )
    result = np.array(raw, dtype=np.bool_, copy=True, order="C")
    if not np.all(np.any(result, axis=1)):
        raise SourceHarvesterError("every focal row must have a legal native action")
    result.setflags(write=False)
    return result


def _masked_argmax_q12(q1: object, q2: object, mask: object) -> tuple[np.ndarray, np.ndarray]:
    """Return detached ``Q1 + learned-Q2`` and its native masked argmax."""

    first = _native_surface(q1, field="q1")
    second = _native_surface(q2, field="learned_q2")
    legal = _native_mask(mask)
    with np.errstate(over="raise", invalid="raise"):
        try:
            background_q12 = np.array(first + second, dtype=np.float64, copy=True)
        except FloatingPointError as error:
            raise SourceHarvesterError("Q1+Q2 background is non-finite") from error
    if not np.all(np.isfinite(background_q12)):
        raise SourceHarvesterError("Q1+Q2 background is non-finite")
    if not np.all(np.any(legal, axis=1)):
        raise SourceHarvesterError("native mask contains an empty row")
    background = np.argmax(
        np.where(legal, background_q12, -np.inf), axis=1
    ).astype(np.int64, copy=False)
    if not np.all(legal[np.arange(EXPECTED_USERS), background]):
        raise SourceHarvesterError("background action is outside the native mask")
    background_q12.setflags(write=False)
    background.setflags(write=False)
    return background_q12, background


@dataclass(frozen=True)
class SourceHarvestConfig:
    """External identity/config binding; no experiment identity is inferred."""

    contract_sha256: str
    config_sha256: str
    code_manifest_sha256: str
    world_seed: int
    lineage: int
    split: str
    field_root_digest: str
    q1_checkpoint_sha256: str
    q2_checkpoint_sha256: str
    q1_parameter_sha256: str
    q2_parameter_sha256: str
    kappa_bits: float
    declared_worlds: tuple[int, ...]
    declared_lineages: tuple[int, ...]
    contract_status: str = FROZEN_CONTRACT_STATUS
    status: str = HARVEST_STATUS
    users: int = EXPECTED_USERS
    steps: int = EXPECTED_STEPS
    action_dim: int = ACTION_DIM
    test_split_opened: bool = False
    episode_training: bool = False
    learner_update: bool = False

    def __post_init__(self) -> None:
        for field, value in (
            ("contract_sha256", self.contract_sha256),
            ("config_sha256", self.config_sha256),
            ("code_manifest_sha256", self.code_manifest_sha256),
            ("field_root_digest", self.field_root_digest),
            ("q1_checkpoint_sha256", self.q1_checkpoint_sha256),
            ("q2_checkpoint_sha256", self.q2_checkpoint_sha256),
            ("q1_parameter_sha256", self.q1_parameter_sha256),
            ("q2_parameter_sha256", self.q2_parameter_sha256),
        ):
            _digest(value, field=field)
        _positive_int(self.world_seed, field="world_seed")
        _positive_int(self.lineage, field="lineage")
        if not self.declared_worlds or len(set(self.declared_worlds)) != len(self.declared_worlds):
            raise SourceHarvesterError("declared_worlds must be nonempty and unique")
        if not self.declared_lineages or len(set(self.declared_lineages)) != len(self.declared_lineages):
            raise SourceHarvesterError("declared_lineages must be nonempty and unique")
        if any(
            isinstance(value, bool) or not isinstance(value, (int, np.integer)) or int(value) <= 0
            for value in (*self.declared_worlds, *self.declared_lineages)
        ):
            raise SourceHarvesterError("declared worlds/lineages must be positive integers")
        if self.world_seed not in self.declared_worlds:
            raise SourceHarvesterError("world_seed is not declared by the external config")
        if self.lineage not in self.declared_lineages:
            raise SourceHarvesterError("lineage is not declared by the external config")
        if self.split not in ALLOWED_SPLITS:
            raise SourceHarvesterError(
                f"split must be one of {sorted(ALLOWED_SPLITS)}"
            )
        if self.contract_status != FROZEN_CONTRACT_STATUS:
            raise SourceHarvesterError("contract is not frozen before outcome access")
        if self.status != HARVEST_STATUS:
            raise SourceHarvesterError("harvester status is stale")
        if self.users != EXPECTED_USERS or self.steps != EXPECTED_STEPS:
            raise SourceHarvesterError("source shard must be exactly 10 steps x 100 rows")
        if self.action_dim != ACTION_DIM:
            raise SourceHarvesterError("action_dim is not the native 28-action surface")
        if any(
            value is not False
            for value in (
                self.test_split_opened,
                self.episode_training,
                self.learner_update,
            )
        ):
            raise SourceHarvesterError("source harvester crosses a forbidden boundary")
        kappa = _finite_positive(self.kappa_bits, field="kappa_bits")
        if float(kappa).hex() != float(OPS3_KAPPA_BITS).hex():
            raise SourceHarvesterError("kappa_bits differs from the frozen native scale")
        object.__setattr__(self, "world_seed", int(self.world_seed))
        object.__setattr__(self, "lineage", int(self.lineage))
        object.__setattr__(self, "declared_worlds", tuple(int(value) for value in self.declared_worlds))
        object.__setattr__(self, "declared_lineages", tuple(int(value) for value in self.declared_lineages))
        object.__setattr__(self, "kappa_bits", kappa)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": HARVESTER_SCHEMA,
            "schema_version": HARVESTER_SCHEMA_VERSION,
            "contract_sha256": self.contract_sha256,
            "config_sha256": self.config_sha256,
            "code_manifest_sha256": self.code_manifest_sha256,
            "contract_status": self.contract_status,
            "status": self.status,
            "world_seed": self.world_seed,
            "lineage": self.lineage,
            "split": self.split,
            "declared_worlds": list(self.declared_worlds),
            "declared_lineages": list(self.declared_lineages),
            "field_root_digest": self.field_root_digest,
            "q1_checkpoint_sha256": self.q1_checkpoint_sha256,
            "q2_checkpoint_sha256": self.q2_checkpoint_sha256,
            "q1_parameter_sha256": self.q1_parameter_sha256,
            "q2_parameter_sha256": self.q2_parameter_sha256,
            "kappa_bits_hex": float(self.kappa_bits).hex(),
            "users": self.users,
            "steps": self.steps,
            "action_dim": self.action_dim,
            "test_split_opened": self.test_split_opened,
            "episode_training": self.episode_training,
            "learner_update": self.learner_update,
        }


@dataclass(frozen=True)
class ExactZ3Label:
    """The only exact result accepted across the target boundary."""

    z3_bits: object
    positive_credit_compatible: object


@dataclass(frozen=True)
class AnchorInput:
    """One externally supplied physical anchor adapter.

    ``predecision_encoder`` must call the existing relational encoder with the
    supplied reference action.  ``exact_target_provider`` is called only after
    the capture and sidecar append.  The digest callbacks are intentionally
    required: a default would make checkpoint/live-state drift invisible.
    """

    step_index: int
    q1: object
    learned_q2: object
    action_mask: object
    predecision_encoder: Callable[[np.ndarray], object]
    exact_target_provider: Callable[[PredecisionCapture], object]
    live_rng_digest: Callable[[], str]
    checkpoint_digests: Callable[[], tuple[str, str]]
    parameter_digests: Callable[[], tuple[str, str]]
    execute_background_action: Callable[[np.ndarray], object]
    exact_compatibility_provider: Callable[[PredecisionCapture], object] | None = None


@dataclass(frozen=True)
class AnchorCapture:
    """Authenticated one-step source and evaluation-sidecar capture."""

    step_index: int
    source_capture: RelationalSourceCapture
    background_q12: np.ndarray
    action_mask: np.ndarray
    reference_actions: np.ndarray
    predecision_observation_sha256: str
    exact_target_sha256: str
    compatibility_sha256: str
    live_rng_before_sha256: str
    live_rng_after_sha256: str
    anchor_sha256: str
    q1_checkpoint_sha256: str
    q2_checkpoint_sha256: str
    q1_parameter_sha256: str
    q2_parameter_sha256: str

    def __post_init__(self) -> None:
        if self.step_index < 0 or self.step_index >= EXPECTED_STEPS:
            raise SourceHarvesterError("anchor step index is outside the ten-step shard")
        if self.source_capture.source.rows != EXPECTED_USERS:
            raise SourceHarvesterError("each anchor must contain exactly 100 focal rows")
        q12 = np.asarray(self.background_q12)
        mask = np.asarray(self.action_mask)
        refs = np.asarray(self.reference_actions)
        if q12.shape != (EXPECTED_USERS, ACTION_DIM) or not np.all(np.isfinite(q12)):
            raise SourceHarvesterError("anchor background surface is malformed")
        if mask.dtype != np.bool_ or mask.shape != q12.shape:
            raise SourceHarvesterError("anchor mask is not a native Boolean surface")
        if refs.shape != (EXPECTED_USERS,) or not np.issubdtype(refs.dtype, np.integer):
            raise SourceHarvesterError("anchor reference actions are malformed")
        for field, value in (
            ("predecision_observation_sha256", self.predecision_observation_sha256),
            ("exact_target_sha256", self.exact_target_sha256),
            ("compatibility_sha256", self.compatibility_sha256),
            ("live_rng_before_sha256", self.live_rng_before_sha256),
            ("live_rng_after_sha256", self.live_rng_after_sha256),
            ("anchor_sha256", self.anchor_sha256),
            ("q1_checkpoint_sha256", self.q1_checkpoint_sha256),
            ("q2_checkpoint_sha256", self.q2_checkpoint_sha256),
            ("q1_parameter_sha256", self.q1_parameter_sha256),
            ("q2_parameter_sha256", self.q2_parameter_sha256),
        ):
            _digest(value, field=field)


@dataclass(frozen=True)
class AuthenticatedHarvest:
    """Read-back of a complete aggregate source shard."""

    source: RelationalZRC3Source
    metadata: dict[str, object]
    sequence: dict[str, object]
    sidecar: dict[str, np.ndarray]


def _check_identity(
    values: tuple[str, str], expected: tuple[str, str], *, field: str
) -> None:
    if tuple(values) != tuple(expected):
        raise SourceHarvesterError(f"{field} digest drifted")
    for index, value in enumerate(values):
        _digest(value, field=f"{field}[{index}]")


def _digest_pair(callback: Callable[[], tuple[str, str]], *, field: str) -> tuple[str, str]:
    if not callable(callback):
        raise SourceHarvesterError(f"{field} callback is required")
    try:
        values = callback()
    except Exception as error:  # pragma: no cover - adapter-specific failure
        raise SourceHarvesterError(f"{field} callback failed") from error
    if not isinstance(values, tuple) or len(values) != 2:
        raise SourceHarvesterError(f"{field} callback must return (Q1,Q2) digests")
    return str(values[0]), str(values[1])


def _call_live(callback: Callable[[], str], *, field: str) -> str:
    if not callable(callback):
        raise SourceHarvesterError("live/RNG digest callback is required")
    try:
        value = callback()
    except Exception as error:  # pragma: no cover - adapter-specific failure
        raise SourceHarvesterError(f"{field} callback failed") from error
    return _digest(value, field=field)


def _coerce_exact_label(
    value: object,
    predecision: PredecisionCapture,
    compatibility_provider: Callable[[PredecisionCapture], object] | None,
) -> ExactZ3Label:
    if isinstance(value, ExactZ3Label):
        if compatibility_provider is not None:
            raise SourceHarvesterError(
                "exact label already carries compatibility; duplicate provider is forbidden"
            )
        return value
    if isinstance(value, Mapping):
        raise SourceHarvesterError(
            "exact target provider must return ExactZ3Label, not a teacher mapping"
        )
    if compatibility_provider is None:
        raise SourceHarvesterError(
            "raw z3_bits require an explicit exact compatibility provider"
        )
    try:
        compatible = compatibility_provider(predecision)
    except Exception as error:  # pragma: no cover - adapter-specific failure
        raise SourceHarvesterError("exact compatibility provider failed") from error
    return ExactZ3Label(z3_bits=value, positive_credit_compatible=compatible)


def _validate_compatibility(
    exact: object, predecision: PredecisionCapture
) -> np.ndarray:
    raw = np.asarray(exact)
    expected_shape = predecision.observation.action_mask.shape
    if raw.dtype != np.bool_ or raw.shape != expected_shape:
        raise SourceHarvesterError(
            f"exact compatibility must be Boolean shape {expected_shape}"
        )
    result = np.array(raw, dtype=np.bool_, copy=True, order="C")
    nominal = np.asarray(predecision.observation.positive_credit_compatible)
    if not np.array_equal(result, nominal):
        raise SourceHarvesterError(
            "exact/predecision compatibility bits differ"
        )
    result.setflags(write=False)
    return result


def _anchor_digest(
    capture: RelationalSourceCapture,
    background_q12: np.ndarray,
    action_mask: np.ndarray,
    reference_actions: np.ndarray,
    *,
    step_index: int,
    compatibility_sha256: str,
) -> str:
    return canonical_sha256(
        {
            "step_index": int(step_index),
            "source_arrays_sha256": capture.source.arrays_sha256(),
            "background_q12_sha256": _array_sha256(background_q12),
            "action_mask_sha256": _array_sha256(action_mask),
            "reference_actions_sha256": _array_sha256(reference_actions),
            "compatibility_sha256": compatibility_sha256,
            "target_surface_sha256": capture.target_surface_sha256,
        }
    )


def harvest_anchor(config: SourceHarvestConfig, anchor: AnchorInput) -> AnchorCapture:
    """Capture one anchor in the fixed predecision -> target -> action order."""

    if not isinstance(config, SourceHarvestConfig):
        raise SourceHarvesterError("config must be SourceHarvestConfig")
    if not isinstance(anchor, AnchorInput):
        raise SourceHarvesterError("anchor must be AnchorInput")
    if anchor.step_index < 0 or anchor.step_index >= config.steps:
        raise SourceHarvesterError("anchor step index is outside the configured shard")
    checkpoint_before = _digest_pair(
        anchor.checkpoint_digests, field="checkpoint digests"
    )
    parameter_before = _digest_pair(
        anchor.parameter_digests, field="parameter digests"
    )
    _check_identity(
        checkpoint_before,
        (config.q1_checkpoint_sha256, config.q2_checkpoint_sha256),
        field="Q1/Q2 checkpoint",
    )
    _check_identity(
        parameter_before,
        (config.q1_parameter_sha256, config.q2_parameter_sha256),
        field="Q1/Q2 parameter",
    )
    background_q12, reference_actions = _masked_argmax_q12(
        anchor.q1, anchor.learned_q2, anchor.action_mask
    )
    native_mask = _native_mask(anchor.action_mask)

    try:
        predecision = capture_predecision(
            encoder=lambda: anchor.predecision_encoder(reference_actions),
            world_seed=config.world_seed,
            lineage=config.lineage,
            split=config.split,
            field_root_digest=config.field_root_digest,
            kappa_bits=config.kappa_bits,
        )
    except RelationalSourceBridgeError as error:
        raise SourceHarvesterError("relational predecision capture failed") from error
    observation = predecision.observation
    if observation.action_mask.shape != native_mask.shape:
        raise SourceHarvesterError("relational observation row shape is not 100x28")
    if not np.array_equal(observation.action_mask, native_mask):
        raise SourceHarvesterError("relational encoder mask differs from native mask")
    if not np.array_equal(observation.reference_actions, reference_actions):
        raise SourceHarvesterError("relational encoder reference differs from Q1+Q2 argmax")

    # This is the sidecar append point.  No target provider is touched before
    # the detached background surface and identity have been materialised.
    sidecar_q12 = np.array(background_q12, dtype=np.float64, copy=True, order="C")
    sidecar_q12.setflags(write=False)
    live_before = _call_live(anchor.live_rng_digest, field="live/RNG before")
    try:
        raw_label = anchor.exact_target_provider(predecision)
    except Exception as error:  # pragma: no cover - adapter-specific failure
        raise SourceHarvesterError("exact native-bit target provider failed") from error
    label = _coerce_exact_label(
        raw_label, predecision, anchor.exact_compatibility_provider
    )
    compatible = _validate_compatibility(
        label.positive_credit_compatible, predecision
    )
    try:
        captured = attach_exact_zr_target(predecision, label.z3_bits)
    except RelationalSourceBridgeError as error:
        raise SourceHarvesterError("exact z3_bits target failed native validation") from error
    target = np.asarray(captured.source.target_surface_bits)
    if np.any((target > 0.0) & ~compatible):
        raise SourceHarvesterError(
            "positive native z3_bits target exists outside compatibility"
        )
    live_after = _call_live(anchor.live_rng_digest, field="live/RNG after")
    if live_before != live_after:
        raise SourceHarvesterError("exact measurement changed live state or RNG")
    checkpoint_after_measurement = _digest_pair(
        anchor.checkpoint_digests, field="checkpoint digests"
    )
    parameter_after_measurement = _digest_pair(
        anchor.parameter_digests, field="parameter digests"
    )
    _check_identity(
        checkpoint_after_measurement,
        (config.q1_checkpoint_sha256, config.q2_checkpoint_sha256),
        field="Q1/Q2 checkpoint",
    )
    _check_identity(
        parameter_after_measurement,
        (config.q1_parameter_sha256, config.q2_parameter_sha256),
        field="Q1/Q2 parameter",
    )

    compatibility_sha256 = _array_sha256(compatible)
    anchor_sha256 = _anchor_digest(
        captured,
        sidecar_q12,
        native_mask,
        reference_actions,
        step_index=anchor.step_index,
        compatibility_sha256=compatibility_sha256,
    )
    # The only action crossing this boundary is the detached native background
    # vector.  The caller owns the actual environment advance; this call is
    # made exactly once and only after all counterfactual checks above.
    action_argument = np.array(reference_actions, dtype=np.int64, copy=True)
    action_argument.setflags(write=False)
    try:
        anchor.execute_background_action(action_argument)
    except Exception as error:  # pragma: no cover - adapter-specific failure
        raise SourceHarvesterError("background action/advance failed") from error
    checkpoint_after = _digest_pair(
        anchor.checkpoint_digests, field="checkpoint digests"
    )
    parameter_after = _digest_pair(
        anchor.parameter_digests, field="parameter digests"
    )
    _check_identity(
        checkpoint_after,
        (config.q1_checkpoint_sha256, config.q2_checkpoint_sha256),
        field="Q1/Q2 checkpoint",
    )
    _check_identity(
        parameter_after,
        (config.q1_parameter_sha256, config.q2_parameter_sha256),
        field="Q1/Q2 parameter",
    )
    return AnchorCapture(
        step_index=anchor.step_index,
        source_capture=captured,
        background_q12=sidecar_q12,
        action_mask=native_mask,
        reference_actions=reference_actions,
        predecision_observation_sha256=predecision.predecision_observation_sha256,
        exact_target_sha256=captured.target_surface_sha256,
        compatibility_sha256=compatibility_sha256,
        live_rng_before_sha256=live_before,
        live_rng_after_sha256=live_after,
        anchor_sha256=anchor_sha256,
        q1_checkpoint_sha256=checkpoint_after[0],
        q2_checkpoint_sha256=checkpoint_after[1],
        q1_parameter_sha256=parameter_after[0],
        q2_parameter_sha256=parameter_after[1],
    )


def make_v018_anchor_input(
    *,
    step_index: int,
    environment: object,
    observation: object,
    q1: object,
    learned_q2: object,
    action_mask: object,
    required_power_surface: object,
    opening_feasibility_surface: object,
    pmax_w: float | None,
    exact_target_provider: Callable[[PredecisionCapture], object],
    live_rng_digest: Callable[[], str],
    checkpoint_digests: Callable[[], tuple[str, str]],
    parameter_digests: Callable[[], tuple[str, str]],
    execute_background_action: Callable[[np.ndarray], object],
    exact_compatibility_provider: Callable[[PredecisionCapture], object] | None = None,
) -> AnchorInput:
    """Bind the existing V0.18 encoder without copying its physics formula."""

    from mcrl.runtime.ee_axis_relational_zr_c3 import encode_relational_zr_c3_state

    def encode(reference_actions: np.ndarray) -> object:
        return encode_relational_zr_c3_state(
            environment,
            observation,
            reference_actions=reference_actions,
            required_power_surface=required_power_surface,
            opening_feasibility_surface=opening_feasibility_surface,
            pmax_w=pmax_w,
        )

    return AnchorInput(
        step_index=step_index,
        q1=q1,
        learned_q2=learned_q2,
        action_mask=action_mask,
        predecision_encoder=encode,
        exact_target_provider=exact_target_provider,
        exact_compatibility_provider=exact_compatibility_provider,
        live_rng_digest=live_rng_digest,
        checkpoint_digests=checkpoint_digests,
        parameter_digests=parameter_digests,
        execute_background_action=execute_background_action,
    )


def _aggregate_sources(
    config: SourceHarvestConfig, captures: Sequence[AnchorCapture]
) -> tuple[RelationalZRC3Source, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if len(captures) != config.steps:
        raise SourceHarvesterError("shard must contain exactly ten anchor captures")
    ordered = sorted(captures, key=lambda item: item.step_index)
    if [item.step_index for item in ordered] != list(range(config.steps)):
        raise SourceHarvesterError("capture sequence has a duplicate or missing step")
    sources = [item.source_capture.source for item in ordered]
    if any(source.rows != config.users for source in sources):
        raise SourceHarvesterError("source capture has a row count other than 100")
    for source in sources:
        if (
            source.world_seed != config.world_seed
            or source.lineage != config.lineage
            or source.split != config.split
            or source.field_root_digest != config.field_root_digest
            or float(source.kappa_bits).hex() != float(config.kappa_bits).hex()
        ):
            raise SourceHarvesterError("source anchor identity disagrees with config")
        if tuple(source.feature_fields) != FEATURE_FIELDS:
            raise SourceHarvesterError("source feature fields drifted")
    victim_counts = {source.victim_count for source in sources}
    if len(victim_counts) != 1:
        raise SourceHarvesterError("source anchors disagree on victim count")
    fields = (
        "action_context",
        "victim_tokens",
        "action_mask",
        "victim_mask",
        "positive_credit_compatible",
        "reference_actions",
        "target_surface_bits",
    )
    aggregate_arrays = {
        field: np.concatenate([np.asarray(getattr(source, field)) for source in sources], axis=0)
        for field in fields
    }
    aggregate_source = RelationalZRC3Source(
        **aggregate_arrays,
        world_seed=config.world_seed,
        lineage=config.lineage,
        split=config.split,
        field_root_digest=config.field_root_digest,
        kappa_bits=config.kappa_bits,
        feature_fields=FEATURE_FIELDS,
    )
    if aggregate_source.rows != EXPECTED_ROWS:
        raise SourceHarvesterError("aggregate source is not exactly 1000 rows")
    target = np.asarray(aggregate_source.target_surface_bits)
    compatible = np.asarray(aggregate_source.positive_credit_compatible)
    if np.any((target > 0.0) & ~compatible):
        raise SourceHarvesterError(
            "aggregate has positive native target outside compatibility"
        )
    q12 = np.concatenate([np.asarray(item.background_q12) for item in ordered], axis=0)
    masks = np.concatenate([np.asarray(item.action_mask) for item in ordered], axis=0)
    refs = np.concatenate([np.asarray(item.reference_actions) for item in ordered], axis=0)
    steps = np.repeat(np.arange(config.steps, dtype=np.int64), config.users)
    users = np.tile(np.arange(config.users, dtype=np.int64), config.steps)
    return aggregate_source, q12, masks, refs, steps, users


def _sequence_body(
    config: SourceHarvestConfig,
    captures: Sequence[AnchorCapture],
    source: RelationalZRC3Source,
    sidecar_arrays: Mapping[str, np.ndarray],
) -> dict[str, object]:
    records: list[dict[str, object]] = []
    for capture in sorted(captures, key=lambda item: item.step_index):
        start = capture.step_index * config.users
        stop = start + config.users
        records.append(
            {
                "step_index": capture.step_index,
                "row_start": start,
                "row_stop": stop,
                "row_count": config.users,
                "predecision_observation_sha256": capture.predecision_observation_sha256,
                "exact_target_sha256": capture.exact_target_sha256,
                "compatibility_sha256": capture.compatibility_sha256,
                "live_rng_before_sha256": capture.live_rng_before_sha256,
                "live_rng_after_sha256": capture.live_rng_after_sha256,
                "anchor_sha256": capture.anchor_sha256,
                "source_arrays_sha256": capture.source_capture.source.arrays_sha256(),
                "sidecar_arrays_sha256": _arrays_sha256(
                    {
                        name: np.asarray(values)[start:stop]
                        for name, values in sidecar_arrays.items()
                    }
                ),
                "row_identity_sha256": _arrays_sha256(
                    {
                        "step_indices": np.asarray(sidecar_arrays["step_indices"])[start:stop],
                        "user_indices": np.asarray(sidecar_arrays["user_indices"])[start:stop],
                    }
                ),
                "q1_checkpoint_sha256": capture.q1_checkpoint_sha256,
                "q2_checkpoint_sha256": capture.q2_checkpoint_sha256,
                "q1_parameter_sha256": capture.q1_parameter_sha256,
                "q2_parameter_sha256": capture.q2_parameter_sha256,
            }
        )
    source_arrays = source.arrays_as_mapping()
    return {
        "schema": CAPTURE_SEQUENCE_SCHEMA,
        "schema_version": 1,
        "status": HARVEST_STATUS,
        "capture_order": CAPTURE_ORDER,
        "target_field": NATIVE_BITS_LABEL,
        "target_scale": NATIVE_BITS_SCALE,
        "target_semantics": TARGET_SEMANTICS,
        "filtering": NO_FILTERING,
        "world_seed": config.world_seed,
        "lineage": config.lineage,
        "split": config.split,
        "declared_worlds": list(config.declared_worlds),
        "declared_lineages": list(config.declared_lineages),
        "field_root_digest": config.field_root_digest,
        "kappa_bits_hex": float(config.kappa_bits).hex(),
        "steps": config.steps,
        "users": config.users,
        "rows": source.rows,
        "records": records,
        "aggregate_source_arrays_sha256": source.arrays_sha256(),
        "aggregate_sidecar_arrays_sha256": _arrays_sha256(sidecar_arrays),
        "source_array_sha256": {
            name: _array_sha256(value) for name, value in source_arrays.items()
        },
        "sidecar_array_sha256": {
            name: _array_sha256(value) for name, value in sidecar_arrays.items()
        },
        "contract_sha256": config.contract_sha256,
        "config_sha256": config.config_sha256,
        "code_manifest_sha256": config.code_manifest_sha256,
        "q1_checkpoint_sha256": config.q1_checkpoint_sha256,
        "q2_checkpoint_sha256": config.q2_checkpoint_sha256,
        "q1_parameter_sha256": config.q1_parameter_sha256,
        "q2_parameter_sha256": config.q2_parameter_sha256,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }


def _write_once(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise SourceHarvesterError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_bytes(payload)
        os.link(temporary, path)
    except FileExistsError as error:
        raise SourceHarvesterError(f"refusing to overwrite {path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return _file_sha256(path)


def _write_sidecar(
    root: Path,
    config: SourceHarvestConfig,
    source: RelationalZRC3Source,
    arrays: Mapping[str, np.ndarray],
) -> dict[str, str]:
    if tuple(arrays) != _SIDECAR_ARRAY_NAMES:
        raise SourceHarvesterError("decision sidecar arrays are not closed")
    for name, value in arrays.items():
        array = np.ascontiguousarray(value)
        if not np.all(np.isfinite(array)) if np.issubdtype(array.dtype, np.number) else False:
            raise SourceHarvesterError(f"decision sidecar array is non-finite: {name}")
    expected = {
        "background_q12": ((EXPECTED_ROWS, ACTION_DIM), np.dtype(np.float64)),
        "action_mask": ((EXPECTED_ROWS, ACTION_DIM), np.dtype(np.bool_)),
        "reference_actions": ((EXPECTED_ROWS,), np.dtype(np.int64)),
        "step_indices": ((EXPECTED_ROWS,), np.dtype(np.int64)),
        "user_indices": ((EXPECTED_ROWS,), np.dtype(np.int64)),
    }
    for name, (shape, dtype) in expected.items():
        array = np.asarray(arrays[name])
        if array.shape != shape or array.dtype != dtype:
            raise SourceHarvesterError(f"decision sidecar {name} shape/dtype drifted")
    if not np.array_equal(arrays["action_mask"], source.action_mask):
        raise SourceHarvesterError("sidecar native mask does not match source rows")
    if not np.array_equal(arrays["reference_actions"], source.reference_actions):
        raise SourceHarvesterError("sidecar reference actions do not match source rows")
    if np.any(
        ~np.asarray(arrays["action_mask"])[
            np.arange(EXPECTED_ROWS), np.asarray(arrays["reference_actions"])
        ]
    ):
        raise SourceHarvesterError("sidecar reference action is outside native mask")
    npz_path = root / DECISION_CONTEXT_NPZ_FILENAME
    if npz_path.exists() or npz_path.is_symlink():
        raise SourceHarvesterError(f"refusing to overwrite {npz_path}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{npz_path.name}.", suffix=".tmp.npz", dir=root
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        np.savez_compressed(
            temporary,
            **{name: np.ascontiguousarray(value) for name, value in arrays.items()},
        )
        os.link(temporary, npz_path)
    except FileExistsError as error:
        raise SourceHarvesterError(f"refusing to overwrite {npz_path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    npz_sha256 = _file_sha256(npz_path)
    body = {
        "schema": DECISION_CONTEXT_SCHEMA,
        "schema_version": 1,
        "status": HARVEST_STATUS,
        "evaluation_only": True,
        "learner_loadable": False,
        "npz_filename": DECISION_CONTEXT_NPZ_FILENAME,
        "npz_sha256": npz_sha256,
        "arrays_sha256": _arrays_sha256(arrays),
        "array_sha256": {
            name: _array_sha256(value) for name, value in arrays.items()
        },
        "array_names": list(_SIDECAR_ARRAY_NAMES),
        "row_identity_sha256": _arrays_sha256(
            {
                "step_indices": np.asarray(arrays["step_indices"]),
                "user_indices": np.asarray(arrays["user_indices"]),
            }
        ),
        "world_seed": config.world_seed,
        "lineage": config.lineage,
        "split": config.split,
        "declared_worlds": list(config.declared_worlds),
        "declared_lineages": list(config.declared_lineages),
        "rows": EXPECTED_ROWS,
        "steps": config.steps,
        "users": config.users,
        "background_semantics": "detached-Q1-plus-learned-Q2-native-surface",
        "contract_sha256": config.contract_sha256,
        "config_sha256": config.config_sha256,
        "code_manifest_sha256": config.code_manifest_sha256,
        "source_arrays_sha256": source.arrays_sha256(),
        "field_root_digest": config.field_root_digest,
        "kappa_bits_hex": float(config.kappa_bits).hex(),
        "q1_checkpoint_sha256": config.q1_checkpoint_sha256,
        "q2_checkpoint_sha256": config.q2_checkpoint_sha256,
        "q1_parameter_sha256": config.q1_parameter_sha256,
        "q2_parameter_sha256": config.q2_parameter_sha256,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    metadata = {**body, "decision_context_sha256": canonical_sha256(body)}
    metadata_path = root / DECISION_CONTEXT_METADATA_FILENAME
    metadata_sha256 = _write_once(metadata_path, _canonical_bytes(metadata))
    receipt_values = {
        "schema": DECISION_CONTEXT_SCHEMA,
        "metadata_sha256": metadata_sha256,
        "npz_sha256": npz_sha256,
        "arrays_sha256": body["arrays_sha256"],
        "decision_context_sha256": metadata["decision_context_sha256"],
    }
    receipt_path = root / DECISION_CONTEXT_RECEIPT_FILENAME
    receipt_sha256 = _write_once(
        receipt_path,
        "".join(f"{key}={receipt_values[key]}\n" for key in SIDECAR_RECEIPT_FIELDS).encode(
            "ascii"
        ),
    )
    return {
        "metadata": str(metadata_path),
        "npz": str(npz_path),
        "receipt": str(receipt_path),
        "metadata_sha256": metadata_sha256,
        "npz_sha256": npz_sha256,
        "arrays_sha256": str(body["arrays_sha256"]),
        "decision_context_sha256": str(metadata["decision_context_sha256"]),
        "receipt_sha256": receipt_sha256,
    }


def _write_sequence(root: Path, payload: Mapping[str, object]) -> dict[str, str]:
    body = dict(payload)
    sequence = {**body, "sequence_sha256": canonical_sha256(body)}
    metadata_path = root / CAPTURE_SEQUENCE_FILENAME
    metadata_sha256 = _write_once(metadata_path, _canonical_bytes(sequence))
    values = {
        "schema": CAPTURE_SEQUENCE_SCHEMA,
        "metadata_sha256": metadata_sha256,
        "sequence_sha256": sequence["sequence_sha256"],
    }
    receipt_path = root / CAPTURE_SEQUENCE_RECEIPT_FILENAME
    receipt_sha256 = _write_once(
        receipt_path,
        "".join(f"{key}={values[key]}\n" for key in SEQUENCE_RECEIPT_FIELDS).encode(
            "ascii"
        ),
    )
    return {
        "metadata": str(metadata_path),
        "receipt": str(receipt_path),
        "metadata_sha256": metadata_sha256,
        "sequence_sha256": str(sequence["sequence_sha256"]),
        "receipt_sha256": receipt_sha256,
    }


def _harvest_metadata(
    config: SourceHarvestConfig,
    source: RelationalZRC3Source,
    source_receipt: Mapping[str, str],
    sequence_receipt: Mapping[str, str],
    sidecar_receipt: Mapping[str, str],
) -> dict[str, object]:
    return {
        "schema": HARVESTER_SCHEMA,
        "schema_version": HARVESTER_SCHEMA_VERSION,
        "status": HARVEST_STATUS,
        "contract_status": FROZEN_CONTRACT_STATUS,
        "capture_order": CAPTURE_ORDER,
        "target_field": NATIVE_BITS_LABEL,
        "target_scale": NATIVE_BITS_SCALE,
        "target_semantics": TARGET_SEMANTICS,
        "target_normalized": False,
        "filtering": NO_FILTERING,
        "world_seed": config.world_seed,
        "lineage": config.lineage,
        "split": config.split,
        "declared_worlds": list(config.declared_worlds),
        "declared_lineages": list(config.declared_lineages),
        "field_root_digest": config.field_root_digest,
        "kappa_bits_hex": float(config.kappa_bits).hex(),
        "users": config.users,
        "steps": config.steps,
        "rows": source.rows,
        "contract_sha256": config.contract_sha256,
        "config_sha256": config.config_sha256,
        "code_manifest_sha256": config.code_manifest_sha256,
        "q1_checkpoint_sha256": config.q1_checkpoint_sha256,
        "q2_checkpoint_sha256": config.q2_checkpoint_sha256,
        "q1_parameter_sha256": config.q1_parameter_sha256,
        "q2_parameter_sha256": config.q2_parameter_sha256,
        "source_arrays_sha256": source.arrays_sha256(),
        "source_npz_sha256": source_receipt["npz_sha256"],
        "source_metadata_sha256": source_receipt["metadata_sha256"],
        "source_bridge_metadata_sha256": source_receipt[
            "bridge_metadata_sha256"
        ],
        "capture_sequence_metadata_sha256": sequence_receipt["metadata_sha256"],
        "capture_sequence_sha256": sequence_receipt["sequence_sha256"],
        "decision_context_metadata_sha256": sidecar_receipt["metadata_sha256"],
        "decision_context_npz_sha256": sidecar_receipt["npz_sha256"],
        "decision_context_sha256": sidecar_receipt["decision_context_sha256"],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }


def _read_canonical_json(path: Path, *, field: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise SourceHarvesterError(f"missing {field}: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SourceHarvesterError(f"{field} is not canonical JSON") from error
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        raise SourceHarvesterError(f"{field} is not canonical JSON")
    return payload


def _read_receipt(path: Path, fields: Sequence[str], schema: str) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise SourceHarvesterError(f"missing receipt: {path}")
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise SourceHarvesterError("receipt is not ASCII") from error
    values: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            raise SourceHarvesterError("receipt contains a malformed line")
        key, value = line.split("=", 1)
        if key in values or key not in fields:
            raise SourceHarvesterError("receipt contains an unknown or duplicate field")
        values[key] = value
    if tuple(values) != tuple(fields):
        raise SourceHarvesterError("receipt fields are incomplete or reordered")
    if values["schema"] != schema:
        raise SourceHarvesterError("receipt schema is stale")
    for key in fields[1:]:
        _digest(values[key], field=f"receipt.{key}")
    return values


def _reject_symlinks(root: Path) -> None:
    if root.is_symlink() or not root.is_dir():
        raise SourceHarvesterError(f"harvest root is not a regular directory: {root}")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SourceHarvesterError(f"harvest closure contains a symlink: {path}")


def _read_sidecar(root: Path) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    metadata = _read_canonical_json(
        root / DECISION_CONTEXT_METADATA_FILENAME, field="decision-context metadata"
    )
    receipt = _read_receipt(
        root / DECISION_CONTEXT_RECEIPT_FILENAME,
        SIDECAR_RECEIPT_FIELDS,
        DECISION_CONTEXT_SCHEMA,
    )
    body = {key: value for key, value in metadata.items() if key != "decision_context_sha256"}
    supplied = _digest(
        metadata.get("decision_context_sha256"), field="decision_context_sha256"
    )
    if canonical_sha256(body) != supplied:
        raise SourceHarvesterError("decision-context metadata self-digest failed")
    if metadata.get("schema") != DECISION_CONTEXT_SCHEMA or metadata.get("schema_version") != 1:
        raise SourceHarvesterError("decision-context schema is stale")
    if metadata.get("evaluation_only") is not True or metadata.get("learner_loadable") is not False:
        raise SourceHarvesterError("decision-context sidecar is not evaluation-only")
    if metadata.get("array_names") != list(_SIDECAR_ARRAY_NAMES):
        raise SourceHarvesterError("decision-context array list is not closed")
    array_digests = metadata.get("array_sha256")
    if not isinstance(array_digests, Mapping) or set(array_digests) != set(_SIDECAR_ARRAY_NAMES):
        raise SourceHarvesterError("decision-context array digest map is incomplete")
    for name in _SIDECAR_ARRAY_NAMES:
        _digest(array_digests.get(name), field=f"decision-context array_sha256.{name}")
    npz_path = root / DECISION_CONTEXT_NPZ_FILENAME
    npz_sha256 = _file_sha256(npz_path)
    if npz_sha256 != metadata.get("npz_sha256") or npz_sha256 != receipt["npz_sha256"]:
        raise SourceHarvesterError("decision-context NPZ digest mismatch")
    if receipt["metadata_sha256"] != _file_sha256(root / DECISION_CONTEXT_METADATA_FILENAME):
        raise SourceHarvesterError("decision-context metadata digest mismatch")
    if receipt["decision_context_sha256"] != supplied:
        raise SourceHarvesterError("decision-context self-digest receipt mismatch")
    try:
        with np.load(npz_path, allow_pickle=False) as loaded:
            if tuple(loaded.files) != _SIDECAR_ARRAY_NAMES:
                raise SourceHarvesterError("decision-context NPZ keys are not closed")
            arrays = {name: np.array(loaded[name], copy=True, order="C") for name in _SIDECAR_ARRAY_NAMES}
    except (OSError, ValueError, TypeError) as error:
        if isinstance(error, SourceHarvesterError):
            raise
        raise SourceHarvesterError("decision-context NPZ is malformed") from error
    expected = {
        "background_q12": ((EXPECTED_ROWS, ACTION_DIM), np.dtype(np.float64)),
        "action_mask": ((EXPECTED_ROWS, ACTION_DIM), np.dtype(np.bool_)),
        "reference_actions": ((EXPECTED_ROWS,), np.dtype(np.int64)),
        "step_indices": ((EXPECTED_ROWS,), np.dtype(np.int64)),
        "user_indices": ((EXPECTED_ROWS,), np.dtype(np.int64)),
    }
    for name, (shape, dtype) in expected.items():
        if arrays[name].shape != shape or arrays[name].dtype != dtype:
            raise SourceHarvesterError(f"decision-context {name} shape/dtype mismatch")
        if np.issubdtype(dtype, np.number) and not np.all(np.isfinite(arrays[name])):
            raise SourceHarvesterError(f"decision-context {name} is non-finite")
        if _array_sha256(arrays[name]) != array_digests[name]:
            raise SourceHarvesterError(f"decision-context {name} digest mismatch")
        arrays[name].setflags(write=False)
    if _arrays_sha256(arrays) != metadata.get("arrays_sha256") or receipt["arrays_sha256"] != metadata.get("arrays_sha256"):
        raise SourceHarvesterError("decision-context array digest mismatch")
    expected_row_identity = _arrays_sha256(
        {
            "step_indices": arrays["step_indices"],
            "user_indices": arrays["user_indices"],
        }
    )
    if metadata.get("row_identity_sha256") != expected_row_identity:
        raise SourceHarvesterError("decision-context row identity digest mismatch")
    if not np.array_equal(
        arrays["step_indices"], np.repeat(np.arange(EXPECTED_STEPS), EXPECTED_USERS)
    ) or not np.array_equal(
        arrays["user_indices"], np.tile(np.arange(EXPECTED_USERS), EXPECTED_STEPS)
    ):
        raise SourceHarvesterError("decision-context row ordering is not 10x100")
    return arrays, metadata


def _validate_sequence(
    root: Path, source: RelationalZRC3Source, sidecar: Mapping[str, np.ndarray]
) -> dict[str, object]:
    sequence = _read_canonical_json(root / CAPTURE_SEQUENCE_FILENAME, field="capture sequence")
    receipt = _read_receipt(
        root / CAPTURE_SEQUENCE_RECEIPT_FILENAME,
        SEQUENCE_RECEIPT_FIELDS,
        CAPTURE_SEQUENCE_SCHEMA,
    )
    body = {key: value for key, value in sequence.items() if key != "sequence_sha256"}
    supplied = _digest(sequence.get("sequence_sha256"), field="sequence_sha256")
    if canonical_sha256(body) != supplied or receipt["sequence_sha256"] != supplied:
        raise SourceHarvesterError("capture sequence self-digest failed")
    if (
        sequence.get("schema") != CAPTURE_SEQUENCE_SCHEMA
        or sequence.get("schema_version") != 1
        or sequence.get("status") != HARVEST_STATUS
        or sequence.get("capture_order") != CAPTURE_ORDER
        or sequence.get("world_seed") != source.world_seed
        or sequence.get("lineage") != source.lineage
        or sequence.get("split") != source.split
        or sequence.get("field_root_digest") != source.field_root_digest
        or sequence.get("kappa_bits_hex") != float(source.kappa_bits).hex()
    ):
        raise SourceHarvesterError("capture sequence identity/status drifted")
    if sequence.get("steps") != EXPECTED_STEPS or sequence.get("users") != EXPECTED_USERS or sequence.get("rows") != EXPECTED_ROWS:
        raise SourceHarvesterError("capture sequence dimensions are not 10x100")
    if sequence.get("target_field") != NATIVE_BITS_LABEL or sequence.get("target_scale") != NATIVE_BITS_SCALE:
        raise SourceHarvesterError("capture sequence target scale is not native z3_bits")
    if sequence.get("filtering") != NO_FILTERING:
        raise SourceHarvesterError("capture sequence declares target/support filtering")
    if any(
        sequence.get(field) is not False
        for field in ("test_split_opened", "episode_training", "learner_update")
    ):
        raise SourceHarvesterError("capture sequence crosses a forbidden boundary")
    records = sequence.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_STEPS:
        raise SourceHarvesterError("capture sequence records are incomplete")
    ordered = sorted(records, key=lambda item: int(item.get("step_index", -1)) if isinstance(item, Mapping) else -1)
    if [item.get("step_index") for item in ordered if isinstance(item, Mapping)] != list(range(EXPECTED_STEPS)):
        raise SourceHarvesterError("capture sequence has duplicate or missing steps")
    for record in ordered:
        if not isinstance(record, Mapping):
            raise SourceHarvesterError("capture sequence record is malformed")
        step = int(record["step_index"])
        start, stop = int(record["row_start"]), int(record["row_stop"])
        if (start, stop, int(record["row_count"])) != (step * EXPECTED_USERS, (step + 1) * EXPECTED_USERS, EXPECTED_USERS):
            raise SourceHarvesterError("capture sequence row interval is malformed")
        for field in (
            "predecision_observation_sha256",
            "exact_target_sha256",
            "compatibility_sha256",
            "live_rng_before_sha256",
            "live_rng_after_sha256",
            "anchor_sha256",
            "source_arrays_sha256",
            "sidecar_arrays_sha256",
            "row_identity_sha256",
            "q1_checkpoint_sha256",
            "q2_checkpoint_sha256",
            "q1_parameter_sha256",
            "q2_parameter_sha256",
        ):
            _digest(record.get(field), field=f"sequence.{field}")
        source_slice = {
            name: np.asarray(getattr(source, name))[start:stop]
            for name in source.arrays_as_mapping()
        }
        sidecar_slice = {
            name: np.asarray(values)[start:stop] for name, values in sidecar.items()
        }
        if _arrays_sha256(source_slice) != record["source_arrays_sha256"]:
            raise SourceHarvesterError("capture sequence source child digest mismatch")
        if _arrays_sha256(sidecar_slice) != record["sidecar_arrays_sha256"]:
            raise SourceHarvesterError("capture sequence sidecar child digest mismatch")
        if _arrays_sha256({name: sidecar_slice[name] for name in ("step_indices", "user_indices")}) != record["row_identity_sha256"]:
            raise SourceHarvesterError("capture sequence row identity mismatch")
        if np.any(
            (np.asarray(source.target_surface_bits)[start:stop] > 0.0)
            & ~np.asarray(source.positive_credit_compatible)[start:stop]
        ):
            raise SourceHarvesterError("positive target is outside compatibility")
    if receipt["metadata_sha256"] != _file_sha256(root / CAPTURE_SEQUENCE_FILENAME):
        raise SourceHarvesterError("capture sequence metadata digest mismatch")
    return sequence


def _persist_harvest(
    output_dir: str | Path,
    config: SourceHarvestConfig,
    captures: Sequence[AnchorCapture],
) -> AuthenticatedHarvest:
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise SourceHarvesterError(f"refusing to overwrite harvest output: {destination}")
    aggregate_source, q12, masks, refs, steps, users = _aggregate_sources(config, captures)
    sidecar_arrays = {
        "background_q12": np.asarray(q12, dtype=np.float64),
        "action_mask": np.asarray(masks, dtype=np.bool_),
        "reference_actions": np.asarray(refs, dtype=np.int64),
        "step_indices": np.asarray(steps, dtype=np.int64),
        "user_indices": np.asarray(users, dtype=np.int64),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_receipt = write_source_closure_for_source(destination, aggregate_source)
    sequence = _sequence_body(config, captures, aggregate_source, sidecar_arrays)
    sequence_receipt = _write_sequence(destination, sequence)
    sidecar_receipt = _write_sidecar(
        destination, config, aggregate_source, sidecar_arrays
    )
    body = _harvest_metadata(
        config,
        aggregate_source,
        source_receipt,
        sequence_receipt,
        sidecar_receipt,
    )
    metadata = {**body, "harvest_metadata_sha256": canonical_sha256(body)}
    metadata_path = destination / HARVEST_METADATA_FILENAME
    metadata_sha256 = _write_once(metadata_path, _canonical_bytes(metadata))
    values = {
        "schema": HARVESTER_SCHEMA,
        "metadata_sha256": metadata_sha256,
        "source_arrays_sha256": aggregate_source.arrays_sha256(),
        "capture_sequence_sha256": sequence_receipt["sequence_sha256"],
        "decision_context_sha256": sidecar_receipt["decision_context_sha256"],
        "harvest_metadata_sha256": metadata["harvest_metadata_sha256"],
    }
    harvest_receipt = destination / HARVEST_RECEIPT_FILENAME
    _write_once(
        harvest_receipt,
        "".join(f"{key}={values[key]}\n" for key in HARVEST_RECEIPT_FIELDS).encode(
            "ascii"
        ),
    )
    _reject_symlinks(destination)
    return read_harvest_closure(destination)


def harvest_source_shard(
    config: SourceHarvestConfig,
    anchor_provider: Callable[[int], AnchorInput],
    output_dir: str | Path,
) -> AuthenticatedHarvest:
    """Harvest exactly ten ordered anchors and persist one complete shard."""

    if not isinstance(config, SourceHarvestConfig):
        raise SourceHarvesterError("config must be SourceHarvestConfig")
    if not callable(anchor_provider):
        raise SourceHarvesterError("anchor_provider callback is required")
    captures: list[AnchorCapture] = []
    for step_index in range(config.steps):
        try:
            anchor = anchor_provider(step_index)
        except Exception as error:  # pragma: no cover - adapter-specific failure
            raise SourceHarvesterError(f"anchor provider failed at step {step_index}") from error
        if not isinstance(anchor, AnchorInput) or anchor.step_index != step_index:
            raise SourceHarvesterError("anchor provider returned a duplicate or missing step")
        captures.append(harvest_anchor(config, anchor))
    return _persist_harvest(output_dir, config, captures)


def read_harvest_closure(output_dir: str | Path) -> AuthenticatedHarvest:
    """Re-authenticate aggregate source, sequence, sidecar, and bindings."""

    root = Path(output_dir)
    _reject_symlinks(root)
    try:
        source, source_bridge = read_source_closure(root)
    except Exception as error:
        if isinstance(error, SourceHarvesterError):
            raise
        raise SourceHarvesterError("aggregate source closure authentication failed") from error
    metadata = _read_canonical_json(root / HARVEST_METADATA_FILENAME, field="harvest metadata")
    receipt = _read_receipt(root / HARVEST_RECEIPT_FILENAME, HARVEST_RECEIPT_FIELDS, HARVESTER_SCHEMA)
    body = {key: value for key, value in metadata.items() if key != "harvest_metadata_sha256"}
    supplied = _digest(metadata.get("harvest_metadata_sha256"), field="harvest_metadata_sha256")
    if canonical_sha256(body) != supplied:
        raise SourceHarvesterError("harvest metadata self-digest failed")
    if metadata.get("schema") != HARVESTER_SCHEMA or metadata.get("schema_version") != HARVESTER_SCHEMA_VERSION:
        raise SourceHarvesterError("harvester schema is stale")
    if metadata.get("status") != HARVEST_STATUS or metadata.get("contract_status") != FROZEN_CONTRACT_STATUS:
        raise SourceHarvesterError("harvest status is not frozen implementation status")
    for field in (
        "contract_sha256",
        "config_sha256",
        "code_manifest_sha256",
        "field_root_digest",
        "q1_checkpoint_sha256",
        "q2_checkpoint_sha256",
        "q1_parameter_sha256",
        "q2_parameter_sha256",
        "source_arrays_sha256",
        "source_npz_sha256",
        "source_metadata_sha256",
        "source_bridge_metadata_sha256",
        "capture_sequence_metadata_sha256",
        "capture_sequence_sha256",
        "decision_context_metadata_sha256",
        "decision_context_npz_sha256",
        "decision_context_sha256",
    ):
        _digest(metadata.get(field), field=f"harvest.{field}")
    if metadata.get("target_field") != NATIVE_BITS_LABEL or metadata.get("target_scale") != NATIVE_BITS_SCALE or metadata.get("target_normalized") is not False:
        raise SourceHarvesterError("harvest target is not native z3_bits")
    if metadata.get("filtering") != NO_FILTERING:
        raise SourceHarvesterError("harvest declares target/sign/support filtering")
    if any(metadata.get(field) is not False for field in ("test_split_opened", "episode_training", "learner_update")):
        raise SourceHarvesterError("harvest crosses a forbidden boundary")
    if source.rows != EXPECTED_ROWS or metadata.get("rows") != EXPECTED_ROWS:
        raise SourceHarvesterError("aggregate source row count is not exactly 1000")
    if source.world_seed != int(metadata["world_seed"]) or source.lineage != int(metadata["lineage"]) or source.split != metadata["split"]:
        raise SourceHarvesterError("aggregate source identity disagrees with harvest metadata")
    if source.field_root_digest != metadata["field_root_digest"]:
        raise SourceHarvesterError("aggregate source field root disagrees with metadata")
    if float(source.kappa_bits).hex() != str(metadata["kappa_bits_hex"]):
        raise SourceHarvesterError("aggregate source kappa disagrees with metadata")
    if source.arrays_sha256() != metadata["source_arrays_sha256"] or receipt["source_arrays_sha256"] != metadata["source_arrays_sha256"]:
        raise SourceHarvesterError("aggregate source digest mismatch")
    if _file_sha256(root / "source.npz") != metadata["source_npz_sha256"] or _file_sha256(root / "metadata.json") != metadata["source_metadata_sha256"]:
        raise SourceHarvesterError("aggregate source file binding mismatch")
    if _file_sha256(root / BRIDGE_METADATA_FILENAME) != metadata[
        "source_bridge_metadata_sha256"
    ]:
        raise SourceHarvesterError("aggregate source bridge binding mismatch")
    if metadata.get("world_seed") not in metadata.get("declared_worlds", ()) or metadata.get("lineage") not in metadata.get("declared_lineages", ()):
        raise SourceHarvesterError("harvest identity is outside its declared config")
    if receipt["metadata_sha256"] != _file_sha256(root / HARVEST_METADATA_FILENAME):
        raise SourceHarvesterError("harvest metadata file digest mismatch")
    if receipt["harvest_metadata_sha256"] != supplied:
        raise SourceHarvesterError("harvest metadata receipt self-digest mismatch")
    sidecar, sidecar_metadata = _read_sidecar(root)
    if sidecar_metadata.get("source_arrays_sha256") != source.arrays_sha256():
        raise SourceHarvesterError("sidecar/source array identity mismatch")
    if sidecar_metadata.get("world_seed") != source.world_seed or sidecar_metadata.get("lineage") != source.lineage or sidecar_metadata.get("split") != source.split:
        raise SourceHarvesterError("sidecar identity disagrees with source")
    if (
        sidecar_metadata.get("contract_sha256") != metadata["contract_sha256"]
        or sidecar_metadata.get("config_sha256") != metadata["config_sha256"]
        or sidecar_metadata.get("code_manifest_sha256")
        != metadata["code_manifest_sha256"]
    ):
        raise SourceHarvesterError("sidecar contract/config binding drifted")
    for field in (
        "q1_checkpoint_sha256",
        "q2_checkpoint_sha256",
        "q1_parameter_sha256",
        "q2_parameter_sha256",
        "field_root_digest",
        "kappa_bits_hex",
    ):
        if sidecar_metadata.get(field) != metadata[field]:
            raise SourceHarvesterError(f"sidecar {field} binding drifted")
    if not np.array_equal(sidecar["action_mask"], source.action_mask) or not np.array_equal(sidecar["reference_actions"], source.reference_actions):
        raise SourceHarvesterError("sidecar row identity differs from source arrays")
    if np.any((source.target_surface_bits > 0.0) & ~source.positive_credit_compatible):
        raise SourceHarvesterError("positive target is outside compatibility")
    sequence = _validate_sequence(root, source, sidecar)
    for field in (
        "contract_sha256",
        "config_sha256",
        "code_manifest_sha256",
        "q1_checkpoint_sha256",
        "q2_checkpoint_sha256",
        "q1_parameter_sha256",
        "q2_parameter_sha256",
    ):
        if sequence.get(field) != metadata[field]:
            raise SourceHarvesterError(f"capture sequence {field} binding drifted")
    if sequence.get("aggregate_source_arrays_sha256") != source.arrays_sha256():
        raise SourceHarvesterError("sequence/source aggregate digest mismatch")
    if sequence.get("aggregate_sidecar_arrays_sha256") != _arrays_sha256(sidecar):
        raise SourceHarvesterError("sequence/sidecar aggregate digest mismatch")
    if receipt["capture_sequence_sha256"] != sequence["sequence_sha256"]:
        raise SourceHarvesterError("harvest receipt sequence binding mismatch")
    if receipt["decision_context_sha256"] != sidecar_metadata["decision_context_sha256"]:
        raise SourceHarvesterError("harvest receipt sidecar binding mismatch")
    if metadata["capture_sequence_metadata_sha256"] != _file_sha256(root / CAPTURE_SEQUENCE_FILENAME):
        raise SourceHarvesterError("harvest sequence metadata binding mismatch")
    if metadata["decision_context_metadata_sha256"] != _file_sha256(root / DECISION_CONTEXT_METADATA_FILENAME):
        raise SourceHarvesterError("harvest sidecar metadata binding mismatch")
    return AuthenticatedHarvest(
        source=source,
        metadata=metadata,
        sequence=sequence,
        sidecar=sidecar,
    )


harvest_shard = harvest_source_shard


__all__ = [
    "ACTION_CONTEXT_DIM",
    "ACTION_DIM",
    "AnchorCapture",
    "AnchorInput",
    "AuthenticatedHarvest",
    "CAPTURE_SEQUENCE_FILENAME",
    "CAPTURE_SEQUENCE_RECEIPT_FILENAME",
    "CAPTURE_SEQUENCE_SCHEMA",
    "DECISION_CONTEXT_METADATA_FILENAME",
    "DECISION_CONTEXT_NPZ_FILENAME",
    "DECISION_CONTEXT_RECEIPT_FILENAME",
    "DECISION_CONTEXT_SCHEMA",
    "EXPECTED_ROWS",
    "EXPECTED_STEPS",
    "EXPECTED_USERS",
    "ExactZ3Label",
    "HARVESTER_SCHEMA",
    "HARVEST_METADATA_FILENAME",
    "HARVEST_RECEIPT_FILENAME",
    "HARVEST_STATUS",
    "NATIVE_BITS_LABEL",
    "NATIVE_BITS_SCALE",
    "NO_FILTERING",
    "SourceHarvestConfig",
    "SourceHarvesterError",
    "canonical_sha256",
    "harvest_anchor",
    "harvest_shard",
    "harvest_source_shard",
    "make_v018_anchor_input",
    "read_harvest_closure",
]
