#!/usr/bin/env python3
"""Generate current V0.23 C1/C2 target datasets from sealed source plans.

This file is an orchestration seam, not a second implementation of either
target formula.  It authenticates the predecision capture and its write-once
materialization, replays only the named TRAIN world/anchor, and delegates
physical target production to the current opening and repriced OPS-3 adapters.

Importing this module is inert with respect to the simulator.  The real
loader is reached only by :func:`generate_targets` (or the CLI), after the
sealed inputs and fresh output boundary have been checked.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SRC = REPO / "src"
MATERIALIZER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v023-c1c2-neutral-materialization"
    / "materialize_v023_c1c2.py"
)
CAPTURE_BRIDGE_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v023-c1c2-predecision-capture"
    / "v023_c1c2_predecision_capture.py"
)
SOURCE_ADAPTER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v023-r6-fit-binding-fix"
    / "v023_lcsrs_source_adapter.py"
)
OPS3_PRODUCER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v023-r7-launch-ready"
    / "v023_lcsrs_source_adapter.py"
)
D40_ADAPTER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v023-c1c2-target-generation-launch"
    / "d40_checkpoint_runtime_adapter.py"
)
D40_CHECKPOINT_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v020-c3-source-audit"
    / "repriced-q1-q2-fit"
    / "lineage-2026092101"
    / "checkpoints"
    / "lineage-2026092101-q2init-2026108101-rung-003000.pt"
)
DEFAULT_USERS = 100
OPENING_SOURCE_POLICY_VERSION = 1
SCHEMA = "multi-catfish-mcrl-v023-c1c2-target-generation-v1"
SCHEDULE_SCHEMA = "multi-catfish-mcrl-v023-c1c2-target-schedule-v1"
OPS3_SELECTED_PAIR_SCHEMA = "multi-catfish-mcrl-v023-repriced-ops3-selected-pair-dataset-v1"
OPS3_TARGET_UNIT = "normalized-repriced-ops3-delta-over-kappa"
CLAIM_CEILING = (
    "TRAIN_PHYSICAL_TARGET_GENERATION_ONLY_NO_LEARNER_NO_EPISODE_TRAINING_"
    "NO_EFFICACY_NO_TEST"
)
TRAIN = "TRAIN"


class TargetGenerationError(RuntimeError):
    """A sealed source plan cannot be converted into current typed targets."""


def _load_module(name: str, path: Path) -> Any:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise TargetGenerationError(f"required module is missing or symlinked: {target}")
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise TargetGenerationError(f"cannot load module: {target}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        sys.modules.pop(name, None)
        raise TargetGenerationError(f"module import failed: {target}") from error
    return module


def _materializer() -> Any:
    name = "mcrl_v023_c1c2_target_materializer"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    return _load_module(name, MATERIALIZER_PATH)


def _capture_bridge() -> Any:
    name = "mcrl_v023_c1c2_target_capture_bridge"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    return _load_module(name, CAPTURE_BRIDGE_PATH)


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TargetGenerationError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _canonical_bytes(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            .encode("ascii")
        )
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise TargetGenerationError("value is not canonical finite JSON") from error


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise TargetGenerationError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _slot_table_payload(table: Any) -> dict[str, object]:
    """Serialize a live SlotTable exactly as the sealed capture does."""

    return {
        "norad_ids": [int(value) for value in np.asarray(table.norad_ids).tolist()],
        "cell_ids": [int(value) for value in np.asarray(table.cell_ids).tolist()],
        "mask": [bool(value) for value in np.asarray(table.mask).tolist()],
    }


def _manifest_entries(path: Path) -> dict[str, str]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise TargetGenerationError(f"materialization manifest is missing: {source}")
    entries: dict[str, str] = {}
    lines = source.read_text(encoding="ascii").splitlines()
    if not lines:
        raise TargetGenerationError("materialization manifest is empty")
    for line_number, line in enumerate(lines, start=1):
        if not line or "  " not in line:
            raise TargetGenerationError(
                f"materialization manifest line {line_number} is malformed"
            )
        digest, name = line.split("  ", 1)
        _digest(digest, field=f"manifest[{line_number}].digest")
        if not name or name in entries or "/" in name or name.startswith("."):
            raise TargetGenerationError(
                f"materialization manifest line {line_number} has an invalid name"
            )
        entries[name] = digest
    return entries


@dataclass(frozen=True)
class SealedInputs:
    """Validated capture/materialization pair handed to the replay layer."""

    bundle: Any
    c1_records: tuple[Any, ...]
    c1_record_by_anchor: Mapping[str, Any]
    c1_state_sha256_by_anchor: Mapping[str, str]
    c2_anchor_by_key: Mapping[tuple[str, int], Any]
    capture_path: Path
    materialization_dir: Path
    capture_sha256: str
    materialization_manifest_sha256: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    pool_sha256: str

    @property
    def c1_routes(self) -> Mapping[str, Any]:
        return {"informed": self.bundle.c1_informed, "neutral": self.bundle.c1_neutral}

    @property
    def c2_routes(self) -> Mapping[str, Any]:
        return {"informed": self.bundle.c2_informed, "neutral": self.bundle.c2_neutral}


def _expected_materialization_payloads(bundle: Any, materializer: Any) -> dict[str, dict[str, object]]:
    """Build the exact payloads written by the existing V2 materializer."""

    pool_id = bundle.pool_id
    pool_sha256 = bundle.pool_sha256
    provenance = dict(bundle.provenance)
    anchors = bundle.c2_informed.anchors
    # These are the materializer's canonical serializers, intentionally used
    # instead of a second decoder/serializer in this target seam.
    return {
        "c1-informed.json": materializer._c1_selection_payload(
            bundle.c1_informed, pool_id=pool_id, pool_sha256=pool_sha256
        ),
        "c1-neutral.json": materializer._c1_selection_payload(
            bundle.c1_neutral, pool_id=pool_id, pool_sha256=pool_sha256
        ),
        "c2-informed.json": materializer._c2_informed_payload(bundle.c2_informed),
        "c2-neutral.json": materializer._c2_selection_payload(
            bundle.c2_neutral,
            pool_id=pool_id,
            pool_sha256=pool_sha256,
            provenance=provenance,
            anchors=anchors,
            informed=False,
        ),
    }


def _expected_materialization_receipt(
    bundle: Any,
    route_hashes: Mapping[str, str],
    materializer: Any,
) -> dict[str, object]:
    return {
        "schema": materializer.OUTPUT_SCHEMA,
        "status": "MATERIALIZED_TRAIN_PREDECISION_ONLY",
        "claim_ceiling": materializer.CLAIM_CEILING,
        "split": TRAIN,
        "pool_id": bundle.pool_id,
        "pool_sha256": bundle.pool_sha256,
        "provenance": dict(bundle.provenance),
        "route_budgets": {
            "C1_informed": bundle.c1_informed.budget,
            "C1_neutral": bundle.c1_neutral.budget,
            "C2_informed": bundle.c2_informed.budget,
            "C2_neutral": bundle.c2_neutral.budget,
        },
        "route_rules": {
            "C1_informed": materializer.C1_INFORMED_SOURCE_RULE,
            "C1_neutral": materializer.C1_CLUSTER_NEUTRAL_SOURCE_RULE,
            "C2_informed": materializer.C2_INFORMED_SOURCE_RULE,
            "C2_neutral": materializer.C2_NEUTRAL_SOURCE_RULE,
        },
        "c1_cluster_match_audit": materializer._c1_cluster_match_audit(
            bundle.c1_informed,
            bundle.c1_neutral,
        ),
        "files": dict(route_hashes),
        "controls": {
            "simulator_run": False,
            "learner_update": False,
            "episode_training": False,
            "test_split_opened": False,
            "outcome_tuning": False,
            "head_drop": False,
            "source_alias": False,
            "shared_route_learner_budget_assumed": False,
        },
    }


def load_sealed_inputs(capture_path: Path, materialization_dir: Path) -> SealedInputs:
    """Authenticate both source stages before loading any simulator module."""

    materializer = _materializer()
    capture = Path(capture_path)
    materialization = Path(materialization_dir)
    try:
        payload = materializer.read_canonical_json(capture)
    except Exception as error:
        raise TargetGenerationError("capture is not canonical ASCII JSON") from error
    try:
        bundle = materializer.materialize_capture(payload)
        bundle.verify()
    except Exception as error:
        raise TargetGenerationError("sealed predecision capture failed typed verification") from error
    if payload.get("split") != TRAIN:
        raise TargetGenerationError("sealed capture is not TRAIN")
    if materialization.is_symlink() or not materialization.is_dir():
        raise TargetGenerationError(
            f"materialization directory must be a regular directory: {materialization}"
        )

    expected_payloads = _expected_materialization_payloads(bundle, materializer)
    expected_names = set(expected_payloads) | {"receipt.json"}
    manifest_path = materialization / "MANIFEST.sha256"
    entries = _manifest_entries(manifest_path)
    if set(entries) != expected_names:
        raise TargetGenerationError(
            "materialization manifest closure disagrees: "
            f"missing={sorted(expected_names - set(entries))}, "
            f"extra={sorted(set(entries) - expected_names)}"
        )
    route_hashes: dict[str, str] = {}
    for name, expected in expected_payloads.items():
        path = materialization / name
        actual_hash = _sha256_file(path)
        if actual_hash != entries[name]:
            raise TargetGenerationError(f"materialization hash drifted for {name}")
        expected_bytes = materializer.canonical_bytes(expected) + b"\n"
        if path.read_bytes() != expected_bytes:
            raise TargetGenerationError(
                f"materialization {name} is not the sealed source selection"
            )
        route_hashes[name] = actual_hash

    receipt_path = materialization / "receipt.json"
    receipt_hash = _sha256_file(receipt_path)
    if receipt_hash != entries["receipt.json"]:
        raise TargetGenerationError("materialization receipt hash drifted")
    expected_receipt = _expected_materialization_receipt(
        bundle, route_hashes, materializer
    )
    try:
        receipt = materializer.read_canonical_json(receipt_path)
    except Exception as error:
        raise TargetGenerationError("materialization receipt is not canonical ASCII JSON") from error
    if receipt != expected_receipt:
        raise TargetGenerationError("materialization receipt disagrees with its route files")

    provenance = dict(bundle.provenance)
    raw_records = payload.get("c1", {}).get("records") if isinstance(payload.get("c1"), dict) else None
    if not isinstance(raw_records, list) or not raw_records:
        raise TargetGenerationError("capture has no C1 records for replay binding")
    try:
        records = tuple(
            materializer._c1_record(item, provenance=provenance)
            for item in raw_records
        )
    except Exception as error:
        raise TargetGenerationError("capture C1 records failed typed replay binding") from error
    by_anchor = {str(record.anchor_sha256): record for record in records}
    if len(by_anchor) != len(records):
        raise TargetGenerationError("capture C1 anchor identities are not unique")
    state_sha256_by_anchor = {
        str(item["anchor_sha256"]): _digest(
            item["state_sha256"], field="c1 record state_sha256"
        )
        for item in raw_records
    }
    if set(state_sha256_by_anchor) != set(by_anchor):
        raise TargetGenerationError("capture C1 state-digest bindings are not unique")
    for selection in (bundle.c1_informed, bundle.c1_neutral):
        for opportunity in selection.opportunities:
            record = by_anchor.get(opportunity.anchor_sha256)
            if record is None:
                raise TargetGenerationError(
                    "C1 selected opportunity has no source-record replay binding"
                )
            if record.source_record_sha256 != opportunity.source_record_sha256:
                raise TargetGenerationError(
                    "C1 selected opportunity source-record digest disagrees"
                )
    anchors = {
        (anchor.anchor.anchor_sha256, int(anchor.anchor.focal_user)): anchor
        for anchor in bundle.c2_informed.anchors
    }
    if len(anchors) != len(bundle.c2_informed.anchors):
        raise TargetGenerationError("C2 authenticated anchors are not unique")
    for selection in (bundle.c2_informed, bundle.c2_neutral):
        for opportunity in selection.opportunities:
            if (opportunity.anchor_sha256, opportunity.focal_user) not in anchors:
                raise TargetGenerationError(
                    "C2 selected opportunity has no authenticated anchor binding"
                )
    if bundle.c1_informed.budget != bundle.c1_neutral.budget:
        raise TargetGenerationError("C1 informed/neutral budgets disagree")
    if bundle.c2_informed.budget != bundle.c2_neutral.budget:
        raise TargetGenerationError("C2 informed/neutral budgets disagree")
    return SealedInputs(
        bundle=bundle,
        c1_records=records,
        c1_record_by_anchor=by_anchor,
        c1_state_sha256_by_anchor=state_sha256_by_anchor,
        c2_anchor_by_key=anchors,
        capture_path=capture.resolve(),
        materialization_dir=materialization.resolve(),
        capture_sha256=_sha256_file(capture),
        materialization_manifest_sha256=_sha256_file(manifest_path),
        source_manifest_sha256=_digest(
            provenance["source_manifest_sha256"], field="source_manifest_sha256"
        ),
        checkpoint_sha256=_digest(
            provenance["checkpoint_sha256"], field="checkpoint_sha256"
        ),
        pool_sha256=_digest(bundle.pool_sha256, field="pool_sha256"),
    )


def _group_c1_by_world(sealed: SealedInputs, selection: Any) -> dict[int, tuple[Any, ...]]:
    groups: dict[int, list[Any]] = defaultdict(list)
    for opportunity in selection.opportunities:
        record = sealed.c1_record_by_anchor[opportunity.anchor_sha256]
        groups[int(record.source_seed)].append(opportunity)
    return {
        world: tuple(sorted(rows, key=lambda row: (row.step_index, row.focal_user, row.candidate_physical_key)))
        for world, rows in sorted(groups.items())
    }


def _group_c2_by_world(sealed: SealedInputs, selection: Any) -> dict[int, tuple[Any, ...]]:
    groups: dict[int, list[Any]] = defaultdict(list)
    for opportunity in selection.opportunities:
        anchor = sealed.c2_anchor_by_key[(opportunity.anchor_sha256, opportunity.focal_user)]
        if int(anchor.world_id) != int(anchor.source_seed):
            raise TargetGenerationError(
                "C2 world_id and source_seed disagree; refusing to replay a different world"
            )
        groups[int(anchor.source_seed)].append(opportunity)
    return {
        world: tuple(sorted(rows, key=lambda row: (row.step_index, row.focal_user, row.candidate_physical_key)))
        for world, rows in sorted(groups.items())
    }


def _schedule_key(mode: str, world: int) -> str:
    return f"{mode}:{int(world)}"


def _c1_schedule_row(sealed: SealedInputs, opportunity: Any, *, world: int) -> dict[str, object]:
    """Return the source-owned identity for one C1 target row."""

    record = sealed.c1_record_by_anchor[opportunity.anchor_sha256]
    return {
        "source_anchor_sha256": str(opportunity.anchor_sha256),
        "source_record_sha256": str(opportunity.source_record_sha256),
        "world": int(world),
        "step_index": int(opportunity.step_index),
        "focal_user": int(opportunity.focal_user),
        "reference_action": int(opportunity.reference_action),
        "candidate_action": int(opportunity.candidate_action),
        "candidate_physical_key": [
            int(opportunity.candidate_physical_key[0]),
            int(opportunity.candidate_physical_key[1]),
        ],
        "source_rule": str(opportunity.source_rule),
        "source_seed": int(record.source_seed),
    }


def _c2_schedule_row(opportunity: Any, *, world: int) -> dict[str, object]:
    """Return the source-owned identity for one C2 target row."""

    return {
        "source_anchor_sha256": str(opportunity.anchor_sha256),
        "world": int(world),
        "step_index": int(opportunity.step_index),
        "focal_user": int(opportunity.focal_user),
        "reference_action": int(opportunity.reference_action),
        "candidate_action": int(opportunity.candidate_action),
        "candidate_physical_key": [
            int(opportunity.candidate_physical_key[0]),
            int(opportunity.candidate_physical_key[1]),
        ],
        "source_rule": str(opportunity.source_rule),
    }


def build_schedule(
    sealed: SealedInputs,
    *,
    modes: Sequence[str] = ("informed", "neutral"),
    worlds: Sequence[int] | None = None,
) -> dict[str, dict[str, object]]:
    """Build the immutable mode-by-world work schedule before runtime setup.

    The schedule is derived from the authenticated source selections, not from
    output filenames.  A requested world may contain C1 rows, C2 rows, or both;
    an empty mode/world shard is rejected so the controller cannot silently
    omit work.
    """

    mode_values = tuple(str(value) for value in modes)
    if not mode_values or any(value not in ("informed", "neutral") for value in mode_values):
        raise TargetGenerationError("modes must contain informed and/or neutral")
    if len(set(mode_values)) != len(mode_values):
        raise TargetGenerationError("modes must not contain duplicates")
    if worlds is None:
        requested_worlds: tuple[int, ...] | None = None
    else:
        requested_worlds = tuple(worlds)
        if any(type(value) is not int for value in requested_worlds):
            raise TargetGenerationError("worlds must contain exact integers")
        if len(set(requested_worlds)) != len(requested_worlds):
            raise TargetGenerationError("worlds must not contain duplicates")
    grouped_c1 = {
        mode: _group_c1_by_world(sealed, sealed.c1_routes[mode]) for mode in mode_values
    }
    grouped_c2 = {
        mode: _group_c2_by_world(sealed, sealed.c2_routes[mode]) for mode in mode_values
    }
    schedule: dict[str, dict[str, object]] = {}
    for mode in mode_values:
        available = set(grouped_c1[mode]) | set(grouped_c2[mode])
        mode_worlds = (
            tuple(sorted(available))
            if requested_worlds is None
            else tuple(sorted(requested_worlds))
        )
        for world in mode_worlds:
            c1_rows = grouped_c1[mode].get(world, ())
            c2_rows = grouped_c2[mode].get(world, ())
            if not c1_rows and not c2_rows:
                raise TargetGenerationError(
                    f"mode/world shard {mode}:{world} has no selected rows"
                )
            schedule[_schedule_key(mode, world)] = {
                "mode": mode,
                "world": int(world),
                "C1": [
                    _c1_schedule_row(sealed, row, world=world) for row in c1_rows
                ],
                "C2": [_c2_schedule_row(row, world=world) for row in c2_rows],
            }
    return schedule


def schedule_sha256(schedule: Mapping[str, Mapping[str, object]]) -> str:
    """Hash a canonical schedule payload for cross-process merge binding."""

    payload = {"schema": SCHEDULE_SCHEMA, "shards": dict(schedule)}
    return _canonical_sha256(payload)


@dataclass(frozen=True)
class RuntimeModules:
    """The exact current production modules used by the real replay."""

    source: Any
    ops3_source: Any
    opening_runner: Any
    opening_dataset: Any
    opening_source: Any
    state: Any
    d40_adapter: Any


def _runtime_modules() -> RuntimeModules:
    for path in (REPO, SRC):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    source = _load_module("mcrl_v023_target_source_adapter", SOURCE_ADAPTER_PATH)
    # R7 is the declared exact producer for the repriced OPS-3 surface.  It
    # shares the frozen V0.20 Q1/Q2 source lineage, while its R7 runner itself
    # intentionally rejects the older sealed C1/C2 TRAIN worlds.  We therefore
    # authenticate those worlds through the sealed R6 source adapter and call
    # this producer directly; it opens no new world or policy route.
    ops3_source = _load_module("mcrl_v023_target_ops3_producer", OPS3_PRODUCER_PATH)
    d40_adapter = _load_module(
        "mcrl_v023_target_d40_checkpoint_adapter", D40_ADAPTER_PATH
    )
    import mcrl.runtime.ee_axis_opening_dataset as opening_dataset  # noqa: PLC0415
    import mcrl.runtime.ee_axis_opening_runner as opening_runner  # noqa: PLC0415
    import mcrl.runtime.ee_axis_opening_source as opening_source  # noqa: PLC0415
    import mcrl.runtime.ee_axis_state as state  # noqa: PLC0415
    return RuntimeModules(
        source=source,
        ops3_source=ops3_source,
        opening_runner=opening_runner,
        opening_dataset=opening_dataset,
        opening_source=opening_source,
        state=state,
        d40_adapter=d40_adapter,
    )


@dataclass(frozen=True)
class RuntimeContext:
    modules: RuntimeModules
    archive: Any
    trainer: Any
    checkpoint: Mapping[str, Any]
    v018: Any
    q1: Any
    q2: Any
    auth: Mapping[str, Any]
    source_family: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    model_digest: str
    lambda_bits_per_j: float
    kappa_bits: float
    interval_s: float
    users: int


def _prepare_runtime(
    sealed: SealedInputs,
    *,
    tle_root: Path,
    prereg: Path,
    manifest: Path,
    manifest_digest: Path,
    execution_addendum: Path,
    users: int,
    temporary: Path,
) -> RuntimeContext:
    modules = _runtime_modules()
    source = modules.source
    try:
        config = source.V023SourceAdapterConfig(
            tle_root=Path(tle_root).resolve(strict=False),
            prereg=Path(prereg).resolve(strict=False),
            manifest=Path(manifest).resolve(strict=False),
            manifest_digest=Path(manifest_digest).resolve(strict=False),
            execution_addendum=Path(execution_addendum).resolve(strict=False),
        )
        runtime = source.V023RuntimeSourceAdapter(config)
        v020, v018, q1, q2, auth, current_manifest = runtime._authenticate(
            expected_manifest_sha256=sealed.source_manifest_sha256
        )
    except Exception as error:
        raise TargetGenerationError("current V0.23 source authority authentication failed") from error
    if current_manifest != sealed.source_manifest_sha256:
        raise TargetGenerationError("current source manifest disagrees with sealed capture")
    try:
        record = v018._V015._V013.read_prereg(config.prereg)
        archive = v018._V015._V013.screen._frozen_archive(
            record, Path(tle_root), Path(temporary) / "frozen-tle"
        )
        checkpoint = modules.d40_adapter.authenticate_d40_checkpoint(
            D40_CHECKPOINT_PATH,
            expected_sha256=sealed.checkpoint_sha256,
        )
        trainer = modules.d40_adapter.D40CheckpointRuntimeAdapter(
            source_adapter=source,
            v018=v018,
            q1=q1,
            q2=q2,
            model_digest=source._model_digest(
                q1,
                q2,
                auth["q1_receipt"],
                auth["q2_receipt"],
            ),
            checkpoint_sha256=sealed.checkpoint_sha256,
        )
    except Exception as error:
        raise TargetGenerationError("current d40 TRAIN checkpoint adapter failed") from error
    checkpoint_sha256 = _digest(
        str(checkpoint["checkpoint_sha256"]), field="loaded checkpoint_sha256"
    )
    if checkpoint_sha256 != sealed.checkpoint_sha256:
        raise TargetGenerationError("loaded checkpoint disagrees with sealed capture")
    q1_receipt = auth["q1_receipt"]
    q2_receipt = auth["q2_receipt"]
    model_digest = source._model_digest(q1, q2, q1_receipt, q2_receipt)
    calibration_environment = v018._V015._V013.screen._make_environment(
        archive, users=int(users)
    )
    interval_s = float(
        calibration_environment.environment.driver.config.ephemeris.time_step_s
    )
    lambda_bits_per_j = float(source.LAMBDA_BITS_PER_J)
    kappa_bits = float(source.KAPPA_BITS)
    if (
        float(modules.ops3_source.LAMBDA_BITS_PER_J) != lambda_bits_per_j
        or float(modules.ops3_source.KAPPA_BITS) != kappa_bits
    ):
        raise TargetGenerationError("R7 OPS-3 producer constants disagree with sealed source")
    if lambda_bits_per_j <= 0.0 or kappa_bits <= 0.0 or interval_s <= 0.0:
        raise TargetGenerationError("current formula constants are not positive")
    return RuntimeContext(
        modules=modules,
        archive=archive,
        trainer=trainer,
        checkpoint=checkpoint,
        v018=v018,
        q1=q1,
        q2=q2,
        auth=auth,
        source_family=str(config.source_family),
        source_manifest_sha256=sealed.source_manifest_sha256,
        checkpoint_sha256=checkpoint_sha256,
        model_digest=model_digest,
        lambda_bits_per_j=lambda_bits_per_j,
        kappa_bits=kappa_bits,
        interval_s=interval_s,
        users=int(users),
    )


def _reset_world(
    ctx: RuntimeContext, world: int
) -> tuple[Any, np.random.Generator, Any, Any, Any, Any]:
    screen = ctx.v018._V015._V013.screen
    wrapped = screen._make_environment(ctx.archive, users=ctx.users)
    env_rng, mobility_rng, _action_rng, _control_rng = screen._evaluation_rngs(int(world))
    from mcrl.env.keyed_fading import KeyedFadingField  # noqa: PLC0415

    field = KeyedFadingField.from_components(ctx.source_family, int(world))
    if getattr(wrapped.environment, "_started", False):
        raise TargetGenerationError("world environment started before field binding")
    wrapped.environment._fading_field = field
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    return wrapped, env_rng, field, states, masks, observation


def _native_q12(ctx: RuntimeContext, step_env: Any, observation: Any) -> Mapping[str, Any]:
    return ctx.modules.ops3_source._native_q12_anchor(
        v018=ctx.v018,
        q1=ctx.q1,
        q2=ctx.q2,
        step_env=step_env,
        observation=observation,
        model_digest=ctx.model_digest,
    )


def _advance_main(
    ctx: RuntimeContext,
    wrapped: Any,
    env_rng: np.random.Generator,
    actions: np.ndarray,
) -> tuple[Any, Any, Any] | None:
    outcome = wrapped.step(np.asarray(actions, dtype=np.int64), env_rng)
    if outcome.done:
        return None
    observation = ctx.modules.source._step_result_observation(wrapped, outcome)
    return outcome.user_states, outcome.action_masks, observation


def _verify_c1_anchor(
    sealed: SealedInputs,
    opportunity: Any,
    record: Any,
    *,
    native: Any,
    observation: Any,
    reference: np.ndarray,
    materializer: Any,
) -> None:
    if int(record.step_index) != int(observation.step_index):
        raise TargetGenerationError("C1 replay reached the wrong step")
    captured_state_sha256 = sealed.c1_state_sha256_by_anchor.get(
        str(opportunity.anchor_sha256)
    )
    if captured_state_sha256 is None:
        raise TargetGenerationError("C1 replay has no captured state-digest binding")
    if str(native.state_sha256) != captured_state_sha256:
        raise TargetGenerationError("C1 replay state digest disagrees with capture")
    if not np.array_equal(reference, opportunity.reference_actions):
        raise TargetGenerationError("C1 replay Main action vector disagrees with capture")
    tables = tuple(observation.candidates.slot_tables)
    anchor_digest = materializer.c1_anchor_sha256(
        {
            "source_seed": int(record.source_seed),
            "step_index": int(observation.step_index),
            "state_sha256": str(native.state_sha256),
            "reference_actions": [int(value) for value in reference.tolist()],
            "slot_tables": [_slot_table_payload(table) for table in tables],
        }
    )
    if anchor_digest != opportunity.anchor_sha256:
        raise TargetGenerationError("C1 replay anchor digest disagrees with source plan")
    if not np.array_equal(
        np.asarray(tables[opportunity.focal_user].mask, dtype=np.bool_),
        np.asarray(opportunity.action_mask, dtype=np.bool_),
    ):
        raise TargetGenerationError("C1 replay focal action mask disagrees with source plan")


def _generate_c1_world(
    ctx: RuntimeContext,
    sealed: SealedInputs,
    selection: Any,
    *,
    world: int,
) -> tuple[Any, list[dict[str, object]]]:
    materializer = _materializer()
    grouped = _group_c1_by_world(sealed, selection)
    opportunities = grouped.get(int(world), ())
    if not opportunities:
        raise TargetGenerationError(f"C1 selection has no rows for world {world}")
    by_step: dict[int, list[Any]] = defaultdict(list)
    for row in opportunities:
        by_step[int(row.step_index)].append(row)
    wrapped, env_rng, field, states, masks, observation = _reset_world(ctx, int(world))
    results: list[Any] = []
    bindings: list[dict[str, object]] = []
    max_step = max(by_step)
    for _ in range(max_step + 1):
        native_data = _native_q12(ctx, wrapped.environment, observation)
        native = native_data["native"]
        reference = np.asarray(native_data["background"], dtype=np.int64)
        if int(observation.step_index) in by_step:
            for opportunity in by_step[int(observation.step_index)]:
                record = sealed.c1_record_by_anchor[opportunity.anchor_sha256]
                _verify_c1_anchor(
                    sealed,
                    opportunity,
                    record,
                    native=native,
                    observation=observation,
                    reference=reference,
                    materializer=materializer,
                )
                try:
                    state_observation = ctx.modules.state.encode_ee_axis_state(
                        wrapped.environment, observation
                    )
                    result = ctx.modules.opening_runner.materialize_opening_opportunity(
                        wrapped.environment,
                        observation=observation,
                        state_observation=state_observation,
                        opportunity=opportunity,
                        source_policy_version=OPENING_SOURCE_POLICY_VERSION,
                        source_manifest_sha256=ctx.source_manifest_sha256,
                        checkpoint_sha256=ctx.checkpoint_sha256,
                        common_random_field=field,
                        other_route_source_rule="c3-equal-budget-uniform-predecision-v1",
                        rng=env_rng,
                        lambda_bits_per_j=ctx.lambda_bits_per_j,
                        interval_s=ctx.interval_s,
                    )
                except Exception as error:
                    raise TargetGenerationError(
                        f"C1 opening target materialization failed at world={world} "
                        f"step={observation.step_index} user={opportunity.focal_user}"
                    ) from error
                results.append(result)
                bindings.append(
                    {
                        **_c1_schedule_row(sealed, opportunity, world=world),
                        "common_random_field_sha256": result.raw_pair.common_random_field_sha256,
                        "comparison_sha256": result.raw_pair.comparison_sha256,
                    }
                )
        if int(observation.step_index) == max_step:
            break
        following = _advance_main(ctx, wrapped, env_rng, reference)
        if following is None:
            raise TargetGenerationError("C1 replay terminated before its declared anchor")
        states, masks, observation = following
    if len(results) != len(opportunities):
        raise TargetGenerationError("C1 replay did not materialize every selected row")
    return ctx.modules.opening_dataset.EEAxisOpeningDataset.from_results(results), bindings


def _verify_c2_anchor(
    sealed: SealedInputs,
    anchor: Any,
    *,
    ctx: RuntimeContext,
    observation: Any,
    native: Any,
    reference: np.ndarray,
    previous_associations: Sequence[Any],
) -> None:
    bridge = _capture_bridge()
    focal = int(anchor.anchor.focal_user)
    if int(observation.step_index) != int(anchor.anchor.step_index):
        raise TargetGenerationError("C2 replay reached the wrong anchor step")
    if str(native.state_sha256) != str(anchor.state_sha256):
        raise TargetGenerationError("C2 replay state digest disagrees with capture")
    if int(reference[focal]) != int(anchor.anchor.reference_action):
        raise TargetGenerationError("C2 replay reference action disagrees with capture")
    provenance = getattr(observation, "observation_provenance", None)
    if provenance is None or str(provenance.content_digest) != str(anchor.observation_sha256):
        raise TargetGenerationError("C2 replay observation provenance disagrees with capture")
    departures = bridge.detect_physical_departures(
        reference,
        previous_associations,
        tuple(observation.candidates.slot_tables),
        step_index=int(observation.step_index),
    )
    departure = next((row for row in departures if row.focal_user == focal), None)
    if departure is None:
        raise TargetGenerationError("C2 replay no longer exposes the sealed departure")
    current_anchor = bridge.build_c2_anchor_payload(
        world_id=int(anchor.world_id),
        source_seed=int(anchor.source_seed),
        source_manifest_sha256=ctx.source_manifest_sha256,
        checkpoint_sha256=ctx.checkpoint_sha256,
        state_schema=str(native.schema),
        state_schema_sha256=str(native.schema_sha256),
        state_sha256=str(native.state_sha256),
        observation_sha256=str(provenance.content_digest),
        step_index=int(observation.step_index),
        focal_user=focal,
        reference_action=int(reference[focal]),
        incumbent_physical_key=departure.incumbent_physical_key,
        candidate_sinr=np.asarray(observation.candidate_sinr[focal], dtype=np.float64),
        slot_table=departure.slot_table,
    )
    if current_anchor["anchor_sha256"] != anchor.anchor.anchor_sha256:
        raise TargetGenerationError("C2 replay anchor digest disagrees with source plan")


def _ops3_schedule_sha256(
    *,
    native_data: Mapping[str, Any],
    source_anchor_sha256: str,
    selected_rows: Sequence[Any],
    mode: str,
) -> str:
    payload = {
        "schema": "multi-catfish-mcrl-v023-ops3-selected-pair-schedule-v1",
        "mode": str(mode),
        "source_anchor_sha256": str(source_anchor_sha256),
        "ops3_anchor_sha256": _digest(
            native_data["ops3_anchor_sha256"], field="OPS-3 anchor hash"
        ),
        "ops3_projection_sha256": _digest(
            native_data["ops3_projection_sha256"], field="OPS-3 projection hash"
        ),
        "scheduled_focal_users": sorted(int(row.focal_user) for row in selected_rows),
        "candidate_rows": [
            {
                "focal_user": int(row.focal_user),
                "candidate_physical_key": [
                    int(row.candidate_physical_key[0]),
                    int(row.candidate_physical_key[1]),
                ],
                "source_rule": str(row.source_rule),
            }
            for row in sorted(selected_rows, key=lambda row: (row.focal_user, row.candidate_physical_key))
        ],
    }
    return _canonical_sha256(payload)


def _ops3_selected_pair_record(
    opportunity: Any,
    *,
    world: int,
    mode: str,
    native_data: Mapping[str, Any],
    schedule_sha256: str,
) -> dict[str, object]:
    """Bind one sealed C2 selection to the authoritative repriced OPS-3 row.

    ``target_values`` returned by ``_repriced_ops3_context`` are already
    centered and divided by kappa.  The selected-pair label below is therefore
    a direct subtraction in that authenticated normalized unit: no second
    kappa division is valid.
    """

    focal = int(opportunity.focal_user)
    candidate = int(opportunity.candidate_action)
    reference = int(opportunity.reference_action)
    masks = np.asarray(native_data["masks"], dtype=np.bool_)
    context = native_data.get("q2_context")
    if not isinstance(context, Mapping):
        raise TargetGenerationError("OPS-3 q2_context is missing")
    state = np.asarray(context.get("state_matrix"), dtype=np.float32)
    targets = np.asarray(context.get("target_values"), dtype=np.float64)
    features = np.asarray(context.get("features"), dtype=np.float64)
    persistence = np.asarray(context.get("persistence"), dtype=np.float64)
    rates = np.asarray(context.get("rate_bps"), dtype=np.float64)
    powers = np.asarray(context.get("marginal_power_w"), dtype=np.float64)
    required = np.asarray(context.get("required_power_w"), dtype=np.float64)
    if (
        masks.ndim != 2
        or not (0 <= focal < masks.shape[0])
        or state.ndim != 2
        or state.shape[0] != masks.shape[0]
        or targets.shape != masks.shape
        or features.shape != (masks.shape[0], masks.shape[1], 16)
        or persistence.ndim != 3
        or persistence.shape[0] != masks.shape[0]
        or persistence.shape[1] != 3
        or persistence.shape[2] != masks.shape[1]
        or rates.shape != persistence.shape
        or powers.shape != persistence.shape
        or required.shape != persistence.shape
    ):
        raise TargetGenerationError("OPS-3 selected-pair context shape drifted")
    if not np.array_equal(
        state,
        features.astype(np.float32).transpose(0, 2, 1).reshape(
            masks.shape[0], -1
        ),
    ):
        raise TargetGenerationError("OPS-3 selected-pair state is not its target-free feature surface")
    action_count = masks.shape[1]
    if not (0 <= candidate < action_count and 0 <= reference < action_count):
        raise TargetGenerationError("OPS-3 selected-pair action is out of range")
    if not bool(masks[focal, candidate]):
        raise TargetGenerationError("OPS-3 selected-pair candidate action is illegal")
    if not bool(masks[focal, reference]):
        raise TargetGenerationError("OPS-3 selected-pair reference action is illegal")
    if not all(np.all(np.isfinite(value)) for value in (state, targets, features, persistence, rates, powers, required)):
        raise TargetGenerationError("OPS-3 selected-pair context is non-finite")
    horizon = context.get("horizon")
    if type(horizon) is not int or not 0 <= horizon <= persistence.shape[1]:
        raise TargetGenerationError("OPS-3 selected-pair horizon drifted")
    if horizon < persistence.shape[1] and any(
        np.any(value[focal, horizon:] != 0.0)
        for value in (persistence, rates, powers, required)
    ):
        raise TargetGenerationError("OPS-3 selected-pair leaks beyond terminal truncation")
    q1_reference = np.asarray(native_data.get("q1_reference"), dtype=np.int64)
    if q1_reference.shape != (masks.shape[0],):
        raise TargetGenerationError("OPS-3 Q1 reference shape drifted")
    provenance = {
        name: _digest(native_data.get(name), field=f"OPS-3 {name}")
        for name in (
            "ops3_anchor_sha256",
            "ops3_tracker_seed_sha256",
            "ops3_projection_sha256",
        )
    }
    for name in ("ops3_future_d2_indices", "ops3_sample_times_utc", "ops3_offset_times_utc"):
        value = native_data.get(name)
        if not isinstance(value, list):
            raise TargetGenerationError(f"OPS-3 {name} is malformed")
        provenance[name] = list(value)
    reference_value = float(targets[focal, reference])
    candidate_value = float(targets[focal, candidate])
    return {
        "schema": OPS3_SELECTED_PAIR_SCHEMA,
        "world": int(world),
        "mode": str(mode),
        "source_anchor_sha256": _digest(opportunity.anchor_sha256, field="source anchor hash"),
        "step_index": int(opportunity.step_index),
        "focal_user": focal,
        "reference_action": reference,
        "candidate_action": candidate,
        "candidate_physical_key": [
            int(opportunity.candidate_physical_key[0]),
            int(opportunity.candidate_physical_key[1]),
        ],
        "source_rule": str(opportunity.source_rule),
        "schedule_sha256": _digest(schedule_sha256, field="OPS-3 selected-pair schedule hash"),
        "target_unit": OPS3_TARGET_UNIT,
        "target_reference_value": reference_value,
        "target_candidate_value": candidate_value,
        "target_delta": candidate_value - reference_value,
        "q1_reference_action": int(q1_reference[focal]),
        "action_mask": [bool(value) for value in masks[focal].tolist()],
        "q2_state": [float(value) for value in state[focal].tolist()],
        "q2_features": [[float(value) for value in row] for row in features[focal].tolist()],
        "persistence": [[float(value) for value in row] for row in persistence[focal].tolist()],
        "rate_bps": [[float(value) for value in row] for row in rates[focal].tolist()],
        "marginal_power_w": [[float(value) for value in row] for row in powers[focal].tolist()],
        "required_power_w": [[float(value) for value in row] for row in required[focal].tolist()],
        "horizon": int(horizon),
        "provenance": provenance,
    }


def _generate_c2_world(
    ctx: RuntimeContext,
    sealed: SealedInputs,
    selection: Any,
    *,
    world: int,
    mode: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    grouped = _group_c2_by_world(sealed, selection)
    opportunities = grouped.get(int(world), ())
    if not opportunities:
        raise TargetGenerationError(f"C2 selection has no rows for world {world}")
    by_step: dict[int, list[Any]] = defaultdict(list)
    for row in opportunities:
        by_step[int(row.step_index)].append(row)
    wrapped, env_rng, _field, states, masks, observation = _reset_world(ctx, int(world))
    rows: list[dict[str, object]] = []
    bindings: list[dict[str, object]] = []
    max_step = max(by_step)
    for _ in range(max_step + 1):
        native_data = _native_q12(ctx, wrapped.environment, observation)
        native = native_data["native"]
        reference = np.asarray(native_data["background"], dtype=np.int64)
        current_step = int(observation.step_index)
        if current_step in by_step:
            rows_at_step = by_step[current_step]
            for opportunity in rows_at_step:
                anchor = sealed.c2_anchor_by_key[(opportunity.anchor_sha256, opportunity.focal_user)]
                _verify_c2_anchor(
                    sealed,
                    anchor,
                    ctx=ctx,
                    observation=observation,
                    native=native,
                    reference=reference,
                    previous_associations=tuple(
                        getattr(wrapped.environment, "_previous_association", ())
                    ),
                )
                try:
                    schedule = _ops3_schedule_sha256(
                        native_data=native_data,
                        source_anchor_sha256=opportunity.anchor_sha256,
                        selected_rows=rows_at_step,
                        mode=mode,
                    )
                    selected = _ops3_selected_pair_record(
                        opportunity,
                        world=world,
                        mode=mode,
                        native_data=native_data,
                        schedule_sha256=schedule,
                    )
                except TargetGenerationError:
                    raise
                except Exception as error:
                    raise TargetGenerationError(
                        f"C2 OPS-3 target materialization failed at world={world} "
                        f"step={current_step} user={opportunity.focal_user}"
                    ) from error
                rows.append(selected)
                bindings.append(
                    {
                        **_c2_schedule_row(opportunity, world=world),
                        "schedule_sha256": schedule,
                        "ops3_anchor_sha256": selected["provenance"]["ops3_anchor_sha256"],
                        "ops3_projection_sha256": selected["provenance"]["ops3_projection_sha256"],
                        "target_delta": selected["target_delta"],
                        "target_unit": OPS3_TARGET_UNIT,
                    }
                )
        if current_step == max_step:
            break
        following = _advance_main(ctx, wrapped, env_rng, reference)
        if following is None:
            raise TargetGenerationError("C2 replay terminated before its declared anchor")
        states, masks, observation = following
    if len(rows) != len(opportunities):
        raise TargetGenerationError("C2 replay did not materialize every selected row")
    dataset = {
        "schema": OPS3_SELECTED_PAIR_SCHEMA,
        "source_manifest_sha256": ctx.source_manifest_sha256,
        "checkpoint_sha256": ctx.checkpoint_sha256,
        "lambda_bits_per_j": float(ctx.lambda_bits_per_j).hex(),
        "kappa_bits": float(ctx.kappa_bits).hex(),
        "target_unit": OPS3_TARGET_UNIT,
        "rows": rows,
    }
    return dataset, bindings


def _write_once_json(path: Path, payload: Mapping[str, object]) -> str:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise TargetGenerationError(f"refusing to overwrite output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_bytes(payload) + b"\n"
    with target.open("xb") as handle:
        handle.write(encoded)
    return hashlib.sha256(encoded).hexdigest()


def _row_count(dataset: object) -> int:
    rows: Any
    if isinstance(dataset, Mapping):
        if "rows" not in dataset:
            raise TargetGenerationError("mapping dataset is missing required 'rows'")
        rows = dataset["rows"]
    else:
        try:
            rows = getattr(dataset, "rows")
        except AttributeError as error:
            raise TargetGenerationError(
                "object dataset is missing required 'rows'"
            ) from error
    try:
        return len(rows)
    except TypeError as error:
        raise TargetGenerationError("dataset 'rows' must be sized") from error


def _output_code_closure() -> dict[str, str]:
    """Return the exact code/data closure declared by every target receipt.

    C2 is consumed from the R7 repriced OPS-3 adapter, not from the old
    Temporal-Fork backend.  Include the producer and the authenticated D40
    checkpoint adapter/data pair so a sealed output remains independently
    traceable even after it leaves the launcher directory.
    """

    closure_paths = [
        Path(__file__),
        MATERIALIZER_PATH,
        CAPTURE_BRIDGE_PATH,
        SOURCE_ADAPTER_PATH,
        OPS3_PRODUCER_PATH,
        D40_ADAPTER_PATH,
        D40_CHECKPOINT_PATH,
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_opening_runner.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_opening_source.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_opening_dataset.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3_live.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_v014_q2_state.py",
    ]
    return {
        str(path.resolve().relative_to(REPO)): _sha256_file(path)
        for path in sorted(set(closure_paths), key=lambda value: str(value))
    }


def _write_outputs(
    output: Path,
    *,
    sealed: SealedInputs,
    ctx: RuntimeContext,
    schedule: Mapping[str, Mapping[str, object]],
    c1_datasets: Mapping[tuple[str, int], Any],
    c2_datasets: Mapping[tuple[str, int], Any],
    c1_bindings: Sequence[Mapping[str, object]],
    c2_bindings: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    destination = Path(output)
    if destination.exists() or destination.is_symlink():
        raise TargetGenerationError(f"refusing to overwrite target output root: {destination}")
    destination.mkdir(parents=True)
    files: dict[str, str] = {}
    dataset_meta: dict[str, object] = {"C1": {}, "C2": {}}
    for (mode, world), dataset in sorted(c1_datasets.items()):
        name = f"c1-{mode}-world-{world}.json"
        path = destination / name
        ctx.modules.opening_dataset.write_opening_dataset(path, dataset)
        files[name] = _sha256_file(path)
        dataset_meta["C1"][f"{mode}:{world}"] = {
            "path": name,
            "rows": _row_count(dataset),
            "source_manifest_sha256": dataset.source_manifest_sha256,
            "common_random_field_sha256": dataset.common_random_field_sha256,
            "dataset_sha256": dataset.verify(),
        }
    for (mode, world), dataset in sorted(c2_datasets.items()):
        name = f"c2-{mode}-world-{world}.json"
        path = destination / name
        payload = dict(dataset)
        dataset_digest = _canonical_sha256(payload)
        _write_once_json(path, payload)
        files[name] = _sha256_file(path)
        dataset_meta["C2"][f"{mode}:{world}"] = {
            "path": name,
            "schema": OPS3_SELECTED_PAIR_SCHEMA,
            "rows": _row_count(dataset),
            "source_manifest_sha256": dataset["source_manifest_sha256"],
            "dataset_sha256": dataset_digest,
        }
    closure = _output_code_closure()
    receipt: dict[str, object] = {
        "schema": SCHEMA,
        "status": "TARGETS_MATERIALIZED_TRAIN",
        "claim_ceiling": CLAIM_CEILING,
        "training_or_replay_write": False,
        "learner_update": False,
        "test_split_opened": False,
        "source": {
            "capture_path": str(sealed.capture_path),
            "capture_sha256": sealed.capture_sha256,
            "materialization_dir": str(sealed.materialization_dir),
            "materialization_manifest_sha256": sealed.materialization_manifest_sha256,
            "pool_sha256": sealed.pool_sha256,
            "source_family": ctx.source_family,
            "source_manifest_sha256": sealed.source_manifest_sha256,
            "checkpoint_sha256": sealed.checkpoint_sha256,
        },
        "formula_constants": {
            "lambda_bits_per_j": float(ctx.lambda_bits_per_j).hex(),
            "kappa_bits": float(ctx.kappa_bits).hex(),
            "interval_s": float(ctx.interval_s).hex(),
            "c2_schema": OPS3_SELECTED_PAIR_SCHEMA,
            "c2_target_unit": OPS3_TARGET_UNIT,
            "c2_horizon_steps": 3,
            "c2_terminal_rule": "PREDECLARED_H_T_TRUNCATION_TERMINAL_ZERO",
        },
        "datasets": dataset_meta,
        "schedule": {
            "schema": SCHEDULE_SCHEMA,
            "shards": {
                key: dict(schedule[key]) for key in sorted(schedule)
            },
            "sha256": schedule_sha256(schedule),
        },
        "row_bindings": {
            "C1": list(c1_bindings),
            "C2": list(c2_bindings),
        },
        "code_closure": closure,
        "code_closure_sha256": _canonical_sha256(closure),
    }
    if len(schedule) == 1:
        only = next(iter(schedule.values()))
        receipt["shard"] = {
            "mode": str(only["mode"]),
            "world": int(only["world"]),
        }
    receipt_hash = _write_once_json(destination / "receipt.json", receipt)
    files["receipt.json"] = receipt_hash
    manifest = destination / "MANIFEST.sha256"
    if manifest.exists() or manifest.is_symlink():
        raise TargetGenerationError("refusing to overwrite target manifest")
    manifest.write_text(
        "".join(f"{files[name]}  {name}\n" for name in sorted(files)),
        encoding="ascii",
    )
    return {
        "schema": SCHEMA,
        "status": receipt["status"],
        "output": str(destination.resolve()),
        "manifest": str(manifest.resolve()),
        "manifest_sha256": _sha256_file(manifest),
        "files": files,
        "row_counts": {
            "C1": sum(_row_count(dataset) for dataset in c1_datasets.values()),
            "C2": sum(_row_count(dataset) for dataset in c2_datasets.values()),
        },
        "claim_ceiling": CLAIM_CEILING,
    }


def generate_targets(
    *,
    capture_path: Path,
    materialization_dir: Path,
    output: Path,
    tle_root: Path,
    prereg: Path,
    manifest: Path,
    manifest_digest: Path,
    execution_addendum: Path,
    users: int = DEFAULT_USERS,
    modes: Sequence[str] = ("informed", "neutral"),
    worlds: Sequence[int] | None = None,
) -> dict[str, object]:
    """Replay selected C1/C2 rows and write typed route datasets.

    ``worlds`` is an optional shard boundary.  When omitted, all authenticated
    mode/world shards are replayed; when supplied, exactly those worlds are
    replayed for every requested mode.
    """

    if type(users) is not int or users != DEFAULT_USERS:
        raise TargetGenerationError(
            f"target-generation runtime is fixed at exactly {DEFAULT_USERS} users"
        )
    mode_values = tuple(str(value) for value in modes)
    if not mode_values or any(value not in ("informed", "neutral") for value in mode_values):
        raise TargetGenerationError("modes must contain informed and/or neutral")
    if len(set(mode_values)) != len(mode_values):
        raise TargetGenerationError("modes must not contain duplicates")
    sealed = load_sealed_inputs(capture_path, materialization_dir)
    schedule = build_schedule(sealed, modes=mode_values, worlds=worlds)
    destination = Path(output)
    if destination.exists() or destination.is_symlink():
        raise TargetGenerationError(f"refusing to overwrite target output root: {destination}")
    c1_datasets: dict[tuple[str, int], Any] = {}
    c2_datasets: dict[tuple[str, int], Any] = {}
    c1_bindings: list[Mapping[str, object]] = []
    c2_bindings: list[Mapping[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="mcrl-v023-c1c2-targets-") as temporary_name:
        ctx = _prepare_runtime(
            sealed,
            tle_root=Path(tle_root),
            prereg=Path(prereg),
            manifest=Path(manifest),
            manifest_digest=Path(manifest_digest),
            execution_addendum=Path(execution_addendum),
            users=users,
            temporary=Path(temporary_name),
        )
        network_before = str(ctx.modules.source._model_digest(
            ctx.q1, ctx.q2, ctx.auth["q1_receipt"], ctx.auth["q2_receipt"]
        ))
        for shard in schedule.values():
            mode = str(shard["mode"])
            world = int(shard["world"])
            if shard["C1"]:
                dataset, bindings = _generate_c1_world(
                    ctx, sealed, sealed.c1_routes[mode], world=world
                )
                c1_datasets[(mode, world)] = dataset
                c1_bindings.extend({"mode": mode, **row} for row in bindings)
            if shard["C2"]:
                dataset, bindings = _generate_c2_world(
                    ctx, sealed, sealed.c2_routes[mode], world=world, mode=mode
                )
                c2_datasets[(mode, world)] = dataset
                c2_bindings.extend({"mode": mode, **row} for row in bindings)
        # Read-only source generation must not update either authenticated Main
        # head.  C2 now reads the OPS-3 projection directly and has no legacy
        # trainer/replay backend to mutate.
        network_after = str(ctx.modules.source._model_digest(
            ctx.q1, ctx.q2, ctx.auth["q1_receipt"], ctx.auth["q2_receipt"]
        ))
        if network_after != network_before:
            raise TargetGenerationError("target generation changed the Main network")
        return _write_outputs(
            destination,
            sealed=sealed,
            ctx=ctx,
            schedule=schedule,
            c1_datasets=c1_datasets,
            c2_datasets=c2_datasets,
            c1_bindings=c1_bindings,
            c2_bindings=c2_bindings,
        )


def _parser() -> Any:
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--materialization-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-digest", type=Path, required=True)
    parser.add_argument("--execution-addendum", type=Path, required=True)
    parser.add_argument("--users", type=int, default=DEFAULT_USERS)
    parser.add_argument(
        "--mode",
        choices=("informed", "neutral", "both"),
        default="both",
    )
    parser.add_argument(
        "--world",
        type=int,
        help="replay exactly one authenticated world for the selected mode",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    import json as _json  # noqa: PLC0415

    args = _parser().parse_args(argv)
    modes = ("informed", "neutral") if args.mode == "both" else (args.mode,)
    try:
        result = generate_targets(
            capture_path=args.capture,
            materialization_dir=args.materialization_dir,
            output=args.output,
            tle_root=args.tle_root,
            prereg=args.prereg,
            manifest=args.manifest,
            manifest_digest=args.manifest_digest,
            execution_addendum=args.execution_addendum,
            users=args.users,
            modes=modes,
            worlds=None if args.world is None else (args.world,),
        )
    except Exception as error:
        print(f"V023_C1C2_TARGET_GENERATION_BLOCKED: {error}", file=sys.stderr)
        return 2
    print(_json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
