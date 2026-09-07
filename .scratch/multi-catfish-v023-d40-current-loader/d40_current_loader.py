"""Fail-closed PLUMBING_ONLY adapter for the authenticated D40 checkpoint.

The D40 file is a V0.20 *split* checkpoint.  Its Q1 and Q2 payloads are not
assumed to have the current V0.23 architecture: the payload is inspected first
and every target parameter key, shape, dtype, and relevant configuration field
is checked before either current head is mutated.

This module never converts scientific values, trains, evaluates, opens TEST,
starts a simulator, or labels a result as a trained five-arm policy.  The real
D40 file currently fails the exact-compatibility check; callers receive a
field-level report and no model is returned.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
from typing import Any

import torch

from mcrl.algorithms.ee_axis_action_shared import (
    ACTION_ALIGNED_FEATURES,
    ACTION_SHARED_ALGORITHM,
    GLOBAL_FEATURES,
    ActionSharedQNetwork,
    EEAxisActionSharedConfig,
)
from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3QNetwork
from mcrl.algorithms.ee_axis_lcsrs_three_route import (
    EEAxisLCSRSThreeRoute,
    LCSRSThreeRouteConfig,
)


PLUMBING_ONLY = "PLUMBING_ONLY"
NON_EVALUABLE = "NON_EVALUABLE"
NON_GATE_BOUND = "NON_GATE_BOUND"
D40_ADAPTER_SCHEMA = "multi-catfish-mcrl-v023-d40-current-loader-v1"
PLUMBING_CHECKPOINT_SCHEMA = (
    "multi-catfish-mcrl-v023-d40-plumbing-only-current-three-route-checkpoint-v1"
)

D40_CHECKPOINT_RELATIVE_PATH = Path(
    ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/"
    "lineage-2026092101/checkpoints/"
    "lineage-2026092101-q2init-2026108101-rung-003000.pt"
)
REPO_ROOT = Path(__file__).resolve().parents[2]
D40_CHECKPOINT_PATH = REPO_ROOT / D40_CHECKPOINT_RELATIVE_PATH
D40_CHECKPOINT_SHA256 = (
    "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc"
)
D40_CHECKPOINT_SCHEMA = (
    "multi-catfish-mcrl-v020-repriced-q1-q2-source-fit-v1-checkpoint"
)
D40_CLAIM_CEILING = "SOURCE_ONLY_NO_SIMULATOR_NO_TEST_NO_EPISODE_EE"
D40_LINEAGE = 2026092101
D40_Q2_INITIALIZATION = 2026108101
D40_Q1_UPDATE_COUNT = 10
D40_Q2_UPDATE_COUNT = 3000
D40_Q1_HEAD_INDEX = 0
D40_STATE_DIM = 112
D40_Q1_STATE_DIM = 228
D40_Q2_STATE_DIM = 448
D40_ACTION_DIM = 28
D40_Q1_ALGORITHM = (
    "multi-catfish-mcrl-ee-axis-v03-action-shared-masked-meanmax"
)
D40_Q2_ALGORITHM = "multi-catfish-mcrl-v014-independent-action-set-head"


class D40AdapterError(RuntimeError):
    """Base class for a rejected D40/current-model boundary."""


class D40DigestMismatchError(D40AdapterError):
    """The source bytes are not the authenticated D40 checkpoint."""


class D40MalformedCheckpointError(D40AdapterError):
    """The authenticated bytes do not carry the required V0.20 split shape."""


class D40LegacyQ3Error(D40MalformedCheckpointError):
    """A legacy Q3 payload was found in a Q1/Q2-only source checkpoint."""


class D40ModeError(D40AdapterError):
    """The caller requested a mode other than the narrow plumbing lane."""


class D40PolicyLabelError(D40AdapterError):
    """The caller attempted to assign a forbidden trained-policy label."""


class D40PartialLoadError(D40AdapterError):
    """A transactional parameter load failed or changed an off-target head."""


@dataclass(frozen=True)
class FieldIncompatibility:
    """One exact source/target mismatch, retaining field-level provenance."""

    field: str
    expected: str
    actual: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {
            "field": self.field,
            "expected": self.expected,
            "actual": self.actual,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class D40CompatibilityReport:
    """Machine-readable compatibility result produced before any load."""

    checkpoint_sha256: str
    source_schema: str
    target_type: str
    mismatches: tuple[FieldIncompatibility, ...]

    @property
    def compatible(self) -> bool:
        return not self.mismatches

    def as_dict(self) -> dict[str, object]:
        return {
            "checkpoint_sha256": self.checkpoint_sha256,
            "source_schema": self.source_schema,
            "target_type": self.target_type,
            "compatible": self.compatible,
            "mismatches": [item.as_dict() for item in self.mismatches],
        }

    def format(self) -> str:
        lines = [
            "D40/current exact compatibility failed; no tensors were loaded.",
            f"checkpoint_sha256={self.checkpoint_sha256}",
        ]
        for mismatch in self.mismatches:
            lines.append(
                f"- {mismatch.field}: expected {mismatch.expected}; "
                f"actual {mismatch.actual} ({mismatch.reason})"
            )
        return "\n".join(lines)


class D40CompatibilityError(D40AdapterError):
    """The source is authenticated but cannot be loaded exactly."""

    def __init__(self, report: D40CompatibilityReport) -> None:
        self.report = report
        super().__init__(report.format())


@dataclass(frozen=True)
class PlumbingOnlyReceipt:
    """Non-evaluable provenance attached to a successfully loaded model."""

    schema: str
    use_mode: str
    evaluability: str
    gate_binding: str
    trained_five_arm_policy: bool
    checkpoint_sha256: str
    checkpoint_path: str
    q3_initialization_seed: int
    q3_initialization: str
    loaded_source_fields: tuple[str, ...]
    loaded_parameter_fields: tuple[str, ...]
    optimizer_state_loaded: bool
    test_split_opened: bool
    episode_training: bool
    simulator_run: bool
    claim_ceiling: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class LoadedPlumbingOnlyModel:
    """A current model plus an explicit non-evaluable status receipt."""

    model: EEAxisLCSRSThreeRoute
    receipt: PlumbingOnlyReceipt


@dataclass(frozen=True)
class _D40Source:
    payload: Mapping[str, Any]
    checkpoint_sha256: str
    q1_config: Mapping[str, Any]
    q2_config: Mapping[str, Any]
    q1_algorithm: str
    q2_algorithm: str
    q1_state: Mapping[str, torch.Tensor]
    q2_state: Mapping[str, torch.Tensor]
    inspection: Mapping[str, object]


_MISSING = object()
_LEGACY_Q3_KEYS = {
    "q3",
    "q3_head",
    "q3_model",
    "q3_network",
    "q3_networks",
    "q3_optimizer",
    "q3_state",
}


def _display(value: object) -> str:
    return repr(value)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _require_expected_digest(value: object, *, field: str) -> str:
    if not _is_sha256(value):
        raise D40DigestMismatchError(f"{field} must be a lowercase SHA-256 digest")
    if value != D40_CHECKPOINT_SHA256:
        raise D40DigestMismatchError(
            f"{field} is not the authenticated D40 digest: expected "
            f"{D40_CHECKPOINT_SHA256}, got {value}"
        )
    return value


def _sha256_file(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise D40AdapterError(f"expected a regular checkpoint file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _reject_legacy_q3(value: object, *, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if isinstance(key, str) and key.casefold() in _LEGACY_Q3_KEYS:
                raise D40LegacyQ3Error(f"legacy Q3 field is forbidden: {child_path}")
            _reject_legacy_q3(child, path=child_path)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_legacy_q3(child, path=f"{path}[{index}]")


def _require_mapping(value: object, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise D40MalformedCheckpointError(f"{field} must be a mapping")
    return value  # type: ignore[return-value]


def _required(mapping: Mapping[str, Any], field: str, *, where: str) -> Any:
    value = mapping.get(field, _MISSING)
    if value is _MISSING:
        raise D40MalformedCheckpointError(f"missing required field {where}.{field}")
    return value


def _require_exact(
    mapping: Mapping[str, Any], field: str, expected: object, *, where: str
) -> Any:
    actual = _required(mapping, field, where=where)
    if type(actual) is not type(expected) or actual != expected:
        raise D40MalformedCheckpointError(
            f"{where}.{field} drifted: expected {_display(expected)}, "
            f"got {_display(actual)}"
        )
    return actual


def _validate_hidden_layers(value: object, *, field: str) -> None:
    if (
        isinstance(value, (str, bytes))
        or not isinstance(value, Sequence)
        or not value
        or any(isinstance(width, bool) or not isinstance(width, int) or width < 1 for width in value)
    ):
        raise D40MalformedCheckpointError(f"{field} is not a positive hidden-layer sequence")


def _validate_state_dict(
    value: object, *, field: str
) -> Mapping[str, torch.Tensor]:
    state = _require_mapping(value, field=field)
    if not state:
        raise D40MalformedCheckpointError(f"{field} is empty")
    result: dict[str, torch.Tensor] = {}
    for name, tensor in state.items():
        if not isinstance(name, str) or not name:
            raise D40MalformedCheckpointError(f"{field} contains a non-string key")
        if not isinstance(tensor, torch.Tensor):
            raise D40MalformedCheckpointError(
                f"{field}.{name} is not a torch tensor"
            )
        if not (tensor.is_floating_point() or tensor.is_complex()):
            raise D40MalformedCheckpointError(
                f"{field}.{name} is not a floating/complex parameter tensor"
            )
        if not bool(torch.isfinite(tensor).all()):
            raise D40MalformedCheckpointError(f"{field}.{name} is non-finite")
        result[name] = tensor
    return result


def _state_summary(state: Mapping[str, torch.Tensor]) -> list[dict[str, object]]:
    return [
        {
            "key": name,
            "shape": list(int(extent) for extent in state[name].shape),
            "dtype": str(state[name].dtype),
        }
        for name in sorted(state)
    ]


def _validate_d40_payload(
    payload: object, *, checkpoint_sha256: str
) -> _D40Source:
    digest = _require_expected_digest(checkpoint_sha256, field="checkpoint_sha256")
    root = _require_mapping(payload, field="checkpoint root")
    _reject_legacy_q3(root)

    _require_exact(root, "schema", D40_CHECKPOINT_SCHEMA, where="root")
    _require_exact(root, "claim_ceiling", D40_CLAIM_CEILING, where="root")
    _require_exact(root, "lineage", D40_LINEAGE, where="root")
    _require_exact(root, "q2_initialization", D40_Q2_INITIALIZATION, where="root")
    _require_exact(root, "q1_update_count", D40_Q1_UPDATE_COUNT, where="root")
    _require_exact(root, "q2_update_count", D40_Q2_UPDATE_COUNT, where="root")
    _require_exact(root, "q1_head_index", D40_Q1_HEAD_INDEX, where="root")
    for field in ("test_split_opened", "simulator_run", "episode_training"):
        _require_exact(root, field, False, where="root")
    authority = _required(root, "authority_sha256", where="root")
    if not _is_sha256(authority):
        raise D40MalformedCheckpointError("root.authority_sha256 is not a SHA-256 digest")

    q1 = _require_mapping(_required(root, "q1", where="root"), field="root.q1")
    q2 = _require_mapping(_required(root, "q2", where="root"), field="root.q2")

    _require_exact(q1, "algorithm", D40_Q1_ALGORITHM, where="root.q1")
    _require_exact(q1, "format_version", 1, where="root.q1")
    _require_exact(q1, "train_seed", D40_LINEAGE, where="root.q1")
    _require_exact(q1, "update_count", D40_Q1_UPDATE_COUNT, where="root.q1")
    q1_config = _require_mapping(
        _required(q1, "config", where="root.q1"), field="root.q1.config"
    )
    for field in (
        "state_dim",
        "action_dim",
        "hidden_layers",
        "activation",
        "learning_rate",
        "kappa_bits",
        "beta",
        "loss_weights",
    ):
        _required(q1_config, field, where="root.q1.config")
    _require_exact(q1_config, "state_dim", D40_Q1_STATE_DIM, where="root.q1.config")
    _require_exact(q1_config, "action_dim", D40_ACTION_DIM, where="root.q1.config")
    _validate_hidden_layers(q1_config["hidden_layers"], field="root.q1.config.hidden_layers")

    q1_networks_value = _required(q1, "q_networks", where="root.q1")
    if (
        isinstance(q1_networks_value, (str, bytes))
        or not isinstance(q1_networks_value, Sequence)
        or len(q1_networks_value) != 3
    ):
        raise D40MalformedCheckpointError(
            "root.q1.q_networks must contain exactly three source networks"
        )
    q1_networks = tuple(
        _validate_state_dict(item, field=f"root.q1.q_networks[{index}]")
        for index, item in enumerate(q1_networks_value)
    )
    q1_state = q1_networks[D40_Q1_HEAD_INDEX]

    _require_exact(q2, "algorithm", D40_Q2_ALGORITHM, where="root.q2")
    _require_exact(q2, "format_version", 1, where="root.q2")
    _require_exact(q2, "train_seed", D40_Q2_INITIALIZATION, where="root.q2")
    _require_exact(q2, "update_count", D40_Q2_UPDATE_COUNT, where="root.q2")
    q2_config = _require_mapping(
        _required(q2, "config", where="root.q2"), field="root.q2.config"
    )
    for field in (
        "action_dim",
        "local_feature_dim",
        "global_feature_dim",
        "hidden_layers",
        "activation",
        "learning_rate",
        "kappa_bits",
        "beta",
    ):
        _required(q2_config, field, where="root.q2.config")
    _require_exact(q2_config, "action_dim", D40_ACTION_DIM, where="root.q2.config")
    _require_exact(q2_config, "local_feature_dim", 16, where="root.q2.config")
    _require_exact(q2_config, "global_feature_dim", 0, where="root.q2.config")
    _validate_hidden_layers(q2_config["hidden_layers"], field="root.q2.config.hidden_layers")
    q2_state = _validate_state_dict(
        _required(q2, "q", where="root.q2"), field="root.q2.q"
    )

    inspection: dict[str, object] = {
        "schema": D40_ADAPTER_SCHEMA,
        "checkpoint_schema": D40_CHECKPOINT_SCHEMA,
        "checkpoint_sha256": digest,
        "source_split": "V0.20",
        "legacy_q3_present": False,
        "q1": {
            "source_field": "q1.q_networks[0]",
            "algorithm": q1["algorithm"],
            "head_index": D40_Q1_HEAD_INDEX,
            "network_count": len(q1_networks),
            "config": dict(q1_config),
            "state_dict": _state_summary(q1_state),
        },
        "q2": {
            "source_field": "q2.q",
            "algorithm": q2["algorithm"],
            "config": dict(q2_config),
            "state_dict": _state_summary(q2_state),
        },
        "loaded_source_fields": ["q1.q_networks[0]", "q2.q"],
        "optimizer_state_loaded": False,
    }
    return _D40Source(
        payload=root,
        checkpoint_sha256=digest,
        q1_config=q1_config,
        q2_config=q2_config,
        q1_algorithm=q1["algorithm"],
        q2_algorithm=q2["algorithm"],
        q1_state=q1_state,
        q2_state=q2_state,
        inspection=inspection,
    )


def _read_authenticated_d40(path: Path) -> _D40Source:
    source = Path(path)
    actual = _sha256_file(source)
    if actual != D40_CHECKPOINT_SHA256:
        raise D40DigestMismatchError(
            f"D40 checkpoint hash mismatch: expected {D40_CHECKPOINT_SHA256}, "
            f"got {actual}"
        )
    try:
        payload = torch.load(source, map_location="cpu", weights_only=True)
    except Exception as error:  # pragma: no cover - exact torch I/O is environment-specific
        raise D40MalformedCheckpointError("authenticated D40 checkpoint is unreadable") from error
    return _validate_d40_payload(payload, checkpoint_sha256=actual)


def inspect_authenticated_d40_payload(
    payload: object, *, checkpoint_sha256: str = D40_CHECKPOINT_SHA256
) -> dict[str, object]:
    """Validate an already-read payload for tests/read-only inspection only."""

    source = _validate_d40_payload(
        payload, checkpoint_sha256=_require_expected_digest(
            checkpoint_sha256, field="checkpoint_sha256"
        )
    )
    return deepcopy(dict(source.inspection))


def inspect_d40_checkpoint(
    path: Path = D40_CHECKPOINT_PATH,
) -> dict[str, object]:
    """Read and authenticate D40, then report its actual split payload."""

    return deepcopy(dict(_read_authenticated_d40(Path(path)).inspection))


def _validate_current_model(model: object) -> EEAxisLCSRSThreeRoute:
    if not isinstance(model, EEAxisLCSRSThreeRoute):
        raise TypeError("model must be the current EEAxisLCSRSThreeRoute")
    if not isinstance(model.config, LCSRSThreeRouteConfig):
        raise D40AdapterError("current model lacks LCSRSThreeRouteConfig")
    if not isinstance(model.config.q12, EEAxisActionSharedConfig):
        raise D40AdapterError("current model lacks the action-shared Q1/Q2 config")
    if len(model.q_networks) != 3 or len(model.optimizers) != 3:
        raise D40AdapterError("current model must contain exactly three heads/optimizers")
    if not isinstance(model.q1, ActionSharedQNetwork) or not isinstance(
        model.q2, ActionSharedQNetwork
    ):
        raise D40AdapterError("current Q1/Q2 heads must be ActionSharedQNetwork")
    if not isinstance(model.q3, LCSRSC3QNetwork):
        raise D40AdapterError("current Q3 head must be LCSRSC3QNetwork")
    if isinstance(model.train_seed, bool) or not isinstance(model.train_seed, int):
        raise D40AdapterError("current model train_seed must be an integer")
    return model


def _state_dict_mismatches(
    source: Mapping[str, torch.Tensor],
    target: Mapping[str, torch.Tensor],
    *,
    source_prefix: str,
    target_prefix: str,
) -> list[FieldIncompatibility]:
    mismatches: list[FieldIncompatibility] = []
    source_keys = set(source)
    target_keys = set(target)
    for name in sorted(target_keys - source_keys):
        mismatches.append(
            FieldIncompatibility(
                field=f"{source_prefix}.{name}",
                expected=f"present as {target_prefix}.{name}",
                actual="missing",
                reason="missing parameter key",
            )
        )
    for name in sorted(source_keys - target_keys):
        mismatches.append(
            FieldIncompatibility(
                field=f"{source_prefix}.{name}",
                expected="absent from the current head",
                actual="present",
                reason="unexpected parameter key",
            )
        )
    for name in sorted(source_keys & target_keys):
        source_tensor = source[name]
        target_tensor = target[name]
        if tuple(source_tensor.shape) != tuple(target_tensor.shape):
            mismatches.append(
                FieldIncompatibility(
                    field=f"{source_prefix}.{name}",
                    expected=f"shape={tuple(target_tensor.shape)} in {target_prefix}.{name}",
                    actual=f"shape={tuple(source_tensor.shape)}",
                    reason="parameter shape is incompatible; no reshape is allowed",
                )
            )
        if source_tensor.dtype != target_tensor.dtype:
            mismatches.append(
                FieldIncompatibility(
                    field=f"{source_prefix}.{name}.dtype",
                    expected=f"{target_tensor.dtype}",
                    actual=f"{source_tensor.dtype}",
                    reason="parameter dtype differs; no value conversion is allowed",
                )
            )
    return mismatches


def _first_scorer_input_width(state: Mapping[str, torch.Tensor]) -> int | None:
    tensor = state.get("scorer.0.weight")
    if tensor is None or tensor.ndim != 2:
        return None
    return int(tensor.shape[1])


def _mapping_mismatches(
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    *,
    prefix: str,
) -> list[FieldIncompatibility]:
    mismatches: list[FieldIncompatibility] = []
    for field in sorted(set(source) | set(target)):
        expected = target.get(field, _MISSING)
        actual = source.get(field, _MISSING)
        if expected is _MISSING:
            mismatches.append(
                FieldIncompatibility(
                    field=f"{prefix}.{field}",
                    expected="not present in the current configuration",
                    actual=_display(actual),
                    reason="source configuration carries an unconsumed field",
                )
            )
        elif actual is _MISSING or type(actual) is not type(expected) or actual != expected:
            mismatches.append(
                FieldIncompatibility(
                    field=f"{prefix}.{field}",
                    expected=_display(expected),
                    actual="missing" if actual is _MISSING else _display(actual),
                    reason="configuration value is not exactly equal",
                )
            )
    return mismatches


def _compatibility_report(
    model: EEAxisLCSRSThreeRoute,
    source: _D40Source,
) -> D40CompatibilityReport:
    mismatches: list[FieldIncompatibility] = []
    if source.q1_algorithm != ACTION_SHARED_ALGORITHM:
        mismatches.append(
            FieldIncompatibility(
                field="q1.algorithm",
                expected=repr(ACTION_SHARED_ALGORITHM),
                actual=repr(source.q1_algorithm),
                reason="current Q1 is an ActionSharedQNetwork, not masked mean/max",
            )
        )
    if source.q2_algorithm != ACTION_SHARED_ALGORITHM:
        mismatches.append(
            FieldIncompatibility(
                field="q2.algorithm",
                expected=repr(ACTION_SHARED_ALGORITHM),
                actual=repr(source.q2_algorithm),
                reason="current Q2 is an ActionSharedQNetwork, not a V0.14 head",
            )
        )

    current_config = asdict(model.config.q12)
    mismatches.extend(
        _mapping_mismatches(
            source.q1_config,
            current_config,
            prefix="q1.config",
        )
    )
    for field in (
        "action_dim",
        "hidden_layers",
        "activation",
        "learning_rate",
        "kappa_bits",
        "beta",
    ):
        source_value = source.q2_config.get(field, _MISSING)
        target_value = current_config.get(field, _MISSING)
        if (
            source_value is _MISSING
            or target_value is _MISSING
            or type(source_value) is not type(target_value)
            or source_value != target_value
        ):
            mismatches.append(
                FieldIncompatibility(
                    field=f"q2.config.{field}",
                    expected="missing" if target_value is _MISSING else _display(target_value),
                    actual="missing" if source_value is _MISSING else _display(source_value),
                    reason="shared configuration value is not exactly equal",
                )
            )

    target_input_width = ACTION_ALIGNED_FEATURES + GLOBAL_FEATURES
    q1_input_width = _first_scorer_input_width(source.q1_state)
    if q1_input_width is not None and q1_input_width != target_input_width:
        mismatches.append(
            FieldIncompatibility(
                field="q1.architecture.scorer_input_width",
                expected=f"{target_input_width} (current ActionSharedQNetwork)",
                actual=f"{q1_input_width} (D40 masked-mean/max scorer)",
                reason="architecture differs even though the outer state width is 228",
            )
        )
    q2_input_width = _first_scorer_input_width(source.q2_state)
    if q2_input_width is not None and q2_input_width != target_input_width:
        mismatches.append(
            FieldIncompatibility(
                field="q2.architecture.scorer_input_width",
                expected=f"{target_input_width} (current ActionSharedQNetwork)",
                actual=f"{q2_input_width} (D40 V0.14 action-set scorer)",
                reason="current Q2 does not consume the V0.14 local/global feature contract",
            )
        )
    mismatches.extend(
        _state_dict_mismatches(
            source.q1_state,
            model.q1.state_dict(),
            source_prefix="q1.q_networks[0]",
            target_prefix="q1",
        )
    )
    mismatches.extend(
        _state_dict_mismatches(
            source.q2_state,
            model.q2.state_dict(),
            source_prefix="q2.q",
            target_prefix="q2",
        )
    )
    return D40CompatibilityReport(
        checkpoint_sha256=source.checkpoint_sha256,
        source_schema=D40_CHECKPOINT_SCHEMA,
        target_type=type(model).__name__,
        mismatches=tuple(mismatches),
    )


def _clone_state_dict(state: Mapping[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    return {name: tensor.detach().clone() for name, tensor in state.items()}


def _restore_heads(
    model: EEAxisLCSRSThreeRoute,
    q1_before: Mapping[str, torch.Tensor],
    q2_before: Mapping[str, torch.Tensor],
) -> None:
    model.q1.load_state_dict(q1_before, strict=True)
    model.q2.load_state_dict(q2_before, strict=True)


def _transactional_q12_load(
    model: EEAxisLCSRSThreeRoute,
    q1_state: Mapping[str, torch.Tensor],
    q2_state: Mapping[str, torch.Tensor],
) -> tuple[str, ...]:
    q1_before = _clone_state_dict(model.q1.state_dict())
    q2_before = _clone_state_dict(model.q2.state_dict())
    q3_before = _clone_state_dict(model.q3.state_dict())
    try:
        model.q1.load_state_dict(q1_state, strict=True)
        model.q2.load_state_dict(q2_state, strict=True)
        for name, tensor in q1_state.items():
            if not torch.equal(model.q1.state_dict()[name], tensor):
                raise D40PartialLoadError(f"post-load Q1 tensor mismatch at {name}")
        for name, tensor in q2_state.items():
            if not torch.equal(model.q2.state_dict()[name], tensor):
                raise D40PartialLoadError(f"post-load Q2 tensor mismatch at {name}")
        for name, tensor in q3_before.items():
            if not torch.equal(model.q3.state_dict()[name], tensor):
                raise D40PartialLoadError(
                    f"Q3 changed during a Q1/Q2-only load at {name}"
                )
    except Exception as error:
        try:
            _restore_heads(model, q1_before, q2_before)
        except Exception as rollback_error:  # pragma: no cover - catastrophic state failure
            raise D40PartialLoadError(
                "Q1/Q2 load failed and rollback also failed"
            ) from rollback_error
        if isinstance(error, D40PartialLoadError):
            raise
        raise D40PartialLoadError(
            "Q1/Q2 load failed; all target heads were rolled back"
        ) from error
    return tuple(
        [f"q1.{name}" for name in sorted(q1_state)]
        + [f"q2.{name}" for name in sorted(q2_state)]
    )


def load_exact_compatible_q12_parameters(
    model: EEAxisLCSRSThreeRoute,
    *,
    q1_state: Mapping[str, torch.Tensor],
    q2_state: Mapping[str, torch.Tensor],
) -> tuple[str, ...]:
    """Load two already-selected current-format state dicts transactionally.

    This narrow structural helper is used by tests to prove the actual current
    class copies exact tensors.  It does not authenticate a D40 file; the
    public path is :func:`load_authenticated_d40_into_current_model`.
    """

    current = _validate_current_model(model)
    q1 = _validate_state_dict(q1_state, field="fixture.q1_state")
    q2 = _validate_state_dict(q2_state, field="fixture.q2_state")
    mismatches = _state_dict_mismatches(
        q1, current.q1.state_dict(), source_prefix="fixture.q1", target_prefix="q1"
    )
    mismatches.extend(
        _state_dict_mismatches(
            q2, current.q2.state_dict(), source_prefix="fixture.q2", target_prefix="q2"
        )
    )
    if mismatches:
        raise D40CompatibilityError(
            D40CompatibilityReport(
                checkpoint_sha256="structural-fixture-not-a-d40-checkpoint",
                source_schema="current-format-structural-fixture",
                target_type=type(current).__name__,
                mismatches=tuple(mismatches),
            )
        )
    return _transactional_q12_load(current, q1, q2)


def _validate_mode_and_label(
    *, use_mode: str, output_label: str | None
) -> None:
    if use_mode != PLUMBING_ONLY:
        raise D40ModeError(f"only {PLUMBING_ONLY} is permitted, got {use_mode!r}")
    if output_label is None:
        return
    if not isinstance(output_label, str):
        raise D40PolicyLabelError("output_label must be a string when supplied")
    normalized = output_label.casefold().replace("_", " ").replace("–", "-")
    if (
        "policy" in normalized
        and "train" in normalized
        and (
            "five-arm" in normalized
            or "five arm" in normalized
            or "5-arm" in normalized
            or "5 arm" in normalized
        )
    ):
        raise D40PolicyLabelError(
            "PLUMBING_ONLY output cannot be labelled as a trained five-arm policy"
        )


def load_authenticated_d40_into_current_model(
    model: EEAxisLCSRSThreeRoute,
    *,
    checkpoint_path: Path = D40_CHECKPOINT_PATH,
    use_mode: str = PLUMBING_ONLY,
    output_label: str | None = None,
) -> PlumbingOnlyReceipt:
    """Authenticate D40, validate exact compatibility, then load Q1/Q2 only."""

    _validate_mode_and_label(use_mode=use_mode, output_label=output_label)
    current = _validate_current_model(model)
    source = _read_authenticated_d40(Path(checkpoint_path))
    report = _compatibility_report(current, source)
    if not report.compatible:
        raise D40CompatibilityError(report)
    loaded_fields = _transactional_q12_load(current, source.q1_state, source.q2_state)
    return PlumbingOnlyReceipt(
        schema=D40_ADAPTER_SCHEMA,
        use_mode=PLUMBING_ONLY,
        evaluability=NON_EVALUABLE,
        gate_binding=NON_GATE_BOUND,
        trained_five_arm_policy=False,
        checkpoint_sha256=source.checkpoint_sha256,
        checkpoint_path=str(Path(checkpoint_path).resolve()),
        q3_initialization_seed=current.train_seed,
        q3_initialization="EXPLICIT_DETERMINISTIC_SEED_ONLY",
        loaded_source_fields=("q1.q_networks[0]", "q2.q"),
        loaded_parameter_fields=loaded_fields,
        optimizer_state_loaded=False,
        test_split_opened=False,
        episode_training=False,
        simulator_run=False,
        claim_ceiling="PLUMBING_ONLY_NON_EVALUABLE_NON_GATE_BOUND",
    )


def build_plumbing_only_model(
    config: LCSRSThreeRouteConfig,
    *,
    q3_seed: int,
    checkpoint_path: Path = D40_CHECKPOINT_PATH,
    device: str = "cpu",
    use_mode: str = PLUMBING_ONLY,
    output_label: str | None = None,
) -> LoadedPlumbingOnlyModel:
    """Construct Q3 from an explicit seed and admit D40 only if exact."""

    _validate_mode_and_label(use_mode=use_mode, output_label=output_label)
    if isinstance(q3_seed, bool) or not isinstance(q3_seed, int):
        raise TypeError("q3_seed must be an integer explicitly supplied by the caller")
    model = EEAxisLCSRSThreeRoute(config, train_seed=q3_seed, device=device)
    receipt = load_authenticated_d40_into_current_model(
        model,
        checkpoint_path=checkpoint_path,
        use_mode=use_mode,
        output_label=output_label,
    )
    if receipt.q3_initialization_seed != q3_seed:
        raise D40PartialLoadError("Q3 initialization seed receipt drifted")
    return LoadedPlumbingOnlyModel(model=model, receipt=receipt)


def plumbing_checkpoint_state(
    loaded: LoadedPlumbingOnlyModel, *, update_count: int
) -> dict[str, object]:
    """Serialize the current model with its non-evaluable plumbing receipt."""

    if not isinstance(loaded, LoadedPlumbingOnlyModel):
        raise TypeError("loaded must be a LoadedPlumbingOnlyModel")
    return {
        "schema": PLUMBING_CHECKPOINT_SCHEMA,
        "use_mode": PLUMBING_ONLY,
        "evaluability": NON_EVALUABLE,
        "gate_binding": NON_GATE_BOUND,
        "trained_five_arm_policy": False,
        "receipt": loaded.receipt.as_dict(),
        "model": loaded.model.checkpoint_state(update_count=update_count),
    }


def load_plumbing_checkpoint_state(
    loaded: LoadedPlumbingOnlyModel, state: Mapping[str, object]
) -> int:
    """Resume an adapter envelope while preserving its status boundary."""

    if not isinstance(loaded, LoadedPlumbingOnlyModel):
        raise TypeError("loaded must be a LoadedPlumbingOnlyModel")
    if not isinstance(state, Mapping):
        raise D40MalformedCheckpointError("plumbing checkpoint root must be a mapping")
    if state.get("schema") != PLUMBING_CHECKPOINT_SCHEMA:
        raise D40MalformedCheckpointError("plumbing checkpoint schema mismatch")
    if state.get("use_mode") != PLUMBING_ONLY:
        raise D40ModeError("plumbing checkpoint is not PLUMBING_ONLY")
    if state.get("evaluability") != NON_EVALUABLE or state.get("gate_binding") != NON_GATE_BOUND:
        raise D40MalformedCheckpointError("plumbing checkpoint status boundary drifted")
    if state.get("trained_five_arm_policy") is not False:
        raise D40PolicyLabelError("plumbing checkpoint cannot be a trained five-arm policy")
    receipt = state.get("receipt")
    if receipt != loaded.receipt.as_dict():
        raise D40MalformedCheckpointError("plumbing checkpoint receipt mismatch")
    model_state = state.get("model")
    if not isinstance(model_state, Mapping):
        raise D40MalformedCheckpointError("plumbing checkpoint model payload is missing")

    before = deepcopy(loaded.model.checkpoint_state(update_count=0))
    try:
        return loaded.model.load_checkpoint_state(model_state)
    except Exception as error:
        try:
            loaded.model.load_checkpoint_state(before)
        except Exception as rollback_error:  # pragma: no cover - catastrophic state failure
            raise D40PartialLoadError(
                "model checkpoint load failed and rollback also failed"
            ) from rollback_error
        raise D40PartialLoadError(
            "model checkpoint load failed; current model was rolled back"
        ) from error


__all__ = [
    "D40_ADAPTER_SCHEMA",
    "D40_CHECKPOINT_PATH",
    "D40_CHECKPOINT_RELATIVE_PATH",
    "D40_CHECKPOINT_SCHEMA",
    "D40_CHECKPOINT_SHA256",
    "D40CompatibilityError",
    "D40CompatibilityReport",
    "D40AdapterError",
    "D40DigestMismatchError",
    "D40LegacyQ3Error",
    "D40MalformedCheckpointError",
    "D40ModeError",
    "D40PartialLoadError",
    "D40PolicyLabelError",
    "FieldIncompatibility",
    "LoadedPlumbingOnlyModel",
    "NON_EVALUABLE",
    "NON_GATE_BOUND",
    "PLUMBING_CHECKPOINT_SCHEMA",
    "PLUMBING_ONLY",
    "PlumbingOnlyReceipt",
    "build_plumbing_only_model",
    "inspect_authenticated_d40_payload",
    "inspect_d40_checkpoint",
    "load_authenticated_d40_into_current_model",
    "load_exact_compatible_q12_parameters",
    "load_plumbing_checkpoint_state",
    "plumbing_checkpoint_state",
]
