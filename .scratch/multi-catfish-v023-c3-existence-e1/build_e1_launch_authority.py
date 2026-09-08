#!/usr/bin/env python3
"""Build the immutable E1 launch authority after sealed preflight."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3_existence_e1 as e1


def build_authority(
    *, preflight_manifest: Path, contract: Path, output_root: Path,
    tle_root: Path, launch_arguments: Sequence[str], authority_path: Path,
) -> dict[str, object]:
    preflight_path = Path(preflight_manifest)
    _manifest, preflight_sha = e1.validate_preflight_manifest(preflight_path)
    sealed_contract = e1.sealed_contract_binding()
    contract_path = Path(contract)
    output_path = Path(output_root)
    tle_path = Path(tle_root)
    if not contract_path.is_absolute() or str(contract_path.resolve()) != sealed_contract["path"]:
        raise e1.E1Error("--contract must be the absolute controller-sealed E1 contract")
    if not output_path.is_absolute() or output_path.is_symlink():
        raise e1.E1Error("--output-root must be an absolute non-symlink path")
    if not tle_path.is_absolute() or tle_path != e1.CANONICAL_TLE_ROOT or tle_path.is_symlink():
        raise e1.E1Error("--tle-root must be the canonical frozen E1 TLE root")
    arguments = list(launch_arguments)
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    if not arguments or any(not isinstance(value, str) for value in arguments):
        raise e1.E1Error("--launch-arguments must contain the exact runner argv template")
    parsed = e1._parser().parse_args(arguments)
    if (
        parsed.dry_run
        or (parsed.unit is None) == (not parsed.merge)
        or parsed.output is None
        or str(parsed.output) != str(output_path)
        or parsed.preflight_manifest != preflight_path
        or parsed.tle_root is not None and parsed.tle_root != tle_path
        or parsed.unit is not None and parsed.tle_root != tle_path
        or parsed.launch_authority is None
        or Path(parsed.launch_authority).resolve() != Path(authority_path).resolve()
    ):
        raise e1.E1Error("launch arguments do not bind one exact unit/merge invocation")
    frozen_inputs = e1.prereg_tle_bindings()
    return {
        "schema": e1.LAUNCH_AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": e1.CLAIM_CEILING,
        "preflight_manifest": {
            "path": e1._preflight_path_record(preflight_path),
            "sha256": preflight_sha,
        },
        "contract": sealed_contract,
        "bindings": e1.panel_bindings(),
        "checkout_root": str(e1.REPO.resolve()),
        "output_root": str(output_path.resolve()),
        "tle_root": str(tle_path),
        "preregistration": frozen_inputs["preregistration"],
        "tle_archive": frozen_inputs["tle_archive"],
        "launch_arguments": arguments,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def write_authority(
    *, preflight_manifest: Path, contract: Path, output_root: Path,
    tle_root: Path, launch_arguments: Sequence[str], output: Path,
) -> tuple[Path, Path, str]:
    target = Path(output)
    sidecar = target.with_suffix(".sha256")
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise e1.E1Error("refusing to overwrite launch authority or digest sidecar")
    payload = build_authority(
        preflight_manifest=preflight_manifest, contract=contract,
        output_root=output_root, tle_root=tle_root,
        launch_arguments=launch_arguments, authority_path=target,
    )
    digest = e1._write_once(target, payload)
    with sidecar.open("xb") as handle:
        handle.write(f"{digest}  {target.name}\n".encode("ascii"))
        handle.flush()
        os.fsync(handle.fileno())
    sidecar.chmod(0o444)
    e1._validate_digest_sidecar(target, digest=digest, label="E1 launch authority")
    return target, sidecar, digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--launch-arguments", nargs=argparse.REMAINDER, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        target, sidecar, digest = write_authority(
            preflight_manifest=args.preflight_manifest, contract=args.contract,
            output_root=args.output_root, tle_root=args.tle_root,
            launch_arguments=args.launch_arguments, output=args.output,
        )
    except Exception as error:
        print(f"E1_LAUNCH_AUTHORITY_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"E1_LAUNCH_AUTHORITY_PASS authority={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
