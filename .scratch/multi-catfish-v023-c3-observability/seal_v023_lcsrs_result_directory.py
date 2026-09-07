#!/usr/bin/env python3
"""Prepare and seal one immutable V0.23 LC-SRS gate result directory.

This module performs provenance and filesystem work only.  It never imports
the simulator or learner, reads TLE data, opens TEST, or starts training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


CONTRACT_SHA256 = "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
ADDENDUM_SHA256 = "486568d017de84bfba5aa8bb65f634998446ac4b3ad471795b9055085e8f5070"
RESULT_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-result-v1"
FROZEN_THRESHOLDS = {
    "pair_coverage": {
        "closure_pairs_min": 24,
        "pairs_per_world_min": 1,
        "placebo_supported_coverage_per_fold_min": 0.80,
    },
    "mechanics": {"pair_pass_fraction_min": 0.90, "draws_per_pair": 32},
    "physical_signature": {
        "pooled_ratio_of_sums_ee_direction": "STRICTLY_POSITIVE",
        "positive_worlds_min": 4,
        "world_count": 8,
    },
    "target_support": {"absolute_mean_target_min": 0.02, "rows_min": 24},
    "held_out_learner": {
        "informed_spearman_min": 0.20,
        "informed_sign_accuracy_min": 0.60,
        "informed_minus_placebo_sign_accuracy_min": 0.05,
    },
    "world_stability": {
        "mean_seed_informed_beats_placebo_worlds_min": 6,
        "per_seed_nonnegative_spearman_worlds_min": 5,
    },
    "action_exposure": {"informed_action_change_fraction_min": 0.10},
    "pair_composition": {
        "informed_literal_11_fraction_min": 0.25,
        "literal_11_positive_worlds_min": 4,
        "harmful_partial_fraction_max": 0.05,
    },
    "topology_consistency": {"selected_11_fraction_min": 0.80},
    "teacher_composition": {
        "pooled_ee_direction": "STRICTLY_POSITIVE",
        "positive_worlds_min": 4,
    },
    "learned_composition": {
        "pooled_ee_direction": "STRICTLY_POSITIVE",
        "positive_worlds_min": 4,
    },
    "service": {"per_world_served_margin": 0.01},
    "c1_context": {
        "spearman_min": 0.20,
        "sign_accuracy_min": 0.55,
        "nontrivial_rows_min": 24,
        "absolute_normalized_value_min": 0.02,
    },
    "c2_context": {
        "exposure_fraction_min": 0.10,
        "absolute_native_delta_min": 0.02,
    },
}
FROZEN_DESIGN_BASIS = {
    "method": "LC_SRS",
    "objective": "MAIN_ONLY_RATIO_OF_SUMS_EE",
    "formula": "V022_EXACT_TWO_PLAYER_COALITION_RESIDUAL",
    "teacher": "FOUR_PROFILE_00_10_01_11_COMMON_RANDOM_FIELD",
    "learner": "REFERENCE_CENTRED_RELATIONAL_C3_SHARED_TOKEN",
    "comparison": "INFORMED_VS_MATCHED_PLACEBO",
    "evaluation": "EIGHT_WORLD_LEAVE_ONE_WORLD_OUT_THREE_SEEDS",
    "composition": "ONE_PASS_Q1_PLUS_Q2_PLUS_Q3_MASKED_ARGMAX",
    "background": "V020_REPRICED_LINEAGE_2026092101_RUNG_003000",
    "split": "TRAIN_DEVELOPMENT",
}


class V023ResultSealError(RuntimeError):
    """A write-once result-directory boundary was violated."""


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023ResultSealError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
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
        ).encode("ascii") + b"\n"
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023ResultSealError("value is not canonical finite ASCII JSON") from error


def _read_canonical_json(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023ResultSealError(f"JSON input is missing or symlinked: {source}")
    raw = source.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023ResultSealError(f"JSON input is malformed: {source}") from error
    if not isinstance(payload, dict) or raw not in (
        _canonical_bytes(payload),
        _canonical_bytes(payload).rstrip(b"\n"),
    ):
        raise V023ResultSealError(f"JSON input is not canonical: {source}")
    return payload


def _write_once(path: Path, data: bytes) -> None:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise V023ResultSealError(f"refusing to overwrite: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _copy_or_verify(source: Path, target: Path) -> None:
    origin = Path(source)
    if origin.is_symlink() or not origin.is_file():
        raise V023ResultSealError(f"authority input is missing or symlinked: {origin}")
    data = origin.read_bytes()
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file() or target.read_bytes() != data:
            raise V023ResultSealError(f"existing authority snapshot drifted: {target}")
        return
    _write_once(target, data)


def _require_run_root(run_root: Path) -> Path:
    requested = Path(run_root)
    if requested.is_symlink():
        raise V023ResultSealError(f"run root is symlinked: {requested}")
    root = requested.resolve(strict=False)
    if not root.is_dir():
        raise V023ResultSealError(f"run root is missing or symlinked: {root}")
    metadata = root / "LAUNCH-METADATA.json"
    payload = _read_canonical_json(metadata)
    if (
        payload.get("schema") != "multi-catfish-mcrl-v023-lcsrs-server-run-v1"
        or payload.get("split") != "TRAIN_DEVELOPMENT"
        or payload.get("test_split_opened") is not False
        or payload.get("episode_training") is not False
    ):
        raise V023ResultSealError("launch metadata crossed a frozen boundary")
    return root


def prepare_authority(
    *,
    run_root: Path,
    contract: Path,
    addendum: Path,
    preflight_manifest: Path,
    preflight_digest: Path,
) -> Path:
    """Snapshot frozen authority bytes before source work; safely resumable."""

    root = _require_run_root(run_root)
    if file_sha256(contract) != CONTRACT_SHA256:
        raise V023ResultSealError("contract digest drifted")
    if file_sha256(addendum) != ADDENDUM_SHA256:
        raise V023ResultSealError("execution addendum digest drifted")
    manifest_sha = file_sha256(preflight_manifest)
    digest_lines = Path(preflight_digest).read_text(encoding="ascii").splitlines()
    if len(digest_lines) != 1 or digest_lines[0].split() != [
        manifest_sha,
        Path(preflight_manifest).name,
    ]:
        raise V023ResultSealError("preflight digest sidecar disagrees")

    authority = root / "authority"
    if authority.exists() or authority.is_symlink():
        if authority.is_symlink() or not authority.is_dir():
            raise V023ResultSealError("authority snapshot directory is not a regular directory")
    else:
        authority.mkdir(mode=0o755)
    snapshots = {
        "contract": (Path(contract), authority / Path(contract).name),
        "execution_addendum": (Path(addendum), authority / Path(addendum).name),
        "preflight_manifest": (
            Path(preflight_manifest),
            authority / "PREFLIGHT-MANIFEST.json",
        ),
        "preflight_manifest_digest": (
            Path(preflight_digest),
            authority / "PREFLIGHT-MANIFEST.sha256",
        ),
    }
    for source, target in snapshots.values():
        _copy_or_verify(source, target)
    receipt: dict[str, Any] = {
        "schema": "multi-catfish-mcrl-v023-lcsrs-authority-snapshot-v1",
        "contract_sha256": CONTRACT_SHA256,
        "execution_addendum_sha256": ADDENDUM_SHA256,
        "preflight_manifest_sha256": manifest_sha,
        "entries": {
            role: {
                "path": target.relative_to(root).as_posix(),
                "sha256": file_sha256(target),
            }
            for role, (_, target) in sorted(snapshots.items())
        },
        "test_split_opened": False,
        "episode_training": False,
    }
    receipt_path = authority / "AUTHORITY.json"
    encoded = _canonical_bytes(receipt)
    if receipt_path.exists() or receipt_path.is_symlink():
        if receipt_path.is_symlink() or receipt_path.read_bytes() != encoded:
            raise V023ResultSealError("existing authority receipt drifted")
    else:
        _write_once(receipt_path, encoded)
    _verify_authority_snapshot(root)
    return receipt_path


def _verify_authority_snapshot(root: Path) -> dict[str, Any]:
    receipt_path = root / "authority" / "AUTHORITY.json"
    receipt = _read_canonical_json(receipt_path)
    manifest_path = root / "authority" / "PREFLIGHT-MANIFEST.json"
    expected_paths = {
        "contract": (
            "authority/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md",
            CONTRACT_SHA256,
        ),
        "execution_addendum": (
            "authority/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md",
            ADDENDUM_SHA256,
        ),
        "preflight_manifest": (
            "authority/PREFLIGHT-MANIFEST.json",
            file_sha256(manifest_path),
        ),
        "preflight_manifest_digest": (
            "authority/PREFLIGHT-MANIFEST.sha256",
            None,
        ),
    }
    if (
        receipt.get("schema")
        != "multi-catfish-mcrl-v023-lcsrs-authority-snapshot-v1"
        or receipt.get("contract_sha256") != CONTRACT_SHA256
        or receipt.get("execution_addendum_sha256") != ADDENDUM_SHA256
        or receipt.get("preflight_manifest_sha256") != expected_paths[
            "preflight_manifest"
        ][1]
        or receipt.get("test_split_opened") is not False
        or receipt.get("episode_training") is not False
    ):
        raise V023ResultSealError("authority snapshot identity drifted")
    entries = receipt.get("entries")
    if not isinstance(entries, Mapping) or set(entries) != set(expected_paths):
        raise V023ResultSealError("authority snapshot entry set drifted")
    for role, (relative_text, fixed_digest) in expected_paths.items():
        entry = entries.get(role)
        if not isinstance(entry, Mapping) or entry.get("path") != relative_text:
            raise V023ResultSealError(f"authority snapshot path drifted for {role}")
        path = root / relative_text
        actual = file_sha256(path)
        if entry.get("sha256") != actual or (
            fixed_digest is not None and actual != fixed_digest
        ):
            raise V023ResultSealError(f"authority snapshot digest drifted for {role}")
    digest_sidecar = root / expected_paths["preflight_manifest_digest"][0]
    fields = digest_sidecar.read_text(encoding="ascii").split()
    if fields != [file_sha256(manifest_path), "PREFLIGHT-MANIFEST.json"]:
        raise V023ResultSealError("authority preflight digest sidecar disagrees")
    return receipt


def _result_from_source_stage(verification: Mapping[str, Any]) -> dict[str, Any]:
    if (
        verification.get("status") != "VERIFIED_SOURCE_STAGE"
        or verification.get("decision") != "INSUFFICIENT_PAIRS"
        or verification.get("fit_launched") is not False
        or verification.get("learner_update") is not False
        or verification.get("test_split_opened") is not False
        or verification.get("episode_training") is not False
    ):
        raise V023ResultSealError("source-stage receipt is not an insufficient-pairs stop")
    source_panel = verification.get("source_panel")
    if not isinstance(source_panel, Mapping):
        raise V023ResultSealError("source-stage receipt lacks its verified source panel")
    predicates = source_panel.get("predicates")
    if not isinstance(predicates, Mapping):
        raise V023ResultSealError("source-stage receipt lacks source predicates")
    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS_SOURCE_STAGE_INTEGRITY",
        "integrity_status": "VERIFIED_SOURCE_ONLY",
        "c3_decision": "INSUFFICIENT_PAIRS",
        "context_status": source_panel.get("context_status"),
        "context": {
            "c1": source_panel.get("c1"),
            "c2": source_panel.get("c2"),
        },
        "scientific_claim": False,
        "claim_ceiling": verification.get("claim_ceiling"),
        "contract_sha256": verification.get("contract_sha256"),
        "preflight_manifest_sha256": verification.get("preflight_manifest_sha256"),
        "source_count": verification.get("source_count"),
        "fit_count": 0,
        "composition_count": 0,
        "test_split_opened": False,
        "episode_training": False,
        "no_rescue": True,
        "predicates": {
            **dict(predicates),
            "held_out_learner": "NOT_EVALUATED_SOURCE_STAGE_STOP",
            "world_stability": "NOT_EVALUATED_SOURCE_STAGE_STOP",
            "action_exposure": "NOT_EVALUATED_SOURCE_STAGE_STOP",
            "literal_11": "NOT_EVALUATED_SOURCE_STAGE_STOP",
            "harmful_partial": "NOT_EVALUATED_SOURCE_STAGE_STOP",
            "topology_consistency": "NOT_EVALUATED_SOURCE_STAGE_STOP",
            "teacher_composition": "NOT_EVALUATED_SOURCE_STAGE_STOP",
            "learned_composition": "NOT_EVALUATED_SOURCE_STAGE_STOP",
            "service": "NOT_EVALUATED_SOURCE_STAGE_STOP",
        },
        "denominators": {
            "pair_count": source_panel.get("pair_count"),
            "mechanics_pass_count": source_panel.get("mechanics_pass_count"),
            "target_support_count": source_panel.get("target_support_count"),
            "placebo_folds": source_panel.get("placebo_folds"),
            "world_results": source_panel.get("world_results"),
        },
        "source_panel": dict(source_panel),
        "thresholds": FROZEN_THRESHOLDS,
        "design_basis": FROZEN_DESIGN_BASIS,
    }


def _regular_result_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise V023ResultSealError(f"result tree contains a symlink: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise V023ResultSealError(f"result tree contains a special file: {path}")
        relative = path.relative_to(root).as_posix()
        if relative in {"MANIFEST.sha256", "COMPLETE"}:
            continue
        files.append(path)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def seal_result_directory(
    *, run_root: Path, verification_path: Path, kind: str
) -> tuple[Path, Path]:
    """Write result/verification, hash every immutable result file, then COMPLETE."""

    root = _require_run_root(run_root)
    authority = _verify_authority_snapshot(root)
    preflight_sha256 = authority.get("preflight_manifest_sha256")
    if (
        authority.get("contract_sha256") != CONTRACT_SHA256
        or authority.get("execution_addendum_sha256") != ADDENDUM_SHA256
        or not isinstance(preflight_sha256, str)
        or len(preflight_sha256) != 64
    ):
        raise V023ResultSealError("authority snapshot identity drifted")
    requested_verification = Path(verification_path)
    if requested_verification.is_symlink():
        raise V023ResultSealError("verification source is symlinked")
    verification_source = requested_verification.resolve()
    if not verification_source.is_relative_to(root):
        raise V023ResultSealError("verification source must stay inside the run root")
    verification = _read_canonical_json(verification_source)
    if kind == "full":
        if (
            verification.get("status") != "PASS_FINAL_INTEGRITY"
            or verification.get("integrity_status") != "VERIFIED"
            or verification.get("source_count") != 8
            or verification.get("fit_count") != 48
            or verification.get("composition_count") != 48
            or verification.get("contract_sha256") != CONTRACT_SHA256
            or verification.get("execution_addendum_sha256") != ADDENDUM_SHA256
            or verification.get("preflight_manifest_sha256") != preflight_sha256
            or verification.get("scientific_claim") is not False
            or verification.get("test_split_opened") is not False
            or verification.get("episode_training") is not False
        ):
            raise V023ResultSealError("full verification receipt did not pass integrity")
        result = dict(verification)
        result["thresholds"] = FROZEN_THRESHOLDS
        result["design_basis"] = FROZEN_DESIGN_BASIS
    elif kind == "source-insufficient":
        result = _result_from_source_stage(verification)
        if verification.get("preflight_manifest_sha256") != preflight_sha256:
            raise V023ResultSealError(
                "source-stage receipt disagrees with the authority preflight"
            )
        result["source_stage_receipt_sha256"] = file_sha256(verification_source)
    else:
        raise V023ResultSealError(f"unsupported result kind: {kind}")

    result_path = root / "result.json"
    verification_path_out = root / "verification.json"
    _write_once(result_path, _canonical_bytes(result))
    _write_once(verification_path_out, _canonical_bytes(verification))

    manifest_path = root / "MANIFEST.sha256"
    complete_path = root / "COMPLETE"
    if manifest_path.exists() or manifest_path.is_symlink():
        raise V023ResultSealError("result manifest already exists")
    if complete_path.exists() or complete_path.is_symlink():
        raise V023ResultSealError("COMPLETE already exists")
    entries = [
        f"{file_sha256(path)}  {path.relative_to(root).as_posix()}"
        for path in _regular_result_files(root)
    ]
    if not entries:
        raise V023ResultSealError("result manifest would be empty")
    _write_once(manifest_path, ("\n".join(entries) + "\n").encode("ascii"))
    for line in manifest_path.read_text(encoding="ascii").splitlines():
        digest, relative = line.split("  ", 1)
        target = root / relative
        if not target.resolve().is_relative_to(root) or file_sha256(target) != digest:
            raise V023ResultSealError(f"result manifest verification failed: {relative}")
    manifest_digest = file_sha256(manifest_path)
    _write_once(complete_path, f"{manifest_digest}  MANIFEST.sha256\n".encode("ascii"))
    return manifest_path, complete_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--run-root", required=True, type=Path)
    prepare.add_argument("--contract", required=True, type=Path)
    prepare.add_argument("--addendum", required=True, type=Path)
    prepare.add_argument("--preflight-manifest", required=True, type=Path)
    prepare.add_argument("--preflight-digest", required=True, type=Path)
    seal = subparsers.add_parser("seal")
    seal.add_argument("--run-root", required=True, type=Path)
    seal.add_argument("--verification", required=True, type=Path)
    seal.add_argument("--kind", choices=("full", "source-insufficient"), required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "prepare":
            output = prepare_authority(
                run_root=args.run_root,
                contract=args.contract,
                addendum=args.addendum,
                preflight_manifest=args.preflight_manifest,
                preflight_digest=args.preflight_digest,
            )
        else:
            output, _ = seal_result_directory(
                run_root=args.run_root,
                verification_path=args.verification,
                kind=args.kind,
            )
    except V023ResultSealError as error:
        print(f"V023_RESULT_SEAL_ERROR: {error}", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
