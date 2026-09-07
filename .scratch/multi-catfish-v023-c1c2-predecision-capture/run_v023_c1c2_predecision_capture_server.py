#!/usr/bin/env python3
"""Explicit Ubuntu-server entrypoint for one TRAIN predecision capture.

Importing this file is inert: no NumPy, PyTorch, simulator, TLE reader, or
runtime adapter is imported until :func:`launch_capture` is called after the
CLI has checked the write-once output boundary.  The bridge writes one
canonical V2 JSON capture and refuses to overwrite an existing target.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import sys
import traceback
from types import ModuleType
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE_ADAPTER_PATH = (
    REPO / ".scratch" / "multi-catfish-v023-r6-fit-binding-fix" / "v023_lcsrs_source_adapter.py"
)
BRIDGE_PATH = HERE / "v023_c1c2_predecision_capture.py"
PREFLIGHT_PATH = (
    REPO / ".scratch" / "multi-catfish-v023-r6-fit-binding-fix" / "PREFLIGHT-MANIFEST.json"
)
PREFLIGHT_DIGEST_PATH = (
    REPO / ".scratch" / "multi-catfish-v023-r6-fit-binding-fix" / "PREFLIGHT-MANIFEST.sha256"
)
EXECUTION_ADDENDUM_PATH = (
    REPO / "docs" / "MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"
)
WORLDS = tuple(range(2026121705, 2026121713))
LINEAGE = 2026092101
SOURCE_FAMILY = "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1"
PLACEBO_KEY = "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1"
PLACEBO_KEY_SHA256 = "7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825"


class PredecisionServerError(RuntimeError):
    """The explicit capture-server boundary failed closed."""


def _load_module(name: str, path: Path) -> ModuleType:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise PredecisionServerError(f"required module is missing or symlinked: {target}")
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise PredecisionServerError(f"cannot load required module: {target}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise PredecisionServerError(f"module import failed: {target}") from error
    return module


def _assert_write_once(output: Path) -> Path:
    target = Path(output)
    if not target.is_absolute():
        raise PredecisionServerError("--output must be an absolute path")
    if target.exists() or target.is_symlink():
        raise PredecisionServerError(f"refusing to overwrite capture: {target}")
    return target.resolve(strict=False)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", type=int, choices=WORLDS, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=PREFLIGHT_PATH)
    parser.add_argument("--manifest-digest", type=Path, default=PREFLIGHT_DIGEST_PATH)
    parser.add_argument("--execution-addendum", type=Path, default=EXECUTION_ADDENDUM_PATH)
    parser.add_argument("--placebo-key", default=PLACEBO_KEY)
    parser.add_argument("--placebo-key-sha256", default=PLACEBO_KEY_SHA256)
    parser.add_argument("--lineage", type=int, default=LINEAGE)
    parser.add_argument("--source-family", default=SOURCE_FAMILY)
    parser.add_argument("--preflight-sha256", required=True)
    parser.add_argument("--c1-neutral-seed", type=int)
    parser.add_argument("--c2-neutral-seed", type=int)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def launch_capture(args: argparse.Namespace) -> Path:
    """Capture one world after explicit argument and output checks."""

    output = _assert_write_once(Path(args.output))
    bridge = _load_module("mcrl_v023_c1c2_capture_bridge_server", BRIDGE_PATH)
    adapter = _load_module("mcrl_v023_c1c2_source_adapter_server", SOURCE_ADAPTER_PATH)
    config_type = getattr(adapter, "V023SourceAdapterConfig", None)
    if not callable(config_type):
        raise PredecisionServerError("source adapter lacks V023SourceAdapterConfig")
    try:
        config = config_type(
            tle_root=Path(args.tle_root).resolve(strict=False),
            prereg=Path(args.prereg).resolve(strict=False),
            manifest=Path(args.manifest).resolve(strict=False),
            manifest_digest=Path(args.manifest_digest).resolve(strict=False),
            execution_addendum=Path(args.execution_addendum).resolve(strict=False),
            placebo_key=str(args.placebo_key),
            placebo_key_sha256=str(args.placebo_key_sha256),
            lineage=int(args.lineage),
            source_family=str(args.source_family),
        )
        payload = bridge.capture_world(
            config,
            world=int(args.world),
            expected_manifest_sha256=str(args.preflight_sha256),
            c1_neutral_seed=args.c1_neutral_seed,
            c2_neutral_seed=args.c2_neutral_seed,
        )
        bridge.write_capture(payload, output)
    except Exception as error:
        raise PredecisionServerError("TRAIN predecision capture failed closed") from error
    return output


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = launch_capture(args)
    except PredecisionServerError as error:
        print(f"PREDECISION_CAPTURE_ERROR world={args.world} pid={os.getpid()}: {error}", file=sys.stderr)
        traceback.print_exception(error, file=sys.stderr)
        return 2
    print(f"PREDECISION_CAPTURE_PASS: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
