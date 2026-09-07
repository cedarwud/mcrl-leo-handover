#!/usr/bin/env python3
"""Build the sealed F3 D/F dense source from authenticated F2 shared tapes.

Real execution replays BASE only to reconstruct the imported R7 ``C3View``;
all labels are recomputed by F2's own authenticated F0 reader path.  Imports
and ``--dry-run`` are simulator-inert.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import io
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import traceback
from typing import Any, Callable, Mapping, Sequence

import numpy as np

import f3_common as common
from f3_neutral_rule import (
    C1_CLUSTER_NEUTRAL_SOURCE_RULE,
    C2_NEUTRAL_SOURCE_RULE,
    F3_NEUTRAL_KEY,
    F3_NEUTRAL_KEY_SHA256,
    F3_NEUTRAL_RULE,
    IMPORTED_NEUTRAL_RULES,
    F3NeutralMaterialization,
    build_f3_neutral,
)
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.runtime.ee_axis_lcsrs_c3_encoder import capture_lcsrs_c3_predecision
from mcrl.runtime.ee_axis_lcsrs_c3_state import C3View


f2 = common.f2
HERE = common.HERE
SOURCE_SCHEMA = f"{common.SCHEMA}-source-artifact"
SOURCE_RECORD_SCHEMA = f"{SOURCE_SCHEMA}-record"
SOURCE_RECEIPT_SCHEMA = f"{SOURCE_SCHEMA}-receipt"


def neutral_rule_binding() -> dict[str, object]:
    """Distinguish C3 label permutation from C1/C2 source selection."""

    return {
        "c3_f3": {
            "rule": F3_NEUTRAL_RULE,
            "key": F3_NEUTRAL_KEY,
            "scope": "FOLD_LOCAL_TRAINING_ONLY_LABEL_PERMUTATION",
        },
        "c1_predecision_source_selection": C1_CLUSTER_NEUTRAL_SOURCE_RULE,
        "c2_predecision_source_selection": C2_NEUTRAL_SOURCE_RULE,
    }


SOURCE_MANIFEST_SCHEMA = f"{SOURCE_SCHEMA}-manifest"
DEFAULT_PREFLIGHT = HERE / "F3-PREFLIGHT-MANIFEST.json"


@dataclass(frozen=True)
class ReplayedView:
    view: C3View
    state_sha256: str
    q12: np.ndarray
    action_physical_keys: tuple[tuple[tuple[int, int] | None, ...], ...]


@dataclass(frozen=True)
class F3SourceRecord:
    world: int
    lineage: int
    step: int
    anchor_id: str
    view: C3View
    q12: np.ndarray
    targets_bits: np.ndarray
    targets_normalized: np.ndarray
    tape_sha256: str
    state_sha256: str
    action_physical_keys: tuple[tuple[tuple[int, int] | None, ...], ...]

    def __post_init__(self) -> None:
        if self.world not in common.WORLDS or self.lineage not in common.LINEAGES:
            raise common.F3Error("source record is outside the F3 panel")
        if self.step not in common.ANCHORS:
            raise common.F3Error("source record must be a noninitial step 1..9")
        if self.anchor_id != f"w{self.world}:l{self.lineage}:t{self.step}":
            raise common.F3Error("source anchor identifier drifted")
        self.view.verify()
        q12 = np.array(self.q12, dtype=np.float32, copy=True, order="C")
        bits = np.array(self.targets_bits, dtype=np.float64, copy=True, order="C")
        normalized = np.array(
            self.targets_normalized, dtype=np.float32, copy=True, order="C"
        )
        shape = self.view.action_mask.shape
        if q12.shape != shape or bits.shape != shape or normalized.shape != shape:
            raise common.F3Error("source Q12/target shapes disagree with C3View")
        if not np.all(np.isfinite(q12)) or not np.all(np.isfinite(bits)) or not np.all(
            np.isfinite(normalized)
        ):
            raise common.F3Error("source Q12/targets are non-finite")
        expected_reference = np.argmax(
            np.where(self.view.action_mask, q12, -np.inf), axis=1
        ).astype(np.int64)
        if not np.array_equal(expected_reference, self.view.reference_actions):
            raise common.F3Error("source Q12 disagrees with the C3View reference")
        rows = np.arange(shape[0])
        if np.any(bits[~self.view.action_mask] != 0.0) or np.any(
            normalized[~self.view.action_mask] != 0.0
        ):
            raise common.F3Error("source targets widened the native mask")
        if np.any(bits[rows, self.view.reference_actions] != 0.0) or np.any(
            normalized[rows, self.view.reference_actions] != 0.0
        ):
            raise common.F3Error("reference targets must remain exact zero")
        expected = np.asarray(bits / common.KAPPA_BITS, dtype=np.float32)
        if not np.array_equal(expected, normalized):
            raise common.F3Error("source target was not divided by kappa exactly once")
        common.digest(self.tape_sha256, field="source tape sha256")
        common.digest(self.state_sha256, field="source state sha256")
        if len(self.action_physical_keys) != shape[0] or any(
            len(row) != shape[1] for row in self.action_physical_keys
        ):
            raise common.F3Error("source action-identity table has the wrong shape")
        q12.setflags(write=False)
        bits.setflags(write=False)
        normalized.setflags(write=False)
        object.__setattr__(self, "q12", q12)
        object.__setattr__(self, "targets_bits", bits)
        object.__setattr__(self, "targets_normalized", normalized)

    @property
    def content_digest(self) -> str:
        digest = common.hashlib.sha256()
        digest.update(SOURCE_RECORD_SCHEMA.encode("ascii"))
        for value in (self.world, self.lineage, self.step):
            digest.update(int(value).to_bytes(8, "big"))
        for text in (
            self.anchor_id,
            self.view.content_digest,
            self.tape_sha256,
            self.state_sha256,
        ):
            digest.update(text.encode("ascii"))
        for array in (self.q12, self.targets_bits, self.targets_normalized):
            value = np.ascontiguousarray(array)
            digest.update(value.dtype.str.encode("ascii"))
            digest.update(repr(value.shape).encode("ascii"))
            digest.update(value.tobytes(order="C"))
        return digest.hexdigest()


ViewProvider = Callable[[f2.UnitKey, int, Mapping[str, object]], ReplayedView]


def _physical_keys(value: object) -> tuple[tuple[tuple[int, int] | None, ...], ...]:
    if not isinstance(value, list):
        raise common.F3Error("action physical-key table must be a list")
    rows = []
    for row in value:
        if not isinstance(row, list):
            raise common.F3Error("action physical-key table row is malformed")
        converted = []
        for key in row:
            if key is None:
                converted.append(None)
            elif (
                isinstance(key, list)
                and len(key) == 2
                and all(type(item) is int for item in key)
            ):
                converted.append((int(key[0]), int(key[1])))
            else:
                raise common.F3Error("action physical key is not null or [satellite,cell]")
        rows.append(tuple(converted))
    return tuple(rows)


def build_source_records(
    tapes: Mapping[f2.UnitKey, tuple[Mapping[str, object], str]],
    *,
    survivor: str,
    view_provider: ViewProvider,
    expected_units: Sequence[f2.UnitKey] = f2.ALL_UNITS,
) -> tuple[F3SourceRecord, ...]:
    """Materialise dense D/F rows through F2's verified target reader."""

    if survivor not in {"D", "F"}:
        raise common.F3NotAdmitted("F3_NOT_ADMITTED: source needs D or F")
    units = tuple(expected_units)
    if not units or set(tapes) != set(units):
        raise common.F3Error("source build does not cover its exact declared F2 units")
    records: list[F3SourceRecord] = []
    for key in units:
        tape, tape_sha = tapes[key]
        verified = f2.verify_unit_tape(tape, key=key)
        if survivor not in verified["survivors"]:
            raise common.F3Error("F3 survivor was not evaluated in an F2 unit tape")
        steps = tape["steps"]
        assert isinstance(steps, list)
        for step_index in common.ANCHORS:
            step = steps[step_index]
            if not isinstance(step, Mapping):
                raise common.F3Error("F2 step is malformed")
            replayed = view_provider(key, step_index, step)
            if not isinstance(replayed, ReplayedView):
                raise common.F3Error("view provider did not return ReplayedView")
            replayed.view.verify()
            tape_q12 = np.asarray(f2.f1._matrix_from_hex(step["q12"], field="q12"), dtype=np.float32)
            tape_mask = np.asarray(step["action_masks"], dtype=np.bool_)
            tape_reference = np.asarray(step["reference_actions"], dtype=np.int64)
            tape_keys = _physical_keys(step["action_physical_keys"])
            if (
                replayed.state_sha256 != step.get("state_sha256")
                or not np.array_equal(np.asarray(replayed.q12, dtype=np.float32), tape_q12)
                or not np.array_equal(replayed.view.action_mask, tape_mask)
                or not np.array_equal(replayed.view.reference_actions, tape_reference)
                or replayed.action_physical_keys != tape_keys
            ):
                raise common.F3Error(
                    "BASE replay disagrees with stored state/Q12/mask/reference/action identity"
                )
            if np.any(~np.any(tape_mask, axis=1)):
                raise common.F3Error("F3_INTERFACE_UNSUPPORTED: an anchor has an empty legal mask")
            d_bits, f_bits = f2.f1.target_surfaces_from_step(step)
            bits = d_bits if survivor == "D" else f_bits
            normalized = np.asarray(bits / common.KAPPA_BITS, dtype=np.float32)
            records.append(
                F3SourceRecord(
                    world=key.world,
                    lineage=key.lineage,
                    step=step_index,
                    anchor_id=f"w{key.world}:l{key.lineage}:t{step_index}",
                    view=replayed.view,
                    q12=tape_q12,
                    targets_bits=bits,
                    targets_normalized=normalized,
                    tape_sha256=tape_sha,
                    state_sha256=str(step["state_sha256"]),
                    action_physical_keys=tape_keys,
                )
            )
    expected = len(units) * len(common.ANCHORS)
    if len(records) != expected:
        raise common.F3Error("F3 source record count drifted")
    return tuple(records)


def build_neutral_folds(
    records: Sequence[F3SourceRecord],
) -> dict[int, F3NeutralMaterialization]:
    folds: dict[int, F3NeutralMaterialization] = {}
    for held_out in common.WORLDS:
        training_worlds = tuple(world for world in common.WORLDS if world != held_out)
        neutral = build_f3_neutral(records, training_worlds=training_worlds)
        if not neutral.meets_coverage_gate:
            raise common.F3Error(
                f"F3 neutral coverage below {common.PLACEBO_COVERAGE_MIN} for held-out {held_out}"
            )
        folds[held_out] = neutral
    return folds


def _npz_bytes(arrays: Mapping[str, np.ndarray]) -> bytes:
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    return buffer.getvalue()


def _record_metadata(record: F3SourceRecord, *, npz_name: str, npz_sha256: str) -> dict[str, object]:
    legal = np.asarray(record.view.action_mask)
    references = np.asarray(record.view.reference_actions)
    nonreference = legal.copy()
    nonreference[np.arange(references.size), references] = False
    return {
        "schema": SOURCE_RECORD_SCHEMA,
        "world": record.world,
        "lineage": record.lineage,
        "step": record.step,
        "anchor_id": record.anchor_id,
        "content_digest": record.content_digest,
        "view_content_digest": record.view.content_digest,
        "state_sha256": record.state_sha256,
        "f2_tape_sha256": record.tape_sha256,
        "legal_rows": int(np.count_nonzero(legal)),
        "legal_nonreference_rows": int(np.count_nonzero(nonreference)),
        "reference_rows": int(references.size),
        "target_unit": "bits_and_normalized_bits_per_kappa",
        "npz": {"path": npz_name, "sha256": npz_sha256},
    }


def write_source_artifact(
    output: Path,
    *,
    records: Sequence[F3SourceRecord],
    neutral_folds: Mapping[int, F3NeutralMaterialization],
    survivor: str,
    preflight_sha256: str,
    f2_receipt_path: Path,
    f2_receipt_sha256: str,
) -> Path:
    target = Path(output)
    if target.exists() or target.is_symlink():
        raise common.F3Error(f"refusing to overwrite source artifact: {target}")
    if survivor not in {"D", "F"} or set(neutral_folds) != set(common.WORLDS):
        raise common.F3Error("source artifact survivor/fold set drifted")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.stage-", dir=target.parent))
    try:
        record_entries = []
        ordered = tuple(records)
        for index, record in enumerate(ordered):
            stem = f"records/{index:03d}-{record.world}-{record.lineage}-t{record.step}"
            npz_path = stage / f"{stem}.npz"
            arrays = {
                "action_context": np.asarray(record.view.action_context),
                "tokens": np.asarray(record.view.tokens),
                "token_mask": np.asarray(record.view.token_mask),
                "action_mask": np.asarray(record.view.action_mask),
                "reference_actions": np.asarray(record.view.reference_actions),
                "q12": np.asarray(record.q12),
                "targets_bits": np.asarray(record.targets_bits),
                "targets_normalized": np.asarray(record.targets_normalized),
            }
            npz_sha = common.write_once_bytes(npz_path, _npz_bytes(arrays))
            metadata = _record_metadata(
                record, npz_name=f"{stem}.npz", npz_sha256=npz_sha
            )
            json_path = stage / f"{stem}.json"
            json_sha = common.write_once_json(json_path, metadata)
            record_entries.append(
                {
                    "path": f"{stem}.json",
                    "sha256": json_sha,
                    "npz_path": f"{stem}.npz",
                    "npz_sha256": npz_sha,
                    "content_digest": record.content_digest,
                }
            )
        neutral_entries = []
        for held_out in common.WORLDS:
            materialization = neutral_folds[held_out]
            training_indices = [
                index for index, record in enumerate(ordered) if record.world != held_out
            ]
            if len(training_indices) != len(materialization.targets_by_record):
                raise common.F3Error("neutral fold target count disagrees with training records")
            arrays = {
                f"record_{record_index:03d}": target_array
                for record_index, target_array in zip(
                    training_indices, materialization.targets_by_record, strict=True
                )
            }
            npz_name = f"neutral/heldout-{held_out}.npz"
            npz_sha = common.write_once_bytes(stage / npz_name, _npz_bytes(arrays))
            mapping_name = f"neutral/heldout-{held_out}.json"
            mapping_payload = {
                "schema": f"{SOURCE_SCHEMA}-neutral-fold",
                "held_out_world": held_out,
                "training_worlds": [world for world in common.WORLDS if world != held_out],
                "source_rule": F3_NEUTRAL_RULE,
                "source_key_sha256": F3_NEUTRAL_KEY_SHA256,
                "imported_neutral_rules": IMPORTED_NEUTRAL_RULES,
                "eligible_rows": materialization.eligible_rows,
                "total_rows": materialization.total_rows,
                "coverage": materialization.coverage,
                "coverage_min": common.PLACEBO_COVERAGE_MIN,
                "content_digest": materialization.content_digest,
                "targets_npz": {"path": npz_name, "sha256": npz_sha},
                "mappings": [
                    {
                        "stratum": list(mapping.stratum.key()),
                        "source": [mapping.source_record, mapping.source_user, mapping.source_action],
                        "destination": [
                            mapping.destination_record,
                            mapping.destination_user,
                            mapping.destination_action,
                        ],
                        "shift": mapping.shift,
                    }
                    for mapping in materialization.mappings
                ],
                "held_out_labels_moved": False,
            }
            mapping_sha = common.write_once_json(stage / mapping_name, mapping_payload)
            neutral_entries.append(
                {
                    "held_out_world": held_out,
                    "path": mapping_name,
                    "sha256": mapping_sha,
                    "npz_path": npz_name,
                    "npz_sha256": npz_sha,
                    "coverage": materialization.coverage,
                }
            )
        manifest = {
            "schema": SOURCE_MANIFEST_SCHEMA,
            "status": "SEALED_WRITE_ONCE",
            "claim_ceiling": common.SOURCE_CLAIM_CEILING,
            "survivor": survivor,
            "panel": common.panel_bindings(),
            "model": common.model_bindings(),
            "preflight_manifest_sha256": common.digest(
                preflight_sha256, field="F3 preflight sha256"
            ),
            "f2_terminal_receipt": {
                "path": str(Path(f2_receipt_path).resolve()),
                "sha256": common.digest(f2_receipt_sha256, field="F2 receipt sha256"),
            },
            "record_count": len(record_entries),
            "records": record_entries,
            "neutral_rule": neutral_rule_binding(),
            "neutral_folds": neutral_entries,
            "test_split_opened": False,
            "episode_training": False,
            "efficacy_claim": False,
        }
        manifest_sha = common.write_once_json(stage / "manifest.json", manifest)
        receipt = {
            "schema": SOURCE_RECEIPT_SCHEMA,
            "status": "COMPLETE",
            "outcome": "F3_SOURCE_COMPLETE",
            "claim_ceiling": common.SOURCE_CLAIM_CEILING,
            "observability_statement": common.OBSERVABILITY_STATEMENT,
            "survivor": survivor,
            "manifest": {"path": "manifest.json", "sha256": manifest_sha},
            "record_count": len(record_entries),
            "neutral_fold_count": len(neutral_entries),
            "neutral_coverage_min_observed": min(
                float(entry["coverage"]) for entry in neutral_entries
            ),
            "neutral_rule": neutral_rule_binding(),
            "method_provenance": {
                "loss": common.panel_bindings()["loss"],
                "thresholds": common.threshold_bindings(),
            },
            "test_split_opened": False,
            "episode_training": False,
            "efficacy_claim": False,
        }
        receipt_sha = common.write_once_json(stage / "receipt.json", receipt)
        complete = {
            "schema": f"{SOURCE_SCHEMA}-complete",
            "manifest_sha256": manifest_sha,
            "receipt_sha256": receipt_sha,
        }
        common.write_once_json(stage / "COMPLETE", complete)
        os.rename(stage, target)
    except BaseException:
        raise
    return target


def authenticate_f2_tapes(
    f2_root: Path, *, f2_terminal: Mapping[str, object]
) -> dict[f2.UnitKey, tuple[dict[str, Any], str]]:
    root = Path(f2_root)
    preflight_sha = str(f2_terminal["preflight_manifest_sha256"])
    f1_binding = f2_terminal["f1_result"]
    if not isinstance(f1_binding, Mapping):
        raise common.F3Error("F2 terminal receipt lacks F1 binding")
    result = {}
    for key in f2.ALL_UNITS:
        f2.authenticate_unit_bundle(
            root,
            key=key,
            preflight_sha256=preflight_sha,
            f1_binding=f1_binding,
        )
        tape_path = root / "units" / key.slug / f2.DEFAULT_TAPE_NAME
        tape = f2._load_json(tape_path, field=f"F2 unit {key.slug} tape")
        result[key] = (tape, f2.file_sha256(tape_path))
    return result


def make_runtime_view_provider(*, tle_root: Path) -> ViewProvider:
    """Create a lazy exact-BASE replay provider; no work occurs until called."""

    cache: dict[f2.UnitKey, dict[int, ReplayedView]] = {}

    def replay_unit(key: f2.UnitKey) -> dict[int, ReplayedView]:
        physical, server = f2.f1._runtime_modules()
        import v023_lcsrs_source_adapter as r7_source
        from mcrl.runtime.prereg import read_prereg
        from mcrl.runtime.training_pipeline import _evaluation_rngs

        record = read_prereg(f2.f1.PREREG_PATH)
        if record.digest != f2.f1.PREREG_RECORD_DIGEST:
            raise common.F3Error("TRAIN preregistration digest changed")
        frozen = f2._load_frozen_heads(key.lineage)
        v018 = f2.v020_loader._load_module(
            f"mcrl_v018_f3_source_{key.lineage}", f2.v020_loader.V018_PATH
        )
        model_digest = r7_source._model_digest(
            frozen.q1,
            frozen.q2,
            frozen.q1_receipt,
            frozen.q2_receipt,
        )
        field = KeyedFadingField.from_components(f2.FIELD_COMPONENT, key.world)
        result: dict[int, ReplayedView] = {}
        with tempfile.TemporaryDirectory(prefix=f"mcrl-v023-c3-f3-{key.slug}-tle-") as temporary:
            archive = server._freeze_archive(
                record, Path(tle_root), Path(temporary) / "frozen", physical
            )
            environment = server._make_environment(archive)
            step_env = environment.environment
            if getattr(step_env, "_started", False):
                raise common.F3Error("environment started before keyed field binding")
            step_env._fading_field = field
            rngs = tuple(_evaluation_rngs(key.world))
            _states, _masks, observation = environment.reset(rngs[0], rngs[1])
            for step_index in f2.CANONICAL_STEP_INDICES:
                anchor_data = r7_source._native_q12_anchor(
                    v018=v018,
                    q1=frozen.q1,
                    q2=frozen.q2,
                    step_env=step_env,
                    observation=observation,
                    model_digest=model_digest,
                )
                native = anchor_data["native"]
                q12 = np.asarray(anchor_data["q12"], dtype=np.float32)
                reference = np.asarray(anchor_data["background"], dtype=np.int64)
                if step_index > 0:
                    capture = capture_lcsrs_c3_predecision(
                        step_env,
                        observation,
                        world_id=key.world,
                        anchor_id=f"w{key.world}:l{key.lineage}:t{step_index}",
                        detached_q12=anchor_data["snapshot"],
                        reference_actions=reference,
                        opening_feasibility_surface=anchor_data["opening"],
                    )
                    result[step_index] = ReplayedView(
                        view=capture.view,
                        state_sha256=native.state_sha256,
                        q12=np.asarray(q12, dtype=np.float32),
                        action_physical_keys=_physical_keys(
                            f2.f1.action_physical_keys(observation)
                        ),
                    )
                environment.step(reference, rngs[0])
                committed = environment.last_outcome
                if step_index < f2.CANONICAL_STEP_INDICES[-1]:
                    if bool(committed.done):
                        raise common.F3Error("BASE replay terminated before step 9")
                    observation = committed.observation
        return result

    def provider(key: f2.UnitKey, step: int, _stored: Mapping[str, object]) -> ReplayedView:
        if key not in cache:
            cache[key] = replay_unit(key)
        try:
            return cache[key][step]
        except KeyError as error:
            raise common.F3Error("BASE replay omitted a noninitial anchor") from error

    return provider


def run(args: argparse.Namespace) -> dict[str, object]:
    _manifest, preflight_sha = common.validate_preflight_manifest(args.preflight_manifest)
    if args.dry_run and args.launch_authority is None:
        return {"preflight": args.preflight_manifest}
    if args.launch_authority is None:
        raise common.F3Error("source build requires --launch-authority")
    authority, f2_terminal = common.validate_launch_authority(
        args.launch_authority,
        preflight_path=args.preflight_manifest,
        preflight_sha256=preflight_sha,
    )
    if args.dry_run:
        return {"preflight": args.preflight_manifest, "authority": args.launch_authority}
    if args.output is None or args.tle_root is None:
        raise common.F3Error("source build requires --output and --tle-root")
    f2_path = Path(authority["f2_terminal_receipt"]["path"])
    root = args.f2_root if args.f2_root is not None else f2_path.parent
    tapes = authenticate_f2_tapes(root, f2_terminal=f2_terminal)
    records = build_source_records(
        tapes,
        survivor=str(authority["survivor"]),
        view_provider=make_runtime_view_provider(tle_root=args.tle_root),
    )
    neutral = build_neutral_folds(records)
    artifact = write_source_artifact(
        args.output,
        records=records,
        neutral_folds=neutral,
        survivor=str(authority["survivor"]),
        preflight_sha256=preflight_sha,
        f2_receipt_path=f2_path,
        f2_receipt_sha256=str(authority["f2_terminal_receipt"]["sha256"]),
    )
    return {"artifact": artifact}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preflight-manifest", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--f2-root", type=Path)
    parser.add_argument("--tle-root", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run(args)
    except common.F3NotAdmitted as error:
        print(str(error), file=sys.stderr)
        return 3
    except Exception as error:
        print(f"F3_SOURCE_ERROR: {error}", file=sys.stderr)
        traceback.print_exception(error, file=sys.stderr)
        return 2
    if args.dry_run:
        print(f"F3_SOURCE_DRY_RUN_PASS preflight={result['preflight']}")
    else:
        print(f"F3_SOURCE_WRITTEN artifact={result['artifact']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
