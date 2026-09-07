#!/usr/bin/env python3
"""Fail-closed V0.23 replay and full-roster physical callbacks.

Importing this module is inert: it imports neither the simulator nor the
V0.23 source adapter.  :func:`build_runtime` returns a cheap callback object;
the production backend authenticates and opens the frozen TRAIN world only on
the first ``replay_anchor`` call.

The callback object deliberately owns a narrow state machine.  It accepts
phases 1..9 in order, accepts each physical role exactly once, evaluates each
of the 32 keyed draws exactly once, and has no optimizer, training, TEST,
coordinator, repair, or action-selection path.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
from types import ModuleType
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE_ADAPTER_PATH = HERE / "v023_lcsrs_source_adapter.py"
PREFLIGHT_PATH = HERE / "PREFLIGHT-MANIFEST.json"
PREFLIGHT_DIGEST_PATH = HERE / "PREFLIGHT-MANIFEST.sha256"

CONTRACT_SHA256 = "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
FIELD_COMPONENT = "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1"
LINEAGE = 2026092101
DRAW_COUNT = 32
ACTION_COUNT = 28
PHASES = tuple(range(1, 10))
WORLDS = tuple(range(2026121705, 2026121713))
SEEDS = (2026135101, 2026135102, 2026135103)
ARMS = ("INFORMED", "MATCHED_PLACEBO")
NONMUTATION_NAMES = (
    "environment",
    "rng",
    "q1",
    "q2",
    "q3",
    "matched_field",
)
FORBIDDEN_VIEW_FIELDS = (
    "teacher",
    "teacher_q3",
    "targets",
    "labels",
    "outcomes",
    "profile_bits",
    "profile_energy_j",
)


class V023CompositionRuntimeError(RuntimeError):
    """The production replay/measurement boundary failed closed."""


def _step_result_observation(environment: Any, result: Any) -> Any:
    """Get the successor observation from the wrapper's full step outcome.

    ``TrainerEnvironment.step`` returns the compact ``StepResult``; the full
    physical ``StepOutcome`` is available through ``last_outcome``.  The
    direct-result fallback keeps this seam compatible with native outcomes.
    """

    full_outcome = getattr(environment, "last_outcome", None)
    observation = getattr(full_outcome, "observation", None)
    if observation is None:
        observation = getattr(result, "observation", None)
    if observation is None:
        raise V023CompositionRuntimeError(
            "step result omitted observation and environment has no full last_outcome"
        )
    return observation


def _sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023CompositionRuntimeError(f"{field} is not a lowercase SHA-256")
    return value


def _file_sha256(path: Path, *, field: str) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023CompositionRuntimeError(f"{field} is missing or is a symlink: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
        raise V023CompositionRuntimeError("value is not finite canonical JSON") from error


def _read_canonical_json(path: Path, *, field: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023CompositionRuntimeError(f"{field} is missing or is a symlink")
    raw = target.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023CompositionRuntimeError(f"{field} is not ASCII JSON") from error
    if not isinstance(payload, dict) or raw not in (
        _canonical_bytes(payload),
        _canonical_bytes(payload) + b"\n",
    ):
        raise V023CompositionRuntimeError(f"{field} is not canonical JSON")
    return payload


def _safe_child(root: Path, child: Path, *, field: str) -> Path:
    root_resolved = Path(root).resolve()
    unresolved = Path(child)
    if unresolved.is_symlink() or not unresolved.is_file():
        raise V023CompositionRuntimeError(f"{field} is missing or is a symlink")
    resolved = unresolved.resolve()
    if not resolved.is_relative_to(root_resolved):
        raise V023CompositionRuntimeError(f"{field} escapes its declared root")
    return resolved


def _array_sha256(value: object, *, domain: str) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    if array.dtype == object:
        raise V023CompositionRuntimeError("object arrays cannot be hashed")
    digest = hashlib.sha256()
    digest.update(domain.encode("ascii"))
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _action_sha256(value: object) -> str:
    array = np.ascontiguousarray(np.asarray(value), dtype=np.int64)
    if array.ndim != 1 or array.size < 2:
        raise V023CompositionRuntimeError("physical action vector must contain a full roster")
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-profile-actions-v1")
    digest.update(struct.pack(">I", int(array.size)))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _readonly(value: object, *, dtype: np.dtype[Any], ndim: int, field: str) -> np.ndarray:
    try:
        array = np.array(value, dtype=dtype, copy=True)
    except (TypeError, ValueError, OverflowError) as error:
        raise V023CompositionRuntimeError(f"{field} cannot be materialised") from error
    if array.ndim != ndim or (np.issubdtype(array.dtype, np.floating) and not np.all(np.isfinite(array))):
        raise V023CompositionRuntimeError(f"{field} is malformed")
    array.setflags(write=False)
    return array


@dataclass(frozen=True)
class ReplayMaterial:
    """Target-free backend result used to construct a typed replay receipt."""

    capture: object
    q1: np.ndarray
    q2: np.ndarray
    action_mask: np.ndarray
    reference_actions: np.ndarray
    backend_anchor: object
    preflight_manifest_sha256: str
    source_manifest_sha256: str
    source_index_sha256: str
    field_root_sha256: str
    target_free_inference: bool = True

    def __post_init__(self) -> None:
        if self.target_free_inference is not True:
            raise V023CompositionRuntimeError("replay backend did not attest target-free inference")
        for name in (
            "preflight_manifest_sha256",
            "source_manifest_sha256",
            "source_index_sha256",
            "field_root_sha256",
        ):
            _sha256(getattr(self, name), field=f"replay material {name}")
        q1 = _readonly(self.q1, dtype=np.dtype(np.float32), ndim=2, field="replayed Q1")
        q2 = _readonly(self.q2, dtype=np.dtype(np.float32), ndim=2, field="replayed Q2")
        raw_mask = np.asarray(self.action_mask)
        if raw_mask.dtype != np.bool_:
            raise V023CompositionRuntimeError("replayed action mask is not Boolean")
        mask = _readonly(raw_mask, dtype=np.dtype(np.bool_), ndim=2, field="replayed action mask")
        references = _readonly(
            self.reference_actions,
            dtype=np.dtype(np.int64),
            ndim=1,
            field="replayed references",
        )
        if (
            q1.shape != q2.shape
            or q1.shape != mask.shape
            or q1.shape[1] != ACTION_COUNT
            or references.shape != (q1.shape[0],)
        ):
            raise V023CompositionRuntimeError("replayed Q1/Q2/mask/reference shapes disagree")
        object.__setattr__(self, "q1", q1)
        object.__setattr__(self, "q2", q2)
        object.__setattr__(self, "action_mask", mask)
        object.__setattr__(self, "reference_actions", references)


@dataclass(frozen=True)
class DrawMeasurement:
    """One complete-vector, one-draw noncommitting physical measurement."""

    draw_index: int
    action_sha256: str
    common_field_sha256: str
    per_user_bits: np.ndarray
    energy_j: float
    served: np.ndarray
    active_beam_keys: np.ndarray
    active_satellites: np.ndarray
    beam_power_w: np.ndarray
    nonmutation_before: Mapping[str, str]
    nonmutation_after: Mapping[str, str]

    def __post_init__(self) -> None:
        if type(self.draw_index) is not int or not 0 <= self.draw_index < DRAW_COUNT:
            raise V023CompositionRuntimeError("draw measurement index is outside 0..31")
        _sha256(self.action_sha256, field="draw action digest")
        _sha256(self.common_field_sha256, field="draw common-field digest")
        bits = _readonly(
            self.per_user_bits,
            dtype=np.dtype(np.float64),
            ndim=1,
            field="draw per-user bits",
        )
        raw_served = np.asarray(self.served)
        if raw_served.dtype != np.bool_:
            raise V023CompositionRuntimeError("draw served array is not Boolean")
        served = _readonly(raw_served, dtype=np.dtype(np.bool_), ndim=1, field="draw served")
        beams = _readonly(
            self.active_beam_keys,
            dtype=np.dtype(np.int64),
            ndim=2,
            field="draw active beam keys",
        )
        satellites = _readonly(
            self.active_satellites,
            dtype=np.dtype(np.int64),
            ndim=1,
            field="draw active satellites",
        )
        powers = _readonly(
            self.beam_power_w,
            dtype=np.dtype(np.float64),
            ndim=1,
            field="draw beam powers",
        )
        energy = float(self.energy_j)
        if (
            bits.shape != served.shape
            or beams.shape[1:] != (2,)
            or powers.shape != (beams.shape[0],)
            or np.any(bits < 0.0)
            or np.any(powers < 0.0)
            or not math.isfinite(energy)
            or energy <= 0.0
        ):
            raise V023CompositionRuntimeError("draw physical arrays are malformed")
        before = dict(self.nonmutation_before)
        after = dict(self.nonmutation_after)
        if tuple(before) != NONMUTATION_NAMES or tuple(after) != NONMUTATION_NAMES:
            raise V023CompositionRuntimeError("draw mutation receipt names/order drifted")
        for name in NONMUTATION_NAMES:
            _sha256(before[name], field=f"draw before {name}")
            _sha256(after[name], field=f"draw after {name}")
        object.__setattr__(self, "per_user_bits", bits)
        object.__setattr__(self, "served", served)
        object.__setattr__(self, "active_beam_keys", beams)
        object.__setattr__(self, "active_satellites", satellites)
        object.__setattr__(self, "beam_power_w", powers)
        object.__setattr__(self, "energy_j", energy)
        object.__setattr__(self, "nonmutation_before", before)
        object.__setattr__(self, "nonmutation_after", after)


class V023CompositionRuntime:
    """Typed callbacks with one-pass sequencing and defensive receipts."""

    def __init__(self, *, spec: object, adapter: ModuleType, backend: object) -> None:
        self._spec = spec
        self._adapter = adapter
        self._backend = backend
        self._failed = False
        self._expected_phase = 1
        self._current_material: ReplayMaterial | None = None
        self._current_handle: object | None = None
        self._next_role = 0
        self._source_index_sha256: str | None = None
        self._field_root_sha256: str | None = None
        self._common_fields: np.ndarray | None = None
        self._validate_factory_scope()

    def _validate_factory_scope(self) -> None:
        world = getattr(self._spec, "held_out_world", None)
        seed = getattr(self._spec, "student_seed", None)
        arm = getattr(self._spec, "arm", None)
        if world not in WORLDS or seed not in SEEDS or arm not in ARMS:
            raise V023CompositionRuntimeError("composition runtime spec is outside the frozen panel")
        for name in (
            "preflight_manifest_sha256",
            "source_manifest_sha256",
            "fit_receipt_sha256",
        ):
            _sha256(getattr(self._spec, name, None), field=f"runtime spec {name}")
        for name in ("model_bytes_sha256", "model_sha256"):
            value = getattr(self._spec, name, None)
            if value is not None:
                _sha256(value, field=f"runtime spec {name}")
        declared_contract = getattr(self._spec, "contract_sha256", None)
        contract = _sha256(
            (
                declared_contract
                if declared_contract is not None
                else getattr(self._adapter, "V023_CONTRACT_SHA256", None)
            ),
            field="runtime spec contract_sha256",
        )
        if contract != CONTRACT_SHA256:
            raise V023CompositionRuntimeError("runtime spec contract digest drifted")
        required_adapter_names = (
            "ReplayAnchorRequest",
            "PhysicalEvaluationRequest",
            "ImmutableAnchorHandle",
            "ReplayedAnchor",
            "PhysicalEvaluation",
        )
        if any(not callable(getattr(self._adapter, name, None)) for name in required_adapter_names):
            raise V023CompositionRuntimeError("composition adapter omits a required typed API")
        if not callable(getattr(self._backend, "replay_anchor", None)) or not callable(
            getattr(self._backend, "evaluate_draw", None)
        ):
            raise V023CompositionRuntimeError("runtime backend omits replay/evaluation methods")

    def _guard(self) -> None:
        if self._failed:
            raise V023CompositionRuntimeError("composition runtime is poisoned after a prior failure")

    def _poison(self, error: Exception) -> None:
        self._failed = True
        if isinstance(error, V023CompositionRuntimeError):
            raise error
        raise V023CompositionRuntimeError("composition runtime callback failed closed") from error

    def _validate_replay_request(self, request: object) -> None:
        if not isinstance(request, self._adapter.ReplayAnchorRequest):
            raise V023CompositionRuntimeError("replay callback requires ReplayAnchorRequest")
        if self._current_material is not None and self._next_role != len(self._expected_roles()):
            raise V023CompositionRuntimeError("next anchor requested before all physical roles")
        if self._expected_phase not in PHASES:
            raise V023CompositionRuntimeError("all nine anchors were already replayed")
        expected_anchor = f"w{self._spec.held_out_world}:t{self._expected_phase}"
        if (
            request.world != self._spec.held_out_world
            or request.phase != self._expected_phase
            or request.anchor_id != expected_anchor
        ):
            raise V023CompositionRuntimeError("replay world/phase/anchor identity drifted")
        if Path(request.source_directory).resolve() != Path(self._spec.source_directory).resolve():
            raise V023CompositionRuntimeError("replay source directory disagrees with server spec")
        if (
            request.preflight_manifest_sha256 != self._spec.preflight_manifest_sha256
            or request.source_manifest_sha256 != self._spec.source_manifest_sha256
        ):
            raise V023CompositionRuntimeError("replay manifest identity disagrees with server spec")
        if self._source_index_sha256 not in (None, request.source_index_sha256):
            raise V023CompositionRuntimeError("replay source-index identity changed between anchors")
        if self._field_root_sha256 not in (None, request.field_root_sha256):
            raise V023CompositionRuntimeError("replay field root changed between anchors")

    def _bind_material(self, request: object, material: ReplayMaterial) -> None:
        if not isinstance(material, ReplayMaterial):
            raise V023CompositionRuntimeError("replay backend returned an untyped material")
        for name in (
            "preflight_manifest_sha256",
            "source_manifest_sha256",
            "source_index_sha256",
            "field_root_sha256",
        ):
            if getattr(material, name) != getattr(request, name):
                raise V023CompositionRuntimeError(f"replay material {name} disagrees")
        capture = material.capture
        verify = getattr(capture, "verify", None)
        actual_predecision = None if not callable(verify) else verify()
        if actual_predecision != request.predecision_sha256:
            topology = getattr(capture, "topology", None)
            view = getattr(capture, "view", None)
            provenance = getattr(capture, "native_observation_provenance", None)
            topology_capture = getattr(topology, "capture", None)
            snapshot = getattr(topology_capture, "q12_snapshot", None)
            details = {
                "expected_predecision": request.predecision_sha256,
                "actual_predecision": actual_predecision,
                "expected_topology": request.topology_sha256,
                "actual_topology": None if topology is None else getattr(topology, "content_digest", None),
                "expected_view": request.view_sha256,
                "actual_view": None if view is None else getattr(view, "content_digest", None),
                "expected_state_schema": request.state_schema_sha256,
                "actual_state_schema": getattr(capture, "state_schema_sha256", None),
                "expected_state": request.state_sha256,
                "actual_state": getattr(capture, "state_sha256", None),
                "expected_event": request.q12_event_sha256,
                "actual_event": None if provenance is None else getattr(provenance, "content_digest", None),
                "expected_q12_snapshot": request.q12_snapshot_sha256,
                "actual_q12_snapshot": None if snapshot is None else getattr(snapshot, "content_digest", None),
                "expected_q12_model": request.q12_model_sha256,
                "actual_q12_model": None if snapshot is None else getattr(snapshot, "model_digest", None),
                "expected_q12_source_state": request.q12_source_state_sha256,
                "actual_q12_source_state": None if snapshot is None else getattr(snapshot, "source_state_digest", None),
                "expected_reference_actions": request.reference_actions_sha256,
                "actual_reference_actions": _array_sha256(
                    material.reference_actions, domain="v023-reference-actions"
                ),
                "actual_action_mask": _array_sha256(
                    material.action_mask, domain="v023-diagnostic-action-mask"
                ),
            }
            raise V023CompositionRuntimeError(
                "replayed predecision digest disagrees: " + repr(details)
            )
        topology = getattr(capture, "topology", None)
        topology_verify = getattr(topology, "verify", None)
        view = getattr(capture, "view", None)
        view_verify = getattr(view, "verify", None)
        if (
            not callable(topology_verify)
            or topology_verify() != request.topology_sha256
            or not callable(view_verify)
            or view_verify() != request.view_sha256
        ):
            raise V023CompositionRuntimeError("replayed topology/view digest disagrees")
        topology_capture = getattr(topology, "capture", None)
        snapshot = getattr(topology_capture, "q12_snapshot", None)
        provenance = getattr(capture, "native_observation_provenance", None)
        scalar_checks = {
            "world": getattr(topology_capture, "world_id", None),
            "phase": getattr(topology_capture, "phase", None),
            "anchor_id": getattr(topology_capture, "anchor_id", None),
            "state_schema_sha256": getattr(capture, "state_schema_sha256", None),
            "state_sha256": getattr(capture, "state_sha256", None),
            "q12_snapshot_sha256": getattr(snapshot, "content_digest", None),
            "q12_model_sha256": getattr(snapshot, "model_digest", None),
            "q12_source_state_sha256": getattr(snapshot, "source_state_digest", None),
            "q12_event_sha256": getattr(snapshot, "native_observation_event_digest", None),
        }
        mismatched = [name for name, actual in scalar_checks.items() if actual != getattr(request, name)]
        if mismatched:
            raise V023CompositionRuntimeError(
                "replayed scalar identity/digest mismatch: " + ", ".join(mismatched)
            )
        if getattr(provenance, "field_root_digest", None) != request.field_root_sha256:
            raise V023CompositionRuntimeError("replayed observation field root disagrees")
        for name, expected, actual in (
            ("Q1", getattr(snapshot, "q1", None), material.q1),
            ("Q2", getattr(snapshot, "q2", None), material.q2),
            ("action mask", getattr(topology_capture, "action_mask", None), material.action_mask),
            (
                "reference actions",
                getattr(topology_capture, "reference_actions", None),
                material.reference_actions,
            ),
        ):
            if not np.array_equal(np.asarray(expected), np.asarray(actual)):
                raise V023CompositionRuntimeError(f"replayed {name} disagrees with capture")
        if _array_sha256(
            material.reference_actions, domain="v023-reference-actions"
        ) != request.reference_actions_sha256:
            raise V023CompositionRuntimeError("replayed reference-action digest disagrees")
        if any(hasattr(view, name) for name in FORBIDDEN_VIEW_FIELDS):
            raise V023CompositionRuntimeError("replayed view exposes teacher/target/outcome data")
        if any(
            np.asarray(getattr(view, name)).flags.writeable
            for name in ("action_context", "tokens", "token_mask", "action_mask", "reference_actions")
        ):
            raise V023CompositionRuntimeError("replayed view is mutable")
        if not np.array_equal(np.asarray(view.action_mask), material.action_mask) or not np.array_equal(
            np.asarray(view.reference_actions), material.reference_actions
        ):
            raise V023CompositionRuntimeError("replayed view mask/reference disagrees")

    def replay_anchor(self, request: object) -> object:
        """Rebuild and bind exactly the next TRAIN predecision anchor."""

        self._guard()
        try:
            self._validate_replay_request(request)
            material = self._backend.replay_anchor(request)
            self._bind_material(request, material)
            handle = self._adapter.ImmutableAnchorHandle(
                token=(
                    f"v023:{request.source_index_sha256}:{request.world}:"
                    f"{request.phase}:{request.anchor_id}"
                ),
                content_digest=request.predecision_sha256,
            )
            result = self._adapter.ReplayedAnchor(
                handle=handle,
                world=request.world,
                phase=request.phase,
                anchor_id=request.anchor_id,
                predecision_sha256=request.predecision_sha256,
                state_schema_sha256=request.state_schema_sha256,
                state_sha256=request.state_sha256,
                q12_snapshot_sha256=request.q12_snapshot_sha256,
                q12_model_sha256=request.q12_model_sha256,
                q12_source_state_sha256=request.q12_source_state_sha256,
                q12_event_sha256=request.q12_event_sha256,
                view_sha256=request.view_sha256,
                topology_sha256=request.topology_sha256,
                q1=material.q1,
                q2=material.q2,
                action_mask=material.action_mask,
                reference_actions=material.reference_actions,
                view=material.capture.view,
            )
            self._current_material = material
            self._current_handle = handle
            self._next_role = 0
            self._common_fields = None
            self._source_index_sha256 = request.source_index_sha256
            self._field_root_sha256 = request.field_root_sha256
            self._expected_phase += 1
            return result
        except Exception as error:
            self._poison(error)

    def _expected_roles(self) -> tuple[str, str, str]:
        return ("ZERO_SURFACE_B", str(self._spec.arm), "TEACHER_ORACLE")

    def _validate_physical_request(self, request: object) -> tuple[np.ndarray, str]:
        if not isinstance(request, self._adapter.PhysicalEvaluationRequest):
            raise V023CompositionRuntimeError("physical callback requires PhysicalEvaluationRequest")
        if self._current_material is None or self._current_handle is None:
            raise V023CompositionRuntimeError("physical request has no live replay anchor")
        if self._next_role >= len(self._expected_roles()):
            raise V023CompositionRuntimeError("all physical roles for this anchor were already measured")
        if request.role != self._expected_roles()[self._next_role]:
            raise V023CompositionRuntimeError("physical role order or multiplicity drifted")
        if request.handle != self._current_handle:
            raise V023CompositionRuntimeError("physical request handle disagrees with replay")
        expected_phase = self._expected_phase - 1
        if (
            request.world != self._spec.held_out_world
            or request.phase != expected_phase
            or request.anchor_id != f"w{request.world}:t{expected_phase}"
        ):
            raise V023CompositionRuntimeError("physical world/phase/anchor identity drifted")
        if not np.array_equal(request.draw_index, np.arange(DRAW_COUNT, dtype=np.int64)):
            raise V023CompositionRuntimeError("physical request draw sequence drifted")
        actions = np.array(request.actions, dtype=np.int64, copy=True)
        material = self._current_material
        if actions.shape != (material.action_mask.shape[0],):
            raise V023CompositionRuntimeError("physical action vector is not the complete roster")
        if np.any(actions < 0) or np.any(actions >= ACTION_COUNT) or not np.all(
            material.action_mask[np.arange(actions.size), actions]
        ):
            raise V023CompositionRuntimeError("physical action vector contains an illegal action")
        actions.setflags(write=False)
        return actions, _action_sha256(actions)

    def _assemble_physical(
        self,
        *,
        request: object,
        actions: np.ndarray,
        action_digest: str,
        draws: list[DrawMeasurement],
    ) -> object:
        if len(draws) != DRAW_COUNT or tuple(item.draw_index for item in draws) != tuple(range(DRAW_COUNT)):
            raise V023CompositionRuntimeError("physical backend did not return exactly draws 0..31")
        users = actions.size
        if any(item.per_user_bits.shape != (users,) or item.served.shape != (users,) for item in draws):
            raise V023CompositionRuntimeError("physical backend did not measure the full roster")
        if any(item.action_sha256 != action_digest for item in draws):
            raise V023CompositionRuntimeError("physical backend action identity drifted")
        field_digests = np.asarray(
            [item.common_field_sha256.encode("ascii") for item in draws], dtype="S64"
        )
        if self._common_fields is not None and not np.array_equal(field_digests, self._common_fields):
            raise V023CompositionRuntimeError("physical roles did not reuse one common draw field")
        maximum_beams = max(item.active_beam_keys.shape[0] for item in draws)
        maximum_satellites = max(item.active_satellites.shape[0] for item in draws)
        beam_keys = np.full((DRAW_COUNT, maximum_beams, 2), -1, dtype=np.int64)
        beam_power = np.zeros((DRAW_COUNT, maximum_beams), dtype=np.float64)
        satellites = np.full((DRAW_COUNT, maximum_satellites), -1, dtype=np.int64)
        beam_counts = np.zeros(DRAW_COUNT, dtype=np.int64)
        satellite_counts = np.zeros(DRAW_COUNT, dtype=np.int64)
        before = np.empty((DRAW_COUNT, len(NONMUTATION_NAMES)), dtype="S64")
        after = np.empty_like(before)
        for row, item in enumerate(draws):
            beam_count = item.active_beam_keys.shape[0]
            satellite_count = item.active_satellites.shape[0]
            beam_counts[row] = beam_count
            satellite_counts[row] = satellite_count
            beam_keys[row, :beam_count] = item.active_beam_keys
            beam_power[row, :beam_count] = item.beam_power_w
            satellites[row, :satellite_count] = item.active_satellites
            before[row] = [item.nonmutation_before[name].encode("ascii") for name in NONMUTATION_NAMES]
            after[row] = [item.nonmutation_after[name].encode("ascii") for name in NONMUTATION_NAMES]
        flags = before == after
        if not np.all(flags):
            raise V023CompositionRuntimeError("physical evaluation mutated a frozen input")
        bits = np.stack([item.per_user_bits for item in draws]).astype(np.float64, copy=False)
        totals = np.sum(bits, axis=1, dtype=np.float64)
        return self._adapter.PhysicalEvaluation(
            role=request.role,
            actions=actions,
            draw_index=np.arange(DRAW_COUNT, dtype=np.int64),
            total_bits=totals,
            per_user_bits=bits,
            energy_j=np.asarray([item.energy_j for item in draws], dtype=np.float64),
            served=np.stack([item.served for item in draws]).astype(np.bool_, copy=False),
            active_beam_counts=beam_counts,
            active_beam_keys=beam_keys,
            active_satellite_counts=satellite_counts,
            active_satellites=satellites,
            beam_power_w=beam_power,
            action_sha256=action_digest,
            common_field_digest=field_digests,
            nonmutation_names=NONMUTATION_NAMES,
            nonmutation_before_sha256=before,
            nonmutation_after_sha256=after,
            nonmutation_flags=flags,
        )

    def evaluate_physical(self, request: object) -> object:
        """Evaluate one unchanged full-roster vector on all 32 keyed draws."""

        self._guard()
        try:
            actions, action_digest = self._validate_physical_request(request)
            original_request_digest = _action_sha256(request.actions)
            draws: list[DrawMeasurement] = []
            assert self._current_material is not None
            for draw_index in range(DRAW_COUNT):
                measurement = self._backend.evaluate_draw(
                    self._current_material,
                    actions,
                    draw_index,
                )
                if not isinstance(measurement, DrawMeasurement):
                    raise V023CompositionRuntimeError("physical backend returned an untyped draw")
                if _action_sha256(actions) != action_digest or _action_sha256(request.actions) != original_request_digest:
                    raise V023CompositionRuntimeError("physical backend edited the selected action vector")
                if any(
                    measurement.nonmutation_before[name]
                    != measurement.nonmutation_after[name]
                    for name in NONMUTATION_NAMES
                ):
                    raise V023CompositionRuntimeError(
                        "physical evaluation mutated a frozen input"
                    )
                draws.append(measurement)
            result = self._assemble_physical(
                request=request,
                actions=actions,
                action_digest=action_digest,
                draws=draws,
            )
            if self._common_fields is None:
                self._common_fields = np.array(result.common_field_digest, copy=True)
                self._common_fields.setflags(write=False)
            self._next_role += 1
            return result
        except Exception as error:
            self._poison(error)


class _ProductionBackend:
    """Lazy adapter around the frozen source/simulator implementation."""

    def __init__(self, spec: object, adapter: ModuleType) -> None:
        self._spec = spec
        self._adapter = adapter
        self._source: ModuleType | None = None
        self._source_runtime: object | None = None
        self._v018: object | None = None
        self._q1: object | None = None
        self._q2: object | None = None
        self._environment: object | None = None
        self._step_env: object | None = None
        self._env_rng: np.random.Generator | None = None
        self._observation: object | None = None
        self._model_digest: str | None = None
        self._q1_sha256: str | None = None
        self._q2_sha256: str | None = None
        self._q3_sha256: str | None = None
        self._model_bytes_sha256: str | None = None
        self._last_background: np.ndarray | None = None
        self._last_phase = 0
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        self._source_index: dict[str, Any] | None = None
        self._field_root_sha256: str | None = None

    def _load_source_module(self) -> ModuleType:
        if SOURCE_ADAPTER_PATH.is_symlink() or not SOURCE_ADAPTER_PATH.is_file():
            raise V023CompositionRuntimeError("frozen V0.23 source adapter is missing")
        name = f"mcrl_v023_composition_source_{id(self):x}"
        module_spec = importlib.util.spec_from_file_location(name, SOURCE_ADAPTER_PATH)
        if module_spec is None or module_spec.loader is None:
            raise V023CompositionRuntimeError("cannot load frozen V0.23 source adapter")
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[name] = module
        try:
            module_spec.loader.exec_module(module)
        except Exception as error:
            sys.modules.pop(name, None)
            raise V023CompositionRuntimeError("frozen V0.23 source adapter import failed") from error
        return module

    def _authenticate_source_files(self, request: object) -> tuple[dict[str, Any], Path]:
        root = Path(self._spec.source_directory)
        if root.is_symlink() or not root.is_dir():
            raise V023CompositionRuntimeError("source directory is missing or is a symlink")
        root = root.resolve()
        manifest_input = Path(self._spec.source_manifest)
        if not manifest_input.is_absolute():
            manifest_input = root / manifest_input
        manifest_path = _safe_child(root, manifest_input, field="source manifest")
        manifest = _read_canonical_json(manifest_path, field="source manifest")
        body = dict(manifest)
        body.pop("source_manifest_sha256", None)
        body.pop("manifest_sha256", None)
        declared_body = _sha256(
            manifest.get("source_manifest_sha256"), field="source manifest body digest"
        )
        if hashlib.sha256(_canonical_bytes(body)).hexdigest() != declared_body:
            raise V023CompositionRuntimeError("source manifest body seal disagrees")
        sealed = dict(manifest)
        sealed.pop("manifest_sha256", None)
        if hashlib.sha256(_canonical_bytes(sealed)).hexdigest() != _sha256(
            manifest.get("manifest_sha256"), field="source manifest seal"
        ):
            raise V023CompositionRuntimeError("source manifest final seal disagrees")
        if (
            declared_body != request.source_manifest_sha256
            or manifest.get("preflight_manifest_sha256") != request.preflight_manifest_sha256
            or manifest.get("contract_sha256") != CONTRACT_SHA256
            or manifest.get("split") != "TRAIN_DEVELOPMENT"
            or manifest.get("worlds") != list(WORLDS)
            or manifest.get("test_split_opened") is not False
            or manifest.get("episode_training") is not False
            or manifest.get("learner_update") is not False
        ):
            raise V023CompositionRuntimeError("source manifest identity/boundary drifted")
        entries = manifest.get("entries")
        if not isinstance(entries, list):
            raise V023CompositionRuntimeError("source manifest entries are missing")
        matches = [item for item in entries if isinstance(item, Mapping) and item.get("world") == request.world]
        if len(matches) != 1:
            raise V023CompositionRuntimeError("source manifest has no unique requested world")
        entry = matches[0]
        expected_relative = f"source/world-{request.world}.json"
        if entry.get("relative_name") != expected_relative:
            raise V023CompositionRuntimeError("source world path is not canonical")
        index_path = _safe_child(root, root / expected_relative, field="source world index")
        index_bytes = _file_sha256(index_path, field="source world index")
        if index_bytes != entry.get("sha256") or index_bytes != request.source_index_sha256:
            raise V023CompositionRuntimeError("source world index byte digest disagrees")
        index = _read_canonical_json(index_path, field="source world index")
        receipt = _sha256(index.get("receipt_sha256"), field="source world receipt seal")
        unsigned = dict(index)
        unsigned.pop("receipt_sha256", None)
        if hashlib.sha256(_canonical_bytes(unsigned)).hexdigest() != receipt:
            raise V023CompositionRuntimeError("source world receipt seal disagrees")
        world_receipt = index.get("world_receipt")
        if not isinstance(world_receipt, Mapping):
            raise V023CompositionRuntimeError("source world receipt is missing")
        if (
            index.get("world") != request.world
            or index.get("preflight_manifest_sha256") != request.preflight_manifest_sha256
            or index.get("contract_sha256") != CONTRACT_SHA256
            or index.get("split") != "TRAIN_DEVELOPMENT"
            or index.get("test_split_opened") is not False
            or index.get("episode_training") is not False
            or index.get("learner_update") is not False
            or world_receipt.get("field_root_digest") != request.field_root_sha256
            or world_receipt.get("phase_count") != 9
        ):
            raise V023CompositionRuntimeError("source world identity/boundary drifted")
        return index, index_path

    def _preflight_paths(self) -> tuple[Path, Path]:
        if _file_sha256(PREFLIGHT_PATH, field="preflight manifest") != self._spec.preflight_manifest_sha256:
            raise V023CompositionRuntimeError("runtime preflight bytes disagree with server spec")
        payload = _read_canonical_json(PREFLIGHT_PATH, field="preflight manifest")
        configuration = payload.get("configuration")
        bindings = payload.get("bindings")
        if not isinstance(configuration, Mapping) or not isinstance(bindings, list):
            raise V023CompositionRuntimeError("preflight manifest structure is malformed")
        if (
            configuration.get("split") != "TRAIN_DEVELOPMENT"
            or configuration.get("test_split_opened") is not False
            or configuration.get("episode_training") is not False
            or configuration.get("worlds") != list(WORLDS)
            or configuration.get("student_seeds") != list(SEEDS)
            or configuration.get("action_count") != ACTION_COUNT
            or configuration.get("draw_count") != DRAW_COUNT
            or configuration.get("steps_per_episode") != 10
            or configuration.get("users") != 100
            or configuration.get("lineage") != LINEAGE
            or configuration.get("field_component") != FIELD_COMPONENT
        ):
            raise V023CompositionRuntimeError("preflight execution configuration drifted")
        prereg_entries = [
            item for item in bindings if isinstance(item, Mapping) and item.get("role") == "preregistration"
        ]
        tle = configuration.get("tle")
        if len(prereg_entries) != 1 or not isinstance(tle, Mapping):
            raise V023CompositionRuntimeError("preflight prereg/TLE authority is missing")
        prereg_relative = prereg_entries[0].get("path")
        tle_default = tle.get("root_default")
        if not isinstance(prereg_relative, str) or not isinstance(tle_default, str):
            raise V023CompositionRuntimeError("preflight prereg/TLE paths are malformed")
        prereg = _safe_child(REPO, REPO / prereg_relative, field="frozen preregistration")
        if _file_sha256(prereg, field="frozen preregistration") != prereg_entries[0].get("sha256"):
            raise V023CompositionRuntimeError("frozen preregistration digest disagrees")
        unresolved_tle_root = Path(os.path.expanduser(tle_default))
        if unresolved_tle_root.is_symlink() or not unresolved_tle_root.is_dir():
            raise V023CompositionRuntimeError("frozen TLE root is missing or is a symlink")
        tle_root = unresolved_tle_root.resolve()
        return prereg, tle_root

    def _authenticate_fit_identity(self, request: object) -> None:
        spec_type = getattr(self._adapter, "CompositionShardSpec", None)
        authenticator = getattr(self._adapter, "authenticate_fit_artifact", None)
        if not callable(spec_type) or not callable(authenticator):
            raise V023CompositionRuntimeError("composition adapter omits fit authentication")
        manifest = Path(self._spec.source_manifest)
        if not manifest.is_absolute():
            manifest = Path(self._spec.source_directory) / manifest
        try:
            adapter_spec = spec_type(
                held_out_world=self._spec.held_out_world,
                student_seed=self._spec.student_seed,
                arm=self._spec.arm,
                source_directory=self._spec.source_directory,
                source_manifest=manifest,
                fit_receipt=self._spec.fit_receipt,
                preflight_manifest_sha256=self._spec.preflight_manifest_sha256,
                source_manifest_sha256=self._spec.source_manifest_sha256,
                output=self._spec.output,
            )
            fitted = authenticator(adapter_spec, device=self._spec.device)
        except Exception as error:
            raise V023CompositionRuntimeError("independent fit identity authentication failed") from error
        fitted_type = getattr(self._adapter, "AuthenticatedFitArtifact", None)
        if fitted_type is not None and not isinstance(fitted, fitted_type):
            raise V023CompositionRuntimeError(
                "independent fit authenticator returned an untyped artifact"
            )
        checks = {
            "held_out_world": self._spec.held_out_world,
            "student_seed": self._spec.student_seed,
            "arm": self._spec.arm,
            "preflight_manifest_sha256": self._spec.preflight_manifest_sha256,
            "source_manifest_sha256": self._spec.source_manifest_sha256,
            "fit_receipt_sha256": self._spec.fit_receipt_sha256,
            "source_index_sha256": request.source_index_sha256,
            "update_count": 2000,
        }
        mismatched = [name for name, expected in checks.items() if getattr(fitted, name, None) != expected]
        if mismatched:
            raise V023CompositionRuntimeError(
                "independently authenticated fit identity disagrees: " + ", ".join(mismatched)
            )
        model_bytes = _sha256(
            getattr(fitted, "model_bytes_sha256", None),
            field="authenticated fit model bytes",
        )
        model = _sha256(
            getattr(fitted, "model_sha256", None),
            field="authenticated fit logical model",
        )
        if getattr(self._spec, "model_bytes_sha256", None) not in (None, model_bytes):
            raise V023CompositionRuntimeError("declared model bytes disagree with authenticated fit")
        if getattr(self._spec, "model_sha256", None) not in (None, model):
            raise V023CompositionRuntimeError("declared logical model disagrees with authenticated fit")
        self._model_bytes_sha256 = model_bytes
        self._q3_sha256 = model

    def _initialize(self, request: object) -> None:
        self._source_index, _index_path = self._authenticate_source_files(request)
        self._authenticate_fit_identity(request)
        prereg, tle_root = self._preflight_paths()
        source = self._load_source_module()
        config = source.V023SourceAdapterConfig(
            tle_root=tle_root,
            prereg=prereg,
            manifest=PREFLIGHT_PATH,
            manifest_digest=PREFLIGHT_DIGEST_PATH,
        )
        runtime = source.V023RuntimeSourceAdapter(config)
        try:
            _v020, v018, q1, q2, auth, manifest_sha = runtime._authenticate(
                expected_manifest_sha256=request.preflight_manifest_sha256
            )
        except Exception as error:
            raise V023CompositionRuntimeError("frozen source/Q1+Q2 authentication failed") from error
        if (
            manifest_sha != request.preflight_manifest_sha256
            or not isinstance(auth, Mapping)
            or auth.get("q12_authority", {}).get("target_free_inference") is not True
        ):
            raise V023CompositionRuntimeError("frozen Q1+Q2 authority receipt drifted")
        q1_digest = str(v018._V015._q_parameter_sha256(q1))
        q2_digest = str(v018._V015._q_parameter_sha256(q2))
        world_receipt = self._source_index["world_receipt"]
        if (
            q1_digest != world_receipt.get("q1_parameter_sha256")
            or q2_digest != world_receipt.get("q2_parameter_sha256")
        ):
            raise V023CompositionRuntimeError("replayed Q1/Q2 parameters disagree with source")
        model_digest = source._model_digest(q1, q2, auth["q1_receipt"], auth["q2_receipt"])
        record = v018._V015._V013.read_prereg(prereg)
        temporary = tempfile.TemporaryDirectory(prefix="mcrl-v023-composition-tle-")
        try:
            archive = v018._V015._V013.screen._frozen_archive(
                record, tle_root, Path(temporary.name) / "frozen-tle"
            )
            receipt = v018._V015._V013.screen.assert_ephemeris_matches_record(record, archive=archive)
            if not isinstance(receipt, Mapping):
                raise V023CompositionRuntimeError("ephemeris validator returned no receipt")
            environment = v018._V015._V013.screen._make_environment(archive, users=v018.USERS)
            step_env = environment.environment
            world_field = source.KeyedFadingField.from_components(FIELD_COMPONENT, request.world)
            if world_field.root_digest != request.field_root_sha256:
                raise V023CompositionRuntimeError("reconstructed world field root disagrees")
            step_env._fading_field = world_field
            env_rng, mobility_rng, _action_rng, _control_rng = v018._V015._V013.screen._evaluation_rngs(
                request.world
            )
            _states, _masks, observation = environment.reset(env_rng, mobility_rng)
        except Exception:
            temporary.cleanup()
            raise
        self._source = source
        self._source_runtime = runtime
        self._v018 = v018
        self._q1 = q1
        self._q2 = q2
        self._environment = environment
        self._step_env = step_env
        self._env_rng = env_rng
        self._observation = observation
        self._model_digest = model_digest
        self._q1_sha256 = q1_digest
        self._q2_sha256 = q2_digest
        self._temporary = temporary
        self._field_root_sha256 = world_field.root_digest

    def _target_free_q12(self) -> dict[str, Any]:
        source = self._source
        v018 = self._v018
        step_env = self._step_env
        observation = self._observation
        if source is None or v018 is None or step_env is None or observation is None:
            raise V023CompositionRuntimeError("production replay is not initialized")
        if (
            self._network_digest(self._q1, name="Q1") != self._q1_sha256
            or self._network_digest(self._q2, name="Q2") != self._q2_sha256
        ):
            raise V023CompositionRuntimeError("frozen Q1/Q2 changed before replay inference")
        native = v018._V015._V013.encode_ee_axis_state(step_env, observation)
        native.verify()
        provenance = getattr(observation, "observation_provenance", None)
        if provenance is None or provenance.verify() != provenance.content_digest:
            raise V023CompositionRuntimeError("native observation provenance is unavailable")
        masks = np.asarray(native.action_masks, dtype=np.bool_)
        with source.torch.no_grad():
            q1_values = np.asarray(v018._q1_values(self._q1, native.state_matrix, masks), dtype=np.float64)
            q1_reference = v018._V015.select_actions(
                q1_values,
                np.zeros_like(q1_values),
                np.zeros_like(q1_values),
                masks,
                include_c3=False,
            )
            anchor = v018.snapshot_ops3_anchor(step_env, observation)
            projection = v018.project_ops3_anchor(anchor)
            surfaces = v018.build_ops3_live_surfaces(anchor, projection, q1_reference)
            q2_state = v018._V015.encode_ee_axis_v014_q2_states(surfaces)
            q2_state.verify()
            q2_values = np.asarray(
                v018._q2_values(self._q2, q2_state.state_matrix, q2_state.action_masks),
                dtype=np.float64,
            )
        if not np.array_equal(q2_state.action_masks, masks):
            raise V023CompositionRuntimeError("Q2 inference mask differs from native mask")
        if q1_values.shape != masks.shape or q2_values.shape != masks.shape:
            raise V023CompositionRuntimeError("Q1/Q2 inference surface shape drifted")
        snapshot = source.DetachedQ12Snapshot(
            q1=np.asarray(q1_values, dtype=np.float32),
            q2=np.asarray(q2_values, dtype=np.float32),
            source_state_digest=native.state_sha256,
            native_observation_event_digest=provenance.content_digest,
            model_digest=self._model_digest,
        )
        background = source._masked_argmax(np.asarray(snapshot.q12, dtype=np.float64), masks)
        _required_power, opening = v018._current_required_power_and_opening(
            current_gain_linear=anchor.current_gain_linear,
            segment_start_gain_linear=anchor.segment_start_gain_linear,
            action_masks=masks,
        )
        if (
            self._network_digest(self._q1, name="Q1") != self._q1_sha256
            or self._network_digest(self._q2, name="Q2") != self._q2_sha256
        ):
            raise V023CompositionRuntimeError("replay inference mutated frozen Q1/Q2")
        return {
            "snapshot": snapshot,
            "q1": np.asarray(snapshot.q1, dtype=np.float32),
            "q2": np.asarray(snapshot.q2, dtype=np.float32),
            "masks": masks,
            "background": np.asarray(background, dtype=np.int64),
            "opening": np.asarray(opening, dtype=np.bool_),
        }

    def _advance_once(self, background: np.ndarray) -> None:
        assert self._environment is not None and self._env_rng is not None
        outcome = self._environment.step(background, self._env_rng)
        if outcome.done:
            raise V023CompositionRuntimeError("replay episode terminated before phase 9")
        self._observation = _step_result_observation(self._environment, outcome)

    def _bind_source_anchor_entry(self, request: object) -> None:
        if self._source_index is None:
            raise V023CompositionRuntimeError("authenticated source index is unavailable")
        anchors = self._source_index.get("anchors")
        if not isinstance(anchors, list) or len(anchors) != len(PHASES):
            raise V023CompositionRuntimeError("source index does not declare phases 1..9")
        entry = anchors[request.phase - 1]
        topology = entry.get("topology") if isinstance(entry, Mapping) else None
        if not isinstance(entry, Mapping) or not isinstance(topology, Mapping):
            raise V023CompositionRuntimeError("source anchor declaration is malformed")
        checks = {
            "phase": entry.get("phase"),
            "anchor_id": entry.get("anchor_id"),
            "predecision_sha256": entry.get("predecision_sha256"),
            "state_schema_sha256": entry.get("state_schema_sha256"),
            "state_sha256": entry.get("state_sha256"),
            "q12_snapshot_sha256": entry.get("q12_snapshot_sha256"),
            "q12_model_sha256": entry.get("q12_model_sha256"),
            "q12_source_state_sha256": entry.get("q12_source_state_sha256"),
            "q12_event_sha256": entry.get("q12_event_sha256"),
            "topology_sha256": topology.get("content_digest"),
            "reference_actions_sha256": entry.get("reference_actions_sha256"),
        }
        mismatched = [name for name, declared in checks.items() if declared != getattr(request, name)]
        if mismatched:
            raise V023CompositionRuntimeError(
                "replay request disagrees with authenticated source index: "
                + ", ".join(mismatched)
            )

    def replay_anchor(self, request: object) -> ReplayMaterial:
        if self._source is None:
            self._initialize(request)
        self._bind_source_anchor_entry(request)
        if request.phase != self._last_phase + 1:
            raise V023CompositionRuntimeError("production backend replay phase is not sequential")
        if self._last_phase == 0:
            if int(self._observation.step_index) != 0:
                raise V023CompositionRuntimeError("replay reset did not begin at phase 0")
            initial = self._target_free_q12()
            self._advance_once(initial["background"])
        else:
            if self._last_background is None:
                raise V023CompositionRuntimeError("prior Q1+Q2 trajectory action is missing")
            self._advance_once(self._last_background)
        if int(self._observation.step_index) != request.phase:
            raise V023CompositionRuntimeError("replay observation phase drifted")
        assert self._source is not None and self._v018 is not None
        assert self._environment is not None and self._env_rng is not None
        live_before = str(
            self._source._live_digest(self._v018, self._environment, self._env_rng)
        )
        rng_before = str(
            self._source._rng_digest(copy.deepcopy(self._env_rng.bit_generator.state))
        )
        anchor_data = self._target_free_q12()
        assert self._step_env is not None
        capture = self._source.capture_lcsrs_c3_predecision(
            self._step_env,
            self._observation,
            world_id=request.world,
            anchor_id=request.anchor_id,
            detached_q12=anchor_data["snapshot"],
            reference_actions=anchor_data["background"],
            opening_feasibility_surface=anchor_data["opening"],
        )
        capture.verify()
        live_after = str(
            self._source._live_digest(self._v018, self._environment, self._env_rng)
        )
        rng_after = str(
            self._source._rng_digest(copy.deepcopy(self._env_rng.bit_generator.state))
        )
        if live_after != live_before or rng_after != rng_before:
            raise V023CompositionRuntimeError("replay inference/capture mutated world state or RNG")
        self._last_background = np.array(anchor_data["background"], dtype=np.int64, copy=True)
        self._last_background.setflags(write=False)
        self._last_phase = request.phase
        return ReplayMaterial(
            capture=capture,
            q1=anchor_data["q1"],
            q2=anchor_data["q2"],
            action_mask=anchor_data["masks"],
            reference_actions=anchor_data["background"],
            backend_anchor=(request.world, request.phase, request.anchor_id),
            preflight_manifest_sha256=request.preflight_manifest_sha256,
            source_manifest_sha256=request.source_manifest_sha256,
            source_index_sha256=request.source_index_sha256,
            field_root_sha256=request.field_root_sha256,
            target_free_inference=True,
        )

    def _network_digest(self, network: object, *, name: str) -> str:
        assert self._v018 is not None
        try:
            return _sha256(
                str(self._v018._V015._q_parameter_sha256(network)),
                field=f"live {name} parameters",
            )
        except Exception as error:
            raise V023CompositionRuntimeError(f"cannot digest frozen {name} parameters") from error

    def evaluate_draw(
        self,
        material: ReplayMaterial,
        actions: np.ndarray,
        draw_index: int,
    ) -> DrawMeasurement:
        if (
            self._source is None
            or self._source_runtime is None
            or self._v018 is None
            or self._environment is None
            or self._step_env is None
            or self._env_rng is None
        ):
            raise V023CompositionRuntimeError("physical backend is not initialized")
        if material.backend_anchor != (self._spec.held_out_world, self._last_phase, f"w{self._spec.held_out_world}:t{self._last_phase}"):
            raise V023CompositionRuntimeError("physical backend anchor token drifted")
        immutable_actions = np.array(actions, dtype=np.int64, copy=True)
        immutable_actions.setflags(write=False)
        action_digest = _action_sha256(immutable_actions)
        field = self._source_runtime._make_draw_field(
            self._spec.held_out_world,
            f"w{self._spec.held_out_world}:t{self._last_phase}",
            draw_index,
        )
        field_before = _sha256(field.root_digest, field="matched field root")
        original_field = getattr(self._step_env, "_fading_field", None)
        rng_state_before = copy.deepcopy(self._env_rng.bit_generator.state)
        before = {
            "environment": str(self._source._live_digest(self._v018, self._environment, self._env_rng)),
            "rng": str(self._source._rng_digest(rng_state_before)),
            "q1": self._network_digest(self._q1, name="Q1"),
            "q2": self._network_digest(self._q2, name="Q2"),
            # The callback API does not carry the fitted object.  This column
            # binds the server-authenticated logical Q3 digest; the adapter
            # independently hashes the actual fitted object before/after Q3
            # inference and again after all physical callbacks.
            "q3": _sha256(self._q3_sha256, field="authenticated fitted Q3"),
            "matched_field": field_before,
        }
        evaluation: object
        try:
            self._step_env._fading_field = field
            evaluation = self._step_env.evaluate_actions(immutable_actions, self._env_rng)
        finally:
            self._step_env._fading_field = original_field
        rng_state_after = copy.deepcopy(self._env_rng.bit_generator.state)
        after = {
            "environment": str(self._source._live_digest(self._v018, self._environment, self._env_rng)),
            "rng": str(self._source._rng_digest(rng_state_after)),
            "q1": self._network_digest(self._q1, name="Q1"),
            "q2": self._network_digest(self._q2, name="Q2"),
            "q3": _sha256(self._q3_sha256, field="authenticated fitted Q3"),
            "matched_field": _sha256(field.root_digest, field="matched field root"),
        }
        if (
            before != after
            or getattr(self._step_env, "_fading_field", None) is not original_field
            or _action_sha256(immutable_actions) != action_digest
        ):
            raise V023CompositionRuntimeError("physical simulator call mutated a frozen input")
        interval_s = float(self._step_env.driver.config.ephemeris.time_step_s)
        record = self._source._evaluation_record(
            evaluation,
            actions=immutable_actions,
            interval_s=interval_s,
        )
        return DrawMeasurement(
            draw_index=draw_index,
            action_sha256=action_digest,
            common_field_sha256=field_before,
            per_user_bits=np.asarray(record["per_user_bits"], dtype=np.float64),
            energy_j=float(record["energy_j"]),
            served=np.asarray(record["served"], dtype=np.bool_),
            active_beam_keys=np.asarray(record["active_beam_keys"], dtype=np.int64).reshape(-1, 2),
            active_satellites=np.asarray(record["active_satellites"], dtype=np.int64),
            beam_power_w=np.asarray(record["beam_power_w"], dtype=np.float64),
            nonmutation_before=before,
            nonmutation_after=after,
        )


def build_runtime(
    *,
    spec: object,
    adapter: ModuleType,
    backend_factory: Callable[[object], object] | None = None,
) -> V023CompositionRuntime:
    """Build the exact callbacks expected by the composition server.

    ``backend_factory`` exists only as a narrow non-heavy test seam.  The
    server supplies no such argument and therefore receives the lazy,
    authenticated production backend.
    """

    backend = (
        _ProductionBackend(spec, adapter)
        if backend_factory is None
        else backend_factory(spec)
    )
    return V023CompositionRuntime(spec=spec, adapter=adapter, backend=backend)


__all__ = [
    "DrawMeasurement",
    "ReplayMaterial",
    "V023CompositionRuntime",
    "V023CompositionRuntimeError",
    "build_runtime",
]
