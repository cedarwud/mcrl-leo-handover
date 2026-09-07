"""Route-aware, no-EE E1 evaluation behind an explicit test-opening seam.

This file is intentionally outside the frozen fresh-source manifest.  It does
not import or read test artifacts at module import time.  Resampling identities
are derived from verified :class:`E1PairIndexRow` values; callers never supply
free-form cluster identifiers.
"""

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_e1_split import (
    E1PairIndexRow,
    E1SplitContractError,
    verify_full_sibling_groups,
)
from mcrl.runtime.ee_axis_e1_statistics import (
    ClusterBootstrapInterval,
    bootstrap_pair_skill,
)


class E1RouteAwareEvaluationError(MCRLContractError):
    """A route-aware E1 evaluation input violates its sealed contract."""


class E1InsufficientCoverageError(E1RouteAwareEvaluationError):
    """The sealed rows cannot support the preregistered sensitivity gate."""


class E1TestOpeningError(E1RouteAwareEvaluationError):
    """Public E1 authority does not permit the one-time test opening."""


@dataclass(frozen=True)
class E1PointGate:
    """One preregistered scalar point gate used by every C2 sensitivity."""

    comparison: str
    threshold: float

    def __post_init__(self) -> None:
        if self.comparison not in {"at_least", "at_most"}:
            raise E1RouteAwareEvaluationError(
                "point gate comparison must be at_least or at_most"
            )
        if isinstance(self.threshold, (bool, np.bool_)) or not isinstance(
            self.threshold, (int, float, np.number)
        ):
            raise E1RouteAwareEvaluationError("point gate threshold must be finite")
        converted = float(self.threshold)
        if not math.isfinite(converted):
            raise E1RouteAwareEvaluationError("point gate threshold must be finite")
        object.__setattr__(self, "threshold", converted)

    def passes(self, value: float) -> bool:
        if not math.isfinite(float(value)):
            return False
        if self.comparison == "at_least":
            return float(value) >= self.threshold
        return float(value) <= self.threshold


@dataclass(frozen=True)
class E1LeaveOneWorldAnchorOutEstimate:
    source_seed: int
    world_anchor_sha256: str
    estimate: float
    point_gate_passed: bool
    direction_matches_primary: bool


@dataclass(frozen=True)
class E1RoutePairSkillEvaluation:
    evaluator_file_sha256: str
    route: str
    resampling_identity: str
    primary: ClusterBootstrapInterval
    primary_point_gate_passed: bool
    anchor_balanced_estimate: float | None
    anchor_balanced_point_gate_passed: bool | None
    anchor_balanced_direction_matches_primary: bool | None
    leave_one_world_anchor_out: tuple[E1LeaveOneWorldAnchorOutEstimate, ...]


@dataclass(frozen=True)
class E1SelectedCheckpoint:
    initialization_seed: int
    path: Path
    file_sha256: str


@dataclass(frozen=True)
class E1TestDatasetAuthority:
    source_seed: int
    opening_dataset_sha256: str
    opening_file_sha256: str
    temporal_dataset_sha256: str
    temporal_file_sha256: str


@dataclass(frozen=True)
class E1TestOpeningPermit:
    """Opaque authorization produced without reading any test-only file."""

    source_root: Path
    ladder_root: Path
    source_receipt_file_sha256: str
    ladder_result_seal_file_sha256: str
    evaluator_file_sha256: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    selected_common_rung: int
    test_index_file_sha256: str
    test_source_seeds: tuple[int, int]
    datasets: tuple[E1TestDatasetAuthority, E1TestDatasetAuthority]
    selected_checkpoints: tuple[
        E1SelectedCheckpoint, E1SelectedCheckpoint, E1SelectedCheckpoint
    ]


@dataclass(frozen=True)
class E1OpenedTestDataset:
    source_seed: int
    opening_path: Path
    opening_dataset_sha256: str
    temporal_path: Path
    temporal_dataset_sha256: str


@dataclass(frozen=True)
class E1OpenedTestArtifacts:
    """Authenticated test paths exposed only by :func:`open_test_split`."""

    source_manifest_sha256: str
    checkpoint_sha256: str
    evaluator_file_sha256: str
    selected_common_rung: int
    selected_checkpoints: tuple[
        E1SelectedCheckpoint, E1SelectedCheckpoint, E1SelectedCheckpoint
    ]
    datasets: tuple[E1OpenedTestDataset, E1OpenedTestDataset]
    opening_receipt_path: Path
    opening_receipt_file_sha256: str
    test_split_opened: bool = True
    held_out_ee_evaluated: bool = False


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise E1TestOpeningError(f"{field} must be lowercase SHA-256")
    return value


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha256_file(path: Path, *, label: str) -> str:
    if path.is_symlink() or not path.is_file():
        raise E1TestOpeningError(f"{label} is missing, non-regular, or a symlink")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _evaluator_file_sha256() -> str:
    return _sha256_file(Path(__file__), label="route-aware evaluator")


def _read_canonical_json(path: Path, *, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise E1TestOpeningError(f"{label} is missing, non-regular, or a symlink")
    raw = path.read_bytes()
    try:
        payload = json.loads(
            raw.decode("ascii"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise E1TestOpeningError(f"{label} is invalid JSON") from error
    if not isinstance(payload, dict):
        raise E1TestOpeningError(f"{label} must be a JSON object")
    if raw != _canonical_bytes(payload) + b"\n":
        raise E1TestOpeningError(f"{label} is not canonical JSON")
    return payload


def _write_once_json(path: Path, payload: Mapping[str, Any]) -> str:
    parent = _regular_directory(path.parent, label="test-opening receipt parent")
    destination = parent / path.name
    if path.name in {"", ".", ".."} or destination.is_symlink():
        raise E1TestOpeningError("test-opening receipt path is invalid")
    encoded = _canonical_bytes(dict(payload)) + b"\n"
    try:
        with destination.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise E1TestOpeningError(
            "test-opening receipt already exists; test split may open only once"
        ) from error
    return hashlib.sha256(encoded).hexdigest()


def _regular_directory(path: Path, *, label: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise E1TestOpeningError(f"{label} must be a regular directory")
    return path.resolve(strict=True)


def _mapping(value: object, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise E1TestOpeningError(f"{field} must be an object")
    return value


def _test_seed_split(receipt: Mapping[str, Any]) -> tuple[int, int]:
    split_receipt = _mapping(receipt.get("split_receipt"), field="split_receipt")
    raw_split = _mapping(split_receipt.get("seed_split"), field="seed_split")
    normalized: dict[int, str] = {}
    for raw_seed, split in raw_split.items():
        if not isinstance(raw_seed, str) or not raw_seed.isdigit():
            raise E1TestOpeningError("seed_split keys must be decimal source seeds")
        seed = int(raw_seed)
        if str(seed) != raw_seed or split not in {"train", "validation", "test"}:
            raise E1TestOpeningError("source seed split is malformed")
        normalized[seed] = str(split)
    counts = {
        name: sum(split == name for split in normalized.values())
        for name in ("train", "validation", "test")
    }
    if counts != {"train": 3, "validation": 1, "test": 2}:
        raise E1TestOpeningError("source receipt is not the sealed 3/1/2 split")
    test_seeds = tuple(sorted(seed for seed, split in normalized.items() if split == "test"))
    return test_seeds  # type: ignore[return-value]


def _selected_checkpoints(
    *,
    ladder_root: Path,
    result: Mapping[str, Any],
    ladder_spec: Mapping[str, Any],
    selected_rung: int,
) -> tuple[E1SelectedCheckpoint, E1SelectedCheckpoint, E1SelectedCheckpoint]:
    raw_seeds = ladder_spec.get("initialization_seeds")
    if (
        not isinstance(raw_seeds, list)
        or len(raw_seeds) != 3
        or any(type(seed) is not int or seed < 0 for seed in raw_seeds)
        or len(set(raw_seeds)) != 3
    ):
        raise E1TestOpeningError("ladder authority has invalid initialization seeds")
    selected = _mapping(
        result.get("selected_checkpoint_files"), field="selected_checkpoint_files"
    )
    if set(selected) != {str(seed) for seed in raw_seeds}:
        raise E1TestOpeningError("selected checkpoint receipt is incomplete")
    run_root = _regular_directory(ladder_root / "run", label="ladder run root")
    checkpoint_root = _regular_directory(
        run_root / "checkpoints", label="ladder checkpoint root"
    )
    checkpoints: list[E1SelectedCheckpoint] = []
    for seed in sorted(raw_seeds):
        row = _mapping(selected[str(seed)], field=f"selected_checkpoint_files[{seed}]")
        if set(row) != {"path", "file_sha256"}:
            raise E1TestOpeningError("selected checkpoint row has unexpected fields")
        expected_relative = f"checkpoints/init-{seed}-rung-{selected_rung:06d}.pt"
        if row.get("path") != expected_relative:
            raise E1TestOpeningError("selected checkpoint path changed")
        expected_sha256 = _digest(
            row.get("file_sha256"), field=f"selected checkpoint {seed}"
        )
        path = checkpoint_root / f"init-{seed}-rung-{selected_rung:06d}.pt"
        try:
            if path.resolve(strict=True).parent != checkpoint_root:
                raise E1TestOpeningError("selected checkpoint escaped its directory")
        except OSError as error:
            raise E1TestOpeningError("selected checkpoint cannot be resolved") from error
        if _sha256_file(path, label=f"selected checkpoint {seed}") != expected_sha256:
            raise E1TestOpeningError("selected checkpoint bytes changed")
        checkpoints.append(
            E1SelectedCheckpoint(
                initialization_seed=seed,
                path=path,
                file_sha256=expected_sha256,
            )
        )
    return tuple(checkpoints)  # type: ignore[return-value]


def authorize_test_opening(
    *,
    source_root: str | Path,
    ladder_root: str | Path,
    expected_source_receipt_sha256: str,
    expected_ladder_result_seal_sha256: str,
) -> E1TestOpeningPermit:
    """Verify target-free authority without reading the test index or datasets."""

    source = _regular_directory(Path(source_root), label="source root")
    ladder = _regular_directory(Path(ladder_root), label="ladder root")
    expected_source = _digest(
        expected_source_receipt_sha256,
        field="expected_source_receipt_sha256",
    )
    expected_ladder_seal = _digest(
        expected_ladder_result_seal_sha256,
        field="expected_ladder_result_seal_sha256",
    )
    evaluator_file_sha256 = _evaluator_file_sha256()

    result_seal_path = ladder / "result-seal.json"
    if (
        _sha256_file(result_seal_path, label="ladder result seal")
        != expected_ladder_seal
    ):
        raise E1TestOpeningError("ladder result seal differs from external authority")
    result_seal = _read_canonical_json(
        result_seal_path, label="ladder result seal"
    )
    if set(result_seal) != {
        "schema",
        "result_file_sha256",
        "authority_sha256",
    } or result_seal.get("schema") != (
        "multi-catfish-mcrl-v03-e1-ladder-result-seal-v1"
    ):
        raise E1TestOpeningError("ladder result seal schema is invalid")
    sealed_result_sha256 = _digest(
        result_seal.get("result_file_sha256"), field="result_file_sha256"
    )
    sealed_authority_sha256 = _digest(
        result_seal.get("authority_sha256"), field="authority_sha256"
    )

    result_path = ladder / "result.json"
    if _sha256_file(result_path, label="ladder result") != sealed_result_sha256:
        raise E1TestOpeningError("ladder result differs from result seal")
    result = _read_canonical_json(result_path, label="ladder result")
    if (
        result.get("schema") != "multi-catfish-mcrl-v03-e1-ladder-result-v1"
        or result.get("status") != "PASS_VALIDATION_SELECTION_COMPLETE"
        or result.get("claim_ceiling") != "NO_EE_INSTRUMENT_VALIDITY_ONLY"
        or result.get("authority_sha256") != sealed_authority_sha256
        or result.get("test_split_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
    ):
        raise E1TestOpeningError("ladder result does not authorize test opening")
    selected_rung = result.get("selected_common_rung")
    if type(selected_rung) is not int or selected_rung < 0:
        raise E1TestOpeningError("selected common rung is invalid")

    authority = _read_canonical_json(
        ladder / "authority.json", label="ladder authority"
    )
    supplied_authority_sha256 = authority.get("authority_sha256")
    authority_body = dict(authority)
    authority_body.pop("authority_sha256", None)
    if (
        authority.get("schema")
        != "multi-catfish-mcrl-v03-e1-ladder-authority-v1"
        or authority.get("claim_ceiling") != "NO_EE_INSTRUMENT_VALIDITY_ONLY"
        or supplied_authority_sha256 != sealed_authority_sha256
        or hashlib.sha256(_canonical_bytes(authority_body)).hexdigest()
        != sealed_authority_sha256
        or authority.get("execution_device") != "cpu"
        or authority.get("test_split_opened") is not False
        or authority.get("held_out_ee_evaluated") is not False
    ):
        raise E1TestOpeningError("ladder authority is invalid or changed")
    ladder_spec = _mapping(authority.get("ladder_spec"), field="ladder_spec")
    rungs = ladder_spec.get("update_rungs")
    if rungs != [10, 100, 1_000, 10_000] or selected_rung not in rungs:
        raise E1TestOpeningError("selected rung is outside the sealed ladder")

    data_root = _regular_directory(
        source / "source-data", label="source-data root"
    )
    receipt_path = data_root / "receipt.json"
    if _sha256_file(receipt_path, label="source receipt") != expected_source:
        raise E1TestOpeningError("source receipt differs from external authority")
    receipt = _read_canonical_json(receipt_path, label="source receipt")
    if (
        receipt.get("schema")
        != "multi-catfish-mcrl-v03-e1-fresh-source-receipt-v1"
        or receipt.get("status") != "PASS"
        or receipt.get("claim_ceiling")
        != "FRESH_SOURCE_AND_INSTRUMENT_DATA_ONLY_NOT_EE_EFFICACY"
        or receipt.get("training") is not False
        or receipt.get("held_out_ee_evaluated") is not False
    ):
        raise E1TestOpeningError("source receipt does not authorize test opening")
    source_manifest_sha256 = _digest(
        receipt.get("source_manifest_sha256"), field="source_manifest_sha256"
    )
    checkpoint_sha256 = _digest(
        receipt.get("checkpoint_sha256"), field="checkpoint_sha256"
    )
    source_access = _mapping(
        authority.get("source_access_receipt"), field="source_access_receipt"
    )
    if (
        ladder_spec.get("source_receipt_file_sha256") != expected_source
        or source_access.get("source_receipt_file_sha256") != expected_source
        or source_access.get("test_dataset_paths_opened") != []
        or source_access.get("test_split_opened") is not False
        or ladder_spec.get("source_manifest_sha256") != source_manifest_sha256
        or authority.get("source_manifest_sha256") != source_manifest_sha256
        or ladder_spec.get("checkpoint_sha256") != checkpoint_sha256
    ):
        raise E1TestOpeningError("ladder and source authority disagree")

    test_seeds = _test_seed_split(receipt)
    test_index_file_sha256 = _digest(
        receipt.get("test_index_file_sha256"), field="test_index_file_sha256"
    )
    opening_dataset = _mapping(
        receipt.get("opening_dataset_sha256s"), field="opening_dataset_sha256s"
    )
    temporal_dataset = _mapping(
        receipt.get("temporal_dataset_sha256s"), field="temporal_dataset_sha256s"
    )
    opening_files = _mapping(
        receipt.get("opening_dataset_file_sha256s"),
        field="opening_dataset_file_sha256s",
    )
    temporal_files = _mapping(
        receipt.get("temporal_dataset_file_sha256s"),
        field="temporal_dataset_file_sha256s",
    )
    datasets = tuple(
        E1TestDatasetAuthority(
            source_seed=seed,
            opening_dataset_sha256=_digest(
                opening_dataset.get(str(seed)),
                field=f"opening_dataset_sha256s[{seed}]",
            ),
            opening_file_sha256=_digest(
                opening_files.get(str(seed)),
                field=f"opening_dataset_file_sha256s[{seed}]",
            ),
            temporal_dataset_sha256=_digest(
                temporal_dataset.get(str(seed)),
                field=f"temporal_dataset_sha256s[{seed}]",
            ),
            temporal_file_sha256=_digest(
                temporal_files.get(str(seed)),
                field=f"temporal_dataset_file_sha256s[{seed}]",
            ),
        )
        for seed in test_seeds
    )
    checkpoints = _selected_checkpoints(
        ladder_root=ladder,
        result=result,
        ladder_spec=ladder_spec,
        selected_rung=selected_rung,
    )
    return E1TestOpeningPermit(
        source_root=source.resolve(strict=True),
        ladder_root=ladder.resolve(strict=True),
        source_receipt_file_sha256=expected_source,
        ladder_result_seal_file_sha256=expected_ladder_seal,
        evaluator_file_sha256=evaluator_file_sha256,
        source_manifest_sha256=source_manifest_sha256,
        checkpoint_sha256=checkpoint_sha256,
        selected_common_rung=selected_rung,
        test_index_file_sha256=test_index_file_sha256,
        test_source_seeds=test_seeds,
        datasets=datasets,  # type: ignore[arg-type]
        selected_checkpoints=checkpoints,
    )


def _canonical_test_path(
    *, data_root: Path, raw: object, expected: str, file_sha256: str
) -> Path:
    if raw != expected:
        raise E1TestOpeningError("test dataset path changed")
    path = data_root / expected
    try:
        if path.resolve(strict=True).parent != data_root.resolve(strict=True):
            raise E1TestOpeningError("test dataset escaped source-data")
    except OSError as error:
        raise E1TestOpeningError("test dataset cannot be resolved") from error
    if _sha256_file(path, label=f"test dataset {expected}") != file_sha256:
        raise E1TestOpeningError("test dataset file bytes changed")
    return path


def open_test_split(permit: E1TestOpeningPermit) -> E1OpenedTestArtifacts:
    """Explicitly cross the test boundary after reauthorizing public receipts."""

    if not isinstance(permit, E1TestOpeningPermit):
        raise E1TestOpeningError(
            "open_test_split requires an E1TestOpeningPermit"
        )
    current = authorize_test_opening(
        source_root=permit.source_root,
        ladder_root=permit.ladder_root,
        expected_source_receipt_sha256=permit.source_receipt_file_sha256,
        expected_ladder_result_seal_sha256=permit.ladder_result_seal_file_sha256,
    )
    if current != permit:
        raise E1TestOpeningError("test-opening authority changed after authorization")

    receipt_path = permit.ladder_root / "test-opening-receipt.json"
    receipt_file_sha256 = _write_once_json(
        receipt_path,
        {
            "schema": "multi-catfish-mcrl-v03-e1-test-opening-receipt-v1",
            "source_receipt_file_sha256": permit.source_receipt_file_sha256,
            "ladder_result_seal_file_sha256": (
                permit.ladder_result_seal_file_sha256
            ),
            "evaluator_file_sha256": permit.evaluator_file_sha256,
            "source_manifest_sha256": permit.source_manifest_sha256,
            "checkpoint_sha256": permit.checkpoint_sha256,
            "selected_common_rung": permit.selected_common_rung,
            "test_source_seeds": list(permit.test_source_seeds),
            "selected_checkpoint_file_sha256s": {
                str(row.initialization_seed): row.file_sha256
                for row in permit.selected_checkpoints
            },
            "test_split_opened": True,
            "held_out_ee_evaluated": False,
        },
    )

    data_root = _regular_directory(
        permit.source_root / "source-data", label="source-data root"
    )
    index_path = data_root / "test-index.json"
    if _sha256_file(index_path, label="test index") != permit.test_index_file_sha256:
        raise E1TestOpeningError("test index differs from source receipt")
    index = _read_canonical_json(index_path, label="test index")
    expected_fields = {
        "schema",
        "source_manifest_sha256",
        "checkpoint_sha256",
        "seed_split",
        "datasets",
        "held_out_ee_evaluated",
        "may_open_only_after_selected_common_rung",
    }
    if (
        set(index) != expected_fields
        or index.get("schema")
        != "multi-catfish-mcrl-v03-e1-test-source-index-v1"
        or index.get("source_manifest_sha256") != permit.source_manifest_sha256
        or index.get("checkpoint_sha256") != permit.checkpoint_sha256
        or index.get("seed_split")
        != {str(seed): "test" for seed in permit.test_source_seeds}
        or index.get("held_out_ee_evaluated") is not False
        or index.get("may_open_only_after_selected_common_rung") is not True
    ):
        raise E1TestOpeningError("test index authority is invalid")
    raw_datasets = _mapping(index.get("datasets"), field="test index datasets")
    if set(raw_datasets) != {str(seed) for seed in permit.test_source_seeds}:
        raise E1TestOpeningError("test index dataset map is incomplete")

    opened: list[E1OpenedTestDataset] = []
    for authority in permit.datasets:
        seed = authority.source_seed
        row = _mapping(raw_datasets[str(seed)], field=f"test dataset {seed}")
        if set(row) != {
            "opening_path",
            "opening_dataset_sha256",
            "temporal_path",
            "temporal_dataset_sha256",
        }:
            raise E1TestOpeningError("test dataset index row has unexpected fields")
        if (
            row.get("opening_dataset_sha256")
            != authority.opening_dataset_sha256
            or row.get("temporal_dataset_sha256")
            != authority.temporal_dataset_sha256
        ):
            raise E1TestOpeningError("test dataset content digest changed")
        opening_path = _canonical_test_path(
            data_root=data_root,
            raw=row.get("opening_path"),
            expected=f"opening-{seed}.json",
            file_sha256=authority.opening_file_sha256,
        )
        temporal_path = _canonical_test_path(
            data_root=data_root,
            raw=row.get("temporal_path"),
            expected=f"temporal-{seed}.json",
            file_sha256=authority.temporal_file_sha256,
        )
        opened.append(
            E1OpenedTestDataset(
                source_seed=seed,
                opening_path=opening_path,
                opening_dataset_sha256=authority.opening_dataset_sha256,
                temporal_path=temporal_path,
                temporal_dataset_sha256=authority.temporal_dataset_sha256,
            )
        )
    return E1OpenedTestArtifacts(
        source_manifest_sha256=permit.source_manifest_sha256,
        checkpoint_sha256=permit.checkpoint_sha256,
        evaluator_file_sha256=permit.evaluator_file_sha256,
        selected_common_rung=permit.selected_common_rung,
        selected_checkpoints=permit.selected_checkpoints,
        datasets=tuple(opened),  # type: ignore[arg-type]
        opening_receipt_path=receipt_path,
        opening_receipt_file_sha256=receipt_file_sha256,
    )


def _identity_sha256(parts: tuple[object, ...]) -> str:
    encoded = json.dumps(
        parts,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _validated_metric_rows(
    index_rows: Sequence[E1PairIndexRow],
    model_absolute_errors: np.ndarray,
    baseline_absolute_errors: np.ndarray,
) -> tuple[tuple[E1PairIndexRow, ...], np.ndarray, np.ndarray, str]:
    rows = tuple(index_rows)
    if not rows or any(not isinstance(row, E1PairIndexRow) for row in rows):
        raise E1RouteAwareEvaluationError(
            "index_rows must be a nonempty sequence of E1PairIndexRow"
        )
    for row in rows:
        row.verify()
    routes = {row.route for row in rows}
    if len(routes) != 1:
        raise E1RouteAwareEvaluationError("one evaluation may contain exactly one route")
    route = next(iter(routes))
    model = np.asarray(model_absolute_errors, dtype=np.float64)
    baseline = np.asarray(baseline_absolute_errors, dtype=np.float64)
    if model.shape != (len(rows),) or baseline.shape != model.shape:
        raise E1RouteAwareEvaluationError(
            "absolute-error vectors must align exactly with sealed index rows"
        )
    if (
        not np.all(np.isfinite(model))
        or not np.all(np.isfinite(baseline))
        or np.any(model < 0.0)
        or np.any(baseline < 0.0)
    ):
        raise E1RouteAwareEvaluationError(
            "absolute-error vectors must be finite and nonnegative"
        )
    row_keys = [
        (
            row.route,
            row.source_seed,
            row.anchor_sha256,
            row.inference_anchor_sha256,
            row.focal_user,
            row.reference_action,
            row.candidate_action,
        )
        for row in rows
    ]
    if len(set(row_keys)) != len(row_keys):
        raise E1RouteAwareEvaluationError("sealed index rows contain a duplicate pair")
    return rows, model, baseline, route


def _inference_anchor_ids(rows: tuple[E1PairIndexRow, ...]) -> list[str]:
    return [
        _identity_sha256(
            ("inference-anchor", row.route, row.source_seed, row.inference_anchor_sha256)
        )
        for row in rows
    ]


def _c2_intervention_ids(rows: tuple[E1PairIndexRow, ...]) -> list[str]:
    identities = [
        (
            "intervention-cluster",
            row.route,
            row.source_seed,
            row.inference_anchor_sha256,
            row.focal_user,
        )
        for row in rows
    ]
    if len(set(identities)) != len(identities):
        raise E1RouteAwareEvaluationError(
            "C2 sealed index must contain one row per intervention cluster"
        )
    return [_identity_sha256(identity) for identity in identities]


def _pair_skill_point(model: np.ndarray, baseline: np.ndarray) -> float:
    denominator = float(np.sum(baseline))
    if denominator <= 0.0:
        raise E1RouteAwareEvaluationError(
            "action-only baseline has zero held-out error"
        )
    result = 1.0 - float(np.sum(model)) / denominator
    if not math.isfinite(result):
        raise E1RouteAwareEvaluationError("pair-skill estimate is non-finite")
    return result


def _direction(value: float) -> int:
    if value > 0.0:
        return 1
    if value < 0.0:
        return -1
    return 0


def _c2_sensitivities(
    *,
    rows: tuple[E1PairIndexRow, ...],
    model: np.ndarray,
    baseline: np.ndarray,
    primary_estimate: float,
    point_gate: E1PointGate,
) -> tuple[
    float,
    bool,
    tuple[E1LeaveOneWorldAnchorOutEstimate, ...],
]:
    anchor_rows: dict[tuple[int, str], list[int]] = {}
    for index, row in enumerate(rows):
        anchor_rows.setdefault(
            (row.source_seed, row.inference_anchor_sha256), []
        ).append(index)
    if len(anchor_rows) < 3:
        raise E1InsufficientCoverageError(
            "INSUFFICIENT_COVERAGE: C2 requires at least three world anchors"
        )
    if any(len(indices) > 5 for indices in anchor_rows.values()):
        raise E1InsufficientCoverageError(
            "INSUFFICIENT_COVERAGE: C2 permits at most five focal "
            "interventions per world anchor"
        )

    ordered = sorted(anchor_rows)
    anchor_model = np.asarray(
        [float(np.mean(model[anchor_rows[key]])) for key in ordered],
        dtype=np.float64,
    )
    anchor_baseline = np.asarray(
        [float(np.mean(baseline[anchor_rows[key]])) for key in ordered],
        dtype=np.float64,
    )
    balanced = _pair_skill_point(anchor_model, anchor_baseline)
    primary_direction = _direction(primary_estimate)
    balanced_direction_matches = (
        primary_direction != 0 and _direction(balanced) == primary_direction
    )
    balanced_gate_passed = point_gate.passes(balanced)
    if not balanced_gate_passed or not balanced_direction_matches:
        raise E1InsufficientCoverageError(
            "INSUFFICIENT_COVERAGE: C2 anchor-balanced estimate failed "
            "the primary point gate or changed direction"
        )

    leave_one: list[E1LeaveOneWorldAnchorOutEstimate] = []
    for source_seed, world_anchor in ordered:
        retained = np.ones(len(rows), dtype=np.bool_)
        retained[anchor_rows[(source_seed, world_anchor)]] = False
        estimate = _pair_skill_point(
            model[retained], baseline[retained]
        )
        gate_passed = point_gate.passes(estimate)
        direction_matches = (
            primary_direction != 0 and _direction(estimate) == primary_direction
        )
        leave_one.append(
            E1LeaveOneWorldAnchorOutEstimate(
                source_seed=source_seed,
                world_anchor_sha256=world_anchor,
                estimate=estimate,
                point_gate_passed=gate_passed,
                direction_matches_primary=direction_matches,
            )
        )
        if not gate_passed or not direction_matches:
            raise E1InsufficientCoverageError(
                "INSUFFICIENT_COVERAGE: C2 leave-one-world-anchor-out "
                f"estimate failed for {world_anchor}"
            )
    return balanced, balanced_direction_matches, tuple(leave_one)


def evaluate_route_pair_skill(
    *,
    index_rows: Sequence[E1PairIndexRow],
    model_absolute_errors: np.ndarray,
    baseline_absolute_errors: np.ndarray,
    point_gate: E1PointGate,
    replications: int,
    confidence: float,
    bootstrap_seed: int,
) -> E1RoutePairSkillEvaluation:
    """Evaluate route pair skill without accepting caller-defined clusters."""

    if not isinstance(point_gate, E1PointGate):
        raise E1RouteAwareEvaluationError("point_gate must be E1PointGate")
    rows, model, baseline, route = _validated_metric_rows(
        index_rows, model_absolute_errors, baseline_absolute_errors
    )
    if route in {"C1", "C3"}:
        try:
            verify_full_sibling_groups(rows, route=route)
        except E1SplitContractError as error:
            raise E1RouteAwareEvaluationError(str(error)) from error
        cluster_ids = _inference_anchor_ids(rows)
        resampling_identity = "inference_anchor"
    else:
        cluster_ids = _c2_intervention_ids(rows)
        resampling_identity = "intervention_cluster"
    primary = bootstrap_pair_skill(
        model_absolute_errors=model,
        baseline_absolute_errors=baseline,
        cluster_ids=cluster_ids,
        replications=replications,
        confidence=confidence,
        bootstrap_seed=bootstrap_seed,
    )
    balanced: float | None = None
    balanced_gate_passed: bool | None = None
    balanced_direction_matches: bool | None = None
    leave_one: tuple[E1LeaveOneWorldAnchorOutEstimate, ...] = ()
    if route == "C2":
        balanced, balanced_direction_matches, leave_one = _c2_sensitivities(
            rows=rows,
            model=model,
            baseline=baseline,
            primary_estimate=primary.estimate,
            point_gate=point_gate,
        )
        balanced_gate_passed = True
    return E1RoutePairSkillEvaluation(
        evaluator_file_sha256=_evaluator_file_sha256(),
        route=route,
        resampling_identity=resampling_identity,
        primary=primary,
        primary_point_gate_passed=point_gate.passes(primary.estimate),
        anchor_balanced_estimate=balanced,
        anchor_balanced_point_gate_passed=balanced_gate_passed,
        anchor_balanced_direction_matches_primary=balanced_direction_matches,
        leave_one_world_anchor_out=leave_one,
    )


__all__ = [
    "E1InsufficientCoverageError",
    "E1LeaveOneWorldAnchorOutEstimate",
    "E1OpenedTestArtifacts",
    "E1OpenedTestDataset",
    "E1PointGate",
    "E1RouteAwareEvaluationError",
    "E1RoutePairSkillEvaluation",
    "E1SelectedCheckpoint",
    "E1TestDatasetAuthority",
    "E1TestOpeningError",
    "E1TestOpeningPermit",
    "authorize_test_opening",
    "evaluate_route_pair_skill",
    "open_test_split",
]
