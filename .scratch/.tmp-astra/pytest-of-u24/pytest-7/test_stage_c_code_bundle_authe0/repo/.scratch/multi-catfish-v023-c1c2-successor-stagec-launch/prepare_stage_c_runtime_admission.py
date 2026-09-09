#!/usr/bin/env python3
"""Prepare Stage-C runtime admission after Stage-A/B PASS, without launching."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import run_v023_c1c2_successor_stage_c as controller
import stagec_common as common


def prepare(args: argparse.Namespace) -> dict[str, object]:
    bindings = common.verify_bindings(args.bindings)
    supplement = common.verify_stage_ab_supplement(
        args.admission_supplement, args.bindings, bindings
    )
    stage_b = supplement["stage_b_pass_receipt"]
    expected_gate = args.stage_b_root / "stage-b-gate.json"
    if stage_b.get("path") != str(expected_gate.resolve()):
        raise common.StageCError("supplement Stage-B gate differs from requested root")
    resolved = common.materialize_stage_ab(bindings, supplement)
    common.verify_runtime_identity(resolved)
    controller._authenticate_stage_b(
        args.stage_b_root, common.file_sha256(args.bindings)
    )
    runner = controller._module(
        common.PHYSICAL / "v023_c1c2_successor_physical_runner.py"
    )
    return controller._stage_c_runtime_admission(
        bindings=resolved,
        runner=runner,
        stage_b_root=args.stage_b_root,
        admission_root=args.output_root,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--admission-supplement", type=Path, required=True)
    parser.add_argument("--stage-b-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        admission = prepare(args)
    except Exception as error:
        print(f"STAGEC_RUNTIME_ADMISSION_ERROR: {error}", file=sys.stderr)
        return 2
    print(
        "FORMAL_RUNTIME_ADMITTED "
        f"path={admission['admission_path']} sha256={admission['admission_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
