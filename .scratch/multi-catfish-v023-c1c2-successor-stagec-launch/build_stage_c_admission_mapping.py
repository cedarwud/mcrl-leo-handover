#!/usr/bin/env python3
"""Build the authenticated four-arm admission mapping for Stage-C chunk merge."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import run_v023_c1c2_successor_stage_c as sequential_controller
import stagec_common as common


def build(args: argparse.Namespace) -> dict[str, object]:
    bindings = common.verify_bindings(args.bindings)
    supplement = common.verify_stage_ab_supplement(
        args.admission_supplement, args.bindings, bindings
    )
    common.verify_acceptance_bundle(
        args.acceptance_bundle,
        {**bindings, "bindings_sha256": common.file_sha256(args.bindings)},
    )
    bindings = common.materialize_stage_ab(bindings, supplement)
    common.verify_runtime_identity(bindings, chunk_mode=True)
    bindings_sha = common.file_sha256(args.bindings)
    sequential_controller._authenticate_stage_b(args.stage_b_root, bindings_sha)

    runner = sequential_controller._module(
        common.PHYSICAL / "v023_c1c2_successor_physical_runner.py"
    )
    runtime_admission = runner.authenticate_runtime_admission(
        args.runtime_admission,
        expected_sha256=common.verify_named_sidecar(args.runtime_admission),
        expected_statuses=(
            "PASS_SOURCE_TRAINING_INTEGRITY",
            "PASS_PLUMBING_INTEGRITY",
        ),
    )
    policies = sequential_controller._policies(bindings, runner)
    adapter, _plan = sequential_controller._adapter_and_plan(
        bindings,
        runner,
        policies=policies,
        runtime_admission=runtime_admission,
    )
    return {"admission_mapping": sequential_controller._admission_mapping(bindings, adapter)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--admission-supplement", type=Path, required=True)
    parser.add_argument("--acceptance-bundle", type=Path, required=True)
    parser.add_argument("--runtime-admission", type=Path, required=True)
    parser.add_argument("--stage-b-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build(args)
        common.write_once(args.output, payload)
        common.write_digest_sidecar(args.output)
        digest = common.file_sha256(args.output)
    except Exception as error:
        print(f"STAGEC_ADMISSION_MAPPING_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"STAGEC_ADMISSION_MAPPING_WRITTEN path={args.output} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
