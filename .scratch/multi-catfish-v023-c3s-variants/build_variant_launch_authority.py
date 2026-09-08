#!/usr/bin/env python3
"""Build one immutable exact-invocation C3-S variant launch authority."""

from __future__ import annotations
import argparse
from pathlib import Path
import sys
from typing import Sequence
import run_v023_c3s_variants as runner


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--launch-arguments", nargs=argparse.REMAINDER, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        runner.pin_single_thread_runtime()
        target = runner._local(args.output, field_name="launch authority")
        payload = runner.build_authority(preflight=args.preflight_manifest, contract=args.contract,
                                         output_root=args.output_root, launch_arguments=args.launch_arguments,
                                         authority_path=target)
        target, sidecar, digest = runner.write_once_with_sidecar(target, payload)
    except Exception as error:
        print(f"C3S_VARIANTS_AUTHORITY_ERROR: {error}", file=sys.stderr); return 2
    print(f"C3S_VARIANTS_AUTHORITY_PASS authority={target} sidecar={sidecar} sha256={digest}"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
