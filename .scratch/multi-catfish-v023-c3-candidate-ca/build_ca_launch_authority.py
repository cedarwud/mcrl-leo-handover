#!/usr/bin/env python3
"""Build one immutable C-A launch authority after sealed preflight."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3_candidate_ca as ca


def build_authority(
    *, preflight_manifest: Path, contract: Path, output_root: Path,
    tle_root: Path, profile_count_cap: int, launch_arguments: Sequence[str],
    authority_path: Path,
) -> dict[str, object]:
    preflight = Path(preflight_manifest)
    _manifest, preflight_sha = ca.validate_preflight_manifest(
        preflight, profile_count_cap=profile_count_cap
    )
    sealed_contract = ca.sealed_contract_binding()
    if Path(contract).resolve() != Path(sealed_contract["path"]):
        raise ca.CAError("--contract must be the exact controller-sealed C-A contract")
    output = Path(output_root)
    ca.validate_output_root(output)
    if Path(tle_root) != ca.CANONICAL_TLE_ROOT or Path(tle_root).is_symlink():
        raise ca.CAError("--tle-root must be the canonical frozen TLE root")
    arguments = list(launch_arguments)
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    parsed = ca._parser().parse_args(arguments)
    if (
        parsed.estimate or parsed.dry_run
        or (parsed.unit is None) == (not parsed.merge)
        or parsed.output is None or str(parsed.output) != str(output)
        or parsed.preflight_manifest != preflight
        or parsed.launch_authority is None
        or Path(parsed.launch_authority).resolve() != Path(authority_path).resolve()
        or parsed.profile_count_cap != profile_count_cap
        or Path(parsed.e1_output).resolve() != ca.E1_OUTPUT_ROOT.resolve()
        or parsed.unit is not None and parsed.tle_root != Path(tle_root)
        or parsed.tle_root is not None and parsed.tle_root != Path(tle_root)
    ):
        raise ca.CAError("launch arguments do not bind one exact unit/merge invocation")
    frozen = ca.static_bindings(profile_count_cap)
    return {
        "schema": ca.LAUNCH_AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": ca.CLAIM_CEILING,
        "preflight_manifest": {"path": str(preflight.resolve()), "sha256": preflight_sha},
        "contract": sealed_contract,
        "controller_review": frozen["controller_review"],
        "e1_terminal_receipt": frozen["e1_terminal_receipt"],
        "bindings": frozen["bindings"],
        "checkout_root": str(ca.REPO.resolve()),
        "output_root": str(output.resolve()),
        "tle_root": str(ca.CANONICAL_TLE_ROOT),
        "preregistration": frozen["preregistration"],
        "tle_archive": frozen["tle_archive"],
        "lineage_authorities": frozen["lineage_authorities"],
        "formula_digests": frozen["formula_digests"],
        "launch_arguments": arguments,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def write_authority(
    *, preflight_manifest: Path, contract: Path, output_root: Path,
    tle_root: Path, profile_count_cap: int, launch_arguments: Sequence[str],
    output: Path,
) -> tuple[Path, Path, str]:
    target = Path(output)
    if target.exists() or target.is_symlink() or Path(f"{target}.sha256").exists():
        raise ca.CAError("refusing to overwrite launch authority or sidecar")
    payload = build_authority(
        preflight_manifest=preflight_manifest, contract=contract,
        output_root=output_root, tle_root=tle_root,
        profile_count_cap=profile_count_cap, launch_arguments=launch_arguments,
        authority_path=target,
    )
    digest = ca.write_once(target, payload)
    sidecar = ca._write_sidecar(target, digest)
    ca.validate_launch_authority(
        target, preflight_path=preflight_manifest,
        preflight_sha256=ca.file_sha256(preflight_manifest),
        profile_count_cap=profile_count_cap,
    )
    return target, sidecar, digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--profile-count-cap", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--launch-arguments", nargs=argparse.REMAINDER, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        ca.pin_single_thread_runtime()
        args = _parser().parse_args(argv)
        target, sidecar, digest = write_authority(
            preflight_manifest=args.preflight_manifest,
            contract=args.contract,
            output_root=args.output_root,
            tle_root=args.tle_root,
            profile_count_cap=args.profile_count_cap,
            launch_arguments=args.launch_arguments,
            output=args.output,
        )
    except Exception as error:
        print(f"CA_LAUNCH_AUTHORITY_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"CA_LAUNCH_AUTHORITY_PASS authority={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
