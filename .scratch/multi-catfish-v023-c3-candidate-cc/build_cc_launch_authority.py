#!/usr/bin/env python3
"""Build an immutable per-invocation C-C launch authority."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3_candidate_cc as cc


def build_authority(
    *,
    preflight_manifest: Path,
    contract: Path,
    from_e1_root: Path,
    output_root: Path,
    launch_arguments: Sequence[str],
    authority_path: Path,
) -> dict[str, object]:
    preflight_path = Path(preflight_manifest)
    _manifest, preflight_sha = cc.validate_preflight_manifest(preflight_path)
    sealed_contract = cc.sealed_contract_binding()
    contract_path = Path(contract)
    source = Path(from_e1_root)
    destination = Path(output_root)
    authority = cc._candidate_local(Path(authority_path), field="launch authority")
    if (
        not contract_path.is_absolute()
        or str(contract_path.resolve()) != sealed_contract["path"]
    ):
        raise cc.CCError("--contract must be the absolute controller-sealed C-C contract")
    if not source.is_absolute() or source.is_symlink() or not source.is_dir():
        raise cc.CCError("--from-e1-root must be an absolute non-symlink directory")
    if not destination.is_absolute() or destination.is_symlink():
        raise cc.CCError("--output-root must be an absolute non-symlink path")
    destination = cc._candidate_local(destination, field="output root")

    arguments = list(launch_arguments)
    if not arguments or any(not isinstance(value, str) for value in arguments):
        raise cc.CCError("--launch-arguments must contain one exact runner invocation")
    parsed = cc._parser().parse_args(arguments)
    if (
        parsed.dry_run
        or (parsed.unit is None) == (not parsed.merge)
        or parsed.launch_authority is None
        or Path(parsed.launch_authority).resolve() != authority
        or parsed.from_e1_root is None
        or Path(parsed.from_e1_root).resolve() != source.resolve()
        or parsed.output is None
        or Path(parsed.output).resolve() != destination
        or Path(parsed.preflight_manifest).resolve() != preflight_path.resolve()
    ):
        raise cc.CCError("launch arguments do not bind one exact C-C unit/merge invocation")
    if parsed.unit is not None:
        try:
            cc.e1.UnitKey.parse(parsed.unit)
        except cc.e1.E1Error as error:
            raise cc.CCError(str(error)) from error

    e1_input = cc.discover_e1_input(source, hash_tapes=True)
    terminal_binding = e1_input.get("terminal_receipt")
    if (
        not isinstance(terminal_binding, dict)
        or terminal_binding.get("sha256") != cc.E1_TERMINAL_SHA256
    ):
        raise cc.CCError("E1 input does not carry the reviewed terminal digest")
    e1_input = {
        **e1_input,
        "terminal_receipt": {
            **terminal_binding,
            "sha256": cc.E1_TERMINAL_SHA256,
        },
    }

    return {
        "schema": cc.LAUNCH_AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": cc.CLAIM_CEILING,
        "preflight_manifest": {
            "path": str(preflight_path.resolve()),
            "sha256": preflight_sha,
        },
        "contract": sealed_contract,
        "e1_input": e1_input,
        "code_files": cc.expected_code_bindings(),
        "output_root": str(destination),
        "launch_arguments": arguments,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def write_authority(
    *,
    preflight_manifest: Path,
    contract: Path,
    from_e1_root: Path,
    output_root: Path,
    launch_arguments: Sequence[str],
    output: Path,
) -> tuple[Path, Path, str]:
    target = cc._candidate_local(Path(output), field="launch authority")
    payload = build_authority(
        preflight_manifest=preflight_manifest,
        contract=contract,
        from_e1_root=from_e1_root,
        output_root=output_root,
        launch_arguments=launch_arguments,
        authority_path=target,
    )
    return cc.write_once_with_sidecar(target, payload)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--from-e1-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--launch-arguments", nargs=argparse.REMAINDER, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        cc.pin_single_thread_runtime()
    except cc.CCError as error:
        print(f"C_C_LAUNCH_AUTHORITY_ERROR: {error}", file=sys.stderr)
        return 2
    args = _parser().parse_args(argv)
    try:
        target, sidecar, digest = write_authority(
            preflight_manifest=args.preflight_manifest,
            contract=args.contract,
            from_e1_root=args.from_e1_root,
            output_root=args.output_root,
            launch_arguments=args.launch_arguments,
            output=args.output,
        )
    except Exception as error:
        print(f"C_C_LAUNCH_AUTHORITY_ERROR: {error}", file=sys.stderr)
        return 2
    print(
        f"C_C_LAUNCH_AUTHORITY_PASS authority={target} "
        f"sidecar={sidecar} sha256={digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
