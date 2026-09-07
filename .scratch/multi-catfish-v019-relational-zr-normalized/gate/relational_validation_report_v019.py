"""Validation-only reporting for the provisional V0.19 relational Q3 gate.

The runner in this directory owns the optimizer and writes raw validation
predictions.  This module is deliberately below that runner: it authenticates
those write-once artifacts, reads already-authenticated source closures, and
computes validation quantities from the raw Q3 surface and the exact-ZR label.
It never imports a simulator, opens a TEST split, or performs a learner
update.

All experimental choices are supplied by :class:`RelationalValidationConfig`.
In particular, there are no world, lineage, seed, threshold, or background
checkpoint defaults here.  The three null implementations are mechanical
estimands selected by the caller; their names must be listed in the external
configuration before a report is generated.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

import numpy as np
import torch


_GATE_ROOT = Path(__file__).resolve().parent
_LEARNER_ROOT = _GATE_ROOT.parent / "learner"
_REPO_ROOT = _GATE_ROOT.parents[2]
_SOURCE_ROOT = _REPO_ROOT / "src"
for _path in (_GATE_ROOT, _LEARNER_ROOT, _SOURCE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_relational_zr_c3_head_v019 import (  # noqa: E402
    NORMALIZED_BITS_PER_KAPPA,
    OUTPUT_UNIT_MODES,
)
from relational_q3_learner_v019 import (  # noqa: E402
    CHECKPOINT_SCHEMA,
    CHECKPOINT_VERSION,
)

from relational_learner_runner_v019 import (  # noqa: E402
    REQUIRED_UPDATES,
    RUNNER_SCHEMA,
    RelationalLearnerRunnerError,
    VerifiedSourceClosure,
    VerifiedSourcePanel,
    _file_sha256,
    _read_canonical_json,
    load_verified_source_panel,
    read_validation_predictions,
)
from relational_source_bridge import read_source_closure  # noqa: E402
from relational_source_schema import (  # noqa: E402
    ACTION_DIM,
    RelationalZRC3Source,
)


REPORT_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-validation-report-v1"
REPORT_VERSION = 1
REPORT_FILENAME = "result.json"
REPORT_SEAL_FILENAME = "result-seal.json"
SURFACE_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-validation-surfaces-v1"
SURFACE_VERSION = 1
SURFACE_NPZ_FILENAME = "validation-surfaces.npz"
SURFACE_METADATA_FILENAME = "validation-surfaces.json"
SURFACE_RECEIPT_FILENAME = "validation-surfaces.sha256"
BACKGROUND_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-background-surfaces-v1"
BACKGROUND_VERSION = 1
BACKGROUND_NPZ_FILENAME = "background.npz"
BACKGROUND_METADATA_FILENAME = "background.json"
BACKGROUND_RECEIPT_FILENAME = "background.sha256"
BACKGROUND_PANEL_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-background-panel-v1"
BACKGROUND_PANEL_FILENAME = "background-panel.json"
BACKGROUND_REPRESENTATION_SEPARATE = "SEPARATE_Q1_Q2"
BACKGROUND_REPRESENTATION_SUM_ZERO = "Q1_PLUS_Q2_SUM_WITH_ZERO_RIGHT"
BACKGROUND_REPRESENTATIONS = frozenset(
    {BACKGROUND_REPRESENTATION_SEPARATE, BACKGROUND_REPRESENTATION_SUM_ZERO}
)
CLAIM_CEILING = "TRAIN_VALIDATION_SOURCE_ONLY_NO_TRAJECTORY_EE_OR_EFFICACY_CLAIM"
FROZEN_STATUS = "FROZEN_BEFORE_OUTCOME"
EXPECTED_TRAIN_WORLD_COUNT = 4
EXPECTED_VALIDATION_WORLD_COUNT = 3
EXPECTED_INITIALIZATION_COUNT = 3
REQUIRED_NULL_KINDS = ("zero", "action_only")
_Q_VALUE_KEY = re.compile(r"^q_values_(\d{4})$")
_NULL_KINDS = frozenset({"zero", "train_median", "action_only"})


class RelationalValidationReportError(ValueError):
    """A source, prediction, checkpoint, or validation-report boundary failed."""


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
        raise RelationalValidationReportError(
            "report payload is not finite canonical JSON"
        ) from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RelationalValidationReportError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RelationalValidationReportError(f"{field} must be a positive integer")
    return value


def _finite(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise RelationalValidationReportError(f"{field} must be finite") from error
    if not math.isfinite(result):
        raise RelationalValidationReportError(f"{field} must be finite")
    return result


def _finite_positive(value: object, *, field: str) -> float:
    result = _finite(value, field=field)
    if result <= 0.0:
        raise RelationalValidationReportError(f"{field} must be finite and positive")
    return result


def _array_sha256(value: object) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _write_once(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise RelationalValidationReportError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    except FileExistsError as error:
        raise RelationalValidationReportError(f"refusing to overwrite {path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return _file_sha256(path)


def _as_tuple_ints(values: Sequence[int], *, field: str) -> tuple[int, ...]:
    result = tuple(values)
    if not result:
        raise RelationalValidationReportError(f"{field} must not be empty")
    for value in result:
        _positive_int(value, field=field)
    if len(set(result)) != len(result):
        raise RelationalValidationReportError(f"{field} contains duplicates")
    return result


def _digest_pairs(
    values: Sequence[tuple[int, str]], *, field: str
) -> tuple[tuple[int, str], ...]:
    if not values:
        raise RelationalValidationReportError(f"{field} must not be empty")
    result = tuple(
        (_positive_int(lineage, field=f"{field}.lineage"), _digest(value, field=f"{field}.sha256"))
        for lineage, value in values
    )
    if len({lineage for lineage, _value in result}) != len(result):
        raise RelationalValidationReportError(f"{field} contains duplicate lineages")
    return tuple(sorted(result))


def _initialization_pairs(
    values: Sequence[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    if not values:
        raise RelationalValidationReportError("initialization_lineages must not be empty")
    result = tuple(
        (
            _positive_int(seed, field="initialization_seed"),
            _positive_int(lineage, field="initialization_lineage"),
        )
        for seed, lineage in values
    )
    if len({seed for seed, _lineage in result}) != len(result):
        raise RelationalValidationReportError("initialization seeds contain duplicates")
    if len({lineage for _seed, lineage in result}) != len(result):
        raise RelationalValidationReportError("initialization lineages contain duplicates")
    return tuple(sorted(result))


def _gate_mapping(value: object, *, contract_sha256: str) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        # Accept the pure draft gate config without importing it into the
        # reporting seam.  This keeps the report's computation independent of
        # the draft adjudicator implementation.
        required = (
            "contract_sha256",
            "contract_status",
            "min_mean_skill",
            "min_positive_initializations",
            "min_supported_change_rate",
            "min_supported_initializations",
            "required_updates",
        )
        if not all(hasattr(value, field) for field in required):
            raise RelationalValidationReportError("gate_config must be a mapping or gate config")
        raw = {field: getattr(value, field) for field in required}
    else:
        raw = dict(value)
    expected = {
        "contract_sha256",
        "contract_status",
        "min_mean_skill",
        "min_positive_initializations",
        "min_supported_change_rate",
        "min_supported_initializations",
        "required_updates",
    }
    if set(raw) != expected:
        raise RelationalValidationReportError(
            "gate_config contains unknown or missing fields"
        )
    if raw["contract_sha256"] != contract_sha256:
        raise RelationalValidationReportError("gate contract digest disagrees with report config")
    if raw["contract_status"] != FROZEN_STATUS:
        raise RelationalValidationReportError("gate contract is not frozen before outcome")
    if raw["required_updates"] != REQUIRED_UPDATES:
        raise RelationalValidationReportError(
            f"gate required_updates must be exactly {REQUIRED_UPDATES}"
        )
    skill = _finite(raw["min_mean_skill"], field="gate.min_mean_skill")
    support = _finite(raw["min_supported_change_rate"], field="gate.min_supported_change_rate")
    if not 0.0 <= support <= 1.0:
        raise RelationalValidationReportError("gate min_supported_change_rate must lie in [0, 1]")
    for field in ("min_positive_initializations", "min_supported_initializations"):
        if (
            isinstance(raw[field], bool)
            or not isinstance(raw[field], int)
            or raw[field] < 1
        ):
            raise RelationalValidationReportError(f"gate {field} must be a positive integer")
    if (
        skill != 0.0
        or support != 0.5
        or raw["min_positive_initializations"] != 2
        or raw["min_supported_initializations"] != 2
    ):
        raise RelationalValidationReportError(
            "gate thresholds disagree with the frozen V0.19 acceptance rule"
        )
    return raw


@dataclass(frozen=True)
class RelationalValidationConfig:
    """External choices for one validation report.

    No field has a scientific default.  ``null_kinds`` is the predeclared
    ordered set used to identify the strongest null; the first item wins a
    numerical tie.  ``gate_config`` is optional so a report can be generated
    before a support-bearing Q1/Q2 package is made available.  In that case no
    acceptance decision is emitted.
    """

    contract_sha256: str
    code_manifest_sha256: str
    source_panel_sha256: str
    train_worlds: tuple[int, ...]
    validation_worlds: tuple[int, ...]
    initialization_lineages: tuple[tuple[int, int], ...]
    q1_checkpoint_sha256_by_lineage: tuple[tuple[int, str], ...]
    q2_checkpoint_sha256_by_lineage: tuple[tuple[int, str], ...]
    kappa_bits: float
    output_unit_mode: str
    null_kinds: tuple[str, ...]
    gate_config: Mapping[str, object] | object | None = None
    expected_checkpoint_sha256_by_initialization: tuple[tuple[int, str], ...] = ()

    def __post_init__(self) -> None:
        _digest(self.contract_sha256, field="contract_sha256")
        _digest(self.code_manifest_sha256, field="code_manifest_sha256")
        _digest(self.source_panel_sha256, field="source_panel_sha256")
        _finite_positive(self.kappa_bits, field="kappa_bits")
        if self.output_unit_mode != NORMALIZED_BITS_PER_KAPPA:
            raise RelationalValidationReportError(
                "V0.19 validation gate requires normalized_bits_per_kappa"
            )
        train = _as_tuple_ints(self.train_worlds, field="train_worlds")
        validation = _as_tuple_ints(self.validation_worlds, field="validation_worlds")
        if set(train) & set(validation):
            raise RelationalValidationReportError(
                "train_worlds and validation_worlds must be disjoint"
            )
        initializations = _initialization_pairs(self.initialization_lineages)
        q1 = _digest_pairs(
            self.q1_checkpoint_sha256_by_lineage,
            field="q1_checkpoint_sha256_by_lineage",
        )
        q2 = _digest_pairs(
            self.q2_checkpoint_sha256_by_lineage,
            field="q2_checkpoint_sha256_by_lineage",
        )
        lineages = {lineage for _seed, lineage in initializations}
        if {lineage for lineage, _digest_value in q1} != lineages:
            raise RelationalValidationReportError("Q1 digest bindings do not cover initializations")
        if {lineage for lineage, _digest_value in q2} != lineages:
            raise RelationalValidationReportError("Q2 digest bindings do not cover initializations")
        nulls = tuple(str(kind) for kind in self.null_kinds)
        if not nulls or len(set(nulls)) != len(nulls):
            raise RelationalValidationReportError("null_kinds must be nonempty and unique")
        if any(kind not in _NULL_KINDS for kind in nulls):
            raise RelationalValidationReportError(
                f"null_kinds must be selected from {sorted(_NULL_KINDS)}"
            )
        checkpoint_pairs = tuple(self.expected_checkpoint_sha256_by_initialization)
        if checkpoint_pairs:
            checked = tuple(
                (
                    _positive_int(seed, field="expected checkpoint initialization_seed"),
                    _digest(value, field="expected checkpoint sha256"),
                )
                for seed, value in checkpoint_pairs
            )
            if {seed for seed, _value in checked} != {
                seed for seed, _lineage in initializations
            }:
                raise RelationalValidationReportError(
                    "expected checkpoint bindings do not cover initializations"
                )
            object.__setattr__(self, "expected_checkpoint_sha256_by_initialization", tuple(sorted(checked)))
        object.__setattr__(self, "train_worlds", train)
        object.__setattr__(self, "validation_worlds", validation)
        object.__setattr__(self, "initialization_lineages", initializations)
        object.__setattr__(self, "q1_checkpoint_sha256_by_lineage", q1)
        object.__setattr__(self, "q2_checkpoint_sha256_by_lineage", q2)
        object.__setattr__(self, "null_kinds", nulls)
        gate = _gate_mapping(self.gate_config, contract_sha256=self.contract_sha256)
        if gate is not None:
            if len(train) != EXPECTED_TRAIN_WORLD_COUNT:
                raise RelationalValidationReportError(
                    f"frozen gate requires exactly {EXPECTED_TRAIN_WORLD_COUNT} TRAIN worlds"
                )
            if len(validation) != EXPECTED_VALIDATION_WORLD_COUNT:
                raise RelationalValidationReportError(
                    f"frozen gate requires exactly {EXPECTED_VALIDATION_WORLD_COUNT} VALIDATION worlds"
                )
            if len(initializations) != EXPECTED_INITIALIZATION_COUNT:
                raise RelationalValidationReportError(
                    f"frozen gate requires exactly {EXPECTED_INITIALIZATION_COUNT} initializations"
                )
            if nulls != REQUIRED_NULL_KINDS:
                raise RelationalValidationReportError(
                    "frozen gate requires ordered null_kinds zero, action_only"
                )
        object.__setattr__(self, "gate_config", gate)

    @property
    def initialization_seeds(self) -> tuple[int, ...]:
        return tuple(seed for seed, _lineage in self.initialization_lineages)

    @property
    def initialization_lineage_map(self) -> dict[int, int]:
        return {seed: lineage for seed, lineage in self.initialization_lineages}

    @property
    def q1_digest_map(self) -> dict[int, str]:
        return {lineage: digest for lineage, digest in self.q1_checkpoint_sha256_by_lineage}

    @property
    def q2_digest_map(self) -> dict[int, str]:
        return {lineage: digest for lineage, digest in self.q2_checkpoint_sha256_by_lineage}

    @property
    def expected_checkpoint_map(self) -> dict[int, str]:
        return {seed: digest for seed, digest in self.expected_checkpoint_sha256_by_initialization}

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_sha256": self.contract_sha256,
            "code_manifest_sha256": self.code_manifest_sha256,
            "source_panel_sha256": self.source_panel_sha256,
            "train_worlds": list(self.train_worlds),
            "validation_worlds": list(self.validation_worlds),
            "initialization_lineages": [
                {"initialization_seed": seed, "lineage": lineage}
                for seed, lineage in self.initialization_lineages
            ],
            "q1_checkpoint_sha256_by_lineage": [
                {"lineage": lineage, "sha256": digest}
                for lineage, digest in self.q1_checkpoint_sha256_by_lineage
            ],
            "q2_checkpoint_sha256_by_lineage": [
                {"lineage": lineage, "sha256": digest}
                for lineage, digest in self.q2_checkpoint_sha256_by_lineage
            ],
            "kappa_bits_hex": float(self.kappa_bits).hex(),
            "output_unit_mode": self.output_unit_mode,
            "null_kinds": list(self.null_kinds),
            "gate_config": dict(self.gate_config) if self.gate_config is not None else None,
            "expected_checkpoint_sha256_by_initialization": [
                {"initialization_seed": seed, "sha256": digest}
                for seed, digest in self.expected_checkpoint_sha256_by_initialization
            ],
        }


@dataclass(frozen=True)
class _AuthenticatedInitialization:
    seed: int
    lineage: int
    output_dir: Path
    result: dict[str, object]
    prediction_arrays: dict[str, np.ndarray]
    prediction_metadata: dict[str, object]
    checkpoint_path: Path
    checkpoint_sha256: str


@dataclass(frozen=True)
class _BackgroundSurface:
    seed: int
    lineage: int
    source_sha256: str
    q1_checkpoint_sha256: str
    q2_checkpoint_sha256: str
    representation: str
    arrays: dict[tuple[str, int, int], tuple[np.ndarray, np.ndarray]]
    metadata_sha256: str
    npz_sha256: str


def _read_ascii_json(path: Path, *, label: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise RelationalValidationReportError(f"missing regular {label}: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RelationalValidationReportError(f"{label} is not JSON: {path}") from error
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        raise RelationalValidationReportError(f"{label} is not canonical JSON: {path}")
    return payload


def _verify_contract_file(path: str | Path | None, expected_sha256: str) -> str:
    if path is None:
        return expected_sha256
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise RelationalValidationReportError(f"expected a regular contract file: {source}")
    actual = _file_sha256(source)
    if actual != expected_sha256:
        raise RelationalValidationReportError("contract digest mismatch")
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise RelationalValidationReportError("contract is not readable text") from error
    if FROZEN_STATUS not in text:
        raise RelationalValidationReportError("contract is not frozen before outcome")
    return actual


def _resolve_artifact(path_value: object, *, output_dir: Path, field: str) -> Path:
    if not isinstance(path_value, str) or not path_value:
        raise RelationalValidationReportError(f"{field} path is malformed")
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = output_dir / candidate
    if candidate.is_symlink() or not candidate.is_file():
        raise RelationalValidationReportError(f"missing regular {field}: {candidate}")
    return candidate


def _verify_normalized_checkpoint(path: Path) -> None:
    """Authenticate the V0.19 scorer-unit marker inside the checkpoint.

    The learner result and prediction metadata are JSON receipts, but the
    checkpoint is a torch mapping.  Reading only these immutable metadata
    fields keeps the validation report independent of model execution while
    preventing a raw-bits checkpoint from being relabelled as V0.19.
    """

    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except (OSError, EOFError, RuntimeError, ValueError, TypeError) as error:
        raise RelationalValidationReportError(
            "learner checkpoint could not be decoded"
        ) from error
    if not isinstance(payload, Mapping):
        raise RelationalValidationReportError("learner checkpoint is not a mapping")
    if payload.get("schema") != CHECKPOINT_SCHEMA or payload.get("format_version") != CHECKPOINT_VERSION:
        raise RelationalValidationReportError("learner checkpoint schema is stale")
    if payload.get("update_count") != REQUIRED_UPDATES:
        raise RelationalValidationReportError(
            f"learner checkpoint must contain exactly {REQUIRED_UPDATES} updates"
        )
    if payload.get("test_split_opened") is not False or payload.get("episode_training") is not False:
        raise RelationalValidationReportError(
            "learner checkpoint crosses the evaluation boundary"
        )
    if payload.get("output_unit_mode") != NORMALIZED_BITS_PER_KAPPA:
        raise RelationalValidationReportError(
            "learner checkpoint output_unit_mode is not normalized_bits_per_kappa"
        )
    config = payload.get("config")
    if not isinstance(config, Mapping):
        raise RelationalValidationReportError("learner checkpoint config is missing")
    if config.get("output_unit_mode") != NORMALIZED_BITS_PER_KAPPA:
        raise RelationalValidationReportError(
            "learner checkpoint config output_unit_mode drifted"
        )


def _read_prediction_result(output_dir: Path) -> tuple[dict[str, object], str]:
    result_path = output_dir / REPORT_FILENAME
    # The learner runner writes result.json with its own schema.  A separate
    # report also uses result.json, so this function is called only on an init
    # directory, never on the final report directory.
    if result_path.is_symlink() or not result_path.is_file():
        raise RelationalValidationReportError(f"missing learner result: {result_path}")
    result = _read_ascii_json(result_path, label="learner result")
    supplied = _digest(result.get("result_sha256"), field="learner result_sha256")
    body = {key: value for key, value in result.items() if key != "result_sha256"}
    if canonical_sha256(body) != supplied:
        raise RelationalValidationReportError("learner result self-digest failed")
    if result.get("schema") != RUNNER_SCHEMA:
        raise RelationalValidationReportError("learner result schema is stale")
    if result.get("output_unit_mode") != NORMALIZED_BITS_PER_KAPPA:
        raise RelationalValidationReportError(
            "learner result output_unit_mode is not normalized_bits_per_kappa"
        )
    result_config = result.get("config")
    if not isinstance(result_config, Mapping) or result_config.get("output_unit_mode") != NORMALIZED_BITS_PER_KAPPA:
        raise RelationalValidationReportError(
            "learner result config output_unit_mode drifted"
        )
    return result, _file_sha256(result_path)


def _validate_prediction_entries(
    *,
    arrays: Mapping[str, np.ndarray],
    metadata: Mapping[str, object],
    panel: VerifiedSourcePanel,
    lineage: int,
) -> dict[tuple[str, int, int], np.ndarray]:
    if metadata.get("output_unit_mode") != NORMALIZED_BITS_PER_KAPPA:
        raise RelationalValidationReportError(
            "prediction output_unit_mode is not normalized_bits_per_kappa"
        )
    raw_entries = metadata.get("arrays")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise RelationalValidationReportError("prediction array manifest is empty")
    if set(arrays) != {str(entry.get("key")) for entry in raw_entries if isinstance(entry, Mapping)}:
        raise RelationalValidationReportError("prediction arrays contain unknown or missing keys")
    result: dict[tuple[str, int, int], np.ndarray] = {}
    for index, entry in enumerate(raw_entries):
        if not isinstance(entry, Mapping):
            raise RelationalValidationReportError("prediction manifest entry is malformed")
        expected_key = f"q_values_{index:04d}"
        if entry.get("key") != expected_key or _Q_VALUE_KEY.fullmatch(expected_key) is None:
            raise RelationalValidationReportError("prediction manifest contains a non-Q3 or reordered array")
        split = entry.get("split")
        if split != "VALIDATION":
            raise RelationalValidationReportError("prediction artifact contains a non-validation split")
        try:
            world = _positive_int(entry.get("world_seed"), field="prediction.world_seed")
            entry_lineage = _positive_int(entry.get("lineage"), field="prediction.lineage")
        except RelationalValidationReportError:
            raise
        if entry_lineage != lineage:
            raise RelationalValidationReportError("prediction lineage disagrees with initialization")
        key = ("VALIDATION", world, entry_lineage)
        if key in result:
            raise RelationalValidationReportError("prediction manifest contains duplicate world/lineage")
        try:
            closure = panel.lookup(split="VALIDATION", world_seed=world, lineage=lineage)
        except RelationalLearnerRunnerError as error:
            raise RelationalValidationReportError(
                "prediction world/lineage is outside the authenticated validation panel"
            ) from error
        values = np.asarray(arrays[expected_key])
        if values.ndim != 2 or values.shape != (closure.source.rows, ACTION_DIM):
            raise RelationalValidationReportError(
                f"prediction shape disagrees for world/lineage {world}/{lineage}"
            )
        if not np.issubdtype(values.dtype, np.floating) or not np.all(np.isfinite(values)):
            raise RelationalValidationReportError("prediction surface is nonfinite or nonnumeric")
        rows = np.arange(values.shape[0], dtype=np.int64)
        if np.any(values[~closure.source.action_mask] != 0.0):
            raise RelationalValidationReportError("prediction surface is nonzero outside native mask")
        if np.any(values[rows, closure.source.reference_actions] != 0.0):
            raise RelationalValidationReportError("prediction surface is nonzero at reference action")
        if set(entry) != {
            "key",
            "split",
            "world_seed",
            "lineage",
            "rows",
            "dtype",
            "shape",
            "array_sha256",
        }:
            raise RelationalValidationReportError("prediction manifest entry contains unknown fields")
        if entry.get("rows") != values.shape[0] or entry.get("shape") != list(values.shape):
            raise RelationalValidationReportError("prediction manifest shape disagrees with NPZ")
        if entry.get("dtype") != values.dtype.str or entry.get("array_sha256") != _array_sha256(values):
            raise RelationalValidationReportError("prediction manifest digest disagrees with NPZ")
        result[key] = np.array(values, copy=True, order="C")
    expected = {
        ("VALIDATION", world, lineage) for world in panel.validation_worlds
    }
    if set(result) != expected:
        raise RelationalValidationReportError("validation prediction closure is missing a world")
    return result


def _authenticate_initialization(
    *,
    output_dir: str | Path,
    seed: int,
    lineage: int,
    panel: VerifiedSourcePanel,
    config: RelationalValidationConfig,
) -> _AuthenticatedInitialization:
    root = Path(output_dir)
    if root.is_symlink() or not root.is_dir():
        raise RelationalValidationReportError(f"learner output is not a regular directory: {root}")
    result, _result_file_sha256 = _read_prediction_result(root)
    if result.get("status") != "MECHANICAL_ARTIFACT_WRITTEN":
        raise RelationalValidationReportError("learner result is not a mechanical artifact")
    if result.get("output_unit_mode") != config.output_unit_mode:
        raise RelationalValidationReportError(
            "learner result output_unit_mode disagrees with validation config"
        )
    if result.get("initialization_seed") != seed or result.get("lineage") != lineage:
        raise RelationalValidationReportError("learner result initialization identity mismatch")
    if result.get("source_panel_sha256") != config.source_panel_sha256:
        raise RelationalValidationReportError("learner result source digest mismatch")
    if result.get("update_count") != REQUIRED_UPDATES or result.get("restored_update_count") != REQUIRED_UPDATES:
        raise RelationalValidationReportError(
            f"learner result must contain exactly {REQUIRED_UPDATES} updates"
        )
    if result.get("reload_bitwise_equal") is not True:
        raise RelationalValidationReportError("learner checkpoint reload was not bitwise identical")
    if result.get("test_split_opened") is not False or result.get("episode_training") is not False:
        raise RelationalValidationReportError("learner result crosses the evaluation boundary")
    binding = result.get("q1_q2_digest_binding")
    if not isinstance(binding, Mapping) or binding.get("loaded") is not False or binding.get("modified") is not False:
        raise RelationalValidationReportError("Q1/Q2 binding is not frozen and unloaded")
    if binding.get("q1_checkpoint_sha256") != config.q1_digest_map[lineage] or binding.get("q2_checkpoint_sha256") != config.q2_digest_map[lineage]:
        raise RelationalValidationReportError("Q1/Q2 checkpoint digest binding mismatch")
    checkpoint_record = result.get("checkpoint")
    if not isinstance(checkpoint_record, Mapping):
        raise RelationalValidationReportError("learner checkpoint receipt is missing")
    checkpoint_path = _resolve_artifact(
        checkpoint_record.get("path"), output_dir=root, field="learner checkpoint"
    )
    checkpoint_sha256 = _digest(checkpoint_record.get("checkpoint_sha256"), field="checkpoint_sha256")
    if _file_sha256(checkpoint_path) != checkpoint_sha256:
        raise RelationalValidationReportError("checkpoint digest mismatch")
    _verify_normalized_checkpoint(checkpoint_path)
    expected_checkpoint = config.expected_checkpoint_map.get(seed)
    if expected_checkpoint is not None and checkpoint_sha256 != expected_checkpoint:
        raise RelationalValidationReportError("checkpoint digest disagrees with external binding")
    try:
        arrays, metadata = read_validation_predictions(root)
    except Exception as error:
        if isinstance(error, RelationalValidationReportError):
            raise
        raise RelationalValidationReportError("validation prediction artifact failed authentication") from error
    if metadata.get("source_sha256") != config.source_panel_sha256:
        raise RelationalValidationReportError("prediction source digest mismatch")
    if metadata.get("initialization_seed") != seed or metadata.get("lineage") != lineage:
        raise RelationalValidationReportError("prediction metadata initialization identity mismatch")
    if metadata.get("output_unit_mode") != config.output_unit_mode:
        raise RelationalValidationReportError(
            "prediction output_unit_mode disagrees with validation config"
        )
    if result.get("parameter_sha256") != metadata.get("parameter_sha256"):
        raise RelationalValidationReportError("prediction parameter digest mismatch")
    prediction_record = result.get("validation_predictions")
    if not isinstance(prediction_record, Mapping):
        raise RelationalValidationReportError("learner result is missing prediction receipt")
    for field in (
        "npz_sha256",
        "arrays_sha256",
        "prediction_metadata_sha256",
    ):
        if prediction_record.get(field) != metadata.get(field):
            raise RelationalValidationReportError(f"prediction receipt {field} mismatch")
    if result.get("validation_prediction_digest") != metadata.get("arrays_sha256"):
        raise RelationalValidationReportError("validation prediction digest mismatch")
    _validate_prediction_entries(
        arrays=arrays,
        metadata=metadata,
        panel=panel,
        lineage=lineage,
    )
    return _AuthenticatedInitialization(
        seed=seed,
        lineage=lineage,
        output_dir=root,
        result=result,
        prediction_arrays=arrays,
        prediction_metadata=metadata,
        checkpoint_path=checkpoint_path,
        checkpoint_sha256=checkpoint_sha256,
    )


def _pairs_for_source(
    source: RelationalZRC3Source,
    *,
    q_surface: np.ndarray | None,
    kappa_bits: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if float(source.kappa_bits).hex() != float(kappa_bits).hex():
        raise RelationalValidationReportError("source kappa disagrees with validation configuration")
    mask = np.asarray(source.action_mask)
    references = np.asarray(source.reference_actions, dtype=np.int64)
    rows, candidates = np.nonzero(
        mask & ~np.eye(ACTION_DIM, dtype=np.bool_)[references]
    )
    if rows.size < 1:
        raise RelationalValidationReportError("source closure has no non-reference validation comparison")
    target = np.asarray(source.target_surface_bits, dtype=np.float64)
    target_delta = (target[rows, candidates] - target[rows, references[rows]]) / float(kappa_bits)
    if q_surface is None:
        prediction_delta = np.zeros_like(target_delta)
    else:
        q = np.asarray(q_surface)
        if q.shape != (source.rows, ACTION_DIM) or not np.issubdtype(q.dtype, np.floating) or not np.all(np.isfinite(q)):
            raise RelationalValidationReportError("validation Q3 surface is malformed")
        prediction_delta = np.asarray(q[rows, candidates] - q[rows, references[rows]], dtype=np.float64)
    return rows.astype(np.int64), candidates.astype(np.int64), target_delta, prediction_delta


def _fit_action_only(
    rows: Sequence[tuple[RelationalZRC3Source, np.ndarray | None]],
    *,
    kappa_bits: float,
) -> tuple[np.ndarray, np.ndarray]:
    references: list[int] = []
    candidates: list[int] = []
    targets: list[float] = []
    for source, _surface in rows:
        row_index, candidate, target_delta, _prediction = _pairs_for_source(
            source, q_surface=None, kappa_bits=kappa_bits
        )
        references.extend(source.reference_actions[row_index].tolist())
        candidates.extend(candidate.tolist())
        targets.extend(target_delta.tolist())
    if not targets:
        raise RelationalValidationReportError("TRAIN source has no comparison rows for action-only null")
    design = np.zeros((len(targets), ACTION_DIM), dtype=np.float64)
    index = np.arange(len(targets), dtype=np.int64)
    design[index, np.asarray(candidates, dtype=np.int64)] = 1.0
    design[index, np.asarray(references, dtype=np.int64)] = -1.0
    coefficients, _residuals, _rank, _singular = np.linalg.lstsq(
        design, np.asarray(targets, dtype=np.float64), rcond=None
    )
    if not np.all(np.isfinite(coefficients)):
        raise RelationalValidationReportError("action-only null fit is nonfinite")
    # A held-out pair must be identified by the TRAIN action graph.  The
    # additive fit otherwise invents a value for an disconnected component.
    adjacency = [set() for _action in range(ACTION_DIM)]
    for left, right in zip(references, candidates, strict=True):
        adjacency[left].add(right)
        adjacency[right].add(left)
    components = np.full(ACTION_DIM, -1, dtype=np.int64)
    component = 0
    for start in range(ACTION_DIM):
        if components[start] >= 0 or not adjacency[start]:
            continue
        stack = [start]
        components[start] = component
        while stack:
            current = stack.pop()
            for neighbour in adjacency[current]:
                if components[neighbour] < 0:
                    components[neighbour] = component
                    stack.append(neighbour)
        component += 1
    return coefficients, components


def _null_prediction(
    kind: str,
    *,
    source: RelationalZRC3Source,
    target_delta: np.ndarray,
    train_median: float | None,
    action_coefficients: np.ndarray | None,
) -> np.ndarray:
    if kind == "zero":
        return np.zeros_like(target_delta)
    if kind == "train_median":
        if train_median is None:
            raise RelationalValidationReportError("train median null was not fit")
        return np.full_like(target_delta, train_median)
    if kind == "action_only":
        if action_coefficients is None:
            raise RelationalValidationReportError("action-only null was not fit")
        rows, candidates, _targets, _prediction = _pairs_for_source(
            source, q_surface=None, kappa_bits=source.kappa_bits
        )
        references = source.reference_actions[rows]
        return action_coefficients[candidates] - action_coefficients[references]
    raise RelationalValidationReportError(f"unknown null kind: {kind}")


def _mae_by_world(
    errors_by_world: Mapping[int, np.ndarray],
) -> tuple[float, float, dict[str, float]]:
    if not errors_by_world or any(values.size < 1 for values in errors_by_world.values()):
        raise RelationalValidationReportError("validation error set is empty")
    world_mae = {
        str(world): float(np.mean(values)) for world, values in sorted(errors_by_world.items())
    }
    macro = float(np.mean(tuple(world_mae.values())))
    pooled = float(np.mean(np.concatenate(tuple(errors_by_world.values()))))
    return macro, pooled, world_mae


def _validation_metrics(
    *,
    panel: VerifiedSourcePanel,
    lineage: int,
    predictions: Mapping[tuple[str, int, int], np.ndarray],
    null_kinds: Sequence[str],
    kappa_bits: float,
    background: Mapping[tuple[str, int, int], tuple[np.ndarray, np.ndarray]] | None = None,
) -> dict[str, object]:
    train_sources = [closure.source for closure in panel.train if closure.source.lineage == lineage]
    validation_closures = [closure for closure in panel.validation if closure.source.lineage == lineage]
    if not train_sources or not validation_closures:
        raise RelationalValidationReportError("lineage source closure is incomplete")
    train_pairs: list[float] = []
    for source in train_sources:
        _rows, _candidates, targets, _prediction = _pairs_for_source(
            source, q_surface=None, kappa_bits=kappa_bits
        )
        train_pairs.extend(targets.tolist())
    train_target = np.asarray(train_pairs, dtype=np.float64)
    train_median = float(np.median(train_target)) if "train_median" in null_kinds else None
    action_coefficients = None
    action_components = None
    if "action_only" in null_kinds:
        action_coefficients, action_components = _fit_action_only(
            [(source, None) for source in train_sources], kappa_bits=kappa_bits
        )
    model_errors: dict[int, np.ndarray] = {}
    null_errors: dict[str, dict[int, np.ndarray]] = {kind: {} for kind in null_kinds}
    # Decision-level metrics are intentionally separate from pairwise error
    # diagnostics.  A Q3 surface is useful for the gate only when the frozen
    # Q1+learned-Q2 background is present: without it there is no deployable
    # exact-ZR teacher action to compare against.
    model_decision_by_world: dict[int, np.ndarray] = {}
    null_decision_by_world: dict[str, dict[int, np.ndarray]] = {
        kind: {} for kind in null_kinds
    }
    null_pivotal_by_world: dict[str, dict[int, np.ndarray]] = {
        kind: {} for kind in null_kinds
    }
    pivotal_by_world: dict[int, tuple[int, int, int]] = {}
    total_changed = 0
    total_supported = 0
    total_positive_target_changes = 0
    total_pairs = 0
    for closure in sorted(validation_closures, key=lambda item: item.identity):
        identity = closure.identity
        if identity not in predictions:
            raise RelationalValidationReportError("validation prediction is missing a source closure")
        source = closure.source
        if action_components is not None:
            row_index, candidate_index, _target_delta, _prediction_delta = _pairs_for_source(
                source, q_surface=None, kappa_bits=kappa_bits
            )
            references_for_components = source.reference_actions[row_index]
            if np.any(action_components[candidate_index] < 0) or np.any(
                action_components[candidate_index] != action_components[references_for_components]
            ):
                raise RelationalValidationReportError(
                    "validation action pair is unidentified by the TRAIN null graph"
                )
        rows, _candidates, target_delta, prediction_delta = _pairs_for_source(
            source, q_surface=predictions[identity], kappa_bits=kappa_bits
        )
        if background is not None:
            if identity not in background:
                raise RelationalValidationReportError(
                    "background package is missing a validation closure"
                )
            q1, q2 = background[identity]
            if q1.shape != (source.rows, ACTION_DIM) or q2.shape != (source.rows, ACTION_DIM):
                raise RelationalValidationReportError(
                    "Q1/Q2 background surface shape disagrees with source"
                )
            if not np.all(np.isfinite(q1)) or not np.all(np.isfinite(q2)):
                raise RelationalValidationReportError(
                    "Q1/Q2 background surface is nonfinite"
                )
            base_scores = np.asarray(q1, dtype=np.float64) + np.asarray(q2, dtype=np.float64)
            model_scores = base_scores + np.asarray(predictions[identity], dtype=np.float64)
            teacher_scores = base_scores + np.asarray(source.target_surface_bits, dtype=np.float64) / float(kappa_bits)
            native_mask = np.asarray(source.action_mask)
            base_actions = _masked_argmax(base_scores, native_mask)
            model_actions = _masked_argmax(model_scores, native_mask)
            teacher_actions = _masked_argmax(teacher_scores, native_mask)
            model_decision_by_world[source.world_seed] = np.asarray(
                model_actions == teacher_actions, dtype=np.float64
            )
            pivotal = teacher_actions != base_actions
            pivotal_by_world[source.world_seed] = (
                int(np.count_nonzero(pivotal)),
                int(np.count_nonzero((model_actions == teacher_actions) & pivotal)),
                int(np.count_nonzero((teacher_actions == base_actions) & (model_actions == base_actions))),
            )
            changed = model_actions != base_actions
            target_at_model = np.asarray(source.target_surface_bits)[
                np.arange(source.rows, dtype=np.int64), model_actions
            ]
            compatible_at_model = np.asarray(source.positive_credit_compatible)[
                np.arange(source.rows, dtype=np.int64), model_actions
            ]
            total_changed += int(np.count_nonzero(changed))
            total_supported += int(np.count_nonzero(changed & compatible_at_model & (target_at_model > 0.0)))
            total_positive_target_changes += int(np.count_nonzero(changed & (target_at_model > 0.0)))
            for kind in null_kinds:
                if kind == "zero":
                    null_surface = np.zeros_like(model_scores)
                elif kind == "train_median":
                    if train_median is None:
                        raise RelationalValidationReportError("train median null was not fit")
                    null_surface = np.zeros_like(model_scores)
                    null_surface[native_mask] = train_median
                    null_surface[
                        np.arange(source.rows, dtype=np.int64), source.reference_actions
                    ] = 0.0
                elif kind == "action_only":
                    if action_coefficients is None:
                        raise RelationalValidationReportError("action-only null was not fit")
                    null_surface = np.zeros_like(model_scores)
                    legal_rows, legal_candidates = np.nonzero(native_mask)
                    null_surface[legal_rows, legal_candidates] = (
                        action_coefficients[legal_candidates]
                        - action_coefficients[source.reference_actions[legal_rows]]
                    )
                else:
                    raise RelationalValidationReportError(f"unknown null kind: {kind}")
                null_actions = _masked_argmax(base_scores + null_surface, native_mask)
                null_decision_by_world[kind][source.world_seed] = np.asarray(
                    null_actions == teacher_actions, dtype=np.float64
                )
                null_pivotal_by_world[kind][source.world_seed] = np.asarray(
                    (null_actions == teacher_actions) & pivotal, dtype=np.float64
                )
        total_pairs += int(target_delta.size)
        model_row_errors: list[float] = []
        null_row_errors: dict[str, list[float]] = {kind: [] for kind in null_kinds}
        references = source.reference_actions[rows]
        for row in range(source.rows):
            keep = rows == row
            if not np.any(keep):
                continue
            model_row_errors.append(float(np.mean(np.abs(prediction_delta[keep] - target_delta[keep]))))
            for kind in null_kinds:
                if kind == "zero":
                    null_prediction = np.zeros(int(np.count_nonzero(keep)), dtype=np.float64)
                elif kind == "train_median":
                    if train_median is None:
                        raise RelationalValidationReportError("train median null was not fit")
                    null_prediction = np.full(int(np.count_nonzero(keep)), train_median, dtype=np.float64)
                elif kind == "action_only":
                    if action_coefficients is None:
                        raise RelationalValidationReportError("action-only null was not fit")
                    candidates = np.asarray(_candidates[keep], dtype=np.int64)
                    reference = np.full(candidates.shape, int(references[keep][0]), dtype=np.int64)
                    null_prediction = action_coefficients[candidates] - action_coefficients[reference]
                else:
                    raise RelationalValidationReportError(f"unknown null kind: {kind}")
                null_row_errors[kind].append(float(np.mean(np.abs(null_prediction - target_delta[keep]))))
        model_errors[source.world_seed] = np.asarray(model_row_errors, dtype=np.float64)
        for kind in null_kinds:
            null_errors[kind][source.world_seed] = np.asarray(null_row_errors[kind], dtype=np.float64)
    model_mae, model_pooled, model_by_world = _mae_by_world(model_errors)
    null_metrics: dict[str, dict[str, object]] = {}
    for kind in null_kinds:
        mae, pooled, by_world = _mae_by_world(null_errors[kind])
        null_metrics[kind] = {
            "mae": mae,
            "pooled_pair_mae": pooled,
            "mae_by_world": by_world,
        }
    # The null used by the acceptance metric is selected mechanically from
    # pivotal teacher-action agreement.  ZERO wins an exact tie.  Pairwise
    # MAE is retained only as a transparent diagnostic.
    if background is None:
        strongest_name = None
        skill = None
        model_agreement = None
        model_agreement_by_world: dict[str, float] = {}
        null_agreement: dict[str, dict[str, object]] = {}
        null_pivotal_agreement: dict[str, dict[str, object]] = {}
        pivotal_agreement_by_world: dict[str, float] = {}
        pivotal_rows = 0
        pivotal_agreement = None
        stable_preservation = None
        strongest_pivotal_agreement = None
    else:
        model_agreement_by_world = {
            str(world): float(np.mean(values))
            for world, values in sorted(model_decision_by_world.items())
        }
        model_agreement = float(np.mean(tuple(model_agreement_by_world.values())))
        pivotal_agreement_by_world = {
            str(world): (
                float(value[1] / value[0]) if value[0] else 0.0
            )
            for world, value in sorted(pivotal_by_world.items())
        }
        pivotal_rows = sum(value[0] for value in pivotal_by_world.values())
        null_agreement = {}
        null_pivotal_agreement = {}
        for kind in null_kinds:
            by_world = {
                str(world): float(np.mean(values))
                for world, values in sorted(null_decision_by_world[kind].items())
            }
            pivotal_by_world_for_null = {
                str(world): (
                    float(np.count_nonzero(values) / pivotal_by_world[world][0])
                    if pivotal_by_world[world][0]
                    else 0.0
                )
                for world, values in sorted(null_pivotal_by_world[kind].items())
            }
            null_agreement[kind] = {
                "teacher_action_agreement_by_world": by_world,
                "teacher_action_agreement": float(np.mean(tuple(by_world.values()))),
            }
            null_pivotal_agreement[kind] = {
                "pivotal_agreement_by_world": pivotal_by_world_for_null,
                "pivotal_agreement": (
                    float(
                        sum(
                            int(np.count_nonzero(values))
                            for values in null_pivotal_by_world[kind].values()
                        )
                        / pivotal_rows
                    )
                    if pivotal_rows
                    else 0.0
                ),
            }
            null_agreement[kind].update(null_pivotal_agreement[kind])
        strongest_name = max(
            null_kinds,
            key=lambda kind: (
                float(null_agreement[kind]["pivotal_agreement"]),
                1 if kind == "zero" else 0,
                -tuple(null_kinds).index(kind),
            ),
        )
        strongest_pivotal_agreement = float(
            null_agreement[strongest_name]["pivotal_agreement"]
        )
        pivotal_total = sum(value[0] for value in pivotal_by_world.values())
        pivotal_correct = sum(value[1] for value in pivotal_by_world.values())
        # ``validation_skill`` is the preregistered decision-level recovery
        # on pivotal rows over the strongest predeclared null.  All-anchor
        # agreement remains a separately reported diagnostic.
        pivotal_agreement = float(pivotal_correct / pivotal_total) if pivotal_total else 0.0
        skill = float(pivotal_agreement - strongest_pivotal_agreement)
        # The exact stable denominator is the number of rows where teacher and
        # base agree.  Reconstruct it directly from persisted surfaces rather
        # than deriving it from the pivotal tuple.
        stable_correct = 0
        stable_total = 0
        for closure in validation_closures:
            identity = closure.identity
            source = closure.source
            q1, q2 = background[identity]
            base = _masked_argmax(
                np.asarray(q1, dtype=np.float64) + np.asarray(q2, dtype=np.float64),
                source.action_mask,
            )
            teacher = _masked_argmax(
                np.asarray(q1, dtype=np.float64)
                + np.asarray(q2, dtype=np.float64)
                + np.asarray(source.target_surface_bits, dtype=np.float64) / float(kappa_bits),
                source.action_mask,
            )
            stable = teacher == base
            stable_total += int(np.count_nonzero(stable))
            learned = _masked_argmax(
                np.asarray(q1, dtype=np.float64)
                + np.asarray(q2, dtype=np.float64)
                + np.asarray(predictions[identity], dtype=np.float64),
                source.action_mask,
            )
            stable_correct += int(np.count_nonzero(stable & (learned == base)))
        stable_preservation = float(stable_correct / stable_total) if stable_total else 0.0
    strongest_mae = (
        float(null_metrics[strongest_name]["mae"])
        if strongest_name is not None
        else None
    )
    return {
        "lineage": lineage,
        "validation_worlds": sorted(model_errors),
        "validation_rows": int(sum(values.size for values in model_errors.values())),
        "validation_pairs": total_pairs,
        "model_mae": model_mae,
        "model_pooled_pair_mae": model_pooled,
        "model_mae_by_world": model_by_world,
        "nulls": null_metrics,
        "strongest_null_name": strongest_name,
        "strongest_null_mae": strongest_mae,
        "strongest_null_pivotal_agreement": strongest_pivotal_agreement,
        "validation_skill": skill,
        "skill_vs_strongest_null": skill,
        "teacher_action_agreement": model_agreement,
        "teacher_action_agreement_by_world": model_agreement_by_world,
        "null_teacher_action_agreement": null_agreement,
        "pivotal_rows": pivotal_rows,
        "pivotal_agreement": pivotal_agreement,
        "pivotal_agreement_by_world": pivotal_agreement_by_world,
        "stable_preservation": stable_preservation,
        "background_changed_action_count": total_changed if background is not None else None,
        "supported_positive_change_count": total_supported if background is not None else None,
        "positive_target_change_count": total_positive_target_changes if background is not None else None,
        "positive_support_rate": (
            float(total_supported / total_changed)
            if background is not None and total_changed
            else (0.0 if background is not None else None)
        ),
        "has_change_exposure": bool(total_changed) if background is not None else None,
        # Keep the gate-facing name explicit; it is the same validation skill
        # and is not inferred from an outcome or a favourable initialization.
        "update_count": REQUIRED_UPDATES,
    }


def _masked_argmax(scores: np.ndarray, mask: np.ndarray) -> np.ndarray:
    values = np.asarray(scores, dtype=np.float64)
    legal = np.asarray(mask)
    if values.ndim != 2 or legal.dtype != np.bool_ or values.shape != legal.shape:
        raise RelationalValidationReportError("background scores and native mask are misaligned")
    if not np.all(np.isfinite(values)) or not np.all(np.any(legal, axis=1)):
        raise RelationalValidationReportError("background scores are nonfinite or have no legal action")
    return np.argmax(np.where(legal, values, -np.inf), axis=1).astype(np.int64)


def _background_metrics(
    *,
    source: RelationalZRC3Source,
    q3: np.ndarray,
    background: tuple[np.ndarray, np.ndarray],
) -> dict[str, object]:
    q1, q2 = background
    expected = (source.rows, ACTION_DIM)
    if np.asarray(q1).shape != expected or np.asarray(q2).shape != expected:
        raise RelationalValidationReportError("Q1/Q2 background surface shape disagrees with source")
    if not np.all(np.isfinite(q1)) or not np.all(np.isfinite(q2)):
        raise RelationalValidationReportError("Q1/Q2 background surface is nonfinite")
    mask = np.asarray(source.action_mask)
    base_action = _masked_argmax(np.asarray(q1) + np.asarray(q2), mask)
    learned_action = _masked_argmax(np.asarray(q1) + np.asarray(q2) + np.asarray(q3), mask)
    changed = learned_action != base_action
    rows = np.arange(source.rows, dtype=np.int64)
    supported = (
        np.asarray(source.positive_credit_compatible)[rows, learned_action]
        & (np.asarray(source.target_surface_bits)[rows, learned_action] > 0.0)
    )
    changed_count = int(np.count_nonzero(changed))
    supported_count = int(np.count_nonzero(changed & supported))
    positive_target_count = int(np.count_nonzero(changed & (np.asarray(source.target_surface_bits)[rows, learned_action] > 0.0)))
    return {
        "rows": source.rows,
        "background_action_count": int(np.count_nonzero(base_action != source.reference_actions)),
        "learned_action_count": int(np.count_nonzero(learned_action != source.reference_actions)),
        "changed_action_count": changed_count,
        "supported_positive_change_count": supported_count,
        "positive_target_change_count": positive_target_count,
        "positive_support_rate": float(supported_count / changed_count) if changed_count else 0.0,
        "has_change_exposure": changed_count > 0,
    }


def _gate_result(
    *,
    config: RelationalValidationConfig,
    reports: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    gate = config.gate_config
    if gate is None:
        return {
            "evaluated": False,
            "passed": False,
            "decision": "NO_GATE_CONFIG",
            "reason": "gate configuration was not supplied externally",
            "output_unit_mode": NORMALIZED_BITS_PER_KAPPA,
        }
    if len(reports) != EXPECTED_INITIALIZATION_COUNT:
        raise RelationalValidationReportError(
            f"frozen gate requires exactly {EXPECTED_INITIALIZATION_COUNT} initialization reports"
        )
    skill_values = [report.get("validation_skill") for report in reports]
    support_values = [report.get("positive_support_rate") for report in reports]
    exposure_values = [report.get("background_changed_action_count") for report in reports]
    supported_count_values = [report.get("supported_positive_change_count") for report in reports]
    if any(
        value is None
        for value in (*skill_values, *support_values, *exposure_values, *supported_count_values)
    ):
        return {
            "evaluated": False,
            "passed": False,
            "decision": "STOP_MISSING_AUTHENTICATED_Q1_Q2_ARRAYS",
            "reason": "positive-support gate requires external authenticated Q1/Q2 arrays",
            "required_updates": REQUIRED_UPDATES,
            "contract_sha256": config.contract_sha256,
            "output_unit_mode": NORMALIZED_BITS_PER_KAPPA,
        }
    skills = [float(value) for value in skill_values]
    exposures = [int(value) for value in exposure_values]
    supported_counts = [int(value) for value in supported_count_values]
    if any(value < 0 for value in exposures) or any(
        value < 0 or value > exposure
        for value, exposure in zip(supported_counts, exposures, strict=True)
    ):
        raise RelationalValidationReportError("validation support counts are inconsistent")
    support = [
        float(value / exposure) if exposure else 0.0
        for value, exposure in zip(supported_counts, exposures, strict=True)
    ]
    if any(
        float(reported) != recomputed
        for reported, recomputed in zip(support_values, support, strict=True)
    ):
        raise RelationalValidationReportError("validation support rate disagrees with raw counts")
    mean_skill = float(math.fsum(skills) / len(skills))
    mean_support = float(math.fsum(support) / len(support))
    pooled_exposure = int(sum(exposures))
    pooled_supported = int(sum(supported_counts))
    pooled_support = (
        float(pooled_supported / pooled_exposure) if pooled_exposure else 0.0
    )
    positive = int(sum(value > float(gate["min_mean_skill"]) for value in skills))
    exposed = int(sum(value > 0 for value in exposures))
    supported = int(sum(value > float(gate["min_supported_change_rate"]) for value in support))
    passed = bool(
        mean_skill > float(gate["min_mean_skill"])
        and positive >= int(gate["min_positive_initializations"])
        and pooled_exposure > 0
        and exposed >= 2
        and pooled_support > float(gate["min_supported_change_rate"])
        and supported >= int(gate["min_supported_initializations"])
    )
    return {
        "evaluated": True,
        "passed": passed,
        "decision": "PASS_LEARNER_GATE" if passed else "STOP_LEARNER_GATE",
        "reason": "all injected 100-update validation predicates passed" if passed else "one or more injected validation predicates failed",
        "contract_sha256": config.contract_sha256,
        "output_unit_mode": NORMALIZED_BITS_PER_KAPPA,
        "required_updates": REQUIRED_UPDATES,
        "initialization_count": len(reports),
        "mean_validation_skill": mean_skill,
        "positive_initializations": positive,
        "exposed_initializations": exposed,
        "pooled_student_change_exposure": pooled_exposure,
        "pooled_supported_positive_changes": pooled_supported,
        "pooled_supported_change_rate": pooled_support,
        "mean_positive_support_rate_diagnostic": mean_support,
        "supported_initializations": supported,
    }


def _load_panel(
    panel: VerifiedSourcePanel | None,
    *,
    train_source_paths: Sequence[str | Path] | None,
    validation_source_paths: Sequence[str | Path] | None,
    config: RelationalValidationConfig,
) -> VerifiedSourcePanel:
    if train_source_paths is not None or validation_source_paths is not None:
        if train_source_paths is None or validation_source_paths is None:
            raise RelationalValidationReportError("both TRAIN and VALIDATION source paths are required")
        try:
            return load_verified_source_panel(
                train_source_paths,
                validation_source_paths,
                train_worlds=config.train_worlds,
                validation_worlds=config.validation_worlds,
                lineages=tuple(lineage for _seed, lineage in config.initialization_lineages),
            )
        except Exception as error:
            if isinstance(error, RelationalValidationReportError):
                raise
            raise RelationalValidationReportError("source panel authentication failed") from error
    if not isinstance(panel, VerifiedSourcePanel):
        raise RelationalValidationReportError("an authenticated source panel or both source path lists is required")
    # Re-open every closure through the bridge reader before using its arrays.
    # This prevents a caller from mutating an in-memory panel after its initial
    # authentication and makes the source digest a file-backed receipt.
    try:
        return load_verified_source_panel(
            [closure.path for closure in panel.train],
            [closure.path for closure in panel.validation],
            train_worlds=config.train_worlds,
            validation_worlds=config.validation_worlds,
            lineages=tuple(lineage for _seed, lineage in config.initialization_lineages),
        )
    except Exception as error:
        if isinstance(error, RelationalValidationReportError):
            raise
        raise RelationalValidationReportError("source panel re-authentication failed") from error


def _write_surface_artifact(
    output_dir: Path,
    surfaces: Mapping[str, np.ndarray],
    identities: Mapping[str, tuple[int, int, int]],
    *,
    source_sha256: str,
) -> dict[str, object]:
    keys = tuple(sorted(surfaces))
    entries: list[dict[str, object]] = []
    arrays: dict[str, np.ndarray] = {}
    for key in keys:
        value = np.ascontiguousarray(surfaces[key])
        if key not in identities:
            raise RelationalValidationReportError("surface identity manifest is incomplete")
        if value.ndim != 2 or value.shape[1] != ACTION_DIM or not np.issubdtype(value.dtype, np.floating) or not np.all(np.isfinite(value)):
            raise RelationalValidationReportError("validation surface artifact is malformed")
        arrays[key] = value
        _split, world, lineage = identities[key]
        entries.append(
            {
                "key": key,
                "split": "VALIDATION",
                "world_seed": world,
                "lineage": lineage,
                "rows": int(value.shape[0]),
                "dtype": value.dtype.str,
                "shape": list(value.shape),
                "array_sha256": _array_sha256(value),
            }
        )
    npz_path = output_dir / SURFACE_NPZ_FILENAME
    if npz_path.exists() or npz_path.is_symlink():
        raise RelationalValidationReportError(f"refusing to overwrite {npz_path}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{SURFACE_NPZ_FILENAME}.", suffix=".tmp.npz", dir=output_dir
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        np.savez_compressed(temporary, **arrays)
        os.link(temporary, npz_path)
    except FileExistsError as error:
        raise RelationalValidationReportError(f"refusing to overwrite {npz_path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    npz_sha256 = _file_sha256(npz_path)
    body = {
        "schema": SURFACE_SCHEMA,
        "schema_version": SURFACE_VERSION,
        "source_panel_sha256": source_sha256,
        "npz_filename": SURFACE_NPZ_FILENAME,
        "npz_sha256": npz_sha256,
        "arrays": entries,
        "arrays_sha256": canonical_sha256(entries),
        "test_split_opened": False,
        "episode_training": False,
    }
    payload = {**body, "metadata_sha256": canonical_sha256(body)}
    metadata_path = output_dir / SURFACE_METADATA_FILENAME
    metadata_sha256 = _write_once(metadata_path, _canonical_bytes(payload))
    receipt_body = {
        "schema": SURFACE_SCHEMA,
        "metadata_sha256": metadata_sha256,
        "npz_sha256": npz_sha256,
        "arrays_sha256": body["arrays_sha256"],
        "metadata_self_sha256": payload["metadata_sha256"],
    }
    receipt = "".join(f"{field}={receipt_body[field]}\n" for field in receipt_body)
    receipt_path = output_dir / SURFACE_RECEIPT_FILENAME
    receipt_sha256 = _write_once(receipt_path, receipt.encode("ascii"))
    return {
        "schema": SURFACE_SCHEMA,
        "npz": SURFACE_NPZ_FILENAME,
        "metadata": SURFACE_METADATA_FILENAME,
        "receipt": SURFACE_RECEIPT_FILENAME,
        "npz_sha256": npz_sha256,
        "metadata_sha256": metadata_sha256,
        "arrays_sha256": body["arrays_sha256"],
        "metadata_self_sha256": payload["metadata_sha256"],
        "receipt_sha256": receipt_sha256,
        "entries": entries,
    }


def _background_metadata_body(
    *,
    seed: int,
    lineage: int,
    source_sha256: str,
    q1_checkpoint_sha256: str,
    q2_checkpoint_sha256: str,
    representation: str,
    npz_sha256: str,
    entries: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": BACKGROUND_SCHEMA,
        "schema_version": BACKGROUND_VERSION,
        "initialization_seed": seed,
        "lineage": lineage,
        "source_panel_sha256": source_sha256,
        "q1_checkpoint_sha256": q1_checkpoint_sha256,
        "q2_checkpoint_sha256": q2_checkpoint_sha256,
        "representation": representation,
        "npz_filename": BACKGROUND_NPZ_FILENAME,
        "npz_sha256": npz_sha256,
        "arrays": entries,
        "arrays_sha256": canonical_sha256(entries),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }


def write_background_surface_package(
    output_dir: str | Path,
    *,
    initialization_seed: int,
    lineage: int,
    source_sha256: str,
    q1_checkpoint_sha256: str,
    q2_checkpoint_sha256: str,
    arrays: Mapping[tuple[str, int, int], tuple[np.ndarray, np.ndarray]],
    representation: str = BACKGROUND_REPRESENTATION_SEPARATE,
) -> dict[str, str]:
    """Write an authenticated external Q1/Q2 validation-surface package.

    The package is an optional input to :func:`generate_validation_report`.
    It contains no target or learner output.  The report generator verifies
    its checkpoint bindings before using it for action-change/support metrics.
    """

    seed = _positive_int(initialization_seed, field="initialization_seed")
    line = _positive_int(lineage, field="lineage")
    source_digest = _digest(source_sha256, field="source_panel_sha256")
    q1_digest = _digest(q1_checkpoint_sha256, field="q1_checkpoint_sha256")
    q2_digest = _digest(q2_checkpoint_sha256, field="q2_checkpoint_sha256")
    if representation not in BACKGROUND_REPRESENTATIONS:
        raise RelationalValidationReportError("background representation is unknown")
    root = Path(output_dir)
    if root.exists() or root.is_symlink():
        raise RelationalValidationReportError(f"refusing to overwrite background package: {root}")
    if not arrays:
        raise RelationalValidationReportError("background package arrays must not be empty")
    root.mkdir(parents=True, exist_ok=False)
    npz_arrays: dict[str, np.ndarray] = {}
    entries: list[dict[str, object]] = []
    for index, identity in enumerate(sorted(arrays)):
        split, world, entry_lineage = identity
        if split != "VALIDATION" or entry_lineage != line:
            raise RelationalValidationReportError("background arrays must be VALIDATION and match lineage")
        q1, q2 = arrays[identity]
        left = np.ascontiguousarray(q1)
        right = np.ascontiguousarray(q2)
        if left.ndim != 2 or right.shape != left.shape or left.shape[1] != ACTION_DIM:
            raise RelationalValidationReportError("background Q1/Q2 arrays are malformed")
        if not np.issubdtype(left.dtype, np.floating) or not np.issubdtype(right.dtype, np.floating):
            raise RelationalValidationReportError("background Q1/Q2 arrays must be floating")
        if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
            raise RelationalValidationReportError("background Q1/Q2 arrays must be finite")
        if representation == BACKGROUND_REPRESENTATION_SUM_ZERO and np.any(right != 0.0):
            raise RelationalValidationReportError(
                "sum-with-zero background representation requires an exact zero right surface"
            )
        q1_key = f"q1_{index:04d}"
        q2_key = f"q2_{index:04d}"
        npz_arrays[q1_key] = left
        npz_arrays[q2_key] = right
        entries.append(
            {
                "split": split,
                "world_seed": int(world),
                "lineage": int(entry_lineage),
                "q1_key": q1_key,
                "q2_key": q2_key,
                "rows": int(left.shape[0]),
                "shape": list(left.shape),
                "q1_dtype": left.dtype.str,
                "q2_dtype": right.dtype.str,
                "q1_sha256": _array_sha256(left),
                "q2_sha256": _array_sha256(right),
            }
        )
    npz_path = root / BACKGROUND_NPZ_FILENAME
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{BACKGROUND_NPZ_FILENAME}.", suffix=".tmp.npz", dir=root
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        np.savez_compressed(temporary, **npz_arrays)
        os.link(temporary, npz_path)
    except FileExistsError as error:
        raise RelationalValidationReportError("refusing to overwrite background NPZ") from error
    finally:
        temporary.unlink(missing_ok=True)
    npz_sha256 = _file_sha256(npz_path)
    body = _background_metadata_body(
        seed=seed,
        lineage=line,
        source_sha256=source_digest,
        q1_checkpoint_sha256=q1_digest,
        q2_checkpoint_sha256=q2_digest,
        representation=representation,
        npz_sha256=npz_sha256,
        entries=entries,
    )
    metadata = {**body, "metadata_sha256": canonical_sha256(body)}
    metadata_path = root / BACKGROUND_METADATA_FILENAME
    metadata_sha256 = _write_once(metadata_path, _canonical_bytes(metadata))
    receipt_body = {
        "schema": BACKGROUND_SCHEMA,
        "metadata_sha256": metadata_sha256,
        "npz_sha256": npz_sha256,
        "arrays_sha256": body["arrays_sha256"],
        "metadata_self_sha256": metadata["metadata_sha256"],
    }
    receipt_path = root / BACKGROUND_RECEIPT_FILENAME
    receipt_sha256 = _write_once(
        receipt_path,
        "".join(f"{field}={receipt_body[field]}\n" for field in receipt_body).encode("ascii"),
    )
    return {
        "output_dir": str(root),
        "npz_sha256": npz_sha256,
        "metadata_sha256": metadata_sha256,
        "receipt_sha256": receipt_sha256,
    }


def write_background_surface_packages_from_harvests(
    *,
    panel: VerifiedSourcePanel,
    config: RelationalValidationConfig,
    output_root: str | Path,
) -> tuple[dict[int, Path], dict[str, object]]:
    """Convert authenticated validation Q1+Q2 sidecars into gate packages.

    The harvester deliberately stores only the detached sum actually used by
    the deployment argmax.  The legacy package reader consumes two arrays, so
    the sum is placed in the left slot and an exact-zero right slot is written
    under an explicit representation tag.  Their sum is therefore bitwise the
    harvested background; no Q surface is recomputed after outcomes open.
    """

    if not isinstance(panel, VerifiedSourcePanel):
        raise RelationalValidationReportError("panel must be VerifiedSourcePanel")
    if not isinstance(config, RelationalValidationConfig):
        raise RelationalValidationReportError("config must be RelationalValidationConfig")
    if panel.source_sha256 != config.source_panel_sha256:
        raise RelationalValidationReportError("source panel digest mismatch")
    root = Path(output_root)
    if root.exists() or root.is_symlink():
        raise RelationalValidationReportError(
            f"refusing to overwrite background panel: {root}"
        )
    root.mkdir(parents=True, exist_ok=False)
    try:
        from relational_source_harvester import read_harvest_closure
    except ImportError as error:  # pragma: no cover - packaging failure
        raise RelationalValidationReportError(
            "source harvester reader is unavailable"
        ) from error

    outputs: dict[int, Path] = {}
    entries: list[dict[str, object]] = []
    for seed, lineage in config.initialization_lineages:
        arrays: dict[tuple[str, int, int], tuple[np.ndarray, np.ndarray]] = {}
        for closure in sorted(panel.validation, key=lambda item: item.identity):
            if closure.source.lineage != lineage:
                continue
            try:
                harvest = read_harvest_closure(closure.path)
            except Exception as error:
                raise RelationalValidationReportError(
                    f"cannot authenticate validation harvest: {closure.path}"
                ) from error
            if harvest.source.arrays_sha256() != closure.source.arrays_sha256():
                raise RelationalValidationReportError(
                    "validation harvest/source-panel array digest mismatch"
                )
            metadata = harvest.metadata
            if metadata.get("contract_sha256") != config.contract_sha256:
                raise RelationalValidationReportError(
                    "validation harvest contract differs from gate config"
                )
            if metadata.get("code_manifest_sha256") != config.code_manifest_sha256:
                raise RelationalValidationReportError(
                    "validation harvest code manifest differs from gate config"
                )
            if metadata.get("q1_checkpoint_sha256") != config.q1_digest_map[lineage]:
                raise RelationalValidationReportError(
                    "validation harvest Q1 checkpoint differs from gate config"
                )
            if metadata.get("q2_checkpoint_sha256") != config.q2_digest_map[lineage]:
                raise RelationalValidationReportError(
                    "validation harvest Q2 checkpoint differs from gate config"
                )
            q12 = np.ascontiguousarray(harvest.sidecar["background_q12"])
            expected = (closure.source.rows, ACTION_DIM)
            if q12.shape != expected or not np.issubdtype(q12.dtype, np.floating) or not np.all(np.isfinite(q12)):
                raise RelationalValidationReportError(
                    "harvested validation Q1+Q2 background is malformed"
                )
            arrays[closure.identity] = (q12, np.zeros_like(q12))
        expected_identities = {
            ("VALIDATION", world, lineage) for world in config.validation_worlds
        }
        if set(arrays) != expected_identities:
            raise RelationalValidationReportError(
                "validation background sidecars do not form a complete world panel"
            )
        destination = root / f"init-{seed}"
        receipt = write_background_surface_package(
            destination,
            initialization_seed=seed,
            lineage=lineage,
            source_sha256=config.source_panel_sha256,
            q1_checkpoint_sha256=config.q1_digest_map[lineage],
            q2_checkpoint_sha256=config.q2_digest_map[lineage],
            arrays=arrays,
            representation=BACKGROUND_REPRESENTATION_SUM_ZERO,
        )
        outputs[seed] = destination
        entries.append(
            {
                "initialization_seed": seed,
                "lineage": lineage,
                "output_dir": str(destination),
                "metadata_sha256": receipt["metadata_sha256"],
                "npz_sha256": receipt["npz_sha256"],
                "receipt_sha256": receipt["receipt_sha256"],
            }
        )
    body: dict[str, object] = {
        "schema": BACKGROUND_PANEL_SCHEMA,
        "representation": BACKGROUND_REPRESENTATION_SUM_ZERO,
        "contract_sha256": config.contract_sha256,
        "source_panel_sha256": config.source_panel_sha256,
        "entries": entries,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    payload = {**body, "background_panel_sha256": canonical_sha256(body)}
    _write_once(root / BACKGROUND_PANEL_FILENAME, _canonical_bytes(payload))
    return outputs, payload


def _read_receipt(path: Path, *, schema: str, fields: Sequence[str]) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise RelationalValidationReportError(f"missing receipt: {path}")
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise RelationalValidationReportError("receipt is not ASCII") from error
    values: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            raise RelationalValidationReportError("receipt contains malformed line")
        key, value = line.split("=", 1)
        if key in values or key not in fields:
            raise RelationalValidationReportError("receipt contains unknown or duplicate field")
        values[key] = value
    if tuple(values) != tuple(fields):
        raise RelationalValidationReportError("receipt fields are incomplete or reordered")
    if values["schema"] != schema:
        raise RelationalValidationReportError("receipt schema is stale")
    for field in fields[1:]:
        _digest(values[field], field=f"receipt.{field}")
    return values


def read_background_surface_package(
    output_dir: str | Path,
    *,
    expected_source_sha256: str | None = None,
    expected_lineage: int | None = None,
    expected_q1_checkpoint_sha256: str | None = None,
    expected_q2_checkpoint_sha256: str | None = None,
) -> _BackgroundSurface:
    """Authenticate one optional external Q1/Q2 validation package."""

    root = Path(output_dir)
    metadata_path = root / BACKGROUND_METADATA_FILENAME
    metadata = _read_ascii_json(metadata_path, label="background metadata")
    receipt = _read_receipt(
        root / BACKGROUND_RECEIPT_FILENAME,
        schema=BACKGROUND_SCHEMA,
        fields=("schema", "metadata_sha256", "npz_sha256", "arrays_sha256", "metadata_self_sha256"),
    )
    supplied = _digest(metadata.get("metadata_sha256"), field="background metadata_sha256")
    body = {key: value for key, value in metadata.items() if key != "metadata_sha256"}
    if canonical_sha256(body) != supplied or receipt["metadata_self_sha256"] != supplied:
        raise RelationalValidationReportError("background metadata self-digest failed")
    if metadata.get("schema") != BACKGROUND_SCHEMA or metadata.get("schema_version") != BACKGROUND_VERSION:
        raise RelationalValidationReportError("background metadata schema is stale")
    seed = _positive_int(metadata.get("initialization_seed"), field="background.initialization_seed")
    lineage = _positive_int(metadata.get("lineage"), field="background.lineage")
    source_sha256 = _digest(metadata.get("source_panel_sha256"), field="background.source_panel_sha256")
    q1_digest = _digest(metadata.get("q1_checkpoint_sha256"), field="background.q1_checkpoint_sha256")
    q2_digest = _digest(metadata.get("q2_checkpoint_sha256"), field="background.q2_checkpoint_sha256")
    representation = str(metadata.get("representation"))
    if representation not in BACKGROUND_REPRESENTATIONS:
        raise RelationalValidationReportError("background representation is unknown")
    if expected_source_sha256 is not None and source_sha256 != expected_source_sha256:
        raise RelationalValidationReportError("background source digest mismatch")
    if expected_lineage is not None and lineage != expected_lineage:
        raise RelationalValidationReportError("background lineage mismatch")
    if expected_q1_checkpoint_sha256 is not None and q1_digest != expected_q1_checkpoint_sha256:
        raise RelationalValidationReportError("background Q1 checkpoint digest mismatch")
    if expected_q2_checkpoint_sha256 is not None and q2_digest != expected_q2_checkpoint_sha256:
        raise RelationalValidationReportError("background Q2 checkpoint digest mismatch")
    if metadata.get("npz_filename") != BACKGROUND_NPZ_FILENAME or metadata.get("test_split_opened") is not False or metadata.get("episode_training") is not False or metadata.get("learner_update") is not False:
        raise RelationalValidationReportError("background package crosses the source-only boundary")
    raw_entries = metadata.get("arrays")
    if not isinstance(raw_entries, list) or not raw_entries or canonical_sha256(raw_entries) != metadata.get("arrays_sha256"):
        raise RelationalValidationReportError("background array manifest is malformed")
    npz_path = root / BACKGROUND_NPZ_FILENAME
    npz_sha256 = _digest(metadata.get("npz_sha256"), field="background.npz_sha256")
    if _file_sha256(npz_path) != npz_sha256 or receipt["npz_sha256"] != npz_sha256:
        raise RelationalValidationReportError("background NPZ digest mismatch")
    if receipt["arrays_sha256"] != metadata.get("arrays_sha256"):
        raise RelationalValidationReportError("background array manifest digest mismatch")
    arrays: dict[tuple[str, int, int], tuple[np.ndarray, np.ndarray]] = {}
    try:
        with np.load(npz_path, allow_pickle=False) as loaded:
            expected_npz_keys: set[str] = set()
            for entry in raw_entries:
                if not isinstance(entry, Mapping) or set(entry) != {
                    "split", "world_seed", "lineage", "q1_key", "q2_key", "rows", "shape", "q1_dtype", "q2_dtype", "q1_sha256", "q2_sha256"
                }:
                    raise RelationalValidationReportError("background array manifest entry is malformed")
                identity = (
                    str(entry["split"]),
                    _positive_int(entry["world_seed"], field="background.world_seed"),
                    _positive_int(entry["lineage"], field="background.lineage"),
                )
                if identity in arrays or identity[0] != "VALIDATION" or identity[2] != lineage:
                    raise RelationalValidationReportError("background array identity is malformed")
                q1_key = str(entry["q1_key"])
                q2_key = str(entry["q2_key"])
                expected_npz_keys.update((q1_key, q2_key))
                left = np.array(loaded[q1_key], copy=True)
                right = np.array(loaded[q2_key], copy=True)
                if left.dtype.str != entry["q1_dtype"] or right.dtype.str != entry["q2_dtype"] or list(left.shape) != entry["shape"] or right.shape != left.shape or entry["rows"] != left.shape[0] or _array_sha256(left) != entry["q1_sha256"] or _array_sha256(right) != entry["q2_sha256"]:
                    raise RelationalValidationReportError("background array digest or shape mismatch")
                if not np.issubdtype(left.dtype, np.floating) or not np.issubdtype(right.dtype, np.floating) or not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
                    raise RelationalValidationReportError("background arrays are nonfinite or nonfloating")
                if representation == BACKGROUND_REPRESENTATION_SUM_ZERO and np.any(right != 0.0):
                    raise RelationalValidationReportError(
                        "sum-with-zero background representation has a nonzero right surface"
                    )
                arrays[identity] = (left, right)
            if set(loaded.files) != expected_npz_keys:
                raise RelationalValidationReportError("background NPZ contains unknown arrays")
    except (OSError, KeyError, ValueError, TypeError) as error:
        if isinstance(error, RelationalValidationReportError):
            raise
        raise RelationalValidationReportError("background NPZ is malformed") from error
    return _BackgroundSurface(
        seed=seed,
        lineage=lineage,
        source_sha256=source_sha256,
        q1_checkpoint_sha256=q1_digest,
        q2_checkpoint_sha256=q2_digest,
        representation=representation,
        arrays=arrays,
        metadata_sha256=_file_sha256(metadata_path),
        npz_sha256=npz_sha256,
    )


def _background_index(
    package: _BackgroundSurface,
    *,
    panel: VerifiedSourcePanel,
) -> dict[tuple[str, int, int], tuple[np.ndarray, np.ndarray]]:
    expected = {("VALIDATION", world, package.lineage) for world in panel.validation_worlds}
    if set(package.arrays) != expected:
        raise RelationalValidationReportError("background package is missing a validation world")
    for identity, (q1, q2) in package.arrays.items():
        source = panel.lookup(split="VALIDATION", world_seed=identity[1], lineage=package.lineage).source
        if q1.shape != (source.rows, ACTION_DIM) or q2.shape != (source.rows, ACTION_DIM):
            raise RelationalValidationReportError("background array shape disagrees with authenticated source")
    return package.arrays


def generate_validation_report(
    *,
    panel: VerifiedSourcePanel | None = None,
    train_source_paths: Sequence[str | Path] | None = None,
    validation_source_paths: Sequence[str | Path] | None = None,
    config: RelationalValidationConfig,
    initialization_outputs: Mapping[int, str | Path] | Sequence[str | Path],
    output_dir: str | Path,
    contract_path: str | Path | None = None,
    background_outputs: Mapping[int, str | Path] | None = None,
) -> dict[str, object]:
    """Generate one canonical validation report from authenticated artifacts."""

    if not isinstance(config, RelationalValidationConfig):
        raise RelationalValidationReportError("config must be RelationalValidationConfig")
    _verify_contract_file(contract_path, config.contract_sha256)
    authenticated_panel = _load_panel(
        panel,
        train_source_paths=train_source_paths,
        validation_source_paths=validation_source_paths,
        config=config,
    )
    if authenticated_panel.source_sha256 != config.source_panel_sha256:
        raise RelationalValidationReportError("source panel digest mismatch")
    for closure in (*authenticated_panel.train, *authenticated_panel.validation):
        if float(closure.source.kappa_bits).hex() != float(config.kappa_bits).hex():
            raise RelationalValidationReportError("source kappa disagrees with validation configuration")
    if isinstance(initialization_outputs, Mapping):
        outputs = {int(seed): Path(path) for seed, path in initialization_outputs.items()}
    else:
        values = tuple(Path(path) for path in initialization_outputs)
        if len(values) != len(config.initialization_seeds):
            raise RelationalValidationReportError("initialization output count disagrees with configuration")
        outputs = dict(zip(config.initialization_seeds, values, strict=True))
    if set(outputs) != set(config.initialization_seeds):
        raise RelationalValidationReportError("initialization output set disagrees with configuration")
    authenticated: list[_AuthenticatedInitialization] = []
    for seed, lineage in config.initialization_lineages:
        authenticated.append(
            _authenticate_initialization(
                output_dir=outputs[seed],
                seed=seed,
                lineage=lineage,
                panel=authenticated_panel,
                config=config,
            )
        )
    background: dict[int, _BackgroundSurface] = {}
    if background_outputs is not None:
        if set(int(seed) for seed in background_outputs) != set(config.initialization_seeds):
            raise RelationalValidationReportError("background output set disagrees with configuration")
        for seed, lineage in config.initialization_lineages:
            background[seed] = read_background_surface_package(
                background_outputs[seed],
                expected_source_sha256=config.source_panel_sha256,
                expected_lineage=lineage,
                expected_q1_checkpoint_sha256=config.q1_digest_map[lineage],
                expected_q2_checkpoint_sha256=config.q2_digest_map[lineage],
            )
            _background_index(background[seed], panel=authenticated_panel)
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise RelationalValidationReportError(f"refusing to overwrite validation report: {destination}")
    destination.mkdir(parents=True, exist_ok=False)
    per_initialization: list[dict[str, object]] = []
    surfaces: dict[str, np.ndarray] = {}
    surface_identities: dict[str, tuple[int, int, int]] = {}
    for item in authenticated:
        predictions_by_identity = _validate_prediction_entries(
            arrays=item.prediction_arrays,
            metadata=item.prediction_metadata,
            panel=authenticated_panel,
            lineage=item.lineage,
        )
        metrics = _validation_metrics(
            panel=authenticated_panel,
            lineage=item.lineage,
            predictions=predictions_by_identity,
            null_kinds=config.null_kinds,
            kappa_bits=float(config.kappa_bits),
            background=(background[item.seed].arrays if item.seed in background else None),
        )
        background_metrics: dict[str, object] | None = None
        if item.seed in background:
            by_world: dict[str, dict[str, object]] = {}
            for identity, q3 in sorted(predictions_by_identity.items()):
                by_world[str(identity[1])] = _background_metrics(
                    source=authenticated_panel.lookup(split="VALIDATION", world_seed=identity[1], lineage=item.lineage).source,
                    q3=q3,
                    background=background[item.seed].arrays[identity],
                )
            changed = sum(int(value["changed_action_count"]) for value in by_world.values())
            supported = sum(int(value["supported_positive_change_count"]) for value in by_world.values())
            background_metrics = {
                "worlds": by_world,
                "changed_action_count": changed,
                "supported_positive_change_count": supported,
                "positive_support_rate": float(supported / changed) if changed else 0.0,
                "has_change_exposure": changed > 0,
                "q1_checkpoint_sha256": background[item.seed].q1_checkpoint_sha256,
                "q2_checkpoint_sha256": background[item.seed].q2_checkpoint_sha256,
                "source_panel_sha256": background[item.seed].source_sha256,
            }
        # ``_validation_metrics`` computes the same values over the exact
        # source/prediction ordering used by the action agreement metrics.
        metrics["background_action_changes"] = background_metrics
        record = {
            "initialization_seed": item.seed,
            "lineage": item.lineage,
            "update_count": REQUIRED_UPDATES,
            "checkpoint_sha256": item.checkpoint_sha256,
            "checkpoint": {
                "path": str(item.checkpoint_path),
                "sha256": item.checkpoint_sha256,
            },
            "prediction": {
                "source_sha256": item.prediction_metadata["source_sha256"],
                "parameter_sha256": item.prediction_metadata["parameter_sha256"],
                "npz_sha256": item.prediction_metadata["npz_sha256"],
                "arrays_sha256": item.prediction_metadata["arrays_sha256"],
                "prediction_metadata_sha256": item.prediction_metadata["prediction_metadata_sha256"],
                "output_dir": str(item.output_dir),
            },
            "validation": metrics,
            "test_split_opened": False,
            "episode_training": False,
        }
        per_initialization.append(record)
        for index, identity in enumerate(sorted(predictions_by_identity)):
            key = f"init_{item.seed}_{index:04d}"
            surfaces[key] = np.ascontiguousarray(predictions_by_identity[identity])
            surface_identities[key] = identity
    surface_receipt = _write_surface_artifact(
        destination,
        surfaces,
        surface_identities,
        source_sha256=config.source_panel_sha256,
    )
    gate = _gate_result(config=config, reports=[record["validation"] for record in per_initialization])
    source_closures = []
    for closure in sorted((*authenticated_panel.train, *authenticated_panel.validation), key=lambda item: item.identity):
        entry = dict(closure.manifest_entry())
        entry["path"] = str(closure.path)
        source_closures.append(entry)
    report_body: dict[str, object] = {
        "schema": REPORT_SCHEMA,
        "schema_version": REPORT_VERSION,
        "status": "VALIDATION_GATE_EVALUATED" if gate["evaluated"] else "VALIDATION_REPORT_WRITTEN",
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": config.contract_sha256,
        "code_manifest_sha256": config.code_manifest_sha256,
        "source_panel_sha256": config.source_panel_sha256,
        "output_unit_mode": config.output_unit_mode,
        "config": config.as_dict(),
        "source_closures": source_closures,
        "background_outputs": (
            {str(seed): str(path) for seed, path in sorted(background_outputs.items())}
            if background_outputs is not None
            else None
        ),
        "validation_surfaces": surface_receipt,
        "initializations": per_initialization,
        "gate": gate,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    report_payload = {**report_body, "result_sha256": canonical_sha256(report_body)}
    result_path = destination / REPORT_FILENAME
    result_file_sha256 = _write_once(result_path, _canonical_bytes(report_payload))
    seal_body = {
        "schema": f"{REPORT_SCHEMA}-seal",
        "result_sha256": report_payload["result_sha256"],
        "result_file_sha256": result_file_sha256,
        "contract_sha256": config.contract_sha256,
        "source_panel_sha256": config.source_panel_sha256,
        "output_unit_mode": config.output_unit_mode,
        "surface_npz_sha256": surface_receipt["npz_sha256"],
        "surface_metadata_sha256": surface_receipt["metadata_sha256"],
        "test_split_opened": False,
        "episode_training": False,
    }
    seal_payload = {**seal_body, "seal_sha256": canonical_sha256(seal_body)}
    _write_once(destination / REPORT_SEAL_FILENAME, _canonical_bytes(seal_payload))
    return report_payload


def generate_validation_report_from_paths(
    *,
    train_source_paths: Sequence[str | Path],
    validation_source_paths: Sequence[str | Path],
    config: RelationalValidationConfig,
    initialization_outputs: Mapping[int, str | Path] | Sequence[str | Path],
    output_dir: str | Path,
    contract_path: str | Path | None = None,
    background_outputs: Mapping[int, str | Path] | None = None,
) -> dict[str, object]:
    """Path-oriented wrapper that authenticates the complete source panel."""

    return generate_validation_report(
        train_source_paths=train_source_paths,
        validation_source_paths=validation_source_paths,
        config=config,
        initialization_outputs=initialization_outputs,
        output_dir=output_dir,
        contract_path=contract_path,
        background_outputs=background_outputs,
    )


__all__ = [
    "BACKGROUND_METADATA_FILENAME",
    "BACKGROUND_NPZ_FILENAME",
    "BACKGROUND_PANEL_FILENAME",
    "BACKGROUND_PANEL_SCHEMA",
    "BACKGROUND_RECEIPT_FILENAME",
    "BACKGROUND_REPRESENTATION_SEPARATE",
    "BACKGROUND_REPRESENTATION_SUM_ZERO",
    "BACKGROUND_SCHEMA",
    "CLAIM_CEILING",
    "FROZEN_STATUS",
    "REPORT_FILENAME",
    "REPORT_SCHEMA",
    "REPORT_SEAL_FILENAME",
    "RelationalValidationConfig",
    "RelationalValidationReportError",
    "SURFACE_METADATA_FILENAME",
    "SURFACE_NPZ_FILENAME",
    "SURFACE_RECEIPT_FILENAME",
    "SURFACE_SCHEMA",
    "canonical_sha256",
    "generate_validation_report",
    "generate_validation_report_from_paths",
    "read_background_surface_package",
    "write_background_surface_package",
    "write_background_surface_packages_from_harvests",
]
